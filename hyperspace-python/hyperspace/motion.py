"""Motion — the envelope followers the analyzer is made of, for any signal.

The analyzer's expressiveness is a handful of one-pole followers: the level
path's asymmetric attack / decay per band, the transient path's fast
tracker, the STAC and SLEW shapers. They are `pole` and `follow` here, and
the chain calls them (analyzer.py, bands.py) — the same arithmetic, to the
bit, so the parity oracle still holds. Beside them, `spring`: a damped
spring, solved exactly per step, so it is frame-rate independent and stable
at any dt.

A `Motion` is a feel: how a reading travels to where the source is. A route
row carries one (`routing.Binding.motion`) and the Router runs it on the
row's reading before push / position, so a stick that snaps back to centre
arrives at the param as a glide or a bounce. A row with none takes its
source's own feel (`Router.feel_of`): the pad's, a session setting, for
the `axis` lanes — the same knobs drive the sticks' default camera job.

  follow   asymmetric one-pole, the analyzer's level path: `atk` seconds
           moving away from rest, `rel` seconds moving back toward it.
           About rest, not up / down, so a centred stick is fast out and
           slow home in either direction; at rest 0 it is the analyzer's
           ``u > env`` exactly.
  spring   a mass on a spring toward the reading, set the way Apple's
           springs are (WWDC23, "Animate with springs"): `dur` its
           perceptual duration — the undamped period, how long it feels
           — and `bounce`, 0 the fastest arrival with no overshoot,
           above 0 it overshoots and rings (toward 1, forever), below 0
           it creeps. Exactly a natural frequency and a damping ratio
           (`hz` = 1 / dur; `damp` = 1 − bounce, or 1 / (1 + bounce)
           below 0), which the kernel runs on. SPRINGS names a few.

Times are seconds, τ the one-pole's time constant (63 % of the way in τ).

`response` and `settle` say what a feel does to a jump, in closed form —
where the reading is t seconds on, and when it has arrived. The panel
plots them beside a feel's knobs (ui_feel.py).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields
from functools import lru_cache

MODES = ("off", "follow", "spring")

ATK_MAX = 2.0        # s — the panel's throws; a file may hold more
REL_MAX = 4.0
HZ_MIN, HZ_MAX = 0.1, 12.0       # the kernel's; a file's hz / damp convert (Motion.from_json)
DAMP_MAX = 3.0
DUR_MIN, DUR_MAX = 0.05, 4.0     # s — the panel's spring throws; 1 / HZ_MAX … under 1 / HZ_MIN
BOUNCE_MIN, BOUNCE_MAX = -0.75, 0.95     # ζ 4 … ζ 0.05
# the named springs: perceptual duration (s), bounce. Apple's smooth and
# bouncy, a snappier snappy, and two slower ends of the range
SPRINGS = {
    "snappy": (0.3, 0.15),
    "smooth": (0.5, 0.0),
    "bouncy": (0.5, 0.3),
    "wobbly": (0.8, 0.6),
    "lazy": (1.2, 0.0),
}
SETTLE = 1e-4       # a Follower this close to its target, and this slow, lands
_CRIT = 1e-6         # |damp − 1| under this is critical damping
BAND = 0.02          # `settle`: within this of where it is going counts as arrived


# ------------------------------------------------------------- kernels

def pole(x: float, target: float, dt: float, tau: float) -> float:
    """One step of a one-pole toward `target` with time constant `tau`
    (≤ 0: arrive at once). The analyzer's every smoother is this line."""
    if tau <= 0:
        return target
    return x + (target - x) * (1 - math.exp(-dt / tau))


def follow(x: float, target: float, dt: float, atk: float, rel: float,
           rest: float = 0.0) -> float:
    """The asymmetric one-pole: `atk` while the target is farther from
    `rest` than the follower is, `rel` otherwise. With rest 0 and readings
    ≥ 0 this is the analyzer's ``atk if u > env else dec``."""
    tau = atk if abs(target - rest) > abs(x - rest) else rel
    return pole(x, target, dt, tau)


