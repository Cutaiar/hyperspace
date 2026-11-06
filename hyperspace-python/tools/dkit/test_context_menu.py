"""The ContextMenu's placement law, pinned to what Chromium actually does.

Pure geometry — no GL, no display, no imgui context. `place_at_pointer` is
the kind of function that is wrong in ways you only notice when a menu opens
off the bottom of someone else's screen, so it is pinned here rather than
eyeballed once, the way test_box.py pins `place_popover`.

Every expected number came out of a real right-click on the `?probe` route's
`contextmenu.target` block (Radix's ContextMenu has no `defaultOpen`), read
back from `getBoundingClientRect` in both themes — not from the Tailwind
classes. The ones that matter most:

* the pointer offset is **+2**, not 0 (Radix's `sideOffset` on its implicit
  `side="right" align="start"`);
* it **flips** on x and **shifts** on y, and the flip threshold is exact;
* an item is **28** px tall, because `text-sm` is 20/14 — not the 26 that
  "py-1 around a 14px line" suggests.

    uv run python -m pytest tools/dkit/test_context_menu.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from box import Rect                                       # noqa: E402
from comp_context_menu import (CONTEXT_MENU,               # noqa: E402
                               CONTEXT_MENU_DARK,
                               context_menu_table,
                               place_at_pointer)

VIEW = Rect(0, 0, 1000, 800)
W, H = 144.0, 125.0          # the measured panel on the probe's menu


# --------------------------------------------------------------------------
# the offset law
# --------------------------------------------------------------------------

def test_the_pointer_offset_is_two_not_zero():
    """Measured dx = +2.000 at every click point, in both themes."""
    r = place_at_pointer(400, 300, W, H, VIEW)
    assert r.x == 402
    assert r.y == 300
    assert (r.w, r.h) == (W, H)


def test_the_offset_is_on_x_only():
    assert CONTEXT_MENU["pointer_dx"] == 2.0
    assert CONTEXT_MENU["pointer_dy"] == 0.0


def test_no_collision_padding():
    """Unlike place_popover's 8px gutter: the browser let the panel's right
    edge land exactly on the viewport's (gap 0.000) without flipping."""
    assert CONTEXT_MENU["collision_pad"] == 0.0
    r = place_at_pointer(854, 300, W, H, Rect(0, 0, 1000, 800))
    assert r.right == 1000.0


def test_a_moving_pointer_moves_the_panel_one_for_one():
    a = place_at_pointer(400, 300, W, H, VIEW)
    b = place_at_pointer(401, 301, W, H, VIEW)
    assert (b.x - a.x, b.y - a.y) == (1, 1)


# --------------------------------------------------------------------------
# flip on x, shift on y
# --------------------------------------------------------------------------
# Measured in a 400x900 viewport with the 144px panel: the click at x=254
# stays on the right and its right edge lands on 400.000; the click at x=255
# flips, landing at 109. That is the threshold to the pixel.
FLIP_VIEW = Rect(0, 0, 400, 900)


@pytest.mark.parametrize("px,want_x", [
    (200, 202), (240, 242), (250, 252), (253, 255), (254, 256),
    (255, 109), (256, 110), (260, 114), (300, 154),
])
def test_x_flip_threshold_is_exact(px, want_x):
    assert place_at_pointer(px, 100, W, H, FLIP_VIEW).x == want_x


def test_flipped_panel_hangs_off_the_other_side_of_the_pointer():
    r = place_at_pointer(255, 100, W, H, FLIP_VIEW)
    assert r.right == 255 - CONTEXT_MENU["pointer_dx"]


def test_y_never_flips_it_only_clamps():
    """Radix shifts on the align axis. A click near the floor does NOT put
    the panel above the pointer — it slides it up to sit on the floor."""
    r = place_at_pointer(124, 870, W, H, Rect(0, 0, 1200, 900))
    assert r.bottom == 900
    assert r.y == 775                      # measured
    assert r.y < 870                       # and so it covers the pointer


@pytest.mark.parametrize("py,want_y", [
    (759, 759),        # fits: dy = 0.000
    (780, 775),
    (786, 775),
    (790, 775),
    (813, 775),
    (860, 775),
    (870, 775),
])
def test_y_offset_is_zero_until_the_floor(py, want_y):
    assert place_at_pointer(124, py, W, H, Rect(0, 0, 1200, 900)).y == want_y


