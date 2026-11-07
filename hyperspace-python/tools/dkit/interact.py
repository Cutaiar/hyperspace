"""The sandwich: stock ImGui widgets for behaviour, dkit chrome for looks.

This is `Panel._track` (hyperspace/ui.py:1311-1357) generalized. That function
is the one place in 20,800 lines of UI code that already does the right thing
— run the real widget, push its own colours to transparent, and paint custom
chrome on a lower draw channel — and the whole kit hangs off making it the
normal way to build a widget rather than a one-off.

Three rules it has to keep:

* **Every interactive primitive carries an `invisible_button` with its
  `##id`.** `tests/ui_driver.py:43-46` finds controls by wrapping stock imgui
  widgets and reading the text after `##`, and twenty-two `test_ui_*.py` files
  drive the panel that way. A widget drawn purely into a draw list is
  invisible to all of them.
* **Chrome is drawn from eased state, not from the raw boolean.** ImGui holds
  nothing between frames, so the 150ms shadcn transition lives in `ease.Anim`.
* **Every focusable control rings on `:focus-visible`, and only there.**
  Measured on the whole registry, in both themes, every control gives the
  same two-part answer: a 3px `ring/50` band immediately outside the border
  box (`draw.ring`) and the 1px border swapping to `ring`. It needs a
  KEYBOARD focus - a control reached with the pointer matches `:focus` and
  not `:focus-visible` - so the strength comes from `Ui.focus_f`, which
  gates it on `Ui.focus_visible` and eases it. Two measured exceptions: a
  text field rings from a pointer click too (`text_input`), and a Slider's
  thumb also rings on hover and while active (`hover:ring-3 active:ring-3`).
  `ui.hit` has to pass `ButtonFlags_.enable_nav` for any of it to be
  reachable at all; the comment there says why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from imgui_bundle import imgui

import draw as D
import tokens as T
from ease import Anim, mix
from contextlib import contextmanager


@dataclass
class State:
    """What the stock widget reported this frame."""
    hovered: bool = False
    held: bool = False
    clicked: bool = False
    focused: bool = False   # raw imgui focus - see Ui.focus_f for the ring
    hot: float = 0.0        # eased hover, 0..1
    down: float = 0.0       # eased press, 0..1


@dataclass
class Ui:
    """Everything a primitive needs, threaded in one object.

    `dl` must be a real window's draw list, not the background list:
    replay.keep (hyperspace/replay.py:91) only carries the page window's own
    list into the canvas tap, so background-list chrome would vanish from
    `panel:graph`.
    """
    dl: object
    faces: dict
    theme: dict
    anim: Anim
    grad_tex: int | None = None
    theme_name: str = "light"
    _seen: set = field(default_factory=set)

    # Per-widget state that outlives the frame lives on `anim`, because a Ui
    # is rebuilt every frame (dashboard.py:569) and anything kept here would
    # be thrown away before it could be read back.
    @property
    def drag(self) -> dict:
        return self.anim.store["drag"]

    @property
    def texting(self) -> dict:
        return self.anim.store["texting"]

    @property
    def scroll(self) -> dict:
        return self.anim.store.setdefault("scroll", {})

    @property
    def focus_visible(self) -> bool:
        """Whether a focus ring should show at all - CSS `:focus-visible`.

        ImGui has one notion of focus and a mouse click sets it, so a button
        clicked with the pointer kept its ring for ever and the ring walked
        from one button to the next as you clicked them. The browser does
        not do that: `:focus-visible` rings a control reached by KEYBOARD
        and never one reached by pointer.

        So the kit tracks which the last input was. Any mouse button press
        turns it off; Tab or an arrow turns it on. That is the same
        heuristic browsers use, and it is the whole of the difference.
        """
        return bool(self.anim.store.get("kbd", False))

    # -- the measured component tables, resolved for this theme ----------
    def __post_init__(self):
        self.slider_tbl = T.slider_table(self.theme_name)
        self.switch_tbl = T.switch_table(self.theme_name)
        self.input_tbl = T.input_table(self.theme_name)
        self.select_tbl = T.select_table(self.theme_name)
        self.tooltip_tbl = T.tooltip_table(self.theme_name)

    @property
    def viewport(self):
        import box as B
        vp = imgui.get_main_viewport()
        return B.Rect(vp.work_pos.x, vp.work_pos.y,
                      vp.work_size.x, vp.work_size.y)

    def hover_clock(self, key: str, hovered: bool) -> float:
        """Seconds this id has been hovered without a break."""
        h = self.anim.store["hover"]
        if not hovered:
            h.pop(key, None)
            return 0.0
        h[key] = h.get(key, 0.0) + self._dt
        return h[key]

    # -- state ------------------------------------------------------------
    def hit(self, key: str, x, y, w, h, *, allow_overlap: bool = False,
            nav: bool = True) -> State:
        """Place an invisible_button over the rect and read it back.

        `allow_overlap` lets a later, smaller control on top of this one take
        the hover — a row with a kebab in it, for instance. Without it the
        row swallows the button.

        `nav=False` keeps the target out of the Tab order. It is for a
        target that exists only to catch a POINTER: a range slider's track
        is one, and left navigable it swallowed the Tab that belongs to the
        thumbs, so the keyboard could focus a slider and ring nothing.
        """
        if w <= 0 or h <= 0:
            return State()
        if key in self._seen:
            raise ValueError(f"duplicate dkit widget id: {key!r}")
        self._seen.add(key)
        imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
        if allow_overlap:
            imgui.set_next_item_allow_overlap()
        # `enable_nav`, and without it NONE of the kit's focus rings can ever
        # appear. Measured in ImGui 1.92.9: an `invisible_button` submitted
        # plainly is added with `ImGuiItemFlags_NoNav`, so `is_item_focused`
        # is False for ever - under an arrow key, under Tab, and even after
        # `set_keyboard_focus_here`, which is the one case that proves it is
        # the item and not the input. `ImGuiButtonFlags_EnableNav` (1.91) is
        # the supported way back in, and with it focus lands on the frame the
        # window is navigated. The alternative - a real `imgui.button` with
        # its three colours pushed transparent - would also take focus, but
        # it reports `is_item_hovered` True while merely nav-focused, which
        # would light every hover tint in the kit off the keyboard.
        clicked = imgui.invisible_button(
            f"##{key}", imgui.ImVec2(w, h),
            imgui.ButtonFlags_.enable_nav if nav else 0)
        hovered = imgui.is_item_hovered()
        held = imgui.is_item_active()
        # read here or not at all: `is_item_focused` answers for the LAST
        # submitted item, so a caller that asks two draw calls later gets
        # whatever was submitted since. Ring strength is `Ui.focus_f`.
        focused = imgui.is_item_focused()
        return State(
            hovered=hovered, held=held, clicked=clicked, focused=focused,
            hot=self.anim.to(f"{key}:hot", 1.0 if hovered else 0.0),
            down=self.anim.to(f"{key}:down", 1.0 if held else 0.0),
        )

    @property
    def _dt(self) -> float:
        return self.anim.store.get("dt", 1.0 / 60.0)

    _NAV_KEYS = ("tab", "left_arrow", "right_arrow", "up_arrow",
                 "down_arrow", "home", "end", "enter", "space")

    def frame_done(self, dt: float) -> None:
        self.anim.step(dt)
        self.anim.store["dt"] = dt
        self._seen.clear()
        # see `focus_visible`: the last input decides whether a ring shows
        io = imgui.get_io()
        if any(imgui.is_mouse_clicked(b) for b in (0, 1, 2)):
            self.anim.store["kbd"] = False
        else:
            for name in self._NAV_KEYS:
                k = getattr(imgui.Key, name, None)
                if k is not None and imgui.is_key_pressed(k):
                    self.anim.store["kbd"] = True
                    break

    def focus_f(self, key: str, focused: bool, *, disabled: bool = False
                ) -> float:
        """The eased `:focus-visible` ring strength for one control, 0..1.

        The same three lines `comp_button.ui_button` writes out, which every
        ringed control in the kit needs and four of them were missing:

          * the ring is `:focus-visible`, so a control reached with the
            POINTER never gets one - `focus_visible` is the gate;
          * a `disabled` control never rings;
          * it eases on shadcn's 150ms curve rather than snapping.

        The Input is the one measured exception and does not come through
        here: a text field matches `:focus-visible` from a pointer click too.
        See `text_input` and tokens.INPUT.
        """
        on = bool(focused) and self.focus_visible and not disabled
        return self.anim.to(f"{key}:focus", 1.0 if on else 0.0)

    def col(self, name, a: float = 1.0):
        return T.rgba(name, a, theme=self.theme)


# --------------------------------------------------------------------------
# interactive primitives
# --------------------------------------------------------------------------

def button(ui: Ui, key, x, y, w, h, s, *, variant="outline") -> State:
    st = ui.hit(key, x, y, w, h)
    r = T.RADII["md"]
    # shadcn hovers `bg-primary/90`, `bg-accent`; press is the same colour a
    # touch further along, which is what `down` adds on top of `hot`.
    f = min(1.0, st.hot + st.down * 0.35)
    if variant == "default":
        base = ui.col("primary")
        hov = mix(base, ui.col("background"), 0.10)
        D.box(ui.dl, x, y, w, h, fill_col=mix(base, hov, f), radius=r)
        ink = "primary-foreground"
    else:
        rest = ui.col("transparent")
        hov = ui.col("accent")
        D.box(ui.dl, x, y, w, h, fill_col=mix(rest, hov, f),
              border_col=ui.col("border") if variant == "outline" else None,
              radius=r)
        ink = "foreground"
    D.label(ui.dl, x, y, s, ui.faces, "medium", 14, ui.col(ink),
            align="center", box_w=w, baseline_box=h)
    return st


def sidebar_item(ui: Ui, key, x, y, w, h, s, *, active=False, icon=None) -> State:
    st = ui.hit(key, x, y, w, h)
    rest = ui.col("accent") if active else ui.col("transparent")
    hov = ui.col("accent")
    f = min(1.0, st.hot + st.down * 0.4)
    D.fill(ui.dl, x, y, w, h, mix(rest, hov, f), T.RADII["md"])
    ink = mix(ui.col("muted-foreground"), ui.col("foreground"),
              1.0 if active else f)
    tx = x + 10
    if icon and D.icon(ui.dl, icon, x + 10, y + h / 2.0 - 8, 16, ink):
        tx = x + 34
    D.label(ui.dl, tx, y, s, ui.faces, "medium", 14, ink, baseline_box=h)
    return st


def tabs(ui: Ui, key, x, y, h, items, active, *, pad=3.0) -> tuple:
    """Returns (clicked_index_or_None, total_width)."""
    ih = h - 2 * pad
    widths = [D.text_w(s, ui.faces, "medium", 14) + 20 for s in items]
    total = sum(widths) + 2 * pad
    D.fill(ui.dl, x, y, total, h, ui.col("muted"), T.RADII["lg"])
    hit_idx, cx = None, x + pad
    for i, (s, w) in enumerate(zip(items, widths)):
        st = ui.hit(f"{key}.{i}", cx, y + pad, w, ih)
        if st.clicked:
            hit_idx = i
        sel = ui.anim.to(f"{key}:sel{i}", 1.0 if i == active else 0.0)
        if sel > 0.01:
            D.shadow(ui.dl, cx, y + pad, w, ih, (0, 0, 0, 0.10 * sel),
                     T.RADII["md"], dy=1.0, blur=3.0)
            D.fill(ui.dl, cx, y + pad, w, ih,
                   mix(ui.col("transparent"), ui.col("card"), sel),
                   T.RADII["md"])
        ink = mix(ui.col("muted-foreground"), ui.col("foreground"),
                  max(sel, st.hot * 0.7))
        D.label(ui.dl, cx, y + pad, s, ui.faces, "medium", 14, ink,
                align="center", box_w=w, baseline_box=ih)
        cx += w
    return hit_idx, total


def row(ui: Ui, key, x, y, w, h) -> State:
    """A table row: hover tints the whole band, as shadcn's `hover:bg-muted/50`."""
    st = ui.hit(key, x, y, w, h, allow_overlap=True)
    if st.hot > 0.01:
        D.fill(ui.dl, x, y, w, h, mix(ui.col("transparent"),
                                      ui.col("muted", 0.5), st.hot))
    return st


