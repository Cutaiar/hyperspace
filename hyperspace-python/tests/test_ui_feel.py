"""A feel's curve (ui_feel): motion.response across a time axis fitted to
the feel — a spring's step, a follow's push and let-go — a playhead that
loops it, and the plots on the panel, which still fits its window."""

import math

import pytest
from imgui_bundle import imgui
from test_ui_shell import CONTROL_SIZE, build_rig, frame

import hyperspace.gamepad as gp
from hyperspace import app, modifiers, motion, ui_feel, ui_routing
from hyperspace.motion import Motion
from hyperspace.ui import Panel
from hyperspace.ui_feel import (
    PAUSE,
    RING_CYCLES,
    WINDOW_MIN,
    curve,
    let_go,
    playhead,
    position,
    target,
    window,
)

SPRING = Motion("spring", hz=2.0, damp=0.5)
FOLLOW = Motion("follow", atk=0.1, rel=0.4)


def test_a_springs_curve_is_its_step_response():
    assert let_go(SPRING) is None and target(SPRING, 10.0) == 1.0
    assert position(SPRING, 0.2) == pytest.approx(motion.response(SPRING, 0.2))
    pts = curve(SPRING, 16)
    assert len(pts) == 17 and pts[0] == (0.0, 0.0)
    assert pts[-1][0] == pytest.approx(window(SPRING))


def test_below_critical_a_spring_overshoots_and_at_or_above_it_does_not():
    assert max(y for _, y in curve(Motion("spring", hz=1.5, damp=0.3))) > 1.2
    for damp in (1.0, 2.5):
        pts = curve(Motion("spring", hz=1.5, damp=damp))
        assert max(y for _, y in pts) <= 1.0 + 1e-9
        assert abs(pts[-1][1] - 1.0) <= motion.BAND + 1e-9    # settled by the axis' end


def test_a_follows_curve_is_a_push_out_on_attack_and_home_on_release():
    g = let_go(FOLLOW)
    out, home = motion.settle(FOLLOW), motion.settle(FOLLOW, home=True)
    assert g == pytest.approx(max(out, (out + home) / 3))    # held until the attack arrives
    assert target(FOLLOW, g * 0.5) == 1.0 and target(FOLLOW, g * 1.01) == 0.0
    assert position(FOLLOW, g) >= 1 - motion.BAND
    x = position(FOLLOW, g)
    assert position(FOLLOW, g + 0.2) == pytest.approx(x * math.exp(-0.2 / FOLLOW.rel))
    assert window(FOLLOW) == pytest.approx(g + motion.settle(FOLLOW, home=True))
    assert abs(curve(FOLLOW)[-1][1]) <= motion.BAND               # home by the axis' end


def test_an_instant_edge_still_shows_its_plateau():
    m = Motion("follow", atk=0.0, rel=0.4)
    assert let_go(m) == pytest.approx(window(m) / 4)           # a third of the release's 3/4
    assert position(m, 0.001) == 1.0


def test_the_time_axis_fits_the_feel():
    assert window(Motion("spring", hz=4, damp=1)) < window(Motion("spring", hz=1, damp=1))
    assert window(Motion("spring", hz=2, damp=3)) > window(Motion("spring", hz=2, damp=1))
    assert window(Motion("spring", hz=2.0, damp=0.0)) == pytest.approx(RING_CYCLES / 2.0)
    assert window(Motion("spring", hz=motion.HZ_MAX, damp=1.0)) >= WINDOW_MIN
    assert window(Motion("follow", atk=0.0, rel=0.0)) == pytest.approx(WINDOW_MIN)


def test_the_playhead_sweeps_then_rests_then_sweeps_again():
    w = window(SPRING)
    assert playhead(0.0, SPRING) == 0.0
    assert playhead(w / 2, SPRING) == pytest.approx(w / 2)
    assert playhead(w + PAUSE / 2, SPRING) == pytest.approx(w)
    assert playhead(w + PAUSE + 0.01, SPRING) == pytest.approx(0.01)


def test_a_smooth_modifier_plots_the_feel_it_steps():
    assert modifiers.smooth_motion({"attack": 0.1, "release": 0.5}) == \
        Motion("follow", atk=0.1, rel=0.5)
    m = modifiers.smooth_motion({"attack": 0.05, "spring": 1.0})
    assert m.mode == "spring" and m.damp == modifiers.SPRING_DAMP
    assert m.hz == pytest.approx(1 / (2 * math.pi * 0.05))


@pytest.mark.parametrize("mode", ["off", "follow", "spring"])
def test_the_system_page_fits_with_the_sticks_feel_plotted(tmp_path, monkeypatch, mode):
    """The gamepad section's plot under the feel's knobs, above both
    dials: SYSTEM still fits the control window (no page scrolls,
    test_ui_shell.test_every_page_fits_the_control_window)."""
    drawn, room = [], []
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
        assert r.router.source_feel("axis").mode == mode
        real_draw = ui_feel.draw
        monkeypatch.setattr(ui_feel, "draw", lambda m, *a, **k: (drawn.append(m), real_draw(m, *a, **k)))
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        for _ in range(3):
            frame(r.panel, "system")
        assert (drawn[-1].mode == mode) if mode != "off" else not drawn
        assert room[-1] <= 0


def test_a_smooth_modifiers_block_plots_the_feel_it_steps(tmp_path, monkeypatch):
    """GRAPH's side pane for a selected smooth (`modifier_block`, stacked):
    its params, then its curve; the other kinds draw none."""
    drawn = []
    monkeypatch.setattr(ui_feel, "draw", lambda m, *a, **k: drawn.append(m))
    with build_rig(tmp_path) as r:
        smooth = r.router.table.add_modifier("smooth", ["hand:right.energy"], r.reg,
                                             attack=0.2, spring=1.0)
        curve_ = r.router.table.add_modifier("curve", ["hand:right.energy"], r.reg)
        for m in (smooth, curve_):
            imgui.new_frame()
            imgui.begin("side")
            ui_routing.modifier_block(r.panel, r.router, m, stacked=True)
            imgui.end()
            imgui.end_frame()
        assert drawn == [modifiers.smooth_motion(smooth.params)]
        assert drawn[0].mode == "spring"
