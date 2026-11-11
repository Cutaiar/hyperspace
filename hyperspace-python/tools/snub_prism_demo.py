#!/usr/bin/env python3
"""The snub icosidodecadodecahedron through Prism: two demo videos, drawn
offscreen by the real renderer and the real effect chain (render.py → fx.py).

  uv run python tools/snub_prism_demo.py --out <scratch folder> [--only knobs|pulse]

Writes into --out, a scratch folder: videos stay out of the repository
(.claude/skills/drive-the-app).

- `snub-prism-knobs.mp4` — Prism's knobs one at a time on the turning star:
  Amount, Rim, Tilt and the lens's centre, then Bloom after the split.
- `snub-prism-pulse.mp4` — Prism and Bloom pulsed by a 120 BPM envelope, as a
  band route on the kick would drive them, on one star and on a field of nine.
  The envelope is a curve, not audio: the video is silent.

1280×720 at 30 fps, encoded by catalog_demo's encoder. The shape turns by
`ViewState.integrate`, as the app turns it, and starts with a pentagram
facing the eye. An effect's knobs are written into its `FxState` every frame
(the chain reads them as it runs); switching an effect on is a new wiring,
so that happens only between segments.
"""

from __future__ import annotations

import argparse
import math
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import moderngl
import numpy as np
from catalog_demo import FPS, H, W, encoder, font
from PIL import Image, ImageDraw

from hyperspace import geometry as G
from hyperspace.fx import FxState
from hyperspace.graphmigrate import wiring_of
from hyperspace.patterns import NAMES as PATTERN_NAMES
from hyperspace.render import Renderer
from hyperspace.view import ViewState

SNUB = G.shape_index("Snub icosidodecadodecahedron")
# a turn about x that brings the five-fold axis (0, φ, 1) to the eye: a
# pentagram face-on, as Wikipedia's picture has it
FACE_ON = [0.0, 0.0, math.atan2(G.PHI, 1.0), 0.0, 0.0, 0.0]
XZ, XZ_YZ = [False, True, False, False, False, False], [False, True, True, False, False, False]
BPM = 120.0
# a 3D shape turns in its own planes: the W planes do nothing to it


def ease(u: float) -> float:
    """0 → 1 with no jolt at either end (smoothstep)."""
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def kick(t: float, bpm: float = BPM, decay: float = 0.11) -> float:
    """A kick's envelope: 1 on each beat, falling away exponentially."""
    return math.exp(-(t % (60.0 / bpm)) / decay)


Knobs = Callable[[float, float], dict]          # (u in the segment, t in the video) → fx values


@dataclass
class Segment:
    title: str
    sub: Callable[[float, float], str]         # (u, t) → the line under the title
    seconds: float
    effects: Knobs                             # every effect on in the segment, its knobs now
    view: dict = field(default_factory=dict)   # ViewState fields set as the segment starts
    planes: list[bool] = field(default_factory=lambda: list(XZ))


class Stage:
    """One framebuffer, and a renderer per run of effects: a segment that
    switches another effect on is wired afresh, as a load wires it."""

    def __init__(self) -> None:
        self.ctx = moderngl.create_context(standalone=True)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.ctx.renderbuffer((W, H))])
        self.fx: FxState | None = None
        self.r: Renderer | None = None
        self.on: frozenset = frozenset()

    def shot(self, v: ViewState, values: dict, t: float) -> Image.Image:
        on = frozenset(values)
        if self.r is None or on != self.on:
            self.fx, self.on = FxState(), on
            for name in on:
                self.fx.values[name]["on"] = True
            self.r = Renderer(self.ctx, fx=self.fx)
            self.r.wiring = wiring_of(self.fx)
        assert self.fx is not None
        for name, knobs in values.items():
            self.fx.values[name].update(knobs)
        self.fbo.use()
        self.ctx.viewport = (0, 0, W, H)
        self.r.draw(v, W, H, t_now=t)
        raw = self.fbo.read(components=3)
        return Image.fromarray(np.frombuffer(raw, np.uint8).reshape(H, W, 3)[::-1])


