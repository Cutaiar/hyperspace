"""Plan 26 A4: the render graph in the preset as JSON; node instances and
the naming rule; the OUTPUT and LOOKBACK pages in words.

A preset may carry a `graph` section (`graph.GraphSpec`: node instances
and their wiring, never a param). None is the default graph — every
preset from before A4, every factory preset. One this build cannot read
is a note and the default graph, never a crash. A second instance of a
node gets the marked ids (`fx.acid.2.*`, `ghost.2.*`) and its own params;
the first keeps today's. The proof preset is a fixture,
`tests/fixtures/presets/hands-lines.json`, loaded through a scratch
library (its pictures are `tests/test_golden_frames.py`'s).

The pure half first (the JSON, the wiring, the default graph's shape,
the words), then the preset loads over a scratch library, then the GL
half: two acids in one chain, two hands nodes each its own Ghost, hands
drawn as lines, a time per node.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_presets import boot, put

from hyperspace import graph as G
from hyperspace import preset
from hyperspace.fx import FxState, SpecError, instance_of_name, parse
from hyperspace.library import FACTORY, PRESETS
from hyperspace.outputs import Switches, View

S = Switches
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "presets" / "hands-lines.json"
DEFAULT = G.Wiring()


def _old(w: G.Wiring) -> G.Wiring:
    """The plan 33 wiring a landed wiring says (plan 35 T3: every load lands
    a wired frame — read back by its round trip, `graphmigrate.unwired`,
    from the section the wiring was read from, so these tests keep asking
    what the frame is in the words they were written in). A wiring of no
    wired frame is itself."""
    from hyperspace import graphmigrate as M

    if not w.wired:
        return w
    nodes = [{"kind": "hands", **({"draw": w.draw} if w.draw != "solid" else {}),
              **({"laid": w.blend} if w.blend != "over" else {})}]
    nodes += [{"kind": "hands", "instance": h.n, **({"draw": h.draw} if h.draw != "solid"
                                                    else {})} for h in w.extra]
    nodes += [{"kind": "effect", "file": e.file, **({"instance": e.n} if e.n != 1 else {}),
               e.where[0]: e.where[1]} for e in w.placed]
    nodes += [c.to_json() for c in (*w.composites, *w.copies)]
    section = {"frame": "wired", "nodes": nodes, "wires": [x.to_json() for x in w.wires]}
    got = M.unwired(section)
    assert got is not None, section
    return G.read_graph(got[0]).wiring()


def _bare(w: G.Wiring) -> G.Wiring:
    """`w` without its run (plan 33 T3: every loaded preset carries its
    run as wires, `Wiring.run`; these tests are about the rest), in plan
    33's words (`_old`)."""
    from dataclasses import replace

    return replace(_old(w), run=None)

# ---------------------------------------------------------------- the JSON


def test_a_graph_section_reads_and_writes_itself_plainly():
    """Every node kind and key the section takes, read and written back
    in a fixed order — defaults left out, `laid` on the node that makes
    the layer — and the wiring and effect instances it says."""
    section = {"nodes": [
        {"kind": "effect", "file": "acid", "instance": 2},
        {"kind": "hands", "instance": 2, "into": "layer", "laid": "depth"},
        {"kind": "history", "holds": "scene+hands"},
        {"kind": "hands", "into": "scene", "draw": "lines"},
    ]}
    spec = G.read_graph(section)
    assert spec.wiring() == G.Wiring(hands="scene", blend="depth", history="scene+hands",
                                     draw="lines", extra=(G.HandsAt(2, "layer"),))
    assert spec.effect_counts() == {"acid": 2}
    assert spec.to_json() == {"nodes": [
        {"kind": "hands", "into": "scene", "draw": "lines"},
        {"kind": "hands", "instance": 2, "laid": "depth"},
        {"kind": "effect", "file": "acid", "instance": 2},
        {"kind": "history", "holds": "scene+hands"}]}
    assert G.read_graph(spec.to_json()) == spec
    # an empty section, or only defaults, is the default graph's wiring
    for plain in ({"nodes": []}, {}, {"nodes": [{"kind": "hands"},
                                                {"kind": "history", "holds": "scene"}]}):
        got = G.read_graph(plain)
        assert got.wiring() == DEFAULT and got.to_json() == {"nodes": []}
    # the first hands node laid on depth-aware, written on the node that makes the layer
    got = G.read_graph({"nodes": [{"kind": "hands", "laid": "add"}]})
    assert got.wiring() == G.Wiring(blend="add")
    assert got.to_json() == {"nodes": [{"kind": "hands", "laid": "add"}]}
    # three effect instances of one file: the chain holds it three times
    got = G.read_graph({"nodes": [{"kind": "effect", "file": "warp", "instance": 3},
                                  {"kind": "effect", "file": "warp", "instance": 2}]})
    assert got.effect_counts() == {"warp": 3}


