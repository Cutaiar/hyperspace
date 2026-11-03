"""Emit a QArt code as SVG, in the shape hyperspace-contact expects.

No width/height so the page can scale it, a white plate behind the modules so it
scans on the black page, and horizontal runs merged into single rects to keep
the file small.
"""
import argparse
import pathlib

import tesseract

from paths import WEB, WORK


def matrix(url, img_path, version, level=0, mask=None):
    from pyqart import QArtist
    art = QArtist(url, str(img_path), version=version, mask=mask, level=level)
    return art.as_bool_matrix  # property, not a method


def to_svg(m, quiet=4, fg="#000000", bg="#ffffff", plate_radius=0):
    n = len(m)
    side = n + 2 * quiet
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" '
        f'shape-rendering="crispEdges" role="img">',
    ]
    if bg:
        r = f' rx="{plate_radius}"' if plate_radius else ""
        out.append(f'<rect width="{side}" height="{side}" fill="{bg}"{r}/>')
    out.append(f'<g fill="{fg}">')
    for y, row in enumerate(m):
        x = 0
        while x < n:
            if row[x]:
                run = 1
                while x + run < n and row[x + run]:
                    run += 1
                out.append(f'<rect x="{x + quiet}" y="{y + quiet}" width="{run}" height="1"/>')
                x += run
            else:
                x += 1
    out += ["</g>", "</svg>"]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--preset", default="nested_tilt")
    ap.add_argument("--version", type=int, default=12)
    ap.add_argument("--stroke", type=int, default=3)
    ap.add_argument("--quiet", type=int, default=4)
    ap.add_argument("--fg", default="#000000")
    ap.add_argument("--bg", default="#ffffff")
    ap.add_argument("--radius", type=float, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    n = 4 * args.version + 17
    here = WORK / "svg"
    here.mkdir(parents=True, exist_ok=True)
    tgt = here / f"_svg_{args.preset}_v{args.version}_s{args.stroke}.png"
    tesseract.render(n, stroke=args.stroke, **tesseract.PRESETS[args.preset]).save(tgt)

    m = matrix(args.url, tgt, args.version)
    svg = to_svg(m, quiet=args.quiet, fg=args.fg, bg=args.bg, plate_radius=args.radius)
    p = pathlib.Path(args.out)
    p.write_text(svg, encoding="utf-8")

    # Verify the SVG text itself, with no renderer in the loop: parse the rects
    # back out, confirm they reproduce the matrix exactly, then decode that.
    import re
    import numpy as np
    import zxingcpp
    from PIL import Image

    n = len(m)
    side = n + 2 * args.quiet
    grid = np.zeros((side, side), bool)
    body = svg.split('<g fill=', 1)[1]
    for x, y, w, h in re.findall(
            r'<rect x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)"/>', body):
        x, y, w, h = int(x), int(y), int(w), int(h)
        grid[y:y + h, x:x + w] = True
    src = np.zeros((side, side), bool)
    src[args.quiet:args.quiet + n, args.quiet:args.quiet + n] = np.array(m, bool)
    roundtrip = bool((grid == src).all())

    px = 8
    img = Image.fromarray(np.where(grid, 0, 255).astype("uint8")).resize(
        (side * px, side * px), Image.NEAREST)
    hit = zxingcpp.read_barcodes(img.convert("RGB"))
    got = hit[0].text if hit else None
    ok = bool(got) and got.split("#", 1)[0] == args.url.rstrip("#")

    print(f"{p}  {n}x{n} modules, {len(svg)} bytes")
    print(f"svg round-trips to the exact matrix: {'YES' if roundtrip else 'NO'}")
    print(f"decodes: {'YES' if ok else 'NO'}  ->  {got!r}")
    return 0 if (ok and roundtrip) else 1


if __name__ == "__main__":
    raise SystemExit(main())
