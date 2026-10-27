"""Plan 36 T1 (W1, decision D1): outputs show only their own wires; All
outputs is a drawn bus.

A window's port takes its own wire, else All outputs' by the rig's bus
cable `output.all.<port> → output.<n>.<port>` (`graph.window_ports`) —
nothing else reaches it. The bus cables are the open show's
(`library.Project.rig`, `graph.RigWires`): present by default, drawn on
GRAPH as ordinary render cables, cut and joined there, saved in the show's
file. A drag changes the one wire it lands (`render_wire`): no placement,
guide or other wire moves with it. The install's repro is the first test:
wiring the scene into `output.1.image` on the factory `party-trip` changes
that one port and nothing else."""

from __future__ import annotations

import json

from test_plan31_wiring import make_app

from hyperspace import graph as G
from hyperspace import graphview
from hyperspace.library import Project
from hyperspace.outputs import Switches, View
from hyperspace.params import Registry
from hyperspace.routing import Bindings

SIZE = (240, 150)


def _views(n: int = 2) -> list[View]:
    return [View(Switches(), SIZE) for _ in range(n)]


def _party(tmp_path):
    """The headless app on the factory `party-trip`, and a GRAPH edit on it
    holding the open show (its rig wires), its undo steps counted."""
    app = make_app(tmp_path)
    app.lib.load("presets", "party-trip")
    pushed: list[str] = []
    e = graphview.Edit(graph=app.presets.graph, push=pushed.append)
    e.show = app.lib.project
    return app, e, pushed


def _build(app, n: int = 2):
    """(the render graph the renderer would build, the canvas over it)."""
    spec = app.presets.graph.spec
    g = G.build_graph(_views(n), spec.wiring(), (), tuple(sorted(app.presets.graph.fx.specs))
                      if app.presets.graph.fx is not None else (), G.rig_of(app.lib.project))
    return g, graphview.build(Bindings(), Registry(), None, None, g, spec)


def _into(view, node: str, port: str) -> list[graphview.VCable]:
    return [c for c in view.cables if c.kind == "render" and c.dst_port == f"rin:{node}/{port}"]


def _ports(g, n: int) -> dict[str, str | None]:
    out = g.outputs[n - 1]
    return {p: (v.name if v is not None else None)
            for p, v in (("image", out.inputs["image"]), ("hands", out.inputs["hands"]),
                         ("guide", out.inputs["readout"]))}


# ---------------------------------------------------------------- the install's repro

def test_rewiring_output_1_changes_that_one_port_and_nothing_else(tmp_path):
    """The install's bug: on `party-trip`, wiring the scene into
    `output.1.image` changes that one port. The section's other wires,
    every other port's input and output 2 are as they were, and output 1's
    hands and guide are exactly the drawn bus cables — what the canvas
    draws into each of output 1's ports is one cable, and it is what the
    render graph reads."""
    app, e, pushed = _party(tmp_path)
    spec = app.presets.graph.spec
    before = list(spec.wires)
    into_before = {w.dst: w.src for w in before}
    g0, _ = _build(app)
    out2 = G.signature(g0)[1]
    assert e.wire("scene", "output.1.image") is None and pushed == [
        "wire scene → output.1.image"]
    after = list(app.presets.graph.spec.wires)
    assert set(after) - set(before) == {G.Wire("scene", "output.1.image")}
    assert set(before) <= set(after)
    into_after = {w.dst: w.src for w in after}
    assert {d: s for d, s in into_after.items() if d != "output.1.image"} == into_before
    assert app.presets.graph.spec.effects == spec.effects        # no placement moved
    assert app.lib.project.rig == G.RigWires()                   # no rig cable moved
    g, view = _build(app)
    assert G.signature(g)[1] == out2                             # output 2: as it was
    # output 1's ports: its own picture; its hands and guide by the bus,
    # each one drawn cable, and the render graph reads exactly those
    image, = _into(view, "output.1", "image")
    assert image.ref == G.Wire("scene", "output.1.image")
    for port in ("hands", "guide"):
        cable, = _into(view, "output.1", port)
        assert cable.ref == G.bus_wire(1, port) and G.is_bus(cable.ref)
        assert cable.src_port == f"rout:output.all.{port}"
    assert _ports(g, 1)["image"] == "shown(scene)"
    assert _ports(g, 1)["hands"] == _ports(g, 2)["hands"] == "hands.layer"
    assert _ports(g, 1)["guide"] == _ports(g, 2)["guide"]
    # every window port has exactly one cable into it, always drawn
    for n in (1, 2):
        for port in G.BUS_PORTS:
            assert len(_into(view, f"output.{n}", port)) == 1, (n, port)