@pytest.mark.parametrize("section, why", [
    ({"nodes": [{"kind": "teapot"}]}, "unknown node kind 'teapot'"),
    ({"nodes": [{"kind": "hands", "into": "sky"}]}, "into 'sky'"),
    ({"nodes": [{"kind": "hands", "draw": "dots"}]}, "draw 'dots'"),
    ({"nodes": [{"kind": "hands", "laid": "screen"}]}, "laid 'screen'"),
    ({"nodes": [{"kind": "hands", "alpha": 0.5}]}, "no key 'alpha'"),
    ({"nodes": [{"kind": "hands", "instance": 0}]}, "instance 0"),
    ({"nodes": [{"kind": "hands", "instance": 2}]}, "one hands node makes the layer"),
    ({"nodes": [{"kind": "hands", "into": "scene"}, {"kind": "hands", "into": "scene"}]},
     "two hands nodes of instance 1"),
    ({"nodes": [{"kind": "hands", "into": "scene", "laid": "add"},
                {"kind": "hands", "instance": 2}]}, "but ghost.2 makes the layer"),
    # (plan 33 R21: an unplaced instance 1 reads — the file kept on no wire)
    ({"nodes": [{"kind": "effect", "file": "acid", "instance": 0}]}, "instance 0"),
    ({"nodes": [{"kind": "effect", "file": "Acid!", "instance": 2}]}, "lower_snake_case"),
    ({"nodes": [{"kind": "effect", "instance": 2}]}, "names no file"),
    ({"nodes": [{"kind": "history"}, {"kind": "history"}]}, "two history nodes"),
    ({"nodes": [{"kind": "history", "holds": "fx"}]}, "holds 'fx'"),
    ({"nodes": ["hands"]}, "names no kind"),
    ({"nodes": {"kind": "hands"}}, "not a list"),
    ({"nodes": [], "values": {}}, "no key 'values'"),
    ([], "not an object"),
])
def test_a_section_this_build_cannot_read_says_why(section, why):
    with pytest.raises(G.GraphError, match=why.replace("(", r"\(")):
        G.read_graph(section)


def test_the_kind_table_is_the_one_place_a_new_node_kind_is_named(monkeypatch):
    """`NODE_KINDS` (A4b adds its point cloud with one line): a kind read
    by a later WP rides in `others` and is written back as read; unknown
    until it is in the table."""
    entry = {"kind": "points", "role": "kinect"}
    with pytest.raises(G.GraphError, match="unknown node kind 'points'"):
        G.read_graph({"nodes": [entry]})
    monkeypatch.setitem(G.NODE_KINDS, "points", lambda e: {k: v for k, v in e.items()
                                                           if k != "kind"})
    spec = G.read_graph({"nodes": [entry]})
    assert spec.others == (("points", {"role": "kinect"}),) and spec.wiring() == DEFAULT
    assert spec.to_json() == {"nodes": [entry]}


def test_the_wiring_holds_the_hands_nodes_and_one_makes_the_layer():
    w = G.Wiring(hands="scene", extra=(G.HandsAt(2),))
    assert [h.n for h in w.nodes()] == [1, 2] and w.layer_node() == G.HandsAt(2)
    assert w.in_scene() == [G.HandsAt(1, "scene")]
    assert G.Wiring(hands="scene").layer_node() == G.HandsAt(1, "scene")   # A3: its own
    for bad in ({"extra": (G.HandsAt(2),)}, {"extra": (G.HandsAt(1, "scene"),)},
                {"hands": "scene", "extra": (G.HandsAt(2, "scene"), G.HandsAt(2, "scene"))},
                {"draw": "dots"}):
        with pytest.raises(ValueError, match="wiring"):
            G.Wiring(**bad)
    assert [G.hands_name(n) for n in (1, 2)] == ["ghost", "ghost.2"]
    assert [G.layer_name(n) for n in (1, 2)] == ["hands", "hands.2"]
    assert [G.readout_name(n) for n in (1, 3)] == ["readout", "readout.3"]


# ---------------------------------------------------------------- the default graph


def _names(g):
    return [n.name for n in g.order]


