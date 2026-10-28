"""The modulator bank (modbank.py, plan 31 B): voices with stable ids, the
LFOs as one of N. Ids are one past the highest and never compact, a gap
publishes NaN so a route from a removed voice goes dormant, a change of
membership rebuilds the patch through the registry's serial, and the
membership is the preset's and undo's."""

import ast
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperspace import lfo, modbank, modgraph, undo
from hyperspace.lfo import REST, SHAPES, LFOs, register
from hyperspace.params import Registry
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.tempo import Clock
from hyperspace.tempo import register as register_tempo

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


class Voice:
    def __init__(self):
        self.level, self.out, self.at = 0.25, 0.0, None

    def step(self, dt, t, clock):
        self.out = self.level
        return self.out


class Toy(modbank.Bank):
    SCHEME, LABEL, KEY = "toy", "Toy", "toys"
    DEFAULT = (1, 2)

    def make(self):
        return Voice()


def declare_toy(reg, n, v):
    reg.continuous(f"toy.{n}.level", f"Toy {n} level", lambda v=v: v.level,
                   lambda x, v=v: setattr(v, "level", float(x)), group="toy")


def rig(ids=None):
    reg = Registry()
    c = Clock(now=lambda: 0.0)
    lfos = LFOs(seed=1)
    register_tempo(reg, c)
    register(reg, lfos, c)
    if ids is not None:
        lfos.set(ids)
    return reg, c, lfos


# ---- the bank ----

def test_add_remove_next_id_and_the_cap():
    reg = Registry()
    bank = Toy()
    bank.bind(reg, declare_toy)
    assert bank.ids() == [1, 2] and "toy.2.level" in reg
    assert bank.next_id() == 3 and bank.add() == 3 and "toy.3.level" in reg
    assert bank.remove(2) and "toy.2.level" not in reg and bank.ids() == [1, 3]
    assert not bank.remove(2)
    assert bank.next_id() == 4                  # one past the highest, never the gap
    bank.remove(3)
    assert bank.next_id() == 4                  # the top id too: never reused this session
    with pytest.raises(ValueError):
        bank.add(1)                             # there already
    while bank.can_add():
        bank.add()
    assert len(bank) == modbank.MAX == lfo.MAX == 16
    with pytest.raises(ValueError):
        bank.add()


def test_parse_reads_a_files_membership():
    assert Toy.parse(None) == ([1, 2], [])
    ids, notes = Toy.parse([7, 3, 3, "x", True, 0, 1])
    assert ids == [1, 3, 7] and len(notes) == 4
    ids, notes = Toy.parse("nope")
    assert ids == [1, 2] and notes
    ids, notes = Toy.parse(list(range(1, 20)))
    assert ids == list(range(1, 17)) and notes


def test_a_gap_publishes_nan_and_an_empty_label():
    bank = Toy([1, 3])
    bank.step(1 / 60, 0.0, None)
    assert bank.outputs[0] == 0.25 and math.isnan(bank.outputs[1]) and bank.outputs[2] == 0.25
    assert bank.labels == ["Toy 1", "", "Toy 3"]
    with pytest.raises(IndexError):
        bank[1]                                 # lane 1 is the gap


def test_set_touches_only_what_differs():
    reg = Registry()
    bank = Toy([1, 2, 3])
    bank.bind(reg, declare_toy)
    keep = reg["toy.1.level"]
    bank.voice(1).level = 0.9
    bank.set([1, 3, 5])
    assert bank.ids() == [1, 3, 5] and reg["toy.1.level"] is keep
    assert bank.voice(1).level == 0.9 and bank.voice(5).level == 0.25


def test_modbank_imports_nothing_from_the_host():
    """A leaf, like lfo.py: the registry and the router are arguments."""
    for n in ast.walk(ast.parse((PKG / "modbank.py").read_text())):
        if isinstance(n, ast.ImportFrom):
            assert not n.level and not (n.module or "").startswith("hyperspace"), n.module
        elif isinstance(n, ast.Import):
            assert not any(a.name.startswith("hyperspace") for a in n.names)


def test_the_lfo_knobs_are_the_modgraphs():
    assert LFOs.KNOBS == modgraph.LFO_KNOBS


# ---- the LFOs as a bank ----

def test_removing_lfo_2_keeps_lfo_3_on_lfo_2():
    reg, c, lfos = rig()
    three = lfos.voice(3)
    lfos.remove(2)
    assert lfos.ids() == [1, 3, 4] and lfos[2] is three
    assert "lfo.2.depth" not in reg and "lfo.3.depth" in reg
    reg["lfo.3.depth"].set(0.4)
    assert three.depth == 0.4                   # the knob is still LFO 3's
    router = Router(reg, Bindings([Binding("lfo:2", "view.bright", "push", 1.0)]))
    router.use_lfos(lfos, c)
    nodes = router.modgraph.nodes
    assert "lfo:2" in nodes and "lfo:1" not in nodes and nodes["lfo:2"].kind == "lfo"
    assert ("bank", "lfo", 2) in router.__dict__["_plan"]
    assert lfos.add() == 5                      # one past the highest


