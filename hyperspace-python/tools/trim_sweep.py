"""Sweep one band's input trim on a clip and print the settled output.

    uv run python tools/trim_sweep.py [clip.wav] [--band 1] [--manual]

Audit A10 / ENGINEERING §4: on the AUTO path (the reference's adaptive
window) a cut of 6–12 dB can drive a band harder; on MANUAL the trim is a
plain gain and the output falls monotonically. The settled output is the
mean of the band's `out` over the clip's second half. Default clip is the
generated brickwalled fixture (tools/gen_test_audio.py makes it).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.bands import default_params
from hyperspace.offline import load_wav

FIXTURES = ROOT / "tests" / "fixtures"


def settled_out(samples, sr, band: int, trim: float, manual: bool, fps: float = 60.0) -> float:
    """Mean of `out[band]` over the clip's second half, trim in dB."""
    params = default_params()
    params[band].trim = trim
    params[band].norm = 1 if manual else 0
    an = Analyser(sr)
    chain = Analyzer(an, params)
    hop = round(sr / fps)
    dt = hop / sr
    outs = []
    for start in range(0, len(samples) - hop, hop):
        an.feed(samples[start: start + hop])
        chain.step(dt)
        outs.append(float(chain.out[band]))
    half = outs[len(outs) // 2:]
    return float(np.mean(half))


def sweep(path: Path, band: int, manual: bool, trims=range(0, -22, -2)) -> list[tuple[int, float]]:
    samples, sr = load_wav(path)
    return [(t, settled_out(samples, sr, band, float(t), manual)) for t in trims]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clip", nargs="?", default=str(FIXTURES / "brickwalled.wav"))
    ap.add_argument("--band", type=int, default=1)
    ap.add_argument("--manual", action="store_true")
    a = ap.parse_args()
    path = Path(a.clip)
    if not path.exists():
        subprocess.run([sys.executable, str(ROOT / "tools" / "gen_test_audio.py"),
                        "--out", str(FIXTURES)], check=True)
    mode = "MANUAL" if a.manual else "AUTO"
    print(f"{path.name}, band {a.band}, {mode}")
    for t, v in sweep(path, a.band, a.manual):
        print(f"  trim {t:+4d} dB → out {v:.3f}")


if __name__ == "__main__":
    main()
