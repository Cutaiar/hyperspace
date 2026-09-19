"""Offline driver: run a WAV through the chain at a fixed frame cadence.

Used by the plan-01 behaviour tests and by future constant-tuning work
(plan 06). Live capture replaces the file reader in plan 03; the chain
itself neither knows nor cares.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from .analysis import Analyser
from .bands import Chain, Params
from .routing import legacy_planedrive


def load_wav(path: Path) -> tuple[np.ndarray, float]:
    """Mono float64 samples in [-1, 1] and the sample rate."""
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        if w.getnchannels() > 1:
            raw = raw.reshape(-1, w.getnchannels()).mean(axis=1)
    return raw.astype(np.float64) / 32768.0, float(sr)


def run_wav(
    path: Path,
    fps: float = 60.0,
    dyn: float = 1.0,
    params: list[Params] | None = None,
) -> dict[str, np.ndarray]:
    """Feed the file frame by frame; return the per-frame chain history."""
    samples, sr = load_wav(path)
    an = Analyser(sr)
    chain = Chain(an, params)
    chain.dyn = dyn
    hop = round(sr / fps)
    dt = hop / sr
    t, inp, out, drive = [], [], [], []
    for start in range(0, len(samples) - hop, hop):
        an.feed(samples[start : start + hop])
        chain.step(dt)
        t.append(start / sr)
        inp.append(chain.inp.copy())
        out.append(chain.out.copy())
        drive.append(legacy_planedrive(chain.out, chain.gain))   # the reference's PLANEDRIVE
    return {
        "t": np.asarray(t),
        "inp": np.asarray(inp),
        "out": np.asarray(out),
        "drive": np.asarray(drive),
    }
