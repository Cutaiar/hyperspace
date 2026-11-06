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

import box as B
import draw as D
import tokens as T
from ease import mix

# Where each menu was last drawn, keyed by popup id: {key: (x, y, w, h)}.
# ImGui places the popup, so a test cannot know the rect ahead of time, and
# finding it from pixels is unreliable — a hovered table row composites to
# within a level of the popover fill. This is the seam instead.
LAST_RECT: dict = {}

PAD = 4.0            # p-1
# Measured in Chromium, not derived from the classes. `text-sm` carries a
# 20px LINE-HEIGHT, not a 14px one, so py-1 either side is 20 + 4 + 4. The
# 26 that stood here was the font size plus the padding, and it was wrong by
# two pixels on every row of every menu the kit has ever drawn.
ITEM_H = 28.0        # py-1 either side of a 20px line box
# A label is `text-xs` (16/16) + py-1, which is NOT an item height.
LABEL_H = 24.0
ITEM_PAD_X = 6.0     # px-1.5
GAP = 6.0            # gap-1.5
MIN_W = 128.0        # min-w-32
SEP_MY = 4.0         # my-1
DESTRUCTIVE_HOVER_A = {"light": 0.10, "dark": 0.20}
# `tracking-widest` is real and Chromium trails it: a 12px shortcut measures
# 2 x 1.2px wider than its glyphs. draw.text_w has no letter-spacing.
SHORTCUT_TRACKING = 1.2
ICON = 16.0          # size-4, measured; 14 was a guess


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


def panel_chrome(ui, dl, x, y, w, h, a: float = 1.0) -> None:
    """A menu panel's shadow, fill and ring - the chrome with no lifecycle.

    Pulled out of `popup` so three callers can share one answer: `popup`
    itself, the gallery cell that diffs this against the browser, and a
    Combobox, whose panel is measured byte-identical but whose body is a
    filtered list rather than a row loop.

    shadow-md's two layers, `bg-popover`, and a 1px `ring-foreground/10`
    which is a box-shadow and so sits wholly OUTSIDE the box.
    """
    # the shadow and the ring fall outside the window rect, which imgui
    # clips to; widen the clip while the chrome is drawn
    dl.push_clip_rect(imgui.ImVec2(x - 16, y - 16),
                      imgui.ImVec2(x + w + 16, y + h + 16), False)
    for _dx, dy, blur, spread, al in T.SHADOW_MD:
        D.shadow(dl, x, y, w, h, (0, 0, 0, al * a), T.RADII["lg"],
                 dy=dy, blur=blur, spread=spread)
    D.fill(dl, x, y, w, h, ui.col("popover", a), T.RADII["lg"])
    D.border(dl, x - 1, y - 1, w + 2, h + 2,
             ui.col("foreground", 0.10 * a), T.RADII["lg"] + 1, 1.0)
    dl.pop_clip_rect()


def rows(ui, items, x, y, w, key, a: float = 1.0, *, chrome_only: bool = False):
    """Draw a menu's rows at (x, y). Returns the chosen id, or None.

    The body of `popup`, so the gallery can draw the same rows without a
    popup window around them.

    `chrome_only` submits no widgets and draws no text - which the gallery
    needs for both reasons. A widget outside any imgui window makes ImGui
    auto-create its "Debug" window, and the first version of the gallery
    cell painted one straight over the top third of the canvas; and the
    chrome pass hides text on the React side, so drawing it here would
    compare glyphs against nothing.

    The separator's y is what makes this worth diffing: it sits at
    pad + label + item + item, so it encodes every row height above it.
    """
    out, iy = None, y
    for i, it in enumerate(items):
        if _row(ui, it, x, iy, w, f"{key}.{i}", a, chrome_only=chrome_only):
            out = it.id
        iy += row_h(it)
    return out


def row_h(it) -> float:
    """How tall one row is. Measured: an item is 28 (a 20px line box with
    py-1), a label is 24 (text-xs, 16/16 with py-1) and a separator is a 1px
    rule with my-1 either side.

    One function because `measure` and the stride loop in `popup` both need
    the answer, and the two disagreeing puts every row below a label a pixel
    out - which is exactly what happened while labels were drawn on an item
    box.
    """
    if it.kind == "sep":
        return 1.0 + 2 * SEP_MY
    return LABEL_H if it.kind == "label" else ITEM_H


def measure(ui, items, min_w: float = MIN_W) -> tuple[float, float]:
    """The content box a menu needs, before chrome padding."""
    w = min_w - 2 * PAD
    h = 0.0
    for it in items:
        h += row_h(it)
        if it.kind == "sep":
            continue
        tw = D.text_w(it.label, ui.faces,
                      "medium" if it.kind == "label" else "regular",
                      12 if it.kind == "label" else 14)
        extra = 2 * ITEM_PAD_X
        if it.icon or it.checked is not None:
            extra += ICON + GAP
        if it.shortcut:
            # ONE gap, not two: measured at max-content a row is
            # `pad + label + gap + shortcut + pad`, which came to the panel
            # width to the 1/64 px. Reserving two made every menu with a
            # shortcut 6px wider than the browser's.
            extra += GAP + D.text_w(it.shortcut, ui.faces, "regular", 12,
                                    True) + SHORTCUT_TRACKING * len(it.shortcut)
        w = max(w, tw + extra)
    return w, h


