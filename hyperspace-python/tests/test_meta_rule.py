"""The hard rule (the owner, 2026-11-04; register rows 743–745): no row of a
loadable patch may drive a meta controller param (`part_of(p) == "session"`). Every door
refuses it in words, a saved one drops with a note and the next save removes it,
and the meta controller's own rows stay.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import seed
from test_graph_groups import BREATH
from test_hands_orbit import GRAB, YAW, Run, closing, fist
from test_hands_orbit import app as orbit_app  # noqa: F401 — the fixture
from test_loadable import boot, put
from test_midi import cc, push, shift
from test_midi import rig as midi_rig  # noqa: F401 — the fixture
from test_pad_learn import ScriptedPad
from test_routing import rig as analyzer_rig
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import apc40, gamepad, graphview, headless, patches, ui_graph, ui_routing, undo
from hyperspace.bands import CEIL
from hyperspace.learn import PAIR_SPRING_WANT, Learn
from hyperspace.motion import Motion
from hyperspace.params import (
    META_PARTS,
    Kind,
    Param,
    Registry,
    chase_reaches,
    is_meta_id,
    part_of,
    part_of_id,
)
from hyperspace.routing import (
    MOD_OPS,
    TURN_OP,
    Binding,
    Bindings,
    Macro,
    Sub,
    act,
    factory_desk,
    is_meta_row,
    meta_refusal,
    meta_row_refusal,
)

ROOT = Path(__file__).resolve().parents[1]
WORDS = "master.gain is the meta controller's"


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)
    return shell_rig


def tool():
    spec = importlib.util.spec_from_file_location("meta_routes", ROOT / "tools" / "meta_routes.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["meta_routes"] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------- one predicate

def test_the_id_and_the_param_say_the_same_of_every_param(tmp_path):
    """Review of #371: the doors judge by id (a table has no registry), the panel
    by the param. Over a whole app's registry the two can never disagree."""
    app = headless.make_app(seed(tmp_path))
    assert not [p.id for p in app.reg if part_of(p) != part_of_id(p.id)]


@pytest.mark.parametrize("pid", ["edit.undo", "edit.redo", "app.restart", "seq.page",
                                 "seq.select"])
def test_the_five_with_a_foreign_prefix_are_refused_at_the_doors(pid):
    t = Bindings()
    with pytest.raises(ValueError, match="meta controller"):
        t.add(Binding("note:0:60", pid, "toggle", layer="preset"))
    assert t.set_desk([Binding("note:0:60", pid, "toggle")])
    assert not t.desk()


# ------------------------------------------------- the line, by layer alone

@pytest.mark.parametrize("row", [
    Binding("cc:0:14", "master.gain", "abs"),                  # invariant: the APC's MASTER
    Binding("cc:7:7", "master.trim", "abs", layer="global"),
    Binding("pad:A", "tempo.tap", "fire"),
    Binding("key:space", "audio.play", "toggle"),
])
def test_the_meta_controllers_own_rows_are_not_a_loadables(row):
    assert is_meta_row(row) and meta_row_refusal(row) is None
    assert Bindings().add(row) is row


@pytest.mark.parametrize("row", [
    *(Binding("hand:left.y", "master.gain", op, 0.375) for op in MOD_OPS),
    Binding("hand:left.y", "master.gain", "push", 0.375, enabled=False),
    Binding("cc:0:14", "master.gain", "abs", layer="preset"),
])
def test_a_loadables_rows_are_refused_at_the_one_door(row):
    assert not is_meta_row(row)
    assert WORDS in meta_row_refusal(row)
    t = Bindings()
    with pytest.raises(ValueError, match=WORDS):
        t.add(row)
    assert t.bindings == []


def test_every_factory_row_on_a_meta_param_is_the_meta_controllers():
    """The line is mechanical: the factory's rows on a meta param all pass by
    their layer, and the factory's patch layer holds none, with no id listed."""
    table = Bindings.factory()
    on_meta = [b for b in table.bindings if meta_refusal(b.target) is not None]
    assert any(b.target == "output.dim" for b in on_meta) and len(on_meta) > 40
    assert all(is_meta_row(b) and meta_row_refusal(b) is None for b in on_meta)
    assert not [b for b in factory_desk() if b.layer == "preset"
                and meta_refusal(b.target) is not None]


def test_the_masters_row_survives_a_load_that_drops_a_loadables(tmp_path):
    r = boot(tmp_path)
    table = r.router.table
    master = [b for b in table.bindings if b.target == "output.dim" and is_meta_row(b)]
    assert master
    put(tmp_path, "LEANS", routes=[
        {"source": "hand:left.y", "target": "output.dim", "op": "push", "value": 0.375}])
    r.loaded_patch.load("LEANS")
    assert all(any(x is b for x in table.bindings) for b in master)
    assert not table.routes_to("output.dim")


