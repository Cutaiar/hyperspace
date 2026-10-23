"""The MEDIA page (plan 32 U, ui_media.py): the missing banner, the
library, the eight channels with their bins, the backdrop's and the
faces' pickers.

Headless, on the shell's rig (tests/test_ui_shell.py): the full registry
over a default `MediaState` (no resolver: every id is missing), a stand-in
media folder and device registry, the page drawn for real and clicked
through imgui's own mouse events. Nothing here opens a source: the page
never may."""

from types import SimpleNamespace as NS

import pytest
from imgui_bundle import imgui
from test_ui_shell import _click, _drawn, _mouse, frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import ui_media
from hyperspace.media.channels import BIN, CHANNELS
from hyperspace.media.folder import Entry
from hyperspace.ui import PAGE_KEYS, Panel


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


class FakeFolder:
    """The media folder's face the page reads: the last scan's entries, a
    thumbnail path (None: not made yet), Add file and Copy to shared."""

    def __init__(self, entries=(), shared=True):
        self.entries = tuple(entries)
        self.changed = 1
        self.shared = "/shared" if shared else None
        self.added: list[str] = []
        self.copied: list[str] = []
        self.thumbs_asked: list[str] = []

    def thumb(self, sid):
        self.thumbs_asked.append(sid)

    def add_file(self, path):
        sid = f"file:{path}"
        self.added.append(sid)
        return sid

    def copy_to_shared(self, sid):
        from concurrent.futures import Future
        if self.shared is None:
            raise ValueError("no shared folder: set [library] path")
        self.copied.append(sid)
        f = Future()
        f.set_result("shared:copy.png")
        return f


def entry(sid, status="ready", kind="still"):
    return Entry(sid, None, kind, 1, 1.0, "", status)


def attach(rig, folder=None, feeds=None):
    """The page's inputs as app.py gives them: the folder and the channels
    (`panel.media`, an `app.MediaIO`), the device registry's live feeds."""
    state = rig.reg.media
    rig.panel.media = NS(folder=folder, state=state)
    if feeds is not None:
        rig.panel.devices = NS(media_feeds=lambda: feeds, devices=[], lines=list)
    return state


def page_state(rig):
    return ui_media._state(rig.panel)


def test_media_tab_replaces_bitmap(rig):
    """The bitmap page is gone; MEDIA stands where it stood, drawn by
    `ui_media.draw`, and draws with no folder, with an empty one and with
    a full one."""
    assert "bitmap" not in PAGE_KEYS and "media" in PAGE_KEYS
    assert PAGE_KEYS.index("media") == PAGE_KEYS.index("faces") + 1
    assert not hasattr(Panel, "_page_bitmap")
    frame(rig.panel, "media")                      # no panel.media at all
    attach(rig, FakeFolder())
    frame(rig.panel, "media")
    attach(rig, FakeFolder([entry("shared:loops/tunnel.mp4", kind="video"),
                            entry("local:me.png"), entry("shared:sync.mov", "fetching")]),
           feeds={"ndi:Resolume": NS(status="connected")})
    for tab in range(3):
        page_state(rig)["tab"] = tab
        frame(rig.panel, "media")
        frame(rig.panel, "media")


def test_banner_lists_missing(rig, monkeypatch):
    """While the bins name sources this Mac lacks, the page opens with one
    line per id — what shows instead (black) said with it; with none, no
    banner."""
    state = attach(rig, FakeFolder())
    drawn = _drawn(monkeypatch)
    frame(rig.panel, "media")
    assert not any("not on this Mac" in s for s in drawn)
    state.assign("a", 0, "local:gone.mp4")
    state.assign("c", 3, "camera:FaceTime HD Camera")
    state.assign("d", 1, "local:gone.mp4")              # once each
    drawn.clear()
    frame(rig.panel, "media")
    lines = [s for s in drawn if "not on this Mac" in s]
    assert len(lines) == 2
    assert "local:gone.mp4" in lines[0] and "camera:FaceTime HD Camera" in lines[1]
    assert all("black" in s for s in lines)
    # many: the first few, then how many more — the page still fits
    for i in range(BIN):
        state.assign("h", i, f"local:x{i}.png")
    drawn.clear()
    frame(rig.panel, "media")
    lines = [s for s in drawn if "not on this Mac" in s]
    assert len(lines) == ui_media.BANNER_LINES
    assert any(s.startswith("and ") and "more" in s for s in drawn)


