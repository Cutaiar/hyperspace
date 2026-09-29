"""The analysis chain's parts — port of the audio module of hyperspace.html.

Every constant keeps its reference name (ENGINEERING §4). The known input-trim
non-monotonicity is ported as-is on the AUTO path; a band switched to MANUAL
normalisation (``Params.norm``, plan 11 / audit A10) takes a plain monotonic
trim instead.

The chain itself lives in analyzer.py since plan 07 (N bands, not six);
this module keeps what it is made of — the reference band table (the six
edges, planes and directions the legacy6 preset and the parity oracle
need), the headroom constants, the transfer functions and the per-band
Params. The scenes are the band presets in library/band/*.json
(control.SCENES names them). The reference's per-band attack / release
windows live once, in `default_params()`, and `balanced.json` is pinned
to that table by a test. The constants that belong to other layers moved
out in plan 11: `DRIVE` (fader → rotation rate) is `params.DRIVE`, the
meter's nominal line is `ui.NOM`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# the package's one clamp (tapers.py, audit R10), re-exported under the
# reference's name: the chain and the frozen oracle (tests/legacy_chain.py)
# read it from here like every other reference constant
from .tapers import clamp  # noqa: F401

# ------------------------------------------------------------------ bands

@dataclass
class Band:
    """One reference band: its edges and the plane it drove. The attack /
    release windows are not here — `default_params()` is their one home."""

    id: str
    plane: int
    pl: str
    lo: float
    hi: float
    dir: int


BANDS = [
    Band("SUB", 5, "ZW", 20, 60, 1),
    Band("BASS", 3, "XW", 60, 160, 1),
    Band("MIDB", 4, "YW", 160, 400, -1),
    Band("MID", 0, "XY", 400, 1200, -1),
    Band("UPR", 1, "XZ", 1200, 4000, 1),
    Band("AIR", 2, "YZ", 4000, 14000, -1),
]

# -------------------------------------------------------------- constants

KNEE = 1.25      # where the soft ceiling starts to bend
CEIL = 2.6       # asymptotic ceiling, fader output
HEAD = CEIL      # the reference's name for the same ceiling on the input / transfer signal
U_LO, U_SPAN = -80.0, 56.0
PK_TAU, VAL_TAU = 2.5, 6.0
PK_MIN, SPAN_MIN = 0.10, 0.04
CONF_LO, CONF_SPAN = 0.08, 0.18
OPEN_SPAN = 0.22
SQ_FLOOR = 0.35
MEAN_TAU, TARGET = 2.5, 0.72
DEV_AIM, DEV_MIN, WARM_F = 0.70, 0.06, 60
COUPLE = 0.7
FAST_A, FAST_R, SLOW_T = 0.003, 0.060, 0.30
FLUX_G, FLUX_K, FLUX_MIN, TRN_HEAD = 3.2, 0.15, 0.12, 1.4


def soft_ceil(x: float, knee: float, ceil: float) -> float:
    """Identity below the knee; bends toward `ceil` above it, never arrives.

    Slope 1 at the knee, t^-3 tail — strictly increasing everywhere, which
    is the whole point (a flat top is zero dynamics, ENGINEERING §4).
    """
    if x <= knee:
        return x if x > 0 else 0.0
    r = ceil - knee
    t = (x - knee) / r
    return knee + r * t / math.sqrt(1 + t * t)


# ---------------------------------------------------------------- shapers

def _sh_lin(s, x, dt):
    return x


def _sh_sqrt(s, x, dt):
    return math.sqrt(x)


def _sh_sq(s, x, dt):
    return x * x


def _sh_cube(s, x, dt):
    return x * x * x


def _sh_curv(s, x, dt):
    return x * x * (3 - 2 * x) if x < 1 else x  # linear past nominal


def _sh_gate(s, x, dt):
    return (x if x > 1 else 1.0) if x > 0.35 else 0.0  # keep the overshoot


def _sh_inv(s, x, dt):
    return 1 - soft_ceil(x, 0.5, 1)  # approaches rest, never flat


def _sh_hold(s, x, dt):
    s["h"] = max(x, s.get("h", 0.0) - dt / 0.7)
    return s["h"]


def _sh_stac(s, x, dt):
    e = s.get("e", 0.0)
    tau = 0.004 if x > e else 0.075
    e += (x - e) * (1 - math.exp(-dt / tau))
    s["e"] = e
    return e if e > 0.12 else 0.0


def _sh_chop(s, x, dt):
    s["p"] = (s.get("p", 0.0) + dt * 5) % 1
    return x if s["p"] < 0.5 else 0.0


def _sh_trem(s, x, dt):
    s["p"] = (s.get("p", 0.0) + dt * 6) % 1
    return x * (0.3 + 0.7 * (0.5 + 0.5 * math.sin(s["p"] * 6.2832)))


def _sh_snh(s, x, dt):
    s["t"] = s.get("t", 0.0) + dt
    if s["t"] > 0.18:
        s["t"] = 0.0
        s["v"] = x
    return s.get("v") or 0.0


def _sh_slew(s, x, dt):
    e = s.get("e", 0.0)
    e += (x - e) * (1 - math.exp(-dt / 0.8))
    s["e"] = e
    return e


@dataclass(frozen=True)
class Shaper:
    tag: str
    name: str
    f: object = field(repr=False)


SHAPERS = [
    Shaper("LIN", "Linear — Y = X", _sh_lin),
    Shaper("SQRT", "Sqrt — Y = √X, lifts quiet", _sh_sqrt),
    Shaper("SQ", "Squared — Y = X², punchier", _sh_sq),
    Shaper("CUBE", "Cubed — Y = X³, peaks only", _sh_cube),
    Shaper("CURV", "S-curve — soft knee both ends", _sh_curv),
    Shaper("GATE", "Gate — hard on above threshold", _sh_gate),
    Shaper("INV", "Invert — loud stops, silence spins", _sh_inv),
    Shaper("HOLD", "Peak hold — instant rise, slow fall", _sh_hold),
    Shaper("STAC", "Staccato — 4 ms attack, 75 ms decay", _sh_stac),
    Shaper("CHOP", "Chop — square gate at 5 Hz", _sh_chop),
    Shaper("TREM", "Tremolo — 6 Hz sine, 70% depth", _sh_trem),
    Shaper("S&H", "Sample & hold — re-samples every 180 ms", _sh_snh),
    Shaper("SLEW", "Slew — 800 ms smoothing, glacial drift", _sh_slew),
]

# ----------------------------------------------------- per-band parameters

@dataclass
class Params:
    fn: int
    trim: float
    pre: float
    post: float
    atk: float
    dec: float
    thr: float
    exp: float
    trn: float
    norm: int = 0    # NORMS index: 0 auto (the reference's adaptive window), 1 manual


# per-band normalisation (plan 11, audit A10): AUTO is the reference chain
# bit for bit; MANUAL bypasses the adaptive window and trim is a plain gain
NORMS = ["AUTO", "MANUAL"]


def default_params() -> list[Params]:
    return [
        Params(1, 0, 1, 1, 0.250, 0.850, 0.075, 0.55, 0.10),   # SUB  sqrt
        Params(7, 0, 1, 1, 0.015, 0.130, 0.075, 0.90, 0.30),   # BASS hold
        Params(8, 0, 1, 1, 0.006, 0.070, 0.075, 0.95, 0.38),   # MIDB staccato
        Params(4, 0, 1, 1, 0.050, 0.300, 0.075, 0.80, 0.22),   # MID  s-curve
        Params(0, 0, 1, 1, 0.090, 0.500, 0.075, 0.85, 0.28),   # UPR  linear
        Params(12, 0, 1, 1, 0.180, 0.900, 0.075, 0.85, 0.32),  # AIR  slew
    ]


def default_band_params() -> Params:
    """A band added beyond the six: linear, MID's timing."""
    return Params(0, 0, 1, 1, 0.050, 0.300, 0.075, 0.80, 0.22)


# A band past a scene's rows takes default_band_params() — the linear,
# MID-timed strip above. The scenes themselves are the band presets in
# library/band/*.json (control.SCENES names them in combo order); since
# plan 11 this module holds no copy of them.

