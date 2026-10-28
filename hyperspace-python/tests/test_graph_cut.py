# ruff: noqa: F811 — `ctx` is test_graph_faces' fixture, taken as each GL test's argument
"""Plan 39 T3 — `cut`: picture + mask → picture (W3; decisions 1 and 6).

`cut[.n]` takes the picture on its `image` port and the mask on its `mask`
port: where the mask passes the picture, elsewhere cut away to transparent
black (premultiplied, so colour and alpha go together) — on a
`composite.over` what is under shows through. `cut.amount` how far (1 to
nothing, 0.5 the cut part dimmed by half), `cut.invert` keeps the hole and
cuts the rest. No mask wired, or a mask making nothing: its picture
through, untouched. The mask is sampled bilinearly at the picture's size,
fitted by cover, flipped for a mask whose rows are top first (`mask_of`:
the flag T4's segment sets).

What it must keep honest: the hole is transparent before any composite;
the under shows through it on one; the mask lands the right way up; no
mask is byte-identical to the picture; the `/7` round trip of the entry
and its values (`cut-out`, the fixture the goldens draw). The GL tests use
test_graph_faces' harness and skip without a standalone context."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from test_graph_faces import (
    Still,
    _fbo,
    _media,
    _px,
    _rgba,
    ctx,  # noqa: F401 — the GL context fixture, taken as each GL test's argument
)
from test_graph_resize import FACTORY_FRAME
from test_graph_wired import wired

from hyperspace import graph as G
from hyperspace import params, view
from hyperspace.outputs import Switches, View
from hyperspace.view import CutState, MatteState, ResizeState

CUT = {"kind": "cut"}
CUT2 = {"kind": "cut", "instance": 2}
MATTE = {"kind": "matte"}
COMPOSITE = {"kind": "composite"}
RESIZE = {"kind": "resize"}
FIXTURE = Path(__file__).parent / "fixtures" / "presets" / "cut-out.json"


def _read(*pairs, nodes=(CUT, MATTE)):
    return G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=list(nodes)))


def _spec(*pairs, nodes=(CUT, MATTE)):
    spec = _read(*pairs, nodes=nodes)
    assert not spec.notes, spec.notes
    return spec


def _views(n=2, size=(64, 48)):
    return [View(Switches(), size) for _ in range(n)]


def _chain(n):
    """An output's picture past its end (`Shown`)."""
    while isinstance(n, G.Shown):
        n = n.inputs["image"]
    return n


# ---------------------------------------------------------------- the node and its entry

def test_the_cut_node_says_what_it_is():
    assert G.CutNode.KIND == "cut" and G.CutNode.TIMED
    assert G.CutNode.INPUTS == {"image": G.IMAGE, "mask": G.MASK}
    assert G.CutNode.OUTPUT == G.IMAGE
    assert G.WIRED_MAKES["cut"] == G.IMAGE
    assert G.WIRED_TAKES["cut"] == {"image": G.IMAGE, "mask": G.MASK}
    assert "cut" in G.DECLARED and "cut" in G.RESERVED
    assert G.wire_node_kind("cut", wired=True) == "cut"
    assert G.wire_node_kind("cut.2", wired=True) == "cut"
    assert G.wire_node_kind("cut.1", wired=True) is None
    # (an effect file named cut… is still an effect: only the word itself is reserved)
    assert G.wire_node_kind("cutter", wired=True) == "effect"


def test_a_cut_entry_round_trips():
    for e in (CUT, CUT2):
        name = G.CutAt(e.get("instance", 1)).name
        spec = G.read_graph(wired(("channel.a", f"{name}.image"), nodes=[e]))
        assert spec.cuts == (G.CutAt(e.get("instance", 1)),)
        assert G.read_graph(spec.to_json()).to_json() == spec.to_json()
        assert e in spec.to_json()["nodes"]
    with pytest.raises(G.GraphError):
        G.read_graph(wired(nodes=[{"kind": "cut", "instance": 0}]))
    with pytest.raises(G.GraphError):
        G.read_graph(wired(nodes=[{"kind": "cut", "amount": 0.5}]))


def test_a_cut_must_be_declared():
    spec = _read(("channel.a", "cut.image"), ("cut", "output.2.image"), nodes=())
    assert spec.notes and all('add one: {"kind": "cut"}' in n for n in spec.notes), spec.notes


