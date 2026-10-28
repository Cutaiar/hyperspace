"""Plan 39 T5 (W6): GRAPH and the pages — plan 39's three nodes on the
canvas.

The picker lists `segment` under media ▸ and `matte` and `cut` under a
new masks ▸; each adds an unwired node, one undo step. The **cut-out**
starter wires `channel.a → segment.image`, `segment.fg → composite.over`,
`scene → composite.under`, `composite → output.all.image`, refusing
nothing, and names what fed All outputs before (as the scene chain now
does too). A cable whose maker makes a mask is purple (MASK) whatever port
takes it; every segment instance's pins are drawn; a matte, a cut or a
segment the renderer built none of says its state in words (`said`,
read by `summary`); each round-trips through a `/7` save with its values."""

from __future__ import annotations

import json

import pytest
from test_graph_edit import wired_rig, wired_wires
from test_plan36_edges import build, cable, spec_of, view_of

from hyperspace import graph as G
from hyperspace import graphview, params
from hyperspace.routing import Bindings

ALL = "output.all.image"
SCENE = {"frame": "wired", "wires": [{"from": "shape", "to": "scene.geometry"},
                                     {"from": "scene", "to": ALL}]}
CUT_OUT = {("channel.a", "segment.image"), ("segment.fg", "composite.over"),
           ("scene", "composite.under"), ("composite", ALL)}


def _entries(rig) -> list[dict]:
    return [e for e in rig.presets.graph.spec.to_json().get("nodes", [])
            if e.get("kind") != "hands"]


# ---------------------------------------------------------------- the picker

def test_the_picker_lists_the_three_in_their_groups(tmp_path):
    _, e, _ = wired_rig(tmp_path, {"frame": "wired"})
    items = [(k, f, w) for k, f, w in graphview.picker(e)
             if k in ("segment", "matte", "cut")]
    assert items == [("segment", None, "segment"), ("matte", None, "matte"),
                     ("cut", None, "cut")]
    assert graphview.PICKER_GROUP["segment"] == "media"
    assert graphview.PICKER_GROUP["matte"] == graphview.PICKER_GROUP["cut"] == "masks"
    groups = graphview.PICKER_GROUPS
    assert groups.index("pictures") < groups.index("media") < groups.index("masks") \
        < groups.index("effects")


@pytest.mark.parametrize("kind", ["matte", "cut", "segment"])
def test_each_adds_unwired_one_undo_step_and_a_second_is_the_next(tmp_path, kind):
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.add_node(kind) is None
    assert e.added == kind and {"kind": kind} in _entries(rig)
    assert e.said == graphview.ADD_SAID[kind].format(name=kind)
    assert wired_wires(rig) == {("shape", "scene.geometry"), ("scene", ALL)}
    assert e.add_node(kind) is None
    assert e.added == f"{kind}.2" and {"kind": kind, "instance": 2} in _entries(rig)
    assert pushed == [f"add {kind}", f"add {kind}.2"]
    assert rig.presets.graph.spec.notes == ()


def test_a_new_one_skips_a_name_a_wire_already_says(tmp_path):
    """`segment.2.fg` wired with no entry for it names segment.2: the next
    add is segment (1), then segment.3."""
    section = {"frame": "wired", "nodes": [{"kind": "segment", "instance": 2}],
               "wires": [{"from": "channel.a", "to": "segment.2.image"},
                         {"from": "segment.2.fg", "to": ALL}]}
    _, e, _ = wired_rig(tmp_path, section)
    assert e.add_node("segment") is None and e.added == "segment.3"


# ---------------------------------------------------------------- the cut-out starter

def test_the_cut_out_on_the_scene_chain(tmp_path):
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("cut-out") is None
    assert wired_wires(rig) == {("shape", "scene.geometry")} | CUT_OUT
    assert {"kind": "segment"} in _entries(rig) and {"kind": "composite"} in _entries(rig)
    assert rig.presets.graph.spec.notes == ()
    assert pushed == ["starter: cut-out"]
    assert e.placed == ("segment", "composite")      # (the scene, channel a, All outputs stay)
    assert e.said == ("cut-out: channel.a → segment.image, segment.fg over the scene in "
                      "composite → All outputs — in place of scene into All outputs")


def test_the_cut_out_on_a_blank_preset_lays_the_scene_too(tmp_path):
    rig, e, _ = wired_rig(tmp_path, {"frame": "wired"})
    assert e.starter("cut-out") is None
    assert wired_wires(rig) == CUT_OUT
    assert e.placed == ("scene", "segment", "composite")
    assert e.said.endswith(graphview.CUT_OUT_NO_SHAPE)
    assert "in place of" not in e.said


