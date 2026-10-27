"""Plan 36 T2 (W2): every hidden edge is a port and a drawn, saved,
deletable cable.

| was read by name                 | now a wire                                  | unwired      |
|----------------------------------|---------------------------------------------|--------------|
| the shape read `pattern`         | `pattern → shape.faces`                     | plain faces  |
| the cover built from the scene   | `scene.cover → lookback.cover` (a mask)     | no occlusion |
| a layer / guide read `hands`     | `hands → hands.layer.hands` / `.guide.hands`| empty        |
| clouds injected into the scene   | `cloud → scene.geometry` (the rig's)        | no cloud     |
| `depth` auto-wired, one `blend`  | `scene.depth → composite.depth` / an output's, `laid` the layer's | no depth |

Per row: unwired behaves as the table says; wired reproduces what the
builder read by name; the migration (`graphmigrate.drawn_edges`) adds the
wire to a `/4`–`/6` frame; the canvas draws it. The goldens are the proof
that the migrated frames draw what they drew (tests/test_golden_frames.py)."""

from __future__ import annotations

import pytest

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace import graphview
from hyperspace.outputs import Switches, View
from hyperspace.params import Registry
from hyperspace.routing import Bindings

SIZE = (240, 150)
# (plan 36 T4: the look-back records the scene and its trail is shown)
FRAME = [("shape", "scene.geometry"), ("scene", "lookback.image"),
         ("lookback", "output.all.image"), ("hands.layer", "output.all.hands"),
         ("hands.layer", "output.all.guide")]
# the same frame in the words before T4 (a `/6` file's: the look-back laid
# over `lookback.image`, recording `lookback.capture`) — a migration's input
OLD_FRAME = [*FRAME, ("scene", "lookback.capture")]
TRACERS = {"dream.on": True, "dream.mix": 0.0}      # an old file's look-back on, no dream


def wired(*pairs, nodes=()):
    return {"frame": "wired", "nodes": list(nodes),
            "wires": [{"from": a, "to": b} for a, b in pairs]}


def spec_of(*pairs, nodes=()):
    spec = G.read_graph(wired(*pairs, nodes=nodes))
    assert spec.notes == (), spec.notes
    return spec


def build(spec, n=1, clouds=(), rig=None, effects=()):
    return G.build_graph([View(Switches(), SIZE) for _ in range(n)], spec.wiring(),
                         tuple(clouds), tuple(effects), rig)


def view_of(spec, g, rig=None):
    return graphview.build(Bindings(), Registry(), None, None, g, spec, rig=rig)


def cable(view, src: str, dst: str):
    got = [c for c in view.cables if c.kind == "render" and c.src_port == f"rout:{src}"
           and c.dst_port == "rin:{}/{}".format(*dst.rsplit(".", 1))]
    assert len(got) == 1, (src, dst, [(c.src_port, c.dst_port) for c in view.cables
                                      if c.kind == "render"])
    return got[0]


def migrated(section: dict | None = None, values: dict | None = None) -> dict:
    doc = {"values": dict(values or {}), **({"graph": section} if section is not None else {})}
    out, notes = M.seven(doc, {})
    assert not notes, notes
    return out["graph"]


def pairs_of(section: dict) -> list[tuple[str, str]]:
    return [(w["from"], w["to"]) for w in section["wires"]]


def test_the_edge_tables_are_gone():
    """Nothing reads an edge no wire says: the tables and their loop words
    are deleted, and loops are found over the drawn wires alone."""
    for name in ("HIDDEN_EDGES", "IMPLICIT_EDGES", "FRAME_EDGES", "LOOP_FRAME", "sink_loops"):
        assert not hasattr(G, name), name


# ---------------------------------------------------------------- the faces' pattern

def test_unwired_faces_are_plain_and_read_no_pattern():
    g = build(spec_of(*FRAME))
    assert "pattern" not in g.nodes and g.nodes["shape"].inputs["faces"] is None
    assert g.nodes["shape"].pattern() is None
    # a pattern the section declares is not read by name either
    g = build(spec_of(*FRAME, nodes=[{"kind": "pattern"}]))
    assert "pattern" not in g.nodes


