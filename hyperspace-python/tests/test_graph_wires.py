"""Plan 28 N4: the render graph edited as nodes and a wire list, outputs as nodes.

A preset's `graph` section is nodes plus wires: `{"nodes": [...],
"wires": [{"from": "hands.2", "to": "output.2.hands"}, …]}`. A wire
names a node's output and a `node.port`; an input no wire names is the
default graph's (an output's ports follow the session's switches); D1's
`after` / `into` are the same wires written short. A wire this build
cannot honour — no such node or port, a port of another type, two into
one port, a loop — is a note and that port's default. On the GRAPH page
an image cable dragged between two ports is a wire, the picker adds an
effect instance, a hands node or a composite, and deleting a render node
or cable edits the section; each edit lands through the preset's
`GraphSection` (an undo step, the preset dirty, the renderer building the
graph again).

The pure half first (the JSON, the refusals, the graph's shape), then the
edits over a scratch library and the canvas, then the GL half. The
fixtures' pictures are `tests/test_golden_frames.py`'s.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_graph_json import Stub, _bare
from test_presets import boot, put

from hyperspace import graph as G
from hyperspace import graphview, preset
from hyperspace.library import FACTORY, PRESETS
from hyperspace.outputs import SCENE, Switches, View

S = Switches
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "presets"
WIRED = ("hands-glass-only", "wired-outputs")
FILES = {"warp", "acid", "palette", "kaleido"}
RUN = ("warp", "acid", "acid.2", "palette")


def _fixture(slug: str) -> dict:
    return json.loads((FIXTURES / f"{slug}.json").read_text())


def _views(*sw):
    return [View(s, (10, 10)) for s in sw]


def _wires(*pairs) -> list[dict]:
    return [{"from": a, "to": b} for a, b in pairs]


# ---------------------------------------------------------------- the JSON


def test_a_wire_list_round_trips_and_d1_keys_read_as_wires():
    """The section's `wires` read and written back as they were (one a
    line in the file); D1's `after` / `into` read as the wires they are
    short for — the same placements, the same built graph — and are still
    written short when a section has only those; a section with no wires
    writes no `wires` key."""
    section = {"nodes": [{"kind": "hands", "into": "scene"},
                         {"kind": "hands", "instance": 2},
                         {"kind": "effect", "file": "acid", "instance": 2}],
               "wires": _wires(("hands.2", "output.2.hands"), ("palette", "output.1.image"),
                               ("history", "acid.2.image"), ("acid.2", "output.2.image"))}
    spec = G.read_graph(section, effects=FILES)
    assert spec.notes == () and spec.to_json() == section
    assert G.read_graph(spec.to_json()) == spec
    assert spec.wires == (G.Wire("hands.2", "output.2.hands"), G.Wire("palette", "output.1.image"),
                          G.Wire("history", "acid.2.image"), G.Wire("acid.2", "output.2.image"))
    text = preset.dumps({"graph": section})
    assert '"wires": [\n  {"from": "hands.2", "to": "output.2.hands"},\n' in text
    assert json.loads(text)["graph"] == section
    # D1's keys and the wires they are short for: one placement, one graph
    for d1, wires in (
            ({"file": "palette", "after": "hands"}, [("hands", "palette.image")]),
            ({"file": "palette", "into": "output.2"}, [("palette", "output.2.image")]),
            ({"file": "palette", "into": "history"}, [("palette", "history.image")]),
            ({"file": "acid", "instance": 2, "after": "scene"}, [("scene", "acid.2.image")])):
        extra = ([{"kind": "effect", "file": "acid", "instance": 2}]
                 if d1.get("instance") else [])
        short = G.read_graph({"nodes": [{"kind": "effect", **d1}]})
        long = G.read_graph({"nodes": extra, "wires": _wires(*wires)})
        assert short.notes == () and long.notes == (), d1
        assert short.all_wires() == long.all_wires() == [G.Wire(*w) for w in wires]
        assert short.wiring().placed == long.wiring().placed, d1
        assert short.to_json() == {"nodes": [{"kind": "effect", **d1}]}    # still short
        vs = _views(S(), S(through=True))
        a = G.default_graph(vs, short.wiring(), effects=RUN)
        b = G.default_graph(vs, long.wiring(), effects=RUN)
        assert repr(a) == repr(b), d1
    # a graph with only D1's keys, or nodes alone, writes no wires key
    for slug in ("palette-hands", "palette-glass", "acid-scene", "hands-lines"):
        g = _fixture(slug)["graph"]
        assert G.read_graph(g).to_json() == g and "wires" not in g
    # the two fixtures round-trip, wires and all
    for slug in WIRED:
        g = _fixture(slug)["graph"]
        assert G.read_graph(g, effects=FILES).to_json() == g and g["wires"]


def test_a_wire_into_an_output_overrides_its_switch_and_an_unnamed_output_keeps_them():
    """`output.<n>.image` takes the wired picture whatever the output's
    switches (a `Wired` end of its own, its through hands and their guide
    gone with the picture they were in); `.hands` lays the wired layer
    over (and its guide); an output no wire names is exactly the default
    graph's — the session's switches, the rig's, not the look's."""
    vs = _views(S(), S(through=True), S(scene=False), S())
    plain = G.default_graph(vs, effects=RUN)
    spec = G.read_graph({"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
                         "wires": _wires(("history", "acid.2.image"),
                                         ("acid.2", "output.2.image"),
                                         ("hands", "output.4.hands"))}, effects=FILES)
    g = G.default_graph(vs, spec.wiring(), effects=RUN)
    o2, o4 = g.nodes["output.2"], g.nodes["output.4"]
    end = o2.inputs["image"]
    assert isinstance(end, G.Wired) and end.inputs["image"] is g.nodes["acid.2"]
    assert g.nodes["acid.2"].inputs["image"] is g.nodes["history"]
    assert g.nodes["acid.2"].placed == "wire" and "acid.2" in g.placed_names
    assert o2.inputs["hands"] is None and o2.inputs["readout"] is None
    assert end in g.nodes["capture"].after                   # the capture after every end
    assert o4.inputs["hands"] is g.nodes["hands"] and o4.inputs["readout"] is g.nodes["hands"]
    # output 4 had scene + hands over already: its hands are the layer either way
    assert plain.nodes["output.4"].inputs["hands"] is plain.nodes["hands"]
    for name in ("output.1", "output.3"):                    # no wire names them
        assert repr(g.nodes[name]) == repr(plain.nodes[name])
    # acid.2 runs nowhere else: not in any pipeline's run
    assert all(e.effect != "acid.2" for end in (g.nodes["fx"], g.nodes["fx(scene+hands)"])
               for e in end.effects)
    # the hands of hands 2 over output 2 alone, ghost 1 in the scene
    spec = G.read_graph(_fixture("hands-glass-only")["graph"])
    g = G.default_graph(_views(S(), S(), S(scene=False)), spec.wiring())
    assert g.nodes["output.2"].inputs["hands"] is g.nodes["hands.2"]
    assert g.nodes["output.1"].inputs["hands"] is None       # the scene holds ghost
    assert g.nodes["output.3"].inputs["hands"] is g.nodes["hands.2"]  # its switches
    # a wire on a node the built graph lacks is dormant, in words
    g = G.default_graph(_views(S()), G.read_graph(
        {"wires": _wires(("hands", "output.3.hands"))}).wiring())
    assert g.dormant == {"hands → output.3.hands":
                         "wire hands → output.3.hands — no output 3 this frame"}
    assert "wire hands → output.3.hands — no output 3 this frame" in G.graph_words(
        G.read_graph({"wires": _wires(("hands", "output.3.hands"))}), g.dormant)
    # a preset load never writes a switch: the views' switches are as they were
    assert [v.switches for v in vs] == [S(), S(through=True), S(scene=False), S()]


def test_a_wire_of_the_wrong_type_or_into_a_missing_port_is_a_note_and_the_default(tmp_path):
    """Each wire this build cannot honour is a note in words and that
    port's default; the rest of the graph stands. Through a preset load:
    the note on the strip ("; the default wiring"), the section kept as
    the file had it, a clean dot."""
    cases = [
        (("ghost", "output.1.image"),
         "ghost makes geometry, output.1.image takes a picture"),
        (("history", "scene.geometry"), "history makes a picture, scene.geometry takes geometry"),
        (("cover", "output.1.hands"), "cover makes a mask, output.1.hands takes a picture"),
        (("palette", "output.1.picture"),
         "output.1 has no port 'picture' (it takes image, hands, readout)"),
        (("Teapot", "output.1.image"), "no node 'Teapot': a wire leaves"),
        (("teapot", "output.1.image"), "no teapot effect in this build"),
        (("palette", "teapot.image"), "no teapot effect in this build"),
        # plan 33 G: `fx` is the pipeline end now, not an effect file
        (("palette", "fx.image"), "fx.image takes the run from frame; to replace"),
        (("output.1", "output.2.image"), "output.1 is an output: it makes nothing"),
        (("hands.2", "output.1.hands"), "no hands.2 layer in this graph (hands makes"),
        (("ghost", "scene.geometry"), "a hands node's place is its into"),
        (("palette", "output.1.readout"), "output.1.readout takes a hands layer's guide"),
        (("palette", "palette.image"), "palette into itself makes a loop"),
        (("scene", "acid.3.image"), "no acid.3 effect in this build"),
    ]
    for (a, b), why in cases:
        spec = G.read_graph({"nodes": [{"kind": "hands", "into": "scene"}],
                             "wires": _wires((a, b))}, effects=FILES)
        assert len(spec.notes) == 1, (a, b, spec.notes)
        assert spec.notes[0].startswith(f"wire {a} → {b} — {why}"), spec.notes
        assert spec.wires == () and spec.wiring().wires == () and spec.wiring().placed == ()
        assert spec.wiring().hands == "scene"                # the rest stands
    # two wires into one port: each refused, the port keeps its default
    spec = G.read_graph({"wires": _wires(("scene", "output.1.image"),
                                         ("history", "output.1.image"),
                                         ("hands", "output.2.hands"))})
    assert spec.notes == tuple(
        f"wire {s} → output.1.image — output.1.image takes one wire, and 2 go into it "
        "(scene and history): it keeps its default" for s in ("scene", "history"))
    assert spec.wires == (G.Wire("hands", "output.2.hands"),)
    # … D1's placement counts as one: the wire is refused, D1's stands
    spec = G.read_graph({"nodes": [{"kind": "effect", "file": "palette", "into": "output.1"}],
                         "wires": _wires(("history", "output.1.image"))})
    assert spec.notes[0].startswith("wire history → output.1.image — output.1.image takes one")
    assert spec.wiring().placed == (G.EffectAt("palette", 1, into="output.1"),)
    # an effect D1 places is not wired elsewhere
    spec = G.read_graph({"nodes": [{"kind": "effect", "file": "palette", "after": "hands"}],
                         "wires": _wires(("palette", "output.2.hands"))})
    assert spec.notes == (("wire palette → output.2.hands — palette sits after 'hands' already "
                           "(its node says so): one place"),)
    # unreadable wires are a GraphError (the default graph), as A4's nodes are
    for bad in ("x", [1], [{"from": "a"}], [{"from": "scene", "to": "history"}],
                [{"from": "scene", "to": "history.image", "how": 1}]):
        with pytest.raises(G.GraphError):
            G.read_graph({"wires": bad})
    # through a preset load
    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    section = {"nodes": [{"kind": "hands", "into": "scene"}],
               "wires": _wires(("ghost", "output.1.image"), ("hands", "output.2.hands"))}
    put(rig.home, "Odd", values={"view.bright": 3.0}, graph=section)
    rig.lib.load(PRESETS, "Odd")
    assert rig.presets.notes == [
        ("graph: wire ghost → output.1.image — ghost makes geometry, output.1.image takes a "
         "picture; the default wiring")]
    assert _bare(stub.wiring) == G.Wiring(hands="scene",
                                          wires=(G.Wire("hands", "output.2.hands"),))
    assert rig.presets.document("Odd")[preset.GRAPH_KEY] == section
    assert not rig.lib.is_dirty(PRESETS)


def test_a_cycle_of_wires_is_refused():
    """A wire through which a node would read its own picture is refused,
    with the loop in words — every wire on it; D1's placements take part;
    and the build refuses one too (an effect that reads what reads it)."""
    spec = G.read_graph({"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
                         "wires": _wires(("acid.2", "palette.image"),
                                         ("palette", "acid.2.image"),
                                         ("hands", "output.1.hands"))}, effects=FILES)
    assert spec.notes == (
        "wire acid.2 → palette.image — that makes a loop (palette → acid.2 → palette)",
        "wire palette → acid.2.image — that makes a loop (acid.2 → palette → acid.2)")
    assert spec.wires == (G.Wire("hands", "output.1.hands"),)
    # through the history: the history reads acid, acid reads the history
    spec = G.read_graph({"wires": _wires(("history", "acid.image"), ("acid", "history.image"))})
    assert len(spec.notes) == 2 and all("that makes a loop" in n for n in spec.notes)
    # with a D1 placement on the loop
    spec = G.read_graph({"nodes": [{"kind": "effect", "file": "palette", "after": "acid"}],
                         "wires": _wires(("palette", "acid.image"))})
    assert spec.notes == (("wire palette → acid.image — that makes a loop "
                           "(acid → palette → acid)"),)
    assert spec.wiring().placed == (G.EffectAt("palette", 1, after="acid"),)
    assert G.wire_loops([G.Wire("scene", "acid.image")]) == {}


# ---------------------------------------------------------------- the edits


def _edit_rig(tmp_path, **kw):
    """A headless rig over a scratch library, the graph section attached to
    a stub renderer, an Edit on it whose undo steps are counted."""
    rig = boot(tmp_path, **kw)
    stub = Stub()
    rig.presets.graph.attach(stub)
    pushed: list[str] = []
    edit = graphview.Edit(graph=rig.presets.graph, push=pushed.append)
    return rig, stub, edit, pushed


def test_an_edit_lands_the_wire_through_the_preset_and_says_its_refusals(tmp_path):
    """`Edit.wire` lands a new spec through the preset's GraphSection: an
    undo step, the renderer's wiring, the preset dirty, the section the
    save writes; a wire that would be refused is refused in the note's
    words and nothing changes; dragging again into the same port replaces
    the wire; `unwire` takes it out (back to no section, clean)."""
    rig, stub, edit, pushed = _edit_rig(tmp_path)
    rig.presets.save_as("Base")
    assert not rig.lib.is_dirty(PRESETS) and rig.presets.graph.doc is None
    assert edit.wire("ghost", "output.1.image") == (
        "wire ghost → output.1.image — ghost makes geometry, output.1.image takes a picture")
    assert pushed == [] and rig.presets.graph.doc is None
    assert edit.wire("hands", "output.2.hands") is None
    assert pushed == ["wire hands → output.2.hands"] and edit.said == "wired hands → output.2.hands"
    assert stub.wiring.wires == (G.Wire("hands", "output.2.hands"),)
    assert rig.lib.is_dirty(PRESETS)
    assert rig.presets.document("Base")[preset.GRAPH_KEY] == {
        "nodes": [], "wires": _wires(("hands", "output.2.hands"))}
    assert edit.wire("history", "output.2.hands").endswith("or an effect after it over")
    assert edit.wire("scene", "output.2.hands") is None          # replaces it
    assert rig.presets.graph.spec.wires == (G.Wire("frame", "fx.image"),   # (plan 33: the run)
                                            G.Wire("scene", "output.2.hands"))
    # an effect wired after a node: in a section with a run that is a
    # branch reaching nothing, not D1's `after hands` (the owner, 2026-10-24)
    assert edit.wire("hands", "palette.image") is None
    assert stub.wiring.placed == ()
    assert "palette" in graphview.unreached(rig.presets.graph.spec)
    assert edit.unwire("hands", "palette.image") is None
    assert edit.unwire("scene", "output.2.hands") is None
    assert rig.presets.graph.doc is None and _bare(stub.wiring) == G.Wiring()
    assert not rig.lib.is_dirty(PRESETS)
    # the default graph's own edge is refused in words
    assert edit.unwire("history", "output.1.image").startswith(
        "history → output.1.image is the default graph's")
    # a D1 placement moves when its effect is wired elsewhere
    put(rig.home, "Placed", graph={"nodes": [{"kind": "effect", "file": "palette",
                                              "after": "hands"}]})
    rig.lib.load(PRESETS, "Placed")
    assert edit.wire("palette", "output.1.hands") is None
    assert rig.presets.graph.doc == {"nodes": [], "wires": _wires(("palette", "output.1.hands"))}
    # a geometry cable: where a hands node is drawn
    assert edit.wire("ghost", "scene.geometry") is None
    assert stub.wiring.hands == "scene"
    assert edit.unwire("ghost", "scene.geometry") is None and stub.wiring.hands == "layer"


def test_dragging_an_image_cable_on_the_canvas_edits_the_spec_and_dirties_the_preset(
        tmp_path, monkeypatch):
    """On the GRAPH page, drawn headless on the node editor: the widget
    reports a new link between the hands' layer's output and output 2's
    `hands` port; the page's dispatch (by the cable's type: image is N4's)
    checks it, accepts it and lands the wire — the preset dirty, one undo
    step, the renderer's wiring holding the wire. A drag of the wrong type
    is refused red, with the note's words, and nothing changes; a render
    cable deleted on the canvas is unwired."""
    from imgui_bundle import imgui_node_editor as ed
    from test_ui_shell import build_rig, frame

    from hyperspace import ui_graph

    with build_rig(tmp_path) as rig:
        rig.lib.load(PRESETS, "party-trip")
        rig.lib.presets.save_as("mine")
        assert not rig.lib.is_dirty(PRESETS)
        stub = Stub()
        rig.lib.presets.graph.attach(stub)
        g = G.default_graph(_views(S(), S(scene=False)), effects=("acid", "palette"))
        stub._graph = g
        rig.panel.renderer = stub
        frame(rig.panel, "graph")
        st = ui_graph._state(rig.panel)
        pushed = []
        monkeypatch.setattr(ui_graph.undo, "push", lambda label, load=False: pushed.append(label))
        got = {"tip": None, "accepted": 0, "rejected": 0}

        def drag(a: str, b: str):
            # what the widget reports while a cable is dragged from pin a to b
            pins = (ui_graph._id(st, a), ui_graph._id(st, b))
            monkeypatch.setattr(ed, "begin_create", lambda *a, **k: True)
            monkeypatch.setattr(ed, "end_create", lambda: None)
            monkeypatch.setattr(ui_graph, "new_link", lambda: pins)
            monkeypatch.setattr(ed, "accept_new_item",
                                lambda *a: got.__setitem__("accepted", got["accepted"] + 1)
                                or True)
            monkeypatch.setattr(ed, "reject_new_item",
                                lambda *a: got.__setitem__("rejected", got["rejected"] + 1))
            monkeypatch.setattr(ui_graph, "_drag_tip", lambda w: got.__setitem__("tip", w))
            frame(rig.panel, "graph")
            monkeypatch.undo()

        # the input end first: the page turns it round
        drag("rin:output.2/hands", "rout:hands")
        assert got["accepted"] == 1 and got["tip"] is None
        assert stub.wiring.wires == (G.Wire("hands", "output.2.hands"),)
        assert rig.lib.presets.graph.doc == {"nodes": [],
                                             "wires": _wires(("hands", "output.2.hands"))}
        assert rig.lib.is_dirty(PRESETS) and pushed == ["wire hands → output.2.hands"]
        assert st["said"] == "wired hands → output.2.hands"
        # the wrong type: red, the words, nothing changed
        monkeypatch.setattr(ui_graph.undo, "push", lambda label, load=False: pushed.append(label))
        drag("rout:ghost", "rin:output.1/image")
        assert got["rejected"] == 1 and got["tip"] == (
            "wire ghost → output.1.image — ghost makes geometry, output.1.image takes a picture")
        assert stub.wiring.wires == (G.Wire("hands", "output.2.hands"),) and len(pushed) == 1
        # an effect of a pipeline's run names its instance
        monkeypatch.setattr(ui_graph.undo, "push", lambda label, load=False: pushed.append(label))
        drag("rout:acid", "rin:output.2/image")
        # (a wire, not D1's `into output.2`, in a section with a run: the
        # owner, 2026-10-24)
        assert stub.wiring.placed == ()
        assert G.Wire("acid", "output.2.image") in stub.wiring.wires
        # a render cable deleted on the canvas
        cable = graphview.VCable("wire:hands>output.2/hands", "rout:hands", "rin:output.2/hands",
                                 G.IMAGE, ref=(g.nodes["hands"], g.nodes["output.2"], "hands"),
                                 kind="render")
        cut = []
        monkeypatch.setattr(ed, "accept_deleted_item", lambda *a: cut.append("accepted"))
        monkeypatch.setattr(ed, "reject_deleted_item", lambda: cut.append("rejected"))
        ui_graph.DELETE["render"](rig.panel, st, None, cable)
        assert cut == ["accepted"] and st["note"] == ""
        assert stub.wiring.wires == (G.Wire("acid", "output.2.image"),)
        # the default graph's own edge: kept, said on the head
        ui_graph.DELETE["render"](rig.panel, st, None, cable)
        assert cut == ["accepted", "rejected"] and "is the default graph's" in st["note"]
        monkeypatch.undo()
        rig.panel.close()


def test_the_picker_adds_an_effect_instance_with_its_params(tmp_path):
    """The right-click picker lists every effect file, a hands node and a
    composite; an effect picked is the file itself while nothing holds it
    (R25: switched on), then the next instance (`EffectAt(file, n + 1)`)
    with its own `fx.<file>.<n+1>.*` params, at their defaults but `on`,
    on no wire; deleting the node drops it and its params; a hands node
    is the next instance, drawn in the scene while another makes the
    layer; a composite is the first; the frame's own nodes stay."""
    rig, stub, edit, pushed = _edit_rig(tmp_path)
    kinds = graphview.picker(edit)
    assert ("effect", "acid", "acid") in kinds and kinds[-2:] == [
        ("hands", None, "hands"), ("composite", None, "composite")]
    assert "fx.acid.2.on" not in rig.reg
    assert edit.add_node("effect", "acid") is None
    assert edit.said == "acid added: its params are fx.acid.*"
    assert rig.reg["fx.acid.on"].value is True                    # R25: on, to show
    assert rig.presets.graph.spec.effects == (G.EffectAt("acid", 1),)
    assert edit.add_node("effect", "acid") is None
    assert edit.said == "acid.2 added: its params are fx.acid.2.*"
    assert rig.reg["fx.acid.2.on"].value is True
    assert {"fx.acid.2.mix", "fx.acid.2.twist"} <= {p.id for p in rig.reg}
    assert rig.presets.graph.spec.effects == (G.EffectAt("acid", 1), G.EffectAt("acid", 2))
    assert edit.add_node("effect", "acid") is None and "fx.acid.3.on" in rig.reg
    assert edit.add_node("effect", "teapot") == "no teapot effect in this build"
    assert edit.drop_node("acid.3") is None and "fx.acid.3.on" not in rig.reg
    # plan 33 T7 (R21): instance 1 is in the graph where it is wired, and
    # deleting it takes it out like any instance — not in it, it says so
    assert edit.drop_node("zoomblur") == "zoomblur is not in the preset's graph"
    # … wired (a branch, not D1's `after hands`: the owner, 2026-10-24):
    # deleting it takes it, and its wire, out of the graph
    assert edit.wire("hands", "palette.image") is None
    assert G.Wire("hands", "palette.image") in rig.presets.graph.spec.wires
    assert edit.drop_node("palette") is None and edit.said == "palette deleted"
    assert G.Wire("hands", "palette.image") not in rig.presets.graph.spec.wires
    assert stub.wiring.placed == ()
    assert edit.add_node("hands") is None and edit.said == "ghost.2 added, drawn in the scene"
    assert "ghost.2.alpha" in rig.reg
    assert edit.add_node("composite") is None
    assert rig.presets.graph.spec.composites() == (G.CompositeAt(1),)
    assert edit.wire("hands", "composite.over") is None
    assert edit.wire("composite", "output.1.image") is None
    assert stub.wiring.wires == (G.Wire("hands", "composite.over"),
                                 G.Wire("composite", "output.1.image"))
    g = G.default_graph(_views(S()), stub.wiring)
    comp = g.nodes["composite"]
    assert isinstance(comp, G.Composite) and comp.inputs["over"] is g.nodes["hands"]
    assert g.nodes["output.1"].inputs["image"].inputs["image"] is comp
    assert edit.drop_node("composite") is None and stub.wiring.wires == ()
    assert edit.drop_node("output.1") == "output.1 is the frame's own: it stays"
    assert edit.drop_node("ghost") == ("hands 1 is the frame's own hands: it stays "
                                       "(switch it off on HANDS)")
    assert len(pushed) == 11


