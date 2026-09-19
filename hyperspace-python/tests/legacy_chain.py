"""The six-band `Chain` exactly as it was before plan 07 WP4a (commit 628ae7e).

Frozen here as the parity reference: the analyzer with the "Legacy 6"
layout must reproduce this frame for frame, bit for bit
(test_analyzer.py::test_legacy_layout_is_bit_exact). Do not edit — if the
chain math changes on purpose, change it in analyzer.py and re-freeze.
"""

from __future__ import annotations

import math

import numpy as np

from hyperspace.bands import (
    BANDS,
    CEIL,
    CONF_LO,
    CONF_SPAN,
    COUPLE,
    DEV_AIM,
    DEV_MIN,
    DRIVE,
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
    default_params,
    soft_ceil,
)


class LegacyChain:
    """The full per-frame chain: spectrum in, PLANEDRIVE out."""

    def __init__(self, analyser, params: list[Params] | None = None):
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