def test_wired_faces_read_their_pattern_by_the_wire():
    g = build(spec_of(*FRAME, ("pattern", "shape.faces"), ("channel.a", "pattern.media")))
    shape, pattern = g.nodes["shape"], g.nodes["pattern"]
    assert shape.inputs["faces"] is pattern and shape.pattern() is pattern
    assert pattern.channel == "a"
    # through effects too: the media layer is the pattern node the faces lead back to
    g = build(spec_of(*FRAME, ("pattern", "acid.image"), ("acid", "shape.faces")),
              effects=("acid",))
    assert g.nodes["shape"].pattern() is g.nodes["pattern"]


def test_the_migration_wires_the_faces_pattern():
    assert ("pattern", "shape.faces") in pairs_of(migrated())
    # a /6 wired frame from before T2 gains it on load …
    assert ("pattern", "shape.faces") in pairs_of(migrated(wired(*FRAME)))
    # … but never over a wire of its own into the faces
    got = pairs_of(migrated(wired(*FRAME, ("channel.b", "shape.faces"))))
    assert [p for p in got if p[1] == "shape.faces"] == [("channel.b", "shape.faces")]
    # (twice is once)
    sec = migrated(wired(*FRAME))
    assert M.drawn_edges(sec) is sec


def test_the_canvas_draws_the_faces_pattern_cable():
    spec = G.read_graph(migrated())
    c = cable(view_of(spec, build(spec)), "pattern", "shape.faces")
    assert c.ref == G.Wire("pattern", "shape.faces") and c.type == graphview.IMAGE


def test_plain_faces_draw_no_pattern_and_the_wire_draws_it(ctx, rig):
    """GL: with a pattern on, the faces wired `pattern → shape.faces` draw
    it; unwired the same frame draws plain faces — another picture."""
    from test_graph_frame import _draw, _land

    rig.reg["view.pattern"].set(3)
    rig.reg["view.pattern_mix"].set(1.0)
    _land(rig, migrated())
    patterned, = _draw(ctx, rig, [Switches()])
    assert G.Wire("pattern", "shape.faces") in rig.renderer.wiring.wires
    _land(rig, M.drawn_edges(wired(*FRAME)) | {"wires": [
        w for w in M.drawn_edges(wired(*FRAME))["wires"] if w["to"] != "shape.faces"]})
    plain, = _draw(ctx, rig, [Switches()])
    assert patterned[..., :3].max() > 20 and not (patterned == plain).all()


# ---------------------------------------------------------------- the look-back's cover

def test_unwired_the_look_back_has_no_cover():
    g = build(spec_of(*FRAME))
    assert g.nodes["lookback"].inputs["cover"] is None
    assert "lookback(cover)" not in g.nodes


def test_wired_the_cover_is_the_scenes_faces_mask():
    g = build(spec_of(*FRAME, ("scene.cover", "lookback.cover")))
    cover = g.nodes["lookback(cover)"]
    assert isinstance(cover, G.Cover) and cover.inputs["scene"] is g.nodes["scene"]
    assert g.nodes["lookback"].inputs["cover"] is cover
    # a pin of the scene: it reaches the scene, and goes into the cover port alone
    assert {"scene", "scene.cover"} <= G.reaches(spec_of(*FRAME, ("scene.cover",
                                                                  "lookback.cover")))
    spec = G.read_graph(wired(*FRAME, ("scene.cover", "acid.image"), ("acid", "output.1.image")))
    assert spec.notes == ("wire scene.cover → acid.image — scene.cover is "
                          + G.PIN_WORDS["scene.cover"],)
    spec = G.read_graph(wired(*FRAME, ("scene", "lookback.cover")))
    assert spec.notes == (("wire scene → lookback.cover — scene makes a picture, "
                           "lookback.cover takes a mask"),)


def test_the_migration_wires_the_cover_where_both_are_reached():
    assert ("scene.cover", "lookback.cover") in pairs_of(migrated(values=TRACERS))
    # no look-back reached: no cover
    got = pairs_of(migrated(wired(("shape", "scene.geometry"), ("scene", "output.all.image"))))
    assert ("scene.cover", "lookback.cover") not in got


def test_the_canvas_draws_the_cover_cable_from_the_scenes_pin():
    spec = G.read_graph(migrated(values=TRACERS))
    view = view_of(spec, build(spec))
    c = cable(view, "scene.cover", "lookback.cover")
    assert c.type == graphview.MASK
    scene = next(n for n in view.nodes if n.id == "render:scene")
    assert {"rout:scene.cover", "rout:scene.depth"} <= {p.id for p in scene.ports}
    assert "render:scene.cover" not in {n.id for n in view.nodes}