def test_two_hands_nodes_one_in_the_scene_one_over_the_glass():
    """`ghost` in the scene (the projector), `ghost.2` the layer laid on
    the glass (scene off): two geometry nodes, each its own Ghost; the
    projector's readout is the scene's hands' (the readout alone), the
    glass's its layer's. The layer's geometry is in no scene, so only the
    scene's hands get a line of their own."""
    w = G.Wiring(hands="scene", extra=(G.HandsAt(2, "layer", "lines"),))
    g = G.default_graph([View(S(), (10, 10)), View(S(scene=False), (10, 10)),
                         View(S(scene=False, through=True), (10, 10))], w)
    assert _names(g) == ["shape", "ghost", "ghost.2", "scene", "cover", "hands.2", "readout",
                         "history", "fx", "composite(hands)", "fx(hands)", "capture",
                         "output.1", "output.2", "output.3"]
    ghost, ghost2 = g.nodes["ghost"], g.nodes["ghost.2"]
    assert g.nodes["scene"].inputs == {"geometry": ghost, "geometry.2": g.nodes["shape"]}
    assert ghost.draw_as == "solid" and ghost2.draw_as == "lines"
    layer = g.nodes["hands.2"]
    assert layer.inputs == {"geometry": ghost2} and layer.readout == "through"
    assert g.nodes["readout"].inputs == {"geometry": ghost}
    o1, o2, o3 = (g.nodes[f"output.{k}"] for k in (1, 2, 3))
    assert o1.inputs["image"] is g.nodes["fx"] and o1.inputs["hands"] is None
    assert o1.inputs["readout"] is g.nodes["readout"]
    assert o2.inputs["hands"] is layer and o2.inputs["readout"] is layer
    assert o3.inputs["image"] is g.nodes["fx(hands)"] and o3.inputs["readout"] is layer
    assert g.nodes["composite(hands)"].inputs["over"] is layer
    # a time per node: the scene's hands (its consumer edge), the second
    # instance's layer and readout lines
    assert g.in_scene() == {"ghost"}
    assert g.timed == ["ghost", "scene", "cover", "hands.2", "readout", "history", "fx",
                       "composite(hands)", "fx(hands)", "capture", "output.1", "output.2",
                       "output.3"]
    # the projector alone: no layer at all, the second node not built
    g = G.default_graph([View(S(), (10, 10))], w)
    assert "ghost.2" not in g.nodes and "hands.2" not in g.nodes


def test_one_hands_node_feeding_a_scene_and_a_layer_is_timed_by_its_scene():
    """The fix A3 left for A4: `Hands.TIMED` is not set by the scene that
    holds it. One hands node feeding the scene and the glass's layer has
    its own line (its in-scene draws) beside the layer's; a hands node
    only in a layer has none (the layer's line is its time); the same
    node object in two graphs is never changed by either."""
    w = G.Wiring(hands="scene")
    both = G.default_graph([View(S(), (1, 1)), View(S(scene=False), (1, 1))], w)
    assert {"ghost", "hands"} <= set(both.timed) and both.in_scene() == {"ghost"}
    only = G.default_graph([View(S(), (1, 1))])
    assert "ghost" not in only.timed and "hands" in only.timed
    shared = G.Hands("ghost")
    a, b = G.Graph(), G.Graph()
    a.add(shared)
    a.add(G.Scene("scene", geometry=shared))
    b.add(shared)
    b.add(G.HandsLayer("hands", geometry=shared))
    assert a.timed == ["ghost", "scene"] and b.timed == ["hands"]
    assert shared.TIMED is False


# ---------------------------------------------------------------- the words


def test_the_wiring_in_words():
    """The OUTPUT page's words (`hands_words`, `layer_words`) and the
    LOOKBACK page's (`history_words`), and the graph's one line."""
    w = DEFAULT
    assert G.hands_words(w, S()) == "hands: over"
    assert G.hands_words(w, S(through=True)) == "hands: through FX"
    assert G.hands_words(w, S(hands=False)) == "hands: off"
    assert G.hands_words(G.Wiring(blend="depth"), S()) == "hands: over · depth-aware"
    assert G.hands_words(G.Wiring(blend="add"), S()) == "hands: over · added"
    lines = G.Wiring(hands="scene", draw="lines")
    assert G.hands_words(lines, S()) == "hands: in the scene as lines"
    assert G.hands_words(lines, S(scene=False, through=True)) == "hands: through FX as lines"
    two = G.Wiring(hands="scene", extra=(G.HandsAt(2),))
    assert G.hands_words(two, S()) == "hands: in the scene (1)"
    assert G.hands_words(two, S(scene=False)) == "hands: over (2)"
    assert G.layer_words(DEFAULT) == ""
    assert G.history_words(DEFAULT) == "history: the scene"
    assert G.history_words(G.Wiring(history="scene+hands")) == \
        "history: the scene · with the hands"
    assert G.history_words(G.Wiring(hands="scene")) == "history: the scene · with the hands"
    spec = G.read_graph(json.loads(FIXTURE.read_text())["graph"])
    assert G.graph_words(spec) == \
        "graph: hands 1 in the scene as lines · history with the hands"
    assert G.graph_words(None) == "graph: default"
    assert G.graph_words(G.read_graph({"nodes": [
        {"kind": "hands", "into": "scene"}, {"kind": "hands", "instance": 2},
        {"kind": "effect", "file": "acid", "instance": 2}]})) == \
        "graph: hands 1 in the scene · hands 2 a layer · acid ×2"


