"""Plan 26 A1, A3: the render graph (graph.py).

The pure half first — the module's imports, the node and port contract,
the frame's shape for each set of states, its order — then the renderer's
half on offscreen targets: the graph is built once per count of windows
and reused, an end no window takes this frame does not run, the timer
lists the graph's nodes, and a hot reload rebuilds the graph.

Plan 35 T4: the pipelines are gone — every frame is `build_graph`'s from
wires (an unwired `Wiring` wired first, `graph.wired`), the render nodes
named in the new ids, and a state that put the hands through is its
output's wiring (`tests/wiredframe.py`). The
pixels themselves are `tests/test_golden_frames.py`'s (427 frames, byte
for byte) and `tests/test_outputs.py`'s.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from wiredframe import Shows, Thru, graph, wire_switches

from hyperspace import graph as G
from hyperspace.graphmigrate import wired_wiring
from hyperspace.outputs import Switches, View

# ---------------------------------------------------------------- no GL


def test_the_pipelines_are_gone():
    """Plan 35 T4 (row 377): no pipeline is left — the switch half of the
    default graph, its ends, its names and the through switch went; every
    frame is `build_graph`'s from wires."""
    from hyperspace import outputs

    for name in ("pipelines_of", "FX_NAMES", "COMPOSITE_NAMES", "HISTORY_COMPOSITE",
                 "GROUNDED", "Fx", "Wired", "default_graph", "effect_node_name"):
        assert not hasattr(G, name), name
    for name in ("route", "PIPELINES", "SCENE", "SCENE_HANDS", "HANDS", "NAMES"):
        assert not hasattr(outputs, name), name
    assert not hasattr(Switches(), "through")


def test_no_preset_draws_the_factory_frame():
    """Plan 35 T4: the factory look is `frame_wires(read_graph({}))`,
    signature for signature. Plan 36 T3 (W3): only the one-way migration
    writes it (`graphmigrate.wired_wiring` of the old words, `Wiring()`);
    nothing landed is the empty frame — the outputs alone — and a wired
    wiring is itself."""
    from hyperspace import graphmigrate as M

    entries, wires = M.frame_wires(G.read_graph({}))
    # (plan 36 T2: with the hidden edges' wires, `drawn_edges`; T4: its
    # look-back split as the old words' off had it — none drawn)
    factory = G.read_graph(M.split_lookback(M.drawn_edges(
        {"frame": "wired", "nodes": entries, "wires": wires}), "off")).wiring()
    one = [View(Switches(), (10, 10))]
    want = G.signature(G.build_graph(one, wired_wiring(factory)))
    assert G.signature(G.build_graph(one, wired_wiring(G.Wiring()))) == want
    assert [n.name for n in G.build_graph(one, None).order] == ["output.1"]
    assert wired_wiring(factory) is factory and not hasattr(G, "wired")


