"""The parameter registry — one address space for everything the surface can set.

Every control the panel draws, every hotkey, every gamepad button and every
MIDI binding resolves to a Param here, by a stable string id
(``view.bright``, ``band.2.atk``, ``preset.load.0``). The registry is the
core's own contract (BLUEPRINT §3.6 inbound: "addressed by the same
parameter registry the UI uses"), so nothing in it may import from an
adapter — midi.py depends on this module, never the other way round.

Five kinds, one normalized interface:

  CONTINUOUS  value in a range; exposes norm ∈ [0, 1] both ways. Tapered
              params (tapers.Taper) quantize to the taper's integer throw so
              a fader position and a MIDI value agree on what the value is;
              untapered ones get a plain (or log) range.
  ENUM        an index into a list of choice names.
  TOGGLE      a bool.
  TRIGGER     an action; fire() and nothing else.
  TEXT        a string (a file path). Loadable patches save it; every numeric
              surface ignores it — no norm, no step, no modulation.

``step(n)`` moves any non-trigger param by n detents — taper positions, a
hundredth of an untapered range, one choice, or a flip — which is what
keys, d-pads and relative encoders all want.

Values are read live through getters, never cached, so a param stays true
after a hot reload or after the chain object is recreated on a source
attach (getters go through ``audio.chain``, not a captured chain).

Two flags say what a param is *for*: ``persist`` (it belongs in a
snapshot — a loadable patch's values when its group is performance, a project's
meta controller part when it is meta controller, `part_of`; off for transient UI state,
transport and triggers) and ``modulatable``
(a continuous source such as an audio lane may drive it — off for things
like which screen the output is on). An ``alias`` (band.sel.*) is neither.

Modulation — the one control concept every source shares — lives here.
Sources (an audio band, an LFO, a hand axis, a MIDI lane) never touch a
param directly: each adapter hands its lane values to ``router.feed`` and
``Router.modulate`` (routing.py) is the one caller of ``modulate(u)``, once
per frame per live row, with an offset in the param's normalized space.
Once per frame ``Registry.apply()`` then writes
``effective = base + Σ offsets`` into the live object. The *base* is what
the user set and what loadable patches save; the object holds the effective value
the renderer reads. Base is adopted from the object the first time a
param is modulated; the param-level setters (set / set_norm / step…)
write the base while it is modulated; a direct write to the object by
other code shifts the base by the same delta (so the rotation integrator
keeps adding to ``ang`` while a lane adds a phase offset on top); and when
the last source lets go the base is written back. Continuous params are
mapped as floats — no detents — so a lane never zippers; enum and toggle
targets move with hysteresis so a noisy lane cannot flap them; a trigger
fires on a rising edge.

The base chase (plan 52) is the one way a performer reaches a base: while
`Registry.base_chase` is on, each landing also writes what the param shows
into its base. `_trim` is the ledger that keeps that from counting twice:
how much of the pushes' offset the base already holds. The offset rides on
top less the trim, and once the verb is let go the trim only falls, with the
offset on its way home (`_came_home`), so the look stays where the performer
left it. A source flickering out leaves it, since the offset coming back is
the one the base holds. A base replaced replaces it too: a load's holds no
commit, and an undo's holds what it held then (`Registry.restore`). The table
is not touched: a route's depth is the depth it was.
"""

from __future__ import annotations

import copy
import math
import re
import warnings
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from . import fx, groupwords, patterns, tapers, undo
from .analyzer import CURVES, F_HI, F_LO, Q_HI, Q_LO
from .bands import CEIL, NORMS, SHAPERS
from .fx import FxState
from .fx import declare as declare_fx
from .geometry import EYE_DISTANCE, EYE_FOV, PLANE_NAMES, SHAPES, pan_px_to_world
from .ghost import GhostState
from .ghost import register as declare_ghost
from .lookback import (
    FADE_HI,
    FADE_LO,
    GAP_HI,
    GAP_LO,
    LAYERS,
    LOOKBACK_KEYS,
    MAX_ECHOES,
    OCTAVES,
    RES,
    TINT_FROM,
    DreamState,
    is_lookback_key,
)
from .media import channels as media_channels
from .media.transport import LOOPS as MEDIA_LOOPS
from .tapers import Taper
from .tapers import clamp as _clamp
from .view import (
    MATTE_FEATHER,
    MATTE_FROM,
    RESIZE_ASPECTS,
    RESIZE_FILTERS,
    RESIZE_FITS,
    RESIZE_SIDES,
    SEGMENT_FEATHER,
    SEGMENT_LEARN,
    SEGMENT_MODES,
    SEGMENT_QUALITY,
    CutState,
    MatteState,
    ResizeState,
    SegmentState,
)

PATTERNS = patterns.NAMES   # the face patterns, in patterns.glsl's mode order
# field.py's layouts, in its order: three flat, then the six 3D lattices
INST_LAYOUT = ["GRID", "HEX", "RING", "CUBIC", "BCC", "FCC", "HCP", "HEX PRISM", "DIAMOND"]
INST_MOTION = ["STILL", "ORBIT", "WAVE", "RIPPLE"]
MEDIA_PATHS = ["STILL", "ORBIT", "FIG-8", "SWAY"]   # the faces' media path (view.media_mode)
BMP_ALPHA = "view.bmp_alpha"   # the one bitmap id kept: an alias of view.media_alpha
PLANES = PLANE_NAMES   # the rotation planes' names, in geometry.PLANES's order

RAW_STEPS = 100  # detents across an untapered continuous range
N_MACROS = 8     # macro.1–8: knobs that act through their subscribers and may be owned
# the bank slots a function key reaches (F1–F8): each has a `preset.load.k`
# and a `preset.save.k` trigger. The bank itself is longer (library.SLOTS);
# `library.F_KEYS` and `routing.F_KEYS` are this number
F_KEYS = 8
# the patch / meta controller split (plan 13 §4, D9), by group, declared
# once. Performance is what a loadable patch (loadable.py) holds and
# replaces: the look, its LFOs and its macros. The meta controller is everything and the
# room (the clock, the hands' feel, the analyzer and its source, the
# output, the UI, the desk's own feel: `desk.slew`, routing.register_desk),
# which a loadable patch never moves, so a tapped BPM or the band
# scene survives a loadable patch load. Every persisted param is in exactly one
# (tests/test_params.py walks the full registry); a group in neither
# (`preset`, the bank) has no persisted params, and `rot.phase.*` is `persist=False`.
# `mod` (plan 28 N1): the modifier nodes' params, `mod.<n>.<p>` — the
# loadable patch's, declared while it holds the modifier (routing.declare_modifiers)
# `env` and `seq` (plan 31): the envelopes' knobs and the sequencer's
# pattern are the look's, like the LFOs' (decision 8: the pattern is the
# loadable patch's, `seq.run` and the playhead are not persisted at all)
# `switch` (plan 33 S): each switch node's `select`, the loadable patch's, declared
# while its graph holds the switch (declare_switches)
# `resize` (plan 34 Z): each resize node's size, aspect, fit, filter and
# crop, the loadable patch's, declared while its graph holds the entry (declare_resizes)
# `matte` (plan 39 T2): each matte node's source, key, edge and feather, the
# loadable patch's, declared while its graph holds the entry (declare_mattes)
# `cut` (plan 39 T3): each cut node's invert and amount, the loadable patch's,
# declared while its graph holds the entry (declare_cuts)
# `segment` (plan 39 T4): each segment node's mode, level, feather, smooth,
# switch and motion's sense and learn, the loadable patch's, declared while its
# graph holds the entry (declare_segments)
# `eye` (plan 43 C2, the owner, 2026-11-02, row 555): the one orbit camera is
# the look's — `camera.*` (the shape's pose and scale in the world) and
# `eye.*` (the fixed eye the world is seen through) are one camera in the
# loadable patch. The ids keep their group (`eye.fov`, a saved id, is a format):
# the merge is the group's move from the meta controller, not a rename
# `ghost` and `cloud` (plan 43 §6 item 1, plan 44 D3, schema `/10`): the
# hands' look and the point clouds' look are the look's — a loadable patch carries
# them, a load lands them — but for the one setting each hands node keeps
# for the room (`SHARED_META_KEYS`: `ghost.mirror`, a real mirror in front of
# the performer's hands; the owner's answer of 2026-11-02, kept 2026-11-03)
# `pad` (plan 28, rows 729-730): how each stick reads as a dial, petal or blend
# (`pad.dial.left` / `.right`, `declare_dial`): the loadable patch's, since a reading
# changes what its own `axis:L.*` / `axis:R.*` routes do. The pad's feel (`desk.pad.*`)
# is about the hardware, and stays the meta controller's
PATCH_GROUPS = ("view", "rot", "camera", "eye", "pattern", "dream", "fx", "media",
                      "backdrop", "switch", "resize", "matte", "cut", "segment", "ghost",
                      "cloud", "lfo", "env", "seq", "macro", "pad", "mod")
SHARED_META_GROUPS = ("tempo", "hands", "band", "master", "scene", "audio", "output",
                  "overlay", "ui", "desk", "playlist")
# plan 44 D3 (row 612): the shared meta params inside a patch group, by
# group → the last segment of their ids — `ghost.mirror`. They keep their group
# (the HANDS page lists the group; an id is a saved format) and are the meta
# controller's single copy: `part_of` asks here first, so a loadable patch never names
# one and the show keeps it. `ghost.2.mirror` is no param since LY1 (a hands node's
# state follows `ghost.mirror`); an old show may hold the id, which stays classed here
# so no look ever takes it, until the old reader goes (CL1)
SHARED_META_KEYS: dict[str, tuple[str, ...]] = {"ghost": ("mirror",)}
# review of #371: the shared meta params whose group is not their id's first segment
# (`edit.undo`, `app.restart`: group `ui`; `seq.page`: group `desk`). The app's
# verbs and the desk's page latch: no part of a look. Asked first by `part_of_id`,
# so a table with no registry (`routing.meta_refusal`) and `part_of` cannot
# disagree (tests/test_meta_rule.py walks the registry)
SHARED_META_IDS = ("app.restart", "edit.undo", "edit.redo", "seq.page", "seq.select")
# plan 43 C2 (row 573): the spin's pose — where each plane is in its turn,
# `view.body` folded in (`ViewState.pose`) — saved by every loadable patch under
# these ids (its `pose` section, loadable.POSE_KEY, beside `values`) and set
# by its load. The params stay `persist=False`: the turn moves every frame,
# so it is no base, no undo step and no dirty dot
POSE_IDS = tuple(f"rot.phase.{name}" for name in PLANE_NAMES)
# SEM (register row 746): the meta controller's params that are one per `Deck`. They
# close over one deck (`preset.*` its `DeckProject`, `deck.chase` its registry's
# `chasing`, `totem.*` and `poi.*` their `on_reg`), so they cannot be a shared meta param,
# which `Registry.add` makes one object on every deck. They count as the meta controller's
# for `routing.meta_refusal` and the one-layer test, and stay each deck's own object.
# None persists, so no file holds one and none is in a snapshot
PER_DECK_META_GROUPS = ("preset", "deck", "totem", "poi")
PER_DECK_META = "per_deck_meta"
PARTS = {"patch": PATCH_GROUPS, "shared_meta": SHARED_META_GROUPS,
         PER_DECK_META: PER_DECK_META_GROUPS}
# the two layers (the owner, 2026-11-04, fourth round: "two layers of granularity and no
# others"): these parts are the meta controller's, and "patch" is the patch's. A param
# is in exactly one (tests/test_layer_boundary.py, over the app's whole registry)
META_PARTS = ("shared_meta", PER_DECK_META)

# the reference's fader → rotation-rate factor (its PLANEDRIVE was
# dir · out · DRIVE · gain). It lives here, not in the chain, because it is
# a routing constant: the rate range below and the legacy6 routes
# (routing.ROT_DEPTH) both derive from it, and routing.py imports params.
DRIVE = 3.2
# rot.rate.* spans the largest drive the reference ever put on a plane — a
# lane at the CEIL asymptote through DRIVE at the drive fader's 8× — so the
# legacy6 routes (routing.py) land today's rate without clamping. Wide for
# a slider (RAW_STEPS detents of 1.33×); WP5a can give it a finer widget.
ROT_RATE_MAX = CEIL * DRIVE * tapers.T_DRIVE.map(tapers.T_DRIVE.steps)

# camera.pan's reach, world units (plan 26 A2). Chosen so a routed pan
# travels as far as the old ±4000 px did on the 1080p screen
# (geometry.PAN_REF_PX, 324 px a unit there: ±12.3): hands-orbit's push
# of 0.1 moves the shape ±1.2 units (≈ ±390 px) for a hand across the box,
# where it moved ±400 px
PAN_RANGE = 12.0
# the eye's ranges: a field of view from a long lens to a wide one, and a
# distance from just outside a unit shape to far off. Plan 43 C2 (row 574)
# made both modulatable and left their tapers as they were — `eye.fov`
# linear, `eye.distance` log — so a desk row or macro learned onto either
# before lands the same value for the same knob position
EYE_FOV_RANGE = (10.0, 120.0)
EYE_DISTANCE_RANGE = (1.5, 40.0)

# modulation hysteresis: a toggle or trigger goes high above ON and low
# below OFF; an enum or integer only moves once the target is this far
# past the midpoint between two choices
MOD_ON, MOD_OFF = 0.6, 0.4
MOD_DEADBAND = 0.15

# the base chase (plan 52): the deck's meta control, held to commit the
# performer into the base. Its group is meta, one per deck (`PER_DECK_META_GROUPS`):
# every deck has its own, and no file holds it
CHASE_PARAM = "deck.chase"
CHASE_LABEL = "base chase"     # the undo step's name
# a macro's base moves its base subscribers (`Router.follow_macros`), which an
# offset never did: committing one would jump them (register row 655)
CHASE_REFUSED_GROUPS = ("macro",)


class Kind(Enum):
    CONTINUOUS = "continuous"
    ENUM = "enum"
    TOGGLE = "toggle"
    TRIGGER = "trigger"
    TEXT = "text"



