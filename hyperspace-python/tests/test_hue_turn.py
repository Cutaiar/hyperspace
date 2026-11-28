"""Hue cycle is retired. Its bands were a field it hid; they are Line,
Rings, Scale and Combine now, wired into Hue turn's Turn at a depth of 360,
and every saved Hue cycle is rewritten so on load (`graphmigrate.hue_turns`).

Held here:

- the picture: Hue cycle's own shader (kept as a fixture, the oracle) against
  the migrated patch, through the renderer, over the saved looks' settings and
  a sweep of every knob, at three times — equal to the GPU's rounding;
- the migration: names, values, rows (a push on Spread halved, a set's norm
  moved, an abs desk row kept and said, a row on Rings left out and said),
  slots, layout and groups; a document naming no Hue cycle untouched;
- every saved file in the corpus loads with no Hue cycle left and no note but
  the migration's."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))

from hyperspace import graph as G
from hyperspace import graphmigrate
from hyperspace.fx import FX_DIR, FxState

moderngl = pytest.importorskip("moderngl")

RETIRED = FX_DIR / "retired" / "huecycle.glsl"
CORPUS = Path(__file__).parent / "corpus" / "loadable"


@pytest.fixture(scope="module")
def ctx():
    c = moderngl.create_context(standalone=True)
    yield c
    c.release()


@pytest.fixture(scope="module")
def old_dir(tmp_path_factory):
    """The effects folder as it was: today's files and Hue cycle's."""
    d = tmp_path_factory.mktemp("fx-with-huecycle")
    for f in FX_DIR.glob("*.glsl"):
        shutil.copy(f, d / f.name)
    shutil.copy(RETIRED, d / "huecycle.glsl")
    return d


def _section(wires, nodes=()):
    return {"frame": "wired", "nodes": list(nodes),
            "wires": [{"from": "shape", "to": "scene.geometry"},
                      {"from": "pattern", "to": "shape.faces"}, *wires]}


def _frames(ctx, section, values, state=None):
    from test_field_wire import _views
    from test_graph_faces import _faces, _px

    from hyperspace.render import Renderer
    r = Renderer(ctx)
    if state is not None:
        r.fx.state = state
    r.ghost.state.on = False
    spec = G.read_graph(section, effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    counts: dict[str, int] = {}
    for e in section["nodes"]:
        if e.get("kind") == "effect":
            counts[e["file"]] = max(counts.get(e["file"], 1), e.get("instance", 1))
    r.fx.state.set_instances({f: n for f, n in counts.items() if n > 1})
    r.wiring = spec.wiring()
    for pid, v in values.items():
        _, rest = pid.split(".", 1)
        name, _, key = rest.rpartition(".")
        r.fx.state.values[name][key] = v
    vs = _views(ctx, 1)
    out = []
    for k in range(3):
        r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0 + k * 0.37)
        out.append(_px(vs[0].target).astype(int))
    return out


LOOKS = [
    {"paint": 0.7, "spread": 0.8, "rings": 0.5, "sat": 1.0, "speed": 0.25},   # the corpus's
    {"paint": 0.5, "spread": 0.8, "rings": 0.5, "sat": 1.0, "speed": 0.25},   # party-trip
    {"paint": 0.7, "spread": 1.2, "rings": 0.5, "sat": 1.0, "speed": 0.25},   # party-acid
    {"paint": 0.0, "spread": 0.0, "rings": 0.0, "sat": 1.0, "speed": 0.1},
    {"paint": 1.0, "spread": 4.0, "rings": 1.0, "sat": 2.0, "speed": 1.0},
    {"paint": 0.3, "spread": 2.5, "rings": 0.2, "sat": 0.0, "speed": 0.6},
    {"paint": 0.9, "spread": 0.1, "rings": 0.8, "sat": 1.6, "speed": 0.05},
]


@pytest.mark.parametrize("look", LOOKS, ids=lambda v: "-".join(f"{x:g}" for x in v.values()))
def test_the_patch_draws_hue_cycle(ctx, old_dir, look):
    values = {**{f"fx.huecycle.{k}": v for k, v in look.items()}, "fx.huecycle.on": True}
    section = _section([{"from": "scene", "to": "huecycle.image"},
                        {"from": "huecycle", "to": "output.1.image"}],
                       [{"kind": "effect", "file": "huecycle"}])
    file = _frames(ctx, section, values, FxState(old_dir))
    doc, notes = graphmigrate.hue_turns({"graph": section, "values": values})
    assert notes and "huecycle" not in json.dumps(doc)
    patch = _frames(ctx, doc["graph"], doc["values"])
    assert file[0][..., :3].max() > 30                       # a picture, not black
    for a, b in zip(file, patch, strict=True):
        d = np.abs(a - b).max(axis=2)
        assert d.max() <= 2 and (d > 0).mean() < 0.01, (int(d.max()), float((d > 0).mean()))


# ---------------------------------------------------------------- the migration

def _doc(**rest):
    section = _section([{"from": "scene", "to": "huecycle.image"},
                        {"from": "huecycle", "to": "output.all.image"}],
                       [{"kind": "effect", "file": "huecycle"}])
    return {"schema": "hyperspace.loadable/12", "name": "t", "graph": section, **rest}


def test_a_document_naming_no_hue_cycle_is_itself():
    doc = {"graph": _section([{"from": "scene", "to": "output.all.image"}]), "values": {}}
    assert graphmigrate.hue_turns(doc) == (doc, [])
    assert graphmigrate.hue_turns(doc)[0] is doc


def test_rows_values_macros_layout_and_groups_follow():
    doc = _doc(
        values={"fx.huecycle.on": True, "fx.huecycle.paint": 0.4, "fx.huecycle.spread": 2.0,
                "fx.huecycle.rings": 0.25, "fx.huecycle.speed": 0.5},
        routes=[{"source": "lane:0", "target": "fx.huecycle.spread", "op": "push", "value": 0.4},
                {"source": "lane:1", "target": "fx.huecycle.paint", "op": "push", "value": 0.3},
                {"source": "lane:2", "target": "fx.huecycle.rings", "op": "push", "value": 0.3}],
        desk=[{"source": "cc:*:23", "target": "fx.huecycle.spread", "op": "abs"},
              {"source": "cc:*:24", "target": "fx.huecycle.spread", "op": "set", "value": 0.5}],
        macros={"macro.1": {"label": "m", "subs": [
            {"base": "fx.huecycle.spread", "from": 0.0, "to": 1.0},
            {"base": "fx.huecycle.paint", "from": 0.2, "to": 0.8}]}},
        layout={"render:huecycle": [10, 20]},
        groups=[{"id": "group.1", "name": "g", "nodes": ["render:huecycle"]}])
    got, notes = graphmigrate.hue_turns(doc)
    assert "huecycle" not in json.dumps(got)
    v = got["values"]
    assert v["fx.hueturn.paint"] == 0.4 and v["fx.hueturn.speed"] == 0.5 and v["fx.hueturn.on"]
    assert "fx.hueturn.spread" not in v and "fx.hueturn.rings" not in v
    assert v["fx.scale.mul"] == 0.75 and v["fx.scale.2.mul"] == 0.25      # 1 − Rings, Rings
    assert v["fx.scale.3.mul"] == 2.0                                       # Spread
    assert v["fx.line.angle"] == pytest.approx(np.pi / 4) and v["fx.rings.scale"] == 2.0
    routes = {r["source"]: r for r in got["routes"]}
    assert routes["lane:0"]["target"] == "fx.scale.3.mul" and routes["lane:0"]["value"] == 0.2
    assert routes["lane:1"]["target"] == "fx.hueturn.paint" and routes["lane:1"]["value"] == 0.3
    assert "lane:2" not in routes                                         # Rings: left out
    desk = {r["source"]: r for r in got["desk"]}
    assert desk["cc:*:23"]["target"] == "fx.scale.3.mul"                  # kept, said
    assert desk["cc:*:24"]["value"] == 0.75        # Spread 2 (norm 0.5) is × 2 (norm 0.75)
    subs = got["macros"]["macro.1"]["subs"]
    assert subs[0] == {"base": "fx.scale.3.mul", "from": 0.5, "to": 1.0}
    assert subs[1]["base"] == "fx.hueturn.paint"
    assert got["layout"] == {"render:hueturn": [10, 20]}
    assert got["groups"][0]["nodes"] == ["render:hueturn"]
    assert any("Hue turn now" in n for n in notes)
    assert any("places the bands' Scale ×" in n for n in notes)
    assert any("left out" in n for n in notes)
    turn = next(w for w in got["graph"]["wires"] if w["to"] == "hueturn.turn")
    assert turn == {"from": "scale.3", "to": "hueturn.turn", "depth": 360.0}


def test_a_second_instance_and_its_slot_are_renamed_to_free_names():
    section = _section([{"from": "scene", "to": "huecycle.2.image"},
                        {"from": "huecycle.2", "to": "output.all.image"},
                        {"from": "hands.layer", "to": "huecycle.2.slot.2.image"},
                        {"from": "huecycle.2.slot.2", "to": "output.1.image"}],
                       [{"kind": "effect", "file": "huecycle", "instance": 2, "slots": 2},
                        {"kind": "effect", "file": "hueturn"}, {"kind": "effect", "file": "line"}])
    got, _ = graphmigrate.hue_turns({"graph": section,
                                     "values": {"fx.huecycle.2.paint": 0.1}})
    pairs = {(w["from"], w["to"]) for w in got["graph"]["wires"]}
    assert {("scene", "hueturn.2.image"), ("hueturn.2.slot.2", "output.1.image"),
            ("hands.layer", "hueturn.2.slot.2.image"), ("line.2", "scale.image")} <= pairs
    assert {"kind": "effect", "file": "hueturn", "instance": 2, "slots": 2} in got["graph"]["nodes"]
    assert got["values"]["fx.hueturn.2.paint"] == 0.1
    spec = G.read_graph(got["graph"], effects=set(FxState().specs))
    assert not spec.notes, spec.notes


def test_one_named_by_its_knobs_alone_is_renamed_with_no_bands():
    doc = {"graph": _section([{"from": "scene", "to": "output.all.image"}]),
           "values": {"fx.huecycle.on": False, "fx.huecycle.paint": 0.2,
                      "fx.huecycle.spread": 1.0},
           "macros": {"macro.1": {"label": "m",
                                  "subs": [{"base": "fx.huecycle.speed", "from": 0, "to": 1}]}}}
    got, notes = graphmigrate.hue_turns(doc)
    assert got["values"] == {"fx.hueturn.on": False, "fx.hueturn.paint": 0.2}
    assert got["macros"]["macro.1"]["subs"][0]["base"] == "fx.hueturn.speed"
    assert got["graph"] == doc["graph"] and notes


def test_a_patch_fragment_is_retired_through_its_ladder():
    from hyperspace import patches
    doc = {"schema": "hyperspace.patch/3", "name": "p",
           "nodes": [{"kind": "effect", "file": "huecycle"}],
           "wires": [],
           "ports": [{"id": "in", "type": "image", "to": "huecycle.image", "was": "scene"},
                     {"id": "out", "type": "image", "from": "huecycle", "was": "output.all.image"}],
           "values": {"fx.huecycle.spread": 0.5}}
    got = patches.forward(doc)
    assert "huecycle" not in json.dumps(got)
    assert got["ports"][0]["to"] == "hueturn.image" and got["ports"][1]["from"] == "hueturn"
    assert {"from": "scale.3", "to": "hueturn.turn", "depth": 360.0} in got["wires"]
    assert patches.check(got) == []


def test_an_old_file_loads_retired_and_resaves_as_itself(tmp_path):
    """End to end (REVIEW.md: a format change opens an old file whole): a `/2`
    party-trip from an older format, through the library's own load and save."""
    from hyperspace import headless
    old = Path(__file__).parent / "fixtures" / "v4-saves" / "factory--party-trip.json"
    assert "huecycle" in old.read_text()
    raw, notes, _ = headless.resave(old, tmp_path / "a")
    assert any("Hue turn now" in n for n in notes)
    assert b"huecycle" not in raw
    doc = json.loads(raw)
    assert {"from": "scale.3", "to": "hueturn.turn", "depth": 360.0} in doc["graph"]["wires"]
    again = tmp_path / "again.json"
    again.write_bytes(raw)
    raw2, notes2, _ = headless.resave(again, tmp_path / "b")
    assert raw2 == raw and notes2 == []