def _row(ui, it, x, y, w, key, alpha, *, chrome_only: bool = False):
    """One menu row. Returns True if it was chosen this frame."""
    if it.kind == "sep":
        # `-mx-1` exactly cancels the panel's `p-1`, so the rule is
        # FULL-BLEED: measured x == panel.x and w == panel.w. The +-1 inset
        # that stood here was invented.
        D.fill(ui.dl, x - PAD, y + SEP_MY, w + 2 * PAD, 1,
               ui.col("border", alpha))
        return False
    if it.kind == "label":
        if not chrome_only:
            D.label(ui.dl, x + ITEM_PAD_X, y, it.label, ui.faces, "medium", 12,
                    ui.col("muted-foreground", alpha), baseline_box=LABEL_H)
        return False

    st = None if chrome_only else (ui.hit(key, x, y, w, ITEM_H)
                                   if it.enabled else None)
    hot = st.hot if st else 0.0
    if hot > 0.01:
        # themed alpha, as the destructive Badge is: /10 light, /20 dark
        bg = ("destructive", DESTRUCTIVE_HOVER_A.get(ui.theme_name, 0.10)) \
            if it.variant == "destructive" else ("accent", 1.0)
        D.fill(ui.dl, x, y, w, ITEM_H,
               mix(ui.col("transparent"), ui.col(*bg), hot * alpha),
               T.RADII["md"])
    # `focus:text-accent-foreground`: hovering changes the INK, not only the
    # fill. Measured in LIGHT, where the item goes 0.145 -> 0.205 and the
    # shortcut jumps 0.556 -> 0.205; in dark both already sit at 0.985, so a
    # dark-only measurement concludes the effect does not exist.
    # `accent-foreground` is not in the token tables, and its measured value
    # is exactly `secondary-foreground` in both themes.
    if it.variant == "destructive":
        ink = ui.col("destructive", alpha)          # does not change on hover
        sc_ink = ink
    elif not it.enabled:
        ink = ui.col("muted-foreground", 0.5 * alpha)
        sc_ink = ink
    else:
        ink = mix(ui.col("popover-foreground", alpha),
                  ui.col("secondary-foreground", alpha), hot)
        sc_ink = mix(ui.col("muted-foreground", alpha),
                     ui.col("secondary-foreground", alpha), hot)

    if chrome_only:
        return False

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
                sc_ink, align="right",
                box_w=w - ITEM_PAD_X, baseline_box=ITEM_H, tabular=True)
    return bool(st and st.clicked)


def popup(ui, key: str, items, *, min_w: float = MIN_W, anchor=None,
          side: str = "bottom", align: str = "end",
          offset: float = 4.0) -> str | None:
    """Draw the menu `key` if ImGui has it open. Returns the chosen item id.

    Open it with `imgui.open_popup(key)` from the trigger — usually
    `interact.row_action(..., "ellipsis-vertical")`.

    Pass `anchor` (the trigger's `box.Rect`) and the panel hangs off that
    control, flipping and shifting to stay on screen — Radix's model, which
    is what shadcn uses. Without it ImGui places the popup at the mouse,
    which reads wrong for a row action: the menu should land in the same
    place however you arrived at the button.
    """
    cw, ch = measure(ui, items, min_w)
    w, h = cw + 2 * PAD, ch + 2 * PAD

    if anchor is not None:
        vp = imgui.get_main_viewport()
        avail = B.Rect(vp.work_pos.x, vp.work_pos.y,
                       vp.work_size.x, vp.work_size.y)
        at, _ = B.place_popover(anchor, w, h, avail, side=side, align=align,
                                offset=offset)
        imgui.set_next_window_pos(imgui.ImVec2(at.x, at.y))
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
        LAST_RECT[key] = (x, y, w, h)
        saved, ui.dl = ui.dl, dl
        # the shadow and the ring fall OUTSIDE the window rect, which imgui
        # clips to; widen the clip while the chrome is drawn
        panel_chrome(ui, dl, x, y, w, h, a)

        iy = y + PAD
        for i, it in enumerate(items):
            if _row(ui, it, x + PAD, iy, cw, f"{key}.{i}", a):
                chosen = it.id
                imgui.close_current_popup()
            iy += row_h(it)
        ui.dl = saved
        imgui.end_popup()
    else:
        LAST_RECT.pop(key, None)
        ui.anim.to(f"{key}:open", 0.0)
    imgui.pop_style_color()
    imgui.pop_style_var(3)
    return chosen
