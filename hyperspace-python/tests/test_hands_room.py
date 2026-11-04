"""The room lanes (plan 51, hands/room.py): the palm's orientation in the
room's frame, whatever the sensor's mount and whatever the camera does.

The proof is tape-driven: hand poses written as a real tape file, played
through `TapeSource` and `HandsIO` the way `[hands] tape` plays one. Nothing
here has seen a real sensor (hand checks 514–516).
"""

from __future__ import annotations

import json
import math
import random
from types import SimpleNamespace as NS

import numpy as np
import pytest
from test_hands import Clock, FakeOut, _frame, hand, make_app

from hyperspace import ghost
from hyperspace import hands as H
from hyperspace.hands import HandSettings, HandsIO
from hyperspace.hands import core as hc
from hyperspace.hands import room as R
from hyperspace.hands import tape as T
from hyperspace.routing import Binding

FPS = 90.0
UP_AWAY = ((0.0, -1.0, 0.0), (0.0, 0.0, -1.0))        # level: palm down, fingers away


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def pose(roll=0.0, pitch=0.0, yaw=0.0, sensor=None):
    """(normal, direction) of a palm at these room angles, degrees; `sensor`
    is Leap → room (a mode's basis, a tilted mount), default the identity."""
    r = _ry(math.radians(yaw)) @ _rx(math.radians(pitch)) @ _rz(math.radians(roll))
    if sensor is not None:
        r = np.asarray(sensor).T @ r
    return tuple(-r[:, 1]), tuple(-r[:, 2])


def write_tape(path, poses, side="right", mode="desktop", at=(40.0, 200.0, 0.0)):
    """Poses as a tape on disk, one a frame at FPS; None is a frame with no
    hand. Each frame holds the features and skeleton a live hand gives."""
    frames = []
    for k, p in enumerate(poses):
        hands = {}
        if p is not None:
            h = hand(side, pos=at, normal=p[0], direction=p[1])
            hands[side] = {"features": hc.features(h), "confidence": 1.0,
                           "skeleton": hc.skeleton(h)}
        frames.append({"t": k / FPS, "hands": hands})
    T.save({"schema": T.TAPE_SCHEMA, "mode": mode, "frames": frames}, path)
    return path


def play(path, *, smooth=1e6, response=0.0, cal=None, router=None, each=None, **cfg):
    """A tape through `HandsIO`, a poll a frame; the list of `lanes()`. The
    default filter passes through: a test that wants it turns it on."""
    clock = Clock()
    src = T.TapeSource(path, clock, loop=False)
    settings = HandSettings.from_config(cfg)
    settings.smooth, settings.response = smooth, response
    io = HandsIO(settings, cfg, source=src, out=FakeOut(), clock=clock, cal_path=cal)
    clock.t = 0.5 / FPS
    out = []
    for k in range(len(src.frames)):
        io.poll(1.0 / FPS, None, router)
        out.append(list(io.lanes()))
        if each is not None:
            each(io, k)
        clock.t += 1.0 / FPS
    return NS(io=io, lanes=out, clock=clock)


def lane(run, name):
    return [row[run.io.layout.index[name]] for row in run.lanes]


def deg(v):
    return (v - 0.5) * 360.0


def turned(a, b):
    """Shortest difference between two lane values, in degrees."""
    return R.wrap((a - b) * 360.0)


# ------------------------------------------------------------ the frame

def test_a_level_palm_reads_level_on_every_lane(tmp_path):
    run = play(write_tape(tmp_path / "t.json", [UP_AWAY] * 3))
    for k in R.ROOM:
        assert lane(run, f"right.room.{k}")[-1] == pytest.approx(0.5, abs=1e-3)


@pytest.mark.parametrize("name,kw", [("yaw", {"yaw": 30.0}), ("pitch", {"pitch": 30.0}),
                                     ("roll", {"roll": 30.0})])
