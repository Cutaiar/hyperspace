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
                or a loadable patch load never jumps a knob's value.
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
                the loadable patch bank) is a press *and* a hold: the press sets
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
loadable patch load) clears the catch of a fader whose param it moved — the
crossfader, MASTER and the meta controller's faders keep their hold through it.

Bindings persist with every other source's in bindings.json (routing.py;
an old midi_map.json is migrated on first run). With no file the device
profile's default map is used. Right-click → Learn on any panel control,
then a knob or button, writes a patch-layer row into the loaded patch
(`_learned`, plan 13 §3.3): the loadable patch is dirty and bindings.json is not
written; a learn on an invariant control or with the global layer up is
refused with the reason. `MidiIO.bindings` is the MIDI-side view of that table —
what this adapter routes through and the panel edits. The profile (apc40.py is the
first) knows the device's port name, its power-up SysEx, which controls
have rings, and what velocities its LEDs take.

Knob smoothing (plan 18 WP2). `set_norm` lands on a detent, and an
untapered param has 100 of them, so a slow turn used to move the base a
whole detent at a time. With the meta controller's `desk.slew` above 0
(`Bindings.slew`, seconds; 0 on a bare table, routing.SLEW_DEFAULT_S in
the app) an `abs` row on a continuous, non-integer param aims a glide
instead (`_aim`), and `_glide` walks the base to it once a poll: a
straight line, written between detents with `Param.set`, that arrives
`desk.slew` after the last message with the very `set_norm` the row makes
today, so the value rests where it always did. Still a scene-setter
writing the base, never an offset. One glide per param, whoever sent it.
Anyone else's write to the param ends its glide and stands (the panel, a
key, an undo); a loadable patch load ends every glide but a shared meta param's
(`redraw`); a layer switch ends none; turning `desk.slew` to 0, or the
port going away, lands them all at once. A ring shows where the knob is
sending the base, not the base in flight (`_ring_norm`): the same message
as before, so the encoder is never re-based behind the hand. `rel` and
`rel64` knobs, buttons and discrete targets are not smoothed. At 0 no
glide is ever made and every base and every message sent is as before.

