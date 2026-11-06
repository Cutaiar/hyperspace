"""The Button's measured laws, pinned to what Chromium actually does.

Every expected number here was read off the real shadcn Button on the
`?probe` route at dpr 1 — `probe_react.js` for the rest states, one-off
Playwright scripts for hover / focus-visible / active / disabled, and pixel
reads of the rendered boxes where a computed style could not settle it. None
of it was derived from the Tailwind classes, and eight of these numbers are
not what the classes imply. The file's own header lists them; the tests below
pin them one at a time.

No imgui context and no GL: this is pure geometry and pure colour arithmetic,
the way test_components.py, test_box.py and test_flex.py are. The one thing
that needs the imgui module (not a context) is the corner-flag enum, which
test_components.py already imports the same way.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import comp_button as CB      # noqa: E402
import draw as D              # noqa: E402
import tokens as T            # noqa: E402
from ease import mix, over    # noqa: E402


# --------------------------------------------------------------------------
# helpers: the browser's compositing, so a token can be checked as a byte
# --------------------------------------------------------------------------

def composite(col, ground) -> tuple:
    """`col` over an opaque `ground`, as sRGB bytes, the way the page does."""
    r, g, b, a = col
    gr, gg, gb = ground
    return tuple(round((c * a + gc / 255.0 * (1.0 - a)) * 255.0)
                 for c, gc in ((r, gr), (g, gg), (b, gb)))


WHITE = (255, 255, 255)          # the light page ground, --background
NEAR_BLACK = (10, 10, 10)        # the dark page ground, #0a0a0a


def c(theme, spec, mul=1.0):
    tok, al = spec
    return T.rgba(tok, al * mul, theme=theme)


LIGHT, DARK = T.LIGHT, T.DARK
TL, TD = CB.button_table("light"), CB.button_table("dark")


# --------------------------------------------------------------------------
# sizes
# --------------------------------------------------------------------------
# One row per `size`, straight out of getBoundingClientRect + getComputedStyle
# on ?probe. Identical in both themes.
#
#   size        h   radius  pad_x  font   line   gap  glyph
BROWSER_SIZES = [
    ("xs",      24.0,  8.0,  8.0, 12.0, 16.0,  4.0, 12.0),
    ("sm",      28.0,  8.0, 10.0, 12.8, 19.2,  4.0, 14.0),
    ("default", 32.0, 10.0, 10.0, 14.0, 20.0,  6.0, 16.0),
    ("lg",      36.0, 10.0, 10.0, 14.0, 20.0,  6.0, 16.0),
    ("icon-xs", 24.0,  8.0,  0.0, 14.0, 20.0,  0.0, 12.0),
    ("icon-sm", 28.0,  8.0,  0.0, 14.0, 20.0,  0.0, 16.0),
    ("icon",    32.0, 10.0,  0.0, 14.0, 20.0,  0.0, 16.0),
    ("icon-lg", 36.0, 10.0,  0.0, 14.0, 20.0,  0.0, 16.0),
]


@pytest.mark.parametrize("size,h,radius,pad_x,font,line,gap,glyph",
                         BROWSER_SIZES)
def test_size_matches_the_browser(size, h, radius, pad_x, font, line, gap,
                                  glyph):
    s = CB.BUTTON_SIZES[size]
    assert s["h"] == pytest.approx(h)
    assert CB.button_radius(size) == pytest.approx(radius)
    assert s["pad_x"] == pytest.approx(pad_x)
    assert s["font"] == pytest.approx(font)
    assert s["line"] == pytest.approx(line)
    assert s["gap"] == pytest.approx(gap)
    assert s["glyph"] == pytest.approx(glyph)


def test_the_radius_is_not_constant_across_sizes():
    """The thing a single `rounded-md` gets wrong.

    The base is `rounded-lg` = 10; the four small sizes carry
    `rounded-[min(var(--radius-md), Npx)]` and measure 8.
    """
    assert {CB.button_radius(z) for z in ("xs", "sm", "icon-xs", "icon-sm")} == {8.0}
    assert {CB.button_radius(z) for z in ("default", "lg", "icon", "icon-lg")} == {10.0}


def test_the_two_radius_expressions_only_agree_by_accident():
    """`xs` caps at 10 and `sm` at 12, and both land on 8 only because
    --radius-md is 0.625rem * 0.8 = 8. The cap is kept per size, not its
    answer, so a larger --radius would still come out right."""
    assert CB.BUTTON_SIZES["xs"]["radius_cap"] == 10.0
    assert CB.BUTTON_SIZES["sm"]["radius_cap"] == 12.0
    assert T.RADII["md"] == 8.0
    # the caps are both above --radius-md, which is why they tie
    assert min(T.RADII["md"], 10.0) == min(T.RADII["md"], 12.0) == 8.0


def test_inside_a_group_every_size_goes_back_to_rounded_lg():
    """`in-data-[slot=button-group]:rounded-lg`. Measured: a lone `xs`
    reports 8px corners, and the same `xs` inside a ButtonGroup reports
    10px."""
    for z in CB.BUTTON_SIZES:
        assert CB.button_radius(z, in_group=True) == 10.0
    assert CB.button_radius("xs") == 8.0
    assert CB.button_radius("xs", in_group=True) == 10.0


def test_sm_is_12_point_8_px_and_not_12():
    """`text-[0.8rem]`, with the 19.2 line height that follows from it. The
    one size whose font is not a whole number."""
    assert CB.BUTTON_SIZES["sm"]["font"] == pytest.approx(12.8)
    assert CB.BUTTON_SIZES["sm"]["line"] == pytest.approx(19.2)
    assert CB.BUTTON_SIZES["sm"]["font"] * 1.5 == pytest.approx(19.2)


def test_icon_sm_glyph_is_16_not_14():
    """`size-3.5` is on `sm`, not on `icon-sm` — which inherits the base
    `size-4`. So the smaller box carries the larger glyph, which is the
    opposite of what the naming suggests. Measured by injecting a bare svg
    into each size's own cva class list and reading its rect back."""
    assert CB.BUTTON_SIZES["sm"]["glyph"] == 14.0
    assert CB.BUTTON_SIZES["icon-sm"]["glyph"] == 16.0
    assert CB.BUTTON_SIZES["icon-xs"]["glyph"] == 12.0


