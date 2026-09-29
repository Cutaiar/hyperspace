"""The parameter registry — one address space for everything the surface can set.

Every control the panel draws, every hotkey, every gamepad button and every
MIDI binding resolves to a Param here, by a stable string id
(``view.bright``, ``band.2.atk``, ``theme.load.0``). The registry is the
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
  TEXT        a string (a file path). Presets save it; every numeric
              surface ignores it — no norm, no step, no modulation.

``step(n)`` moves any non-trigger param by n detents — taper positions, a
hundredth of an untapered range, one choice, or a flip — which is what
keys, d-pads and relative encoders all want.

Values are read live through getters, never cached, so a param stays true
after a hot reload or after the chain object is recreated on a source
attach (getters go through ``audio.chain``, not a captured chain).

Two flags say what a param is *for*: ``persist`` (it belongs in a preset —
off for UI state, transport and rig-specific choices) and ``modulatable``
(a continuous source such as an audio lane may drive it — off for things
like which screen the output is on). An ``alias`` (band.sel.*) is neither.

Modulation — the one control concept every source shares — lives here.
Sources (an audio band, an LFO, a hand axis, a MIDI lane) never touch a
param directly: each adapter hands its lane values to ``router.feed`` and
``Router.modulate`` (routing.py) is the one caller of ``modulate(u)``, once
per frame per live row, with an offset in the param's normalized space.
Once per frame ``Registry.apply()`` then writes
``effective = base + Σ offsets`` into the live object. The *base* is what
the user set and what presets save; the object holds the effective value
the renderer reads. Base is adopted from the object the first time a
param is modulated; the param-level setters (set / set_norm / step…)
write the base while it is modulated; a direct write to the object by
other code shifts the base by the same delta (so the rotation integrator
keeps adding to ``ang`` while a lane adds a phase offset on top); and when
the last source lets go the base is written back. Continuous params are
mapped as floats — no detents — so a lane never zippers; enum and toggle
targets move with hysteresis so a noisy lane cannot flap them; a trigger
fires on a rising edge.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from . import tapers
from .analyzer import CURVES, F_HI, F_LO, Q_HI, Q_LO
from .bands import CEIL, NORMS, SHAPERS
from .fx import FxState
from .fx import declare as declare_fx
from .geometry import PLANE_NAMES, SHAPES
from .lookback import LAYERS, MAX_ECHOES, OCTAVES, RES, TINT_FROM, DreamState
from .tapers import Taper
from .tapers import clamp as _clamp

PATTERNS = [
    "FLAT", "RINGS", "PLAID", "MOIRE", "BLOOM", "CAUSTIC",
    "HEX", "SPIRAL", "CELLS", "PLASMA", "WEAVE", "EMBER",
]
INST_MOTION = ["STILL", "ORBIT", "WAVE", "RIPPLE"]
BMP_PATHS = ["STILL", "ORBIT", "FIG-8", "SWAY"]
PLANES = PLANE_NAMES   # the rotation planes' names, in geometry.PLANES's order

RAW_STEPS = 100  # detents across an untapered continuous range
N_MACROS = 8     # macro.1–8: knobs that exist to be a route's scale and to be owned
# the performance / session split (plan 13 §4, D9), by group, declared
# once. Performance is what a theme slot (later a preset) captures and
# replaces: the look, its LFOs and its macros. Session is the rig and the
# room (the clock, the hands' feel, the analyzer and its source, the
# output, the UI), which a theme never moves, so a tapped BPM or the band
# scene survives a theme change. Every persisted param is in exactly one
# (tests/test_params.py walks the full registry); a group in neither
# (`theme`) has no persisted params, and `rot.phase.*` is `persist=False`.
PERFORMANCE_GROUPS = ("view", "rot", "camera", "pattern", "dream", "fx", "lfo", "macro")
SESSION_GROUPS = ("tempo", "hands", "band", "master", "scene", "audio", "output",
                  "overlay", "ui")
PARTS = {"performance": PERFORMANCE_GROUPS, "session": SESSION_GROUPS}

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

# modulation hysteresis: a toggle or trigger goes high above ON and low
# below OFF; an enum or integer only moves once the target is this far
# past the midpoint between two choices
MOD_ON, MOD_OFF = 0.6, 0.4
MOD_DEADBAND = 0.15


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
    # ENUM: a list, or a callable returning one (theme names change on save)
    choices: list[str] | Callable[[], list[str]] = field(default_factory=list)
    # what the param is for
    persist: bool = True         # belongs in a preset
    modulatable: bool = True     # a lane may drive it
    alias: bool = False          # a view onto another param (band.sel.*)
    # modulation state — runtime only
    _base: float | None = field(default=None, repr=False)   # norm; None = not modulated
    _mod: float = field(default=0.0, repr=False)            # this frame's offsets
    _held: bool = field(default=False, repr=False)          # a source called this frame
    _last: float | None = field(default=None, repr=False)   # norm we last wrote
    _disc: float | None = field(default=None, repr=False)   # last discrete effective
    _armed: bool = field(default=True, repr=False)          # trigger edge detector

    def __post_init__(self):
        if self.alias:
            self.persist = self.modulatable = False
        if self.kind is Kind.TRIGGER:
            self.persist = False
        if self.kind is Kind.TEXT:
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
        """What the user set, in the param's own units — what a preset saves.

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
            if m:
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

    def cycle(self, n: int = 1) -> None:
        """Like step, but an enum wraps around."""
        if self.kind is Kind.ENUM and self.names:
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

    def modulate(self, u: float) -> None:
        """Add a source's offset for this frame, in normalized units.

        A source calls this every frame it is routed here, even with 0 —
        holding the param is what keeps its base apart from the object;
        the frame nothing calls, `apply()` writes the base back.
        """
        if not self.modulatable:
            return
        if self._base is None:
            self._base = self._norm_of(self.get())   # adopt the user's setting
            self._last = self._base
            self._disc = None
        self._mod += float(u)
        self._held = True

    def apply(self) -> None:
        """End of frame: write base + offsets to the object, or let go."""
        if self._base is None:
            return
        held, mod = self._held, self._mod
        self._held, self._mod = False, 0.0
        k = self.kind
        if not held:                          # last source left: restore base
            if k is not Kind.TRIGGER:
                self.put(self._value_of_norm(self._base))
            self._base = self._last = self._disc = None
            return
        if k is not Kind.TRIGGER:
            # something wrote the object since we did (the rotation
            # integrator, presets.load…): that delta belongs to the base
            cur = self._norm_of(self.get())
            if self._last is not None and cur != self._last:
                self._base += cur - self._last
                self._base = self._base % 1.0 if self.wrap else _clamp(self._base, 0.0, 1.0)
        target = self._base + mod
        if k is Kind.CONTINUOUS:
            target = target % 1.0 if self.wrap else _clamp(target, 0.0, 1.0)
            if self.integer:
                self.put(self._raw_value(self._snap(target * self.steps) / self.steps))
            else:
                self.put(self._value_of_norm(target))
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

    def _snap(self, x: float) -> float:
        """Nearest integer, moving only once past the midpoint + deadband."""
        cur = self._disc
        if cur is None or abs(x - cur) > 0.5 + MOD_DEADBAND:
            cur = float(round(_clamp(x, 0, self.steps)))
        self._disc = cur
        return cur


