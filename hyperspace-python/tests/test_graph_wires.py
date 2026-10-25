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
from test_graph_json import Stub, _bare, _old
from test_presets import boot, put
from wiredframe import Shows, Thru, graph, wire_switches, wiring

from hyperspace import graph as G
from hyperspace import graphview, preset
from hyperspace.library import FACTORY, PRESETS
from hyperspace.outputs import Switches, View

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
        shows = [Shows(), Shows(through=True)]
        a = graph(shows, short, effects=RUN)
        b = graph(shows, long, effects=RUN)
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
    state (an end of its own, `Shown`; its through hands and their guide
    gone with the picture they were in); `.hands` lays the wired layer
    over (and its guide); an output no wire names is exactly the frame's
    without the wires — the window's mutes, the rig's, not the look's."""
    shows = [Shows(), Shows(through=True), Shows(scene=False), Shows()]
    plain = graph(shows, effects=RUN)
    section = {"nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
               "wires": _wires(("history", "acid.2.image"), ("acid.2", "output.2.image"),
                               ("hands", "output.4.hands"))}
    assert G.read_graph(section, effects=FILES).notes == ()
    g = graph(shows, section, effects=RUN)
    o2, o4 = g.nodes["output.2"], g.nodes["output.4"]
    end = o2.inputs["image"]
    assert isinstance(end, G.Shown) and end.inputs["image"] is g.nodes["acid.2"]
    assert g.nodes["acid.2"].inputs["image"] is g.nodes["lookback"]
    assert g.nodes["acid.2"].placed == "wire" and "acid.2" in g.placed_names
    assert o2.inputs["hands"] is None and o2.inputs["readout"] is None
    assert end in g.nodes["lookback(capture)"].after          # the capture after every end
    assert (o4.inputs["hands"] is g.nodes["hands.layer"]
            and o4.inputs["readout"] is g.nodes["hands.layer"])
    # output 4 had scene + hands over already: its hands are the layer either way
    assert plain.nodes["output.4"].inputs["hands"] is plain.nodes["hands.layer"]
    for name in ("output.1", "output.3"):                    # no wire names them
        assert repr(g.nodes[name]) == repr(plain.nodes[name])
    # acid.2 runs nowhere else: not in the run
    assert "acid.2" not in g.run
    # the hands of hands 2 over output 2 alone, hands 1 in the scene
    spec = G.read_graph(_fixture("hands-glass-only")["graph"])
    g = graph([Shows(), Shows(), Shows(scene=False)], spec)
    assert g.nodes["output.2"].inputs["hands"] is g.nodes["hands.2.layer"]
    assert g.nodes["output.1"].inputs["hands"] is None       # the scene holds hands 1
    assert g.nodes["output.3"].inputs["hands"] is g.nodes["hands.2.layer"]   # its state
    # a wire on a node the built graph lacks is dormant, in words (plan 35
    # T4: an output this rig has not open, in the wired frame's names)
    g = G.build_graph(_views(S()), G.read_graph(
        {"wires": _wires(("hands", "output.3.hands"))}).wiring())
    assert g.dormant == {"hands.layer → output.3.hands":
                         "wire hands.layer → output.3.hands — no output 3 this frame"}
    # a preset load never writes a mute: the windows' switches are as they were
    vs = _views(S(), S(scene=False))
    G.build_graph(vs, G.read_graph(section, effects=FILES).wiring(), effects=RUN)
    assert [v.switches for v in vs] == [S(), S(scene=False)]


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
    assert rig.presets.notes == [       # (plan 35 V2: in the new ids — `ghost` is `hands`)
        ("graph: wire hands → output.1.image — hands makes geometry, output.1.image takes a "
         "picture; the default wiring")]
    assert _bare(_old(stub.wiring)) == G.Wiring(hands="scene",
                                          wires=(G.Wire("hands", "output.2.hands"),))
    # (row 394: the save is the frame the load landed)
    assert rig.presets.document("Odd")[preset.GRAPH_KEY] == rig.presets.graph.free_doc()
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
    the wire; `unwire` takes it out. Plan 35 G: in the wired frame's ids —
    the hands geometry `hands`, its layer `hands.layer`, the look-back
    `lookback` — every wire of the frame an ordinary wire."""
    rig, stub, edit, pushed = _edit_rig(tmp_path)
    rig.presets.save_as("Base")
    assert not rig.lib.is_dirty(PRESETS) and rig.presets.graph.doc is None
    assert edit.wire("hands", "output.1.image") == (
        "wire hands → output.1.image — hands makes geometry, output.1.image takes a picture")
    assert pushed == [] and rig.presets.graph.doc is None
    assert edit.wire("hands.layer", "output.2.hands") is None
    assert pushed == ["wire hands.layer → output.2.hands"]
    assert edit.said == "wired hands.layer → output.2.hands"
    assert G.Wire("hands.layer", "output.2.hands") in stub.wiring.wires
    assert rig.lib.is_dirty(PRESETS)
    assert preset.GRAPH_KEY in rig.presets.document("Base")
    assert edit.wire("lookback", "output.2.hands").endswith("or an effect after it over")
    assert edit.wire("scene", "output.2.hands") is None          # replaces it
    wires = set(rig.presets.graph.spec.wires)
    assert G.Wire("scene", "output.2.hands") in wires
    assert G.Wire("hands.layer", "output.2.hands") not in wires
    # an effect wired after a node: a branch reaching nothing, not D1's
    # `after` (the owner, 2026-10-24)
    assert edit.wire("hands.layer", "palette.image") is None
    assert stub.wiring.placed == ()
    assert "palette" in graphview.unreached(rig.presets.graph.spec)
    assert edit.unwire("hands.layer", "palette.image") is None
    assert edit.drop_node("palette") is None
    assert edit.unwire("scene", "output.2.hands") is None
    assert not [w for w in rig.presets.graph.spec.wires if w.node == "output.2"]
    # (plan 35 G: no default edge is left to refuse — a wire the section
    # does not have is the one refusal)
    assert edit.unwire("lookback", "output.1.image") == graphview.NO_SUCH_WIRE.format(
        wire="lookback → output.1.image")
    # a D1 placement moves when its effect is wired elsewhere
    put(rig.home, "Placed", graph={"nodes": [{"kind": "effect", "file": "palette",
                                              "after": "hands"}]})
    rig.lib.load(PRESETS, "Placed")
    assert edit.wire("palette", "output.1.hands") is None
    spec = rig.presets.graph.spec
    assert G.Wire("palette", "output.1.hands") in spec.wires
    assert not [e for e in spec.effects if e.placed]
    # a geometry cable: the hands into the scene is a wire (plan 35 F), before the shape
    assert edit.wire("hands", "scene.geometry") is None
    into = [w.src for w in rig.presets.graph.spec.wires if w.dst == "scene.geometry"]
    assert into == ["hands", "shape"]
    assert edit.unwire("hands", "scene.geometry") is None
    assert G.Wire("hands", "scene.geometry") not in rig.presets.graph.spec.wires


def test_dragging_an_image_cable_on_the_canvas_edits_the_spec_and_dirties_the_preset(
        tmp_path, monkeypatch):
    """On the GRAPH page, drawn headless on the node editor: the widget
    reports a new link between the hands' layer's output and output 2's
    `hands` port; the page's dispatch (by the cable's type: image is N4's)
    checks it, accepts it and lands the wire — the preset dirty, one undo
    step, the renderer's wiring holding the wire. A drag of the wrong type
    is refused red, with the note's words, and nothing changes; a render
    cable deleted on the canvas is unwired (plan 35 G: a second delete of
    it is the one refusal left, "no such wire")."""
    from imgui_bundle import imgui_node_editor as ed
    from test_ui_shell import build_rig, frame

    from hyperspace import ui_graph

    with build_rig(tmp_path) as rig:
        rig.lib.load(PRESETS, "party-trip")
        rig.lib.presets.save_as("mine")
        assert not rig.lib.is_dirty(PRESETS)
        stub = Stub()
        rig.lib.presets.graph.attach(stub)
        g = G.build_graph(_views(S(), S(scene=False)), stub.wiring,
                          effects=("plasma", "kaleido", "zoomblur", "huecycle"))
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
        drag("rin:output.2/hands", "rout:hands.layer")
        assert got["accepted"] == 1 and got["tip"] is None
        assert G.Wire("hands.layer", "output.2.hands") in stub.wiring.wires
        assert rig.lib.is_dirty(PRESETS) and pushed == ["wire hands.layer → output.2.hands"]
        assert st["said"] == "wired hands.layer → output.2.hands"
        # the wrong type: red, the words, nothing changed
        monkeypatch.setattr(ui_graph.undo, "push", lambda label, load=False: pushed.append(label))
        before = stub.wiring.wires
        drag("rout:hands", "rin:output.1/image")
        assert got["rejected"] == 1 and got["tip"] == (
            "wire hands → output.1.image — hands makes geometry, output.1.image takes a picture")
        assert stub.wiring.wires == before and len(pushed) == 1
        # an effect of the run names its instance
        monkeypatch.setattr(ui_graph.undo, "push", lambda label, load=False: pushed.append(label))
        drag("rout:plasma", "rin:output.2/image")
        assert stub.wiring.placed == ()
        assert G.Wire("plasma", "output.2.image") in stub.wiring.wires
        # a render cable deleted on the canvas
        cable = graphview.VCable("wire:hands.layer>output.2/hands", "rout:hands.layer",
                                 "rin:output.2/hands", G.IMAGE,
                                 ref=G.Wire("hands.layer", "output.2.hands"), kind="render")
        cut = []
        monkeypatch.setattr(ed, "accept_deleted_item", lambda *a: cut.append("accepted"))
        monkeypatch.setattr(ed, "reject_deleted_item", lambda: cut.append("rejected"))
        ui_graph.DELETE["render"](rig.panel, st, None, cable)
        assert cut == ["accepted"] and st["note"] == ""
        assert G.Wire("hands.layer", "output.2.hands") not in stub.wiring.wires
        assert G.Wire("plasma", "output.2.image") in stub.wiring.wires
        # deleted again: no such wire, said on the head
        ui_graph.DELETE["render"](rig.panel, st, None, cable)
        assert cut == ["accepted", "rejected"] and st["note"].endswith("no such wire")
        monkeypatch.undo()
        rig.panel.close()


def test_the_picker_adds_an_effect_instance_with_its_params(tmp_path):
    """The right-click picker lists every effect file, a hands node and a
    composite; an effect picked is the file itself while nothing holds it
    (R25: switched on), then the next instance (`EffectAt(file, n + 1)`)
    with its own `fx.<file>.<n+1>.*` params, at their defaults but `on`,
    on no wire; deleting the node drops it and its params; a hands node is
    the next instance; a composite is the first. Plan 35 G: every node of
    the section deletes — a window its wires, hands 1 with its layer's."""
    rig, stub, edit, pushed = _edit_rig(tmp_path)
    kinds = graphview.picker(edit)
    assert ("effect", "acid", "acid") in kinds
    assert ("hands", None, "hands") in kinds and ("composite", None, "composite") in kinds
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
    # … wired (a branch, not D1's `after`: the owner, 2026-10-24): deleting
    # it takes it, and its wire, out of the graph
    assert edit.wire("hands.layer", "palette.image") is None
    assert G.Wire("hands.layer", "palette.image") in rig.presets.graph.spec.wires
    assert edit.drop_node("palette") is None and edit.said == "palette deleted"
    assert G.Wire("hands.layer", "palette.image") not in rig.presets.graph.spec.wires
    assert stub.wiring.placed == ()
    assert edit.add_node("hands") is None and edit.added == "hands.2"
    assert edit.said == "Hands 2 added: wire it into scene.geometry, or add its layer"
    assert "ghost.2.alpha" in rig.reg
    assert edit.add_node("composite") is None
    assert rig.presets.graph.spec.composites() == (G.CompositeAt(1),)
    assert edit.wire("hands.layer", "composite.over") is None
    assert edit.wire("composite", "output.1.image") is None
    assert {G.Wire("hands.layer", "composite.over"),
            G.Wire("composite", "output.1.image")} <= set(stub.wiring.wires)
    g = G.build_graph(_views(S()), stub.wiring)
    comp = g.nodes["composite"]
    assert isinstance(comp, G.Composite) and comp.inputs["over"] is g.nodes["hands.layer"]
    assert g.nodes["output.1"].inputs["image"].inputs["image"] is comp
    assert edit.drop_node("composite") is None
    assert not [w for w in stub.wiring.wires if "composite" in (w.src, w.node)]
    assert edit.drop_node("output.1") is None
    assert edit.said == "nothing to delete: output 1 has no wires"   # (its wires went with the composite)
    assert edit.drop_node("hands") is None and edit.said == "Hands deleted"
    assert not [w for w in stub.wiring.wires if w.src in ("hands", "hands.layer")]
    assert len(pushed) == 12


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
    before = stub.wiring.wires
    edit = graphview.Edit(graph=r.presets.graph, push=lambda label: undo.push(label, load=True))
    assert edit.wire("hands.layer", "output.2.hands") is None
    settle(r)
    assert G.Wire("hands.layer", "output.2.hands") in stub.wiring.wires
    assert r.undo.undo() and r.undo.status.endswith("wire hands.layer → output.2.hands")
    assert stub.wiring.wires == before


