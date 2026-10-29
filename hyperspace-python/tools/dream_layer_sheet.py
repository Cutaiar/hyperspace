#!/usr/bin/env python3
"""Every dream layer side by side: one input dreamed at each, a contact sheet.

The worker's own recipe (dream.py) on a still frame at 256 px, the
defaults (k 0.05, two passes of strength 0.03, jitter 8, one scale),
for `--frames` frames, tiles in the layer menu's order (lookback.
LAYER_INFO) with each name under its tile, and each layer's median ms
per frame printed. `--input render` is a rotating 24-cell through the real
renderer (standalone GL context, no window), cropped to the shape;
`--input texture` is a soft colour field with the mask open, which shows
each layer's own texture. Needs the weights: `--weights DIR` is read (and
downloaded into, ~580 MB) through dream.load_state.

  uv run python tools/dream_layer_sheet.py --weights /tmp/w --out sheet.jpg
  uv run python tools/dream_layer_sheet.py --weights /tmp/w --input texture --frames 60 \
      --out sheet-texture.jpg

The pictures in docs/plans/assets/20-fx-dream-looks/dream-layers*.jpg are
these two runs.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

W, H = 1280, 820
TILE_W, CAP, COLS = 300, 28, 6


def rendered(res: int):
    import moderngl
    from PIL import Image

    from hyperspace.graph import Wiring
    from hyperspace.graphmigrate import wired_wiring
    from hyperspace.lookback import DreamState, echo_size
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    r = Renderer(ctx, DreamState(on=False))
    # plan 36 T3: a bare renderer draws the app's empty frame; the
    # tool's own wiring is today's frame (render.render_offscreen's)
    r.wiring = wired_wiring(Wiring())
    s = ViewState(shape=10, faces=True, pattern=2, bright=1.3, speed=3.0)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    s.yaw, s.pitch = 0.4, 0.25
    for k in range(30):
        s.integrate(1 / 60)
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=k / 60)
    ctx.finish()
    px = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1]
    return Image.fromarray(px.copy()).resize(echo_size(res, W, H), Image.BILINEAR)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--input", choices=("render", "texture"), default="render")
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--res", type=int, default=256)
    args = ap.parse_args()

    import torch
    import torch.nn.functional as F
    from PIL import Image, ImageDraw, ImageFont

    from hyperspace import dream
    from hyperspace.lookback import LAYER_INFO, echo_size

    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    ew, eh = echo_size(args.res, W, H)
    if args.input == "texture":
        torch.manual_seed(3)
        lo = torch.rand(1, 3, 6, 9, device=dev)
        frame = 0.25 + 0.5 * F.interpolate(lo, size=(eh, ew), mode="bicubic",
                                           align_corners=False).clamp(0, 1)
        mask = torch.ones(1, 1, eh, ew, device=dev)
        src = Image.fromarray(frame[0].permute(1, 2, 0).mul(255).byte().cpu().numpy())
        box = (0, 0, ew, eh)
    else:
        src = rendered(args.res)
        frame = torch.from_numpy(np.array(src)).permute(2, 0, 1)[None].float().div(255).to(dev)
        lum = F.avg_pool2d(frame.mean(1, keepdim=True), dream.MASK_BLUR, stride=1,
                           padding=dream.MASK_BLUR // 2)
        mask = (lum * dream.MASK_GAIN).clamp(0, 1)
        ys, xs = np.nonzero(mask[0, 0].cpu().numpy() > 0.05)
        box = (max(0, xs.min() - 6), max(0, ys.min() - 6), min(ew, xs.max() + 6),
               min(eh, ys.max() + 6))

    def sync():
        if dev.type == "mps":
            torch.mps.synchronize()

    stacks: dict = {}
    tiles = [("input", "", src)]
    for name, (net_name, _, _) in LAYER_INFO.items():
        net = dream.build_trunk(name, args.weights, dev, torch.float32, stacks)
        torch.manual_seed(1)
        D, times = frame.clone(), []
        for _ in range(args.frames):
            sync()
            t = time.perf_counter()
            D = D * 0.95 + frame * 0.05
            D = dream.dream_octave(D, net, 1.0, 2, 0.03, 8, mask).detach()
            sync()
            times.append((time.perf_counter() - t) * 1e3)
        out = (D * mask)[0].permute(1, 2, 0).clamp(0, 1).mul(255).byte().cpu().numpy()
        tiles.append((name, net_name, Image.fromarray(out)))
        print(f"{name:12s} {statistics.median(times[5:]):6.1f} ms a frame "
              f"(two passes, {ew}×{eh}, {dev.type})", flush=True)

    tile_h = round(TILE_W * (box[3] - box[1]) / (box[2] - box[0]))
    font = ImageFont.load_default(size=18)
    rows = (len(tiles) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TILE_W, rows * (tile_h + CAP)), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for k, (name, net_name, im) in enumerate(tiles):
        x, y = (k % COLS) * TILE_W, (k // COLS) * (tile_h + CAP)
        sheet.paste(im.crop(box).resize((TILE_W - 4, tile_h - 4), Image.LANCZOS), (x + 2, y + 2))
        draw.text((x + 6, y + tile_h + 4), f"{name}  {net_name}", fill=(235, 235, 235),
                  font=font)
    sheet.save(args.out, quality=85, optimize=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