def test_assign_from_library(rig):
    """A click on a library item picks it; a click on a bin cell then puts
    it there (`MediaState.assign`); a right-click on a cell empties it. A
    click on a cell with nothing picked cues it: the slot param moves,
    through the registry."""
    sid = "shared:loops/tunnel.mp4"
    state = attach(rig, FakeFolder([entry(sid, kind="video"), entry("shared:b.png")]))
    panel = rig.panel
    frame(panel, "media")
    frame(panel)
    st = page_state(rig)
    _click(panel, st["rects"][("item", sid)])
    assert st["pick"] == sid
    _click(panel, st["rects"][("cell", "a", 0)])
    assert state.channels["a"].bin[0] == sid
    _click(panel, st["rects"][("cell", "b", 5)])
    assert state.channels["b"].bin[5] == sid           # the pick stays for another cell
    _click(panel, st["rects"][("cell", "b", 5)], button=1)
    assert state.channels["b"].bin[5] is None
    # nothing picked: a click cues the cell
    st["pick"] = None
    _click(panel, st["rects"][("cell", "a", 3)])
    assert rig.reg["media.a.slot"].base == 3
    assert st["sel"] == "a"


def test_live_feeds_and_this_mac_are_their_own_tabs(rig):
    """Shared, This Mac (the local folder and added files) and Live (the
    device registry's feeds) each list their own; the search narrows."""
    folder = FakeFolder([entry("shared:a.png"), entry("local:b.png"),
                         entry("file:/Users/x/c.mov", kind="video")])
    attach(rig, folder, feeds={"ndi:Resolume": NS(status="connected"),
                               "camera:FaceTime HD Camera": NS(status="ready")})
    st = page_state(rig)
    assert [i.sid for i in ui_media.items(rig.panel, 0)] == ["shared:a.png"]
    assert [i.sid for i in ui_media.items(rig.panel, 1)] == ["local:b.png",
                                                            "file:/Users/x/c.mov"]
    assert [i.sid for i in ui_media.items(rig.panel, 2)] == ["ndi:Resolume",
                                                            "camera:FaceTime HD Camera"]
    st["search"] = "face"
    assert [i.sid for i in ui_media.items(rig.panel, 2)] == ["camera:FaceTime HD Camera"]


def test_copy_to_shared_says_where_it_landed(rig):
    folder = FakeFolder([entry("local:b.png")])
    attach(rig, folder)
    st = page_state(rig)
    st["tab"], st["pick"] = 1, "local:b.png"
    ui_media.copy_to_shared(rig.panel)
    frame(rig.panel, "media")
    assert folder.copied == ["local:b.png"]
    assert "shared:copy.png" in st["said"]
    # no shared folder: said, nothing raised
    attach(rig, FakeFolder([entry("local:b.png")], shared=False))
    ui_media.copy_to_shared(rig.panel)
    assert "[library] path" in st["said"]


