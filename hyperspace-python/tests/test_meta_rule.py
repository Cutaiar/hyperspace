"""The hard rule (the owner, 2026-11-04; register rows 743–745): no row of a
preset may drive a meta controller param (`part_of(p) == "session"`). Every door
refuses it in words, a saved one drops with a note and the next save removes it,
and the meta controller's own rows stay.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from conftest import seed
from test_graph_groups import BREATH
from test_pad_learn import ScriptedPad
from test_presets import boot, put
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import gamepad, graphview, headless, patches, ui_graph, ui_routing, undo
from hyperspace.learn import Learn
from hyperspace.params import part_of, part_of_id
from hyperspace.routing import (
    MOD_OPS,
    Binding,
    Bindings,
    Macro,
    Sub,
    factory_desk,
    is_session_row,
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
def test_the_meta_controllers_own_rows_are_not_a_presets(row):
    assert is_session_row(row) and meta_row_refusal(row) is None
    assert Bindings().add(row) is row


@pytest.mark.parametrize("row", [
    *(Binding("hand:left.y", "master.gain", op, 0.375) for op in MOD_OPS),
    Binding("hand:left.y", "master.gain", "push", 0.375, enabled=False),
    Binding("cc:0:14", "master.gain", "abs", layer="preset"),
])
def test_a_presets_rows_are_refused_at_the_one_door(row):
    assert not is_session_row(row)
    assert WORDS in meta_row_refusal(row)
    t = Bindings()
    with pytest.raises(ValueError, match=WORDS):
        t.add(row)
    assert t.bindings == []


def test_every_factory_row_on_a_meta_param_is_the_meta_controllers():
    """The line is mechanical: the factory's rows on a meta param all pass by
    their layer, and the factory's preset layer holds none, with no id listed."""
    table = Bindings.factory()
    on_meta = [b for b in table.bindings if meta_refusal(b.target) is not None]
    assert any(b.target == "output.dim" for b in on_meta) and len(on_meta) > 40
    assert all(is_session_row(b) and meta_row_refusal(b) is None for b in on_meta)
    assert not [b for b in factory_desk() if b.layer == "preset"
                and meta_refusal(b.target) is not None]


def test_the_masters_row_survives_a_load_that_drops_a_presets(tmp_path):
    r = boot(tmp_path)
    table = r.router.table
    master = [b for b in table.bindings if b.target == "output.dim" and is_session_row(b)]
    assert master
    put(tmp_path, "LEANS", routes=[
        {"source": "hand:left.y", "target": "output.dim", "op": "push", "value": 0.375}])
    r.presets.load("LEANS")
    assert all(any(x is b for x in table.bindings) for b in master)
    assert not table.routes_to("output.dim")


def test_a_presets_row_moved_or_woken_onto_a_meta_param_is_refused():
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
    r.presets.load("LEANS")
    table, notes = r.router.table, r.presets.notes
    assert any(n.startswith("dropped hand:left.y → master.gain: " + WORDS) for n in notes)
    assert any(n.startswith("dropped axis:RX → master.dyn: master.dyn is") for n in notes)
    assert any(n.startswith("dropped cc:0:48 → tempo.bpm: tempo.bpm is") for n in notes)
    assert any("depth subscriber on hand:left.y → master.gain" in n for n in notes)
    assert [b.target for b in table.routes()] == ["view.speed"]
    assert [b.target for b in table.desk()] == ["view.bright"]
    assert path.read_bytes() == before and not r.lib.is_dirty("presets")
    r.lib.save_as("presets", "LEANS")
    doc = json.loads(path.read_text())
    assert [x["target"] for x in doc["routes"]] == ["view.speed"]
    assert [x["target"] for x in doc["desk"]] == ["view.bright"]
    assert doc["macros"]["macro.1"]["subs"] == [{"base": "view.bright", "from": 0.0, "to": 0.5}]
    r.presets.load("LEANS")
    assert not [n for n in r.presets.notes if "meta controller" in n]


def test_no_corpus_file_holds_a_row_on_a_meta_param():
    """party-tumble's `hand:left.y → master.gain` was the only one, removed."""
    t = tool()
    for kind in ("presets", "patches"):
        assert t.scan(ROOT / "tests" / "corpus" / kind)[1] == [], kind


def test_party_tumble_keeps_its_other_rows_and_its_scale():
    """A `scale` reads a meta param and never moves it (row 18 (a)): it stays."""
    doc = json.loads((ROOT / "tests/corpus/presets/party-tumble.json").read_text())
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
    """The desk's preset layer is refused, wherever the control. A pad button is
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
    doc = r.presets.document("LEFT")
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
    assert "invariant" in why and "meta controller" not in why
    lrn = Learn(rig.reg, table)
    lrn.arm("tempo.bpm", "desk")
    assert lrn.learn_control(fader) is False
    assert "invariant" in lrn.last and lrn.learning == "tempo.bpm"


# ------------------------------------------------------------- the pickers

def test_routing_and_the_desk_combo_offer_no_meta_param(rig):
    panel, reg = rig.panel, rig.reg
    for offered in (ui_routing._targets(panel), ui_routing._desk_targets(panel)):
        assert offered and not [p for p in offered if part_of(p) == "session"]
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
    still draws: it is not a preset's."""
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


# ----------------------------------------------------------- macros, modifiers

def test_macro_base_and_depth_subscribers_on_a_meta_param_are_dropped():
    """Decided: both, at `set_macros`. A base already was (D9); a depth has no
    route to scale. A depth on a preset's route stays."""
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
    app.lib.load("presets", "party-trip")
    pre, table, reg = app.presets, app.router.table, app.reg
    u = undo.Undo(reg, table, banks=pre.banks)
    undo.install(u)
    try:
        e = graphview.Edit(table, reg, app.router, graph=pre.graph,
                           push=lambda label: undo.push(label, load=True))
        e.presets = pre
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
    (root / "presets" / "sub").mkdir(parents=True)
    (root / "presets" / "trash").mkdir()
    (root / "patches").mkdir()
    row = {"source": "hand:left.y", "target": "master.gain", "op": "push", "value": 0.375}
    (root / "presets" / "a.json").write_text(json.dumps({"routes": [row], "desk": [
        {"source": "cc:0:48", "target": "tempo.bpm", "op": "abs"},
        {"source": "cc:0:49", "target": "view.bright", "op": "abs"}]}))
    (root / "presets" / "sub" / "b.json").write_text(json.dumps({"routes": [row], "macros": {
        "macro.1": {"subs": [{"base": "master.dyn"},
                             {"depth": {"source": "hand:1", "target": "master.gain"}}]}}}))
    (root / "presets" / "clean.json").write_text(json.dumps({"routes": [
        {"source": "lane:0", "target": "view.bright", "op": "push", "scale": "master.gain"}]}))
    (root / "presets" / "trash" / "gone.json").write_text(json.dumps({"routes": [row]}))
    (root / "presets" / "bad.json").write_text("{nope")
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
    assert "presets: 5 row(s) in 2 of 3 file(s), dropped at the next load of each" in out
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
    (lib / "presets" / "nulled.json").write_text(json.dumps({"routes": [row]}))
    (lib / "presets" / "subbed.json").write_text(json.dumps(
        {"macros": {"macro.1": {"subs": [{"depth": 3}]}}}))
    assert t.main([str(lib)]) == 0
    out = capsys.readouterr().out
    assert "subbed.json" in out and "a.json  [routes]" in out


def test_the_tool_has_no_default_path(tmp_path, capsys):
    t = tool()
    with pytest.raises(SystemExit):
        t.main([])
    assert t.main([str(tmp_path / "none")]) == 2
