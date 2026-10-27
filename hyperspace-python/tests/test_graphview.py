"""The GRAPH page (plan 28 N2): the model (graphview.py) and the page
(ui_graph.py), headless.

The model is built from the shell's rig (tests/test_ui_shell.py: the full
registry, the factory table, a scratch library on tmp_path) with factory
presets loaded through it, a render graph built by `graph.default_graph`
(or by hand, for an effect placed off the default chain) and a device
registry of fakes. The page is drawn under the same headless imgui
context the other pages are, with the node editor's own context on it:
`imgui_node_editor` runs headless (it lays out and answers its queries
without a renderer), so the page is drawn for real, not stubbed."""

import ast
import importlib
from pathlib import Path

import pytest
from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture
from wiredframe import Shows
from wiredframe import wiring as wired_for

from hyperspace import devices, graphview, ui_graph, ui_routing
from hyperspace import graph as G
from hyperspace.devices import Port
from hyperspace.graphmigrate import wired_wiring
from hyperspace.outputs import Switches, View
from hyperspace.routing import MOD_OPS
from hyperspace.ui import PAGES

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def _every_file(rig) -> None:
    """Every effect file's params, as before a graph landed (plan 36 T3:
    `FxState.hold(None)`) — a canvas these tests build from a render graph
    no preset's section says."""
    from hyperspace.fx import declare

    st = rig.reg.fx_state
    declare(rig.reg, st, st.hold(None))


def build(rig, render_graph=None, devs=None):
    return graphview.build(rig.router.table, rig.reg, rig.router, devs, render_graph, None)


def views(*sw):
    return [View(s, (640, 360)) for s in sw]


def thru(w, effects, *shows, look: str = "off") -> G.Graph:
    """Plan 35 T4: the frame `w` draws on one window per state of `shows`
    (the retired switches as each output's wiring, `tests/wiredframe.py`:
    `Shows(through=True)` where `Switches(through=True)` was); plan 36 T4:
    its look-back as `look` says the old words had it."""
    return G.build_graph(views(*(Switches() for _ in shows)),
                         wired_wiring(wired_for(w, *shows, look=look)), effects=effects)


def stacked(effects, wiring=None) -> G.Wiring:
    """`wiring` (None: the default) with `effects` its run — those no wire
    or placement of it takes, in the order given: what the order-built
    stack ran for a wiring that said no run, and what a load lands for an
    old preset with them on (plan 33 R23: a graph fixture says its run)."""
    from dataclasses import replace

    wiring = wiring if wiring is not None else G.Wiring()
    if wiring.run is not None:
        return wiring
    taken = {e.name for e in wiring.placed}
    taken |= {n for w in wiring.wires if not G.is_aux(w) for n in (w.src, w.node)
              if G.wire_node_kind(n) == "effect"}
    return replace(wiring, run=tuple(e for e in effects if e not in taken))


def owner_of(view, pid):
    hit = view.owner(f"mod:{pid}")
    return None if hit is None else hit[0].id


# ---------------------------------------------------------------- the model

def test_every_route_is_one_cable_and_every_cable_one_route(rig):
    """Today's routes convert one-to-one (decision 13): every performer
    row of a loaded preset — enabled or not — is exactly one `route`
    cable whose `ref` is that row, into its target's `mod` stub, and no
    route cable stands for anything else."""
    for name in ("party-trip", "lfo-breathe", "hands-fx", "legacy6"):
        rig.lib.load("presets", name)
        rows = rig.router.table.routes()
        rows[-1].enabled = False                        # a dormant row is a cable too
        view = build(rig)
        cables = [c for c in view.cables if c.kind == "route"]
        assert len(cables) == len(rows), name
        assert [c.ref for c in cables] == rows          # the same objects, table order
        for c in cables:
            b = c.ref
            assert b.op in MOD_OPS
            assert c.dst_port == f"mod:{b.target}"
            src = view.owner(c.src_port)
            assert src is not None and src[1].direction == graphview.OUT
        assert cables[-1].off and cables[-1].dormant    # the switched-off row
        # the desk / pad / key rows are setter cables into `base`, never routes
        setters = [c for c in view.cables if c.kind == "setter"]
        assert setters and all(c.dst_port.startswith("base:") for c in setters)
        assert all(c.ref.op not in MOD_OPS for c in setters)


def test_macro_subs_are_cables_into_base_or_depth(rig):
    """A macro is a bus node: its knob in, one output, and each subscriber
    one cable from that output — a base subscriber into the param's `base`
    stub, a depth subscriber into the `depth` stub of the param its route
    lands on (lfo-breathe has both)."""
    rig.lib.load("presets", "lfo-breathe")
    table = rig.router.table
    view = build(rig)
    subs = [c for c in view.cables if c.kind == "sub"]
    want = [(mid, s) for mid, m in sorted(table.macros.items()) for s in m.subs]
    assert len(want) == 3 and {id(c.ref[1]) for c in subs} == {id(s) for _, s in want}
    for c in subs:
        mid, s = c.ref
        assert c.src_port == f"bus:{mid}"
        assert view.node(mid).kind == "macro"
        if s.depth is None:
            assert c.dst_port == f"base:{s.base}"
        else:
            assert c.dst_port == f"depth:{s.depth[1]}"
            assert not c.off                       # its route is there
            port = view.owner(c.dst_port)[1]
            assert c.dst_port in port.pins and f"mod:{s.depth[1]}" in port.pins
    # a depth subscriber naming a route the table lacks is drawn, off
    from hyperspace.routing import Sub
    orphan = Sub(depth=("lane:5", "view.speed"))
    table.macros["macro.1"].subs.append(orphan)
    table.macros_serial += 1
    view = build(rig)
    c = next(c for c in view.cables if c.kind == "sub" and c.ref[1] is orphan)
    assert c.off and c.dormant and c.dst_port == "depth:view.speed"


