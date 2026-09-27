"""Routing — the one binding table every source drives the registry through.

Keys, the gamepad, a MIDI controller and the analyzer's lanes used to be
three tables and a special case: KEYMAP / PADMAP / HATMAP in app.py,
midi_map.json, and `planedrive` computed inside the chain. They are one
table now — a list of `Binding` rows, each "this source does this op to
this param" — persisted as one JSON file (`bindings.json`). app.py's
`Keys` / gamepad's `Pad` and midi.py's `MidiIO` are the *adapters*: they
poll hardware and look up the rows of their scheme. The analyzer is a
source like any other, read by the `Router` once per frame.

Sources are one string, ``scheme:address``:

  key:<NAME>       a GLFW key by constant name without KEY_ ("R", "F1",
                   "LEFT_BRACKET", "1")
  pad:<NAME>       a gamepad button by gamepad.py's name ("A", "LB", "LSTICK")
  hat:<DIR>        the d-pad: UP DOWN LEFT RIGHT
  cc:<ch>:<n>      MIDI control change n on 0-based channel ch, or * for any
  note:<ch>:<n>    MIDI note n
  pitch:<ch>       MIDI pitch bend
  lane:<i>         analyzer lane i — continuous, held every frame it is live
  ext:<i>          an external MIDI lane (WP4c); lfo:<i> is reserved
  hand:<i>         Ultraleap hand axis i's output in [0, 1] (hands.py),
                   then one presence lane per hand; NaN before that hand
                   was ever seen, and a NaN reading is not live

Ops — what a row does to its target. The first group is the *scene-
setters*: they write the param's base, the value a performer works from
and returns to. The last two are the *performer* ops:

  fire       fire a trigger
  toggle     flip a toggle, next enum choice, or fire a trigger
  step       move `value` detents (signed)
  set        set `value`: an enum choice, a toggle state, a fader's norm
  abs        an absolute MIDI control's position → set_norm (cc / pitch,
             with soft pickup); a trigger fires on the rising half. MIDI
             only: a continuous source never sets the base
  rel/rel64  a relative encoder's delta → step
  momentary  note-on sets a toggle on, note-off sets it off
  push       the performer adds to the base: every frame the source is
             live the row calls ``param.modulate(depth · scale · (u −
             rest))`` — `value` the signed depth in norm units, u the
             source's normalized reading, `rest` where the source sits
             idle (a lane 0, a centred hand axis or an LFO 0.5, so an
             idle source pushes nothing), and `scale` the live value of
             the param the row's `scale` names (an attenuator on the
             depth; 1 when it names none)
  position   the performer *is* the fader: while live the target sits at
             position ``depth · scale · u`` of its throw (clamped to
             [0, 1]), along its own taper and without detents; the base
             returns when the source stops. Depth 1 is the whole control
             whatever its units or curve — what a learned hand is

Both go through the same modulate(): position's offset is ``clamp(depth ·
scale · u) − base_norm``, so range, wrap and dormancy are push's. Rows to
unknown or unmodulatable params, or with an unknown scale param, are
dormant no-ops.

One performer per parameter — the model (plan 09)::

                       scene-setters (write the BASE, never prompt)
    panel · keys · pad buttons · APC40 · presets · mouse/stick (relative, on base)
                                   │
                                   ▼
   Param ─── base ──────────────────────────────▶ effective = base + offset
                                   ▲
                                   │  ONE route row, ONE per-frame path: Router.modulate
              performer ───────────┘
    lane:<i> · hand:<i> · ext:<i> · lfo:<i>      op = push | position
                                                  depth · scale (a param, e.g. macro.3)
                                                  rest (push only) · when (a gate)

   chaining:  hand:7 ──position──▶ lfo.1.depth      lfo:1 ──push──▶ view.bright
              lane:0 ──push──▶ macro.2              hand:1 ──position──▶ fx.mix  ×scale macro.2

A *performer* is an enabled row whose source is a continuous scheme
(LANE_SCHEMES) and whose op is in MOD_OPS. A target has at most one:
`Bindings.add` / `bind` raise `Owned` when another enabled performer
already has it (`Bindings.owner`), and the caller asks — the ROUTING
page's prompt, a hand learn held pending on the MIDI adapter — before
`replace_owner` swaps them. A preset or file with two rows on one target
keeps the first and lists the rest in `Bindings.dropped` until the next
edit. Disabled rows don't own. Layering is chaining, never stacking: a
hand owns an LFO's depth, the LFO owns brightness. Scene-setters never
prompt and are never blocked — an APC knob turned on a hand-owned param
moves the value the hand returns to.

Gating (`when`): any row may name a second *fed* source address — one an
adapter hands in with `feed` (hand, ext, lfo), which is where switch-like
lanes live; the analyzer's own lanes are not switches at all, so a row
gated on one stays shut. A gate has to read on (≥ 0.5) before the row
acts at all — a pinch switch over a hand axis, so the same movement means
one thing pinched and nothing open. A gated-off row stops modulating and
apply() writes the base back. A gate whose source is not live holds the
row shut, never open: nothing should start moving because a camera was
unplugged. Gates don't exempt a row from the referee: two rows on one
target with different pinches are still two performers.

Lane normalization: ``u = lane / CEIL`` — the analyzer's lanes are in
[0, CEIL) (bands.CEIL, the fader asymptote), so a lane at the asymptote
reads u = 1.0 and nominal (1.0) reads 1 / CEIL. u is not clamped; the
target param clamps to its own range in apply(). `master.gain` stays the
analyzer's output gain param; it reaches a route as a `scale`, which is
how the drive fader keeps its meaning on the rotation routes without
also scaling the pattern inputs the reference fed raw.

Frame order (app.py) is fixed: input adapters (keys, pad, MIDI) →
``hands.poll`` (feeds `hand`) → ``audio.step`` (the analyzer) → bridge
(feeds `ext`) → ``Router.modulate`` (every live performer row calls
modulate) → ``reg.apply()`` → ``integrate`` → ``draw``. A lane may
modulate the analyzer's own params: the offset lands in apply() and the
next step() reads it, one frame late, like every other modulated value.

Legacy 6 — the parity anchor. The reference drove the planes with
``PLANEDRIVE[plane] = dir · out[i] · DRIVE · gain`` in place of the
constant 1, and the shaders read ``u_bands[i] = out[i]``. As routes: lane
i → ``rot.rate.<plane>`` *push* with depth ``dir · ROT_DEPTH`` scaled by
``master.gain`` on a base of 0 (u = out / CEIL and ROT_DEPTH is the depth
that puts CEIL · DRIVE · 8 on the plane at the drive fader's 8×, so the
offset is ``dir · out · DRIVE · gain`` in rate units: a gated band stops
its plane at exactly 0.0); and lane i → ``pattern.mod.i`` *push* with
depth 1 on a base of 0. ``rot.rate`` spans ±ROT_RATE_MAX = ±(CEIL ·
DRIVE · 8) — the largest drive the reference could produce — so nothing
clamps at any gain, and the effective rate is the reference's number to
round-off *while the source is live* (a value passes through the
registry's normalized space and back: within an ulp of the range, the
same float32 the GPU sees; params.py says why the range is that wide).
`PRESETS["legacy6"]` carries the routes and the bases (`values`: zeros
for the rates and the pattern inputs — a push reproduces "audio replaces
the constant" only on 0). Where the reference spun at 1× the moment the
source stopped, the planes now stop: the base is 0 and the parity anchor
is the driven value, not the idle one (plan 09, inside the relaxed bar).
The factory table ships the same routes on WP0's bases of 1, so a plane
keeps its un-driven spin and a lane rides on top.

File format (``bindings.json``, schema ``hyperspace.bindings/2``):

  {"schema": "hyperspace.bindings/2", "profile": "apc40",
   "bindings": [{"source": "key:RIGHT", "target": "view.shape",
                 "op": "step", "value": 1},
                {"source": "lane:0", "target": "rot.rate.ZW", "op": "push",
                 "value": 0.0625, "scale": "master.gain"},
                {"source": "hand:7", "target": "view.bright", "op": "position",
                 "when": "hand:18"}, …],
   "values": {…}}            # optional: bases a routing preset assumes

Rows carry only what differs from the defaults. `Bindings.load` reads the
file, or builds the factory table when there is none — and if an old
``midi_map.json`` (midi.py's version-1 file) is present, its rows replace
the factory MIDI part and the merged table is written once, with a note.
A schema-1 file migrates the same way (`migrate_v1`: ``mod`` → push with
a rest by scheme, ``span`` → position, a lane-scheme ``abs`` → position at
depth 1, ``replace`` dropped, a second owner dropped — each dropped row
named on stderr, the file written back once). `bindings_path(home)` says
where the file lives; `home` defaults to the working directory so WP2's
library home can be dropped in.

Routing presets are the same file format with only modulation rows:
the factory exports in ``hyperspace/library/bindings/`` and the user's
``<home>/bindings/*.json`` (`preset_files`). `Router.load_preset` replaces
the routes from one and lands its bases; `Router.save_preset` writes the
current routes to the user folder — the ROUTING page's strip (WP5b).
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import numpy as np

from . import apc40
from .bands import BANDS, CEIL, DRIVE
from .params import PLANES, ROT_RATE_MAX, Kind, Param, Registry

SCHEMA = "hyperspace.bindings/2"
SCHEMA_V1 = "hyperspace.bindings/1"
FILE = "bindings.json"
LEGACY_MIDI_FILE = Path("midi_map.json")
FACTORY_DIR = Path(__file__).parent / "library" / "bindings"

MIDI_SCHEMES = ("cc", "note", "pitch")
INPUT_SCHEMES = ("key", "pad", "hat", *MIDI_SCHEMES)
LANE_SCHEMES = ("lane", "ext", "lfo", "hand")          # continuous, read by the Router
MOD_OPS = ("push", "position")                 # the performer ops: the Router's rows
OPS = ("fire", "toggle", "step", "set", "abs", "rel", "rel64", "momentary", *MOD_OPS)

# midi_map.json's `mode` → op
MODE_TO_OP = {"abs": "abs", "rel": "rel", "rel64": "rel64", "trigger": "toggle",
              "momentary": "momentary", "set": "set", "step": "step"}
# schema 1's performer ops → schema 2's (migrate_v1); `replace` has no twin
# but a push on a base of 0, which a file can't ask for, so it is dropped
V1_TO_OP = {"mod": "push", "span": "position", "abs": "position"}

# the legacy rate route: a push on a base of 0 lands the reference's
# drive — a lane at full drive (out = CEIL, gain 8) reaches rot.rate's end
# stop when depth · (CEIL · 8 / CEIL) · 2 · ROT_RATE_MAX = CEIL · DRIVE · 8
# →  depth = DRIVE · CEIL / (2 · ROT_RATE_MAX) = 1/16
ROT_DEPTH = DRIVE * CEIL / (2 * ROT_RATE_MAX)


class Owned(Exception):
    """The target already has a performer — `existing` is that row, `new`
    the one that asked. The caller decides: `Bindings.replace_owner(new)`
    or leave the table alone."""

    def __init__(self, existing: Binding, new: Binding | None = None):
        self.existing, self.new = existing, new
        super().__init__(f"{existing.target} is already performed by {existing.describe()}")


# ---------------------------------------------------------------- binding

@dataclass
class Binding:
    source: str                  # "scheme:address", see the module docstring
    target: str                  # param id
    op: str = "fire"
    value: float = 1.0           # set: the value · step: the detents · push/position: the depth
    enabled: bool = True
    scale: str | None = None     # push/position: a param whose value multiplies the depth
    # a source address ("hand:14") that must read on for this row to apply:
    # a pinch switch gating an axis, so the same hand move means two things
    when: str | None = None
    # push: where the source sits idle — the reading that pushes nothing
    # (Router.rests says what an adapter's lanes rest at)
    rest: float = 0.0
    # MIDI controls only (midi.py); other sources ignore them
    pickup: bool = True
    feedback: str | None = None  # "ring" | "led" | None
    on: int = 1                  # led velocity when lit
    off: int = 0                 # led velocity when dark
    ring: int = 2                # ring style for "ring" feedback (profile-defined)
    # runtime, never persisted
    caught: bool = field(default=False, repr=False, compare=False)
    last_hw: float | None = field(default=None, repr=False, compare=False)
    last_out: int | None = field(default=None, repr=False, compare=False)
    lit: bool = field(default=False, repr=False, compare=False)

    _RUNTIME = ("caught", "last_hw", "last_out", "lit")

    # ---- the source, taken apart ----

    @property
    def scheme(self) -> str:
        return self.source.split(":", 1)[0]

    @property
    def parts(self) -> list[str]:
        return self.source.split(":")[1:]

    @property
    def key(self) -> str:
        """What identifies the control: the source string."""
        return self.source

    @property
    def is_midi(self) -> bool:
        return self.scheme in MIDI_SCHEMES

    @property
    def kind(self) -> str | None:
        """MIDI: "cc" | "note" | "pitch"; None for any other source."""
        return self.scheme if self.is_midi else None

    @property
    def channel(self) -> int | None:
        """MIDI channel, 0-based; None matches any."""
        if not self.is_midi:
            return None
        ch = self.parts[0] if self.parts else "*"
        return None if ch == "*" else int(ch)

    @property
    def number(self) -> int:
        """MIDI cc number or note; 0 for pitch and for other sources."""
        if not self.is_midi or self.scheme == "pitch" or len(self.parts) < 2:
            return 0
        return int(self.parts[1])

    @property
    def index(self) -> int:
        """A lane-like source's index (lane:3 → 3); −1 when not numeric."""
        try:
            return int(self.parts[0])
        except (IndexError, ValueError):
            return -1

    @property
    def is_performer(self) -> bool:
        """An enabled push / position row from a continuous source — what
        owns a target. A disabled row keeps its settings and owns nothing."""
        return self.enabled and self.scheme in LANE_SCHEMES and self.op in MOD_OPS

    @staticmethod
    def midi_source(kind: str, channel: int | None, number: int = 0) -> str:
        ch = "*" if channel is None else str(int(channel))
        return f"pitch:{ch}" if kind == "pitch" else f"{kind}:{ch}:{int(number)}"

    def matches(self, kind: str, channel: int, number: int) -> bool:
        if self.kind != kind:
            return False
        if self.channel is not None and self.channel != channel:
            return False
        return kind == "pitch" or self.number == number

    # ---- files ----

    def to_json(self) -> dict:
        d = asdict(self)
        for k in self._RUNTIME:
            d.pop(k)
        # only what differs from the defaults keeps the file readable
        for k in ("value", "enabled", "scale", "when", "rest", "pickup", "feedback",
                  "on", "off", "ring"):
            if d[k] == self.__dataclass_fields__[k].default:
                d.pop(k)
        return d

    @classmethod
    def from_json(cls, d: dict) -> Binding:
        if "source" not in d and "kind" in d:        # midi_map.json version 1
            return cls.from_midi_v1(d)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_midi_v1(cls, d: dict) -> Binding:
        """A midi.py version-1 row: {param, kind, number, channel, mode, …}."""
        src = cls.midi_source(d["kind"], d.get("channel"), d.get("number", 0))
        b = cls(src, d["param"], MODE_TO_OP.get(d.get("mode", "abs"), "abs"))
        for f in ("value", "pickup", "feedback", "on", "off", "ring"):
            if f in d:
                setattr(b, f, d[f])
        return b

    def describe(self) -> str:
        s = self.scheme
        if self.is_midi:
            ch = "any ch" if self.channel is None else f"ch{self.channel + 1}"
            if s == "pitch":
                return f"MIDI pitch bend {ch}"
            what = "CC" if s == "cc" else "note"
            extra = "" if self.op in ("abs", "toggle") else f" {self.op}"
            return f"MIDI {what} {self.number} {ch}{extra}"
        addr = ":".join(self.parts)
        if s == "hat":
            return f"d-pad {addr}"
        if s in LANE_SCHEMES and self.op in MOD_OPS:
            by = f" × {self.scale}" if self.scale else ""
            gate = f" while {self.when}" if self.when else ""
            if self.op == "push":
                return f"{s} {addr} pushes {self.value:+.3g}{by}{gate}"
            depth = "" if self.value == 1.0 else f" {self.value:.3g}"
            return f"{s} {addr} positions{depth}{by}{gate}"
        return f"{s} {addr}"


