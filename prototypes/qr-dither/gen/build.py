"""Generate QArt hypercube codes and verify every one of them actually decodes."""
import argparse
import itertools
import pathlib
import sys

from PIL import Image

import tesseract

from paths import WEB, WORK

OUT = WORK / "stills"


def decode(path):
    """Return the decoded payload, trying zxing-cpp then OpenCV."""
    results = {}
    try:
        import zxingcpp
        img = Image.open(path).convert("RGB")
        hits = zxingcpp.read_barcodes(img)
        results["zxing"] = hits[0].text if hits else None
    except Exception as e:
        results["zxing"] = f"<error: {type(e).__name__}>"
    try:
        import cv2
        import numpy as np
        arr = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        txt, pts, _ = cv2.QRCodeDetector().detectAndDecode(arr)
        results["opencv"] = txt or None
    except Exception as e:
        results["opencv"] = f"<error: {type(e).__name__}>"
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="plain URL; pyqart appends the # fragment itself")
    ap.add_argument("--versions", default="10,12,15", help="QR versions to try")
    ap.add_argument("--strokes", default="2,3,4", help="edge thickness in modules")
    ap.add_argument("--presets", default=",".join(tesseract.PRESETS))
    ap.add_argument("--point-width", type=int, default=12, help="px per module in the PNG")
    args = ap.parse_args()

    from pyqart import QArtist, QrImagePrinter

    OUT.mkdir(exist_ok=True)
    (OUT / "targets").mkdir(exist_ok=True)

    versions = [int(v) for v in args.versions.split(",")]
    strokes = [int(s) for s in args.strokes.split(",")]
    presets = [p.strip() for p in args.presets.split(",")]

    rows = []
    for version, stroke, name in itertools.product(versions, strokes, presets):
        n = 4 * version + 17
        tag = f"v{version}_{name}_s{stroke}"
        target = OUT / "targets" / f"{tag}.png"
        tesseract.render(n, stroke=stroke, **tesseract.PRESETS[name]).save(target)

        out = OUT / f"qart_{tag}.png"
        try:
            # level 0 = L: QArt trades error correction for free bits to draw with
            artist = QArtist(args.url, str(target), version=version, mask=None, level=0)
            QrImagePrinter.print(artist, str(out), point_width=args.point_width,
                                 border_width=args.point_width * 4)
        except Exception as e:
            rows.append((tag, n, "BUILD FAILED", f"{type(e).__name__}: {e}"))
            continue

        d = decode(out)
        # pyqart appends "#<filler>" itself; everything after the first "#" is a
        # fragment the browser discards, so the destination is the part before it.
        base = args.url.rstrip("#")
        def lands_right(p):
            return isinstance(p, str) and p.split("#", 1)[0] == base
        ok = lands_right(d["zxing"]) or lands_right(d["opencv"])
        payload = d["zxing"] or d["opencv"]
        rows.append((tag, n, "scans" if ok else "NO SCAN",
                     repr(payload)[:58] if payload else f"zxing={d['zxing']!r} cv={d['opencv']!r}"))

    print(f"\n{'variant':26} {'mods':>5}  {'verdict':10} payload")
    print("-" * 104)
    for tag, n, verdict, payload in rows:
        print(f"{tag:26} {n:>3}x{n:<3} {verdict:10} {payload}")
    good = sum(1 for r in rows if r[2] == "scans")
    print(f"\n{good}/{len(rows)} decoded back to the exact URL")
    print(f"images: {OUT}")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
