"""Editing the modulation on the GRAPH page (plan 28 N3), headless.

Every edit is a `graphview.Edit` request (the model: no imgui) or one of
the page's plain functions over the panel (`ui_graph.connect`,
`disconnect`, `insert_modifier`, `add_modifier`, `dropped`, the pin
menu) — the way test_ui_routing drives ROUTING. The rig is the shell's
(tests/test_ui_shell.py: the full registry, the factory table, a scratch
library); the undo test boots app.main's construction order
(tests/test_undo.py) so the watcher and the named steps are real."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import seed
from imgui_bundle import imgui
from test_graphview import FakeDevice
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import devices, gamepad, graphview, learn, ui_graph, ui_pad, ui_routing
from hyperspace import graph as G
from hyperspace.devices import Port
from hyperspace.learn import Learn
from hyperspace.motion import DEFAULT_ROUTE_FEEL
from hyperspace.routing import MOD_OPS, Binding, is_meta_row

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)         # (the corpus: the presets the tests load by slug)
    return shell_rig


def leap():
    """A hands device: one one-sided axis, one centred, one dance lane."""
    return devices.DeviceRegistry(devices=[FakeDevice("leap", "hands", ("hand", "hands"), (
        Port("right.y", "right y", group="axes", scheme="hand"),
        Port("right.roll", "right roll", group="axes", bipolar=True, rest=0.5, scheme="hand"),
        Port("right.energy", "right energy", group="dance", scheme="hand"),
    ))])


def edit(rig, devs=None):
    table = rig.router.table
    view = graphview.build(table, rig.reg, rig.router, devs, None, None)
    return graphview.Edit(table, rig.reg, rig.router, view), view


def free_param(rig, *, centred=None):
    """A modulatable continuous param nothing performs (centred on zero
    or not, as `learn.centred_target` says)."""
    from hyperspace.params import Kind
    table = rig.router.table
    for p in rig.reg:
        if (ui_routing.route_target(p) and not p.alias and p.kind is Kind.CONTINUOUS
                and not p.integer
                and table.owner(p.id) is None and not table.routes_to(p.id)
                and (centred is None or learn.centred_target(p) == centred)):
            return p
    raise AssertionError("no free param")


def cables(view, kind="route"):
    return [c for c in view.cables if c.kind == kind]


# ---------------------------------------------------------------- the eight

def test_connecting_a_source_to_a_mod_port_adds_the_route_learn_would(rig):
    """A cable from a source into a param's `mod` stub is `Bindings.add`
    of the row the hand learn makes for that pair (`learn.row_for`): a
    one-sided hand axis on a plain param is the `position` fader at 1; a
    centred one (the device says `bipolar`) is a `push` at the hands'
    Learn depth; a band lane a push at `learn.LANE_DEPTH` (the owner,
    after the show of 2026-10-30). It lands as one cable next build.
    The same pair learned by a hand lands the same row."""
    reg, table = rig.reg, rig.router.table
    reg["hands.learn_depth"].set(0.4)
    a, b = free_param(rig, centred=False), free_param(rig, centred=True)
    e, view = edit(rig, leap())
    row = e.connect("out:hand:right.y", f"mod:{a.id}")
    assert isinstance(row, Binding) and row in table.bindings
    assert (row.source, row.target, row.op, row.value) == ("hand:right.y", a.id, "position", 1.0)
    c = free_param(rig, centred=False)
    roll = e.connect(f"mod:{c.id}", "out:hand:right.roll")     # dragged from the input end
    assert roll.op == "push" and roll.value == pytest.approx(0.4)
    lane = e.connect("out:lane:2", f"mod:{b.id}")
    assert lane.op == "push" and lane.value == learn.LANE_DEPTH   # a lane: a calm push
    # the hand's own learn of the first pair lands the same row
    table.remove(row)
    lrn = Learn(reg, table)
    lrn.arm(a.id, "hand:right")
    lrn.learn_source("hand:right.y", depth=0.4)
    learned = table.owner(a.id)
    assert (learned.op, learned.value) == (row.op, row.value)
    # one cable per route, next build
    _, view = edit(rig, leap())
    for r in (learned, roll, lane):
        c = next(c for c in cables(view) if c.ref is r)
        assert c.dst_port == f"mod:{r.target}" and c.src_port == f"out:{r.source}"
    # refusals, in words, the table untouched
    n = len(table.bindings)
    assert e.connect("out:cc:0:52", f"mod:{a.id}") == (
        "a desk knob sets a base, not a performer; aim at base")
    assert e.connect("out:lane:2", f"mod:{b.id}") == graphview.ALREADY
    assert e.connect("out:lane:1", "out:lane:2") == graphview.SAME_SIDE
    assert len(table.bindings) == n


def test_a_taken_param_asks_and_replace_owner_lands_the_cable(rig):
    """A cable into a param another performer holds is ROUTING's prompt
    (`ui_routing.ask`): the table is untouched until it is answered;
    *Keep* leaves it; *Replace* is `replace_owner` — the old row goes, the
    new is the param's one performer, and the canvas draws it."""
    panel, table = rig.panel, rig.router.table
    old = next(b for b in table.routes() if b.enabled and b.target in rig.reg)
    frame(panel, "graph")
    res = ui_graph.connect(panel, "out:lane:5", f"mod:{old.target}")
    assert isinstance(res, graphview.Ask) and res.old is old
    assert ui_routing.prompt(panel) == (old, res.new)
    assert table.owner(old.target) is old                  # nothing moved yet
    ui_routing.answer(panel, False)                        # Keep
    assert ui_routing.prompt(panel) is None and table.owner(old.target) is old
    res = ui_graph.connect(panel, "out:lane:5", f"mod:{old.target}")
    ui_routing.answer(panel, True)                         # Replace
    assert table.owner(old.target) is res.new and old not in table.bindings
    frame(panel, "graph")
    view = ui_graph._state(panel)["view"]
    into = [c for c in cables(view) if c.dst_port == f"mod:{old.target}"]
    assert [c.ref for c in into] == [res.new] and into[0].src_port == "out:lane:5"


def test_moving_a_cables_end_moves_the_route_and_its_depth_subs_follow(rig):
    """A cable's end picked up at its param and dropped on another param's
    `mod` stub is `move_route`: the same row (op, depth) now lands there,
    and the macro subscriber scaling its depth follows it. Onto a taken
    param it asks, and Replace retargets the row (`replace_owner(…,
    target=)`)."""
    rig.lib.load("presets", "lfo-breathe")
    table = rig.router.table
    _mid, s = next((mid, s) for mid, m in table.macros.items() for s in m.subs
                  if s.depth is not None)
    row = next(b for b in table.routes() if (b.source, b.target) == s.depth)
    op, depth = row.op, row.value
    to = free_param(rig)
    e, view = edit(rig)
    assert e.connect(f"mod:{row.target}", f"mod:{to.id}") is None
    assert (row.target, row.op, row.value) == (to.id, op, depth) and row in table.bindings
    assert s.depth == (row.source, to.id)
    _, view = edit(rig)
    c = next(c for c in cables(view) if c.ref is row)
    assert c.dst_port == f"mod:{to.id}"
    sub = next(c for c in cables(view, "sub") if c.ref[1] is s)
    assert sub.dst_port == f"depth:{to.id}" and not sub.off
    # onto a taken param: the prompt, then Replace retargets
    other = next(b for b in table.routes() if b is not row and b.enabled)
    e, view = edit(rig)
    ask = e.connect(f"mod:{other.target}", f"mod:{row.target}")
    assert isinstance(ask, graphview.Ask) and ask.old is row and ask.new is other
    ask.commit()
    assert table.owner(to.id) is other and row not in table.bindings


def test_a_hand_into_a_base_port_is_refused_in_words_and_a_pad_is_a_setter_row(rig):
    """`base` is the setters' stub: a hand (any lane) is refused in words;
    a desk knob is the desk learn's row (a preset-layer `abs` row,
    `bind(write=False)`: the loaded preset's); a pad button the pad
    learn's (the session's, as the factory's pad rows are). A macro's
    cable is a base subscriber there, a depth subscriber on a depth stub."""
    reg, table = rig.reg, rig.router.table
    e, view = edit(rig, leap())
    n = len(table.bindings)
    assert e.connect("out:hand:right.y", "base:view.bright") == "a hand sets no base; aim at mod"
    assert e.connect("out:lane:0", "base:view.bright") == "the analyzer sets no base; aim at mod"
    assert len(table.bindings) == n
    knob = e.connect("out:cc:0:52", "base:camera.zoom")
    assert (knob.op, knob.layer, knob.target) == ("abs", "preset", "camera.zoom")
    assert not is_meta_row(knob)
    pad = e.connect("out:pad:BACK", "base:view.points")
    assert (pad.source, pad.target, pad.op) == ("pad:BACK", "view.points", "toggle")
    assert is_meta_row(pad) and pad in table.bindings
    _, view = edit(rig, leap())
    refs = [c.ref for c in cables(view, "setter")]
    assert any(x is knob for x in refs) and any(x is pad for x in refs)
    # a macro: a base subscriber (from where the param sits to the top of
    # its fader, row 537 — the land itself moves nothing; the next
    # `follow_macros` does) and a depth one
    route = e.connect("out:lane:3", f"mod:{free_param(rig).id}")
    e, view = edit(rig, leap())
    was = reg["view.bright"].base
    s = e.connect("bus:macro.2", "base:view.bright")
    assert s.base == "view.bright" and s in table.macros["macro.2"].subs
    assert reg["view.bright"].base == was
    assert (s.lo, s.hi) == (pytest.approx(reg["view.bright"].norm), 1.0) and s.lo < s.hi
    d = e.connect(f"depth:{route.target}", "bus:macro.2")      # either end first
    assert d.depth == (route.source, route.target)
    assert e.connect("out:lane:1", f"depth:{route.target}") == graphview.ONLY_MACRO_DEPTH
    assert e.connect("bus:macro.2", f"mod:{route.target}") == graphview.MACRO_NO_MOD


def test_dropping_a_modifier_on_a_cable_inserts_it(rig):
    """A modifier dropped onto a route: the route's source becomes the
    modifier's input and its lane the route's source (`move_route`: the
    row's op and depth kept, a push keeps its old source's rest). The
    page finds the drop by the curve the widget draws (`cable_near`) —
    only for a modifier still free of cables."""
    table, panel = rig.router.table, rig.panel
    p = free_param(rig, centred=False)
    route = table.add(Binding("lane:0", p.id, "position", 0.8))
    e, view = edit(rig)
    c = next(c for c in cables(view) if c.ref is route)
    m = e.insert_modifier(c, "smooth")
    assert m.inputs == ("lane:0",) and route.source == m.address
    assert (route.op, route.value, route.target) == ("position", 0.8, p.id)
    _, view = edit(rig)
    assert any(x.kind == "input" and x.ref[0].id == m.id and x.addr == "lane:0"
               for x in view.cables)
    # on the page: a free modifier let go on the cable's curve goes in
    q = free_param(rig, centred=False)
    push = table.add(Binding("lane:4", q.id, "push", 0.3))
    frame(panel, "graph")
    free = ui_graph.add_modifier(panel, "curve", at=(10, 10))
    assert panel.library.presets.layout[free.id] == [10, 10]
    frame(panel, "graph")
    st = ui_graph._state(panel)
    view = st["view"]
    cab = next(x for x in cables(view) if x.ref is push)
    st["pin_xy"] = {cab.src_port: (0.0, 0.0), cab.dst_port: (400.0, 0.0)}
    assert ui_graph.dropped(panel, view, free.id, (500.0, 300.0)) is None    # off the curve
    assert push.source == "lane:4"
    assert ui_graph.dropped(panel, view, free.id, (200.0, 4.0)) is cab
    assert push.source == free.address and table.modifier(free.id).inputs == ("lane:4",)
    assert push.rest == rig.router.rest_of("lane:4")
    # a modifier with cables is not inserted by a drop
    frame(panel, "graph")
    view = st["view"]
    assert ui_graph.dropped(panel, view, free.id, (200.0, 4.0)) is None
    # a desk row is no place for a modifier
    setter = next(x for x in cables(view, "setter"))
    assert e.insert_modifier(setter, "smooth") == graphview.MOD_ONLY_ROUTE


def test_deleting_a_cable_removes_the_route_and_undo_puts_it_back(tmp_path):
    """Delete on a route's cable is `remove` — its macro depth subscriber
    goes with it — as one named undo step; ⌘Z puts the row and the
    subscriber back. A session row's cable (a key, the pad) is refused."""
    from test_undo import boot, settle
    r = boot(tmp_path / "home")
    settle(r)
    r.lib.load("presets", "lfo-breathe")
    settle(r)
    r.undo.clear()
    table = r.table
    mid, s = next((mid, s) for mid, m in table.macros.items() for s in m.subs
                  if s.depth is not None)
    row = next(b for b in table.routes() if (b.source, b.target) == s.depth)
    panel = SimpleNamespace(router=r.router, reg=r.reg, library=r.lib, midi=None)
    view = ui_graph.view_of(panel)
    c = next(c for c in cables(view) if c.ref is row)
    ui_graph.disconnect(panel, c)
    assert row not in table.bindings and s not in table.macros[mid].subs
    settle(r)
    assert r.undo.undo() and r.undo.status.endswith(f"delete cable {c.id}")
    back = [b for b in table.routes() if (b.source, b.target) == s.depth]
    assert len(back) == 1 and back[0].op == row.op and back[0].value == row.value
    assert any(x.depth == s.depth for x in table.macros[mid].subs)
    view = ui_graph.view_of(panel)
    assert any(x.ref is back[0] for x in cables(view))
    # the session's rows are bindings.json's: refused, kept
    key = next(c for c in cables(view, "setter") if is_meta_row(c.ref))
    res = ui_graph.disconnect(panel, key)
    assert res == graphview.META_ROW.format(what=key.ref.source)
    assert key.ref in table.bindings
    assert ui_graph._state(panel)["note"] == res


def test_learn_from_a_port_lands_as_a_cable(rig, monkeypatch):
    """Right-click a param's `mod` pin: the param menu's own Learn items
    (`Panel._ctx_learn`, the very function); picking "Learn hand ▸ right"
    arms the learn as the widget's menu does, the hand completes it, and
    the row is a cable the next frame — the view rebuilt from the table."""
    panel, table = rig.panel, rig.router.table
    panel.learn = Learn(rig.reg, table, lane=rig.router.lane)
    p = free_param(rig, centred=False)
    frame(panel, "graph")
    st = ui_graph._state(panel)
    seen = []
    real = type(panel)._ctx_learn
    monkeypatch.setattr(type(panel), "_ctx_learn",
                        lambda self, a, q: (seen.append((a.id, q.id)), real(self, a, q)))
    # the menu's clicks: "Learn hand" opens, "right" is picked
    import hyperspace.ui as ui_mod
    monkeypatch.setattr(ui_mod.imgui, "begin_menu", lambda label, *a: label == "Learn hand")
    monkeypatch.setattr(ui_mod.imgui, "end_menu", lambda: None)
    monkeypatch.setattr(ui_mod.imgui, "menu_item_simple", lambda label, *a, **k: label == "right")
    imgui.new_frame()
    imgui.begin("menu")
    st["menu"] = ("pin", f"mod:{p.id}")
    ui_graph.menu(panel, st, st["view"])
    imgui.end()
    imgui.end_frame()
    monkeypatch.undo()
    assert seen == [(p.id, p.id)]
    assert (panel.learn.learning, panel.learn.want) == (p.id, "hand:right")
    panel.learn.learn_source("hand:right.y")              # the hand moves
    frame(panel, "graph")
    view = ui_graph._state(panel)["view"]
    c = next(c for c in cables(view) if c.dst_port == f"mod:{p.id}")
    assert c.ref is table.owner(p.id) and c.ref.source == "hand:right.y"
    # the pin's menu with the learn armed draws Cancel; another pin just says what it is
    panel.learn.arm(p.id, "hand:right")
    imgui.new_frame()
    imgui.begin("menu")
    ui_graph._pin_menu(panel, view, f"mod:{p.id}")
    ui_graph._pin_menu(panel, view, "out:lane:0")
    imgui.end()
    imgui.end_frame()
    assert ui_graph.port_param(f"mod:{p.id}") == p.id and ui_graph.port_param("base:x") is None


def test_the_routing_page_and_the_graph_page_show_one_table(rig, monkeypatch):
    """One table, two views, both ways: a cable made on GRAPH is a row of
    ROUTING's table (`table.routes()`, drawn by ROUTING's `_row` in GRAPH's
    side pane — plan 28 N7: ROUTING itself draws only the pointer to
    GRAPH now) and a modifier picked on the canvas is in the table's
    modifiers; deleted through the table, the cable is gone from GRAPH."""
    panel, table = rig.panel, rig.router.table
    p = free_param(rig, centred=False)
    frame(panel, "graph")
    b = ui_graph.connect(panel, "out:lane:6", f"mod:{p.id}")
    m = ui_graph.add_modifier(panel, "threshold")
    drawn, strip = [], []
    real_row, real_mods = ui_routing._row, ui_routing.modifiers
    monkeypatch.setattr(ui_routing, "_row", lambda pn, r, x, k: drawn.append(x)
                        or real_row(pn, r, x, k))
    monkeypatch.setattr(ui_routing, "modifiers", lambda pn, r: strip.extend(
        r.table.modifiers) or real_mods(pn, r))
    frame(panel, "routing")
    assert not drawn and not strip                    # N7: ROUTING draws neither
    assert any(x is b for x in table.routes()) and m in table.modifiers
    # the cable selected on GRAPH: its ROUTING row in the side pane
    frame(panel, "graph")
    st = ui_graph._state(panel)
    cable = next(c for c in st["view"].cables if c.ref is b)
    imgui.new_frame()
    imgui.begin("side")
    ui_graph._side(panel, st, st["view"], ("cable", cable))
    imgui.end()
    imgui.end_frame()
    assert any(x is b for x in drawn)
    table.remove(b)                                   # ROUTING's ×
    frame(panel, "graph")
    view = ui_graph._state(panel)["view"]
    assert not any(c.ref is b for c in view.cables)
    assert view.node(m.id) is not None


# ---------------------------------------------------------------- the rest

