#!/usr/bin/env python3
"""The distortion effects' demo: Shake, Wave and Blocks (shaders/fx/), each
knob shown doing what it does, drawn offscreen by the real renderer and the
real effect passes.

  uv run python tools/distort_demo.py --out <dir>          # distort-demo.mp4 + a sheet
  uv run python tools/distort_demo.py --out <dir> --only 3,7 --no-video

Each segment is the turning scene put through one effect (`FxChain.run_one`,
the pass a graph Effect node runs), with the same pass over a test card in
the corner, so what the field does to straight lines is plain. Where a
caption says "kick", Amount rides a 120 bpm decaying pulse — a stand-in for
a bass band wired to it; "swell" is a slow rise and fall, a hand's. The
stage's font, the caption band and the encoder are catalog_demo's. Videos
stay out of the repository: --out is yours to choose.
"""

from __future__ import annotations

import argparse
import math
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import moderngl
import numpy as np
from catalog_demo import FPS, H, W, encoder, font
from PIL import Image, ImageDraw

from hyperspace import geometry as G
from hyperspace.fx import FxChain, FxState
from hyperspace.graph import Wiring
from hyperspace.graphmigrate import wired_wiring
from hyperspace.patterns import NAMES as PATTERN_NAMES
from hyperspace.render import Renderer
from hyperspace.view import ViewState

CW, CH = 320, 180           # the test card's corner
BPM = 120.0


def kick(t: float) -> float:
    """A kick drum's envelope at BPM: 1 on the beat, gone by the next."""
    return math.exp(-7.0 * ((t * BPM / 60.0) % 1.0))


def swell(t: float) -> float:
    """A slow rise and fall, 0 … 1 every 4 s."""
    return 0.5 - 0.5 * math.cos(t * math.tau / 4.0)


DRIVES = {"kick": kick, "swell": swell, "": lambda t: 1.0}


@dataclass
class Segment:
    """One effect (or a run of them) with its values; `drive` scales every
    effect's Amount by a signal each frame."""
    title: str
    sub: str
    fx: list[tuple[str, dict]]
    drive: str = ""
    seconds: float = 5.0
    each: object = None               # each(values_by_effect, u): per-frame knob moves
    names: list[str] = field(default_factory=list)


def S(title, sub, name, drive="", seconds=5.0, each=None, **values) -> Segment:
    return Segment(title, sub, [(name, values)], drive, seconds, each)


