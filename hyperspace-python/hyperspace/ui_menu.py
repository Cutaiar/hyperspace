"""A right-click menu described once and drawn two ways.

GRAPH's menus were built the way imgui wants them: `menu_item_simple` and
`begin_menu` called in place, each item's action run from inside the `if`
that drew it. dkit's menu is the other shape — it is handed the rows, it
measures them, and it hands back the id that was chosen — and the two
cannot be mixed in one panel, because a dkit panel places its rows by
screen position and an imgui menu item would land wherever the cursor
happened to be.

So a menu is DESCRIBED here and drawn by one of two renderers:

- `draw_imgui` — imgui's own menu items, which is what the panel's param
  menus still use and what the whole of GRAPH used before this;
- `draw_kit` — dkit's `menu.popup`, the measured shadcn panel, with
  submenus (`dkit/menu.py`, SUBMENUS).

A `Menu` is built with the same shape the imgui code had, so the move is
mechanical and reads as the menu it draws:

    m = Menu("graph.cable")
    m.heading(cable_tip(view, c).splitlines()[0])
    with m.sub("insert"):
        for kind in modifiers.KINDS:
            m.item(kind, partial(insert_modifier, panel, c, kind))
    m.item("delete", lambda: disconnect(panel, c), variant="destructive")

**An action runs after the draw, not during it.** A renderer returns the
chosen id and `Menu.pick` runs that row's `on_pick`; the dkit panel cannot
know what was chosen until its rows have been submitted, and the imgui
renderer follows the same order so the two cannot diverge on a menu whose
action edits the very view the menu was built from.

**Ids are the test seam.** A row's id is what follows ``##`` in the imgui
path and the dkit row's hit-target key in the kit path, so
`tests/ui_driver.py` and the graph tests find a row by the same name
either way. Where the imgui code already named one (``spawn.<slug>``,
``route_from.lfo.0``) the builder is given that name; otherwise it is the
label, under its submenu's id, with a counter where a label repeats.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from imgui_bundle import imgui

from . import ui, ui_kit

# A heading is drawn in the micro face (the panel's own small label); a note
# is a dimmed line of words. dkit has one row for both — shadcn's menu Label
# — and the difference only shows in the imgui path, where the two are
# `ui._micro` and `imgui.text_disabled` as the menus always drew them.
HEADING, NOTE, SEP, ITEM, SUB = "heading", "note", "sep", "item", "sub"

_ID_CUT = re.compile(r"[^0-9a-zA-Z._:-]+")


def _slug(text: str) -> str:
    """A label as an id: its words, nothing imgui's ``##`` could eat."""
    return _ID_CUT.sub("-", text.strip()).strip("-").lower() or "row"


@dataclass
class Row:
    """One row of a menu, drawn by either renderer."""

    kind: str = ITEM
    id: str = ""
    label: str = ""
    enabled: bool = True
    checked: bool | None = None
    shortcut: str = ""
    variant: str = "default"        # default | destructive
    tip: str = ""
    icon: str = ""
    rows: list = field(default_factory=list)        # a sub's rows
    on_pick: Callable[[], object] | None = None
    # Did the CALLER name this row's id? The imgui renderer then writes
    # `label##id`, as the menus it replaced did at exactly those rows
    # (``spawn.<slug>``, ``route_from.lfo.0``, a param's own id) — and
    # writes the bare label everywhere else, so the panel's param menu
    # submits the labels it always did. The kit's panel keys every row by
    # its id either way.
    named: bool = False