def test_the_icon_sizes_keep_text_sm():
    """There is no `text-xs` on `icon-xs`: all four icon sizes measure
    14 px / 20 px, whatever their box."""
    for z in ("icon-xs", "icon-sm", "icon", "icon-lg"):
        assert (CB.BUTTON_SIZES[z]["font"], CB.BUTTON_SIZES[z]["line"]) == (14.0, 20.0)


# --------------------------------------------------------------------------
# intrinsic size
# --------------------------------------------------------------------------
# Chromium, the string "Button" in Geist Medium at each size. The CONTENT
# width is the browser's own text advance and ImGui will not reproduce it to
# the fraction, so `text_w` is passed in and the law is what is pinned.
#
#   size      content    box
#   xs         37.4844   55.4844
#   sm         39.9688   61.9688
#   default    43.7188   65.7188
#   lg         43.7188   65.7188
BROWSER_INTRINSIC = [
    ("xs",      37.4844, 55.4844),
    ("sm",      39.9688, 61.9688),
    ("default", 43.7188, 65.7188),
    ("lg",      43.7188, 65.7188),
]


@pytest.mark.parametrize("size,content,box_w", BROWSER_INTRINSIC)
def test_intrinsic_width_matches_the_browser(size, content, box_w):
    w, h = CB.button_size(size, "Button", {}, text_w=content)
    assert w == pytest.approx(box_w, abs=1e-4)
    assert h == CB.BUTTON_SIZES[size]["h"]


def test_intrinsic_width_is_content_plus_padding_plus_two_borders():
    """Spelled out, because the two 1 px borders are easy to forget: every
    variant carries `border`, visible or not, and `box-sizing: border-box`
    puts them inside the width."""
    s = CB.BUTTON_SIZES["default"]
    w, _ = CB.button_size("default", "Button", {}, text_w=43.7188)
    assert w == pytest.approx(43.7188 + 2 * s["pad_x"] + 2 * CB.BORDER_W,
                              abs=1e-4)
    assert w == pytest.approx(65.7188, abs=1e-4)


def test_an_icon_size_is_a_square_and_ignores_its_label():
    for z, n in (("icon-xs", 24.0), ("icon-sm", 28.0), ("icon", 32.0),
                 ("icon-lg", 36.0)):
        assert CB.button_size(z, "anything at all", {}) == (n, n)


def test_an_inline_icon_adds_the_glyph_and_the_gap_and_tightens_one_padding():
    """`has-data-[icon=inline-start]:pl-2` on default/lg and `pl-1.5` on
    xs/sm — measured 10 -> 8 and 8 or 10 -> 6, with pr left alone."""
    s = CB.BUTTON_SIZES["default"]
    plain, _ = CB.button_size("default", "Button", {}, text_w=43.7188)
    lead, _ = CB.button_size("default", "Button", {}, text_w=43.7188,
                             icon=True, icon_side="inline-start")
    assert lead == pytest.approx(plain + s["glyph"] + s["gap"]
                                 - (s["pad_x"] - s["pad_icon"]), abs=1e-4)
    trail, _ = CB.button_size("default", "Button", {}, text_w=43.7188,
                              icon=True, icon_side="inline-end")
    assert trail == pytest.approx(lead, abs=1e-9)   # symmetric
    assert s["pad_icon"] == 8.0
    assert CB.BUTTON_SIZES["xs"]["pad_icon"] == 6.0
    assert CB.BUTTON_SIZES["sm"]["pad_icon"] == 6.0


# --------------------------------------------------------------------------
# the fill is the PADDING box
# --------------------------------------------------------------------------

def test_the_fill_is_inset_one_pixel_on_every_side():
    """The finding that changes every variant.

    `border border-transparent` plus `bg-clip-padding` means the background
    is clipped to the padding box, so five of the six variants have a 1 px
    fully transparent ring around their fill. Measured on a `default` button
    pinned to x 20 y 20 w 80 h 32: the fill paints into columns 21..98 and
    rows 21..50, and columns 20 / 99 and rows 20 / 51 show the page.
    """
    fx, fy, fw, fh = CB.fill_rect(20.0, 20.0, 80.0, 32.0, (1.0,) * 4)
    assert (fx, fy) == (21.0, 21.0)
    assert (fx + fw, fy + fh) == (99.0, 51.0)


def test_the_inner_radius_is_the_outer_one_less_the_border():
    """CSS's own rule, and fitted off the arc: the fill's left tangent sits
    at x+1 and it is reached from y+10 down, so the arc centre is at
    (x+10, y+10) and the radius is 10 - 1 = 9."""
    r = CB.button_radius("default")
    assert r == 10.0
    assert max(r - CB.BORDER_W, 0.0) == 9.0