def test_an_edit_is_one_undo_step(tmp_path):
    """A wire landed by the page is one undo step: ⌘Z puts the graph (and
    the renderer's wiring) back as it was."""
    from test_undo import boot as undo_boot
    from test_undo import settle

    from hyperspace import undo

    r = undo_boot(tmp_path / "home")
    settle(r)
    r.undo.clear()
    stub = Stub()
    r.presets.graph.attach(stub)
    edit = graphview.Edit(graph=r.presets.graph, push=lambda label: undo.push(label, load=True))
    assert edit.wire("hands", "output.2.hands") is None
    settle(r)
    assert stub.wiring.wires == (G.Wire("hands", "output.2.hands"),)
    assert r.undo.undo() and r.undo.status.endswith("wire hands → output.2.hands")
    assert r.presets.graph.doc is None and _bare(stub.wiring) == G.Wiring()


def test_hands_as_lines_through_the_acid_with_tracers_by_wires_alone(ctx, tmp_path):
    """The wishlist's done-when: "hands as lines, through the acid, with
    tracers", made on the GRAPH page — a geometry cable from the hands
    into the scene (which sets the hands node's `into`, A4's JSON: a
    hands node's place is not a wire, see the register row) and the node
    drawn as lines from its menu (`set_node`) — reproduces the fixture
    `hands-lines.json`: the same wiring, the same graph, the same picture.
    The name keeps the brief's words; no image wire is involved."""
    import numpy as np
    from test_outputs import rig as gl_rig
    from test_outputs import run, views

    _, stub, edit, _ = _edit_rig(tmp_path)
    assert edit.wire("ghost", "scene.geometry") is None
    assert edit.set_node("ghost", draw="lines") is None
    # with the hands in the scene the history holds them whatever it says;
    # the fixture says so too, and a set_node on the history is the JSON's
    want = G.read_graph(_fixture("hands-lines")["graph"])
    assert _bare(stub.wiring) == G.Wiring(hands="scene", draw="lines")
    assert want.wiring() == G.Wiring(hands="scene", draw="lines", history="scene+hands")
    vs = _views(S(), S(through=True), S(scene=False))
    assert repr(G.default_graph(vs, _bare(stub.wiring), effects=("acid",))) == repr(
        G.default_graph(vs, want.wiring(), effects=("acid",)))

    def picture(wiring):
        r = gl_rig(ctx, effects=("acid",), echoes=True)
        r.wiring = wiring
        return run(ctx, r, views(ctx, S(), S(through=True)), frames=3)

    got, fixture = picture(_bare(stub.wiring)), picture(want.wiring())
    assert all(np.array_equal(a, b) for a, b in zip(got, fixture))
    plain = picture(G.Wiring())
    assert not np.array_equal(got[0], plain[0])               # the lines, in the scene


