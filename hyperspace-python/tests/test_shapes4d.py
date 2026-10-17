"""4D shapes and 3D shapes (plan 28, replacing plan 22's lifts and masks).

A shape says honestly what it is (`Shape.dims`). A 4D shape has real
w-extent and the W planes turn it through w. A 3D shape sits at w = 0 and
the W planes do nothing to it (`geometry.view_angles`): nothing is
invented for a fourth dimension it does not have. The 3D switch holds a 4D
shape's W pose (`ViewState.w_hold`). The volume ratio
(`geometry.volume_ratio`) still gates the 4D shapes through the W planes.
"""

import dataclasses
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace import geometry as G

DIGESTS = Path(__file__).parent / "golden" / "shape_digests.json"


def digest(i: int) -> dict:
    """What shape i draws, hashed: V, E, the face cycles, their
    triangulation and their UVs. Floats are rounded to 1e-9 first, so a
    last-bit libm difference between machines is not a change; integers
    are hashed as they are."""
    g = G.geom(i)
    h = hashlib.sha256()
    h.update((np.round(g["V"], 9) + 0.0).tobytes())
    h.update(g["E"].tobytes())
    h.update(json.dumps(G.faces(i)).encode())
    h.update(G.face_triangles(i).tobytes())
    h.update((np.round(G.face_uvs(i), 9) + 0.0).tobytes())
    return {"name": G.SHAPES[i].name, "n": g["n"], "m": g["m"],
            "faces": len(G.faces(i)), "sha256": h.hexdigest()}


HEART = next(i for i, s in enumerate(G.SHAPES) if s.name == "Heart")
THREE_D = [i for i, s in enumerate(G.SHAPES) if s.dims == 3]
FOUR_D = [i for i, s in enumerate(G.SHAPES) if s.dims == 4]


# --------------------------------------------------- what each shape draws

@pytest.mark.parametrize("i", range(len(G.SHAPES)), ids=[s.name for s in G.SHAPES])
def test_every_shape_draws_what_it_was_recorded_drawing(i):
    # recorded on plan-22-integration @ 2d4ea11; plan 28 took the plan 22
    # lifts off again (those rows back at w = 0) and added the catalog. A
    # shape that changes on purpose: re-record its row (python
    # tests/test_shapes4d.py --record) and say so in the commit; a
    # polytope's row must never move
    assert digest(i) == json.loads(DIGESTS.read_text())[str(i)]


# ------------------------------------------------------- 4D or 3D, honestly

def test_a_shape_is_4d_or_3d():
    assert all(s.dims == 4 for s in G.SHAPES[:18])
    assert all(s.dims in G.DIMS for s in G.SHAPES)
    assert {G.SHAPES[i].name for i in FOUR_D[18:]} == {
        "Hopf fibration", "Celestial tesseract", "Snub 24-cell", "Rectified 24-cell",
        "Bitruncated 5-cell", "Omnitruncated 5-cell", "Grand antiprism",
        "Disphenoidal 288-cell"}
    with pytest.raises(ValueError):
        dataclasses.replace(G.SHAPES[21], dims=5)


@pytest.mark.parametrize("i", THREE_D, ids=lambda i: G.SHAPES[i].name)
def test_a_3d_shape_sits_at_w_0(i):
    # nothing invented for a fourth dimension it does not have
    assert (G.geom(i)["V"][:, 3] == 0).all()


def test_a_mesh_is_built_at_w_0():
    g, _ = G._mesh3([[(0, 0, 0), (1, 0, 0)], [(0, 1, 0), (1, 1, 0)]], False, False)
    assert [v[3] for v in g["V"]] == [0.0] * 4


def test_a_4d_shape_takes_the_views_angles_as_they_are():
    ang = [0.3, 0.1, 0.7, 0.2, 0.5, 0.9]
    for i in FOUR_D:
        assert G.view_angles(i, ang) is ang


