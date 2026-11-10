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

import math

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame, page_frame
from ui_driver import Driver

from hyperspace import ui, ui_graph, undo
from hyperspace.app import CONTROL_SIZE
from hyperspace.field import NAMES
from hyperspace.motion import Motion
from hyperspace.routing import Binding

DX = 120.0     # px the mouse travels in each drag


@pytest.fixture()
def view_page(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        r.view.instances, r.view.inst_layout = 12, NAMES.index("fcc")   # the depth slider shows
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


# ---- what T2 left out (row 731): the sliders drawn straight from imgui ----


def rows_frame(r, rows):
    """One frame of a route's rows, as GRAPH's side pane draws them, wide."""
    imgui.new_frame()
    r.panel._fine_frame()
    imgui.set_next_window_pos(imgui.ImVec2(10, 10))
    imgui.set_next_window_size(imgui.ImVec2(900, 300))
    imgui.begin("rows")
    ui_graph.route_rows(r.panel, rows)
    imgui.end()
    imgui.end_frame()


@pytest.fixture()
def route(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        b = r.router.table.add(Binding("lane:1", "view.bright", "push", 0.2, rest=0.4))
        d = Driver(step=lambda: rows_frame(r, [b]))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        yield r, d, b


def fine_and_plain(d, key, read, reset, dx=DX):
    """How far a Shift drag and a plain drag of `dx` move a raw slider, each
    read from the press (a plain press lands where the mouse is)."""
    reset()
    d.run(d.reveal(key))
    x, y = d.centre(key)
    d.run(d.move((x, y)), d.press(True))
    at_press = read()
    d.run(d.move((x + dx, y), 8), d.press(False), d.park())
    plain = read() - at_press
    reset()
    d.run(d.wait(1))
    before = read()
    d.run(drag(d, key, dx, held=True))
    return read() - before, plain


def test_a_shift_drag_moves_a_routes_depth_and_rest_a_tenth_as_far(route):
    _, d, b = route
    fine, plain = fine_and_plain(d, "depth", lambda: b.value, lambda: setattr(b, "value", 0.2),
                                 20)
    assert plain > 0.1 and fine == pytest.approx(plain * ui.FINE, rel=0.05)
    fine, plain = fine_and_plain(d, "rest", lambda: b.rest, lambda: setattr(b, "rest", 0.4), 6)
    assert plain > 0.1 and fine == pytest.approx(plain * ui.FINE, rel=0.05)


def test_the_readout_and_the_fill_are_the_values_through_a_fine_drag(route, monkeypatch):
    """imgui's slider follows the mouse; what it is told to print must not.
    A real slider, the mouse far right of a depth at +0.20."""
    _, d, b = route
    shown: list[str] = []
    fills: list[float] = []
    real, track = imgui.slider_float, ui.Panel._track

    def noted(label, v, lo, hi, fmt="%.3f", *a):
        if label == "##depth":
            shown.append(fmt)
        return real(label, v, lo, hi, fmt, *a)

    def tracked(self, draw, norm, *a, **k):
        fills.append(norm)
        return track(self, draw, norm, *a, **k)
    monkeypatch.setattr(ui.Panel, "_track", tracked)
    from hyperspace import ui_kit
    if ui_kit.ready():          # on the kit the fill is the fraction the kit slider is handed
        I = ui_kit.mod("interact")
        real_kit = I.slider

        def kit_slider(k, key, *a, **kw):
            if key == "depth":
                fills.append(kw["frac"])
            return real_kit(k, key, *a, **kw)
        monkeypatch.setattr(I, "slider", kit_slider)
    d2 = Driver(step=d.step)                     # (over a wrap of its own, so the driver sees it)
    monkeypatch.setattr(imgui, "slider_float", noted)
    d2.record(monkeypatch.setattr)
    b.value = 0.2
    d2.run(d2.wait(1))
    _x0, y0, x1, y1 = d2.rect("depth")
    y = (y0 + y1) / 2
    d2.run(shift(True), d2.move((x1 - 2, y)), d2.press(True), d2.wait(2))
    assert shown[-1] == "+0.20" and b.value == pytest.approx(0.2)
    d2.run(d2.move((x1 + 8, y), 2))
    assert 0.2 < b.value < 0.3
    d2.run(d2.wait(1))
    assert float(shown[-1]) == pytest.approx(b.value, abs=0.006)     # not imgui's +1.00
    from hyperspace import ui_kit
    # (stock: the rest's fill is drawn last; the kit's list holds the depth's alone)
    fill = fills[-1] if ui_kit.ready() else fills[-2]
    assert fill == pytest.approx((b.value + 1) / 2, abs=1e-6)
    d2.run(d2.press(False), shift(False), d2.park())


def test_a_depth_a_file_left_out_of_range_comes_in_without_a_jump(route):
    """Row 608's no-jump holds for 1.5 on a ±1 slider: it creeps in, no further out."""
    _, d, b = route
    b.value = 1.5
    d.run(d.wait(1))
    x, y = d.centre("depth")
    d.run(shift(True), d.move((x, y)), d.press(True), d.move((x - 10, y), 2))
    moved = b.value
    assert 1.4 < moved < 1.5
    d.run(d.move((x + 200, y), 4))
    assert moved < b.value <= 1.5
    d.run(d.press(False), shift(False), d.park())


def test_a_shift_press_leaves_an_auto_rest_auto_until_the_mouse_moves(route):
    """A press with no move writes nothing: a rest following its source stays so."""
    _, d, b = route
    b.rest = None
    d.run(d.wait(1))
    x, y = d.centre("rest")
    d.run(shift(True), d.move((x, y)), d.press(True), d.wait(2), d.press(False), shift(False),
          d.park())
    assert b.rest is None


def test_a_shift_drag_on_a_routes_feel_follows_a_log_slider_along_its_curve(route):
    """`dur` is logarithmic: a fine drag is a tenth of the plain drag along
    the throw, where its log moves evenly, not its value."""
    _, d, b = route
    start = Motion("spring", dur=0.2, bounce=0.0)

    def reset():
        b.motion = start
    reset()
    d.run(d.wait(1))
    fine, plain = fine_and_plain(d, "dur", lambda: math.log(b.motion.dur), reset, 30)
    assert plain > 0.1 and fine == pytest.approx(plain * ui.FINE, rel=0.1)
    fine, plain = fine_and_plain(d, "bounce", lambda: b.motion.bounce, reset, 30)
    assert plain > 0.05 and fine == pytest.approx(plain * ui.FINE, rel=0.1)


def test_the_raw_tooltip_says_fine_while_shift_is_held(route, monkeypatch):
    _, d, _b = route
    said: list[str] = []
    monkeypatch.setattr(ui, "tooltip", said.append)
    d.run(d.move("depth"), d.wait(1))
    assert said and not any("FINE" in s for s in said)
    said.clear()
    d.run(shift(True), d.wait(1))
    assert said and said[-1].startswith(ui.FINE_TIP) and "Depth" in said[-1]
    x, y = d.centre("depth")
    d.run(d.press(True), d.move((x, y + 200), 4))        # off the track, still held
    said.clear()
    d.run(d.wait(1))
    assert said and set(said) == {ui.FINE_TIP}
    d.run(d.press(False), shift(False), d.park())


def test_a_shift_drag_moves_a_macro_subscribers_from_and_to_a_tenth_as_far(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(1600, 1200)
        table = r.router.table
        table.set_macros({"macro.1": {"subs": [{"base": "view.depth4", "from": 0.2, "to": 0.8}]}},
                         r.reg)
        d = Driver(step=lambda: page_frame(r.panel, "routing"))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        s = table.macros["macro.1"].subs[0]
        fine, plain = fine_and_plain(d, "from", lambda: s.lo, lambda: setattr(s, "lo", 0.2), 6)
        assert plain > 0.05 and fine == pytest.approx(plain * ui.FINE, rel=0.1)
        fine, plain = fine_and_plain(d, "to", lambda: s.hi, lambda: setattr(s, "hi", 0.5), 6)
        assert plain > 0.05 and fine == pytest.approx(plain * ui.FINE, rel=0.1)


def test_a_shift_drag_moves_graphs_backdrop_a_tenth_as_far(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(1600, 900)
        d = Driver(step=lambda: frame(r.panel))
        frame(r.panel, "graph")
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        st = ui_graph._state(r.panel)
        st["backdrop"] = True
        d.run(d.wait(2))
        fine, plain = fine_and_plain(d, "graph.backdrop", lambda: st["backdrop_alpha"],
                                     lambda: st.__setitem__("backdrop_alpha", 0.3), 20)
        assert plain > 0.1 and fine == pytest.approx(plain * ui.FINE, rel=0.1)


def test_a_slider_keeps_its_shape_through_a_drag(route, monkeypatch):
    """A raw slider's readout grows as its value does ("200 ms" to "1584 ms");
    on the kit the slider's room for it is the widest it ever says, so the
    control under the pointer keeps one width all through a drag — it used to
    flip between a track and a value box mid-drag, and the drag with it."""
    _, d, b = route
    b.motion = Motion("spring", dur=0.2, bounce=0.0)
    d.run(d.wait(1))
    widths: list[float] = []
    real = imgui.slider_float

    def noted(label, *a, **k):
        out = real(label, *a, **k)
        if label == "##dur":
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            widths.append(round(hi.x - lo.x, 3))
        return out
    monkeypatch.setattr(imgui, "slider_float", noted)
    d.run(d.reveal("dur"))
    x0, y0, x1, y1 = d.rect("dur")
    y = (y0 + y1) / 2
    d.run(d.move((x0 + 4, y)), d.press(True), d.move((x1 + 200, y), 12), d.press(False), d.park())
    assert b.motion.dur > 1.0                           # it went the whole way…
    assert len(set(widths)) == 1, sorted(set(widths))   # …in one shape
