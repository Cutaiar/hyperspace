#!/usr/bin/env python3
"""Plan 28's demo: the catalog, the scenes and the 3D switch, drawn
offscreen by the real renderer.

  uv run python tools/catalog_demo.py            # video, stills and the sheet
  uv run python tools/catalog_demo.py --no-video # stills and the sheet only

Writes into docs/plans/assets/28-catalog/: `demo.mp4` (1280×720, 30 fps,
through ffmpeg on the PATH), one still per scene (`scene-*.png`), the 3D
switch before and after (`three-d-*.png`) and a contact sheet of every
shape the catalog adds (`catalog.png`). Each segment is a ViewState
turned by `ViewState.integrate`, as the app turns it; captions are drawn
over the frames, never into the scene.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from hyperspace import geometry as G
from hyperspace.patterns import NAMES as PATTERN_NAMES
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "28-catalog"
W, H, FPS = 1280, 720, 30
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size: int):
    for path in (FONT, "/System/Library/Fonts/SFNSRounded.ttf",
                 "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def idx(name: str) -> int:
    return G.shape_index(name)


@dataclass
class Segment:
    title: str
    sub: str
    seconds: float
    view: dict
    still: str = ""                   # file name of the still, "" none
    still_at: float = 0.6             # where in the segment, 0–1
    each: object = None               # each(view, u): per-frame changes, u in 0–1
    caption: object = None            # caption(u) -> (title, sub), else the segment's
    planes: list = field(default_factory=lambda: [False, True, True, True, True, True])


def zoom_in(lo: float, hi: float):
    def each(v, u):
        v.zoom = lo * (hi / lo) ** (0.5 - 0.5 * math.cos(math.pi * u))
    return each


def switch_3d(v, u):
    # on for the middle of the segment: the W planes hold, the 3D planes
    # turn on, and it goes off again from the pose it held
    v.three_d = 0.35 <= u < 0.75


def three_d_caption(u: float) -> tuple[str, str]:
    if 0.35 <= u < 0.75:
        sub = ("VIEW → 3D: the W planes hold — the tesseract keeps its pose in w "
               "and turns on in XY, XZ, YZ")
        return ("The 3D switch · on", sub)
    sub = ("the tesseract turning through w in every plane — no jump as the switch "
           "goes on or off")
    return ("The 3D switch · off", sub)


def segments() -> list[Segment]:
    segs = [
        Segment("Celestial tesseract", "scene · Hopf glome ⊃ tesseract ⊃ small stellated "
                "dodecahedron — the star counter-turns in 3D inside a 4D tumble", 11.0,
                {"shape": idx("Celestial tesseract"), "faces": True, "bright": 1.35, "speed": 0.45},
                still="scene-celestial-tesseract.png", still_at=0.45),
        Segment("Celestial cube", "scene · armillary sphere ⊃ cube ⊃ great stellated "
                "dodecahedron — its points break through the cube's faces", 9.0,
                {"shape": idx("Celestial cube"), "faces": True, "bright": 1.35, "speed": 0.45},
                still="scene-celestial-cube.png", still_at=0.5),
        Segment("Mysterium Cosmographicum", "scene · Kepler, 1596: Saturn ⊃ cube ⊃ Jupiter ⊃ "
                "tetrahedron ⊃ Mars ⊃ dodecahedron ⊃ Earth ⊃ icosahedron ⊃ Venus ⊃ "
                "octahedron ⊃ Mercury", 12.0,
                {"shape": idx("Mysterium Cosmographicum"), "faces": True, "bright": 1.4,
                 "speed": 0.35},
                still="scene-mysterium.png", still_at=0.55, each=zoom_in(0.95, 6.5)),
        Segment("The 3D switch", "", 12.0,
                {"shape": idx("Tesseract"), "faces": True, "bright": 1.2, "speed": 0.6},
                still="three-d-tesseract.png", still_at=0.6, each=switch_3d,
                caption=three_d_caption, planes=[True] * 6),
        Segment("Faces on a star", "Moravian star · faces on, pattern KALEIDO", 6.0,
                {"shape": idx("Moravian star"), "faces": True, "bright": 1.5, "speed": 0.4,
                 "pattern": PATTERN_NAMES.index("KALEIDO")},
                still="moravian-kaleido.png", still_at=0.5),
    ]
    for i in range(len(G.SHAPES)):
        s = G.SHAPES[i]
        if not s.family or s.family == "Scene":
            continue
        segs.append(Segment(f"{s.name}", f"{s.alias} · {s.sym}", 1.6,
                            {"shape": i, "faces": True, "bright": 1.3, "speed": 0.7}))
    return segs


class Stage:
    """One renderer drawing into one framebuffer, read back as RGB."""

    def __init__(self, w: int = W, h: int = H):
        self.ctx = moderngl.create_context(standalone=True)
        self.w, self.h = w, h
        self.fbo = self.ctx.framebuffer(color_attachments=[self.ctx.renderbuffer((w, h))])
        self.fbo.use()
        self.ctx.viewport = (0, 0, w, h)
        self.r = Renderer(self.ctx)

    def shot(self, v: ViewState, t: float) -> Image.Image:
        self.fbo.use()
        self.r.draw(v, self.w, self.h, t_now=t)
        raw = self.fbo.read(components=3)
        return Image.fromarray(np.frombuffer(raw, np.uint8).reshape(self.h, self.w, 3)[::-1])


def caption(im: Image.Image, title: str, sub: str, k: int, n: int) -> Image.Image:
    # a band darkening the foot of the frame, so a scene that fills it
    # never runs through the words
    band = np.asarray(im, dtype=np.float32)
    fade = np.clip((np.arange(H) - (H - 150)) / 60, 0, 0.8)[:, None, None]
    im = Image.fromarray((band * (1 - fade)).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((40, H - 92), title, font=font(30), fill=(235, 235, 235))
    if sub:
        d.text((40, H - 50), sub, font=font(16), fill=(255, 92, 92))
    d.text((W - 40, 34), f"plan 28 · {k}/{n}", font=font(14), fill=(120, 120, 120), anchor="ra")
    return im


def run(video: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stage = Stage()
    segs = segments()
    ff = None
    if video:
        if shutil.which("ffmpeg") is None:
            raise SystemExit("ffmpeg is not on the PATH (or pass --no-video)")
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset",
             "slow", "-crf", "27", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             str(OUT / "demo.mp4")], stdin=subprocess.PIPE)
    t = 0.0
    for k, seg in enumerate(segs, 1):
        v = ViewState(**seg.view)
        v.planes = list(seg.planes)
        v.ang = [0.3, 0.2, 0.1, 0.0, 0.0, 0.0]
        v.pitch = 0.18
        frames = int(seg.seconds * FPS) if video else 1
        still_frame = int(seg.still_at * (frames - 1)) if video else 0
        for f in range(frames):
            u = f / max(frames - 1, 1)
            if seg.each is not None:
                seg.each(v, u if video else seg.still_at)
            if not video:
                v.integrate(seg.still_at * seg.seconds)
            im = stage.shot(v, t)
            if seg.still and f == still_frame:
                im.save(OUT / seg.still, optimize=True)
            if seg.still == "three-d-tesseract.png" and f == int(0.2 * (frames - 1)):
                im.save(OUT / "three-d-off.png", optimize=True)
            if ff is not None:
                title, sub = seg.caption(u) if seg.caption else (seg.title, seg.sub)
                ff.stdin.write(caption(im, title, sub, k, len(segs)).tobytes())
            v.integrate(1 / FPS)
            t += 1 / FPS
        print(f"{k:2d}/{len(segs)} {seg.title}")
    if ff is not None:
        ff.stdin.close()
        ff.wait()
        print("wrote", OUT / "demo.mp4")
    sheet()


def sheet() -> None:
    """Every shape the catalog adds, one tile each, at a generic pose."""
    ids = [i for i, s in enumerate(G.SHAPES) if s.family]
    tw, th, cols = 400, 340, 6
    stage = Stage(tw, th)
    rows = math.ceil(len(ids) / cols)
    out = Image.new("RGB", (tw * cols, th * rows))
    for k, i in enumerate(ids):
        v = ViewState(shape=i, ang=list(G.GENERIC_POSE), yaw=0.4, pitch=0.25, faces=True,
                      bright=1.3)
        im = stage.shot(v, 1.0)
        d = ImageDraw.Draw(im)
        d.text((10, 8), f"{i + 1} {G.SHAPES[i].name}", font=font(15), fill=(230, 230, 230))
        d.text((10, 28), G.SHAPES[i].family, font=font(12), fill=(255, 92, 92))
        out.paste(im, ((k % cols) * tw, (k // cols) * th))
    out.save(OUT / "catalog.png", optimize=True)
    print("wrote", OUT / "catalog.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-video", action="store_true", help="stills and the sheet only")
    run(not ap.parse_args().no_video)