def test_hands_as_lines_through_the_acid_with_tracers_by_wires_alone(ctx, tmp_path):
    """The wishlist's done-when: "hands as lines, through the acid, with
    tracers", made on the GRAPH page by wires alone (plan 35 G) — the hands
    wired into the scene, their guide (not their layer) over the outputs,
    acid on the look-back's picture, and the hands node drawn as lines from
    its menu (`set_node`) — reproduces the fixture `hands-lines.json` as a
    load wires it: the same wires, the same graph, the same picture."""
    import numpy as np
    from test_outputs import rig as gl_rig
    from test_outputs import run, views

    from hyperspace import graphmigrate as M
    rig, _, edit, _ = _edit_rig(tmp_path)
    put(rig.home, "Plain", graph={"nodes": []})
    rig.lib.load(PRESETS, "Plain")
    assert edit.wire("hands", "scene.geometry") is None
    assert edit.unwire("hands.layer", "output.all.hands") is None
    assert edit.unwire("hands.layer", "output.all.guide") is None
    assert edit.drop_node("hands.layer") is None
    assert edit.wire("hands.guide", "output.all.guide") is None
    assert edit.insert_effect(("lookback", "output.all.image"), "acid") is None
    assert edit.set_node("hands", draw="lines") is None
    doc, _ = M.migrate(_fixture("hands-lines"), {})
    want = G.read_graph(doc["graph"])
    got = rig.presets.graph.spec
    assert set(got.wires) == set(want.wires)
    assert got.wiring().draw == want.wiring().draw == "lines"
    vs = _views(S(), S(), S())
    assert repr(G.build_graph(vs, got.wiring(), effects=("acid",))) == repr(
        G.build_graph(vs, want.wiring(), effects=("acid",)))

    def picture(w):
        r = gl_rig(ctx, effects=("acid",), echoes=True)
        r.wiring = w
        return run(ctx, r, views(ctx, S(), S()), frames=3)

    a, b = picture(got.wiring()), picture(want.wiring())
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    plain = picture(G.Wiring())
    assert not np.array_equal(a[0], plain[0])                 # the lines, in the scene
