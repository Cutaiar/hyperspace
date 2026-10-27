"""Plan 30 D0: the effect node, and the frame chain as a run of them.

The pure half first — the frame holds one `graph.Effect` node per
effect instance in the run's wire order, and (plan 35 T4) one `graph.Copy`
per effect for each output wired with the hands through, each chain ending
in its end (`graph.Shown`), and the pool it asks for — then the
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
from wiredframe import Shows, Thru, graph

from hyperspace import graph as G
from hyperspace.graphmigrate import wired_wiring
from hyperspace.outputs import Switches, View

S = Switches
RUN = ("warp", "acid", "acid.2", "palette")

# ---------------------------------------------------------------- no GL


def _effects(g: G.Graph, end: str) -> list[G.Effect]:
    """The effects (copies too) end `end` reads, first first."""
    return G._effects_of(g.nodes[end].inputs["image"])


def _run_of(g: G.Graph, end: str) -> list[str]:
    return [e.effect for e in _effects(g, end)]


def _end(g: G.Graph) -> str:
    """Output 1's end, by name."""
    return g.nodes["output.1"].inputs["image"].name


def test_the_default_graph_holds_one_effect_node_per_instance_in_wire_order():
    """All outputs' end reads the last of a run of effect nodes, one per
    instance in the run's wire order (plan 33 R; plan 35: `lookback → … →
    output.all.image`), the first reading the look-back; each output wired
    with the hands through has a copy of each (`Copy`, named `copy`,
    `copy.2` …) over its composite (plan 35 T4, row 377); none given, the
    end reads the look-back as before D0. Plan 36 T1: with every window
    through, the run is built (All outputs' picture) but no end shows it."""
    wires = [{"from": a, "to": f"{b}.image"} for a, b in zip(("frame", *RUN), RUN)]
    section = {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
               "wires": [*wires, {"from": RUN[-1], "to": "fx.image"}]}
    assert G.read_graph(section).wiring().run == RUN
    shows = [Shows(through=True), Shows(scene=False, through=True)]
    g = graph(shows, section, effects=tuple(sorted(RUN)))
    assert g.run == RUN
    # (R23, plan 33 T7: a wiring that says no run has the empty one)
    assert graph(shows, effects=RUN).run == ()
    assert "shown(palette)" not in g.nodes and g.nodes["palette"].inputs["image"] is \
        g.nodes["acid.2"]
    for end, src, names in (
            ("shown(copy.4)", "composite", ["copy", "copy.2", "copy.3", "copy.4"]),
            ("shown(copy.8)", "composite.2", ["copy.5", "copy.6", "copy.7", "copy.8"])):
        run = _effects(g, end)
        assert _run_of(g, end) == list(RUN)
        assert [e.name for e in run] == names
        assert all(isinstance(e, G.Effect) and e.KIND == "effect" for e in run)
        assert run[0].inputs == {"image": g.nodes[src], "aux": None}
        assert g.nodes[end].inputs["image"] is run[-1]
        order = [n.name for n in g.order]
        assert [order.index(n) for n in names] == sorted(order.index(n) for n in names)
        assert order.index(names[-1]) < order.index(end)
    assert all(isinstance(g.nodes[f"copy.{k}"], G.Copy) for k in range(2, 9))
    # the timed lines are the graph's own: an effect has one only when it runs
    assert not set(g.timed) & {n.name for n in g.order if isinstance(n, G.Effect)}
    assert g.pool == 2
    # none given: no effect node, and no pool
    bare = G.build_graph([View(S(), (10, 10))], wired_wiring(G.Wiring()))
    assert bare.nodes["shown(scene)"].inputs["image"] is bare.nodes["scene"]   # (plan 36 T4)
    assert bare.pool == 0


def test_an_effect_named_like_another_node_is_kept_apart():
    """An effect file called `capture` (nothing stops one being dropped in
    the folder) is its own node: the frame's look-back, capture and cover
    are named apart from any effect (plan 35 T4: `lookback`,
    `lookback(capture)`, `lookback(cover)`)."""
    names = ("capture", "warp")
    g = G.build_graph([View(S(), (10, 10))], wired_wiring(G.Wiring(run=names), "trail"),
                      effects=names)
    assert [e.name for e in _effects(g, _end(g))] == ["capture", "warp"]
    assert isinstance(g.nodes["lookback(capture)"], G.Capture)
    assert isinstance(g.nodes["lookback(cover)"], G.Cover)
    assert isinstance(g.nodes["lookback"], G.History)


def test_an_effect_node_takes_an_image_and_makes_one():
    e = G.Effect("palette")
    # plan 32 T7: and a second picture, aux, unwired by default
    assert e.name == e.effect == "palette" and e.INPUTS == {"image": G.IMAGE, "aux": G.IMAGE}
    assert e.OUTPUT == G.IMAGE and e.inputs == {"image": None, "aux": None}
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