# ---------------------------------------------------------------- the type rule

def test_a_picture_into_the_cut_mask_names_the_matte():
    spec = _read(("channel.a", "cut.image"), ("channel.b", "cut.mask"),
                 ("cut", "output.2.image"))
    assert spec.notes == (("wire channel.b → cut.mask — channel.b makes a picture, "
                           "cut.mask takes a mask — put a matte between"),)
    _spec(("channel.a", "cut.image"), ("channel.b", "matte.image"), ("matte", "cut.mask"),
          ("cut", "output.2.image"))


def test_a_cut_is_a_picture_wherever_one_is_taken():
    nodes = [CUT, MATTE, {"kind": "matte", "instance": 2}, COMPOSITE,
             {"kind": "effect", "file": "acid", "instance": 2}]
    for dst in ("output.2.image", "composite.over", "composite.under", "acid.2.image",
                "shape.faces", "matte.2.image"):
        spec = G.read_graph(wired(("channel.a", "cut.image"), ("cut", dst),
                                  ("channel.b", "matte.image"), ("matte", "cut.mask"),
                                  *FACTORY_FRAME, nodes=nodes))
        assert not spec.notes, (dst, spec.notes)
    # … and never a mask
    spec = _read(("channel.a", "cut.image"), ("cut", "lookback.cover"),
                 ("scene", "lookback.image"), ("lookback", "output.2.image"))
    assert spec.notes and "put a matte between" in spec.notes[0], spec.notes


# ---------------------------------------------------------------- the build

def test_a_cut_takes_the_mask_itself_and_its_picture():
    spec = _spec(("channel.a", "cut.image"), ("channel.b", "matte.image"),
                 ("matte", "cut.mask"), ("cut", "output.2.image"))
    g = G.build_graph(_views(), spec.wiring())
    cut, matte = g.nodes["cut"], g.nodes["matte"]
    assert isinstance(cut, G.CutNode) and isinstance(matte, G.MatteNode)
    assert cut.inputs["image"] is g.nodes["channel.a"]
    assert cut.inputs["mask"] is matte                   # the mask, not its picture
    assert not [n for n in g.nodes.values() if isinstance(n, G.MaskPicture)]
    assert _chain(g.outputs[1].inputs["image"]) is cut
    order = [n.name for n in g.order]
    assert order.index("matte") < order.index("cut") and "cut" in g.timed


def test_a_cut_fed_no_picture_is_not_built_and_one_with_no_mask_is():
    g = G.build_graph(_views(), _spec(("cut", "output.2.image")).wiring())
    assert not [n for n in g.nodes.values() if isinstance(n, G.CutNode)]
    assert g.dormant["cut"] == "cut is fed by nothing here: wire its image"
    g = G.build_graph(_views(), _spec(("channel.a", "cut.image"),
                                      ("cut", "output.2.image")).wiring())
    assert g.nodes["cut"].inputs["mask"] is None


def test_a_mask_whose_rows_are_top_first_is_flagged():
    """The flip flag's shape (T4 sets it): a mask maker's
    `rows_top_first(frame)`; none, False. `native` before `image`."""

    class Native(G.Node):
        OUTPUT = G.MASK

        def native(self, frame):
            return "native"

        def image(self, frame):
            return "image"

    class TopFirst(Native):
        def rows_top_first(self, frame):
            return True

    class Plain(G.Node):
        OUTPUT = G.MASK

        def image(self, frame):
            return "image"

    assert G.mask_of(Native("m"), None) == ("native", False)
    assert G.mask_of(TopFirst("m"), None) == ("native", True)
    assert G.mask_of(Plain("m"), None) == ("image", False)


def test_the_canvas_knows_the_cut():
    from hyperspace import graphview

    assert graphview.LABELS["cut"] == "Cut" and graphview.HOVERS["cut"]
    assert graphview.FRAME_CLASS["cut"] is G.CutNode
    assert graphview.PICKER_GROUP["cut"] == "masks"
    stand = graphview._stand_in("cut.2")
    assert isinstance(stand, G.CutNode) and stand.name == "cut.2"
    owner = graphview.OWNERS["cut"]
    assert owner("cut.2.amount", None) == "cut.2" and owner("cut.invert", None) == "cut"
    assert graphview._node_name({"kind": "cut", "instance": 3}) == "cut.3"


# ---------------------------------------------------------------- the params

