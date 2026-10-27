#!/usr/bin/env python3
"""The instance count at zero, offscreen: one scene, five frames.

Renders a 24-cell with face patterns through the real pipeline (render.py)
and writes a strip to docs/plans/assets/16-paper-cuts/instances-zero.png
(plan 16 WP5):

  1  instances 1            the scene
  2  instances 0            nothing drawn: the ground
  3  instances 0 + plasma   a generator effect still paints
  4  instances 0, the look-back on, a few frames after the count left 1:
     the echoes of the frames that were drawn, over the empty scene
  5  the same, later: the echoes fading as the ring turns over

Under each tile it prints the picture's mean and how many face vertices
the scene pass left for the cover pass.

An offscreen render, not the rig: it shows what the passes put in the
framebuffer, not what a projector shows.

    uv run python tools/instances_shots.py [--after 3] [--later 12]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.fx import FxState
from hyperspace.graphmigrate import wiring_of
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "16-paper-cuts"
W, H = 640, 400
LABEL = 20
WARM = 12            # frames at the tile's first count before the shot


def view() -> ViewState:
    s = ViewState(shape=10, faces=True, pattern=2, bright=1.3)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    s.yaw, s.pitch = 0.4, 0.25
    return s


def shot(ctx, counts: list[int], *, plasma: bool = False,
         lookback: bool = False) -> tuple[np.ndarray, int]:
    """One frame per entry of `counts` at 60 fps, the scene turning; the
    last as RGB, with the face vertices its scene pass drew."""
    fx = FxState()
    fx.values["plasma"]["on"] = plasma
    r = Renderer(ctx, fx=fx)
    r.wiring = wiring_of(fx)  # plan 33 R23: its run as a load lands it
    if lookback:
        st = r.lookback.state
        st.on, st.echoes, st.gap, st.echo_mix, st.tint_from = True, 8, 1 / 30, 0.8, 0
        r.dreamer.source = None                      # no dream worker: the echoes alone
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
    s = view()
    for k, n in enumerate(counts):
        s.instances = n
        s.ang = [a + 0.04 for a in s.ang]
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=4.0 + k / 60)
        assert ctx.fbo is fbo, "a frame did not end on its target"
    img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1].copy()
    fbo.release()
    return img, r._face_verts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--after", type=int, default=3,
                    help="frames at 0 before the look-back tile's shot")
    ap.add_argument("--later", type=int, default=12,
                    help="frames at 0 before the second look-back tile's shot")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = moderngl.create_context(standalone=True)
    tiles = [
        ("instances 1", shot(ctx, [1] * WARM)),
        ("instances 0 · nothing drawn", shot(ctx, [0] * WARM)),
        ("0 + plasma (a generator)", shot(ctx, [0] * WARM, plasma=True)),
        (f"0, look-back: {a.after} frames after 1",
         shot(ctx, [1] * WARM + [0] * a.after, lookback=True)),
        (f"…and {a.later} frames after",
         shot(ctx, [1] * WARM + [0] * a.later, lookback=True)),
    ]
    tw, th = W // 2, H // 2
    strip = Image.new("RGB", (len(tiles) * tw, th + LABEL), "black")
    d = ImageDraw.Draw(strip)
    for k, (label, (img, face_verts)) in enumerate(tiles):
        print(f"{label:>36}: mean {img.mean():6.2f}  max {img.max():3d}  "
              f"face vertices {face_verts}")
        strip.paste(Image.fromarray(img).resize((tw, th)), (k * tw, LABEL))
        d.text((k * tw + 4, 4), label, fill="white")
    assert tiles[0][1][0].any() and not tiles[1][1][0].any(), "tile 2 is not the bare ground"
    assert tiles[2][1][0].any() and tiles[3][1][0].any(), "the effect or the trail drew nothing"
    path = OUT / "instances-zero.png"
    strip.save(path)
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
