"""Dropdown menus and popovers, on ImGui's popup stack.

The hard parts of a popup are not the chrome — they are focus, dismissal on
click-away or Escape, nesting, and keeping the thing above everything else.
ImGui already does all of that, so this borrows its popup window and paints
shadcn's chrome into it rather than reimplementing any of it.

Measured off `prototypes/dashboard/src/components/ui/dropdown-menu.tsx`:

    content   rounded-lg (10) · p-1 (4) · bg-popover · shadow-md
              · ring-1 ring-foreground/10 · min-w-32 (128)
    item      rounded-md (8) · px-1.5 (6) · py-1 (4) · text-sm (14)
              · gap-1.5 (6) · focus:bg-accent
    destructive  text-destructive · focus:bg-destructive/10

**One caveat worth knowing before this goes near the GRAPH canvas.**
`replay.keep` (`hyperspace/replay.py:91`) carries only the page window's own
draw list into the canvas tap, and explicitly drops "every popup, menu and
tooltip (their own windows)". So a menu opened over that canvas will not
appear in the `panel:graph` texture that feeds the render graph. It is fine
on the panel; it cannot be part of anything projected.
"""

from __future__ import annotations

from dataclasses import dataclass

from imgui_bundle import imgui

import draw as D
import tokens as T
from ease import mix

PAD = 4.0            # p-1
ITEM_H = 26.0        # py-1 either side of a 14px line
ITEM_PAD_X = 6.0     # px-1.5
GAP = 6.0            # gap-1.5
MIN_W = 128.0        # min-w-32
SEP_MY = 4.0         # my-1
ICON = 14.0


@dataclass
class Item:
    """One row. `kind` is item | sep | label."""
    id: str = ""
    label: str = ""
    icon: str = ""
    shortcut: str = ""
    kind: str = "item"
    variant: str = "default"      # default | destructive
    checked: bool | None = None
    enabled: bool = True


def sep() -> Item:
    return Item(kind="sep")


def heading(text: str) -> Item:
    return Item(kind="label", label=text)


def measure(ui, items, min_w: float = MIN_W) -> tuple[float, float]:
    """The content box a menu needs, before chrome padding."""
    w = min_w - 2 * PAD
    h = 0.0
    for it in items:
        if it.kind == "sep":
            h += 1 + 2 * SEP_MY
            continue
        tw = D.text_w(it.label, ui.faces, "medium" if it.kind == "label"
                      else "regular", 14)
        extra = 2 * ITEM_PAD_X
        if it.icon or it.checked is not None:
            extra += ICON + GAP
        if it.shortcut:
            extra += GAP * 2 + D.text_w(it.shortcut, ui.faces, "regular", 12,
                                        True)
        w = max(w, tw + extra)
        h += ITEM_H
    return w, h


def _row(ui, it, x, y, w, key, alpha):
    """One menu row. Returns True if it was chosen this frame."""
    if it.kind == "sep":
        D.fill(ui.dl, x - PAD + 1, y + SEP_MY, w + 2 * PAD - 2, 1,
               ui.col("border", alpha))
        return False
    if it.kind == "label":
        D.label(ui.dl, x + ITEM_PAD_X, y, it.label, ui.faces, "medium", 12,
                ui.col("muted-foreground", alpha), baseline_box=ITEM_H)
        return False

    st = ui.hit(key, x, y, w, ITEM_H) if it.enabled else None
    hot = st.hot if st else 0.0
    if hot > 0.01:
        bg = ("destructive", 0.10) if it.variant == "destructive" \
            else ("accent", 1.0)
        D.fill(ui.dl, x, y, w, ITEM_H,
               mix(ui.col("transparent"), ui.col(*bg), hot * alpha),
               T.RADII["md"])
    if it.variant == "destructive":
        ink = ui.col("destructive", alpha)
    elif not it.enabled:
        ink = ui.col("muted-foreground", 0.5 * alpha)
    else:
        ink = ui.col("popover-foreground", alpha)

    tx = x + ITEM_PAD_X
    if it.checked is not None:
        if it.checked:
            D.icon(ui.dl, "check", tx, y + (ITEM_H - ICON) / 2, ICON, ink)
        tx += ICON + GAP
    elif it.icon:
        D.icon(ui.dl, it.icon, tx, y + (ITEM_H - ICON) / 2, ICON, ink)
        tx += ICON + GAP
    D.label(ui.dl, tx, y, it.label, ui.faces, "regular", 14, ink,
            baseline_box=ITEM_H)
    if it.shortcut:
        D.label(ui.dl, x, y, it.shortcut, ui.faces, "regular", 12,
                ui.col("muted-foreground", alpha), align="right",
                box_w=w - ITEM_PAD_X, baseline_box=ITEM_H, tabular=True)
    return bool(st and st.clicked)


def popup(ui, key: str, items, *, min_w: float = MIN_W) -> str | None:
    """Draw the menu `key` if ImGui has it open. Returns the chosen item id.

    Open it with `imgui.open_popup(key)` from the trigger — usually
    `interact.icon_button(..., "ellipsis-vertical")`.
    """
    cw, ch = measure(ui, items, min_w)
    w, h = cw + 2 * PAD, ch + 2 * PAD

    imgui.set_next_window_size(imgui.ImVec2(w, h))
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
    imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
    imgui.push_style_var(imgui.StyleVar_.popup_rounding, T.RADII["lg"])
    imgui.push_style_color(imgui.Col_.popup_bg, imgui.ImVec4(0, 0, 0, 0))
    chosen = None
    if imgui.begin_popup(key):
        # shadcn fades the menu in over 100ms (`duration-100`). The window
        # itself is placed by ImGui, so only the chrome is animated.
        a = ui.anim.to(f"{key}:open", 1.0)
        dl = imgui.get_window_draw_list()
        p = imgui.get_window_pos()
        x, y = p.x, p.y
        saved, ui.dl = ui.dl, dl
        # the shadow and the ring fall OUTSIDE the window rect, which imgui
        # clips to; widen the clip while the chrome is drawn
        dl.push_clip_rect(imgui.ImVec2(x - 16, y - 16),
                          imgui.ImVec2(x + w + 16, y + h + 16), False)
        D.shadow(dl, x, y, w, h, (0, 0, 0, 0.10 * a), T.RADII["lg"],
                 dy=4.0, blur=6.0, spread=-1.0)
        D.shadow(dl, x, y, w, h, (0, 0, 0, 0.10 * a), T.RADII["lg"],
                 dy=2.0, blur=4.0, spread=-2.0)
        D.fill(dl, x, y, w, h, ui.col("popover", a), T.RADII["lg"])
        D.border(dl, x - 1, y - 1, w + 2, h + 2,
                 ui.col("foreground", 0.10 * a), T.RADII["lg"] + 1, 1.0)

        dl.pop_clip_rect()

        iy = y + PAD
        for i, it in enumerate(items):
            if _row(ui, it, x + PAD, iy, cw, f"{key}.{i}", a):
                chosen = it.id
                imgui.close_current_popup()
            iy += (1 + 2 * SEP_MY) if it.kind == "sep" else ITEM_H
        ui.dl = saved
        imgui.end_popup()
    else:
        ui.anim.to(f"{key}:open", 0.0)
    imgui.pop_style_color()
    imgui.pop_style_var(3)
    return chosen
