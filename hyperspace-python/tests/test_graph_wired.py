"""Plan 35 F, V2 (T1): the wired frame as words — the marker (`"frame":
"wired"`), the frame's nodes in the owner's names (`scene`, `shape`,
`backdrop`, `pattern`, `lookback`, `hands.layer`, `hands.guide`,
`channel.<c>`), copies, All outputs (`output.all`), `ground`, the reach
from the outputs and the capture, the loops through the two edges left
hidden, and the ids old and new (`NEW_IDS`, `param_prefix`). Data only:
`read_graph`, `wire_error`, `reaches`, `sink_loops`; the builder is T2's."""

from __future__ import annotations

import pytest

from hyperspace import graph as G
from hyperspace import graphmigrate as M

WIRED = {"frame": "wired"}


def wired(*pairs, nodes=()):
    return {"frame": "wired", "nodes": list(nodes),
            "wires": [{"from": a, "to": b} for a, b in pairs]}


def note(pair, words):
    return f"wire {G.Wire(*pair)} — {words}"


def test_the_marker_reads_and_round_trips():
    spec = G.read_graph(WIRED)
    assert spec.notes == ()
    assert spec.wired
    assert spec.to_json() == {"frame": "wired", "nodes": [{"kind": "hands", "laid": "over"}]}   # (plan 36 T3: hands written)
    assert not G.read_graph({}).wired
    with pytest.raises(G.GraphError) as err:
        G.read_graph({"frame": "yes"})
    assert str(err.value) == G.FRAME_VALUE.format(value="yes")


FULL_NODES = [
    {"kind": "scene"}, {"kind": "shape"}, {"kind": "backdrop"}, {"kind": "pattern"},
    {"kind": "lookback"}, {"kind": "layer", "instance": 2}, {"kind": "guide"},
    {"kind": "effect", "file": "acid"}, {"kind": "copy", "of": "acid"}]
FULL_WIRES = [
    ("shape", "scene.geometry"), ("hands", "scene.geometry"), ("scene", "backdrop.scene"),
    ("channel.a", "backdrop.image"), ("backdrop", "lookback.image"),
    ("scene", "lookback.capture"), ("lookback", "acid.image"), ("acid", "output.all.image"),
    ("lookback", "copy.image"), ("copy", "output.2.image"),
    ("hands.layer", "output.all.hands"), ("hands.layer", "output.all.guide"),
    # plan 36 T2: the edges the builder read by name, as wires
    ("pattern", "shape.faces"), ("scene.cover", "lookback.cover"),
    ("hands", "hands.layer.hands"), ("hands", "hands.guide.hands")]


def test_the_frame_kinds_read_and_round_trip():
    spec = G.read_graph(wired(*FULL_WIRES, nodes=FULL_NODES))
    assert spec.notes == ()
    assert spec.wired
    assert G.read_graph(spec.to_json()) == spec
    assert spec.to_json()["frame"] == "wired" and next(iter(spec.to_json())) == "frame"
    assert spec.frame_nodes == (G.SceneAt(), G.ShapeAt(), G.BackdropAt(), G.PatternAt(),
                                G.LookbackAt(), G.LayerAt(2), G.GuideAt())
    assert spec.copies == (G.CopyAt(1, "acid"),)
    assert [w.to_json() for w in spec.wires] == [{"from": a, "to": b} for a, b in FULL_WIRES]
    for at, name, js in ((G.SceneAt(), "scene", {"kind": "scene"}),
                         (G.ShapeAt(), "shape", {"kind": "shape"}),
                         (G.BackdropAt(), "backdrop", {"kind": "backdrop"}),
                         (G.PatternAt(), "pattern", {"kind": "pattern"}),
                         (G.LookbackAt(), "lookback", {"kind": "lookback"}),
                         (G.LayerAt(), "hands.layer", {"kind": "layer"}),
                         (G.LayerAt(3), "hands.3.layer", {"kind": "layer", "instance": 3}),
                         (G.GuideAt(), "hands.guide", {"kind": "guide"}),
                         (G.GuideAt(2), "hands.2.guide", {"kind": "guide", "instance": 2}),
                         (G.CopyAt(1, "acid"), "copy", {"kind": "copy", "of": "acid"}),
                         (G.CopyAt(2, "acid.2"), "copy.2",
                          {"kind": "copy", "of": "acid.2", "instance": 2})):
        assert at.name == name and at.to_json() == js
    assert G.SceneAt().n == G.LookbackAt().n == 1
    assert set(G.FRAME_KINDS) | {"copy"} <= set(G.DECLARED)
    assert {"copy", "ground"} <= set(G.RESERVED)