@dataclass(eq=False)
class Param:
    id: str
    label: str
    kind: Kind
    get: Callable[[], Any] = field(repr=False, default=lambda: None)
    put: Callable[[Any], None] = field(repr=False, default=lambda v: None)  # raw object write
    fire: Callable[[], None] = field(repr=False, default=lambda: None)
    group: str = ""
    tip: str = ""
    # CONTINUOUS
    taper: Taper | None = None
    lo: float = 0.0
    hi: float = 1.0
    log: bool = False           # untapered range mapped in octaves
    integer: bool = False       # untapered range that only takes ints
    wrap: bool = False          # a circular range (yaw): stepping wraps
    fmt: Callable[[float], str] = field(repr=False, default=lambda v: f"{v:.2f}")
    # ENUM: a list, or a callable returning one (loadable patch names change on save)
    choices: list[str] | Callable[[], list[str]] = field(default_factory=list)
    # ENUM: which of the choices hold something (a bank slot that names a
    # loadable patch) — what a light needs to say "filled"; None: no such notion
    has: Callable[[int], bool] | None = field(repr=False, default=None)
    # ENUM: what a desk `set` button held midi.HOLD_S does with its choice
    # (a bank pad: save the live state into an empty slot) — True when it
    # did something, so the new light blinks; None: a hold is a press
    held: Callable[[int], bool] | None = field(repr=False, default=None)
    # ENUM: what a desk `set` button tapped while the desk's SAVE is held
    # does with its choice (plan 24 C1: a bank pad saves the live state into
    # its slot, filled or empty) — True when it saved, so the pad blinks;
    # None: under SAVE the press is an ordinary press
    save_into: Callable[[int], bool] | None = field(repr=False, default=None)
    # told a desk fader's position on every message, caught or not (soft pickup
    # drops an uncaught one before anything else hears it); True: the message goes
    # no further, nothing is written. None: nobody asks
    touched: Callable[[float], bool] | None = field(repr=False, default=None)
    # what the param is for
    persist: bool = True         # belongs in a snapshot: a loadable patch or a project's session (part_of)
    modulatable: bool = True     # a lane may drive it; never on a meta param (`__post_init__`)
    alias: bool = False          # a view onto another param (band.sel.*)
    # modulation state — runtime only
    _base: float | None = field(default=None, repr=False)   # norm; None = not modulated
    _mod: float = field(default=0.0, repr=False)            # this frame's offsets
    _held: bool = field(default=False, repr=False)          # a source called this frame
    _last: float | None = field(default=None, repr=False)   # norm we last wrote
    _disc: float | None = field(default=None, repr=False)   # last discrete effective
    _armed: bool = field(default=True, repr=False)          # trigger edge detector
    _bad: bool = field(default=False, repr=False)           # a non-finite value was dropped
    # the frame mark this param last landed under (plan 28 N0): `apply`
    # with the same mark again is a no-op, so `Router.modulate` can land a
    # param something in the pass reads and `Registry.apply` skip it
    _mark: int | None = field(default=None, repr=False)
    # the base chase (plan 52): position rows' share of `_mod` this frame
    # (None: no position row called); the verb is held on this param; how
    # much of the pushes' offset the base already holds
    _pos: float | None = field(default=None, repr=False)
    _chase: bool = field(default=False, repr=False)
    _trim: float = field(default=0.0, repr=False)

    def __post_init__(self):
        if self.alias:
            self.persist = self.modulatable = False
        if self.kind is Kind.TRIGGER:
            self.persist = False
        if self.kind is Kind.TEXT:
            self.modulatable = False
        # plan 44 D3 (review of #351): its part of the split, once — an id and
        # a group never change, and `snapshot(part=)` asks every frame the
        # dirty dot is drawn
        self._part = None if self.group is None else part_of_id(self.id, self.group)
        # register row 775: no route lands on a meta param (row 743), so the flag says so,
        # whatever the declaration said or left out. By the part and by the id, which is
        # what the doors judge (`is_meta_id`), so the two can't disagree. Its desk rows,
        # keys and pad buttons set it (`routing.act`, `Router.dispatch`) and never ask this
        if self._part in META_PARTS or is_meta_id(self.id):
            self.modulatable = False

    # ---- generic value access ----

    @property
    def value(self):
        """The live (effective) value — what the renderer sees."""
        return self.get()

    @property
    def modulated(self) -> bool:
        return self._base is not None

    @property
    def base(self):
        """What the user set, in the param's own units — what a loadable patch saves.

        Equal to `value` unless a source is modulating the param; then the
        object holds base + offsets and this is the underlying setting.
        Every surface-facing reader below (norm, position, text, step…)
        works on the base, so a fader shows and moves the setting while
        the lane rides on top of it.
        """
        if self._base is None:
            return self.get()
        return self._value_of_norm(self._base)

    @property
    def eff_norm(self) -> float:
        """The effective (object) value as a float in [0, 1]."""
        return self._norm_of(self.get())

    def set(self, v) -> None:
        """Write a raw value — to the object, or to the base while modulated."""
        if self._base is None:
            self.put(v)
        else:
            self._base = self._norm_of(v)

    @property
    def names(self) -> list[str]:
        return self.choices() if callable(self.choices) else self.choices

    @property
    def steps(self) -> int:
        """Detents across the throw; the resolution step() moves in."""
        if self.kind is Kind.CONTINUOUS:
            if self.taper is not None:
                return self.taper.steps
            if self.integer:
                return round(self.hi - self.lo)
            return RAW_STEPS
        if self.kind is Kind.ENUM:
            return max(len(self.names) - 1, 0)
        return 1

    # ---- norm ↔ value, both ways, without detents ----

    def _norm_of(self, v) -> float:
        k = self.kind
        if k is Kind.CONTINUOUS:
            if self.taper is not None:
                return self._taper_pos(v) / self.taper.steps
            return self._raw_norm(v)
        if k is Kind.ENUM:
            n = self.steps
            return 0.0 if n == 0 else _clamp(int(v) / n, 0.0, 1.0)
        if k is Kind.TOGGLE:
            return 1.0 if v else 0.0
        return 0.0

    def _taper_pos(self, v: float) -> float:
        """A tapered value's position as a float: the detent when it sits on
        one (set_value puts it there, so the check is exact), otherwise
        found between the neighbouring detents by bisection on map(), a
        monotonic closed form in a float position. This is what keeps a
        sub-detent nudge in the base while a source rides the param."""
        t = self.taper
        p = t.unmap(v)
        if t.map(p) == v:
            return float(p)
        lo, hi = max(p - 1, 0), min(p + 1, t.steps)
        if v <= t.map(lo):
            return float(lo)
        if v >= t.map(hi):
            return float(hi)
        for _ in range(32):
            mid = (lo + hi) / 2
            if t.map(mid) < v:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def _value_of_norm(self, u: float):
        """The value at a float position — the un-detented map a lane uses.

        Every taper's map() is a closed form in the position, so it takes a
        float as happily as an int; only unmap() rounds.
        """
        k = self.kind
        if k is Kind.CONTINUOUS:
            if self.taper is not None:
                return self.taper.map(u * self.taper.steps)
            return self._raw_value(u)
        if k is Kind.ENUM:
            return round(u * self.steps)
        if k is Kind.TOGGLE:
            return u >= 0.5
        return None

    # ---- CONTINUOUS ----

    def set_value(self, v: float) -> None:
        """Set a real value, clamped (or wrapped) into range."""
        if self.kind is not Kind.CONTINUOUS:
            raise TypeError(f"{self.id} is {self.kind.value}, not continuous")
        if self.taper is not None:
            self.set(self.taper.map(self.taper.unmap(v)))
            return
        if self.wrap:
            span = self.hi - self.lo
            v = self.lo + (v - self.lo) % span
        else:
            v = _clamp(v, self.lo, self.hi)
        self.set(round(v) if self.integer else v)

    def position(self) -> int:
        """Detent index of the current setting, 0..steps."""
        if self._base is not None:
            return round(self._base * self.steps)
        v = self.get()
        if self.taper is not None:
            return self.taper.unmap(v)
        return round(self._raw_norm(v) * self.steps)

    def set_position(self, p: int) -> None:
        p = _clamp(int(p), 0, self.steps)
        if self.taper is not None:
            self.set(self.taper.map(p))
        else:
            self.set(self._raw_value(p / self.steps))

    def _raw_norm(self, v: float) -> float:
        if self.log:
            lo, hi = math.log2(self.lo), math.log2(self.hi)
            u = (math.log2(max(v, 1e-9)) - lo) / (hi - lo)
        else:
            u = (v - self.lo) / (self.hi - self.lo)
        return _clamp(u, 0.0, 1.0)

    def _raw_value(self, u: float) -> float:
        u = _clamp(u, 0.0, 1.0)
        if self.log:
            lo, hi = math.log2(self.lo), math.log2(self.hi)
            v = 2.0 ** (lo + u * (hi - lo))
        else:
            v = self.lo + u * (self.hi - self.lo)
        return round(v) if self.integer else v

    # ---- normalized interface, every non-trigger kind ----

    @property
    def norm(self) -> float:
        """The setting as a float in [0, 1] (the base while modulated).
        Continuous: a tapered value between detents reads between them;
        `position()` is the detent."""
        if self._base is not None:
            return self._base
        return self._norm_of(self.get())

    def set_norm(self, u: float) -> None:
        """Set from a float in [0, 1] — what a MIDI value or a fader is."""
        u = _clamp(float(u), 0.0, 1.0)
        k = self.kind
        if k is Kind.CONTINUOUS:
            self.set_position(round(u * self.steps))
        elif k is Kind.ENUM:
            self.set(round(u * self.steps))
        elif k is Kind.TOGGLE:
            self.set(u >= 0.5)
        elif k is Kind.TRIGGER and u >= 0.5:
            self.fire()

    # ---- discrete moves ----

    def step(self, n: int = 1) -> None:
        """Move n detents: taper positions, choices, or a flip."""
        k = self.kind
        if k is Kind.CONTINUOUS:
            if self.wrap and self.taper is None:
                self.set_value(self.base + n * (self.hi - self.lo) / self.steps)
            else:
                self.set_position(self.position() + n)
        elif k is Kind.ENUM:
            m = len(self.names)
            if m and self.has is not None:
                self.set(self._walk(n, wrap=False))
            elif m:
                self.set(_clamp(self.base + n, 0, m - 1))
        elif k is Kind.TOGGLE:
            if n:
                self.set(not self.base)
        elif k is Kind.TRIGGER:
            self.fire()

    # ---- relative moves in the param's own units: the mouse, the sticks, ↑/↓ ----
    #
    # Both work on the *base* and write it back, so while a performer owns
    # the param its offset rides on the move instead of folding into it
    # (plan 09 decision 3). Neither snaps to a detent: a drag or a held key
    # moves a tapered param by a fraction of a step per frame, and
    # set_value's unmap round-trip would land it back on the same detent
    # every frame — so the value is written raw through set(), and a
    # modulated base keeps its continuous position (_taper_pos).

    def nudge(self, delta: float) -> float:
        """Add `delta` to the base, wrapped or clamped into range; returns
        the delta actually applied (less than asked at a stop)."""
        if self.kind is not Kind.CONTINUOUS:
            raise TypeError(f"{self.id} is {self.kind.value}, not continuous")
        old = self.base
        lo, hi = self._bounds()
        if self.wrap:
            v = lo + (old + delta - lo) % (hi - lo)
        else:
            v = _clamp(old + delta, lo, hi)
        if self.integer:
            v = round(v)
        self.set(v)
        return delta if self.wrap else v - old

    def scale(self, factor: float) -> float:
        """Multiply the base by `factor`, clamped into range; returns the
        ratio actually applied. A ratio means nothing on a base of 0 or a
        range that reaches 0 or below: then 1.0, and nothing moves."""
        if self.kind is not Kind.CONTINUOUS:
            raise TypeError(f"{self.id} is {self.kind.value}, not continuous")
        old = self.base
        lo, hi = self._bounds()
        if lo <= 0.0 or old <= 0.0:
            return 1.0
        v = _clamp(old * factor, lo, hi)
        if self.integer:
            v = round(v)
        self.set(v)
        return v / old

    def _bounds(self) -> tuple[float, float]:
        """The range in the param's own units — the taper's ends, or lo..hi."""
        t = self.taper
        return (t.map(0), t.map(t.steps)) if t is not None else (self.lo, self.hi)

    def _walk(self, n: int, *, wrap: bool) -> int:
        """Where n steps land on an enum whose choices can be empty
        (`has`, e.g. the bank's slots): each step goes to the next choice
        that holds something, so a learned step or toggle never stops on
        an empty slot (audit R14). Past the last filled choice a step
        stays put and a cycle wraps; with nothing filled, nothing moves."""
        m, k = len(self.names), int(self.base)
        d = 1 if n > 0 else -1
        for _ in range(abs(int(n))):
            j = m if (wrap and k < 0 and d < 0) else k    # (nothing loaded: -1)
            for _ in range(m):
                j += d
                if wrap:
                    j %= m
                elif not 0 <= j < m:
                    break
                if self.has(j):
                    k = j
                    break
        return k

    def cycle(self, n: int = 1) -> None:
        """Like step, but an enum wraps around."""
        if self.kind is Kind.ENUM and self.names and self.has is not None:
            self.set(self._walk(n, wrap=True))
        elif self.kind is Kind.ENUM and self.names:
            self.set((self.base + n) % len(self.names))
        else:
            self.step(n)

    def toggle(self) -> None:
        if self.kind is Kind.TOGGLE:
            self.set(not self.base)
        elif self.kind is Kind.TRIGGER:
            self.fire()

    # ---- readout ----

    def text(self) -> str:
        k = self.kind
        v = self.base
        if k is Kind.CONTINUOUS:
            return self.fmt(v)
        if k is Kind.ENUM:
            names = self.names
            return names[v] if 0 <= v < len(names) else "—"
        if k is Kind.TOGGLE:
            return "on" if v else "off"
        if k is Kind.TEXT:
            return str(v or "")
        return ""

    # ---- modulation: any source, one rule ----

    def modulate(self, u: float, *, position: bool = False) -> None:
        """Add a source's offset for this frame, in normalized units.

        A source calls this every frame it is routed here, even with 0 —
        holding the param is what keeps its base apart from the object;
        the frame nothing calls, `apply()` writes the base back. `position`:
        the offset is a position row's, which lands an absolute value
        whatever the base is, so the base chase's ledger leaves it out.
        """
        if not self.modulatable:
            return
        if self._base is None:
            base = self._norm_of(self.get())         # adopt the user's setting
            self._base = base if math.isfinite(base) else 0.0
            self._last = self._base
            self._disc = None
        u = float(u)
        if math.isfinite(u):
            self._mod += u
            if position:
                self._pos = (self._pos or 0.0) + u
        else:                   # a NaN or an inf never reaches the base (plan 14 WP1)
            self._bad = True
        self._held = True

    def apply(self, mark: int | None = None) -> None:
        """End of frame: write base + offsets to the object, or let go.

        `mark` is the frame's (plan 28 N0, `Registry.frame`): a second call
        under the mark this param already landed under does nothing — no
        base restored twice, no offset doubled, no toggle flipped twice. So
        `Router.modulate` lands a param a later node of the pass reads, and
        `Registry.apply` lands every other one. None: no mark, today's call
        (`Registry.remove`, a test)."""
        if mark is not None:
            if getattr(self, "_mark", None) == mark:
                return
            self._mark = mark
        if self._base is None:
            return
        held, mod, pos = self._held, self._mod, self._pos
        self._held, self._mod, self._pos = False, 0.0, None
        k = self.kind
        if not held:                          # last source left: restore base
            if k is not Kind.TRIGGER:
                self.put(self._value_of_norm(self._base))
            # (the trim stays: a source back next frame, after a gate's or a
            # lane's flicker, brings the offset the base already holds)
            self._base = self._last = self._disc = None
            return
        if k is not Kind.TRIGGER:
            # something wrote the object since we did (the rotation
            # integrator, loaded_patch.load…): that delta belongs to the base
            cur = self._norm_of(self.get())
            if not math.isfinite(cur):          # the object went non-finite: the base holds
                self._bad = True
            elif self._last is not None and cur != self._last:
                self._base += cur - self._last
                self._base = self._base % 1.0 if self.wrap else _clamp(self._base, 0.0, 1.0)
        target = self._base + mod
        if k is Kind.CONTINUOUS:
            push = mod if pos is None else mod - pos
            if self._trim and not self._chase:
                self._trim = _came_home(self._trim, push)
            if pos is None:                   # a position row lands absolutely: no trim on it
                target -= self._trim
            raw = target
            target = target % 1.0 if self.wrap else _clamp(target, 0.0, 1.0)
            if self.integer and self.taper is not None:
                self.put(self.taper.map(self._snap(target * self.steps)))
            elif self.integer:
                self.put(self._raw_value(self._snap(target * self.steps) / self.steps))
            else:
                self.put(self._value_of_norm(target))
            if self._chase:
                self._commit(raw, target, push)
        elif k is Kind.ENUM:
            self.put(int(self._snap(target * self.steps)))
        elif k is Kind.TOGGLE:
            on = self._disc == 1.0
            on = target > MOD_OFF if on else target >= MOD_ON
            self._disc = 1.0 if on else 0.0
            self.put(on)
        else:  # TRIGGER: fire on the rising edge, re-arm below the low mark
            if self._armed and target >= MOD_ON:
                self._armed = False
                self.fire()
            elif not self._armed and target < MOD_OFF:
                self._armed = True
            return
        self._last = self._norm_of(self.get())

    def _commit(self, raw: float, target: float, push: float) -> None:
        """The base chase's landing (plan 52): what the param shows now
        becomes its base, and the trim says how much of the pushes' offset
        that holds. The part a range's end cut off (`raw` past `target`) is
        not in the base, so it stays on the offset's side of the ledger: the
        next frame lands where it would have with no verb held."""
        shown = self._norm_of(self.get()) if self.integer else target
        self._trim = push - (0.0 if self.wrap else raw - shown)
        self._base = shown

    def _snap(self, x: float) -> float:
        """Nearest integer, moving only once past the midpoint + deadband."""
        cur = self._disc
        if cur is None or abs(x - cur) > 0.5 + MOD_DEADBAND:
            cur = float(round(_clamp(x, 0, self.steps)))
        self._disc = cur
        return cur


def _came_home(trim: float, push: float) -> float:
    """The trim after this frame's push (plan 52): it only falls, following
    an offset on its way to zero and never past it. So a source going home
    moves nothing (offset less trim stays 0), one pushing further than it
    was moves the look on from where it stands, and one past zero rides in
    full. A frame's motion is the only step it ever makes."""
    if trim > 0.0:
        return trim if push >= trim else max(push, 0.0)
    return trim if push <= trim else min(push, 0.0)


def chase_reaches(p: Param) -> bool:
    """Does the base chase commit this param (plan 52, row 654): continuous,
    modulatable and the deck's own. A shared meta param is the room's and a
    deck's verb never writes it; a macro is left out (`CHASE_REFUSED_GROUPS`)."""
    return (p.kind is Kind.CONTINUOUS and p.modulatable and part_of(p) == "patch"
            and p.group not in CHASE_REFUSED_GROUPS)


def part_of(p: Param) -> str | None:
    """"patch", "shared_meta" or `PER_DECK_META`, by the param's group; None for a
    group in none of them, which the one-layer test fails. A shared meta key of a
    patch group (`SHARED_META_KEYS`: `ghost.mirror`) is the meta controller's. The one
    rule (plan 44 D3): a deck's registry hands the meta controller every param this calls
    "shared_meta". Cached on the param at its declaration (`Param._part`); one from
    before a hot reload is asked."""
    got = p.__dict__.get("_part", _UNSET)
    if got is not _UNSET:
        return got
    return None if p.group is None else part_of_id(p.id, p.group)


_UNSET = object()


def is_shared_meta_id(pid: str | None) -> bool:
    """Does `pid` name a shared meta param (`SHARED_META_GROUPS`, plan 13 §4), the one object every
    deck shares? By its group prefix, so a param this registry lacks (a band a layout has
    not built yet) is still classed."""
    return bool(pid) and part_of_id(pid) == "shared_meta"


def is_meta_id(pid: str | None) -> bool:
    """Does `pid` name a param of the meta controller, whichever kind? The test for "may
    a patch's row reach it"; `is_shared_meta_id` only for "is it one object on every deck"."""
    return bool(pid) and part_of_id(pid) in META_PARTS


def is_per_deck_meta_id(pid: str | None) -> bool:
    """Does `pid` name a meta param that is one per `Deck` (`PER_DECK_META`)?"""
    return bool(pid) and part_of_id(pid) == PER_DECK_META


def group_part(group: str | None) -> str | None:
    """The part a whole group is in (one of `PARTS`, or None)."""
    for name, groups in PARTS.items():
        if group in groups:
            return name
    return None


def in_group(p: Param, group: str) -> bool:
    """Whether `p` is one of `group`'s params on every per-group road — a
    module preset's values, its reset, its dirty dot, `snapshot(group)`,
    the library's fresh values (review of #351, round 2): its group, and
    its group's part — so a shared meta key (`ghost.mirror`) is never moved,
    saved or counted by the `ghost` group's roads, though the HANDS page
    (`Registry.group`) still lists it."""
    return p.group == group and part_of(p) == group_part(group)


