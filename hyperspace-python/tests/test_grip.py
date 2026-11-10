"""Plan 60: the hand rig — the joint, the coupling, the throw, the shaped
inertia (precession), the skater effect, the box, the safety rules, and the
`grip.*` params. Tape-driven (`hands/tape.py`) or pure; nothing on a sensor."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pytest
from fake_hands import hand

from hyperspace import app
from hyperspace import geometry as G
from hyperspace import ghost as GH
from hyperspace import grip as R
from hyperspace import world as W
from hyperspace.hands import HandSettings, HandsIO, features, skeleton
from hyperspace.hands import tape as T
from hyperspace.params import MetaRegistry, part_of

RNG = np.random.default_rng(60)


def _quat() -> np.ndarray:
    return W.qnorm(RNG.normal(size=4))


def _palm(q, at) -> tuple:
    return np.asarray(at, dtype=float), W.rot3(q)


def _rigged(coupling: float = 1.0, *, zoom: float = 0.7, pan=(0.2, 0.1), drag: float = 0.0,
            **state) -> tuple[W.World, R.GripState, dict]:
    """A world with the grip on, the holding clutch a dict entry the test flips."""
    w = W.World.default()
    w.home("shape", W.shape_home(zoom, pan))
    st = R.GripState(on=True, coupling=coupling, drag=drag, **state)
    gates: dict[str, bool] = {}
    R.apply(w, st, lambda a: gates.get(a, False))
    return w, st, gates


def _frame(w, st, gates, dt, palms):
    R.apply(w, st, lambda a: gates.get(a, False))
    w.frame(dt, palms)


def _same_pose(a: W.Pose, b: W.Pose, tol=1e-9) -> bool:
    return (np.abs(a.position - b.position).max() <= tol
            and np.abs(W.short(a.ql, b.ql) - b.ql).max() <= tol)


# ---------------------------------------------------------------- the joint

@pytest.mark.parametrize("coupling", [1.0, 0.6, 0.0])
def test_closing_the_clutch_at_any_pose_moves_nothing_on_that_frame(coupling):
    for _ in range(10):
        w, st, gates = _rigged(coupling)
        w["shape"].offset = W.Pose.turn3(_quat(), RNG.uniform(-0.3, 0.3, 3))
        palm = _palm(_quat(), RNG.uniform(-0.5, 0.5, 3))
        _frame(w, st, gates, 1 / 60, {"right": palm})
        before = w["shape"].pose
        gates["hand:right.grab"] = True
        _frame(w, st, gates, 1 / 60, {"right": palm})
        assert w.joints["shape"].rel is not None
        assert _same_pose(w["shape"].pose, before, 1e-12)


def test_welded_the_shape_is_the_hands_pose_times_the_captured_one_every_frame():
    w, st, gates = _rigged(1.0)
    w["shape"].offset = W.Pose.turn3(_quat(), (0.1, -0.2, 0.3))
    gates["hand:right.grab"] = True
    for k in range(40):
        q = W.qnorm(W.qmul(W.qexp([0.05 * k, 0.03 * k, -0.02 * k]), [0.1, 0.2, 0.3, 0.9]))
        _frame(w, st, gates, 1 / 60, {"right": _palm(q, (0.3 + 0.01 * k, 0.1 * math.sin(k), 0.0))})
        want = w["hand.right"].home.compose(w.joints["shape"].rel)
        assert _same_pose(w["shape"].pose, want, 1e-9)


def test_welded_the_velocities_are_the_hands_so_a_let_go_flies_on():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0))
    gates["hand:right.grab"] = True
    for k in range(10):                          # the hand carried right at 0.6 units/s
        _frame(w, st, gates, 1 / 60, {"right": _palm([0, 0, 0, 1], (0.01 * k, 0.0, 0.0))})
    b = w.bodies["shape"]
    assert b.velocity[:3] == pytest.approx((0.6, 0.0, 0.0))
    gates["hand:right.grab"] = False
    x0 = w["shape"].pose.position[0]
    for _ in range(6):
        _frame(w, st, gates, 1 / 60, {"right": _palm([0, 0, 0, 1], (0.09, 0.0, 0.0))})
    assert w.joints["shape"].rel is None
    assert w["shape"].pose.position[0] - x0 == pytest.approx(0.6 * 0.1, rel=1e-6)   # no drag


def test_a_turning_hand_swings_the_shape_round_it():
    """A hand turning about its own centre carries a shape held out from it
    round that centre: the target's velocity is ω × r, so a throw at the end
    of a swing flies off along the swing."""
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0))
    w["shape"].offset = W.Pose((1.0, 0.0, 0.0))
    gates["hand:right.grab"] = True
    for k in range(10):                          # 1 rad/s about z, the shape 1 unit out on x
        _frame(w, st, gates, 1 / 60, {"right": _palm(W.qexp([0, 0, k / 60]), (0, 0, 0))})
    b = w.bodies["shape"]
    r = w["shape"].pose.position[:3]
    assert b.velocity[:3] == pytest.approx(np.cross((0, 0, 1.0), r), abs=1e-9)
    assert b.spin_l == pytest.approx((0, 0, 1.0))


def test_a_lost_hand_opens_the_clutch_and_the_body_keeps_its_velocity():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0))
    gates["hand:right.grab"] = True
    for k in range(5):
        _frame(w, st, gates, 1 / 60, {"right": _palm([0, 0, 0, 1], (0.0, 0.02 * k, 0.0))})
    _frame(w, st, gates, 1 / 60, {})
    assert w.joints["shape"].rel is None
    assert w.bodies["shape"].velocity[1] == pytest.approx(1.2)


def _hands_tape() -> dict:
    """The right hand closing to a fist, then carried and rolled, for 50 frames."""
    frames = []
    for k in range(50):
        grip = "open" if k < 3 else "fist"
        h = hand("right", grip, (40.0 + 2 * k, 200.0 + k, 5.0 - k), roll=3.0 * k)
        frames.append({"t": k / 90, "hands": {"right": {
            "features": features(h), "confidence": 1.0, "skeleton": skeleton(h)}}})
    return {"schema": T.TAPE_SCHEMA, "mode": "desktop", "frames": frames}


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_a_tape_held_by_its_grab_welds_the_shape_to_the_palm():
    """Tape-driven, through the ghost hands' calibration and the grab's Gate:
    once the fist closes, every frame the shape is the palm times the pose
    captured as it closed."""
    clock = Clock()
    io = HandsIO(HandSettings.from_config({}), {"out": ""},
                 source=T.TapeSource(_hands_tape(), clock), clock=clock)
    gh = GH.Ghost(ctx=None, state=GH.GhostState(on=True))
    gh.source = io
    w = W.World.default()
    w.home("shape", W.shape_home(0.8, (0.0, 0.0)))
    st = R.GripState(on=True, coupling=1.0)
    closed = lambda a: a == "hand:right.grab" and io.grab["right"].on   # the lane's Gate
    held = 0
    for k in range(50):
        clock.t = k / 90 + 1e-4
        io.poll(1 / 90)
        R.apply(w, st, closed)
        w.frame(1 / 90, app.palms_in_world(gh))
        j = w.joints["shape"]
        if j.rel is not None:
            held += 1
            assert _same_pose(w["shape"].pose, w["hand.right"].home.compose(j.rel), 1e-9)
    assert held > 30


# ---------------------------------------------------------------- the spring

def test_the_coupling_sets_a_frequency_falling_to_a_floor_and_damping_with_it():
    lo, hi = W.spring_of(0.0), W.spring_of(0.999)
    assert lo[0] == pytest.approx(2 * math.pi * W.SPRING_HZ[0])
    assert hi[0] == pytest.approx(2 * math.pi * W.SPRING_HZ[1], rel=0.01)
    assert lo[1] < W.spring_of(0.5)[1] < hi[1] <= 1.0
    freqs = [W.spring_of(c)[0] for c in np.linspace(0, 0.99, 12)]
    assert all(np.diff(np.log(freqs)) > 0)                        # geometric: log-linear
    assert np.allclose(np.diff(np.log(freqs)), np.diff(np.log(freqs))[0])


def _step_response(t, wn, zeta):
    """x'' = ωn² (1 − x) + 2ζωn (v_hand − x'), x(0) = x'(0) = 0, the hand stepped
    by 1 at t = 0: its velocity an impulse of area 1, so the damper's pull adds
    2ζωn to x'(0) — the step response plus that velocity's free response."""
    wd = wn * math.sqrt(1 - zeta * zeta)
    decay = math.exp(-zeta * wn * t)
    step = 1 - decay * (math.cos(wd * t) + zeta / math.sqrt(1 - zeta * zeta) * math.sin(wd * t))
    return step + 2 * zeta * wn / wd * decay * math.sin(wd * t)


@pytest.mark.parametrize("coupling", [0.2, 0.5])
def test_a_step_of_the_hand_settles_as_the_springs_frequency_and_damping_say(coupling):
    w, st, gates = _rigged(coupling, zoom=1.0, pan=(0.0, 0.0))
    gates["hand:right.grab"] = True
    dt = W.STEP_S                                      # a frame a step: the step lands whole
    _frame(w, st, gates, dt, {"right": _palm([0, 0, 0, 1], (0, 0, 0))})
    wn, zeta = W.spring_of(coupling)
    worst = 0.0
    for k in range(1, int(3.0 / dt)):
        _frame(w, st, gates, dt, {"right": _palm([0, 0, 0, 1], (0.5, 0, 0))})
        got = w["shape"].pose.position[0] / 0.5
        worst = max(worst, abs(got - _step_response(k * dt, wn, zeta)))
    assert worst < 0.02
    settle = 4.0 / (zeta * wn)                         # 2% settling time
    if settle < 3.0:
        assert abs(w["shape"].pose.position[0] - 0.5) < 0.5 * 0.02


def test_the_rotation_spring_acts_on_the_angular_velocity_without_gimbal_trouble():
    """A held shape follows a hand turned 2 rad about an axis through a pitch
    of 90° (gimbal lock for Euler angles) and settles exactly on it."""
    w, st, gates = _rigged(0.5, zoom=1.0, pan=(0.0, 0.0))
    gates["hand:right.grab"] = True
    _frame(w, st, gates, 1 / 60, {"right": _palm([0, 0, 0, 1], (0, 0, 0))})
    q = W.qmul(W.qexp([0, math.pi / 2, 0]), W.qexp([2.0, 0, 0]))
    for _ in range(240):
        _frame(w, st, gates, 1 / 60, {"right": _palm(q, (0, 0, 0))})
    want = w["hand.right"].home.compose(w.joints["shape"].rel)
    assert _same_pose(w["shape"].pose, want, 1e-6)


# ---------------------------------------------------------------- coasting

@pytest.mark.parametrize("fps", [30, 60, 144])
def test_a_release_coasts_down_at_the_drags_closed_form_rate(fps):
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), drag=1.5)
    b = w.bodies["shape"]
    b.velocity = np.array([0.4, 0.0, 0.0, 0.0])
    b.spin3((0.0, 2.0, 0.0))
    for _ in range(fps):
        _frame(w, st, gates, 1 / fps, {})
    t = fps * (1 / fps) - w.left
    assert b.velocity[0] == pytest.approx(0.4 * math.exp(-1.5 * t), rel=1e-9)
    assert b.spin_l[1] == pytest.approx(2.0 * math.exp(-1.5 * t), rel=1e-9)
    want = 0.4 / 1.5 * (1 - math.exp(-1.5 * t))
    assert w["shape"].offset.position[0] == pytest.approx(want, rel=2e-3)


def test_a_thrown_shape_is_held_to_the_box_while_its_physics_runs_on():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0))
    w.box = (1.5, 1.0, 2.0)
    b = w.bodies["shape"]
    b.velocity = np.array([3.0, 0.0, 0.0, 0.0])
    for _ in range(60):
        _frame(w, st, gates, 1 / 60, {})
    assert w["shape"].pose.position[0] == pytest.approx(1.5)        # drawn at the edge
    assert b.place[0] == pytest.approx(3.0, rel=1e-3)               # the physics ran on
    # taking hold there captures what is drawn: nothing jumps, the physics comes back
    gates["hand:right.grab"] = True
    palm = _palm([0, 0, 0, 1], (1.0, 0.0, 0.0))
    _frame(w, st, gates, 1 / 60, {"right": palm})
    assert w["shape"].pose.position[0] == pytest.approx(1.5)
    assert b.place[0] == pytest.approx(1.5)


def test_a_home_outside_the_box_is_not_pulled_in():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(3.0, 0.0))
    w.box = (1.5, 1.0, 2.0)
    _frame(w, st, gates, 1 / 60, {})
    assert w["shape"].pose.position[0] == pytest.approx(3.0)


# ---------------------------------------------------------------- inertia

def test_a_symmetric_body_precesses_at_the_analytic_rate():
    """Torque free, symmetric about its third axis, spinning slightly off it:
    in the body ω's cross part turns at Ω = (I₃ − I₁) / I₁ · ω₃."""
    for i1, i3, w3 in ((1.0, 2.0, 3.0), (2.0, 1.0, 4.0), (1.0, 3.5, -2.0)):
        # shaped, its clutch open: the inertia set here stays locked in the body
        w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), drag=0.0, inertia=True)
        b = w.bodies["shape"]
        b.inertia = np.diag([i1, i1, i3])
        w["shape"].offset = W.Pose.turn3(_quat())
        r0 = W.rot3(w["shape"].offset.ql)
        b.spin3(r0 @ np.array([0.1, 0.0, w3]))
        ts, angs = [], []
        for k in range(1, 121):
            _frame(w, st, gates, 1 / 60, {})
            wb = W.rot3(w["shape"].offset.ql).T @ b.spin_l
            ts.append(k / 60)
            angs.append(math.atan2(wb[1], wb[0]))
            assert wb[2] == pytest.approx(w3, rel=1e-4)            # ω₃ constant
        rate = np.polyfit(ts, np.unwrap(angs), 1)[0]
        assert rate == pytest.approx((i3 - i1) / i1 * w3, rel=1e-3)


