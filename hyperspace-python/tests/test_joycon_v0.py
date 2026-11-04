"""Version 0 of the Joy-Con (the owner, 2026-11-04): the gyro and shake,
nothing driving the shape's position. Real moves from the owner's two tapes
(`tests/fixtures/pads/joycon-v0-moves.jsonl`): a rest, a pickup off the table,
a carry, a sword swing, thrusts, standing up and sitting down.

The shakes here are simulated: neither tape holds a deliberate shake, so the
firing side still has to be judged on the real pad (hand check 521)."""

import itertools
import json
import math
import random
from pathlib import Path

import pytest
from test_totem import DT, FakePad, phase
from test_totem import rig as totem_rig

from hyperspace import totem
from hyperspace.pads import gesture, hid, nintendo

HERE = Path(__file__).resolve().parent
TAPE = HERE / "fixtures" / "pads" / "joycon-v0-moves.jsonl"
FINDINGS = HERE.parent / "docs" / "plans" / "assets" / "46-joycon" / "joycon-findings.json"
amap = nintendo.AXIS_MAP


def calibration(offset_counts=0):
    found = json.loads(FINDINGS.read_text())
    records = {int(a, 16): bytes.fromhex(h) for a, h in found["flash"].items()}
    cal = nintendo.calibration(records, "l")
    if offset_counts:     # a pad whose rest reads off: the flash's origin is that far wrong
        gyro = tuple((o - offset_counts, s) for o, s in cal.gyro)
        cal = nintendo.Calibration(cal.left, cal.right, gyro, cal.accel, cal.nominal, cal.user_stick)
    return cal


def windows():
    rows = [json.loads(ln) for ln in TAPE.read_text().splitlines() if ln.strip()]
    out, name = {}, None
    for d in rows[1:]:
        if "note" in d:
            name = d["note"]
            out[name] = []
        else:
            out[name].append((d["t"], bytes.fromhex(d["r"])))
    return out


def turned(reports, cal, turn=None):
    """The reader's turn over `reports`, degrees about the sensor's axes."""
    turn = turn or hid.Turn()
    total = [0.0, 0.0, 0.0]
    for t, r in reports:
        samples = nintendo.gyro_of(r, None)
        if samples is not None:
            turn.add(samples, t, cal, nintendo.report_clock(r))
        got, _ = turn.take()
        total = [a + b for a, b in zip(total, got, strict=True)]
    return total, turn


def shakes_of(reports, cal):
    """The frames the shake lane fires over `reports`, as the app reads them."""
    m, last, fired = gesture.Motion(), None, []
    for t, r in reports:
        f = nintendo.decode(r, "l", cal)
        if f is None or not f.full:
            continue
        dt = 0.0 if last is None else min(0.25, t - last)
        last = t
        m.step(amap.pick(cal.gyro_dps(f.gyro), amap.gyro), amap.pick(cal.accel_g(f.accel), amap.accel), dt)
        if m.shake:
            fired.append(t)
    return fired


def shaken(hz=6.0, g=1.5, seconds=2.0, drop=0.0, axis=0):
    """Fires of a simulated shake at the Joy-Con's report rate."""
    rnd = random.Random(1)
    m, last, t, fired = gesture.Motion(), 0.0, 0.0, []
    while t < seconds:
        if rnd.random() >= drop:
            a = [0.0, 1.0, 0.0]
            a[axis] += g * math.sin(2 * math.pi * hz * t)
            m.step((0.0, 0.0, 0.0), a, t - last)
            last = t
            if m.shake:
                fired.append(t)
        t += 0.015
    return fired


@pytest.mark.parametrize("move", ["rest", "pickup", "carry", "swing", "thrust", "stand up", "sit down"])
def test_real_moves_that_are_not_a_shake_never_fire_it(move):
    assert shakes_of(windows()[move], calibration()) == []


@pytest.mark.parametrize(("hz", "g", "drop"), [(3, 1.5, 0.0), (6, 1.5, 0.0), (8, 2.0, 0.0),
                                               (6, 1.5, 0.15), (6, 1.5, 0.3)])
def test_a_shake_fires_soon_and_keeps_firing_even_with_reports_lost(hz, g, drop):
    fired = shaken(hz, g, drop=drop)
    assert fired and fired[0] < 1.0
    assert len(fired) >= 3
    assert all(b - a >= gesture.SHAKE_GAP_S - 1e-9 for a, b in itertools.pairwise(fired))


def test_one_jolt_is_not_a_shake():
    m = gesture.Motion()
    for i in range(60):
        push = 3.0 if 20 <= i < 24 else 0.0
        m.step((0.0, 0.0, 0.0), (push, 1.0, 0.0), DT)
        assert m.shake == 0.0


def test_a_shake_is_one_frame_long():
    m, seen = gesture.Motion(), []
    for i in range(120):
        m.step((0.0, 0.0, 0.0), (1.5 * math.sin(2 * math.pi * 6 * i * 0.015), 1.0, 0.0), 0.015)
        seen.append(m.shake)
    assert 1.0 in seen
    assert all(not (a and b) for a, b in itertools.pairwise(seen))


def test_a_real_rest_turns_nothing():
    total, _ = turned(windows()["rest"], calibration())
    assert max(abs(v) for v in total) < 0.01


def test_the_rest_measures_this_pads_small_offset():
    _, turn = turned(windows()["rest"], calibration())
    assert 0.05 < abs(turn.offset[0]) + abs(turn.offset[1]) + abs(turn.offset[2]) < 1.0


def test_a_pad_whose_rest_reads_past_the_dead_band_stops_turning_within_seconds():
    """Rest read 8 deg/s off, far past the 3 deg/s band: unlearned, the shape
    would spin at that rate for ever."""
    counts = round(8.0 / 0.061)
    reports = windows()["rest"]
    cal = calibration(counts)
    first_s = reports[0][0] + 3.0
    early, turn = turned([x for x in reports if x[0] <= first_s], cal)
    assert max(abs(v) for v in early) < 30.0                     # the seconds before it is learned
    late, turn = turned([x for x in reports if x[0] > first_s], cal, turn)
    assert max(abs(v) for v in late) < 0.05                      # the rest of the rest: nothing
    assert max(abs(v) for v in turn.offset) == pytest.approx(8.0, abs=0.5)


def test_a_real_moving_hand_is_never_learned_as_an_offset():
    for move in ("carry", "swing", "thrust"):
        reports = windows()[move]
        turn = hid.Turn()
        before = None
        for t, r in reports:
            samples = nintendo.gyro_of(r, None)
            if samples is not None:
                turn.add(samples, t, calibration(), nintendo.report_clock(r))
            if max(abs(v) for v in turn.offset) > 1.0:
                before = t
        assert before is None, move


def test_version_0_moves_nothing_but_the_turn():
    """A tilted, flung pad: the totem turns the shape and the pan stays put."""
    reg, state, _ = totem_rig()
    state.pan = totem.TotemState().pan                            # the real default
    assert state.pan is False and reg["totem.pan"].value is False
    pad = FakePad()
    reg["totem.on"].set(True)
    for i in range(100):
        pad.frame(gyro=(0.0, 0.0, 90.0), accel=(2.0 * math.sin(i), 1.0, -1.0))
        totem.step(state, pad, reg, DT)
    assert reg["camera.pan.x"].value == 0.0 and reg["camera.pan.y"].value == 0.0
    assert abs(phase(reg, "XY")) > 1.0
