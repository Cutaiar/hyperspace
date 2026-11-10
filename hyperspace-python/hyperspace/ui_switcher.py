"""The side pane's view switcher on dkit (`ui_kit`): what replaces the bar of
chips (`ui_pane._bar`) where the kit is there.

Two rows, whatever the pane's width:

- **the six views no canvas node leads to** (`ui_pane.TABS`: selection,
  patches, audio, routing, players, system) as one TabsList of
  icons — the kit's muted ground, the view's own tab lifted on the card
  colour with its icon in the one red. Each tab's name, and what it would
  say live (`ui_pane._live`), is its tooltip; a dot in a tab's corner is
  its group moved off its patch, as on the chip;
- **the other eleven** (`ui_pane.MENU`, each also a node's **open on …**)
  as one Select, which names the view while it is one of them and says
  "sections" otherwise; a row's dot is the same dirty dot, as the menu's.

Every tab is ``##pane.<key>``, the Select ``##pane.sections`` and each of
its rows ``##pane.<key>``, so the panel driver and the tests that walk the
views (`tests/test_ui_pane.py::_click_view`) find them as they found the
chips and the menu. A click shows what it names (`ui_pane.show`).
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui, ui_fields, ui_kit, ui_pane

TAB_H = 32.0            # the TabsList: h-8, its triggers inset by its 3 px padding
TAB_PAD = 3.0
DIRTY = "●"             # a Select row's dirty mark, at its end
ICONS = {               # Lucide's names (hyperspace/dkit/icons.py)
    ui_pane.SELECTION: "mouse_pointer_2",
    "loadable": "layers",
    "audio": "audio_lines",
    "routing": "route",
    "players": "users",
    "system": "cpu",
}


def height() -> float:
    """The switcher's two rows and the step between them."""
    return TAB_H + ui_kit.mod("tokens").SPACE[2] + ui.FIELD_ROW_H


def bar(panel, key: str, said: str = "") -> None:
    """The switcher at the cursor, `key` the view up; the window's flow told
    its size after (`ui_kit.end_block`)."""
    k = ui_kit.begin(panel)
    x, y, w, _ = ui_kit.block(0.0)
    h = height()
    with ui_kit.mod("uictx").chrome(k):
        _tabs(panel, k, key, said, x, y, w)
        _sections(panel, k, key, x, y + TAB_H + ui_kit.mod("tokens").SPACE[2], w)
    ui_kit.end_block((x, y, w, h))


def _tabs(panel, k, key: str, said: str, x: float, y: float, w: float) -> None:
    """The views of `ui_pane.TABS` as the kit's Tabs — its triggers ``##pane.<key>``, its
    icons Lucide's, the active one's in the one red — then each tab's dirty
    dot and tooltip over the rects it hands back."""
    I = ui_kit.mod("interact")
    titles = {kk: t for kk, t, _, _ in ui_pane.SECTIONS}
    groups = {kk: g for kk, _, g, _ in ui_pane.SECTIONS}
    tabs = list(ui_pane.TABS)
    rects: list = []
    hit, _w = I.tabs(k, "pane.tabs", x, y, TAB_H, [titles[kk] for kk in tabs],
                     tabs.index(key) if key in tabs else -1, pad=TAB_PAD,
                     keys=[f"pane.{kk}" for kk in tabs], icons=[ICONS[kk] for kk in tabs],
                     w=w, active_ink="primary", rects=rects)
    m = imgui.get_io().mouse_pos
    over = imgui.is_window_hovered()
    for kk, (tx, ty, tw, th) in zip(tabs, rects):
        if ui_pane._dirty(panel, groups[kk]):
            k.dl.add_circle_filled(imgui.ImVec2(tx + tw - ui_pane.CHIP_DOT_R - 3,
                                                ty + ui_pane.CHIP_DOT_R + 3),
                                   ui_pane.CHIP_DOT_R, ui.u32(ui.RED))
        if over and tx <= m.x < tx + tw and ty <= m.y < ty + th:
            live = ui_pane._live(panel, kk, said)
            # what it would say live first, as the chip's tooltip does; then
            # the name the icon stands for
            ui.tooltip("\n".join(t for t in (live, titles[kk], ui_pane.VIEW_TIP) if t))
    if hit is not None and tabs[hit] != key:
        ui_pane.show(panel, tabs[hit])


def _sections(panel, k, key: str, x: float, y: float, w: float) -> None:
    I, M = ui_kit.mod("interact"), ui_kit.mod("menu")
    titles = {kk: t for kk, t, _, _ in ui_pane.SECTIONS}
    groups = {kk: g for kk, _, g, _ in ui_pane.SECTIONS}
    # the rows' dirty marks only while the menu is up: asking every group
    # each frame for a menu nobody sees was the switcher's largest cost
    # (tools/profile_kit.py; a group's dirt is a snapshot compare)
    up = imgui.is_popup_open("##sel.pane.sections")
    items = [M.Item(id=kk, label=titles[kk], checked=kk == key,
                    shortcut=DIRTY if up and ui_pane._dirty(panel, groups[kk]) else "")
             for kk in ui_pane.MENU]
    label = titles[key] if key in ui_pane.MENU else ""
    chosen, _open = I.select(k, "pane.sections", x, y, w, label, items,
                             size=ui_fields.SELECT_SIZE, placeholder=ui_pane.SECTIONS_WORD,
                             row_id=lambda it, i: f"pane.{it.id}")
    if imgui.is_item_hovered() and not _open:
        ui.tooltip(ui_pane.MENU_TIP)
    # a section in the menu moved off its patch: a dot on the Select, as on
    # the stock sections chip (any(): the first dirty group answers)
    if any(ui_pane._dirty(panel, groups[kk]) for kk in ui_pane.MENU):
        r = ui_pane.CHIP_DOT_R
        k.dl.add_circle_filled(imgui.ImVec2(x + w - r - 3, y + r + 3), r, ui.u32(ui.RED))
    if chosen is not None and chosen != key:
        ui_pane.show(panel, chosen)