def test_the_output_pages_shows_line_says_the_wiring():
    """`ui.output_shows` under a preset's graph: an output whose scene
    holds the hands says so (no layer over it); a layer names its node,
    lines and blend; the default wiring's words are today's, unchanged."""
    from hyperspace.ui import output_shows

    assert output_shows(S(), False, True, 1.0, DEFAULT) == \
        output_shows(S(), False, True, 1.0) == ("scene + hands over the effects", "")
    lines = G.Wiring(hands="scene", draw="lines")
    assert output_shows(S(), True, True, 1.0, lines) == (
        "scene + hands: in the scene as lines", "")
    assert output_shows(S(scene=False), True, True, 1.0, lines) == ("hands as lines", "")
    assert output_shows(S(through=True), True, False, 1.0, G.Wiring(blend="depth")) == (
        "scene", "")
    assert output_shows(S(), True, True, 1.0, G.Wiring(blend="depth")) == (
        "scene + hands over the effects · depth-aware", "")
    two = G.Wiring(hands="scene", extra=(G.HandsAt(2),))
    assert output_shows(S(scene=False, through=True), True, True, 0.5, two) == (
        "hands through the effects (2) · 50%", "")
    # the scene holds the hands whatever the output's hands switch says
    # (the golden hands-lines|present|scene is the scene+hands picture):
    # the words never say "off" for hands that are in the picture
    assert output_shows(S(hands=False), True, False, 1.0, lines) == (
        "scene + hands: in the scene as lines", "")
    assert G.hands_words(lines, S(hands=False)) == "hands: in the scene as lines"
    assert G.hands_words(lines, S(scene=False, hands=False)) == "hands: off"


def test_the_lookback_page_says_what_the_history_holds():
    from types import SimpleNamespace as NS

    from hyperspace.ui_lookback import history_line

    assert history_line(None) == "history: the scene"
    assert history_line(NS(wiring=G.Wiring(history="scene+hands"))) == \
        "history: the scene · with the hands"


# ---------------------------------------------------------------- effect instances


def test_an_effect_file_whose_name_would_read_as_an_instance_is_refused(tmp_path):
    """`acid.2.glsl` (or any stem with a dot, or `2.glsl`) would read as an
    instance of the naming rule: refused before parsing, with the reason,
    never taken for an instance and never dropped by `set_instances`."""
    from hyperspace.fx import FX_DIR

    (tmp_path / "acid.glsl").write_text((FX_DIR / "acid.glsl").read_text())
    (tmp_path / "acid.2.glsl").write_text((FX_DIR / "acid.glsl").read_text())
    (tmp_path / "2.glsl").write_text((FX_DIR / "acid.glsl").read_text())
    fx = FxState(tmp_path)
    assert set(fx.specs) == {"acid"}
    assert "instance" in fx.errors["acid.2"] and "instance" in fx.errors["2"]
    assert fx.set_instances({"acid": 2}) == {"acid.2"}
    assert fx.specs["acid.2"].label.endswith(" 2") and fx.specs["acid.2"].name == "acid"
    fx.load()                                  # a re-scan: the instance stays the instance
    assert set(fx.specs) == {"acid", "acid.2"} and "instance" in fx.errors["acid.2"]


def test_a_purely_decimal_param_key_is_refused_at_the_source():
    """The guard A0 asked for: `u_2` would make `fx.<file>.2`, which the
    naming rule reads as the second instance — the file does not load."""
    src = "uniform float u_2; // @param 0 1 0.5 \"Two\"\nvec4 effect(vec2 uv) { return vec4(0); }"
    with pytest.raises(SpecError, match="instance number"):
        parse("bad", src)
    assert instance_of_name("acid.2") == 2 and instance_of_name("acid") is None
    assert instance_of_name("acid.1") is None and instance_of_name("acid.x") is None


def _registry(fx=None):
    from types import SimpleNamespace as NS

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState

    chain = Analyzer(Analyser())
    return build_registry(ViewState(), Control(chain), NS(chain=chain), None,
                          fx=fx if fx is not None else FxState())


def test_a_second_acid_is_its_own_params_clock_and_place_in_the_chain():
    """`FxState.set_instances({"acid": 2})`: the effect `acid.2` — the
    acid file's spec labelled "Acid 2", its own values, clock and order —
    declared as `fx.acid.2.*` (performance params, so a preset carries
    them); the first acid keeps `fx.acid.*`. A re-declare of the acid file
    (a hot edit) never drops the second's; going back to one drops them."""
    from hyperspace.fx import declare
    from hyperspace.params import instance_of, part_of

    fx = FxState()
    reg = _registry(fx)
    assert reg.fx_state is fx
    first = [p.id for p in reg if p.id.startswith("fx.acid.")]
    changed = fx.set_instances({"acid": 2})
    assert changed == {"acid.2"}
    declare(reg, fx, changed)
    second = [p.id for p in reg if p.id.startswith("fx.acid.2.")]
    assert sorted(second) == sorted(pid.replace("fx.acid.", "fx.acid.2.") for pid in first)
    assert all(instance_of(pid, "fx.acid") == (2, pid.split(".", 3)[3]) for pid in second)
    assert reg["fx.acid.2.mix"].label == "Acid 2 mix" and part_of(reg["fx.acid.2.mix"]) == \
        "performance"
    assert fx.specs["acid.2"].name == "acid" and fx.file_of("acid.2") == "acid"
    # its own values and clock
    reg["fx.acid.2.twist"].set(1.7)
    assert fx.values["acid.2"]["twist"] == 1.7 and fx.values["acid"]["twist"] != 1.7
    fx.values["acid"]["on"] = fx.values["acid.2"]["on"] = True
    fx.values["acid"]["speed"], fx.values["acid.2"]["speed"] = 1.0, 2.0
    fx.phase["acid"] = fx.phase["acid.2"] = 0.0
    fx.advance(0.5)
    assert fx.phase["acid.2"] == 2 * fx.phase["acid"] > 0
    # (plan 33 T7: no order of its own — where it runs is its wires; both on,
    # a load lands them in the run by their file's @order, then by name)
    from hyperspace.graphmigrate import wiring_of
    assert wiring_of(fx).run == ("acid", "acid.2")
    assert "fx.acid.2.order" not in reg
    # a hot edit re-declares the acid file: the second keeps its ids
    declare(reg, fx, {"acid"})
    assert "fx.acid.2.twist" in reg and reg["fx.acid.2.twist"].value == 1.7
    # the file reloaded from disk keeps the instance (FxState.load)
    fx.load()
    assert "acid.2" in fx.specs and fx.values["acid.2"]["twist"] == 1.7
    # back to one: its params go, the first's stay
    changed = fx.set_instances({})
    declare(reg, fx, changed)
    assert changed == {"acid.2"} and not [p for p in reg if p.id.startswith("fx.acid.2.")]
    assert all(pid in reg for pid in first) and "acid.2" not in fx.values


