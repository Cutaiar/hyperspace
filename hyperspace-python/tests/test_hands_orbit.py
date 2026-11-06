"""The Ultraleap orbit (plan 51 O2): a clutch and `turn` rows onto the one camera.

Tape-driven through the real route path: hand poses as a real tape file, played
through `TapeSource` and `HandsIO`, the fist read from the skeleton's curls, the
rows run by `Router.modulate`. Nothing here has seen a real sensor (hand checks
517–519).
"""

from __future__ import annotations

import json
import math
from itertools import pairwise
from types import SimpleNamespace

import pytest
from fake_hands import hand as fake_hand
from test_hands import make_app, v3
from test_hands_room import FPS, lane, play, pose
from test_undo import boot, settle

from hyperspace import learn, preset, ui_routing, undo
from hyperspace.deck import Deck
from hyperspace.hands import core as hc
from hyperspace.hands import room as R
from hyperspace.hands import tape as T
from hyperspace.routing import MOD_OPS, TURN_GRACE_S, TURN_OP, Binding, Owned, is_meta_row

YAW, PITCH = "hand:right.room.yaw", "hand:right.room.pitch"
GRAB = "hand:right.grab"
SETTLE_FRAMES = round(hc.GRAB_HOLD_S * FPS) + 2      # a fist held long enough to close
LONG_OPEN = round((TURN_GRACE_S + 0.1) * FPS)        # long enough to be another closure


def fist(**kw):
    return (pose(**kw), True)


def opened(**kw):
    return (pose(**kw), False)


def closing(**kw):
    """A fist held until the debounce has closed the clutch, the palm still."""
    return [fist(**kw)] * SETTLE_FRAMES


def opening(**kw):
    return [opened(**kw)] * SETTLE_FRAMES


def write(path, script, at=(40.0, 200.0, 0.0)):
    """(palm pose, fist?) a frame at FPS, as a tape on disk; None: no hand."""
    frames = []
    for k, step in enumerate(script):
        hands = {}
        if step is not None:
            (normal, direction), closed = step
            h = fake_hand("right", "fist" if closed else "open", at)
            h.palm.normal, h.palm.direction = v3(*normal), v3(*direction)
            hands["right"] = {"features": hc.features(h), "confidence": 1.0,
                              "skeleton": hc.skeleton(h)}
        frames.append({"t": k / FPS, "hands": hands})
    T.save({"schema": T.TAPE_SCHEMA, "mode": "desktop", "frames": frames}, path)
    return path


def orbit_rows(table, *rows):
    for b in list(table.bindings):
        if b.target in ("camera.yaw", "camera.pitch"):
            table.remove(b)
    for b in rows or (Binding(YAW, "camera.yaw", TURN_OP, when=GRAB),):
        table.add(b)


class Run:
    """A script through the real path; `yaw[k]` the camera's base after frame
    k, in degrees, and `value[k]` what it shows."""

    def __init__(self, app, tmp_path, script, *, target="camera.yaw", steps=None, each=None,
                 **kw):
        p = app.reg[target]
        self.yaw, self.value = [], []

        def frame(io, k):
            if steps is not None:
                steps.tick(k / FPS)
            app.router.modulate(dt=1 / FPS)
            app.reg.apply()
            self.yaw.append(math.degrees(p.base))
            self.value.append(math.degrees(p.value))
            if each is not None:
                each(io, k)

        self.run = play(write(tmp_path / "t.json", script), router=app.router, each=frame, **kw)


def steps_of(seq):
    """Each frame's move, shortest way round."""
    return [R.wrap(b - a) for a, b in pairwise(seq)]


@pytest.fixture()
def app(tmp_path):
    a = make_app(tmp_path)
    orbit_rows(a.table)
    a.reg["camera.yaw"].set(0.0)
    a.reg["camera.pitch"].set(0.0)
    return a


# ------------------------------------------------------------ the clutch

def test_a_closed_hand_turns_the_camera_one_for_one_and_it_stays(app, tmp_path):
    script = closing() + [fist(yaw=float(k)) for k in range(31)] + opening(yaw=30.0)
    r = Run(app, tmp_path, script)
    assert r.yaw[-1] == pytest.approx(30.0, abs=0.2)
    assert r.value[-1] == pytest.approx(r.yaw[-1])       # the base: nothing rides on it
    assert not app.reg["camera.yaw"].modulated


def test_an_open_hand_moves_freely_and_closing_continues_with_no_jump(app, tmp_path):
    """The mouse lifted: the palm goes back while open, and closing there
    starts from where the camera sits, not from the palm's angle."""
    script = (closing() + [fist(yaw=float(k)) for k in range(31)] + opening(yaw=30.0)
              + [opened(yaw=30.0 - k) for k in range(61)]           # swings to −30°, free
              + closing(yaw=-30.0)
              + [fist(yaw=-30.0 + k) for k in range(21)])           # another 20°
    r = Run(app, tmp_path, script)
    k_open = len(closing()) + 31 + len(opening())
    assert r.yaw[k_open] == pytest.approx(30.0, abs=0.3)
    assert all(v == pytest.approx(r.yaw[k_open]) for v in r.yaw[k_open:k_open + 61])
    assert r.yaw[-1] == pytest.approx(50.0, abs=0.4)             # 30 + 20, not the palm's −10
    assert max(abs(s) for s in steps_of(r.yaw)) < 1.01           # never more than the palm's 1°


