"""Combobox: Base UI's, where the trigger IS the input.

**shadcn ships `src/components/ui/combobox.tsx`** and it wraps
`@base-ui/react`'s Combobox: a `ComboboxInput` (an InputGroup around a
real `<input>`, with a ghost chevron in an inline-end addon) over a
portalled `ComboboxContent` holding a `ComboboxList`. You type into the
thing you clicked.

It is NOT the Popover-plus-Command recipe - a Button that opens a panel
with a separate search box inside it - and the first version of this
module was, because I told an agent that shadcn had no combobox
component. Everything below that still refers to `Popover`, `Command`,
`cmdk` or `CommandItem` is either the fuzzy ranking (which really is
cmdk's `commandScore`, kept because Base UI's default filter is a plain
substring match and the ranking is better) or a `_old_recipe_` entry kept
as a record of what was wrong. **Read `combobox.tsx` before trusting any
sentence here that names Command.** Two numbers - the group heading's
weight and the separator's margin - were still `command.tsx`'s as late as
the ergonomics pass, and nothing on the page exercised either.

Everything numeric below came out of Chromium, off the `combobox.*` probe
blocks in both themes, not out of a reading of the Tailwind classes.
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
  none` in both themes, open and closed, hovered and not — it is
  `:focus-visible`, and a pointer does not match it. Under a real keyboard
  focus the same trigger rings: `ring/50 0 0 0 3px`, with the border going
  to `ring` in light and *staying* `input` in dark, which is the outline
  Button's own dark anomaly measured again here. So `_trigger` takes a
  `focus_f` and the open state is the fill above, not a ring.
  `interact.select` used to drive its ring off `open_`, which paints one in
  exactly the state that has none; it does not any more.

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

from math import floor

from imgui_bundle import imgui

from . import box as B
from . import draw as D
from . import tokens as T

# re-exported for `C.x` callers (the gallery, the tests, comp_command)
from .combobox_items import Item, _is_row, _k, filter_items, heading, sep  # noqa: F401
from .combobox_measure import (
    _rows_node,
    combobox_size,  # noqa: F401
    list_content_h,
)
from .combobox_select import (
    _MISSING,
    CLEARED,
    SEL_FIRST,
    SEL_LAST,
    SEL_NONE,
    SENTINELS,
    resolve_open,
)

# The pure parts live in four modules of their own (HANDOFF item 3c). Every
# name below is either used by the widget here or re-exported for `C.x`
# callers - test_module_surface.py checks each one resolves.
from .combobox_tokens import COMBOBOX, COMBOBOX_DARK, combobox_table  # noqa: F401
from .ease import mix  # noqa: F401

# How much room the popup window keeps around its content for the field's
# focus ring.
#
# ZERO, deliberately, and the reason is worth keeping. The ring is a 3px
# band drawn OUTSIDE the field's box, and ImGui clips a window's draw list
# to the window - so with the window ending at the field's edge the ring is
# cut off square on whichever side it reaches. Inflating the window by 6 on
# every side fixed that here and produced visible artifacts around the top
# and bottom edges of the panel on a Retina Mac, which this machine (Mesa,
# density 1) does not reproduce. A cosmetic clip on a ring that only shows
# when the list is reached by Tab is the smaller of the two faults, so the
# inflation is off until the real fix lands.
#
# The real fix is not a bigger window: it is not putting the trigger inside
# the popup at all. The trigger is in there because ImGui hands a popup the
# keyboard the moment it appears, so an input left in the parent stops
# receiving characters - see the note in `combobox`. A list drawn as an
# ordinary window with `no_focus_on_appearing` would leave the caret where
# it is and need no inflation, at the cost of hand-rolling the dismissal
# and z-order that the popup stack gives for free.
RING_PAD = 0.0

# The margin a popover keeps off the viewport edge - floating-ui's own
# `padding`, and `box.place_popover`'s default.
VP_PAD = T.SPACE[2]

# Where each panel was last drawn, keyed by popup id — the same seam
# menu.LAST_RECT is, and for the same reason: ImGui places the popup, so a
# test cannot know the rect ahead of time, and reading it off pixels is
# unreliable.
LAST_RECT: dict = {}


# --------------------------------------------------------------------------
# the widget
# --------------------------------------------------------------------------
#
# PANEL CHROME. The two panels were measured identical (see the module
# docstring), and they are now the same code: `menu.panel_chrome`, which was
# pulled out of `menu.popup` precisely so that `popup`, the gallery cell and
# a Combobox could share one answer. This file held a copy of those four
# lines until then, with a note saying the fix needed menu.py edited.


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
    """The panel's shadow, fill and ring - which is `menu.panel_chrome`.

    This used to be a copy of those four lines, with a note saying the right
    fix was "a `menu.panel_chrome(ui, x, y, w, h, alpha)` that both call;
    adding it means editing menu.py, which this change may not do". That
    function exists now, and its own docstring names a Combobox as one of
    the three callers it was pulled out for - so the copy was the only thing
    left of the problem, and the panel's chrome was being diffed against the
    browser in the `menu` cell while this drew its own version.

    It is now the same code, so `menu.panel` and `contextmenu.panel` in the
    pixel diff cover this panel's chrome too. test_panel_chrome_is_menus
    holds the tokens to that, because the delegation is only sound while
    COMBOBOX's radius, bg and ring still say what menu.py draws.
    """
    from . import menu as M
    M.panel_chrome(ui, dl, x, y, w, h, a)




def field_chrome(ui, x, y, w, h, tbl, *, value: str = "",
                 placeholder: str = "", disabled: bool = False,
                 focus_f: float = 0.0, text: bool = True) -> None:
    """The trigger's chrome: the box, the ring, the placeholder, the chevron.

    Pulled out of `_input_trigger`'s `if chrome:` tail for the same reason
    `menu.rows` grew `chrome_only` - the gallery draws into the background
    draw list, where submitting the real `imgui.input_text` that function is
    built around would make ImGui auto-create its "Debug" window over the
    canvas.

    `text=False` is the chrome pass: it drops the placeholder's glyphs and
    keeps the chevron, which is a vector the diff measures as a silhouette
    rather than as ink.

    The box is measured identical to `tokens.INPUT`, ring included - Base
    UI's ComboboxInput is an InputGroup wrapping a real <input>, and the
    group's band and border measure as the Input's - at `rounded-lg`.
    """
    dim = 0.5 if disabled else 1.0
    it = T.input_table(ui.theme_name)
    D.field(ui.dl, x, y, w, h, ui.theme, it, focus_f=focus_f,
            disabled=disabled, radius=T.RADII["lg"])
    # The placeholder shows whenever the VALUE is empty, focused or not.
    # Measured in Chromium on the real component: the placeholder ink is
    # there at rest, under a keyboard focus, and with the list open -
    # `::placeholder` keys off the value, not the focus. The kit hid it on
    # focus, so clicking an empty combobox blanked the field.
    if text and not value:
        D.label(ui.dl, x + tbl["input_pad_l"], y, placeholder, ui.faces,
                "regular", tbl["field_font"],
                ui.col(it["placeholder"][0], it["placeholder"][1] * dim),
                baseline_box=h)
    g = tbl["field_icon"]
    # `has-disabled:opacity-50` is on the input GROUP, so it dims the
    # chevron and the placeholder along with the box - measured, the group
    # computes `opacity: 0.5` and the svg's own stays 1. Only the box was
    # dimmed. Folding the group's opacity into each colour is right here
    # because the border and the chevron do not overlap; comp_button has to
    # keep them apart because bg-clip-padding makes its fill and border
    # disjoint.
    ink = tbl["field_icon_ink"]
    # `dim` is the GROUP's opacity; the chevron's own button multiplies a
    # second one on top of it when disabled. See the two tokens.
    ia = ink[1] * dim * (tbl["field_icon_disabled_opacity"]
                         if disabled else 1.0)
    D.icon(ui.dl, "chevron-down",
           x + w - tbl["field_chevron_right"] - g, y + (h - g) / 2.0, g,
           ui.col(ink[0], ia))


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
               _col(ui, tbl["item_sel_bg"]), T.RADII[tbl["row_radius"]])
    ink = _col(ui, tbl["item_sel_ink"] if selected else tbl["item_ink"], dim)

    tx = r.x + tbl["row_pad_x"]
    cs = tbl["check"]
    if _k(it, "icon", ""):
        g = tbl["field_icon"]
        D.icon(ui.dl, _k(it, "icon", ""), tx, r.y + (r.h - g) / 2.0, g, ink)
        tx += g + tbl["row_gap"]
    # `pr-8` is the label's limit whether or not this row is checked: the
    # indicator is absolutely positioned, so it takes the row out of flow
    # and the padding is what reserves its space.
    D.label(ui.dl, tx, r.y, _k(it, "label", ""), ui.faces, "regular",
            tbl["item_font"], ink, baseline_box=r.h,
            max_w=r.x + r.w - tbl["row_pad_r"] - tx)
    if checked:
        # `absolute right-2` on a `size-4` span: the check's RIGHT edge is
        # 8 from the row's, not its left edge 8 in from the padding.
        D.icon(ui.dl, "check", r.x + r.w - tbl["check_gap"] - cs,
               r.y + (r.h - cs) / 2.0, cs, _col(ui, tbl["check_ink"], dim))
    return bool(st and st.clicked)


def _state(ui, key) -> dict:
    """Per-combobox state that has to outlive the frame.

    It lives on `ui.anim.store` because a `Ui` is rebuilt every frame and
    anything kept on one is thrown away before it can be read back — the
    trap the tooltip's hover clock already fell into.
    """
    return ui.anim.store.setdefault("combobox", {}).setdefault(
        key, {"q": "", "sel": None, "focus": True, "typed": False,
              "was_focused": False, "side": ""})


# Where each field's caret was last seen, keyed the same way `_state` is.
# It cannot live in `_state` because it is read back on the frame the popup
# OPENS, before `_state` has been touched for that frame, and because the
# two halves of the split field write it from two different call sites.
_CARET: dict = {}


def _read_caret(item_id) -> int | None:
    """The cursor offset inside an `input_text`, or None.

    `imgui.internal.get_input_text_state` is private API and the only way
    to ask. It is wrapped rather than trusted: if a binding stops exposing
    it the field keeps working and only the caret handover is lost, which
    is the behaviour the kit had before this.
    """
    try:
        st = imgui.internal.get_input_text_state(item_id)
        if st is None or st.id_ != item_id:
            return None
        return int(st.get_cursor_pos())
    except Exception:   # noqa: BLE001 - a binding without the internal state: no caret
        return None


def _place_caret(item_id, pos: int) -> bool:
    """Put the cursor at `pos` with nothing selected.

    This is what undoes ImGui's select-all. `set_keyboard_focus_here()`
    activates an InputText the way a Tab does, and ImGui selects the whole
    value on that path - so the popup's copy of the field came up with the
    value highlighted and the caret at the end, and the click's caret was
    thrown away. Measured in Chromium: clicking a combobox that holds
    `Gamma` at +18px leaves `selectionStart == selectionEnd == 1`. There is
    no select-all anywhere in the real component.
    """
    try:
        st = imgui.internal.get_input_text_state(item_id)
        if st is None or st.id_ != item_id:
            return False
        at = max(0, min(int(pos), int(st.text_len)))
        st.set_selection(at, at)
        return True
    except Exception:   # noqa: BLE001 - a binding without the internal state: no caret
        return False


def _caret_pending(st: dict, slot: str, applied: bool | None) -> None:
    """Hold a wanted caret until `_place_caret` takes it, then let go.

    The retry is not belt-and-braces: measured, on the frame
    `set_keyboard_focus_here()` is called `get_input_text_state` still
    reports nothing for that id, so a single attempt ALWAYS fails and the
    select-all stands. The budget is there so that a binding which stops
    exposing the state degrades to the old behaviour instead of pinning the
    caret on every frame for ever.
    """
    if st.get(slot) is None:
        return
    k = slot + "_try"
    st[k] = st.get(k, 0) + 1
    if applied or st[k] > 4:
        st.pop(slot, None)
        st.pop(k, None)


def _input_trigger(ui, key, tbl, x, y, w, h, text, placeholder, *,
                   disabled=False, open_=False, grab_focus=False,
                   chrome=True, ink=True, focus_hint=False, caret=None):
    """The trigger, which IS an input. Returns (changed, text, focused,
    clicked).

    `chrome` / `ink` split the field in two, and that split is what keeps
    the focus ring off ImGui's clip edge. See THE SPLIT FIELD in
    `combobox`: the copy drawn in the PARENT window owns the chrome (the
    box, the ring, the placeholder, the chevron) and the copy drawn inside
    the POPUP owns the widget (the caret, the selection, the keyboard and
    the clipboard). Exactly one of them paints the glyphs, or the two
    passes stack and the value comes out bolder than the theme's
    foreground - measured at 255 against a `foreground` of 250.

    `focus_hint` rings the field although THIS copy's `input_text` is not
    the active one, which is the parent's case while the list is open: the
    keyboard is in the popup, and the browser rings a focused input group
    whether or not its list is up.

    `caret` is a character offset to put the cursor at instead of letting
    `set_keyboard_focus_here` select the whole value.

    This is the whole shape of the real component: Base UI's
    `ComboboxInput` is an InputGroup wrapping a real <input>, with a ghost
    chevron in an inline-end addon. You type into the thing you clicked.
    The kit first shipped a Button that opened a panel with a separate
    search box inside it - the old Popover+Command recipe - and that is what
    this replaces.

    The sandwich is `interact.text_input`'s: a real `imgui.input_text` for
    the caret, the selection, the keyboard and the clipboard, with its own
    frame pushed transparent and dkit's drawn underneath.
    """
    from . import interact as I
    cz = tbl["field_icon"] + 2 * T.SPACE[1]        # the chevron's addon
    pl = tbl["input_pad_l"]

    cols = I._sandwich_begin(ui, clear_grab=False)
    # imgui's own Col_.text is WHITE by default, which is invisible on the
    # light theme - the same trap interact.text_input records.
    #
    # `ink=False` pushes it TRANSPARENT instead, which is how the parent's
    # copy stops painting a second set of glyphs over the popup's. The
    # selection band goes with it: an inactive InputText draws no band, but
    # saying so costs one call and does not depend on that staying true.
    imgui.push_style_color(
        imgui.Col_.text,
        imgui.ImVec4(*ui.col("foreground")) if ink
        else imgui.ImVec4(0, 0, 0, 0))
    if not ink:
        imgui.push_style_color(imgui.Col_.text_selected_bg,
                               imgui.ImVec4(0, 0, 0, 0))
    # ImGui draws a blue nav-cursor rectangle around a keyboard-focused
    # item. No shadcn component has one, and it is very visible on the
    # field the moment the list opens - which is exactly when the kit asks
    # for that focus.
    imgui.push_style_color(imgui.Col_.nav_cursor, imgui.ImVec4(0, 0, 0, 0))
    # The SAME font `draw.label` draws every other string in the kit with.
    # Without it the stock widget renders the value in imgui's CURRENT font
    # at imgui's current size, which is not the Geist face at
    # `font * FONT_SPAN_EM` - so the value and the placeholder, one line of
    # one field, had different metrics and did not land on the same rows.
    # Measured 1 px apart on Mesa at density 1; far wider on a Retina Mac,
    # where the atlas is rasterised at 2x, which is where it was spotted.
    D.push_css_font(ui.faces, "regular", tbl["field_font"])
    fs = imgui.get_font_size()
    # `FramePadding` IS the field's padding, and that is the point.
    #
    # It used to be zeroed, so that the cursor was the text's top-left. The
    # cost was that an InputText's HIT AREA is its frame, and the frame was
    # then the text box alone: the field's leading 10 px and everything
    # right of the text box were dead. Measured on the dashboard's Find
    # combobox (w 150): a press at x+2 or x+120 neither focused the field
    # nor opened the list, where the browser treats the whole padded box as
    # the input - `cursor: text` on the group, and clicking the left pad
    # puts the caret at offset 0.
    #
    # So the frame is the input's own box, x .. x + w - <the addon>, and
    # the padding puts the glyphs back at `input_pad_l` and centres them:
    # the frame comes out `fs + 2 * (h - fs)/2` = h, and the text's
    # top-left is unchanged from the zeroed version.
    #
    # ImGui's FramePadding.x is symmetric, so the text's RIGHT inset is 10
    # where the browser's is 6 (`pr-1.5` from the inline-end addon). That
    # clips a very long value four pixels earlier than Chromium would; it
    # is the deliberate half of the trade.
    #
    # The glyphs then sit on imgui's line, whose baseline is its face's
    # ascent below the padding - not Blink's, which `draw.label` (the
    # placeholder) uses. The frame is moved by the difference, which is
    # zero at the field's 14px in an even box and at most a pixel anywhere.
    pad_y = max(0.0, (h - fs) / 2.0)
    imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(pl, pad_y))
    imgui.set_cursor_screen_pos(
        imgui.ImVec2(x, D.stock_text_y(y, tbl["field_font"], h, ui.faces) - pad_y))
    imgui.push_item_width(w - cz)
    if grab_focus:
        # The popup window has the keyboard the moment it appears, but
        # nothing in it is ACTIVE - so characters went nowhere and the list
        # never filtered. This hands the caret to the field on the frame it
        # opens, and only then, or it would fight the user every frame.
        imgui.set_keyboard_focus_here()
    if disabled:
        imgui.begin_disabled()
    changed, out = imgui.input_text(f"##{key}.q", text)
    if disabled:
        imgui.end_disabled()
    wid = imgui.get_item_id()
    # NOT gated on `grab_focus`. Measured: on the frame
    # `set_keyboard_focus_here()` is called, `get_input_text_state` still
    # reports no state for this id - ImGui activates the widget but has not
    # adopted it as the one being edited until the frame after - so a
    # single attempt on the open frame always failed and the select-all
    # stood. The caller retries with a budget; `caret_set` says when to
    # stop.
    caret_set = False if caret is not None else None
    if caret is not None:
        caret_set = _place_caret(wid, caret)
    imgui.pop_item_width()
    imgui.pop_font()
    imgui.pop_style_var()
    # `interact.text_input`'s rule, and measured on this control too: the
    # trigger is an InputGroup that rings on
    # `has-[[data-slot=input-group-control]:focus-visible]`, and its control
    # is a text field - so a POINTER click into it rings as well (measured
    # `:focus-visible` true, band `ring/50 0 0 0 3px`, border -> `ring`, in
    # both themes). That is why this one is not gated on `ui.focus_visible`.
    focused = (imgui.is_item_active()
               or (imgui.is_item_focused() and ui.focus_visible))
    # Measured: clicking the input OPENS the list, with nothing highlighted.
    # Focus alone does not - Tab into it and it stays closed - so the open
    # has to hang off the click rather than off the focus, which is what the
    # kit had and why tabbing to it opened the list.
    clicked = imgui.is_item_clicked()
    if ink:
        _CARET[key] = _read_caret(wid)
    imgui.pop_style_color(3 if not ink else 2)
    I._sandwich_end(ui, cols)

    # the Input's own chrome: measured identical to tokens.INPUT, ring
    # included - the InputGroup's band and border measure as the Input's
    if chrome:
        focus_f = ui.anim.to(f"{key}:focus",
                             1.0 if (focused or focus_hint) else 0.0)
        field_chrome(ui, x, y, w, h, tbl, value=out,
                     placeholder=placeholder, disabled=disabled,
                     focus_f=focus_f)
    # MERGE. `_sandwich_end` only restores the channel; leaving the split
    # open makes the next one nest, which ImGui asserts on rather than
    # tolerates ("Nested channel splitting is not supported").
    ui.dl.channels_merge()
    return changed, out, focused, clicked, caret_set


# The KEYBOARD, measured on the real Base UI component rather than
# reasoned about. `?probe` carries `combobox.kb`, which is the only block on
# that route WITHOUT `open` - every other one reports `aria-expanded: true`
# whatever you press, which is how the first pass at this got it wrong.
#
#   closed  focus (a Tab into it)   stays CLOSED
#   closed  click the input         opens; VALUE's row, else none
#   closed  click the chevron       opens; VALUE's row, else none
#   closed  ArrowDown               opens; VALUE's row, else the first
#   closed  ArrowUp                 opens; VALUE's row, else the LAST
#   closed  typing                  opens, filters, highlight NONE
#   open    typing                  filters, highlight back to NONE
#   open    ArrowDown               none -> first, i -> i+1, last -> NONE
#   open    ArrowUp                 none -> last,  i -> i-1, first -> NONE
#   open    arrows                  SCROLL the list to follow the highlight
#   open    the wheel               scrolls; the highlight does not move
#   open    the pointer, MOVING     takes the highlight; parked, it does not
#   open    Home/End/PageUp/PageDn  move the CARET; the highlight is untouched
#   open    Enter, highlight set    selects it, closes, focus STAYS, caret
#                                   at the end of the new value
#   open    Enter, no highlight     closes, value reverts, focus STAYS
#   open    Escape                  closes, value reverts, focus and caret STAY
#   open    Tab                     closes, value reverts, focus MOVES ON
#   open    click the field again   stays open, caret where clicked
#   open    click the chevron       CLOSES it
#   open    click away              closes, value reverts
#   closed  Escape                  CLEARS the value   <- NOT implemented, see
#                                   the note at the end of this comment
#
# Three things in there are easy to get wrong and were.
#
# The highlight has a real NONE state - it does not wrap, it falls off
# either end into nothing and comes back round on the next press.
#
# Tab is not the list's key. The kit trapped it inside the popup, so a
# keyboard user could get into the combobox and not out of it.
#
# And the VALUE beats the gesture. The first pass at this model was driven
# on `?probe`'s `combobox.kb`, which carries no `defaultValue` - so every
# open there falls through to the none / first / last case and that is the
# only case it recorded. Re-driven on `combobox.many` (sixteen rows,
# `defaultValue="Gamma"` at index 2) all four gestures open on Gamma, which
# is also the row that carries the check. `resolve_open` is that table.
#
# A second Escape on a CLOSED combobox CLEARS the committed value -
# measured: one Escape reverts the query and closes, the next sets
# `input.value` to "". The kit could not express it, because `combobox()`
# signals a choice by returning its id and a cleared value is a falsy id,
# which every caller reads as "nothing happened". `CLEARED` is that third
# answer: a sentinel distinct from both None and "", so
# `if got is not None` separates the three cases.
KEY_MODEL = """closed: focus keeps it closed; click/chevron/type/arrow open
it, on the committed value's row if there is one. open: arrows move one
highlight with a NONE state at both ends and scroll the list to follow it,
Enter takes the highlight, Escape closes and keeps focus, Tab closes and
moves on."""


def combobox(ui, key, x, y, w, label, items, *, size="default",
             disabled=False, placeholder="Select an option",
             search="Search...", empty="No results found.") -> tuple:
    """shadcn's Combobox recipe: the trigger here, the panel on ImGui's
    popup stack. Returns `(chosen_id_or_None, open)`.

    The keyboard model is `KEY_MODEL` above, measured key by key.

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
    from . import interact as I

    tbl = combobox_table(ui.theme_name)
    hh, _rkey = T.SELECT_SIZES[size]
    pid = f"##cb.{key}"

    s = _state(ui, key)
    # The input shows the chosen label until you type over it, which is
    # what Base UI does: the query and the value live in one field.
    if not s.get("typed"):
        s["q"] = label or ""

    # Escape closes the list and KEEPS the focus on the field - measured,
    # and the next arrow reopens it. The field drawn here is a different
    # imgui id from the one drawn inside the popup, so the focus does not
    # come back on its own: the close asks for it and this hands it over on
    # the one frame after.
    regrab = bool(s.pop("refocus", False))
    # THE SPLIT FIELD.
    #
    # The field is drawn twice - once here in the parent window and once
    # inside the popup - and which half does what is the fix for the
    # clipped focus ring.
    #
    # Why there are two at all: ImGui hands a popup the keyboard the
    # instant it appears, so an `input_text` left behind in the parent
    # stops receiving characters exactly when the list opens. The copy
    # inside the popup is the one that can hold the caret.
    #
    # What went wrong: that copy used to draw the field's CHROME as well,
    # and ImGui clips a window's draw list to the window. The popup starts
    # at the field's top-left and is exactly `w` wide, so the 3px ring
    # drawn OUTSIDE the field's box was cut off on three sides. Measured
    # on the dashboard's Find combobox, dark, pointer parked off the
    # control: with the list CLOSED the band reads 46 at d=1,2,3 on all
    # four sides; with it OPEN it reads 0 left, 0 right, 0 top and 46 only
    # at the bottom, where the window carries on down toward the panel.
    # Tab and click differ in nothing but whether the list opens, which is
    # what localises the fault to this one window.
    #
    # So: this copy owns the CHROME - the box, the ring, the placeholder
    # and the chevron - and it is in the parent window, where nothing
    # clips it. The popup's copy owns the WIDGET: the caret, the
    # selection, the keyboard and the clipboard. `ink` hands the glyphs to
    # whichever of them has the caret, because both were painting them and
    # the value came out at 255 against a `foreground` of 250.
    open_now = imgui.is_popup_open(pid)
    changed, q, focused, clicked, _cs = _input_trigger(
        ui, key, tbl, x, y, w, hh, s["q"], placeholder,
        disabled=disabled, open_=open_now,
        grab_focus=regrab, chrome=True, ink=not open_now,
        focus_hint=open_now, caret=s.get("caret0"))
    _caret_pending(s, "caret0", _cs)
    focused = focused or regrab

    def _open(sel):
        # `armed` says the popup opened on THIS frame. The arrow that opened
        # it must not also be processed by the list, or the first ArrowDown
        # lands on the second row: the closed-field branch sets the
        # highlight to the first item and the popup's own handler, running
        # later in the same frame, moves it on by one. Measured as an
        # off-by-one at both ends.
        s["sel"], s["focus"], s["armed"] = sel, True, True
        # Hand the parent copy's caret over to the popup's, so a click into
        # the middle of the value leaves the cursor where it was clicked
        # rather than selecting the whole value. Measured in Chromium:
        # clicking `Gamma` at +18px gives selectionStart == selectionEnd ==
        # 1, at +3px gives 0, past the text gives 5. Never a selection.
        s["caret"] = _CARET.get(key)
        imgui.open_popup(pid)

    if not disabled:
        was_open = imgui.is_popup_open(pid)
        if changed:
            # typing opens it and clears the highlight - measured, and it is
            # why `sel` starts at None rather than 0: after a filter nothing
            # is highlighted until an arrow is pressed
            s["q"], s["sel"], s["typed"] = q, None, True
            if not was_open:
                _open(None)
        elif clicked and not was_open:
            _open(SEL_NONE)
        elif focused and not was_open:
            # an arrow OPENS it, and which arrow decides where the highlight
            # lands. `FIRST`/`LAST` are resolved once `rows` is known.
            if imgui.is_key_pressed(imgui.Key.down_arrow, False):
                _open(SEL_FIRST)
            elif imgui.is_key_pressed(imgui.Key.up_arrow, False):
                _open(SEL_LAST)
    # kept before it is overwritten: ImGui DEACTIVATES an input_text when
    # Escape is pressed - that is its "cancel the edit" - so on the very
    # frame the key arrives the field reports itself unfocused. Anything
    # that asks "was this field focused when Escape came" has to ask about
    # the frame before.
    had_focus = bool(s.get("was_focused"))
    s["was_focused"] = focused
    # the chevron's own target, so clicking it toggles without stealing the
    # caret from the field
    cz = tbl["field_icon"] + 2 * T.SPACE[1]
    if ui.hit(f"{key}.chev", x + w - cz, y, cz, hh).clicked and not disabled:
        if imgui.is_popup_open(pid):
            imgui.close_current_popup()
        else:
            # measured: the chevron opens on the committed row exactly as a
            # click on the field does
            s["typed"] = False
            _open(SEL_NONE)
    open_ = imgui.is_popup_open(pid)

    if not open_:
        LAST_RECT.pop(pid, None)
        ui.anim.to(f"{pid}:open", 0.0)
        s["typed"] = False               # the field goes back to the value
        s["side"] = ""                   # decided afresh on the next open
        # The SECOND Escape, the one pressed while it is already closed,
        # empties the field. Measured.
        #
        # No flag is needed to tell the two apart, and the flag I reached
        # for first was the bug: the Escape that CLOSES the list is seen by
        # the open branch, because `open_` was still true on that frame, so
        # this branch cannot run until the frame after - by which time the
        # key is no longer pressed. Any Escape that gets here is therefore
        # already the second one.
        if ((focused or had_focus) and not disabled and label
                and imgui.is_key_pressed(imgui.Key.escape, False)):
            s["q"] = ""
            return CLEARED, False
        return None, False

    # filtered on what is IN the field, unless it still holds the value
    shown = filter_items(items, s["q"] if s.get("typed") else "")
    rows = [i for i, it in enumerate(shown)
            if _is_row(it) and _k(it, "enabled", True)]
    # resolve the token an open leaves behind, and drop a highlight the
    # filter has taken away. The committed value beats all three tokens -
    # see `_committed_row`.
    if s["sel"] in SENTINELS:
        s["sel"] = resolve_open(s["sel"], shown, rows, label)
        # an open scrolls the list to whatever it highlighted: measured,
        # reopening with the LAST row committed comes up at scrollTop 204
        # of a 204 range, not at the top
        s["scroll_to"] = s["sel"]
    elif s["sel"] is not None and s["sel"] >= len(rows):
        s["sel"] = None

    pad = tbl["pad"]
    ch = list_content_h(shown, tbl)

    # --- which side, and how tall ------------------------------------------
    # Measured on the real component, 16 items pinned 90px from the bottom of
    # a 900px viewport: it opens on `side="top"`, its list clamps to
    # `max-height: 252px` and SCROLLS, and when a filter cuts it to one row
    # the panel keeps side=top - the near edge stays 6px off the field and
    # only the far edge moves. It does not hop to the other side.
    #
    # The kit re-ran the placement every frame against the current content
    # height, so the first keystroke shrank the panel, the shrunken panel
    # suddenly fitted below, and it jumped from above the field to below it
    # mid-word. The side is decided ONCE, when the popup opens, and kept -
    # which is also what `--available-height` is for: a panel that clamps
    # never needs to flip.
    vp = ui.viewport
    room_below = vp.bottom - VP_PAD - (y + hh + tbl["side_offset"])
    room_above = (y - tbl["side_offset"]) - (vp.y + VP_PAD)
    if not s.get("side"):
        s["side"] = ("bottom" if room_below >= min(ch + 2 * pad,
                                                   tbl["list_max_h"])
                     or room_below >= room_above else "top")
        # `--available-height` only ever shrinks the clamp, so a panel that
        # clamps never needs to flip - measured, filtering 16 rows down to
        # one keeps `data-side="top"` and moves only the far edge.
    room = room_below if s["side"] == "bottom" else room_above
    # `data-empty:p-0`: with nothing to show the list collapses and the
    # panel is exactly the empty block. Measured at 319x36.
    if not rows:
        pad = 0.0
    # no search row: the panel is the list and its padding, because the
    # search field IS the trigger
    lh = max(tbl["row_h"],
             min(ch, tbl["list_max_h"] - 2 * pad, room - 2 * pad))
    ph = pad + lh + pad

    # The popup spans the TRIGGER as well as the panel. ImGui gives a popup
    # window the keyboard focus, so an input left behind in the parent stops
    # receiving characters the moment the list opens - you could click the
    # field, see the list, and type into nothing. Covering the trigger puts
    # the field inside the focused window, which is where the caret has to
    # be. Base UI has the same field doing both jobs; this is how that works
    # on ImGui's popup stack.
    at, _side = B.place_popover(B.Rect(x, y, w, hh), w, ph, ui.viewport,
                                side=s["side"], align=tbl["align"],
                                offset=tbl["side_offset"], pad=VP_PAD)
    # The window is inflated by RING_PAD on every side, and everything in
    # it is drawn RING_PAD in from its corner.
    #
    # ImGui clips a window's draw list to the window, and the field's focus
    # ring is a 3px band drawn OUTSIDE the field's box - so a window that
    # ended at the field's edge cut the ring off square, and took the right
    # ends of the rows with it. It only showed when the list was reached
    # with Tab, because that is the one way in that rings the field while
    # the list is open.
    win_y = min(at.y, y) - RING_PAD
    win_h = (at.y + ph) - win_y + RING_PAD
    # Radix rounds its own transform, so the panel's origin is integral and
    # the gap off a fractional trigger runs 3.625 … 4.5 rather than a
    # constant 4. Measured; see the module docstring.
    imgui.set_next_window_pos(
        imgui.ImVec2(round_px(at.x) - RING_PAD, round_px(win_y)))
    imgui.set_next_window_size(imgui.ImVec2(w + 2 * RING_PAD, win_h))
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
    imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
    # A POPUP's border is `PopupBorderSize`, which is 1.0 by default and
    # which `WindowBorderSize` does not touch. That 1px ran down both sides
    # of this window - and this window is deliberately taller than its panel,
    # because it spans the trigger as well, so the border showed as two
    # vertical lines bridging the 6px gap between the field and the list.
    # Measured at 75 against a 23 ground, the full height of the gap, at
    # exactly x+0 and x+w-1.
    #
    # Every other popup in the kit hides this by accident: their window IS
    # their panel, so the border sits under chrome that covers it. This one
    # does not, which is why it is the one that showed.
    imgui.push_style_var(imgui.StyleVar_.popup_border_size, 0.0)
    imgui.push_style_var(imgui.StyleVar_.popup_rounding,
                         T.RADII[tbl["radius"]])
    imgui.push_style_color(imgui.Col_.popup_bg, imgui.ImVec4(0, 0, 0, 0))

    chosen = None
    picked = None            # the committed row's label, for the caret
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
            pid,
            imgui.WindowFlags_.no_scrollbar
            | imgui.WindowFlags_.no_scroll_with_mouse):
        # shadcn fades the panel in over 100ms (`animation: enter 0.1s`).
        # ImGui places the window, so only the chrome is animated.
        a = ui.anim.to(f"{pid}:open", 1.0)
        dl = imgui.get_window_draw_list()
        p = imgui.get_window_pos()
        px = p.x + RING_PAD
        py = p.y + (at.y - win_y)            # the panel, below the trigger
        LAST_RECT[pid] = (px, py, w, ph)
        saved, ui.dl = ui.dl, dl
        # The widget half: the caret, the selection, the keyboard and the
        # clipboard, and NO chrome - see THE SPLIT FIELD above. Placed at
        # the field's own (x, y) rather than at the popup-relative one, so
        # the glyphs and the caret land exactly where the parent drew the
        # box even when the trigger's x is fractional.
        changed2, q2, _f2, _c2, caret_set = _input_trigger(
            ui, f"{key}.open", tbl, x, y, w, hh, s["q"],
            placeholder, disabled=disabled, open_=True,
            grab_focus=s.get("focus", False), chrome=False, ink=True,
            caret=s.get("caret"))
        s["focus"] = False
        _caret_pending(s, "caret", caret_set)
        if changed2:
            # typing clears the highlight, here as well as on the closed
            # field - measured, and the two paths have to agree or the
            # highlight survives a filter on one of them
            s["q"], s["sel"], s["typed"] = q2, None, True
        _panel_chrome(ui, dl, px, py, w, ph, a, tbl)

        # One highlight, moved by EITHER the pointer or the keyboard. It
        # does NOT wrap: measured, going past the last item clears it and
        # the next press comes back round at the other end, so there is a
        # real "nothing highlighted" state between the two ends.
        n = len(rows)
        if s.pop("armed", False):
            n = 0                       # this frame's arrow opened the list
        if n:
            moved = False
            if imgui.is_key_pressed(imgui.Key.down_arrow, True):
                cur = s["sel"]
                s["sel"] = 0 if cur is None else (
                    None if cur + 1 >= n else cur + 1)
                moved = True
            if imgui.is_key_pressed(imgui.Key.up_arrow, True):
                cur = s["sel"]
                s["sel"] = n - 1 if cur is None else (
                    None if cur - 1 < 0 else cur - 1)
                moved = True
            if moved:
                # the KEYBOARD scrolls the list to follow itself; the
                # pointer and the wheel do not - see SCROLL TO THE
                # HIGHLIGHT below
                s["scroll_to"] = s["sel"]

        # The scroll child spans the WHOLE panel and the rows are inset
        # inside it, rather than the child BEING the rows' box.
        #
        # ImGui clips a child window to its own rect, and a rounded rect
        # whose edge lands exactly on that boundary loses the outer column
        # of its corner arc - so a row that filled the child read as square
        # on whichever side the clip touched. Giving the child the panel's
        # full width puts the clip `pad` away from every row edge, where it
        # cannot touch an arc, and the rows keep the geometry the browser
        # measures: inset 4 from the panel, both sides, `rounded-md`.
        lx, ly, lw = px, py + pad, w
        # `no-scrollbar` on the real list, measured as a zero-width
        # scrollbar in every state - including one scrolled 204px. It
        # scrolls and shows nothing.
        with I.scroll_area(ui, f"{key}.list", lx, ly, lw, lh, ch,
                           bars=False) as view:
            node = _rows_node(shown, lambda *a: 0.0, tbl, empty=empty)
            place = B.lay(node, B.Rect(view.x + pad, view.y,
                                       view.w - 2 * pad, ch))

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

            # SCROLL TO THE HIGHLIGHT.
            #
            # The real list follows its keyboard highlight: measured on
            # `combobox.many`, sixteen rows in a 252px clamp, the arrows
            # take `scrollTop` 0 -> 92 (row 11) -> 204 (row 15) and back to
            # 0 when the highlight wraps round to the first row. The kit
            # did not scroll at all, so arrowing past the ninth row moved a
            # highlight nobody could see.
            #
            # Minimum movement, which is `scrollIntoView({block:
            # "nearest"})`. The browser's list carries `scroll-py-1`, four
            # pixels of scroll padding at each end - and it needs it
            # because its own `p-1` is INSIDE the scrollable box. The
            # kit's 4px rails are outside the scroll viewport, so the two
            # cancel and the numbers come out identical with no padding
            # here: row 11 wants 12*28 - 244 = 92, row 15 wants
            # 16*28 - 244 = 204. Both are the measured values.
            #
            # Only the KEYBOARD scrolls. Measured, a wheel scroll moves the
            # list and leaves the highlight where it was, and a highlight
            # taken by the pointer is on a row that is visible by
            # definition - so scrolling on either of those would fight the
            # user.
            at = s.pop("scroll_to", _MISSING)
            # bounded as well as popped: a request that outlives the frame
            # that made it - an empty panel draws no scroll area, so the
            # pop does not run - would index a `rows` that has since
            # shrunk under a filter
            if (at is not _MISSING and at is not None
                    and rows and 0 <= at < len(rows)):
                r = place[("row", rows[at])]
                sy = imgui.get_scroll_y()
                top = r.y - ly + sy
                bot = top + r.h
                want = sy
                if top < sy:
                    want = top
                elif bot > sy + lh:
                    want = bot - lh
                want = max(0.0, min(want, max(0.0, ch - lh)))
                if abs(want - sy) > 0.5:
                    imgui.set_scroll_y(want)

            for i, it in enumerate(shown):
                kind = _k(it, "kind", "item")
                if kind == "sep":
                    r = place[("sep", i)]
                    # `-mx-1`: it reaches out past the list, over the
                    # panel's own padding. `my-1` puts the rule 4 down
                    # inside its own 9px block.
                    D.fill(ui.dl, r.x - pad, r.y + tbl["sep_my"],
                           r.w + 2 * pad, tbl["sep_h"],
                           _col(ui, tbl["sep_col"]))
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
                        selected=(s["sel"] is not None and bool(rows)
                                  and rows[s["sel"]] == i),
                        checked=bool(chk)):
                    chosen = _k(it, "id", "")
            if not rows and ("empty", 0) in place:
                r = place[("empty", 0)]
                D.label(ui.dl, r.x, r.y, empty, ui.faces, "regular",
                        tbl["empty_font"], _col(ui, tbl["empty_ink"]),
                        align="center", box_w=r.w, baseline_box=r.h)

        if (imgui.is_key_pressed(imgui.Key.enter, False)
                or imgui.is_key_pressed(imgui.Key.keypad_enter, False)):
            # with a highlight it takes it; with none it just closes, and
            # the query reverts to the committed value on the way out
            if rows and s["sel"] is not None:
                chosen = _k(shown[rows[s["sel"]]], "id", "")
                picked = _k(shown[rows[s["sel"]]], "label", "")
            else:
                # with no highlight it just closes, and the field keeps the
                # focus - measured, `document.activeElement` is still the
                # input after Enter either way
                s["refocus"] = True
                s["caret0"] = _CARET.get(f"{key}.open")
                imgui.close_current_popup()
        # Tab is NOT the list's key. Measured: it closes the list and moves
        # focus on. The kit swallowed it inside the popup, so a keyboard
        # user could get into the combobox and not back out of it.
        if imgui.is_key_pressed(imgui.Key.tab, False):
            imgui.close_current_popup()
        if chosen is not None:
            # MEASURED: committing - by Enter or by clicking a row - leaves
            # the field focused with the caret at the END of the new value
            # and nothing selected. `Enter` on a 'et' query gives value
            # `Beta` and selectionStart == selectionEnd == 4, with
            # `document.activeElement` still the input. The kit dropped the
            # focus on the floor, so the ring went out and the next arrow
            # did nothing.
            s["refocus"] = True
            if picked is None:
                picked = next((_k(it, "label", "") for it in shown
                               if _k(it, "id", "") == chosen), "")
            s["caret0"] = len(picked or "")
            imgui.close_current_popup()
        elif imgui.is_key_pressed(imgui.Key.escape, False):
            # focus stays on the field, so the next arrow reopens the
            # list - and the caret stays where it was, measured: a click at
            # +40px then Escape leaves selectionStart == 3, not 0 and not
            # the end
            s["refocus"] = True
            s["caret0"] = _CARET.get(f"{key}.open")
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
    imgui.pop_style_var(4)
    return chosen, open_