# --------------------------------------------------------------------------
# the browser rows, straight out of the probe
# --------------------------------------------------------------------------
# (viewport, click, panel) exactly as Chromium reported them. Identical in
# light and dark — the placement carries no theme.
BROWSER = [
    ((1200, 900), (27, 759), (29, 759)),
    ((1200, 900), (124, 786), (126, 775)),
    ((1200, 900), (125, 787), (127, 775)),
    ((1200, 900), (441, 813), (443, 775)),
    ((1200, 900), (124, 870), (126, 775)),
    ((400, 900), (200, 786), (202, 775)),
    ((400, 900), (255, 786), (109, 775)),
    ((400, 900), (300, 786), (154, 775)),
    ((300, 900), (150, 786), (152, 775)),
    ((300, 900), (220, 786), (74, 775)),
]


@pytest.mark.parametrize("vp,click,want", BROWSER)
def test_matches_the_browser(vp, click, want):
    r = place_at_pointer(click[0], click[1], W, H, Rect(0, 0, vp[0], vp[1]))
    assert (r.x, r.y) == want


# --------------------------------------------------------------------------
# the one deliberate divergence
# --------------------------------------------------------------------------

def test_clamps_x_where_radix_would_let_it_hang_off():
    """With a 160px viewport and a 144px panel, neither side of the pointer
    fits. Radix keeps the side that overflows less and lets the panel hang
    off the edge — measured at x=82 (66px past the right) for a click at 80,
    and at x=-6 for a click at 140. An ImGui popup off the window is simply
    lost, so this clamps; the SIDE CHOICE still follows the browser."""
    narrow = Rect(0, 0, 160, 900)
    assert place_at_pointer(80, 300, W, H, narrow).x == 16     # 160 - 144
    assert place_at_pointer(140, 300, W, H, narrow).x == 0
    assert place_at_pointer(20, 300, W, H, narrow).x == 16


def test_a_tie_keeps_the_preferred_side():
    """At px=80 in a 160px viewport both sides overflow by 66, and the
    browser kept the right side (x = px + 2 = 82). Unclamped, that is the
    side this picks too."""
    r = place_at_pointer(80, 300, W, H, Rect(0, 0, 160, 900), pad=0.0)
    assert r.x == 16            # clamped from 82, i.e. still the right side
    assert r.right == 160


# --------------------------------------------------------------------------
# a panel bigger than the viewport
# --------------------------------------------------------------------------

def test_height_clamps_to_the_viewport():
    """`max-h-(--radix-context-menu-content-available-height)`: measured, a
    100px-tall viewport gave a 100px-tall panel at y=0 rather than a 125px
    one hanging off."""
    r = place_at_pointer(124, 50, W, H, Rect(0, 0, 1200, 100))
    assert (r.y, r.h) == (0, 100)


def test_a_short_viewport_still_sits_on_the_floor():
    r = place_at_pointer(124, 60, W, H, Rect(0, 0, 1200, 130))
    assert (r.y, r.h) == (5, 125)          # measured
    assert r.bottom == 130


def test_a_panel_taller_than_the_view_pins_to_the_top():
    r = place_at_pointer(500, 400, W, 2000, VIEW)
    assert r.y == VIEW.y
    assert r.h == VIEW.h


# --------------------------------------------------------------------------
# the sweep: it is never off screen, from anywhere
# --------------------------------------------------------------------------

@pytest.mark.parametrize("px", list(range(0, 1001, 143)) + [999])
@pytest.mark.parametrize("py", list(range(0, 801, 113)) + [799])
def test_never_leaves_the_viewport(px, py):
    r = place_at_pointer(px, py, W, H, VIEW)
    assert r.x >= VIEW.x and r.y >= VIEW.y
    assert r.right <= VIEW.right and r.bottom <= VIEW.bottom


@pytest.mark.parametrize("w,h", [(144, 125), (320, 600), (900, 790)])
@pytest.mark.parametrize("px,py", [(0, 0), (999, 799), (0, 799), (999, 0),
                                   (998, 798)])
def test_never_leaves_the_viewport_at_any_size(w, h, px, py):
    r = place_at_pointer(px, py, w, h, VIEW)
    assert r.x >= VIEW.x and r.y >= VIEW.y
    assert r.right <= VIEW.right + 1e-9
    assert r.bottom <= VIEW.bottom + 1e-9


@pytest.mark.parametrize("px", range(20, 1021, 199))
@pytest.mark.parametrize("py", range(30, 831, 157))
def test_respects_a_work_area_that_does_not_start_at_zero(px, py):
    """`ui.viewport` is imgui's WORK area, so its origin is not 0,0."""
    work = Rect(20, 30, 1000, 800)
    r = place_at_pointer(px, py, W, H, work)
    assert r.x >= work.x and r.y >= work.y
    assert r.right <= work.right and r.bottom <= work.bottom