def test_graph_imports_only_the_render_stack_and_names_no_write():
    """graph.py imports moderngl and its sibling render modules only —
    never params, routing, library, preset, undo, control, app or ui —
    and no node method is named apply, modulate, snapshot or set_value
    (the rule `test_render.py` holds render.py to)."""
    tree = ast.parse(Path(G.__file__).read_text())
    banned = {"params", "routing", "library", "preset", "undo", "control", "app", "ui",
              "overlay", "config", "midi", "bridge", "dream", "osc", "torch", "leap",
              "segment", "Vision"}
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
    """One output, the factory frame with its look-back drawn
    (`graphmigrate.wired_wiring`, the old words' on: plan 36 T4) — the
    shape into the scene, the cover, the hands (a geometry, A3) into their
    own layer, the look-back, the composite adding it onto the scene, its
    end, the capture, the output — every node after what it depends on,
    each name once, in the new ids (plan 35 T4), a geometry's time counted
    in whatever draws it (the hands' in their layer's: they are in no
    scene)."""
    g = G.build_graph([_view()], wired_wiring(G.Wiring(), "trail"))
    assert _names(g) == ["pattern", "shape", "hands", "scene", "lookback(cover)", "hands.layer",
                         "lookback", "composite", "shown(composite)", "lookback(capture)",
                         "output.1"]
    assert g.timed == ["scene", "lookback(cover)", "hands.layer", "lookback", "composite",
                       "shown(composite)", "lookback(capture)", "output.1"]
    assert g.key == (1,) and g.wiring == wired_wiring(G.Wiring(), "trail")
    seen: list[G.Node] = []
    for n in g.order:
        for d in n.deps():
            assert d in seen, (n.name, d.name)
        seen.append(n)
    assert len({n.name for n in g.order}) == len(g.order)
    # the wiring: the scene from the shape, the layer from the hands, the
    # look-back held back by the scene and the cover, the composite adding
    # it onto the scene, the end from the composite, the capture from the
    # scene, the output after the capture with the end on its image port
    # and the hands' layer over it
    assert g.nodes["scene"].inputs == {"geometry": g.nodes["shape"]}
    assert g.nodes["hands.layer"].inputs == {"geometry": g.nodes["hands"]}
    assert g.nodes["hands.layer"].readout == "downstream" and "hands" not in g.in_scene()
    assert g.nodes["lookback"].inputs == {"occluder": g.nodes["scene"],
                                          "cover": g.nodes["lookback(cover)"]}
    comp = g.nodes["composite"]
    assert comp.blend == "add" and comp.inputs == {
        "under": g.nodes["scene"], "over": g.nodes["lookback"], "depth": None}
    end = g.nodes["shown(composite)"]
    assert end.inputs == {"image": comp}
    assert end.after == (g.nodes["hands.layer"],)
    assert g.nodes["lookback(capture)"].inputs == {"image": g.nodes["scene"]}
    out = g.nodes["output.1"]
    assert out.index == 0 and out.after == (g.nodes["lookback(capture)"],)
    assert out.inputs == {"image": end, "hands": g.nodes["hands.layer"],
                          "readout": g.nodes["hands.layer"], "depth": None}
    assert out.blend == "over" and g.outputs == [out]
    assert [n.KIND for n in g.order] == ["pattern", "geometry", "geometry", "scene", "layer",
                                         "layer", "history", "composite", "shown", "history",
                                         "output"]
    assert "Graph(pattern → shape → hands → scene" in repr(g)


def test_a_through_output_is_a_composite_and_its_end():
    """Plan 35 T4 (row 377): the hands through the effects are an output's
    wiring — a composite laying the layer over the look-back (or over
    nothing, the picture muted); the hands only where some output's wiring
    lays them. Plan 36 T1: its end is always itself (no stand-down, so no
    end for the look-back no window shows) and the composite is told the
    window it is for (`mute_hands`). Plan 36 T4: the look-back drawn (the
    old words' on) — the trail added onto the scene, `composite.3`."""
    g = graph([Shows(through=True), Shows(scene=False, through=True)], look="trail")
    assert _names(g) == ["pattern", "shape", "hands", "scene", "lookback(cover)", "hands.layer",
                         "lookback", "composite.3", "composite", "shown(composite)",
                         "composite.2", "shown(composite.2)", "lookback(capture)",
                         "output.1", "output.2"]
    assert g.nodes["composite"].inputs == {"under": g.nodes["composite.3"],
                                           "over": g.nodes["hands.layer"], "depth": None}
    assert g.nodes["composite.2"].inputs == {"under": None, "over": g.nodes["hands.layer"],
                                             "depth": None}
    assert g.nodes["composite.2"].blend == "over"
    assert g.nodes["lookback(capture)"].after[:2] == tuple(
        g.nodes[n] for n in ("shown(composite)", "shown(composite.2)"))
    assert g.nodes["composite"].mute_hands == (0,)
    assert g.nodes["composite.2"].mute_hands == (1,)
    # each output's image port is its end; through, the hands go before the
    # effects, so no layer over
    o1, o2 = g.nodes["output.1"], g.nodes["output.2"]
    assert o1.inputs["image"] is g.nodes["shown(composite)"] and o1.inputs["hands"] is None
    assert o2.inputs["image"] is g.nodes["shown(composite.2)"] and o2.inputs["hands"] is None
    assert o1.inputs["readout"] is o2.inputs["readout"] is g.nodes["hands.layer"]
    # an output wired to show no hands: nothing wired to its ports (the layer
    # is All outputs' still, and a window wired to nothing shows its ground)
    g = graph([Shows(hands=False)])
    assert g.nodes["output.1"].inputs["hands"] is g.nodes["output.1"].inputs["readout"] is None
    g = graph([Shows(scene=False, hands=False)])
    assert g.nodes["output.1"].inputs == {"image": None, "hands": None, "readout": None,
                                          "depth": None}
    # nothing wired at all: the outputs and nothing else (Review Focus 2)
    g = G.build_graph([_view()], wired_wiring(G.read_graph({"frame": "wired"}).wiring()))
    assert _names(g) == ["output.1"]


