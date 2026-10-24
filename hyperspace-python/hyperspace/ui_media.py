"""The MEDIA page (plan 32 U) — the eight channels and what fills them.

Top to bottom:

  missing      while the bins name sources this Mac lacks (`MediaState.
               missing`): one line per id, and what shows instead —
               black. The first `BANNER_LINES`, then how many more.
  library      Shared · This Mac · Live, Add file…; a search box, Copy to
               shared; the list — a thumbnail, the name, the status
               (fetching, missing, error) — of the shared folder, this
               Mac's own folder with the files added by hand, or the
               device registry's live feeds. A click picks an item.
  channels     eight columns, A–H: the live picture, the playhead, the bin
               as sixteen cells (the slot on the channel lit red). A click
               on a cell puts the picked item there; with nothing picked it
               cues the cell (`media.<c>.slot`); a right-click empties it.
               A click on a column's letter selects the channel.
  channel A    the selected channel's transport and fit — rate · jog,
               position · loop, slot · fit — as the panel's own widgets,
               then what is on it, its status and its time.
  backdrop · faces   which channel each is wired to (plan 33 T7: the
               graph's wires into `backdrop.image` and `pattern.media`,
               through a switch at its pick — wired on GRAPH, said here)
               and their alphas; the hint that the desk's cue knob is a jog.

Read across a room in the dark (the restyle of PR #24): the panel's own
widgets and faces, a bin cell lit solid red, a missing source in the
warning colour. No desk binding is made here (row 339: the desk is
Dylan's); Learn on any of the page's params reaches it.

The page only reads and writes. It reads the channels (`MediaState`:
`channels`, `status`, `playhead`, `missing`), the folder's last scan
(`MediaFolder.entries`, `thumb`) and the live feeds' ids; it writes the
registry's params like every page (so Learn, the undo watcher and the
routing see them) and the bins through `MediaState.assign`. It never
opens, reads or polls a source: the frame thread's `MediaState.poll`
opens what a slot names. The live picture is the renderer's — the page
asks for the channels it shows (`Renderer.media_watch`) and draws what
the frame read (`Renderer.media_shown`). A thumbnail is the folder's PNG,
decoded on the media pool once per (id, mtime) and handed to the
renderer to upload in its own frame (`Renderer.ui_upload`), so nothing
here makes a GL object on the control window's context.

A bin edit is one undo step (`assign`: pushed as a load, whose marks
carry the bins). A function over the Panel,
its state on the panel (``panel._media_page``), so a save of this file
lands live (hotreload.MODULES)."""

from __future__ import annotations

import math
import os
from concurrent.futures import Future
from dataclasses import dataclass

from imgui_bundle import imgui

from . import ui, undo
from .graph import source_into, wire_node_kind
from .media import pool
from .media.adapters import VIDEO_EXT
from .media.channels import BIN, CHANNELS, EMPTY
from .media.source import FETCHING, MISSING, READY
from .media.still import STILL_EXT

STATE = "_media_page"      # the panel's attribute: survives a reload of this module
TABS = ("Shared", "This Mac", "Live")
BANNER_LINES = 3           # missing ids drawn one per line; the rest are "and n more"
ROW_H = 34.0               # a library row: its thumbnail's height and padding
LIST_ROWS = 4              # library rows shown before the list scrolls (in its own child)
THUMB_W = 54.0             # a library thumbnail's box (16:9)
GAP = 6.0                  # between two channel columns
CELL_H = 16.0              # a bin cell
CELL_GAP = 2.0
BAR_H = 4.0                # the playhead bar under a channel's picture
THUMBS_KEPT = 512          # decoded thumbnails held for the renderer: the least recently
                           # drawn goes first, one at a time
DECODES = 4                # thumbnail decodes on the media pool at once, at most
UPLOADS = 4                # thumbnails handed to the renderer a frame, at most
MEDIA_FILTER = ["Media", " ".join(f"*{e}" for e in sorted(STILL_EXT | VIDEO_EXT))]
DEAD = imgui.ImVec4(0.10, 0.10, 0.11, 1.0)       # a picture box with nothing in it
FULL = imgui.ImVec4(0.42, 0.42, 0.45, 1.0)       # a bin cell holding a source
JOG_HINT = "Learn the cue knob to media.{c}.jog"


