"""An endless, centred fractal dive.

- the zoom and the turn are taken about the middle of the screen
  (`fractal.centre`), and a re-root still moves nothing;
- a dive settles onto the middle of the cell it is in (`SETTLE_ON = "cell"`,
  the default: the picture stays full and centred), or holds one point of
  the shape under the middle for good (`"point"`);
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
    """A dive that holds one point under the middle (the alternative settle)."""
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
    of the screen: the point there stays (no drift)."""
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
    """Either settle re-roots without a jump."""
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
    """A moved and turned shape (the grip's offset) dived into by the
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
    """Under the FRACTAL section's key, with Detail, Reach and Near:
    written only for a fractal, so no other look's file changes; a key with
    no "dive" loads it at 0."""
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


# ---- a pan, a camera restore and the deck's undo during a dive

def test_a_pan_made_during_a_dive_stays_made():
    """Diving, a pan (or a flight) is kept as the performer's framing
    (`Dive.frame`): the settle steers each new cell's middle to where the pan
    put it, not back to the screen's middle — the dive never stops."""
    a, b = _view("Menger sponge", frac_dive=1.0), _view("Menger sponge", frac_dive=1.0)
    for _ in range(60):
        _frame(a, 0.1)
        _frame(b, 0.1)
    a.pan[0] += 0.1                                  # one nudge of the stick, then let go
    for _ in range(100):                             # ten levels on, still diving
        _frame(a, 0.1)
        _frame(b, 0.1)
    assert a.dive.frame == pytest.approx([0.1, 0.0, 0.0, 0.0])
    if a.dive.path == b.dive.path:                   # the same cells: the pan is all that differs
        # (kept, not damped away: the zoom about the middle scales it a little
        # over the level, as it does the settle's own lag)
        d = _p(a)[:2] - _p(b)[:2]
        assert 0.08 < d[0] < 0.3 and abs(d[1]) < 0.01, d
    # and either way the cell's middle ends each level by the framing
    late = []
    for _ in range(100):
        _frame(a, 0.1)
        if a.zoom > 0.8 * fractal.Z_IN:
            late.append(np.linalg.norm(_p(a)[:3] - a.dive.frame[:3]) / a.zoom)
    assert late and max(late) < 0.45


def test_a_camera_an_undo_restores_is_taken_as_it_is():
    """An undo or redo writes zoom and pan back together; the deck's restore
    (`deck._unseen`) has the dive take them as they are on the next step, not
    as a zoom about the middle since the view it last saw."""
    from hyperspace import deck
    s = _view("Menger sponge", frac_dive=1.0)
    for _ in range(35):
        _frame(s, 0.1)
    s.frac_dive = 0.0
    _frame(s, 0.1)
    zoom, pan, path = s.zoom, list(s.pan), list(s.dive.path)
    s.zoom *= 1.05                                   # a gesture, within the cell
    _frame(s, 1 / 60)
    assert s.dive.path == path and s.pan != pan
    s.zoom, s.pan = zoom, list(pan)                  # the undo's restore
    deck._unseen(s)
    _frame(s, 1 / 60)
    assert (s.zoom, s.pan, s.dive.path) == (zoom, pan, path)


def test_the_deck_undo_drops_the_dive_reference_on_a_restore_from_another_dive(tmp_path):
    """The real deck's undo (`Deck.build`, `deck.DiveFrame`): a restore that
    writes the camera from another dive's life has the dive take it as it is
    (`_unseen`); within one, it keeps the zoom it saw, so a restored zoom is
    taken about the middle of the screen, as the edit it undoes was."""
    from hyperspace import deck
    from tests.test_undo import boot
    r = boot(tmp_path / "home")
    beside = r.undo.beside
    assert isinstance(beside, deck.DiveFrame)
    d = r.view.dive
    d.seen = (1.0, np.zeros(4), np.eye(4))
    beside.put({"frame": (0.0,) * 4, "lives": d.lives}, kept=True)
    assert d.seen is not None and d.seen[0] == 1.0
    beside.put({"frame": (0.0,) * 4, "lives": d.lives - 1}, kept=False)
    assert d.seen is None