def test_graph_key_is_the_views_count_and_nothing_else():
    """Plan 35 B (row 379): a window's mutes, size and look are read when
    its nodes run — the key is how many windows there are."""
    S = Switches
    a = View(S(), (10, 10))
    b = View(S(scene=False, hands=False), (999, 5), viewport=(1, 2, 3, 4), bg_alpha=0.0,
             presenter=object())
    assert G.graph_key([a]) == G.graph_key([b]) == (1,)
    assert G.graph_key([a, b]) == (2,)
    assert G.graph_key([View(S(dim=0.2, flip_x=True, flip_y=True), (1, 1))]) == G.graph_key([a])
    assert G.graph_key([]) == (0,)


def test_ports_are_typed_and_the_graph_checks_its_wiring():
    """A port takes nodes of its type only; an unknown port, a dependency
    outside the graph and a second node of one name are refused."""
    g = G.Graph()
    shape = g.add(G.Shape("shape"))
    scene = g.add(G.Scene("scene", geometry=shape))
    cover = g.add(G.Cover("cover", scene=scene))
    assert (scene.OUTPUT, cover.OUTPUT, shape.OUTPUT) == (G.IMAGE, G.MASK, G.GEOMETRY)
    with pytest.raises(TypeError, match="takes image, 'cover' makes mask"):
        G.History("history", occluder=cover, cover=cover)
    with pytest.raises(TypeError, match="takes mask"):
        G.History("history", occluder=scene, cover=scene)
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
    # A4: a geometry's time is its scene's call (the consumer edge): the
    # node itself is never told it is in a scene
    assert not two.inputs["geometry"].TIMED and two.inputs["geometry"].SOLID
    assert G.Capture("capture", image=scene, after=(cover,)).deps() == [scene, cover]
    assert _names(g) == ["shape", "scene", "cover"]


def test_order_puts_dependencies_first_and_ties_in_insertion_order():
    """A node added before its consumer but after an unrelated one keeps
    its place; a node whose dependency was added later still runs after
    it."""
    g = G.Graph()
    shape = g.add(G.Shape("shape"))
    scene = g.add(G.Scene("scene", geometry=shape))
    hands = g.add(G.HandsLayer("hands.layer"))
    cover = g.add(G.Cover("lookback(cover)", scene=scene))
    history = g.add(G.History("lookback", occluder=scene, cover=cover))
    end = g.add(G.Shown("shown(lookback)", after=(hands,), image=history))
    g.add(G.Output("output.1", 0, after=(end,), image=end, hands=hands))
    assert _names(g) == ["shape", "scene", "hands.layer", "lookback(cover)", "lookback",
                         "shown(lookback)", "output.1"]
    assert g.timed == ["scene", "hands.layer", "lookback(cover)", "lookback", "shown(lookback)",
                       "output.1"]


def test_the_wiring_is_checked_and_its_default_is_todays_frame():
    assert G.Wiring() == G.Wiring("layer", "over", "scene")
    for bad in ({"hands": "glass"}, {"blend": "multiply"}, {"history": "fx"}):
        with pytest.raises(ValueError, match="wiring"):
            G.Wiring(**bad)
    # the same windows under another wiring are another graph
    a = G.build_graph([_view()], wired_wiring(G.Wiring()))
    b = G.build_graph([_view()], wired_wiring(G.Wiring(blend="depth")))
    assert a.key == b.key and a.wiring != b.wiring


