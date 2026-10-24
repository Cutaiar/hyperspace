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
from imgui_bundle import imgui
from test_graphview import FakeDevice
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import devices, graphview, learn, ui_graph, ui_routing
from hyperspace.devices import Port
from hyperspace.learn import Learn
from hyperspace.routing import MOD_OPS, Binding, is_session_row

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
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
        if (p.modulatable and not p.alias and p.kind is Kind.CONTINUOUS and not p.integer
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
    Learn depth; a band lane the fader. It lands as one cable next build.
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
    assert lane.op == "push" and lane.value == learn.PUSH_DEPTH   # a centred target: push
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
    assert e.connect("out:lane:0", "base:view.bright") == "a band sets no base; aim at mod"
    assert len(table.bindings) == n
    knob = e.connect("out:cc:0:52", "base:camera.zoom")
    assert (knob.op, knob.layer, knob.target) == ("abs", "preset", "camera.zoom")
    assert not is_session_row(knob)
    pad = e.connect("out:pad:BACK", "base:view.points")
    assert (pad.source, pad.target, pad.op) == ("pad:BACK", "view.points", "toggle")
    assert is_session_row(pad) and pad in table.bindings
    _, view = edit(rig, leap())
    refs = [c.ref for c in cables(view, "setter")]
    assert any(x is knob for x in refs) and any(x is pad for x in refs)
    # a macro: a base subscriber (it moves nothing as it lands) and a depth one
    route = e.connect("out:lane:3", f"mod:{free_param(rig).id}")
    e, view = edit(rig, leap())
    was = reg["view.bright"].base
    s = e.connect("bus:macro.2", "base:view.bright")
    assert s.base == "view.bright" and s in table.macros["macro.2"].subs
    assert reg["view.bright"].base == was
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
    key = next(c for c in cables(view, "setter") if is_session_row(c.ref))
    res = ui_graph.disconnect(panel, key)
    assert res == graphview.SESSION_ROW.format(what=key.ref.source)
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
    table = rig.router.table
    view = graphview.build(table, rig.reg, rig.router, None, None, None)
    e = graphview.Edit(table, rig.reg, rig.router, view, graph=rig.lib.presets.graph)
    assert graphview.RENDER_NOT_YET not in (
        e.connect("rout:shape", "rin:scene/geometry"),
        e.refusal("rin:scene/geometry", "rout:shape"))
    got = e.connect("rout:shape", "rin:scene/geometry")
    assert isinstance(got, graphview.Refusal) and got == (
        "shape is drawn by the scene, not wired")
    assert e.refusal("rin:output.1/image", "rout:ghost") == (
        "wire ghost → output.1.image — ghost makes geometry, output.1.image takes a picture")
    # input end first: ordered, and it lands
    assert e.connect("rin:output.2/hands", "rout:hands") is None
    assert rig.lib.presets.graph.spec.wires[0].dst == "output.2.hands"
    wire = graphview.VCable("wire:hands>output.2/hands", "rout:hands", "rin:output.2/hands",
                            graphview.IMAGE, kind="render")
    assert e.disconnect(wire) is None and rig.lib.presets.graph.spec is None
    got = e.disconnect(wire)
    assert isinstance(got, graphview.Refusal) and "is the default graph's" in got
    got = e.remove_node("render:shape")
    assert isinstance(got, graphview.Refusal) and got.startswith("shape is drawn")
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
    ui_graph.remove_node(panel, m.id)
    assert table.modifier(m.id) is None and route in table.bindings
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
                                            "_rig_node_cut", "_delete_render_cable",
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
    assert b.op in MOD_OPS and not is_session_row(b)
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
    output node is N4's (the frame's own nodes refused in words), a
    kind not listed is the rig's; a macro node's delete goes through the
    table's `set_macros`, its label and subscribers with it."""
    from imgui_bundle import imgui_node_editor as ed
    monkeypatch.setattr(ed, "reject_deleted_item", lambda: None)
    st = {"note": ""}
    shape = graphview.VNode("render:shape", "render", "shape")
    ui_graph.DELETE_NODE[shape.kind](rig.panel, st, None, shape)
    assert st["note"] == "shape is drawn by the scene, not wired"
    assert ui_graph.DELETE_NODE["output"] is ui_graph._delete_render_node
    group = graphview.VNode("group:tempo", "group", "tempo")
    ui_graph.DELETE_NODE.get(group.kind, ui_graph._rig_node_cut)(rig.panel, st, None, group)
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