# ---- the framing: off air, saved, and undo

def _diving(name: str = "Menger sponge", frames: int = 60, rate: float = 1.0) -> ViewState:
    s = _view(name, frac_dive=rate)
    for _ in range(frames):
        _frame(s, 0.1)
    assert s.dive.path
    return s


def _turn(R: np.ndarray, u=(0.0, 0.0, 0.0)) -> np.ndarray:
    F = np.eye(4)
    F[:3, :3], F[:3, 3] = R, u
    return F


def test_a_flight_that_only_turns_leaves_no_framing():
    """A grab that only turns the space, the rooted cell off the middle: the
    turn is about the middle of the screen, which a pan is not — the framing
    stays none (it was the cell's offset turned, read as a pan), and the dive
    after it still lands each cell's middle on the screen's."""
    s = _diving()
    s.pan[0], s.pan[1] = s.pan[0] + 0.3, s.pan[1] - 0.2      # the cell well off the middle
    fractal.centre(s, None, None, 0.0)
    s.dive.frame = np.zeros(4)
    fractal.fold_flight(s, None, np.eye(4), epoch=1)            # (the first fold reads the pose)
    R = W.rot3(W.qexp([0.0, 0.0, 0.6]))
    fractal.fold_flight(s, None, _turn(R), epoch=1)
    assert np.allclose(s.dive.frame, 0.0, atol=1e-12), s.dive.frame
    late = []
    for _ in range(100):
        _frame(s, 0.1)
        if s.zoom > 0.8 * fractal.Z_IN:
            late.append(np.linalg.norm(_p(s)[:3]) / s.zoom)
    assert np.allclose(s.dive.frame, 0.0, atol=1e-12)
    assert late and max(late) < 0.45


def test_a_flight_moves_its_framing_rigidly():
    """A turn and a move with a framing already made: the framing's point (the
    cell's middle, at mid + frame) goes where the flight takes it — turned
    about the middle and moved — and w, which a flight does not reach, stays."""
    s = _diving()
    fr = np.array([0.12, -0.05, 0.03, 0.02])
    s.dive.frame = fr.copy()
    fractal.fold_flight(s, None, np.eye(4), epoch=1)
    R, u = W.rot3(W.qexp([0.2, -0.4, 0.3])), np.array([0.05, 0.1, -0.02])
    fractal.fold_flight(s, None, _turn(R, u), epoch=1)
    want = fr.copy()
    want[:3] = R @ fr[:3] + u
    assert np.allclose(s.dive.frame, want, atol=1e-12)


def _off_air(s, dt: float = 0.1) -> None:
    """A frame of a deck off air: no crossing (`app._space`), the re-root only."""
    s.integrate(dt)
    s.reroot(None, None, dt)


def test_an_off_air_climb_out_drops_the_framing():
    """Off air nothing runs `go_outside`, so the step drops the framing once
    the view has climbed out and eased home, as on air: a second dive with no
    pan is centred, not framed by the first dive's pan."""
    s = _view("Menger sponge", frac_dive=2.0)
    for _ in range(80):
        _off_air(s)
    assert s.dive.path and not s.dive.inside
    s.pan[0] += 0.1
    for _ in range(20):
        _off_air(s)
    assert s.dive.frame[0] == pytest.approx(0.1)
    s.frac_dive = -2.0
    for _ in range(250):
        _off_air(s)
    assert not s.dive.path and s.zoom == pytest.approx(fractal.Z_HOME)
    assert not s.dive.frame.any()
    s.frac_dive = 2.0                                # dived again, no pan
    late = []
    for _ in range(150):
        _off_air(s)
        if len(s.dive.path) > 10 and s.zoom > 0.8 * fractal.Z_IN:
            late.append(np.linalg.norm(_p(s)[:3]) / s.zoom)
    assert not s.dive.frame.any()
    assert late and max(late) < 0.45, max(late)


