#!/usr/bin/env python3
"""The pattern-input convention (plan 22 B1), offscreen: contact sheets.

One sheet per mode: a row per input (SCALE … SPREAD), three tiles — the
input at 0, at 1.0 and at 2.6, every other input at 1.0. Read down a
column at 1.0 and every row is the same picture, the mode as designed;
read across a row and the input does its one thing. Then one sheet per
input: a row per mode, the same three columns — read down it to see the
input do the same kind of change on every mode.

A tile is one face's pattern alone (`Renderer.pattern_tile`): what face 5
shows, premultiplied by its intensity over black, the disk a face can
cover at full light and the corners outside it dimmed. Two rows are not
stills, because a still cannot show them: SPEED is an exposure (the
average of eight stills across half a second — 0 is sharp, a fast
pattern smears), and SPREAD shows four faces (0–3) side by side, which
drift apart above 0.

And a gallery (plan 22 B3): a row per mode, three columns — silence at
neutral, a quiet passage and a loud one with a hard kick and bright hats
— the bands as the analyzer would read them (`Renderer.bands`, which
METER and PULSE draw) and the eight inputs as the factory routes would
push them (lane i on input i, depth 1 on a base of 1: 1 + 2.6·u, held to
the range; HUE and SPREAD unrouted) — and a fourth, the loud passage
through the same routes at depth 0.3.

Writes docs/plans/assets/22-face-patterns/mode-NN-<name>.png,
input-K-<name>.png and b3-gallery.png. Offscreen renders on this machine's GPU, not the app
on a screen.

    uv run python tools/pattern_sheet.py [--t 4.0] [--tile 128]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.patterns import INPUTS, MODES, N_INPUTS, SPEED, SPREAD, effect
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "22-face-patterns"
VALUES = (0.0, 1.0, 2.6)
FID = 5                       # the face a still shows: not face 0, so SPREAD's scatter shows
EXPOSURE = (0.5, 8)           # SPEED's row: seconds, stills
BG, INK, DIM = (18, 18, 22), (232, 232, 232), (150, 150, 158)


def tile(r: Renderer, mode: int, k: int, v: float, t: float, n: int) -> np.ndarray:
    """Mode `mode` with input `k` at `v` (the rest at 1.0), as an n² tile."""
    mods = [1.0] * N_INPUTS
    mods[k] = v
    s = ViewState(pattern=mode, pattern_mod=mods)
    if k == SPEED:
        span, count = EXPOSURE
        acc = sum(r.pattern_tile(s, n, t + span * j / (count - 1), FID).astype(np.float32)
                  for j in range(count))
        img = (acc / count).astype(np.uint8)
    elif k == SPREAD:
        h = n // 2
        quads = [r.pattern_tile(s, h, t, f) for f in range(4)]
        img = np.zeros((n, n, 3), np.uint8)
        for f, q in enumerate(quads):
            y, x = divmod(f, 2)
            img[y * h:(y + 1) * h, x * h:(x + 1) * h] = q
        return img
    else:
        img = r.pattern_tile(s, n, t, FID)
    yy, xx = np.mgrid[0:n, 0:n]
    disk = (np.hypot(xx + 0.5 - n / 2, yy + 0.5 - n / 2) <= n / 2)[..., None]
    return np.where(disk, img, (img * 0.3).astype(np.uint8))


def save(img: Image.Image, path: Path) -> None:
    img = img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    img.save(path, optimize=True)
    print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


def mode_sheet(r: Renderer, mode: int, t: float, n: int) -> Image.Image:
    m = MODES[mode]
    lw, gap, head = 300, 4, 64
    img = Image.new("RGB", (lw + 3 * (n + gap), head + N_INPUTS * (n + gap)), BG)
    d = ImageDraw.Draw(img)
    big, font, small = (ImageFont.load_default(size=s) for s in (20, 15, 12))
    d.text((10, 8), f"{mode}  {m.name}", fill=INK, font=big)
    d.text((10, 34), m.about, fill=DIM, font=small)
    for c, v in enumerate(VALUES):
        d.text((lw + c * (n + gap) + n // 2 - 12, head - 18), f"{v:.1f}", fill=DIM, font=font)
    for k, inp in enumerate(INPUTS):
        y = head + k * (n + gap)
        d.text((10, y + n // 2 - 18), f"{k}  {inp.name}", fill=INK, font=font)
        d.text((10, y + n // 2 + 2), effect(mode, k) or "(not read)", fill=DIM, font=small)
        for c, v in enumerate(VALUES):
            img.paste(Image.fromarray(tile(r, mode, k, v, t, n)), (lw + c * (n + gap), y))
    return img


def input_sheet(r: Renderer, k: int, t: float, n: int) -> Image.Image:
    inp = INPUTS[k]
    modes = range(1, len(MODES))              # FLAT reads nothing
    lw, gap, head = 260, 4, 64
    img = Image.new("RGB", (lw + 3 * (n + gap), head + len(modes) * (n + gap)), BG)
    d = ImageDraw.Draw(img)
    big, font, small = (ImageFont.load_default(size=s) for s in (20, 15, 12))
    d.text((10, 8), f"{k}  {inp.name}", fill=INK, font=big)
    d.text((10, 34), inp.meaning[:96], fill=DIM, font=small)
    for c, v in enumerate(VALUES):
        d.text((lw + c * (n + gap) + n // 2 - 12, head - 18), f"{v:.1f}", fill=DIM, font=font)
    for row, mode in enumerate(modes):
        y = head + row * (n + gap)
        d.text((10, y + n // 2 - 18), MODES[mode].name, fill=INK, font=font)
        d.text((10, y + n // 2 + 2), effect(mode, k) or "(not read)", fill=DIM, font=small)
        for c, v in enumerate(VALUES):
            img.paste(Image.fromarray(tile(r, mode, k, v, t, n)), (lw + c * (n + gap), y))
    return img


QUIET = (0.22, 0.18, 0.15, 0.20, 0.12, 0.10)
LOUD = (0.85, 0.90, 0.30, 0.35, 0.45, 0.80)      # a hard kick and bright hats
# (column title, the six bands SUB … AIR as out / CEIL, the routes' depth)
PASSAGES = (("silence", (0.0,) * 6, 1.0),
            ("quiet", QUIET, 1.0),
            ("loud: kick + hats", LOUD, 1.0),
            ("loud, depth 0.3", LOUD, 0.3))


def factory_inputs(bands, depth: float = 1.0) -> list[float]:
    """The eight inputs as the factory routes leave them: lane i pushes
    input i at `depth` (the factory's is 1: a whole range per unit) on a
    base of 1, held to the range."""
    mods = [1.0] * N_INPUTS
    for i, u in enumerate(bands):
        mods[i] = min(max(1.0 + 2.6 * depth * u, 0.0), 2.6)
    return mods


def gallery(r: Renderer, t: float, n: int) -> Image.Image:
    modes = range(1, len(MODES))
    lw, gap, head = 300, 4, 64
    img = Image.new("RGB", (lw + len(PASSAGES) * (n + gap), head + len(modes) * (n + gap)), BG)
    d = ImageDraw.Draw(img)
    big, font, small = (ImageFont.load_default(size=s) for s in (20, 15, 12))
    d.text((10, 8), "every pattern, silent and driven", fill=INK, font=big)
    d.text((10, 34), "bands as the analyzer reads them; inputs as the factory routes push them "
                     "(depth 1 unless said)",
           fill=DIM, font=small)
    for c, (title, _, _) in enumerate(PASSAGES):
        d.text((lw + c * (n + gap) + 4, head - 18), title, fill=DIM, font=small)
    for row, mode in enumerate(modes):
        y = head + row * (n + gap)
        d.text((10, y + n // 2 - 18), f"{mode}  {MODES[mode].name}", fill=INK, font=font)
        d.text((10, y + n // 2 + 2), MODES[mode].about[:44], fill=DIM, font=small)
        for c, (_, bands, depth) in enumerate(PASSAGES):
            r.bands = bands
            s = ViewState(pattern=mode, pattern_mod=factory_inputs(bands, depth))
            img.paste(Image.fromarray(r.pattern_tile(s, n, t, FID)), (lw + c * (n + gap), y))
    r.bands = ()
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--t", type=float, default=4.0, help="pattern time of the stills, seconds")
    ap.add_argument("--tile", type=int, default=128, help="tile size, px")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = moderngl.create_context(standalone=True)
    r = Renderer(ctx)
    if r.pattern_error:
        sys.exit(f"patterns.glsl does not compile: {r.pattern_error}")
    for mode in range(1, len(MODES)):
        save(mode_sheet(r, mode, args.t, args.tile),
             OUT / f"mode-{mode:02d}-{MODES[mode].name.lower()}.png")
    for k in range(N_INPUTS):
        save(input_sheet(r, k, args.t, args.tile), OUT / f"input-{k}-{INPUTS[k].name.lower()}.png")
    save(gallery(r, args.t, args.tile), OUT / "b3-gallery.png")
    ctx.release()


if __name__ == "__main__":
    main()
