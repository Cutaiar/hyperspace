#!/usr/bin/env python3
"""What each face pattern costs (plan 22 B3), as a relative number.

The 600-cell (1200 triangular faces) and the 120-cell (720 pentagons) with
their faces on, drawn offscreen at 1280×720 with each pattern in turn,
the bands of a loud passage fed (METER and PULSE read them): the median
of `--frames` frames, `ctx.finish()` after each, beside FLAT (no pattern
runs). On this machine's GL — llvmpipe in the container, a software
rasteriser — so read the ratios, not the milliseconds: a GPU spends far
less on fragments. Writes docs/plans/assets/22-face-patterns/b3-cost.txt.

    uv run python tools/pattern_cost.py [--frames 20]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import moderngl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.geometry import SHAPES
from hyperspace.graph import Wiring
from hyperspace.graphmigrate import wired_wiring
from hyperspace.patterns import MODES
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "22-face-patterns" / "b3-cost.txt"
SIZE = (1280, 720)
LOUD = (0.85, 0.90, 0.30, 0.35, 0.45, 0.80)
SHAPE_NAMES = ("600-cell", "120-cell")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--frames", type=int, default=20)
    args = ap.parse_args()
    ctx = moderngl.create_context(standalone=True)
    r = Renderer(ctx)
    # plan 36 T3: a bare renderer draws the app's empty frame; the
    # tool's own wiring is today's frame (render.render_offscreen's)
    r.wiring = wired_wiring(Wiring())
    r.bands = LOUD
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer(SIZE)])
    shapes = [next(i for i, s in enumerate(SHAPES) if s.name == n) for n in SHAPE_NAMES]
    rows = []
    for mode, m in enumerate(MODES):
        ms = []
        for shape in shapes:
            s = ViewState(shape=shape, faces=True, pattern=mode, pattern_mix=1.0,
                          ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3])
            times = []
            for k in range(args.frames + 3):
                fbo.use()
                ctx.viewport = (0, 0, *SIZE)
                t0 = time.perf_counter()
                r.draw(s, *SIZE, t_now=2.0 + k / 60)
                ctx.finish()
                if k >= 3:                       # the first frames build caches
                    times.append(time.perf_counter() - t0)
            ms.append(statistics.median(times) * 1000)
        rows.append((mode, m.name, ms))
    flat = rows[0][2]
    head = f"{'mode':<4} {'name':<8} " + "  ".join(f"{n:>17}" for n in SHAPE_NAMES)
    lines = ["Face pattern cost, offscreen 1280x720, median ms per frame and x FLAT",
             "(llvmpipe: relative numbers only; tools/pattern_cost.py)", "", head]
    for mode, name, ms in rows:
        cells = "  ".join(f"{v:7.1f} ms {v / f:5.2f}x" for v, f in zip(ms, flat, strict=True))
        lines.append(f"{mode:<4} {name:<8} {cells}")
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
