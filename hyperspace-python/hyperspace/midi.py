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
                or a preset load never jumps a knob's value.
       rel      two's-complement relative encoder → step(±n)
       rel64    64-centred relative encoder → step(±n)
       toggle   rising edge → toggle()/fire()
  note toggle   note-on → toggle()/fire() (enum: next choice)
       momentary note-on sets on, note-off sets off (toggle params)
       set      note-on → set(value) — one button per enum choice
       step     note-on → step(value)
       hold     the target fires once the button has been down HOLD_S,
                while it is still held; a shorter press does nothing.
                A `set` row on an enum that declares `held` (Param.held:
                the preset bank) is a press *and* a hold: the press sets
                at once, and held HOLD_S it calls held(choice) — a bank pad
                on an empty slot saves the live state there; the new pad
                blinks.
                Rows with one target are one control (a bar): any of them held lights
                them all, a hand across several fires once, and a button
                still down afterwards fires nothing more. On the fire the
                bar, and every LED the fire turned on, blink for BLINK_S
                (the profile's `blink_of`) and then show their own state;
                a fire that answers False did nothing, and nothing blinks
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

Two layers under a latched SHIFT (plan 13 §3). A message goes to the
invariant rows on its control, else to the rows of the layer that is up
(`Bindings.dispatch`) — nothing falls through, so a control the up layer
does not map does nothing; a note-off goes to the rows its note-on went
to, whatever the layer is by then (D12). Only the up layer's rows and the
invariant ones draw (`Bindings.active`); a layer switch or a desk
replacement re-sends every ring and LED (`redraw`), a control no active
row draws going dark. A knob's ring also re-bases the endless encoder
(`apc40.RING_REBASES_KNOB`, hand check 31), so the row is caught at the
value just sent; the faders keep soft pickup, and a desk replacement (a
preset load) clears the catch of a fader whose param it moved — the
crossfader and the session's faders keep their hold through it.

Bindings persist with every other source's in bindings.json (routing.py;
an old midi_map.json is migrated on first run). With no file the device
profile's default map is used. Right-click → Learn on any panel control,
then a knob or button, writes a preset-layer row into the loaded preset
(`_learned`, plan 13 §3.3): the preset is dirty and bindings.json is not
written; a learn on an invariant control or with the global layer up is
refused with the reason. `MidiIO.bindings` is the MIDI-side view of that table —
what this adapter routes through and the panel edits. The profile (apc40.py is the
first) knows the device's port name, its power-up SysEx, which controls
have rings, and what velocities its LEDs take.

Knob smoothing (plan 18 WP2). `set_norm` lands on a detent, and an
untapered param has 100 of them, so a slow turn used to move the base a
whole detent at a time. With the session's `desk.slew` above 0
(`Bindings.slew`, seconds; 0 on a bare table, routing.SLEW_DEFAULT_S in
the app) an `abs` row on a continuous, non-integer param aims a glide
instead (`_aim`), and `_glide` walks the base to it once a poll: a
straight line, written between detents with `Param.set`, that arrives
`desk.slew` after the last message with the very `set_norm` the row makes
today, so the value rests where it always did. Still a scene-setter
writing the base, never an offset. One glide per param, whoever sent it.
Anyone else's write to the param ends its glide and stands (the panel, a
key, an undo); a preset load ends every glide but a session param's
(`redraw`); a layer switch ends none; turning `desk.slew` to 0, or the
port going away, lands them all at once. A ring shows where the knob is
sending the base, not the base in flight (`_ring_norm`): the same message
as before, so the encoder is never re-based behind the hand. `rel` and
`rel64` knobs, buttons and discrete targets are not smoothed. At 0 no
glide is ever made and every base and every message sent is as before.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

import mido

from . import apc40
from .learn import Learn
from .params import Kind, Param, Registry
from .routing import (
    PICKUP_TOL,
    Binding,
    Bindings,
    act,
    bindings_path,
    is_session_id,
    led_level,
    led_lit,
    register_desk,
)

