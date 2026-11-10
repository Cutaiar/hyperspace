"""The Combobox's two pure halves: the filter and the intrinsic size.

No imgui context, no GL and no display, the way test_components.py,
test_box.py and test_flex.py are. That is possible because the only thing
either half needs from the renderer is a text width, and
`combobox_size(measure=...)` takes that as a function.

The expected numbers come from two oracles, and each test says which:

* `GOLDEN_SCORE` is `commandScore` out of the SHIPPED `cmdk@1.1.1`
  (node_modules/cmdk/dist/command-score.js), run under node. 59 pairs were
  compared while the port was written and every one agreed to 1e-12; these
  are the nine that pin the behaviour worth pinning.
* `BROWSER_*` is `tools/dkit/probe_react.js` against the real
  Popover + Command on the `?probe&open` route, both themes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import box as B
import comp_combobox as C
import tokens as T


# A fake text measurer: 7 px a character, which is close enough to Geist at
# 14px to keep the numbers readable and, more to the point, EXACT — so a
# width assertion below is arithmetic rather than a tolerance.
def mw(s, variant="regular", size=14.0):
    return 7.0 * len(s)


def items(*labels):
    return [C.Item(id=s.lower(), label=s) for s in labels]


SOLIDS = items("Dodecahedron", "Great Dodecahedron", "Dual Dodecahedron",
               "Tesseract", "16-cell")


# --------------------------------------------------------------------------
# filter_items
# --------------------------------------------------------------------------

def test_an_empty_query_returns_the_list_unchanged():
    """cmdk's sort returns early on `!search`: with no query there is no
    filtering AND no re-ranking, so the author's order is the order."""
    src = [C.heading("Solids"), *SOLIDS, C.sep(), *items("Cube")]
    out = C.filter_items(src, "")
    assert out == src
    assert out is not src          # a copy, so a caller cannot be surprised


@pytest.mark.parametrize("q", ["", "   ", "\t", "\n "])
def test_a_blank_query_is_not_a_query(q):
    assert C.filter_items(SOLIDS, q) == list(SOLIDS)


def test_no_matches_gives_an_empty_list():
    assert C.filter_items(SOLIDS, "zzzz") == []


def test_no_matches_drops_the_heading_too():
    """cmdk shows a group only when `filtered.groups` has it, i.e. when at
    least one of its rows scored above 0."""
    src = [C.heading("Solids"), *SOLIDS]
    assert C.filter_items(src, "zzzz") == []


@pytest.mark.parametrize("q", ["dod", "DOD", "Dod", "dOd"])
def test_the_match_is_case_insensitive(q):
    """Both sides go through `toLowerCase()`, so the SET of matches cannot
    depend on the case typed."""
    assert [i.id for i in C.filter_items(SOLIDS, q)] == \
        ["dodecahedron", "great dodecahedron", "dual dodecahedron"]


def test_ranking_puts_the_prefix_first():
    """The reason the score has to be ported rather than approximated: a
    substring test cannot order these three, and all three contain "dod".

    "Dodecahedron" starts with the query, so every character continues the
    run (1.0). The other two jump to a word boundary (0.9).
    """
    out = [i.id for i in C.filter_items(SOLIDS, "dod")]
    assert out[0] == "dodecahedron"
    assert set(out[1:]) == {"great dodecahedron", "dual dodecahedron"}


@pytest.mark.skip(reason="measured against the OLD Popover+Command recipe, which is not what shadcn ships; superseded by the re-measured tests at the end of this file")
def test_a_group_travels_as_a_block_ordered_by_its_best_row():
    """cmdk sorts items globally by score, then sorts the GROUPS by their
    best item's score — so a group never interleaves with another."""
    src = [
        C.heading("Stars"), *items("Small Stellated Dodecahedron"),
        C.heading("Platonic"), *items("Dodecahedron", "Cube"),
    ]
    out = C.filter_items(src, "dod")
    assert [i.kind for i in out] == ["label", "item", "label", "item"]
    # Platonic wins: its "Dodecahedron" is a perfect prefix run
    assert out[0].label == "Platonic"
    assert out[1].id == "dodecahedron"
    assert out[2].label == "Stars"
    assert out[3].id == "small stellated dodecahedron"


def test_rows_before_the_first_heading_are_their_own_group():
    """`<CommandGroup>` with no `heading` prop — the implicit group."""
    src = [*items("Cube"), C.heading("Stars"), *items("Stellated Cube")]
    out = C.filter_items(src, "cube")
    assert [getattr(i, "label", None) for i in out] == \
        ["Cube", "Stars", "Stellated Cube"]


def test_separators_survive_an_empty_query_and_vanish_under_one():
    """Measured in cmdk 1.1.1's own source: a CommandSeparator renders only
    while `!search` (unless `alwaysRender`)."""
    src = [*items("Cube"), C.sep(), *items("Dodecahedron")]
    assert [i.kind for i in C.filter_items(src, "")] == \
        ["item", "sep", "item"]
    assert [i.kind for i in C.filter_items(src, "c")] == ["item", "item"]


def test_a_disabled_row_still_matches():
    """`data-disabled` dims a row and stops it being chosen; it does not
    take it out of the filter, and cmdk's score knows nothing about it."""
    src = [C.Item(id="a", label="Cube", enabled=False)]
    assert [i.id for i in C.filter_items(src, "cube")] == ["a"]


