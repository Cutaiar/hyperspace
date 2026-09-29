"""N-band graphic-EQ analyzer — the six-band chain, reshaped (plan 07 WP4a).

The per-band chain math is bands.py's, moved here untouched: spectrum in,
`atk dec thr exp trn trim fn pre post` per band, N lanes out. What changed
is the shape. A band is no longer a fixed row of the BANDS table but a
`BandSpec` — centre frequency, Q and a weighting curve — and there are
1..N_MAX of them, added, removed and reordered at runtime.

Band model. The stored form is (f, q): f is the geometric centre in Hz and
q = f / (hi − lo), the usual band-pass Q, so lo and hi are derived
(`edges`) and the centre sits at the log midpoint of the two — which is
exactly how the reference table's edges relate (SUB 20–60 has f = 34.6 Hz,
q = 0.87). f/q is what the layout schema carries, what a fader maps evenly
(f is log-scaled), and what an editor's drag handles want: move f and the
band keeps its shape. The edges are a readout.

Weighting. Each band owns a weight vector over the FFT bins, recomputed
only when f/q/curve change; band RMS is the weighted mean of the power
spectrum under it. `RECT` is today's behaviour bit for bit — every bin
between the edges at the reference's exact rounding (`Analyser.band_bins`),
weight 1.0 — and the other curves are shaped in log frequency about the
centre with the edges as their half-power points (TRI: zero at the edges).
Weights are normalised to mean 1 over their support so the u/dB
calibration, the gate threshold and every constant keep their meaning.

Harmonic coupling reads the next band *in frequency order*, which for the
legacy layout is `i + 1` (and the top band reads itself), as before.

Band → plane and `dir` are not the analyzer's business — the output is
`lanes`, and what they drive is the routing table's (routing.py; the
legacy table lives there as the "legacy6" preset).

Spectrum history: a ring of the last HIST_S seconds of spectra on a
log-frequency axis, for the heat map (WP5b). One column every HIST_DT of
frame time; a column is a `maximum.reduceat` over the frame's dB spectrum
into a preallocated row — no per-frame allocation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .analysis import Analyser
from .bands import (
    BANDS,
    CEIL,
    CONF_LO,
    CONF_SPAN,
    COUPLE,
    DEV_AIM,
    DEV_MIN,
    FAST_A,
    FAST_R,
    FLUX_G,
    FLUX_K,
    FLUX_MIN,
    HEAD,
    KNEE,
    MEAN_TAU,
    OPEN_SPAN,
    PK_MIN,
    PK_TAU,
    SHAPERS,
    SLOW_T,
    SPAN_MIN,
    SQ_FLOOR,
    TARGET,
    TRN_HEAD,
    U_LO,
    U_SPAN,
    VAL_TAU,
    WARM_F,
    Params,
    clamp,
    default_band_params,
    default_params,
    soft_ceil,
)

N_MAX = 16
F_LO, F_HI = 20.0, 20000.0     # centre frequency range, Hz
Q_LO, Q_HI = 0.1, 20.0         # from ten octaves wide to a sliver
W_EPS = 1e-4                   # below this weight a bin is outside the band
BUTTER_ORDER = 4

# history ring: HIST_T columns over HIST_S seconds, HIST_F log-spaced bins
HIST_S, HIST_T, HIST_F = 4.0, 240, 256
HIST_DT = HIST_S / HIST_T
HIST_LO = 20.0                 # Hz; the top is Nyquist
HIST_FLOOR = -120.0            # dB, silence and the unwritten ring

_SQRT_2LN2 = math.sqrt(2 * math.log(2))


# --------------------------------------------------------------- f/q ↔ edges

def edges(f: float, q: float) -> tuple[float, float]:
    """(lo, hi) Hz of a band with centre f and Q; hi − lo = f / q, lo·hi = f²."""
    h = 1 / (2 * q)
    r = math.sqrt(1 + h * h)
    return f * (r - h), f * (r + h)


def centre_q(lo: float, hi: float) -> tuple[float, float]:
    """The inverse of `edges`: geometric centre and f / bandwidth."""
    f = math.sqrt(lo * hi)
    return f, f / (hi - lo)


# ------------------------------------------------------------------ curves

# a curve maps x (octaves from the centre) and hw (half-width in octaves,
# the edges) to a weight in [0, 1]; vectorised over x

def _cv_rect(x, hw):
    return np.where(np.abs(x) <= hw, 1.0, 0.0)


def _cv_tri(x, hw):
    return np.maximum(0.0, 1 - np.abs(x) / hw)


def _cv_gauss(x, hw):
    return np.exp(-0.5 * (x / (hw / _SQRT_2LN2)) ** 2)   # half power at the edges


def _cv_butter(x, hw):
    return 1 / (1 + (np.abs(x) / hw) ** (2 * BUTTER_ORDER))


@dataclass(frozen=True)
class Curve:
    tag: str
    name: str
    f: object = field(repr=False)


CURVES = [
    Curve("RECT", "Rectangular — every bin between the edges, equally", _cv_rect),
    Curve("TRI", "Triangular — full at the centre, zero at the edges", _cv_tri),
    Curve("GAUSS", "Gaussian — half power at the edges, soft skirts", _cv_gauss),
    Curve("BUTTER", "Butterworth — flat top, 4th-order skirts, half power at the edges",
          _cv_butter),
]
RECT = 0


def curve_index(c) -> int:
    """A curve tag (any case), a Curve or an index → index into CURVES."""
    if isinstance(c, Curve):
        return CURVES.index(c)
    if isinstance(c, str):
        tags = [cv.tag for cv in CURVES]
        return tags.index(c.upper())
    i = int(c)
    if not 0 <= i < len(CURVES):
        raise ValueError(f"no curve {c}")
    return i


# ------------------------------------------------------------------- bands

@dataclass
class BandSpec:
    """Where a band listens: the spectral half of a band (the chain half is Params)."""
    f: float
    q: float
    curve: int = RECT
    name: str | None = None     # explicit tag; None → named by its centre

    @property
    def label(self) -> str:
        if self.name:
            return self.name
        return f"{self.f:.0f} Hz" if self.f < 1000 else f"{self.f / 1000:.1f} kHz"

    def edges(self) -> tuple[float, float]:
        return edges(self.f, self.q)


def legacy_layout() -> dict:
    """Today's six bands at the reference edges, RECT — the parity anchor."""
    rows = []
    for b in BANDS:
        f, q = centre_q(b.lo, b.hi)
        rows.append({"f": f, "q": q, "curve": CURVES[RECT].tag, "name": b.id})
    return {"bands": rows}


