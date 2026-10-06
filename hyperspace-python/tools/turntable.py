#!/usr/bin/env python3
"""The turntable: does a shape keep its volume through each W plane?

For every shape and each of the three W planes (XW, YW, ZW) on its own,
sweep the plane through a full turn and measure the projected 3D cloud's
volume ratio — smallest singular value over largest
(geometry.volume_ratio, the same function the tests gate on) — and the
share of face area the projection turns edge-on
(geometry.edge_on_share, the tests' second gate, at most 0.15). A shape in
the w = 0 hyperplane falls to ~0 at 90° and 270°: the turn has carried a
whole axis into w and the 4D→3D divide drops it. Two passes per plane:
the other five planes at 0 ("axis"), and at a fixed generic pose
("generic").

The sweep goes through geometry.view_angles, as the renderer does, so a
shape whose W planes are masked (Shape.w == "mask") turns in the 3D
plane each W plane is remapped onto instead.

Writes, under docs/plans/assets/22-flat-shapes/ (plan 22, Stream A):

  <prefix>-ratios.json / .csv   min ratio per shape per plane per pass,
                                and the angle where it occurs; the max
                                edge-on share and its angle
  <prefix>-NN-<name>.png        one sheet per shape: a row per W plane,
                                --frames tiles across 360°, drawn by the
                                real renderer offscreen, each tile labelled
                                with its angle and ratio

An offscreen render, not the rig: it shows the geometry, not what a
projector shows.

    uv run python tools/turntable.py --prefix before
    uv run python tools/turntable.py --prefix after --shapes 18-24 --no-png
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace import geometry as G
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "22-flat-shapes"
W_PLANES = ("XW", "YW", "ZW")
TILE = 132           # px, square
LABEL = 14           # px under each tile for its angle / ratio
HEAD = 18            # px for the sheet's title
ROW_LABEL = 34       # px left of each row for the plane name
YAW, PITCH = 0.5, 0.35   # a camera a little off-axis, so depth reads
ZOOM = 1.45              # the shape fills its tile


def slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def parse_shapes(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.extend(range(int(a), int(b or a) + 1))
    return [i for i in out if 0 <= i < len(G.SHAPES)]


def measure(i: int, steps: int) -> dict:
    """{pass: {plane: {"min": r, "at": degrees, "edge_on": share,
    "edge_on_at": degrees}}} for one shape: the volume ratio's minimum and
    the edge-on face share's maximum round the turn."""
    res: dict = {}
    for pname, pose in (("axis", None), ("generic", G.GENERIC_POSE)):
        res[pname] = {}
        for plane in W_PLANES:
            r = G.sweep_ratios(i, plane, steps=steps, pose=pose)
            e = G.sweep_edge_on(i, plane, steps=steps, pose=pose)
            k, j = int(np.argmin(r)), int(np.argmax(e))
            res[pname][plane] = {"min": float(r[k]), "at": 360.0 * k / steps,
                                 "edge_on": float(e[j]), "edge_on_at": 360.0 * j / steps}
    return res