def test_a_climb_on_air_and_off_air_ends_the_same():
    """The same dive, pan and climb on air and off: both end with no framing."""
    a, b = _view("Menger sponge", frac_dive=2.0), _view("Menger sponge", frac_dive=2.0)
    for _ in range(60):
        _frame(a, 0.1)
        _off_air(b)
    a.pan[0] += 0.1
    b.pan[0] += 0.1
    a.frac_dive = b.frac_dive = -2.0
    for _ in range(250):
        _frame(a, 0.1)
        _off_air(b)
    assert not a.dive.frame.any() and not b.dive.frame.any()


def test_a_saved_dive_keeps_its_framing(tmp_path):
    """A loadable patch keeps the framing (`frame`, optional): saved
    mid-dive and loaded, the dive resumes framed — past the first frame,
    which takes the loaded view as it is — and goes on framed."""
    from tests.test_fractal_grab import _rig
    rig = _rig(tmp_path)
    reg, view = rig.reg, rig.view
    reg["view.shape"].set(geometry.shape_index("Menger sponge"))
    view.dive.reset()
    view.zoom = 1.3

    def frame(dt: float = 0.1) -> None:
        reg.apply()
        view.integrate(dt)
        app._space(SimpleNamespace(view=view, world=None), reg)
        view.reroot(reg, None, dt)

    reg["view.frac_dive"].set(1.0)
    for _ in range(60):
        frame()
    reg["camera.pan.x"].set(reg["camera.pan.x"].base + 0.1)
    for _ in range(5):
        frame()
    fr = view.dive.frame.copy()
    assert fr[0] == pytest.approx(0.1)
    doc = json.loads(rig.loaded_patch.save_as("Framed").read_text())
    assert doc["dive"]["frame"] == pytest.approx(list(fr))
    rig.reg["camera.reset"].fire()
    assert not view.dive.frame.any()
    rig.loaded_patch.load("Framed")
    assert np.allclose(view.dive.frame, fr)
    for _ in range(3):                               # past the first frame
        frame()
    assert np.allclose(view.dive.frame, fr)
    late = []
    for _ in range(100):                             # ten levels on, framed still
        frame()
        if view.zoom > 0.8 * fractal.Z_IN:
            late.append(np.linalg.norm(_p(view)[:3] - fr[:3]) / view.zoom)
    assert np.allclose(view.dive.frame, fr)
    assert late and max(late) < 0.45


def test_a_dive_with_no_framing_saves_as_before():
    """No framing: no `frame` key, so a dive saved before reads unchanged."""
    d = fractal.Dive(path=[1, 2], inside=True)
    assert "frame" not in d.to_json("Menger sponge")
    d.frame = np.array([0.1, 0.0, 0.0, 0.0])
    doc = d.to_json("Menger sponge")
    assert doc["frame"] == [0.1, 0.0, 0.0, 0.0]
    e = fractal.Dive()
    assert e.from_json(doc, "Menger sponge") == "" and np.allclose(e.frame, d.frame)
    del doc["frame"]
    assert e.from_json(doc, "Menger sponge") == "" and not e.frame.any()


@pytest.mark.parametrize("bad", [[0.1, 0.0, 0.0], "near", [0.1, "x", 0.0, 0.0],
                                 [0.1, True, 0.0, 0.0], [1e13, 0.0, 0.0, 0.0]])
def test_a_framing_that_cannot_land_refuses_the_dive_whole(bad):
    """As `shift`: a framing that is not four finite numbers refuses the dive."""
    doc = fractal.Dive(path=[1, 2], inside=True).to_json("Menger sponge")
    doc["frame"] = bad
    e = fractal.Dive()
    assert e.from_json(doc, "Menger sponge") and not e.path and not e.frame.any()


# ---- undo while a dive runs (the real deck's undo, `Deck.build`)

def _undo_rig(tmp_path):
    from tests.test_undo import boot, settle
    r = boot(tmp_path / "home")
    r.reg["view.shape"].set(geometry.shape_index("Menger sponge"))
    r.view.dive.reset()
    settle(r)
    return r


def _run(r, n: int) -> None:
    """`n` frames in app.frame's order, the dive's step last."""
    from tests.test_undo import DT, frames
    for _ in range(n):
        frames(r)
        app._space(SimpleNamespace(view=r.view, world=None), r.reg)
        r.view.reroot(r.reg, None, DT)


