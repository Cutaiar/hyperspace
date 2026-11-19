"""Plan 64: one shape interface (shapeframe.py) and a fractal's cells on the
GPU (fractal_gl.py), held against the CPU path they replace or stand beside."""

from __future__ import annotations

import moderngl
import numpy as np
import pytest

from hyperspace import fractal, fractal_gl, geometry, shapeframe
from hyperspace import world as W
from hyperspace.render import Renderer
from hyperspace.view import ViewState

EVERY = pytest.mark.parametrize("name", list(fractal.FRACTALS))
WD, HT = 480, 320


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"no GL context: {e}")
    yield c
    c.release()


def _turned(i: int, **kw) -> ViewState:
    s = ViewState(shape=i, ang=[0.3, 0.1, 0.2, 0.4, 0.5, 0.6], yaw=0.4, pitch=0.2,
                  faces=True, lines=True, points=True)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def _dived(name: str, steps: int = 40, **kw) -> ViewState:
    """A view some levels into fractal `name`, re-rooted on the way."""
    s = ViewState(shape=geometry.shape_index(name), yaw=0.45, pitch=0.3, faces=True,
                  lines=True, points=True)
    s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
    for k, v in kw.items():
        setattr(s, k, v)
    s.zoom = 1.3
    for _ in range(steps):
        s.zoom *= 1.1
        fractal.step(s)
    return s


def _offset():
    return W.Pose.turn3(W.qexp([0.2, -0.4, 0.3]), (0.3, -0.2, 0.5)).model3()


# ---- the provider: a pure refactor for every shape that is not a fractal

def _not_fractals() -> list[int]:
    return [i for i in range(len(geometry.SHAPES)) if fractal.spec_of(i) is None]


@pytest.mark.parametrize("i", _not_fractals())
def test_the_provider_gives_a_fixed_shape_what_draw_scene_made(i):
    """Every field draw_scene used to compute for a fixed shape or a scene,
    byte for byte, from the same calls."""
    s = _turned(i)
    sf = shapeframe.frame(s, WD, HT)
    P, w4, pd = geometry.shape_world(i, s.ang, s.yaw, s.pitch, d4=s.depth4,
                                     flat=s.held, body=s.body)
    g = geometry.geom(i)
    assert sf.g is g
    assert np.array_equal(sf.P, P) and np.array_equal(sf.w4, w4) and np.array_equal(sf.pd, pd)
    assert sf.cue is None and sf.dens_m == g["m"] and sf.zoom_strokes and sf.walk is None
    assert sf.style is g.get("style")
    assert isinstance(shapeframe.provider(i), shapeframe.Scene if g.get("layers")
                      else shapeframe.Fixed)
    tris, uv, ta = sf.faces()
    assert tris is geometry.face_triangles(i) and ta is None
    assert np.array_equal(uv, geometry.face_uvs(i).reshape(-1, 3, 2))
    # with the world's offset: the 3D shapes' cue turned (plan 60), as before
    off = _offset()
    turned = shapeframe.frame(s, WD, HT, off)
    assert np.array_equal(turned.pd, geometry.turned_depth(i, P, pd, off))


@pytest.mark.parametrize("i", [3, 10, next(i for i, x in enumerate(geometry.SHAPES)
                                             if x.family == "Scenes")])
def test_the_line_order_switch_leaves_a_fixed_shape_alone(ctx, i):
    """`view.frac_additive` is a fractal's alone: a fixed shape's frame is
    the same bytes with it on."""
    shots = []
    for add in (False, True):
        shots.append(_draw(ctx, _turned(i, frac_additive=add, instances=3)))
    assert shots[0] == shots[1]


def _draw(ctx, s, world=None) -> bytes:
    r = Renderer(ctx)
    r.world = world
    tex = ctx.texture((WD, HT), 4)
    dep = ctx.depth_texture((WD, HT))
    fbo = ctx.framebuffer(color_attachments=[tex], depth_attachment=dep)
    fbo.use()
    ctx.viewport = (0, 0, WD, HT)
    try:
        r.draw_scene(s, WD, HT, t_now=0.0)
        assert ctx.error == "GL_NO_ERROR"
        out = fbo.read(components=4) + dep.read()
        if s.faces:
            r.scene.ensure((WD, HT), 0)
            r._draw_cover(WD, HT)               # the look-back's cover, too
            assert ctx.error == "GL_NO_ERROR"
        return out
    finally:
        for res in (fbo, tex, dep):
            res.release()


# ---- the GPU path against the CPU path