def test_params_group_under_the_render_node_that_owns_them(rig):
    """The one table (`graphview.OWNERS`): the shape's params on `shape`,
    an effect's on its node, the look-back's (`dream.*`) on `lookback`, the
    camera's on `camera`, an output's on its output node, the hands'
    (`ghost.*`) on their hands node — plan 35 V2: the nodes in the new ids,
    the params in theirs; an LFO's knobs on that LFO; a group no render
    node owns on a node of its own."""
    from hyperspace.routing import Binding
    out1 = next(p.id for p in rig.reg if p.id.startswith("output.1."))
    rig.router.table.bindings.append(Binding("key:F9", out1, "toggle"))   # a setter onto it
    g = thru(stacked(("acid", "palette")), ("acid", "palette"), Shows(),
             Shows(scene=False, through=True), look="trail")
    _every_file(rig)
    view = build(rig, g)
    names = {n.id for n in view.nodes}
    # (plan 35 T4: output 2's hands through are a copy of each effect over a
    # composite, `copy` …; plan 35 G: no end nor `fx` is drawn — none is a node)
    assert {"render:shape", "render:acid", "render:copy", "render:lookback",
            "render:output.1", "render:output.2", "render:output.all",
            "render:camera"} <= names
    assert not {n for n in names if n.startswith(("render:shown", "render:history"))}
    assert owner_of(view, "view.bright") == "render:shape"
    rot = next(p.id for p in rig.reg if p.group == "rot" and p.modulatable)
    assert owner_of(view, rot) == "render:shape"
    assert owner_of(view, "fx.acid.mix") == "render:acid"
    assert owner_of(view, "fx.palette.mix") == "render:palette"
    assert owner_of(view, "fx.mix") == "group:fx"            # (no pipeline end to own it)
    assert owner_of(view, "dream.mix") == "render:lookback"
    assert owner_of(view, "camera.zoom") == "render:camera"
    assert owner_of(view, "ghost.alpha") == "render:hands"
    assert owner_of(view, out1) == "render:output.1"
    assert owner_of(view, "lfo.1.depth") == "lfo.1"
    assert owner_of(view, "tempo.bpm") == "group:tempo"
    assert owner_of(view, "master.gain") == "group:master"
    # no render graph: the same params fall to their groups' nodes
    bare = build(rig)
    assert owner_of(bare, "view.bright") == "group:view"
    assert owner_of(bare, "camera.zoom") == "render:camera"
    # every param port has a base and a mod stub
    port = view.owner("mod:view.bright")[1]
    assert port.pins[:2] == ("base:view.bright", "mod:view.bright")
    # where each node's position lives
    assert graphview.home(view.node("render:shape")) == graphview.PRESET
    assert graphview.home(view.node("render:output.1")) == graphview.SESSION
    # plan 31 G1: an LFO is the preset's (a bank's membership is preset content)
    assert graphview.home(view.node("lfo.1")) == graphview.PRESET
    assert graphview.home(view.node(graphview.ANALYZER)) == graphview.SESSION
    assert graphview.home(view.node("group:tempo")) == graphview.SESSION


class FakeDevice(devices.Base):
    def __init__(self, role, kind, schemes, ports, *, connected=True):
        super().__init__(role, io=object() if connected else None)
        self.kind = kind
        self.schemes = self.feeds = schemes
        self._ports = ports

    @property
    def sources(self):
        return self._ports if self.io is not None else ()


def test_device_nodes_come_from_the_registry_with_their_port_groups(rig):
    """One node per listed device, by role, its ports its `Device.sources`
    in their port groups; a lost device is grey with no ports of its own,
    and the rows that name it draw from a port added for them, dormant."""
    hands = FakeDevice("leap", "hands", ("hand", "hands"), (
        Port("right.y", "right y", group="axes", scheme="hand"),
        Port("right.roll", "right roll", group="axes", scheme="hand"),
        Port("right.pinch.index", "right pinch", group="switches", scheme="hand"),
        Port("right.energy", "right energy", group="dance", scheme="hand"),
    ))
    pad = FakeDevice("pad", "gamepad", ("axis",), (), connected=False)
    reg = devices.DeviceRegistry(devices=[hands, pad])
    rig.lib.load("presets", "hands-fx")
    rig.router.table.add(rig.router.table.routes()[0].__class__(
        "axis:LX", "camera.zoom", "push", 0.3))
    view = build(rig, devs=reg)
    leap, gp = view.node("device:leap"), view.node("device:pad")
    assert leap.kind == gp.kind == "device" and not leap.grey and gp.grey
    # plan 28 N5: the hands' `switches` drawn as the design's pinches (and grab)
    assert [p.group for p in leap.ports[:4]] == ["axes", "axes", "pinches", "dance"]
    assert leap.ports[0].pins == ("out:hand:right.y",)
    # a hand route whose address the device names draws from that port
    hand_routes = [c for c in view.cables if c.kind == "route" and c.addr.startswith("hand:")]
    assert hand_routes and all(view.owner(c.src_port)[0] is leap for c in hand_routes)
    # the lost pad's row: a port added on its node, the cable dormant
    lx = next(c for c in view.cables if c.addr == "axis:LX")
    assert view.owner(lx.src_port)[0] is gp and lx.dormant
    # a scheme no device publishes (the keys): a grey source node
    keys = view.node("source:key")
    assert keys is not None and keys.grey and keys.kind == "source"


