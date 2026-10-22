"""The SEQ page (ui_seq.py, plan 31 U): draws with and without a
sequencer, every widget has its own imgui id, a click on a cell is an
undoable param write, the playhead and the length show on the grid, and
the envelope strips add and remove extras as undo steps."""

from types import SimpleNamespace

import pytest
from imgui_bundle import imgui, implot

from hyperspace import envelope, hotreload, lfo, sequencer, tempo, ui, ui_seq, undo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.app import CONTROL_SIZE
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.params import build_registry
from hyperspace.routing import Bindings
from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts
from hyperspace.view import ViewState


@pytest.fixture()
def rig(tmp_path):
    ictx = imgui.create_context()
    pctx = implot.create_context()
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(*CONTROL_SIZE)
    io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
    apply_style()
    load_fonts()
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
    view = ViewState()
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(view, control, audio, lib.project)
    clock = tempo.Clock(now=lambda: 0.0)
    lfos = lfo.LFOs(seed=2)
    envs = envelope.Envelopes()
    seq = sequencer.Sequencer()
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    envelope.register(reg, envs, clock)
    sequencer.register(reg, seq, clock)
    lib.attach(reg)
    panel = Panel(control, audio, view, bank=lib.project, registry=reg, library=lib)
    panel.clock, panel.lfos, panel.envs, panel.seq = clock, lfos, envs, seq
    try:
        yield SimpleNamespace(panel=panel, reg=reg, clock=clock, envs=envs, seq=seq)
    finally:
        implot.destroy_context(pctx)
        imgui.destroy_context(ictx)


def frame(panel):
    panel.reg["ui.page"].set(PAGE_KEYS.index("seq"))
    imgui.new_frame()
    panel.draw(1 / 60, 60.0)
    imgui.end_frame()


def _record(monkeypatch, *fns):
    seen: list[tuple[int, str]] = []
    for fn in fns:
        real = getattr(imgui, fn)

        def rec(label, *a, _real=real, **k):
            seen.append((imgui.get_id(label), label))
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    return seen


WIDGETS = ("button", "checkbox", "slider_float", "slider_int", "combo", "begin_combo",
           "invisible_button", "small_button", "arrow_button")


def _draw_page(panel):
    imgui.new_frame()
    imgui.begin("page")
    ui_seq.page(panel, 1 / 60)
    imgui.end()
    imgui.end_frame()


def _undo(rig):
    u = undo.Undo(rig.reg, Bindings([]), banks=lambda: {"env": rig.envs})
    undo.install(u)
    t = [0.0]

    def settle():
        for _ in range(3):
            t[0] += 1.0
            u.tick(t[0])
    settle()
    return u, settle


def test_the_page_is_in_pages_after_lfo():
    assert PAGE_KEYS.index("seq") == PAGE_KEYS.index("lfo") + 1
    assert hasattr(Panel, "_page_seq")
    mods = hotreload.MODULES
    assert mods.index("ui_lfo") < mods.index("ui_seq") < mods.index("ui")


def test_the_page_draws_with_the_default_bank(rig):
    seq, envs, clock = rig.seq, rig.envs, rig.clock
    assert envs.ids() == [1, 2, 3, 4, 5]
    rig.reg["seq.run"].set(True)
    rig.reg["seq.1.1"].set(True)
    rig.reg["seq.2.3"].set(True)
    rig.reg["seq.2.mute"].set(True)
    for k in range(4):
        t = k * 0.13
        clock.tick(t)
        seq.step(t, clock, lambda i, n, at, v: envs.fire(n, at=at, velocity=v))
        envs.step(1 / 60, t, clock)
        frame(rig.panel)
    for m in range(len(envelope.MODES)):
        rig.reg["env.1.mode"].set(m)
        frame(rig.panel)


def test_the_page_says_so_without_a_sequencer(rig):
    rig.panel.seq = rig.panel.envs = None
    frame(rig.panel)
    frame(rig.panel)


def test_the_default_page_fits_the_control_window(rig, monkeypatch):
    over = {}
    draw = Panel._page_seq

    def measured(self, dt):
        draw(self, dt)
        over["seq"] = imgui.get_scroll_max_y()
    monkeypatch.setattr(Panel, "_page_seq", measured)
    for _ in range(3):
        frame(rig.panel)
    assert over["seq"] == 0