def _wire_built(n) -> bool:
    """A node only a section's own wire builds: a composite the section
    added — instance 1 is plain `composite`, later ones `composite.<n>` —
    or an end of a picture that is no frame's (plan 35 T4: the frame's own
    through composites are numbered too, so a section's are told apart by
    what feeds their `over`: a section's here lays the hands geometry's
    layer directly, the frame's lay `hands.layer` the same way — see the
    test below)."""
    return isinstance(n, G.Composite) and (
        n.name == "composite" or n.name.startswith("composite."))


def test_the_wire_built_check_sees_a_wired_composite():
    """The check is not vacuous: a section adding composite 1 (named plain
    `composite`) and composite 2 trips it."""
    section = {"nodes": [{"kind": "composite"}, {"kind": "composite", "instance": 2}],
               "wires": _wires(("hands", "composite.over"), ("composite", "output.1.image"),
                               ("hands", "composite.2.over"), ("composite.2", "output.2.image"))}
    spec = G.read_graph(section, effects=FILES)
    assert spec.notes == ()
    g = G.build_graph(_views(S(), S()), spec.wiring(), effects=RUN)
    built = sorted(n.name for n in g.nodes.values() if _wire_built(n))
    assert "composite" in built and "composite.2" in built
    plain = G.build_graph(_views(S(), S()), effects=RUN)
    assert not any(_wire_built(n) for n in plain.nodes.values())


