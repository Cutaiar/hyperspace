"""An effect's slots, and the one-way migration of a copy node to one.

A `copy` node drew an effect instance again on another
picture with its knobs and clock, as a node of its own that owned no params.
An effect node has slots — slot 1 is
its own name and ports, slot k is `acid.slot.<k>` (its own `image` / `aux`
in, its own picture out) — every slot run with the one set of knobs. A
saved graph holding copies loads as slots (`graphmigrate.slots_of_copies`,
`twelve`; a patch fragment's `_slots_step`), the picture the same: a slot's
pass is the copy's pass (`graph.Slot` is what `graph.Copy` was), which the
goldens of `through-one-output` — recorded with its copy — hold
(tests/test_golden_frames.py).
"""

from __future__ import annotations

import copy

import numpy as np
import pytest
from test_graph_frame import _draw, _land, _tool, views, wired

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace import patches
from hyperspace.outputs import Switches

# ---------------------------------------------------------------- the migration rule


def _w(a: str, b: str) -> dict:
    return {"from": a, "to": b}


OLD = {"frame": "wired",
       "nodes": [{"kind": "hands", "laid": "over"},
                 {"kind": "effect", "file": "acid"},
                 {"kind": "composite"},
                 {"kind": "copy", "of": "acid"},
                 {"kind": "copy", "of": "acid.2", "instance": 2},
                 {"kind": "copy", "of": "acid", "instance": 3},
                 {"kind": "copy", "of": "teapot", "instance": 4}],
       "wires": [_w("shape", "scene.geometry"), _w("scene", "acid.image"),
                 _w("acid", "output.all.image"),
                 _w("scene", "acid.2.image"), _w("acid.2", "output.4.image"),
                 _w("scene", "composite.under"), _w("hands.layer", "composite.over"),
                 _w("hands", "hands.layer.hands"),
                 _w("composite", "copy.image"), _w("scene", "copy.aux"),
                 _w("copy", "output.2.image"),
                 _w("composite", "copy.2.image"), _w("copy.2", "copy.3.image"),
                 _w("copy.3", "output.3.image"),
                 _w("scene", "copy.4.image"), _w("copy.4", "output.5.image")],
       "keys": ["copy.3", "acid"]}


def test_each_copy_is_its_effects_next_slot():
    """The rule: a section's copies of one effect instance, lowest copy
    instance first, become that effect's next slots; the effect's entry says
    `slots` (one is added for an instance only its wires named); every wire
    end and `keys` member that named the copy names the slot; a copy of no
    effect the section holds is dropped with its wires, said."""
    got, renames, notes = M.slots_of_copies(copy.deepcopy(OLD))
    assert renames == {"copy": "acid.slot.2", "copy.2": "acid.2.slot.2",
                       "copy.3": "acid.slot.3"}
    assert notes == [M.COPY_DROPPED.format(name="copy.4", of="teapot")]
    assert [e for e in got["nodes"] if e["kind"] in ("effect", "copy")] == [
        {"kind": "effect", "file": "acid", "slots": 3},
        {"kind": "effect", "file": "acid", "instance": 2, "slots": 2}]
    assert got["wires"] == [
        *OLD["wires"][:8],
        _w("composite", "acid.slot.2.image"), _w("scene", "acid.slot.2.aux"),
        _w("acid.slot.2", "output.2.image"),
        _w("composite", "acid.2.slot.2.image"), _w("acid.2.slot.2", "acid.slot.3.image"),
        _w("acid.slot.3", "output.3.image")]
    assert got["keys"] == ["acid.slot.3", "acid"]
    spec = G.read_graph(got)
    assert spec.notes == ()
    assert spec.slots == (G.SlotAt("acid", 2), G.SlotAt("acid", 3), G.SlotAt("acid.2", 2))
    # the frame builds what the copies built: a Slot pass per copy, each its
    # effect's, on the picture the copy took
    g = G.build_graph(views(5), spec.wiring(), effects=("acid", "acid.2"))
    for name, effect, src in (("acid.slot.2", "acid", "composite"),
                              ("acid.2.slot.2", "acid.2", "composite"),
                              ("acid.slot.3", "acid", "acid.2.slot.2")):
        n = g.nodes[name]
        assert isinstance(n, G.Slot) and n.effect == effect and n.inputs["image"].name == src
    assert g.nodes["acid.slot.2"].inputs["aux"].name == "scene"
    # a section with no copy is the same object back
    assert M.slots_of_copies(got)[0] is got


