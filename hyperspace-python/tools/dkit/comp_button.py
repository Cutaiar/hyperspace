"""shadcn Button and ButtonGroup, as measured.

Every number in this file came out of Chromium — `probe_react.js` on the
`?probe` route for the rest states, one-off Playwright scripts for the states
that only exist under a pseudo-class, and pixel reads of the rendered boxes
where a computed style could not settle it. Nothing here was derived from a
reading of the Tailwind classes, because eight of these numbers are not what
the classes imply.

What surprised me, in the order it cost me time
-----------------------------------------------

* **The fill is inset 1 px from the box on every side.** Every variant carries
  `border border-transparent` *and* `bg-clip-padding`, so the background is
  clipped to the padding box and the 1 px border ring is fully transparent on
  five of the six variants. A `default` button at x 20 w 80 paints its
  `primary` fill into columns 21..98 and leaves columns 20 and 99 showing the
  page. The inner radius is the outer one less the border, so a `rounded-lg`
  button fills at radius 9, not 10 — fitted off the corner arc, whose left
  tangent sits at x+1 from y+10 down.

* **`disabled:opacity-50` does NOT need `ease.over` here**, which is the
  opposite of the Input. Because `bg-clip-padding` makes the border ring and
  the fill DISJOINT, each is composited against the page and dimmed on its
  own. Measured on the one case that can tell them apart — a disabled
  `outline` in dark, whose border is white/15 over a white/4.5 fill: the
  border paints at **28** and the fill at **15**. Dimming each separately
  predicts 28.3 and 15.5; folding the border over the fill first (what
  `draw.field` correctly does for the Input, whose fill does run under its
  border) predicts 33. So `draw.field`'s rule is right for the Input and
  wrong for the Button, and the difference is five levels.

* **`hover:bg-primary/80` is an ALPHA, not a mix, and it is /80 not /90.**
  The existing `draw.button` stub mixed `primary` 10% toward `background`;
  measured, light hover is #171717 at 0.8 over white = **69**, and a 10% mix
  would be 46. Two separate errors in one line.

* **`outline` is not transparent in light.** It is `bg-background` — opaque
  white — and `dark:bg-input/30`. Its border is `border-border` in light but
  `dark:border-input`, which are different tokens in dark (0.10 vs 0.15
  alpha).

* **In dark, `outline` keeps its border colour under focus.** Every other
  variant takes `focus-visible:border-ring`; `dark:border-input` sorts after
  `focus-visible:border-ring` in Tailwind's output and wins, so the dark
  outline button's border is still `input` while focused (measured 46, where
  `ring` would be 115). Light does take the ring. The class list gives no
  hint of this.

* **`secondary`'s hover is an oklch mix and has to be a literal.**
  `hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)]`
  rasterizes to #e7e7e7 in light and #2f2f2f in dark. The same 5% done as an
  sRGB lerp gives #e9e9e9 and #313131 — two levels out in both themes, so the
  mix cannot be faked with `ease.mix` and the measured bytes go in the table.

* **The radius is size-dependent and the two expressions for it agree only by
  accident.** `xs` is `rounded-[min(var(--radius-md),10px)]` and `sm` is
  `rounded-[min(var(--radius-md),12px)]`; with this project's
  `--radius: 0.625rem` both resolve to 8, and the base `rounded-lg` is 10. At
  a larger `--radius` they would diverge, so the cap is kept per size rather
  than the answer.

* **Inside a ButtonGroup every size's radius becomes 10.**
  `in-data-[slot=button-group]:rounded-lg` overrides the small sizes' 8.

* **`sm`'s font size is 12.8 px**, not 12 — `text-[0.8rem]`, with a 19.2 px
  line height. And `icon-sm`'s glyph is 16, not 14: the `size-3.5` override
  belongs to `sm`, and `icon-sm` inherits the base `size-4`.

* **The press nudge rides on the `translate` property, not `transform`.**
  `active:not-aria-[haspopup]:translate-y-px` reads back as
  `translate: 0px 1px` with `transform: none`, and the box's own rect moves
  by exactly +1.0 in y. It is 1 px, downward, and `aria-haspopup` suppresses
  it — so a dropdown trigger does not bounce.

* **Hover tint and press nudge belong to different states.** Press the button
  and drag off it while still held: `:active` stays true and the nudge stays,
  but `:hover` goes false and the fill returns to its REST colour. So the
  tint tracks hover alone and the nudge tracks the press alone. The active
  background is otherwise identical to the hover background — there is no
  third colour, which is what the old stub's extra `down * 0.35` invented.

* **A ButtonGroup's borders are not doubled, and its top and bottom borders
  run straight through the seam.** Three 60 px children at x 20/80/140 make a
  180 px group — the widths sum exactly, with no overlap and no gap. The seam
  is ONE column: child 0's right border at x 79. Child 1 has `border-l-0`, so
  its fill starts at its own box edge (x 80), but its top border still covers
  x 80 — the dropped side loses only its own strip's interior, not the 1 px
  where the perpendicular borders reach the corner.

What I could NOT measure, and where I guessed
---------------------------------------------

* **The link underline's thickness at sizes other than 14 px.**
  `text-decoration-thickness: auto` resolves out of the font, and I only have
  a rendered `link` button at the default size: one row, 1 px, at box-relative
  y 25 of a 32 px button, spanning exactly the text's own advance width. The
  offset (`underline-offset-4` = 4 px below the alphabetic baseline) is
  measured and `UNDERLINE_W` is pinned at 1.0 for every size — a guess for
  xs/sm, where Chromium might pick a thinner rule.

* **`aria-expanded:bg-muted`** on outline/ghost/secondary, and the whole
  `aria-invalid:` group. There is no probe block that opens a button into an
  expanded state, so those are absent from this table rather than guessed at.

* **Chromium loses ~23% of coverage on the single pixel where two of an
  element's own borders meet** (light: 235 where the border is 229), which is
  its mitre join antialiasing. Not modelled: it is one pixel and it is the
  browser's painting, not the geometry.

Where a value is (token, alpha) the alpha MULTIPLIES whatever the token
already carries, as everywhere else in the kit — see tokens.rgba.
"""