class Menu:
    """A menu's rows, and the action behind each.

    `key` names the menu for ids and for the popup: the kit's panel is
    keyed by it and every row's id is unique inside it.
    """

    def __init__(self, key: str) -> None:
        self.key = key
        self.rows: list[Row] = []
        self._open: list[Row] = []           # the sub being filled
        self._acts: dict[str, Callable[[], object]] = {}
        self._seen: set[str] = set()

    # ---------------------------------------------------------------- build

    def _at(self) -> list[Row]:
        return self._open[-1].rows if self._open else self.rows

    def _id(self, label: str, rid: str | None) -> str:
        """A row's id: the one the caller gave, else the label under the
        submenu it sits in — with a counter where a label repeats, so two
        rows can never answer to one name.

        An id the caller GAVE is absolute: it is not put under the sub it
        sits in. Those are the ids the imgui menus already wrote after
        ``##`` — ``spawn.<slug>``, ``route_from.lfo.0``, a param's own id,
        a pin's — and the tests and the panel driver find rows by them, so
        a submenu must not rename them.
        """
        if rid is not None:
            base = rid
        else:
            base = _slug(label)
            if self._open:
                base = f"{self._open[-1].id}.{base}"
        out, n = base, 2
        while out in self._seen:
            out, n = f"{base}~{n}", n + 1
        self._seen.add(out)
        return out

    def heading(self, text: str) -> None:
        """A label over the rows under it (the subject, usually)."""
        if text:
            self._at().append(Row(HEADING, label=text))

    def note(self, text: str) -> None:
        """A dimmed line of words: what a thing is, or why it cannot be."""
        if text:
            self._at().append(Row(NOTE, label=text))

    def sep(self) -> None:
        """A rule, dropped where it would be the first or a second row."""
        at = self._at()
        if at and at[-1].kind != SEP:
            at.append(Row(SEP))

    def item(self, label: str, on_pick: Callable[[], object] | None = None, *,
             id: str | None = None, enabled: bool = True,
             checked: bool | None = None, shortcut: str = "",
             variant: str = "default", tip: str = "", icon: str = "") -> str:
        """One pickable row. Returns its id."""
        rid = self._id(label, id)
        self._at().append(Row(ITEM, rid, label, enabled, checked, shortcut,
                              variant, tip, icon, named=id is not None))
        if on_pick is not None:
            self._acts[rid] = on_pick
        return rid

    @contextmanager
    def sub(self, label: str, *, id: str | None = None,
            enabled: bool = True, tip: str = "") -> Iterator[Row]:
        """A submenu. Its rows are what is added inside the `with`.

        A sub that ends up empty is dropped: the menus this replaced wrote
        that as `if not rows or not imgui.begin_menu(...)`, and a submenu
        that opens onto nothing is worse in a panel that measures its rows
        than in one that does not.
        """
        row = Row(SUB, self._id(label, id), label, enabled, tip=tip,
                  named=id is not None)
        self._at().append(row)
        self._open.append(row)
        try:
            yield row
        finally:
            self._open.pop()
            if not row.rows:
                self._at().remove(row)

    # ---------------------------------------------------------------- read

    def empty(self) -> bool:
        """Is there nothing to pick: no item and no sub, headings aside."""
        return not any(r.kind in (ITEM, SUB) for r in self.rows)

    def pick(self, rid: str | None) -> bool:
        """Run the action behind `rid`. True if there was one."""
        fn = self._acts.get(rid or "")
        if fn is None:
            return False
        fn()
        return True

    def walk(self) -> Iterator[Row]:
        """Every row, subs included, depth first — for the tests."""
        def go(rows):
            for r in rows:
                yield r
                yield from go(r.rows)
        yield from go(self.rows)

    def labels(self) -> list[str]:
        """Every pickable row's label, subs included: what a test reads."""
        return [r.label for r in self.walk() if r.kind in (ITEM, SUB)]

    def row(self, *labels: str) -> Row | None:
        """The row at a path of LABELS: `m.row("insert", "effects", "acid")`.

        For the tests, which read a menu the way a person does — by the
        words on the rows — rather than by the ids the builder derives from
        them. Returns None where the path is not there, which is itself
        what a test often wants to assert.
        """
        rows, hit = self.rows, None
        for label in labels:
            hit = next((r for r in rows if r.label == label), None)
            if hit is None:
                return None
            rows = hit.rows
        return hit

    def id_of(self, *labels: str) -> str | None:
        """The id of the row at a path of labels (`row`)."""
        r = self.row(*labels)
        return None if r is None else r.id

    def choose(self, *labels: str) -> bool:
        """Pick the row at a path of labels: what a click on it does."""
        return self.pick(self.id_of(*labels))

    def starting(self, prefix: str) -> Row | None:
        """The first pickable row ANYWHERE whose label starts with
        `prefix` — for a test that knows the words and not the path."""
        return next((r for r in self.walk()
                     if r.kind == ITEM and r.label.startswith(prefix)), None)


# -------------------------------------------------------------------- imgui

def draw_imgui(m: Menu) -> str | None:
    """Draw `m` with imgui's own menu items, inside an open popup.

    The renderer the panel's param menus use, and GRAPH's fallback with
    ``HYPERSPACE_KIT=0``. Returns the chosen id, having run its action.
    """
    rid = _rows_imgui(m.rows)
    m.pick(rid)
    return rid


def _rows_imgui(rows: list[Row]) -> str | None:
    out = None
    for r in rows:
        if r.kind is SEP or r.kind == SEP:
            imgui.separator()
        elif r.kind == HEADING:
            ui._micro(r.label)
        elif r.kind == NOTE:
            imgui.text_disabled(r.label)
        elif r.kind == SUB:
            if imgui.begin_menu(_label_imgui(r), r.enabled):
                out = _rows_imgui(r.rows) or out
                imgui.end_menu()
            _tip_imgui(r)
        elif r.checked is None and not r.shortcut:
            # `menu_item_simple`, which is what these rows were drawn with
            # before they were described: a plain row has no tick and no
            # shortcut, and the tests that read the panel's param menu
            # watch this call by name.
            if imgui.menu_item_simple(_label_imgui(r), enabled=r.enabled):
                out = r.id
            _tip_imgui(r)
        else:
            hit, _ = imgui.menu_item(_label_imgui(r), r.shortcut,
                                     bool(r.checked), r.enabled)
            if hit:
                out = r.id
            _tip_imgui(r)
    return out


def _label_imgui(r: Row) -> str:
    """A row's imgui label: ``label##id`` where the caller named the id,
    the bare label otherwise (`Row.named`)."""
    return f"{r.label}##{r.id}" if r.named else r.label


def _tip_imgui(r: Row) -> None:
    # `allow_when_disabled`: a refused row's tooltip is the whole reason it
    # is drawn rather than left out
    if r.tip and imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        ui.tooltip(r.tip)


