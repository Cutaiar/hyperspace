#!/usr/bin/env python3
"""Plan 12 — the party presets, offscreen: each preset's look under a set
of hand poses, and the sweep tables the plan cites.

Every ``party-*`` preset of the test corpus (``tests/corpus/presets/``, copied
into a scratch library home) is loaded through the real ``Presets`` over a
``Router`` — its values and its routes in one load, as its pad does — and
two fake hands are driven through the real ``HandsIO`` chain
(range → One Euro → dead zone → follower) at a handful of poses, each held
for a second and a half before the frame is taken. No audio source: the
lane rows are quiet, so what the shots show is the hands alone over the
preset's bases. No dream worker either (the tool attaches none), so in the wake
shots the echoes are real and the dream buffer is empty.

    uv run python tools/preset_shots.py [--only tumble,trip] [--frames 90] [--no-shots]

Writes, under docs/plans/assets/12-presets/:
  <name>/<pose>.png       one frame per pose, 960×600
  <name>-sheet.png        the poses side by side
  <name>-sweep.md         per hand row: the target's value at u = 0, ¼, ½, ¾, 1,
                          then with the hand gone, then never seen
"""

from __future__ import annotations

import argparse
import math
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace import envelope, lfo, sequencer, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer, legacy_layout
from hyperspace.bands import default_params
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.hands import HandSettings, HandsIO
from hyperspace.hands.core import DEFAULT_DOFS, PINCHES, default_range
from hyperspace.library import PRESETS, Library
from hyperspace.lookback import DreamState
from hyperspace.params import Kind, build_registry
from hyperspace.preset import Presets
from hyperspace.render import Renderer, ViewState
from hyperspace.routing import Bindings, Router

OUT = ROOT / "docs" / "plans" / "assets" / "12-presets"
CORPUS = ROOT / "tests" / "corpus" / "presets"      # the presets, as test data
HAND_AXES = tuple(DEFAULT_DOFS)                       # x y z roll pitch yaw
W, H = 960, 600
DT = 1 / 60
SETTLE = 90            # frames a pose is held before the frame is taken
SIDE = {"L": "left", "R": "right"}