def test_honours_a_collision_pad_when_one_is_asked_for():
    r = place_at_pointer(995, 795, W, H, VIEW, pad=8.0)
    assert r.right <= VIEW.right - 8
    assert r.bottom <= VIEW.bottom - 8


# --------------------------------------------------------------------------
# the measured table
# --------------------------------------------------------------------------

def test_panel_is_the_sum_of_its_measured_rows():
    """4 + label 24 + item 28 + item 28 + separator 9 + item 28 + 4 = 125,
    which is the panel height Chromium reported to the 1/64 px."""
    t = CONTEXT_MENU
    block = t["sep_h"] + 2 * t["sep_my"]
    assert block == 9
    total = (2 * t["pad"] + t["label_h"] + 3 * t["item_h"] + block)
    assert total == H


def test_item_is_28_because_text_sm_carries_a_20px_line():
    assert CONTEXT_MENU["item_h"] == 28.0
    assert CONTEXT_MENU["item_h"] == 20.0 + 2 * CONTEXT_MENU["pad"]
    assert CONTEXT_MENU["label_h"] == 16.0 + 2 * CONTEXT_MENU["pad"]


def test_min_width_is_the_one_chrome_number_that_differs_from_dropdown():
    """ContextMenuContent is `min-w-36` where DropdownMenuContent is
    `min-w-32`; every other chrome class on the content, item, label,
    separator and shortcut is character-identical."""
    import menu
    assert CONTEXT_MENU["min_w"] == 144.0
    assert menu.MIN_W == 128.0
    assert CONTEXT_MENU["min_w"] != menu.MIN_W


def test_the_values_shared_with_menu_py_are_not_silent_duplicates():
    """Where the table says `== menu.X`, it has to stay true."""
    import menu
    assert CONTEXT_MENU["pad"] == menu.PAD
    assert CONTEXT_MENU["sep_my"] == menu.SEP_MY
    assert CONTEXT_MENU["item_pad_x"] == menu.ITEM_PAD_X
    assert CONTEXT_MENU["gap"] == menu.GAP


def test_menu_py_now_agrees_with_the_browser():
    """This test was written to pin a DISAGREEMENT: menu.py had an item at
    26 and an icon at 14 where the browser measures 28 and 16, and it had
    shipped that way. The fix has landed, so the test now asserts agreement
    instead - and keeps asserting it, which is the point.

    The item classes are byte-identical between ContextMenu and
    DropdownMenu, so the browser's answer is the same for both.
    """
    import menu
    assert menu.ITEM_H == CONTEXT_MENU["item_h"] == 28.0
    assert menu.ICON == CONTEXT_MENU["icon"] == 16.0
    assert menu.LABEL_H == 24.0          # text-xs 16/16 + py-1, not an item


def test_destructive_hover_alpha_is_themed_not_the_token():
    light = context_menu_table("light")
    dark = context_menu_table("dark")
    assert light["destructive_hover_bg"] == ("destructive", 0.10)
    assert dark["destructive_hover_bg"] == ("destructive", 0.20)
    assert light["destructive_ink"] == dark["destructive_ink"]


def test_hover_changes_the_ink_as_well_as_the_fill():
    """focus:bg-accent AND focus:text-accent-foreground. Invisible in dark,
    where both land on #fafafa — which is why it has to be measured in
    light."""
    t = context_menu_table("light")
    assert t["hover_bg"] == ("accent", 1.0)
    assert t["hover_ink"] != t["ink"]


def test_accent_foreground_resolves_to_the_measured_colour():
    """There is no `accent-foreground` token; the measured value is
    `secondary-foreground` in both themes."""
    import tokens as T
    name, a = CONTEXT_MENU["hover_ink"]
    assert a == 1.0
    assert T.LIGHT[name] == "#171717"      # oklch(0.205 0 0)
    assert T.DARK[name] == "#fafafa"       # oklch(0.985 0 0)


def test_dark_overrides_only_what_it_measured_differently():
    assert set(CONTEXT_MENU_DARK) <= set(CONTEXT_MENU)
    assert context_menu_table("light") == CONTEXT_MENU
    for k, v in CONTEXT_MENU.items():
        if k not in CONTEXT_MENU_DARK:
            assert context_menu_table("dark")[k] == v


def test_the_separator_is_full_bleed():
    """-mx-1 cancels the panel's p-1: measured x = panel.x, w = panel.w."""
    assert CONTEXT_MENU["sep_bleed"] is True