def test_menu_items_are_accepted_too():
    """Every field is read through getattr, so a caller holding menu rows
    does not have to convert them."""
    import menu
    src = [menu.Item(id="a", label="Dodecahedron"),
           menu.Item(id="b", label="Cube")]
    assert [i.id for i in C.filter_items(src, "dod")] == ["a"]


# --------------------------------------------------------------------------
# combobox_size — the panel's intrinsic height, through box.wants
# --------------------------------------------------------------------------
# Straight off the probe: the `combobox.open` panel is 220 x 176 with a
# heading and three rows.
#
# The empty figure was RE-measured on the real Base UI component, which is
# not what the 112 above it came from: type a query that matches nothing and
# the whole panel is 319 x 36, because `data-empty:p-0` collapses the list's
# padding and the empty block (`py-2` on a 20px line) becomes the panel.
BROWSER_PANEL_H = 176.0
BROWSER_EMPTY_PANEL_H = 36.0
BROWSER_LIST_H = 132.0
BROWSER_FIELD_BLOCK_H = 36.0


@pytest.mark.skip(reason="measured against the OLD Popover+Command recipe, which is not what shadcn ships; superseded by the re-measured tests at the end of this file")
def test_the_panel_height_matches_the_browser():
    src = [C.heading("Planes"), *items("XY", "XZ", "XW")]
    _w, h = C.combobox_size(src, None, measure=mw)
    assert h == BROWSER_PANEL_H


@pytest.mark.skip(reason="measured against the OLD Popover+Command recipe, which is not what shadcn ships; superseded by the re-measured tests at the end of this file")
def test_the_panel_height_is_the_sum_the_browser_laid_out():
    """176 = Command p-1 (4) + the input wrapper's 36 + the list's 132 + 4,
    and the list's 132 = group p-1 (4) + heading 28 + 3 x 32 + 4. Asserted
    as the decomposition, so a wrong total says WHICH part moved."""
    src = [C.heading("Planes"), *items("XY", "XZ", "XW")]
    t = C.COMBOBOX
    assert C.list_content_h(src, t) == BROWSER_LIST_H
    assert t["group_pad"] * 2 + t["head_h"] + 3 * t["item_h"] == \
        BROWSER_LIST_H
    assert t["field_pad"] + t["field_h"] == BROWSER_FIELD_BLOCK_H
    assert (t["pad"] + BROWSER_FIELD_BLOCK_H + BROWSER_LIST_H
            + t["pad"]) == BROWSER_PANEL_H


def test_an_empty_list_is_the_browsers_thirty_six():
    """`ComboboxEmpty` is `py-2` on a 20px line box = 36, and `data-empty:p-0`
    takes the list's rails away, so the panel IS the empty block."""
    _w, h = C.combobox_size([], None, measure=mw, empty="Nothing found.")
    assert h == BROWSER_EMPTY_PANEL_H
    assert C.COMBOBOX["empty_h"] == BROWSER_EMPTY_PANEL_H


def test_a_query_that_filters_everything_out_shrinks_the_panel():
    """The two halves compose: filter first, size the result."""
    src = [C.heading("Planes"), *items("XY", "XZ", "XW")]
    shown = C.filter_items(src, "zzz")
    assert shown == []
    _w, h = C.combobox_size(shown, None, measure=mw, empty="Nothing found.")
    assert h == BROWSER_EMPTY_PANEL_H


@pytest.mark.skip(reason="measured against the OLD Popover+Command recipe, which is not what shadcn ships; superseded by the re-measured tests at the end of this file")
def test_a_long_list_clamps_at_max_h_72():
    """`max-h-72` = 288, confirmed in the computed style. Past it the panel
    stops growing and the list scrolls — which is why `combobox` hands
    `list_content_h` to `interact.scroll_area` rather than the clamp."""
    src = items(*[f"Item {i}" for i in range(40)])
    content = C.list_content_h(src, C.COMBOBOX)
    assert content == 40 * 32.0 + 2 * 4.0            # 1288, well past 288
    _w, h = C.combobox_size(src, None, measure=mw)
    assert h == 4.0 + 36.0 + 288.0 + 4.0
    assert C.COMBOBOX["list_max_h"] == 288.0
    # one row fewer than the clamp still grows
    short = items(*[f"Item {i}" for i in range(8)])
    assert C.combobox_size(short, None, measure=mw)[1] == \
        4.0 + 36.0 + (8 * 32.0 + 8.0) + 4.0


def test_the_intrinsic_width_comes_from_the_widest_row():
    """A row wants its text plus `pl-1.5 pr-8`, and the panel adds the
    list's `p-1`. The group contributes nothing: measured on the real
    component, the first row's x is the content's x + 4 and no more.

    Every number is read out of the table rather than written here, so a
    re-measurement moves the assertion with it.
    """
    t = C.combobox_table("light")
    src = items("XY", "Dodecahedron")
    w, _h = C.combobox_size(src, None, measure=mw)
    row = mw("Dodecahedron") + t["row_pad_x"] + t["row_pad_r"]
    assert w == row + 2 * t["pad"] + 2 * t["group_pad"]