@dataclass(frozen=True)
class Item:
    """One library row: its source id, the name shown, its status (the
    folder's word, or a feed's), kind ("still", "video", "live") and mtime
    (a thumbnail's key with the id: a changed file gets a new one)."""

    sid: str
    name: str
    status: str
    kind: str
    mtime: float = 0.0


def _state(panel) -> dict:
    st = getattr(panel, STATE, None)
    if st is None:
        st = {"tab": 0, "search": "", "pick": None, "sel": "a", "rects": {}, "said": "",
              "dialog": None, "copy": None, "thumbs": {}, "decoding": set(),
              "uploads": 0, "listing": (None, [])}
        setattr(panel, STATE, st)
    return st


def media_of(panel):
    """The channels (`MediaState`): the app's (`panel.media.state`), else the
    registry's own (`build_registry` keeps the one its params write)."""
    io = getattr(panel, "media", None)
    state = getattr(io, "state", None)
    return state if state is not None else getattr(panel.reg, "media", None)


def folder_of(panel):
    return getattr(getattr(panel, "media", None), "folder", None)


def _feeds(panel) -> dict:
    devices = getattr(panel, "devices", None)
    fn = getattr(devices, "media_feeds", None)
    if fn is None:
        return {}
    try:
        return dict(fn())
    except Exception:  # noqa: BLE001 — a device's listing must not take the page down
        return {}


def _name(sid: str) -> str:
    scheme, _, rest = sid.partition(":")
    if scheme == "file":
        return os.path.basename(rest) or rest
    return rest


def items(panel, tab: int) -> list[Item]:
    """The library's rows on tab `tab` (`TABS`), narrowed by the search:
    the shared folder's files, this Mac's (its folder, then the files added
    by hand), or the live feeds the devices have found — no other kind
    (`scan(all=True)`'s "other" is never listed)."""
    st = _state(panel)
    want = (st.get("search") or "").strip().lower()
    out: list[Item] = []
    if tab == 2:
        for sid, feed in _feeds(panel).items():
            out.append(Item(sid, _name(sid), str(getattr(feed, "status", "") or ""), "live"))
        if want:
            out = [i for i in out if want in i.sid.lower()]
        return out
    # a folder's rows: made again only when the scan, the tab or the search
    # moved, so a frame of a big library costs no walk over it
    folder = folder_of(panel)
    entries = getattr(folder, "entries", ()) if folder is not None else ()
    key = (id(folder), id(entries), getattr(folder, "changed", 0), tab, want)
    made, rows = st.get("listing", (None, []))
    if made == key:
        return rows
    heads = ("shared:",) if tab == 0 else ("local:", "file:")
    mine = [e for e in entries if e.sid.startswith(heads) and e.kind in ("still", "video")]
    mine.sort(key=lambda e: heads.index(e.sid.partition(":")[0] + ":"))   # stable
    out = [Item(e.sid, _name(e.sid), e.status, e.kind, e.mtime) for e in mine]
    if want:
        out = [i for i in out if want in i.sid.lower()]
    st["listing"] = (key, out)
    return out


# ---------------------------------------------------------------- the page

def draw(panel, dt: float) -> None:
    st = _state(panel)
    st["rects"] = {}
    st["uploads"] = 0
    _poll_jobs(panel, st)
    state = media_of(panel)
    if state is None:
        panel._section("media")
        imgui.text_disabled("no media channels — app.py builds them")
        return
    y0 = imgui.get_cursor_pos_y()
    _banner(state)
    # the banner's room comes out of the library's list, so the page still fits
    lost = math.ceil((imgui.get_cursor_pos_y() - y0) / ROW_H)
    _library(panel, st, max(1, LIST_ROWS - lost))
    _channels(panel, st, state)
    _selected(panel, st, state)
    _pickers(panel, st)