# the poses per preset: label → {"<side>.<axis>": u}. A side named at all
# is in the box (its other axes at rest: height 0, the centred ones 0.5);
# a side not named is out of the box.
POSES: dict[str, list[tuple[str, dict[str, float]]]] = {
    "party-tumble": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("L roll thumb-up", {"L.roll": 1}), ("L pitch fingers-up", {"L.pitch": 1}),
        ("L yaw fingers-out", {"L.yaw": 1}), ("L up (drive)", {"L.y": 1}),
        ("R up (speed)", {"R.y": 1}), ("R reach in (4D deep)", {"R.z": 0}),
        ("R pull back (4D flat)", {"R.z": 1}), ("R roll thumb-up (XW)", {"R.roll": 1}),
        ("R yaw fingers-out (ZW)", {"R.yaw": 1}),
    ],
    "party-faces": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("L up (glow)", {"L.y": 1}), ("L roll thumb-up", {"L.roll": 1}),
        ("R up (pattern)", {"R.y": 1}), ("R reach in (zoom)", {"R.z": 0}),
        ("R roll thumb-up (mod 2)", {"R.roll": 1}), ("R roll thumb-down", {"R.roll": 0}),
        ("R pitch fingers-up (mod 3)", {"R.pitch": 1}), ("R pitch fingers-down", {"R.pitch": 0}),
    ],
    "party-field": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("R half up", {"R.y": 0.5}), ("R up (crowd)", {"R.y": 1}),
        ("R roll thumb-up (XW)", {"R.roll": 1}), ("R yaw fingers-out (ZW)", {"R.yaw": 1}),
        ("L up (swing)", {"L.y": 1}), ("L left", {"L.x": 0}), ("L right", {"L.x": 1}),
        ("L reach in", {"L.z": 0}),
    ],
    "party-wake": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("L roll thumb-up", {"L.roll": 1}), ("L up (speed)", {"L.y": 1}),
        ("R up (echoes)", {"R.y": 1}), ("R up + reach in (long)", {"R.y": 1, "R.z": 0}),
        ("R up + pull back (short)", {"R.y": 1, "R.z": 1}),
        ("R roll thumb-up (hue)", {"R.roll": 1}), ("R pitch fingers-up (dream)", {"R.pitch": 1}),
    ],
    "party-trip": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("R up (burst)", {"R.y": 1}), ("R reach in (kaleido zoom)", {"R.z": 0}),
        ("R roll thumb-up (swirl)", {"R.roll": 1}), ("R roll thumb-down", {"R.roll": 0}),
        ("R yaw fingers-out (hues)", {"R.yaw": 1}), ("R pitch fingers-up (plasma)", {"R.pitch": 1}),
        ("L up (pump)", {"L.y": 1}), ("L left + R up", {"L.x": 0, "R.y": 1}),
        ("L reach in + R up", {"L.z": 0, "R.y": 1}),
    ],
    # plan 14 WP6: the legible echoes (in the list, on no F-key)
    "party-tracer": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("L roll thumb-up (turn)", {"L.roll": 1}), ("L up (spin)", {"L.y": 1}),
        ("R up (bright trail)", {"R.y": 1}), ("R reach in (long)", {"R.z": 0}),
        ("R pull back (short)", {"R.z": 1}), ("R roll thumb-up (covered)", {"R.roll": 1}),
        ("R roll thumb-down (through)", {"R.roll": 0}), ("R pitch fingers-up (hard)", {"R.pitch": 1}),
    ],
    # plan 14 WP5: the effect families on F6–F8
    "party-acid": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("R up (heave)", {"R.y": 1}), ("R reach in (rings)", {"R.z": 0}),
        ("R roll thumb-up (twist)", {"R.roll": 1}), ("R pitch fingers-up (split)", {"R.pitch": 1}),
        ("R yaw fingers-out (hues)", {"R.yaw": 1}), ("L up (wobble)", {"L.y": 1}),
        ("L roll thumb-up", {"L.roll": 1}), ("both up", {"L.y": 1, "R.y": 1}),
    ],
    "party-mandala": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("R up (fractals)", {"R.y": 1}), ("R reach in (fold)", {"R.z": 0}),
        ("R pull back", {"R.z": 1}), ("R roll thumb-up (swirl)", {"R.roll": 1}),
        ("R pitch fingers-up (plasma)", {"R.pitch": 1}), ("R yaw fingers-out (cells)", {"R.yaw": 1}),
        ("L up (glints)", {"L.y": 1}), ("L roll thumb-up", {"L.roll": 1}),
    ],
    "party-noita": [
        ("no hands", {}), ("both level", {"L.y": 0, "R.y": 0}),
        ("R half up", {"R.y": 0.5}), ("R up (next stage)", {"R.y": 1}),
        ("R reach in (fine warp)", {"R.z": 0}), ("R roll thumb-up (double)", {"R.roll": 1}),
        ("R pitch fingers-up (pulse)", {"R.pitch": 1}), ("L up (drift)", {"L.y": 1}),
        ("L roll thumb-up", {"L.roll": 1}), ("both up", {"L.y": 1, "R.y": 1}),
    ],
}


class DictSource:
    """latest() like LeapSource, from feature dicts the caller puts."""

    def __init__(self, clock):
        self.clock = clock
        self.seq, self.hands = 0, {}
        self.status, self.on = "fake", True

    def put(self, hands: dict[str, dict[str, float]]) -> None:
        self.seq += 1
        self.hands = {side: (feats, 1.0) for side, feats in hands.items()}

    def latest(self):
        return self.seq, self.clock(), self.hands


class NullOut:
    name = "none"

    def send(self, m):
        pass


def pose_hands(pose: dict[str, float]) -> dict[str, dict[str, float]]:
    """{'left': features, …} for the hands a pose names, at u per axis."""
    out: dict[str, dict[str, float]] = {}
    sides = {k.split(".")[0] for k in pose}
    for s in sides:
        side = SIDE[s]
        feats: dict[str, float] = {}
        for axis in HAND_AXES:
            lo, hi = default_range(side, axis)
            u = pose.get(f"{s}.{axis}", 0.0 if axis == "y" else 0.5)
            feats[axis] = lo + u * (hi - lo)
        feats.update({f"pinch_{f}": 1.0 for f in PINCHES})
        feats.update(grab=0.0, pinch=0.0, grab_angle=0.0, pinch_mm=80.0)
        out[side] = feats
    return out


