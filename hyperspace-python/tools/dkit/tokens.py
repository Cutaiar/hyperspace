"""shadcn design tokens, as data.

The light palette is Tailwind's neutral ramp exactly (verified against the
computed styles of prototypes/dashboard), plus one red. Every value is
achromatic except `destructive`, so there is no colour-management risk in
moving them to ImGui: an sRGB byte triple is the whole story.

Colours are "#rrggbb" or "#rrggbbaa". `rgba()` returns the 0..1 float tuple
ImGui wants, extending the parser idea in hyperspace/ui_pad_lab.py:30-52.
"""

from __future__ import annotations

# --- light ----------------------------------------------------------------
LIGHT = {
    "background": "#ffffff",
    "foreground": "#0a0a0a",
    "card": "#ffffff",
    "popover": "#ffffff",
    "popover-foreground": "#0a0a0a",
    "primary": "#171717",
    "primary-foreground": "#fafafa",
    "secondary": "#f5f5f5",
    "secondary-foreground": "#171717",
    "muted": "#f5f5f5",
    "muted-foreground": "#737373",
    "accent": "#f5f5f5",
    "border": "#e5e5e5",
    "input": "#e5e5e5",
    "ring": "#a1a1a1",
    "destructive": "#e7000b",
    "sidebar": "#fafafa",
    "transparent": "#00000000",
}

# --- dark (the one Hyperspace will actually wear) -------------------------
DARK = {
    "background": "#0a0a0a",
    "foreground": "#fafafa",
    "card": "#171717",
    "popover": "#171717",              # oklch(0.205 0 0)
    "popover-foreground": "#fafafa",
    "primary": "#e5e5e5",
    "primary-foreground": "#171717",
    "secondary": "#262626",
    "secondary-foreground": "#fafafa",
    "muted": "#262626",
    "muted-foreground": "#a1a1a1",
    "accent": "#262626",
    "border": "#ffffff1a",
    "input": "#ffffff26",
    "ring": "#737373",
    "destructive": "#ff6467",
    "sidebar": "#171717",
    "transparent": "#00000000",
}

# The oklab lightness behind the achromatic tokens, for anything that has to
# interpolate in oklab (the card gradient). Keeping L rather than the hex
# avoids a round trip back out of sRGB.
LIGHT_L = {"primary": 0.205, "card": 1.0}
DARK_L = {"primary": 0.922, "card": 0.205}


# --------------------------------------------------------------------------
# spacing
# --------------------------------------------------------------------------
#
# Tailwind's 4px base, which is what shadcn spaces everything on. This exists
# because the dashboard was written without it and read cramped: rows on a
# 27px pitch carrying 24px controls, a 3px gutter, and a card header whose
# title and description were 20px apart where shadcn puts them 4.
#
# That is the same failure box.py was written to stop one layer down - "the
# answer is not better constants; it is not writing constants" - so the
# numbers below are measured off a real Card + Field on the ?probe route
# rather than chosen:
#
#     card padding            16    (px-4 py-4)
#     title -> description     4    (gap-1)
#     header -> content       16    (gap-4)
#     label -> its control     8    (gap-2)
#
# Use SPACE[n], and reach for box.flex(direction="column", gap=...) rather
# than writing `i * pitch`: the kit has had that since flex landed.
# Half steps included because shadcn leans on them for control padding:
# px-2.5 is the Input's 10 and py-1.5 is the Tooltip's 6. Without them those
# read as arbitrary numbers instead of as points on one scale.
SPACE = {0: 0.0, 0.5: 2.0, 1: 4.0, 1.5: 6.0, 2: 8.0, 2.5: 10.0, 3: 12.0,
         3.5: 14.0, 4: 16.0, 5: 20.0, 6: 24.0, 8: 32.0, 10: 40.0, 12: 48.0}


def sp(n):
    """A point on the spacing scale. `sp(2.5)` is Tailwind's px-2.5 = 10."""
    return SPACE[n]

# The Card's own measured rhythm, so a header is not re-derived per card.
CARD_PAD = SPACE[4]          # 16, all four sides
CARD_TITLE_GAP = SPACE[1]    # 4, title baseline box -> description
CARD_HEAD_GAP = SPACE[4]     # 16, description -> first content row
CARD_TITLE_H = 22.0          # text-base, line-height 22
CARD_DESC_H = 20.0           # text-sm, line-height 20


def card_body_y(card_y: float, *, description: bool = True) -> float:
    """Where a Card's content starts, measured rather than guessed."""
    y = card_y + CARD_PAD + CARD_TITLE_H
    if description:
        y += CARD_TITLE_GAP + CARD_DESC_H
    return y + CARD_HEAD_GAP


