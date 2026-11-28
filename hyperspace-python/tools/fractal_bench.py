"""The rig bench: a fractal's frame on the CPU path (sorted) against
the GPU path (additive), for every fractal, a few depths into it, the faces
off and on.

Per case, the median over `--frames` frames of:

- `walk`: wall ms of `fractal.walk` (the cull and the split; both paths);
- `build`: wall ms of what each path makes of the walk on the CPU — the
  frame's geometry (`fractal.geometry_of`) sorted, the instance rows
  (`fractal.instances`) additive;
- `draw`: wall ms of the whole `Renderer.draw_scene` (walk, build, the
  painter sort and the vertex packing, the GL calls), with the GPU waited
  on (`ctx.finish`) so the wall time is the frame's;
- `gpu`: GPU ms of the same draw, from a timer query (`ctx.query(time=True)`,
  as the renderer's `PassTimer` times a node); blank where the context has
  no timer queries;
- `cells` and `edges`: how much the frame drew.

Mesa's software rasteriser (a cloud session) says nothing about the rig:
run it on the Mac.

    uv run python tools/fractal_bench.py                      # 1920×1080, every fractal
    uv run python tools/fractal_bench.py --frames 60 --json bench.json
    uv run python tools/fractal_bench.py --only "Menger sponge" --levels 0 6
"""

from __future__ import annotations

import argparse
import json
import statistics
import time

import moderngl
import numpy as np

from hyperspace import fractal
from hyperspace.geometry import shape_index
from hyperspace.render import Renderer
from hyperspace.view import ViewState


def dive(name: str, levels: int, faces: bool, additive: bool) -> ViewState:
    """A view `levels` re-roots into fractal `name` (0: the whole shape)."""
    s = ViewState(shape=shape_index(name), yaw=0.45, pitch=0.3, faces=faces, lines=True,
                  points=True)
    s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
    s.frac_additive = additive
    s.zoom = 1.3
    for _ in range(4000):
        if len(s.dive.path) >= levels:
            break
        s.zoom *= 1.05
        fractal.step(s)
    return s


def bench(ctx, r: Renderer, fbo, s: ViewState, w: int, h: int, frames: int) -> dict:
    spec = fractal.spec_of(s.shape)
    query = None
    try:
        query = ctx.query(time=True)
    except Exception:  # noqa: BLE001 — no timer queries: wall time only
        query = None
    walk_ms, build_ms, draw_ms, gpu_ms = [], [], [], []
    wk = None
    for k in range(frames + 3):           # three to warm up: compile, upload
        s.yaw = 0.45 + 0.002 * k          # a turn a frame, as a live view has
        t0 = time.perf_counter()
        wk = fractal.walk(spec, s, w, h)
        t1 = time.perf_counter()
        if s.frac_additive:
            fractal.instances(wk)
        else:
            fractal.geometry_of(wk)
        t2 = time.perf_counter()
        fbo.use()
        ctx.viewport = (0, 0, w, h)
        ctx.finish()
        t3 = time.perf_counter()
        if query is not None:
            with query:
                r.draw_scene(s, w, h, t_now=0.0)
        else:
            r.draw_scene(s, w, h, t_now=0.0)
        ctx.finish()
        t4 = time.perf_counter()
        if k < 3:
            continue
        walk_ms.append((t1 - t0) * 1e3)
        build_ms.append((t2 - t1) * 1e3)
        draw_ms.append((t4 - t3) * 1e3)
        if query is not None:
            gpu_ms.append(query.elapsed / 1e6)
    assert wk is not None
    cells = len(wk.line_s) + len(wk.face_s) + int(wk.whole)
    edges = len(wk.line_s) * len(spec.new_E) + (len(spec.E) if wk.whole else 0)
    med = statistics.median
    return {"walk": med(walk_ms), "build": med(build_ms), "draw": med(draw_ms),
            "gpu": med(gpu_ms) if gpu_ms else None, "cells": cells, "edges": edges,
            "depth": len(s.dive.path)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--size", type=int, nargs=2, default=(1920, 1080), metavar=("W", "H"))
    ap.add_argument("--samples", type=int, default=0, help="MSAA samples of the target")
    ap.add_argument("--frames", type=int, default=30)
    ap.add_argument("--levels", type=int, nargs="+", default=(0, 3, 8, 16))
    ap.add_argument("--only", nargs="+", default=None, help="fractal names")
    ap.add_argument("--json", default=None, help="write the rows here too")
    a = ap.parse_args()
    w, h = a.size
    ctx = moderngl.create_context(standalone=True)
    tex = ctx.renderbuffer((w, h), 4, samples=a.samples)
    dep = ctx.depth_renderbuffer((w, h), samples=a.samples)
    fbo = ctx.framebuffer(color_attachments=[tex], depth_attachment=dep)
    r = Renderer(ctx)
    print(f"{ctx.info['GL_RENDERER']} · {w}×{h} · {a.frames} frames a case, medians in ms")
    head = (f"{'fractal':24} {'lv':>3} {'faces':>5} {'mode':>8} {'cells':>6} {'edges':>6}"
            f" {'walk':>7} {'build':>7} {'draw':>7} {'gpu':>7}")
    print(head)
    print("-" * len(head))
    rows = []
    for name in a.only or fractal.FRACTALS:
        for levels in a.levels:
            for faces in (False, True):
                for additive in (False, True):
                    s = dive(name, levels, faces, additive)
                    b = bench(ctx, r, fbo, s, w, h, a.frames)
                    row = {"fractal": name, "levels": levels, "faces": faces,
                           "mode": "additive" if additive else "sorted", **b}
                    rows.append(row)
                    gpu = f"{b['gpu']:7.2f}" if b["gpu"] is not None else f"{'-':>7}"
                    print(f"{name:24} {b['depth']:3d} {'on' if faces else 'off':>5}"
                          f" {row['mode']:>8} {b['cells']:6d} {b['edges']:6d}"
                          f" {b['walk']:7.2f} {b['build']:7.2f} {b['draw']:7.2f} {gpu}",
                          flush=True)
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"renderer": ctx.info["GL_RENDERER"], "size": [w, h],
                       "frames": a.frames, "rows": rows}, f, indent=1)
    # the totals: each path's mean frame over every case
    for mode in ("sorted", "additive"):
        d = [x["draw"] for x in rows if x["mode"] == mode]
        print(f"{mode:>8}: draw mean {np.mean(d):.2f} ms, worst {max(d):.2f} ms")


if __name__ == "__main__":
    main()
