"""Combobox: a Popover whose content is a Command.

**There is no `combobox` component in shadcn.** It is a recipe — a
`Popover` (`src/components/ui/popover.tsx`) holding a `Command`
(`src/components/ui/command.tsx`, which wraps `cmdk`) — so this module is
the recipe, not a port of one file.

Everything numeric below came out of Chromium, off the `combobox.open`
probe block in both themes, not out of a reading of the Tailwind classes.
Getting the oracle to hold still was half the work and is worth recording:
the route's forced-open *modal* Select puts `pointer-events: none` on
`#root`, and its stealing focus at mount fires the Popover's own
`onFocusOutside`, so the Popover the route declares `defaultOpen` is
**already shut** by the time anything measures it. Escape leaves a layer
behind that dismisses the Popover again one frame after it opens. What
works is closing the Select by *choosing an item* — a real interaction,
after which Radix unmounts its layer and hands focus back.

What the measurements said, and what surprised me
-------------------------------------------------

* **The panel's chrome is byte-identical to `menu.py`'s.** radius
  `rounded-lg` = 10, `bg-popover`, a 1px `ring-foreground/10` (measured
  `oklab(0.145 0 0 / 0.1)` light, `oklab(0.985 0 0 / 0.1)` dark) and
  `shadow-md`'s two layers, `0 4 6 -1 / .1` + `0 2 4 -2 / .1`, which is
  `tokens.SHADOW_MD` exactly. The panel padding comes out at 4 as well —
  but for a different reason: a `PopoverContent` is `p-2.5` (10), the
  recipe overrides it to `p-0`, and the `Command` inside supplies `p-1`.
  Same number, different owner. (The `Command` also carries
  `rounded-xl!` = 14 inside the panel's 10, which is invisible: both are
  `bg-popover`, and a 14px corner cuts away only what the 10px one already
  painted.) `menu.popup`'s panel chrome is reproduced here rather than
  called, for the reason under PANEL CHROME below.

* **The row is NOT a menu row.** This is where the two components really
  part company, and every number differs:

        menu.py item          CommandItem (measured)
        h       26            32          (py-1.5 on a 20px line box)
        pad_x    6 (px-1.5)    8          (px-2)
        radius   8 (md)        6          (rounded-sm)
        gap      6 (gap-1.5)   8          (gap-2)
        check   left,  14     right, 16
        fill    accent        muted

  `accent` and `muted` are the *same* value in both of this project's
  themes (#f5f5f5 / #262626), so the fill is interchangeable — but the
  class is `data-selected:bg-muted`, so that is the token named here.

* **Hover and keyboard selection are ONE state, not two.** This is the
  thing I expected to differ and it does not: hovering a row sets
  `data-selected="true"` on it and *clears* it from whichever row had it,
  and ArrowDown moves the same attribute. cmdk selects on `onPointerMove`,
  so a Command list has exactly one highlight and the mouse and the
  keyboard take turns owning it. There is no second hover tint to measure.

* **The highlight does not animate.** `transition-duration` on a
  `command-item` measures **0s** — there is no `transition-colors` on it or
  on any ancestor. So the row highlight SNAPS, against the kit's usual
  habit of easing chrome out of `ease.Anim`. The trigger does ease
  (`transition-all` 150ms on `cubic-bezier(.4,0,.2,1)`) and the panel fades
  in over 100ms (`animation: enter 0.1s`), which is what `menu.popup`
  already does.

* **cmdk pre-selects the first matching row.** At rest, with an empty
  query, row 0 carries `data-selected`; type a query and the first row that
  *matches* carries it.

* **The search field is tinted in light, where a plain Input is not.**
  `CommandInput` hard-codes `border-input/30 bg-input/30` for both themes:
  measured `oklab(0.922 0 0 / 0.3)` light and `oklab(1 0 0 / 0.045)` dark
  (dark `input` is #ffffff26 ≈ .149, and .149 × .3 = .0447). `tokens.INPUT`
  has a *transparent* light background and reaches `input/30` only in dark,
  so this is not `input_table()` with a different height.

* **The search field has no focus ring and no focus border.** Measured
  focused: box-shadow all-transparent, border unchanged. `InputGroup` rings
  on `has-[[data-slot=input-group-control]:focus-visible]` while
  `CommandPrimitive.Input` carries `data-slot="command-input"`, so the
  selector never matches. There is nothing to animate.

* **The search placeholder is `foreground/50`, not `muted-foreground`.**
  Measured `oklab(0.145 0 0 / 0.5)` light and `oklab(0.985 0 0 / 0.5)`
  dark, against a plain `Input`'s `oklch(0.556 0 0)` = `muted-foreground`
  on the same page. `CommandPrimitive.Input` has no `placeholder:` class at
  all, so what is measured is **Chromium's default placeholder** —
  currentColor at half alpha. A token would have been the wrong guess.

* **`CommandEmpty`'s ink is `popover-foreground`, not muted.** `py-6
  text-center text-sm`, no colour class, so it inherits the panel's full
  strength foreground. 68 tall = 24 + 20 + 24.

* **Radix ROUNDS the placed panel to a whole pixel.** `sideOffset` is 4,
  but with the trigger's bottom at 2661.375 the panel landed at 2665 — a
  gap of 3.625. Swept across eight sub-pixel trigger positions the rule is
  exactly `round(anchor.bottom + 4)`: 2665.375 → 2665, 2665.5 → 2666,
  2666.25 → 2666. So the *declared* offset is 4 and the *observed* gap runs
  3.625 … 4.5. That is Radix rounding its own transform, a different thing
  from the kit's "Chromium pixel-snaps what it paints" rule: here the
  layout itself is integral, so `place_popover`'s result is rounded rather
  than only its paint.

* **The panel is as wide as its trigger**, because the recipe puts the same
  `w-[220px]` on both. Which also means `align` could not be measured:
  start and center are indistinguishable at equal widths. `popover.tsx`
  defaults to `align="center"`, and that is what is used here.

* **The list hides its scrollbar.** `max-h-72` = 288 (confirmed in the
  computed style) with `overflow-y: auto`, and `scrollbar-width: none`
  measured on the list — the gutter is 0 and a row stays 204 wide when the
  content overflows. The kit draws `interact.scroll_area`'s overlay thumb
  anyway: a deliberate deviation, recorded because an invisible affordance
  is worse than a 10px one that takes no layout space (Radix's overlays its
  viewport, so the geometry is unchanged either way).

* **The trigger is a Button, not a SelectTrigger**, and the difference is
  real in light. Measured `Button variant="outline" size="default"`: h 32,
  `rounded-lg` 10, px-2.5 both sides (a Select is px-2.5 / pr-2), text 14
  at weight **500**, `justify-between`, `gap-1.5`. Light: `bg-background`
  #ffffff at rest and `bg-muted` #f5f5f5 hovered — where `tokens.SELECT`
  records, correctly for a Select, *no light hover tint at all*. Dark is
  `SELECT_DARK` exactly: `input/30` → `input/50`.

* **Opening the panel tints the trigger in light and NOT in dark.** The
  Button carries `aria-expanded:bg-muted`, and a `PopoverTrigger` is
  `aria-expanded="true"` while its panel is up. Measured with the pointer
  parked off the control: light goes #ffffff → #f5f5f5 on open, dark stays
  at `input/30` and only moves on hover, because `dark:bg-input/30` wins.
  So the open state is a fill in one theme and nothing at all in the other
  — not something a reading of the class list produces.

* **A mouse-opened trigger has no focus ring**, measured `box-shadow:
  none` in both themes, open and closed, hovered and not. Its
  `focus-visible:ring-3` needs keyboard focus, which this kit does not
  route yet (the gap `interact.switch` already records). `interact.select`
  drives its ring off `open_`; on this control that would paint a ring the
  browser does not. So `focus_f` is 0 here and the open state is the fill
  above.

Where a value equals one the kit already has, it says so rather than
restating it: `T.SELECT_SIZES` gives the trigger's (height, radius) — the
Button and the SelectTrigger measured identical there — `T.SHADOW_MD` the
panel's shadow, `T.RADII` every corner and `T.SPACE` every inset.

What could NOT be measured here is flagged `# DERIVED` or `# NOT MEASURED`
in the table: the trigger's chevron (the probe's Button carries no icon), a
row's leading icon, a checked row's check, a disabled row, and a separator
— the probe block has none of those. Each is derived from the class it is
declared with, and says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

from imgui_bundle import imgui

import box as B
import draw as D
import tokens as T
from ease import mix

# --------------------------------------------------------------------------
# the measured table
# --------------------------------------------------------------------------
#
# (token, alpha) pairs multiply, exactly as tokens.rgba() does, so
# ("input", 0.3) is Tailwind's `bg-input/30` over a dark `input` that is
# itself #ffffff26. Lengths are CSS px at dpr 1.

COMBOBOX = {
    # ---- trigger: Button variant=outline, size=default ------------------
    # Its (height, radius key) is T.SELECT_SIZES, NOT a second table: the
    # Button and the SelectTrigger measured identical there (32, rounded-lg
    # = 10). Only `default` is measured; `sm` is the Select's, borrowed.
    "trigger_pad_x": T.SPACE[2.5],        # px-2.5 = 10, BOTH sides
    "trigger_font": 14.0,                 # text-sm
    "trigger_weight": "medium",           # font-medium = 500  (Select: 400)
    "trigger_gap": T.SPACE[1.5],          # gap-1.5 = 6
    "trigger_bg": ("background", 1.0),    # light bg-background, opaque white
    "trigger_hover": ("muted", 1.0),      # light DOES tint; a Select's does not
    # `aria-expanded:bg-muted`: in LIGHT the trigger is tinted the whole
    # time its panel is open, hovered or not. In dark it is not — measured,
    # `dark:bg-input/30` wins and the open trigger is byte-identical to the
    # closed one. An asymmetry no reading of the class list produces.
    "trigger_open": ("muted", 1.0),
    # `border-border` in light and `dark:border-input` in dark. The two
    # tokens are the SAME #e5e5e5 in light, so the measurement cannot tell
    # them apart there; in dark it can, and says input: measured
    # `oklch(1 0 0 / 0.15)` is #ffffff26 (input), not #ffffff1a (border).
    "trigger_border": ("border", 1.0),
    # NOT MEASURED, and deliberately NOT drawn: `focus-visible:ring-3
    # ring-ring/50` needs keyboard focus, which this kit does not route yet
    # (the same gap interact.switch records). A mouse-opened trigger was
    # measured with `box-shadow: none` in both themes and at every state
    # below, so `combobox` passes focus_f=0 and the open state is a FILL
    # change, not a ring. The entry is kept because draw.field wants one.
    "trigger_ring": ("ring", 0.5),
    # DERIVED, not measured — the probe's trigger carries no icon. The
    # recipe's is `<ChevronsUpDownIcon className="opacity-50"/>`, 16px by
    # `[&_svg:not([class*='size-'])]:size-4`, and `justify-between` puts its
    # right edge on the content box's, i.e. border 1 + pr 10 in. The glyph
    # `chevrons-up-down` is not in the generated table (icons.py has 38 and
    # that is not one), so `chevron-down` stands in — what select_trigger
    # draws.
    "chevron": 16.0,
    "chevron_icon": "chevron-down",
    "chevron_ink": ("foreground", 0.5),   # opacity-50 over currentColor

    # ---- panel: PopoverContent (p-0) + Command (p-1) --------------------
    "pad": T.SPACE[1],                    # 4 — the Command's p-1
    "radius": "lg",                       # 10, the same as menu.py's panel
    "bg": ("popover", 1.0),               # as menu.py
    "ring": ("foreground", 0.10),         # ring-1 ring-foreground/10, as menu.py
    "side_offset": T.SPACE[1],            # sideOffset 4, then ROUNDED
    "align": "center",                    # popover.tsx's default
    "fade": 0.10,                         # animation: enter 0.1s, as menu.py

    # ---- CommandInput ---------------------------------------------------
    "field_h": 32.0,                      # h-8!
    "field_radius": "lg",                 # rounded-lg! = 10
    "field_pad": T.SPACE[1],              # the wrapper's p-1 pb-0
    "field_bg": ("input", 0.3),           # bg-input/30 in BOTH themes
    "field_border": ("input", 0.3),       # border-input/30 in BOTH themes
    "field_icon": 16.0,                   # size-4
    "field_icon_x": 9.0,                  # border 1 + the addon's pl-2 (8)
    "field_icon_ink": ("muted-foreground", 0.5),  # opacity-50 on the addon
    "field_text_x": 31.0,                 # 1 + addon 24 + the input's pl-1.5
    "field_text_r": 1.0,                  # the input's right edge: the border
    "field_font": 14.0,                   # text-sm
    "field_line": 20.0,                   # line-height; centred in h-8 -> +6
    "field_ink": ("popover-foreground", 1.0),
    "field_placeholder": ("foreground", 0.5),   # Chromium's own, measured

    # ---- CommandList ----------------------------------------------------
    "list_max_h": 288.0,                  # max-h-72

    # ---- CommandGroup ---------------------------------------------------
    "group_pad": T.SPACE[1],              # p-1
    "head_h": 28.0,                       # py-1.5 on a 16px line box
    "head_pad_x": T.SPACE[2],             # px-2
    "head_font": 12.0,                    # text-xs
    "head_weight": "medium",              # font-medium
    "head_ink": ("muted-foreground", 1.0),

    # ---- CommandItem ----------------------------------------------------
    "item_h": 32.0,                       # py-1.5 on a 20px line box
    "item_pad_x": T.SPACE[2],             # px-2
    "item_radius": "sm",                  # rounded-sm = 6
    "item_gap": T.SPACE[2],               # gap-2
    "item_font": 14.0,                    # text-sm
    "item_ink": ("popover-foreground", 1.0),
    "item_sel_bg": ("muted", 1.0),        # data-selected:bg-muted
    "item_sel_ink": ("foreground", 1.0),  # the same value as popover-foreground
    # DERIVED from `data-[disabled=true]:opacity-50`; no disabled row exists
    # on the probe route.
    "item_disabled_opacity": 0.5,
    # Measured at 16x16, right-aligned inside the padding and vertically
    # centred, with `opacity: 0` — no probe row is checked, so the OPAQUE
    # colour is DERIVED: `<CheckIcon/>` at currentColor.
    "check": 16.0,
    "check_ink": ("popover-foreground", 1.0),
    # DERIVED from `-mx-1 h-px bg-border` on a child of CommandList: 1px, no
    # margin block, pulled 4px out each side so it spans the whole panel.
    # menu.py's separator is inset 1px from the panel edge instead, and
    # carries my-1 (4) above and below; this one carries none.
    "sep_h": 1.0,
    "sep_col": ("border", 1.0),

    # ---- CommandEmpty ---------------------------------------------------
    "empty_h": 68.0,                      # py-6 on a 20px line box
    "empty_font": 14.0,                   # text-sm
    "empty_ink": ("popover-foreground", 1.0),   # NOT muted-foreground
}

# The only values that move with the theme, and all four are the trigger's.
# The first two are tokens.SELECT_DARK's two exactly, because a dark
# Button-outline and a dark SelectTrigger measure the same. Everything else
# in the table above is a token that swaps itself.
COMBOBOX_DARK = {
    "trigger_bg": ("input", 0.3),         # dark:bg-input/30
    "trigger_hover": ("input", 0.5),      # dark:hover:bg-input/50
    # measured: an OPEN dark trigger is byte-identical to a closed one
    "trigger_open": ("input", 0.3),
    "trigger_border": ("input", 1.0),     # dark:border-input
}


def combobox_table(theme_name: str) -> dict:
    """COMBOBOX resolved for a theme, the shape tokens.select_table has."""
    t = dict(COMBOBOX)
    if theme_name == "dark":
        t.update(COMBOBOX_DARK)
    return t


# Where each panel was last drawn, keyed by popup id — the same seam
# menu.LAST_RECT is, and for the same reason: ImGui places the popup, so a
# test cannot know the rect ahead of time, and reading it off pixels is
# unreliable.
LAST_RECT: dict = {}


# --------------------------------------------------------------------------
# items
# --------------------------------------------------------------------------

@dataclass
class Item:
    """One row. `kind` is item | label | sep, as `menu.Item`'s is.

    A `menu.Item` is accepted anywhere this is: every field below is read
    through `getattr` with a default, so the two are interchangeable and a
    caller already holding menu rows does not have to convert them.
    """
    id: str = ""
    label: str = ""
    icon: str = ""
    kind: str = "item"
    # cmdk scores `value + " " + keywords.join(" ")`, so a keyword is a
    # second spelling a row can be found by.
    keywords: tuple = ()
    enabled: bool = True
    # None means "work it out from the trigger's current label", which is
    # what the recipe does with `value === item.value`.
    checked: bool | None = None


def heading(text: str) -> Item:
    """A CommandGroup heading. It also OPENS a group: the rows after it are
    ranked among themselves and the group travels as a block, which is what
    cmdk does — it sorts groups by their best row's score."""
    return Item(kind="label", label=text)


