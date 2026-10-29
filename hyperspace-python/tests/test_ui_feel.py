"""A feel drawn live (ui_feel): the reading and what the feel makes of it,
sampled from the Router as the panel draws — a route row's own feel, a
smooth modifier's, the pad's — and the panel still fits its window."""

import math

import numpy as np
import pytest
from imgui_bundle import imgui
from test_ui_shell import CONTROL_SIZE, build_rig, frame

import hyperspace.gamepad as gp
from hyperspace import app, modifiers, motion, ui_feel, ui_graph, ui_routing
from hyperspace.motion import Motion
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.ui import Panel
from hyperspace.ui_feel import KEEP, SPAN_MAX, SPAN_MIN, TRACES, Trace, busiest, sample, span

DT = 1 / 60
SPRING = Motion("spring", dur=0.5, bounce=0.3)
FOLLOW = Motion("follow", atk=0.1, rel=0.4)


# ---- the span, the trace ----

def test_the_span_is_twice_the_settle_within_its_bounds():
    out, home = motion.settle(FOLLOW), motion.settle(FOLLOW, home=True)
    assert span(FOLLOW) == pytest.approx(2 * (out + home))
    assert span(Motion("spring", dur=0.05, bounce=0.0)) == SPAN_MIN      # tight: the floor
    assert span(Motion("spring", dur=4.0, bounce=-0.5)) == SPAN_MAX      # lazy: the ceiling
    assert span(Motion("spring", dur=0.5, bounce=1.0)) == pytest.approx(3.0)   # rings: 3 periods
    assert span(motion.OFF) == SPAN_MIN


def test_a_trace_keeps_the_last_seconds_and_marks_what_was_not_live():
    tr = Trace()
    tr.push(0.0, 0.2, 0.1)
    tr.push(0.5, None, None)             # not live: a gap
    tr.push(0.5, 0.4, 0.3)               # drawn twice in a frame: one sample, the last
    assert len(tr.pts) == 2 and tr.pts[-1] == (0.5, 0.4, 0.3)
    tr.push(1.0, 0.6, None)
    assert math.isnan(tr.pts[-1][2])
    assert [t for t, _, _ in tr.since(1.0, 0.6)] == [0.5, 1.0]
    tr.push(SPAN_MAX + 0.6, 0.0, 0.0)    # the oldest have fallen off
    assert tr.pts[0][0] == 1.0


def test_sample_keeps_a_trace_per_key_on_the_panel_and_drops_stale_ones():
    class P:
        pass
    p = P()
    a = sample(p, "a", 0.1, 0.2, now=0.0)
    assert sample(p, "a", 0.3, 0.4, now=0.1) is a and len(a.pts) == 2
    for i in range(KEEP):
        sample(p, ("old", i), 0.0, 0.0, now=0.0)
    sample(p, "new", 0.0, 0.0, now=SPAN_MAX + 1)         # past KEEP: the stale go
    assert set(getattr(p, TRACES)) == {"new"}


def test_busiest_is_the_trace_that_moved_most_lately():
    still, moved = Trace(), Trace()
    for k in range(10):
        still.push(k * 0.1, 0.5, 0.5)
        moved.push(k * 0.1, 0.5 + 0.04 * k, 0.5)
    assert busiest([still, moved], 0.9, 2.0) == 1
    assert busiest([still, still], 0.9, 2.0) == 0


# ---- live on the panel ----

def _draws(monkeypatch) -> list:
    drawn = []
    real = ui_feel.draw

    def rec(m, trace, width, height, title=""):
        right = imgui.get_cursor_screen_pos().x + width
        edge = imgui.get_window_pos().x + imgui.get_window_width()
        drawn.append((m, trace, title, right <= edge + 0.5))
        real(m, trace, width, height, title)
    monkeypatch.setattr(ui_feel, "draw", rec)
    return drawn