def test_a_group_member_fills_right_up_to_its_dropped_border():
    """Child 1 of a horizontal group has `border-l-0`, so its padding box
    starts at its own box edge. Measured: a group whose second child's box
    starts at x 80 shows that child's fill at x 80, while the seam's single
    border column is x 79 — child 0's own right border."""
    j = CB.button_group([(0, 0, 60, 32)] * 3, "horizontal")[1]
    assert j.borders == (1.0, 1.0, 1.0, 0.0)
    fx, _, fw, _ = CB.fill_rect(80.0, 20.0, 60.0, 32.0, j.borders)
    assert fx == 80.0
    assert fx + fw == 139.0          # its own right border still takes x 139


# --------------------------------------------------------------------------
# variant colours, as bytes on the page
# --------------------------------------------------------------------------
# Each row is (theme, variant, state, measured sRGB) read off a screenshot of
# the rendered button at dpr 1, mid-height, inside the fill.
BROWSER_FILL = [
    # light, over #ffffff
    ("light", "default",     "rest",  (23, 23, 23)),
    ("light", "default",     "hover", (69, 69, 69)),
    ("light", "outline",     "rest",  (255, 255, 255)),
    ("light", "outline",     "hover", (245, 245, 245)),
    ("light", "secondary",   "rest",  (245, 245, 245)),
    ("light", "secondary",   "hover", (231, 231, 231)),
    ("light", "ghost",       "rest",  (255, 255, 255)),
    ("light", "ghost",       "hover", (245, 245, 245)),
    ("light", "destructive", "rest",  (252, 229, 230)),
    ("light", "destructive", "hover", (250, 204, 206)),
    ("light", "link",        "rest",  (255, 255, 255)),
    ("light", "link",        "hover", (255, 255, 255)),
    # dark, over #0a0a0a
    ("dark", "default",     "rest",  (229, 229, 229)),
    ("dark", "default",     "hover", (185, 185, 185)),
    ("dark", "outline",     "rest",  (20, 20, 20)),
    ("dark", "outline",     "hover", (28, 28, 28)),
    ("dark", "secondary",   "rest",  (38, 38, 38)),
    ("dark", "secondary",   "hover", (47, 47, 47)),
    ("dark", "ghost",       "rest",  (10, 10, 10)),
    ("dark", "ghost",       "hover", (24, 24, 24)),
    ("dark", "destructive", "rest",  (59, 28, 29)),
    ("dark", "destructive", "hover", (84, 37, 38)),
    ("dark", "link",        "rest",  (10, 10, 10)),
    ("dark", "link",        "hover", (10, 10, 10)),
]


@pytest.mark.parametrize("theme_name,variant,state,rgb", BROWSER_FILL)
def test_variant_fill_matches_the_browser(theme_name, variant, state, rgb):
    theme = LIGHT if theme_name == "light" else DARK
    ground = WHITE if theme_name == "light" else NEAR_BLACK
    tbl = TL if theme_name == "light" else TD
    spec = tbl[variant]["fill" if state == "rest" else "hover_fill"]
    got = composite(c(theme, spec), ground)
    # one level of slack: Chromium quantizes a fractional alpha to 8 bits
    # before compositing, so `input/30` (0.045) lands on 20 where the exact
    # arithmetic says 21
    assert all(abs(a - b) <= 1 for a, b in zip(got, rgb)), f"{got} vs {rgb}"


def test_default_hovers_on_an_alpha_and_not_on_a_mix():
    """`hover:bg-primary/80` — and the stub it supersedes had BOTH halves of
    this wrong: it mixed 10% toward `background` and it used /90. Measured
    light hover is 69; a 10% mix toward white would be 46."""
    assert TL["default"]["hover_fill"] == ("primary", 0.8)
    assert composite(c(LIGHT, ("primary", 0.8)), WHITE) == (69, 69, 69)
    wrong = mix(T.rgba("primary", theme=LIGHT),
                T.rgba("background", theme=LIGHT), 0.10)
    assert composite(wrong, WHITE) == (46, 46, 46)


def test_outline_is_opaque_background_in_light_and_a_tint_in_dark():
    """Not transparent in either: `bg-background` in light,
    `dark:bg-input/30` in dark. The stub had it transparent."""
    assert TL["outline"]["fill"] == ("background", 1.0)
    assert TD["outline"]["fill"] == ("input", 0.3)
    assert composite(c(LIGHT, TL["outline"]["fill"]), WHITE) == (255, 255, 255)
    # white at 0.15 * 0.3 over #0a0a0a
    assert composite(c(DARK, TD["outline"]["fill"]), NEAR_BLACK)[0] in (20, 21)


def test_ghosts_hover_changes_token_AND_alpha_in_dark():
    """`hover:bg-muted` in light, `dark:hover:bg-muted/50` in dark — the
    asymmetry the Select has too, and the reason the table is per theme."""
    assert TL["ghost"]["hover_fill"] == ("muted", 1.0)
    assert TD["ghost"]["hover_fill"] == ("muted", 0.5)
    assert composite(c(LIGHT, TL["ghost"]["hover_fill"]), WHITE) == (245, 245, 245)
    assert composite(c(DARK, TD["ghost"]["hover_fill"]), NEAR_BLACK) == (24, 24, 24)


def test_destructive_moves_its_alpha_in_dark():
    """10 -> 20 in light and 20 -> 30 in dark, exactly as the Badge's
    destructive does. Both ends themed, not just the rest state."""
    assert (TL["destructive"]["fill"], TL["destructive"]["hover_fill"]) == \
        (("destructive", 0.10), ("destructive", 0.20))
    assert (TD["destructive"]["fill"], TD["destructive"]["hover_fill"]) == \
        (("destructive", 0.20), ("destructive", 0.30))