def test_a_frame_kind_is_only_in_a_wired_frame():
    for entry in ({"kind": "scene"}, {"kind": "lookback"}, {"kind": "copy", "of": "acid"}):
        with pytest.raises(G.GraphError):
            G.read_graph({"nodes": [entry]})


@pytest.mark.parametrize(("pair", "name"), [
    (("lookback", "fx.image"), "fx"),
    (("frame", "acid.image"), "frame"),
])
def test_frame_and_fx_are_gone_in_a_wired_frame(pair, name):
    spec = G.read_graph(wired(pair))
    assert spec.notes == (note(pair, G.GONE_IN_A_WIRED_FRAME.format(name=name)),)
    assert spec.wires == ()


def test_holds_and_into_are_wires_in_a_wired_frame():
    with pytest.raises(G.GraphError) as err:
        G.read_graph(wired(nodes=[{"kind": "lookback", "holds": "scene+hands"}]))
    assert str(err.value) == G.HOLDS_IS_A_WIRE
    with pytest.raises(G.GraphError) as err:
        G.read_graph(wired(nodes=[{"kind": "hands", "instance": 2, "into": "scene"}]))
    assert str(err.value) == G.INTO_IS_A_WIRE.format(hands="hands.2")
    with pytest.raises(G.GraphError) as err:
        G.read_graph(wired(nodes=[{"kind": "hands", "into": "layer"}]))
    assert str(err.value) == G.INTO_IS_A_WIRE.format(hands="hands")
    # outside a wired frame both are read as today
    spec = G.read_graph({"nodes": [{"kind": "hands", "into": "scene"},
                                   {"kind": "history", "holds": "scene+hands"}]})
    assert spec.hands[0].into == "scene" and spec.history.holds == "scene+hands"


def test_geometry_goes_into_the_scene_only():
    spec = G.read_graph(wired(("shape", "output.all.image")))
    assert spec.notes == (note(("shape", "output.all.image"),
                               "shape makes geometry, output.all.image takes a picture"),)
    spec = G.read_graph(wired(("hands", "lookback.image")))
    assert spec.notes == (note(("hands", "lookback.image"),
                               G.GEOMETRY_INTO_SCENE.format(src="hands")),)
    spec = G.read_graph(wired(("shape", "scene.geometry")))
    assert spec.notes == () and spec.wires == (G.Wire("shape", "scene.geometry"),)
    # the scene takes geometry only; a guide takes a layer or a guide
    spec = G.read_graph(wired(("channel.a", "scene.geometry")))
    assert spec.notes == (note(("channel.a", "scene.geometry"),
                               "channel.a makes a picture, scene.geometry takes geometry"),)
    assert G.read_graph(wired(("hands.guide", "output.1.guide"))).notes == ()
    assert G.read_graph(wired(("hands.layer", "output.all.guide"))).notes == ()
    assert G.read_graph(wired(("scene", "output.all.guide"))).notes != ()


def test_the_scene_takes_several_geometry_wires_in_order():
    spec = G.read_graph(wired(("hands", "scene.geometry"), ("hands.2", "scene.geometry"),
                              ("shape", "scene.geometry"),
                              nodes=[{"kind": "hands", "instance": 2}]))
    assert spec.notes == ()
    assert [w.src for w in spec.wires if w.dst == "scene.geometry"] == ["hands", "hands.2",
                                                                         "shape"]
    assert "scene.geometry" in G.MANY_PORTS
    # any other port still takes one wire
    spec = G.read_graph(wired(("scene", "output.all.image"),
                              ("channel.a", "output.all.image")))
    assert len(spec.notes) == 2 and spec.wires == ()


def test_ground_goes_only_into_outputs():
    spec = G.read_graph(wired(("ground", "output.2.image"), ("ground", "output.all.hands"),
                              ("shape", "scene.geometry"), ("scene", "output.all.image")))
    assert spec.notes == ()
    assert "ground" not in G.reaches(spec)
    spec = G.read_graph(wired(("ground", "acid.image")))
    assert spec.notes == (note(("ground", "acid.image"), G.GROUND_ONLY_INTO_OUTPUTS),)
    assert G.GROUND == "ground"