def test_no_factory_preset_changes():
    """No library file carries a graph (so no wire): every factory preset
    loads with the factory frame — which holds nothing a section's wire
    builds: nothing dormant, every output's picture an end (`Shown`) or
    the ground, a through output's its own copies."""
    for path in sorted(FACTORY.rglob("*.json")):
        doc = json.loads(path.read_text())
        assert not isinstance(doc, dict) or "graph" not in doc, path
    for sw in ((Shows(),), (Shows(), Shows(through=True)),
               (Shows(scene=False), Shows(), Shows(through=True)),
               (Shows(scene=False, through=True), Shows(scene=False))):
        g = graph(sw, G.Wiring(run=RUN), effects=RUN)
        assert all(n.placed in (None, "wire") for n in g.nodes.values()
                   if isinstance(n, G.Effect))
        assert all(isinstance(n, G.Copy) for n in g.nodes.values()
                   if isinstance(n, G.Effect) and n.placed == "wire")
        assert g.dormant == {} and g.notes == []
        for out in g.outputs:
            img = out.inputs["image"]
            assert img is None or isinstance(img, G.Shown)


def test_the_fixtures_load_clean_through_a_scratch_library(tmp_path):
    """Each N4 fixture loaded like a user's preset: no note, a clean dot,
    the renderer handed its wires, the save the frame the load landed
    (row 394)."""
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
        assert doc["graph"]
        assert rig.presets.document(slug)[preset.GRAPH_KEY] == rig.presets.graph.free_doc()
    assert _old(stub.wiring).wires == (G.Wire("history", "acid.2.image"),
                                 G.Wire("acid.2", "output.2.image"))
    assert _old(stub.wiring).placed == (G.EffectAt("palette", 1, into="output.1"),)
    assert rig.reg["fx.acid.2.on"].value is True