def test_an_even_inertia_gives_no_gyroscopic_term():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), drag=0.0)
    b = w.bodies["shape"]
    b.spin3((0.3, -1.1, 2.0))
    for _ in range(120):
        _frame(w, st, gates, 1 / 60, {})
    assert b.spin_l == pytest.approx((0.3, -1.1, 2.0), abs=1e-12)


def test_the_angular_momentum_of_a_free_uneven_body_is_kept():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), drag=0.0, inertia=True)
    b = w.bodies["shape"]
    b.inertia = np.diag([1.0, 2.0, 3.0])          # three inertias: tumbling, L still kept
    b.spin3((0.4, 2.0, 0.3))
    def mom():
        r = W.rot3(w["shape"].offset.ql)
        return r @ b.inertia @ r.T @ b.spin_l
    l0, i0 = mom(), b.inertia.copy()
    for _ in range(240):
        _frame(w, st, gates, 1 / 60, {})
    assert np.array_equal(b.inertia, i0)
    assert mom() == pytest.approx(l0, abs=1e-9)
    assert not np.allclose(b.spin_l, (0.4, 2.0, 0.3), atol=1e-3)   # and ω has moved


def test_the_palms_vector_shapes_the_inertia_and_its_ratio_is_clamped():
    d = np.array([0.0, 3.0, 4.0])                 # length 5, along (0, .6, .8)
    i = W.shaped_inertia(d, 1.0, span=10.0)       # m = 0.5: 1.5 along n
    n = d / 5.0
    assert i @ n == pytest.approx(1.5 * n)
    perp = np.array([1.0, 0.0, 0.0])
    assert i @ perp == pytest.approx(perp)
    assert np.linalg.eigvalsh(W.shaped_inertia(d, 50.0, span=5.0)).max() == pytest.approx(4.0)
    assert np.linalg.eigvalsh(W.shaped_inertia(d, -50.0, span=5.0)).min() == pytest.approx(0.25)
    assert np.array_equal(W.shaped_inertia((0, 0, 0), 2.0), np.eye(3))