def part_of_id(pid: str, group: str | None = None) -> str | None:
    """`part_of` by id alone: `group` is the param's, else the id's first
    segment (every group's ids start with it but the bank's, `preset`)."""
    if pid in SHARED_META_IDS:
        return "shared_meta"
    group = pid.partition(".")[0] if group is None else group
    keys = SHARED_META_KEYS.get(group)
    if keys and pid.rpartition(".")[2] in keys:
        return "shared_meta"
    for name, groups in PARTS.items():
        if group in groups:
            return name
    return None


def instance_id(node: str, key: str, n: int = 1) -> str:
    """The naming rule for a render node's params (plan 26 A0; ENGINEERING
    §2, "Node instances"). `node` is the node's id prefix — ``fx.acid``
    for an effect, ``ghost``, ``dream`` — and `key` the param's own name.
    The first instance keeps today's id (``fx.acid.mix``); instance n ≥ 2
    carries its number as a segment right after the prefix
    (``fx.acid.2.mix``, ``ghost.2.alpha``). The first segment never
    changes: it is the group, which decides whether the param is in a
    loadable patch (`part_of`), so a single-instance graph never migrates a loadable patch
    or a binding."""
    if n < 1:
        raise ValueError(f"instance numbers start at 1, not {n}")
    return f"{node}.{key}" if n == 1 else f"{node}.{n}.{key}"


def instance_of(pid: str, node: str) -> tuple[int, str] | None:
    """`instance_id` backwards: (n, key) when `pid` is a param of some
    instance of `node`, else None. A purely decimal segment right after
    the prefix is the marker (n ≥ 2); no key and no effect file is ever
    purely decimal (tests/test_params.py pins it), so today's ids all
    read as the first instance."""
    head = f"{node}."
    if not pid.startswith(head):
        return None
    rest = pid[len(head):]
    mark, dot, key = rest.partition(".")
    if dot and mark.isdecimal() and key and int(mark) >= 2 and str(int(mark)) == mark:
        return int(mark), key
    # by design an explicit `.1.` (or `.02.`) is no marker: `instance_id`
    # never writes one, so `fx.acid.1.mix` reads as instance 1, key `1.mix`
    return (1, rest) if rest else None


def is_instance_id(pid: str) -> bool:
    """Is `pid` a param of an extra node instance — `fx.<file>.<n>.<key>`
    or `ghost.<n>.<key>`, n ≥ 2 — one that exists only while a loadable patch's
    graph holds that instance (plan 26 A4)? A loadable patch load sorts such ids
    against the graph it lands; an old show's `ghost.<n>.*` ones the registry
    lacks are held back (`Project._held_back`)."""
    parts = pid.split(".")
    if parts[0] == "fx" and len(parts) >= 4:
        mark = parts[2]
    elif parts[0] == "ghost" and len(parts) >= 3:
        mark = parts[1]
    else:
        return False
    return mark.isdecimal() and str(int(mark)) == mark and int(mark) >= 2


class Registry:
    """An ordered map of Param by id."""

    # this deck's dial readings, {"L": "petal", "R": "blend"} (`declare_dial`); None: a
    # registry with no dial
    dial_modes: dict[str, str] | None = None

    @staticmethod
    def group_word(group: str) -> str:
        """`groupwords.group_word`, for `undo.py`, a leaf that holds a registry."""
        return groupwords.group_word(group)

    # class-level so a registry from before a hot reload has them (plan 28 N0):
    # `serial` moves on every add and remove (the modulation patch's cache
    # key, `Router.modgraph`); `frame` is the frame mark `Router.modulate`
    # opens (`begin_frame`) and `landed` the mark `apply` lands under —
    # the params the pass already landed are skipped — and closes
    serial: int = 0
    frame: int = 0
    landed: int | None = None
    # plan 44 D3: the meta controller registry this deck's registry follows — None
    # for a registry of its own (a bare one, the tests'; and one from
    # before a hot reload, on the class)
    meta_reg: MetaRegistry | None = None
    # the base chase (plan 52): held now; this deck's `undo.Undo`
    # (`Deck.build`), None: a bare registry has no steps
    chasing: bool = False
    chase_undo: Any = None
    _chase_steps: Any = None             # the `undo.Undo` the press opened its step on

    def __init__(self, meta_reg: MetaRegistry | None = None):
        self._p: dict[str, Param] = {}
        self.nonfinite: list[str] = []   # params that dropped a NaN / inf last apply()
        # the one rule for what an alias stands for right now (band.sel.*
        # → the selected band), installed by build_registry; the panel's
        # widgets, the Learn object and the routing menu all ask here
        self.real_of: Callable[[Param], Param] | None = None
        # the other alias families, by id prefix → who they stand for right
        # now (hands.sel.* → the selected hand axis, hands/core.py), asked
        # after `real_of`; a module that declares an alias adds its rule
        self.aliases: dict[str, Callable[[Param], Param | None]] = {}
        if meta_reg is not None:
            self.follow(meta_reg)

    def follow(self, meta_reg: MetaRegistry) -> None:
        """Hold `meta_reg`'s params by reference from now on (plan 44 D3): the
        ones it has now, added here in its order, and every one it gains or
        loses later — one `Param` object in every deck's registry, so
        `reg["output.dim"]` reads and writes the room's from any deck. A
        shared meta param declared on this registry goes to `meta_reg` (`add`)."""
        if self.meta_reg is meta_reg:
            return
        if self.meta_reg is not None:
            raise ValueError("a deck's registry follows one meta registry")
        self.meta_reg = meta_reg
        meta_reg._follow(self)
        for p in list(meta_reg):
            self._put(p)

    def real(self, p: Param) -> Param:
        """The param behind an alias — where the base and the modulation
        state live — or `p` itself when it is not one. A meta controller alias
        (`band.sel.*`) is answered by the meta controller's rules (plan 44 D3)."""
        if not p.alias:
            return p
        if self.real_of is not None:
            q = self.real_of(p)
            if q is not None and q is not p:
                return q
        for prefix, rule in self.aliases.items():
            if p.id.startswith(prefix):
                return rule(p) or p
        meta_reg = self.meta_reg
        if meta_reg is not None and meta_reg is not self:
            return meta_reg.real(p)
        return p

    def _put(self, p: Param) -> Param:
        """`p` into this registry's own map, whoever declared it."""
        if p.id in self._p:
            raise ValueError(f"duplicate param id {p.id}")
        self._p[p.id] = p
        self.serial += 1
        if self.chasing:                 # (a loadable patch landed under the verb declared it)
            p._chase = chase_reaches(p)
        return p

    def add(self, p: Param) -> Param:
        """Declare `p`. On a deck's registry (one that follows a meta controller) a
        shared meta param (`part_of`) is the meta controller's: added there, and so to
        every deck that follows it — declared once (plan 44 D3)."""
        meta_reg = self.meta_reg
        if meta_reg is not None and meta_reg is not self and part_of(p) == "shared_meta":
            return meta_reg.add(p)            # (its one duplicate check, every deck)
        return self._put(p)

    def __getitem__(self, pid: str) -> Param:
        return self._p[pid]

    def __contains__(self, pid: str) -> bool:
        return pid in self._p

    def __iter__(self) -> Iterator[Param]:
        return iter(self._p.values())

    def __len__(self) -> int:
        return len(self._p)

    def get(self, pid: str) -> Param | None:
        return self._p.get(pid)

    def ids(self) -> list[str]:
        return list(self._p)

    def group(self, name: str) -> list[Param]:
        return [p for p in self if p.group == name]

    def remove(self, pid: str) -> Param | None:
        """Drop a param (a band that was deleted). Bindings to it go dormant —
        every adapter already treats an unknown id as a no-op. A shared meta param
        is the meta controller's to drop, on `MetaRegistry.remove`, and it leaves
        every deck there. A deck's registry keeps it, warns and returns None (LY1):
        whatever a deck's own section drops, no other deck loses anything."""
        meta_reg = self.meta_reg
        if meta_reg is not None and meta_reg is not self:
            q = meta_reg.get(pid)
            if q is not None and q is self._p.get(pid):
                warnings.warn(f"{pid} is shared: a deck's registry doesn't drop it, "
                              "MetaRegistry.remove does", stacklevel=2)
                return None
        p = self._p.pop(pid, None)
        if p is not None:
            self.serial += 1
        if p is not None and p.modulated:
            p._held = False
            p.apply()            # hand the object its base back
        return p

    def remove_prefix(self, prefix: str) -> list[Param]:
        gone = (self.remove(pid) for pid in list(self._p) if pid.startswith(prefix))
        return [p for p in gone if p is not None]

    # ---- frame ----

    def begin_frame(self) -> int:
        """A new frame mark (plan 28 N0): `Router.modulate` lands the params
        its pass reads under it, and the next `apply` skips those. Returns
        the mark.

        A deck's registry (plan 44 D3, review of #351) takes its mark from
        its session: the first deck to begin a frame moves the meta controller's
        frame on, every other deck adopts it, so every deck's pass in one
        frame lands the shared shared meta params under **one** mark — a
        shared meta param a pass landed is never landed again that frame by
        another deck, and two registries' counters can never meet by
        chance on a shared `Param`."""
        meta_reg = self.meta_reg
        if meta_reg is not None and meta_reg is not self:
            if self.frame == meta_reg.frame:      # this deck is the first this frame
                meta_reg.frame += 1
            self.frame = meta_reg.frame
            meta_reg.landed = meta_reg.frame       # (the meta controller's own apply dedups by it)
        else:
            self.frame += 1
        self.landed = self.frame
        return self.frame

    def _owned_by_meta(self, p: Param) -> bool:
        """Whether `p` is a shared meta param this deck holds by reference."""
        meta_reg = self.meta_reg
        return (meta_reg is not None and meta_reg is not self
                and meta_reg._p.get(p.id) is p)

    def lands(self, p: Param) -> bool:
        """Does this deck land `p`? All its own, and the meta controller's only when
        it is the meta controller's lead. What a macro's base subscriber asks
        (`Router.follow_macros`) and the line under a row (`ui_routing`)."""
        meta_reg = self.meta_reg
        return (meta_reg is None or meta_reg is self or meta_reg.on_air_reg is self
                or not self._owned_by_meta(p))

    def apply(self) -> None:
        """Once per frame, after every source has called modulate(): base +
        offsets onto every modulated param, in registry order — but for
        those `Router.modulate` already landed under this frame's mark
        (plan 28 N0: a param the pass reads lands before its reader), which
        `Param.apply` skips. Closes the mark: an `apply` with no pass
        before it lands everything, as before.

        A shared meta param is one `Param` in every deck, and no route moves
        one (row 775), so it has no offset for any deck to land, and
        `app.frame` running the lead first is what has another deck read this
        frame's meta controller values."""
        # over a copy: a modulated trigger may add or remove params
        # (a band layout change) while we are still walking the table.
        # `nonfinite`: the params that dropped a NaN / inf this frame (the
        # stall log names each once, app.py) — those the pass landed too
        mark, self.landed = self.landed, None
        bad: list[str] = []
        for p in list(self._p.values()):
            if p._base is not None:
                p.apply(mark)
            if p._bad:
                p._bad = False
                bad.append(p.id)
        self.nonfinite = bad

    # ---- the base chase (plan 52): the verb, a deck operation ----

    def base_chase(self, on: bool, *, steps=None) -> bool:
        """Hold or let go of the verb on this deck: while on, every param it
        reaches (`chase_reaches`) writes what it shows into its base at each
        landing (`Param._commit`), with no per-frame scan and no change to
        what is shown. Let go, the look stays where the performer left it.

        One hold is one undo step on `steps` (a `undo.Undo`; None: this
        deck's, `chase_undo`), remembered at the press so any
        let-go closes that one; what closes the step otherwise (an undo, a
        load, a learn under the verb) ends the verb with it. Returns
        whether the verb is on now."""
        on = bool(on)
        if on == self.chasing:
            return on
        if on:
            self._chase_steps = steps if steps is not None else self.chase_undo
            if self._chase_steps is not None:                 # before any base moves
                undo.keep_open(CHASE_LABEL, self._chase_steps,
                               on_end=lambda: self.base_chase(False))
        self.chasing = on
        for p in self._p.values():
            p._chase = on and chase_reaches(p)
        if not on:
            opened, self._chase_steps = self._chase_steps, None
            if opened is not None:
                undo.let_close(opened)
        return on

    # ---- persistence: the one serialization every loadable patch is made of ----

    def snapshot(self, group: str | None = None, *, ids=None,
                 part: str | None = None) -> dict[str, Any]:
        """{id: base value} for every persistent param, the macros
        included, or only one group, one id set, or one part of the split
        (``part="patch"`` / ``"shared_meta"``, PARTS). The filters
        combine: each one given must hold. A part is `part_of`'s (plan 44
        D3: `ghost.mirror` is the meta controller's though its group is not)."""
        out: dict[str, Any] = {}
        if part is not None and part not in PARTS:
            raise KeyError(part)
        for p in self._p.values():
            if not p.persist:
                continue
            if group is not None and not in_group(p, group):
                continue
            if ids is not None and p.id not in ids:
                continue
            if part is not None and part_of(p) != part:
                continue
            v = p.base
            out[p.id] = list(v) if isinstance(v, list) else v
        return out

    def forget_commits(self, ids: Iterable[str]) -> None:
        """The base chase's ledger empties on these params (plan 52): whatever
        their bases hold now, no commit of the verb's is in them."""
        for pid in ids:
            p = self._p.get(pid)
            if p is not None:
                p._trim = 0.0

    def take_running(self, src: Registry) -> None:
        """What `src`'s params are in the middle of, onto this deck's of the same
        id, for "copy on air to off air" (`MetaController.copy_on_air`): the base
        a route rides on to the last bit, what it last wrote, where a discrete
        target and a trigger's edge stand, and the chase ledger. So the next
        landing here is the next landing there. Patch params only: a
        shared meta param is one object, on both already. No undo step, no dirty dot:
        the bases are the ones the doc road landed."""
        for p in self._p.values():
            q = src._p.get(p.id)
            if q is None or q is p or part_of(p) != "patch":
                continue
            p._trim = q._trim
            if p.kind is not Kind.TRIGGER and p.get() != q.get():
                p.put(q.get())                 # what it shows, as `_last` says it does
            p._base, p._last, p._disc, p._armed = q._base, q._last, q._disc, q._armed

    def restore(self, values: dict[str, Any], *, trims: dict[str, float] | None = None
                ) -> list[str]:
        """Set every param named; returns the ids this registry doesn't have.
        The base chase's ledger goes with the base it describes (plan 52): a
        continuous param's trim is what `trims` (an undo's state) says that
        base held, and none when there is no such state (a load: a look's
        values hold no commit, so a route on them rides in full)."""
        missing = []
        for pid, v in values.items():
            p = self._p.get(pid)
            if p is None:
                missing.append(pid)
                continue
            k = p.kind
            if k is Kind.CONTINUOUS:
                # raw, not set_value: a saved value lands exactly where it
                # was, detent or not (the base is detented only while modulated)
                p.set(float(v))
                p._trim = trims.get(pid, 0.0) if trims else 0.0
            elif k is Kind.ENUM:
                p.set(int(v))
            elif k is Kind.TOGGLE:
                p.set(bool(v))
            elif k is Kind.TEXT:
                p.set(str(v))
        return missing

    # ---- declaration helpers ----

    def continuous(self, pid, label, get, set, *, taper=None, lo=0.0, hi=1.0, log=False,
                   integer=False, wrap=False, fmt=None, group="", tip="",
                   persist=True, modulatable=True, alias=False) -> Param:
        if fmt is None:
            fmt = (lambda v: f"{int(v)}") if integer else (lambda v: f"{v:.2f}")
        return self.add(Param(
            pid, label, Kind.CONTINUOUS, get, set, group=group, tip=tip, taper=taper,
            lo=lo, hi=hi, log=log, integer=integer, wrap=wrap, fmt=fmt,
            persist=persist, modulatable=modulatable, alias=alias,
        ))

    def enum(self, pid, label, get, set, choices, *, group="", tip="",
             persist=True, modulatable=True, alias=False,
             has: Callable[[int], bool] | None = None,
             held: Callable[[int], bool] | None = None,
             save_into: Callable[[int], bool] | None = None) -> Param:
        """`has`, if given, says which choices hold something — the enum's
        counterpart of `trigger(lit=)`: the param carries what its lights
        need (a filled bank slot), so an adapter learns nothing about what
        the choices are. Stored as `Param.has`. `held`, likewise, is what a
        `set` button held midi.HOLD_S does with its choice (`Param.held`),
        and `save_into` what its tap does while the desk's SAVE is held
        (`Param.save_into`, plan 24 C1)."""
        return self.add(Param(pid, label, Kind.ENUM, get, set, group=group, tip=tip,
                              choices=choices, persist=persist, modulatable=modulatable,
                              alias=alias, has=has, held=held, save_into=save_into))

    def toggle(self, pid, label, get, set, *, group="", tip="",
               persist=True, modulatable=True, alias=False) -> Param:
        return self.add(Param(pid, label, Kind.TOGGLE, get, set, group=group, tip=tip,
                              persist=persist, modulatable=modulatable, alias=alias))

    def trigger(self, pid, label, fire, *, group="", tip="", modulatable=True,
                lit: Callable[[], bool] | None = None) -> Param:
        """`lit`, if given, is the light the trigger's button shows on its
        own — the METRONOME LED blinking on the beat (midi.py reads it as
        the param's `get`); without it a button only echoes its press."""
        p = Param(pid, label, Kind.TRIGGER, fire=fire, group=group, tip=tip,
                  modulatable=modulatable)
        if lit is not None:
            p.get = lit
        return self.add(p)

    def text(self, pid, label, get, set, *, group="", tip="", persist=True) -> Param:
        return self.add(Param(pid, label, Kind.TEXT, get, set, group=group, tip=tip,
                              persist=persist))


