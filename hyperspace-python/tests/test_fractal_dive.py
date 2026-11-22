"""Plan 81: an endless, centred fractal dive.

- the zoom and the turn are taken about the middle of the screen
  (`fractal.centre`), and a re-root still moves nothing;
- a dive settles onto the middle of the cell it is in (`SETTLE_ON = "cell"`,
  the default: the picture stays full and centred), or holds one point of
  the shape under the middle for good (`"point"`, the letter of D4);
- a dive rate (`view.frac_dive`, levels a second, signed) dives for as long
  as it is set and climbs back out to the whole shape;
- 3D and 4D fractals alike; a grabbed view still re-roots without a jump.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace import app, fractal, geometry, shapeframe
from hyperspace import world as W
from hyperspace.view import ViewState

EVERY = pytest.mark.parametrize("name", list(fractal.FRACTALS))
BOTH = pytest.mark.parametrize("name", ["Menger sponge", "Sierpinski 5-cell"])
WD, HT = 960, 540


def _view(name: str, spin: bool = False, **kw) -> ViewState:
    s = ViewState(shape=geometry.shape_index(name), yaw=0.45, pitch=0.3, zoom=1.3)
    s.ang = [0.3, 0.7, 1.1, 0.2, 0.0, 0.1]
    s.playing = spin
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def _p(s) -> np.ndarray:
    return np.array([s.pan[0], -s.pan[1], s.dive.z, s.dive.w])


def _rooted(spec, x: np.ndarray, was: list[int], now: list[int]) -> np.ndarray:
    """Points `x` in the frame of the cell `was` roots, in the frame of `now`'s."""
    r = spec.ratio
    n = 0
    while n < min(len(was), len(now)) and was[n] == now[n]:
        n += 1
    for k in reversed(was[n:]):                      # up to the common ancestor
        x = r * x + (1.0 - r) * spec.centres[k]
    for k in now[n:]:                                # and down
        x = (x - (1.0 - r) * spec.centres[k]) / r
    return x


def _q(s, x: np.ndarray) -> np.ndarray:
    """Where the view puts points `x` of its rooted cell (4D, before the
    divide: everything after it is a function of this)."""
    return max(float(s.zoom), 1e-3) * (x @ fractal.turn(s)) + _p(s)


def _under_middle(s) -> np.ndarray:
    return ((-_p(s)) / max(float(s.zoom), 1e-3)) @ fractal.turn(s).T


def _frame(s, dt: float) -> None:
    """A frame as the app runs it, with no world: the turn, the crossing, the
    dive and the re-root."""
    s.integrate(dt)
    app._space(SimpleNamespace(view=s, world=None), None)
    s.reroot(None, None, dt)


# ---- a long dive at a fixed rate

@pytest.fixture
def point(monkeypatch):
    """A dive that holds one point under the middle (row 1012's alternative)."""
    monkeypatch.setattr(fractal, "SETTLE_ON", "point")


def _long_dive(name: str, levels: int, rate: float = 2.0, dt: float = 0.1,
               spin: bool = False, settle_after: int = 10) -> ViewState:
    """A dive at `rate`: no re-root moves a point, the zoom stays in its band;
    holding a point ("point"), once settled it never leaves the middle; on
    the cell's middle ("cell"), that middle stays near the screen's."""
    held_point = fractal.SETTLE_ON == "point"
    s = _view(name, spin=spin, frac_dive=rate)
    spec = fractal.spec_of(s.shape)
    held = None                                      # the point under the middle, once settled
    worst_jump = worst_drift = 0.0
    for _ in range(int(levels / (rate * dt)) + 1):
        s.integrate(dt)
        app._space(SimpleNamespace(view=s, world=None), None)
        # the dive and the zoom about the middle
        fractal.centre(s, None, None, dt)
        # the re-root on its own: every point where it was
        path = list(s.dive.path)
        x = _under_middle(s) + np.array([[0.0, 0, 0, 0], [0.2, -0.1, 0.05, 0],
                                         [-0.15, 0.1, 0.1, 0.03]])
        before = _q(s, x)
        fractal.step(s, None, None, 0.0)
        after = _q(s, _rooted(spec, x, path, s.dive.path))
        worst_jump = max(worst_jump, float(np.abs(after - before).max()) / s.zoom)
        assert np.all(np.isfinite(after)) and s.zoom < fractal.Z_IN
        if s.dive.path:
            assert s.zoom >= fractal.Z_IN * spec.ratio * fractal.Z_SLACK * 0.999
        # settled: the point under the middle stays there, or the rooted
        # cell's middle near the screen's
        if len(s.dive.path) >= settle_after and not held_point:
            # (steered in over each level: by its end, within under half the
            # cell's reach of the screen's middle)
            off_middle = np.linalg.norm(_p(s)[:3]) / s.zoom
            assert off_middle < fractal.OUTSIDE
            if s.zoom > 0.8 * fractal.Z_IN:
                assert off_middle < 0.45, off_middle
        if len(s.dive.path) >= settle_after and held_point:
            if held is not None:
                hx, hp = held
                worst_drift = max(worst_drift, float(np.abs(
                    _q(s, _rooted(spec, hx, hp, s.dive.path))).max()) / s.zoom)
            held = (_under_middle(s), list(s.dive.path))
    assert worst_jump < 1e-9, worst_jump
    # (a float holds a point on the fractal only so far, so the dive keeps
    # nudging it back on: well under a pixel a frame, 1e-4 of the zoom being
    # about a fiftieth of one at 1080 lines)
    assert worst_drift < 1e-4, worst_drift
    return s