def test_page_never_opens_sources(rig, monkeypatch):
    """The page reads the channels and the folder and writes params; it
    never opens, reads or polls a source — an opener that raises, a feed
    whose every call raises and a `frame` that raises never fire, however
    the page is drawn and clicked."""
    calls: list = []

    def opener(*a, **k):
        calls.append(a)
        raise AssertionError("the page opened a source")

    class Feed:
        status = "connected"

        def __getattr__(self, k):
            calls.append(k)
            raise AssertionError(f"the page read the feed's {k}")

    sid = "shared:loops/tunnel.mp4"
    state = attach(rig, FakeFolder([entry(sid, kind="video")]), feeds={"ndi:X": Feed()})
    state.opener = opener
    monkeypatch.setattr(state, "frame", lambda c: (calls.append(("frame", c)), 1 / 0))
    monkeypatch.setattr(state, "poll", lambda *a: (calls.append("poll"), 1 / 0))
    for c in CHANNELS:
        state.assign(c, 0, sid)
    panel = rig.panel
    frame(panel, "media")
    frame(panel)
    st = page_state(rig)
    _click(panel, st["rects"][("item", sid)])
    _click(panel, st["rects"][("cell", "c", 2)])
    for tab in range(3):
        st["tab"] = tab
        frame(panel)
    _mouse(panel, 0, 0)
    assert calls == []
    assert all(ch.source is None for ch in state.channels.values())


def test_the_live_picture_is_the_renderers_never_the_pages(rig):
    """The column's live picture is whatever the renderer read this frame
    (`Renderer.media_shown`); the page asks for the channels it shows
    (`media_watch`) and reads nothing itself."""
    attach(rig, FakeFolder())
    seen: list[str] = []
    rig.panel.renderer = NS(media_watch=set(),
                            media_shown=lambda c: seen.append(c) or None,
                            ui_texture=lambda key: None, ui_upload=lambda *a: None)
    frame(rig.panel, "media")
    assert set(seen) == set(CHANNELS)
    assert set(rig.panel.renderer.media_watch) == set(CHANNELS)


def test_a_thumbnail_is_decoded_once_off_the_ui_thread(rig, tmp_path, monkeypatch):
    """A library item's thumbnail: the folder's PNG decoded on the media
    pool, once per (id, mtime), handed to the renderer to upload; drawn
    from the renderer's texture once it is there."""
    from PIL import Image

    png = tmp_path / "t.png"
    Image.new("RGB", (16, 9), (255, 0, 0)).save(png)
    folder = FakeFolder([entry("shared:a.png")])
    folder.thumb = lambda sid: png
    attach(rig, folder)
    decodes: list = []
    real = ui_media._decode
    monkeypatch.setattr(ui_media, "_decode", lambda p: (decodes.append(p), real(p))[1])
    uploads: dict = {}
    rig.panel.renderer = NS(media_watch=set(), media_shown=lambda c: None,
                            ui_texture=lambda key: uploads.get(key),
                            ui_upload=lambda key, size, data: uploads.setdefault(
                                key, NS(glo=1, size=size)))
    for _ in range(4):
        frame(rig.panel, "media")
        ui_media.wait_thumbs(rig.panel)
    assert len(decodes) == 1
    (key, tex), = uploads.items()
    assert key[0] == "shared:a.png" and tex.size == (16, 9)


def test_the_media_page_fits(rig, monkeypatch):
    """Full: a library of many items, every bin full, a missing banner at
    its most — the page still draws without scrolling at the control size."""
    from test_ui_shell import _page_scroll

    folder = FakeFolder([entry(f"shared:clip{i}.mp4", kind="video") for i in range(40)])
    state = attach(rig, folder)
    for c in CHANNELS:
        for i in range(BIN):
            state.assign(c, i, f"local:missing-{c}{i}.mp4")
    over = _page_scroll(rig, monkeypatch)
    assert over["media"] <= 0
    imgui.get_io().display_size = imgui.ImVec2(820, 820)


