"""Plan 30 D0: the effect node, and the frame chain as a run of them.

The pure half first — the default graph holds one `graph.Effect` node
per effect instance in the stack's order, per pipeline, ending in the
pipeline's end (`graph.Fx`), and the pool it asks for — then the
renderer's half on offscreen targets: an off effect reads through and
runs no pass, two instances are two nodes on one program, an effect read
by two consumers runs once, SYSTEM times each effect that ran, the end
still paints straight into a frame-sized output, and the run draws what
the one-block chain drew before it, byte for byte. The factory presets'
pixels are `tests/test_golden_frames.py`'s (every golden unchanged).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hyperspace import graph as G
from hyperspace.outputs import HANDS, SCENE, SCENE_HANDS, Switches, View

S = Switches
RUN = ("warp", "acid", "acid.2", "palette")

# ---------------------------------------------------------------- no GL


def _run_of(g: G.Graph, end: str) -> list[str]:
    return [e.effect for e in g.nodes[end].effects]


def test_the_default_graph_holds_one_effect_node_per_instance_in_chain_order():
    """Each pipeline's end reads the last of a run of effect nodes, one per
    instance in the order given, the first reading the pipeline's source;
    the scene's run is named by the effects, the others by the pipeline's
    suffix; none given, the end reads its source as before D0."""
    g = G.default_graph([View(S(through=True), (10, 10)),
                         View(S(scene=False, through=True), (10, 10))], effects=RUN)
    assert g.effects == RUN
    for end, src, names in (
            ("fx", "history", list(RUN)),
            ("fx(scene+hands)", "composite(scene+hands)", [f"{e}(scene+hands)" for e in RUN]),
            ("fx(hands)", "composite(hands)", [f"{e}(hands)" for e in RUN])):
        fx = g.nodes[end]
        assert _run_of(g, end) == list(RUN)
        assert [e.name for e in fx.effects] == names
        assert all(isinstance(e, G.Effect) and e.KIND == "effect" for e in fx.effects)
        assert fx.effects[0].inputs == {"image": g.nodes[src]}
        assert fx.inputs["image"] is fx.effects[-1] and fx.source is g.nodes[src]
        order = [n.name for n in g.order]
        assert [order.index(n) for n in names] == sorted(order.index(n) for n in names)
        assert order.index(names[-1]) < order.index(end)
    # the layer and its stand-down still find the composite behind the run
    assert g.nodes["fx(scene+hands)"].layer is g.nodes["hands"]
    assert g.nodes["fx(hands)"].fallback is None
    assert g.nodes["fx(scene+hands)"].fallback is g.nodes["fx"]
    # the timed lines are the graph's own: an effect has one only when it runs
    assert not set(g.timed) & {n.name for n in g.order if isinstance(n, G.Effect)}
    assert g.pool == 2
    # none given: no effect node, and no pool
    bare = G.default_graph([View(S(), (10, 10))])
    assert bare.nodes["fx"].inputs["image"] is bare.nodes["history"] and bare.pool == 0
    assert G.effect_node_name("acid.2", SCENE) == "acid.2"
    assert G.effect_node_name("acid.2", SCENE_HANDS) == "acid.2(scene+hands)"
    assert G.effect_node_name("acid.2", HANDS) == "acid.2(hands)"


def test_an_effect_named_like_another_node_is_kept_apart():
    """An effect file called `scene` or `capture` (nothing stops one being
    dropped in the folder) gets the params' prefix as its node's name."""
    g = G.default_graph([View(S(), (10, 10))], effects=("scene", "capture", "warp"))
    assert [e.name for e in g.nodes["fx"].effects] == ["fx.scene", "fx.capture", "warp"]
    assert isinstance(g.nodes["scene"], G.Scene) and isinstance(g.nodes["capture"], G.Capture)
    # one called `fx`: its nodes would be the ends' names in every pipeline
    g = G.default_graph([View(S(through=True), (10, 10)),
                         View(S(scene=False, through=True), (10, 10))], effects=("fx",))
    assert [e.name for e in g.nodes["fx"].effects] == ["fx.fx"]
    assert [e.name for e in g.nodes["fx(scene+hands)"].effects] == ["fx.fx(scene+hands)"]
    assert [e.name for e in g.nodes["fx(hands)"].effects] == ["fx.fx(hands)"]
    assert all(isinstance(g.nodes[n], G.Fx) for n in G.FX_NAMES.values())


def test_an_effect_node_takes_an_image_and_makes_one():
    e = G.Effect("palette")
    assert e.name == e.effect == "palette" and e.INPUTS == {"image": G.IMAGE}
    assert e.OUTPUT == G.IMAGE and e.inputs == {"image": None}
    with pytest.raises(TypeError):
        G.Effect("palette", image=G.Shape("shape"))     # a geometry is not an image


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


def _count(r):
    """A counting stub over the frame chain's `run_one`: (name, dst) per pass."""
    calls = []
    real = r.fx.run_one

    def run_one(name, src, dst, t):
        calls.append((name, dst))
        real(name, src, dst, t)

    r.fx.run_one = run_one
    return calls


