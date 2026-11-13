"""Prove the affine form reproduces valid, decodable QArt codes in Python,
before any of it is ported to the browser."""
import math, sys, time
import numpy as np
from PIL import Image
import zxingcpp

import tesseract
from basis import Affine

URL = "https://www.instagram.com/hyperspace.av/"


def decode(m):
    n = len(m)
    a = np.array(m, bool)
    pad = np.ones((n + 8, n + 8), bool) * False
    pad[4:4 + n, 4:4 + n] = a
    img = Image.fromarray(np.where(pad, 0, 255).astype("uint8")).resize(
        ((n + 8) * 6, (n + 8) * 6), Image.NEAREST).convert("RGB")
    hit = zxingcpp.read_barcodes(img)
    return hit[0].text if hit else None


t0 = time.time()
aff = Affine(URL, version=12, mask=0, level=0)
build = time.time() - t0
free = sum(len(b["pivots"]) for b in aff.blocks)
forced = sum(len(b["forced"]) for b in aff.blocks)
print(f"factorised in {build:.1f}s   modules {aff.n}x{aff.n}   "
      f"pivots {free} (of which {forced} pinned to zero for numeric legality)")
print(f"drawable modules: {free - forced} of {aff.n*aff.n}\n")

ok = 0
trials = 12
t0 = time.time()
for i in range(trials):
    theta = (math.pi / 2) * i / trials
    tgt = tesseract.render(aff.n, angles={(0, 3): theta}, stroke=3,
                           w_dist=7.0, z_dist=3.0, margin=0.08)
    px = np.array(tgt) < 128
    want = {(x, y): bool(px[y][x]) for y in range(aff.n) for x in range(aff.n)}
    m, _ = aff.solve(want)
    got = decode(m)
    good = bool(got) and got.split("#", 1)[0] == URL
    ok += good
    # how faithful is the drawing where we had freedom?
    agree = sum(1 for (x, y), v in want.items() if m[y][x] == v)
    print(f"  xw={math.degrees(theta):5.1f}deg  {'ok ' if good else 'FAIL'}  "
          f"pixels matched {100*agree/(aff.n*aff.n):5.1f}%")
solve_ms = (time.time() - t0) / trials * 1000
print(f"\n{ok}/{trials} decode to {URL}")
print(f"mean solve {solve_ms:.0f} ms/frame in Python (JS with typed arrays will be far faster)")
sys.exit(0 if ok == trials else 1)