def test_a_render_edit_s_line_goes_at_the_next_edit_or_refusal(rig):
    """`st["said"]` (the last render edit's words on the head) is cleared
    by the next value edit, landed or refused (`_settle`), and by any
    refusal, render or not; a render landing puts its own words back."""
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
    ui_graph._rig_node_cut(panel, st, None, graphview.VNode("lfo.1", "lfo", "LFO 1"))
    assert st["said"] == "" and st["note"] == graphview.NOT_REMOVABLE.format(label="LFO 1")


def test_a_selection_delete_keeps_its_first_refusal_s_words(rig, monkeypatch):
    """Delete on a selection of three: the frame's own shape (refused), a
    modifier (it goes) and an LFO (refused) — the head keeps the first
    refusal's words for the frame, not wiped by the modifier's landing nor
    replaced by the LFO's. The next delete starts afresh: a landing alone
    clears the note."""
    from imgui_bundle import imgui_node_editor as ed
    panel, table = rig.panel, rig.router.table
    st = ui_graph._state(panel)
    m = ui_graph.add_modifier(panel, "threshold")
    shape = graphview.VNode("render:shape", "render", "shape")
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
    assert st["note"] == "shape is drawn by the scene, not wired"   # … the first words stay
    assert "held" not in st
    m2 = ui_graph.add_modifier(panel, "threshold")
    st["note"] = "an old refusal"
    queue[:] = [ui_graph._id(st, f"n:{m2.id}")]
    view.nodes.append(graphview.VNode(m2.id, "modifier", "threshold"))
    ui_graph._delete(panel, st, view)
    assert table.modifier(m2.id) is None and st["note"] == ""


# ---------------------------------------------------------------- plan 33 T6: the free graph

def _section(*pairs, nodes=()):
    return {"nodes": list(nodes), "wires": [{"from": a, "to": b} for a, b in pairs]}


def free_rig(tmp_path, *pairs, nodes=(), undo_rig=False):
    """A headless rig over a scratch library with preset "Free" loaded —
    its graph section the free graph's wires `pairs` and `nodes` — the
    section attached to a stub renderer, and an Edit on it whose undo steps
    are counted (`undo_rig`: test_undo's boot, its Undo real)."""
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
    put(rig.home, "Free", graph=_section(*pairs, nodes=nodes))
    rig.lib.load(PRESETS, "Free")
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


def test_the_picker_adds_an_effect_unwired(tmp_path):
    """Plan 33 U: the picker's effect is the next instance, in the section
    and on no wire — it reaches nothing, so the canvas draws it faint with
    "reaches nothing" (`VNode.faint`), never idle — and a switch is added
    the same way (`switch`, its `select` declared); the run is untouched."""
    from test_graphview import views

    from hyperspace import graph as G
    from hyperspace.outputs import Switches
    rig, e, pushed = free_rig(tmp_path, ("frame", "acid.image"), ("acid", "fx.image"))
    before = wires_of(rig)
    assert ("switch", None, "switch") in graphview.picker(e)
    assert e.add_node("effect", "acid") is None and e.added == "acid.2"
    spec = rig.presets.graph.spec
    assert G.EffectAt("acid", 2) in spec.effects and wires_of(rig) == before
    assert "acid.2" not in G.reaches(spec) and G.run_of(spec) == ("acid",)
    assert e.add_node("switch") is None and e.added == "switch"
    spec = rig.presets.graph.spec
    assert [s.name for s in spec.switches] == ["switch"] and "switch.select" in rig.reg
    assert wires_of(rig) == before and pushed == ["add acid.2", "add switch"]
    # on the canvas: faint, drawn, saying so
    g = G.default_graph(views(Switches()), spec.wiring(), effects=("acid", "acid.2"))
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    for nid in ("render:acid.2", "render:switch"):
        n = view.node(nid)
        assert n is not None and n.faint and not n.idle, nid
        assert graphview.summary(n)[0] == graphview.REACHES_NOTHING == "reaches nothing"
    assert not view.node("render:acid").faint


