#!/usr/bin/env python3
"""A Menger sponge dive, rendered offscreen, for a before/after pair.

The real pipeline (`Renderer.draw`, the default wiring) on whatever GL this
machine has — drive-the-app §1 — with a red cross at the middle of the
screen and, in the corner, how many levels in and how much of the screen
has something drawn on it (an 8 × 8 grid of tiles).

- `--mode zoom`: camera.zoom grown by a ratio a frame and `fractal.step`
  re-rooting, as a saw LFO on the zoom (or a hand) does. This mode needs nothing
  but the zoom and `fractal.step`.
- `--mode rate`: the dive rate (`view.frac_dive`) at the same levels a
  second; `--settle cell` (the default) or `point`.

    uv run python tools/fractal_dive_demo.py --mode rate --out after.mp4

An offscreen render, not the rig: it shows what the passes put in the
framebuffer, not what a projector shows.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace import fractal
from hyperspace.geometry import shape_index
from hyperspace.graph import Wiring
from hyperspace.graphmigrate import wired_wiring
from hyperspace.render import Renderer
from hyperspace.view import ViewState

FPS = 30
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TILES = 8


def view(name: str, spin: bool) -> ViewState:
    s = ViewState(shape=shape_index(name), lines=True, points=True)
    s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
    s.yaw, s.pitch = 0.45, 0.3
    s.zoom = 1.3
    s.playing = spin
    return s


def advance(s: ViewState, mode: str, levels_per_s: float, dt: float) -> None:
    """One frame: the spin, the dive, the re-root (and, as the app does, the
    view goes inside once it has gone into a cell or outgrown the screen)."""
    s.integrate(dt)
    spec = fractal.spec_of(s.shape)
    if mode == "zoom":
        s.zoom *= (1.0 / spec.ratio) ** (levels_per_s * dt)
        fractal.step(s)
        return
    s.frac_dive = levels_per_s
    s.dive.inside = bool(s.dive.path) or s.zoom >= fractal.Z_IN
    fractal.step(s, None, None, dt)


def coverage(a: np.ndarray) -> float:
    h, w = a.shape[:2]
    lit = a.max(axis=2) > 40
    th, tw = h // TILES, w // TILES
    return float(lit[:th * TILES, :tw * TILES].reshape(TILES, th, TILES, tw).any(axis=(1, 3)).mean())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True, help="the .mp4 (a .png still beside it)")
    ap.add_argument("--mode", choices=("zoom", "rate"), required=True)
    ap.add_argument("--settle", choices=("cell", "point"), default="cell")
    ap.add_argument("--shape", default="Menger sponge")
    ap.add_argument("--seconds", type=float, default=24.0)
    ap.add_argument("--rate", type=float, default=1.0, help="levels a second")
    ap.add_argument("--spin", action="store_true")
    ap.add_argument("--label", default="")
    ap.add_argument("--size", default="960x540")
    args = ap.parse_args()
    if args.mode == "rate":
        fractal.SETTLE_ON = args.settle
    w, h = (int(v) for v in args.size.split("x"))
    ctx = moderngl.create_context(standalone=True)
    r = Renderer(ctx)
    r.wiring = wired_wiring(Wiring())
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((w, h), 3)])
    try:
        font = ImageFont.truetype(FONT, 18)
    except OSError:
        font = ImageFont.load_default()
    s = view(args.shape, args.spin)
    n = int(args.seconds * FPS)
    hold = FPS                                   # a second of the whole shape first
    covs = []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(n):
            t = k / FPS
            if k >= hold:
                advance(s, args.mode, args.rate, 1.0 / FPS)
            else:
                s.integrate(1.0 / FPS)
            fbo.use()
            ctx.viewport = (0, 0, w, h)
            r.draw(s, w, h, t_now=t)
            a = np.frombuffer(fbo.read(components=3), np.uint8).reshape(h, w, 3)[::-1]
            c = coverage(a)
            if k >= hold + 3 * FPS:
                covs.append(c)
            img = Image.fromarray(a.copy())
            d = ImageDraw.Draw(img)
            cx, cy = w // 2, h // 2
            d.line([(cx - 14, cy), (cx + 14, cy)], fill=(255, 40, 40), width=2)
            d.line([(cx, cy - 14), (cx, cy + 14)], fill=(255, 40, 40), width=2)
            text = (f"{args.label}   {len(s.dive.path)} levels in   "
                    f"screen drawn on: {100 * c:.0f}%")
            box = d.textbbox((10, 8), text, font=font)
            d.rectangle((box[0] - 5, box[1] - 4, box[2] + 5, box[3] + 4), fill=(0, 0, 0))
            d.text((10, 8), text, fill=(235, 235, 235), font=font)
            img.save(Path(tmp) / f"{k:05d}.png", compress_level=1)
            if k == n - FPS:
                img.save(args.out.with_suffix(".png"), optimize=True)
        src = ["-framerate", str(FPS), "-i", str(Path(tmp) / "%05d.png")]
        enc = ["-c:v", "libx264", "-preset", "slow", "-b:v", "1400k"]
        log = str(Path(tmp) / "pass")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, *enc, "-pass", "1",
                        "-passlogfile", log, "-an", "-f", "null", "/dev/null"], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, *enc, "-pass", "2",
                        "-passlogfile", log, "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(args.out)], check=True)
    cv = np.array(covs)
    print(f"{args.out}: {len(s.dive.path)} levels; screen drawn on {100 * cv.mean():.0f}% "
          f"on average, {100 * cv.min():.0f}% at the least (after the first 3 s of the dive)")


if __name__ == "__main__":
    main()