def test_each_lane_reads_its_own_turn_and_only_that(tmp_path, name, kw):
    run = play(write_tape(tmp_path / "t.json", [pose(**kw)] * 3))
    for k in R.ROOM:
        want = 30.0 if k == name else 0.0
        assert deg(lane(run, f"right.room.{k}")[-1]) == pytest.approx(want, abs=0.05)


def test_the_signs_are_the_rooms_as_the_table_says():
    """Fingers swinging left is +yaw, rising +pitch; the palm's right side
    rising +roll: spelled in raw vectors, with no helper's convention."""
    s = math.sqrt(0.5)
    m = R.MODES["desktop"]
    read = lambda n, d: R.angles(R.palm_axes(n, d, m))
    roll, pitch, yaw, _ = read((0.0, -1.0, 0.0), (-s, 0.0, -s))     # fingers front-left
    assert yaw == pytest.approx(45.0) and roll == pytest.approx(0.0, abs=1e-9)
    roll, pitch, yaw, _ = read((0.0, -s, -s), (0.0, s, -s))         # fingers up-front
    assert pitch == pytest.approx(45.0) and yaw == pytest.approx(0.0, abs=1e-9)
    roll, pitch, yaw, _ = read((s, -s, 0.0), (0.0, 0.0, -1.0))      # the normal leans right
    assert roll == pytest.approx(45.0) and pitch == pytest.approx(0.0, abs=1e-9)


def test_the_two_hands_read_alike_not_mirrored(tmp_path):
    """The anatomical axes mirror: this is what the room lanes do instead."""
    p = pose(roll=25.0, pitch=-15.0, yaw=40.0)
    l = play(write_tape(tmp_path / "l.json", [p] * 3, side="left"))
    r = play(write_tape(tmp_path / "r.json", [p] * 3, side="right"))
    for k in R.ROOM:
        assert (lane(l, f"left.room.{k}")[-1]
                == pytest.approx(lane(r, f"right.room.{k}")[-1], abs=1e-4))


@pytest.mark.parametrize("mode", sorted(R.MODES))
def test_the_same_pose_in_the_room_reads_the_same_from_every_mount(tmp_path, mode):
    """The sensor's frame is taken out: hung, on a table or on a head."""
    p = pose(roll=25.0, pitch=-15.0, yaw=40.0, sensor=R.MODES[mode])
    run = play(write_tape(tmp_path / "t.json", [p] * 3, mode=mode), mode=mode)
    got = [deg(lane(run, f"right.room.{k}")[-1]) for k in R.ROOM]
    assert got == pytest.approx([25.0, -15.0, 40.0], abs=0.05)


def test_the_mode_table_is_the_ghosts():
    """A copy, because the instrument imports nothing from the host."""
    assert R.MODES == ghost.MODES


def test_nothing_of_the_camera_reaches_the_lanes(tmp_path):
    """An orbit, written to the camera between frames, moves no lane."""
    app = make_app(tmp_path)
    path = write_tape(tmp_path / "t.json", [pose(roll=20.0, yaw=30.0)] * 6)
    still = play(path, router=app.router)

    def orbit(io, k):
        app.reg["camera.yaw"].set(0.5 * k)
        app.reg["camera.pitch"].set(-0.3 * k)
        app.reg["camera.zoom"].set(1.0 + k)
        _frame(app)

    orbiting = play(path, router=app.router, each=orbit)
    assert app.reg["camera.yaw"].value != 0.0
    assert orbiting.lanes == still.lanes


def test_every_angle_reads_back_through_the_plain_reading():
    rng = random.Random(51)
    m = R.MODES["desktop"]
    for _ in range(300):
        want = (rng.uniform(-179, 179), rng.uniform(-80, 80), rng.uniform(-179, 179))
        n, d = pose(*want)
        assert R.angles(R.palm_axes(n, d, m))[:3] == pytest.approx(want, abs=1e-6)


# ------------------------------------------------------------ wrap at ±180°

