#!/usr/bin/env python3
"""The dream worker live in the real pipeline, offscreen (WP6b).

Renders a rotating 24-cell at 1280×820 through Renderer + Lookback with
the DreamWorker on the slot, paced at 60 fps like a vsynced window, the
worker free-running (latest wins), and writes the composite at the last
frame to docs/plans/assets/06-lookback/dream-live.png. Then reports the
worker's ms per submit (p50 / p99) and the renderer's own frame time with
the worker running against the same loop without one — the contention
number of spike C on the real pipeline.

    uv run python tools/dream_shots.py [--frames 90] [--layer conv3_3]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.lookback import LAYERS, DreamState
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "06-lookback" / "dream-live.png"
W, H = 1280, 820


def registry(dream):
    from types import SimpleNamespace

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import build_registry

    chain = Analyzer(Analyser())
    return build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain), None,
                          dream=dream)


def scene(ctx, dream):
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    r = Renderer(ctx, dream)
    s = ViewState(shape=10, faces=True, pattern=2, bright=1.3, speed=3.0)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    s.yaw, s.pitch = 0.4, 0.25
    return fbo, r, s


def frame(ctx, fbo, r, s, t):
    s.integrate(1 / 60)
    fbo.use()
    ctx.viewport = (0, 0, W, H)
    r.draw(s, W, H, t_now=t)


def pct(xs, q):
    return sorted(xs)[min(len(xs) - 1, int(q * len(xs)))]


def run(ctx, dream, worker, frames, fps=60.0):
    """The paced loop; returns (frame times ms, last composite)."""
    fbo, r, s = scene(ctx, dream)
    r.lookback.source = worker
    times = []
    tick = 1.0 / fps
    next_tick = time.perf_counter()
    for k in range(frames):
        t0 = time.perf_counter()
        frame(ctx, fbo, r, s, k / 60)
        ctx.finish()
        times.append((time.perf_counter() - t0) * 1e3)
        next_tick += tick
        rem = next_tick - time.perf_counter()
        if rem > 0:
            time.sleep(rem)
        else:
            next_tick = time.perf_counter()
    px = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1].copy()
    fbo.release()
    return times, px


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=90)
    ap.add_argument("--layer", default="conv3_3", choices=LAYERS)
    ap.add_argument("--precision", default="fp32", choices=("fp32", "fp16"))
    args = ap.parse_args()
    from hyperspace.dream import DreamWorker

    ctx = moderngl.create_context(standalone=True)
    # the spike's defaults (DreamState), the dream buffer alone over the scene
    dream = DreamState(on=True, echoes=0, every=1, layer=LAYERS.index(args.layer))
    reg = registry(dream)
    worker = DreamWorker(reg, {"enabled": True, "precision": args.precision})
    # warm: the trunk loads on the first submit; keep the loop from timing that
    fbo, r, s = scene(ctx, dream)
    r.lookback.source = worker
    frame(ctx, fbo, r, s, 0.0)
    worker.drain(120.0)
    fbo.release()
    worker._times.clear()
    with_times, px = run(ctx, dream, worker, args.frames)
    st = worker.stats()
    steps = [ms for _, ms in list(worker._times)]
    print(f"worker: {worker.status()}")
    worker.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(px).quantize(256, method=Image.Quantize.MEDIANCUT,
                                 dither=Image.Dither.FLOYDSTEINBERG).save(OUT, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB)")

    none_times, _ = run(ctx, DreamState(on=True, echoes=0, every=1), None, args.frames)
    print(f"\n{args.layer} {args.precision} at {r.lookback.echo[0]}x{r.lookback.echo[1]}, "
          f"{args.frames} frames paced at 60 fps, renderer at {W}x{H} (ms)")
    print("| what | p50 | p99 | max | n |")
    print("|---|---|---|---|---|")
    print(f"| dream step (per submit) | {pct(steps, 0.5):.2f} | {pct(steps, 0.99):.2f} | "
          f"{max(steps):.2f} | {len(steps)} |")
    print(f"| renderer frame, worker on | {pct(with_times, 0.5):.2f} | "
          f"{pct(with_times, 0.99):.2f} | {max(with_times):.2f} | {len(with_times)} |")
    print(f"| renderer frame, no worker | {pct(none_times, 0.5):.2f} | "
          f"{pct(none_times, 0.99):.2f} | {max(none_times):.2f} | {len(none_times)} |")
    print(f"\ndrops {st['drops']} · behind at the end {st['behind']} · "
          f"nan resets {st['nan_resets']} · copy path {st['path']} on {st['device']}")


if __name__ == "__main__":
    main()
