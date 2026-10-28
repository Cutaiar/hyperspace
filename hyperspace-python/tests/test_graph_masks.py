# ruff: noqa: F811 — `ctx` is test_graph_faces' fixture, taken as each GL test's argument
"""Plan 39 T2 — the mask wire (W1) and `matte` (W2).

A mask is a pattern — a pixel passes or it does not — on its own `mask`
wire, a one-channel 8-bit texture at its maker's size; never a picture's
alpha. Wired where a picture is taken it reads as one (white where it
passes, black elsewhere, at the consumer's size, fitted by cover:
`MaskPicture`); a picture into a mask port is refused with the converter's
name. `matte[.n]` makes one from a picture: by its brightness, its coverage
or a keyed hue, at `key`, `soft` about it, `invert`, `feather`.

What it must keep honest: no node of plan 36 or earlier changes
(`scene.cover → lookback.cover` as it was, every factory preset's
`graph.signature` — `test_graph_frame.py` — unmoved); the matte's three
sources, its knobs, its one channel; the promotion at the consumer's size
and the right way up; an unwired matte makes nothing; `masks.py` is a
leaf. The GL tests use test_graph_faces' harness and skip without a
standalone context."""

from __future__ import annotations

import ast
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
from hyperspace import masks, media_tex, params, view
from hyperspace.outputs import Switches, View
from hyperspace.view import MatteState, ResizeState

MATTE = {"kind": "matte"}
MATTE2 = {"kind": "matte", "instance": 2}
RESIZE = {"kind": "resize"}
ACID2 = {"kind": "effect", "file": "acid", "instance": 2}
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
FIXTURE = Path(__file__).parent / "fixtures" / "presets" / "mask-as-picture.json"


def _read(*pairs, nodes=(MATTE,)):
    return G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=list(nodes)))


def _spec(*pairs, nodes=(MATTE,)):
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


# ---------------------------------------------------------------- the boundary

def test_masks_is_a_leaf():
    """`masks.py` imports moderngl, numpy and `glsl` only (and the standard
    library's typing): graph.py reaches it through the renderer, never by
    import."""
    tree = ast.parse(Path(masks.__file__).read_text())
    got = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            got.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            got |= {a.name for a in node.names}
    assert got <= {"__future__", "collections.abc", "moderngl", "numpy", ".glsl"}, got
    graph_imports = {(n.module or "") for n in ast.walk(ast.parse(Path(G.__file__).read_text()))
                     if isinstance(n, ast.ImportFrom)}
    assert "masks" not in graph_imports


def test_the_cover_scale_is_the_media_cover():
    for src, dst in (((64, 36), (160, 90)), ((256, 144), (64, 64)), ((10, 30), (30, 10))):
        assert masks.cover_scale(src, dst) == pytest.approx(
            media_tex.fit_scale(media_tex.COVER, src, dst))


def test_the_matte_node_says_what_it_is():
    assert G.MatteNode.KIND == "matte" and G.MatteNode.INPUTS == {"image": G.IMAGE}
    assert G.MatteNode.OUTPUT == G.MASK and G.MatteNode.TIMED
    assert G.MaskPicture.INPUTS == {"mask": G.MASK} and G.MaskPicture.OUTPUT == G.IMAGE
    assert G.WIRED_MAKES["matte"] == G.MASK and G.WIRED_TAKES["matte"] == {"image": G.IMAGE}
    assert "matte" in G.DECLARED and "matte" in G.RESERVED
    assert G.wire_node_kind("matte.2", wired=True) == "matte"
    assert G.wire_node_kind("matte.1", wired=True) is None


# ---------------------------------------------------------------- the entry

def test_a_matte_entry_round_trips():
    for e in (MATTE, MATTE2):
        spec = G.read_graph(wired(("channel.a", f"{G.MatteAt(e.get('instance', 1)).name}.image"),
                                  nodes=[e]))
        assert spec.mattes == (G.MatteAt(e.get("instance", 1)),)
        assert G.read_graph(spec.to_json()).to_json() == spec.to_json()
        assert e in spec.to_json()["nodes"]
    with pytest.raises(G.GraphError):
        G.read_graph(wired(nodes=[{"kind": "matte", "instance": 0}]))
    with pytest.raises(G.GraphError):
        G.read_graph(wired(nodes=[{"kind": "matte", "key": 0.5}]))