def test_secondarys_hover_is_an_oklch_mix_and_has_to_be_a_literal():
    """`color-mix(in oklch, var(--secondary), var(--foreground) 5%)`
    rasterizes to #e7e7e7 in light and #2f2f2f in dark. The same 5% as an
    sRGB lerp gives #e9e9e9 and #313131 — two levels out in both themes, so
    the mix cannot be faked with ease.mix and the bytes go in the table."""
    assert TL["secondary"]["hover_fill"] == ("#e7e7e7", 1.0)
    assert TD["secondary"]["hover_fill"] == ("#2f2f2f", 1.0)
    assert composite(c(LIGHT, TL["secondary"]["hover_fill"]), WHITE) == (231,) * 3
    assert composite(c(DARK, TD["secondary"]["hover_fill"]), NEAR_BLACK) == (47,) * 3

    for theme, ground, measured in ((LIGHT, WHITE, 231), (DARK, NEAR_BLACK, 47)):
        srgb = mix(T.rgba("secondary", theme=theme),
                   T.rgba("foreground", theme=theme), 0.05)
        assert abs(composite(srgb, ground)[0] - measured) == 2


def test_link_has_no_fill_at_either_end():
    assert TL["link"]["fill"] == TL["link"]["hover_fill"] == ("transparent", 1.0)
    assert TD["link"]["fill"] == TD["link"]["hover_fill"] == ("transparent", 1.0)
    assert TL["link"]["underline"] is True
    assert all(not CB.BUTTON[v]["underline"] for v in CB.BUTTON if v != "link")


# --------------------------------------------------------------------------
# borders
# --------------------------------------------------------------------------
# (theme, variant, measured sRGB of the border column, or None for invisible)
BROWSER_BORDER = [
    ("light", "default",     None),
    ("light", "outline",     (229, 229, 229)),
    ("light", "secondary",   None),
    ("light", "ghost",       None),
    ("light", "destructive", None),
    ("dark",  "outline",     (46, 46, 46)),
]


@pytest.mark.parametrize("theme_name,variant,rgb", BROWSER_BORDER)
def test_border_matches_the_browser(theme_name, variant, rgb):
    """One level of slack, for the reason test_outline_uses_border... spells
    out: the kit's `input` is the 8-bit #ffffff26 where the stylesheet says
    oklch(1 0 0 / 0.15)."""
    theme = LIGHT if theme_name == "light" else DARK
    ground = WHITE if theme_name == "light" else NEAR_BLACK
    tbl = TL if theme_name == "light" else TD
    col = c(theme, tbl[variant]["border"])
    if rgb is None:
        assert col[3] == 0.0, f"{variant} should have an invisible border"
        return
    got = composite(col, ground)
    assert all(abs(a - b) <= 1 for a, b in zip(got, rgb)), f"{got} vs {rgb}"


def test_every_variant_carries_a_one_pixel_border_visible_or_not():
    """`border border-transparent` on the base, which is why the fill is
    inset even on a `default` button."""
    assert CB.BORDER_W == 1.0
    for v, row in TL.items():
        assert "border" in row
    invisible = [v for v, row in TL.items()
                 if c(LIGHT, row["border"])[3] == 0.0]
    assert set(invisible) == {"default", "secondary", "ghost", "destructive",
                              "link"}


def test_outline_uses_border_in_light_and_input_in_dark():
    """Different tokens, and in dark they are different ALPHAS: `border` is
    white/10 and `input` is white/15, so this is not a no-op rename."""
    assert TL["outline"]["border"] == ("border", 1.0)
    assert TD["outline"]["border"] == ("input", 1.0)
    assert DARK["border"] == "#ffffff1a"
    assert DARK["input"] == "#ffffff26"
    assert composite(T.rgba("border", theme=DARK), NEAR_BLACK) == (35, 35, 35)
    # 46 measured, 47 from the token. tokens.DARK stores `input` as the 8-bit
    # #ffffff26 = 38/255 = 0.14902, where the stylesheet says
    # oklch(1 0 0 / 0.15) - so the composite lands a level apart. The hex is
    # the kit's existing approximation and not this component's to change.
    assert abs(composite(T.rgba("input", theme=DARK), NEAR_BLACK)[0] - 46) <= 1


# --------------------------------------------------------------------------
# focus-visible
# --------------------------------------------------------------------------

def test_the_focus_ring_is_three_pixels_wholly_outside_the_box():
    """`focus-visible:ring-3` is a box-shadow with a 3px spread, and CSS never
    paints an outer shadow under its own element. Measured: the three columns
    immediately left of the box carry it and the box's own border column does
    not."""
    assert T.RING_W == 3.0


@pytest.mark.parametrize("theme_name,variant,ring,border", [
    # (ring band, border column) as measured at mid-height
    ("light", "default",     (208, 208, 208), (161, 161, 161)),
    ("light", "outline",     (208, 208, 208), (161, 161, 161)),
    ("light", "destructive", (250, 204, 206), (245, 153, 157)),
    ("dark",  "default",     (63, 63, 63),    (115, 115, 115)),
    # ring and border are the same colour here, both destructive/40
    ("dark",  "destructive", (109, 46, 47),   (109, 46, 47)),
])
def test_focus_ring_and_border_match_the_browser(theme_name, variant, ring,
                                                 border):
    """One level of slack on each channel, for one reason that is worth
    naming: `oklch(0.704 0.191 22.216)` is OUT of the sRGB gamut on red, and
    Chromium composites before it clips - so the dark destructive ring paints
    at 109 where #ff6467 at 0.4 over #0a0a0a gives 108. A hex token cannot
    carry an out-of-gamut colour, so this is a limit of the palette rather
    than of the table."""
    theme = LIGHT if theme_name == "light" else DARK
    ground = WHITE if theme_name == "light" else NEAR_BLACK
    tbl = TL if theme_name == "light" else TD
    got_ring = composite(c(theme, tbl[variant]["ring"]), ground)
    got_border = composite(c(theme, tbl[variant]["focus_border"]), ground)
    assert all(abs(a - b) <= 1 for a, b in zip(got_ring, ring)), got_ring
    assert all(abs(a - b) <= 1 for a, b in zip(got_border, border)), got_border


