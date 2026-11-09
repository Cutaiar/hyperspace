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
    # Memoised on what the colour RESOLVED to, not on the theme: a theme is
    # a mutable dict, and keying on it (or its id) would go stale the moment
    # one were edited. Resolving the token is one dict lookup; the parse
    # below is what cost ~300 calls a frame.
    try:
        return _RGBA[(c, a)]
    except KeyError:
        pass
    except TypeError:                   # a list: unhashable, so not cached
        return _rgba(c, a)
    if len(_RGBA) > 4096:               # an animated alpha mints new keys
        _RGBA.clear()
    _RGBA[(c, a)] = out = _rgba(c, a)
    return out


_RGBA: dict = {}


def _rgba(c, a):
    if isinstance(c, (tuple, list)):
        v = [x / 255.0 for x in c]
        if len(v) == 3:
            v.append(1.0)
        return (v[0], v[1], v[2], v[3] * a)
    hit = _HEX.get(c)
    if hit is None:
        s = c.lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        hit = _HEX[c] = (int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0,
                         int(s[4:6], 16) / 255.0,
                         int(s[6:8], 16) / 255.0 if len(s) == 8 else 1.0)
    r, g, b, al = hit
    return (r, g, b, al * a)


# A colour's parse, by its string: a draw asks for a few dozen colours ~200
# times a frame (measured in Hyperspace's panel, tools/profile_kit.py), and
# parsing the hex each time was the kit's largest own cost there. Keyed by
# the string alone - never by `a`, which is an eased, continuous value and
# would grow the table without bound.
_HEX: dict = {}


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
# Every number below came out of hyperspace/dkit/dev/probe_react.js against the real
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
# Chromium's own text-selection highlight, which is what a shadcn app gets:
# nothing in the registry declares `::selection`, so the UA default stands.
# Measured on a focused Input with its value selected, in BOTH themes —
# `rgba(0, 65, 198, 0.8)`, which composites to (51,103,209) over white and
# (4,56,162) over #151515. ImGui's own default is a paler, bluer
# (0.26, 0.59, 0.98, 0.35) and reads nothing like it.
SELECTION = (0.0, 65 / 255.0, 198 / 255.0, 0.8)

RING_W = 3.0

# --------------------------------------------------------------------------
# Focus rings for interact.py's own primitives
# --------------------------------------------------------------------------
#
# MEASURED per control on `?probe`, not ported from Button, and the reason to
# measure the second and third is that all three differ. HANDOFF said this
# was "applying a settled model"; it is not one model.
#
#   Button            ring/50 at 3px, border -> ring
#   TabsTrigger       the same, PLUS a 1px solid outline at full `ring`
#   SidebarMenuButton ring at 2px, FULL opacity, and no border change at all
#   TableRow          not focusable at all - a <tr>, no tabindex,
#                     document.activeElement never becomes it
TABS_FOCUS = {
    "ring": ("ring", 0.5),              # focus-visible:ring-[3px] ring-ring/50
    "ring_w": RING_W,
    "focus_border": ("ring", 1.0),      # focus-visible:border-ring
    # `focus-visible:outline-1 outline-ring` - a 1px SOLID outline in
    # full-strength `ring`, immediately outside the border box, so it covers
    # the ring band's innermost pixel. Measured outlineStyle `solid`,
    # outlineWidth 1px, outlineColor oklch(0.708 0 0) in light and
    # oklch(0.556 0 0) in dark, which is `ring` at 1.0 in both. No other
    # control in the kit has an outline as well as a ring.
    "outline": ("ring", 1.0),
    "outline_w": 1.0,
}
TABS_FOCUS_DARK = {
    # `dark:border-input` sorts AFTER `focus-visible:border-ring` in
    # Tailwind's output and wins - exactly the precedence comp_button records
    # for the dark outline Button. Measured oklch(1 0 0 / 0.15), and `input`
    # in dark IS #ffffff26 = white at 0.149.
    "focus_border": ("input", 1.0),
}
SIDEBAR_FOCUS = {
    # `focus-visible:ring-2` with `ring-sidebar-ring`. TWO pixels, at FULL
    # opacity - measured oklch(0.708 0 0) light and oklch(0.556 0 0) dark,
    # with no alpha - where every other ring in the kit is 3px at /50.
    #
    # `sidebar-ring` is not a separate token here because it measured
    # IDENTICAL to `ring` in both themes. That is a measurement, not an
    # assumption: if a future palette splits them this is the line to change.
    "ring": ("ring", 1.0),
    "ring_w": 2.0,
    # and no focus_border: the measured borderTopColor is unchanged by focus
    # (oklch(0.922 0 0) light, oklch(1 0 0 / 0.1) dark - the plain `border`).
}


