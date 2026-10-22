"""Fader tapers — port of the taper objects of hyperspace.html.

A taper owns both directions of the mapping between an integer fader
position and the real value stored in the chain, and every pair
round-trips exactly: unmap(map(p)) == p over the whole throw. That law is
what stops selecting a band or loading a scene from walking a fader
sideways. LIN vs LOG per control is a considered decision (ENGINEERING.md,
audio chain section, "Fader tapers") — don't re-litigate it here.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

OCT = 20     # slider steps per doubling, gain-like controls
OCT_T = 12   # slider steps per doubling, time constants


def clamp(x, a, b):
    """The package's one clamp (audit R10). tempo.py, lfo.py and the hands
    package keep a private copy: they import nothing from the package.
    NaN lands on `a`, never through: a NaN base once made every integer
    and enum param raise in `reg.apply` each frame (plan 14 WP1)."""
    return a if not x >= a else min(x, b)


@dataclass(frozen=True)
class Taper:
    steps: int
    log: bool
    map: Callable[[int], float] = field(repr=False)
    unmap: Callable[[float], int] = field(repr=False)
    unity: int | None = None  # position of the detent notch, if any


def exp_zero(u: int, n: int) -> Taper:
    """Exponential with a hard zero at position 0; unity detent at u."""
    return Taper(
        steps=n, unity=u, log=True,
        map=lambda p: 0.0 if p <= 0 else 2.0 ** ((p - u) / OCT),
        unmap=lambda v: 0 if v <= 0 else clamp(round(u + OCT * math.log2(v)), 1, n),
    )


def exp_pure(u: int, n: int) -> Taper:
    """Exponential with no zero — for quantities never legitimately off."""
    return Taper(
        steps=n, unity=u, log=True,
        map=lambda p: 2.0 ** ((p - u) / OCT),
        unmap=lambda v: clamp(round(u + OCT * math.log2(max(v, 1e-9))), 0, n),
    )


def exp_time(v0: float, n: int) -> Taper:
    """Exponential time constant; v0 is ms at position 0, value stored in s."""
    return Taper(
        steps=n, log=True,
        map=lambda p: v0 * 2.0 ** (p / OCT_T) / 1000,
        unmap=lambda s: clamp(round(OCT_T * math.log2(max(s * 1000, 1e-6) / v0)), 0, n),
    )


def lin_t(d: float, n: int) -> Taper:
    """Linear: value = position / d."""
    return Taper(
        steps=n, log=False,
        map=lambda p: p / d,
        unmap=lambda v: clamp(round(v * d), 0, n),
    )


def lin_db(lo: float, hi: float, n: int) -> Taper:
    """dB trim: position 0 is a true −∞; 1..n runs lo..hi dB at 1 dB/step.

    Marked LIN and that is correct, not a shortcut — dB is already a
    logarithm; an exponential over a dB scale would take the log twice.
    """
    return Taper(
        steps=n, log=False,
        unity=round(1 - lo * (n - 1) / (hi - lo)),
        map=lambda p: -math.inf if p <= 0 else lo + (hi - lo) * (p - 1) / (n - 1),
        unmap=lambda v: (
            clamp(round((v - lo) * (n - 1) / (hi - lo)) + 1, 1, n)
            if math.isfinite(v)
            else 0
        ),
    )


# ---- module-level fader tapers, exactly the reference's instances ----

T_TRIM_LO, T_TRIM_HI = -60, 12
T_TRIM = lin_db(T_TRIM_LO, T_TRIM_HI, T_TRIM_HI - T_TRIM_LO + 1)

# 4D perspective: exponential in (D−1) — even in what the eye reads.
T_DEPTH = Taper(
    steps=160, log=True,
    map=lambda p: 1 + 0.05 * 2.0 ** (p / OCT),
    unmap=lambda v: clamp(round(OCT * math.log2(max(v - 1, 1e-6) / 0.05)), 0, 160),
)

def count(lin: int, top: int, per_oct: int) -> Taper:
    """A whole-number count: position p is p itself up to `lin` (every
    count reachable, 0 included), then exponential at `per_oct` steps a
    doubling up to `top`. `lin` ≥ per_oct / ln 2 keeps every step a new
    count. map() takes a float position and returns a whole number."""
    steps = lin + round(per_oct * math.log2(top / lin))
    return Taper(
        steps=steps, log=False,
        map=lambda p: (max(0, round(p)) if p <= lin
                       else min(top, round(lin * 2.0 ** ((p - lin) / per_oct)))),
        unmap=lambda v: (clamp(round(v), 0, lin) if v <= lin
                         else clamp(round(lin + per_oct * math.log2(v / lin)), lin, steps)),
    )


# the instance count (view.instances): 0–64 one at a time, then to 4096 at
# 40 steps a doubling — 304 detents, every copy count to 64 on the throw
T_INSTANCES = count(64, 4096, 40)

T_DRIVE = exp_zero(100, 160)   # master audio drive: off, 0.03×–8.00×
T_DYN = exp_zero(80, 120)      # dynamics: bypass, then 0.06×–4.00×
T_BRIGHT = exp_pure(60, 100)   # brightness: 0.13×–4.00×, never off
T_SPEED = exp_zero(120, 160)   # rotation speed: stop, then 0.016–4.00 rad/s


# ---- readout formatters ----

def fmt_gain(v: float) -> str:
    return "off" if v <= 0 else f"{v:.2f}×"


def fmt_db(v: float) -> str:
    if not math.isfinite(v):
        return "off"
    sign = "+" if v > 0 else "−" if v < 0 else ""
    return f"{sign}{abs(v):.0f} dB"


def fmt_time(s: float) -> str:
    ms = s * 1000
    if ms >= 1000:
        return f"{ms / 1000:.2f} s"
    if ms >= 100:
        return f"{round(ms)} ms"
    return f"{ms:.2f} ms" if ms < 10 else f"{ms:.1f} ms"


# ---- the per-band knob specs (strip order == chain order) ----

@dataclass(frozen=True)
class Knob:
    key: str
    label: str
    t: Taper
    fmt: Callable[[float], str] = field(repr=False)
    tip: str = ""


KNOBS = [
    Knob("trim", "Input trim", T_TRIM, fmt_db,
         "LIN, off then −60 dB to +12 dB in 1 dB steps, detent at 0. Input gain on what "
         "this band hears, ahead of the envelope, window and gate — a channel trim, not "
         "a drive. At the bottom notch the band hears nothing at all."),
    Knob("exp", "Contrast", lin_t(40, 160), lambda v: f"1:{1 + v:.2f}",
         "LIN, 1:1 to 1:5. Upward expansion about this band's running average — the "
         "inverse of what the mastering limiter did. Pulls dynamics back out of a "
         "brickwalled track."),
    Knob("trn", "Transient", lin_t(100, 100), lambda v: f"{round(v * 100)}%",
         "LIN, 0–100%. Blends the fader from following level toward following change. "
         "A limiter flattens level but cannot flatten change. At 100% the plane only "
         "moves on hits."),
    Knob("pre", "Pre-drive", exp_zero(80, 140), fmt_gain,
         "LOG, off then 0.06× to 8.00×, detent at unity. Gain into the transfer "
         "function."),
    Knob("post", "Post-drive", exp_zero(80, 140), fmt_gain,
         "LOG, off then 0.06× to 8.00×, detent at unity. Gain out of the transfer — "
         "how much this band contributes overall."),
    Knob("atk", "Attack", exp_time(0.5, 144), fmt_time,
         "LOG, 0.5 ms to 2.05 s, doubling every 12 steps. How fast the rolling window "
         "rises. Short catches transients; long tracks the swell."),
    Knob("dec", "Decay", exp_time(5, 144), fmt_time,
         "LOG, 5 ms to 20.5 s, doubling every 12 steps. How fast the window falls — how "
         "long the band keeps driving after the sound stops."),
    Knob("thr", "Threshold", lin_t(200, 120), lambda v: f"{v:.3f}",
         "LIN, 0 to 0.60 in steps of 0.005 — linear here IS logarithmic, the gated "
         "signal is already a dB scale. Below this the band outputs nothing and its "
         "plane stops dead."),
]
