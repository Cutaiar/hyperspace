"""Write the recorded point-cloud fixture (plan 27 B4) the `cloud` device and
its tests play: a torus knot turning about its vertical axis, 16 frames at
12 fps, the point count different on every frame (so the file's ragged
offsets are exercised), coloured by height. Deterministic — no random
numbers, no clock — so the arrays come out the same on every run and every
machine (the .npz's zip timestamps differ; the arrays do not:
tests/test_clouds.py compares them).

    uv run python tools/cloud_fixture.py                # → tests/fixtures/clouds/knot.npz
    uv run python tools/cloud_fixture.py some/other.npz

tests/fixtures/ is gitignored at the repo root: commit the file with
``git add -f``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hyperspace.devices import write_clouds

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "clouds" / "knot.npz"
FRAMES = 16
RATE = 12.0
BASE_N = 96          # points on frame 0; frame i has BASE_N + 8 i


def knot(i: int) -> tuple[np.ndarray, np.ndarray]:
    """Frame `i`: the (2, 3) torus knot, its points evenly along it, turned
    by i / FRAMES of a revolution; RGB from height (blue low, warm high)."""
    n = BASE_N + 8 * i
    s = np.arange(n, dtype=np.float64) * (2 * np.pi / n)
    r = 2.0 + np.cos(3 * s)
    x, y, z = r * np.cos(2 * s), np.sin(3 * s), r * np.sin(2 * s)
    a = 2 * np.pi * i / FRAMES
    pts = np.stack([x * np.cos(a) - z * np.sin(a), y, x * np.sin(a) + z * np.cos(a)], axis=1)
    h = (y + 1.0) / 2.0
    rgb = np.stack([h, 0.4 + 0.2 * h, 1.0 - h], axis=1)
    return pts.astype(np.float32), rgb.astype(np.float32)


def frames() -> tuple[list[np.ndarray], list[np.ndarray]]:
    pts, cols = zip(*(knot(i) for i in range(FRAMES)), strict=True)
    return list(pts), list(cols)


def main(argv: list[str]) -> int:
    out = Path(argv[0]) if argv else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    pts, cols = frames()
    write_clouds(out, pts, RATE, cols)
    print(f"{out}: {FRAMES} frames at {RATE:g} fps, {sum(len(p) for p in pts)} points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