def test_a_matte_must_be_declared():
    spec = _read(("channel.a", "matte.image"), ("matte", "output.2.image"), nodes=())
    assert spec.notes and all('add one: {"kind": "matte"}' in n for n in spec.notes), spec.notes


# ---------------------------------------------------------------- the type rule (W1)

@pytest.mark.parametrize("dst", ["output.2.image", "output.3.hands", "acid.2.image",
                                 "acid.2.aux", "composite.over", "switch.in1", "shape.faces",
                                 "delay.image", "resize.image", "lookback.occluder"])
def test_a_mask_goes_where_a_picture_is_taken(dst):
    nodes = [MATTE, ACID2, {"kind": "composite"}, {"kind": "switch"}, {"kind": "delay"}, RESIZE]
    spec = G.read_graph(wired(("channel.a", "matte.image"), ("matte", dst), *FACTORY_FRAME,
                              nodes=nodes))
    assert not spec.notes, spec.notes


def test_a_picture_into_a_mask_port_names_the_matte():
    spec = _read(("channel.a", "lookback.cover"), ("lookback", "output.2.image"),
                 ("scene", "lookback.image"), nodes=())
    assert spec.notes == (("wire channel.a → lookback.cover — channel.a makes a picture, "
                           "lookback.cover takes a mask — put a matte between"),)
    # through a matte it stands
    _spec(("channel.a", "matte.image"), ("matte", "lookback.cover"),
          ("lookback", "output.2.image"), ("scene", "lookback.image"))


def test_a_mask_is_still_no_geometry_and_no_depth():
    spec = _read(("channel.a", "matte.image"), ("matte", "scene.geometry"))
    assert spec.notes == (("wire matte → scene.geometry — matte makes a mask, "
                           "scene.geometry takes geometry"),)
    spec = _read(("channel.a", "matte.image"), ("matte", "output.2.depth"),
                 ("channel.a", "output.2.image"))
    assert spec.notes and "scene.depth" in spec.notes[0], spec.notes


def test_the_scene_cover_is_as_it_was():
    """No node of plan 36 changes: the cover goes into `lookback.cover`
    straight, no promotion between; elsewhere it is still refused in the
    pin's words."""
    spec = _spec(("scene.cover", "lookback.cover"), ("scene", "lookback.image"),
                 ("lookback", "output.2.image"), nodes=())
    g = G.build_graph(_views(), spec.wiring())
    cover = g.nodes["lookback(cover)"]
    assert isinstance(cover, G.Cover) and g.nodes["lookback"].inputs["cover"] is cover
    assert not [n for n in g.nodes.values() if isinstance(n, G.MaskPicture)]
    spec = _read(("scene.cover", "output.2.image"), nodes=())
    assert spec.notes == ("wire scene.cover → output.2.image — scene.cover is "
                          + G.PIN_WORDS["scene.cover"],)


# ---------------------------------------------------------------- the build

def test_a_matte_is_built_only_when_reached_and_fed():
    spec = _spec(("channel.a", "matte.image"))
    assert "matte" not in G.reaches(spec)
    g = G.build_graph(_views(), spec.wiring())
    assert not [n for n in g.nodes.values() if isinstance(n, G.MatteNode)]
    g = G.build_graph(_views(), _spec(("matte", "output.2.image")).wiring())
    assert not [n for n in g.nodes.values() if isinstance(n, (G.MatteNode, G.MaskPicture))]
    assert g.dormant["matte"] == "matte is fed by nothing here: wire its input"


