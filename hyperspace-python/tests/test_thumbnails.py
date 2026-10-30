"""Plan 37 C1 (P1, D2): nodes are pictures — a live thumbnail on every
picture node of the GRAPH page.

`outputs.PreviewTextures` keeps a small texture per node name, made at
the end of the frame after the page wanted it (`Renderer._thumbnails`,
from `render.thumb_source`), dropped when not wanted for a second; a node
that made nothing shows its last thumbnail dimmed, then black. The page
wants only the picture nodes it draws on screen (`ui_graph.thumb_wants`).
What the outputs show is the same, byte for byte, with thumbnails wanted
or not (no golden moves)."""

from __future__ import annotations

from types import SimpleNamespace as NS

import numpy as np
import pytest
from conftest import seed
from test_graph_legible import party as _party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import graphview, render, ui_graph
from hyperspace.graphmigrate import wired_wiring
from hyperspace.outputs import (
    THUMB_BLACK_S,
    THUMB_DROP_S,
    THUMB_PX,
    PreviewTextures,
    Switches,
    View,
    thumb_size,
)
from hyperspace.view import ViewState


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t

def party(rig):
    """`test_graph_legible.party` over the corpus: party-trip is test data
    since 2026-10-28, seeded into the rig's home first (never over a file)."""
    seed(rig.lib.home, "presets")
    return _party(rig)


def _frame(th: PreviewTextures, made: dict) -> None:
    """One renderer frame's end as `Renderer._thumbnails` runs it: what was
    wanted, `put` from `made` (name → a picture's size, or absent: nothing)."""
    wanted = th.take()
    th.begin_frame()
    for name in wanted:
        if name in made:
            th.put(name, NS(size=made[name]))
    th.end_frame()


# ---------------------------------------------------------------- the model, no GL

def test_wanted_is_made_next_frame_and_dropped_after_a_second_unwanted():
    clock = Clock()
    th = PreviewTextures(None, clock)
    _frame(th, {"acid": (1920, 1080)})
    assert th.kept == 0 and th.count == 0           # nothing wanted: nothing made
    th.want({"acid": "picture"})
    assert th.wanted == {"acid": "picture"}
    _frame(th, {"acid": (1920, 1080)})
    assert th.count == 1 and th.kept == 1 and th.shade("acid") == 1.0
    assert th.size_of("acid") == (1920, 1080)
    clock.t += THUMB_DROP_S - 0.1                    # unwanted, not yet a second
    _frame(th, {"acid": (1920, 1080)})
    assert th.kept == 1 and th.count == 0           # kept, not copied: not wanted
    clock.t += 0.2
    _frame(th, {"acid": (1920, 1080)})
    assert th.kept == 0 and th.size_of("acid") is None and th.shade("acid") == 0.0
    th.want(["acid"])                                # wanted again: made again
    _frame(th, {"acid": (960, 540)})
    assert th.count == 1 and th.size_of("acid") == (960, 540) and th.shade("acid") == 1.0


def test_a_node_that_made_nothing_is_dimmed_then_black_after_a_second():
    clock = Clock()
    th = PreviewTextures(None, clock)
    th.want({"acid": "picture"})
    _frame(th, {"acid": (64, 64)})
    assert th.shade("acid") == 1.0
    th.want({"acid": "picture"})
    clock.t += 0.1
    _frame(th, {})                                   # wanted, made nothing
    assert th.count == 0 and th.kept == 1
    assert th.shade("acid") == PreviewTextures.DIM   # a flag the page reads, not a copy
    clock.t += THUMB_BLACK_S
    th.want({"acid": "picture"})
    _frame(th, {})
    assert th.shade("acid") == 0.0
    th.want({"acid": "picture"})                     # it makes one again: lit again
    _frame(th, {"acid": (64, 64)})
    assert th.shade("acid") == 1.0