PROFILES = {"apc40": apc40}          # config's `[midi] profile` names one of these
RECONNECT_S = 2.0
RECONNECT_FAST = 5        # looks at RECONNECT_S after a port goes missing, then
RECONNECT_SLOW_S = 10.0   # this often. Every look makes a CoreMIDI client; one
#                           the system refuses aborts the process inside rtmidi,
#                           past any `except` (audit R15), so a desk that is not
#                           there is not asked after thirty times a minute all night
HOLD_S = 0.6        # a `hold` row fires once its button has been down this long


def _hold_key(b) -> object:
    """What one hold fires once for: a `hold` row's target (its bar is one
    control, however many buttons are down), a held `set` row's target and
    choice (each bank pad its own slot)."""
    return b.target if b.op == "hold" else (b.target, float(b.value))
BLINK_S = 1.5       # how long the LEDs blink after a hold fires
SLEW_TOL = 1e-6     # norm: further than this from our last write, someone else set it
SLEW_BACK_S = 0.05  # a new glide starts at the previous poll, no further back than this

__all__ = ["PICKUP_TOL", "Binding", "MidiIO", "Ports", "Slew", "find_port", "retry_after"]


@dataclass
class Slew:
    """One param's glide (knob smoothing, `MidiIO._aim` / `_glide`)."""

    y: float            # where the base is now, norm, between detents
    target: float       # where it will rest: the norm `set_norm(u)` lands
    t: float            # the clock at the last step
    t_end: float        # the clock when it lands: the last message + desk.slew
    wrote: float        # p.norm as read back after our last write
    steps: int = 0      # the steps it has taken (`_glide`)


def find_port(names: list[str], match: str) -> str | None:
    m = match.lower()
    return next((n for n in names if m in n.lower()), None)


def retry_after(misses: int) -> float:
    """Seconds until the next look for a missing port, after `misses` looks
    in a row that opened nothing."""
    return RECONNECT_S if misses <= RECONNECT_FAST else RECONNECT_SLOW_S


