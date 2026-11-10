"""shadcn Checkbox, driven - and the Switch hit area it exposed.

The chrome is in the pixel diff (`checkbox.*` cells, both themes). The diff
is blind to behaviour by construction, so every behaviour measured on the
real component on `?probe` is driven here instead:

* the stretched hit area - 11px either side, 7px above and below - and the
  Switch's, which was 3 and 2 until the Checkbox was measured;
* Space toggles and Enter does NOT (Radix follows WAI-ARIA; ImGui activates
  a focused button on both);
* the ring is keyboard-only, and a disabled box neither toggles nor rings;
* a click on the Label toggles the box, as `htmlFor` does;
* the tick SNAPS while the fill eases.

    xvfb-run -a uv run python -m pytest hyperspace/dkit/dev/test_checkbox.py -q -n0
"""

from __future__ import annotations

from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

from hyperspace.dkit import box as B
from hyperspace.dkit import tokens as T
from hyperspace.dkit.dev.test_interaction import (
    DWELL,
    FAR,
    PROBE_X,
    PROBE_Y,
    _gl_or_skip,
    ground_of,
    left_band,
    one_widget,
    ring_ink,
)

SIZE = T.CHECKBOX["size"]


def click_at(x, y, *, after=DWELL):
    """A pointer script: settle, press for two frames, release, dwell."""
    return [(x, y)] * 4 + [(x, y, True)] * 2 + [(x, y, False)] * after


def run_checkbox(script=None, keys=None, *, on=False, theme="light", **kw):
    from hyperspace.dkit import interact as I
    state = {"on": on, "clicks": 0}

    def paint(ui):
        c, state["on"] = I.checkbox(ui, "cb", PROBE_X, PROBE_Y, state["on"],
                                    **kw)
        state["clicks"] += int(c)

    script = script or [FAR] * DWELL
    frames = one_widget(theme, paint, len(script), script=script, keys=keys)
    return state, frames


# --------------------------------------------------------------------------
# geometry - pure, no GL
# --------------------------------------------------------------------------

def test_the_hit_area_is_the_measured_after_box():
    """`after:-inset-x-3 -inset-y-2` is 12 and 8 by the classes, but the
    pseudo element is inset from the PADDING box, a border inside the edge.
    ?probe measured its computed size as 38 x 30 around the 16px checkbox
    and 54 x 32.390625 around the 32 x 18.390625 switch."""
    cb = B.stretched_hit(0, 0, SIZE, SIZE, stretch=T.HIT_STRETCH,
                         border=T.CHECKBOX["border_w"])
    assert (cb.x, cb.y, cb.w, cb.h) == (-11.0, -7.0, 38.0, 30.0)
    tw, th, _ = T.SWITCH_SIZES["default"]
    sw = B.stretched_hit(0, 0, tw, th, stretch=T.HIT_STRETCH, border=1.0)
    assert (sw.x, sw.y, sw.w) == (-11.0, -7.0, 54.0)
    assert abs(sw.h - 32.390625) < 1e-9


# --------------------------------------------------------------------------
# the pointer
# --------------------------------------------------------------------------

# Offsets from the box's top-left, each at least a pixel clear of the edge
# of the 38 x 30 target: ?probe clicked the real one at every whole pixel,
# and these are the points it toggled at (inside) and did not (outside).
INSIDE = [(8, 8), (-10.5, 8), (26.5, 8), (8, -6.5), (8, 22.5),
          (-10.5, -6.5), (26.5, 22.5)]
OUTSIDE = [(-12.5, 8), (28.5, 8), (8, -8.5), (8, 23.5)]


@pytest.mark.parametrize("dx,dy", INSIDE)
def test_a_click_inside_the_stretched_target_toggles(dx, dy):
    _gl_or_skip()
    st, _ = run_checkbox(click_at(PROBE_X + dx, PROBE_Y + dy))
    assert st["on"] is True and st["clicks"] == 1, (
        f"a click at ({dx}, {dy}) from the box did not toggle it; the real "
        f"one toggles anywhere in its 38 x 30 ::after")