@EVERY
def test_a_dive_stays_centred_and_never_jumps(name):
    """Sixty levels in at a fixed rate, every fractal, 3D and 4D: no re-root
    moves a point, the zoom stays in its band, and the cell the view is in
    stays in the middle of the screen."""
    s = _long_dive(name, 60)
    assert len(s.dive.path) >= 58


@EVERY
def test_a_dive_holding_a_point_never_lets_it_leave_the_middle(name, point):
    """The same, holding a point ("point"): once settled onto the fractal, the
    point under the middle of the screen never leaves it."""
    _long_dive(name, 60)


@BOTH
@pytest.mark.parametrize("settle", ["cell", "point"])
def test_a_long_dive_of_hundreds_of_levels(name, settle, monkeypatch):
    """Three hundred levels: the same, and the numbers stay small (float64
    never runs out: the view is a rooted cell's, whatever the depth)."""
    monkeypatch.setattr(fractal, "SETTLE_ON", settle)
    s = _long_dive(name, 300)
    assert len(s.dive.path) >= 298
    assert max(abs(s.pan[0]), abs(s.pan[1]), abs(s.dive.z), abs(s.dive.w)) < 11.0


@BOTH
@pytest.mark.parametrize("settle", ["cell", "point"])
def test_a_spinning_dive_turns_about_the_middle(name, settle, monkeypatch):
    """With the shape spinning: the turn is taken about the middle of the
    screen, not the rooted cell's (a held point stays held)."""
    monkeypatch.setattr(fractal, "SETTLE_ON", settle)
    _long_dive(name, 30, spin=True)


def test_the_dive_runs_at_its_rate():
    """Levels a second: one level is × 1 / ratio on the zoom."""
    s = _view("Menger sponge", frac_dive=1.5)
    for _ in range(100):
        _frame(s, 0.1)
    assert abs(len(s.dive.path) - 15) <= 1


@BOTH
def test_a_negative_rate_climbs_back_out_to_the_whole_shape(name):
    """Dived in, then the rate turned down: out of every cell, the shape eased
    home to the middle at zoom 1, and held there however long it stays down."""
    s = _view(name, frac_dive=2.0)
    for _ in range(150):
        _frame(s, 0.1)
    assert len(s.dive.path) >= 25
    s.frac_dive = -2.0
    for _ in range(250):
        _frame(s, 0.1)
    assert not s.dive.path and not s.dive.inside
    assert s.zoom == pytest.approx(fractal.Z_HOME)
    assert np.allclose(_p(s), 0.0, atol=1e-9)
    zoom = s.zoom
    for _ in range(30):
        _frame(s, 0.1)
    assert s.zoom == zoom


def test_a_rate_of_zero_holds_still():
    s = _view("Menger sponge", frac_dive=1.0)
    for _ in range(40):
        _frame(s, 0.1)
    s.frac_dive = 0.0
    zoom, pan, path = s.zoom, list(s.pan), list(s.dive.path)
    for _ in range(20):
        _frame(s, 0.1)
    assert s.zoom == pytest.approx(zoom, rel=1e-12) and s.dive.path == path
    assert s.pan == pytest.approx(pan, abs=1e-12)


