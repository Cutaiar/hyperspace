# -*- coding: utf-8 -*-
"""One-of-one codes: a pose, and a constant pinned into the fragment.

The gallery's stills vary the drawing. These vary the *payload* as well: each
edition pairs one polytope pose with one irrational constant, pinned into the
leading digits of the numeric filler, so the fragment opens with the number and
no other code in the series carries both.

    uv run --with pyqart --with pillow --with numpy --with mpmath \\
      --with segno --with zxing-cpp python3 gen/editions.py \\
      --url https://hyperspace.cutaiar.io

Nothing here is trusted on looks: every SVG is rasterised by headless Chrome,
decoded by zxing, and the decoded fragment is checked to actually begin with
the digits that were asked for. Exit code is non-zero unless all of them do.

Output lands in work/editions/ rather than app/public/data, because no view
reads these yet -- they are a series, not a gallery section.

WHY THIS PATH AND NOT GALLERY.PY
pyqart cannot pin bits; only gen/basis.py's affine form has a `forced` map to
extend. That costs about 3.5 points of drawing fidelity, and measurement says
the cost is the 511 cap rather than the pinning: basis.py holds every 10-bit
numeric group under 512 so validity is structural and the live solver never
retries, which spends 269 modules. Pinning 24 digits spends 72. The cap is the
live path's price, paid here for no benefit -- lifting it for stills is the
obvious next move and is not done.
"""
import argparse
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

import polytopes
import robust
import style as sty
from basis import Affine
from gallery import find_chrome
from paths import WORK

OUT = WORK / "editions"

# Measured over all eight masks and five pivot orders on tess_tilt: mask 5 and
# the low-discrepancy "even" order came out best, and "even" spreads what it
# cannot control as a uniform sparkle instead of as line artefacts.
ORDER, MASK = "even", 5

# Each constant is computed, never recalled. mpmath gives as many digits as the
# filler could possibly hold.
CONSTANTS = {
    "pi":     ("π",  "Pi",             lambda mp: mp.pi),
    "tau":    ("τ",  "Tau",            lambda mp: 2 * mp.pi),
    "e":      ("ℯ",  "Euler's number", lambda mp: mp.e),
    "phi":    ("φ",  "Golden ratio",   lambda mp: mp.phi),
    "sqrt2":  ("√2", "Pythagoras'",    lambda mp: mp.sqrt(2)),
    "apery":  ("ζ(3)", "Apéry's",      lambda mp: mp.apery),
    "gamma":  ("γ",  "Euler–Mascheroni", lambda mp: mp.euler),
    "catalan": ("G",      "Catalan's",      lambda mp: mp.catalan),
}

# (edition, pose, stroke, constant, why this pairing and not another)
EDITIONS = [
    ("I",   "tess_tilt",  2, "pi",     "the circle constant on the hypercube"),
    ("II",  "c16_tilt",   2, "phi",    "the golden ratio on the tesseract's dual"),
    ("III", "c24_tilt",   2, "apery",  "96 edges, and the constant nobody expected to be irrational"),
    ("IV",  "duo88_tilt", 2, "tau",    "two octagonal rings, one full turn"),
    ("V",   "cube_tilt",  2, "sqrt2",  "the first irrational, on the only 3-D solid here"),
]


def digits_of(key, n):
    """The constant's digits, decimal point dropped, computed to order."""
    from mpmath import mp
    mp.dps = n + 20
    v = mp.nstr(CONSTANTS[key][2](mp), n + 10, strip_zeros=False)
    return "".join(ch for ch in v if ch.isdigit())[:n]


def rasterise(svg, png, units, chrome, px=10):
    side = units * px
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         "--force-device-scale-factor=1", f"--window-size={side},{side}",
         "--default-background-color=FFFFFFFF", f"--screenshot={png}", str(svg)],
        check=True, capture_output=True, timeout=180)


def decode(png):
    import zxingcpp
    hits = zxingcpp.read_barcodes(Image.open(png).convert("RGB"))
    return hits[0].text if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--version", type=int, default=12)
    ap.add_argument("--digits", type=int, default=24,
                    help="digits of the constant to pin; 3 modules each, "
                         "rounded down to whole 3-digit groups")
    ap.add_argument("--keep", action="store_true", help="keep the rasterised PNGs")
    args = ap.parse_args()
    url = args.url.rstrip("#")

    chrome = find_chrome()          # fail now, not after the first solve
    OUT.mkdir(parents=True, exist_ok=True)
    n = 4 * args.version + 17

    base = Affine(url, version=args.version, mask=MASK, level=0, order=ORDER)
    base_free = sum(len([p for p in b["pivots"] if p not in b["forced"]])
                    for b in base.blocks)
    print(f"version {args.version} · {n}x{n} · order {ORDER} · mask {MASK}")
    print(f"the filler holds {base.numbers_count} digits; "
          f"{base_free} modules are free to draw with\n")
    print(f"{'ed':4} {'pose':12} {'const':8} {'pinned':>7} {'cost':>5} "
          f"{'drawn':>7} {'min ppm':>8} {'ok':>4}  fragment")
    print("-" * 100)

    bad = []
    for ed, pose, stroke, key, why in EDITIONS:
        glyph, name, _ = CONSTANTS[key]
        pins = digits_of(key, args.digits)
        aff = Affine(url, version=args.version, mask=MASK, level=0,
                     order=ORDER, pin_digits=pins)
        free = sum(len([p for p in b["pivots"] if p not in b["forced"]])
                   for b in aff.blocks)

        px = np.array(polytopes.pose(n, pose, stroke=stroke)) < 128
        want = {(x, y): bool(px[y][x]) for y in range(n) for x in range(n)}
        m, _ = aff.solve(want)
        drawn = 100 * sum(1 for (x, y), v in want.items() if m[y][x] == v) / (n * n)

        svg = OUT / f"ed-{ed}-{key}.svg"
        svg.write_text(sty.to_svg(m, dot="extra-rounded", eye_frame="rounded",
                                  eye_core="rounded"), encoding="utf-8")
        png = OUT / f"ed-{ed}-{key}.png"
        rasterise(svg, png, n + 8, chrome)
        got = decode(png)

        url_ok = bool(got) and got.split("#", 1)[0] == url
        frag = got.split("#", 1)[1] if got and "#" in got else ""
        # the whole point: the digits asked for are the digits that came back
        pin_ok = frag.startswith(aff.pin_digits)
        ok = url_ok and pin_ok
        rb = robust.measure(png, n, url) if ok else {"min_ppm": None}
        if not ok:
            bad.append(f"{ed} ({key}): url {url_ok}, pinned prefix {pin_ok}, got {frag[:30]!r}")

        print(f"{ed:4} {pose:12} {glyph:8} {len(aff.pin_digits):>7} "
              f"{base_free - free:>5} {drawn:>6.1f}% {str(rb['min_ppm']):>8} "
              f"{'yes' if ok else 'NO':>4}  #{frag[:24]}…")
        print(f"     {why}")

    if not args.keep:
        for p in OUT.glob("*.png"):
            p.unlink()

    print(f"\n{len(EDITIONS) - len(bad)}/{len(EDITIONS)} rasterised, decoded, and "
          f"carrying the digits they were given")
    for b in bad:
        print(f"  FAILED {b}")
    print(f"editions: {OUT}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
