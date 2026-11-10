"""The rigged hand models (handmesh.py): every shipped file loads, and the
skinning puts each model's bones on the tracked joints, whatever the hand."""

from __future__ import annotations

import ast
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
def test_each_bone_lands_on_the_tracked_joints(name, grip):
    """A bone's base goes to its tracked joint and its far end to the next:
    the model's fingers on the performer's, whatever the two sizes."""
    for side in ("left", "right"):
        p = _pose(side, grip)
        m = G.mesh_model(p, name)
        assert m is not None and m.side == side
        mats = HM.bone_matrices(m, p.joints)
        R = HM.rest_joints(m)
        for i, nm in enumerate(m.names):
            slot = m.slots[nm]
            if slot == HM.PALM or slot[1] >= 4:
                continue
            d, k = slot
            if np.linalg.norm(R[d, k] - R[d, k + 1]) < 1e-6:
                continue
            rot, off = mats[i, :3, :3], mats[i, :3, 3]
            assert np.allclose(rot @ R[d, k] + off, p.joints[d, k], atol=1e-6), (nm, side)
            assert np.allclose(rot @ R[d, k + 1] + off, p.joints[d, k + 1], atol=1e-6), (nm, side)


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