def test_the_renderer_builds_the_run_from_the_wires_and_a_toggle_does_not_rebuild(ctx):
    """Plan 33 R (rewritten from plan 30 D0's stack-order test): a wiring
    that says a run builds it from its wires, in wire order; the graph
    keys on the effect files present, so switching one on keeps the graph
    object, and a rewire builds another. A wiring that says no run (no
    preset's graph) has the empty one (R23, plan 33 T7: the stack is gone),
    whatever is switched on."""
    from test_outputs import rig, run, views

    r = rig(ctx)
    r.wiring = wired_wiring(G.read_graph({"wires": [{"from": "frame", "to": "acid.image"},
                                       {"from": "acid", "to": "warp.image"},
                                       {"from": "warp", "to": "fx.image"}]}).wiring())
    vs = views(ctx, S())
    run(ctx, r, vs, frames=1)
    g = r._graph
    assert set(g.effects) == set(r.fx.state.specs) and len(g.effects) >= 12
    assert _run_of(g, _end(g)) == ["acid", "warp"] == list(g.run)
    r.fx.state.values["acid"]["on"] = True
    run(ctx, r, vs, frames=1)
    assert r._graph is g
    r.wiring = wired_wiring(G.read_graph({"wires": [{"from": "frame", "to": "warp.image"},
                                       {"from": "warp", "to": "fx.image"}]}).wiring())
    run(ctx, r, vs, frames=1)
    assert r._graph is not g and _run_of(r._graph, _end(r._graph)) == ["warp"]
    # no run said: the empty run, whatever is on
    r = rig(ctx)
    r.wiring = wired_wiring(G.Wiring())
    run(ctx, r, vs, frames=1)
    g = r._graph
    assert _run_of(g, _end(g)) == [] and g.run == ()
    r.fx.state.values["acid"]["on"] = True
    run(ctx, r, vs, frames=1)
    assert r._graph is g and _run_of(g, _end(g)) == [] and not r.stats["fx_on"]


def test_an_off_effect_is_read_through_and_runs_no_pass(ctx):
    """Every effect off: no pass and no texture of the pool, the frame
    the one with no effect nodes at all. One on among the off ones: that
    one pass a frame, no other."""
    import numpy as np
    from test_outputs import rig, run, views, wired

    def every_one_wired(r):
        """Every effect in the run (by its file's @order), switched off."""
        st = r.fx.state
        names = sorted(st.specs, key=lambda n: (st.specs[n].order, n))
        chain = ["frame", *names]
        r.wiring = wired_wiring(wired(r, {"wires": [{"from": a, "to": f"{b}.image"}
                                       for a, b in zip(chain, names)]
                             + [{"from": names[-1], "to": "fx.image"}]}))
        return r

    r = every_one_wired(rig(ctx, effects=()))
    calls = _count(r)
    got = run(ctx, r, views(ctx, S()), frames=3)[0]
    assert calls == [] and r.stats["effects"] == [] and r.stats["chain_runs"] == 0
    assert r.fx._tex == []                                # no texture taken
    assert len(_effects(r._graph, _end(r._graph))) >= 12
    bare = rig(ctx, effects=())
    bare._graph_for = lambda vs: G.build_graph(vs, wired_wiring(G.Wiring()))   # no effect nodes
    want = run(ctx, bare, views(ctx, S()), frames=3)[0]
    assert not _effects(bare._graph_for(views(ctx, S())), "shown(scene)")
    assert np.array_equal(got, want)
    # one on: one pass a frame, the off ones around it none
    r = every_one_wired(rig(ctx, effects=("warp",)))
    calls = _count(r)
    run(ctx, r, views(ctx, S()), frames=3)
    assert [n for n, _ in calls] == ["warp"] * 3 and r.stats["effects"] == ["warp"]
    assert r.stats["chain_runs"] == 1