def icon_button(ui: Ui, key, x, y, size, icon, *, glyph=16,
                alpha: float = 1.0) -> State:
    """A square ghost button holding one icon — the kebab trigger's shape.

    `alpha` fades the chrome WITHOUT withdrawing the hit target. A control
    that only reveals on hover must still be submitted every frame: gate its
    submission on the row's hover and it oscillates, because taking the hover
    is exactly what stops the row being hovered. See `row_action`.
    """
    st = ui.hit(key, x, y, size, size)
    if alpha <= 0.001:
        return st
    f = min(1.0, st.hot + st.down * 0.4)
    D.fill(ui.dl, x, y, size, size,
           mix(ui.col("transparent"), ui.col("accent", alpha), f),
           T.RADII["md"])
    ink = mix(ui.col("muted-foreground", alpha), ui.col("foreground", alpha), f)
    D.icon(ui.dl, icon, x + (size - glyph) / 2, y + (size - glyph) / 2,
           glyph, ink)
    return st


def row_action(ui: Ui, key, x, y, size, icon, row_hot: float, *,
               pinned: bool = False, glyph=16) -> State:
    """A control that appears on row hover — a kebab, usually.

    The trap this exists to close: gating submission on `row_hot` makes the
    control flicker and become unclickable. The control takes the hover from
    the row, so the row stops being hovered, so `row_hot` decays, so the
    control is withdrawn, so the row is hovered again. It oscillates at the
    easing's period and a press can land on a frame where the button does not
    exist.

    So it is always submitted, and visibility is `max(row hover, its own
    hover, pinned)` — which is stable under the handover.
    """
    st = ui.hit(key, x, y, size, size)
    vis = max(row_hot, st.hot, 1.0 if pinned else 0.0)
    if vis > 0.001:
        f = min(1.0, st.hot + st.down * 0.4)
        D.fill(ui.dl, x, y, size, size,
               mix(ui.col("transparent"), ui.col("accent", vis), f),
               T.RADII["md"])
        ink = mix(ui.col("muted-foreground", vis), ui.col("foreground", vis), f)
        D.icon(ui.dl, icon, x + (size - glyph) / 2, y + (size - glyph) / 2,
               glyph, ink)
    return st