def test_declare_cuts_comes_and_goes():
    reg = params.Registry()
    got = params.declare_cuts(reg, ["cut", "cut.2"])
    ids = params.cut_ids("cut") + params.cut_ids("cut.2")
    assert sorted(got) == sorted(ids) and len(ids) == 4
    for pid in ids:
        assert reg[pid].group == params.CUT_GROUP == "cut", pid
        assert reg[pid].modulatable, pid
        assert params.is_cut_id(pid), pid
    st = CutState()
    assert (st.invert, st.amount) == (False, 1.0)
    assert reg["cut.invert"].value is False and reg["cut.amount"].value == 1.0
    assert (reg["cut.amount"].lo, reg["cut.amount"].hi) == (0.0, 1.0)
    gone = params.declare_cuts(reg, ["cut"])
    assert sorted(gone) == sorted(params.cut_ids("cut.2"))
    assert "cut.2" not in reg.cut_state
    reg["cut.amount"].set(0.5)
    assert reg.cut_state["cut"].amount == 0.5
    kept = reg.cut_state["cut"]
    assert params.declare_cuts(reg, ["cut"]) == []
    assert reg.cut_state["cut"] is kept
    assert not params.is_cut_id("cut.1.amount") and params.is_cut_id("cut.12.invert")
    assert not params.is_cut_id("view.cut_through")
    groups = params.PERFORMANCE_GROUPS
    assert groups.index("cut") == groups.index("matte") + 1


def test_the_registry_writes_the_view_states_cuts():
    from types import SimpleNamespace

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control

    v = view.ViewState()
    assert v.cuts == {}
    chain = Analyzer(Analyser())
    reg = params.build_registry(v, Control(chain), SimpleNamespace(chain=chain))
    assert reg.cut_state is v.cuts
    params.declare_cuts(reg, ["cut"])
    reg["cut.invert"].set(True)
    assert v.cuts["cut"].invert is True


def test_the_fixture_saves_and_loads_as_seven(tmp_path):
    """`cut-out` (a `/7` wired frame with a matte, a cut and a composite
    and their values), loaded, saved and loaded into a fresh rig, lands the
    same `GraphSpec` and the same cut values, and saves `/7`."""
    from test_presets import boot

    src = json.loads(FIXTURE.read_text())
    assert src["schema"] == "hyperspace.preset/7"
    spec, saved = None, None
    for home in (tmp_path / "a", tmp_path / "b"):
        (home / "presets").mkdir(parents=True, exist_ok=True)
        (home / "presets" / FIXTURE.name).write_text(saved or FIXTURE.read_text())
        r = boot(home)
        r.presets.load("cut-out")
        got = r.presets.graph.spec
        assert got is not None and got.wired and not got.notes
        assert got.cuts == (G.CutAt(1),) and got.mattes == (G.MatteAt(1),)
        assert [n for n in r.presets.notes if n.startswith("graph:")] == []
        assert r.reg["cut.amount"].value == pytest.approx(1.0)
        assert r.reg["cut.invert"].value is False
        assert r.reg["matte.key"].value == pytest.approx(0.95)
        if spec is not None:
            assert got == spec
        spec = got
        saved = r.presets.save_as("cut-out").read_text()
        doc = json.loads(saved)
        assert doc["schema"] == "hyperspace.preset/7"
        assert {"kind": "cut"} in doc["graph"]["nodes"]
        assert doc["values"]["cut.amount"] == pytest.approx(1.0)


def test_a_new_preset_holds_no_cut_values(tmp_path):
    from test_presets import boot

    home = tmp_path / "h"
    (home / "presets").mkdir(parents=True)
    (home / "presets" / FIXTURE.name).write_text(FIXTURE.read_text())
    r = boot(home)
    r.presets.load("cut-out")
    r.presets.new()
    doc = json.loads(r.presets.save_as("fresh").read_text())
    assert not [k for k in doc["values"] if params.is_cut_id(k)]


# ---------------------------------------------------------------- GL
moderngl = pytest.importorskip("moderngl")

SIZE = (64, 48)
COLOUR = (200, 100, 50)
BLUE = (0, 0, 255)
# channel a: the mask's picture (dark left, bright right); b: what is cut;
# c: what lies under
MASKED = [("channel.a", "matte.image"), ("matte", "cut.mask"), ("channel.b", "cut.image")]


