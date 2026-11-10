"""The modal layer: a scrim, a panel, a focus trap, z-order, click-outside.

`HANDOFF.md` item 3 names this as the thing to build BEFORE Dialog and
Sheet, because both are a panel on a scrim and neither can be done properly
without one.

Like `menu.py`, it BORROWS ImGui's own popup rather than reimplementing any
of it. The hard parts of a modal - trapping focus, stacking above everything,
dismissing on click-away or Escape - are already `begin_popup_modal`'s, and
the measured work is the chrome painted into it.

Everything here was measured on `?probe&open`, which carries an open Dialog
and an open Sheet. Three of the numbers are ones a reading of the classes
gets wrong:

* **the scrim is `bg-black/10`** - ten percent, not the fifty or eighty a
  guess lands on - and `oklab(0 0 0 / 0.1)` is a LITERAL black, not a token,
  the same way the slider thumb's white is;
* **it also carries `backdrop-filter: blur(4px)`**, which is most of what
  makes a modal read as separated at an alpha that low, and which a draw
  list cannot do at all. See THE BLUR below;
* **a Dialog has no drop shadow.** Its only box-shadow is a 1px
  `foreground/10` ring - measured, with every other layer transparent -
  where a Sheet has `shadow-lg` and no ring. They are not the same panel
  with a different position.

## THE BLUR

`backdrop-blur-sm` filters what is BEHIND the scrim, which needs the frame
so far as a texture. ImGui draws into one command list over whatever was
drawn before it; there is no read-back. Reproducing it means rendering the
page to an offscreen target, blurring that, and compositing - a renderer
change, not a draw call, and far outside what this kit is for.

So the kit paints the 10% wash and not the blur, and that is a DEVIATION
rather than a detail: at 10% the wash alone dims almost nothing, so a
dkit modal reads as less separated from the page than the browser's does.
The number to reach for if Hyperspace wants the separation without the blur
is a heavier wash, and that is a design decision for the app rather than a
fidelity fix - which is why this module does not quietly pick one.
`SCRIM["blur"]` is recorded so the gap is a number, not a shrug.
"""

from __future__ import annotations

from contextlib import contextmanager

from imgui_bundle import imgui

from . import box as B
from . import draw as D
from . import tokens as T

# --------------------------------------------------------------------------
# measured
# --------------------------------------------------------------------------

SCRIM = {
    # `bg-black/10`. A literal black, as measured: oklab(0 0 0 / 0.1). Not
    # `foreground`, which is #0a0a0a in light and #fafafa in dark - a scrim
    # that swapped with the theme would go WHITE in dark, and the real one
    # does not. Measured identical in both themes.
    "bg": ("#000000", 0.10),
    # `backdrop-blur-sm`, in CSS px. Not drawn - see THE BLUR in the module
    # docstring. Here so the deviation is a number.
    "blur": 4.0,
    "z": 50,
}

DIALOG = {
    "w": 384.0,                  # sm:max-w-lg, measured at a 1200px viewport
    "radius": "xl",              # rounded-xl = 14, NOT the menus' lg
    "bg": ("background", 1.0),
    # its ONLY box-shadow: ring-1 ring-foreground/10, outside the box, the
    # same ring menu.panel_chrome draws. No drop shadow at all.
    "ring": ("foreground", 0.10),
    "ring_w": 1.0,
    "shadow": None,
    "pad": T.SPACE[4],           # p-4 = 16
    "gap": T.SPACE[4],           # gap-4 = 16
    "close": 28.0,               # the close button's box
}

SHEET = {
    "size": 384.0,               # the cross-axis extent; the other is full
    "radius": 0.0,               # square: it is flush to the edge
    "bg": ("background", 1.0),
    "ring": None,                # measured: no ring
    "ring_w": 0.0,
    "shadow": T.SHADOW_LG,       # and a Dialog has none, which is the surprise
    "pad": 0.0,                  # the HEADER pads; the panel does not
    "gap": T.SPACE[4],
    "close": 28.0,
}


# --------------------------------------------------------------------------
# geometry - pure, so it is testable without a GL context
# --------------------------------------------------------------------------

def dialog_rect(viewport, w: float | None = None,
                h: float = 0.0) -> B.Rect:
    """A Dialog is centred in the viewport.

    `left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2`, and the browser
    pixel-snaps what it paints, so this rounds the way `draw.px` does rather
    than leaving the panel on a half pixel - the finding that the Slider and
    the Switch both turned on.
    """
    vw, vh = float(viewport[0]), float(viewport[1])
    ww = DIALOG["w"] if w is None else float(w)
    ww = min(ww, max(vw - 2.0 * T.SPACE[4], 0.0))
    return B.Rect(D.px((vw - ww) / 2.0), D.px((vh - h) / 2.0), ww, h)


def sheet_rect(viewport, side: str = "right",
               size: float | None = None) -> B.Rect:
    """A Sheet is flush to one edge, full extent on the other axis."""
    if side not in ("left", "right", "top", "bottom"):
        raise ValueError(f"side must be left/right/top/bottom, not {side!r}")
    vw, vh = float(viewport[0]), float(viewport[1])
    sz = SHEET["size"] if size is None else float(size)
    if side == "right":
        return B.Rect(D.px(vw - min(sz, vw)), 0.0, min(sz, vw), vh)
    if side == "left":
        return B.Rect(0.0, 0.0, min(sz, vw), vh)
    if side == "bottom":
        return B.Rect(0.0, D.px(vh - min(sz, vh)), vw, min(sz, vh))
    return B.Rect(0.0, 0.0, vw, min(sz, vh))


