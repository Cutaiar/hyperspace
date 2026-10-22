"""The LFO page (ui_lfo.py): draws with and without a clock, fits the
control window, and every widget has its own imgui id."""

from types import SimpleNamespace

import pytest
from imgui_bundle import imgui, implot

from hyperspace import lfo, tempo, ui_lfo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.app import CONTROL_SIZE
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.params import build_registry
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
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    lib.attach(reg)
    panel = Panel(control, audio, view, bank=lib.project, registry=reg, library=lib)
    panel.clock, panel.lfos = clock, lfos
    try:
        yield SimpleNamespace(panel=panel, reg=reg, clock=clock, lfos=lfos)
    finally:
        implot.destroy_context(pctx)
        imgui.destroy_context(ictx)


def frame(panel):
    panel.reg["ui.page"].set(PAGE_KEYS.index("lfo"))
    imgui.new_frame()
    panel.draw(1 / 60, 60.0)
    imgui.end_frame()


def test_the_page_draws_every_shape_and_sync(rig):
    panel, reg, lfos, clock = rig.panel, rig.reg, rig.lfos, rig.clock
    for k in range(len(lfo.SHAPES)):
        reg["lfo.1.shape"].set(k)
        reg["lfo.2.sync"].set(k % len(lfo.SYNCS))
        lfos.step(1 / 60, k / 60, clock)
        frame(panel)
    reg["lfo.3.depth"].set_value(0.0)
    frame(panel)


def test_the_page_says_so_without_a_clock(rig):
    rig.panel.clock = rig.panel.lfos = None
    frame(rig.panel)
    frame(rig.panel)


def test_the_page_fits_the_control_window(rig, monkeypatch):
    over = {}
    draw = Panel._page_lfo

    def measured(self, dt):
        draw(self, dt)
        over["lfo"] = imgui.get_scroll_max_y()
    monkeypatch.setattr(Panel, "_page_lfo", measured)
    for _ in range(3):
        frame(rig.panel)
    assert over["lfo"] == 0


def test_the_page_has_no_conflicting_ids(rig, monkeypatch):
    """Every widget its own imgui id. The two preset strips and the four
    strips reuse labels under push_id, so it is the resolved id (the label
    hashed with the id stack) that must be unique, not the label."""
    ids: list[tuple[int, str]] = []
    for fn in ("button", "checkbox", "slider_float", "slider_int", "combo",
               "invisible_button", "small_button"):
        real = getattr(imgui, fn)

        def rec(label, *a, _real=real, **k):
            ids.append((imgui.get_id(label), label))
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    imgui.new_frame()
    imgui.begin("page")
    ui_lfo.page(rig.panel, 1 / 60)
    imgui.end()
    imgui.end_frame()
    seen = [i for i, _ in ids]
    dup = {lb for i, lb in ids if seen.count(i) > 1}
    assert not dup, f"conflicting ids {sorted(dup)}"
    assert len([lb for _, lb in ids if lb.endswith(".reset")]) == 4


def test_the_lfos_are_offered_as_routing_sources(rig):
    """The ROUTING page's source combo lists whatever the router has labels
    for — lanes, then lfo, then the rest in the order they spoke (plan 27
    B2: `lane` and `lfo` are the built-ins, listed first; the registry
    orders the devices' schemes) — so LFO 1–4 can be routed."""
    from hyperspace import ui_routing
    from hyperspace.routing import Binding, Bindings, Router

    router = Router(rig.reg, Bindings([]))
    rig.panel.router = router
    before = ui_routing._sources(rig.panel, router)
    assert all(s.startswith("lane:") for s, _ in before)
    rig.lfos.publish(router)
    router.labels["hand"] = ["L x", "R x"]
    router.feed("ext", [0.0] * 3)
    srcs = ui_routing._sources(rig.panel, router)
    order = [s.split(":")[0] for s, _ in srcs]
    assert order == sorted(order, key=("lane", "lfo", "hand", "ext").index)
    assert [(s, lb) for s, lb in srcs if s.startswith("lfo:")] == [
        (f"lfo:{i}", f"lfo LFO {i + 1}") for i in range(4)]
    assert ("hand:1", "hand R x") in srcs and ("ext:2", "ext 2") in srcs
    # a row naming a scheme nobody feeds still shows it — up to the lane its
    # rows name (plan 27 B3: no fixed count for ext; the bridge publishes
    # its labels when it is on)
    r2 = Router(rig.reg, Bindings([Binding("ext:5", "view.bright", "push", 0.1)]))
    offered = ui_routing._sources(rig.panel, r2)
    assert ("ext:5", "ext 5") in offered and not any(s == "ext:6" for s, _ in offered)
    frame(rig.panel)


def test_the_buttons_fire_the_trigger_params(rig):
    """The chips are the trigger params: firing them does what a press would."""
    reg, clock, lfos = rig.reg, rig.clock, rig.lfos
    reg["lfo.1.sync"].set(lfo.SYNCS.index("1 bar"))
    clock.tick(2.0)
    reg["tempo.tap"].fire()
    clock.tick(2.5)
    reg["tempo.tap"].fire()
    assert clock.bpm == pytest.approx(120.0)
    clock.tick(3.3)
    lfos.step(1 / 60, 3.3, clock)
    assert lfos[0].x != 0.0
    reg["lfo.trigger"].fire()
    lfos.step(1 / 60, 3.3, clock)
    assert lfos[0].x == 0.0 and clock.t0 == 3.3
    frame(rig.panel)


