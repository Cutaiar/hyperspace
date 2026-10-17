"""Plan 28 (spike): the catalog of closed 3D solids, the mathematical toys,
the scenes that put several shapes in one frame, and the 3D switch.

The solids are appended after the Klein bottle (index is identity) and are
all masked: rigid 3D bodies whose W planes turn them in 3D planes. A scene
(`Shape.layers`) is several shapes sharing one centre, each layer at its
own scale, weight, colour and spin (`geometry.shape_view`).
"""

import math

import numpy as np
import pytest

from hyperspace import geometry as G

CATALOG = [i for i, s in enumerate(G.SHAPES) if s.family]
SOLIDS = [i for i in CATALOG if G.SHAPES[i].family not in ("Toy", "Scene", "Vector")]
SCENES = [i for i in CATALOG if G.SHAPES[i].family == "Scene"]
VECTORS = [i for i in CATALOG if G.SHAPES[i].family == "Vector"]
BY_NAME = {s.name: i for i, s in enumerate(G.SHAPES)}

# V, E, F of every solid: the textbook counts. A star is counted as what is
# seen — its visible surface, the buried core left out
COUNTS = {
    "Tetrahedron": (4, 6, 4), "Cube": (8, 12, 6), "Octahedron": (6, 12, 8),
    "Dodecahedron": (20, 30, 12), "Icosahedron": (12, 30, 20),
    "Cuboctahedron": (12, 24, 14), "Truncated octahedron": (24, 36, 14),
    "Rhombicuboctahedron": (24, 48, 26), "Snub cube": (24, 60, 38),
    "Icosidodecahedron": (30, 60, 32), "Truncated icosahedron": (60, 90, 32),
    "Rhombic dodecahedron": (14, 24, 12), "Rhombic triacontahedron": (32, 60, 30),
    "Small stellated dodecahedron": (32, 90, 60), "Great stellated dodecahedron": (32, 90, 60),
    "Moravian star": (50, 144, 96), "Starburst": (32, 90, 60),
    "Stella octangula": (8, 12, 8), "Five tetrahedra": (20, 30, 20),
    "Five cubes": (20, 60, 30), "Cube + octahedron": (14, 24, 14),
    "Dodecahedron + icosahedron": (32, 60, 32),
}


def test_the_catalog_is_appended_after_the_klein_bottle():
    assert CATALOG[0] == 26 and CATALOG == list(range(26, len(G.SHAPES)))
    assert G.SHAPES[25].name == "Klein bottle"
    # the scenes come after every shape they name; the vector subjects,
    # appended later, after the scenes (index is identity)
    for i in SCENES:
        assert all(G.shape_index(L.shape) < i for L in G.SHAPES[i].layers)
    assert SCENES + VECTORS == CATALOG[-len(SCENES) - len(VECTORS):]


def test_every_solid_has_a_count_and_every_count_a_solid():
    assert {G.SHAPES[i].name for i in SOLIDS} == set(COUNTS)


@pytest.mark.parametrize("i", SOLIDS, ids=lambda i: G.SHAPES[i].name)
def test_a_solid_has_its_textbook_counts(i):
    g, F = G.geom(i), G.faces(i)
    assert (g["n"], g["m"], len(F)) == COUNTS[G.SHAPES[i].name]


@pytest.mark.parametrize("i", CATALOG, ids=lambda i: G.SHAPES[i].name)
def test_a_catalog_shape_is_well_formed(i):
    s, g = G.SHAPES[i], G.geom(i)
    V, E = g["V"], g["E"]
    assert s.w in ("mask", "native")
    if s.w == "mask":
        assert (V[:, 3] == 0).all(), "a masked shape stays in w = 0"
    assert abs(np.linalg.norm(V, axis=1).max() - 1.0) < 1e-9
    assert (E[:, 0] != E[:, 1]).all()
    assert len({frozenset(e) for e in E.tolist()}) == g["m"]
    for cyc in G.faces(i):
        assert len(set(cyc)) == len(cyc) >= 3
    uv = G.face_uvs(i)
    assert uv.size == 0 or (uv.min() >= 0.0 and uv.max() <= 1.0)