def test_a_second_cut_out_is_refused_nothing(tmp_path):
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("cut-out") is None
    assert e.starter("cut-out") is None
    got = wired_wires(rig)
    assert {("channel.a", "segment.2.image"), ("segment.2.fg", "composite.2.over"),
            ("scene", "composite.2.under"), ("composite.2", ALL)} <= got
    assert ("composite", ALL) not in got             # (one wire into a port)
    assert "in place of composite into All outputs" in e.said
    assert e.placed == ("segment.2", "composite.2") and len(pushed) == 2
    assert rig.presets.graph.spec.notes == ()


def test_the_cut_out_from_the_picker_lands_at_the_point(tmp_path):
    _, e, _ = wired_rig(tmp_path, SCENE)
    assert e.add_node("starter", "cut-out") is None
    lay = graphview.chain_layout(e.placed, (100.0, 50.0))
    assert lay == {"render:segment": [100, 50], "render:composite": [100 + graphview.COL_W, 50]}


def test_the_scene_chain_names_what_it_replaced(tmp_path):
    """Plan 36's follow-up: the scene chain no longer drops what fed All
    outputs' picture in silence."""
    _, e, _ = wired_rig(tmp_path, {"frame": "wired",
                                     "wires": [{"from": "channel.b", "to": ALL}]})
    assert e.starter("scene") is None
    assert e.said == graphview.STARTER_SAID + " — in place of channel.b into All outputs"
    _, e, _ = wired_rig(tmp_path / "again", SCENE)
    assert e.starter("scene") is None and e.said in ("already so", graphview.STARTER_SAID)


# ---------------------------------------------------------------- the canvas

def test_a_promoted_mask_cable_is_purple_into_a_red_port():
    spec = spec_of(("channel.a", "matte.image"), ("matte", ALL), nodes=[{"kind": "matte"}])
    view = view_of(spec, build(spec))
    c = cable(view, "matte", ALL)
    assert c.type == graphview.MASK
    port = next(p for n in view.nodes for p in n.ports if p.id == "rin:output.all/image")
    assert port.type == graphview.IMAGE
    # a picture into the same port stays red; a matte's own input too
    assert cable(view, "channel.a", "matte.image").type == graphview.IMAGE


def test_a_segment_s_mask_pin_is_purple_its_pictures_red():
    spec = spec_of(("channel.a", "segment.image"), ("segment.mask", "composite.over"),
                   ("segment.fg", "composite.under"), ("composite", ALL),
                   nodes=[{"kind": "segment"}, {"kind": "composite"}])
    view = view_of(spec, build(spec))
    assert cable(view, "segment.mask", "composite.over").type == graphview.MASK
    assert cable(view, "segment.fg", "composite.under").type == graphview.IMAGE


def test_every_segment_instance_draws_its_pins_and_their_cables():
    """T4's review: `PINS` lists instance 1 alone; a wired `segment.2` must
    never be invisible."""
    spec = spec_of(("channel.a", "segment.2.image"), ("segment.2.fg", ALL),
                   ("segment.2.mask", "lookback.cover"), ("scene", "lookback.image"),
                   nodes=[{"kind": "segment", "instance": 2}, {"kind": "lookback"}])
    view = view_of(spec, build(spec))
    node = next(n for n in view.nodes if n.id == "render:segment.2")
    pins = {p.id: p.type for p in node.ports if p.direction == graphview.OUT}
    assert pins == {"rout:segment.2.fg": G.IMAGE, "rout:segment.2.bg": G.IMAGE,
                    "rout:segment.2.mask": G.MASK}
    assert cable(view, "segment.2.fg", ALL).type == graphview.IMAGE
    assert cable(view, "segment.2.mask", "lookback.cover").type == graphview.MASK


def test_segment_one_s_pins_are_drawn_once():
    spec = spec_of(("channel.a", "segment.image"), ("segment.fg", ALL),
                   nodes=[{"kind": "segment"}])
    view = view_of(spec, build(spec))
    node = next(n for n in view.nodes if n.id == "render:segment")
    outs = [p.id for p in node.ports if p.direction == graphview.OUT]
    assert outs == ["rout:segment.fg", "rout:segment.bg", "rout:segment.mask"]


def test_each_node_s_params_are_its_ports():
    reg = params.Registry()
    params.declare_mattes(reg, ["matte"])
    params.declare_cuts(reg, ["cut.2"])
    params.declare_segments(reg, ["segment.2"])
    spec = spec_of(("channel.a", "matte.image"), ("channel.b", "cut.2.image"),
                   ("matte", "cut.2.mask"), ("cut.2", ALL),
                   ("channel.c", "segment.2.image"), ("segment.2.fg", "output.2.image"),
                   nodes=[{"kind": "matte"}, {"kind": "cut", "instance": 2},
                          {"kind": "segment", "instance": 2}])
    view = graphview.build(Bindings(), reg, None, None, build(spec, n=2), spec)
    for name, group in (("matte", "matte"), ("cut.2", "cut.2"), ("segment.2", "segment.2")):
        node = next(n for n in view.nodes if n.id == f"render:{name}")
        mine = {p.param for p in node.ports if p.param is not None}
        want = {p.id for p in reg if p.id.rpartition(".")[0] == group and p.modulatable}
        assert want and want <= mine, (name, want - mine)