# ---------------------------------------------------------------- the preset


class Stub:
    """What `GraphSection.attach` hands the wiring to (a renderer)."""

    def __init__(self):
        self.wiring, self.ghost_states = G.Wiring(), {}


def _fixture_in(home: Path) -> None:
    dst = home / "presets" / FIXTURE.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(FIXTURE.read_text())


def test_no_factory_preset_carries_a_graph_and_each_loads_as_before(tmp_path):
    """Every factory preset loads with the default graph, no graph note,
    a document with no `graph` key and a clean dot; no file under the
    library has one (no preset is edited or added in this run)."""
    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    for path in sorted((FACTORY / "presets").glob("*.json")):
        assert "graph" not in json.loads(path.read_text()), path.name
    for slug in preset.FACTORY_PRESETS:
        rig.lib.load(PRESETS, slug)
        name = rig.lib.current(PRESETS)
        assert not [n for n in rig.presets.notes if n.startswith("graph")], slug
        # plan 33 T3: the run as wires, the file's section (none) kept
        assert rig.presets.graph.doc is None and _bare(stub.wiring) == DEFAULT
        assert _old(stub.wiring).run is not None and stub.wiring.wired
        assert preset.GRAPH_KEY not in rig.presets.document(name)
        # (plan 33 T3: the dirty dot reads the section as wires — the run)
        assert json.loads(rig.presets.signature()[4])["frame"] == "wired"     # (plan 35)
        assert not rig.lib.is_dirty(PRESETS), slug


def test_the_proof_preset_loads_its_graph_from_a_scratch_library(tmp_path):
    """`hands-lines` (a fixture, never a factory preset): its graph lands
    — the hands in the scene as lines, the history holding them — on the
    attached renderer, the acid on, the look-back on; nothing missing, no
    note, a clean dot; a save writes the section back as the file has it,
    one node per line."""
    rig = boot(tmp_path)
    _fixture_in(rig.home)
    stub = Stub()
    rig.presets.graph.attach(stub)
    missing = rig.lib.load(PRESETS, "hands-lines")
    assert missing == [] and rig.presets.notes == []
    # (plan 35: the hands are in the scene, so what the look-back records is
    # the scene — the capture wire `scene → lookback.capture` says both
    # `holds` would, the hands already in its picture)
    assert _bare(stub.wiring) == G.Wiring(hands="scene", draw="lines")
    assert G.Wire("scene", "lookback.capture") in stub.wiring.wires
    assert _old(stub.wiring).run == ("acid",)          # plan 33 T3: its run, as wires
    assert rig.reg["fx.acid.on"].value and rig.reg["dream.on"].value
    assert not rig.lib.is_dirty(PRESETS)
    doc = rig.presets.document("hands-lines")
    assert doc[preset.GRAPH_KEY] == json.loads(FIXTURE.read_text())["graph"]
    text = preset.dumps(doc)
    assert '"graph": {"nodes": [\n  {"kind": "hands", "into": "scene", "draw": "lines"},\n' \
        in text
    # another preset with no graph: back to the default, the section gone
    rig.lib.load(PRESETS, "party-tumble")
    assert _bare(stub.wiring) == DEFAULT and rig.presets.graph.doc is None


def test_an_unknown_node_kind_is_a_note_and_the_default_graph(tmp_path):
    """A section this build cannot read never stops the load: the values
    land, the graph is the default, the note says why, and a save keeps
    the section as the file had it (a newer build's nodes are not lost)."""
    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    section = {"nodes": [{"kind": "teapot", "spout": 3}, {"kind": "hands", "into": "scene"}]}
    put(rig.home, "Odd", values={"view.bright": 3.0}, graph=section)
    rig.lib.load(PRESETS, "Odd")
    assert rig.reg["view.bright"].value == 3.0
    assert stub.wiring == DEFAULT and rig.presets.graph.spec is None
    note = rig.presets.notes[0]
    assert note.startswith("graph: unknown node kind 'teapot'") and \
        note.endswith("; the default graph")
    assert rig.presets.document("Odd")[preset.GRAPH_KEY] == section
    assert not rig.lib.is_dirty(PRESETS)