from __future__ import annotations

from dataclasses import dataclass

from imgui_bundle import imgui

import draw as D
from ease import mix
from tokens import RADII, RING_W, SPACE, rgba


# --------------------------------------------------------------------------
# sizes
# --------------------------------------------------------------------------
#
# Chromium, one row per `size` on ?probe, rest state, both themes (identical):
#
#   size       box          radius  pad_x  font   line   gap  glyph
#   xs          55.484x24      8      8    12     16      4    12
#   sm          61.969x28      8     10    12.8   19.2    4    14
#   default     65.719x32     10     10    14     20      6    16
#   lg          65.719x36     10     10    14     20      6    16
#   icon-xs         24x24      8      0    14     20      -    12
#   icon-sm         28x28      8      0    14     20      -    16
#   icon            32x32     10      0    14     20      -    16
#   icon-lg         36x36     10      0    14     20      -    16
#
# The box widths are for the string "Button" in Geist Medium 14 and are not
# pinned anywhere: the content width is what `button_size` computes, and
# ImGui's rasterizer will not agree with Chromium's to the fraction. The
# browser's content widths, for the record, were 43.719 / 37.484 / 39.969 at
# 14 / 12 / 12.8 px — all three the same string, scaled.
#
# `pad_icon` is the padding that `has-data-[icon=inline-start]:pl-N` and
# `...inline-end]:pr-N` swap in on the side the icon is on: measured
# 10 -> 8 on default/lg and 8 or 10 -> 6 on xs/sm.
#
# `radius_cap` is the `min(var(--radius-md), Npx)` cap, kept rather than its
# answer because `xs` caps at 10 and `sm` at 12 and both only happen to land
# on 8 with --radius at 0.625rem. None means the base `rounded-lg`.

BUTTON_SIZES = {
    "xs": {
        "h": 24.0, "radius_cap": 10.0, "square": False,
        "pad_x": SPACE[2], "pad_icon": SPACE[1.5],
        "font": 12.0, "line": 16.0, "gap": SPACE[1], "glyph": 12.0,
    },
    "sm": {
        "h": 28.0, "radius_cap": 12.0, "square": False,
        "pad_x": SPACE[2.5], "pad_icon": SPACE[1.5],
        # text-[0.8rem]: 12.8, NOT 12 - and its line height is 19.2
        "font": 12.8, "line": 19.2, "gap": SPACE[1], "glyph": 14.0,
    },
    "default": {
        "h": 32.0, "radius_cap": None, "square": False,
        "pad_x": SPACE[2.5], "pad_icon": SPACE[2],
        "font": 14.0, "line": 20.0, "gap": SPACE[1.5], "glyph": 16.0,
    },
    "lg": {
        "h": 36.0, "radius_cap": None, "square": False,
        "pad_x": SPACE[2.5], "pad_icon": SPACE[2],
        "font": 14.0, "line": 20.0, "gap": SPACE[1.5], "glyph": 16.0,
    },
    # The icon sizes keep text-sm (14/20) even though their box is smaller:
    # there is no `text-xs` on `icon-xs`. It matters if a caller puts a glyph
    # or a single character in one.
    "icon-xs": {
        "h": 24.0, "radius_cap": 10.0, "square": True,
        "pad_x": 0.0, "pad_icon": 0.0,
        "font": 14.0, "line": 20.0, "gap": 0.0, "glyph": 12.0,
    },
    "icon-sm": {
        "h": 28.0, "radius_cap": 12.0, "square": True,
        "pad_x": 0.0, "pad_icon": 0.0,
        # 16, not 14: `size-3.5` is on `sm`, and `icon-sm` inherits `size-4`
        "font": 14.0, "line": 20.0, "gap": 0.0, "glyph": 16.0,
    },
    "icon": {
        "h": 32.0, "radius_cap": None, "square": True,
        "pad_x": 0.0, "pad_icon": 0.0,
        "font": 14.0, "line": 20.0, "gap": 0.0, "glyph": 16.0,
    },
    "icon-lg": {
        "h": 36.0, "radius_cap": None, "square": True,
        "pad_x": 0.0, "pad_icon": 0.0,
        "font": 14.0, "line": 20.0, "gap": 0.0, "glyph": 16.0,
    },
}