def sheet(ctx, renderer, i: int, frames: int) -> Image.Image:
    """A row per W plane, `frames` tiles across a turn, axis pose."""


    shape = G.SHAPES[i]
    big = TILE * 2           # render at 2×, downsample: smoother lines
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((big, big), 4)])
    img = Image.new("RGB", (ROW_LABEL + frames * TILE, HEAD + 3 * (TILE + LABEL)), "black")
    d = ImageDraw.Draw(img)
    # PIL's built-in font is ASCII: Möbius is drawn as Mobius
    name = unicodedata.normalize("NFKD", shape.name).encode("ascii", "ignore").decode()
    title = f"{i:02d} {name}  -  w: {shape.w}"
    if shape.w == "mask":
        title += "  (W planes remapped: " + ", ".join(
            f"{G.PLANE_NAMES[p]}->{G.PLANE_NAMES[q]}" for p, q in G.W_REMAP.items()) + ")"
    d.text((4, 3), title, fill="white")
    V = G.geom(i)["V"]
    for row, plane in enumerate(W_PLANES):
        p = G.PLANE_NAMES.index(plane)
        y0 = HEAD + row * (TILE + LABEL)
        d.text((4, y0 + TILE // 2 - 6), plane, fill="white")
        for k in range(frames):
            ang = [0.0] * 6
            ang[p] = 2 * math.pi * k / frames
            ratio = G.volume_ratio(G.project3(V, G.view_angles(i, ang)))
            s = ViewState(shape=i, playing=False, faces=True, bright=1.2, zoom=ZOOM)
            s.ang, s.yaw, s.pitch = ang, YAW, PITCH
            fbo.use()
            ctx.viewport = (0, 0, big, big)
            renderer.draw(s, big, big, t_now=0.0)
            px = np.frombuffer(fbo.read(components=3), dtype=np.uint8)
            tile = Image.fromarray(px.reshape(big, big, 3)[::-1].copy())
            x0 = ROW_LABEL + k * TILE
            img.paste(tile.resize((TILE, TILE), Image.LANCZOS), (x0, y0))
            colour = "white" if ratio >= G.VOLUME_FLOOR else (255, 90, 90)
            d.text((x0 + 3, y0 + TILE), f"{360 * k // frames} deg  {ratio:.2f}", fill=colour)
    fbo.release()
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--prefix", default="before", help="file name prefix: before / after")
    ap.add_argument("--shapes", default=f"0-{len(G.SHAPES) - 1}",
                    help="indices, e.g. 18-24 or 17,21")
    ap.add_argument("--steps", type=int, default=72, help="sweep steps per turn (72 = 5°)")
    ap.add_argument("--frames", type=int, default=12, help="tiles per row in the sheets")
    ap.add_argument("--no-png", action="store_true", help="numbers only, no GL")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    shapes = parse_shapes(a.shapes)

    rows = []
    for i in shapes:
        m = measure(i, a.steps)
        rows.append({"index": i, "name": G.SHAPES[i].name, "w": G.SHAPES[i].w, **m})
        worst = min(m[ps][pl]["min"] for ps in m for pl in m[ps])
        line = "  ".join(f"{pl} {m['axis'][pl]['min']:.3f}@{m['axis'][pl]['at']:3.0f}°"
                         for pl in W_PLANES)
        print(f"{i:2d} {G.SHAPES[i].name:22s} {G.SHAPES[i].w:6s} {line}  worst {worst:.3f}")

    meta = {"steps": a.steps, "d4": ViewState().depth4, "floor": G.VOLUME_FLOOR,
            "generic_pose": list(G.GENERIC_POSE),
            "measure": "smallest / largest singular value of the centred 3D cloud "
                       "after rotate4 and the 4D→3D divide (geometry.volume_ratio)",
            "edge_on": "share of face area drawn at under a tenth of its 4D area "
                       "(geometry.edge_on_share); the tests gate a lifted or masked shape "
                       "at 0.15"}
    (OUT / f"{a.prefix}-ratios.json").write_text(
        json.dumps({**meta, "shapes": rows}, indent=1, ensure_ascii=False) + "\n")
    with open(OUT / f"{a.prefix}-ratios.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["index", "name", "w", "pass", "plane", "min_ratio", "at_deg",
                     "max_edge_on_share", "edge_on_at_deg"])
        for r in rows:
            for ps in ("axis", "generic"):
                for pl in W_PLANES:
                    m = r[ps][pl]
                    wr.writerow([r["index"], r["name"], r["w"], ps, pl, f"{m['min']:.4f}",
                                 f"{m['at']:.0f}", f"{m['edge_on']:.3f}",
                                 f"{m['edge_on_at']:.0f}"])
    print("wrote", (OUT / f"{a.prefix}-ratios.json").relative_to(ROOT))

    if a.no_png:
        return
    import moderngl

    from hyperspace.render import Renderer

    ctx = moderngl.create_context(standalone=True)
    renderer = Renderer(ctx)
    for i in shapes:
        path = OUT / f"{a.prefix}-{i:02d}-{slug(G.SHAPES[i].name)}.png"
        # red on black quantizes to a small palette with nothing lost to the eye
        img = sheet(ctx, renderer, i, a.frames).quantize(64, dither=Image.Dither.NONE)
        img.save(path, optimize=True)
        print("wrote", path.relative_to(ROOT), f"{path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