def test_a_fist_closing_at_an_angle_does_not_slam_the_camera_there(app, tmp_path):
    script = opening(yaw=120.0) + closing(yaw=120.0)
    r = Run(app, tmp_path, script)
    assert all(v == pytest.approx(0.0, abs=1e-6) for v in r.yaw)


def test_turning_while_open_moves_nothing(app, tmp_path):
    r = Run(app, tmp_path, [opened(yaw=float(k)) for k in range(60)])
    assert all(v == 0.0 for v in r.yaw)


def test_the_grab_debounce_is_the_clutchs_edge(app, tmp_path):
    """The clutch closes on the grab lane, not on the first fist frame."""
    closed = []
    script = [fist(yaw=float(k)) for k in range(30)]
    r = Run(app, tmp_path, script,
            each=lambda io, k: closed.append(io.lanes()[io.layout.grab["right"]]))
    first = closed.index(1.0)
    assert 0 < first < 15
    assert all(v == 0.0 for v in r.yaw[:first + 1])              # its first frame only reads
    assert r.yaw[-1] == pytest.approx(29.0 - first, abs=0.3)


# ------------------------------------------------------------ the seam

def test_the_palm_crossing_the_seam_is_one_turn_with_no_sweep(app, tmp_path):
    script = closing(yaw=170.0) + [fist(yaw=170.0 + k) for k in range(21)]     # through ±180°
    r = Run(app, tmp_path, script)
    lanes = lane(r.run, "right.room.yaw")
    assert max(lanes) - min(lanes) > 0.9                         # the lane did step across
    assert all(abs(s) < 1.01 for s in steps_of(r.yaw))
    assert r.yaw[-1] == pytest.approx(20.0, abs=0.3)


@pytest.mark.parametrize("depth", [0.5, -0.5])
def test_the_seam_is_the_shortest_way_at_any_depth(app, tmp_path, depth):
    """At depth 1 a wrapping target would hide a linear difference (a whole
    throw wraps to nothing); off 1 the seam shows whether it is read as a turn."""
    orbit_rows(app.table, Binding(YAW, "camera.yaw", TURN_OP, depth, when=GRAB))
    r = Run(app, tmp_path, closing(yaw=170.0) + [fist(yaw=170.0 + k) for k in range(21)])
    assert all(abs(s) < 0.51 for s in steps_of(r.yaw))
    assert r.yaw[-1] == pytest.approx(20.0 * depth, abs=0.3)


def test_the_camera_crossing_its_own_seam_wraps(app, tmp_path):
    app.reg["camera.yaw"].set(math.radians(175.0))
    script = closing() + [fist(yaw=float(k)) for k in range(21)]
    r = Run(app, tmp_path, script)
    assert R.wrap(r.yaw[-1] - 195.0) == pytest.approx(0.0, abs=0.3)
    assert all(abs(s) < 1.01 for s in steps_of(r.yaw))
    assert -180.0 <= r.yaw[-1] < 180.0


def test_whole_turns_keep_adding_up(app, tmp_path):
    """Two turns of the palm, past both seams: the two have drifted by nothing."""
    script = closing() + [fist(yaw=k * 2.0) for k in range(361)]         # 720°
    r = Run(app, tmp_path, script)
    assert R.wrap(r.yaw[-1]) == pytest.approx(0.0, abs=0.5)
    assert sum(steps_of(r.yaw)) == pytest.approx(720.0, abs=0.5)


# ------------------------------------------------------------ a lost hand

def test_a_lost_hand_is_an_opened_clutch_and_returns_with_no_jump(app, tmp_path):
    script = (closing() + [fist(yaw=float(k)) for k in range(31)]
              + [None] * 30                                       # gone, mid-clutch
              + closing(yaw=-60.0)                                # back, elsewhere, still a fist
              + [fist(yaw=-60.0 + k) for k in range(11)])
    r = Run(app, tmp_path, script)
    gone = len(closing()) + 31
    assert r.yaw[gone - 1] == pytest.approx(30.0, abs=0.2)
    assert all(v == pytest.approx(r.yaw[gone - 1]) for v in r.yaw[gone:gone + 30])
    assert r.value[gone + 5] == pytest.approx(r.yaw[gone - 1])    # holds: does not go to a base
    assert r.yaw[-1] == pytest.approx(40.0, abs=0.3)
    assert all(abs(s) < 1.01 for s in steps_of(r.yaw))


def test_a_hand_lost_for_one_frame_holds_too(app, tmp_path):
    script = (closing() + [fist(yaw=float(k)) for k in range(11)] + [None]
              + [fist(yaw=11.0 + k) for k in range(20)])
    r = Run(app, tmp_path, script)
    assert all(abs(s) < 1.01 for s in steps_of(r.yaw))


def test_a_hand_the_box_keeps_out_moves_nothing(app, tmp_path):
    cal = tmp_path / "hands.json"
    cal.write_text(json.dumps({"schema": hc.CAL_SCHEMA, "axes": {},
                               "box": {"x": [-500.0, 0.0], "y": None, "z": None}}))
    r = Run(app, tmp_path, closing() + [fist(yaw=float(k)) for k in range(30)], cal=cal)
    assert r.run.io.box is not None
    assert all(v == 0.0 for v in r.yaw)