# --radius: 0.625rem = 10px, and the scale shadcn derives from it.
RADIUS = 10.0
RADII = {
    "sm": RADIUS - 4,   # 6
    "md": RADIUS - 2,   # 8
    "lg": RADIUS,       # 10
    "xl": RADIUS + 4,   # 14  (cards)
    "4xl": RADIUS + 16,  # 26  (badges; clamps to h/2 on short boxes)
}


def rgba(c: str | tuple, a: float = 1.0, theme: dict | None = None) -> tuple:
    """"#rrggbb" | "#rrggbbaa" | a token name | (r,g,b[,a]) 0-255 -> floats 0-1.

    `a` multiplies whatever alpha the colour already carries, so
    rgba("destructive", 0.10) is Tailwind's `bg-destructive/10`.
    """
    if theme and isinstance(c, str) and c in theme:
        c = theme[c]
    if isinstance(c, (tuple, list)):
        v = [x / 255.0 for x in c]
        if len(v) == 3:
            v.append(1.0)
        return (v[0], v[1], v[2], v[3] * a)
    s = c.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    al = int(s[6:8], 16) / 255.0 if len(s) == 8 else 1.0
    return (r, g, b, al * a)


# Per-variant chrome for Badge, read off src/components/ui/badge.tsx.
# Every variant carries a 1px border; only `outline` makes it visible.
BADGE = {
    "default": {"fill": ("primary", 1.0), "border": ("transparent", 1.0)},
    "secondary": {"fill": ("secondary", 1.0), "border": ("transparent", 1.0)},
    "destructive": {"fill": ("destructive", 0.10), "border": ("transparent", 1.0)},
    "outline": {"fill": ("transparent", 1.0), "border": ("border", 1.0)},
}

# Not every variant is a pure token swap: the destructive badge carries
# `bg-destructive/10 dark:bg-destructive/20`, so the alpha itself is themed.
BADGE_DARK = {
    "destructive": {"fill": ("destructive", 0.20), "border": ("transparent", 1.0)},
}


def badge_table(theme_name: str) -> dict:
    t = dict(BADGE)
    if theme_name == "dark":
        t.update(BADGE_DARK)
    return t


# --------------------------------------------------------------------------
# Tier 1 components, as measured
# --------------------------------------------------------------------------
#
# Every number below came out of tools/dkit/probe_react.js against the real
# components on the ?probe route - not out of reading the Tailwind classes.
# Four of them are things a reading gets wrong:
#
#   * the switch is 18.390625 px tall. The class says `h-[18.4px]`; Chromium
#     lays out on a 1/64 px grid, so 18.4 becomes 1177/64.
#   * the slider thumb is `bg-white` - a LITERAL, not a token. It stays pure
#     white on Hyperspace's #0a0a0a ground. Every other fill in the kit
#     swaps with the theme; this one must not.
#   * the switch thumb INVERTS in dark: `foreground` when off,
#     `primary-foreground` when on. In light both states are white.
#   * the select trigger has no hover tint in light at all, and does have one
#     in dark (`input/30` -> `input/50`).
#
# Where a value is (token, alpha) the alpha MULTIPLIES whatever the token
# already carries, which is how `bg-input/80` works on a dark `input` that is
# itself #ffffff26. See rgba().

# shadcn's focus/hover ring: `ring-3` is a 3px box-shadow spread, outside the
# border box, and CSS clips an outer shadow so it never paints under the
# element. See draw.ring.
RING_W = 3.0

SLIDER = {
    "track_h": 4.0,          # Track is `h-1`
    "thumb": 12.0,           # Thumb is `size-3`
    "track": ("muted", 1.0),
    "range": ("primary", 1.0),
    # literal, NOT a token - see the note above
    "thumb_fill": ("#ffffff", 1.0),
    "thumb_border": ("ring", 1.0),
    "ring": ("ring", 0.5),
    "disabled_opacity": 0.5,
}

# (w, h, thumb) per size. The fractional height is not a typo.
SWITCH_SIZES = {
    "default": (32.0, 18.390625, 16.0),
    "sm": (24.0, 14.0, 12.0),
}
SWITCH = {
    "off": ("input", 1.0),
    "on": ("primary", 1.0),
    "thumb_off": ("background", 1.0),
    "thumb_on": ("background", 1.0),
    "border": ("transparent", 1.0),
}
SWITCH_DARK = {
    "off": ("input", 0.8),              # dark:data-unchecked:bg-input/80
    "thumb_off": ("foreground", 1.0),   # dark:data-unchecked:bg-foreground
    "thumb_on": ("primary-foreground", 1.0),
}