def spring(x: float, v: float, target: float, dt: float, hz: float,
           damp: float) -> tuple[float, float]:
    """One exact step of a damped spring pulling (x, v) toward a target
    held for the step: ÿ = −ω²y − 2ζωẏ about the target, ω = 2π·hz,
    ζ = damp. Closed form for each regime, so no dt is too long."""
    if hz <= 0:
        return target, 0.0
    w = 2 * math.pi * hz
    z = max(damp, 0.0)
    y0, v0 = x - target, v
    if abs(z - 1) < _CRIT:                       # critical
        e = math.exp(-w * dt)
        c = v0 + w * y0
        return target + (y0 + c * dt) * e, (v0 - w * c * dt) * e
    if z < 1:                                    # under-damped: rings
        wd = w * math.sqrt(1 - z * z)
        e = math.exp(-z * w * dt)
        cs, sn = math.cos(wd * dt), math.sin(wd * dt)
        y = e * (y0 * cs + (v0 + z * w * y0) / wd * sn)
        vy = e * (v0 * cs - (w * w * y0 + z * w * v0) / wd * sn)
        return target + y, vy
    s = math.sqrt(z * z - 1)                     # over-damped: creeps
    r1, r2 = -w * (z - s), -w * (z + s)
    c2 = (v0 - r1 * y0) / (r2 - r1)
    c1 = y0 - c2
    e1, e2 = math.exp(r1 * dt), math.exp(r2 * dt)
    return target + c1 * e1 + c2 * e2, r1 * c1 * e1 + r2 * c2 * e2


# ---------------------------------------------------------------- feel

def spring_hz(dur: float, bounce: float) -> tuple[float, float]:
    """A perceptual duration and a bounce as the kernel's (hz, damp)."""
    hz = 0.0 if dur <= 0 else 1.0 / dur
    damp = 1.0 - bounce if bounce >= 0 else 1.0 / max(1.0 + bounce, 1e-6)
    return hz, damp


def spring_feel(hz: float, damp: float) -> tuple[float, float]:
    """The kernel's (hz, damp) as a perceptual duration and a bounce —
    `spring_hz` inverted, for a file written with hz / damp."""
    dur = 1.0 / hz if hz > 0 else DUR_MAX
    bounce = 1.0 - damp if damp <= 1 else 1.0 / damp - 1.0
    return dur, bounce


def spring_name(dur: float, bounce: float) -> str | None:
    """The SPRINGS entry these knobs are, None when they are no preset."""
    for name, (d, b) in SPRINGS.items():
        if abs(d - dur) < 1e-3 and abs(b - bounce) < 1e-3:
            return name
    return None