def test_the_render_graphs_edges_are_image_cables_including_a_placed_effect():
    """Plan 35 G: every wire of the wired frame is one `render` cable of its
    port's type, its `ref` the wire — geometry into the scene, a picture
    along the chain — and an effect on the hands' layer before an output
    (as plan 30's placements were) is a node like any other, its cables
    picture cables. Nothing the render graph makes for itself (an end, the
    cover, the capture) is drawn: none is a node of the section."""
    from hyperspace.params import Registry
    from hyperspace.routing import Bindings
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "effect", "file": "acid",
                                                      "instance": 2}],
                         "wires": [{"from": "shape", "to": "scene.geometry"},
                                   {"from": "hands", "to": "scene.geometry"},
                                   {"from": "scene", "to": "lookback.image"},
                                   {"from": "lookback", "to": "output.all.image"},
                                   {"from": "hands.layer", "to": "acid.2.image"},
                                   {"from": "acid.2", "to": "output.1.hands"}]})
    assert not spec.notes
    g = G.build_graph(views(Switches()), wired_wiring(spec.wiring()), effects=("acid.2",))
    view = graphview.build(Bindings(), Registry(), None, None, g, spec)
    wires = [c for c in view.cables if c.kind == "render" and not G.is_bus(c.ref)]
    assert [c.ref for c in wires] == list(spec.wires)
    # plan 36 T1: and the rig's bus cables into the ports the section
    # leaves to All outputs (its own wire takes output.1.hands)
    assert [c.ref for c in view.cables if c.kind == "render" and G.is_bus(c.ref)] == [
        G.bus_wire(1, "image"), G.bus_wire(1, "guide"), G.bus_wire(1, "depth")]
    by = {(c.ref.src, c.ref.node): c for c in wires}
    assert by[("shape", "scene")].type == by[("hands", "scene")].type == graphview.GEOMETRY
    assert by[("hands.layer", "acid.2")].type == graphview.IMAGE
    assert by[("acid.2", "output.1")].type == graphview.IMAGE
    c = by[("acid.2", "output.1")]
    assert c.src_port == "rout:acid.2" and c.dst_port == "rin:output.1/hands"
    assert not [n.id for n in view.nodes if "(" in n.id or n.id == "render:shown"]
    assert view.node("render:acid.2").kind == "render"
    assert view.node("render:output.1").kind == "output"
    # plan 32 T7: every port wired but the effect's aux, open until a wire
    # puts a second picture on it
    ports = {p.id: p for p in view.node("render:acid.2").ports}
    assert not ports.pop("rin:acid.2/aux").patched
    assert all(p.patched for p in ports.values())


def test_old_layout_positions_follow_the_renamed_ids(rig):
    """R14: positions saved on the canvas before plan 35 (`render:eye`,
    `render:history`, `render:media.a`, `render:ghost`, `render:hands` the
    layer …) are read under the wired frame's ids (`graphmigrate.
    renamed_layout`), in the preset's layout and in the show's, so the
    owner's arrangement stays; a layout already in the new ids is as it is."""
    import json

    from hyperspace import graphmigrate as M
    from hyperspace.preset import LAYOUT_KEY
    old = {"render:eye": [1, 2], "render:history": [3, 4], "render:media.a": [5, 6],
           "render:ghost": [7, 8], "render:hands": [9, 10], "render:readout.2": [11, 12],
           "render:acid.2": [13, 14], "lfo.1": [15, 16]}
    new = {"render:camera": [1, 2], "render:lookback": [3, 4], "render:channel.a": [5, 6],
           "render:hands": [7, 8], "render:hands.layer": [9, 10],
           "render:hands.2.guide": [11, 12], "render:acid.2": [13, 14], "lfo.1": [15, 16]}
    assert M.renamed_layout(old) == new
    assert M.renamed_layout(new) == new           # (new ids: untouched — `render:hands` too)
    lib, presets, project = rig.lib, rig.lib.presets, rig.lib.project
    lib.load("presets", "party-trip")
    doc = presets.document("party-trip")
    doc[LAYOUT_KEY] = old
    presets.load_doc(doc)
    assert presets.layout == new
    project.save("old-show")
    raw = json.loads(project.path.read_text())
    raw["layout"] = {"render:eye": [40, 50], "render:output.1": [60, 70]}
    project.path.write_text(json.dumps(raw))
    project.load("old-show")
    assert project.layout == {"render:camera": [40, 50], "render:output.1": [60, 70]}