def test_render_pins_reach_n4s_methods_and_refuse_as_a_refusal(rig):
    """The seam: a request touching an image / geometry / mask pin, a
    render cable or a render node is dispatched to N4's methods by name
    (`wire`, `unwire`, `remove_render_node`, `wire_refusal`); their plain
    words come back as a `Refusal` (the page's note), a landing as None;
    the page's drag and delete tables route those types to N4's handlers."""
    rig.lib.load("presets", "party-wake")            # (plan 35 T5: a wired frame landed)
    table = rig.router.table
    view = graphview.build(table, rig.reg, rig.router, None, None, None)
    e = graphview.Edit(table, rig.reg, rig.router, view, graph=rig.lib.presets.graph)
    gs = rig.lib.presets.graph
    assert graphview.RENDER_NOT_YET not in (
        e.connect("rout:shape", "rin:scene/geometry"),
        e.refusal("rin:scene/geometry", "rout:shape"))
    # plan 35 G: the shape into the scene is a wire like any other
    assert e.refusal("rin:scene/geometry", "rout:shape") is None
    got = e.refusal("rin:output.1/image", "rout:hands")
    assert isinstance(got, str) and "hands makes geometry" in got
    # input end first: ordered, and it lands
    assert e.connect("rin:output.2/hands", "rout:hands.layer") is None
    assert G.Wire("hands.layer", "output.2.hands") in gs.spec.wires
    wire = graphview.VCable("wire:hands.layer>output.2/hands", "rout:hands.layer",
                            "rin:output.2/hands", graphview.IMAGE, kind="render")
    assert e.disconnect(wire) is None
    assert G.Wire("hands.layer", "output.2.hands") not in gs.spec.wires
    got = e.disconnect(wire)
    assert isinstance(got, graphview.Refusal) and got == graphview.NO_SUCH_WIRE.format(
        wire="hands.layer → output.2.hands")
    # (plan 35 G: the shape deletes too; the camera is the look's one, kept)
    got = e.remove_node("render:camera")
    assert isinstance(got, graphview.Refusal) and got == graphview.CAMERA_KEPT.format(
        label="Camera")
    for t in graphview.RENDER_TYPES:
        assert ui_graph.CREATE[t] is ui_graph._create_render
    for t in (graphview.VALUE, graphview.TRIGGER):
        assert ui_graph.CREATE[t] is ui_graph._value_drag
    assert ui_graph.DELETE["render"] is ui_graph._delete_render_cable
    assert ui_graph.DELETE_NODE["render"] is ui_graph.DELETE_NODE["output"] is (
        ui_graph._delete_render_node)
    # a subclass that brings its own `wire` gets the call (by name)
    calls = []

    class N4(graphview.Edit):
        def wire(self, src, dst):
            calls.append((src, dst))
    n4 = N4(rig.router.table, rig.reg, rig.router, None)
    assert n4.connect("rin:scene/geometry", "rout:shape") is None
    assert calls == [("rout:shape", "rin:scene/geometry")]


def test_nodes_the_picker_adds_and_delete_removes(rig):
    """The picker's modifier and macro, a modifier's input by a cable, and
    a node delete: a modifier and a macro go (a route on the modifier's
    lane stays, dormant); the rig's nodes are refused."""
    panel, table = rig.panel, rig.router.table
    frame(panel, "graph")
    m = ui_graph.add_modifier(panel, "combine", at=(300, 40))
    view = ui_graph.view_of(panel)
    assert "macro.7" in ui_graph.macros_free(panel, view)
    ui_graph.show_macro(panel, "macro.7", at=(600, 40))
    frame(panel, "graph")
    view = ui_graph._state(panel)["view"]
    assert view.node(m.id).kind == "modifier" and view.node("macro.7").kind == "macro"
    assert table.macros["macro.7"].label == "macro 7"
    assert panel.library.presets.layout["macro.7"] == [600, 40]
    assert "macro.7" not in ui_graph.macros_free(panel, view)
    e = ui_graph.edit_of(panel, view)
    e.connect("out:lane:0", f"in:{m.id}.0")
    e.connect(f"in:{m.id}.1", "out:lane:3")
    assert table.modifier(m.id).inputs == ("lane:0", "lane:3")
    assert e.connect(m.address and f"out:{m.address}", f"in:{m.id}.0") == graphview.SELF_LOOP
    assert e.connect("bus:macro.7", f"in:{m.id}.0") == graphview.MACRO_NO_LANE
    p = free_param(rig, centred=False)
    route = e.connect(f"out:{m.address}", f"mod:{p.id}")
    assert route.source == m.address
    # a second modifier reading the first, to see it bridged too
    m2 = table.add_modifier("smooth", (m.address,), rig.panel.reg)
    ui_graph.remove_node(panel, m.id)
    # deleting it closes the chain over it: what fed its first input feeds
    # what read it — the route and the other modifier's input
    assert table.modifier(m.id) is None and route in table.bindings
    assert route.source == "lane:0" and route.target == p.id
    assert table.modifier(m2.id).inputs[0] == "lane:0"
    # with nothing in its first input, a route on its lane is left dormant
    m3 = table.add_modifier("smooth", (), rig.panel.reg)
    q = free_param(rig, centred=False)
    dormant = table.add(Binding(m3.address, q.id, "position", 0.5))
    ui_graph.remove_node(panel, m3.id)
    assert table.modifier(m3.id) is None and dormant.source == m3.address
    # a loop through it (a → b → a): b is never left reading its own lane
    a = table.add_modifier("smooth", (), rig.panel.reg)
    b = table.add_modifier("smooth", (a.address,), rig.panel.reg)
    table.set_modifier_input(a.id, 0, b.address, rig.panel.reg)
    ui_graph.remove_node(panel, a.id)
    assert table.modifier(b.id).inputs[0] == ""
    # a threshold makes a trigger of a value: what read its trigger is not
    # handed the value — its route is left dormant, as before
    t = table.add_modifier("threshold", ("lane:0",), rig.panel.reg)
    r = free_param(rig, centred=False)
    fires = table.add(Binding(t.address, r.id, "position", 0.5))
    ui_graph.remove_node(panel, t.id)
    assert table.modifier(t.id) is None and fires.source == t.address
    ui_graph.remove_node(panel, "macro.7")
    assert "macro.7" not in table.macros
    assert ui_graph.remove_node(panel, graphview.ANALYZER) == graphview.NOT_REMOVABLE.format(
        label=view.node(graphview.ANALYZER).label)
    # an LFO is the preset's since plan 31 (G1): it goes through its bank,
    # and a rig whose router steps none says so
    assert ui_graph.remove_node(panel, "lfo.1") == graphview.NO_BANK.format(what="LFO")


def test_the_page_draws_with_its_editing_menus(rig):
    """The page draws with each right-click menu's subject set (a pin, a
    cable, a node, the picker) and a refusal on its head — the create and
    delete queries open every frame without a drag and change nothing."""
    panel = rig.panel
    rig.lib.load("presets", "lfo-breathe")
    frame(panel, "graph")
    st = ui_graph._state(panel)
    view = st["view"]
    n = len(rig.router.table.bindings)
    route = cables(view)[0]
    for subject in (("pin", f"mod:{route.ref.target}"), ("cable", route.id),
                    ("node", "lfo.1"), ("picker", "")):
        st["menu"] = subject
        imgui.new_frame()
        imgui.begin("menu")
        ui_graph.menu(panel, st, view)
        imgui.end()
        imgui.end_frame()
    st["note"] = graphview.HAND_NO_BASE
    for _ in range(2):
        frame(panel, "graph")
    assert len(rig.router.table.bindings) == n and st["pin_xy"]


def test_cable_near_follows_the_widgets_curve():
    """The drop test is the widget's curve: a point on the bezier between
    two pins is near, one on the straight chord where the curve is not is
    not, and a cable into the dropped node itself is passed over."""
    view = graphview.View(cables=[graphview.VCable("c", "out:a", "mod:x", kind="route")],
                          pins={"out:a": ("n1", "a"), "mod:x": ("n2", "x")})
    pins = {"out:a": (0.0, 0.0), "mod:x": (300.0, 200.0)}
    mid = graphview.bezier(pins["out:a"], pins["mod:x"])[8]
    assert graphview.cable_near(view, pins, mid) is view.cables[0]
    assert graphview.cable_near(view, pins, (40.0, 80.0)) is None
    assert graphview.cable_near(view, pins, mid, skip=("n2",)) is None


def test_cables_near_lists_the_cables_under_a_node_nearest_first():
    """A dragged node over cables: each within `NEAR` of its centre — or,
    given its size, through its box — with its distance from the centre,
    nearest first; one outside the box is not under it."""
    view = graphview.View(cables=[graphview.VCable("low", "out:a", "mod:x", kind="route"),
                                  graphview.VCable("high", "out:b", "mod:y", kind="route"),
                                  graphview.VCable("far", "out:c", "mod:z", kind="route")],
                          pins={"out:a": ("n1", "a"), "mod:x": ("n2", "x"),
                                "out:b": ("n1", "b"), "mod:y": ("n2", "y"),
                                "out:c": ("n1", "c"), "mod:z": ("n2", "z")})
    pins = {"out:a": (0.0, 8.0), "mod:x": (400.0, 8.0),
            "out:b": (0.0, -3.0), "mod:y": (400.0, -3.0),
            "out:c": (0.0, 300.0), "mod:z": (400.0, 300.0)}
    under = graphview.cables_near(view, pins, (200.0, 0.0))
    assert [c.id for _, c in under] == ["high", "low"]
    assert [round(d) for d, _ in under] == [3, 8]
    pins["out:a"], pins["mod:x"] = (0.0, 40.0), (400.0, 40.0)    # out of reach of the centre
    assert [c.id for _, c in graphview.cables_near(view, pins, (200.0, 0.0))] == ["high"]
    boxed = graphview.cables_near(view, pins, (200.0, 0.0), size=(100.0, 60.0))
    assert [c.id for _, c in boxed] == ["high", "low"]          # the box reaches it


def test_onto_words_names_a_cable_whose_port_is_gone():
    """A pin whose port its node no longer lists (`View.owner` gives None
    for it): the chooser and the drag's words name the node, never fail."""
    n1 = graphview.VNode("n1", "render", "Acid", ports=[])
    n2 = graphview.VNode("n2", "render", "Wobble", ports=[])
    view = graphview.View(nodes=[n1, n2],
                          cables=[graphview.VCable("c", "rout:n1", "rin:n2/gone", kind="render")],
                          pins={"rout:n1": ("n1", "out"), "rin:n2/gone": ("n2", "gone")})
    assert graphview.onto_words(view, view.cables[0]) == "Acid → Wobble"


def _two_cable_rig(rig):
    """`lookback → acid → output.all` and a free `wobble.2`, the page
    drawn once and its stubs placed by hand: lookback 0–100, acid
    300–400, output.all at 600."""
    from types import SimpleNamespace as NS

    from test_graphview import views
    from test_presets import put

    from hyperspace.outputs import Switches
    put(rig.lib.home, "Two", schema="hyperspace.preset/7", graph=_section(
        *FRAME0, ("lookback", "acid.image"), ("acid", "output.all.image"),
        nodes=[{"kind": "effect", "file": "wobble", "instance": 2}]))
    rig.lib.load("presets", "Two")
    gs = rig.lib.presets.graph
    rig.panel.renderer = NS(_graph=G.build_graph(views(Switches()), gs.spec.wiring(),
                                                   effects=("acid", "wobble.2")))
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    st["pin_xy"] = {}                       # only these three nodes' stubs are drawn
    for nid, x in {"render:lookback": 0.0, "render:acid": 300.0,
                   "render:output.all": 600.0}.items():
        st["pin_xy"][graphview.stub_out(nid)] = (x + 100.0, 0.0)
        st["pin_xy"][graphview.stub_in(nid)] = (x, 0.0)
    return st, st["view"], gs


def test_a_node_dropped_on_two_cables_as_near_asks_which(rig):
    """An effect let go with its centre equally near two picture cables is
    put on neither: a chooser opens naming both (`st["onto"]`), and the one
    picked takes it — its picture into the effect's ``image``, the
    effect's output on into the port the cable fed."""
    st, view, gs = _two_cable_rig(rig)
    # the two cables drawn over each other: a tie under the centre
    st["pin_xy"][graphview.stub_out("render:acid")] = (0.0, 0.0)
    st["pin_xy"][graphview.stub_in("render:output.all")] = (300.0, 0.0)
    assert ui_graph.dropped(rig.panel, view, "render:wobble.2", (150.0, 0.0)) is None
    assert G.run_back(gs.spec, "output.all.image") == ("acid",)
    held = st["onto"]
    assert held["node"] == "render:wobble.2" and len(held["cables"]) == 2
    words = {graphview.onto_words(view, c) for c in view.cables if c.id in held["cables"]}
    assert len(words) == 2 and all(" → " in w for w in words)
    after = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    assert ui_graph.put_onto(rig.panel, view, "render:wobble.2", after) is after
    assert G.run_back(gs.spec, "output.all.image") == ("acid", "wobble.2")
    assert st["onto"] is None


def test_the_drag_plan_lights_what_the_drop_will_do(rig):
    """`onto_plan` is what the drag lights and what the drop does: a free
    effect over a cable lights it as the one it goes onto; a wired effect
    without ⌘ lights nothing and says to hold ⌘; with ⌘ it lights the
    cable, fades its own and shows the join its chain closes with; a
    cable it may not go onto is refused in words."""
    st, view, gs = _two_cable_rig(rig)
    into = next(c for c in view.cables if c.dst_port == "rin:acid/image")
    out = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    free = ui_graph.onto_plan(rig.panel, view, "render:wobble.2", (500.0, 0.0))
    assert free["best"] == out.id and free["lit"] == [out.id] and not free["lift"]
    # a box across both cables lights both; the one nearest the centre is it
    both = ui_graph.onto_plan(rig.panel, view, "render:wobble.2", (420.0, 60.0), (400.0, 160.0))
    assert both["best"] == out.id and set(both["lit"]) == {out.id, into.id}
    assert ui_graph.drag_words(view, free).startswith("let go: ")
    assert free["hot"]                      # a free node: its border says a drop can land
    # over nothing: still hot, nothing lit, nothing said
    away = ui_graph.onto_plan(rig.panel, view, "render:wobble.2", (500.0, 900.0))
    assert away["hot"] and away["best"] is None and ui_graph.drag_words(view, away) == ""
    # acid, wired, without ⌘: not hot, and taught ⌘ from the drag's start —
    # here over only its own cable
    own = ui_graph.onto_plan(rig.panel, view, "render:acid", (200.0, 0.0))
    assert not own["hot"] and own["hint"] == "away" and own["best"] is None
    assert "hold ⌘ to lift" in ui_graph.drag_words(view, own)
    assert ui_graph.onto_plan(rig.panel, view, "render:acid", (200.0, 0.0), lift=True)["hot"]
    # wobble.2 wired in after acid; acid over wobble.2's cable to the output
    assert ui_graph.put_onto(rig.panel, view, "render:wobble.2", out) is out
    frame(rig.panel, "graph")
    view = st["view"]
    st["pin_xy"][graphview.stub_out("render:wobble.2")] = (800.0, 0.0)
    st["pin_xy"][graphview.stub_in("render:wobble.2")] = (700.0, 0.0)
    st["pin_xy"][graphview.stub_in("render:output.all")] = (1000.0, 0.0)
    last = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    still = ui_graph.onto_plan(rig.panel, view, "render:acid", (900.0, 0.0))
    assert still["hint"] == "over" and still["best"] is None and not still["lit"]
    assert "hold ⌘" in ui_graph.drag_words(view, still)
    assert ui_graph.dropped(rig.panel, view, "render:acid", (900.0, 0.0)) is None
    assert G.run_back(gs.spec, "output.all.image") == ("acid", "wobble.2")
    lifted = ui_graph.onto_plan(rig.panel, view, "render:acid", (900.0, 0.0), lift=True)
    assert lifted["lift"] and lifted["best"] == last.id
    assert "out of its chain" in ui_graph.drag_words(view, lifted)
    assert ui_graph.dropped(rig.panel, view, "render:acid", (900.0, 0.0), lift=True) is last
    assert G.run_back(gs.spec, "output.all.image") == ("wobble.2", "acid")
    # a geometry cable under a free effect: refused, in words
    frame(rig.panel, "graph")
    view = st["view"]
    geo = next(c for c in view.cables if c.type == graphview.GEOMETRY)
    st["pin_xy"][geo.src_port] = (0.0, 500.0)
    st["pin_xy"][geo.dst_port] = (400.0, 500.0)
    no = ui_graph.onto_plan(rig.panel, view, "render:wobble.2", (200.0, 500.0))
    if no is not None:                      # (wobble.2 is wired now: a lift asks)
        assert no["best"] is None
    no = ui_graph.onto_plan(rig.panel, view, "render:wobble.2", (200.0, 500.0), lift=True)
    assert no["best"] is None and geo.id in no["refused"] and ui_graph.drag_words(view, no)


def test_a_lifted_drag_draws_its_lit_cable_border_and_join(rig, monkeypatch):
    """The drag drawn (hand check 404 judges the look): the node the mouse
    went down on (`st["press"]`), dragged — its plan asked where the
    pointer has taken it, not where the editor says it is; the lit cable,
    a dimmed one, the dotted join and its outline drawn without error, the
    words said and no hover card over them; let go, the plan is gone."""
    from imgui_bundle import imgui
    st, view, _ = _two_cable_rig(rig)
    drawn = [c for c in view.cables if c.type == graphview.IMAGE]
    plan = {"node": "render:wobble.2", "hot": True, "lift": True, "lit": [drawn[0].id],
            "best": drawn[0].id, "tie": [], "refused": {}, "hint": ""}
    asked = []
    monkeypatch.setattr(ui_graph, "onto_plan", lambda *a, **k: asked.append(a[3]) or plan)
    monkeypatch.setattr(imgui, "is_mouse_down", lambda *a: True)
    monkeypatch.setattr(imgui, "is_mouse_clicked", lambda *a, **k: False)
    monkeypatch.setattr(imgui, "is_mouse_dragging", lambda *a: True)
    said = []
    monkeypatch.setattr(ui_graph, "_drag_tip", said.append)
    imgui.get_io().add_mouse_pos_event(400.0, 400.0)
    frame(rig.panel, "graph")
    st["press"] = ("render:wobble.2", (-1000.0, -1000.0), (0.0, 0.0))
    for _ in range(2):
        frame(rig.panel, "graph")
    assert st["onto_lit"] is plan and said and "out of its chain" in said[-1]
    # the pointer is far from where it went down: so is the centre asked of
    assert asked and asked[-1][0] > 500.0
    tips = []
    monkeypatch.setattr(ui_graph.ui, "tooltip", tips.append)
    ui_graph._hover(st, st["view"], rig.panel)
    assert tips == []
    monkeypatch.setattr(imgui, "is_mouse_down", lambda *a: False)
    frame(rig.panel, "graph")
    assert st["onto_lit"] is None and st["press"] is None
    imgui.get_io().add_mouse_pos_event(-1.0, -1.0)