def test_a_loadables_row_moved_or_woken_onto_a_meta_param_is_refused():
    t = Bindings()
    b = t.add(Binding("hand:left.y", "view.bright", "push", 0.3))
    for call in (lambda: t.move_route(b, target="master.gain"),
                 lambda: t.replace_owner(b, target="master.gain"),
                 lambda: t.bind(Binding("cc:0:14", "master.gain", "abs", layer="preset"),
                                write=False)):
        with pytest.raises(ValueError, match=WORDS):
            call()
    assert b.target == "view.bright" and t.bindings == [b]        # nothing moved
    t.move_route(b, source="hand:left.x")                         # any other move is free
    assert b.source == "hand:left.x"


# ------------------------------------------------------------- at the load

def test_a_saved_row_drops_with_a_note_and_a_later_save_removes_it(tmp_path):
    """As a non-modulatable target does: the note, the file left alone, not
    dirty, and `master.dyn` off a pad stick goes the same way. The desk's and
    the macros' too. The next save writes the file without any of them."""
    r = boot(tmp_path)
    path = put(tmp_path, "LEANS", routes=[
        {"source": "hand:left.y", "target": "master.gain", "op": "push", "value": 0.375},
        {"source": "axis:RX", "target": "master.dyn", "op": "push", "value": 0.2},
        {"source": "hand:right.y", "target": "view.speed", "op": "push", "value": 0.45}],
        desk=[{"source": "cc:0:48", "target": "tempo.bpm", "op": "abs"},
              {"source": "cc:0:49", "target": "view.bright", "op": "abs"}],
        macros={"macro.1": {"subs": [
            {"depth": {"source": "hand:left.y", "target": "master.gain"}, "from": 0.0, "to": 1.0},
            {"base": "view.bright", "from": 0.0, "to": 0.5}]}})
    before = path.read_bytes()
    r.loaded_patch.load("LEANS")
    table, notes = r.router.table, r.loaded_patch.notes
    assert any(n.startswith("dropped hand:left.y → master.gain: " + WORDS) for n in notes)
    assert any(n.startswith("dropped axis:RX → master.dyn: master.dyn is") for n in notes)
    assert any(n.startswith("dropped cc:0:48 → tempo.bpm: tempo.bpm is") for n in notes)
    assert any("depth subscriber on hand:left.y → master.gain" in n for n in notes)
    assert [b.target for b in table.routes()] == ["view.speed"]
    assert [b.target for b in table.desk()] == ["view.bright"]
    assert path.read_bytes() == before and not r.lib.is_dirty("loadable")
    r.lib.save_as("loadable", "LEANS")
    doc = json.loads(path.read_text())
    assert [x["target"] for x in doc["routes"]] == ["view.speed"]
    assert [x["target"] for x in doc["desk"]] == ["view.bright"]
    assert doc["macros"]["macro.1"]["subs"] == [{"base": "view.bright", "from": 0.0, "to": 0.5}]
    r.loaded_patch.load("LEANS")
    assert not [n for n in r.loaded_patch.notes if "meta controller" in n]


def test_no_corpus_file_holds_a_row_on_a_meta_param():
    """party-tumble's `hand:left.y → master.gain` was the only one, removed."""
    t = tool()
    for kind in ("loadable", "patches"):
        assert t.scan(ROOT / "tests" / "corpus" / kind)[1] == [], kind


def test_party_tumble_keeps_its_other_rows_and_its_scale():
    """A `scale` reads a meta param and never moves it (row 18 (a)): it stays."""
    doc = json.loads((ROOT / "tests/corpus/loadable/party-tumble.json").read_text())
    assert not [r for r in doc["routes"] if r["target"] == "master.gain"]
    assert sum(r.get("scale") == "master.gain" for r in doc["routes"]) == 6
    assert Bindings().add(Binding("lane:0", "rot.rate.XY", "push", 0.1, scale="master.gain"))


# ---------------------------------------------------------------- at Learn

def test_a_hand_or_a_stick_learn_on_a_meta_param_is_refused_in_words(tmp_path):
    r = boot(tmp_path)
    table = r.router.table
    lrn = Learn(r.reg, table)
    for source in ("hand:left.y", "axis:RX"):
        lrn.arm("master.gain")
        lrn.learn_source(source)
        assert lrn.refused and WORDS in lrn.last and lrn.learning is None
        assert lrn.pending is None and not table.routes_to("master.gain")