# ---- N strips (plan 31 U) ----

def _bank(lfos, ids):
    """The bank holding exactly `ids`."""
    for n in list(lfos.ids()):
        if n not in ids:
            lfos.remove(n)
    for n in ids:
        if n not in lfos:
            lfos.add(n)
    assert lfos.ids() == sorted(ids)


def _record(monkeypatch, *fns):
    """The resolved ids and labels of every call to the imgui widgets `fns`, in order."""
    seen: list[tuple[int, str]] = []
    for fn in fns:
        real = getattr(imgui, fn)

        def rec(label, *a, _real=real, **k):
            seen.append((imgui.get_id(label), label))
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    return seen


def _draw_page(panel):
    imgui.new_frame()
    imgui.begin("page")
    ui_lfo.page(panel, 1 / 60)
    imgui.end()
    imgui.end_frame()


@pytest.mark.parametrize("ids", [[1, 2, 3, 4], [1, 2, 3, 4, 5, 6, 7], list(range(1, 17)),
                                 [1, 3, 9]])
def test_the_page_draws_n_strips_and_gaps(rig, monkeypatch, ids):
    """4, 7, 16 and a bank with gaps: the page draws, every widget its own
    id; at four or fewer every strip is full, above four exactly one is."""
    _bank(rig.lfos, ids)
    rig.lfos.step(1 / 60, 0.5, rig.clock)
    for _ in range(2):
        frame(rig.panel)
    seen = _record(monkeypatch, "button", "combo", "invisible_button", "arrow_button",
                   "slider_float", "slider_int", "checkbox", "small_button")
    _draw_page(rig.panel)
    got = [i for i, _ in seen]
    dup = {lb for i, lb in seen if got.count(i) > 1}
    assert not dup, f"conflicting ids {sorted(dup)}"
    resets = [lb for _, lb in seen if lb.endswith(".reset")]
    opens = [lb for _, lb in seen if lb.endswith(".open")]
    if len(ids) <= ui_lfo.FOLD_AT:
        assert len(resets) == len(ids) and not opens
    else:
        assert len(resets) == 1 and len(opens) == len(ids) - 1
        assert ui_lfo.selected(rig.panel, rig.lfos) == ids[0]


def test_four_lfos_do_not_fold_and_still_fit(rig, monkeypatch):
    """The default page is what it was: four full strips, no scroll."""
    assert rig.lfos.ids() == [1, 2, 3, 4]
    test_the_page_fits_the_control_window(rig, monkeypatch)


def test_sixteen_lfos_scroll_and_one_is_open(rig, monkeypatch):
    _bank(rig.lfos, list(range(1, 17)))
    ui_lfo.select(rig.panel, 9)
    over = {}
    draw = Panel._page_lfo

    def measured(self, dt):
        draw(self, dt)
        over["lfo"] = imgui.get_scroll_max_y()
    monkeypatch.setattr(Panel, "_page_lfo", measured)
    for _ in range(3):
        frame(rig.panel)
    assert over["lfo"] > 0                       # the page child scrolls
    assert ui_lfo.selected(rig.panel, rig.lfos) == 9


def test_the_selection_follows_the_bank(rig):
    """A removed open strip hands the open slot to the first; an added LFO
    opens; the selection is the Panel's, never the preset's."""
    _bank(rig.lfos, [1, 3, 5, 7, 9])
    assert ui_lfo.selected(rig.panel, rig.lfos) == 1
    ui_lfo.select(rig.panel, 7)
    assert ui_lfo.selected(rig.panel, rig.lfos) == 7
    ui_lfo.remove_lfo(rig.panel, rig.lfos, 7)
    assert ui_lfo.selected(rig.panel, rig.lfos) == 1
    n = ui_lfo.add_lfo(rig.panel, rig.lfos)
    assert n == 10 and ui_lfo.selected(rig.panel, rig.lfos) == 10
    frame(rig.panel)


def test_add_is_refused_at_the_cap(rig):
    _bank(rig.lfos, list(range(1, 17)))
    assert not rig.lfos.can_add()
    assert ui_lfo.add_lfo(rig.panel, rig.lfos) is None
    assert len(rig.lfos) == 16
    frame(rig.panel)                              # the disabled chip draws


def test_add_and_remove_through_the_chips_are_undoable(rig):
    """The chips' actions (add_lfo, remove_lfo) are one undo step each,
    and × asks nothing."""
    from hyperspace import undo
    from hyperspace.routing import Bindings

    u = undo.Undo(rig.reg, Bindings([]), banks=lambda: {"lfo": rig.lfos})
    undo.install(u)
    try:
        t = [0.0]

        def settle():
            for _ in range(3):
                t[0] += 1.0
                u.tick(t[0])
        settle()
        n = ui_lfo.add_lfo(rig.panel, rig.lfos)
        settle()
        assert n == 5 and rig.lfos.ids() == [1, 2, 3, 4, 5]
        ui_lfo.remove_lfo(rig.panel, rig.lfos, 2)
        settle()
        assert rig.lfos.ids() == [1, 3, 4, 5] and "lfo.2.rate" not in rig.reg
        assert u.undo() and rig.lfos.ids() == [1, 2, 3, 4, 5]
        assert u.undo() and rig.lfos.ids() == [1, 2, 3, 4] and "lfo.5.rate" not in rig.reg
        assert u.redo() and rig.lfos.ids() == [1, 2, 3, 4, 5]
        frame(rig.panel)
    finally:
        undo.install(None)