def test_a_mask_into_picture_ports_is_read_through_one_picture():
    spec = _spec(("channel.a", "matte.image"), ("matte", "output.2.image"),
                 ("matte", "acid.2.image"), ("acid.2", "output.3.image"),
                 ("matte", "lookback.cover"), ("scene", "lookback.image"),
                 ("lookback", "output.1.image"), nodes=[MATTE, ACID2])
    g = G.build_graph(_views(3), spec.wiring(), (), ("acid.2",))
    matte = g.nodes["matte"]
    assert isinstance(matte, G.MatteNode) and matte.inputs["image"] is g.nodes["channel.a"]
    pic = g.nodes["matte(picture)"]
    assert isinstance(pic, G.MaskPicture) and pic.inputs["mask"] is matte
    assert _chain(g.outputs[1].inputs["image"]) is pic
    (acid,) = [n for n in g.nodes.values() if isinstance(n, G.Effect)]
    assert acid.inputs["image"] is pic
    # a mask port takes the mask as it is
    assert g.nodes["lookback"].inputs["cover"] is matte
    assert len([n for n in g.nodes.values() if isinstance(n, G.MaskPicture)]) == 1
    order = [n.name for n in g.order]
    assert order.index("channel.a") < order.index("matte") < order.index("matte(picture)")
    assert "matte" in g.timed and "matte(picture)" not in g.timed


def test_the_canvas_knows_the_matte():
    from hyperspace import graphview

    assert graphview.LABELS["matte"] == "Matte" and graphview.HOVERS["matte"]
    assert graphview.FRAME_CLASS["matte"] is G.MatteNode
    assert graphview.PICKER_GROUP["matte"] == "masks"
    stand = graphview._stand_in("matte.2")
    assert isinstance(stand, G.MatteNode) and stand.name == "matte.2"
    owner = graphview.OWNERS["matte"]
    assert owner("matte.2.key", None) == "matte.2" and owner("matte.feather", None) == "matte"
    assert graphview._node_name({"kind": "matte", "instance": 3}) == "matte.3"


# ---------------------------------------------------------------- the params

def test_declare_mattes_comes_and_goes():
    reg = params.Registry()
    got = params.declare_mattes(reg, ["matte", "matte.2"])
    ids = params.matte_ids("matte") + params.matte_ids("matte.2")
    assert sorted(got) == sorted(ids) and len(ids) == 14
    for pid in ids:
        assert reg[pid].group == params.MATTE_GROUP == "matte", pid
        assert reg[pid].modulatable, pid
        assert params.is_matte_id(pid), pid
    assert reg["matte.from"].choices == ["luma", "alpha", "chroma"] == list(view.MATTE_FROM)
    st = MatteState()
    assert (st.source, st.key, st.soft, st.invert, st.feather) == (0, 0.5, 0.0, False, 0.0)
    assert reg["matte.key"].value == 0.5 and reg["matte.soft"].hi == 0.5
    assert reg["matte.feather"].hi == 32.0 and reg["matte.2.sat"].value == 1.0
    assert reg["matte.invert"].value is False
    gone = params.declare_mattes(reg, ["matte"])
    assert sorted(gone) == sorted(params.matte_ids("matte.2"))
    assert "matte.2" not in reg.matte_state
    reg["matte.from"].set(2)
    assert reg.matte_state["matte"].source == 2
    kept = reg.matte_state["matte"]
    assert params.declare_mattes(reg, ["matte"]) == []
    assert reg.matte_state["matte"] is kept
    assert not params.is_matte_id("matte.1.key") and params.is_matte_id("matte.12.hue")
    groups = params.PERFORMANCE_GROUPS
    assert groups.index("matte") == groups.index("resize") + 1


def test_the_registry_writes_the_view_states_mattes():
    from types import SimpleNamespace

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control

    v = view.ViewState()
    assert v.mattes == {}
    chain = Analyzer(Analyser())
    reg = params.build_registry(v, Control(chain), SimpleNamespace(chain=chain))
    assert reg.matte_state is v.mattes
    params.declare_mattes(reg, ["matte"])
    reg["matte.feather"].set(8.0)
    assert v.mattes["matte"].feather == 8.0