_SCENE_KEYS = ("fn", "trim", "pre", "post", "atk", "dec", "thr", "exp", "trn", "norm")
_INT_KEYS = ("fn", "norm")


def scene_strip(values: dict, n: int, bands=None) -> dict:
    """The complete ``band.{i}.*`` strip a scene lands on `n` bands (or on
    the bands in `bands`): the scene's row where it has one, the default
    strip (default_band_params) for a key or a band it lacks. What the
    scene combo hands the registry, and what apply_scene writes."""
    rows, d = scene_rows(values), default_band_params()
    out: dict = {}
    for i in (range(n) if bands is None else bands):
        row = rows.get(i) or {}
        for k in _SCENE_KEYS:
            v = row.get(k, getattr(d, k))
            out[f"band.{i}.{k}"] = int(v) if k in _INT_KEYS else v
    return out


def scene_rows(values: dict) -> dict[int, dict]:
    """``{"band.3.atk": 0.05, …}`` → ``{3: {"atk": 0.05, …}}``, the strip
    keys only (a layout knob such as ``band.3.f`` is not a scene row)."""
    out: dict[int, dict] = {}
    for pid, v in values.items():
        parts = pid.split(".")
        if (len(parts) == 3 and parts[0] == "band" and parts[1].isdigit()
                and parts[2] in _SCENE_KEYS):
            out.setdefault(int(parts[1]), {})[parts[2]] = v
    return out


def _spec_of(row: dict) -> BandSpec:
    return BandSpec(float(row["f"]), float(row["q"]),
                    curve_index(row.get("curve", RECT)), row.get("name") or None)


# per-band tracker arrays and what a fresh band starts from
_SEEDS = (
    ("env", 0.0), ("fast", 0.0), ("slow", 0.0), ("fpk", 0.2), ("peak", 0.25),
    ("val", 0.25), ("avg", 0.5), ("dvr", DEV_AIM * DEV_AIM), ("norm", 0.0),
    ("inp", 0.0), ("out", 0.0),
)


# ---------------------------------------------------------------- analyzer

