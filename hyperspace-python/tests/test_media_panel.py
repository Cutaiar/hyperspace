"""`panel:graph` (2026-11-02): the GRAPH canvas as a media source. The id,
the source's frames and status over a fake tap and clock, the resolver's
built-in that every call answers with the one object, the MEDIA page's
live list, and the page's `canvas_px` recorded only while GRAPH draws."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from hyperspace import app, ui_media
from hyperspace.media import ids, live
from hyperspace.media.channels import MediaState
from hyperspace.media.frame import TEX_2D
from hyperspace.media.panel import GRAPH, PanelSource
from hyperspace.media.source import FETCHING, LOST, READY
from hyperspace.ui import PAGE_KEYS

sys.path.insert(0, str(Path(__file__).parent))
from test_ui_shell import build_rig, frame


class Clock:
    def __init__(self, t: float = 100.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


class FakeTap:
    """What `outputs.CanvasTap` shows a source: wanted, the texture written
    last, its size, the grab count and time."""

    def __init__(self):
        self.wants = 0
        self.tex = None
        self.size = None
        self.frame_no = 0
        self.at = 0.0

    def want(self):
        self.wants += 1

    def grab(self, glo: int, size, at: float):
        self.tex, self.size, self.frame_no, self.at = NS(glo=glo), size, self.frame_no + 1, at


# ---------------------------------------------------------------- the id

def test_panel_graph_is_a_source_id():
    assert "panel" in ids.KINDS
    assert ids.parse(GRAPH) == ids.SourceId("panel", "graph")
    assert ids.parse("panel:graph").kind not in ids.FILE_KINDS
    with pytest.raises(ValueError):
        ids.parse("canvas:graph")


# ---------------------------------------------------------------- the source

def test_the_source_hands_over_the_texture_the_tap_wrote_last():
    clock, tap = Clock(), FakeTap()
    src = PanelSource(tap, clock=clock)
    assert src.sid == GRAPH and src.kind == "panel" and not src.timed and src.duration == 0.0
    src.open()
    assert src.status == FETCHING                 # just opened, nothing grabbed yet
    assert src.gl_poll() is None and tap.wants == 1   # asked, nothing to show yet
    tap.grab(7, (400, 240), clock())
    f = src.gl_poll()
    assert tap.wants == 2
    assert f is not None and f.pixels is None and f.texture == 7 and f.tex_size == (400, 240)
    assert f.tex_target == TEX_2D and f.frame == 1 and f.t == clock()
    assert src.status == READY and src.latest() is f
    # no new grab: the same frame object, so a reader uploads nothing again
    assert src.gl_poll() is f
    # the next grab, the other texture: a new frame naming it
    clock.t += 0.02
    tap.grab(8, (400, 240), clock())
    g = src.gl_poll()
    assert g is not f and g.texture == 8 and g.frame == 2


def test_off_the_page_the_last_frame_holds_then_lost():
    """GRAPH not on screen: no grab, the frame holds `HOLD_S`, then the
    source reads None (black) and says `lost`; the first grab back is
    `ready` again."""
    clock, tap = Clock(), FakeTap()
    src = PanelSource(tap, clock=clock)
    src.open()
    tap.grab(7, (400, 240), clock())
    f = src.gl_poll()
    clock.t += live.HOLD_S
    assert src.gl_poll() is f and src.status == READY
    clock.t += 0.01
    assert src.gl_poll() is None and src.latest() is None and src.status == LOST
    tap.grab(8, (400, 240), clock())
    assert src.gl_poll().texture == 8 and src.status == READY


def test_holders_are_counted_and_a_fault_is_said_until_the_next_frame():
    clock, tap = Clock(), FakeTap()
    src = PanelSource(tap, clock=clock)
    src.open()
    src.open()
    assert src.held == 2
    src.close()
    assert src.held == 1 and src.status == FETCHING
    src.close()
    assert src.held == 0 and src.status == LOST       # nobody holds it: not fetching
    src.status = "error: boom"
    assert src.status == "error: boom"
    tap.grab(7, (4, 4), clock())
    src.gl_poll()
    assert src.status == READY
    src.want(3.0)                                      # untimed: a no-op
    assert PanelSource(None).gl_poll() is None         # no tap (headless): nothing


def test_the_source_imports_nothing_from_the_host():
    import ast

    from hyperspace.media import panel

    tree = ast.parse(Path(panel.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module != "__future__":
            assert node.level, node.module                     # only the package's own
            assert (node.module or "").split(".")[0] in ("frame", "live", "source")
        elif isinstance(node, ast.Import):
            assert all(a.name == "time" for a in node.names)


# ---------------------------------------------------------------- the resolver

def test_the_resolver_answers_panel_graph_with_the_one_object():
    """A built-in, before the devices, the same object every call — so
    `channels._stale` keeps the channel's source — and a channel on it
    opens it and holds the tap's frame."""
    src = PanelSource(FakeTap())
    feeds = {"ndi:X": NS(status="ready")}
    reg = NS(media_feeds=lambda: feeds)
    r = app.MediaResolver(NS(path=lambda sid: None), reg, builtin={GRAPH: src})
    assert r.live(GRAPH) is src and r.live(GRAPH) is src
    assert r.live("ndi:X") is feeds["ndi:X"]
    assert r.live("panel:other") is None
    ms = MediaState(r)
    ms.channels["a"].bin[0] = GRAPH
    ms.poll(1 / 60, 1.0)
    assert ms.channels["a"].source is src and src.held == 1
    assert not ms._stale(ms.channels["a"])
    ms.poll(1 / 60, 2.5)                              # the recheck a second on: kept
    assert ms.channels["a"].source is src and src.held == 1
    ms.channels["a"].bin[0] = None
    ms.poll(1 / 60, 3.0)
    assert ms.drain(2.0) and src.held == 0


