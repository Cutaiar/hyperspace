"""How much abuse do these survive, versus a plain high-ECC code?

Simulates the three things that actually kill a printed code: too few camera
pixels per module, optical blur, and a specular hotspot from a phone flash.
"""
import io, math, pathlib
import numpy as np
from PIL import Image, ImageFilter
import segno, zxingcpp

from paths import WEB, WORK

OUT = WORK / "stills"
URL = "https://cutaiar.io/"


def read(img):
    hits = zxingcpp.read_barcodes(img.convert("RGB"))
    return bool(hits) and hits[0].text.split("#", 1)[0] == URL.rstrip("#")


def at_ppm(src_modules, img, ppm, blur=0.0, hotspot=0.0, quiet=4):
    """Render at ppm pixels/module, optionally blurred and flashed."""
    n = src_modules
    side = int(n * ppm)
    im = img.resize((side, side), Image.NEAREST).convert("L")
    q = int(quiet * ppm)
    canvas = Image.new("L", (side + 2 * q, side + 2 * q), 255)
    canvas.paste(im, (q, q))
    if blur:
        canvas = canvas.filter(ImageFilter.GaussianBlur(blur * ppm))
    if hotspot:
        a = np.asarray(canvas).astype(np.float32)
        h, w = a.shape
        yy, xx = np.mgrid[0:h, 0:w]
        cy, cx = h * 0.38, w * 0.46
        r = np.hypot(yy - cy, xx - cx) / (min(h, w) * 0.30)
        a = a + 255.0 * hotspot * np.exp(-r * r)          # specular blow-out
        canvas = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return canvas


def core(path):
    """Strip the printed border back to the raw module grid."""
    im = Image.open(path).convert("L")
    a = np.asarray(im) < 128
    ys, xs = np.where(a)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    return im


CASES = []
# the art codes, ECC L
for tag, n in [("v12_nested_wide_s3", 65), ("v15_nested_open_s3", 77), ("v15_nested_tilt_s3", 77)]:
    CASES.append((f"QArt {tag} (ECC L)", n, core(OUT / f"qart_{tag}.png")))
# plain baselines
for ecc, lbl in [("H", "plain ECC H"), ("Q", "plain ECC Q")]:
    q = segno.make(URL, error=ecc)
    buf = io.BytesIO(); q.save(buf, kind="png", scale=1, border=0); buf.seek(0)
    CASES.append((f"{lbl} (v{q.version})", q.symbol_size(scale=1, border=0)[0], Image.open(buf)))

print(f"{'code':34} {'mods':>5} {'min px/module':>14} {'blur limit':>11} {'flash survived':>15}")
print("-" * 86)
for name, n, img in CASES:
    ppm_min = next((p for p in range(1, 15) if read(at_ppm(n, img, p))), None)
    base = max(ppm_min or 6, 6)
    blur_lim = 0.0
    for b in [x / 20 for x in range(1, 21)]:
        if read(at_ppm(n, img, base, blur=b)): blur_lim = b
        else: break
    flash = 0.0
    for hs in [x / 10 for x in range(1, 13)]:
        if read(at_ppm(n, img, base, hotspot=hs)): flash = hs
        else: break
    print(f"{name:34} {n:>3}x{n:<3} {str(ppm_min or 'FAIL'):>12}   {blur_lim:>10.2f} {flash:>14.1f}")

print("\nblur limit = sigma in modules at which it stops decoding (higher is better)")
print("flash      = peak added brightness as a fraction of full white, survived")
