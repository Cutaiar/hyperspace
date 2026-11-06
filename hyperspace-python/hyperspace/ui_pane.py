"""GRAPH's side pane, always on, as folding sections (plan 49, all three stages).

GRAPH is the panel: always drawn (stage 3 took the rail away). The pane is
always beside the canvas (or under it, on a narrow page) and holds a stack
of sections, each a header that folds and unfolds by a click:

- **selection** — the selected thing's details (`ui_graph._side`), or, with
  nothing selected, a line in words saying so;
- every other section (`SECTIONS`) — the body that was a page, drawn by the
  page's own function (`Panel._page_presets`, `ui_fx.page`, …), so a
  section is one row there.

**The focus** (stage 3). `ui.page` no longer switches a page: what a key
row, a pad or ⌘[ / ⌘] moves names a section (`ui.PAGE_KEYS`, by index, so
every saved binding keeps its meaning; `section_of`). `Panel.page` is the
one owner of the focus (`focused` reads it); the pane's next draw scrolls to
the section (`scroll_to`), shows it however it is folded and gives it the
room under the headers (`draw`). The focus does not touch the fold: the
section goes back to what a click left it when the focus moves on (a walk
through the sections leaves no pile of open ones) or lets go (`ui.page` on
GRAPH's slot; a click on its own header, `let_go`). A click on another
header beside the canvas leaves the focus alone. In the narrow band the
focused section is the only body, the only lit chip, the band grows to
leave `CANVAS_MIN` of canvas (`ui_graph.band_height`) and a click on any
chip lets go and shows what it asked for.

The open sections share the pane's height evenly; each body is a child
of its own, so a long one scrolls by itself. Beside the canvas a body is
never under `MIN_BODY_H` (past that the pane scrolls). On a narrow page
the pane is #266's band under the canvas: there the headers are rows of
chips (a chip that would pass the edge starts the next row: sixteen do not
fit one) and the bodies share the rest with no floor, so one open
section has the whole band.

Which sections are open is this Mac's, kept in ``<machine>/ui.json``
beside the pane's width (``graph.side_w``): ``pane.open`` for the column
beside the canvas (selection and presets open at first), ``pane.below``
for the narrow page's band (selection alone at first). A click is
written `WRITE_AFTER_S` after the last one (`flush`; `ui_graph.close`
writes what is left), atomically (`library._write_text`). A selection
never unfolds a section: a folded **selection** header names what is
selected.

**Ids.** A widget in a section carries the label it carries on its page
— `##<param id>` for every param widget — so the panel driver
(`tests/ui_driver.py`, which finds a control by what follows ``##``),
Learn's framing and the right-click menu find it as on the page. imgui's
own id is the label hashed under the id stack, and each section's body
is drawn under ``push_id("pane.<key>")`` inside the pane's child, so a
section's ids never collide with another's (the presets section and the
lookback section both draw preset strips). Each header is ``##pane.<key>``
for the driver.

**Narrow.** The pages were laid out for the panel's width; at the pane's
(`ui_graph.SIDE_MIN`, 240 px, at the narrowest) a chip or a tick that
would pass the right edge starts a new row (`ui.beside`), and the MEDIA
grid, the SEQ grid, the LFO and envelope strips and the OUTPUT blocks
lay themselves out for the room they are given (plan 49, stage 2), as do
VIEW's rows, ROUTING's head, HANDS and SYSTEM (stage 3).

**Cost.** Each drawn body's time is kept (``st["pane_ms"]``, a running
mean) and the SYSTEM page says it under GRAPH's own line
(`timing_line`); a body scrolled out of the pane's view is not drawn
(imgui skips the child), so it costs nothing.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path

from imgui_bundle import imgui

from . import library, ui, ui_fx, ui_players, ui_presets, undo

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
# draw; None for selection, whose body `draw` is handed): down the pane,
# the graph's own things first (what is selected, the preset, the shape,
# its effects and pictures), then the voices that move them and the desk's
# rows, then the room and the rig
SECTIONS: tuple[tuple[str, str, tuple[str, ...], Callable | None], ...] = (
    ("selection", "selection", (), None),
    ("presets", "presets", ("presets",), _paged("presets")),
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
    ("system", "system", (), _wrapped("system")),
    # last, so focused it has the pane: a body has the room under the headers after it
    ("players", "players", (), _paged("players")),
)
KEYS = tuple(k for k, *_ in SECTIONS)
# beside the canvas: selection and presets open at first (stage 1); every
# section stages 2 and 3 added folded (rec: a fresh Mac's pane reads as it did)
DEFAULT_OPEN = {k: k in ("selection", "presets") for k in KEYS}
DEFAULT_BELOW = {k: k == "selection" for k in KEYS}     # the narrow page's band
LAYOUTS = {"open": DEFAULT_OPEN, "below": DEFAULT_BELOW}   # ui.json's pane.<layout>
ROUTING = "routing"      # the section a picked desk control never dims (`_body`)
MIN_BODY_H = 150.0       # beside the canvas, an open body is never shorter (the pane scrolls)
CHIP_MAX = 220.0         # px: the most a band header's words take
WRITE_AFTER_S = 0.5      # a fold is written this long after the last click
COST_KEEP = 0.9          # a body's running mean: this much the last mean, the rest the newest
NOTHING = "nothing selected — click a node, a cable or a group on the canvas"
OPEN_TIP = "Fold or unfold this section (kept on this Mac)"


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
    it was — for another module's own key beside the pane's (the presets'
    folds, ``presets``, plan 48 stage 2), deferred by its caller as
    `flush` defers the pane's (`WRITE_AFTER_S`)."""
    doc = read_doc(machine)
    doc[key] = value
    write_doc(machine, doc, who)