def test_two_edits_during_a_dive_are_two_steps(tmp_path):
    """A dive at a constant rate writes camera.zoom's base every frame
    (`Param.follow`), which the watcher does not count: two slider
    edits a second apart are two steps, and undoing the second takes back that
    one alone — and does not yank the dive back to where it stood."""
    r = _undo_rig(tmp_path)
    r.reg["view.frac_dive"].set(1.0)
    _run(r, 60)
    n = len(r.undo.stack)
    detail = r.reg["view.frac_detail"]
    d0 = detail.base
    detail.set(d0 + 0.2)
    _run(r, 60)                                      # a second on, still diving
    detail.set(d0 + 0.4)
    _run(r, 60)
    assert len(r.undo.stack) == n + 2, [s.label for s in r.undo.stack]
    assert r.undo.stack[-1].label.startswith("Detail")
    path = list(r.view.dive.path)
    zoom = r.view.zoom
    r.undo.undo()
    assert detail.base == pytest.approx(d0 + 0.2)
    assert r.view.dive.path == path and r.view.zoom == pytest.approx(zoom)
    _run(r, 30)                                      # and the dive goes on from there
    assert len(r.view.dive.path) > len(path)
    r.undo.undo()
    assert detail.base == pytest.approx(d0)


def test_a_running_dive_makes_no_step(tmp_path):
    r = _undo_rig(tmp_path)
    r.reg["view.frac_dive"].set(1.5)
    _run(r, 60)
    n = len(r.undo.stack)
    _run(r, 120)
    assert len(r.view.dive.path) >= 4
    assert len(r.undo.stack) == n and r.undo._open is None


def test_undoing_a_pan_takes_its_framing_back(tmp_path):
    """An undo writes the camera's bases back, and the dive's framing with
    them (`deck.DiveFrame`): an undone pan's framing does not come
    back once the dive resumes; a redo brings it back."""
    r = _undo_rig(tmp_path)
    r.reg["view.frac_dive"].set(1.0)
    _run(r, 60)
    pan = r.reg["camera.pan.x"]
    pan.set(pan.base + 0.1)
    _run(r, 60)
    assert r.view.dive.frame[0] == pytest.approx(0.1)
    assert r.undo.stack[-1].label.startswith("Pan X")
    r.undo.undo()
    _run(r, 60)
    assert not r.view.dive.frame.any(), r.view.dive.frame
    r.undo.redo()
    _run(r, 5)
    assert r.view.dive.frame[0] == pytest.approx(0.1)


def test_an_unrelated_undo_leaves_the_framing(tmp_path):
    """An undo that writes no camera param leaves the framing as it is."""
    r = _undo_rig(tmp_path)
    r.reg["view.frac_dive"].set(1.0)
    _run(r, 60)
    pan = r.reg["camera.pan.x"]
    pan.set(pan.base + 0.1)
    _run(r, 60)
    detail = r.reg["view.frac_detail"]
    detail.set(detail.base + 0.3)
    _run(r, 60)
    r.undo.undo()
    _run(r, 30)
    assert r.view.dive.frame[0] == pytest.approx(0.1)


# ---- undoing a load and a zoom; wheel zoom inside a dive

def _frame_reg(s, reg, dt: float) -> None:
    reg.apply()
    s.integrate(dt)
    app._space(SimpleNamespace(view=s, world=None), reg)
    s.reroot(reg, None, dt)


def test_undoing_a_load_puts_the_camera_back_as_it_was(tmp_path):
    """A load replaces the dive (another life): undoing it puts the camera
    back as it was, not with the loaded dive's motion carried onto it."""
    from tests.test_loadable import put
    from tests.test_undo import settle
    r = _undo_rig(tmp_path)
    r.reg["view.shape"].set(geometry.shape_index("Tesseract"))
    r.reg["camera.zoom"].set(1.0)
    r.reg["camera.pan.x"].set(0.0)
    settle(r)
    zoom, pan = r.reg["camera.zoom"].base, r.reg["camera.pan.x"].base
    put(r.home, "Sponge", values={"view.shape": geometry.shape_index("Menger sponge"),
                                  "camera.zoom": 1.0},
        fractal={"detail": 1.0, "far": 0.0, "near": 0.0, "dive": 1.0})
    r.loaded_patch.load("Sponge")
    _run(r, 180)                                     # three levels in, past re-roots
    assert len(r.view.dive.path) >= 2
    r.undo.undo()
    assert r.reg["view.shape"].base == geometry.shape_index("Tesseract")
    assert r.reg["camera.zoom"].base == pytest.approx(zoom)
    assert r.reg["camera.pan.x"].base == pytest.approx(pan, abs=1e-12)


