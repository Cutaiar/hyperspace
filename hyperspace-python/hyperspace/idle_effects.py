"""Idle effects: the whole-desk animations `idle_lights` can play.

Dylan's APC40 screensavers (2026-11-16, first as a standalone demo), made
patterns of the one idle system: each one treats every light of a set as a
pixel at its place on the device (`Light.x`, `Light.y`), so a ring crosses
the clip grid and the button rows below it together. An effect gives each
light a level (0..1) and a colour name ("green", "yellow", "red") or None;
`Light.show` turns that into what the light can show: a light with
`colours` (the APC40's clip pads) lights that colour above THRESHOLD, any
other light shows the level on its own `levels`. So every effect also runs
on a one-colour device (the DDJ-FLX4): it reads as shapes, not colours.

Where an effect is centred comes from the set itself: the middle of the
lights that show colour (the APC40's clip grid), else of all of them.

What the APC40 can show, measured by Dylan on the desk (2026-11-16): the
clip grid is the one colour screen (off, green, yellow, red; no brightness
levels); every other button is one colour, on or off; it takes ~25 000 LED
messages a second, so `idle_lights.FPS` is no strain. The knob rings are not
drawn: in mode 0x42 a ring value re-bases its knob (apc40.RING_REBASES_KNOB),
so the knob that woke the desk would turn on from the animation's value.

An effect is made fresh each time it starts (`make`), so one that keeps
state (fireworks) starts clean. Imports nothing from the package but
`geometry`, and that only when a zoom is made.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .idle_lights import Light

__all__ = ["EFFECTS", "HEAT", "THRESHOLD", "Effect", "heart_gauge", "make"]

THRESHOLD = 0.5                       # a colour light is lit above this level
HEAT = ("green", "yellow", "red")     # a level's colour on a heat ramp, cool → hot

Level = tuple[float, "str | None"]


def heat(level: float) -> str:
    """A level's colour on the heat ramp: green, yellow, red as it rises."""
    return HEAT[min(2, int(max(0.0, level) * 3))]


def bump(d: float, width: float = 0.6) -> float:
    """1 at d = 0, falling smoothly to 0 at |d| = width."""
    a = abs(d) / width
    return 0.0 if a >= 1 else 0.5 + 0.5 * math.cos(math.pi * a)


