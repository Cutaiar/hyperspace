"""Six-band analysis chain — port of the audio module of hyperspace.html.

Every constant keeps its reference name (ENGINEERING §4). The known input-trim
non-monotonicity is ported as-is; the fix belongs to plan 06, not the port.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .analysis import Analyser

# ------------------------------------------------------------------ bands

@dataclass
class Band:
    id: str
    plane: int
    pl: str
    lo: float
    hi: float
    atk: float
    rel: float
    dir: int


BANDS = [
    Band("SUB", 5, "ZW", 20, 60, 0.250, 0.850, 1),
    Band("BASS", 3, "XW", 60, 160, 0.015, 0.130, 1),
    Band("MIDB", 4, "YW", 160, 400, 0.006, 0.070, -1),
    Band("MID", 0, "XY", 400, 1200, 0.050, 0.300, -1),
    Band("UPR", 1, "XZ", 1200, 4000, 0.090, 0.500, 1),
    Band("AIR", 2, "YZ", 4000, 14000, 0.180, 0.900, -1),
]

# -------------------------------------------------------------- constants

NOM = 1.0        # nominal — a band working normally
KNEE = 1.25      # where the soft ceiling starts to bend
HEAD = 2.6       # asymptotic ceiling, input / transfer signal
CEIL = 2.6       # asymptotic ceiling, fader output
DRIVE = 3.2      # fader → rotation rate
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


def clamp(x: float, a: float, b: float) -> float:
    return a if x < a else min(x, b)


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


def default_params() -> list[Params]:
    return [
        Params(1, 0, 1, 1, 0.250, 0.850, 0.075, 0.55, 0.10),   # SUB  sqrt
        Params(7, 0, 1, 1, 0.015, 0.130, 0.075, 0.90, 0.30),   # BASS hold
        Params(8, 0, 1, 1, 0.006, 0.070, 0.075, 0.95, 0.38),   # MIDB staccato
        Params(4, 0, 1, 1, 0.050, 0.300, 0.075, 0.80, 0.22),   # MID  s-curve
        Params(0, 0, 1, 1, 0.090, 0.500, 0.075, 0.85, 0.28),   # UPR  linear
        Params(12, 0, 1, 1, 0.180, 0.900, 0.075, 0.85, 0.32),  # AIR  slew
    ]


DEF_EXP = [0.55, 0.90, 0.95, 0.80, 0.85, 0.85]
DEF_TRN = [0.10, 0.30, 0.38, 0.22, 0.28, 0.32]
DEF_TRIM = [0, 0, 0, 0, 0, 0]

# Scenes: each band row is [fn, pre, post, atk ms, dec ms, thr, exp, trn, trim dB];
# the last three are optional and fall back per band (older rows still load).
PRESETS: list[dict] = [
    {"name": "Balanced",
     "b": [[1, 1, 1, 250, 850, .075, .55, .10], [7, 1, 1, 15, 130, .075, .90, .30],
           [8, 1, 1, 6, 70, .075, .95, .38], [4, 1, 1, 50, 300, .075, .80, .22],
           [0, 1, 1, 90, 500, .075, .85, .28], [12, 1, 1, 180, 900, .075, .85, .32]]},
    {"name": "Kick & Sizzle",
     "b": [[12, 1, .5, 300, 900, .09, .50, .05], [7, 1.4, 1.8, 4, 180, .10, 1.20, .60],
           [5, 1, 1.2, 5, 60, .14, 1.20, .65], [0, 1, .6, 60, 260, .08, .70, .20],
           [2, 1.2, 1, 70, 340, .07, .90, .35], [8, 1.5, 1.6, 10, 150, .08, 1.10, .60]]},
    {"name": "Glacial Drift",
     "b": [[1, 1.2, .9, 400, 1600, .05, .45, 0], [12, 1, .8, 300, 1400, .05, .45, 0],
           [12, 1, .7, 250, 1200, .05, .45, 0], [1, 1, .8, 300, 1400, .05, .45, 0],
           [12, 1.1, .8, 350, 1500, .05, .50, 0], [12, 1.2, .9, 400, 1800, .05, .50, 0]]},
    {"name": "Strobe Cage",
     "b": [[5, 1.2, 1.4, 8, 90, .12, 1.10, .45], [9, 1, 1.6, 4, 60, .12, 1.30, .70],
           [9, 1.2, 1.6, 4, 50, .12, 1.30, .75], [5, 1, 1.3, 10, 110, .12, 1.10, .50],
           [9, 1, 1.5, 8, 90, .12, 1.20, .65], [5, 1.2, 1.4, 12, 130, .12, 1.20, .60]]},
    {"name": "Bass Engine",
     "b": [[1, 1.4, 1.6, 200, 700, .06, .75, .15, 0], [7, 1.5, 2, 8, 140, .07, 1.25, .55, 0],
           [8, 1.4, 1.8, 5, 70, .08, 1.20, .55, 0], [0, 1, .15, 60, 300, .10, .60, .15, -10],
           [0, 1, .1, 90, 500, .10, .60, .15, -16], [0, 1, 0, 180, 900, .10, .60, .15, -24]]},
    {"name": "Air & Lace",
     "b": [[12, 1, .12, 300, 1200, .10, .50, .05, -20], [0, 1, .15, 20, 160, .10, .70, .20, -14],
           [0, 1, .2, 8, 80, .10, .80, .30, -8], [1, 1.2, 1.2, 60, 340, .06, .95, .35, 0],
           [1, 1.3, 1.7, 80, 420, .05, 1.10, .50, 0], [1, 1.4, 2, 140, 700, .05, 1.15, .55, 0]]},
    {"name": "Inverse World",
     "b": [[6, 1, .7, 260, 900, .04, .50, 0], [6, 1, .8, 40, 300, .04, .60, 0],
           [0, 1, 1, 10, 90, .07, .95, .35], [0, 1, 1, 60, 320, .07, .80, .25],
           [1, 1, 1.1, 90, 500, .06, .85, .25], [6, 1, .7, 200, 900, .04, .55, 0]]},
    {"name": "Percussive",
     "b": [[8, 1.2, 1.2, 6, 140, .09, 1.10, .55], [8, 1.3, 1.5, 4, 110, .09, 1.25, .75],
           [8, 1.3, 1.5, 4, 80, .09, 1.25, .80], [8, 1.2, 1.3, 6, 140, .09, 1.15, .70],
           [8, 1.2, 1.3, 8, 180, .09, 1.15, .70], [8, 1.2, 1.2, 10, 220, .09, 1.10, .65]]},
    {"name": "Tremolo Web",
     "b": [[7, 1, 1, 200, 700, .07, .60, .10], [7, 1.1, 1.2, 20, 240, .07, .85, .25],
           [10, 1.2, 1.3, 10, 120, .08, .95, .30], [10, 1.2, 1.4, 50, 300, .07, .90, .25],
           [10, 1.3, 1.4, 80, 420, .06, .90, .25], [11, 1.2, 1.2, 150, 700, .06, .85, .20]]},
    {"name": "Harmonic Bloom",
     "b": [[1, 1.2, 1, 300, 1000, .06, .55, .05], [1, 1.2, 1.1, 60, 420, .06, .80, .15],
           [4, 1.1, 1.1, 20, 200, .07, .85, .20], [4, 1.2, 1.2, 80, 420, .06, .85, .20],
           [1, 1.3, 1.3, 120, 600, .05, .90, .25], [1, 1.3, 1.2, 200, 900, .05, .90, .25]]},
    {"name": "Slow Bass / Fast Air",
     "b": [[1, 1.1, 1, 500, 1800, .05, .45, 0], [1, 1.1, 1, 300, 1200, .05, .55, .05],
           [0, 1, 1, 60, 400, .07, .85, .25], [0, 1, 1.1, 20, 160, .08, 1.00, .45],
           [2, 1.2, 1.4, 8, 90, .09, 1.20, .65], [8, 1.3, 1.6, 4, 60, .10, 1.25, .75]]},
]


# ------------------------------------------------------------------ chain

class Chain:
    """The full per-frame chain: spectrum in, PLANEDRIVE out."""

    def __init__(self, analyser: Analyser, params: list[Params] | None = None):
        self.an = analyser
        self.params = params if params is not None else default_params()
        self.gain = 1.0
        self.dyn = 1.0
        self.trim = 0.0  # global input trim, dB
        self.bin_lo = []
        self.bin_hi = []
        for b in BANDS:
            lo, hi = analyser.band_bins(b.lo, b.hi)
            self.bin_lo.append(lo)
            self.bin_hi.append(hi)
        self.env = np.zeros(6)
        self.fast = np.zeros(6)
        self.slow = np.zeros(6)
        self.fpk = np.full(6, 0.2)
        self.peak = np.full(6, 0.25)
        self.val = np.full(6, 0.25)
        self.avg = np.full(6, 0.5)
        self.dvr = np.full(6, DEV_AIM * DEV_AIM)
        self.norm = np.zeros(6)
        self.inp = np.zeros(6)
        self.out = np.zeros(6)
        self.st: list[dict] = [{} for _ in range(6)]
        self.warm = 0
        self.planedrive = np.ones(6)

    def apply_preset_band(self, k: int, i: int) -> None:
        p, P = PRESETS[k]["b"][i], self.params[i]
        P.fn, P.pre, P.post = p[0], p[1], p[2]
        P.atk, P.dec, P.thr = p[3] / 1000, p[4] / 1000, p[5]
        P.exp = p[6] if len(p) > 6 else DEF_EXP[i]
        P.trn = p[7] if len(p) > 7 else DEF_TRN[i]
        P.trim = p[8] if len(p) > 8 else DEF_TRIM[i]
        self.st[i] = {}

    def apply_preset(self, k: int) -> None:
        for i in range(len(PRESETS[k]["b"])):
            self.apply_preset_band(k, i)

    def step(self, dt: float) -> np.ndarray:
        """One frame: read the analyser, run the chain, return PLANEDRIVE."""
        freq = self.an.float_frequency_data()
        dyn = self.dyn

        k_pk = 1 - math.exp(-dt / PK_TAU)
        k_val = 1 - math.exp(-dt / VAL_TAU)
        k_slow = 1 - math.exp(-dt / SLOW_T)
        fpk_dec = math.exp(-dt / 2.5)

        self.warm += 1
        seeding = self.warm <= 3
        k_avg = 1 - math.exp(-dt / (0.25 if self.warm < 60 else MEAN_TAU))

        for i in range(6):
            P = self.params[i]

            # band RMS from the power spectrum, into u where 1.0 is nominal
            mags = 10.0 ** (freq[self.bin_lo[i] : self.bin_hi[i] + 1] / 20.0)
            rms = math.sqrt(float(np.mean(mags * mags))) if len(mags) else 0.0
            db = 20 * math.log10(rms + 1e-9)

            # input trim, applied pre-envelope AND as tU offset below —
            # the double application is the reference's design (and its bug)
            t_db = P.trim + self.trim
            t_u = t_db / U_SPAN
            u = clamp((db + t_db - U_LO) / U_SPAN, 0, 2.5)

            # LEVEL path — asymmetric one-pole
            tau = P.atk if u > self.env[i] else P.dec
            self.env[i] += (u - self.env[i]) * (1 - math.exp(-dt / tau))

            # TRANSIENT path — fast minus slow, relative flux, peak-normalised
            ft = FAST_A if u > self.fast[i] else FAST_R
            self.fast[i] += (u - self.fast[i]) * (1 - math.exp(-dt / ft))
            self.slow[i] += (u - self.slow[i]) * k_slow
            flux = clamp((self.fast[i] - self.slow[i]) / (self.slow[i] + FLUX_K) * FLUX_G, 0, 1.5)
            self.fpk[i] = max(flux, self.fpk[i] * fpk_dec, FLUX_MIN)
            trn = clamp(flux / self.fpk[i], 0, 1) * TRN_HEAD

            # WINDOW — moving ceiling and floor
            if seeding:
                self.peak[i] = self.val[i] = self.env[i]
            self.peak[i] = max(self.env[i], self.peak[i] + (self.env[i] - self.peak[i]) * k_pk)
            self.val[i] = min(self.env[i], self.val[i] + (self.env[i] - self.val[i]) * k_val)

            lo, hi = self.val[i], max(self.peak[i], PK_MIN)
            if hi - lo < SPAN_MIN:
                c = (hi + lo) * 0.5
                lo, hi = c - SPAN_MIN * 0.5, c + SPAN_MIN * 0.5

            conf = clamp((hi - CONF_LO) / CONF_SPAN, 0, 1)
            da = clamp(dyn, 0, 1) * conf
            n_dyn = clamp((self.env[i] - lo) / (hi - lo), 0, 1)
            n_abs = clamp(self.env[i] / max(hi, PK_MIN), 0, 1)
            nrm = n_abs + (n_dyn - n_abs) * da
            self.norm[i] = nrm

            # EXPANSION about the running mean, scaled by how squashed the band is
            squash = clamp(1 - (self.peak[i] - self.val[i]) / OPEN_SPAN, 0, 1)
            if seeding:
                self.avg[i] = nrm
            self.avg[i] += (nrm - self.avg[i]) * k_avg
            c_ratio = 1 + P.exp * dyn * conf * (SQ_FLOOR + (1 - SQ_FLOOR) * squash)
            dev = (nrm - self.avg[i]) * c_ratio

            # gain staging on the expanded deviation (attenuate-only), warm-up fade
            if seeding:
                self.dvr[i] = dev * dev
            self.dvr[i] += (dev * dev - self.dvr[i]) * k_avg
            dev *= min(1, DEV_AIM / max(math.sqrt(self.dvr[i]), DEV_MIN))
            dev *= min(1, self.warm / WARM_F)
            lvl = TARGET * conf + dev

            x = lvl + (trn * conf - lvl) * P.trn + t_u
            if self.env[i] < P.thr:
                x = 0.0  # gate: band goes quiet, plane stops
            self.inp[i] = x if x > 0 else 0.0

        # harmonic coupling — last thing before the single input saturation
        for i in range(6):
            up = min(self.inp[min(i + 1, 5)], 1)
            coh = math.sqrt(min(self.inp[i], 1) * up)
            self.inp[i] = soft_ceil(self.inp[i] * (1 + COUPLE * coh), KNEE, HEAD)

        # TRANSFER stage — pre-drive → shaper → post-drive → fader
        for i in range(6):
            P = self.params[i]
            x = soft_ceil(self.inp[i] * P.pre, KNEE, HEAD)
            y = SHAPERS[P.fn].f(self.st[i], x, dt)
            self.out[i] = soft_ceil(y * P.post, KNEE, CEIL)
            self.planedrive[BANDS[i].plane] = BANDS[i].dir * self.out[i] * DRIVE * self.gain

        return self.planedrive
