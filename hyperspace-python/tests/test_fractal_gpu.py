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


# ---- the re-root with the world's offset (row 887): nothing jumps

def _drawn(s, off, x_root) -> np.ndarray:
    """Where points of the shape (its top frame) are drawn: the walk's
    placement, then the renderer's model matrix (home ∘ offset)."""
    spec = fractal.spec_of(s.shape)
    r = spec.ratio
    x = np.array(x_root, dtype=np.float64)
    for k in s.dive.path:
        x = (x - (1.0 - r) * spec.centres[k]) / r
    P, _, _, _ = fractal.walk(spec, s, WD, HT, off).place(x)
    m = geometry.model_matrix(s.zoom, s.pan, off)
    return P @ m[:3, :3].T + m[:3, 3]


OFFSETS = {
    "moved": W.Pose.turn3(W.qexp([0.0, 0.0, 0.0]), (0.3, -0.1, 0.0)),
    "moved in depth": W.Pose.turn3(W.qexp([0.0, 0.0, 0.0]), (0.0, 0.0, 0.4)),
    "turned, moved, scaled": W.Pose.turn3(W.qexp([0.2, 0.5, -0.3]), (0.2, -0.1, 0.3), 1.3),
    # the depth axis edge-on to the screen: a 3D fractal falls back to the rebase
    "turned edge-on": W.Pose.turn3(W.qexp([0.0, 1.5708, 0.0]), (0.1, 0.0, 0.0)),
}


@EVERY
@pytest.mark.parametrize("pose", list(OFFSETS))
def test_a_reroot_of_a_moved_fractal_moves_nothing(name, pose):
    """In and back out, a level at a time: at each re-root every point is
    drawn where it was — the drawn shape does not jump (it did by 0.6 world
    units for an offset of 0.3 before plan 64's fix). A 3D fractal makes up
    for the offset in its pan and depth; a 4D one has its offset rebased
    (`World.rebase`)."""
    wd = W.World.default()
    wd.objects["shape"].offset = OFFSETS[pose]
    s = ViewState(shape=geometry.shape_index(name), yaw=0.4, pitch=0.25)
    s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
    s.pan = [0.05, 0.02]
    rng = np.random.default_rng(3)
    X = np.c_[rng.uniform(-0.4, 0.4, (5, 3)), np.zeros(5)]
    reroots = 0
    for f in [1.15] * 40 + [1 / 1.15] * 40:
        s.zoom *= f
        off = wd.offset_matrix("shape")
        before = _drawn(s, off, X)
        path = list(s.dive.path)
        moved = fractal.step(s, None, off)
        if moved is not None:
            wd.rebase("shape", *moved)
        if s.dive.path == path:
            continue
        reroots += 1
        after = _drawn(s, wd.offset_matrix("shape"), X)
        assert np.allclose(after, before, atol=1e-9 * max(1.0, s.zoom / fractal.Z_IN)), (
            np.abs(after - before).max())
    assert reroots >= 4


def test_the_reroot_dives_into_the_cell_under_the_eye_where_it_is_drawn():
    """With the shape turned by the offset, the cell taken is the one the
    middle of the screen is over as drawn: after a dive the rooted cell
    holds the point drawn at the middle of the screen. (A moved offset is in
    the home's units, × camera.zoom (plan 59): zooming in carries a moved
    shape off the screen, as it does any shape, so it is turned here.)"""
    i = geometry.shape_index("Sierpinski tetrahedron")
    wd = W.World.default()
    wd.objects["shape"].offset = W.Pose.turn3(W.qexp([0.3, 0.9, -0.2]))
    s = ViewState(shape=i, yaw=0.4, pitch=0.25, pan=[0.04, -0.03])
    for _ in range(60):
        s.zoom *= 1.1
        moved = fractal.step(s, None, wd.offset_matrix("shape"))
        if moved is not None:
            wd.rebase("shape", *moved)
    assert len(s.dive.path) >= 4
    off = wd.offset_matrix("shape")
    # the point drawn at the middle, in the rooted cell's own frame
    m = geometry.model_matrix(s.zoom, s.pan, off)
    P = np.linalg.solve(m[:3, :3], -m[:3, 3])
    wf = s.zoom * P + np.array([s.pan[0], -s.pan[1], 0.0])
    q = np.r_[wf, 0.0] - np.array([s.pan[0], -s.pan[1], s.dive.z, s.dive.w])
    x = (q / s.zoom) @ fractal.turn(s).T
    assert np.linalg.norm(x) < fractal.OUTSIDE


