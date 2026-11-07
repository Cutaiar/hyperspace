"""ContextMenu: the DropdownMenu panel, opened by a right-click at the pointer.

A ContextMenu is not a new panel. It is `menu.popup` placed at the POINTER
instead of against a trigger, so this module is placement plus a gesture and
nothing else — the chrome comes from `menu.py` wholesale.

**The verdict on the chrome, with the evidence.** Diffing
`prototypes/dashboard/src/components/ui/context-menu.tsx` against
`dropdown-menu.tsx`, the class strings for the item, the label, the separator
and the shortcut are character-for-character identical, and the content panel
differs in exactly one chrome token:

    content   dropdown  ... min-w-32 w-(--radix-dropdown-menu-trigger-width)
              context   ... min-w-36                     <- 144, not 128
    item      identical: rounded-md px-1.5 py-1 text-sm gap-1.5
                         focus:bg-accent focus:text-accent-foreground
                         destructive: /10, dark /20
    label     identical: px-1.5 py-1 text-xs font-medium text-muted-foreground
    separator identical: -mx-1 my-1 h-px bg-border
    shortcut  identical: ml-auto text-xs tracking-widest text-muted-foreground

(The two differ again in `SubContent` — context's carries `border` where
dropdown's carries `ring-1 ring-foreground/10` — but neither `menu.py` nor
this module draws submenus, so it is out of scope.)

So: **the chrome is identical apart from the 144px floor**, and `min_w` is
the only thing this module overrides when it calls `menu.popup`.

Everything below was measured on the real component in Chromium at dpr 1 —
`?probe`, block `contextmenu.target`, opened with a real right-click because
Radix's ContextMenu has no `defaultOpen` — in both themes, hovering each item
and dwelling 400ms (past the 150ms transition). Rest + hover + the placement
sweep, not a reading of the classes.

    panel     144.000 x 125.000   radius 10   p-1 = 4
              bg popover (#ffffff / #171717)
              ring  1px spread box-shadow, foreground/10, OUTSIDE the box
                    (light oklab(0.145 0 0 / .1), dark oklab(0.985 0 0 / .1))
              shadow-md  rgba(0,0,0,.1) 0 4 6 -1 + rgba(0,0,0,.1) 0 2 4 -2
                         — identical in both themes
              max-height = the viewport's available height; overflow-y auto
    rows      label 24  ·  item 28  ·  separator 1 with my-1 -> a 9px block
              4 + 24 + 28 + 28 + 9 + 28 + 4 = 125, which is the panel exactly
    item      px-1.5 = 6   gap 6   text 14/20   radius 8   icon 16 at y + 6
    shortcut  text 12/16, right edge = item.right - 6, centred at y + 6
    label     text 12/16 weight 500, muted-foreground

What surprised me, i.e. what a reading of the classes gets wrong:

* **an item is 28px tall, not 26.** `menu.py` uses `ITEM_H = 26.0`
  ("py-1 either side of a 14px line"), but `text-sm` carries a 20px
  line-height, so the row is 20 + 4 + 4 = 28. Measured on three separate
  items, with and without a shortcut, with and without an icon: 28.000 every
  time. The item classes are identical between the two components, so this is
  a `menu.py` number to fix rather than a ContextMenu difference — it is
  reported, not patched, and this module takes its panel height from
  `menu.measure` so it stays right when that lands.
* **the label row is 24, not an item height.** `text-xs` is 16/16 + py-1.
* **the separator is full-bleed.** `-mx-1` exactly cancels the panel's `p-1`,
  so the rule runs from the panel's left edge to its right edge: measured
  x = panel.x, w = 144.000 = panel.w. `menu.py` insets it by 1px a side.
* **hovering an item changes the TEXT colour too**, not just the background:
  `focus:text-accent-foreground`. Light goes #0a0a0a -> #171717 (lighter, not
  darker) and the shortcut jumps muted-foreground -> accent-foreground
  (oklch .556 -> .205), which is the loudest part of the change. In dark both
  land on #fafafa, so the effect is invisible there — measure one theme only
  and you would conclude it does not exist.
* **`accent-foreground` is not in `tokens.LIGHT`/`DARK` at all.** Measured
  oklch(0.205 0 0) light and oklch(0.985 0 0) dark, which are exactly
  `secondary-foreground` in each theme (#171717 / #fafafa). That is the token
  named below, with the measurement recorded so the coincidence is visible.
* **the destructive hover fill is themed in its ALPHA**, like `tokens.BADGE`:
  `destructive/10` light, `destructive/20` dark — measured
  oklab(... / 0.1) and oklab(... / 0.2). `menu.py` uses 0.10 in both.
  The destructive ink does NOT change on hover.
* **an item's icon is 16, not 14.** `[&_svg:not([class*='size-'])]:size-4`;
  measured 16x16 at (6, 6) in a 28 row. `menu.py` uses `ICON = 14.0`.
* **the shortcut carries letter-spacing 1.2px** (`tracking-widest` = 0.1em at
  12px), and Chromium puts that space after the last glyph too: "⌘O"
  measures 23.2813, which is 2 x 1.2 wider than its glyphs. Neither
  `menu.py` nor `draw.text_w` tracks text, so a shortcut's reserved width is
  short by 1.2 px per character.
* **the width law gives a shortcut ONE gap, not two.** At max-content the
  item is `6 + label + 6 + shortcut + 6`: measured label 194.3125 +
  shortcut 23.2813 + 26 = 243.5938 = the panel's width to the 1/64 px.
  `menu.measure` reserves `GAP * 2` there, so it comes out 6px wide.

**The pointer offset is +2, and it is not zero.** Radix's ContextMenu anchors
a 0x0 virtual element at the pointer and places the panel with
`side="right" sideOffset={2} align="start"`, so

    panel.x = pointer.x + 2        panel.y = pointer.y

Measured dx = +2.000 at every click point in both themes, and dy = 0.000
whenever the panel fits below the pointer.

Two more things the sweep showed, both of which this module reproduces:

* **it flips on x and shifts on y.** The flip threshold is exact: in a 400px
  viewport with a 144px panel, a click at x=254 stays on the right (its right
  edge landing on 400.000) and a click at x=255 flips to
  `panel.right = pointer.x - 2`, measured at x=109. On y it never flips: it
  clamps to `viewport.bottom - h` with **zero** collision padding (bottom gap
  measured 0.000 at several click points), and a viewport shorter than the
  panel clamps the panel's own height instead (vh=100 -> h=100, y=0).
* **Radix does NOT clamp x.** With a 160px viewport, a click at x=80 left the
  panel at x=82 hanging 66px off the right edge, and a click at x=140 flipped
  it to x=-6, 6px off the left. `place_at_pointer` clamps instead — a
  deliberate divergence, documented there, which can only bite in a window
  narrower than `min_w + 2`.

**The KEYBOARD is `menu.popup`'s, and that is a measurement rather than an
assumption.** Driven on `?probe`'s `contextmenu.target` with a real
right-click - Radix's ContextMenu has no `defaultOpen`, which is the one way
this block was already right - the keyboard is the DropdownMenu's to the
key: a right-click opens the panel with NOTHING highlighted and focus on the
content; ArrowDown then takes the first row and ArrowUp the LAST; the arrows
move one row and CLAMP at both ends rather than wrapping; Home and PageUp go
to the first row and End and PageDown to the last; a letter jumps by prefix
with a 1s buffer; Enter and Space take the highlight and close; Escape
closes; and Tab is SWALLOWED - the panel stays open and focus does not move.

The one difference from a DropdownMenu is where the focus goes afterwards,
and it is forced rather than chosen: a ContextMenu has no trigger button, so
Escape and Enter leave `document.activeElement` on the BODY where a
DropdownMenu returns it to the trigger.

So this module needs no keyboard of its own. The full measured table lives
above THE KEYBOARD in `menu.py`, with the probe block each row came from
named beside it, and `test_menu_keys.py::test_a_right_clicked_menu_answers_the_same_keys`
drives this panel through it - which is what makes "it inherits" a claim and
not a hope.

**One caveat before this goes near the GRAPH canvas.** `replay.keep`
(`hyperspace/replay.py:91`) carries only the page window's own draw list into
the canvas tap and explicitly drops "every popup, menu and tooltip (their own
windows)". A context menu opened over that canvas will NOT appear in the
`panel:graph` texture that feeds the render graph. It is fine on the panel; it
cannot be part of anything projected.
"""

