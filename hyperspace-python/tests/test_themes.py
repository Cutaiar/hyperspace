"""Global theme save states: seeds, capture/apply round trip, persistence.

The bank lives in the project file now (library.py); these tests keep the
F1–F8 semantics pinned. Since plan 13 WP1 a slot is the performance part
only (params.PARTS): it carries the macros and never moves a session param.
"""

import json
from types import SimpleNamespace

from hyperspace import tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import SLOTS, Library, Project
from hyperspace.params import build_registry
from hyperspace.view import ViewState


def make(tmp_path):
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    lib = Library(tmp_path)
    reg = build_registry(view, control, audio, lib.project)
    lib.attach(reg)
    return lib.project, view, control, chain


def test_seeded_slots(tmp_path):
    pr, *_ = make(tmp_path)
    assert isinstance(pr, Project)
    assert len(pr.slots) == SLOTS
    assert pr.slots[0]["name"] == "BIG BLUE WAVE"
    assert pr.slots[1]["name"] == "EMBER ORBIT"
    # every slot ships seeded with a distinct house theme
    assert all(s is not None for s in pr.slots)
    assert len({s["name"] for s in pr.slots}) == SLOTS
    assert pr.active == -1


def test_load_seed_applies_the_view_and_leaves_the_scene(tmp_path):
    pr, view, control, chain = make(tmp_path)
    scene, atk = control.scene, chain.params[0].atk
    assert pr.slots[0]["values"]["scene.select"] == 2      # the seed still names one…
    pr.load_slot(0)
    assert view.shape == 17 and view.faces and view.pattern == 5
    # …but the analyzer is session (plan 13 §4, D9): a theme never moves it
    assert control.scene == scene and chain.params[0].atk == atk
    assert pr.active == 0
    # ids a theme doesn't mention in a group it does land on the defaults
    assert view.instances == 1 and view.pan == [0.0, 0.0]


def test_save_load_round_trip(tmp_path):
    pr, view, control, chain = make(tmp_path)
    view.shape, view.speed, view.zoom = 7, 1.23, 2.5
    view.planes = [True] * 6
    chain.params[2].atk, chain.gain, chain.trim = 0.111, 1.7, -6.0
    control.scene = 4
    pr.save_slot(3)

    assert "band.2.atk" not in pr.slots[3]["values"]   # a slot is the performance only
    pr.load_slot(1)  # stomp the look with the other seed
    assert view.shape != 7 and chain.gain == 1.7 and control.scene == 4   # session stays

    pr.load_slot(3)
    assert (view.shape, view.speed, view.zoom) == (7, 1.23, 2.5)
    assert view.planes == [True] * 6
    assert chain.params[2].atk == 0.111
    assert (chain.gain, chain.trim) == (1.7, -6.0)
    assert control.scene == 4


def test_rotation_phases_survive_a_switch(tmp_path):
    pr, view, *_ = make(tmp_path)
    view.ang = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    pr.save_slot(5)
    view.ang = [9.0] * 6
    pr.load_slot(5)
    assert view.ang == [9.0] * 6  # the spin keeps flowing, no snap


def test_slots_persist_across_sessions(tmp_path):
    pr, view, *_ = make(tmp_path)
    view.shape = 12
    pr.save_slot(6)
    # the bank rides in the user's default project, next to nothing else
    doc = json.loads((tmp_path / "projects" / "default.hyp.json").read_text())
    assert doc["schema"] == "hyperspace.project/1" and len(doc["bank"]) == SLOTS

    pr2, view2, _, _ = make(tmp_path)
    # saving over a seed keeps its name; the saved state replaces the seed
    assert pr2.slots[6]["name"] == "HEX ENGINE"
    assert "view.speed" in pr2.slots[6]["values"] and "band.2.atk" not in pr2.slots[6]["values"]
    pr2.load_slot(6)
    assert view2.shape == 12


def test_loaded_state_does_not_alias_the_slot(tmp_path):
    pr, view, *_ = make(tmp_path)
    pr.load_slot(1)
    view.planes[0] = not view.planes[0]
    before = dict(pr.slots[1]["values"])
    pr.load_slot(1)
    assert pr.slots[1]["values"] == before


def test_cycle_flips_through_saved_slots(tmp_path):
    pr, view, *_ = make(tmp_path)
    pr.cycle()
    assert pr.active == 0 and view.shape == 17  # first filled slot
    pr.cycle()
    assert pr.active == 1 and view.shape == 10
    for _ in range(SLOTS - 2):
        pr.cycle()
    assert pr.active == SLOTS - 1
    pr.cycle()
    assert pr.active == 0  # wraps at the end of the table
    pr.cycle(-1)
    assert pr.active == SLOTS - 1  # and backwards


def test_a_slot_with_unknown_ids_still_loads(tmp_path):
    pr, view, *_ = make(tmp_path)
    pr.slots[2] = {"name": "FUTURE", "values": {"view.shape": 5, "nebula.glow": 0.3}}
    pr.load_slot(2)
    assert view.shape == 5 and pr.active == 2
    assert "nebula.glow" in pr.lib.warning


def test_a_theme_slot_never_moves_the_tempo(tmp_path):
    """Plan 13 §4, D9: the clock is session. A slot that names tempo.bpm and
    scene.select (every house theme names a scene) keeps them in the file, and
    a load moves neither: a tapped BPM survives a theme change."""
    pr, view, control, _ = make(tmp_path)
    clock = tempo.Clock()
    tempo.register(pr.lib.reg, clock)
    pr.lib.reg["tempo.bpm"].set(100.0)
    scene = control.scene
    pr.slots[2] = {"name": "FAST", "values": {
        "view.shape": 5, "tempo.bpm": 140.0, "scene.select": (scene + 1) % 3}}
    pr.load_slot(2)
    assert view.shape == 5 and pr.active == 2
    assert clock.bpm == 100.0 and control.scene == scene
    assert pr.slots[2]["values"]["tempo.bpm"] == 140.0           # kept in the file
    assert pr.lib.warning == ""                                  # ignored, not unknown


def test_a_theme_slot_carries_the_macros(tmp_path):
    """The macros are performance state now: a slot saves and restores them."""
    pr, *_ = make(tmp_path)
    m = pr.lib.reg["macro.1"]
    m.set_value(0.3)
    pr.save_slot(4)
    assert pr.slots[4]["values"]["macro.1"] == 0.3
    m.set_value(0.8)
    pr.load_slot(4)
    assert m.value == 0.3