# --------------------------------------------------------------------------
# Tier 1: the sandwich, over stock widgets
# --------------------------------------------------------------------------
#
# These run a REAL imgui widget for behaviour and paint dkit chrome under it,
# which is Panel._track (hyperspace/ui.py:1311-1357) generalized. Using the
# stock widget rather than hand-rolling the input is not a shortcut, it is the
# constraint: tests/ui_driver.py:43-46 finds controls by wrapping stock
# widgets and reading the text after `##`, and its `enter()` action drives a
# slider by Ctrl+clicking it into a text field - behaviour only
# `imgui.slider_float` has. Twenty-two test files depend on that.
#
# Taper is deliberately NOT in here. `_track` takes a `norm` in 0..1 along
# the throw and lets the caller own the mapping, because a taper belongs to
# the param model rather than to the chrome; the kit follows that.


@contextmanager
def chrome(ui: Ui):
    """Hold the imgui style settings the kit overrides, for a whole frame.

    Two of ImGui's stock colours are visible through every widget the kit
    wraps and neither has any counterpart in shadcn:

      * **`nav_cursor`** — the blue rectangle ImGui draws around whatever
        has keyboard focus. shadcn's focus affordance is the ring this kit
        draws itself (`draw.ring`), on `:focus-visible` only, and the two
        on screen together read as a bug.
      * **`text_selected_bg`** — ImGui's is `(0.26, 0.59, 0.98, 0.35)`. The
        browser's, measured, is `tokens.SELECTION`.

    Putting them here rather than in each component is the point: a widget
    that forgets is still right, and there is one place to change when a
    measurement moves.
    """
    imgui.push_style_color(imgui.Col_.nav_cursor, imgui.ImVec4(0, 0, 0, 0))
    imgui.push_style_color(imgui.Col_.text_selected_bg,
                           imgui.ImVec4(*T.SELECTION))
    try:
        yield ui
    finally:
        imgui.pop_style_color(2)


def _sandwich_begin(ui: Ui, clear_grab: bool = True) -> list:
    """Split the draw list and make the stock widget's own chrome invisible.

    Returns the pushed colour list so `_sandwich_end` can pop the right
    number - the same bookkeeping ui.py:1327-1332 does by hand.
    """
    ui.dl.channels_split(2)
    ui.dl.channels_set_current(1)
    cols = [imgui.Col_.frame_bg, imgui.Col_.frame_bg_hovered,
            imgui.Col_.frame_bg_active]
    if clear_grab:
        cols += [imgui.Col_.slider_grab, imgui.Col_.slider_grab_active]
    clear = imgui.ImVec4(0, 0, 0, 0)
    for c in cols:
        imgui.push_style_color(c, clear)
    # `nav_cursor` is ImGui's blue focus rectangle. No shadcn component has
    # one: focus is a ring the kit draws itself, and only on `focus-visible`.
    # It is cleared here as well as in `chrome()` so a component used on its
    # own - in a test, in the gallery - is never ringed in blue either.
    imgui.push_style_color(imgui.Col_.nav_cursor, clear)
    cols = cols + [imgui.Col_.nav_cursor]
    return cols


def _sandwich_end(ui: Ui, cols: list) -> None:
    imgui.pop_style_color(len(cols))
    ui.dl.channels_set_current(0)