def _wire_built(n) -> bool:
    """A node only a wire builds: a `Wired` end (`wire(…)`) or a composite
    the section added — instance 1 is plain `composite`, later ones
    `composite.<n>`; the default graph's own are `composite(…)`."""
    return isinstance(n, (G.Wired, G.Composite)) and (
        n.name == "composite" or n.name.startswith(("wire(", "composite.")))


def test_the_wire_built_check_sees_a_wired_composite():
    """The check `test_no_factory_preset_changes` leans on is not vacuous:
    a section adding composite 1 (named plain `composite`) and composite 2
    trips it; the default graph's own composites do not."""
    section = {"nodes": [{"kind": "composite"}, {"kind": "composite", "instance": 2}],
               "wires": _wires(("hands", "composite.over"), ("composite", "output.1.image"),
                               ("hands", "composite.2.over"), ("composite.2", "output.2.image"))}
    spec = G.read_graph(section, effects=FILES)
    assert spec.notes == ()
    g = G.default_graph(_views(S(), S()), spec.wiring(), effects=RUN)
    built = sorted(n.name for n in g.nodes.values() if _wire_built(n))
    assert "composite" in built and "composite.2" in built
    plain = G.default_graph(_views(S(), S(through=True)), effects=RUN)
    assert any(isinstance(n, G.Composite) for n in plain.nodes.values())
    assert not any(_wire_built(n) for n in plain.nodes.values())


