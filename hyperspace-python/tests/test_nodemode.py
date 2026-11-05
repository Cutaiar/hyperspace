"""Plan 57 (NM0): node mode's saved form, the fill it derives its rows from, and
the cable kind. Over the corpus on a scratch home; no behaviour yet (N1, N2)."""

import json
from pathlib import Path

import pytest
from conftest import CORPUS, seed

from hyperspace import gamepad, graphview, headless, nodemode, preset, routing, ui_graph, undo
from hyperspace.library import Marks
from hyperspace.nodemode import NodeMode, Slot, fill
from hyperspace.pads import models

CORPUS_PRESETS = sorted(p.stem for p in (CORPUS / "presets").glob("*.json"))
ENTRY = {"player": 2, "controller": "gamepad", "node": "macro.1"}


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    home = tmp_path_factory.mktemp("nodemode")
    seed(home)
    return headless.make_app(home)


def save(app, name: str) -> bytes:
    return Path(app.presets.save_as(name)).read_bytes()


def load(app, stem: str) -> str:
    app.lib.load(preset.GROUP, stem)
    return app.lib.current(preset.GROUP) or stem


def put_file(app, stem: str, **keys) -> None:
    doc = {"schema": preset.SAVE_SCHEMA, "name": stem, "values": {}, "routes": [], "desk": [],
           "macros": {}, **keys}
    (Path(app.lib.home) / preset.GROUP / f"{stem}.json").write_text(json.dumps(doc))


# ---- the saved form ----

def test_the_entries_read_in_one_order_and_another_node_just_switches():
    a, _ = NodeMode.read([ENTRY, {"player": 1, "controller": "midi", "node": "macro.2"}])
    b = NodeMode().pointing(2, "gamepad", "macro.1").pointing(1, "midi", "macro.2")
    assert a == b and a.to_json()[0]["player"] == 1
    moved = a.pointing(2, "gamepad", "macro.3")
    assert moved.of(2, "gamepad") == "macro.3" and len(moved.entries) == 2
    assert moved.leaving(2, "gamepad").of(2, "gamepad") is None


@pytest.mark.parametrize("bad", [
    "nope", [3], [{"player": 5, "controller": "midi", "node": "x"}],
    [{"player": True, "controller": "midi", "node": "x"}],
    [{"player": 1, "node": "x"}], [{"player": 1, "controller": "midi", "node": ""}],
])
def test_what_is_not_an_entry_is_said_and_left_out(bad):
    got, notes = NodeMode.read(bad)
    assert not got and notes == [nodemode.BAD_ENTRY]


def test_a_second_entry_for_one_controller_loses_and_a_kind_unknown_here_is_kept():
    got, notes = NodeMode.read([ENTRY, {**ENTRY, "node": "macro.2"},
                                {"player": 1, "controller": "theremin", "node": "macro.1"}])
    assert got.of(2, "gamepad") == "macro.1" and got.of(1, "theremin") == "macro.1"
    assert notes == [nodemode.TWICE.format(player=2, controller="gamepad", node="macro.1")]


def test_a_preset_says_the_key_one_entry_a_line():
    text = preset.dumps({"schema": preset.SAVE_SCHEMA, "node_mode": [ENTRY, ENTRY]})
    assert f'  {json.dumps(ENTRY)},\n  {json.dumps(ENTRY)}\n' in text


# ---- the corpus ----

@pytest.mark.parametrize("stem", CORPUS_PRESETS)
def test_node_mode_round_trips_over_the_corpus(app, stem):
    """The point of the key: open it again and it is back; take it out and the
    file is the bytes it was."""
    name = load(app, stem)
    plain = save(app, name)
    assert b"node_mode" not in plain
    node = min(n for n in app.presets._held_canvas() if n.startswith(("render:", "macro.")))
    assert app.presets.point_node_mode(1, "midi", node) is None
    assert app.presets.point_node_mode(2, "gamepad", "macro.2") is None
    saved = save(app, name)
    assert json.loads(saved)["node_mode"] == [
        {"player": 1, "controller": "midi", "node": node},
        {"player": 2, "controller": "gamepad", "node": "macro.2"}]
    load(app, name)
    assert app.presets.node_mode.of(1, "midi") == node
    assert app.presets.node_mode.of(2, "gamepad") == "macro.2"
    assert not [n for n in app.presets.notes if "node mode" in n]
    assert save(app, name) == saved                     # a fixed point
    doc = json.loads(saved)
    del doc["node_mode"]
    assert preset.dumps(doc).encode() == plain          # the key and nothing else
    app.presets.leave_node_mode(1, "midi")
    app.presets.leave_node_mode(2, "gamepad")
    assert save(app, name) == plain                     # byte for byte


def test_a_load_with_no_key_points_at_nothing(app):
    load(app, CORPUS_PRESETS[0])
    app.presets.point_node_mode(1, "midi", "macro.1")
    load(app, CORPUS_PRESETS[1])                        # no preset affects another
    assert not app.presets.node_mode