@pytest.mark.parametrize("path", sorted(CORPUS.glob("*.json")) + sorted(
    (Path(__file__).parents[1] / "loadable").rglob("*.json")), ids=lambda p: p.stem)
def test_no_saved_look_names_hue_cycle(path):
    assert "huecycle" not in path.read_text(), path


# ---------------------------------------------------------------- the rename reaches keys and sections

def test_black_is_clear_follows_the_rename():
    """The section's `keys` and the `key.<node>.*` knobs name the node too."""
    doc = _doc(values={"fx.huecycle.on": True, "key.huecycle.level": 0.2})
    doc["graph"]["keys"] = ["huecycle"]
    got, _ = graphmigrate.hue_turns(doc)
    assert got["graph"]["keys"] == ["hueturn"]
    assert got["values"]["key.hueturn.level"] == 0.2 and "huecycle" not in json.dumps(got)


def test_a_field_on_spread_or_rings_lands_where_that_knob_is_now():
    doc = _doc(values={"fx.huecycle.on": True})
    doc["graph"]["nodes"].append({"kind": "effect", "file": "noise"})
    doc["graph"]["wires"] += [{"from": "noise", "to": "huecycle.spread", "depth": 0.5},
                              {"from": "noise", "to": "huecycle.rings", "depth": 0.25}]
    got, _ = graphmigrate.hue_turns(doc)
    wires = got["graph"]["wires"]
    assert {"from": "noise", "to": "scale.3.mul", "depth": 0.5} in wires
    assert {"from": "noise", "to": "scale.2.mul", "depth": 0.25} in wires       # Rings
    assert {"from": "noise", "to": "scale.mul", "depth": -0.25} in wires        # 1 − Rings
    assert not any(w["to"].endswith((".spread", ".rings")) for w in wires)
    spec = G.read_graph(got["graph"], effects=set(FxState().specs))
    assert not spec.notes, spec.notes


