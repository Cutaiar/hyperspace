"""The owner's Joy-Con (L) over Bluetooth (2026-11-02, the probe's full
tape, `tests/fixtures/pads/joycon-poi-excerpt.jsonl`): a real pickup off
the table and a real hold in the hand, through the app's exact path — the
reader's per-report turn on the report clock (`hid.Turn`), the frame's
newest sample, `poi.step`. The first build ran the hand off every screen
in both: the pickup left the attitude 40° off and the hand eight units
out; the hold, with the pad dead still (0.1 deg/s), read a 6° attitude
error as a push for four seconds because "still" was judged from that
very attitude. These hold the fix to the tape."""

import json
import math
from pathlib import Path

from test_poi import FakePad, pan, rig

from hyperspace import poi
from hyperspace.pads import hid, nintendo

HERE = Path(__file__).resolve().parent
TAPE = HERE / "fixtures" / "pads" / "joycon-poi-excerpt.jsonl"
FINDINGS = HERE.parent / "docs" / "plans" / "assets" / "46-joycon" / "joycon-findings.json"
SCREEN = poi.DEFAULT_BOX                  # the rig's TV through the default eye


def tape():
    rows = [json.loads(line) for line in TAPE.read_text().splitlines() if line.strip()]
    assert rows[0]["model"] == "joycon-l" and rows[0]["transport"] == "bluetooth"
    found = json.loads(FINDINGS.read_text())
    records = {int(a, 16): bytes.fromhex(h) for a, h in found["flash"].items()}
    return rows[1:], nintendo.calibration(records, "l")


def replay(rows, cal, **dials):
    """The tape through the app's path, frame by frame: (note, t, state,
    accel in the pad's axes, pan, zoom) after each report's frame."""
    reg, state, _ = rig(**dials)
    reg["poi.on"].set(True)
    state.box = list(SCREEN)
    pad, turn, amap = FakePad(), hid.Turn(), nintendo.AXIS_MAP
    note, last = None, None
    for d in rows:
        if "note" in d:
            note = d["note"]
            continue
        t, r = float(d["t"]), bytes.fromhex(d["r"])
        samples = nintendo.gyro_of(r, None)
        if samples is not None:
            turn.add(samples, t, cal, nintendo.report_clock(r))
        f = nintendo.decode(r, "l", cal)
        if f is None or not f.full:
            continue
        dt = 0.0 if last is None else min(0.25, t - last)
        last = t
        degrees, _n = turn.take()
        pad.motion.add_turn(amap.pick(degrees, amap.gyro))
        accel = amap.pick(cal.accel_g(f.accel), amap.accel)
        pad.motion.step(amap.pick(cal.gyro_dps(f.gyro), amap.gyro), accel, dt, integrate=False)
        poi.step(state, pad, reg, dt)
        yield note, t, state, accel, pan(reg), reg["camera.zoom"].value


def tilt_error(state, accel) -> float:
    """Degrees between the accel through the attitude and the world's up."""
    up = poi._apply(state.att, list(accel))
    n = poi._norm(up) or 1.0
    return math.degrees(math.acos(max(-1.0, min(1.0, up[1] / n))))


def test_the_excerpt_is_the_two_windows_at_the_joycons_rate():
    rows, cal = tape()
    notes = [d["note"] for d in rows if "note" in d]
    assert notes == ["pickup", "hold"]
    assert not cal.nominal
    assert sum(1 for d in rows if "r" in d) > 700          # 13.5 s at ~62 a second


def test_a_real_pickup_and_a_real_hold_keep_the_shape_and_the_hand_on_the_screen():
    rows, cal = tape()
    hx, hy, hz = SCREEN
    for _, _, state, _, (x, y), zoom in replay(rows, cal):
        assert abs(x) <= hx + 1e-6 and abs(y) <= hy + 1e-6
        assert 2.0 ** (-hz * poi.DEPTH_OCTAVES) - 1e-6 <= zoom <= 2.0 ** (hz * poi.DEPTH_OCTAVES) + 1e-6
        assert abs(state.wrist[0]) <= hx + 1e-6 and abs(state.wrist[1]) <= hy + 1e-6


def test_a_real_pickup_lands_within_a_screen_and_leaves_a_quiet_hand():
    """Lifted off the table and held: the hand lands within the picture
    (the first build: eight units, three screens out) and is not still
    moving a second later."""
    rows, cal = tape()
    ends = {}
    for note, _, state, _, _, _ in replay(rows, cal):
        ends[note] = (poi._norm(state.wrist), poi._norm(state.wrist_v))
    travel, speed = ends["pickup"]
    assert travel < 2.0
    assert speed < 0.5


def test_a_dead_still_hold_corrects_the_attitude_and_zeroes_the_hand():
    """The owner's hand at rest with a few degrees of attitude error (the
    four-second dead-lock of the first build): the error is gone, the
    velocity zeroed, the hand quiet, by the end of the window."""
    rows, cal = tape()
    last = None
    for note, _, state, accel, _, _ in replay(rows, cal):
        if note == "hold":
            last = (tilt_error(state, accel), list(state.wrist_v), state.still)
    err, v, still = last
    assert err < 2.0
    assert v == [0.0, 0.0, 0.0] and still >= poi.STILL_S


def test_with_home_off_the_hand_still_stays_on_the_screen():
    rows, cal = tape()
    hx, hy, _ = SCREEN
    for _, _, state, _, (x, y), _ in replay(rows, cal, home=0.0):
        assert state.home == 0.0
        assert abs(x) <= hx + 1e-6 and abs(y) <= hy + 1e-6
