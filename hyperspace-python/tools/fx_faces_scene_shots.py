#!/usr/bin/env python3
"""An effect on the frame and the same effect on the faces, offscreen.

The question a newcomer asks after aiming an effect at the faces: does
the picture change, and only on the faces? Two scenes, as a person
meets them — the app's default view with Faces switched on (the
tesseract, FLAT fill) and party-tumble's view (a 24-cell, faces on, a
pattern), and that again at full Brightness (a face's opacity scales
with Brightness; there is no face-opacity control) — each rendered through the real pipeline (render.py → fx.py)
with: no effect; Plasma on the frame; Plasma on the faces; Kaleidoscope
on the faces. A last column is the difference between "no effect" and
"Plasma on the faces", brightened: where the face-aimed effect changed
the picture.

These are offscreen renders on this machine's GPU, not the app on a
screen and not the rig.

    uv run python tools/fx_faces_scene_shots.py
        → docs/plans/assets/20-fx-dream-looks/fx-faces-scene.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.fx import FACES, FRAME, FxState
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "20-fx-dream-looks"
W, H = 640, 400
FRAMES = 60
BAR = 18
PRESET = ROOT / "hyperspace" / "library" / "presets" / "party-tumble.json"
# preset keys → ViewState fields, for the ones that change the picture
FIELDS = {"view.shape": "shape", "view.depth4": "depth4", "view.bright": "bright",
          "view.points": "points", "view.lines": "lines", "view.faces": "faces",
          "view.pattern": "pattern", "view.pattern_mix": "pattern_mix",
          "camera.zoom": "zoom", "view.instances": "instances"}


def default_view() -> ViewState:
    s = ViewState(faces=True)               # the launch view, Faces switched on
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    return s


def preset_view() -> ViewState:
    s = default_view()
    values = json.loads(PRESET.read_text())["values"]
    for key, attr in FIELDS.items():
        if key in values:
            setattr(s, attr, type(getattr(s, attr))(values[key]))
    return s


def shot(ctx, fbo, s: ViewState, name: str | None, target: int) -> np.ndarray:
    fx = FxState()
    if name is not None:
        fx.values[name].update(on=True, target=target)
    r = Renderer(ctx, fx=fx)
    for k in range(FRAMES):
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=4.0 + k / 60)     # the view held still: the same pose in every tile
    if r.face_error or r.fx.errors:
        print("  errors:", r.face_error, r.fx.errors)
    img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1].copy()
    r.face_fx.release()
    r.face_pic.release()
    r.fx.release()
    return img


COLS = ("no effect", "Plasma on the frame", "Plasma on the faces", "Kaleidoscope on the faces",
        "changed by Plasma on the faces (×4)")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    def bright(v: ViewState) -> ViewState:
        v.bright = 4.0                  # Brightness at the top of its fader
        return v

    rows = []
    for label, view in (("default view, Faces on (Brightness 1.0)", default_view),
                        ("party-tumble's view (Brightness 2.0)", preset_view),
                        ("party-tumble's view, Brightness 4.0", lambda: bright(preset_view()))):
        tiles = [shot(ctx, fbo, view(), None, FRAME),
                 shot(ctx, fbo, view(), "plasma", FRAME),
                 shot(ctx, fbo, view(), "plasma", FACES),
                 shot(ctx, fbo, view(), "kaleido", FACES)]
        diff = np.abs(tiles[2].astype(np.int16) - tiles[0].astype(np.int16))
        tiles.append(np.clip(diff * 4, 0, 255).astype(np.uint8))
        changed = (diff.max(axis=2) > 8).mean()
        print(f"{label}: plasma on the faces changed {changed:.1%} of the pixels "
              f"(mean |Δ| {diff.mean():.1f}/255)")
        rows.append((label, tiles))
    tw, th = W // 2, H // 2
    sheet = Image.new("RGB", (tw * len(COLS), (th + BAR) * len(rows) + BAR), "black")
    d = ImageDraw.Draw(sheet)
    for c, name in enumerate(COLS):
        d.text((c * tw + 4, 3), name, fill=(220, 220, 225))
    for k, (label, tiles) in enumerate(rows):
        y = BAR + k * (th + BAR)
        d.text((4, y + 3), label, fill=(160, 160, 170))
        for c, img in enumerate(tiles):
            sheet.paste(Image.fromarray(img).resize((tw, th), Image.LANCZOS), (c * tw, y + BAR))
    path = OUT / "fx-faces-scene.png"
    sheet.save(path, optimize=True)
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