class Stage:
    """Everything one preset needs: registry, router, hands, clock, LFOs."""

    def __init__(self, name: str, ctx=None, load: str | None = None):
        """`load`: the name the list holds the preset under, when it is not
        a party preset's upper-case slot name (tools/orbit_demo.py)."""
        self.t = 0.0
        self.view = ViewState()
        self.fx, self.dream = FxState(), DreamState()
        chain = Analyzer(Analyser(48_000), default_params(), layout=legacy_layout())
        self.reg = build_registry(self.view, Control(chain), SimpleNamespace(chain=chain),
                                  None, self.dream, self.fx)
        self.clock = tempo.Clock(now=lambda: self.t)
        self.lfos = lfo.LFOs()
        tempo.register(self.reg, self.clock)
        lfo.register(self.reg, self.lfos, self.clock)
        # plan 31: a /7 file carries the envelopes' and the sequencer's values
        envs, seq = envelope.Envelopes(), sequencer.Sequencer()
        envelope.register(self.reg, envs, self.clock)
        sequencer.register(self.reg, seq, self.clock)
        # the preset through the one loader (plan 13 WP2), over a throwaway
        # library home holding the corpus, so nothing touches ~/Hyperspace
        self._home = tempfile.TemporaryDirectory()
        own = Path(self._home.name) / PRESETS
        own.mkdir()
        for f in sorted(CORPUS.glob("*.json")):
            shutil.copyfile(f, own / f.name)
        lib = Library(Path(self._home.name))
        lib.attach(self.reg)
        self.router = Router(self.reg, Bindings())
        self.router.use_bank(envs, self.clock)
        self.router.use_sequencer(seq, envs, self.clock)
        presets = Presets(lib, self.reg, self.router)
        missing = presets.load(load or name.split("-", 1)[1].upper())
        assert not missing and not presets.notes and not self.router.table.dropped, (
            name, missing, presets.notes)
        # the preset's own routes: the table was empty before the load
        self.routes = list(self.router.table.routes())
        self.src = DictSource(lambda: self.t)
        self.io = HandsIO(HandSettings.from_config(), {"enabled": True}, source=self.src,
                          out=NullOut(), clock=lambda: self.t)
        self.clock.trigger(0.0)
        self.renderer = Renderer(ctx, dream=self.dream, fx=self.fx) if ctx is not None else None
        if self.renderer is not None:
            # plan 36 T3: a bare renderer draws the app's empty frame; the
            # preset's graph onto it, as app.py attaches it
            presets.graph.attach(self.renderer)
            errs = self.renderer.fx.compile_all()     # before any frame: a broken shader is a stop
            if errs:
                raise RuntimeError(f"fx shaders failed to build: {errs}")

    def release(self) -> None:
        """Free the renderer's GL objects (one Stage per pose, one context)."""
        r = self.renderer
        if r is not None:
            r.scene.release()
            r.cover.release()
            r.lookback.release_ring()
            r.fx.release_targets()

    def frame(self, hands: dict, fbo=None) -> None:
        """One frame in the app's order: hands → LFOs → modulate → apply → integrate → draw."""
        self.t += DT
        self.src.put(hands)
        self.io.poll(DT, None, self.router)
        self.clock.tick(self.t)
        self.lfos.step(DT, self.t, self.clock)
        self.lfos.publish(self.router)
        self.router.modulate()
        self.reg.apply()
        self.view.integrate(DT)
        if fbo is not None:
            fbo.use()
            self.renderer.ctx.viewport = (0, 0, W, H)
            self.renderer.draw(self.view, W, H, t_now=self.t)

    def hold(self, pose: dict[str, float], frames: int, fbo=None) -> None:
        hands = pose_hands(pose)
        for _ in range(frames):
            self.frame(hands, fbo)


def fmt(p, v) -> str:
    """A reading; a rotation phase as the hand's offset from the base, since
    the integrator keeps turning a live plane underneath the hand."""
    if p.kind is Kind.CONTINUOUS:
        if p.id.startswith("rot.phase"):
            off = math.remainder(v - p.base, 2 * math.pi)
            return f"{math.degrees(off):+.0f}°"
        return p.fmt(v)
    return str(v)


