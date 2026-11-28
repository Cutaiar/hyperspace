"""The playlist: choose one, play it, and write one. A playlist is the meta
controller's, so it is not in the side pane: a
**playlist** chip on GRAPH's deck row (deck · load… · save as · playlist · copy on air to off air ·
fade; `ui_graph._deck_row`), lit while one plays, its hover saying where it has got to
(`where`), opens these controls in a popup under it (`popup`), `WIDTH` wide.

Top to bottom: the file to play (or a new one by name), play and stop, back and on (the
fade's seconds are the deck row's own, beside its fade), a line saying where it has got
to, then the entries, each one row `ROW_H` tall (a trackpad's target): its place and name,
its dwell and a × to take it out. The entries are a list of their own that scrolls, as tall as the screen leaves under the
popup, so a long list never runs off its edge;
the entry on air is scrolled into view as the popup opens and each time it changes. Under
them, always in view, a list to add another from. An edit is
written to the file when it is done (`playlist.save`), so a dwell typed over writes one file
and not one per key, and `Playing` reads the file before each load anyway.

The library's folders are listed only with a list open, and on the poll's cadence
(`ui_loadable.names`), so an open list globs no Drive folder a frame on the machine driving
the room. Nothing here is on an undo stack, so ⌘Z over the popup takes nothing back and
says so (`Panel.in_meta_section`: the popup sets `UNDER` as the section under
the mouse).

Ids for `tests/ui_driver.py`: ``graph.playlist`` (the chip), ``playlist.pick``,
``playlist.name``, ``playlist.new``, ``chip.playlist.play``, ``playlist.next``,
``playlist.prev``, ``playlist.add``, ``playlist.dwell.<n>``, ``playlist.out.<n>``.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import playlist, ui, ui_loadable, ui_media
from .library import LOADABLE, PLAYLISTS, LibraryError, slug
from .playlist import Playlist

STATE = "_playlist_ui"    # on the panel: the name typed for a new one
POPUP = "graph.playlist.popup"
UNDER = "playlist"        # what `ui_pane.where` says while the mouse is over the popup
WIDTH = 340.0             # px: the popup's width (its height is what it holds)
NAME_MAX = 18             # chars of a list's name the chip shows before eliding
ROW_H = 34.0              # px: an entry's row, its dwell field and its ×: a trackpad's target
DWELL_W = 72.0            # px: an entry's dwell field
OUT_W = 34.0              # px: an entry's ×, square on its row
MIN_ROWS = 3              # the entries' list is never shorter than this many rows
EDGE = 8.0                # px kept between the popup's foot and the screen's
TIP = ("The playlist, for installs: a new look every few minutes, loaded off air and "
       "faded on. Choose a list, play or stop it, edit its looks and dwells")


def _state(panel) -> dict:
    return panel.__dict__.setdefault(STATE, {"name": ""})


def where(p) -> str:
    """The section's line, and the folded header's: where the list has got to."""
    pl = p.playlist
    if pl is None:
        return ""
    n = len(pl.entries)
    if p.on and p.lost:
        left = p.left()
        return (f"{pl.name}: nothing will play now, and what is on air stays"
                + (f" · trying again in {ui_media._mmss(left)}" if left is not None else ""))
    if not p.on:
        return f"{pl.name}: stopped · {n} {'entry' if n == 1 else 'entries'}"
    left = p.left()
    if p.at is None or p.at >= n:
        return f"{pl.name}: " + (f"next in {ui_media._mmss(left)}" if left is not None else "starting")
    return (f"{pl.name}: {p.at + 1} of {n}, {pl.entries[p.at].loadable}"
            + (f" · next in {ui_media._mmss(left)}" if left is not None else " · next now"))


def _pick(panel, p) -> None:
    imgui.set_next_item_width(-1)
    if imgui.begin_combo("##playlist.pick", p.playlist.name if p.playlist else "choose a list"):
        for name in ui_loadable.names(panel, PLAYLISTS):
            if imgui.selectable(name, p.playlist is not None and name == p.playlist.name)[0]:
                p.select(name)
        imgui.end_combo()
    st = _state(panel)
    imgui.set_next_item_width(max(60.0, imgui.get_content_region_avail().x - ui.chip_w("new") - 8))
    _, st["name"] = ui.input_text_with_hint("##playlist.name", "a new list's name", st["name"])
    ui.beside(ui.chip_w("new"))
    if ui.chip("new##playlist.new") and st["name"].strip():
        _new(panel, p, st)


def _new(panel, p, st: dict) -> None:
    """A new, empty list. A name that resolves to a list there is (`Cart!` is `cart`) is
    refused: writing it would empty that list."""
    name, lib = st["name"].strip(), panel.library
    if slug(name) in lib._taken(PLAYLISTS):
        lib.say(warning=f"there is already a list called {name}: choose it, or another name")
        return
    try:
        playlist.save(lib, Playlist(name))
    except LibraryError as e:
        lib.say(warning=str(e))
    else:
        st["name"] = ""
        ui_loadable.invalidate(panel, PLAYLISTS)
        p.select(name)


def _transport(panel, p) -> None:
    panel._lit_button("playlist.play", "stop" if p.on else "play", p.on)
    for pid, label in (("playlist.prev", "back"), ("playlist.next", "on")):
        ui.beside(ui.chip_w(label))
        panel._button(pid, label, small=True)
    install = panel.library.install
    at_launch = bool(p.key) and getattr(install, "plays", None) == p.key
    if ui.checkbox("start this list at launch##playlist.at_launch", at_launch)[0] and p.key:
        install.play_at_launch(None if at_launch else p.key)
    if imgui.is_item_hovered():
        ui.tooltip("A cart: when the app opens, this list plays by itself. Kept in the install file.")


def _room(rows: int) -> float:
    """The entries' height: all `rows` where they fit, else what is left of the screen
    under them, less the add list and the popup's edge, never under `MIN_ROWS` rows."""
    pitch = ROW_H + imgui.get_style().item_spacing.y
    under = imgui.get_frame_height_with_spacing() + 2 * imgui.get_style().window_padding.y + EDGE
    left = imgui.get_io().display_size.y - imgui.get_cursor_screen_pos().y - under
    return max(min(rows, MIN_ROWS) * pitch, min(rows * pitch, left))


