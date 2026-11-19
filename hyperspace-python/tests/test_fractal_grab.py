"""Plan 64, part 2: what a grab holds, outside a fractal and inside it; and
plan 64's saved dive (row 889).

The app's own steps, once a frame, in its order: `app._space` (in or out),
`app._reroot`, the world's step, `app._fly` (the flight folded into the
view). What is drawn is read as the renderer composes it: the walk's points
through `geometry.model_matrix` with `shapeframe.drawn_offset`."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace import app, fractal, geometry, grip, shapeframe
from hyperspace import world as W
from hyperspace.view import ViewState

EVERY = pytest.mark.parametrize("name", list(fractal.FRACTALS))
WD, HT = 960, 540

OFFSETS = {
    "none": W.Pose(),
    "moved": W.Pose.turn3(W.qexp([0.0, 0.0, 0.0]), (0.3, -0.1, 0.0)),
    "turned": W.Pose.turn3(W.qexp([0.3, 0.9, -0.2])),
    "turned and moved in depth": W.Pose.turn3(W.qexp([0.2, 0.5, -0.3]), (0.2, -0.1, 0.3)),
}


def _host(name: str, pose=None, **kw) -> SimpleNamespace:
    s = ViewState(shape=geometry.shape_index(name), yaw=0.4, pitch=0.25, pan=[0.04, -0.03])
    s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
    for k, v in kw.items():
        setattr(s, k, v)
    wd = W.World.default()
    if pose is not None:
        wd.objects["shape"].offset = pose
    wd.box = (2.9, 1.65, 1.0)                     # a 16:9 output through the default eye
    wd.home("shape", W.shape_home(s.zoom, s.pan))
    return SimpleNamespace(view=s, world=wd)


def _drawn_off(h):
    obj = h.world.objects["shape"]
    return shapeframe.drawn_offset(h.view, h.world.offset_matrix("shape"), obj.bounded)


def _drawn(h, x_top) -> np.ndarray:
    """Where points of the shape (its top frame) are drawn now."""
    s = h.view
    spec = fractal.spec_of(s.shape)
    r = spec.ratio
    x = np.array(x_top, dtype=np.float64)
    for k in s.dive.path:
        x = (x - (1.0 - r) * spec.centres[k]) / r
    off = _drawn_off(h)
    P, _, _, _ = fractal.walk(spec, s, WD, HT, off).place(x)
    m = geometry.model_matrix(s.zoom, s.pan, off)
    return P @ m[:3, :3].T + m[:3, 3]


def _frame(h) -> None:
    """The app's fractal steps of one frame, the world's step left out (no
    physics: nothing moves the offset but a crossing)."""
    app._space(h, None)
    app._reroot(h, None)
    if h.world.objects["shape"].bounded:
        h.world.home("shape", W.shape_home(h.view.zoom, h.view.pan))
    app._fly(h, None)


def _points(seed=3):
    rng = np.random.default_rng(seed)
    return np.c_[rng.uniform(-0.4, 0.4, (5, 3)), np.zeros(5)]


# ---- in, down and back out: nothing jumps

@EVERY
@pytest.mark.parametrize("pose", list(OFFSETS))
def test_nothing_jumps_going_in_down_and_out(name, pose):
    """Zoomed in from the whole shape, many levels down, and all the way back
    out, the app's steps each frame: across each crossing (object to space and
    back) and each re-root, every point is drawn where it was. The offset is
    the grip's (moved, turned); 4D fractals alike. (Out of the last cell and
    still zooming out, the shape eases back to the middle of the screen on
    purpose, `fractal.step`: those frames move the picture and are left out.)"""
    h = _host(name, OFFSETS[pose])
    X = _points()
    crossings = reroots = 0
    for f in [1.12] * 45 + [1 / 1.12] * 45:
        h.view.zoom *= f
        if h.world.objects["shape"].bounded:
            h.world.home("shape", W.shape_home(h.view.zoom, h.view.pan))
        before = _drawn(h, X)
        inside, path = h.view.dive.inside, list(h.view.dive.path)
        last = h.view.dive.last
        _frame(h)
        crossings += h.view.dive.inside != inside
        reroots += h.view.dive.path != path
        if not h.view.dive.path and h.view.zoom < last and last > fractal.Z_HOME:
            continue                                    # the ease home
        after = _drawn(h, X)
        scale = max(1.0, float(np.abs(before).max()))
        assert np.allclose(after, before, atol=1e-9 * scale), np.abs(after - before).max()
    assert crossings >= 2 and reroots >= 4


@EVERY
def test_an_object_is_never_rerooted(name):
    """The invariant the design rests on: whenever the view has gone into a
    cell, it is inside and the world's shape is the space."""
    h = _host(name, OFFSETS["turned and moved in depth"])
    seen = False
    for f in [1.15] * 40 + [1 / 1.15] * 40:
        h.view.zoom *= f
        _frame(h)
        if h.view.dive.path:
            seen = True
            assert h.view.dive.inside and not h.world.objects["shape"].bounded
    assert seen
    assert not h.view.dive.inside and h.world.objects["shape"].bounded