def read_open(machine, layout: str = "open") -> dict[str, bool]:
    """Which sections this Mac keeps open in `layout` ("open": beside the
    canvas; "below": the narrow page's band): its defaults overlaid with
    ``pane.<layout>`` from ui.json, a key that is not a section or a value
    that is not a bool ignored."""
    got = dict(LAYOUTS[layout])
    pane = read_doc(machine).get("pane") if machine is not None else None
    held = pane.get(layout) if isinstance(pane, dict) else None
    if isinstance(held, dict):
        for k, v in held.items():
            if k in got and isinstance(v, bool):
                got[k] = v
    return got


def write_open(machine, opened: dict[str, bool], layout: str = "open") -> None:
    """Keep `opened` as ``pane.<layout>`` in ui.json, the rest of the file
    as it was (the side width, the other layout, anything a later build
    adds)."""
    doc = read_doc(machine)
    pane = doc.get("pane")
    if not isinstance(pane, dict):
        pane = doc["pane"] = {}
    pane[layout] = {k: bool(opened.get(k, LAYOUTS[layout][k])) for k in KEYS}
    write_doc(machine, doc, "pane")


# ---------------------------------------------------------------- state

def opened(st: dict, layout: str = "open") -> dict[str, bool]:
    """`layout`'s open state on GRAPH's page state (`ui_graph._state`):
    the defaults while the machine is not known, then read from this Mac's
    file — once, the first frame `st["machine"]` is (a library attached
    after GRAPH first drew is read then), with any fold clicked before
    that laid over what the file says (`pane_clicks`), so it is kept and
    written by the next `flush`."""
    states = st.get("pane_open")
    if not isinstance(states, dict) or set(states) - set(LAYOUTS):
        states = st["pane_open"] = {}           # (a state from before the layouts)
    machine = st.get("machine")
    if machine is not None and st.get("pane_from") != machine:
        st["pane_from"] = machine               # the file, now it can be asked
        clicks = st.get("pane_clicks") or {}
        for other in LAYOUTS:
            states[other] = {**read_open(machine, other), **clicks.get(other, {})}
    elif layout not in states:
        states[layout] = read_open(machine, layout)
    return states[layout]


def set_open(st: dict, key: str, on: bool, layout: str = "open",
             now: float | None = None) -> None:
    """Fold or unfold section `key` in `layout`; written `WRITE_AFTER_S`
    after the last change (`flush`)."""
    got = opened(st, layout)
    if got.get(key) == on:
        return
    got[key] = on
    st.setdefault("pane_dirty", set()).add(layout)
    # the clicks not yet written, laid over the file if it is read after them
    st.setdefault("pane_clicks", {}).setdefault(layout, {})[key] = on
    st["pane_dirty_at"] = time.monotonic() if now is None else now


def section_of(page: str | None) -> str | None:
    """The section `ui.PAGE_KEYS`' name `page` focuses: the one of its name, or
    None for a row with none (GRAPH's: the canvas is always there)."""
    return page if page in KEYS else None


