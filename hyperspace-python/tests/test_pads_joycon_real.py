"""A real Joy-Con (L), over Bluetooth on macOS (2026-11-02, the owner's):
half a second of each of the probe's steps
(`tests/fixtures/pads/joycon-bt-excerpt.jsonl`, cut by
`tools/pad_tape_excerpt.py`) decoded through the calibration its flash
gave (`docs/plans/assets/46-joycon/joycon-findings.json`) and turned into
lanes exactly as the app does. The first test bytes from the hardware
itself; hand check 425."""

import json
from pathlib import Path

from hyperspace.pads import gesture, models, nintendo, sony

HERE = Path(__file__).resolve().parent
TAPE = HERE / "fixtures" / "pads" / "joycon-bt-excerpt.jsonl"
FINDINGS = HERE.parent / "docs" / "plans" / "assets" / "46-joycon" / "joycon-findings.json"
NAMES = {i: n for n, i in models.CANON.items()}


def windows() -> dict[str, list[tuple[float, bytes]]]:
    rows = [json.loads(line) for line in TAPE.read_text().splitlines()]
    assert rows[0] == {"tape": "hyperspace.padtape/1", "model": "joycon-l",
                       "transport": "bluetooth"}
    out: dict[str, list] = {}
    name = None
    for d in rows[1:]:
        if "note" in d:
            name = d["note"]
            out[name] = []
        else:
            out[name].append((d["t"], bytes.fromhex(d["r"])))
    return out


def calibration() -> nintendo.Calibration:
    """The flash as the probe read it, then the stick's rest as the app
    takes it at connect (`recentre`), from the tape's own still step."""
    found = json.loads(FINDINGS.read_text())
    records = {int(a, 16): bytes.fromhex(h) for a, h in found["flash"].items()}
    cal = nintendo.calibration(records, "l")
    rest = [nintendo.raw_sticks(r)[0] for _, r in windows()["still"]]
    return nintendo.recentre(cal, "l", rest)


def test_every_report_is_the_full_report_and_the_flash_calibrated_it():
    cal = calibration()
    assert not cal.nominal and not cal.user_stick             # the factory's records, no user ones
    assert abs(cal.gyro[0][1] - 0.061) < 0.002                 # ±2000 deg/s: 0.061 deg/s a count
    assert abs(cal.accel[2][1] - 1 / 4096) < 1e-5              # ±8 g: 4096 counts a g
    for name, reports in windows().items():
        assert len(reports) >= 20, name                        # ~60 a second over Bluetooth
        replies = [r for _, r in reports if r[0] == nintendo.REPORT_REPLY]
        assert not replies or name == "settle", name           # the flash answering, at connect only
        for _, r in reports:
            if r[0] == nintendo.REPORT_REPLY:
                assert nintendo.decode(r, "l", cal) is None    # a reply is no frame
                continue
            f = nintendo.decode(r, "l", cal)
            assert f is not None and f.kind == sony.BT_IN and f.full, name
            assert f.battery == 5, name                        # it read "low"


def held(name: str, cal) -> set[str]:
    frames = [nintendo.decode(r, "l", cal) for _, r in windows()[name]]
    out = {NAMES[i] for i in NAMES if all(f.buttons[i] for f in frames)}
    if all(f.axes[4] > 0.5 for f in frames):
        out.add("axis:LT")
    return out


FACE = {"A": "S", "B": "E", "X": "W", "Y": "N"}


def test_every_button_lands_where_the_vocabulary_says():
    cal = calibration()
    assert held("still", cal) == set()
    for step in ("A", "Y", "B", "X", "LP", "RP", "LB", "axis:LT", "VIEW", "SHARE", "LSTICK"):
        assert held(step, cal) == {FACE.get(step, step)}, step     # (the tape's words, NSEW's names)


def test_the_stick_reaches_each_way_and_rests_at_centre():
    cal = calibration()

    def axes(step: str) -> list[list[float]]:
        return [nintendo.decode(r, "l", cal).axes for _, r in windows()[step]]
    assert max(a[0] for a in axes("stick right")) > 0.95
    assert min(a[0] for a in axes("stick left")) < -0.95
    assert min(a[1] for a in axes("stick up")) < -0.95          # GLFW's up is −
    assert max(a[1] for a in axes("stick down")) > 0.95
    rest = axes("rest")
    assert all(abs(a[0]) < 0.05 and abs(a[1]) < 0.05 for a in rest)   # recentred: the drift reads 0


def motion(name: str) -> dict[str, float]:
    """The motion lanes at the end of a step, the reports replayed in time
    through the flash's calibration and the Joy-Con's axis map."""
    m, cal, last = gesture.Motion(), calibration(), None
    amap = nintendo.AXIS_MAP
    for t, r in windows()[name]:
        f = nintendo.decode(r, "l", cal)
        m.step(amap.pick(cal.gyro_dps(f.gyro), amap.gyro), amap.pick(cal.accel_g(f.accel), amap.accel),
               0.0 if last is None else t - last)
        last = t
    return dict(zip(gesture.MOTION_LANES, m.lanes(), strict=True))


def test_tilt_and_turn_read_the_way_the_lanes_say():
    flat = motion("flat")
    assert abs(flat["roll"] - 0.5) < 0.08 and abs(flat["pitch"] - 0.5) < 0.08
    assert motion("right down")["roll"] > 0.65                 # right side down: roll high
    assert motion("far up")["pitch"] > 0.65                    # the far end up: pitch high
    turn = motion("turn right")
    assert turn["spin.yaw"] > 0.52 and turn["yaw"] > 0.5       # turning right: yaw high