# ------------------------------------------------------------------- ops

def act(reg: Registry, b: Binding) -> None:
    """A discrete row fires: keys, pad buttons and MIDI buttons share this."""
    p = reg.get(b.target)
    if p is None or not b.enabled:
        return
    op = b.op
    if op == "step":
        p.step(int(b.value))
    elif op == "toggle":
        p.cycle(1) if p.kind is Kind.ENUM else p.toggle()
    elif op == "fire":
        p.fire()
    elif op == "set":
        set_value(p, b.value)


def set_value(p: Param, value: float) -> None:
    """`set` by kind: a fader's norm, a toggle's state, an enum's choice."""
    if p.kind is Kind.CONTINUOUS:
        p.set_norm(float(value))
    elif p.kind is Kind.TOGGLE:
        p.set(bool(value))
    elif p.kind is Kind.ENUM:
        p.set(int(value))
    else:
        p.fire()


# --------------------------------------------------------------- the table

def bindings_path(home: Path | str | None = None) -> Path:
    """Where the table lives: <home>/bindings.json, home = the working
    directory unless told otherwise (WP2's library home goes here)."""
    return Path(home if home is not None else ".") / FILE


def keymap() -> list[Binding]:
    """The keyboard table app.py used to hold (ui.CHEATSHEET is the human list)."""
    rows = [
        ("RIGHT", "view.shape", "step", 1), ("LEFT", "view.shape", "step", -1),
        ("SPACE", "view.rotate", "toggle"), ("P", "view.points", "toggle"),
        ("L", "view.lines", "toggle"), ("F", "view.faces", "toggle"),
        ("H", "ui.panel", "toggle"), ("SLASH", "ui.cheatsheet", "toggle"),
        ("LEFT_BRACKET", "view.bright", "step", -3), ("RIGHT_BRACKET", "view.bright", "step", 3),
        ("COMMA", "view.speed", "step", -4), ("PERIOD", "view.speed", "step", 4),
        ("M", "audio.mic", "toggle"), ("K", "audio.play", "toggle"),
        ("0", "audio.restart", "fire"),
        ("T", "overlay.on", "toggle"), ("G", "overlay.passthrough", "toggle"),
        *[(str(p + 1), f"view.plane.{n}", "toggle") for p, n in enumerate(PLANES)],
    ]
    return [Binding(f"key:{k}", pid, op, *arg) for k, pid, op, *arg in rows]