def test_a_heading_can_be_the_widest_thing_in_the_panel():
    src = [C.heading("A very long group heading"), *items("XY")]
    w, _h = C.combobox_size(src, None, measure=mw)
    t = C.combobox_table("light")
    head = mw("A very long group heading") + 2 * t["head_pad_x"]
    assert w == head + 2 * t["pad"] + 2 * t["group_pad"]


def test_a_leading_icon_widens_a_row_by_the_icon_and_its_gap():
    plain = [C.Item(id="a", label="Cube")]
    iconed = [C.Item(id="a", label="Cube", icon="box")]
    wp = C.combobox_size(plain, None, measure=mw)[0]
    wi = C.combobox_size(iconed, None, measure=mw)[0]
    assert wi - wp == 16.0 + 8.0


def test_min_w_is_a_floor_not_a_width():
    src = items("XY")
    assert C.combobox_size(src, None, measure=mw, min_w=300.0)[0] == 300.0
    assert C.combobox_size(src, None, measure=mw, min_w=1.0)[0] > 1.0


def test_the_search_field_contributes_no_width():
    """It is `w-full`: measured, the 220px panel's width came entirely from
    the recipe's `w-[220px]`, with the field stretching to fill it."""
    t = C.combobox_table("light")
    narrow = C.combobox_size(items("X"), None, measure=mw)[0]
    assert narrow == (mw("X") + t["row_pad_x"] + t["row_pad_r"]
                      + 2 * t["pad"] + 2 * t["group_pad"])
    assert narrow < 220.0


@pytest.mark.skip(reason="measured against the OLD Popover+Command recipe, which is not what shadcn ships; superseded by the re-measured tests at the end of this file")
def test_a_separator_is_a_pixel_and_sits_outside_the_groups():
    """`-mx-1 h-px`: it is a child of the LIST, so it adds 1px and splits
    the rows into two groups, each with its own p-1 — 8 more px than one."""
    one = C.list_content_h(items("A", "B"), C.COMBOBOX)
    two = C.list_content_h([*items("A"), C.sep(), *items("B")], C.COMBOBOX)
    assert one == 2 * 32.0 + 8.0
    assert two == one + 1.0 + 8.0


# --------------------------------------------------------------------------
# the measured table itself
# --------------------------------------------------------------------------
# These are the numbers a reading of the classes would have got wrong, so
# they are pinned rather than trusted.

@pytest.mark.skip(reason="measured against the OLD Popover+Command recipe, which is not what shadcn ships; superseded by the re-measured tests at the end of this file")
def test_the_row_is_not_a_menu_row():
    """Every one of the five differs from menu.py's, which is the evidence
    that a Command list is not a dropdown menu with a search box."""
    import menu
    t = C.COMBOBOX
    # menu.py's item was 26 and its icon 14 when this was written; both
    # were wrong and have since been corrected to the browser's 28 and 16.
    # The rows still differ on every axis, which is the claim here.
    assert (t["item_h"], menu.ITEM_H) == (32.0, 28.0)
    assert (t["item_pad_x"], menu.ITEM_PAD_X) == (8.0, 6.0)
    assert (t["item_gap"], menu.GAP) == (8.0, 6.0)
    assert T.RADII[t["item_radius"]] == 6.0          # rounded-sm
    assert T.RADII["md"] == 8.0                      # menu.py's row radius
    assert t["check"] == menu.ICON == 16.0           # the one they share


def test_the_panel_chrome_is_the_menus():
    """Measured identical, so the reuse is stated as a test rather than as
    a comment that can rot."""
    t = C.COMBOBOX
    assert T.RADII[t["radius"]] == T.RADII["lg"] == 10.0
    assert t["bg"] == ("popover", 1.0)
    assert t["ring"] == ("foreground", 0.10)
    assert t["pad"] == menu_pad()
    # shadow-md, the same token the Select's popover and menu.py use
    assert T.SHADOW_MD == ((0.0, 4.0, 6.0, -1.0, 0.10),
                           (0.0, 2.0, 4.0, -2.0, 0.10))


def menu_pad():
    import menu
    return menu.PAD


def test_the_trigger_borrows_the_selects_measured_size():
    """A Button variant=outline size=default and a SelectTrigger measured
    identical at (32, rounded-lg), so there is no second size table."""
    assert T.SELECT_SIZES["default"] == (32.0, "lg")
    assert T.RADII["lg"] == 10.0
    # ...but NOT the Select's fills: light hovers here and does not there
    assert C.COMBOBOX["trigger_hover"] == ("muted", 1.0)
    assert T.SELECT["hover_bg"] == ("transparent", 1.0)
    # dark is the same pair for both
    assert T.SELECT_DARK["bg"] == C.COMBOBOX_DARK["trigger_bg"] == \
        ("input", 0.3)
    assert T.SELECT_DARK["hover_bg"] == C.COMBOBOX_DARK["trigger_hover"] == \
        ("input", 0.5)


def test_opening_the_panel_tints_the_trigger_in_light_only():
    """`aria-expanded:bg-muted` on the Button, measured with the pointer
    parked away: light #ffffff -> #f5f5f5 on open, dark unchanged because
    `dark:bg-input/30` wins. An asymmetry the class list does not show."""
    light, dark = C.combobox_table("light"), C.combobox_table("dark")
    assert light["trigger_bg"] != light["trigger_open"]
    assert dark["trigger_bg"] == dark["trigger_open"] == ("input", 0.3)