def test_a_bin_edit_is_one_undo_step(tmp_path):
    """Putting a source in a cell, or emptying one, is an undo step of its
    own (`undo.push(…, load=True)`: the marks carry the bins), named for
    what it did; undoing it puts the bin back."""
    from test_undo import boot, settle

    r = boot(tmp_path / "home")
    settle(r)
    r.undo.clear()
    panel = NS(reg=r.reg, media=None)
    ui_media.assign(panel, "a", 2, "shared:loops/tunnel.mp4")
    settle(r)
    ui_media.assign(panel, "a", 2, None)
    settle(r)
    assert [s.label for s in r.undo.stack] == ["loops/tunnel.mp4 → A 3", "A 3 emptied"]
    assert r.undo.undo() and r.reg.media.channels["a"].bin[2] == "shared:loops/tunnel.mp4"
    settle(r)
    assert r.undo.undo() and r.reg.media.channels["a"].bin[2] is None


def test_a_big_library_costs_what_is_in_view(rig, tmp_path, monkeypatch):
    """2000 items, scrolled for 120 frames: only the rows in view are drawn
    and ask for thumbnails (a list clipper); decodes are submitted only for
    rows that were drawn, at most `DECODES` at a time; the renderer is
    handed at most `UPLOADS` a frame and uploads at most that many
    (`UiTextures`); no cache is ever cleared wholesale; the listing is not
    rebuilt while the scan stands still."""
    from hyperspace.media_tex import UI_UPLOADS, UiTextures

    n = 2000
    folder = FakeFolder([entry(f"shared:clip{i:04d}.png") for i in range(n)])
    png = tmp_path / "t.png"
    png.write_bytes(b"")
    asked: list[str] = []
    folder.thumb = lambda sid: (asked.append(sid), png)[1]
    attach(rig, folder)
    decodes: list = []
    monkeypatch.setattr(ui_media, "_decode",
                        lambda p: (decodes.append(p), ((4, 4), bytes(64)))[1])
    made: list[int] = []

    class Ctx:
        def texture(self, size, comps, data):
            made[-1] += 1
            return NS(size=size, glo=1, release=lambda: None, repeat_x=0, repeat_y=0)

    ut = UiTextures(Ctx())
    handed: list[int] = []
    rig.panel.renderer = NS(media_watch=set(), media_shown=lambda c: None,
                            ui_texture=ut.get,
                            ui_upload=lambda key, size, data: (handed.__setitem__(
                                -1, handed[-1] + 1), ut.put(key, size, data)))
    drawn: list[list[str]] = []
    row = ui_media._row
    monkeypatch.setattr(ui_media, "_row",
                        lambda panel, st, it: (drawn[-1].append(it.sid), row(panel, st, it)))

    class NoClear(dict):
        def clear(self):
            raise AssertionError("a thumbnail cache cleared wholesale")

    st = page_state(rig)
    st["thumbs"] = NoClear()
    panel = rig.panel
    drawn.append([]), handed.append(0), made.append(0)
    frame(panel, "media")
    listing = st["listing"][1]
    x0, y0, x1, y1 = st["rects"][("item", "shared:clip0000.png")]
    io = imgui.get_io()
    per_frame_asks = []
    for _ in range(120):
        drawn.append([]), handed.append(0), made.append(0)
        before = len(asked)
        io.add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
        io.add_mouse_wheel_event(0.0, -1.0)
        frame(panel)
        ut.upload()                                  # the renderer's end of frame
        ui_media.wait_thumbs(panel)
        per_frame_asks.append(len(asked) - before)
        assert len(st["decoding"]) <= ui_media.DECODES
        assert len(st["thumbs"]) <= ui_media.THUMBS_KEPT
    visible = ui_media.LIST_ROWS + 2                 # the clipper's partial rows
    assert max(len(d) for d in drawn) <= visible
    assert max(per_frame_asks) <= visible
    seen = {sid for d in drawn for sid in d}
    first = sorted(seen)
    assert seen and max(int(s[11:15]) for s in first) < 600   # scrolled, nowhere near 2000
    assert int(first[-1][11:15]) > visible                     # …but it did scroll
    assert len(decodes) <= len(seen)                 # one per row that was drawn, once
    assert max(handed) <= ui_media.UPLOADS and max(made) <= UI_UPLOADS
    assert st["listing"][1] is listing               # not rebuilt: the scan stood still