def padmap() -> list[Binding]:
    """Xbox-layout gamepad buttons and the d-pad."""
    rows = [
        ("pad:A", "view.rotate", "toggle"), ("pad:B", "theme.next", "fire"),
        ("pad:X", "view.points", "toggle"), ("pad:Y", "view.faces", "toggle"),
        ("pad:LB", "view.shape", "step", -1), ("pad:RB", "view.shape", "step", 1),
        ("pad:VIEW", "ui.panel", "toggle"), ("pad:MENU", "ui.cheatsheet", "toggle"),
        ("pad:LSTICK", "camera.reset", "fire"), ("pad:RSTICK", "camera.reset", "fire"),
        ("hat:UP", "view.bright", "step", 3), ("hat:DOWN", "view.bright", "step", -3),
        ("hat:LEFT", "view.speed", "step", -4), ("hat:RIGHT", "view.speed", "step", 4),
    ]
    return [Binding(src, pid, op, *arg) for src, pid, op, *arg in rows]


def legacy6_routes() -> list[Binding]:
    """The reference's band → plane table and shader inputs, as routes.

    The rate rows push dir · ROT_DEPTH · gain · u with u = out / CEIL, which
    on a base of 0 is dir · out · DRIVE · gain on the plane in rate units.
    The pattern rows push u on their base, 1 : 1 with out on a base of 0.
    """
    rows = [Binding(f"lane:{i}", f"rot.rate.{b.pl}", "push", b.dir * ROT_DEPTH,
                    scale="master.gain") for i, b in enumerate(BANDS)]
    rows += [Binding(f"lane:{i}", f"pattern.mod.{i}", "push", 1.0) for i in range(len(BANDS))]
    return rows


