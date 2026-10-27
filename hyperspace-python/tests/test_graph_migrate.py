"""Plan 33 M: old presets as wires (graphmigrate). Row 394: one way, on
load — a save is always `/6`, so nothing writes the wires back as `/4`
values any more."""

from __future__ import annotations

import copy
import json
import re
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from test_plan31_wiring import make_app

from hyperspace import fx, preset
from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace.library import LibraryError

ROOT = Path(__file__).parent.parent / "hyperspace"
# plan 36 T3: the factory presets' sources (the factory files are their `/7`)
SOURCES = Path(__file__).parent / "fixtures" / "factory-sources" / "presets"
FILES = sorted([*SOURCES.glob("*.json"), *(ROOT / "library" / "fx").glob("*.json")])
# the presets written before plan 33 (a `/5` fixture — plan 33 T4's proofs —
# is the free graph's own: nothing to migrate, nothing `/4` can say; a `/6`
# one, plan 35 T3's, the wired frame's)
FIXTURES = sorted(p for p in [*SOURCES.glob("*.json"),
                              *(Path(__file__).parent / "fixtures" / "presets").glob("*.json"),
                              *(Path(__file__).parent / "fixtures" / "merge-31-32").glob("*.json")]
                  if json.loads(p.read_text()).get("schema") not in (M.FREE_SCHEMA,
                                                                       M.SIX_SCHEMA))
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
    section = out["graph"]                  # (plan 35: a wired frame, in the new ids)
    assert notes == [] and section["frame"] == "wired"
    assert {"kind": "switch"} in section["nodes"]
    assert {"kind": "switch", "instance": 2} in section["nodes"]
    w = wires_of(section)
    for sw, end in (("switch", "pattern.media"), ("switch.2", "backdrop.image")):
        assert {(f"channel.{c}", f"{sw}.in{i}") for i, c in enumerate("abcdefgh", 1)} <= w
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
def test_the_migrated_runs_are_the_old_stacks(path):
    """Every preset from before plan 33: the runs its section is given are
    the ones the old stack ran from its values (orders, targets) — the
    migration's half of what `legacy_values` checked both ways until row
    394 retired the way back."""
    doc = load(path)
    section, _ = M.to_free(doc, SPECS)
    frame, faces = runs(section)
    assert old_run(doc, 0) == frame and old_run(doc, 1) == faces


BRANCH = {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
          "wires": [{"from": "media.a", "to": "acid.2.image"},
                    {"from": "acid.2", "to": "shape.faces"}]}


def test_a_branch_saves_as_v6_and_reloads(tmp_path):
    """A branch saves `/6` (row 394: every save does), its graph the wired
    frame the load made of it, and it reloads as it saved."""
    doc = {"schema": "hyperspace.preset/2", "name": "t", "graph": BRANCH, "values": {}}
    assert G.read_graph(copy.deepcopy(BRANCH)).to_json() == BRANCH
    app = make_app(tmp_path)
    assert app.presets.load_doc(copy.deepcopy(doc)) == []
    saved = app.presets.document("t")
    wired, _ = M.migrate(doc, app.presets.graph.specs())
    assert saved["schema"] == M.WIRED_SCHEMA
    assert saved["graph"] == G.read_graph(wired["graph"]).to_json()     # (plan 36 T3: hands)
    assert saved["graph"][G.FRAME_KEY] == G.WIRED_FRAME
    assert app.presets.load_doc(copy.deepcopy(saved)) == []
    assert app.presets.document("t") == saved                 # and reloads as it saved


def test_v6_is_refused_by_the_ladder_below(tmp_path):
    """Row 385: a `/6` save (a frame only a wired one says: a channel into
    All outputs) is refused, values and all, by a plan 33/34 build's ladder
    (2 … 5) in its own words."""
    app = make_app(tmp_path)
    app.presets.load_doc({"schema": "hyperspace.preset/6", "name": "six", "values": {},
                          "graph": {"frame": "wired", "nodes": [],
                                    "wires": [{"from": "channel.a",
                                               "to": "output.all.image"}]}})
    app.presets.save_as("six")
    lib = app.lib
    assert lib.read("presets", "six")["schema"] == M.WIRED_SCHEMA
    kinds = lib._kinds
    assert preset.VERSIONS == (2, 3, 4, 5, 6, 7)
    try:
        kinds["presets"] = replace(kinds["presets"], versions=(2, 3, 4, 5))
        with pytest.raises(LibraryError, match="is not a hyperspace.preset"):
            lib.read("presets", "six")
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
    assert not after.notes and any(w.src == "frame" for w in after.all_wires())
    assert {e.name: e.where for e in after.wiring().placed} == {
        e.name: e.where for e in before}
    assert "palette" not in G.run_of(after)


def _values_of(doc: dict) -> dict:
    return doc.get("values") or {}


