"""A real DualSense Edge, over Bluetooth on macOS (2026-11-02): a slice of
the probe's tape (`tests/fixtures/pads/edge-bt-excerpt.jsonl`, half a
second of each step, a second of the touch sweep) decoded and turned into
lanes exactly as the app does. The first test bytes from the hardware
itself; the findings it came with are in
docs/plans/assets/42-controllers/edge-bt.json."""

import json
from pathlib import Path

from hyperspace.pads import gesture, models, sony

TAPE = Path(__file__).resolve().parent / "fixtures" / "pads" / "edge-bt-excerpt.jsonl"
NAMES = {i: n for n, i in models.CANON.items()}


def windows() -> dict[str, list[tuple[float, bytes]]]:
    rows = [json.loads(line) for line in TAPE.read_text().splitlines()]
    assert rows[0] == {"tape": "hyperspace.padtape/1", "model": "edge", "transport": "bluetooth"}
    out: dict[str, list] = {}
    name = None
    for d in rows[1:]:
        if "note" in d:
            name = d["note"]
            out[name] = []
        else:
            out[name].append((d["t"], bytes.fromhex(d["r"])))
    return out


def test_every_report_is_a_full_bluetooth_report_with_a_good_crc():
    for name, reports in windows().items():
        assert len(reports) >= 25, name                    # ~64 a second over Bluetooth
        for _, r in reports:
            f = sony.decode(r, bluetooth=True)
            assert f is not None and f.kind == sony.BT_IN and sony.bt_crc_ok(r), name


def held(name: str) -> set[str]:
    reports = windows()[name]
    frames = [sony.decode(r, bluetooth=True) for _, r in reports]
    return {NAMES[i] for i in NAMES if all(f.buttons[i] for f in frames)}


def test_the_back_buttons_report_their_own_bits():
    assert held("still") == set()
    assert held("left back") == {"LP"}
    assert held("right back") == {"RP"}


def motion(name: str) -> dict[str, float]:
    """The motion lanes at the end of a step, the reports replayed in time
    through the nominal calibration (the tape holds no feature report)."""
    m, cal, last = gesture.Motion(), sony.Calibration(), None
    for t, r in windows()[name]:
        f = sony.decode(r, bluetooth=True)
        m.step(cal.gyro_dps(f.gyro), cal.accel_g(f.accel), 0.0 if last is None else t - last)
        last = t
    return dict(zip(gesture.MOTION_LANES, m.lanes(), strict=True))


def test_tilt_and_turn_read_the_way_the_lanes_say():
    assert motion("right down")["roll"] > 0.65              # right side down: roll high
    assert motion("far up")["pitch"] > 0.65                 # far edge up: pitch high
    turn = motion("turn right")
    assert turn["spin.yaw"] > 0.52 and turn["yaw"] > 0.5    # turning right: yaw high


def test_the_touchpad_reaches_its_documented_size():
    seen = [t for _, r in windows()["touch reach"]
            for t in sony.decode(r, bluetooth=True).touches if t.down]
    assert seen
    assert all(0 <= t.x < sony.TOUCH_W and 0 <= t.y < sony.TOUCH_H for t in seen)
