#!/usr/bin/env python3
"""Plan 64, part 2: a grabbed fractal dived into, then flown through.

Each segment drives the app's own fractal steps once a frame, in the app's
order (`app._space`, `app._reroot`, the shape's home, `app._fly`), on a world
whose shape the grip has turned (and in one, moved):

1. the whole shape, held still: an object, the world's offset on it;
2. a zoom in: past the rig's box the view goes inside (the space), then
   down through the cells — at each crossing and each re-root the point at the
   middle of the screen is followed across it, and how far it lands from where
   it was, in pixels, is printed (0 is no jump);
3. a flight inside: the world's offset on the space turned and moved, as the
   grip's physics would, folded into the view — it turns about the middle of
   the screen and travels through the fractal's own space.

Offscreen on whatever GL this machine has (`Renderer.draw`, the default
wiring), not the rig.

    uv run python tools/fractal_grab_demo.py --out docs/plans/assets/64-recursive-geometry
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace import app, fractal, geometry, poi, shapeframe
from hyperspace import world as W
from hyperspace.graph import Wiring
from hyperspace.graphmigrate import wired_wiring
from hyperspace.render import Renderer
from hyperspace.view import ViewState

FPS = 30
LABEL = 28
FOOT = 48
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

SEGMENTS = (
    ("Sierpinski tetrahedron", "turned by the grip",
     W.Pose.turn3(W.qexp([0.3, 0.9, -0.2]))),
    ("Menger sponge", "turned and moved by the grip",
     W.Pose.turn3(W.qexp([-0.4, 0.6, 0.2]), (0.05, -0.03, 0.0))),
    ("Sierpinski 5-cell", "turned by the grip (4D)",
     W.Pose.turn3(W.qexp([0.5, -0.7, 0.3]))),
)


def middle(h, w, hh):
    """The shape's point drawn at the middle of the screen (top frame), and
    its pixel there."""
    s, spec = h.view, fractal.spec_of(h.view.shape)
    off = drawn_off(h)
    m = geometry.model_matrix(s.zoom, s.pan, off)
    P = np.linalg.solve(m[:3, :3], -m[:3, 3])
    wf = s.zoom * P + np.array([s.pan[0], -s.pan[1], 0.0])
    q = np.r_[wf, 0.0] - np.array([s.pan[0], -s.pan[1], s.dive.z, s.dive.w])
    x = (q / s.zoom) @ fractal.turn(s).T
    for k in reversed(s.dive.path):
        x = spec.ratio * x + (1.0 - spec.ratio) * spec.centres[k]
    return x, px(h, x, w, hh)


def drawn_off(h):
    obj = h.world.objects["shape"]
    return shapeframe.drawn_offset(h.view, h.world.offset_matrix("shape"), obj.bounded)


def px(h, x_top, w, hh):
    s, spec = h.view, fractal.spec_of(h.view.shape)
    x = np.array(x_top, dtype=np.float64)[None]
    for k in s.dive.path:
        x = (x - (1.0 - spec.ratio) * spec.centres[k]) / spec.ratio
    off = drawn_off(h)
    P, _, _, _ = fractal.walk(spec, s, w, hh, off).place(x)
    m = geometry.model_matrix(s.zoom, s.pan, off)
    c = geometry.eye_matrix(w, hh) @ np.r_[P[0] @ m[:3, :3].T + m[:3, 3], 1.0]
    return None if c[3] <= geometry.EYE_NEAR else np.array([c[0] / c[3], c[1] / c[3]]) * (w / 2, hh / 2)


def run(out: Path, w: int, hh: int, seconds: float) -> None:
    ctx = moderngl.create_context(standalone=True)
    r = Renderer(ctx)
    r.wiring = wired_wiring(Wiring())
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((w, hh), 3)],
                          depth_attachment=ctx.depth_renderbuffer((w, hh)))
    font, bold = ImageFont.truetype(FONT, 15), ImageFont.truetype(BOLD, 17)
    n = int(seconds * FPS)
    hold, dive_end = FPS // 2, int(0.6 * n)
    box = poi.box_for(w, hh)
    sheet = []
    with tempfile.TemporaryDirectory() as tmp:
        k = 0
        for name, how, pose in SEGMENTS:
            s = ViewState(shape=geometry.shape_index(name), lines=True, points=True)
            s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
            s.yaw, s.pitch, s.zoom, s.pan = 0.45, 0.3, 1.0, [0.03, -0.02]
            world = W.World.default()
            world.objects["shape"].offset = pose
            world.box = tuple(box)
            h = SimpleNamespace(view=s, world=world)
            spec = fractal.FRACTALS[name]
            rate = (1.0 / spec.ratio) ** (5.0 / (dive_end - hold))
            jumps: list[float] = []
            for f in range(n):
                s.integrate(1.0 / FPS)
                diving = hold <= f < dive_end
                if diving:
                    s.zoom *= rate
                obj = world.objects["shape"]
                if obj.bounded:
                    world.home("shape", W.shape_home(s.zoom, s.pan))
                x, before = middle(h, w, hh)
                path, inside, last = list(s.dive.path), s.dive.inside, s.dive.last
                app._space(h, None)
                app._reroot(h, None)
                eased = not s.dive.path and s.zoom < last and last > fractal.Z_HOME
                if (s.dive.path != path or s.dive.inside != inside) and not eased:
                    after = px(h, x, w, hh)
                    if before is not None and after is not None:
                        jumps.append(float(np.linalg.norm(after - before)))
                if obj.bounded:
                    world.home("shape", W.shape_home(s.zoom, s.pan))
                if f >= dive_end and not obj.bounded:
                    # the flight: what the grip's physics would do to the space
                    t = (f - dive_end) / FPS
                    obj.offset = W.Pose.turn3(W.qexp([0.0, 0.35 * t, 0.12 * t]),
                                              (0.08 * t, 0.0, 0.05 * t))
                app._fly(h, None)
                r.world = world
                fbo.use()
                ctx.viewport = (0, 0, w, hh)
                r.draw(s, w, hh, t_now=f / FPS)
                pic = np.frombuffer(fbo.read(components=3), np.uint8).reshape(hh, w, 3)[::-1]
                img = Image.new("RGB", (w, LABEL + hh + FOOT), (12, 12, 12))
                img.paste(Image.fromarray(pic), (0, LABEL))
                d = ImageDraw.Draw(img)
                phase = ("held still: an object" if f < hold else
                         "zooming in" if diving else "inside: flying through it")
                d.text((10, 5), f"{name} · {how} · {phase}", fill=(235, 235, 235), font=bold)
                cx, cy = w // 2, LABEL + hh // 2
                d.line([(cx - 9, cy), (cx + 9, cy)], fill=(80, 200, 255))
                d.line([(cx, cy - 9), (cx, cy + 9)], fill=(80, 200, 255))
                what = "the space (inside)" if s.dive.inside else "an object (outside)"
                d.text((10, LABEL + hh + 4),
                       f"the fist holds {what}   levels in {len(s.dive.path):2d}",
                       fill=(200, 200, 200), font=font)
                worst = max(jumps, default=0.0)
                d.text((10, LABEL + hh + 25),
                       f"crossings and re-roots {len(jumps):2d}   worst jump {worst:6.3f} px",
                       fill=(120, 230, 140) if worst <= 0.5 else (255, 90, 90), font=font)
                img.save(Path(tmp) / f"{k:05d}.png", compress_level=1)
                if f in (dive_end - 1, n - 1):
                    sheet.append(img.copy())
                k += 1
            print(f"{name}: {len(jumps)} crossings and re-roots, worst jump "
                  f"{max(jumps, default=0.0):.3f} px")
        rows = [np.concatenate([np.asarray(sheet[i]), np.asarray(sheet[i + 1])], axis=1)
                for i in range(0, len(sheet), 2)]
        Image.fromarray(np.concatenate(rows, axis=0)).save(out / "grab-dive.png", optimize=True)
        src = ["-framerate", str(FPS), "-i", str(Path(tmp) / "%05d.png")]
        enc = ["-c:v", "libx264", "-preset", "slow", "-b:v", "1400k"]
        log = str(Path(tmp) / "pass")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, *enc, "-pass", "1",
                        "-passlogfile", log, "-an", "-f", "null", "/dev/null"], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, *enc, "-pass", "2",
                        "-passlogfile", log, "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(out / "grab-dive.mp4")], check=True)
    print(f"{out / 'grab-dive.mp4'}, {out / 'grab-dive.png'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", type=int, nargs=2, default=(800, 450), metavar=("W", "H"))
    ap.add_argument("--seconds", type=float, default=8.0, help="per segment")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    run(a.out, *a.size, a.seconds)


if __name__ == "__main__":
    main()