def test_undoing_a_zoom_in_a_paused_dive_puts_the_cell_back(tmp_path):
    """A zoom edit in a paused dive is taken about the middle (the cell's
    place moves with it); its undo takes the zoom back about the middle too,
    so the cell lands where it was, and a redo where the edit had it."""
    r = _undo_rig(tmp_path)
    r.reg["view.frac_dive"].set(1.0)
    _run(r, 70)
    r.reg["view.frac_dive"].set(0.0)
    _run(r, 60)
    s = r.view
    zoom, p, path = s.zoom, _p(s), list(s.dive.path)
    z = r.reg["camera.zoom"]
    z.set(z.base * 1.05)
    _run(r, 60)
    assert s.dive.path == path and not np.allclose(_p(s), p)
    zoom1, p1 = s.zoom, _p(s)
    r.undo.undo()
    _run(r, 5)
    assert s.dive.path == path
    assert s.zoom == pytest.approx(zoom, rel=1e-9)
    assert np.allclose(_p(s), p, atol=1e-9 * s.zoom), _p(s) - p
    assert not s.dive.frame.any()
    r.undo.redo()
    _run(r, 5)
    assert s.zoom == pytest.approx(zoom1, rel=1e-9)
    assert np.allclose(_p(s), p1, atol=1e-6 * s.zoom), _p(s) - p1


def test_a_wheel_zoom_at_the_middle_inside_a_dive_is_about_the_middle():
    """Inside a dive the step takes a zoom about the middle of the screen; the
    wheel at the middle adds no pan of its own, so the point under the middle
    stays and no framing is made."""
    from tests.test_fractal import _reg
    s = _view("Menger sponge", frac_dive=1.0)
    reg = _reg(s)
    for _ in range(70):
        _frame_reg(s, reg, 0.1)
    reg["view.frac_dive"].set(0.0)
    _frame_reg(s, reg, 0.1)
    reg["camera.pan.x"].set(reg["camera.pan.x"].base + 0.05)    # the cell off the middle
    _frame_reg(s, reg, 0.1)
    fr = s.dive.frame.copy()
    spec = fractal.spec_of(s.shape)
    x, path = _under_middle(s), list(s.dive.path)
    assert fractal.about_middle(s)
    app._zoom_about(reg["camera.zoom"], reg["camera.pan.x"], reg["camera.pan.y"], s,
                    -1.0, WD / 2, HT / 2, WD, HT)               # a notch out, at the middle
    _frame_reg(s, reg, 1 / 60)
    assert s.dive.path == path
    assert np.allclose(s.dive.frame, fr, atol=1e-12)
    assert np.abs(_q(s, _rooted(spec, x, path, s.dive.path))).max() / s.zoom < 1e-9


def test_a_wheel_zoom_outside_a_fractal_is_about_the_cursor_as_before():
    from tests.test_fractal import _reg
    s = ViewState(shape=geometry.shape_index("Tesseract"), zoom=1.3, pan=[0.2, 0.1])
    reg = _reg(s)
    assert not fractal.about_middle(s)
    app._zoom_about(reg["camera.zoom"], reg["camera.pan.x"], reg["camera.pan.y"], s,
                    -1.0, WD / 2, HT / 2, WD, HT)
    reg.apply()
    f = s.zoom / 1.3
    assert s.pan == pytest.approx([0.2 * f, 0.1 * f])