from __future__ import annotations

import box as B
import tokens as T

# --------------------------------------------------------------------------
# the measured table
# --------------------------------------------------------------------------
#
# `(token, alpha)` pairs follow tokens.BADGE / tokens.SWITCH: the alpha
# MULTIPLIES whatever the token already carries, which is how
# `bg-destructive/10` works. Sizes are in CSS px at dpr 1.
#
# Where a value is already in `menu.py`, the comment says so and gives
# menu.py's name - these are NOT silent duplicates, and
# test_context_menu.py asserts the agreement so the two cannot drift. The
# four rows marked DIFFERS are where menu.py and the browser disagree.
CONTEXT_MENU = {
    # -- panel ----------------------------------------------------------
    # min-w-36. The ONLY chrome number that differs between ContextMenu and
    # DropdownMenu (menu.MIN_W = 128 = min-w-32), and so the only thing this
    # module passes down to menu.popup.
    "min_w": 144.0,
    "pad": T.SPACE[1],                  # p-1 = 4          == menu.PAD
    "radius": "lg",                     # rounded-lg = 10  == menu.popup's
    "bg": ("popover", 1.0),             #                  == menu.popup's
    "ring": ("foreground", 0.10),       # ring-1 ring-foreground/10, outside
    "ring_w": 1.0,                      #                  == menu.popup's
    "shadow": T.SHADOW_MD,              # shadow-md        == menu.popup's

    # -- rows -----------------------------------------------------------
    "item_h": 28.0,                     # DIFFERS: menu.ITEM_H is 26
    "label_h": 24.0,                    # DIFFERS: menu.py draws labels at 26
    "sep_h": 1.0,                       # h-px             == menu.py's 1
    "sep_my": T.SPACE[1],               # my-1 = 4         == menu.SEP_MY
    "sep_bleed": True,                  # DIFFERS: menu.py insets it 1px/side
    "sep": ("border", 1.0),             #                  == menu.py's
    "item_pad_x": T.SPACE[1.5],         # px-1.5 = 6       == menu.ITEM_PAD_X
    "item_radius": "md",                # rounded-md = 8   == menu.py's
    "gap": T.SPACE[1.5],                # gap-1.5 = 6      == menu.GAP
    "icon": 16.0,                       # DIFFERS: menu.ICON is 14
    "font": 14.0,                       # text-sm/20       == menu.py's
    "label_font": 12.0,                 # text-xs/16       == menu.py's
    "shortcut_font": 12.0,              # text-xs/16       == menu.py's
    "shortcut_tracking": 1.2,           # tracking-widest = 0.1em at 12px
                                        # (not implemented by draw.text_w)

    # -- ink ------------------------------------------------------------
    "ink": ("popover-foreground", 1.0),
    "muted_ink": ("muted-foreground", 1.0),      # label + resting shortcut
    "hover_bg": ("accent", 1.0),
    # measured accent-foreground: oklch(0.205 0 0) light, oklch(0.985 0 0)
    # dark - i.e. #171717 / #fafafa, which is `secondary-foreground` in both
    # themes. There is no `accent-foreground` key in tokens.LIGHT/DARK.
    "hover_ink": ("secondary-foreground", 1.0),
    "destructive_ink": ("destructive", 1.0),
    "destructive_hover_bg": ("destructive", 0.10),
    "disabled_opacity": 0.5,            # data-disabled:opacity-50 (class;
                                        # the probe has no disabled item)

    # -- placement ------------------------------------------------------
    "pointer_dx": 2.0,                  # Radix sideOffset on side="right"
    "pointer_dy": 0.0,                  # align="start" on a 0x0 anchor
    "collision_pad": 0.0,               # measured bottom/right gap of 0.000
}