def sep() -> Item:
    """A CommandSeparator. cmdk renders one only while the search box is
    EMPTY (`alwaysRender` aside) — read out of cmdk 1.1.1's own source — so
    `filter_items` drops separators as soon as there is a query."""
    return Item(kind="sep")


def _k(it, name, default):
    return getattr(it, name, default)


def _is_row(it) -> bool:
    return _k(it, "kind", "item") == "item"


# --------------------------------------------------------------------------
# the filter — pure, no imgui
# --------------------------------------------------------------------------
#
# WHICH RULE cmdk ACTUALLY USES, read out of the shipped package rather than
# assumed: `cmdk@1.1.1`'s default filter is `commandScore`
# (node_modules/cmdk/dist/chunk-NZJY6EH4.mjs, re-exported as
# dist/command-score.mjs), and it is
#
#   * a SUBSEQUENCE match, not a substring one — "ec" matches "Dodecahedron"
#   * CASE-INSENSITIVE: both sides go through
#     `s.toLowerCase().replace(/[\s-]/g, " ")`, so a hyphen folds to a space
#     as well
#   * SCORED in (0, 1]: 0 means no match, and cmdk's gate for showing a row
#     is literally `filtered.items.get(id) > 0`
#   * ranked DESCENDING by that score, ties left in source order (V8's sort
#     is stable, and so is Python's)
#
# The score is not a tie-break bolted onto a substring test — it IS the
# rule, so the algorithm is ported outright below, constant for constant,
# rather than approximated. It was cross-checked against the shipped JS over
# 59 (string, query[, keywords]) pairs and agrees to 1e-12 on every one.
#
# Why that matters rather than being pedantry: with "dod" over
# ["Great Dodecahedron", "Dodecahedron", "Dual Dodecahedron"] a substring
# test cannot say which comes first. commandScore puts the one that STARTS
# with the query first, because a jump to the head of the string scores 1, a
# jump to a word boundary 0.9 and a jump into the middle of a word 0.17.