def legacy6_values() -> dict[str, float]:
    """The bases the legacy6 routes assume: a push lands the reference's
    number only from 0."""
    return {**{f"rot.rate.{n}": 0.0 for n in PLANES},
            **{f"pattern.mod.{i}": 0.0 for i in range(len(BANDS))}}


# routing presets: {name: (routes, values)} — `values` are the bases the
# routes assume; None leaves the user's settings alone
PRESETS: dict[str, tuple[list[Binding], dict | None]] = {
    "legacy6": (legacy6_routes(), legacy6_values()),
}


def referee(rows: Iterable[Binding]) -> tuple[list[Binding], list[tuple[Binding, str]]]:
    """First performer per target wins: (kept, [(dropped row, why)]).

    What a preset or a file gets instead of a prompt — the loader asks
    nothing, so the rule is fixed: table order decides.
    """
    kept: list[Binding] = []
    dropped: list[tuple[Binding, str]] = []
    owners: dict[str, Binding] = {}
    for b in rows:
        if b.is_performer:
            cur = owners.get(b.target)
            if cur is not None:
                dropped.append((b, f"{b.target} is already performed by {cur.describe()}"))
                continue
            owners[b.target] = b
        kept.append(b)
    return kept, dropped


def default_rest(source: str) -> float:
    """Where a source of schema 1's `mod` rows rests, for the migration —
    the table is fixed, the loader asks nothing: an LFO and a centred hand
    axis (the default dofs' bipolar ones) at 0.5, everything else at 0."""
    scheme, _, addr = source.partition(":")
    if scheme == "lfo":
        return 0.5
    if scheme == "hand":
        from .hands.core import BIPOLAR, DEFAULT_DOFS  # the default layout, nothing live

        try:
            i = int(addr)
        except ValueError:
            return 0.0
        if 0 <= i < 2 * len(DEFAULT_DOFS) and DEFAULT_DOFS[i % len(DEFAULT_DOFS)] in BIPOLAR:
            return 0.5
    return 0.0