# Not a pure token swap: the destructive focus fill carries
# `data-[variant=destructive]:focus:bg-destructive/10
#  dark:data-[variant=destructive]:focus:bg-destructive/20`, so the ALPHA is
# themed - the same shape as tokens.BADGE_DARK. Measured
# oklab(0.577 .. / 0.1) light and oklab(0.704 .. / 0.2) dark.
CONTEXT_MENU_DARK = {
    "destructive_hover_bg": ("destructive", 0.20),
}


def context_menu_table(theme_name: str) -> dict:
    """The table resolved for one theme, like tokens.badge_table."""
    t = dict(CONTEXT_MENU)
    if theme_name == "dark":
        t.update(CONTEXT_MENU_DARK)
    return t


POINTER_DX = CONTEXT_MENU["pointer_dx"]
POINTER_DY = CONTEXT_MENU["pointer_dy"]
MIN_W = CONTEXT_MENU["min_w"]


# --------------------------------------------------------------------------
# placement: at the pointer, not against a trigger
# --------------------------------------------------------------------------

def place_at_pointer(px: float, py: float, w: float, h: float,
                     avail: B.Rect, *, dx: float = POINTER_DX,
                     dy: float = POINTER_DY,
                     pad: float = 0.0) -> B.Rect:
    """Where a context menu goes for a right-click at (px, py). Pure geometry.

    This is the one way a context menu differs from `box.place_popover`: the
    anchor is the POINTER, a 0x0 virtual element, rather than a control. The
    law is Radix's, measured rather than assumed:

      * `x = px + 2`, `y = py` — the +2 is Radix's `sideOffset` on the
        implicit `side="right" align="start"`, and it is not zero.
      * **flip on x**: if the panel's right edge would pass the viewport's,
        put it on the other side of the pointer (`right = px - 2`). If
        neither side fits, keep the side that overflows less, and keep the
        preferred (right) side on a tie — floating-ui's `bestFit`, which is
        what the measurements show.
      * **shift on y**: it never flips upward. It clamps to
        `avail.bottom - h`, with zero collision padding, exactly as measured.
      * a panel taller than the viewport has its HEIGHT clamped, the way
        Radix's `max-h-(--radix-context-menu-content-available-height)` does
        (measured: a 100px-tall viewport gave a 100px-tall panel at y=0).

    One deliberate divergence: Radix lets the panel hang off the left or
    right edge when neither side fits (measured 66px off the right in a 160px
    viewport), because its `shift` middleware runs on the align axis only.
    This clamps x as well, so the panel is always reachable — it can only
    matter in a window narrower than `min_w + dx`, and an ImGui popup that
    leaves the window is simply lost.
    """
    h = min(h, max(avail.h - 2.0 * pad, 0.0))

    x = px + dx
    if x + w > avail.right - pad:
        alt = px - dx - w
        over_right = (x + w) - (avail.right - pad)
        over_left = (avail.x + pad) - alt
        if over_left < over_right:
            x = alt

    y = py + dy

    # clamp last, and clamp low last of all, so a panel that cannot fit pins
    # to the top-left rather than hiding its first row (the same ordering
    # box.place_popover uses, and for the same reason)
    x = min(x, avail.right - pad - w)
    x = max(x, avail.x + pad)
    y = min(y, avail.bottom - pad - h)
    y = max(y, avail.y + pad)
    return B.Rect(x, y, w, h)