def test_a_desk_learn_on_a_meta_param_ends_and_a_pad_button_still_lands(tmp_path):
    """The desk's patch layer is refused, wherever the control. A pad button is
    the meta controller's own row, which stays allowed: the learn it answers
    was armed bare, so the refusal leaves it armed for that."""
    r = boot(tmp_path)
    table = r.router.table
    lrn = Learn(r.reg, table)
    rows = list(table.bindings)
    lrn.arm("master.trim", "desk")
    assert lrn.learn_control("cc:3:16") is False
    assert lrn.refused and "master.trim is the meta controller's" in lrn.last
    assert lrn.learning is None and table.bindings == rows
    lrn.arm("master.trim")
    assert lrn.learn_control("cc:3:16") is False and lrn.learning == "master.trim"
    assert lrn.learn_pad_button("pad:A") is True
    assert any(b.source == "pad:A" and b.target == "master.trim" for b in table.bindings)


def test_a_picked_control_is_refused_on_a_meta_param_and_stays_picked(tmp_path):
    r = boot(tmp_path)
    lrn = Learn(r.reg, r.router.table)
    lrn.pick("cc:3:16")
    assert lrn.map_picked("master.trim") is False
    assert lrn.refused and "master.trim is the meta controller's" in lrn.last
    assert lrn.control == "cc:3:16" and lrn.learning is None


def test_a_row_a_hot_reload_left_is_not_saved(tmp_path):
    """Review of #371: the rule holds on the way in, so a row already in the
    live table (a hot reload) must not be written back by a save."""
    r = boot(tmp_path)
    table = r.router.table
    table.bindings.append(Binding("hand:left.y", "master.gain", "push", 0.375))
    table.bindings.append(Binding("cc:3:16", "tempo.bpm", "abs", layer="preset"))
    doc = r.loaded_patch.document("LEFT")
    assert not [x for x in doc["routes"] if x["target"] == "master.gain"]
    assert not [x for x in doc["desk"] if x["target"] == "tempo.bpm"]


def test_stick_drift_never_ends_a_learn_a_button_can_land(tmp_path):
    """Review of #371: Learn pad on a meta param waits for a button, so the
    adapters ask `routable` before reading an axis."""
    r = boot(tmp_path)
    lrn = Learn(r.reg, r.router.table)
    assert lrn.routable(r.reg["view.bright"])
    assert not lrn.routable(r.reg["master.gain"]) and not lrn.routable(None)
    assert not lrn.routable(r.reg["ghost.guide"])                 # not modulatable
    pad = ScriptedPad()
    pad.frame()
    lrn.arm("master.gain", "pad")
    pad.frame(axes=[1.0, 0.0, 0.0, 0.0, -1.0, -1.0])              # a stick, well past drift
    gamepad.learn_from(pad, lrn)
    assert lrn.learning == "master.gain" and not lrn.refused
    pad.frame(held={gamepad.A}, axes=[1.0, 0.0, 0.0, 0.0, -1.0, -1.0])
    assert gamepad.learn_from(pad, lrn) is True
    assert any(b.source == "pad:A" and b.target == "master.gain" for b in lrn.table.bindings)


def test_a_drag_from_an_invariant_control_says_invariant_not_the_rule(rig):
    """Review of #371: a row on an invariant control is the meta controller's, so
    the rule's words would say the opposite of the line."""
    table = rig.router.table
    view = graphview.build(table, rig.reg, rig.router, None, None, None)
    e = graphview.Edit(table, rig.reg, rig.router, view)
    fader = next(b.source for b in table.invariant_rows() if b.target == "output.dim")
    why = e._value_refusal(f"out:{fader}", "base:tempo.bpm")
    assert why == f"{fader} is invariant (the meta controller's)"
    lrn = Learn(rig.reg, table)
    lrn.arm("tempo.bpm", "desk")
    assert lrn.learn_control(fader) is False
    assert "invariant" in lrn.last and lrn.learning == "tempo.bpm"


# ------------------------------------------------------------- the pickers

def test_routing_and_the_desk_combo_offer_no_meta_param(rig):
    panel, reg = rig.panel, rig.reg
    for offered in (ui_routing._targets(panel), ui_routing._desk_targets(panel)):
        assert offered and not [p for p in offered if part_of(p) == "shared_meta"]
    gain = reg["master.gain"]
    assert not ui_routing.route_target(gain) and not ui_routing.desk_target(gain)
    assert ui_routing.pad_target(gain)
    assert ui_routing.route_target(reg["view.bright"]) and ui_routing.desk_target(reg["view.bright"])
    assert not hasattr(ui_routing, "SESSION_MARK") and not hasattr(ui_routing, "SESSION_TIP")