def test_no_factory_preset_changes():
    """No library file carries a graph (so no wire): every factory preset
    loads with the default graph — and the default graph holds nothing a
    wire builds: no `Wired` end, no effect placed by a wire, nothing
    dormant, every output's picture a pipeline's end or the ground."""
    for path in sorted(FACTORY.rglob("*.json")):
        doc = json.loads(path.read_text())
        assert not isinstance(doc, dict) or "graph" not in doc, path
    for sw in ((S(),), (S(), S(through=True)), (S(scene=False), S(), S(through=True)),
               (S(scene=False, hands=True, through=True), S(scene=False))):
        g = G.default_graph(_views(*sw), effects=RUN)
        assert not any(_wire_built(n) for n in g.nodes.values())
        assert all(n.placed is None for n in g.nodes.values() if isinstance(n, G.Effect))
        assert g.dormant == {} and g.notes == []
        for out in g.outputs:
            img = out.inputs["image"]
            assert img is None or (isinstance(img, G.Fx) and not isinstance(img, G.Wired))


def test_the_fixtures_load_clean_through_a_scratch_library(tmp_path):
    """Each N4 fixture loaded like a user's preset: no note, a clean dot,
    the renderer handed its wires, the section saved back as the file."""
    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    for slug in WIRED:
        doc = _fixture(slug)
        dst = rig.home / "presets" / f"{slug}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text((FIXTURES / f"{slug}.json").read_text())
        assert rig.lib.load(PRESETS, slug) == [] and rig.presets.notes == [], slug
        assert not rig.lib.is_dirty(PRESETS), slug
        assert rig.presets.document(slug)[preset.GRAPH_KEY] == doc["graph"]
    assert stub.wiring.wires == (G.Wire("history", "acid.2.image"),
                                 G.Wire("acid.2", "output.2.image"))
    assert stub.wiring.placed == (G.EffectAt("palette", 1, into="output.1"),)
    assert rig.reg["fx.acid.2.on"].value is True