def test_layout_round_trips_through_the_preset_and_the_show(rig):
    """The look's nodes' positions are the preset's ``layout``, the rig's
    the show's: written on save, read on load. A preset without the key
    (every factory preset) loads with no note and no dirt; one with a bad
    entry keeps the good ones and says so."""
    from hyperspace.preset import LAYOUT_KEY
    lib, presets, project = rig.lib, rig.lib.presets, rig.lib.project
    lib.load("presets", "party-trip")
    # (plan 36 T3: the factory `/7` holds the envelopes' and the sequencer's
    # values, which this rig — the panel's, built without them — lacks)
    said = [n for n in presets.notes if not n.endswith("…") or "env." not in n]
    assert presets.layout == {} and said == [] and not lib.is_dirty("presets")
    assert LAYOUT_KEY not in presets.document("party-trip")
    presets.layout["render:shape"] = [520, 40]
    presets.layout["mod.1"] = [260, 300]
    assert lib.is_dirty("presets")                  # a node moved is an edit
    lib.save_as("presets", "trip-laid")
    doc = lib.read("presets", "trip-laid")
    assert doc[LAYOUT_KEY] == {"mod.1": [260, 300], "render:shape": [520, 40]}
    lib.load("presets", "party-trip")
    assert presets.layout == {}
    lib.load("presets", "trip-laid")
    assert presets.layout == {"mod.1": [260, 300], "render:shape": [520, 40]}
    assert not lib.is_dirty("presets")
    # one entry a line in the file
    text = (lib.path_of("presets", "trip-laid")).read_text()
    assert '  "render:shape": [520, 40]' in text
    # a bad entry: dropped, said
    doc[LAYOUT_KEY]["oops"] = ["x", 1]
    presets.load_doc(doc)
    assert presets.layout == {"mod.1": [260, 300], "render:shape": [520, 40]}
    assert any(n.startswith("layout: 1 entry") for n in presets.notes)
    # the show: the rig's nodes
    project.save("laid-show")
    assert not project.is_dirty()
    project.layout["lfo.1"] = [0, 120]
    project.layout["device:leap"] = [0, 0]
    assert project.is_dirty()
    project.save()
    assert not project.is_dirty()
    raw = project.path.read_text()
    project.layout.clear()
    project.load("laid-show")
    assert project.layout == {"device:leap": [0, 0], "lfo.1": [0, 120]}
    assert '"layout"' in raw


def test_auto_layout_gives_every_unplaced_node_a_column(rig):
    """Every node not placed gets a position, in its area's columns left to
    right (plan 28 N9: controllers → audio → modulation → plan 35 G's media
    → scene → look-back → effects → outputs; the render nodes by their
    depth within theirs); a placed node keeps its own and takes no room."""
    rig.lib.load("presets", "lfo-breathe")
    rig.router.table.add_modifier("smooth", ["lane:0"], rig.reg)
    # (plan 36 T4: the look-back drawn, as the old words with it on)
    g = G.build_graph(views(Switches()), wired_wiring(stacked(("acid",)), "trail"),
                      effects=("acid",))
    _every_file(rig)
    view = build(rig, g)
    placed = {"render:shape": (999.0, 999.0)}
    pos = graphview.auto_layout(view, placed)
    assert set(pos) == {n.id for n in view.nodes} - set(placed)
    x = {nid: xy[0] for nid, xy in pos.items()}
    # N9: the areas' columns, not the kinds' — the analyzer and the tempo
    # are the audio's; an LFO, a modifier and a macro the modulation's
    col = [x["source:key"], x[graphview.ANALYZER], x["lfo.1"], x["render:camera"],
           x["render:scene"], x["render:lookback"], x["render:output.all"]]
    # review round 1: lfo-breathe has the acid off and no cable on it: idle, at
    # the effects' idle line, and a through wire from where the run starts
    # (the look-back's picture) to where it ends (plan 35 G: All outputs)
    assert view.node("render:acid").idle
    assert any(c.src_port == "rout:composite" and c.dst_port == "rin:output.all/image"
               for c in graphview.layout(view).throughs)
    assert col == sorted(col) and len(set(col)) == len(col)
    assert x["group:tempo"] == x[graphview.ANALYZER]
    assert x["mod.1"] == x["macro.1"] == x["lfo.1"]
    assert x["render:output.1"] == max(x.values())
    # a column's drawn nodes are stacked, never on top of one another (N9:
    # the idle LFOs 3 and 4 sit at the modulation's idle line, drawn by none)
    drawn = [nid for nid in pos if x[nid] == x["lfo.1"] and not view.node(nid).idle]
    ys = sorted(pos[nid][1] for nid in drawn)
    assert {"lfo.1", "lfo.2", "mod.1", "macro.1"} <= set(drawn)
    assert len(set(ys)) == len(ys)
    # the preset's map and the show's, by home
    pre, ses = graphview.split(view, {**pos, **placed})
    assert "render:shape" in pre and "mod.1" in pre and "macro.1" in pre and "lfo.1" in pre
    assert graphview.ANALYZER in ses and "render:output.1" in ses
    assert not set(pre) & set(ses)


def test_graphview_imports_no_imgui():
    tree = ast.parse((PKG / "graphview.py").read_text())
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any("imgui" in m for m in names)


def test_no_plumbing_words_remain():
    """Plan 35 T5: the frame is ordinary nodes and wires, so the canvas's
    words for the old frame's own plumbing are gone, and so are the T3/T4
    bridges that drew a wired frame in plan 33's words."""
    from hyperspace import preset, ui_graph
    for name in ("PLUMBING", "RUN_KEPT", "FEEDS", "FEEDS_NO_DELETE", "FrameNode",
                 "canvas_name", "run_end", "_with_run", "_framed", "_is_plumbing"):
        assert not hasattr(graphview, name), name
    assert not hasattr(ui_graph, "_feeds_cut")
    assert not hasattr(preset.GraphSection, "said")
    src = (PKG / "graphview.py").read_text()
    assert "is the default graph's" not in src and "FX_NAMES" not in src


