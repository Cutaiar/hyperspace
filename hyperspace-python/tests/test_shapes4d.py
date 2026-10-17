"""The four-coordinate surface path and the W-plane mask (plan 22, A1).

A 3D surface built in the w = 0 hyperplane collapses onto a plane when a
W plane turns it a quarter turn. Two ways out, declared per shape in
`Shape.w`: lift the surface into w (every builder takes an optional `w`
of its own parameters), or keep it 3D and mask its W planes
(`geometry.view_angles`). The volume ratio (`geometry.volume_ratio`) is
the measure both are judged by — here and in tools/turntable.py.
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


def _as(monkeypatch, i: int, w: str) -> None:
    """Shape i declared `w` ("flat", "mask"…), for the length of one test."""
    shapes = list(G.SHAPES)
    shapes[i] = dataclasses.replace(shapes[i], w=w)
    monkeypatch.setattr(G, "SHAPES", shapes)


HEART = next(i for i, s in enumerate(G.SHAPES) if s.name == "Heart")   # masked (plan 22 A2)


# ------------------------------------------------- the lift changes nothing

@pytest.mark.parametrize("i", range(len(G.SHAPES)), ids=[s.name for s in G.SHAPES])
def test_every_shape_draws_what_it_drew_before_the_lift_existed(i):
    # recorded on plan-22-integration @ 2d4ea11, before any builder took a
    # lift; the six lifted shapes' rows re-recorded by plan 22 A2, the
    # Klein bottle's added by A3. A shape that is given a lift changes on
    # purpose: re-record its row (python tests/test_shapes4d.py --record)
    # and say so in the commit; a polytope's row must never move
    assert digest(i) == json.loads(DIGESTS.read_text())[str(i)]


def test_mesh3_carries_a_fourth_coordinate_when_given_one():
    flat, _ = G._mesh3([[(0, 0, 0), (1, 0, 0)], [(0, 1, 0), (1, 1, 0)]], False, False)
    assert [v[3] for v in flat["V"]] == [0.0] * 4
    lifted, _ = G._mesh3([[(0, 0, 0, 0.5), (1, 0, 0, -0.5)],
                          [(0, 1, 0, 0.25), (1, 1, 0, 0.0)]], False, False)
    assert [v[3] for v in lifted["V"]] == [0.5, -0.5, 0.25, 0.0]
    assert lifted["E"] == flat["E"] and lifted["F"] == flat["F"]
    # points merge only when every coordinate agrees: same xyz, other w
    # are two vertices
    split, _ = G._mesh3([[(0, 0, 0, 0.0), (0, 0, 0, 1.0)], [(0, 1, 0), (1, 1, 0)]],
                        False, False)
    assert len(split["V"]) == 4


def _torus(u, v):
    return ((1 + 0.45 * math.cos(v)) * math.cos(u), 0.45 * math.sin(v),
            (1 + 0.45 * math.cos(v)) * math.sin(u))


def test_a_lift_keeps_the_surface_and_its_faces_and_adds_w():
    flat = G.param_surface(_torus, 32, 16)
    lift = lambda u, v: 0.4 * math.sin(2 * u) * math.cos(v)
    up = G.param_surface(_torus, 32, 16, w=lift)
    assert len(up["V"]) == len(flat["V"]) and up["E"] == flat["E"] and up["F"] == flat["F"]
    assert np.array_equal(np.asarray(up["V"])[:, :3], np.asarray(flat["V"])[:, :3])
    du, dv = 2 * math.pi / 32, 2 * math.pi / 16
    want = [lift(i * du, j * dv) for i in range(32) for j in range(16)]
    assert np.allclose(np.asarray(up["V"])[:, 3], want)
    # a sample function may also return all four coordinates itself
    native = G.param_surface(lambda u, v: (*_torus(u, v), lift(u, v)), 32, 16)
    assert native == up


def test_every_builder_takes_a_lift_of_its_own_parameters():
    # spherical: w(θ, φ); the poles still merge when w agrees there
    s = G.spherical_surface(lambda th, ph: 1.0, 12, 7, w=lambda th, ph: math.sin(ph) ** 2)
    assert len(s["V"]) == len(G.spherical_surface(lambda th, ph: 1.0, 12, 7)["V"])
    V = np.asarray(s["V"])
    assert np.allclose(V[:, 3], 1 - V[:, 1] ** 2)
    # prisms: w(t, z), t the outline parameter, z = ±depth / 2
    p = G.polar_prism(lambda th: 1.0, n=16, depth=0.4, w=lambda t, z: z * math.cos(t))
    V = np.asarray(p["V"])
    assert np.allclose(V[:, 3], V[:, 2] * V[:, 0])
    star = G.ring_prism([(1, 0), (0, 1), (-1, 0), (0, -1)], 1.0, w=lambda t, z: t)
    assert sorted({round(v[3], 9) for v in star["V"]}) == [
        round(k * math.pi / 2, 9) for k in range(4)]
    # tube: w(t, a), t along the curve, a the nominal angle round it
    c = lambda t: (math.cos(t), math.sin(t), 0.0)
    tb = G.tube(c, n=12, m=6, radius=0.2, w=lambda t, a: math.sin(a))
    flat = G.tube(c, n=12, m=6, radius=0.2)
    assert np.allclose(np.asarray(tb["V"])[:, :3], np.asarray(flat["V"])[:, :3])
    assert np.allclose(np.asarray(tb["V"])[:, 3],
                       [math.sin(2 * math.pi * j / 6) for _ in range(12) for j in range(6)])


def _mobius(u, v):
    h = v - 0.5
    rr = 1 + 0.45 * h * math.cos(u / 2)
    return (rr * math.cos(u), 0.45 * h * math.sin(u / 2), rr * math.sin(u))


def test_the_mobius_seam_welds_only_under_a_lift_that_agrees_across_it():
    # the u = 2π column meets the u = 0 column flipped in v: a lift must
    # satisfy w(2π, 1 − v) == w(0, v) or the strip is left open there
    welds = G.param_surface(_mobius, 65, 5, v1=1.0, wrap_u=False, wrap_v=False,
                            w=lambda u, v: 0.3 * math.sin(u))
    assert len(welds["V"]) == 65 * 5 - 5
    opens = G.param_surface(_mobius, 65, 5, v1=1.0, wrap_u=False, wrap_v=False,
                            w=lambda u, v: 0.3 * (v - 0.5))
    assert len(opens["V"]) == 65 * 5 - 1      # only the centre line still meets


def test_a_shape_says_how_it_fills_w():
    assert all(s.w == "native" for s in G.SHAPES[:18])
    assert all(s.w in G.W_KINDS for s in G.SHAPES)
    with pytest.raises(ValueError):
        dataclasses.replace(G.SHAPES[21], w="squash")


# ------------------------------------------------------------- the mask

def test_no_shape_but_a_masked_one_has_its_angles_touched():
    ang = [0.3, 0.1, 0.7, 0.2, 0.5, 0.9]
    for i, s in enumerate(G.SHAPES):
        if s.w != "mask":
            assert G.view_angles(i, ang) is ang
    assert not any(s.w == "mask" for s in G.SHAPES[:18])


def test_a_masked_shape_turns_in_3d_where_its_w_planes_would_have_turned_it():
    assert G.SHAPES[HEART].w == "mask"
    ang = [0.3, 0.1, 0.7, 0.2, 0.5, 0.9]
    out = G.view_angles(HEART, ang)
    assert out[3:] == [0.0, 0.0, 0.0]
    for p, q in G.W_REMAP.items():
        assert out[q] == ang[q] + ang[p]
    assert ang == [0.3, 0.1, 0.7, 0.2, 0.5, 0.9], "the view's angles are never written"
    # the bass planes cannot move it into w: w stays 0 whatever the angles
    V = G.geom(HEART)["V"]
    for a in np.linspace(0, 2 * math.pi, 13):
        v = G.rotate4(V, G.view_angles(HEART, [a] * 6))
        assert np.abs(v[:, 3]).max() == 0.0


def test_the_renderer_draws_a_masked_shape_through_view_angles(monkeypatch):
    from hyperspace.render import render_offscreen
    from hyperspace.view import ViewState

    def frame(i, plane=None):
        s = ViewState(shape=i, playing=False)
        s.ang = [0.0] * 6
        if plane:
            s.ang[G.PLANE_NAMES.index(plane)] = 1.1
        return render_offscreen(s, 96, 96)

    assert np.array_equal(frame(HEART, "XW"), frame(HEART, "XZ"))  # XW is remapped onto XZ
    assert np.array_equal(frame(HEART, "YW"), frame(HEART, "YZ"))
    assert np.array_equal(frame(HEART, "ZW"), frame(HEART, "XY"))
    masked_rest = frame(HEART)
    torus = next(i for i, s in enumerate(G.SHAPES) if s.name == "Torus")   # lifted
    assert G.SHAPES[torus].w == "lift"                    # its W planes are its own
    assert not np.array_equal(frame(torus, "XW"), frame(torus, "XZ"))
    # w is 0 at every angle, so the depth cue reads z instead: at rest the
    # same heart left flat draws at the cue's dimmest, masked it does not
    _as(monkeypatch, HEART, "flat")
    assert not np.array_equal(frame(HEART, "XW"), frame(HEART, "XZ"))
    assert masked_rest.mean() > 1.5 * frame(HEART).mean()


def test_a_masked_shape_cues_depth_toward_the_camera_however_the_camera_turns():
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


def test_a_flat_shape_collapses_at_a_quarter_turn_of_each_w_plane(monkeypatch):
    # the bug, measured: w = 0, so a quarter turn carries a whole axis into
    # w and the 4D→3D divide drops it. No shape ships flat since plan 22
    # A2; the heart, built at w = 0, shows it with its mask taken off
    _as(monkeypatch, HEART, "flat")
    for plane in ("XW", "YW", "ZW"):
        r = G.sweep_ratios(HEART, plane, steps=72)
        assert r[18] < 1e-9 and r[54] < 1e-9, plane     # 90° and 270°


@pytest.mark.parametrize("i", [i for i, s in enumerate(G.SHAPES) if s.w == "native"],
                         ids=lambda i: G.SHAPES[i].name)
def test_every_4d_shape_clears_the_volume_floor(i):
    # the floor is set from these: every polytope and the Clifford torus
    # keep at least this much volume through every W plane, so a surface
    # held to it is held to what the 4D shapes already do
    for pose in (None, G.GENERIC_POSE):
        for plane in ("XW", "YW", "ZW"):
            assert G.sweep_ratios(i, plane, pose=pose).min() >= G.VOLUME_FLOOR, plane


def test_masking_a_flat_surface_lifts_it_over_the_floor(monkeypatch):
    for plane in ("XW", "YW", "ZW"):
        assert G.sweep_ratios(HEART, plane).min() >= G.VOLUME_FLOOR
    _as(monkeypatch, HEART, "flat")
    assert G.sweep_ratios(HEART, "XW").min() < G.VOLUME_FLOOR


# a single ring (a scene's orbit, plan 28) is flat by what it is: it is
# gated for its faces (it has none) but not for its volume
FLAT_BY_NATURE = {"Orbit"}
GATED = [i for i, s in enumerate(G.SHAPES) if s.w in ("lift", "mask")]
GATED_VOLUME = [i for i in GATED if G.SHAPES[i].name not in FLAT_BY_NATURE]


def test_every_shape_past_the_polytopes_is_lifted_or_masked():
    # what keeps the two gates below from passing on an empty list: every
    # surface after the Clifford torus is gated, none ships flat. The plan
    # 28 catalog's 4D toys (the Hopf fibration, a scene round a tesseract)
    # are native, and held to the 4D floor instead
    native = [i for i in range(18, len(G.SHAPES)) if i not in GATED]
    assert all(G.SHAPES[i].family and G.SHAPES[i].w == "native" for i in native)
    assert [G.SHAPES[i].name for i in native] == ["Hopf fibration", "Celestial tesseract"]
    assert not any(s.w == "flat" for s in G.SHAPES)


@pytest.mark.parametrize("i", GATED_VOLUME, ids=lambda i: G.SHAPES[i].name)
def test_a_lifted_or_masked_shape_keeps_its_volume_through_each_w_plane(i):
    # Stream A's acceptance: no turn of XW, YW or ZW alone — from rest or
    # from a generic pose — reduces the shape to a plane or a line
    for pose in (None, G.GENERIC_POSE):
        for plane in ("XW", "YW", "ZW"):
            r = G.sweep_ratios(i, plane, pose=pose)
            assert r.min() >= G.VOLUME_FLOOR, (
                f"{plane} from {'rest' if pose is None else 'a generic pose'}: "
                f"{r.min():.3f} at {5 * int(r.argmin())}°")


@pytest.mark.parametrize("i", GATED, ids=lambda i: G.SHAPES[i].name)
def test_a_lifted_or_masked_shape_never_turns_much_of_itself_edge_on(i):
    # the second gate: a cloud can keep its volume while its faces turn
    # edge-on and the surface reads as a sheet. 0.15 sits just under the
    # 4D shapes' own worst — the cubic pyramid turns 0.155 of its face
    # area edge-on, the 3,3-duoprism 0.167 — and over every gated shape's
    # (the star's 0.139 is the closest); a masked shape never turns any
    for pose in (None, G.GENERIC_POSE):
        for plane in ("XW", "YW", "ZW"):
            assert G.sweep_edge_on(i, plane, pose=pose).max() <= 0.15, plane


def test_a_lifted_cap_is_triangulated_over_its_own_outline():
    # the star's caps are bent through w by its lift: each is framed in its
    # least-squares plane (geometry._face_xy), where its outline must stay
    # simple and its triangles must tile it exactly — no gap, no overlap
    star = next(i for i, s in enumerate(G.SHAPES) if s.name == "Star")
    V, F, T = G.geom(star)["V"], G.faces(star), G.face_triangles(star)
    caps = [fi for fi, c in enumerate(F) if len(c) > 4]
    assert len(caps) == 2
    for fi in caps:
        cyc = F[fi]
        P = V[np.asarray(cyc)]
        assert np.linalg.svd(P - P.mean(0), compute_uv=False)[2] > 1e-3, "the cap is bent"
        xy = G._face_xy(P)
        pos = {v: k for k, v in enumerate(cyc)}
        cross = lambda a, b, c: (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        poly = 0.5 * sum(cross((0, 0), xy[k], xy[(k + 1) % len(xy)]) for k in range(len(xy)))
        tris = [0.5 * cross(xy[pos[int(a)]], xy[pos[int(b)]], xy[pos[int(c)]])
                for a, b, c, f in T if f == fi]
        assert min(tris) > 0, "every triangle keeps the outline's winding"
        assert sum(tris) == pytest.approx(poly, rel=1e-9)


if __name__ == "__main__" and "--record" in sys.argv:
    DIGESTS.write_text(json.dumps({str(i): digest(i) for i in range(len(G.SHAPES))},
                                  indent=1, ensure_ascii=False) + "\n")
    print("wrote", DIGESTS)