def test_insert_effect_on_a_render_cable(tmp_path):
    """"insert effect ▸ kaleido" on the cable `media.a → shape.faces`: the
    next kaleido instance, wired `media.a → kaleido.2.image`,
    `kaleido.2 → shape.faces` in one landing; one undo puts the one wire
    back. Inserted into the empty run `frame → fx.image`, the run is
    `frame → new → fx.image` (R9)."""
    from test_undo import settle

    from hyperspace import graph as G
    rig, e, pushed = free_rig(tmp_path, ("frame", "fx.image"), ("media.a", "shape.faces"),
                              undo_rig=True)
    cable = graphview.VCable("c", "rout:media.a", "rin:shape/faces", graphview.IMAGE,
                             kind="render")
    # (R25: no wire, node or placement holds kaleido, so it is instance 1)
    assert e.insert_effect(cable, "kaleido") is None and e.added == "kaleido"
    got = wires_of(rig)
    assert ("media.a", "kaleido.image") in got and ("kaleido", "shape.faces") in got
    assert ("media.a", "shape.faces") not in got and len(pushed) == 1
    settle(rig)
    assert rig.undo.undo()
    assert ("media.a", "shape.faces") in wires_of(rig)
    assert "kaleido" not in {x.name for x in rig.presets.graph.spec.effects}
    # into the empty run: frame → acid → fx.image
    assert e.insert_effect(("frame", "fx.image"), "acid") is None
    assert G.run_of(rig.presets.graph.spec) == ("acid",)
    assert ("frame", "fx.image") not in wires_of(rig)
    assert e.insert_effect(cable, "teapot") == "no teapot effect in this build"


def test_inserting_an_effect_no_one_holds_uses_instance_one_and_switches_it_on(tmp_path):
    """R25: an effect inserted on a cable, or added from the picker, that no
    wire, node or placement in the section holds is the file itself
    (instance 1), and it is switched on (`fx.<name>.on`) in the same
    landing — the first gesture shows something."""
    from hyperspace import graph as G
    rig, e, pushed = free_rig(tmp_path, ("frame", "fx.image"))
    reg = rig.reg
    assert not reg["fx.kaleido.on"].value and not reg["fx.wobble.on"].value
    assert e.insert_effect(("frame", "fx.image"), "kaleido") is None and e.added == "kaleido"
    assert G.run_of(rig.presets.graph.spec) == ("kaleido",)
    assert reg["fx.kaleido.on"].value is True and pushed == ["insert kaleido into frame → fx.image"]
    assert e.add_node("effect", "wobble") is None and e.added == "wobble"
    assert reg["fx.wobble.on"].value is True
    assert "wobble" in {x.name for x in rig.presets.graph.spec.effects}


def test_a_second_insert_of_the_same_file_takes_instance_two(tmp_path):
    """R25: the run holds kaleido, so the next kaleido inserted is
    `kaleido.2`, and it is switched on too."""
    from hyperspace import graph as G
    rig, e, _ = free_rig(tmp_path, ("frame", "fx.image"))
    assert e.insert_effect(("frame", "fx.image"), "kaleido") is None and e.added == "kaleido"
    assert e.insert_effect(("kaleido", "fx.image"), "kaleido") is None
    assert e.added == "kaleido.2"
    assert G.run_of(rig.presets.graph.spec) == ("kaleido", "kaleido.2")
    assert rig.reg["fx.kaleido.2.on"].value is True and rig.reg["fx.kaleido.on"].value is True