def test_a_hand_passing_just_outside_the_cone_does_not_sweep_the_camera(app, tmp_path):
    """About 9° off vertical, never in the cone: `atan2` swings most of half a
    turn in a few frames, each step short of a flip."""
    def over(k):
        # the fingers' tilt from vertical: 9° to the side, sliding front to back
        a, b = math.radians(9.0), math.radians(k - 30.0)
        z = (math.sin(a), math.cos(a) * math.cos(b), math.cos(a) * math.sin(b))
        return z

    def palm(k):
        back = over(k)
        up = (back[0], -back[2], back[1])
        d = sum(u * v for u, v in zip(up, back))
        up = tuple(u - d * v for u, v in zip(up, back))
        n = math.sqrt(sum(u * u for u in up))
        normal = tuple(-u / n for u in up)
        return (normal, tuple(-v for v in back))

    script = [(palm(0), True)] * SETTLE_FRAMES + [(palm(k), True) for k in range(61)]
    r = Run(app, tmp_path, script)
    yaw = lane(r.run, "right.room.yaw")
    live = [v for v in yaw if not math.isnan(v)]
    assert any(math.isnan(v) for v in yaw)                      # it went blind
    assert live
    moved = max(abs(v) for v in r.yaw)
    assert moved < 45.0       # outside the zone its real yaw, inside POLE_SWING_DEG; not ~160°


def test_a_hand_that_went_blind_starts_afresh_on_leaving(tmp_path):
    palm = R.Palm()
    m = R.stage("desktop")

    def at(t, **kw):
        n, d = pose(**kw)
        palm.step(R.palm_axes(n, d, m), t, 1e6, 0.0)

    at(0.00, pitch=80.0, yaw=0.0)
    palm._near = 0.0
    at(0.01, pitch=80.0, yaw=60.0)                               # strayed near the pole
    assert palm.deg == {}
    at(0.02, pitch=75.0, yaw=60.0)                               # still near
    assert palm.deg == {}
    at(0.03, pitch=60.0, yaw=60.0)                               # away: afresh, no glide
    assert palm.deg["yaw"] == pytest.approx(60.0, abs=0.01)
    assert not palm._blind and palm._near is None


def test_a_twist_inside_the_cone_is_no_step_on_the_way_out(app, tmp_path):
    """Up to vertical, twisted there, back down: the yaw the hand left the cone
    with is no turn of it, so the lane restarts and the camera does not step."""
    climb = [fist(yaw=10.0, pitch=2.0 * k) for k in range(46)]             # to 90°
    twist = [fist(yaw=10.0, pitch=90.0, roll=2.0 * k) for k in range(31)]  # 60° about the fingers
    # the same palm seen from outside the cone: yaw 70° (Ry·Rx·Rz at pitch 90 is yaw + roll)
    down = [fist(yaw=70.0, pitch=90.0 - 2.0 * k) for k in range(31)]
    r = Run(app, tmp_path, closing(yaw=10.0) + climb + twist + down)
    assert max(abs(s) for s in steps_of(r.yaw)) < 2.0
    lanes = lane(r.run, "right.room.yaw")
    assert any(math.isnan(v) for v in lanes)                     # blind until away from the pole
    assert sum(math.isnan(v) for v in lanes) <= 8


def test_a_small_step_out_of_the_cone_does_not_restart():
    """Noise at the cone's edge is not a twist: the reading goes on."""
    palm = R.Palm()
    m = R.stage("desktop")

    def at(pitch, yaw, t):
        n, d = pose(pitch=pitch, yaw=yaw)
        palm.step(R.palm_axes(n, d, m), t, 1e6, 0.0)

    for k, p in enumerate((70.0, 85.0, 89.0, 85.0, 75.0)):
        at(p, 10.0 + (2.0 if p == 75.0 else 0.0), k / FPS)
    assert not palm.pole and "yaw" in palm.deg
    assert palm.deg["yaw"] == pytest.approx(12.0, abs=0.1)


# ------------------------------------------------------------ the row

@pytest.mark.parametrize("depth, want", [(1.0, 30.0), (-1.0, -30.0), (0.5, 15.0)])
def test_the_depth_is_signed_and_scales_the_turn(app, tmp_path, depth, want):
    orbit_rows(app.table, Binding(YAW, "camera.yaw", TURN_OP, depth, when=GRAB))
    r = Run(app, tmp_path, closing() + [fist(yaw=float(k)) for k in range(31)])
    assert r.yaw[-1] == pytest.approx(want, abs=0.2)


def test_yaw_and_pitch_turn_together(app, tmp_path):
    orbit_rows(app.table, Binding(YAW, "camera.yaw", TURN_OP, when=GRAB),
               Binding(PITCH, "camera.pitch", TURN_OP, when=GRAB))
    r = Run(app, tmp_path, closing() + [fist(yaw=float(k), pitch=k / 2.0) for k in range(31)])
    assert r.yaw[-1] == pytest.approx(30.0, abs=0.3)
    assert math.degrees(app.reg["camera.pitch"].base) == pytest.approx(15.0, abs=0.3)


def test_a_row_with_no_gate_is_dormant_and_says_so(app, tmp_path):
    """It would never stop acting: no closure to be one undo step, and no way to
    reposition the hand."""
    orbit_rows(app.table, Binding(YAW, "camera.yaw", TURN_OP))
    r = Run(app, tmp_path, [opened(yaw=float(k)) for k in range(31)])
    assert all(v == 0.0 for v in r.yaw)
    assert app.table.owner("camera.yaw").describe("R room yaw").endswith("(dormant)")