def test_route_a_lane_here_says_why_on_a_meta_param(rig, monkeypatch):
    panel, reg = rig.panel, rig.reg
    seen, items = [], []
    monkeypatch.setattr(ui_routing.imgui, "text_disabled", seen.append)
    monkeypatch.setattr(ui_routing.imgui, "menu_item_simple",
                        lambda label, *a, **k: items.append(label) or False)
    ui_routing.ctx_item(panel, reg["master.gain"])
    assert seen == [ui_routing.META_LINE] and items == []
    seen.clear()
    ui_routing.ctx_item(panel, reg["view.bright"])
    assert seen == [] and items == ["Route a lane here…"]


def test_add_route_says_why_and_lands_nothing(rig):
    panel = rig.panel
    table = ui_routing.router_of(panel).table
    assert ui_routing.add_route(panel, "master.gain") is None
    assert not table.routes_to("master.gain")
    assert WORDS in ui_routing._state(panel)["error"]


def test_route_from_offers_no_lfo_or_envelope_or_macro_on_a_meta_param(rig):
    panel, reg = rig.panel, rig.reg
    assert ui_graph.route_from_items(panel, reg["master.gain"]) is None
    assert ui_graph.route_from_items(panel, reg["view.bright"])


def test_a_graph_cable_onto_a_meta_param_is_refused_in_words(rig):
    table = rig.router.table
    view = graphview.build(table, rig.reg, rig.router, None, None, None)
    e = graphview.Edit(table, rig.reg, rig.router, view)
    assert e._value_refusal("out:hand:left.y", "mod:master.gain").startswith(WORDS)
    assert e._value_refusal("out:cc:3:16", "base:master.gain").startswith(WORDS)
    assert e._value_refusal("out:hand:left.y", "mod:view.bright") is None


def test_the_graph_lists_no_mod_port_for_a_meta_param_but_a_meta_row_stands(rig):
    """A meta param gets no stub of its own, and a row of the meta controller's
    still draws: it is not a loadable patch's."""
    table = rig.router.table
    table.set_routes([])
    table.bindings = [b for b in table.bindings if b.target != "tempo.bpm"]
    view = graphview.build(table, rig.reg, rig.router, None, None, None)
    ports = {p.id for n in view.nodes for p in n.ports}
    assert "param:view.bright" in ports and "param:tempo.bpm" not in ports
    assert any(b.target == "output.dim" for b in table.bindings)
    assert "param:output.dim" in ports


def test_a_route_end_moved_onto_a_meta_param_is_refused(rig):
    table = rig.router.table
    table.set_routes([])
    b = table.add(Binding("hand:left.y", "view.bright", "push", 0.3))
    view = graphview.build(table, rig.reg, rig.router, None, None, None)
    e = graphview.Edit(table, rig.reg, rig.router, view)
    res = e.move("mod:view.bright", "mod:master.gain")
    assert isinstance(res, graphview.Refusal) and WORDS in res
    assert b.target == "view.bright"


# ------------------------------------------------- the flag says what is true

def _lanes(n=64):
    """What `Router.modulate` reads of an analyzer: every lane at its ceiling."""
    return SimpleNamespace(lanes=np.full(n, CEIL))


def test_no_meta_param_says_a_lane_may_drive_it(rig):
    """Row 775: over the whole panel's registry, by the one rule and no list of ids.
    §9 counted 102 that said otherwise on a 6-band rig, 89 shared and 13 per deck."""
    reg = rig.reg
    meta = [p for p in reg if part_of(p) in META_PARTS]
    assert len(meta) > 102 and not [p.id for p in meta if p.modulatable]
    for pid in ("master.gain", "master.dyn", "master.trim", "band.0.f", "band.0.curve",
                "band.reset", "tempo.bpm", "tempo.nudge", "output.bg", "output.alpha",
                "scene.select", "scene.reset_all", "audio.mic", "preset.load.0", "preset.next"):
        assert is_meta_id(pid) and not reg[pid].modulatable, pid
    assert reg["view.bright"].modulatable and reg["view.speed"].modulatable


