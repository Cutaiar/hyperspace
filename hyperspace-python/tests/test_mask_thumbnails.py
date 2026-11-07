"""SM3 (register row 777): a matte and a segment show their mask on GRAPH.

A mask is one channel, so `PreviewTextures` reads it as grey, white where it
passes; a segment's worker keeps its rows top first, so its thumbnail is read
upside down and lands the right way up. A thumbnail is not part of a render:
the outputs are byte for byte the same, a mask nothing pulled is not made for
it, and a mask costs one downsample pass with no readback (it is grey, so its
hue is never read). A thumbnail never makes a mask: it shows only one the
frame already made. A box with no mask says why on the node. A segment's `fg`
and `bg` are their own pictures, on a folded group and to a cable's tint. The
GL tests use test_graph_segment's harness and fake
worker, and skip without a standalone context."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
from test_graph_faces import Still, _fbo, _media, _rgba
from test_graph_segment import (
    COLOUR,
    FIXTURE,
    SEGMENT,
    SIZE,
    FakeWorker,
    _draw,
    _renderer,
    _s,
    _sources,
    _top,
)
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import graphview, masks, render, ui_graph
from hyperspace.graphview import MASK_PIC
from hyperspace.outputs import Switches, View, thumb_size
from hyperspace.view import MatteState

MATTE = {"kind": "matte"}
SEG_WANT = {"segment": MASK_PIC}
FG_ONLY = [("channel.a", "segment.image"), ("segment.fg", "output.2.image")]


def _thumb(r, name) -> np.ndarray:
    """`name`'s thumbnail, top row first, as the page draws it (GL's rows
    turned: `ui_graph._thumb`)."""
    tex = r.thumbs.get(name)
    w, h = tex.size
    return np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4)[::-1].astype(int)


def _wanted(ctx, r, s, name_how, n=2, frames=2):
    """Draw `frames` frames with the thumbnails in `name_how` wanted."""
    px = []
    for k in range(frames):
        r.thumbs.want(name_how)
        px = _draw(ctx, r, s, n=n, t=2.0 + k / 60)
    return px


def _halves(px) -> tuple[int, int]:
    """(the top half's mean, the bottom half's) at the middle column."""
    h, w = px.shape[:2]
    return int(px[h // 4, w // 2, 0]), int(px[3 * h // 4, w // 2, 0])


def _is_grey(px) -> bool:
    return bool((px[..., 0] == px[..., 1]).all() and (px[..., 1] == px[..., 2]).all()
                and (px[..., 3] == 255).all())


# ---------------------------------------------------------------- the table

def test_a_matte_and_a_segment_are_mask_thumbnails_and_a_pin_is_no_node():
    assert graphview.THUMBS["matte"] == graphview.THUMBS["segment"] == MASK_PIC
    assert graphview.thumb_of("matte", G.MatteNode("matte")) == MASK_PIC
    assert graphview.thumb_of("matte.2", G.MatteNode("matte.2")) == MASK_PIC
    assert graphview.thumb_of("segment.2", G.SegmentNode("segment.2")) == MASK_PIC


def test_the_hover_calls_a_mask_a_mask():
    n = graphview.VNode("render:matte", "render", "Matte", thumb=MASK_PIC, picture=(64, 48))
    assert "64×48 mask" in graphview.picture_hover(n)
    n = graphview.VNode("render:scene", "render", "Scene", thumb="picture", picture=(64, 48))
    assert "64×48 picture" in graphview.picture_hover(n)


# ---------------------------------------------------------------- the picture

def test_a_segments_thumbnail_is_its_matte_in_grey_the_right_way_up(ctx):
    r = _renderer(ctx, _sources(), FG_ONLY, worker=FakeWorker(_top()))
    _wanted(ctx, r, _s(), SEG_WANT)
    assert r.thumbs.count == 1 and r.thumbs.shade("segment") == 1.0
    assert r.thumbs.size_of("segment") == (32, 24)        # the matte's own, not the frame's
    assert tuple(r.thumbs.get("segment").size) == thumb_size((32, 24))
    px = _thumb(r, "segment")
    assert _is_grey(px)
    top, bottom = _halves(px)
    assert top == 255 and bottom == 0                     # the worker's first rows on top


def test_a_mattes_thumbnail_is_what_its_promotion_shows_the_right_way_up(ctx):
    half = _rgba(*SIZE, (0, 0, 0))
    half[: SIZE[1] // 2, :, :3] = 255                     # (a media frame's rows: top first)
    pairs = [("channel.a", "matte.image"), ("matte", "output.2.image")]
    r = _renderer(ctx, _media(a=Still(half)), pairs, nodes=(MATTE,))
    s = _s()
    s.mattes = {"matte": MatteState()}
    out = _wanted(ctx, r, s, {"matte": MASK_PIC})
    px = _thumb(r, "matte")
    assert _is_grey(px)
    assert _halves(px) == _halves(out[1]) == (255, 0)


def test_a_motion_matte_is_grey_and_not_turned(ctx):
    """Motion's matte is a GL pass's, first row at the bottom: no flip. Its
    thumbnail matches what its promotion shows."""
    pairs = [("channel.a", "segment.image"), ("segment.mask", "output.2.image")]
    r = _renderer(ctx, _sources(), pairs)
    out = _wanted(ctx, r, _s(mode=1), SEG_WANT)
    px = _thumb(r, "segment")
    assert _is_grey(px)
    assert abs(px[..., 0].mean() - out[1][..., 0].mean()) < 2.0


def test_a_picture_after_a_mask_is_still_in_colour(ctx):
    """The pass's two switches are uniforms of one program: a mask's copy
    leaves nothing set for the next node's."""
    pairs = [("channel.a", "segment.image"), ("segment.fg", "output.2.image")]
    r = _renderer(ctx, _sources(), pairs, worker=FakeWorker(_top()))
    _wanted(ctx, r, _s(), {**SEG_WANT, "channel.a": "picture"})
    px = _thumb(r, "channel.a")
    assert tuple(px[px.shape[0] // 2, px.shape[1] // 2][:3]) == COLOUR


# ---------------------------------------------------------------- not part of a render

def test_the_outputs_are_byte_identical_with_and_without_a_mask_thumbnail(ctx):
    pairs = [("channel.a", "segment.image"), ("segment.fg", "output.2.image"),
             ("channel.a", "matte.image"), ("matte", "output.3.image")]
    nodes = (SEGMENT, MATTE)
    plain = _renderer(ctx, _sources(), pairs, nodes=nodes, worker=FakeWorker(_top()))
    want = _renderer(ctx, _sources(), pairs, nodes=nodes, worker=FakeWorker(_top()))
    s = _s()
    for k in range(3):
        t = 2.0 + k / 60
        a = _draw(ctx, plain, s, n=3, t=t)
        want.thumbs.want({**SEG_WANT, "matte": MASK_PIC})
        b = _draw(ctx, want, s, n=3, t=t)
        for pa, pb in zip(a, b, strict=True):
            assert np.array_equal(pa, pb), k
    assert want.thumbs.count == 2 and plain.thumbs.count == 0


def test_a_shown_mask_adds_no_readback_no_refit_and_no_second_feed(ctx, monkeypatch):
    reads: list[int] = []
    real = masks.MaskPasses.readback

    def counting(self, *a, **kw):
        reads.append(1)
        return real(self, *a, **kw)

    monkeypatch.setattr(masks.MaskPasses, "readback", counting)
    w = FakeWorker(_top())
    r = _renderer(ctx, _sources(), FG_ONLY, worker=w)
    # the input is a still on a channel, so its frame id does not move and
    # the worker is fed once, by the shortcut, with or without the thumbnail
    _wanted(ctx, r, _s(), SEG_WANT, frames=3)
    assert len(w.submits) == 1 and reads == []
    assert "segment#fit" not in r._frames                 # nothing refitted for the thumbnail
    assert r.thumbs.repainted == 0


def test_the_system_lines_repainted_count_is_honest_for_a_mask(ctx, monkeypatch):
    """A mask that left a new entry in the frame's data would count, so the
    zero above is a reading: the mask's copy goes by the same count."""
    r = _renderer(ctx, _sources(), FG_ONLY, worker=FakeWorker(_top()))
    real = render.thumb_source

    def leaving_an_entry(frame, name, how, pulled=None):
        frame.data["spy#made"] = None
        return real(frame, name, how, pulled)

    monkeypatch.setattr(render, "thumb_source", leaving_an_entry)
    _wanted(ctx, r, _s(), SEG_WANT, frames=1)
    assert r.thumbs.count == 1 and r.thumbs.repainted == 1


def test_a_mask_is_never_read_for_a_hue(ctx):
    r = _renderer(ctx, _sources(), FG_ONLY, worker=FakeWorker(_top()))
    for k in range(4):
        r.thumbs.want_hues()
        r.thumbs.want(SEG_WANT)
        _draw(ctx, r, _s(), t=2.0 + k / 60)
    assert r.thumbs.hue_reads == 0 and r.thumbs._hue_pending is None
    assert r.thumbs.hue("segment") is None                # the cable stays plain
    r.thumbs.drop("segment")
    assert "segment" not in r.thumbs.masks


def test_a_mask_nothing_pulled_is_not_made_for_its_thumbnail(ctx):
    half = _rgba(*SIZE, COLOUR)
    pairs = [("channel.a", "matte.image"), ("matte", "switch.in2"),
             ("channel.c", "switch.in1"), ("switch", "output.2.image")]
    r = _renderer(ctx, _media(a=Still(half), c=Still(half)), pairs,
                  nodes=(MATTE, {"kind": "switch"}))
    s = _s()
    s.switch = {"switch": 1}
    _wanted(ctx, r, s, {"matte": MASK_PIC})
    assert r.thumbs.count == 0 and r.thumbs.get("matte") is None
    assert not any("matte#mask" in str(k) for k in r._frames)
    s.switch = {"switch": 2}
    _wanted(ctx, r, s, {"matte": MASK_PIC})
    assert r.thumbs.count == 1 and r.thumbs.shade("matte") == 1.0


def _counting_mattes(monkeypatch) -> list[int]:
    made: list[int] = []
    real = masks.MaskPasses.matte

    def counting(self, *a, **kw):
        made.append(1)
        return real(self, *a, **kw)

    monkeypatch.setattr(masks.MaskPasses, "matte", counting)
    return made


def test_a_dangling_matte_is_not_built_so_no_thumbnail_makes_it(ctx, monkeypatch):
    """Nothing reads it, so `reaches` leaves it out of the graph: a stand-in
    on the canvas, nothing to copy. The same for a matte into a dangling cut."""
    made = _counting_mattes(monkeypatch)
    still = _media(a=Still(_rgba(*SIZE, COLOUR)))
    for pairs, nodes in (([("channel.a", "matte.image")], (MATTE,)),
                         ([("channel.a", "matte.image"), ("channel.a", "cut.image"),
                           ("matte", "cut.mask")], (MATTE, {"kind": "cut"}))):
        r = _renderer(ctx, still, pairs, nodes=nodes)
        s = _s()
        _wanted(ctx, r, s, {"matte": MASK_PIC})
        assert "matte" not in r._graph.nodes
        assert r.thumbs.count == 0 and made == []


def test_a_mask_the_frame_did_not_ask_for_is_not_made_for_its_thumbnail(ctx, monkeypatch):
    """Built and pulled, but asked for by nobody this frame: a matte into an
    output whose picture is muted. No pass runs for the thumbnail, and the box
    stays black."""
    made = _counting_mattes(monkeypatch)
    pairs = [("channel.a", "matte.image"), ("matte", "output.2.image")]
    r = _renderer(ctx, _media(a=Still(_rgba(*SIZE, COLOUR))), pairs, nodes=(MATTE,))
    views = [View(Switches(), SIZE, target=_fbo(ctx, *SIZE)),
             View(Switches(scene=False), SIZE, target=_fbo(ctx, *SIZE))]
    s = _s()
    _draw(ctx, r, s, t=2.0, views=views)
    assert "matte" in r._graph.nodes and made == []       # (the frame does not ask)
    r.thumbs.want({"matte": MASK_PIC})
    _draw(ctx, r, s, t=2.1, views=views)
    assert made == [] and r.thumbs.count == 0 and r.thumbs.get("matte") is None


def test_a_mask_a_pictures_repaint_made_shows_whatever_the_order(ctx, monkeypatch):
    """A cut's thumbnail paints it, and that asks its matte. The matte's
    thumbnail, wanted first or last, shows that one: masks are copied last."""
    made = _counting_mattes(monkeypatch)
    pairs = [("scene", "lookback.image"), ("channel.a", "matte.image"),
             ("matte", "lookback.cover"), ("lookback", "output.2.image"),
             ("channel.a", "cut.image"), ("matte", "cut.mask"), ("cut", "output.3.image")]
    r = _renderer(ctx, _media(a=Still(_rgba(*SIZE, COLOUR))), pairs,
                  nodes=(MATTE, {"kind": "cut"}))
    _wanted(ctx, r, _s(), {"matte": MASK_PIC, "cut": "picture"}, n=3, frames=1)
    assert r.thumbs.count == 2 and len(made) == 1


def test_a_failing_flip_read_costs_one_thumbnail_not_the_frames_end(ctx, monkeypatch):
    """`_thumbnails` never raises: a mask's flag is read inside the per-node
    guard, so the others are copied and `end_frame` still runs."""
    r = _renderer(ctx, _sources(), FG_ONLY, worker=FakeWorker(_top()))

    def boom(node, frame):
        raise RuntimeError("no flag")

    monkeypatch.setattr(render, "mask_flip", boom)
    ended: list[int] = []
    real_end = r.thumbs.end_frame
    monkeypatch.setattr(r.thumbs, "end_frame", lambda: (ended.append(1), real_end()))
    _wanted(ctx, r, _s(), {**SEG_WANT, "channel.a": "picture"}, frames=1)
    assert r.thumbs.count == 1 and r.thumbs.get("channel.a") is not None
    assert "no flag" in r.thumbs.error and ended == [1]


def test_a_refusal_is_in_the_nodes_words_and_clears_with_a_mask(ctx):
    n = graphview.VNode("render:segment", "render", "Segment", thumb=MASK_PIC)
    w = FakeWorker(_top())
    r = _renderer(ctx, _sources(), FG_ONLY, worker=w)
    seg = lambda: r._graph.nodes["segment"]
    _draw(ctx, r, _s())
    n.ref = seg()
    assert graphview.mask_words(n) == ""                  # a matte: nothing to say
    _draw(ctx, r, _s(mode=2), t=2.1)
    assert "subject is not in this build" in graphview.mask_words(n)
    _draw(ctx, r, _s(on=False), t=2.2)
    assert graphview.mask_words(n).startswith("off")
    w.error = "the model would not load"
    _draw(ctx, r, _s(), t=2.3)
    assert "the model would not load" in graphview.mask_words(n)
    w.error = ""
    _draw(ctx, r, _s(), t=2.4)
    assert graphview.mask_words(n) == ""
    # a picture node never says it this way, whatever its ref holds
    assert graphview.mask_words(graphview.VNode("x", "render", "X", ref=seg())) == ""


def test_a_matte_reading_nothing_and_an_unbuilt_one_say_so():
    assert graphview._stand_in("matte").refused == graphview.MATTE_UNWIRED
    assert graphview._stand_in("segment").refused == graphview.SEGMENT_UNWIRED
    assert G.MatteNode("matte").refused == ""


def test_box_lines_wrap_and_stop_at_four():
    measure = lambda text: NS(x=float(len(text)))
    assert ui_graph.box_lines("", measure, 10) == []
    assert ui_graph.box_lines("short", measure, 10) == ["short"]
    assert ui_graph.box_lines("aaaa bbbb cccc", measure, 10) == ["aaaa bbbb", "cccc"]
    got = ui_graph.box_lines(" ".join(["word"] * 40), measure, 10)
    assert len(got) == ui_graph.BOX_LINES


def test_a_segment_making_no_matte_has_no_thumbnail(ctx):
    w = FakeWorker(_top())
    r = _renderer(ctx, _sources(), FG_ONLY, worker=w)
    _wanted(ctx, r, _s(on=False), SEG_WANT)
    assert r.thumbs.count == 0 and w.submits == []        # off: the worker stays asleep
    assert r.thumbs.shade("segment") == 0.0


def test_a_hot_reload_makes_the_mask_pass_again(ctx):
    r = _renderer(ctx, _sources(), FG_ONLY, worker=FakeWorker(_top()))
    _wanted(ctx, r, _s(), SEG_WANT)
    r.thumbs.close()
    r.thumbs = None
    r._thumbs()
    _wanted(ctx, r, _s(), SEG_WANT)
    assert _halves(_thumb(r, "segment")) == (255, 0)


# ---------------------------------------------------------------- the page

def _segment_page(rig, groups=()):
    """The saved `segment-motion` on the GRAPH page, drawn twice."""
    (Path(rig.lib.home) / "presets").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE, Path(rig.lib.home) / "presets" / FIXTURE.name)
    rig.lib.load("presets", FIXTURE.stem)
    rig.lib.loaded_patch.groups = [dict(g) for g in groups]
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    return ui_graph._state(rig.panel)


def test_the_page_wants_a_segments_mask_under_its_render_nodes_name(shell_rig):  # noqa: F811
    st = _segment_page(shell_rig)
    n = st["view"].node("render:segment")
    assert n.thumb == MASK_PIC and ui_graph.thumb_name(n) == "segment"
    st["seen_rect"] = None
    want = ui_graph.thumb_wants(st, st["view"], lambda nid: ((0.0, 0.0), (10.0, 10.0)))
    assert want["segment"] == MASK_PIC


def test_a_groups_fg_outlet_shows_the_foreground_not_the_matte(shell_rig):  # noqa: F811
    """A folded group's thumbnail is its last picture outlet's. `view.pins`
    gives `segment.fg`'s owner, whose thumbnail is the matte; the pin's own
    node makes the picture, so that is what the group wants and draws."""
    st = _segment_page(shell_rig, [{"id": "group.1", "name": "cut", "open": False,
                                    "nodes": ["render:segment"]}])
    view = st["view"]
    (g,) = view.groups
    assert g.thumb == "render:segment" and g.thumb_pin == "segment.fg"
    n = graphview.group_picture(view, g)
    assert ui_graph.thumb_name(n) == "segment.fg" and n.thumb == graphview.PICTURE
    st["seen_rect"] = None
    want = ui_graph.thumb_wants(st, view, lambda nid: ((0.0, 0.0), (10.0, 10.0)))
    assert want["segment.fg"] == graphview.PICTURE and "segment" not in want


def test_a_segment_pin_is_its_own_picture_and_any_other_pin_is_not(shell_rig):  # noqa: F811
    view = _segment_page(shell_rig)["view"]
    assert graphview.pin_picture(view, "rout:segment.fg") == "segment.fg"
    assert graphview.pin_picture(view, "rout:segment.2.bg") == "segment.2.bg"
    assert graphview.pin_picture(view, "rout:segment.mask") is None    # a mask, not a picture
    assert graphview.pin_picture(view, "rout:scene") is None
    assert graphview.pin_picture(view, "rout:scene.depth") is None


def test_a_fg_cable_tints_from_the_foreground_only_while_lit(shell_rig):  # noqa: F811
    st = _segment_page(shell_rig)
    view = st["view"]
    cable = next(c for c in view.cables if c.src_port == "rout:segment.fg")
    want = {"segment": MASK_PIC}
    assert ui_graph.tint_wants({**st, "tint": False}, view, want) == {}
    lit = {**st, "tint": True}
    assert ui_graph.tint_wants(lit, view, want) == {"segment.fg": graphview.PICTURE}
    assert ui_graph.tint_wants(lit, view, {}) == {}       # its node off screen: no copy
    hues = {"segment.fg": (0.33, 1.0)}
    th = NS(hue=hues.get)
    assert cable.id in ui_graph.cable_tints({**lit, "thumbs": th}, view)
    assert ui_graph.cable_tints({**st, "tint": False, "thumbs": th}, view) == {}


def test_a_box_with_no_mask_says_why_on_the_page(shell_rig, monkeypatch):  # noqa: F811
    said: list[str] = []
    real = ui_graph.box_lines

    def spying(words, measure, width):
        said.append(words)
        return real(words, measure, width)

    monkeypatch.setattr(ui_graph, "box_lines", spying)
    st = _segment_page(shell_rig)
    assert said and all(said)
    assert st["view"].node("render:segment").thumb == MASK_PIC


# ---------------------------------------------------------------- positions

def test_a_taller_mask_node_keeps_a_saved_position_and_the_auto_layout_clears_it(shell_rig):  # noqa: F811
    """WYSIWYG: a saved position never moves. A patch with no saved layout (all
    three fixtures holding a mask node, row 777's count) takes the auto layout,
    which counts the thumbnail's height, so nothing overlaps there."""
    view = _segment_page(shell_rig)["view"]
    n = view.node("render:segment")
    assert graphview.height(n, collapsed=True) == graphview.HEAD_H + graphview.THUMB_H
    # (a saved position isn't the layout's to give: the page reads it first)
    assert "render:segment" not in graphview.layout(view, {"render:segment": (123.0, 456.0)}).nodes
    laid = graphview.layout(view, collapsed=lambda nid: True).nodes
    boxes = [(nid, *xy, graphview.height(v, collapsed=True))
             for nid, xy in laid.items() if (v := view.node(nid)) is not None and not v.idle]
    for i, (a, ax, ay, ah) in enumerate(boxes):
        for b, bx, by, bh in boxes[i + 1:]:
            apart = (abs(ax - bx) >= ui_graph.NODE_W or ay + ah <= by or by + bh <= ay)
            assert apart, (a, b)


def test_no_shipped_patch_saves_a_layout_with_a_mask_node():
    """Row 777's measure, kept honest: a corpus or fixture file with a matte or
    a segment and a saved layout would have to be looked at by eye."""
    root = Path(__file__).parent
    found = []
    for f in [*(root / "corpus").rglob("*.json"), *(root / "fixtures").rglob("*.json")]:
        try:
            doc = json.loads(f.read_text())
        except ValueError:
            continue
        graph = doc.get("graph") if isinstance(doc, dict) else None
        nodes = graph.get("nodes") if isinstance(graph, dict) else None
        kinds = {x.get("kind") for x in nodes or () if isinstance(x, dict)}
        if kinds & {"matte", "segment"} and doc.get("layout"):
            found.append(f.name)
    assert found == []