def test_a_full_turn_of_yaw_crosses_the_seam_in_one_frame_and_never_sweeps(tmp_path):
    """Two whole turns, past ±180° twice, with the filter on."""
    poses = [pose(yaw=90.0 + 4.0 * k) for k in range(180)]
    run = play(write_tape(tmp_path / "t.json", poses), smooth=1.0, response=4.0)
    y = lane(run, "right.room.yaw")
    assert all(0.0 <= v < 1.0 for v in y)
    jumps = [k for k in range(1, len(y)) if abs(y[k] - y[k - 1]) > 0.5]
    assert len(jumps) == 2                                  # a seam a turn, each one frame
    for k in range(1, len(y)):
        assert 0.0 <= turned(y[k], y[k - 1]) < 8.0          # always onward, no sweep back
    assert turned(y[-1], 0.5 + R.wrap(90.0 + 4.0 * 179) / 360.0) == pytest.approx(0.0, abs=10.0)


def test_a_palm_held_on_the_seam_never_reads_the_middle_of_the_lane(tmp_path):
    """Roll held at the seam: a palm turned up, shaking across ±180° on a
    real hand's jitter. Filtered wrapped, it would read the middle of the lane."""
    poses = [pose(roll=180.0 + (1.0 if k % 2 else -1.0)) for k in range(60)]
    run = play(write_tape(tmp_path / "t.json", poses), smooth=1.0, response=4.0)
    y = lane(run, "right.room.roll")
    assert all(v < 0.02 or v > 0.98 for v in y)


def test_over_the_top_no_lane_flips(tmp_path):
    """Fingers up and past vertical: the plain reading flips yaw and roll by
    180°. Here pitch runs on past 90° and they stay."""
    poses = [pose(yaw=20.0, pitch=2.0 * k) for k in range(70)]         # to 138°
    run = play(write_tape(tmp_path / "t.json", poses))
    yaw, pitch, roll = (lane(run, f"right.room.{k}") for k in ("yaw", "pitch", "roll"))
    assert all(deg(v) == pytest.approx(20.0, abs=0.1) for v in yaw)
    assert all(deg(v) == pytest.approx(0.0, abs=0.1) for v in roll)
    assert deg(pitch[-1]) == pytest.approx(138.0, abs=0.1)
    assert all(turned(pitch[k], pitch[k - 1]) == pytest.approx(2.0, abs=0.1)
               for k in range(1, len(pitch)))


def test_inside_the_poles_cone_yaw_holds_and_roll_carries_the_twist(tmp_path):
    """Fingers straight up, the hand twisting about them."""
    poses = [pose(yaw=10.0, pitch=2.0 * k) for k in range(45)]        # up to vertical
    poses += [pose(yaw=10.0, pitch=90.0, roll=2.0 * k) for k in range(30)]
    seen = []
    run = play(write_tape(tmp_path / "t.json", poses),
               each=lambda io, k: seen.append(io.room["right"].pole))
    yaw, roll = lane(run, "right.room.yaw"), lane(run, "right.room.roll")
    assert seen[-1] and not seen[0]
    assert all(deg(v) == pytest.approx(10.0, abs=0.1) for v in yaw)
    assert deg(roll[-1]) == pytest.approx(58.0, abs=0.2)


# ------------------------------------------------------------ a lost hand

def test_a_lost_hand_reads_nan_that_frame_and_returns_with_no_glide(tmp_path):
    poses = [pose(yaw=-120.0)] * 20 + [None] * 3 + [pose(yaw=150.0)] * 3
    run = play(write_tape(tmp_path / "t.json", poses), smooth=1.0, response=4.0)
    y = lane(run, "right.room.yaw")
    assert deg(y[19]) == pytest.approx(-120.0, abs=0.1)
    assert all(math.isnan(v) for v in y[20:23])
    assert deg(y[23]) == pytest.approx(150.0, abs=0.1)      # at once: no way round the circle