def test_the_hands_in_the_scene_are_its_first_geometry_and_a_glass_still_gets_the_layer():
    """`Wiring(hands="scene")`: the scene holds the hands (solid, first)
    and the shape; an output with the scene shows them there — no layer
    over it, no composite of its own — and its guide; an output without
    the scene (the glass) gets the hands' layer, over or through, with
    the guide split out of it always (it must never ride the scene)."""
    w = G.Wiring(hands="scene")
    # (plan 36 T4: the old words' look-back off — none drawn)
    g = graph([Shows(through=True), Shows(scene=False), Shows(scene=False, through=True)], w)
    assert _names(g) == ["pattern", "shape", "hands", "scene", "hands.layer", "shown(scene)",
                         "composite", "shown(composite)", "output.1", "output.2", "output.3"]
    scene, hands = g.nodes["scene"], g.nodes["hands"]
    assert scene.inputs == {"geometry": hands, "geometry.2": g.nodes["shape"]}
    assert g.in_scene() == {"hands"} and g.timed[:2] == ["hands", "scene"]
    assert g.nodes["hands.layer"].readout == "always"
    o1, o2, o3 = (g.nodes[f"output.{k}"] for k in (1, 2, 3))
    assert o1.inputs["image"] is g.nodes["shown(scene)"] and o1.inputs["hands"] is None
    assert o1.inputs["readout"] is g.nodes["hands.layer"]
    assert o2.inputs["image"] is None and o2.inputs["hands"] is g.nodes["hands.layer"]
    assert o3.inputs["image"] is g.nodes["shown(composite)"] and o3.inputs["hands"] is None
    # the scene alone shows the hands: no layer, the guide on its own
    g = graph([Shows()], w)
    assert _names(g) == ["pattern", "shape", "hands", "scene", "hands.guide", "shown(scene)",
                         "output.1"]
    assert g.nodes["output.1"].inputs["readout"] is g.nodes["hands.guide"]
    assert g.timed == ["hands", "scene", "hands.guide", "shown(scene)", "output.1"]


def test_the_history_is_wired_to_the_scene_or_the_scene_with_the_hands():
    """`Wiring.history`: the capture takes the scene (today), or a
    composite of the hands' layer over the scene — with the layer's blend,
    and the layer drawn even when no output lays it on."""
    g = graph([Shows()], look="trail")
    assert g.nodes["lookback(capture)"].inputs["image"] is g.nodes["scene"]
    g = graph([Shows()], G.Wiring(history="scene+hands", blend="depth"), look="trail")
    held = g.nodes["lookback(capture)"].inputs["image"]
    assert held is g.nodes["composite"] and held.blend == "depth"
    assert held.inputs == {"under": g.nodes["scene"], "over": g.nodes["hands.layer"],
                           "depth": g.nodes["scene"]}
    g = graph([Shows(hands=False)], G.Wiring(history="scene+hands"), look="trail")
    assert "hands.layer" in g.nodes and g.nodes["output.1"].inputs["hands"] is None
    # with the hands in the scene the scene holds them already
    g = graph([Shows()], G.Wiring(hands="scene", history="scene+hands"), look="trail")
    assert g.nodes["lookback(capture)"].inputs["image"] is g.nodes["scene"]
    # …even when a glass (scene off, hands on) makes the hands' layer: it
    # is never laid over a scene that holds the hands (no doubled echoes;
    # plan 36 T4: the one composite adds the trail)
    g = graph([Shows(), Shows(scene=False)], G.Wiring(hands="scene", history="scene+hands"),
              look="trail")
    assert "hands.layer" in g.nodes
    assert [c.name for c in g.nodes.values() if isinstance(c, G.Composite)] == ["composite"]
    assert g.nodes["composite"].inputs["over"] is g.nodes["lookback"]
    assert g.nodes["lookback(capture)"].inputs["image"] is g.nodes["scene"]


