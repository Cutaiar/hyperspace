"""Plan 90 H3: a saved dream opens as public parts, folded in one group
(Q31): Resize (keyed: brightness is coverage) → Dream → Hue turn / Palette /
Curve, each only where its old value is off neutral → Fade (mix × (1 −
darken)) → Composite over the input. `graphmigrate.dreams`, the ladder's
last step after the look-back's; `patches.forward` for a fragment. The old
`dream.*` ids move to `fx.dream.*` (the worker's) or onto the parts."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from hyperspace import graph as G
from hyperspace import graphmigrate as GM
from hyperspace import patches

HERE = Path(__file__).parent


def doc(values=None, wires=None, nodes=None, **rest):
    return {"schema": GM.TWELVE_SCHEMA, "name": "t",
            "graph": {"frame": "wired",
                      "nodes": nodes if nodes is not None else [{"kind": "dream"}],
                      "wires": wires if wires is not None else [
                          {"from": "scene", "to": "dream.image"},
                          {"from": "dream", "to": "output.all.image"}]},
            "values": {"dream.on": True, **(values or {})}, **rest}


def migrated(d):
    out, notes = GM.dreams(d)
    return out, notes, out["graph"]


def node_files(g):
    return [e.get("file") or e.get("kind") for e in g["nodes"]]


def into(g, port):
    return [w["from"] for w in g["wires"] if w["to"] == port]


# ---------------------------------------------------------------- the chain

def test_a_default_dream_is_resize_dream_fade_composite_over_its_input():
    out, notes, g = migrated(doc())
    assert sorted(node_files(g)) == ["composite", "dream", "fade", "resize"]
    assert {"kind": "dream"} not in g["nodes"]
    assert into(g, "resize.image") == ["scene"]
    assert into(g, "dream.image") == ["resize"]
    assert into(g, "fade.image") == ["dream"]
    assert into(g, "composite.over") == ["fade"]
    assert into(g, "composite.under") == ["scene"]
    assert into(g, "output.all.image") == ["composite"]
    assert g["keys"] == ["resize"]                    # brightness is coverage, as the mask
    v = out["values"]
    assert v["fx.dream.on"] is True and v["fx.dream.mix"] == 1.0 and v["fx.dream.blend"] == 0
    assert v["fx.dream.k"] == 0.05                    # the old default, written (Q32)
    assert v["fx.dream.layer"] == 1 and v["fx.dream.steps"] == 2
    assert v["fx.fade.level"] == pytest.approx(0.7 * 0.9)      # mix × (1 − darken)
    assert v["resize.size"] == 5                      # res 256 short → 512 long (16 : 10)
    assert v["key.resize.measure"] == 0 and v["key.resize.ramp"] == 1
    assert v["key.resize.soft"] == pytest.approx(0.25)          # 4 × brightness, as the mask
    comp = next(e for e in g["nodes"] if e["kind"] == "composite")
    assert comp.get("blend", "over") == "over"
    assert not any(k.startswith("dream.") for k in v)
    assert any("public parts" in n for n in notes)
    G.read_graph(g, effects={"dream", "fade", "hueturn", "palette", "curve"})


def test_it_folds_in_one_group_named_dream():
    out, _, _ = migrated(doc())
    (grp,) = out[GM.GROUPS_KEY]
    assert grp["name"] == GM.DREAM_GROUP == "dream" and grp["open"] is False
    assert set(grp["nodes"]) == {"render:resize", "render:dream", "render:fade",
                                 "render:composite"}


def test_the_trail_group_is_named_trail():
    assert GM.LB_GROUP == "trail"                     # Q29


def test_grades_off_neutral_are_parts_in_the_old_order():
    out, _, g = migrated(doc({"dream.hue": 90.0, "dream.sat": 1.2, "dream.tint": 0.5,
                              "dream.tint_hue": 30.0, "dream.tint_sat": 0.8,
                              "dream.contrast": 2.0, "dream.darken": 0.0, "dream.mix": 0.5}))
    assert into(g, "hueturn.image") == ["dream"]
    assert into(g, "palette.image") == ["hueturn"]
    assert into(g, "curve.image") == ["palette"]
    assert into(g, "fade.image") == ["curve"]
    v = out["values"]
    assert v["fx.hueturn.turn"] == 90.0 and v["fx.hueturn.sat"] == 1.2
    assert v["fx.hueturn.paint"] == 0.0 and v["fx.hueturn.speed"] == 0.0
    assert v["fx.palette.mode"] == 1 and v["fx.palette.anchors"] == 2
    assert v["fx.palette.mix"] == 0.5 and v["fx.palette.a2_hue"] == 30.0
    assert v["fx.palette.a2_sat"] == 0.8 and v["fx.palette.a1_val"] == 0.0
    assert v["fx.curve.shape"] == pytest.approx(math.log(2.0) / math.log(4.0))
    assert v["fx.fade.level"] == pytest.approx(0.5)


def test_a_negative_hue_turns_the_other_way_round_the_wheel():
    out, _, _ = migrated(doc({"dream.hue": -90.0}))
    assert out["values"]["fx.hueturn.turn"] == 270.0


def test_neutral_grades_bring_no_part():
    _, _, g = migrated(doc({"dream.hue": 0.0, "dream.sat": 1.0, "dream.tint": 0.0,
                            "dream.contrast": 1.0}))
    assert not {"hueturn", "palette", "curve"} & set(node_files(g))


def test_a_tint_from_the_scene_keeps_its_chosen_colour_said():
    out, notes, _ = migrated(doc({"dream.tint": 1.0, "dream.tint_from": 1}))
    assert out["values"]["fx.palette.a2_hue"] == 200.0
    assert any("tint from the scene" in n for n in notes)


def test_res_sets_the_resize_and_the_linger_merges_into_hold_said():
    out, notes, _ = migrated(doc({"dream.res": 0, "dream.mask_decay": 0.95}))
    assert out["values"]["resize.size"] == 4                    # 128 short → 256 long
    assert any("mask_decay" in n and "Hold" in n for n in notes)


def test_a_dream_off_and_undriven_drew_nothing_left_out_said():
    out, notes, g = migrated(doc({"dream.on": False}))
    assert node_files(g) == []
    assert into(g, "output.all.image") == ["scene"]
    assert any("was off" in n for n in notes)
    assert not any(k.startswith(("dream.", "fx.dream.")) for k in out["values"])


def test_a_dream_off_but_driven_keeps_its_parts_off():
    d = doc({"dream.on": False}, routes=[{"source": "key:d", "target": "dream.on",
                                         "op": "toggle"}])
    out, _, g = migrated(d)
    assert "dream" in node_files(g) and out["values"]["fx.dream.on"] is False
    assert out["routes"][0]["target"] == "fx.dream.on"


def test_an_unfed_dream_wires_what_it_can():
    out, _, g = migrated(doc(wires=[{"from": "dream", "to": "output.all.image"}]))
    assert into(g, "resize.image") == [] and into(g, "composite.under") == []
    assert into(g, "output.all.image") == ["composite"]


def test_a_second_dream_drew_nothing_left_out_said():
    out, notes, g = migrated(doc(nodes=[{"kind": "dream"}, {"kind": "dream", "instance": 2}]))
    assert node_files(g).count("dream") == 1
    assert any("dream.2" in n for n in notes)


def test_new_parts_take_the_next_free_instances():
    nodes = [{"kind": "dream"}, {"kind": "composite"}, {"kind": "effect", "file": "fade"}]
    wires = [{"from": "scene", "to": "fade.image"}, {"from": "fade", "to": "dream.image"},
             {"from": "dream", "to": "composite.over"}, {"from": "scene", "to": "composite.under"},
             {"from": "composite", "to": "output.all.image"}]
    _, _, g = migrated(doc(nodes=nodes, wires=wires))
    assert into(g, "resize.image") == ["fade"]
    assert "composite.2" in into(g, "composite.over") or into(g, "composite.over") == [
        "composite.2"]
    assert into(g, "composite.2.under") == ["fade"]
    assert into(g, "fade.2.image") == ["dream"]


# ---------------------------------------------------------------- ids and rows

def test_whole_number_knobs_land_whole():
    out, _, _ = migrated(doc({"dream.steps": 2.0, "dream.jitter": 8.0, "dream.layer": 3.0}))
    v = out["values"]
    assert [type(v[f"fx.dream.{k}"]) for k in ("steps", "jitter", "layer")] == [int] * 3


def test_the_workers_ids_move_to_the_effects():
    out, _, _ = migrated(doc({"dream.layer": 4, "dream.octaves": 2, "dream.jitter": 3,
                              "dream.step": 0.02, "dream.steps": 3, "dream.k": 0.1}))
    v = out["values"]
    assert (v["fx.dream.layer"], v["fx.dream.octaves"], v["fx.dream.jitter"],
            v["fx.dream.step"], v["fx.dream.steps"], v["fx.dream.k"]) == (4, 2, 3, 0.02, 3, 0.1)


def test_rows_follow_their_knob():
    rows = [{"source": "lfo:1", "target": "dream.step", "op": "push", "value": 0.2},
            {"source": "lfo:2", "target": "dream.hue", "op": "push", "value": 0.5},
            {"source": "lfo:3", "target": "dream.mix", "op": "push", "value": 0.4},
            {"source": "lfo:4", "target": "dream.res", "op": "push", "value": 0.4}]
    out, notes, g = migrated(doc(routes=rows))
    got = {r["source"]: r for r in out["routes"]}
    assert got["lfo:1"]["target"] == "fx.dream.step" and got["lfo:1"]["value"] == 0.2
    assert got["lfo:2"]["target"] == "fx.hueturn.turn"          # a driven hue brings Hue turn
    assert "hueturn" in node_files(g)
    assert got["lfo:3"]["target"] == "fx.fade.level"
    assert got["lfo:3"]["value"] == pytest.approx(0.4 * 0.9)    # × (1 − darken)
    assert "lfo:4" not in got and any("dream.res" in n for n in notes)


def test_a_row_on_hold_keeps_its_reach_on_the_log_range():
    rows = [{"source": "lfo:1", "target": "dream.k", "op": "set", "value": 0.5}]
    out, _, _ = migrated(doc(routes=rows))
    k = 0.03 + 0.5 * 0.27                       # the old linear 0.03 … 0.3
    want = math.log(k / 0.03) / math.log(1.0 / 0.03)
    assert out["routes"][0]["value"] == pytest.approx(want, abs=1e-6)


def test_the_master_switch_compensated_as_the_look_backs():
    d = doc({"fx.on": False, "fx.acid.on": True},
            nodes=[{"kind": "dream"}, {"kind": "effect", "file": "acid"}])
    out, notes, _ = migrated(d)
    v = out["values"]
    assert v["fx.on"] is True and v["fx.acid.on"] is False
    assert any("fx.on" in n for n in notes)


def test_a_file_with_no_dream_is_untouched_but_loses_old_ids_quietly():
    d = {"schema": GM.TWELVE_SCHEMA, "name": "t",
         "graph": {"frame": "wired", "nodes": [], "wires": []},
         "values": {"dream.layer": 3, "dream.darken": 0.1, "fx.acid.on": True}}
    out, notes = GM.dreams(d)
    assert out["values"] == {"fx.acid.on": True} and notes == []
    plain = {**d, "values": {"fx.acid.on": True}}
    assert GM.dreams(plain)[0] is plain


def test_it_runs_once():
    out, _, _ = migrated(doc())
    again, notes = GM.dreams(out)
    assert again is out and notes == []


# ---------------------------------------------------------------- the ladders

def test_the_ladder_runs_it_last():
    fw = GM.forward(doc(), {})
    assert "dream" in node_files(fw.doc["graph"])
    assert any("public parts" in n for n in fw.migrate_notes)


def test_party_wake_opens_whole():
    raw = json.loads((HERE / "corpus/loadable/party-wake.json").read_text())
    fw = GM.forward(raw, {})
    g = fw.doc["graph"]
    assert "hueturn" in node_files(g)                  # its sat 1.2
    spec = G.read_graph(g, effects={"dream", "fade", "hueturn", "trail", "read", "curve",
                                    "palette", *(e["file"] for e in g["nodes"]
                                                 if e.get("kind") == "effect")})
    assert not [n for n in spec.notes if "dream" in n], spec.notes


def test_a_fragment_holding_a_dream_is_its_parts():
    frag = {"schema": patches.SCHEMA, "name": "f",
            "nodes": [{"kind": "dream"}],
            "wires": [],
            "ports": [{"id": "in", "type": "image", "to": "dream.image", "was": "scene"},
                      {"id": "out", "type": "image", "from": "dream",
                       "was": "output.all.image"}],
            "values": {"dream.on": True, "dream.mix": 0.5}}
    out = patches.forward(frag)
    assert {"kind": "dream"} not in out["nodes"]
    ins = [p for p in out["ports"] if "to" in p]
    assert {p["to"] for p in ins} == {"resize.image", "composite.under"}
    assert len({p["id"] for p in out["ports"]}) == len(out["ports"])     # ids unique
    assert {p.get("was") for p in ins} == {"scene"}
    assert [p["from"] for p in out["ports"] if "from" in p] == ["composite"]
    assert not any(k.startswith("dream.") for k in out["values"])


# ---------------------------------------------------------------- old dream presets (Q33)

def test_old_dream_presets_are_retired_left_on_disk_and_said_once(tmp_path):
    from types import SimpleNamespace as NS

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import RETIRED_MODULES, Library
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState

    folder = tmp_path / "patches" / "dream"
    folder.mkdir(parents=True)
    old = folder / "wake.json"
    old.write_text(json.dumps({"schema": "hyperspace.patch/2", "name": "wake",
                               "group": "dream", "values": {"dream.k": 0.08}}))
    chain = Analyzer(Analyser())
    reg = build_registry(ViewState(), Control(chain), NS(chain=chain))
    lib = Library(tmp_path)
    lib.attach(reg)
    assert "dream" in RETIRED_MODULES and "dream" not in lib.groups()
    assert "dream" in lib.warning and "1 preset" in lib.warning
    lib.warning = ""
    lib.groups()
    assert lib.warning == ""                       # once
    assert old.exists()                            # left on disk


def test_an_old_frame_as_the_whole_ladder_ends_it_has_its_dream_as_parts():
    """`split_retired` (the golden rig's and `wired_of`'s road) ends as the
    ladder does: the dream an old "dream" look drew is its parts too — on,
    since that look was the dream drawn."""
    sec = GM.split_retired(GM.wired_of(G.Wiring(), placements=False), "dream")
    files = [e.get("file") or e.get("kind") for e in sec["nodes"]]
    assert "dream" in files and {"kind": "dream"} not in sec["nodes"]
    assert "resize" in files and "composite" in files