def _box(lights: Sequence[Light]) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) around the lights that show colour, else all of them."""
    pts = [lt for lt in lights if lt.colours] or list(lights)
    if not pts:
        return 0.0, 0.0, 0.0, 0.0
    xs, ys = [lt.x for lt in pts], [lt.y for lt in pts]
    return min(xs), min(ys), max(xs), max(ys)


class Effect:
    """One run of an effect over a set of lights. `frame(t)` gives a
    (level, colour) per light, `t` seconds since it started."""

    name = ""

    def __init__(self, lights: Sequence[Light]):
        self.lights = tuple(lights)
        x0, y0, x1, y1 = self.box = _box(self.lights)
        self.cx, self.cy = (x0 + x1) / 2, (y0 + y1) / 2

    def frame(self, t: float) -> list[Level]:
        return [self.at(lt, t) for lt in self.lights]

    def at(self, lt: Light, t: float) -> Level:
        raise NotImplementedError


class Wash(Effect):
    """A diagonal band from the top left to the bottom right, a colour a pass."""

    name = "wash"

    def at(self, lt, t):
        d = (lt.x + lt.y) / 2.2 - 3.2 * t
        k = math.floor(d / 9.0)
        return bump(d - 9.0 * k - 4.5, 1.6), HEAT[int(k) % 3]


class Ripple(Effect):
    """Rings going out from the centre, each a colour."""

    name = "ripple"
    speed, gap, width = 3.0, 2.4, 0.55

    def gauge(self, lt, t) -> float:
        return math.hypot(lt.x - self.cx, (lt.y - self.cy) * 1.15)

    def colour(self, k: int) -> str:
        return HEAT[-k % 3]

    def at(self, lt, t):
        d = self.gauge(lt, t) - self.speed * t
        k = math.floor(d / self.gap)
        return bump(d - self.gap * (k + 0.5), self.width), self.colour(k)


class Wobble(Ripple):
    """Wiggly rings: the radius wobbles with the angle, and the wobble turns."""

    name = "wobble"

    def gauge(self, lt, t):
        dx, dy = lt.x - self.cx, (lt.y - self.cy) * 1.15
        a = math.atan2(dy, dx)
        return math.hypot(dx, dy) * (1 + 0.35 * math.sin(3 * a + 2.5 * t)
                                     + 0.15 * math.sin(5 * a - 1.7 * t))


class Heat(Effect):
    """A slow heat map: drifting sums of sines, cool green to hot red."""

    name = "heat"

    def at(self, lt, t):
        x, y = lt.x, lt.y
        v = (math.sin(0.9 * x + 0.7 * t) + math.sin(0.8 * y - 0.9 * t)
             + math.sin(0.5 * (x + y) + 0.4 * t) + math.sin(math.hypot(x - 4, y - 4) - 1.1 * t))
        v = (v + 4) / 8                     # 0..1
        return (v, heat((v - 0.35) / 0.65)) if v > 0.35 else (0.0, None)


def _heart_inside(x: float, y: float) -> bool:
    """The heart curve (x²+y²−1)³ ≤ x²y³, point down, about 2.3 wide."""
    return (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0


def heart_gauge(x: float, y: float) -> float:
    """The smallest scale s at which (x, y) is inside s · heart."""
    if x == 0 and y == 0:
        return 0.0
    lo, hi = 0.0, 50.0
    for _ in range(30):
        s = (lo + hi) / 2
        if _heart_inside(x / s, y / s):
            hi = s
        else:
            lo = s
    return hi


class Hearts(Ripple):
    """Heart-shaped rings going out from the centre: red, red, yellow."""

    name = "hearts"
    speed, gap, width = 2.2, 2.6, 0.6

    def __init__(self, lights):
        super().__init__(lights)
        self._g = [heart_gauge(lt.x - self.cx, -(lt.y - self.cy - 0.4) * 1.15) * 1.3
                   for lt in self.lights]

    def frame(self, t):
        out = []
        for g in self._g:
            d = g - self.speed * t
            k = math.floor(d / self.gap)
            out.append((bump(d - self.gap * (k + 0.5), self.width), ("red", "red", "yellow")[-k % 3]))
        return out


HEART = (".XX.XX.",
         "XXXXXXX",
         ".XXXXX.",
         "..XXX..",
         "...X...")


class Beat(Effect):
    """One red heart on the colour lights (the clip grid), beating at about
    70 bpm; every other light breathes with it."""

    name = "heartbeat"

    def at(self, lt, t):
        ph = (t * 70 / 60) % 1
        pulse = max(bump(ph, 0.12), 0.7 * bump(ph - 0.22, 0.1))
        if lt.colours:
            col, row = round(lt.x - self.box[0]), round(lt.y - self.box[1])
            on = 0 <= row < len(HEART) and 0 <= col < len(HEART[row]) and HEART[row][col] == "X"
            return (1.0, "red") if on else (0.0, None)
        return pulse * 0.9, "red"


class Fireworks(Effect):
    """Rockets climb from below the lights, burst over the colour lights into
    sparks that fall, cool red → yellow → green, and fade."""

    name = "fireworks"

    def __init__(self, lights, seed: int | None = None):
        super().__init__(lights)
        self.rng = random.Random(seed)
        self.rockets: list[list[float]] = []     # x, y, vy, burst_y
        self.sparks: list[list[float]] = []      # x, y, vx, vy, born
        self.last: float | None = None
        self.next_launch = 0.0
        self.floor = max((lt.y for lt in self.lights), default=0.0) + 0.5
        self.span = max(1.0, self.floor - min((lt.y for lt in self.lights), default=0.0))

    def frame(self, t):
        dt = 0.0 if self.last is None else min(0.1, t - self.last)
        self.last = t
        r, (x0, y0, x1, y1) = self.rng, self.box
        if t >= self.next_launch:
            burst = self.cy + r.uniform(-0.85, 0.25) * max(1.0, y1 - y0)
            self.rockets.append([r.uniform(x0, x1), self.floor, -r.uniform(9, 12) * self.span / 10,
                                 burst])
            self.next_launch = t + r.uniform(0.5, 1.4)
        for k in self.rockets:
            k[1] += k[2] * dt
        for k in [k for k in self.rockets if k[1] <= k[3]]:
            self.rockets.remove(k)
            for i in range(14):
                a = 2 * math.pi * i / 14 + r.uniform(-0.2, 0.2)
                v = r.uniform(2.5, 4.5)
                self.sparks.append([k[0], k[1], v * math.cos(a), v * math.sin(a), t])
        for s in self.sparks:
            s[3] += 5.0 * dt
            s[0] += s[2] * dt
            s[1] += s[3] * dt
        self.sparks = [s for s in self.sparks if t - s[4] < 1.4 and s[1] < self.floor + 1]
        out: list[Level] = []
        for lt in self.lights:
            lv, col = 0.0, None
            for k in self.rockets:
                if abs(lt.x - k[0]) < 0.6 and abs(lt.y - k[1]) < 0.7:
                    lv, col = 1.0, "yellow"
            for s in self.sparks:
                age = (t - s[4]) / 1.4
                b = max(0.0, 1 - math.hypot(lt.x - s[0], lt.y - s[1]) / 0.75) * (1 - age)
                if b > lv:
                    lv, col = b * 1.6, HEAT[2 - min(2, int(age * 3))]
            out.append((min(1.0, lv), col))
        return out


def _hull(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def half(seq):
        h: list[tuple[float, float]] = []
        for p in seq:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1])
                                   - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(list(reversed(pts)))
    return lo[:-1] + up[:-1]


def shape_vertices(shape: str) -> list[tuple[float, float, float, float]]:
    """A geometry shape's vertices in 4D, scaled to unit size (KeyError: no such shape)."""
    from . import geometry
    s: Any = geometry.SHAPES[geometry.shape_index(shape)]
    vs = [[float(c) for c in v][:4] + [0.0] * (4 - len(v)) for v in s.build()["V"]]
    r = max(math.sqrt(sum(c * c for c in v)) for v in vs) or 1.0
    return [(v[0] / r, v[1] / r, v[2] / r, v[3] / r) for v in vs]