def _banner(state) -> None:
    """The ids the bins name that this Mac lacks, one per line, while there
    are any (spec U: what shows instead is black)."""
    gone = state.missing()
    if not gone:
        return
    ui._micro("this preset relies on sources this Mac lacks", ui.WARN)
    w = imgui.get_content_region_avail().x
    for sid in gone[:BANNER_LINES]:
        line = f"{sid} — not on this Mac: shows black"
        imgui.text_colored(ui.WARN, ui.fit_text(line, w))
        if imgui.is_item_hovered():
            imgui.set_tooltip(line)
    more = len(gone) - BANNER_LINES
    if more > 0:
        imgui.text_disabled(f"and {more} more — each shows black")
        if imgui.is_item_hovered():
            imgui.set_tooltip("\n".join(gone))


# ---- the library ----

def _library(panel, st: dict, rows_shown: int = LIST_ROWS) -> None:
    folder = folder_of(panel)
    # the last thing done (an add, a copy, an assign) in the title's note
    note = st["said"] or "pick, then click a cell"
    panel._section("library", note=_fit_note("library", note))
    for k, label in enumerate(TABS):
        if k:
            imgui.same_line()
        if ui.lit_chip(f"{label}##media.tab", st["tab"] == k):
            st["tab"] = k
    add = "Add file…"
    imgui.same_line(imgui.get_content_region_avail().x + imgui.get_cursor_pos_x()
                    - ui.chip_w(add))
    imgui.begin_disabled(folder is None)
    if ui.chip(f"{add}##media.add"):
        st["dialog"] = panel.open_file_dialog("Add media", MEDIA_FILTER)
        if st["dialog"] is None:
            st["said"] = panel.dialog_error
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        imgui.set_tooltip("A file anywhere on this Mac, read where it is: listed under "
                          "This Mac. Copy to shared puts it in the cloud folder.")
    copy = "Copy to shared"
    imgui.set_next_item_width(-(ui.button_w(copy) + imgui.get_style().item_spacing.x))
    imgui.push_font(ui._FONTS["ui"], ui.FONT_BASE)
    _, st["search"] = imgui.input_text_with_hint("##media.search", "search", st["search"])
    imgui.pop_font()
    imgui.same_line()
    pick = st["pick"] or ""
    can = (folder is not None and getattr(folder, "shared", None) is not None
           and pick.startswith(("local:", "file:")) and st["copy"] is None)
    imgui.begin_disabled(not can)
    if imgui.button(f"{copy}##media.copy"):
        copy_to_shared(panel)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        imgui.set_tooltip("The picked file copied into the shared folder, so the other Mac "
                          "has it too" if getattr(folder, "shared", None) is not None else
                          "no shared folder: set [library] path in config.toml")
    rows = items(panel, st["tab"])
    if imgui.begin_child("##media.list", imgui.ImVec2(0, rows_shown * ROW_H + 4)):
        if not rows:
            imgui.text_disabled(_empty_words(panel, st["tab"]))
        # only the rows in view are drawn — and only they ask for thumbnails
        clip = imgui.ListClipper()
        clip.begin(len(rows), ROW_H - 4 + imgui.get_style().item_spacing.y)
        while clip.step():
            for k in range(clip.display_start, clip.display_end):
                _row(panel, st, rows[k])
        clip.end()
    imgui.end_child()


def _fit_note(title: str, text: str) -> str:
    """A section note cut to what its title leaves it on the line."""
    room = imgui.get_content_region_avail().x - ui._micro_width(title) - 24
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    out = ui.fit_text(text.upper(), room)
    imgui.pop_font()
    return out


def _empty_words(panel, tab: int) -> str:
    if _state(panel)["search"]:
        return "nothing matches"
    if tab == 2:
        return "no live feeds — Syphon, NDI and cameras listed in config.toml show here"
    if folder_of(panel) is None:
        return "no media folder"
    if tab == 0 and getattr(folder_of(panel), "shared", None) is None:
        return "no shared folder: set [library] path in config.toml"
    return "nothing here yet — Add file…, or drop files in the folder"