@pytest.mark.parametrize("source", ["hand:right.x", "hand:right.yaw", "hands:gap"])
def test_a_source_that_is_no_circle_is_dormant(app, tmp_path, source):
    """A linear lane has no shortest way: 0.1 to 0.8 is not −0.3."""
    orbit_rows(app.table, Binding(source, "camera.yaw", TURN_OP, when=GRAB))
    r = Run(app, tmp_path, closing() + [fist(yaw=float(k), pitch=k / 2.0) for k in range(31)])
    assert all(v == 0.0 for v in r.yaw)


def test_a_clamped_target_stops_at_its_end(app, tmp_path):
    """Not a wrapping param: added up the same, and clamped."""
    bright = app.reg["view.bright"]
    bright.set_norm(0.9)
    start = bright.norm
    app.table.add(Binding(YAW, "view.bright", TURN_OP, when=GRAB))
    Run(app, tmp_path, closing() + [fist(yaw=float(k)) for k in range(91)], target="view.bright")
    assert start < bright.norm <= 1.0 and bright.norm == pytest.approx(1.0)


def test_a_target_that_cannot_turn_is_dormant(app, tmp_path):
    """An enum: no turn, no error, no state."""
    app.table.add(Binding(YAW, "view.shape", TURN_OP, when=GRAB))
    v = app.reg["view.shape"].value
    Run(app, tmp_path, closing() + [fist(yaw=float(k)) for k in range(31)])
    assert app.reg["view.shape"].value == v
    assert (YAW, "view.shape") not in app.router.__dict__.get("_turns", {})


def test_a_feel_on_the_row_is_not_read(app, tmp_path):
    from hyperspace.motion import DEFAULT_ROUTE_FEEL
    orbit_rows(app.table,
               Binding(YAW, "camera.yaw", TURN_OP, when=GRAB, motion=DEFAULT_ROUTE_FEEL))
    r = Run(app, tmp_path, closing(yaw=170.0) + [fist(yaw=170.0 + k) for k in range(21)])
    assert all(abs(s) < 171.0 for s in steps_of(r.yaw[len(closing()) + 1:]))
    assert r.yaw[-1] == pytest.approx(20.0, abs=0.3)
    assert "_movers" not in app.router.__dict__ or not app.router.__dict__["_movers"]


def test_it_is_a_performer_and_the_referee_keeps_one(app):
    row = app.table.owner("camera.yaw")
    assert row.op == TURN_OP and row.is_performer and TURN_OP in MOD_OPS
    with pytest.raises(Owned):
        app.table.add(Binding(PITCH, "camera.yaw", "position"))


def test_it_is_the_presets_row_never_the_rigs(app):
    row = app.table.owner("camera.yaw")
    assert not is_meta_row(row)
    assert row.to_json()["op"] == TURN_OP and row.to_json()["when"] == GRAB
    assert Binding.from_json(row.to_json()) == row
    assert '"turn"' not in app.table.dumps()
    assert row.describe("R room yaw", "R grab") == "R room yaw turns +1 while R grab"


def test_a_disabled_row_turns_nothing_and_a_new_one_starts_afresh(app, tmp_path):
    row = app.table.owner("camera.yaw")
    row.enabled = False
    r = Run(app, tmp_path, closing() + [fist(yaw=float(k)) for k in range(31)])
    assert all(v == 0.0 for v in r.yaw)


def test_no_turn_row_leaves_the_pass_as_it_was(app):
    for b in list(app.table.routes()):
        app.table.remove(b)
    app.router.modulate()
    assert "_turns" not in app.router.__dict__


# ------------------------------------------------------------ the wire

def test_a_room_lane_on_a_wrapping_target_lands_the_clutched_turn(app):
    row = learn.row_for(YAW, app.reg["camera.yaw"])
    assert (row.op, row.value, row.when, row.motion) == (TURN_OP, 1.0, GRAB, None)
    named = learn.row_for(YAW, app.reg["camera.yaw"], "hand:right.pinch.index")
    assert named.when == "hand:right.pinch.index"
    left = learn.row_for("hand:left.room.pitch", app.reg["camera.pitch"])
    assert left.when == "hand:left.grab"


def test_a_room_lane_on_a_clamped_target_stays_the_fader(app):
    row = learn.row_for(YAW, app.reg["view.bright"])
    assert (row.op, row.value, row.when, row.motion) == ("position", 1.0, None, None)


def test_the_op_chip_goes_between_position_and_turn_from_a_room_lane():
    room = Binding(YAW, "camera.yaw", TURN_OP)
    assert ui_routing._next_op(room, True) == "position"
    room.op = "position"
    assert ui_routing._next_op(room, True) == TURN_OP
    assert ui_routing._next_op(room, False) == "push"           # a clamped target: as ever
    room.op = "push"
    assert ui_routing._next_op(room, True) == ui_routing._next_op(room, False) == "position"
    plain = Binding("lane:0", "camera.yaw", "position")
    assert ui_routing._next_op(plain, True) == "push"
    assert ui_routing.OP_CHIP[TURN_OP] == "turn"