# the sticks' dial readings (plan 28, rows 729-730). Restated from `gamepad`
# (`DIAL_MODES`, `DIAL_DEFAULT`): the import wall forces it, `params` being both layers'
# and `gamepad` the meta controller's, and it imports glfw. tests/test_dial.py holds them equal
DIAL_READINGS = ("petal", "blend")
DIAL_SIDES = (("L", "left", "petal"), ("R", "right", "blend"))   # stick, its id's word, default


def dial_id(stick: str) -> str:
    """The param of stick "L" or "R"'s dial reading."""
    return f"pad.dial.{'left' if stick == 'L' else 'right'}"


def declare_dial(r: Registry) -> None:
    """The sticks' dial readings on one deck's registry: `pad.dial.left` and `.right`,
    saved and landed with its loadable patch like its routes, and `pad.dial.swap`, which
    trades them. Each registry holds its own (`Registry.dial_modes`, {"L": "petal", …}), so
    a load on one `Deck` changes nothing a pad on the other reads: a pad reads that dict
    of the `Deck` it drives (`devices.PadDevice.poll`). They start at the launch readings,
    the meta controller's (`MetaRegistry.dial_launch`). Not a performer's: no lane rides a
    reading, though a row can set one."""
    launch = r.meta_reg.dial_launch or {}
    modes = r.dial_modes = {stick: launch.get(stick, fresh) for stick, _, fresh in DIAL_SIDES}

    def set_mode(stick: str, i) -> None:
        modes[stick] = DIAL_READINGS[int(i) % len(DIAL_READINGS)]

    tip = ("How the {} stick reads as a dial (its axis:{}.* lanes): petal, the sector it "
           "points into gets the whole push; blend, neighbouring sectors crossfade as it "
           "sweeps round. The loadable patch's: saved with its routes.")
    for stick, side, _ in DIAL_SIDES:
        r.enum(dial_id(stick), f"{side.capitalize()} dial",
               lambda s=stick: DIAL_READINGS.index(modes[s]),
               lambda i, s=stick: set_mode(s, i),
               list(DIAL_READINGS), group="pad", modulatable=False,
               tip=tip.format(side, stick))

    def swap() -> None:
        left, right = r[dial_id("L")], r[dial_id("R")]
        a, b = left.value, right.value
        left.set(b)
        right.set(a)
    r.trigger("pad.dial.swap", "Swap dials", swap, group="pad", modulatable=False,
              tip="Swap the two sticks' dial readings, petal and blend.")


class MetaRegistry(Registry):
    """The meta controller's params, one set for every deck (plan 44 D3): the meta controller
    groups (`SHARED_META_GROUPS`, `SHARED_META_KEYS`) and the params of no part
    that only the meta controller declares (`app.restart`, the undo keys). Built by
    `build_meta`; each deck's `Registry` follows it (`Registry.follow`)
    and holds these `Param` objects by reference — a param added or removed
    here is added to or removed from every deck at once, in the order it
    came. A patch param is refused: it is a deck's."""

    # the launch readings of the sticks' dials ({"L": …, "R": …}; `app._dial_launch`), set
    # before any deck's registry is built: where each deck's start, and so the fresh values
    # a loadable patch naming none gets. None: `DIAL_SIDES`'s defaults
    dial_launch: dict[str, str] | None = None

    def __init__(self):
        super().__init__()
        self._decks: list[Any] = []       # weak references to the following registries

    def _follow(self, deck: Registry) -> None:
        import weakref
        self._decks.append(weakref.ref(deck))
        if self.on_air_reg is None:             # nobody named yet: the first deck, until one is
            self.on_air_reg = deck

    @property
    def decks(self) -> list[Registry]:
        """The live deck registries that follow this session, in the order
        they came."""
        live = [d for r in self._decks if (d := r()) is not None]
        if len(live) != len(self._decks):
            import weakref
            self._decks = [weakref.ref(d) for d in live]
        return live

    @property
    def on_air_reg(self) -> Registry | None:
        """The deck whose `apply` lands the meta controller's params, once a frame
        (review of #351, round 2): **named** — the deck on air, which
        `Deck.build(on_air=True)` (the host's one deck today) sets — held
        weakly; until one is named, the first deck that follows. A registry
        that follows and is not the lead (a stale deck a closure still
        holds, a scratch registry in a tool) never lands them. None: no
        deck — `apply` on the meta controller itself is then the one road."""
        ref = self.__dict__.get("_lead")
        return ref() if ref is not None else None

    @on_air_reg.setter
    def on_air_reg(self, deck: Registry | None) -> None:
        import weakref
        if deck is not None and deck.meta_reg is not self:
            raise ValueError("the lead is a deck that follows this meta registry")
        self.__dict__["_lead"] = weakref.ref(deck) if deck is not None else None

    def apply(self) -> None:
        """The meta controller's params landed from the meta controller itself (review of
        #351, round 2): under the frame's shared mark when a deck began one
        (`Registry.begin_frame` sets `landed`), so in the same frame as the
        lead's apply — before or after it — each param lands once; with no
        frame begun (no deck, a test) every one lands, as `Registry.apply`
        does. The lead's apply is the normal road; this one is for a host
        with no lead."""
        super().apply()

    def add(self, p: Param) -> Param:
        part = part_of(p)
        if part == "patch":
            raise ValueError(f"{p.id} is a performance param: a deck's, never the meta controller's")
        if part == PER_DECK_META:
            raise ValueError(f"{p.id} closes over one deck: each deck's own, never shared")
        decks = self.decks
        for d in decks:
            if p.id in d._p:
                raise ValueError(f"duplicate param id {p.id}")
        self._put(p)
        for d in decks:
            d._put(p)
        return p

    def remove(self, pid: str) -> Param | None:
        p = super().remove(pid)
        if p is not None:
            for d in self.decks:
                if d._p.get(pid) is p:
                    del d._p[pid]
                    d.serial += 1
        return p


# ---------------------------------------------------------------- builder

# plan 26 A2: camera.pan is in world units (the shape's unit circumradius),
# no longer logical px. A document saved since says so with this key (the
# schema stays preset/2: `load_doc` ignores keys it does not know, so an
# older build still loads the file — reading its pan as px); one without
# it is a preset/2 file from before, its pan read in px and converted
UNITS_KEY = "units"
# wave 0 T1: a route's depth onto an effect's `speed` or an `amount` param
# is measured along the param's taper (`fx.retaper_of`), where a document
# from before measured it along the linear range; `retaper_depths` reads
# the old file as it was, and this key says a document is already so
DEPTH_UNIT, DEPTH_TAPER = "fx.depth", "taper"
UNITS = {"camera.pan": "world", DEPTH_UNIT: DEPTH_TAPER}
PAN_IDS = ("camera.pan.x", "camera.pan.y")


def pan_world(doc: dict) -> tuple[dict, bool]:
    """A loadable patch document — a whole loadable patch (`preset.load_doc`) or a camera
    module preset (`Library._apply_doc`, `Library.defaults`) — with its
    camera.pan in world units (plan 26 A2):
    a file without the `units` key stored logical px, which become world
    units through the default eye on the 1080p screen
    (`geometry.pan_px_to_world`), so the shape sits where it did there.
    Only its values are converted: a route's or a desk row's depth and a
    macro base subscriber's from / to are fractions of the param's range
    (`Sub.at` lands a norm), and `params.PAN_RANGE` was chosen so that
    range reaches as far on that screen as the old ±4000 px did (±12 units,
    ±3888 px). Returns (a copy, whether anything changed); the document
    itself when it is already in world units or names no pan value."""
    units = doc.get(UNITS_KEY)
    # a hand-edited non-object `units` is no marker: the pan is read in px
    if isinstance(units, dict) and units.get("camera.pan") == "world":
        return doc, False
    values = doc.get("values")
    if not isinstance(values, dict) or not any(k in values for k in PAN_IDS):
        return doc, False
    out = copy.deepcopy(doc)
    changed = False
    for pid in PAN_IDS:
        v = out["values"].get(pid)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            new = pan_px_to_world(v)
            changed |= new != v
            out["values"][pid] = new
    return out, changed


# ---- wave 0 T1: a depth onto a retapered effect param, read as it was ----
#
# A route's depth is in the target's normalised units; the effects' `speed`
# and `amount` params were linear and are now on tapers (fx.T_SPEED,
# fx.amount_taper), so the same number means another real-unit change.
# Bases are stored in real units and are safe; the depths are not. A
# document without `units[DEPTH_UNIT]` had its depths measured along the
# linear range, and is converted here — at load (`LoadedPatch.load_doc`) and
# for good by tools/retaper_routes.py, which writes the marker.

_RETAPER_OPS = ("push", "position", "set")
# the row lists a document may hold: a loadable patch's or patch's `routes` and
# `desk`, a desk template's `desk`, the meta table's `bindings`
_ROW_SECTIONS = ("routes", "desk", "bindings")
_FALLBACK_FILES: dict | None = None


def fx_files(source=None) -> dict:
    """The effect specs to measure a document's depths against
    (`retaper_depths`): an `FxState`'s own `files`, or the one a registry
    declared from (`Registry.fx_state`, build_registry). With neither — a
    reader with no registry in hand, `Bindings.from_json`, `patches.read` — the
    shader folder as it ships (`fx.FX_DIR`), parsed **once** per process
    and kept; a test rig whose effects live elsewhere passes its own state."""
    global _FALLBACK_FILES
    files = getattr(source, "files", None)
    if files is None:
        files = getattr(getattr(source, "fx_state", None), "files", None)
    if files is not None:
        return files
    if _FALLBACK_FILES is None:
        _FALLBACK_FILES = FxState().files
    return _FALLBACK_FILES


def _number(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) \
        and math.isfinite(v) else None


def retaper_depths(doc: dict, files: dict) -> tuple[dict, list[str]]:
    """A document — a loadable patch, a patch, a desk template or the meta controller
    table — with every depth onto a retapered effect param (`fx.retaper_of`
    over `files`, `FxState.files`) measured along the param's taper, and
    marked so (`units[DEPTH_UNIT]`). Returns (the document, what moved —
    one line per row); the document itself when it is already marked. The
    rows are its ``routes``, ``desk`` and ``bindings`` lists and its macros'
    base subscribers. Each row's real-unit effect is kept where it can be:

    - a ``position`` row (and a ``set`` row's value, a norm): the real
      value the source lands at full throw is the same, so the new depth is
      that value's position on the taper. Exact at the top; below it the
      source is the param's new fader, as a position row means;
    - a ``push`` row: the real value a full push reaches **from the row's
      base** — the document's own value of the param, or the effect's
      default where it names none (a meta table always) — is the same,
      so the new depth is the taper distance from the base to that value.
      Exact at rest and at full push about that base; between the two, and
      from another base, the taper's curve stands in for the line. A push
      that over- or undershoots the range from that base (a negative push
      from a base of 0) keeps its sign and its overshoot: the part inside
      the range is converted and the part beyond it is carried over in
      norm as it was, so a depth is never written 0 for a row that had
      one — such a row is said "overshoots";
    - a macro's base subscriber on such a param: its ``from`` and ``to``
      are norms, and are moved as a position's depth is.

    Depth subscribers, ``scale`` and ``rest`` are multipliers or the
    source's and do not move. A row whose value is not a number is left."""
    units = doc.get(UNITS_KEY)
    if isinstance(units, dict) and units.get(DEPTH_UNIT) == DEPTH_TAPER:
        return doc, []
    out = copy.deepcopy(doc)
    values = out.get("values") if isinstance(out.get("values"), dict) else {}
    moved: list[str] = []
    probe = Param("", "", Kind.CONTINUOUS)

    def retapered(target):
        return fx.retaper_of(target, files) if isinstance(target, str) else None

    def new_norm(got, v: float) -> float:
        probe.taper = got[3]
        return probe._norm_of(v)

    def old_value(got, n: float) -> float:
        lo, hi = got[0], got[1]
        return lo + _clamp(n, 0.0, 1.0) * (hi - lo)

    def old_norm(got, v: float) -> float:
        lo, hi = got[0], got[1]
        return _clamp((v - lo) / (hi - lo), 0.0, 1.0)

    def rows(section):
        part = out.get(section)
        return [r for r in part if isinstance(r, dict)] if isinstance(part, list) else []

    for section in _ROW_SECTIONS:
        for row in rows(section):
            got = retapered(row.get("target"))
            op = row.get("op")
            if got is None or op not in _RETAPER_OPS:
                continue
            d = _number(row.get("value", 1.0))
            if d is None:
                continue
            target = row["target"]
            said = ""
            if op == "push":
                base = _number(values.get(target))
                base = got[2] if base is None else base
                at = old_norm(got, base)
                target_norm = at + d
                inside = _clamp(target_norm, 0.0, 1.0) - at      # the part within the range
                beyond = target_norm - _clamp(target_norm, 0.0, 1.0)   # the overshoot, as it was
                new = new_norm(got, old_value(got, at + inside)) - new_norm(got, base) + beyond
                about = f" about {base:g}"
                if beyond:
                    said = f" (overshoots the range by {beyond:+.3g} in norm: carried over)"
            else:
                new = new_norm(got, old_value(got, d))
                about = ""
            if new != d:
                row["value"] = new
                moved.append(f"{section} {row.get('source', '?')} → {target}: {op} {d:g} → "
                             f"{new:.4g}{about}{said}")
    macros = out.get("macros")
    for mid, macro in (macros.items() if isinstance(macros, dict) else ()):
        subs = macro.get("subs") if isinstance(macro, dict) else None
        for s in (subs if isinstance(subs, list) else ()):
            if not isinstance(s, dict) or "depth" in s:
                continue
            got = retapered(s.get("base"))
            if got is None:
                continue
            for key in ("from", "to"):
                n = _number(s.get(key, 0.0 if key == "from" else 1.0))
                if n is None:
                    continue
                new = new_norm(got, old_value(got, n))
                if new != n:
                    s[key] = new
                    moved.append(f"{mid} base {s['base']}: {key} {n:g} → {new:.4g}")
    units = out.get(UNITS_KEY)
    if not isinstance(units, dict):
        units = out[UNITS_KEY] = {}
    units[DEPTH_UNIT] = DEPTH_TAPER
    return out, moved


def _attr(obj, name):
    return (lambda: getattr(obj, name)), (lambda v: setattr(obj, name, v))


def _item(get_list, i):
    return (lambda: get_list()[i]), (lambda v: get_list().__setitem__(i, v))


# ---- plan 33 S: the switches' picks ----
SWITCH_GROUP = "switch"
# off, then the eight inputs (R11: choice k is the input `in<k>`)
SWITCH_CHOICES = ["off", *(str(i) for i in range(1, 9))]
_SWITCH_ID = re.compile(r"(switch(?:\.(?:[2-9]|[1-9][0-9]+))?)\.select")


def switch_id(name: str) -> str:
    """The `select` param of switch node `name` (`switch.2` → `switch.2.select`)."""
    return f"{name}.select"


def is_switch_id(pid: str) -> bool:
    """Is `pid` a switch's `select` — one that exists only while a loadable patch's
    graph holds that switch (plan 33 S)? A loadable patch load sorts such ids
    against the graph it lands, as it does an effect instance's."""
    return bool(_SWITCH_ID.fullmatch(pid))


def _switch_state(r: Registry) -> dict[str, int]:
    """The picks the `select` params write, switch name → 0–8: the view
    state's (`ViewState.switch`, which the renderer reads once a frame),
    kept by `build_registry` as `r.switch_state`; a dict of the registry's
    own for one built without a view (a test, a registry from before a hot
    reload brought the switch)."""
    state = getattr(r, "switch_state", None)
    if not isinstance(state, dict):
        state = r.switch_state = {}
    return state


def declare_switches(r: Registry, names: Iterable[str]) -> list[str]:
    """The switches' params (plan 33 S), as `FxState.set_instances` and
    `fx.declare` do the effect instances': `switch[.<n>].select` for each
    switch `names` holds — an enum off / 1–8 (`SWITCH_CHOICES`), off when
    first declared, group `switch` (a patch group: the loadable patch's),
    modulatable, so a route, a desk row, a macro, an LFO or a sequencer
    step drives it like any param — and those of every switch no longer
    named dropped (a route on one goes dormant, as for a deleted band). A
    switch still named keeps its pick. Returns the ids that appeared or
    went."""
    state = _switch_state(r)
    want = {switch_id(n): n for n in names}
    changed: list[str] = []
    for p in [p for p in r if p.group == SWITCH_GROUP and p.id not in want]:
        r.remove(p.id)
        state.pop(p.id[:-len(".select")], None)
        changed.append(p.id)
    for pid, name in want.items():
        if pid in r:
            continue
        state[name] = 0
        r.enum(pid, f"{name} select", (lambda n=name: int(state.get(n, 0))),
               (lambda v, n=name: state.__setitem__(n, int(v))), SWITCH_CHOICES,
               group=SWITCH_GROUP,
               tip=f"Which of {name}'s eight inputs it passes on (in1 … in8), or off: "
                   "the faces then show the pattern, the backdrop nothing. Only the "
                   "picked input's picture is made.")
        changed.append(pid)
    return changed


# ---- plan 34 Z: the resizes' values ----
RESIZE_GROUP = "resize"
_RESIZE_KEYS = ("size", "aspect", "fit", "filter", "crop_x", "crop_y", "crop_w", "crop_h")
_RESIZE_ID = re.compile(r"resize(?:\.(?:[2-9]|[1-9][0-9]+))?\.(size|aspect|fit|filter|crop_x"
                        r"|crop_y|crop_w|crop_h)")


def resize_ids(name: str) -> list[str]:
    """Resize node `name`'s params (`resize.2` → `resize.2.size` …), in order."""
    return [f"{name}.{k}" for k in _RESIZE_KEYS]


def is_resize_id(pid: str) -> bool:
    """Is `pid` one of a resize's values — one that exists only while a
    loadable patch's graph holds that resize (plan 34 Z)? A loadable patch load sorts such
    ids against the graph it lands, as it does a switch's `select`."""
    return bool(_RESIZE_ID.fullmatch(pid))


