"""Plan 26 A1, A3: the render graph (graph.py).

The pure half first — the module's imports, the node and port contract,
the default graph's shape for each set of switches, its order — then the
renderer's half on offscreen targets: the graph is built once per set of
switches and reused, a pipeline no view routes to does not run, the
timer lists the graph's nodes, and a hot reload rebuilds the graph. The
pixels themselves are `tests/test_golden_frames.py`'s (427 frames, byte
for byte) and `tests/test_outputs.py`'s.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hyperspace import graph as G
from hyperspace.outputs import HANDS, SCENE, SCENE_HANDS, Switches, View

# ---------------------------------------------------------------- no GL


def test_graph_imports_only_the_render_stack_and_names_no_write():
    """graph.py imports moderngl and its sibling render modules only —
    never params, routing, library, preset, undo, control, app or ui —
    and no node method is named apply, modulate, snapshot or set_value
    (the rule `test_render.py` holds render.py to)."""
    tree = ast.parse(Path(G.__file__).read_text())
    banned = {"params", "routing", "library", "preset", "undo", "control", "app", "ui",
              "overlay", "config", "midi", "bridge", "dream", "osc", "torch", "leap"}
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[-1]] + [a.name for a in node.names]
        elif isinstance(node, ast.Import):
            names = [a.name.split(".")[-1] for a in node.names]
        assert not banned & set(names), names
    called = {n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not called & {"set_value", "modulate", "apply", "snapshot"}
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert not defined & {"set_value", "modulate", "apply", "snapshot"}
    # the dependency runs one way: outputs.py imports nothing of the graph
    from hyperspace import outputs

    for node in ast.walk(ast.parse(Path(outputs.__file__).read_text())):
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[-1] != "graph", node.module
            assert "graph" not in {a.name for a in node.names}
        elif isinstance(node, ast.Import):
            assert "graph" not in {a.name.split(".")[-1] for a in node.names}


def _names(g: G.Graph) -> list[str]:
    return [n.name for n in g.order]


def _view(**kw) -> View:
    return View(Switches(**kw), (480, 320))


def test_the_default_graph_for_one_default_view_is_todays_frame_in_order():
    """One output with the default switches: the shape into the scene, the
    cover, the hands (a geometry, A3) into their own layer, the history,
    the SCENE chain, the capture, the output — every node after what it
    depends on, each name once, a geometry's time counted in whatever
    draws it (the hands' in their layer's: they are in no scene)."""
    g = G.default_graph([_view()])
    assert _names(g) == ["shape", "ghost", "scene", "cover", "hands", "history", "fx",
                         "capture", "output.1"]
    assert g.timed == ["scene", "cover", "hands", "history", "fx", "capture", "output.1"]
    assert g.key == ((True, True, False),) and g.wiring == G.Wiring()
    seen: list[G.Node] = []
    for n in g.order:
        for d in n.deps():
            assert d in seen, (n.name, d.name)
        seen.append(n)
    assert len({n.name for n in g.order}) == len(g.order)
    # the wiring: the scene from the shape, the layer from the hands, the
    # history from the scene and the cover, the chain from the history,
    # the capture from the scene, the output after the capture with the
    # SCENE pipeline on its image port and the hands' layer over it
    assert g.nodes["scene"].inputs == {"geometry": g.nodes["shape"]}
    assert g.nodes["hands"].inputs == {"geometry": g.nodes["ghost"]}
    assert g.nodes["hands"].readout == "through" and not g.nodes["ghost"].in_scene
    assert g.nodes["history"].inputs == {"image": g.nodes["scene"], "cover": g.nodes["cover"]}
    assert g.nodes["fx"].inputs == {"image": g.nodes["history"]}
    assert g.nodes["fx"].key == SCENE and g.nodes["fx"].after == (g.nodes["hands"],)
    assert g.nodes["capture"].inputs == {"image": g.nodes["scene"]}
    assert g.nodes["capture"].after == (g.nodes["fx"],)
    out = g.nodes["output.1"]
    assert out.index == 0 and out.after == (g.nodes["capture"],)
    assert out.inputs == {"image": g.nodes["fx"], "hands": g.nodes["hands"],
                          "readout": g.nodes["hands"], "depth": None}
    assert out.blend == "over" and g.outputs == [out]
    assert [n.KIND for n in g.order] == ["geometry", "geometry", "scene", "layer", "layer",
                                         "history", "fx", "history", "output"]
    assert "Graph(shape → ghost → scene" in repr(g) and repr(g.nodes["fx"]).startswith("fx('fx'")


def test_pipelines_of_follows_the_route_table():
    """The pipelines a set of switches can reach (`outputs.route`): the
    scene for any view showing it; the hands onto the scene for a view
    with the scene and the hands through; the hands alone for one with
    the scene off and the hands through. The through switch without the
    hands reaches nothing extra."""
    S = Switches
    assert G.pipelines_of([S()]) == [SCENE]
    assert G.pipelines_of([S(hands=False)]) == [SCENE]
    assert G.pipelines_of([S(through=True)]) == [SCENE, SCENE_HANDS]
    assert G.pipelines_of([S(scene=False, through=True)]) == [HANDS]
    assert G.pipelines_of([S(scene=False)]) == []
    assert G.pipelines_of([S(scene=False, hands=False)]) == []
    assert G.pipelines_of([S(hands=False, through=True)]) == [SCENE]
    assert G.pipelines_of([S(scene=False, hands=False, through=True)]) == []
    assert G.pipelines_of([S(through=True), S(scene=False, through=True)]) == [
        SCENE, SCENE_HANDS, HANDS]
    assert G.pipelines_of([S(scene=False, through=True), S()]) == [SCENE, HANDS]


def test_the_default_graph_has_a_pipeline_per_reachable_route_and_hands_only_when_shown():
    S = Switches
    g = G.default_graph([View(S(through=True), (10, 10)), View(S(scene=False, through=True),
                                                               (10, 10))])
    assert _names(g) == ["shape", "ghost", "scene", "cover", "hands", "history", "fx",
                         "composite(scene+hands)", "fx(scene+hands)", "composite(hands)",
                         "fx(hands)", "capture", "output.1", "output.2"]
    assert g.nodes["composite(scene+hands)"].inputs == {"under": g.nodes["history"],
                                                       "over": g.nodes["hands"], "depth": None}
    assert g.nodes["composite(hands)"].inputs == {"under": None, "over": g.nodes["hands"],
                                                 "depth": None}
    assert g.nodes["composite(hands)"].blend == "over"
    assert g.nodes["fx(hands)"].key == HANDS and g.nodes["fx(scene+hands)"].key == SCENE_HANDS
    assert g.nodes["capture"].after == tuple(g.nodes[n] for n in ("fx", "fx(scene+hands)",
                                                                  "fx(hands)"))
    # each output's image port is its pipeline's end; through, the hands
    # go before the effects, so no layer over; a through end that is not
    # bent this frame stands down for its fallback (the scene's, or the ground)
    o1, o2 = g.nodes["output.1"], g.nodes["output.2"]
    assert o1.inputs["image"] is g.nodes["fx(scene+hands)"] and o1.inputs["hands"] is None
    assert o2.inputs["image"] is g.nodes["fx(hands)"] and o2.inputs["hands"] is None
    assert o1.inputs["readout"] is o2.inputs["readout"] is g.nodes["hands"]
    assert g.nodes["fx(scene+hands)"].fallback is g.nodes["fx"]
    assert g.nodes["fx(hands)"].fallback is None and g.nodes["fx"].layer is None
    assert g.nodes["fx(hands)"].layer is g.nodes["hands"]
    # no view shows the hands: no hands at all, nothing wired to them
    g = G.default_graph([View(S(hands=False), (10, 10))])
    assert _names(g) == ["shape", "scene", "cover", "history", "fx", "capture", "output.1"]
    assert g.nodes["output.1"].inputs["hands"] is g.nodes["output.1"].inputs["readout"] is None
    # nothing shown at all: the once-a-frame nodes and the output alone
    g = G.default_graph([View(S(scene=False, hands=False), (10, 10))])
    assert _names(g) == ["shape", "scene", "cover", "history", "capture", "output.1"]
    assert g.nodes["capture"].after == ()


def test_graph_key_is_the_views_switches_and_nothing_else():
    S = Switches
    a = View(S(), (10, 10))
    b = View(S(), (999, 5), viewport=(1, 2, 3, 4), bg_alpha=0.0, presenter=object())
    assert G.graph_key([a]) == G.graph_key([b]) == ((True, True, False),)
    assert G.graph_key([a, View(S(scene=False, through=True), (1, 1))]) == (
        (True, True, False), (False, True, True))
    # the dim and the flips are read when the nodes run, not in the key
    assert G.graph_key([View(S(dim=0.2, flip_x=True, flip_y=True), (1, 1))]) == G.graph_key([a])
    assert G.graph_key([]) == ()


def test_ports_are_typed_and_the_graph_checks_its_wiring():
    """A port takes nodes of its type only; an unknown port, a dependency
    outside the graph and a second node of one name are refused."""
    g = G.Graph()
    shape = g.add(G.Shape("shape"))
    scene = g.add(G.Scene("scene", geometry=shape))
    cover = g.add(G.Cover("cover", scene=scene))
    assert (scene.OUTPUT, cover.OUTPUT, shape.OUTPUT) == (G.IMAGE, G.MASK, G.GEOMETRY)
    with pytest.raises(TypeError, match="takes image, 'cover' makes mask"):
        G.History("history", image=cover, cover=cover)
    with pytest.raises(TypeError, match="takes mask"):
        G.History("history", image=scene, cover=scene)
    with pytest.raises(ValueError, match="no port \\['picture'\\]"):
        G.History("history", picture=scene)
    with pytest.raises(ValueError, match="two nodes named 'scene'"):
        g.add(G.Scene("scene", geometry=shape))
    loose = G.Scene("loose", geometry=G.Shape("other"))
    with pytest.raises(ValueError, match="'loose' depends on 'other', not in the graph"):
        g.add(loose)
    # an input left None is allowed (the ground under a composite)
    c = G.Composite("c", under=None, over=scene)
    assert c.inputs == {"under": None, "over": scene, "depth": None} and c.deps() == [scene]
    with pytest.raises(ValueError, match="blend 'screen'"):
        G.Composite("c", blend="screen", over=scene)
    # a scene takes any number of geometries, one port each
    two = G.Scene("two", geometries=[G.Hands("h"), G.Shape("s")])
    assert list(two.inputs) == ["geometry", "geometry.2"]
    assert two.inputs["geometry"].in_scene and two.inputs["geometry"].TIMED
    assert G.Capture("capture", image=scene, after=(cover,)).deps() == [scene, cover]
    assert _names(g) == ["shape", "scene", "cover"]


def test_order_puts_dependencies_first_and_ties_in_insertion_order():
    """A node added before its consumer but after an unrelated one keeps
    its place; a node whose dependency was added later still runs after
    it."""
    g = G.Graph()
    shape = g.add(G.Shape("shape"))
    scene = g.add(G.Scene("scene", geometry=shape))
    hands = g.add(G.HandsLayer("hands"))
    cover = g.add(G.Cover("cover", scene=scene))
    history = g.add(G.History("history", image=scene, cover=cover))
    fx = g.add(G.Fx("fx", SCENE, after=(hands,), image=history))
    g.add(G.Output("output.1", 0, after=(fx,), image=fx, hands=hands))
    assert _names(g) == ["shape", "scene", "hands", "cover", "history", "fx", "output.1"]
    assert g.timed == ["scene", "hands", "cover", "history", "fx", "output.1"]


def test_the_wiring_is_checked_and_its_default_is_todays_frame():
    assert G.Wiring() == G.Wiring("layer", "over", "scene")
    for bad in ({"hands": "glass"}, {"blend": "multiply"}, {"history": "fx"}):
        with pytest.raises(ValueError, match="wiring"):
            G.Wiring(**bad)
    # the same switches under another wiring are another graph
    a = G.default_graph([_view()])
    b = G.default_graph([_view()], G.Wiring(blend="depth"))
    assert a.key == b.key and a.wiring != b.wiring


def test_the_hands_in_the_scene_are_its_first_geometry_and_a_glass_still_gets_the_layer():
    """`Wiring(hands="scene")`: the scene holds the hands (solid, first)
    and the shape; an output with the scene shows them there — no layer
    over it, no SCENE+HANDS pipeline — and its readout; an output without
    the scene (the glass) gets the hands' layer, over or through, with
    the guide split out of it always (it must never ride the scene)."""
    S = Switches
    w = G.Wiring(hands="scene")
    g = G.default_graph([View(S(through=True), (10, 10)), View(S(scene=False), (10, 10)),
                         View(S(scene=False, through=True), (10, 10))], w)
    assert _names(g) == ["shape", "ghost", "scene", "cover", "hands", "history", "fx",
                         "composite(hands)", "fx(hands)", "capture", "output.1", "output.2",
                         "output.3"]
    scene, ghost = g.nodes["scene"], g.nodes["ghost"]
    assert scene.inputs == {"geometry": ghost, "geometry.2": g.nodes["shape"]}
    assert ghost.in_scene and g.timed[:2] == ["ghost", "scene"]
    assert g.nodes["hands"].readout == "always"
    o1, o2, o3 = (g.nodes[f"output.{k}"] for k in (1, 2, 3))
    assert o1.inputs["image"] is g.nodes["fx"] and o1.inputs["hands"] is None
    assert o1.inputs["readout"] is g.nodes["hands"]
    assert o2.inputs["image"] is None and o2.inputs["hands"] is g.nodes["hands"]
    assert o3.inputs["image"] is g.nodes["fx(hands)"] and o3.inputs["hands"] is None
    # the scene alone shows the hands: no layer, the readout on its own
    g = G.default_graph([_view()], w)
    assert _names(g) == ["shape", "ghost", "scene", "cover", "readout", "history", "fx",
                         "capture", "output.1"]
    assert g.nodes["output.1"].inputs["readout"] is g.nodes["readout"]
    assert g.timed == ["ghost", "scene", "cover", "readout", "history", "fx", "capture",
                       "output.1"]


def test_the_history_is_wired_to_the_scene_or_the_scene_with_the_hands():
    """`Wiring.history`: the capture takes the scene (today), or a
    composite of the hands' layer over the scene — with the layer's blend,
    and the layer drawn even when no output lays it on."""
    g = G.default_graph([_view()])
    assert g.nodes["capture"].inputs["image"] is g.nodes["scene"]
    g = G.default_graph([_view()], G.Wiring(history="scene+hands", blend="depth"))
    held = g.nodes["capture"].inputs["image"]
    assert held is g.nodes["composite(history)"] and held.blend == "depth"
    assert held.inputs == {"under": g.nodes["scene"], "over": g.nodes["hands"],
                           "depth": g.nodes["scene"]}
    g = G.default_graph([_view(hands=False)], G.Wiring(history="scene+hands"))
    assert "hands" in g.nodes and g.nodes["output.1"].inputs["hands"] is None
    # with the hands in the scene the scene holds them already
    g = G.default_graph([_view()], G.Wiring(hands="scene", history="scene+hands"))
    assert g.nodes["capture"].inputs["image"] is g.nodes["scene"]


def test_depth_aware_wiring_hands_each_composite_and_output_the_scenes_depth():
    S = Switches
    g = G.default_graph([View(S(), (1, 1)), View(S(through=True), (1, 1))],
                        G.Wiring(blend="depth"))
    c = g.nodes["composite(scene+hands)"]
    assert c.blend == "depth" and c.inputs["depth"] is g.nodes["scene"]
    for k in (1, 2):
        o = g.nodes[f"output.{k}"]
        assert o.blend == "depth" and o.inputs["depth"] is g.nodes["scene"]


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


def test_the_graph_is_built_once_per_set_of_switches_and_reused(ctx):
    """Frames with the same switches evaluate one Graph object; a changed
    switch builds another; the same switches again build again (no cache
    beyond the last graph); a hot reload drops it; a renderer from
    before the graph gets one."""
    from test_outputs import rig, run, views

    S = Switches
    r = rig(ctx)
    assert r._graph is None
    vs = views(ctx, S(), S(hands=False))
    run(ctx, r, vs, frames=3)
    g1 = r._graph
    assert g1 is not None and g1.key == ((True, True, False), (True, False, False))
    run(ctx, r, vs, frames=2)
    assert r._graph is g1                                   # reused
    vs[1].switches.through = True
    run(ctx, r, vs, frames=1)
    assert r._graph is not g1 and r._graph.key == ((True, True, False), (True, False, True))
    r.on_reload()
    assert r._graph is None
    run(ctx, r, vs, frames=1)
    assert r._graph is not None
    del r._graph                                            # from before A1
    run(ctx, r, vs, frames=1)
    assert isinstance(r._graph, G.Graph)
    # a renderer carrying A0's timer through a live reload: `end_frame`
    # took no names and the pending frames had another shape. The timer is
    # not a reload target, so the renderer drops it for a fresh one — on
    # `on_reload`, and again if one of another class turns up without it
    from hyperspace.render import PassTimer

    class OldTimer:
        on, note, freed = True, "", False

        def time(self, name):
            raise AssertionError("an old timer must never be asked")

        def end_frame(self):                          # A0's signature
            raise AssertionError("an old timer must never end a frame")

        def _off(self, e):
            self.freed = True

    old = r.timer = OldTimer()
    r.on_reload()
    assert r.timer is None and old.freed
    run(ctx, r, vs, frames=2)
    assert type(r.timer) is PassTimer
    old = r.timer = OldTimer()                        # re-classed, no on_reload
    run(ctx, r, vs, frames=2)
    assert type(r.timer) is PassTimer and old.freed


def test_a_pipeline_no_view_routes_to_this_frame_does_not_run(ctx):
    """The graph for an output with the hands through holds the
    SCENE+HANDS pipeline whether or not a hand shows; which pipeline runs
    is the route's, per frame: with no hand the SCENE chain alone runs
    (one chain run, as before), with a hand the SCENE+HANDS one."""
    from test_outputs import rig, run, views

    S = Switches
    for hands in (False, True):
        r = rig(ctx, hands=hands)
        run(ctx, r, views(ctx, S(through=True)), frames=2)
        assert "fx(scene+hands)" in r._graph.nodes and "fx" in r._graph.nodes
        assert r.stats["pipelines"] == [SCENE_HANDS if hands else SCENE]
        assert r.stats["chain_runs"] == 1 and r.stats["layer"] is hands
        assert r.stats["direct"] is True


def test_the_timer_lists_the_graphs_nodes_and_drops_a_node_that_left(ctx):
    """The medians are keyed by node, in the graph's order; a node of one
    frame's graph that the next graph lacks leaves the medians once its
    frame has been read back (LAG frames later)."""
    from test_outputs import rig, run, views

    from hyperspace.render import PassTimer

    S = Switches
    r = rig(ctx)
    if not r.timer.on:
        pytest.skip(f"this context has no timer queries: {r.timer.note}")
    vs = views(ctx, S(through=True))
    run(ctx, r, vs, frames=PassTimer.LAG + 2)
    assert list(r.stats["gpu_ms"]) == r._graph.timed
    assert "fx(scene+hands)" in r.stats["gpu_ms"] and "composite(scene+hands)" in r.stats["gpu_ms"]
    vs[0].switches.through = False
    run(ctx, r, vs, frames=PassTimer.LAG + 1)
    assert list(r.stats["gpu_ms"]) == r._graph.timed == [
        "scene", "cover", "hands", "history", "fx", "capture", "output.1"]


def test_a_made_image_paints_itself_one_to_one(ctx):
    """`Node.paint` for a node that made a texture (the default): the
    scene's texture shown 1:1 into a framebuffer is the scene's bytes."""
    import numpy as np
    from test_outputs import H, W, fbo, rig, run, views

    S = Switches
    r = rig(ctx, effects=())
    run(ctx, r, views(ctx, S()), frames=1)
    want = np.frombuffer(r.scene.tex.read(), dtype=np.uint8)
    frame = G.Frame(r, ctx, None, W, H, 1.0, 2.0, [], (W, H), 0, r.scene.fbo, (0, 0, W, H))
    out = fbo(ctx)
    out.use()
    ctx.viewport = (0, 0, W, H)
    r._graph.nodes["scene"].paint(frame, out)
    assert np.array_equal(np.frombuffer(out.read(components=4), dtype=np.uint8), want)
    assert r._graph.nodes["history"].image(frame) is None     # painted, never made
    assert r._graph.nodes["scene"].image(frame) is r.scene.tex
    out.release()
