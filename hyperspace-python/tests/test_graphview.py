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

from hyperspace import devices, graphview, ui_graph, ui_routing
from hyperspace import graph as G
from hyperspace.devices import Port
from hyperspace.outputs import Switches, View
from hyperspace.routing import MOD_OPS
from hyperspace.ui import PAGES

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def build(rig, render_graph=None, devs=None):
    return graphview.build(rig.router.table, rig.reg, rig.router, devs, render_graph, None)


def views(*sw):
    return [View(s, (640, 360)) for s in sw]


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
    an effect's on its node in the scene's pipeline, the chain's own on
    its end, the look-back's on `history`, the camera's on `eye`, an
    output's on its output node, the hands' on their hands node; an LFO's
    knobs on that LFO; a group no render node owns on a node of its own."""
    from hyperspace.routing import Binding
    out1 = next(p.id for p in rig.reg if p.id.startswith("output.1."))
    rig.router.table.bindings.append(Binding("key:F9", out1, "toggle"))   # a setter onto it
    g = G.default_graph(views(Switches(), Switches(scene=False, hands=True, through=True)),
                        effects=("acid", "palette"))
    view = build(rig, g)
    names = {n.id for n in view.nodes}
    assert {"render:shape", "render:acid", "render:acid(hands)", "render:fx",
            "render:history", "render:output.1", "render:output.2", "render:eye"} <= names
    assert owner_of(view, "view.bright") == "render:shape"
    rot = next(p.id for p in rig.reg if p.group == "rot" and p.modulatable)
    assert owner_of(view, rot) == "render:shape"
    assert owner_of(view, "fx.acid.mix") == "render:acid"      # the scene pipeline's node
    assert owner_of(view, "fx.palette.mix") == "render:palette"
    assert owner_of(view, "fx.mix") == "render:fx"
    assert owner_of(view, "dream.mix") == "render:history"
    assert owner_of(view, "camera.zoom") == "render:eye"
    assert owner_of(view, "ghost.alpha") == "render:ghost"
    assert owner_of(view, out1) == "render:output.1"
    assert owner_of(view, "lfo.1.depth") == "lfo.1"
    assert owner_of(view, "tempo.bpm") == "group:tempo"
    assert owner_of(view, "master.gain") == "group:master"
    # no render graph: the same params fall to their groups' nodes
    bare = build(rig)
    assert owner_of(bare, "view.bright") == "group:view"
    assert owner_of(bare, "camera.zoom") == "render:eye"
    # every param port has a base and a mod stub
    port = view.owner("mod:view.bright")[1]
    assert port.pins[:2] == ("base:view.bright", "mod:view.bright")
    # where each node's position lives
    assert graphview.home(view.node("render:shape")) == graphview.PRESET
    assert graphview.home(view.node("render:output.1")) == graphview.SESSION
    assert graphview.home(view.node("lfo.1")) == graphview.SESSION
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
    assert [p.group for p in leap.ports[:4]] == ["axes", "axes", "switches", "dance"]
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
    """Every input wired in the render graph is one `render` cable of its
    port's type — geometry into the scene, image along the pipeline, mask
    into the history — and an effect placed off the default chain (here
    on the hands' layer before the output, as plan 30's placements do) is
    a node like any other, its cables image cables."""
    g = G.Graph()
    shape = g.add(G.Shape("shape"))
    hands = g.add(G.Hands("ghost"))
    scene = g.add(G.Scene("scene", geometries=[hands, shape]))
    cover = g.add(G.Cover("cover", scene=scene))
    history = g.add(G.History("history", image=scene, cover=cover))
    layer = g.add(G.HandsLayer("hands", geometry=hands))
    placed = g.add(G.Effect("acid.2", image=layer, node="acid.2"))
    end = g.add(G.Fx("fx", 0, image=history))
    g.add(G.Output("output.1", 0, image=end, hands=placed))
    from hyperspace.params import Registry
    from hyperspace.routing import Bindings
    view = graphview.build(Bindings(), Registry(), None, None, g, None)
    wires = [c for c in view.cables if c.kind == "render"]
    expect = [(src.name, n.name, port) for n in g.order for port, src in n.inputs.items()
              if src is not None]
    assert [(c.ref[0].name, c.ref[1].name, c.ref[2]) for c in wires] == expect
    by = {(c.ref[0].name, c.ref[1].name): c for c in wires}
    assert by[("shape", "scene")].type == graphview.GEOMETRY
    assert by[("cover", "history")].type == graphview.MASK
    assert by[("hands", "acid.2")].type == graphview.IMAGE
    assert by[("acid.2", "output.1")].type == graphview.IMAGE
    c = by[("acid.2", "output.1")]
    assert c.src_port == "rout:acid.2" and c.dst_port == "rin:output.1/hands"
    assert view.node("render:acid.2").kind == "render"
    assert view.node("render:output.1").kind == "output"
    assert all(p.patched for p in view.node("render:acid.2").ports)


def test_layout_round_trips_through_the_preset_and_the_show(rig):
    """The look's nodes' positions are the preset's ``layout``, the rig's
    the show's: written on save, read on load. A preset without the key
    (every factory preset) loads with no note and no dirt; one with a bad
    entry keeps the good ones and says so."""
    from hyperspace.preset import LAYOUT_KEY
    lib, presets, project = rig.lib, rig.lib.presets, rig.lib.project
    lib.load("presets", "party-trip")
    assert presets.layout == {} and presets.notes == [] and not lib.is_dirty("presets")
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
    """Every node not placed gets a position, its column by kind left to
    right — the sources, the LFOs, the modifiers, the macros, the param
    groups and the render nodes by their depth, the outputs last; a
    placed node keeps its own and takes no room."""
    rig.lib.load("presets", "lfo-breathe")
    rig.router.table.add_modifier("smooth", ["lane:0"], rig.reg)
    g = G.default_graph(views(Switches()), effects=("acid",))
    view = build(rig, g)
    placed = {"render:shape": (999.0, 999.0)}
    pos = graphview.auto_layout(view, placed)
    assert set(pos) == {n.id for n in view.nodes} - set(placed)
    x = {nid: xy[0] for nid, xy in pos.items()}
    col = [x[graphview.ANALYZER], x["lfo.1"], x["mod.1"], x["macro.1"], x["group:tempo"],
           x["render:scene"], x["render:history"], x["render:acid"], x["render:output.1"]]
    assert col == sorted(col) and len(set(col)) == len(col)
    assert x["render:output.1"] == max(x.values())
    # a column's nodes are stacked, never on top of one another
    ys = sorted(xy[1] for nid, xy in pos.items() if xy[0] == x["lfo.1"])
    assert len(ys) == 4 and len(set(ys)) == 4
    # the preset's map and the show's, by home
    pre, ses = graphview.split(view, {**pos, **placed})
    assert "render:shape" in pre and "mod.1" in pre and "macro.1" in pre
    assert "lfo.1" in ses and graphview.ANALYZER in ses and "render:output.1" in ses
    assert not set(pre) & set(ses)


def test_graphview_imports_no_imgui():
    tree = ast.parse((PKG / "graphview.py").read_text())
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any("imgui" in m for m in names)


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
    rig.lib.load("presets", "party-trip")
    rig.panel.renderer = type("R", (), {})()
    rig.panel.renderer._graph = G.default_graph(views(Switches(), Switches(through=True)),
                                                effects=("acid", "palette"))
    for _ in range(3):
        frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    view = st["view"]
    assert st["created"] == 1 and st["editor"] is not None
    assert view.node("render:acid") is not None
    assert all(n.id in st["applied"] for n in view.nodes)   # every node placed
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
    node into the loaded preset's layout (dirtying it), an LFO into the
    show's — once the mouse lets go; a node left alone is written nowhere."""
    rig.lib.load("presets", "party-trip")
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    assert rig.lib.presets.layout == {} and rig.lib.project.layout == {}
    assert not rig.lib.is_dirty("presets")

    def move():
        ed.set_node_position(ed.NodeId(ui_graph._id(st, "n:render:eye")), imgui.ImVec2(700, 50))
        ed.set_node_position(ed.NodeId(ui_graph._id(st, "n:lfo.2")), imgui.ImVec2(30, 640))
    _in_editor(rig, move)
    frame(rig.panel, "graph")
    assert rig.lib.presets.layout == {"render:eye": [700, 50]}
    assert rig.lib.project.layout == {"lfo.2": [30, 640]}
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
    frame(rig.panel)                                 # another page: no context yet
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


