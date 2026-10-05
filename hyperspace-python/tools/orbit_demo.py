#!/usr/bin/env python3
"""Plan 18 WP4 — `hands-orbit`, two hands on the camera, shown headless.

SYNTHETIC HANDS and OFFSCREEN RENDERS: no tracker and no window. The
factory preset is loaded through the real `Presets` over a `Router` on a
throwaway library home (`tools/preset_shots.py`'s construction, so
nothing touches ~/Hyperspace), and two fake hands are driven through the
real `HandsIO` chain (range → One Euro → dead zone → follower, the
default feel and the default ranges, no interaction box), each reading
held for a second and a half.

    uv run python tools/orbit_demo.py [--frames 90] [--no-shots]

Writes, under docs/plans/assets/18-hand-and-knob-feel/:
  orbit-sweeps.txt   per row: the hand's reading (u across the axis's
                     range, and in the axis's own unit) → the camera
                     param, with the other four camera params' largest
                     move beside it; then the hand gone; then a camera
                     the mouse moved first, played and let go
  orbit.png          the default scene, 3 × 3: the right hand at the
                     left / centre / right of its range (columns), the
                     left hand low / half up / high (rows)

It shows what the five rows do to the numbers and to a frame. It does not
show how the depths feel under a real hand (hand check N9).
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import preset_shots as shots  # tools/preset_shots.py: Stage, the fake source, the poses

from hyperspace.hands.core import default_range
from hyperspace.preset import FACTORY_PRESETS

NAME = "hands-orbit"
OUT = ROOT / "docs" / "plans" / "assets" / "18-hand-and-knob-feel"
W, H = shots.W, shots.H
US = (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)
UNIT = {"x": "mm", "y": "mm", "z": "mm", "roll": "°", "pitch": "°", "yaw": "°"}
SAY = {("right", "x"): "left … right", ("right", "pitch"): "fingers down … up",
       ("left", "x"): "left … right", ("left", "z"): "reaching in … pulled back",
       ("left", "y"): "low … high"}
# a camera the mouse moved before the hands came in (the last table)
MOUSE = {"camera.yaw": math.radians(30), "camera.pitch": math.radians(-10),
         "camera.zoom": 1.6, "camera.pan.x": 120.0, "camera.pan.y": -60.0}
# the strip: the right hand across its range, the left hand low / half / high
COLS = (("R left", 0.0), ("R centre", 0.5), ("R right", 1.0))
ROWS = (("L low", 0.0), ("L half up", 0.5), ("L high", 1.0))


class Stage(shots.Stage):
    """`preset_shots.Stage` on a preset the list holds under its own name
    (the party presets load by their upper-case slot name)."""

    def __init__(self, ctx=None, mouse: dict[str, float] | None = None):
        super().__init__(NAME, ctx, load=NAME)
        for pid, v in (mouse or {}).items():
            self.reg[pid].set(v)                    # a scene-setter's write: the base


def rows():
    return [b for b in FACTORY_PRESETS[NAME].routes()]


def axis_of(b) -> tuple[str, str]:
    side, axis = b.source.split(":", 1)[1].split(".")
    return side, axis


def reading(side: str, axis: str, u: float) -> str:
    lo, hi = default_range(side, axis)
    v = lo + u * (hi - lo)
    if UNIT[axis] == "°":
        return f"{v:+7.1f}°"                      # the angle features are degrees
    return f"{v:+7.1f} mm"


def camera(st) -> dict[str, float]:
    """The five camera params as the picture has them, in norm units."""
    return {b.target: st.reg[b.target].eff_norm for b in rows()}


def others(st, own: str, before: dict[str, float]) -> str:
    """The largest move, in norm units, of the four camera params the row
    does not own: what the picture has now against `before` (`camera`,
    taken before the hold), so a moved base counts as much as an offset."""
    worst = 0.0
    for pid, was in before.items():
        if pid == own:
            continue
        p = st.reg[pid]
        d = p.eff_norm - was
        worst = max(worst, abs(math.remainder(d, 1.0) if p.wrap else d))
    return f"{worst:.4f}"


def sweeps(frames: int) -> str:
    out = [(f"Hyperspace — {NAME}: each hand axis against its camera param "
            "(tools/orbit_demo.py; plan 18 WP4)"),
           ("SYNTHETIC HANDS through the real HandsIO chain (default feel, default ranges, "
            "no box): nothing here was seen by a tracker."),
           ("Each line is a fresh load of the preset with one hand held at that reading for "
            f"{frames} frames ({frames / 60:.1f} s); its other axes are at rest"),
           ("(height at the bottom, the centred ones in the middle) and the other hand is "
            "out. 'others' is the largest move, in norm units,"),
           ("of the four camera params the row does not own. The depths are a first cut "
            "nobody has felt (hand check N9)."), ""]
    for b in rows():
        side, axis = axis_of(b)
        s = side[0].upper()
        out.append(f"{b.source} → {b.target}   push {b.value:+g}   ({SAY[side, axis]})")
        for u in US:
            st = Stage()
            p = st.reg[b.target]
            base = camera(st)
            if u == US[0]:
                out += [f"    base (no hand): {p.fmt(p.value)}",
                        f"    {'u':>6}   {'hand reads':>11}   {p.label.lower():>10}   others"]
            st.hold({f"{s}.{axis}": u}, frames)
            rest = "   (rest)" if u == (0.0 if axis == "y" else 0.5) else ""
            out.append(f"    {u:6.3f}   {reading(side, axis, u):>11}   {p.fmt(p.value):>10}   "
                       f"{others(st, b.target, base)}{rest}")
        st.hold({}, frames)
        out += [f"    hand gone, {frames} frames after u = 1: {p.fmt(p.value)}", ""]
    st = Stage(mouse=MOUSE)

    def fmt() -> str:
        return "  ".join(f"{pid.split('camera.')[1]} {st.reg[pid].fmt(st.reg[pid].value)}"
                         for pid in MOUSE)

    out += [("A camera the mouse moved first (bases written as a scene-setter writes them), "
             "then both hands, then no hands"),
            f"    mouse left it at:         {fmt()}"]
    st.hold({"L.y": 0.0, "R.y": 0.0}, frames)
    out.append(f"    both hands in, at rest:   {fmt()}")
    st.hold({"R.x": 1.0, "R.pitch": 1.0, "L.x": 1.0, "L.z": 0.0, "L.y": 1.0}, frames)
    out.append(f"    both hands at an end:     {fmt()}")
    st.hold({}, frames)
    out.append(f"    both hands out:           {fmt()}")
    return "\n".join(out) + "\n"


def strip(ctx, frames: int, path: Path) -> None:
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    tw, th, label = W // 2, H // 2, 20
    im = Image.new("RGB", (len(COLS) * tw, len(ROWS) * (th + label)), "black")
    d = ImageDraw.Draw(im)
    for j, (lname, ly) in enumerate(ROWS):
        for i, (rname, rx) in enumerate(COLS):
            st = Stage(ctx)
            st.hold({}, 30)                          # the scene settles
            st.hold({"R.x": rx, "L.y": ly}, frames, fbo)
            img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1]
            cam = st.reg
            # ASCII only: PIL's built-in font has no ° or ×
            text = (f"{rname}, {lname}:  yaw {math.degrees(cam['camera.yaw'].value):+.0f} deg"
                    f"  zoom {cam['camera.zoom'].value:.2f}x")
            x, y = i * tw, j * (th + label)
            im.paste(Image.fromarray(img.copy()).resize((tw, th)), (x, y + label))
            d.text((x + 6, y + 4), text, fill="white")
            st.release()
    im.quantize(256, method=Image.Quantize.MEDIANCUT,
                dither=Image.Dither.FLOYDSTEINBERG).save(path, optimize=True)
    fbo.release()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=shots.SETTLE)
    ap.add_argument("--no-shots", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "orbit-sweeps.txt").write_text(sweeps(a.frames))
    print("wrote", (OUT / "orbit-sweeps.txt").relative_to(ROOT))
    if not a.no_shots:
        strip(moderngl.create_context(standalone=True), a.frames, OUT / "orbit.png")
        print("wrote", (OUT / "orbit.png").relative_to(ROOT))


if __name__ == "__main__":
    main()