# ---------------------------------------------------------------- plan 35 T3: every section a wired frame
#
# Plan 35 M (rows 372, 383–385): every section this build loads lands as a
# wired frame in the owner's names — `migrate` runs plan 33's steps, then
# `renamed` (V2: old ids → new), then `wired_section` (today's frame for
# the default switches, written once into All outputs). `backdrop.history`
# and the look-back's `holds` are the capture wire now.

TESTS = Path(__file__).parent
PRESET_FIXTURES = sorted([*(TESTS / "fixtures" / "presets").glob("*.json"),
                          *(TESTS / "fixtures" / "merge-31-32").glob("*.json")])
FACTORY = sorted((ROOT / "library" / "presets").glob("*.json"))
# a name that is only ever an old id (V2): `ghost[.n]`, `readout[.n]`,
# `history`, `media.<c>` (`hands` is the geometry now, not the old layer)
_OLD_ONLY = r"ghost(\.[0-9]+)?|readout(\.[0-9]+)?|history|media\.[a-h]"


def loaded(tmp_path: Path, path: Path):
    """`path` loaded as the rig loads it — a factory preset by name, a
    fixture copied in as a user's preset — on the app's presets: (the graph
    section's spec, its free section, the load's notes)."""
    if path.parent != ROOT / "library" / "presets":
        (tmp_path / "presets").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, tmp_path / "presets" / path.name)
    app = make_app(tmp_path)
    app.lib.load("presets", path.stem)
    gs = app.presets.graph
    return gs.spec, gs.free_doc(), list(app.presets.notes)


def old_ends(spec: G.GraphSpec) -> list[str]:
    """Every wire end and D1 place of `spec` that names an old id."""
    out = []
    for w in spec.all_wires():
        for name in (w.src, w.node):
            if re.fullmatch(_OLD_ONLY, name) or (G.wire_node_kind(name, wired=True) is None
                                                 and name != G.GROUND):
                out.append(name)
        if w.port == "readout":
            out.append(w.dst)
    for e in spec.effects:
        if e.where is not None and (re.fullmatch(_OLD_ONLY, e.where[1])
                                    or re.fullmatch(r"hands(\.[0-9]+)?", e.where[1])):
            out.append(f"{e.name} {e.where[0]} {e.where[1]}")
    return out