def test_the_count_is_this_frames_copies():
    th = PreviewTextures(None, Clock())
    th.want({"a": "picture", "b": "picture", "c": "picture"})
    _frame(th, {"a": (8, 8), "b": (8, 8)})
    assert (th.count, th.kept) == (2, 2)          # c wanted, never made: none kept
    th.want({"a": "picture"})
    _frame(th, {"a": (8, 8)})
    assert th.count == 1


def test_a_thumbnails_size_is_its_long_side_at_the_pictures_aspect():
    assert THUMB_PX == 192
    assert thumb_size((1920, 1080)) == (192, 108)
    assert thumb_size((600, 800)) == (144, 192)
    assert thumb_size((1920, 1)) == (192, 1)
    assert thumb_size((96, 64)) == (96, 64)          # never above the picture


# ---------------------------------------------------------------- the table

def test_every_picture_kind_has_a_thumbnail_and_the_modulation_side_none():
    # (plan 39's segment pins `fg`/`bg` are ports of the one segment node,
    # never a canvas node of their own, as the scene's depth pin is)
    for kind, made in G.WIRED_MAKES.items():
        if made == G.IMAGE and kind not in (G.GROUND, G.DEPTH_PORT, *G.SEGMENT_PINS):
            assert graphview.THUMBS[kind] == graphview.PICTURE, kind
    # plan 39: a matte makes a mask and a segment's own output is its matte: text
    assert graphview.thumb_of("matte", G.MatteNode("matte")) is None
    assert graphview.thumb_of("segment", G.SegmentNode("segment")) is None
    assert graphview.THUMBS["shape"] == graphview.THUMBS["cloud"] == graphview.SCENE_PIC
    assert graphview.THUMBS["hands"] == graphview.LAYER_PIC
    assert graphview.thumb_of("output.2") == graphview.WINDOW_PIC
    assert graphview.thumb_of(G.ALL_OUTPUTS) is None
    assert graphview.thumb_of(graphview.CAMERA) is None
    assert graphview.thumb_of("lfo.1") is None and graphview.thumb_of("mod.1") is None
    # a kind the table does not name (plan 39's, say) whose node makes a picture
    assert graphview.thumb_of("acid.3", G.Effect("acid.3")) == graphview.PICTURE


# ---------------------------------------------------------------- the renderer


SIZE = (96, 64)


def _wire(*pairs, nodes=()):
    return wired_wiring(G.read_graph({"frame": "wired", "nodes": list(nodes),
                                      "wires": [{"from": a, "to": b} for a, b in pairs]}
                                     ).wiring())


def _renderer(ctx):
    r = render.Renderer(ctx)
    r.ghost.state.on = False
    r.fx.state.values["kaleido"].update(on=True, mix=1.0)
    assert not r.fx.compile_all()
    # the scene through an effect to output 1; into output 2 a composite of
    # that effect a frame late (a delay) under the look-back's trail picked
    # by a switch: painted and made nodes, and the stateful kinds
    r.wiring = _wire(("shape", "scene.geometry"), ("scene", "kaleido.image"),
                     ("kaleido", "output.1.image"), ("kaleido", "delay.image"),
                     ("delay", "composite.under"), ("scene", "lookback.image"),
                     ("lookback", "switch.in1"), ("switch", "composite.over"),
                     ("composite", "output.2.image"),
                     nodes=({"kind": "effect", "file": "kaleido"}, {"kind": "composite"},
                            {"kind": "delay"}, {"kind": "switch"}))
    return r


def _views(ctx):
    one = ctx.framebuffer(color_attachments=[ctx.renderbuffer(SIZE, 4)])
    two = ctx.framebuffer(color_attachments=[ctx.texture(SIZE, 4)])   # publish-only
    return [View(Switches(), SIZE, target=one), View(Switches(), SIZE, target=two)]


def _px(fbo) -> np.ndarray:
    return np.frombuffer(fbo.read(components=4), np.uint8).copy()


S = ViewState(shape=10, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25,
              faces=True, pattern=2)
S.switch = {"switch": 1}
EVERY = {"shape": "scene", "scene": "picture", "kaleido": "picture",
         "composite": "picture", "output.2": "window", "delay": "picture",
         "lookback": "picture", "switch": "picture"}