def test_undo_of_an_insert_restores_the_on_value_too(tmp_path):
    """R25: the insert and its `on` are one undo step — one undo takes the
    effect off the cable and puts `fx.kaleido.on` back off."""
    from test_undo import settle

    from hyperspace import graph as G
    rig, e, _ = free_rig(tmp_path, ("frame", "fx.image"), undo_rig=True)
    assert rig.reg["fx.kaleido.on"].value is False
    assert e.insert_effect(("frame", "fx.image"), "kaleido") is None
    assert rig.reg["fx.kaleido.on"].value is True
    settle(rig)
    assert len(rig.undo.stack) == 1 and rig.undo.undo()
    assert rig.reg["fx.kaleido.on"].value is False
    assert G.run_of(rig.presets.graph.spec) == () and wires_of(rig) == {("frame", "fx.image")}


def test_switch_over_the_channels_wires_all_eight_and_keeps_the_channel(tmp_path):
    """R28: the picker's "switch over the channels ▸ faces media" is one
    landing: a new switch, `media.a … h → in1 … in8`, the switch into
    `pattern.media` in place of what fed it, and `select` the channel that
    fed it (c: 3). "▸ backdrop" on a backdrop fed by nothing is a second
    switch at select 1."""
    rig, e, pushed = free_rig(tmp_path, ("frame", "fx.image"), ("media.c", "pattern.media"))
    items = graphview.picker(e)
    assert ("channels", "pattern.media", "faces media") in items
    assert ("channels", "backdrop.image", "backdrop") in items
    assert e.switch_channels("pattern.media") is None and e.added == "switch"
    got = wires_of(rig)
    for i, c in enumerate("abcdefgh", 1):
        assert (f"media.{c}", f"switch.in{i}") in got
    assert ("switch", "pattern.media") in got and ("media.c", "pattern.media") not in got
    assert rig.reg["switch.select"].value == 3 and len(pushed) == 1
    assert e.switch_channels("backdrop.image") is None and e.added == "switch.2"
    assert ("switch.2", "backdrop.image") in wires_of(rig)
    assert rig.reg["switch.2.select"].value == 1 and len(pushed) == 2
    assert e.switch_channels("output.1.image") == (
        "a switch over the channels goes into pattern.media or backdrop.image")


def test_undo_of_switch_over_the_channels_puts_the_channel_back(tmp_path):
    """R28: the switch, its nine wires and its `select` are one undo step:
    one undo leaves `media.c → pattern.media` and no switch."""
    from test_undo import settle
    rig, e, _ = free_rig(tmp_path, ("frame", "fx.image"), ("media.c", "pattern.media"),
                         undo_rig=True)
    assert e.switch_channels("pattern.media") is None
    assert rig.reg["switch.select"].value == 3
    settle(rig)
    assert len(rig.undo.stack) == 1 and rig.undo.undo()
    assert wires_of(rig) == {("frame", "fx.image"), ("media.c", "pattern.media")}
    assert rig.presets.graph.spec.switches == () and "switch.select" not in rig.reg


