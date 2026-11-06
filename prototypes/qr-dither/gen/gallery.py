"""Build the stills gallery, and decode every file it writes.

Each entry is solved with pyqart -- whose pivot order is adaptive, spending the
code's freedom where the drawing has edges, which is what grows the organic
halo the live solver's fixed orders can only approximate. One solve per
(pose, stroke, version); styles and palettes reuse that matrix.

Verification is on the shipped artefact, not on a model of it: the SVG that
goes in web/gallery/ is rasterised by headless Chrome and decoded by zxing, so
what is checked is the exact file the page serves.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

import polytopes
import robust
import style as sty

from paths import WEB, WORK

# Headless Chrome rasterises each SVG so the thing decoded is the shipped file.
# Nothing else about this prototype is platform-specific, so the lookup is not
# either: set QRD_CHROME to point at any Chromium build.
CHROME_CANDIDATES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def find_chrome():
    env = os.environ.get("QRD_CHROME")
    if env:
        if pathlib.Path(env).exists():
            return env
        sys.exit(f"QRD_CHROME is set to {env!r}, which does not exist.")
    for c in CHROME_CANDIDATES:
        hit = shutil.which(c) or (c if pathlib.Path(c).exists() else None)
        if hit:
            return hit
    sys.exit(
        "Need headless Chrome to verify the SVGs, and none was found.\n"
        "Tried: " + ", ".join(CHROME_CANDIDATES) + "\n"
        "Set QRD_CHROME to a Chromium binary, or install Chrome.")

OUT = WEB / "gallery"
RAST = WORK / "gallery-rast"

RED, INK, PAPER = "#ff2b2b", "#000000", "#ffffff"

# (id, pose, stroke, version, title, blurb, style overrides)
SHAPES = [
    ("tess-nested",  "tess_nested",    2, 12, "Tesseract, cell first",
     "Four nested squares: the w- and z-divisions compose."),
    ("tess-tilt",    "tess_tilt",      2, 12, "Tesseract, turned 45°",
     "The same solid on the diagonal — every edge still lands on a grid line."),
    ("tess-wide",    "tess_wide",      2, 12, "Tesseract, far camera",
     "w 9.0 / z 2.6. The nesting tightens as the camera pulls back."),
    ("tess-deep",    "tess_deep",      2, 12, "Tesseract, near camera",
     "w 4.2 / z 2.2. Strong perspective pushes the inner cell small."),
    ("tess-tiltdeep", "tess_tilt_deep", 2, 12, "Tesseract, turned and near",
     "The diamond with the inner cells spaced wide apart."),
    ("tess-shallow", "tess_shallow",   3, 12, "Tesseract, flattened",
     "w 14 / z 4: the four cells collapse towards two. The minimal reading."),
    ("c16-star",     "c16_star",       5, 12, "16-cell, axis first",
     "The tesseract's dual. Four of its eight vertices project to the origin, "
     "so it reads as a cross inside a diamond. Wants a 5-module stroke: its arms "
     "converge on a point, and anything thinner dissolves into the halo."),
    ("c16-tilt",     "c16_tilt",       2, 12, "16-cell, turned 45°",
     "The same solid as a square with an X — the boldest silhouette here."),
    ("duo48-flat",   "duo48_flat",     2, 12, "4-8 duoprism",
     "A square ring times an octagonal one."),
    ("duo88-flat",   "duo88_flat",     2, 12, "8-8 duoprism",
     "Two octagons multiplied. Octagon edges sit on 45s, so they survive the grid."),
    ("duo88-tilt",   "duo88_tilt",     2, 12, "8-8 duoprism, turned 22.5°",
     "Half a step of rotation and the rings line up vertex to edge."),
    ("c24-tilt",     "c24_tilt",       2, 12, "24-cell",
     "Self-dual, 96 edges \u2014 the densest subject that still reads. A rosette "
     "rather than a silhouette."),
    ("cube-flat",    "cube_flat",      2, 12, "3-cube in the w=0 plane",
     "A plain cube for contrast: square in square, corners joined."),
    ("cube-tilt",    "cube_tilt",      2, 12, "3-cube, turned 45°",
     "The same cube on the diagonal."),
    ("tess-tilt-v15", "tess_tilt",     3, 15, "Tesseract, version 15",
     "77 modules instead of 65. More of the code is free, so the halo is finer "
     "grained \u2014 and every module is smaller for a camera to resolve."),
    ("duo88-heavy",  "duo88_tilt",     3, 12, "8-8 duoprism, heavy stroke",
     "The same octagons at a 3-module stroke: solid rings, almost no interior."),
]

STYLE_POSE = ("c16_tilt", 2, 12)
STYLES = [
    ("square",         "square",        "square",        "Square"),
    ("rounded",        "rounded",       "rounded",       "Rounded"),
    ("extra-rounded",  "extra-rounded", "extra-rounded", "Extra rounded"),
    ("dots",           "dot",           "dot",           "Dots"),
    ("dots-tight",     "dot",           "dot",           "Dots, tight"),
    ("classy",         "rounded",       "square",        "Classy"),
    ("classy-rounded", "rounded",       "rounded",       "Classy rounded"),
]

# (id, pose, stroke, version, dot, title, blurb, fg, fg2, bg)
PALETTES = [
    ("pal-ink",    "tess_tilt_deep", 2, 12, "extra-rounded", "Ink on paper",
     "The safe one. Maximum contrast, every reader's best case.", INK, None, PAPER),
    ("pal-red",    "tess_tilt_deep", 2, 12, "extra-rounded", "Hyperspace red",
     "#ff2b2b on white. Red is dark enough in the luminance channel to binarise.",
     RED, None, PAPER),
    ("pal-grad",   "c16_tilt",       2, 12, "rounded", "Ink to red",
     "A diagonal gradient. The light end is where a reader will struggle first.",
     INK, RED, PAPER),
    ("pal-invert", "c16_tilt",       2, 12, "square", "Inverted",
     "White on black, for the page's own background. Most modern readers invert "
     "happily; some older ones refuse outright.", PAPER, None, INK),
    ("pal-redpap", "duo88_tilt",     2, 12, "dots", "Red dots",
     "Circular modules drop the ink fill fraction, the hardest combination to read.",
     RED, None, PAPER),
    ("pal-plate",  "tess_tilt",      2, 12, "extra-rounded", "Rounded plate",
     "A rounded white plate, for dropping on the black page as a sticker.",
     INK, None, PAPER),
]


def solve(url, pose, stroke, version, cache):
    key = (pose, stroke, version)
    if key in cache:
        return cache[key]
    from pyqart import QArtist
    n = 4 * version + 17
    tdir = WORK / "gallery-targets"
    tdir.mkdir(parents=True, exist_ok=True)
    tgt = tdir / f"{pose}_s{stroke}_v{version}.png"
    polytopes.pose(n, pose, stroke=stroke).save(tgt)
    m = QArtist(url, str(tgt), version=version, mask=None, level=0).as_bool_matrix
    cache[key] = m
    return m


def rasterise(svg_path, png_path, px=10, quiet=4):
    side = 0
    txt = svg_path.read_text()
    vb = txt.split('viewBox="0 0 ', 1)[1].split(" ", 1)[0]
    side = int(float(vb)) * px
    subprocess.run(
        [find_chrome(), "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         "--force-device-scale-factor=1", f"--window-size={side},{side}",
         "--default-background-color=FFFFFFFF", f"--screenshot={png_path}", str(svg_path)],
        check=True, capture_output=True, timeout=90)
    return side


def decode(png_path):
    import zxingcpp
    from PIL import Image
    hits = zxingcpp.read_barcodes(Image.open(png_path).convert("RGB"))
    return hits[0].text if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--px", type=int, default=10, help="px per module when verifying")
    ap.add_argument("--keep", action="store_true", help="keep the rasterised PNGs")
    args = ap.parse_args()
    base = args.url.rstrip("#")

    chrome = find_chrome()            # fail now, not after the first solve
    print(f"verifying with {chrome}")

    OUT.mkdir(parents=True, exist_ok=True)
    RAST.mkdir(parents=True, exist_ok=True)
    cache, items, bad = {}, [], []

    def emit(ident, pose, stroke, version, title, blurb, section, **kw):
        m = solve(args.url, pose, stroke, version, cache)
        svg = sty.to_svg(m, **kw)
        p = OUT / f"{ident}.svg"
        p.write_text(svg, encoding="utf-8")
        png = RAST / f"{ident}.png"
        side = rasterise(p, png, px=args.px)
        got = decode(png)
        ok = bool(got) and got.split("#", 1)[0] == base
        n = len(m)
        # measured on the rasterised SVG, so the dot style is part of the answer
        rb = robust.measure(png, n, base) if ok else {"min_ppm": None, "blur": 0.0, "flash": 0.0}
        items.append({"id": ident, "file": f"gallery/{ident}.svg", "title": title,
                      "note": blurb, "section": section, "modules": n,
                      "bytes": len(svg), "decodes": ok,
                      "dark": kw.get("bg", "#ffffff").lower() in ("#000000", "#000"),
                      "pose": pose, "stroke": stroke, "version": version,
                      "dot": kw.get("dot", "square"),
                      "min_ppm": rb["min_ppm"], "blur": rb["blur"], "flash": rb["flash"],
                      "matrix": robust.pack(m)})
        if not ok:
            bad.append((ident, got))
        print(f"  {ident:16} {n}x{n}  {len(svg):>6}B  "
              f"{'scans' if ok else 'NO SCAN':8} min {str(rb['min_ppm']):>4} px/mod  "
              f"blur {rb['blur']:.2f}  flash {rb['flash']:.1f}")

    print("\nshapes")
    for ident, pose, stroke, ver, title, blurb in SHAPES:
        emit(ident, pose, stroke, ver, title, blurb, "shapes")

    print("\nstyles")
    pose, stroke, ver = STYLE_POSE
    for dot, frame, core, label in STYLES:
        emit(f"sty-{dot}", pose, stroke, ver, label,
             f"dot {dot} · eye {frame}/{core}", "styles",
             dot=dot, eye_frame=frame, eye_core=core)

    print("\npalettes")
    for ident, pose, stroke, ver, dot, title, blurb, fg, fg2, bg in PALETTES:
        emit(ident, pose, stroke, ver, title, blurb, "palettes",
             dot=dot, eye_frame="rounded", eye_core="rounded",
             fg=fg, fg2=fg2, bg=bg,
             plate_radius=6 if ident == "pal-plate" else 0)

    # the controls: boring codes for the same destination, measured the same way,
    # so every verdict on this page has something to be a verdict against
    print("\nbaselines")
    baselines = [robust.plain(base, e) for e in ("L", "M", "Q", "H")]
    for b in baselines:
        print(f"  plain ECC {b['ecc']:2} v{b['version']:<3} {b['modules']}x{b['modules']}"
              f"  min {str(b['min_ppm']):>4} px/mod  blur {b['blur']:.2f}  flash {b['flash']:.1f}")

    (OUT / "manifest.json").write_text(
        json.dumps({"url": base, "items": items, "baselines": baselines,
                    "matrix_encoding": "base64, row-major, MSB first, bit i = y*n + x"},
                   indent=1), encoding="utf-8")

    if not args.keep:
        shutil.rmtree(RAST, ignore_errors=True)

    good = sum(1 for i in items if i["decodes"])
    print(f"\n{good}/{len(items)} rasterised and decoded back to {base}")
    for ident, got in bad:
        print(f"  FAILED {ident}: {got!r}")
    print(f"gallery: {OUT}")
    return 0 if good == len(items) else 1


if __name__ == "__main__":
    raise SystemExit(main())