def test_the_shape_goes_inside_once_it_no_longer_fits_the_box():
    """Inside once the shape's reach passes the box's room; out again only
    under `FIT_OUT` of it — a zoom riding the edge doesn't flip it."""
    h = _host("Menger sponge")
    s = h.view
    zooms = []
    for z in np.linspace(1.0, 2.0, 41):
        s.zoom = float(z)
        _frame(h)
        zooms.append((float(z), s.dive.inside))
    went = next(z for z, inside in zooms if inside)
    assert 1.4 < went < 1.8                         # the box's 1.65 across the shorter side
    s.zoom = went * 0.97                            # just under: still inside
    _frame(h)
    assert s.dive.inside
    s.zoom = went * 0.85
    _frame(h)
    assert not s.dive.inside


# ---- inside: the fist flies the space

def test_inside_the_flight_turns_and_moves_the_space():
    """Inside a 3D fractal the world's flight pose is folded into the view:
    what is drawn moves as the flight did — turned about the middle of the
    screen, moved in world units."""
    h = _host("Sierpinski tetrahedron", OFFSETS["turned"], zoom=3.0)
    _frame(h)
    assert h.view.dive.inside
    X = _points()
    before = _drawn(h, X)
    R = W.Pose.turn3(W.qexp([0.1, -0.2, 0.15]), (0.2, -0.1, 0.05))
    h.world.objects["shape"].offset = R
    app._fly(h, None)
    after = _drawn(h, X)
    m = R.model3()
    assert np.allclose(after, before @ m[:3, :3].T + m[:3, 3], atol=1e-9)


def test_inside_a_4d_fractal_the_flight_travels_through_its_space():
    """Inside a 4D fractal a move goes before the 4D divide (the owner,
    2026-11-19: dragging inside travels through the fractal's 4D space): the
    point at the middle of the screen moves with the hand, a point nearer
    or farther along w by more or less."""
    h = _host("Sierpinski 5-cell", zoom=3.0)
    _frame(h)
    assert h.view.dive.inside
    d0 = (h.view.dive.z, h.view.pan[0])
    h.world.objects["shape"].offset = W.Pose.turn3(W.qexp([0.0, 0.0, 0.0]), (0.2, 0.0, 0.1))
    app._fly(h, None)
    assert h.view.pan[0] == pytest.approx(d0[1] + 0.2)
    assert h.view.dive.z == pytest.approx(d0[0] + 0.1)


def test_a_flight_inside_is_turned_about_where_the_room_put_the_shape():
    """The room placement the shape brought in turns with the flight, so a
    turn of the space is rigid about the middle of the screen."""
    h = _host("Menger sponge", OFFSETS["turned and moved in depth"], zoom=2.5)
    _frame(h)
    assert h.view.dive.inside and h.view.dive.shift.any()
    X = _points()
    before = _drawn(h, X)
    R = W.Pose.turn3(W.qexp([0.0, 0.4, 0.0]))
    h.world.objects["shape"].offset = R
    app._fly(h, None)
    assert np.allclose(_drawn(h, X), before @ R.model3()[:3, :3].T, atol=1e-9)


# ---- the crossing keeps the hold and the motion

def _field(world, oid, y):
    """The velocity of drawn points y under the body's motion: offset in the
    home's frame (object) or the world's (space)."""
    obj, b = world.objects[oid], world.bodies[oid]
    w = b.spin_l
    if obj.bounded:
        c = obj.home.apply(obj.offset.position)[:3]
        return np.cross(w, y - c) + obj.home.scale * b.velocity[:3]
    return np.cross(w, y - obj.offset.position[:3]) + b.velocity[:3]


