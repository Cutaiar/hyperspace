"""Trip warp as a patch — `noise (flow) × rings → scale`, `point →
scale.2`, added (`combine.2`) → Displace — **near, not equal** to `warp.glsl`
(`tests/trippatch.py` says why). warp.glsl stays and draws every saved Trip warp look as it did.

What is held:

- **The push is the formula.** Read back, the patch's push is, to float32,
  `(uv − ½)(s − 1) + flow × 0.2 Amount × r × (H/W, 1)` in frame fractions,
  with `flow` the file's two drifting octaves (Noise's Out flow, the same
  clock), `s − 1` the file's zoom and `r` the distance from the middle in frame
  heights. The file reads `r` in fractions of the frame instead (`length(uv −
  ½)`): equal on the frame's axes, apart toward the corners (the patch's swim
  up to about a quarter more up and down there). The zoom is the file's.
- **Amount 0 is the picture,** byte for byte, in both.
- **How far apart they look,** on a smooth picture (a picture of speckle
  exaggerates a sub-pixel move): a mean of about 1.7 levels at Amount 1, held
  to `2 × Amount + 0.1`."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace.fx import FxChain, FxState

sys.path.insert(0, str(Path(__file__).parent))
from trippatch import INSTANCES, trip_patch

moderngl = pytest.importorskip("moderngl")

W, H = 96, 64
TIMES = (0.0, 0.41, 2.7)
LOOKS = [{"amount": 0.0}, {"amount": 0.2}, {"amount": 0.5}, {"amount": 1.0}, {"amount": 2.0},
         {"amount": 0.5, "scale": 12.0}, {"amount": 0.5, "drift": 4.0}, {"amount": 0.7, "speed": 1.0}]


def _smooth():
    yy, xx = np.mgrid[0:H, 0:W]
    return np.stack([128 + 100 * np.sin(xx / 9.0), 128 + 100 * np.cos(yy / 7.0),
                     128 + 60 * np.sin((xx + yy) / 11.0), np.full_like(xx, 255.0)],
                    -1).astype(np.uint8)


class _Rig:
    def __init__(self, ctx):
        self.ctx = ctx
        self.f = {k: ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4, dtype="f4")])
                  for k in ("pt", "fl", "r", "c", "s", "s2", "c2")}
        self.a = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4, dtype="f1")])
        self.b = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4, dtype="f1")])

    def tex(self, k):
        return self.f[k].color_attachments[0]

    def field(self, k):
        return np.frombuffer(self.f[k].read(components=4, dtype="f4"), np.float32).reshape(H, W, 4)

    def run(self, look, src, t):
        ws = FxState()
        ws.values["warp"].update(on=True, mix=1.0, **look)
        v = dict(ws.values["warp"])
        ps = FxState()
        ps.set_instances(INSTANCES)
        for n, vals in trip_patch(v).items():
            ps.values[n].update(vals)
        wc, pc = FxChain(self.ctx, ws), FxChain(self.ctx, ps)
        wc.run_one("warp", src, self.a, t, opaque=1)
        for n, k in (("point", "pt"), ("noise", "fl"), ("rings", "r")):
            pc.run_one(n, src, self.f[k], t, opaque=1, res=(W, H))
        pc.run_one("combine", self.tex("fl"), self.f["c"], t, opaque=1, field=self.tex("r"))
        pc.run_one("scale", self.tex("c"), self.f["s"], t, opaque=1)
        pc.run_one("scale.2", self.tex("pt"), self.f["s2"], t, opaque=1)
        pc.run_one("combine.2", self.tex("s"), self.f["c2"], t, opaque=1, field=self.tex("s2"))
        pc.run_one("displace", src, self.b, t, opaque=1, field=self.tex("c2"))
        assert wc.errors == {} and pc.errors == {} and self.ctx.error == "GL_NO_ERROR"
        wc.release()
        pc.release()
        pic = [np.frombuffer(fb.read(components=4), np.uint8).reshape(H, W, 4).astype(int)
               for fb in (self.a, self.b)]
        return v, pic[0], pic[1]


def test_the_patch_pushes_by_the_formula_it_says(ctx):
    rig, src = _Rig(ctx), ctx.texture((W, H), 4, _smooth().tobytes())
    uv = np.stack(np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H), -1)
    for look in LOOKS:
        for t in TIMES:
            v, _, _ = rig.run(look, src, t)
            a = v["amount"]
            s1 = -0.1 * min(1.0, 1.5 * a)
            flow = rig.field("fl")[..., :2]
            r = np.hypot((uv[..., 0] - 0.5) * W / H, uv[..., 1] - 0.5)
            want = (uv - 0.5) * s1 + flow * 0.2 * a * r[..., None] * np.array([H / W, 1.0])
            got = rig.field("c2")[..., :2] * 0.5 * np.array([H / W, 1.0])   # Displace's 0.5
            assert np.allclose(got, want, atol=1e-5), (look, t, float(np.abs(got - want).max()))


def test_amount_zero_is_the_picture_in_both(ctx):
    rig = _Rig(ctx)
    pic = _smooth()
    src = ctx.texture((W, H), 4, pic.tobytes())
    for t in TIMES:
        _, a, b = rig.run({"amount": 0.0}, src, t)
        assert np.array_equal(a, b) and np.array_equal(a, pic.astype(int))


def test_the_patch_looks_near_the_file(ctx):
    rig, src = _Rig(ctx), ctx.texture((W, H), 4, _smooth().tobytes())
    for look in LOOKS:
        for t in TIMES:
            v, a, b = rig.run(look, src, t)
            mean = float(np.abs(a - b)[..., :3].mean())
            assert mean <= 2.0 * v["amount"] + 0.1, (look, t, mean)