def test_depth_aware_wiring_hands_each_composite_and_output_the_scenes_depth():
    g = graph([Shows(), Shows(through=True)], G.Wiring(blend="depth"))
    c = g.nodes["composite"]
    assert c.blend == "depth" and c.inputs["depth"] is g.nodes["scene"]
    o1, o2 = g.nodes["output.1"], g.nodes["output.2"]
    assert o1.blend == "depth" and o1.inputs["depth"] is g.nodes["scene"]
    # (plan 36 T1: the through window lays no layer itself — its composite
    # does, depth-aware — so it reads no depth: there is no stand-down to lay for)
    assert o2.inputs["hands"] is None and o2.inputs["depth"] is None


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


def test_the_graph_is_built_once_per_set_of_switches_and_reused(ctx):
    """Frames with the same windows evaluate one Graph object; a mute
    flipped builds nothing (plan 35 B: it is read at the window); another
    wiring builds another (no cache beyond the last graph); a hot reload
    drops it; a renderer from before the graph gets one."""
    from test_outputs import rig, run, views

    S = Switches
    r = rig(ctx)
    assert r._graph is None
    vs = views(ctx, S(), S(hands=False))
    run(ctx, r, vs, frames=3)
    g1 = r._graph
    assert g1 is not None and g1.key == (2,)
    run(ctx, r, vs, frames=2)
    assert r._graph is g1                                   # reused
    vs[1].switches.scene = False
    run(ctx, r, vs, frames=1)
    assert r._graph is g1                                   # a mute: no rebuild
    wire_switches(r, S(), Thru())
    run(ctx, r, vs, frames=1)
    assert r._graph is not g1 and r._graph.key == (2,)
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


def test_a_through_window_runs_its_chain_as_wired(ctx):
    """The graph for an output wired with the hands through holds its copy
    chain and runs it whether or not a hand shows (plan 36 T1: no
    stand-down; the run's own end, which no window shows, is not built)."""
    from test_outputs import rig, run, wviews

    for hands in (False, True):
        r = rig(ctx, hands=hands)
        run(ctx, r, wviews(ctx, r, Thru()), frames=2)
        assert "shown(copy)" in r._graph.nodes and "shown(warp)" not in r._graph.nodes
        assert r.stats["ends"] == ["shown(copy)"]
        assert r.stats["chain_runs"] == 1 and r.stats["layer"] is hands
        assert r.stats["direct"] is True


def test_the_timer_lists_the_graphs_nodes_and_drops_a_node_that_left(ctx):
    """The medians are keyed by node, in the graph's order; a node of one
    frame's graph that the next graph lacks leaves the medians once its
    frame has been read back (LAG frames later)."""
    from test_outputs import rig, run, wviews

    from hyperspace.render import PassTimer

    S = Switches
    r = rig(ctx)
    if not r.timer.on:
        pytest.skip(f"this context has no timer queries: {r.timer.note}")
    vs = wviews(ctx, r, Thru())
    run(ctx, r, vs, frames=PassTimer.LAG + 2)
    # plan 30 D0 (decision 5): the effect that ran has its own line, in
    # its place before its end; the graph's static lines are the rest
    # (plan 35 T4: the hands through are a copy of warp over a composite)
    timed = r._graph.timed
    at = timed.index("shown(copy)")
    assert list(r.stats["gpu_ms"]) == [*timed[:at], "copy", *timed[at:]]
    assert "shown(copy)" in r.stats["gpu_ms"] and "composite" in r.stats["gpu_ms"]
    vs = wviews(ctx, r, S())
    run(ctx, r, vs, frames=PassTimer.LAG + 1)
    assert r._graph.timed == ["scene", "hands.layer", "shown(warp)", "output.1"]
    assert list(r.stats["gpu_ms"]) == ["scene", "hands.layer", "warp", "shown(warp)",
                                       "output.1"]


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
    assert r._graph.nodes["scene"].image(frame) is r.scene.tex
    out.release()