class Zoom(Ripple):
    """A shape zooming out from the centre: its outline (the hull of its
    vertices, turned in 4D and projected) as rings that grow and turn as the
    shape does. On an 8 × 5 grid it reads as a turning square or triangle."""

    name = "zoom"
    speed, gap, width = 2.0, 3.4, 0.85

    def __init__(self, lights, shape: str = "Tesseract"):
        super().__init__(lights)
        self.V = shape_vertices(shape)
        self._t: float | None = None
        self._planes: list[tuple[float, float]] = []

    def _outline(self, t):
        a, b, c = 0.21 * t, 0.13 * t, 0.08 * t
        pts = []
        for x, y, z, w in self.V:
            x, w = x * math.cos(a) - w * math.sin(a), x * math.sin(a) + w * math.cos(a)
            y, z = y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)
            x, z = x * math.cos(c) - z * math.sin(c), x * math.sin(c) + z * math.cos(c)
            k = 1 / (2.2 - w)             # 4D → 3D perspective, then flat
            pts.append((x * k, y * k))
        h = _hull(pts)
        r = max((math.hypot(*p) for p in h), default=0.0) or 1.0      # unit-size outline
        h = [(p[0] / r, p[1] / r) for p in h]
        planes = []                        # each hull edge as n·p ≤ d
        for i, p in enumerate(h):
            q = h[(i + 1) % len(h)]
            nx, ny = q[1] - p[1], p[0] - q[0]
            ln = math.hypot(nx, ny) or 1
            nx, ny = nx / ln, ny / ln
            d = nx * p[0] + ny * p[1]
            if d > 1e-6:
                planes.append((nx / d, ny / d))
        return planes

    def gauge(self, lt, t):
        if self._t != t:
            self._t, self._planes = t, self._outline(t)
        dx, dy = lt.x - self.cx, (lt.y - self.cy) * 1.15
        return max((nx * dx + ny * dy for nx, ny in self._planes), default=0.0)


_ALL: tuple[type[Effect], ...] = (Wash, Ripple, Wobble, Heat, Fireworks, Hearts, Beat, Zoom)
EFFECTS: dict[str, Callable[..., Effect]] = {e.name: e for e in _ALL}


def make(name: str, lights: Sequence[Light], *, shape: str = "Tesseract") -> Effect:
    """A fresh run of the effect called `name` over `lights`."""
    if name == "zoom":
        return Zoom(lights, shape=shape)
    return EFFECTS[name](lights)
