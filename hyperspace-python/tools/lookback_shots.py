#!/usr/bin/env python3
"""The plain tracer, offscreen (WP6a), and what the post pass costs.

Renders a rotating 24-cell at 1280×820 through the real pipeline with the
look-back on and no dream worker — the echoes alone — and writes the last
frame to docs/plans/assets/06-lookback/tracer-core.png. Then times the
post pass (composite + capture, render drained) at 0, 8 and 32 echoes.

    uv run python tools/lookback_shots.py [--frames 90]
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

from hyperspace.graph import Wiring
from hyperspace.graphmigrate import look_of, wired_wiring
from hyperspace.lookback import DreamState, fade_of_decay
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "06-lookback" / "tracer-core.png"
W, H = 1280, 820


def scene(ctx, dream):
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    r = Renderer(ctx, dream)
    # plan 36 T3: a bare renderer draws the app's empty frame; the
    # tool's own wiring is today's frame, its look-back as `dream` has it
    # (plan 36 T4: drawn while on, with the dream while its mix is above 0)
    r.wiring = wired_wiring(Wiring(), look_of({"dream.on": dream.on, "dream.mix": dream.mix}))
    s = ViewState(shape=10, faces=True, pattern=2, bright=1.3, speed=3.0)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    s.yaw, s.pitch = 0.4, 0.25
    return fbo, r, s


def frame(ctx, fbo, r, s, t):
    s.integrate(1 / 60)
    fbo.use()
    ctx.viewport = (0, 0, W, H)
    r.draw(s, W, H, t_now=t)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=90)
    args = ap.parse_args()
    ctx = moderngl.create_context(standalone=True)

    # the shot: the tracer-only preset's look, a little heavier so it reads in a still
    dream = DreamState(on=True, echoes=8, gap=3 / 60, fade=fade_of_decay(0.94), echo_mix=0.7,
                       darken=0.2,
                       contrast=1.2, res=2)
    fbo, r, s = scene(ctx, dream)
    for k in range(args.frames):
        frame(ctx, fbo, r, s, k / 60)
    px = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # palette-quantised like the spike's gallery, to keep the asset small
    Image.fromarray(px).quantize(256, method=Image.Quantize.MEDIANCUT,
                                 dither=Image.Dither.FLOYDSTEINBERG).save(OUT, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB)")
    fbo.release()

    # the cost: scene pass alone vs the whole draw, per echo count
    print(f"\npost pass at {W}x{H}, echoes at {r.lookback.echo[0]}x{r.lookback.echo[1]}"
          " (ms, p50 / p99 over 120 frames, ctx.finish per frame)")
    rows = []
    for echoes in (0, 8, 32):
        dream = DreamState(on=echoes > 0, echoes=echoes, gap=0.0, res=2)
        fbo, r, s = scene(ctx, dream)
        for k in range(40):                     # fill the ring, warm the caches
            frame(ctx, fbo, r, s, k / 60)
        ctx.finish()
        full, only = [], []
        for k in range(120):
            t0 = time.perf_counter()
            frame(ctx, fbo, r, s, k / 60)
            ctx.finish()
            full.append(time.perf_counter() - t0)
            t0 = time.perf_counter()
            s.integrate(1 / 60)
            r.scene.draw_fbo.use()
            ctx.viewport = (0, 0, W, H)
            r.draw_scene(s, W, H, t_now=k / 60)
            ctx.finish()
            only.append(time.perf_counter() - t0)
        p = lambda xs, q: sorted(xs)[min(len(xs) - 1, int(q * len(xs)))] * 1e3
        post50 = p(full, 0.5) - p(only, 0.5)
        rows.append((echoes, p(full, 0.5), p(full, 0.99), p(only, 0.5), post50))
        fbo.release()
    print("| echoes | frame p50 | frame p99 | scene pass p50 | post pass p50 |")
    print("|---|---|---|---|---|")
    for e, f50, f99, o50, post in rows:
        print(f"| {e} | {f50:.2f} | {f99:.2f} | {o50:.2f} | {post:.2f} |")


if __name__ == "__main__":
    main()