def _row(panel, st: dict, it: Item) -> None:
    w = imgui.get_content_region_avail().x
    imgui.invisible_button(f"##item.{it.sid}", imgui.ImVec2(w, ROW_H - 4))
    a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    st["rects"][("item", it.sid)] = (a.x, a.y, b.x, b.y)
    if imgui.is_item_clicked(imgui.MouseButton_.left):
        st["pick"] = None if st["pick"] == it.sid else it.sid
    picked = st["pick"] == it.sid
    dl = imgui.get_window_draw_list()
    if picked:
        dl.add_rect_filled(a, b, ui.u32(ui.FILL), ui.ROUND)
    elif imgui.is_item_hovered():
        dl.add_rect_filled(a, b, ui.u32(ui.LINE), ui.ROUND)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{it.sid}\n{it.status or READY}"
                          + ("" if picked else "\nclick to pick, then click a bin cell"))
    th = ROW_H - 8
    box = (imgui.ImVec2(a.x + 2, a.y + 1), imgui.ImVec2(a.x + 2 + THUMB_W, a.y + 1 + th))
    _thumb(panel, st, it, dl, *box)
    word = "" if it.status in (READY, "", "connected") else it.status.split(":")[0]
    ww = ui._micro_width(word) if word else 0.0
    x = box[1].x + 10
    room = b.x - x - ww - 12
    imgui.push_font(ui._FONTS["ui"], ui.FONT_BASE)
    ty = a.y + (ROW_H - 4 - ui.FONT_BASE) / 2
    dl.add_text(imgui.ImVec2(x, ty), ui.u32(ui.TEXT if it.status in (READY, "connected", "")
                                            else ui.DIM), ui.fit_text(it.name, room))
    imgui.pop_font()
    if word:
        imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
        bad = it.status not in (FETCHING,)
        dl.add_text(imgui.ImVec2(b.x - ww - 6, a.y + (ROW_H - 4 - ui.FONT_MICRO) / 2),
                    ui.u32(ui.WARN if bad else ui.FAINT), word.upper())
        imgui.pop_font()


def _thumb(panel, st: dict, it: Item, dl, p0, p1) -> None:
    """A library item's thumbnail into the box p0–p1, aspect kept; a dark box
    with the item's kind until it is there."""
    tex = None
    r = getattr(panel, "renderer", None)
    if it.kind != "live" and r is not None and hasattr(r, "ui_texture"):
        key = (it.sid, it.mtime)
        tex = r.ui_texture(key)
        if tex is None:
            _want_thumb(panel, st, it, key, r)
    if tex is None:
        dl.add_rect_filled(p0, p1, ui.u32(DEAD), 4.0)
        imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
        word = {"live": "LIVE", "video": "CLIP"}.get(it.kind, "")
        if word:
            tw = imgui.calc_text_size(word).x
            dl.add_text(imgui.ImVec2((p0.x + p1.x - tw) / 2, (p0.y + p1.y - ui.FONT_MICRO) / 2),
                        ui.u32(ui.FAINT), word)
        imgui.pop_font()
        return
    _image(dl, tex.glo, tuple(tex.size), p0, p1, flipped=True)