def test_the_triggers_border_token_differs_by_theme():
    """`border-border` light, `dark:border-input` dark. In LIGHT the two
    tokens are the same #e5e5e5, so no measurement can tell them apart; in
    dark they differ and the measured 0.15 alpha names `input`."""
    assert C.combobox_table("light")["trigger_border"] == ("border", 1.0)
    assert C.combobox_table("dark")["trigger_border"] == ("input", 1.0)
    assert T.LIGHT["border"] == T.LIGHT["input"] == "#e5e5e5"
    assert T.DARK["border"] != T.DARK["input"]
    assert T.DARK["input"] == "#ffffff26"       # the 0.15 that was measured


def test_the_search_field_is_tinted_in_both_themes():
    """`border-input/30 bg-input/30` is hard-coded on CommandInput, where
    tokens.INPUT is transparent in light and only reaches input/30 in
    dark."""
    light = C.combobox_table("light")
    dark = C.combobox_table("dark")
    assert light["field_bg"] == dark["field_bg"] == ("input", 0.3)
    assert light["field_border"] == dark["field_border"] == ("input", 0.3)
    assert T.INPUT["bg"] == ("transparent", 1.0)
    assert T.INPUT_DARK["bg"] == ("input", 0.3)


def test_the_search_placeholder_is_not_muted_foreground():
    """Chromium's default placeholder — currentColor at half alpha —
    measured, because CommandInput carries no `placeholder:` class at all.
    A plain Input's IS muted-foreground, on the same page."""
    assert C.COMBOBOX["field_placeholder"] == ("foreground", 0.5)
    assert T.INPUT["placeholder"] == ("muted-foreground", 1.0)


def test_the_empty_state_is_muted_after_all():
    """It WAS `popover-foreground` on the Popover+Command recipe, and this
    test pinned that correctly. The real Base UI `ComboboxEmpty` carries
    `text-muted-foreground`, measured as `oklch(0.556 0 0)` — which is what
    muted-foreground resolves to in light.

    Kept as a flipped assertion rather than deleted, because the thing worth
    remembering is that a correct measurement of the wrong component is
    still wrong."""
    assert C.COMBOBOX["empty_ink"] == ("muted-foreground", 1.0)
    assert T.rgba("muted-foreground", theme=T.LIGHT)[:3] != \
        T.rgba("popover-foreground", theme=T.LIGHT)[:3]


def test_the_triggers_chevron_is_where_the_browser_puts_it():
    """The chevron's RIGHT edge is 8.203 in from the trigger's right, and it
    is drawn in muted-foreground at FULL strength.

    This replaces an assertion that `field_icon_x == 1.0 + T.SPACE[2]`,
    which is RETRO row 27's trap in miniature: an arithmetic identity over
    the token, which cannot fail and says nothing about the browser. Worse,
    the number it modelled belonged to the leading magnifier of the
    Popover+Command search field - a component this has not been since that
    recipe was replaced - so it was a correct identity over a dead token.

    Measured on the real Base UI component at two widths, 200 and 320, and
    constant at both: svg 16x16 with its right edge at trigger_right -
    8.203, `oklch(0.556 0 0)` at `opacity: 1`, which is muted-foreground.
    """
    t = C.COMBOBOX
    assert t["field_chevron_right"] == 8.203
    assert t["field_icon"] == 16.0
    assert t["field_icon_ink"] == ("muted-foreground", 1.0)
    # disabled dims it twice: the group's opacity-50 AND the chevron's own
    # button's. Measured 0.25 of full ink, not 0.5.
    assert t["field_icon_disabled_opacity"] == 0.5
    # full strength, and that is the point: #737373, level 115
    assert T.rgba("muted-foreground", theme=T.LIGHT)[:3] == \
        tuple(c / 255.0 for c in (0x73, 0x73, 0x73))
    # the line box is 20 in a 32 field, so the glyphs sit 6 down
    assert (t["field_h"] - t["field_line"]) / 2.0 == 6.0
    # the dead tokens are gone, not merely unused
    assert "field_icon_x" not in t
    assert "field_text_x" not in t


# --------------------------------------------------------------------------
# placement — Radix rounds its own transform
# --------------------------------------------------------------------------
# (trigger bottom, placed panel y), swept across eight sub-pixel trigger
# positions in Chromium. sideOffset is 4 throughout; the OBSERVED gap runs
# 3.625 .. 4.5, which is the whole point.
BROWSER_PLACEMENT = [
    (2661.375, 2665.0),
    (2661.5, 2666.0),
    (2661.625, 2666.0),
    (2661.75, 2666.0),
    (2661.875, 2666.0),
    (2662.0, 2666.0),
    (2662.125, 2666.0),
    (2662.25, 2666.0),
]


@pytest.mark.skip(reason="measured against the OLD Popover+Command recipe, which is not what shadcn ships; superseded by the re-measured tests at the end of this file")
@pytest.mark.parametrize("bottom,placed", BROWSER_PLACEMENT)
def test_the_panel_lands_on_a_whole_pixel(bottom, placed):
    anchor = B.Rect(24.0, bottom - 32.0, 220.0, 32.0)
    avail = B.Rect(0.0, 0.0, 1200.0, 10000.0)
    at, side = B.place_popover(anchor, 220.0, 176.0, avail, side="bottom",
                               align=C.COMBOBOX["align"],
                               offset=C.COMBOBOX["side_offset"])
    assert side == "bottom"
    assert C.round_px(at.y) == placed