def part_of(p: Param) -> str | None:
    """"performance" or "session", by the param's group; None for a group
    in neither (no group, or `theme`, whose params never persist)."""
    for name, groups in PARTS.items():
        if p.group in groups:
            return name
    return None


class Registry:
    """An ordered map of Param by id."""

    def __init__(self):
        self._p: dict[str, Param] = {}
        # the one rule for what an alias stands for right now (band.sel.*
        # → the selected band), installed by build_registry; the panel's
        # widgets, the Learn object and the routing menu all ask here
        self.real_of: Callable[[Param], Param] | None = None

    def real(self, p: Param) -> Param:
        """The param behind an alias — where the base and the modulation
        state live — or `p` itself when it is not one."""
        if p.alias and self.real_of is not None:
            return self.real_of(p) or p
        return p

    def add(self, p: Param) -> Param:
        if p.id in self._p:
            raise ValueError(f"duplicate param id {p.id}")
        self._p[p.id] = p
        return p

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
        every adapter already treats an unknown id as a no-op."""
        p = self._p.pop(pid, None)
        if p is not None and p.modulated:
            p._held = False
            p.apply()            # hand the object its base back
        return p

    def remove_prefix(self, prefix: str) -> list[Param]:
        return [self.remove(pid) for pid in list(self._p) if pid.startswith(prefix)]

    # ---- frame ----

    def apply(self) -> None:
        """Once per frame, after every source has called modulate()."""
        # over a copy: a modulated trigger may add or remove params
        # (a band layout change) while we are still walking the table
        for p in list(self._p.values()):
            if p._base is not None:
                p.apply()

    # ---- persistence: the one serialization every preset is made of ----

    def snapshot(self, group: str | None = None, *, ids=None,
                 part: str | None = None) -> dict[str, Any]:
        """{id: base value} for every persistent param, the macros
        included, or only one group, one id set, or one part of the split
        (``part="performance"`` / ``"session"``, PARTS). The filters
        combine: each one given must hold."""
        out: dict[str, Any] = {}
        groups = None if part is None else PARTS[part]
        for p in self._p.values():
            if not p.persist:
                continue
            if group is not None and p.group != group:
                continue
            if ids is not None and p.id not in ids:
                continue
            if groups is not None and p.group not in groups:
                continue
            v = p.base
            out[p.id] = list(v) if isinstance(v, list) else v
        return out

    def restore(self, values: dict[str, Any]) -> list[str]:
        """Set every param named; returns the ids this registry doesn't have."""
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
             persist=True, modulatable=True, alias=False) -> Param:
        return self.add(Param(pid, label, Kind.ENUM, get, set, group=group, tip=tip,
                              choices=choices, persist=persist, modulatable=modulatable,
                              alias=alias))

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