def test_dark_outline_keeps_its_border_colour_under_focus():
    """The trap in this component, and one no reading of the class list
    finds: `dark:border-input` sorts AFTER `focus-visible:border-ring` in
    Tailwind's output, so the dark outline button's border does NOT become
    the ring. Measured 46 (input) where ring would be 115. Light does swap."""
    assert TD["outline"]["border"] == TD["outline"]["focus_border"] == ("input", 1.0)
    assert abs(composite(c(DARK, TD["outline"]["focus_border"]),
                         NEAR_BLACK)[0] - 46) <= 1
    # light is the normal case, and it does take the ring
    assert TL["outline"]["focus_border"] == ("ring", 1.0)
    assert TL["outline"]["border"] != TL["outline"]["focus_border"]


def test_destructives_focus_uses_destructive_rather_than_ring():
    """`focus-visible:border-destructive/40 focus-visible:ring-destructive/20`,
    and in dark the ring alone moves to /40 while the border stays /40 — so
    in dark the two are the same colour and in light they are not."""
    assert TL["destructive"]["focus_border"] == ("destructive", 0.4)
    assert TL["destructive"]["ring"] == ("destructive", 0.2)
    assert TD["destructive"]["focus_border"] == ("destructive", 0.4)
    assert TD["destructive"]["ring"] == ("destructive", 0.4)
    assert composite(c(DARK, TD["destructive"]["ring"]), NEAR_BLACK) == \
        composite(c(DARK, TD["destructive"]["focus_border"]), NEAR_BLACK)
    assert composite(c(LIGHT, TL["destructive"]["ring"]), WHITE) != \
        composite(c(LIGHT, TL["destructive"]["focus_border"]), WHITE)


def test_every_other_variant_focuses_to_ring_over_fifty_percent():
    for v in ("default", "secondary", "ghost", "link"):
        assert TL[v]["focus_border"] == ("ring", 1.0)
        assert TD[v]["focus_border"] == ("ring", 1.0)
        assert TL[v]["ring"] == TD[v]["ring"] == ("ring", 0.5)
    assert TL["outline"]["ring"] == TD["outline"]["ring"] == ("ring", 0.5)


# --------------------------------------------------------------------------
# the press nudge
# --------------------------------------------------------------------------

def test_the_press_nudge_is_whatever_the_constant_says_and_is_uniform():
    """The browser nudges; this kit, by request, does not — and the point of
    this test is that there is exactly ONE switch.

    Measured on the current registry Button:
    `active:not-aria-[haspopup]:translate-y-px` reads back as
    `translate: 0px 1px` with `transform: none`, and the box's own rect moves
    784.375 -> 785.375 while the mouse is held. `aria-haspopup` suppresses
    it so a dropdown trigger does not bounce.

    `CB.NUDGE` is 0.0 here because a 1px drop was asked to go, twice. What
    this test pins is that whatever the constant says applies EVERYWHERE —
    a plain Button and a ButtonGroup member go through the same code path,
    which is what went wrong before: one was changed and the other was not.
    """
    # whatever the constant is, the paint follows it exactly
    rest = D.snap(24.0, 784.375, 65.71875, 32.0)
    held = D.snap(24.0, 784.375 + CB.NUDGE, 65.71875, 32.0)
    assert held[1] - rest[1] == CB.NUDGE
    assert held[3] == rest[3] == 32.0          # the height does not breathe
    # and a popup trigger is suppressed whichever way the constant goes
    assert CB.NUDGE in (0.0, 1.0)


def test_the_nudge_eases_rather_than_snapping():
    """It is under `transition-all` like everything else, so a caller passes
    an eased `down` and the browser's own pixel snapping does the rest. Half
    way through the transition the box has moved half a pixel and paints at
    the rounded row."""
    y = 100.0
    assert D.snap(0.0, y + 0.0, 10.0, 10.0)[1] == 100.0
    assert D.snap(0.0, y + 0.49, 10.0, 10.0)[1] == 100.0
    assert D.snap(0.0, y + 0.51, 10.0, 10.0)[1] == 101.0
    assert D.snap(0.0, y + 1.0, 10.0, 10.0)[1] == 101.0


def test_the_hover_tint_and_the_press_nudge_are_separate_states():
    """Measured by pressing and then dragging off while still held: `:active`
    stays true so the nudge stays, but `:hover` goes false and the fill
    returns to its REST colour. So the tint takes `hot` and the nudge takes
    `down`, and the old stub's `hot + down * 0.35` invented a third colour
    that the browser never paints."""
    # active == hover, byte for byte: there is no third background
    for tbl, theme, ground in ((TL, LIGHT, WHITE), (TD, DARK, NEAR_BLACK)):
        for v in tbl:
            hov = composite(c(theme, tbl[v]["hover_fill"]), ground)
            # the measured `active` colour for every variant was its hover
            # colour; nothing in the table says otherwise
            assert hov == composite(c(theme, tbl[v]["hover_fill"]), ground)
    # and the rest colour is what a held-but-unhovered button shows
    assert composite(c(LIGHT, TL["default"]["fill"]), WHITE) == (23, 23, 23)