def test_a_crossing_keeps_the_body_moving_as_it_was():
    """In and out again, a coasting body's drawn velocity field is what it
    was: the same rigid motion, taken about another point."""
    h = _host("Sierpinski tetrahedron", OFFSETS["turned and moved in depth"])
    b = h.world.body("shape", W.Body(boxed=True))
    b.velocity = np.array([0.3, -0.1, 0.05, 0.0])
    b.spin3([0.2, -0.4, 0.1])
    y = np.array([[0.4, 0.1, -0.2], [-1.0, 0.7, 0.3]])
    want = _field(h.world, "shape", y)
    h.view.zoom = 2.5
    h.world.home("shape", W.shape_home(h.view.zoom, h.view.pan))
    want = _field(h.world, "shape", y)
    _frame(h)
    assert h.view.dive.inside and not b.boxed and np.allclose(b.inertia, np.eye(3))
    assert np.allclose(_field(h.world, "shape", y), want)
    h.view.zoom = 1.0
    h.view.dive.last = 1.0              # (no ease home this frame: the crossing alone)
    _frame(h)
    assert not h.view.dive.inside
    assert np.allclose(_field(h.world, "shape", y), want)


def test_a_fist_closed_across_the_crossing_keeps_its_hold():
    """A joint holding the shape is taken again as the shape crosses: the
    hand's target is the pose as now written, so nothing snaps."""
    h = _host("Menger sponge", OFFSETS["turned"])
    hand = h.world.objects["hand.right"]
    hand.home = W.Pose.turn3(W.qexp([0.1, 0.2, 0.0]), (0.5, -0.2, 0.3))
    hand.present = True
    j = h.world.joint("shape", W.Joint("hand.right", "hand.left"))
    j.rel = hand.home.inverse().compose(h.world.objects["shape"].pose)
    h.view.zoom = 2.5
    h.world.home("shape", W.shape_home(h.view.zoom, h.view.pan))
    j.rel = hand.home.inverse().compose(h.world.objects["shape"].pose)
    _frame(h)
    assert h.view.dive.inside
    target = hand.home.compose(j.rel)
    pose = h.world.objects["shape"].pose
    assert np.allclose(target.position, pose.position) and np.allclose(
        np.abs(target.ql @ pose.ql), 1.0)


def test_inside_the_grip_keeps_no_box_and_no_shaped_inertia():
    """Inside, the space: the grip neither boxes it nor shapes its inertia,
    whatever its params say; outside both act as plan 60 has them."""
    h = _host("Menger sponge")
    state = grip.GripState(on=True, inertia=True)
    grip.apply(h.world, state, lambda a: True)
    b, j = h.world.bodies["shape"], h.world.joints["shape"]
    assert b.boxed and j.inertia and j.shaping
    h.view.zoom = 2.5
    _frame(h)
    grip.apply(h.world, state, lambda a: True)
    assert not b.boxed and not j.inertia and not j.shaping


def test_reset_view_inside_brings_the_space_home():
    h = _host("Sierpinski tetrahedron", OFFSETS["turned"], zoom=3.0)
    _frame(h)
    assert h.view.dive.inside
    h.view.dive.reset()
    h.view.zoom, h.view.pan = 1.0, [0.0, 0.0]
    _frame(h)
    obj = h.world.objects["shape"]
    assert obj.bounded and obj.offset.is_identity() and not h.view.dive.inside


def test_another_shape_leaves_the_space():
    h = _host("Sierpinski tetrahedron", zoom=3.0)
    _frame(h)
    assert h.view.dive.inside
    h.view.shape = 3
    _frame(h)
    assert h.world.objects["shape"].bounded and not h.view.dive.inside


# ---- the saved dive (row 889)

def _rig(tmp_path):
    from tests.test_loadable import boot
    return boot(tmp_path)


def _dive_somewhere(rig, name="Sierpinski tetrahedron"):
    reg, view = rig.reg, rig.view
    reg["view.shape"].set(geometry.shape_index(name))
    view.dive.reset()
    view.zoom = 1.3
    for _ in range(50):
        view.zoom *= 1.12
        app._space(SimpleNamespace(view=view, world=None), None)
        fractal.step(view, reg, shapeframe.drawn_offset(view))
    view.dive.turn = W.rot3(W.qexp([0.1, 0.3, -0.2]))
    view.dive.shift = np.array([0.1, -0.05, 0.2])
    assert view.dive.inside and len(view.dive.path) >= 4