@pytest.mark.parametrize("name", ["Tetrahedron", "Cube", "Octahedron", "Dodecahedron",
                                  "Icosahedron"])
def test_a_platonic_solid_is_regular(name):
    # one edge length, one face size, every corner on the sphere
    i = BY_NAME[name]
    g, F = G.geom(i), G.faces(i)
    V = g["V"]
    lens = np.linalg.norm(V[g["E"][:, 0]] - V[g["E"][:, 1]], axis=1)
    assert np.ptp(lens) < 1e-9
    assert len({len(c) for c in F}) == 1
    assert np.allclose(np.linalg.norm(V, axis=1), 1.0)


@pytest.mark.parametrize("name", ["Small stellated dodecahedron", "Great stellated dodecahedron",
                                  "Moravian star", "Starburst"])
def test_a_star_is_closed_like_a_sphere(name):
    # what shows of a star is one closed surface: every edge on two faces,
    # V − E + F = 2; its points on the circumsphere, its valleys inside it
    i = BY_NAME[name]
    g, F = G.geom(i), G.faces(i)
    count: dict = {}
    for c in F:
        for k in range(len(c)):
            e = frozenset((c[k], c[(k + 1) % len(c)]))
            count[e] = count.get(e, 0) + 1
    assert set(count.values()) == {2} and len(count) == g["m"]
    assert g["n"] - g["m"] + len(F) == 2
    r = np.linalg.norm(g["V"], axis=1)
    assert r.min() < 0.6 < r.max() == pytest.approx(1.0)


def test_a_kepler_star_is_spikes_on_its_buried_core():
    # the small stellated dodecahedron: 12 points at the icosahedron's
    # corners, 20 valleys at a buried dodecahedron's; the great stellated:
    # 20 points at the dodecahedron's, 12 valleys at an icosahedron's
    for name, points, valleys in (("Small stellated dodecahedron", 12, 20),
                                  ("Great stellated dodecahedron", 20, 12)):
        r = np.round(np.linalg.norm(G.geom(BY_NAME[name])["V"], axis=1), 9)
        assert sorted(np.unique(r, return_counts=True)[1].tolist()) == sorted([points, valleys])
        assert (r == 1.0).sum() == points


@pytest.mark.parametrize("name,k", [("Five tetrahedra", 5), ("Five cubes", 5),
                                    ("Stella octangula", 2)])
def test_a_compound_shares_its_corners(name, k):
    # the five cubes use each dodecahedron corner twice, the five
    # tetrahedra once; the stella octangula's two tetrahedra fill a cube
    g = G.geom(BY_NAME[name])
    assert g["n"] == (20 if k == 5 else 8)
    assert np.allclose(np.linalg.norm(g["V"], axis=1), 1.0)


def test_dual_compounds_cross_at_their_edges_midpoints():
    for name in ("Cube + octahedron", "Dodecahedron + icosahedron"):
        g = G.geom(BY_NAME[name])
        V, E = g["V"], g["E"]
        mids = (V[E[:, 0]] + V[E[:, 1]]) / 2
        keys = [G.kkey(m) for m in mids]
        # every midpoint is shared by exactly one edge of the other solid
        assert all(keys.count(k) == 2 for k in keys), name


def test_the_hopf_fibration_lies_on_the_3_sphere_in_linked_great_circles():
    i = BY_NAME["Hopf fibration"]
    g = G.geom(i)
    assert G.SHAPES[i].w == "native" and G.faces(i) == []
    assert np.allclose(np.linalg.norm(g["V"], axis=1), 1.0)
    # each fibre is a great circle: its 36 points span a plane through 0
    for k in range(0, g["n"], 36):
        P = g["V"][k:k + 36]
        assert np.linalg.svd(P, compute_uv=False)[2] < 1e-9


