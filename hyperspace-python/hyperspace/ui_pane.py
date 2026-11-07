"""GRAPH's side pane: one viewer, showing one thing at a time (plan 49,
then the single viewer of 2026-11-07).

GRAPH is the panel: always drawn. The pane is always beside the canvas (or
under it, on a narrow page) and shows **one view** at the pane's full
height:

- **selection**: the selected thing's details (`ui_graph._side`), or,
  with nothing selected, a line saying so;
- every other section (`SECTIONS`): the body that was a page, drawn by
  the page's own function (`Panel._page_loadable`, `ui_fx.page`, …), so a
  section is one row there.

**The view is `ui.page`.** `Panel.page`, an index into `ui.PAGE_KEYS`, is
the one owner of what the pane shows (`showing`): a section's own slot
shows it, and GRAPH's slot shows the selection (the canvas is always
there, so "graph" means "what is selected on it"). Everything that moves
the view moves `ui.page`, so ⌘[ / ⌘] (`ui.PageHistory`) step back and
forward through every view the pane has shown, whatever moved it: a chip,
the sections menu, a node's **open on …**, the **←** back chip, a key row, a
pad, a click on a node.

**Every view has a mouse route** (Dillon, 2026-11-07: nothing
stranded). Over the body, a row of chips (`_bar`) wrapping at the pane's
edge: **selection** and the six sections no canvas node leads to (`TABS`:
patches, audio, routing, playlist, players, system), then a **sections**
chip whose menu holds the other eleven (`MENU`, each also a node's
**open on …**). The lit chip is the view; the menu's chip names the view
while it is one of the eleven. A section opened from the selected node's
**open on …** has a **← <node>** chip back to it (`draw`'s `home`).

**A click on the canvas shows the selection** (`ui_graph.page`): a node,
a cable or a group picked by the mouse brings the selection view up, so
what was clicked is what the pane shows. A selection made by code (FX's
show on GRAPH, OUTPUT's open on GRAPH, a controller) leaves the view
where it is: the section being worked in is not thrown away.

Each section's body is a child of its own (``pane.<key>/##body``), so it
scrolls by itself and imgui keeps each one's scroll: back to a section is
back to where it was. Which view is up is not kept between launches: the
app opens on the selection, as `Panel.page` starts on GRAPH's slot. (The
folds plan 49 kept in ``<machine>/ui.json`` as ``pane.open`` and
``pane.below`` are no longer read or written; a file holding them keeps
them.)

**Ids.** A widget in a section carries the label it carries on its page
— `##<param id>` for every param widget — so the panel driver
(`tests/ui_driver.py`, which finds a control by what follows ``##``),
Learn's framing and the right-click menu find it as on the page. imgui's
own id is the label hashed under the id stack, and each section's body
is drawn under ``push_id("pane.<key>")`` inside the pane's child. Each
view's chip, and each menu row, is ``##pane.<key>``; the menu's chip is
``##pane.sections`` and the back chip ``##pane.back``.

**Narrow.** The pages were laid out for the panel's width; at the pane's
(`ui_graph.SIDE_MIN`, 240 px, at the narrowest) a chip or a tick that
would pass the right edge starts a new row (`ui.beside`), and the MEDIA
grid, the SEQ grid, the LFO and envelope strips and the OUTPUT blocks
lay themselves out for the room they are given (plan 49, stage 2), as do
VIEW's rows, ROUTING's head, HANDS and SYSTEM (stage 3). In the narrow
band under the canvas a section's view grows the band
(`ui_graph.band_height`); the selection's keeps it `BELOW_H`.

**Cost.** The body drawn has its time kept (``st["pane_ms"]``, a running
mean) and the SYSTEM page says it under GRAPH's own line (`timing_line`).
One body draws a frame, so the pane costs one section, never all of them.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path

from imgui_bundle import imgui

from . import library, ui, ui_fx, ui_loadable, ui_players, ui_playlist, undo

UI_FILE = "ui.json"      # <machine>/ui.json: this Mac's panel settings


# each body looked up as it is called, so a hot reload of its page lands; the
# `Panel._page_<key>` methods are the bodies' one name (the fx browser has
# no page of its own: the FX page went with stage 2)
def _fx(panel, dt: float) -> None:
    ui_fx.page(panel, dt)


def _paged(key: str) -> Callable:
    def body(panel, dt: float) -> None:
        getattr(panel, f"_page_{key}")(dt)
    return body


def _wrapped(key: str) -> Callable:
    """A body of long status lines (HANDS, SYSTEM: paths, device lines,
    timings): in the pane's width they wrap rather than run off its edge."""
    def body(panel, dt: float) -> None:
        imgui.push_text_wrap_pos(0.0)
        try:
            getattr(panel, f"_page_{key}")(dt)
        finally:
            imgui.pop_text_wrap_pos()
    return body


