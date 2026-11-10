"""Plan 59 — world objects: the pose, the registries, the step, the puppets and the render.

The world (`hyperspace/world.py`) holds the things drawn — the shape and the two
hands — each with a home pose and an offset pose; bodies, joints, puppets and
clipping are registries keyed by an object's id. With an identity offset nothing
drawn changes (the golden frames are the proof of the whole; here, a frame with
the app's default world against one with none); a known offset moves the shape by
exactly that much.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pytest
from fake_hands import hand

from hyperspace import app, poi
from hyperspace import geometry as G
from hyperspace import ghost as GH
from hyperspace import world as W
from hyperspace.hands import HandSettings, HandsIO, features, skeleton
from hyperspace.hands import tape as T
from hyperspace.hands.room import palm_axes
from hyperspace.params import MetaRegistry, part_of
from hyperspace.view import ViewState

RNG = np.random.default_rng(59)


def _unit_quat() -> np.ndarray:
    q = RNG.normal(size=4)
    return q / np.linalg.norm(q)


def _pose(general: bool = True) -> W.Pose:
    ql = _unit_quat()
    return W.Pose(RNG.normal(size=4) if general else np.r_[RNG.normal(size=3), 0.0],
                  ql, _unit_quat() if general else ql, float(RNG.uniform(0.3, 3.0)))


def _rot3(q) -> np.ndarray:
    """The textbook 3×3 of unit quaternion (x, y, z, w): an oracle that is not
    `world.py`'s."""
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


# ---------------------------------------------------------------- the pose

def test_a_pair_of_equal_quaternions_is_the_3d_turn_and_keeps_w():
    for _ in range(20):
        q = _unit_quat()
        p = W.Pose.turn3(q)
        pts = RNG.normal(size=(16, 4))
        out = p.turn(pts)
        assert np.allclose(out[:, :3], pts[:, :3] @ _rot3(q).T)
        assert np.allclose(out[:, 3], pts[:, 3])              # w stays where it was
        assert p.is_3d()
    assert not W.Pose(ql=_unit_quat(), qr=_unit_quat()).is_3d()


def test_the_4x4_turn_is_orthonormal_with_determinant_one():
    for _ in range(20):
        r = _pose().rotation4()
        assert np.allclose(r @ r.T, np.eye(4))
        assert np.linalg.det(r) == pytest.approx(1.0)


def test_the_matrix_and_ql_v_qr_bar_agree_on_random_points():
    for _ in range(20):
        p = _pose()
        for v in RNG.normal(size=(8, 4)):
            direct = W.qmul(W.qmul(p.ql, v), W.qconj(p.qr))
            assert np.allclose(p.rotation4() @ v, direct)
            assert np.allclose(p.apply(v), p.position + p.scale * direct)


def test_compose_and_inverse_round_trip():
    for _ in range(20):
        a, b = _pose(), _pose()
        pts = RNG.normal(size=(8, 4))
        assert np.allclose(a.compose(b).apply(pts), a.apply(b.apply(pts)))
        ident = a.compose(a.inverse())
        assert np.allclose(ident.apply(pts), pts)
        assert np.allclose(a.inverse().apply(a.apply(pts)), pts)


def test_log_and_exp_round_trip():
    for _ in range(20):
        a = _pose()
        b = W.Pose.exp(a.log())
        pts = RNG.normal(size=(8, 4))
        assert np.allclose(b.apply(pts), a.apply(pts))
    assert np.allclose(W.Pose().log(), 0.0)
    assert W.Pose.exp(np.zeros(11)).is_identity()


def test_slerp_runs_from_one_pose_to_the_other_the_short_way():
    for _ in range(20):
        a, b = _pose(), _pose()
        pts = RNG.normal(size=(8, 4))
        assert np.allclose(a.slerp(b, 0.0).apply(pts), a.apply(pts))
        assert np.allclose(a.slerp(b, 1.0).apply(pts), b.apply(pts))
    # halfway between none and a quarter turn about z is an eighth turn
    q = W.qexp([0.0, 0.0, math.pi / 2])
    half = W.Pose().slerp(W.Pose.turn3(q), 0.5)
    assert np.allclose(half.ql, W.qexp([0.0, 0.0, math.pi / 4]))
    # (q, q) and (−q, −q) are one turn: the way there is still the short one
    flipped = W.Pose(ql=-q, qr=-q)
    assert np.allclose(W.Pose().slerp(flipped, 0.5).turn([1.0, 0, 0, 0]),
                       half.turn([1.0, 0, 0, 0]))


