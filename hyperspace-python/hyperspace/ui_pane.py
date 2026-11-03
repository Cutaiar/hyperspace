"""GRAPH's side pane, always on, as folding sections (plan 49, stages 1 and 2).

The pane PR #266 made resizable used to open only while a node, a cable,
a bundle or a group was selected. Now it is always beside the canvas
(or under it, on a narrow page) and holds a stack of sections, each a
header that folds and unfolds by a click:

- **selection** — what the pane showed before: the selected thing's
  details (`ui_graph._side`), or, with nothing selected, a line in words
  saying so;
- **presets**, **fx**, **lookback**, **faces**, **media**, **lfo**,
  **seq**, **analyzer**, **audio**, **camera**, **output** — the body of
  the page of that name, drawn by the very function the page draws
  (`Panel._page_presets`, `ui_fx.page`, `ui_lookback.page`, … and the
  `Panel._page_<key>` methods of the pages that are Panel methods): the
  page is the section at full height. `SECTIONS` holds each body's
  function, so a section is one row there. Stage 2 (U2) added fx, media,
  lfo, seq, audio, camera and output, and retired the FX page: its
  browser is the fx section alone, and `ui.page` landing on FX opens
  GRAPH with that section unfolded (`focus`, `ui.RETIRED`).

The open sections share the pane's height evenly; each body is a child
of its own, so a long one scrolls by itself. Beside the canvas a body is
never under `MIN_BODY_H` (past that the pane scrolls). On a narrow page
the pane is #266's band under the canvas: there the headers are rows of
chips (a chip that would pass the edge starts the next row: twelve do not
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
section's ids never collide with its page's, nor one section's with
another's (the presets section and the lookback section both draw
preset strips). A page and its section are never drawn in one frame:
the pane is on GRAPH, and the page is one of the others. Each header is
``##pane.<key>`` for the driver.

**Narrow.** The pages were laid out for the panel's width; at the pane's
(`ui_graph.SIDE_MIN`, 240 px, at the narrowest) a chip or a tick that
would pass the right edge starts a new row (`ui.beside`), and the MEDIA
grid, the SEQ grid, the LFO and envelope strips and the OUTPUT blocks
lay themselves out for the room they are given (plan 49, stage 2).

**Cost.** Each drawn body's time is kept (``st["pane_ms"]``, a running
mean) and the SYSTEM page says it under GRAPH's own line
(`timing_line`); a body scrolled out of the pane's view is not drawn
(imgui skips the child), so it costs nothing.

The rail and every other page stay: stage 3 takes the rail away (plan 49).
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path

from imgui_bundle import imgui

from . import (
    library,
    ui,
    ui_fx,
    ui_lfo,
    ui_lookback,
    ui_media,
    ui_patterns,
    ui_presets,
    ui_seq,
)

UI_FILE = "ui.json"      # <machine>/ui.json: this Mac's panel settings


# each body looked up as it is called, so a hot reload of its page lands
def _presets(panel, dt: float) -> None:
    panel._page_presets(dt)


def _lookback(panel, dt: float) -> None:
    ui_lookback.page(panel, dt)


def _faces(panel, dt: float) -> None:
    ui_patterns.page(panel, dt)


def _analyzer(panel, dt: float) -> None:
    panel._page_analyzer(dt)


# plan 49 stage 2 (U2): the rest of the pages
def _fx(panel, dt: float) -> None:
    ui_fx.page(panel, dt)          # the FX page's browser; the page itself is retired


def _media(panel, dt: float) -> None:
    ui_media.draw(panel, dt)


def _lfo(panel, dt: float) -> None:
    ui_lfo.page(panel, dt)


def _seq(panel, dt: float) -> None:
    ui_seq.page(panel, dt)


def _audio(panel, dt: float) -> None:
    panel._page_audio(dt)


def _camera(panel, dt: float) -> None:
    panel._page_camera(dt)


def _output(panel, dt: float) -> None:
    panel._page_output(dt)


# (key, title, the rail's groups for its dirty dot, the body — the page's
# own draw; None for selection, whose body `draw` is handed): down the pane,
# the graph's own things first (what is selected, the preset, its effects
# and pictures), then the voices that move them, then the room and the rig
SECTIONS: tuple[tuple[str, str, tuple[str, ...], Callable | None], ...] = (
    ("selection", "selection", (), None),
    ("presets", "presets", ("presets",), _presets),
    ("fx", "fx", ("fx",), _fx),
    ("lookback", "lookback", ("dream",), _lookback),
    ("faces", "faces", ("pattern",), _faces),
    ("media", "media", ("media", "backdrop"), _media),
    ("lfo", "lfo", ("lfo", "tempo"), _lfo),
    ("seq", "seq", ("seq", "env"), _seq),
    ("analyzer", "analyzer", ("band",), _analyzer),
    ("audio", "audio", ("master",), _audio),
    ("camera", "camera", ("camera",), _camera),
    ("output", "output", ("output",), _output),
)
KEYS = tuple(k for k, *_ in SECTIONS)
# beside the canvas: selection and presets open at first (stage 1); every
# section stage 2 added folded (rec: a fresh Mac's pane reads as it did)
DEFAULT_OPEN = {k: k in ("selection", "presets") for k in KEYS}
DEFAULT_BELOW = {k: k == "selection" for k in KEYS}     # the narrow page's band
LAYOUTS = {"open": DEFAULT_OPEN, "below": DEFAULT_BELOW}   # ui.json's pane.<layout>
MIN_BODY_H = 160.0       # beside the canvas, an open body is never shorter (the pane scrolls)
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


def focus(st: dict, key: str) -> None:
    """Ask the pane's next draw to unfold section `key` and scroll it into
    view, in whichever layout that draw is (beside the canvas, or the
    narrow page's band: review fix 1): what `ui.page` landing on a retired
    page does (`ui.RETIRED`: FX → the fx section), and what stage 3's
    "focus section" will do for every page. The unfold is a click's, so
    it is kept on this Mac."""
    st["pane_focus"] = key


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
    want = st.pop("pane_focus", None)    # `focus`: unfolded here, in this draw's layout
    if want in KEYS:                     # (a state or file from before a section existed)
        set_open(st, want, True, layout)
    n_open = sum(1 for k in KEYS if got.get(k))
    drawn = st["pane_drawn"] = []        # the sections whose bodies drew (the tests read it)
    if below:
        for i, (key, title, groups, _) in enumerate(SECTIONS):
            on = bool(got.get(key))
            if _header(panel, key, title, on, said if key == "selection" else "", groups,
                       chip=True, first=i == 0):
                set_open(st, key, not on, layout)
        h = body_height(imgui.get_content_region_avail().y, n_open, 0.0)
        for key, _, _, body in SECTIONS:
            if got.get(key):
                if key == want:
                    imgui.set_scroll_here_y(0.0)    # the focused body at the band's top
                _body(panel, st, key, body, dt, selection, h, drawn)
    else:
        head_h = imgui.get_frame_height_with_spacing()
        h = body_height(imgui.get_content_region_avail().y - head_h * len(SECTIONS), n_open)
        for key, title, groups, body in SECTIONS:
            on = bool(got.get(key))
            if _header(panel, key, title, on, said if key == "selection" else "", groups):
                set_open(st, key, not on, layout)
                on = not on
            if key == want:
                imgui.set_scroll_here_y(0.0)        # the focused section's header at the top
            if on:
                _body(panel, st, key, body, dt, selection, h, drawn)
    flush(st)


def _body(panel, st: dict, key: str, body, dt: float, selection, h: float,
          drawn: list) -> None:
    """Section `key`'s body, `h` tall, under its own id: the page's draw,
    or the selection's details (or words saying there is none). Its time
    is kept for the SYSTEM page (`timing_line`)."""
    imgui.push_id(f"pane.{key}")
    try:
        if imgui.begin_child("##body", imgui.ImVec2(0, h)):
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
        imgui.pop_id()


def timing_line(panel) -> str:
    """The SYSTEM page's line for the pane (plan 49 stage 2): each section
    whose body drew last time GRAPH drew, its running mean in ms, the
    dearest first — "" until one has (or GRAPH never drew). GRAPH's own
    line above this one times the whole page, these included."""
    from . import ui_graph  # (late: ui_graph imports this module)
    st = panel.__dict__.get(ui_graph.STATE) or {}
    cost, shown = st.get("pane_ms") or {}, st.get("pane_drawn") or []
    got = sorted(((cost[k], k) for k in shown if k in cost), reverse=True)
    if not got:
        return ""
    return "side pane: " + "  ·  ".join(f"{k} {ms:.2f}" for ms, k in got) + " ms"


def _header(panel, key: str, title: str, on: bool, said: str, groups,
            chip: bool = False, first: bool = True) -> bool:
    """One section's header: ▾ / ▸ and its title in the micro face (the
    selection's named after it), a dot where the section's group has moved
    off its preset, as on the rail. `chip`: as wide as its words (the
    band's rows), lit while open, on the row of the chip before it (`first`:
    there is none) unless it would pass the edge. True when clicked."""
    dot = any(ui_presets.dirty(panel, g, polled=True) for g in groups)
    room = 2 * ui.RAIL_DOT_R + 12 if dot else 0.0
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
            imgui.ImVec2(hi.x - ui.RAIL_DOT_R - 3, (lo.y + hi.y) / 2), ui.RAIL_DOT_R,
            ui.u32(ui.RED))
    return bool(hit)