def focused(panel) -> str | None:
    """The section focused now: what `Panel.page`, the one owner of the
    focus, names (`ui.page`, the history and this always agree)."""
    page, keys = getattr(panel, "page", None), ui.PAGE_KEYS
    return section_of(keys[page]) if isinstance(page, int) and 0 <= page < len(keys) else None


def where(panel) -> str | None:
    """The section you are in, for ⌘Z (plan 44 D5b): the one under the mouse, as of
    the latest draw; anywhere else (the canvas, a header, the desk, the render
    window) none. Never the focus: a click in another section leaves it, and a
    key row or a pad moves it, so it would say "analyzer" an hour on."""
    from . import ui_graph  # (late: ui_graph imports this module)
    return (panel.__dict__.get(ui_graph.STATE) or {}).get("pane_under")


def left(panel) -> None:
    """A frame's draw begins: nothing is under the mouse until the draw says so, so
    a panel hidden or collapsed says nothing is (`where`, `Panel.in_meta_section`)."""
    from . import ui_graph  # (late: ui_graph imports this module)
    undo.by_hand(imgui.is_any_item_active()
                 or any(imgui.is_mouse_down(b) or imgui.is_mouse_released(b) for b in (0, 1)))
    panel._param_under = None
    st = panel.__dict__.get(ui_graph.STATE)
    if st is not None:
        st["pane_under"] = None


def scroll_to(st: dict) -> None:
    """Ask the pane's next draw, in whichever layout that is, to scroll the
    focused section into view — with none focused, to the pane's top. Not a
    click: `opened` and the file are untouched."""
    st["pane_scroll"] = True


def let_go(panel) -> None:
    """A click on a header lets go of the focus: `Panel.page` on GRAPH's
    slot, so `ui.page` and the history say so too. The pane stays where it
    is: the click was on it."""
    panel.page = panel._focus_seen = ui.PAGE_KEYS.index("graph")


def shown(panel, key: str) -> bool:
    """Did section `key`'s body draw (the latest draw; a body scrolled out of
    the pane's view does not): is it on screen, for the words of whoever
    is not the pane."""
    from . import ui_graph  # (late: ui_graph imports this module)
    st = panel.__dict__.get(ui_graph.STATE) or {}
    return key in (st.get("pane_drawn") or ())


def flush(st: dict, now: float | None = None, force: bool = False) -> bool:
    """Write the layouts folded or unfolded since the last write, once
    `WRITE_AFTER_S` has passed since the last change (`force`: now, as
    `ui_graph.close` asks). True when it wrote."""
    dirty, machine = st.get("pane_dirty"), st.get("machine")
    if not dirty or machine is None:
        return False
    now = time.monotonic() if now is None else now
    if not force and now - st.get("pane_dirty_at", now) < WRITE_AFTER_S:
        return False
    states = st.get("pane_open") or {}
    for layout in sorted(dirty):
        if layout in states:
            write_open(machine, states[layout], layout)
    dirty.clear()
    st.pop("pane_clicks", None)
    return True


def body_height(room: float, n_open: int, floor: float = MIN_BODY_H) -> float:
    """Each open body's height: the room under the headers shared evenly,
    never under `floor`."""
    return max(floor, room / n_open) if n_open else 0.0


# ---------------------------------------------------------------- drawing