def caption(im: Image.Image, title: str, sub: str, label: str) -> Image.Image:
    # a band darkening the foot of the frame, so the rainbow never runs
    # through the words
    band = np.asarray(im, dtype=np.float32)
    fade = np.clip((np.arange(H) - (H - 150)) / 60, 0, 0.8)[:, None, None]
    im = Image.fromarray((band * (1 - fade)).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((40, H - 92), title, font=font(30), fill=(235, 235, 235))
    if sub:
        d.text((40, H - 50), sub, font=font(16), fill=(255, 92, 92))
    d.text((W - 40, 34), label, font=font(14), fill=(120, 120, 120), anchor="ra")
    return im


# ------------------------------------------------------------------- knobs

def _prism(**knobs) -> dict:
    return {"taps": 32, **knobs}          # 32 wavelengths: no speckle at a wide split


def knobs_video() -> list[Segment]:
    def amount(u, t):
        return {"prism": _prism(amount=0.13 * ease(u), fringe=0.8, rim=1.0)}

    def rim(u, t):
        r = 1.0 + 2.0 * math.sin(math.pi * ease(u)) - 0.6 * ease(max(0.0, 2 * u - 1))
        return {"prism": _prism(amount=0.13, fringe=0.8, rim=max(r, 0.0))}

    def tilt(u, t):
        return {"prism": _prism(amount=0.025 + 0.02 * ease(u), fringe=1.0, rim=1.0,
                                tilt=18.0 * ease(min(1.0, 1.6 * u)), speed=0.9)}

    def centre(u, t):
        a = 2 * math.pi * ease(u)
        r = 0.35 * math.sin(math.pi * u)
        return {"prism": _prism(amount=0.09, fringe=0.9, rim=1.6,
                                cx=r * math.cos(a), cy=r * math.sin(a))}

    def bloom(u, t):
        return {"prism": _prism(amount=0.1, fringe=1.1, rim=1.4),
                "bloom": {"amount": 0.9 * ease(min(1.0, 2 * u)), "threshold": 0.35}}

    return [
        Segment("The snub icosidodecadodecahedron",
                lambda u, t: "U46 · 60 corners, 104 faces · its corners from the plastic number"
                             " · Prism on, at 0",
                4.0, lambda u, t: {"prism": _prism(amount=0.0)},
                view={"faces": True, "bright": 1.35, "speed": 0.45, "zoom": 1.15}),
        Segment("Prism · Amount",
                lambda u, t: f"amount {0.13 * ease(u):.2f} · the frame resampled once per"
                             " wavelength: red out, violet in",
                8.0, amount),
        Segment("Prism · Rim",
                lambda u, t: f"rim {rim(u, t)['prism']['rim']:.1f} · 0 splits the whole frame,"
                             " 1 a lens, 3 only the outer ring",
                8.0, rim),
        Segment("Prism · Tilt",
                lambda u, t: f"tilt {tilt(u, t)['prism']['tilt']:.0f} px · a straight split on top,"
                             " its direction turning with the speed",
                7.0, tilt),
        Segment("Prism · the lens's centre",
                lambda u, t: "centre ({cx:+.2f}, {cy:+.2f}) · the lens slides off the star"
                             " and back".format(**centre(u, t)["prism"]),
                7.0, centre),
        Segment("Prism, then Bloom",
                lambda u, t: f"bloom {bloom(u, t)['bloom']['amount']:.2f} after the split ·"
                             " the pentagrams' fills catch the light",
                8.0, bloom, view={"bright": 1.5}),
    ]


# ------------------------------------------------------------------- pulse

def pulse_video() -> list[Segment]:
    def beat(u, t):
        k = kick(t)
        return {"prism": _prism(amount=0.02 + 0.12 * k, fringe=0.6 + 0.8 * k, rim=1.2,
                                tilt=8.0 * k, speed=0.4),
                "bloom": {"amount": 0.35 + 0.7 * k, "threshold": 0.35}}

    def wander(u, t):
        k = kick(t, BPM / 2, 0.22)
        a = 2 * math.pi * u
        return {"prism": _prism(amount=0.05 + 0.1 * k, fringe=1.0, rim=1.8,
                                cx=0.35 * math.sin(a), cy=0.25 * math.sin(2 * a)),
                "bloom": {"amount": 0.4 + 0.5 * k, "threshold": 0.35}}

    def field_(u, t):
        k = kick(t)
        return {"prism": _prism(amount=0.015 + 0.055 * k, fringe=0.9, rim=1.0, speed=0.4,
                                tilt=4.0 * k),
                "bloom": {"amount": 0.3 + 0.6 * k, "threshold": 0.4}}

    def env(u, t, bpm=BPM, decay=0.11):
        return "▮" * round(12 * kick(t, bpm, decay))

    return [
        Segment("Prism on the beat",
                lambda u, t: f"amount, fringe, tilt and bloom on a 120 BPM kick's envelope ·"
                             f" what a band route does  {env(u, t)}",
                10.0, beat, planes=list(XZ_YZ),
                view={"faces": True, "bright": 1.45, "speed": 0.7, "zoom": 1.15}),
        Segment("Half time, the lens wandering",
                lambda u, t: f"60 BPM, a longer tail · the lens's centre on a slow figure eight"
                             f"  {env(u, t, BPM / 2, 0.22)}",
                8.0, wander, planes=list(XZ),
                view={"speed": 0.5, "pattern": PATTERN_NAMES.index("caustic")}),
        Segment("A field of nine",
                lambda u, t: f"nine stars on a grid, rippling · one lens over the whole frame"
                             f"  {env(u, t)}",
                10.0, field_, planes=list(XZ_YZ),
                view={"instances": 9, "inst_motion": 3, "inst_amp": 0.3, "zoom": 0.34,
                      "pattern": PATTERN_NAMES.index("flat"), "speed": 0.6}),
    ]


VIDEOS = {"knobs": ("snub-prism-knobs.mp4", knobs_video),
          "pulse": ("snub-prism-pulse.mp4", pulse_video)}


def render(name: str, out: Path) -> Path:
    path = out / VIDEOS[name][0]
    segs = VIDEOS[name][1]()
    stage = Stage()
    ff = encoder(path)
    assert ff.stdin is not None
    v = ViewState(shape=SNUB)
    v.ang = list(FACE_ON)
    v.pitch = 0.08
    t = 0.0
    for k, seg in enumerate(segs, 1):
        for key, val in seg.view.items():
            setattr(v, key, val)
        v.planes = list(seg.planes)
        frames = int(seg.seconds * FPS)
        for f in range(frames):
            u = f / max(frames - 1, 1)
            im = stage.shot(v, seg.effects(u, t), t)
            label = f"snub icosidodecadodecahedron × prism · {k}/{len(segs)}"
            ff.stdin.write(caption(im, seg.title, seg.sub(u, t), label).tobytes())
            v.integrate(1 / FPS)
            t += 1 / FPS
        print(f"{name} {k}/{len(segs)} {seg.title}")
    ff.stdin.close()
    ff.wait()
    print("wrote", path)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True,
                    help="a scratch folder for the videos (not the repository)")
    ap.add_argument("--only", choices=sorted(VIDEOS), help="one of the two videos")
    args = ap.parse_args()
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is not on the PATH")
    args.out.mkdir(parents=True, exist_ok=True)
    for name in ([args.only] if args.only else list(VIDEOS)):
        render(name, args.out)


if __name__ == "__main__":
    main()