def test_a_new_preset_points_at_nothing(app):
    load(app, CORPUS_PRESETS[0])
    app.presets.point_node_mode(1, "midi", "macro.1")
    app.presets.new()
    assert not app.presets.node_mode


def test_the_migration_road_keeps_the_key_as_a_fixed_point(tmp_path):
    src = tmp_path / "with.json"
    doc = json.loads((CORPUS / "presets" / f"{CORPUS_PRESETS[0]}.json").read_text())
    doc["node_mode"] = [ENTRY]
    src.write_text(preset.dumps(doc))
    once, notes, _ = headless.resave(src, tmp_path / "a")
    assert json.loads(once)["node_mode"] == [ENTRY]
    assert not [n for n in notes if "node mode" in n]
    again = tmp_path / "again.json"
    again.write_bytes(once)
    assert headless.resave(again, tmp_path / "b")[0] == once


def test_a_node_the_graph_does_not_have_is_said_and_left_out(app):
    put_file(app, "gone", node_mode=[{**ENTRY, "player": 1, "node": "render:nothing"}, ENTRY])
    load(app, "gone")
    assert app.presets.node_mode.to_json() == [ENTRY]
    assert nodemode.NODE_GONE.format(node="nothing") in app.presets.notes


def test_pointing_at_a_node_the_preset_does_not_have_is_refused(app):
    load(app, CORPUS_PRESETS[0])
    was = app.presets.node_mode
    assert app.presets.point_node_mode(1, "midi", "render:nothing") == (
        nodemode.NODE_GONE.format(node="nothing"))
    assert app.presets.node_mode == was


def test_re_pointing_lights_the_dot(app):
    name = load(app, CORPUS_PRESETS[0])
    save(app, name)
    assert not app.lib.is_dirty(preset.GROUP)
    app.presets.point_node_mode(1, "midi", "macro.1")
    assert app.lib.is_dirty(preset.GROUP)
    app.presets.leave_node_mode(1, "midi")
    assert not app.lib.is_dirty(preset.GROUP)


def test_a_node_that_goes_lets_go(app):
    load(app, CORPUS_PRESETS[0])
    bank = app.presets.banks()["lfo"]
    voice = bank.doc()[-1]
    node = f"lfo.{voice}"
    assert app.presets.point_node_mode(1, "midi", node) is None
    app.presets.settle_groups()
    assert app.presets.node_mode.of(1, "midi") == node  # still there: stays
    bank.remove(voice)                                  # the mechanism's hook, not a caller
    assert not app.presets.node_mode


def test_re_pointing_is_one_undo_step_that_puts_it_back(app):
    load(app, CORPUS_PRESETS[0])
    was = undo._installed
    try:
        u = undo.Undo(app.reg, app.router.table, marks=Marks(app.lib))
        undo.install(u)
        app.presets.point_node_mode(1, "midi", "macro.1")
        u.tick(1.0)                                     # another frame, another action
        app.presets.point_node_mode(1, "midi", "macro.2")
        u.tick(2.0)
        assert app.presets.node_mode.of(1, "midi") == "macro.2"
        assert len(u.stack) == 2
        assert u.undo() and app.presets.node_mode.of(1, "midi") == "macro.1"
        assert u.undo() and not app.presets.node_mode
        assert u.redo() and app.presets.node_mode.of(1, "midi") == "macro.1"
    finally:
        undo.install(was)
        app.presets.node_mode = NodeMode()


# ---- the row map: derived, never saved ----

def test_the_params_fill_the_freedoms_in_order():
    got = fill(["a", "b"], [("axis:LX",), ("axis:LY",), ("axis:RX",)])
    assert got.slots == (Slot(("axis:LX",), "a"), Slot(("axis:LY",), "b"))
    assert not got.over and not got.kept and got.too_many("render:acid") is None


def test_a_mapping_on_the_node_stays_and_the_rest_fill_what_is_left():
    got = fill(["a", "b", "c"], [("axis:LX",), ("axis:LY",), ("axis:RX",)],
               rows=[("axis:LX", "b"), ("axis:RY", "elsewhere")])
    assert got.kept == ("b",)
    assert got.slots == (Slot(("axis:LY",), "a"), Slot(("axis:RX",), "c"))


def test_another_players_mapping_stays_and_takes_no_freedom_of_this_controller():
    got = fill(["a", "b"], [("axis:LX",), ("axis:LY",)], rows=[("axis:LX", "a")], qualifier="p2")
    assert got.kept == ("a",) and got.slots == (Slot(("axis:LX",), "b"),)
    got = fill(["a", "b"], [("axis:LX",), ("axis:LY",)], rows=[("axis@p2:LX", "a")],
               qualifier="p2")
    assert got.slots == (Slot(("axis:LY",), "b"),)