# ---------------------------------------------------------------- the show's bus cables

def test_cutting_a_bus_cable_persists_in_the_show_and_empties_the_port(tmp_path):
    """Delete on a bus cable cuts it in the open show — one undo step, the
    preset untouched, the show dirty: window 1 shows nothing on its hands
    port (no cable drawn there, nothing read) while window 2 keeps its
    own. The cut is saved in the show's file (`rig`) and read back; a drag
    from All outputs' pin joins it again."""
    app, e, pushed = _party(tmp_path)
    show = app.lib.project
    section = app.presets.graph.spec.to_json()
    _, view = _build(app)
    cable, = _into(view, "output.1", "hands")
    assert e.unwire(cable) is None and pushed == ["cut output.all.hands → output.1.hands"]
    assert show.rig.cut == {G.bus_wire(1, "hands")} and show.is_dirty()
    assert app.presets.graph.spec.to_json() == section
    g, view = _build(app)
    assert _ports(g, 1)["hands"] is None and _ports(g, 2)["hands"] == "hands.layer"
    assert _into(view, "output.1", "hands") == []
    assert G.output_ports(app.presets.graph.wiring, 1, show.rig)["hands"] is None
    # (a second cut of it is the one refusal)
    assert e.unwire(cable) == graphview.NO_SUCH_WIRE.format(wire=str(G.bus_wire(1, "hands")))
    # in the show's file, and back
    path = show.save("bus test")
    doc = json.loads(path.read_text())
    assert doc["rig"] == {"cut": [{"from": "output.all.hands", "to": "output.1.hands"}]}
    assert not show.is_dirty()
    other = Project(app.lib)
    other._take(doc, path, path.name)
    assert other.rig == show.rig
    # an undo mark holds it; joined again by a drag from the bus's pin
    mark = show.mark()
    assert e.wire("rout:output.all.hands", "rin:output.1/hands") is None
    assert show.rig == G.RigWires() and show.is_dirty()
    show.remark(mark)
    assert show.rig.cut == {G.bus_wire(1, "hands")}
    # a port's name alone: whatever is wired into it — here the bus cable
    assert e.unwire("output.2.guide") is None
    assert show.rig.cut == {G.bus_wire(1, "hands"), G.bus_wire(2, "guide")}


def test_a_show_with_every_cable_standing_writes_no_rig():
    """The rig as it ships writes nothing (a factory show's file is as it
    was); a hand-edited `rig` that is not wires is left out, never an error."""
    assert G.RigWires().to_json() == {}
    rig = G.RigWires().cutting(G.bus_wire(2, "image")).cutting(G.bus_wire(1, "guide"))
    assert rig.to_json() == {"cut": [{"from": "output.all.guide", "to": "output.1.guide"},
                                     {"from": "output.all.image", "to": "output.2.image"}]}
    assert G.RigWires.read(rig.to_json()) == rig
    assert G.RigWires.read({"cut": [{"from": "x"}, 3, {"from": "a", "to": "b"},
                                    {"from": "a", "to": "b.c"}]}).cut == {G.Wire("a", "b.c")}
    assert G.RigWires.read(None) == G.RigWires.read([]) == G.RigWires()