def test_a_declaration_cannot_say_otherwise():
    say = {"kind": Kind.CONTINUOUS, "modulatable": True}
    assert not Param("master.new", "New", group="master", **say).modulatable
    assert Param("view.new", "New", group="view", **say).modulatable
    # a group of the patch's with one key of the meta controller's goes by its part
    assert not Param("ghost.mirror", "Mirror", group="ghost", **say).modulatable
    # the id alone says so, as it does at the doors: no group, or another's
    assert not Param("master.x", "X", group="view", **say).modulatable
    assert not Param("tempo.foo", "Foo", group="", **say).modulatable
    assert not Registry().continuous("tempo.foo", "Foo", lambda: 0.0, lambda v: None).modulatable


def test_the_flag_changes_nothing_a_file_holds(rig):
    """Nothing saved moves here: the saved half of row 776 waits for the migration, so
    the same ids stay saved, those it will stop saving or move among them."""
    reg = rig.reg
    held = reg.snapshot(part="shared_meta")
    for pid in ("master.gain", "band.0.post", "tempo.bpm", "output.bg",
                "output.alpha", "scene.select"):
        assert reg[pid].persist and pid in held, pid
    assert not reg["tempo.nudge"].persist and "tempo.nudge" not in held    # (plan 58 §8)


# (the rows act: each is the meta controller's, on a real table and a real adapter)

@pytest.mark.parametrize("pid", ["master.gain", "master.dyn", "master.trim", "band.0.post",
                                 "band.0.f", "tempo.bpm", "tempo.nudge", "output.bg"])
def test_a_meta_desk_row_still_moves_its_param(midi_rig, pid):  # noqa: F811
    """How a person plays the meta controller: a global-layer fader sets the param, with
    no lane and no `modulate` in the way."""
    r = midi_rig
    p = r.reg[pid]
    assert not p.modulatable
    r.midi.table.add(Binding("cc:7:99", pid, "abs", layer="global", pickup=False))
    r.midi.table.set_layer("global")
    for v in (0, 127, 64):
        push(r, cc(99, v, channel=7))
        assert p.norm == pytest.approx(v / 127, abs=0.01), (pid, v)
    assert not p.modulated                  # set, not held: its base is the value


def test_the_factorys_shift_faders_still_ride_the_band_and_the_master(midi_rig):  # noqa: F811
    """The APC itself, nothing added: SHIFT up, S1 is `band.0.post`, S7 `master.dyn`,
    S8 `master.trim`, each caught at its own value, then moved."""
    r = midi_rig
    shift(r)
    for channel, pid in ((0, "band.0.post"), (6, "master.dyn"), (7, "master.trim")):
        p = r.reg[pid]
        here = round(p.norm * 127)
        to = here + 5 if here < 100 else here - 5
        push(r, cc(apc40.CC_FADER, here, channel=channel),
             cc(apc40.CC_FADER, to, channel=channel))
        assert p.norm == pytest.approx(to / 127, abs=0.02), pid


@pytest.mark.parametrize("row", [
    Binding("pad:A", "output.passthrough", "toggle"),
    Binding("pad:A", "band.0.curve", "step", 1.0),
    Binding("key:b", "band.0.fn", "step", 1.0),
    Binding("pad:A", "scene.select", "step", 1.0),
    Binding("pad:A", "tempo.bpm", "step", 1.0),
])
def test_a_key_or_a_pad_button_still_lands_on_a_meta_param(rig, row):
    p = rig.reg[row.target]
    was = p.value
    assert Bindings().add(row) is row
    act(rig.reg, row)
    assert p.value != was, row.target


def test_a_pad_button_still_fires_a_meta_trigger(rig):
    """`preset.*` and `band.reset`: a press is a person's, with the flag off."""
    fired = []
    p = rig.reg.trigger("band.poke", "Poke", lambda: fired.append(1), group="band")
    assert not p.modulatable
    act(rig.reg, Binding("pad:A", p.id, "fire"))
    assert fired == [1]


@pytest.mark.parametrize("op", ["push", "position"])
def test_a_row_past_every_door_moves_no_meta_param(tmp_path, op):
    """The one thing the flag changes: a performer row already in a live table (a hot
    reload) used to act until a save dropped it. Now it sits dormant and the page says
    so (`ui_routing.undriven_words`, the graph's `off`). A turn row has its own test."""
    r = boot(tmp_path)
    p = r.reg["master.gain"]
    p.set_norm(0.5)
    r.router.table.bindings.append(Binding("lane:0", "master.gain", op, 1.0))
    for _ in range(2):
        r.router.modulate(_lanes())
        r.reg.apply()
    assert p.norm == pytest.approx(0.5) and not p.modulated