def test_the_outputs_are_byte_identical_with_and_without_thumbnails(ctx):
    """No golden moves: three frames drawn with every node's thumbnail
    wanted give the same bytes, on both outputs, as three without — and the
    frame's own counts and GPU lines are the frame's."""
    plain, wanted = _renderer(ctx), _renderer(ctx)
    pv, wv = _views(ctx), _views(ctx)
    for k in range(3):
        t = 2.0 + k / 60
        plain.draw_outputs(S, *SIZE, 1.0, pv, t_now=t)
        wanted.thumbs.want(EVERY)
        wanted.draw_outputs(S, *SIZE, 1.0, wv, t_now=t)
        assert ctx.error == "GL_NO_ERROR"
        for a, b in zip(pv, wv, strict=True):
            assert np.array_equal(_px(a.target), _px(b.target)), k
        assert plain.stats["effects"] == wanted.stats["effects"]
        assert plain.stats["chain_runs"] == wanted.stats["chain_runs"]
    assert wanted.thumbs.count == len(EVERY) and plain.thumbs.count == 0
    assert 0 < wanted.thumbs.repainted < len(EVERY)     # some made, some painted again
    assert set(wanted.thumbs.tex) == set(EVERY) and not plain.thumbs.tex
    # the GPU timer took no query for the thumbnails' passes
    timer = wanted.timer
    if timer is not None and timer.on:
        assert not timer._frame and not getattr(timer, "_active", False)


def test_graph_picture_is_asked_only_for_the_wanted_nodes(ctx, monkeypatch):
    asked: list[str] = []
    real = render.picture

    def counting(frame, node, *a, **kw):
        asked.append(node.name)
        return real(frame, node, *a, **kw)

    monkeypatch.setattr(render, "picture", counting)
    r, views = _renderer(ctx), _views(ctx)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    assert asked == []                          # nothing wanted: nothing asked
    r.thumbs.want({"kaleido": "picture"})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    assert asked == ["kaleido"]
    asked.clear()
    r.thumbs.want({"shape": "scene"})           # a geometry: its scene's picture
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.2)
    assert asked == ["scene"]
    asked.clear()
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.3)
    assert asked == []


def test_a_thumbnail_is_the_pictures_aspect_and_shows_it(ctx):
    r, views = _renderer(ctx), _views(ctx)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    r.thumbs.want(EVERY)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    tex = r.thumbs.get("composite")
    assert tex is not None and tuple(tex.size) == thumb_size(SIZE)
    assert r.thumbs.size_of("composite") == SIZE
    # output 2's thumbnail is what output 2 shows, made small
    out = np.frombuffer(views[1].target.color_attachments[0].read(), np.uint8).reshape(
        SIZE[1], SIZE[0], 4)[..., :3].astype(float)
    th = np.frombuffer(r.thumbs.get("output.2").read(), np.uint8).reshape(
        SIZE[1], SIZE[0], 4)
    assert (th[..., 3] == 255).all()            # opaque: the picture over black
    assert abs(th[..., :3].mean() - out.mean()) < 4.0
    assert out.mean() > 1.0                     # (the frame draws something)


def test_a_node_not_built_or_not_drawing_makes_nothing(ctx):
    r, views = _renderer(ctx), _views(ctx)
    r.thumbs.want({"acid.2": "picture", "hands": "layer", "output.1": "window",
                   "channel.a": "picture"})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    r.thumbs.want({"acid.2": "picture", "hands": "layer", "output.1": "window",
                   "channel.a": "picture"})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    assert r.thumbs.count == 0 and not r.thumbs.tex and not r.thumbs.error
    assert r.thumbs.shade("acid.2") == 0.0


def test_a_hot_reload_drops_the_thumbnails_and_makes_them_again(ctx):
    r, views = _renderer(ctx), _views(ctx)
    r.thumbs.want({"scene": "picture"})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    assert r.thumbs.count == 1
    r.on_reload()
    assert r.thumbs is None
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    assert r.thumbs is not None and r.thumbs.count == 0


