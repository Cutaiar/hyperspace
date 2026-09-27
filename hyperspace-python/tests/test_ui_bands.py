"""The band editor and the routing matrix (WP5b).

The geometry first — fit_box, drag_edge, pooled, band_under are pure
and are checked against the analyzer's own f/q ↔ edges — then the
registry writes, then the headless harness (test_ui_shell's rig, with
an implot context) drawing the ANALYZER page at 1, 6 and 16 bands and
around add / remove, the ghost for a modulated centre, and the ROUTING
page with routes, a live lane, edits and the preset strip's actions.
A mouse can't be driven here, so the drag handlers' *effects* are what
the tests call.
"""

import json
import math

import numpy as np
import pytest
from imgui_bundle import imgui
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import routing, ui_bands, ui_routing
from hyperspace.analysis import FFT_SIZE
from hyperspace.analyzer import (
    F_HI,
    F_LO,
    HIST_DT,
    HIST_F,
    HIST_FLOOR,
    HIST_T,
    N_MAX,
    Q_HI,
    Q_LO,
    centre_q,
    edges,
)
from hyperspace.bands import CEIL
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.ui import PAGE_KEYS


@pytest.fixture()
def rig(shell_rig):  # noqa: F811 — pytest hands the shell's rig through under its name
    return shell_rig


# ---------------------------------------------------------------- geometry

def test_fit_box_is_the_frequency_extent_either_way_up():
    f, q = ui_bands.fit_box(60.0, 20.0)
    lo, hi = edges(f, q)
    assert lo == pytest.approx(20.0) and hi == pytest.approx(60.0)
    assert ui_bands.fit_box(20.0, 60.0) == (f, q)
    assert (f, q) == pytest.approx(centre_q(20.0, 60.0))


def test_fit_box_clamps_to_the_params_ranges():
    # the whole axis: wider than Q_LO allows, so the band is narrower than the box
    f, q = ui_bands.fit_box(20.0, 24000.0)
    assert q == Q_LO and F_LO <= f <= F_HI
    # a sliver (a drag with no height) pins Q at the top
    f, q = ui_bands.fit_box(1000.0, 1000.5)
    assert q == Q_HI and f == pytest.approx(1000.25, rel=1e-3)
    # off the axis: the centre clamps
    assert ui_bands.fit_box(1.0, 5.0)[0] == F_LO
    assert ui_bands.fit_box(30000.0, 40000.0)[0] == F_HI


def test_drag_edge_moves_one_edge_and_keeps_the_other():
    lo, hi = 100.0, 400.0
    f, q = ui_bands.drag_edge(lo, hi, "lo", 50.0)
    assert edges(f, q) == pytest.approx((50.0, 400.0))
    f, q = ui_bands.drag_edge(lo, hi, "hi", 800.0)
    assert edges(f, q) == pytest.approx((100.0, 800.0))
    # dragged through the other edge: the band never flips — it narrows to
    # MIN_OCT about the fixed edge, which Q_HI then widens a little
    f, q = ui_bands.drag_edge(lo, hi, "lo", 1000.0)
    assert q == Q_HI and abs(math.log2(f / 400.0)) < 0.05
    f, q = ui_bands.drag_edge(lo, hi, "hi", 10.0)
    assert q == Q_HI and abs(math.log2(f / 100.0)) < 0.05
    # a narrow-enough range that Q_HI allows keeps the fixed edge exactly
    f, q = ui_bands.drag_edge(lo, hi, "lo", 380.0)
    assert edges(f, q) == pytest.approx((380.0, 400.0))


def test_band_under_picks_the_narrowest():
    specs = [(20.0, 20000.0), (100.0, 400.0), (150.0, 300.0)]
    assert ui_bands.band_under(specs, 200.0) == 2
    assert ui_bands.band_under(specs, 120.0) == 1
    assert ui_bands.band_under(specs, 5000.0) == 0
    assert ui_bands.band_under(specs, 5.0) is None