def test_flipping_to_turn_lands_as_a_wire_does():
    from hyperspace.motion import DEFAULT_ROUTE_FEEL
    row = Binding(YAW, "camera.yaw", "position", motion=DEFAULT_ROUTE_FEEL)
    ui_routing._flip_op(row, True)
    assert (row.op, row.when, row.motion) == (TURN_OP, GRAB, None)
    ui_routing._flip_op(row, True)
    assert row.op == "position" and row.motion is None          # no stale spring back
    assert row.when is None                                     # the clutch it landed with
    chosen = Binding(YAW, "camera.yaw", "position", when="hand:right.pinch.index")
    ui_routing._flip_op(chosen, True)
    assert chosen.when == "hand:right.pinch.index"
    ui_routing._flip_op(chosen, True)
    assert (chosen.op, chosen.when) == ("position", "hand:right.pinch.index")


def test_the_chip_always_moves_a_room_row_on_a_clamped_target():
    row = Binding(YAW, "view.bright", "position")
    seen = []
    for _ in range(3):
        ui_routing._flip_op(row, False)
        seen.append(row.op)
    assert seen == ["push", "position", "push"]


def test_a_pass_with_no_dt_runs_a_closure_through_its_grace(app, tmp_path):
    """`modulate` makes a None dt its 60 Hz frame before `_end_turns` reads it."""
    p = app.reg["camera.yaw"]
    seen = []

    def each(io, k):
        app.router.modulate()
        app.reg.apply()
        seen.append(p.base)

    script = closing() + [fist(yaw=float(k)) for k in range(11)] + opening(yaw=10.0)
    play(write(tmp_path / "t.json", script + [opened(yaw=10.0)] * LONG_OPEN),
         router=app.router, each=each)
    assert math.degrees(seen[-1]) == pytest.approx(10.0, abs=0.3)
    assert not app.router.__dict__["_turn_held"]


def test_moving_to_the_other_hand_takes_its_clutch(app):
    row = app.table.owner("camera.yaw")
    row.value = -1.0
    learn.move_route(app.table, app.reg, row, source="hand:left.room.yaw")
    assert (row.op, row.when, row.value) == (TURN_OP, "hand:left.grab", -1.0)


def test_moving_keeps_a_gate_someone_picked(app):
    row = app.table.owner("camera.yaw")
    row.when = "hand:right.pinch.index"
    learn.move_route(app.table, app.reg, row, source="hand:left.room.yaw")
    assert row.when == "hand:right.pinch.index"


def test_moving_onto_a_clamped_target_lands_the_fader(app):
    row = app.table.owner("camera.yaw")
    learn.move_route(app.table, app.reg, row, target="view.bright")
    assert (row.op, row.value, row.when, row.motion) == ("position", 1.0, None, None)


def test_moving_to_a_source_that_is_no_circle_lands_its_row(app):
    row = app.table.owner("camera.yaw")
    learn.move_route(app.table, app.reg, row, source="lane:0")
    want = learn.row_for("lane:0", app.reg["camera.yaw"])
    assert (row.op, row.value, row.when) == (want.op, want.value, None)
    assert row.op != TURN_OP


def test_moving_a_plain_row_keeps_what_it_was(app):
    app.table.add(Binding("lane:0", "view.bright", "push", 0.3))
    row = app.table.owner("view.bright")
    learn.move_route(app.table, app.reg, row, source="lane:1")
    assert (row.op, row.value) == ("push", 0.3)


def test_moving_a_room_row_onto_a_wrapping_target_lands_the_orbit(app):
    app.table.add(Binding(PITCH, "view.bright", "position"))
    row = app.table.owner("view.bright")
    learn.move_route(app.table, app.reg, row, target="camera.pitch")
    assert (row.op, row.when) == (TURN_OP, GRAB)


def test_a_cable_moved_on_the_graph_lands_as_a_wire_does(tmp_path):
    from test_ui_shell import build_rig

    from hyperspace import graphview

    with build_rig(tmp_path) as rig:
        table, reg = rig.router.table, rig.reg
        for b in list(table.bindings):
            if b.target in ("camera.yaw", "view.bright"):
                table.remove(b)
        table.add(Binding(YAW, "camera.yaw", TURN_OP, when=GRAB))
        row = table.owner("camera.yaw")
        view = graphview.build(table, reg, rig.router, None, None, None)
        e = graphview.Edit(table, reg, rig.router, view)
        # refused: nothing about the row moves, its op and clutch least of all
        assert isinstance(e.move("mod:camera.yaw", "mod:no.such.param"), graphview.Refusal)
        assert (row.target, row.op, row.when) == ("camera.yaw", TURN_OP, GRAB)
        got = e.move("mod:camera.yaw", "mod:view.bright")
        assert not isinstance(got, graphview.Refusal), got
        assert row.target == "view.bright" and (row.op, row.when) == ("position", None)


# ------------------------------------------------------------ undo

@pytest.fixture()
def deck(tmp_path):
    """The app's own deck, its `Undo` installed as app.main does."""
    r = boot(tmp_path / "home")
    orbit_rows(r.table)
    r.reg["camera.yaw"].set(0.0)
    settle(r)
    was = undo.installed()
    undo.install(r.undo)
    r.undo.tick(r.t)
    yield r
    undo.install(was)


def _orbits(r):
    return [s.label for s in r.undo.stack if s.label == "orbit"]