def _resize_state(r: Registry) -> dict[str, ResizeState]:
    """The states the resize params write, resize name → `ResizeState`: the
    view state's (`ViewState.resize`, which the renderer reads once a
    frame), kept by `build_registry` as `r.resize_state`; a dict of the
    registry's own for one built without a view (as `_switch_state`)."""
    state = getattr(r, "resize_state", None)
    if not isinstance(state, dict):
        state = r.resize_state = {}
    return state


_RESIZE_TIPS = {
    "size": "The long side {name} makes its picture at, in pixels: what comes after "
            "it (a delay, an effect) runs at that size.",
    "aspect": "{name}'s shape: its input's aspect, or square.",
    "fit": "How {name}'s crop is laid into its size: cover crops, contain "
           "letterboxes, stretch fills.",
    "filter": "How {name} samples its input: linear (mipmapped for a big "
              "reduction), or nearest — hard pixels.",
    "crop_x": "The centre of {name}'s crop across its input, 0 left … 1 right.",
    "crop_y": "The centre of {name}'s crop down its input, 0 top … 1 bottom.",
    "crop_w": "The width of {name}'s crop, a share of its input's.",
    "crop_h": "The height of {name}'s crop, a share of its input's.",
}


def declare_resizes(r: Registry, names: Iterable[str]) -> list[str]:
    """The resizes' params (plan 34 Z), as `declare_switches` does the
    switches': for each resize `names` holds, `size` (an enum over
    `RESIZE_SIDES`), `aspect`, `fit` and `filter` (enums), and the crop
    (`crop_x`, `crop_y` 0–1; `crop_w`, `crop_h` 0.01–1) — group `resize`
    (a patch group: the loadable patch's), modulatable — over a
    `ResizeState` made when first declared and kept while the name stays;
    those of every resize no longer named dropped, with their states.
    Returns the ids that appeared or went."""
    state = _resize_state(r)
    want = {n: resize_ids(n) for n in names}
    keep = {pid for ids in want.values() for pid in ids}
    changed: list[str] = []
    for p in [p for p in r if p.group == RESIZE_GROUP and p.id not in keep]:
        r.remove(p.id)
        changed.append(p.id)
    for name in [n for n in state if n not in want]:
        del state[name]
    enums = {"size": [str(s) for s in RESIZE_SIDES], "aspect": list(RESIZE_ASPECTS),
             "fit": list(RESIZE_FITS), "filter": list(RESIZE_FILTERS)}
    for name, ids in want.items():
        st = state.get(name)
        # (made only when missing — never by class: after a hot reload of
        # `view` a live state is the old class's, and its params, bound to
        # it, are kept below; replacing it would leave them writing a dead one)
        if st is None:
            st = state[name] = ResizeState()
        for pid, key in zip(ids, _RESIZE_KEYS, strict=True):
            if pid in r:
                continue
            label = f"{name} {key.replace('_', ' ')}"
            tip = _RESIZE_TIPS[key].format(name=name)
            if key in enums:
                r.enum(pid, label, *_attr(st, key), enums[key], group=RESIZE_GROUP, tip=tip)
            else:
                lo = 0.0 if key in ("crop_x", "crop_y") else 0.01
                r.continuous(pid, label, *_attr(st, key), lo=lo, hi=1.0,
                             group=RESIZE_GROUP, tip=tip)
            changed.append(pid)
    return changed


# ---- plan 39 T2: the mattes' values ----
MATTE_GROUP = "matte"
# `matte[.n].from` is the param; its state's field is `source` (`from` is a keyword)
_MATTE_KEYS = ("from", "key", "soft", "invert", "feather", "hue", "sat")
_MATTE_ATTR = {"from": "source"}
_MATTE_ID = re.compile(r"matte(?:\.(?:[2-9]|[1-9][0-9]+))?\.(" + "|".join(_MATTE_KEYS) + ")")


def matte_ids(name: str) -> list[str]:
    """Matte node `name`'s params (`matte.2` → `matte.2.from` …), in order."""
    return [f"{name}.{k}" for k in _MATTE_KEYS]


def is_matte_id(pid: str) -> bool:
    """Is `pid` one of a matte's values — one that exists only while a
    loadable patch's graph holds that matte (plan 39 T2)? A loadable patch load sorts such
    ids against the graph it lands, as it does a resize's."""
    return bool(_MATTE_ID.fullmatch(pid))


def _matte_state(r: Registry) -> dict[str, MatteState]:
    """The states the matte params write, matte name → `MatteState`: the
    view state's (`ViewState.mattes`, which the renderer reads once a
    frame), kept by `build_registry` as `r.matte_state`; a dict of the
    registry's own for one built without a view (as `_resize_state`)."""
    state = getattr(r, "matte_state", None)
    if not isinstance(state, dict):
        state = r.matte_state = {}
    return state


_MATTE_TIPS = {
    "from": "What makes a pixel of {name}'s picture pass: its brightness (luma), its "
            "own coverage (alpha), or how near its colour is to {name}'s hue (chroma).",
    "key": "Where a pixel of {name}'s picture starts to pass, 0–1: at or past it, it "
           "passes.",
    "soft": "The width of {name}'s edge either side of the key: 0 is hard, pass or not.",
    "invert": "{name} passes what it would not, and the other way round.",
    "feather": "A blur of {name}'s mask, in pixels: 0 keeps the edge as the key makes it.",
    "hue": "The colour {name} keys on in chroma, round the wheel (0 red, 0.33 green, "
           "0.67 blue).",
    "sat": "How saturated the colour {name} keys on in chroma is: 0 keys the greys.",
}


def declare_mattes(r: Registry, names: Iterable[str]) -> list[str]:
    """The mattes' params (plan 39 T2), as `declare_resizes` does the
    resizes': for each matte `names` holds, `from` (an enum over
    `MATTE_FROM`), `key` 0–1, `soft` 0–0.5, `invert`, `feather` 0–32 px and
    the chroma key's `hue` and `sat` (0–1) — group `matte` (a performance
    group: the loadable patch's), modulatable — over a `MatteState` made when first
    declared and kept while the name stays; those of every matte no longer
    named dropped, with their states. Returns the ids that appeared or went."""
    state = _matte_state(r)
    want = {n: matte_ids(n) for n in names}
    keep = {pid for ids in want.values() for pid in ids}
    changed: list[str] = []
    for p in [p for p in r if p.group == MATTE_GROUP and p.id not in keep]:
        r.remove(p.id)
        changed.append(p.id)
    for name in [n for n in state if n not in want]:
        del state[name]
    for name, ids in want.items():
        st = state.get(name)
        # (made only when missing — a live state is kept across a hot
        # reload of `view`, its params bound to it: `declare_resizes`')
        if st is None:
            st = state[name] = MatteState()
        for pid, key in zip(ids, _MATTE_KEYS, strict=True):
            if pid in r:
                continue
            label = f"{name} {key}"
            tip = _MATTE_TIPS[key].format(name=name)
            got = _attr(st, _MATTE_ATTR.get(key, key))
            if key == "from":
                r.enum(pid, label, *got, list(MATTE_FROM), group=MATTE_GROUP, tip=tip)
            elif key == "invert":
                r.toggle(pid, label, *got, group=MATTE_GROUP, tip=tip)
            else:
                hi = {"soft": 0.5, "feather": MATTE_FEATHER}.get(key, 1.0)
                r.continuous(pid, label, *got, lo=0.0, hi=hi, group=MATTE_GROUP, tip=tip)
            changed.append(pid)
    return changed


# ---- plan 39 T3: the cuts' values ----
CUT_GROUP = "cut"
_CUT_KEYS = ("invert", "amount")
_CUT_ID = re.compile(r"cut(?:\.(?:[2-9]|[1-9][0-9]+))?\.(" + "|".join(_CUT_KEYS) + ")")


def cut_ids(name: str) -> list[str]:
    """Cut node `name`'s params (`cut.2` → `cut.2.invert`, `cut.2.amount`)."""
    return [f"{name}.{k}" for k in _CUT_KEYS]


def is_cut_id(pid: str) -> bool:
    """Is `pid` one of a cut's values — one that exists only while a
    loadable patch's graph holds that cut (plan 39 T3)? A loadable patch load sorts such ids
    against the graph it lands, as it does a matte's."""
    return bool(_CUT_ID.fullmatch(pid))


def _cut_state(r: Registry) -> dict[str, CutState]:
    """The states the cut params write, cut name → `CutState`: the view
    state's (`ViewState.cuts`), kept by `build_registry` as `r.cut_state`; a
    dict of the registry's own for one built without a view (as
    `_matte_state`)."""
    state = getattr(r, "cut_state", None)
    if not isinstance(state, dict):
        state = r.cut_state = {}
    return state


_CUT_TIPS = {
    "invert": "{name} keeps the hole and cuts the rest: the picture shows where the mask "
              "does not pass.",
    "amount": "How far {name} cuts, 0–1: 1 cuts to nothing where the mask does not pass, "
              "0.5 dims it by half, 0 leaves the picture whole.",
}


def declare_cuts(r: Registry, names: Iterable[str]) -> list[str]:
    """The cuts' params (plan 39 T3), as `declare_mattes` does the mattes':
    for each cut `names` holds, `invert` (off) and `amount` 0–1 (1) — group
    `cut` (a patch group: the loadable patch's), both modulatable — over a
    `CutState` made when first declared and kept while the name stays;
    those of every cut no longer named dropped, with their states. Returns
    the ids that appeared or went."""
    state = _cut_state(r)
    want = {n: cut_ids(n) for n in names}
    keep = {pid for ids in want.values() for pid in ids}
    changed: list[str] = []
    for p in [p for p in r if p.group == CUT_GROUP and p.id not in keep]:
        r.remove(p.id)
        changed.append(p.id)
    for name in [n for n in state if n not in want]:
        del state[name]
    for name, ids in want.items():
        st = state.get(name)
        # (made only when missing — a live state is kept across a hot
        # reload of `view`, its params bound to it: `declare_mattes`')
        if st is None:
            st = state[name] = CutState()
        for pid, key in zip(ids, _CUT_KEYS, strict=True):
            if pid in r:
                continue
            label = f"{name} {key}"
            tip = _CUT_TIPS[key].format(name=name)
            got = _attr(st, key)
            if key == "invert":
                r.toggle(pid, label, *got, group=CUT_GROUP, tip=tip)
            else:
                r.continuous(pid, label, *got, lo=0.0, hi=1.0, group=CUT_GROUP, tip=tip)
            changed.append(pid)
    return changed


# ---- plan 39 T4: the segments' values ----
SEGMENT_GROUP = "segment"
_SEGMENT_KEYS = ("mode", "quality", "feather", "smooth", "on", "sense", "learn")
_SEGMENT_ID = re.compile(r"segment(?:\.(?:[2-9]|[1-9][0-9]+))?\.("
                         + "|".join(_SEGMENT_KEYS) + ")")


def segment_ids(name: str) -> list[str]:
    """Segment node `name`'s params (`segment.2` → `segment.2.mode` …), in order."""
    return [f"{name}.{k}" for k in _SEGMENT_KEYS]


def is_segment_id(pid: str) -> bool:
    """Is `pid` one of a segment's values — one that exists only while a
    loadable patch's graph holds that segment (plan 39 T4)? A loadable patch load sorts
    such ids against the graph it lands, as it does a cut's."""
    return bool(_SEGMENT_ID.fullmatch(pid))


def _segment_state(r: Registry) -> dict[str, SegmentState]:
    """The states the segment params write, segment name → `SegmentState`:
    the view state's (`ViewState.segments`), kept by `build_registry` as
    `r.segment_state`; a dict of the registry's own for one built without
    a view (as `_cut_state`)."""
    state = getattr(r, "segment_state", None)
    if not isinstance(state, dict):
        state = r.segment_state = {}
    return state


_SEGMENT_TIPS = {
    "mode": "What {name} takes for its foreground: a person (a model on the Neural "
            "Engine), what moves against a still camera (motion), or any subject (not in "
            "this build).",
    "quality": "The person model's level for {name}: fast (256×192 matte), balanced, or "
               "accurate (finer edges, slower results).",
    "feather": "A blur of {name}'s matte, in pixels: 0 keeps the model's own edge.",
    "smooth": "How much of {name}'s last matte each new one keeps, 0–1: against flicker, "
              "at the cost of a little more trail.",
    "on": "{name} cuts its picture: off, its foreground is the picture whole, its "
          "background and matte nothing, and its worker idle.",
    "sense": "Motion: how far a pixel of {name}'s picture must differ from the background "
             "it has learnt to be foreground, 0–1.",
    "learn": "Motion: how many seconds a still thing takes to fade into {name}'s "
             "background.",
}


def declare_segments(r: Registry, names: Iterable[str]) -> list[str]:
    """The segments' params (plan 39 T4), as `declare_cuts` does the cuts':
    for each segment `names` holds, `mode` (person / motion / subject, not
    modulatable: a model is not started per frame), `quality` (fast /
    balanced / accurate, not modulatable likewise), `feather` 0–32 px,
    `smooth` 0–1, `on`, and motion's `sense` 0–1 and `learn` 0.1–30 s —
    group `segment` (a patch group: the loadable patch's) — over a
    `SegmentState` made when first declared and kept while the name stays;
    those of every segment no longer named dropped, with their states.
    Returns the ids that appeared or went."""
    state = _segment_state(r)
    want = {n: segment_ids(n) for n in names}
    keep = {pid for ids in want.values() for pid in ids}
    changed: list[str] = []
    for p in [p for p in r if p.group == SEGMENT_GROUP and p.id not in keep]:
        r.remove(p.id)
        changed.append(p.id)
    for name in [n for n in state if n not in want]:
        del state[name]
    for name, ids in want.items():
        st = state.get(name)
        # (made only when missing — a live state is kept across a hot
        # reload of `view`, its params bound to it: `declare_cuts`')
        if st is None:
            st = state[name] = SegmentState()
        for pid, key in zip(ids, _SEGMENT_KEYS, strict=True):
            if pid in r:
                continue
            label = f"{name} {key}"
            tip = _SEGMENT_TIPS[key].format(name=name)
            got = _attr(st, key)
            if key in ("mode", "quality"):
                choices = SEGMENT_MODES if key == "mode" else SEGMENT_QUALITY
                r.enum(pid, label, *got, list(choices), group=SEGMENT_GROUP, tip=tip,
                       modulatable=False)
            elif key == "on":
                r.toggle(pid, label, *got, group=SEGMENT_GROUP, tip=tip)
            else:
                lo, hi = {"feather": (0.0, SEGMENT_FEATHER),
                          "learn": SEGMENT_LEARN}.get(key, (0.0, 1.0))
                r.continuous(pid, label, *got, lo=lo, hi=hi, group=SEGMENT_GROUP, tip=tip)
            changed.append(pid)
    return changed


# ---- plan 36 T4: the extra look-backs' values ----
# `lookback.<n>` (n ≥ 2) has its own ring and trail: `dream.<n>.<key>` for
# the look-back's own knobs (`lookback`'s are `dream.<key>`, as ever), in
# the look-back's group, declared while the loadable patch's graph holds the entry
_LOOKBACK_ID = re.compile(r"dream\.(?:[2-9]|[1-9][0-9]+)\.(" + "|".join(LOOKBACK_KEYS) + ")")


def is_lookback_knob(pid: str) -> bool:
    """Whether `dream.*` param `pid` is a look-back's — its ring and trail,
    `dream.<key>` or `dream.<n>.<key>` for a key of `LOOKBACK_KEYS` — not the
    dream node's own (plan 36 T4: `dream.on` gates the dream's alone)."""
    parts = pid.split(".")
    return parts[0] == "dream" and len(parts) >= 2 and is_lookback_key(parts[-1])


def lookback_ids(name: str) -> list[str]:
    """Look-back `name`'s own params (`lookback.2` → `dream.2.echo_mix` …),
    in order; `lookback`'s are the `dream.*` ones."""
    rest = name.partition(".")[2]
    return [f"dream.{rest}.{k}" for k in LOOKBACK_KEYS] if rest else [
        f"dream.{k}" for k in LOOKBACK_KEYS]


def is_lookback_id(pid: str) -> bool:
    """Is `pid` one of an extra look-back's values (`dream.<n>.<key>`, n ≥
    2) — one that exists only while a loadable patch's graph holds that look-back
    (plan 36 T4)? A loadable patch load sorts such ids against the graph it lands,
    as it does a resize's."""
    return bool(_LOOKBACK_ID.fullmatch(pid))


def _lookback_state(r: Registry) -> dict:
    """The states the extra look-backs' params write, look-back name →
    `DreamState`: the view state's (`ViewState.lookback`, which the
    renderer reads once a frame), kept by `build_registry` as
    `r.lookback_state`; a dict of the registry's own without one."""
    state = getattr(r, "lookback_state", None)
    if not isinstance(state, dict):
        state = r.lookback_state = {}
    return state