def test_the_run_keeps_its_frame_head(tmp_path):
    """R9 / R20: the section always keeps a `frame` run. Deleting a cable
    of the run takes the effect it leads into out of the run (the last
    cable's, the effect it leaves), the run closed over it; taking the
    last effect out leaves `frame → fx.image`; deleting `frame → fx.image`
    itself is refused in words, nothing changed; a run effect deleted
    closes the run over it too."""
    from hyperspace import graph as G
    rig, e, pushed = free_rig(tmp_path, ("frame", "acid.image"), ("acid", "wobble.image"),
                              ("wobble", "fx.image"))
    assert e.unwire("acid", "wobble.image") is None
    assert G.run_of(rig.presets.graph.spec) == ("acid",)
    assert ("wobble", "fx.image") not in wires_of(rig)
    assert e.unwire("acid", "fx.image") is None
    assert G.run_of(rig.presets.graph.spec) == ()
    assert wires_of(rig) == {("frame", "fx.image")}
    n = len(pushed)
    assert e.unwire("frame", "fx.image") == graphview.RUN_KEPT == (
        "the run starts at frame and ends at fx.image — insert effects into it")
    assert wires_of(rig) == {("frame", "fx.image")} and len(pushed) == n
    assert e.insert_effect(("frame", "fx.image"), "acid") is None
    assert e.drop_node("acid.2") is None and wires_of(rig) == {("frame", "fx.image")}


def test_reordering_the_run_is_rewiring(tmp_path):
    """`frame → acid → wobble → fx.image`: acid dragged onto the cable
    `wobble → fx.image` — out of its place, the run closed over it, then
    in after wobble — is one landing, one undo step: the run is wobble,
    acid."""
    from hyperspace import graph as G
    rig, e, pushed = free_rig(tmp_path, ("frame", "acid.image"), ("acid", "wobble.image"),
                              ("wobble", "fx.image"))
    assert e.place_effect(("wobble", "fx.image"), "acid") is None
    assert G.run_of(rig.presets.graph.spec) == ("wobble", "acid")
    assert pushed == ["move acid onto wobble → fx.image"]
    assert e.place_effect(("wobble", "acid.image"), "acid") == "acid is on that cable already"


def test_dropping_a_free_effect_on_the_run_inserts_it(rig):
    """A free effect node (`wobble.2`: in the section, no cable in or out)
    let go on the canvas over the cable `frame → fx.image` is inserted into
    it (`ui_graph.dropped`, as a modifier is into a value cable) — it is in
    the run; one let go over nothing stays where it is."""
    from types import SimpleNamespace as NS

    from test_graphview import views
    from test_presets import put

    from hyperspace import graph as G
    from hyperspace.outputs import Switches
    put(rig.lib.home, "Free", graph=_section(
        ("frame", "fx.image"), nodes=[{"kind": "effect", "file": "wobble", "instance": 2}]))
    rig.lib.load("presets", "Free")
    gs = rig.lib.presets.graph
    rig.panel.renderer = NS(_graph=G.default_graph(views(Switches()), gs.spec.wiring(),
                                                   effects=("wobble", "wobble.2")))
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    view = st["view"]
    assert view.node("render:wobble.2").faint and view.node("render:frame") is not None
    cable = next(c for c in view.cables
                 if (c.src_port, c.dst_port) == ("rout:frame", "rin:fx/image"))
    st["pin_xy"].update({graphview.stub_out("render:frame"): (0.0, 0.0),
                         graphview.stub_in("render:fx"): (400.0, 0.0)})
    assert ui_graph.dropped(rig.panel, view, "render:wobble.2", (900.0, 900.0)) is None
    assert G.run_of(gs.spec) == ()
    assert ui_graph.dropped(rig.panel, view, "render:wobble.2", (200.0, 0.0)) is cable
    assert G.run_of(gs.spec) == ("wobble.2",)


