"""The CAMERA section on dkit (`ui_camera.py`, `ui_kit.py`): the kit's
HANDOFF item 5. Driven through the real route — GRAPH, the pane, `ui.page`
focusing the section — so the kit is measured where a person meets it.

Each test is about a behaviour a person has at the stock widgets and must
still have on the kit's, or about the kit actually being the thing drawn:
a test that passes against the fallback proves nothing about the port, so
`test_the_section_is_the_kit` is first and the rest lean on it."""

import math

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace import ui, ui_camera, ui_fields, ui_graph, ui_kit
from hyperspace.ui import PAGE_KEYS

WIDE = (1600, 900)      # the pane beside the canvas (test_ui_pane.WIDE)
SLIDERS = ui_camera.ORBIT + ui_camera.EYE


def _rig(r, monkeypatch) -> Driver:
    r.panel.desk = False
    imgui.get_io().display_size = imgui.ImVec2(*WIDE)
    d = Driver(step=lambda: frame(r.panel))
    d.record(monkeypatch.setattr)
    d.run(d.wait(2))
    ui_graph._state(r.panel)["side_w"] = ui_graph.SIDE_W
    r.reg["ui.page"].set(PAGE_KEYS.index("camera"))
    d.run(d.wait(4))
    return d


@pytest.fixture()
def cam(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        yield r, _rig(r, monkeypatch)


def _h(rect) -> float:
    return rect[3] - rect[1]


def test_the_section_is_the_kit(cam):
    """The kit is there, the section drew on it (its state on the panel),
    and every control is the kit's: a slider is the kit's 20 px row, not
    the stock frame's 28."""
    r, d = cam
    assert ui_kit.ready()
    assert ui_kit.STATE in r.panel.__dict__
    for pid in SLIDERS:
        assert _h(d.rect(pid)) == ui_fields.SLIDER_H, pid
    assert _h(d.rect(ui_camera.RESET)) == ui_kit.mod("comp_button").BUTTON_SIZES["sm"]["h"]


def test_without_the_kit_the_section_is_drawn_as_before(tmp_path, monkeypatch):
    """``HYPERSPACE_KIT=0``: the stock widgets, at the stock frame's height."""
    monkeypatch.setenv(ui_kit.ENV, "0")
    with build_rig(tmp_path) as r:
        d = _rig(r, monkeypatch)
        assert ui_kit.STATE not in r.panel.__dict__
        assert _h(d.rect("camera.zoom")) == pytest.approx(imgui.get_frame_height())


def test_a_log_slider_pressed_at_its_middle_reads_its_geometric_middle(cam):
    """camera.zoom is log, 0.005 … 200, so its middle is 1× — what the
    stock slider gave and the kit's must (`SliderFlags_.logarithmic`); a
    linear throw would put ~100× there."""
    r, d = cam
    r.reg["camera.zoom"].set_value(30.0)
    d.run(d.click("camera.zoom"), d.park())
    assert r.view.zoom == pytest.approx(1.0, rel=0.15)


def test_a_slider_press_lands_where_the_thumb_is_drawn(cam):
    """The stock slider's throw and the kit thumb's agree: a press at a
    point of the track leaves the thumb's centre under it (to imgui's 2 px
    grab padding)."""
    r, d = cam
    p = r.reg["camera.pan.x"]
    thumb = ui_kit.mod("tokens").SLIDER["thumb"]
    for u in (0.2, 0.75):
        d.run(d.wait(2))      # (a write dirties the patch: the strip above can move the body)
        x0, y0, x1, y1 = d.rect("camera.pan.x")
        at = x0 + thumb / 2 + (x1 - x0 - thumb) * u
        d.run(d.click((at, (y0 + y1) / 2)), d.park())
        drawn = x0 + thumb / 2 + (x1 - x0 - thumb) * p.norm
        assert abs(drawn - at) <= 2.5, (u, drawn, at)


def test_ctrl_click_types_a_value_not_a_fraction(cam):
    r, d = cam
    d.run(d.enter("camera.zoom", 2.5), d.park())
    assert r.view.zoom == pytest.approx(2.5)
    d.run(d.enter("camera.yaw", 1.0), d.park())
    assert r.view.yaw == pytest.approx(1.0)


def test_a_drag_moves_each_slider(cam):
    r, d = cam
    for pid in SLIDERS:
        p = r.reg[pid]
        p.set_value(p.lo + (p.hi - p.lo) * 0.25 if not p.log else math.sqrt(p.lo * p.hi) / 2)
        before = p.base
        d.run(d.wait(2))      # the controls where they are after the write (see above)
        x, y = d.centre(pid)
        d.run(d.move((x - 30, y)), d.press(True), d.move((x + 30, y), 6), d.press(False),
              d.park())
        assert p.base > before, pid


def test_a_shift_drag_moves_a_tenth_as_far(cam):
    """The panel's own fine mode (`Panel._fine_throw`), measured over the
    kit thumb's throw: the same 100 px moves the value a tenth as far."""
    r, d = cam
    p = r.reg["camera.pan.x"]

    def drag(held: bool) -> float:
        p.set_value(0.0)
        d.run(d.wait(2))
        x, y = d.centre("camera.pan.x")
        io = imgui.get_io()
        d.run(d.move((x, y)), d.press(True))
        start = p.base
        if held:
            io.add_key_event(imgui.Key.mod_shift, True)
        d.run(d.move((x + 100, y), 8), d.press(False))
        if held:
            io.add_key_event(imgui.Key.mod_shift, False)
        d.run(d.park())
        return p.base - start

    plain, fine = drag(False), drag(True)
    assert plain > 0 and fine == pytest.approx(plain * ui.FINE, rel=0.1)


def test_reset_view_is_the_kit_button_and_resets(cam):
    r, d = cam
    r.reg["camera.zoom"].set_value(4.0)
    r.reg["camera.yaw"].set_value(1.2)
    d.run(d.click(ui_camera.RESET), d.park())
    assert r.view.zoom == pytest.approx(1.0) and r.view.yaw == 0.0


def test_a_right_click_opens_the_params_menu(cam):
    """On the slider and on its label, as the stock row's (`Panel._ctx`,
    `_ctx_label`)."""
    r, d = cam
    shown: list[str] = []
    real = r.panel._ctx_learn_block
    r.panel._ctx_learn_block = lambda a, p: (shown.append(a.id), real(a, p))[1]
    d.run(d.click("camera.yaw", button=1), d.wait(2))
    assert "camera.yaw" in shown
    d.run(d.key(imgui.Key.escape), d.park(), d.wait(2))
    shown.clear()
    x0, y0, x1, _ = d.rect("camera.pitch")
    d.run(d.click((x0 + 8, y0 - 10), button=1), d.wait(2))   # its header, above the slider
    assert "camera.pitch" in shown


def test_learns_frame_hangs_off_the_kit_slider(cam):
    """`Panel._learn_frame` (Learn's red outline) is asked for each param
    while that param's kit slider is the last item, so the frame goes
    round the kit's control and not round something drawn after it."""
    r, d = cam
    seen: dict[str, tuple] = {}
    real = r.panel._learn_frame

    def spy(p):
        seen[p.id] = (imgui.get_item_rect_min().y, imgui.get_item_rect_max().y)
        real(p)

    r.panel._learn_frame = spy
    d.run(d.wait(1))
    for pid in SLIDERS:
        _x0, y0, _x1, y1 = d.rect(pid)
        assert seen[pid] == (y0, y1), pid
    assert seen[ui_camera.RESET] == (d.rect(ui_camera.RESET)[1], d.rect(ui_camera.RESET)[3])


def test_the_section_fits_the_narrowest_pane(tmp_path, monkeypatch):
    """At `SIDE_MIN` nothing passes the pane's edge, and the key hint is
    the first thing to go (REVIEW: a widget fits its narrowest width)."""
    with build_rig(tmp_path) as r:
        d = _rig(r, monkeypatch)
        ui_graph._state(r.panel)["side_w"] = ui_graph.SIDE_MIN
        d.run(d.wait(3))
        (x, _y), (w, _h) = ui_graph._state(r.panel)["details_rect"]
        for pid in (*SLIDERS, ui_camera.RESET):
            assert d.rect(pid)[2] <= x + w + 1, pid


def test_a_rows_label_stays_in_its_column(tmp_path, monkeypatch):
    """`Panel._label_cell` on the kit cuts a label to its column (the stock
    slider's opaque frame hid the overflow; the kit's thin track does not:
    "KNOB SMOOTHING" ran into its fill), and its hover says the whole of it."""
    from hyperspace import ui as ui_mod
    drawn: list[tuple[str, float]] = []
    real = ui_mod.fit_micro

    def fit(text, width, least=12.0):
        out = real(text, width, least)
        drawn.append((text, width, out))
        return out
    monkeypatch.setattr(ui_mod, "fit_micro", fit)
    with build_rig(tmp_path) as r:
        d = _rig(r, monkeypatch)
        r.reg["ui.page"].set(PAGE_KEYS.index("system"))
        d.run(d.wait(3))
    knob = [x for x in drawn if x[0] == r.reg["desk.slew"].label]
    assert knob, drawn[:5]
    text, width, out = knob[-1]
    assert out != text.upper() and out.endswith("…")
    assert width == ui.LABEL_W - ui.LABEL_GAP
