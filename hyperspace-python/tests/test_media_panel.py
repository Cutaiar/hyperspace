"""`panel:graph` (2026-11-02): the GRAPH canvas as a media source. The id,
the source's frames — each with a lease on its texture — and its status
(`fetching`, `ready`, the hold, `off page`, `lost`) over a fake tap and
clock, the shared base it has with a live feed (holders under a lock),
the resolver's built-in that every call answers with the one object, the
MEDIA page's live list and the `off page` hint, and the page's
`canvas_px` recorded only while GRAPH draws."""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from hyperspace import app, ui_media
from hyperspace.media import ids, live
from hyperspace.media.channels import FROZEN, MediaState
from hyperspace.media.frame import TEX_2D
from hyperspace.media.panel import GRAPH, OFF_PAGE, PanelSource
from hyperspace.media.source import FETCHING, LOST, READY
from hyperspace.ui import PAGE_KEYS

sys.path.insert(0, str(Path(__file__).parent))
from test_ui_shell import build_rig, frame, page_frame


class Clock:
    def __init__(self, t: float = 100.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


class FakeLease:
    """`outputs.Lease` in shape: the texture's name, size and generation,
    and the count it holds up while it lives."""

    generation = 1

    def __init__(self, tap, glo: int, size):
        self.tap, self.texture, self.size = tap, glo, tuple(size)
        tap.leases[glo] = tap.leases.get(glo, 0) + 1

    def __del__(self):
        self.tap.leases[self.texture] -= 1


class FakeTap:
    """What `outputs.CanvasTap` shows a source: wanted, the texture written
    last and a lease on it, its size, the grab count and time."""

    def __init__(self):
        self.wants = 0
        self.tex = None
        self.size = None
        self.frame_no = 0
        self.at = 0.0
        self.leases: dict[int, int] = {}

    def want(self):
        self.wants += 1

    def lease(self):
        return None if self.tex is None else FakeLease(self, self.tex.glo, self.size)

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
    assert f.tex_target == TEX_2D and f.frame == 1 and f.t == clock() and f.tex_gen == 1
    assert src.status == READY and src.latest() is f
    # the frame holds its texture: a lease that lives as long as the frame
    assert f.lease is not None and f.lease.texture == 7 and tap.leases == {7: 1}
    # no new grab: the same frame object, so a reader uploads nothing again
    assert src.gl_poll() is f
    # the next grab, another texture: a new frame naming it, and the source
    # letting the first go frees its texture — unless someone else holds it
    clock.t += 0.02
    tap.grab(8, (400, 240), clock())
    g = src.gl_poll()
    assert g is not f and g.texture == 8 and g.frame == 2
    assert tap.leases == {7: 1, 8: 1}       # `f` is still in hand here
    del f
    assert tap.leases == {7: 0, 8: 1}


def test_a_channel_at_rate_0_holds_the_texture_through_the_frames_lease():
    """The exact hold: channel a frozen on the tap's texture 7 while
    channel b reads on — three more grabs, and 7 stays leased (no grab
    writes a leased texture); a's rate back up lets it go."""
    clock, tap = Clock(), FakeTap()
    src = PanelSource(tap, clock=clock)
    r = app.MediaResolver(NS(path=lambda sid: None), builtin={GRAPH: src})
    ms = MediaState(r)
    for c in "ab":
        ms.channels[c].bin[0] = GRAPH
    ms.poll(1 / 60, 1.0)
    tap.grab(7, (400, 240), clock())
    ms.channels["a"].rate = 0.0
    ms.poll(1 / 60, 1.1)                                   # a freezes on 7
    assert ms.status("a") == FROZEN and ms.frame("a").texture == 7
    for glo in (8, 9, 10):
        clock.t += 1 / 60
        tap.grab(glo, (400, 240), clock())
        ms.poll(1 / 60, clock.t)
        assert ms.frame("b").texture == glo                # b live
        assert ms.frame("a").texture == 7                  # a as it was
        assert tap.leases[7] == 1                          # the hold is on
    ms.channels["a"].rate = 1.0
    ms.poll(1 / 60, clock.t)
    assert ms.frame("a").texture == 10 and tap.leases[7] == 0


def test_the_status_runs_fetching_ready_the_hold_off_page_and_back():
    """Opened on GRAPH: `fetching` until the first grab, `ready` with one.
    GRAPH left (the page says it draws no canvas — `on_page`, the panel's
    own fact): the frame holds `HOLD_S` — still `ready`, the picture —
    then the source reads None (black) and says `off page`, never `lost`;
    the first grab back is `ready` again."""
    clock, tap, page = Clock(), FakeTap(), {"on": True}
    src = PanelSource(tap, on_page=lambda: page["on"], clock=clock)
    src.open()
    assert src.status == FETCHING
    tap.grab(7, (400, 240), clock())
    f = src.gl_poll()
    assert src.status == READY
    page["on"] = False                                     # on MEDIA now
    clock.t += live.HOLD_S
    assert src.gl_poll() is f and src.status == READY      # the hold
    clock.t += 0.01
    assert src.gl_poll() is None and src.latest() is None and src.status == OFF_PAGE
    clock.t += 10.0
    assert src.status == OFF_PAGE                          # as long as the page is away
    page["on"] = True
    tap.grab(8, (400, 240), clock())
    assert src.gl_poll().texture == 8 and src.status == READY


def test_off_page_from_the_start_and_lost_only_when_the_page_draws_nothing():
    """A channel opened while on MEDIA says `off page` at once (not a
    second of `fetching` for a frame that cannot come); `lost` is for a
    page that draws and a tap that gets nothing — the window minimised,
    where the backend skips the frame and `grab` draws nothing — and for
    no tap at all. Without `on_page` the page is taken as drawing."""
    clock, tap, page = Clock(), FakeTap(), {"on": False}
    src = PanelSource(tap, on_page=lambda: page["on"], clock=clock)
    src.open()
    assert src.status == OFF_PAGE
    page["on"] = True                                      # GRAPH up, the window minimised
    assert src.status == FETCHING
    for _ in range(3):
        assert src.gl_poll() is None                       # wanted, never grabbed
    clock.t += live.HOLD_S + 0.01
    assert src.status == LOST and src.gl_poll() is None
    headless = PanelSource(None, clock=clock)
    headless.open()
    clock.t += live.HOLD_S + 0.01
    assert headless.status == LOST
    assert PanelSource(FakeTap(), clock=clock).on_page() is True


def test_a_source_picked_again_after_its_last_holder_left_is_fetching():
    """`SharedSource.close` forgets the open time with the last holder, so
    the two subclasses agree: a feed picked again after a while says
    `fetching` for its first `HOLD_S`, not `lost` off a stale open."""
    clock = Clock()
    panel = PanelSource(FakeTap(), clock=clock)
    reader = NS(open=lambda: None, read=lambda: None, close=lambda: None)
    feed = live.LiveSource("ndi:X", reader, clock=clock)
    try:
        for src in (panel, feed):
            src.open()
            assert src.status == FETCHING
            clock.t += live.HOLD_S + 0.5
            assert src.status == LOST
            src.close()
            assert src.held == 0 and src._opened_at is None and src.status == LOST
            clock.t += 30.0
            src.open()                                     # picked again
            assert src.status == FETCHING
            clock.t += live.HOLD_S + 0.01
            assert src.status == LOST
    finally:
        feed.shut()


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


def test_the_source_is_a_shared_source_as_a_live_feed_is():
    """`open` (the frame thread) and `close` (the channels' closer thread)
    count holders under the one lock a live feed uses: the base class in
    `media.live`, the panel source adding `gl_poll` and its words alone."""
    assert issubclass(PanelSource, live.SharedSource)
    assert issubclass(live.LiveSource, live.SharedSource)
    for name in ("open", "close", "latest", "held", "want", "_publish"):
        assert getattr(PanelSource, name) is getattr(live.SharedSource, name)
        assert getattr(live.LiveSource, name) is getattr(live.SharedSource, name)
    assert not hasattr(live.SharedSource, "_publish_pixels")   # the reader's hook is the feed's
    assert PanelSource.status.fget is live.SharedSource.status.fget
    src = PanelSource(FakeTap())
    assert isinstance(src._lock, type(threading.Lock()))
    n = 2000
    go = threading.Barrier(2)

    def opener():
        go.wait()
        for _ in range(n):
            src.open()

    def dropper():
        go.wait()
        for _ in range(n):
            src.close()

    threads = [threading.Thread(target=opener), threading.Thread(target=dropper)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert 0 <= src.held <= n
    for _ in range(src.held):
        src.close()
    assert src.held == 0


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
    assert "resolver.builtin[PANEL_GRAPH] = PanelSource(\n" in src
    assert "panel.canvas_tap, on_page=lambda: panel.canvas_px is not None)" in src
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
        page_frame(rig.panel, "media")                     # the page draws it
        # on MEDIA the page draws no canvas: the row says `off page`, with why
        src.on_page = lambda: rig.panel.canvas_px is not None
        [row] = ui_media.items(rig.panel, 2)
        assert row.status == OFF_PAGE
        assert "GRAPH page is on screen" in ui_media.hint(OFF_PAGE) and ui_media.hint(LOST) == ""
        assert f"{live.HOLD_S:g} s" in ui_media.hint(OFF_PAGE)
        page_frame(rig.panel, "media")


def test_canvas_px_is_recorded_while_the_panel_draws(tmp_path):
    with build_rig(tmp_path) as rig:
        panel = rig.panel
        assert panel.canvas_px is None
        frame(panel, "graph")
        px = panel.canvas_px
        assert px is not None
        _origin, size, scale, page, omit = px
        assert size[0] >= 80 and size[1] >= 80 and scale == (1.0, 1.0)
        assert page.startswith("CONTROLS/##page_") and "/" not in page[len("CONTROLS/"):]
        assert omit[1] > omit[0]                      # plan 49: the pane, selected or not
        frame(panel, "view")
        assert panel.canvas_px is not None            # plan 49 stage 3: GRAPH is always drawn
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
            dec = vtx[ids[cut]]
            # the decorations: on the pane. The border's anti-aliasing fringe
            # lands a vertex a pixel or so outside it (CI's Linux a hair
            # further than the Mac), so the slack is a few px, still far
            # inside anything the canvas draws
            assert on_pane(dec, 4.0).all(), (
                f"decorations off the pane {pos}+{psize}: x {dec['x'].min()}..{dec['x'].max()} "
                f"y {dec['y'].min()}..{dec['y'].max()}") if len(dec) else True
            if c.clip_rect[1] < origin[1]:                     # the window's clip, not the canvas's
                kept = vtx[ids[~cut]]
                assert not on_pane(kept, -16.0).any()          # nothing else inside it (clear of the canvas outline's rounded corners)