def test_the_fixture_saves_and_loads_as_seven(tmp_path):
    """`mask-as-picture` (a `/7` wired frame with a matte entry and its
    values), loaded, saved and loaded into a fresh rig, lands the same
    `GraphSpec` and the same matte values, and saves `/7`."""
    from test_presets import boot

    src = json.loads(FIXTURE.read_text())
    assert src["schema"] == "hyperspace.preset/7"
    spec, saved = None, None
    for home in (tmp_path / "a", tmp_path / "b"):
        (home / "presets").mkdir(parents=True, exist_ok=True)
        (home / "presets" / FIXTURE.name).write_text(saved or FIXTURE.read_text())
        r = boot(home)
        r.presets.load("mask-as-picture")
        got = r.presets.graph.spec
        assert got is not None and got.wired and not got.notes
        assert got.mattes == (G.MatteAt(1),)
        assert [n for n in r.presets.notes if n.startswith("graph:")] == []
        assert r.reg["matte.key"].value == pytest.approx(0.95)
        assert r.reg["matte.feather"].value == pytest.approx(4.0)
        if spec is not None:
            assert got == spec
        spec = got
        saved = r.presets.save_as("mask-as-picture").read_text()
        doc = json.loads(saved)
        assert doc["schema"] == "hyperspace.preset/7"
        assert {"kind": "matte"} in doc["graph"]["nodes"]
        assert doc["values"]["matte.key"] == pytest.approx(0.95)


# ---------------------------------------------------------------- GL
moderngl = pytest.importorskip("moderngl")

SIZE = (64, 48)
OUT = [("channel.a", "matte.image"), ("matte", "output.2.image")]


def _renderer(ctx, media=None, pairs=OUT, nodes=(MATTE,)):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    spec = G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=list(nodes)),
                        effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    return r


def _s(**kw) -> view.ViewState:
    from hyperspace.view import ViewState

    resize = kw.pop("resize", None)
    s = ViewState(lines=False, points=False, faces=False, mattes={"matte": MatteState(**kw)})
    if resize is not None:
        s.resize = {"resize": resize}
    return s