def test_a_hand_the_box_keeps_out_is_lost_too(tmp_path):
    cal = tmp_path / "hands.json"
    cal.write_text(json.dumps({"schema": hc.CAL_SCHEMA, "axes": {},
                               "box": {"x": [-500.0, 0.0], "y": None, "z": None}}))
    run = play(write_tape(tmp_path / "t.json", [UP_AWAY] * 3), cal=cal)
    assert run.io.box is not None
    assert all(math.isnan(v) for v in lane(run, "right.room.yaw"))


def test_a_source_with_no_skeleton_reads_nan_and_the_other_axes_still_run(tmp_path):
    """As the curls do: the features hold only the anatomical angles."""
    path = write_tape(tmp_path / "t.json", [UP_AWAY] * 3)
    tape = json.loads(path.read_text())
    for f in tape["frames"]:
        f["hands"]["right"]["skeleton"] = None
    path.write_text(json.dumps(tape))
    run = play(path)
    assert all(math.isnan(v) for v in lane(run, "right.room.roll"))
    assert lane(run, "right.roll")[-1] == pytest.approx(0.5, abs=1e-3)


def test_vectors_that_give_no_frame_read_nan_not_a_guess(tmp_path):
    m = R.MODES["desktop"]
    assert R.palm_axes((0.0, 0.0, 0.0), (0.0, 0.0, -1.0), m) is None
    assert R.palm_axes((0.0, -1.0, 0.0), (0.0, 0.0, 0.0), m) is None
    assert R.palm_axes((0.0, 0.0, -1.0), (0.0, 0.0, -1.0), m) is None       # parallel
    assert R.palm_axes((math.nan, -1.0, 0.0), (0.0, 0.0, -1.0), m) is None
    assert R.palm_axes((0.0, -1.0, 0.0), (math.inf, 0.0, -1.0), m) is None
    run = play(write_tape(tmp_path / "t.json", [((0.0, 0.0, -1.0), (0.0, 0.0, -1.0))] * 2))
    assert all(math.isnan(v) for v in lane(run, "right.room.yaw"))


# ------------------------------------------------------------ calibration

def _tilted():
    """A Leap on a wedge, 20° up and 15° round: Leap → room."""
    return _ry(math.radians(15.0)) @ _rx(math.radians(20.0))


def _level(tmp_path, sensor, seconds=0.5):
    """Level on a flat palm seen through `sensor`, then read a turned one."""
    flat = pose(sensor=sensor)
    turned_palm = pose(roll=25.0, pitch=-15.0, yaw=40.0, sensor=sensor)
    n = int(FPS * seconds) + 8
    path = write_tape(tmp_path / "t.json", [flat] * n + [turned_palm] * 3)
    cal = tmp_path / "hands.json"

    def start(io, k):
        if k == 0:
            io.start_level(seconds)

    return play(path, cal=cal, each=start), cal


def test_levelling_makes_a_tilted_mount_read_as_a_level_one(tmp_path):
    run, _ = _level(tmp_path, _tilted())
    got = [deg(lane(run, f"right.room.{k}")[-1]) for k in R.ROOM]
    assert got == pytest.approx([25.0, -15.0, 40.0], abs=0.1)
    assert "levelled" in run.io.cal_note
    assert run.io.levelling == 0.0


def test_a_tilted_mount_unlevelled_reads_the_tilt(tmp_path):
    """What the levelling is for: without it, the wedge is in the reading."""
    run = play(write_tape(tmp_path / "t.json", [pose(sensor=_tilted())] * 3))
    assert abs(deg(lane(run, "right.room.pitch")[-1])) > 5.0


