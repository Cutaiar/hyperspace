"""The Ultraleap orbit (plan 51 O2): a clutch and `turn` rows onto the one camera.

Tape-driven through the real route path: hand poses as a real tape file, played
through `TapeSource` and `HandsIO`, the fist read from the skeleton's curls, the
rows run by `Router.modulate`. Nothing here has seen a real sensor (hand checks
517–519).
"""

from __future__ import annotations

import json
import math
from types import SimpleNamespace

import pytest
from fake_hands import hand as fake_hand
from test_hands import make_app, v3
from test_hands_room import FPS, lane, play, pose
from test_undo import boot, settle

from hyperspace import graph as G
from hyperspace import hold as H
from hyperspace import learn, preset, ui_routing, undo
from hyperspace.hands import core as hc
from hyperspace.hands import room as R
from hyperspace.hands import tape as T
from hyperspace.routing import MOD_OPS, TURN_OP, Binding, Owned, is_session_row

YAW, PITCH = "hand:right.room.yaw", "hand:right.room.pitch"
GRAB = "hand:right.grab"
SETTLE_FRAMES = round(hc.GRAB_HOLD_S * FPS) + 2      # a fist held long enough to close


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
    return [R.wrap(b - a) for a, b in zip(seq, seq[1:])]


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
    assert any(math.isnan(v) for v in lanes)                     # the one frame it restarted
    assert sum(math.isnan(v) for v in lanes) <= 2


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


def test_a_row_with_no_gate_turns_whenever_the_hand_is_there(app, tmp_path):
    orbit_rows(app.table, Binding(YAW, "camera.yaw", TURN_OP))
    r = Run(app, tmp_path, [opened(yaw=float(k)) for k in range(31)])
    assert r.yaw[-1] == pytest.approx(30.0, abs=0.2)


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
    assert not is_session_row(row)
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
    assert ui_routing._next_op(room) == "position"
    room.op = "position"
    assert ui_routing._next_op(room) == TURN_OP
    plain = Binding("lane:0", "camera.yaw", "position")
    assert ui_routing._next_op(plain) == "push"
    assert ui_routing.OP_CHIP[TURN_OP] == "turn"


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
              + closing(yaw=30.0) + [fist(yaw=30.0 + k) for k in range(21)]
              + opening(yaw=50.0))
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
              + [fist(yaw=15.0 + k / 2.0) for k in range(31)] + opening(yaw=30.0))
    Run(deck, tmp_path, script, steps=deck.undo)
    assert _orbits(deck) == ["orbit"]


def test_two_rows_turning_together_are_one_step(deck, tmp_path):
    orbit_rows(deck.table, Binding(YAW, "camera.yaw", TURN_OP, when=GRAB),
               Binding(PITCH, "camera.pitch", TURN_OP, when=GRAB))
    settle(deck)
    deck.undo.tick(deck.t)
    script = (closing() + [fist(yaw=float(k), pitch=k / 2.0) for k in range(21)]
              + opening(yaw=20.0, pitch=10.0))
    Run(deck, tmp_path, script, steps=deck.undo)
    assert _orbits(deck) == ["orbit"]


def test_a_closure_that_moved_nothing_leaves_no_step(deck, tmp_path):
    Run(deck, tmp_path, closing() * 2 + opening(), steps=deck.undo)
    assert _orbits(deck) == []


def test_a_lost_hand_closes_the_step(deck, tmp_path):
    script = (closing() + [fist(yaw=float(k)) for k in range(21)] + [None] * 20
              + closing(yaw=20.0) + [fist(yaw=20.0 + k) for k in range(11)] + opening(yaw=30.0))
    Run(deck, tmp_path, script, steps=deck.undo)
    assert _orbits(deck) == ["orbit", "orbit"]