def test_create_and_delete_open_only_in_the_typed_dispatch():
    """The canvas's create and delete queries live in `_create` / `_delete`
    alone, and an item is accepted or rejected only by a handler those
    dispatch to (`CREATE` / `DELETE`): the seam N4's handlers join."""
    tree = ast.parse((PKG / "ui_graph.py").read_text())
    where: dict[str, set[str]] = {}
    for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
                where.setdefault(c.func.attr, set()).add(fn.name)
    assert where["begin_create"] == {"_create"}
    assert where["query_new_link"] == {"new_link"}          # N4: `_create` asks it
    assert where["begin_delete"] == where["query_deleted_link"] == {"_delete"}
    # plan 28 N7: a drag onto a collapsed node's stub opens its port picker
    # (`_stub_drag`); a bundle's delete is refused in words (`delete_bundle`)
    assert where["accept_new_item"] == {"_value_drag", "_create_render", "_stub_drag"}
    assert where["accept_deleted_item"] == {"_value_cut", "_value_node_cut", "_voice_node_cut",
                                            "_delete_render_cable", "_delete_render_node"}
    assert where["reject_deleted_item"] <= {"_value_cut", "_unknown_cut", "_delete",
                                            "_fixture_node_cut", "_delete_render_cable",
                                            "_voice_node_cut", "_lane_cut",   # plan 31 G1
                                            "_delete_render_node", "delete_bundle",
                                            "delete_through",   # N9: a through wire
                                            "_feeds_cut"}   # plan 33 U: frame's picture
    assert where["reject_new_item"] <= {"_value_drag", "_create_render", "_stub_drag"}
    # plan 28 N4: the render types and kinds are in the dispatch, to N4's handlers
    assert set(graphview.RENDER_TYPES) <= set(ui_graph.CREATE)
    assert ui_graph.DELETE["render"] is ui_graph._delete_render_cable
    assert ui_graph.DELETE_NODE["render"] is ui_graph._delete_render_node


def test_a_route_from_the_canvas_is_a_performer_row_in_the_preset(rig):
    """What the canvas adds is the loaded preset's (a performer row): the
    preset is dirty, bindings.json is not written."""
    lib, table = rig.lib, rig.router.table
    lib.load("presets", "party-trip")
    assert not lib.is_dirty("presets")
    before = table.path.read_text() if table.path.exists() else None
    frame(rig.panel, "graph")
    b = ui_graph.connect(rig.panel, "out:lane:1", f"mod:{free_param(rig, centred=False).id}")
    assert b.op in MOD_OPS and not is_meta_row(b)
    assert lib.is_dirty("presets")
    assert (table.path.read_text() if table.path.exists() else None) == before


# ---------------------------------------------------------------- review round 1

def test_undoing_an_insert_is_one_step_the_modifier_gone_the_route_as_it_was(tmp_path):
    """A modifier inserted into a push route is one undo step: ⌘Z takes
    the modifier away and gives the route back its source and its rest
    (None: the source's own, every frame)."""
    from test_undo import boot, settle
    r = boot(tmp_path / "home")
    settle(r)
    table = r.table
    pid = next(p.id for p in r.reg if p.modulatable and not p.alias
               and table.owner(p.id) is None and not table.routes_to(p.id)
               and learn.centred_target(p))
    table.add(Binding("lane:4", pid, "push", 0.3))
    settle(r)
    r.undo.clear()
    panel = SimpleNamespace(router=r.router, reg=r.reg, library=r.lib, midi=None)
    view = ui_graph.view_of(panel)
    c = next(c for c in cables(view) if c.ref.target == pid)
    m = ui_graph.insert_modifier(panel, c, "smooth")
    row = table.owner(pid)
    assert row.source == m.address and row.rest == r.router.rest_of("lane:4")
    settle(r)
    assert len(r.undo.stack) == 1 and r.undo.undo()
    assert table.modifier(m.id) is None and not table.modifiers
    row = table.owner(pid)
    assert (row.source, row.op, row.value, row.rest) == ("lane:4", "push", 0.3, None)


def test_a_move_picks_up_the_performer_not_a_sleeping_route(rig):
    """A param with a sleeping route and a performer: a drag from its
    `mod` stub picks up the performer's cable (`Bindings.owner`)."""
    table = rig.router.table
    p = free_param(rig, centred=False)
    sleeper = Binding("lane:1", p.id, "position", 1.0, enabled=False)
    table.bindings.append(sleeper)
    performer = table.add(Binding("lane:2", p.id, "position", 1.0))
    to = free_param(rig, centred=False)
    e, _ = edit(rig)
    assert e.connect(f"mod:{p.id}", f"mod:{to.id}") is None
    assert performer.target == to.id and sleeper.target == p.id


def test_deleting_a_node_dispatches_by_kind(rig, monkeypatch):
    """Delete on a node goes by its kind (`DELETE_NODE`): a render or an
    output node is N4's (the camera refused in words: plan 35 G — the look's
    one since plan 43 C2), a
    kind not listed is the rig's; a macro node's delete goes through the
    table's `set_macros`, its label and subscribers with it."""
    from imgui_bundle import imgui_node_editor as ed
    monkeypatch.setattr(ed, "reject_deleted_item", lambda: None)
    st = {"note": ""}
    shape = graphview.VNode("render:camera", "render", "Camera")
    ui_graph.DELETE_NODE[shape.kind](rig.panel, st, None, shape)
    assert st["note"] == graphview.CAMERA_KEPT.format(label="Camera")
    assert ui_graph.DELETE_NODE["output"] is ui_graph._delete_render_node
    group = graphview.VNode("group:tempo", "group", "tempo")
    ui_graph.DELETE_NODE.get(group.kind, ui_graph._fixture_node_cut)(rig.panel, st, None, group)
    assert st["note"] == graphview.NOT_REMOVABLE.format(label="tempo")
    # plan 31 G1: an LFO and an envelope go through their bank; a lane
    # envelope is kept, said
    assert ui_graph.DELETE_NODE["lfo"] is ui_graph.DELETE_NODE["env"] is ui_graph._voice_node_cut
    env = graphview.VNode("env.2", "env", "env 2")
    ui_graph.DELETE_NODE[env.kind](rig.panel, st, None, env)
    assert st["note"] == graphview.LANE_ENV_KEPT.format(label="env 2")
    table = rig.router.table
    e, _ = edit(rig)
    e.show_macro("macro.5")
    e.connect("bus:macro.5", "base:view.bright")
    serial = table.macros_serial
    assert e.remove_node("macro.5") == []
    assert "macro.5" not in table.macros and table.macros_serial > serial


def test_a_render_edit_s_line_goes_at_the_next_edit_or_refusal(rig, monkeypatch):
    """`st["said"]` (the last render edit's words on the head) is cleared
    by the next value edit, landed or refused (`_settle`), and by any
    refusal, render or not; a render landing puts its own words back."""
    # the node editor's reject call segfaults with no editor context, which
    # only an earlier test in the same process happened to have made
    monkeypatch.setattr(ui_graph.ed, "reject_deleted_item", lambda: None)
    panel = rig.panel
    st = ui_graph._state(panel)
    landed = SimpleNamespace(said="wired hands → output.2.hands")

    def said_once():
        assert ui_graph._render_said(panel, landed, lambda e: None, st) is None
        assert st["said"] == landed.said and st["note"] == ""

    said_once()
    m = ui_graph.add_modifier(panel, "threshold")            # a value edit that lands
    assert m is not None and st["said"] == "" and st["note"] == ""
    said_once()
    ui_graph._settle(panel, graphview.Refusal("no such pin"))  # a value edit refused
    assert st["said"] == "" and st["note"] == "no such pin"
    said_once()
    assert ui_graph._render_said(panel, landed, lambda e: "a loop", st) == "a loop"
    assert st["said"] == "" and st["note"] == "a loop"
    said_once()
    ui_graph._fixture_node_cut(panel, st, None, graphview.VNode("lfo.1", "lfo", "LFO 1"))
    assert st["said"] == "" and st["note"] == graphview.NOT_REMOVABLE.format(label="LFO 1")


def test_a_selection_delete_keeps_its_first_refusal_s_words(rig, monkeypatch):
    """Delete on a selection of three: the camera (refused: the look's one), a
    modifier (it goes) and an LFO (refused) — the head keeps the first
    refusal's words for the frame, not wiped by the modifier's landing nor
    replaced by the LFO's. The next delete starts afresh: a landing alone
    clears the note."""
    from imgui_bundle import imgui_node_editor as ed
    panel, table = rig.panel, rig.router.table
    st = ui_graph._state(panel)
    m = ui_graph.add_modifier(panel, "threshold")
    shape = graphview.VNode("render:camera", "render", "Camera")
    lfo = graphview.VNode("lfo.1", "lfo", "LFO 1")
    mod = graphview.VNode(m.id, "modifier", "threshold")
    view = graphview.View(nodes=[shape, mod, lfo])
    queue: list[int] = []

    class Id:
        k = 0

        def id(self):
            return self.k

    def query(nk):
        if not queue:
            return False
        nk.k = queue.pop(0)
        return True

    monkeypatch.setattr(ed, "begin_delete", lambda: True)
    monkeypatch.setattr(ed, "end_delete", lambda: None)
    monkeypatch.setattr(ed, "NodeId", Id)
    monkeypatch.setattr(ed, "LinkId", Id)
    monkeypatch.setattr(ed, "query_deleted_node", query)
    monkeypatch.setattr(ed, "query_deleted_link", lambda lk: False)
    monkeypatch.setattr(ed, "accept_deleted_item", lambda *a: True)
    monkeypatch.setattr(ed, "reject_deleted_item", lambda: None)
    queue[:] = [ui_graph._id(st, f"n:{n.id}") for n in (shape, mod, lfo)]
    ui_graph._delete(panel, st, view)
    assert table.modifier(m.id) is None                     # the modifier went …
    assert st["note"] == graphview.CAMERA_KEPT.format(label="Camera")   # … the first words stay
    assert "held" not in st
    m2 = ui_graph.add_modifier(panel, "threshold")
    st["note"] = "an old refusal"
    queue[:] = [ui_graph._id(st, f"n:{m2.id}")]
    view.nodes.append(graphview.VNode(m2.id, "modifier", "threshold"))
    ui_graph._delete(panel, st, view)
    assert table.modifier(m2.id) is None and st["note"] == ""


# ---------------------------------------------------------------- plan 33 T6: the free graph
#
# (plan 35 T5: every section here is a wired frame in the new ids — the run
# is the look-back's picture through the effects into All outputs, and
# each of its wires is an ordinary wire)

def _section(*pairs, nodes=()):
    return {"frame": "wired", "nodes": list(nodes),
            "wires": [{"from": a, "to": b} for a, b in pairs]}


def free_rig(tmp_path, *pairs, nodes=(), undo_rig=False):
    """A headless rig over a scratch library with preset "Free" loaded —
    its graph section the wired frame of wires `pairs` and entries `nodes`
    (a `/6` file) — the section attached to a stub renderer, and an Edit on
    it whose undo steps are counted (`undo_rig`: test_undo's boot, its Undo
    real)."""
    from test_graph_json import Stub
    from test_presets import boot, put

    from hyperspace import undo
    from hyperspace.library import PRESETS
    if undo_rig:
        from test_undo import boot as undo_boot
        from test_undo import settle
        rig = undo_boot(tmp_path / "home")
        settle(rig)
    else:
        rig = boot(tmp_path)
    put(rig.home, "Free", schema="hyperspace.preset/7", graph=_section(*pairs, nodes=nodes))
    rig.lib.load(PRESETS, "Free")
    assert not [n for n in rig.presets.notes if n.startswith("graph")], rig.presets.notes
    stub = Stub()
    rig.presets.graph.attach(stub)
    pushed: list[str] = []
    if undo_rig:
        settle(rig)
        rig.undo.clear()

        def push(label):
            pushed.append(label)
            undo.push(label, load=True)
    else:
        push = pushed.append
    return rig, graphview.Edit(graph=rig.presets.graph, push=push), pushed


def wires_of(rig) -> set[tuple[str, str]]:
    return {(w.src, w.dst) for w in rig.presets.graph.spec.wires}


def run_of(rig) -> tuple[str, ...]:
    """The effects from the look-back into All outputs (the run, in wires)."""
    return G.run_back(rig.presets.graph.spec, "output.all.image")


def test_the_picker_adds_an_effect_unwired(tmp_path):
    """Plan 33 U: the picker's effect is the next instance, in the section
    and on no wire — it reaches nothing, so the canvas draws it faint with
    "reaches nothing" (`VNode.faint`), never idle — and a switch is added
    the same way (`switch`, its `select` declared); the run is untouched."""
    from test_graphview import views

    from hyperspace.outputs import Switches
    rig, e, pushed = free_rig(tmp_path, ("lookback", "acid.image"), ("acid", "output.all.image"))
    before = wires_of(rig)
    assert ("switch", None, "switch") in graphview.picker(e)
    assert e.add_node("effect", "acid") is None and e.added == "acid.2"
    spec = rig.presets.graph.spec
    assert G.EffectAt("acid", 2) in spec.effects and wires_of(rig) == before
    assert "acid.2" not in G.reaches(spec) and run_of(rig) == ("acid",)
    assert e.add_node("switch") is None and e.added == "switch"
    spec = rig.presets.graph.spec
    assert [s.name for s in spec.switches] == ["switch"] and "switch.select" in rig.reg
    assert wires_of(rig) == before and pushed == ["add acid.2", "add switch"]
    # on the canvas: faint, drawn, saying so
    g = G.build_graph(views(Switches()), spec.wiring(), effects=("acid", "acid.2"))
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    for nid in ("render:acid.2", "render:switch"):
        n = view.node(nid)
        assert n is not None and n.faint and not n.idle, nid
        assert graphview.summary(n)[0] == graphview.REACHES_NOTHING == "reaches nothing"
    assert not view.node("render:acid").faint


def test_insert_effect_on_a_render_cable(tmp_path):
    """"insert effect ▸ kaleido" on the cable `channel.a → shape.faces`: the
    next kaleido instance, wired `channel.a → kaleido.image`, `kaleido →
    shape.faces` in one landing; one undo puts the one wire back. Inserted
    on `lookback → output.all.image`, the run is that one effect."""
    from test_undo import settle

    rig, e, pushed = free_rig(tmp_path, ("lookback", "output.all.image"),
                              ("channel.a", "shape.faces"), undo_rig=True)
    cable = graphview.VCable("c", "rout:channel.a", "rin:shape/faces", graphview.IMAGE,
                             kind="render")
    # (R25: no wire, node or placement holds kaleido, so it is instance 1)
    assert e.insert_effect(cable, "kaleido") is None and e.added == "kaleido"
    got = wires_of(rig)
    assert ("channel.a", "kaleido.image") in got and ("kaleido", "shape.faces") in got
    assert ("channel.a", "shape.faces") not in got and len(pushed) == 1
    settle(rig)
    assert rig.undo.undo()
    assert ("channel.a", "shape.faces") in wires_of(rig)
    assert "kaleido" not in {x.name for x in rig.presets.graph.spec.effects}
    assert e.insert_effect(("lookback", "output.all.image"), "acid") is None
    assert run_of(rig) == ("acid",)
    assert ("lookback", "output.all.image") not in wires_of(rig)
    assert e.insert_effect(cable, "teapot") == "no teapot effect in this build"


def test_inserting_an_effect_no_one_holds_uses_instance_one_and_switches_it_on(tmp_path):
    """R25: an effect inserted on a cable, or added from the picker, that no
    wire, node or placement in the section holds is the file itself
    (instance 1), and it is switched on (`fx.<name>.on`) in the same
    landing — the first gesture shows something."""
    rig, e, pushed = free_rig(tmp_path, ("lookback", "output.all.image"))
    reg = rig.reg
    # (plan 36 T3: neither exists before a gesture names it)
    assert "fx.kaleido.on" not in reg and "fx.wobble.on" not in reg
    assert e.insert_effect(("lookback", "output.all.image"), "kaleido") is None
    assert e.added == "kaleido" and run_of(rig) == ("kaleido",)
    assert reg["fx.kaleido.on"].value is True
    assert pushed == ["insert kaleido into lookback → output.all.image"]
    assert e.add_node("effect", "wobble") is None and e.added == "wobble"
    assert reg["fx.wobble.on"].value is True
    assert "wobble" in {x.name for x in rig.presets.graph.spec.effects}


def test_a_second_insert_of_the_same_file_takes_instance_two(tmp_path):
    """R25: the run holds kaleido, so the next kaleido inserted is
    `kaleido.2`, and it is switched on too."""
    rig, e, _ = free_rig(tmp_path, ("lookback", "output.all.image"))
    assert e.insert_effect(("lookback", "output.all.image"), "kaleido") is None
    assert e.added == "kaleido"
    assert e.insert_effect(("kaleido", "output.all.image"), "kaleido") is None
    assert e.added == "kaleido.2"
    assert run_of(rig) == ("kaleido", "kaleido.2")
    assert rig.reg["fx.kaleido.2.on"].value is True and rig.reg["fx.kaleido.on"].value is True


def test_undo_of_an_insert_restores_the_on_value_too(tmp_path):
    """R25: the insert and its `on` are one undo step — one undo takes the
    effect off the cable and puts `fx.kaleido.on` back off."""
    from test_undo import settle

    rig, e, _ = free_rig(tmp_path, ("lookback", "output.all.image"), undo_rig=True)
    assert "fx.kaleido.on" not in rig.reg            # (plan 36 T3: not in the section)
    assert e.insert_effect(("lookback", "output.all.image"), "kaleido") is None
    assert rig.reg["fx.kaleido.on"].value is True
    settle(rig)
    assert len(rig.undo.stack) == 1 and rig.undo.undo()
    assert "fx.kaleido.on" not in rig.reg           # (gone with its node: plan 36 T3)
    assert run_of(rig) == () and wires_of(rig) == {("lookback", "output.all.image")}


