"""tools/calm_lanes.py: a library's analyzer routes held to the new
route's depth and given the smooth spring, once (the owner, 2026-11-02).

Every test runs on a scratch library under tmp_path; the machine home
(the backup's place) is the conftest's tmp one."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "corpus" / "loadable"


def _tool():
    if "calm_lanes" in sys.modules:
        return sys.modules["calm_lanes"]
    spec = importlib.util.spec_from_file_location("calm_lanes", ROOT / "tools" / "calm_lanes.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["calm_lanes"] = mod
    spec.loader.exec_module(mod)
    return mod


SMOOTH = {"mode": "spring", "dur": 0.5, "bounce": 0.0}
BOUNCY = {"mode": "spring", "dur": 0.6666666666666666, "bounce": 0.4}


def _doc(*routes):
    return {"schema": "hyperspace.preset/7", "name": "x", "routes": list(routes)}


def test_a_hot_push_is_held_to_the_cap_and_sprung():
    t = _tool()
    doc = _doc({"source": "lane:0", "target": "pattern.mod.0", "op": "push", "value": 0.35},
               {"source": "lane:2", "target": "rot.rate.YW", "op": "push", "value": -0.35,
                "scale": "master.gain"})
    c = t.calm(doc, cap=0.12)
    assert (c.lanes, c.capped, c.faders, c.sprung, c.kept_feel) == (2, 2, 0, 2, 0)
    a, b = doc["routes"]
    assert (a["value"], a["motion"]) == (0.12, SMOOTH)
    assert (b["value"], b["motion"], b["scale"]) == (-0.12, SMOOTH, "master.gain")  # sign, scale kept


def test_a_calm_push_keeps_its_depth_and_a_fader_becomes_a_push():
    t = _tool()
    doc = _doc({"source": "lane:1", "target": "rot.rate.XW", "op": "push", "value": 0.0625},
               {"source": "lane:0", "target": "pattern.mod.0", "op": "position", "value": 0.07},
               {"source": "lane:3", "target": "pattern.mod.3", "op": "position", "value": 1.0})
    c = t.calm(doc, cap=0.12)
    assert (c.capped, c.faders, c.sprung) == (0, 2, 3)
    calm, fader, full = doc["routes"]
    assert calm["value"] == 0.0625
    assert (fader["op"], fader["value"]) == ("push", 0.07)
    assert (full["op"], full["value"]) == ("push", 0.12)


def test_feels_the_owner_tuned_are_kept_and_the_old_bouncy_default_is_not():
    t = _tool()
    tuned = {"mode": "spring", "dur": 5.887, "bounce": 0.95}
    follow = {"mode": "follow", "atk": 0.02, "rel": 0.3}
    doc = _doc({"source": "lane:0", "target": "fx.kaleido.swirl", "op": "push", "value": 0.1,
                "motion": dict(tuned)},
               {"source": "lane:1", "target": "fx.acid.reach", "op": "push", "value": 0.1,
                "motion": dict(follow)},
               {"source": "lane:2", "target": "pattern.mod.2", "op": "push", "value": 0.1,
                "motion": dict(BOUNCY)},
               {"source": "lane:3", "target": "pattern.mod.3", "op": "push", "value": 0.1,
                "motion": {"mode": "spring", "hz": 1.5, "damp": 0.6}})   # the old spelling of bouncy
    c = t.calm(doc, cap=0.12)
    assert (c.sprung, c.kept_feel) == (2, 2)
    r = doc["routes"]
    assert r[0]["motion"] == tuned and r[1]["motion"] == follow
    assert r[2]["motion"] == SMOOTH and r[3]["motion"] == SMOOTH


def test_only_lane_rows_move_and_a_second_run_changes_nothing():
    t = _tool()
    doc = _doc({"source": "hand:right.x", "target": "camera.yaw", "op": "push", "value": 0.9},
               {"source": "lfo:0", "target": "fx.acid.mix", "op": "position", "value": 1.0},
               {"source": "cc@launch:7", "target": "view.bright", "op": "abs"},
               {"source": "lane:0", "target": "pattern.mod.0", "op": "push", "value": 0.35})
    before = json.dumps(doc["routes"][:3])
    c = t.calm(doc, cap=0.12)
    assert c.lanes == 1 and c.changed
    assert json.dumps(doc["routes"][:3]) == before
    again = t.calm(doc, cap=0.12)
    assert not again.changed and again.kept_feel == 1


def test_the_run_writes_as_the_app_writes_and_backs_up_first(tmp_path, monkeypatch):
    """A dry run writes nothing; --apply copies the library to the machine
    home first and rewrites only the loadable patches with a hot or feel-less lane
    row, byte for byte as the app saves (indent 1, a trailing newline),
    every other key as it was."""
    t = _tool()
    home = tmp_path / "home"
    library = tmp_path / "library"
    (library / "loadable").mkdir(parents=True)
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    src = json.loads((CORPUS / "party-trip.json").read_text())
    assert any(str(r.get("source", "")).startswith("lane:") for r in src["routes"])
    (library / "loadable" / "party-trip.json").write_text(json.dumps(src, indent=1) + "\n")
    calm_doc = {"schema": "hyperspace.preset/7", "name": "calm", "routes": [
        {"source": "lane:0", "target": "pattern.mod.0", "op": "push", "value": 0.05,
         "motion": dict(SMOOTH)}]}
    (library / "loadable" / "calm.json").write_text(json.dumps(calm_doc, indent=1) + "\n")
    (library / "loadable" / ".party-trip.json.tmp").write_text("{}")

    assert t.main(["--library", str(library)]) == 0
    assert json.loads((library / "loadable" / "party-trip.json").read_text()) == src
    assert not list(home.glob("library-backup-*"))

    assert t.main(["--library", str(library), "--apply"]) == 0
    backups = list(home.glob("library-backup-*"))
    assert len(backups) == 1
    assert json.loads((backups[0] / "loadable" / "party-trip.json").read_text()) == src
    text = (library / "loadable" / "party-trip.json").read_text()
    out = json.loads(text)
    assert text == json.dumps(out, indent=1) + "\n"
    for k in src:
        if k != "routes":
            assert out[k] == src[k]
    lanes = [r for r in out["routes"] if str(r["source"]).startswith("lane:")]
    assert lanes and all(r["op"] == "push" and abs(r["value"]) <= 0.12 for r in lanes)
    assert all(r["motion"]["mode"] == "spring" for r in lanes)
    others = [r for r in src["routes"] if not str(r["source"]).startswith("lane:")]
    assert [r for r in out["routes"] if not str(r["source"]).startswith("lane:")] == others
    # the already-calm loadable patch and the dot-file were left alone
    assert json.loads((library / "loadable" / "calm.json").read_text()) == calm_doc
    assert (library / "loadable" / ".party-trip.json.tmp").read_text() == "{}"


@pytest.mark.parametrize("value", [0.12, -0.12, 0.0])
def test_a_push_at_or_under_the_cap_is_not_capped(value):
    t = _tool()
    doc = _doc({"source": "lane:0", "target": "pattern.mod.0", "op": "push", "value": value})
    c = t.calm(doc, cap=0.12)
    assert c.capped == 0 and doc["routes"][0]["value"] == value