SCORE_CONTINUE_MATCH = 1.0
SCORE_SPACE_WORD_JUMP = 0.9
SCORE_NON_SPACE_WORD_JUMP = 0.8
SCORE_CHARACTER_JUMP = 0.17
SCORE_TRANSPOSITION = 0.1
PENALTY_SKIPPED = 0.999
PENALTY_CASE_MISMATCH = 0.9999
PENALTY_NOT_COMPLETE = 0.99

# cmdk's IS_GAP_REGEXP / IS_SPACE_REGEXP, as sets. `\s` is JavaScript's,
# which includes U+00A0 and the unicode separators; the five ASCII ones plus
# the no-break space cover everything a label here can hold.
_GAP_CHARS = frozenset("\\/_+.#\"@[({&")
_SPACE_CHARS = frozenset(" \t\n\r\f\v -")


def _at(s: str, i: int) -> str:
    """JavaScript's `String.prototype.charAt`: "" when out of range.

    Not `s[i]` — a negative index WRAPS in Python, so `s[-1]` would read
    the last character as if it were the one before the start, and
    `charAt(-1)` is reached for real at index 0.
    """
    return s[i] if 0 <= i < len(s) else ""


def _count(s: str, chars: frozenset) -> int:
    """`s.match(/…/g)?.length ?? 0` for a single-character class."""
    return sum(1 for c in s if c in chars)