def test_one_clutch_closure_is_one_undo_step(deck, tmp_path):
    script = (closing() + [fist(yaw=float(k)) for k in range(31)] + opening(yaw=30.0)
              + [opened(yaw=30.0)] * LONG_OPEN
              + closing(yaw=30.0) + [fist(yaw=30.0 + k) for k in range(21)]
              + opening(yaw=50.0) + [opened(yaw=50.0)] * LONG_OPEN)
    before = len(deck.undo.stack)
    Run(deck, tmp_path, script, steps=deck.undo)
    assert _orbits(deck) == ["orbit", "orbit"]
    assert len(deck.undo.stack) == before + 2
    yaw = deck.reg["camera.yaw"]
    assert math.degrees(yaw.base) == pytest.approx(50.0, abs=0.5)
    deck.undo.undo()
    assert math.degrees(yaw.base) == pytest.approx(30.0, abs=0.5)
    deck.undo.undo()
    assert math.degrees(yaw.base) == pytest.approx(0.0, abs=1e-3)
    deck.undo.redo()
    assert math.degrees(yaw.base) == pytest.approx(30.0, abs=0.5)


def test_a_still_fist_past_the_settle_time_is_still_one_step(deck, tmp_path):
    still = [fist(yaw=15.0)] * round(FPS * (undo.SETTLE_S + 0.3))
    script = (closing() + [fist(yaw=k / 2.0) for k in range(31)] + still
              + [fist(yaw=15.0 + k / 2.0) for k in range(31)] + opening(yaw=30.0)
              + [opened(yaw=30.0)] * LONG_OPEN)
    Run(deck, tmp_path, script, steps=deck.undo)
    assert _orbits(deck) == ["orbit"]


def test_two_rows_turning_together_are_one_step(deck, tmp_path):
    orbit_rows(deck.table, Binding(YAW, "camera.yaw", TURN_OP, when=GRAB),
               Binding(PITCH, "camera.pitch", TURN_OP, when=GRAB))
    settle(deck)
    deck.undo.tick(deck.t)
    script = (closing() + [fist(yaw=float(k), pitch=k / 2.0) for k in range(21)]
              + opening(yaw=20.0, pitch=10.0) + [opened(yaw=20.0, pitch=10.0)] * LONG_OPEN)
    Run(deck, tmp_path, script, steps=deck.undo)
    assert _orbits(deck) == ["orbit"]


def test_a_closure_that_moved_nothing_leaves_no_step(deck, tmp_path):
    Run(deck, tmp_path, closing() * 2 + opening() + [opened()] * LONG_OPEN, steps=deck.undo)
    assert _orbits(deck) == []
    assert deck.undo._kept is None


def test_a_hand_lost_past_the_grace_closes_the_step(deck, tmp_path):
    script = (closing() + [fist(yaw=float(k)) for k in range(21)] + [None] * LONG_OPEN
              + closing(yaw=20.0) + [fist(yaw=20.0 + k) for k in range(11)] + opening(yaw=30.0)
              + [opened(yaw=30.0)] * LONG_OPEN)
    Run(deck, tmp_path, script, steps=deck.undo)
    assert _orbits(deck) == ["orbit", "orbit"]


def test_twenty_dropouts_are_still_one_step(deck, tmp_path):
    """Each a frame with no hand, the grab's debounce coming back after it: the
    row forgets each time (no jump), and the closure is one step, with no
    `_flush` / `_take` on the frame path for each."""
    script = closing()
    a = 0.0
    for _ in range(20):
        script = script + [None] + closing(yaw=a) + [fist(yaw=a + k) for k in range(3)]
        a += 2.0
    script += opening(yaw=a) + [opened(yaw=a)] * LONG_OPEN
    opens = []
    keep = deck.undo.keep_open
    deck.undo.keep_open = lambda *x, **k: (opens.append(1), keep(*x, **k))[1]
    Run(deck, tmp_path, script, steps=deck.undo)
    assert _orbits(deck) == ["orbit"] and len(opens) == 1


def test_an_undo_with_the_fist_still_closed_stops_the_turn_until_it_opens(deck, tmp_path):
    """The undo is not fought: a closed hand does not run on from what was put
    back, and the next closure turns again, from there."""
    n = len(closing()) + 31

    def each(io, k):
        if k == n:
            deck.undo.undo()

    script = (closing() + [fist(yaw=float(k)) for k in range(31)]
              + [fist(yaw=30.0 + k) for k in range(30)]                # still turning
              + opening(yaw=60.0) + [opened(yaw=60.0)] * LONG_OPEN
              + closing(yaw=60.0) + [fist(yaw=60.0 + k) for k in range(11)] + opening(yaw=70.0)
              + [opened(yaw=70.0)] * LONG_OPEN)
    r = Run(deck, tmp_path, script, steps=deck.undo, each=each)
    assert r.yaw[n + 1] == pytest.approx(0.0, abs=1e-3)
    assert all(v == pytest.approx(0.0, abs=1e-3) for v in r.yaw[n + 1:n + 30])
    assert r.yaw[-1] == pytest.approx(10.0, abs=0.3)
    assert _orbits(deck) == ["orbit"]                                  # the second; the first redoable
    assert len(deck.undo.redos) == 0                                   # a new edit clears the redo