BORDER_W = 1.0           # `border` on every variant, visible or not
NUDGE = 1.0              # active:...:translate-y-px, measured as exactly +1 y
UNDERLINE_OFFSET = SPACE[1]     # underline-offset-4
UNDERLINE_W = 1.0        # measured at 14px only - see the note at the top

# Geist: ascender 1005 / (1005 + 295) of the span draw.FONT_SPAN_EM carries.
# The link's underline hangs off the alphabetic baseline, which is that far
# down the glyph box - not off the box's own centre.
ASCENT_FRAC = 1005.0 / 1300.0


# --------------------------------------------------------------------------
# variants
# --------------------------------------------------------------------------
#
# `fill`/`hover_fill` are the background; `border` is the 1 px ring, which is
# transparent on everything but `outline`; `ink` is the text. `focus_border`
# is what `focus-visible` swaps the border to and `ring` is the 3 px
# `focus-visible:ring-N` band outside it.
#
# `hover_ink` is deliberately absent: `outline` and `ghost` both carry
# `hover:text-foreground`, and measured, that is the colour they already had
# at rest in both themes. The class promises a change that never happens.

BUTTON = {
    "default": {
        "fill": ("primary", 1.0),
        "hover_fill": ("primary", 0.8),          # bg-primary/80, an ALPHA
        "border": ("transparent", 1.0),
        "focus_border": ("ring", 1.0),
        "ink": ("primary-foreground", 1.0),
        "ring": ("ring", 0.5),
        "underline": False,
    },
    "outline": {
        "fill": ("background", 1.0),             # opaque white in light
        "hover_fill": ("muted", 1.0),
        "border": ("border", 1.0),
        "focus_border": ("ring", 1.0),
        "ink": ("foreground", 1.0),
        "ring": ("ring", 0.5),
        "underline": False,
    },
    "secondary": {
        "fill": ("secondary", 1.0),
        # color-mix(in oklch, secondary, foreground 5%), rasterized. A
        # LITERAL: an sRGB lerp lands on #e9e9e9, two levels out.
        "hover_fill": ("#e7e7e7", 1.0),
        "border": ("transparent", 1.0),
        "focus_border": ("ring", 1.0),
        "ink": ("secondary-foreground", 1.0),
        "ring": ("ring", 0.5),
        "underline": False,
    },
    "ghost": {
        "fill": ("transparent", 1.0),
        "hover_fill": ("muted", 1.0),
        "border": ("transparent", 1.0),
        "focus_border": ("ring", 1.0),
        "ink": ("foreground", 1.0),
        "ring": ("ring", 0.5),
        "underline": False,
    },
    "destructive": {
        "fill": ("destructive", 0.10),
        "hover_fill": ("destructive", 0.20),
        "border": ("transparent", 1.0),
        "focus_border": ("destructive", 0.4),    # not `ring`
        "ink": ("destructive", 1.0),
        "ring": ("destructive", 0.2),
        "underline": False,
    },
    "link": {
        "fill": ("transparent", 1.0),
        "hover_fill": ("transparent", 1.0),      # no tint at all
        "border": ("transparent", 1.0),
        "focus_border": ("ring", 1.0),
        "ink": ("primary", 1.0),
        "ring": ("ring", 0.5),
        "underline": True,                       # hover:underline
    },
}