def _row(panel, p, i: int, entry, name_w: float):
    """One entry on one row, `ROW_H` tall: its place and name, its dwell, its ×. The edit
    it asks for, or None."""
    act = None
    playing = p.on and i == p.at
    words = f"{'▸' if playing else ' '} {i + 1}  {entry.loadable}"
    imgui.align_text_to_frame_padding()
    imgui.push_style_color(imgui.Col_.text, ui.TEXT if playing else ui.DIM)
    imgui.text(ui.fit_text(words, name_w))
    imgui.pop_style_color()
    if imgui.is_item_hovered():
        ui.tooltip(entry.loadable)
    imgui.same_line(name_w + imgui.get_style().item_spacing.x)
    imgui.set_next_item_width(DWELL_W)
    _, dwell = imgui.input_float(f"##playlist.dwell.{i}", entry.dwell_s, 0.0, 0.0, "%.0f s")
    if imgui.is_item_deactivated_after_edit():
        act = (p.set_dwell, i, entry.loadable, dwell)
    elif imgui.is_item_hovered():
        ui.tooltip("Seconds from this look's fade to the next one's.")
    imgui.same_line()
    if ui.chip(f"×##playlist.out.{i}", imgui.ImVec2(OUT_W, ROW_H)):
        act = (p.remove, i, entry.loadable)
    return act