def test_the_app_builds_the_source_on_the_canvas_tap(monkeypatch):
    """`MediaResolver` with no built-ins answers none (the tests' and the
    headless app's); the running app registers `panel:graph` on
    `panel.canvas_tap` (app.main) — held here by the resolver's shape."""
    r = app.MediaResolver(NS(path=lambda sid: None))
    assert r.live(GRAPH) is None and r.builtin == {}
    src = Path(app.__file__).read_text()
    assert "resolver.builtin[PANEL_GRAPH] = PanelSource(panel.canvas_tap)" in src
    assert "replay.grab(panel.canvas_tap, impl, imgui.get_draw_data(), panel.canvas_px)" in src


# ---------------------------------------------------------------- the pages

def test_the_media_page_lists_panel_graph_among_the_live_feeds(tmp_path):
    with build_rig(tmp_path) as rig:
        state = rig.reg.media
        src = PanelSource(FakeTap())
        state.resolver = app.MediaResolver(NS(path=lambda sid: None), builtin={GRAPH: src})
        rig.panel.media = NS(folder=None, state=state)
        rig.panel.devices = NS(media_feeds=lambda: {"ndi:Resolume": NS(status="connected")},
                               devices=[], lines=list)
        rows = ui_media.items(rig.panel, 2)
        assert [i.sid for i in rows] == [GRAPH, "ndi:Resolume"]
        assert rows[0].name == "graph" and rows[0].kind == "live" and rows[0].status == LOST
        ui_media._state(rig.panel)["search"] = "graph"
        assert [i.sid for i in ui_media.items(rig.panel, 2)] == [GRAPH]
        frame(rig.panel, "media")                     # the page draws it


def test_canvas_px_is_recorded_only_while_graph_draws(tmp_path):
    with build_rig(tmp_path) as rig:
        panel = rig.panel
        assert panel.canvas_px is None
        frame(panel, "graph")
        px = panel.canvas_px
        assert px is not None
        _origin, size, scale, page, omit = px
        assert size[0] >= 80 and size[1] >= 80 and scale == (1.0, 1.0)
        assert page.startswith("CONTROLS/##page_") and "/" not in page[len("CONTROLS/"):]
        assert omit == (0, 0)                         # nothing selected: no pane
        frame(panel, "view")
        assert panel.canvas_px is None
        panel.reg["ui.page"].set(PAGE_KEYS.index("graph"))
        panel.open = False
        frame(panel)
        assert panel.canvas_px is None                # the panel hidden: no canvas
        panel.open = True
        frame(panel)
        assert panel.canvas_px is not None


def test_the_pane_decorations_are_noted_for_the_replay_to_cut_out(tmp_path):
    """imgui draws a child's ground, border and scrollbar on its parent's
    list inside `begin_child`: on the page's list, the canvas's picture.
    With a node selected the page notes the indices they took, and every
    vertex of that range lies on the pane; outside the range no vertex of
    the page list's window-clipped commands lies inside the pane."""
    import ctypes

    import numpy as np
    from imgui_bundle import imgui

    from hyperspace import ui_graph

    vtx_t = np.dtype([("x", "f4"), ("y", "f4"), ("u", "f4"), ("v", "f4"), ("col", "u4")])
    with build_rig(tmp_path) as rig:
        panel = rig.panel
        panel.reg["ui.page"].set(PAGE_KEYS.index("graph"))
        for _ in range(3):
            frame(panel)
        view = ui_graph.view_of(panel)
        panel.select_graph_node(view.nodes[0].id)
        for _ in range(3):
            frame(panel)
        imgui.new_frame()
        panel.draw(1 / 60, 60.0)
        imgui.render()
        origin, _size, _scale, page, omit = panel.canvas_px
        pos, psize = ui_graph._state(panel)["details_rect"]
        assert omit[1] > omit[0] and omit[0] % 3 == 0 and omit[1] % 3 == 0
        [dl] = [d for d in imgui.get_draw_data().cmd_lists if d._owner_name == page]
        n = dl.vtx_buffer.size()
        vtx = np.frombuffer((ctypes.c_ubyte * (n * imgui.VERTEX_SIZE)).from_address(
            dl.vtx_buffer.data_address()), vtx_t)
        ni = dl.idx_buffer.size()
        idx = np.frombuffer((ctypes.c_ubyte * (ni * imgui.INDEX_SIZE)).from_address(
            dl.idx_buffer.data_address()), np.uint16 if imgui.INDEX_SIZE == 2 else np.uint32)
        assert omit[1] <= ni

        def on_pane(v, slack):
            return ((v["x"] >= pos[0] - slack) & (v["x"] <= pos[0] + psize[0] + slack)
                    & (v["y"] >= pos[1] - slack) & (v["y"] <= pos[1] + psize[1] + slack))

        for c in dl.cmd_buffer:
            if not c.elem_count:
                continue
            ids = idx[c.idx_offset:c.idx_offset + c.elem_count] + c.vtx_offset
            cut = (np.arange(c.idx_offset, c.idx_offset + c.elem_count) >= omit[0]) & (
                np.arange(c.idx_offset, c.idx_offset + c.elem_count) < omit[1])
            assert on_pane(vtx[ids[cut]], 1.0).all()           # the decorations: on the pane
            if c.clip_rect[1] < origin[1]:                     # the window's clip, not the canvas's
                kept = vtx[ids[~cut]]
                assert not on_pane(kept, -16.0).any()          # nothing else inside it (clear of the canvas outline's rounded corners)