def declare_lookbacks(r: Registry, names: Iterable[str]) -> list[str]:
    """The extra look-backs' params (plan 36 T4), as `declare_resizes` does
    the resizes': for each `lookback.<n>` (n ≥ 2) `names` holds, its own
    echo brightness, fade, count, time apart, darken, contrast, shape-hides
    and detail (`dream.<n>.<key>`, bounds and defaults `dream.<key>`'s),
    group `dream`, over a `DreamState` made when first declared and kept
    while the name stays; those of every one no longer named dropped.
    Returns the ids that appeared or went."""
    state = _lookback_state(r)
    want = {n: lookback_ids(n) for n in names if n != "lookback"}
    keep = {pid for ids in want.values() for pid in ids}
    changed: list[str] = []
    for p in [p for p in r if is_lookback_id(p.id) and p.id not in keep]:
        r.remove(p.id)
        changed.append(p.id)
    for name in [n for n in state if n not in want]:
        del state[name]
    for name, ids in want.items():
        st = state.get(name)
        if st is None:
            st = state[name] = DreamState()
        for pid, key in zip(ids, LOOKBACK_KEYS, strict=True):
            if pid in r:
                continue
            base = r.get(f"dream.{key}")
            label = f"{name} {key.replace('_', ' ')}"
            tip = (f"{name}'s own: " + base.tip) if base is not None and base.tip else (
                f"{name}'s {key.replace('_', ' ')}.")
            if key == "res":
                r.enum(pid, label, *_attr(st, key), [str(v) for v in RES], group="dream",
                       modulatable=False, tip=tip)
            elif key == "echoes":
                r.continuous(pid, label, *_attr(st, key), lo=0, hi=MAX_ECHOES, integer=True,
                             group="dream", tip=tip)
            elif key == "fade":
                r.continuous(pid, label, *_attr(st, key), lo=FADE_LO, hi=FADE_HI, log=True,
                             group="dream", tip=tip)
            elif key == "gap":
                r.continuous(pid, label, *_attr(st, key), lo=GAP_LO, hi=GAP_HI,
                             group="dream", modulatable=False, tip=tip)
            elif key == "contrast":
                r.continuous(pid, label, *_attr(st, key), lo=0.5, hi=3.0, group="dream",
                             tip=tip)
            else:
                r.continuous(pid, label, *_attr(st, key), lo=0.0, hi=1.0, group="dream",
                             tip=tip)
            changed.append(pid)
    return changed


def dream_half_life(k: float) -> int:
    """`dream.k` as its readout: the processed frames in which a frame's
    share of the dream buffer halves, ``log ½ / log(1 − k)``, rounded (the
    buffer is ``D ← D·(1 − k) + frame·k``, dream.py). 23 at the slow end
    of the knob, 14 at the default, 2 at the fast end; never under 1, and 1
    for a value that is not a number (a readout must not raise mid-frame)."""
    k = float(k)
    if not math.isfinite(k):
        return 1
    k = min(max(k, 1e-6), 1.0 - 1e-9)
    return max(1, round(math.log(0.5) / math.log(1.0 - k)))


def dream_speed_text(k: float) -> str:
    """`dream.k`'s readout. Whole frames from ten up ("≈14 frames"); under
    ten, one decimal ("1.9 frames"), because whole frames read "≈2 frames"
    over nearly half the knob's travel at its fast end and an undo label
    said "≈2 frames → ≈2 frames". The same width either way."""
    k = float(k)
    if not math.isfinite(k):
        return "≈1 frames"
    k = min(max(k, 1e-6), 1.0 - 1e-9)
    h = max(1.0, math.log(0.5) / math.log(1.0 - k))
    return f"{h:.1f} frames" if h < 9.95 else f"≈{round(h)} frames"


def build_registry(view, control, audio, bank=None, dream=None, fx=None,
                   restart=None, ghost=None, media=None, *,
                   meta_reg: MetaRegistry | None = None) -> Registry:
    """Declare every parameter the surface owns.

    `audio` only needs a `.chain` attribute (tests pass a namespace); the
    chain is looked up on every access because a source attach replaces it.
    Its capture side is optional too: with `start_mic` / `stop` and a
    `devices` list (audio.AudioEngine) ``audio.mic`` and ``audio.device`` do
    something; without them they are declared anyway, so a key row (`M`)
    resolves with or without a panel. `dream` is the renderer's lookback
    state (lookback.DreamState); a fresh one stands in when there is no
    renderer, so the group is always declared; `fx` (fx.FxState, the
    renderer's effects' values) likewise, and `ghost` (ghost.GhostState, the
    renderer's ghost hands), and `media` (media.channels.MediaState, the
    eight channels the ``media.*`` params write; kept as ``r.media``, the
    one the loadable patch's bins and the renderer read). `bank` is the open project
    (library.Project), whose loadable patch slots the ``preset.*`` params
    load, save and cycle. `restart` is the host's request to
    restart the process (``app.restart``; app.py polls a flag) — a no-op
    without a host. Only the panel's own state (``ui.*``) is added by the
    panel once it exists.
    """
    if meta_reg is None:
        meta_reg = build_meta(control, audio, restart, media=media)
    return build_patch(view, bank, dream=dream, fx=fx, ghost=ghost, media=media,
                             meta_reg=meta_reg)


def build_meta(control, audio, restart=None, media=None) -> MetaRegistry:
    """Declare the meta controller's params once (plan 44 D3): the analyzer's (`master`,
    `scene`, `band` — the bands rebuilt on a layout change, `band.sel.*`
    the selected band's views), the audio transport, `app.restart` and the
    undo keys. What every deck shares by reference (`MetaRegistry`); the
    rest of the meta controller — the clock's, the hands', the outputs', the
    desk's, the panel's — is declared later on a deck's registry, which
    hands it here (`Registry.add`). `audio` only needs a `.chain` (see
    `build_registry`); `restart` is the host's restart request; `media` the
    meta controller's media sources (`media.channels.MediaSources`, or the deck's
    `Channels` that reads through them), whose mixer `audio.mix` listens to
    — none, a stand-in nobody feeds, and the toggle is not declared."""
    r = MetaRegistry()
    chain = lambda: audio.chain

    # ---- master faders ----
    g = "master"
    r.continuous("master.gain", "Audio drive",
                 lambda: chain().gain, lambda v: setattr(chain(), "gain", v),
                 taper=tapers.T_DRIVE, fmt=tapers.fmt_gain, group=g,
                 tip="Master gain on every analyzer band's fader, after the transfer stage. Only "
                     "does anything while a source is attached.")
    r.continuous("master.dyn", "Dynamics",
                 lambda: chain().dyn, lambda v: setattr(chain(), "dyn", v),
                 taper=tapers.T_DYN, fmt=tapers.fmt_gain, group=g,
                 tip="How much of the range a limiter took is put back. At 0 the chain is "
                     "a plain level follower; up to 1× it blends toward the moving window "
                     "and grows the expansion; past 1× only the expansion keeps growing.")
    r.continuous("master.trim", "Input trim",
                 lambda: chain().trim, lambda v: setattr(chain(), "trim", v),
                 taper=tapers.T_TRIM, fmt=tapers.fmt_db, group=g,
                 tip="One offset added to every analyzer band's trim, at the very head of the "
                     "chain — moves a whole song down into the 56 dB working window.")

    # ---- scene ----
    g = "scene"
    r.enum("scene.select", "Scene", lambda: control.scene, control.select_scene,
           control.scene_names, group=g,
           tip="The eleven factory scenes, re-tuned onto the analyzer's bands; the "
               "preset strip loads an analyzer file whole, layout included.")
    r.trigger("scene.reset_all", "Reset all", control.reset_all_clicked, group=g,
              tip="Reloads the selected scene across the whole analyzer. Undoable for 8 s.")

    # ---- bands ----
    # The analyzer has N bands (plan 07), so this block is a function: it
    # drops every band.* id and declares them again for the current N, and
    # runs whenever the layout changes (a band added, removed or moved, a
    # loadable patch's layout applied) — control.on_layout is that hook.
    shaper_tags = [s.tag for s in SHAPERS]
    curve_tags = [c.tag for c in CURVES]
    fmt_hz = lambda v: f"{v:.0f} Hz" if v < 1000 else f"{v / 1000:.2f} kHz"

    def band_params(prefix: str, idx: Callable[[], int], label_of: Callable[[str], str],
                    alias: bool = False):
        g = "band"
        # where the band listens: centre, Q and curve retune the analyzer in
        # place (weights recomputed, trackers keep running)
        r.continuous(f"{prefix}.f", label_of("Centre"),
                     lambda: chain().spec[idx()].f,
                     lambda v: chain().set_band(idx(), f=v),
                     lo=F_LO, hi=F_HI, log=True, fmt=fmt_hz, group=g, alias=alias,
                     tip="LOG, 20 Hz to 20 kHz. The band's centre frequency; the edges "
                         "follow from it and Q.")
        r.continuous(f"{prefix}.q", label_of("Q"),
                     lambda: chain().spec[idx()].q,
                     lambda v: chain().set_band(idx(), q=v),
                     lo=Q_LO, hi=Q_HI, log=True, fmt=lambda v: f"Q {v:.2f}", group=g,
                     alias=alias,
                     tip="LOG, 0.1 to 20. Centre over bandwidth: 1 is an octave-ish "
                         "band, 0.1 spans most of the spectrum, 20 is a sliver.")
        r.enum(f"{prefix}.curve", label_of("Curve"),
               lambda: chain().spec[idx()].curve,
               lambda c: chain().set_band(idx(), curve=c), curve_tags, group=g, alias=alias,
               tip="How the FFT bins between the edges are weighted: RECT is every "
                   "bin equally (the reference), the others taper toward the edges.")
        r.enum(f"{prefix}.fn", label_of("Transfer"),
               lambda: chain().params[idx()].fn,
               lambda fn: control.set_shaper(idx(), fn), shaper_tags, group=g, alias=alias)
        r.enum(f"{prefix}.norm", label_of("Normalise"),
               lambda: chain().params[idx()].norm,
               lambda v: setattr(chain().params[idx()], "norm", int(v)), NORMS,
               group=g, alias=alias, modulatable=False,
               tip="AUTO: the reference's adaptive window — it undoes a limiter, and "
                   "cancels most of a trim (a 6–12 dB cut can even drive harder). "
                   "MANUAL: no window; the trim is a plain gain and the band follows "
                   "its level, 1.0 at nominal.")
        for knob in tapers.KNOBS:
            r.continuous(
                f"{prefix}.{knob.key}", label_of(knob.label),
                (lambda k=knob.key: getattr(chain().params[idx()], k)),
                (lambda v, k=knob.key: setattr(chain().params[idx()], k, v)),
                taper=knob.t, fmt=knob.fmt, tip=knob.tip, group=g, alias=alias,
            )

    def build_bands():
        g = "band"
        r.remove_prefix("band.")
        r.enum("band.select", "Analyzer band", lambda: control.selb,
               lambda i: setattr(control, "selb", i), lambda: chain().band_names, group=g,
               persist=False, modulatable=False,
               tip="Which of the analyzer's bands has its strip open; the selected-band "
                   "targets (band.sel.*) follow it.")
        # structural: never lane-driven (they rebuild this very block)
        r.trigger("band.add", "Add analyzer band", control.add_band, group=g, modulatable=False,
                  tip="A new analyzer band in the widest gap between the others; it becomes "
                      "the open strip.")
        r.trigger("band.remove", "Remove analyzer band", control.remove_band, group=g,
                  modulatable=False, tip="Drops the open band. The last one stays.")
        r.trigger("band.reset", "Reset analyzer band", control.reset_band, group=g,
                  tip="Puts this band's whole strip back to the selected scene.")
        for i, name in enumerate(chain().band_names):
            band_params(f"band.{i}", (lambda i=i: i), lambda lb, b=name: f"{b} {lb}")
            r.trigger(f"band.{i}.reset", f"{name} reset",
                      lambda i=i: control.reset_band(i), group=g)
        # the selected band's strip: views onto band.{selb}.*, never saved or driven
        band_params("band.sel", lambda: control.selb, lambda lb: lb, alias=True)

    def real_of(p: Param) -> Param:
        if p.id.startswith("band.sel."):
            return r.get(f"band.{control.selb}.{p.id[9:]}") or p
        return p

    r.real_of = real_of
    build_bands()
    control.on_layout = build_bands

    # ---- audio transport (only what the engine exposes headlessly) ----
    g = "audio"

    def mic_on() -> bool:
        return bool(getattr(audio, "on", False) and getattr(audio, "mode", None) == "mic")

    def set_mic(on: bool) -> None:
        devices = getattr(audio, "devices", None) or []
        if on and devices and not mic_on():
            sel = min(max(int(getattr(audio, "device_sel", 0)), 0), len(devices) - 1)
            audio.start_mic(devices[sel]["index"])
        elif not on and mic_on():
            audio.stop()

    r.toggle("audio.mic", "Mic", mic_on, set_mic, group=g, persist=False,
             tip="Listen to the selected input device.")

    # plan 45 V3: the third source — the media mixer's sum, the videos' sound.
    # The mixer is the media sources' (plan 44 D3: shared, one for the room)
    def mix_on() -> bool:
        return bool(getattr(audio, "on", False) and getattr(audio, "mode", None) == "mix")

    def set_mix(on: bool) -> None:
        if on and not mix_on() and hasattr(audio, "start_mix"):
            audio.start_mix(media.live_mixer())
        elif not on and mix_on():
            audio.stop()

    # only with the host's media: a stand-in's mixer is fed by nobody, and
    # the toggle would "succeed" into silence for ever
    if media is not None:
        r.toggle("audio.mix", "Video sound", mix_on, set_mix, group=g, persist=False,
                 tip="Listen to the media mixer: the channels whose sound is on, summed "
                     "after their gains. Silent until a channel's sound is on; no input "
                     "device is opened.")
    r.enum("audio.device", "Input device",
           lambda: int(getattr(audio, "device_sel", 0)),
           lambda i: setattr(audio, "device_sel", int(i)),
           lambda: [("● " if d["loopback"] else "") + d["name"]
                    for d in (getattr(audio, "devices", None) or [])],
           group=g, persist=False, modulatable=False)
    if hasattr(audio, "rescan"):
        r.trigger("audio.rescan", "Rescan devices", audio.rescan, group=g, modulatable=False,
                  tip="Read the input device list again — for a driver or an interface "
                      "plugged in after launch.")
    r.trigger("app.restart", "Restart process",
              restart if restart is not None else (lambda: None), group="ui",
              modulatable=False,
              tip="Restart the process (Cmd+R). Full cold reload; view state is lost.")
    # undo and redo (undo.py, plan 15 WP1): key rows fire them (⌘Z / Ctrl+Z,
    # with ⇧ to redo), on the stack `undo.here` names; none installed: nothing
    r.trigger("edit.undo", "Undo", lambda: undo.undo(), group="ui", modulatable=False,
              tip="Take back the last gesture or the last load, learn or delete on the "
                  "deck the panel is on; with the mouse on a meta controller setting, or in the output, "
                  "audio, analyzer, hands or players section, the last meta controller change (Cmd+Z or Ctrl+Z). "
                  "After you come to a deck or a meta section it takes nothing back until "
                  "you change something there; after that it goes all the way down.")
    r.trigger("edit.redo", "Redo", lambda: undo.redo(), group="ui", modulatable=False,
              tip="Put back what the last undo took (Cmd+Shift+Z or Ctrl+Shift+Z). Not "
                  "straight after you come to a deck or a meta section, as Undo.")
    if hasattr(audio, "toggle_play"):
        r.toggle("audio.play", "Play",
                 lambda: bool(getattr(audio, "playing", False)),
                 lambda on: audio.toggle_play() if on != bool(audio.playing) else None,
                 group=g, persist=False, tip="Play / pause the loaded track.")
        r.trigger("audio.restart", "Restart track", audio.restart, group=g)
        r.trigger("audio.stop", "Stop source", audio.stop, group=g, modulatable=False)
    return r