def test_a_window_port_is_its_own_wire_else_the_bus_cable_else_nothing():
    """`window_ports`, the one rule: a preset's wire into the port takes it
    (the bus cable is then not read); with none, All outputs' wire into the
    same port while the bus cable stands; cut, nothing — no other fallback."""
    wires = [G.Wire("lookback", "output.all.image"), G.Wire("hands.layer", "output.all.hands"),
             G.Wire("scene", "output.1.image")]
    # (plan 36 T2: and the depth the hands are laid against, the fourth port)
    assert G.window_ports(wires, 1) == {"image": wires[2], "hands": wires[1], "guide": None,
                                        "depth": None}
    assert G.window_ports(wires, 2) == {"image": wires[0], "hands": wires[1], "guide": None,
                                        "depth": None}
    cut = G.RigWires().cutting(G.bus_wire(2, "image")).cutting(G.bus_wire(1, "image"))
    assert G.window_ports(wires, 2, cut)["image"] is None
    assert G.window_ports(wires, 1, cut)["image"] == wires[2]   # its own wire stands
    assert G.is_bus(G.bus_wire(3, "guide"))
    assert not G.is_bus(G.Wire("output.all.image", "output.1.hands"))
    assert not G.is_bus(G.Wire("lookback", "output.1.image"))


def test_a_drag_from_the_bus_takes_the_port_and_only_into_the_same_port(tmp_path):
    """A drag from All outputs' bus pin onto a window's same port is the
    rig's cable: the preset's own wire into that port gives it up (one
    wire into a port), in one step. Into another port, or with no show to
    hold it, refused in words; an effect does not go onto a bus cable."""
    app, e, pushed = _party(tmp_path)
    assert e.wire("scene", "output.2.image") is None
    assert e.wire("rout:output.all.image", "rin:output.2/image") is None
    assert G.Wire("scene", "output.2.image") not in app.presets.graph.spec.wires
    assert len(pushed) == 2
    _, view = _build(app)
    cable, = _into(view, "output.2", "image")
    assert cable.ref == G.bus_wire(2, "image")
    assert e.wire("rout:output.all.image", "rin:output.2/hands") == \
        graphview.BUS_SAME_PORT.format(port="image")
    assert e.insert_effect(cable, "acid") == graphview.BUS_NO_EFFECT.format(
        wire="output.all.image → output.2.image")
    alone = graphview.Edit(graph=app.presets.graph, push=pushed.append)
    assert alone.wire("rout:output.all.image", "rin:output.2/image") == graphview.BUS_NO_SHOW


def test_deleting_a_window_takes_its_bus_cables_too(tmp_path):
    """A window is the rig's: deleting its node takes every wire drawn into
    it — the preset's and the bus cables — in one step, so it shows its
    ground as the words say; "as All outputs" on OUTPUT joins its picture's
    cable again."""
    app, e, pushed = _party(tmp_path)
    assert e.drop_node("render:output.2") is None
    assert e.said == graphview.OUTPUT_UNWIRED.format(label="Output 2") and len(pushed) == 1
    assert app.lib.project.rig.cut == {G.bus_wire(2, p) for p in G.BUS_PORTS}
    g, view = _build(app)
    assert _ports(g, 2) == {"image": None, "hands": None, "guide": None}
    assert not [c for c in view.cables if c.dst_port.startswith("rin:output.2/")]
    assert graphview.picture_now(app.presets.graph.spec, "output.2.image",
                                 app.lib.project.rig) == graphview.NOTHING
    assert graphview.set_picture(e, "output.2.image", graphview.AS_ALL) is None
    assert app.lib.project.rig.cut == {G.bus_wire(2, p) for p in ("hands", "guide", "depth")}
    assert _ports(_build(app)[0], 2)["image"] == _ports(g, 1)["image"]
    assert e.drop_node("render:output.2") is None
    assert e.drop_node("render:output.2") is None
    assert e.said == graphview.NOTHING_TO_DELETE.format(what="output 2")


def test_an_undo_puts_a_cut_bus_cable_back(tmp_path):
    """A cut is one undo step of the app's (`undo.push(…, load=True)`, the
    show's mark): undone, the cable stands again and the show is as it was."""
    from test_graph_edit import free_rig
    from test_undo import settle

    rig, e, _ = free_rig(tmp_path, ("lookback", "output.all.image"), undo_rig=True)
    e.show = rig.lib.project
    assert e.unwire("rout:output.all.image", "rin:output.1/image") is None
    assert rig.lib.project.rig.cut == {G.bus_wire(1, "image")}
    settle(rig)
    assert len(rig.undo.stack) == 1 and rig.undo.undo()
    assert rig.lib.project.rig == G.RigWires()


