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

import box as B
import draw as D
import tokens as T
from ease import mix

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
SEP_MY = 4.0         # my-1
DESTRUCTIVE_HOVER_A = {"light": 0.10, "dark": 0.20}
# `tracking-widest` is real and Chromium trails it: a 12px shortcut measures
# 2 x 1.2px wider than its glyphs. draw.text_w has no letter-spacing.
SHORTCUT_TRACKING = 1.2
ICON = 16.0          # size-4, measured; 14 was a guess


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


def _begin_keys(ui, key: str, items, x, y, w, role: str):
    """Resolve the open, let the pointer and the keys move the highlight,
    and hand back which row holds it. Runs BEFORE the rows are drawn.

    Returns a position in `item_rows(items)`, or None for "nothing
    highlighted" - which a pointer-opened menu really is.
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
    if rows and (io.mouse_delta.x or io.mouse_delta.y):
        iy = y
        for i, it in enumerate(items):
            if i in rows and imgui.is_mouse_hovering_rect(
                    imgui.ImVec2(x, iy), imgui.ImVec2(x + w, iy + ITEM_H)):
                st["sel"] = rows.index(i)
            iy += row_h(it)

    # second, so an arrow beats the pointer on a frame that carries both
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
    imgui.close_current_popup()
    return getattr(items[rows[hi]], "id", "")


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


def measure(ui, items, min_w: float = MIN_W) -> tuple[float, float]:
    """The content box a menu needs, before chrome padding."""
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
        if it.shortcut:
            # ONE gap, not two: measured at max-content a row is
            # `pad + label + gap + shortcut + pad`, which came to the panel
            # width to the 1/64 px. Reserving two made every menu with a
            # shortcut 6px wider than the browser's.
            extra += GAP + D.text_w(it.shortcut, ui.faces, "regular", 12,
                                    True) + SHORTCUT_TRACKING * len(it.shortcut)
        w = max(w, tw + extra)
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
            baseline_box=ITEM_H)
    if it.shortcut:
        D.label(ui.dl, x, y, it.shortcut, ui.faces, "regular", 12,
                sc_ink, align="right",
                box_w=w - ITEM_PAD_X, baseline_box=ITEM_H, tabular=True)
    return bool(st and st.clicked)


def popup(ui, key: str, items, *, min_w: float = MIN_W, anchor=None,
          side: str = "bottom", align: str = "end",
          offset: float = 4.0, role: str = "menu",
          keyboard: bool = True, row_id=None) -> str | None:
    """Draw the menu `key` if ImGui has it open. Returns the chosen item id.

    `row_id(item, index)` names each row's hit target, for a host whose
    tests find a row by its own id (Hyperspace's side pane: ``pane.fx``);
    by default a row is ``<key>.<index>``.

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
        if keyboard:
            at = highlighted_item(
                items, _begin_keys(ui, key, items, x + PAD, y + PAD, cw, role))

        iy = y + PAD
        for i, it in enumerate(items):
            rk = row_id(it, i) if row_id is not None else f"{key}.{i}"
            if _row(ui, it, x + PAD, iy, cw, rk, a,
                    hi=(i == at) if keyboard else None):
                chosen = it.id
                imgui.close_current_popup()
            iy += row_h(it)
        # AFTER the rows, so a click on one has already had its say: Enter
        # and Space on a highlighted row do what clicking it does.
        if keyboard and chosen is None:
            chosen = _end_keys(ui, key, items)
        ui.dl = saved
        imgui.end_popup()
    else:
        LAST_RECT.pop(key, None)
        ui.anim.to(f"{key}:open", 0.0)
    imgui.pop_style_color()
    imgui.pop_style_var(4)
    return chosen