# Only the keys that actually differ. `button_table` merges per VARIANT key,
# not per variant, so a one-line change here does not have to restate a whole
# variant - and every entry below is something a reading of the classes gets
# wrong in dark.
BUTTON_DARK = {
    "outline": {
        "fill": ("input", 0.3),                  # dark:bg-input/30
        "hover_fill": ("input", 0.5),            # dark:hover:bg-input/50
        "border": ("input", 1.0),                # dark:border-input, not `border`
        # `dark:border-input` sorts AFTER `focus-visible:border-ring` in
        # Tailwind's output and wins, so the dark outline button's border does
        # not change under focus. Measured 46 (input) where ring would be 115.
        "focus_border": ("input", 1.0),
    },
    "secondary": {
        # the same oklch mix, rasterized on the dark palette
        "hover_fill": ("#2f2f2f", 1.0),
    },
    "ghost": {
        "hover_fill": ("muted", 0.5),            # dark:hover:bg-muted/50
    },
    "destructive": {
        "fill": ("destructive", 0.20),           # dark:bg-destructive/20
        "hover_fill": ("destructive", 0.30),
        "ring": ("destructive", 0.4),            # dark:focus-visible:ring/40
    },
}

DISABLED_OPACITY = 0.5           # disabled:opacity-50


def button_table(theme_name: str) -> dict:
    """The variant table resolved for one theme.

    Merged per key rather than per variant, so BUTTON_DARK only has to carry
    what is genuinely themed. tokens.badge_table replaces whole entries
    because a Badge has two keys; a Button has seven and restating them all
    would hide which ones move.
    """
    out = {k: dict(v) for k, v in BUTTON.items()}
    if theme_name == "dark":
        for variant, over in BUTTON_DARK.items():
            out[variant].update(over)
    return out


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def button_radius(size: str, *, in_group: bool = False) -> float:
    """The outer corner radius for a size.

    `rounded-lg` by default; the four small sizes carry
    `rounded-[min(var(--radius-md), Npx)]` and land on 8 with this project's
    --radius. Inside a ButtonGroup `in-data-[slot=button-group]:rounded-lg`
    puts every size back to 10 — measured, not inferred.
    """
    s = BUTTON_SIZES[size]
    if in_group or s["radius_cap"] is None:
        return RADII["lg"]
    return min(RADII["md"], s["radius_cap"])


def button_size(size: str, label: str, faces: dict, *, icon: bool = False,
                icon_side: str = "inline-start", drop: str | None = None,
                text_w: float | None = None) -> tuple:
    """The intrinsic (w, h) of a button, for the layout tree to size it.

    `inline-flex shrink-0` with `justify-center`, so the width is the content
    plus the two paddings plus the two borders:

        w = text + icon? (glyph + gap) + pad_left + pad_right + borders

    An icon-only size is a square and ignores the label. `icon=True` also
    swaps in the tighter padding on the icon's own side
    (`has-data-[icon=inline-start]:pl-2` and friends).

    `drop` is the side whose border a ButtonGroup removed ("left" or "top").
    It only ever changes a SHRINK-TO-FIT axis, and only one axis is ever
    shrink-to-fit, which took a measurement to pin down:

      * a text size's WIDTH is its content's, so `border-l-0` makes it
        exactly 1 px narrower. Measured, three `default` children in a
        horizontal group: 65.7188 / 64.7188 / 64.7188, summing to the
        group's 195.1563.
      * a `size-N` icon button's width is EXPLICIT, so `border-l-0` leaves
        the box at 32 and gives the content a pixel instead. Measured: three
        `icon` children in a horizontal group are 32 / 32 / 32, group 96.
      * the HEIGHT is explicit (`h-8`) at every size, so `border-t-0` in a
        vertical group never changes it. Measured: both children of the real
        vertical group are 32 tall and the group is 64.

    `text_w` overrides the measurement, so the law can be unit-tested without
    a font atlas or a GL context. Otherwise the label is measured with
    `draw.text_w` on the `medium` face at the size's own font size, which is
    what the chrome will draw with.
    """
    s = BUTTON_SIZES[size]
    h = s["h"]
    if s["square"]:
        return (h, h)

    tw = (D.text_w(label, faces, "medium", s["font"]) if text_w is None
          else float(text_w))
    pad_l = pad_r = s["pad_x"]
    inner = tw
    if icon:
        inner += s["glyph"] + s["gap"]
        if icon_side == "inline-start":
            pad_l = s["pad_icon"]
        else:
            pad_r = s["pad_icon"]
    bw = 2.0 * BORDER_W - (BORDER_W if drop == "left" else 0.0)
    return (inner + pad_l + pad_r + bw, h)