def _halves(left, right, w=64, h=48) -> np.ndarray:
    return _rgba(w, h, left, right=right)


def _sources(**over):
    got = {"a": Still(_halves((20, 20, 20), (230, 230, 230))),
           "b": Still(_rgba(*SIZE, COLOUR)), "c": Still(_rgba(*SIZE, BLUE))}
    got.update(over)
    return _media(**{k: v for k, v in got.items() if v is not None})


def _renderer(ctx, media, pairs, nodes=(CUT, MATTE)):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    spec = G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=list(nodes)),
                        effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    return r


def _s(cut=None, matte=None, resize=None) -> view.ViewState:
    from hyperspace.view import ViewState

    s = ViewState(lines=False, points=False, faces=False,
                  mattes={"matte": matte or MatteState()}, cuts={"cut": cut or CutState()})
    if resize is not None:
        s.resize = {"resize": resize}
    return s


def _draw(ctx, r, s, size=SIZE, n=2):
    vs = [View(Switches(), size, target=_fbo(ctx, *size)) for _ in range(n)]
    r.draw_outputs(s, *size, 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    return _px(vs[1].target)


def _cut_px(r, key="cut#cut") -> np.ndarray:
    """The cut's own picture (its frame target), rows top first."""
    tex = r._frames[key][0]
    w, h = tex.size
    return np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4)[::-1].astype(int)