def test_a_dropout_with_the_fist_closed_is_not_letting_go_of_the_cut(deck, tmp_path):
    """Undo mid-orbit, then a one-frame NaN, and the fist comes back still closed:
    the turn stays cut, and the next real closure turns from what was put back."""
    n = len(closing()) + 11
    back = n + 5

    def each(io, k):
        if k == n:
            deck.undo.undo()

    fists = [fist(yaw=float(k)) for k in range(21)]
    script = (closing() + fists + [None] + closing(yaw=20.0)
              + [fist(yaw=20.0 + k) for k in range(21)])
    total = len(script)
    script += (opening(yaw=40.0) + [opened(yaw=40.0)] * LONG_OPEN
               + closing(yaw=40.0) + [fist(yaw=40.0 + k) for k in range(11)]
               + opening(yaw=50.0) + [opened(yaw=50.0)] * LONG_OPEN)
    r = Run(deck, tmp_path, script, steps=deck.undo, each=each)
    assert all(v == pytest.approx(0.0, abs=1e-3) for v in r.yaw[back:total])
    assert r.yaw[-1] == pytest.approx(10.0, abs=0.5)


def test_a_cut_clears_after_the_same_grace_with_the_hand_gone(deck, tmp_path):
    n = len(closing()) + 11

    def each(io, k):
        if k == n:
            deck.undo.undo()

    script = (closing() + [fist(yaw=float(k)) for k in range(21)] + [None] * LONG_OPEN
              + closing(yaw=20.0) + [fist(yaw=20.0 + k) for k in range(11)]
              + opening(yaw=30.0) + [opened(yaw=30.0)] * LONG_OPEN)
    r = Run(deck, tmp_path, script, steps=deck.undo, each=each)
    assert r.yaw[-1] == pytest.approx(10.0, abs=0.5)
    assert not deck.router.__dict__["_turn_cut"]


def test_the_cut_is_each_rows_own(deck, tmp_path):
    """Undo with both rows acting: the clutched row, once its fist has opened and
    closed, turns again while the other, never let go, stays cut."""
    orbit_rows(deck.table, Binding(YAW, "camera.yaw", TURN_OP, when="hand:right.present"),
               Binding(PITCH, "camera.pitch", TURN_OP, when=GRAB))
    settle(deck)
    deck.undo.tick(deck.t)
    n = len(closing()) + 11

    def each(io, k):
        if k == n:
            deck.undo.undo()

    pitch = deck.reg["camera.pitch"]
    pitch.set(0.0)
    script = (closing() + [fist(yaw=float(k), pitch=float(k)) for k in range(21)]
              + opening(yaw=20.0, pitch=20.0) + [opened(yaw=20.0, pitch=20.0)] * LONG_OPEN
              + closing(yaw=20.0, pitch=20.0)
              + [fist(yaw=20.0 + k, pitch=20.0 + k) for k in range(11)])
    r = Run(deck, tmp_path, script, steps=deck.undo, each=each)
    assert math.degrees(pitch.base) == pytest.approx(10.0, abs=0.5)
    assert r.yaw[-1] == pytest.approx(r.yaw[n + 1], abs=1e-6)


def test_a_load_with_the_fist_closed_cuts_the_new_presets_row_only_until_it_opens(deck, tmp_path):
    deck.loaded_patch.save_as("ORBIT")
    n = len(closing()) + 11

    def each(io, k):
        if k == n:
            assert deck.loaded_patch.load("ORBIT") == []

    script = (closing() + [fist(yaw=float(k)) for k in range(31)]
              + opening(yaw=30.0) + [opened(yaw=30.0)] * LONG_OPEN
              + closing(yaw=30.0) + [fist(yaw=30.0 + k) for k in range(11)]
              + opening(yaw=40.0) + [opened(yaw=40.0)] * LONG_OPEN)
    r = Run(deck, tmp_path, script, steps=deck.undo, each=each)
    assert r.yaw[-1] == pytest.approx(10.0, abs=0.5)             # 0 at the load; only the last 10°


def test_a_deck_that_is_not_installed_has_its_own_step_and_cut(tmp_path):
    """Deck B's `Undo`, found by its registry, one step a closure; and installing
    another deck mid-closure changes nothing for it."""
    a = make_app(tmp_path)
    orbit_rows(a.table)
    a.reg["camera.yaw"].set(0.0)
    steps = undo.Undo(a.reg, a.table)
    was = undo.installed()
    (tmp_path / "other").mkdir()
    other = make_app(tmp_path / "other")
    other_steps = undo.Undo(other.reg, other.table)
    undo.install(other_steps)
    n = len(closing()) + 11

    def each(io, k):
        if k == n:
            undo.install(steps)
        if k == n + 5:
            steps.undo()

    try:
        script = (closing() + [fist(yaw=float(k)) for k in range(31)]
                  + opening(yaw=30.0) + [opened(yaw=30.0)] * LONG_OPEN
                  + closing(yaw=30.0) + [fist(yaw=30.0 + k) for k in range(11)]
                  + opening(yaw=40.0) + [opened(yaw=40.0)] * LONG_OPEN)
        r = Run(a, tmp_path, script, steps=steps, each=each)
    finally:
        undo.install(was)
    assert r.yaw[n + 6] == pytest.approx(0.0, abs=1e-3)          # the undo stood, no running on
    assert r.yaw[-1] == pytest.approx(10.0, abs=0.5)
    assert other_steps.stack == []
    assert undo.watching(a.reg) is steps and undo.watching(other.reg) is other_steps


