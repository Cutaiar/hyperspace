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

Every op here is a scene-setter (plan 09 decision 3): on a param a
performer owns — a hand, a lane, an LFO riding it through routing.py —
an `abs` knob moves the *return value*, the base the performer works
from and the param comes back to when the performer leaves. Nothing
prompts and nothing is blocked; the knob simply never sees the offset.

Feedback runs every frame, change-gated: "ring" sends ``p.norm`` — the
base, so a ring shows the knob's own setting and never chases a
performer — back as the same CC (LED rings on knobs); "led" sends a note
velocity from `_lit`: on a toggle, or on an enum `set` row, it reads
``p.value``, the effective value, so it follows a performer; on a
continuous `set` row it compares the base (``p.norm``) with the row's
value; any other row echoes its own press. So the surface shows
what the engine has, except a ring, which shows what the hand set.
Triggers echo their press so the button lights while held, or show a
light of their own when the param carries one (``Registry.trigger(lit=)``:
the METRONOME LED blinks on the beat through ``lfo.trigger``).

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
from .routing import Binding, Bindings, Owned, act, bindings_path

PROFILES = {"apc40": apc40}
MAP_FILE = bindings_path()
RECONNECT_S = 2.0
PICKUP_TOL = 1.5 / 127   # a knob "reaches" the value within this

__all__ = ["PICKUP_TOL", "Binding", "MidiIO", "MidiMap", "Ports", "find_port"]


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


class Ports:
    """An input and an output, found by name substring, reopened on their
    own when they vanish — the port handling MidiIO and bridge.py share.

    `inp`/`out` may be injected (tests hand in fakes with iter_pending()
    and send()). A controller names both by one substring; the bridge
    names each side on its own — None leaves that side closed. An error
    on either side drops both, and `retry` reopens them after RECONNECT_S.
    """

    def __init__(self, in_match: str | None, out_match: str | None = None, *,
                 inp=None, out=None, clock=time.monotonic):
        self.in_match, self.out_match = in_match, out_match
        self.clock = clock
        self.inp, self.out = inp, out
        self.injected = inp is not None or out is not None
        self.name = "injected" if self.injected else ""
        self.in_name = self.out_name = self.name
        self.error = ""
        self._next_try = 0.0

    @property
    def on(self) -> bool:
        return self.inp is not None or self.out is not None

    def connect(self) -> bool:
        """Open whatever is present now; True when something opened."""
        self._next_try = self.clock() + RECONNECT_S
        try:
            iname = find_port(mido.get_input_names(), self.in_match) if self.in_match else None
            oname = find_port(mido.get_output_names(), self.out_match) if self.out_match else None
        except Exception as e:  # noqa: BLE001 — backend missing / broken
            self.error = f"{type(e).__name__}: {e}"[:120]
            return False
        if iname is None and oname is None:
            self.inp = self.out = None
            return False
        try:
            self.inp = mido.open_input(iname) if iname else None
            self.out = mido.open_output(oname) if oname else None
        except Exception as e:  # noqa: BLE001
            self.error = f"open {iname or oname}: {e}"[:120]
            self.inp = self.out = None
            return False
        self.in_name, self.out_name = iname or "", oname or ""
        self.name = iname or oname
        self.error = ""
        return True

    def retry(self) -> bool:
        """Reconnect when due; True the frame the ports come back."""
        if self.on or self.injected or self.clock() < self._next_try:
            return False
        return self.connect()

    def recv(self) -> list:
        """Drain the input; a read error drops the ports (retry reopens)."""
        if self.inp is None:
            return []
        try:
            return list(self.inp.iter_pending())
        except Exception as e:  # noqa: BLE001
            self.error = f"read: {e}"[:120]
            self.inp = self.out = None
            return []

    def send(self, msg) -> None:
        if self.out is None:
            return
        try:
            self.out.send(msg)
        except Exception as e:  # noqa: BLE001 — device yanked mid-frame
            self.error = f"send: {e}"[:120]
            self.inp = self.out = None

    def close(self) -> None:
        for port in (self.inp, self.out):
            if port is not None and not self.injected:
                try:
                    port.close()
                except Exception:  # noqa: BLE001, S110
                    pass
        self.inp = self.out = None