def _want_thumb(panel, st: dict, it: Item, key, r) -> None:
    """The thumbnail for `key`, drawn row by row (only rows in view ask):
    asked of the folder (which makes it on the pool), decoded on the pool
    once — at most `DECODES` at a time, so a scroll through a big library
    never starves the pool the channels' decodes share — then handed to the
    renderer, at most `UPLOADS` a frame, again whenever the renderer has
    let it go. A thumbnail that would not decode is remembered (False) and
    not tried again while it is kept. The cache is least-recently-drawn:
    past `THUMBS_KEPT` the oldest goes, one at a time."""
    thumbs = st["thumbs"]
    got = thumbs.pop(key, None)
    if got is not None:
        thumbs[key] = got                       # drawn now: the newest
    else:
        busy = st.setdefault("decoding", set())
        busy -= {k for k in busy if not isinstance(thumbs.get(k), Future) or thumbs[k].done()}
        if len(busy) >= DECODES:
            return
        folder = folder_of(panel)
        path = folder.thumb(it.sid) if folder is not None else None
        if path is None:
            return
        try:
            thumbs[key] = pool.submit(_decode, path)
        except RuntimeError:            # the pool is shutting down (app exit)
            return
        busy.add(key)
        while len(thumbs) > THUMBS_KEPT:
            old = next(iter(thumbs))
            gone = thumbs.pop(old)
            if isinstance(gone, Future):
                gone.cancel()            # not started yet: never decoded
        return
    if isinstance(got, Future):
        if not got.done():
            return
        try:
            got = thumbs[key] = got.result()
        except Exception:  # noqa: BLE001 — a bad thumbnail just stays a dark box
            thumbs[key] = False
            return
    if got and st["uploads"] < UPLOADS:
        st["uploads"] += 1
        size, data = got
        r.ui_upload(key, size, data)


def _decode(path) -> tuple[tuple[int, int], bytes]:
    """A thumbnail PNG as RGBA8 rows, top first — on the media pool."""
    from PIL import Image

    with Image.open(path) as im:
        rgba = im.convert("RGBA")
        return rgba.size, rgba.tobytes()


def wait_thumbs(panel, timeout: float = 5.0) -> None:
    """Every thumbnail decode under way finished (tests; never the page)."""
    for f in list(_state(panel)["thumbs"].values()):
        if isinstance(f, Future):
            try:
                f.result(timeout=timeout)
            except Exception:  # noqa: BLE001, S110 — `_want_thumb` says what failed
                pass


def _image(dl, glo: int, size: tuple[int, int], p0, p1, flipped: bool) -> None:
    """Texture `glo` of `size` into the box p0–p1, contained (aspect kept,
    centred). `flipped`: its rows top first (an upload), else GL's."""
    bw, bh = p1.x - p0.x, p1.y - p0.y
    sw, sh = max(size[0], 1), max(size[1], 1)
    k = min(bw / sw, bh / sh)
    w, h = sw * k, sh * k
    x0, y0 = p0.x + (bw - w) / 2, p0.y + (bh - h) / 2
    uv0, uv1 = (imgui.ImVec2(0, 0), imgui.ImVec2(1, 1)) if flipped else (
        imgui.ImVec2(0, 1), imgui.ImVec2(1, 0))
    dl.add_image(imgui.ImTextureRef(glo), imgui.ImVec2(x0, y0), imgui.ImVec2(x0 + w, y0 + h),
                 uv0, uv1)


# ---- Add file… and Copy to shared ----

def _poll_jobs(panel, st: dict) -> None:
    """The file dialog's answer (each picked file added: listed under This
    Mac, the first picked) and a copy's (its new shared id said)."""
    dlg = st.get("dialog")
    if dlg is not None:
        try:
            ready = dlg.ready()
        except Exception:  # noqa: BLE001 — a dialog that died is a dialog closed
            ready, st["dialog"] = False, None
        if ready:
            st["dialog"] = None
            picked = dlg.result() or []
            folder = folder_of(panel)
            if picked and folder is not None:
                sids = [folder.add_file(p) for p in picked]
                st["tab"], st["pick"] = 1, sids[0]
                st["said"] = (f"added {_name(sids[0])}" + (f" and {len(sids) - 1} more"
                              if len(sids) > 1 else "") + " — picked: click a cell")
    fut = st.get("copy")
    if fut is not None and fut.done():
        st["copy"] = None
        try:
            new = fut.result()
        except Exception as e:  # noqa: BLE001 — a failed copy is said, never raised
            st["said"] = f"copy failed: {e}"
        else:
            st["said"] = f"copied to {new}"