# ---------------------------------------------------------------------- dkit

def kit_items(rows: list[Row]):
    """`rows` as dkit menu items (`dkit.menu.Item`), subs and all."""
    M = ui_kit.mod("menu")
    out = []
    for r in rows:
        if r.kind == SEP:
            out.append(M.sep())
        elif r.kind in (HEADING, NOTE):
            out.append(M.heading(r.label))
        elif r.kind == SUB:
            out.append(M.Item(id=r.id, label=r.label, enabled=r.enabled,
                              items=tuple(kit_items(r.rows))))
        else:
            out.append(M.Item(id=r.id, label=r.label, icon=r.icon,
                              shortcut=r.shortcut, variant=r.variant,
                              checked=r.checked, enabled=r.enabled))
    return out


def draw_kit(panel, m: Menu, at: tuple[float, float] | None = None) -> str | None:
    """Draw `m` as dkit's ContextMenu panel at `at` (screen px).

    The popup is ImGui's — `imgui.open_popup(m.key)` is the caller's, on the
    gesture — and everything inside it is the kit's: the measured panel, the
    rows, the submenus and the keyboard (`dkit/menu.py`). Returns the chosen
    id, having run its action.

    Placement is `comp_context_menu.place_at_pointer`, the measured law for
    a panel opened at a pointer rather than against a trigger, so a menu on
    the canvas lands where the one on the side pane would.
    """
    CX, M = ui_kit.mod("comp_context_menu"), ui_kit.mod("menu")
    B = ui_kit.mod("box")
    kit = ui_kit.begin(panel)
    items = kit_items(m.rows)
    if imgui.is_popup_open(m.key):
        cw, ch = M.measure(kit, items, CX.MIN_W)
        w, h = cw + 2.0 * M.PAD, ch + 2.0 * M.PAD
        px, py = at if at is not None else (0.0, 0.0)
        panel_rect = CX.place_at_pointer(px, py, w, h, kit.viewport)
        imgui.set_next_window_pos(imgui.ImVec2(panel_rect.x, panel_rect.y))
    rid = M.popup(kit, m.key, items, min_w=CX.MIN_W,
                  row_id=lambda it, i: it.id or f"{m.key}.{i}")
    _tips_kit(kit, m, items, B, M)
    m.pick(rid)
    return rid


def _tips_kit(kit, m: Menu, items, B, M) -> None:
    """The tooltip of whichever row the pointer is on, in any open panel.

    dkit's rows carry no tooltip of their own, and a row's rect is only
    known once the stride has walked to it — so the stride is walked here,
    off `menu.LAST_RECT`, which is where every panel says it was drawn. The
    tooltip itself is the panel's own (`ui.tooltip`): an imgui tooltip
    window sits above the popup stack, where a tooltip drawn into the
    panel's draw list would be clipped to the panel.

    A row with no tip of its own gets one when its LABEL did not fit: the
    panel is capped at `menu.MAX_W` and a long row is ellipsised there, so
    the words that were cut have to be reachable. The graph's refusals are
    what need it — "faces pattern: Faces pattern is in the graph already:
    drag it onto the cable" is a whole sentence on one row.
    """
    tips = {r.id: r.tip for r in m.walk() if r.tip}
    mouse = imgui.get_mouse_pos()
    for key, rect in list(M.LAST_RECT.items()):
        if not key.startswith(m.key):
            continue
        rows = _rows_at(items, key, m.key)
        if rows is None:
            continue
        x, y, w, _h = rect
        inset = M.PAD + (0.0 if key == m.key else M.SUB_BORDER)
        iy = y + inset
        for it in rows:
            rh = M.row_h(it)
            if x <= mouse.x < x + w and iy <= mouse.y < iy + rh:
                tip = tips.get(getattr(it, "id", "")) or _cut_label(kit, it, w - 2 * inset, M)
                if tip:
                    ui.tooltip(tip)
                return
            iy += rh


def _cut_label(kit, it, cw: float, M) -> str:
    """The row's whole label, where the panel's cap cut it; "" otherwise."""
    label = getattr(it, "label", "")
    if not label or getattr(it, "kind", "item") == "sep":
        return ""
    D = ui_kit.mod("draw")
    size = 12 if getattr(it, "kind", "item") == "label" else 14
    variant = "medium" if getattr(it, "kind", "item") == "label" else "regular"
    room = M.label_room(it, cw, kit) if size == 14 else cw - 2 * M.ITEM_PAD_X
    return label if D.text_w(label, kit.faces, variant, size) > room + 0.5 else ""


def _rows_at(items, key: str, root: str):
    """The items of the panel keyed `key`: the root's, or a sub's, found by
    walking the ``parent>id`` key `dkit.menu` builds for a submenu."""
    if key == root:
        return items
    rest = key[len(root):].lstrip(">")
    rows = items
    for step in rest.split(">"):
        hit = next((it for it in rows
                    if getattr(it, "id", "") == step and getattr(it, "items", ())), None)
        if hit is None:
            return None
        rows = list(hit.items)
    return rows