def test_the_w_planes_leave_a_3d_shape_alone():
    ang = [0.3, 0.1, 0.7, 0.2, 0.5, 0.9]
    out = G.view_angles(HEART, ang)
    assert out == [0.3, 0.1, 0.7, 0.0, 0.0, 0.0]
    assert ang == [0.3, 0.1, 0.7, 0.2, 0.5, 0.9], "the view's angles are never written"
    # turned in a W plane alone it is where it was, whatever the angle
    V = G.geom(HEART)["V"]
    for a in np.linspace(0, 2 * math.pi, 13):
        for p in (3, 4, 5):
            ang = [0.0] * 6
            ang[p] = a
            assert np.array_equal(G.rotate4(V, G.view_angles(HEART, ang)), V)


def test_the_renderer_draws_a_3d_shape_without_its_w_turns():
    from hyperspace.render import render_offscreen
    from hyperspace.view import ViewState

    def frame(i, plane=None):
        s = ViewState(shape=i, playing=False)
        s.ang = [0.0] * 6
        if plane:
            s.ang[G.PLANE_NAMES.index(plane)] = 1.1
        return render_offscreen(s, 96, 96)

    rest = frame(HEART)
    for plane in ("XW", "YW", "ZW"):
        assert np.array_equal(frame(HEART, plane), rest), plane
    assert not np.array_equal(frame(HEART, "XZ"), rest)
    # a 4D shape is turned by them
    assert not np.array_equal(frame(3, "XW"), frame(3))


def test_a_3d_shape_cues_depth_toward_the_camera_however_the_camera_turns():
    # the cue is the depth the 3D divide reads, camera included: a camera
    # yawed half round draws what the shape turned half round in XZ draws.
    # Cued on the shape's own z, the far side would come out bright and on
    # top (every pixel's difference averaged 8.7 of 255 that way)
    from hyperspace.render import render_offscreen
    from hyperspace.view import ViewState

    def frame(ang, yaw=0.0):
        s = ViewState(shape=HEART, playing=False)
        s.ang, s.yaw = list(ang), yaw
        return render_offscreen(s, 96, 96).astype(int)

    turned = frame([0.0, math.pi, 0.0, 0.0, 0.0, 0.0])
    assert np.abs(turned - frame([0.0] * 6, yaw=math.pi)).mean() < 0.1
    V = G.geom(HEART)["V"]
    assert np.array_equal(G.view_depth(V, [0.0] * 6, 0.0, 0.0), V[:, 2])   # at rest: z


# ---------------------------------------------------------- the 3D switch

def _drawn(s):
    """Where the renderer puts the tesseract's corners for view s."""
    px, py, pd, _ = G.shape_view(3, s.ang, s.yaw, s.pitch, d4=s.depth4,
                                 flat=s.held, body=s.body)
    return np.stack([px, py, pd], axis=1)


def test_the_3d_switch_never_jumps_on_or_off():
    from hyperspace.view import ViewState

    s = ViewState(shape=3, planes=[True] * 6, speed=1.0)
    s.integrate(0.8)
    before = _drawn(s)
    s.three_d = True
    s.integrate(0.0)                                    # the frame it goes on
    assert s.held
    assert np.allclose(_drawn(s), before), "on: no jump"
    w, xyz = list(s.ang[3:6]), list(s.ang[:3])
    s.integrate(0.7)
    assert s.ang[3:6] == w and s.ang[:3] != xyz         # 3D planes on, W stopped
    held = _drawn(s)
    s.ang[3] += 1.0                                     # a route on a W angle
    assert np.allclose(_drawn(s), held), "while it holds, W moves nothing"
    s.three_d = False
    s.integrate(0.0)                                    # the frame it goes off
    assert not s.held
    assert np.allclose(_drawn(s), held), "off: no jump"
    s.integrate(0.5)
    assert s.ang[3:6] != w                              # the W planes go on


