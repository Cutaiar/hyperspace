#!/usr/bin/env python3
"""The master dim, offscreen: one frame at four settings of the crossfader.

Renders a 24-cell with face patterns through the real pipeline (render.py)
with an effect on and two synthetic ghost hands over it (the hands
tests/test_ghost.py feeds — no tracker), then the same frame with
`Renderer.dim` at 1.0, 0.5, 0.15 and 0, and writes the strip to
docs/plans/assets/15-safety-net/dim.png (plan 15 WP3). Under each tile it
prints the mean of the picture and its lowest alpha: the colour scales,
the opaque ground's alpha does not.

An offscreen render, not the rig: it shows what the pass does to the
framebuffer, not how the throw feels on the glass.

    uv run python tools/dim_shots.py [--effect warp] [--frames 30]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fake_hands import hand  # tests/fake_hands.py

from hyperspace.fx import FxState
from hyperspace.graphmigrate import wiring_of
from hyperspace.hands import skeleton
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "15-safety-net"
W, H = 640, 400
DIMS = (1.0, 0.5, 0.15, 0.0)
LABEL = 20


def view() -> ViewState:
    s = ViewState(shape=10, faces=True, pattern=2, bright=1.3)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    s.yaw, s.pitch = 0.4, 0.25
    return s


def hands() -> SimpleNamespace:
    """What the Ghost reads of a tracker: two skeletons and the mode."""
    return SimpleNamespace(
        skeleton={"left": skeleton(hand("left", "open", (-90.0, 210.0, 0.0))),
                  "right": skeleton(hand("right", "fist", (90.0, 200.0, 10.0)))},
        cfg={"mode": "desktop"})


def shot(ctx, dim: float, effect: str, frames: int) -> np.ndarray:
    """`frames` frames at 60 fps with the master at `dim`; the last as RGBA."""
    fx = FxState()
    if effect:
        fx.values[effect]["on"] = True
    r = Renderer(ctx, fx=fx)
    r.wiring = wiring_of(fx)  # plan 33 R23: its run as a load lands it
    r.ghost.state.on, r.ghost.state.alpha, r.ghost.source = True, 1.0, hands()
    r.dim = dim
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
    s = view()
    for k in range(frames):
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=4.0 + k / 60)
    if r.dim_error or r.ghost.error:
        print("  errors:", r.dim_error, r.ghost.error)
    img = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4)[::-1].copy()
    fbo.release()
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--effect", default="warp")
    ap.add_argument("--frames", type=int, default=30)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = moderngl.create_context(standalone=True)
    tw, th = W // 2, H // 2
    strip = Image.new("RGB", (len(DIMS) * tw, th + LABEL), "black")
    d = ImageDraw.Draw(strip)
    full = None
    for k, dim in enumerate(DIMS):
        img = shot(ctx, dim, a.effect, a.frames)
        full = img if full is None else full
        rgb, alpha = img[..., :3].astype(float), img[..., 3]
        ratio = rgb.mean() / max(full[..., :3].mean(), 1e-9)
        label = f"dim {'black' if dim <= 0 else f'{dim * 100:.0f}%'}"
        print(f"{label:>10}: mean {rgb.mean():6.2f} ({ratio:.3f} of full), "
              f"lowest alpha {alpha.min()}")
        strip.paste(Image.fromarray(img[..., :3]).resize((tw, th)), (k * tw, LABEL))
        d.text((k * tw + 4, 4), f"{label}   alpha {alpha.min()}", fill="white")
    path = OUT / "dim.png"
    strip.save(path)
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
