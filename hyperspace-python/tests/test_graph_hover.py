"""Plan 37 C2 (P1, D2, D3): a picture node's hover gives its details, and
the GRAPH head's **pictures · tint cables** switch.

Hovering a picture node's thumbnail says what its collapsed lines said
before it was a picture (`graphview.summary`), the size of the picture
its thumbnail was copied from, and its GPU time (`graphview.picture_hover`,
`ui_graph.thumb_tip`). The switch is off by default and page state only;
lit, a picture cable's red leans toward its maker's dominant hue
(`outputs.dominant_hue`, read from the thumbnail once a second;
`ui_graph.tint`, always a red)."""

from __future__ import annotations

import colorsys
import itertools
import json
from types import SimpleNamespace as NS

import moderngl
import pytest
from conftest import seed
from test_graph_legible import party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import graphview, ui, ui_graph
from hyperspace.outputs import HUE_EVERY_S, HUE_GRID, PreviewTextures, dominant_hue
from hyperspace.view import RED as RED_RGB


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)         # (the corpus: the presets the tests load by slug)
    return shell_rig


def _hue_deg(rgb) -> float:
    """An rgb's hue in signed degrees from red (−180…180)."""
    h = colorsys.rgb_to_hsv(*rgb)[0] * 360.0
    return h - 360.0 if h > 180.0 else h


def _solid(rgb, size=(32, 16)) -> bytes:
    px = bytes(round(v * 255) for v in rgb) + b"\xff"
    return px * (size[0] * size[1])


# ---------------------------------------------------------------- the hover

def test_a_picture_nodes_hover_is_its_summary_its_size_and_its_gpu_time(rig):
    st = party(rig)
    scene = st["view"].node("render:scene")
    assert scene is not None and scene.thumb is not None
    scene.picture = (1920, 1080)
    lines = graphview.picture_hover(scene, 0.4249).split("\n")
    assert lines[0] == scene.label                  # its title first (it stays on the node too)
    for line in graphview.summary(scene):
        assert line in lines
    assert "1920×1080 picture" in lines
    assert "gpu 0.42 ms" in lines
    # no size yet, no timer line: those lines left out
    scene.picture = None
    assert graphview.picture_hover(scene).split("\n") == [scene.label, *graphview.summary(scene)]


def test_the_page_finds_the_gpu_time_by_the_render_nodes_name(rig):
    st = party(rig)
    n = st["view"].node("render:scene")
    n.picture = (640, 360)
    st["gpu_ms"] = {ui_graph.thumb_name(n): 1.5, "other": 9.0}
    tip = ui_graph.thumb_tip(st, n)
    assert "gpu 1.50 ms" in tip and "640×360 picture" in tip and "9.00" not in tip
    st["gpu_ms"] = {}
    assert "gpu" not in ui_graph.thumb_tip(st, n)


def test_a_switch_and_an_unreached_node_say_so_on_hover():
    """The lines a collapsed picture node lost to its thumbnail (C1) are
    its hover's: a switch's pick, "reaches nothing"."""
    port = graphview.VPort("p", "select", graphview.IN, param="switch.select",
                           live=2 / len(G.SWITCH_PORTS))
    sw = graphview.VNode("render:switch", "render", "Switch", ports=[port],
                         ref=G.SwitchNode("switch"))
    sw.faint = True
    tip = graphview.picture_hover(sw)
    assert graphview.REACHES_NOTHING in tip and "picks in2" in tip


# ---------------------------------------------------------------- the switch

def test_the_tint_switch_is_off_by_default_and_on_the_head_last(rig, monkeypatch):
    st = party(rig)
    assert st["tint"] is False
    labels: list[str] = []
    lit = ui.lit_chip
    monkeypatch.setattr(ui, "lit_chip", lambda label, on, *a, **k:
                        labels.append(label) or lit(label, on, *a, **k))
    frame(rig.panel, "graph")
    head = [x for x in labels if x.endswith("##graph")]
    assert head[-1] == ui_graph.TINT_LABEL          # after every chip today's head has
    assert head.index("output behind##graph") < head.index(ui_graph.TINT_LABEL)
    # off: every picture cable plain red
    assert ui_graph.cable_tints(st, st["view"]) == {}


def test_the_tint_switch_reaches_neither_the_preset_nor_the_show(rig):
    st = party(rig)
    lib = rig.lib
    plain = json.loads(lib.presets.save_as("UNTINTED").read_text())
    lib.project.save("plain-show")
    show_plain = json.loads(lib.project.path.read_text())
    st["tint"] = True
    frame(rig.panel, "graph")
    tinted = json.loads(lib.presets.save_as("TINTED").read_text())
    lib.project.save("tinted-show")
    show_tinted = json.loads(lib.project.path.read_text())
    for doc in (plain, tinted, show_plain, show_tinted):
        doc.pop("name", None)
        assert "tint cables" not in json.dumps(doc)
    assert plain == tinted
    assert show_plain == show_tinted