# (key, title, the groups for its dirty dot, the body — the page's own
# draw; None for selection, whose body `draw` is handed), in the sections
# menu's order: the graph's own things first (what is selected, the loadable patch, the shape,
# its effects and pictures), then the voices that move them and the desk's
# rows, then the room and the meta controller
SECTIONS: tuple[tuple[str, str, tuple[str, ...], Callable | None], ...] = (
    ("selection", "selection", (), None),
    ("loadable", "patches", ("loadable",), _paged("loadable")),
    ("view", "view", ("view",), _paged("view")),
    ("fx", "fx", ("fx",), _fx),
    ("lookback", "lookback", ("dream",), _paged("lookback")),
    ("faces", "faces", ("pattern",), _paged("faces")),
    ("media", "media", ("media", "backdrop"), _paged("media")),
    ("lfo", "lfo", ("lfo", "tempo"), _paged("lfo")),
    ("seq", "seq", ("seq", "env"), _paged("seq")),
    ("hands", "hands", ("hands",), _wrapped("hands")),
    ("routing", "routing", (), _paged("routing")),
    ("analyzer", "analyzer", ("band",), _paged("analyzer")),
    ("audio", "audio", ("master",), _paged("audio")),
    ("camera", "camera", ("camera",), _paged("camera")),
    ("output", "output", ("output",), _paged("output")),
    ("playlist", "playlist", (), _paged("playlist")),
    ("system", "system", (), _wrapped("system")),
    ("players", "players", (), _paged("players")),
)
KEYS = tuple(k for k, *_ in SECTIONS)
SELECTION = "selection"
# the views with a chip of their own: the selection, and the sections no canvas
# node's "open on …" leads to (`ui_graph.home_page`), so the mouse reaches them
TABS = (SELECTION, "loadable", "audio", "routing", "playlist", "players", "system")
MENU = tuple(k for k in KEYS if k not in TABS)  # the sections chip's menu: the rest, in order
ROUTING = "routing"      # the section a picked desk control never dims (`_body`)
CHIP_MAX = 220.0         # px: the most a chip's words take
WRITE_AFTER_S = 0.5      # a setting in ui.json is written this long after the last change
COST_KEEP = 0.9          # a body's running mean: this much the last mean, the rest the newest
NOTHING = "nothing selected — click a node, a cable or a group on the canvas"
VIEW_TIP = "Show this in the pane (⌘[ / ⌘] step back and forward)"
MENU_TIP = "The sections a node on the canvas leads to: show one in the pane"
BACK_TIP = "Back to what is selected on the canvas"


# ---------------------------------------------------------------- ui.json

def read_doc(machine) -> dict:
    """``<machine>/ui.json`` as a dict (`library._read_json`); {} for no
    file, an unreadable one or one that is not an object. Never raises."""
    try:
        return library._read_json(Path(machine) / UI_FILE)
    except (library.LibraryError, TypeError):
        return {}


def write_doc(machine, doc: dict, who: str = "panel") -> None:
    """Write `doc` as ``<machine>/ui.json``, atomically
    (`library._write_text`); a failed write says so on stderr (as `who`)
    and costs only the memory."""
    try:
        library._write_text(Path(machine) / UI_FILE, library._json_text(doc))
    except (library.LibraryError, OSError, TypeError) as e:
        print(f"{who}: {UI_FILE} not written ({e})", file=sys.stderr)


def write_key(machine, key: str, value, who: str = "panel") -> None:
    """Keep `value` as ui.json's top-level `key`, the rest of the file as
    it was — for another module's own key (the loadable patches' folds,
    ``presets``, plan 48 stage 2), deferred by its caller `WRITE_AFTER_S`
    after its last change."""
    doc = read_doc(machine)
    doc[key] = value
    write_doc(machine, doc, who)


# ---------------------------------------------------------------- the view

def section_of(page: str | None) -> str:
    """The view `ui.PAGE_KEYS`' name `page` shows: the section of its name,
    the selection for GRAPH's (the canvas is always there), or for a name
    that is no section."""
    return page if page in KEYS else SELECTION


def slot_of(key: str) -> int:
    """`key`'s index in `ui.PAGE_KEYS`: the selection's is GRAPH's slot."""
    return ui.PAGE_KEYS.index("graph" if key == SELECTION else key)


def showing(panel) -> str:
    """The view the pane shows: what `Panel.page`, its one owner, names
    (`ui.page`, the history and this always agree)."""
    page, keys = getattr(panel, "page", None), ui.PAGE_KEYS
    return section_of(keys[page]) if isinstance(page, int) and 0 <= page < len(keys) else SELECTION


