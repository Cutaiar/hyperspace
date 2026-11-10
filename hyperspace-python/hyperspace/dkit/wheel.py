"""The scroll wheel: how a raw delta becomes pixels, and where it is scaled.

Moved out of `interact.py` (`HANDOFF.md` item 3b) because it is the part of
the kit with the most measurement behind it per line - the 10 px per unit,
the 0.1 GLFW scale factor, whole-pixel offsets - and it touches nothing else
in that module. `interact.py` re-exports every name a caller uses, so
`I.install_wheel(` and `I.note_wheel_step()` in `dashboard.py` are unchanged.

`_PRECISE` and `_WHEEL` are module state, MUTATED in place and never
rebound. That is what keeps the re-exported `interact._PRECISE` the same
object as this one; rebinding either here would silently split them.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import tokens as T
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