class Analyzer:
    """The full per-frame chain: spectrum in, N lanes out.

    `params` and `layout` default to the legacy six; a `params` list must
    match the layout's band count. `out` is the lanes array.
    """

    def __init__(self, analyser: Analyser, params: list[Params] | None = None,
                 layout: dict | None = None):
        self.an = analyser
        self.gain = 1.0
        self.dyn = 1.0
        self.trim = 0.0  # global input trim, dB
        self.spec: list[BandSpec] = []
        self.params: list[Params] = []
        self.st: list[dict] = []
        for name, _seed in _SEEDS:
            setattr(self, name, np.zeros(0))
        self._wlo: list[int] = []
        self._whi: list[int] = []
        self._w: list[np.ndarray] = []
        self._next = np.zeros(0, dtype=int)
        self.warm = 0
        self.layout_version = 0     # bumped whenever the band set changes shape
        self._hist_init()
        if layout is None:
            layout = legacy_layout()
            if params is None:
                params = default_params()
        self.apply_layout(layout, params=params)

    # ---- shape ----

    @property
    def n(self) -> int:
        return len(self.spec)

    @property
    def band_names(self) -> list[str]:
        return [s.label for s in self.spec]

    @property
    def lanes(self) -> np.ndarray:
        """The N band outputs in [0, CEIL) — valid after step()."""
        return self.out

    def edges(self, i: int) -> tuple[float, float]:
        """The derived readout: (lo, hi) Hz of band i."""
        return self.spec[i].edges()

    def layout(self) -> dict:
        """{"bands": [{"f", "q", "curve"(, "name")}, …]} — the preset's layout key."""
        rows = []
        for s in self.spec:
            row = {"f": s.f, "q": s.q, "curve": CURVES[s.curve].tag}
            if s.name:
                row["name"] = s.name
            rows.append(row)
        return {"bands": rows}

    def apply_layout(self, layout: dict, params: list[Params] | None = None) -> None:
        """Take the band set from a layout. Trackers of bands that keep their
        index carry on; new indices start fresh. Params are kept by index
        (a preset restores its values after the layout) unless given."""
        specs = [_spec_of(r) for r in layout["bands"]]
        if not 1 <= len(specs) <= N_MAX:
            raise ValueError(f"a layout has 1..{N_MAX} bands, not {len(specs)}")
        if params is not None and len(params) != len(specs):
            raise ValueError(f"{len(params)} params for {len(specs)} bands")
        old = self.n
        self._reshape([k if k < old else None for k in range(len(specs))])
        self.spec = specs
        if params is not None:
            self.params = list(params)
            self.st = [{} for _ in params]
        self._rebuild()

    def add_band(self, f: float | None = None, q: float = 1.0, curve=RECT,
                 name: str | None = None) -> int:
        """Insert a band in frequency order (into the widest gap when f is
        not given) and return its index."""
        if self.n >= N_MAX:
            raise ValueError(f"already {N_MAX} bands")
        if f is None:
            f = self._widest_gap()
        i = sum(1 for s in self.spec if s.f < f)
        idx = list(range(self.n))
        idx.insert(i, None)
        self._reshape(idx)
        self.spec.insert(i, BandSpec(float(f), float(q), curve_index(curve), name))
        self._rebuild()
        return i

    def remove_band(self, i: int) -> None:
        if self.n <= 1:
            raise ValueError("the last band stays")
        self._reshape([k for k in range(self.n) if k != i])
        del self.spec[i]
        self._rebuild()

    def move_band(self, i: int, j: int) -> None:
        """Move band i to index j — strip order, not frequency order."""
        idx = list(range(self.n))
        idx.insert(j, idx.pop(i))
        self._reshape(idx)
        self.spec = [self.spec[k] for k in idx]
        self._rebuild()

    def set_band(self, i: int, f: float | None = None, q: float | None = None,
                 curve=None, name=...) -> None:
        """Retune a band in place — trackers keep running."""
        s = self.spec[i]
        if f is not None:
            s.f = float(f)
        if q is not None:
            s.q = float(q)
        if curve is not None:
            s.curve = curve_index(curve)
        if name is not ...:
            s.name = name or None
        self._weigh(i)
        if f is not None:
            self._recouple()

    def _widest_gap(self) -> float:
        """Log midpoint of the widest gap between centres (and the range ends)."""
        fs = sorted([F_LO] + [s.f for s in self.spec] + [F_HI])
        k = int(np.argmax(np.diff(np.log2(fs))))
        return math.sqrt(fs[k] * fs[k + 1])

    def _reshape(self, idx: list[int | None]) -> None:
        """Re-lay every per-band array/list along idx: an int keeps that
        band's state, None seeds a fresh one."""
        for name, seed in _SEEDS:
            a = getattr(self, name)
            setattr(self, name, np.array([seed if k is None else a[k] for k in idx]))
        self.params = [default_band_params() if k is None else self.params[k] for k in idx]
        self.st = [{} if k is None else self.st[k] for k in idx]
        self.layout_version += 1

    def _rebuild(self) -> None:
        self._wlo, self._whi, self._w = [0] * self.n, [0] * self.n, [None] * self.n
        for i in range(self.n):
            self._weigh(i)
        self._recouple()

    def _recouple(self) -> None:
        # each band couples with the next one up in frequency; the top band
        # with itself (the reference's min(i + 1, 5))
        order = sorted(range(self.n), key=lambda i: (self.spec[i].f, i))
        nxt = np.zeros(self.n, dtype=int)
        for k, i in enumerate(order):
            nxt[i] = order[k + 1] if k + 1 < self.n else i
        self._next = nxt

    # ---- weighting ----

    def _weigh(self, i: int) -> None:
        """Band i's weights over its support [bin_lo, bin_hi], mean 1."""
        s = self.spec[i]
        lo, hi = s.edges()
        bins = self.an.bins
        if s.curve == RECT:
            # the reference's rounding, verbatim: floor the low edge, ceil the high
            blo, bhi = self.an.band_bins(lo, hi)
            blo = min(blo, bhi)
            w = np.ones(bhi - blo + 1)
        else:
            df = self.an.sample_rate / 2 / bins
            k = np.arange(1, bins)               # DC is never in a band
            w = CURVES[s.curve].f(np.log2(k * df / s.f), math.log2(hi / s.f))
            on = np.nonzero(w > W_EPS)[0]
            if len(on) == 0:                     # narrower than a bin: the nearest one
                blo = bhi = int(clamp(round(s.f / df), 1, bins - 1))
                w = np.ones(1)
            else:
                blo, bhi = int(on[0]) + 1, int(on[-1]) + 1
                w = w[on[0] : on[-1] + 1]
                w = w / w.mean()
        self._wlo[i], self._whi[i], self._w[i] = blo, bhi, w

    def weights(self, i: int) -> np.ndarray:
        """Band i's weight over every FFT bin (zero outside its support)."""
        w = np.zeros(self.an.bins)
        w[self._wlo[i] : self._whi[i] + 1] = self._w[i]
        return w

    def band_curve(self, i: int, freqs, f: float | None = None,
                   q: float | None = None) -> np.ndarray:
        """Band i's weighting rasterised on a frequency axis, peak 1 — for
        drawing over the spectrum history. `f` / `q` override the band's
        own (the editor draws the *base* while a lane modulates them)."""
        s = self.spec[i]
        fc = s.f if f is None else float(f)
        lo, hi = edges(fc, s.q if q is None else float(q))
        fx = np.maximum(np.asarray(freqs, dtype=float), 1e-9)
        if s.curve == RECT:       # compared in Hz so the edges themselves are inside
            return ((fx >= lo) & (fx <= hi)).astype(float)
        return np.asarray(CURVES[s.curve].f(np.log2(fx / fc), math.log2(hi / fc)), dtype=float)

    # ---- spectrum history ----

    def _hist_init(self) -> None:
        nyq = self.an.sample_rate / 2
        bins = self.an.bins
        df = nyq / bins
        self._hfreq = np.geomspace(HIST_LO, nyq, HIST_F)
        # each log bin reads the FFT bins from its lower edge (geometric
        # midpoint to its neighbour) up to the next one's; a log bin narrower
        # than an FFT bin reads the one bin it sits in (reduceat's rule for
        # equal consecutive indices)
        lower = np.concatenate([[HIST_LO], np.sqrt(self._hfreq[1:] * self._hfreq[:-1])])
        self._hstart = np.clip(np.rint(lower / df).astype(int), 1, bins - 1)
        self._hrow = np.zeros(HIST_F)
        self._hist = np.full((HIST_T, HIST_F), HIST_FLOOR, dtype=np.float32)
        self._hw = 0
        self._hacc = 0.0

    def _hist_push(self, freq: np.ndarray, dt: float) -> None:
        self._hacc += dt
        if self._hacc < HIST_DT:
            return
        np.maximum.reduceat(freq, self._hstart, out=self._hrow)
        np.maximum(self._hrow, HIST_FLOOR, out=self._hrow)     # -inf (silence) → floor
        pushes = 0
        while self._hacc >= HIST_DT and pushes < HIST_T:      # a long frame repeats its column
            self._hist[self._hw] = self._hrow
            self._hw = (self._hw + 1) % HIST_T
            self._hacc -= HIST_DT
            pushes += 1
        self._hacc = min(self._hacc, HIST_DT)

    def history(self) -> tuple[np.ndarray, np.ndarray]:
        """(spec[T, F] in dB, oldest column first; freqs[F] Hz log-spaced)."""
        return np.roll(self._hist, -self._hw, axis=0), self._hfreq

    # ---- scenes ----

    def apply_scene_band(self, i: int, row: dict | None) -> None:
        """One band's strip from a scene: `row` is that band's values with
        the ``band.{i}.`` prefix off ({"fn", "pre", …}); None, or a key the
        scene lacks, takes the default strip (default_band_params)."""
        P, d = self.params[i], default_band_params()
        row = row or {}
        for k in _SCENE_KEYS:
            v = row.get(k, getattr(d, k))
            setattr(P, k, int(v) if k in _INT_KEYS else v)
        self.st[i] = {}

    def apply_scene(self, values: dict) -> None:
        """A scene's values onto every band loaded — the ``band.{i}.*``
        entries of a band preset (library/band/*.json). Bands past the
        scene's rows take the default strip. The layout is not this
        method's: a strip load applies it first (Library.load); the scene
        combo re-tunes whatever bands are loaded."""
        rows = scene_rows(values)
        for i in range(self.n):
            self.apply_scene_band(i, rows.get(i))

    # ---- the frame ----

    def step(self, dt: float) -> np.ndarray:
        """One frame: read the analyser, run the chain, return the lanes."""
        freq = self.an.float_frequency_data()
        self._hist_push(freq, dt)
        dyn = self.dyn
        n = self.n

        k_pk = 1 - math.exp(-dt / PK_TAU)
        k_val = 1 - math.exp(-dt / VAL_TAU)
        k_slow = 1 - math.exp(-dt / SLOW_T)
        fpk_dec = math.exp(-dt / 2.5)

        self.warm += 1
        seeding = self.warm <= 3
        k_avg = 1 - math.exp(-dt / (0.25 if self.warm < 60 else MEAN_TAU))

        for i in range(n):
            P = self.params[i]

            # band RMS — the weighted mean of the power spectrum under the
            # band's curve, into u where 1.0 is nominal. RECT weights are
            # exactly 1.0, so this is the reference's mean over the slice.
            mags = 10.0 ** (freq[self._wlo[i] : self._whi[i] + 1] / 20.0)
            rms = math.sqrt(float(np.mean(self._w[i] * (mags * mags))))
            db = 20 * math.log10(rms + 1e-9)

            # input trim, applied pre-envelope AND (AUTO only) as tU offset
            # below — the double application is the reference's design, and
            # why a cut can drive harder there; MANUAL applies it once
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

            if P.norm:
                # MANUAL (audit A10): no adaptive window, no confidence, no
                # expansion, no warm-up. The level is the envelope itself in
                # u (1.0 = nominal), which already carries the trim once, as
                # a plain gain; the transient knob blends toward the
                # peak-normalised flux scaled by that level, so it too falls
                # with the trim. The trackers above still run, so switching
                # back to AUTO resumes where the window would have been.
                lvl = self.env[i]
                x = lvl + (trn * lvl - lvl) * P.trn
            else:
                x = lvl + (trn * conf - lvl) * P.trn + t_u
            if self.env[i] < P.thr:
                x = 0.0  # gate: band goes quiet, plane stops
            self.inp[i] = x if x > 0 else 0.0

        # harmonic coupling — last thing before the single input saturation.
        # Every band reads its neighbour's uncoupled value, whatever the
        # strip order, so the result is order-independent.
        raw = self.inp.copy()
        for i in range(n):
            up = min(raw[self._next[i]], 1)
            coh = math.sqrt(min(raw[i], 1) * up)
            self.inp[i] = soft_ceil(raw[i] * (1 + COUPLE * coh), KNEE, HEAD)

        # TRANSFER stage — pre-drive → shaper → post-drive → fader
        for i in range(n):
            P = self.params[i]
            x = soft_ceil(self.inp[i] * P.pre, KNEE, HEAD)
            y = SHAPERS[P.fn].f(self.st[i], x, dt)
            self.out[i] = soft_ceil(y * P.post, KNEE, CEIL)

        return self.out

