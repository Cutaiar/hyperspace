"""Plan 90 (H2, row 1179): `scene.cover` goes into a cut's mask (a migrated
look-back's second Cut takes it, H2c). A cut is made in its own `run`, in order,
where it is read at the frame's size — never pulled half-way through another
node's pass (its mask pass binds its own target and texture units): a
trail cut by the cover under Plasma drew black."""

from __future__ import annotations

import numpy as np
import pytest
from test_graph_faces import _fbo, _px

from hyperspace import graph as G
from hyperspace.outputs import Switches, View

moderngl = pytest.importorskip("moderngl")

W, H = 160, 100


def _frame(ctx, wires, nodes, delay=False):
    from hyperspace.render import Renderer
    from hyperspace.view import CutState, ViewState

    r = Renderer(ctx)
    r.ghost.state.on = False
    spec = G.read_graph({"frame": "wired", "nodes": nodes,
                         "wires": [{"from": "shape", "to": "scene.geometry"},
                                   {"from": "pattern", "to": "shape.faces"}, *wires]},
                        effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    r.fx.state.values["plasma"].update(on=True, level=0.0)
    if delay:
        r.fx.state.values["trail"].update(on=True, level=1.0, fade=10.0)
    from hyperspace.view import DelayState
    s = ViewState(shape=3, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], faces=True,
                  cuts={"cut": CutState(amount=1.0, invert=True)})
    if delay:
        s.delay["delay"] = DelayState(depth=4)
    out = None
    for k in range(3):
        vs = [View(Switches(), (W, H), target=_fbo(ctx, W, H)) for _ in range(2)]
        r.draw_outputs(s, W, H, 1.0, vs, t_now=2.0 + k / 60)
        out = _px(vs[0].target)
    return out


def test_a_cut_by_the_cover_leaves_the_frame_drawn(ctx):
    nodes = [{"kind": "effect", "file": "plasma"}, {"kind": "cut"},
             {"kind": "composite", "blend": "add"}]
    base = [{"from": "scene", "to": "composite.under"}, {"from": "composite", "to": "plasma.image"},
            {"from": "plasma", "to": "output.all.image"}]
    cut = [{"from": "scene", "to": "cut.image"}, {"from": "scene.cover", "to": "cut.mask"},
           {"from": "cut", "to": "composite.over"}]
    alone = _frame(ctx, base, nodes)
    with_cut = _frame(ctx, base + cut, nodes)
    lit = (alone[..., :3].max(axis=2) > 8).mean()
    assert lit > 0.05
    # (the cut adds on: never darker than the picture under it)
    assert (with_cut[..., :3] >= alone[..., :3] - 1).all()
    assert (with_cut[..., :3].max(axis=2) > 8).mean() >= lit
    assert np.isfinite(with_cut).all()


def test_a_trail_cut_by_the_cover_under_an_effect_is_drawn(ctx):
    """The migrated look-back's shape: a delay's trail, cut by the faces'
    cover, added on the scene, an effect after (Plasma at level 0: the
    picture as it is)."""
    nodes = [{"kind": "effect", "file": "plasma"}, {"kind": "effect", "file": "trail"},
             {"kind": "delay"}, {"kind": "cut"}, {"kind": "composite", "blend": "add"}]
    base = [{"from": "scene", "to": "composite.under"}, {"from": "composite", "to": "plasma.image"},
            {"from": "plasma", "to": "output.all.image"}, {"from": "scene", "to": "delay.image"},
            {"from": "delay", "to": "trail.stack"}, {"from": "trail", "to": "cut.image"},
            {"from": "cut", "to": "composite.over"}]
    alone = _frame(ctx, base, nodes, delay=True)
    with_cover = _frame(ctx, [*base, {"from": "scene.cover", "to": "cut.mask"}], nodes,
                        delay=True)
    lit = (alone[..., :3].max(axis=2) > 8).mean()
    assert lit > 0.05
    assert (with_cover[..., :3].max(axis=2) > 8).mean() > 0.5 * lit, "drawn black"