def segments() -> list[Segment]:
    return [
        # ---- Shake
        S("Shake · buzz", "back and forth along a line · rate 14 a second · Amount on the kick",
          "shake", "kick", amount=0.03, rate=14.0),
        S("Shake · buzz + Smear", "the shutter left open across the travel: a blur, not a jump",
          "shake", "kick", amount=0.05, rate=14.0, smear=1.0),
        S("Shake · buzz + Split", "red ahead of green, blue behind: the picture holds, "
          "the edges buzz in colour", "shake", "kick", amount=0.035, rate=9.0, split=1.0),
        S("Shake · orbit + Split", "round a circle, the three colours a third of a turn apart "
          "· Amount on a swell", "shake", "swell", amount=0.03, rate=1.5, motion=1, split=1.0),
        S("Shake · punch", "in and out about the centre · Hard 1 snaps between the two ends",
          "shake", "kick", amount=0.06, rate=8.0, motion=2, hard=1.0, smear=0.5),
        S("Shake · jolt", "knocked a new way each shake, then settling · Smear and Split on",
          "shake", "kick", amount=0.08, rate=6.0, motion=3, smear=0.6, split=0.5),
        # ---- Wave
        S("Wave · line · slide", "a sine counted up the frame, pushing sideways: rows slip "
          "past each other", "wave", "swell", amount=0.08, waves=3.0),
        S("Wave · line · squeeze", "the same wave pushing along its own travel: the picture "
          "bunches and stretches", "wave", "swell", amount=0.07, waves=3.0, push=1, angle=0.0),
        S("Wave · rings · squeeze", "counted out from the centre: ripples in a pond",
          "wave", "swell", amount=0.05, waves=5.0, along=1, push=1, drift=1.0),
        S("Wave · rings · slide", "each ring turned against the next", "wave", "swell",
          amount=0.12, waves=3.0, along=1, push=0, drift=0.4),
        S("Wave · spokes · slide", "counted round the centre, pushing out: petals",
          "wave", "swell", amount=0.12, waves=7.0, along=2, push=0, drift=0.5),
        S("Wave · square, 0 Steps → saw", "a waveform with an edge cuts the picture into "
          "slabs · then a saw", "wave", "", amount=0.06, waves=6.0, shape=2, drift=0.3,
          each=lambda v, u: v["wave"].update(shape=2 if u < 0.5 else 3)),
        S("Wave · sine in 2 Steps", "a smooth wave flattened into levels: slabs that hold "
          "their picture", "wave", "swell", amount=0.1, waves=4.0, steps=2, drift=0.4),
        S("Wave · noise", "a new random level each wave, eased between · on the kick",
          "wave", "kick", amount=0.12, waves=14.0, shape=4, drift=6.0),
        S("Wave · rings · squeeze + Split", "the colours part along the push: aberration "
          "that follows the ripple", "wave", "swell", amount=0.06, waves=4.0, along=1, push=1,
          drift=0.8, split=0.8),
        # ---- Blocks
        S("Blocks · shift · random", "48 px cells, each slid by its own number",
          "blocks", "swell", amount=0.6, cell=48.0, drift=0.5),
        S("Blocks · shift · rows · Aspect 16", "long strips, every row out of step with the "
          "next: a picture losing sync", "blocks", "kick", amount=0.7, cell=14.0, aspect=16.0,
          rule=0, shape=4, spread=0.37, drift=5.0),
        S("Blocks · zoom · Group 4", "16 px units in 4 × 4 blocks: each block magnifies or "
          "shrinks its cells together", "blocks", "swell", amount=2.5, cell=16.0, group=4,
          action=1, drift=0.3),
        S("Blocks · stretch", "one way only: where a cell's number is low, a single line of "
          "it is pulled into streaks", "blocks", "swell", amount=4.0, cell=64.0, action=2,
          drift=0.3, angle=math.pi / 2),
        S("Blocks · turn · diagonal · square", "a checkerboard (Spread ½) snapping a "
          "quarter turn each way", "blocks", "", amount=1.0, cell=90.0, action=3, rule=2,
          shape=2, drift=0.7),
        S("Blocks · turn · rings · sine", "the turn running out from the middle in square "
          "rings", "blocks", "", amount=1.0, cell=60.0, action=3, rule=3, spread=0.12,
          drift=0.4),
        S("Blocks · bulge", "a lens in every cell, still at its rim, so the picture stays "
          "joined", "blocks", "swell", amount=2.0, cell=120.0, action=4, rule=2, spread=0.5,
          drift=0.4),
        S("Blocks · swap · noise", "cells trade places with their neighbours, whole cells "
          "at a time", "blocks", "", amount=2.5, cell=80.0, action=5, shape=4, drift=2.0),
        S("Blocks · shift + Split", "the colours part along each cell's move · on the kick",
          "blocks", "kick", amount=0.8, cell=40.0, group=2, split=1.0, shape=4, drift=3.0),
        # ---- together
        Segment("Wave → Blocks → Shake", "three nodes in a row, all three Amounts on the kick",
                [("wave", {"amount": 0.05, "waves": 4.0, "along": 1, "push": 1, "drift": 0.8,
                           "split": 0.5}),
                 ("blocks", {"amount": 0.5, "cell": 36.0, "aspect": 8.0, "rule": 0, "shape": 4,
                             "spread": 0.37, "drift": 4.0}),
                 ("shake", {"amount": 0.03, "rate": 12.0, "smear": 0.7, "split": 0.6})],
                "kick", 8.0),
    ]