def test_the_routing_page_and_the_graph_page_show_one_table(rig):
    """One table, two views: a route added on ROUTING is a cable on the
    canvas the next frame, and gone when ROUTING deletes it."""
    frame(rig.panel, "graph")
    n0 = sum(1 for c in ui_graph._state(rig.panel)["view"].cables if c.kind == "route")
    b = ui_routing.add_route(rig.panel, "view.bright", "lane:2", 0.4)
    frame(rig.panel, "graph")
    view = ui_graph._state(rig.panel)["view"]
    assert sum(1 for c in view.cables if c.kind == "route") == n0 + 1
    assert any(c.ref is b for c in view.cables)
    rig.router.table.remove(b)
    frame(rig.panel, "graph")
    assert not any(c.ref is b for c in ui_graph._state(rig.panel)["view"].cables)


# ---------------------------------------------------------------- the page

def test_the_graph_page_sits_after_routing():
    keys = [k for k, _, _ in PAGES]
    assert keys.index("graph") == keys.index("routing") + 1
    assert PAGES[keys.index("graph")][2] == PAGES[keys.index("routing")][2]


def test_the_page_draws_with_a_factory_preset_and_a_render_graph(rig):
    """The page drawn for real on the node editor, headless: a factory
    preset loaded, a render graph with effects, every node expanded and
    collapsed, a route and an effect node selected (the side column), a
    tidy — and nothing raises; the SYSTEM page then has its line."""
    from test_graph_legible import party  # (plan 35 T5: its frame landed as the preset's)
    party(rig)
    rig.reg["fx.acid.on"].set(1)        # N9: an off effect with no cable is not drawn
    for _ in range(3):
        frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    view = st["view"]
    assert st["created"] == 1 and st["editor"] is not None
    assert view.node("render:acid") is not None
    # every drawn node placed (N9: an idle one is not on the canvas)
    assert all(n.id in st["applied"] for n in view.nodes if ui_graph.drawn_node(st, n))
    # plan 28 N7: every node starts collapsed; expanded, a route is its own cable
    assert not st["open"]
    ui_graph.expand_all(st, view, True)
    frame(rig.panel, "graph")
    st["patched_only"] = False
    frame(rig.panel, "graph")
    st["folds"].add(("render:shape", "view"))
    frame(rig.panel, "graph")
    # select a route, then an effect's node: the side column draws
    route = next(c for c in view.cables if c.kind == "route")
    _in_editor(rig, lambda: ed.select_link(ed.LinkId(ui_graph._id(st, "c:" + route.id))))
    frame(rig.panel, "graph")
    assert ui_graph._selection(st, view) == ("cable", route)
    _in_editor(rig, lambda: (ed.clear_selection(), ed.select_node(
        ed.NodeId(ui_graph._id(st, "n:render:acid")))))
    frame(rig.panel, "graph")
    assert ui_graph._selection(st, view)[1].id == "render:acid"
    st["tidy"] = True
    frame(rig.panel, "graph")
    assert ui_graph.timing_line(rig.panel).startswith("graph page: ")
    frame(rig.panel, "system")


def _in_editor(rig, fn):
    """Run `fn` on the panel's editor context inside a frame (what a
    click on the canvas would do)."""
    st = ui_graph._state(rig.panel)
    imgui.new_frame()
    imgui.begin("probe")
    ed.set_current_editor(st["editor"])
    ed.begin("##graph", imgui.ImVec2(400, 400))
    fn()
    ed.end()
    imgui.end()
    imgui.end_frame()


def test_a_node_dropped_on_the_canvas_is_saved_in_its_home(rig):
    """A node moved on the canvas is written where it lives — a render
    node and an LFO (plan 31 G1) into the loaded preset's layout (dirtying
    it), the analyzer into the show's — once the mouse lets go; a node left
    alone is written nowhere."""
    rig.lib.load("presets", "party-trip")
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    assert rig.lib.presets.layout == {} and rig.lib.project.layout == {}
    assert not rig.lib.is_dirty("presets")

    def move():
        ed.set_node_position(ed.NodeId(ui_graph._id(st, "n:render:camera")), imgui.ImVec2(700, 50))
        ed.set_node_position(ed.NodeId(ui_graph._id(st, "n:lfo.1")), imgui.ImVec2(30, 640))
        ed.set_node_position(ed.NodeId(ui_graph._id(st, "n:analyzer")), imgui.ImVec2(40, 20))
    _in_editor(rig, move)
    frame(rig.panel, "graph")
    # N9: lfo.2 is idle, not drawn
    assert rig.lib.presets.layout == {"render:camera": [700, 50], "lfo.1": [30, 640]}
    assert rig.lib.project.layout == {"analyzer": [40, 20]}
    assert rig.lib.is_dirty("presets")
    # tidy forgets them both
    st["tidy"] = True
    frame(rig.panel, "graph")
    assert rig.lib.presets.layout == {} and rig.lib.project.layout == {}