def test_a_preset_says_two_acids_in_data_and_carries_the_seconds_values(tmp_path):
    """The proof of the naming rule for effects: a preset whose graph
    holds the acid twice carries `fx.acid.2.*` in its values, which land
    once the graph has (they are not unknown); the first acid keeps
    `fx.acid.*`; a preset without the second drops its params; a save
    round-trips both."""
    rig = boot(tmp_path)
    graph = {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}]}
    put(rig.home, "Twice", graph=graph, values={
        "fx.on": True, "fx.acid.on": True, "fx.acid.twist": 0.3,
        "fx.acid.2.on": True, "fx.acid.2.twist": 1.9, "fx.acid.2.order": 70})
    missing = rig.lib.load(PRESETS, "Twice")
    reg = rig.reg
    assert missing == [] and rig.presets.notes == []
    assert reg["fx.acid.twist"].value == 0.3 and reg["fx.acid.2.twist"].value == 1.9
    assert G.run_of(rig.presets.graph.spec, "lookback", "output.all.image") == ("acid", "acid.2")
    assert not rig.lib.is_dirty(PRESETS)
    doc = rig.presets.document("Twice")
    assert doc["graph"] == graph and doc["values"]["fx.acid.2.twist"] == 1.9
    # an id of an instance the graph does not hold is unknown, as ever
    put(rig.home, "Stray", values={"fx.acid.3.twist": 1.0})
    assert rig.lib.load(PRESETS, "Stray") == ["fx.acid.3.twist"]
    assert "fx.acid.2.twist" not in reg and G.run_of(rig.presets.graph.spec, "lookback", "output.all.image") == ()
    rig.lib.load(PRESETS, "Twice")
    assert reg["fx.acid.2.twist"].value == 1.9


def test_a_second_hands_node_gets_its_own_session_params_and_state(tmp_path):
    """`ghost.2.*`: the naming rule's same group, so the session's (a
    preset never sets them; one that names them is noted); its own
    `GhostState`, handed to the renderer for the second node's Ghost and
    kept while the app runs, so the node's settings come back with it."""
    from hyperspace.params import part_of

    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    put(rig.home, "Glass", graph={"nodes": [{"kind": "hands", "into": "scene"},
                                            {"kind": "hands", "instance": 2}]},
        values={"ghost.2.alpha": 0.2})
    rig.lib.load(PRESETS, "Glass")
    reg = rig.reg
    assert part_of(reg["ghost.2.alpha"]) == "session" and reg["ghost.2.alpha"].label == \
        "Ghost 2 opacity"
    assert rig.presets.notes == ["ghost.2.alpha is the session's, ignored"]
    state = stub.ghost_states["ghost.2"]
    reg["ghost.2.mirror"].set(True)
    assert state.mirror and not reg["ghost.mirror"].value
    assert stub.wiring.extra == (G.HandsAt(2),)
    rig.lib.load(PRESETS, "party-tumble")
    assert "ghost.2.mirror" not in reg and stub.ghost_states == {}
    rig.lib.load(PRESETS, "Glass")
    assert reg["ghost.2.mirror"].value is True and stub.ghost_states["ghost.2"] is state


def test_a_load_refused_for_a_value_puts_the_graph_back(tmp_path):
    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    _fixture_in(rig.home)
    rig.lib.load(PRESETS, "hands-lines")
    before = stub.wiring
    put(rig.home, "Bad", graph={"nodes": [{"kind": "effect", "file": "acid", "instance": 2}]},
        values={"fx.acid.2.twist": "fast"})
    with pytest.raises(Exception, match="would not land"):
        rig.lib.load(PRESETS, "Bad")
    assert stub.wiring == before and "fx.acid.2.twist" not in rig.reg


def test_an_instance_id_is_sorted_against_the_graph_the_load_lands(tmp_path):
    """Review fix: with a second acid landed, a preset whose graph does not
    hold it (no section, or one that fell back) and whose values name
    `fx.acid.2.*` loads, the ids unknown — never a KeyError after the old
    graph was dropped. And anything that raises after the graph landed
    puts the old graph back with its instances' values."""
    from hyperspace.library import LibraryError

    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    reg = rig.reg
    twice = {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}]}
    put(rig.home, "Twice", graph=twice, values={"fx.acid.2.twist": 1.9})
    put(rig.home, "Plain", values={"fx.acid.2.twist": 0.5, "view.bright": 3.0})
    put(rig.home, "Newer", graph={"nodes": [{"kind": "cloud", "role": "kinect"}]},
        values={"fx.acid.2.twist": 0.5})
    for other in ("Plain", "Newer"):
        rig.lib.load(PRESETS, "Twice")
        assert reg["fx.acid.2.twist"].value == 1.9
        missing = rig.lib.load(PRESETS, other)
        assert missing == ["fx.acid.2.twist"] and rig.lib.current(PRESETS) == other
        gs = rig.presets.graph            # (plan 33 T3: Plain's spec is its bare run)
        assert "fx.acid.2.twist" not in reg and (gs.spec is None or not gs.spec.effect_counts())
        assert any("unknown id(s): fx.acid.2.twist" in n for n in rig.presets.notes)
    # a raise after the graph landed (not a value error): the graph that
    # was there comes back, with its instances' values, and the load stops
    rig.lib.load(PRESETS, "Twice")
    real = rig.lib.resolved

    def boom(group, values):
        raise KeyError("boom")
    rig.lib.resolved = boom
    try:
        with pytest.raises((KeyError, LibraryError)):
            rig.lib.load(PRESETS, "Plain")
    finally:
        rig.lib.resolved = real
    assert reg["fx.acid.2.twist"].value == 1.9 and rig.presets.graph.spec is not None
    assert rig.reg.fx_state.instances == {"acid": 2} and rig.lib.current(PRESETS) == "Twice"


