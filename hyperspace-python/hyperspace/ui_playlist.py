"""The playlist's section of the side pane (plan 44 D6b): choose one, play it, and write
one, at the pane's narrowest (`ui_graph.SIDE_MIN`, 240 px).

Top to bottom: the file to play (or a new one by name), play and stop, back and on, the
fade's seconds (`output.xfade_s`), a line saying where it has got to, then the entries,
each its name, its dwell and a × to take it out, and a list to add another from. An edit is
written to the file when it is done (`playlist.save`), so a dwell typed over writes one file
and not one per key, and `Playing` reads the file before each load anyway.

The library's folders are listed only with a list open: a closed section costs nothing
and an open one lists no folder a frame, which on the shared Drive is worth keeping.

Ids for `tests/ui_driver.py`: ``playlist.pick``, ``playlist.name``, ``playlist.new``,
``chip.playlist.play``, ``playlist.next``, ``playlist.prev``, ``playlist.add``,
``playlist.dwell.<n>``, ``playlist.out.<n>``.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import playlist, ui
from .library import LOADABLE, PLAYLISTS, LibraryError
from .playlist import Entry, Playlist

STATE = "_playlist_ui"    # on the panel: the name typed for a new one


def _state(panel) -> dict:
    return panel.__dict__.setdefault(STATE, {"name": ""})


def clock(seconds: float) -> str:
    """Seconds as a countdown reads: 4:05."""
    whole = max(0, round(seconds))
    return f"{whole // 60}:{whole % 60:02d}"


def where(p) -> str:
    """The section's line, and the folded header's: where the list has got to."""
    pl = p.playlist
    if pl is None:
        return ""
    n = len(pl.entries)
    if not p.on:
        return f"{pl.name}: stopped · {n} {'entry' if n == 1 else 'entries'}"
    if p.at is None or p.at >= n:
        return f"{pl.name}: starting"
    left = p.left()
    return (f"{pl.name}: {p.at + 1} of {n}, {pl.entries[p.at].loadable}"
            + (f" · next in {clock(left)}" if left is not None else " · next now"))


def _write(panel, p, entries: list[Entry]) -> None:
    """The entries changed: the list as it plays and its file, said if refused."""
    try:
        p.playlist = Playlist(p.playlist.name, entries)
        playlist.save(panel.library, p.playlist)
    except LibraryError as e:
        panel.library.say(warning=str(e))


def _pick(panel, p) -> None:
    imgui.set_next_item_width(-1)
    if imgui.begin_combo("##playlist.pick", p.playlist.name if p.playlist else "choose a list"):
        for name in panel.library.list(PLAYLISTS):
            if imgui.selectable(name, p.playlist is not None and name == p.playlist.name)[0]:
                p.select(name)
        imgui.end_combo()
    st = _state(panel)
    imgui.set_next_item_width(max(60.0, imgui.get_content_region_avail().x - ui.chip_w("new") - 8))
    _, st["name"] = imgui.input_text_with_hint("##playlist.name", "a new list's name", st["name"])
    ui.beside(ui.chip_w("new"))
    if ui.chip("new##playlist.new") and st["name"].strip():
        name = st["name"].strip()
        try:
            playlist.save(panel.library, Playlist(name))
        except LibraryError as e:
            panel.library.say(warning=str(e))
        else:
            st["name"] = ""
            p.select(name)


def _transport(panel, p) -> None:
    panel._lit_button("playlist.play", "stop" if p.on else "play", p.on)
    for pid, label in (("playlist.prev", "back"), ("playlist.next", "on")):
        ui.beside(ui.chip_w(label))
        panel._button(pid, label, small=True)
    if "output.xfade_s" in panel.reg:
        panel._slider("output.xfade_s")


def _entries(panel, p) -> None:
    entries = p.playlist.entries
    out = None
    for i, entry in enumerate(entries):
        imgui.push_id(i)
        mark = "▸ " if p.on and i == p.at else ""
        imgui.text_wrapped(f"{i + 1}  {mark}{entry.loadable}")
        imgui.set_next_item_width(max(60.0, imgui.get_content_region_avail().x
                                      - ui.chip_w("×") - 8))
        _, dwell = imgui.input_float(f"##playlist.dwell.{i}", entry.dwell_s, 0.0, 0.0, "%.0f s")
        if imgui.is_item_deactivated_after_edit():
            out = [*entries]
            out[i] = Entry(entry.loadable, max(playlist.MIN_DWELL_S, float(dwell)), entry.fade_s)
        elif imgui.is_item_hovered():
            ui.tooltip("Seconds from this look's fade to the next one's.")
        ui.beside(ui.chip_w("×"))
        if ui.chip(f"×##playlist.out.{i}"):
            out = [e for k, e in enumerate(entries) if k != i]
        imgui.pop_id()
    imgui.set_next_item_width(-1)
    if imgui.begin_combo("##playlist.add", "add a look"):
        for name in panel.library.list(LOADABLE):
            if imgui.selectable(name, False)[0]:
                out = [*entries, Entry(name)]
        imgui.end_combo()
    if out is not None:
        _write(panel, p, out)


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