The fine button (wave 2 T3, register rows 609–610). While `desk.fine` is
on — the profile's `FINE` control held (SEND B on the APC40), or the
param set any other way — an `abs` knob row (one with a ring) on a
continuous, non-integer param reads the knob relatively: each message
moves the base by what the knob moved since its last message, divided by
FINE_DIV, written between detents with `Param.set` (no glide). A tenth of
a MIDI step is under one detent of every param, so a slow turn creeps.
The ring follows the base, and a ring sent re-bases the encoder as ever;
when fine lets go, every knob it moved has its ring re-sent, so the
encoder is re-based onto the param and the next coarse turn continues
from there (no jump, no pickup) — on a profile whose rings do not re-base
(`RING_REBASES_KNOB` False) those knobs lose their catch instead and pick
up. Faders, discrete targets and relative rows are never fine. The button
is the adapter's, not a table row: it works on every bindings.json, gives
way to any row this device's table puts on its control (that row is the
owner's), is never a learn's candidate, and its LED is lit while it is
held. `desk.fine` is the meta controller's (group desk, never saved, not modulatable):
a reconnect lets go of it, as of SAVE.
"""

from __future__ import annotations

import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import mido

from . import apc40, generic, seq_page
from .learn import Learn
from .midiports import port_names
from .params import Kind, Param, Registry, is_meta_id
from .pointer import Through
from .routing import (
    FINE_DIV,
    FINE_PARAM,
    HELD_ONLY,
    PICKUP_TOL,
    SAVE_PARAM,
    Binding,
    Bindings,
    act,
    bindings_path,
    fine_gives_way,
    is_shared_meta_id,
    led_lit,
    led_shade,
    let_go_lost,
    press_momentary,
    register_desk,
)

# a `[[devices]]` MIDI entry's `profile` names one of these (plan 27 B2:
# the entry's, never bindings.json's "profile" field, which says only
# which profile the file's unqualified rows were written for)
PROFILES = {"apc40": apc40, "generic": generic}
RECONNECT_S = 2.0
RECONNECT_FAST = 5        # bridge.OutPort: looks at RECONNECT_S after a port goes missing,
RECONNECT_SLOW_S = 10.0   # then this often; a port that opens starts the count again
HOLD_S = 0.6        # a `hold` row fires once its button has been down this long
REENTER_S = 2.0     # the intro is sent again at most this often (`MidiIO._reenter`)


def _hold_key(b) -> object:
    """What one hold fires once for: a `hold` row's target (its bar is one
    control, however many buttons are down), a held `set` row's target and
    choice (each bank pad its own slot)."""
    return b.target if b.op == "hold" else (b.target, float(b.value))
BLINK_S = 1.5       # how long the LEDs blink after a hold fires
SLEW_TOL = 1e-6     # norm: further than this from our last write, someone else set it
SLEW_BACK_S = 0.05  # a new glide starts at the previous poll, no further back than this
DESK_LOG_SIZE = 20  # the desk event log keeps this many events (plan 24 C1)

__all__ = ["FINE_DIV", "FINE_PARAM", "PICKUP_TOL", "Binding", "DeskEvent", "DeskLog", "MidiIO", "Ports", "Slew",
           "find_port", "retry_after"]


# the desk's held buttons: a toggle the hand holds on, never saved, never
# performed, that losing the desk or a reconnect lets go of
# (`MidiIO._let_go_held`) so a lost note-off cannot leave it down — SAVE
# (routing.register_desk), the base chase (plan 52) and FINE
HELD_PARAMS = (*HELD_ONLY, FINE_PARAM)


@dataclass(frozen=True)
class DeskEvent:
    """One desk event (plan 24 C1): a press, a hold that fired or a
    two-handed save — the control in the device's words, what it did, and
    the layer it was read on: "preset", "global" (SHIFT up), or "both" (an
    invariant control, the same on either)."""

    when: str           # the wall clock, HH:MM:SS
    control: str
    what: str
    layer: str

    def line(self) -> str:
        return f"{self.when}  {self.control}  {self.what}  [{self.layer}]"


class DeskLog:
    """The last `size` desk events, oldest first in `events` (plan 24 C1,
    decision 18: so the owner can see what a press did). The SYSTEM page
    prints `lines()`, newest first. Its own small class, so a device that
    takes the adapter over (plan 27 B2) carries it whole."""

    def __init__(self, size: int = DESK_LOG_SIZE, wall=None):
        self.size = size
        self.events: deque[DeskEvent] = deque(maxlen=size)
        self._wall = wall if wall is not None else (lambda: time.strftime("%H:%M:%S"))

    def add(self, control: str, what: str, layer: str) -> DeskEvent:
        e = DeskEvent(self._wall(), control, what, layer)
        self.events.append(e)
        return e

    def lines(self) -> list[str]:
        """Newest first, one line an event."""
        return [e.line() for e in reversed(self.events)]

    def __len__(self) -> int:
        return len(self.events)


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
    """The port `match` names: exactly, else the first it is part of, so an entry for
    "Launch Control XL" never opens "Launch Control XL 2" when both are there."""
    m = match.lower()
    return next((n for n in names if m == n.lower()), None) or next(
        (n for n in names if m in n.lower()), None)


def retry_after(misses: int) -> float:
    """Seconds until `bridge.OutPort`'s next try, after `misses` in a row that opened
    nothing (`devices.retry_after` is held equal). A desk's `Ports` doesn't slow down."""
    return RECONNECT_S if misses <= RECONNECT_FAST else RECONNECT_SLOW_S


class Ports:
    """An input and an output, found by name substring, reopened on their
    own when they vanish — the port handling MidiIO and bridge.py share.

    `inp`/`out` may be injected (tests hand in fakes with iter_pending()
    and send()). A controller names both by one substring; the bridge
    names each side on its own — None leaves that side closed. An error
    on either side drops both, and `retry` looks again every RECONNECT_S,
    all night: a look is cheap (`midiports`), and a desk plugged back in late
    comes back as soon as one that was only just lost (row 791).
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
        # (the one road; it can't abort on a refusal it sees: audit R15)
        seen = port_names(fresh=True)
        # (only the sides this entry names: an out-only bridge doesn't care for the inputs)
        self.error = (seen.in_why if self.in_match else "") or (seen.out_why if self.out_match else "")
        if self.error:
            return False
        iname = find_port(seen.inputs, self.in_match) if self.in_match else None
        oname = find_port(seen.outputs, self.out_match) if self.out_match else None
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

    Several at once (plan 27 B2): each is one `[[devices]]` MIDI entry,
    with its own `role` and `profile`. It reads and draws only its own
    rows of the shared table (`Bindings.serves`): an unqualified row is the
    first MIDI role's, any other device's rows carry its role
    (``cc@launch:0:7``), and a learn on it writes that form (`qualifier`).
    Each role has its own layer (`Bindings.layer_of`); SHIFT's latch,
    `desk.shift`, is the first role's. `role` None is the first role —
    a bare adapter (the tests', the probe's) is today's one desk.

    Plan 44 D5a: `reg` and `table` read through this desk's own pointer, and
    `learner` through the panel's, once it has them (`point`).
    """

    reg = Through("reg")
    table = Through("table")
    learner = Through("learn", via="panel_pointer")

    def __init__(self, registry: Registry, table: Bindings | None = None, *,
                 path: Path | None = None, port: str | None = None, profile: str = "apc40",
                 inp=None, out=None, clock=time.monotonic, learner: Learn | None = None,
                 role: str | None = None):
        self.reg = registry
        # the binding table — the app's shared one, or one loaded from
        # `path` (a bindings.json; an old midi_map.json beside it is
        # migrated) — the home's own when neither is given, resolved now,
        # not at import; this adapter reads its MIDI rows off it
        if table is None:
            table = Bindings.load(bindings_path() if path is None else path, profile)
        self.table = table
        self.role = role
        if profile not in PROFILES:
            raise ValueError(f"no MIDI profile {profile!r}; one of {', '.join(PROFILES)}")
        self.profile = PROFILES[profile]
        self.port_match = port or self.profile.PORT_MATCH
        if not self.port_match and inp is None and out is None:
            raise ValueError(f"the {profile} profile matches no port by itself — "
                             "give the entry a `port` (a substring of its name)")
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
        # lit it has left the table (a loadable patch load's smaller desk, the
        # ROUTING page's ×) — D8, review of PR #67
        self._shown: dict[tuple, Binding] = {}
        # knob smoothing: the glides in flight, by param id, and the clock
        # at the previous poll (where a new glide's line starts)
        self._slews: dict[str, Slew] = {}
        self._polled: float | None = None
        # params seen to move on their own (`_glide`): written at once
        self._restless: set[str] = set()
        # the last position each fader or knob sent, by control (plan 24
        # C1): a load's fresh rows start from where the control is, so a
        # fader's first move after a load can pick up by crossing
        self._hw: dict[tuple, float] = {}
        # the last twenty desk events, for the SYSTEM page (plan 24 C1)
        self.desk_log = DeskLog()
        # SHIFT's param and the smoothing's, for a bare adapter too
        register_desk(registry, self.table)
        # the fine button (wave 2 T3): the knobs it moved, by control, and
        # its LED as last sent
        self._fine_moved: set[tuple] = set()
        self._fine_was = False
        self._fine_out: int | None = None
        self._fine_held: tuple[int, int] | None = None   # FINE's press, held
        self._fine_seen: tuple | None = None             # `_fine_control`'s cache key
        self._fine_at: tuple[int, int] | None = None
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
        # a SAVE whose note-off was lost (plan 24 C1) must not turn the next
        # pad press into a save: power-up lets go of it
        # (and of FINE, wave 2 T3: the knobs it moved are forgotten with it)
        self._let_go_held()
        self._fine_held, self._fine_was = None, False
        self.__dict__["_fine_moved"] = set()
        # where the faders were is forgotten too: one moved while the cable
        # was out would otherwise seed a false pickup crossing (`redraw`)
        self.__dict__["_hw"] = {}
        for b in self._own_rows():
            b.last_out = None
            b.caught = False
            if b.kind in ("cc", "pitch"):
                b.last_hw = None    # and each row's own last position (review of PR #180)
        if self.out is not None:
            for msg in self.profile.enter():
                self._send(msg)
            self.redraw(whole=True)     # every control: lit by a row, else dark

    def _let_go_held(self, reg=None) -> None:
        """Every press this desk can no longer end (`routing.let_go_lost`), its
        own and no other desk's, and every held button (`HELD_PARAMS`) up, unless
        another device's button still has it. FINE records no press, so this
        is what lets it go. `reg`: the deck it pressed them on, if not this one."""
        reg = reg if reg is not None else self.reg
        presses = self._presses()
        gone = {source for rows in presses.values() for source, _target in rows}
        presses.clear()
        if gone:
            let_go_lost(reg, gone.__contains__)
        for pid in HELD_PARAMS:
            held = reg.get(pid)
            if held is not None and held.value and not held.__dict__.get("_pressed_by"):
                held.set(False)

    def _presses(self) -> dict[tuple[int, int], set[tuple[str, str]]]:
        """What each note of this desk still down holds through a momentary row:
        (channel, note) → its rows' (source, target) as they were at the press.
        A row deleted, retargeted or switched off since cannot lose its release."""
        return self.__dict__.setdefault("_momentary_down", {})

    def close(self) -> None:
        self._let_go_held()     # no poll follows, so `poll`'s cable check will not (plan 52)
        self._land_all()        # knob smoothing: no value is left between detents at exit
        if self.out is not None:
            try:
                for msg in self.profile.leave():
                    self._send(msg)
            except Exception:  # noqa: BLE001, S110
                pass
        self.ports.close()

    def _send(self, msg) -> None:
        if getattr(self.profile, "FEEDBACK", True):      # a generic desk: no lights, nothing sent
            self.ports.send(msg)

    # ---- the table's MIDI rows ----

    @property
    def bindings(self) -> list[Binding]:
        """This device's MIDI rows of the shared table (`Bindings.midi`,
        those `Bindings.serves` says are this role's); the edits (`bind`,
        `route`, `for_param`, `write`) are the table's own."""
        role, t = self._role(), self.table
        return [b for b in t.midi() if t.serves(role, b)]

    def _node_rows(self) -> list[Binding]:
        """What node mode derives for this desk on the deck it is on (N1a)."""
        return self.table.node_rows(self._role())

    def _own_rows(self) -> list[Binding]:
        """Every row of this desk's whose knob or fader state this adapter keeps:
        the table's and the ones node mode derives (never in the table)."""
        return [*self.bindings, *self._node_rows()]

    def _role(self) -> str | None:
        """This device's role (None: the first MIDI role) — read here for
        an adapter from before a hot reload, which has none."""
        return self.__dict__.get("role")

    @property
    def qualifier(self) -> str:
        """What this device's sources carry (plan 27 B2): "" for the first
        MIDI role — every row before plan 27 is unqualified — else its role
        (``cc@launch:0:7``)."""
        role = self._role()
        return "" if self.table.is_primary(role) else (role or "")

    def _source(self, kind: str, channel: int | None, number: int = 0) -> str:
        return Binding.midi_source(kind, channel, number, self.qualifier)

    def _active(self) -> list[Binding]:
        """The rows that show on this device now (`Bindings.active`)."""
        return self.table.active(self._role())

    # ---- learn / bindings ----

    def binding_for(self, pid: str) -> Binding | None:
        return self.table.for_param(pid)

    def unbind(self, pid: str) -> list[Binding]:
        """The loaded patch's desk rows on `pid` go — `Learn.unbind` with
        the routes left alone (plan 17 WP1: the menu calls the learn object
        itself, so Unbind is there with no adapter). The table's
        `redraw_serial` moves, so this adapter redraws and the controls go
        dark (`_follow_table`); the undo step, and the refusal for a param
        only the meta controller maps (D5, D6), are `Learn.unbind`'s."""
        return self.learner.unbind((pid,), routes=False, name=self.control_name)

    def control_name(self, b: Binding) -> str:
        """The control a row names, in the device's words where the
        profile has them — its glyph, then Akai's name ("D3 (device knob 3)",
        plan 14 WP7) — else the row's own. Another desk's row (plan 27 B2)
        is never named in this desk's words: it describes itself."""
        if not self.table.serves(self._role(), b):
            return b.describe()
        name = getattr(self.profile, "named", None) or getattr(self.profile, "control_name", None)
        return (name(b.bare) if name is not None else None) or b.describe()

    def _learned(self, kind: str, channel: int, number: int, value: int) -> None:
        """A desk message completes the armed learn: `Learn.learn_control`
        with this device's profile (plan 17 WP2, fork 7 — the row-making
        lives there, so a click on the on-screen desk makes the same row
        with no adapter). When it lands, the table's `redraw_serial` tells
        this adapter to redraw; a refusal (the global layer, D5) changes
        nothing and leaves the learn armed."""
        self.learner.learn_control(self._source(kind, channel, number), self.profile)

    # ---- per frame ----

    def poll(self) -> None:
        if not self.on:
            if self.__dict__.pop("_was_on", False):
                self._let_go_held()     # the cable went: no note-off is coming (plan 52)
            if self.ports.retry():
                self._connected()
            if not self.on:
                self._land_all()    # no device: nothing is left in flight
                return
        self._was_on = True
        self._follow_pointer()
        self._follow_table()
        self._uncatch_moved()
        for msg in self.ports.recv():
            self._handle(msg)
        self._fire_holds()
        self._follow_table()        # SHIFT pressed just now: this frame's redraw
        # knob smoothing: each glide's step for this frame — after the
        # table is followed, so a loadable patch a pad loaded in this very poll has
        # ended its glides (`redraw`) before any of them steps over it
        self._glide(self._now())
        self._follow_fine()
        self.feedback()

    def point(self, pointer, panel=None) -> None:
        """This desk's rows act on the deck `pointer` is on from now on, and
        its learn is the one the panel's deck holds (plan 44 D5a). The first
        desk carries the sequencer page with it (`seq_page.of`)."""
        self._on = (self.reg, self.table)      # where it was: `_follow_pointer` compares
        self.pointer, self.panel_pointer = pointer, panel
        if self.table.is_primary(self._role()):
            page = seq_page.of(self.reg)
            if page is not None:
                page.pointer = pointer

    def _follow_pointer(self) -> None:
        """The pointer moved since the last look: nothing of the deck left may
        act on the deck arrived at. Each press still down is released now on
        the deck it pressed, by the road a note-off takes, and its real note-off
        goes nowhere (its key stays, mapped to no rows); its held buttons let go
        there too; a timed hold is forgotten; a glide or a catch on a loadable patch's
        param goes, a shared meta param's stays (`is_shared_meta_id`: the same object
        on both); and the new table's rows are drawn and re-armed as a load's
        are. One identity test a frame."""
        was = self.__dict__.get("_on")
        table = self.table
        if was is None or was[1] is table:
            self._on = (self.reg, table)
            return
        for key, rows in self._held.items():
            for b in rows:
                p = was[0].get(b.target)
                if p is not None and b.enabled and b.op != "hold":
                    self._apply(b, p, 0)
            self._held[key] = []
        self._let_go_held(was[0])
        self._on = (self.reg, table)
        holds, blinks = self._hold_state()
        holds.clear()
        blinks.clear()
        for pid in [pid for pid in self._writes if not is_shared_meta_id(pid)]:
            del self._writes[pid]
        self._seen = self._serials()
        self.redraw(load=True)

    def _follow_table(self) -> None:
        """A layer switch or a desk replacement since the last look: redraw
        every ring and LED; a replacement (a loadable patch load) also clears the
        catch of each fader whose param it moved; a desk row edited in place (`redraw_serial`, the
        ROUTING page) only redraws."""
        seen = self._serials()
        if seen != self._seen:
            load = seen[1] != self._seen[1]
            # (node mode's rows came or went, N1a: each fader on them picks up from
            # where it is, as across a layer switch, so leaving never jumps a saved row)
            # (by slices: an adapter from before a hot reload holds a shorter tuple)
            switch = seen[0] != self._seen[0] or seen[4:] != self._seen[4:]
            if seen[3:4] != self._seen[3:4]:
                self._drop_page_holds()
            self._seen = seen
            self.redraw(load=load, switch=switch)

    def _serials(self) -> tuple[int, int, int, int, int]:
        """(this desk's layer serial, the desk serial, the redraw serial,
        the surface page's serial, node mode's rows' serial): the layer serial is
        this role's own (plan 27 B2), so SHIFT on the APC40 never re-arms a second
        desk's faders; the page is the first role's only (plan 31 §A)."""
        t = self.table
        of = getattr(t, "layer_serial_of", None)
        layer = of(self._role()) if of is not None else t.layer_serial
        page = getattr(t, "page_serial", 0) if t.is_primary(self._role()) else 0
        return (layer, t.desk_serial, getattr(t, "redraw_serial", 0), page,
                t.node_rows_serial(self._role()))

    def _page_rows(self) -> list[Binding]:
        """The surface page's rows, on the first MIDI role's desk only."""
        t = self.table
        return getattr(t, "page_rows", []) if t.is_primary(self._role()) else []

    def _drop_page_holds(self) -> None:
        """The page went up (plan 31 §A): a hold timing on one of its
        controls — a bank pad held across SEND A — is forgotten, so it
        cannot save, and its blink goes with it. Its release still goes to
        the rows its press went to (D12), and does nothing."""
        on = {b.control for b in self._page_rows()}
        holds, blinks = self._hold_state()
        for key in [k for k in holds if ("note", *k) in on]:
            del holds[key]
        for c in [c for c in blinks if c in on]:
            del blinks[c]
        self._light_bars()

    def _uncatch_moved(self) -> None:
        """A param that moved without us re-arms pickup on its knob."""
        for b in self._own_rows():
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
        # a desk that fell back to its power-up mode (apc40.fell_back,
        # 2026-10-16): the intro again, and the message read as Mode 2 would
        # send it (a device button on channel 0)
        fell_back = getattr(self.profile, "fell_back", None)
        fell = fell_back is not None and fell_back(kind, ch, number, value > 0,
                                                   (ch, number) in self._held)
        if fell:
            self._reenter()
        ch = getattr(self.profile, "in_channel", lambda k, c, n: c)(kind, ch, number)
        if kind != "note":          # where the control is now (plan 24 C1, `redraw`)
            full = 16383.0 if kind == "pitch" else 127.0
            self.__dict__.setdefault("_hw", {})[(kind, ch, number)] = value / full
        if kind == "note" and value == 0 and self._hold_state()[0].pop((ch, number), None):
            self._light_bars()      # let go before HOLD_S: a tap, nothing fires
        held_fine = self.__dict__.get("_fine_held")
        if kind == "note" and ((value > 0 and self._fine_control() == (ch, number))
                               or (value == 0 and held_fine == (ch, number))):
            self._fine_press(ch, number, value > 0)
            if fell and value > 0 and number in getattr(self.profile, "MODE0_TOGGLES", ()):
                self._fine_press(ch, number, False)     # no release will come (see below)
            return
        # an armed learn (plan 17 WP2): a CC or a press is a candidate only
        # when the learn waits for the desk (`Learn.accepts`: not during a
        # hand learn) and the control is not invariant (fork 6: SHIFT, a
        # fader, TAP do their own job while a learn is armed). A candidate
        # is not dispatched, landed or refused; everything else is, as if
        # no learn were armed — a note-off included (never a candidate)
        lrn, t, role = self.learner, self.table, self._role()
        if lrn.learning is not None and (kind != "note" or value > 0):
            source = self._source(kind, ch, number)
            if lrn.accepts(source) and not t.is_invariant(Binding(source, lrn.learning)):
                for b in t.dispatch(kind, ch, number, role):
                    self._passed_over(b, value)
                self._learned(kind, ch, number, value)
                if kind == "note":
                    self._held[(ch, number)] = []   # its release is the learn's: nothing
                    self._log_press(source, f"learn: {lrn.last}", t.layer_of(role))
                return
        # the layer is read at the press (D12): a note-off goes to the rows
        # its note-on went to, whatever is up by now — on this device's
        # own latch (plan 27 B2)
        if kind == "note" and value > 0:
            rows = self._held[(ch, number)] = t.dispatch(kind, ch, number, role)
        elif kind == "note":
            rows = self._held.pop((ch, number), None)
            if rows is None:
                rows = t.dispatch(kind, ch, number, role)
        else:
            rows = t.dispatch(kind, ch, number, role)
            for b in t.route(kind, ch, number):    # (dispatch leaves these out)
                if not b.enabled and t.serves(role, b):
                    self._passed_over(b, value)
        pressed = kind == "note" and value > 0
        # the layer the press was read on, for the log: "both" when only
        # invariant rows took it
        layer = ("both" if rows and all(b.layer is None for b in rows)
                 else t.layer_of(role))
        source = self._source(kind, ch, number)
        if pressed and self._save_tap(rows, source, layer):
            return                  # SAVE held: the pad saved; it neither loads nor holds
        timed = []
        did: list[str] = []
        for b in rows:
            p = self.reg.get(b.target)
            if p is None or not b.enabled:
                self._passed_over(b, value)
                continue
            if b.op == "hold":      # timed, never applied; only a note has a press
                timed.append(b)
                did.append(f"{p.label}: held {HOLD_S:g} s fires it")
            else:
                self._apply(b, p, value)
                if pressed and b.op == "momentary" and p.kind is Kind.TOGGLE:
                    self._presses().setdefault((ch, number), set()).add((b.source, b.target))
                did.append(p.label if p.kind is Kind.TRIGGER else f"{p.label} → {p.text()}")
                if b.op == "set" and getattr(p, "held", None) is not None:
                    timed.append(b)     # a press that is a hold as well (a bank pad)
        if kind == "note" and not pressed:
            for pressed_by, target in self._presses().pop((ch, number), ()):
                p = self.reg.get(target)        # whatever became of the row since
                if p is not None and pressed_by in p.__dict__.get("_pressed_by", ()):
                    press_momentary(p, pressed_by, False)
        if pressed:
            what = ("; ".join(did) if did
                    else "nothing (its row is off)" if rows
                    else f"nothing (no row on the {layer} layer)")
            self._log_press(source, what, layer)
        if timed and pressed:
            self._hold_state()[0][(ch, number)] = (self._now(), timed)
            self._light_bars()
        # a Mode-0 toggle's note-on that revealed the fall-back is a whole
        # press: the desk, in Alternate mode now, never sends its release,
        # so it is released here (`_held` popped, an echo dark) — else the
        # next press would read as a second note-on while held. The release
        # is no sign itself (held, and off)
        if (fell and pressed
                and number in getattr(self.profile, "MODE0_TOGGLES", ())):
            self._handle(mido.Message("note_off", channel=msg.channel, note=number))

    def _reenter(self) -> None:
        """The desk sent a message only its power-up mode sends
        (`profile.fell_back`): the intro again (`_enter`: the mode SysEx and
        every light, as at a reconnect), at most once every REENTER_S, said
        on stderr and in the desk log."""
        now = self._now()
        last = self.__dict__.get("_reentered")
        if last is not None and now - last < REENTER_S:
            return
        self._reentered = now
        print(f"midi: {self.name} had left the app's mode (it sent a Generic-mode "
              "message) — put back", file=sys.stderr)
        self._log().add(self.name or "desk", "back in the app's mode (it was in Generic "
                        "mode: a power cycle?)", "both")
        self._enter()

    # ---- the two-handed save and the desk log (plan 24 C1) ----

    def _save_tap(self, rows: list[Binding], source: str, layer: str) -> bool:
        """The two-handed save (plan 24 C1, decision 18): while the desk's
        SAVE is held (`desk.save`, track 8's clip stop), a press on a `set`
        row whose param saves into its choice (`Param.save_into`: a bank
        pad) saves the live state into that slot — an empty slot as #158's
        hold does, a filled one as a **new** loadable patch the slot then points
        at (`library.Project.save_into`: nothing is overwritten or
        trashed) — instead of loading it, and starts no hold. The pad
        blinks for BLINK_S when the save worked. SAVE and the pads are
        invariant, so this is the same under SHIFT. True when the press was
        a save tap, whether or not the save worked; False leaves it an
        ordinary press (SAVE up, or a control that is not a bank pad)."""
        save = self.reg.get(SAVE_PARAM)
        if save is None or not save.value:
            return False
        taps = [(b, p) for b in rows if b.op == "set" and b.enabled
                for p in (self.reg.get(b.target),)
                if p is not None and getattr(p, "save_into", None) is not None]
        if not taps:
            return False
        blinks = self._hold_state()[1]
        for b, p in taps:
            k = int(b.value)
            if p.save_into(k) is False:      # not in the slot: no blink (the footer says why)
                self._log_press(source, f"save into slot {k + 1}: did not land there", layer)
                continue
            blinks[b.control] = self._now() + BLINK_S
            self._log_press(source, f"saved into slot {k + 1}: {p.names[k]}", layer)
        return True

    def _log(self) -> DeskLog:
        """The desk log — made here for an adapter from before a hot
        reload, which keeps the object and never re-runs __init__."""
        return self.__dict__.setdefault("desk_log", DeskLog())

    def _log_press(self, source: str, what: str, layer: str) -> None:
        name = getattr(self.profile, "named", None)
        bare = Binding(source, "").bare        # the profile names its own controls
        self._log().add((name(bare) if name is not None else None) or source, what, layer)

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
        for b in self._active():
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
                has = getattr(p, "has", None)
                filled = b.op != "hold" and has is not None and has(int(b.value))
                # a `hold` row fires its trigger; a `set` row held (a bank
                # pad) hands its choice to the param's `held` (Param.held)
                done = p.fire() if b.op == "hold" else p.held(int(b.value))
                layer = "both" if b.layer is None else b.layer
                if done is False:
                    self._log_press(b.source, "held: nothing saved" + (
                        " (a filled pad only loads)" if filled else ""), layer)
                    continue
                self._log_press(b.source, f"held: {p.label}" if b.op == "hold" else
                                f"held: saved into slot {int(b.value) + 1}: {p.names[int(b.value)]}", layer)
                bar = {x.control for x in self._active()
                       if x.op == "hold" and x.target == b.target and x.feedback == "led"}
                # (a pad held: its light says the deck off air, and the save is this
                # deck's, so it may not come on; a save blinks its pad regardless)
                held = {b.control} if b.op != "hold" else set()
                for c in (self._leds_on() - before) | bar | held:
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
                    press_momentary(p, b.source, pressed)
                elif pressed:
                    p.toggle()
            elif not pressed:
                # a press echo goes dark at the release: a trigger's, and an
                # enum stepped by a toggle row (the solo row's next transfer,
                # 2026-10-16 — its light used to stay on for good)
                if p.kind is Kind.TRIGGER or (p.kind is Kind.ENUM and op == "toggle"):
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
            if p.touched is not None and p.touched(u):
                b.last_hw = u                     # (a timed fade's: jitter writes nothing)
                return
            if self._fine_on() and b.feedback == "ring" and p.kind is Kind.CONTINUOUS \
                    and not p.integer:
                self._fine_move(b, p, u)
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

    # ---- the fine button (wave 2 T3) ----

    def _fine_control(self) -> tuple[int, int] | None:
        """(channel, note) of the profile's FINE button, or None: a profile
        with none, or a table that puts a row of this device on it (any
        layer — that row is the owner's, and the button gives way)."""
        fine = getattr(self.profile, "FINE", None)
        if fine is None:
            return None
        t = self.table
        key = (self._serials(), getattr(t, "rows_serial", 0), id(t.bindings),
               len(t.bindings))
        if key == self.__dict__.get("_fine_seen"):
            return self.__dict__.get("_fine_at")
        number, ch = fine
        at = None if fine_gives_way(self.bindings, number, ch) else (ch, number)
        self._fine_seen, self._fine_at = key, at
        return at

    def _fine_on(self) -> bool:
        p = self.reg.get(FINE_PARAM)
        return p is not None and bool(p.value)

    def _fine_press(self, ch: int, number: int, pressed: bool) -> None:
        """FINE pressed or let go: `desk.fine` follows the hand. `_held`
        keeps the press, so `fell_back` reads its release as Mode 2's."""
        p = self.reg.get(FINE_PARAM)
        if p is None:                   # an adapter from before a hot reload
            register_desk(self.reg, self.table)
            p = self.reg[FINE_PARAM]
        if pressed:
            self._held[(ch, number)] = []
            self._fine_held = (ch, number)
            p.set(True)
            self._log_press(self._source("note", ch, number),
                            f"fine: knobs move {FINE_DIV}× less while held", "both")
        else:
            self._held.pop((ch, number), None)
            self._fine_held = None
            p.set(False)
            self._fine_release()     # now: a coarse CC later in this batch must not jump

    def _fine_move(self, b: Binding, p: Param, u: float) -> None:
        """A knob's message while fine is on: the base moves by the knob's
        own move since its last message over FINE_DIV, between detents. A
        knob with no last position (never moved, never drawn) only takes
        this one as its position. Any glide on the param is dropped."""
        was, b.last_hw = b.last_hw, u
        if was is None:
            return
        d = u - was
        if d == 0.0:
            if u not in (0.0, 1.0):
                return
            # an end stop: the encoder sends its end again for each detent
            # turned against it — one MIDI step that way
            d = 1.0 / 127.0 if u == 1.0 else -1.0 / 127.0
        s = self._slew_state().pop(p.id, None)
        if s is not None and abs(p.norm - s.wrote) <= SLEW_TOL:
            p.set_norm(s.target)    # a glide in flight lands where the ring showed
        y = p.norm + d / FINE_DIV
        y = y % 1.0 if p.wrap else min(max(y, 0.0), 1.0)
        p.set(p._value_of_norm(y))
        self._note_written(p)
        self.__dict__.setdefault("_fine_moved", set()).add(b.control)

    def _follow_fine(self) -> None:
        """`desk.fine` turned off since the last poll by anything but the
        button (the panel, a learned row): the release `_fine_press` makes."""
        on = self._fine_on()
        was = self.__dict__.get("_fine_was", False)
        self._fine_was = on
        if was and not on:
            self._fine_release()

    def _fine_release(self) -> None:
        """Fine let go: each knob it moved loses its catch and has its ring
        re-sent. Until the ring goes out, a message the knob sent from
        where it had wandered is read as pickup and moves nothing; the
        ring re-bases the encoder onto the param (`_rebase` catches it
        there). Where rings do not re-base the catch stays let go: soft
        pickup, as the faders."""
        moved = self.__dict__.setdefault("_fine_moved", set())
        for b in self._own_rows():        # (a knob node mode fills is one too, row 609)
            if b.control in moved:
                b.last_out, b.caught = None, False
        moved.clear()

    def _fine_light(self) -> None:
        """FINE's LED: lit while fine is on, change-gated."""
        c = self._fine_control()
        if c is None:
            return
        v = 1 if self._fine_on() else 0
        if v != self.__dict__.get("_fine_out"):
            self._fine_out = v
            self._send(mido.Message("note_on", channel=c[0], note=c[1], velocity=v))

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
        The light is `led_shade`'s; a surface page's own shades (plan 31
        §A: a step under the playhead, a muted lane) take the profile's
        `shade_of` velocity. A playhead moving sends only what changed.
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
        for b in self._active():        # the up layer's rows and the invariant ones
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
                shade = led_shade(b, p)
                v = b.on if shade == "on" else b.off
                if shade == "held":
                    filled_of = getattr(self.profile, "filled_of", None)
                    filled = filled_of(b.number, b.on) if filled_of is not None else None
                    v = b.off if filled is None else filled
                elif shade not in ("on", "off"):     # a page's own (plan 31 §A)
                    shade_of = getattr(self.profile, "shade_of", None)
                    hit = shade_of(b.number, shade) if shade_of is not None else None
                    v = b.on if hit is None else hit
                if b.control in blinks:
                    v = blink_of(b.number, b.on) if blink_of is not None else b.on
                if v != b.last_out:
                    b.last_out = v
                    self._send(mido.Message(
                        "note_on", channel=b.channel or 0, note=b.number, velocity=v
                    ))
        self._fine_light()

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

    def redraw(self, *, load: bool = False, whole: bool = False,
               switch: bool = False) -> None:
        """Every ring and LED for the layer that is up (plan 13 §3.1): each
        control some row names, or feedback drew since the last redraw
        (`_shown` — a row since removed lit it: a loadable patch load's smaller
        desk, the ROUTING page's ×), goes dark unless an active row draws
        it (D8); then every active row is re-sent — a knob's ring re-bases
        it (`_rebase`). `load` (a desk replacement: a loadable patch load) also
        clears a fader's catch when its param is no longer where this
        adapter last put it — `_uncatch_moved`'s test — or it has no last
        write, or the param is not where this fader itself last was
        (`_writes` is per param: another control on the same param may
        have made the last write): a fader whose base the load moved
        picks up, and one whose param the load left alone (the
        crossfader, SM's dim, and the audio strip on S1–S8 under SHIFT: a
        loadable patch never moves a shared meta param, D9) keeps its hold (plan 15 WP3, fork 19). A load also ends
        every glide (knob smoothing) but a shared meta param's, before anything
        else: the load's value stands, even where it equals the glide's
        last write; a shared meta param the load never moves goes on arriving,
        and its fader is compared with where the glide is taking the param
        (the fader's own position), so it keeps its hold too.

        **Every load relights the whole desk** (plan 24 C1, decision 18;
        this changes register row 44): `load` — and `whole`, the power-up —
        also sends dark every control of the profile's layout that no
        active row draws, not only those a row has named (`_dark_desk`: a
        light another program left on goes out), and **every fader the new
        loadable patch binds** (a patch-layer row) lets go, moved or not, so each
        picks up from the new loadable patch the same way every time. A fresh row
        starts from where its control physically is (`_hw`), so a fader
        already on the value catches on its first move. The meta controller's
        faders (invariant or global: a loadable patch never moves their params,
        D9) keep the rule above.

        **A layer switch re-arms every layered fader** (`switch`; plan 24
        C2, D7): since the track faders carry the loadable patch's targets on one
        layer and the audio strip under SHIFT, one physical fader serves
        two params. Each layered fader row starts from where the fader
        physically is (`_hw`) and is caught only when its param is already
        there, so a fader moved on the other layer picks up its own param
        instead of jumping it. A load's rule above wins over this one."""
        if load:
            if getattr(self.profile, "RING_REBASES_KNOB", False):
                # every ring is re-sent below, re-basing each knob: nothing
                # left for a release to do. Where rings do not re-base the
                # knobs fine moved keep their place, so a release still
                # lets go of their catch (review of #344, round 2)
                self.__dict__["_fine_moved"] = set()
            slews = self._slew_state()
            for pid in [pid for pid in slews if not is_meta_id(pid)]:   # (a load moves none)
                del slews[pid]
        active = self._active()
        drawn = {b.control for b in active if b.feedback}
        hw = self.__dict__.setdefault("_hw", {})
        for b in self._page_rows():         # the surface page's rows: re-sent too
            b.last_out = None
        for b in self._own_rows():
            b.last_out = None
            if b.kind in ("cc", "pitch") and b.op == "abs" and b.last_hw is None:
                b.last_hw = hw.get(b.control)        # a fresh row: where its control is
            if (switch and b.layer is not None and b.kind in ("cc", "pitch")
                    and b.op == "abs" and b.feedback != "ring" and b.pickup):
                # where the fader is, moved on any layer — or None when no
                # position is known (never moved since power-up): then only
                # an on-value catch counts, never a crossing from a stale one
                p, pos = self.reg.get(b.target), hw.get(b.control)
                b.last_hw = pos
                b.caught = (p is not None and pos is not None
                            and abs(self._ring_norm(p) - pos) <= PICKUP_TOL)
            if load and b.kind in ("cc", "pitch") and b.op == "abs" and b.feedback != "ring":
                p, seen = self.reg.get(b.target), self._writes.get(b.target)
                if (b.layer == "preset" or p is None or seen is None or b.last_hw is None
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
        if load or whole:
            self._dark_desk(drawn, dark)
            if self._fine_control() is not None:
                self._fine_out = 0          # FINE has no row: `_dark_desk` just sent it dark
        self.feedback()

    def _dark_desk(self, drawn: set, dark: set) -> None:
        """Every control of the profile's layout (`apc40.LAYOUT`) that no
        active row draws, and that the redraw has not darkened already,
        goes dark: a button's LED off, a knob's ring off (plan 24 C1: a
        load relights the whole desk). A fader has no light; a profile
        with no layout darkens nothing more."""
        for c in getattr(self.profile, "LAYOUT", ()):
            kind = c.source.partition(":")[0]
            feedback = "led" if kind == "note" else "ring" if c.kind == "knob" else None
            if feedback is None:
                continue
            b = Binding(c.source, "", "toggle", feedback=feedback)
            if b.control not in drawn and b.control not in dark:
                dark.add(b.control)
                self._dark(b, velocity=0)

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
        register_desk(self.reg, self.table)
        self._fine_out = None
        for b in (*self._own_rows(), *self._page_rows()):
            b.last_out = None