@pytest.mark.parametrize("extras", [0, 3, 11])
def test_no_conflicting_ids(rig, monkeypatch, extras):
    """With the five lane envelopes, and with extras up to the cap."""
    for _ in range(extras):
        rig.envs.add()
    assert len(rig.envs) == 5 + extras
    for _ in range(2):
        frame(rig.panel)
    for opened in (None, rig.envs.ids()[-1]):
        ui_seq.open_strip(rig.panel, opened)
        seen = _record(monkeypatch, *WIDGETS)
        _draw_page(rig.panel)
        got = [i for i, _ in seen]
        dup = {lb for i, lb in seen if got.count(i) > 1}
        assert not dup, f"conflicting ids {sorted(dup)}"
        cells = [lb for _, lb in seen if lb.startswith("##seq.") and lb.count(".") == 2
                 and lb.rsplit(".", 1)[1].isdigit() and "head" not in lb]
        assert len(cells) == 40
        assert len([lb for _, lb in seen if lb.endswith(".open")]) == len(rig.envs) - 1
        monkeypatch.undo()


def test_a_click_toggles_a_step_and_is_undoable(rig):
    u, settle = _undo(rig)
    try:
        assert ui_seq.toggle_step(rig.panel, rig.seq, 2, 4)
        settle()
        assert rig.seq.lanes[2].steps[4] == 1.0 and rig.reg["seq.3.5"].value
        assert u.undo() and rig.seq.lanes[2].steps[4] == 0.0
        assert u.redo() and rig.seq.lanes[2].steps[4] == 1.0
        frame(rig.panel)
    finally:
        undo.install(None)


def _cell_rects(monkeypatch):
    """Where each grid cell was drawn this frame: label → (x, y, w, h)."""
    rects: dict[str, tuple] = {}
    real = imgui.invisible_button

    def rec(label, size, *a, **k):
        p = imgui.get_cursor_screen_pos()
        rects[label] = (p.x, p.y, size.x, size.y)
        return real(label, size, *a, **k)
    monkeypatch.setattr(imgui, "invisible_button", rec)
    return rects


def _click(panel, x, y):
    io = imgui.get_io()
    io.add_mouse_pos_event(x, y)
    frame(panel)
    io.add_mouse_button_event(0, True)
    frame(panel)
    io.add_mouse_button_event(0, False)
    frame(panel)
    io.add_mouse_pos_event(-1, -1)
    frame(panel)


def test_a_mouse_click_on_a_cell_toggles_it(rig, monkeypatch):
    """The real road: a press and release over the cell, through imgui."""
    rects = _cell_rects(monkeypatch)
    frame(rig.panel)
    frame(rig.panel)
    x, y, w, h = rects["##seq.4.2"]
    _click(rig.panel, x + w / 2, y + h / 2)
    assert rig.seq.lanes[3].steps[1] == 1.0
    # a column past the length takes no click
    rig.reg["seq.length"].set(4)
    frame(rig.panel)
    x, y, w, h = rects["##seq.4.6"]
    _click(rig.panel, x + w / 2, y + h / 2)
    assert rig.seq.lanes[3].steps[5] == 0.0
    # a step number sets the length
    x, y, w, h = rects["##seq.head.7"]
    _click(rig.panel, x + w / 2, y + h / 2)
    assert rig.seq.length == 7


def test_columns_past_length_are_inert(rig):
    rig.reg["seq.length"].set(3)
    assert not ui_seq.toggle_step(rig.panel, rig.seq, 0, 3)
    assert not ui_seq.toggle_step(rig.panel, rig.seq, 0, 7)
    assert rig.seq.lanes[0].steps == [0.0] * 8
    assert ui_seq.toggle_step(rig.panel, rig.seq, 0, 2)
    assert rig.seq.lanes[0].steps[2] == 1.0
    # a step left lit past the length shows no playhead and stays lit
    rig.seq.lanes[0].steps[6] = 1.0
    rig.seq.playhead = 2
    assert ui_seq.cell_state(rig.seq, 0, 6) == (ui_seq.ON_S, False)
    frame(rig.panel)


