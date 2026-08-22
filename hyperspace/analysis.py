"""Web-Audio-equivalent spectrum front end.

Replicates AnalyserNode semantics so the constants ported into bands.py
keep their meaning: fftSize 4096, Blackman window, FFT normalised by 1/N,
per-call magnitude smoothing s = τ·prev + (1−τ)·|X| applied in linear
magnitude, then dB conversion — per the Web Audio spec's
getFloatFrequencyData definition.
"""

from __future__ import annotations

import numpy as np

FFT_SIZE = 4096
SMOOTHING = 0.15


def _blackman(n: int) -> np.ndarray:
    # The spec's Blackman: a0=0.42, a1=0.5, a2=0.08 (alpha = 0.16).
    k = np.arange(n)
    return 0.42 - 0.5 * np.cos(2 * np.pi * k / n) + 0.08 * np.cos(4 * np.pi * k / n)


class Analyser:
    """Feed it samples; read the smoothed dB spectrum like an AnalyserNode."""

    def __init__(self, sample_rate: float = 48_000.0):
        self.sample_rate = sample_rate
        self.bins = FFT_SIZE // 2
        self._window = _blackman(FFT_SIZE)
        self._buf = np.zeros(FFT_SIZE)
        self._smooth = np.zeros(self.bins)

    def feed(self, samples: np.ndarray) -> None:
        """Append mono samples; keeps the most recent fftSize of them."""
        n = len(samples)
        if n >= FFT_SIZE:
            self._buf = samples[-FFT_SIZE:].astype(np.float64)
        else:
            self._buf = np.concatenate([self._buf[n:], samples.astype(np.float64)])

    def float_frequency_data(self) -> np.ndarray:
        """Smoothed spectrum in dB, length fftSize/2 (like getFloatFrequencyData)."""
        spec = np.abs(np.fft.rfft(self._buf * self._window))[: self.bins] / FFT_SIZE
        self._smooth = SMOOTHING * self._smooth + (1 - SMOOTHING) * spec
        with np.errstate(divide="ignore"):
            return 20.0 * np.log10(self._smooth)

    def band_bins(self, lo_hz: float, hi_hz: float) -> tuple[int, int]:
        """Band edges → bin indices, with the reference's exact rounding."""
        nyq = self.sample_rate / 2
        lo = max(1, int(np.floor(lo_hz / nyq * self.bins)))
        hi = min(self.bins - 1, max(2, int(np.ceil(hi_hz / nyq * self.bins))))
        return lo, hi