def test_an_off_air_dive_centres_where_its_room_placement_draws_it():
    """A loaded dive with a room placement (`Dive.shift`) dived off air
    (`app._reroot_off_air`) goes as the same dive on air with no world."""
    def loaded() -> ViewState:
        s = _view("Menger sponge", frac_dive=1.0)
        doc = fractal.Dive(path=[3, 7], inside=True).to_json("Menger sponge")
        doc["shift"] = [0.5, -0.2, 0.0]
        assert s.dive.from_json(doc, "Menger sponge") == ""
        s.dive.shape = int(s.shape)
        return s
    a, b = loaded(), loaded()
    for _ in range(120):
        a.integrate(0.1)
        b.integrate(0.1)
        app._reroot(SimpleNamespace(view=a, world=None), None, 0.1)
        app._reroot_off_air(SimpleNamespace(view=b, reg=None), 0.1)
    assert a.dive.path == b.dive.path and len(a.dive.path) > 5
    assert np.allclose(_p(a), _p(b), atol=1e-12) and a.zoom == b.zoom


# ---- undoing a pause and a routed pan; a wheel notch out

def test_undoing_a_pause_resumes_from_the_paused_view(tmp_path):
    """Dive at +1 for a while, paused in the cell it is in, the pause undone:
    the rate comes back and the camera stays where the pause left it (to a
    frame's motion), not where the last step before the dive had it."""
    r = _undo_rig(tmp_path)
    rate = r.reg["view.frac_dive"]
    rate.set(1.0)
    _run(r, 60)                                      # (that edit's step closes)
    _run(r, 180)                                     # three levels on
    rate.set(0.0)
    _run(r, 60)
    s = r.view
    zoom, p, path = s.zoom, _p(s), list(s.dive.path)
    r.undo.undo()
    assert rate.base == pytest.approx(1.0)
    assert s.dive.path == path
    assert s.zoom == pytest.approx(zoom, rel=0.05)
    assert np.allclose(_p(s), p, atol=0.05 * s.zoom), (_p(s), p)


def test_undoing_a_pan_with_a_route_on_it_leaves_no_framing(tmp_path, monkeypatch):
    """A steady route on Pan X (its effective pan lands at the next `apply`):
    an undone pan takes its framing back, and the route's offset is not read
    as a pan the other way once it lands."""
    r = _undo_rig(tmp_path)
    pan = r.reg["camera.pan.x"]
    feed = r.router.modulate

    def modulate(*a, **k):
        feed(*a, **k)
        pan.modulate(0.01)                           # a steady offset, every frame
    monkeypatch.setattr(r.router, "modulate", modulate)
    r.reg["view.frac_dive"].set(1.0)
    _run(r, 60)
    pan.set(pan.base + 0.1)
    _run(r, 60)
    assert r.view.dive.frame[0] == pytest.approx(0.1, abs=1e-6)
    r.undo.undo()
    _run(r, 60)
    assert np.allclose(r.view.dive.frame, 0.0, atol=1e-6), r.view.dive.frame
    r.undo.redo()
    _run(r, 60)
    assert r.view.dive.frame[0] == pytest.approx(0.1, abs=1e-6)


def test_a_wheel_notch_that_takes_the_view_back_outside_holds_the_middle():
    """Inside at the top, panned, a notch out that makes the shape fit the box
    again: the middle's pivot the wheel left to the step is taken before the
    crossing out, so the pan scales with the zoom as about the middle."""
    from hyperspace import poi
    from tests.test_fractal import _reg
    s = _view("Menger sponge", zoom=1.0, pan=[0.2, 0.0])
    reg = _reg(s)
    h = SimpleNamespace(view=s, world=None)
    while not s.dive.inside:                         # in: too big for the box
        reg["camera.zoom"].set(reg["camera.zoom"].base * 1.03)
        _frame_reg(s, reg, 1 / 60)
    assert not s.dive.path
    out = 0
    while s.dive.inside and out < 200:               # notches out until it fits again
        z0, x0, last = s.zoom, s.pan[0], s.dive.last
        app._zoom_about(reg["camera.zoom"], reg["camera.pan.x"], reg["camera.pan.y"], s,
                        -0.2, WD / 2, HT / 2, WD, HT)
        reg.apply()
        s.integrate(1 / 60)
        app._space(h, reg)
        s.reroot(reg, None, 1 / 60)
        out += 1
    assert not s.dive.inside and poi.DEFAULT_BOX is not None
    # about the middle (× zoom ratio), then eased home as at the top any
    # zoom out is (`fractal.step`)
    ease = (s.zoom - fractal.Z_HOME) / (min(last, fractal.Z_IN) - fractal.Z_HOME)
    assert s.pan[0] == pytest.approx(x0 * s.zoom / z0 * min(max(ease, 0.0), 1.0), rel=1e-6)