class Ports:
    """An input and an output, found by name substring, reopened on their
    own when they vanish — the port handling MidiIO and bridge.py share.

    `inp`/`out` may be injected (tests hand in fakes with iter_pending()
    and send()). A controller names both by one substring; the bridge
    names each side on its own — None leaves that side closed. An error
    on either side drops both, and `retry` reopens them after RECONNECT_S
    — after RECONNECT_FAST looks that found nothing, every RECONNECT_SLOW_S
    (`retry_after`); a port that opens puts the count back to zero, so one
    that drops mid-set is looked for quickly again.
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
        self.misses = 0           # looks in a row that opened nothing

    @property
    def on(self) -> bool:
        return self.inp is not None or self.out is not None

    def connect(self) -> bool:
        """Open whatever is present now; True when something opened."""
        self.misses += 1
        self._next_try = self.clock() + retry_after(self.misses)
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
        self.misses = 0
        self._next_try = self.clock() + RECONNECT_S      # (not the slow pace it was found at)
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

    def __init__(self, registry: Registry, table: Bindings | None = None, *,
                 path: Path | None = None, port: str | None = None, profile: str = "apc40",
                 inp=None, out=None, clock=time.monotonic, learner: Learn | None = None):
        self.reg = registry
        # the binding table — the app's shared one, or one loaded from
        # `path` (a bindings.json; an old midi_map.json beside it is
        # migrated) — the home's own when neither is given, resolved now,
        # not at import; this adapter reads its MIDI rows off it
        if table is None:
            table = Bindings.load(bindings_path() if path is None else path, profile)
        self.table = table
        self.profile = PROFILES.get(self.table.profile) or PROFILES[profile]
        self.port_match = port or self.profile.PORT_MATCH
        self.ports = Ports(self.port_match, self.port_match, inp=inp, out=out, clock=clock)
        self.clock = clock      # times a `hold` row's press and the blink after it
        self.last = ""          # last message seen, for the status line
        # the armed param and the held question (learn.py) — the app's
        # shared one, so a hand can complete a learn this adapter never
        # sees; a bare adapter (tests, the probe) makes its own
        self.learner = learner if learner is not None else Learn(registry, self.table)
        self._writes: dict[str, float] = {}  # param → norm we last wrote / saw
        # D12: a note-on's rows, by (channel, note), so its note-off goes to
        # the same rows whatever layer is up by then
        self._held: dict[tuple[int, int], list[Binding]] = {}
        # the `hold` rows of each note still down, with the time of its
        # press, by (channel, note); and the controls blinking after a
        # hold fired, with the time each stops
        self._holds: dict[tuple[int, int], tuple[float, list[Binding]]] = {}
        self._blinks: dict[tuple, float] = {}
        # the table's layer / desk counters as last drawn (`_follow_table`)
        self._seen = self._serials()
        # every control feedback has drawn since the last redraw, by
        # (kind, channel, number), with the row that drew it: a redraw
        # darkens each one no active row draws now, even when the row that
        # lit it has left the table (a preset load's smaller desk, the
        # ROUTING page's ×) — D8, review of PR #67
        self._shown: dict[tuple, Binding] = {}
        # knob smoothing: the glides in flight, by param id, and the clock
        # at the previous poll (where a new glide's line starts)
        self._slews: dict[str, Slew] = {}
        self._polled: float | None = None
        # params seen to move on their own (`_glide`): written at once
        self._restless: set[str] = set()
        # SHIFT's param and the smoothing's, for a bare adapter too
        register_desk(registry, self.table)
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
              f"{len(self.bindings)} bindings)", file=sys.stderr)
        self._enter()

    def _enter(self) -> None:
        """Device power-up: mode SysEx and every ring/LED at its true value.
        A press held across a reconnect is forgotten: no hold, no blink."""
        self._hold_state()[0].clear()
        self._hold_state()[1].clear()
        self._light_bars()
        for b in self.bindings:
            b.last_out = None
            b.caught = False
        if self.out is not None:
            for msg in self.profile.enter():
                self._send(msg)
            self.redraw()

    def close(self) -> None:
        self._land_all()        # knob smoothing: no value is left between detents at exit
        if self.out is not None:
            try:
                for msg in self.profile.leave():
                    self._send(msg)
            except Exception:  # noqa: BLE001, S110
                pass
        self.ports.close()

    def _send(self, msg) -> None:
        self.ports.send(msg)

    # ---- the table's MIDI rows ----

    @property
    def bindings(self) -> list[Binding]:
        """The MIDI rows of the shared table (`Bindings.midi`); the edits
        (`bind`, `route`, `for_param`, `write`) are the table's own."""
        return self.table.midi()

    # ---- learn / bindings ----

    def binding_for(self, pid: str) -> Binding | None:
        return self.table.for_param(pid)

    def unbind(self, pid: str) -> list[Binding]:
        """The loaded preset's desk rows on `pid` go — `Learn.unbind` with
        the routes left alone (plan 17 WP1: the menu calls the learn object
        itself, so Unbind is there with no adapter). The table's
        `redraw_serial` moves, so this adapter redraws and the controls go
        dark (`_follow_table`); the undo step, and the refusal for a param
        only the session maps (D5, D6), are `Learn.unbind`'s."""
        return self.learner.unbind((pid,), routes=False, name=self.control_name)

    def control_name(self, b: Binding) -> str:
        """The control a row names, in the device's words where the
        profile has them — its glyph, then Akai's name ("D3 (device knob 3)",
        plan 14 WP7) — else the row's own."""
        name = getattr(self.profile, "named", None) or getattr(self.profile, "control_name", None)
        return (name(b.source) if name is not None else None) or b.describe()

    def _learned(self, kind: str, channel: int, number: int, value: int) -> None:
        """A desk message completes the armed learn: `Learn.learn_control`
        with this device's profile (plan 17 WP2, fork 7 — the row-making
        lives there, so a click on the on-screen desk makes the same row
        with no adapter). When it lands, the table's `redraw_serial` tells
        this adapter to redraw; a refusal (the global layer, D5) changes
        nothing and leaves the learn armed."""
        self.learner.learn_control(Binding.midi_source(kind, channel, number), self.profile)

    # ---- per frame ----

    def poll(self) -> None:
        if not self.on:
            if self.ports.retry():
                self._connected()
            if not self.on:
                self._land_all()    # no device: nothing is left in flight
                return
        self._follow_table()
        self._uncatch_moved()
        for msg in self.ports.recv():
            self._handle(msg)
        self._fire_holds()
        self._follow_table()        # SHIFT pressed just now: this frame's redraw
        # knob smoothing: each glide's step for this frame — after the
        # table is followed, so a preset a pad loaded in this very poll has
        # ended its glides (`redraw`) before any of them steps over it
        self._glide(self._now())
        self.feedback()

    def _follow_table(self) -> None:
        """A layer switch or a desk replacement since the last look: redraw
        every ring and LED; a replacement (a preset load) also clears the
        catch of each fader whose param it moved; a desk row edited in place (`redraw_serial`, the
        ROUTING page) only redraws."""
        seen = self._serials()
        if seen != self._seen:
            load = seen[1] != self._seen[1]
            self._seen = seen
            self.redraw(load=load)

    def _serials(self) -> tuple[int, int, int]:
        t = self.table
        return t.layer_serial, t.desk_serial, getattr(t, "redraw_serial", 0)

    def _uncatch_moved(self) -> None:
        """A param that moved without us re-arms pickup on its knob."""
        for b in self.bindings:
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
        if kind == "note" and value == 0 and self._hold_state()[0].pop((ch, number), None):
            self._light_bars()      # let go before HOLD_S: a tap, nothing fires
        # an armed learn (plan 17 WP2): a CC or a press is a candidate only
        # when the learn waits for the desk (`Learn.accepts`: not during a
        # hand learn) and the control is not invariant (fork 6: SHIFT, a
        # fader, TAP do their own job while a learn is armed). A candidate
        # is not dispatched, landed or refused; everything else is, as if
        # no learn were armed — a note-off included (never a candidate)
        lrn = self.learner
        if lrn.learning is not None and (kind != "note" or value > 0):
            source = Binding.midi_source(kind, ch, number)
            if lrn.accepts(source) and not self.table.is_invariant(Binding(source, lrn.learning)):
                for b in self.table.dispatch(kind, ch, number):
                    self._passed_over(b, value)
                self._learned(kind, ch, number, value)
                return
        # the layer is read at the press (D12): a note-off goes to the rows
        # its note-on went to, whatever is up by now
        if kind == "note" and value > 0:
            rows = self._held[(ch, number)] = self.table.dispatch(kind, ch, number)
        elif kind == "note":
            rows = self._held.pop((ch, number), None)
            if rows is None:
                rows = self.table.dispatch(kind, ch, number)
        else:
            rows = self.table.dispatch(kind, ch, number)
            for b in self.table.route(kind, ch, number):    # (dispatch leaves these out)
                if not b.enabled:
                    self._passed_over(b, value)
        timed = []
        for b in rows:
            p = self.reg.get(b.target)
            if p is None or not b.enabled:
                self._passed_over(b, value)
                continue
            if b.op == "hold":      # timed, never applied; only a note has a press
                timed.append(b)
            else:
                self._apply(b, p, value)
                if b.op == "set" and getattr(p, "held", None) is not None:
                    timed.append(b)     # a press that is a hold as well (a bank pad)
        if timed and kind == "note" and value > 0:
            self._hold_state()[0][(ch, number)] = (self._now(), timed)
            self._light_bars()

    @staticmethod
    def _passed_over(b: Binding, value: int) -> None:
        """A message its row did not apply (the row is disabled, or an
        armed learn took it): the fader or knob moved without its param,
        so a pickup row has to pick up again from where the control is
        now — its next applied message would otherwise write the whole
        distance it travelled meanwhile (audit R13)."""
        if b.kind in ("cc", "pitch") and b.op == "abs" and b.pickup:
            b.caught = False
            b.last_hw = value / (16383.0 if b.kind == "pitch" else 127.0)

    # ---- hold rows ----

    def _hold_state(self) -> tuple[dict, dict]:
        """(`_holds`, `_blinks`) — made here for an adapter from before a
        hot reload, which keeps the object and never re-runs __init__."""
        d = self.__dict__
        return d.setdefault("_holds", {}), d.setdefault("_blinks", {})

    def _now(self) -> float:
        return self.__dict__.setdefault("clock", self.ports.clock)()

    def _light_bars(self) -> None:
        """A `hold` row's press echo, spread over its bar: every enabled
        hold row is lit while any press on its target is being timed."""
        held = {b.target for _t, rows in self._hold_state()[0].values() for b in rows}
        for b in self.bindings:
            if b.op == "hold":
                b.lit = b.enabled and b.target in held

    def _leds_on(self) -> set[tuple]:
        """The controls whose LED an active row lights now."""
        on = set()
        for b in self.table.active():
            p = self.reg.get(b.target) if b.feedback == "led" else None
            if p is not None and self._lit(b, p):
                on.add(b.control)
        return on

    def _fire_holds(self) -> None:
        """Every press held HOLD_S or longer fires its target, once per
        target however many buttons of the bar are down, and every press
        on that target is forgotten: a button still down fires nothing
        more, only a new press starts a new hold. The bar's rows and each
        LED the fire turned on then blink for BLINK_S (`feedback`) — the
        adapter does not know why a light came on (after a save-as it is
        the new slot's pad). A fire that returns False says it did
        nothing (a save that failed): no blink, the bar just goes dark."""
        holds, blinks = self._hold_state()
        if not holds:
            return
        now = self._now()
        fired: set = set()
        for t0, rows in list(holds.values()):
            if now - t0 < HOLD_S:
                continue
            for b in rows:
                p = self.reg.get(b.target)
                if p is None or not b.enabled or _hold_key(b) in fired:
                    continue
                fired.add(_hold_key(b))
                before = self._leds_on()
                # a `hold` row fires its trigger; a `set` row held (a bank
                # pad) hands its choice to the param's `held` (Param.held)
                done = p.fire() if b.op == "hold" else p.held(int(b.value))
                if done is False:
                    continue
                bar = {x.control for x in self.table.active()
                       if x.op == "hold" and x.target == b.target and x.feedback == "led"}
                for c in (self._leds_on() - before) | bar:
                    blinks[c] = now + BLINK_S
        if fired:
            for key in [k for k, (_t, rows) in holds.items()
                        if any(_hold_key(b) in fired for b in rows)]:
                del holds[key]
            self._light_bars()

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
            # knob smoothing (plan 18 WP2): a continuous value glides to
            # where set_norm would put it; at desk.slew 0, and on a
            # discrete or integer target, the write is the immediate one
            seconds = getattr(self.table, "slew", 0.0)
            if (seconds > 0.0 and p.kind is Kind.CONTINUOUS and not p.integer
                    and p.id not in self.__dict__.setdefault("_restless", set())):
                self._aim(p, u, seconds)
            else:
                self._slew_state().pop(p.id, None)
                p.set_norm(u)
        self._note_written(p)

    def _note_written(self, p: Param) -> None:
        if p.kind is not Kind.TRIGGER:
            self._writes[p.id] = p.norm

    # ---- knob smoothing ----

    def _slew_state(self) -> dict[str, Slew]:
        """`_slews` — made here for an adapter from before a hot reload."""
        return self.__dict__.setdefault("_slews", {})

    @staticmethod
    def _landing(p: Param, u: float) -> float:
        """The norm `p.set_norm(u)` would leave: the detent, read back the
        way `Param.norm` reads it, so a ring drawn from it is the ring
        drawn after the write."""
        k = round(min(max(float(u), 0.0), 1.0) * p.steps)
        v = p.taper.map(k) if p.taper is not None else p._value_of_norm(k / p.steps)
        return p._norm_of(v)

    def _aim(self, p: Param, u: float, seconds: float) -> None:
        """Point the param's glide at what `set_norm(u)` would land, to
        arrive `seconds` from now. A param with no glide — or one somebody
        else has written since ours — starts one from where the base is,
        its line beginning at the previous poll (no further back than
        SLEW_BACK_S), so the first step lands on the frame the message
        arrives: the glide adds no dead frame. One glide per param: a
        second control on the same param re-aims it, from where it is."""
        slews, now = self._slew_state(), self._now()
        s = slews.get(p.id)
        if s is None or abs(p.norm - s.wrote) > SLEW_TOL:
            y = p.norm
            polled = self.__dict__.get("_polled")
            t = now if polled is None else min(max(polled, now - SLEW_BACK_S), now)
            s = slews[p.id] = Slew(y, y, t, now, y)
        s.target = self._landing(p, u)
        s.t_end = now + seconds

    def _glide(self, now: float) -> None:
        """Once a poll: every glide one step along its straight line, or
        its landing — the `set_norm` the knob's row makes with smoothing
        off, so the value rests on the same detent — when its time is up
        or `desk.slew` is now 0. A param whose base is not where this
        adapter left it was set by someone else: theirs stands and the
        glide is dropped. Scene-setter writes of the base, both of them
        (`Param.set`, `Param.set_norm`); never an offset.

        A param that has moved on the very poll after a glide's first step
        is taken to move on its own (`rot.phase.*` while its plane turns:
        the integrator's, not a setting): a glide on it would be dropped
        every frame and never arrive, so from then on its knob writes at
        once, as with smoothing off (`_restless`; review of PR #98)."""
        slews = self._slew_state()
        if slews:
            seconds = getattr(self.table, "slew", 0.0)
            for pid, s in list(slews.items()):
                p = self.reg.get(pid)
                if p is None or abs(p.norm - s.wrote) > SLEW_TOL:
                    if p is not None and s.steps == 1:
                        self.__dict__.setdefault("_restless", set()).add(pid)
                    del slews[pid]
                    continue
                if seconds <= 0.0 or now >= s.t_end:
                    p.set_norm(s.target)
                    del slews[pid]
                else:
                    f = min(max((now - s.t) / (s.t_end - s.t), 0.0), 1.0)
                    s.y += (s.target - s.y) * f
                    p.set(p._value_of_norm(s.y))        # the base, between detents
                    s.t = now
                    s.wrote = p.norm
                    s.steps += 1
                self._note_written(p)       # ours: no fader loses its catch to it
        self._polled = now

    def _land_all(self) -> None:
        """Every glide lands on its target now (the port went away): no
        value is left in flight with nothing polling it. One a foreign
        write has ended is only forgotten."""
        slews = self._slew_state()
        for pid, s in list(slews.items()):
            p = self.reg.get(pid)
            if p is not None and abs(p.norm - s.wrote) <= SLEW_TOL:
                p.set_norm(s.target)
                self._note_written(p)
        slews.clear()

    def _ring_norm(self, p: Param) -> float:
        """What a ring shows for `p`: the base — during a glide the base
        the knob is setting (the glide's target, the value the ring showed
        the same frame before there was a glide), never the base in
        flight, which would re-base the encoder behind the hand."""
        s = self._slew_state().get(p.id)
        return p.norm if s is None else s.target

    # ---- feedback ----

    def feedback(self) -> None:
        """Push every bound param's state to its ring or LED, change-gated.

        Rings show the base — a pickup readback, so a knob can always
        catch its own value under a performer. LEDs on a toggle or an
        enum `set` row show the effective value — a state light shows
        what the show is doing. Intended (owner, 2026-09-28, audit R6).
        An unlit `set` row on an enum whose choice holds something
        (`led_level` 1: a bank pad whose slot is filled, plan 19 WP2) gets
        the profile's `filled_of` velocity where the control has one —
        amber on the clip grid — else its off.
        A control blinking after a hold fired (`_fire_holds`) gets its
        blink velocity, whatever its state, until BLINK_S is up.
        """
        if self.out is None:
            return
        blinks = self._hold_state()[1]
        if blinks:
            now = self._now()
            for c in [c for c, until in blinks.items() if now >= until]:
                del blinks[c]
        blink_of = getattr(self.profile, "blink_of", None)
        # an adapter made before `_shown` existed (a hot reload keeps the
        # object and never re-runs __init__) gets it here
        shown = self.__dict__.setdefault("_shown", {})
        for b in self.table.active():        # the up layer's rows and the invariant ones
            if not b.feedback:
                continue
            p = self.reg.get(b.target)
            if p is None:
                continue
            shown.setdefault(b.control, b)
            if b.feedback == "ring":
                v = round(self._ring_norm(p) * 127)
                if b.last_out is None:
                    for msg in self.profile.ring_setup(b.channel or 0, b.number, b.ring):
                        self._send(msg)
                if v != b.last_out:
                    b.last_out = v
                    self._send(mido.Message(
                        "control_change", channel=b.channel or 0, control=b.number, value=v
                    ))
                    self._rebase(b, p, v)
            elif b.feedback == "led":
                lit = self._lit(b, p)
                v = b.on if lit else b.off
                if not lit and led_level(b, p) == 1:
                    filled_of = getattr(self.profile, "filled_of", None)
                    filled = filled_of(b.number, b.on) if filled_of is not None else None
                    v = b.off if filled is None else filled
                if b.control in blinks:
                    v = blink_of(b.number, b.on) if blink_of is not None else b.on
                if v != b.last_out:
                    b.last_out = v
                    self._send(mido.Message(
                        "note_on", channel=b.channel or 0, note=b.number, velocity=v
                    ))

    def _rebase(self, b: Binding, p: Param, v: int) -> None:
        """Plan 13 D7, hand check 31 (`profile.RING_REBASES_KNOB`): the ring
        CC just sent also set the endless knob's own value, so the knob is
        caught there — its next turn continues from the ring, no pickup.
        A fader never gets here (it has no ring) and keeps soft pickup."""
        if b.op != "abs" or not getattr(self.profile, "RING_REBASES_KNOB", False):
            return
        b.caught, b.last_hw = True, v / 127.0
        if p.kind is not Kind.TRIGGER:
            self._writes[p.id] = p.norm

    def redraw(self, *, load: bool = False) -> None:
        """Every ring and LED for the layer that is up (plan 13 §3.1): each
        control some row names, or feedback drew since the last redraw
        (`_shown` — a row since removed lit it: a preset load's smaller
        desk, the ROUTING page's ×), goes dark unless an active row draws
        it (D8); then every active row is re-sent — a knob's ring re-bases
        it (`_rebase`). `load` (a desk replacement: a preset load) also
        clears a fader's catch when its param is no longer where this
        adapter last put it — `_uncatch_moved`'s test — or it has no last
        write, or the param is not where this fader itself last was
        (`_writes` is per param: another control on the same param may
        have made the last write): a fader whose base the load moved
        picks up, and one whose param the load left alone (the
        crossfader's dim, S1–S8 and SM: a preset never moves a session
        param, D9) keeps its hold (plan 15 WP3, fork 19). A load also ends
        every glide (knob smoothing) but a session param's, before anything
        else: the load's value stands, even where it equals the glide's
        last write; a session param the load never moves goes on arriving,
        and its fader is compared with where the glide is taking the param
        (the fader's own position), so it keeps its hold too."""
        if load:
            slews = self._slew_state()
            for pid in [pid for pid in slews if not is_session_id(pid)]:
                del slews[pid]
        active = self.table.active()
        drawn = {b.control for b in active if b.feedback}
        for b in self.bindings:
            b.last_out = None
            if load and b.kind in ("cc", "pitch") and b.op == "abs" and b.feedback != "ring":
                p, seen = self.reg.get(b.target), self._writes.get(b.target)
                if (p is None or seen is None or b.last_hw is None
                        or abs(p.norm - seen) > PICKUP_TOL
                        or abs(self._ring_norm(p) - b.last_hw) > PICKUP_TOL):
                    b.caught = False
        if self.out is None:
            return
        shown, self._shown = getattr(self, "_shown", {}), {}   # hot-reload safe
        dark: set = set()
        for b in (*self.bindings, *shown.values()):
            c = b.control
            if b.feedback and c not in drawn and c not in dark:
                dark.add(c)
                self._dark(b, velocity=0)
        self.feedback()

    @staticmethod
    def _lit(b: Binding, p: Param) -> bool:
        return led_lit(b, p)       # the rule is the table's: the desk diagram draws it too

    def _dark(self, b: Binding, velocity: int | None = None) -> None:
        if b.kind == "note":
            self._send(mido.Message(
                "note_on", channel=b.channel or 0, note=b.number,
                velocity=b.off if velocity is None else velocity,
            ))
        elif b.kind == "cc" and b.feedback == "ring":
            for msg in self.profile.ring_setup(b.channel or 0, b.number, 0):
                self._send(msg)
        b.last_out = None

    def on_reload(self) -> None:
        """Hot reload: re-send everything so the surface matches the code."""
        for b in self.bindings:
            b.last_out = None