def card() -> Image.Image:
    """A test card: a grid, a circle and colour bars, so a field's shape shows."""
    im = Image.new("RGB", (CW, CH), (16, 16, 20))
    d = ImageDraw.Draw(im)
    for k, c in enumerate([(230, 60, 60), (230, 200, 60), (60, 200, 90), (60, 200, 220),
                           (70, 90, 230), (200, 70, 220)]):
        d.rectangle((k * CW // 6, CH - 24, (k + 1) * CW // 6, CH), fill=c)
    for x in range(0, CW, 20):
        d.line((x, 0, x, CH - 25), fill=(210, 210, 210))
    for y in range(0, CH - 24, 20):
        d.line((0, y, CW, y), fill=(210, 210, 210))
    d.ellipse((CW // 2 - 60, CH // 2 - 72, CW // 2 + 60, CH // 2 + 48),
              outline=(255, 255, 255), width=3)
    return im


class Stage:
    """The scene drawn into a texture, and effect passes over it."""

    def __init__(self):
        self.ctx = ctx = moderngl.create_context(standalone=True)
        self.scene = ctx.texture((W, H), 4)
        self.scene_fbo = ctx.framebuffer(color_attachments=[self.scene])
        self.ping = [ctx.texture((W, H), 4) for _ in range(2)]
        self.ping_fbo = [ctx.framebuffer(color_attachments=[t]) for t in self.ping]
        rgba = np.asarray(card().convert("RGBA"))[::-1]
        self.card = ctx.texture((CW, CH), 4, np.ascontiguousarray(rgba).tobytes())
        self.cping = [ctx.texture((CW, CH), 4) for _ in range(2)]
        self.cping_fbo = [ctx.framebuffer(color_attachments=[t]) for t in self.cping]
        self.r = Renderer(ctx)
        self.r.wiring = wired_wiring(Wiring())

    def _through(self, chain, names, src, texs, fbos, t) -> np.ndarray:
        for k, name in enumerate(names):
            chain.run_one(name, src, fbos[k % 2], t, opaque=1)
            src = texs[k % 2]
        h, w = src.size[1], src.size[0]
        return np.frombuffer(src.read(), np.uint8).reshape(h, w, 4)[::-1, :, :3]

    def shot(self, v: ViewState, chain: FxChain, names: list[str], t: float) -> Image.Image:
        self.scene_fbo.use()
        self.ctx.viewport = (0, 0, W, H)
        self.r.draw(v, W, H, t_now=t)
        im = Image.fromarray(self._through(chain, names, self.scene, self.ping,
                                           self.ping_fbo, t))
        small = Image.fromarray(self._through(chain, names, self.card, self.cping,
                                              self.cping_fbo, t))
        im.paste(small, (W - CW - 24, 24))
        ImageDraw.Draw(im).rectangle((W - CW - 25, 23, W - 24, 24 + CH), outline=(90, 90, 90))
        return im


def caption(im: Image.Image, seg: Segment, k: int, n: int, level: float) -> Image.Image:
    band = np.asarray(im, dtype=np.float32)
    fade = np.clip((np.arange(H) - (H - 150)) / 60, 0, 0.8)[:, None, None]
    im = Image.fromarray((band * (1 - fade)).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((40, H - 92), seg.title, font=font(30), fill=(235, 235, 235))
    d.text((40, H - 50), seg.sub, font=font(16), fill=(255, 92, 92))
    d.text((W - 40, H - 86), f"{k}/{n}", font=font(14), fill=(120, 120, 120), anchor="ra")
    if seg.drive:
        # the signal on Amount, as a meter
        x0, y0, w = W - 240, H - 44, 200
        d.text((x0 - 10, y0 - 3), f"{seg.drive} → Amount", font=font(13), fill=(150, 150, 150),
               anchor="ra")
        d.rectangle((x0, y0, x0 + w, y0 + 10), outline=(90, 90, 90))
        d.rectangle((x0, y0, x0 + int(w * level), y0 + 10), fill=(255, 92, 92))
    return im


def view() -> ViewState:
    v = ViewState(shape=G.shape_index("Celestial tesseract"), faces=True, bright=1.35,
                  speed=0.3, pattern=PATTERN_NAMES.index("plaid"))
    v.ang = [0.3, 0.2, 0.1, 0.0, 0.0, 0.0]
    v.pitch = 0.18
    v.zoom = 1.5                    # fill the frame: a field shows where there is picture
    return v


def run(out: Path, video: bool, only: set[int]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    stage = Stage()
    segs = segments()
    ff = None
    if video:
        if shutil.which("ffmpeg") is None:
            raise SystemExit("ffmpeg is not on the PATH (or pass --no-video)")
        ff = encoder(out / "distort-demo.mp4")
    v = view()
    t = 0.0
    stills = []
    for k, seg in enumerate(segs, 1):
        if only and k not in only:
            continue
        st = FxState()
        names = [name for name, _ in seg.fx]
        base = {}
        for name, values in seg.fx:
            unknown = set(values) - {p.key for p in st.specs[name].params}
            assert not unknown, f"{name}: no such knob {unknown}"
            st.values[name].update(on=True, **values)
            base[name] = values.get("amount", st.values[name]["amount"])
        chain = FxChain(stage.ctx, st)
        frames = int(seg.seconds * FPS)
        for f in range(frames):
            u = f / max(frames - 1, 1)
            if seg.each is not None:
                seg.each(st.values, u)
            level = DRIVES[seg.drive](f / FPS)
            for name in names:
                st.values[name]["amount"] = base[name] * level
            im = caption(stage.shot(v, chain, names, t), seg, k, len(segs), level)
            # the sheet's still: mid-segment, on a beat when the kick drives it
            if f == round(int(0.5 * seg.seconds * BPM / 60) * 60 / BPM * FPS) + 2:
                stills.append(im)
            if ff is not None:
                ff.stdin.write(im.tobytes())
            v.integrate(1 / FPS)
            t += 1 / FPS
        errs = chain.state.errors
        assert not errs, errs
        print(f"{k:2d}/{len(segs)} {seg.title}", flush=True)
    if ff is not None:
        ff.stdin.close()
        ff.wait()
        print("wrote", out / "distort-demo.mp4")
    cols = 4
    tw, th = W // 3, H // 3
    sheet = Image.new("RGB", (cols * tw, -(-len(stills) // cols) * th), "black")
    for k, im in enumerate(stills):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
    sheet.save(out / "distort-sheet.png", optimize=True)
    print("wrote", out / "distort-sheet.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--only", default="", help="segment numbers, comma-separated")
    a = ap.parse_args()
    run(a.out, not a.no_video, {int(x) for x in a.only.split(",") if x})