# -- ButtonGroup -----------------------------------------------------------
#
# The joins are the whole component. Measured on a group pinned to whole
# pixels - three 60 px children at x 20 / 80 / 140, inside a 180 px group:
#
#   * the widths SUM to the group's width. No overlap, no gap.
#   * the seam is ONE border column, x 79, which is child 0's own RIGHT
#     border. Child 1 carries `border-l-0`, so its fill starts at x 80.
#   * the top and bottom borders run CONTINUOUSLY across the seam: pixel
#     (80, 20) is border, even though child 1 has no left border. A dropped
#     side loses its strip's interior, not the corner pixels where the
#     perpendicular borders reach it.
#   * inner corners go square, outer ones stay rounded, and the last child
#     is forced back to `rounded-r-lg!` whatever its own size said.

_CORNERS = ("tl", "tr", "br", "bl")


@dataclass(frozen=True)
class Join:
    """How one member of a ButtonGroup differs from a standalone button."""
    index: int
    first: bool
    last: bool
    corners: tuple           # the corner names that stay rounded
    borders: tuple           # (top, right, bottom, left) widths in px
    drop: str | None         # the side whose border is gone: "left" | "top"

    @property
    def flags(self) -> int:
        """ImDrawFlags for `corners`, to pass as a rounded fill's `flags`."""
        return corner_flags(self.corners)


def corner_flags(corners) -> int:
    """ImDrawFlags for a set of corner names.

    Resolved on call rather than at import, the way draw._corner_flag_table
    is: the enum lives on the imgui module and naming it at import time would
    make this module depend on an order it has no reason to care about.
    """
    f = imgui.ImDrawFlags_
    tbl = {"tl": f.round_corners_top_left, "tr": f.round_corners_top_right,
           "br": f.round_corners_bottom_right, "bl": f.round_corners_bottom_left}
    out = 0
    for c in corners:
        out |= tbl[c]
    return out or f.round_corners_none


def button_group(rects, orientation: str = "horizontal") -> list:
    """Per-member corner rounding and border handling for a ButtonGroup.

    `rects` is one (x, y, w, h) per button, in group order — only its length
    is used for the flags, but taking the rects keeps this the one place that
    knows a group's layout and lets `button_group_place` be checked against
    it.

    Returns a `Join` per member:

      * `corners` — which corners stay rounded. A horizontal group squares
        the right pair on everything but the last and the left pair on
        everything but the first; a vertical group does the same top/bottom.
      * `borders` — (top, right, bottom, left) widths. The joined side is 0,
        which is what stops the shared border being drawn twice.
      * `drop` — that side's name, for `button_size` and `button`.

    A single-child group is a plain button: all four corners rounded, all four
    borders present. `[&>*:not(:first-child)]` and `[&>*:not(:last-child)]`
    both fail to match, so Radix's own rules say the same.
    """
    if orientation not in ("horizontal", "vertical"):
        raise ValueError("orientation must be horizontal or vertical, "
                         f"not {orientation!r}")
    n = len(rects)
    out = []
    for i in range(n):
        first, last = i == 0, i == n - 1
        if orientation == "horizontal":
            keep = set()
            if first:
                keep |= {"tl", "bl"}
            if last:
                keep |= {"tr", "br"}
            drop = None if first else "left"
            borders = (BORDER_W, BORDER_W, BORDER_W,
                       0.0 if drop else BORDER_W)
        else:
            keep = set()
            if first:
                keep |= {"tl", "tr"}
            if last:
                keep |= {"bl", "br"}
            drop = None if first else "top"
            borders = (0.0 if drop else BORDER_W,
                       BORDER_W, BORDER_W, BORDER_W)
        out.append(Join(index=i, first=first, last=last,
                        corners=tuple(c for c in _CORNERS if c in keep),
                        borders=borders, drop=drop))
    return out


def button_group_place(sizes, x: float, y: float, *,
                       orientation: str = "horizontal") -> list:
    """Tile a group's members from their intrinsic sizes.

    `sizes` is one (w, h) per member, each already computed with the `drop`
    its `Join` carries — so the joined side's missing border is already out of
    the number. The members then abut exactly, which is what the browser does:
    three children of 48.6875 / 47.8125 / 57.5625 make a group of 154.0625,
    the sum, with the seam a single border column.

    `flex w-fit items-stretch`, so the cross axis is the largest member's and
    every member is stretched to it.
    """
    if orientation == "horizontal":
        h = max((s[1] for s in sizes), default=0.0)
        out, cx = [], x
        for w, _ in sizes:
            out.append((cx, y, w, h))
            cx += w
        return out
    w = max((s[0] for s in sizes), default=0.0)
    out, cy = [], y
    for _, hh in sizes:
        out.append((x, cy, w, hh))
        cy += hh
    return out


# --------------------------------------------------------------------------
# chrome
# --------------------------------------------------------------------------

def _u32(col) -> int:
    return imgui.get_color_u32(imgui.ImVec4(*col))


def _dim(col, f: float):
    return (col[0], col[1], col[2], col[3] * f)


