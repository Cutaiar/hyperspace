"""Dropdown menus and popovers, on ImGui's popup stack.

The hard parts of a popup are not the chrome — they are focus, dismissal on
click-away or Escape, nesting, and keeping the thing above everything else.
ImGui already does all of that, so this borrows its popup window and paints
shadcn's chrome into it rather than reimplementing any of it.

The KEYBOARD is measured too, and it is the long comment under THE KEYBOARD
below: `popup` carries the whole model, so the dropdown, the ContextMenu and
a Select's panel inherit one answer rather than disagreeing three ways. Two
of its rules are the opposite of the Combobox's - a menu's arrows CLAMP and
its Tab is SWALLOWED - which is why that table was measured rather than
ported.

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

from . import box as B
from . import draw as D
from . import tokens as T
from .ease import mix

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
# How wide a panel may get. The real component has no maximum: a shadcn menu
# item carries no `truncate`, so in the browser a long row simply makes the
# panel as wide as its words (and wraps once the viewport runs out). That is
# not a law this kit can keep — a menu row here is ONE line, and the graph's
# insert menu carries refusals like "faces pattern: Faces pattern is in the
# graph already: drag it onto the cable", which made a 980px panel over the
# canvas. So this is the kit's own policy, like the x-clamp in
# `comp_context_menu.place_at_pointer`, and the number is the one the kit
# already uses for a floating box of words (`interact.tooltip`'s max_w).
# A row too long for it is ellipsised, and the host can put the whole of it
# in that row's tooltip (`ui_menu._tips_kit`).
MAX_W = 320.0
SEP_MY = 4.0         # my-1
DESTRUCTIVE_HOVER_A = {"light": 0.10, "dark": 0.20}
# `tracking-widest` is real and Chromium trails it: a 12px shortcut measures
# 2 x 1.2px wider than its glyphs. draw.text_w has no letter-spacing.
SHORTCUT_TRACKING = 1.2
ICON = 16.0          # size-4, measured; 14 was a guess

# --------------------------------------------------------------------------
# SUBMENUS, measured
# --------------------------------------------------------------------------
#
# Measured on the real ContextMenu in Chromium at dpr 1, in both themes, by
# `hyperspace/dkit/dev/probe_submenu.js` against the `contextmenu.sub` and
# `contextmenu.subwide` blocks of `?probe`. None of it could come out of
# `probe_react.js`: that walks the DOM once, and a Radix SubContent is not
# in the DOM at all until its trigger is HOVERED, which is a gesture and
# not a selector.
#
#   SubTrigger   an ITEM row to the pixel - 28 tall, px-1.5, gap-1.5,
#                rounded-md, 14/20 - plus a 16px chevron whose RIGHT edge is
#                `row.right - ITEM_PAD_X`, at `y + 6`.
#                width  6 + label + 6 + 16 + 6: ONE gap, exactly as a
#                       shortcut gets one. The wide block measured
#                       221.3594 = 6 + 187.3594 + 6 + 16 + 6, and the
#                       chevron does not sit over the label.
#                open   bg `accent`, ink `secondary-foreground` - the same
#                       pair hover paints (`data-open:bg-accent`), so an
#                       open trigger needs no colour of its own.
#   SubContent   min-w-32 = 128, NOT the ContextMenu's own 144 floor.
#                rounded-lg 10 · p-1 4 · bg-popover · shadow-**LG**, not md
#                · `border`: a 1px SOLID border INSIDE the box, where the
#                top panel's ring is a box-shadow wholly outside it. So a
#                sub panel's rows start 5px in, not 4, and the measured
#                103px panel is 1 + 4 + 28 + 28 + 9 + 28 + 4 + 1.
#                separator  full-bleed INSIDE the border: measured x =
#                           panel.x + 1 and w = 126 in a 128 panel.
#   placement    x = trigger.RIGHT, y = trigger.y. side="right"
#                align="start" with no offset, anchored on the TRIGGER ROW
#                and not on the panel: measured dx 0.000 from the trigger's
#                right edge (which is -4 from the panel's) and dy 0.000.
#   the gesture  hover opens after Radix's 100 ms timer - measured 114, 123
#                and 129 ms with a 10 ms poll - and moving to another row of
#                the parent closes it again inside 100 ms.
#   the keys     ArrowRight, Enter and Space on the trigger each open it and
#                highlight its FIRST row; ArrowLeft closes it and leaves the
#                highlight on the trigger; ArrowDown / ArrowUp then move
#                inside the sub; and Escape in a sub closes the WHOLE menu,
#                the parent panel with it. All six driven, not read.
#
# One deliberate divergence, and it is the one `place_at_pointer` already
# carries: Radix neither flips nor clamps a SubContent. Measured in a 250px
# viewport the panel stayed at `trigger.right` and hung 20px off the edge.
# `place_sub` flips it to the trigger's left instead, because an ImGui popup
# that leaves the window is simply lost.
SUB_MIN_W = 128.0       # min-w-32
SUB_BORDER = 1.0        # `border`, and inside the box
SUB_SHADOW = T.SHADOW_LG
SUB_OPEN_S = 0.10       # Radix's hover timer
# THE SAFE TRIANGLE (Amazon's "golden triangle", jQuery menu-aim's cone).
# Not from the browser: Radix has none, and a diagonal from a trigger to the
# far corner of its panel crosses the rows between them, each of which would
# take the pointer and close the panel you were on your way to. The triangle
# is the standard answer - while the pointer is inside the wedge from where
# it was to the panel's near edge, it is treated as heading there, and the
# rows it crosses do nothing.
AIM_SAMPLE_S = 0.15     # how old the point the wedge is drawn from may be
AIM_HOLD_S = 0.70       # a pointer parked in the wedge gives up after this
CHEVRON = "chevron_right"


def is_sub(it) -> bool:
    """Is this row a SubTrigger - an item carrying items of its own."""
    return bool(getattr(it, "items", ()))


# --------------------------------------------------------------------------
# THE KEYBOARD, measured
# --------------------------------------------------------------------------
#
# Driven on the real components in Chromium at dpr 1, with `?probe` blocks
# that are NOT forced open - which is the whole point. A `defaultOpen`
# component reports `data-state="open"` whatever you press, so "did this key
# open it" and "did this key close it" both come back yes, and the Combobox's
# first keyboard model came out wrong for exactly that reason (RETRO row 17).
# The blocks added for this are `menu.kb` (a DropdownMenu with a real
# trigger, one label, one separator, one DISABLED item, one destructive item
# and six enabled rows with distinct initials), `menu.long` (sixteen rows),
# `contextmenu.target` (opened with a real right-click), `select.kb` (a
# Select holding `Gamma`) and `select.kbnone` (the same Select holding
# nothing). Each row below names the block it came from.
#
# CLOSED - the trigger
#
#   gesture       DropdownMenu       ContextMenu      Select            block
#   ------------- ------------------ ---------------- ----------------- -----
#   focus alone   stays CLOSED       n/a, no trigger  stays CLOSED      menu.kb / select.kb
#   click         opens, NO highlight  right-click:   opens on the      menu.kb / contextmenu.target
#                                      opens, NO hl   CHECKED row       select.kb
#   Enter         opens on the FIRST  --              CHECKED row       menu.kb / select.kb
#   Space         opens on the FIRST  --              CHECKED row       menu.kb / select.kb
#   ArrowDown     opens on the FIRST  --              CHECKED row       menu.kb / select.kb
#   ArrowUp       does NOT OPEN      --               CHECKED row       menu.kb / select.kb
#   a letter      --                  --              sets the VALUE    select.kb
#                                                     without opening
#
# `select.kbnone`, the same Select holding nothing, answers the other
# column: all four gestures open it on the FIRST row - not on none, and not
# on the last for ArrowUp. The value beats the gesture and the gesture is
# only the fallback, which is `resolve_open`, and which is the same shape
# `comp_combobox.resolve_open` records for the Combobox (RETRO row 26).
#
# OPEN - the panel
#
#   key                   DropdownMenu / ContextMenu        Select
#   --------------------- --------------------------------- -----------------
#   ArrowDown, no hl      the FIRST row                     (always has one)
#   ArrowUp, no hl        the LAST row                      --
#   ArrowDown on i        i + 1, CLAMPING on the last       the same
#   ArrowUp on i          i - 1, clamping on the first      the same
#   Home, PageUp          the FIRST row                     Home only
#   End, PageDown         the LAST row                      End only
#   a letter              typeahead, below                   the same
#   Enter                 takes the hl, closes, focus       the same
#                         back on the trigger
#   Space                 the same as Enter - UNLESS the    the same
#                         typeahead buffer is live
#   Escape                closes, focus back on the         the same
#                         trigger (the BODY for a context
#                         menu, which has no trigger)
#   Tab                   SWALLOWED. Stays open, focus      SWALLOWED
#                         does not move. Three Tabs and
#                         a Shift+Tab, all swallowed.
#   a separator, a label  never highlighted (tabIndex -1)   n/a
#   a DISABLED item       skipped by the arrows AND by      n/a
#                         typeahead
#   the pointer, MOVING   takes the highlight               the same
#
# **The arrows CLAMP; they do not wrap and there is no none-state between
# the ends.** Measured as ArrowDown x24 off the bottom of a six-row menu and
# ArrowUp x20 off the top, both of which simply sit on the end row. This is
# the one place a menu and the Combobox genuinely differ - the Combobox
# falls off either end into nothing and comes back round on the next press -
# and porting the Combobox's table would have got it wrong. Radix's
# `RovingFocusGroup` takes a `loop` prop and the menus do not pass it.
#
# **Tab is the opposite of the Combobox's too.** Radix's menu content runs
# `if (event.key === "Tab") event.preventDefault()`, so a menu really does
# trap Tab, and so does a Select. It is a modal roving-focus layer: the only
# ways out are Escape, Enter, Space and a click. The kit already satisfied
# this by accident, because ImGui will not tab out of a popup window either.
#
# TYPEAHEAD is the thing menus have that comboboxes do not, and it is
# Radix's `getNextMatch`, reproduced in `next_match`:
#
#   * characters accumulate for 1000ms after the last one, then the buffer
#     clears. 'e' then 'p' inside the second lands on Epsilon; 'e', a wait,
#     then 'p' lands on Pi.
#   * the match is a case-insensitive PREFIX of the row's label.
#   * the search starts at the row AFTER the highlight and wraps round, so a
#     repeated letter walks the rows that start with it. A single-character
#     search excludes the current row, which is why 'a' twice on a menu with
#     one A-row stays put rather than flickering.
#   * disabled rows are not candidates. Typing 'g' with `Gamma` disabled
#     moves nothing.
#   * no match leaves the highlight alone. 'q' moved nothing.
#   * Space is a typeahead character while the buffer is live and the
#     SELECTION key when it is empty. Measured both ways: 'e' then Space
#     inside the second left the menu open on Epsilon; 'e', 1.3s, Space
#     selected it.
#
# TWO ROWS THE KIT CANNOT EXPRESS, recorded rather than implemented:
#
#   * **the panel scrolls to follow its keyboard highlight.** Measured on
#     `menu.long` in a 260px viewport: the panel clamps to 114px, and
#     arrowing down past the visible rows scrolls it by the minimum - 30,
#     86, 142, 198 ... 338 of a 342 range - exactly as the Combobox's list
#     does. `menu.popup` has no scroll area and no height clamp at all: it
#     sizes the window to its content and lets `place_popover` put it
#     somewhere. Giving a menu a clamp is a sizing job, not a keyboard one,
#     and it is the next thing to do here.
#   * **a Select's closed typeahead.** Measured: with the panel SHUT and the
#     trigger focused, typing 'd' set the trigger to `Delta` without opening
#     anything. `interact.select` reads no characters, so there is nowhere
#     for this to live yet.
KEY_MODEL = """closed: focus keeps it closed; a click opens a menu with
NOTHING highlighted and a Select on its CHECKED row; Enter, Space and
ArrowDown open a menu on its FIRST row. open: the arrows move one row and
CLAMP at both ends, Home/End go to the ends, a letter jumps by prefix,
Enter and Space take the highlight, Escape closes, and Tab is swallowed."""

# Which end an open puts the highlight on, before the row list is known.
# Sentinels rather than 0 / -1 / None, because None is itself one of the
# answers: "nothing highlighted" is the state a pointer-opened menu is in.
SEL_NONE = object()
SEL_FIRST = object()
SEL_LAST = object()
SENTINELS = (SEL_NONE, SEL_FIRST, SEL_LAST)

# How long a typeahead buffer survives its last character, in seconds.
# Radix clears it on a 1000ms timer; driven rather than read - 'e' then 'p'
# inside the second lands on Epsilon, and 'e', 1.3s, Space SELECTS.
TYPEAHEAD_HOLD = 1.0

def item_rows(items) -> list[int]:
    """The indices of the rows a highlight can land on.

    A separator and a label carry `tabIndex -1` on the real component and
    can never hold `data-highlighted`; a disabled item is filtered out of
    the candidate list by Radix itself (`getItems().filter(i => !i.disabled)`
    in both the arrow handler and the typeahead), and measured, ArrowDown
    stepped 0 -> 1 -> 3 straight over the disabled row at index 2.
    """
    return [i for i, it in enumerate(items)
            if getattr(it, "kind", "item") == "item"
            and getattr(it, "enabled", True)]


def highlighted_item(items, hi) -> int | None:
    """Turn a highlight position into an index into `items`, or None.

    Two numbering systems meet here and keeping them straight is the whole
    job: the keyboard counts the rows it can land on (`item_rows`), while
    the draw loop walks every item, separators and labels included. A menu
    with a label above it had its highlight two rows off when this was done
    inline at one of the two call sites.
    """
    if hi is None:
        return None
    rows = item_rows(items)
    return rows[hi] if 0 <= hi < len(rows) else None


def checked_row(items, rows) -> int | None:
    """Which POSITION in `rows` carries the check, or None.

    A position in `rows` rather than an index into `items`, because that is
    what the highlight counts in - the same convention
    `comp_combobox._committed_row` uses, and for the same reason: the
    highlighted row and the ticked row must not be able to disagree.
    """
    for n, i in enumerate(rows):
        if getattr(items[i], "checked", None):
            return n
    return None


def resolve_open(want, items, rows, *, on_checked: bool = False):
    """Which row an open highlights: the measured table, in one place.

                        a Select (on_checked)   a menu
        click           the CHECKED row         nothing
        Enter / Space   the CHECKED row         the FIRST row
        ArrowDown       the CHECKED row         the FIRST row
        ArrowUp         the CHECKED row         (does not open)

    `want` is one of the three sentinels - which end the gesture asked for -
    and the checked row BEATS it whenever `on_checked` is set, falling back
    to the gesture's end when nothing is checked. Measured both ways:
    `select.kb` holds `Gamma` and all four gestures open on Gamma;
    `select.kbnone` holds nothing and all four open on the first row.

    `on_checked` is off for a menu because the probe's DropdownMenu has no
    checked item, so that column was never asked - and a measurement that
    was not made is not a default. A caller that wants it says so.

    A free function so the rule can be asked without a GL context: the
    dashboard's Selects both hold a value, so the no-value column is not
    reachable by driving the app at all.
    """
    if want not in SENTINELS:
        return want
    if on_checked:
        at = checked_row(items, rows)
        if at is not None:
            return at
    if want is SEL_FIRST:
        return 0 if rows else None
    if want is SEL_LAST:
        return len(rows) - 1 if rows else None
    return None


def next_match(items, rows, buf: str, cur):
    """Radix's `getNextMatch`, which is what a menu's typeahead is.

    Returns the position in `rows` the buffer jumps to, or None to stay put.

    The search starts at the row AFTER the current highlight and wraps, so a
    repeated letter walks every row beginning with it. A ONE-character
    search drops the current row from the candidates - which is why typing
    'a' twice on a menu with a single A-row stays on it rather than
    flickering - and a buffer of the same character repeated is treated as
    that one character, so holding 'a' walks the A-rows instead of looking
    for a row called "aaa".
    """
    if not buf or not rows:
        return None
    repeated = len(buf) > 1 and all(c == buf[0] for c in buf)
    needle = (buf[0] if repeated else buf).lower()
    start = cur + 1 if cur is not None else 0
    order = [(start + k) % len(rows) for k in range(len(rows))]
    for n in order:
        if n == cur and len(needle) == 1:
            continue
        if getattr(items[rows[n]], "label", "").lower().startswith(needle):
            return None if n == cur else n
    return None


def _kb(ui, key: str) -> dict:
    """The per-menu keyboard state, on `ui.anim.store`.

    It has to live there and not on the `Ui`: a `Ui` is rebuilt every frame
    (dashboard.py), and `anim.store` is the one object the kit already
    threads across frames. The same trap kept the tooltip from reaching its
    delay and the context menu from remembering where it was clicked.
    """
    return ui.anim.store.setdefault("menukb", {}).setdefault(
        key, {"sel": None, "armed": False, "buf": "", "buf_age": 0.0,
              "frame": -10})


def arm(ui, key: str, want=SEL_FIRST) -> None:
    """Say which end the open that is about to happen asked for.

    Call it beside `imgui.open_popup(key)`, never instead of it. Without it
    a fresh popup starts at `SEL_NONE`, which is the measured answer for the
    POINTER - a click opens a menu with nothing highlighted - so only a
    keyboard open needs to say anything.

    It also sets `armed`, and that is not decoration. **The key that OPENS
    the panel must not also be processed by the panel.** The open happens in
    the parent window and this popup's handler runs later in the SAME frame,
    so without it an opening ArrowDown lands on the second row: the trigger
    resolves the highlight to the first and the panel's own handler moves it
    on by one. Measured as an off-by-one at both ends on the Combobox, which
    carries the same flag for the same reason.
    """
    st = _kb(ui, key)
    st["sel"], st["armed"] = want, True
    st["buf"], st["buf_age"] = "", 0.0


def open_from_trigger(ui, key: str, st, *, role: str = "menu",
                      disabled: bool = False) -> bool:
    """The trigger's half of the model. Returns True if it opened the popup.

    `st` is the trigger's own `interact.State`. A click opens on the
    gesture's own end (`SEL_NONE` for a menu, which `resolve_open` turns
    into the checked row for a listbox); Enter, Space and ArrowDown open on
    the FIRST row; ArrowUp opens a listbox and, measured, does NOT open a
    menu at all - Radix's `DropdownMenuTrigger` answers
    `["Enter", " ", "ArrowDown"]` and nothing else.

    Here rather than in `interact` so that the whole model is in one file
    and a second trigger cannot disagree with the first. The keys are read
    with `is_key_pressed`, which ignores key ownership - that is what lets
    it see a key a widget has claimed.
    """
    from imgui_bundle import imgui
    if disabled:
        return False
    if st.clicked:
        arm(ui, key, SEL_NONE)
        imgui.open_popup(key)
        return True
    if not st.focused or imgui.is_popup_open(key):
        return False
    for k in (imgui.Key.enter, imgui.Key.keypad_enter, imgui.Key.space,
              imgui.Key.down_arrow):
        if imgui.is_key_pressed(k, False):
            arm(ui, key, SEL_FIRST)
            imgui.open_popup(key)
            return True
    # measured: ArrowUp opens a Select and is inert on a DropdownMenu
    if role == "listbox" and imgui.is_key_pressed(imgui.Key.up_arrow, False):
        arm(ui, key, SEL_FIRST)
        imgui.open_popup(key)
        return True
    return False


def _keys(ui, key: str, items, rows, role: str) -> None:
    """Move the highlight for this frame. The OPEN panel's movement keys.

    Called before the rows are drawn, so the highlight the keys chose is the
    one this frame paints. Activation - Enter, Space, Escape - is handled
    after the loop, where a click on a row has already had its say.
    """
    from imgui_bundle import imgui
    st = _kb(ui, key)
    n = len(rows)
    # the key that opened the panel is still down on this frame; see `arm`.
    # NOT popped here - `_end_keys` runs later in the same frame and needs the
    # same answer, so it is the one that clears it.
    if st.get("armed") or not n:
        return
    cur = st["sel"]
    if cur is not None and cur >= n:
        cur = st["sel"] = None

    # CLAMPING, not wrapping, and no none-state between the ends - measured
    # as ArrowDown x24 and ArrowUp x20 off a six-row menu, both sitting on
    # the end row. From NO highlight, down takes the first and up the LAST.
    if imgui.is_key_pressed(imgui.Key.down_arrow, True):
        st["sel"] = 0 if cur is None else min(cur + 1, n - 1)
        return
    if imgui.is_key_pressed(imgui.Key.up_arrow, True):
        st["sel"] = n - 1 if cur is None else max(cur - 1, 0)
        return
    # ArrowRight opens the submenu under the highlight, and does nothing on
    # a row that has none (measured; Enter and Space do the same, and live
    # in `_end_keys` with the rest of a row's activation). ArrowLeft is the
    # OWNER's key, not this one's: it is handled by the level holding the
    # open panel (`_submenus`), which is the only one that can tell whether
    # a deeper panel should answer first.
    if imgui.is_key_pressed(imgui.Key.right_arrow, False):
        row = highlighted_item(items, cur)
        if row is not None and is_sub(items[row]):
            st["open_sub"] = row
        return
    first = [imgui.Key.home]
    last = [imgui.Key.end]
    # PageUp / PageDown are a menu's keys and not a listbox's. Measured:
    # they move a DropdownMenu's highlight to the first / last row (NOT by a
    # page of rows - Radix maps them straight onto first and last, and
    # sixteen rows behaved exactly as six did), and on a Select they do
    # nothing whatever.
    if role != "listbox":
        first.append(imgui.Key.page_up)
        last.append(imgui.Key.page_down)
    if any(imgui.is_key_pressed(k, False) for k in first):
        st["sel"] = 0
        return
    if any(imgui.is_key_pressed(k, False) for k in last):
        st["sel"] = n - 1
        return

    # TYPEAHEAD. The buffer ages out after a second, so it is stepped
    # whether or not anything was typed.
    st["buf_age"] = st.get("buf_age", 0.0) + ui._dt
    if st["buf_age"] > TYPEAHEAD_HOLD:
        st["buf"] = ""
    typed = "".join(chr(c) for c in imgui.get_io().input_queue_characters
                    if c >= 32)
    if not typed:
        return
    st["buf"], st["buf_age"] = st["buf"] + typed, 0.0
    at = next_match(items, rows, st["buf"], st["sel"])
    if at is not None:
        st["sel"] = at


def _begin_keys(ui, key: str, items, x, y, w, role: str,
                frozen: bool = False, off: float = 0.0, hold: bool = False):
    """Resolve the open, let the pointer and the keys move the highlight,
    and hand back which row holds it. Runs BEFORE the rows are drawn.

    Returns a position in `item_rows(items)`, or None for "nothing
    highlighted" - which a pointer-opened menu really is.

    `frozen` holds the KEYS off: a panel with an open submenu has handed
    them to that panel, and two levels both reading ArrowDown would move
    two highlights with one press.

    It does NOT hold the pointer off, and that is the correction to a
    first version which did. A frozen pointer leaves the highlight behind:
    move down a menu, open one row's submenu in passing, carry on to
    another row, and the first row stayed lit while the second ran the
    submenu - two rows lit at once, which is what the owner saw. Nothing
    is lost by letting the pointer through, because the hand-over below
    only happens when the mouse MOVES: a mouse parked over a trigger while
    the keyboard drives the submenu cannot take anything.

    `hold` is the pointer's own exception, and it is the other half of the
    safe triangle (`_keep`): while the pointer is INSIDE this panel's open
    submenu, or cutting the corner toward it, the rows it is passing over
    must not take the highlight either - the row that owns the open panel
    keeps it. Without this the parent lit the row under the pointer while
    the submenu of another row stood open beside it, which is the same two
    rows lit, arrived at the other way round.

    `off` is where the rows START, scrolled (`scrolled`). Without it a
    capped panel hit-tests the pointer against the UNSCROLLED rows: on a
    32-row submenu scrolled 266px, a pointer 20px into the panel is over
    row 11 and this said row 1 — so Enter took a row nobody was pointing
    at, and `_scroll` then dragged the list back to show it.
    """
    from imgui_bundle import imgui
    st = _kb(ui, key)
    rows = item_rows(items)

    # Is this the frame the panel appeared on? Counted in FRAMES rather than
    # read off `LAST_RECT`, which would be the obvious seam and is the wrong
    # one: `LAST_RECT` is cleared by `popup`'s CLOSED branch, so it only
    # answers for a caller that hands the popup a closed frame. One did not -
    # `interact.select` called `popup` under `if open_`, which is fixed, and
    # which is a thing a future caller can get wrong again for free. A frame
    # count depends on nothing outside this function.
    fc = imgui.get_frame_count()
    fresh = st.get("frame", -10) != fc - 1
    st["frame"] = fc
    if fresh:
        # Nobody armed it => the POINTER opened it, and measured, a click
        # opens a menu with NOTHING highlighted. `resolve_open` turns that
        # into the checked row for a listbox, which is the Select's rule.
        want = st["sel"] if st.get("armed") else SEL_NONE
        st["sel"] = resolve_open(want, items, rows,
                                 on_checked=(role == "listbox"))
        st["buf"], st["buf_age"] = "", 0.0

    # The pointer takes the highlight only when it MOVES. Radix hands it over
    # on `onPointerMove`, and taking it every frame would let a parked mouse
    # override the arrow keys - which is the whole reason cmdk carries
    # `disablePointerSelection`. Hit-tested on geometry rather than on
    # `ui.hit`, so it can be read before the row is submitted and the
    # highlight the keys chose is the one THIS frame paints.
    io = imgui.get_io()
    if rows and not hold and (io.mouse_delta.x or io.mouse_delta.y):
        iy = y - off
        for i, it in enumerate(items):
            if i in rows and imgui.is_mouse_hovering_rect(
                    imgui.ImVec2(x, iy), imgui.ImVec2(x + w, iy + ITEM_H)):
                st["sel"] = rows.index(i)
            iy += row_h(it)

    # second, so an arrow beats the pointer on a frame that carries both
    if not frozen:
        _keys(ui, key, items, rows, role)
    return st["sel"]


def _end_keys(ui, key: str, items) -> str | None:
    """Enter and Space on the highlight. Runs AFTER the rows are drawn.

    Escape and Tab are both deliberately absent:

    * **Escape** is already ImGui's - it dismisses the top popup on its own,
      and measured on the kit it always did. The Combobox has to close its
      popup by hand only because an `InputText` inside it eats the first
      Escape as "cancel the edit"; a menu holds no text field, so there is
      nothing to eat it.
    * **Tab** is swallowed, which is what the real menu does
      (`if (event.key === "Tab") event.preventDefault()` in Radix's menu
      content) - and so there is nothing to write. ImGui will not tab out of
      a popup window, and with every row submitted `nav=False` there is
      nothing inside one for a Tab to reach either. Measured on the real
      component: three Tabs and a Shift+Tab all left the menu open on the
      same row. This is the one place the kit was right by accident, and it
      is the opposite of the Combobox, where Tab closes the list and moves
      on.
    """
    from imgui_bundle import imgui
    st = _kb(ui, key)
    rows = item_rows(items)
    hi = st.get("sel")
    # The key that OPENED the panel must not be taken by it either. Enter and
    # Space BOTH open a menu and commit a row, so without this an opening
    # Enter commits whatever the open resolved to and the panel flashes:
    # measured on the dashboard's Plane Select, where Enter on the closed
    # trigger opened the list and chose the committed row in one frame.
    # `arm` sets the flag, `_keys` reads it, and this clears it - last in the
    # frame, so both halves see the same answer.
    if st.pop("armed", False):
        return None
    # Space SELECTS when the typeahead buffer is empty and is a typeahead
    # CHARACTER while it is live. Measured both ways on `menu.kb`: Space on a
    # fresh open selected and closed; 'e' then Space inside the second left
    # the menu open on Epsilon; 'e', 1.3s, then Space selected it. Radix:
    # `if (isTypingAhead && event.key === " ") return`.
    take = (imgui.is_key_pressed(imgui.Key.enter, False)
            or imgui.is_key_pressed(imgui.Key.keypad_enter, False)
            or (not st.get("buf")
                and imgui.is_key_pressed(imgui.Key.space, False)))
    # With NOTHING highlighted both keys do nothing at all and the menu stays
    # open - measured on a pointer-opened `menu.kb`. Not the Combobox's rule,
    # where an Enter with no highlight closes the list.
    if not take or hi is None or not (0 <= hi < len(rows)):
        return None
    it = items[rows[hi]]
    if is_sub(it):
        # Measured: Enter and Space on a SubTrigger open it and highlight
        # its first row, and the parent panel stays up - they are
        # ArrowRight, not a choice.
        st["open_sub"] = rows[hi]
        return None
    imgui.close_current_popup()
    return getattr(it, "id", "")


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
    # A SubTrigger's rows. Empty for an ordinary item; set, the row grows a
    # chevron and `popup` hangs a panel off it (`SUBMENUS, measured`). A
    # tuple rather than a list so an Item stays hashable-ish and two menus
    # cannot share one mutable child list by accident.
    items: tuple = ()


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
    # draw.shadow_stack, not a loop of its own: CSS lists shadows FRONT to
    # back, so they have to go up reversed, and this loop went up forward
    # and dropped dx on the floor. Both are invisible on SHADOW_MD - two
    # layers of the same colour and alpha composite to the same result in
    # either order, and neither carries a dx - so this is pixel-neutral
    # today and was one differently-shaped token away from not being.
    D.shadow_stack(dl, x, y, w, h, T.RADII["lg"],
                   [(dx, dy, blur, spread, al * a)
                    for dx, dy, blur, spread, al in T.SHADOW_MD])
    D.fill(dl, x, y, w, h, ui.col("popover", a), T.RADII["lg"])
    D.border(dl, x - 1, y - 1, w + 2, h + 2,
             ui.col("foreground", 0.10 * a), T.RADII["lg"] + 1, 1.0)
    dl.pop_clip_rect()


def sub_chrome(ui, dl, x, y, w, h, a: float = 1.0) -> None:
    """A SubContent panel's chrome: shadow-lg, bg-popover, and a 1px
    `border` INSIDE the box.

    Not `panel_chrome` with a bigger shadow. The top panel's outline is a
    `ring-1` box-shadow, which sits wholly OUTSIDE the box and costs its
    rows nothing; a SubContent carries `border`, which is a real CSS border
    and takes a pixel off each edge. That one pixel is why a sub panel is
    2px wider and taller than its rows need and why its rows start 5px in,
    and it is measurable: the 128x103 panel measured `1 + 4 + 28 + 28 + 9 +
    28 + 4 + 1` tall with its first row at `panel.y + 5`.
    """
    dl.push_clip_rect(imgui.ImVec2(x - 20, y - 20),
                      imgui.ImVec2(x + w + 20, y + h + 20), False)
    D.shadow_stack(dl, x, y, w, h, T.RADII["lg"],
                   [(dx, dy, blur, spread, al * a)
                    for dx, dy, blur, spread, al in SUB_SHADOW])
    D.fill(dl, x, y, w, h, ui.col("popover", a), T.RADII["lg"])
    D.border(dl, x, y, w, h, ui.col("border", a), T.RADII["lg"], SUB_BORDER)
    dl.pop_clip_rect()


def sub_size(ui, items) -> tuple[float, float]:
    """A submenu panel's box for `items`: its rows, its padding and its
    border. One function because the placement and the window size must not
    be able to disagree.

    `min-w-32` is the floor on the PANEL, so the border comes off it before
    `measure` is asked for a content width - otherwise the floor is applied
    to the rows and the panel comes out 130 wide where the browser measures
    128 and its rows 118.
    """
    edge = 2 * (PAD + SUB_BORDER)
    cw, ch = measure(ui, items, SUB_MIN_W - 2 * SUB_BORDER,
                     MAX_W - 2 * SUB_BORDER)
    return cw + edge, ch + edge


def _dismiss(ui, key: str) -> None:
    """Close the popup `key` if ImGui is still holding it open.

    `imgui.close_current_popup` closes the popup it is called INSIDE and
    nothing else, so a submenu the parent has decided to close cannot be
    closed from the parent: it has to be begun one last time to dismiss
    itself. Begun at 1x1 with a transparent ground and nothing drawn in it,
    so the frame it goes on paints nothing.

    Not optional, and not only tidiness: without it the panel stays on
    ImGui's popup stack with nobody submitting it, and `LAST_RECT` keeps the
    rect of a panel that is no longer there - the exact staleness
    `test_menu_keys._painted` exists because of.
    """
    if imgui.is_popup_open(key):
        old = LAST_RECT.get(key) or (0.0, 0.0)
        imgui.set_next_window_pos(imgui.ImVec2(old[0], old[1]))
        imgui.set_next_window_size(imgui.ImVec2(1.0, 1.0))
        imgui.push_style_color(imgui.Col_.popup_bg, imgui.ImVec4(0, 0, 0, 0))
        imgui.push_style_var(imgui.StyleVar_.popup_border_size, 0.0)
        if imgui.begin_popup(key, imgui.WindowFlags_.no_scrollbar
                             | imgui.WindowFlags_.no_focus_on_appearing):
            imgui.close_current_popup()
            imgui.end_popup()
        imgui.pop_style_var()
        imgui.pop_style_color()
    # ITS descendants too. `_dismiss` begins this panel only to close it, so
    # the closed branch of `sub_popup` — which is what normally forgets a
    # chain — never runs for it, and its own `open` and `shown` would still
    # name the grandchild. Reopening the panel then brought that grandchild
    # straight back without its trigger ever being hovered.
    _forget(ui, key)
    LAST_RECT.pop(key, None)
    ui.anim.to(f"{key}:open", 0.0)


def chain_side(trig, avail, width: float = MAX_W) -> str:
    """Which side a whole chain of submenus opens on: "right" or "left".

    Decided ONCE, when a menu's first submenu opens, and kept for every
    level under it. Each level choosing for itself is what made the menus
    jump: a narrow panel fits to the right of a trigger near the window's
    edge and a wide one does not, so `insert ▸` opened rightward and
    `effects ▸` under it flipped back over the top of it. Nothing about the
    menu changed between those two moments except how long one word was.

    `width` is what a panel may take at most (`MAX_W`), not what the next
    one happens to need — that is the whole point. A side with room for the
    widest panel the kit can draw has room for every panel in the chain, so
    the decision taken here cannot be overtaken by a later level.
    """
    if not isinstance(trig, B.Rect):
        trig = B.Rect(*trig)
    if trig.right + width <= avail.right:
        return "right"
    if trig.x - width >= avail.x:
        return "left"
    # neither side has room for the widest panel: take the roomier one,
    # which is the same rule `place_sub` falls back on
    return "right" if (avail.right - trig.right) >= (trig.x - avail.x) else "left"


def place_sub(trig, w: float, h: float, avail, side: str = "") -> B.Rect:
    """Where a submenu panel goes beside its trigger row. Pure geometry.

    The law is measured: `x = trigger.right`, `y = trigger.y`, anchored on
    the TRIGGER and not on the panel - Radix's implicit `side="right"
    align="start"` with no offset.

    The flip is not. Radix leaves a SubContent hanging off the edge (in a
    250px viewport it stayed at `trigger.right` and overhung by 20px, the
    same way `place_at_pointer` records for the panel itself), so this
    flips to the trigger's LEFT when the right does not fit, keeping the
    side that overflows less when neither does. An ImGui popup that leaves
    the window is simply lost, which is the reason the divergence is worth
    it here and was worth it there.

    `side` is the chain's own, from `chain_side`, and when it is given it
    is obeyed rather than worked out per panel: a chain that opens leftward
    stays leftward, however wide its levels turn out to be.
    """
    if not isinstance(trig, B.Rect):
        trig = B.Rect(*trig)
    h = min(h, max(avail.h, 0.0))
    if side == "left":
        x = trig.x - w
    elif side == "right":
        x = trig.right
    else:
        x = trig.right
        if x + w > avail.right:
            alt = trig.x - w
            if (avail.x - alt) < (x + w - avail.right):
                x = alt
    # clamp last, and low last of all, as `place_at_pointer` does: a panel
    # that cannot fit pins to the top-left rather than hiding its first row
    x = min(x, avail.right - w)
    x = max(x, avail.x)
    y = min(trig.y, avail.bottom - h)
    return B.Rect(x, max(y, avail.y), w, h)


def _side(a, b, p) -> float:
    """Which side of the line a->b the point p is on (its cross product)."""
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def in_triangle(p, a, b, c) -> bool:
    """Is `p` inside the triangle `a b c` (edges count as inside)."""
    d1, d2, d3 = _side(a, b, p), _side(b, c, p), _side(c, a, p)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def aiming_at(prev, now, rect) -> bool:
    """Is the pointer on its way INTO the panel at `rect`?

    The wedge is `prev` and the panel's two NEAR corners - its left edge
    when the panel is to the right, its right edge when it is to the left.
    A pointer anywhere in that wedge is moving toward the panel however
    many rows lie under the diagonal, which is the whole trick: without it
    the rows between a trigger and the far corner of its own panel each
    take the pointer in turn and close the panel it was heading for.

    Pure geometry, so the rule can be read without a GL context.
    """
    if prev is None or rect is None or prev == now:
        # A PARKED pointer is heading nowhere, and the degenerate triangle a
        # zero-length move makes contains every point — so without this the
        # wedge is "true" for as long as the hand rests on the trigger, and
        # its patience (`AIM_HOLD_S`) is spent before the move it exists for
        # has even started. Measured in the app: five seconds of it.
        return False
    x, y, w, h = rect
    near_x = x if now[0] <= x else x + w
    if x <= now[0] <= x + w:
        return False                    # already over the panel: not "toward"
    if (near_x - now[0]) * (near_x - prev[0]) < 0:
        return False                    # it has crossed the panel's edge line
    return in_triangle(now, prev, (near_x, y), (near_x, y + h))


def _subs(ui, key: str) -> dict:
    """Which of `key`'s rows has its submenu open, and the hover timer.

    On `ui.anim.store` for the reason `_kb` is: a `Ui` is rebuilt every
    frame, so anything that has to outlive one - an open panel, a dwell -
    cannot live on it.
    """
    return ui.anim.store.setdefault("menusub", {}).setdefault(
        key, {"open": None, "hot": None, "age": 0.0})


def _forget(ui, key: str) -> None:
    """Drop every record of `key`'s submenu chain, closed panels and all.

    ImGui closes a child popup with its parent, so when the top panel goes
    nothing submits the children again and their `LAST_RECT` entries would
    outlive the panels - which is a seam going stale, the thing
    `test_menu_keys._painted` exists because of.
    """
    st = _subs(ui, key)
    shown = st.get("shown")
    if shown is not None:
        _forget(ui, shown)
        LAST_RECT.pop(shown, None)
        ui.anim.to(f"{shown}:open", 0.0)
    st["open"], st["shown"], st["hot"], st["age"] = None, None, None, 0.0
    st["side"] = None           # the next open decides it afresh
    # and the pointer's claim on a row, or a panel dismissed with the
    # pointer inside it would dwell its child open again on the way back
    st["pointer_row"] = None


def _keep(ui, st: dict) -> bool:
    """Should this panel's open submenu stay open, whatever row the pointer
    is geometrically over?

    Two reasons it should, and the first is not the clever one:

    * **the pointer is IN it.** `is_mouse_hovering_rect` knows nothing
      about which window is on top, so a parent panel reads the pointer as
      being on one of its own rows while it is really inside the submenu
      drawn over them — and closed the submenu the pointer had reached.
      The two panels overlap by four pixels by construction (the submenu
      starts at `trigger.right`, which is inside the parent's padding), so
      this is not an edge case: every approach from the parent's side
      crosses it.
    * **the pointer is on its way in** — the safe triangle.

    Keeps the wedge's origin ~`AIM_SAMPLE_S` old rather than last frame's
    point: a wedge drawn from 16ms ago is barely a direction at all, and
    one drawn from a quarter of a second ago is the path the hand is
    actually on. A pointer that sits in the wedge without arriving gives up
    after `AIM_HOLD_S`, so a menu can never be stuck open by a parked
    mouse. Having ARRIVED never ages out: the submenu is the pointer's.
    """
    m = imgui.get_mouse_pos()
    now = (m.x, m.y)
    st["aim_t"] = st.get("aim_t", 0.0) + ui._dt
    if st.get("aim_from") is None or st["aim_t"] >= AIM_SAMPLE_S:
        st["aim_from"], st["aim_t"] = st.get("aim_now", now), 0.0
    st["aim_now"] = now
    rect = LAST_RECT.get(st.get("shown") or "") if st.get("open") is not None else None
    if rect is None:
        st["aim_age"] = 0.0
        return False
    x, y, w, h = rect
    if x <= now[0] < x + w and y <= now[1] < y + h:
        st["aim_age"] = 0.0
        return True                     # arrived
    if not aiming_at(st.get("aim_from"), now, rect):
        st["aim_age"] = 0.0
        return False
    st["aim_age"] = st.get("aim_age", 0.0) + ui._dt
    return st["aim_age"] < AIM_HOLD_S


def _submenus(ui, key: str, items, rects: dict, over, a: float, *,
              row_id=None) -> str | None:
    """Open, close and draw `key`'s submenus. Returns a chosen id, or None.

    Called from INSIDE the parent's popup window, which is what makes the
    panel a nested ImGui popup: `open_popup` registers at the current popup
    stack level, so ImGui closes the submenu when the parent goes, keeps it
    above everything, and dismisses the lot on a click away. None of that
    is reimplemented here.

    `rects` is `{index: Rect}` for the SubTrigger rows drawn this frame and
    `over` the index of the row the pointer is on (None for none of them -
    including when the pointer is inside the submenu, which is exactly when
    the panel has to STAY open).
    """
    st, kb = _subs(ui, key), _kb(ui, key)
    # already worked out this frame, before the keys ran (`popup`)
    aim = st.get("keep", False)
    # A row is the POINTER'S only by motion, exactly as the highlight is
    # (`_begin_keys`). `over` is pure geometry and answers the same every
    # frame a mouse rests, so hanging the hover rules on it let a parked
    # mouse act: ArrowRight opened a submenu and the row the mouse happened
    # to be resting on closed it again on the very next frame, with nobody
    # touching the mouse. The dwell still runs while the pointer rests —
    # that is what a dwell is — but on the row it last MOVED onto.
    io = imgui.get_io()
    # A SCROLL moves the rows under a pointer that has not moved at all, so
    # the claim has to be re-taken then too: wheel a capped panel and the
    # trigger under the cursor changes without a pixel of `mouse_delta`,
    # and the panel of the row that USED to be there would otherwise stay
    # open over the one that is.
    off = scrolled(ui, key)
    if io.mouse_delta.x or io.mouse_delta.y or off != st.get("off"):
        st["pointer_row"] = over
    st["off"] = off
    on = st.get("pointer_row")
    # `by_key` is the row a KEY asked to open — ArrowRight, Enter or Space.
    # It is not the same as "a panel opened this frame", and conflating the
    # two armed a HOVER-opened panel on its first row: measured, a hover
    # open highlights nothing, and a row lit under a pointer that is still
    # in the parent is the second of the two rows the owner saw lit at once.
    by_key = kb.pop("open_sub", None)
    if by_key is not None and by_key in rects:
        st["open"], st["hot"], st["age"] = by_key, by_key, 0.0
        # The keyboard has taken the panel, so the pointer's claim is
        # DROPPED rather than moved onto this row: a mouse resting
        # elsewhere must not close what the keys just opened, and a row
        # the keys opened must not read as hovered either — that would
        # re-open it the moment ArrowLeft closed it. The next real
        # movement gives the pointer a row again.
        st["pointer_row"] = None
    elif aim:
        # in the open panel, or on its way into it: the rows it crosses do
        # nothing, and neither their dwell nor the open one's closing may
        # start (`_keep`)
        pass
    elif on is not None and on != st["open"]:
        # The pointer is on ANOTHER row, so the open panel goes at once —
        # whether that row has a submenu of its own or not. Closing is
        # immediate and only OPENING is on Radix's 100 ms timer, and the
        # two were conflated here: a move from one SubTrigger to the next
        # left the first panel up for the whole dwell, so for six frames
        # the menu had TWO rows lit, the old one on `data-open` and the new
        # one on hover. The real component never shows that.
        st["open"] = None
        # the dwell is per ROW: moving along them must not pour one row's
        # wait into the next
        if st["hot"] != on:
            st["hot"], st["age"] = on, 0.0
        st["age"] += ui._dt
        if on in rects and st["age"] >= SUB_OPEN_S:
            st["open"] = on

    at = st["open"]
    subkey = ""
    if at is not None and at in rects:
        it = items[at]
        subkey = f"{key}>{getattr(it, 'id', '') or at}"
        # ArrowLeft and Escape belong to the DEEPEST open panel: with a
        # level below this one up, that level answers them and this one
        # must not, or one press would collapse two panels.
        if _subs(ui, subkey)["open"] is None:
            if imgui.is_key_pressed(imgui.Key.left_arrow, False):
                # measured: the highlight is left on the trigger, where it
                # already is, so there is nothing to restore. The pointer's
                # claim goes with it, or the row it was resting on would
                # dwell the panel straight back open.
                at = st["open"] = None
                st["pointer_row"] = None
            elif imgui.is_key_pressed(imgui.Key.escape, False):
                # measured: Escape in a submenu closes the WHOLE menu.
                # ImGui's own Escape closes only the topmost popup, so each
                # level says so on its way out and the chain goes together.
                at = st["open"] = None
                imgui.close_current_popup()
    else:
        at = st["open"] = None

    # A panel this level was showing and is not any more has to be begun
    # once more to be dismissed (`_dismiss`).
    shown = st.get("shown")
    if shown is not None and shown != (subkey if at is not None else ""):
        _dismiss(ui, shown)
        st["shown"] = None
    if at is None:
        return None

    st["shown"] = subkey
    root = _subs(ui, key.split(">")[0])
    if root.get("side") is None:
        root["side"] = chain_side(rects[at], ui.viewport)
    if not imgui.is_popup_open(subkey):
        imgui.open_popup(subkey)
        if by_key is not None:
            # a KEY opened it: measured, the first row is highlighted. A
            # hover open highlights nothing, which is what no `arm` means.
            arm(ui, subkey, SEL_FIRST)
    chosen = sub_popup(ui, subkey, items[at].items, rects[at], a,
                       row_id=row_id, side=root["side"])
    if chosen is not None:
        st["open"] = None
    return chosen


def sub_popup(ui, key: str, items, trig, a: float = 1.0, *,
              row_id=None, side: str = "") -> str | None:
    """Draw one submenu panel beside `trig`. Returns the chosen id.

    The panel is a nested ImGui popup with `no_focus_on_appearing`, and
    that flag is the whole trick. A popup that takes focus takes hovering
    with it: ImGui's `IsWindowContentHoverable` refuses hover to every
    window outside the focused popup's begin-stack chain, so a focused
    submenu would make its own PARENT dead to the mouse - no switching to
    another row, no click on one. Left unfocused, the parent keeps focus
    and hover, the submenu is hoverable as its child, and Escape keeps
    reaching the parent, which is what the measured "Escape closes the
    whole menu" needs.
    """
    w, h = sub_size(ui, items)
    at = place_sub(trig, w, h, ui.viewport, side)
    # `place_sub` clamps a panel taller than the viewport, which on its own
    # would CUT the rows off the bottom: the look-back frame menu is 32
    # rows, 906px, and the last of them cannot be clicked in any window
    # shorter than that. Capped, the rows scroll, exactly as `popup`'s do.
    scrolls = at.h < h - 0.5
    imgui.set_next_window_pos(imgui.ImVec2(at.x, at.y))
    imgui.set_next_window_size(imgui.ImVec2(at.w, at.h))
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
    imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
    imgui.push_style_var(imgui.StyleVar_.popup_border_size, 0.0)
    imgui.push_style_var(imgui.StyleVar_.popup_rounding, T.RADII["lg"])
    imgui.push_style_color(imgui.Col_.popup_bg, imgui.ImVec4(0, 0, 0, 0))
    chosen = None
    if imgui.begin_popup(
            key,
            imgui.WindowFlags_.no_scrollbar
            | imgui.WindowFlags_.no_scroll_with_mouse
            | imgui.WindowFlags_.no_focus_on_appearing):
        op = ui.anim.to(f"{key}:open", 1.0)
        dl = imgui.get_window_draw_list()
        p = imgui.get_window_pos()
        x, y = p.x, p.y
        LAST_RECT[key] = (x, y, at.w, at.h)
        saved, ui.dl = ui.dl, dl
        sub_chrome(ui, dl, x, y, at.w, at.h, op)
        inset = PAD + SUB_BORDER
        cw = at.w - 2 * inset
        ch = h - 2 * inset              # the rows' own height, uncapped
        sub_st = _subs(ui, key)
        frozen = sub_st["open"] is not None
        sub_st["keep"] = _keep(ui, sub_st)
        hi = highlighted_item(
            items, _begin_keys(ui, key, items, x + inset, y + inset, cw,
                               "menu", frozen,
                               scrolled(ui, key) if scrolls else 0.0,
                               sub_st["keep"]))
        off = 0.0
        if scrolls:
            off = _scroll(ui, key, items, hi, at.h - 2 * inset, ch)
            dl.push_clip_rect(imgui.ImVec2(x, y + inset),
                              imgui.ImVec2(x + at.w, y + at.h - inset), True)
        chosen, rects, over = _row_loop(
            ui, key, items, x + inset, y + inset - off, cw, op, at=hi,
            row_id=row_id, keyboard=True,
            window=(y + inset, y + at.h - inset) if scrolls else None)
        if scrolls:
            dl.pop_clip_rect()
            view = at.h - 2 * inset
            tw = 4.0
            th = max(view * view / ch, 16.0)
            ty = y + inset + (view - th) * (off / max(ch - view, 1.0))
            D.fill(dl, x + at.w - tw - 2.0 - SUB_BORDER, ty, tw, th,
                   ui.col("border", op), tw / 2)
        if chosen is not None:
            imgui.close_current_popup()
        else:
            chosen = _submenus(ui, key, items, rects, over, op, row_id=row_id)
            if chosen is not None:
                imgui.close_current_popup()
        if chosen is None and not frozen:
            chosen = _end_keys(ui, key, items)
        ui.dl = saved
        imgui.end_popup()
    else:
        LAST_RECT.pop(key, None)
        ui.anim.to(f"{key}:open", 0.0)
        # a closed panel holds no open submenu: without this, the next open
        # of the same menu comes up with the last submenu already showing -
        # and its children's rects outlive the children
        _forget(ui, key)
    imgui.pop_style_color()
    imgui.pop_style_var(4)
    return chosen


def _row_loop(ui, key: str, items, x: float, y: float, cw: float, a: float, *,
              at, row_id=None, keyboard: bool = True, window=None):
    """The row stride, shared by `popup` and `sub_popup`.

    Returns `(chosen id or None, {index: Rect} of the SubTrigger rows, the
    index of the row the pointer is on or None)`. The last two are what
    `_submenus` needs and neither can be worked out from outside the loop:
    a row's rect is only known once the stride has walked to it.

    `window` is `(top, bottom)` for a panel whose rows scroll: a row
    outside it is not submitted at all, which is `popup`'s cap.
    """
    chosen, rects, over = None, {}, None
    sub_open = _subs(ui, key)["open"]
    iy = y
    for i, it in enumerate(items):
        rh = row_h(it)
        if window is not None and (iy + rh <= window[0] or iy >= window[1]):
            iy += rh                # out of view: not submitted
            continue
        rk = row_id(it, i) if row_id is not None else f"{key}.{i}"
        # `data-open:bg-accent`: an open SubTrigger is painted exactly as a
        # highlighted row is, so the pointer can be inside the submenu and
        # the row it came through stays lit.
        lit = (i == at) or (i == sub_open)
        hit = _row(ui, it, x, iy, cw, rk, a,
                   hi=lit if (keyboard or i == sub_open) else None)
        if is_sub(it):
            rects[i] = B.Rect(x, iy, cw, ITEM_H)
            if hit:                 # a click on a SubTrigger opens it
                _kb(ui, key)["open_sub"] = i
        elif hit:
            chosen = it.id
        if it.kind == "item" and imgui.is_mouse_hovering_rect(
                imgui.ImVec2(x, iy), imgui.ImVec2(x + cw, iy + ITEM_H)):
            over = i
        iy += rh
    return chosen, rects, over


def rows(ui, items, x, y, w, key, a: float = 1.0, *,
         chrome_only: bool = False):
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
    # No `hi`: this path has no popup to route a key through, so every row
    # falls back to its own hover, which is the gallery's chrome diff and is
    # what it has always drawn. The keyboard highlight belongs to `popup`,
    # which owns the key routing and the state that outlives the frame.
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


def label_room(it, cw: float, ui) -> float:
    """How much of a row `cw` wide is left for its label.

    The same reservations `measure` makes, read the other way round: what
    the label may take once its icon, its chevron and its shortcut have
    had theirs. `_row` draws to it, so a label that did not fit is
    ellipsised rather than running under the chevron or off the panel.
    """
    room = cw - 2 * ITEM_PAD_X
    if it.icon or it.checked is not None:
        room -= ICON + GAP
    if is_sub(it):
        room -= GAP + ICON
    if it.shortcut:
        room -= GAP + D.text_w(it.shortcut, ui.faces, "regular", 12, True) \
            + SHORTCUT_TRACKING * len(it.shortcut)
    return max(room, 0.0)


def measure(ui, items, min_w: float = MIN_W,
            max_w: float = MAX_W) -> tuple[float, float]:
    """The content box a menu needs, before chrome padding.

    Capped at `max_w` (`MAX_W`): past it a row's label is ellipsised, which
    is this kit's policy rather than the browser's — see MAX_W.
    """
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
        if is_sub(it):
            # the chevron, with ONE gap - measured, the same law the
            # shortcut follows and for the same reason
            extra += GAP + ICON
        if it.shortcut:
            # ONE gap, not two: measured at max-content a row is
            # `pad + label + gap + shortcut + pad`, which came to the panel
            # width to the 1/64 px. Reserving two made every menu with a
            # shortcut 6px wider than the browser's.
            extra += GAP + D.text_w(it.shortcut, ui.faces, "regular", 12,
                                    True) + SHORTCUT_TRACKING * len(it.shortcut)
        w = max(w, tw + extra)
    if max_w:
        w = min(w, max_w - 2 * PAD)
    return w, h


def _row(ui, it, x, y, w, key, alpha, *, chrome_only: bool = False,
         hi: bool | None = None):
    """One menu row. Returns True if it was chosen this frame.

    `hi` is whether this row holds THE highlight - the real component has
    exactly one `data-highlighted` and either the pointer or the keyboard
    owns it. `popup` always passes a bool, because it owns the highlight and
    feeds the pointer into it on movement; `None` falls back to this row's
    own hover, which is the `rows()` path - the gallery's chrome diff, which
    has no popup to route a key through and no keyboard to route.
    """
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

    # `nav=False`, and it is not an optimisation. An `invisible_button` with
    # `enable_nav` is reported by `is_item_hovered` while merely NAV-focused,
    # so ImGui's own nav cursor was driving the kit's hover tint through the
    # menu - which looked like a keyboard highlight and was not one. It
    # started on the second row (ImGui parks NavId on the first item when the
    # popup appears and the arrow then moves it on), it WRAPPED at both ends
    # where the real one clamps, and Enter never took the row. The menu's
    # items carry `tabIndex -1` on the real component and are driven by a
    # roving-focus group, so taking them out of ImGui's tab order is the
    # faithful thing as well as the one that leaves the kit owning the
    # highlight. Tab stays trapped either way: ImGui will not tab out of a
    # popup window, and with nothing navigable inside it there is nowhere
    # for a Tab to go - which is what the real menu does too.
    st = None if chrome_only else (ui.hit(key, x, y, w, ITEM_H, nav=False)
                                   if it.enabled else None)
    hot = ui.anim.to(f"{key}:hi", 1.0 if hi else 0.0) if hi is not None \
        else (st.hot if st else 0.0)
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
            baseline_box=ITEM_H, max_w=max(x + w - ITEM_PAD_X - tx - _after(it, ui), 0.0))
    if it.shortcut:
        D.label(ui.dl, x, y, it.shortcut, ui.faces, "regular", 12,
                sc_ink, align="right",
                box_w=w - ITEM_PAD_X, baseline_box=ITEM_H, tabular=True)
    if is_sub(it):
        # ChevronRightIcon, `ml-auto`: its right edge is the row's right
        # edge less the row's own padding (measured 136 in a 142-wide row)
        D.icon(ui.dl, CHEVRON, x + w - ITEM_PAD_X - ICON,
               y + (ITEM_H - ICON) / 2, ICON, ink)
    return bool(st and st.clicked)


def scrolled(ui, key: str) -> float:
    """How far `key`'s rows were scrolled when they were last DRAWN.

    `_scroll` cannot answer before the highlight is known and the highlight
    cannot be read before the rows the pointer is over are known, which is
    a circle. Last frame's offset breaks it, and it is the right answer
    rather than a convenient one: the rows under the pointer now are the
    rows that were painted last frame, at last frame's offset.
    """
    return ui.anim.store.get("menu_scroll", {}).get(key, 0.0)


def _after(it, ui) -> float:
    """What a row keeps to the RIGHT of its label: the chevron of a
    SubTrigger, or a shortcut. The label is drawn to what is left."""
    if is_sub(it):
        return GAP + ICON
    if it.shortcut:
        return GAP + D.text_w(it.shortcut, ui.faces, "regular", 12, True) \
            + SHORTCUT_TRACKING * len(it.shortcut)
    return 0.0


def _scroll(ui, key: str, items, at, view: float, content: float) -> float:
    """The scroll of a capped menu (`popup`'s `max_h`), kept with the
    menu's state: moved by the wheel over the panel, and — when the
    keyboard highlight moves — just enough to show its row."""
    st = ui.anim.store.setdefault("menu_scroll", {})
    off = st.get(key, 0.0)
    if imgui.is_window_hovered():
        off -= imgui.get_io().mouse_wheel * ITEM_H
    if at is not None and st.get(f"{key}:at") != at:
        top = sum(row_h(it) for it in items[:at])
        off = min(max(off, top + row_h(items[at]) - view), top)
    st[f"{key}:at"] = at
    off = min(max(off, 0.0), max(content - view, 0.0))
    st[key] = off
    return off


def popup(ui, key: str, items, *, min_w: float = MIN_W, anchor=None,
          side: str = "bottom", align: str = "end",
          offset: float = 4.0, role: str = "menu",
          keyboard: bool = True, row_id=None, max_h: float | None = None) -> str | None:
    """Draw the menu `key` if ImGui has it open. Returns the chosen item id.

    `row_id(item, index)` names each row's hit target, for a host whose
    tests find a row by its own id (Hyperspace's side pane: ``pane.fx``);
    by default a row is ``<key>.<index>``.

    `max_h` caps the panel's height: past it the rows scroll — the wheel
    over the panel, and the keyboard highlight pulling its row into view —
    clipped to the panel, a thin thumb at its right edge saying how much
    there is. Only the rows in view are submitted. None: as tall as its
    rows (the measured component, which has no cap of its own).

    The keyboard is the measured model in THE KEYBOARD above, and it lives
    here so that the dropdown, the ContextMenu and the Select inherit one
    answer rather than three. `role` is the only thing that varies:

        "menu"      a DropdownMenu or a ContextMenu. PageUp / PageDown move
                    the highlight to the ends; an open starts where the
                    gesture asked (nothing, for a pointer).
        "listbox"   a Select. PageUp / PageDown do nothing at all, and an
                    open starts on the CHECKED row whatever the gesture.

    Both were measured; neither is a guess about the other. `keyboard=False`
    turns the whole of it off, for a caller that owns the keys itself.

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
    scrolls = False
    if max_h is not None and h > max_h:
        h, scrolls = max_h, True

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
    # `PopupBorderSize` is a SEPARATE style var, 1.0 by default, and
    # `WindowBorderSize` does not cover it. This panel fills its window
    # exactly, so the stray 1px has always been hidden under the panel's
    # own chrome - which is luck rather than a decision. The Combobox,
    # whose window spans the trigger too, is where that luck ran out.
    imgui.push_style_var(imgui.StyleVar_.popup_border_size, 0.0)
    imgui.push_style_var(imgui.StyleVar_.popup_rounding, T.RADII["lg"])
    imgui.push_style_color(imgui.Col_.popup_bg, imgui.ImVec4(0, 0, 0, 0))
    chosen = None
    # NO SCROLLBAR, and `begin_popup` will give you one unless you say so.
    #
    # `BeginPopup` adds `AlwaysAutoResize` to whatever flags you pass, and a
    # window with that flag works its size out from the extent its CURSOR
    # reached. This popup places things absolutely with
    # `set_cursor_screen_pos` and holds a child window, so on a frame where
    # that extent lands past the explicit `set_next_window_size`, ImGui
    # draws the WINDOW's own scrollbar - a bright grey bar down the right
    # of the panel, for a frame, on open.
    #
    # It is the window's bar, not the list's: the list runs `bars=False`
    # because the real component carries `no-scrollbar`. Select never showed
    # it because its panel holds no child window, so its extent cannot
    # overshoot. This is the only popup in the kit that can.
    if imgui.begin_popup(
            key,
            imgui.WindowFlags_.no_scrollbar
            | imgui.WindowFlags_.no_scroll_with_mouse):
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

        # `at` is an index into `items`; `hi` counts only the rows a
        # highlight can land on. `None` for `at` is a real answer - nothing
        # highlighted, which is what a pointer-opened menu is.
        at = None
        # a panel with a SUBMENU up hands its keys to that panel, and holds
        # its own highlight where it is (`_begin_keys`' `frozen`)
        sub_st = _subs(ui, key)
        frozen = sub_st["open"] is not None
        # ONCE a frame, and before the keys: `_keep` ages a timer, and the
        # pointer's hand-over has to know its answer
        sub_st["keep"] = _keep(ui, sub_st)
        if keyboard:
            at = highlighted_item(
                items, _begin_keys(ui, key, items, x + PAD, y + PAD, cw, role,
                                   frozen, scrolled(ui, key) if scrolls else 0.0,
                                   sub_st["keep"]))

        off = 0.0
        if scrolls:
            off = _scroll(ui, key, items, at, h - 2 * PAD, ch)
            dl.push_clip_rect(imgui.ImVec2(x, y + PAD), imgui.ImVec2(x + w, y + h - PAD), True)
        chosen, rects, over = _row_loop(
            ui, key, items, x + PAD, y + PAD - off, cw, a, at=at,
            row_id=row_id, keyboard=keyboard,
            window=(y + PAD, y + h - PAD) if scrolls else None)
        if chosen is not None:
            imgui.close_current_popup()
        if scrolls:
            dl.pop_clip_rect()
            view = h - 2 * PAD
            tw = 4.0
            th = max(view * view / ch, 16.0)
            ty = y + PAD + (view - th) * (off / max(ch - view, 1.0))
            D.fill(dl, x + w - tw - 2.0, ty, tw, th, ui.col("border", a), tw / 2)
        # The submenus AFTER the rows, so their panels are drawn over this
        # one and a click on a row of this panel has already had its say.
        if chosen is None:
            chosen = _submenus(ui, key, items, rects, over, a, row_id=row_id)
            if chosen is not None:
                imgui.close_current_popup()
        # AFTER the rows, so a click on one has already had its say: Enter
        # and Space on a highlighted row do what clicking it does.
        if keyboard and chosen is None and not frozen:
            chosen = _end_keys(ui, key, items)
        ui.dl = saved
        imgui.end_popup()
    else:
        LAST_RECT.pop(key, None)
        ui.anim.to(f"{key}:open", 0.0)
        # a closed panel holds no open submenu: without this, the next open
        # of the same menu comes up with the last submenu already showing -
        # and its children's rects outlive the children
        _forget(ui, key)
    imgui.pop_style_color()
    imgui.pop_style_var(4)
    return chosen