def test_a_copy_past_the_most_slots_is_dropped_and_said():
    old = {"frame": "wired", "nodes": [{"kind": "copy", "of": "acid", "instance": k}
                                       for k in range(1, G.MAX_SLOTS + 1)],
           "wires": [_w("scene", "acid.image"), _w("acid", "output.all.image")]}
    got, renames, notes = M.slots_of_copies(old)
    assert len(renames) == G.MAX_SLOTS - 1
    assert notes == [M.COPY_PAST_SLOTS.format(name=f"copy.{G.MAX_SLOTS}", of="acid",
                                              most=G.MAX_SLOTS)]
    assert G.read_graph(got).notes == ()


def test_an_old_loadable_with_copies_loads_as_slots_and_saves_twelve():
    """`/11` → `/12` (`graphmigrate.forward`, the one ladder): the graph's copies
    are slots, their GRAPH places and group memberships dropped (a slot is drawn
    on its effect's node), the strip says it was migrated; a `/12` passes as it
    is."""
    doc = {"schema": M.ELEVEN_SCHEMA, "name": "copies", "values": {},
           "graph": copy.deepcopy(OLD),
           "layout": {"render:acid": [1, 2], "render:copy": [3, 4], "render:copy.3": [5, 6]},
           "groups": [{"id": "group.1", "name": "g", "open": False,
                       "nodes": ["render:copy", "render:acid"]}]}
    fwd = M.forward(copy.deepcopy(doc), {})
    assert fwd.doc["schema"] == M.TWELVE_SCHEMA == M.SAVE_SCHEMA
    assert fwd.migrated == M.SLOTS_MIGRATED_NOTE.format(old=M.ELEVEN_SCHEMA,
                                                        new=M.TWELVE_SCHEMA)
    assert fwd.migrate_notes == (M.COPY_DROPPED.format(name="copy.4", of="teapot"),)
    assert fwd.doc["graph"] == M.slots_of_copies(OLD)[0]
    assert fwd.doc["layout"] == {"render:acid": [1, 2]}
    assert fwd.doc["groups"][0]["nodes"] == ["render:acid"]
    again = M.forward(copy.deepcopy(fwd.doc), {})
    assert again.doc == fwd.doc and again.migrated == "" and again.migrate_notes == ()


def test_a_six_with_a_copy_goes_up_the_whole_ladder():
    """`through-one-output` (a `/6` wired frame with a copy) lands with acid's slot 2 where its copy was, nothing refused."""
    import json
    from pathlib import Path
    path = Path(__file__).parent / "fixtures" / "presets" / "through-one-output.json"
    fwd = M.forward(json.loads(path.read_text()), {})
    spec = G.read_graph(fwd.doc["graph"])
    assert spec.notes == () and spec.slots == (G.SlotAt("acid", 2),)
    assert {(w.src, w.dst) for w in spec.wires} >= {
        ("composite.2", "acid.slot.2.image"), ("acid.slot.2", "output.2.image")}
    assert not any("copy" in (w.src, w.node) for w in spec.wires)


def test_an_old_patch_fragment_with_a_copy_reads_as_slots():
    """A `patch/2` fragment holding an effect and a copy of it is a `patch/3`
    with the slot (`patches._slots_step`): its entries, wires, a boundary
    port's own end and `keys` renamed, the copy's canvas place dropped."""
    old = {"schema": "hyperspace.patch/2", "name": "two looks",
           "nodes": [{"kind": "effect", "file": "acid"}, {"kind": "copy", "of": "acid"}],
           "wires": [_w("acid", "copy.image")],
           "ports": [{"id": "in", "type": "image", "to": "acid.image", "was": "scene"},
                     {"id": "out", "type": "image", "from": "copy", "was": "output.2.image"}],
           "layout": {"render:acid": [0, 0], "render:copy": [1, 0]},
           "keys": ["copy"]}
    new = patches.forward(old)
    assert new["schema"] == patches.SCHEMA == "hyperspace.patch/3"
    assert new["nodes"] == [{"kind": "effect", "file": "acid", "slots": 2}]
    assert new["wires"] == [_w("acid", "acid.slot.2.image")]
    assert new["ports"][1]["from"] == "acid.slot.2" and new["ports"][0]["to"] == "acid.image"
    assert new["layout"] == {"render:acid": [0, 0]} and new["keys"] == ["acid.slot.2"]
    assert patches.check(new) == []
    assert patches.forward(new) == new