# ---------------------------------------------------------------- the page

@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def test_the_page_wants_the_picture_nodes_it_draws_on_screen(rig):
    st = party(rig)
    view = st["view"]
    pics = [n for n in view.nodes if n.thumb is not None]
    assert pics and any(n.thumb == graphview.SCENE_PIC for n in pics)
    everywhere = ((-1e9, -1e9), (1e9, 1e9))
    st["seen_rect"] = everywhere
    st["preset_only"] = False
    st["hide"] = ui_graph.hidden_ids(st, view)
    got = ui_graph.thumb_wants(st, view, lambda nid: ((0.0, 0.0), (10.0, 10.0)))
    drawn = {ui_graph.thumb_name(n) for n in pics
             if ui_graph.drawn_node(st, n) and not ui_graph.by_preview(n)}
    assert set(got) == drawn and drawn
    assert "output.1" not in got                 # output 1 is the page's Preview
    # off screen: nothing
    st["seen_rect"] = ((5000.0, 5000.0), (6000.0, 6000.0))
    assert ui_graph.thumb_wants(st, view, lambda nid: ((0.0, 0.0), (10.0, 10.0))) == {}
    # hidden by preset only: not wanted (and so never copied)
    st["seen_rect"] = everywhere
    st["preset_only"] = True
    st["hide"] = ui_graph.hidden_ids(st, view)
    hidden = {ui_graph.thumb_name(n) for n in pics if n.id in st["hide"]}
    assert hidden
    got = ui_graph.thumb_wants(st, view, lambda nid: ((0.0, 0.0), (10.0, 10.0)))
    assert not hidden & set(got)


def test_on_screen_is_any_overlap():
    rect = ((0.0, 0.0), (100.0, 100.0))
    assert ui_graph.on_screen(rect, (90.0, 90.0), (50.0, 50.0))
    assert not ui_graph.on_screen(rect, (100.0, 0.0), (50.0, 50.0))
    assert not ui_graph.on_screen(rect, (-60.0, 10.0), (50.0, 50.0))
    assert ui_graph.on_screen(rect, (-40.0, -40.0), (200.0, 200.0))


def test_the_page_draws_a_thumbnail_on_every_picture_node_collapsed_or_not(rig, monkeypatch):
    """Headless draw: each picture node drawn asks for its body's picture
    (`_body_of`), collapsed and expanded (D2), wants its thumbnail, and a
    picture node's lines are gone from its body; a text node draws as
    before."""
    st = party(rig)
    view = st["view"]
    th = PreviewTextures(None)
    rig.panel.renderer.thumbs = th
    asked: list[str] = []
    real = ui_graph._body_of
    monkeypatch.setattr(ui_graph, "_body_of",
                        lambda st_, n: (asked.append(n.id), real(st_, n))[1])
    lines: list[str] = []
    real_disabled = ui_graph.imgui.text_disabled
    monkeypatch.setattr(ui_graph.imgui, "text_disabled",
                        lambda s: (lines.append(s), real_disabled(s)))
    # a picture to draw for one node: a texture-shaped stand-in
    scene = view.node("render:scene")
    assert scene is not None and scene.thumb == graphview.PICTURE
    th.tex["scene"] = (NS(glo=7, size=(192, 108)), None)
    th.sizes["scene"], th.made_in["scene"], th.frame = (1920, 1080), 1, 1
    st["pan"] = (-1600.0, 0.0)                  # the scene's column on the small canvas
    frame(rig.panel, "graph")
    drawn_pics = {n.id for n in view.nodes
                  if n.thumb is not None and ui_graph.drawn_node(st, n)}
    assert drawn_pics and drawn_pics <= set(asked)
    # wanted for the next frame: the ones on screen, the scene among them
    rect = st["seen_rect"]
    on = {ui_graph.thumb_name(view.node(nid)) for nid in drawn_pics
          if not ui_graph.by_preview(view.node(nid))
          and ui_graph.on_screen(rect, *ui_graph._where(st, nid))}
    assert "scene" in th.wanted and set(th.wanted) == on
    assert "output.1" not in th.wanted and "composite" not in th.wanted   # off screen
    assert scene.picture == (1920, 1080)        # the hook C2's hover reads
    for nid in drawn_pics:
        for line in graphview.summary(view.node(nid)):
            assert line not in lines or any(
                line in graphview.summary(m) for m in view.nodes
                if m.thumb is None and ui_graph.drawn_node(st, m)), (nid, line)
    asked.clear()
    ui_graph.toggle_open(st, "render:scene")        # expanded: the thumbnail stays
    frame(rig.panel, "graph")
    assert "render:scene" in asked