def test_watching_knows_no_stand_in_and_finds_the_installed_one():
    class Stand:
        pass

    assert undo.watching(Stand()) is None
    assert undo.watching({}) is None                             # not hashable: no error
    reg = Stand()
    was = undo.installed()
    undo.install(SimpleNamespace(reg=reg))                       # as an `Undo` from before a reload
    try:
        assert undo.watching(reg) is undo.installed()
    finally:
        undo.install(was)


def test_another_decks_turn_keeps_no_step_on_this_undo(deck, tmp_path):
    (tmp_path / "other").mkdir()
    other = make_app(tmp_path / "other")
    orbit_rows(other.table)
    before = len(deck.undo.stack)
    Run(other, tmp_path, closing() + [fist(yaw=float(k)) for k in range(21)] + opening(yaw=20.0))
    assert len(deck.undo.stack) == before
    assert deck.undo._kept is None


# ------------------------------------------------------------ saved and held

def test_a_save_has_the_row_and_the_turned_camera(deck, tmp_path):
    """The camera route is the preset's (plan 43 C2): saved, reloaded, it is there."""
    script = closing() + [fist(yaw=float(k)) for k in range(31)] + opening(yaw=30.0)
    Run(deck, tmp_path, script, steps=deck.undo)
    path = deck.loaded_patch.save_as("ORBIT")
    doc = json.loads(path.read_text())
    assert doc["schema"].endswith("/10")                  # no schema move
    assert doc["values"]["camera.yaw"] == pytest.approx(math.radians(30.0), abs=0.01)
    assert {"source": YAW, "target": "camera.yaw", "op": TURN_OP, "when": GRAB}.items() <= next(
        r for r in doc["routes"] if r["target"] == "camera.yaw").items()
    deck.reg["camera.yaw"].set(0.0)
    orbit_rows(deck.table, Binding(PITCH, "camera.pitch", "position"))
    assert deck.loaded_patch.load("ORBIT") == []
    assert deck.table.owner("camera.yaw").op == TURN_OP
    assert deck.reg["camera.yaw"].base == pytest.approx(math.radians(30.0), abs=0.01)


def test_what_an_older_build_does_with_the_row(deck, tmp_path, monkeypatch):
    """An older build's `MOD_OPS` has no turn: the row goes with a note, the rest
    of the file lands, and nothing is refused. So no schema move (row 683)."""
    deck.reg["camera.pitch"].set(0.5)
    deck.loaded_patch.save_as("ORBIT")
    monkeypatch.setattr(preset, "MOD_OPS", ("push", "position"))
    deck.loaded_patch.load("ORBIT")
    notes = deck.loaded_patch.notes
    assert any("(turn): not a performer row" in n for n in notes)
    assert deck.table.owner("camera.yaw") is None
    assert deck.reg["camera.pitch"].base == pytest.approx(0.5)


def test_an_orbit_moves_the_deck_it_is_on_and_no_other(deck, tmp_path):
    """Row 684 reversed (plan 44 D5d): a turn writes the base of the deck it acts on,
    on air or off, and the deck beside it has its own camera. Plan 55: where the row
    acts is the player's duty (`test_players`)."""
    beside = Deck.beside(deck.deck)
    other = beside.reg["camera.yaw"]
    was = other.base
    Run(deck, tmp_path, closing() + [fist(yaw=float(k)) for k in range(31)] + opening(yaw=30.0),
        steps=deck.undo)
    assert math.degrees(deck.reg["camera.yaw"].base) == pytest.approx(30.0, abs=0.3)
    assert other.base == was and not beside.undo.stack


# ------------------------------------------------------------ with the base chase (plan 52)

def test_an_orbit_starting_under_a_held_chase_leaves_the_verb_on(deck, tmp_path):
    """The chase keeps its step; the orbit lands in it, and a fist ends no verb."""
    assert deck.reg.base_chase(True, steps=deck.undo)
    script = (closing() + [fist(yaw=float(k)) for k in range(21)]
              + opening(yaw=20.0) + [opened(yaw=20.0)] * LONG_OPEN)
    r = Run(deck, tmp_path, script, steps=deck.undo)
    assert deck.reg.chasing
    assert r.yaw[-1] == pytest.approx(20.0, abs=0.3)
    assert _orbits(deck) == []
    deck.reg.base_chase(False)
    deck.undo.undo()
    assert math.degrees(deck.reg["camera.yaw"].base) == pytest.approx(0.0, abs=1e-3)


def test_a_chase_pressed_during_an_orbit_cuts_the_turn_and_the_fist_opening_leaves_the_verb(
        deck, tmp_path):
    n = len(closing()) + 11
    k_open = len(closing()) + 21 + len(opening()) + LONG_OPEN

    def each(io, k):
        if k == n:
            assert deck.reg.base_chase(True, steps=deck.undo)
        if k > k_open:
            assert deck.reg.chasing                     # (c) the fist opening let it be

    script = (closing() + [fist(yaw=float(k)) for k in range(21)]
              + opening(yaw=20.0) + [opened(yaw=20.0)] * (LONG_OPEN + 3))
    r = Run(deck, tmp_path, script, steps=deck.undo, each=each)
    assert r.yaw[-1] == pytest.approx(r.yaw[n], abs=1e-6)        # (b) cut from the press
    assert deck.reg.chasing and deck.undo._kept is not None
    assert _orbits(deck) == ["orbit"]                            # its own, closed by the press
    deck.reg.base_chase(False)
    assert deck.undo._kept is None
