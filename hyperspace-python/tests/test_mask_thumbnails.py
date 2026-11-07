"""SM3 (register row 777): a matte and a segment show their mask on GRAPH.

A mask is one channel, so `PreviewTextures` reads it as grey, white where it
passes; a segment's worker keeps its rows top first, so its thumbnail is read
upside down and lands the right way up. A thumbnail is not part of a render:
the outputs are byte for byte the same, a mask nothing pulled is not made for
it, and a mask costs one downsample pass with no readback (it is grey, so its
hue is never read). The GL tests use test_graph_segment's harness and fake
worker, and skip without a standalone context."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
from test_graph_faces import Still, _media, _rgba
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
from hyperspace import graphview, masks, ui_graph
from hyperspace.graphview import MASK_PIC
from hyperspace.outputs import thumb_size
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


def test_a_groups_fg_outlet_does_not_show_the_segments_matte(shell_rig):  # noqa: F811
    """A folded group's thumbnail is its last picture outlet's. A segment's
    `fg` is a picture, its node's thumbnail its matte: not that picture, so
    the group shows none and does not want the matte for it."""
    st = _segment_page(shell_rig, [{"id": "group.1", "name": "cut", "open": False,
                                    "nodes": ["render:segment"]}])
    (g,) = st["view"].groups
    assert [p.type for p in g.ports if p.direction == graphview.OUT] == [graphview.IMAGE]
    assert g.thumb is None
    st["seen_rect"] = None
    want = ui_graph.thumb_wants(st, st["view"], lambda nid: ((0.0, 0.0), (10.0, 10.0)))
    assert "segment" not in want