def test_two_instances_of_one_effect_are_two_nodes_on_one_program(ctx):
    """`acid` and `acid.2`: two nodes, each its own pass with its own
    values, one compiled program between them."""
    from test_outputs import rig, run, views

    from hyperspace.graphmigrate import wiring_of

    r = rig(ctx, effects=())
    st = r.fx.state
    st.set_instances({"acid": 2})
    st.values["acid"]["on"] = st.values["acid.2"]["on"] = True
    r.wiring = wired_wiring(wiring_of(st))  # plan 33 R23: both in the run
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
    g.add(G.Shown("fx", image=warp))
    g.add(G.Shown("fx(hands)", image=warp))
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
        g.add(G.Shown("fx", image=kal))
        if held:                                           # a second reader of warp
            g.add(G.Shown("fx(hands)", image=warp))
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
    order before their end, the end's own line kept, and no line for an
    effect that is off."""
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
    end = _end(r._graph)
    at = static.index(end)
    assert list(ms) == [*static[:at], *on, *static[at:]]
    assert "acid" not in ms and all(v >= 0.0 for v in ms.values())
    lines = Panel.gpu_lines(SimpleNamespace(renderer=r))
    # (plan 35 T4: the last line names the ends that ran)
    assert lines[-1] == f"ends: {end}"
    named = [ln.split()[0] for ln in lines[1:-1]]
    assert named == list(ms) and {"warp", "kaleido", end} <= set(named)


def test_the_pipeline_end_still_paints_straight_into_a_frame_sized_output(ctx):
    """One output at the frame's size, unflipped: the last effect's pass
    writes the output's own framebuffer (no frame texture); a flipped one
    takes its end's frame texture, as before."""
    from test_outputs import rig, run, views

    r = rig(ctx, effects=("warp", "kaleido"))
    vs = views(ctx, S())
    run(ctx, r, vs, frames=1)
    calls = _count(r)
    run(ctx, r, vs, frames=1)
    end = _end(r._graph)
    assert r.stats["direct"] is True and r.stats["ends"] == [end]
    assert len(calls) == 2 and calls[-1][1] is vs[0].target
    assert any(calls[0][1] is f for _, f in r.fx.pool(r.fx.size, 2))   # the first: the pool's
    assert end not in (getattr(r, "_frames", None) or {})              # no frame texture
    r = rig(ctx, effects=("warp",))
    calls = _count(r)
    vs = views(ctx, S(flip_x=True))
    run(ctx, r, vs, frames=1)
    assert r.stats["direct"] is False
    assert calls[-1][1] is r._frame_target(_end(r._graph),
                                           (vs[0].rect[2], vs[0].rect[3]))[1]


def _block_paint(self, frame, dst):
    """The pipelines' end's `paint` as it was before D0, verbatim (plan 35
    T4: on `graph.Shown`, the ends' one class now): the whole stack as one
    block through `FxChain.begin` / `run`."""
    src = self.inputs["image"]
    if not frame.fx_on:
        src.paint(frame, dst)
        return
    from test_outputs import _stack_begin, _stack_run

    buf = _stack_begin(frame.r, frame.size)
    src.paint(frame, buf)
    with frame.timed(self.name):
        _stack_run(frame.r, dst, frame.t)
    frame.stats["chain_runs"] += 1


@pytest.mark.parametrize("effects", [("warp",), ("kaleido", "acid", "palette")])
def test_the_run_draws_what_the_one_block_chain_drew(ctx, monkeypatch, effects):
    """Byte for byte, with the off effects between the on ones read
    through: the run of nodes against the pre-D0 end (no effect nodes, the
    block chain), through the scene and the hands-through outputs (plan
    35 T4: their copies)."""
    import numpy as np
    from test_outputs import rig, run, views, wviews
    from wiredframe import wiring

    sw = (S(), Thru(), Thru(scene=False))
    r = rig(ctx, effects=effects)
    if "palette" in effects:
        r.fx.state.values["palette"].update(mix=1.0, hue_from=170.0, hue_to=230.0)
    got = run(ctx, r, wviews(ctx, r, *sw), frames=3)
    with monkeypatch.context() as m:
        m.setattr(G.Shown, "paint", _block_paint)
        old = rig(ctx, effects=effects)
        if "palette" in effects:
            old.fx.state.values["palette"].update(mix=1.0, hue_from=170.0, hue_to=230.0)
        # the pre-D0 graph: the ends read their sources, no effect node —
        # its runs' effects named (plan 33 R: what `fx_on` asks), not built;
        # a through's end is always itself (hands drawn and an effect on:
        # what bent the pipeline)
        thru = wiring(G.Wiring(), *(s.shows if isinstance(s, Thru) else Shows() for s in sw))
        assert not thru.copies

        def bare(vs, o=old):
            from test_outputs import _stack_names
            g = G.build_graph(vs, wired_wiring(thru), (), tuple(sorted(o.fx.state.specs)))
            g.run = tuple(_stack_names(o))           # (the stack's: `o.wiring`'s run)
            for n in g.order:
                if isinstance(n, G.Shown):
                    n.stands = False
            return g

        old._graph_for = bare
        want = run(ctx, old, views(ctx, S(), S(), S()), frames=3)
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
    g = graph([Shows(through=True), Shows(scene=False, through=True)],
              G.Wiring(run=RUN), effects=RUN)
    for node in g.order:
        assert node.OUTPUT != G.VALUE and G.VALUE not in node.INPUTS.values(), node.name
    assert patch.RENDER_VALUE == G.VALUE
    for node in ast.walk(ast.parse(Path(patch.__file__).read_text())):
        if isinstance(node, ast.ImportFrom):
            assert "graph" not in {(node.module or "").split(".")[-1],
                                   *(a.name for a in node.names)}