# --------------------------------------------------------------------------
# Scrolling: what was decided, and what was decided against
# --------------------------------------------------------------------------
# NO SMOOTHING, on purpose, for a trackpad or anything else. Nothing here
# interpolates toward a target position; a delta arrives, it is scaled, the
# page moves. Momentum is NOT smoothing and is not ours: macOS keeps sending
# real events after the finger lifts, and we pass them through untouched.
#
# One multiplier, and it is measured rather than tuned - every delta a
# trackpad sends is a multiple of 0.1, so a unit is ten points of finger and
# the rate is 10 px (tokens.SCROLL). Whole pixels out, via `snap_scroll` and
# `draw.px`, because the alternative is text that wobbles.
#
# The one deliberate difference from a browser: Chrome animates a glide per
# NOTCHED WHEEL tick and we step. It only shows with a wheel mouse, and it
# would be easy to add if it ever grates.
#
# Has this session ever seen a FRACTIONAL wheel delta? One is proof of a
# pixel-precise device - a trackpad, a Magic Mouse - because a notched wheel
# only ever sends whole units. It is sticky: a trackpad emits plenty of
# whole-unit deltas mid-gesture, and deciding per event put a 10x jump in
# the middle of every swipe.
_PRECISE = {"seen": False}

# ImGui moves `5 * font_size` px per unit of wheel. The scaling happens in a
# GLFW callback, where there is no frame and no current window, so the step
# is cached from inside the frame by `note_wheel_step`.
_WHEEL = {"step": 90.0}


def wheel_px_per_unit() -> float:
    """How many pixels one unit of raw wheel should move.

    `DKIT_SCROLL_PX` overrides it, so this can be dialled on the machine
    that can feel it without editing code.
    """
    import os
    env = os.environ.get("DKIT_SCROLL_PX")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return T.SCROLL["px_per_unit"] if _PRECISE["seen"] else T.SCROLL["notch_px"]


def snap_scroll(sy: float) -> float:
    """A scroll offset, snapped to a whole pixel.

    `draw.label` rounds a glyph run's origin, because at rest that is what
    keeps type crisp. With a FRACTIONAL offset every line has a different
    fractional y, so as the offset drifts each line crosses .5 at its own
    moment and jumps a whole pixel on its own - the page appears to snap up
    and back down while you scroll slowly. Hyperspace's own panel never did
    this with far faster scrolling, because `ui.py` passes raw floats to
    `add_text` and never rounds; that comparison is what identified the
    rounding as the cause rather than the scroll rate.

    Snapping the OFFSET keeps every line's fractional part constant, so the
    page moves together in whole pixels and the type stays crisp. It is the
    rule this project already measured in the browser: Chromium lays out on
    fractions and snaps what it PAINTS to whole device pixels.

    The offset is fractional in the first place because ImGui's own step is
    `ImFloor(ImMin(5 * font_size, inner_height * 0.67))` - floored, and
    clamped by the window's height - while the scale factor is computed
    from `5 * font_size` alone, so a short region moves a slightly
    different number of pixels than the factor asks for and the remainder
    lands in the offset.
    """
    return float(round(sy))


def note_wheel_step() -> None:
    """Cache ImGui's px-per-unit. Call once per frame, INSIDE the frame."""
    _WHEEL["step"] = 5.0 * max(imgui.get_font_size(), 1.0)


def scale_wheel(delta: float, step: float, px_per_unit: float) -> float:
    """Raw wheel delta -> the units ImGui wants, for `px_per_unit` pixels.

    Pure, so the arithmetic is testable with no GL and no window - the same
    reason `combobox_size` takes a `measure`.
    """
    return px_per_unit * delta / max(step, 1e-6)


def install_wheel(window, impl, *, log=None) -> None:
    """Scale the wheel where it ENTERS, in the GLFW callback.

    This is the only place it can be done, and finding that out cost a
    shipped fix that never ran. The backend's `scroll_callback` calls
    `io.add_mouse_wheel_event`, which QUEUES the event; `io.mouse_wheel` is
    not populated until `imgui.new_frame()`, and ImGui applies the scrolling
    during that same call. So code between `process_inputs()` and
    `new_frame()` - which is where the first version lived - reads zero and
    writes zero, every frame. Its unit test passed because it handed the
    function a fake `io`, which is a lesson of its own: a pure function
    tested in isolation says nothing about whether it is wired to anything.

    WHAT A BROWSER DOES, measured. On macOS a trackpad sends pixel-precise
    deltas and the browser applies them 1:1 with no smoothing of its own -
    one 300px wheel lands at exactly 300 in a single step, checked in
    Chromium. Inertia is the OS as well: AppKit keeps sending events with
    `momentumPhase` set and decaying deltas after the finger lifts. So this
    is only a scale factor, and momentum arrives for free if GLFW forwards
    those events.

    `log(dx, dy)` sees the RAW deltas, which is what `--wheel-probe` prints.
    """
    import glfw

    def _cb(win, dx, dy):
        if dx or dy:
            if (abs(dy - round(dy)) > 1e-4) or (abs(dx - round(dx)) > 1e-4):
                _PRECISE["seen"] = True
            if log is not None:
                log(dx, dy)
            k = wheel_px_per_unit()
            dx = scale_wheel(dx, _WHEEL["step"], k)
            dy = scale_wheel(dy, _WHEEL["step"], k)
        impl.io.add_mouse_wheel_event(dx, dy)

    glfw.set_scroll_callback(window, _cb)


FINE = 0.1          # Shift scales a drag to a tenth, as the panel's does