def test_the_words_say_the_wires():
    """OUTPUT's "shows:" line and LOOKBACK's history line say the wires."""
    from hyperspace.ui import output_shows

    spec = G.read_graph(_fixture("wired-outputs")["graph"])
    w = spec.wiring()
    assert G.graph_words(spec) == ("graph: acid ×2 · palette on output 1 only · acid 2 reads "
                                   "the history · output 2 shows acid 2")
    assert output_shows(S(), True, True, 1.0, w, n=2)[0] == "acid 2 by a wire"
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
    assert G.lookback_words(G.read_graph({"wires": _wires(("hands", "history.image"))}).wiring()
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
    assert r.stats["chain_runs"] == 1 and r.stats["routes"][1] == ("shown(lookback)", False)
    assert r.stats["routes"][0] == ("shown(warp)", False)


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
    assert r._graph.nodes["output.2"].inputs["hands"] is r._graph.nodes["hands.2.layer"]
    differ = (a != b).any(axis=2)
    assert differ.any()
    assert r.stats["routes"] == [("shown(lookback)", False), ("shown(lookback)", True)]
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
    assert edit.wire("rout:hands.layer", "rin:output.2/hands") is None      # (plan 35 V2)
    run(ctx, r, views(ctx, S(), S()), frames=1)
    assert r._graph is not first and G.Wire("hands.layer", "output.2.hands") in r.wiring.wires
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
    # (plan 35 T4: output 2's state — the scene and its hands off, the wire
    # into its hands kept — is its wiring; a mute would ignore the wire)
    r.wiring = wiring(spec, Shows(), Shows(scene=False, hands=False))
    a, b = run(ctx, r, views(ctx, S(), S()), frames=2)
    comp = r._graph.nodes["composite"]
    assert r._graph.nodes["output.2"].inputs["hands"] is comp
    assert r.stats["routes"][1] == (None, True)
    # the scene with the hands, laid opaque onto the ground: output 1's picture
    assert b.any() and np.abs(a - b).max() <= 2
    # a presenter gets the composite's picture, not hands 1's layer
    pv = View(S(), (W, H), presenter=object())
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
    r.wiring = wired(r, section)                     # (plan 33 R23: warp's run with it)
    vs = views(ctx, *wire_switches(r, S(), Thru(), Thru(scene=False)))
    g = G.build_graph(_views(S(), S(), S()), r.wiring, effects=("warp",))
    o2, o3 = g.nodes["output.2"], g.nodes["output.3"]
    assert (o2.inputs["image"] is g.nodes["shown(warp)"]
            and o2.inputs["hands"] is g.nodes["hands.layer"])
    assert o3.inputs["image"] is None and o3.inputs["hands"] is g.nodes["hands.layer"]
    a, b, _ = run(ctx, r, vs, frames=2)
    assert np.array_equal(a, b)                    # the scene, the hands over: once
    assert r.stats["routes"][1:] == [("shown(warp)", True), (None, True)]
    assert r.stats["chain_runs"] == 1              # no copy runs


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
    assert edit.wire("channel.a", "blend.aux") is None              # (plan 35 V2)
    spec = rig.presets.graph.spec
    assert spec.effects == (G.EffectAt("blend", 1, after="hands.layer"),)
    assert stub.wiring.placed == (G.EffectAt("blend", 1, after="hands.layer"),)
    assert G.Wire("channel.a", "blend.aux") in stub.wiring.wires
    assert edit.wire("scene", "blend.image") is None
    assert stub.wiring.placed == ()
    assert "blend" in graphview.unreached(rig.presets.graph.spec)