def tabs_focus(theme_name: str) -> dict:
    """TABS_FOCUS resolved for one theme, like `badge_table`."""
    t = dict(TABS_FOCUS)
    if theme_name == "dark":
        t.update(TABS_FOCUS_DARK)
    return t

SLIDER = {
    "track_h": 4.0,          # Track is `h-1`
    "thumb": 12.0,           # Thumb is `size-3`
    "track": ("muted", 1.0),
    "range": ("primary", 1.0),
    # literal, NOT a token - see the note above
    "thumb_fill": ("#ffffff", 1.0),
    "thumb_border": ("ring", 1.0),
    # The thumb's band, `ring-ring/50`. THREE things turn it on - the thumb
    # carries `hover:ring-3 focus-visible:ring-3 active:ring-3` - which makes
    # it the only control in the kit a bare HOVER rings: measured hovered,
    # `:focus-visible` false and box-shadow `ring/50 0 0 0 3px` painted.
    # The border does NOT swap under focus: `border-ring` is already the rest
    # border, measured oklch(0.708 0 0) at rest and focused alike.
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
    # `focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50`
    # - the same two-part answer every other control gives, and measured
    # identical in BOTH themes (light border oklch(0.708 0 0) = `ring`, dark
    # oklch(0.556 0 0) = `ring`; the dark outline Button's "keeps its border"
    # exception does not reach here). Keyboard only: measured with the pointer
    # held down on the track, `:focus-visible` is false and box-shadow is
    # `none`. draw.switch draws both halves off these two entries.
    "focus_border": ("ring", 1.0),
    "ring": ("ring", 0.5),
}
SWITCH_DARK = {
    "off": ("input", 0.8),              # dark:data-unchecked:bg-input/80
    "thumb_off": ("foreground", 1.0),   # dark:data-unchecked:bg-foreground
    "thumb_on": ("primary-foreground", 1.0),
}

# `after:absolute after:-inset-x-3 after:-inset-y-2` - the stretched hit
# area a Switch and a Checkbox both carry, so a click a few px off a small
# control still lands. The CLASSES say 12 and 8; the browser says 11 and 7,
# because an absolutely positioned ::after is inset from its containing
# block's PADDING box, which sits one border-width inside the edge. Measured
# on ?probe by real clicks AND by the ::after's computed box (38 x 30 around
# a 16px checkbox, 54 x 32.39 around a 32 x 18.39 switch) - the two
# instruments agree. `rect.stretched_hit` applies it.
HIT_STRETCH = (SPACE[3], SPACE[2])

# shadcn Checkbox (radix-ui), measured on ?probe in both themes. One size:
# the registry ships no size variant.
CHECKBOX = {
    "size": 16.0,                         # size-4
    # rounded-[4px] is a LITERAL in the recipe, not a step on RADII - it is
    # neither `sm` nor `md`, so it is spelled here rather than borrowed.
    "radius": 4.0,
    "border_w": 1.0,
    # the indicator is the 14px padding box, and the Lucide `check` inside
    # it is [&>svg]:size-3.5 = 14px at Lucide's own stroke width
    "icon": 14.0,
    "off_bg": ("transparent", 1.0),
    "off_border": ("input", 1.0),
    "on_bg": ("primary", 1.0),            # data-checked:bg-primary
    "on_border": ("primary", 1.0),        # data-checked:border-primary
    "tick": ("primary-foreground", 1.0),  # data-checked:text-primary-foreground
    # MEASURED, and a cascade question rather than a reading: on a CHECKED
    # box `focus-visible:border-ring` beats `data-checked:border-primary`,
    # so a keyboard-focused checked box has a `ring` border around a
    # `primary` fill - in both themes. Keyboard only: a pointer click
    # focuses it and paints neither half.
    "focus_border": ("ring", 1.0),
    "ring": ("ring", 0.5),
    # `disabled:opacity-50` on the WHOLE control - a group opacity, which is
    # not the same as halving each colour where a tick sits over a fill.
    # See draw.checkbox.
    "disabled_opacity": 0.5,
    # No hover chrome: measured byte-identical hovered and at rest, both
    # states, both themes.
    #
    # The label beside it, as the registry's own demo composes it:
    # `flex items-center gap-3` + Label (`text-sm leading-none font-medium`).
    # Measured: the label box is 14 tall at x 28, y 1 - vertically centred
    # on the 16px box - and `peer-disabled:opacity-50` dims it with the box.
    "label_gap": SPACE[3],
    "label_font": 14.0,
    "label_ink": ("foreground", 1.0),
}
CHECKBOX_DARK = {
    "off_bg": ("input", 0.3),             # dark:bg-input/30
}