@pytest.mark.skip(reason="measured against the OLD Popover+Command recipe, which is not what shadcn ships; superseded by the re-measured tests at the end of this file")
def test_the_observed_gap_is_not_the_declared_offset():
    """A reading of `sideOffset={4}` gets this wrong on any trigger that
    does not sit on a whole pixel, which on a 1/64 px layout grid is
    most of them."""
    gaps = []
    for bottom, placed in BROWSER_PLACEMENT:
        gaps.append(placed - bottom)
    assert min(gaps) == pytest.approx(3.625)
    assert max(gaps) == pytest.approx(4.5)
    assert C.COMBOBOX["side_offset"] == 4.0


def test_round_px_is_the_browsers_rounding_not_pythons():
    """Math.round is half-UP; Python's round is banker's. They disagree on
    every odd .5, and a popover under a trigger lands on one often enough
    to matter."""
    assert C.round_px(2666.5) == 2667.0
    assert round(2666.5) == 2666          # ...which is what NOT to use
    assert C.round_px(2665.5) == 2666.0
    assert C.round_px(2665.375) == 2665.0
    assert C.round_px(-0.5) == 0.0


# --------------------------------------------------------------------------
# the one state a Command list has
# --------------------------------------------------------------------------

def test_the_first_matching_row_is_the_one_cmdk_preselects():
    """Measured: with an empty query row 0 carries `data-selected`, and
    under a query it is the first row that MATCHES - which after ranking is
    just index 0 of the filtered list."""
    src = [C.heading("Planes"), *items("XY", "XZ", "XW")]
    shown = C.filter_items(src, "xw")
    rows = [i for i, it in enumerate(shown) if it.kind == "item"]
    assert shown[rows[0]].id == "xw"


# --------------------------------------------------------------------------
# Re-measured against the REAL component
# --------------------------------------------------------------------------
# The kit first built the old Popover+Command recipe, because the brief said
# shadcn had no combobox component. It does: `combobox.tsx`, built on Base
# UI, whose `ComboboxInput` IS the trigger. Everything below was measured on
# that, and supersedes the numbers above where the two disagree.


def test_the_match_is_a_substring_case_insensitive():
    """Measured by typing into the real component and reading its rows:

        "dodec" -> Dodecahedron, Great Dodecahedron
        "DODEC" -> the same two
        "ant"   -> Grand antiprism      (not anchored to the start)
        "dcd"   -> nothing
        "grt"   -> nothing
        "tsrct" -> nothing

    The last three decide it: every one of them MATCHES under cmdk's
    subsequence scoring, and the component returns none of them.
    """
    items = [C.Item(id=n, label=n) for n in
             ("Dodecahedron", "Great Dodecahedron", "Tesseract",
              "Grand antiprism")]
    got = lambda q: [i.label for i in C.filter_items(items, q)]
    assert got("dodec") == ["Dodecahedron", "Great Dodecahedron"]
    assert got("DODEC") == ["Dodecahedron", "Great Dodecahedron"]
    assert got("ant") == ["Grand antiprism"]
    for q in ("dcd", "grt", "tsrct"):
        assert got(q) == [], f"{q!r} matched; that is the cmdk rule, not this"


def test_an_empty_query_keeps_the_authors_order():
    items = [C.Item(id=n, label=n) for n in ("Zeta", "Alpha", "Mu")]
    assert [i.label for i in C.filter_items(items, "")] == ["Zeta", "Alpha", "Mu"]
    assert [i.label for i in C.filter_items(items, "   ")] == ["Zeta", "Alpha", "Mu"]


def test_the_cmdk_scorer_lives_with_the_component_that_wants_it():
    """It is not the Combobox's rule and it is no longer in the Combobox's
    file. The port is exact - verified against the shipped JavaScript over
    382 pairs - and it was answering a question nobody asked, which is
    RETRO row 3. `comp_command.py` is where the Command palette will find
    it.

    This asserts the split rather than the code: the scorer is gone from
    here, present there, and the Combobox's own filter is the substring
    one.
    """
    import comp_command
    assert not hasattr(C, "command_score")
    assert not hasattr(C, "rank_items_cmdk")
    assert hasattr(comp_command, "command_score")
    assert hasattr(comp_command, "rank_items_cmdk")
    # and the rule this component does use is `contains`, not a subsequence
    assert C.filter_items(items("Dodecahedron"), "dcd") == []
    assert len(C.filter_items(items("Dodecahedron"), "dec")) == 1
def test_the_trigger_is_an_input_not_a_button():
    """The whole shape of the component. Measured 320x32, radius 10, a 1px
    `input` border, transparent in light and `input/30` in dark - which is
    tokens.INPUT - with pl 10 and pr 6."""
    t = C.COMBOBOX
    assert t["input_pad_l"] == 10.0 and t["input_pad_r"] == 6.0
    assert t["side_offset"] == 6.0        # not the Select's 4