@dataclass(frozen=True)
class Motion:
    """A feel, as a route row or the pad's session setting holds it."""

    mode: str = "follow"
    atk: float = 0.02     # follow: s, away from rest
    rel: float = 0.35     # follow: s, back toward rest
    dur: float = 2 / 3    # spring: perceptual duration, s (1.5 Hz)
    bounce: float = 0.4   # spring: 0 none, toward 1 rings, below 0 creeps (ζ 0.6)

    @property
    def on(self) -> bool:
        return self.mode in ("follow", "spring")

    @property
    def hz(self) -> float:
        """The spring's natural frequency, what the kernel runs on."""
        return spring_hz(self.dur, self.bounce)[0]

    @property
    def damp(self) -> float:
        """The spring's damping ratio, what the kernel runs on."""
        return spring_hz(self.dur, self.bounce)[1]

    def to_json(self) -> dict:
        """The mode and the knobs it reads — the other mode's stay out of the file."""
        d = asdict(self)
        keep = {"follow": ("atk", "rel"), "spring": ("dur", "bounce")}.get(self.mode, ())
        return {k: v for k, v in d.items() if k == "mode" or k in keep}

    @classmethod
    def from_json(cls, d) -> Motion | None:
        """A file's motion: a dict, or None. An unknown mode reads as off,
        unknown keys are ignored, a missing knob takes its default. A
        spring written as hz / damp (before the perceptual knobs) reads as
        the same spring."""
        if d is None:
            return None
        if isinstance(d, Motion):
            return d
        names = {f.name for f in fields(cls)}
        kw = {k: (str(v) if k == "mode" else float(v)) for k, v in d.items() if k in names}
        if ("hz" in d or "damp" in d) and not ("dur" in kw or "bounce" in kw):
            kw["dur"], kw["bounce"] = spring_feel(float(d.get("hz", 1.5)),
                                                  float(d.get("damp", 0.6)))
        if kw.get("mode") not in MODES:
            kw["mode"] = "off"
        return cls(**kw)

    def describe(self) -> str:
        if self.mode == "follow":
            return f"follow {self.atk * 1000:.0f}/{self.rel * 1000:.0f} ms"
        if self.mode == "spring":
            name = spring_name(self.dur, self.bounce)
            return (f"spring {name}" if name else
                    f"spring {self.dur * 1000:.0f} ms, bounce {self.bounce * 100:.0f} %")
        return "no motion"


OFF = Motion("off")


class Follower:
    """One signal's motion state: where it is and how fast it moves."""

    __slots__ = ("v", "x")

    def __init__(self, x: float = 0.0):
        self.x, self.v = float(x), 0.0

    def step(self, target: float, dt: float, m: Motion, rest: float = 0.0) -> float:
        target = float(target)
        if m.mode == "follow":
            self.x, self.v = follow(self.x, target, dt, m.atk, m.rel, rest), 0.0
        elif m.mode == "spring":
            self.x, self.v = spring(self.x, self.v, target, dt, m.hz, m.damp)
        else:
            self.x, self.v = target, 0.0
        # settled: land exactly, so a tail that would decay forever stops
        # writing (a relative writer's nudge would never let undo settle)
        if abs(self.x - target) < SETTLE and abs(self.v) < SETTLE * 10:
            self.x, self.v = target, 0.0
        return self.x


# ------------------------------------------------------------ response

def response(m: Motion, t: float, x: float = 0.0, target: float = 1.0,
             rest: float = 0.0) -> float:
    """Where a reading resting at `x` is t s after it jumped to `target`,
    under the feel `m`: its kernel stepped once over the whole time —
    exact, each kernel being closed form for a held target. No motion:
    already there."""
    if t <= 0:
        return x
    if m.mode == "follow":
        return follow(x, target, t, m.atk, m.rel, rest)
    if m.mode == "spring":
        return spring(x, 0.0, target, t, m.hz, m.damp)[0]
    return target


@lru_cache(maxsize=256)    # the panel asks every frame; the knobs change rarely
def settle(m: Motion, home: bool = False) -> float:
    """Seconds until a jump from rest 0 to 1 (`home`: from 1 back to rest)
    stays within BAND of where it is going. follow: ln(1 / BAND) of the
    edge's τ. A spring, the same either way: measured off its own
    response, since critical damping's (1 + ωt)·e^(−ωt) lands later than
    its envelope says — never, undamped. No motion: 0."""
    if m.mode == "follow":
        return max(m.rel if home else m.atk, 0.0) * math.log(1 / BAND)
    if m.mode != "spring" or m.hz <= 0:
        return 0.0
    w, z = 2 * math.pi * m.hz, max(m.damp, 0.0)
    if z <= _CRIT:
        return math.inf
    r = z * w if z <= 1 else w * (z - math.sqrt(z * z - 1))    # the slowest root
    end, n = 8.0 / r, 400                       # its envelope, well inside BAND by then
    for i in range(n, -1, -1):
        if abs(response(m, end * i / n) - 1.0) > BAND:
            return end * min(i + 1, n) / n
    return 0.0