def test_lit_a_picture_cable_takes_its_makers_hue_and_off_it_is_red_again(rig):
    st = party(rig)
    view = st["view"]
    th = PreviewTextures(None)
    rig.panel.renderer.thumbs = th
    frame(rig.panel, "graph")
    pic = [c for c in view.cables if c.type == graphview.IMAGE
           and view.owner(c.src_port) is not None]
    assert pic
    c = pic[0]
    maker = ui_graph.thumb_name(view.owner(c.src_port)[0])
    th.hues[maker] = (1 / 3, 0.8)                     # a green picture
    assert ui_graph.cable_tints(st, view) == {}       # off: plain red
    st["tint"] = True
    frame(rig.panel, "graph")                          # the head lit: hues wanted
    assert th.hue_asked is not None
    got = st["tints"][c.id]
    assert (got.x, got.y, got.z) == pytest.approx(ui_graph.tint(1 / 3, 0.8))
    # only cables whose maker has a hue read are tinted
    for x in view.cables:
        if x.id in st["tints"]:
            assert ui_graph.thumb_name(view.owner(x.src_port)[0]) in th.hues
    # the five colours themselves are untouched
    assert ui_graph.COLOURS[graphview.IMAGE].x == pytest.approx(RED_RGB[0])
    assert ui_graph.COLOURS[graphview.IMAGE].y == pytest.approx(RED_RGB[1])
    st["tint"] = False
    frame(rig.panel, "graph")
    assert st["tints"] == {}


# ---------------------------------------------------------------- the tint, a pure function

def test_the_tint_always_leaves_a_red():
    trigger = _hue_deg((1.0, 0.74, 0.28))
    mask = _hue_deg((0.72, 0.52, 1.0))
    span = ui_graph.TINT_SPAN * 360.0
    for k in range(360):
        rgb = ui_graph.tint(k / 360.0, 1.0)
        d = _hue_deg(rgb)
        assert abs(d) <= span + 1e-6, k
        assert rgb[0] == pytest.approx(1.0) and max(rgb) == pytest.approx(1.0)   # red leads
        assert abs(d - trigger) > 10.0 and abs(d - mask) > 60.0
    # no hue to give: red exactly
    assert ui_graph.tint(0.6, 0.0) == pytest.approx(RED_RGB)
    # the yellow-green half leans toward orange, the blue-violet half toward
    # rose, most at a quarter round; red and cyan (on the axis) not at all
    assert _hue_deg(ui_graph.tint(1 / 6, 1.0)) > 0 > _hue_deg(ui_graph.tint(2 / 3, 1.0))
    assert _hue_deg(ui_graph.tint(0.25, 1.0)) == pytest.approx(span, abs=0.01)
    assert _hue_deg(ui_graph.tint(0.75, 1.0)) == pytest.approx(-span, abs=0.01)
    assert _hue_deg(ui_graph.tint(0.5, 1.0)) == pytest.approx(0.0, abs=0.01)
    # continuous all the way round: no flip anywhere (cyan included)
    leans = [_hue_deg(ui_graph.tint(k / 720.0, 1.0)) for k in range(721)]
    assert max(abs(a - b) for a, b in itertools.pairwise(leans)) < 0.2
    # a faint hue leans less than a strong one
    assert abs(_hue_deg(ui_graph.tint(1 / 3, 0.05))) < abs(_hue_deg(ui_graph.tint(1 / 3, 0.5)))


def test_the_dominant_hue_is_a_chroma_weighted_mean():
    size = (32, 16)
    h, s = dominant_hue(_solid((0.0, 1.0, 0.0), size), size)
    assert h == pytest.approx(1 / 3, abs=1e-3) and s > 0.8
    h, s = dominant_hue(_solid((0.1, 0.2, 0.9), size), size)
    assert h == pytest.approx(colorsys.rgb_to_hsv(0.1, 0.2, 0.9)[0], abs=0.03)
    assert dominant_hue(_solid((0.5, 0.5, 0.5), size), size)[1] < 1e-3   # grey: no hue
    assert dominant_hue(b"", size) == (0.0, 0.0)
    # half red, half grey: red, at half the strength of all red
    half = _solid((1.0, 0.0, 0.0), (32, 8)) + _solid((0.5, 0.5, 0.5), (32, 8))
    h, s = dominant_hue(half, size)
    assert min(h, 1 - h) < 1e-3
    assert s == pytest.approx(dominant_hue(_solid((1.0, 0.0, 0.0), size), size)[1] / 2, rel=0.1)


# ---------------------------------------------------------------- the hue read's cost

class FakeTex:
    """A thumbnail whose `read()` must never be called (a stall on the GPU)."""
    def __init__(self, rgb, size=(32, 16)):
        self.size, self.rgb, self.reads = size, rgb, 0

    def read(self):
        self.reads += 1
        return _solid(self.rgb, self.size)


class FakeBuf:
    def __init__(self, rgb):
        self.data = _solid(rgb, (HUE_GRID, HUE_GRID))

    def read(self):
        return self.data