# --------------------------------------------------------------------------
# the widget
# --------------------------------------------------------------------------

def context_menu(ui, key: str, rect, items, *, min_w: float = MIN_W,
                 allow_overlap: bool = True) -> str | None:
    """Right-click inside `rect` to open `items`. Returns the chosen id.

    Follows `interact.select`: a real hit target, `imgui.open_popup` on the
    gesture, and `menu.popup` for the panel — the hard parts of a popup
    (focus, dismissal on click-away or Escape, nesting, z-order) are already
    ImGui's and reimplementing them would be the wrong kind of work.

    Two details that are not optional:

    * The target keeps an `invisible_button` with its `##id` (`ui.hit`), so
      `tests/ui_driver.py:43-46` can find it. `allow_overlap` is on by
      default because a context-menu target is usually a whole region with
      smaller controls drawn on top of it, and without it the region would
      swallow their hover.
    * The pointer position has to SURVIVE the frame it was clicked in — the
      panel is placed every frame while it is open, and a `Ui` is rebuilt
      every frame (dashboard.py). So it lives in `ui.anim.store`, which is
      the one object the kit already threads across frames; that is the same
      trap that kept the tooltip from ever reaching its delay.

    `menu.popup` draws the panel, so the chrome is DropdownMenu's, which is
    what the class diff says it should be. Only `min_w` is overridden (144,
    `min-w-36`). The panel's size comes from `menu.measure`, so when
    menu.py's measured row heights are corrected the placement follows.
    """
    from imgui_bundle import imgui
    import menu

    if not isinstance(rect, B.Rect):
        rect = B.Rect(*rect)
    pkey = f"##ctx.{key}"
    at = ui.anim.store.setdefault("ctxmenu", {})

    st = ui.hit(key, rect.x, rect.y, rect.w, rect.h,
                allow_overlap=allow_overlap)
    if st.hovered and imgui.is_mouse_clicked(imgui.MouseButton_.right):
        m = imgui.get_mouse_pos()
        at[key] = (m.x, m.y)
        imgui.open_popup(pkey)

    if imgui.is_popup_open(pkey):
        px, py = at.get(key, (rect.x, rect.y))
        cw, ch = menu.measure(ui, items, min_w)
        w, h = cw + 2.0 * menu.PAD, ch + 2.0 * menu.PAD
        panel = place_at_pointer(px, py, w, h, ui.viewport)
        # menu.popup only sets the window position when it is given an
        # `anchor`; with none, this request is the one Begin consumes.
        imgui.set_next_window_pos(imgui.ImVec2(panel.x, panel.y))
    else:
        at.pop(key, None)

    # called either way: the closed branch of menu.popup is what resets the
    # open animation and clears menu.LAST_RECT
    return menu.popup(ui, pkey, items, min_w=min_w)