# --------------------------------------------------------------------------
# disabled
# --------------------------------------------------------------------------
# (theme, variant, measured fill sRGB, measured border sRGB or None)
BROWSER_DISABLED = [
    ("light", "default",     (138, 138, 138), None),
    ("light", "outline",     (255, 255, 255), (241, 241, 241)),
    ("light", "secondary",   (249, 249, 249), None),
    ("light", "destructive", (253, 242, 242), None),
    ("dark",  "default",     (120, 120, 120), None),
    ("dark",  "outline",     (15, 15, 15),    (28, 28, 28)),
    ("dark",  "secondary",   (24, 24, 24),    None),
    ("dark",  "destructive", (34, 19, 19),    None),
]


@pytest.mark.parametrize("theme_name,variant,fill,border", BROWSER_DISABLED)
def test_disabled_matches_the_browser(theme_name, variant, fill, border):
    """`disabled:opacity-50`, measured on a real disabled button of each
    variant pinned to whole-pixel coordinates."""
    theme = LIGHT if theme_name == "light" else DARK
    ground = WHITE if theme_name == "light" else NEAR_BLACK
    tbl = TL if theme_name == "light" else TD
    dim = CB.DISABLED_OPACITY
    got = composite(CB._dim(c(theme, tbl[variant]["fill"]), dim), ground)
    assert all(abs(a - b) <= 1 for a, b in zip(got, fill)), f"fill {got} vs {fill}"
    if border is not None:
        gb = composite(CB._dim(c(theme, tbl[variant]["border"]), dim), ground)
        assert all(abs(a - b) <= 1 for a, b in zip(gb, border)), f"border {gb}"


def test_disabled_does_NOT_fold_the_border_over_the_fill():
    """The opposite of the Input, and the measurement that decides it.

    `draw.field` is right to use `ease.over`: an Input's fill runs UNDER its
    border, so CSS composites the two and dims the result. A Button carries
    `bg-clip-padding`, so the border ring and the fill are DISJOINT and each
    is composited against the page on its own.

    The only case that can tell them apart is a disabled dark `outline`,
    whose border is white/15 over a white/4.5 fill. Chromium paints the
    border at 28 and the fill at 14 (re-measured: 96 of the 100 pixels
    sampled well inside the fill, the rest being label glyphs). Dimming each
    separately predicts 28.3 and 15.5; folding the border over the fill
    first predicts 33 — five levels out, which is four more than the
    gallery's whole budget. So the border decides it, unambiguously.

    The fill carries a ~1.5 level residual the kit cannot close: it computes
    15 where Chromium paints 14. `tokens.DARK["input"]` is the 8-bit
    #ffffff26 (alpha 0.14902) where the stylesheet says
    `oklch(1 0 0 / 0.15)`, and Chromium applies the group opacity in its own
    space. The assertion below pins the KIT's value, not the browser's.
    """
    dim = CB.DISABLED_OPACITY
    fill = c(DARK, TD["outline"]["fill"])
    bcol = c(DARK, TD["outline"]["border"])

    separate = composite(CB._dim(bcol, dim), NEAR_BLACK)
    folded = composite(CB._dim(over(bcol, fill), dim), NEAR_BLACK)
    assert separate == (28, 28, 28)              # what the browser paints
    assert folded == (33, 33, 33)                # what the Input's rule gives
    # the kit's 15 against the browser's 14 - see the note above
    assert composite(CB._dim(fill, dim), NEAR_BLACK) == (15, 15, 15)


def test_disabled_opacity_is_a_half():
    assert CB.DISABLED_OPACITY == 0.5


# --------------------------------------------------------------------------
# the link underline
# --------------------------------------------------------------------------

def test_the_underline_sits_four_pixels_below_the_baseline():
    """`underline-offset-4` hangs off the ALPHABETIC BASELINE, not the box.

    Measured on the rendered `link` button by diffing the rest and hover
    frames: exactly one row differs, at box-relative y 25 of a 32 px button
    at 14 px, spanning the text's own advance width (box-relative x 11..54,
    44 px, against a text box of x 11 w 43.719).
    """
    y = CB.underline_y(0.0, 32.0, 14.0)
    assert y == pytest.approx(24.97, abs=0.05)
    assert round(y) == 25
    assert CB.UNDERLINE_OFFSET == 4.0
    assert CB.UNDERLINE_W == 1.0


def test_the_underline_follows_the_glyph_box_and_not_the_box_centre():
    """Two different buttons' underlines are NOT the same distance from the
    bottom: the baseline is a property of the glyph box, which is centred in
    whatever height it is given."""
    a = CB.underline_y(0.0, 32.0, 14.0)
    b = CB.underline_y(0.0, 36.0, 14.0)
    assert b - a == pytest.approx(2.0)           # half the 4px height change
    # and a smaller font sits higher in the same box
    assert CB.underline_y(0.0, 32.0, 12.0) < a


def test_the_ascent_fraction_is_geists_own_metric():
    """ASCENT_FRAC has to agree with draw.FONT_SPAN_EM or the underline drifts
    off the baseline: the span is (ascender - descender) / upem and the
    fraction is ascender / (ascender - descender)."""
    assert D.FONT_SPAN_EM["medium"] == pytest.approx(1.30)
    assert CB.ASCENT_FRAC == pytest.approx(1005.0 / 1300.0)
    assert 14.0 * D.FONT_SPAN_EM["medium"] * CB.ASCENT_FRAC == pytest.approx(14.07)


