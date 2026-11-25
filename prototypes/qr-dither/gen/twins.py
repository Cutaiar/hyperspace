"""Is lib/style.ts really the twin of gen/style.py?

Not a question to answer by reading both. `cd app && npm run twins` draws all
29 gallery stills a second time through the TypeScript renderer, in the same
viewBox -- one unit to a module -- and this shoots each pair with the same
headless Chrome and compares them pixel for pixel.

    cd app && npm run twins
    uv run --with pillow --with numpy python3 gen/twins.py

What it should say, and did when the port landed: every style whose modules are
rectangles or rounded cells is *bit identical*. The three circular ones differ
slightly, because style.py emits a <circle> and the port emits the same circle
as four arcs, and Chrome rounds the edge pixel of a primitive differently from
the edge pixel of a path -- at 10 px/module `sty-dots` disagreed on exactly
3788 pixels, four per circular module, its four tangent points.

The test is not how many pixels differ but *where*. A disagreement one pixel
deep along a shape's own boundary is the rasteriser choosing a rim pixel. A
disagreement anywhere else is the geometry being wrong, however few pixels it
is. So every differing pixel has to lie in the one-pixel band around an edge of
the Python render, at both a coarse and a fine resolution -- which also rules
out the one failure mode a share-of-pixels threshold would hide, a module in
the wrong place that happens to be small.

Its sensitivity, measured by nudging the TypeScript render and watching: at the
fine pass's 40 px/module, a 0.1-module offset puts 123,000 pixels off the rim
and fails loudly, while a 0.02-module offset is under a pixel and passes. So
this says the two renderers agree to about a fortieth of a module -- 0.015 mm
on a 44 mm sticker -- and not that they agree exactly.
"""
import argparse
import json
import pathlib
import subprocess

import numpy as np
from PIL import Image

from gallery import find_chrome
from paths import WEB, WORK

GAL = WEB / "gallery"
TWINS = WORK / "twins"
RAST = TWINS / "rast"

# Styles whose modules are circles, and so the only ones allowed to differ at
# all. Everything else has to come out bit identical.
ROUND = {"dots", "dots-tight"}
FINE_PX = 40


def shoot(svg, png, side_px, chrome):
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         "--force-device-scale-factor=1", f"--window-size={side_px},{side_px}",
         "--default-background-color=FFFFFFFF", f"--screenshot={png}", str(svg)],
        check=True, capture_output=True, timeout=300)
    return np.asarray(Image.open(png).convert("L"), dtype=np.int16)


def masks(a, b):
    """The two renders as ink/paper, cropped to their common size. A pixel on
    opposite sides of the binariser's midpoint is the only difference a decoder
    could ever see."""
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    return a[:h, :w] < 128, b[:h, :w] < 128


def rim(mask):
    """Pixels with a 4-neighbour on the other side of a boundary: the one-pixel
    band an anti-aliased edge is allowed to wander within."""
    out = np.zeros_like(mask)
    v = mask[:-1, :] != mask[1:, :]
    out[:-1, :] |= v
    out[1:, :] |= v
    h = mask[:, :-1] != mask[:, 1:]
    out[:, :-1] |= h
    out[:, 1:] |= h
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--px", type=int, default=10, help="coarse pass, px per module")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    if not TWINS.exists():
        raise SystemExit("no work/twins/. Run `cd app && npm run twins` first.")
    chrome = find_chrome()
    RAST.mkdir(parents=True, exist_ok=True)
    man = json.loads((GAL / "manifest.json").read_text())

    bad = []
    print(f"{'code':20} {'dot':15} {'differs':>9} {'off the rim':>13}")
    print("-" * 62)
    for it in man["items"]:
        side = it["modules"] + 8
        worst_share, off_rim = 0.0, 0
        for px in (args.px, FINE_PX):
            n = side * px
            a = shoot(GAL / f"{it['id']}.svg", RAST / f"{it['id']}-py.png", n, chrome)
            b = shoot(TWINS / f"{it['id']}.svg", RAST / f"{it['id']}-ts.png", n, chrome)
            pm, tm = masks(a, b)
            diff = pm != tm
            worst_share = max(worst_share, diff.mean() * 100)
            off_rim += int((diff & ~rim(pm)).sum())
        print(f"{it['id']:20} {it['dot']:15} {worst_share:8.4f}% {off_rim:>13}")
        if it["dot"] not in ROUND and worst_share > 0:
            bad.append(f"{it['id']}: differs at all, and its modules are not circles")
        elif off_rim:
            bad.append(f"{it['id']}: {off_rim} differing pixels are not on an edge, "
                       f"so this is geometry and not anti-aliasing")

    if not args.keep:
        for p in RAST.glob("*.png"):
            p.unlink()
        RAST.rmdir()

    print(f"\n{len(man['items']) - len(bad)}/{len(man['items'])} agree with gen/style.py")
    for b in bad:
        print(f"  FAILED {b}")
    print("\nA circular module is a <circle> in Python and four arcs in TypeScript, so its")
    print("rim pixel is the rasteriser's choice, not the geometry's -- those codes may")
    print("differ, but only within one pixel of an edge. Every other style has to be bit")
    print("identical, and anything else is a bug in the port.")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