def test_an_instance_one_effect_taken_out_of_the_run_stays_faint(tmp_path):
    """R21 (row 349): `acid` taken out of `frame → acid → fx.image` leaves
    the empty run and is kept in the section — `{"kind": "effect", "file":
    "acid"}`, on no wire — drawn faint, "reaches nothing"; saved, the preset
    is `/5` (`/4` has no word for it); one undo puts it back in the run."""
    import json

    from test_graphview import views
    from test_undo import settle

    from hyperspace import graph as G
    from hyperspace import graphmigrate
    from hyperspace.outputs import Switches
    rig, e, pushed = free_rig(tmp_path, ("frame", "acid.image"), ("acid", "fx.image"),
                              undo_rig=True)
    rig.reg["fx.acid.on"].set(True)              # (R26: live, so /4 cannot say it)
    settle(rig)
    rig.undo.clear()
    assert e.unwire("frame", "acid.image") is None and len(pushed) == 1
    spec = rig.presets.graph.spec
    assert G.run_of(spec) == () and wires_of(rig) == {("frame", "fx.image")}
    assert G.EffectAt("acid", 1) in spec.effects
    assert {"kind": "effect", "file": "acid"} in rig.presets.graph.free_doc()["nodes"]
    g = G.default_graph(views(Switches()), spec.wiring(), effects=("acid",))
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    n = view.node("render:acid")
    assert n is not None and n.faint and not n.idle
    assert graphview.summary(n)[0] == graphview.REACHES_NOTHING
    # a /5 save: legacy_values has no /4 words for it, the old build's section drops it
    assert graphmigrate.legacy_values(spec.to_json(), {"fx.acid.on": True}) is None
    assert graphmigrate.legacy_section(spec.to_json()) is None
    doc = json.loads(rig.presets.save_as("Out").read_text())
    assert doc["schema"] == "hyperspace.preset/5"
    assert {"kind": "effect", "file": "acid"} in doc["graph"]["nodes"]
    settle(rig)
    assert rig.undo.undo()
    assert G.run_of(rig.presets.graph.spec) == ("acid",)
    # wired in again, it is named by its wires alone
    rig2, e2, _ = free_rig(tmp_path / "again", ("frame", "acid.image"), ("acid", "fx.image"))
    assert e2.unwire("acid", "fx.image") is None
    assert e2.place_effect(("frame", "fx.image"), "acid") is None
    assert rig2.presets.graph.spec.to_json()["nodes"] == []


def test_an_unwired_instance_one_switched_off_saves_as_four(tmp_path):
    """R26 (refines R21): `acid` taken out of the run and switched off is
    nothing `/4` lacks a word for — `legacy_values` takes the unwired
    instance-1 entry (`legacy_section` strips it), so the preset saves as
    `/4` again; while acid is still on it is `/5` (row 349)."""
    import json

    from hyperspace import graphmigrate
    rig, e, _ = free_rig(tmp_path, ("frame", "acid.image"), ("acid", "fx.image"))
    rig.reg["fx.acid.on"].set(True)
    assert e.unwire("frame", "acid.image") is None
    section = rig.presets.graph.spec.to_json()
    assert {"kind": "effect", "file": "acid"} in section["nodes"]
    assert graphmigrate.legacy_values(section, {"fx.acid.on": True}) is None
    assert json.loads(rig.presets.save_as("On").read_text())["schema"] == "hyperspace.preset/5"
    rig.reg["fx.acid.on"].set(False)
    assert graphmigrate.legacy_values(section, {"fx.acid.on": False}) is not None
    doc = json.loads(rig.presets.save_as("Off").read_text())
    assert doc["schema"] != "hyperspace.preset/5" and "graph" not in doc   # (/4 or lower)


def test_an_unwired_instance_one_round_trips():
    """R21: an unplaced instance 1 — no `instance` key, or `instance: 1` —
    is read, written back as `{"kind": "effect", "file": …}` and read again
    the same; D1's placed forms are as they were."""
    from hyperspace import graph as G
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