def test_rebase_keeps_what_is_drawn():
    """`World.rebase`: home ∘ offset is the same map before and after, the
    turn and scale kept, the body's velocity in the new home's units."""
    wd = W.World.default()
    pose = OFFSETS["turned, moved, scaled"]
    wd.objects["shape"].offset = pose
    b = wd.body("shape")
    b.velocity = np.array([0.4, -0.2, 0.1, 0.0])
    z0, pan0, k = 3.0, (0.2, -0.3), 0.5
    g = np.array([0.15, -0.05, 0.0])
    z1, pan1 = z0 * k, (pan0[0] + g[0] * z0, pan0[1] - g[1] * z0)
    before = geometry.model_matrix(z0, pan0, wd.offset_matrix("shape"))
    wd.rebase("shape", k, g)
    after = geometry.model_matrix(z1, pan1, wd.offset_matrix("shape"))
    # a point of the old frame P and the same point of the new frame (P - g) / k
    P = np.array([[0.3, 0.1, -0.2], [-0.5, 0.4, 0.6]])
    old = P @ before[:3, :3].T + before[:3, 3]
    new = ((P - g) / k) @ after[:3, :3].T + after[:3, 3]
    assert np.allclose(old, new)
    off = wd.objects["shape"].offset
    assert np.allclose(off.ql, pose.ql) and off.scale == pose.scale
    assert np.allclose(b.velocity, np.array([0.4, -0.2, 0.1, 0.0]) / k)


@pytest.mark.parametrize(("name", "rebased"), [("Menger sponge", False),
                                              ("Sierpinski 5-cell", True)])
def test_the_app_hands_the_offset_to_the_reroot(name, rebased):
    """`app._reroot`: the on-air view re-roots with the world's offset. A 3D
    fractal leaves the offset as it is (its pan and depth make up for it); a
    4D one has it rebased; with Fit on the offset is not drawn and the view
    re-roots as with none."""
    from types import SimpleNamespace

    from hyperspace import app

    for fit in (False, True):
        wd = W.World.default()
        wd.objects["shape"].offset = OFFSETS["moved"]
        s = ViewState(shape=geometry.shape_index(name), zoom=4.5, inst_fit=fit)
        s.dive.last = 4.5
        app._reroot(SimpleNamespace(view=s, world=wd), None)
        assert s.dive.path
        moved = not np.allclose(wd.objects["shape"].offset.position, OFFSETS["moved"].position)
        assert moved == (rebased and not fit)


def test_a_turned_fractal_dives_as_an_unturned_one():
    """The zoom still centres on the cell under the eye with the shape
    turned by the offset: the rooted cell stays as near the middle of the
    screen, and at the same depth, as with no offset (a rebase alone kept
    the picture whole at each re-root but let the zoom carry the dive off
    sideways and away: 900 px and 60 units deep after 80 frames)."""
    vp = geometry.eye_matrix(960, 540)

    def dive(pose):
        wd = W.World.default()
        wd.objects["shape"].offset = pose
        s = ViewState(shape=geometry.shape_index("Sierpinski tetrahedron"), yaw=0.4,
                      pitch=0.25, pan=[0.04, -0.03])
        far = 0.0
        for _ in range(80):
            s.zoom *= 1.1
            moved = fractal.step(s, None, wd.offset_matrix("shape"))
            assert moved is None                     # a 3D fractal: the offset stays
            m = geometry.model_matrix(s.zoom, s.pan, wd.offset_matrix("shape"))
            D = m[:3, :3] @ np.array([0.0, 0.0, s.dive.z / s.zoom]) + m[:3, 3]
            c = vp @ np.r_[D, 1.0]
            far = max(far, float(c[3]))
        return len(s.dive.path), far

    plain, turned = dive(W.Pose()), dive(W.Pose.turn3(W.qexp([0.3, 0.9, -0.2])))
    assert turned[0] == plain[0] >= 8
    assert turned[1] < 2.0 * plain[1]


def test_takes_offset_is_the_scene_passs_rule():
    from hyperspace import field

    assert field.takes_offset(ViewState(instances=1))
    assert field.takes_offset(ViewState(instances=7, inst_layout=0))
    assert not field.takes_offset(ViewState(instances=1, inst_fit=True))
    lattice = next(i for i in range(len(field.NAMES)) if field.is_3d(i))
    assert not field.takes_offset(ViewState(instances=7, inst_layout=lattice))
