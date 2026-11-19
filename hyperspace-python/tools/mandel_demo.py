#!/usr/bin/env python3
"""The Mandelbrot effect's demo (plan 63): stills and a short video, drawn
offscreen by the real pass (`FxChain.run_one`, a graph Effect node's), its
grey step count coloured by the real Palette pass in gradient mode, as a
patch would wire them (mandel → palette → output).

  uv run python tools/mandel_demo.py --out <dir>               # stills + mandel-demo.mp4
  uv run python tools/mandel_demo.py --out <dir> --no-video    # the stills alone

The stills (`docs/plans/assets/63-mandelbrot/` holds the committed set):

- `sizes.png` — one view at 540, 810 and 1080 lines into a 1920×1080 output,
  a quarter of each enlarged, so the upscale's softness is plain;
- `zoom.png` — a dive into the seahorse valley, 1× to 10⁹×, across the
  switch from float32 direct to perturbation at 10⁴×;
- `terms.png` — the term sweep: c round a circle on the Julia slice, the
  Slice from the Mandelbrot set to a Julia set, p from 2 to 6, z₀ off 0;
- `colour.png` — Output steps through Palette's gradient, the built-in ramp,
  and the inside coloured.

The video is the zoom and the sweeps as motion, 1280×720 at 30 fps,
captioned. Videos stay out of the repository. Frame times here are Mesa's:
`tools/mandel_bench.py` on the rig is the measure.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import moderngl
import numpy as np
from catalog_demo import FPS, H, W, encoder, font
from PIL import Image, ImageDraw

from hyperspace import mandel as M
from hyperspace.fx import FxChain, FxState

SEAHORSE = (-0.743643887037151, 0.131825904205330)
GRADIENT = {"mode": 1, "anchors": 4,             # Palette gradient: ink, violet, amber, cream
            "a1_hue": 230.0, "a1_sat": 0.8, "a1_val": 0.05,
            "a2_hue": 280.0, "a2_sat": 0.7, "a2_val": 0.55,
            "a3_hue": 35.0, "a3_sat": 0.9, "a3_val": 0.95,
            "a4_hue": 50.0, "a4_sat": 0.15, "a4_val": 1.0}


class Stage:
    """A chain with the Mandelbrot and a Palette after it, drawing into an
    output of `size`."""

    def __init__(self, ctx, size: tuple[int, int]):
        self.ctx, self.size = ctx, size
        self.st = FxState()
        self.mv = self.st.values["mandel"]
        self.defaults = dict(self.mv, on=True)
        self.st.values["palette"].update(on=True, mix=1.0, **GRADIENT)
        self.chain = FxChain(ctx, self.st)
        self.src = ctx.texture(size, 4)
        self.mid = ctx.framebuffer(color_attachments=[ctx.texture(size, 4, dtype="f2")])
        self.out = ctx.framebuffer(color_attachments=[ctx.texture(size, 4)])
        self.t = 0.0

    def draw(self, palette: bool = True, **view) -> Image.Image:
        self.mv.clear()
        self.mv.update(self.defaults)
        self.mv.update(view)
        self.chain.run_one("mandel", self.src, self.mid if palette else self.out, self.t, opaque=1)
        if palette:
            self.chain.run_one("palette", self.mid.color_attachments[0], self.out, self.t,
                               opaque=1)
        self.t += 1 / FPS
        w, h = self.size
        px = np.frombuffer(self.out.read(components=3), np.uint8).reshape(h, w, 3)
        return Image.fromarray(px[::-1].copy())

    @property
    def stats(self) -> dict:
        return self.chain.mandel.states["mandel"].stats

    def release(self):
        self.chain.release()
        for o in (self.src, self.mid, self.out):
            o.release()


def caption(im: Image.Image, text: str, size: int = 26) -> Image.Image:
    im = im.copy()
    d = ImageDraw.Draw(im)
    f = font(size)
    box = d.textbbox((0, 0), text, font=f)
    d.rectangle((0, im.height - box[3] - 24, box[2] + 32, im.height), fill=(0, 0, 0))
    d.text((16, im.height - box[3] - 12), text, font=f, fill=(255, 255, 255))
    return im


def sheet(tiles: list[Image.Image], cols: int) -> Image.Image:
    w, h = tiles[0].size
    rows = -(-len(tiles) // cols)
    out = Image.new("RGB", (cols * w, rows * h), (20, 20, 20))
    for i, t in enumerate(tiles):
        out.paste(t, ((i % cols) * w, (i // cols) * h))
    return out


def sizes_still(ctx, out: Path) -> None:
    """One view at each Size into 1920×1080, a quarter of each enlarged."""
    st = Stage(ctx, (1920, 1080))
    view = {"centre_x": -0.7436, "centre_y": 0.1318, "zoom": 60.0, "iters": 600.0}
    tiles = []
    for i, lines in enumerate(M.SIZES):
        full = st.draw(size=i, **view)
        crop = full.crop((720, 405, 1200, 675)).resize((960, 540), Image.NEAREST)
        w, h = st.stats["size"]
        how = "upscaled to" if (w, h) != (1920, 1080) else "drawn straight into"
        tiles.append(caption(crop, f"Size {lines}: rendered {w}×{h}, {how} 1920×1080"
                                   " (a quarter of it, 2× enlarged)", 20))
    st.release()
    sheet(tiles, 3).save(out / "sizes.png")


ZOOMS = (1.0, 30.0, 1e3, 9e3, 2e4, 1e6, 1e8, 1e9)


def zoom_still(ctx, out: Path) -> None:
    st = Stage(ctx, (640, 360))
    tiles = []
    for z in ZOOMS:
        im = st.draw(centre_x=SEAHORSE[0], centre_y=SEAHORSE[1], zoom=z, iters=1500.0,
                     size=0)
        tier = "perturbation" if st.stats["perturb"] else "float32 direct"
        tiles.append(caption(im, f"{z:.3g}× · {tier}", 18))
    st.release()
    sheet(tiles, 4).save(out / "zoom.png")


def terms_views() -> list[tuple[str, dict]]:
    out = []
    for k in range(4):
        a = k * math.tau / 4
        cx, cy = 0.7885 * math.cos(a), 0.7885 * math.sin(a)
        out.append((f"Julia slice, |c| 0.7885 at {90 * k}°", {"slice": 1.0, "centre_x": 0.0,
                    "c_x": cx, "c_y": cy, "zoom": 0.9, "iters": 400.0}))
    for s in (0.0, 0.35, 0.7, 1.0):
        out.append((f"Slice {s:g}: c = (-0.8, 0.156)", {"slice": s, "centre_x": -0.25,
                    "c_x": -0.8, "c_y": 0.156, "zoom": 0.9, "iters": 400.0}))
    for p in (2, 3, 4, 6):
        out.append((f"Power {p}", {"power": p, "centre_x": 0.0, "zoom": 0.9, "iters": 300.0}))
    for z in (0.0, 0.3, 0.6, 0.9):
        out.append((f"z₀ = ({z:g}, 0) on the Mandelbrot slice",
                    {"z0_x": z, "centre_x": -0.5, "zoom": 0.9, "iters": 300.0}))
    return out


def terms_still(ctx, out: Path) -> None:
    st = Stage(ctx, (480, 270))
    tiles = [caption(st.draw(**v), label, 15) for label, v in terms_views()]
    st.release()
    sheet(tiles, 4).save(out / "terms.png")


def colour_still(ctx, out: Path) -> None:
    st = Stage(ctx, (640, 360))
    view = {"centre_x": -0.7436, "centre_y": 0.1318, "zoom": 40.0, "iters": 800.0,
            "cycle": 48.0}
    tiles = [caption(st.draw(palette=False, **view), "Output steps (grey), as the node puts it out", 18),
             caption(st.draw(**view), "steps → Palette gradient", 18),
             caption(st.draw(palette=False, output=1, **view), "Output ramp (built in)", 18),
             caption(st.draw(interior=1, **view), "Inside coloured (periodicity time)", 18)]
    st.release()
    sheet(tiles, 2).save(out / "colour.png")


def video(ctx, out: Path, seconds_zoom: float = 10.0) -> None:
    st = Stage(ctx, (W, H))
    enc = encoder(out / "mandel-demo.mp4")
    try:
        n = int(seconds_zoom * FPS)
        for i in range(n):           # a dive: 1× → 10⁹× at a steady rate, through the switch
            z = 10 ** (9 * i / (n - 1))
            im = st.draw(centre_x=SEAHORSE[0], centre_y=SEAHORSE[1], zoom=z, iters=1200.0,
                         size=0)
            tier = "perturbation" if st.stats["perturb"] else "float32 direct"
            enc.stdin.write(caption(im, f"Dive · {z:.3g}× · {tier} · Size 540").tobytes())
        for i in range(4 * FPS):     # c round a circle on the Julia slice
            a = math.tau * i / (4 * FPS)
            im = st.draw(slice=1.0, centre_x=0.0, c_x=0.7885 * math.cos(a),
                         c_y=0.7885 * math.sin(a), zoom=0.9, iters=300.0, size=0)
            enc.stdin.write(caption(im, "Julia slice · c round a circle").tobytes())
        for i in range(4 * FPS):     # the tilt from the Mandelbrot set to a Julia set
            s = 0.5 - 0.5 * math.cos(math.pi * i / (4 * FPS))
            im = st.draw(slice=s, centre_x=-0.25, c_x=-0.8, c_y=0.156, zoom=0.9,
                         iters=300.0, size=0)
            enc.stdin.write(caption(im, f"Slice {s:.2f} · Mandelbrot → Julia").tobytes())
    finally:
        enc.stdin.close()
        enc.wait()
        st.release()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True, help="where the stills and video go")
    ap.add_argument("--no-video", action="store_true", help="the stills alone")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    ctx = moderngl.create_context(standalone=True)
    for still in (sizes_still, zoom_still, terms_still, colour_still):
        still(ctx, a.out)
        print("drew", still.__name__, flush=True)
    if not a.no_video:
        video(ctx, a.out)
        print("drew mandel-demo.mp4", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