def test_a_pan_made_inside_is_kept():
    """Inside, a pan is a move of its own: the zoom about the middle keeps it."""
    s = _view("Menger sponge", frac_dive=1.0)
    for _ in range(40):
        _frame(s, 0.1)
    s.frac_dive = 0.0
    _frame(s, 0.1)
    s.pan[0] += 0.1
    pan = list(s.pan)
    _frame(s, 0.1)
    assert s.pan == pytest.approx(pan, abs=1e-12)


def test_a_zoom_inside_is_about_the_middle(point):
    """A plain zoom (camera.zoom moved, no rate) inside is about the middle
    of the screen: the point there stays (plan 81's fix of the drift)."""
    s = _view("Sierpinski tetrahedron", frac_dive=1.0)
    spec = fractal.spec_of(s.shape)
    for _ in range(150):                             # (settled onto the fractal)
        _frame(s, 0.1)
    s.frac_dive = 0.0
    _frame(s, 0.1)
    x, path = _under_middle(s), list(s.dive.path)
    for _ in range(40):
        s.zoom *= 1.07
        _frame(s, 1 / 60)
    assert len(s.dive.path) > len(path)
    # (the settle onto the fractal moves it by less than a pixel: it is on it)
    assert np.abs(_q(s, _rooted(spec, x, path, s.dive.path))).max() / s.zoom < 1e-4


def test_an_endless_dive_keeps_its_path_to_the_longest_a_file_takes():
    """Past `MAX_PATH` levels the outermost go (never drawn, `ABOVE`): the
    picture is the same and a save of it still loads."""
    s = _view("Menger sponge", frac_dive=1.0)
    for _ in range(40):
        _frame(s, 0.1)
    s.dive.path[:0] = [0] * (fractal.MAX_PATH - len(s.dive.path))
    spec = fractal.spec_of(s.shape)
    g0, _, _, _ = fractal.frame(spec, s, WD, HT)
    for _ in range(20):
        _frame(s, 0.1)
    assert len(s.dive.path) == fractal.MAX_PATH
    g1, _, _, _ = fractal.frame(spec, s, WD, HT)
    assert g1["m"] > 100 and g0["m"] > 100


@BOTH
def test_the_cpu_and_the_gpu_paths_draw_deep_in_a_dive(name):
    """Deep in a dive both paths have cells to draw, every number finite."""
    s = _view(name, frac_dive=2.0)
    for _ in range(400):
        _frame(s, 0.1)
    spec = fractal.spec_of(s.shape)
    g, P, _, pd = fractal.frame(spec, s, WD, HT)
    assert g["m"] > 100 and np.isfinite(P).all() and np.isfinite(pd).all()
    rows = fractal.instances(fractal.walk(spec, s, WD, HT))
    assert len(rows["lines"]) > 10 and np.isfinite(rows["lines"]).all()


@pytest.mark.parametrize("settle", ["cell", "point"])
def test_either_settle_dives_without_a_jump(settle, monkeypatch):
    """Either settle (row 1012) re-roots without a jump."""
    monkeypatch.setattr(fractal, "SETTLE_ON", settle)
    s = _view("Menger sponge", frac_dive=2.0)
    spec = fractal.spec_of(s.shape)
    for _ in range(100):
        s.integrate(0.1)
        app._space(SimpleNamespace(view=s, world=None), None)
        fractal.centre(s, None, None, 0.1)
        path, x = list(s.dive.path), _under_middle(s)
        before = _q(s, x)
        fractal.step(s)
        assert np.allclose(_q(s, _rooted(spec, x, path, s.dive.path)), before, atol=1e-9)
    assert len(s.dive.path) >= 19


# ---- a grabbed view, the params, a loadable patch

def _host(name: str, pose) -> SimpleNamespace:
    s = _view(name, pan=[0.04, -0.03])
    wd = W.World.default()
    wd.objects["shape"].offset = pose
    wd.box = (2.9, 1.65, 1.0)
    wd.home("shape", W.shape_home(s.zoom, s.pan))
    return SimpleNamespace(view=s, world=wd)