# ---------------------------------------------------------------- scenes

@pytest.mark.parametrize("i", SCENES, ids=lambda i: G.SHAPES[i].name)
def test_a_scene_is_its_layers_in_order(i):
    s, g = G.SHAPES[i], G.geom(i)
    rows = g["layers"]
    assert len(rows) == len(s.layers)
    assert rows[0][0] == 0 and rows[-1][1] == g["n"]
    for (a, b, j, spin), L in zip(rows, s.layers):
        assert G.SHAPES[j].name == L.shape and spin == L.spin
        own = G.geom(j)["V"] * L.scale
        assert np.allclose(g["V"][a:b], own / max(x.scale for x in s.layers))
    # faces only from the layers that draw them
    assert len(G.faces(i)) == sum(len(G.faces(j)) for _, _, j, _ in rows
                                  if s.layers[[r[2] for r in rows].index(j)].faces > 0)


def test_a_scene_turns_each_layer_at_its_own_angles():
    # a layer is drawn where its own shape would be, scaled, at the view's
    # angles (masked as its shape is) times its spin
    i = BY_NAME["Celestial tesseract"]
    g = G.geom(i)
    ang, yaw, pitch = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], 0.4, 0.25
    px, py, pd, _ = G.shape_view(i, ang, yaw, pitch)
    for a, b, j, spin in g["layers"]:
        la = [x * spin for x in G.view_angles(j, ang)]
        qx, qy, qd, _ = G.project_h(g["V"][a:b], la, yaw, pitch)
        assert np.allclose(px[a:b], qx) and np.allclose(py[a:b], qy)
        if G.w_masked(j):
            qd = G.view_depth(g["V"][a:b], la, yaw, pitch)
        assert np.allclose(pd[a:b], qd)


def test_the_star_pokes_through_the_tesseract():
    # the scene's point: at rest, the star's tips reach past the faces of
    # the tesseract's inner cube while the glome stays round them both
    i = BY_NAME["Celestial tesseract"]
    g = G.geom(i)
    P = G.project3(g["V"], [0.0] * 6)
    (h0, h1, _, _), (t0, t1, _, _), (s0, s1, _, _) = g["layers"]
    inner = np.abs(P[t0:t1][g["V"][t0:t1, 3] < 0]).max()       # the w < 0 cube's half side
    star = np.abs(P[s0:s1]).max(axis=1)
    assert (star > inner).sum() >= 6
    assert np.linalg.norm(P[h0:h1], axis=1).max() > np.linalg.norm(P[t0:t1], axis=1).max()


def test_a_shape_that_is_not_a_scene_is_drawn_as_before():
    # shape_view on one shape is project_h at view_angles, the depth cue
    # swapped for a masked one: the renderer's old path, to the bit
    ang, yaw, pitch = [0.3, 0.1, 0.7, 0.2, 0.5, 0.9], 0.4, -0.2
    for i in (3, 18, 21, BY_NAME["Cube"]):
        V = G.geom(i)["V"]
        a = G.view_angles(i, ang)
        want = list(G.project_h(V, a, yaw, pitch))
        if G.w_masked(i):
            want[2] = G.view_depth(V, a, yaw, pitch)
        for got, w in zip(G.shape_view(i, ang, yaw, pitch), want):
            assert np.array_equal(got, w)


# ---------------------------------------------------------- the 3D switch