def test_a_cut_cable_draws_what_a_ground_wire_draws_and_rebuilds():
    """On the golden rig (two synthetic hands): the renderer reads the show's
    rig wires (`rig_source`) — cutting window 2's hands and guide cables
    builds a new graph, and window 2 draws pixel for pixel what window 3,
    wired `ground` into those ports, draws; with every cable standing the
    two differ (the layer is laid over). Skips without a standalone GL
    context."""
    from types import SimpleNamespace

    import numpy as np
    import pytest
    from test_graph_frame import _draw, _land, _tool, the_frame, wires_of

    try:
        import moderngl

        ctx = moderngl.create_context(standalone=True)
    except Exception as err:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {err}")
    rig = _tool().Rig("legacy6", "present", ctx)
    try:
        sec = the_frame({})
        sec["wires"] += wires_of([("ground", "output.3.hands"), ("ground", "output.3.guide")])
        _land(rig, sec)
        show = SimpleNamespace(rig=G.RigWires())
        rig.renderer.rig_source = show
        _, standing, grounded = _draw(ctx, rig, [Switches()] * 3)
        first = rig.renderer._graph
        assert rig.renderer.stats["layer"] and not np.array_equal(standing, grounded)
        show.rig = show.rig.cutting(G.bus_wire(2, "hands")).cutting(G.bus_wire(2, "guide"))
        _, cut, grounded = _draw(ctx, rig, [Switches()] * 3)
        assert rig.renderer._graph is not first and rig.renderer._graph.rig == show.rig
        assert np.array_equal(cut, grounded)
    finally:
        rig.close()


def test_deleting_a_window_cuts_only_the_bus_cables_drawn(tmp_path):
    """Review M2: a bus cable into a port the preset wires itself is not
    drawn, so deleting the window does not cut it — the preset's wire goes,
    and that cable stands (the port reads All outputs' again by it)."""
    app, e, _ = _party(tmp_path)
    assert e.wire("scene", "output.2.hands") is None
    assert e.drop_node("render:output.2") is None
    assert app.lib.project.rig.cut == {G.bus_wire(2, p) for p in ("image", "guide", "depth")}
    assert _ports(_build(app)[0], 2)["hands"] == "hands.layer"


def test_through_refuses_a_window_with_no_picture_or_its_own_hands(tmp_path):
    """Review M3: with its picture cable cut a window shows no picture to put
    the hands through; with a hands wire of the preset's own, through would
    drop it — both refused in words, nothing changed (the toggle is
    lossless: off puts back exactly what on took)."""
    app, e, _ = _party(tmp_path)
    assert e.unwire("output.2.image") is None                    # the bus cable cut
    before = app.presets.graph.spec.to_json()
    assert graphview.set_through(e, 2, True) == graphview.THROUGH_NO_PICTURE.format(
        label="Output 2")
    assert graphview.set_picture(e, "output.2.image", graphview.AS_ALL) is None
    assert e.wire("ground", "output.2.hands") is None
    assert graphview.set_through(e, 2, True) == graphview.THROUGH_OWN_HANDS.format(
        label="Output 2", src="ground", n=2)
    assert e.unwire("ground", "output.2.hands") is None
    assert app.presets.graph.spec.to_json() == before
    assert graphview.set_through(e, 2, True) is None
    assert graphview.set_through(e, 2, False) is None
    assert app.presets.graph.spec.to_json() == before


def test_through_writes_only_the_wires_it_names(tmp_path):
    """OUTPUT's "hands through the effects" (plan 36 T1, no `_Wiring._put`
    rule): on, the chain into the window's picture and `ground` on its
    hands — its guide untouched, still the bus cable; off, exactly those
    back out."""
    app, e, _ = _party(tmp_path)
    before = app.presets.graph.spec.to_json()
    assert graphview.set_through(e, 1, True) is None
    spec = app.presets.graph.spec
    own = {w.port: w.src for w in spec.wires if w.node == "output.1"}
    assert set(own) == {"image", "hands"} and own["hands"] == G.GROUND
    assert graphview.is_through(spec, 1, app.lib.project.rig)
    _, view = _build(app)
    guide, = _into(view, "output.1", "guide")
    assert guide.ref == G.bus_wire(1, "guide")
    assert graphview.set_through(e, 1, False) is None
    assert app.presets.graph.spec.to_json() == before