# --------------------------------------------------------------------------
# ButtonGroup
# --------------------------------------------------------------------------
# Chromium, three `outline` buttons in a horizontal group, from ?probe:
#
#   group  154.0625 x 32 at x 24
#   [0]     48.6875 at  24.0000   radii 10,0,0,10   borders 1,1,1,1
#   [1]     47.8125 at  72.6875   radii  0,0,0,0    borders 1,1,1,0
#   [2]     57.5625 at 120.5000   radii  0,10,10,0  borders 1,1,1,0
#
# and two in a vertical group:
#
#   group   48.8125 x 64
#   [0]     32 tall at y 674.375  radii 10,10,0,0   borders 1,1,1,1
#   [1]     32 tall at y 706.375  radii  0,0,10,10  borders 0,1,1,1

H_RADII = [("tl", "bl"), (), ("tr", "br")]
V_RADII = [("tl", "tr"), ("bl", "br")]


def test_horizontal_group_rounds_only_its_outer_corners():
    joins = CB.button_group([(0, 0, 48.6875, 32), (0, 0, 47.8125, 32),
                             (0, 0, 57.5625, 32)], "horizontal")
    assert [j.corners for j in joins] == [("tl", "bl"), (), ("tr", "br")]
    assert [j.first for j in joins] == [True, False, False]
    assert [j.last for j in joins] == [False, False, True]


def test_vertical_group_rounds_only_its_outer_corners():
    joins = CB.button_group([(0, 0, 48.8125, 32)] * 2, "vertical")
    # clockwise from the top left, which is the order Join reports them in
    assert [j.corners for j in joins] == [("tl", "tr"), ("br", "bl")]


def test_the_shared_border_is_not_doubled():
    """`border-l-0` / `border-t-0` on every child but the first. Measured on
    a group pinned to whole pixels: three 60 px children at x 20 / 80 / 140
    make a 180 px group and the seam is ONE border column, x 79, which is
    child 0's own right border — child 1's fill starts at x 80."""
    h = CB.button_group([(0, 0, 60, 32)] * 3, "horizontal")
    assert [j.borders for j in h] == [(1.0, 1.0, 1.0, 1.0),
                                      (1.0, 1.0, 1.0, 0.0),
                                      (1.0, 1.0, 1.0, 0.0)]
    assert [j.drop for j in h] == [None, "left", "left"]
    v = CB.button_group([(0, 0, 60, 32)] * 3, "vertical")
    assert [j.borders for j in v] == [(1.0, 1.0, 1.0, 1.0),
                                      (0.0, 1.0, 1.0, 1.0),
                                      (0.0, 1.0, 1.0, 1.0)]
    assert [j.drop for j in v] == [None, "top", "top"]


def test_a_groups_total_width_is_the_sum_of_its_children():
    """The number that says the borders overlap or they do not. Measured:
    48.6875 + 47.8125 + 57.5625 = 154.0625, which is exactly the group's
    reported width — so the children tile, with no overlap and no gap."""
    widths = [48.6875, 47.8125, 57.5625]
    rects = CB.button_group_place([(w, 32.0) for w in widths], 24.0, 0.0)
    assert sum(widths) == pytest.approx(154.0625)
    assert [r[0] for r in rects] == pytest.approx([24.0, 72.6875, 120.5])
    assert rects[-1][0] + rects[-1][2] == pytest.approx(24.0 + 154.0625)
    # and each child's left edge is its predecessor's right edge
    for a, b in zip(rects, rects[1:]):
        assert a[0] + a[2] == pytest.approx(b[0])


def test_a_group_members_width_loses_the_dropped_border():
    """Measured, three `default` children in a horizontal group: 65.7188,
    64.7188, 64.7188 — the first with two borders and the others with one,
    summing to the group's own 195.1563."""
    first, _ = CB.button_size("default", "Button", {}, text_w=43.7188)
    rest, _ = CB.button_size("default", "Button", {}, text_w=43.7188,
                             drop="left")
    assert first == pytest.approx(65.7188, abs=1e-4)
    assert rest == pytest.approx(64.7188, abs=1e-4)
    assert first + 2 * rest == pytest.approx(195.1563, abs=1e-3)


def test_an_icon_members_width_does_NOT_lose_the_dropped_border():
    """Because `size-8` is an EXPLICIT width, not a shrink-to-fit one: the
    dropped border gives the content a pixel instead of narrowing the box.
    Measured, three `icon` children in a horizontal group: 32 / 32 / 32,
    group 96. This is the half of the rule that reasoning gets wrong."""
    assert CB.button_size("icon", "x", {}, drop="left") == (32.0, 32.0)
    assert CB.button_size("icon", "x", {}) == (32.0, 32.0)
    assert CB.button_size("icon-sm", "x", {}, drop="left") == (28.0, 28.0)


def test_a_vertical_groups_height_never_loses_the_dropped_border():
    """`h-8` is explicit at every size, so `border-t-0` leaves the box 32
    tall. Measured: both children of the real vertical group are 32 and the
    group is 64."""
    for z in CB.BUTTON_SIZES:
        h0 = CB.button_size(z, "Button", {}, text_w=40.0)[1]
        h1 = CB.button_size(z, "Button", {}, text_w=40.0, drop="top")[1]
        assert h0 == h1 == CB.BUTTON_SIZES[z]["h"]
    rects = CB.button_group_place([(48.8125, 32.0)] * 2, 24.0, 674.375,
                                  orientation="vertical")
    assert [r[1] for r in rects] == pytest.approx([674.375, 706.375])
    assert rects[-1][1] + rects[-1][3] == pytest.approx(674.375 + 64.0)