def _rr(dl, x, y, w, h, col, radius, flags) -> None:
    """A filled rounded rect with explicit corner flags.

    `draw.fill` rounds all four corners, which a group member must not: its
    inner corners are square. ImGui ignores `rounding` entirely when the flags
    name no corner, so one call covers both.
    """
    if col[3] <= 0.0 or w <= 0.0 or h <= 0.0:
        return
    dl.add_rect_filled(imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h),
                       _u32(col), D.css_radius(radius, w, h), flags)


def _border(dl, x, y, w, h, col, radius, flags, borders) -> None:
    """A 1 px CSS border with one side possibly missing.

    `draw.border` is the right call for all four sides — its placement is
    calibrated, an add_rect stroke of thickness 1 landing wholly inside the
    rect bounds, which is border-box. What it cannot do is leave a side out,
    and a ButtonGroup member needs exactly that.

    So the rect goes up clipped to everything but the dropped side's strip,
    and the 1 px where the two PERPENDICULAR borders reach into that strip is
    filled back in. That is not a nicety: measured, pixel (80, 20) of a group
    whose second child starts at x 80 and has `border-l-0` is still border
    colour, because the top border covers the full box width. Clipping the
    whole column away would leave a 1 px notch in the group's top rule at
    every seam.
    """
    if col[3] <= 0.0:
        return
    bt, br, bb, bl = borders
    drop_left = bl <= 0.0
    drop_top = bt <= 0.0
    if not (drop_left or drop_top):
        dl.add_rect(imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h), _u32(col),
                    rounding=D.css_radius(radius, w, h), thickness=BORDER_W,
                    flags=flags)
        return

    if drop_left:
        lo = imgui.ImVec2(x + BORDER_W, y)
        hi = imgui.ImVec2(x + w, y + h)
        patches = (((x, y), (BORDER_W, bt)),
                   ((x, y + h - bb), (BORDER_W, bb)))
    else:
        lo = imgui.ImVec2(x, y + BORDER_W)
        hi = imgui.ImVec2(x + w, y + h)
        patches = (((x, y), (bl, BORDER_W)),
                   ((x + w - br, y), (br, BORDER_W)))

    dl.push_clip_rect(lo, hi, True)
    dl.add_rect(imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h), _u32(col),
                rounding=D.css_radius(radius, w, h), thickness=BORDER_W,
                flags=flags)
    dl.pop_clip_rect()
    for (px, py), (pw, ph) in patches:
        if pw > 0.0 and ph > 0.0:
            D.fill(dl, px, py, pw, ph, col)


def fill_rect(x, y, w, h, borders) -> tuple:
    """The padding box: where `bg-clip-padding` actually paints the fill.

    Measured, and the single most consequential finding about this component.
    A `default` button at x 20 w 80 paints `primary` into columns 21..98 and
    leaves 20 and 99 showing the page, because every variant carries
    `border border-transparent` AND `bg-clip-padding`. Five of the six
    variants therefore have a 1 px fully transparent ring around their fill.
    """
    bt, br, bb, bl = borders
    return (x + bl, y + bt, w - bl - br, h - bt - bb)


def underline_y(y: float, h: float, font: float) -> float:
    """Where the `link` variant's underline sits, in unsnapped px.

    `underline-offset-4` hangs it 4 px below the ALPHABETIC BASELINE, not
    below the box or the glyph box. The glyph box is `font * FONT_SPAN_EM`
    tall and centred in the button, and the baseline is ASCENT_FRAC down it.

    Measured: a 32 px `link` button at 14 px puts one 1 px rule at
    box-relative y 25, which is what this returns (24.97, snapped to 25).
    """
    span = font * D.FONT_SPAN_EM.get("medium", 1.0)
    glyph_top = y + (h - span) / 2.0
    return glyph_top + ASCENT_FRAC * span + UNDERLINE_OFFSET