# ---------------------------------------------------------------- the words

def _said(spec, name: str) -> list[str]:
    view = view_of(spec, build(spec))
    node = next(n for n in view.nodes if n.id == f"render:{name}")
    return graphview.summary(node)


def test_an_unwired_matte_cut_and_segment_say_so():
    spec = spec_of(("scene", ALL), nodes=[{"kind": "matte"}, {"kind": "cut"},
                                          {"kind": "segment"}])
    assert graphview.MATTE_UNWIRED in _said(spec, "matte")
    assert graphview.CUT_NO_PICTURE in _said(spec, "cut")
    assert graphview.SEGMENT_UNWIRED in _said(spec, "segment")
    assert _said(spec, "matte")[0] == graphview.REACHES_NOTHING


def test_wired_but_unreached_they_say_their_source():
    spec = spec_of(("scene", ALL), ("channel.a", "matte.image"), ("channel.b", "cut.image"),
                   ("channel.c", "segment.image"),
                   nodes=[{"kind": "matte"}, {"kind": "cut"}, {"kind": "segment"}])
    assert "a mask of channel.a's picture" in _said(spec, "matte")
    assert graphview.CUT_NO_MASK in _said(spec, "cut")
    assert graphview.CUT_NO_MASK == "no mask wired: its picture through, whole"
    assert "channel.c into it: no worker runs until it is reached" in _said(spec, "segment")
    spec = spec_of(("scene", ALL), ("channel.a", "matte.image"), ("channel.b", "cut.image"),
                   ("matte", "cut.mask"), nodes=[{"kind": "matte"}, {"kind": "cut"}])
    assert "channel.b cut by matte" in _said(spec, "cut")


def test_a_built_node_says_its_own_words():
    """A node the renderer built keeps its own `said` (the worker's state
    for a segment): the stand-in's words are for an unbuilt one only."""
    spec = spec_of(("channel.a", "segment.image"), ("segment.fg", ALL),
                   nodes=[{"kind": "segment"}])
    g = build(spec)
    g.nodes["segment"].said = "Vision · fast · 30/s"
    view = view_of(spec, g)
    node = next(n for n in view.nodes if n.id == "render:segment")
    assert graphview.summary(node)[0] == "Vision · fast · 30/s"


# ---------------------------------------------------------------- the /7 round trip

def test_each_entry_round_trips_through_a_seven_save_with_its_values(tmp_path):
    from test_presets import boot

    rig, e, _ = wired_rig(tmp_path / "a", SCENE)
    for kind in ("matte", "cut", "segment", "segment"):
        assert e.add_node(kind) is None
    rig.reg["matte.key"].set(0.3)
    rig.reg["cut.amount"].set(0.5)
    rig.reg["segment.2.feather"].set(6.0)
    saved = rig.presets.save_as("t5-round").read_text()
    doc = json.loads(saved)
    assert doc["schema"] == "hyperspace.preset/7"
    nodes = doc["graph"]["nodes"]
    assert {"kind": "matte"} in nodes and {"kind": "cut"} in nodes
    assert {"kind": "segment"} in nodes and {"kind": "segment", "instance": 2} in nodes
    home = tmp_path / "b"
    (home / "presets").mkdir(parents=True)
    (home / "presets" / "t5-round.json").write_text(saved)
    r = boot(home)
    r.presets.load("t5-round")
    got = r.presets.graph.spec
    assert got == rig.presets.graph.spec and not got.notes
    assert got.mattes == (G.MatteAt(1),) and got.cuts == (G.CutAt(1),)
    assert r.reg["matte.key"].value == pytest.approx(0.3)
    assert r.reg["cut.amount"].value == pytest.approx(0.5)
    assert r.reg["segment.2.feather"].value == pytest.approx(6.0)


# ---------------------------------------------------------------- the FX page

def test_edges_is_an_effect_file_like_any(tmp_path):
    """W6: `edges` (T0) is on the picker's effects ▸ and on the FX page as
    any effect file is — nothing of its own."""
    from hyperspace import ui_fx

    rig, e, _ = wired_rig(tmp_path, SCENE)
    assert ("effect", "edges", "edges") in graphview.picker(e)
    assert e.add_node("effect", "edges") is None
    spec = rig.presets.graph.spec
    assert any("edges" in names for _, names in ui_fx.groups(spec))