def test_switch_over_the_channels_wires_all_eight_and_keeps_the_channel(tmp_path):
    """R28: the picker's "switch over the channels ▸ faces media" is one
    landing: a new switch, `channel.a … h → in1 … in8`, the switch into
    `pattern.media` in place of what fed it, and `select` the channel that
    fed it (c: 3). "▸ backdrop" on a backdrop fed by nothing is a second
    switch at select 1."""
    rig, e, pushed = free_rig(tmp_path, ("lookback", "output.all.image"),
                              ("channel.c", "pattern.media"))
    items = graphview.picker(e)
    assert ("channels", "pattern.media", "faces media") in items
    assert ("channels", "backdrop.image", "backdrop") in items
    assert e.switch_channels("pattern.media") is None and e.added == "switch"
    got = wires_of(rig)
    for i, c in enumerate("abcdefgh", 1):
        assert (f"channel.{c}", f"switch.in{i}") in got
    assert ("switch", "pattern.media") in got and ("channel.c", "pattern.media") not in got
    assert rig.reg["switch.select"].value == 3 and len(pushed) == 1
    assert e.switch_channels("backdrop.image") is None and e.added == "switch.2"
    assert ("switch.2", "backdrop.image") in wires_of(rig)
    assert rig.reg["switch.2.select"].value == 1 and len(pushed) == 2
    assert e.switch_channels("output.1.image") == (
        "a switch over the channels goes into pattern.media or backdrop.image")


def test_undo_of_switch_over_the_channels_puts_the_channel_back(tmp_path):
    """R28: the switch, its nine wires and its `select` are one undo step:
    one undo leaves `channel.c → pattern.media` and no switch."""
    from test_undo import settle
    rig, e, _ = free_rig(tmp_path, ("lookback", "output.all.image"),
                         ("channel.c", "pattern.media"), undo_rig=True)
    assert e.switch_channels("pattern.media") is None
    assert rig.reg["switch.select"].value == 3
    settle(rig)
    assert len(rig.undo.stack) == 1 and rig.undo.undo()
    assert wires_of(rig) == {("lookback", "output.all.image"), ("channel.c", "pattern.media")}
    assert rig.presets.graph.spec.switches == () and "switch.select" not in rig.reg


def test_the_runs_cables_are_ordinary_wires(tmp_path):
    """Plan 35 G (the owner's refusal of `frame → fx` retired with R20):
    a cable of the run deletes as any wire — the effect it left stays,
    named by its other wire, or (R21) by its entry once it has none, drawn
    faint; the effect deleted goes with its wires; deleting a wire the
    section does not have is the one refusal left."""
    rig, e, pushed = free_rig(tmp_path, ("lookback", "acid.image"), ("acid", "wobble.image"),
                              ("wobble", "output.all.image"))
    assert e.unwire("acid", "wobble.image") is None
    assert wires_of(rig) == {("lookback", "acid.image"), ("wobble", "output.all.image")}
    assert e.unwire("lookback", "acid.image") is None
    assert G.EffectAt("acid", 1) in rig.presets.graph.spec.effects     # (R21: kept, faint)
    assert "acid" in graphview.unreached(rig.presets.graph.spec)
    assert e.drop_node("render:acid") is None and e.said == "acid deleted"
    assert G.EffectAt("acid", 1) not in rig.presets.graph.spec.effects
    n = len(pushed)
    assert e.unwire("lookback", "output.all.image") == graphview.NO_SUCH_WIRE.format(
        wire="lookback → output.all.image")
    assert len(pushed) == n
    # a run effect deleted closes the chain over it
    assert e.insert_effect(("wobble", "output.all.image"), "acid") is None
    assert e.drop_node("render:acid") is None
    assert wires_of(rig) == {("wobble", "output.all.image")}


def test_reordering_the_run_is_rewiring(tmp_path):
    """`lookback → acid → wobble → output.all`: acid dragged onto the cable
    `wobble → output.all.image` — out of its place, the chain closed over
    it, then in after wobble — is one landing, one undo step: the run is
    wobble, acid."""
    rig, e, pushed = free_rig(tmp_path, ("lookback", "acid.image"), ("acid", "wobble.image"),
                              ("wobble", "output.all.image"))
    assert e.place_effect(("wobble", "output.all.image"), "acid") is None
    assert run_of(rig) == ("wobble", "acid")
    assert pushed == ["move acid onto wobble → output.all.image"]
    assert e.place_effect(("wobble", "acid.image"), "acid") == "acid is on that cable already"


FRAME0 = (("shape", "scene.geometry"), ("scene", "lookback.image"))


def test_dropping_a_free_effect_on_the_run_inserts_it(rig):
    """A free effect node (`wobble.2`: in the section, no cable in or out)
    let go on the canvas over the cable `lookback → output.all.image` is
    inserted into it (`ui_graph.dropped`, as a modifier is into a value
    cable) — it is in the run; one let go over nothing stays where it is."""
    from types import SimpleNamespace as NS

    from test_graphview import views
    from test_presets import put

    from hyperspace.outputs import Switches
    put(rig.lib.home, "Free", schema="hyperspace.preset/7", graph=_section(
        *FRAME0, ("lookback", "output.all.image"),
        nodes=[{"kind": "effect", "file": "wobble", "instance": 2}]))
    rig.lib.load("presets", "Free")
    gs = rig.lib.presets.graph
    rig.panel.renderer = NS(_graph=G.build_graph(views(Switches()), gs.spec.wiring(),
                                                   effects=("wobble", "wobble.2")))
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    view = st["view"]
    assert view.node("render:wobble.2").faint and view.node("render:frame") is None
    cable = next(c for c in view.cables
                 if (c.src_port, c.dst_port) == ("rout:lookback", "rin:output.all/image"))
    st["pin_xy"].update({graphview.stub_out("render:lookback"): (0.0, 0.0),
                         graphview.stub_in("render:output.all"): (400.0, 0.0)})
    assert ui_graph.dropped(rig.panel, view, "render:wobble.2", (900.0, 900.0)) is None
    assert G.run_back(gs.spec, "output.all.image") == ()
    assert ui_graph.dropped(rig.panel, view, "render:wobble.2", (200.0, 0.0)) is cable
    assert G.run_back(gs.spec, "output.all.image") == ("wobble.2",)


def test_an_instance_one_effect_taken_out_of_the_run_stays_faint(tmp_path):
    """R21 (row 349): `acid` unwired from both sides is kept in the section
    — `{"kind": "effect", "file": "acid"}`, on no wire — drawn faint,
    "reaches nothing"; saved, the preset is `/6` (plan 35: an edited frame
    no older schema says); undo puts its wires back."""
    import json

    from test_graphview import views
    from test_undo import settle

    from hyperspace.outputs import Switches
    rig, e, pushed = free_rig(tmp_path, ("lookback", "acid.image"), ("acid", "output.all.image"),
                              undo_rig=True)
    rig.reg["fx.acid.on"].set(True)
    settle(rig)
    rig.undo.clear()
    assert e.unwire("acid", "output.all.image") is None
    assert e.unwire("lookback", "acid.image") is None and len(pushed) == 2
    spec = rig.presets.graph.spec
    assert run_of(rig) == () and wires_of(rig) == set()
    assert G.EffectAt("acid", 1) in spec.effects
    assert {"kind": "effect", "file": "acid"} in rig.presets.graph.free_doc()["nodes"]
    g = G.build_graph(views(Switches()), spec.wiring(), effects=("acid",))
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    n = view.node("render:acid")
    assert n is not None and n.faint and not n.idle
    assert graphview.summary(n)[0] == graphview.REACHES_NOTHING
    doc = json.loads(rig.presets.save_as("Out").read_text())
    assert doc["schema"] == "hyperspace.preset/10"
    assert {"kind": "effect", "file": "acid"} in doc["graph"]["nodes"]
    settle(rig)
    assert rig.undo.undo()           # (both unwires inside one settle: one step)
    assert wires_of(rig) == {("lookback", "acid.image"), ("acid", "output.all.image")}
    # wired in again, it is named by its wires alone
    rig2, e2, _ = free_rig(tmp_path / "again", ("lookback", "acid.image"),
                           ("acid", "output.all.image"))
    assert e2.unwire("lookback", "acid.image") is None
    assert e2.unwire("acid", "output.all.image") is None
    assert e2.wire("rout:lookback", "rin:output.all/image") is None
    assert e2.place_effect(("lookback", "output.all.image"), "acid") is None
    assert rig2.presets.graph.spec.to_json()["nodes"] == [{"kind": "hands", "laid": "over"}]


def test_an_unwired_instance_one_saves_with_its_entry_on_or_off(tmp_path):
    """R26 (refines R21), in the wired frame: party-trip with `huecycle`
    taken out of its run on GRAPH (its wires gone, R21's entry keeping it,
    faint) — on or off, the save is `/6` (row 394) with the entry kept and
    the run as wired, so a reload finds it where it was left."""
    import json
    rig, e, _ = wired_rig(tmp_path, slug="party-trip")
    assert run_of(rig) == ("plasma", "kaleido", "zoomblur", "huecycle")
    assert e.unwire("huecycle", "output.all.image") is None
    assert e.unwire("zoomblur", "huecycle.image") is None
    assert e.wire("rout:zoomblur", "rin:output.all/image") is None
    assert run_of(rig) == ("plasma", "kaleido", "zoomblur")
    assert {"kind": "effect", "file": "huecycle"} in rig.presets.graph.spec.to_json()["nodes"]
    rig.reg["fx.huecycle.on"].set(True)
    for name, on in (("On", True), ("Off", False)):
        rig.reg["fx.huecycle.on"].set(on)
        doc = json.loads(rig.presets.save_as(name).read_text())
        assert doc["schema"] == "hyperspace.preset/10", name
        assert {"kind": "effect", "file": "huecycle"} in doc["graph"]["nodes"], name
        assert G.run_back(G.read_graph(doc["graph"]), "output.all.image") == (
            "plasma", "kaleido", "zoomblur"), name


def test_an_unwired_instance_one_round_trips():
    """R21: an unplaced instance 1 — no `instance` key, or `instance: 1` —
    is read, written back as `{"kind": "effect", "file": …}` and read again
    the same; D1's placed forms are as they were."""
    for entry in ({"kind": "effect", "file": "acid"},
                  {"kind": "effect", "file": "acid", "instance": 1}):
        section = {"nodes": [entry], "wires": [{"from": "frame", "to": "fx.image"}]}
        spec = G.read_graph(section, effects={"acid"})
        assert spec.notes == () and spec.effects == (G.EffectAt("acid", 1),)
        out = spec.to_json()
        assert out["nodes"] == [{"kind": "effect", "file": "acid"}]
        assert G.read_graph(out, effects={"acid"}) == spec
        assert "acid" not in G.reaches(spec) and spec.effect_counts() == {}
    placed = {"nodes": [{"kind": "effect", "file": "palette", "after": "hands"}]}
    assert G.read_graph(placed).to_json() == placed


def test_a_sink_loop_drag_is_refused_in_words(tmp_path):
    """Plan 34 L (Review Focus 2), in a wired frame: the canvas's dry run
    reads the loop at read, so `scene → shape.faces` goes red with words —
    never green, then dormant — and nothing changes. With a delay declared,
    `delay → shape.faces` lands (plan 35 G: only types and loops refuse)."""
    rig, e, pushed = free_rig(tmp_path, *FRAME0, ("lookback", "output.all.image"))
    before = rig.presets.graph.spec.to_json()
    why = e.refusal("rout:scene", "rin:shape/faces")
    # (R5: every wire on the loop is refused, the first named)
    assert isinstance(why, str) and "a loop through the faces" in why and "delay" in why
    assert rig.presets.graph.spec.to_json() == before and pushed == []
    assert e.add_node("delay") is None and e.added == "delay"
    assert graphview.render_wire(e, "rout:delay", "rin:shape/faces", dry=True) is None


def test_a_plain_loop_drag_points_at_a_delay(tmp_path):
    """Plan 34 T5 (row 359): a wired frame's other loop (`wobble → acid.aux`
    with `acid → wobble` already wired) is refused in `LOOP_PLAIN`'s words,
    which point at a delay; wired through one it lands, the section read
    with no notes."""
    rig, e, _ = free_rig(
        tmp_path, *FRAME0, ("lookback", "acid.image"), ("acid", "wobble.image"),
        ("wobble", "output.all.image"),
        nodes=[{"kind": "effect", "file": "acid"}, {"kind": "effect", "file": "wobble"}])
    before = rig.presets.graph.spec.to_json()
    why = e.refusal("rout:wobble", "rin:acid/aux")
    assert isinstance(why, str) and why.startswith("wire ") and "that makes a loop (" in why
    assert why.endswith(": wire it through a delay for last frame's picture")
    assert rig.presets.graph.spec.to_json() == before
    assert e.add_node("delay") is None
    assert graphview.render_wire(e, "rout:wobble", "rin:delay/image") is None
    assert graphview.render_wire(e, "rout:delay", "rin:acid/aux") is None
    spec = rig.presets.graph.spec
    assert not spec.notes
    assert any((w.src, w.dst) == ("delay", "acid.aux") for w in spec.wires)


def test_dragging_a_run_member_onto_another_cable_moves_it(rig, monkeypatch):
    """R22: an effect already wired (`acid` in `lookback → acid → wobble →
    output.all`) let go on another picture cable (`wobble →
    output.all.image`) is moved there in one undo step — the run is wobble,
    acid; let go on its own cables, or on nothing, it stays where it is."""
    from types import SimpleNamespace as NS

    from test_graphview import views
    from test_presets import put

    from hyperspace import undo as undo_mod
    from hyperspace.outputs import Switches
    put(rig.lib.home, "Run", schema="hyperspace.preset/7", graph=_section(
        ("lookback", "acid.image"), ("acid", "wobble.image"), ("wobble", "output.all.image")))
    rig.lib.load("presets", "Run")
    gs = rig.lib.presets.graph
    rig.panel.renderer = NS(_graph=G.build_graph(views(Switches()), gs.spec.wiring(),
                                                   effects=("acid", "wobble")))
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    view = st["view"]
    pushed = []
    monkeypatch.setattr(undo_mod, "push",
                        lambda label, load=False: pushed.append(label))
    xy = {"render:lookback": 0.0, "render:acid": 300.0, "render:wobble": 600.0,
          "render:output.all": 900.0}
    for nid, x in xy.items():
        st["pin_xy"][graphview.stub_out(nid)] = (x + 100.0, 0.0)
        st["pin_xy"][graphview.stub_in(nid)] = (x, 0.0)
    # on its own cables (lookback → acid, acid → wobble), and on nothing: no change
    for at in ((200.0, 0.0), (500.0, 900.0)):
        assert ui_graph.dropped(rig.panel, view, "render:acid", at, lift=True) is None
    # on another cable without ⌘ (2026-10-29): only moved on the canvas
    assert ui_graph.dropped(rig.panel, view, "render:acid", (800.0, 0.0)) is None
    assert G.run_back(gs.spec, "output.all.image") == ("acid", "wobble")
    assert pushed == []
    cable = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    assert ui_graph.dropped(rig.panel, view, "render:acid", (800.0, 0.0), lift=True) is cable
    assert G.run_back(gs.spec, "output.all.image") == ("wobble", "acid")
    assert pushed == ["move acid onto wobble → output.all.image"]


def test_the_strip_has_no_order_or_onto(tmp_path, monkeypatch):
    """Plan 33 U: the strip (the FX page's open effect, GRAPH's side pane)
    draws no order slider and no ONTO chips — an effect's place is its
    wires — and no faces line; on, mix, speed and blend stay."""
    from test_fx import PageRig

    from hyperspace import ui_fx
    page = PageRig(tmp_path, monkeypatch)
    try:
        name = page.panel.fx_selected = "warp"
        page.frame()
        ids = set(page.rects)
        assert f"fx.{name}.mix" in ids and f"fx.{name}.blend" in ids
        assert not [k for k in ids if k.endswith(".order") or k.startswith("onto.")], ids
        assert not hasattr(ui_fx, "FAINT_FACES") and not hasattr(ui_fx, "ORDER_W")
    finally:
        page.close()


# ---------------------------------------------------------------- Route from ▸ (the owner, 2026-10-24)
#
# The param menu's "Route from ▸": every LFO and envelope of the banks, then
# "new LFO" / "new envelope" — a pick is the cable a drag on GRAPH makes
# (`Edit.connect_value` from the voice's ``out:`` pin into the param's
# ``mod`` stub), its Ask, its Refusal and its undo step.

@pytest.fixture()
def banks():
    """test_plan31_wiring's rig (four LFOs, five envelopes, the router
    stepping them) with a real undo carrying the banks' membership, and a
    bare panel over it, as test_graph_seq's page."""
    from test_plan31_wiring import rig as wiring_rig

    from hyperspace import undo
    r = wiring_rig()
    u = undo.Undo(r.reg, r.router.table, banks=lambda: r.router._banks())
    undo.install(u)
    t = [0.0]

    def settle():
        for _ in range(3):
            t[0] += 1.0
            u.tick(t[0])

    panel = SimpleNamespace(router=r.router, reg=r.reg, library=None, midi=None,
                            learn=None)
    settle()
    yield SimpleNamespace(r=r, u=u, settle=settle, panel=panel)
    undo.install(None)


def drawn_route_from(panel, p, monkeypatch, pick=None):
    """Draw the Route from submenu of `p` with imgui's calls recorded:
    (the submenus opened, the items as (label, checked, enabled)); `pick`
    is the label of the item that is clicked."""
    opened, items = [], []

    def begin_menu(label, *a, **k):
        opened.append(label)
        return True

    def menu_item(label, shortcut="", selected=False, enabled=True):
        items.append((label.split("##")[0], bool(selected), bool(enabled)))
        return (label.split("##")[0] == pick, selected)

    def menu_item_simple(label, shortcut="", selected=False, enabled=True):
        return menu_item(label, shortcut, selected, enabled)[0]

    monkeypatch.setattr(imgui, "begin_menu", begin_menu)
    monkeypatch.setattr(imgui, "end_menu", lambda: None)
    monkeypatch.setattr(imgui, "menu_item", menu_item)
    monkeypatch.setattr(imgui, "menu_item_simple", menu_item_simple)
    monkeypatch.setattr(imgui, "separator", lambda: None)
    try:
        ui_graph.route_from_menu(panel, p)
    finally:
        monkeypatch.undo()
    return opened, items


VOICES = ["LFO 1", "LFO 2", "LFO 3", "LFO 4", "env 1", "env 2", "env 3", "env 4", "env 5"]
MACROS = [f"macro {k}" for k in range(1, 9)]


