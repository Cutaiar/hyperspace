#!/usr/bin/env python3
"""The effect stack, offscreen: one shot per effect and one per factory preset.

Renders a rotating 24-cell with face patterns through the real pipeline
(render.py → fx.py), each factory effect alone at its defaults and then
every factory fx preset (hyperspace/library/fx/), and writes them to
docs/plans/assets/09-fx/ with a contact sheet. Then times the chain.

    uv run python tools/fx_shots.py [--frames 60] [--only warp,acid]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.fx import FxState
from hyperspace.graphmigrate import wiring_of
from hyperspace.library import FACTORY
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "09-fx"
W, H = 960, 600


def view() -> ViewState:
    s = ViewState(shape=10, faces=True, pattern=2, bright=1.3, speed=0.6)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    s.yaw, s.pitch = 0.4, 0.25
    return s


def shot(ctx, fbo, values: dict, frames: int, scene: bool = True) -> np.ndarray:
    """`frames` frames at 60 fps with fx values applied; the last one as RGB."""
    fx = FxState()
    for name, v in values.items():
        if name in ("on", "mix"):
            setattr(fx, name, v)
        else:
            fx.values[name].update(v)
    r = Renderer(ctx, fx=fx)
    r.wiring = wiring_of(fx)  # plan 33 R23: its run as a load lands it
    s = view()
    if not scene:
        s.lines = s.points = s.faces = False
    for k in range(frames):
        s.integrate(1 / 60)
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=4.0 + k / 60)
    errs = r.fx.compile_all()
    if errs:
        print("  errors:", errs)
    img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1]
    return img.copy()


def preset_values(doc: dict) -> dict:
    """A preset file's fx.* ids → shot()'s {effect: {key: v}} form."""
    out: dict = {}
    for pid, v in doc["values"].items():
        parts = pid.split(".")
        if len(parts) == 2:
            out[parts[1]] = v
        else:
            out.setdefault(parts[1], {})[parts[2]] = v
    return out


def sheet(tiles: list[tuple[str, Path]], path: Path, cols: int = 4) -> None:
    tw, th = W // 3, H // 3
    rows = (len(tiles) + cols - 1) // cols
    im = Image.new("RGB", (cols * tw, rows * (th + 18)), "black")
    d = ImageDraw.Draw(im)
    for k, (label, p) in enumerate(tiles):
        x, y = (k % cols) * tw, (k // cols) * (th + 18)
        im.paste(Image.open(p).resize((tw, th)), (x, y + 18))
        d.text((x + 4, y + 3), label, fill="white")
    im.save(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    only = {x for x in a.only.split(",") if x}
    tiles = []
    p = OUT / "off.png"
    Image.fromarray(shot(ctx, fbo, {}, a.frames)).save(p)
    tiles.append(("off", p))
    for name in FxState().names():
        if only and name not in only:
            continue
        p = OUT / f"effect-{name}.png"
        Image.fromarray(shot(ctx, fbo, {name: {"on": True}}, a.frames)).save(p)
        tiles.append((name, p))
        print("wrote", p.relative_to(ROOT))
    for f in sorted((FACTORY / "fx").glob("*.json")):
        doc = json.loads(f.read_text())
        if only and f.stem not in only:
            continue
        p = OUT / f"preset-{f.stem}.png"
        Image.fromarray(shot(ctx, fbo, preset_values(doc), a.frames,
                             scene=not doc.get("no_scene", False))).save(p)
        tiles.append((doc["name"], p))
        print("wrote", p.relative_to(ROOT))
    sheet(tiles, OUT / "sheet.png")
    print("wrote", (OUT / "sheet.png").relative_to(ROOT))

    # the chain's cost: the heavy trip preset, render drained
    heavy = FACTORY / "fx" / "noita-tripping-balls.json"
    if heavy.exists():
        vals = preset_values(json.loads(heavy.read_text()))
        fx = FxState()
        for name, v in vals.items():
            if isinstance(v, dict):
                fx.values[name].update(v)
        for label, st in (("off", FxState()), ("tripping balls", fx)):
            r = Renderer(ctx, fx=st)
            r.wiring = wiring_of(st)  # plan 33 R23: its run as a load lands it
            s = view()
            ts = []
            for k in range(40):
                fbo.use()
                ctx.viewport = (0, 0, W, H)
                t0 = time.perf_counter()
                r.draw(s, W, H, t_now=k / 60)
                ctx.finish()
                ts.append(time.perf_counter() - t0)
            print(f"frame {label}: {np.median(ts[10:]) * 1e3:.2f} ms at {W}×{H}")


if __name__ == "__main__":
    main()