def button(dl, x, y, w, h, label, faces, theme, tbl, *, variant="default",
           size="default", hot=0.0, down=0.0, focus_f=0.0, disabled=False,
           join=None, in_group=False, icon=None, icon_side="inline-start",
           haspopup=False, radius=None):
    """shadcn Button — pure chrome, every state passed in.

    `hot`, `down` and `focus_f` are 0..1 so a caller can ease them on the
    kit's own curve; `tbl` is `button_table(theme_name)`. Mirrors
    `draw.slider` and `draw.field`: no imgui widget, no state kept, so the
    gallery can pin it to a spec rect and the diff can measure one cell.

    Three measured laws it keeps, each of which the obvious implementation
    breaks:

    * the fill is the PADDING box, inset by the borders that are present,
      at radius - 1. `bg-clip-padding` with a transparent 1 px border.
    * `hot` drives the fill and `down` drives nothing but a 1 px downward
      nudge. They are separate states: drag off a held button and the tint
      goes back to rest while the nudge stays.
    * `disabled:opacity-50` dims the border and the fill SEPARATELY, because
      `bg-clip-padding` leaves them disjoint. Folding one over the other -
      which is right for the Input - is five levels wrong here.

    Returns the border box actually painted, as (x, y, w, h).
    """
    s = BUTTON_SIZES[size]
    v = tbl[variant]
    r = button_radius(size, in_group=in_group or join is not None) \
        if radius is None else radius
    borders = join.borders if join is not None else (BORDER_W,) * 4
    flags = join.flags if join is not None else corner_flags(_CORNERS)
    dim = DISABLED_OPACITY if disabled else 1.0

    def c(spec, mul=1.0):
        tok, al = spec
        return rgba(tok, al * mul, theme=theme)

    # `active:not-aria-[haspopup]:translate-y-px` - 1 px, downward, and
    # suppressed on a popup trigger so a dropdown does not bounce. It rides
    # `transition-all` like everything else, so it takes `down` rather than a
    # boolean; the browser pixel-snaps each frame, and so does `snap`.
    dy = 0.0 if haspopup else down * NUDGE
    bx, by, bw, bh = D.snap(x, y + dy, w, h)

    # the ring is a box-shadow, so it is a true annulus wholly OUTSIDE the
    # border box - measured at exactly the three columns left of the box
    if focus_f > 0.01 and not disabled:
        D.ring(dl, bx, by, bw, bh, c(v["ring"], focus_f), r, RING_W)

    bcol = mix(c(v["border"]), c(v["focus_border"]), 0.0 if disabled else focus_f)
    bg = mix(c(v["fill"]), c(v["hover_fill"]), 0.0 if disabled else hot)
    if dim < 1.0:
        bcol, bg = _dim(bcol, dim), _dim(bg, dim)

    _border(dl, bx, by, bw, bh, bcol, r, flags, borders)
    fx, fy, fw, fh = fill_rect(bx, by, bw, bh, borders)
    _rr(dl, fx, fy, fw, fh, bg, max(r - BORDER_W, 0.0), flags)

    # --- content -----------------------------------------------------------
    ink = _dim(c(v["ink"]), dim)
    bt, br_, bb, bl = borders
    pad_l = pad_r = s["pad_x"]
    if icon is not None and not s["square"]:
        if icon_side == "inline-start":
            pad_l = s["pad_icon"]
        else:
            pad_r = s["pad_icon"]
    # `justify-center` centres in the CONTENT box, which is the padding box
    # less the paddings - the same thing as centring in the whole box only
    # while the two paddings agree, which with an icon they do not
    cx0 = bx + bl + pad_l
    cw = bw - bl - br_ - pad_l - pad_r

    if s["square"]:
        if icon is not None:
            D.icon(dl, icon, bx + (bw - s["glyph"]) / 2.0,
                   by + (bh - s["glyph"]) / 2.0, s["glyph"], ink)
        elif label:
            D.label(dl, bx, by, label, faces, "medium", s["font"], ink,
                    align="center", box_w=bw, baseline_box=bh)
        return (bx, by, bw, bh)

    tw = D.text_w(label, faces, "medium", s["font"]) if label else 0.0
    run = tw + (s["glyph"] + s["gap"] if icon is not None else 0.0)
    tx = cx0 + (cw - run) / 2.0
    if icon is not None and icon_side == "inline-start":
        D.icon(dl, icon, tx, by + (bh - s["glyph"]) / 2.0, s["glyph"], ink)
        tx += s["glyph"] + s["gap"]
    if label:
        D.label(dl, tx, by, label, faces, "medium", s["font"], ink,
                baseline_box=bh)
        # hover:underline on `link`, and on nothing else. One 1 px rule under
        # the text's own advance width, 4 px below the baseline.
        #
        # One deliberate deviation: `text-decoration-line` is not animatable,
        # so the browser's rule appears instantly while this one fades in on
        # `hot`. The position and the thickness are measured; only the reveal
        # differs, the same trade scroll_area's scrollbar makes.
        if v.get("underline") and hot > 0.01 and not disabled:
            uy = underline_y(by, bh, s["font"])
            ux, uyy, uw, uh = D.snap(tx, uy, tw, UNDERLINE_W)
            D.fill(dl, ux, uyy, uw, uh, _dim(ink, hot))
    if icon is not None and icon_side != "inline-start":
        D.icon(dl, icon, tx + tw + s["gap"], by + (bh - s["glyph"]) / 2.0,
               s["glyph"], ink)
    return (bx, by, bw, bh)