def _shaping(w, st, gates, spread: float, frames: int = 90):
    for _ in range(frames):
        _frame(w, st, gates, 1 / 60, {"right": _palm([0, 0, 0, 1], (0, 0, 0)),
                                      "left": _palm([0, 0, 0, 1], (spread, 0, 0))})


def test_the_inertia_shaped_in_the_room_locks_into_the_body_when_its_clutch_opens():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), inertia=True, shape=1.0)
    w["shape"].offset = W.Pose.turn3(W.qexp([0, 0, 0.7]))
    gates["hand:left.grab"] = True
    _shaping(w, st, gates, W.SPAN)                # m = 1: 2 along x, in the room
    b = w.bodies["shape"]
    r = W.rot3(w["shape"].offset.ql)
    assert r @ b.inertia @ r.T == pytest.approx(np.diag([2.0, 1.0, 1.0]), abs=1e-9)
    gates["hand:left.grab"] = False
    locked = b.inertia.copy()
    _shaping(w, st, gates, 0.5 * W.SPAN, 30)      # the hands move: nothing changes now
    assert np.array_equal(b.inertia, locked)


def test_the_skater_keeps_angular_momentum_so_halving_the_inertia_doubles_the_spin():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), inertia=True, shape=1.0)
    gates["hand:left.grab"] = True
    _shaping(w, st, gates, W.SPAN)                # 2 along x
    b = w.bodies["shape"]
    b.spin3((1.5, 0.0, 0.0))                      # spinning about the palms' line
    l0 = 2.0 * 1.5
    _shaping(w, st, gates, 1e-12, 120)            # hands together: even, 1 along x
    assert b.spin_l[0] == pytest.approx(3.0, rel=1e-6)            # doubled
    r = W.rot3(w["shape"].offset.ql)
    assert (r @ b.inertia @ r.T @ b.spin_l)[0] == pytest.approx(l0, rel=1e-6)