def test_the_system_page_says_the_thumbnails(rig, monkeypatch):
    import hyperspace.ui as ui_mod

    th = PreviewTextures(None)
    th.want({"a": "picture", "b": "picture"})
    _frame(th, {"a": (8, 8)})
    rig.panel.renderer = NS(thumbs=th, stats={})
    assert ui_graph.thumbnail_line(rig.panel) == "thumbnails · 1 copied · 0 repainted · 1 kept"
    drawn: list[str] = []
    real = ui_mod.imgui.text_disabled
    monkeypatch.setattr(ui_mod.imgui, "text_disabled", lambda s: (drawn.append(s), real(s)))
    frame(rig.panel, "system")
    assert "thumbnails · 1 copied · 0 repainted · 1 kept" in drawn
    rig.panel.renderer = None
    assert ui_graph.thumbnail_line(rig.panel) == ""


def test_a_node_behind_an_unpicked_switch_input_is_not_made(ctx):
    """Review: a composite only the switch's unpicked input reads made
    nothing this frame (plan 33 S) — its thumbnail is not copied, its
    channel is not read for it, and it dims, then goes black a second
    later; picked again, it is copied again."""
    from test_graph_faces import Still, _media, _rgba
    from test_graph_switch import section

    m = _media(a=Still(_rgba(16, 9, (255, 0, 0))), b=Still(_rgba(16, 9, (0, 0, 255))))
    r = render.Renderer(ctx)
    r.ghost.state.on = False
    r.media = m
    spec = G.read_graph(section(("frame", "fx.image"), ("media.a", "composite.under"),
                                ("scene", "composite.over"), ("composite", "switch.in2"),
                                ("media.b", "switch.in1"), ("switch", "output.1.image"),
                                nodes=[{"kind": "composite"}, {"kind": "switch"}]))
    assert not spec.notes, spec.notes
    r.wiring = wired_wiring(spec.wiring())
    clock = Clock()
    r.thumbs.clock = clock
    views = _views(ctx)[:1]
    s = ViewState(lines=False, points=False, faces=False)
    s.switch = {"switch": 2}                    # picked: made, copied
    r.thumbs.want({"composite": "picture"})
    r.draw_outputs(s, *SIZE, 1.0, views, t_now=2.0)
    assert r.thumbs.count == 1 and r.thumbs.shade("composite") == 1.0
    s.switch = {"switch": 1}                    # unpicked: nothing made for it
    for k in range(2):
        clock.t += 0.1
        r.thumbs.want({"composite": "picture"})
        r.draw_outputs(s, *SIZE, 1.0, views, t_now=2.1 + k / 60)
        assert r.thumbs.count == 0, k
        assert {key for key in r._media_now if key[0] == "raw"} == {("raw", "b")}
        assert "composite" not in r.stats.get("effects", [])
    assert r.thumbs.shade("composite") == PreviewTextures.DIM
    clock.t += THUMB_BLACK_S
    r.thumbs.want({"composite": "picture"})
    r.draw_outputs(s, *SIZE, 1.0, views, t_now=2.2)
    assert r.thumbs.count == 0 and r.thumbs.shade("composite") == 0.0
    s.switch = {"switch": 2}
    r.thumbs.want({"composite": "picture"})
    r.draw_outputs(s, *SIZE, 1.0, views, t_now=2.3)
    assert r.thumbs.count == 1 and r.thumbs.shade("composite") == 1.0