def test_the_words_say_the_wires():
    """OUTPUT's "shows:" line and LOOKBACK's history line say the wires."""
    from hyperspace.ui import output_shows

    spec = G.read_graph(_fixture("wired-outputs")["graph"])
    w = spec.wiring()
    assert G.graph_words(spec) == ("graph: acid ×2 · palette on output 1 only · acid 2 reads "
                                   "the history · output 2 shows acid 2")
    assert output_shows(S(through=True), True, True, 1.0, w, n=2)[0] == "acid 2 by a wire"
    # the FX page's groups (plan 33 T7, `ui_fx.groups`; plan 30 D2's
    # `placed_chips` went with the placed grid) say where a wire puts each
    from hyperspace.ui_fx import groups
    assert groups(spec) == [("→ output 1", ["palette"]), ("→ output 2", ["acid.2"])]
    assert groups(G.read_graph({"wires": _wires(("hands", "palette.image"),
                                                ("palette", "output.2.hands"))})
                  ) == [("→ output 2", ["palette"])]
    assert output_shows(S(), True, True, 1.0, w, n=1)[0].endswith(
        "palette on this output only")
    spec = G.read_graph(_fixture("hands-glass-only")["graph"])
    w = spec.wiring()
    assert output_shows(S(), True, True, 1.0, w, n=2)[0].endswith(" · hands 2 over output 2")
    assert G.history_words(G.read_graph({"wires": _wires(("hands", "history.image"))}).wiring()
                           ) == "history: the scene · the history holds the hands"


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def test_a_wired_output_shows_its_picture_and_no_other_output_moves(ctx):
    """With warp on: the history wired into output 2's picture shows the
    frame with no effect (byte for byte the chain-less rig's), output 1 is
    byte for byte the default graph's; the chain ran once (for output 1),
    and output 2's route is its own end."""
    import numpy as np
    from test_outputs import rig as gl_rig
    from test_outputs import run, views, wired

    def frame(effects, section):
        r = gl_rig(ctx, effects=effects, hands=False)
        if section is not None:          # (plan 33 R23: the rig's run kept)
            r.wiring = wired(r, section)
        return r, run(ctx, r, views(ctx, S(), S()), frames=2)

    r, (a1, a2) = frame(("warp",), {"wires": _wires(("history", "output.2.image"))})
    _, (b1, _) = frame(("warp",), None)
    _, (c1, _) = frame((), None)
    assert np.array_equal(a1, b1) and np.array_equal(a2, c1) and not np.array_equal(a1, a2)
    assert r.stats["chain_runs"] == 1 and r.stats["routes"][1] == ("wire(output.2)", False)
    assert r.stats["routes"][0] == (SCENE, False)


