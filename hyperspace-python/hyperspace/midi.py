"""MIDI adapter — any registry Param ↔ any MIDI message, with feedback.

The inbound half of the DAW bridge (BLUEPRINT §3.6, plan 05 task 3): a
hardware controller drives the same parameter registry the panel draws,
so anything the panel can change, a knob can change. This module depends
on params.py; nothing in the core imports it — app.py attaches it only
when a configured port is present, and the adapter costs nothing absent.

A Binding ties one (message kind, channel, number) to one param id and
says how to read it:

  cc   abs      absolute 7-bit knob or fader → set_norm, with soft pickup:
                after the param moved by other means the knob does nothing
                until it sweeps through the current value, so a band switch
                or a theme load never jumps a knob's value.
       rel      two's-complement relative encoder → step(±n)
       rel64    64-centred relative encoder → step(±n)
       trigger  rising edge → toggle()/fire()
  note trigger  note-on → toggle()/fire() (enum: next choice)
       momentary note-on sets on, note-off sets off (toggle params)
       set      note-on → set(value) — one button per enum choice
       step     note-on → step(value)
  pitch abs     14-bit pitch bend → set_norm

Feedback runs every frame, change-gated: "ring" sends the param's norm
back as the same CC (LED rings on knobs); "led" sends a note velocity
that tracks the param — a toggle's state, or whether an enum equals the
binding's value — so the surface always shows what the engine has.
Triggers echo their press so the button lights while held.

Bindings persist in midi_map.json next to presets.json. With no file the
device profile's default map is used; right-click → Learn on any panel
control writes the file. The profile (apc40.py is the first) knows the
device's port name, its power-up SysEx, which controls have rings, and
what velocities its LEDs take.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import mido

from . import apc40
from .params import Kind, Param, Registry

PROFILES = {"apc40": apc40}
MAP_FILE = Path("midi_map.json")
RECONNECT_S = 2.0
PICKUP_TOL = 1.5 / 127   # a knob "reaches" the value within this


@dataclass
class Binding:
    param: str
    kind: str                    # "cc" | "note" | "pitch"
    number: int = 0              # cc number or note; ignored for pitch
    channel: int | None = None   # 0-based; None matches any channel
    mode: str = "abs"
    value: float = 1.0           # "set": the choice / "step": the delta
    pickup: bool = True
    feedback: str | None = None  # "ring" | "led" | None
    on: int = 1                  # led velocity when lit
    off: int = 0                 # led velocity when dark
    ring: int = 2                # ring style for "ring" feedback (profile-defined)
    # runtime, not persisted
    caught: bool = field(default=False, repr=False, compare=False)
    last_hw: float | None = field(default=None, repr=False, compare=False)
    last_out: int | None = field(default=None, repr=False, compare=False)
    lit: bool = field(default=False, repr=False, compare=False)

    @property
    def key(self) -> tuple:
        return (self.kind, self.channel, self.number)

    def to_json(self) -> dict:
        d = asdict(self)
        for k in ("caught", "last_hw", "last_out", "lit"):
            d.pop(k)
        return d

    @classmethod
    def from_json(cls, d: dict) -> Binding:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def describe(self) -> str:
        ch = "any ch" if self.channel is None else f"ch{self.channel + 1}"
        if self.kind == "pitch":
            return f"MIDI pitch bend {ch}"
        what = "CC" if self.kind == "cc" else "note"
        extra = "" if self.mode in ("abs", "trigger") else f" {self.mode}"
        return f"MIDI {what} {self.number} {ch}{extra}"

    def matches(self, kind: str, channel: int, number: int) -> bool:
        if self.kind != kind:
            return False
        if self.channel is not None and self.channel != channel:
            return False
        return self.kind == "pitch" or self.number == number


class MidiMap:
    """The binding table, persisted as JSON, indexed for routing."""

    def __init__(self, path: Path | None = MAP_FILE, profile: str = "apc40"):
        self.path = path
        self.profile = profile
        self.bindings: list[Binding] = []
        self.error = ""
        if not self._read():
            self.bindings = [Binding.from_json(b) for b in PROFILES[profile].DEFAULT_MAP]

    def route(self, kind: str, channel: int, number: int) -> list[Binding]:
        return [b for b in self.bindings if b.matches(kind, channel, number)]

    def for_param(self, pid: str) -> Binding | None:
        return next((b for b in self.bindings if b.param == pid), None)

    def bind(self, b: Binding) -> None:
        """A control drives one param; a param keeps one control per role.

        Drops whatever the key drove before, and the param's previous
        binding in the same role: a knob (any cc or pitch binding) when
        learning a knob, or a button of the same mode and value when
        learning a button — so a param's step buttons survive a knob learn.
        """
        def same_role(x: Binding) -> bool:
            if x.param != b.param:
                return False
            if b.kind == "note":
                return x.kind == "note" and x.mode == b.mode and x.value == b.value
            return x.kind in ("cc", "pitch")

        self.bindings = [x for x in self.bindings if x.key != b.key and not same_role(x)]
        self.bindings.append(b)
        self.write()

    def unbind(self, pid: str) -> None:
        self.bindings = [b for b in self.bindings if b.param != pid]
        self.write()

    def _read(self) -> bool:
        if self.path is None or not self.path.exists():
            return False
        try:
            data = json.loads(self.path.read_text())
            self.profile = data.get("profile", self.profile)
            self.bindings = [Binding.from_json(b) for b in data.get("bindings", [])]
            return True
        except (OSError, ValueError, TypeError) as e:
            self.error = f"midi map: {e}"
            return False

    def write(self) -> None:
        if self.path is None:
            return
        try:
            self.path.write_text(json.dumps(
                {"version": 1, "profile": self.profile,
                 "bindings": [b.to_json() for b in self.bindings]},
                indent=1,
            ))
            self.error = ""
        except OSError as e:
            self.error = f"midi map: {e}"


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
        b = Binding(pid, kind, number, channel)
        if kind == "cc":
            if self.profile.is_relative(number):
                b.mode = "rel"
            elif p.kind is Kind.TRIGGER:
                b.mode = "trigger"
        elif kind == "note":
            b.mode = "trigger"
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
            if b.kind not in ("cc", "pitch") or b.mode != "abs" or not b.pickup:
                continue
            p = self.reg.get(b.param)
            if p is None or p.kind is Kind.TRIGGER:
                continue
            seen = self._writes.get(b.param)
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
            p = self.reg.get(b.param)
            if p is not None:
                self._apply(b, p, value)

    def _apply(self, b: Binding, p: Param, value: int) -> None:
        mode = b.mode
        if b.kind == "note":
            pressed = value > 0
            if mode == "momentary":
                if p.kind is Kind.TOGGLE:
                    p.set(pressed)
                elif pressed:
                    p.toggle()
            elif not pressed:
                if p.kind is Kind.TRIGGER:
                    b.lit = False
                return
            elif mode == "set":
                if p.kind is Kind.CONTINUOUS:
                    p.set_norm(float(b.value))
                elif p.kind is Kind.TOGGLE:
                    p.set(bool(b.value))
                elif p.kind is Kind.ENUM:
                    p.set(int(b.value))
                else:
                    p.fire()
            elif mode == "step":
                p.step(int(b.value))
            else:  # trigger
                p.cycle(1) if p.kind is Kind.ENUM else p.toggle()
                b.lit = True
            self._note_written(p)
            return
        # cc / pitch
        full = 16383.0 if b.kind == "pitch" else 127.0
        u = value / full
        if mode == "rel":
            n = value if value < 64 else value - 128
            p.step(n)
        elif mode == "rel64":
            p.step(value - 64)
        elif mode == "trigger":
            was = b.last_hw or 0.0
            b.last_hw = u
            if u > 0 and was == 0:
                p.cycle(1) if p.kind is Kind.ENUM else p.toggle()
        elif mode == "step":
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
            p = self.reg.get(b.param)
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
            return bool(p.value) if b.mode != "set" else bool(p.value) == bool(b.value)
        if p.kind is Kind.ENUM:
            return p.value == int(b.value) if b.mode == "set" else b.lit
        if p.kind is Kind.CONTINUOUS and b.mode == "set":
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