def _left_right(px):
    h, w = px.shape[:2]
    return px[h // 2, w // 4], px[h // 2, 3 * w // 4]


def test_the_hole_is_transparent_before_any_composite(ctx):
    r = _renderer(ctx, _sources(), [*MASKED, ("cut", "output.2.image")])
    _draw(ctx, r, _s())
    left, right = _left_right(_cut_px(r))
    assert tuple(left) == (0, 0, 0, 0)                   # the mask fails: cut away
    assert tuple(right) == (*COLOUR, 255)                # the mask passes: the picture
    assert r._graph.nodes["cut"].said == "cut by matte"


def test_the_under_shows_through_the_hole(ctx):
    pairs = [*MASKED, ("cut", "composite.over"), ("channel.c", "composite.under"),
             ("composite", "output.2.image")]
    r = _renderer(ctx, _sources(), pairs, (CUT, MATTE, COMPOSITE))
    left, right = _left_right(_draw(ctx, r, _s()))
    assert tuple(left) == (*BLUE, 255)
    assert tuple(right) == (*COLOUR, 255)


def test_amount_a_half_dims_the_cut_part_by_half(ctx):
    r = _renderer(ctx, _sources(), [*MASKED, ("cut", "output.2.image")])
    _draw(ctx, r, _s(cut=CutState(amount=0.5)))
    left, right = _left_right(_cut_px(r))
    want = [c * 0.5 for c in (*COLOUR, 255)]
    assert np.allclose(left, want, atol=1.5), left       # colour and alpha both halved
    assert tuple(right) == (*COLOUR, 255)
    assert r._graph.nodes["cut"].said == "cut by matte · amount 0.50"
    # … and on a composite, half of each
    pairs = [*MASKED, ("cut", "composite.over"), ("channel.c", "composite.under"),
             ("composite", "output.2.image")]
    r = _renderer(ctx, _sources(), pairs, (CUT, MATTE, COMPOSITE))
    left, _ = _left_right(_draw(ctx, r, _s(cut=CutState(amount=0.5))))
    assert np.allclose(left[:3], [100, 50, 25 + 127.5], atol=2), left


def test_invert_keeps_the_hole_and_cuts_the_rest(ctx):
    r = _renderer(ctx, _sources(), [*MASKED, ("cut", "output.2.image")])
    _draw(ctx, r, _s(cut=CutState(invert=True)))
    left, right = _left_right(_cut_px(r))
    assert tuple(left) == (*COLOUR, 255) and tuple(right) == (0, 0, 0, 0)
    assert r._graph.nodes["cut"].said == "cut by matte · inverted"


def test_amount_zero_leaves_the_picture_whole(ctx):
    r = _renderer(ctx, _sources(), [*MASKED, ("cut", "output.2.image")])
    _draw(ctx, r, _s(cut=CutState(amount=0.0)))
    px = _cut_px(r)
    assert (px == np.array([*COLOUR, 255])).all()


def test_no_mask_is_the_picture_untouched(ctx):
    """No mask wired: byte-identical to the picture wired straight — no
    pass, no texture of its own."""
    want = _draw(ctx, _renderer(ctx, _sources(), [("channel.b", "output.2.image")]), _s())
    r = _renderer(ctx, _sources(), [("channel.b", "cut.image"), ("cut", "output.2.image")])
    got = _draw(ctx, r, _s())
    assert (got == want).all()
    assert "cut#cut" not in r._frames
    assert r._graph.nodes["cut"].said == "no mask wired: its picture through, whole"


def test_a_mask_making_nothing_is_the_picture_untouched(ctx):
    """W2: a matte reading nothing (an empty channel) makes nothing, and a
    cut fed by it shows its picture whole."""
    want = _draw(ctx, _renderer(ctx, _sources(a=None), [("channel.b", "output.2.image")]),
                 _s())
    r = _renderer(ctx, _sources(a=None), [*MASKED, ("cut", "output.2.image")])
    got = _draw(ctx, r, _s())
    assert (got == want).all()
    assert "cut#cut" not in r._frames
    assert r._graph.nodes["cut"].said == "matte makes nothing: its picture through, whole"


def test_the_mask_of_an_asymmetric_picture_lands_on_the_right_rows(ctx):
    """The orientation risk (spec "Risks"): a mask from a still bright in
    its top-left quarter only (rows top first, as media is) keeps the
    picture top-left only."""
    px = _rgba(64, 48, (20, 20, 20))
    px[:24, :32, :3] = 230
    r = _renderer(ctx, _sources(a=Still(px)), [*MASKED, ("cut", "output.2.image")])
    _draw(ctx, r, _s())
    out = _cut_px(r)
    for (y, x), alpha in (((10, 10), 255), ((10, 50), 0), ((38, 10), 0), ((38, 50), 0)):
        assert out[y, x, 3] == alpha, (y, x, out[y, x])


def test_the_flip_reads_a_rows_top_first_mask_the_right_way_up(ctx):
    """A mask uploaded from a CPU array as it is (rows top first: T4's
    segment) passing its top half: flipped, the picture's top half stays;
    unflipped (read as a GL pass's mask), the bottom."""
    from hyperspace.render import Renderer

    passes = Renderer(ctx).mask_passes()
    src = ctx.texture((8, 8), 4, data=bytes([255, 255, 255, 255] * 64))
    m = np.zeros((8, 8), np.uint8)
    m[:4] = 255                                          # the top rows, as the array has them
    mask = ctx.texture((8, 8), 1, data=m.tobytes())
    for flip, top in ((True, 255), (False, 0)):
        out = ctx.texture((8, 8), 4)
        fbo = ctx.framebuffer(color_attachments=[out])
        fbo.viewport = (0, 0, 8, 8)
        passes.cut(src, mask, fbo, flip=flip)
        alpha = np.frombuffer(out.read(), np.uint8).reshape(8, 8, 4)[::-1, :, 3]
        assert (alpha[:4] == top).all() and (alpha[4:] == 255 - top).all(), (flip, alpha)


def test_a_cut_of_an_own_sized_picture_is_made_at_its_size(ctx):
    """Its own size is its picture's: a resize's 64×36 picture is cut at
    64×36 (the mask fitted into it by cover), then laid into the 160×90
    window by cover — the right half kept, the left half cut away."""
    pairs = [("channel.b", "resize.image"), ("resize", "cut.image"),
             ("channel.a", "matte.image"), ("matte", "cut.mask"),
             ("cut", "composite.over"), ("channel.c", "composite.under"),
             ("composite", "output.2.image")]
    size = (160, 90)
    media = _sources(a=Still(_halves((20, 20, 20), (230, 230, 230), *size)),
                     b=Still(_rgba(*size, COLOUR)), c=Still(_rgba(*size, BLUE)))
    r = _renderer(ctx, media, pairs, (CUT, MATTE, COMPOSITE, RESIZE))
    out = _draw(ctx, r, _s(resize=ResizeState(size=2)), size=size)
    keys = [k for k in r._frames if isinstance(k, tuple) and k[0] == "cut#cut"]
    assert keys and r._frames[keys[0]][0].size == (64, 36), keys
    left, right = _left_right(out)
    assert tuple(left[:3]) == BLUE
    assert np.allclose(right[:3], COLOUR, atol=2), right