def test_hands_2_wired_to_the_glass_alone(ctx):
    """`hands-glass-only`: ghost in the scene, ghost.2 the layer, wired to
    output 2's hands only — output 2 is output 1 plus hands 2 laid over
    where its layer covers; output 1 shows no layer."""
    from test_outputs import rig as gl_rig
    from test_outputs import run, views

    from hyperspace.ghost import GhostState

    r = gl_rig(ctx, effects=())
    r.ghost_states = {"ghost.2": GhostState(on=True)}
    r.wiring = G.read_graph(_fixture("hands-glass-only")["graph"]).wiring()
    a, b = run(ctx, r, views(ctx, S(), S()), frames=2)
    g2 = r.ghost_of("ghost.2")
    assert r._graph.nodes["output.2"].inputs["hands"] is r._graph.nodes["hands.2"]
    differ = (a != b).any(axis=2)
    assert differ.any()
    assert r.stats["routes"] == [(SCENE, False), (SCENE, True)]
    assert g2.tex is not None


def test_a_renderer_rebuilds_its_graph_when_an_edit_lands(ctx, tmp_path):
    """The renderer's graph key holds the wires (they ride in the wiring):
    an edit that lands a new GraphSpec builds the graph again, an edit
    landing the same spec does not."""
    from test_outputs import rig as gl_rig
    from test_outputs import run, views

    r = gl_rig(ctx, effects=())
    run(ctx, r, views(ctx, S(), S()), frames=1)
    first = r._graph
    rig = boot(tmp_path)
    rig.presets.graph.attach(r)
    edit = graphview.Edit(graph=rig.presets.graph, render=first)
    assert edit.wire("rout:hands", "rin:output.2/hands") is None
    run(ctx, r, views(ctx, S(), S()), frames=1)
    assert r._graph is not first and r.wiring.wires == (G.Wire("hands", "output.2.hands"),)
    again = r._graph
    run(ctx, r, views(ctx, S(), S()), frames=1)
    assert r._graph is again