def test_a_copy_needs_an_of_and_an_instance():
    with pytest.raises(G.GraphError) as err:
        G.read_graph(wired(nodes=[{"kind": "copy", "instance": 2}]))
    assert str(err.value) == G.COPY_NO_OF.format(name="copy.2")
    spec = G.read_graph(wired(("lookback", "copy.image"), ("copy", "output.2.image"),
                              ("lookback", "output.all.image"),
                              nodes=[{"kind": "copy", "of": "teapot"}]))
    assert spec.notes == (G.COPY_BAD_OF.format(name="copy", of="teapot"),)
    assert spec.copies == ()
    assert spec.wires == (G.Wire("lookback", "output.all.image"),)
    # an of the section holds by a wire or an entry stands; a copy on a wire needs its entry
    spec = G.read_graph(wired(("lookback", "acid.2.image"), ("acid.2", "output.all.image"),
                              nodes=[{"kind": "copy", "of": "acid.2", "instance": 3}]))
    assert spec.notes == () and spec.copies == (G.CopyAt(3, "acid.2"),)
    spec = G.read_graph(wired(("lookback", "copy.image")))
    assert spec.notes == (note(("lookback", "copy.image"),
                               'no copy node in this graph (add one: {"kind": "copy"})'),)


def test_reach_runs_from_the_outputs_and_the_capture():
    assert G.reaches(G.read_graph(wired(("shape", "scene.geometry")))) == frozenset()
    assert G.reaches(G.read_graph(wired(("shape", "scene.geometry"),
                                        ("scene", "output.all.image")))) == {"shape", "scene"}
    assert G.reaches(G.read_graph(wired(("shape", "scene.geometry"),
                                        ("scene", "lookback.capture")))) == {"shape", "scene"}
    faces = [("channel.a", "pattern.media"), ("shape", "scene.geometry"),
             ("scene", "output.1.image")]
    # (plan 36 T2: the faces read the pattern by a wire, never by name)
    assert {"pattern", "channel.a"}.isdisjoint(G.reaches(G.read_graph(wired(*faces))))
    got = G.reaches(G.read_graph(wired(*faces, ("pattern", "shape.faces"))))
    assert {"pattern", "channel.a", "shape", "scene"} <= got
    got = G.reaches(G.read_graph(wired(*faces, ("channel.b", "shape.faces"))))
    assert "pattern" not in got and "channel.a" not in got and "channel.b" in got
    # a delay's input is reached only once the delay is (plan 34's rule)
    d = [{"kind": "delay"}]
    assert "lookback" not in G.reaches(G.read_graph(wired(("lookback", "delay.image"),
                                                           nodes=d)))
    assert {"delay", "lookback"} <= G.reaches(G.read_graph(wired(
        ("lookback", "delay.image"), ("delay", "output.all.image"), nodes=d)))


def test_loops_in_a_wired_frame_keep_plan_34s_words():
    spec = G.read_graph(wired(("shape", "scene.geometry"), ("scene", "shape.faces")))
    assert note(("scene", "shape.faces"),
                G.LOOP_FACES.format(path="shape → scene → shape")) in spec.notes
    assert G.Wire("scene", "shape.faces") not in spec.wires
    spec = G.read_graph(wired(("scene", "backdrop.scene"), ("backdrop", "lookback.image"),
                              ("lookback", "backdrop.image")))
    w = ("lookback", "backdrop.image")
    assert note(w, G.LOOP_BACKDROP.format(path="backdrop → lookback → backdrop")) in spec.notes
    assert G.Wire(*w) not in spec.wires
    # plan 36 T2: the cover reads the scene's faces by its drawn wire — a pin
    # of the scene, so a loop through it runs through the scene; unwired, no
    # edge is read (the old hidden edge (lookback, scene) is gone)
    loop = (("channel.a", "lookback.image"), ("shape", "scene.geometry"),
            ("lookback", "shape.faces"))
    assert G.read_graph(wired(*loop)).notes == ()
    spec = G.read_graph(wired(*loop, ("scene.cover", "lookback.cover")))
    assert note(("lookback", "shape.faces"), G.LOOP_FACES.format(
        path="shape → scene → scene.cover → lookback → shape")) in spec.notes
    assert G.Wire("lookback", "shape.faces") not in spec.wires
    assert not hasattr(G, "HIDDEN_EDGES") and not hasattr(G, "IMPLICIT_EDGES")
    # a wire into the capture is recorded for the frames after: no loop
    spec = G.read_graph(wired(("lookback", "acid.image"), ("acid", "lookback.capture"),
                              ("acid", "output.all.image")))
    assert spec.notes == ()
    # through a delay a loop is legal, as in plan 34
    spec = G.read_graph(wired(("shape", "scene.geometry"), ("scene", "delay.image"),
                              ("delay", "shape.faces"), nodes=[{"kind": "delay"}]))
    assert spec.notes == ()