@pytest.mark.parametrize("dx,dy", OUTSIDE)
def test_a_click_outside_the_stretched_target_does_nothing(dx, dy):
    _gl_or_skip()
    st, _ = run_checkbox(click_at(PROBE_X + dx, PROBE_Y + dy))
    assert st["on"] is False, f"a click at ({dx}, {dy}) toggled the box"


def test_one_click_toggles_once_and_a_second_toggles_back():
    _gl_or_skip()
    c = (PROBE_X + 8, PROBE_Y + 8)
    st, _ = run_checkbox(click_at(*c, after=12) + click_at(*c))
    assert st["clicks"] == 2 and st["on"] is False


def test_a_disabled_checkbox_ignores_the_pointer():
    _gl_or_skip()
    st, _ = run_checkbox(click_at(PROBE_X + 8, PROBE_Y + 8), disabled=True)
    assert st["on"] is False and st["clicks"] == 0


# --------------------------------------------------------------------------
# the keyboard
# --------------------------------------------------------------------------

def test_space_toggles_and_enter_does_not():
    """Measured on ?probe: a focused Radix checkbox toggles on Space and
    ignores Enter. ImGui activates a focused button on BOTH, so without the
    filter in `interact.checkbox` Enter would toggle it."""
    from imgui_bundle import imgui
    _gl_or_skip()
    st, _ = run_checkbox(keys=[(2, imgui.Key.tab), (8, imgui.Key.enter)])
    assert st["on"] is False, "Enter toggled a checkbox"
    st, _ = run_checkbox(keys=[(2, imgui.Key.tab), (8, imgui.Key.space)])
    assert st["on"] is True, "Space did not toggle a focused checkbox"


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_ring_is_keyboard_only(theme_name):
    """`focus-visible:ring-3 ring/50` - a band outside the box under the
    keyboard, and nothing after a pointer click, which on ?probe left the box
    focused (`document.activeElement`) with `box-shadow: none`."""
    from imgui_bundle import imgui
    _gl_or_skip()
    ground = ground_of(theme_name)
    _, rest = run_checkbox(theme=theme_name)
    _, kb = run_checkbox(keys=[(2, imgui.Key.tab)], theme=theme_name)
    _, clicked = run_checkbox(click_at(PROBE_X + 8, PROBE_Y + 8),
                              theme=theme_name)
    band = [ring_ink(left_band(f[-1], PROBE_X, PROBE_Y, SIZE), ground)
            for f in (rest, kb, clicked)]
    assert band[0] < 1.0, f"an untouched checkbox painted outside: {band[0]:.1f}"
    assert band[1] > 10.0, f"no ring under the keyboard: {band[1]:.1f}"
    assert band[2] < 1.0, f"a CLICKED checkbox rang: {band[2]:.1f}"


def test_a_disabled_checkbox_never_rings_and_space_does_nothing():
    from imgui_bundle import imgui
    _gl_or_skip()
    st, fs = run_checkbox(keys=[(2, imgui.Key.tab), (8, imgui.Key.space)],
                          disabled=True)
    assert st["on"] is False
    ink = ring_ink(left_band(fs[-1], PROBE_X, PROBE_Y, SIZE), ground_of("light"))
    assert ink < 1.0, f"a disabled checkbox rang: {ink:.1f}"


# --------------------------------------------------------------------------
# the label
# --------------------------------------------------------------------------

def label_box():
    """Where the label is, asked of the token table and the font - the gap,
    the font size and the text's own width - not copied from ?probe."""
    from imgui_bundle import imgui  # noqa: F401  (a context exists in run)
    c = T.CHECKBOX
    return (PROBE_X + SIZE + c["label_gap"],
            PROBE_Y + (SIZE - c["label_font"]) / 2.0, c["label_font"])