def test_hues_are_read_a_frame_late_one_a_frame_each_once_a_second_only_while_asked():
    clock = Clock()
    th = PreviewTextures(None, clock)
    a, b = FakeTex((0.0, 1.0, 0.0)), FakeTex((0.0, 0.0, 1.0))
    th.tex = {"a": (a, None), "b": (b, None)}
    started: list[str] = []

    def start(name):                    # the downsample + read_into, as a stand-in
        started.append(name)
        th._hue_pending = (name, FakeBuf(th.tex[name][0].rgb))
    th._hue_start = start
    th.begin_frame()
    assert started == []                           # not asked: nothing started
    th.want_hues()
    th.begin_frame()
    assert len(started) == 1 and th.hues == {}     # one a frame, not yet arrived
    first = started[0]
    th.begin_frame()
    assert len(started) == 2 and set(th.hues) == {first}     # arrived a frame later
    th.begin_frame()
    assert len(started) == 2                       # each at most once a second
    assert th.hue("a")[0] == pytest.approx(1 / 3, abs=1e-3)
    assert th.hue("b")[0] == pytest.approx(2 / 3, abs=1e-3)
    assert th.hue_reads == 2
    clock.t += HUE_EVERY_S
    th.want_hues()
    th.begin_frame()
    assert len(started) == 3
    th.stop_hues()                                 # the switch went off: none started
    th.begin_frame()
    th.begin_frame()
    assert len(started) == 3 and th.hue_reads == 3     # (the one in flight collected)
    th.tex.pop("a")
    th.drop("a")                                   # dropped: its hue forgotten
    assert th.hue("a") is None and th.hue("b") is not None
    assert a.reads == b.reads == 0                 # never a texture's read()


def test_a_real_thumbnails_hue_is_its_pictures_a_frame_later_without_a_texture_read(
        ctx, monkeypatch):
    th = PreviewTextures(ctx)
    size = (96, 64)
    src = ctx.texture(size, 4, data=_solid((0.9, 0.6, 0.1), size))
    th.want({"orange": "picture"})
    th.take()
    th.begin_frame()
    assert th.put("orange", src)
    th.end_frame()
    th.want_hues()
    reads = []
    real = moderngl.Texture.read
    monkeypatch.setattr(moderngl.Texture, "read",
                        lambda self, *a, **k: (reads.append(self), real(self, *a, **k))[1])
    th.begin_frame()                               # started: downsample + read_into
    assert th.hue("orange") is None and th.hue_reads == 0
    th.begin_frame()                               # a frame later: from the buffer
    h, s = th.hue("orange")
    assert h == pytest.approx(colorsys.rgb_to_hsv(0.9, 0.6, 0.1)[0], abs=0.02) and s > 0.5
    assert th.hue_reads == 1 and ctx.error == "GL_NO_ERROR"
    assert reads == []                             # no texture read: no stall
    th.close()
    src.release()


def test_the_page_draws_with_the_switch_lit_and_a_thumbnail_hovered(rig, monkeypatch):
    """Headless draw: the switch lit, a thumbnail with a hue, the pointer
    on it — the page draws, and the tooltip it gives is the hover text."""
    st = party(rig)
    view = st["view"]
    th = PreviewTextures(None)
    rig.panel.renderer.thumbs = th
    rig.panel.renderer.stats = {"gpu_ms": {"scene": 0.75}}
    th.tex["scene"] = (NS(glo=7, size=(192, 108)), None)
    th.sizes["scene"], th.made_in["scene"], th.frame = (1920, 1080), 1, 1
    th.hues["scene"] = (0.55, 0.6)
    st["tint"] = True
    st["pan"] = (-1600.0, 0.0)                     # the scene's column on the small canvas
    frame(rig.panel, "graph")
    scene = view.node("render:scene")
    tips: list[str] = []
    monkeypatch.setattr(ui, "tooltip", lambda t, *a, **k: tips.append(t))
    hovered = ui_graph._id(st, "n:render:scene")
    monkeypatch.setattr(ui_graph.ed, "get_hovered_node", lambda: NS(id=lambda: hovered))
    monkeypatch.setattr(ui_graph.ed, "get_hovered_link", lambda: NS(id=lambda: 0))
    monkeypatch.setattr(ui_graph.ed, "get_hovered_pin", lambda: NS(id=lambda: 0))
    real_thumb = ui_graph._thumb

    def on_thumb(st_, n):
        real_thumb(st_, n)
        if n.id == "render:scene":
            st_["thumb_hover"] = n.id              # the pointer on its picture
    monkeypatch.setattr(ui_graph, "_thumb", on_thumb)
    frame(rig.panel, "graph")
    want = graphview.picture_hover(scene, 0.75)
    assert [t for t in tips if t.startswith(want)] == [want + f"\n{scene.status}"]
    assert "1920×1080 picture" in want and "gpu 0.75 ms" in want