def show(panel, key: str) -> None:
    """Show view `key` in the pane: through ``ui.page`` (so its history, ⌘[
    / ⌘], has it too), straight on `Panel.page` for a panel without the
    param."""
    k = slot_of(key)
    if "ui.page" in getattr(panel, "reg", ()):
        panel.reg["ui.page"].set(k)
    else:
        panel.page = k


def where(panel) -> str | None:
    """The section you are in, for ⌘Z (plan 44 D5b): the one under the mouse, as of
    the latest draw; anywhere else (the canvas, a header, the desk, the render
    window) none. Never the focus: a click in another section leaves it, and a
    key row or a pad moves it, so it would say "analyzer" an hour on."""
    from . import ui_graph  # (late: ui_graph imports this module)
    return (panel.__dict__.get(ui_graph.STATE) or {}).get("pane_under")


def _working() -> bool:
    """Is the person working the panel, as far as a frame's start can say (`undo.by_hand`)?
    A button down or just released, or an item live. Not a text field: one stays live with
    nobody at it for as long as the cursor sits there, so a text field's writers report
    their own write, `undo.by_hand(True)` where they write (row 757)."""
    return (any(imgui.is_mouse_down(b) or imgui.is_mouse_released(b) for b in (0, 1))
            or (imgui.is_any_item_active() and not imgui.get_io().want_text_input))


def left(panel) -> None:
    """A frame's draw begins: nothing is under the mouse until the draw says so, so
    a panel hidden or collapsed says nothing is (`where`, `Panel.in_meta_section`)."""
    from . import ui_graph  # (late: ui_graph imports this module)
    undo.by_hand(_working())
    panel._param_under = None
    st = panel.__dict__.get(ui_graph.STATE)
    if st is not None:
        st["pane_under"] = None


def shown(panel, key: str) -> bool:
    """Did section `key`'s body draw (the latest draw; a body scrolled out of
    the pane's view does not): is it on screen, for the words of whoever
    is not the pane."""
    from . import ui_graph  # (late: ui_graph imports this module)
    st = panel.__dict__.get(ui_graph.STATE) or {}
    return key in (st.get("pane_drawn") or ())


# ---------------------------------------------------------------- drawing

def draw(panel, st: dict, dt: float, selection: Callable[[], None] | None,
         said: str = "", home: str | None = None) -> None:
    """The pane inside the pane's child: the row of chips (`_bar`), then the
    view's body at all the height left. `selection` draws the selected
    thing's details (None: nothing is selected, and the view says so);
    `said` names it on its chip. `home`: the section the selected node's
    **open on …** leads to — shown, it has a **←** chip back to the
    selection."""
    key = showing(panel)
    # the sections whose bodies drew: last frame's for `timing_line`, which
    # the SYSTEM section asks mid-draw (the tests read this frame's)
    st["pane_last"] = st.get("pane_drawn") or []
    drawn = st["pane_drawn"] = []
    _bar(panel, key, said)
    if home is not None and key == home and key != SELECTION and said:
        most = min(CHIP_MAX, imgui.get_content_region_avail().x - 2 * ui.CHIP_PAD.x)
        if ui.chip(ui.fit_text(f"←  {said}", most) + "##pane.back"):
            show(panel, SELECTION)
        if imgui.is_item_hovered():
            ui.tooltip(BACK_TIP)
    imgui.separator()
    body = next(b for k, _, _, b in SECTIONS if k == key)
    _body(panel, st, key, body, dt, selection, 0.0, drawn)


def _bar(panel, key: str, said: str) -> None:
    """The views' chips: `TABS`, then the **sections** chip and its menu
    (`MENU`), each lit while it is the view, a chip that would pass the
    pane's edge starting the next row. A click shows what it names."""
    titles = {k: t for k, t, _, _ in SECTIONS}
    groups = {k: g for k, _, g, _ in SECTIONS}
    for i, k in enumerate(TABS):
        if _chip(panel, f"pane.{k}", titles[k].upper(), k == key, _said(panel, k, said),
                 _dirty(panel, groups[k]), first=i == 0, tip=VIEW_TIP):
            show(panel, k)
    words = f"{titles[key].upper()}  ▾" if key in MENU else "SECTIONS  ▾"
    if _chip(panel, "pane.sections", words, key in MENU, "",
             any(_dirty(panel, groups[k]) for k in MENU), first=False, tip=MENU_TIP):
        imgui.open_popup("##pane.menu")
    if imgui.begin_popup("##pane.menu"):
        imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
        try:
            for k in MENU:
                hit, _ = imgui.selectable(f"{titles[k].upper()}##pane.{k}", k == key)
                if _dirty(panel, groups[k]):
                    _dot()
                if hit:
                    show(panel, k)
        finally:
            imgui.pop_font()
        imgui.end_popup()