def test_a_second_hands_nodes_settings_survive_reopening_the_show(tmp_path):
    """Review fix: a show restores its session before its startup preset
    declares `ghost.2`; the node is seeded from the show's session when it
    is first declared, so its settings come back, no unknown id is said,
    and the show is clean. A preset without the node then keeps them in
    the show (a save does not drop them, nor counts them as an edit)."""
    from hyperspace.library import PROJECT_SUFFIX, PROJECTS

    rig = boot(tmp_path)
    put(rig.home, "Glass", graph={"nodes": [{"kind": "hands", "into": "scene"},
                                            {"kind": "hands", "instance": 2}]})
    session = {"ghost.2.on": True, "ghost.2.mirror": True, "ghost.2.alpha": 0.3,
               "ghost.2.style": 3}
    show = rig.home / PROJECTS / f"rig{PROJECT_SUFFIX}"
    show.parent.mkdir(parents=True, exist_ok=True)
    show.write_text(json.dumps({"schema": "hyperspace.project/2", "name": "rig",
                                "startup": "Glass", "bank": ["Glass"],
                                "session": session, "modules": {}}))
    rig.lib.warning = ""
    missing = rig.lib.project.load("rig")
    reg = rig.reg
    assert missing == [] and "unknown" not in rig.lib.warning
    assert rig.lib.current(PRESETS) == "Glass"
    assert {pid: reg[pid].value for pid in session} == session
    state = rig.presets.graph.states["ghost.2"]
    assert state.on and state.mirror and state.style == 3
    assert not rig.lib.project.is_dirty()
    # a preset without the node: the show still holds its settings, clean
    rig.lib.load(PRESETS, "party-tumble")
    assert "ghost.2.on" not in reg and not rig.lib.project.is_dirty()
    rig.lib.project.save()
    saved = json.loads(show.read_text())["session"]
    assert {pid: saved[pid] for pid in session} == session
    # a change made live is the live one when the node comes back in this run
    rig.lib.load(PRESETS, "Glass")
    reg["ghost.2.alpha"].set(0.8)
    rig.lib.load(PRESETS, "party-tumble")
    rig.lib.load(PRESETS, "Glass")
    assert reg["ghost.2.alpha"].value == 0.8
    # opening the show again brings its own settings back
    rig.lib.load(PRESETS, "party-tumble")
    rig.lib.project.load("rig")
    assert reg["ghost.2.alpha"].value == 0.3 and not rig.lib.project.is_dirty()


def test_undoing_a_load_puts_the_graph_back_before_the_values(tmp_path):
    """The marks carry the graph (`library.Marks`): undoing a load of a
    preset with a second acid takes its params away again, and redoing it
    brings them back with their values."""
    from test_undo import boot as undo_boot
    from test_undo import settle

    rig = undo_boot(tmp_path / "home")
    stub = Stub()
    rig.presets.graph.attach(stub)
    put(rig.home, "Twice", graph={"nodes": [{"kind": "effect", "file": "acid", "instance": 2},
                                            {"kind": "hands", "into": "scene"}]},
        values={"fx.acid.2.twist": 1.9})
    settle(rig)
    rig.undo.clear()
    rig.lib.load(PRESETS, "Twice")
    settle(rig)
    assert rig.reg["fx.acid.2.twist"].value == 1.9 and _old(stub.wiring).hands == "scene"
    assert rig.undo.undo()
    assert "fx.acid.2.twist" not in rig.reg and _bare(stub.wiring) == DEFAULT
    assert rig.undo.redo()
    assert rig.reg["fx.acid.2.twist"].value == 1.9 and _old(stub.wiring).hands == "scene"


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def test_two_acids_run_in_one_chain_on_one_program(ctx):
    """The second acid is a pass of its own in the chain (its own mix and
    clock) on the file's one compiled program; the frame differs from one
    acid's."""
    import numpy as np
    from test_outputs import rig, run, views

    from hyperspace.graphmigrate import wiring_of

    one = rig(ctx, effects=("acid",), hands=False)
    a = run(ctx, one, views(ctx, S()))[0]
    two = rig(ctx, effects=("acid",), hands=False)
    fx = two.fx.state
    fx.set_instances({"acid": 2})
    fx.values["acid.2"].update(on=True, twist=1.5)
    two.wiring = wiring_of(fx)                   # plan 33 R23: both in the run
    b = run(ctx, two, views(ctx, S()))[0]
    assert two.stats["chain_runs"] == 1 and not np.array_equal(a, b)
    assert list(two.fx._progs) == ["acid"] and two.wiring.run == ("acid", "acid.2")
    # the second acid's own params act: the same rig twice, only
    # acid.2's twist changed (acid's values untouched) — another frame
    first = dict(fx.values["acid"])

    def frame(twist):
        r = rig(ctx, effects=("acid",), hands=False)
        st = r.fx.state
        st.set_instances({"acid": 2})
        st.values["acid"].update(first)
        st.values["acid.2"].update(on=True, twist=twist)
        r.wiring = wiring_of(st)
        return run(ctx, r, views(ctx, S()))[0], st

    c, st_c = frame(0.2)
    d, st_d = frame(1.8)
    assert st_c.values["acid"] == st_d.values["acid"] == first
    assert not np.array_equal(c, d)