def test_a_turn_row_past_every_door_turns_no_meta_param(orbit_app, tmp_path):  # noqa: F811
    """A real room lane and a closed clutch, which turn a patch's param through the
    same script: only the flag stops the row on `master.gain`."""
    gain, bright = orbit_app.reg["master.gain"], orbit_app.reg["view.bright"]
    gain.set_norm(0.5)
    bright.set_norm(0.5)
    for pid in ("master.gain", "view.bright"):
        orbit_app.table.bindings.append(Binding(YAW, pid, TURN_OP, when=GRAB))
    Run(orbit_app, tmp_path, closing() + [fist(yaw=float(k)) for k in range(31)],
        target="master.gain")
    assert bright.norm > 0.5                                # the script does turn
    assert gain.norm == pytest.approx(0.5)


def test_a_dormant_row_does_no_work_and_a_live_one_keeps_its_feel(tmp_path):
    """Checked once, right after the target is found: a feel on a dormant row keeps no
    follower, and on a live row it does."""
    r = boot(tmp_path)
    table = r.router.table
    table.set_routes([])
    feel = Motion("follow", atk=0.2, rel=0.2)
    table.bindings.append(Binding("lane:0", "master.gain", "push", 1.0, motion=feel))
    r.router.modulate(_lanes())
    r.reg.apply()
    assert not r.router.__dict__.get("_movers")
    table.add(Binding("lane:0", "view.bright", "push", 0.5, motion=feel))
    r.router.modulate(_lanes())
    r.reg.apply()
    assert [k[1] for k in r.router.__dict__["_movers"]] == ["view.bright"]


def test_a_row_standing_on_a_meta_param_is_dormant_in_the_rules_words(tmp_path):
    r = boot(tmp_path)
    said = ui_routing.undriven_words(r.reg["master.gain"])
    assert WORDS in said and said.endswith("the row is dormant") and "modulatable" not in said
    said = ui_routing.undriven_words(r.reg["ghost.guide"])
    assert said == "ghost.guide is not modulatable — the row is dormant"


# (the doors that ask the flag: the rule's words come first at each, as before)

def test_learn_keeps_the_rules_words_and_not_the_flags(tmp_path):
    """`learn.py` asks `meta_refusal` before the flag: flipped, a person reads what they
    read before, the rule, never "not modulatable". A patch param's flag has its own."""
    r = boot(tmp_path)
    lrn = Learn(r.reg, r.router.table)
    for pid, source in (("master.gain", "hand:left.y"), ("band.0.post", "axis:RX"),
                        ("preset.next", "hand:left.y")):
        lrn.arm(pid)
        lrn.learn_source(source)
        assert lrn.refused and f"{pid} is the meta controller's" in lrn.last, pid
        assert "not modulatable" not in lrn.last
    lrn.arm("ghost.guide")
    lrn.learn_source("hand:left.y")
    assert "can't follow a hand (not modulatable)" in lrn.last


def test_learn_pair_spring_is_not_offered_and_still_refuses_in_words(tmp_path):
    """`ui.py`'s "Learn pair (spring)" sits inside `_desk_target`, False on every meta
    param, so the flag is never read there and the menu is as it was. A learn armed for
    it anyway ends at the rule, not the flag."""
    r = boot(tmp_path)
    for pid in ("master.gain", "band.0.post", "tempo.bpm"):
        assert not ui_routing.desk_target(r.reg[pid]) and ui_routing.pad_target(r.reg[pid])
    lrn = Learn(r.reg, r.router.table)
    lrn.arm("master.gain", PAIR_SPRING_WANT)
    assert lrn.learn_pair("pair:UP/DOWN")
    assert lrn.refused and WORDS in lrn.last
    assert not r.router.table.routes_to("master.gain")


def test_the_graph_says_the_rule_not_the_flag(rig):
    table = rig.router.table
    view = graphview.build(table, rig.reg, rig.router, None, None, None)
    e = graphview.Edit(table, rig.reg, rig.router, view)
    for pid in ("band.0.post", "master.dyn", "tempo.nudge"):
        why = e._value_refusal("out:hand:left.y", f"mod:{pid}")
        assert why.startswith(f"{pid} is the meta controller's"), why


def test_a_patch_params_position_row_and_chase_read_as_before(tmp_path):
    """The flag only moved on meta params: `chase_reaches` never took one, and a
    position row on a patch's fader still lands its value."""
    r = boot(tmp_path)
    bright = r.reg["view.bright"]
    assert chase_reaches(bright) and not chase_reaches(r.reg["master.gain"])
    r.router.table.set_routes([])
    r.router.table.add(Binding("lane:0", "view.bright", "position", 0.5))
    r.router.modulate(_lanes())
    r.reg.apply()
    assert bright.modulated and bright._norm_of(bright.value) == pytest.approx(0.5)


