"""`tools/poi_probe.py` on the owner's Joy-Con (L) over Bluetooth (2026-11-02,
`tests/fixtures/pads/joycon-poi-excerpt.jsonl`): a real pickup off the table
and a real hold in the hand, through the app's exact path: the reader's
per-report turn on the report clock (`hid.Turn`), the frame's newest sample,
`poi.step`.

These hold only what is true of `poi.py` today, and the tool's own working.
The tape also shows the hand driven to `poi.HAND_LIMIT` and left there during
the hold (register row 786). That is reported, not pinned: **nothing here says
the hand stays on the screen**, and a fix to `poi.py` should not move a test
here except to add that."""

import dataclasses
import importlib.util
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperspace import poi
from hyperspace.pads import gesture, models, nintendo
from hyperspace.params import PAN_RANGE

ROOT = Path(__file__).resolve().parents[1]
TAPE = ROOT / "tests" / "fixtures" / "pads" / "joycon-poi-excerpt.jsonl"
EDGE = ROOT / "tests" / "fixtures" / "pads" / "edge-bt-excerpt.jsonl"
FINDINGS = ROOT / "docs" / "plans" / "assets" / "46-joycon" / "joycon-findings.json"
VENDOR, JOYCON_L = 0x057E, 0x2006


def _tool():
    if "poi_probe" in sys.modules:
        return sys.modules["poi_probe"]
    spec = importlib.util.spec_from_file_location("poi_probe", ROOT / "tools" / "poi_probe.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["poi_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


def _frames(**dials):
    return _tool().frames(TAPE, FINDINGS, dials)


def _report_rows():
    rows = [json.loads(line) for line in TAPE.read_text().splitlines() if line.strip()]
    return rows[0], rows[1:]


def test_the_tape_is_the_two_windows_at_the_joycons_rate():
    head, rows = _report_rows()
    assert head["model"] == "joycon-l" and head["transport"] == "bluetooth"
    assert [d["note"] for d in rows if "note" in d] == ["pickup", "hold"]
    assert sum(1 for d in rows if "r" in d) > 700          # 13.5 s at ~62 a second
    found = json.loads(FINDINGS.read_text())
    records = {int(a, 16): bytes.fromhex(h) for a, h in found["flash"].items()}
    assert not nintendo.calibration(records, "l").nominal


def test_the_probe_replays_its_own_tape_on_this_poi(capsys):
    """The proof the tool works: from its command line, on the tape, a row a
    window and the walls named."""
    _tool().main(["--replay", str(TAPE), "--findings", str(FINDINGS)])
    out = capsys.readouterr().out
    table = {ln.split()[0] for ln in out.splitlines() if ln.strip()}
    assert {"pickup", "hold"} <= table
    assert f"the hand at {poi.HAND_LIMIT:.1f} world units" in out


def test_the_series_prints_every_frame_between_two_times(capsys):
    _tool().main(["--replay", str(TAPE), "--findings", str(FINDINGS), "--series", "16", "17"])
    lines = [ln for ln in capsys.readouterr().out.splitlines() if "|a|" in ln]
    assert len(lines) > 40                                  # a second at ~62 reports
    assert all(16.0 <= float(ln.split("s")[0]) <= 17.0 for ln in lines)


def test_a_tape_with_no_calibration_beside_it_reads_nominal(tmp_path, capsys):
    tape = tmp_path / "t.jsonl"
    tape.write_bytes(TAPE.read_bytes())
    rows = _tool().replay(tape, None, {}, None, 0.0)
    assert "nominal" in capsys.readouterr().err
    assert [r["note"] for r in rows] == ["pickup", "hold"]


def test_the_numbers_stay_finite_and_inside_the_limits_poi_has():
    """`poi.py`'s own walls hold on a real tape: the hand at `HAND_LIMIT`, the
    pan at its reach. Those are the only walls it has."""
    for _, _, _, rig, n in _frames():
        assert poi._norm(n["wrist"]) <= poi.HAND_LIMIT + 1e-6
        assert all(abs(v) <= PAN_RANGE + 1e-6 for v in n["pan"])
        assert n["zoom"] > 0.0
        assert all(math.isfinite(v) for v in (*n["wrist"], *n["ball"], *n["pan"], n["zoom"]))
        assert rig.state.settled


def test_a_real_pickup_lands_near_home_and_leaves_a_quiet_hand():
    """Lifted off the table and held (the tape's A falls inside this window):
    the window ends with the hand within a screen and no longer moving."""
    ends = None
    for _, note, _, _, n in _frames():
        if note == "pickup":
            ends = poi._norm(n["wrist"]), n["speed"]
    assert ends[0] < 2.0
    assert ends[1] < 0.5


def test_a_dead_still_hold_ends_with_the_attitude_right_and_the_hand_at_rest():
    """The last of the hold, the pad dead still: by the end the attitude has
    been pulled to gravity and the velocity zeroed. Says nothing of where the
    hand was left."""
    last = None
    for _, note, _, rig, n in _frames():
        if note == "hold":
            last = n["err"], list(rig.state.wrist_v), n["still"]
    err, v, still = last
    assert err < 2.0
    assert v == [0.0, 0.0, 0.0]
    assert still >= poi.STILL_S


def test_with_the_hand_dial_at_zero_the_wrist_stays_home():
    """`poi.hand` 0 is the wrist alone: the dials reach the probe's rig, and
    with no push the weight stays within its string of home."""
    for _, _, _, rig, n in _frames(hand=0.0):
        assert rig.state.hand == 0.0
        assert n["wrist"] == [0.0, 0.0, 0.0]
        assert max(abs(v) for v in n["pan"]) < 2.0


def test_a_button_on_the_tape_resets_as_the_app_does():
    """The tape's one press (A, just after 18.75 s) puts the hand home on that
    frame: the one frame the hand's travel falls to nothing."""
    was, homes = None, []
    for _, _, t, _, n in _frames():
        travel = poi._norm(n["wrist"])
        if was is not None and was > 0.5 and travel < 1e-2:
            homes.append(t)
        was = travel
    assert len(homes) == 1
    assert 18.75 <= homes[0] <= 18.8


# ---- the app's path, on what a real tape does not hold (review of SM1)

SIDE_ON = (1.0, 0.0, 0.0)          # gravity along the pad's x: lying on its side


class Reader:
    """A reader with the sensors held at `accel`, and no report while `f` is None."""

    def __init__(self, accel=SIDE_ON, gyro=(0.0, 0.0, 0.0)):
        _, rows = _report_rows()
        raw = next(bytes.fromhex(d["r"]) for d in rows if "r" in d)
        self.model = models.MODELS["joycon-l"]
        self.axis_map = gesture.AxisMap()
        self.calibration = SimpleNamespace(gyro_dps=lambda _g: gyro, accel_g=lambda _a: accel)
        self.report = nintendo.decode(raw, "l", nintendo.Calibration())
        self.f = self.report

    def latest(self):
        return self.f

    def take_turn(self):
        return (0.0, 0.0, 0.0), 1 if self.f is not None else 0


def test_frames_before_the_pad_reports_settle_nothing():
    """"waiting for the pad" frames are no reading: a pad first heard on its
    side levels from that, it isn't 90 degrees out and flung to the wall."""
    tool, reader = _tool(), Reader()
    rig = tool.Rig()
    reader.f = None
    for _ in range(60):
        rig.frame(reader, 1 / 60)
        assert rig.pad.motion_lanes() is None
    assert not rig.state.settled
    reader.f = reader.report
    for _ in range(120):
        rig.frame(reader, 1 / 60)
        n = rig.numbers()
        assert n["err"] < 1.0
        assert n["walls"] == ""
        assert poi._norm(n["wrist"]) < 0.1


def test_a_pad_lost_comes_back_with_a_new_motion_and_the_hand_home():
    tool, reader = _tool(), Reader(accel=(0.0, 1.0, 0.0))
    rig = tool.Rig()
    for _ in range(10):
        rig.frame(reader, 1 / 60)
    before = rig.motion
    rig.state.wrist = [1.0, 0.0, 0.0]
    reader.f = None
    rig.frame(reader, 1 / 60)
    assert rig.motion is not before
    assert rig.state.driving is None
    reader.f = reader.report
    rig.frame(reader, 1 / 60)
    assert rig.state.wrist == [0.0, 0.0, 0.0]


def test_a_replay_treats_a_pause_past_stale_as_the_reader_does(tmp_path):
    """Two stretches 2 s apart: the second reads the pad afresh, as live."""
    head, rows = _report_rows()
    reports = [d for d in rows if "r" in d][:40]
    t0 = reports[0]["t"]
    lines = [json.dumps(head)]
    for shift in (0.0, 3.0):
        lines += [json.dumps({"t": d["t"] - t0 + shift, "r": d["r"]}) for d in reports]
    tape = tmp_path / "gap.jsonl"
    tape.write_text("\n".join(lines) + "\n")
    motions = {id(rig.motion) for _, _, _, rig, _ in _tool().frames(tape, FINDINGS, {})}
    assert len(motions) == 2


def test_the_d_pad_down_resets_on_its_edge_only():
    """`poi._buttons` reads the hat too: its edge, not its being held."""
    tool, reader = _tool(), Reader(accel=(0.0, 1.0, 0.0))
    rig = tool.Rig()
    for _ in range(10):
        rig.frame(reader, 1 / 60)
    rig.state.wrist = [1.0, 0.0, 0.0]
    reader.f = dataclasses.replace(reader.report, hat=poi.HAT_DOWN)
    rig.frame(reader, 1 / 60)
    assert rig.state.wrist == [0.0, 0.0, 0.0]
    rig.state.wrist = [1.0, 0.0, 0.0]
    rig.frame(reader, 1 / 60)                               # still held
    assert rig.state.wrist[0] == pytest.approx(1.0)


# ---- the tool on other tapes

def test_an_edge_tape_reads_through_its_own_codec(capsys):
    rows = _tool().replay(EDGE, None, {}, None, 0.0)
    assert rows[0]["note"] == "still"
    assert all(r["n"] > 0 for r in rows)
    assert "nominal" in capsys.readouterr().err


def _write(path, *lines):
    path.write_text("".join(ln + "\n" for ln in lines))
    return path


def test_a_tape_that_decodes_to_nothing_exits_non_zero(tmp_path):
    head = json.dumps({"tape": "hyperspace.padtape/1", "model": "joycon-l"})
    tape = _write(tmp_path / "empty.jsonl", head)
    with pytest.raises(SystemExit) as got:
        _tool().main(["--replay", str(tape)])
    assert "nothing to show" in str(got.value.code)
    tape = _write(tmp_path / "junk.jsonl", head, json.dumps({"t": 1.0, "r": "00ff"}))
    with pytest.raises(SystemExit) as got:
        _tool().main(["--replay", str(tape)])
    assert "nothing to show" in str(got.value.code)


def test_two_notes_of_one_word_are_two_rows(tmp_path):
    head, rows = _report_rows()
    reports = [d for d in rows if "r" in d][:60]
    lines = [json.dumps(head), json.dumps({"t": reports[0]["t"], "note": "mark"})]
    lines += [json.dumps(d) for d in reports[:20]]
    lines.append(json.dumps({"t": reports[20]["t"], "note": "other"}))
    lines += [json.dumps(d) for d in reports[20:40]]
    lines.append(json.dumps({"t": reports[40]["t"], "note": "mark"}))
    lines += [json.dumps(d) for d in reports[40:]]
    tape = _write(tmp_path / "marks.jsonl", *lines)
    got = _tool().replay(tape, FINDINGS, {}, None, 0.0)
    assert [r["note"] for r in got] == ["mark", "other", "mark"]
    assert [r["n"] for r in got] == [20, 20, 20]


def test_a_killed_recording_replays_up_to_where_it_stopped(tmp_path):
    """A line cut short, and rows that aren't, as `hid.TapePad` takes them."""
    text = TAPE.read_text().splitlines()[:60]
    tape = _write(tmp_path / "killed.jsonl", *text, "[1, 2]", "7", '{"t": "x", "note": "bad"}',
                  text[-1][:25])
    got = _tool().replay(tape, FINDINGS, {}, None, 0.0)
    assert [r["note"] for r in got] == ["pickup"]


def test_a_file_that_is_no_pad_tape_is_refused_in_words(tmp_path):
    tape = _write(tmp_path / "other.jsonl", json.dumps({"tape": "someone.else/9"}))
    with pytest.raises(SystemExit) as got:
        _tool().main(["--replay", str(tape)])
    assert "not a pad tape" in str(got.value.code)
    with pytest.raises(SystemExit) as got:
        _tool().main(["--replay", str(tmp_path / "gone.jsonl")])
    assert got.value.code not in (0, None)


def test_a_named_findings_file_must_be_there_and_hold_flash(tmp_path):
    tool = _tool()
    with pytest.raises(SystemExit) as got:
        tool.main(["--replay", str(TAPE), "--findings", str(tmp_path / "gone.json")])
    assert "no such findings file" in str(got.value.code)
    for name, body, says in (("noflash.json", "{}", "no flash records"),
                             ("list.json", "[]", "no flash records"),
                             ("text.json", "not json", "not JSON"),
                             ("hex.json", '{"flash": {"0x6020": "zz"}}', "bad flash records")):
        side = tmp_path / name
        side.write_text(body)
        with pytest.raises(SystemExit) as got:
            tool.main(["--replay", str(TAPE), "--findings", str(side)])
        assert says in str(got.value.code)


@pytest.mark.parametrize(("link", "transport"), [
    ({"bus_type": 2}, "bluetooth"), ({"bus_type": 1}, "usb"),
    ({"interface_number": -1}, "bluetooth"), ({"interface_number": 0}, "usb"), ({}, "usb")])
def test_live_reads_a_reader_as_the_app_does_and_keeps_the_tape(tmp_path, monkeypatch, capsys,
                                                                link, transport):
    """The live loop on a stand-in for the reader, held to the real class
    below: its calibration file and its tape land beside each other, and the
    tape says the link as `hid._on_usb` does."""
    tool = _tool()
    _, rows = _report_rows()
    raws = [bytes.fromhex(d["r"]) for d in rows if "r" in d][:30]
    frames = iter(raws)
    built = {}

    class Stand:
        def __init__(self, info, recorder=None):
            built["recorder"] = recorder
            self.model = models.by_ids(info["vendor_id"], info["product_id"])
            self.calibration = nintendo.Calibration()
            self.axis_map = nintendo.AXIS_MAP
            self.flash = {0x6020: b"\x01\x02"}
            self.reports = 0
            self.note = ""

        def latest(self):
            try:
                r = next(frames)
            except StopIteration:
                raise KeyboardInterrupt from None
            self.reports += 1
            built["recorder"].write(r)
            return nintendo.decode(r, "l", self.calibration)

        def take_turn(self):
            return (0.1, 0.0, 0.0), 1

        def close(self):
            built["closed"] = True

    def no_keys(*_):
        raise EOFError

    monkeypatch.setattr(tool.hid, "HidPad", Stand)
    monkeypatch.setattr("builtins.input", no_keys)
    monkeypatch.setattr(tool.time, "sleep", lambda _s: None)
    tape = tmp_path / "poi.jsonl"
    tool.live({"vendor_id": VENDOR, "product_id": JOYCON_L, **link}, tape, {})
    out = capsys.readouterr().out
    assert "|a|" in out and "tape written" in out
    assert built["closed"]
    head = json.loads(tape.read_text().splitlines()[0])
    assert head["model"] == models.by_ids(VENDOR, JOYCON_L).id and head["transport"] == transport
    side = json.loads((tmp_path / "poi.jsonl.findings.json").read_text())
    assert side["flash"] == {"0x6020": "0102"}


def test_the_real_reader_has_what_live_asks_of_it():
    """`live` above runs on a stand-in: this holds the stand-in to the class."""
    tool = _tool()
    info = {"vendor_id": VENDOR, "product_id": JOYCON_L}
    reader = tool.hid.HidPad(info, start=False)
    for name in ("model", "calibration", "axis_map", "flash", "reports", "note", "latest",
                 "take_turn", "close"):
        assert hasattr(reader, name), name
    assert reader.axis_map is not None