def test_the_panel_rows_are_menu_rows():
    """Measured h 28, rounded-md, px 6 - every one equal to menu.py's, so a
    Combobox panel is a menu panel with an input above it."""
    import menu as M
    t = C.COMBOBOX
    assert t["item_h"] == M.ITEM_H == 28.0
    assert T.RADII[t["row_radius"]] == T.RADII["md"] == 8.0
    assert t["row_pad_x"] == M.ITEM_PAD_X == 6.0


# --------------------------------------------------------------------------
# the row, re-measured on the REAL combobox-item
# --------------------------------------------------------------------------
# `node /tmp/cb.js` against `?probe`, `[data-slot="combobox-item"]`:
#
#     content   319 x 120 @ 25,2531   radius 10   padding 0
#     list      319 x 120 @ 25,2531   padding 4   max-height 252px
#               offsetWidth - clientWidth == 0   <- no scrollbar, ever
#     item[0]   311 x  28 @ 29,2535   radius 8    padding 4/32/4/6
#     indicator span 16 wide, 287 from the row's left, 8 from its right
#
# Three of those the kit had wrong: it drew the row with 8 of padding on
# BOTH sides (so the check crowded the row's edge and a long label ran
# under it), rounded it by 6 rather than 8, and nested a p-1 group inside
# the p-1 list so every row was inset 8 instead of 4.
BROWSER_ITEM = {
    "content_w": 319.0, "list_pad": 4.0, "item_w": 311.0, "item_h": 28.0,
    "item_radius": 8.0, "pad_t": 4.0, "pad_r": 32.0, "pad_b": 4.0,
    "pad_l": 6.0, "indicator_w": 16.0, "indicator_right": 8.0,
    "list_max_h": 252.0, "scrollbar_w": 0.0,
}


def test_a_row_is_inset_from_the_panel_by_the_lists_padding_alone():
    """311 = 319 - 2x4. The group adds nothing."""
    t = C.combobox_table("light")
    inset = (BROWSER_ITEM["content_w"] - BROWSER_ITEM["item_w"]) / 2
    assert inset == BROWSER_ITEM["list_pad"]
    assert t["pad"] + t["group_pad"] == inset


def test_the_rows_padding_is_six_left_and_thirty_two_right():
    """`pl-1.5 pr-8`. The asymmetry is the point: the right pad is what
    reserves room for the ItemIndicator, which is absolutely positioned and
    so takes no space of its own."""
    t = C.combobox_table("light")
    assert t["row_pad_x"] == BROWSER_ITEM["pad_l"]
    assert t["row_pad_r"] == BROWSER_ITEM["pad_r"]
    assert t["row_pad_r"] > t["row_pad_x"]


def test_the_check_sits_eight_from_the_rows_right_edge():
    """`absolute right-2` on a `size-4` span - the indicator's RIGHT edge is
    8 in, so a 16px glyph starts 24 in. The kit placed it at
    `row.right - padding - 16` with padding 8, which put it 8 from the edge
    by coincidence of the old numbers and would have drifted the moment
    either moved."""
    t = C.combobox_table("light")
    assert t["check"] == BROWSER_ITEM["indicator_w"]
    assert t["check_gap"] == BROWSER_ITEM["indicator_right"]
    row_w = BROWSER_ITEM["item_w"]
    icon_x = row_w - t["check_gap"] - t["check"]
    assert icon_x == 311.0 - 24.0            # the measured 287
    assert row_w - (icon_x + t["check"]) == BROWSER_ITEM["indicator_right"]


def test_a_label_stops_at_the_right_padding_not_at_the_check():
    """The reserved strip is `pr-8` = 32 whether or not the row is checked,
    because the indicator is out of flow. A label clipped at the CHECK
    instead would reflow the moment a row became selected."""
    t = C.combobox_table("light")
    row_w = BROWSER_ITEM["item_w"]
    avail = row_w - t["row_pad_r"] - t["row_pad_x"]
    assert avail == 311.0 - 32.0 - 6.0
    # and that is strictly less than the room up to the check, so the label
    # can never touch it
    assert t["row_pad_r"] > t["check_gap"] + t["check"] - 8.0


def test_the_row_radius_is_rounded_md():
    t = C.combobox_table("light")
    assert T.RADII[t["row_radius"]] == BROWSER_ITEM["item_radius"]


def test_the_list_clamps_rather_than_growing():
    """`max-height: 252px` with `overflow-y: auto`. Sixteen rows measured
    456 of content in a 252 box - it scrolls, it does not grow.

    And 252 is the PADDED list's height, which is the panel's. Measured on
    `combobox.tight`, sixteen rows: the content element AND the list both
    report 319x252, with `scrollHeight` 456 and `clientHeight` 252 - so the
    `p-1` rails are INSIDE the clamp, not added to it.

    This assertion used to read `h == list_max_h + 2 * pad`, i.e. 260. It
    asked the source for the number and still got the answer wrong, because
    it had the wrong model of what the number clamps: the rows, rather than
    the box the browser measured. 252 is what Chromium paints.
    """
    t = C.combobox_table("light")
    assert t["list_max_h"] == BROWSER_ITEM["list_max_h"]
    tall = items(*[f"Row {i}" for i in range(16)])
    _w, h = C.combobox_size(tall, None, measure=mw)
    assert C.list_content_h(tall, t) > t["list_max_h"]
    assert h == t["list_max_h"]
    # and a list SHORT of the clamp is still its content plus the rails
    short = items(*[f"Row {i}" for i in range(4)])
    assert C.combobox_size(short, None, measure=mw)[1] == \
        C.list_content_h(short, t) + 2 * t["pad"]