class MidiIO:
    """One controller: opens the ports, routes input, sends feedback.

    `inp`/`out` may be injected (tests hand in fakes with iter_pending()
    and send()); otherwise the ports are found by substring and reopened
    on their own if the device disappears (`Ports`).
    """

    def __init__(self, registry: Registry, mapping: MidiMap | None = None, *,
                 port: str | None = None, profile: str = "apc40", inp=None, out=None,
                 clock=time.monotonic):
        self.reg = registry
        self.map = mapping if mapping is not None else MidiMap(profile=profile)
        self.profile = PROFILES.get(self.map.profile) or PROFILES[profile]
        self.port_match = port or self.profile.PORT_MATCH
        self.ports = Ports(self.port_match, self.port_match, inp=inp, out=out, clock=clock)
        self.last = ""          # last message seen, for the status line
        self.learning: str | None = None
        # a hand learn the referee refused, (new row, the target's current
        # performer), held until the panel's prompt calls resolve_pending
        self.pending: tuple[Binding, Binding] | None = None
        self._writes: dict[str, float] = {}  # param → norm we last wrote / saw
        if self.ports.injected:
            self._enter()
        elif self.ports.connect():
            self._connected()

    # ---- ports ----

    @property
    def on(self) -> bool:
        return self.ports.on

    @property
    def inp(self):
        return self.ports.inp

    @property
    def out(self):
        return self.ports.out

    @property
    def name(self) -> str:
        return self.ports.name

    @property
    def error(self) -> str:
        return self.ports.error

    def _connected(self) -> None:
        print(f"midi: {self.name} ({self.profile.__name__.rsplit('.', 1)[-1]}, "
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
        self.ports.close()

    def _send(self, msg) -> None:
        self.ports.send(msg)

    # ---- learn / bindings ----

    def learn(self, pid: str | None) -> None:
        """Arm (or cancel) a learn. A learn the prompt hasn't answered yet
        is forgotten: the new one is what the performer means now."""
        self.learning = pid
        self.pending = None

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

    def learn_source(self, source: str, when: str | None = None) -> None:
        """Another adapter completes the learn with one of its own sources
        (hands/core.py: ``hand:<i>``): a `position` route at depth 1 — the
        source is the whole fader, through the Router like every route,
        with no pickup and no device feedback. `when` gates the row on a
        second source (a pinch held while learning), so the row only acts
        while that reads on.

        A learned axis drives one param: learning it onto another *moves*
        it (its other position rows go), and learning it again onto the
        same param only refreshes the gate. If the param already has a
        different performer the learn is held in `pending` for the panel's
        prompt (`resolve_pending`) — the table untouched until it answers —
        rather than taking the target or being lost. `learning` is cleared
        first, so the hands adapter, which keys off it, cannot fire again.
        """
        pid = self.learning
        self.learning = None
        if pid is None or self.reg.get(pid) is None:
            return
        b = Binding(source, pid, "position", 1.0, when=when)
        table = self.map.table
        cur = table.owner(pid)
        if cur is not None and cur.source == source and cur.op == "position":
            cur.when = when                          # the same axis again: no move
            self.map.write()
            self.last = f"learned {pid} ← {cur.describe()}"
            return
        if cur is not None:
            self.pending = (b, cur)
            self.last = f"{Owned(cur, b)} — replace?"
            return
        self._place(b)

    def resolve_pending(self, replace: bool) -> Binding | None:
        """The prompt's answer to a held learn: *Replace* swaps the target's
        performer for the learned row and writes the file; *Keep* leaves
        the table as it was. Returns the row now in the table, or None."""
        if self.pending is None:
            return None
        new, old = self.pending
        self.pending = None
        if not replace:
            self.last = f"kept {old.describe()} on {old.target}"
            return None
        self._place(new)
        return new

    def _place(self, b: Binding) -> None:
        """The learned row into the table: the axis's other position rows
        go first (one axis, one param), then `replace_owner` — the one door
        onto a target, which reads the owner *now* (a free target takes the
        row; the prompt's Replace removes whoever holds it at this moment,
        not whoever did when the question was asked) — then the file."""
        table = self.map.table
        for x in [x for x in table.of(b.scheme) if x.source == b.source and x.op == "position"]:
            table.remove(x)
        table.replace_owner(b)
        self.map.write()
        self.last = f"learned {b.target} ← {b.describe()}"

    # ---- per frame ----

    def poll(self) -> None:
        if not self.on:
            if self.ports.retry():
                self._connected()
            if not self.on:
                return
        self._uncatch_moved()
        for msg in self.ports.recv():
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
        if p.kind is Kind.TRIGGER:
            # the press echo, or a light the param carries itself (a trigger
            # declared with `lit=`: the METRONOME LED blinking on the beat)
            return b.lit or bool(p.get())
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