def test_pooled_keeps_peaks_and_turns_the_map():
    spec = np.full((HIST_T, HIST_F), HIST_FLOOR, dtype=np.float32)
    spec[3, 7] = -10.0        # early in time, low in frequency
    spec[-1, -1] = -5.0       # now, at the top
    m = ui_bands.pooled(spec)
    assert m.shape == (HIST_F // 2, HIST_T // 2) and m.dtype == np.float32
    assert m.flags["C_CONTIGUOUS"]
    assert m[0, -1] == -5.0                         # top row = highest bin, last column = now
    assert m[HIST_F // 2 - 1 - 3, 1] == -10.0       # row 3 from the bottom, column 1
    assert (m == HIST_FLOOR).sum() == m.size - 2


def test_history_fills_from_a_fed_analyser(rig):
    """A tone lands in the ring at its bin — what the heat map shows."""
    chain = rig.chain
    sr = chain.an.sample_rate
    t = np.arange(FFT_SIZE) / sr
    chain.an.feed(0.5 * np.sin(2 * np.pi * 1000.0 * t))
    for _ in range(6):
        chain.step(HIST_DT)
    spec, freqs = chain.history()
    assert spec.shape == (HIST_T, HIST_F) and len(freqs) == HIST_F
    col = spec[-1]
    assert col.max() > -40 and abs(freqs[int(col.argmax())] - 1000) < 60
    assert spec[0].max() == HIST_FLOOR             # the ring is mostly unwritten


# ------------------------------------------------------- registry writes

def test_apply_fq_writes_through_the_registry(rig):
    reg, chain = rig.reg, rig.chain
    ui_bands.apply_fq(reg, 1, *ui_bands.fit_box(200.0, 800.0))
    assert chain.edges(1) == pytest.approx((200.0, 800.0))
    assert reg["band.1.f"].value == pytest.approx(400.0)
    # only the centre: q keeps
    q = chain.spec[1].q
    ui_bands.apply_fq(reg, 1, f=1000.0)
    assert chain.spec[1].f == 1000.0 and chain.spec[1].q == q
    # the params clamp
    ui_bands.apply_fq(reg, 1, f=1.0, q=99.0)
    assert (chain.spec[1].f, chain.spec[1].q) == (F_LO, Q_HI)


def test_handle_writes_land_on_the_base_while_modulated(rig):
    """A lane on band.0.f: the handle moves the base, the ghost the effective."""
    reg, chain = rig.reg, rig.chain
    pf = reg["band.0.f"]
    base = pf.base
    pf.modulate(0.2)
    reg.apply()
    assert pf.modulated and pf.value > base and pf.base == pytest.approx(base)
    ui_bands.apply_fq(reg, 0, f=100.0)
    pf.modulate(0.2)
    reg.apply()
    assert pf.base == pytest.approx(100.0, rel=1e-6) and pf.value > 100.0
    assert ui_bands._base_fq(reg, 0)[0] == pytest.approx(100.0, rel=1e-6)
    reg.apply()                                     # the lane lets go
    assert not pf.modulated and chain.spec[0].f == pytest.approx(100.0, rel=1e-6)


# ------------------------------------------------------------- the page

def test_editor_draws_at_every_band_count(rig):
    panel, control, chain = rig.panel, rig.panel.control, rig.chain
    frame(panel, "analyzer")
    assert chain.n == 6
    while chain.n > 1:
        control.remove_band()
        frame(panel)
    assert chain.n == 1
    frame(panel)
    while chain.n < N_MAX:
        control.add_band()
        frame(panel)
    assert chain.n == N_MAX and control.selb < N_MAX
    frame(panel)
    # the state the editor keeps is only the gesture and the colormap id
    st = ui_bands._state(panel)
    assert st["box"] is None and st["cmap"] >= 0
    assert ui_bands.HINT and ui_bands.PLOT_H > 0


def test_editor_add_remove_follow_the_registry(rig):
    panel, reg, chain = rig.panel, rig.reg, rig.chain
    frame(panel, "analyzer")
    reg["band.add"].fire()
    assert chain.n == 7 and "band.6.f" in reg
    frame(panel)
    reg["band.select"].set(6)
    reg["band.remove"].fire()
    assert chain.n == 6 and "band.6.f" not in reg
    frame(panel)
    panel.control.move_band(0, 5)
    frame(panel)


def test_modulated_centre_draws_a_ghost_in_the_editor(rig):
    panel, reg = rig.panel, rig.reg
    frame(panel, "analyzer")
    assert panel.ghosts == 0
    reg["band.0.f"].modulate(0.15)
    reg.apply()
    frame(panel)
    # the editor's hairline, and band.sel.f's fader (band 0 is selected)
    assert panel.ghosts == 2
    reg["band.select"].set(2)
    reg["band.0.f"].modulate(0.15)
    reg.apply()
    frame(panel)
    assert panel.ghosts == 1
    reg.apply()
    frame(panel)
    assert panel.ghosts == 0


# ------------------------------------------------------------- routing

def _with_router(rig, tmp_path):
    table = Bindings.factory(path=routing.bindings_path(tmp_path))
    rig.panel.router = Router(rig.reg, table)
    return rig.panel.router


def test_routing_page_draws_routes(rig, tmp_path):
    panel = rig.panel
    frame(panel, "routing")                     # no router: says so
    router = _with_router(rig, tmp_path)
    assert len(router.table.routes()) == 12
    frame(panel)
    frame(panel)
    assert ui_routing._state(panel)["current"] is None
    assert not ui_routing.dirty(panel, router)


def test_routing_page_live_lane_draws_ghost_and_bar(rig, tmp_path):
    panel, reg, chain = rig.panel, rig.reg, rig.chain
    # one route only: the factory table's replace rows would all hold their
    # targets (a replace at 0 is still a value), a ghost bar each
    router = panel.router = Router(reg, Bindings([Binding("lane:1", "view.bright", "push", 0.5)]))
    panel.audio.on = True
    chain.out[:] = 0.0
    chain.out[1] = CEIL * 0.5
    router.modulate(chain)
    reg.apply()
    bright = reg["view.bright"]
    assert bright.modulated
    assert ui_routing._live(panel, router, router.table.routes()[-1]) == pytest.approx(0.5)
    frame(panel, "routing")
    assert panel.ghosts == 1                    # the live bar's red hairline
    panel.audio.on = False
    assert ui_routing._live(panel, router, router.table.routes()[-1]) is None
    reg.apply()
    frame(panel)
    assert panel.ghosts == 0


def test_routing_add_and_delete(rig, tmp_path):
    panel, reg = rig.panel, rig.reg
    router = _with_router(rig, tmp_path)
    frame(panel, "routing")
    b = ui_routing.add_route(panel, "view.bright")
    assert b.source == "lane:0" and b.op == "push" and b.value == 0.5
    assert router.table.routes_to("view.bright") == [b]
    frame(panel)
    reg["band.select"].set(3)
    b2 = ui_routing.add_route(panel, "camera.zoom", depth=-0.25)
    assert b2.source == "lane:3" and b2.value == -0.25
    frame(panel)
    router.table.remove(b)
    assert not router.table.routes_to("view.bright") and b2 in router.table.routes()
    frame(panel)


def _on_disk(tmp_path):
    return Bindings.load(routing.bindings_path(tmp_path), legacy_midi=None)


def test_routing_page_edits_land_in_bindings_json(rig, tmp_path):
    """A route deleted on the page stays deleted: the page writes the table
    once it changes, not only when a learn happens to."""
    panel = rig.panel
    router = _with_router(rig, tmp_path)
    frame(panel, "routing")
    for b in list(router.table.routes()):
        router.table.remove(b)
    frame(panel)
    assert _on_disk(tmp_path).routes() == []
    b = ui_routing.add_route(panel, "view.bright")   # the context menu's add, page unseen
    assert [x.target for x in _on_disk(tmp_path).routes()] == ["view.bright"]
    b.value = -0.25
    frame(panel)
    assert _on_disk(tmp_path).routes()[0].value == -0.25


def test_the_routing_page_shows_the_referees_refusals(rig, tmp_path):
    """One performer per target: a preset's second owner is listed as
    dropped until the next edit; adding a route on an owned target says
    so in the strip (WP5 makes it the prompt) and leaves the table alone;
    a new push row has no rest of its own (it rests where its source
    does); one that has shows an "auto" chip."""
    panel = rig.panel
    router = _with_router(rig, tmp_path)
    router.table.set_routes([Binding("hand:7", "view.bright", "position"),
                             Binding("hand:1", "view.bright", "push", 0.5)])
    router.feed("hand", [0.5] * 20)
    router.labels["hand"] = [f"ax{i}" for i in range(12)]
    router.rests["hand"] = [0.5, 0.0] * 6 + [0.0] * 8
    router.gates["hand"] = [(14, "L ind")]
    frame(panel, "routing")
    assert [b.source for b, _ in router.table.dropped] == ["hand:1"]
    assert ui_routing.add_route(panel, "view.bright") is None            # owned: refused
    assert "already performed by hand 7 positions" in ui_routing._state(panel)["error"]
    assert [b.source for b in router.table.routes_to("view.bright")] == ["hand:7"]
    frame(panel)                                                           # draws the notice
    b = ui_routing.add_route(panel, "view.speed", source="hand:2")        # free: added
    assert (b.op, b.rest) == ("push", None) and router.table.dropped == []  # an edit clears
    assert router.rest_of(b.source) == 0.5                                 # what the row uses
    assert ui_routing.add_route(panel, "view.depth4", source="hand:1").rest is None
    b.rest = 0.1                                                           # the row's own: "auto" shows
    frame(panel)
    frame(panel)
    assert [x.target for x in _on_disk(tmp_path).routes()] == [
        "view.bright", "view.speed", "view.depth4"]
    # the row's checkbox goes through the referee too: waking a row onto
    # a taken target leaves it off and says why
    off = router.table.add(Binding("hand:3", "view.speed", "push", 0.2, enabled=False))
    with pytest.raises(routing.Owned):
        router.table.enable(off)
    assert not off.enabled
    frame(panel)


def test_route_a_lane_here_jumps_to_the_page(rig, tmp_path):
    panel, reg = rig.panel, rig.reg
    _with_router(rig, tmp_path)
    frame(panel, "view")
    p = reg["band.sel.atk"]                     # an alias: the route goes to the real param
    real = panel._real(p)
    ui_routing.add_route(panel, real.id)
    reg["ui.page"].set(PAGE_KEYS.index("routing"))
    assert panel.router.table.routes_to("band.0.atk")
    frame(panel)
    assert panel.page == PAGE_KEYS.index("routing")


def test_routing_presets_step_load_save(rig, tmp_path):
    panel = rig.panel
    router = _with_router(rig, tmp_path)
    frame(panel, "routing")
    listing = ui_routing.names(panel)
    assert listing == ["default", "hands-fx", "hands-pinch", "hands-play", "legacy6"]    # the factory exports
    # next from nothing: the first; prev wraps to the last
    assert ui_routing.step(panel, router, 1) == "default"
    assert ui_routing._state(panel)["current"] == "default"
    assert not ui_routing.dirty(panel, router)
    frame(panel)
    assert ui_routing.step(panel, router, -1) == "legacy6"
    assert rig.view.pattern_mod[0] == 0.0       # legacy6 lands its bases
    frame(panel)
    # an edit dirties; save-as writes the routes to the user folder and cleans
    router.table.add(Binding("lane:2", "view.bright", "push", 0.3))
    assert ui_routing.dirty(panel, router)
    frame(panel)
    ui_routing.save_as(panel, router, "My Routes")
    path = tmp_path / "bindings" / "my-routes.json"
    assert path.exists()
    doc = json.loads(path.read_text())
    assert doc["schema"] == routing.SCHEMA and len(doc["bindings"]) == 13
    assert all(b["op"] in routing.MOD_OPS for b in doc["bindings"])
    assert ui_routing._state(panel)["current"] == "my-routes"
    assert not ui_routing.dirty(panel, router)
    ui_routing.invalidate(panel)
    assert ui_routing.names(panel) == [
        "default", "hands-fx", "hands-pinch", "hands-play", "legacy6", "my-routes"]
    assert not routing.is_factory_preset("my-routes", tmp_path)
    frame(panel)
    # load a factory preset back: the user route goes, the inputs stay
    n_inputs = len(router.table.of(*routing.INPUT_SCHEMES))
    ui_routing.load(panel, router, "default")
    assert not router.table.routes_to("view.bright")
    assert len(router.table.of(*routing.INPUT_SCHEMES)) == n_inputs
    # and the user file round-trips
    ui_routing.load(panel, router, "my-routes")
    assert router.table.routes_to("view.bright")[0].value == 0.3
    frame(panel)
    # a bad name shows in the strip, never raises
    ui_routing.load(panel, router, "no-such")
    assert "no-such" in ui_routing._state(panel)["error"]
    frame(panel)


def test_routing_strip_name_field_draws(rig, tmp_path):
    from hyperspace import ui_presets

    panel = rig.panel
    router = _with_router(rig, tmp_path)
    frame(panel, "routing")
    ui_presets._begin_naming(panel, ui_routing.KEY, "seed")
    frame(panel)
    ui_presets._state(panel)["naming"] = None
    frame(panel)
    assert not ui_routing.dirty(panel, router)


def test_router_preset_files_and_save(tmp_path):
    """routing.py's side: the file listing and Router.load/save_preset."""
    from test_routing import rig as routing_rig

    r = routing_rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings.factory())
    assert routing.preset_names(tmp_path) == ["default", "hands-fx", "hands-pinch", "hands-play", "legacy6"]
    assert routing.is_factory_preset("legacy6", tmp_path)
    router.table.add(Binding("lane:0", "view.bright", "push", 0.5, enabled=False))
    path = router.save_preset("Show A", tmp_path)
    assert path == tmp_path / "bindings" / "show-a.json"
    saved = Bindings.from_json(json.loads(path.read_text()))
    assert len(saved.bindings) == 13 and not saved.bindings[-1].enabled
    assert saved.values is None
    assert router.load_preset("legacy6", tmp_path) == []
    assert len(router.table.routes()) == 12
    assert router.load_preset("show-a", tmp_path) == []
    assert len(router.table.routes()) == 13
    with pytest.raises(FileNotFoundError):
        router.load_preset("nope", tmp_path)
    assert imgui.get_version()