@EVERY
def test_the_gpu_places_every_corner_where_the_cpu_does(ctx, name):
    """`fractal_gl.FRAC_PLACE` (float32, from the instance rows) against
    `Walk.place` (float64, from the shape's own frame): P, the 4D divisor,
    the depth cue and the fade along w, for every new corner of every cell
    the frame draws, deep in a dive."""
    s = _dived(name, 160)                        # 1.1¹⁶⁰: about 22 halvings in
    spec = fractal.spec_of(s.shape)
    assert len(s.dive.path) >= 6
    wk = fractal.walk(spec, s, WD, HT)
    assert len(wk.line_s), "the dive draws something"
    rows = fractal.instances(wk)["lines"]
    got = fractal_gl.probe(ctx, wk, spec.new_V, rows)
    X = (wk.line_s[:, None, None] * spec.new_V[None] + wk.line_o[:, None, :]).reshape(-1, 4)
    P, div4, pd, along = wk.place(X)
    # the cells span ~256× in size: the tolerance is each cell's own size
    # (through the 4D divide), float32's few parts in a million of it
    reach = np.repeat(wk.line_s * wk.d4 / np.maximum(div4.reshape(len(rows), -1).min(1), 1e-9),
                      len(spec.new_V))
    err = np.linalg.norm(got[:, 0:3] - P, axis=1)
    assert (err <= 2e-5 * reach + 1e-6).all(), (err / reach).max()
    assert np.allclose(got[:, 3], div4, rtol=1e-5, atol=1e-5)
    assert np.allclose(got[:, 4], pd, atol=2e-4)
    assert np.allclose(got[:, 5], along, atol=2e-4)


def test_the_gpu_places_a_cell_where_the_cpu_does_with_an_offset(ctx):
    """The cue reads the world's offset on the GPU as on the CPU."""
    s = _dived("Menger sponge", 30)
    spec = fractal.spec_of(s.shape)
    wk = fractal.walk(spec, s, WD, HT, _offset())
    rows = fractal.instances(wk)["lines"]
    got = fractal_gl.probe(ctx, wk, spec.new_V, rows)
    X = (wk.line_s[:, None, None] * spec.new_V[None] + wk.line_o[:, None, :]).reshape(-1, 4)
    _, _, pd, _ = wk.place(X)
    assert np.allclose(got[:, 4], pd, atol=2e-4)


@pytest.mark.parametrize("name", ["Sierpinski tetrahedron", "Menger sponge", "Sierpinski 5-cell"])
@pytest.mark.parametrize("faces", [False, True])
def test_an_additive_frame_draws_the_cells(ctx, name, faces):
    """The GPU path draws, with no GL error, where the sorted one does: the
    two frames light the same pixels, near enough (the additive one adds
    up; the shapes are the same)."""
    shots = {}
    for add in (False, True):
        s = _dived(name, faces=faces, frac_additive=add)
        img = np.frombuffer(_draw(ctx, s)[: WD * HT * 4], np.uint8).reshape(HT, WD, 4)
        shots[add] = img[..., :3].max(axis=2) > 8
    lit = shots[False].sum()
    assert lit > 500
    both = (shots[False] & shots[True]).sum()
    assert both > 0.85 * lit, (both, lit)


def test_an_additive_frame_draws_every_copy(ctx):
    s = _dived("Sierpinski tetrahedron", 20, frac_additive=True, instances=5, inst_fit=True)
    img = _draw(ctx, s)
    assert np.frombuffer(img[: WD * HT * 4], np.uint8).any()


def test_the_additive_frame_hands_the_copies_cull_a_box_around_the_cells():
    s = _dived("Sierpinski tetrahedron", 30, frac_additive=True)
    sf = shapeframe.frame(s, WD, HT)
    assert sf.walk is not None and sf.g["m"] == 0
    cpu = shapeframe.frame(_dived("Sierpinski tetrahedron", 30), WD, HT)
    lo, hi = sf.P.min(axis=0), sf.P.max(axis=0)
    inside = ((cpu.P >= lo - 1e-9) & (cpu.P <= hi + 1e-9)).all(axis=1)
    assert inside.all()


# ---- the instance rows

def test_the_instance_rows_of_a_known_dive():
    """One level into the tetrahedron at rest: the outline row is the whole
    shape, ×2 about −c₀ (cell 0's centre, scaled back up), in the view; each
    split cell's row is its centre and radius at the zoom."""
    i = geometry.shape_index("Sierpinski tetrahedron")
    s = ViewState(shape=i, zoom=2.0, pan=[0.1, -0.05])
    s.dive.path = [0]
    s.dive.z = 0.2
    spec = fractal.spec_of(i)
    wk = fractal.walk(spec, s, WD, HT)
    assert np.allclose(wk.M, np.eye(4))
    rows = fractal.instances(wk)
    assert set(rows) == {"lines", "outline", "corners", "faces"}
    assert all(r.dtype == np.float32 and r.shape[1] == 6 for r in rows.values())
    p = np.array([0.1, 0.05, 0.2, 0.0])
    c0 = spec.centres[0]
    assert wk.whole and wk.scale == 2.0 and np.allclose(wk.origin, -c0)
    assert np.allclose(rows["outline"], [[*(2.0 * -c0 + p), 4.0, spec.ink]])
    assert np.allclose(rows["corners"], [[*(2.0 * -c0 + p), 4.0, 1.0]])
    L = rows["lines"]
    assert len(L) == len(wk.line_s) > 1
    assert np.allclose(L[:, 0:4], 2.0 * wk.line_o + p, atol=1e-6)
    assert np.allclose(L[:, 4], 2.0 * wk.line_s)
    assert np.allclose(L[:, 5], wk.line_a) and (L[:, 5] >= 0).all() and (L[:, 5] <= 1).all()
    # the first row is the top cell's split, then its children: largest first
    assert L[0, 4] == L[:, 4].max() == 4.0
    assert not len(rows["faces"])           # the faces off
    s.faces = True
    f = fractal.instances(fractal.walk(spec, s, WD, HT))["faces"]
    assert len(f) and f[0, 4] == 4.0