def draw(panel, st: dict, dt: float, selection: Callable[[], None] | None,
         said: str = "", below: bool = False) -> None:
    """The pane's sections inside the pane's child. `selection` draws the
    selected thing's details (None: nothing is selected, and the section
    says so); `said` names it on the header. `below`: the narrow page's
    band — its own fold state, the headers one row of chips, the bodies
    sharing the rest with no floor."""
    layout = "below" if below else "open"
    got = opened(st, layout)
    held = focused(panel)                # shown however it is folded
    scroll = st.pop("pane_scroll", False)
    if scroll and (below or held is None):
        imgui.set_scroll_y(0.0)          # (the band: the focused body is under its chips)
    n_open = sum(1 for k in KEYS if got.get(k))
    # the sections whose bodies drew: last frame's for `timing_line`, which
    # the SYSTEM section asks mid-draw (the tests read this frame's)
    st["pane_last"] = st.get("pane_drawn") or []
    drawn = st["pane_drawn"] = []
    if below:
        for i, (key, title, groups, _) in enumerate(SECTIONS):
            # with one focused it is the only body, so the only chip lit: a
            # click on another asks for that one, whatever its fold says
            on = key == held if held else bool(got.get(key))
            if _header(panel, key, title, on, _said(panel, key, said), groups,
                       chip=True, first=i == 0):
                set_open(st, key, not on, layout)
                if held:                        # a chip lets go: the band as it was clicked
                    let_go(panel)
                    held = None
        room = imgui.get_content_region_avail().y
        n_open = sum(1 for k in KEYS if got.get(k))
        h = body_height(room, 1 if held else n_open, 0.0)
        for key, _, _, body in SECTIONS:
            if key == held or (held is None and got.get(key)):
                _body(panel, st, key, body, dt, selection, h, drawn)
    else:
        imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)   # a header's height: its face's line
        head_h = imgui.get_text_line_height_with_spacing()
        imgui.pop_font()
        pane_h = imgui.get_content_region_avail().y
        gap = imgui.get_style().item_spacing.y               # after each body but the last
        h = body_height(pane_h - head_h * len(SECTIONS) - gap * max(n_open - 1, 0), n_open)
        # the focused body, with its header scrolled to the top: down to the
        # headers after it, which stay in view for the next click
        held_h = (body_height(pane_h - head_h * (len(KEYS) - KEYS.index(held)) - gap, 1)
                  if held else h)
        for key, title, groups, body in SECTIONS:
            on = bool(got.get(key)) or key == held
            if _header(panel, key, title, on, _said(panel, key, said), groups):
                set_open(st, key, not on, layout)
                on = not on
                if key == held:                 # its own header lets go
                    let_go(panel)
                    held = None
            if key == held and scroll:
                imgui.set_scroll_here_y(0.0)    # the focused section's header at the top
            if on:
                _body(panel, st, key, body, dt, selection, held_h if key == held else h, drawn)
    flush(st)


def _body(panel, st: dict, key: str, body, dt: float, selection, h: float,
          drawn: list) -> None:
    """Section `key`'s body, `h` tall, under its own id: the page's draw,
    or the selection's details (or words saying there is none). Its time
    is kept for the SYSTEM section (`timing_line`). While a desk control is
    picked every body but ROUTING's is drawn disabled, and a click on a
    param is `Panel._ctx_pick`'s (ROUTING: the picked control's own line is
    what the user came for)."""
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
    """What a header names beside its title: the selection's what is selected;
    the players' who is where, so it reads folded."""
    if key == "selection":
        return said
    return ui_players.summary(panel) if key == "players" else ""


def _header(panel, key: str, title: str, on: bool, said: str, groups,
            chip: bool = False, first: bool = True) -> bool:
    """One section's header: ▾ / ▸ and its title in the micro face (the
    selection's named after it), a dot where the section's group has moved
    off its preset. `chip`: as wide as its words (the
    band's rows), lit while open, on the row of the chip before it (`first`:
    there is none) unless it would pass the edge. True when clicked."""
    dot = any(ui_presets.dirty(panel, g, polled=True) for g in groups)
    room = 2 * ui.HEADER_DOT_R + 12 if dot else 0.0
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)   # measured in the face it is drawn in
    try:
        words = f"{'▾' if on else '▸'}  {title.upper()}"
        if said:
            words += f"  ·  {said}"
        if chip:
            words = ui.fit_text(words, CHIP_MAX)
            size = imgui.ImVec2(imgui.calc_text_size(words).x + room, 0)
            if not first:               # a selectable pads its words by the frame's padding
                ui.beside(size.x + 2 * imgui.get_style().frame_padding.x)
        else:
            words = ui.fit_text(words, imgui.get_content_region_avail().x - room - 8)
            size = imgui.ImVec2(0, 0)
        hit, _ = imgui.selectable(f"{words}##pane.{key}", on and chip, 0, size)
    finally:
        imgui.pop_font()
    if imgui.is_item_hovered():
        ui.tooltip(OPEN_TIP)
    if dot:
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        imgui.get_window_draw_list().add_circle_filled(
            imgui.ImVec2(hi.x - ui.HEADER_DOT_R - 3, (lo.y + hi.y) / 2), ui.HEADER_DOT_R,
            ui.u32(ui.RED))
    return bool(hit)