# --------------------------------------------------------------------------
# which row an open highlights - the table in `resolve_open`
# --------------------------------------------------------------------------
# Driven on `?probe`'s `combobox.many` (sixteen rows, `defaultValue="Gamma"`
# at index 2) and `combobox.kb` (six rows, no value), reading
# `data-highlighted` off the DOM after each gesture:
#
#                        combobox.many        combobox.kb
#     click the field    Gamma   (idx 2)      none
#     click the chevron  Gamma   (idx 2)      none
#     ArrowDown          Gamma   (idx 2)      Alpha  (first)
#     ArrowUp            Gamma   (idx 2)      Zeta   (last)
#     typing             none                 none
#
# The left-hand column is the one the kit got wrong: it opened with nothing
# highlighted on a click and with the first / last row on an arrow, in every
# case, because the model was measured on the block that holds no value.
BROWSER_OPEN = {
    ("click", True): 2, ("chevron", True): 2,
    ("down", True): 2, ("up", True): 2, ("type", True): None,
    ("click", False): None, ("chevron", False): None,
    ("down", False): 0, ("up", False): 5, ("type", False): None,
}


def _sixteen():
    src = items(*["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta",
                  "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu",
                  "Xi", "Omicron", "Pi"])
    return src, list(range(len(src)))


def _six():
    src = items(*["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"])
    return src, list(range(len(src)))


WANT = {"click": C.SEL_NONE, "chevron": C.SEL_NONE, "down": C.SEL_FIRST,
        "up": C.SEL_LAST, "type": None}


def test_an_open_lands_on_the_committed_row_whatever_opened_it():
    """The left column of BROWSER_OPEN: with a value, all four gestures
    land on its row. The kit opened on none / first / last instead."""
    src, rows = _sixteen()
    for gesture in ("click", "chevron", "down", "up", "type"):
        got = C.resolve_open(WANT[gesture], src, rows, "Gamma")
        assert got == BROWSER_OPEN[(gesture, True)], \
            f"{gesture} with a value: {got}"


def test_with_no_committed_row_the_gesture_decides():
    """The right column: none for a pointer, the first row for ArrowDown,
    the LAST for ArrowUp. This half cannot be reached by driving the app -
    the dashboard's only Combobox holds a value that matches a row - which
    is why the rule is a function and not four lines inside `combobox`."""
    src, rows = _six()
    for gesture in ("click", "chevron", "down", "up", "type"):
        got = C.resolve_open(WANT[gesture], src, rows, "")
        assert got == BROWSER_OPEN[(gesture, False)], \
            f"{gesture} with no value: {got}"


def test_a_value_that_matches_nothing_shown_falls_back_to_the_gesture():
    """After a filter the committed row may not be on screen. Measured:
    query `et` on `combobox.many` (value Gamma, which does not match)
    leaves nothing highlighted, and ArrowDown then takes `Beta`, the first
    MATCH - not Gamma's old index."""
    src, _ = _sixteen()
    shown = C.filter_items(src, "et")
    rows = [i for i, it in enumerate(shown) if C._is_row(it)]
    assert shown and all(C._k(it, "label", "") != "Gamma" for it in shown)
    assert C.resolve_open(C.SEL_FIRST, shown, rows, "Gamma") == 0
    assert C.resolve_open(C.SEL_NONE, shown, rows, "Gamma") is None


def test_an_empty_list_highlights_nothing_whatever_was_asked_for():
    assert C.resolve_open(C.SEL_FIRST, [], [], "Gamma") is None
    assert C.resolve_open(C.SEL_LAST, [], [], "") is None


def test_the_highlighted_row_on_open_is_the_row_that_carries_the_check():
    """Measured: `data-highlighted` and the rendered ItemIndicator are on
    the SAME row (item 2) when `combobox.many` opens. They are found by one
    rule here so they cannot drift apart."""
    src, rows = _sixteen()
    at = C.resolve_open(C.SEL_NONE, src, rows, "Gamma")
    assert C._k(src[rows[at]], "label", "") == "Gamma"
    # an explicit `checked` is honoured as well, exactly as `_row` honours
    # it: a caller that ticks a row itself gets that row highlighted, with
    # no label to match on
    src2 = [C.Item(id="a", label="A"), C.Item(id="b", label="B", checked=True)]
    assert C.resolve_open(C.SEL_NONE, src2, [0, 1], "") == 1