def test_a_node_that_does_not_fit_lists_what_is_over_and_does_not_page():
    got = fill(["a", "b", "c"], [("axis:LX",)])
    assert got.slots == (Slot(("axis:LX",), "a"),) and got.over == ("b", "c")
    assert got.too_many("render:acid") == nodemode.TOO_MANY.format(node="acid", params="b, c")


def test_a_pair_is_one_degree_of_freedom_and_a_row_on_it_takes_both_poles():
    pair = ("hat:UP", "hat:DOWN")
    assert fill(["a", "b"], [pair, ("axis:LX",)]).slots[0] == Slot(pair, "a")
    assert nodemode.own_sources("pair:UP/DOWN") == pair
    assert nodemode.own_sources("pair@p2:UP/DOWN") == ()
    got = fill(["a", "b"], [pair, ("axis:LX",)], rows=[("pair:UP/DOWN", "a")])
    assert got.slots == (Slot(("axis:LX",), "b"),)
    got = fill(["a"], [pair, ("axis:LX",)], rows=[("hat:UP", "a")])
    assert got.kept == ("a",) and not got.slots


def test_busy_sources_are_left_alone():
    got = fill(["a"], [("axis:LT",), ("axis:RT",)], busy=["axis:LT"])
    assert got.slots == (Slot(("axis:RT",), "a"),)


def test_one_file_fills_what_each_controller_has():
    """Why no row is saved: the patch names a player, and the map is that
    controller's. On the shipped factories, not a stand-in."""
    params = [f"p{i}" for i in range(40)]
    xbox = gamepad.degrees_of_freedom()
    joycon = gamepad.degrees_of_freedom(models.MODELS["joycon-l"])
    assert len(fill(params, xbox).slots) == len(xbox) != len(joycon)
    assert len(fill(params, joycon).slots) == len(joycon)
    assert fill(params, xbox) == fill(params, xbox)                 # one map


def test_a_meta_param_is_never_filled(app):
    reg = app.reg
    assert routing.meta_refusal("master.gain") is not None
    assert "master.gain" not in nodemode.fillable(reg, ["master.gain"])
    assert nodemode.enter_refusal(reg, "render:out", ["master.gain"]) == (
        nodemode.ONLY_META.format(node="out"))


def test_only_a_continuous_param_with_no_alias_is_filled(app):
    reg = app.reg
    ids = [p.id for p in reg]
    got = nodemode.fillable(reg, ids)
    assert got and all(reg[p].kind is nodemode.Kind.CONTINUOUS and not reg[p].alias for p in got)
    assert all(routing.meta_refusal(p) is None for p in got)
    assert set(nodemode.fillable(reg, ids, routed=True)) <= set(got)
    assert all(reg[p].modulatable for p in nodemode.fillable(reg, ids, routed=True))


def test_you_enter_with_a_node_selected_and_a_node_with_no_params_cannot(app):
    reg = app.reg
    assert nodemode.enter_refusal(reg, None, []) == nodemode.NO_NODE
    assert nodemode.enter_refusal(reg, "render:acid", []) == nodemode.NO_PARAMS.format(node="acid")
    pid = nodemode.fillable(reg, [p.id for p in reg])[0]
    assert nodemode.enter_refusal(reg, "render:acid", [pid]) is None


# ---- the cable ----

def test_a_node_mode_cable_is_its_own_kind_drawn_and_labelled():
    c = graphview.node_mode_cable(2, "src", "dst", "LX", "Mix")
    assert c.kind == graphview.NODE_MODE and not c.dormant and not c.off
    assert c.label == "node mode: player 2, LX → Mix"
    asleep = graphview.node_mode_cable(2, "src", "dst", "LX", "Mix", dormant=True)
    assert asleep.dormant and asleep.off and "other Deck" in asleep.label


def test_its_colour_is_no_other_cables_and_not_white(monkeypatch):
    k = ui_graph.KIND_COLOURS[graphview.NODE_MODE]
    rgb = (k.x, k.y, k.z)
    assert all(rgb != (o.x, o.y, o.z) for o in ui_graph.COLOURS.values())
    assert min(rgb) < 0.5                                   # no white, no grey
    seen = {}
    monkeypatch.setattr(ui_graph.ed, "link",
                        lambda lid, a, b, col, thick: seen.update(col=col))
    st = {}
    monkeypatch.setattr(ui_graph, "_id", lambda st, key: 1)
    ui_graph._cable(st, graphview.node_mode_cable(1, "a", "b", "LX", "Mix"))
    assert (seen["col"].x, seen["col"].y, seen["col"].z, seen["col"].w) == (*rgb, k.w)
    ui_graph._cable(st, graphview.node_mode_cable(1, "a", "b", "LX", "Mix", dormant=True))
    assert seen["col"].w == pytest.approx(ui_graph.DORMANT_ALPHA)


def test_a_node_mode_cable_cannot_be_deleted_as_a_cable():
    """A delete goes through the kind's table: this kind is not in it (leaving
    node mode is the chip's, N1b)."""
    assert graphview.NODE_MODE not in ui_graph.DELETE