def test_the_levelling_is_saved_and_read_back_and_cleared(tmp_path):
    _, cal = _level(tmp_path, _tilted())
    raw = json.loads(cal.read_text())
    assert raw["schema"] == hc.CAL_SCHEMA == "hyperspace.hands/3"       # no schema move
    again = play(write_tape(tmp_path / "again.json",
                            [pose(roll=25.0, pitch=-15.0, yaw=40.0, sensor=_tilted())] * 3),
                 cal=cal)
    got = [deg(lane(again, f"right.room.{k}")[-1]) for k in R.ROOM]
    assert got == pytest.approx([25.0, -15.0, 40.0], abs=0.1)
    again.io.clear_level()
    assert again.io.level is None and "room" not in json.loads(cal.read_text())


def test_an_unlevelled_file_is_written_as_it_was(tmp_path):
    """No key, so a build from before and this one write the same bytes."""
    cal = tmp_path / "hands.json"
    run = play(write_tape(tmp_path / "t.json", [UP_AWAY] * 2), cal=cal)
    run.io.save_ranges()
    assert set(json.loads(cal.read_text())) == {"schema", "axes", "box", "units"}


def test_too_few_frames_leave_the_room_as_it_was(tmp_path):
    cal = tmp_path / "hands.json"

    def start(io, k):
        if k == 0:
            io.start_level(0.05)

    run = play(write_tape(tmp_path / "t.json", [UP_AWAY] * 10), cal=cal, each=start)
    assert run.io.level is None and "left as it was" in run.io.cal_note
    assert not cal.exists()


@pytest.mark.parametrize("bad", ["yes", [1, 2, 3], [[1, 0, 0], [0, 1, 0]],
                                 [[2, 0, 0], [0, 1, 0], [0, 0, 1]],
                                 [[1, 0, 0], [0, 1, 0], [0, 0, -1]],     # a mirror
                                 [[1, 0, 0], [0, 1, 0], [0, 0, "x"]]])
def test_a_bad_room_entry_is_ignored_and_said(tmp_path, capsys, bad):
    cal = tmp_path / "hands.json"
    cal.write_text(json.dumps({"schema": hc.CAL_SCHEMA, "axes": {}, "room": bad}))
    assert hc.load_room(cal) is None
    assert "room" in capsys.readouterr().err


def test_a_file_from_before_has_no_room_and_null_is_none(tmp_path):
    cal = tmp_path / "hands.json"
    assert hc.load_room(None) is None and hc.load_room(cal) is None
    cal.write_text(json.dumps({"schema": "hyperspace.hands/2", "axes": {}}))
    assert hc.load_room(cal) is None
    cal.write_text(json.dumps({"schema": hc.CAL_SCHEMA, "axes": {}, "room": None}))
    assert hc.load_room(cal) is None


# ---------------------------------------------------- the layout, and use

def test_every_older_lane_stays_where_it_was():
    """A row saved by number still reads the same lane: these come last."""
    names = H.default_addresses()
    assert names[:40] == [
        *(f"{s}.{a}" for s in H.SIDES for a in H.DEFAULTS["dofs"]),
        *(f"{s}.present" for s in H.SIDES),
        *(f"{s}.pinch.{f}" for s in H.SIDES for f in H.PINCHES),
        *(f"{s}.{k}" for s in H.SIDES for k in H.DANCE),
        *(f"{s}.grab" for s in H.SIDES)]
    assert names[40:] == [f"{s}.room.{k}" for s in H.SIDES for k in H.ROOM]
    lay = hc.Layout(HandSettings.from_config({}).axes)
    assert lay.n == 46 == len(lay.names) and lay.names[40] == "L room roll"


def test_the_lanes_rest_level_and_the_older_rests_do_not_move(tmp_path):
    run = play(write_tape(tmp_path / "t.json", [UP_AWAY]))
    rests, lay = run.io.rests(), run.io.layout
    assert [rests[i] for i in lay.room.values()] == [0.5] * 6
    assert rests[lay.grab["right"]] == 0.0