def _fold(s: str) -> str:
    """cmdk's `formatInput`: lowercase, with `[\\s-]` folded to a space."""
    return "".join(" " if c in _SPACE_CHARS else c for c in s.lower())


def _score(string, abbr, lower_string, lower_abbr, si, ai, memo):
    if ai == len(abbr):
        return (SCORE_CONTINUE_MATCH if si == len(string)
                else PENALTY_NOT_COMPLETE)
    key = (si, ai)
    hit = memo.get(key)
    if hit is not None:
        return hit

    ch = lower_abbr[ai]
    high = 0.0
    idx = lower_string.find(ch, si)
    while idx >= 0:
        s = _score(string, abbr, lower_string, lower_abbr, idx + 1, ai + 1,
                   memo)
        # The multipliers apply only when the recursive score already beats
        # the best so far — that is how the JS is written, `E>S&&(E*=…)`,
        # and the transposition branch below then compares against the RAW
        # score. Ported faithfully rather than tidied, because tidying it
        # changes the numbers.
        if s > high:
            if idx == si:
                s *= SCORE_CONTINUE_MATCH
            elif _at(string, idx - 1) in _GAP_CHARS:
                s *= SCORE_NON_SPACE_WORD_JUMP
                n = _count(string[si:idx - 1], _GAP_CHARS)
                if n and si > 0:
                    s *= PENALTY_SKIPPED ** n
            elif _at(string, idx - 1) in _SPACE_CHARS:
                s *= SCORE_SPACE_WORD_JUMP
                n = _count(string[si:idx - 1], _SPACE_CHARS)
                if n and si > 0:
                    s *= PENALTY_SKIPPED ** n
            else:
                s *= SCORE_CHARACTER_JUMP
                if si > 0:
                    s *= PENALTY_SKIPPED ** (idx - si)
            if _at(string, idx) != _at(abbr, ai):
                s *= PENALTY_CASE_MISMATCH
        if ((s < SCORE_TRANSPOSITION
             and _at(lower_string, idx - 1) == _at(lower_abbr, ai + 1))
            or (_at(lower_abbr, ai + 1) == _at(lower_abbr, ai)
                and _at(lower_string, idx - 1) != _at(lower_abbr, ai))):
            t = _score(string, abbr, lower_string, lower_abbr, idx + 1,
                       ai + 2, memo)
            if t * SCORE_TRANSPOSITION > s:
                s = t * SCORE_TRANSPOSITION
        if s > high:
            high = s
        idx = lower_string.find(ch, idx + 1)

    memo[key] = high
    return high


def command_score(string: str, query: str, keywords=()) -> float:
    """cmdk's `commandScore(value, search, keywords)`, in Python.

    0 is "no match"; anything above it matches, and bigger is better.
    Keywords are appended to the haystack with spaces, exactly as cmdk does,
    so they match as if they were part of the label.
    """
    if keywords:
        string = string + " " + " ".join(k.strip() for k in keywords)
    return _score(string, query, _fold(string), _fold(query), 0, 0, {})


