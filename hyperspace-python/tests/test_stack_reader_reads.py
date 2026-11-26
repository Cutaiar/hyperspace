"""Plan 90 (H2): a stack reader (Trail, Read: `@takes image none`) reads what
its stack's delay reads — so a node that asks whether its picture reads
anything (a Cut, a Matte) takes the trail, as the migrated look-back's Cuts do.
Before, an effect with no picture wired read only if it generated."""

from __future__ import annotations

import numpy as np
import pytest
from test_graph_faces import Still, _media
from test_graph_masks import _draw, _renderer

from hyperspace.view import ViewState

moderngl = pytest.importorskip("moderngl")

TRAIL = {"kind": "effect", "file": "trail"}
CUT = {"kind": "cut"}
DELAY = {"kind": "delay"}


def _white(w=64, h=48):
    px = np.full((h, w, 4), 255, np.uint8)
    return px


@pytest.mark.parametrize("reader", ["trail", "read"])
def test_a_stack_reader_into_a_cut_reads(ctx, reader):
    pairs = [("channel.a", "delay.image"), ("delay", f"{reader}.stack"),
             (reader, "cut.image"), ("cut", "output.2.image")]
    nodes = (DELAY, {"kind": "effect", "file": reader}, CUT)
    r = _renderer(ctx, _media(a=Still(_white())), pairs=pairs, nodes=nodes)
    s = ViewState(lines=False, points=False, faces=False)
    r.fx.state.on = True
    r.fx.state.values[reader]["on"] = True
    for _ in range(4):
        out = _draw(ctx, r, s)
    assert r._graph.nodes["cut"].said != "its picture reads nothing"
    assert out[..., :3].max() > 0