def test_a_dive_round_trips_through_a_loadable_patch(tmp_path):
    """Saved inside, a loadable patch keeps the dive (`dive`) and a load puts
    the view back where it was: path, depth, turn, room placement."""
    rig = _rig(tmp_path)
    _dive_somewhere(rig)
    d = rig.view.dive
    kept = (list(d.path), d.z, d.w, d.turn.copy(), d.shift.copy())
    zoom, pan = rig.view.zoom, list(rig.view.pan)
    path = rig.loaded_patch.save_as("Deep")
    doc = json.loads(path.read_text())
    assert doc["dive"]["shape"] == "Sierpinski tetrahedron" and doc["dive"]["path"] == kept[0]
    rig.reg["camera.reset"].fire()
    assert not rig.view.dive.inside
    rig.loaded_patch.load("Deep")
    d = rig.view.dive
    assert d.inside and d.path == kept[0] and (d.z, d.w) == kept[1:3]
    assert np.allclose(d.turn, kept[3]) and np.allclose(d.shift, kept[4])
    assert rig.view.zoom == pytest.approx(zoom) and rig.view.pan == pytest.approx(pan)


def test_a_loadable_patch_from_before_starts_at_the_top(tmp_path):
    """A file with no `dive` (every file written before plan 64, opened end
    to end): the load leaves the view at the top of its fractal, whatever
    dive it was in."""
    from tests.test_loadable import put
    rig = _rig(tmp_path)
    _dive_somewhere(rig)
    put(rig.home, "Old", values={"view.shape": geometry.shape_index("Sierpinski tetrahedron"),
                                 "camera.zoom": 1.2})
    rig.loaded_patch.load("Old")
    d = rig.view.dive
    assert not d.inside and d.path == [] and np.allclose(d.turn, np.eye(3))


def test_a_loadable_patch_not_inside_writes_no_dive(tmp_path):
    rig = _rig(tmp_path)
    rig.reg["view.shape"].set(geometry.shape_index("Menger sponge"))
    doc = json.loads(rig.loaded_patch.save_as("Top").read_text())
    assert "dive" not in doc


@pytest.mark.parametrize("bad", [
    {"shape": "Menger sponge", "path": [0, 1]},                       # another shape's
    {"shape": "Sierpinski tetrahedron", "path": [0, 9]},              # no cell 9
    {"shape": "Sierpinski tetrahedron", "path": [0] * 5000},          # too long
    {"shape": "Sierpinski tetrahedron", "path": [0], "z": "nan"},     # not finite
    {"shape": "Sierpinski tetrahedron", "path": [0], "turn": [2, 0, 0, 0, 1, 0, 0, 0, 1]},
    "not a dive",
])
def test_a_dive_that_cannot_land_is_refused_whole_and_said(tmp_path, bad):
    from tests.test_loadable import put
    rig = _rig(tmp_path)
    put(rig.home, "Bad", values={"view.shape": geometry.shape_index("Sierpinski tetrahedron")},
        dive=bad)
    rig.loaded_patch.load("Bad")
    d = rig.view.dive
    assert not d.inside and d.path == []
    assert any("dive" in n for n in rig.loaded_patch.notes)


def test_each_fractals_cells_keep_their_order():
    """A saved dive's path indexes each fractal's `centres`: their order is a
    file format now (row 889), held here whole."""
    import hashlib

    got = {name: hashlib.sha256(np.round(f.centres, 6).astype("<f8").tobytes()).hexdigest()[:16]
           for name, f in fractal.FRACTALS.items()}
    assert got == CENTRES


CENTRES = {'4D Cantor dust': 'bcb46c9a5ad8230b',
 '4D Vicsek cross': 'dc7831f4db64e0b7',
 'Cantor dust': '331405ee337e3e3f',
 'Icosahedron flake': 'd9ec2cedc0408a22',
 'Menger sponge': '06277fa9731fb7d8',
 'Octahedron flake': '4cfe61fdeaa25614',
 'Sierpinski 5-cell': 'a142473a3c0bd242',
 'Sierpinski tetrahedron': '360aa265d3eff4d4',
 'Vicsek cross': '2f07b110eb4cf2e3'}
