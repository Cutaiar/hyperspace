"""GRAPH's side pane, always on, as folding sections (plan 49, stage 1).

The pane PR #266 made resizable used to open only while a node, a cable,
a bundle or a group was selected. Now it is always beside the canvas
(or under it, on a narrow page) and holds a stack of sections, each a
header that folds and unfolds by a click:

- **selection** — what the pane showed before: the selected thing's
  details (`ui_graph._side`), or, with nothing selected, a line in words
  saying so;
- **presets**, **lookback**, **faces**, **analyzer** — the body of the
  page of that name, drawn by the very function the page draws
  (`Panel.presets_body`, `ui_lookback.page`, `ui_patterns.page`,
  `Panel.analyzer_body`): the page is the section at full height.

The open sections share the pane's height evenly (never under
`MIN_BODY_H`; past that the pane scrolls); each body is a child of its
own, so a long one scrolls by itself. Which sections are open is this
Mac's, kept in ``<machine>/ui.json`` under ``pane.open`` beside the
pane's width (``graph.side_w``), written when a header is clicked. A new
selection unfolds **selection** if it was folded (written like a click):
the details come up where they always did.

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

The rail and every page are untouched: stage 2 folds the rest of the
pages in, stage 3 takes the rail away (plan 49).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

from imgui_bundle import imgui

from . import ui, ui_lookback, ui_patterns, ui_presets

UI_FILE = "ui.json"      # <machine>/ui.json: this Mac's panel settings
# (key, title, the rail's groups for its dirty dot) — the order down the pane
SECTIONS = (
    ("selection", "selection", ()),
    ("presets", "presets", ("presets",)),
    ("lookback", "lookback", ("dream",)),
    ("faces", "faces", ("pattern",)),
    ("analyzer", "analyzer", ("band",)),
)
KEYS = tuple(k for k, _, _ in SECTIONS)
DEFAULT_OPEN = {"selection": True, "presets": True, "lookback": False, "faces": False,
                "analyzer": False}
MIN_BODY_H = 160.0       # an open section's body is never shorter: the pane scrolls past it
NOTHING = "nothing selected — click a node, a cable or a group on the canvas"
OPEN_TIP = "Fold or unfold this section (kept on this Mac)"


# ---------------------------------------------------------------- ui.json

def read_doc(machine) -> dict:
    """``<machine>/ui.json`` as a dict; {} for no file, an unreadable one
    or one that is not an object. Never raises."""
    try:
        doc = json.loads((Path(machine) / UI_FILE).read_text())
    except (OSError, ValueError, TypeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def write_doc(machine, doc: dict, who: str = "panel") -> None:
    """Write `doc` as ``<machine>/ui.json``; a failed write says so on
    stderr (as `who`) and costs only the memory."""
    try:
        (Path(machine) / UI_FILE).write_text(json.dumps(doc, indent=1) + "\n")
    except OSError as e:
        print(f"{who}: {UI_FILE} not written ({e})", file=sys.stderr)


def read_open(machine) -> dict[str, bool]:
    """Which sections this Mac keeps open: `DEFAULT_OPEN` overlaid with
    ``pane.open`` from ui.json, a key that is not a section or a value
    that is not a bool ignored."""
    got = dict(DEFAULT_OPEN)
    pane = read_doc(machine).get("pane") if machine is not None else None
    held = pane.get("open") if isinstance(pane, dict) else None
    if isinstance(held, dict):
        for k, v in held.items():
            if k in got and isinstance(v, bool):
                got[k] = v
    return got


def write_open(machine, opened: dict[str, bool]) -> None:
    """Keep `opened` as ``pane.open`` in ui.json, the rest of the file as
    it was (the side width, anything a later build adds)."""
    doc = read_doc(machine)
    pane = doc.get("pane")
    if not isinstance(pane, dict):
        pane = doc["pane"] = {}
    pane["open"] = {k: bool(opened.get(k, DEFAULT_OPEN[k])) for k in KEYS}
    write_doc(machine, doc, "pane")


# ---------------------------------------------------------------- state

def opened(st: dict) -> dict[str, bool]:
    """The open state on GRAPH's page state (`ui_graph._state`), read from
    this Mac's file once `st["machine"]` is known (the page sets it before
    the pane draws)."""
    got = st.get("pane_open")
    if got is None:
        got = st["pane_open"] = read_open(st.get("machine"))
    return got


def set_open(st: dict, key: str, on: bool) -> None:
    """Fold or unfold section `key`, written for this Mac."""
    got = opened(st)
    if got.get(key) == on:
        return
    got[key] = on
    if st.get("machine") is not None:
        write_open(st["machine"], got)


def note_selection(st: dict, sel_key) -> None:
    """A new selection (`sel_key` not None and not last frame's) unfolds
    the selection section."""
    if sel_key is not None and sel_key != st.get("pane_sel"):
        set_open(st, "selection", True)
    st["pane_sel"] = sel_key


def body_height(room: float, n_open: int) -> float:
    """Each open body's height: the room under the headers shared evenly,
    never under `MIN_BODY_H`."""
    return max(MIN_BODY_H, room / n_open) if n_open else 0.0


# ---------------------------------------------------------------- drawing

def draw(panel, st: dict, dt: float, selection: Callable[[], None] | None,
         said: str = "") -> None:
    """The pane's sections, top to bottom, inside the pane's child.
    `selection` draws the selected thing's details (None: nothing is
    selected, and the section says so); `said` names it on the header."""
    got = opened(st)
    head_h = imgui.get_frame_height_with_spacing()
    room = imgui.get_content_region_avail().y - head_h * len(SECTIONS)
    h = body_height(room, sum(1 for k in KEYS if got.get(k)))
    drawn = st["pane_drawn"] = []        # the sections whose bodies drew (the tests read it)
    for key, title, groups in SECTIONS:
        on = bool(got.get(key))
        if _header(panel, key, title, on, said if key == "selection" else "", groups):
            set_open(st, key, not on)
            on = not on
        if not on:
            continue
        imgui.push_id(f"pane.{key}")
        try:
            if imgui.begin_child("##body", imgui.ImVec2(0, h)):
                _body(panel, key, dt, selection)
                drawn.append(key)
            imgui.end_child()
        finally:
            imgui.pop_id()


def _header(panel, key: str, title: str, on: bool, said: str, groups) -> bool:
    """One section's header: ▾ / ▸ and its title in the micro face (the
    selection's named after it), a dot where the section's group has moved
    off its preset, as on the rail. True when clicked."""
    words = f"{'▾' if on else '▸'}  {title.upper()}"
    if said:
        words += f"  ·  {said}"
    words = ui.fit_text(words, imgui.get_content_region_avail().x - 24)
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    try:
        hit, _ = imgui.selectable(f"{words}##pane.{key}", False)
    finally:
        imgui.pop_font()
    if imgui.is_item_hovered():
        ui.tooltip(OPEN_TIP)
    if any(ui_presets.dirty(panel, g, polled=True) for g in groups):
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        imgui.get_window_draw_list().add_circle_filled(
            imgui.ImVec2(hi.x - 11, (lo.y + hi.y) / 2), ui.RAIL_DOT_R, ui.u32(ui.RED))
    return bool(hit)


def _body(panel, key: str, dt: float, selection) -> None:
    """Section `key`'s body: the page's own function (looked up as it is
    called, so a hot reload of a page module lands on the next frame)."""
    if key == "selection":
        if selection is None:
            imgui.text_wrapped(NOTHING)
        else:
            selection()
    elif key == "presets":
        panel.presets_body(dt)
    elif key == "lookback":
        ui_lookback.page(panel, dt)
    elif key == "faces":
        ui_patterns.page(panel, dt)
    elif key == "analyzer":
        panel.analyzer_body(dt)