def test_route_from_lists_the_lfos_and_envelopes_on_a_modulatable_param(banks, rig,
                                                                         monkeypatch):
    """On a modulatable param the submenu is one submenu per kind (the
    owner, 2026-10-28): LFO ▸ every LFO by its bank's label then new LFO,
    envelope ▸ the envelopes then new envelope — and, where the rig has
    macros, macro ▸ (`test_route_from_lists_the_macros…`); this rig has
    none. A trigger and a param no lane may drive have none. The shared
    param menu (`Panel._ctx_learn`) draws it — on fx.glimmer.mix, between
    the Learn items and Learn sink."""
    panel, reg = banks.panel, banks.r.reg
    opened, items = drawn_route_from(panel, reg["t.x"], monkeypatch)
    assert opened == [ui_graph.ROUTE_FROM, "LFO", "envelope"]
    assert [i[0] for i in items] == VOICES[:4] + ["new LFO"] + VOICES[4:] + ["new envelope"]
    assert all(enabled and not checked for _, checked, enabled in items)
    assert list(ui_graph.route_from_items(panel, reg["t.x"])) == ["lfo", "env"]
    assert ui_graph.route_from_items(panel, reg["t.hit"]) is None          # a trigger
    reg.continuous("t.fixed", "fixed", lambda: 0.0, lambda v: None, group="view",
                   modulatable=False)
    assert ui_graph.route_from_items(panel, reg["t.fixed"]) is None
    assert drawn_route_from(panel, reg["t.fixed"], monkeypatch) == ([], [])
    # the shared menu: the panel's own Learn items draw it, on the FX page's glimmer
    from hyperspace.learn import Learn
    p = rig.panel
    p.learn = Learn(rig.reg, rig.router.table, lane=rig.router.lane)
    rig.router.use_lfos(p.lfos, p.clock)
    seen = []
    real = ui_graph.route_from_menu
    monkeypatch.setattr(ui_graph, "route_from_menu",
                        lambda pan, q: (seen.append(q.id), real(pan, q)))
    monkeypatch.setattr(imgui, "begin_menu", lambda label, *a: False)
    monkeypatch.setattr(imgui, "menu_item_simple", lambda label, *a, **k: False)
    # (plan 36 T3: an effect's params exist where the graph names it)
    gs = rig.panel.library.presets.graph
    spec = G.read_graph({**gs.spec.to_json(), "nodes": [
        *gs.spec.to_json()["nodes"], {"kind": "effect", "file": "glimmer"}]})
    gs.land(spec, spec.to_json())
    g = rig.reg["fx.glimmer.mix"]
    imgui.new_frame()
    imgui.begin("menu")
    p._ctx_learn(g, g)
    p._ctx_learn(rig.reg["view.bmp_alpha"], rig.reg["view.bmp_alpha"])
    imgui.end()
    imgui.end_frame()
    monkeypatch.undo()
    assert seen == ["fx.glimmer.mix", "view.bmp_alpha"]
    assert ui_graph.route_from_items(p, rig.reg["view.bmp_alpha"]) is None   # an alias
    sections = ui_graph.route_from_items(p, g)
    assert list(sections) == ["lfo", "env", "macro"]
    assert [i[0] for i in sections["lfo"]][:4] == VOICES[:4]
    assert [i[0] for i in sections["macro"]] == MACROS


def test_route_from_lists_the_macros_on_a_param_a_base_subscriber_may_name(rig, monkeypatch):
    """macro ▸ (the owner, 2026-10-28: the Route from menu "should
    probably include the macros as well"): the rig's eight knobs by label
    (`macro_label`: ROUTING's label, else "macro 3"), one already setting
    the param checked — on a persisted performance param, modulatable or
    not (a base subscriber is no route), never on a macro or a session
    param (`routing.base_refusal`, plan 13 D9)."""
    from hyperspace.routing import Macro, Sub

    panel, reg, table = rig.panel, rig.reg, rig.router.table
    table.macros["macro.3"] = Macro("Test", [Sub(base="view.bright", lo=0.2, hi=1.0)])
    opened, items = drawn_route_from(panel, reg["view.bright"], monkeypatch)
    assert opened == [ui_graph.ROUTE_FROM, "LFO", "envelope", "macro"]
    macros = items[-8:]
    assert [m[0] for m in macros] == MACROS[:2] + ["Test"] + MACROS[3:]
    assert [m[0] for m in macros if m[1]] == ["Test"]                     # checked
    # a param no lane may drive still takes a macro: only macro ▸
    fixed = reg.continuous("view.t_fixed", "fixed", lambda: 0.0, lambda v: None,
                           group="view", modulatable=False)
    assert list(ui_graph.route_from_items(panel, fixed)) == ["macro"]
    assert drawn_route_from(panel, fixed, monkeypatch)[0] == [ui_graph.ROUTE_FROM, "macro"]
    # never on a macro, nor on a session param (the BPM)
    assert "macro" not in (ui_graph.route_from_items(panel, reg["macro.1"]) or {})
    assert "macro" not in (ui_graph.route_from_items(panel, reg["tempo.bpm"]) or {})


def test_route_from_a_macro_makes_the_base_subscriber_a_graph_cable_makes(rig, monkeypatch):
    """A macro picked: the cable from its bus into the param's base stub
    (`Edit.connect_value` → `subscribe`) — a base subscriber from where
    the param sits to the top of its fader (row 537), the idle macro
    labelled "macro 2" as the canvas's picker labels it, in one undo step;
    then the macro's knob moves the param (`Router.follow_macros`) — the
    owner's "Tracer Macro Test" symptom, where from = to moved nothing.
    A second pick is checked and does nothing."""
    from hyperspace import undo

    panel, reg, table, router = rig.panel, rig.reg, rig.router.table, rig.router
    u = undo.Undo(reg, table)
    undo.install(u)
    try:
        p = reg["view.bright"]
        p.set_norm(0.4)
        assert "macro.2" not in table.macros
        drawn_route_from(panel, p, monkeypatch, pick="macro 2")
        m = table.macros["macro.2"]
        assert m.label == "macro 2" and len(m.subs) == 1
        s = m.subs[0]
        assert (s.base, s.lo, s.hi) == ("view.bright", pytest.approx(0.4), 1.0)
        # the knob has a throw from the day it lands
        knob = reg["macro.2"]
        for v, at in ((0.0, 0.4), (0.5, 0.7), (1.0, 1.0)):
            knob.set_norm(v)
            router.follow_macros()
            reg.apply()
            assert p.norm == pytest.approx(at), v
        # checked now: a click does nothing
        _, items = drawn_route_from(panel, p, monkeypatch, pick="macro 2")
        assert ("macro 2", True, True) in items and len(table.macros["macro.2"].subs) == 1
        # one step takes the label and the subscriber back
        t = 1.0
        for _ in range(3):
            u.tick(t)
            t += 1.0
        assert u.undo() and u.status.endswith("connect macro.2 → view.bright")
        assert table.macros.get("macro.2") is None or table.macros["macro.2"].empty
    finally:
        undo.install(None)


def test_route_from_an_lfo_makes_the_route_a_graph_cable_makes(banks, monkeypatch):
    """LFO 1 picked on a free param: one route lfo… → it, the row
    `Edit.connect_value` makes for the same pins, as one undo step."""
    r, panel, table = banks.r, banks.panel, banks.r.router.table
    before = list(table.bindings)
    drawn_route_from(panel, r.reg["t.x"], monkeypatch, pick="LFO 1")
    new = [b for b in table.bindings if b not in before]
    assert len(new) == 1 and new[0].source.startswith("lfo:") and new[0].target == "t.x"
    # the same pins through the GRAPH page's edit, on a twin table
    from hyperspace.routing import Bindings, Router
    twin = Router(r.reg, Bindings(before))
    twin.use_lfos(r.lfos, r.clock)
    e = graphview.Edit(twin.table, r.reg, twin, graphview.build(twin.table, r.reg, twin))
    src = f"out:{r.router.address('lfo', 0)}"
    made = e.connect_value(src, "mod:t.x")
    assert (new[0].source, new[0].target, new[0].op, new[0].value) == (
        made.source, made.target, made.op, made.value)
    banks.settle()
    assert banks.u.undo() and list(table.bindings) == before     # one step takes it back
    assert banks.u.status.endswith(f"connect {src.partition(':')[2]} → t.x")   # GRAPH's label


def test_route_from_on_a_taken_param_asks_replace_or_keep(banks, monkeypatch):
    """The param already has a performer: the pick holds ROUTING's
    Replace / Keep prompt and the table is untouched until it is answered;
    Replace puts the LFO there."""
    r, panel, table = banks.r, banks.panel, banks.r.router.table
    old = Binding("lane:2", "t.x", "position", 1.0)
    table.add(old)
    before = list(table.bindings)
    drawn_route_from(panel, r.reg["t.x"], monkeypatch, pick="LFO 2")
    held = ui_routing._state(panel)["prompt"]
    assert held is not None and held[0] is old and held[1].source == r.router.address("lfo", 1)
    assert list(table.bindings) == before
    ui_routing.answer(panel, True)
    assert table.owner("t.x").source == r.router.address("lfo", 1) and old not in table.bindings


def test_route_from_new_lfo_adds_one_and_routes_it(banks, monkeypatch):
    """"new LFO": the bank grows by one and the new LFO drives the param —
    GRAPH's picker (`add_voice`) then its cable, in one frame, so one undo
    step (the picker's "add LFO") takes both back. At the cap the item is
    greyed with the bank's words."""
    r, panel, table = banks.r, banks.panel, banks.r.router.table
    before, ids = list(table.bindings), r.lfos.ids()
    drawn_route_from(panel, r.reg["t.x"], monkeypatch, pick="new LFO")
    assert r.lfos.ids() == ids + [5]
    owner = table.owner("t.x")
    assert owner is not None and r.router.lane(owner.source) == ("lfo", 4)
    banks.settle()
    assert banks.u.undo() and banks.u.status.endswith("add LFO")
    assert r.lfos.ids() == ids and list(table.bindings) == before
    # full: greyed, in the bank's words, and a click does nothing
    while r.lfos.can_add():
        r.lfos.add()
    _, items = drawn_route_from(panel, r.reg["t.x"], monkeypatch)
    full = graphview.BANK_FULL.format(k=r.lfos.MAX, what="LFOs")
    assert (full, False, False) in items


def test_an_lfo_already_driving_is_checked(banks, monkeypatch):
    """The LFO whose route lands on the param is drawn checked; a click on
    it does nothing — no prompt, no new row."""
    r, panel, table = banks.r, banks.panel, banks.r.router.table
    table.add(Binding(r.router.address("lfo", 2), "t.x", "position", 1.0))
    before = list(table.bindings)
    _, items = drawn_route_from(panel, r.reg["t.x"], monkeypatch, pick="LFO 3")
    assert [label for label, checked, _ in items if checked] == ["LFO 3"]
    assert list(table.bindings) == before and ui_routing.prompt(panel) is None


# ---------------------------------------------------------------- an envelope's row
# The owner, 2026-10-24: "the envelopes have no way for me to set a
# baseline … they all reduce the base to 0 in between fires no matter what I
# set the base to be." An envelope rests at 0, so `row_for` made it the
# `position` fader at 1: the param sat at its minimum between fires.

def _glimmer_mix(r, base: float = 0.4):
    box = SimpleNamespace(v=0.0)
    p = r.reg.continuous("fx.glimmer.mix", "mix", lambda: box.v,
                         lambda v: setattr(box, "v", float(v)), group="fx")
    p.set(base)
    return p, box


def test_an_envelope_route_is_a_push_about_the_base(banks, monkeypatch):
    from test_plan31_wiring import frame, one_shot

    r, panel, table = banks.r, banks.panel, banks.r.router.table
    p, box = _glimmer_mix(r)
    row = learn.row_for("env:0", p)
    assert (row.op, row.rest) == ("push", None) and row.value == pytest.approx(0.6)
    # the push's depth never drops below PUSH_DEPTH, however high the base
    p.set(0.9)
    assert learn.row_for("env:0", p).value == pytest.approx(learn.PUSH_DEPTH)
    p.set(0.4)
    # Route from ▸ env 1 makes that row (`connect_value` → `route_for`)
    drawn_route_from(panel, p, monkeypatch, pick="env 1")
    made = table.owner(p.id) or next(b for b in table.bindings if b.target == p.id)
    assert made.source.startswith("env:") and made.op == "push"
    assert made.value == pytest.approx(0.6) and made.rest is None
    # between fires the base, at the peak the top of the range
    one_shot(r, 1)
    frame(r, 0.5)
    assert box.v == pytest.approx(0.4)
    r.envs.fire(1, at=1.0)
    frame(r, 1.1)                                    # the peak of a 100 ms attack
    assert r.envs.outputs[0] == pytest.approx(1.0) and box.v == pytest.approx(1.0)
    for t in (1.3, 1.6, 1.9, 2.2):
        frame(r, t)
    assert r.envs.outputs[0] == 0.0 and box.v == pytest.approx(0.4)


def test_an_envelope_on_a_toggle_stays_position(banks):
    r = banks.r
    box = SimpleNamespace(on=False, n=1)
    t = r.reg.toggle("fx.glimmer.on", "on", lambda: box.on,
                     lambda v: setattr(box, "on", bool(v)), group="fx")
    n = r.reg.continuous("fx.zoomblur.taps", "taps", lambda: box.n,
                         lambda v: setattr(box, "n", int(v)), lo=1, hi=16, integer=True,
                         group="fx")
    for q in (t, n):
        row = learn.row_for("env:0", q)
        assert (row.op, row.value) == ("position", 1.0), q.id


def test_an_lfo_route_is_unchanged(banks, monkeypatch):
    """The envelope's row is the envelope's alone: an LFO into the same
    param makes the table's own LFO row — a push about the base at
    PUSH_DEPTH, not the headroom push (the owner, after the show of
    2026-10-30: as the fader an LFO swept the whole throw whatever the
    base); the same on a centred pin."""
    r, panel, table = banks.r, banks.panel, banks.r.router.table
    p, _ = _glimmer_mix(r)
    drawn_route_from(panel, p, monkeypatch, pick="LFO 1")
    made = next(b for b in table.bindings if b.target == p.id)
    assert made.source.startswith("lfo:")
    assert (made.op, made.value, made.rest) == ("push", learn.PUSH_DEPTH, None)
    assert made.motion == DEFAULT_ROUTE_FEEL          # a new route is the smooth spring
    assert learn.row_for("lfo:0", p) == Binding("lfo:0", p.id, "push", learn.PUSH_DEPTH,
                                                motion=DEFAULT_ROUTE_FEEL)
    assert learn.row_for("lfo:0", p, centred=True) == Binding(
        "lfo:0", p.id, "push", learn.PUSH_DEPTH, motion=DEFAULT_ROUTE_FEEL)


def test_route_from_an_envelope_keeps_auto_feel(banks, monkeypatch):
    """The owner, 2026-10-31: every new route is a spring — but an
    envelope's row keeps auto (`motion=None`): it has an attack and a
    release of its own, and a spring on top would blunt a kick-fired hit.
    Route from ▸ env 1 lands that; Route from ▸ LFO 1 the spring."""
    r, panel, table = banks.r, banks.panel, banks.r.router.table
    p, _ = _glimmer_mix(r)
    drawn_route_from(panel, p, monkeypatch, pick="env 1")
    env_row = next(b for b in table.bindings if b.target == p.id)
    assert env_row.source.startswith("env:") and env_row.motion is None
    assert "motion" not in env_row.to_json()
    table.remove(env_row)
    drawn_route_from(panel, p, monkeypatch, pick="LFO 1")
    lfo_row = next(b for b in table.bindings if b.target == p.id)
    assert lfo_row.source.startswith("lfo:") and lfo_row.motion == DEFAULT_ROUTE_FEEL


def test_a_graph_cable_into_a_mod_pin_lands_the_smooth_spring(rig):
    """The owner, 2026-10-31: a cable dragged into a param's mod pin
    (`Edit.connect` → `route_for` → `row_for`) lands with
    `motion.DEFAULT_ROUTE_FEEL`, whatever row the table picks: the
    position fader from a one-sided axis, a push from a centred one or
    onto a centred target, a band lane's row."""
    a, b = free_param(rig, centred=False), free_param(rig, centred=True)
    e, _ = edit(rig, leap())
    rows = [e.connect("out:hand:right.y", f"mod:{a.id}")]
    c = free_param(rig, centred=False)                   # free still: `a` is taken now
    rows.append(e.connect(f"mod:{c.id}", "out:hand:right.roll"))
    rows.append(e.connect("out:lane:2", f"mod:{b.id}"))
    assert [r.op for r in rows] == ["position", "push", "push"]
    assert all(r.motion == DEFAULT_ROUTE_FEEL for r in rows)
    assert all(r.to_json()["motion"] == {"mode": "spring", "dur": 0.5, "bounce": 0.0}
               for r in rows)


# ---------------------------------------------------------------- plan 35 T5: GRAPH deletes anything
#
# The wired frame on the canvas in the owner's names (plan 35 G, rows 373,
# 379): every node and wire of it deletes — only the type words and the
# loops refuse — the nodes are named for what they are, the picker groups
# them by primitive, and its first item wires a scene to All outputs.

def wired_rig(tmp_path, graph=None, *, slug=None, undo_rig=False):
    """`free_rig` for a wired frame: preset "Wired" whose section is
    `graph` (a `/6` section) — or corpus preset `slug` (tests/corpus) loaded,
    migrated as every load is — on a stub renderer, an Edit on it."""
    from test_graph_json import Stub
    from test_presets import boot, put

    from hyperspace import undo
    from hyperspace.library import PRESETS
    if undo_rig:
        from test_undo import boot as undo_boot
        from test_undo import settle
        rig = undo_boot(tmp_path / "home")
        settle(rig)
    else:
        rig = boot(tmp_path)
    fixture = Path(__file__).parent / "fixtures" / "presets" / f"{slug}.json"
    if slug is None:
        put(rig.home, "Wired", schema="hyperspace.preset/7", graph=graph)
        rig.lib.load(PRESETS, "Wired")
    elif fixture.exists():          # (a graph fixture, loaded and migrated as a file is)
        (rig.home / "presets").mkdir(parents=True, exist_ok=True)
        (rig.home / "presets" / fixture.name).write_text(fixture.read_text())
        rig.lib.load(PRESETS, slug)
    else:                           # (a corpus preset, seeded into the scratch library)
        seed(rig.home, "presets", "dream")
        rig.lib.load(PRESETS, slug)
    stub = Stub()
    rig.presets.graph.attach(stub)
    pushed: list[str] = []
    if undo_rig:
        settle(rig)
        rig.undo.clear()

        def push(label):
            pushed.append(label)
            undo.push(label, load=True)
    else:
        push = pushed.append
    return rig, graphview.Edit(graph=rig.presets.graph, push=push), pushed