# --------------------------------------------------------------------------
# the group heading and the separator, re-measured on combobox.tsx
# --------------------------------------------------------------------------
# `?probe`'s `combobox.grp` block - a ComboboxGroup holding a ComboboxLabel,
# an item, a ComboboxSeparator and a second item:
#
#     content  319 x 101 @ 25,2750    padding 0
#     list     319 x 101 @ 25,2750    padding 4
#     group    311 x  93 @ 29,2754    padding 0   margin 0
#     label    311 x  28 @ 29,2754    padding 6px 8px   12px   weight 400
#     item[0]  311 x  28 @ 29,2782
#     sep      319 x   1 @ 25,2814    margin 4px -4px
#     item[1]  311 x  28 @ 29,2819
#
# Two of those the kit had from `command.tsx` - the OLD Popover+Command
# recipe - rather than from `combobox.tsx`: the heading's weight (that one
# is `font-medium`, this one has no weight class at all) and the
# separator's margin block (that one is `-mx-1 h-px bg-border`, this one is
# `-mx-1 my-1 h-px bg-border`). Same failure as the empty block's 68px: an
# exact measurement of the wrong component.
BROWSER_GRP = {
    "group_h": 93.0, "panel_h": 101.0, "label_h": 28.0, "label_weight": 400,
    "label_pad_x": 8.0, "label_font": 12.0, "item_h": 28.0,
    "sep_h": 1.0, "sep_margin": 4.0, "sep_w": 319.0, "content_w": 319.0,
}


def test_the_group_heading_is_regular_weight_not_medium():
    """Measured `font-weight: 400` on `[data-slot=combobox-label]`.
    `ComboboxLabel` is `px-2 py-1.5 text-xs text-muted-foreground` and
    declares no weight, so it inherits the panel's. The kit carried
    `medium`, which is `command.tsx`'s CommandGroup heading."""
    t = C.combobox_table("light")
    # asked of the source: the kit's variant names map to Geist's face
    # files, and the one Chromium reports as 400 is the Regular face.
    import draw as D
    faces = dict(D.FACE_FILES)
    assert faces[t["head_weight"]] == "Geist-Regular.ttf", \
        f"{t['head_weight']} is not the 400 face"
    assert faces["medium"] == "Geist-Medium.ttf"      # i.e. 500, which it is not
    assert BROWSER_GRP["label_weight"] == 400
    assert t["head_h"] == BROWSER_GRP["label_h"]
    assert t["head_pad_x"] == BROWSER_GRP["label_pad_x"]
    assert t["head_font"] == BROWSER_GRP["label_font"]


def test_a_separator_carries_four_pixels_above_and_below():
    """`my-1`, measured as `margin: 4px -4px`. The kit gave it one pixel of
    height and no margin, so two rows either side of a separator sat 8px
    closer together than the browser draws them."""
    t = C.combobox_table("light")
    assert t["sep_my"] == BROWSER_GRP["sep_margin"]
    # the rows the probe block holds, in the probe block's order
    src = [C.heading("Planes"), C.Item(id="a", label="Alpha"), C.sep(),
           C.Item(id="b", label="Beta")]
    assert C.list_content_h(src, t) == BROWSER_GRP["group_h"]
    _w, h = C.combobox_size(src, None, measure=mw)
    assert h == BROWSER_GRP["panel_h"]


def test_the_separators_rule_is_centred_in_its_margin_block():
    """One pixel of ink, four above it and four below - not a 9px rule and
    not a rule flush to the row above. Asked of the placed tree, which is
    what the widget draws from."""
    t = C.combobox_table("light")
    src = [C.Item(id="a", label="Alpha"), C.sep(), C.Item(id="b", label="B")]
    node = C._rows_node(src, mw, t)
    place = B.lay(node, B.Rect(0.0, 0.0, 311.0, C.list_content_h(src, t)))
    row0, sep, row1 = place[("row", 0)], place[("sep", 1)], place[("row", 2)]
    assert sep.h == t["sep_h"] + 2 * t["sep_my"]
    # the ink, where `combobox` draws it
    ink_y = sep.y + t["sep_my"]
    assert ink_y - (row0.y + row0.h) == BROWSER_GRP["sep_margin"]
    assert row1.y - (ink_y + t["sep_h"]) == BROWSER_GRP["sep_margin"]
    # and `-mx-1` reaches it out over the list's own p-1, so the rule the
    # widget draws is the PANEL's full width: measured 319 against a 311
    # row in a 319 panel
    assert sep.w + 2 * t["pad"] == BROWSER_GRP["sep_w"]
    assert sep.w == BROWSER_GRP["sep_w"] - 2 * t["pad"]


# --------------------------------------------------------------------------
# the panel chrome is menu.py's, and may only stay so while the tokens agree
# --------------------------------------------------------------------------

def test_panel_chrome_is_menus():
    """`_panel_chrome` delegates to `menu.panel_chrome`, which hardcodes the
    popover fill, the foreground/10 ring and `rounded-lg`. COMBOBOX still
    declares all three, and the delegation is sound only while they say the
    same thing - so this asserts the equivalence the delegation assumes
    rather than leaving it to the comment that claims it.

    If a future shadcn moves the Combobox's panel off the menu's chrome,
    this fails and `_panel_chrome` has to grow its own body back.
    """
    import menu as M
    assert C.COMBOBOX["radius"] == "lg"
    assert C.COMBOBOX["bg"] == ("popover", 1.0)
    assert C.COMBOBOX["ring"] == ("foreground", 0.10)
    # and menu.py draws exactly those
    assert M.PAD == 4.0
    src = __import__("inspect").getsource(M.panel_chrome)
    assert 'ui.col("popover", a)' in src
    assert 'ui.col("foreground", 0.10 * a)' in src
    assert 'T.RADII["lg"]' in src