def test_the_skater_off_keeps_the_spin_and_only_the_inertia_changes():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), inertia=True, shape=1.0,
                           skater=False)
    gates["hand:left.grab"] = True
    _shaping(w, st, gates, W.SPAN)
    b = w.bodies["shape"]
    b.spin3((1.5, 0.0, 0.0))
    _shaping(w, st, gates, 1e-12, 120)
    assert b.spin_l[0] == pytest.approx(1.5, rel=1e-9)


def test_a_large_inertia_change_is_spread_over_several_frames():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), inertia=True, shape=3.0)
    gates["hand:left.grab"] = True
    b = w.bodies["shape"]
    _shaping(w, st, gates, W.SPAN, 1)             # one frame: 1 → 4 asked
    first = b.inertia[0, 0]
    assert 1.0 < first < 1.2                      # INERTIA_RATE / 60 of the way, about
    _shaping(w, st, gates, W.SPAN, 60)
    assert b.inertia[0, 0] == pytest.approx(4.0)


def test_the_angular_speed_is_held_under_its_ceiling():
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0), inertia=True, shape=3.0)
    gates["hand:left.grab"] = True
    _shaping(w, st, gates, W.SPAN)                # 4 along x
    b = w.bodies["shape"]
    b.spin3((0.9 * W.MAX_SPIN, 0.0, 0.0))
    _shaping(w, st, gates, 1e-12, 120)            # the skater would quadruple it
    assert np.linalg.norm(b.spin_l) <= W.MAX_SPIN + 1e-9