def wired_wires(rig) -> set[tuple[str, str]]:
    return {(w.src, w.dst) for w in rig.presets.graph.spec.wires}


def _names(spec) -> list[str]:
    """Every node a wired section names: its entries' and its wires' ends."""
    from hyperspace import graph as G
    out: list[str] = []
    for e in spec.to_json().get("nodes", []):
        kind = e["kind"]
        n = e.get("instance", e.get("index", 1))
        if kind == "effect":
            out.append(G.instance_name(e["file"], n))
        elif kind in ("layer", "guide"):
            out.append(f"{G.wired_hands_name(n)}.{kind}")
        elif kind == "hands":
            out.append(G.wired_hands_name(n))
        elif kind == "echo":
            out.append(f"echo.{n}")
        else:
            out.append(kind if n == 1 else f"{kind}.{n}")
    for w in spec.wires:
        out += [w.src, w.node]
    return list(dict.fromkeys(x for x in out if x != G.GROUND))


DELETES = ("party-wake", "through-one-output", "branch-two-sizes")


@pytest.mark.parametrize("slug", DELETES)
def test_every_frame_node_and_wire_deletes(tmp_path, slug):
    """Review Focus 5: on party-wake migrated — and (R16, R15) the copy
    fixture `through-one-output` and the two-out fixture `branch-two-sizes`
    — each wire in turn, and then each node in turn, goes with its words
    said and no refusal — the owner's refusals deleting `grounded`, `frame →
    fx` and the run's cables are gone. What is left is the marker alone.
    And nodes first, their wires in place: every node goes the same way."""
    rig, e, pushed = wired_rig(tmp_path, slug=slug)
    gs = rig.presets.graph
    assert gs.spec.wired and gs.spec.wires
    for w in list(gs.spec.wires):
        e.said = ""
        assert e.unwire(f"rout:{w.src}", f"rin:{w.node}/{w.port}") is None, w
        assert e.said, w
    assert not gs.spec.wires
    names = _names(gs.spec)
    assert names                     # (the frame's nodes stay, declared, faint)
    for name in names:
        e.said = ""
        assert e.drop_node(f"render:{name}") is None, name
        assert e.said, name
    # (plan 36 T3: hands 1 is always there, its entry always written)
    assert {k: v for k, v in gs.spec.to_json().items() if v} == {
        "frame": "wired", "nodes": [{"kind": "hands", "laid": "over"}]}
    assert pushed and all(p.startswith(("unwire", "delete")) for p in pushed)
    rig, e, _ = wired_rig(tmp_path / "nodes-first", slug=slug)
    gs = rig.presets.graph
    for name in _names(gs.spec):
        if name not in _names(gs.spec):          # (gone with another: a copy with its effect)
            continue
        e.said = ""
        assert e.drop_node(f"render:{name}") is None, name
        assert e.said, name
    assert not gs.spec.wires and not gs.spec.copies


def test_deleting_an_effect_takes_its_copies(tmp_path):
    """R16: an effect a copy draws again, deleted, takes its copies (their
    entries and wires) in the same landing — a copy of nothing is no node —
    and says so."""
    rig, e, pushed = wired_rig(tmp_path, slug="through-one-output")
    spec = rig.presets.graph.spec
    name = min({c.of for c in spec.copies})
    mine = [c.name for c in spec.copies if c.of == name]
    n = len(pushed)
    assert e.drop_node(f"render:{name}") is None
    words = "its copy" if len(mine) == 1 else f"its {len(mine)} copies"
    assert e.said == f"{name} deleted, and {words}" and len(pushed) == n + 1
    spec = rig.presets.graph.spec
    assert not [c for c in spec.copies if c.of == name]
    assert not [w for w in spec.wires if {w.src, w.node} & set(mine)]


def test_unwiring_an_effects_only_input_leaves_it_faint_with_its_outs(tmp_path):
    """R15: in a wired frame an effect with no input reads nothing — drawn
    faint, its outs kept, no refusal (`branch-two-sizes`: `acid.2` fed by a
    channel into two ports)."""
    rig, e, _ = wired_rig(tmp_path, slug="branch-two-sizes")
    spec = rig.presets.graph.spec
    feed = next(w for w in spec.wires if w.dst == "acid.2.image")
    outs = {w for w in spec.wires if w.src == "acid.2"}
    assert len(outs) > 1
    assert e.unwire(f"rout:{feed.src}", "rin:acid.2/image") is None
    spec = rig.presets.graph.spec
    assert {w for w in spec.wires if w.src == "acid.2"} == outs and not spec.notes
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, None, spec)
    assert view.node("render:acid.2").faint
    # deleting the channel that fed it: the same
    rig, e, _ = wired_rig(tmp_path / "again", slug="branch-two-sizes")
    assert e.drop_node(f"render:{feed.src}") is None
    assert {w for w in rig.presets.graph.spec.wires if w.src == "acid.2"} == outs


def test_deleting_an_unwired_window_says_nothing_to_delete(tmp_path):
    """A window with no wires of its own, deleted: nothing happens, and the
    words say so (not that its wires went)."""
    _, e, pushed = wired_rig(tmp_path, slug="party-wake")
    assert e.drop_node("render:output.2") is None and pushed == []
    assert e.said == "nothing to delete: output 2 has no wires"


# backdrop-still's frame (a channel under the scene on the backdrop) with
# two effects in its run: the owner's sequence of deletes
OWNERS = {"frame": "wired", "nodes": [], "wires": [
    {"from": "channel.a", "to": "backdrop.image"},
    {"from": "shape", "to": "scene.geometry"},
    {"from": "scene", "to": "backdrop.scene"},
    {"from": "backdrop", "to": "lookback.image"},
    {"from": "lookback", "to": "plasma.image"},
    {"from": "plasma", "to": "kaleido.image"},
    {"from": "kaleido", "to": "output.all.image"},
    {"from": "hands.layer", "to": "output.all.hands"},
    {"from": "hands.layer", "to": "output.all.guide"}]}


def test_the_owners_sequence(tmp_path):
    """The owner's gestures of 2026-10-24, each now a plain delete: the
    scene off the backdrop, the look-back off the first effect, each
    effect's way out, the last one off All outputs — every one lands, and
    then nothing reaches the look-back."""
    from hyperspace import graph as G
    rig, e, _ = wired_rig(tmp_path, OWNERS)
    for src, dst in (("scene", "backdrop/scene"), ("lookback", "plasma/image"),
                     ("plasma", "kaleido/image"), ("kaleido", "output.all/image")):
        assert e.unwire(f"rout:{src}", f"rin:{dst}") is None, (src, dst)
    spec = rig.presets.graph.spec
    assert "lookback" not in G.reaches(spec)
    assert ("kaleido", "output.all.image") not in wired_wires(rig)


def test_deleting_the_backdrop_lifts_it_like_an_effect(tmp_path):
    """R18 (final review): on the owner's glimmer-bug (displace-moo's shape:
    a switch of two channel branches under the scene), deleting the
    backdrop joins what its `scene` port took to what it fed — the scene
    goes on to All outputs (plan 36 T4: its look-back was off, so none is
    drawn) — and says so; drawn, the frame is not black."""
    from test_graph_frame import SIZE, _fbo, _px, _tool

    from hyperspace.outputs import Switches, View

    rig, e, _ = wired_rig(tmp_path, slug="glimmer-bug")
    spec = rig.presets.graph.spec
    into = next(w.src for w in spec.wires if w.dst == "backdrop.scene")
    fed = sorted(w.dst for w in spec.wires if w.src == "backdrop")
    assert into == "scene" and fed == ["output.all.image"]
    assert e.drop_node("render:backdrop") is None
    assert e.said.startswith("Backdrop deleted; the scene goes on to "), e.said
    wires = wired_wires(rig)
    assert ("scene", "output.all.image") in wires
    assert not [w for w in wires if "backdrop" in w[0] or w[1].startswith("backdrop.")]
    try:
        import moderngl

        gl_ctx = moderngl.create_context(standalone=True)
    except Exception as ex:  # noqa: BLE001 — any GL failure means skip the drawing
        pytest.skip(f"no standalone GL context available: {ex}")
    gl = _tool().Rig("legacy6", "present", gl_ctx)
    try:
        gl.renderer.wiring = rig.presets.graph.spec.wiring()
        vs = [View(Switches(), SIZE, target=_fbo(gl_ctx))]
        for _ in range(3):
            gl.frame(vs, SIZE, 1.0)
        assert gl_ctx.error == "GL_NO_ERROR" and not vs[0].error, vs[0].error
        assert _px(vs[0].target)[..., :3].max() > 0
    finally:
        gl.close()


def test_deleting_a_window_unwires_it(tmp_path):
    """An output is the rig's window: delete takes the wires into it and
    says so (`OUTPUT_UNWIRED`), not a refusal; it shows its ground."""
    section = {"frame": "wired", "wires": [
        {"from": "channel.b", "to": "output.2.image"},
        {"from": "hands.layer", "to": "output.2.hands"},
        {"from": "channel.a", "to": "output.all.image"}]}
    rig, e, pushed = wired_rig(tmp_path, section)
    assert e.drop_node("render:output.2") is None
    assert not [w for w in rig.presets.graph.spec.wires if w.node == "output.2"]
    assert e.said == graphview.OUTPUT_UNWIRED.format(label="Output 2") == (
        "Output 2 is a window of this rig: its wires are gone, it shows its ground")
    assert ("channel.a", "output.all.image") in wired_wires(rig) and len(pushed) == 1


def test_the_picker_groups_by_primitive(tmp_path):
    """The picker in the owner's groups: starters ▸ (plan 36 T5), then scene ▸,
    look-back ▸, pictures ▸, media ▸ (the channels, 2026-10-31; the segment)
    and masks ▸ (plan 39 T5), the effect files, a copy of each effect
    instance in the section — each item's group `PICKER_GROUP[kind]`."""
    section = {"frame": "wired", "nodes": [{"kind": "effect", "file": "acid", "instance": 2}],
               "wires": [{"from": "scene", "to": "acid.image"},
                         {"from": "acid", "to": "output.all.image"}]}
    rig, e, _ = wired_rig(tmp_path, section)
    files = sorted(rig.presets.graph.files())
    echoes = [("echo", "1", "echo.1 (newest)"),
              *(("echo", str(k), f"echo.{k}") for k in range(2, 32)),
              ("echo", "32", "echo.32 (oldest)")]
    items = graphview.picker(e)
    assert items == [
        *(("starter", k, w) for k, w in graphview.STARTERS),
        ("scene", None, "scene"), ("shape", None, "shape"), ("hands", None, "hands"),
        ("layer", None, "hands layer"), ("guide", None, "hands guide"),
        ("backdrop", None, "backdrop"),
        ("lookback", None, "look-back"), *echoes, ("dream", None, "dream"),
        ("pattern", None, "faces pattern"), ("composite", None, "composite"),
        ("switch", None, "switch"),
        ("channels", "pattern.media", "faces media"), ("channels", "backdrop.image", "backdrop"),
        ("resize", None, "resize"), ("delay", None, "delay"),
        # (media ▸ the eight channels, 2026-10-31, and plan 39 T5 (W6)'s
        # segment; masks ▸ the matte and the cut)
        *(("channel", c, f"channel {c}") for c in "abcdefgh"),
        ("segment", None, "segment"), ("matte", None, "matte"), ("cut", None, "cut"),
        *(("effect", f, f) for f in files),
        ("copy", "acid", "copy of acid"), ("copy", "acid.2", "copy of acid.2")]
    groups = [graphview.PICKER_GROUP[k] for k, _, _ in items]
    assert list(dict.fromkeys(groups)) == ["starters", "scene", "look-back", "pictures",
                                           "media", "masks", "effects", "copy of"]


def test_the_starter_wires_the_scene_to_all_outputs(tmp_path):
    """The scene chain starter (plan 36 T5; plan 35 G's "scene starter")
    on a blank preset: `shape → scene.geometry` and `scene →
    output.all.image`, in one undo step, said `STARTER_SAID`."""
    rig, e, pushed = wired_rig(tmp_path, {"frame": "wired"})
    assert e.starter() is None
    assert wired_wires(rig) == {("shape", "scene.geometry"), ("scene", "output.all.image")}
    assert e.said == graphview.STARTER_SAID == "scene chain: shape → scene → All outputs"
    assert pushed == ["starter: scene chain"]


GROUNDED = {"frame": "wired", "wires": [{"from": "scene", "to": "output.all.image"},
                                        {"from": "shape", "to": "scene.geometry"},
                                        {"from": "ground", "to": "output.2.image"}]}


def test_a_ground_wire_is_drawn(tmp_path):
    """R13: `ground → output.2.image` is plumbing the owner can see — a
    small Ground source in OUTPUTS, hovered with what it is (the window's
    background), its cable into the window's port, laid out running right."""
    from test_graphview import views

    from hyperspace.outputs import Switches
    rig, _, _ = wired_rig(tmp_path, GROUNDED)
    spec = rig.presets.graph.spec
    g = G.build_graph(views(Switches(), Switches()), spec.wiring())
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    n = view.node("render:ground")
    assert n is not None and n.label == "Ground" and n.area == graphview.OUTPUTS_AREA
    assert not n.faint and not n.idle
    assert "background" in n.status and n.status.endswith("· id ground")
    c = next(c for c in view.cables if c.dst_port == "rin:output.2/image")
    assert c.src_port == "rout:ground" and c.ref == G.Wire("ground", "output.2.image")
    pos = graphview.auto_layout(view)
    assert pos["render:ground"][0] < pos["render:output.2"][0]
    # no ground wire: no Ground node
    plain = graphview.build(rig.router.table, rig.reg, rig.router, None, None,
                            G.read_graph({"frame": "wired"}))
    assert plain.node("render:ground") is None


def test_a_ground_wire_deletes(tmp_path):
    """R13: the ground cable deletes as any wire — one undo step through
    `_land` — and so does the Ground node (every ground wire with it)."""
    from test_undo import settle
    rig, e, pushed = wired_rig(tmp_path, GROUNDED, undo_rig=True)
    cable = graphview.VCable("c", "rout:ground", "rin:output.2/image", graphview.IMAGE,
                             ref=G.Wire("ground", "output.2.image"), kind="render")
    assert e.unwire(cable) is None and pushed == ["unwire output.2.image"]
    assert ("ground", "output.2.image") not in wired_wires(rig)
    settle(rig)
    assert rig.undo.undo() and ("ground", "output.2.image") in wired_wires(rig)
    assert e.drop_node("render:ground") is None and e.said == "Ground deleted"
    assert not [w for w in rig.presets.graph.spec.wires if w.src == "ground"]


def test_a_frame_node_is_added_once(tmp_path):
    """A frame kind from the picker is its entry, there once: a second add
    is refused in words; a copy of an instance is `CopyAt(next, of)`."""
    from hyperspace import graph as G
    rig, e, _ = wired_rig(tmp_path, {"frame": "wired"})
    assert e.add_node("lookback") is None and e.added == "lookback"
    assert G.LookbackAt() in rig.presets.graph.spec.frame_nodes
    assert e.add_node("lookback") == "Look-back is in the graph already"
    assert e.add_node("effect", "acid") is None
    assert e.add_node("copy", "acid") is None and e.added == "copy"
    assert e.add_node("copy", "acid") is None and e.added == "copy.2"
    assert rig.presets.graph.spec.copies == (G.CopyAt(1, "acid"), G.CopyAt(2, "acid"))
    assert e.add_node("copy", "teapot") == "copy of teapot: no such effect instance in the graph"


def test_the_pad_nodes_details_draw_the_pad(rig, monkeypatch):
    """The pad's node selected on GRAPH, whatever its role is called (plan
    42: "edge", "xbox", not only "pad"): its details draw the pad's picture
    (ui_pad.inline) — every control of its layout — under the readout's
    drop-down (`ui.pad_view`, as on SYSTEM), and not the port lines under
    it. A second pad's node and another device's draw no picture."""
    panel = rig.panel
    frame(panel, "graph")
    st = ui_graph._state(panel)
    pad, other = SimpleNamespace(on=False), SimpleNamespace(on=False)
    panel.pad = pad
    drew, real = [], ui_pad.inline
    monkeypatch.setattr(ui_pad, "inline", lambda p: (drew.append(1), real(p)))
    picked, combo = [], panel._combo
    monkeypatch.setattr(panel, "_combo", lambda pid, **k: (picked.append(pid), combo(pid, **k))[1])
    said, disabled = [], imgui.text_disabled
    monkeypatch.setattr(imgui, "text_disabled", lambda s: (said.append(s), disabled(s))[1])
    port = graphview.VPort("pad:A", "A", "out", patched=True)
    nodes = (("edge", SimpleNamespace(kind="gamepad", io=pad), [1]),
             ("pad", SimpleNamespace(kind="gamepad", io=pad), [1]),
             ("xbox", SimpleNamespace(kind="gamepad", io=other), []),
             ("off", SimpleNamespace(kind="gamepad", io=None), []),
             ("apc40", SimpleNamespace(kind="midi", io=pad), []))
    for role, dev, want in nodes:
        drew.clear()
        picked.clear()
        said.clear()
        imgui.new_frame()
        imgui.begin("side")
        ui_graph._side(panel, st, st["view"],
                       ("node", graphview.VNode(f"device:{role}", "device", role, [port], ref=dev)))
        imgui.end()
        imgui.end_frame()
        assert drew == want, role
        assert picked == (["ui.pad_view"] if want else []), role   # the readout's drop-down
        assert ("A: not live" in said) is (not want), role         # the port lines: not under it
    assert ui_pad.rect(panel, gamepad.LAYOUT[0]) is not None    # it really laid the pad out


# ---------------------------------------------------------------- 2026-11-01: any picture node onto a cable
#
# The owner: "It's not just for effects. We want more or less all nodes
# that we've been using to be able to be dragged and dropped onto wires
# and have them intelligently remap. A composite has an over and an under:
# when you drop that onto a cable, you should be asked where you want this
# input to go, over or under. There's nothing special about effects."
# These drive real mouse drags through the node editor (the throwaway
# harness of 2026-10-31, kept): press on a node's title, move, let go.