def slider(ui: Ui, key, x, y, w, h, value, lo=0.0, hi=1.0, *, detents=(),
           snap=0.02, fine=True, disabled=False, fmt="%.3f") -> tuple:
    """shadcn Slider over a real `imgui.slider_float`.

    Returns (changed, value). `value` is in the caller's own domain; a taper
    is the caller's business - pass a 0..1 norm if the mapping is not linear,
    exactly as Panel._track expects.

    `detents` are values to snap to when the result lands within `snap` of
    one, as a fraction of the span. Shift makes a drag ten times finer, which
    the stock slider has no notion of, so it is applied by hand from the
    mouse delta while the item is active.
    """
    span = float(hi - lo) or 1.0
    cols = _sandwich_begin(ui)
    # The stock slider draws its format string across the middle of the
    # widget. shadcn's has no inline text - a readout is a separate label -
    # so it is pushed transparent, EXCEPT while Ctrl+click text entry is up,
    # which is the one time those glyphs are the thing being typed into.
    #
    # imgui_bundle does not expose temp_input_is_active, but text entry lasts
    # many frames, so last frame's answer is good enough: the only cost is
    # that the first frame of entry draws the caret invisibly.
    texting = ui.texting.get(key, False)
    imgui.push_style_color(
        imgui.Col_.text,
        # transparent normally; the theme's ink while text entry is up, since
        # imgui's own default is white and would vanish on the light theme
        imgui.ImVec4(*ui.col("foreground")) if texting
        else imgui.ImVec4(0, 0, 0, 0))
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    imgui.push_item_width(w)
    if disabled:
        imgui.begin_disabled()
    changed, out = imgui.slider_float(f"##{key}", float(value), float(lo),
                                      float(hi), fmt)
    if disabled:
        imgui.end_disabled()
    imgui.pop_item_width()
    active, hovered = imgui.is_item_active(), imgui.is_item_hovered()
    # `is_item_focused` answers for the item just submitted, so it is read
    # here beside the other two rather than after the chrome is drawn.
    kb_focus = imgui.is_item_focused() and ui.focus_visible
    imgui.pop_style_color()
    ui.texting[key] = bool(active and imgui.get_io().want_text_input)
    _sandwich_end(ui, cols)

    # --- Shift: a tenth of the drag -------------------------------------
    st = ui.drag.get(key)
    if fine and active and imgui.get_io().key_shift:
        dx = imgui.get_io().mouse_delta.x
        base = st if st is not None else float(value)
        out = min(max(base + dx / max(w, 1.0) * span * FINE, lo), hi)
        changed = out != value
        ui.drag[key] = out
    elif active:
        ui.drag[key] = out
    else:
        ui.drag.pop(key, None)

    # --- detents ---------------------------------------------------------
    if changed and detents:
        for d in detents:
            if abs(out - d) <= snap * span:
                out = d
                break

    frac = (out - lo) / span
    tbl = ui.slider_tbl
    # The thumb is the one control whose band is not focus-only: it carries
    # `hover:ring-3 focus-visible:ring-3 active:ring-3`, so THREE states turn
    # the same `ring/50` band on. Measured hovered with the pointer,
    # `:focus-visible` false and the band painted - and measured under a real
    # keyboard focus, which is the state this was missing: hover and active
    # were here and `focus-visible` was not, so a slider tabbed to showed
    # nothing at all.
    ring_f = ui.anim.to(
        f"{key}:ring",
        1.0 if (hovered or active or kb_focus) and not disabled else 0.0)
    D.slider(ui.dl, x, y, w, h, [min(max(frac, 0.0), 1.0)], ui.theme, tbl,
             ring_f=ring_f, disabled=disabled)
    ui.dl.channels_merge()
    return changed, out


def switch(ui: Ui, key, x, y, on: bool, *, size="default", disabled=False) -> tuple:
    """shadcn Switch. Returns (clicked, on).

    An invisible_button rather than a stock checkbox: the hit area shadcn
    gives it (`after:-inset-x-3 after:-inset-y-2`) is bigger than the track,
    and a checkbox would draw its own box inside ours. The id is still an
    `##key` on a widget ui_driver knows.
    """
    tw, th, _ = T.SWITCH_SIZES[size]
    st = ui.hit(key, x - 3.0, y - 2.0, tw + 6.0, th + 4.0)
    out = on
    if st.clicked and not disabled:
        out = not on
    on_f = ui.anim.to(f"{key}:on", 1.0 if out else 0.0)
    # No hover chrome at all: measured, the track's fill is byte-identical
    # hovered and at rest. The one state that changes the chrome is
    # `focus-visible`, and it is the WHOLE two-part answer - a 3px `ring/50`
    # band outside the track and the track's own border swapping to `ring`.
    # Measured keyboard-only in both themes: held under the pointer the
    # switch matches `:focus` and not `:focus-visible`, and paints neither.
    focus_f = ui.focus_f(key, st.focused, disabled=disabled)
    D.switch(ui.dl, x, y, on_f, ui.theme, ui.switch_tbl, size=size,
             focus_f=focus_f, disabled=disabled)
    return (st.clicked and not disabled), out


