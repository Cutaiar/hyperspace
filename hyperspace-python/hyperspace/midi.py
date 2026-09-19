"""MIDI adapter — any registry Param ↔ any MIDI message, with feedback.

The inbound half of the DAW bridge (BLUEPRINT §3.6, plan 05 task 3): a
hardware controller drives the same parameter registry the panel draws,
so anything the panel can change, a knob can change. This module depends
on params.py; nothing in the core imports it — app.py attaches it only
when a configured port is present, and the adapter costs nothing absent.

The bindings are rows of the one table in routing.py — `Binding` here is
that class — with a MIDI source (``cc:<ch>:<n>``, ``note:<ch>:<n>``,
``pitch:<ch>``) and an op that says how to read the message:

  cc   abs      absolute 7-bit knob or fader → set_norm, with soft pickup:
                after the param moved by other means the knob does nothing
                until it sweeps through the current value, so a band switch
                or a theme load never jumps a knob's value.
       rel      two's-complement relative encoder → step(±n)
       rel64    64-centred relative encoder → step(±n)
       toggle   rising edge → toggle()/fire()
  note toggle   note-on → toggle()/fire() (enum: next choice)
       momentary note-on sets on, note-off sets off (toggle params)
       set      note-on → set(value) — one button per enum choice
       step     note-on → step(value)
  pitch abs     14-bit pitch bend → set_norm

Feedback runs every frame, change-gated: "ring" sends the param's norm
back as the same CC (LED rings on knobs); "led" sends a note velocity
that tracks the param — a toggle's state, or whether an enum equals the
binding's value — so the surface always shows what the engine has.
Triggers echo their press so the button lights while held.

Bindings persist with every other source's in bindings.json (routing.py;
an old midi_map.json is migrated on first run). With no file the device
profile's default map is used; right-click → Learn on any panel control
writes the file. `MidiMap` is the MIDI-side view of that table — what
MidiIO routes through and the panel edits. The profile (apc40.py is the
first) knows the device's port name, its power-up SysEx, which controls
have rings, and what velocities its LEDs take.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import mido

from . import apc40
from .params import Kind, Param, Registry
from .routing import Binding, Bindings, act, bindings_path

PROFILES = {"apc40": apc40}
MAP_FILE = bindings_path()
RECONNECT_S = 2.0
PICKUP_TOL = 1.5 / 127   # a knob "reaches" the value within this

__all__ = ["PICKUP_TOL", "Binding", "MidiIO", "MidiMap", "find_port"]


class MidiMap:
    """The MIDI rows of the binding table, indexed for routing.

    Wraps a routing.Bindings — the app's shared one, or a table loaded
    from `path` (a bindings.json; an old midi_map.json is migrated).
    """

    def __init__(self, path: Path | None = MAP_FILE, profile: str = "apc40",
                 table: Bindings | None = None):
        self.table = table if table is not None else Bindings.load(path, profile)

    @property
    def path(self) -> Path | None:
        return self.table.path

    @property
    def profile(self) -> str:
        return self.table.profile

    @property
    def error(self) -> str:
        return self.table.error

    @property
    def bindings(self) -> list[Binding]:
        return self.table.midi()

    def route(self, kind: str, channel: int, number: int) -> list[Binding]:
        return self.table.route(kind, channel, number)

    def for_param(self, pid: str) -> Binding | None:
        return self.table.for_param(pid)

    def bind(self, b: Binding) -> None:
        self.table.bind(b)

    def unbind(self, pid: str) -> None:
        self.table.unbind(pid)

    def write(self) -> None:
        self.table.write()


def find_port(names: list[str], match: str) -> str | None:
    m = match.lower()
    return next((n for n in names if m in n.lower()), None)


class MidiIO:
    """One controller: opens the ports, routes input, sends feedback.

    `inp`/`out` may be injected (tests hand in fakes with iter_pending()
    and send()); otherwise the ports are found by substring and reopened
    on their own if the device disappears.
    """

    def __init__(self, registry: Registry, mapping: MidiMap | None = None, *,
                 port: str | None = None, profile: str = "apc40", inp=None, out=None,
                 clock=time.monotonic):
        self.reg = registry
        self.map = mapping if mapping is not None else MidiMap(profile=profile)
        self.profile = PROFILES.get(self.map.profile) or PROFILES[profile]
        self.port_match = port or self.profile.PORT_MATCH
        self.clock = clock
        self.inp, self.out = inp, out
        self._injected = inp is not None or out is not None
        self.name = ""
        self.error = ""
        self.last = ""          # last message seen, for the status line
        self.learning: str | None = None
        self._next_try = 0.0
        self._writes: dict[str, float] = {}  # param → norm we last wrote / saw
        if self._injected:
            self.name = "injected"
            self._enter()
        else:
            self._connect()

    # ---- ports ----

    @property
    def on(self) -> bool:
        return self.inp is not None

    def _connect(self) -> None:
        self._next_try = self.clock() + RECONNECT_S
        try:
            ins = mido.get_input_names()
            outs = mido.get_output_names()
        except Exception as e:  # noqa: BLE001 — backend missing / broken
            self.error = f"{type(e).__name__}: {e}"[:120]
            return
        name = find_port(ins, self.port_match)
        if name is None:
            self.inp = self.out = None
            return
        try:
            self.inp = mido.open_input(name)
            oname = find_port(outs, self.port_match)
            self.out = mido.open_output(oname) if oname else None
        except Exception as e:  # noqa: BLE001
            self.error = f"open {name}: {e}"[:120]
            self.inp = self.out = None
            return
        self.name = name
        self.error = ""
        print(f"midi: {name} ({self.profile.__name__.rsplit('.', 1)[-1]}, "
              f"{len(self.map.bindings)} bindings)", file=sys.stderr)
        self._enter()

    def _enter(self) -> None:
        """Device power-up: mode SysEx and every ring/LED at its true value."""
        for b in self.map.bindings:
            b.last_out = None
            b.caught = False
        if self.out is not None:
            for msg in self.profile.enter():
                self._send(msg)
            self.feedback()

    def close(self) -> None:
        if self.out is not None:
            try:
                for msg in self.profile.leave():
                    self._send(msg)
            except Exception:  # noqa: BLE001, S110
                pass
        for port in (self.inp, self.out):
            if port is not None and not self._injected:
                try:
                    port.close()
                except Exception:  # noqa: BLE001, S110
                    pass
        self.inp = self.out = None

    def _send(self, msg) -> None:
        if self.out is None:
            return
        try:
            self.out.send(msg)
        except Exception as e:  # noqa: BLE001 — device yanked mid-frame
            self.error = f"send: {e}"[:120]
            self.inp = self.out = None

    # ---- learn / bindings ----

    def learn(self, pid: str | None) -> None:
        self.learning = pid

    def binding_for(self, pid: str) -> Binding | None:
        return self.map.for_param(pid)

    def unbind(self, pid: str) -> None:
        b = self.map.for_param(pid)
        if b is not None and b.feedback:
            self._dark(b)
        self.map.unbind(pid)

    def _learned(self, kind: str, channel: int, number: int, value: int) -> None:
        pid = self.learning
        self.learning = None
        p = self.reg.get(pid)
        if p is None:
            return
        b = Binding(Binding.midi_source(kind, channel, number), pid, "abs")
        if kind == "cc":
            if self.profile.is_relative(number):
                b.op = "rel"
            elif p.kind is Kind.TRIGGER:
                b.op = "toggle"
        elif kind == "note":
            b.op = "toggle"
        old = self.map.for_param(pid)
        if old is not None and old.feedback:
            self._dark(old)
        for x in self.map.route(kind, channel, number):
            if x.feedback:
                self._dark(x)
        fb = self.profile.feedback_for(kind, channel, number)
        if fb:
            b.feedback, b.ring = fb["feedback"], fb.get("ring", b.ring)
            b.on, b.off = fb.get("on", b.on), fb.get("off", b.off)
        self.map.bind(b)
        self.last = f"learned {pid} ← {b.describe()}"

    # ---- per frame ----

    def poll(self) -> None:
        if not self.on:
            if not self._injected and self.clock() >= self._next_try:
                self._connect()
            if not self.on:
                return
        self._uncatch_moved()
        try:
            msgs = list(self.inp.iter_pending())
        except Exception as e:  # noqa: BLE001
            self.error = f"read: {e}"[:120]
            self.inp = self.out = None
            return
        for msg in msgs:
            self._handle(msg)
        self.feedback()

    def _uncatch_moved(self) -> None:
        """A param that moved without us re-arms pickup on its knob."""
        for b in self.map.bindings:
            if b.kind not in ("cc", "pitch") or b.op != "abs" or not b.pickup:
                continue
            p = self.reg.get(b.target)
            if p is None or p.kind is Kind.TRIGGER:
                continue
            seen = self._writes.get(b.target)
            if b.caught and seen is not None and abs(p.norm - seen) > PICKUP_TOL:
                b.caught = False

    def _handle(self, msg) -> None:
        t = msg.type
        if t == "control_change":
            kind, number, value = "cc", msg.control, msg.value
        elif t in ("note_on", "note_off"):
            kind, number = "note", msg.note
            value = msg.velocity if t == "note_on" else 0
        elif t == "pitchwheel":
            kind, number, value = "pitch", 0, msg.pitch + 8192
        else:
            return
        ch = msg.channel
        self.last = f"{kind} {number} ch{ch + 1} = {value}"
        if self.learning is not None:
            if kind != "note" or value > 0:
                self._learned(kind, ch, number, value)
            return
        for b in self.map.route(kind, ch, number):
            p = self.reg.get(b.target)
            if p is not None and b.enabled:
                self._apply(b, p, value)

    def _apply(self, b: Binding, p: Param, value: int) -> None:
        op = b.op
        if b.kind == "note":
            pressed = value > 0
            if op == "momentary":
                if p.kind is Kind.TOGGLE:
                    p.set(pressed)
                elif pressed:
                    p.toggle()
            elif not pressed:
                if p.kind is Kind.TRIGGER:
                    b.lit = False
                return
            else:  # set / step / toggle / fire — the discrete ops every button shares
                act(self.reg, b)
                if op == "toggle":
                    b.lit = True
            self._note_written(p)
            return
        # cc / pitch
        full = 16383.0 if b.kind == "pitch" else 127.0
        u = value / full
        if op == "rel":
            n = value if value < 64 else value - 128
            p.step(n)
        elif op == "rel64":
            p.step(value - 64)
        elif op == "toggle":
            was = b.last_hw or 0.0
            b.last_hw = u
            if u > 0 and was == 0:
                p.cycle(1) if p.kind is Kind.ENUM else p.toggle()
        elif op == "step":
            if u > 0 and (b.last_hw or 0.0) == 0:
                p.step(int(b.value))
            b.last_hw = u
        else:  # abs, with pickup
            if p.kind is Kind.TRIGGER:
                if u >= 0.5 and (b.last_hw or 0.0) < 0.5:
                    p.fire()
                b.last_hw = u
                return
            if b.pickup and not b.caught:
                cur = p.norm
                crossed = b.last_hw is not None and (b.last_hw - cur) * (u - cur) <= 0
                if abs(u - cur) <= PICKUP_TOL or crossed:
                    b.caught = True
                b.last_hw = u
                if not b.caught:
                    return
            b.last_hw = u
            p.set_norm(u)
        self._note_written(p)

    def _note_written(self, p: Param) -> None:
        if p.kind is not Kind.TRIGGER:
            self._writes[p.id] = p.norm

    # ---- feedback ----

    def feedback(self) -> None:
        """Push every bound param's state to its ring or LED, change-gated."""
        if self.out is None:
            return
        for b in self.map.bindings:
            if not b.feedback:
                continue
            p = self.reg.get(b.target)
            if p is None:
                continue
            if b.feedback == "ring":
                v = round(p.norm * 127)
                if b.last_out is None:
                    for msg in self.profile.ring_setup(b.channel or 0, b.number, b.ring):
                        self._send(msg)
                if v != b.last_out:
                    b.last_out = v
                    self._send(mido.Message(
                        "control_change", channel=b.channel or 0, control=b.number, value=v
                    ))
            elif b.feedback == "led":
                lit = self._lit(b, p)
                v = b.on if lit else b.off
                if v != b.last_out:
                    b.last_out = v
                    self._send(mido.Message(
                        "note_on", channel=b.channel or 0, note=b.number, velocity=v
                    ))

    @staticmethod
    def _lit(b: Binding, p: Param) -> bool:
        if p.kind is Kind.TOGGLE:
            return bool(p.value) if b.op != "set" else bool(p.value) == bool(b.value)
        if p.kind is Kind.ENUM:
            return p.value == int(b.value) if b.op == "set" else b.lit
        if p.kind is Kind.CONTINUOUS and b.op == "set":
            return abs(p.norm - float(b.value)) <= PICKUP_TOL
        return b.lit

    def _dark(self, b: Binding) -> None:
        if b.kind == "note":
            self._send(mido.Message(
                "note_on", channel=b.channel or 0, note=b.number, velocity=b.off
            ))
        elif b.kind == "cc" and b.feedback == "ring":
            for msg in self.profile.ring_setup(b.channel or 0, b.number, 0):
                self._send(msg)
        b.last_out = None

    def on_reload(self) -> None:
        """Hot reload: re-send everything so the surface matches the code."""
        for b in self.map.bindings:
            b.last_out = None