def _drag_rig(rig, monkeypatch, *pairs, nodes=(), effects=("acid", "wobble.2"), on=("acid",),
              layout=None):
    """The page drawn on preset "Drag" — the wired frame of `pairs` and
    `nodes` — with a probe on `_moved` (the editor's origin and scale on
    screen, the press and the last plan lit); every node at `layout`'s
    place (canvas units) when given. Returns (the section, the probe)."""
    from types import SimpleNamespace as NS

    from test_graphview import views
    from test_presets import put

    from hyperspace.outputs import Switches
    put(rig.lib.home, "Drag", schema="hyperspace.preset/7", graph=_section(*pairs, nodes=nodes),
        **({"layout": layout} if layout else {}))
    rig.lib.load("presets", "Drag")
    gs = rig.lib.presets.graph
    rig.panel.renderer = NS(_graph=G.build_graph(views(Switches()), gs.spec.wiring(),
                                                   effects=effects))
    imgui.get_io().display_size = imgui.ImVec2(1600, 1000)
    rig.panel.desk = False
    # the app's canvas: preset only (the conftest starts the page tests on
    # the full canvas, where a params group sits over the free node's place)
    ui_graph._state(rig.panel)["preset_only"] = True
    probe: dict = {}
    real = ui_graph._moved

    def moved(panel, st, view):
        from imgui_bundle import imgui_node_editor as ed
        o = ed.canvas_to_screen(imgui.ImVec2(0, 0))
        u = ed.canvas_to_screen(imgui.ImVec2(100, 0))
        probe.update(o=(o.x, o.y), k=(u.x - o.x) / 100.0, zoom=ed.get_current_zoom(),
                     press=st.get("press"), lit=st.get("onto_lit"))
        if st.get("onto_lit") is not None:      # the pointer's words, as this frame's view says them
            probe["words"] = ui_graph.drag_words(view, st["onto_lit"])
        return real(panel, st, view)
    monkeypatch.setattr(ui_graph, "_moved", moved)
    for e in on:
        if rig.reg.get(f"fx.{e}.on") is not None:
            rig.reg[f"fx.{e}.on"].set(True)
    for _ in range(4):
        frame(rig.panel, "graph")
    return gs, probe


def _to_screen(probe, p):
    return (probe["o"][0] + p[0] * probe["k"], probe["o"][1] + p[1] * probe["k"])


def _node_box(rig, nid):
    from imgui_bundle import imgui_node_editor as ed
    st = ui_graph._state(rig.panel)
    ed.set_current_editor(st["editor"])
    p = ed.get_node_position(ed.NodeId(ui_graph._id(st, "n:" + nid)))
    s = ed.get_node_size(ed.NodeId(ui_graph._id(st, "n:" + nid)))
    return (p.x, p.y), (s.x, s.y)


def _cable_mid(rig, dst):
    """The drawn cable into pin `dst` and its midpoint (canvas units: the
    pins drawn this frame, a collapsed end's stub)."""
    st = ui_graph._state(rig.panel)
    view = st["view"]
    c = next(c for c in view.cables if c.dst_port == dst)
    s, d = graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port)
    a = st["pin_xy"].get(c.src_port) or st["pin_xy"][graphview.stub_out(s)]
    b = st["pin_xy"].get(c.dst_port) or st["pin_xy"][graphview.stub_in(d)]
    return c, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _centre_on(rig, probe, point):
    """Pan so canvas `point` sits in the middle of the canvas on screen."""
    st = ui_graph._state(rig.panel)
    (x0, y0), (x1, y1) = st["seen_rect"]
    mid = ((x0 + x1) / 2, (y0 + y1) / 2)
    px, py = st["pan"]
    st["pan"] = (px + mid[0] - point[0], py + mid[1] - point[1])
    for _ in range(4):
        frame(rig.panel)


def _cmd(down: bool) -> None:
    io = imgui.get_io()
    io.add_key_event(imgui.Key.mod_super, down)
    io.add_key_event(imgui.Key.left_super, down)


def _zoom_out(rig, probe, notches: int) -> None:
    """⌘ + wheel over the canvas's middle, `notches` clicks out."""
    st = ui_graph._state(rig.panel)
    (x0, y0), (x1, y1) = st["seen_rect"]
    io = imgui.get_io()
    io.add_mouse_pos_event(*_to_screen(probe, ((x0 + x1) / 2, (y0 + y1) / 2)))
    frame(rig.panel)
    for _ in range(notches):
        _cmd(True)
        frame(rig.panel)
        io.add_mouse_wheel_event(0.0, -1.0)
        frame(rig.panel)
        _cmd(False)
        frame(rig.panel)
    for _ in range(40):                    # the smooth zoom settles
        frame(rig.panel)


def _drag_to(rig, probe, nid, centre_to, cmd=False, steps=12):
    """A real drag: press on node `nid`'s title, move so its box's centre
    ends at canvas `centre_to` (⌘ held through it when `cmd`), let go.
    Returns (what was pressed, the last plan lit)."""
    io = imgui.get_io()
    (px, py), (sx, sy) = _node_box(rig, nid)
    grab = (px + sx * 0.35, py + 6.0)
    dx, dy = centre_to[0] - (px + sx / 2), centre_to[1] - (py + sy / 2)
    s0 = _to_screen(probe, grab)
    k = probe["k"]
    io.add_mouse_pos_event(*s0)
    frame(rig.panel)
    frame(rig.panel)
    if cmd:
        _cmd(True)
        frame(rig.panel)
    io.add_mouse_button_event(0, True)
    frame(rig.panel)
    pressed = probe.get("press")
    for i in range(1, steps + 1):
        u = i / steps
        io.add_mouse_pos_event(s0[0] + dx * k * u, s0[1] + dy * k * u)
        frame(rig.panel)
    frame(rig.panel)
    frame(rig.panel)
    lit = probe.get("lit")
    io.add_mouse_button_event(0, False)
    frame(rig.panel)
    if cmd:
        _cmd(False)
    frame(rig.panel)
    frame(rig.panel)
    io.add_mouse_pos_event(-1.0, -1.0)
    return pressed, lit


RUN = (*FRAME0, ("lookback", "output.all.image"))
# every node at hand on one screen: the run along y = 0, the free node below
PLACES = {"render:lookback": [0, 0], "render:output.all": [700, 0], "render:scene": [-400, 0],
          "render:shape": [-800, 0]}


def _free_node_rig(rig, monkeypatch, entry: dict, nid: str, *more, effects=("acid", "wobble.2")):
    """`shape → scene → lookback → output.all` with free node `entry` (`nid`)
    placed under the run, the canvas centred on the run's last cable."""
    gs, probe = _drag_rig(rig, monkeypatch, *RUN, *more, nodes=[entry], effects=effects,
                          layout={**PLACES, nid: [250, 400]})
    _, mid = _cable_mid(rig, "rin:output.all/image")
    _centre_on(rig, probe, (mid[0], mid[1] + 150))
    return gs, probe


def test_a_free_composite_dropped_on_a_cable_asks_under_or_over(rig, monkeypatch):
    """A free composite dragged onto `lookback → output.all.image`: the drag
    says "then pick under or over", the drop opens the chooser for its
    inlets and changes nothing; "over" picked wires `lookback →
    composite.over`, `composite → output.all.image` in one step, and the
    line says under is open."""
    _, probe = _free_node_rig(rig, monkeypatch, {"kind": "composite"}, "render:composite")
    st = ui_graph._state(rig.panel)
    c, mid = _cable_mid(rig, "rin:output.all/image")
    pressed, lit = _drag_to(rig, probe, "render:composite", mid)
    assert pressed and pressed[0] == "render:composite"
    assert lit and lit["best"] == c.id and lit["ask"] == ("under", "over")
    assert probe["words"] == (
        "let go: Composite onto Look-back → All outputs, then pick under or over")
    held = st["onto"]
    assert held["node"] == "render:composite" and held["inlets"] == ("under", "over")
    assert held["cables"] == [c.id]
    assert wires_of(rig.lib) == set(RUN)        # nothing until the pick
    view = st["view"]
    assert ui_graph.put_onto(rig.panel, view, "render:composite", c, "over") is c
    assert wires_of(rig.lib) == {*FRAME0, ("lookback", "composite.over"),
                                 ("composite", "output.all.image")}
    assert st["said"] == ("composite moved: lookback → composite over → output.all.image; "
                          "composite under is open")
    assert st["onto"] is None


def test_the_chooser_takes_under_too_and_a_switch_asks_its_inputs(rig, monkeypatch):
    """The other inlet: "under" picked wires the composite's under. A free
    switch asks between in1 … in8, and the one picked takes the picture;
    the line says the rest are open."""
    _, probe = _free_node_rig(rig, monkeypatch, {"kind": "composite"}, "render:composite")
    st = ui_graph._state(rig.panel)
    c, mid = _cable_mid(rig, "rin:output.all/image")
    _drag_to(rig, probe, "render:composite", mid)
    assert st["onto"] and st["onto"]["inlets"] == ("under", "over")
    assert ui_graph.put_onto(rig.panel, st["view"], "render:composite", c, "under") is c
    assert wires_of(rig.lib) == {*FRAME0, ("lookback", "composite.under"),
                                 ("composite", "output.all.image")}
    assert st["said"].endswith("; composite over is open")
    # a switch
    _, probe = _free_node_rig(rig, monkeypatch, {"kind": "switch"}, "render:switch")
    st = ui_graph._state(rig.panel)
    c, mid = _cable_mid(rig, "rin:output.all/image")
    _, lit = _drag_to(rig, probe, "render:switch", mid)
    assert lit["ask"] == G.SWITCH_PORTS
    assert probe["words"].endswith(", then pick in1 … in8")
    assert st["onto"]["inlets"] == G.SWITCH_PORTS
    assert ui_graph.put_onto(rig.panel, st["view"], "render:switch", c, "in3") is c
    assert wires_of(rig.lib) == {*FRAME0, ("lookback", "switch.in3"),
                                 ("switch", "output.all.image")}
    assert st["said"] == ("switch moved: lookback → switch in3 → output.all.image; "
                          "switch in1 … in8 are open")


def test_a_channel_dropped_on_a_cable_takes_it_over(rig, monkeypatch):
    """A source: channel a dragged onto `lookback → output.all.image` feeds
    the port instead — `channel.a → output.all.image`, the old wire gone,
    the look-back kept (its own wire in stays) and the line says it feeds
    nothing now; the drag said so first."""
    gs, probe = _drag_rig(rig, monkeypatch, *RUN, layout=PLACES)
    st = ui_graph._state(rig.panel)
    ui_graph.pick_channel(rig.panel, "a", (250.0, 400.0))       # media ▸ channel a: revealed
    for _ in range(60):                 # (the editor's glide to the selection, run out)
        frame(rig.panel)
    c, mid = _cable_mid(rig, "rin:output.all/image")
    _centre_on(rig, probe, (mid[0], mid[1] + 150))
    c, mid = _cable_mid(rig, "rin:output.all/image")
    pressed, lit = _drag_to(rig, probe, "render:channel.a", mid)
    assert pressed[0] == "render:channel.a" and lit["source"] and lit["best"] == c.id
    assert probe["words"] == "let go: Channel A feeds All outputs instead of Look-back"
    assert wires_of(rig.lib) == {*FRAME0, ("channel.a", "output.all.image")}
    assert st["said"] == ("channel.a feeds output.all.image instead of lookback; "
                          "lookback feeds nothing now")
    assert G.run_back(gs.spec, "output.all.image") == ()


def test_cmd_lifts_a_wired_pattern_onto_a_cable_and_closes_its_gap(rig, monkeypatch):
    """⌘-drag of the pattern (wired `channel.b → pattern.media`, `pattern →
    shape.faces`) onto `lookback → output.all.image`: out of its place —
    its source bridged to its consumer, `channel.b → shape.faces` — and
    spliced: `lookback → pattern.media`, `pattern → output.all.image`.
    Without ⌘ the drag only moves it and says to hold ⌘."""
    more = (("channel.b", "pattern.media"), ("pattern", "shape.faces"))
    _, probe = _drag_rig(rig, monkeypatch, *RUN, *more,
                          layout={**PLACES, "render:pattern": [250, 400],
                                  "render:channel.b": [-200, 400]})
    c, mid = _cable_mid(rig, "rin:output.all/image")
    _centre_on(rig, probe, (mid[0], mid[1] + 150))
    c, mid = _cable_mid(rig, "rin:output.all/image")
    st = ui_graph._state(rig.panel)
    pressed, lit = _drag_to(rig, probe, "render:pattern", mid)
    assert pressed[0] == "render:pattern" and lit["hint"] == "over" and not lit["hot"]
    assert probe["words"].startswith("hold ⌘")
    assert wires_of(rig.lib) == {*RUN, *more}
    _centre_on(rig, probe, (mid[0], mid[1] + 150))
    c, mid = _cable_mid(rig, "rin:output.all/image")
    pressed, lit = _drag_to(rig, probe, "render:pattern", mid, cmd=True)
    assert lit["lift"] and lit["hot"] and lit["best"] == c.id
    assert wires_of(rig.lib) == {*FRAME0, ("channel.b", "shape.faces"),
                                 ("lookback", "pattern.media"), ("pattern", "output.all.image")}
    assert st["said"] == "pattern moved: lookback → pattern → output.all.image"


def test_a_node_that_never_splices_is_refused_in_words_and_dims_nothing(rig, monkeypatch):
    """The shape dragged over the picture cable: not hot (nothing dims,
    every cable cold), the words say it makes geometry, and nothing
    changes; a matte says it makes a mask."""
    _, probe = _drag_rig(rig, monkeypatch, *RUN, nodes=[{"kind": "matte"}],
                          layout={**PLACES, "render:shape": [250, 400], "render:matte": [650, 400]})
    c, mid = _cable_mid(rig, "rin:output.all/image")
    _centre_on(rig, probe, (mid[0], mid[1] + 150))
    c, mid = _cable_mid(rig, "rin:output.all/image")
    st = ui_graph._state(rig.panel)
    pressed, lit = _drag_to(rig, probe, "render:shape", mid)
    assert pressed[0] == "render:shape" and not lit["hot"] and lit["best"] is None
    assert lit["refused"][c.id] == graphview.GEOMETRY_NODE.format(label="Shape")
    assert probe["words"] == lit["refused"][c.id]
    assert {x.id for x in st["view"].cables} <= lit["cold"]
    assert wires_of(rig.lib) == set(RUN)
    c, mid = _cable_mid(rig, "rin:output.all/image")
    pressed, lit = _drag_to(rig, probe, "render:matte", mid)
    assert lit["refused"][c.id] == graphview.MASK_NODE.format(label="Matte")
    assert wires_of(rig.lib) == set(RUN)


def test_the_other_refusals_are_said_and_cold(rig):
    """A picture node over a value cable, a modifier over a picture cable,
    a free effect over the rig's bus cable and over a through wire (an off
    effect's): each refused in its words, each cable cold (undimmed) while
    the node is dragged — "won't take it" reads differently from "not
    near enough"."""
    st, view, _ = _two_cable_rig(rig)
    out = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    # a value cable under wobble.2
    val = next(c for c in view.cables if c.type == graphview.VALUE)
    st["pin_xy"][val.src_port] = (0.0, 500.0)
    st["pin_xy"][val.dst_port] = (400.0, 500.0)
    plan = ui_graph.onto_plan(rig.panel, view, "render:wobble.2", (200.0, 500.0))
    assert plan["best"] is None and plan["refused"][val.id] == ui_graph.PICTURE_ON_VALUE.format(
        node="wobble 2")
    assert val.id in plan["cold"] and out.id not in plan["cold"]
    # the bus cable All outputs → output 1
    bus = next(c for c in view.cables if c.dst_port == "rin:output.1/image")
    st["pin_xy"][graphview.stub_in("render:output.1")] = (1000.0, 0.0)
    plan = ui_graph.onto_plan(rig.panel, view, "render:wobble.2", (850.0, 0.0))
    assert plan["best"] is None and bus.id in plan["cold"]
    assert plan["refused"][bus.id] == graphview.BUS_NO_EFFECT.format(
        wire="output.all.image → output.1.image")
    # a modifier over the picture cable
    ui_graph.add_modifier(rig.panel, "smooth", (0.0, 0.0))
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    view = st["view"]
    st["pin_xy"] = {graphview.stub_out("render:acid"): (0.0, 0.0),
                    graphview.stub_in("render:output.all"): (300.0, 0.0)}
    mod = next(n for n in view.nodes if n.kind == "modifier")
    out = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    plan = ui_graph.onto_plan(rig.panel, view, mod.id, (150.0, 0.0))
    assert plan["best"] is None and plan["refused"][out.id] == ui_graph.MOD_ON_PICTURE
    assert out.id in plan["cold"]