def migrate_v1(rows: Iterable[Binding]) -> tuple[list[Binding], list[str]]:
    """Schema 1 → 2: the performer ops renamed, `replace` dropped. Returns
    (rows, a note per dropped row); `referee` then settles second owners."""
    out: list[Binding] = []
    notes: list[str] = []
    for b in rows:
        if b.scheme not in LANE_SCHEMES:
            out.append(b)
            continue
        op = V1_TO_OP.get(b.op)
        if op is None:
            notes.append(f"dropped {b.source} → {b.target} ({b.op}): no such op — "
                         "a push on a base of 0 is the additive twin")
            continue
        if b.op == "mod":
            b.rest = default_rest(b.source)
        elif b.op == "abs":          # a learned hand: the whole throw, no pickup
            b.value, b.pickup = 1.0, True
        b.op = op
        out.append(b)
    return out, notes


# routing preset *files*: the factory exports (write_factory) and the
# user's <home>/bindings/*.json — what the ROUTING page's strip steps
# through. A user file shadows a factory one of the same name.
PRESET_DIR = "bindings"


def preset_files(home: Path | str | None = None) -> dict[str, Path]:
    """name → path of every routing preset file, user over factory."""
    out: dict[str, Path] = {}
    dirs = [FACTORY_DIR] + ([Path(home) / PRESET_DIR] if home is not None else [])
    for d in dirs:
        if d.is_dir():
            out.update((p.name[:-5], p) for p in sorted(d.glob("*.json")))
    return out


def preset_names(home: Path | str | None = None) -> list[str]:
    return sorted(preset_files(home), key=str.lower)


def is_factory_preset(name: str, home: Path | str | None = None) -> bool:
    p = preset_files(home).get(name)
    return p is not None and FACTORY_DIR in p.parents


def legacy_planedrive(lanes, gain: float = 1.0) -> np.ndarray:
    """The reference's PLANEDRIVE from six lanes — what the legacy6 routes
    must land on rot.rate.*; offline.py's per-frame `drive` history."""
    drive = np.ones(6)
    for i, b in enumerate(BANDS[: len(lanes)]):
        drive[b.plane] = b.dir * lanes[i] * DRIVE * gain
    return drive