def test_loop_words_in_a_wired_frame():
    assert G.loop_words("a → b → a", {("scene", "hands")}) == (
        G.LOOP_FACES.format(path="a → b → a"))
    assert G.loop_words("a → b → a", {("lookback", "backdrop")}) == (
        G.LOOP_BACKDROP.format(path="a → b → a"))
    assert G.loop_words("a → b → a", {("acid", "b")}) == G.LOOP_PLAIN.format(path="a → b → a")


def test_outside_a_wired_frame_nothing_changes():
    """Plan 34's `tests/test_graph_feedback.py` passes unedited (the
    suite runs it); here the old ids still read as they did."""
    spec = G.read_graph({"wires": [{"from": "history", "to": "output.2.image"},
                                   {"from": "hands", "to": "output.2.hands"},
                                   {"from": "frame", "to": "fx.image"}]})
    assert spec.notes == () and not spec.wired
    assert G.wire_node_kind("hands") == "layer" and G.wire_node_kind("ghost") == "ghost"
    assert G.wire_node_kind("hands", wired=True) == "hands"
    assert G.wire_node_kind("output.all") is None
    assert G.wire_node_kind("output.all", wired=True) == "output"
    assert G.ALL_OUTPUTS == "output.all" and G.FRAME_KEY == "frame" and G.WIRED_FRAME == "wired"
    spec = G.read_graph({"wires": [{"from": "scene", "to": "output.all.image"}]})
    assert len(spec.notes) == 1 and spec.wires == ()


IDS = [("ghost", "hands"), ("ghost.2", "hands.2"), ("hands", "hands.layer"),
       ("hands.2", "hands.2.layer"), ("readout", "hands.guide"), ("readout.3", "hands.3.guide"),
       ("history", "lookback"), ("media.c", "channel.c"), ("output.2.readout", "output.2.guide")]


def test_the_ids_map_both_ways():
    assert len(G.NEW_IDS) == len(IDS)
    for old, new in IDS:
        assert G.new_id(old) == new
        assert G.old_id(new) == old
        assert G.old_id(G.new_id(old)) == old
    assert G.OLD_IDS == {v: k for k, v in G.NEW_IDS.items()}
    for same in ("acid.2", "delay", "echo.3", "dream", "shape", "scene", "pattern",
                 "backdrop", "output.2", "composite.2", "switch", "resize.2"):
        assert G.new_id(same) == same and G.old_id(same) == same
    assert G.old_id("output.all.guide") == "output.all.guide"


def test_a_nodes_params_keep_their_prefix():
    for name, prefix in (("hands", "ghost"), ("hands.2", "ghost.2"), ("hands.2.layer", "ghost.2"),
                         ("hands.guide", "ghost"), ("lookback", "dream"),
                         ("channel.a", "media.a"), ("camera", "eye"), ("acid.2", "fx.acid.2"),
                         ("pattern", "pattern"), ("backdrop", "backdrop"),
                         ("output.2", "output.2")):
        assert G.param_prefix(name) == prefix, name
    assert G.PARAM_PREFIX == {"hands": "ghost", "lookback": "dream", "channel": "media",
                              "camera": "eye"}


@pytest.mark.parametrize(("pair", "old", "new"), [
    (("history", "output.all.image"), "history", "lookback"),
    (("ghost", "scene.geometry"), "ghost", "hands"),
    (("media.a", "output.all.image"), "media.a", "channel.a"),
    (("hands.layer", "output.2.readout"), "output.2.readout", "output.2.guide"),
])
def test_an_old_id_in_a_wired_frame_is_refused(pair, old, new):
    spec = G.read_graph(wired(pair))
    assert spec.notes == (note(pair, G.OLD_ID_IN_A_WIRED_FRAME.format(old=old, new=new)),)
    with pytest.raises(G.GraphError) as err:
        G.read_graph(wired(nodes=[{"kind": "history"}]))
    assert str(err.value) == G.OLD_ID_IN_A_WIRED_FRAME.format(old="history", new="lookback")


def test_a_full_wired_frame_saves_as_it_stands(tmp_path):
    """A wired frame's words — every frame kind, a copy, a ground — load
    and save `/6` as the frame stands (row 394: every save is `/6`, so no
    frame is put back into older words), and reload the same."""
    from test_plan31_wiring import make_app

    section = wired(*FULL_WIRES, nodes=FULL_NODES)
    want = G.read_graph(section).to_json()
    app = make_app(tmp_path)
    doc = {"schema": M.WIRED_SCHEMA, "name": "full", "values": {}, "graph": section}
    assert app.presets.load_doc(doc) == []
    out = app.presets.document("full")
    assert out["schema"] == M.WIRED_SCHEMA and out["graph"] == want
    assert app.presets.load_doc(out) == [] and app.presets.document("full") == out