def test_a_composite_wired_into_an_outputs_hands_is_laid_as_its_own_picture(ctx):
    """A wire into `output.<n>.hands` from a node that is not a hands' layer
    (a composite: the scene with the hands laid on) is laid through the
    node — its own picture, not hands 1's Ghost — onto the output's ground;
    a presenter's hand-off carries that picture. The history is refused
    there (it paints into what reads it: there is no picture to lay)."""
    import numpy as np
    from test_outputs import H, W, run, views
    from test_outputs import rig as gl_rig

    spec = G.read_graph({"nodes": [{"kind": "composite"}],
                         "wires": _wires(("scene", "composite.under"),
                                         ("hands", "composite.over"),
                                         ("composite", "output.2.hands"))})
    assert spec.notes == ()
    r = gl_rig(ctx, effects=())
    r.wiring = spec.wiring()
    a, b = run(ctx, r, views(ctx, S(), S(scene=False, hands=False)), frames=2)
    comp = r._graph.nodes["composite"]
    assert r._graph.nodes["output.2"].inputs["hands"] is comp
    assert r.stats["routes"][1] == (None, True)
    # the scene with the hands, laid opaque onto the ground: output 1's picture
    assert b.any() and np.abs(a - b).max() <= 2
    # a presenter gets the composite's picture, not hands 1's layer
    pv = View(S(scene=False, hands=False), (W, H), presenter=object())
    run(ctx, r, [views(ctx, S())[0], pv], frames=1)
    assert pv.handoff.hands is not None and pv.handoff.hands is not r.ghost.tex
    assert pv.handoff.hands is r._frames["composite"][0]
    assert G.read_graph({"wires": _wires(("history", "output.1.hands"))}).notes[0].endswith(
        "wire it into the output's image, or an effect after it over")