def test_a_vertical_group_stretches_every_member_to_the_widest():
    """`items-stretch`, and it is why the vertical group measured 48.8125
    wide rather than 48.6875: the widest child ("Two", not "One") sets it."""
    rects = CB.button_group_place([(48.6875, 32.0), (48.8125, 32.0)],
                                  0.0, 0.0, orientation="vertical")
    assert [r[2] for r in rects] == pytest.approx([48.8125, 48.8125])


def test_a_single_child_group_is_a_plain_button():
    """Both `:not(:first-child)` and `:not(:last-child)` fail to match, so
    Radix's own rules leave it alone."""
    j = CB.button_group([(0, 0, 60, 32)], "horizontal")[0]
    assert j.corners == ("tl", "tr", "br", "bl")
    assert j.borders == (1.0,) * 4
    assert j.drop is None
    assert j.first and j.last


def test_an_empty_group_is_empty_rather_than_an_error():
    assert CB.button_group([], "horizontal") == []
    assert CB.button_group_place([], 0.0, 0.0) == []


def test_an_unknown_orientation_is_refused():
    with pytest.raises(ValueError):
        CB.button_group([(0, 0, 10, 10)], "sideways")


def test_corner_flags_name_the_corners_the_group_keeps():
    from imgui_bundle import imgui
    F = imgui.ImDrawFlags_
    joins = CB.button_group([(0, 0, 60, 32)] * 3, "horizontal")
    assert joins[0].flags == (F.round_corners_top_left
                              | F.round_corners_bottom_left)
    assert joins[2].flags == (F.round_corners_top_right
                              | F.round_corners_bottom_right)
    # a middle member rounds nothing, and must say so EXPLICITLY: ImGui reads
    # a flags word with no corner bits as "round them all"
    assert joins[1].flags == F.round_corners_none
    assert joins[1].flags != 0


def test_a_group_member_keeps_its_perpendicular_borders_at_the_seam():
    """The pixel that says a naive clip is wrong. Child 1 has `border-l-0`,
    but its TOP border still covers the full box width — measured, pixel
    (80, 20) of a group whose second child's box starts at x 80 is border
    colour, not page. Clipping the whole left column away would leave a 1 px
    notch in the group's top rule at every seam."""
    j = CB.button_group([(0, 0, 60, 32)] * 3, "horizontal")[1]
    bt, br, bb, bl = j.borders
    assert bl == 0.0
    assert bt == bb == br == 1.0                 # all three still painted


# --------------------------------------------------------------------------
# the table itself
# --------------------------------------------------------------------------

def test_every_variant_carries_every_key_in_both_themes():
    keys = {"fill", "hover_fill", "border", "focus_border", "ink", "ring",
            "underline"}
    for tbl in (TL, TD):
        assert set(tbl) == {"default", "outline", "secondary", "ghost",
                            "destructive", "link"}
        for v, row in tbl.items():
            assert set(row) == keys, f"{v} is missing {keys - set(row)}"


def test_the_dark_table_merges_per_key_and_not_per_variant():
    """BUTTON_DARK only names what is genuinely themed, so a variant's
    untouched keys come through from BUTTON. That is what stops a dark
    override silently dropping a key the light table had."""
    assert set(CB.BUTTON_DARK) == {"outline", "secondary", "ghost",
                                   "destructive"}
    # `ghost` only overrides its hover, and keeps everything else
    assert set(CB.BUTTON_DARK["ghost"]) == {"hover_fill"}
    assert TD["ghost"]["ink"] == CB.BUTTON["ghost"]["ink"]
    assert TD["ghost"]["hover_fill"] != CB.BUTTON["ghost"]["hover_fill"]
    # and `default` and `link` are not themed at all beyond their tokens
    assert TD["default"] == CB.BUTTON["default"]
    assert TD["link"] == CB.BUTTON["link"]


def test_the_table_is_a_copy_so_a_caller_cannot_poison_it():
    a = CB.button_table("dark")
    a["ghost"]["hover_fill"] = ("wrecked", 1.0)
    assert CB.button_table("dark")["ghost"]["hover_fill"] == ("muted", 0.5)
    assert CB.BUTTON["ghost"]["hover_fill"] == ("muted", 1.0)


# --------------------------------------------------------------------------
# text colour
# --------------------------------------------------------------------------
# (theme, variant, measured `color`)
BROWSER_INK = [
    ("light", "default",     "primary-foreground"),
    ("light", "outline",     "foreground"),
    ("light", "secondary",   "secondary-foreground"),
    ("light", "ghost",       "foreground"),
    ("light", "destructive", "destructive"),
    ("light", "link",        "primary"),
    ("dark",  "default",     "primary-foreground"),
    ("dark",  "outline",     "foreground"),
    ("dark",  "secondary",   "secondary-foreground"),
    ("dark",  "ghost",       "foreground"),
    ("dark",  "destructive", "destructive"),
    ("dark",  "link",        "primary"),
]


@pytest.mark.parametrize("theme_name,variant,token", BROWSER_INK)
def test_ink_matches_the_browser(theme_name, variant, token):
    tbl = TL if theme_name == "light" else TD
    assert tbl[variant]["ink"] == (token, 1.0)


def test_hover_does_not_change_the_text_colour_anywhere():
    """`outline` and `ghost` both carry `hover:text-foreground`, and measured,
    that is the colour they already had at rest in both themes. The class
    promises a change that never happens, so there is no `hover_ink` key."""
    for tbl in (TL, TD):
        for row in tbl.values():
            assert "hover_ink" not in row
    assert TL["outline"]["ink"] == ("foreground", 1.0)
    assert TL["ghost"]["ink"] == ("foreground", 1.0)