class Bindings:
    """The whole table: rows of every scheme, one file, indexed for the adapters."""

    def __init__(self, bindings: Iterable[Binding] = (), *, path: Path | None = None,
                 profile: str = "apc40", values: dict | None = None):
        self.bindings: list[Binding] = list(bindings)
        self.path = path
        self.profile = profile
        self.values = values
        self.error = ""
        # what the referee refused from the last preset or file, (row, why),
        # for the ROUTING page to show until the next edit
        self.dropped: list[tuple[Binding, str]] = []
        # from_json read a schema-1 file: `notes` names every row it dropped
        # (Bindings.load prints them), so the machine's file can be checked
        self.migrated = False
        self.notes: list[str] = []

    # ---- construction ----

    @classmethod
    def factory(cls, profile: str = "apc40", path: Path | None = None) -> Bindings:
        """Keys, pad, the device profile's default MIDI map, the legacy6 routes."""
        midi = [Binding.from_json(b) for b in apc40.DEFAULT_MAP] if profile == "apc40" else []
        return cls([*keymap(), *padmap(), *midi, *legacy6_routes()], path=path,
                   profile=profile)

    @classmethod
    def load(cls, path: Path | None, profile: str = "apc40",
             legacy_midi: Path | None = LEGACY_MIDI_FILE) -> Bindings:
        """The file at `path`, else the factory table — with an old
        midi_map.json's rows in place of the factory MIDI part, written once.
        A schema-1 file is migrated the same way: noted on stderr, written
        back once, and from then on the file rules."""
        if path is not None and path.exists():
            try:
                t = cls.from_json(json.loads(path.read_text()), path=path)
                t.profile = t.profile or profile
            except (OSError, ValueError, TypeError, KeyError) as e:
                t = cls.factory(profile, path)
                t.error = f"bindings: {e}"
                return t
            if t.migrated:
                for note in t.notes:
                    print(f"bindings: {path}: {note}", file=sys.stderr)
                print(f"bindings: migrated {path} to {SCHEMA}"
                      + (f" ({len(t.notes)} rows dropped)" if t.notes else ""),
                      file=sys.stderr)
                t.write()
            return t
        t = cls.factory(profile, path)
        if legacy_midi is not None and legacy_midi.exists():
            try:
                data = json.loads(legacy_midi.read_text())
                rows = [Binding.from_json(b) for b in data.get("bindings", [])]
                t.profile = data.get("profile", profile)
                t.bindings = [b for b in t.bindings if not b.is_midi] + rows
                print(f"bindings: migrated {len(rows)} rows from {legacy_midi}"
                      + (f" into {path}" if path is not None else ""), file=sys.stderr)
                t.write()
            except (OSError, ValueError, TypeError, KeyError) as e:
                t.error = f"bindings: {legacy_midi}: {e}"
        return t

    @classmethod
    def from_json(cls, data: dict, path: Path | None = None) -> Bindings:
        """A file's dict. Schema 1 (or none) goes through `migrate_v1`; a
        schema-2 file with two owners on a target keeps the first, the rest
        in `dropped` — the referee, not a prompt, since nobody is asking."""
        rows = [Binding.from_json(b) for b in data.get("bindings", [])]
        notes: list[str] = []
        migrated = data.get("schema") != SCHEMA
        if migrated:
            rows, notes = migrate_v1(rows)
        t = cls(rows, path=path, profile=data.get("profile", "apc40"),
                values=data.get("values"))
        t.bindings, t.dropped = referee(t.bindings)
        if migrated:
            notes += [f"dropped {b.source} → {b.target}: {why}" for b, why in t.dropped]
        t.migrated, t.notes = migrated, notes
        return t

    def to_json(self) -> dict:
        d = {"schema": SCHEMA, "profile": self.profile,
             "bindings": [b.to_json() for b in self.bindings]}
        if self.values is not None:
            d["values"] = dict(self.values)
        return d

    def dumps(self) -> str:
        """The file text: one row per line, so a diff reads as a binding."""
        d = self.to_json()
        rows = ",\n".join("  " + json.dumps(b) for b in d["bindings"])
        text = (f'{{\n "schema": {json.dumps(d["schema"])},\n'
                f' "profile": {json.dumps(d["profile"])},\n "bindings": [\n{rows}\n ]')
        if "values" in d:
            text += f',\n "values": {json.dumps(d["values"], indent=2)}'
        return text + "\n}\n"

    def write(self) -> None:
        if self.path is None:
            return
        try:
            self.path.write_text(self.dumps())
            self.error = ""
        except OSError as e:
            self.error = f"bindings: {e}"

    # ---- queries ----

    def of(self, *schemes: str) -> list[Binding]:
        return [b for b in self.bindings if b.scheme in schemes]

    def midi(self) -> list[Binding]:
        return self.of(*MIDI_SCHEMES)

    def mods(self) -> list[Binding]:
        """The enabled performer rows, in table order — the Router's pass."""
        return [b for b in self.bindings if b.op in MOD_OPS and b.enabled]

    def routes(self) -> list[Binding]:
        """Every performer row, disabled ones too — what the matrix lists
        and a routing preset saves."""
        return [b for b in self.bindings if b.op in MOD_OPS]

    def performers(self) -> list[Binding]:
        """The rows that own a target: enabled, a continuous source, push
        or position (`Binding.is_performer`)."""
        return [b for b in self.bindings if b.is_performer]

    def owner(self, pid: str) -> Binding | None:
        """The one performer on `pid`, or None — the referee's question."""
        return next((b for b in self.bindings if b.is_performer and b.target == pid), None)

    def route(self, kind: str, channel: int, number: int) -> list[Binding]:
        return [b for b in self.bindings if b.matches(kind, channel, number)]

    def for_param(self, pid: str, schemes: tuple[str, ...] = MIDI_SCHEMES) -> Binding | None:
        return next((b for b in self.bindings if b.target == pid and b.scheme in schemes), None)

    def routes_to(self, pid: str) -> list[Binding]:
        return [b for b in self.bindings if b.op in MOD_OPS and b.target == pid]

    # ---- edits ----

    def _check(self, b: Binding) -> None:
        """The referee: a performer joining the table (or waking up) must
        find its target free, or held by itself. A continuous source has
        no other op — `abs` is MIDI's, the one path is Router.modulate."""
        if b.scheme in LANE_SCHEMES and b.op not in MOD_OPS:
            raise ValueError(f"{b.op!r} is not an op for a {b.scheme} source; "
                             f"one of {', '.join(MOD_OPS)}")
        if not b.is_performer:
            return
        cur = next((x for x in self.bindings
                    if x is not b and x.is_performer and x.target == b.target), None)
        if cur is not None:
            raise Owned(cur, b)

    def bind(self, b: Binding) -> None:
        """A control drives one param; a param keeps one control per role.

        Drops whatever the key drove before, and the param's previous
        binding in the same role: a knob (any cc or pitch binding) when
        learning a knob, or a button of the same op and value when
        learning a button — so a param's step buttons survive a knob learn.
        A continuous source's row (a hand learn) is a performer like any
        route: `add`, then written — `Owned` if the target is taken.
        """
        if not b.is_midi:
            self.add(b)
            self.write()
            return

        def same_role(x: Binding) -> bool:
            if x.target != b.target or not x.is_midi:
                return False
            if b.scheme == "note":
                return x.scheme == "note" and x.op == b.op and x.value == b.value
            return x.scheme in ("cc", "pitch")

        self.bindings = [x for x in self.bindings if x.key != b.key and not same_role(x)]
        self.bindings.append(b)
        self.dropped = []
        self.write()

    def unbind(self, pid: str, schemes: tuple[str, ...] = MIDI_SCHEMES) -> None:
        self.bindings = [b for b in self.bindings
                         if not (b.target == pid and b.scheme in schemes)]
        self.dropped = []
        self.write()

    def add(self, b: Binding) -> Binding:
        """A route (or any row) added at runtime — the routing matrix's
        edit. Raises `Owned` when the target has another performer."""
        self._check(b)
        self.bindings.append(b)
        self.dropped = []
        return b

    def replace_owner(self, new: Binding) -> Binding | None:
        """The prompt's *Replace*: the target's performer goes, `new` comes
        in. Returns the row removed (None when the target was free)."""
        cur = self.owner(new.target)
        if cur is new:
            return None
        if cur is not None:
            self.remove(cur)
        if not any(x is new for x in self.bindings):
            self.add(new)
        return cur

    def enable(self, b: Binding, on: bool = True) -> None:
        """A row's checkbox. Waking a row is joining the table as far as
        the referee is concerned — `Owned` if its target was taken while
        it slept; the row stays off."""
        if on and not b.enabled:
            b.enabled = True
            try:
                self._check(b)
            except Owned:
                b.enabled = False
                raise
        b.enabled = on
        self.dropped = []

    def remove(self, b: Binding) -> None:
        self.bindings = [x for x in self.bindings if x is not b]
        self.dropped = []

    def set_routes(self, routes: Iterable[Binding]) -> None:
        """Replace every performer row, keeping the input bindings. Two
        rows on one target: the first stays, the rest go to `dropped`."""
        kept, self.dropped = referee(routes)
        self.bindings = [b for b in self.bindings if b.op not in MOD_OPS] + kept