# ---------------------------------------------------------------- the hands' layer and guide

def test_unwired_a_layer_and_a_guide_are_empty():
    g = build(spec_of(*FRAME))
    layer = g.nodes["hands.layer"]
    assert layer.inputs["geometry"] is None and "hands" not in g.nodes
    spec = spec_of(*FRAME[:3], ("hands.guide", "output.all.guide"))
    g = build(spec)
    assert g.nodes["hands.guide"].inputs["geometry"] is None
    assert "hands" in graphview.unreached(spec)


def test_wired_a_layer_draws_its_hands_and_the_guide_splits_out_of_it():
    g = build(spec_of(*FRAME, ("hands", "hands.layer.hands")))
    assert g.nodes["hands.layer"].inputs["geometry"] is g.nodes["hands"]
    spec = spec_of(*FRAME[:4], ("hands.guide", "output.all.guide"),
                   ("hands", "hands.layer.hands"), ("hands", "hands.guide.hands"))
    g = build(spec)
    assert g.outputs[0].inputs["readout"] is g.nodes["hands.layer"]     # one pass, as ever
    # a guide drawing other hands than its layer's is its own
    spec = spec_of(*FRAME[:4], ("hands.guide", "output.all.guide"),
                   ("hands", "hands.layer.hands"), ("hands.2", "hands.guide.hands"),
                   nodes=[{"kind": "hands", "instance": 2}])
    g = build(spec)
    guide = g.outputs[0].inputs["readout"]
    assert isinstance(guide, G.Readout) and guide.inputs["geometry"] is g.nodes["hands.2"]
    # only a hands node goes in
    got = G.read_graph(wired(*FRAME, ("shape", "hands.layer.hands")))
    assert got.notes == ("wire shape → hands.layer.hands — "
                         + G.LAYER_TAKES_HANDS.format(dst="hands.layer.hands"),)


def test_the_migration_wires_each_layer_and_guide_its_hands():
    got = pairs_of(migrated({"nodes": [{"kind": "hands", "into": "scene"}]}))
    assert ("hands", "hands.guide.hands") in got
    assert ("hands", "hands.layer.hands") not in got          # (no such layer here)
    got = pairs_of(migrated(wired(*OLD_FRAME, ("hands.2.layer", "output.2.hands"),
                                  nodes=[{"kind": "hands", "instance": 2}])))
    assert {("hands.2", "hands.2.layer.hands"), ("hands", "hands.layer.hands")} <= set(got)
    # a layer whose hands node the section lacks is left to the read's words
    got = pairs_of(migrated(wired(*OLD_FRAME, nodes=[{"kind": "layer", "instance": 3}])))
    assert ("hands.3", "hands.3.layer.hands") not in got


def test_the_canvas_draws_the_hands_cable():
    spec = G.read_graph(migrated())
    c = cable(view_of(spec, build(spec)), "hands", "hands.layer.hands")
    assert c.type == graphview.GEOMETRY


def test_an_unwired_layer_draws_nothing_on_the_golden_rig(ctx, rig):
    """GL, hands present: the layer with its hands wire draws them; without
    it, nothing — the frame is the one with no hands laid over at all."""
    from test_graph_frame import _draw, _land

    _land(rig, migrated(wired(*OLD_FRAME), values=TRACERS))
    lit, = _draw(ctx, rig, [Switches()])
    assert rig.renderer.stats["layer"]
    # (plan 36 T4: the scene shown straight — a look-back drawn is on, and
    # its trail would grow between the two draws)
    plain = [("shape", "scene.geometry"), ("scene", "output.all.image")]
    _land(rig, wired(*plain, *FRAME[3:], ("pattern", "shape.faces")))
    empty, = _draw(ctx, rig, [Switches()])
    assert not rig.renderer.stats["layer"]
    _land(rig, wired(*plain, ("pattern", "shape.faces")))
    bare, = _draw(ctx, rig, [Switches()])
    assert (empty == bare).all() and not (lit == bare).all()


# ---------------------------------------------------------------- the rig's clouds