def test_an_undo_with_the_fist_still_closed_stops_the_turn_until_it_opens(deck, tmp_path):
    """The undo is not fought: a closed hand does not run on from what was put
    back, and the next closure turns again, from there."""
    n = len(closing()) + 31

    def each(io, k):
        if k == n:
            deck.undo.undo()

    script = (closing() + [fist(yaw=float(k)) for k in range(31)]
              + [fist(yaw=30.0 + k) for k in range(30)]                # still turning
              + opening(yaw=60.0)
              + closing(yaw=60.0) + [fist(yaw=60.0 + k) for k in range(11)] + opening(yaw=70.0))
    r = Run(deck, tmp_path, script, steps=deck.undo, each=each)
    assert r.yaw[n + 1] == pytest.approx(0.0, abs=1e-3)
    assert all(v == pytest.approx(0.0, abs=1e-3) for v in r.yaw[n + 1:n + 30])
    assert r.yaw[-1] == pytest.approx(10.0, abs=0.3)
    assert _orbits(deck) == ["orbit"]                                  # the second; the first redoable
    assert len(deck.undo.redos) == 0                                   # a new edit clears the redo


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
    path = deck.presets.save_as("ORBIT")
    doc = json.loads(path.read_text())
    assert doc["schema"].endswith("/10")                  # no schema move
    assert doc["values"]["camera.yaw"] == pytest.approx(math.radians(30.0), abs=0.01)
    assert {"source": YAW, "target": "camera.yaw", "op": TURN_OP, "when": GRAB}.items() <= next(
        r for r in doc["routes"] if r["target"] == "camera.yaw").items()
    deck.reg["camera.yaw"].set(0.0)
    orbit_rows(deck.table, Binding(PITCH, "camera.pitch", "position"))
    assert deck.presets.load("ORBIT") == []
    assert deck.table.owner("camera.yaw").op == TURN_OP
    assert deck.reg["camera.yaw"].base == pytest.approx(math.radians(30.0), abs=0.01)


def test_what_an_older_build_does_with_the_row(deck, tmp_path, monkeypatch):
    """An older build's `MOD_OPS` has no turn: the row goes with a note, the rest
    of the file lands, and nothing is refused. So no schema move (row 683)."""
    deck.reg["camera.pitch"].set(0.5)
    deck.presets.save_as("ORBIT")
    monkeypatch.setattr(preset, "MOD_OPS", ("push", "position"))
    deck.presets.load("ORBIT")
    notes = deck.presets.notes
    assert any("(turn): not a performer row" in n for n in notes)
    assert deck.table.owner("camera.yaw") is None
    assert deck.reg["camera.pitch"].base == pytest.approx(0.5)


def _hold(deck):
    deck.renderer = SimpleNamespace(wiring=G.EMPTY, ghost_states={}, rig_source=deck.presets)
    deck.presets.graph.attach(deck.renderer)
    hold = H.Hold(deck.reg, deck.renderer, undo=deck.undo, section=deck.presets.graph)
    settle(deck)
    return hold


def test_under_the_hold_it_moves_the_preview_as_a_knob_would(deck, tmp_path):
    """The base is the operator's side: the projector keeps the held camera."""
    hold = _hold(deck)
    assert hold.engage(deck.t)
    Run(deck, tmp_path, closing() + [fist(yaw=float(k)) for k in range(31)] + opening(yaw=30.0),
        steps=deck.undo)
    yaw = deck.reg["camera.yaw"]
    assert math.degrees(yaw.base) == pytest.approx(30.0, abs=0.3)
    with hold.program():
        assert yaw.value == pytest.approx(0.0, abs=1e-6)
    assert "camera.yaw" in hold.changed()


def test_engaging_the_hold_mid_orbit_cuts_it_with_the_step_closed(deck, tmp_path):
    hold = _hold(deck)
    n = len(closing()) + 21

    def each(io, k):
        if k == n:
            assert hold.engage(deck.t)

    script = closing() + [fist(yaw=float(k)) for k in range(41)]
    r = Run(deck, tmp_path, script, steps=deck.undo, each=each)
    assert r.yaw[-1] == pytest.approx(r.yaw[n])              # cut until the fist opens
    assert deck.undo._kept is None
