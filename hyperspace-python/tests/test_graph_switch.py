"""Plan 33 T5 (S) — the switch: eight pictures in, one param picks, only
the picked one runs.

`switch[.n]` takes eight `IMAGE` inputs `in1` … `in8` and passes the one
`switch[.n].select` picks (off, 1–8: R11) through at its consumer's size —
a cut, no pass of its own (row 352). Only the selected input's branch is
made each frame: the other seven run no pass and their channels upload
nothing (Review Focus 2), and moving `select` never builds the graph
again. The param is declared from the preset's graph, as the effect
instances are, and a route on the old `view.media` / `backdrop.channel`
drives it after the migration (row 350, R19).

The channels are the real `MediaState` over fake stills
(test_graph_faces's). The GL half skips without a standalone context."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace import graph as G
from hyperspace.outputs import Switches, View

ROOT = Path(__file__).resolve().parents[1]
DRIVEN = ROOT / "tests" / "fixtures" / "plan33-driven"
RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)
SWITCH = {"kind": "switch"}


def section(*pairs, nodes=()):
    return {"nodes": list(nodes), "wires": [{"from": a, "to": b} for a, b in pairs]}


# ---------------------------------------------------------------- data

def test_the_switch_node_is_eight_pictures_and_one_out():
    assert G.SwitchNode.KIND == "switch"
    assert G.SwitchNode.INPUTS == {f"in{i}": G.IMAGE for i in range(1, 9)}
    assert G.SwitchNode.OUTPUT == G.IMAGE


def test_the_switch_is_built_from_its_wires():
    """A switch's wires are the wiring's now (T4 held them back): the
    switch is one node, each wired input on its port, its picture on what
    the switch feeds; an unwired input is None."""
    spec = G.read_graph(section(("frame", "fx.image"), ("media.a", "switch.in1"),
                                ("media.c", "switch.in3"), ("switch", "pattern.media"),
                                nodes=[SWITCH]))
    assert not spec.notes
    w = spec.wiring()
    assert G.Wire("media.a", "switch.in1") in w.wires and G.Wire("switch", "pattern.media") \
        in w.wires
    g = G.default_graph([View(Switches(), (64, 48))], w)
    sw = g.nodes["switch"]
    assert isinstance(sw, G.SwitchNode)
    assert sw.inputs["in1"] is g.nodes["media.a"] and sw.inputs["in3"] is g.nodes["media.c"]
    assert sw.inputs["in2"] is None
    assert g.nodes["pattern"].inputs["media"] is sw


def test_a_switch_that_reaches_nothing_has_no_node():
    spec = G.read_graph(section(("frame", "fx.image"), ("media.a", "switch.in1"),
                                nodes=[SWITCH]))
    g = G.default_graph([View(Switches(), (64, 48))], spec.wiring())
    assert "switch" not in g.nodes


def test_declare_switches_comes_and_goes():
    from hyperspace.params import Kind, Registry, declare_switches

    r = Registry()
    assert declare_switches(r, ["switch", "switch.2"]) == ["switch.select", "switch.2.select"]
    p = r["switch.2.select"]
    assert p.kind is Kind.ENUM and p.names == ["off", *[str(i) for i in range(1, 9)]]
    assert p.value == 0 and p.group == "switch" and p.modulatable and p.persist
    p.set(4)
    assert declare_switches(r, ["switch", "switch.2"]) == []
    assert r["switch.2.select"].value == 4                 # kept while it is named
    assert declare_switches(r, ["switch"]) == ["switch.2.select"]
    assert "switch.2.select" not in r and "switch.select" in r


# ---------------------------------------------------------------- GL
moderngl = pytest.importorskip("moderngl")

from test_graph_faces import Still, _fbo, _media, _px, _rgba


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c


def _empty(select=None, **kw):
    from hyperspace.view import ViewState

    s = ViewState(lines=False, points=False, faces=False, **kw)
    s.switch = dict(select or {})
    return s


def _renderer(ctx, media=None, pairs=(), nodes=(), instances=None, values=None):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    st = r.fx.state
    if instances:
        st.set_instances(instances)
    for name, v in (values or {}).items():
        st.values[name].update(v)
    spec = G.read_graph(section(("frame", "fx.image"), *pairs, nodes=nodes),
                        effects=set(st.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    return r


def _centre(px, d=4):
    h, w = px.shape[:2]
    return px[h // 2 - d: h // 2 + d, w // 2 - d: w // 2 + d, :3].reshape(-1, 3).mean(axis=0)


def _views(ctx, size=(96, 64)):
    return [View(Switches(), size, target=_fbo(ctx, *size))]


def _frame(ctx, r, s, vs, k=0):
    size = vs[0].size
    r.draw_outputs(s, *size, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return _px(vs[0].target)


def test_the_switch_shows_its_selected_input(ctx):
    """A red still on a, a blue on b, into `switch.in1` / `in2`, the switch
    into output 1's picture: the centre is red at `select` 1, blue at 2,
    the black ground at off."""
    m = _media(a=Still(_rgba(16, 9, RED)), b=Still(_rgba(16, 9, BLUE)))
    r = _renderer(ctx, m, [("media.a", "switch.in1"), ("media.b", "switch.in2"),
                           ("switch", "output.1.image")], [SWITCH])
    vs = _views(ctx)
    s = _empty()
    got = {}
    for k in (1, 2, 0):
        s.switch["switch"] = k
        got[k] = _centre(_frame(ctx, r, s, vs, k))
    assert got[1][0] > 200 and got[1][2] < 30, got[1]
    assert got[2][2] > 200 and got[2][0] < 30, got[2]
    assert got[0].max() < 5, got[0]


def _eight(ctx):
    """Eight playing channels, each through its own acid (`acid`, `acid.2`
    … `acid.8`, all on) into `in1` … `in8`, the switch on output 1."""
    stills = {c: Still(_rgba(16, 9, (30 * i, 255 - 30 * i, 90)))
              for i, c in enumerate("abcdefgh")}
    names = ["acid", *[f"acid.{n}" for n in range(2, 9)]]
    pairs = [(f"media.{c}", f"{n}.image") for c, n in zip("abcdefgh", names)]
    pairs += [(n, f"switch.in{i}") for i, n in enumerate(names, 1)]
    pairs.append(("switch", "output.1.image"))
    nodes = [SWITCH, *({"kind": "effect", "file": "acid", "instance": n} for n in range(2, 9))]
    r = _renderer(ctx, _media(**stills), pairs, nodes, {"acid": 8},
                  {n: {"on": True, "mix": 1.0} for n in names})
    return r, names


def test_only_the_selected_input_is_made(ctx):
    """Review Focus 2: at `select` 3 the frame runs acid.3's pass alone —
    the other seven effects run none — and only channel c is read and
    uploaded."""
    r, _ = _eight(ctx)
    vs = _views(ctx)
    s = _empty({"switch": 3})
    _frame(ctx, r, s, vs)
    assert r.stats["effects"] == ["acid.3"]
    assert {k for k in r._media_now if k[0] == "raw"} == {("raw", "c")}
    assert r.media_tex.uploads == 1
    _frame(ctx, r, s, vs, 1)
    assert r.stats["effects"] == ["acid.3"] and r.media_tex.uploads == 1


def test_select_changes_do_not_rebuild_the_graph(ctx):
    """Review Focus 2: `select` stepped 1 → 8 over eight frames — the same
    graph every frame, and each frame the one effect selected runs."""
    r, names = _eight(ctx)
    vs = _views(ctx)
    s = _empty({"switch": 1})
    graphs, ran = [], []
    for k in range(1, 9):
        s.switch["switch"] = k
        _frame(ctx, r, s, vs, k)
        graphs.append(r._graph_for(vs))
        ran.append(list(r.stats["effects"]))
    assert all(g is graphs[0] for g in graphs)
    assert ran == [[n] for n in names]


def _app(media=None, view=None):
    """A registry over `view` (and `media`), the LFOs and a router, the
    library and the presets — the app's, as test_plan31_wiring.make_app
    builds it, with the view state kept for the renderer."""
    import tempfile

    from hyperspace import lfo, preset, routing, tempo
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.fx import FxState
    from hyperspace.library import Library
    from hyperspace.lookback import DreamState
    from hyperspace.params import build_registry

    home = Path(tempfile.mkdtemp(prefix="hyperspace-switch-"))
    chain = Analyzer(Analyser())
    lib = Library(home, period=0.0)
    reg = build_registry(view, Control(chain), SimpleNamespace(chain=chain), lib.project,
                         dream=DreamState(), fx=FxState(), media=media)
    clock = tempo.Clock(now=lambda: 0.0)
    lfos = lfo.LFOs(seed=1)
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    table = routing.Bindings.load(routing.bindings_path(home), legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    router = routing.Router(reg, table)
    router.use_lfos(lfos, clock)
    presets = preset.Presets(lib, reg, router)
    return SimpleNamespace(lib=lib, reg=reg, router=router, presets=presets, lfos=lfos,
                           clock=clock)


def _on_renderer(ctx, app, media):
    from hyperspace.render import Renderer

    r = Renderer(ctx, fx=app.reg.fx_state)
    r.ghost.state.on = False
    app.presets.graph.attach(r)
    r.media = media
    return r


def test_a_route_drives_select(ctx):
    """An LFO's square wave routed onto `switch.select` (base 2, depth ¼):
    the select steps 1, 3, 1, 3 … and the output alternates between the
    red on `in1` and the blue on `in3` (the green on `in2`, the base, is
    never shown)."""
    from hyperspace.lfo import SHAPES
    from hyperspace.routing import Binding
    from hyperspace.view import ViewState

    m = _media(a=Still(_rgba(16, 9, RED)), b=Still(_rgba(16, 9, GREEN)),
               c=Still(_rgba(16, 9, BLUE)))
    view = ViewState(lines=False, points=False, faces=False)
    app = _app(m, view)
    doc = {"schema": "hyperspace.preset/5", "name": "lfo-switch",
           "values": {"switch.select": 2},
           "graph": section(("frame", "fx.image"), ("media.a", "switch.in1"),
                            ("media.b", "switch.in2"), ("media.c", "switch.in3"),
                            ("switch", "output.1.image"), nodes=[SWITCH])}
    app.presets.load_doc(doc)
    assert app.reg["switch.select"].value == 2
    one = app.lfos[0]
    one.shape, one.rate, one.depth = SHAPES.index("square"), 1.0, 1.0
    app.router.table.bindings.append(Binding("lfo:0", "switch.select", "push", 0.25))
    for c, src in zip("abc", (RED, GREEN, BLUE)):          # the bins the load emptied
        m.assign(c, 0, f"file:/fake/{c}.png")
    m.poll(0.0, 0.0)
    r = _on_renderer(ctx, app, m)
    vs = _views(ctx)
    seen, colours = [], []
    for k in range(1, 9):
        t = k * 0.25
        app.clock.tick(t)
        app.router.modulate(None, 0.25, now=t)
        app.reg.apply()
        seen.append(app.reg["switch.select"].value)
        c = _centre(_frame(ctx, r, view, vs, k))
        colours.append("red" if c[0] > 200 else "blue" if c[2] > 200 else
                       "green" if c[1] > 200 else "?")
    assert set(seen) == {1, 3}, seen
    assert colours == ["red" if v == 1 else "blue" for v in seen], (seen, colours)


class _Lanes:
    """An analyzer as `Router.modulate` reads one: its lanes, × CEIL."""

    def __init__(self, n=8):
        from hyperspace.routing import CEIL

        self.ceil = CEIL
        self.lanes = np.zeros(n)

    def set(self, i, u):
        self.lanes[i] = u * self.ceil


def _faces_view():
    from hyperspace.view import ViewState

    return ViewState(shape=3, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25,
                     faces=True, lines=False, points=False, bright=2.0, zoom=1.6,
                     media_scale=1.0)


def test_a_migrated_view_media_route_still_switches_the_faces(ctx):
    """T2's migrated preset: a /2 file with `view.media` 2 and a lane route
    on it (driven-media-v2). It loads with a switch over the eight
    channels into `pattern.media`, the route on `switch.select`, the select
    at 2 — so the faces show channel b at rest and channel c (index 3) once
    the lane pushes the knob a step on, as `view.media` did."""
    m = _media(b=Still(_rgba(16, 9, RED)), c=Still(_rgba(16, 9, BLUE)))
    view = _faces_view()
    app = _app(m, view)
    src = json.loads((DRIVEN / "driven-media-v2.json").read_text())
    assert app.presets.load_doc(src) == []
    assert [b.target for b in app.router.table.routes()] == ["switch.select"]
    assert app.reg["switch.select"].value == 2
    free = app.presets.graph.free_doc()
    assert SWITCH in free["nodes"] and {"from": "switch", "to": "pattern.media"} in free["wires"]
    for i, c in enumerate("abcdefgh", 1):
        assert {"from": f"media.{c}", "to": f"switch.in{i}"} in free["wires"]
    for c in "bc":
        m.assign(c, 0, f"file:/fake/{c}.png")
    m.poll(0.0, 0.0)
    r = _on_renderer(ctx, app, m)
    vs = _views(ctx, (160, 120))
    seen = []
    real = r.draw_scene

    def spy(s, *a, **kw):
        seen.append(r._face_media(s))
        return real(s, *a, **kw)

    r.draw_scene = spy
    lanes = _Lanes()
    shown = []
    for k, u in enumerate((0.0, 0.25, 0.0)):
        lanes.set(0, u)
        app.router.modulate(lanes, 1 / 60)
        app.reg.apply()
        _frame(ctx, r, view, vs, k)
        (tex, _), = seen[k:]
        shown.append((app.reg["switch.select"].value, tex))
    assert [v for v, _ in shown] == [2, 3, 2]
    raw = {c: r._channel_layer(c)[0] for c in "bc"}
    assert [t for _, t in shown] == [raw["b"], raw["c"], raw["b"]]


def test_a_migrated_backdrop_route_switches_the_backdrop(ctx):
    """driven-channels (a /4 with `backdrop.channel` 3 and a lane route on
    it): the backdrop is a second switch's picture, laid under an empty
    scene — channel c at rest, channel d once the lane moves the knob."""
    m = _media(c=Still(_rgba(16, 9, RED)), d=Still(_rgba(16, 9, BLUE)))
    view = _empty()
    app = _app(m, view)
    src = json.loads((DRIVEN / "driven-channels.json").read_text())
    assert app.presets.load_doc(src) == []
    assert [b.target for b in app.router.table.routes()] == ["switch.select",
                                                             "switch.2.select"]
    assert app.reg["switch.2.select"].value == 3
    for c in "cd":
        m.assign(c, 0, f"file:/fake/{c}.png")
        m.channels[c].fit = 2
    m.poll(0.0, 0.0)
    r = _on_renderer(ctx, app, m)
    vs = _views(ctx)
    lanes = _Lanes()
    got = []
    for k, u in enumerate((0.0, 0.5, 0.0)):
        lanes.set(1, u)
        app.router.modulate(lanes, 1 / 60)
        app.reg.apply()
        got.append((app.reg["switch.2.select"].value, _centre(_frame(ctx, r, view, vs, k))))
    assert [v for v, _ in got] == [3, 4, 3]
    assert got[0][1][0] > 150 and got[0][1][2] < 30, got[0]
    assert got[1][1][2] > 150 and got[1][1][0] < 30, got[1]


def test_switch_params_come_and_go_with_the_graph(tmp_path):
    """A preset whose graph holds `switch.2` declares `switch.2.select` (its
    value landed); loading one without it takes the param away."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    doc = {"schema": "hyperspace.preset/5", "name": "two",
           "values": {"switch.2.select": 5},
           "graph": section(("frame", "fx.image"), ("media.a", "switch.2.in5"),
                            ("switch.2", "output.2.image"),
                            nodes=[{"kind": "switch", "instance": 2}])}
    assert app.presets.load_doc(doc) == []
    assert app.reg["switch.2.select"].value == 5 and app.reg["switch.2.select"].group == "switch"
    assert app.presets.document("two")["values"]["switch.2.select"] == 5
    assert app.presets.load_doc({"schema": "hyperspace.preset/4", "name": "none",
                                 "values": {}}) == []
    assert "switch.2.select" not in app.reg


def test_the_switch_onto_the_faces_is_a_cut(ctx):
    """switch-faces (the golden fixture) at select 2: every pixel is the
    frame the still wired straight onto the faces draws — the switch adds
    no pass — and acid.2, on in3, runs none."""
    from test_graph_faces import _rig_frame

    got, r = _rig_frame(ctx, "switch-faces")
    assert r.stats["effects"] == [] and isinstance(r._graph.nodes["switch"], G.SwitchNode)
    assert r._graph.nodes["shape"].inputs["faces"] is r._graph.nodes["switch"]
    straight = G.read_graph(section(("frame", "fx.image"),
                                    ("media.a", "shape.faces"))).wiring()
    want, _ = _rig_frame(ctx, "switch-faces", wiring=straight)
    assert got[..., :3].max() > 40 and np.array_equal(got, want)
    unwired, _ = _rig_frame(ctx, "switch-faces",
                            wiring=G.read_graph(section(("frame", "fx.image"))).wiring())
    assert not np.array_equal(got, unwired)
