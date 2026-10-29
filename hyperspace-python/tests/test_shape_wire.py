"""The shape node's wireframe on GRAPH's side panel: the renderer draws the
shape's edges alone, white on black, into a square of its own at the end of
a frame (`Renderer.want_wire`, `_wire`) while the page asks, and frees it a
second after; the page shows it when the shape node is selected
(`ui_graph._wireframe`). No output pixel moves for it."""

from __future__ import annotations

from types import SimpleNamespace as NS

import numpy as np
from conftest import seed
from test_thumbnails import SIZE, S, _px, _renderer, _views, ctx  # noqa: F401 — the GL fixture
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graphview, render, ui_graph
from hyperspace import hold as holdmod


def _rgba(tex) -> np.ndarray:
    w, h = tex.size
    return np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4)


def test_the_outputs_are_byte_identical_with_and_without_the_wireframe(ctx):  # noqa: F811
    """Three frames with the wireframe asked for give the same bytes on both
    outputs, and the same counts, as three without."""
    plain, wired = _renderer(ctx), _renderer(ctx)
    pv, wv = _views(ctx), _views(ctx)
    for k in range(3):
        t = 2.0 + k / 60
        plain.draw_outputs(S, *SIZE, 1.0, pv, t_now=t)
        wired.want_wire(128)
        wired.draw_outputs(S, *SIZE, 1.0, wv, t_now=t)
        assert ctx.error == "GL_NO_ERROR"
        for a, b in zip(pv, wv, strict=True):
            assert np.array_equal(_px(a.target), _px(b.target)), k
        assert plain.stats["effects"] == wired.stats["effects"]
    assert plain.wire_texture() is None and wired.wire_texture() is not None
    assert not getattr(wired, "wire_error", "")


def test_the_wireframe_is_the_shapes_edges_white_on_black(ctx):  # noqa: F811
    """The square is opaque black with grey-to-white lines on it — no
    faces' colour, no red points — and turns with the shape."""
    r, views = _renderer(ctx), _views(ctx)
    r.want_wire(128)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    tex = r.wire_texture()
    assert tuple(tex.size) == (128, 128)
    px = _rgba(tex).astype(int)
    assert (px[..., 3] == 255).all()                         # opaque: over black
    lit = px[..., :3].max(axis=2) > 24
    assert 0.01 < lit.mean() < 0.6                           # lines, not a fill
    assert px[..., :3].max() > 150                           # some of them bright
    rgb = px[lit][:, :3]
    assert (rgb.max(axis=1) - rgb.min(axis=1)).max() <= 2    # grey: no colour at all
    corners = px[[0, 0, -1, -1], [0, -1, 0, -1], :3]
    assert (corners == 0).all()                              # black ground
    turned = render.ViewState(**{**S.__dict__, "ang": [1.3, 0.2, 0.4, 1.9, 0.1, 0.6]})
    r.want_wire(128)
    r.draw_outputs(turned, *SIZE, 1.0, views, t_now=2.1)
    assert not np.array_equal(_rgba(r.wire_texture()).astype(int), px)


def test_the_wireframe_follows_its_size_and_is_dropped_unasked(ctx, monkeypatch):  # noqa: F811
    """Its square is the size asked (clamped); not asked for `WIRE_DROP_S`,
    its texture is freed; a hot reload frees it too."""
    r, views = _renderer(ctx), _views(ctx)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    assert r.wire_texture() is None                          # never asked: nothing made
    r.want_wire(64)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    assert tuple(r.wire_texture().size) == (64, 64)
    r.want_wire(96)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.2)
    assert tuple(r.wire_texture().size) == (96, 96)
    r.want_wire(10 ** 6)
    assert r.wire_asked[0] == render.WIRE_PX_MAX
    r.want_wire(96)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.3)
    monkeypatch.setattr(render, "WIRE_DROP_S", 0.0)          # a second has gone by
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.4)
    assert r.wire_texture() is None and r.wire_asked is None
    monkeypatch.setattr(render, "WIRE_DROP_S", 1.0)
    r.want_wire(96)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.5)
    assert r.wire_texture() is not None
    r.on_reload()
    assert r.wire_texture() is None


def test_wire_px_is_the_box_in_framebuffer_px():
    assert ui_graph.wire_px(260.0, 1.0) == 260
    assert ui_graph.wire_px(260.0, 2.0) == 520               # a Retina screen: 1:1, sharp
    assert ui_graph.wire_px(4.0, 1.0) == 16


def test_only_the_shape_nodes_details_ask_for_the_wireframe(shell_rig, monkeypatch):  # noqa: F811
    """The shape node selected on GRAPH asks the canvas's renderer for its
    wireframe at the box's size; another node's details do not."""
    seed(shell_rig.lib.home)
    panel = shell_rig.panel
    frame(panel, "graph")
    st = ui_graph._state(panel)
    asked: list[int] = []
    stub = NS(want_wire=asked.append, wire_texture=lambda: None)
    monkeypatch.setattr(holdmod, "canvas_renderer", lambda p: stub)
    from imgui_bundle import imgui
    shape = st["view"].node("render:shape")
    got = []
    for n in (shape, graphview.VNode("device:pad", "device", "pad")):
        asked.clear()
        imgui.new_frame()
        imgui.set_next_window_size(imgui.ImVec2(400, 600))
        imgui.begin("side")
        ui_graph._side(panel, st, st["view"], ("node", n))
        imgui.end()
        imgui.end_frame()
        got.append(list(asked))
    assert len(got[0]) == 1 and 16 <= got[0][0] <= ui_graph.WIRE_MAX
    assert got[1] == []