def text_input(ui: Ui, key, x, y, w, text, *, h=None, placeholder="",
               invalid=False, disabled=False, flags=0) -> tuple:
    """shadcn Input over a real `imgui.input_text`. Returns (changed, text).

    The stock widget supplies the caret, the selection, the keyboard and the
    clipboard, none of which is worth rewriting; the sandwich replaces only
    its frame. Focus is read back off the widget so the 3px ring eases in on
    shadcn's own curve rather than snapping.
    """
    tbl = ui.input_tbl
    hh = tbl["h"] if h is None else h
    cols = _sandwich_begin(ui, clear_grab=False)
    # The stock widget draws the text itself, with imgui's own Col_.text -
    # which is WHITE by default. On the dark theme that happens to look
    # right; on the light one the value is invisible against the field. The
    # theme has to be pushed explicitly rather than relied on.
    imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(*ui.col("foreground")))
    # ImGui draws an InputText's text at the cursor PLUS `FramePadding`, and
    # the default is (4, 3). So the value sat 4 right and 3 down of where
    # this put it: the selection band measured 9 px above and 4 below in a
    # 32 px field instead of 6.5 either side, and - worse, because it is
    # visible without selecting anything - the placeholder (drawn here, at
    # `pad_x`) and the value (drawn by imgui, at `pad_x + 4`) did not line
    # up with each other.
    #
    # Zeroing it is better than subtracting it: the frame is the kit's own
    # `draw.field`, the stock one is transparent, so there is no padding for
    # imgui to be adding in the first place and the cursor becomes exactly
    # the text's top-left.
    imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(0, 0))
    # The SAME font `draw.label` draws the placeholder with. Without this
    # the stock widget renders the value in imgui's CURRENT font at imgui's
    # current size, which is not the Geist face at `font * FONT_SPAN_EM` -
    # so the value and the placeholder, one line of one field, had
    # different metrics and did not land on the same rows. Measured 1 px
    # apart on Mesa at density 1; far wider on a Retina Mac, where the
    # atlas is rasterised at 2x, which is where it was spotted.
    #
    # And it is why centring on `font * 1.3` by hand was wrong even after
    # FramePadding went to zero: that is the size the KIT would have used,
    # not the size imgui was about to draw at. `get_font_size()` with the
    # face pushed is the same number for both.
    D.push_css_font(ui.faces, "regular", tbl["font"])
    imgui.set_cursor_screen_pos(
        imgui.ImVec2(x + tbl["pad_x"],
                     y + (hh - imgui.get_font_size()) / 2.0))
    imgui.push_item_width(w - 2.0 * tbl["pad_x"])
    if disabled:
        imgui.begin_disabled()
    changed, out = imgui.input_text(f"##{key}", text, flags=flags)
    if disabled:
        imgui.end_disabled()
    imgui.pop_item_width()
    imgui.pop_font()
    imgui.pop_style_var()
    # NOT gated on `ui.focus_visible`, and that is measured rather than
    # sloppy: a text field is the one control Chromium matches
    # `:focus-visible` on however the focus arrived. Clicked with the
    # pointer, the real Input rings - same `ring/50 0 0 0 3px` band, same
    # `ring` border - where a clicked Button, Switch or SelectTrigger does
    # not. `is_item_active` is imgui's "this field is being edited", which is
    # what a pointer click into it produces; the second term catches a field
    # the keyboard has navigated to but not yet activated.
    focused = (imgui.is_item_active()
               or (imgui.is_item_focused() and ui.focus_visible))
    imgui.pop_style_color()
    _sandwich_end(ui, cols)

    focus_f = ui.anim.to(f"{key}:focus", 1.0 if focused else 0.0)
    D.field(ui.dl, x, y, w, hh, ui.theme, tbl, focus_f=focus_f,
            invalid=invalid, disabled=disabled)
    if placeholder and not out:
        D.label(ui.dl, x + tbl["pad_x"], y, placeholder, ui.faces, "regular",
                tbl["font"], ui.col(*tbl["placeholder"]), baseline_box=hh)
    ui.dl.channels_merge()
    return changed, out


def select(ui: Ui, key, x, y, w, label, items, *, size="default",
           disabled=False, placeholder="Select") -> tuple:
    """shadcn Select: the trigger here, the panel on imgui's popup stack.

    Returns (chosen_id_or_None, open). The popup is menu.popup - the hard
    parts of a popover (focus, dismissal on click-away or Escape, nesting,
    z-order) are already ImGui's and reimplementing them would be the wrong
    kind of work.
    """
    import menu
    hh, rkey = T.SELECT_SIZES[size]
    pkey = f"##sel.{key}"
    st = ui.hit(key, x, y, w, hh)
    # THE KEYBOARD, and the whole of it is `menu`'s. A Select's panel IS
    # `menu.popup`, so the open panel's model comes with it; this one call is
    # the TRIGGER's half - measured on `?probe`'s `select.kb` / `select.kbnone`,
    # a click, Enter, Space, ArrowDown and ArrowUp all open it, on the CHECKED
    # row if there is one and on the first row if there is not. It lives in
    # menu.py so that a second trigger cannot disagree with this one.
    menu.open_from_trigger(ui, pkey, st, role="listbox", disabled=disabled)
    open_ = imgui.is_popup_open(pkey)
    hot = ui.anim.to(f"{key}:hot", 1.0 if st.hovered and not disabled else 0.0)
    # Measured, and the opposite of what this used to do. A trigger reached
    # with the KEYBOARD and still CLOSED rings: `ring/50 0 0 0 3px` and its
    # border -> `ring`, both themes. Open it and Radix moves focus into the
    # listbox, so the trigger's ring goes with it (`:focus-visible` false,
    # box-shadow `none`, border back to `input`) and Escape brings it back. A
    # trigger opened with the POINTER never rings at all. Driving `focus_f`
    # off `open_` painted a ring in exactly the two states that have none.
    focus_f = ui.focus_f(key, st.focused and not open_, disabled=disabled)
    D.select_trigger(ui.dl, x, y, w, hh, ui.theme, ui.select_tbl, size=size,
                     hot=hot, focus_f=focus_f, disabled=disabled, open_=open_)
    ink = "foreground" if label else "muted-foreground"
    D.label(ui.dl, x + ui.select_tbl["pad_l"], y, label or placeholder,
            ui.faces, "regular", ui.select_tbl["font"], ui.col(ink),
            baseline_box=hh,
            max_w=w - ui.select_tbl["pad_l"] - ui.select_tbl["pad_r"]
            - ui.select_tbl["chevron"] - 4.0)
    import box as B
    # `role="listbox"`: a Select's measured keyboard differs from a menu's in
    # exactly two places - an open lands on the CHECKED row whatever the
    # gesture, and PageUp / PageDown do nothing at all.
    # Called EITHER WAY, and the `if open_` that stood here was a seam bug.
    # `menu.popup`'s closed branch is what resets the open animation and pops
    # `menu.LAST_RECT`, so a Select that was never handed a closed frame left
    # its entry in that dict for the rest of the process - and `LAST_RECT` is
    # how a test knows whether the panel is up, so a probe reading it after a
    # Select closed was sampling page pixels through a rect that no longer
    # existed. Same shape, and same fix, as `comp_context_menu.context_menu`,
    # which already says so in its own comment.
    chosen = menu.popup(ui, pkey, items, min_w=w,
                        anchor=B.Rect(x, y, w, hh), side="bottom",
                        align="start", offset=4.0, role="listbox")
    return chosen, open_


# tooltips open after a delay and close at once, which needs a clock rather
# than an eased value: `delay` is in seconds of continuous hover.
TOOLTIP_DELAY = 0.4


