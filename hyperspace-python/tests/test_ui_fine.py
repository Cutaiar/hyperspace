"""Wave 2 T2 (register rows 607–608): holding Shift while dragging a
continuous slider or fader on the panel moves the value a tenth as far;
letting Shift go mid-drag goes back to coarse without a jump; the drag is
one undo step; a toggle and an integer slider are untouched; the tooltip
says FINE while Shift is held over a control that has the mode.

Driven through imgui's own input queue (`tests/ui_driver.py`), each
control found by its param id, on the VIEW page: `view.inst_persp` is an
untapered float slider (`Panel._slider`), `view.bright` a tapered fader
(`Panel._fader`), `view.instances` a tapered integer slider and
`view.inst_fit` a toggle."""

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, page_frame
from ui_driver import Driver

from hyperspace import ui, undo
from hyperspace.app import CONTROL_SIZE
from hyperspace.field import NAMES

DX = 120.0     # px the mouse travels in each drag


@pytest.fixture()
def view_page(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        r.view.instances, r.view.inst_layout = 12, NAMES.index("FCC")   # the depth slider shows
        d = Driver(step=lambda: page_frame(r.panel, "view"))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        yield r, d


def shift(down: bool):
    imgui.get_io().add_key_event(imgui.Key.mod_shift, down)
    yield


def drag(d: Driver, pid: str, dx: float, *, held: bool = False, frames: int = 8):
    """Press at the control's centre, move `dx` px along it over `frames`,
    release — with Shift held throughout when `held`."""
    x, y = d.centre(pid)
    if held:
        yield from shift(True)
    yield from d.move((x, y))
    yield from d.press(True)
    yield from d.move((x + dx, y), frames)
    yield from d.press(False)
    if held:
        yield from shift(False)
    yield from d.park()


def plain_and_fine(r, d, pid: str, read, reset) -> tuple[float, float]:
    """The value's change under a plain drag and under a Shift drag of the
    same `DX`, each from the press (a plain press jumps to the mouse)."""
    reset()
    d.run(d.wait(1))
    x, y = d.centre(pid)
    d.run(d.move((x, y)), d.press(True))
    at_press = read()                       # a plain press lands where the mouse is
    d.run(d.move((x + DX, y), 8), d.press(False), d.park())
    plain = read() - at_press
    reset()
    d.run(d.wait(1))
    before = read()
    d.run(drag(d, pid, DX, held=True))
    return plain, read() - before


def test_a_shift_drag_moves_a_float_slider_a_tenth_as_far(view_page):
    r, d = view_page
    p = r.reg["view.inst_persp"]
    plain, fine = plain_and_fine(r, d, "view.inst_persp", lambda: p.base,
                                 lambda: p.set_value(0.3))
    assert plain > 0.2                                   # the plain drag went somewhere
    assert fine == pytest.approx(plain * ui.FINE, rel=0.05)


def test_a_shift_drag_moves_a_tapered_fader_a_tenth_as_far(view_page):
    r, d = view_page
    p = r.reg["view.bright"]
    plain, fine = plain_and_fine(r, d, "view.bright", lambda: p.position(),
                                 lambda: p.set_position(p.steps // 4))
    assert plain >= 10                                   # detents (100 across the throw)
    assert fine == pytest.approx(plain * ui.FINE, abs=1)  # whole detents
    assert 0 < fine < plain


def test_a_shift_press_does_not_jump_to_the_mouse(view_page):
    r, d = view_page
    p = r.reg["view.inst_persp"]
    p.set_value(0.1)
    d.run(d.wait(1))
    x0, y0, x1, y1 = d.rect("view.inst_persp")
    d.run(shift(True), d.move((x0 + (x1 - x0) * 0.8, (y0 + y1) / 2)), d.press(True), d.wait(2))
    assert p.base == pytest.approx(0.1)                  # a plain press would land near 0.8
    d.run(d.press(False), shift(False), d.park())
    assert p.base == pytest.approx(0.1)


def test_letting_shift_go_mid_drag_returns_to_coarse_without_a_jump(view_page):
    r, d = view_page
    p = r.reg["view.inst_persp"]
    p.set_value(0.2)
    d.run(d.wait(1))
    x0, y0, x1, y1 = d.rect("view.inst_persp")
    x, y = (x0 + x1) / 2, (y0 + y1) / 2          # the mouse sits far from the grab's 0.2
    d.run(shift(True), d.move((x, y)), d.press(True), d.move((x + 60, y), 4))
    fine = p.base - 0.2
    assert 0 < fine < 0.05
    d.run(shift(False), d.wait(2))               # Shift up, the mouse still
    assert p.base == pytest.approx(0.2 + fine)   # no jump to the mouse's place on the track
    d.run(d.move((x + 120, y), 4))               # coarse again: the full rate
    coarse = p.base - (0.2 + fine)
    assert coarse == pytest.approx(fine * 10, rel=0.1)
    d.run(d.press(False), d.park())
    assert p.base == pytest.approx(0.2 + fine + coarse)


def test_a_fine_drag_is_one_undo_step(view_page):
    r, d = view_page
    p = r.reg["view.inst_persp"]
    u = undo.Undo(r.reg, r.router.table)
    clock = [0.0]

    def step():
        page_frame(r.panel, "view")
        clock[0] += 1 / 60
        u.tick(clock[0])

    p.set_value(0.4)
    d.step = step
    d.run(d.wait(40))                            # settled: the set is behind us
    u.clear()
    d.run(drag(d, "view.inst_persp", DX, held=True, frames=30))
    moved = p.base
    assert moved > 0.4
    d.run(d.wait(40))
    assert u.undo() and p.base == pytest.approx(0.4)
    assert not u.undo()                          # one step, not one a frame
    assert u.redo() and p.base == pytest.approx(moved)


def test_a_toggle_and_an_integer_slider_are_untouched_by_shift(view_page):
    r, d = view_page
    v = r.view
    fit = v.inst_fit
    d.run(shift(True), d.click("view.inst_fit"), shift(False), d.park())
    assert v.inst_fit is not fit                 # a shift-click toggles as a click does
    p = r.reg["view.instances"]
    x0, y0, x1, y1 = d.rect("view.instances")
    at = (x0 + (x1 - x0) * 0.7, (y0 + y1) / 2)
    d.run(d.click(at), d.park())
    plain = p.base
    p.set_value(1)
    d.run(d.wait(1))
    d.run(shift(True), d.click(at), shift(False), d.park())
    assert p.base == plain                       # absolute, as without Shift


def test_the_tooltip_says_fine_while_shift_is_held(view_page, monkeypatch):
    _, d = view_page
    said: list[str] = []
    monkeypatch.setattr(ui, "tooltip", said.append)
    d.run(d.move("view.inst_persp"), d.wait(1))
    assert said and not any("FINE" in s for s in said)
    said.clear()
    d.run(shift(True), d.wait(1))
    assert said and said[-1].startswith(ui.FINE_TIP)
    d.run(d.move("view.instances"))
    said.clear()
    d.run(d.wait(1))                             # an integer: no fine mode, no word
    assert not any("FINE" in s for s in said)
    d.run(shift(False), d.park())


def test_shift_joining_mid_drag_does_not_step_back(view_page):
    """⇧ pressed in the same frame the mouse moves: that frame's movement
    counts at the fine rate from where the grab was — not lost, and the
    grab never steps back to last frame's value (review, PR #348)."""
    r, d = view_page
    p = r.reg["view.inst_persp"]
    x0, y0, x1, y1 = d.rect("view.inst_persp")
    x, y = (x0 + x1) / 2, (y0 + y1) / 2
    d.run(d.move((x, y)), d.press(True), d.move((x + 40, y), 4))   # a plain drag
    coarse = p.base
    io = imgui.get_io()

    def join():
        io.add_key_event(imgui.Key.mod_shift, True)
        d.mouse = (x + 70, y)
        io.add_mouse_pos_event(*d.mouse)                           # the same frame
        yield
    d.run(join())
    joined = p.base
    assert joined > coarse                                         # no step back
    d.run(d.move((x + 130, y), 4))
    fine_60 = p.base - joined
    d.run(d.press(False), shift(False), d.park())
    assert joined - coarse == pytest.approx(fine_60 / 2, rel=0.15)  # the join frame's 30 px, fine


def test_a_shift_press_on_a_log_slider_writes_nothing(view_page):
    """`view.inst_spacing` is a log range: a press that has not moved
    leaves its base bit-for-bit, so no undo step opens (review, PR #348)."""
    r, d = view_page
    p = r.reg["view.inst_spacing"]
    u = undo.Undo(r.reg, r.router.table)
    clock = [0.0]

    def step():
        page_frame(r.panel, "view")
        clock[0] += 1 / 60
        u.tick(clock[0])

    p.set_value(1.34)                            # a value log2 / 2** does not round-trip
    d.step = step
    d.run(d.wait(40))
    u.clear()
    was = p.base
    x0, y0, x1, y1 = d.rect("view.inst_spacing")
    d.run(shift(True), d.move((x0 + (x1 - x0) * 0.85, (y0 + y1) / 2)), d.press(True),
          d.wait(3), d.press(False), shift(False), d.park(), d.wait(40))
    assert p.base == was
    assert not u.undo()


def test_a_tapered_slider_keeps_a_base_between_detents_on_a_shift_press(tmp_path, monkeypatch):
    """`Panel._slider` on a tapered param (as MEDIA draws a channel's gain)
    with a base between detents — where a lane or a drive left it: a ⇧
    press does not snap it to a detent; a ⇧ drag then walks a tenth as far
    as a plain one (review, PR #348)."""
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)

        def step():
            imgui.new_frame()
            r.panel._fine_frame()
            imgui.set_next_window_pos(imgui.ImVec2(0, 0))
            imgui.set_next_window_size(imgui.ImVec2(700, 200))
            imgui.begin("fine test")
            r.panel._slider("view.bright", 600)
            imgui.end()
            imgui.end_frame()

        d = Driver(step=step)
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        p = r.reg["view.bright"]
        x0, y0, x1, y1 = d.rect("view.bright")
        x, y = x0 + (x1 - x0) * 0.8, (y0 + y1) / 2
        d.run(d.move((x, y)), d.press(True))
        at_press = p.position()
        d.run(d.move((x - 2 * DX, y), 8), d.press(False), d.park())
        plain = at_press - p.position()                # detents, plain
        assert plain >= 20
        p.set(p.taper.map(30.5))                       # half-way between detents 30 and 31
        was = p.base
        d.run(d.wait(1))
        d.run(shift(True), d.move((x, y)), d.press(True), d.wait(3))
        assert p.base == was                           # no snap, no jump to the mouse
        d.run(d.move((x - 2 * DX, y), 8), d.press(False), shift(False), d.park())
        fine = 30.5 - p.position()
        assert fine == pytest.approx(plain * ui.FINE, abs=1)