def filter_items(items, query: str) -> list:
    """Rank and filter `items` by `query`, the way cmdk does. Pure.

    * An EMPTY (or all-whitespace) query returns the list UNCHANGED — not
      re-ranked. cmdk's sort returns early on `!search`, so the author's
      order is the order, and separators survive.
    * Otherwise a row is kept when `command_score > 0`, and rows come out
      ordered by that score, descending, with ties in source order.
    * A `heading()` opens a group: its rows are ranked among themselves and
      the group moves as a block, groups ordered by their best row's score.
      A group whose rows all scored 0 disappears, heading and all — cmdk's
      `filtered.groups` rule.
    * Separators are dropped while there is a query, because cmdk renders a
      `CommandSeparator` only when the search box is empty.

    Rows before the first heading form an implicit, unheaded group, which is
    what `<CommandGroup>` with no `heading` prop is.
    """
    items = list(items)
    if not query or not query.strip():
        return items

    # (heading_or_None, [rows]) in source order; separators are gone
    groups: list = [(None, [])]
    for it in items:
        kind = _k(it, "kind", "item")
        if kind == "sep":
            continue
        if kind == "label":
            groups.append((it, []))
        else:
            groups[-1][1].append(it)

    ranked = []
    for head, rows in groups:
        scored = []
        for it in rows:
            s = command_score(_k(it, "label", "") or str(_k(it, "id", "")),
                              query, tuple(_k(it, "keywords", ())))
            if s > 0.0:
                scored.append((s, it))
        if not scored:
            continue
        # `sorted` is stable, so equal scores keep source order — which is
        # also what V8's sort gives cmdk
        best = max(s for s, _ in scored)
        scored.sort(key=lambda p: -p[0])
        ranked.append((best, head, [it for _, it in scored]))
    ranked.sort(key=lambda p: -p[0])

    out: list = []
    for _best, head, rows in ranked:
        if head is not None:
            out.append(head)
        out.extend(rows)
    return out


# --------------------------------------------------------------------------
# intrinsic size, through the layout tree
# --------------------------------------------------------------------------

def _rows_node(items, mw, tbl, *, empty: str = "") -> B.Node:
    """The CommandList's content, as a `box.Node` column.

    Every row carries a `key`, so `box.place_tree` hands its rect straight
    back — which is the whole reason to build a tree instead of adding up
    offsets, the failure `box.py` exists to stop.

    `mw(text, variant, size) -> width` measures text.
    """
    pad = tbl["group_pad"]
    kids: list = []
    group: B.Node | None = None

    def open_group() -> B.Node:
        nonlocal group
        group = B.Node(dir="column", pad=(pad, pad, pad, pad), kids=[])
        kids.append(group)
        return group

    for i, it in enumerate(items):
        kind = _k(it, "kind", "item")
        if kind == "sep":
            # `-mx-1`: a separator is a child of the LIST and reaches out
            # past a group's padding, so it does not live inside a group.
            group = None
            kids.append(B.Node(h=tbl["sep_h"], key=("sep", i)))
            continue
        if kind == "label":
            g = open_group()
            tw = mw(_k(it, "label", ""), tbl["head_weight"],
                    tbl["head_font"]) + 2 * tbl["head_pad_x"]
            g.kids.append(B.Node(h=tbl["head_h"], key=("row", i),
                                 measure=lambda w=tw: (w, tbl["head_h"])))
            continue
        g = group if group is not None else open_group()
        lead = ((tbl["field_icon"] + tbl["item_gap"])
                if _k(it, "icon", "") else 0.0)
        tw = (mw(_k(it, "label", ""), "regular", tbl["item_font"]) + lead
              + 2 * tbl["item_pad_x"] + tbl["item_gap"] + tbl["check"])
        g.kids.append(B.Node(h=tbl["item_h"], key=("row", i),
                             measure=lambda w=tw: (w, tbl["item_h"])))

    if not any(_is_row(it) for it in items):
        # CommandEmpty is a child of the LIST, not of a group: measured at
        # the list's own width, with no 4px inset.
        tw = mw(empty, "regular", tbl["empty_font"]) if empty else 0.0
        kids.append(B.Node(h=tbl["empty_h"], key=("empty", 0),
                           measure=lambda w=tw: (w, tbl["empty_h"])))
    return B.Node(dir="column", kids=kids, key="list")


def combobox_size(items, faces, *, min_w: float = 0.0, measure=None,
                  theme_name: str = "light", empty: str = "") -> tuple:
    """The panel's intrinsic (w, h), from its contents.

    `box.wants` does the arithmetic; nothing here types a height. The one
    thing that is not a sum is the list's `max-h-72` (288), which is a real
    clamp in the class and is applied as one.

    `measure(text, variant, size) -> width` is injectable, so this is
    testable with no GL and no display the way `box.Node.measure` already
    is; left out, it goes through `draw.text_w` with `faces`.

    The search field contributes no width: it is `w-full`, and measured, the
    220px panel's width came entirely from the recipe's `w-[220px]` with the
    field stretching to fill it.
    """
    tbl = combobox_table(theme_name)
    mw = measure or (lambda s, v, size: D.text_w(s, faces, v, size))
    cw, ch = B.wants(_rows_node(items, mw, tbl, empty=empty))
    pad, fp = tbl["pad"], tbl["field_pad"]
    panel = B.Node(dir="column", pad=(pad, pad, pad, pad), kids=[
        # the input wrapper's `p-1 pb-0` over an h-8 field
        B.Node(pad=(fp, fp, 0.0, fp), kids=[B.Node(h=tbl["field_h"])]),
        B.Node(w=cw, h=min(ch, tbl["list_max_h"])),
    ])
    w, h = B.wants(panel)
    return max(w, min_w), h


def list_content_h(items, tbl) -> float:
    """How tall the list's CONTENT is, which is what a ScrollArea has to be
    told. The same tree, measured with a zero text width — none of the
    heights in it depend on any text."""
    return B.wants(_rows_node(items, lambda *a: 0.0, tbl, empty="x"))[1]


