"""Plan 67 F1 — the field wire (the owner, 2026-11-22: "Field is its own wire").

A field is a value, or a pair, at every pixel: float32 at the frame's size,
signed and unbounded, its .a 0 for a scalar and 1 for a vector. Effect files
make and take one by saying so (`// @makes field`, `// @takes <port> field`);
the first were Measure — now Point, Line, Rings, Spokes, Cells and Noise (generators, no input; plan 67 §15) — and To field (picture → field),
and Displace reads one on its new `field` port. What is held here:

- the types and the directives: `graph.FIELD` is `fx.FIELD`; each file's ports;
- the wire checks, in words: a field into a field port; a field into a picture
  port, promoted to grey; a picture into a field port refused, naming the
  converter; no port where a file has none;
- the build: a field maker is a `FieldEffect`, made once a frame into a float32
  target and read by every consumer; a picture port reads it through one
  `FieldPicture`; Displace's field port holds it;
- on the GPU: the field is raw (negative, past 1), shown grey into anything
  that is no field target; off it is no field; Displace moves the picture by it;
  To field reads mid-grey as 0;
- GRAPH: the ports a field maker draws, the field cable's type, its thumbnail."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace import fx
from hyperspace import graph as G
from hyperspace.fx import FxChain, FxState, SpecError, parse, ports_of

sys.path.insert(0, str(Path(__file__).parent))

moderngl = pytest.importorskip("moderngl")

W, H = 64, 48


def wired(*pairs, nodes=("rings", "displace")):
    return {"frame": "wired", "nodes": [{"kind": "effect", "file": n} for n in nodes],
            "wires": [{"from": "shape", "to": "scene.geometry"},
                      *({"from": a, "to": b} for a, b in pairs)]}


BASIC = wired(("scene", "displace.image"), ("rings", "displace.field"),
              ("displace", "output.1.image"), ("rings", "output.2.image"))


def _spec(section):
    return G.read_graph(section, effects=set(FxState().specs))


# ---------------------------------------------------------------- types and files

def test_the_field_type_is_one_word_in_both_modules():
    assert G.FIELD == fx.FIELD == "field" and G.FIELD in G.PORT_TYPES
    assert G.FIELD_PORT == fx.FIELD_PORT == "field"
    assert G.TYPE_WORDS[G.FIELD] == "a field"


def test_each_file_says_what_its_ports_carry():
    assert ports_of("rings") == ("field", {"aux": "image", "field": "field"})   # no input; a point
    assert ports_of("tofield") == ("field", {"image": "image", "aux": "image"})
    assert ports_of("displace") == ("image", {"image": "image", "aux": "image", "field": "field"})
    assert ports_of("wave") == ("image", {"image": "image", "aux": "image"})
    assert ports_of("no_such_file") == ("image", {"image": "image", "aux": "image"})


def test_a_bad_directive_is_refused_in_words():
    body = "vec4 effect(vec2 uv) { return vec4(0.0); }\n"
    with pytest.raises(SpecError, match="@makes 'colour': image or field"):
        parse("x", "// @makes colour\n" + body)
    with pytest.raises(SpecError, match="@takes 'aux field'"):
        parse("x", "// @takes aux field\n" + body)      # the aux stays a picture
    with pytest.raises(SpecError, match="@takes 'image mask'"):
        parse("x", "// @takes image mask\n" + body)


# ---------------------------------------------------------------- the wire checks

def test_a_field_goes_into_a_field_port_and_into_a_picture_port():
    spec = _spec(BASIC)
    assert not spec.notes, spec.notes


@pytest.mark.parametrize("pair, said", [
    (("scene", "displace.field"),
     "scene makes a picture, displace.field takes a field — put a To field (tofield) between"),
    (("scene", "rings.image"), "rings has no port 'image'"),
    (("rings", "wave.field"), "wave has no port 'field'"),
])
def test_a_wire_a_field_cannot_take_is_refused_in_words(pair, said):
    spec = _spec(wired(pair, nodes=("rings", "displace", "wave")))
    assert any(said in n for n in spec.notes), spec.notes


def test_a_field_is_no_mask():
    section = wired(("scene", "cut.image"), ("rings", "cut.mask"), ("cut", "output.1.image"),
                    nodes=("rings",))
    section["nodes"].append({"kind": "cut"})
    spec = _spec(section)
    assert any("rings makes a field, cut.mask takes a mask" in n for n in spec.notes), spec.notes


# ---------------------------------------------------------------- the build

def _views(ctx, n=2):
    from test_graph_faces import _fbo

    from hyperspace.outputs import Switches, View
    return [View(Switches(), (160, 120), target=_fbo(ctx, 160, 120)) for _ in range(n)]


def _rig(ctx, section, values):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    spec = _spec(section)
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    for name, v in values.items():
        r.fx.state.values[name].update(v)
    return r


ON = {"rings": {"on": True}, "displace": {"on": True, "mix": 1.0, "amount": 0.1}}


def _draw(ctx, r, n=2):
    from test_graph_faces import _faces, _px

    vs = _views(ctx, n)
    r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target) for v in vs]


def test_the_build_makes_the_field_once_and_promotes_it_for_a_picture_port(ctx):
    r = _rig(ctx, BASIC, ON)
    _draw(ctx, r)
    g = r._graph
    m, d = g.nodes["rings"], g.nodes["displace"]
    assert isinstance(m, G.FieldEffect) and m.OUTPUT == G.FIELD
    assert isinstance(d, G.Effect) and d.inputs["field"] is m and d.INPUTS["field"] == G.FIELD
    pic = g.nodes["rings(picture)"]
    assert isinstance(pic, G.FieldPicture) and pic.inputs["field"] is m
    assert r.stats["effects"].count("rings") == 1          # once, for both readers
    assert not g.dormant


def test_the_promoted_field_is_grey_about_the_middle(ctx):
    """Rings from the centre: 0 there (mid-grey), growing to the corners."""
    _, out2 = _draw(ctx, _rig(ctx, BASIC, ON))
    h, w = out2.shape[:2]
    centre = out2[h // 2, w // 2, :3].astype(int)
    corner = out2[2, 2, :3].astype(int)
    assert np.all(np.abs(centre - 128) <= 2)
    assert corner[0] == corner[1] == corner[2] and corner[0] > 200
    r = h / 2 / h * np.hypot(w / h, 1.0)                      # (the corner, in frame heights)
    assert abs(corner[0] - 255 * (0.5 + 0.5 * min(r, 1.0))) < 12


def test_displace_moves_the_picture_by_the_field_and_not_without_it(ctx):
    moved, _ = _draw(ctx, _rig(ctx, BASIC, ON))
    still = _rig(ctx, BASIC, {**ON, "displace": {**ON["displace"], "amount": 0.0}})
    plain, _ = _draw(ctx, still)
    assert np.abs(moved.astype(int) - plain.astype(int)).max() > 30
    off = _rig(ctx, BASIC, {**ON, "rings": {"on": False}})   # off: no field, nothing moves
    same, grey = _draw(ctx, off)
    assert np.array_equal(same, plain)
    assert np.all(np.abs(grey[..., :3].astype(int) - 128) <= 1)


# ---------------------------------------------------------------- on the GPU, one pass

def _pass(ctx, name, values, picture=None, dtype="f4", field=None):
    st = FxState()
    st.values[name].update(on=True, **values)
    chain = FxChain(ctx, st)
    src = ctx.texture((W, H), 4, (picture if picture is not None
                                  else np.zeros((H, W, 4), np.uint8)).tobytes())
    tex = ctx.texture((W, H), 4, dtype=dtype)
    out = ctx.framebuffer(color_attachments=[tex])
    chain.run_one(name, src, out, 0.0, opaque=1, res=(W, H), field=field)
    assert chain.errors == {} and ctx.error == "GL_NO_ERROR"
    np_t = np.float32 if dtype == "f4" else np.uint8
    got = np.frombuffer(out.read(components=4, dtype=dtype), np_t).reshape(H, W, 4).copy()
    return got, tex


def test_a_field_is_raw_signed_and_unbounded(ctx):
    got, _ = _pass(ctx, "line", {"scale": 4.0})   # the line, across, × 4
    x = ((np.arange(W) + 0.5) / W - 0.5) * (W / H) * 4.0
    assert np.allclose(got[H // 2, :, 0], x, atol=1e-4)
    assert got[..., 0].min() < -2.0 and got[..., 0].max() > 2.0
    assert np.all(got[..., 3] == 0.0)                              # a scalar
    vec, _ = _pass(ctx, "line", {"out": 1, "angle": 0.0})
    assert np.allclose(vec[..., 0], 1.0) and np.allclose(vec[..., 1], 0.0, atol=1e-6)
    assert np.all(vec[..., 3] == 1.0)                              # a vector


def test_into_a_target_that_is_no_field_it_shows_grey(ctx):
    """A preview, a thumbnail's card: the same pass into RGBA8 is the grey."""
    got, _ = _pass(ctx, "line", {"scale": 1.0}, dtype="f1")
    row = got[H // 2, :, 0].astype(int)
    assert np.all(np.diff(row) >= 0) and row[0] < 60 and row[-1] > 195
    assert np.all(got[..., 0] == got[..., 1]) and np.all(got[..., 3] == 255)


def test_to_field_reads_mid_grey_as_zero_signed(ctx):
    pic = np.zeros((H, W, 4), np.uint8)
    pic[...] = (128, 128, 128, 255)
    pic[:, : W // 2] = (255, 255, 255, 255)
    got, _ = _pass(ctx, "tofield", {"read": 0, "about": 0}, picture=pic)
    assert np.allclose(got[:, W - 4, 0], 2 * 128 / 255 - 1, atol=1e-3)
    assert np.allclose(got[:, 4, 0], 1.0, atol=1e-3)
    un, _ = _pass(ctx, "tofield", {"read": 0, "about": 1}, picture=pic)
    assert np.allclose(un[:, 4, 0], 1.0, atol=1e-3) and np.allclose(un[:, W - 4, 0], 128 / 255,
                                                                     atol=1e-3)
    rg, _ = _pass(ctx, "tofield", {"read": 2}, picture=pic)
    assert np.all(rg[..., 3] == 1.0)


def test_displace_pushes_a_column_by_a_constant_vector_field(ctx):
    """A vector field (1, 0) everywhere, Amount 0.25: the picture is read a
    quarter of a frame height to the right, so a white column moves left by
    that many pixels."""
    _, field = _pass(ctx, "line", {"out": 1, "angle": 0.0})
    pic = np.zeros((H, W, 4), np.uint8)
    pic[..., 3] = 255
    pic[:, W // 2, :3] = 255
    got, _ = _pass(ctx, "displace", {"mix": 1.0, "amount": 0.25}, picture=pic, dtype="f1",
                   field=field)
    col = int(np.argmax(got[H // 2, :, 0]))
    assert abs(col - (W // 2 - 0.25 * H)) <= 1, col


# ---------------------------------------------------------------- GRAPH

def test_the_canvas_draws_a_field_maker_and_a_field_cable(tmp_path):
    from test_graph_edit import wired_rig
    from test_graphview import views

    from hyperspace import graphview
    from hyperspace.outputs import Switches

    rig, _, _ = wired_rig(tmp_path, BASIC)
    spec = rig.loaded_patch.graph.spec
    assert not spec.notes, spec.notes
    g = G.build_graph(views(Switches(), Switches()), spec.wiring())
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    m = view.node("render:rings")
    ins = {p.name for p in m.ports if p.direction == graphview.IN}
    outs = [p for p in m.ports if p.direction == graphview.OUT]
    assert "image" not in ins and outs and outs[0].type == graphview.FIELD
    d = view.node("render:displace")
    assert any(p.name == "field" and p.type == graphview.FIELD for p in d.ports)
    into = {c.dst_port: c.type for c in view.cables if c.src_port == "rout:rings"}
    assert into["rin:displace/field"] == graphview.FIELD
    assert into["rin:output.2/image"] == graphview.FIELD           # promoted, still a field cable


def test_a_field_nodes_thumbnail_is_its_grey(ctx):
    """The page wants Rings' thumbnail: it is the field the frame made, grey
    (rings: mid-grey at the centre, lighter at the corners), never made for it."""
    r = _rig(ctx, BASIC, ON)
    _draw(ctx, r)
    r.thumbs.want({"rings": "picture"})
    _draw(ctx, r)
    assert not r.thumbs.error and r.thumbs.count >= 1
    tex = r.thumbs.get("rings")
    assert tex is not None
    w, h = tex.size
    px = np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4)
    assert abs(int(px[h // 2, w // 2, 0]) - 128) <= 6 and int(px[1, 1, 0]) > 190


def test_a_field_reaches_displace_in_all_outputs_run(ctx):
    """Displace wired into `output.all.image` is in All outputs' run, where it
    paints by `Effect._pass` (plan 80) rather than `_one`: the field must reach
    it there too. The merge of plan 80 once left it out of that path, so on the
    rig the field examples (all wired to `output.all`) moved nothing while these
    tests, wired to `output.1`, passed (the owner, 2026-11-24)."""
    from test_graph_faces import _faces, _px

    from hyperspace.render import Renderer

    section = wired(("scene", "displace.image"), ("rings", "displace.field"),
                    ("displace", "output.all.image"))
    shots = []
    for amount in (0.0, 0.15):
        r = Renderer(ctx)
        r.ghost.state.on = False
        r.wiring = _spec(section).wiring()
        r.fx.state.values["rings"].update(on=True, out=1)
        r.fx.state.values["displace"].update(on=True, amount=amount)
        vs = _views(ctx, 1)
        r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0)
        assert ctx.error == "GL_NO_ERROR"
        assert r.stats["effects"] == ["rings", "displace"]
        shots.append(_px(vs[0].target).astype(int))
    assert shots[0][..., :3].max() > 30                       # a picture, not black
    assert (np.abs(shots[1] - shots[0]).max(axis=2) > 20).mean() > 0.05


def test_a_field_generator_wired_into_a_reader_reaches():
    """GRAPH's `unreached`: an effect no wire feeds reads nothing (R15) — but a
    field generator takes no picture by design, so Rings wired into
    Displace's field port reaches, is drawn lit, and its thumbnail is its
    field, not the test card (the owner's screenshot, 2026-11-24, said
    "reaches nothing"). Unwired, it reaches nothing as before."""
    from hyperspace import graphview

    spec = _spec(wired(("scene", "displace.image"), ("rings", "displace.field"),
                       ("displace", "output.all.image")))
    assert "rings" not in graphview.unreached(spec)
    alone = _spec(wired(("scene", "displace.image"), ("displace", "output.all.image")))
    assert "rings" in graphview.unreached(alone)


def _shots(ctx, section, values):
    """Output 1 drawn twice, Displace's Amount 0 then 0.15."""
    from test_graph_faces import _faces, _px

    from hyperspace.render import Renderer

    shots = []
    for amount in (0.0, 0.15):
        r = Renderer(ctx)
        r.ghost.state.on = False
        spec = _spec(section)
        assert not spec.notes, spec.notes
        r.wiring = spec.wiring()
        for name, v in values.items():
            r.fx.state.values[name].update(v)
        r.fx.state.values["displace"].update(on=True, amount=amount)
        vs = _views(ctx, 1)
        r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0)
        assert ctx.error == "GL_NO_ERROR"
        shots.append(_px(vs[0].target).astype(int))
    return shots


def test_a_keyed_displace_still_reads_its_field(ctx):
    """Plan 87's black is clear builds a keyed node through a `KeyNode`; the
    field binds to the effect behind it, as its aux does (Devin's review of
    #489: a keyed Displace dropped its field)."""
    section = {**wired(("scene", "displace.image"), ("rings", "displace.field"),
                       ("displace", "output.1.image")), "keys": ["displace"]}
    a, b = _shots(ctx, section, {"rings": {"on": True, "out": 1}})
    assert (np.abs(b - a).max(axis=2) > 20).mean() > 0.05


def test_a_displace_slot_takes_a_field(ctx):
    """A picture effect's slot takes what its effect takes (plan 89 + 67): a
    field wired into `displace.slot.2.field` is accepted and moves that slot's
    picture (Devin's review of #489: the canvas drew the port, the wire was
    refused)."""
    section = wired(("scene", "displace.slot.2.image"), ("rings", "displace.slot.2.field"),
                    ("displace.slot.2", "output.1.image"))
    section["nodes"] = [{"kind": "effect", "file": "rings"},
                        {"kind": "effect", "file": "displace", "slots": 2}]
    a, b = _shots(ctx, section, {"rings": {"on": True, "out": 1}})
    assert (np.abs(b - a).max(axis=2) > 20).mean() > 0.05