def test_a_cloud_is_in_the_scene_by_the_rigs_wire_and_cut_it_is_not():
    spec = G.read_graph(migrated())
    g = build(spec, clouds=("scan", "desk"))
    clouds = [n for n in g.nodes["scene"].geometries() if isinstance(n, G.PointCloud)]
    assert [c.name for c in clouds] == ["cloud", "cloud.2"]
    assert G.cloud_wires(("scan", "desk")) == (G.Wire("cloud", "scene.geometry"),
                                               G.Wire("cloud.2", "scene.geometry"))
    rig = G.RigWires().cutting(G.cloud_wire(0))
    g = build(spec, clouds=("scan", "desk"), rig=rig)
    clouds = [n for n in g.nodes["scene"].geometries() if isinstance(n, G.PointCloud)]
    assert [c.name for c in clouds] == ["cloud.2"]
    assert G.is_rig(G.cloud_wire(1)) and not G.is_rig(G.Wire("hands", "scene.geometry"))
    # (a show from before T2 cut nothing: every cloud's wire stands)
    assert G.RigWires.read({}).present(G.cloud_wires(("scan",))) == (G.cloud_wire(0),)
    assert G.RigWires.read(rig.to_json()) == rig


def test_the_canvas_draws_the_clouds_wire_and_a_cut_one_is_gone():
    spec = G.read_graph(migrated())
    view = view_of(spec, build(spec, clouds=("scan",)))
    c = cable(view, "cloud", "scene.geometry")
    assert c.ref == G.cloud_wire(0) and c.type == graphview.GEOMETRY and not c.dormant
    rig = G.RigWires().cutting(G.cloud_wire(0))
    view = view_of(spec, build(spec, clouds=("scan",), rig=rig), rig)
    assert not [c for c in view.cables if c.ref == G.cloud_wire(0)]
    assert "render:cloud" in {n.id for n in view.nodes}                 # to join again


def test_the_clouds_wire_is_cut_and_joined_on_graph(tmp_path):
    from test_plan36_bus import _party

    app, e, pushed = _party(tmp_path)
    spec = app.presets.graph.spec
    before = spec.to_json()
    g = G.build_graph([View(Switches(), SIZE)], spec.wiring(), ("scan",), (),
                      G.rig_of(app.lib.project))
    c = cable(graphview.build(Bindings(), Registry(), None, None, g, spec),
              "cloud", "scene.geometry")
    assert e.unwire(c) is None and app.lib.project.rig.cut == {G.cloud_wire(0)}
    assert app.presets.graph.spec.to_json() == before and app.lib.project.is_dirty()
    assert e.wire("rout:cloud", "rin:scene/geometry") is None
    assert app.lib.project.rig.cut == frozenset() and len(pushed) == 2
    assert e.wire("rout:cloud", "rin:lookback/image") == graphview.CLOUD_INTO_SCENE.format(
        cloud="cloud")


# ---------------------------------------------------------------- depth and blend

DEPTH_HANDS = [{"kind": "hands", "laid": "depth"}]


def test_unwired_a_depth_composite_and_an_output_test_no_depth():
    spec = spec_of(*FRAME, ("scene", "composite.under"), ("hands.layer", "composite.over"),
                   ("composite", "output.2.image"), ("hands", "hands.layer.hands"),
                   nodes=[*DEPTH_HANDS, {"kind": "composite", "blend": "depth"}])
    g = build(spec, n=2)
    assert g.nodes["composite"].inputs["depth"] is None
    assert g.outputs[0].inputs["depth"] is None and g.outputs[0].blend == "depth"


def test_wired_the_scenes_depth_goes_to_a_composite_and_an_output():
    spec = spec_of(*FRAME, ("scene", "composite.under"), ("hands.layer", "composite.over"),
                   ("composite", "output.2.image"), ("hands", "hands.layer.hands"),
                   ("scene.depth", "composite.depth"), ("scene.depth", "output.all.depth"),
                   nodes=[*DEPTH_HANDS, {"kind": "composite", "blend": "depth"}])
    g = build(spec, n=2)
    scene = g.nodes["scene"]
    assert g.nodes["composite"].inputs["depth"] is scene
    # each window by the bus cable from All outputs' depth
    assert g.outputs[0].inputs["depth"] is scene and g.outputs[1].inputs["depth"] is scene
    cut = G.RigWires().cutting(G.bus_wire(1, "depth"))
    assert build(spec, n=2, rig=cut).outputs[0].inputs["depth"] is None
    # only the scene's depth goes into a depth port
    got = G.read_graph(wired(*FRAME, ("scene", "output.all.depth")))
    assert got.notes == ("wire scene → output.all.depth — "
                         + G.DEPTH_TAKES.format(dst="output.all.depth"),)