def test_the_editor_context_is_made_once_kept_across_a_reload_and_destroyed_on_close(rig,
                                                                                     monkeypatch):
    """One context per panel: made on the page's first draw, kept in the
    panel's state so a hot reload of ui_graph draws on the same one (no
    second context, no leak), destroyed by `Panel.close` (quit, ⌘R) —
    twice is harmless — and made afresh if the page draws again."""
    made, gone = [], []
    real_create, real_destroy = ed.create_editor, ed.destroy_editor
    monkeypatch.setattr(ed, "create_editor", lambda cfg: made.append(cfg.settings_file)
                        or real_create(cfg))
    monkeypatch.setattr(ed, "destroy_editor", lambda c: gone.append(c) or real_destroy(c))
    frame(rig.panel, "view")                         # another page: no context yet
    assert made == []
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    assert made == [""]                              # the widget's settings file is off
    first = ui_graph._state(rig.panel)["editor"]
    mod = importlib.reload(ui_graph)                 # what the hot reloader does
    frame(rig.panel, "graph")
    assert made == [""] and mod._state(rig.panel)["editor"] is first
    rig.panel.close()
    rig.panel.close()
    assert gone == [first] and mod._state(rig.panel)["editor"] is None
    frame(rig.panel, "graph")
    assert len(made) == 2
    rig.panel.close()


# ---------------------------------------------------------------- review round 1

def test_a_d1_placed_effect_from_a_real_spec_is_an_effect_node_with_image_cables(rig):
    """D1's placement (`palette-hands.json`: the palette `after` the hands'
    layer), read by `graph.read_graph` and built by `default_graph`, is an
    `effect` render node on the canvas with its image cables in and out,
    and the palette's params on it — nothing here reads `after` / `into`."""
    import json
    doc = json.loads((Path(__file__).parent / "fixtures" / "presets" /
                      "palette-hands.json").read_text())
    # (plan 36 T3: the canvas draws a `/7` frame — the old section migrated,
    # its placement the wires it stood for)
    from hyperspace import graphmigrate as M

    old = G.read_graph(doc["graph"])
    spec = G.read_graph(M.seven(doc, {})[0]["graph"])
    g = thru(old.wiring(), ("acid", "palette"), Shows(), Shows(through=True))
    _every_file(rig)
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    node = view.node("render:palette")
    # (plan 36 T3: the placement is the wires it stood for — a wired effect)
    assert node is not None and isinstance(node.ref, G.Effect) and node.ref.placed == "wire"
    assert view.spec is spec
    wires = [c for c in view.cables if c.kind == "render"]
    into = [c for c in wires if c.dst_port == "rin:palette/image"]
    out = [c for c in wires if c.src_port == "rout:palette"]
    assert [c.src_port for c in into] == ["rout:hands.layer"]     # (plan 35 V2)
    assert out and all(c.type == graphview.IMAGE for c in (*into, *out))
    assert owner_of(view, "fx.palette.mix") == "render:palette"


def test_a_route_depth_follows_its_macro_and_its_slider_without_a_rebuild(rig):
    """The hover's depth (`value × scale × Π depth subscribers`) is
    `refresh`'s: a depth-subscribing macro turned, or the row's depth
    dragged, moves it with the same view (no rebuild per frame)."""
    rig.lib.load("presets", "lfo-breathe")
    table = rig.router.table
    mid, s = next((mid, s) for mid, m in table.macros.items() for s in m.subs
                  if s.depth is not None)
    b = next(b for b in table.routes() if (b.source, b.target) == s.depth)
    k0 = graphview.key(table, rig.reg, rig.router, None, None, None)
    view = build(rig)
    c = next(c for c in view.cables if c.ref is b)
    rig.reg[mid].set_norm(0.0)
    b.value = 0.8
    assert graphview.key(table, rig.reg, rig.router, None, None, None) == k0
    graphview.refresh(view, rig.reg, rig.router)
    want = 0.8 * s.at(float(rig.reg[mid].base))
    if b.scale is not None:
        want *= float(rig.reg[b.scale].value)
    assert c.depth == pytest.approx(want) and "depth +0.80" in c.label


def test_an_expanded_node_pushes_its_column_down():
    """auto_layout counts a node's own expand: the node under it moves down
    by the extra port lines, never overlapping it."""
    view = graphview.View(nodes=[
        graphview.VNode("a", "lfo", "a", ports=[graphview.VPort(f"p{i}", "p", "in",
                                                                param=f"x{i}")
                                                for i in range(10)]),
        graphview.VNode("b", "lfo", "b")])
    flat = graphview.auto_layout(view)
    full = graphview.auto_layout(view, expanded=lambda nid: nid == "a")
    assert full["b"][1] - flat["b"][1] == pytest.approx(10 * graphview.ROW_H)


def _undo_rig(tmp_path):
    from test_undo import boot, settle
    r = boot(tmp_path / "home")
    settle(r)
    r.undo.clear()
    return r, settle


def test_undoing_a_load_puts_the_earlier_layout_back(tmp_path):
    """The marks carry the GRAPH page's positions: undoing a preset load
    over a plain preset leaves no positions and no dirt; undoing a show
    load gives the earlier show's map back, clean."""
    from hyperspace.library import PRESETS
    r, settle = _undo_rig(tmp_path)
    lib, presets, pr = r.lib, r.presets, r.lib.project
    presets.save_as("plain")
    presets.layout["render:shape"] = [40, 80]
    presets.save_as("laid")
    lib.load(PRESETS, "plain")
    settle(r)
    lib.load(PRESETS, "laid")
    settle(r)
    assert presets.layout == {"render:shape": [40, 80]}
    assert r.undo.undo()
    assert lib.current(PRESETS) == "plain"
    assert presets.layout == {} and not lib.is_dirty(PRESETS)
    # the show
    pr.save("show-plain")
    pr.layout["lfo.1"] = [0, 10]
    pr.save("show-laid")
    pr.load("show-plain")
    settle(r)
    assert pr.layout == {} and not pr.is_dirty()
    r.undo.clear()
    pr.load("show-laid")
    settle(r)
    assert pr.layout == {"lfo.1": [0, 10]}
    assert r.undo.undo()
    assert pr.name == "show-plain" and pr.layout == {} and not pr.is_dirty()