# --------------------------------------------------------------------------
# the widget
# --------------------------------------------------------------------------
#
# PANEL CHROME. The four lines in `_panel_chrome` are the four `menu.popup`
# draws, and that is not an accident: the two panels were measured identical
# (see the module docstring). They are here rather than called because
# `menu.popup` is one function that owns the popup's whole lifecycle — the
# style vars, the `begin_popup`, the fade, the chrome AND the row loop — and
# a Combobox needs the first four with a completely different body. The
# right fix is a `menu.panel_chrome(ui, x, y, w, h, alpha)` that both call;
# adding it means editing menu.py, which this change may not do.


def _col(ui, spec, a: float = 1.0):
    tok, al = spec
    return ui.col(tok, al * a)


def round_px(v: float) -> float:
    """JavaScript's `Math.round`, which is what Radix rounds its transform
    with — and NOT Python's `round`, which is banker's: `round(2666.5)` is
    2666 in Python and 2667 in the browser. Measured on eight sub-pixel
    trigger positions, the panel's placed y is exactly this of
    `anchor.bottom + sideOffset`.
    """
    return float(floor(v + 0.5))


def _panel_chrome(ui, dl, x, y, w, h, a, tbl) -> None:
    r = T.RADII[tbl["radius"]]
    # the shadow and the ring fall OUTSIDE the window rect, which imgui
    # clips to; widen the clip while the chrome is drawn
    dl.push_clip_rect(imgui.ImVec2(x - 16, y - 16),
                      imgui.ImVec2(x + w + 16, y + h + 16), False)
    D.shadow_stack(dl, x, y, w, h, r,
                   [(dx, dy, bl, sp, al * a)
                    for dx, dy, bl, sp, al in T.SHADOW_MD])
    D.fill(dl, x, y, w, h, _col(ui, tbl["bg"], a), r)
    D.border(dl, x - 1, y - 1, w + 2, h + 2, _col(ui, tbl["ring"], a),
             r + 1, 1.0)
    dl.pop_clip_rect()


def _trigger(ui, tbl, x, y, w, h, radius, label, placeholder, *,
             hot=0.0, open_f=0.0, disabled=False) -> None:
    """The recipe's trigger: a Button variant="outline".

    `draw.field` draws the box — genuinely shared chrome, measured identical
    on an Input, a SelectTrigger and this Button: one 1px border inside the
    box, plus a 3px ring outside it. Only the fill, the font weight and the
    chevron's inset differ, and those three are what is set here.

    `draw.select_trigger` is NOT reused, although it is the same shape,
    because it reads its radius out of `tokens.SELECT_SIZES`, hard-codes
    `muted-foreground` for the chevron and places it at `pad_r` — three
    values this trigger measures differently. Making those table-driven
    would let the two share one function; that is a change to draw.py, which
    this change may not make.
    """
    ft = {
        "bg": ("#00000000", 1.0),      # painted below, after the ring
        "border": tbl["trigger_border"],
        "ring": tbl["trigger_ring"],
        "disabled_opacity": 0.5,
    }
    # focus_f=0: measured, a mouse-opened trigger carries no ring at all,
    # in either theme. The open state is the FILL, below.
    D.field(ui.dl, x, y, w, h, ui.theme, ft, focus_f=0.0,
            disabled=disabled, radius=radius)
    # open first, then hover on top of it: in light they are the same
    # colour so the order cannot show, and in dark `open` is the rest fill
    # and hover is the only tint — which is what the measurement says.
    bg = mix(_col(ui, tbl["trigger_bg"]), _col(ui, tbl["trigger_open"]),
             open_f)
    D.fill(ui.dl, x, y, w, h,
           mix(bg, _col(ui, tbl["trigger_hover"]), hot), radius)

    pad, cs = tbl["trigger_pad_x"], tbl["chevron"]
    # `justify-between`: the icon's right edge is the content box's right
    # edge, i.e. border 1 + padding in from the trigger's own
    D.icon(ui.dl, tbl["chevron_icon"], x + w - 1.0 - pad - cs,
           y + (h - cs) / 2.0, cs, _col(ui, tbl["chevron_ink"]))
    # measured: a SelectValue sits at x + 1 + padding-left, the border
    # included — the same place this Button's text box starts
    D.label(ui.dl, x + 1.0 + pad, y, label or placeholder, ui.faces,
            tbl["trigger_weight"], tbl["trigger_font"],
            ui.col("foreground" if label else "muted-foreground"),
            baseline_box=h,
            max_w=w - 2.0 * (1.0 + pad) - cs - tbl["trigger_gap"])


def _field(ui, key, x, y, w, h, tbl, text, placeholder, *, focus: bool):
    """The search box: a real `imgui.input_text` under the sandwich.

    The stock widget supplies the caret, the selection, the keyboard and the
    clipboard, none of which is worth rewriting; the sandwich replaces only
    its frame. `interact.text_input`'s arrangement exactly, with this
    field's own measured colours and insets — and with NO focus ring,
    because measured, this field has none.
    """
    import interact as I

    cols = I._sandwich_begin(ui, clear_grab=False)
    # imgui's own Col_.text is WHITE: on the light theme the typed query
    # would be invisible against the field unless the theme is pushed.
    imgui.push_style_color(imgui.Col_.text,
                           imgui.ImVec4(*_col(ui, tbl["field_ink"])))
    # ImGui draws a blue nav cursor around whatever the keyboard focused,
    # and `set_keyboard_focus_here` below guarantees that is this field.
    # Measured, the real one has no focus chrome at all — the InputGroup's
    # ring selector never matches a `command-input` — so it is cleared
    # rather than restyled. It showed up at once in a headless drive: a
    # blue rectangle no shadcn component has, around the one field in the
    # kit that takes the keyboard without being asked.
    imgui.push_style_color(imgui.Col_.nav_cursor, imgui.ImVec4(0, 0, 0, 0))
    tx = x + tbl["field_text_x"]
    # the CSS line box is 20 in a 32 field, so the glyphs sit 6 down;
    # imgui adds frame_padding.y inside the frame it draws from the cursor
    imgui.set_cursor_screen_pos(imgui.ImVec2(
        tx, y + (h - tbl["field_line"]) / 2.0
        - imgui.get_style().frame_padding.y))
    imgui.push_item_width(w - tbl["field_text_x"] - tbl["field_text_r"])
    if focus:
        # a fresh Popover mounts its Command with the input focused
        imgui.set_keyboard_focus_here()
    changed, out = imgui.input_text(f"##{key}", text)
    imgui.pop_item_width()
    imgui.pop_style_color(2)
    I._sandwich_end(ui, cols)

    D.box(ui.dl, x, y, w, h, fill_col=_col(ui, tbl["field_bg"]),
          border_col=_col(ui, tbl["field_border"]),
          radius=T.RADII[tbl["field_radius"]], border_w=1.0)
    g = tbl["field_icon"]
    D.icon(ui.dl, "search", x + tbl["field_icon_x"], y + (h - g) / 2.0, g,
           _col(ui, tbl["field_icon_ink"]))
    if not out:
        D.label(ui.dl, tx, y, placeholder, ui.faces, "regular",
                tbl["field_font"], _col(ui, tbl["field_placeholder"]),
                baseline_box=h)
    ui.dl.channels_merge()
    return changed, out


