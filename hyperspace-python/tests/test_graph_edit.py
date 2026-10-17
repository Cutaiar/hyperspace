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
    """One table, two views, both ways: a cable made on GRAPH is a row
    ROUTING draws the next frame, and a modifier picked on the canvas is
    on ROUTING's MODIFIERS strip; deleted on ROUTING, the cable is gone
    from GRAPH."""
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
    assert any(x is b for x in drawn) and m in strip
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
    assert ui_graph.remove_node(panel, "lfo.1") == graphview.NOT_REMOVABLE.format(
        label=view.node("lfo.1").label)


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
    assert where["accept_new_item"] == {"_value_drag", "_create_render"}
    assert where["accept_deleted_item"] == {"_value_cut", "_value_node_cut",
                                            "_delete_render_cable", "_delete_render_node"}
    assert where["reject_deleted_item"] <= {"_value_cut", "_unknown_cut", "_delete",
                                            "_rig_node_cut", "_delete_render_cable",
                                            "_delete_render_node"}
    assert where["reject_new_item"] <= {"_value_drag", "_create_render"}
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
    lfo = graphview.VNode("lfo.1", "lfo", "LFO 1")
    ui_graph.DELETE_NODE.get(lfo.kind, ui_graph._rig_node_cut)(rig.panel, st, None, lfo)
    assert st["note"] == graphview.NOT_REMOVABLE.format(label="LFO 1")
    table = rig.router.table
    e, _ = edit(rig)
    e.show_macro("macro.5")
    e.connect("bus:macro.5", "base:view.bright")
    serial = table.macros_serial
    assert e.remove_node("macro.5") == []
    assert "macro.5" not in table.macros and table.macros_serial > serial