INPUT = {
    "h": 32.0,               # h-8
    "radius": "lg",          # rounded-lg = 10
    "pad_x": SPACE[2.5],     # px-2.5 = 10
    "font": 14.0,            # md:text-sm
    "bg": ("transparent", 1.0),
    "border": ("input", 1.0),
    "focus_border": ("ring", 1.0),
    "ring": ("ring", 0.5),
    "invalid_border": ("destructive", 1.0),
    "invalid_ring": ("destructive", 0.2),
    "disabled_bg": ("input", 0.5),
    "disabled_opacity": 0.5,
    "placeholder": ("muted-foreground", 1.0),
}
INPUT_DARK = {
    "bg": ("input", 0.3),               # dark:bg-input/30
    "invalid_border": ("destructive", 0.5),
    "invalid_ring": ("destructive", 0.4),
    "disabled_bg": ("input", 0.8),
}

# The trigger's radius is NOT constant across sizes: default is rounded-lg
# (10) and sm is rounded-md (8).
SELECT_SIZES = {"default": (32.0, "lg"), "sm": (28.0, "md")}
SELECT = {
    "pad_l": SPACE[2.5],     # px-2.5 on the left
    "pad_r": SPACE[2],       # pr-2, tighter: the chevron needs less room
    "chevron": 16.0,
    "font": 14.0,
    "bg": ("transparent", 1.0),
    "hover_bg": ("transparent", 1.0),   # light has no hover tint
    "border": ("input", 1.0),
    "ring": ("ring", 0.5),
}
SELECT_DARK = {
    "bg": ("input", 0.3),
    "hover_bg": ("input", 0.5),
}

TOOLTIP = {
    "radius": "md",          # rounded-md = 8
    "pad_x": SPACE[3],       # px-3 = 12
    "pad_y": SPACE[1.5],     # py-1.5 = 6
    "font": 12.0,            # text-xs
    "bg": ("foreground", 1.0),
    "fg": ("background", 1.0),
    "arrow": 10.0,           # size-2.5, rotated 45 -> a 14.142 bbox
    "arrow_radius": 2.0,
    "arrow_dy": 2.0,         # translate-y-[calc(-50% - 2px)]
    "side_offset": 0.0,
    # Radix reserves the arrow's full DECLARED size between the panel and the
    # anchor, so panel bottom = anchor top - arrow_space - side_offset.
    # Measured: a 0x0 anchor at y 958 put the panel's bottom at 948. The
    # rendered diamond only uses 5.071 px of that, so there is a ~4.9 px gap
    # below the tip - which is Radix's doing, not a mistake to correct.
    "arrow_space": 10.0,
}

# shadow-md, which the Select's popover carries on top of its 1px ring.
SHADOW_MD = ((0.0, 4.0, 6.0, -1.0, 0.10), (0.0, 2.0, 4.0, -2.0, 0.10))


def _themed(base: dict, dark: dict, theme_name: str) -> dict:
    t = dict(base)
    if theme_name == "dark":
        t.update(dark)
    return t


def slider_table(theme_name: str) -> dict:
    return dict(SLIDER)                 # no per-theme overrides: all tokens


def switch_table(theme_name: str) -> dict:
    return _themed(SWITCH, SWITCH_DARK, theme_name)


def input_table(theme_name: str) -> dict:
    return _themed(INPUT, INPUT_DARK, theme_name)


def select_table(theme_name: str) -> dict:
    return _themed(SELECT, SELECT_DARK, theme_name)


def tooltip_table(theme_name: str) -> dict:
    return dict(TOOLTIP)


# --------------------------------------------------------------------------
# ScrollArea, as measured
# --------------------------------------------------------------------------
#
# Radix's scrollbar OVERLAYS its viewport rather than taking layout space,
# which is the whole reason to draw it ourselves: ImGui's own scrollbar is a
# column of the child window and is always there. Measured on ?probe at
# several content ratios:
#
#     scrollbar       10 wide (w-2.5), right-aligned inside the border
#     thumb            7 wide, 2 in from the scrollbar's left edge
#                      (a 1px transparent border-l, then 1px of padding)
#     track            the scrollbar less 1px of padding at each end
#     thumb height     max(18, viewport / content * track)
#     thumb travel     track_y + frac * (track - thumb)
#
# The 18 is a floor and not a rounding artifact: at a viewport of 198 the
# ideal thumb goes 97.0, 32.3, 12.9, 4.9, 1.3 as the content grows, and the
# rendered one stops at 18 and stays there.
SCROLL = {
    "bar_w": SPACE[2.5],       # w-2.5 = 10
    "thumb_w": 7.0,
    "thumb_inset": 2.0,        # border-l 1 + p-px 1
    "track_inset": 1.0,        # p-px, top and bottom
    "thumb_min": 18.0,
    "thumb": ("border", 1.0),  # bg-border; measured identical when hovered
    "hide_delay": 0.6,         # Radix's scrollHideDelay, for type="hover"
}