def copy_to_shared(panel) -> None:
    """The picked file copied into the shared folder on the pool
    (`MediaFolder.copy_to_shared`); said when it lands."""
    st = _state(panel)
    folder, sid = folder_of(panel), st.get("pick")
    if folder is None or not sid:
        return
    try:
        st["copy"] = folder.copy_to_shared(sid)
    except ValueError as e:              # no shared folder
        st["said"] = str(e)
    except FileNotFoundError:
        st["said"] = f"{sid} is not on this Mac"
    except Exception as e:  # noqa: BLE001
        st["said"] = f"copy failed: {e}"
    else:
        st["said"] = f"copying {_name(sid)} to the shared folder…"
    _poll_jobs(panel, st)


# ---- the eight channels ----

def _status_colour(status: str) -> imgui.ImVec4:
    if status == EMPTY:
        return ui.LINE
    if status in (MISSING, "lost") or status.startswith("error"):
        return ui.WARN
    if status == FETCHING:
        return ui.FAINT
    return ui.DIM


def _channels(panel, st: dict, state) -> None:
    panel._section("channels", note="right-click a cell: empty it")
    r = getattr(panel, "renderer", None)
    if r is not None and hasattr(r, "media_watch"):
        r.media_watch = set(CHANNELS)        # the next frame reads them (`media_shown`)
    avail = imgui.get_content_region_avail().x
    cw = (avail - GAP * (len(CHANNELS) - 1)) / len(CHANNELS)
    top = imgui.get_cursor_screen_pos()
    gone = set(state.missing())
    backdrop = _channel_of(panel, "backdrop.image")
    faces = _channel_of(panel, "pattern.media")
    pic_h = cw * 9 / 16
    bottom = top.y
    dl = imgui.get_window_draw_list()
    for k, c in enumerate(CHANNELS):
        x = top.x + k * (cw + GAP)
        ch = state.channels[c]
        status = state.status(c)
        imgui.set_cursor_screen_pos(imgui.ImVec2(x, top.y))
        if ui.lit_chip(f"{c.upper()}##media.sel.{c}", st["sel"] == c,
                       size=imgui.ImVec2(cw, 0)):
            st["sel"] = c
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"channel {c.upper()}: {status}"
                              + ("\nthe backdrop" if backdrop == c else "")
                              + ("\non the faces" if faces == c else ""))
        y = imgui.get_item_rect_max().y + 4
        p0, p1 = imgui.ImVec2(x, y), imgui.ImVec2(x + cw, y + pic_h)
        dl.add_rect_filled(p0, p1, ui.u32(DEAD), 3.0)
        shown = r.media_shown(c) if r is not None and hasattr(r, "media_shown") else None
        if shown is not None:
            tex, flipped = shown
            _image(dl, tex.glo, tuple(tex.size), p0, p1, flipped)
        dl.add_rect(p0, p1, ui.u32(_status_colour(status)), 3.0, 1.5)
        # who reads it: B the backdrop, F the faces — in the picture's corner
        tags = ("B" if backdrop == c else "") + ("F" if faces == c else "")
        if tags:
            imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
            tw = imgui.calc_text_size(tags).x
            q = imgui.ImVec2(p0.x + 2, p1.y - ui.FONT_MICRO - 3)
            dl.add_rect_filled(q, imgui.ImVec2(q.x + tw + 6, p1.y - 2), ui.u32(DEAD), 3.0)
            dl.add_text(imgui.ImVec2(q.x + 3, q.y), ui.u32(ui.TEXT), tags)
            imgui.pop_font()
        y = p1.y + 3
        head = state.playhead(c)
        dl.add_rect_filled(imgui.ImVec2(x, y), imgui.ImVec2(x + cw, y + BAR_H), ui.u32(ui.LINE))
        if head is not None and head[1] > 0:
            u = min(max(head[0] / head[1], 0.0), 1.0)
            dl.add_rect_filled(imgui.ImVec2(x, y), imgui.ImVec2(x + cw * u, y + BAR_H),
                               ui.u32(ui.RED))
        y += BAR_H + 5
        y = _bin(panel, st, state, c, ch, gone, x, y, cw)
        bottom = max(bottom, y)
    imgui.set_cursor_screen_pos(imgui.ImVec2(top.x, bottom))
    imgui.dummy(imgui.ImVec2(avail, 4))


