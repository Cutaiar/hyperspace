"""The look-back retired onto public parts.

A saved look-back (`lookback`, `lookback.<n>`), its echo pins and its knobs
(`dream.*`, `dream.<n>.*`) are rewritten on load (`graphmigrate.lookbacks`, the
ladder's last step; a fragment's `patches.forward` too): X → Curve (where
contrast is not 1, or driven) → Fade (1 − darken, keyed: peak, linear, level 0,
soft 1, keep colour) → Resize (512) → Delay (depth = echoes, Hz = 1 / gap) ═►
Trail (level, fade, over) → Cut (a Matte of the occluder: peak, linear, ⅛, ⅛)
→ Cut (the cover), each Cut's amount the occlude; where its picture went, the
last of them. An echo pin is a Read at k − 1, nearest; past the echoes, of a
second delay at that depth (Q25). Rows retarget with their ranges; a row on
the gap is left out, said (Q27); darken, contrast and res stay the dream's,
a row on one copied onto the look-back's part too (Q26)."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from hyperspace import graph as G
from hyperspace import graphmigrate, patches
from hyperspace.fx import FxState

CORPUS = Path(__file__).parent / "corpus" / "loadable"
TRACER = CORPUS / "party-tracer.json"
ECHO_FACES = Path(__file__).parent / "fixtures" / "presets" / "echo-faces.json"


def _doc(wires, values=None, nodes=(), **rest):
    return {"schema": "hyperspace.loadable/12", "name": "t",
            "graph": {"frame": "wired", "nodes": [{"kind": "hands", "laid": "over"}, *nodes],
                      "wires": [{"from": "shape", "to": "scene.geometry"},
                                {"from": "pattern", "to": "shape.faces"}, *wires]},
            "values": dict(values or {}), **rest}


TRAIL = [{"from": "scene", "to": "lookback.image"}, {"from": "scene", "to": "lookback.occluder"},
         {"from": "scene.cover", "to": "lookback.cover"},
         {"from": "scene", "to": "composite.under"}, {"from": "lookback", "to": "composite.over"},
         {"from": "composite", "to": "output.all.image"}]
COMP = [{"kind": "composite", "blend": "add"}]


def _wires(doc):
    return [(w["from"], w["to"]) for w in doc["graph"]["wires"]]


def _reads(doc):
    spec = G.read_graph(doc["graph"], effects=set(FxState().specs))
    assert not spec.notes, spec.notes
    return spec


def test_the_trail_is_public_parts():
    got, notes = graphmigrate.lookbacks(_doc(TRAIL, {"dream.echo_mix": 0.6, "dream.fade": 0.5,
                                                     "dream.echoes": 12, "dream.gap": 0.05,
                                                     "dream.darken": 0.25,
                                                     "dream.occlude": 0.3}, COMP))
    w = _wires(got)
    for pair in [("scene", "fade.image"), ("fade", "resize.image"), ("resize", "delay.image"),
                 ("delay", "trail.stack"), ("trail", "cut.image"), ("scene", "matte.image"),
                 ("matte", "cut.mask"), ("cut", "cut.2.image"), ("scene.cover", "cut.2.mask"),
                 ("cut.2", "composite.over"), ("scene", "composite.under")]:
        assert pair in w, pair
    assert not any("lookback" in x for p in w for x in p)
    assert not any(n.get("kind") == "lookback" for n in got["graph"]["nodes"])
    assert "curve" not in json.dumps(got["graph"])          # contrast 1, undriven
    assert got["graph"]["keys"] == ["fade"]
    v = got["values"]
    assert v["fx.fade.level"] == 0.75 and v["fx.fade.on"] is True
    assert (v["key.fade.measure"], v["key.fade.ramp"], v["key.fade.level"], v["key.fade.soft"],
            v["key.fade.keep"]) == (0, 1, 0.0, 1.0, True)
    assert v["resize.size"] == 5                              # 512 on the long side (Q24)
    assert (v["delay.depth"], v["delay.every"], v["delay.hz"]) == (12, 1, 20.0)
    assert (v["fx.trail.level"], v["fx.trail.fade"], v["fx.trail.lay"]) == (0.6, 0.5, 0)
    assert (v["matte.from"], v["matte.ramp"], v["matte.key"], v["matte.soft"]) == (
        3, 1, 0.125, 0.125)
    assert v["cut.amount"] == v["cut.2.amount"] == 0.3
    assert v["cut.invert"] is v["cut.2.invert"] is True       # held back where it passes
    for gone in ("echo_mix", "fade", "echoes", "gap", "occlude"):
        assert f"dream.{gone}" not in v
    assert v["dream.darken"] == 0.25                          # the dream's still (Q26)
    assert any("lookback is public parts now" in n for n in notes)
    _reads(got)


def test_a_gap_of_none_is_every_frame_and_contrast_brings_a_curve():
    got, _ = graphmigrate.lookbacks(_doc(TRAIL, {"dream.gap": 0.0, "dream.contrast": 2.0}, COMP))
    v = got["values"]
    assert (v["delay.every"], v["delay.frames"]) == (0, 1) and "delay.hz" not in v
    assert ("scene", "curve.image") in _wires(got) and ("curve", "fade.image") in _wires(got)
    assert v["fx.curve.shape"] == pytest.approx(0.5)           # log₄ 2
    _reads(got)


def test_defaults_are_the_old_look_backs():
    got, _ = graphmigrate.lookbacks(_doc(TRAIL, {}, COMP))
    v = got["values"]
    assert (v["delay.depth"], v["delay.hz"]) == (8, 30.0)
    assert (v["fx.trail.level"], v["fx.trail.fade"]) == (0.4, 0.2252)
    assert v["fx.fade.level"] == pytest.approx(0.9) and v["cut.amount"] == 1.0


def test_only_what_is_wired_is_cut():
    wires = [x for x in TRAIL if x["to"] not in ("lookback.occluder", "lookback.cover")]
    got, _ = graphmigrate.lookbacks(_doc(wires, {}, COMP))
    assert ("trail", "composite.over") in _wires(got)
    assert "matte" not in json.dumps(got["graph"]) and '"cut' not in json.dumps(got["graph"])


def test_echo_pins_are_reads_and_a_deeper_one_a_second_delay():
    wires = [{"from": "scene", "to": "lookback.image"},
             {"from": "lookback.echo.3", "to": "output.1.image"},
             {"from": "lookback.echo.20", "to": "output.2.image"}]
    got, notes = graphmigrate.lookbacks(_doc(wires, {"dream.echoes": 8}))
    w = _wires(got)
    assert ("delay", "read.stack") in w and ("read", "output.1.image") in w
    assert ("resize", "delay.2.image") in w and ("delay.2", "read.2.stack") in w
    assert ("read.2", "output.2.image") in w
    v = got["values"]
    assert (v["fx.read.at"], v["fx.read.between"]) == (2.0, 1)
    assert v["fx.read.2.at"] == 19.0 and v["delay.2.depth"] == 20 and v["delay.depth"] == 8
    assert "trail" not in json.dumps(got["graph"])     # its own picture read by none
    assert sum("Read of" in n for n in notes) == 2
    _reads(got)


def test_a_second_look_back_has_its_own_parts_and_knobs():
    wires = [*TRAIL, {"from": "scene", "to": "lookback.2.image"},
             {"from": "lookback.2", "to": "output.2.image"}]
    got, _ = graphmigrate.lookbacks(_doc(wires, {"dream.2.echo_mix": 0.9, "dream.2.echoes": 3,
                                                 "dream.2.darken": 0.0, "dream.echoes": 5},
                                         [*COMP, {"kind": "lookback", "instance": 2}]))
    v = got["values"]
    assert v["delay.depth"] == 5 and v["delay.2.depth"] == 3
    assert v["fx.trail.2.level"] == 0.9 and v["fx.fade.2.level"] == 1.0
    assert ("trail.2", "output.2.image") in _wires(got)
    assert not any(k.startswith("dream.2.") for k in v)
    assert sorted(got["graph"]["keys"]) == ["fade", "fade.2"]
    _reads(got)


def test_new_parts_take_the_next_free_instance():
    nodes = [*COMP, {"kind": "delay"}, {"kind": "effect", "file": "fade"}, {"kind": "cut"}]
    wires = [*TRAIL, {"from": "scene", "to": "delay.image"}, {"from": "delay", "to": "fade.image"},
             {"from": "fade", "to": "cut.image"}, {"from": "cut", "to": "output.2.image"}]
    got, _ = graphmigrate.lookbacks(_doc(wires, {}, nodes))
    w = _wires(got)
    assert ("scene", "fade.2.image") in w and ("resize", "delay.2.image") in w
    assert ("trail", "cut.2.image") in w and ("cut.3", "composite.over") in w
    assert ("delay", "fade.image") in w                          # (theirs, untouched)
    _reads(got)


ROWS = [{"source": "lane:0", "target": "dream.echo_mix", "op": "push", "value": 0.3},
        {"source": "lane:1", "target": "dream.darken", "op": "push", "value": 0.4},
        {"source": "lane:2", "target": "dream.darken", "op": "set", "value": 0.2},
        {"source": "lane:3", "target": "dream.echoes", "op": "push", "value": 0.5},
        {"source": "lane:4", "target": "dream.gap", "op": "push", "value": 0.5},
        {"source": "lane:5", "target": "dream.occlude", "op": "push", "value": 0.6},
        {"source": "lane:6", "target": "dream.contrast", "op": "push", "value": 0.2},
        {"source": "lane:7", "target": "dream.mix", "op": "push", "value": 0.2}]


def test_rows_retarget_with_their_ranges():
    got, notes = graphmigrate.lookbacks(_doc(TRAIL, {"dream.contrast": 1.0}, COMP, routes=ROWS))
    rows = {(r["source"], r["target"]): r.get("value") for r in got["routes"]}
    assert rows[("lane:0", "fx.trail.level")] == 0.3
    assert rows[("lane:1", "fx.fade.level")] == -0.4 and rows[("lane:1", "dream.darken")] == 0.4
    assert rows[("lane:2", "fx.fade.level")] == pytest.approx(0.8)
    assert rows[("lane:3", "delay.depth")] == pytest.approx(0.5 * 32 / 63, abs=1e-6)
    assert not any(s == "lane:4" for s, _ in rows)                       # gap: left out
    assert rows[("lane:5", "cut.amount")] == rows[("lane:5", "cut.2.amount")] == 0.6
    # (contrast driven: a curve; d shape = d c / (c ln 4), a norm of 2 wide)
    assert rows[("lane:6", "dream.contrast")] == 0.2
    assert rows[("lane:6", "fx.curve.shape")] == pytest.approx(0.2 * 2.5 / math.log(4) / 2,
                                                               abs=1e-6)
    assert rows[("lane:7", "dream.mix")] == 0.2                            # the dream's own
    assert any("dream.gap" in n and "left out" in n for n in notes)
    assert ("scene", "curve.image") in _wires(got)


def test_a_macro_on_darken_is_copied_and_turned_over():
    macros = {"m1": {"subs": [{"base": "dream.darken", "from": 0.0, "to": 0.5},
                              {"base": "dream.echo_mix"}]}}
    got, _ = graphmigrate.lookbacks(_doc(TRAIL, {}, COMP, macros=macros))
    subs = got["macros"]["m1"]["subs"]
    assert {"base": "dream.darken", "from": 0.0, "to": 0.5} in subs
    assert {"base": "fx.fade.level", "from": 1.0, "to": 0.5} in subs
    assert {"base": "fx.trail.level"} in subs


def test_a_patch_with_no_look_back_drops_its_retired_knobs_only():
    doc = _doc([], {"dream.echo_mix": 0.4, "dream.fade": 0.2, "dream.darken": 0.1,
                    "dream.mix": 0.7, "dream.2.echoes": 3},
               routes=[{"source": "lane:0", "target": "dream.fade", "op": "push"}])
    got, notes = graphmigrate.lookbacks(doc)
    assert got["values"] == {"dream.darken": 0.1, "dream.mix": 0.7}
    assert got["routes"] == [] and any("dream.fade" in n for n in notes)
    assert got["graph"] == doc["graph"]


def test_a_patch_naming_none_is_handed_back():
    doc = _doc([], {"dream.darken": 0.1, "dream.mix": 0.7})
    got, notes = graphmigrate.lookbacks(doc)
    assert got is doc and notes == []


def test_it_runs_once():
    doc = json.loads(TRACER.read_text())
    once, _ = graphmigrate.lookbacks(doc)
    twice, notes = graphmigrate.lookbacks(copy.deepcopy(once))
    assert twice == once and notes == []


def test_the_ladder_runs_it_last():
    doc = json.loads(TRACER.read_text())
    fwd = graphmigrate.forward(doc, {})
    assert "lookback" not in json.dumps(fwd.doc["graph"])
    assert any("public parts" in n for n in fwd.migrate_notes)


def test_a_fragment_retires_its_look_back_and_its_ports():
    doc = {"schema": patches.SCHEMA, "name": "f",
           "nodes": [{"kind": "composite", "blend": "add"}],
           "wires": [{"from": "lookback", "to": "composite.over"}],
           "ports": [{"name": "in", "to": "lookback.image"},
                     {"name": "out", "from": "composite"}],
           "values": {"dream.echoes": 4}}
    got = patches.forward(doc)
    assert {"from": "trail", "to": "composite.over"} in got["wires"]
    assert {"name": "in", "to": "fade.image"} in got["ports"]
    assert got["values"]["delay.depth"] == 4 and got["keys"] == ["fade"]


# ---------------------------------------------------------------- whole files

def test_an_old_look_back_file_loads_migrated_with_no_unknown_id(tmp_path):
    """End to end (REVIEW.md: a format change opens an old file whole): the
    corpus's party-tracer, through the library's own load and save."""
    from hyperspace import headless
    raw, notes, _ = headless.resave(TRACER, tmp_path / "a")
    assert any("public parts" in n for n in notes)
    assert not any("unknown id" in n or n.startswith("graph:") for n in notes), notes
    assert b"lookback" not in raw and b"dream.echo_mix" not in raw
    doc = json.loads(raw)
    assert {"from": "cut.2", "to": "composite.over"} in doc["graph"]["wires"]
    again = tmp_path / "again.json"
    again.write_bytes(raw)
    raw2, notes2, _ = headless.resave(again, tmp_path / "b")
    assert raw2 == raw and notes2 == []


def test_an_old_echo_pin_file_loads_migrated(tmp_path):
    from hyperspace import headless
    raw, notes, _ = headless.resave(ECHO_FACES, tmp_path / "a")
    assert not any("unknown id" in n or n.startswith("graph:") for n in notes), notes
    doc = json.loads(raw)
    assert {"from": "read", "to": "shape.faces"} in doc["graph"]["wires"]
    assert doc["values"]["fx.read.at"] == 2.0


@pytest.mark.parametrize("path", sorted(CORPUS.glob("*.json")) + sorted(
    (Path(__file__).parents[1] / "loadable").rglob("*.json")), ids=lambda p: p.stem)
def test_every_saved_look_migrates_to_no_look_back(path):
    fwd = graphmigrate.forward(json.loads(path.read_text()), {})
    text = json.dumps(fwd.doc)
    assert "lookback" not in text and "dream.echo_mix" not in text, path


def test_the_parts_draw_whatever_the_master_switch_said():
    """The look-back drew under `fx.on` off and at any `fx.mix`; its parts are
    effects, which those gate and scale — so they are on and at 1, and the
    patch's other effects stay as they drew: off, or at their mix × the master's."""
    nodes = [*COMP, {"kind": "effect", "file": "acid"}, {"kind": "effect", "file": "wave"}]
    wires = [*TRAIL, {"from": "scene", "to": "acid.image"}, {"from": "acid", "to": "wave.image"},
             {"from": "wave", "to": "output.2.image"}]
    got, notes = graphmigrate.lookbacks(_doc(wires, {"fx.on": False, "fx.acid.on": True,
                                                     "fx.wave.on": False}, nodes))
    v = got["values"]
    assert v["fx.on"] is True and v["fx.acid.on"] is False and v["fx.wave.on"] is False
    assert v["fx.trail.on"] is True and v["fx.fade.on"] is True
    got, notes = graphmigrate.lookbacks(_doc(wires, {"fx.mix": 0.5, "fx.acid.on": True,
                                                     "fx.acid.mix": 0.8}, nodes,
                                             routes=[{"source": "lane:0", "target": "fx.mix",
                                                      "op": "push"}]))
    v = got["values"]
    assert v["fx.mix"] == 1.0 and v["fx.acid.mix"] == pytest.approx(0.4)
    assert v["fx.acid.on"] is True
    assert any("fx.mix" in n and "parts too" in n for n in notes)


# ---------------------------------------------------------------- one group

def test_a_look_back_lands_folded_in_one_group_of_its_parts():
    """The parts a look-back becomes are detail on
    demand — one folded group, picture in and picture out, `+` away from
    the parts. Its number is past every group the file named; the Reads
    of its echo pins are the patch's, not the group's."""
    doc = {"schema": "hyperspace.loadable/12", "name": "t",
           "graph": {"frame": "wired", "nodes": [{"kind": "effect", "file": "acid"}],
                     "wires": [{"from": "scene", "to": "lookback.image"},
                               {"from": "scene", "to": "lookback.occluder"},
                               {"from": "lookback", "to": "acid.image"},
                               {"from": "lookback.echo.2", "to": "shape.faces"},
                               {"from": "acid", "to": "output.all.image"}]},
           "values": {"dream.echoes": 8},
           "groups": [{"id": "group.4", "name": "mine", "nodes": ["render:acid"], "open": True}]}
    got, _ = graphmigrate.lookbacks(doc)
    assert got["groups"][0] == doc["groups"][0]
    g = got["groups"][1]
    assert g["id"] == "group.5" and g["name"] == graphmigrate.LB_GROUP and g["open"] is False
    assert g["nodes"] == ["render:fade", "render:resize", "render:delay", "render:trail",
                          "render:matte", "render:cut"]   # (no faces: no cover cut)
    assert doc["groups"] == [{"id": "group.4", "name": "mine", "nodes": ["render:acid"],
                              "open": True}]        # (pure)


def test_an_old_look_back_file_opens_with_its_group(tmp_path):
    from hyperspace import headless
    raw, notes, _ = headless.resave(TRACER, tmp_path / "a")
    groups = json.loads(raw)["groups"]
    assert [(g["name"], g["open"]) for g in groups] == [(graphmigrate.LB_GROUP, False)]
    assert "render:trail" in groups[0]["nodes"] and "render:cut.2" in groups[0]["nodes"]
    assert not [n for n in notes if n.startswith("groups:")], notes


def test_a_look_back_a_group_of_the_file_held_brings_its_parts_into_it():
    """Old files could group the look-back itself (`render:lookback`): its
    parts join that group — a node is in one group at most — and no
    second group is made."""
    doc = {"schema": "hyperspace.loadable/12", "name": "t",
           "graph": {"frame": "wired", "nodes": [{"kind": "effect", "file": "acid"}],
                     "wires": [{"from": "scene", "to": "lookback.image"},
                               {"from": "lookback", "to": "acid.image"},
                               {"from": "acid", "to": "output.all.image"}]},
           "values": {"dream.echoes": 8},
           "groups": [{"id": "group.1", "name": "mine",
                       "nodes": ["render:acid", "render:lookback"], "open": True}]}
    got, _ = graphmigrate.lookbacks(doc)
    assert got["groups"] == [{"id": "group.1", "name": "mine", "open": True, "nodes": [
        "render:acid", "render:delay", "render:fade", "render:resize", "render:trail"]}]


# ---------------------------------------------------------------- a fragment with no dream

def test_a_fragment_with_no_dream_keeps_none_of_the_dreams_values():
    """A saved look-back fragment holds the dream's shared knobs (darken,
    contrast, res) from its lift; with no dream node in it they are the
    host's, and `patches.check` refuses a fragment setting them — so they go
    with the look-back (its parts hold the converted copies)."""
    doc = {"schema": patches.SCHEMA, "name": "f",
           "nodes": [{"kind": "composite", "blend": "add"}],
           "wires": [{"from": "lookback", "to": "composite.over"}],
           "ports": [{"id": "in", "type": "image", "to": "lookback.image", "was": "scene"},
                     {"id": "out", "type": "image", "from": "composite",
                      "was": "output.all.image"}],
           "values": {"dream.echoes": 4, "dream.darken": 0.2, "dream.contrast": 1.0,
                      "dream.res": 2}}
    got = patches.forward(doc)
    assert not [k for k in got["values"] if k.startswith("dream.")], got["values"]
    assert got["values"]["fx.fade.level"] == pytest.approx(0.8)
    assert patches.check(got) == []


def test_a_look_back_into_a_look_back_takes_the_first_ones_parts():
    doc = {"schema": "hyperspace.loadable/12", "name": "t",
           "graph": {"frame": "wired",
                     "wires": [{"from": "scene", "to": "lookback.image"},
                               {"from": "lookback", "to": "lookback.2.image"},
                               {"from": "lookback.2", "to": "output.all.image"},
                               {"from": "shape", "to": "scene.geometry"},
                               {"from": "pattern", "to": "shape.faces"}]},
           "values": {}}
    got, _ = graphmigrate.lookbacks(doc)
    wires = got["graph"]["wires"]
    assert not [w for w in wires if "lookback" in w["from"] or "lookback" in w["to"]], wires
    assert {"from": "trail", "to": "fade.2.image"} in wires
    spec = G.read_graph(got["graph"], effects={"fade", "trail"})
    assert not spec.notes, spec.notes


def test_the_master_switch_keeps_wire_declared_and_default_mix_effects_as_they_drew():
    """An effect declared by a wire alone is the patch's too: switched off
    where the master was; one with no saved mix is at its file's mix (here
    acid's 1), scaled by the master's."""
    doc = {"schema": "hyperspace.loadable/12", "name": "t",
           "graph": {"frame": "wired",
                     "wires": [{"from": "scene", "to": "acid.image"},
                               {"from": "acid", "to": "lookback.image"},
                               {"from": "lookback", "to": "output.all.image"},
                               {"from": "shape", "to": "scene.geometry"},
                               {"from": "pattern", "to": "shape.faces"}]},
           "values": {"fx.on": False, "fx.acid.on": True}}
    got, _ = graphmigrate.lookbacks(doc)
    assert got["values"]["fx.on"] is True and got["values"]["fx.acid.on"] is False
    doc["values"] = {"fx.mix": 0.25, "fx.acid.on": True}
    got, _ = graphmigrate.lookbacks(doc)
    assert got["values"]["fx.mix"] == 1.0
    assert got["values"]["fx.acid.mix"] == pytest.approx(0.25)


def test_a_fragment_with_no_dream_keeps_its_rows_onto_the_hosts_dream():
    """Only the dream's values are the host's in
    a fragment with no dream — a row from the fragment's own LFO (voice 1,
    lane `lfo:0`) onto `dream.contrast` may drive the host's, and keeps doing so beside the
    Curve it now drives too. The host's dream has no contrast
    (an effect, `fx.dream.*`), so that copy is left out, said — the row drives the
    Curve alone."""
    doc = {"schema": patches.SCHEMA, "name": "f",
           "nodes": [{"kind": "composite", "blend": "add"}],
           "wires": [{"from": "lookback", "to": "composite.over"}],
           "ports": [{"id": "in", "type": "image", "to": "lookback.image", "was": "scene"},
                     {"id": "out", "type": "image", "from": "composite",
                      "was": "output.all.image"}],
           "lfos": [1],
           "routes": [{"source": "lfo:0", "target": "dream.contrast", "op": "push",
                       "value": 0.2}],
           "values": {"dream.echoes": 4, "dream.contrast": 1.0}}
    got = patches.forward(doc)
    targets = sorted(r["target"] for r in got["routes"])
    assert targets == ["fx.curve.shape"], got["routes"]
    assert "dream.contrast" not in got["values"]
    assert patches.check(got) == []


def test_a_fragment_with_no_dream_drops_a_desk_row_onto_the_hosts_dream():
    """A row whose source is not the fragment's
    own (a desk knob) onto the host's dream is nothing of the patch's —
    `patches.check` refused the whole file. It goes; its copy onto the part
    stays, and a row from the fragment's own LFO keeps both (above)."""
    doc = {"schema": patches.SCHEMA, "name": "f",
           "nodes": [{"kind": "composite", "blend": "add"}],
           "wires": [{"from": "lookback", "to": "composite.over"}],
           "ports": [{"id": "in", "type": "image", "to": "lookback.image", "was": "scene"},
                     {"id": "out", "type": "image", "from": "composite",
                      "was": "output.all.image"}],
           "desk": [{"source": "cc:0:48", "target": "dream.contrast", "op": "abs"}],
           "values": {"dream.echoes": 4, "dream.contrast": 1.0}}
    got = patches.forward(doc)
    assert [r["target"] for r in got["desk"]] == ["fx.curve.shape"], got["desk"]
    assert patches.check(got) == []


@pytest.mark.parametrize("bad", [{"routes": [{"source": "cc:0:1", "target": [], "op": "abs"}]},
                                 {"lfos": 1}], ids=["list-target", "lfos-a-number"])
def test_a_malformed_fragment_migrates_and_is_refused_by_check(bad):
    """The filter of rows onto the host's dream
    reads the file before `check` does — a malformed one must pass through
    to be refused in words (a LibraryError), never raise and stop the list."""
    doc = {"schema": patches.SCHEMA, "name": "f",
           "nodes": [{"kind": "composite", "blend": "add"}],
           "wires": [{"from": "lookback", "to": "composite.over"}],
           "ports": [{"id": "in", "type": "image", "to": "lookback.image", "was": "scene"},
                     {"id": "out", "type": "image", "from": "composite",
                      "was": "output.all.image"}],
           "values": {"dream.echoes": 4}, **bad}
    got = patches.forward(doc)
    assert patches.check(got) != []