def _draw(ctx, r, s, size=SIZE, n=2):
    vs = [View(Switches(), size, target=_fbo(ctx, *size)) for _ in range(n)]
    r.draw_outputs(s, *size, 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    return _px(vs[1].target)


def _mask(r, name="matte"):
    keys = [k for k in r._frames if isinstance(k, tuple) and k[0] == f"{name}#mask"]
    assert len(keys) == 1, keys
    return r._frames[keys[0]][0]


def _mask_px(tex) -> np.ndarray:
    w, h = tex.size
    return np.frombuffer(tex.read(), np.uint8).reshape(h, w)[::-1].astype(int)


def _halves(left, right, w=64, h=48, alpha=(255, 255)) -> np.ndarray:
    px = _rgba(w, h, left, right=right)
    px[:, : w // 2, 3] = alpha[0]
    px[:, w // 2:, 3] = alpha[1]
    return px


def _passes(out) -> tuple[bool, bool]:
    """(the left half white, the right half white) — each else black."""
    h, w = out.shape[:2]
    lo, ro = out[h // 2, w // 4, :3], out[h // 2, 3 * w // 4, :3]
    for px in (lo, ro):
        assert tuple(px) in (WHITE, BLACK), px
    return tuple(lo) == WHITE, tuple(ro) == WHITE


def test_luma_passes_the_bright_half(ctx):
    r = _renderer(ctx, _media(a=Still(_halves((20, 20, 20), (230, 230, 230)))))
    assert _passes(_draw(ctx, r, _s())) == (False, True)
    assert r._graph.nodes["matte"].said == "64×48 mask · luma at 0.50"


def test_alpha_passes_the_opaque_half(ctx):
    # (a bright picture whose left half is see-through: luma would pass both)
    px = _halves(WHITE, WHITE, alpha=(0, 255))
    r = _renderer(ctx, _media(a=Still(px)))
    assert _passes(_draw(ctx, r, _s(source=1))) == (False, True)
    r = _renderer(ctx, _media(a=Still(_halves(WHITE, WHITE, alpha=(255, 0)))))
    assert _passes(_draw(ctx, r, _s(source=1))) == (True, False)


def test_chroma_passes_the_keyed_hue(ctx):
    media = _media(a=Still(_halves((0, 200, 0), (200, 0, 0))))
    r = _renderer(ctx, media)
    assert _passes(_draw(ctx, r, _s(source=2, hue=1 / 3))) == (True, False)
    r = _renderer(ctx, media)
    assert _passes(_draw(ctx, r, _s(source=2, hue=0.0))) == (False, True)
    # a grey keys nothing at full saturation
    r = _renderer(ctx, _media(a=Still(_halves((128, 128, 128), (128, 128, 128)))))
    assert _passes(_draw(ctx, r, _s(source=2, hue=0.0))) == (False, False)


def _ramp(w=64, h=48) -> np.ndarray:
    """Black at the left to white at the right."""
    px = _rgba(w, h, BLACK)
    px[..., :3] = np.linspace(0, 255, w).round().astype(np.uint8)[None, :, None]
    return px


def test_the_key_moves_where_a_pixel_passes(ctx):
    media = _media(a=Still(_ramp()))
    got = {}
    for key in (0.25, 0.75):
        r = _renderer(ctx, media)
        _draw(ctx, r, _s(key=key))
        m = _mask_px(_mask(r))
        assert set(np.unique(m)) <= {0, 255}
        got[key] = (m[24] == 255).mean()
    assert got[0.25] == pytest.approx(0.75, abs=0.05)
    assert got[0.75] == pytest.approx(0.25, abs=0.05)


def test_soft_widens_the_edge_and_invert_flips(ctx):
    media = _media(a=Still(_ramp()))
    r = _renderer(ctx, media)
    _draw(ctx, r, _s(soft=0.2))
    row = _mask_px(_mask(r))[24]
    between = ((row > 0) & (row < 255)).sum()
    assert between >= 20, row             # ±0.2 of a 64-px ramp: about 26 px
    assert row[0] == 0 and row[-1] == 255 and (np.diff(row) >= 0).all()
    r = _renderer(ctx, media)
    _draw(ctx, r, _s(soft=0.2, invert=True))
    assert (_mask_px(_mask(r))[24] == 255 - row).all()
    r = _renderer(ctx, _media(a=Still(_halves((20, 20, 20), (230, 230, 230)))))
    assert _passes(_draw(ctx, r, _s(invert=True))) == (True, False)


def test_the_feather_widens_the_edge_in_one_channel(ctx):
    media = _media(a=Still(_halves((20, 20, 20), (230, 230, 230))))
    rows = {}
    for feather in (0.0, 8.0):
        r = _renderer(ctx, media)
        _draw(ctx, r, _s(feather=feather))
        tex = _mask(r)
        assert tex.components == 1 and tex.dtype == "f1" and tex.size == SIZE
        rows[feather] = _mask_px(tex)[24]
    hard, soft = rows[0.0], rows[8.0]
    assert ((hard > 0) & (hard < 255)).sum() == 0
    assert ((soft > 0) & (soft < 255)).sum() >= 8
    assert (soft > 0).sum() > (hard > 0).sum()       # the passing side reaches further
    assert soft[0] == 0 and soft[-1] == 255
    assert r._graph.nodes["matte"].said == "64×48 mask · luma at 0.50 · feather 8 px"
    # the half-way texture is the matte's own too, one channel
    blur = [k for k in r._frames if isinstance(k, tuple) and k[0] == "matte#mask/blur"]
    assert len(blur) == 1 and r._frames[blur[0]][0].components == 1


def test_the_promotion_is_at_the_consumers_size_by_cover(ctx):
    """A matte of a 64×36 resize (its own size) into a 160×90 window and a
    64×64 one: the mask is made once at 64×36, each window shows it fitted
    by cover — white where it passes, opaque black elsewhere."""
    px = _halves((20, 20, 20), (230, 230, 230), w=160, h=90)
    pairs = [("channel.a", "resize.image"), ("resize", "matte.image"),
             ("matte", "output.1.image"), ("matte", "output.2.image")]
    r = _renderer(ctx, _media(a=Still(px)), pairs, (MATTE, RESIZE))
    s = _s(resize=ResizeState(size=2))
    sizes = ((160, 90), (64, 64))
    vs = [View(Switches(), size, target=_fbo(ctx, *size)) for size in sizes]
    r.draw_outputs(s, *sizes[0], 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    assert _mask(r).size == (64, 36)
    wide, square = _px(vs[0].target), _px(vs[1].target)
    assert wide.shape[:2] == (90, 160) and square.shape[:2] == (64, 64)
    assert _passes(wide) == (False, True) and _passes(square) == (False, True)
    assert (wide[..., 3] == 255).all() and (square[..., 3] == 255).all()


def test_the_promote_pass_fits_by_cover(ctx):
    """`PROMOTE_FS` lays a 64×36 mask bright in its right quarter into a
    square by cover (the sides cropped: only the last few columns white),
    into a 16:9 target whole (a quarter white) — opaque, black elsewhere."""
    from hyperspace.render import Renderer

    passes = Renderer(ctx).mask_passes()
    m = np.zeros((36, 64), np.uint8)
    m[:, 48:] = 255
    mask = ctx.texture((64, 36), 1, data=m.tobytes())
    for size, lo, hi in (((64, 64), 1, 5), ((160, 90), 38, 42)):
        out = ctx.texture(size, 4)
        fbo = ctx.framebuffer(color_attachments=[out])
        fbo.viewport = (0, 0, *size)
        passes.promote(mask, fbo)
        got = np.frombuffer(out.read(), np.uint8).reshape(size[1], size[0], 4).astype(int)
        row = got[size[1] // 2]
        assert lo <= (row[:, 0] == 255).sum() <= hi, row[:, 0]
        assert (got[..., 3] == 255).all() and (row[:, 0] == row[:, 1]).all()
        assert row[0, 0] == 0                # (no wrap from the far edge)


def test_an_asymmetric_picture_lands_the_right_way_up(ctx):
    """The orientation risk (spec "Risks"): a still bright in its top-left
    quarter only (rows top first, as media is) — the matte, promoted onto
    the window, is white top-left only."""
    px = _rgba(64, 48, (20, 20, 20))
    px[:24, :32, :3] = 230
    r = _renderer(ctx, _media(a=Still(px)))
    out = _draw(ctx, r, _s())
    for (y, x), want in (((10, 10), WHITE), ((10, 50), BLACK), ((38, 10), BLACK),
                         ((38, 50), BLACK)):
        assert tuple(out[y, x, :3]) == want, (y, x, out[y, x])
    assert _mask_px(_mask(r))[10, 10] == 255 and _mask_px(_mask(r))[38, 10] == 0


def test_a_matte_reading_nothing_makes_nothing(ctx):
    r = _renderer(ctx, _media())
    out = _draw(ctx, r, _s())
    assert r._graph.nodes["matte"].said == "its input reads nothing: no mask"
    assert not [k for k in r._frames if isinstance(k, tuple) and k[0] == "matte#mask"]
    assert (out[..., :3] == 0).all()


def test_a_matte_into_the_look_back_cover_draws(ctx):
    pairs = [("channel.a", "matte.image"), ("matte", "lookback.cover"),
             ("scene", "lookback.image"), ("lookback", "output.2.image")]
    r = _renderer(ctx, _media(a=Still(_halves(BLACK, WHITE))), pairs)
    _draw(ctx, r, _s())
    assert r._graph.nodes["lookback"].inputs["cover"] is r._graph.nodes["matte"]


def test_an_own_sized_mask_lands_on_the_cover_where_its_picture_shows_it(ctx):
    """Review fix (Important 1): `lookback.cover` fetches its mask 1:1 by the
    frame's pixel, so a matte of a 64×36 resize is handed to it refitted by
    cover to the 160×90 frame (`MatteNode.image`, `MaskPasses.fit`): the
    cover the look-back binds equals the promoted picture on output 1, pixel
    for pixel, and the native mask stays 64×36."""
    px = _rgba(160, 90, (20, 20, 20))
    px[:30, 100:, :3] = 230                  # bright in the top right only
    pairs = [("channel.a", "resize.image"), ("resize", "matte.image"),
             ("matte", "lookback.cover"), ("scene", "lookback.image"),
             ("lookback", "output.2.image"), ("matte", "output.1.image")]
    r = _renderer(ctx, _media(a=Still(px)), pairs, (MATTE, RESIZE))
    seen = []
    from hyperspace import lookback as L

    real = L.Lookback.trail

    def spy(self, target, cover=None, *a, **k):
        if cover is not None:
            w, h = cover.size
            seen.append((cover.size, cover.components,
                         np.frombuffer(cover.read(), np.uint8).reshape(h, w)[::-1].astype(int)))
        return real(self, target, cover, *a, **k)

    L.Lookback.trail = spy
    try:
        size = (160, 90)
        vs = [View(Switches(), size, target=_fbo(ctx, *size)) for _ in range(2)]
        r.draw_outputs(_s(resize=ResizeState(size=2)), *size, 1.0, vs, t_now=2.0)
        assert ctx.error == "GL_NO_ERROR"
    finally:
        L.Lookback.trail = real
    assert _mask(r).size == (64, 36)
    assert seen, "the look-back bound no cover"
    got_size, comps, cover = seen[-1]
    assert got_size == size and comps == 1
    shown = _px(vs[0].target)[..., 0]
    assert np.abs(cover - shown).max() <= 1
    assert cover[10, 150] == 255 and cover[80, 10] == 0 and cover[10, 10] == 0


def test_the_cut_pass_cuts(ctx):
    """`CUT_FS` (T3's `cut` is its caller): where the mask passes the
    picture, elsewhere transparent black at amount 1, half at 0.5; invert
    keeps the hole."""
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    passes = r.mask_passes()
    src = ctx.texture((4, 1), 4, data=bytes([200, 100, 50, 255] * 4))
    mask = ctx.texture((4, 1), 1, data=bytes([255, 255, 0, 0]))
    for invert, amount, want in ((False, 1.0, [255, 255, 0, 0]),
                                 (False, 0.5, [255, 255, 128, 128]),
                                 (True, 1.0, [0, 0, 255, 255])):
        out = ctx.texture((4, 1), 4)
        fbo = ctx.framebuffer(color_attachments=[out])
        fbo.viewport = (0, 0, 4, 1)
        passes.cut(src, mask, fbo, invert=invert, amount=amount)
        got = np.frombuffer(out.read(), np.uint8).reshape(4, 4)
        assert np.allclose(got[:, 3], want, atol=1), (invert, amount, got)
        assert np.allclose(got[:, 0], np.array(want) * 200 / 255, atol=2), got


def test_the_cut_pass_fits_its_mask_by_cover(ctx):
    """Review fix: CUT_FS fits the mask into the picture by cover, as the
    promotion does — a 16×4 mask passing its right quarter, over an 8×8
    picture, has that quarter cropped off (all cut); stretched, the last two
    columns would stay."""
    from hyperspace.render import Renderer

    passes = Renderer(ctx).mask_passes()
    src = ctx.texture((8, 8), 4, data=bytes([255, 255, 255, 255] * 64))
    m = np.zeros((4, 16), np.uint8)
    m[:, 12:] = 255
    mask = ctx.texture((16, 4), 1, data=m.tobytes())
    out = ctx.texture((8, 8), 4)
    fbo = ctx.framebuffer(color_attachments=[out])
    fbo.viewport = (0, 0, 8, 8)
    passes.cut(src, mask, fbo)
    alpha = np.frombuffer(out.read(), np.uint8).reshape(8, 8, 4)[..., 3]
    assert (alpha == 0).all(), alpha


def test_a_reload_drops_the_mask_passes(ctx):
    """Review fix (Important 2): `Renderer.on_reload` releases the cached
    `MaskPasses`, so the next ask compiles `masks.py` as it is now."""
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    first = r.mask_passes()
    assert r.mask_passes() is first
    r.on_reload()
    assert "_mask_passes" not in r.__dict__ and first._progs == {}
    assert r.mask_passes() is not first