def test_a_spread_push_with_no_depth_is_written_halved():
    doc = _doc(values={"fx.huecycle.on": True},
               routes=[{"source": "lane:0", "target": "fx.huecycle.spread", "op": "push"}])
    got, _ = graphmigrate.hue_turns(doc)
    assert got["routes"][0] == {"source": "lane:0", "target": "fx.scale.3.mul", "op": "push",
                                "value": 0.5}


def test_a_spread_position_row_is_kept_and_said():
    """A position sets the knob's place: 0 … 4 cannot become 0 … 4 of −4 … 4
    without an offset a row does not hold — kept, said, as an abs row."""
    doc = _doc(values={"fx.huecycle.on": True},
               routes=[{"source": "lane:0", "target": "fx.huecycle.spread", "op": "position",
                        "value": 0.8}])
    got, notes = graphmigrate.hue_turns(doc)
    assert got["routes"][0]["value"] == 0.8 and got["routes"][0]["target"] == "fx.scale.3.mul"
    assert any("places the bands' Scale ×" in n for n in notes)


def test_an_old_speed_depth_is_retapered_as_hue_cycles():
    """Before the effect tapers a file measured depths linearly; the retaper
    reads the retired file's spec, so Hue cycle's Speed converts as it did."""
    from hyperspace import fx, params
    assert "huecycle" in params.fx_files(FxState())
    assert graphmigrate.RETIRED_SPECS["huecycle"] == (
        fx.retired_specs()["huecycle"].order, fx.retired_specs()["huecycle"].mix)
    doc = {"values": {"fx.huecycle.on": True},
           "routes": [{"source": "lane:0", "target": "fx.huecycle.speed", "op": "push",
                       "value": 0.25}]}
    got, moved = params.retaper_depths(doc, params.fx_files(FxState()))
    assert moved and got["routes"][0]["value"] != 0.25