def test_a_tidy_is_one_undo_step(tmp_path):
    """Tidy forgets both maps' positions as one step; ⌘Z puts them back;
    ⇧⌘Z tidies both again."""
    from types import SimpleNamespace

    from hyperspace.library import PRESETS
    r, settle = _undo_rig(tmp_path)
    lib, presets, pr = r.lib, r.presets, r.lib.project
    presets.layout["render:shape"] = [40, 80]
    pr.layout["lfo.1"] = [0, 10]
    settle(r)
    view = graphview.View(nodes=[graphview.VNode("render:shape", "render", "shape"),
                                 graphview.VNode("lfo.1", "lfo", "LFO 1")])
    ui_graph.forget(SimpleNamespace(library=lib), view)
    assert presets.layout == {} and pr.layout == {}
    settle(r)
    assert r.undo.undo() and r.undo.status.endswith("tidy the graph")
    assert presets.layout == {"render:shape": [40, 80]} and pr.layout == {"lfo.1": [0, 10]}
    assert lib.is_dirty(PRESETS)            # the positions are still not saved
    settle(r)
    assert r.undo.redo() and r.undo.status.endswith("tidy the graph")
    assert presets.layout == {} and pr.layout == {}     # both maps tidied again
    assert not lib.is_dirty(PRESETS)        # (the saved preset holds no positions either)


# ---------------------------------------------------------------- plan 32 T10: the media area

def test_graph_has_media_area(rig):
    """The eight channels are eight source nodes in a titled media area
    (plan 35 V2: `render:channel.<c>`, kind `channel`, a picture out each,
    the channel's `media.<c>.*` params on it), whatever the render graph
    holds; a channel no cable leaves and whose bin is empty is idle (its
    area's line). Plan 35 G: the backdrop is drawn only when the section
    wires or declares it (its params else on their group's node). A wire
    from `channel.a` — into an effect's `aux` port, or under the scene as
    the backdrop — is drawn from the one `channel.a` node, and it names
    `channel.a` again when unwired or rewired."""
    from hyperspace.media.channels import CHANNELS

    view = build(rig)
    media = [n for n in view.nodes if n.area == graphview.MEDIA]
    chans = [n for n in media if n.id.startswith("render:channel.")]
    assert [n.id for n in chans] == [f"render:channel.{c}" for c in CHANNELS]
    assert all(n.kind == "channel" and n.ports[0].id == f"rout:channel.{n.id[-1]}"
               for n in chans)
    assert owner_of(view, "media.c.jog") == "render:channel.c"
    assert view.node("render:backdrop") is None
    assert owner_of(view, "backdrop.alpha") == "group:backdrop"
    assert all(n.idle for n in chans)                       # nothing in a bin, no cable
    assert graphview.TITLES[graphview.MEDIA] == "MEDIA"
    assert graphview.AREAS.index(graphview.MEDIA) < graphview.AREAS.index(graphview.SCENE_AREA)
    lay = graphview.layout(view, collapsed=lambda nid: True)
    assert graphview.MEDIA in lay.titles and lay.idle[graphview.MEDIA]
    assert "8 empty channels" in graphview.idle_words(view.node(i) for i in
                                                       lay.idle[graphview.MEDIA])
    # a bin with something in it: drawn, though nothing is wired
    rig.reg.media.assign("b", 0, "shared:loops/tunnel.mp4")
    assert not build(rig).node("render:channel.b").idle
    # a wire from channel.a into an effect's aux, with the backdrop on a as well
    spec = G.read_graph({"frame": "wired", "wires": [
        {"from": "channel.a", "to": "backdrop.image"}, {"from": "shape", "to": "scene.geometry"},
        {"from": "scene", "to": "backdrop.scene"}, {"from": "backdrop", "to": "acid.image"},
        {"from": "channel.a", "to": "acid.aux"}, {"from": "acid", "to": "output.all.image"}]})
    assert not spec.notes
    g = G.build_graph(views(Switches()), wired_wiring(spec.wiring()), effects=("acid",))
    assert {"channel.a", "channel.a(wire)"} <= set(g.nodes)
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    assert view.node("render:channel.a(wire)") is None       # one node per channel
    froms = [c for c in view.cables if c.src_port == "rout:channel.a"]
    assert {c.dst_port for c in froms} == {"rin:acid/aux", "rin:backdrop/image"}
    assert all(c.type == graphview.IMAGE for c in froms)
    assert not view.node("render:channel.a").idle
    assert view.node("render:backdrop").area == graphview.SCENE_AREA
    assert owner_of(view, "backdrop.alpha") == "render:backdrop"
    wired = next(c for c in froms if c.dst_port == "rin:acid/aux")
    assert graphview.spec_name(wired.src_port, g) == ("channel.a", None)
    assert graphview.spec_name("rout:channel.e", g) == ("channel.e", None)  # not in the graph