def test_a_through_wire_says_what_to_turn_on(rig, monkeypatch):
    """acid switched off: the drawn `lookback → output.all` wire is a
    through wire, no cable; a free wobble.2 dragged onto it is refused
    with "turn it on to splice here", the wire cold."""
    gs, probe = _drag_rig(rig, monkeypatch, *FRAME0, ("lookback", "acid.image"),
                          ("acid", "output.all.image"),
                          nodes=[{"kind": "effect", "file": "wobble", "instance": 2}],
                          on=(), layout={**PLACES, "render:wobble.2": [250, 400],
                                         "render:acid": [300, -300]})
    st = ui_graph._state(rig.panel)
    thr = list(st["throughs"].values())
    assert len(thr) == 1 and thr[0].label == "through 1 off effect: acid"
    a = st["pin_xy"][graphview.stub_out("render:lookback")]
    b = st["pin_xy"][graphview.stub_in("render:output.all")]
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    _centre_on(rig, probe, (mid[0], mid[1] + 150))
    a = st["pin_xy"][graphview.stub_out("render:lookback")]
    b = st["pin_xy"][graphview.stub_in("render:output.all")]
    pressed, lit = _drag_to(rig, probe, "render:wobble.2", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    assert pressed[0] == "render:wobble.2" and lit["best"] is None
    assert lit["refused"] == {thr[0].id: "through 1 off effect: acid — turn it on to splice here"}
    assert thr[0].id in lit["cold"]
    assert G.run_back(gs.spec, "output.all.image") == ("acid",)


@pytest.mark.parametrize("notches", [0, 12])
def test_the_glow_and_the_drop_agree_at_any_zoom(rig, monkeypatch, notches):
    """A free wobble.2 dragged so its box's edge just reaches the cable, at
    zoom 1 and zoomed out: the cable the drag lit is the one the drop
    lands in — the release acts on the last plan lit, not on a plan
    re-asked at the editor's grid-snapped position."""
    gs, probe = _free_node_rig(rig, monkeypatch, {"kind": "effect", "file": "wobble",
                                                  "instance": 2}, "render:wobble.2")
    if notches:
        _zoom_out(rig, probe, notches)
    c, mid = _cable_mid(rig, "rin:output.all/image")
    _centre_on(rig, probe, (mid[0], mid[1] + 150))
    c, mid = _cable_mid(rig, "rin:output.all/image")
    assert (probe["zoom"] > 2.5) == bool(notches)
    _, (_, sy) = _node_box(rig, "render:wobble.2")
    # the box's top edge a hair under the wire: a drop by its box, not its centre
    reach = graphview.drop_reach(probe["zoom"])
    pressed, lit = _drag_to(rig, probe, "render:wobble.2", (mid[0], mid[1] + sy / 2 + reach * 0.5))
    assert pressed[0] == "render:wobble.2"
    assert lit["best"] == c.id, (lit, probe["zoom"])
    assert G.run_back(gs.spec, "output.all.image") == ("wobble.2",)


def test_a_pin_not_drawn_this_frame_is_no_drop_target(rig, monkeypatch):
    """acid expanded (its port pins drawn), collapsed again and the canvas
    panned: `pin_xy` holds only the pins drawn this frame, so the stale
    port pin never stands in for the drawn stub (a drop 300 units off the
    wire)."""
    _drag_rig(rig, monkeypatch, *FRAME0, ("lookback", "acid.image"),
                          ("acid", "output.all.image"), layout=PLACES)
    st = ui_graph._state(rig.panel)
    assert graphview.stub_out("render:acid") in st["pin_xy"] and "rout:acid" not in st["pin_xy"]
    ui_graph.toggle_open(st, "render:acid")
    for _ in range(3):
        frame(rig.panel)
    assert "rout:acid" in st["pin_xy"]
    ui_graph.toggle_open(st, "render:acid")
    px, py = st["pan"]
    st["pan"] = (px + 300, py + 250)
    for _ in range(3):
        frame(rig.panel)
    assert "rout:acid" not in st["pin_xy"] and graphview.stub_out("render:acid") in st["pin_xy"]


def test_a_group_member_dropped_out_onto_a_cable_leaves_and_splices(rig, monkeypatch):
    """wobble.2 grouped alone, its group open, dragged out of the region
    onto `lookback → output.all.image`: it leaves the group and is spliced
    (two steps), as the glow promised."""
    gs, probe = _free_node_rig(rig, monkeypatch, {"kind": "effect", "file": "wobble",
                                                  "instance": 2}, "render:wobble.2")
    st = ui_graph._state(rig.panel)
    assert ui_graph.group_nodes(rig.panel, ["render:wobble.2"]) is not None
    for _ in range(3):
        frame(rig.panel)
    g = st["view"].groups[0]
    ui_graph.set_open(rig.panel, g.id, True)
    for _ in range(4):
        frame(rig.panel)
    c, mid = _cable_mid(rig, "rin:output.all/image")
    _centre_on(rig, probe, (mid[0], mid[1] + 150))
    c, mid = _cable_mid(rig, "rin:output.all/image")
    pressed, lit = _drag_to(rig, probe, "render:wobble.2", mid)
    assert pressed[0] == "render:wobble.2" and lit["best"] == c.id
    assert G.run_back(gs.spec, "output.all.image") == ("wobble.2",)
    assert not st["view"].groups or all(
        "render:wobble.2" not in [m.id for m in x.members] for x in st["view"].groups)


def test_insert_node_from_the_cable_menu(rig):
    """`ui_graph.insert_node`: a composite asked its inlet, then spliced
    where the menu opened; a delay in one call; `insert_items` disables
    the look-back the section has; the effect wrapper still stands."""
    st, view, gs = _two_cable_rig(rig)
    c = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    assert ui_graph.insert_node(rig.panel, c, "composite", at=(321.0, 654.0)) is None
    held = st["onto"]
    assert held["insert"] == ("composite", None) and held["inlets"] == ("under", "over")
    assert G.run_back(gs.spec, "output.all.image") == ("acid",)       # nothing yet
    assert ui_graph.insert_node(rig.panel, c, "composite", None, "over", (321.0, 654.0)) is None
    assert wires_of(rig.lib) >= {("acid", "composite.over"), ("composite", "output.all.image")}
    assert rig.lib.presets.layout["render:composite"] == [321, 654]
    assert st["said"] == ("composite inserted: acid → composite over → output.all.image; "
                          "composite under is open")
    frame(rig.panel, "graph")
    view = st["view"]
    c = next(c for c in view.cables if c.dst_port == "rin:composite/over")
    assert ui_graph.insert_node(rig.panel, c, "delay", at=(1.0, 2.0)) is None
    assert wires_of(rig.lib) >= {("acid", "delay.image"), ("delay", "composite.over")}
    e = ui_graph.render_edit(rig.panel)
    items = {k: why for k, _, why in graphview.insert_items(e)}
    assert items["lookback"] == (
        "Look-back is in the graph already: drag it onto the cable")
    assert items["composite"] is None and items["pattern"] is None
    assert e.insert_node(c, "channel") == graphview.CHANNEL_INSERT
    assert e.insert_node(c, "composite") == graphview.PICK_INLET.format(
        name="composite", ports="under or over", src="acid")
    assert e.insert_node(c, "switch", None, "in9") == graphview.NOT_AN_INLET.format(
        name="switch", port="in9", ports="in1 … in8")
    frame(rig.panel, "graph")
    c = next(c for c in st["view"].cables if c.dst_port == "rin:delay/image")
    assert ui_graph.insert_effect(rig.panel, c, "kaleido", (5.0, 6.0)) is None
    assert {("acid", "kaleido.image"), ("kaleido", "delay.image")} <= wires_of(rig.lib)


def test_place_node_lifts_any_kind_by_its_table(tmp_path):
    """`Edit.place_node` on the section alone: a composite lifted out of its
    place bridges its `under` to its consumer and keeps its `over`; a
    segment goes in by its `fg` pin; a source lifted says what lost its
    feed; a node on the cable already, a kind that never splices and an
    inlet it has not are refused in words; the effect wrappers stand."""
    rig, e, pushed = free_rig(
        tmp_path, ("lookback", "composite.under"), ("channel.c", "composite.over"),
        ("composite", "acid.image"), ("acid", "output.all.image"), ("channel.a", "backdrop.image"),
        nodes=[{"kind": "composite"}])
    assert e.place_node(("acid", "output.all.image"), "composite") == graphview.PICK_INLET.format(
        name="composite", ports="under or over", src="acid")
    assert e.place_node(("acid", "output.all.image"), "composite", "between") == \
        graphview.NOT_AN_INLET.format(name="composite", port="between", ports="under, over")
    assert e.place_node(("composite", "acid.image"), "composite", "under") == \
        "composite is on that cable already"
    assert e.place_node(("acid", "output.all.image"), "composite", "under") is None
    assert wires_of(rig) == {("lookback", "acid.image"), ("channel.c", "composite.over"),
                             ("acid", "composite.under"), ("composite", "output.all.image"),
                             ("channel.a", "backdrop.image")}
    assert e.said == "composite moved: acid → composite under → output.all.image"
    assert pushed[-1] == "move composite onto acid → output.all.image"
    # a source lifted: its old consumer loses its feed, said
    assert e.place_node(("composite", "output.all.image"), "channel.a") is None
    assert e.said == ("channel.a feeds output.all.image instead of composite; "
                      "composite feeds nothing now; backdrop.image fed by nothing now")
    assert ("channel.a", "backdrop.image") not in wires_of(rig)
    # a kind that never splices
    assert e.place_node(("lookback", "acid.image"), "shape") == graphview.GEOMETRY_NODE.format(
        label="Shape")
    assert e.place_node(("lookback", "acid.image"), "output.all") == \
        graphview.OUTPUT_NODE.format(label="All outputs")
    # a segment: in by image, out by fg
    assert e.add_node("segment") is None
    assert e.place_node(("lookback", "acid.image"), "segment") is None
    assert {("lookback", "segment.image"), ("segment.fg", "acid.image")} <= wires_of(rig)
    # (a cable from a pin takes no drop yet: `_cable_ends`' rule, as before)
    assert e.place_node(("segment.fg", "acid.image"), "segment") == \
        graphview.NO_PICTURE_CABLE.format(wire="segment.fg → acid.image")
    assert e.place_node(("lookback", "segment.image"), "segment") == "segment is on that cable already"
    # the effect wrappers stand: a `Refusal`, or None
    why = e.place_effect(("lookback", "segment.image"), "teapot")
    assert isinstance(why, graphview.Refusal) and "no teapot effect" in why
    assert e.place_effect(("segment.fg", "acid.image"), "acid") == \
        graphview.NO_PICTURE_CABLE.format(wire="segment.fg → acid.image")


def test_the_insert_table_names_picture_ports_only():
    """Every inlet `INSERT_PORTS` names is a picture port of its kind, and
    every outlet makes a picture (the table and `graph.WIRED_TAKES` /
    `WIRED_MAKES` agree); every picture-making kind the canvas draws is
    either in the table or refused in words by `drop_refusal`."""
    for kind, (ins, out) in graphview.INSERT_PORTS.items():
        takes = G.WIRED_TAKES[kind]
        assert all(takes[p] == G.IMAGE for p in ins), kind
        assert (G.WIRED_MAKES[kind] if not out else G.SEGMENT_PINS[out]) == G.IMAGE, kind
    pins = (*G.SEGMENT_PINS, "cover", G.DEPTH_PORT, "echo")      # a pin is its node's
    for kind in G.WIRED_MAKES:
        if kind in graphview.INSERT_PORTS or kind in pins:
            continue
        name = {"output": "output.1", "layer": "hands.layer", "guide": "hands.guide"}.get(kind, kind)
        assert graphview.kind_of(name) == kind and graphview.drop_refusal(name), kind


# ---------------------------------------------------------------- 2026-11-02 (G0, row 563): a group by the mouse

def _box_select(rig, probe, a, b, steps=10):
    """A real box-select: press on empty canvas at `a`, drag to `b`, let go
    (canvas units)."""
    io = imgui.get_io()
    s0, s1 = _to_screen(probe, a), _to_screen(probe, b)
    io.add_mouse_pos_event(*s0)
    frame(rig.panel)
    frame(rig.panel)
    io.add_mouse_button_event(0, True)
    frame(rig.panel)
    for i in range(1, steps + 1):
        u = i / steps
        io.add_mouse_pos_event(s0[0] + (s1[0] - s0[0]) * u, s0[1] + (s1[1] - s0[1]) * u)
        frame(rig.panel)
    frame(rig.panel)
    io.add_mouse_button_event(0, False)
    frame(rig.panel)
    frame(rig.panel)
    io.add_mouse_pos_event(-1.0, -1.0)
    frame(rig.panel)


def _right_click(rig, probe, nid):
    """A real right-click on node `nid`'s title: the node's menu opens and
    is drawn on the frames that follow."""
    io = imgui.get_io()
    (px, py), (sx, _sy) = _node_box(rig, nid)
    io.add_mouse_pos_event(*_to_screen(probe, (px + sx * 0.35, py + 6.0)))
    frame(rig.panel)
    frame(rig.panel)
    io.add_mouse_button_event(1, True)
    frame(rig.panel)
    io.add_mouse_button_event(1, False)
    frame(rig.panel)
    frame(rig.panel)
    frame(rig.panel)


def _left_click(rig, probe, nid):
    """A real click on node `nid`'s title: selected, alone."""
    io = imgui.get_io()
    (px, py), (sx, _sy) = _node_box(rig, nid)
    io.add_mouse_pos_event(*_to_screen(probe, (px + sx * 0.35, py + 6.0)))
    frame(rig.panel)
    frame(rig.panel)
    io.add_mouse_button_event(0, True)
    frame(rig.panel)
    io.add_mouse_button_event(0, False)
    frame(rig.panel)
    frame(rig.panel)


def _centre_node(rig, probe, nid):
    """Pan so node `nid` sits in the middle of the canvas; its box after."""
    (px, py), (sx, sy) = _node_box(rig, nid)
    _centre_on(rig, probe, (px + sx / 2, py + sy / 2))
    return _node_box(rig, nid)


def _escape(rig):
    """Escape closes the open menu (keyboard nav on for the press, as
    test_ui_shell does; the shared io's flags put back after)."""
    io = imgui.get_io()
    flags = io.config_flags
    io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard
    try:
        io.add_mouse_pos_event(-1.0, -1.0)
        frame(rig.panel)
        io.add_key_event(imgui.Key.escape, True)
        frame(rig.panel)
        io.add_key_event(imgui.Key.escape, False)
        frame(rig.panel)
        frame(rig.panel)
    finally:
        io.config_flags = flags
    assert not imgui.is_popup_open("", imgui.PopupFlags_.any_popup_id)


def test_a_group_made_taken_apart_and_remade_by_the_mouse(rig, monkeypatch):
    """Row 563, by the mouse (the real editor, the harness above): two
    effects in the run box-selected and grouped from the right-click menu;
    the folded node opened from its menu; one member then the other
    dragged out of the region — the first leaves its group at once, the
    second takes the group with it (ungroup, by the mouse); the two
    regrouped take `group.2`, never `group.1` again; and a member deleted
    with the Delete key is out of the group's list on that same frame.
    The one menu item picked on each menu is the patched `menu_item_simple`;
    everything else is mouse and key events through imgui."""
    from test_graphview import _in_editor
    pairs = (*FRAME0, ("lookback", "acid.image"), ("acid", "wobble.image"),
             ("wobble", "output.all.image"))
    places = {"render:shape": [-800, 0], "render:scene": [-400, 0], "render:lookback": [0, 0],
              "render:acid": [320, 0], "render:wobble": [640, 0], "render:output.all": [960, 0]}
    _gs, probe = _drag_rig(rig, monkeypatch, *pairs, layout=places, effects=("acid", "wobble"), on=("acid", "wobble"))
    st, pre = ui_graph._state(rig.panel), rig.lib.presets
    assert pre.groups == []
    _centre_on(rig, probe, (600.0, 90.0))      # (the page pans by moving the nodes:
    (ax, ay), (aw, ah) = _node_box(rig, "render:acid")        # read them after)
    (wx, wy), (ww, wh) = _node_box(rig, "render:wobble")
    # 1. box-select the two, group them from the menu
    _box_select(rig, probe, (ax - 30, ay - 80), (wx + ww + 30, max(ay + ah, wy + wh) + 80))
    _in_editor(rig, lambda: st.__setitem__("menu_sel", ui_graph.selected_ids(st)))
    assert sorted(st["menu_sel"]) == ["render:acid", "render:wobble"]
    picked: list[str] = []
    want = {"pick": "group "}

    def item(label, *a, **k):               # one click on the item wanted, once
        picked.append(label)
        if want["pick"] and label.startswith(want["pick"]):
            want["pick"] = None
            return True
        return False
    monkeypatch.setattr(imgui, "menu_item_simple", item)
    _right_click(rig, probe, "render:acid")
    assert "group 2 nodes" in picked, picked
    assert [(g["id"], sorted(g["nodes"]), g["open"]) for g in pre.groups] == [
        ("group.1", ["render:acid", "render:wobble"], False)]
    _escape(rig)
    frame(rig.panel)
    assert st["view"].group("group.1") is not None and "render:acid" in st["hide"]
    # 2. open it from its menu, drag one member out, then the other
    picked.clear()
    want["pick"] = "open"
    _right_click(rig, probe, "group.1")
    assert "open" in picked and pre.groups[0]["open"] is True
    _escape(rig)
    frame(rig.panel)
    frame(rig.panel)
    (wx, wy), (ww, wh) = _node_box(rig, "render:wobble")
    _drag_to(rig, probe, "render:wobble", (wx + ww / 2, wy + wh / 2 + 420))
    frame(rig.panel)
    assert pre.groups[0]["nodes"] == ["render:acid"], pre.groups
    assert st["said"] == "wobble left group 1"
    (ax, ay), (aw, ah) = _node_box(rig, "render:acid")
    _drag_to(rig, probe, "render:acid", (ax + aw / 2, ay + ah / 2 - 420))
    frame(rig.panel)
    assert pre.groups == []                                 # ungrouped, by the mouse
    assert st["said"] == "acid left group 1, the last of it: the group is gone"
    assert wires_of(rig.lib) == set(pairs)                 # the graph is untouched
    # 3. regrouped, by another box (the two are 840 units apart now: zoomed
    # out so one box on screen holds both): the next number, never the old
    _zoom_out(rig, probe, 6)
    (ax, ay), (aw, ah) = _node_box(rig, "render:acid")
    (wx, wy), (ww, wh) = _node_box(rig, "render:wobble")
    _centre_on(rig, probe, ((ax + wx + ww) / 2, (ay + wy + wh) / 2))
    (ax, ay), (aw, ah) = _node_box(rig, "render:acid")
    (wx, wy), (ww, wh) = _node_box(rig, "render:wobble")
    _box_select(rig, probe, (min(ax, wx) - 30, min(ay, wy) - 60),
                (max(ax + aw, wx + ww) + 30, max(ay + ah, wy + wh) + 60))
    _in_editor(rig, lambda: st.__setitem__("menu_sel", ui_graph.selected_ids(st)))
    assert sorted(st["menu_sel"]) == ["render:acid", "render:wobble"]
    picked.clear()
    want["pick"] = "group "
    _right_click(rig, probe, "render:wobble")
    assert "group 2 nodes" in picked, picked
    assert [g["id"] for g in pre.groups] == ["group.2"]
    _escape(rig)
    frame(rig.panel)
    # 4. open it, click a member, Delete: out of the list on that frame
    assert ui_graph.set_open(rig.panel, "group.2", True) is None
    frame(rig.panel)
    frame(rig.panel)
    _centre_node(rig, probe, "render:wobble")
    _left_click(rig, probe, "render:wobble")
    io = imgui.get_io()
    io.add_key_event(imgui.Key.delete, True)
    frame(rig.panel)                    # the key queues the selection for the editor…
    frame(rig.panel)                    # …whose query on this frame drops the node
    io.add_key_event(imgui.Key.delete, False)
    assert pre.groups == [{"id": "group.2", "name": "group 2", "nodes": ["render:acid"],
                           "open": True}], (pre.groups, st["note"], st["said"])
    assert "wobble" not in {w.src for w in pre.graph.spec.wires}
    frame(rig.panel)
    assert pre.groups[0]["nodes"] == ["render:acid"]