def test_a_slot_inherits_its_effects_field_when_the_effect_is_unfed_and_never_through_a_loop():
    from hyperspace.outputs import Switches
    sys.path.insert(0, str(Path(__file__).parent))
    from test_graphview import views, wired_wiring

    def build(wires, nodes):
        section = _section(wires, nodes)
        spec = G.read_graph(section, effects=set(FxState().specs))
        assert not spec.notes, spec.notes
        return G.build_graph(views(Switches()), wired_wiring(spec.wiring()),
                             effects=tuple(sorted({n["file"] for n in nodes})))

    def slot(g):
        return next(n for n in g.nodes.values() if isinstance(n, G.Effect)
                    and n.name.startswith("wave.slot.2"))
    # Wave itself unfed: its slot still reads the field on Amount
    g = build([{"from": "scene", "to": "wave.slot.2.image"},
               {"from": "wave.slot.2", "to": "output.all.image"},
               {"from": "line", "to": "wave.amount", "depth": 0.5}],
              [{"kind": "effect", "file": "wave", "slots": 2}, {"kind": "effect", "file": "line"}])
    assert slot(g).depths.get("amount") == 0.5
    # the slot feeds the field: no inheritance, said
    g = build([{"from": "scene", "to": "wave.image"}, {"from": "scene", "to": "wave.slot.2.image"},
               {"from": "wave.slot.2", "to": "tofield.image"},
               {"from": "tofield", "to": "wave.amount"},
               {"from": "wave", "to": "output.all.image"},
               {"from": "wave.slot.2", "to": "output.1.image"}],
              [{"kind": "effect", "file": "wave", "slots": 2}, {"kind": "effect", "file": "tofield"}])
    assert "amount" not in slot(g).depths
    assert any("makes a loop" in v for v in g.dormant.values())