INPUT = {
    "h": 32.0,               # h-8
    "radius": "lg",          # rounded-lg = 10
    "pad_x": SPACE[2.5],     # px-2.5 = 10
    "font": 14.0,            # md:text-sm
    "bg": ("transparent", 1.0),
    "border": ("input", 1.0),
    # The Input is the ONE control that rings under the POINTER as well.
    # Measured: click into it and `:focus-visible` is true, with the same
    # `ring/50 0 0 0 3px` band and `ring` border a keyboard focus gives -
    # Chromium matches `:focus-visible` on anything that takes text whatever
    # the focus came from. A clicked Button, Switch or SelectTrigger does not.
    # So interact.text_input does NOT gate this on `ui.focus_visible`.
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
    # Measured on a keyboard-focused CLOSED trigger: box-shadow
    # `ring/50 0 0 0 3px` AND border -> `ring`, in both themes. The border
    # half was missing from this table, so draw.field fell back to leaving the
    # border alone and the trigger rang without changing colour.
    #
    # The ring is on the trigger only while it is focused and CLOSED. Opening
    # it with the keyboard moves focus into the listbox, and the trigger's
    # ring goes with it (measured `:focus-visible` false, box-shadow `none`,
    # border back to `input`); Escape brings it back. See interact.select.
    "focus_border": ("ring", 1.0),
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
    # `has-data-[slot=kbd]:pr-1.5`: a tooltip holding a Kbd trims its RIGHT
    # padding to 6. Measured: "Save Changes" (78.547) + S makes a 124.547
    # panel = 12 + 78.547 + gap 8 + 20 + 6.
    "kbd_pad_r": SPACE[1.5],
}

# shadcn Kbd, measured on ?probe (`kbd.*`) in both themes. A plain <kbd>:
# no border, no shadow, no interaction (`pointer-events-none`).
KBD = {
    "h": 20.0,                    # h-5
    "min_w": 20.0,                # min-w-5: one glyph is a 20 x 20 square
    "pad_x": SPACE[1],            # px-1. Width = max(min_w, text + 2 pad_x):
    #                               "Ctrl" measured 29.203 = 21.203 + 8
    "radius": "sm",               # rounded-sm = 6, measured
    "font": 12.0,                 # text-xs font-medium
    "bg": ("muted", 1.0),
    "ink": ("muted-foreground", 1.0),
    # KbdGroup: `inline-flex items-center gap-1`. Anything between the keys
    # (the demo's "+") is plain text at the PARENT's size - and in MONOSPACE:
    # KbdGroup renders a <kbd>, the UA stylesheet gives <kbd> `font-family:
    # monospace`, and unlike Kbd the group never resets it to font-sans.
    # Measured: the "+" is 9.609 wide at 16px = 0.6em, the advance of every
    # common UA monospace (Liberation Mono, SF Mono, Menlo). The kit has no
    # mono face, so a separator ADVANCES by this and its glyph is centred in
    # the slot - the layout is the browser's, the glyph shape is Geist's.
    "group_gap": SPACE[1],
    "group_sep_em": 0.6,
    # Inside a Tooltip the recipe restyles it from the ancestor's data-slot:
    # in-data-[slot=tooltip-content]:bg-background/20 text-background, /10
    # in dark - measured oklab(1 0 0 / .2) light, background at .1 dark.
    "tip_bg": ("background", 0.2),
    "tip_ink": ("background", 1.0),
    # the registry demo puts it `gap-2` after the tooltip's text, and the
    # panel grows to hold it: 32 tall (20 + py-1.5 twice) where text alone
    # is 28, and trims its right padding - see TOOLTIP["kbd_pad_r"].
    "tip_gap": SPACE[2],
}
KBD_DARK = {
    "tip_bg": ("background", 0.1),
}