def test_while_it_holds_a_4d_shape_turns_rigidly_in_3d():
    # w is held: every corner keeps its w, so the 4D divide scales it by
    # the same factor whatever the 3D turn — distances from the centre stay
    from hyperspace.view import ViewState

    s = ViewState(shape=3, planes=[True] * 6, speed=1.0)
    s.integrate(0.9)
    s.three_d = True
    s.integrate(0.0)
    radii = lambda: np.linalg.norm(
        G.project3(G.geom(3)["V"] @ s.body.T, G.view_angles(3, s.ang, s.held)), axis=1)
    r0 = radii()
    w0 = (G.geom(3)["V"] @ s.body.T)[:, 3]
    for _ in range(3):
        s.integrate(0.6)
        assert np.allclose(radii(), r0)
        assert np.allclose((G.geom(3)["V"] @ s.body.T)[:, 3], w0)


# ------------------------------------------------------- the volume ratio

def test_the_volume_ratio_reads_a_box_by_its_proportions():
    box = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-0.5, 0.5)])
    assert G.volume_ratio(box) == pytest.approx(0.5)
    assert G.volume_ratio(box * 3 + 7) == pytest.approx(0.5)     # scale and place free
    assert G.volume_ratio(box * [1, 1, 0]) == pytest.approx(0.0, abs=1e-12)
    assert G.volume_ratio(np.zeros((4, 3))) == 0.0


def test_the_edge_on_share_counts_the_face_area_turned_into_w():
    # one square in the XY plane, one in YW: a quarter turn of XW moves
    # the first's x into w (edge-on) and brings the second's w out as x
    V = np.array([[0, 0, 0, 0], [1, 0, 0, 0], [1, 1, 0, 0], [0, 1, 0, 0],
                  [0, 0, 0, 0], [0, 2, 0, 0], [0, 2, 0, 2], [0, 0, 0, 2]], float)
    tris = np.array([[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7]])
    at = lambda a: G.edge_on_share(V, G.project3(V, [0, 0, 0, a, 0, 0]), tris)
    assert at(0.0) == pytest.approx(0.8)          # the YW square, 4 of 5 parts
    assert at(math.pi / 2) == pytest.approx(0.2)  # the XY square
    assert G.edge_on_share(V, V[:, :3], tris[:0]) == 0.0


def test_project3_is_the_first_half_of_project_h():
    ang = [0.3, 0.1, 0.7, 0.2, 0.5, 0.9]
    for i in (3, 17, 21):
        V = G.geom(i)["V"]
        P = G.project3(V, ang, d4=3.1)
        v = G.rotate4(V, ang)
        assert np.array_equal(P, v[:, :3] * (3.1 / (3.1 - v[:, 3]))[:, None])


@pytest.mark.parametrize("i", FOUR_D, ids=lambda i: G.SHAPES[i].name)
def test_every_4d_shape_clears_the_volume_floor(i):
    # every polytope and the Clifford torus keep at least this much volume
    # through every W plane, from rest and from a generic pose
    for pose in (None, G.GENERIC_POSE):
        for plane in ("XW", "YW", "ZW"):
            assert G.sweep_ratios(i, plane, pose=pose).min() >= G.VOLUME_FLOOR, plane


def test_a_3d_shape_is_the_same_through_every_w_plane():
    # what a W turn once did to a 3D shape — a quarter turn carried a whole
    # axis into w and the divide dropped it, a sheet — cannot happen now
    for plane in ("XW", "YW", "ZW"):
        r = G.sweep_ratios(HEART, plane, steps=24)
        assert np.ptp(r) < 1e-12 and r[0] > G.VOLUME_FLOOR, plane


if __name__ == "__main__" and "--record" in sys.argv:
    DIGESTS.write_text(json.dumps({str(i): digest(i) for i in range(len(G.SHAPES))},
                                  indent=1, ensure_ascii=False) + "\n")
    print("wrote", DIGESTS)