def test_slots_round_trip_and_a_spawn_renames_them_with_their_effect():
    """`"slots"` is written only above one, read back the same; a patch
    landing its acid as `acid.3` lands `acid.slot.2` as `acid.3.slot.2`."""
    sec = {"frame": "wired", "nodes": [{"kind": "hands", "laid": "over"},
                                       {"kind": "effect", "file": "acid", "slots": 2}],
           "wires": [_w("scene", "acid.slot.2.image"), _w("acid.slot.2", "output.all.image")]}
    spec = G.read_graph(sec)
    assert spec.to_json() == sec and G.read_graph(spec.to_json()) == spec
    assert patches._family("acid.2.slot.3") == ("acid", 2, ".slot.3")
    assert patches._node_of("acid.slot.2") == "acid"
    rn = patches._Renamer(patches._Members(("acid",)))
    rn.render[("acid", 1)] = 3
    assert rn.src("acid.slot.2") == "acid.3.slot.2"
    assert rn.dst("acid.slot.2.image") == "acid.3.slot.2.image"


# ---------------------------------------------------------------- the picture


@pytest.fixture(scope="module")
def ctx():
    try:
        import moderngl

        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c


@pytest.fixture(scope="module")
def rig(ctx):
    """The golden rig (legacy6, two synthetic hands present), its wiring
    replaced per test (as tests/test_graph_frame.py's)."""
    got = _tool().Rig("legacy6", "present", ctx)
    yield got
    got.close()


@pytest.fixture(autouse=True)
def _current(request):
    """This module's context current before a test that draws on it."""
    if "ctx" in request.fixturenames:
        request.getfixturevalue("ctx").__enter__()


def _acid(rig, on: bool) -> None:
    rig.reg["fx.on"].set(True)
    rig.reg["fx.acid.on"].set(on)
    rig.reg["fx.acid.mix"].set(1.0)


SLOTS = wired(("shape", "scene.geometry"), ("hands", "hands.layer.hands"),
              ("scene", "acid.image"), ("acid", "output.1.image"),
              ("hands.layer", "acid.slot.2.image"), ("acid.slot.2", "output.2.image"),
              ("scene", "acid.slot.3.image"), ("acid.slot.3", "output.3.image"),
              ("scene", "output.4.image"), ("hands.layer", "output.5.image"),
              nodes=[{"kind": "effect", "file": "acid", "slots": 3}])


def test_two_slots_of_one_effect_draw_what_two_copies_drew(ctx, rig):
    """One effect node, three slots, each its own picture through the one
    set of knobs and the one clock, in one frame: a slot on a picture draws
    exactly what the effect's own slot draws on it (slot 3 and slot 1 on the
    scene, byte for byte — what a copy beside its original drew), a slot on
    another picture draws that one bent (slot 2 on the hands' layer), and
    the knobs are shared — acid off, every slot reads its picture through."""
    _land(rig, SLOTS)
    _acid(rig, True)
    one, two, three, scene, layer = _draw(ctx, rig, [Switches()] * 5)
    assert {"acid", "acid.slot.2", "acid.slot.3"} <= set(rig.renderer.stats["effects"])
    assert np.array_equal(one, three)
    assert not np.array_equal(one, scene) and not np.array_equal(two, layer)
    assert not np.array_equal(one, two)
    _acid(rig, False)
    one, two, three, scene, layer = _draw(ctx, rig, [Switches()] * 5)
    assert not ({"acid", "acid.slot.2", "acid.slot.3"} & set(rig.renderer.stats["effects"]))
    assert np.array_equal(one, scene) and np.array_equal(three, scene)
    assert np.array_equal(two, layer)


def test_two_migrated_copies_build_the_frame_the_slots_build():
    """The same frame said twice — once with two copies the migration makes
    slots of, once with the slots written by hand — is one section, and
    builds node for node the same frame (`graph.signature`: a slot's pass is
    the `Effect` a copy's was), each slot's pass its effect's on the picture
    its copy took."""
    old = wired(("shape", "scene.geometry"), ("hands", "hands.layer.hands"),
                ("scene", "acid.image"), ("acid", "output.1.image"),
                ("hands.layer", "copy.image"), ("copy", "output.2.image"),
                ("scene", "copy.2.image"), ("copy.2", "output.3.image"),
                ("scene", "output.4.image"), ("hands.layer", "output.5.image"),
                nodes=[{"kind": "effect", "file": "acid"}, {"kind": "copy", "of": "acid"},
                       {"kind": "copy", "of": "acid", "instance": 2}])
    got, _, notes = M.slots_of_copies(old)
    assert notes == [] and G.read_graph(got) == G.read_graph(SLOTS)
    a = G.build_graph(views(5), G.read_graph(got).wiring(), effects=("acid",))
    b = G.build_graph(views(5), G.read_graph(SLOTS).wiring(), effects=("acid",))
    assert G.signature(a) == G.signature(b)
    assert [G._sig_class(a.nodes[n]) for n in ("acid", "acid.slot.2", "acid.slot.3")] == \
        ["Effect"] * 3