# (what must not change: reading. A patch may read the meta controller)

def test_a_patch_row_may_still_read_master_gain_as_its_scale(tmp_path):
    """A scale reads and never writes: 457 saved rows do this."""
    r = boot(tmp_path)
    gain, bright = r.reg["master.gain"], r.reg["view.bright"]
    bright.set_norm(0.25)
    table = r.router.table
    table.set_routes([])
    table.add(Binding("lane:0", "view.bright", "push", 0.5, rest=0.0, scale="master.gain"))
    moved = {}
    for at in (0.0, 1.0):
        gain.set(at)
        r.router.modulate(_lanes())
        r.reg.apply()
        moved[at] = bright._norm_of(bright.value)
    assert moved[0.0] == pytest.approx(0.25) and moved[1.0] == pytest.approx(0.75)
    assert gain.value == 1.0 and not gain.modulated


def test_a_saved_scale_on_a_meta_param_loads(tmp_path):
    """`party-tumble`'s six rows, through a real load: the rule is on a row's target,
    and a row's source or scale is not touched."""
    r = boot(tmp_path)
    r.loaded_patch.load("party-tumble")
    assert sum(b.scale == "master.gain" for b in r.router.table.routes()) == 6
    assert not [n for n in r.loaded_patch.notes if "meta controller" in n]


def test_the_analyzers_lanes_still_read_its_bands():
    """A lane comes out of `band.*` as ever: what a person sets there reaches the chain a
    route reads, and more post-drive makes more lane, with the flag off."""
    tone = np.sin(2 * np.pi * 60.0 * np.arange(800) / 48_000.0).astype(np.float32)
    out = {}
    for at in (0.5, 1.5):
        r = analyzer_rig()
        post = r.reg["band.0.post"]
        assert not post.modulatable
        post.set(at)
        assert r.chain.params[0].post == pytest.approx(at)
        for _ in range(40):
            r.chain.an.feed(tone)
            lanes = r.chain.step(1 / 60)
        out[at] = float(lanes[0])
    assert out[1.5] > out[0.5] > 0.0


# ----------------------------------------------------------- macros, modifiers

def test_macro_base_and_depth_subscribers_on_a_meta_param_are_dropped():
    """Decided: both, at `set_macros`. A base already was (D9); a depth has no
    route to scale. A depth on a loadable patch's route stays."""
    t = Bindings()
    notes = t.set_macros({"macro.1": {"subs": [
        {"base": "master.gain"},
        {"depth": {"source": "hand:1", "target": "master.gain"}},
        {"depth": {"source": "hand:1", "target": "view.bright"}}]}})
    assert len(notes) == 2 and any("depth subscriber" in n for n in notes)
    assert t.macros["macro.1"].subs == [Sub(depth=("hand:1", "view.bright"))]
    assert isinstance(t.macros["macro.1"], Macro)


def test_a_modifier_has_no_target_its_route_is_refused(tmp_path):
    """Decided: a modifier reads lanes and writes none; what it drives is a
    route off its lane, and that route is refused. It may read anything."""
    r = boot(tmp_path)
    table = r.router.table
    m = table.add_modifier("scale", ("hand:left.y",), r.reg)
    with pytest.raises(ValueError, match=WORDS):
        table.add(Binding(m.address, "master.gain", "push", 0.3))


# ----------------------------------------------------------------- patches

def _with(**more):
    doc = copy.deepcopy(BREATH)
    for k, v in more.items():
        doc[k] = doc[k] + v if isinstance(doc[k], list) else {**doc[k], **v}
    return doc


def test_a_patch_naming_a_meta_param_is_refused_by_check_in_words():
    """Decided: check refuses the file, whole, naming the row, as it does any
    other row a patch may not hold. tools/meta_routes.py lists it for the owner."""
    assert patches.check(BREATH) == []
    route = {"source": "lfo:0", "target": "master.gain", "op": "push", "value": 0.2}
    assert any(WORDS in w for w in patches.check(_with(routes=[route])))
    sub = {"macro.3": {"subs": [{"base": "master.gain"}]}}
    assert any(WORDS in w for w in patches.check(_with(macros=sub)))
    sub = {"macro.3": {"subs": [{"depth": {"source": "lfo:0", "target": "master.gain"}}]}}
    assert any(WORDS in w for w in patches.check(_with(macros=sub)))
    desk = {"source": "lfo:0", "target": "tempo.bpm", "op": "abs"}
    assert any("tempo.bpm is the meta controller's" in w for w in patches.check(_with(desk=[desk])))


