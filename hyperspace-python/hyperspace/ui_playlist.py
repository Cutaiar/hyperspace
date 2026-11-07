"""The playlist's section of the side pane (plan 44 D6b): choose one, play it, and write
one, at the pane's narrowest (`ui_graph.SIDE_MIN`, 240 px).

Top to bottom: the file to play (or a new one by name), play and stop, back and on, the
fade's seconds (`output.xfade_s`), a line saying where it has got to, then the entries,
each its name, its dwell and a × to take it out, and a list to add another from. An edit is
written to the file when it is done (`playlist.save`), so a dwell typed over writes one file
and not one per key, and `Playing` reads the file before each load anyway.

The library's folders are listed only with a list open, and on the poll's cadence
(`ui_loadable.names`), so an open list globs no Drive folder a frame on the machine driving
the room. Nothing here is on an undo stack, so ⌘Z over the section takes nothing back and
says so (`Panel.in_meta_section`, row 709).

Ids for `tests/ui_driver.py`: ``playlist.pick``, ``playlist.name``, ``playlist.new``,
``chip.playlist.play``, ``playlist.next``, ``playlist.prev``, ``playlist.add``,
``playlist.dwell.<n>``, ``playlist.out.<n>``.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import playlist, ui, ui_loadable, ui_media
from .library import LOADABLE, PLAYLISTS, LibraryError, slug
from .playlist import Playlist

STATE = "_playlist_ui"    # on the panel: the name typed for a new one


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
    _, st["name"] = imgui.input_text_with_hint("##playlist.name", "a new list's name", st["name"])
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
    if "output.xfade_s" in panel.reg:
        panel._slider("output.xfade_s")
    install = panel.library.project
    at_launch = bool(p.key) and getattr(install, "plays", None) == p.key
    if imgui.checkbox("start this list at launch##playlist.at_launch", at_launch)[0] and p.key:
        install.play_at_launch(None if at_launch else p.key)
    if imgui.is_item_hovered():
        ui.tooltip("A cart: when the app opens, this list plays by itself. Kept in the install file.")


def _entries(panel, p) -> None:
    entries = p.playlist.entries
    act = None           # one edit a frame, once the rows are drawn: it changes the list
    for i, entry in enumerate(entries):
        imgui.push_id(i)
        mark = "▸ " if p.on and i == p.at else ""
        imgui.text_wrapped(f"{i + 1}  {mark}{entry.loadable}")
        imgui.set_next_item_width(max(60.0, imgui.get_content_region_avail().x
                                      - ui.chip_w("×") - 8))
        _, dwell = imgui.input_float(f"##playlist.dwell.{i}", entry.dwell_s, 0.0, 0.0, "%.0f s")
        if imgui.is_item_deactivated_after_edit():
            act = (p.set_dwell, i, entry.loadable, dwell)
        elif imgui.is_item_hovered():
            ui.tooltip("Seconds from this look's fade to the next one's.")
        ui.beside(ui.chip_w("×"))
        if ui.chip(f"×##playlist.out.{i}"):
            act = (p.remove, i, entry.loadable)
        imgui.pop_id()
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
