"""The parameter registry — one address space for everything the surface can set.

Every control the panel draws, every hotkey, every gamepad button and every
MIDI binding resolves to a Param here, by a stable string id
(``view.bright``, ``band.2.atk``, ``theme.load.0``). The registry is the
core's own contract (BLUEPRINT §3.6 inbound: "addressed by the same
parameter registry the UI uses"), so nothing in it may import from an
adapter — midi.py depends on this module, never the other way round.

Four kinds, one normalized interface:

  CONTINUOUS  value in a range; exposes norm ∈ [0, 1] both ways. Tapered
              params (tapers.Taper) quantize to the taper's integer throw so
              a fader position and a MIDI value agree on what the value is;
              untapered ones get a plain (or log) range.
  ENUM        an index into a list of choice names.
  TOGGLE      a bool.
  TRIGGER     an action; fire() and nothing else.

``step(n)`` moves any non-trigger param by n detents — taper positions, a
hundredth of an untapered range, one choice, or a flip — which is what
keys, d-pads and relative encoders all want.

Values are read live through getters, never cached, so a param stays true
after a hot reload or after the chain object is recreated on a source
attach (getters go through ``audio.chain``, not a captured chain).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from . import tapers
from .bands import BANDS, PRESETS, SHAPERS
from .geometry import SHAPES
from .tapers import Taper

PATTERNS = [
    "FLAT", "RINGS", "PLAID", "MOIRE", "BLOOM", "CAUSTIC",
    "HEX", "SPIRAL", "CELLS", "PLASMA", "WEAVE", "EMBER",
]
INST_MOTION = ["STILL", "ORBIT", "WAVE", "RIPPLE"]
BMP_PATHS = ["STILL", "ORBIT", "FIG-8", "SWAY"]
PLANES = ["XY", "XZ", "YZ", "XW", "YW", "ZW"]

RAW_STEPS = 100  # detents across an untapered continuous range


class Kind(Enum):
    CONTINUOUS = "continuous"
    ENUM = "enum"
    TOGGLE = "toggle"
    TRIGGER = "trigger"


def _clamp(x, a, b):
    return a if x < a else min(x, b)


@dataclass(eq=False)
class Param:
    id: str
    label: str
    kind: Kind
    get: Callable[[], Any] = field(repr=False, default=lambda: None)
    set: Callable[[Any], None] = field(repr=False, default=lambda v: None)
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

    # ---- generic value access ----

    @property
    def value(self):
        return self.get()

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
        """Detent index of the current value, 0..steps."""
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
        """Current state as a float in [0, 1]."""
        k = self.kind
        if k is Kind.CONTINUOUS:
            if self.taper is not None:
                return self.taper.unmap(self.get()) / self.taper.steps
            return self._raw_norm(self.get())
        if k is Kind.ENUM:
            n = self.steps
            return 0.0 if n == 0 else _clamp(self.get() / n, 0.0, 1.0)
        if k is Kind.TOGGLE:
            return 1.0 if self.get() else 0.0
        return 0.0

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
        elif u >= 0.5:
            self.fire()

    # ---- discrete moves ----

    def step(self, n: int = 1) -> None:
        """Move n detents: taper positions, choices, or a flip."""
        k = self.kind
        if k is Kind.CONTINUOUS:
            if self.wrap and self.taper is None:
                self.set_value(self.get() + n * (self.hi - self.lo) / self.steps)
            else:
                self.set_position(self.position() + n)
        elif k is Kind.ENUM:
            m = len(self.names)
            if m:
                self.set(_clamp(self.get() + n, 0, m - 1))
        elif k is Kind.TOGGLE:
            if n:
                self.set(not self.get())
        else:
            self.fire()

    def cycle(self, n: int = 1) -> None:
        """Like step, but an enum wraps around."""
        if self.kind is Kind.ENUM and self.names:
            self.set((self.get() + n) % len(self.names))
        else:
            self.step(n)

    def toggle(self) -> None:
        if self.kind is Kind.TOGGLE:
            self.set(not self.get())
        elif self.kind is Kind.TRIGGER:
            self.fire()

    # ---- readout ----

    def text(self) -> str:
        k = self.kind
        if k is Kind.CONTINUOUS:
            return self.fmt(self.get())
        if k is Kind.ENUM:
            names = self.names
            i = self.get()
            return names[i] if 0 <= i < len(names) else "—"
        if k is Kind.TOGGLE:
            return "on" if self.get() else "off"
        return ""


class Registry:
    """An ordered map of Param by id."""

    def __init__(self):
        self._p: dict[str, Param] = {}

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

    # ---- declaration helpers ----

    def continuous(self, pid, label, get, set, *, taper=None, lo=0.0, hi=1.0, log=False,
                   integer=False, wrap=False, fmt=None, group="", tip="") -> Param:
        if fmt is None:
            fmt = (lambda v: f"{int(v)}") if integer else (lambda v: f"{v:.2f}")
        return self.add(Param(
            pid, label, Kind.CONTINUOUS, get, set, group=group, tip=tip, taper=taper,
            lo=lo, hi=hi, log=log, integer=integer, wrap=wrap, fmt=fmt,
        ))

    def enum(self, pid, label, get, set, choices, *, group="", tip="") -> Param:
        return self.add(Param(pid, label, Kind.ENUM, get, set, group=group, tip=tip,
                              choices=choices))

    def toggle(self, pid, label, get, set, *, group="", tip="") -> Param:
        return self.add(Param(pid, label, Kind.TOGGLE, get, set, group=group, tip=tip))

    def trigger(self, pid, label, fire, *, group="", tip="") -> Param:
        return self.add(Param(pid, label, Kind.TRIGGER, fire=fire, group=group, tip=tip))


# ---------------------------------------------------------------- builder

def _attr(obj, name):
    return (lambda: getattr(obj, name)), (lambda v: setattr(obj, name, v))


def _item(get_list, i):
    return (lambda: get_list()[i]), (lambda v: get_list().__setitem__(i, v))


def build_registry(view, control, audio, presets=None) -> Registry:
    """Declare every parameter the surface owns.

    `audio` only needs a `.chain` attribute (tests pass a namespace); the
    chain is looked up on every access because a source attach replaces it.
    Panel- and app-level actions (panel toggle, restart…) are added by the
    caller with `trigger()` / `toggle()` once those objects exist.
    """
    r = Registry()
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
               "it hot-reloads on save. Patterns read the six band outputs as uniforms.")
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

    # ---- camera ----
    g = "camera"
    r.continuous("camera.zoom", "Zoom", *_attr(view, "zoom"), lo=0.05, hi=40.0, log=True,
                 fmt=lambda v: f"{v:.2f}×", group=g)
    r.continuous("camera.yaw", "Yaw", *_attr(view, "yaw"), lo=-math.pi, hi=math.pi,
                 wrap=True, fmt=lambda v: f"{math.degrees(v):.0f}°", group=g)
    r.continuous("camera.pitch", "Pitch", *_attr(view, "pitch"), lo=-1.55, hi=1.55,
                 fmt=lambda v: f"{math.degrees(v):.0f}°", group=g)

    def reset_view():
        view.ang = [0.0] * 6
        view.yaw = view.pitch = 0.0
        view.zoom, view.pan = 1.0, [0.0, 0.0]

    r.trigger("camera.reset", "Reset view", reset_view, group=g,
              tip="Reset rotation phases, orbit, zoom and pan.")

    # ---- master faders ----
    g = "master"
    r.continuous("master.gain", "Audio drive",
                 lambda: chain().gain, lambda v: setattr(chain(), "gain", v),
                 taper=tapers.T_DRIVE, fmt=tapers.fmt_gain, group=g,
                 tip="Master gain on the six band faders, after the transfer stage. Only "
                     "does anything while a source is attached.")
    r.continuous("master.dyn", "Dynamics",
                 lambda: chain().dyn, lambda v: setattr(chain(), "dyn", v),
                 taper=tapers.T_DYN, fmt=tapers.fmt_gain, group=g,
                 tip="How much of the range a limiter took is put back. At 0 the chain is "
                     "a plain level follower.")
    r.continuous("master.trim", "Input trim",
                 lambda: chain().trim, lambda v: setattr(chain(), "trim", v),
                 taper=tapers.T_TRIM, fmt=tapers.fmt_db, group=g,
                 tip="One offset added to all six per-band trims, at the very head of the "
                     "chain — moves a whole song down into the 56 dB working window.")

    # ---- scene ----
    g = "scene"
    r.enum("scene.select", "Scene", lambda: control.scene, control.select_scene,
           [p["name"] for p in PRESETS], group=g)
    r.trigger("scene.reset_all", "Reset all", control.reset_all_clicked, group=g,
              tip="Reloads the selected scene across all six bands. Undoable for 8 s.")

    # ---- bands ----
    g = "band"
    r.enum("band.select", "Band", lambda: control.selb,
           lambda i: setattr(control, "selb", i), [b.id for b in BANDS], group=g,
           tip="Which band's strip is open — the band.sel.* params follow it.")
    r.trigger("band.reset", "Reset band", control.reset_band, group=g,
              tip="Puts this band's whole strip back to the selected scene.")
    shaper_tags = [s.tag for s in SHAPERS]

    def band_params(prefix: str, idx: Callable[[], int], label_of: Callable[[str], str]):
        r.enum(f"{prefix}.fn", label_of("Transfer"),
               lambda: chain().params[idx()].fn,
               lambda fn: control.set_shaper(idx(), fn), shaper_tags, group=g)
        for knob in tapers.KNOBS:
            r.continuous(
                f"{prefix}.{knob.key}", label_of(knob.label),
                (lambda k=knob.key: getattr(chain().params[idx()], k)),
                (lambda v, k=knob.key: setattr(chain().params[idx()], k, v)),
                taper=knob.t, fmt=knob.fmt, tip=knob.tip, group=g,
            )

    for i, band in enumerate(BANDS):
        band_params(f"band.{i}", (lambda i=i: i), lambda lb, b=band.id: f"{b} {lb}")
        r.trigger(f"band.{i}.reset", f"{band.id} reset",
                  lambda i=i: control.reset_band(i), group=g)
    band_params("band.sel", lambda: control.selb, lambda lb: lb)

    # ---- themes ----
    if presets is not None:
        g = "theme"
        names = lambda: [
            s["name"] if s else f"THEME {k + 1}" for k, s in enumerate(presets.slots)
        ]
        # active is −1 until a theme loads: no choice selected, no LED lit
        r.enum("theme.select", "Theme", lambda: presets.active, presets.load, names,
               group=g, tip="Whole-surface save states — view, faders, all six band strips.")
        for k in range(len(presets.slots)):
            r.trigger(f"theme.load.{k}", f"Load theme {k + 1}",
                      lambda k=k: presets.load(k), group=g)
            r.trigger(f"theme.save.{k}", f"Save theme {k + 1}",
                      lambda k=k: presets.save(k), group=g)
        r.trigger("theme.next", "Next theme", lambda: presets.cycle(1), group=g)
        r.trigger("theme.prev", "Previous theme", lambda: presets.cycle(-1), group=g)

    # ---- audio transport (only what the engine exposes headlessly) ----
    if hasattr(audio, "toggle_play"):
        g = "audio"
        r.toggle("audio.play", "Play",
                 lambda: bool(getattr(audio, "playing", False)),
                 lambda on: audio.toggle_play() if on != bool(audio.playing) else None,
                 group=g, tip="Play / pause the loaded track.")
        r.trigger("audio.restart", "Restart track", audio.restart, group=g)
        r.trigger("audio.stop", "Stop source", audio.stop, group=g)
    return r
