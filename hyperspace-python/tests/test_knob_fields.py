"""Plan 67 P3 (§3.9) — any knob takes a field: `value + depth × field(uv)` per
pixel, on a port named by the knob's key (`wave.amount`).

Held here:

- every knob of every shipped file either takes a field or says why not in
  words (a choice, a count, a `@clock`'s rate, a file with a Python half);
- the accessor: with no knob wired an effect's program is its file's, string
  for string (so no file's bytes move; `tools/fx_sweep.py` proves the renders),
  and every file compiles with all its knobs wired at once;
- a field of 0 draws what the unwired knob draws, and a field moves the knob
  per pixel: half the frame at one value, half at another, each half equal to
  the effect drawn with the knob set there by hand;
- the result stays inside the knob's range (clamped) or wraps (`wrap`)."""

from __future__ import annotations

import numpy as np
import pytest

from hyperspace import fx
from hyperspace.fx import FxChain, FxState

moderngl = pytest.importorskip("moderngl")

W, H = 64, 48


@pytest.fixture(scope="module")
def ctx():
    c = moderngl.create_context(standalone=True)
    yield c
    c.release()


def _pictures(ctx):
    rng = np.random.default_rng(5)
    a = rng.integers(0, 256, (H, W, 4), dtype=np.uint8)
    a[..., 3] = 255
    return ctx.texture((W, H), 4, a.tobytes())


def _field(ctx, values: np.ndarray):
    """A scalar field texture (H, W) of `values`."""
    f = np.zeros((H, W, 4), np.float32)
    f[..., 0] = values
    return ctx.texture((W, H), 4, f.tobytes(), dtype="f4")


def _draw(ctx, name, src, t=0.4, knobs=None, **values) -> np.ndarray:
    st = FxState()
    st.values[name].update(on=True, mix=1.0, **values)
    chain = FxChain(ctx, st)
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    chain.run_one(name, src, out, t, opaque=1, knobs=knobs)
    assert not chain.errors, chain.errors
    got = np.frombuffer(out.read(components=4), np.uint8).reshape(H, W, 4).copy()
    out.release()
    chain.release()
    return got


def test_every_knob_takes_a_field_or_says_why_not():
    st = FxState()
    for name, spec in st.specs.items():
        rates = {k for c in spec.clocks for k in c.factors}
        for p in spec.params:
            why = fx.knob_refusal(spec, p.key)
            if spec.hook:
                assert why and "Python half" in why, (name, p.key)
            elif p.choices:
                assert why and "a choice" in why, (name, p.key)
            elif p.integer:
                assert why and "count" in why, (name, p.key)
            elif p.key in rates:
                assert why and "a rate" in why, (name, p.key)
            else:
                assert why is None, (name, p.key, why)
                assert fx.ports(spec)[1][p.key] == fx.FIELD
        assert not set(fx.field_knobs(spec)) & set(fx.PORT_NAMES)


def test_a_knob_named_as_a_port_is_refused():
    src = 'uniform float u_aux; // @param 0 1 0 "Aux"\nvec4 effect(vec2 uv) { return here(); }\n'
    with pytest.raises(fx.SpecError, match="port's name"):
        fx.parse("x", src)


def test_no_knob_wired_is_the_files_program_string_for_string():
    st = FxState()
    for spec in st.specs.values():
        assert fx.with_knob_fields(spec, ()) == spec.source
        assert fx.knob_declarations(spec, ()) == ("", "")
        plain = fx.fragment_source(st.lib, spec.source, st.common, spec.clocks, spec.makes)
        assert fx.fragment_source(st.lib, spec.source, st.common, spec.clocks, spec.makes,
                                  ("", "")) == plain


def test_every_file_compiles_with_all_its_knobs_wired(ctx):
    st = FxState()
    chain = FxChain(ctx, st)
    for name, spec in st.specs.items():
        keys = tuple(sorted(fx.field_knobs(spec)))[:fx.KNOB_UNITS]
        if keys:
            assert chain._program(name, keys) is not None, (name, chain.errors.get(name))
    chain.release()