def test_a_route_from_a_removed_lfo_goes_dormant():
    reg, c, lfos = rig()
    reg.continuous("view.bright", "bright", lambda: 0.0, lambda v: None)
    table = Bindings([Binding("lfo:1", "view.bright", "push", 1.0),
                      Binding("lfo:2", "lfo.4.depth", "push", 1.0)])
    router = Router(reg, table)
    router.use_lfos(lfos, c)
    lfos.voice(3).shape = SHAPES.index("square")
    lfos.remove(2)
    router.modulate(None, 1 / 60, now=0.1)
    assert math.isnan(router.feeds["lfo"][1])
    assert not reg["view.bright"].modulated     # NaN: no reading, the row lets go
    assert reg["lfo.4.depth"].modulated          # LFO 3 on lfo:2 still drives
    assert router.labels["lfo"] == ["LFO 1", "", "LFO 3", "LFO 4"]


def test_a_membership_change_rebuilds_the_patch():
    reg, c, lfos = rig()
    router = Router(reg, Bindings([]))
    router.use_lfos(lfos, c)
    before = router.modgraph
    serial = reg.serial
    lfos.add()
    assert reg.serial > serial                  # the registry says so…
    after = router.modgraph
    assert after is not before and "lfo:4" in after.nodes   # …and the patch follows
    assert router.modgraph is after                # cached until the next change


def test_an_lfo_owning_another_with_gaps_lands_the_same_frame():
    """LFO 3 (``lfo:2``) pushes LFO 7's depth; with LFO 2 and 4–6 gone,
    the pass still steps LFO 3, lands the depth, then steps LFO 7 — the
    same frame (decision 7)."""
    reg, c, lfos = rig([1, 3, 7])
    three, seven = lfos.voice(3), lfos.voice(7)
    three.shape, three.rate = SHAPES.index("sine"), 1.0
    seven.depth = 0.0
    seven.shape, seven.rate = SHAPES.index("square"), 1.0
    reg["lfo.7.depth"].set(0.0)
    router = Router(reg, Bindings([Binding("lfo:2", "lfo.7.depth", "push", 1.0)]))
    router.use_lfos(lfos, c)
    c.tick(0.25)
    router.modulate(None, 0.25, now=0.25)
    reg.apply()
    assert lfos.outputs[2] == pytest.approx(1.0)
    assert seven.depth == pytest.approx(0.5)
    assert lfos.outputs[6] == pytest.approx(REST + 0.25)    # read this frame, not the next
    assert len(lfos.outputs) == 7 and math.isnan(lfos.outputs[3])


# ---- undo ----

def test_undo_of_add_and_remove_restores_the_params_and_their_bases():
    reg, _, lfos = rig()
    u = undo.Undo(reg, Bindings([]), banks=lambda: {"lfo": lfos})
    undo.install(u)
    try:
        t = [0.0]

        def settle():
            for _ in range(3):
                t[0] += 1.0
                u.tick(t[0])

        reg["lfo.2.depth"].set(0.3)
        settle()
        undo.push("delete LFO 2")
        lfos.remove(2)
        settle()
        assert "lfo.2.depth" not in reg
        assert u.undo()
        assert lfos.ids() == [1, 2, 3, 4] and reg["lfo.2.depth"].base == pytest.approx(0.3)
        assert lfos.voice(2).depth == pytest.approx(0.3)
        assert u.redo() and lfos.ids() == [1, 3, 4]
        assert u.undo() and reg["lfo.2.depth"].base == pytest.approx(0.3)
        settle()
        undo.push("add LFO")
        n = lfos.add()
        reg[f"lfo.{n}.rate"].set(3.0)
        settle()
        assert u.undo() and lfos.ids() == [1, 2, 3, 4] and "lfo.5.rate" not in reg
        assert u.redo() and lfos.ids() == [1, 2, 3, 4, 5]
        assert reg["lfo.5.rate"].base == pytest.approx(3.0)
    finally:
        undo.install(None)


# ---- the preset ----

@pytest.fixture()
def app(tmp_path):
    from hyperspace import preset, routing, tempo
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.fx import FxState
    from hyperspace.library import Library
    from hyperspace.lookback import DreamState
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState

    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.project,
                         dream=DreamState(), fx=FxState())
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    lfos = LFOs()
    tempo.register(reg, clock)
    register(reg, lfos, clock)
    table = routing.Bindings.load(routing.bindings_path(tmp_path), legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    router = routing.Router(reg, table)
    router.use_lfos(lfos, clock)
    presets = preset.Presets(lib, reg, router)
    return SimpleNamespace(lib=lib, reg=reg, router=router, presets=presets, lfos=lfos)


def test_a_preset_without_the_key_loads_four_lfos(app):
    app.lfos.set([1, 3])
    doc = app.presets.document("old")
    assert doc["lfos"] == [1, 3]
    del doc["lfos"]                              # as a file from before plan 31 wrote it
    app.presets.load_doc(doc)
    assert app.lfos.ids() == [1, 2, 3, 4] and "lfo.2.depth" in app.reg
    assert "lfos" not in app.presets.document("again")   # the default writes no key


def test_a_preset_round_trips_with_gaps(app):
    app.lfos.set([1, 3, 7])
    app.reg["lfo.7.depth"].set(0.25)
    app.reg["lfo.3.sync"].set(2)
    doc = app.presets.document("gaps")
    assert doc["lfos"] == [1, 3, 7] and doc["values"]["lfo.7.depth"] == 0.25
    app.lfos.set([1, 2, 3, 4])                  # somewhere else entirely
    assert app.presets.load_doc(doc) == []       # every id known: none unknown
    assert app.lfos.ids() == [1, 3, 7]
    assert app.reg["lfo.7.depth"].value == pytest.approx(0.25)
    assert app.reg["lfo.3.sync"].value == 2
    assert app.presets.document("gaps")["values"] == doc["values"]
