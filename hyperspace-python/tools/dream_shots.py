#!/usr/bin/env python3
"""The dream worker live in the real pipeline, offscreen (the dream
is an effect file, its worker on `renderer.fx.dream_source`).

A party loadable patch (default party-wake, whose dream opens as its folded
chain: Resize → Dream → … → Fade → Composite over) through the real loader
and hand chain (tools/loadable_shots.Stage), the DreamWorker on the dream,
paced at 60 fps like a vsynced window, the worker free-running (submit when
it is free). Writes one frame per pose to
docs/plans/assets/12-presets/<slug>-dream/ and a sheet beside them, then the
worker's ms per job (p50 / p99) and the renderer's own frame time with the
worker running against the same loop without one — spike C's contention
number on the real pipeline. A hand check on the Mac (torch, MPS).

    uv run python tools/dream_shots.py [--preset party-wake] [--frames 90] [--precision fp16]
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
sys.path.insert(0, str(ROOT / "tools"))

WAKE_POSES = [("no hands", {}), ("L up (speed)", {"L.y": 1}),
              ("R up + reach in (long)", {"R.y": 1, "R.z": 0}),
              ("R roll thumb-up (hue)", {"R.roll": 1}),
              ("R pitch fingers-up (dream)", {"R.pitch": 1}),
              ("R pitch fingers-down", {"R.pitch": 0})]


def pct(xs, q):
    return sorted(xs)[min(len(xs) - 1, int(q * len(xs)))]


def paced(ctx, st, fbo, hands, frames) -> list[float]:
    """`frames` frames of `st` at 60 fps; the renderer's own ms a frame."""
    times = []
    next_tick = time.perf_counter()
    for _ in range(frames):
        t0 = time.perf_counter()
        st.frame(hands, fbo)
        ctx.finish()
        times.append((time.perf_counter() - t0) * 1e3)
        next_tick += 1 / 60
        rem = next_tick - time.perf_counter()
        if rem > 0:
            time.sleep(rem)
        else:
            next_tick = time.perf_counter()
    return times


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="party-wake")
    ap.add_argument("--frames", type=int, default=90)
    ap.add_argument("--precision", default="fp32", choices=("fp32", "fp16"))
    args = ap.parse_args()
    import loadable_shots as ps

    from hyperspace.dream import DreamWorker

    ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((ps.W, ps.H))])
    out = ps.OUT / f"{args.preset}-dream"
    out.mkdir(parents=True, exist_ok=True)
    tiles, steps, with_times = [], [], []
    for label, pose in WAKE_POSES:
        st = ps.Stage(args.preset, ctx)
        worker = DreamWorker({"enabled": True, "precision": args.precision})
        st.renderer.fx.dream_source = worker
        st.frame({}, fbo)
        worker.drain(120.0)                       # the trunk loads on the first job
        worker._times.clear()
        with_times += paced(ctx, st, fbo, ps.pose_hands(pose), args.frames)
        steps += [ms for _, ms in list(worker._times)]
        img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(ps.H, ps.W, 3)[::-1]
        p = out / (label.replace(" ", "-").replace("(", "").replace(")", "").lower() + ".png")
        Image.fromarray(img.copy()).quantize(256, method=Image.Quantize.MEDIANCUT,
                                              dither=Image.Dither.FLOYDSTEINBERG).save(
            p, optimize=True)
        tiles.append((label, p))
        print(f"{label}: {worker.status()}")
        worker.close()
        st.release()
    ps.sheet(tiles, ps.OUT / f"{args.preset}-dream-sheet.png", cols=3)
    print("wrote", (ps.OUT / f"{args.preset}-dream-sheet.png").relative_to(ROOT))
    st = ps.Stage(args.preset, ctx)
    none_times = paced(ctx, st, fbo, {}, args.frames)
    st.release()
    fbo.release()
    print(f"\n{args.preset} {args.precision}, {args.frames} frames a pose paced at 60 fps, "
          f"renderer at {ps.W}x{ps.H} (ms)")
    print("| what | p50 | p99 | max | n |")
    print("|---|---|---|---|---|")
    for what, xs in (("dream job", steps), ("renderer frame, worker on", with_times),
                     ("renderer frame, no worker", none_times)):
        if xs:
            print(f"| {what} | {pct(xs, 0.5):.2f} | {pct(xs, 0.99):.2f} | {max(xs):.2f} | "
                  f"{len(xs)} |")


if __name__ == "__main__":
    main()
