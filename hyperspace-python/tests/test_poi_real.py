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

import importlib.util
import json
import math
import sys
from pathlib import Path

from hyperspace import poi
from hyperspace.pads import models, nintendo
from hyperspace.params import PAN_RANGE

ROOT = Path(__file__).resolve().parents[1]
TAPE = ROOT / "tests" / "fixtures" / "pads" / "joycon-poi-excerpt.jsonl"
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
    stats = _tool().replay(tape, None, {}, None, 0.0)
    assert "nominal" in capsys.readouterr().err
    assert set(stats) == {"pickup", "hold"}


def test_the_numbers_stay_finite_and_inside_the_limits_poi_has():
    """`poi.py`'s own walls hold on a real tape: the hand at `HAND_LIMIT`, the
    pan at its reach. Those are the only walls it has."""
    for _, _, rig, n in _frames():
        assert poi._norm(n["wrist"]) <= poi.HAND_LIMIT + 1e-6
        assert all(abs(v) <= PAN_RANGE + 1e-6 for v in n["pan"])
        assert n["zoom"] > 0.0
        assert all(math.isfinite(v) for v in (*n["wrist"], *n["ball"], *n["pan"], n["zoom"]))
        assert rig.state.settled


def test_a_real_pickup_lands_near_home_and_leaves_a_quiet_hand():
    """Lifted off the table and held (the tape's A falls inside this window):
    the window ends with the hand within a screen and no longer moving."""
    ends = None
    for note, _, _, n in _frames():
        if note == "pickup":
            ends = poi._norm(n["wrist"]), n["speed"]
    assert ends[0] < 2.0
    assert ends[1] < 0.5


def test_a_dead_still_hold_ends_with_the_attitude_right_and_the_hand_at_rest():
    """The last of the hold, the pad dead still: by the end the attitude has
    been pulled to gravity and the velocity zeroed. Says nothing of where the
    hand was left."""
    last = None
    for note, _, rig, n in _frames():
        if note == "hold":
            last = n["err"], list(rig.state.wrist_v), n["still"]
    err, v, still = last
    assert err < 2.0
    assert v == [0.0, 0.0, 0.0]
    assert still >= poi.STILL_S


def test_with_the_hand_dial_at_zero_the_wrist_stays_home():
    """`poi.hand` 0 is the wrist alone: the dials reach the probe's rig, and
    with no push the weight stays within its string of home."""
    for _, _, rig, n in _frames(hand=0.0):
        assert rig.state.hand == 0.0
        assert n["wrist"] == [0.0, 0.0, 0.0]
        assert max(abs(v) for v in n["pan"]) < 2.0


def test_a_button_on_the_tape_resets_as_the_app_does():
    """The tape's one press (A, just after 18.75 s) puts the hand home on that
    frame: the one frame the hand's travel falls to nothing."""
    was, homes = None, []
    for _, t, _, n in _frames():
        travel = poi._norm(n["wrist"])
        if was is not None and was > 0.5 and travel < 1e-2:
            homes.append(t)
        was = travel
    assert len(homes) == 1
    assert 18.75 <= homes[0] <= 18.8


def test_live_reads_a_reader_as_the_app_does_and_keeps_the_tape(tmp_path, monkeypatch, capsys):
    """The live loop on a stand-in for the reader: the attributes it asks of
    `hid.HidPad` exist on the real class's instances (a real one, unopened,
    below), its calibration file and its tape land beside each other."""
    tool = _tool()
    _, rows = _report_rows()
    raws = [bytes.fromhex(d["r"]) for d in rows if "r" in d][:30]
    frames = iter(raws)
    built = {}

    class Reader:
        def __init__(self, info, recorder=None):
            built["recorder"] = recorder
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

    monkeypatch.setattr(tool.hid, "HidPad", Reader)
    monkeypatch.setattr("builtins.input", no_keys)
    monkeypatch.setattr(tool.time, "sleep", lambda _s: None)
    tape = tmp_path / "poi.jsonl"
    tool.live({"vendor_id": VENDOR, "product_id": JOYCON_L, "bus_type": 2}, tape, {})
    out = capsys.readouterr().out
    assert "|a|" in out and "tape written" in out
    assert built["closed"]
    head = json.loads(tape.read_text().splitlines()[0])
    assert head["model"] == models.by_ids(VENDOR, JOYCON_L).id and head["transport"] == "bluetooth"
    side = json.loads((tmp_path / "poi.jsonl.findings.json").read_text())
    assert side["flash"] == {"0x6020": "0102"}


def test_the_real_reader_has_what_live_asks_of_it():
    """`live` above runs on a stand-in: this holds the stand-in to the class."""
    tool = _tool()
    info = {"vendor_id": VENDOR, "product_id": JOYCON_L}
    reader = tool.hid.HidPad(info, start=False)
    for name in ("calibration", "axis_map", "flash", "reports", "note", "latest", "take_turn",
                 "close"):
        assert hasattr(reader, name), name
    assert reader.axis_map is not None