def test_the_3d_switch_masks_every_shape():
    ang = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    assert G.view_angles(3, ang) is ang
    flat = G.view_angles(3, ang, flat=True)
    assert flat[3:] == [0.0, 0.0, 0.0]
    assert flat[:3] == pytest.approx([0.1 + 0.6, 0.2 + 0.4, 0.3 + 0.5])
    # the tesseract then holds its rest shadow: no W turn changes its shape
    V = G.geom(3)["V"]
    for a in (0.0, 0.7, math.pi / 2):
        P = G.project3(V, G.view_angles(3, [0, 0, 0, a, 0, 0], flat=True))
        rest = G.project3(V, [0.0] * 6)
        # a turn in XZ, so distances from the centre are kept
        assert np.allclose(np.sort(np.linalg.norm(P, axis=1)),
                           np.sort(np.linalg.norm(rest, axis=1)))



# ------------------------------------------------------- vector subjects

FLOW_MARK, FLOW_CAPS = BY_NAME["Flow mark"], BY_NAME["Flow capsules"]


def _bars(V: np.ndarray, faces: list) -> list:
    """Each bar's (x centre, width, height), left to right."""
    out = []
    for c in faces:
        P = V[np.asarray(c)]
        out.append((P[:, 0].mean(), np.ptp(P[:, 0]), np.ptp(P[:, 1])))
    return sorted(out)


def test_the_flow_mark_is_five_stadia_as_the_svg_draws_them():
    # five bars of one width on one pitch, their heights the SVG's: the
    # two outer bars tallest, then the middle one, the two short ones equal
    g = G.geom(FLOW_MARK)
    V, F = g["V"], G.faces(FLOW_MARK)
    assert len(F) == 5 and (V[:, 2] == 0).all() and g.get("flat") and g.get("curve")
    bars = _bars(V, F)
    widths = [b[1] for b in bars]
    assert np.ptp(widths) < 1e-9
    assert np.ptp(np.diff([b[0] for b in bars])) < 1e-3          # one pitch
    h = [b[2] / widths[0] for b in bars]                          # height in widths
    svg = [(bot - top) / (2 * G.FLOW_R) for _, top, bot in G.FLOW_BARS]
    assert h == pytest.approx(svg, abs=1e-3)
    assert h[0] == pytest.approx(h[4], abs=0.01) and h[1] == pytest.approx(h[3])
    assert h[0] > h[2] > h[1]


def test_the_flow_mark_shows_one_picture_through_its_bars():
    # its face UVs are the mark's own plane: a corner's UV is an affine
    # function of where it is, the same for every bar
    g = G.geom(FLOW_MARK)
    V, F = g["V"], G.faces(FLOW_MARK)
    P = np.concatenate([V[np.asarray(c), :2] for c in F])
    uv = np.concatenate([np.asarray(f) for f in g["FUV"]])
    A = np.hstack([P, np.ones((len(P), 1))])
    fit = np.linalg.lstsq(A, uv, rcond=None)[0]
    assert np.allclose(A @ fit, uv)
    assert fit[0, 0] > 0 and fit[0, 0] == pytest.approx(fit[1, 1])  # square, not stretched


def test_the_flow_capsules_are_the_marks_bars_lifted():
    # each bar, seen face-on, has the flat mark's outline; in depth it is
    # round, one bar's width deep; its UVs wrap it, v running up the bar
    caps, mark = G.geom(FLOW_CAPS), G.geom(FLOW_MARK)
    V = caps["V"]
    assert np.allclose(V[:, :2].min(0), mark["V"][:, :2].min(0))
    assert np.allclose(V[:, :2].max(0), mark["V"][:, :2].max(0))
    width = _bars(mark["V"], G.faces(FLOW_MARK))[0][1]
    assert np.ptp(V[:, 2]) == pytest.approx(width)
    for cyc, f in zip(G.faces(FLOW_CAPS), caps["FUV"]):
        u, v = np.asarray(f).T
        assert np.ptp(u) <= 1 / 16 + 1e-9                      # no quad spans the seam
        dy, dv = np.subtract.outer(V[cyc, 1], V[cyc, 1]), np.subtract.outer(v, v)
        assert (dy * dv >= -1e-12).all()                     # v rises with y