def test_dragging_a_run_member_onto_another_cable_moves_it(rig, monkeypatch):
    """R22: an effect already wired (`acid` in `frame → acid → wobble →
    fx.image`) let go on another picture cable (`wobble → fx.image`) is
    moved there in one undo step — the run is wobble, acid; let go on its
    own cables, or on nothing, it stays where it is."""
    from types import SimpleNamespace as NS

    from test_graphview import views
    from test_presets import put

    from hyperspace import graph as G
    from hyperspace import undo as undo_mod
    from hyperspace.outputs import Switches
    put(rig.lib.home, "Run", graph=_section(("frame", "acid.image"), ("acid", "wobble.image"),
                                            ("wobble", "fx.image")))
    rig.lib.load("presets", "Run")
    gs = rig.lib.presets.graph
    rig.panel.renderer = NS(_graph=G.default_graph(views(Switches()), gs.spec.wiring(),
                                                   effects=("acid", "wobble")))
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    view = st["view"]
    pushed = []
    monkeypatch.setattr(undo_mod, "push",
                        lambda label, load=False: pushed.append(label))
    xy = {"render:frame": 0.0, "render:acid": 300.0, "render:wobble": 600.0,
          "render:fx": 900.0}
    for nid, x in xy.items():
        st["pin_xy"][graphview.stub_out(nid)] = (x + 100.0, 0.0)
        st["pin_xy"][graphview.stub_in(nid)] = (x, 0.0)
    # on its own cables (frame → acid, acid → wobble), and on nothing: no change
    assert ui_graph.dropped(rig.panel, view, "render:acid", (200.0, 0.0)) is None
    assert ui_graph.dropped(rig.panel, view, "render:acid", (500.0, 900.0)) is None
    assert G.run_of(gs.spec) == ("acid", "wobble") and pushed == []
    cable = next(c for c in view.cables if c.dst_port == "rin:fx/image")
    assert ui_graph.dropped(rig.panel, view, "render:acid", (800.0, 0.0)) is cable
    assert G.run_of(gs.spec) == ("wobble", "acid")
    assert pushed == ["move acid onto wobble → fx.image"]


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


def test_route_from_lists_the_lfos_and_envelopes_on_a_modulatable_param(banks, rig,
                                                                         monkeypatch):
    """On a modulatable param the submenu is every LFO, then every
    envelope, by its bank's label, then new LFO / new envelope; a trigger
    and a param no lane may drive have none. The shared param menu
    (`Panel._ctx_learn`) draws it — on fx.glimmer.mix, between the Learn
    items and Learn sink."""
    panel, reg = banks.panel, banks.r.reg
    opened, items = drawn_route_from(panel, reg["t.x"], monkeypatch)
    assert opened == [ui_graph.ROUTE_FROM]
    assert [i[0] for i in items] == VOICES + ["new LFO", "new envelope"]
    assert all(enabled and not checked for _, checked, enabled in items)
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
    g = rig.reg["fx.glimmer.mix"]
    imgui.new_frame()
    imgui.begin("menu")
    p._ctx_learn(g, g)
    p._ctx_learn(rig.reg["view.bmp_alpha"], rig.reg["view.bmp_alpha"])
    imgui.end()
    imgui.end_frame()
    monkeypatch.undo()
    assert seen == ["fx.glimmer.mix", "view.bmp_alpha"]
    assert ui_graph.route_from_items(p, rig.reg["view.bmp_alpha"]) is None
    assert [i[0] for i in ui_graph.route_from_items(p, g)][:4] == VOICES[:4]


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
    param makes the row it made before (the table's: its out port is not
    declared centred, so a plain param takes the fader; a centred pin a
    push at PUSH_DEPTH)."""
    r, panel, table = banks.r, banks.panel, banks.r.router.table
    p, _ = _glimmer_mix(r)
    drawn_route_from(panel, p, monkeypatch, pick="LFO 1")
    made = next(b for b in table.bindings if b.target == p.id)
    assert made.source.startswith("lfo:")
    assert (made.op, made.value) == ("position", 1.0)
    assert learn.row_for("lfo:0", p) == Binding("lfo:0", p.id, "position", 1.0)
    assert learn.row_for("lfo:0", p, centred=True) == Binding(
        "lfo:0", p.id, "push", learn.PUSH_DEPTH)
