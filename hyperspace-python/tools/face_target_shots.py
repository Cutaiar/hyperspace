#!/usr/bin/env python3
"""The faces as an effect target (plan 20 WP1), offscreen: a contact sheet
and the frame's cost.

Every factory effect aimed at the faces, through the real pipeline
(render.py → fx.py): a tesseract with its faces on, once with a test
bitmap over the FLAT pattern and once with the PLAID pattern and no
bitmap. One row per effect, six tiles:

    the 1024² picture (bitmap) · the faces showing it per face · the same
    in screen mapping · the picture (PLAID) · per face (PLAID) · the same
    effect aimed at the frame, as before plan 20

The first row is no effect (its picture tiles are the seed, read through
an effect at a mix of one in a million). Writes
docs/plans/assets/20-fx-dream-looks/face-target-contact-sheet.png, a
four-row face-target.png for the PR, and face-target-timing.txt: the
median frame with no effect, with a four-effect frame chain, with the
same four on the faces, and with four on each.

These are offscreen renders on this machine's GPU, not the app on a
screen and not the rig.

    uv run python tools/face_target_shots.py [--frames 90] [--no-timing]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.fx import FACES, FRAME, PER_FACE, SCREEN, FxState
from hyperspace.render import FACE_PIC, Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "20-fx-dream-looks"
W, H = 960, 600
TILE = (256, 160)            # a tile on the full sheet
PR_TILE = (256, 160)         # and on the PR's four rows
BAR = 18                     # a row's label strip
PR_ROWS = ("kaleido", "plasma", "zoomblur", "huecycle")
FOUR = ("plasma", "kaleido", "zoomblur", "huecycle")     # party-trip's stack
OTHER = ("warp", "acid", "wobble", "tripcolour")
TESSERACT, PLAID = 3, 2


def test_card(path: Path) -> None:
    """A bitmap with something to fold, smear and re-colour: four coloured
    quarters, a white ring, a diagonal, a dark border."""
    n = 256
    y, x = np.mgrid[0:n, 0:n]
    img = np.zeros((n, n, 4), dtype=np.uint8)
    img[..., 3] = 255
    quarters = {(0, 0): (230, 60, 50), (0, 1): (60, 200, 80),
                (1, 0): (60, 110, 240), (1, 1): (240, 200, 50)}
    for (qy, qx), c in quarters.items():
        img[(y // (n // 2) == qy) & (x // (n // 2) == qx), :3] = c
    r = np.hypot(x - n / 2, y - n / 2)
    img[(r > n * 0.28) & (r < n * 0.34), :3] = 255
    img[np.abs(x - y) < 5, :3] = 255
    edge = (x < 8) | (y < 8) | (x >= n - 8) | (y >= n - 8)
    img[edge, :3] = 20
    Image.fromarray(img).save(path)


def view(bitmap: str = "", pattern: int = 0) -> ViewState:
    s = ViewState(shape=TESSERACT, faces=True, pattern=pattern, bright=1.3, speed=0.6,
                  zoom=1.7, bmp_file=bitmap)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    s.yaw, s.pitch = 0.4, 0.25
    return s


def state(name: str | None, target: int, face_map: int = PER_FACE) -> FxState:
    fx = FxState()
    fx.face_map = face_map
    if name is None:
        if target == FACES:          # the seed, through a pass that changes nothing
            fx.values["huecycle"].update(on=True, mix=1e-6, target=FACES)
        return fx
    fx.values[name].update(on=True, target=target)
    if name == "glimmer":
        fx.values[name]["density"] = 1.0
    return fx


def shot(ctx, fbo, s: ViewState, fx: FxState, frames: int) -> tuple[np.ndarray, np.ndarray | None]:
    """`frames` frames at 60 fps; the last as RGB, and the face picture
    (premultiplied RGB over black) if one was made."""
    r = Renderer(ctx, fx=fx)
    for k in range(frames):
        s.integrate(1 / 60)
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=4.0 + k / 60)
    if r.face_error or r.fx.errors:
        print("  errors:", r.face_error, r.fx.errors)
    img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1].copy()
    pic = None
    if r.face_pic.tex is not None:
        raw = np.frombuffer(r.face_pic.tex.read(), dtype=np.uint8)
        pic = raw.reshape(FACE_PIC, FACE_PIC, 4)[::-1, :, :3].copy()
    r.face_fx.release()
    r.face_pic.release()
    r.fx.release()
    return img, pic


def tile(img: np.ndarray | None, size: tuple[int, int]) -> Image.Image:
    """An image fitted into a tile, centred on black (the picture is square)."""
    tw, th = size
    out = Image.new("RGB", size, "black")
    if img is None:
        return out
    im = Image.fromarray(img)
    k = min(tw / im.width, th / im.height)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    out.paste(im, ((tw - im.width) // 2, (th - im.height) // 2))
    return out


def row(ctx, fbo, card: str, name: str | None, frames: int) -> list[np.ndarray | None]:
    f_bmp, pic_bmp = shot(ctx, fbo, view(card), state(name, FACES), frames)
    f_scr, _ = shot(ctx, fbo, view(card), state(name, FACES, SCREEN), frames)
    f_pla, pic_pla = shot(ctx, fbo, view(pattern=PLAID), state(name, FACES), frames)
    f_frm, _ = shot(ctx, fbo, view(card), state(name, FRAME), frames)
    if name is None:                 # the faces as they are with nothing aimed at them
        f_bmp, _ = shot(ctx, fbo, view(card), FxState(), frames)
        f_scr = f_bmp
        f_pla, _ = shot(ctx, fbo, view(pattern=PLAID), FxState(), frames)
    return [pic_bmp, f_bmp, f_scr, pic_pla, f_pla, f_frm]


COLS = ("picture (bitmap over FLAT)", "faces: per face", "faces: screen",
        "picture (PLAID)", "faces: per face (PLAID)", "the effect on the frame")


def sheet(rows: list[tuple[str, list[np.ndarray | None]]], path: Path,
          size: tuple[int, int]) -> None:
    """The rows as one image, small enough to live in git (the full
    sheet is about a megabyte)."""
    tw, th = size
    im = Image.new("RGB", (len(COLS) * tw, BAR + len(rows) * (th + BAR)), "black")
    d = ImageDraw.Draw(im)
    for c, label in enumerate(COLS):
        d.text((c * tw + 4, 3), label, fill=(160, 160, 160))
    for k, (label, shots) in enumerate(rows):
        y = BAR + k * (th + BAR)
        d.text((4, y + 3), label, fill="white")
        for c, img in enumerate(shots):
            im.paste(tile(img, size), (c * tw, y + BAR))
    im.save(path, optimize=True)


def timing(ctx, frames: int = 240, runs: int = 3) -> str:
    """Median frame time at 1920×1080, no MSAA, ctx.finish() around each
    frame: what the face target adds to a frame."""
    w, h = 1920, 1080
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h))])
    cases = (("no effects", (), ()),
             ("frame chain, four effects (Plasma, Kaleidoscope, Zoom burst, Hue cycle)", FOUR, ()),
             ("the same four aimed at the faces, none on the frame", (), FOUR),
             ("four on the frame + four others on the faces (Warp, Acid, Wobble, Trip colour)",
              FOUR, OTHER))
    lines = [f"plan 20 WP1: frame time, {w}x{h} offscreen, no MSAA, ctx.finish() around each frame,",
             (f"median of {frames} frames, {runs} runs; face picture {FACE_PIC}x{FACE_PIC}; "
              f"GPU: {ctx.info['GL_RENDERER']}"),
             ""]
    for label, on_frame, on_faces in cases:
        meds = []
        for _ in range(runs):
            fx = FxState()
            for n in on_frame:
                fx.values[n].update(on=True, target=FRAME)
            for n in on_faces:
                fx.values[n].update(on=True, target=FACES)
            r = Renderer(ctx, fx=fx)
            s = view(pattern=PLAID)
            ts = []
            for k in range(frames + 20):
                s.integrate(1 / 60)
                fbo.use()
                ctx.viewport = (0, 0, w, h)
                ctx.finish()
                t0 = time.perf_counter()
                r.draw(s, w, h, t_now=4.0 + k / 60)
                ctx.finish()
                if k >= 20:              # the first frames compile and allocate
                    ts.append((time.perf_counter() - t0) * 1000)
            meds.append(statistics.median(ts))
            assert not r.face_error and not r.fx.errors
            r.face_fx.release()
            r.face_pic.release()
            r.fx.release()
        lines.append(f"{label:<82} " + " / ".join(f"{m:.2f}" for m in meds) + " ms")
    fbo.release()
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=90)
    ap.add_argument("--no-timing", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    with tempfile.TemporaryDirectory() as tmp:
        card = str(Path(tmp) / "card.png")
        test_card(Path(card))
        base = FxState()
        rows = [("no effect", row(ctx, fbo, card, None, a.frames))]
        for name in base.names():
            rows.append((f"{base.specs[name].label}  ({name})", row(ctx, fbo, card, name, a.frames)))
            print("rendered", name)
    sheet(rows, OUT / "face-target-contact-sheet.png", TILE)
    names = ["no effect", *base.names()]
    pr = [rows[0]] + [rows[names.index(n)] for n in PR_ROWS]
    sheet(pr, OUT / "face-target.png", PR_TILE)
    print("wrote", (OUT / "face-target-contact-sheet.png").relative_to(ROOT))
    print("wrote", (OUT / "face-target.png").relative_to(ROOT))
    if not a.no_timing:
        text = timing(ctx)
        (OUT / "face-target-timing.txt").write_text(text)
        print(text)


if __name__ == "__main__":
    main()