def test_the_renderer_builds_the_run_from_the_stack_and_a_toggle_does_not_rebuild(ctx):
    """The graph's runs are every instance in `FxState.names()` order, on or
    off; switching one on keeps the graph object, a new order builds another."""
    from test_outputs import rig, run, views

    r = rig(ctx)
    vs = views(ctx, S())
    run(ctx, r, vs, frames=1)
    g = r._graph
    assert g.effects == tuple(r.fx.state.names()) and len(g.effects) >= 12
    assert _run_of(g, "fx") == list(g.effects)
    r.fx.state.values["acid"]["on"] = True
    run(ctx, r, vs, frames=1)
    assert r._graph is g
    r.fx.state.values["acid"]["order"] = 0                # first in the stack now
    run(ctx, r, vs, frames=1)
    assert r._graph is not g and _run_of(r._graph, "fx")[0] == "acid"


def test_an_off_effect_is_read_through_and_runs_no_pass(ctx):
    """Every effect off: no pass and no texture of the pool, the frame
    the one with no effect nodes at all. One on among the off ones: that
    one pass a frame, no other."""
    import numpy as np
    from test_outputs import rig, run, views

    r = rig(ctx, effects=())
    calls = _count(r)
    got = run(ctx, r, views(ctx, S()), frames=3)[0]
    assert calls == [] and r.stats["effects"] == [] and r.stats["chain_runs"] == 0
    assert r.fx._tex == []                                # no texture taken
    assert len(r._graph.nodes["fx"].effects) >= 12
    bare = rig(ctx, effects=())
    bare._graph_for = lambda vs: G.default_graph(vs, G.Wiring())   # no effect nodes
    want = run(ctx, bare, views(ctx, S()), frames=3)[0]
    assert not bare._graph_for(views(ctx, S())).nodes["fx"].effects
    assert np.array_equal(got, want)
    # one on: one pass a frame, the off ones around it none
    r = rig(ctx, effects=("warp",))
    calls = _count(r)
    run(ctx, r, views(ctx, S()), frames=3)
    assert [n for n, _ in calls] == ["warp"] * 3 and r.stats["effects"] == ["warp"]
    assert r.stats["chain_runs"] == 1


def test_two_instances_of_one_effect_are_two_nodes_on_one_program(ctx):
    """`acid` and `acid.2`: two nodes, each its own pass with its own
    values, one compiled program between them."""
    from test_outputs import rig, run, views

    r = rig(ctx, effects=())
    st = r.fx.state
    st.set_instances({"acid": 2})
    st.values["acid"]["on"] = st.values["acid.2"]["on"] = True
    calls = _count(r)
    run(ctx, r, views(ctx, S()), frames=2)
    g = r._graph
    assert isinstance(g.nodes["acid"], G.Effect) and isinstance(g.nodes["acid.2"], G.Effect)
    assert (g.nodes["acid"].effect, g.nodes["acid.2"].effect) == ("acid", "acid.2")
    assert [n for n, _ in calls] == ["acid", "acid.2"] * 2
    assert "acid" in r.fx._progs and "acid.2" not in r.fx._progs     # one program, the file's


def test_an_effect_read_by_two_runs_once_into_a_held_texture(ctx):
    """An effect with two consumers (what a placement (D1) can make) is
    painted once a frame into a pool texture held for the frame, and each
    consumer shows that; the pool grows by one for it."""
    import numpy as np
    from test_outputs import H, W, fbo, rig, run, views

    r = rig(ctx, effects=("warp",))
    run(ctx, r, views(ctx, S()), frames=1)                 # the scene's texture exists
    class Picture(G.Node):                                 # last frame's scene as the source
        OUTPUT = G.IMAGE

        def image(self, frame):
            return r.scene.tex

    g = G.Graph()
    scene = g.add(Picture("picture"))
    warp = g.add(G.Effect("warp", image=scene))
    g.add(G.Fx("fx", SCENE, image=warp))
    g.add(G.Fx("fx(hands)", HANDS, image=warp))
    assert g.readers(warp) == 2 and g.pool == 3
    frame = G.Frame(r, ctx, None, W, H, 1.0, 2.0, [], (W, H), 0, r.scene.fbo, (0, 0, W, H),
                    fx_on=True, stats={"chain_runs": 0})
    frame.graph = g
    calls = _count(r)
    a, b = fbo(ctx), fbo(ctx)
    for end, out in (("fx", a), ("fx(hands)", b)):
        out.use()
        ctx.viewport = (0, 0, W, H)
        g.nodes[end].paint(frame, out)
    assert [n for n, _ in calls] == ["warp"] and frame.stats["effects"] == ["warp"]
    assert len(r.fx._tex) == 3 and len(frame.data["fx#held"]) == 1
    pa = np.frombuffer(a.read(components=4), dtype=np.uint8)
    assert np.array_equal(pa, np.frombuffer(b.read(components=4), dtype=np.uint8))
    assert pa.any()
    r.scene.fbo.use()


