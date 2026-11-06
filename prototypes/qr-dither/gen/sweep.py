"""Precompute a rotation sweep of QArt tesseracts and verify every frame.

A hypercube rotated 90 degrees in the XW plane maps its own vertex set onto
itself, so the projection has period 90 degrees: FRAMES steps over that quarter
turn is a seamless loop.  The second axis is YW, following hyperspace's own
drag mapping (x -> XW, y -> YW), and loops the same way.

The mask is pinned (rather than pyqart's default random pick) so the function
patterns stay put from frame to frame instead of strobing.
"""
import argparse
import json
import math
import pathlib

import numpy as np
from PIL import Image

import tesseract

from paths import LEGACY as WEB, WORK

OUT = WEB


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--frames", type=int, default=36)
    ap.add_argument("--frames2", type=int, default=1,
                    help="steps of YW rotation; the second drag axis")
    ap.add_argument("--version", type=int, default=12)
    ap.add_argument("--stroke", type=int, default=3)
    ap.add_argument("--mask", type=int, default=0)
    ap.add_argument("--w-dist", type=float, default=7.0)
    ap.add_argument("--z-dist", type=float, default=3.0)
    ap.add_argument("--margin", type=float, default=0.08)
    ap.add_argument("--tag", default="sweep")
    args = ap.parse_args()

    from pyqart import QArtist
    import zxingcpp

    n = 4 * args.version + 17
    base = args.url.rstrip("#")
    tmp = WORK / "sweep"
    tmp.mkdir(parents=True, exist_ok=True)

    # one row per ZW step, one column per XW step
    cols, rows = args.frames, args.frames2
    total = cols * rows
    sheet = Image.new("L", (cols * n, rows * n), 255)
    ghost = Image.new("L", (cols * n, rows * n), 255)

    span = tesseract.max_span(args.w_dist, args.z_dist)
    print(f'fixed span {span:.4f} (shape will not resize as it folds)', flush=True)

    bad = []
    for k in range(total):
        i, j = k % cols, k // cols
        theta = (math.pi / 2) * i / cols                 # quarter turn == full loop
        phi = (math.pi / 2) * j / rows if rows > 1 else 0.0
        tgt = tesseract.render(
            # planes match hyperspace's own mapping: x -> XW, y -> YW
            n, angles={(0, 3): theta, (1, 3): phi}, stroke=args.stroke,
            w_dist=args.w_dist, z_dist=args.z_dist, margin=args.margin, span=span)
        tp = tmp / f"{k:04d}.png"
        tgt.save(tp)

        art = QArtist(base, str(tp), version=args.version, mask=args.mask, level=0)
        m = np.array(art.as_bool_matrix, bool)

        px = 6
        img = Image.fromarray(np.where(m, 0, 255).astype("uint8"))
        pad = Image.new("L", (n + 8, n + 8), 255)
        pad.paste(img, (4, 4))
        probe = pad.resize(((n + 8) * px, (n + 8) * px), Image.NEAREST).convert("RGB")
        hit = zxingcpp.read_barcodes(probe)
        got = hit[0].text if hit else None
        if not (got and got.split("#", 1)[0] == base):
            bad.append((k, round(math.degrees(theta), 1), round(math.degrees(phi), 1), got))

        x, y = i * n, j * n
        sheet.paste(img, (x, y))
        ghost.paste(tgt, (x, y))
        print(f"frame {k:4d}/{total}  xw={math.degrees(theta):5.1f} yw={math.degrees(phi):5.1f}  "
              f"{'ok' if not bad or bad[-1][0] != k else 'FAIL'}", flush=True)

    sheet.save(OUT / f"{args.tag}.png")
    ghost.save(OUT / f"{args.tag}-ghost.png")
    meta = {"url": base, "frames": cols, "frames2": rows, "total": total,
            "modules": n, "cols": cols, "rows": rows, "version": args.version,
            "mask": args.mask, "stroke": args.stroke, "quiet": 4,
            "verified": total - len(bad)}
    (OUT / f"{args.tag}.json").write_text(json.dumps(meta, indent=2))

    print(f"\n{total - len(bad)}/{total} frames decode to {base}")
    if bad:
        print("FAILED frames:", bad[:10])
    print("sheet:", OUT / f"{args.tag}.png")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