def _row(ui, it, r, key, tbl, *, selected: bool, checked: bool) -> bool:
    """One CommandItem. Returns True if it was clicked.

    No easing on the highlight: `transition-duration` on a command-item
    measures 0s, so it snaps. Everything else in the kit eases; this does
    not, because the browser does not.
    """
    enabled = _k(it, "enabled", True)
    st = ui.hit(key, r.x, r.y, r.w, r.h) if enabled else None
    dim = 1.0 if enabled else tbl["item_disabled_opacity"]
    if selected and enabled:
        D.fill(ui.dl, *D.snap(r.x, r.y, r.w, r.h),
               _col(ui, tbl["item_sel_bg"]), T.RADII[tbl["item_radius"]])
    ink = _col(ui, tbl["item_sel_ink"] if selected else tbl["item_ink"], dim)

    tx = r.x + tbl["item_pad_x"]
    cs = tbl["check"]
    if _k(it, "icon", ""):
        g = tbl["field_icon"]
        D.icon(ui.dl, _k(it, "icon", ""), tx, r.y + (r.h - g) / 2.0, g, ink)
        tx += g + tbl["item_gap"]
    D.label(ui.dl, tx, r.y, _k(it, "label", ""), ui.faces, "regular",
            tbl["item_font"], ink, baseline_box=r.h,
            max_w=r.x + r.w - tbl["item_pad_x"] - cs - tbl["item_gap"] - tx)
    if checked:
        D.icon(ui.dl, "check", r.x + r.w - tbl["item_pad_x"] - cs,
               r.y + (r.h - cs) / 2.0, cs, _col(ui, tbl["check_ink"], dim))
    return bool(st and st.clicked)


def _state(ui, key) -> dict:
    """Per-combobox state that has to outlive the frame.

    It lives on `ui.anim.store` because a `Ui` is rebuilt every frame and
    anything kept on one is thrown away before it can be read back — the
    trap the tooltip's hover clock already fell into.
    """
    return ui.anim.store.setdefault("combobox", {}).setdefault(
        key, {"q": "", "sel": 0, "focus": True})