# --------------------------------------------------------------------------
# chrome
# --------------------------------------------------------------------------

def scrim(ui, dl, a: float = 1.0) -> None:
    """The full-viewport wash. 10% black, and no blur - see THE BLUR."""
    if a <= 0.001:
        return
    tok, al = SCRIM["bg"]
    vw, vh = ui.viewport
    D.fill(dl, 0.0, 0.0, float(vw), float(vh), T.rgba(tok, al * a))


def panel_chrome(ui, dl, x, y, w, h, tbl, a: float = 1.0) -> None:
    """A modal panel's shadow, fill and ring, from its own table.

    Deliberately NOT shared with `menu.panel_chrome`: that one hardcodes
    `popover`, `foreground/10` and `rounded-lg` because the menu, the
    ContextMenu and the Combobox were all measured identical. These two are
    not - a Dialog is rounded-xl with a ring and no shadow, a Sheet is square
    with shadow-lg and no ring - so the table decides and this reads it.
    """
    r = T.RADII[tbl["radius"]] if isinstance(tbl["radius"], str) \
        else float(tbl["radius"])
    # the shadow and the ring fall outside the window rect, which imgui
    # clips to; widen the clip while the chrome is drawn
    dl.push_clip_rect(imgui.ImVec2(x - 24, y - 24),
                      imgui.ImVec2(x + w + 24, y + h + 24), False)
    if tbl["shadow"]:
        D.shadow_stack(dl, x, y, w, h, r,
                       [(dx, dy, bl, sp, al * a)
                        for dx, dy, bl, sp, al in tbl["shadow"]])
    D.fill(dl, x, y, w, h, ui.col(tbl["bg"][0], tbl["bg"][1] * a), r)
    if tbl["ring"]:
        D.border(dl, x - 1, y - 1, w + 2, h + 2,
                 ui.col(tbl["ring"][0], tbl["ring"][1] * a),
                 r + 1, tbl["ring_w"])
    dl.pop_clip_rect()


# --------------------------------------------------------------------------
# the layer itself
# --------------------------------------------------------------------------

def open(key: str) -> None:
    """Open the layer `key`. A separate call so a trigger can do it without
    importing imgui, the way `imgui.open_popup` is used for menus."""
    imgui.open_popup(key)


def is_open(key: str) -> bool:
    return imgui.is_popup_open(key)


LAST_RECT: dict = {}


@contextmanager
def layer(ui, key: str, rect, tbl, *, a: float = 1.0):
    """Hold an open modal layer: scrim, panel chrome, and ImGui's own modal.

    Yields the panel's `box.Rect` while it is open and None while it is not,
    so a caller is `with layer(...) as r: if r is None: ...` - the same shape
    `menu.popup` has, where the CLOSED branch has to run too or the seam
    outlives the panel (RETRO row 39, which was exactly this bug in
    `interact.select`).

    The scrim is painted into the BACKGROUND draw list rather than the popup's
    own: a popup window is the size of its panel, and ImGui clips a window's
    draw list to the window, so a full-viewport wash drawn inside it would be
    cropped to the panel it is supposed to sit behind.
    """
    if not imgui.is_popup_open(key):
        LAST_RECT.pop(key, None)
        yield None
        return

    if not isinstance(rect, B.Rect):
        rect = B.Rect(*rect)

    scrim(ui, imgui.get_background_draw_list(), a)

    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
    imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
    imgui.push_style_var(imgui.StyleVar_.popup_border_size, 0.0)
    # ImGui's own dim is a flat `modal_window_dim_bg` over the whole viewport,
    # which would stack on top of the measured 10% wash and double it.
    imgui.push_style_color(imgui.Col_.modal_window_dim_bg,
                           imgui.ImVec4(0, 0, 0, 0))
    imgui.set_next_window_pos(imgui.ImVec2(rect.x, rect.y))
    imgui.set_next_window_size(imgui.ImVec2(rect.w, rect.h))
    opened = imgui.begin_popup_modal(
        key, None,
        imgui.WindowFlags_.no_decoration
        | imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_saved_settings
        | imgui.WindowFlags_.no_scrollbar
        | imgui.WindowFlags_.no_scroll_with_mouse
        # the kit paints the panel; imgui's window_bg would sit under it and
        # darken the fill, the way it does in the test harness
        | imgui.WindowFlags_.no_background)[0]
    try:
        if opened:
            LAST_RECT[key] = (rect.x, rect.y, rect.w, rect.h)
            panel_chrome(ui, imgui.get_window_draw_list(),
                         rect.x, rect.y, rect.w, rect.h, tbl, a)
            yield rect
        else:
            LAST_RECT.pop(key, None)
            yield None
    finally:
        if opened:
            imgui.end_popup()
        imgui.pop_style_color()
        imgui.pop_style_var(3)