def test_renormalize_makes_both_quaternions_unit_again():
    p = W.Pose(ql=_unit_quat() * 1.01, qr=_unit_quat() * 0.98).renormalized()
    assert np.linalg.norm(p.ql) == pytest.approx(1.0)
    assert np.linalg.norm(p.qr) == pytest.approx(1.0)


def test_the_3d_model_matrix_is_the_pose_on_x_y_z():
    for _ in range(10):
        p = _pose(general=False)
        pts = RNG.normal(size=(8, 3))
        hom = np.c_[pts, np.ones(8)] @ p.model3().T
        assert np.allclose(hom[:, :3], p.apply(pts)[:, :3])


def test_a_rotation_matrix_and_its_quaternion_agree():
    for _ in range(20):
        q = _unit_quat()
        back = W.quat_of(_rot3(q))
        assert np.allclose(back, q) or np.allclose(back, -q)


# ---------------------------------------------------------------- the module

def test_the_world_imports_nothing_from_the_package():
    tree = ast.parse(Path(W.__file__).read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            assert n.level == 0 and not (n.module or "").startswith("hyperspace"), n.module
        elif isinstance(n, ast.Import):
            assert not any(a.name.startswith("hyperspace") for a in n.names)


def test_the_step_is_the_pois():
    assert (W.STEP_S, W.MAX_STEPS) == (poi.STEP_S, poi.MAX_STEPS)


# ---------------------------------------------------------------- the registries

def test_the_default_world_is_the_shape_and_two_puppeted_hands_with_no_bodies():
    w = W.World.default()
    assert list(w.objects) == ["shape", "hand.left", "hand.right"]
    assert [w[o].kind for o in w.objects] == ["shape", "hand", "hand"]
    assert {o: p.side for o, p in w.puppets.items()} == {"hand.left": "left",
                                                         "hand.right": "right"}
    assert w.bodies == w.joints == w.clip == {}
    assert all(o.offset.is_identity() for o in w.objects.values())


def test_a_registry_takes_only_a_registered_object():
    w = W.World.default()
    with pytest.raises(KeyError):
        w.body("poi")
    with pytest.raises(KeyError):
        w.puppet("poi", W.Palm("left"))
    with pytest.raises(ValueError):
        w.add("shape", "shape")
    with pytest.raises(ValueError):
        w.add("poi", "string")


def test_no_body_means_not_moved_and_removing_an_object_clears_every_registry():
    w = W.World.default()
    w.body("shape", W.Body(velocity=np.array([1.0, 0, 0, 0])))
    w.joints["hand.left"] = object()               # plan 60's, by hand here
    w.clip["hand.left"] = object()
    w.step(0.1)
    assert w["shape"].offset.position[0] > 0.09     # the body moved its offset
    assert w["hand.left"].offset.is_identity()      # no body: never moved
    # out of bodies: still drawn, and still
    w.bodies.pop("shape")
    was = w["shape"].offset.position.copy()
    w.step(0.1)
    assert "shape" in w and np.array_equal(w["shape"].offset.position, was)
    # out of the world: out of every registry
    w.remove("hand.left")
    assert "hand.left" not in w
    assert all("hand.left" not in r for r in w.registries())


def test_reset_puts_every_offset_back_to_the_identity_and_stills_every_body():
    w = W.World.default()
    w.body("shape").spin3([0.0, 2.0, 0.0])
    w.step(0.05)
    assert not w["shape"].offset.is_identity()
    w.reset()
    assert w["shape"].offset.is_identity() and w.offset_matrix("shape") is None
    assert not w.bodies["shape"].spin_l.any()


def test_world_reset_is_a_shared_meta_trigger():
    w = W.World.default()
    w.body("shape", W.Body(velocity=np.array([0.0, 1.0, 0, 0])))
    w.step(0.02)
    meta = MetaRegistry()
    W.register(meta, w)
    W.register(meta, w)                            # declared once
    p = meta["world.reset"]
    assert p.group == "world" and part_of(p) == "shared_meta"
    p.fire()
    assert w["shape"].offset.is_identity()


def test_the_pose_drawn_is_home_then_offset():
    w = W.World.default()
    w.home("shape", W.shape_home(2.0, (0.5, 0.25)))
    q = W.qexp([0.0, 0.0, 0.3])
    w["shape"].offset = W.Pose.turn3(q, (0.1, 0.0, 0.0))
    pts = RNG.normal(size=(6, 3))
    want = (np.c_[pts, np.ones(6)] @ (G.model_matrix(2.0, (0.5, 0.25))
                                      @ w["shape"].offset.model3()).T)[:, :3]
    assert np.allclose(w.pose("shape").apply(pts)[:, :3], want)


# ---------------------------------------------------------------- the step

@pytest.mark.parametrize("fps", [30, 60, 144])
def test_a_free_body_under_drag_decays_at_the_closed_form_rate(fps):
    c, v0, seconds = 1.7, 2.0, 1.0
    w = W.World.default()
    b = w.body("shape", W.Body(velocity=np.array([v0, 0, 0, 0]), drag=c, angular_drag=c))
    b.spin3([0.0, 0.0, v0])
    for _ in range(round(seconds * fps)):
        w.step(1.0 / fps)
    t = seconds - w.left                     # the time stepped (to within one step)
    assert b.velocity[0] == pytest.approx(v0 * math.exp(-c * t), rel=1e-9)
    assert b.spin_l[2] == pytest.approx(v0 * math.exp(-c * t), rel=1e-9)
    x = w["shape"].offset.position[0]
    assert x == pytest.approx(v0 * (1.0 - math.exp(-c * t)) / c, rel=2e-3)
    # the turn: the same decay's integral, as an angle about z
    ang = W.qlog(w["shape"].offset.ql)[2]
    assert ang == pytest.approx(x, rel=1e-6)
    assert w["shape"].offset.is_3d()


def test_the_same_second_at_any_frame_rate_lands_in_the_same_place():
    out = []
    for fps in (30, 60, 144):
        w = W.World.default()
        w.body("shape", W.Body(velocity=np.array([1.0, -0.5, 0.25, 0]), drag=0.8))
        for _ in range(fps):
            w.step(1.0 / fps)
        out.append(w["shape"].offset.position.copy())
    assert np.allclose(out[0], out[1], atol=1e-3) and np.allclose(out[1], out[2], atol=1e-3)


def test_a_stall_drops_the_rest():
    w = W.World.default()
    w.body("shape", W.Body(velocity=np.array([1.0, 0, 0, 0])))
    assert w.step(5.0) == W.MAX_STEPS
    assert w["shape"].offset.position[0] == pytest.approx(W.MAX_STEPS * W.STEP_S)
    assert w.left < W.STEP_S


def test_a_turning_body_keeps_unit_quaternions():
    w = W.World.default()
    w.body("shape").spin3([3.0, -2.0, 5.0])
    for _ in range(600):
        w.step(1 / 60)
    off = w["shape"].offset
    assert np.linalg.norm(off.ql) == pytest.approx(1.0, abs=1e-12)
    assert np.allclose(off.ql, off.qr)


# ---------------------------------------------------------------- the puppets

def _frame(t: float, sides: dict) -> dict:
    return {"t": t, "hands": {
        side: {"features": features(h), "confidence": 1.0, "skeleton": skeleton(h)}
        for side, h in sides.items()}}


def _tape() -> dict:
    """Both hands moving and turning for six frames, then the left gone."""
    frames = []
    for k in range(9):
        sides = {"right": hand("right", "open", (60.0 + 4 * k, 210.0, 10.0 - k), roll=6.0 * k)}
        if k < 6:
            sides["left"] = hand("left", "fist", (-70.0, 190.0 + 3 * k, 0.0), roll=-5.0 * k)
        frames.append(_frame(k / 90, sides))
    return {"schema": T.TAPE_SCHEMA, "mode": "desktop", "frames": frames}


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.mark.parametrize("mirror", [False, True])
def test_a_tape_puts_each_hand_object_where_the_ghost_puts_its_palm(mirror):
    clock = Clock()
    io = HandsIO(HandSettings.from_config({}), {"out": ""},
                 source=T.TapeSource(_tape(), clock), clock=clock)
    gh = GH.Ghost(ctx=None, state=GH.GhostState(on=True, mirror=mirror))
    gh.source = io
    w = W.World.default()
    seen = 0
    for k in range(9):
        clock.t = k / 90 + 1e-4
        io.poll(1 / 90)
        w.frame(1 / 90, app.palms_in_world(gh))
        m = GH.basis("desktop", mirror)
        cal = gh.calibrated(GH.box_of(io), m, io.units)
        undo = np.eye(4)
        undo[:3, :3] = m.T
        stage_to_world = cal @ undo                     # what the ghost draws through
        turn = cal[:3, :3] / np.linalg.norm(cal[:3, 0])
        for side, oid in W.HANDS.items():
            obj = w[oid]
            sk = io.skeleton.get(side)
            if sk is None:
                assert not obj.present
                continue
            seen += 1
            p = GH.pose(side, sk, m)                    # the ghost hand's palm, in the stage
            want = (stage_to_world @ np.r_[p.palm, 1.0])[:3]
            assert obj.present
            assert np.allclose(obj.pose.position[:3], want) and obj.pose.position[3] == 0.0
            axes = np.array(palm_axes(sk["normal"], sk["direction"], turn))
            got = obj.pose.turn(np.c_[np.eye(3), np.zeros(3)])[:, :3]   # its x, y, z
            assert np.allclose(got, axes, atol=1e-9)
            assert obj.pose.is_3d()
    assert seen == 9 + 6


def test_a_lost_hand_stays_registered_where_it_was_and_writes_nothing():
    w = W.World.default()
    rot = np.eye(3)
    w.frame(1 / 60, {"left": ((0.1, 0.2, 0.3), rot)})
    w.frame(1 / 60, {"left": ((0.4, 0.2, 0.3), rot)})
    left = w["hand.left"]
    assert left.present and w.puppets["hand.left"].velocity[0] == pytest.approx(0.3 * 60)
    assert not w["hand.right"].present
    w.frame(1 / 60, {})
    assert "hand.left" in w and not left.present
    assert np.allclose(left.home.position[:3], (0.4, 0.2, 0.3))   # where it was last seen
    assert not w.puppets["hand.left"].velocity.any()
    w.frame(1 / 60, {"left": ((0.5, 0.2, 0.3), rot)})
    assert left.present and not w.puppets["hand.left"].velocity.any()   # arriving: no jump


def test_a_puppet_reads_its_spin_from_frame_to_frame():
    w = W.World.default()
    a = W.qexp([0.0, 0.0, 0.0])
    b = W.qexp([0.0, 0.05, 0.0])
    w.frame(1 / 60, {"right": ((0, 0, 0), _rot3(a))})
    w.frame(1 / 60, {"right": ((0, 0, 0), _rot3(b))})
    assert np.allclose(w.puppets["hand.right"].spin, (0.0, 3.0, 0.0))


def test_no_tracker_reads_no_palm():
    assert app.palms_in_world(None) == {}
    assert app.palms_in_world(GH.Ghost(ctx=None)) == {}


def test_the_frame_sets_the_shapes_home_from_the_params():
    w = W.World.default()
    h = NS(world=w, view=NS(zoom=1.5, pan=[0.25, -0.5]), renderer=NS(ghost=None))
    app._step_world(h, 1 / 60)
    home = w["shape"].home
    assert home.scale == 1.5 and np.allclose(home.position, (0.25, 0.5, 0.0, 0.0))
    assert np.allclose(home.model3(), G.model_matrix(1.5, (0.25, -0.5)))
    app._step_world(NS(world=None), 1 / 60)          # no world: nothing to do


# ---------------------------------------------------------------- the render

def test_no_offset_is_the_old_model_matrix_exactly():
    for zoom, pan in ((1.0, (0.0, 0.0)), (2.3, (0.7, -1.1))):
        old = np.eye(4)
        old[0, 0] = old[1, 1] = old[2, 2] = zoom
        old[0, 3], old[1, 3] = pan[0], -pan[1]
        assert np.array_equal(G.model_matrix(zoom, pan), old)
        assert np.array_equal(G.model_matrix(zoom, pan, None), old)
    assert W.World.default().offset_matrix("shape") is None


def test_a_known_offset_moves_each_vertex_by_exactly_that():
    """On the CPU, as the shader does it (`eye_project`): a turn of the offset
    turns the shape about its own centre, then the home places it."""
    V = G.geom(3)["V"]
    q = W.qexp([0.2, -0.4, 0.3])
    off = W.Pose.turn3(q, (0.3, -0.2, 0.5))
    zoom, pan = 1.4, (0.6, 0.2)
    got = G.eye_project(V, [0.1] * 6, 0.3, 0.2, zoom=zoom, pan=pan, offset=off.model3())
    P, _, _ = G.world_points(V, [0.1] * 6, 0.3, 0.2)
    moved = (P @ _rot3(q).T + (0.3, -0.2, 0.5)) * zoom + (pan[0], -pan[1], 0.0)
    mvp = G.eye_matrix(1200, 800)
    c = np.c_[moved, np.ones(len(moved))] @ mvp.T
    assert np.allclose(got[0], 600 + c[:, 0] / c[:, 3] * 600)
    assert np.allclose(got[1], 400 - c[:, 1] / c[:, 3] * 400)


def _draw(ctx, s, world=None, w=600, h=400):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.world = world
    tex = ctx.texture((w, h), 4)
    dep = ctx.depth_texture((w, h))
    fbo = ctx.framebuffer(color_attachments=[tex], depth_attachment=dep)
    fbo.use()
    ctx.viewport = (0, 0, w, h)
    try:
        r.draw_scene(s, w, h, t_now=0.0)
        assert ctx.error == "GL_NO_ERROR"
        return fbo.read(components=4), r._scene_mats
    finally:
        for res in (fbo, tex, dep):
            res.release()


def _view(**kw) -> ViewState:
    s = ViewState(shape=3, ang=[0.3, 0.1, 0.2, 0.4, 0.5, 0.6], yaw=0.4, pitch=0.2,
                  faces=True, lines=True, points=True)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


@pytest.mark.parametrize("kw", [{}, {"instances": 7, "zoom": 0.6},
                                {"instances": 9, "inst_fit": True}])
def test_the_default_world_draws_every_frame_byte_for_byte_as_none(ctx, kw):
    none = _draw(ctx, _view(**kw))
    assert _draw(ctx, _view(**kw), W.World.default()) == none


def test_an_offset_moved_in_x_and_y_is_a_pan(ctx):
    """At zoom 1 an offset's x and y are a pan's (y the other way up): the
    same matrix, the same frame, to the byte."""
    w = W.World.default()
    w["shape"].offset = W.Pose((0.5, 0.25, 0.0))
    moved = _draw(ctx, _view(), w)
    panned = _draw(ctx, _view(pan=[0.5, -0.25]))
    assert moved == panned
    assert moved != _draw(ctx, _view())


def test_an_offset_turn_and_z_reach_the_frame_and_the_cull(ctx):
    w = W.World.default()
    w["shape"].offset = W.Pose.turn3(W.qexp([0.0, 0.6, 0.0]), (0.0, 0.0, 0.4))
    img, mats = _draw(ctx, _view(), w)
    model = np.frombuffer(mats[1], dtype="f4").reshape(4, 4).T
    assert np.allclose(model, (G.model_matrix(1.0, (0.0, 0.0)) @ w["shape"].offset.model3()),
                       atol=1e-6)
    assert img != _draw(ctx, _view())[0]
    # a field of copies with the offset turning it: a copy is kept when its
    # box, turned, is in view, so the turned field is drawn whole
    many = _view(instances=7, zoom=0.5)
    img2, _ = _draw(ctx, many, w)
    assert np.frombuffer(img2, dtype=np.uint8).reshape(400, 600, 4)[..., :3].any()


def test_fit_and_the_3d_lattices_take_no_offset(ctx):
    """Register row 851: the field's own path carries the camera in each
    copy's row and its world transform stays the identity."""
    w = W.World.default()
    w["shape"].offset = W.Pose.turn3(W.qexp([0.0, 0.6, 0.0]), (0.3, 0.0, 0.4))
    fit = _view(instances=9, inst_fit=True)
    assert _draw(ctx, fit, w) == _draw(ctx, fit)