def test_a_route_rows_plot_is_its_reading_and_what_its_feel_made_of_it(tmp_path, monkeypatch):
    drawn = _draws(monkeypatch)
    with build_rig(tmp_path) as r:
        b = Binding("lfo:0", "view.inst_amp", "push", 1.0, rest=0.0, motion=SPRING)
        router = r.panel.router = Router(r.reg, Bindings([b]))
        for u in (0.0, 0.8, 0.8):
            router.feed("lfo", np.array([u]))
            router.modulate(None, DT)
            r.reg.apply()
            imgui.new_frame()
            imgui.set_next_window_size(imgui.ImVec2(360, 400))     # GRAPH's side pane, narrow
            imgui.begin("rows", flags=imgui.WindowFlags_.no_scrollbar)
            ui_graph.route_rows(r.panel, [b])
            imgui.end()
            imgui.end_frame()
        m, trace, _, fits = drawn[-1]
        assert m == SPRING and fits                       # the row's width, never past it
        _, raw, felt = trace.pts[-1]
        assert raw == pytest.approx(0.8)
        assert felt == pytest.approx(router.felt_now(b))
        assert 0.0 < felt < 0.8                           # on its way: the spring at work
        router.feed("lfo", None)                          # not live: a gap, no follower
        router.modulate(None, DT)
        assert router.felt_now(b) is None


def test_a_smooth_modifier_plots_its_input_and_its_output(tmp_path, monkeypatch):
    drawn = _draws(monkeypatch)
    with build_rig(tmp_path) as r:
        router = r.router
        smooth = router.table.add_modifier("smooth", ["lfo:0"], r.reg, attack=0.2)
        curve_ = router.table.add_modifier("curve", ["lfo:0"], r.reg)
        router.feed("lfo", np.array([0.9]))
        for _ in range(2):
            router.modulate(None, DT)
        for m in (smooth, curve_):
            imgui.new_frame()
            imgui.begin("side")
            ui_routing.modifier_block(r.panel, router, m, stacked=True)
            imgui.end()
            imgui.end_frame()
        assert [d[0] for d in drawn] == [modifiers.smooth_motion(smooth.params)]  # curve: none
        _, raw, felt = drawn[0][1].pts[-1]
        assert raw == pytest.approx(0.9)
        assert felt == pytest.approx(ui_routing.modifier_output(router, smooth.id))


def test_the_pad_plot_shows_the_stick_that_moved_after_the_pads_feel(tmp_path, monkeypatch):
    drawn = _draws(monkeypatch)
    with build_rig(tmp_path) as r:
        router = r.router
        r.reg["desk.pad.feel"].set(motion.MODES.index("spring"))
        router.labels["axis"] = ["left stick X", "left stick Y"]
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        for k in range(6):
            lanes = [0.5, 0.5 + 0.08 * k]                 # the left stick's Y moves
            router.feed("axis", np.array(lanes))
            router.felt("axis", lanes, DT)                # the camera job's followers
            frame(r.panel, "system")
        m, trace, title, fits = drawn[-1]
        assert m.mode == "spring" and title == "left stick Y" and fits
        _, raw, felt = trace.pts[-1]
        assert raw == pytest.approx(0.9)
        assert felt == pytest.approx(router.felt_lanes("axis")[1])


@pytest.mark.parametrize("mode", ["off", "follow", "spring"])
def test_the_system_page_fits_with_the_sticks_feel_plotted(tmp_path, monkeypatch, mode):
    """The gamepad section's live plot beside the feel's knobs, above both
    dials: SYSTEM still fits the control window, across and down (no page
    scrolls, test_ui_shell.test_every_page_fits_the_control_window)."""
    drawn = _draws(monkeypatch)
    room = []
    real = Panel._page_system

    def measured(self, dt):
        real(self, dt)
        room.append(imgui.get_scroll_max_y())
    monkeypatch.setattr(Panel, "_page_system", measured)
    with build_rig(tmp_path) as r:
        pad = gp.Pad()
        r.panel.pad = pad
        app._register_dial(r.reg, pad)
        r.reg["desk.pad.feel"].set(motion.MODES.index(mode))
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        for _ in range(3):
            frame(r.panel, "system")
        if mode == "off":
            assert not drawn
        else:
            assert drawn[-1][0].mode == mode and drawn[-1][3]   # drawn, inside the window
        assert room[-1] <= 0
