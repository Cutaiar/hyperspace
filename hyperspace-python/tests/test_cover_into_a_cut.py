"""Plan 90 (H2, row 1179): `scene.cover` goes into a cut's mask. The faces'
cover pass draws into its own target; the frame's target is bound again after
it, so the nodes after it draw where they should (the migrated acid-scene drew
black before: the cover pass left its own framebuffer bound)."""

from __future__ import annotations

import numpy as np
import pytest
from test_graph_faces import _fbo, _px

from hyperspace import graph as G
from hyperspace.outputs import Switches, View

moderngl = pytest.importorskip("moderngl")

W, H = 160, 100


def _frame(ctx, wires, nodes):
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
    r.fx.state.values["acid"]["on"] = True
    s = ViewState(shape=3, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], faces=True,
                  cuts={"cut": CutState(amount=1.0, invert=True)})
    out = None
    for k in range(3):
        vs = [View(Switches(), (W, H), target=_fbo(ctx, W, H)) for _ in range(2)]
        r.draw_outputs(s, W, H, 1.0, vs, t_now=2.0 + k / 60)
        out = _px(vs[0].target)
    return out


def test_a_cut_by_the_cover_leaves_the_frame_drawn(ctx):
    nodes = [{"kind": "effect", "file": "acid"}, {"kind": "cut"},
             {"kind": "composite", "blend": "add"}]
    base = [{"from": "scene", "to": "composite.under"}, {"from": "composite", "to": "acid.image"},
            {"from": "acid", "to": "output.all.image"}]
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