@pytest.mark.parametrize("path", [*FACTORY, *PRESET_FIXTURES],
                         ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_every_section_loads_as_a_wired_frame(tmp_path, path):
    """Every factory preset, every fixture — and so every one of the byte
    test's 38 sources — lands `spec.wired`, in the new ids, with no graph
    note (a refused wire, an old id), no `into` or `holds` left in an entry
    and no retired value left in the registry's way."""
    spec, section, notes = loaded(tmp_path, path)
    assert spec is not None and spec.wired, path.name
    assert section.get(G.FRAME_KEY) == G.WIRED_FRAME
    assert spec.notes == (), spec.notes
    assert [n for n in notes if n.startswith("graph:") or "plan 35" in n] == []
    assert old_ends(spec) == [], path.name
    assert not any(e.get("kind") in ("history", "lookback") and "holds" in e
                   or e.get("kind") == "hands" and "into" in e
                   for e in section.get("nodes", []))


def test_old_ids_are_renamed_on_load():
    """A `/4` section in the old ids loads in the new (V2): the layer of
    hands 2, the look-back, a channel, D1's `after: hands` — and a plan 34
    `/5` fixture keeps its delay, zoomblur and composite wires as they are."""
    doc = {"schema": "hyperspace.preset/4", "name": "renamed",
           "values": {"fx.palette.on": True, "fx.acid.2.on": True},
           "graph": {"nodes": [{"kind": "hands", "into": "scene"},
                               {"kind": "hands", "instance": 2},
                               {"kind": "history", "holds": "scene+hands"},
                               {"kind": "effect", "file": "acid", "instance": 2},
                               {"kind": "effect", "file": "palette", "after": "hands"}],
                     "wires": [{"from": "hands.2", "to": "output.2.hands"},
                               {"from": "history", "to": "acid.2.image"},
                               {"from": "acid.2", "to": "output.1.image"},
                               {"from": "media.c", "to": "output.2.image"}]}}
    out, notes = M.migrate(doc, SPECS)
    section = out["graph"]
    assert notes == [] and section[G.FRAME_KEY] == G.WIRED_FRAME
    got = wires_of(section)
    assert {("hands.2.layer", "output.2.hands"), ("lookback", "acid.2.image"),
            ("acid.2", "output.1.image"), ("channel.c", "output.2.image")} <= got
    assert {"kind": "effect", "file": "palette", "after": "hands.layer"} in section["nodes"]
    spec = G.read_graph(section, placements=True)     # (plan 36 T3: `seven` writes it a wire)
    assert spec.wired and spec.notes == () and old_ends(spec) == []
    # a plan 34 `/5` fixture: its own wires, unchanged
    trails = load(TESTS / "fixtures" / "presets" / "delay-trails.json")
    own = {(w["from"], w["to"]) for w in trails["graph"]["wires"]
           if not {w["from"], w["to"].rpartition(".")[0]} & {"frame", "fx"}}
    assert any("delay" in a or "delay" in b for a, b in own)
    assert any("zoomblur" in a or "zoomblur" in b for a, b in own)
    assert any("composite" in a or "composite" in b for a, b in own)
    out, notes = M.migrate(trails, SPECS)
    assert notes == [] and own <= wires_of(out["graph"])
    assert not G.read_graph(out["graph"]).notes


def test_a_plan_33_run_becomes_wires_to_all_outputs():
    doc = {"values": {"fx.acid.on": True},
           "graph": {"nodes": [], "wires": [{"from": "frame", "to": "acid.image"},
                                            {"from": "acid", "to": "fx.image"}]}}
    out, _ = M.migrate(doc, SPECS)
    got = wires_of(out["graph"])
    assert {("lookback", "acid.image"), ("acid", "output.all.image")} <= got
    assert not any(x in ("frame", "fx") for a, b in got for x in (a, b.rpartition(".")[0]))


# plan 36 T2: the hidden edges' wires a migrated frame ends with (`drawn_edges`)
EDGES = [("pattern", "shape.faces"), ("scene.cover", "lookback.cover"),
         ("hands", "hands.layer.hands")]


@pytest.mark.parametrize(("values", "nodes", "pairs"), [
    ({"backdrop.channel": 3, "backdrop.history": True}, [], [
        ("shape", "scene.geometry"), ("scene", "backdrop.scene"), ("backdrop", "lookback.image"),
        ("lookback", "output.all.image"), ("hands.layer", "output.all.hands"),
        ("hands.layer", "output.all.guide"), ("backdrop", "lookback.capture"), *EDGES]),
    ({}, [{"kind": "history", "holds": "scene+hands"}], [
        ("shape", "scene.geometry"), ("scene", "lookback.image"),
        ("lookback", "output.all.image"), ("hands.layer", "output.all.hands"),
        ("hands.layer", "output.all.guide"), ("scene", "composite.under"),
        ("hands.layer", "composite.over"), ("composite", "lookback.capture"), *EDGES]),
    ({"backdrop.channel": 3, "backdrop.history": True},
     [{"kind": "history", "holds": "scene+hands"}], [
        ("shape", "scene.geometry"), ("scene", "backdrop.scene"), ("backdrop", "lookback.image"),
        ("lookback", "output.all.image"), ("hands.layer", "output.all.hands"),
        ("hands.layer", "output.all.guide"), ("backdrop", "composite.under"),
        ("hands.layer", "composite.over"), ("composite", "lookback.capture"), *EDGES]),
], ids=["backdrop.history", "holds", "both"])
def test_backdrop_history_and_holds_become_the_capture_wire(values, nodes, pairs):
    """T2's variants, reached through `migrate`: the capture wire says what
    `backdrop.history` and `holds` said, and neither is left behind."""
    doc = {"values": dict(values), **({"graph": {"nodes": nodes}} if nodes else {})}
    out, notes = M.migrate(doc, SPECS)
    section = out["graph"]
    frame = [(w["from"], w["to"]) for w in section["wires"]
             if (w["from"], w["to"]) != ("channel.c", "backdrop.image")]
    assert notes == [] and frame == pairs
    assert "backdrop.history" not in out["values"] and "backdrop.channel" not in out["values"]
    assert not any("holds" in e for e in section["nodes"])
    assert not G.read_graph(section).notes


@pytest.mark.parametrize("how", ["route", "desk"])
def test_a_driven_backdrop_history_is_dropped_with_a_note(how):
    doc = base(**{"backdrop.history": True, "backdrop.channel": 1, "fx.acid.on": True})
    row = {"source": "lfo:0" if how == "route" else "midi:cc:1",
           "target": "backdrop.history", "op": "push" if how == "route" else "abs"}
    keep = {"source": "lfo:1", "target": "fx.acid.mix", "op": "push"}
    doc["routes" if how == "route" else "desk"] = [row, keep]
    out, notes = M.migrate(doc, SPECS)
    assert notes == [M.DRIVEN_RETIRED_NOTE.format(pid="backdrop.history")]
    assert M.DRIVEN_RETIRED_NOTE == ("{pid} is a wire now (plan 35): its route is dropped — "
                                     "pick what the look-back records on LOOKBACK")
    rows = out["routes" if how == "route" else "desk"]
    assert [r["target"] for r in rows] == ["fx.acid.mix"]
    assert ("backdrop", "lookback.capture") in wires_of(out["graph"])


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_no_library_preset_drives_backdrop_history(path):
    """Row 381: no library preset drives `backdrop.history` (a route on it
    is dropped with a note), so retiring it costs no preset a look."""
    assert "backdrop.history" in M.RETIRED
    assert "backdrop.history" not in M.targets(load(path))
    out, notes = M.migrate(load(path), SPECS)
    assert notes == [] and "backdrop.history" not in out["values"]