def build_patch(view, bank=None, dream=None, fx=None, ghost=None, media=None, *,
                      meta_reg: MetaRegistry | None = None) -> Registry:
    """Declare a deck's own params (plan 44 D3): the look's — the view, the
    media channels' (`media`, the deck's `Channels`), the backdrop, the
    turn, the camera and the eye, the clouds' and the hands' looks, the
    look-back and the dream, the effects, the macros — and the bank's
    (`bank`, the show's loadable patch slots, which load into this deck), on a
    registry that follows `meta_reg` (the meta controller's params by reference: one
    `Param` in every deck). `meta_reg` None: a fresh one of its own. The
    other arguments are `build_registry`'s."""
    r = Registry(meta_reg=meta_reg if meta_reg is not None else MetaRegistry())
    dream = dream if dream is not None else DreamState()
    media = media if media is not None else media_channels.MediaState()
    r.media = media
    # plan 43 C2 (row 573): the view the rotation params write — what a
    # loadable patch's save reads the spin's pose from and its load sets it on
    # (`ViewState.pose` / `set_pose`; a registry from before is posed by none)
    r.view = view
    # plan 33 S: the switches' picks live on the view state the renderer
    # reads (`ViewState.switch`); their params come with the loadable patch's graph
    picks = getattr(view, "switch", None)
    if not isinstance(picks, dict):
        picks = {}
        try:
            view.switch = picks
        except AttributeError:            # (a view without the field: the registry's own)
            pass
    r.switch_state = picks
    # plan 52: the base chase, held. The deck's meta control, so every deck has
    # its own: a pad's BACK (the factory row) or a learned button presses it, and it is `Deck.chase`'s
    # road: `base_chase` with this deck's undo (`chase_undo`)
    r.toggle(CHASE_PARAM, "Base chase", lambda: r.chasing, lambda v: r.base_chase(bool(v)),
             group="deck", persist=False, modulatable=False,
             tip="While held, whatever the performers are doing to the look is written "
                 "into its values; let go and the look stays where they left it. One undo "
                 "step per hold.")
    # plan 34 Z: the resizes' values likewise (`ViewState.resize`)
    sizes = getattr(view, "resize", None)
    if not isinstance(sizes, dict):
        sizes = {}
        try:
            view.resize = sizes
        except AttributeError:            # (a view without the field: the registry's own)
            pass
    r.resize_state = sizes
    # plan 39 T2: the mattes' values likewise (`ViewState.mattes`)
    mattes = getattr(view, "mattes", None)
    if not isinstance(mattes, dict):
        mattes = {}
        try:
            view.mattes = mattes
        except AttributeError:            # (a view without the field: the registry's own)
            pass
    r.matte_state = mattes
    # plan 39 T3: the cuts' values likewise (`ViewState.cuts`)
    cuts = getattr(view, "cuts", None)
    if not isinstance(cuts, dict):
        cuts = {}
        try:
            view.cuts = cuts
        except AttributeError:            # (a view without the field: the registry's own)
            pass
    r.cut_state = cuts
    # plan 39 T4: the segments' values likewise (`ViewState.segments`)
    segments = getattr(view, "segments", None)
    if not isinstance(segments, dict):
        segments = {}
        try:
            view.segments = segments
        except AttributeError:            # (a view without the field: the registry's own)
            pass
    r.segment_state = segments
    # plan 36 T4: the extra look-backs' values likewise (`ViewState.lookback`)
    rings = getattr(view, "lookback", None)
    if not isinstance(rings, dict):
        rings = {}
        try:
            view.lookback = rings
        except AttributeError:            # (a view without the field: the registry's own)
            pass
    r.lookback_state = rings
    fmt_speed = lambda x: "stop" if x <= 0 else f"{x:.3f}" if x < 1 else f"{x:.2f}"

    # ---- view ----
    g = "view"
    r.enum("view.shape", "Shape", *_attr(view, "shape"), [s.name for s in SHAPES], group=g)
    r.continuous("view.bright", "Brightness", *_attr(view, "bright"),
                 taper=tapers.T_BRIGHT, fmt=tapers.fmt_gain, group=g)
    r.continuous("view.speed", "Speed", *_attr(view, "speed"),
                 taper=tapers.T_SPEED, fmt=fmt_speed, group=g)
    r.continuous("view.depth4", "4D depth", *_attr(view, "depth4"),
                 taper=tapers.T_DEPTH, fmt=lambda x: f"{x:.2f}", group=g)
    for p, name in enumerate(PLANES):
        r.toggle(f"view.plane.{name}", name, *_item(lambda: view.planes, p), group=g,
                 tip=f"Rotate in the {name} plane")
    r.toggle("view.points", "Points", *_attr(view, "points"), group=g)
    r.toggle("view.lines", "Lines", *_attr(view, "lines"), group=g)
    # plan 24 C2: a mix on the two layers that had none (decision 17), at 1
    # — the picture as it was (decision 24); patch params, modulatable
    r.continuous("view.points_alpha", "Points opacity", *_attr(view, "points_alpha"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"points {v:.2f}", group=g,
                 tip="The points' opacity: 1 draws them as they always were, 0 not at all.")
    r.continuous("view.lines_alpha", "Lines opacity", *_attr(view, "lines_alpha"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"lines {v:.2f}", group=g,
                 tip="The lines' opacity: 1 draws them as they always were, 0 not at all.")
    # plan 26 A2b (owner, 2026-10-14): off — strokes in world space, × the
    # zoom (main's picture, decision 24); on — screen space, A2's fixed
    # pixel weight. A performance switch like view.lines: in the loadable patch,
    # routable and modulatable
    r.toggle("view.screen_strokes", "Screen strokes", *_attr(view, "screen_strokes"),
             group=g,
             tip="Off: the edges and the dots are drawn in world space — they grow and "
                 "shrink with the shape as you zoom. On: screen space — they keep the "
                 "same pixel weight whatever the zoom.")
    r.toggle("view.faces", "Faces", *_attr(view, "faces"), group=g,
             tip="Translucent fills on the true 2-faces, under the wireframe. "
                 "First build per shape takes a moment (extraction is cached).")
    r.toggle("view.three_d", "3D", *_attr(view, "three_d"), group=g,
             tip="Hold the fourth dimension: a 4D shape keeps the 4D pose it has and "
                 "turns on as a rigid 3D body (XY, XZ, YZ); the W planes stop until it goes "
                 "off, and the shape goes on in 4D from where it is. A 3D shape has no W "
                 "planes either way.")
    r.toggle("view.cut_through", "Cut-through", *_attr(view, "cut_through"), group=g,
             tip="Overlay mode only: on, the translucent faces (and faint lines) cut the "
                 "window's alpha, so the screen behind the render window shows through "
                 "them; off, they draw over the ground and whatever layer is under them. "
                 "In window and fullscreen the picture is always opaque, on or off.")
    r.toggle("view.rotate", "Rotate", *_attr(view, "playing"), group=g)
    r.continuous("view.instances", "Instances", *_attr(view, "instances"),
                 taper=tapers.T_INSTANCES, lo=0, hi=tapers.T_INSTANCES.map(
                     tapers.T_INSTANCES.steps), integer=True,
                 fmt=lambda v: f"{int(v)} instance(s)" if int(v) > 0 else "0 · nothing drawn",
                 group=g,
                 tip="Synchronized copies, laid out as Layout says — one at a time to 64, "
                     "then faster to 4096. Scroll to zoom out over the field, right-drag "
                     "to pan; Fit frames it to the screen instead. 0 draws nothing: the "
                     "ground, the echoes and the effects carry on.")
    r.enum("view.inst_layout", "Layout", *_attr(view, "inst_layout"), INST_LAYOUT,
           group=g, tip="How the copies are laid out. Flat: a square grid, a honeycomb "
                        "growing from the centre, or one ring. 3D lattices, turned by the "
                        "camera's yaw and pitch: cubic, body-centred cubic, face-centred "
                        "cubic, hexagonal close-packed, stacked honeycombs (hex prism) "
                        "and diamond — neighbours one cell apart in each.")
    r.enum("view.inst_motion", "Field motion", *_attr(view, "inst_motion"), INST_MOTION,
           group=g, tip="Trigonometric motion over the field of copies — each copy's phase "
                        "comes from its place in the layout, so the field moves as one "
                        "figure.")
    r.continuous("view.inst_amp", "Field amp", *_attr(view, "inst_amp"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"amp {v:.2f}", group=g)
    r.continuous("view.inst_rate", "Field rate", *_attr(view, "inst_rate"), lo=0.0, hi=6.0,
                 fmt=lambda v: f"rate {v:.1f}", group=g)
    r.toggle("view.inst_fit", "Fit", *_attr(view, "inst_fit"), group=g,
             tip="Fit the field to the screen: every copy whole, none cut by the edge. A "
                 "grid or honeycomb takes the rows and columns that suit the screen and "
                 "fills it in even cells; zooming in snaps to whole cells and panning "
                 "moves a cell at a time. A ring or a lattice is framed whole and centred.")
    r.continuous("view.inst_spacing", "Spacing", *_attr(view, "inst_spacing"),
                 lo=0.5, hi=4.0, log=True, fmt=lambda v: f"spacing {v:.2f}", group=g,
                 tip="The room between neighbours, in cells: 1 is shoulder to shoulder; "
                     "below 1 the copies overlap. With Fit on, more room makes each copy "
                     "smaller in its cell.")
    r.continuous("view.inst_persp", "Field depth", *_attr(view, "inst_persp"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"depth {v:.2f}", group=g,
                 tip="A 3D lattice's own perspective: 0 every copy one size, 1 the "
                     "nearest copies drawn 2.5× the middle's. Nearer copies draw over "
                     "farther ones, which fade.")
    r.enum("view.pattern", "Pattern", *_attr(view, "pattern"), PATTERNS, group=g,
           tip="Face pattern — edit hyperspace/shaders/patterns.glsl while the app runs; "
               "it hot-reloads on save. Every pattern reads the same eight inputs: "
               + ", ".join(i.name for i in patterns.INPUTS) + ".")
    r.continuous("view.pattern_mix", "Pattern mix", *_attr(view, "pattern_mix"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"mix {v:.2f}", group=g)
    # plan 32 (row 331): the faces draw a media channel where the one
    # bitmap file was; alpha, size and path as the bitmap's were. Which
    # channel is the graph's wire into `pattern.media` (plan 33 T7: no
    # `view.media` — an old loadable patch's is read as that wire, `graphmigrate`)
    r.continuous("view.media_alpha", "Media alpha", *_attr(view, "media_alpha"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"media alpha {v:.2f}", group=g)
    # the default desk's knob 7 (apc40.DEFAULT_MAP, a fresh loadable patch's
    # desk) is `view.bmp_alpha`: kept as a view onto `view.media_alpha`, so
    # the row means what it always meant — the opacity of the picture on
    # the faces. An alias: never saved (a loadable patch writes view.media_alpha),
    # and an old loadable patch's value lands on the real one (LoadedPatch.load_doc)
    r.continuous(BMP_ALPHA, "Media alpha (knob 7)", *_attr(view, "media_alpha"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"media alpha {v:.2f}", group=g, alias=True,
                 tip="The factory desk's knob 7 from before plan 32: Media alpha.")
    r.aliases[BMP_ALPHA] = lambda p: r.get("view.media_alpha")
    r.continuous("view.media_scale", "Media size", *_attr(view, "media_scale"),
                 lo=0.05, hi=2.0, fmt=lambda v: f"media size {v:.2f}", group=g)
    r.enum("view.media_mode", "Media path", *_attr(view, "media_mode"), MEDIA_PATHS, group=g,
           tip="The media's own path about the face centre — independent of the "
               "instance-grid motion.")
    r.continuous("view.media_amp", "Media amp", *_attr(view, "media_amp"), lo=0.0, hi=0.5,
                 fmt=lambda v: f"amp {v:.2f}", group=g)
    r.continuous("view.media_rate", "Media rate", *_attr(view, "media_rate"), lo=0.0, hi=6.0,
                 fmt=lambda v: f"rate {v:.1f}", group=g)
    # the face pattern's eight inputs — what the shaders read as u_mod[8],
    # named by the convention in patterns.py (SCALE GLOW WARP SPEED COLOUR
    # SHARP HUE SPREAD). Base 1.0 is the un-driven look; a routed lane rides on it.
    for k in range(len(view.pattern_mod)):
        r.continuous(f"pattern.mod.{k}", patterns.label(k),
                     *_item(lambda: view.pattern_mod, k), lo=0.0, hi=2.6,
                     fmt=lambda v: f"{v:.2f}", group="pattern", tip=patterns.tip(k))

    # ---- the media channels (plan 32 C, media/channels.py): the bin entry
    # on each, how it fits a frame, and its transport — all performance,
    # all routable; the bins themselves are the loadable patch's `media` section ----
    g = "media"
    fmt_rate = lambda v: "hold" if v == 0 else f"×{v:.2f}"
    for c, ch in media.channels.items():
        r.continuous(f"media.{c}.slot", f"{c.upper()} slot", *_attr(ch, "slot"),
                     lo=0, hi=media_channels.BIN - 1, integer=True,
                     fmt=lambda v: f"slot {int(v) + 1}", group=g,
                     tip="Which of the channel's sixteen bin entries is on it; an empty "
                         "entry, or a source not on this Mac, is black.")
        r.enum(f"media.{c}.fit", f"{c.upper()} fit", *_attr(ch, "fit"),
               list(media_channels.FITS), group=g,
               tip="How the picture fills a frame of another shape: cover crops, "
                   "contain letterboxes, stretch distorts.")
        r.continuous(f"media.{c}.rate", f"{c.upper()} rate", *_attr(ch, "rate"),
                     lo=-4.0, hi=4.0, fmt=fmt_rate, group=g,
                     tip="× the clip's own speed; negative plays backwards, 0 holds. "
                         "On a live feed, 0 freezes the frame.")
        r.continuous(f"media.{c}.pos", f"{c.upper()} position", *_attr(ch, "pos"),
                     lo=0.0, hi=1.0, fmt=lambda v: f"pos {v:.3f}", group=g,
                     tip="The scrub: while it moves the playhead is put there; when it "
                         "rests the clip plays on at the rate from where it was left.")
        r.continuous(f"media.{c}.jog", f"{c.upper()} jog", *_attr(ch, "jog"),
                     lo=-1.0, hi=1.0, fmt=lambda v: f"jog {v:+.2f}", group=g,
                     tip="A push of playhead speed that coasts back to the rate, like a "
                         "platter spun and let go — learn a relative encoder (the cue "
                         "knob) to it.")
        r.enum(f"media.{c}.loop", f"{c.upper()} loop", *_attr(ch, "loop"), list(MEDIA_LOOPS),
               group=g, tip="At the clip's end: loop, play back (pingpong), or hold the "
                            "last frame (once).")
        r.toggle(f"media.{c}.audio", f"{c.upper()} audio", *_attr(ch, "play_audio"), group=g,
                 tip="Play the video's own sound, read at the playhead (plan 45). Forward "
                     "play only for now, with an occasional click; other rates stutter.")
        r.continuous(f"media.{c}.gain", f"{c.upper()} gain", *_attr(ch, "gain"),
                     taper=tapers.T_MEDIA_GAIN, fmt=tapers.fmt_level, group=g,
                     tip="The channel's sound level, off to +6 dB; unity at the notch.")

    # ---- the backdrop (plan 32 R, row 330): a picture under the scene ----
    # (which is the graph's wire into `backdrop.image`: plan 33 T7 retired
    # `backdrop.channel`, an old loadable patch's read as that wire; plan 35 T3
    # retired `backdrop.history` likewise — what the look-back records is
    # the wire into `lookback.capture`, `graphmigrate.RETIRED`)
    g = "backdrop"
    r.continuous("backdrop.alpha", "Backdrop alpha", *_attr(view, "backdrop_alpha"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"backdrop {v:.2f}", group=g)

    # ---- rotation: per-plane rate and phase ----
    # rate multiplies dt·speed·RATE[p]; signed so a lane can spin a plane
    # backwards, and as wide as the reference's plane drive (ROT_RATE_MAX).
    # phase is the integrated angle, folded to one turn: not a base (it moves
    # every frame: no undo step, no dirty dot) but a modulation target — a
    # lane adds a phase offset on top of the integrator. Plan 43 C2 (row
    # 573): a loadable patch saves the pose under these ids all the same
    # (`POSE_IDS`, `ViewState.pose`) and its load sets the turn there.
    g = "rot"
    fold = lambda a: math.remainder(a, 2 * math.pi)   # ±π stay put, the rest folds
    for p, name in enumerate(PLANES):
        r.continuous(f"rot.rate.{name}", f"{name} rate", *_item(lambda: view.rate, p),
                     lo=-ROT_RATE_MAX, hi=ROT_RATE_MAX, fmt=lambda v: f"{v:+.2f}×", group=g,
                     tip=f"Rotation rate multiplier for the {name} plane; negative reverses. "
                         "Route an audio lane here (routing.py) to drive the plane.")
    for p, name in enumerate(PLANES):
        r.continuous(f"rot.phase.{name}", f"{name} phase",
                     (lambda p=p: fold(view.ang[p])),
                     (lambda v, p=p: view.ang.__setitem__(p, v)),
                     lo=-math.pi, hi=math.pi, wrap=True,
                     fmt=lambda v: f"{math.degrees(v):.0f}°", group=g, persist=False,
                     tip=f"Where the {name} plane is in its turn right now.")

    # the 4D spin back to its origin (2026-10-14, the pad's right-stick click):
    # the W planes' rates to 0 through their params (a modulated rate's base
    # too) and their angles to 0, as camera.reset zeroes them all
    w_planes = [(p, name) for p, name in enumerate(PLANES) if name.endswith("W")]

    def reset_w():
        for p, name in w_planes:
            r[f"rot.rate.{name}"].set(0.0)
            view.ang[p] = 0.0
        view.body = None            # the pose the 3D switch folded in (plan 28)

    r.trigger("rot.reset_w", "Reset 4D spin", reset_w, group=g,
              tip="Stop the XW, YW and ZW planes (rate 0) and turn them back to 0°: "
                  "the shape's 4D pose at its origin. The other planes keep turning.")

    # ---- camera ----
    g = "camera"
    # the field of thousands needs far more zoom-out than one shape did: a
    # 4096-copy grid at spacing 4 stands 184 screens tall, and 0.005 frames
    # it (2026-10-21). The ends are geometric about 1×, so the knob's middle,
    # a fader at noon and a level hand all sit at 1× — and the range's span
    # (log: 0.005 … 200, 15.3 octaves) is the unit a push's depth is measured
    # in, so the depths onto zoom moved with it (loadable.py)
    r.continuous("camera.zoom", "Zoom", *_attr(view, "zoom"), lo=0.005, hi=200.0, log=True,
                 fmt=lambda v: f"{v:.2f}×" if v >= 0.1 else f"{v:.3f}×", group=g)
    r.continuous("camera.yaw", "Yaw", *_attr(view, "yaw"), lo=-math.pi, hi=math.pi,
                 wrap=True, fmt=lambda v: f"{math.degrees(v):.0f}°", group=g)
    # pitch wraps like yaw (2026-10-14): the camera is a turn of the points,
    # with no up vector to flip, so tumbling over the top is just more turn
    r.continuous("camera.pitch", "Pitch", *_attr(view, "pitch"), lo=-math.pi, hi=math.pi,
                 wrap=True, fmt=lambda v: f"{math.degrees(v):.0f}°", group=g)
    # plan 26 A2: zoom and pan are the shape's world scale and position
    # (geometry.model_matrix) — the hands stay where the performer is and
    # only the shape grows or moves. Pan is in world units, the shape's
    # unit circumradius (y positive down, as it always was); a preset/2
    # file's px are converted at load (params.pan_world)
    for i, axis in enumerate("xy"):
        r.continuous(f"camera.pan.{axis}", f"Pan {axis.upper()}", *_item(lambda: view.pan, i),
                     lo=-PAN_RANGE, hi=PAN_RANGE, fmt=lambda v: f"{v:+.2f}", group=g,
                     tip="Where the shape sits in the world, in shape radii (the "
                         "shape's own size): x right, y down. The hands do not move.")

    def reset_view():
        view.ang = [0.0] * 6
        view.body = None            # the pose the 3D switch folded in (plan 28)
        view.yaw = view.pitch = 0.0
        view.zoom, view.pan = 1.0, [0.0, 0.0]

    r.trigger("camera.reset", "Reset view", reset_view, group=g,
              tip="Reset rotation phases, orbit, zoom and pan.")

    # ---- the eye (plan 26 A2): the one fixed camera the shape and the
    # hands drawn in the scene are seen through. Plan 43 C2 (the owner,
    # 2026-11-02, rows 555, 574): the loadable patch's, part of the one orbit
    # camera with `camera.*` — a load lands it like any look value — and
    # modulatable: a lane breathes the framing (row 182's objection, that
    # a lane would swing the whole room, went with the eye leaving the
    # room). The defaults are the old 3D divide, so the shape lands where
    # it always did; the hands' calibration is fitted to those defaults,
    # the meta controller's reference eye, never to this one (`ghost.calibration`)
    g = "eye"
    r.continuous("eye.fov", "Eye field of view", *_attr(view, "eye_fov"),
                 lo=EYE_FOV_RANGE[0], hi=EYE_FOV_RANGE[1],
                 fmt=lambda v: f"{v:.1f}°", group=g,
                 tip="How wide the eye sees, across the shorter side of the picture. "
                     f"Wider shows more of the world, smaller; {EYE_FOV:.1f}° is the "
                     "view the shape was always drawn in. The preset's: a lane on it "
                     "breathes the framing.")
    r.continuous("eye.distance", "Eye distance", *_attr(view, "eye_distance"),
                 lo=EYE_DISTANCE_RANGE[0], hi=EYE_DISTANCE_RANGE[1], log=True,
                 fmt=lambda v: f"{v:.2f}", group=g,
                 tip="How far the eye stands from the centre of the world, in shape "
                     "radii. Nearer: a stronger perspective and a bigger shape. "
                     f"{EYE_DISTANCE:.2f} is the view the shape was always drawn in.")

    # ---- the point clouds (plan 26 A4b): how a cloud device's points are
    # drawn in the shared camera (graph.PointCloud). Meta controller, like the
    # hands' look: a cloud is the room's sensor, and a loadable patch load never
    # changes how it is shown. Nothing reads them until a `cloud` device
    # is listed, so they move no picture of today's
    g = "cloud"
    r.continuous("cloud.size", "Cloud point size", *_attr(view, "cloud_size"),
                 lo=0.5, hi=12.0, fmt=lambda v: f"{v:.1f} px", group=g,
                 tip="Each point's radius on screen, in pixels, whatever its depth.")
    r.continuous("cloud.scale", "Cloud scale", *_attr(view, "cloud_scale"),
                 lo=0.01, hi=10.0, log=True, fmt=lambda v: f"{v:.2f}×", group=g,
                 tip="The cloud's own units in the world's (the shape's radius is 1), "
                     "about the world's centre.")
    r.continuous("cloud.bright", "Cloud brightness", *_attr(view, "cloud_bright"),
                 lo=0.0, hi=2.0, fmt=lambda v: f"{v:.2f}", group=g,
                 tip="The points' colour × this; 0 draws them black (they still hide "
                     "what is behind them).")
    r.toggle("cloud.colors", "Cloud colours", *_attr(view, "cloud_colors"), group=g,
             modulatable=False,
             tip="The cloud's own colours, when its source has them; off, every point "
                 "is white.")

    # ---- look-back: the frame history composited over the scene ----
    # lookback.py reads these every frame; the dream worker (WP6b) reads
    # the second half. Cadence and size rebuild the ring, so no lane drives
    # them; everything else is a live fader.
    g = "dream"
    # the labels are the LOOKBACK page's sections (ui_lookback.py): "Echo …"
    # acts on the echoes, "Dream …" on the dream buffer, and the rest on both
    # (plan 20 WP4). Each tip opens with what the knob does.
    # plan 36 T4 (W4): the dream node's own — a look-back drawn is on
    r.toggle("dream.on", "Dream on", *_attr(dream, "on"), group=g,
             tip="The dream, on or off: on, the dream node dreams its picture (once a "
                 "worker is attached); off, it passes the picture through untouched "
                 "and the worker sleeps.")
    r.continuous("dream.mix", "Dream brightness", *_attr(dream, "mix"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"{v:.2f}", group=g,
                 tip="How bright the dream is over its picture: the dream buffer's "
                     "weight, laid over what the dream node takes in.")
    r.continuous("dream.echo_mix", "Echo brightness", *_attr(dream, "echo_mix"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"{v:.2f}", group=g,
                 tip="How bright the newest echo is; older ones fade from it by the "
                     "fade time. An echo is a copy of an earlier frame, drawn faintly "
                     "under this one — together they are the trail a moving shape leaves.")
    r.continuous("dream.fade", "Echo fade time", *_attr(dream, "fade"), lo=FADE_LO, hi=FADE_HI,
                 log=True, fmt=lambda v: f"{v:.2f} s", group=g,
                 tip="How long the trail lasts: an echo halves in brightness every this "
                     "many seconds of its age, whatever the screen's frame rate "
                     "(0.23 s is the old 0.95 a frame at 60 Hz; 0.76 s is 0.985).")
    r.continuous("dream.darken", "Darken", *_attr(dream, "darken"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"×{1.0 - v:.2f}", group=g,
                 tip="Darkens echoes and dream alike: how much darker the wake is than "
                     "the frames it came from.")
    r.continuous("dream.contrast", "Contrast", *_attr(dream, "contrast"), lo=0.5, hi=3.0,
                 fmt=lambda v: f"^{v:.2f}", group=g,
                 tip="Above 1 only the bright parts of the echoes and the dream show: a "
                     "power curve on every layer of the wake.")
    r.continuous("dream.occlude", "Shape hides wake", *_attr(dream, "occlude"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"{v:.2f}", group=g,
                 tip="At 1 the shape covers the echoes and the dream behind it, so the "
                     "tracers only fill the space between; at 0 they glow through it.")
    # the dream buffer's chroma — the net paints in its own primaries; these
    # re-colour D on its way into the composite (lookback.py, chroma())
    r.continuous("dream.hue", "Dream hue", *_attr(dream, "hue"), lo=-180.0, hi=180.0,
                 wrap=True, fmt=lambda v: f"{v:+.0f}°", group=g,
                 tip="Turns the dream's own colours about the grey axis; luminance is "
                     "kept. The echoes are not re-coloured.")
    r.continuous("dream.sat", "Dream saturation", *_attr(dream, "sat"), lo=0.0, hi=2.0,
                 fmt=lambda v: f"sat {v:.2f}", group=g,
                 tip="0 a grey dream, 1 as the net painted it, above that pushed.")
    r.continuous("dream.tint", "Dream tint", *_attr(dream, "tint"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"tint {v:.2f}", group=g,
                 tip="Crosses the dream's colours into one colour: at 1, its luminance "
                     "in the tint colour — the one chosen, or the scene's own hue.")
    r.enum("dream.tint_from", "Dream tint from", *_attr(dream, "tint_from"), TINT_FROM, group=g,
           tip="The tint's colour: the one chosen (tint hue, tint sat), or the hue of "
               "the scene's mean colour this frame.")
    r.continuous("dream.tint_hue", "Dream tint hue", *_attr(dream, "tint_hue"), lo=0.0, hi=360.0,
                 wrap=True, fmt=lambda v: f"{v:.0f}°", group=g,
                 tip="The chosen tint colour's hue; unused while the tint is from the scene.")
    r.continuous("dream.tint_sat", "Dream tint sat", *_attr(dream, "tint_sat"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"sat {v:.2f}", group=g,
                 tip="The chosen tint colour's saturation: 0 tints grey — a greyscale dream.")
    r.continuous("dream.echoes", "Echo count", *_attr(dream, "echoes"), lo=0, hi=MAX_ECHOES,
                 integer=True, fmt=lambda v: f"{int(v)}", group=g,
                 tip="How many echoes are drawn; at 0 only the dream is. With time "
                     "apart it sets how far back the trail reaches: count × time apart "
                     "seconds.")
    r.continuous("dream.gap", "Echo time apart", *_attr(dream, "gap"), lo=GAP_LO, hi=GAP_HI,
                 fmt=lambda v: f"{v * 1000:.0f} ms", group=g, modulatable=False,
                 tip="The time between one echo and the next, in milliseconds, whatever "
                     "the frame rate: short is a smear, long a row of separate copies "
                     "(33 ms is every 2nd frame at 60 Hz, 67 ms every 4th; 0 is every "
                     "frame).")
    r.enum("dream.res", "Look-back detail", *_attr(dream, "res"), [str(v) for v in RES], group=g,
           modulatable=False,
           tip="The size, in pixels, the echoes and the dream are kept at (the short "
               "side; the picture's aspect is kept); a change starts the trail again.")
    # the worker's (WP6b) — loadable patches carry them from day one
    r.continuous("dream.steps", "Dream passes", *_attr(dream, "steps"), lo=1, hi=3, integer=True,
                 fmt=lambda v: f"{int(v)}", group=g,
                 tip="Passes through the net per frame: more is a deeper dream and a "
                     "slower worker; 1 flickers.")
    r.continuous("dream.step", "Dream strength", *_attr(dream, "step"), lo=0.005, hi=0.06,
                 fmt=lambda v: f"{v:.3f}", group=g,
                 tip="How hard the dream is pushed each pass; too hard for the speed and "
                     "it is held back (the status line says 'step clamped'): strength × "
                     "passes is kept at or under 1.5 × k (the speed's value).")
    # the dream's "speed" is its one time constant (plan 20 WP5, fork F8): the
    # share of the newest frame blended into the buffer each processed frame
    r.continuous("dream.k", "Dream speed", *_attr(dream, "k"), lo=0.03, hi=0.3,
                 fmt=dream_speed_text, group=g,
                 tip="How fast the dream follows the picture: fast, it keeps up and lets "
                     "go of what has left; slow, it lags, lingers and grows deeper. In "
                     "dream frames, so it also follows the worker's rate. Slower than "
                     "about 17 frames at the default strength, the strength is held back "
                     "(the status line says 'step clamped'). The readout is the frames in "
                     "which a frame's share of the dream halves; the value is k, the share "
                     "of each new frame blended in.")
    r.enum("dream.layer", "Dream layer", *_attr(dream, "layer"), LAYERS, group=g,
           modulatable=False,      # a change makes the worker load another trunk
           tip="Which layer of which net the dream brings out: every conv layer of VGG16 "
               "and every block of GoogLeNet. Shallow layers draw fine dots and edges, "
               "middle ones textures and swirls, deep ones larger blobs, eyes and "
               "object-like parts; the deepest are slower. The first layer used from a "
               "net loads that net, which takes a moment; the rest of it are then "
               "instant.")
    r.enum("dream.octaves", "Dream scales", *_attr(dream, "octaves"), OCTAVES, group=g,
           tip="The sizes the dream is worked at, in turn, one a frame: more gives "
               "larger forms for the same cost.")
    r.continuous("dream.mask_decay", "Dream linger", *_attr(dream, "mask_decay"),
                 lo=0.9, hi=0.995, fmt=lambda v: f"{v:.3f}", group=g,
                 tip="How long the dream stays where the shape was after it has left: "
                     "the content mask's per-frame decay, 10 to 200 frames. The mask "
                     "decides where the dream may exist; what covers it is Shape hides "
                     "wake.")
    r.continuous("dream.jitter", "Dream jitter", *_attr(dream, "jitter"), lo=0, hi=16,
                 integer=True, fmt=lambda v: f"{int(v)} px", group=g,
                 tip="A random shift each pass, in pixels, that turns pixel noise into "
                     "texture.")

    # ---- effects: one param per annotated uniform in shaders/fx/*.glsl ----
    # (fx.py). A file edited into a new shape re-declares its own ids.
    fx = fx if fx is not None else FxState()
    declare_fx(r, fx)
    fx.on_specs = lambda names: declare_fx(r, fx, names)
    # the effects' state the fx.* params write, for whoever declares more:
    # a loadable patch's graph holding an effect twice (plan 26 A4,
    # loadable.GraphSection — `fx.acid.2.*`)
    r.fx_state = fx
    # the ghost hands' display (ghost.py; the renderer's Ghost.state)
    declare_ghost(r, ghost if ghost is not None else GhostState())
    declare_dial(r)                     # the sticks' dial readings, this deck's

    # ---- macros: the chaining knobs (plan 09, decision 7) ----
    # Nothing reads a macro but the router, through the macro's subscribers
    # (routing.Macro, plan 13 §2.4): a base subscriber follows the macro's
    # base, a depth subscriber its effective value — so a hand that
    # positions macro.2 deepens the routes macro.2 subscribes, one frame
    # later, rather than two performers pulling on one param. No object,
    # so the values live in this list, and the slot clamps itself (a
    # restore writes raw). Base 1: a route that names an untouched macro
    # runs at its full depth, the same as "× 1".
    g = "macro"
    macros = [1.0] * N_MACROS
    for k in range(N_MACROS):
        r.continuous(f"macro.{k + 1}", f"Macro {k + 1}", (lambda k=k: macros[k]),
                     (lambda v, k=k: macros.__setitem__(k, _clamp(float(v), 0.0, 1.0))),
                     lo=0.0, hi=1.0, fmt=lambda v: f"{v * 100:.0f} %", group=g,
                     tip="Does nothing on its own: it acts through its subscribers — "
                         "each sets a param's base or scales a route's depth, over its "
                         "own from → to. Own it with a hand or LFO to ride the depths.")

    # ---- the loadable patch bank ----
    if bank is not None:                   # library.Project: the bank of loadable patch names
        g = "preset"
        names = lambda: [n or f"SLOT {k + 1}" for k, n in enumerate(bank.bank)]
        # active is −1 until a loadable patch loads: no choice selected, no LED lit
        # meta-controls: they *apply* loadable patches, so no loadable patch stores them
        # every slot is a choice (plan 19 WP1: twenty-four); `has` says
        # which hold a loadable patch, for a pad's "filled" light
        r.enum("preset.select", "Preset", lambda: bank.lit, bank.load_slot, names,
               group=g, persist=False, modulatable=False,
               has=lambda k: 0 <= k < len(bank.bank) and bank.bank[k] is not None,
               # a pad held on an empty slot saves the live state into it
               # (2026-10-09, replacing the clip-stop SAVE AS bar); a filled
               # slot held only loads — the press loaded it
               held=bank.save_empty,
               # SAVE held and a pad tapped (plan 24 C1): a new loadable patch into
               # that slot, filled or empty; the old loadable patch stays listed
               save_into=bank.save_into,
               tip="The show's twenty-four pads: the desk's clip rows 1, 4 and 5, the "
                   "first eight on F1–F8. Each one points at a preset — the whole "
                   "performance: the look, its routes, its LFOs and macros, never the "
                   "tempo, the hands or the analyzer. Hold SAVE (track 8's clip stop) "
                   "and tap a pad to save the live state into it as a new preset, or "
                   "hold an empty pad. A pad always loads into the deck off air and never "
                   "touches the room; it is lit for what that deck holds. The panel's "
                   "own load goes to the deck the panel is on.")
        # the F-keys' slots have a load and a save trigger each; slots past
        # them are reached through `preset.select` and the page (plan 19
        # fork 1: no params added)
        for k in range(min(len(bank.bank), F_KEYS)):
            r.trigger(f"preset.load.{k}", f"Load preset {k + 1}",
                      lambda k=k: bank.load_slot(k), group=g,
                      tip=f"Load pad {k + 1}'s preset into the deck off air (F{k + 1}). "
                          "The room does not move.")
            r.trigger(f"preset.save.{k}", f"Save preset {k + 1}",
                      lambda k=k: bank.save_slot(k), group=g, modulatable=False)
        # save-as into the next empty slot (plan 15 WP4): no desk row any
        # more, learnable onto a pad button, never a loadable patch's row (row 752)
        r.trigger("preset.save_new", "Save as a new preset", bank.save_new,
                  group=g, modulatable=False,
                  tip="Save the live state as a new preset, named from the loaded "
                      "one (moo → moo 2), into the next empty pad. It never "
                      "overwrites a preset. On the desk, hold SAVE (track 8's clip "
                      "stop) and tap a pad instead to choose the pad.")
        r.trigger("preset.next", "Next preset", lambda: bank.cycle(1), group=g,
                  tip="Load the next filled pad's preset into the deck off air (the desk's "
                      "QUANT). The room does not move.")
        r.trigger("preset.prev", "Previous preset", lambda: bank.cycle(-1), group=g,
                  tip="Load the previous filled pad's preset into the deck off air. The "
                      "room does not move.")
        # the preset list, not the bank (2026-10-14): they step what the PRESETS
        # page lists, saved ones included. No factory row: a pad button's Learn or
        # the bindings file puts them on a control, never a loadable patch's row (row 700)
        r.trigger("preset.list.next", "Next preset in the list", lambda: bank.walk(1),
                  group=g,
                  tip="Load the next preset of the PRESETS section's list — every "
                      "preset by name, a new one included — into the deck off air, "
                      "wrapping at the end. The room does not move. "
                      "The desk's QUANT walks the pads instead.")
        r.trigger("preset.list.prev", "Previous preset in the list", lambda: bank.walk(-1),
                  group=g,
                  tip="Load the previous preset of the PRESETS section's list into the deck "
                      "off air, wrapping at the start. The room does not move.")
        # home (plan 15 WP2, decision 27): the show's startup loadable patch. Lit
        # while the show names one — the light the desk's OVERDUB shows
        r.trigger("preset.home", "Home", bank.home, group=g,
                  lit=lambda: bool(bank.startup),
                  tip="Home: load this show's startup preset into the deck off air — "
                      "the Home key (fn ← on a laptop) and OVERDUB (B11) on the desk. "
                      "The room does not move. The line at the foot of the window says "
                      "whether ⌘Z takes it back.")

    return r