def tooltip(ui: Ui, key, anchor, text, *, hovered: bool, side="top",
            delay=TOOLTIP_DELAY, max_w=320.0) -> bool:
    """shadcn Tooltip, placed against `anchor` = (x, y, w, h).

    `hovered` comes from the control's own State, so a tooltip never needs a
    hit target of its own - which matters because one that took the hover
    would steal it from the thing it describes, the same trap `row_action`
    exists to close.

    Drawn straight into the draw list rather than into an imgui popup: a
    tooltip is not interactive, so it needs none of the popup stack, and
    replay.keep (hyperspace/replay.py:91) drops popups from the GRAPH canvas
    tap anyway.
    """
    import box as B
    held = ui.hover_clock(key, hovered)
    if held < delay:
        return False
    tbl = ui.tooltip_tbl
    tw = min(D.text_w(text, ui.faces, "regular", tbl["font"]), max_w)
    pw = tw + 2.0 * tbl["pad_x"]
    ph = tbl["font"] * 1.3 + 2.0 * tbl["pad_y"]
    ax, ay, aw, ah = anchor
    # Radix reserves the arrow's full declared size between panel and anchor
    gap = tbl["arrow_space"] + tbl["side_offset"]
    r, _flipped = B.place_popover(B.Rect(ax, ay, aw, ah), pw, ph, ui.viewport,
                                  side=side, align="center", offset=gap)
    D.tooltip_panel(ui.dl, r.x, r.y, r.w, r.h, ui.theme, tbl,
                    arrow_at=ax + aw / 2.0,
                    side="top" if r.y < ay else "bottom")
    D.label(ui.dl, r.x + tbl["pad_x"], r.y, text, ui.faces, "regular",
            tbl["font"], ui.col(*tbl["fg"]), baseline_box=r.h, max_w=tw)
    return True


def range_slider(ui: Ui, key, x, y, w, h, lo, hi, vmin=0.0, vmax=1.0, *,
                 disabled=False, thumb=None) -> tuple:
    """A two-thumb Slider. Returns (changed, lo, hi).

    Separate from `slider` because one `imgui.slider_float` drives one value:
    a range needs two handles that drag independently, which is the half of
    the Radix law a still frame cannot show. So this one does its own drag
    maths over two `invisible_button`s - still widgets `tests/ui_driver.py`
    can find, since it keys off the text after `##`.

    The cost of not using the stock widget is Ctrl+click numeric entry, which
    a range has no single number for anyway. Everything else - the inset
    thumb law, pixel snapping, the hover ring - is shared with `slider`,
    because both draw through `draw.slider`.
    """
    span = float(vmax - vmin) or 1.0
    flo = min(max((lo - vmin) / span, 0.0), 1.0)
    fhi = min(max((hi - vmin) / span, 0.0), 1.0)
    tz = ui.slider_tbl["thumb"] if thumb is None else thumb
    _track, _rng, thumbs = __import__("box").slider_geom(
        x, y, w, h, [flo, fhi], track_h=ui.slider_tbl["track_h"], thumb=tz)

    changed = False
    hot = 0.0
    kb_focus = False

    # The TRACK is a target too, submitted first and `allow_overlap` so the
    # two thumbs on top of it still take their own hover. Without it a click
    # anywhere but on a thumb did nothing, where the single-thumb slider -
    # a stock `imgui.slider_float` - jumps to the pointer, and so does
    # Radix: pressing the track moves the NEAREST thumb there and hands it
    # the drag.
    #
    # Which thumb was grabbed has to outlive the frame, or a drag that
    # carries one thumb past the other would hop to whichever is nearest
    # mid-gesture. It goes in `ui.drag`, the store that already exists for
    # exactly this.
    def _at_pointer():
        """The value under the pointer, through the SAME inset span the
        thumbs were laid out on - a thumb is inset by its own width, so the
        track's usable run is `w - tz`, not `w`."""
        f = (imgui.get_io().mouse_pos.x - x - tz / 2.0) / max(w - tz, 1.0)
        return vmin + span * min(max(f, 0.0), 1.0)

    tr = ui.hit(f"{key}.track", x, y, w, h, allow_overlap=True, nav=False)
    # The PRESS, not the click: `State.clicked` fires on RELEASE, and by then
    # `held` is already False - the first version chose a thumb and dropped
    # it in the same frame, so nothing moved at all.
    if not tr.held:
        ui.drag.pop(key, None)
    elif key not in ui.drag and not disabled:
        v = _at_pointer()
        # nearest in VALUE, not in pixels: the two agree on a linear track
        # and the value is the thing the caller owns
        ui.drag[key] = "lo" if abs(v - lo) <= abs(v - hi) else "hi"
    grabbed = ui.drag.get(key)
    if grabbed and not disabled:
        v = _at_pointer()
        if grabbed == "lo":
            lo = min(v, hi)
        else:
            hi = max(v, lo)
        changed = True

    for i, (name, val) in enumerate((("lo", lo), ("hi", hi))):
        t = thumbs[i]
        st = ui.hit(f"{key}.{name}", t.x, t.y, t.w, t.h)
        hot = max(hot, st.hot, st.down)
        kb_focus = kb_focus or (st.focused and ui.focus_visible)
        if st.held and not disabled:
            # the thumb is inset by its own width, so the pointer maps back
            # through the SAME span its position was laid out on
            at = (imgui.get_io().mouse_pos.x - x - tz / 2.0) / max(w - tz, 1.0)
            v = vmin + span * min(max(at, 0.0), 1.0)
            if name == "lo":
                lo = min(v, hi)
            else:
                hi = max(v, lo)
            changed = True

    flo = min(max((lo - vmin) / span, 0.0), 1.0)
    fhi = min(max((hi - vmin) / span, 0.0), 1.0)
    # `focus-visible` as well as hover and active, the same three states the
    # single-thumb slider answers to. `draw.slider` takes one `ring_f` for
    # every thumb it draws, so both thumbs ring together - which is what
    # hovering one already did and is not changed here.
    ring_f = ui.anim.to(
        f"{key}:ring",
        0.0 if disabled else max(min(hot, 1.0), 1.0 if kb_focus else 0.0))
    D.slider(ui.dl, x, y, w, h, [flo, fhi], ui.theme, ui.slider_tbl,
             ring_f=ring_f, disabled=disabled)
    return changed, lo, hi


# --------------------------------------------------------------------------
# ScrollArea
# --------------------------------------------------------------------------