def test_a_nan_puts_the_body_home_and_says_so_once(capsys):
    w, st, gates = _rigged(1.0, zoom=1.0, pan=(0.0, 0.0))
    b = w.bodies["shape"]
    b.velocity = np.array([math.nan, 0.0, 0.0, 0.0])
    _frame(w, st, gates, 1 / 60, {})
    _frame(w, st, gates, 1 / 60, {})
    b.velocity = np.array([math.nan, 0.0, 0.0, 0.0])
    _frame(w, st, gates, 1 / 60, {})
    assert w["shape"].offset.is_identity() and not b.velocity.any()
    assert w.note and capsys.readouterr().err.count("non-finite") == 1


# ---------------------------------------------------------------- the params

def test_off_the_grip_drops_its_body_and_joint_and_the_offset_stays():
    w, st, gates = _rigged(1.0)
    w.bodies["shape"].velocity = np.array([0.5, 0.0, 0.0, 0.0])
    _frame(w, st, gates, 1 / 60, {})
    was = w["shape"].offset.position.copy()
    st.on = False
    _frame(w, st, gates, 1 / 60, {})
    assert "shape" not in w.bodies and "shape" not in w.joints
    assert np.array_equal(w["shape"].offset.position, was)


def test_the_clutches_default_to_the_grabs_and_follow_the_hand():
    st = R.GripState()
    assert (R.clutch_of(st), R.shape_clutch_of(st)) == ("hand:right.grab", "hand:left.grab")
    st.hand = 0
    assert (R.clutch_of(st), R.shape_clutch_of(st)) == ("hand:left.grab", "hand:right.grab")
    st.clutch, st.shape_clutch = " hand:left.pinch.index ", "pad:A"
    assert (R.clutch_of(st), R.shape_clutch_of(st)) == ("hand:left.pinch.index", "pad:A")


def test_changing_hands_lets_go():
    w, st, gates = _rigged(1.0)
    gates["hand:right.grab"] = True
    _frame(w, st, gates, 1 / 60, {"right": _palm([0, 0, 0, 1], (0, 0, 0))})
    assert w.joints["shape"].rel is not None
    st.hand = 0
    _frame(w, st, gates, 1 / 60, {"right": _palm([0, 0, 0, 1], (0, 0, 0))})
    assert w.joints["shape"].hand == "hand.left" and w.joints["shape"].rel is None


