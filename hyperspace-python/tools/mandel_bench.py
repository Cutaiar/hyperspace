#!/usr/bin/env python3
"""The Mandelbrot effect on the rig's GPU: milliseconds a pass, by
view, render size and iteration cap. Run it on the M3 Max; anywhere else
(Mesa's software rasteriser in a cloud session) the numbers mean nothing.

  uv run python tools/mandel_bench.py                    # the table, output 1920×1080
  uv run python tools/mandel_bench.py --out 3840x2160    # a 4K output
  uv run python tools/mandel_bench.py --frames 60 --caps 256,1024,4096,16384
  uv run python tools/mandel_bench.py --only whole,deep --json bench.json
  uv run python tools/mandel_bench.py --quick            # a smoke run: 2 views, 1 cap
  uv run python tools/mandel_bench.py --owner            # the rig cases at the seahorse

`--owner` runs the cases measured on the rig — the seahorse at Size 810,
Steps 2000: direct and perturbation at 1.5e4, perturbation at 4e5 and 1e7,
the skip on and off at 3e6, and the coloured inside at 1e6 and 9e6 (Steps
6000) — one line each with what the pass chose (the tier, whether the skip
ran), beside the rig ms recorded for it.

Each line is one view at one Size (540, 810, 1080 lines) and one Steps cap:
the pass (`FxChain.run_one`, what a graph Effect node runs) timed by the
renderer's own per-node GPU timer (`render.PassTimer`, a time query around
it, read back three frames late, median over the frames), the skip's two
pre-passes and the upscale inside it. `ref ms` is the CPU's float64
reference orbit for that view and cap — paid only on a frame a term changes
or the view leaves the reference (`mandel.Reference.stale`), so a hand on c
pays it every frame and a pan pays it rarely. Variants per view: the inside
black with the skip (the default), the skip off, and the inside coloured.

What to look at: a budget of ~8 ms at 120 fps (16 at 60) for this one node
beside everything else the frame draws; where 1080 crosses it; how much the
skip saves on the views with a lot of black (`whole`, `minibrot`); and
`ref ms` at the high caps (over a frame's budget means a hand on c stutters).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import moderngl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hyperspace import mandel as M
from hyperspace.fx import FxChain, FxState
from hyperspace.render import PassTimer

# name → the values over the defaults: the slice, the place, the depth
VIEWS = {
    "whole": {"centre_x": -0.5, "centre_y": 0.0, "zoom": 1.0},
    "seahorse": {"centre_x": -0.7436438870, "centre_y": 0.1318259042, "zoom": 2e3},
    "julia": {"slice": 1.0, "centre_x": 0.0, "centre_y": 0.0, "zoom": 1.0,
              "c_x": -0.8, "c_y": 0.156},
    "tilt": {"slice": 0.5, "centre_x": -0.4, "centre_y": 0.3, "zoom": 1.5},
    "power5": {"power": 5, "centre_x": 0.0, "centre_y": 0.0, "zoom": 1.2},
    "minibrot": {"centre_x": -1.7548776662, "centre_y": 0.0, "zoom": 3e4},   # perturb, a period-3 copy
    "deep": {"centre_x": -0.743643887037151, "centre_y": 0.131825904205330, "zoom": 1e10},
}
VARIANTS = {"black": {"interior": 0, "skip": 0},
            "no-skip": {"interior": 0, "skip": 1},
            "coloured": {"interior": 1, "skip": 0}}


DEFAULTS = dict(FxState().values["mandel"], on=True)

# the rig cases (Size 810, Steps 2000, at the seahorse):
# name, the values over the defaults, and the ms recorded on the rig
_SEA = {"centre_x": -0.743643887037151, "centre_y": 0.131825904205330,
        "size": 1, "iters": 2000.0}
OWNER = [
    ("direct 1.5e4", {**_SEA, "zoom": 1.5e4, "tier": 1}, 4.0),
    ("perturb 1.5e4", {**_SEA, "zoom": 1.5e4, "tier": 2}, 19.0),
    ("perturb 4e5", {**_SEA, "zoom": 4e5}, 38.0),
    ("perturb 1e7", {**_SEA, "zoom": 1e7}, 80.0),
    ("skip on 3e6", {**_SEA, "zoom": 3e6, "skip": 0}, 72.0),
    ("skip off 3e6", {**_SEA, "zoom": 3e6, "skip": 1}, 59.0),
    ("coloured 1e6", {**_SEA, "zoom": 1e6, "interior": 1, "iters": 6000.0}, None),
    ("coloured 9e6", {**_SEA, "zoom": 9e6, "interior": 1, "iters": 6000.0}, None),
]


def owner(ctx, chain, st, out, src, frames: int, rows: list) -> None:
    """The rig cases, one line each (`OWNER`)."""
    head = f"{'case':15} {'tier':>8} {'skip':>5} {'ms':>8} {'rig ms':>8}"
    print(head)
    print("-" * len(head))
    for name, view, was in OWNER:
        ms = bench(ctx, chain, st, out, src, view, frames)
        stats = chain.mandel.states["mandel"].stats if chain.mandel else {}
        tier = "perturb" if stats.get("perturb") else "direct"
        skip = "on" if stats.get("skip") else "off"
        rows.append({"case": name, "tier": tier, "skip": skip == "on", "ms": ms,
                     "rig_ms": was, "render": list(stats.get("size", ()))})
        ms_s = "n/a" if ms is None else f"{ms:8.2f}"
        was_s = "" if was is None else f"{was:8.0f}"
        print(f"{name:15} {tier:>8} {skip:>5} {ms_s:>8} {was_s:>8}", flush=True)


def bench(ctx, chain, st, out, src, view: dict, frames: int) -> float | None:
    """The median GPU ms of the pass over `frames` frames at `view` (over the
    defaults: nothing carries from the line before; the skip's
    gate starts again too, and settles over a few untimed passes, so a line
    is the steady state at its view)."""
    timer = PassTimer(ctx)
    if not timer.on:
        return None
    v = st.values["mandel"]
    v.clear()
    v.update(DEFAULTS)
    v.update(view)
    t = 0.0
    if chain.mandel is not None and "mandel" in chain.mandel.states:
        chain.mandel.states["mandel"].gate = M.SkipGate(free=chain.mandel.queries)
    for _ in range(M.SKIP_LAG + 2):
        chain.run_one("mandel", src, out, t, opaque=1)
        t += 1 / 60
    for _ in range(frames + PassTimer.LAG + 1):
        with timer.time("mandel"):
            chain.run_one("mandel", src, out, t, opaque=1)
        timer.end_frame(["mandel"])
        t += 1 / 60
    return timer.medians().get("mandel")


def ref_ms(view: dict, cap: int) -> float:
    """The CPU's reference orbit at this view and cap, ms (best of three)."""
    v = dict(FxState().values["mandel"])
    v.update(view)
    c, z0 = M.terms(complex(v["centre_x"], v["centre_y"]), v)
    best = float("inf")
    for _ in range(3):
        t0 = time.perf_counter()
        M.reference_orbit(c, z0, int(v["power"]), cap)
        best = min(best, (time.perf_counter() - t0) * 1e3)
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="1920x1080", help="the output's size, WxH")
    ap.add_argument("--frames", type=int, default=30, help="frames timed per line")
    ap.add_argument("--caps", default="256,1024,4096", help="Steps caps, comma separated")
    ap.add_argument("--only", default="", help="views, comma separated (default: all)")
    ap.add_argument("--variants", default=",".join(VARIANTS), help="variants, comma separated")
    ap.add_argument("--json", type=Path, help="also write the rows here")
    ap.add_argument("--quick", action="store_true", help="2 views, cap 256, black only")
    ap.add_argument("--owner", action="store_true",
                    help="the rig cases at the seahorse, Size 810, Steps 2000")
    a = ap.parse_args(argv)
    w, h = (int(x) for x in a.out.lower().split("x"))
    caps = [int(x) for x in a.caps.split(",") if x]
    views = a.only.split(",") if a.only else list(VIEWS)
    variants = a.variants.split(",")
    if a.quick:
        views, caps, variants, a.frames = ["whole", "minibrot"], [256], ["black"], 5

    ctx = moderngl.create_context(standalone=True)
    renderer = ctx.info.get("GL_RENDERER", "?")
    st = FxState()
    st.values["mandel"].update(on=True)
    chain = FxChain(ctx, st)
    src = ctx.texture((w, h), 4)
    out = ctx.framebuffer(color_attachments=[ctx.texture((w, h), 4, dtype="f2")])
    print(f"GPU: {renderer}   output {w}×{h}   {a.frames} frames a line, median GPU ms")
    if "Apple" not in renderer:
        print("(not the rig's GPU: these numbers say nothing about the show)")
    rows: list = []
    if a.owner:
        owner(ctx, chain, st, out, src, a.frames, rows)
        views = []
    head = f"{'view':10} {'variant':9} {'size':>5} {'steps':>6} {'tier':>8} {'ms':>8} {'ref ms':>7}"
    if views:
        print(head)
        print("-" * len(head))
    for name in views:
        for cap in caps:
            r_ms = ref_ms(VIEWS[name], cap) if M.perturbs({**DEFAULTS, **VIEWS[name]}) else None
            for var in variants:
                for size in range(len(M.SIZES)):
                    view = {**VIEWS[name], **VARIANTS[var], "iters": float(cap), "size": size}
                    ms = bench(ctx, chain, st, out, src, view, a.frames)
                    stats = chain.mandel.states["mandel"].stats if chain.mandel else {}
                    tier = "perturb" if stats.get("perturb") else "direct"
                    skip = "skip" if stats.get("skip") else ""
                    row = {"view": name, "variant": var, "lines": M.SIZES[size], "steps": cap,
                           "tier": tier, "skip": bool(skip), "ms": ms, "ref_ms": r_ms,
                           "render": list(stats.get("size", ()))}
                    rows.append(row)
                    ms_s = "n/a" if ms is None else f"{ms:8.2f}"
                    ref_s = "" if r_ms is None else f"{r_ms:7.2f}"
                    print(f"{name:10} {var:9} {M.SIZES[size]:>5} {cap:>6} {tier:>8} {ms_s:>8} "
                          f"{ref_s:>7}", flush=True)
    if a.json:
        a.json.write_text(json.dumps({"gpu": renderer, "output": [w, h], "frames": a.frames,
                                      "rows": rows}, indent=1))
    chain.release()
    src.release()
    out.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