@contextmanager
def scroll_area(ui: Ui, key, x, y, w, h, content_h, *, radius=0.0,
                backdrop=None, always=False, pad=0.0, bars=True,
                border=None):
    """A scrolling region with shadcn's overlay scrollbar.

    ImGui's `begin_child` supplies the MECHANISM - the wheel, the clipping,
    the scroll position, keyboard paging, nesting - and reimplementing any
    of that would be wasted work. What it does not supply is the look: its
    scrollbar is a column of the child window, always present, and it takes
    layout space. Radix's floats over the viewport and is 10px wide. So the
    child runs with `no_scrollbar` and the thumb is drawn afterwards, into
    the PARENT's draw list so it sits above the content and is not clipped
    by it.

        with I.scroll_area(ui, "table", x, y, w, h, radius=14) as view:
            ...draw at `view`, which is already scrolled...

    `view` is the content rect, already offset by the scroll position, so a
    caller lays out against it exactly as it would against any other rect.
    `content_h` is how tall that content is - with the layout tree that is
    `box.wants(node)[1]`, which is the question a scroll region exists to
    ask.

    `backdrop` is the colour behind the region: with a `radius` the corners
    are painted back with `draw.cover_corners`, because ImGui clips to a
    rectangle and a draw list cannot erase. That is this primitive's first
    real use - it was built for exactly this and had nothing to call it.

    One deliberate difference from Radix, which is a deviation and not an
    oversight: its default `type="hover"` does not render the scrollbar at
    all until the pointer is over the region, then unmounts it 600ms after
    it leaves - an abrupt appear and disappear. The same information eases
    in here on the kit's own 150ms curve. The GEOMETRY is measured and
    matches to the pixel; only the reveal differs.
    """
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    # `no_background` as well as `no_scrollbar`: a child window paints
    # `Col_.ChildBg` behind its content, and inside a popup that is a SQUARE
    # rectangle over whatever rounded chrome the popup drew - the corners go
    # first. It is transparent in the default dark style, which is exactly
    # the kind of thing that holds until a theme changes it.
    imgui.begin_child(f"##{key}", imgui.ImVec2(w, h), 0,
                      imgui.WindowFlags_.no_scrollbar
                      | imgui.WindowFlags_.no_background)
    # ImGui works a child's scroll range out from the extent its CURSOR
    # reached, and chrome drawn straight into a draw list never moves the
    # cursor - so without this the content measures 0 tall, scroll_max_y is
    # 0 and the wheel does nothing. One zero-width dummy states the height.
    #
    # In WINDOW coordinates, not screen ones. A screen position inside a
    # scrolled child is further down its content the further it has
    # scrolled, so the dummy started lower each frame and the content grew
    # without bound: scroll_max_y went 3238 -> 5638 -> 51238 while the row
    # count never changed.
    imgui.set_cursor_pos(imgui.ImVec2(0.0, 0.0))
    imgui.dummy(imgui.ImVec2(0.0, max(content_h, 0.0)))
    # SNAPPED TO A WHOLE PIXEL, and this is the fix for text that jitters
    # while you scroll slowly.
    #
    # `draw.label` rounds a glyph run's origin - `add_text(round(tx),
    # round(ty))` - because at rest that is what keeps type crisp. With a
    # FRACTIONAL scroll offset every line has a different fractional y, so
    # as the offset drifts each line crosses .5 at its own moment and jumps
    # a whole pixel on its own. The page appears to snap up and back down.
    # Hyperspace's own panel never did this with far faster scrolling,
    # because `ui.py` passes raw floats to `add_text` and never rounds.
    #
    # Rounding the OFFSET instead keeps every line's fractional part
    # constant, so the whole page moves together in whole pixels and the
    # type stays crisp. It is also the rule this project already measured
    # in the browser: Chromium lays out on fractions and snaps what it
    # PAINTS to whole device pixels.
    #
    # The offset is fractional in the first place because ImGui's own step
    # is `ImFloor(ImMin(5 * font_size, inner_height * 0.67))` - floored,
    # and clamped by the window's height - while the scale factor is
    # computed from `5 * font_size` alone. A short region therefore moves a
    # slightly different number of pixels than the factor asks for, and the
    # remainder lands in the offset.
    sy = snap_scroll(imgui.get_scroll_y())
    import box as B
    # The content has to go into the CHILD's draw list, which is what gets
    # clipped to the child's rect. Drawing it into the parent's list instead
    # is not clipped by anything: the first version scrolled correctly and
    # painted the rows straight over the table header above it.
    outer, ui.dl = ui.dl, imgui.get_window_draw_list()
    try:
        yield B.Rect(x + pad, y + pad - sy, w - 2 * pad, h - 2 * pad)
    finally:
        # read INSIDE the child: both are properties of its window
        sy = imgui.get_scroll_y()
        smax = imgui.get_scroll_max_y()
        ui.dl = outer
        imgui.end_child()

        hovered = imgui.is_mouse_hovering_rect(imgui.ImVec2(x, y),
                                               imgui.ImVec2(x + w, y + h))
        if radius and backdrop is not None:
            D.cover_corners(ui.dl, x, y, w, h, radius, backdrop)

        # content height from the child's own scroll range, so the thumb
        # cannot disagree with what actually scrolls
        has = smax > 0.5
        show = ui.anim.to(f"{key}:bar",
                          1.0 if (always or hovered) and has else 0.0)
        # `bars=False` is not a shortcut: shadcn's Combobox list carries
        # `no-scrollbar`, measured as `offsetWidth - clientWidth == 0` in
        # every state including one scrolled by 204px. That list scrolls
        # and shows nothing, and a thumb easing in over it is the kit
        # inventing an affordance the component does not have.
        if bars:
            D.scroll_bar(ui.dl, x, y, w, h, h, h + smax, sy, ui.theme,
                         alpha=show, border=border)
        ui.scroll[key] = (sy, smax)


def scrolled(ui: Ui, key) -> tuple:
    """(scroll_y, scroll_max_y) for a region drawn this frame - what a
    caller needs to know whether there is anything below the fold."""
    return ui.scroll.get(key, (0.0, 0.0))