# ---------------------------------------------------------------- router

class Router:
    """The adapters' lookup and the per-frame modulation pass over one table."""

    def __init__(self, reg: Registry, table: Bindings):
        self.reg = reg
        self.table = table
        self.feeds: dict[str, np.ndarray | None] = {}   # ext/lfo/hand vectors, per frame
        self.labels: dict[str, list[str]] = {}          # scheme → lane names, from the adapter
        # scheme → the lanes an adapter offers as gates, [(index, label)]:
        # switch-like lanes a row's `when` can wait on. The adapter says
        # which of its lanes those are; nothing here knows about hands.
        self.gates: dict[str, list[tuple[int, str]]] = {}
        # scheme → where each lane sits idle, published like `labels`: what
        # a new push row's `rest` defaults to (a centred hand axis 0.5, a
        # presence lane 0, an LFO 0.5); the analyzer's lanes rest at 0
        self.rests: dict[str, list[float]] = {}
        self._codes: dict[str, int | None] = {}

    # ---- discrete adapters ----

    def keys(self, keys) -> None:
        """One frame of keyboard rows; `keys` is anything with pressed(glfw_key)."""
        for b in self.table.of("key"):
            code = self._code(b)
            if code is not None and keys.pressed(code):
                act(self.reg, b)

    def pad(self, pad) -> None:
        """One frame of pad / hat rows; `pad` is a gamepad.Pad."""
        for b in self.table.of("pad", "hat"):
            code = self._code(b)
            if code is None:
                continue
            if (pad.hat_pressed(code) if b.scheme == "hat" else pad.pressed(code)):
                act(self.reg, b)

    def _code(self, b: Binding) -> int | None:
        """The key / button / hat constant a source names; None if there is none."""
        src = b.source
        if src not in self._codes:
            self._codes[src] = _resolve(b.scheme, ":".join(b.parts))
        return self._codes[src]

    # ---- continuous sources ----

    def feed(self, scheme: str, values) -> None:
        """An adapter hands in this frame's vector for `ext` / `lfo` sources
        (None: not live, its rows let go)."""
        self.feeds[scheme] = None if values is None else np.asarray(values, dtype=float)

    def gated(self, b: Binding) -> bool:
        """Is this row allowed to act this frame?

        A row with no `when` always is. One with `when` waits on that
        source address reading on (≥ 0.5) — a pinch switch, say, so the
        same hand movement can mean two different things. A gate whose
        source is not live holds the row shut rather than open: nothing
        should start moving because a camera was unplugged. Only fed
        sources gate — the analyzer's lanes are not switches and are not
        in `feeds`, so a row gated on one stays shut in both passes
        rather than working in one and not the other.
        """
        if b.when is None:
            return True
        scheme, _, addr = b.when.partition(":")
        vec = self.feeds.get(scheme)
        if vec is None:
            return False
        try:
            i = int(addr)
        except ValueError:
            return False
        if not 0 <= i < len(vec):
            return False
        u = float(vec[i])
        return not math.isnan(u) and u >= 0.5

    def rest_of(self, source: str) -> float:
        """Where `source` rests, from its adapter's `rests` — 0 when the
        adapter published none (the analyzer's lanes, an unknown address)."""
        scheme, _, addr = source.partition(":")
        rests = self.rests.get(scheme) or []
        try:
            i = int(addr)
        except ValueError:
            return 0.0
        return float(rests[i]) if 0 <= i < len(rests) else 0.0

    def modulate(self, analyzer=None) -> None:
        """The frame's modulation pass — the one path a continuous source
        has to a param: every enabled performer row whose source is live
        calls modulate on its target. `analyzer` is the live one, or None
        while no audio source runs (its lanes are then not a source)."""
        lanes = None if analyzer is None else analyzer.lanes / CEIL
        for b in self.table.mods():
            vec = lanes if b.scheme == "lane" else self.feeds.get(b.scheme)
            i = b.index
            if vec is None or not 0 <= i < len(vec):
                continue
            u = float(vec[i])
            if math.isnan(u):    # this lane's source is out of view
                continue
            if not self.gated(b):
                continue         # gate open: apply() writes the base back
            p = self.reg.get(b.target)
            if p is None:
                continue
            depth = b.value
            if b.scale is not None:
                sp = self.reg.get(b.scale)
                if sp is None:
                    continue
                depth *= float(sp.value)
            if b.op == "push":
                # centred where the source rests: an idle source adds nothing
                x = depth * (u - b.rest)
            else:
                # position: the source is the fader — the offset that lands
                # it (p.norm is the base while modulated, the object before)
                if p.kind is Kind.TEXT or not p.modulatable:
                    continue
                x = min(1.0, max(0.0, depth * u)) - p.norm
            p.modulate(x)

    # ---- presets ----

    def apply_preset(self, name: str) -> list[str]:
        """Replace the routes with a preset's; land its bases. Returns the
        ids the registry doesn't have. Two rows on one target: the first
        stays, the rest wait in `table.dropped` for the page to show."""
        routes, values = PRESETS[name]
        self.table.set_routes(replace(b) for b in routes)
        return self.reg.restore(values) if values else []

    def load_preset(self, name: str, home: Path | str | None = None) -> list[str]:
        """`apply_preset` over the files: a routing preset by name from the
        factory folder or the user's <home>/bindings/ (preset_files). Only
        its performer rows come in — a full table (default.json) works as
        a preset too. A missing name raises FileNotFoundError, a bad file
        ValueError, so the strip can show it."""
        path = preset_files(home).get(name)
        if path is None:
            raise FileNotFoundError(f"no routing preset {name!r}")
        t = Bindings.from_json(json.loads(path.read_text()))
        self.table.set_routes(replace(b) for b in t.bindings if b.op in MOD_OPS)
        self.table.dropped = t.dropped + self.table.dropped
        return self.reg.restore(t.values) if t.values else []

    def save_preset(self, name: str, home: Path | str) -> Path:
        """The current routes — disabled ones too, no bases — as a user
        preset file under <home>/bindings/; returns the path written."""
        from .library import slug  # the library's file naming; no other tie

        d = Path(home) / PRESET_DIR
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{slug(name)}.json"
        path.write_text(Bindings(replace(b) for b in self.table.routes()).dumps())
        return path


def _resolve(scheme: str, name: str) -> int | None:
    """key:NAME → glfw.KEY_NAME; pad:NAME → gamepad.NAME; hat:DIR → gamepad.HAT_DIR.
    Imported here so the table itself never needs a window system."""
    try:
        if scheme == "key":
            import glfw
            return getattr(glfw, f"KEY_{name}")
        from . import gamepad
        return getattr(gamepad, f"HAT_{name}" if scheme == "hat" else name)
    except (ImportError, AttributeError):
        return None


# --------------------------------------------------------------- factory files

def write_factory(directory: Path = FACTORY_DIR) -> list[Path]:
    """Export the factory table and every routing preset as library files
    (`python -m hyperspace.routing`); test_routing guards them against drift."""
    directory.mkdir(parents=True, exist_ok=True)
    out = [directory / "default.json"]
    out[0].write_text(Bindings.factory().dumps())
    for name, (routes, values) in PRESETS.items():
        p = directory / f"{name}.json"
        p.write_text(Bindings(routes, values=values).dumps())
        out.append(p)
    return out


if __name__ == "__main__":
    for path in write_factory():
        print(path)