# shadow-md, which the Select's popover carries on top of its 1px ring.
SHADOW_MD = ((0.0, 4.0, 6.0, -1.0, 0.10), (0.0, 2.0, 4.0, -2.0, 0.10))
# shadow-lg, measured on a Sheet panel: `0 10px 15px -3px rgba(0,0,0,.1),
# 0 4px 6px -4px rgba(0,0,0,.1)`. A Dialog does NOT carry one - it has a 1px
# ring instead, which is the kind of thing only a dump tells you.
SHADOW_LG = ((0.0, 10.0, 15.0, -3.0, 0.10), (0.0, 4.0, 6.0, -4.0, 0.10))


def _themed(base: dict, dark: dict, theme_name: str) -> dict:
    t = dict(base)
    if theme_name == "dark":
        t.update(dark)
    return t


def slider_table(theme_name: str) -> dict:
    return dict(SLIDER)                 # no per-theme overrides: all tokens


def switch_table(theme_name: str) -> dict:
    return _themed(SWITCH, SWITCH_DARK, theme_name)


def checkbox_table(theme_name: str) -> dict:
    return _themed(CHECKBOX, CHECKBOX_DARK, theme_name)


def kbd_table(theme_name: str) -> dict:
    return _themed(KBD, KBD_DARK, theme_name)


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
    # The scrollbar lives inside the VIEWPORT, not inside the root box, so a
    # bordered region insets it by the border. Measured on a 320x200 root
    # with `rounded-lg border`: viewport at (1,1) 318x198, scrollbar at
    # (309,1) 10x198, thumb at (311,2) 7 wide. The kit drew the bar against
    # the ROOT's edge, which put the thumb on top of the border and one
    # pixel further out than the browser's at every point.
    "border": 1.0,
    # How far one unit of `io.mouse_wheel` scrolls.
    #
    # ImGui's own answer is `5 * font_size`, about 90 px at this type scale.
    # On macOS GLFW hands it `scrollingDeltaY * 0.1` for a precise trackpad,
    # and `scrollingDeltaY` is points of FINGER TRAVEL - so a 100 pt swipe
    # arrives as 10 units and ImGui moves the page 900 px. The browser moves
    # it 100: a trackpad scrolls 1:1 with the finger. That is the whole of
    # why this felt nine times too fast.
    #
    # 10 px per unit puts a precise trackpad back at 1:1. A discrete wheel
    # notch (one unit) then moves 10 px where a browser moves ~100, so
    # `notch_px` scales a unit-sized jump back up - a flick that arrives as
    # one big delta is still one gesture, not a hundred notches.
    # 10 px per unit of raw wheel, and this one is measured rather than
    # chosen. `dashboard.py --wheel-probe` on a MacBook trackpad:
    #
    #   raw    -0.2 -0.4 -0.4 -0.6 -0.1 -0.5 ... -1.5 -0.9 -1.0 -0.2 ...
    #
    # EVERY delta is a multiple of 0.1. That quantum is the whole proof:
    # AppKit's `scrollingDeltaY` is an integer count of points and GLFW
    # multiplies it by 0.1, which is the factor I had claimed from memory
    # for two commits without being able to check it. So one unit is TEN
    # POINTS of finger travel, and 1:1 with a browser - which applies
    # trackpad deltas unscaled and unsmoothed - is 10 px per unit.
    #
    # It also fixes the skipping. At 1 px per unit a 0.1 delta scrolls a
    # tenth of a pixel; glyphs snap to whole pixels, so lines cross a
    # boundary at different moments and the text shears as it moves. At 10
    # every step is exact - 0.1 x 10 = 1 px - and since every delta is a
    # multiple of 0.1, every scroll step lands on a whole pixel. No other
    # value has that property.
    #
    # The same probe answered the inertia question: the tail of a flick
    # reads 1.2, 1.0, 0.8, 0.6, 0.5, 0.3, 0.3, 0.1, 0.1 at 17 ms intervals.
    # That decay is AppKit's momentum phase arriving through GLFW
    # untouched, so inertial scrolling needs nothing built - only this
    # factor, which was scaling it wrong along with everything else.
    "px_per_unit": 10.0,
    # A notched wheel, which only ever sends whole units: a browser gives
    # one of those about 120 px a tick. Note the probe shows a TRACKPAD
    # emitting exact 1.0 deltas too (six of them in one run), which is why
    # the precise-device flag is sticky rather than per event.
    "notch_px": 120.0,
}