def test_world_reset_lets_go_and_evens_the_inertia():
    w, st, gates = _rigged(1.0, inertia=True)
    gates["hand:right.grab"] = True
    _frame(w, st, gates, 1 / 60, {"right": _palm([0, 0, 0, 1], (0.3, 0, 0))})
    w.bodies["shape"].inertia = np.diag([1.0, 1.0, 2.0])
    w.reset()
    assert w.joints["shape"].rel is None and np.array_equal(w.bodies["shape"].inertia, np.eye(3))
    assert w["shape"].offset.is_identity()


class _Router:
    def __init__(self, vec):
        self.feeds = {"hand": vec}

    def lane(self, address):
        return ("hand", {"hand:right.grab": 0, "hand:left.grab": 1}.get(address, -1))


def test_a_gate_reads_closed_at_half_and_open_when_away_or_unknown():
    r = _Router(np.array([0.5, math.nan]))
    assert R.lane_closed(r, "hand:right.grab")
    assert not R.lane_closed(r, "hand:left.grab")                # NaN: the hand away
    assert not R.lane_closed(r, "hand:right.pinch.index")       # no such lane
    assert not R.lane_closed(None, "hand:right.grab")
    assert not R.lane_closed(_Router(None), "hand:right.grab")


def test_the_grip_params_are_a_saved_shared_meta_group():
    meta = MetaRegistry()
    st = R.GripState()
    R.register(meta, st)
    ids = [p.id for p in meta if p.group == R.GROUP]
    assert ids == ["grip.on", "grip.hand", "grip.coupling", "grip.drag", "grip.inertia",
                   "grip.shape", "grip.skater", "grip.clutch", "grip.shape_clutch"]
    for pid in ids:
        p = meta[pid]
        assert part_of(p) == "shared_meta" and p.persist
    # a meta param: no route lands on it (row 775); a desk row (a learned knob) sets it
    assert not meta["grip.coupling"].modulatable
    meta["grip.coupling"].set(0.25)
    meta["grip.hand"].set(0)
    meta["grip.clutch"].set("pad:A")
    assert (st.coupling, st.side, st.clutch) == (0.25, "left", "pad:A")
    R.register(meta, st)                          # twice: once
    assert not st.on                              # off by default


def test_the_host_sets_the_grip_onto_the_world_before_its_frame():
    from types import SimpleNamespace as NS

    w = W.World.default()
    st = R.GripState(on=True)
    h = NS(world=w, grip=st, view=NS(zoom=1.0, pan=[0.0, 0.0]),
           router=_Router(np.array([1.0, 0.0])), renderer=NS(ghost=None))
    app._step_world(h, 1 / 60)
    assert w.joints["shape"].closed and not w.joints["shape"].shaping
    assert w.bodies["shape"].boxed


# ---------------------------------------------------------------- the depth (row 856)

def test_a_turned_offset_turns_a_3d_shapes_depth_cue_and_leaves_a_4d_shapes_w():
    q = W.qexp([0.0, 1.3, 0.0])
    off = W.Pose.turn3(q).model3()
    three = next(i for i in range(len(G.SHAPES)) if G.is_3d(i) and "layers" not in G.geom(i))
    P, _, pd = G.shape_world(three, [0.0] * 6, 0.3, 0.2)
    assert np.allclose(pd, P[:, 2])
    assert np.allclose(G.turned_depth(three, P, pd, off), (P @ W.rot3(q).T)[:, 2])
    four = next(i for i in range(len(G.SHAPES)) if not G.is_3d(i) and "layers" not in G.geom(i))
    P4, _, pd4 = G.shape_world(four, [0.1] * 6, 0.3, 0.2)
    assert np.array_equal(G.turned_depth(four, P4, pd4, off), pd4)


def test_the_grip_imports_only_the_world():
    tree = ast.parse(Path(R.__file__).read_text())
    got = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.level:
            got.update(f"{n.module or ''}.{a.name}".strip(".") for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            assert not (n.module or "").startswith("hyperspace"), n.module
        elif isinstance(n, ast.Import):
            assert not any(a.name.startswith("hyperspace") for a in n.names)
    assert got == {"world"}
