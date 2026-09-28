"""Plan-03 state tests: tapers, control semantics, transport math, faces."""

import math

import pytest

from hyperspace import tapers
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import SCENES, UNDO_S, Control

# ---------------------------------------------------------------- tapers

ALL_TAPERS = {
    "T_TRIM": tapers.T_TRIM,
    "T_DEPTH": tapers.T_DEPTH,
    "T_DRIVE": tapers.T_DRIVE,
    "T_DYN": tapers.T_DYN,
    "T_BRIGHT": tapers.T_BRIGHT,
    "T_SPEED": tapers.T_SPEED,
    **{k.key: k.t for k in tapers.KNOBS},
}


@pytest.mark.parametrize("name", ALL_TAPERS, ids=str)
def test_taper_round_trip(name):
    """The law: unmap(map(p)) == p over the whole throw, every taper."""
    t = ALL_TAPERS[name]
    for p in range(t.steps + 1):
        assert t.unmap(t.map(p)) == p, f"{name} walks sideways at position {p}"


def test_trim_taper_off_notch():
    t = tapers.T_TRIM
    assert t.map(0) == -math.inf
    assert t.unmap(-math.inf) == 0
    assert t.map(1) == -60.0
    assert t.map(t.steps) == 12.0
    assert t.map(t.unity) == 0.0  # detent lands exactly on 0 dB


def test_depth_taper_default():
    # position 100 lands on 2.60 exactly — where the default has always been
    assert abs(tapers.T_DEPTH.map(100) - 2.6) < 1e-12


def test_formatters():
    assert tapers.fmt_gain(0) == "off"
    assert tapers.fmt_db(-math.inf) == "off"
    assert tapers.fmt_db(0) == "0 dB"  # zero is bare: no sign
    assert tapers.fmt_db(-6) == "−6 dB"
    assert tapers.fmt_time(1.5) == "1.50 s"
    assert tapers.fmt_time(0.25) == "250 ms"


# ---------------------------------------------------------------- control

class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture()
def ctl():
    clock = FakeClock()
    c = Control(Analyzer(Analyser()), clock=clock)
    return c, clock


def test_reset_resolves_to_selected_scene(ctl):
    c, _ = ctl
    c.select_scene(4)  # Bass Engine — MID band trim −10 dB
    c.chain.params[3].trim = 5.0  # fiddle
    c.reset_band(3)
    assert c.chain.params[3].trim == -10, "reset must go to the scene, not defaults"


def test_reset_all_undo_window(ctl):
    c, _ = ctl
    c.chain.params[1].pre = 3.3
    c.reset_all_clicked()  # resets to Balanced
    assert c.chain.params[1].pre == 1
    assert c.undo_armed
    c.reset_all_clicked()  # second click inside the window = undo
    assert c.chain.params[1].pre == 3.3
    assert not c.undo_armed


def test_undo_window_lapses(ctl):
    c, clock = ctl
    c.chain.params[1].pre = 3.3
    c.reset_all_clicked()
    clock.t += UNDO_S + 0.1
    assert not c.undo_armed  # lapsed
    c.reset_all_clicked()  # this is a fresh reset, not an undo
    assert c.chain.params[1].pre == 1


def test_scene_change_discards_undo(ctl):
    c, _ = ctl
    c.chain.params[0].post = 2.0
    c.reset_all_clicked()
    assert c.undo_armed
    c.select_scene(2)
    assert not c.undo_armed, "the snapshot belongs to the old scene"


def test_shaper_change_resets_scratch(ctl):
    c, _ = ctl
    c.chain.st[2]["e"] = 0.7
    c.set_shaper(2, 9)
    assert c.chain.st[2] == {}
    assert c.chain.params[2].fn == 9


def test_scene_count_and_order():
    # the index is what the APC40's clip grid and saved projects hold
    assert len(SCENES) == 11 and SCENES[0] == "Balanced" and SCENES[4] == "Bass Engine"


# --------------------------------------------------- headless panel smoke

def test_panel_draws_headless():
    """Run one full imgui frame of the panel with no window — catches any
    imgui API misuse without needing a display."""
    from imgui_bundle import imgui

    from hyperspace.audio import AudioEngine
    from hyperspace.ui import PAGE_KEYS, PAGES, Panel, apply_style, load_fonts
    from hyperspace.view import ViewState

    ctx = imgui.create_context()
    try:
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(1280, 820)
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        apply_style()
        load_fonts()
        audio = AudioEngine()
        panel = Panel(Control(audio.chain), audio, ViewState())  # no library: no strips
        # every page of the rail, twice (the second frame has layout state)
        for k in range(len(PAGES)):
            panel.reg["ui.page"].set(k)
            for _ in range(2):
                imgui.new_frame()
                panel.draw(1 / 60, 60.0)
                imgui.end_frame()
        # the strip follows the analyzer's band count, not the legacy six
        panel.reg["ui.page"].set(PAGE_KEYS.index("analyzer"))
        for change in (panel.reg["band.remove"].fire, panel.reg["band.add"].fire,
                       panel.reg["band.add"].fire):
            change()
            imgui.new_frame()
            panel.draw(1 / 60, 60.0)
            imgui.end_frame()
        assert audio.chain.n == 7
    finally:
        imgui.destroy_context(ctx)
