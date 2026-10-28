"""Plan 40 T1 (P1, D5): the patch as data — `patches.py` and the library's
`patches` kind.

No GL, no imgui: a factory preset's parts are landed headless from its file
(the graph section read, the routes and preset-layer desk in a bare
`routing.Bindings`, its values as the registry's snapshot would hold them).

- `check` refuses each refusable thing in words;
- `read` classifies the spec's example (tests/fixtures/patches/acid-wash.json)
  into its rig rows and host ports;
- `lift` of warp, doublevision and fractals out of party-noita gives one
  inlet, one outlet, the three effects' values and their desk rows;
- `spawn` renames into a host that holds them, lists a desk conflict, and
  notes a macro with no free number;
- the round trip — `read(lift(spawn(p)))` is `read(p)` up to the renames and
  the origin — over the example and over every factory preset's main run;
- the library lists, hides, renames, saves and reads patches, and never
  loads one.
"""

from __future__ import annotations

import ast
import copy
import json
import shutil
from pathlib import Path

import pytest

from hyperspace import graph as G
from hyperspace import graphview, library, patches
from hyperspace.library import (
    FACTORY,
    HIDDEN,
    PATCH_SCHEMA,
    PATCHES,
    Library,
    LibraryError,
)
from hyperspace.patches import Host, read, spawn
from hyperspace.routing import Binding, Bindings

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "patches"
ACID_WASH = FIXTURES / "acid-wash.json"
PRESETS = FACTORY / "presets"


def example() -> dict:
    return json.loads(ACID_WASH.read_text())


def preset(name: str) -> dict:
    return json.loads((PRESETS / f"{name}.json").read_text())


def parts(doc: dict):
    """A preset's parts as the app holds them once it has landed: the
    section read, the table (its routes, its preset-layer desk, modifiers
    and macros), the performance values (a modifier's params among them, as
    the registry's snapshot has them) and the GRAPH layout."""
    spec = G.read_graph(doc["graph"])
    rows = [Binding.from_json(r) for r in doc.get("routes") or ()]
    desk = [Binding.from_json({**r, "layer": "preset"}) for r in doc.get("desk") or ()]
    table = Bindings([*rows, *desk])
    table.set_macros(doc.get("macros"))
    table.set_modifiers(doc.get("modifiers"))
    values = dict(doc.get("values") or {})
    for m in table.modifiers_doc():
        for k, v in m.items():
            if k not in ("id", "kind", "in"):
                values[f"{m['id']}.{k}"] = v
    return spec, table, values, dict(doc.get("layout") or {})


def host_of(p) -> Host:
    spec, table, _values, _layout = p
    return Host.of(spec, table)


def land(p, landing, *, as_saved: bool = True):
    """The Landing put into the parts, every row the patch's (what P3's
    doors do with every conflict resolved to the patch): the section re-read
    with its nodes and wires, the rows, modifiers, macros, values, layout.
    `as_saved`: and each port wired to what it `was` (P3's *wire as saved*;
    an outlet's port taken over from whatever fed it)."""
    spec, table, values, layout = p
    sec = spec.to_json()
    wires = [*sec.get("wires", []), *copy.deepcopy(list(landing.wires))]
    for port in landing.ports if as_saved else ():
        if "to" in port:
            wires.append({"from": port["was"], "to": port["to"]})
        else:
            wires = [w for w in wires if w["to"] != port["was"]]
            wires.append({"from": port["from"], "to": port["was"]})
    sec["nodes"] = [*sec.get("nodes", []), *copy.deepcopy(list(landing.nodes))]
    sec["wires"] = wires
    spec = G.read_graph(sec)
    assert not spec.notes, spec.notes
    table.bindings += [Binding.from_json(r) for r in landing.routes]
    for r in landing.desk:                      # `bind`: a control keeps one row
        b = Binding.from_json({**r, "layer": "preset"})
        table.bindings = [x for x in table.bindings if not (x.layer == "preset"
                                                            and x.overlaps(b))] + [b]
    table.set_modifiers([*table.modifiers_doc(), *landing.modifiers])
    table.set_macros({**table.macros_doc(), **landing.macros})
    values = {**values, **landing.values}
    for m in landing.modifiers:
        for k, v in m.items():
            if k not in ("id", "kind", "in"):
                values[f"{m['id']}.{k}"] = float(v)
    return spec, table, values, {**layout, **landing.layout}


def same(a: dict, b: dict) -> None:
    """Two patch documents read the same, name and note aside."""
    a, b = {**a, "name": "", "note": ""}, {**b, "name": "", "note": ""}
    ra, rb = read(a), read(b)
    for f in ("nodes", "wires", "values", "modifiers", "routes", "desk", "macros", "lfos",
              "envs", "layout", "ports", "rig_rows", "host_ports"):
        assert getattr(ra, f) == getattr(rb, f), f
    assert ra == rb


# ---------------------------------------------------------------- the leaf