def test_a_held_effect_read_through_the_pool_is_never_its_consumers_target(ctx):
    """An on effect whose input is an effect with two readers (D1's
    `after:` placements): the held picture is made into a pool texture
    that is not the one its consumer paints into (no feedback loop), no
    pass reads the texture it writes, and the picture is the straight
    run's, byte for byte (the held texture is shown 1:1, half float to
    half float)."""
    import numpy as np
    from test_outputs import H, W, fbo, rig, run, views

    r = rig(ctx, effects=("warp", "kaleido"))
    run(ctx, r, views(ctx, S()), frames=1)                 # the scene's texture exists

    class Picture(G.Node):
        OUTPUT = G.IMAGE

        def image(self, frame):
            return r.scene.tex

    def draw(held: bool):
        g = G.Graph()
        pic = g.add(Picture("picture"))
        warp = g.add(G.Effect("warp", image=pic))
        kal = g.add(G.Effect("kaleido", image=warp))
        g.add(G.Fx("fx", SCENE, image=kal))
        if held:                                           # a second reader of warp
            g.add(G.Fx("fx(hands)", HANDS, image=warp))
        assert g.readers(warp) == (2 if held else 1) and g.pool == (3 if held else 2)
        frame = G.Frame(r, ctx, None, W, H, 1.0, 2.0, [], (W, H), 0, r.scene.fbo,
                        (0, 0, W, H), fx_on=True, stats={"chain_runs": 0})
        frame.graph = g
        calls = []
        real = r.fx.run_one

        def run_one(name, src, dst, t):
            calls.append((name, src, dst))
            real(name, src, dst, t)

        r.fx.run_one = run_one
        out = fbo(ctx)
        out.use()
        ctx.viewport = (0, 0, W, H)
        g.nodes["fx"].paint(frame, out)
        r.fx.run_one = real
        got = np.frombuffer(out.read(components=4), dtype=np.uint8).copy()
        r.scene.fbo.use()
        return got, calls, frame

    want, _, _ = draw(False)
    got, calls, frame = draw(True)
    assert [n for n, _, _ in calls] == ["warp", "kaleido"]
    for _, src, dst in calls:                              # no pass reads what it writes
        assert all(src is not a for a in dst.color_attachments)
    (_, _, held_dst), (_, kal_src, _) = calls
    held = frame.data["warp"]
    assert held_dst.color_attachments[0] is held           # warp made into the held texture ...
    assert kal_src is not held                             # ... never kaleido's own source
    assert len(frame.data["fx#held"]) == 1
    assert np.array_equal(got, want) and got.any()


def test_the_system_page_times_each_effect_that_ran(ctx):
    """Two effects on among the off ones: a line each, in the graph's
    order before the pipeline's end, the end's own line kept, and no line
    for an effect that is off."""
    from test_outputs import rig, run, views

    from hyperspace.render import PassTimer
    from hyperspace.ui import Panel

    r = rig(ctx, effects=("warp", "kaleido"))
    if not r.timer.on:
        pytest.skip(f"this context has no timer queries: {r.timer.note}")
    run(ctx, r, views(ctx, S()), frames=PassTimer.LAG + 2)
    ms = r.stats["gpu_ms"]
    on = [n for n in r.fx.state.names() if n in ("warp", "kaleido")]
    static = r._graph.timed
    at = static.index("fx")
    assert list(ms) == [*static[:at], *on, *static[at:]]
    assert "acid" not in ms and all(v >= 0.0 for v in ms.values())
    lines = Panel.gpu_lines(SimpleNamespace(renderer=r))
    named = [ln.split()[0] for ln in lines[1:]]
    assert named == list(ms) and {"warp", "kaleido", "fx"} <= set(named)