def test_the_page_edits_only_through_its_dispatch():
    """N2 opened no create or delete on the canvas; plan 28 N4 opens them
    for the render graph and N3 for the modulation, each through the
    page's one dispatch by port type (`CREATE`) and by cable and node kind
    (`DELETE_CABLE`, `DELETE_NODE`) — N4's: image, geometry and mask, the
    render cables and nodes. The widget's create / delete calls live in
    the dispatch's two functions alone."""
    src = (PKG / "ui_graph.py").read_text()
    tree = ast.parse(src)
    edits = {"begin_create", "begin_delete", "query_new_link", "query_deleted_link",
             "accept_new_item", "accept_deleted_item"}
    where = {f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)
             for n in ast.walk(f) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr in edits}
    assert where <= {"_create", "_delete", "new_link", "_create_render"}
    assert set(graphview.RENDER_TYPES) <= set(ui_graph.CREATE)
    assert "render" in ui_graph.DELETE_CABLE and "render" in ui_graph.DELETE_NODE



# ---------------------------------------------------------------- review round 1

def test_a_d1_placed_effect_from_a_real_spec_is_an_effect_node_with_image_cables(rig):
    """D1's placement (`palette-hands.json`: the palette `after` the hands'
    layer), read by `graph.read_graph` and built by `default_graph`, is an
    `effect` render node on the canvas with its image cables in and out,
    and the palette's params on it — nothing here reads `after` / `into`."""
    import json
    doc = json.loads((Path(__file__).parent / "fixtures" / "presets" /
                      "palette-hands.json").read_text())
    spec = G.read_graph(doc["graph"])
    g = G.default_graph(views(Switches(), Switches(through=True)), spec.wiring(),
                        effects=("acid", "palette"))
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    node = view.node("render:palette")
    assert node is not None and isinstance(node.ref, G.Effect) and node.ref.placed == "after"
    assert view.spec is spec
    wires = [c for c in view.cables if c.kind == "render"]
    into = [c for c in wires if c.dst_port == "rin:palette/image"]
    out = [c for c in wires if c.src_port == "rout:palette"]
    assert [c.src_port for c in into] == ["rout:hands"]
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
    """Tidy forgets both maps' positions as one step; ⌘Z puts them back."""
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
