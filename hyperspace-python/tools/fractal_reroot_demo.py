#!/usr/bin/env python3
"""Plan 64, row 887: a moved or turned fractal re-rooted, before and after
the fix, side by side.

The same dive twice, in lockstep, with the same world offset on the shape
(as the hand rig's grip leaves it): on the left the re-root as first
pushed (`fractal.step` with no offset: the offset left as it was), on the
right the fix (`app._reroot`'s road: `fractal.step` with the offset, the
offset rebased when the step asks). At every re-root the point drawn at
the middle of the screen is followed across it, and how far it lands from
where it was, in pixels, is printed under each side: 0 is no jump. A cross
marks the middle of the screen.

Three segments: the Sierpinski tetrahedron turned (a 3D fractal: the pan
and depth make up for the offset), the Menger sponge turned and moved, and
the Sierpinski 5-cell turned (4D: the offset rebased).

    uv run python tools/fractal_reroot_demo.py --out docs/plans/assets/64-recursive-geometry

Offscreen on whatever GL this machine has (`Renderer.draw`, the default
wiring), not the rig.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace import fractal, geometry
from hyperspace import world as W
from hyperspace.graph import Wiring
from hyperspace.graphmigrate import wired_wiring
from hyperspace.render import Renderer
from hyperspace.view import ViewState

FPS = 30
LABEL = 28
FOOT = 46
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

SEGMENTS = (
    ("Sierpinski tetrahedron", "turned 1 rad by the grip",
     W.Pose.turn3(W.qexp([0.3, 0.9, -0.2]))),
    ("Menger sponge", "turned and moved by the grip",
     W.Pose.turn3(W.qexp([-0.4, 0.6, 0.2]), (0.05, -0.03, 0.0))),
    ("Sierpinski 5-cell", "turned by the grip · 4D: no jump, but the dive drifts off (open, row 887)",
     W.Pose.turn3(W.qexp([0.5, -0.7, 0.3]))),
)


class Side:
    """One half: a view, its own world, and how it re-roots."""

    def __init__(self, name: str, pose: W.Pose, fixed: bool):
        self.s = ViewState(shape=geometry.shape_index(name), lines=True, points=True)
        self.s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
        self.s.yaw, self.s.pitch, self.s.zoom = 0.45, 0.3, 1.2
        self.s.pan = [0.03, -0.02]
        self.world = W.World.default()
        self.world.objects["shape"].offset = pose
        self.fixed = fixed
        self.jumps: list[float] = []

    def step(self, w: int, h: int) -> None:
        s = self.s
        off = self.world.offset_matrix("shape")
        x, before = self._middle(w, h)
        path = list(s.dive.path)
        if self.fixed:
            moved = s.reroot(None, off)
            if moved is not None:
                self.world.rebase("shape", *moved)
        else:
            s.reroot(None, None)                    # as first pushed: no offset
        if s.dive.path != path and x is not None:
            after = self._px(x, w, h)
            if after is not None and before is not None:
                self.jumps.append(float(np.linalg.norm(after - before)))

    def _middle(self, w, h):
        """The point drawn at the middle of the screen, in the shape's top
        frame, and where it is drawn (px)."""
        s, spec = self.s, fractal.spec_of(self.s.shape)
        off = self.world.offset_matrix("shape")
        m = geometry.model_matrix(s.zoom, s.pan, off)
        P = np.linalg.solve(m[:3, :3], -m[:3, 3])
        wf = s.zoom * P + np.array([s.pan[0], -s.pan[1], 0.0])
        q = np.r_[wf, 0.0] - np.array([s.pan[0], -s.pan[1], s.dive.z, s.dive.w])
        x = (q / s.zoom) @ fractal.turn(s).T
        for k in reversed(s.dive.path):                 # up to the top frame
            x = spec.ratio * x + (1.0 - spec.ratio) * spec.centres[k]
        return x, self._px(x, w, h)

    def _px(self, x_top, w, h):
        s, spec = self.s, fractal.spec_of(self.s.shape)
        x = np.array(x_top, dtype=np.float64)[None]
        for k in s.dive.path:
            x = (x - (1.0 - spec.ratio) * spec.centres[k]) / spec.ratio
        off = self.world.offset_matrix("shape")
        P, _, _, _ = fractal.walk(spec, s, w, h, off).place(x)
        m = geometry.model_matrix(s.zoom, s.pan, off)
        D = P[0] @ m[:3, :3].T + m[:3, 3]
        c = geometry.eye_matrix(w, h) @ np.r_[D, 1.0]
        if c[3] <= geometry.EYE_NEAR:
            return None
        return np.array([c[0] / c[3] * w / 2, c[1] / c[3] * h / 2])


def run(out: Path, w: int, h: int, seconds: float) -> None:
    ctx = moderngl.create_context(standalone=True)
    r = Renderer(ctx)
    r.wiring = wired_wiring(Wiring())
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((w, h), 3)],
                          depth_attachment=ctx.depth_renderbuffer((w, h)))
    font, bold = ImageFont.truetype(FONT, 15), ImageFont.truetype(BOLD, 17)
    n = int(seconds * FPS)
    hold = FPS // 2
    with tempfile.TemporaryDirectory() as tmp:
        k = 0
        sheet = []
        for name, how, pose in SEGMENTS:
            sides = [Side(name, pose, False), Side(name, pose, True)]
            spec = fractal.FRACTALS[name]
            rate = (1.0 / spec.ratio) ** (6.0 / (n - 2 * hold))   # six levels over the dive
            for f in range(n):
                zoom_now = hold <= f < n - hold
                img = Image.new("RGB", (2 * w, LABEL + h + FOOT), (12, 12, 12))
                d = ImageDraw.Draw(img)
                d.text((10, 5), f"{name} · {how} · zooming in · the same dive, both sides",
                       fill=(235, 235, 235), font=bold)
                for j, side in enumerate(sides):
                    s = side.s
                    s.integrate(1.0 / FPS)
                    if zoom_now:
                        s.zoom *= rate
                    side.step(w, h)
                    r.world = side.world
                    fbo.use()
                    ctx.viewport = (0, 0, w, h)
                    r.draw(s, w, h, t_now=f / FPS)
                    pic = np.frombuffer(fbo.read(components=3), np.uint8).reshape(h, w, 3)[::-1]
                    x0 = j * w
                    img.paste(Image.fromarray(pic), (x0, LABEL))
                    cx, cy = x0 + w // 2, LABEL + h // 2
                    d.line([(cx - 9, cy), (cx + 9, cy)], fill=(80, 200, 255), width=1)
                    d.line([(cx, cy - 9), (cx, cy + 9)], fill=(80, 200, 255), width=1)
                    tag = ("before: the re-root ignores the offset" if j == 0
                           else "after: the re-root keeps every point")
                    box = d.textbbox((x0 + 8, LABEL + 6), tag, font=font)
                    d.rectangle((box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3), fill=(0, 0, 0))
                    d.text((x0 + 8, LABEL + 6), tag, fill=(235, 235, 235), font=font)
                    js = side.jumps
                    last = js[-1] if js else 0.0
                    worst = max(js) if js else 0.0
                    col = (255, 90, 90) if worst > 1.0 else (120, 230, 140)
                    d.text((x0 + 10, LABEL + h + 4),
                           f"re-roots {len(js):2d}   levels in {len(s.dive.path):2d}",
                           fill=(200, 200, 200), font=font)
                    d.text((x0 + 10, LABEL + h + 24),
                           f"jump at the last re-root {last:7.1f} px   worst {worst:7.1f} px",
                           fill=col, font=font)
                    if js and len(js) and last > 1.0 and f % 10 < 6:
                        d.text((x0 + w - 90, LABEL + 8), "JUMP", fill=(255, 90, 90), font=bold)
                d.line([(w, LABEL), (w, LABEL + h + FOOT)], fill=(70, 70, 70))
                img.save(Path(tmp) / f"{k:05d}.png", compress_level=1)
                if f == n - hold:
                    sheet.append(img.copy())
                k += 1
            print(f"{name}: before {len(sides[0].jumps)} re-roots, worst "
                  f"{max(sides[0].jumps, default=0):.1f} px; after {len(sides[1].jumps)}, "
                  f"worst {max(sides[1].jumps, default=0):.3f} px")
        Image.fromarray(np.concatenate([np.asarray(x) for x in sheet], axis=0)).save(
            out / "reroot-fix.png", optimize=True)
        src = ["-framerate", str(FPS), "-i", str(Path(tmp) / "%05d.png")]
        enc = ["-c:v", "libx264", "-preset", "slow", "-b:v", "1600k"]
        log = str(Path(tmp) / "pass")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, *enc, "-pass", "1",
                        "-passlogfile", log, "-an", "-f", "null", "/dev/null"], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, *enc, "-pass", "2",
                        "-passlogfile", log, "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(out / "reroot-fix.mp4")], check=True)
    print(f"{out / 'reroot-fix.mp4'}, {out / 'reroot-fix.png'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", type=int, nargs=2, default=(640, 360), metavar=("W", "H"))
    ap.add_argument("--seconds", type=float, default=7.0, help="per segment")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    run(a.out, *a.size, a.seconds)


if __name__ == "__main__":
    main()