def _dirty(panel, groups) -> bool:
    """Has a section's group moved off its loadable patch (the rail's dot)."""
    return any(ui_loadable.dirty(panel, g, polled=True) for g in groups)


def _dot() -> None:
    """The dirty dot at the right of the item just drawn."""
    lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    imgui.get_window_draw_list().add_circle_filled(
        imgui.ImVec2(hi.x - ui.HEADER_DOT_R - 3, (lo.y + hi.y) / 2), ui.HEADER_DOT_R,
        ui.u32(ui.RED))


def _body(panel, st: dict, key: str, body, dt: float, selection, h: float,
          drawn: list) -> None:
    """Section `key`'s body, `h` tall (0: all the height left), under its
    own id: the page's draw, or the selection's details (or words saying
    there is none). Its time is kept for the SYSTEM section
    (`timing_line`). While a desk control is picked every body but
    ROUTING's is drawn disabled, and a click on a param is
    `Panel._ctx_pick`'s (ROUTING: the picked control's own line is what the
    user came for)."""
    picking = getattr(panel, "_picking", False)
    dim = panel._picking = picking and key != ROUTING
    imgui.push_id(f"pane.{key}")
    if dim:
        imgui.begin_disabled()
    try:
        if imgui.begin_child("##body", imgui.ImVec2(0, h)):
            if imgui.is_window_hovered(imgui.HoveredFlags_.child_windows):
                st["pane_under"] = key     # what ⌘Z goes by (`where`)
            t0 = time.perf_counter()
            if body is not None:
                body(panel, dt)
            elif selection is None:
                imgui.text_wrapped(NOTHING)
            else:
                selection()
            drawn.append(key)
            ms = (time.perf_counter() - t0) * 1000.0
            cost = st.setdefault("pane_ms", {})
            cost[key] = ms if key not in cost else COST_KEEP * cost[key] + (1 - COST_KEEP) * ms
        imgui.end_child()
    finally:
        if dim:
            imgui.end_disabled()
        imgui.pop_id()
        panel._picking = picking


def timing_line(panel) -> str:
    """The SYSTEM section's line for the pane (plan 49 stage 2): each
    section whose body drew last frame, its running mean in ms, the dearest
    first — "" until one has. GRAPH's own line above this one times the
    whole panel, these included."""
    from . import ui_graph  # (late: ui_graph imports this module)
    st = panel.__dict__.get(ui_graph.STATE) or {}
    cost, shown = st.get("pane_ms") or {}, st.get("pane_last") or []
    got = sorted(((cost[k], k) for k in shown if k in cost), reverse=True)
    if not got:
        return ""
    return "side pane: " + "  ·  ".join(f"{k} {ms:.2f}" for ms, k in got) + " ms"


def _said(panel, key: str, said: str) -> str:
    """What a chip names beside its title: the selection's what is selected;
    the playlist's where it is; the players' who is where."""
    if key == "selection":
        return said
    if key == "playlist" and getattr(panel, "playing", None) is not None:
        return ui_playlist.where(panel.playing)
    return ui_players.summary(panel) if key == "players" else ""


def _chip(panel, cid: str, title: str, lit: bool, said: str, dot: bool,
          first: bool, tip: str) -> bool:
    """One chip of the bar: `title` in the micro face with `said` after it,
    as wide as its words (at most `CHIP_MAX`, and never past the pane's
    edge), lit while `lit`, a dot where
    its section's group has moved off its loadable patch, on the row of the
    chip before it (`first`: there is none) unless it would pass the edge.
    True when clicked."""
    room = 2 * ui.HEADER_DOT_R + 12 if dot else 0.0
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)   # measured in the face it is drawn in
    try:
        pad = 2 * imgui.get_style().frame_padding.x
        # (the cursor is at a row's start here: the room is the whole row's)
        most = min(CHIP_MAX, imgui.get_content_region_avail().x - room - pad)
        words = ui.fit_text(f"{title}  ·  {said}" if said else title, most)
        size = imgui.ImVec2(imgui.calc_text_size(words).x + room, 0)
        if not first:               # a selectable pads its words by the frame's padding
            ui.beside(size.x + pad)
        hit, _ = imgui.selectable(f"{words}##{cid}", lit, 0, size)
    finally:
        imgui.pop_font()
    if imgui.is_item_hovered():
        ui.tooltip(tip)
    if dot:
        _dot()
    return bool(hit)