# ---- two loads close together; a zoom that only slows a climb

def test_two_loads_within_the_settle_time_undo_one_at_a_time(tmp_path):
    """A second load before the first's step has settled: its step holds the
    camera as the first load left it, not as it was before both."""
    from tests.test_loadable import put
    from tests.test_undo import frames, settle
    r = _undo_rig(tmp_path)
    r.reg["view.shape"].set(geometry.shape_index("Tesseract"))
    r.reg["camera.zoom"].set(1.0)
    settle(r)
    for name, zoom in (("Two", 2.0), ("Three", 3.0)):
        put(r.home, name, values={"view.shape": geometry.shape_index("Tesseract"),
                                  "camera.zoom": zoom})
    r.loaded_patch.load("Two")
    frames(r, 6)                                     # well within SETTLE_S
    r.loaded_patch.load("Three")
    settle(r)
    assert r.reg["camera.zoom"].base == pytest.approx(3.0)
    r.undo.undo()
    assert r.reg["camera.zoom"].base == pytest.approx(2.0)
    r.undo.undo()
    assert r.reg["camera.zoom"].base == pytest.approx(1.0)


def test_a_zoom_in_that_only_slows_a_climb_is_about_the_middle():
    """Dive at −1 with a zoom in each frame that slows the climb but does not
    turn it: the frame's zoom is outward all told, so it is taken about the
    middle and nothing settles — the point under the middle stays."""
    from tests.test_fractal import _reg
    s = _view("Menger sponge", frac_dive=1.0)
    reg = _reg(s)
    for _ in range(70):
        _frame_reg(s, reg, 0.1)
    reg["view.frac_dive"].set(0.0)
    _frame_reg(s, reg, 0.1)
    reg["camera.pan.x"].set(reg["camera.pan.x"].base + 0.05)    # the cell off the middle
    _frame_reg(s, reg, 0.1)
    while s.zoom < 0.9 * fractal.Z_IN:               # room to climb within the cell
        reg["camera.zoom"].set(reg["camera.zoom"].base * 1.05)
        _frame_reg(s, reg, 1 / 60)
    spec = fractal.spec_of(s.shape)
    x, path = _under_middle(s), list(s.dive.path)
    reg["view.frac_dive"].set(-1.0)
    for _ in range(30):
        z0 = s.zoom
        reg["camera.zoom"].set(reg["camera.zoom"].base * 1.015)  # slows the climb
        _frame_reg(s, reg, 1 / 60)
        assert s.zoom < z0                           # outward all told
    assert s.dive.path == path
    assert np.abs(_q(s, _rooted(spec, x, path, s.dive.path))).max() / s.zoom < 1e-9


# ---- crossing out by the centred pose

def test_a_crossing_out_goes_by_the_centred_pose(monkeypatch):
    """At the top, a turn since the last step (an orbit) moves the pan about
    the middle. Whether the view crosses out goes by that centred pose alone:
    where only the uncentred one would fit, the view stays inside."""
    from tests.test_fractal import _reg
    s = _view("Menger sponge", zoom=1.0, pan=[0.2, 0.0])
    reg = _reg(s)
    h = SimpleNamespace(view=s, world=None)
    while not s.dive.inside:
        reg["camera.zoom"].set(reg["camera.zoom"].base * 1.03)
        _frame_reg(s, reg, 1 / 60)
    assert not s.dive.path and fractal.about_middle(s)
    s.yaw += 0.2                                     # an orbit frame: the pivot is pending
    raw = list(s.pan)
    # the uncentred pose fits the box (wants out), the centred one does not
    monkeypatch.setattr(fractal, "wants_inside", lambda v, box, off=None: list(v.pan) != raw)
    app._space(h, reg)
    assert s.dive.inside
