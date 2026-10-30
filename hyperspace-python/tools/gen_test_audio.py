#!/usr/bin/env python3
"""Generate the deterministic test WAVs for golden-trace recording (plan 00).

The files are not committed — they regenerate bit-identically on any machine
(fixed sample rate, fixed seed, pure numpy math), and tests/golden/audio/
manifest.json records their sha256 so a mismatch is loud.

  uv run python tools/gen_test_audio.py [--out tests/fixtures]

Clips (all 48 kHz, 16-bit mono, 12 s):
  gate-prover.wav   50 Hz + 3 kHz steady mix — SUB/BASS and UPR move, the
                    other bands must sit at exactly zero (proves the gate).
  brickwalled.wav   music-like kick/bass/chords/hats, hard-limited to a
                    near-zero crest factor (exercises dynamics recovery).
  sweep.wav         20 Hz → 14 kHz log sweep, constant power (walks every
                    band boundary in sequence).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import wave
from pathlib import Path

import numpy as np

SR = 48_000
DUR = 12.0
N = int(SR * DUR)
T = np.arange(N) / SR


def write_wav(path: Path, x: np.ndarray) -> str:
    """Written beside `path` and renamed onto it, so a reader (another
    xdist worker generating the same files) never sees one half written."""
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767.0).astype("<i2")
    part = path.with_name(f".{path.stem}.{os.getpid()}.wav")
    with wave.open(str(part), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    os.replace(part, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate_prover() -> np.ndarray:
    return 0.5 * np.sin(2 * np.pi * 50.0 * T) + 0.25 * np.sin(2 * np.pi * 3000.0 * T)


def brickwalled() -> np.ndarray:
    rng = np.random.default_rng(0x4D)  # fixed seed — determinism is the point
    beat = 0.5  # 120 BPM
    x = np.zeros(N)

    # kick: 55 Hz decaying sine every beat, slight pitch drop
    for k in range(int(DUR / beat)):
        t0 = k * beat
        seg = (T >= t0) & (T < t0 + 0.35)
        tt = T[seg] - t0
        x[seg] += 0.9 * np.exp(-tt * 14) * np.sin(2 * np.pi * (55 - 18 * tt) * tt * 2)

    # bass line: 8th-note square-ish pulses alternating 82.4 / 110 Hz (E2/A2)
    for k in range(int(DUR / (beat / 2))):
        t0 = k * beat / 2
        f = 82.4 if (k // 4) % 2 == 0 else 110.0
        seg = (T >= t0) & (T < t0 + 0.20)
        tt = T[seg] - t0
        x[seg] += 0.4 * np.exp(-tt * 6) * np.tanh(3 * np.sin(2 * np.pi * f * tt))

    # chords: detuned saws around 220/330/440 Hz, slow swells
    for f in (220.0, 330.0, 440.0):
        for det in (0.996, 1.0, 1.005):
            ph = rng.uniform(0, 2 * np.pi)
            saw = 2 * ((T * f * det + ph / (2 * np.pi)) % 1.0) - 1.0
            x += 0.06 * saw * (0.6 + 0.4 * np.sin(2 * np.pi * T / 4 + ph))

    # hats: filtered noise bursts on the off-beats
    noise = rng.standard_normal(N)
    hp = noise - np.concatenate(([0.0], noise[:-1]))  # crude one-zero highpass
    for k in range(int(DUR / (beat / 2))):
        t0 = k * beat / 2 + beat / 4
        seg = (T >= t0) & (T < t0 + 0.06)
        x[seg] += 0.25 * np.exp(-(T[seg] - t0) * 60) * hp[seg]

    # brickwall: drive hard into tanh, then normalise to -0.3 dBFS
    x = np.tanh(x * 4.0)
    return x / np.max(np.abs(x)) * 0.966


def sweep() -> np.ndarray:
    f0, f1 = 20.0, 14_000.0
    k = np.log(f1 / f0)
    phase = 2 * np.pi * f0 * DUR / k * (np.exp(T / DUR * k) - 1.0)
    return 0.5 * np.sin(phase)


CLIPS = {
    "gate-prover.wav": gate_prover,
    "brickwalled.wav": brickwalled,
    "sweep.wav": sweep,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tests/fixtures", type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, fn in CLIPS.items():
        digest = write_wav(args.out / name, fn())
        print(f"{name}  sha256={digest}")


if __name__ == "__main__":
    main()