def _bin(panel, st, state, c, ch, gone, x, y, cw) -> float:
    """Channel `c`'s bin as two columns of eight cells, in reading order;
    the slot on the channel solid red, a held source grey, a missing one
    outlined in the warning colour. Returns the y under it."""
    cell_w = (cw - CELL_GAP) / 2
    on = ch.index()
    dl = imgui.get_window_draw_list()
    pick = st.get("pick")
    for i in range(BIN):
        cx = x + (i % 2) * (cell_w + CELL_GAP)
        cy = y + (i // 2) * (CELL_H + CELL_GAP)
        imgui.set_cursor_screen_pos(imgui.ImVec2(cx, cy))
        hit = imgui.invisible_button(
            f"##cell.{c}.{i}", imgui.ImVec2(cell_w, CELL_H),
            imgui.ButtonFlags_.mouse_button_left | imgui.ButtonFlags_.mouse_button_right)
        a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        st["rects"][("cell", c, i)] = (a.x, a.y, b.x, b.y)
        sid = ch.bin[i]
        if hit:
            if imgui.is_mouse_released(imgui.MouseButton_.right):
                if sid is not None:
                    assign(panel, c, i, None)
            elif pick:
                assign(panel, c, i, pick)
            else:
                slot = panel.reg.get(f"media.{c}.slot")
                if slot is not None:
                    panel._real(slot).set_value(float(i))
            st["sel"] = c
            sid = ch.bin[i]
        if imgui.is_item_hovered():
            words = [f"{c.upper()} {i + 1}: {sid or 'empty'}"]
            if sid in gone:
                words.append("not on this Mac: shows black")
            words.append(f"click: put {_name(pick)} here" if pick else "click: cue it")
            if sid:
                words.append("right-click: empty it")
            imgui.set_tooltip("\n".join(words))
        # the slot on the channel: solid red holding a source, a red ring
        # when it is empty (the channel shows black); a held source grey
        if i == on and sid:
            dl.add_rect_filled(a, b, ui.u32(ui.RED), 3.0)
        elif sid:
            dl.add_rect_filled(a, b, ui.u32(FULL), 3.0)
        if sid in gone:
            dl.add_rect(a, b, ui.u32(ui.WARN), 3.0, 2.0)
        elif i == on and not sid:
            dl.add_rect(a, b, ui.u32(ui.RED), 3.0, 2.0)
        elif not sid:
            dl.add_rect(a, b, ui.u32(ui.LINE), 3.0, 1.0)
    return y + (BIN // 2) * (CELL_H + CELL_GAP)


def assign(panel, c: str, i: int, sid: str | None) -> None:
    """Put `sid` (None: empty) in channel `c`'s cell `i` — one undo step,
    named for what it did. A bin is no param, so the watcher cannot see
    it: the step is pushed as a load (`undo.push(…, load=True)`), whose
    marks carry the bins (`library.Marks`), so undoing it puts the bin
    back. The next `MediaState.poll` opens what the slot now names."""
    state = media_of(panel)
    if state is None or state.channels[c].bin[i] == sid:
        return
    said = (f"{_name(sid)} → {c.upper()} {i + 1}" if sid is not None
            else f"{c.upper()} {i + 1} emptied")
    undo.push(said, load=True)
    state.assign(c, i, sid)
    _state(panel)["said"] = said


def _feed(panel, port: str) -> tuple[str | None, bool]:
    """(the node the loaded graph wires into `port` — `backdrop.image`,
    `pattern.media` — or None, whether a switch is on the way): straight,
    or through a switch at its pick (`graph.source_into`; the picks are the
    view's, `ViewState.switch`). Plan 33 T7: what `backdrop.channel` and
    `view.media` said before they were retired. Nothing with no graph."""
    now = getattr(panel, "graph_now", None)
    try:
        spec = now()[1] if now is not None else None
    except (AttributeError, TypeError):     # a stand-in panel: no graph
        spec = None
    if spec is None:
        return None, False
    wires = spec.all_wires()
    direct = next((w.src for w in wires if w.dst == port), None)
    picks = getattr(getattr(panel, "view", None), "switch", None)
    return source_into(wires, port, picks), wire_node_kind(direct) == "switch"


def _channel_of(panel, port: str) -> str | None:
    """The channel the loaded graph feeds `port` with (`_feed`), or None:
    nothing wired, a switch off, or a picture that is no channel's own."""
    src, _ = _feed(panel, port)
    c = src.partition(".")[2] if wire_node_kind(src) == "media" else None
    return c if c and c in CHANNELS else None


def feed_words(panel, port: str) -> str:
    """What feeds `port`, in words: `channel A`, `channel A (switch)`, `acid.2`
    (a picture through effects), `off (switch)`, or `nothing wired`."""
    src, switched = _feed(panel, port)
    via = " (switch)" if switched else ""
    if src is None:
        return f"off{via}" if switched else "nothing wired"
    c = _channel_of(panel, port)
    return f"channel {c.upper()}{via}" if c else f"{src}{via}"


# ---- the selected channel ----

def _selected(panel, st: dict, state) -> None:
    c = st["sel"] if st["sel"] in CHANNELS else "a"
    ch = state.channels[c]
    status = state.status(c)
    # the hint is the title's note: the desk is Dylan's (row 339), so no
    # binding is made — Learn the cue knob (a relative encoder) to the jog
    title = f"channel {c.upper()} · {status.split(':')[0]}"
    panel._section(title, note=_fit_note(title, JOG_HINT.format(c=c)))
    if imgui.begin_table(f"##media.{c}", 2, imgui.TableFlags_.sizing_stretch_same):
        for left, right in (("rate", "jog"), ("pos", "loop"), ("slot", "fit")):
            imgui.table_next_column()
            panel.half(f"media.{c}.{left}", "position" if left == "pos" else left)
            imgui.table_next_column()
            panel.half(f"media.{c}.{right}", right)
        imgui.end_table()
    sid = ch.bin[ch.index()]
    head = state.playhead(c)
    clock = f"{_mmss(head[0])} / {_mmss(head[1])}" if head is not None else ""
    w = imgui.get_content_region_avail().x - (ui._readout_width(clock) + 8 if clock else 0)
    imgui.align_text_to_frame_padding()
    imgui.text_colored(ui.TEXT if sid else ui.FAINT,
                       ui.fit_text(sid if sid else f"slot {ch.index() + 1} is empty", w))
    if sid and imgui.is_item_hovered():
        imgui.set_tooltip(sid)
    if clock:
        imgui.same_line(imgui.get_content_region_avail().x + imgui.get_cursor_pos_x()
                        - ui._readout_width(clock))
        ui._readout(clock, ui.DIM)


def _mmss(s: float) -> str:
    s = max(float(s), 0.0)
    return f"{int(s // 60)}:{int(s % 60):02d}"


# ---- the backdrop and the faces ----

def _pickers(panel, st: dict) -> None:
    panel._section("backdrop · faces", note="which picture each draws · wired on GRAPH")
    if imgui.begin_table("##media.pickers", 2, imgui.TableFlags_.sizing_stretch_same):
        # plan 33 T7: the channel is the graph's wire, said here (GRAPH wires it)
        for port, label in (("backdrop.image", "backdrop"), ("pattern.media", "faces")):
            imgui.table_next_column()
            panel._label_cell(label, width=ui.HALF_LABEL_W)
            imgui.align_text_to_frame_padding()
            imgui.text_colored(ui.TEXT, feed_words(panel, port))
            if imgui.is_item_hovered():
                imgui.set_tooltip(f"what the graph wires into {port}: rewire it on GRAPH")
        for pid in ("backdrop.alpha", "view.media_alpha"):
            imgui.table_next_column()
            if pid in panel.reg:
                panel.half(pid, "alpha")
        imgui.end_table()
