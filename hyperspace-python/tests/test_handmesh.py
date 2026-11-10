"""The rigged hand models (handmesh.py): every shipped file loads, and the
skinning puts each model's bones on the tracked joints, whatever the hand."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest
from fake_hands import hand

from hyperspace import ghost as G
from hyperspace import handmesh as HM
from hyperspace.hands import skeleton


def _pose(side="right", grip="open", mirror=False, **kw):
    return G.pose(side, skeleton(hand(side, grip, **kw)), G.basis("desktop", mirror))


@pytest.mark.parametrize("name", sorted(HM.MODELS))
def test_every_shipped_model_loads_on_both_sides(name):
    ms = HM.models(name)
    assert ms is not None and set(ms) == {"left", "right"}
    for side, m in ms.items():
        assert m.side == side
        assert len(m.names) <= HM.MAX_BONES
        assert m.joints.max() < len(m.names) and m.joints.min() >= 0
        assert np.allclose(m.weights.sum(axis=1), 1.0)
        assert m.indices.max() < len(m.positions)
        # a hand, in mm: a palm to a fingertip is 12-30 cm, model to model
        span = np.ptp(m.positions, axis=0).max()
        assert 120.0 < span < 300.0, span
        # every finger joint the tracker has is in the rig
        slots = {s for s in m.slots.values() if s != HM.PALM}
        assert {(d, k) for d in range(1, 5) for k in range(5)} <= slots
        assert {(0, 2), (0, 3), (0, 4)} <= slots


@pytest.mark.parametrize("name", sorted(HM.MODELS))
def test_the_rest_pose_skins_to_itself(name):
    for m in HM.models(name).values():
        mats = HM.bone_matrices(m, HM.rest_joints(m))
        assert np.allclose(mats, np.eye(4), atol=1e-9)


@pytest.mark.parametrize("grip", ["open", "fist"])
@pytest.mark.parametrize("name", sorted(HM.MODELS))
def test_each_finger_follows_the_tracked_bones(name, grip):
    """Each finger bone points where the tracked one does and is as long;
    each starts where the one before it ends; a fingertip lands near the
    tracked one (the palm is the model's own shape, so not exactly)."""
    for side in ("left", "right"):
        p = _pose(side, grip)
        m = G.mesh_model(p, name)
        assert m is not None and m.side == side
        mats = HM.bone_matrices(m, p.joints)
        R = HM.rest_joints(m)
        at = {m.slots[nm]: mats[i] for i, nm in enumerate(m.names) if m.slots[nm] != HM.PALM}
        move = lambda mat, q: mat[:3, :3] @ q + mat[:3, 3]
        for d in range(5):
            for k in range(2 if d == 0 else 1, 4):
                a, b = move(at[(d, k)], R[d, k]), move(at[(d, k)], R[d, k + 1])
                want = p.joints[d, k + 1] - p.joints[d, k]
                assert np.allclose(b - a, want, atol=1e-6), (name, side, d, k)
                if k < 3:
                    assert np.allclose(b, move(at[(d, k + 1)], R[d, k + 1]), atol=1e-6)
            tip = move(at[(d, 3)], R[d, 4])
            # the synthetic hands' knuckles are not a real hand's: loosely
            assert np.linalg.norm(tip - p.joints[d, 4]) < 0.4 * p.width, (name, side, d)


@pytest.mark.parametrize("name", sorted(HM.MODELS))
def test_spread_fingers_leave_the_palm_alone(name):
    """Spread fingers fan the tracker's metacarpals; the drawn palm keeps
    its shape and its size (a spread once ballooned the whole hand)."""
    def palm_of(p):
        m = G.mesh_model(p, name)
        return HM.bone_matrices(m, p.joints)[next(i for i, nm in enumerate(m.names)
                                                  if m.slots[nm] == HM.PALM)]
    a, b = _pose("right", spread=1.0), _pose("right", spread=2.2)
    sa = np.linalg.svd(palm_of(a)[:3, :3], compute_uv=False)
    sb = np.linalg.svd(palm_of(b)[:3, :3], compute_uv=False)
    assert np.allclose(sa, sb, rtol=1e-6)
    assert np.allclose(sa, sa[0])                       # a uniform scale: no stretch


@pytest.mark.parametrize("name", sorted(HM.MODELS))
def test_on_a_real_hands_joints_the_fingertips_land(name):
    """Ultraleap's reference hand (what the tracker's own hand model
    reports): each fingertip within 10 mm of the tracked one."""
    J = np.array(json.loads((Path(__file__).parent / "fixtures" / "leap_reference_hand.json")
                            .read_text())["joints"])
    m = HM.models(name)["left"]
    R, mats = HM.rest_joints(m), HM.bone_matrices(m, J)
    last = {m.slots[nm][0]: mats[i] for i, nm in enumerate(m.names) if m.slots[nm] != HM.PALM
            and m.slots[nm][1] == 3}
    for d in range(5):
        tip = last[d][:3, :3] @ R[d, 4] + last[d][:3, 3]
        assert np.linalg.norm(tip - J[d, 4]) < 10.0, (name, d)


def test_the_hand_drawn_is_the_poses_own_handedness():
    """A mirrored stage turns a right hand into a left one: the model
    follows the joints, not the tracker's label."""
    for side in ("left", "right"):
        assert HM.chirality(_pose(side).joints, _pose(side).normal) == side
        mp = _pose(side, mirror=True)
        assert HM.chirality(mp.joints, mp.normal) != side


def test_a_mirrored_model_is_the_other_hand():
    m = HM.models("webxr")["right"]
    w = m.mirrored()
    assert w.side == "left"
    assert np.allclose(w.positions[:, 0], -m.positions[:, 0])
    assert np.array_equal(w.indices.reshape(-1, 3), m.indices.reshape(-1, 3)[:, ::-1])
    assert np.allclose(HM.bone_matrices(w, HM.rest_joints(w)), np.eye(4), atol=1e-9)


def test_a_palm_only_pose_has_no_model():
    p = G.pose("right", {"palm": (0, 200, 0), "normal": (0, -1, 0), "direction": (0, 0, -1),
                         "width": 85.0, "digits": []}, G.basis("desktop"))
    assert G.mesh_model(p, "webxr") is None
    spheres, _, _ = G.mesh_parts(p)
    assert spheres and np.allclose(spheres[0][0], p.palm)


def test_junk_is_not_a_glb():
    with pytest.raises(ValueError):
        HM.read_glb(b"not a model at all, not even close")


def test_handmesh_is_a_leaf():
    """numpy only: no GL, no package import."""
    tree = ast.parse(Path(HM.__file__).read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            assert n.level == 0, "imports from the package"
            assert n.module in ("__future__", "dataclasses", "pathlib"), n.module
        elif isinstance(n, ast.Import):
            assert {a.name for a in n.names} <= {"json", "struct", "numpy"}


def test_the_mesh_styles_draw(ctx):
    """Each mesh style puts pixels where the hands are, and a different
    picture from the capsules'."""
    from types import SimpleNamespace as NS

    from hyperspace.render import Renderer

    skel = {"left": skeleton(hand("left", "open", (-90.0, 210.0, 0.0))),
            "right": skeleton(hand("right", "fist", (90.0, 200.0, 10.0)))}
    seen = []
    for style in ("HANDS", "MESH", "LEAP HAND", "LOW POLY"):
        gh = Renderer(ctx).ghost
        gh.state.on, gh.state.alpha, gh.state.style = True, 1.0, G.STYLES.index(style)
        gh.source = NS(skeleton=skel, cfg={"mode": "desktop"})
        for k in range(3):
            assert gh.layer((320, 200), 1.0 + k / 30)
        px = np.frombuffer(gh.tex.read(), dtype=np.uint8).reshape(200, 320, 4)
        assert (px[..., 3] > 0).sum() > 500, style
        seen.append(px.tobytes())
    assert len(set(seen)) == 4


@pytest.mark.parametrize("name", sorted(HM.MODELS))
@pytest.mark.parametrize("side", ["left", "right"])
def test_every_tracked_joint_lands_where_it_is_tracked(name, side):
    """On a real hand's joints, knuckle to tip, each digit's joints land
    on the tracker's own — not merely near them.

    The fingers used to hang off a rigid palm, so each carried its
    knuckle's offset unchanged all the way to the tip: here the pinky sat
    13 mm out, a finger's own width, which is what pulled the ring-pinky
    web about. Driving each finger's metacarpal from the tracker closes
    it. The reference hand, not `fake_hands`, because the synthetic
    metacarpals are all ~78 mm where a real hand's taper 68 → 54, which
    stretches a model's pinky metacarpal past the skinning's own clamp.
    """
    J = np.array(json.loads((Path(__file__).parent / "fixtures" / "leap_reference_hand.json")
                            .read_text())["joints"])
    if side == "right":                     # the reference hand is a left one
        J = J * np.array([-1.0, 1.0, 1.0])
    m = HM.models(name)[side]
    R, mats = HM.rest_joints(m), HM.bone_matrices(m, J)
    at = {m.slots[nm]: mats[i] for i, nm in enumerate(m.names) if m.slots[nm] != HM.PALM}
    for d in range(5):
        for k in range(1, 5):               # the thumb's (0, 0) stays on the palm
            if (d, k) not in at:
                continue
            got = at[(d, k)][:3, :3] @ R[d, k] + at[(d, k)][:3, 3]
            assert np.linalg.norm(got - J[d, k]) < 1e-6, (name, side, d, k)


@pytest.mark.parametrize("name", sorted(HM.MODELS))
@pytest.mark.parametrize("grip,kw", [("open", {}), ("fist", {}), ("open", {"spread": 2.2}),
                                     ("open", {"close": 0.5}), ("open", {"roll": 75.0})])
def test_no_digit_drifts_a_finger_width_off(name, grip, kw):
    """Whatever the grip, no joint sits a finger's width (10 mm) from the
    tracked one. The synthetic hand's metacarpals are long enough to work
    the skinning's stretch clamp, so this is a bound, not the equality
    above; off the rigid palm the pinky broke it at 12.6 mm open."""
    p = _pose("right", grip, **kw)
    m = G.mesh_model(p, name)
    R, mats = HM.rest_joints(m), HM.bone_matrices(m, p.joints)
    at = {m.slots[nm]: mats[i] for i, nm in enumerate(m.names) if m.slots[nm] != HM.PALM}
    for d in range(5):
        for k in range(1, 5):
            if (d, k) not in at:
                continue
            got = at[(d, k)][:3, :3] @ R[d, k] + at[(d, k)][:3, 3]
            assert np.linalg.norm(got - p.joints[d, k]) < 10.0, (name, d, k)


def test_every_material_draws_the_same_bones_differently(ctx):
    """`ghost.material` changes what the hands are made of, not what is
    drawn: the same style and the same poses, a different picture each
    time, and every one of them still a hand's worth of pixels."""
    from types import SimpleNamespace as NS

    from hyperspace.render import Renderer

    skel = {"left": skeleton(hand("left", "open", (-90.0, 210.0, 0.0))),
            "right": skeleton(hand("right", "fist", (90.0, 200.0, 10.0)))}
    seen = []
    for mat in range(len(G.MATERIALS)):
        gh = Renderer(ctx).ghost
        gh.state.on, gh.state.alpha = True, 1.0
        gh.state.style, gh.state.material = G.STYLES.index("BONES"), mat
        gh.source = NS(skeleton=skel, cfg={"mode": "desktop"})
        for k in range(3):
            assert gh.layer((320, 200), 1.0 + k / 30)
        px = np.frombuffer(gh.tex.read(), dtype=np.uint8).reshape(200, 320, 4)
        assert (px[..., 3] > 0).sum() > 300, G.MATERIALS[mat]
        seen.append(px.tobytes())
    assert len(set(seen)) == len(G.MATERIALS)