@pytest.mark.parametrize("name,key,lo,hi", [
    ("wave", "amount", 0.02, 0.08),
    ("palette", "hue_turn", 30.0, 200.0),
    ("fade", "level", 0.2, 0.9),
])
def test_a_field_varies_a_knob_per_pixel(ctx, name, key, lo, hi):
    spec = FxState().specs[name]
    assert key in fx.field_knobs(spec), fx.knob_refusal(spec, key)
    src = _pictures(ctx)
    zero = _field(ctx, np.zeros((H, W), np.float32))
    # a field of 0: the knob as it is
    assert np.array_equal(_draw(ctx, name, src, knobs={key: (zero, 1.0)}, **{key: lo}),
                          _draw(ctx, name, src, **{key: lo}))
    # half the frame (the top rows in GL's order) pushed from lo to hi, by a depth of 2
    split = np.zeros((H, W), np.float32)
    split[H // 2:] = (hi - lo) / 2.0
    f = _field(ctx, split)
    got = _draw(ctx, name, src, knobs={key: (f, 2.0)}, **{key: lo})
    at_lo, at_hi = _draw(ctx, name, src, **{key: lo}), _draw(ctx, name, src, **{key: hi})
    # (read back in GL's row order: row 0 is the field's row 0)
    assert np.abs(got[: H // 2].astype(int) - at_lo[: H // 2]).max() <= 1
    assert np.abs(got[H // 2:].astype(int) - at_hi[H // 2:]).max() <= 1
    assert not np.array_equal(at_lo, at_hi)
    for o in (src, zero, f):
        o.release()


def test_a_knob_stays_in_its_range_or_wraps(ctx):
    src = _pictures(ctx)
    big = _field(ctx, np.full((H, W), 50.0, np.float32))
    # Fade's level clamps to its top
    st = FxState()
    p = next(p for p in st.specs["fade"].params if p.key == "level")
    assert np.array_equal(_draw(ctx, "fade", src, knobs={"level": (big, 1.0)}, level=0.5),
                          _draw(ctx, "fade", src, level=p.hi))
    # Palette's Hue turn wraps (0 … 360): +360 is where it was
    turn = next(p for p in st.specs["palette"].params if p.key == "hue_turn")
    assert turn.wrap
    whole = _field(ctx, np.full((H, W), turn.hi - turn.lo, np.float32))
    assert np.abs(_draw(ctx, "palette", src, knobs={"hue_turn": (whole, 1.0)}, hue_turn=40.0)
                  .astype(int) - _draw(ctx, "palette", src, hue_turn=40.0)).max() <= 1
    for o in (src, big, whole):
        o.release()


def test_a_refused_knob_is_left_out_of_the_pass(ctx):
    """A choice handed a field (a wire the graph would refuse) draws as unwired."""
    src = _pictures(ctx)
    f = _field(ctx, np.full((H, W), 1.0, np.float32))
    assert np.array_equal(_draw(ctx, "wave", src, knobs={"along": (f, 1.0)}),
                          _draw(ctx, "wave", src))
    for o in (src, f):
        o.release()


# ---------------------------------------------------------------- the graph

def _wired(*wires, nodes=("line", "wave")):
    """A wired frame: shape into the scene, `nodes` declared, `wires` (pairs,
    or dicts with a depth)."""
    return {"frame": "wired", "nodes": [{"kind": "effect", "file": n} for n in nodes],
            "wires": [{"from": "shape", "to": "scene.geometry"},
                      *(w if isinstance(w, dict) else {"from": w[0], "to": w[1]} for w in wires)]}


def _spec(section):
    from hyperspace import graph as G
    return G.read_graph(section, effects=set(FxState().specs))


def test_a_field_into_a_knob_stands_and_keeps_its_depth():
    from hyperspace import graph as G
    sec = _wired(("scene", "wave.image"), ("wave", "output.all.image"),
                 {"from": "line", "to": "wave.amount", "depth": 0.25})
    spec = _spec(sec)
    assert not spec.notes, spec.notes
    w = next(w for w in spec.wires if w.dst == "wave.amount")
    assert w.depth == 0.25
    assert w.to_json() == {"from": "line", "to": "wave.amount", "depth": 0.25}
    # a depth of 1 is not written: every other wire is saved as it was
    assert G.Wire("line", "wave.amount").to_json() == {"from": "line", "to": "wave.amount"}
    # the depth is not part of what the wire is
    assert G.Wire("line", "wave.amount", 0.5) == G.Wire("line", "wave.amount")
    # read back as written
    again = _spec({**sec, "wires": [x.to_json() for x in spec.wires]})
    assert next(w for w in again.wires if w.dst == "wave.amount").depth == 0.25
    from hyperspace import patches
    assert patches.wire_type(w, patches.INTO) == G.FIELD     # the one lookup


@pytest.mark.parametrize("port,said", [
    ("along", "Wave's Along is a choice: a choice takes no field"),
    ("steps", "Wave's Steps is a whole number (it counts): a count takes no field"),
    ("drift", "Wave's Drift is a rate: its clock turns once for the whole frame"),
])
def test_a_knob_that_takes_no_field_says_why(port, said):
    spec = _spec(_wired(("scene", "wave.image"), ("wave", "output.all.image"),
                        ("line", f"wave.{port}")))
    assert any(said in n for n in spec.notes), spec.notes


def test_a_depth_is_a_knobs_alone():
    spec = _spec(_wired(("wave", "output.all.image"),
                        {"from": "scene", "to": "wave.image", "depth": 2.0}))
    assert any("only a field into a knob takes one" in n for n in spec.notes), spec.notes


@pytest.mark.parametrize("depth", ["2", None, float("nan"), True])
def test_a_depth_that_is_no_number_is_refused(depth):
    from hyperspace import graph as G
    with pytest.raises(G.GraphError, match="depth is a number"):
        G.read_graph(_wired({"from": "line", "to": "wave.amount", "depth": depth}),
                     effects=set(FxState().specs))


def test_a_picture_into_a_knob_names_to_field():
    spec = _spec(_wired(("scene", "wave.image"), ("wave", "output.all.image"),
                        ("scene", "wave.amount")))
    assert any("put a To field (tofield) between" in n for n in spec.notes), spec.notes


def test_the_graph_and_fx_name_the_ports_alike():
    from hyperspace import graph as G
    assert G.PORT_NAMES == fx.PORT_NAMES


def _render(ctx, section, values):
    sys_path_tests()
    from test_graph_faces import _faces, _fbo, _px

    from hyperspace.outputs import Switches, View
    from hyperspace.render import Renderer
    r = Renderer(ctx)
    r.ghost.state.on = False
    r.wiring = _spec(section).wiring()
    for name, v in values.items():
        r.fx.state.values[name].update(on=True, **v)
    vs = [View(Switches(), (160, 120), target=_fbo(ctx, 160, 120))]
    r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    return _px(vs[0].target).astype(int)


def sys_path_tests():
    import sys
    from pathlib import Path
    p = str(Path(__file__).parent)
    if p not in sys.path:
        sys.path.insert(0, p)


def test_a_field_on_a_knob_moves_the_picture_in_all_outputs_run(ctx):
    """Line into Wave's Amount, wired on `output.all` as patches are: a depth
    of 0 draws what no field draws; a depth moves the picture."""
    plain = _wired(("scene", "wave.image"), ("wave", "output.all.image"))
    values = {"line": {"angle": 0.0}, "wave": {"amount": 0.0, "waves": 2.0}}
    alone = _render(ctx, plain, values)

    def with_depth(d):
        return _render(ctx, _wired(("scene", "wave.image"), ("wave", "output.all.image"),
                                   {"from": "line", "to": "wave.amount", "depth": d}), values)
    assert np.array_equal(with_depth(0.0), alone)
    assert alone[..., :3].max() > 30                       # a picture, not black
    moved = with_depth(0.1)
    assert (np.abs(moved - alone).max(axis=2) > 20).mean() > 0.005


def test_graph_draws_a_knobs_field_port_once_wired():
    from hyperspace import graph as G
    from hyperspace import graphview
    from hyperspace.outputs import Switches
    from hyperspace.params import Registry
    from hyperspace.routing import Bindings
    sys_path_tests()
    from test_graphview import views, wired_wiring

    def ports(section):
        spec = _spec(section)
        g = G.build_graph(views(Switches()), wired_wiring(spec.wiring()), effects=("line", "wave"))
        view = graphview.build(Bindings(), Registry(), None, None, g, spec)
        return {p.id for n in view.nodes for p in n.ports}
    plain = ports(_wired(("scene", "wave.image"), ("wave", "output.all.image")))
    assert "rin:wave/image" in plain and "rin:wave/amount" not in plain
    wired = ports(_wired(("scene", "wave.image"), ("wave", "output.all.image"),
                         ("line", "wave.amount")))
    assert "rin:wave/amount" in wired and "rin:wave/waves" not in wired


def test_a_field_dropped_on_a_knobs_row_is_its_port():
    from hyperspace import graphview
    assert graphview.knob_pin("param:fx.wave.amount") == "rin:wave/amount"
    assert graphview.knob_pin("base:fx.wave.2.amount") == "rin:wave.2/amount"
    assert graphview.knob_pin("mod:fx.wave.along") == "rin:wave/along"    # refused in words
    assert graphview.knob_pin("param:fx.wave.no_such") is None
    assert graphview.knob_pin("param:lfo.1.rate") is None
    assert graphview.knob_pin("rin:wave/image") is None


def test_a_knobs_field_is_wired_on_its_row_and_its_depth_set_and_saved(tmp_path):
    """On GRAPH: a field cable dropped on Wave's Amount row wires
    `line → wave.amount`; its menu's depth lands one undo step, saved in the
    loadable patch as the wire's `depth`; a field dropped on Along is refused
    in words, nothing changed."""
    sys_path_tests()
    from test_graph_wires import _edit_rig

    from hyperspace import graph as G
    from hyperspace import graphview
    rig, stub, edit, pushed = _edit_rig(tmp_path)
    assert edit.add_node("effect", "line") is None
    assert edit.add_node("effect", "wave") is None
    n = len(pushed)
    assert edit.wire("rout:line", "param:fx.wave.amount") is None
    w = next(w for w in rig.loaded_patch.graph.spec.wires if w.dst == "wave.amount")
    assert w == G.Wire("line", "wave.amount") and w.depth == 1.0
    choices = dict(graphview.depth_choices(w))
    assert set(choices) >= {1.0, 0.5, -0.5, 0.125, 0.0625}        # Amount spans 0 … 0.5
    assert edit.set_depth(w, 0.125) is None
    assert len(pushed) == n + 2
    w = next(w for w in rig.loaded_patch.graph.spec.wires if w.dst == "wave.amount")
    assert w.depth == 0.125
    assert {"from": "line", "to": "wave.amount", "depth": 0.125} in rig.loaded_patch.graph.doc["wires"]
    assert next(x for x in stub.wiring.wires if x.dst == "wave.amount").depth == 0.125
    said = edit.wire("rout:line", "base:fx.wave.along")
    assert said is not None and "a choice takes no field" in said
    assert graphview.depth_choices(G.Wire("scene", "wave.image")) == []


def test_a_field_wired_only_into_a_knob_reaches_on_graph_and_the_fx_pane():
    """Line into Wave's Amount reaches what Wave reaches: GRAPH draws it lit
    and the FX pane groups it with Wave, not under "reaches nothing"."""
    from hyperspace import graphview, ui_fx
    spec = _spec(_wired(("scene", "wave.image"), ("wave", "output.all.image"),
                        ("line", "wave.amount")))
    assert "line" not in graphview.unreached(spec)
    groups = dict(ui_fx.groups(spec))
    assert "line" in groups.get("Run", []), groups
    assert "reaches nothing" not in groups


def test_a_depth_changed_alone_reaches_the_picture(ctx):
    """Devin's review of #497: a wire's depth is not part of what the wire is,
    so a wiring that differs only in a depth compared equal and the renderer
    kept its cached graph, drawing the old depth. Change the depth alone after
    a frame is drawn: the next frame draws the new one."""
    sys_path_tests()
    from test_graph_faces import _faces, _fbo, _px

    from hyperspace.outputs import Switches, View
    from hyperspace.render import Renderer

    def section(d):
        return _wired(("scene", "wave.image"), ("wave", "output.all.image"),
                      {"from": "line", "to": "wave.amount", "depth": d})
    r = Renderer(ctx)
    r.ghost.state.on = False
    r.fx.state.values["line"].update(on=True, angle=0.0)
    r.fx.state.values["wave"].update(on=True, amount=0.0, waves=2.0)
    vs = [View(Switches(), (160, 120), target=_fbo(ctx, 160, 120))]

    def draw(d):
        r.wiring = _spec(section(d)).wiring()
        r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0)
        return _px(vs[0].target).astype(int)
    still = draw(0.0)
    assert not np.array_equal(draw(0.1), still)
    assert np.array_equal(draw(0.0), still)


def test_deleting_a_field_node_before_a_knob_keeps_the_depth_or_lets_go(tmp_path):
    """Devin's review of #497: a node deleted out of a chain is bypassed — what
    fed it wired on into what it fed. Into a knob the bypass keeps the cable's
    depth; where what fed it is a picture (To field's input), a knob or field
    port cannot take it, so that cable goes and the deletion lands."""
    sys_path_tests()
    from test_graph_wires import _edit_rig
    rig, _, edit, _ = _edit_rig(tmp_path)
    for f in ("line", "scale", "wave", "tofield", "displace"):
        assert edit.add_node("effect", f) is None
    assert edit.wire("rout:line", "rin:scale/image") is None
    assert edit.wire("rout:scale", "rin:wave/amount") is None
    w = next(w for w in rig.loaded_patch.graph.spec.wires if w.dst == "wave.amount")
    assert edit.set_depth(w, 0.125) is None
    assert edit.drop_node("scale") is None
    got = [w for w in rig.loaded_patch.graph.spec.wires if w.dst == "wave.amount"]
    assert [(w.src, w.depth) for w in got] == [("line", 0.125)]
    # a picture fed To field: neither the knob nor Displace's field port takes it
    assert edit.wire("scene", "tofield.image") is None
    assert edit.wire("rout:tofield", "rin:wave/waves") is None
    assert edit.wire("rout:tofield", "rin:displace/field") is None
    assert edit.drop_node("tofield") is None
    wires = rig.loaded_patch.graph.spec.wires
    assert not [w for w in wires if w.dst in ("wave.waves", "displace.field")]