def sweep(name: str, frames: int) -> str:
    """Every hand row of the preset across its axis's throw — the markdown
    table the plan cites. A fresh stage per reading, so nothing carries."""
    rows = [b for b in Stage(name).routes if b.scheme == "hand"]
    us = (0.0, 0.25, 0.5, 0.75, 1.0)
    intro = ("Each cell is the target's value after the hand has held that position "
             f"for {frames} frames ({frames / 60:.1f} s) through the real hand chain "
             "(default feel: dead zone 0.04 on the centred axes, return 0.5 s), then "
             f"*out* is the value {frames} frames after the hand left at u = 1, and "
             "*never* the value when that hand was never seen. The preset's base is "
             "the first column; a rotation phase is shown as the hand's offset from "
             "the base, since a live plane keeps turning underneath.\n")
    lines = [f"# {name} — hand sweeps\n", intro,
             "| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for b in rows:
        # a named hand row (decision register row 20): hand:right.roll
        hand_side, axis = b.source.split(":", 1)[1].split(".")
        side = {v: k for k, v in SIDE.items()}[hand_side]
        vals = []
        for u in us:
            st = Stage(name)
            p = st.reg[b.target]
            base = p.base
            st.hold({f"{side}.{axis}": u}, frames)
            vals.append(fmt(p, p.value))
        st.hold({}, frames)
        out = fmt(p, p.value)
        never = Stage(name)
        never.hold({}, 3)
        pn = never.reg[b.target]
        op = f"{b.op} {b.value:+.3g}" if b.op == "push" else b.op
        base_s = "0°" if b.target.startswith("rot.phase") else fmt(p, base)
        lines.append(f"| {side} {axis} | `{b.target}` | {op} | {base_s} | "
                     + " | ".join(vals) + f" | {out} | {fmt(pn, pn.value)} |")
    return "\n".join(lines) + "\n"


def sheet(tiles: list[tuple[str, Path]], path: Path, cols: int = 4) -> None:
    tw, th = W // 2, H // 2
    rows = (len(tiles) + cols - 1) // cols
    im = Image.new("RGB", (cols * tw, rows * (th + 20)), "black")
    d = ImageDraw.Draw(im)
    for k, (label, p) in enumerate(tiles):
        x, y = (k % cols) * tw, (k // cols) * (th + 20)
        im.paste(Image.open(p).resize((tw, th)), (x, y + 20))
        d.text((x + 6, y + 4), label, fill="white")
    im.save(path)


def shots(name: str, ctx, frames: int) -> None:
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    tiles = []
    for label, pose in POSES[name]:
        st = Stage(name, ctx)
        st.hold({}, 30)                       # the scene settles, the echoes fill
        st.hold(pose, frames, fbo)
        img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1]
        stem = label.replace(" ", "-").replace("(", "").replace(")", "").replace("+", "and")
        p = d / f"{stem.lower()}.png"
        # palette-quantised like the look-back shots, to keep the assets small
        Image.fromarray(img.copy()).quantize(256, method=Image.Quantize.MEDIANCUT,
                                              dither=Image.Dither.FLOYDSTEINBERG).save(p, optimize=True)
        tiles.append((label, p))
        st.release()
    sheet(tiles, OUT / f"{name}-sheet.png")
    print("wrote", (OUT / f"{name}-sheet.png").relative_to(ROOT))
    fbo.release()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--frames", type=int, default=SETTLE)
    ap.add_argument("--no-shots", action="store_true")
    a = ap.parse_args()
    only = {x if x.startswith("party-") else f"party-{x}" for x in a.only.split(",") if x}
    if unknown := only - set(POSES):
        ap.error(f"no such preset: {', '.join(sorted(unknown))} (one of {', '.join(POSES)})")
    OUT.mkdir(parents=True, exist_ok=True)
    ctx = None if a.no_shots else moderngl.create_context(standalone=True)
    for name in POSES:
        if only and name not in only:
            continue
        (OUT / f"{name}-sweep.md").write_text(sweep(name, a.frames))
        print("wrote", (OUT / f"{name}-sweep.md").relative_to(ROOT))
        if ctx is not None:
            shots(name, ctx, a.frames)


if __name__ == "__main__":
    main()
