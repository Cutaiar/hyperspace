#!/usr/bin/env python3
"""Plan 21's compose path, offscreen: one frame shown on several outputs.

Every picture is drawn by `Renderer.draw_outputs` (render.py) onto
offscreen framebuffers standing in for the windows, with two synthetic
ghost hands (tests/test_ghost.py's open hand and fist — no tracker) over
a 24-cell with face patterns and effects on. No window, screen, glass or
projector is involved: the sheets show what the renderer writes into
each output's framebuffer, not how it looks on the rig.

    uv run python tools/outputs_shots.py compose   # WP1: outputs-compose.png

writes into docs/plans/assets/21-outputs-and-the-hands/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fake_hands import hand  # tests/fake_hands.py

from hyperspace import outputs as O
from hyperspace.fx import FxState
from hyperspace.ghost import _font
from hyperspace.hands import skeleton
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "21-outputs-and-the-hands"
FW, FH = 640, 400            # the frame: the first output's size
BG = (18, 18, 22)
INK = (225, 225, 230)
DIM_INK = (150, 150, 160)


def hands() -> NS:
    """Two synthetic hands, as tests/test_ghost.py feeds the ghost."""
    sk = {"left": skeleton(hand("left", "open", (-90.0, 210.0, 0.0))),
          "right": skeleton(hand("right", "fist", (90.0, 200.0, 10.0)))}
    return NS(skeleton=sk, cfg={"mode": "desktop"})


def renderer(ctx, effects=("warp",), **values) -> Renderer:
    fx = FxState()
    for n in effects:
        fx.values[n]["on"] = True
        fx.values[n].update(values.get(n, {}))
    r = Renderer(ctx, fx=fx)
    r.ghost.state.on, r.ghost.state.alpha = True, 1.0
    r.ghost.source = hands()
    return r


def view_state() -> ViewState:
    return ViewState(shape=10, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25,
                     faces=True, pattern=2)


def target(ctx, size):
    return ctx.framebuffer(color_attachments=[ctx.renderbuffer(size, 4)])


def pixels(f) -> Image.Image:
    w, h = f.size
    a = np.frombuffer(f.read(components=3), dtype=np.uint8).reshape(h, w, 3)[::-1]
    return Image.fromarray(a.copy())


def frames(ctx, r, views, n=12, t0=2.0):
    """`n` frames at 30 fps (the hands fade in, the effects move)."""
    s = view_state()
    for k in range(n):
        s.ang = [a + 0.01 for a in s.ang]
        r.draw_outputs(s, FW, FH, 1.0, views, t_now=t0 + k / 30)


def stats_line(r) -> str:
    st = r.stats
    names = ", ".join(O.NAMES[k] for k in st["pipelines"]) or "none"
    return (f"Renderer.stats: pipelines [{names}] · chain runs {st['chain_runs']} · "
            f"direct {st['direct']} · captures {st['captures']} · hands' layer {st['layer']}")


def compose(ctx) -> Path:
    """Three switch combinations, each on two outputs at once: the glass
    (the frame's size) and a square projector, letterboxed and at 60%."""
    S = O.Switches
    rows = [("scene + hands", S()), ("scene only", S(hands=False)),
            ("hands only", S(scene=False))]
    side = 400
    pad, head, foot = 16, 30, 26
    title = _font(18)
    small = _font(14)
    width = pad + FW + pad + side + pad
    height = pad + 34 + len(rows) * (head + max(FH, side) + foot + pad)
    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, pad), "Plan 21 WP1 — one frame, two outputs, three switch states "
           "(offscreen, synthetic hands, warp on)", fill=INK, font=title)
    y = pad + 34
    for label, sw in rows:
        r = renderer(ctx)
        glass = O.View(sw, (FW, FH), target=target(ctx, (FW, FH)))
        proj = O.View(O.Switches(scene=sw.scene, hands=sw.hands, dim=0.6), (side, side),
                      target=target(ctx, (side, side)))
        frames(ctx, r, [glass, proj])
        d.text((pad, y), f"{label}:  output 1 'glass' {FW}×{FH}", fill=INK, font=small)
        _, y0, w0, h0 = O.fit((FW, FH), (side, side))
        d.text((pad + FW + pad, y), f"output 2 {side}×{side} · frame in {w0}×{h0} at y {y0}"
               f" · own dim 60%", fill=INK, font=small)
        y += head
        sheet.paste(pixels(glass.target), (pad, y))
        sheet.paste(pixels(proj.target), (pad + FW + pad, y))
        d.rectangle((pad + FW + pad - 1, y - 1, pad + FW + pad + side, y + side),
                    outline=(70, 70, 80))
        y += max(FH, side) + 4
        d.text((pad, y), stats_line(r), fill=DIM_INK, font=small)
        y += foot + pad
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "outputs-compose.png"
    sheet.save(path)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=["compose"])
    args = ap.parse_args()
    ctx = moderngl.create_context(standalone=True)
    if args.what == "compose":
        print(compose(ctx))


if __name__ == "__main__":
    main()
