"""The side pane's view switcher on dkit (`ui_kit`): what replaces the bar of
uppercase chips (`ui_pane._bar`) where the kit is there.

Two rows, whatever the pane's width:

- **the seven views no canvas node leads to** (`ui_pane.TABS`: selection,
  patches, audio, routing, playlist, players, system) as one TabsList of
  icons — the kit's muted ground, the view's own tab lifted on the card
  colour with its icon in the one red. Each tab's name, and what it would
  say live (`ui_pane._live`), is its tooltip; a dot in a tab's corner is
  its group moved off its patch, as on the chip;
- **the other eleven** (`ui_pane.MENU`, each also a node's **open on …**)
  as one Select, which names the view while it is one of them and says
  "Sections" otherwise; a row's dot is the same dirty dot, as the menu's.

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
ICON = 16.0             # a tab's glyph (size-4)
DIRTY = "●"             # a Select row's dirty mark, at its end
ICONS = {               # Lucide's names (tools/dkit/icons.py)
    ui_pane.SELECTION: "mouse_pointer_2",
    "loadable": "layers",
    "audio": "audio_lines",
    "routing": "route",
    "playlist": "list_music",
    "players": "users",
    "system": "cpu",
}


def height() -> float:
    """The switcher's two rows and the step between them."""
    return TAB_H + ui_kit.mod("tokens").SPACE[2] + ui_fields.ROW_H


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
    D, T, ease = ui_kit.mod("draw"), ui_kit.mod("tokens"), ui_kit.mod("ease")
    titles = {kk: t for kk, t, _, _ in ui_pane.SECTIONS}
    groups = {kk: g for kk, _, g, _ in ui_pane.SECTIONS}
    D.fill(k.dl, x, y, w, TAB_H, k.col("muted"), T.RADII["lg"])
    n = len(ui_pane.TABS)
    tw = (w - 2 * TAB_PAD) / n
    ih = TAB_H - 2 * TAB_PAD
    for i, kk in enumerate(ui_pane.TABS):
        tx, ty = x + TAB_PAD + i * tw, y + TAB_PAD
        st = k.hit(f"pane.{kk}", tx, ty, tw, ih)
        on = kk == key
        sel = k.anim.to(f"pane.{kk}:sel", 1.0 if on else 0.0)
        if sel > 0.01:
            D.shadow(k.dl, tx, ty, tw, ih, (0, 0, 0, 0.25 * sel), T.RADII["md"], dy=1.0, blur=3.0)
            D.fill(k.dl, tx, ty, tw, ih, ease.mix(k.col("transparent"), k.col("card"), sel),
                   T.RADII["md"])
        ff = k.focus_f(f"pane.{kk}", st.focused)
        if ff > 0.01:
            D.ring(k.dl, tx, ty, tw, ih, k.col("ring", 0.5 * ff), T.RADII["md"], T.RING_W)
        ink = ease.mix(ease.mix(k.col("muted-foreground"), k.col("foreground"), st.hot * 0.7),
                       k.col("primary"), sel)
        D.icon(k.dl, ICONS[kk], tx + (tw - ICON) / 2, ty + (ih - ICON) / 2, ICON, ink)
        if ui_pane._dirty(panel, groups[kk]):
            k.dl.add_circle_filled(imgui.ImVec2(tx + tw - ui_pane.CHIP_DOT_R - 3, ty + ui_pane.CHIP_DOT_R + 3),
                                   ui_pane.CHIP_DOT_R, ui.u32(ui.RED))
        if st.hovered:
            live = ui_pane._live(panel, kk, said)
            # what it would say live first, as the chip's tooltip does; then
            # the name the icon stands for
            ui.tooltip("\n".join(t for t in (live, titles[kk].upper(), ui_pane.VIEW_TIP) if t))
        if st.clicked and not on:
            ui_pane.show(panel, kk)


def _sections(panel, k, key: str, x: float, y: float, w: float) -> None:
    I, M = ui_kit.mod("interact"), ui_kit.mod("menu")
    titles = {kk: t for kk, t, _, _ in ui_pane.SECTIONS}
    groups = {kk: g for kk, _, g, _ in ui_pane.SECTIONS}
    items = [M.Item(id=kk, label=titles[kk].upper(), checked=kk == key,
                    shortcut=DIRTY if ui_pane._dirty(panel, groups[kk]) else "")
             for kk in ui_pane.MENU]
    label = titles[key].upper() if key in ui_pane.MENU else ""
    chosen, _open = I.select(k, "pane.sections", x, y, w, label, items,
                             size=ui_fields.SELECT_SIZE, placeholder="Sections",
                             row_id=lambda it, i: f"pane.{it.id}")
    if imgui.is_item_hovered() and not _open:
        ui.tooltip(ui_pane.MENU_TIP)
    if chosen is not None and chosen != key:
        ui_pane.show(panel, chosen)