def test_the_device_offers_them_as_ports_of_their_own_group(tmp_path):
    from hyperspace.hands.device import HandsDevice

    run = play(write_tape(tmp_path / "t.json", [UP_AWAY]))
    dev = HandsDevice("hands", {}, None, io=run.io)
    room = [p for p in dev.sources if p.group == "room"]
    assert [p.name for p in room] == [f"{s}.room.{k}" for s in H.SIDES for k in H.ROOM]
    assert all(p.bipolar and p.rest == 0.5 and p.scheme == "hand" for p in room)


def test_the_hands_page_draws_the_room_row_and_the_level_line(tmp_path, monkeypatch):
    """Through the real panel, "feel & calibration" open: the level line in
    each of its three states. No click: the button's work is `start_level`."""
    from imgui_bundle import imgui
    from test_ui_shell import build_rig, frame

    import hyperspace.hands.panel as hp
    from hyperspace.app import CONTROL_SIZE

    with build_rig(tmp_path) as rig:
        run = play(write_tape(tmp_path / "t.json", [UP_AWAY] * 3))
        rig.panel.hands = run.io
        imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
        calls = []
        real = hp._level
        monkeypatch.setattr(hp.imgui, "collapsing_header", lambda *a, **k: True)
        monkeypatch.setattr(hp, "_level", lambda io: (calls.append(io), real(io)))
        for _ in range(2):
            frame(rig.panel, "hands")
        assert calls and calls[-1] is run.io
        run.io.start_level(60.0)
        assert run.io.levelling > 0.0
        frame(rig.panel, "hands")           # the "hold one hand flat" line, no button
        run.io.level = R.MODES["desktop"]
        run.io._level_seen = None
        frame(rig.panel, "hands")           # the "clear" line


def test_a_hot_reloaded_handsio_makes_its_room_state(tmp_path):
    """A HandsIO from before the reload has none of it; its first poll does."""
    clock = Clock()
    src = T.TapeSource(write_tape(tmp_path / "t.json", [UP_AWAY] * 4), clock, loop=False)
    settings = HandSettings.from_config({})
    io = HandsIO(settings, {}, source=src, out=FakeOut(), clock=clock)
    for k in ("room", "level", "_level_seen", "_level_until"):
        delattr(io, k)
    old = hc.Layout.__new__(hc.Layout)
    old.pair_index, old.grab = {}, {}
    io.layout = old
    clock.t = 0.5 / FPS
    io.poll(1.0 / FPS)
    assert io.lanes()[io.layout.room[("right", "yaw")]] == pytest.approx(0.5, abs=1e-3)
    assert io.levelling == 0.0


def test_a_route_turns_the_one_camera_one_for_one_across_the_seam(tmp_path):
    """What O2 builds on: a position row onto the wrapping `camera.yaw`, depth
    1 — the palm's angle is the camera's, and the seam lands where it left."""
    app = make_app(tmp_path)
    app.table.add(Binding("hand:right.room.yaw", "camera.yaw", "position"))
    yaw = app.reg["camera.yaw"]
    yaw.set(0.0)
    want = [170.0 + k for k in range(21)]                  # 170° … 190°, through the seam
    path = write_tape(tmp_path / "t.json", [pose(yaw=a) for a in want])
    seen = []

    def each(io, k):
        _frame(app)
        seen.append(math.degrees(yaw.value))

    play(path, router=app.router, each=each)
    for got, a in zip(seen, want):
        assert R.wrap(got - a) == pytest.approx(0.0, abs=0.2)
    assert yaw.base == pytest.approx(0.0)                   # the row never wrote the base


def test_a_real_tape_plays_room_lanes_when_there_is_one():
    """Every recorded tape under tests/fixtures/hands/ (none yet from a real
    sensor): the lanes stay on the circle, or NaN with a hand away."""
    from pathlib import Path

    tapes = sorted((Path(__file__).parent / "fixtures" / "hands").glob("*.json"))
    for path in tapes:
        run = play(path)
        for s in H.SIDES:
            for k in H.ROOM:
                assert all(math.isnan(v) or 0.0 <= v < 1.0 for v in lane(run, f"{s}.room.{k}"))