def _entries(panel, p) -> None:
    """The entries in a list of their own that scrolls: as tall as the screen
    leaves, so forty never run off its edge, with the add list under it. The entry on
    air is scrolled to the list's middle when the popup opens and each time it changes,
    and the hand's scroll is left alone between."""
    entries, st = p.playlist.entries, _state(panel)
    act = None           # one edit a frame, once the rows are drawn: it changes the list
    pad_y = max(imgui.get_style().frame_padding.y, (ROW_H - imgui.get_font_size()) / 2)
    imgui.begin_child("##playlist.entries", imgui.ImVec2(0, _room(len(entries))))
    imgui.push_style_var(imgui.StyleVar_.frame_padding,
                         imgui.ImVec2(imgui.get_style().frame_padding.x, pad_y))
    name_w = max(0.0, imgui.get_content_region_avail().x - DWELL_W - OUT_W
                 - 2 * imgui.get_style().item_spacing.x)
    on_air = p.at if p.on else None
    for i, entry in enumerate(entries):
        imgui.push_id(i)
        act = _row(panel, p, i, entry, name_w) or act
        if i == on_air and st.get("seen") != on_air:
            imgui.set_scroll_here_y(0.5)            # the look on air, into view
            st["seen"] = on_air
        imgui.pop_id()
    imgui.pop_style_var()
    at, size = imgui.get_window_pos(), imgui.get_window_size()
    st["rect"] = (at.x, at.y, at.x + size.x, at.y + size.y)    # (for the tests)
    imgui.end_child()
    imgui.set_next_item_width(-1)
    if imgui.begin_combo("##playlist.add", "add a look"):
        for name in ui_loadable.names(panel, LOADABLE):
            if imgui.selectable(name, False)[0]:
                act = (p.add, name)
        imgui.end_combo()
    if act is not None:
        act[0](*act[1:])
        ui_loadable.invalidate(panel, PLAYLISTS)


def page(panel, dt: float = 0.0) -> None:
    """The section's body."""
    p = getattr(panel, "playing", None)
    if p is None:
        imgui.text_disabled("no playlist here")
        return
    _pick(panel, p)
    if p.playlist is None:
        return
    _transport(panel, p)
    imgui.text_wrapped(where(p))
    imgui.spacing()
    _entries(panel, p)


def label(p) -> str:
    """The deck row's chip: "playlist", or "playlist: <name>" once one is chosen."""
    pl = getattr(p, "playlist", None) if p is not None else None
    if pl is None:
        return "playlist"
    name = pl.name if len(pl.name) <= NAME_MAX else pl.name[:NAME_MAX - 1] + "…"
    return f"playlist: {name}"


def chip(panel, st: dict) -> None:
    """The **playlist** chip on GRAPH's deck row and its popup (`popup`). Lit while a list
    plays; the hover says where it has got to. `st`: GRAPH's state, where ⌘Z reads what
    is under the mouse (``pane_under``). Nothing with no playlist here (a test's panel)."""
    p = getattr(panel, "playing", None)
    if p is None:
        return
    if ui.lit_chip(f"{label(p)}##graph.playlist", bool(p.on)):
        imgui.open_popup(POPUP)
    under = imgui.ImVec2(imgui.get_item_rect_min().x, imgui.get_item_rect_max().y + 4)
    if imgui.is_item_hovered():
        said = where(p)
        ui.tooltip(f"{said}\n\n{TIP}" if said else TIP)
    popup(panel, st, under)


def popup(panel, st: dict, at=None) -> None:
    """The playlist's controls (`page`), in a popup `WIDTH` wide, its corner at `at`
    (under the chip) as it opens, so it never covers the row it came from."""
    if at is not None:
        imgui.set_next_window_pos(at, imgui.Cond_.appearing)
    imgui.set_next_window_size(imgui.ImVec2(WIDTH, 0))
    if not imgui.begin_popup(POPUP):
        return
    if imgui.is_window_appearing():
        _state(panel)["seen"] = None    # the look on air, scrolled to as it opens
    ui._micro("playlist")
    page(panel)
    at, size = imgui.get_window_pos(), imgui.get_window_size()
    st["playlist_rect"] = (at.x, at.y, at.x + size.x, at.y + size.y)    # (for the tests)
    st["playlist_entries_rect"] = _state(panel).get("rect")
    if imgui.is_window_hovered(imgui.HoveredFlags_.child_windows
                               | imgui.HoveredFlags_.allow_when_blocked_by_popup):
        st["pane_under"] = UNDER        # ⌘Z here takes nothing back
    imgui.end_popup()