def test_a_spawn_lands_the_rest_and_says_what_it_refused(tmp_path):
    """Decided: a Landing that reaches the doors anyway (one built past
    `check`) loses that row with a note and lands the rest, as any other row
    the referee refuses at a spawn does."""
    app = headless.make_app(seed(tmp_path))
    app.lib.load("loadable", "party-trip")
    pre, table, reg = app.loaded_patch, app.router.table, app.reg
    u = undo.Undo(reg, table, banks=pre.banks)
    undo.install(u)
    try:
        e = graphview.Edit(table, reg, app.router, graph=pre.graph,
                           push=lambda label: undo.push(label, load=True))
        e.loaded_patch = pre
        doc = _with(routes=[{"source": "lfo:0", "target": "master.gain", "op": "push",
                             "value": 0.2}],
                    desk=[{"source": "cc:3:16", "target": "tempo.bpm", "op": "abs"}])
        landing = patches.spawn(doc, patches.Host.of(pre.graph.spec, table, pre.banks()),
                                (40.0, 60.0))
        assert e.spawn(landing) is None
        assert not table.routes_to("master.gain") and table.routes_to("fx.acid.speed")
        assert not [b for b in table.desk() if b.target == "tempo.bpm"]
        assert WORDS in e.said and "tempo.bpm is the meta controller's" in e.said
    finally:
        undo.install(None)


# ------------------------------------------------------------------ the tool

def _library(root: Path) -> Path:
    (root / "loadable" / "sub").mkdir(parents=True)
    (root / "loadable" / "trash").mkdir()
    (root / "patches").mkdir()
    row = {"source": "hand:left.y", "target": "master.gain", "op": "push", "value": 0.375}
    (root / "loadable" / "a.json").write_text(json.dumps({"routes": [row], "desk": [
        {"source": "cc:0:48", "target": "tempo.bpm", "op": "abs"},
        {"source": "cc:0:49", "target": "view.bright", "op": "abs"}]}))
    (root / "loadable" / "sub" / "b.json").write_text(json.dumps({"routes": [row], "macros": {
        "macro.1": {"subs": [{"base": "master.dyn"},
                             {"depth": {"source": "hand:1", "target": "master.gain"}}]}}}))
    (root / "loadable" / "clean.json").write_text(json.dumps({"routes": [
        {"source": "lane:0", "target": "view.bright", "op": "push", "scale": "master.gain"}]}))
    (root / "loadable" / "trash" / "gone.json").write_text(json.dumps({"routes": [row]}))
    (root / "loadable" / "bad.json").write_text("{nope")
    (root / "patches" / "p.json").write_text(json.dumps({"routes": [row]}))
    return root


def test_the_tool_lists_every_row_that_would_drop_and_writes_nothing(tmp_path, capsys):
    t = tool()
    lib = _library(tmp_path / "lib")
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in lib.rglob("*") if p.is_file()}
    assert t.main([str(lib)]) == 0
    out = capsys.readouterr().out
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns)
                      for p in lib.rglob("*") if p.is_file()}
    assert "loadable: 5 row(s) in 2 of 3 file(s), dropped at the next load of each" in out
    assert "patches: 1 row(s) in 1 of 1 file(s), each patch refused whole when read" in out
    assert "a.json  [routes]  hand:left.y → master.gain  push 0.375" in out
    assert "a.json  [desk]  cc:0:48 → tempo.bpm" in out
    assert "macro.1 → master.dyn" in out and "macro.1 → master.gain" in out
    assert "   2 × hand:left.y → master.gain" in out
    assert "gone.json" not in out and "clean.json" not in out and "view.bright" not in out
    assert "could not read" in out and "bad.json" in out


def test_a_malformed_row_names_its_file_and_the_report_goes_on(tmp_path, capsys):
    """Review of #371: `{"value": null}` crashed the report's format; a row or a
    subscriber this build cannot read is the bad file's, named and passed over."""
    t = tool()
    lib = _library(tmp_path / "lib")
    row = {"source": "hand:left.y", "target": "master.gain", "op": "push", "value": None}
    (lib / "loadable" / "nulled.json").write_text(json.dumps({"routes": [row]}))
    (lib / "loadable" / "subbed.json").write_text(json.dumps(
        {"macros": {"macro.1": {"subs": [{"depth": 3}]}}}))
    assert t.main([str(lib)]) == 0
    out = capsys.readouterr().out
    assert "subbed.json" in out and "a.json  [routes]" in out


def test_the_tool_has_no_default_path(tmp_path, capsys):
    t = tool()
    with pytest.raises(SystemExit):
        t.main([])
    assert t.main([str(tmp_path / "none")]) == 2
