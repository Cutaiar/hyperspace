"""Plan-03 state tests: tapers, control semantics, transport math, faces."""

import math

import pytest

from hyperspace import tapers
from hyperspace.analysis import Analyser
from hyperspace.bands import PRESETS, Chain
from hyperspace.control import UNDO_S, Control
from hyperspace.geometry import SHAPES, faces

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
    c = Control(Chain(Analyser()), clock=clock)
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


def test_scene_count_and_rows():
    assert len(PRESETS) == 11


# -------------------------------------------------------------- transport

def test_transport_position_math():
    import numpy as np

    from hyperspace.audio import AudioEngine

    a = AudioEngine()
    a.track = np.zeros(48_000 * 4)  # 4 s at 48 kHz
    a._track_sr = 48_000.0
    a.playing = True
    a._offset, a._played = 0, 48_000
    assert a.position() == pytest.approx(1.0)
    a.toggle_play()  # pause freezes position
    assert not a.playing
    assert a.position() == pytest.approx(1.0)
    a.toggle_play()  # resume from the same offset
    assert a.position() == pytest.approx(1.0)
    a._played = 48_000 * 5  # loop fold: 1s offset + 5s played on a 4s track
    assert a.position() == pytest.approx(2.0)
    a.restart()  # RTZ preserves transport state
    assert a.playing
    assert a.position() == pytest.approx(0.0)


def test_loopback_detection():
    from hyperspace.audio import is_loopback

    assert is_loopback("BlackHole 2ch")
    assert is_loopback("Loopback Audio")
    assert not is_loopback("MacBook Pro Microphone")


def test_ring_buffer():
    import numpy as np

    from hyperspace.audio import _Ring

    r = _Ring(8)
    r.push(np.array([1.0, 2.0, 3.0]))
    assert list(r.drain()) == [1.0, 2.0, 3.0]
    assert len(r.drain()) == 0
    r.push(np.arange(10.0))  # overflow: only the last 8 survive
    assert list(r.drain()) == list(np.arange(2.0, 10.0))


# ------------------------------------------------------------------ faces

FACE_COUNTS = {
    "5-cell": 10,
    "Tesseract": 24,
    "16-cell": 32,
    "24-cell": 96,
    "Rectified 5-cell": 30,
    "Cubic pyramid": 18,
    "3,3-duoprism": 15,
    "Icosahedral prism": 70,
    "Dodecahedral prism": 54,
}


@pytest.mark.parametrize("name", FACE_COUNTS, ids=str)
def test_face_counts(name):
    i = next(k for k, s in enumerate(SHAPES) if s.name == name)
    assert len(faces(i)) == FACE_COUNTS[name]


@pytest.mark.slow
def test_face_counts_heavy():
    by_name = {s.name: i for i, s in enumerate(SHAPES)}
    assert len(faces(by_name["120-cell"])) == 720
    assert len(faces(by_name["600-cell"])) == 1200
    assert len(faces(by_name["Clifford torus"])) == 560


# --------------------------------------------------- headless panel smoke

def test_panel_draws_headless():
    """Run one full imgui frame of the panel with no window — catches any
    imgui API misuse without needing a display."""
    from imgui_bundle import imgui

    from hyperspace.audio import AudioEngine
    from hyperspace.render import ViewState
    from hyperspace.ui import PAGE_KEYS, PAGES, Panel, apply_style, load_fonts

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
