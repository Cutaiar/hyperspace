"""The migrated look-back draws the old trail's arithmetic.

The old trail pass (`lookback.POST_FS`, since deleted), per echo i oldest
first — ``c = pow(L, contrast)·(1 − darken)``, ``a = w·peak(c)``, ``w =
echo_mix·½^(age / fade)``, ``wake = wake·(1 − a) + c·w`` — held back by
``1 − occlude·min(4·peak(occluder), 1)`` and added under its picture,
``min(under + wake, 1)``, is written here in numpy as the oracle; the patch
`graphmigrate.lookbacks` makes of a look-back (Curve → Fade keyed → Resize →
Delay ═► Trail → Cut by a Matte of the occluder → composite add) is drawn
through the renderer over changing pictures and must equal it to the GPU's
rounding (one level of 255; two where darken is not 0), at a frame size where the Resize (512 on the long
side) is the identity — the old ring's own size (`res` on the short side) is
what the migration changed on purpose (Q24), measured whole-file by
`tools/lookback_proof.py`."""

from __future__ import annotations

import math

import numpy as np
import pytest
from test_graph_faces import _fbo, _px

from hyperspace import graph as G
from hyperspace import graphmigrate
from hyperspace.media.channels import MediaState
from hyperspace.media.frame import MediaFrame
from hyperspace.outputs import Switches, View

moderngl = pytest.importorskip("moderngl")

W, H = 512, 320
DT = 1 / 60
N = 7                       # pictures drawn; the trail at the last holds N − 1


class Frames:
    """A channel source showing picture `i` of its list (stepped by the test)."""

    kind, timed, duration, status = "still", False, 0.0, "ready"

    def __init__(self, pics):
        self.pics, self.i = pics, 0

    def open(self):
        pass

    def close(self):
        pass

    def want(self, t):
        pass

    def latest(self):
        return MediaFrame(self.pics[self.i], 1.0, self.i)


def _pics(seed, n):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        p = rng.integers(0, 256, (H // 8, W // 8, 4), dtype=np.uint8)
        p = np.repeat(np.repeat(p, 8, 0), 8, 1)          # 8-px blocks: no filter between
        p[..., 3] = 255
        out.append(np.ascontiguousarray(p))
    return out


def _migrated(values):
    doc = {"schema": "hyperspace.loadable/12", "name": "t",
           "graph": {"frame": "wired", "nodes": [{"kind": "composite", "blend": "add"}],
                     "wires": [{"from": "channel.a", "to": "lookback.image"},
                               {"from": "channel.b", "to": "lookback.occluder"},
                               {"from": "channel.a", "to": "composite.under"},
                               {"from": "lookback", "to": "composite.over"},
                               {"from": "composite", "to": "output.2.image"},
                               {"from": "shape", "to": "scene.geometry"},
                               {"from": "pattern", "to": "shape.faces"}]},
           "values": dict(values)}
    got, _ = graphmigrate.lookbacks(doc)
    return got


def _land(r, s, doc):
    """The migrated values onto the renderer's states, as a load lands them."""
    from hyperspace.view import CutState, DelayState, KeyState, MatteState, ResizeState
    v = doc["values"]

    def of(prefix):
        return {k[len(prefix):]: x for k, x in v.items() if k.startswith(prefix)
                and "." not in k[len(prefix):]}
    s.delay["delay"] = DelayState(**of("delay."))
    s.resize["resize"] = ResizeState(**of("resize."))
    m = of("matte.")
    m["source"] = m.pop("from")
    s.mattes["matte"] = MatteState(**m)
    s.cuts["cut"] = CutState(**of("cut."))
    s.keys["fade"] = KeyState(**of("key.fade."))
    r.fx.state.on = True
    for eff in ("curve", "fade", "trail"):
        got = of(f"fx.{eff}.")
        if got:
            r.fx.state.values[eff].update(got)


def _oracle(a_pics, occ, under, values, n_held):
    """The old trail pass in float64, oldest first, the newest a frame old."""
    echo_mix, fade = values["dream.echo_mix"], values["dream.fade"]
    darken, contrast = values["dream.darken"], values.get("dream.contrast", 1.0)
    occlude = values["dream.occlude"]
    wake = np.zeros((H, W, 3))
    for k in range(n_held, 0, -1):                 # age k frames
        L = a_pics[-1 - k][..., :3] / 255.0
        c = np.power(np.maximum(L, 1e-6), contrast) * (1.0 - darken)
        w = echo_mix * 0.5 ** (k * DT / fade)
        a = w * c.max(axis=2, keepdims=True)
        wake = wake * (1.0 - a) + c * w
    cover = occlude * np.minimum(4.0 * (occ[..., :3] / 255.0).max(axis=2, keepdims=True), 1.0)
    wake *= 1.0 - cover
    return np.minimum(under[..., :3] / 255.0 + wake, 1.0) * 255.0


@pytest.mark.parametrize("values", [
    {"dream.echo_mix": 0.4, "dream.fade": 0.2252, "dream.darken": 0.1, "dream.occlude": 1.0},
    {"dream.echo_mix": 0.7, "dream.fade": 0.05, "dream.darken": 0.0, "dream.occlude": 0.3},
    {"dream.echo_mix": 1.0, "dream.fade": 10.0, "dream.darken": 0.5, "dream.occlude": 0.0},
], ids=["defaults", "tracer", "long"])
def test_the_migrated_trail_is_the_old_pass(ctx, values):
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    values = {**values, "dream.gap": 0.0, "dream.echoes": 8}
    doc = _migrated(values)
    a, b = Frames(_pics(1, N)), Frames(_pics(2, N))
    by_id = {"file:/fake/a.png": a, "file:/fake/b.png": b}
    media = MediaState(opener=lambda sid, resolver: by_id[sid])
    media.assign("a", 0, "file:/fake/a.png")
    media.assign("b", 0, "file:/fake/b.png")
    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    spec = G.read_graph(doc["graph"], effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    s = ViewState(lines=False, points=False, faces=False)
    _land(r, s, doc)
    for i in range(N):
        a.i = b.i = i
        media.poll(DT, 2.0 + i * DT)
        vs = [View(Switches(), (W, H), target=_fbo(ctx, W, H)) for _ in range(2)]
        r.draw_outputs(s, W, H, 1.0, vs, t_now=2.0 + i * DT)
        assert ctx.error == "GL_NO_ERROR"
    got = _px(vs[1].target)[..., :3]          # (rows top first, as the pictures)
    want = _oracle(a.pics, b.pics[-1], a.pics[-1], values, N - 1)
    d = np.abs(got - want)
    # (to the GPU's rounding; where darken is not 0, the faded picture is held
    # at 8 bits before the delay — the old ring held the picture and darkened
    # each layer in float — so each kept layer may round by half a level more,
    # up to its weight: 2 levels at most over the trail)
    bound = 1.0 if values["dream.darken"] == 0.0 else 2.0
    assert d.max() <= bound + 1e-9, (d.max(), np.unravel_index(d.argmax(), d.shape))
    assert math.isfinite(float(d.mean()))