def test_a_click_on_the_label_toggles_the_box():
    _gl_or_skip()
    lx, ly, fs = label_box()
    # 20px into "Accept terms", well inside the text and right of the box's
    # own 11px stretch, so only the label can have taken it
    st, _ = run_checkbox(click_at(lx + 20, ly + fs / 2), label="Accept terms")
    assert st["on"] is True and st["clicks"] == 1


def test_the_label_target_is_the_text_line_not_the_row():
    """The browser's label box is 14px tall; a click 5px above the text is
    on nothing. The box's own stretched target ends left of the label."""
    _gl_or_skip()
    lx, ly, _fs = label_box()
    st, _ = run_checkbox(click_at(lx + 20, ly - 5), label="Accept terms")
    assert st["on"] is False


def test_a_disabled_label_does_not_toggle_the_box():
    _gl_or_skip()
    lx, ly, fs = label_box()
    st, _ = run_checkbox(click_at(lx + 20, ly + fs / 2), label="Accept terms",
                         disabled=True)
    assert st["on"] is False


# --------------------------------------------------------------------------
# the transition: the fill eases, the tick snaps
# --------------------------------------------------------------------------

def test_the_tick_snaps_while_the_fill_eases(monkeypatch):
    """Measured on ?probe: the indicator is `transition-none` and Radix
    unmounts it when unchecked, so on a check the tick is there on the first
    frame over a fill at 0-8%, and on an uncheck it is gone on the first
    frame while the fill fades out over ~150ms.

    Read at the call into draw, because a light tick over a fill that has
    barely started is white on white - pixels cannot tell the two apart in
    the first frames, and this has to be able to fail.
    """
    from hyperspace.dkit import draw as D
    _gl_or_skip()
    calls = []
    real = D.checkbox

    def spy(dl, x, y, on_f, tick, *a, **k):
        calls.append((on_f, tick))
        return real(dl, x, y, on_f, tick, *a, **k)

    monkeypatch.setattr(D, "checkbox", spy)
    c = (PROBE_X + 8, PROBE_Y + 8)
    run_checkbox(click_at(*c, after=20) + click_at(*c, after=20))
    first_on = next(i for i, (_f, t) in enumerate(calls) if t)
    on_f, _ = calls[first_on]
    assert on_f < 0.3, (
        f"the tick appeared only once the fill was at {on_f:.2f}; it should "
        f"be there on the toggle frame")
    eased = [f for f, _t in calls[first_on:first_on + 20]]
    assert eased[-1] > 0.99 and any(0.1 < f < 0.9 for f in eased), (
        "the fill did not ease in - it snapped, or never arrived")
    first_off = next(i for i, (_f, t) in enumerate(calls)
                     if i > first_on and not t)
    assert calls[first_off][0] > 0.7, (
        "the tick lingered while the fill faded; the real one is gone at once")


# --------------------------------------------------------------------------
# the Switch, whose hit area was the Tailwind step numbers read as pixels
# --------------------------------------------------------------------------

@pytest.mark.parametrize("dx", [-8.5, -4.5])
def test_the_switch_takes_a_click_off_its_left_end(dx):
    """The kit inflated the Switch by `x - 3, y - 2`. Its recipe carries the
    same `after:-inset-x-3 -inset-y-2` as the Checkbox, and the real one is
    the pointer target 11px past each end - so a click 4-11px off the track
    landed in the browser and did nothing here."""
    from hyperspace.dkit import interact as I
    _gl_or_skip()
    _tw, th, _ = T.SWITCH_SIZES["default"]
    state = {"on": False}

    def paint(ui):
        _c, state["on"] = I.switch(ui, "sw", PROBE_X, PROBE_Y, state["on"])

    one_widget("light", paint, DWELL + 6,
               script=click_at(PROBE_X + dx, PROBE_Y + th / 2))
    assert state["on"] is True, f"a click {-dx}px left of the switch missed"