def test_a_second_hands_node_is_its_own_ghost_on_the_glass(ctx):
    """`ghost` in the scene on the projector, `ghost.2` laid over the
    glass: two Ghosts, the second over its own state (`ghost_states`),
    following the first's tracker; the glass shows the second's picture
    (its own opacity), the projector the hands in its scene; each has a
    time on the SYSTEM page, the second instance's layer included; the
    second Ghost goes with a graph that no longer holds it."""
    import numpy as np
    from test_outputs import rig, run, views

    from hyperspace.ghost import GhostState
    from hyperspace.render import PassTimer

    r = rig(ctx, effects=())
    st2 = GhostState(on=True, alpha=0.25)
    r.ghost_states = {"ghost.2": st2}
    r.wiring = G.Wiring(hands="scene", extra=(G.HandsAt(2),))
    vs = views(ctx, S(), S(scene=False))
    pics = run(ctx, r, vs, frames=PassTimer.LAG + 3)
    g2 = r.ghost_of("ghost.2")
    assert g2 is not r.ghost and g2.state is st2 and g2.source is r.ghost.source
    assert r.stats["in_scene"] and r.stats["layer"]
    # the glass: the second Ghost's layer at its own 0.25, not the first's 1.0
    ref = rig(ctx, effects=(), alpha=0.25)
    want = run(ctx, ref, views(ctx, S(scene=False)))[0]
    assert np.array_equal(pics[1], want)
    if r.timer.on:
        assert {"ghost", "scene", "hands.2"} <= set(r.stats["gpu_ms"])
    assert "ghost.2" not in r._graph.timed            # its time is its layer's line
    # back to one hands node: the second Ghost is released with its graph
    r.wiring = G.Wiring()
    run(ctx, r, vs, frames=1)
    assert "ghost.2" not in r._ghosts


def test_hands_as_lines_draw_their_edges(ctx):
    """A hands node drawn as lines: inside the scene and as a layer the
    hands are their meshes' edges (`ctx.wireframe`) — another picture
    than the solid hands, in the same place, and the wireframe is off
    again after (the shape's own passes never see it)."""
    import numpy as np
    from test_outputs import rig, run, views

    def pic(wiring, sw):
        r = rig(ctx, effects=())
        r.wiring = wiring
        return run(ctx, r, views(ctx, sw))[0], r

    for sw, flag in ((S(scene=False), "layer"), (S(), "in_scene")):
        solid, _ = pic(G.Wiring(hands="scene"), sw)
        lines, r = pic(G.Wiring(hands="scene", draw="lines"), sw)
        assert r.stats[flag] and not np.array_equal(solid, lines)
        drawn = lambda p: p[..., :3].sum(axis=2) > 30
        both = (drawn(solid) & drawn(lines)).sum()
        assert both > 0.5 * drawn(solid).sum()                 # where the hands are
        # the edges: inside a solid hand some pixels are the ground now
        assert (drawn(solid) & ~drawn(lines)).sum() > 0
    assert ctx.wireframe is False


def test_the_new_ends_round_trip():
    """Plan 33 G: frame, fx.image, pattern, shape.faces, backdrop.image and
    switch.2 read and write back equal."""
    section = {"nodes": [{"kind": "switch"}, {"kind": "switch", "instance": 2}],
               "wires": [{"from": "frame", "to": "acid.image"},
                         {"from": "acid", "to": "fx.image"},
                         {"from": "media.a", "to": "switch.in1"},
                         {"from": "switch", "to": "pattern.media"},
                         {"from": "pattern", "to": "shape.faces"},
                         {"from": "media.b", "to": "switch.2.in1"},
                         {"from": "switch.2", "to": "backdrop.image"}]}
    spec = G.read_graph(section)
    assert not spec.notes
    assert spec.to_json() == section
    assert G.read_graph(spec.to_json()) == spec