def test_a_hands_wire_on_a_through_output_replaces_the_switch_hands(ctx):
    """A through output's switch hands are inside its picture (laid on
    before the chain): a wire into its `hands` port replaces them — its
    picture becomes the end the hands were laid onto (the scene's, or the
    ground with the scene off) and the wired layer alone is laid over, so
    the hands are never drawn twice and the wire is never dropped."""
    import numpy as np
    from test_outputs import rig as gl_rig
    from test_outputs import run, views, wired

    section = {"wires": _wires(("hands", "output.2.hands"), ("hands", "output.3.hands"))}
    r = gl_rig(ctx, effects=("warp",))
    w = r.wiring = wired(r, section)                 # (plan 33 R23: warp's run with it)
    vs = _views(S(), S(through=True), S(scene=False, through=True))
    g = G.default_graph(vs, w, effects=("warp",))
    o2, o3 = g.nodes["output.2"], g.nodes["output.3"]
    assert o2.inputs["image"] is g.nodes["fx"] and o2.inputs["hands"] is g.nodes["hands"]
    assert o3.inputs["image"] is None and o3.inputs["hands"] is g.nodes["hands"]
    a, b, _ = run(ctx, r, views(ctx, S(), S(through=True), S(scene=False, through=True)),
                  frames=2)
    assert np.array_equal(a, b)                    # the scene, the hands over: once
    assert r.stats["routes"][1:] == [(SCENE, True), (None, True)]
    assert r.stats["chain_runs"] == 1              # no SCENE+HANDS or HANDS run


def test_an_aux_wire_leaves_a_placed_effect_where_it_sits(tmp_path):
    """Plan 32 T7: dragging a channel onto a placed effect's `aux` port is
    a second picture, not a placement — the effect keeps its D1 place and
    the wire rides beside it; its `image` port still moves it — off its
    place onto that wire, a branch reaching nothing until it is wired on
    (a section with a run shortens no wire: the owner, 2026-10-24)."""
    rig, stub, edit, _ = _edit_rig(tmp_path)
    put(rig.home, "Placed", graph={"nodes": [{"kind": "effect", "file": "blend",
                                              "after": "hands"}]})
    rig.lib.load(PRESETS, "Placed")
    assert edit.wire("media.a", "blend.aux") is None
    assert rig.presets.graph.doc == {
        "nodes": [{"kind": "effect", "file": "blend", "after": "hands"}],
        "wires": _wires(("media.a", "blend.aux"))}
    assert stub.wiring.placed == (G.EffectAt("blend", 1, after="hands"),)
    assert stub.wiring.wires == (G.Wire("media.a", "blend.aux"),)
    assert edit.wire("scene", "blend.image") is None
    assert stub.wiring.placed == ()
    assert "blend" in graphview.unreached(rig.presets.graph.spec)