# ---- the cull with the world's offset (plan 59)

def _seen(wk) -> int:
    return len(wk.line_s) + len(wk.face_s)


@EVERY
def test_a_fractal_moved_off_screen_is_culled(name):
    """An offset that carries the shape well off to the side: nothing of it
    is split, where without the offset the frame is full."""
    s = _dived(name, 30, faces=True)
    spec = fractal.spec_of(s.shape)
    assert _seen(fractal.walk(spec, s, WD, HT)) > 1
    away = W.Pose.turn3(W.qexp([0.0, 0.0, 0.0]), (40.0, 0.0, 0.0)).model3()
    wk = fractal.walk(spec, s, WD, HT, away)
    assert not len(wk.line_s) or (wk.line_s == wk.line_s.max()).all()   # the bare top at most


def test_a_turned_fractal_is_culled_where_it_is_drawn():
    """The cull reads the offset: every cell the walk keeps lands, through
    the renderer's own model matrix (home ∘ offset), within reach of the
    screen; and the cells it keeps differ from the unturned frame's."""
    s = _dived("Menger sponge", 35)
    spec = fractal.spec_of(s.shape)
    off = W.Pose.turn3(W.qexp([0.0, 1.2, 0.0]), (0.4, 0.0, 0.0)).model3()
    plain = fractal.walk(spec, s, WD, HT)
    wk = fractal.walk(spec, s, WD, HT, off)
    assert len(wk.line_s) and not np.array_equal(plain.line_o, wk.line_o)
    P, _, _, _ = wk.place(wk.line_o)
    model = geometry.model_matrix(s.zoom, s.pan, off)
    world = P @ model[:3, :3].T + model[:3, 3]
    vp = geometry.eye_matrix(WD, HT, s.eye_fov, s.eye_distance)
    c = np.c_[world, np.ones(len(world))] @ vp.T
    front = c[:, 3] > geometry.EYE_NEAR
    r = s.zoom * wk.line_s * 2.0                   # a generous reach: the cell's own radius
    ndc = np.abs(c[front, :2] / c[front, 3:4])
    reach = 1.0 + 4.0 * r[front][:, None] / c[front, 3:4]
    assert (ndc <= reach).all()


def test_the_cue_reads_the_offset():
    """With an offset the depth cue is each point's distance from the eye
    where the model matrix puts it, not where it would be unmoved."""
    s = _dived("Sierpinski tetrahedron", 25)
    spec = fractal.spec_of(s.shape)
    off = _offset()
    wk = fractal.walk(spec, s, WD, HT, off)
    X = (wk.line_s[:, None, None] * spec.new_V[None] + wk.line_o[:, None, :]).reshape(-1, 4)
    P, _, pd, _ = wk.place(X)
    m = geometry.model_matrix(s.zoom, s.pan, off)
    world = P @ m[:3, :3].T + m[:3, 3]
    rng = np.sqrt(world[:, 0] ** 2 + world[:, 1] ** 2 + (s.eye_distance - world[:, 2]) ** 2)
    want = np.clip(-np.log2(rng / s.eye_distance), -spec.far, wk.top)
    assert np.allclose(pd, want)


def test_draw_scene_hands_the_offset_to_the_fractal(ctx):
    """A grabbed fractal: the renderer passes the world's offset to the walk
    (an offset that carries it off to the side leaves less of it lit)."""
    s = _dived("Sierpinski tetrahedron", 30, faces=False)
    wd = W.World.default()

    def lit() -> int:
        img = np.frombuffer(_draw(ctx, s, wd)[: WD * HT * 4], np.uint8).reshape(HT, WD, 4)
        return int((img[..., :3].max(axis=2) > 8).sum())

    plain = lit()
    wd.objects["shape"].offset = W.Pose.turn3(W.qexp([0.0, 0.0, 0.0]), (6.0, 0.0, 0.0))
    assert lit() < 0.5 * plain