def test_patches_is_a_leaf():
    """patches.py imports graph's names, routing's pure pieces and the
    modifiers' id rule — never the app, the library, a page or the renderer
    (library imports it, for `check`)."""
    tree = ast.parse(Path(patches.__file__).read_text())
    banned = {"library", "preset", "app", "render", "graphview", "undo", "control", "params",
              "midi", "apc40", "devices", "imgui"}
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[-1]] + [a.name for a in node.names]
        elif isinstance(node, ast.Import):
            names = [a.name.split(".")[-1] for a in node.names]
        assert not banned & set(names), names
        assert not any(n.startswith("ui") for n in names), names
    called = {n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not called & {"set_value", "restore", "bind", "replace_owner", "add_modifier",
                         "set_macros", "set_desk", "set_routes", "set_modifiers", "land",
                         "write"}


def test_the_rig_nodes_are_graphviews_not_removable():
    """`RIG_NODES` restates the render nodes the GRAPH page refuses to delete
    as the rig's (`graphview.spec_name`'s `NOT_REMOVABLE`): the two lists
    agree, and the patch reads a name's kind as the canvas does."""
    assert set(patches.RIG_NODES) == {graphview.CAMERA, "cloud"}
    for name in ("camera", "cloud", "cloud.2"):
        got, why = graphview.spec_name(f"render:{name}")
        assert got is None and why == graphview.NOT_REMOVABLE.format(
            label=graphview.label_of(name)), (name, why)
        assert patches.held_words(name) == patches.RIG_WORDS.format(name=name)
    for name in ("acid", "acid.2", "composite.3", "hands.2", "hands.2.layer", "segment.fg",
                 "output.all", "output.2", "channel.a", "scene", "lookback.2", "camera",
                 "cloud.1"):
        want = graphview.kind_of(name)
        want = "output" if want == G.ALL_OUTPUTS else want
        assert patches._kind(name) == want, name


def test_the_slug_is_the_librarys():
    for name in ("acid wash", "Noita Core!", "  ", "über-trip 2"):
        assert patches.slug(name) == library.slug(name)


# ---------------------------------------------------------------- check

def test_the_example_is_a_patch():
    assert patches.check(example()) == []


@pytest.mark.parametrize("edit, said", [
    (lambda d: d["nodes"].append({"kind": "scene"}), "scene is the frame's; left out"),
    (lambda d: d["nodes"].append({"kind": "hands"}), "hands is the frame's; left out"),
    (lambda d: d["nodes"].append({"kind": "lookback", "instance": 2}),
     "lookback.2 is the frame's; left out"),
    (lambda d: d["nodes"].append({"kind": "camera"}), "camera is the rig's; left out"),
    (lambda d: d["nodes"].append({"kind": "cloud"}), "cloud is the rig's; left out"),
    (lambda d: d["nodes"].append({"kind": "output"}),
     "output is the rig's window; left out — a patch's picture leaves by a port"),
    (lambda d: d["nodes"].append({"kind": "channel"}),
     ("channel is a media channel, this Mac's files; left out — a patch reads one through "
      "a port")),
    (lambda d: d["wires"].append({"from": "delay", "to": "output.2.image"}),
     ("wire delay → output.2.image: output.2 is the rig's window; left out — a patch's "
      "picture leaves by a port")),
    (lambda d: d["wires"].append({"from": "channel.a", "to": "wobble.aux"}),
     ("wire channel.a → wobble.aux: channel.a is a media channel, this Mac's files; left "
      "out — a patch reads one through a port")),
    (lambda d: d["wires"].append({"from": "cloud.1", "to": "acid.aux"}),
     "wire cloud.1 → acid.aux: cloud.1 is the rig's; left out"),
    (lambda d: d["ports"][0].update(type="colour"),
     "port in: type 'colour' is not one of image, mask, geometry, value"),
    (lambda d: d["wires"].append({"from": "acid", "to": "zoomblur.image"}),
     "wire acid → zoomblur.image crosses the edge: a port says it"),
    (lambda d: d["values"].update({"view.bright": 0.8}),
     "view.bright is the host's: a patch drives a host param, never sets it (D5)"),
    (lambda d: d.update(envs=[3]),
     "env.3 is a sequencer lane's envelope; left out (a patch's envelope spawns as 6 or more)"),
    (lambda d: d.update(schema="hyperspace.preset/7"),
     "schema 'hyperspace.preset/7' is not hyperspace.patch/1"),
    (lambda d: d["nodes"].append({"kind": "copy", "of": "zoomblur"}),
     "copy draws zoomblur again: take zoomblur with it; left out"),
])
def test_check_refuses_each_refusable_thing_in_words(edit, said):
    doc = example()
    edit(doc)
    assert said in patches.check(doc), patches.check(doc)


def test_a_wire_across_the_edge_is_refused_even_where_a_port_says_it():
    """D2, plan 36: a crossing is a port, an open pin — a wire in the file
    would be landed by a spawn, an attachment by its saved name."""
    doc = example()
    doc["wires"] += [{"from": "scene", "to": "acid.image"},
                     {"from": "delay", "to": "output.all.image"}]
    assert patches.check(doc) == [
        "wire scene → acid.image crosses the edge: a port says it",
        ("wire delay → output.all.image: output.all is the rig's window; left out — a "
         "patch's picture leaves by a port")]


def test_spawn_lands_only_the_patchs_own_wires():
    """Whatever the file says (a caller that skipped `check`), `Landing.wires`
    holds no wire with an end outside the spawned members."""
    doc = example()
    doc["wires"] += [{"from": "scene", "to": "acid.image"},
                     {"from": "delay", "to": "output.all.image"}]
    landing = spawn(doc, Host(names=frozenset({"acid", "scene"})))
    mine = {G.instance_name(e["file"], e.get("instance", 1)) if e["kind"] == "effect"
            else patches.entry_name(e) for e in landing.nodes}
    assert mine == {"acid.2", "wobble", "delay"}
    assert landing.wires == ({"from": "acid.2", "to": "wobble.image"},
                             {"from": "wobble", "to": "delay.image"})
    for w in landing.wires:
        assert patches._node_of(w["from"]) in mine and w["to"].rpartition(".")[0] in mine


def test_spawn_lands_only_the_members_values():
    """D5 for any caller: a host param's value in the file does not land."""
    doc = example()
    doc["values"]["view.bright"] = 0.8
    landing = spawn(doc, Host())
    assert "view.bright" not in landing.values and "fx.acid.speed" in landing.values


# ---------------------------------------------------------------- read

def test_read_classifies_the_example():
    """The spec's example: the lane route and K1's desk row are rig rows
    (verbatim); the two picture ports are its host ports; the modifier's
    route is the patch's own, inside."""
    doc = example()
    p = read(doc)
    assert [r["source"] for r in p.rig_rows] == ["lane:0", "cc:0:48"]
    assert p.rig_rows == (doc["routes"][1], doc["desk"][0])
    assert [h["id"] for h in p.host_ports] == ["in", "out"]
    assert p.host_ports == tuple(sorted(doc["ports"], key=lambda x: x["id"]))
    assert p.members.render == ("acid", "delay", "wobble")
    assert p.members.mods == (1,)


def test_read_derives_the_value_ports():
    """A route from a patch lane onto a host param, a route from a host lane
    onto a member, a member macro's base on a host param and a modifier
    input from a host lane are host ports, derived — not in `ports`."""
    doc = example()
    doc["lfos"] = [1]
    doc["routes"] += [{"source": "lfo:0", "target": "view.bright", "op": "push"},
                      {"source": "lfo:3", "target": "fx.wobble.freq", "op": "push"}]
    doc["macros"] = {"macro.2": {"subs": [{"base": "view.speed", "from": 0, "to": 1}]}}
    doc["modifiers"].append({"id": "mod.2", "kind": "combine", "in": ["mod:1", "env:6"]})
    assert patches.check(doc) == []
    p = read(doc)
    values = [h for h in p.host_ports if h["type"] == G.VALUE]
    assert [(h.get("from"), h.get("to"), h["was"]) for h in values] == [
        ("lfo:0", None, "view.bright"), (None, "fx.wobble.freq", "lfo:3"),
        ("macro.2", None, "view.speed"), (None, "mod.2.in2", "env:6")]
    assert [r["source"] for r in p.rig_rows] == ["lane:0", "cc:0:48"]


# ---------------------------------------------------------------- lift

NOITA_CORE = ["render:warp", "render:doublevision", "render:fractals"]


def test_lift_of_noitas_core():
    """warp, doublevision and fractals out of party-noita: one inlet from
    the scene, one outlet into tripcolour, the three effects' values and
    no others, the desk rows and hand routes on their params verbatim."""
    noita = preset("party-noita")
    doc, refused = patches.lift(*parts(noita), NOITA_CORE)
    assert refused == []
    assert patches.check({**doc, "name": "noita core"}) == []
    assert doc["schema"] == PATCH_SCHEMA and doc["name"] == doc["note"] == ""
    assert doc["ports"] == [
        {"id": "in", "type": "image", "to": "warp.image", "was": "scene"},
        {"id": "out", "type": "image", "from": "fractals", "was": "tripcolour.image"}]
    assert doc["wires"] == [{"from": "warp", "to": "doublevision.image"},
                            {"from": "doublevision", "to": "fractals.image"}]
    mine = ("fx.warp.", "fx.doublevision.", "fx.fractals.")
    assert doc["values"] == {k: v for k, v in noita["values"].items() if k.startswith(mine)}
    assert doc["desk"] == [r for r in noita["desk"] if r["target"].startswith(mine)]
    assert len(doc["desk"]) == 6
    assert doc["routes"] == [r for r in noita["routes"] if r["target"].startswith(mine)]
    assert [n["file"] for n in doc["nodes"]] == ["doublevision", "fractals", "warp"]
    assert doc["layout"] == {} and doc["lfos"] == doc["envs"] == []
    p = read(doc)
    assert len(p.rig_rows) == len(doc["desk"]) + len(doc["routes"])


def test_a_lift_that_names_scene_refuses_it_and_keeps_the_rest():
    noita = preset("party-noita")
    doc, refused = patches.lift(*parts(noita),
                                ["render:scene", "render:warp", "render:output.all",
                                 "render:camera", "seq", "env.2", "device:apc40"])
    assert refused == ["scene is the frame's; left out",
                       ("output.all is the rig's window; left out — a patch's picture "
                        "leaves by a port"),
                       "camera is the rig's; left out",
                       "the sequencer is the rig's; left out",
                       ("env.2 is a sequencer lane's envelope; left out (a patch's envelope "
                        "spawns as 6 or more)"),
                       "device:apc40 is the rig's; left out"]
    assert [n["file"] for n in doc["nodes"]] == ["warp"]
    assert {p["was"] for p in doc["ports"]} == {"scene", "doublevision.image"}


def test_lift_renames_to_the_lowest_ids_and_rebases_the_layout():
    """acid.2 and acid.4 → acid, acid.2; mod.3 → mod.1; lfo.5 → lfo.1;
    env.7 → env.6; macro.2 stays; every reference rewritten; the layout's
    top-left at (0, 0)."""
    sec = {"frame": "wired", "nodes": [{"kind": "hands", "laid": "over"},
                                       {"kind": "effect", "file": "acid", "instance": 2},
                                       {"kind": "effect", "file": "acid", "instance": 4}],
           "wires": [{"from": "scene", "to": "acid.2.image"},
                     {"from": "acid.2", "to": "acid.4.image"},
                     {"from": "acid.4", "to": "output.all.image"},
                     {"from": "shape", "to": "scene.geometry"}]}
    doc = {"graph": sec,
           "values": {"fx.acid.2.bend": 0.1, "fx.acid.4.bend": 0.2, "fx.acid.bend": 9.0,
                      "lfo.5.rate": 2.0, "env.7.attack": 0.3, "macro.2": 0.5,
                      "view.bright": 1.0},
           "routes": [{"source": "mod:3", "target": "fx.acid.4.twist", "op": "push"},
                      {"source": "lfo:4", "target": "fx.acid.2.twist", "op": "push"},
                      {"source": "env:6", "target": "view.bright", "op": "push"},
                      {"source": "hand:left.y", "target": "fx.acid.4.bend", "op": "push"}],
           "desk": [{"source": "cc:0:48", "target": "macro.2", "op": "abs"}],
           "modifiers": [{"id": "mod.3", "kind": "smooth", "in": ["lfo:4"]}],
           "macros": {"macro.2": {"label": "wash", "subs": [
               {"base": "fx.acid.2.reach", "from": 1, "to": 9},
               {"depth": {"source": "lfo:4", "target": "fx.acid.2.twist"}, "from": 0,
                "to": 1}]}},
           "layout": {"render:acid.2": [300, 120], "render:acid.4": [560, 140],
                      "mod.3": [300, 400], "lfo.5": [100, 400], "macro.2": [120, 90]}}
    got, refused = patches.lift(*parts(doc), ["render:acid.4", "render:acid.2", "mod.3",
                                              "lfo.5", "env.7", "macro.2"])
    assert refused == []
    assert got["nodes"] == [{"kind": "effect", "file": "acid"},
                            {"kind": "effect", "file": "acid", "instance": 2}]
    assert got["wires"] == [{"from": "acid", "to": "acid.2.image"}]
    assert got["values"] == {"env.6.attack": 0.3, "fx.acid.2.bend": 0.2, "fx.acid.bend": 0.1,
                             "lfo.1.rate": 2.0, "macro.2": 0.5}
    assert got["routes"] == [
        {"source": "mod:1", "target": "fx.acid.2.twist", "op": "push"},
        {"source": "lfo:0", "target": "fx.acid.twist", "op": "push"},
        {"source": "env:5", "target": "view.bright", "op": "push"},
        {"source": "hand:left.y", "target": "fx.acid.2.bend", "op": "push"}]
    assert got["desk"] == [{"source": "cc:0:48", "target": "macro.2", "op": "abs"}]
    assert got["modifiers"][0]["id"] == "mod.1" and got["modifiers"][0]["in"] == ["lfo:0"]
    assert got["macros"] == {"macro.2": {"label": "wash", "subs": [
        {"base": "fx.acid.reach", "from": 1.0, "to": 9.0},
        {"depth": {"source": "lfo:0", "target": "fx.acid.twist"}, "from": 0.0, "to": 1.0}]}}
    assert got["lfos"] == [1] and got["envs"] == [6]
    assert got["layout"] == {"render:acid": [200, 30], "render:acid.2": [460, 50],
                             "mod.1": [200, 310], "lfo.1": [0, 310], "macro.2": [20, 0]}
    assert patches.check({**got, "name": "x"}) == []


# ---------------------------------------------------------------- spawn

def test_spawn_into_a_host_that_holds_warp_renames_every_reference():
    noita = preset("party-noita")
    doc, _ = patches.lift(*parts(noita), NOITA_CORE)
    doc["name"] = "noita core"
    landing = spawn(doc, host_of(parts(noita)), at=(400, 80))
    assert landing.renames == {"warp": "warp.2", "doublevision": "doublevision.2",
                               "fractals": "fractals.2"}
    assert sorted(G.instance_name(n["file"], n.get("instance", 1)) for n in landing.nodes) == [
        "doublevision.2", "fractals.2", "warp.2"]
    assert landing.wires == ({"from": "doublevision.2", "to": "fractals.2.image"},
                             {"from": "warp.2", "to": "doublevision.2.image"})
    assert set(landing.values) == {k.replace("fx.warp.", "fx.warp.2.")
                                   .replace("fx.fractals.", "fx.fractals.2.")
                                   .replace("fx.doublevision.", "fx.doublevision.2.")
                                   for k in doc["values"]}
    assert {r["target"] for r in (*landing.routes, *landing.desk)} <= {
        k for k in landing.values}
    assert landing.ports == (
        {"id": "in", "type": "image", "to": "warp.2.image", "was": "scene"},
        {"id": "out", "type": "image", "from": "fractals.2", "was": "tripcolour.image"})
    assert landing.group == {"name": "noita core", "patch": "noita-core", "open": False,
                             "nodes": ["render:doublevision.2", "render:fractals.2",
                                       "render:warp.2"]}
    assert "id" not in landing.group                    # T2 numbers the groups
    # its desk knobs are noita's own: six desk conflicts; the right hand's
    # axes already drive noita's params: one-axis-one-param conflicts
    kinds = [c.kind for c in landing.conflicts]
    assert kinds.count("desk") == 6
    c = next(c for c in landing.conflicts if c.kind == "desk")
    assert (c.control_or_source, c.host_target, c.patch_target) == (
        "cc:*:17", "fx.warp.amount", "fx.warp.2.amount")
    assert {c.control_or_source for c in landing.conflicts if c.kind == "source"} == {
        "hand:right.y", "hand:right.z", "hand:right.roll", "hand:left.y"}
    assert set(landing.wants) == {"cc", "hand"}


def test_a_spawn_with_k1_already_mapped_lists_one_conflict_and_lands_nothing():
    """acid-wash into party-noita, where K1 (cc:0:48) is view.bright: one
    conflict — the lane route is no one-owner source — and the host's parts
    are as they were (spawn is pure)."""
    p = parts(preset("party-noita"))
    before = [b.to_json() for b in p[1].bindings], p[1].macros_doc(), p[1].modifiers_doc()
    landing = spawn(example(), host_of(p))
    assert landing.conflicts == (patches.Conflict(
        "desk", "cc:0:48", "view.bright", "fx.acid.speed",
        {"source": "cc:0:48", "target": "fx.acid.speed", "op": "abs", "feedback": "ring"},
        {"source": "cc:0:48", "target": "view.bright", "op": "abs", "feedback": "ring"}),)
    assert ([b.to_json() for b in p[1].bindings], p[1].macros_doc(),
            p[1].modifiers_doc()) == before
    assert landing.renames == {}                    # noita has no acid, wobble, delay, mod
    assert landing.wants == {
        "lane": ({"source": "lane:0", "target": "fx.acid.speed", "op": "push", "value": 0.1,
                  "scale": "master.gain"},),
        "cc": ({"source": "cc:0:48", "target": "fx.acid.speed", "op": "abs",
                "feedback": "ring"},),
        "hand": ({"source": "hand:right.y", "modifier": "mod.1"},)}
    assert landing.notes == ()


def test_spawn_renames_the_modulation_by_the_hosts_rules():
    """mod.1 → one past the host's highest modifier; lfo.1 → the bank's next
    id; an envelope 6 or more; a macro the host uses moves to the lowest
    free one; every reference follows."""
    doc = example()
    doc["lfos"], doc["envs"] = [1], [6]
    doc["routes"] += [{"source": "lfo:0", "target": "fx.acid.twist", "op": "push"},
                      {"source": "env:5", "target": "fx.wobble.freq", "op": "push"}]
    doc["macros"] = {"macro.2": {"subs": [{"base": "fx.acid.reach", "from": 0, "to": 1}]}}
    doc["desk"].append({"source": "cc:0:49", "target": "macro.2", "op": "abs"})
    doc["layout"]["lfo.1"] = [0, 300]
    assert patches.check(doc) == []
    host = Host(names=frozenset({"acid", "acid.2", "scene"}), modifiers=("mod.2", "mod.6"),
                next_voice={"lfo": 6, "env": 3}, room={"lfo": 4, "env": 9},
                macros=frozenset({"macro.1", "macro.2"}))
    landing = spawn(doc, host, at=(100, 50))
    assert landing.renames == {"acid": "acid.3", "mod.1": "mod.7", "lfo.1": "lfo.6",
                               "macro.2": "macro.3"}
    assert landing.lfos == (6,) and landing.envs == (6,)
    assert {r["source"] for r in landing.routes} == {"mod:7", "lane:0", "lfo:5", "env:5"}
    assert {"fx.acid.3.twist", "fx.acid.3.speed"} <= {r["target"] for r in landing.routes}
    assert landing.macros == {"macro.3": {"subs": [
        {"base": "fx.acid.3.reach", "from": 0, "to": 1}]}}
    assert {"source": "cc:0:49", "target": "macro.3", "op": "abs"} in landing.desk
    assert landing.modifiers[0]["id"] == "mod.7"
    assert landing.layout == {"render:acid.3": [100, 50], "render:wobble": [360, 50],
                              "render:delay": [620, 50], "mod.7": [100, 250],
                              "lfo.6": [100, 350]}
    assert landing.group["nodes"] == ["render:acid.3", "render:delay", "render:wobble",
                                      "mod.7", "lfo.6", "env.6", "macro.3"]
    assert landing.ports[0] == {"id": "in", "type": "image", "to": "acid.3.image",
                                "was": "scene"}


def test_a_macro_with_no_free_number_is_a_note_and_the_rest_spawns():
    doc = example()
    doc["macros"] = {"macro.2": {"label": "wash",
                                 "subs": [{"base": "fx.acid.reach", "from": 0, "to": 1}]}}
    doc["values"]["macro.2"] = 0.25
    doc["desk"].append({"source": "cc:0:49", "target": "macro.2", "op": "abs"})
    host = Host(macros=frozenset(f"macro.{n}" for n in range(1, 9)))
    landing = spawn(doc, host)
    assert landing.notes == ("macro.2: no free macro — its subscribers not spawned",)
    assert landing.macros == {} and "macro.2" not in landing.values
    assert [r["target"] for r in landing.desk] == ["fx.acid.speed"]
    assert "macro.2" not in landing.group["nodes"]
    assert [entry["kind"] for entry in landing.nodes] == ["effect", "delay", "effect"]
    assert len(landing.routes) == 2 and landing.modifiers


def _with_an_lfo() -> dict:
    """The example with an LFO read everywhere a lane can be: a route, the
    second input of a modifier, a macro's depth subscriber, a base on its rate."""
    doc = example()
    doc["lfos"] = [1]
    doc["values"]["lfo.1.rate"] = 2.0
    doc["routes"].append({"source": "lfo:0", "target": "fx.acid.twist", "op": "push"})
    doc["modifiers"].append({"id": "mod.2", "kind": "combine", "in": ["mod:1", "lfo:0"]})
    doc["macros"] = {"macro.3": {"subs": [
        {"depth": {"source": "lfo:0", "target": "fx.acid.twist"}, "from": 0, "to": 1},
        {"base": "lfo.1.rate", "from": 0, "to": 4},
        {"base": "fx.acid.reach", "from": 0, "to": 1}]}}
    assert patches.check(doc) == []
    return doc


def _no_lane(landing, lane: str = "lfo:0") -> None:
    assert all(r["source"] != lane for r in (*landing.routes, *landing.desk))
    assert all(lane not in (m.get("in") or ()) for m in landing.modifiers)
    for mac in landing.macros.values():
        for s in mac["subs"]:
            assert (s.get("depth") or {}).get("source") != lane, s
            assert not str(s.get("base", "")).startswith("lfo.1."), s


def test_a_full_bank_is_a_note_and_its_lane_reads_nothing():
    """The LFO does not spawn: its route, its depth subscriber and its base
    stay out, the modifier's input on its lane is left empty and said —
    never `lfo:0`, which would read the host's LFO 1."""
    landing = spawn(_with_an_lfo(), Host(next_voice={"lfo": 17}, room={"lfo": 0}))
    assert landing.notes == (
        "lfo.1: the lfo bank is full — not spawned, nor its routes",
        "mod.2: its input 2 read lfo.1, which did not spawn — left empty")
    assert landing.lfos == () and "lfo.1.rate" not in landing.values
    _no_lane(landing)
    assert landing.modifiers[1]["in"] == ["mod:1", None]
    assert landing.macros == {"macro.3": {"subs": [
        {"base": "fx.acid.reach", "from": 0, "to": 1}]}}
    assert "lfo.1" not in landing.group["nodes"]


def test_used_up_voice_ids_are_a_note():
    """A bank whose next id is past `modbank.MAX_ID` has no room, however
    few voices it holds (`Bank.refusal`)."""
    landing = spawn(_with_an_lfo(), Host(next_voice={"lfo": 65}, room={"lfo": 3}))
    assert landing.notes[0] == ("lfo.1: lfo ids are used up (64 is the highest) — not "
                                "spawned, nor its routes")
    _no_lane(landing)

    class Full:
        MAX = 16

        def next_id(self):
            return 65

        def __len__(self):
            return 2
    host = Host.of(None, Bindings(), banks={"lfo": Full()})
    assert host.room["lfo"] == 0 and host.next_voice["lfo"] == 65


def test_host_of_without_banks_starts_past_every_voice_the_table_names():
    """No bank handed in: one past the highest voice id the table's lanes
    name, and past the default membership (LFOs 1–4, lane envelopes 1–5)."""
    host = Host.of(*parts(preset("party-noita"))[:2])
    assert host.next_voice == {"lfo": 5, "env": 6}
    table = Bindings([Binding("lfo:7", "view.bright", "push")])
    table.set_modifiers([{"id": "mod.1", "kind": "smooth", "in": ["env:9"]}])
    host = Host.of(None, table)
    assert host.next_voice == {"lfo": 9, "env": 11}
    landing = spawn(_with_an_lfo(), host)
    assert landing.renames["lfo.1"] == "lfo.9" and landing.lfos == (9,)


def test_a_patch_twice_collides_with_itself_row_by_row():
    """The second spawn of one patch: its K1 row and its hand row meet the
    first's (now the host's), and its ids are the next ones."""
    p = parts(preset("party-noita"))
    doc = example()
    doc["routes"].append({"source": "hand:left.z", "target": "fx.acid.reach", "op": "push"})
    first = spawn(doc, host_of(p))
    p = land(p, first)
    second = spawn(doc, host_of(p))
    assert second.renames == {"acid": "acid.2", "wobble": "wobble.2", "delay": "delay.2",
                              "mod.1": "mod.2"}
    hit = {(c.kind, c.control_or_source, c.host_target) for c in second.conflicts}
    assert ("desk", "cc:0:48", "fx.acid.speed") in hit
    assert ("source", "hand:left.z", "fx.acid.reach") in hit


def test_a_route_onto_a_host_param_another_performer_owns_is_a_conflict():
    doc = example()
    doc["routes"].append({"source": "mod:1", "target": "view.bright", "op": "push"})
    host = Host(routes=(Binding("lfo:0", "view.bright", "push"),))
    landing = spawn(doc, host)
    c = landing.conflicts[-1]
    assert (c.kind, c.control_or_source, c.host_target, c.patch_target) == (
        "target", "view.bright", "lfo:0", "mod:1")


# ---------------------------------------------------------------- the round trip

def round_trip(doc: dict, p, at=(240, 120)) -> tuple[dict, object]:
    landing = spawn(doc, host_of(p), at=at)
    back, refused = patches.lift(*land(p, landing), landing.group["nodes"])
    assert refused == []
    return back, landing


@pytest.mark.parametrize("host", ["party-noita", "party-acid", "party-wake"])
def test_the_example_round_trips(host):
    back, landing = round_trip(example(), parts(preset(host)))
    same(back, example())
    if host == "party-acid":
        assert landing.renames["acid"] == "acid.2"


# a preset whose main run (the effects wired one after another into All
# outputs' picture) is empty: nothing to cut
NO_RUN = {"big-blue-wave", "ember-orbit", "hands-orbit", "hands-play", "hex-engine",
          "inverse-halo", "legacy6", "party-faces", "party-field", "party-tumble",
          "party-wake", "plasma-heart", "spiral-silk", "strobe-cage", "woven-lattice",
          "party-tracer"}


def test_a_patch_cut_from_every_factory_presets_main_run_round_trips():
    """For each factory preset: its main run (`graph.run_back` into
    `output.all.image`) lifted, spawned back into the same preset — every
    id renamed, `.2` — landed, and lifted again reads as the first."""
    skipped, done = set(), []
    for path in sorted(PRESETS.glob("*.json")):
        doc = json.loads(path.read_text())
        spec = G.read_graph(doc["graph"])
        run = G.run_back(spec, "output.all.image")
        if not run:
            skipped.add(path.stem)
            continue
        p = parts(doc)
        cut, refused = patches.lift(*p, [f"render:{n}" for n in run])
        assert refused == [], path.stem
        cut["name"] = path.stem
        assert patches.check(cut) == [], (path.stem, patches.check(cut))
        back, landing = round_trip(cut, p)
        assert all(landing.renames.get(n) == f"{n}.2" for n in run if "." not in n), path.stem
        same(back, cut)
        done.append(path.stem)
    assert skipped == NO_RUN, skipped ^ NO_RUN
    assert len(done) >= 6, done


# ---------------------------------------------------------------- plan 40 T2: the one classifier

def test_select_is_the_lifts_rule_and_refuses_a_group():
    """`select` (factored out of `lift` for the GRAPH page's Group): the
    lift's members and words, and a group named among the ids — no
    nesting — left out in words."""
    spec, table, _values, _layout = parts(preset("party-noita"))
    mem, refused = patches.select(spec, table, ["render:scene", "render:warp", "group.2",
                                                "macro.3", "env.2", "env.7", "mod.1"])
    assert mem.render == ("warp",) and mem.macros == (3,) and mem.envs == (7,)
    assert mem.canvas() == ["render:warp", "env.7", "macro.3"]
    assert refused == ["scene is the frame's; left out",
                       "group.2 is a group: a group holds nodes, not groups; left out",
                       ("env.2 is a sequencer lane's envelope; left out (a patch's envelope "
                        "spawns as 6 or more)"),
                       "mod.1: no such node; left out"]


def test_crossing_and_the_sides_classify_what_crosses_a_region():
    """`crossing` says where each wire sits against the region (and
    `wire_type` what it carries at the edge); `side`, `sub_side` and
    `input_side` where a row, a macro subscriber and a modifier input sit —
    the rules `read` and `lift` keep and the group node draws."""
    spec, table, _values, _layout = parts(preset("party-noita"))
    mem, _ = patches.select(spec, table, NOITA_CORE)
    where = {(w.src, w.dst): (at, patches.wire_type(w, at))
             for w, at in patches.crossing(spec, mem.render)}
    assert where == {("scene", "warp.image"): (patches.INTO, "image"),
                     ("warp", "doublevision.image"): (patches.INSIDE, "image"),
                     ("doublevision", "fractals.image"): (patches.INSIDE, "image"),
                     ("fractals", "tripcolour.image"): (patches.OUT, "image")}
    m = patches._Members(("acid",), mods=(2,), lfos=(5,), macros=(1,))
    assert patches.side(m, "cc:0:48", "fx.acid.speed") == patches.RIG
    assert patches.side(m, "lfo:0", "fx.acid.speed") == patches.INTO      # a host LFO
    assert patches.side(m, "lfo:4", "view.bright") == patches.OUT          # its own, out
    assert patches.side(m, "mod:2", "fx.acid.mix") == patches.INSIDE
    assert not patches.touches(m, "cc:0:48", "view.bright")
    assert patches.sub_side(m, "macro.1", "fx.acid.mix") == patches.INSIDE
    assert patches.sub_side(m, "macro.1", "view.bright") == patches.OUT
    assert patches.sub_side(m, "macro.4", "fx.acid.mix") == patches.INTO
    assert patches.sub_side(m, "macro.4", "view.bright") is None
    assert patches.input_side(m, "mod.2", "lfo:4") == patches.INSIDE
    assert patches.input_side(m, "mod.2", "hand:right.y") == patches.RIG
    assert patches.input_side(m, "mod.2", "lfo:0") == patches.INTO
    assert patches.input_side(m, "mod.7", "lfo:4") == patches.OUT
    assert patches.input_side(m, "mod.7", "lfo:0") is None


# ---------------------------------------------------------------- the library

@pytest.fixture()
def lib(tmp_path):
    """A scratch library whose factory is a copy of the wheel's plus one
    factory patch (the example), so list, hide and the shadow are seen."""
    factory = tmp_path / "factory"
    shutil.copytree(FACTORY, factory)
    (factory / PATCHES).mkdir(exist_ok=True)
    shutil.copy(ACID_WASH, factory / PATCHES / ACID_WASH.name)
    return Library(tmp_path / "home", factory=factory, period=0.0)


def test_the_factory_ships_no_patch_folder_and_lists_nothing(tmp_path):
    assert not (FACTORY / PATCHES).exists() or not list((FACTORY / PATCHES).glob("*.json"))
    lib = Library(tmp_path / "home", period=0.0)
    assert lib.list(PATCHES) == []
    assert PATCHES in lib.kinds and PATCHES in lib.groups()


def test_save_patch_then_read_patch_is_the_same_dict(lib):
    noita = preset("party-noita")
    doc, _ = patches.lift(*parts(noita), NOITA_CORE)
    doc.update(name="Noita Core", note="the middle of noita")
    path = lib.save_patch(doc)
    assert path == lib.home / PATCHES / "noita-core.json"
    assert lib.read_patch("Noita Core") == doc
    assert lib.read_patch("noita-core") == doc
    assert lib.status == "patches: saved Noita Core"
    assert not (lib.home / "presets").exists()          # nothing else written
    # saved again with another note: the old text goes to the trash first
    lib.save_patch({**doc, "note": "changed"})
    assert [t.group for t in lib.trash()] == [PATCHES]
    assert lib.read_patch("Noita Core")["note"] == "changed"
    # the same text again: nothing trashed
    lib.save_patch({**doc, "note": "changed"})
    assert len(lib.trash()) == 1


def test_a_bad_patch_is_a_library_error(lib):
    doc = example()
    with pytest.raises(LibraryError, match="a patch needs a name"):
        lib.save_patch({**doc, "name": ""})
    with pytest.raises(LibraryError, match="view.bright is the host's"):
        lib.save_patch({**doc, "values": {"view.bright": 1.0}})
    (lib.home / PATCHES).mkdir(parents=True, exist_ok=True)
    (lib.home / PATCHES / "old.json").write_text(json.dumps(
        {**doc, "name": "old", "schema": "hyperspace.patch/2"}))
    with pytest.raises(LibraryError, match="is not a hyperspace.patch"):
        lib.read_patch("old")
    (lib.home / PATCHES / "bad.json").write_text(json.dumps(
        {**doc, "name": "bad", "nodes": [*doc["nodes"], {"kind": "scene"}]}))
    with pytest.raises(LibraryError, match="scene is the frame's; left out"):
        lib.read_patch("bad")
    with pytest.raises(LibraryError, match="a patch is spawned, not loaded"):
        lib.load(PATCHES, "acid wash")


def test_patches_list_hide_and_rename_as_presets_do(lib):
    """Factory and the user's by name, a user's shadowing a factory one by
    slug; × hides a factory patch (`hidden.json`'s ``patches``), not a
    user's; a user's patch renames, the old file to the trash."""
    assert lib.list(PATCHES) == ["acid wash"] and lib.is_factory(PATCHES, "acid wash")
    mine = {**example(), "name": "Blue Wash"}
    lib.save_patch(mine)
    assert lib.list(PATCHES) == ["acid wash", "Blue Wash"]
    assert lib.hide(PATCHES, "acid wash")
    assert lib.status == "hidden acid wash — show hidden in the list brings it back"
    assert json.loads((lib.home / HIDDEN).read_text()) == {
        "schema": "hyperspace.hidden/1", "presets": [], "patches": ["acid-wash"]}
    assert lib.list(PATCHES) == ["Blue Wash"]
    assert lib.list(PATCHES, hidden=True) == ["acid wash", "Blue Wash"]
    assert lib.read_patch("acid wash")["name"] == "acid wash"   # hidden, still read
    assert not lib.hide(PATCHES, "Blue Wash")                   # a user's: deleted, not hidden
    assert lib.hidden() == frozenset()                          # the presets' untouched
    # read back by a fresh library over the same home
    again = Library(lib.home, factory=lib.factory, period=0.0)
    assert again.list(PATCHES) == ["Blue Wash"]
    assert lib.unhide(PATCHES, "acid wash")
    assert json.loads((lib.home / HIDDEN).read_text()) == {
        "schema": "hyperspace.hidden/1", "presets": []}
    dst = lib.rename(PATCHES, "Blue Wash", "Deep Wash")
    assert dst.name == "deep-wash.json" and lib.read_patch("Deep Wash")["name"] == "Deep Wash"
    assert lib.list(PATCHES) == ["acid wash", "Deep Wash"]
    assert lib.status == "renamed Blue Wash → Deep Wash"
    assert {t.name for t in lib.trash()} == {"Blue Wash"}
    with pytest.raises(LibraryError, match="factory preset"):
        lib.rename(PATCHES, "acid wash", "x")
    assert lib.delete(PATCHES, "Deep Wash") and lib.list(PATCHES) == ["acid wash"]
