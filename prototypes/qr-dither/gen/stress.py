"""Measure robustness of codes on disk, against plain-QR controls.

gen/gallery.py already measures everything it writes and puts the numbers in
the manifest. This is the tool for everything else: a code you printed and
photographed, an etched plate, a frame grabbed off the projector. Point it at
image files and it reports them next to boring QRs for the same destination.

    uv run --with pillow --with numpy --with segno --with zxing-cpp \\
      python3 gen/stress.py --url https://hyperspace.cutaiar.io shot.png
"""
import argparse

import robust


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--modules", type=int, default=0,
                    help="module count of the images; 0 reads it from the manifest")
    ap.add_argument("images", nargs="*", help="PNG/JPG files to measure")
    args = ap.parse_args()
    url = args.url.rstrip("#")

    rows = []
    for ecc in ("L", "M", "Q", "H"):
        b = robust.plain(url, ecc)
        rows.append((f"plain ECC {ecc} (v{b['version']})", b["modules"],
                     b["min_ppm"], b["blur"], b["flash"]))
    for path in args.images:
        n = args.modules
        if not n:
            raise SystemExit("--modules is required when measuring your own images")
        from PIL import Image
        r = robust.measure(Image.open(path), n, url)
        rows.append((path, n, r["min_ppm"], r["blur"], r["flash"]))

    print(f"\n{'code':40} {'mods':>7} {'min px/mod':>11} {'blur':>7} {'flash':>7}")
    print("-" * 78)
    for name, n, ppm, blur, flash in rows:
        print(f"{name:40} {n:>3}x{n:<3} {str(ppm or 'FAIL'):>11} {blur:>7.2f} {flash:>7.1f}")
    print("\nblur  = Gaussian sigma in MODULES at which it stops decoding (higher is better).")
    print("        Sigma is per module, so compare absolute tolerance by scaling:")
    print("        a 65-module code's modules are 29/65 the width of a 29-module one")
    print("        at the same physical size, so its real blur budget is that much smaller.")
    print("flash = peak added brightness, as a fraction of full white, survived.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