def test_the_pipeline_end_still_paints_straight_into_a_frame_sized_output(ctx):
    """One output at the frame's size, unflipped: the last effect's pass
    writes the output's own framebuffer (no frame texture); a flipped one
    takes the pipeline's frame texture, as before."""
    from test_outputs import rig, run, views

    r = rig(ctx, effects=("warp", "kaleido"))
    vs = views(ctx, S())
    run(ctx, r, vs, frames=1)
    calls = _count(r)
    run(ctx, r, vs, frames=1)
    assert r.stats["direct"] is True and r.stats["pipelines"] == [SCENE]
    assert len(calls) == 2 and calls[-1][1] is vs[0].target
    assert any(calls[0][1] is f for _, f in r.fx.pool(r.fx.size, 2))   # the first: the pool's
    assert SCENE not in (getattr(r, "_frames", None) or {})            # no frame texture
    r = rig(ctx, effects=("warp",))
    calls = _count(r)
    vs = views(ctx, S(flip_x=True))
    run(ctx, r, vs, frames=1)
    assert r.stats["direct"] is False
    assert calls[-1][1] is r._frame_target(SCENE, (vs[0].rect[2], vs[0].rect[3]))[1]


def _block_paint(self, frame, dst):
    """`graph.Fx.paint` as it was before D0, verbatim: the whole stack as
    one block through `FxChain.begin` / `run`."""
    src = self.inputs["image"]
    if not frame.fx_on:
        src.paint(frame, dst)
        return
    fx = frame.r.fx
    buf = fx.begin(frame.size)
    src.paint(frame, buf)
    with frame.timed(self.name):
        fx.run(dst, frame.t)
    frame.stats["chain_runs"] += 1


@pytest.mark.parametrize("effects", [("warp",), ("kaleido", "acid", "palette")])
def test_the_run_draws_what_the_one_block_chain_drew(ctx, monkeypatch, effects):
    """Byte for byte, with the off effects between the on ones read
    through: the run of nodes against the pre-D0 end (no effect nodes, the
    block chain), through the scene and the hands-through pipelines."""
    import numpy as np
    from test_outputs import rig, run, views

    sw = (S(), S(through=True), S(scene=False, through=True))
    r = rig(ctx, effects=effects)
    if "palette" in effects:
        r.fx.state.values["palette"].update(mix=1.0, hue_from=170.0, hue_to=230.0)
    got = run(ctx, r, views(ctx, *sw), frames=3)
    with monkeypatch.context() as m:
        m.setattr(G.Fx, "paint", _block_paint)
        old = rig(ctx, effects=effects)
        if "palette" in effects:
            old.fx.state.values["palette"].update(mix=1.0, hue_from=170.0, hue_to=230.0)
        # the pre-D0 graph: the ends read their sources, no effect node
        old._graph_for = lambda vs, o=old: G.default_graph(
            vs, getattr(o, "wiring", None) or G.Wiring())
        want = run(ctx, old, views(ctx, *sw), frames=3)
    assert r.stats["chain_runs"] == old.stats["chain_runs"] >= 1
    for a, b in zip(got, want, strict=True):
        assert np.array_equal(a, b)


def test_the_value_port_type_exists_and_no_node_uses_it():
    """Plan 30 D2: `VALUE` is a port type beside `IMAGE`, `MASK` and
    `GEOMETRY`, its docstring naming its two intended uses (the palette's
    value out for a lights sink; an image-in `sample` port setting a
    palette's params) — and no node publishes or reads one in this plan:
    not any Node class, nor any node of a built default graph. `patch.py`
    knows the name without importing the graph (it is a leaf)."""
    import ast
    import inspect
    from pathlib import Path

    from hyperspace import patch

    assert G.VALUE == "value" and G.PORT_TYPES == (G.IMAGE, G.MASK, G.GEOMETRY, G.VALUE)
    assert len(set(G.PORT_TYPES)) == 4
    src = Path(G.__file__).read_text()
    doc = src[src.index('VALUE = "value"'):src.index("PORT_TYPES =")]
    assert "palette" in doc and "lights" in doc and "sample" in doc and "plan 29" in doc
    classes = [c for _, c in inspect.getmembers(G, inspect.isclass) if issubclass(c, G.Node)]
    assert G.Effect in classes and G.Output in classes
    for c in classes:
        assert c.OUTPUT != G.VALUE and G.VALUE not in c.INPUTS.values(), c
        assert c.OUTPUT in (None, *G.PORT_TYPES), c
    g = G.default_graph([View(S(through=True), (10, 10)),
                         View(S(scene=False, through=True), (10, 10))], effects=RUN)
    for node in g.order:
        assert node.OUTPUT != G.VALUE and G.VALUE not in node.INPUTS.values(), node.name
    assert patch.RENDER_VALUE == G.VALUE
    for node in ast.walk(ast.parse(Path(patch.__file__).read_text())):
        if isinstance(node, ast.ImportFrom):
            assert "graph" not in {(node.module or "").split(".")[-1],
                                   *(a.name for a in node.names)}
