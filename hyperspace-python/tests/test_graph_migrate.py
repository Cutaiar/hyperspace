"""Plan 33 M: old presets as wires, and wires back as /4 values (graphmigrate)."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_plan31_wiring import make_app

from hyperspace import fx, preset
from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace.library import LibraryError

ROOT = Path(__file__).parent.parent / "hyperspace"
FILES = sorted([*(ROOT / "library" / "presets").glob("*.json"),
                *(ROOT / "library" / "fx").glob("*.json")])
# the presets written before plan 33 (a `/5` fixture — plan 33 T4's proofs —
# is the free graph's own: nothing to migrate, nothing `/4` can say)
FIXTURES = sorted(p for p in [*(ROOT / "library" / "presets").glob("*.json"),
                              *(Path(__file__).parent / "fixtures" / "presets").glob("*.json"),
                              *(Path(__file__).parent / "fixtures" / "merge-31-32").glob("*.json")]
                  if json.loads(p.read_text()).get("schema") != M.FREE_SCHEMA)
EFFECTS = {p.stem: fx.parse(p.stem, p.read_text())
           for p in (ROOT / "shaders" / "fx").glob("*.glsl") if not p.stem.startswith("_")}
SPECS = {n: (s.order, s.mix) for n, s in EFFECTS.items()}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def old_run(doc: dict, side: int = 0) -> list[str]:
    """The old rule: sorted by (order, name), on and mix > 0, aimed at `side`."""
    v = doc.get("values") or {}
    driven = {n for n in (M.effect_of(p) for p in M.targets(doc)) if n}
    names = set(SPECS) | {n for n in (M.effect_of(k) for k in v) if n}
    section = doc.get("graph")
    if section:                                    # a placed or wired effect leaves the stack
        names -= M._wired_effects(G.read_graph(section))
    live = [n for n in names if v.get(f"fx.{n}.on")
            and (v.get(f"fx.{n}.mix", EFFECTS[n.partition('.')[0]].mix) > 0 or n in driven)
            and (1 if v.get(f"fx.{n}.target", 0) == 1 else 0) == side]
    return sorted(live, key=lambda n: (v.get(f"fx.{n}.order", SPECS[n.partition('.')[0]][0]), n))


def runs(section: dict):
    spec = G.read_graph(section)
    return list(G.run_of(spec)), list(G.run_of(spec, "pattern", "shape.faces"))


def wires_of(section: dict) -> set[tuple[str, str]]:
    return {(w["from"], w["to"]) for w in section.get("wires", [])}


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_every_library_preset_migrates_without_a_note(path):
    doc = load(path)
    section, notes = M.to_free(doc, SPECS)
    assert notes == []
    frame, faces = runs(section)
    assert frame == old_run(doc, 0)
    assert faces == old_run(doc, 1)


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_no_library_preset_routes_an_effect_it_leaves_out(path):
    """The owner's reading (row 346): no preset routes an off effect. A
    failure is a preset to look at, not a test to loosen."""
    doc = load(path)
    section, _ = M.to_free(doc, SPECS)
    frame, faces = runs(section)
    left = sorted({n for n in (M.effect_of(p) for p in M.targets(doc)) if n}
                  - {*frame, *faces})
    assert left == [], f"{path.name} routes {left}, which the migration leaves out"


def test_mandala_keeps_kaleido_first():
    """`fx.kaleido.order = 8` is read: kaleido sits where it did, right
    after the plasma (order 5) it folds and before the fractals (60)."""
    doc = load(ROOT / "library" / "fx" / "mandala.json")
    assert doc["values"]["fx.kaleido.order"] == 8
    section, _ = M.to_free(doc, SPECS)
    assert G.run_of(G.read_graph(section)) == ("plasma", "kaleido", "fractals", "glimmer")
    doc["values"]["fx.kaleido.order"] = 1                  # and a lower order is read too
    section, _ = M.to_free(doc, SPECS)
    assert G.run_of(G.read_graph(section))[0] == "kaleido"


def base(**values) -> dict:
    return {"schema": "hyperspace.preset/2", "name": "t", "values": values}


@pytest.mark.parametrize("how", ["route", "desk", "macro", "modifier", "sequencer"])
def test_an_off_effect_left_out_says_so_when_something_drives_it(how):
    doc = base(**{"fx.warp.on": False, "fx.acid.on": True})
    target = "fx.warp.mix"
    if how == "route":
        doc["routes"] = [{"source": "lfo:0", "target": target, "op": "push"}]
    elif how == "desk":
        doc["desk"] = [{"source": "midi:cc:1", "target": target, "op": "abs"}]
    elif how == "macro":
        doc["macros"] = {"macro.1": {"subs": [{"base": target}]}}
    elif how == "modifier":
        doc["modifiers"] = [{"id": "mod.1", "kind": "smooth", "in": ["lfo:0"]}]
        doc["routes"] = [{"source": "mod:1", "target": target, "op": "push"}]
    else:
        doc["routes"] = [{"source": "env:0", "target": target, "op": "push"}]
    section, notes = M.to_free(doc, SPECS)
    assert "warp" not in G.run_of(G.read_graph(section))
    assert notes == ["warp was off, so it is not in the run: wire it in on GRAPH to use it"]


def test_faces_aimed_effects_become_the_faces_run():
    doc = base(**{"fx.acid.on": True, "fx.acid.target": 1})
    section, notes = M.to_free(doc, SPECS)
    assert notes == []
    assert wires_of(section) == {("frame", "fx.image"), ("pattern", "acid.image"),
                                 ("acid", "shape.faces")}


def test_a_run_is_sorted_and_an_instance_is_declared():
    doc = base(**{"fx.acid.on": True, "fx.wobble.on": True, "fx.acid.2.on": True,
                  "fx.acid.2.order": 12, "fx.wobble.mix": 0.0, "fx.warp.on": True})
    section, _ = M.to_free(doc, SPECS)
    assert G.run_of(G.read_graph(section)) == ("acid", "acid.2", "warp")
    assert {"kind": "effect", "file": "acid", "instance": 2} in section["nodes"]


def test_a_wired_effect_is_not_given_to_the_run():
    doc = base(**{"fx.acid.on": True, "fx.warp.on": True})
    doc["graph"] = {"nodes": [], "wires": [{"from": "media.a", "to": "warp.image"},
                                           {"from": "warp", "to": "output.2.image"}]}
    section, _ = M.to_free(doc, SPECS)
    assert G.run_of(G.read_graph(section)) == ("acid",)


def test_a_section_with_a_frame_run_is_unchanged():
    doc = base(**{"fx.acid.on": True, "fx.warp.on": True, "view.media": 2})
    doc["graph"] = {"nodes": [], "wires": [{"from": "frame", "to": "warp.image"},
                                           {"from": "warp", "to": "fx.image"},
                                           {"from": "media.c", "to": "pattern.media"}]}
    assert M.to_free(doc, SPECS)[0] == doc["graph"]


def test_view_media_and_backdrop_channel_become_wires():
    doc = base(**{"view.media": 3, "backdrop.channel": 2})
    section, _ = M.to_free(doc, SPECS)
    assert wires_of(section) == {("frame", "fx.image"), ("media.c", "pattern.media"),
                                 ("media.b", "backdrop.image")}
    out, _ = M.migrate(doc, SPECS)
    assert not any(M.retired(k) for k in out["values"])


def test_a_route_onto_view_media_becomes_a_switch():
    doc = base(**{"view.media": 2, "backdrop.channel": 4})
    doc["routes"] = [{"source": "lfo:0", "target": "view.media", "op": "push"},
                     {"source": "lfo:1", "target": "backdrop.channel", "op": "push"}]
    doc["desk"] = [{"source": "midi:cc:1", "target": "view.media", "op": "abs"}]
    out, notes = M.migrate(doc, SPECS)
    section = out["graph"]
    assert notes == []
    assert {"kind": "switch"} in section["nodes"]
    assert {"kind": "switch", "instance": 2} in section["nodes"]
    w = wires_of(section)
    for sw, end in (("switch", "pattern.media"), ("switch.2", "backdrop.image")):
        assert {(f"media.{c}", f"{sw}.in{i}") for i, c in enumerate("abcdefgh", 1)} <= w
        assert (sw, end) in w
    assert out["values"]["switch.select"] == 2
    assert out["values"]["switch.2.select"] == 4
    assert out["routes"][0]["target"] == "switch.select"
    assert out["routes"][1]["target"] == "switch.2.select"
    assert out["desk"][0]["target"] == "switch.select"
    spec = G.read_graph(section)
    assert not spec.notes and [s.name for s in spec.switches] == ["switch", "switch.2"]


def test_a_route_onto_only_the_backdrop_takes_the_first_switch():
    doc = base(**{"backdrop.channel": 1})
    doc["macros"] = {"macro.1": {"subs": [{"base": "backdrop.channel"}]}}
    out, _ = M.migrate(doc, SPECS)
    assert out["macros"]["macro.1"]["subs"][0]["base"] == "switch.select"
    assert ("switch", "backdrop.image") in wires_of(out["graph"])


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_legacy_values_inverts_to_free(path):
    doc = load(path)
    values = doc.get("values") or {}
    section, _ = M.to_free(doc, SPECS)
    got = M.legacy_values(section, values, SPECS, M.targets(doc))
    assert got is not None
    frame, faces = runs(section)
    for n in [*frame, *faces]:
        for key in (f"fx.{n}.order", f"fx.{n}.target"):
            if key in values:
                assert got[key] == values[key], key
    for key in ("view.media", "backdrop.channel"):
        if key in values:
            assert got[key] == values[key]
    # and applied, the old rule gives the same runs
    back = {**values, **got}
    back = {"values": back, "graph": doc.get("graph"), "routes": doc.get("routes"),
            "desk": doc.get("desk"), "macros": doc.get("macros")}
    assert old_run(back, 0) == frame and old_run(back, 1) == faces


def test_legacy_values_moves_the_fewest_orders():
    section = {"nodes": [], "wires": [{"from": "frame", "to": "wobble.image"},
                                      {"from": "wobble", "to": "acid.image"},
                                      {"from": "acid", "to": "fx.image"}]}
    values = {"fx.wobble.on": True, "fx.acid.on": True}
    got = M.legacy_values(section, values, SPECS)
    assert got is not None and len(got) == 1          # one move is enough
    assert old_run({"values": {**values, **got}}) == ["wobble", "acid"]


@pytest.mark.parametrize("section", [
    # a branch
    {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
     "wires": [{"from": "media.a", "to": "acid.2.image"}, {"from": "acid.2", "to": "shape.faces"}]},
    # an unreached effect
    {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
     "wires": [{"from": "media.a", "to": "acid.2.image"}]},
    # a switch
    {"nodes": [{"kind": "switch"}], "wires": [{"from": "switch", "to": "pattern.media"}]},
    # a non-channel into the pattern's media
    {"nodes": [], "wires": [{"from": "frame", "to": "acid.image"},
                            {"from": "acid", "to": "pattern.media"}]},
    # two runs from the frame
    {"nodes": [], "wires": [{"from": "frame", "to": "acid.image"},
                            {"from": "acid", "to": "fx.image"},
                            {"from": "frame", "to": "warp.image"},
                            {"from": "warp", "to": "output.2.image"}]},
])
def test_legacy_values_is_none_for_what_four_cannot_say(section):
    values = {"fx.acid.on": True, "fx.warp.on": True, "fx.acid.2.on": True}
    assert M.legacy_values(section, values, SPECS) is None


def test_an_effect_on_outside_every_run_is_not_a_four():
    section = {"nodes": [], "wires": [{"from": "frame", "to": "acid.image"},
                                      {"from": "acid", "to": "fx.image"}]}
    assert M.legacy_values(section, {"fx.acid.on": True, "fx.warp.on": True}, SPECS) is None
    assert M.legacy_values(section, {"fx.acid.on": True}, SPECS) is not None


BRANCH = {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
          "wires": [{"from": "media.a", "to": "acid.2.image"},
                    {"from": "acid.2", "to": "shape.faces"}]}


def test_a_branch_saves_as_v5_and_reloads(tmp_path):
    doc = {"schema": "hyperspace.preset/2", "name": "t", "graph": BRANCH, "values": {}}
    assert preset.schema_of(doc) == M.FREE_SCHEMA == "hyperspace.preset/5"
    assert G.read_graph(copy.deepcopy(BRANCH)).to_json() == BRANCH
    app = make_app(tmp_path)
    assert app.presets.load_doc(copy.deepcopy(doc)) == []
    saved = app.presets.document("t")
    # (plan 33 T3: the load gave it its run's head, the empty run — R9)
    head = {**BRANCH, "wires": [*BRANCH["wires"], {"from": "frame", "to": "fx.image"}]}
    assert saved["schema"] == M.FREE_SCHEMA and saved["graph"] == head
    assert app.presets.load_doc(copy.deepcopy(saved)) == []
    assert app.presets.document("t")["graph"] == head          # and reloads as it saved


def test_a_preset_with_no_free_words_keeps_its_schema():
    assert preset.schema_of({"values": {"fx.acid.on": True}}) == preset.SCHEMA
    hands = {"graph": {"nodes": [{"kind": "effect", "file": "palette", "after": "hands"}]},
             "values": {"fx.palette.on": True}}
    assert preset.schema_of(hands) == preset.SCHEMA
    comp = {"graph": {"nodes": [{"kind": "composite"}],
                      "wires": [{"from": "scene", "to": "composite.under"},
                                {"from": "history", "to": "composite.over"},
                                {"from": "composite", "to": "output.2.image"}]}}
    assert preset.schema_of(comp) == preset.SCHEMA


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_no_existing_preset_changes_schema(path):
    doc = load(path)
    assert preset.schema_of(doc) == doc["schema"] or doc["schema"] not in (
        preset.SCHEMA, preset.SCHEMA_V3, preset.MEDIA_SCHEMA)
    assert preset.schema_of(doc) != M.FREE_SCHEMA


def test_v5_is_refused_by_the_ladder_below(tmp_path):
    app = make_app(tmp_path)
    app.presets.load_doc({"schema": "hyperspace.preset/2", "name": "five", "graph": BRANCH,
                          "values": {}})
    app.presets.save_as("five")
    lib = app.lib
    assert lib.read("presets", "five")["schema"] == M.FREE_SCHEMA
    kinds = lib._kinds
    assert preset.VERSIONS == (2, 3, 4, 5)
    try:
        kinds["presets"] = replace(kinds["presets"], versions=(2, 3, 4))
        with pytest.raises(LibraryError, match="is not a hyperspace.preset"):
            lib.read("presets", "five")
    finally:
        kinds["presets"] = replace(kinds["presets"], versions=preset.VERSIONS)


def test_an_empty_run_is_written_as_frame_to_fx():
    section, notes = M.to_free(base(**{"fx.acid.on": False}), SPECS)
    assert notes == [] and wires_of(section) == {("frame", "fx.image")}
    assert runs(section) == ([], [])
    assert M.to_free({"values": {}, "graph": section}, SPECS)[0] == section      # and stays


def test_a_driven_effect_on_at_mix_zero_stays_in_the_run():
    doc = base(**{"fx.acid.on": True, "fx.acid.mix": 0.0, "fx.warp.on": True, "fx.warp.mix": 0.0})
    doc["routes"] = [{"source": "lfo:0", "target": "fx.acid.mix", "op": "push"}]
    section, notes = M.to_free(doc, SPECS)
    assert G.run_of(G.read_graph(section)) == ("acid",) and notes == []


def test_a_migrated_section_with_its_run_cleared_and_effects_on_saves_v5():
    doc = base(**{"fx.acid.on": True})
    cleared = {"nodes": [], "wires": [{"from": "frame", "to": "fx.image"}]}
    assert preset.schema_of({**doc, "graph": cleared}) == M.FREE_SCHEMA
    migrated, _ = M.to_free(doc, SPECS)
    assert preset.schema_of({**doc, "graph": migrated}) != M.FREE_SCHEMA     # a /4 can say it
    off = base(**{"fx.acid.on": False})
    assert preset.schema_of({**off, "graph": cleared}) != M.FREE_SCHEMA


def test_a_legacy_shortened_placement_migrates_to_an_explicit_after():
    """The owner, 2026-10-24: a free section shortens no wire, so a pre-33
    section's wire D1 would write short (`scene → acid.2.image`, nothing out
    of acid.2) becomes the D1 entry it stood for, before the run is added —
    the same placement, and the same picture. `into` likewise."""
    doc = {**base(**{"fx.acid.2.on": True, "fx.palette.on": True}),
           "graph": {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
                     "wires": [{"from": "scene", "to": "acid.2.image"},
                               {"from": "palette", "to": "output.2.image"}]}}
    before = G.read_graph(doc["graph"]).wiring().placed
    assert {e.name: e.where for e in before} == {"acid.2": ("after", "scene"),
                                                "palette": ("into", "output.2")}
    section, notes = M.to_free(doc, SPECS)
    assert notes == []
    assert {"kind": "effect", "file": "acid", "instance": 2, "after": "scene"} in section["nodes"]
    assert {"kind": "effect", "file": "palette", "into": "output.2"} in section["nodes"]
    assert ("scene", "acid.2.image") not in wires_of(section)
    assert ("palette", "output.2.image") not in wires_of(section)
    after = G.read_graph(section)
    assert M.has_frame_run(after) and not after.notes
    assert {e.name: e.where for e in after.wiring().placed} == {
        e.name: e.where for e in before}
    assert "palette" not in G.run_of(after)
    # /4 can still say it: an explicit `after` / `into` is plan 30's word
    assert M.legacy_values(section, _values_of(doc), SPECS) is not None
    assert preset.schema_of({**doc, "graph": section}) != M.FREE_SCHEMA


def _values_of(doc: dict) -> dict:
    return doc.get("values") or {}