# --------------------------------------------------------------------------
# interactive
# --------------------------------------------------------------------------

def _table_for(ui) -> dict:
    """The theme's variant table, cached across frames.

    Per REVIEW.md per-frame code does no rebuilds, and a `Ui` is thrown away
    every frame (interact.Ui's own note), so the cache lives on `anim.store` —
    the one object the kit already threads from one frame to the next.
    """
    cache = ui.anim.store.setdefault("button_tbl", {})
    t = cache.get(ui.theme_name)
    if t is None:
        t = cache[ui.theme_name] = button_table(ui.theme_name)
    return t


def ui_button(ui, key, x, y, w, h, label, *, variant="default",
              size="default", disabled=False, icon=None,
              icon_side="inline-start", join=None, in_group=False,
              haspopup=False):
    """An interactive Button. Returns the `interact.State` ui.hit gave back.

    The hit target is `ui.hit`, so it is an `invisible_button` carrying
    `##key` — tests/ui_driver.py:43-46 finds controls that way and twenty-two
    test files depend on it. That holds even when `disabled`: the target is
    still submitted (so the driver can still see the control) and the click is
    swallowed instead, which is what `interact.switch` does.

    `focus_f` comes from `imgui.is_item_focused()`, which is ImGui's nav
    focus. That is close to `:focus-visible` but not identical — ImGui has no
    notion of "focused by pointer versus by keyboard", so a control ImGui has
    given nav focus to will show the ring where the browser might not.
    """
    st = ui.hit(key, x, y, w, h)
    focused = imgui.is_item_focused() and not disabled
    focus_f = ui.anim.to(f"{key}:focus", 1.0 if focused else 0.0)
    # `disabled:pointer-events-none`: no hover and no press, so the eased
    # values are driven to 0 rather than read off the widget
    hot = 0.0 if disabled else st.hot
    down = 0.0 if disabled else st.down
    button(ui.dl, x, y, w, h, label, ui.faces, ui.theme, _table_for(ui),
           variant=variant, size=size, hot=hot, down=down, focus_f=focus_f,
           disabled=disabled, join=join, in_group=in_group, icon=icon,
           icon_side=icon_side, haspopup=haspopup)
    if disabled:
        st.clicked = False
        st.hot = st.down = 0.0
    return st


def group_size(items, faces, *, orientation="horizontal", size="default"):
    """A ButtonGroup's intrinsic (w, h), without drawing it.

    So a caller can right-align a group, or hand it to the layout tree,
    without laying it out twice - which is what the dashboard did first, and
    it put a second group at x=0.
    """
    norm = [(it, None) if isinstance(it, str) else it for it in items]
    joins = button_group(norm, orientation)
    sizes = [button_size(size, lab, faces, icon=ic is not None, drop=j.drop)
             for (lab, ic), j in zip(norm, joins)]
    rects = button_group_place(sizes, 0.0, 0.0, orientation=orientation)
    if not rects:
        return 0.0, 0.0
    return (max(r[0] + r[2] for r in rects),
            max(r[1] + r[3] for r in rects))


def ui_button_group(ui, key, x, y, items, *, orientation="horizontal",
                    size="default", variant="outline", disabled=()):
    """A ButtonGroup. Returns (clicked_index_or_None, (x, y, w, h)).

    `items` is one (label, icon_or_None) per member, or a bare label. Each
    member is sized with the `drop` its own `Join` carries, so the group's
    extent is the sum of its members and the seam is a single border — which
    is what the browser does and what `button_group_place` pins.
    """
    norm = [(it, None) if isinstance(it, str) else it for it in items]
    joins = button_group(norm, orientation)
    sizes = [button_size(size, lab, ui.faces, icon=ic is not None,
                         drop=j.drop)
             for (lab, ic), j in zip(norm, joins)]
    rects = button_group_place(sizes, x, y, orientation=orientation)
    # recompute the joins against the real rects, which is what button_group
    # is for - the first pass only needed the count
    joins = button_group(rects, orientation)
    hit = None
    for i, ((lab, ic), j, (rx, ry, rw, rh)) in enumerate(zip(norm, joins, rects)):
        dis = i in disabled
        st = ui_button(ui, f"{key}.{i}", rx, ry, rw, rh, lab, variant=variant,
                       size=size, disabled=dis, icon=ic, join=j, in_group=True)
        if st.clicked:
            hit = i
    if orientation == "horizontal":
        box = (x, y, sum(s[0] for s in sizes),
               max((s[1] for s in sizes), default=0.0))
    else:
        box = (x, y, max((s[0] for s in sizes), default=0.0),
               sum(s[1] for s in sizes))
    return hit, box
