#!/usr/bin/env python3
"""A fractal's lines and faces sorted on the CPU (the default,
`view.frac_additive` off) against additive and unsorted on the GPU (on),
the same dive side by side.

For each fractal, four views stepped in lockstep from the same state — the
faces off (top) and on (bottom), sorted (left) and additive (right) — dive
in from the whole shape, turning as they go, then hold deep inside. Each
frame is the real pipeline offscreen (`render.render_offscreen`'s
`Renderer.draw`, the default wiring). Writes, per fractal:

- `<slug>.png`: one still of the four, deep in the dive;
- `<slug>.mp4`: the dive (`--seconds`, 30 fps, two-pass H.264), with
  `--video`.

An offscreen render on whatever GL this machine has, not the rig: it shows
what the passes put in the framebuffer, not what a projector shows.

    uv run python tools/fractal_compare.py --out docs/plans/assets/64-recursive-geometry --video
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
from hyperspace.render import Renderer
from hyperspace.view import ViewState

DIVES = ("Sierpinski tetrahedron", "Menger sponge", "Sierpinski 5-cell")
FPS = 30
LABEL = 26
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def views(name: str) -> list[ViewState]:
    """The four views, in grid order: (faces, additive) = (off, sorted),
    (off, additive), (on, sorted), (on, additive)."""
    out = []
    for faces in (False, True):
        for additive in (False, True):
            s = ViewState(shape=shape_index(name), faces=faces, lines=True, points=True)
            s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
            s.yaw, s.pitch = 0.45, 0.3
            s.zoom = 1.3
            s.frac_additive = additive
            out.append(s)
    return out


def advance(s: ViewState, dt: float, rate: float) -> None:
    """One frame: the spin, the zoom by `rate`, the re-root."""
    s.integrate(dt)
    s.zoom *= rate
    fractal.step(s)


class Grid:
    def __init__(self, ctx, w: int, h: int):
        self.ctx, self.w, self.h = ctx, w, h
        self.r = Renderer(ctx)
        from hyperspace.graph import Wiring
        from hyperspace.graphmigrate import wired_wiring
        self.r.wiring = wired_wiring(Wiring())
        tex = ctx.texture((w, h), 3)
        self.fbo = ctx.framebuffer(color_attachments=[tex])
        try:
            self.font = ImageFont.truetype(FONT, 16)
        except OSError:
            self.font = ImageFont.load_default()

    def one(self, s: ViewState, t: float) -> np.ndarray:
        self.fbo.use()
        self.ctx.viewport = (0, 0, self.w, self.h)
        self.r.draw(s, self.w, self.h, t_now=t)
        return np.frombuffer(self.fbo.read(components=3), np.uint8).reshape(
            self.h, self.w, 3)[::-1]

    def frame(self, vs: list[ViewState], t: float, title: str) -> Image.Image:
        w, h = self.w, self.h
        img = Image.new("RGB", (2 * w, 2 * h + LABEL), (12, 12, 12))
        d = ImageDraw.Draw(img)
        for k, s in enumerate(vs):
            x, y = (k % 2) * w, LABEL + (k // 2) * h
            img.paste(Image.fromarray(self.one(s, t)), (x, y))
            tag = (f"{'additive · GPU, unsorted' if s.frac_additive else 'sorted · CPU painter'}"
                   f" · faces {'on' if s.faces else 'off'}")
            box = d.textbbox((x + 8, y + 6), tag, font=self.font)
            d.rectangle((box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3), fill=(0, 0, 0))
            d.text((x + 8, y + 6), tag, fill=(235, 235, 235), font=self.font)
        d.text((8, 4), title, fill=(235, 235, 235), font=self.font)
        d.line([(w, LABEL), (w, 2 * h + LABEL)], fill=(60, 60, 60))
        d.line([(0, LABEL + h), (2 * w, LABEL + h)], fill=(60, 60, 60))
        return img


def run(grid: Grid, name: str, out: Path, seconds: float, levels: float,
        video: bool) -> None:
    spec = fractal.FRACTALS[name]
    vs = views(name)
    n = int(seconds * FPS)
    hold0, hold1 = FPS, int(1.5 * FPS)                 # the whole shape; deep inside
    dive = max(n - hold0 - hold1, 1)
    rate = (1.0 / spec.ratio) ** (levels / dive)       # `levels` re-roots over the dive
    slug = name.lower().replace(" ", "-")
    still_at = n - hold1 // 2
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(n):
            t = k / FPS
            r = rate if hold0 <= k < hold0 + dive else 1.0
            for s in vs:
                advance(s, 1.0 / FPS, r)
            if not video and k != still_at:
                continue
            title = (f"{name} · {len(vs[0].dive.path)} levels in · zoom {vs[0].zoom:.2f}"
                     "   (left: sorted, the default — right: additive)")
            img = grid.frame(vs, t, title)
            if k == still_at:
                img.save(out / f"{slug}.png", optimize=True)
            if video:
                img.save(Path(tmp) / f"{k:05d}.png", compress_level=1)
        if video:
            mp4 = out / f"{slug}.mp4"
            src = ["-framerate", str(FPS), "-i", str(Path(tmp) / "%05d.png")]
            enc = ["-c:v", "libx264", "-preset", "slow", "-b:v", "1600k"]
            log = str(Path(tmp) / "pass")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, *enc, "-pass", "1",
                            "-passlogfile", log, "-an", "-f", "null", "/dev/null"], check=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, *enc, "-pass", "2",
                            "-passlogfile", log, "-pix_fmt", "yuv420p", "-movflags",
                            "+faststart", str(mp4)], check=True)
    print(f"{name}: {out / (slug + '.png')}" + (f", {out / (slug + '.mp4')}" if video else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", type=int, nargs=2, default=(640, 360), metavar=("W", "H"),
                    help="one view's size; the grid is twice each")
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--levels", type=float, default=6.0, help="re-roots over the dive")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--only", nargs="+", default=None)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    ctx = moderngl.create_context(standalone=True)
    grid = Grid(ctx, *a.size)
    for name in a.only or DIVES:
        run(grid, name, a.out, a.seconds, a.levels, a.video)


if __name__ == "__main__":
    main()