# ---------------------------------------------------------------- keyed copies


def test_a_keyed_copys_knobs_and_node_mode_follow_it_to_its_slot():
    """A copy's black-is-clear knobs (`key.copy.*`, in values and rows) are
    its slot's after the migration, and a controller in node mode on the
    copy points at the effect the slot is drawn on — a whole patch and a
    fragment alike; `key.copy.2.*` stays `copy.2`'s."""
    doc = {"schema": M.ELEVEN_SCHEMA, "name": "keyed", "graph": copy.deepcopy(OLD),
           "values": {"key.copy.level": 0.7, "key.copy.2.soft": 0.3, "view.bright": 1.0},
           "routes": [{"source": "lane:0", "target": "key.copy.level", "op": "push"}],
           "node_mode": [{"player": 1, "controller": "midi", "node": "render:copy"}]}
    got = M.forward(copy.deepcopy(doc), {}).doc
    assert got["graph"]["keys"] == ["acid.slot.3", "acid"]
    assert got["values"] == {"key.acid.slot.2.level": 0.7, "key.acid.2.slot.2.soft": 0.3,
                             "view.bright": 1.0}
    assert got["routes"][0]["target"] == "key.acid.slot.2.level"
    assert got["node_mode"][0]["node"] == "render:acid"
    frag = {"schema": "hyperspace.patch/2", "name": "f",
            "nodes": [{"kind": "effect", "file": "acid"}, {"kind": "copy", "of": "acid"}],
            "wires": [_w("acid", "copy.image")], "keys": ["copy"],
            "values": {"key.copy.level": 0.7}}
    new = patches.forward(frag)
    assert new["keys"] == ["acid.slot.2"] and new["values"] == {"key.acid.slot.2.level": 0.7}
    assert patches.check(new) == []


def test_a_keyed_slot_is_read_and_spawned_with_its_effect():
    """A fragment's key on a member effect's slot is read (`patches.read`) and
    lands renamed with its effect (`spawn`'s landing keys)."""
    frag = {"schema": patches.SCHEMA, "name": "f",
            "nodes": [{"kind": "effect", "file": "acid", "slots": 2}],
            "wires": [_w("acid", "acid.slot.2.image")], "keys": ["acid.slot.2"]}
    assert patches.check(frag) == []
    p = patches.read(frag)
    assert p.keys == ("acid.slot.2",)


def test_dropping_a_first_instance_effect_on_a_cable_keeps_its_slots():
    """An instance 1's entry that says `slots` is no R21 bare entry: put on a
    cable (`graphview._onto`), it stays, and its slots with it."""
    from hyperspace import graphview
    doc = {"frame": "wired", "nodes": [{"kind": "effect", "file": "acid", "slots": 2}],
           "wires": [_w("scene", "output.all.image"), _w("acid.slot.2", "output.2.image")]}
    graphview._onto(doc, "scene", "output.all.image", "acid")
    assert doc["nodes"] == [{"kind": "effect", "file": "acid", "slots": 2}]
    assert G.read_graph(doc).notes == ()


def test_through_traces_all_outputs_run_through_its_slots():
    """"Hands through the effects" puts the hands through every pass of All
    outputs' run — a slot too, each pass by its own name (its own aux), a new
    slot allocated on its effect."""
    sec = {"frame": "wired", "nodes": [{"kind": "effect", "file": "acid", "slots": 2}],
           "wires": [_w("shape", "scene.geometry"), _w("hands", "hands.layer.hands"),
                     _w("scene", "acid.image"), _w("scene", "acid.aux"),
                     _w("acid", "acid.slot.2.image"), _w("hands.layer", "acid.slot.2.aux"),
                     _w("acid.slot.2", "output.all.image"),
                     _w("hands.layer", "output.all.hands")]}
    got = M.through_wires(G.read_graph(sec), 2)
    assert [e for e in got if "kind" in e][1:] == [
        {"kind": "effect", "file": "acid", "slots": 4}]
    wires = [(w["from"], w["to"]) for w in got if "kind" not in w]
    assert ("composite", "acid.slot.3.image") in wires
    assert ("scene", "acid.slot.3.aux") in wires
    assert ("acid.slot.3", "acid.slot.4.image") in wires
    assert ("hands.layer", "acid.slot.4.aux") in wires
    assert ("acid.slot.4", "output.2.image") in wires