# ---------------------------------------------------------------- builder

def _attr(obj, name):
    return (lambda: getattr(obj, name)), (lambda v: setattr(obj, name, v))


def _item(get_list, i):
    return (lambda: get_list()[i]), (lambda v: get_list().__setitem__(i, v))


def build_registry(view, control, audio, themes=None, dream=None, fx=None,
                   restart=None) -> Registry:
    """Declare every parameter the surface owns.

    `audio` only needs a `.chain` attribute (tests pass a namespace); the
    chain is looked up on every access because a source attach replaces it.
    Its capture side is optional too: with `start_mic` / `stop` and a
    `devices` list (audio.AudioEngine) ``audio.mic`` and ``audio.device`` do
    something; without them they are declared anyway, so a key row (`M`)
    resolves with or without a panel. `dream` is the renderer's lookback
    state (lookback.DreamState); a fresh one stands in when there is no
    renderer, so the group is always declared; `fx` (fx.FxState, the
    renderer's effect stack) likewise. `restart` is the host's request to
    restart the process (``app.restart``; app.py polls a flag) — a no-op
    without a host. Only the panel's own state (``ui.*``) is added by the
    panel once it exists.
    """
    r = Registry()
    dream = dream if dream is not None else DreamState()
    chain = lambda: audio.chain
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
    r.toggle("view.faces", "Faces", *_attr(view, "faces"), group=g,
             tip="Translucent fills on the true 2-faces, under the wireframe. "
                 "First build per shape takes a moment (extraction is cached).")
    r.toggle("view.cut_through", "Cut-through", *_attr(view, "cut_through"), group=g,
             tip="On: the translucent faces (and faint lines) cut the window's alpha, so "
                 "the screen behind the render window shows through them. Off: they "
                 "draw over the ground and whatever layer is under them — nothing behind "
                 "the window shows except where the ground itself is clear.")
    r.toggle("view.rotate", "Rotate", *_attr(view, "playing"), group=g)
    r.continuous("view.instances", "Instances", *_attr(view, "instances"),
                 lo=1, hi=100, integer=True, fmt=lambda v: f"{int(v)} instance(s)", group=g,
                 tip="Synchronized copies in a grid — scroll to zoom out over the field, "
                     "right-drag to pan.")
    r.enum("view.inst_motion", "Grid motion", *_attr(view, "inst_motion"), INST_MOTION,
           group=g, tip="Trigonometric motion over the instance grid — each copy's phase "
                        "comes from its grid position, so the field moves as one figure.")
    r.continuous("view.inst_amp", "Grid amp", *_attr(view, "inst_amp"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"amp {v:.2f}", group=g)
    r.continuous("view.inst_rate", "Grid rate", *_attr(view, "inst_rate"), lo=0.0, hi=6.0,
                 fmt=lambda v: f"rate {v:.1f}", group=g)
    r.enum("view.pattern", "Pattern", *_attr(view, "pattern"), PATTERNS, group=g,
           tip="Face pattern — edit hyperspace/shaders/patterns.glsl while the app runs; "
               "it hot-reloads on save. Patterns read the pattern inputs as u_mod[8].")
    r.continuous("view.pattern_mix", "Pattern mix", *_attr(view, "pattern_mix"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"mix {v:.2f}", group=g)
    r.continuous("view.bmp_alpha", "Bitmap alpha", *_attr(view, "bmp_alpha"),
                 lo=0.0, hi=1.0, fmt=lambda v: f"bitmap alpha {v:.2f}", group=g)
    r.continuous("view.bmp_scale", "Bitmap size", *_attr(view, "bmp_scale"),
                 lo=0.05, hi=2.0, fmt=lambda v: f"bitmap size {v:.2f}", group=g)
    r.enum("view.bmp_mode", "Bitmap path", *_attr(view, "bmp_mode"), BMP_PATHS, group=g,
           tip="The bitmap's own path about the face centre — independent of the "
               "instance-grid motion.")
    r.continuous("view.bmp_amp", "Bitmap amp", *_attr(view, "bmp_amp"), lo=0.0, hi=0.5,
                 fmt=lambda v: f"amp {v:.2f}", group=g)
    r.continuous("view.bmp_rate", "Bitmap rate", *_attr(view, "bmp_rate"), lo=0.0, hi=6.0,
                 fmt=lambda v: f"rate {v:.1f}", group=g)
    r.text("view.bmp_file", "Bitmap file", *_attr(view, "bmp_file"), group=g,
           tip="Image drawn over the face pattern; empty for none.")
    # the face pattern's modulation inputs — what the shaders read as
    # u_mod[8]. Base 1.0 is the un-driven look; a routed lane rides on it.
    for k in range(len(view.pattern_mod)):
        r.continuous(f"pattern.mod.{k}", f"Pattern mod {k + 1}",
                     *_item(lambda: view.pattern_mod, k), lo=0.0, hi=2.6,
                     fmt=lambda v: f"{v:.2f}", group="pattern",
                     tip="A modulation input the face patterns read (patterns.glsl). "
                         "Route an audio band here to drive the pattern.")

    # ---- rotation: per-plane rate and phase ----
    # rate multiplies dt·speed·RATE[p]; signed so a lane can spin a plane
    # backwards, and as wide as the reference's plane drive (ROT_RATE_MAX).
    # phase is the integrated angle, folded to one turn: not a preset value
    # (a theme changes the look, not where the spin is) but a modulation
    # target — a lane adds a phase offset on top of the integrator.
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

    # ---- camera ----
    g = "camera"
    r.continuous("camera.zoom", "Zoom", *_attr(view, "zoom"), lo=0.05, hi=40.0, log=True,
                 fmt=lambda v: f"{v:.2f}×", group=g)
    r.continuous("camera.yaw", "Yaw", *_attr(view, "yaw"), lo=-math.pi, hi=math.pi,
                 wrap=True, fmt=lambda v: f"{math.degrees(v):.0f}°", group=g)
    r.continuous("camera.pitch", "Pitch", *_attr(view, "pitch"), lo=-1.55, hi=1.55,
                 fmt=lambda v: f"{math.degrees(v):.0f}°", group=g)
    for i, axis in enumerate("xy"):
        r.continuous(f"camera.pan.{axis}", f"Pan {axis.upper()}", *_item(lambda: view.pan, i),
                     lo=-4000.0, hi=4000.0, fmt=lambda v: f"{v:+.0f} px", group=g)

    def reset_view():
        view.ang = [0.0] * 6
        view.yaw = view.pitch = 0.0
        view.zoom, view.pan = 1.0, [0.0, 0.0]

    r.trigger("camera.reset", "Reset view", reset_view, group=g,
              tip="Reset rotation phases, orbit, zoom and pan.")

    # ---- look-back: the frame history composited over the scene ----
    # lookback.py reads these every frame; the dream worker (WP6b) reads
    # the second half. Cadence and size rebuild the ring, so no lane drives
    # them; everything else is a live fader.
    g = "dream"
    r.toggle("dream.on", "Look-back", *_attr(dream, "on"), group=g,
             tip="Composite the frame history over the scene: raw echoes now, the "
                 "dreamed wake once a worker is attached.")
    r.continuous("dream.mix", "Dream mix", *_attr(dream, "mix"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"dream {v:.2f}", group=g,
                 tip="The dream buffer's opacity under the scene.")
    r.continuous("dream.echo_mix", "Echo mix", *_attr(dream, "echo_mix"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"echo {v:.2f}", group=g,
                 tip="The echoes' opacity at age zero; each frame of age multiplies "
                     "by the decay.")
    r.continuous("dream.decay", "Decay", *_attr(dream, "decay"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"{v:.3f} / frame", group=g,
                 tip="Per-frame fade of an echo with its age.")
    r.continuous("dream.darken", "Darken", *_attr(dream, "darken"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"×{1.0 - v:.2f}", group=g,
                 tip="How much darker the wake is than the frames it came from.")
    r.continuous("dream.contrast", "Contrast", *_attr(dream, "contrast"), lo=0.5, hi=3.0,
                 fmt=lambda v: f"^{v:.2f}", group=g,
                 tip="A power curve on every layer: above 1 only the bright, "
                     "high-contrast regions of the history read.")
    r.continuous("dream.occlude", "Occlude", *_attr(dream, "occlude"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"occlude {v:.2f}", group=g,
                 tip="The render over the wake: at 1 wherever this frame drew, the "
                     "shape covers the dream and echoes beneath it, so the tracers "
                     "only fill the space between; at 0 the wake glows over the shapes.")
    # the dream buffer's chroma — the net paints in its own primaries; these
    # re-colour D on its way into the composite (lookback.py, chroma())
    r.continuous("dream.hue", "Hue shift", *_attr(dream, "hue"), lo=-180.0, hi=180.0,
                 wrap=True, fmt=lambda v: f"{v:+.0f}°", group=g,
                 tip="Rotate the dream's own colours about the grey axis; luminance "
                     "is kept.")
    r.continuous("dream.sat", "Saturation", *_attr(dream, "sat"), lo=0.0, hi=2.0,
                 fmt=lambda v: f"sat {v:.2f}", group=g,
                 tip="The dream's own colours' saturation: 0 greyscale, 1 as the net "
                     "painted them, above that pushed.")
    r.continuous("dream.tint", "Tint", *_attr(dream, "tint"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"tint {v:.2f}", group=g,
                 tip="Cross-fade from the dream's colours to its luminance in one "
                     "colour — the tint colour below, or the scene's own hue.")
    r.enum("dream.tint_from", "Tint from", *_attr(dream, "tint_from"), TINT_FROM, group=g,
           tip="Where the tint's hue comes from: the tint hue fader, or the hue of "
               "the scene's mean colour this frame.")
    r.continuous("dream.tint_hue", "Tint hue", *_attr(dream, "tint_hue"), lo=0.0, hi=360.0,
                 wrap=True, fmt=lambda v: f"{v:.0f}°", group=g,
                 tip="The tint colour's hue; unused while the tint is from the scene.")
    r.continuous("dream.tint_sat", "Tint sat", *_attr(dream, "tint_sat"), lo=0.0, hi=1.0,
                 fmt=lambda v: f"sat {v:.2f}", group=g,
                 tip="The tint colour's saturation: 0 tints grey — a greyscale dream.")
    r.continuous("dream.echoes", "Echoes", *_attr(dream, "echoes"), lo=0, hi=MAX_ECHOES,
                 integer=True, fmt=lambda v: f"{int(v)} echo(es)", group=g,
                 tip="Frames kept in the history; 0 composites the dream buffer alone.")
    r.continuous("dream.every", "Every", *_attr(dream, "every"), lo=1, hi=8, integer=True,
                 fmt=lambda v: f"every {int(v)}", group=g, modulatable=False,
                 tip="Capture cadence in frames: the spacing between echoes.")
    r.enum("dream.res", "Resolution", *_attr(dream, "res"), [str(v) for v in RES], group=g,
           modulatable=False,
           tip="The history's short side in pixels; the render's aspect is kept.")
    # the worker's (WP6b) — presets carry them from day one
    r.continuous("dream.steps", "Steps", *_attr(dream, "steps"), lo=1, hi=3, integer=True,
                 fmt=lambda v: f"{int(v)} step(s)", group=g,
                 tip="Gradient-ascent steps per frame on the dream buffer; 1 flickers.")
    r.continuous("dream.step", "Step size", *_attr(dream, "step"), lo=0.005, hi=0.06,
                 fmt=lambda v: f"{v:.3f}", group=g,
                 tip="How far each step pushes; step × steps should stay under ~0.6 k.")
    r.continuous("dream.k", "Blend k", *_attr(dream, "k"), lo=0.03, hi=0.3,
                 fmt=lambda v: f"k {v:.3f}", group=g,
                 tip="How much of the new frame enters the dream buffer each frame — "
                     "its memory, 33 frames down to 3.")
    r.enum("dream.layer", "Layer", *_attr(dream, "layer"), LAYERS, group=g,
           tip="The net layer the dream maximises: conv2_2 fine grain, conv3_3 the "
               "classic swirl, conv4_3 blotchier, inception the eyes-and-dogs curls.")
    r.enum("dream.octaves", "Octaves", *_attr(dream, "octaves"), OCTAVES, group=g,
           tip="Scales the dream runs at, one per frame in rotation — larger forms "
               "for the same cost.")
    r.continuous("dream.mask_decay", "Mask decay", *_attr(dream, "mask_decay"),
                 lo=0.9, hi=0.995, fmt=lambda v: f"{v:.3f}", group=g,
                 tip="How long the dream stays where content was, after it leaves: "
                     "the content mask's per-frame decay, 10 to 200 frames. The mask "
                     "decides where the dream may exist; what covers it is Occlude.")
    r.continuous("dream.jitter", "Jitter", *_attr(dream, "jitter"), lo=0, hi=16,
                 integer=True, fmt=lambda v: f"{int(v)} px", group=g,
                 tip="Random pixel offset per step, the classic trick that turns pixel "
                     "noise into coherent texture.")

    # ---- effects: one param per annotated uniform in shaders/fx/*.glsl ----
    # (fx.py). A file edited into a new shape re-declares its own ids.
    fx = fx if fx is not None else FxState()
    declare_fx(r, fx)
    fx.on_specs = lambda names: declare_fx(r, fx, names)

    # ---- master faders ----
    g = "master"
    r.continuous("master.gain", "Audio drive",
                 lambda: chain().gain, lambda v: setattr(chain(), "gain", v),
                 taper=tapers.T_DRIVE, fmt=tapers.fmt_gain, group=g,
                 tip="Master gain on every band fader, after the transfer stage. Only "
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
                 tip="One offset added to every per-band trim, at the very head of the "
                     "chain — moves a whole song down into the 56 dB working window.")

    # ---- macros: the chaining knobs (plan 09, decision 7) ----
    # Nothing reads a macro but the router: a route names one as its
    # `scale`, and a performer may own it — so a hand that positions
    # macro.2 deepens the lane pushing brightness × macro.2, one frame
    # later, rather than two performers pulling on brightness. No object,
    # so the values live in this list, and the slot clamps itself (a
    # restore writes raw). Base 1: a route that names an untouched macro
    # runs at its full depth, the same as "× 1".
    g = "macro"
    macros = [1.0] * N_MACROS
    for k in range(N_MACROS):
        r.continuous(f"macro.{k + 1}", f"Macro {k + 1}", (lambda k=k: macros[k]),
                     (lambda v, k=k: macros.__setitem__(k, _clamp(float(v), 0.0, 1.0))),
                     lo=0.0, hi=1.0, fmt=lambda v: f"{v * 100:.0f} %", group=g,
                     tip="Does nothing on its own. Put it on a route as its scale, or own "
                         "it with a hand or LFO, to chain.")

    # ---- scene ----
    g = "scene"
    r.enum("scene.select", "Scene", lambda: control.scene, control.select_scene,
           control.scene_names, group=g,
           tip="The eleven factory scenes, re-tuned onto the bands you have; the "
               "preset strip loads a band file whole, layout included.")
    r.trigger("scene.reset_all", "Reset all", control.reset_all_clicked, group=g,
              tip="Reloads the selected scene across every band. Undoable for 8 s.")

    # ---- bands ----
    # The analyzer has N bands (plan 07), so this block is a function: it
    # drops every band.* id and declares them again for the current N, and
    # runs whenever the layout changes (a band added, removed or moved, a
    # preset's layout applied) — control.on_layout is that hook.
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
        r.enum("band.select", "Band", lambda: control.selb,
               lambda i: setattr(control, "selb", i), lambda: chain().band_names, group=g,
               persist=False, modulatable=False,
               tip="Which band's strip is open — the band.sel.* params follow it.")
        # structural: never lane-driven (they rebuild this very block)
        r.trigger("band.add", "Add band", control.add_band, group=g, modulatable=False,
                  tip="A new band in the widest gap between the others; it becomes "
                      "the open strip.")
        r.trigger("band.remove", "Remove band", control.remove_band, group=g,
                  modulatable=False, tip="Drops the open band. The last one stays.")
        r.trigger("band.reset", "Reset band", control.reset_band, group=g,
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

    # ---- themes ----
    if themes is not None:                 # library.Project: the F1–F8 bank
        g = "theme"
        names = lambda: [
            s["name"] if s else f"THEME {k + 1}" for k, s in enumerate(themes.slots)
        ]
        # active is −1 until a theme loads: no choice selected, no LED lit
        # meta-controls: they *apply* themes, so no preset stores them
        r.enum("theme.select", "Theme", lambda: themes.active, themes.load_slot, names,
               group=g, persist=False, modulatable=False,
               tip="Save states of the performance: the look, its LFOs and its "
                   "macros. Never the tempo, the hands or the analyzer.")
        for k in range(len(themes.slots)):
            r.trigger(f"theme.load.{k}", f"Load theme {k + 1}",
                      lambda k=k: themes.load_slot(k), group=g)
            r.trigger(f"theme.save.{k}", f"Save theme {k + 1}",
                      lambda k=k: themes.save_slot(k), group=g, modulatable=False)
        r.trigger("theme.next", "Next theme", lambda: themes.cycle(1), group=g)
        r.trigger("theme.prev", "Previous theme", lambda: themes.cycle(-1), group=g)

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
    if hasattr(audio, "toggle_play"):
        r.toggle("audio.play", "Play",
                 lambda: bool(getattr(audio, "playing", False)),
                 lambda on: audio.toggle_play() if on != bool(audio.playing) else None,
                 group=g, persist=False, tip="Play / pause the loaded track.")
        r.trigger("audio.restart", "Restart track", audio.restart, group=g)
        r.trigger("audio.stop", "Stop source", audio.stop, group=g, modulatable=False)
    return r
