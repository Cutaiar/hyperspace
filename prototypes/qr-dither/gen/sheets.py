"""Decode and measure the sticker sheets the exporters wrote.

`cd app && npm run check` writes a set of sheets to work/sheets/ plus an
index.json saying where every sticker sits, in millimetres, taken straight from
lib/sheet.ts so the geometry is single-sourced. This script is the independent
half: it rasterises each file with a renderer that had nothing to do with
writing it -- headless Chrome for the SVG, poppler for the PDF -- decodes every
sticker on the page, and then measures one sticker of each code with
gen/robust.py.

That second step is the point. Styling cannot change what a code says; it very
much changes whether a camera reads it, and the gallery already measures that
on a still: `dots-tight` needs 3 camera pixels per module where `square` needs
1. The same question has to be asked of a styled sheet at a physical size,
because the answer there is what decides whether 44 mm is enough.

    cd app && npm run check
    uv run --with pillow --with numpy --with segno --with zxing-cpp \\
      python3 gen/sheets.py --url https://hyperspace.cutaiar.io

Needs headless Chrome, as gen/gallery.py does, and one system package the rest
of this prototype does not: poppler, for `pdftoppm` (`brew install poppler`,
`apt-get install poppler-utils`). mupdf's `mutool` works too, and failing both
it will use pypdfium2 if the uv command supplies it -- though that is Chrome's
own PDF engine and the SVG half is already Chrome, so it is a fallback and not
a peer. QRD_PDFRAST overrides the lookup, as QRD_CHROME does for the browser.

Exit code is non-zero unless every sticker on every sheet, in both formats,
decoded back to the URL.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

import robust
from gallery import find_chrome
from paths import WORK

SHEETS = WORK / "sheets"

# the quiet zone the generators use, in modules; lib/manifest.ts's QUIET
QUIET = 4

# Chrome lays an SVG sized in millimetres out at the CSS reference of 96 dpi,
# so the window is in CSS pixels and the scale factor is what buys resolution.
# 4x is 384 dpi, comfortably past the 300 a printer wants and past the 3 camera
# pixels per module that dots-tight needs at 0.6 mm a module.
CSS_PER_MM = 96 / 25.4
SVG_SCALE = 4
# The PDF is rasterised at the resolution that comes out of the SVG side, so
# the two columns of the robustness table are comparing the two files rather
# than two rasterisers' settings. 384 dpi is also comfortably past the 300 a
# printer asks for.
PDF_DPI = round(CSS_PER_MM * SVG_SCALE * 25.4)


def shoot_svg(path, png, chrome):
    import re
    txt = path.read_text()
    w = float(re.search(r'width="([\d.]+)mm"', txt).group(1))
    h = float(re.search(r'height="([\d.]+)mm"', txt).group(1))
    cw, ch = int(w * CSS_PER_MM) + 1, int(h * CSS_PER_MM) + 1
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         f"--force-device-scale-factor={SVG_SCALE}", f"--window-size={cw},{ch}",
         "--default-background-color=FFFFFFFF", f"--screenshot={png}", str(path)],
        check=True, capture_output=True, timeout=180)
    return CSS_PER_MM * SVG_SCALE          # px per mm


# Rasterising the PDF is the independent half of the check, so it wants a
# renderer that had nothing to do with writing the file. poppler is the first
# choice and mupdf the second; pdfium is a fallback rather than a peer, because
# it is Chrome's own PDF engine and the SVG side is already Chrome.
#
# Same shape as gallery.py's Chrome lookup, and the same reason: nothing about
# this prototype should be machine-specific, so the lookup is not either. Set
# QRD_PDFRAST to any of these binaries to override it.
def _poppler_argv(tool, path, stem):
    return [tool, "-r", str(PDF_DPI), "-png", "-singlefile", str(path), stem]


def _mutool_argv(tool, path, stem):
    return [tool, "draw", "-r", str(PDF_DPI), "-o", f"{stem}.png", str(path)]


PDF_CANDIDATES = [
    ("pdftoppm", _poppler_argv),            # poppler, splash backend
    ("pdftocairo", _poppler_argv),          # poppler, cairo backend
    ("mutool", _mutool_argv),               # mupdf
]


def find_pdf_rasteriser():
    """(label, callable) that turns a PDF into a PNG at PDF_DPI."""
    env = os.environ.get("QRD_PDFRAST")
    if env:
        if not (shutil.which(env) or pathlib.Path(env).exists()):
            sys.exit(f"QRD_PDFRAST is set to {env!r}, which does not exist.")
        argv = dict(PDF_CANDIDATES).get(pathlib.Path(env).name.split(".")[0], _poppler_argv)
        return env, lambda path, stem: _run(argv(env, path, stem))
    for name, argv in PDF_CANDIDATES:
        hit = shutil.which(name)
        if hit:
            return hit, lambda path, stem, h=hit, a=argv: _run(a(h, path, stem))
    try:
        import pypdfium2                     # noqa: F401
    except ImportError:
        sys.exit(
            "Need something to rasterise the PDFs, and none was found.\n"
            "Tried: " + ", ".join(n for n, _ in PDF_CANDIDATES) + ", and pypdfium2.\n"
            "  macOS:  brew install poppler\n"
            "  Debian: sudo apt-get install poppler-utils\n"
            "Or add --with pypdfium2 to the uv command, which needs no system\n"
            "package -- but it is Chrome's PDF engine and the SVG side is already\n"
            "Chrome, so prefer poppler where the independence matters.\n"
            "QRD_PDFRAST overrides the lookup.")
    return "pypdfium2 (Chrome's own PDF engine -- less independent)", _pdfium


def _run(argv):
    subprocess.run(argv, check=True, capture_output=True, timeout=180)


def _pdfium(path, stem):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(path))
    doc[0].render(scale=PDF_DPI / 72).to_pil().save(f"{stem}.png")


def shoot_pdf(path, png, rasterise):
    stem = str(png)[:-4] if str(png).endswith(".png") else str(png)
    rasterise(path, stem)
    return PDF_DPI / 25.4                  # px per mm


def decoded(img, url):
    import zxingcpp
    hits = zxingcpp.read_barcodes(img.convert("RGB"))
    return sum(1 for h in hits if h.text.split("#", 1)[0] == url), len(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--keep", action="store_true", help="keep the rasterised PNGs")
    ap.add_argument("--only", default="", help="one sheet name, for a quick loop")
    args = ap.parse_args()
    url = args.url.rstrip("#")

    from PIL import Image

    index = SHEETS / "index.json"
    if not index.exists():
        raise SystemExit(f"no {index}. Run `cd app && npm run check` first.")
    idx = json.loads(index.read_text())
    if idx["url"].rstrip("#") != url:
        raise SystemExit(f"the sheets were written for {idx['url']}, not {url}")

    chrome = find_chrome()                # fail now, not after the first shot
    pdf_label, pdf_rasterise = find_pdf_rasteriser()
    print(f"SVG via {chrome}\nPDF via {pdf_label}\n")

    rast = SHEETS / "rast"
    rast.mkdir(parents=True, exist_ok=True)
    bad, rows, measured = [], [], []

    for sh in idx["sheets"]:
        if args.only and sh["name"] != args.only:
            continue
        want = sh["expect"]
        for kind in ("svg", "pdf"):
            src = SHEETS / f"{sh['name']}.{kind}"
            png = rast / f"{sh['name']}-{kind}.png"
            ppmm = (shoot_svg(src, png, chrome) if kind == "svg"
                    else shoot_pdf(src, png, pdf_rasterise))
            img = Image.open(png)
            good, total = decoded(img, url)
            rows.append((sh["name"], kind, sh["mode"], want, good, total,
                         "styled" if sh["styled"] else "plain"))
            if good != want:
                bad.append(f"{sh['name']}.{kind}: {good}/{want} decoded "
                           f"({total} barcodes found)")
            first = sh["placed"][0]
            pitch = first["w"] / (first["modules"] + 2 * QUIET)
            print(f"  {sh['name']:20} {kind}  {good:>2}/{want:<2} decoded"
                  f"   {img.size[0]}x{img.size[1]} px"
                  f"   {ppmm * pitch:.1f} px/module")

            # Measure one sticker of each distinct code, cropped out of the
            # page raster -- the shipped file, not a model of it.
            #
            # The crop is the whole cut, quiet zone included, which is what
            # gen/gallery.py hands robust.measure for a still, so the numbers
            # below are comparable with the manifest's. robust.core() trims a
            # paper quiet zone back off; on an inverted code the quiet zone is
            # ink, so it survives and that code is measured against 73 modules
            # rather than 65 -- about 12% conservative, and the same 12% the
            # manifest's own figure for pal-invert carries. Cropping tighter
            # instead would pad an inverted code with white and destroy the
            # quiet zone it needs.
            seen = set()
            for p in sh["placed"]:
                if p["id"] in seen:
                    continue
                seen.add(p["id"])
                box = tuple(int(round(v * ppmm)) for v in
                            (p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"]))
                r = robust.measure(img.crop(box), p["modules"], url)
                measured.append((f"{sh['name']}.{kind}", p["id"], p["modules"],
                                 p["w"], r))
                if r["min_ppm"] is None:
                    bad.append(f"{sh['name']}.{kind}: {p['id']} would not decode "
                               f"cropped out on its own")
        if not args.keep:
            for kind in ("svg", "pdf"):
                (rast / f"{sh['name']}-{kind}.png").unlink(missing_ok=True)

    print(f"\n{'sheet.format':28} {'code':20} {'size':>8} {'min px/mod':>11} "
          f"{'blur':>6} {'flash':>6}")
    print("-" * 86)
    for name, ident, n, w, r in measured:
        print(f"{name:28} {ident:20} {w:>5.0f} mm {str(r['min_ppm'] or 'FAIL'):>11} "
              f"{r['blur']:>6.2f} {r['flash']:>6.1f}")
    print("\nmin px/mod is measured on a sticker cropped out of the rasterised sheet,")
    print("so it is the exported artefact being judged and not the matrix. blur is a")
    print("Gaussian sigma in MODULES; see gen/robust.py.")

    total_good = sum(r[4] for r in rows)
    total_want = sum(r[3] for r in rows)
    print(f"\n{total_good}/{total_want} stickers decoded across "
          f"{len(rows)} files back to {url}")
    for b in bad:
        print(f"  FAILED {b}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
