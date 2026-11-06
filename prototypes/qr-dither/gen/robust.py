"""How much abuse a finished code survives.

Three things kill a printed or projected code: too few camera pixels per
module, optical blur, and a specular hotspot from a phone flash. Each is
measured by degrading the code until zxing stops reading it.

Measure the *rendered* code, never the bare module matrix. Styling cannot
change what a code decodes to, but it absolutely changes whether a camera
manages to read it -- circular modules drop the ink fill fraction, rounded
corners soften the edges a binariser keys on. Measuring the matrix would report
one number for all seven dot styles and hide the whole effect.
"""
import io

import numpy as np
import segno
import zxingcpp
from PIL import Image, ImageFilter


def read(img, url):
    hits = zxingcpp.read_barcodes(img.convert("RGB"))
    return bool(hits) and hits[0].text.split("#", 1)[0] == url.rstrip("#")


def core(path_or_img):
    """Strip the quiet zone back to the module grid's bounding box."""
    im = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    im = im.convert("L")
    a = np.asarray(im) < 128
    if not a.any():
        return im
    ys, xs = np.where(a)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def at_ppm(img, n, ppm, blur=0.0, hotspot=0.0, quiet=4):
    """Re-render at ppm pixels per module, optionally blurred and flashed.

    A camera sensor integrates over each pixel's area, so going *down* in
    resolution has to area-average (BOX); NEAREST there would alias a styled
    render into noise and badly understate it. Going up, NEAREST is right:
    it keeps the hard module edges a real print would have.
    """
    side = max(1, int(round(n * ppm)))
    im = img.convert("L")
    im = im.resize((side, side), Image.BOX if side < im.width else Image.NEAREST)
    q = max(1, int(round(quiet * ppm)))
    canvas = Image.new("L", (side + 2 * q, side + 2 * q), 255)
    canvas.paste(im, (q, q))
    if blur:
        canvas = canvas.filter(ImageFilter.GaussianBlur(blur * ppm))
    if hotspot:
        a = np.asarray(canvas).astype(np.float32)
        h, w = a.shape
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.hypot(yy - h * 0.38, xx - w * 0.46) / (min(h, w) * 0.30)
        a = a + 255.0 * hotspot * np.exp(-r * r)          # specular blow-out
        canvas = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return canvas


def measure(img, n, url, max_ppm=16):
    """min pixels per module, blur tolerance, and flash tolerance.

    blur is a Gaussian sigma in *modules*, so it compares across versions:
    a 77-module code and a 29-module one are judged by the same yardstick.
    """
    src = core(img)
    min_ppm = next((p for p in range(1, max_ppm + 1) if read(at_ppm(src, n, p), url)), None)
    if min_ppm is None:
        return {"min_ppm": None, "blur": 0.0, "flash": 0.0}
    # judge blur and glare with headroom, not at the edge of resolution
    base = max(min_ppm, 6)
    blur = 0.0
    for b in (x / 20 for x in range(1, 21)):
        if not read(at_ppm(src, n, base, blur=b), url):
            break
        blur = b
    flash = 0.0
    for h in (x / 10 for x in range(1, 13)):
        if not read(at_ppm(src, n, base, hotspot=h), url):
            break
        flash = h
    return {"min_ppm": min_ppm, "blur": round(blur, 2), "flash": round(flash, 1)}


def plain(url, ecc="M"):
    """A boring QR for the same destination -- the control to judge art against."""
    q = segno.make(url, error=ecc)
    buf = io.BytesIO()
    q.save(buf, kind="png", scale=1, border=0)
    buf.seek(0)
    img = Image.open(buf)
    n = q.symbol_size(scale=1, border=0)[0]
    out = {"ecc": ecc, "version": q.version, "modules": n}
    out.update(measure(img, n, url))
    return out


def pack(matrix):
    """Module grid as base64: row-major, MSB first, bit i = y * n + x.

    The node pipeline and the sticker builder want the grid, not an SVG.
    """
    import base64
    n = len(matrix)
    bits = bytearray((n * n + 7) // 8)
    for y, row in enumerate(matrix):
        for x, v in enumerate(row):
            if v:
                i = y * n + x
                bits[i >> 3] |= 0x80 >> (i & 7)
    return base64.b64encode(bytes(bits)).decode("ascii")