def combobox(ui, key, x, y, w, label, items, *, size="default",
             disabled=False, placeholder="Select an option",
             search="Search...", empty="No results found.") -> tuple:
    """shadcn's Combobox recipe: the trigger here, the panel on ImGui's
    popup stack. Returns `(chosen_id_or_None, open)`.

    Shaped after `interact.select`, whose filterable sibling it is — and
    like it, the popup is ImGui's: focus, dismissal on click-away or Escape,
    nesting and z-order are solved there already and reimplementing them
    would be the wrong kind of work.

    The panel is as wide as the trigger, which is what the recipe's matching
    `w-[220px]` on both of them means; `combobox_size` is there for a caller
    that would rather size the trigger from the content.

    One deliberate frame of lag: the panel's height has to be handed to
    `set_next_window_size` BEFORE `begin_popup`, while the query only comes
    back out of `input_text` inside it. So a frame lays out and draws the
    PREVIOUS query's rows and stores the new one, which the next frame
    picks up. The alternative — re-filtering after reading the field — sizes
    the panel for one list and fills it with another.
    """
    import interact as I

    tbl = combobox_table(ui.theme_name)
    hh, rkey = T.SELECT_SIZES[size]
    pid = f"##cb.{key}"

    st = ui.hit(key, x, y, w, hh)
    if st.clicked and not disabled:
        imgui.open_popup(pid)
    open_ = imgui.is_popup_open(pid)
    hot = ui.anim.to(f"{key}:hot",
                     1.0 if st.hovered and not disabled else 0.0)
    # `transition-all` 150ms on the standard curve, measured on the
    # trigger — so both of its states ease, unlike the panel's rows
    open_f = ui.anim.to(f"{key}:open", 1.0 if open_ else 0.0)
    _trigger(ui, tbl, x, y, w, hh, T.RADII[rkey], label, placeholder,
             hot=hot, open_f=open_f, disabled=disabled)

    if not open_:
        LAST_RECT.pop(pid, None)
        ui.anim.to(f"{pid}:open", 0.0)
        # the Popover unmounts its Command, so neither the query nor the
        # keyboard focus survives a close
        ui.anim.store.setdefault("combobox", {}).pop(key, None)
        return None, False

    s = _state(ui, key)
    shown = filter_items(items, s["q"])
    rows = [i for i, it in enumerate(shown)
            if _is_row(it) and _k(it, "enabled", True)]
    if s["sel"] >= len(rows):
        s["sel"] = 0

    pad, fp = tbl["pad"], tbl["field_pad"]
    ch = list_content_h(shown, tbl)
    lh = min(ch, tbl["list_max_h"])
    ph = pad + fp + tbl["field_h"] + lh + pad

    at, _side = B.place_popover(B.Rect(x, y, w, hh), w, ph, ui.viewport,
                                side="bottom", align=tbl["align"],
                                offset=tbl["side_offset"])
    # Radix rounds its own transform, so the panel's origin is integral and
    # the gap off a fractional trigger runs 3.625 … 4.5 rather than a
    # constant 4. Measured; see the module docstring.
    imgui.set_next_window_pos(imgui.ImVec2(round_px(at.x), round_px(at.y)))
    imgui.set_next_window_size(imgui.ImVec2(w, ph))
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
    imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
    imgui.push_style_var(imgui.StyleVar_.popup_rounding,
                         T.RADII[tbl["radius"]])
    imgui.push_style_color(imgui.Col_.popup_bg, imgui.ImVec4(0, 0, 0, 0))

    chosen = None
    if imgui.begin_popup(pid):
        # shadcn fades the panel in over 100ms (`animation: enter 0.1s`).
        # ImGui places the window, so only the chrome is animated.
        a = ui.anim.to(f"{pid}:open", 1.0)
        dl = imgui.get_window_draw_list()
        p = imgui.get_window_pos()
        px, py = p.x, p.y
        LAST_RECT[pid] = (px, py, w, ph)
        saved, ui.dl = ui.dl, dl
        _panel_chrome(ui, dl, px, py, w, ph, a, tbl)

        _ch, q = _field(ui, f"{key}.q", px + pad + fp, py + pad + fp,
                        w - 2 * (pad + fp), tbl["field_h"], tbl, s["q"],
                        search, focus=s["focus"])
        s["focus"] = False
        if q != s["q"]:
            s["q"], s["sel"] = q, 0      # a new query re-ranks; next frame

        # one highlight, moved by EITHER the pointer or the keyboard, which
        # is what cmdk's single `data-selected` attribute means
        if rows:
            if imgui.is_key_pressed(imgui.Key.down_arrow, True):
                s["sel"] = (s["sel"] + 1) % len(rows)
            if imgui.is_key_pressed(imgui.Key.up_arrow, True):
                s["sel"] = (s["sel"] - 1) % len(rows)

        lx, ly, lw = px + pad, py + pad + fp + tbl["field_h"], w - 2 * pad
        with I.scroll_area(ui, f"{key}.list", lx, ly, lw, lh, ch) as view:
            node = _rows_node(shown, lambda *a: 0.0, tbl, empty=empty)
            place = B.lay(node, B.Rect(view.x, view.y, view.w, ch))

            # the pointer takes the highlight only when it MOVES, which is
            # cmdk's `onPointerMove` selection. Taking it every frame would
            # make a parked mouse override the arrow keys, which is the
            # whole reason cmdk has `disablePointerSelection`.
            if imgui.get_io().mouse_delta.x or imgui.get_io().mouse_delta.y:
                for n, i in enumerate(rows):
                    r = place[("row", i)]
                    if imgui.is_mouse_hovering_rect(
                            imgui.ImVec2(r.x, r.y),
                            imgui.ImVec2(r.x + r.w, r.y + r.h)):
                        s["sel"] = n

            for i, it in enumerate(shown):
                kind = _k(it, "kind", "item")
                if kind == "sep":
                    r = place[("sep", i)]
                    # `-mx-1`: it reaches out past the list, over the
                    # panel's own padding
                    D.fill(ui.dl, r.x - pad, r.y, r.w + 2 * pad,
                           tbl["sep_h"], _col(ui, tbl["sep_col"]))
                    continue
                r = place[("row", i)]
                if kind == "label":
                    D.label(ui.dl, r.x + tbl["head_pad_x"], r.y,
                            _k(it, "label", ""), ui.faces,
                            tbl["head_weight"], tbl["head_font"],
                            _col(ui, tbl["head_ink"]), baseline_box=r.h)
                    continue
                chk = _k(it, "checked", None)
                if chk is None:
                    chk = bool(label) and _k(it, "label", "") == label
                # keyed by the item's OWN id, not by its index: a re-rank
                # moves rows, and an index-keyed hit target would hand one
                # row's held/hover state to whichever row took its place —
                # React keeps a node's identity across a re-order, and this
                # is the immediate-mode equivalent. Falls back to the index
                # for rows with no id, which keeps `ui.hit`'s duplicate-id
                # guard from firing on a list of blanks.
                if _row(ui, it, r, f"{key}.r{_k(it, 'id', '') or i}", tbl,
                        selected=bool(rows) and rows[s["sel"]] == i,
                        checked=bool(chk)):
                    chosen = _k(it, "id", "")
            if not rows and ("empty", 0) in place:
                r = place[("empty", 0)]
                D.label(ui.dl, r.x, r.y, empty, ui.faces, "regular",
                        tbl["empty_font"], _col(ui, tbl["empty_ink"]),
                        align="center", box_w=r.w, baseline_box=r.h)

        if rows and (imgui.is_key_pressed(imgui.Key.enter, False)
                     or imgui.is_key_pressed(imgui.Key.keypad_enter, False)):
            chosen = _k(shown[rows[s["sel"]]], "id", "")
        if chosen is not None:
            imgui.close_current_popup()
        elif imgui.is_key_pressed(imgui.Key.escape, False):
            # ImGui dismisses a popup on Escape on its own — but NOT while
            # an InputText inside it has the keyboard, because the field
            # takes the first Escape to cancel its own edit. Measured in a
            # headless drive: one Escape left the panel open, two closed
            # it. Radix closes on the first, so the popup is closed here by
            # hand. `is_key_pressed` ignores key ownership, which is what
            # lets this see a key the field has claimed.
            imgui.close_current_popup()
        ui.dl = saved
        imgui.end_popup()

    imgui.pop_style_color()
    imgui.pop_style_var(3)
    return chosen, open_