def test_the_playhead_column_follows_the_sequencer(rig):
    seq = rig.seq
    seq.lanes[0].steps[3] = 1.0
    seq.lanes[1].steps[3] = 1.0
    seq.lanes[1].mute = True
    seq.playhead = None
    assert all(not ui_seq.cell_state(seq, li, si)[1] for li in range(5) for si in range(8))
    assert ui_seq.cell_state(seq, 0, 3) == (ui_seq.ON_S, False)
    for ph in range(8):
        seq.playhead = ph
        heads = {si for li in range(5) for si in range(8) if ui_seq.cell_state(seq, li, si)[1]}
        assert heads == {ph}
        frame(rig.panel)
    seq.playhead = 3
    assert ui_seq.cell_state(seq, 0, 3) == (ui_seq.PLAY_S, True)      # yellow
    assert ui_seq.cell_state(seq, 1, 3) == (ui_seq.MUTED_S, True)     # muted stays red
    assert ui_seq.cell_state(seq, 2, 3) == (ui_seq.OFF_S, True)
    # and it is the engine's playhead: a running step moves it
    seq.playhead = None
    rig.reg["seq.run"].set(True)
    seq.step(0.0, rig.clock, lambda *a: None)
    assert seq.playhead == 0 and ui_seq.cell_state(seq, 0, 0)[1]


def test_the_lane_selection_opens_its_envelope(rig):
    panel, seq, envs = rig.panel, rig.seq, rig.envs
    assert ui_seq.selected_lane(panel, seq) == 0
    assert ui_seq.open_env(panel, seq, envs) == 1
    ui_seq.select_lane(panel, 3)
    assert ui_seq.open_env(panel, seq, envs) == 4
    ui_seq.open_strip(panel, 2)
    assert ui_seq.open_env(panel, seq, envs) == 2
    rig.reg["seq.4.env"].set(5)
    ui_seq.select_lane(panel, 3)
    assert ui_seq.open_env(panel, seq, envs) == 5
    # a lane pointed at an envelope that is gone opens the first
    rig.reg["seq.4.env"].set(9)
    assert ui_seq.open_env(panel, seq, envs) == 1
    frame(panel)


def test_adding_and_removing_an_extra_env_is_undoable(rig):
    u, settle = _undo(rig)
    try:
        n = ui_seq.add_env(rig.panel, rig.envs)
        settle()
        assert n == 6 and rig.envs.ids() == [1, 2, 3, 4, 5, 6] and "env.6.decay" in rig.reg
        assert ui_seq.open_env(rig.panel, rig.seq, rig.envs) == 6
        frame(rig.panel)
        assert ui_seq.remove_env(rig.panel, rig.envs, 6)
        settle()
        assert rig.envs.ids() == [1, 2, 3, 4, 5] and "env.6.decay" not in rig.reg
        assert u.undo() and rig.envs.ids() == [1, 2, 3, 4, 5, 6]
        assert u.undo() and rig.envs.ids() == [1, 2, 3, 4, 5]
        assert u.redo() and rig.envs.ids() == [1, 2, 3, 4, 5, 6]
        frame(rig.panel)
    finally:
        undo.install(None)


def test_removing_a_lane_envelope_is_refused(rig):
    u, settle = _undo(rig)
    try:
        depth = len(u.stack)
        for n in envelope.LANE_ENVS:
            assert not ui_seq.remove_env(rig.panel, rig.envs, n)
        assert not ui_seq.remove_env(rig.panel, rig.envs, 12)     # no such envelope
        settle()
        assert rig.envs.ids() == [1, 2, 3, 4, 5] and len(u.stack) == depth
    finally:
        undo.install(None)


def test_add_is_refused_at_the_cap(rig):
    while rig.envs.can_add():
        rig.envs.add()
    assert len(rig.envs) == rig.envs.MAX
    assert ui_seq.add_env(rig.panel, rig.envs) is None
    frame(rig.panel)


def test_the_shape_follows_the_knobs(rig):
    env = rig.envs.voice(1)
    rig.reg["env.1.mode"].set(envelope.GATE)
    _a, h, _d, s, _r = ui_seq.segments(env)
    assert s > 0 and h == 0.0                      # hold at its floor is an ADSR
    rig.reg["env.1.mode"].set(envelope.ONE_SHOT)
    assert ui_seq.segments(env)[3] == 0.0          # one-shot: no plateau
    assert ui_seq.now_at(env) is None              # at rest: no dot
    env.fire(at=0.0)
    env.step(env.attack / 2)
    assert ui_seq.now_at(env) == pytest.approx(env.attack / 2, rel=1e-6)


def test_the_cells_use_the_apc_palette():
    from hyperspace import ui_desk
    from hyperspace.apc40 import GREEN, YELLOW
    for led, col in ((GREEN, ui_seq.GREEN), (YELLOW, ui_seq.YELLOW)):
        assert ui_desk._LED[led] == pytest.approx((col.x, col.y, col.z))
    assert ui_seq.fill(ui_seq.MUTED_S) is ui.RED and ui_seq.fill(ui_seq.OFF_S) is None