def test_blend_is_each_composites_own_and_laid_the_layers():
    """No global blend: a composite blended depth-aware with its depth wired
    tests it whatever the hands' `laid` says; `laid` is how its own
    layer is laid on at an output — another picture on the hands port is
    laid plain over."""
    spec = spec_of(*FRAME, ("scene", "composite.under"), ("hands.layer", "composite.over"),
                   ("composite", "output.1.image"), ("scene.depth", "composite.depth"),
                   ("hands", "hands.layer.hands"),
                   nodes=[{"kind": "composite", "blend": "depth"}])
    g = build(spec)
    assert spec.laid == "over" and g.nodes["composite"].inputs["depth"] is g.nodes["scene"]
    assert g.nodes["composite"].blend == "depth" and g.outputs[0].blend == "over"
    spec = spec_of(*FRAME[:3], ("scene", "output.all.hands"), nodes=DEPTH_HANDS)
    assert build(spec).outputs[0].blend == "over"


def test_the_migration_wires_the_depth_for_laid_depth():
    got = pairs_of(migrated({"nodes": [{"kind": "hands", "laid": "depth"},
                                       {"kind": "history", "holds": "scene+hands"}]}))
    assert ("scene.depth", "composite.depth") in got
    assert ("scene.depth", "output.all.depth") in got
    assert not [p for p in pairs_of(migrated()) if p[0] == "scene.depth"]
    # a window's own hands wire takes its own depth wire
    got = pairs_of(migrated({"nodes": [{"kind": "hands", "laid": "depth"}],
                             "wires": [{"from": "hands", "to": "output.2.hands"}]}))
    assert {("hands.layer", "output.2.hands"), ("scene.depth", "output.2.depth")} <= set(got)


def test_through_on_a_depth_laid_frame_wires_its_composites_depth():
    spec = G.read_graph(migrated({"nodes": [{"kind": "hands", "laid": "depth"}],
                                  "wires": [{"from": "frame", "to": "acid.image"},
                                            {"from": "acid", "to": "fx.image"}]}))
    got = M.through_wires(spec, 1)
    comp = next(e for e in got if e.get("kind") == "composite")
    assert comp["blend"] == "depth"
    name = "composite" if comp.get("instance", 1) == 1 else f"composite.{comp['instance']}"
    assert {"from": "scene.depth", "to": f"{name}.depth"} in got


def test_the_canvas_draws_the_depth_cables():
    spec = G.read_graph(migrated({"nodes": [{"kind": "hands", "laid": "depth"},
                                            {"kind": "history", "holds": "scene+hands"}]}))
    view = view_of(spec, build(spec))
    cable(view, "scene.depth", "composite.depth")
    cable(view, "scene.depth", "output.all.depth")
    bus = cable(view, "output.all.depth", "output.1.depth")
    assert bus.ref == G.bus_wire(1, "depth")
    # an effect does not go onto a depth cable
    e = graphview.Edit(graph=None, push=None)
    assert graphview._cable_ends(e, ("rout:scene.depth", "rin:composite/depth"))[2] is not None


# ---------------------------------------------------------------- the old loops

def test_an_old_sections_loop_through_its_frame_is_left_out_by_the_migration():
    doc, notes = M.migrate({"values": {}, "graph": {"wires": [
        {"from": "scene", "to": "pattern.media"}]}}, {})
    assert notes == ["wire scene → pattern.media — " + G.LOOP_FACES.format(
        path="pattern → shape → scene → pattern")]
    assert ("pattern", "shape.faces") in pairs_of(doc["graph"])


@pytest.fixture(scope="module")
def ctx():
    try:
        import moderngl

        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


@pytest.fixture
def rig(ctx):
    from test_graph_frame import _tool

    got = _tool().Rig("legacy6", "present", ctx)
    yield got
    got.close()