def test_the_media_area_draws_on_the_page(rig, monkeypatch):
    """The page draws the media area's title and, a bin filled, its node."""
    from test_graph_areas import drawn_ids

    rig.reg.media.assign("a", 0, "shared:x.png")
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    assert "render:channel.a" in drawn_ids(rig, monkeypatch)
    assert "render:channel.b" not in drawn_ids(rig, monkeypatch)


# ---------------------------------------------------------------- plan 33 T6: the free graph

def test_the_new_nodes_sit_in_their_areas(rig):
    """Plan 33 U, in plan 35's areas: the pattern and a switch are render
    nodes with the channels in the media, the look-back the look-back's,
    an effect the effects', All outputs the outputs' — and the params go to
    the node that owns them: `view.pattern*` and `view.media_*` to the
    pattern, `switch.select` to its switch, `fx.face_map` to the shape
    (whose `faces` port is a picture input). Plan 35 G: no `frame`, no
    `fx`, no feeds — the look-back's picture goes straight into the first
    effect by its wire; the pattern and the backdrop are drawn only when
    the section names them."""
    from hyperspace.params import declare_switches
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "switch"}],
                         "wires": [{"from": "shape", "to": "scene.geometry"},
                                   {"from": "scene", "to": "lookback.image"},
                                   {"from": "lookback", "to": "acid.image"},
                                   {"from": "acid", "to": "output.all.image"},
                                   {"from": "channel.a", "to": "switch.in1"},
                                   {"from": "switch", "to": "pattern.media"}]},
                        effects={"acid"})
    assert not spec.notes
    declare_switches(rig.reg, ["switch"])
    g = G.build_graph(views(Switches()), wired_wiring(spec.wiring()), effects=("acid",))
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    area = {n.id: n.area for n in view.nodes}
    for nid in ("render:pattern", "render:switch", "render:channel.a"):
        assert area[nid] == graphview.MEDIA, nid
    assert area["render:lookback"] == graphview.LOOKBACK_AREA
    assert area["render:acid"] == graphview.EFFECTS_AREA
    assert area["render:output.all"] == graphview.OUTPUTS_AREA
    assert "render:backdrop" not in area and "render:frame" not in area
    assert owner_of(view, "view.pattern_mix") == "render:pattern"
    assert owner_of(view, "view.media_alpha") == "render:pattern"
    assert owner_of(view, "switch.select") == "render:switch"
    assert owner_of(view, "fx.face_map") == "render:shape"
    assert owner_of(view, "view.bright") == "render:shape"
    assert view.node("render:shape").port("rin:shape/faces").type == graphview.IMAGE
    renders = {(c.src_port, c.dst_port) for c in view.cables if c.kind == "render"}
    assert ("rout:lookback", "rin:acid/image") in renders
    assert ("rout:acid", "rin:output.all/image") in renders
    assert ("rout:switch", "rin:pattern/media") in renders
    assert all(c.kind != "feeds" for c in view.cables)
    # with no render graph and no section: neither the pattern nor the backdrop
    bare = build(rig)
    assert bare.node("render:pattern") is None and bare.node("render:backdrop") is None
    # names a wire uses, from the canvas's pins (plan 35 G: the shape too)
    assert graphview.spec_name("rout:lookback", g) == ("lookback", None)
    assert graphview.spec_name("rin:output.all/image", g) == ("output.all.image", None)
    assert graphview.spec_name("rin:shape/faces", g) == ("shape.faces", None)
    assert graphview.spec_name("rin:backdrop/image", g) == ("backdrop.image", None)
    assert graphview.spec_name("rout:shape", g) == ("shape", None)
    assert graphview.spec_name("render:camera", g)[0] is None      # the rig's


def test_an_unreached_branch_is_drawn_faint_from_the_spec(rig):
    """An effect wired from a channel into nothing (`channel.a → acid.2`)
    has no render node — it never runs — but the canvas draws it from the
    spec: a faint node saying "reaches nothing", its cable in, laid out
    with the media (a picture made of the media alone)."""
    spec = G.read_graph({"frame": "wired",
                         "nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
                         "wires": [{"from": "channel.a", "to": "acid.2.image"}]},
                        effects={"acid", "acid.2"})
    g = G.build_graph(views(Switches()), wired_wiring(spec.wiring()), effects=("acid", "acid.2"))
    assert "acid.2" not in g.nodes
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    n = view.node("render:acid.2")
    assert n is not None and n.faint and n.area == graphview.MEDIA
    assert graphview.summary(n)[0] == graphview.REACHES_NOTHING
    assert any((c.src_port, c.dst_port) == ("rout:channel.a", "rin:acid.2/image")
               for c in view.cables if c.kind == "render")
    assert not view.node("render:channel.a").idle
    assert view.node("render:channel.a").faint            # (it reaches nothing either)


def test_a_render_nodes_said_is_its_first_line():
    """Plan 34 T5: a render node's `said` (`Node.said`) is the first line of
    its summary — after a switch's pick, after the faint word — and a node
    with none gives the lines it always did."""
    said = "last frame's · 64×64 half-float"
    d = G.Delay("delay")
    d.said = said
    n = graphview.VNode("render:delay", "render", "delay", ref=d)
    assert graphview.summary(n)[0] == said
    n.faint = True
    assert graphview.summary(n)[:2] == [graphview.REACHES_NOTHING, said]
    c = G.Composite("composite")
    assert getattr(c, "said", "") == ""
    assert graphview.summary(graphview.VNode("render:composite", "render", "composite",
                                             ref=c)) == ["0 params · 0 patched"]