@pytest.mark.parametrize("name", ["Menger sponge", "Sierpinski 5-cell", "Octahedron flake"])
def test_a_grabbed_view_dives_and_reroots_without_a_jump(name):
    """A moved and turned shape (the grip's offset, plan 59) dived into by the
    rate: across its crossing into the space and every re-root after, every
    point is drawn where it was."""
    from tests.test_fractal_grab import _drawn, _drawn_off, _points
    h = _host(name, W.Pose.turn3(W.qexp([0.2, 0.5, -0.3]), (0.2, -0.1, 0.3)))
    h.view.frac_dive = 1.5
    X = _points()
    reroots = 0
    for _ in range(120):
        app._space(h, None)
        fractal.centre(h.view, None, _drawn_off(h), 0.1)
        if h.world.objects["shape"].bounded:
            h.world.home("shape", W.shape_home(h.view.zoom, h.view.pan))
        before, path = _drawn(h, X), list(h.view.dive.path)
        app._reroot(h, None)
        app._fly(h, None)
        reroots += h.view.dive.path != path
        after = _drawn(h, X)
        scale = max(1.0, float(np.abs(before).max()))
        assert np.allclose(after, before, atol=1e-9 * scale), np.abs(after - before).max()
    assert h.view.dive.inside and reroots >= 10


def test_the_dive_rate_is_a_param_a_route_drives():
    """`view.frac_dive` is the look's own, routable: a source on it dives, and
    camera.zoom's base follows each re-root."""
    from tests.test_fractal import _reg
    s = _view("Menger sponge")
    reg = _reg(s)
    p = reg["view.frac_dive"]
    assert p.persist and p.modulatable and (p.lo, p.hi) == (-2.0, 2.0)
    for _ in range(60):
        p.modulate(0.25)                              # a quarter up the range: +1 level/s
        reg.apply()
        s.integrate(0.1)
        app._space(SimpleNamespace(view=s, world=None), None)
        s.reroot(reg, None, 0.1)
        assert reg["camera.zoom"].base == pytest.approx(s.zoom)
    assert s.frac_dive == pytest.approx(1.0) and abs(len(s.dive.path) - 6) <= 1


def test_the_dive_rate_saves_in_a_loadable_patch(tmp_path):
    """Under the FRACTAL section's key, with Detail, Reach and Near (row 902):
    written only for a fractal, so no other look's file changes; a key from
    before plan 81 (no "dive") loads it at 0."""
    from tests.test_fractal_grab import _rig
    from tests.test_loadable import put
    rig = _rig(tmp_path)
    rig.reg["view.shape"].set(geometry.shape_index("Menger sponge"))
    rig.reg["view.frac_dive"].set(0.75)
    path = rig.loaded_patch.save_as("Endless")
    doc = json.loads(path.read_text())
    assert doc["fractal"]["dive"] == 0.75 and "view.frac_dive" not in doc["values"]
    rig.reg["view.frac_dive"].set(0.0)
    rig.loaded_patch.load("Endless")
    assert rig.view.frac_dive == 0.75
    put(rig.home, "Before", values={"view.shape": geometry.shape_index("Menger sponge")},
        fractal={"detail": 1.0, "far": 0.0, "near": 0.0})
    rig.loaded_patch.load("Before")
    assert rig.view.frac_dive == 0.0


def test_another_shape_ignores_the_rate():
    s = ViewState(shape=geometry.shape_index("Tesseract"), zoom=1.3, frac_dive=2.0)
    for _ in range(20):
        _frame(s, 0.1)
    assert s.zoom == 1.3


def test_a_drawn_offset_keeps_the_middle_where_it_is_drawn(point):
    """With the room placement a crossing left (`Dive.shift`), the middle the
    zoom is taken about is the point drawn at the middle of the screen."""
    h = _host("Menger sponge", W.Pose.turn3(W.qexp([0.0, 0.0, 0.0]), (0.3, -0.1, 0.0)))
    h.view.frac_dive = 1.0
    for _ in range(200):                             # (settled onto the fractal)
        app._space(h, None)
        app._reroot(h, None, 0.1)
    assert h.view.dive.inside
    off = shapeframe.drawn_offset(h.view, h.world.offset_matrix("shape"),
                                  h.world.objects["shape"].bounded)
    s = h.view
    mid = fractal._middle(s, off, s.zoom, _p(s))
    x = ((mid - _p(s)) / s.zoom) @ fractal.turn(s).T
    path = list(s.dive.path)
    h.view.frac_dive = 0.0
    for _ in range(20):
        s.zoom *= 1.05
        app._space(h, None)
        app._reroot(h, None, 0.1)
    spec = fractal.spec_of(s.shape)
    off = shapeframe.drawn_offset(h.view, h.world.offset_matrix("shape"),
                                  h.world.objects["shape"].bounded)
    mid = fractal._middle(s, off, s.zoom, _p(s))
    got = _q(s, _rooted(spec, x, path, s.dive.path))
    assert np.abs(got - mid).max() / s.zoom < 1e-4
