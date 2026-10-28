"""Plan 28 N7 — a legible graph: collapsed by default, one wire per node
pair, GRAPH takes the routes.

The owner's decisions of 2026-10-20: every node starts collapsed (its
title and at most five short lines, nothing per port); one wire between
two nodes while either end is collapsed, however many params are mapped
between them, the real cables appearing when both ends are expanded; and
the GRAPH page takes over the routes and the modifiers from ROUTING,
whose desk, macros, session and sinks stay where they are.

Headless, on the harness N2 and N3 used: the shell's rig
(tests/test_ui_shell.py) with party-trip loaded, a render graph built by
`graph.default_graph`, the APC40 as a real `devices.MidiDevice` over a
stand-in adapter (tests/test_graphview_devices.py), and the page drawn
for real on `imgui_node_editor`. No preset is edited or added."""

import json
import math
from types import SimpleNamespace as NS

import numpy as np
import pytest
from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed
from test_graphview import _in_editor, stacked, thru
from test_graphview_devices import rig_devices
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import graphview, modifiers, ui, ui_graph, ui_routing
from hyperspace.app import CONTROL_SIZE
from hyperspace.bands import CEIL
from hyperspace.graphmigrate import Shows
from hyperspace.routing import Binding

DT = 1 / 60


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def party(rig):
    """party-trip on the page: its rows, a render graph with effects, the
    APC40 listed. Returns the page's state after two frames. Plan 35 T5:
    the canvas is the preset's wired frame, so the frame the render graph
    is built from — acid and palette in the run, output 2 the hands
    through them — is landed as the preset's graph too."""
    rig.lib.load("presets", "party-trip")
    spec = land_frame(rig, stacked(("acid", "palette")), Shows(), Shows(through=True))
    g = thru(stacked(("acid", "palette")), ("acid", "palette"), Shows(), Shows(through=True))
    g.section = spec.to_json()          # (what a reload lands again: test_graph_areas.load)
    rig.panel.renderer = NS(_graph=g)
    rig.panel.devices = rig_devices(rig)
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    return ui_graph._state(rig.panel)


def land_frame(rig, src, *shows):
    """The wired frame of `src` with output k's overrides for `shows[k - 1]`
    (`tests/wiredframe.shown`) landed as the loaded preset's graph."""
    from wiredframe import shown
    section = shown(src, *shows)
    spec = G.read_graph(section)
    assert not spec.notes, spec.notes
    rig.lib.presets.graph.land(spec, spec.to_json())
    return spec


def node_pair(view, c):
    return graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port)


def link(st, name):
    """What a click on a drawn wire does: select it."""
    return lambda: ed.select_link(ed.LinkId(ui_graph._id(st, "c:" + name)))


# ---------------------------------------------------------------- collapsed by default

def test_every_node_starts_collapsed_with_at_most_five_lines(rig):
    """Every node is collapsed when the page first draws: no port of its
    own is drawn — only its in / out stubs — and under its title at most
    five short lines (`graphview.summary`): a device's port count and how
    many are patched, its loudest port; a render node's params. The page
    reads as a handful of boxes and wires: far fewer wires than cables."""
    st = party(rig)
    view = st["view"]
    assert len(view.nodes) > 40 and len(view.cables) > 200
    assert st["open"] == set()
    for n in view.nodes:
        assert ui_graph.collapsed(st, n.id) and ui_graph.shown(st, n) == []
        lines = graphview.summary(n)
        assert 1 <= len(lines) <= graphview.SUMMARY_LINES, n.id
        assert all(len(t) <= 32 for t in lines), (n.id, lines)
    assert st["pin_xy"] and all(graphview.is_stub(p) for p in st["pin_xy"])
    desk = graphview.summary(view.node("device:apc40"))
    assert desk[0].endswith("patched") and " ports · " in desk[0]
    # + main's 3D switch, Fit, spacing, depth; plan 32: view.media, and the
    # factory knob 7's row on its alias view.bmp_alpha; plan 33 U: less the
    # pattern's seven (view.pattern*, view.media_*), plus fx.face_map; plan
    # 33 T7: less view.media (retired: the wire into pattern.media); less the
    # eight pattern.mod.k, the faces pattern node's since 2026-10-27
    assert graphview.summary(view.node("render:shape"))[0].startswith("42 params · ")
    assert st["wires"] < len(view.cables) / 3
    # a collapsed node takes its lines' room in the column, not its ports'
    shape = view.node("render:shape")
    assert graphview.height(shape, collapsed=True) == (
        graphview.HEAD_H + graphview.ROW_H * len(graphview.summary(shape)))
    assert graphview.height(shape, collapsed=True) < graphview.height(shape)


def test_the_apc40_to_one_shader_is_one_bundle_while_collapsed(rig):
    """The APC40 talking to the shape over two dozen params is one wire
    while either end is collapsed: one bundle per (source node, target
    node) pair, holding every value / trigger cable between them, drawn
    from the APC40's out stub to the shape's in stub."""
    st = party(rig)
    view = st["view"]
    desk_to_shape = [c for c in view.cables
                     if node_pair(view, c) == ("device:apc40", "render:shape")]
    assert len(desk_to_shape) > 10 and all(c.kind == "setter" for c in desk_to_shape)
    singles, bundles = graphview.wiring(view, lambda nid: True)
    pairs = [(b.src, b.dst) for b in bundles]
    assert len(pairs) == len(set(pairs))                 # one wire a pair
    b = next(b for b in bundles if (b.src, b.dst) == ("device:apc40", "render:shape"))
    assert b.cables == desk_to_shape and b.count == len(desk_to_shape)
    assert (b.src_port, b.dst_port) == ("nout:device:apc40", "nin:render:shape")
    # only render cables stay single
    assert all(c.kind == "render" for c, _, _ in singles)
    # on the page: that bundle is what is drawn, and none of its cables
    assert b.id in st["bundles"]
    assert ui_graph.bundle_thickness(b.count) == ui_graph.BUNDLE_MAX
    assert ui_graph.bundle_thickness(1) == ui_graph.WIRE
    # a render cable with a collapsed end lands on that node's stub
    wire = next(c for c, _, _ in singles if c.dst_port.startswith("rin:output.all"))
    assert next(x for x in singles if x[0] is wire)[2] == "nin:render:output.all"


def test_a_bundle_splits_into_its_cables_when_both_ends_expand(rig):
    """Expanding one end keeps the pair one wire; expanding both draws the
    real cables, each to its port, through N3's paths unchanged (the
    patched ports are drawn, so every cable's pins are there)."""
    st = party(rig)
    view = st["view"]
    bid = "bundle:device:apc40>render:shape"
    ui_graph.toggle_open(st, "device:apc40")
    frame(rig.panel, "graph")
    assert bid in st["bundles"]
    ui_graph.toggle_open(st, "render:shape")
    frame(rig.panel, "graph")
    assert bid not in st["bundles"]
    cables = [c for c in view.cables if node_pair(view, c) == ("device:apc40", "render:shape")]
    singles, _ = graphview.wiring(view, lambda nid: ui_graph.collapsed(st, nid))
    drawn = {c.id: (a, b) for c, a, b in singles}
    assert all(drawn[c.id] == (c.src_port, c.dst_port) for c in cables)
    assert all(c.src_port in st["pin_xy"] and c.dst_port in st["pin_xy"] for c in cables)
    # collapsed again (the node's own −): one wire once more
    ui_graph.toggle_open(st, "render:shape")
    frame(rig.panel, "graph")
    assert bid in st["bundles"]
    # expand all / collapse all
    ui_graph.expand_all(st, view, True)
    frame(rig.panel, "graph")
    assert st["bundles"] == {} and st["wires"] >= len(view.cables) - 5
    ui_graph.expand_all(st, view, False)
    assert st["open"] == set()


def test_a_bundles_hover_and_side_pane_list_its_rows(rig, monkeypatch):
    """Hovering a bundle says "<n> cables: <source port> → <param>, …" —
    the first ten, then "+ k more"; selecting it lists its rows in the side
    pane, each route as ROUTING's own row (`ui_routing._row`, the one table)."""
    st = party(rig)
    # party-trip's eight lane → pattern.mod.k routes end on the faces pattern
    # node (2026-10-27), so the analyzer → shape bundle is five more routes
    # onto shape params nothing performs, to pass ten
    table = rig.router.table
    taken = {b.target for b in table.bindings}
    free = [p.param for p in st["view"].node("render:shape").ports
            if p.param and p.param not in taken and rig.reg[p.param].modulatable
            and not rig.reg[p.param].alias]
    for k, pid in enumerate(free[:5]):
        table.add(Binding(f"lane:{k}", pid, "push", 0.2))
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    view = st["view"]
    b = st["bundles"]["bundle:analyzer>render:shape"]
    assert b.count > 10 and all(c.kind == "route" for c in b.cables)
    tip = graphview.bundle_tip(view, b)
    head, body = tip.split("\n")[:2]
    assert head == "analyzer  →  Shape"            # (plan 35 G: its label)
    assert body.startswith(f"{b.count} cables: ")
    assert body.endswith(f", + {b.count - 10} more")
    assert body.count(" → ") == 10
    first = b.cables[0]
    assert graphview.cable_words(view, first) == (
        f"{view.owner(first.src_port)[1].name} → {first.ref.target}")
    rows = []
    real = ui_routing._row
    monkeypatch.setattr(ui_routing, "_row", lambda pn, r, x, k: rows.append(x)
                        or real(pn, r, x, k))
    _in_editor(rig, link(st, b.id))
    frame(rig.panel, "graph")
    assert ui_graph._selection(st, view) == ("bundle", st["bundles"][b.id])
    frame(rig.panel, "graph")
    assert rows[-b.count:] == [c.ref for c in b.cables]


def test_a_drag_onto_a_collapsed_node_offers_its_ports_and_lands_through_edit(
        rig, monkeypatch):
    """A cable dragged from a source's port onto a collapsed node's in stub:
    let go, the picker lists that node's ports, each with the refusal
    `Edit.connect` would give (a band sets no base: refused, in words);
    the port picked lands through `Edit.connect` unchanged — a route, one
    undo step — without expanding anything."""
    st = party(rig)
    view = st["view"]
    table = rig.router.table
    target = next(p for p in view.node("render:shape").ports
                  if p.param and not p.patched and rig.reg[p.param].modulatable)
    got = {"accepted": 0, "tip": None}
    pins = (ui_graph._id(st, "out:lane:3"), ui_graph._id(st, "nin:render:shape"))
    with monkeypatch.context() as m:              # what the widget reports for the drag
        m.setattr(ed, "begin_create", lambda *a, **k: True)
        m.setattr(ed, "end_create", lambda: None)
        m.setattr(ui_graph, "new_link", lambda: pins)
        m.setattr(ed, "accept_new_item", lambda *a: got.__setitem__("accepted", 1) or True)
        m.setattr(ui_graph, "_drag_tip", lambda w: got.__setitem__("tip", w))
        frame(rig.panel, "graph")
    assert got["accepted"] == 1 and got["tip"] == "let go: pick one of Shape's ports"
    held = st["land"]
    assert held is not None and held["fixed"] == "out:lane:3" and held["node"] == "render:shape"
    by_pin = {pin: why for pin, _, _, why in held["choices"]}
    assert by_pin[f"mod:{target.param}"] is None
    assert by_pin[f"base:{target.param}"] == graphview.NO_BASE.format(what="a band")
    frame(rig.panel, "graph")                     # the picker drawn (it stays open)
    calls = []
    real = graphview.Edit.connect
    monkeypatch.setattr(graphview.Edit, "connect",
                        lambda self, a, b: calls.append((a, b)) or real(self, a, b))
    b = ui_graph.land(rig.panel, "out:lane:3", f"mod:{target.param}")
    assert calls == [("out:lane:3", f"mod:{target.param}")]
    assert isinstance(b, Binding) and table.owner(target.param) is b
    assert st["land"] is None and st["open"] == set()        # nothing was expanded
    frame(rig.panel, "graph")
    assert any(c.ref is b for c in st["bundles"]["bundle:analyzer>render:shape"].cables)
    # the wrong side, or two stubs: refused while held, in words
    assert ui_graph.stub_refusal(view, "nin:render:shape", "mod:view.bright") == (
        graphview.SAME_SIDE)
    assert ui_graph.stub_refusal(view, "nout:analyzer", "nin:render:shape") == (
        ui_graph.BOTH_STUBS)
    # Learn from a collapsed render node: its params, by port group
    params = ui_graph.learn_params(view.node("render:shape"))
    assert target.param in {p for ps in params.values() for p in ps}


def test_deleting_a_bundle_is_refused_in_words(rig, monkeypatch):
    """Delete on a selected bundle: kept, the head says "expand a node to
    edit its cables", and the table is as it was."""
    st = party(rig)
    view = st["view"]
    table = rig.router.table
    rows = list(table.bindings)
    b = st["bundles"]["bundle:analyzer>render:shape"]
    queue = [ui_graph._id(st, "c:" + b.id)]
    said = []

    class Id:
        k = 0

        def id(self):
            return self.k

    def query(lk):
        if not queue:
            return False
        lk.k = queue.pop(0)
        return True
    monkeypatch.setattr(ed, "begin_delete", lambda: True)
    monkeypatch.setattr(ed, "end_delete", lambda: None)
    monkeypatch.setattr(ed, "NodeId", Id)
    monkeypatch.setattr(ed, "LinkId", Id)
    monkeypatch.setattr(ed, "query_deleted_node", lambda nk: False)
    monkeypatch.setattr(ed, "query_deleted_link", query)
    monkeypatch.setattr(ed, "accept_deleted_item", lambda *a: said.append("accepted"))
    monkeypatch.setattr(ed, "reject_deleted_item", lambda: said.append("rejected"))
    ui_graph._delete(rig.panel, st, view)
    assert said == ["rejected"] and st["note"] == graphview.EXPAND_TO_EDIT
    assert table.bindings == rows


def test_tidy_collapses_all_relays_and_says_what_it_did(rig):
    """Tidy always does something visible or says why not: on a page as
    laid out, "already tidy"; with nodes expanded and one moved, every node
    collapsed, every position forgotten, the column layout back — and the
    head says "laid out <n> nodes, every one collapsed"."""
    st = party(rig)
    view = st["view"]
    st["tidy"] = True
    frame(rig.panel, "graph")
    assert st["said"] == ui_graph.ALREADY_TIDY
    ui_graph.toggle_open(st, "render:shape")
    rig.lib.presets.layout["render:camera"] = [900, 40]
    frame(rig.panel, "graph")
    assert st["applied"]["render:camera"] == (900.0, 40.0)
    st["tidy"] = True
    frame(rig.panel, "graph")
    idle = sum(n.idle for n in view.nodes)               # N9: the areas' words
    k = len({n.area for n in view.nodes if not n.idle})     # (plan 35 G: by primitive)
    assert st["said"] == (f"laid out {len(view.nodes) - idle} nodes in {k} areas, every one "
                          f"collapsed · {idle} idle off the canvas")
    assert st["open"] == set() and rig.lib.presets.layout == {}
    auto = ui_graph.layout_of(st, view)
    assert all(st["applied"][n.id] == auto[n.id] for n in view.nodes
               if not n.idle)                           # N9: an idle node is not placed
    assert st["applied"]["render:camera"] != (900.0, 40.0)


def test_beside_shows_only_with_a_selection(rig, monkeypatch):
    """The details chip is drawn only while something is selected and the
    page is narrower than `WIDE`, labelled by what a click does; at `WIDE`
    or more the details sit beside the canvas with no chip."""
    assert ui_graph.beside_chip(False, 500.0, False) is None
    assert ui_graph.beside_chip(True, 500.0, False) == "details beside"
    assert ui_graph.beside_chip(True, 500.0, True) == "details below"
    assert ui_graph.beside_chip(True, ui_graph.WIDE, False) is None
    st = party(rig)
    chips = []
    chip = ui.chip
    monkeypatch.setattr(ui, "chip", lambda label, *a, **k: chips.append(label)
                        or chip(label, *a, **k))
    frame(rig.panel, "graph")
    assert "tidy##graph" in chips and not any(c.startswith("details") for c in chips)
    assert "expand all##graph" in chips
    # a bundle selected on the control window's narrow page: the chip, by what it does
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    _in_editor(rig, link(st, next(iter(st["bundles"]))))
    frame(rig.panel, "graph")
    chips.clear()
    frame(rig.panel, "graph")
    assert "details beside##graph" in chips
    st["beside"] = True
    chips.clear()
    frame(rig.panel, "graph")
    assert "details below##graph" in chips


def test_a_selection_never_resizes_the_canvas(rig, monkeypatch):
    """The owner (2026-10-24): opening the details must not pan the graph.
    The node editor re-centres its view whenever its canvas changes size
    (`CanvasSizeMode` has no "keep the top-left"), so the canvas is always
    the page's whole size and the details are laid over its right edge —
    or its bottom on a narrow page — and every node stays where it was."""
    st = party(rig)
    sizes = []
    begin = ui_graph.ed.begin
    monkeypatch.setattr(ui_graph.ed, "begin",
                        lambda name, size, *a: sizes.append((size.x, size.y))
                        or begin(name, size, *a))
    frame(rig.panel, "graph")
    alone = sizes[-1]
    _in_editor(rig, link(st, next(iter(st["bundles"]))))
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    assert ui_graph._selection(st, rig.view) is not None
    assert sizes[-1] == alone                       # beside: the canvas keeps its size
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    frame(rig.panel, "graph")
    narrow = sizes[-1]
    st["beside"] = False                            # below, on the narrow page
    frame(rig.panel, "graph")
    assert sizes[-1] == narrow
    pos, size = ui_graph.details_rect((10.0, 20.0), (1000.0, 600.0), wide=True)
    assert (pos, size) == ((10.0 + 1000.0 - ui_graph.SIDE_W, 20.0), (ui_graph.SIDE_W, 600.0))
    pos, size = ui_graph.details_rect((10.0, 20.0), (500.0, 600.0), wide=False)
    assert (pos, size) == ((10.0, 20.0 + 600.0 - ui_graph.BELOW_H), (500.0, ui_graph.BELOW_H))


def test_a_right_click_on_the_details_opens_no_graph_menu(rig, monkeypatch):
    """The owner (2026-10-24): a right-click on the details laid over the
    canvas opened the canvas's menu, not the control's Learn menu. The node
    editor still sees a right-click there (the details are over its canvas),
    so the page notes that the mouse is over them (`st["over_details"]`)
    and `_menus` opens no graph menu then; off them it does as before."""
    st = party(rig)
    _in_editor(rig, link(st, next(iter(st["bundles"]))))
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    assert ui_graph._selection(st, rig.view) is not None
    monkeypatch.setattr(ui_graph.ed, "show_background_context_menu", lambda: True)
    opened = []
    real_open = imgui.open_popup
    monkeypatch.setattr(imgui, "open_popup", lambda name, *a: (opened.append(name),
                                                               real_open(name, *a))[1])
    io = imgui.get_io()
    (x, y), (w, h) = st["details_rect"]
    io.add_mouse_pos_event(x + w / 2, y + h / 2)     # over the details
    frame(rig.panel, "graph")
    assert st["over_details"] and ui_graph.MENU not in opened
    opened.clear()
    io.add_mouse_pos_event(x - 200.0, y + h / 2)     # over the canvas, left of them
    frame(rig.panel, "graph")
    assert not st["over_details"] and ui_graph.MENU in opened


def test_routing_no_longer_draws_routes_or_modifiers_but_their_functions_stay(
        rig, monkeypatch):
    """ROUTING draws a pointer line where its routes and its MODIFIERS strip
    were, then its desk, macros, session and sinks as before; the functions
    of the two sections stay and keep working (the canvas and the tests
    call them)."""
    panel, router = rig.panel, rig.router
    rig.lib.load("presets", "party-trip")
    m = ui_routing.add_modifier(panel, "smooth", ["lane:0"])
    texts, rows, strips = [], [], []
    td, tc = imgui.text_disabled, imgui.text_colored
    monkeypatch.setattr(imgui, "text_disabled", lambda s: texts.append(s) or td(s))
    monkeypatch.setattr(imgui, "text_colored", lambda c, s: texts.append(s) or tc(c, s))
    row, mods = ui_routing._row, ui_routing.modifiers
    monkeypatch.setattr(ui_routing, "_row", lambda *a: rows.append(a) or row(*a))
    monkeypatch.setattr(ui_routing, "modifiers", lambda *a: strips.append(a) or mods(*a))
    frame(panel, "routing")
    frame(panel)
    assert ui_routing.POINTER in texts
    assert "ROUTES" not in texts and "MODIFIERS" not in texts and not rows and not strips
    assert {"DESK  ·  PRESET LAYER", "MACROS", "SESSION", "SINKS"} <= set(texts)
    assert texts.index(ui_routing.POINTER) < texts.index("DESK  ·  PRESET LAYER")
    # the functions stay
    assert ui_routing._sources(panel, router) and ui_routing._targets(panel)
    b = ui_routing.add_route(panel, "fx.acid.mix", source=m.address, depth=0.4)
    assert b is not None and router.table.owner("fx.acid.mix") is b
    ui_routing.set_modifier_input(panel, m.id, 0, "lane:1")
    assert router.table.modifier(m.id).inputs == ("lane:1",)
    ui_routing.remove_modifier(panel, m.id)
    assert router.table.modifier(m.id) is None
    # "Route a lane here…" opens GRAPH now
    monkeypatch.setattr(imgui, "menu_item_simple", lambda label, *a, **k: True)
    imgui.new_frame()
    imgui.begin("menu")
    ui_routing.ctx_item(panel, rig.reg["view.bright"])
    imgui.end()
    imgui.end_frame()
    assert panel.page == ui.PAGE_KEYS.index("graph")


def hands(router, energy):
    """A hands device's feed, as far as the right hand's energy goes."""
    if "hand" not in router.names:
        router.names["hand"] = {"right.energy": 0}
        router.labels["hand"] = ["R energy"]
    router.feed("hand", None if energy is None else [energy])


def drop(rig, monkeypatch, a: str, b: str) -> dict:
    """One frame of the page with the widget reporting a cable dragged from
    pin `a` and let go on pin `b` (what `_create` sees). Returns what the
    drag said: accepted / rejected, its tooltip."""
    st = ui_graph._state(rig.panel)
    got = {"accepted": 0, "rejected": 0, "tip": None}
    pins = (ui_graph._id(st, a), ui_graph._id(st, b))
    with monkeypatch.context() as m:
        m.setattr(ed, "begin_create", lambda *x, **k: True)
        m.setattr(ed, "end_create", lambda: None)
        m.setattr(ui_graph, "new_link", lambda: pins)
        m.setattr(ed, "accept_new_item",
                  lambda *x: got.__setitem__("accepted", got["accepted"] + 1) or True)
        m.setattr(ed, "reject_new_item",
                  lambda *x: got.__setitem__("rejected", got["rejected"] + 1))
        m.setattr(ui_graph, "_drag_tip", lambda w: got.__setitem__("tip", w))
        frame(rig.panel, "graph")
    return got


def picked(st, pin):
    """The stub's picker is open (`st["land"]`) and offers `pin`; its source."""
    held = st["land"]
    assert held is not None, "no picker opened"
    ok = {p for p, _, _, why in held["choices"] if why is None}
    assert pin in ok, (pin, sorted(ok))
    return held["fixed"]


def test_the_smoothed_energy_times_band_patch_from_graph_alone(rig, monkeypatch):
    """N1's patch — right hand energy, smoothed, times band 0, into acid
    mix — built from the GRAPH page alone, as check 265 does it (the twin
    of test_modifiers' ROUTING test): two modifiers from the picker, every
    cable dropped through the page's own drop path with the nodes left
    collapsed — the hand's energy onto the smooth's stub, the smooth's out
    stub onto the combine's (a one-output node's stub is its output), band
    0 onto the combine, the combine's out stub onto the acid's — each port
    picked from the stub's menu; the combine's `how` on the side pane's
    editor. Played, it is what N1's is."""
    panel, reg, router = rig.panel, rig.reg, rig.router
    st = party(rig)
    router.table.set_routes([])                     # a preset with no routes yet
    hands(router, 0.0)
    frame(panel, "graph")
    smooth = ui_graph.add_modifier(panel, "smooth", at=(300, 40))
    combine = ui_graph.add_modifier(panel, "combine", at=(300, 200))
    frame(panel, "graph")
    assert ui_graph.collapsed(st, smooth.id) and ui_graph.collapsed(st, combine.id)
    hops = [("out:hand:right.energy", f"nin:{smooth.id}", f"in:{smooth.id}.0"),
            (f"nout:{smooth.id}", f"nin:{combine.id}", f"in:{combine.id}.0"),
            ("out:lane:0", f"nin:{combine.id}", f"in:{combine.id}.1"),
            (f"nout:{combine.id}", "nin:render:acid", "mod:fx.acid.mix")]
    for a, b, pin in hops:
        got = drop(rig, monkeypatch, a, b)
        assert got["accepted"] == 1 and got["rejected"] == 0, (a, b, got)
        fixed = picked(st, pin)
        assert fixed == graphview.stub_pin(st["view"], a)        # a stub: its one output
        res = ui_graph.land(panel, fixed, pin)
        assert not isinstance(res, graphview.Refusal), (a, b, res)
        frame(panel, "graph")
    assert st["open"] == set()                                  # nothing was expanded
    b = router.table.owner("fx.acid.mix")
    assert isinstance(b, Binding) and b.source == combine.address
    assert [m.inputs for m in router.table.modifiers] == [
        ("hand:right.energy",), (smooth.address, "lane:0")]
    # two stubs where neither stands for one output: still refused, in words
    got = drop(rig, monkeypatch, "nout:analyzer", f"nin:{combine.id}")
    assert got["rejected"] == 1 and got["tip"] == ui_graph.BOTH_STUBS
    # the side pane of the selected combine: the strip's editor, its `how`
    blocks = []
    block = ui_routing.modifier_block
    monkeypatch.setattr(ui_routing, "modifier_block",
                        lambda pn, r, m, **k: blocks.append(m.id) or block(pn, r, m, **k))
    view = st["view"]
    _in_editor(rig, lambda: ed.select_node(ed.NodeId(ui_graph._id(st, "n:" + combine.id))))
    frame(panel, "graph")
    assert ui_graph._selection(st, view)[1].id == combine.id and blocks[-1] == combine.id
    reg[f"{combine.id}.how"].set(modifiers.HOW.index("mul"))   # what its combo sets
    # play it: the hand to full energy, band 0 at a half
    p = reg["fx.acid.mix"]
    seen = []
    for _ in range(30):
        hands(router, 1.0)
        router.modulate(NS(lanes=np.array([0.5 * CEIL, 0.0, 0.0])), dt=DT)
        reg.apply()
        seen.append(p.eff_norm)
    smoothed = 1 - math.exp(-30 * DT / 0.05)
    assert seen[-1] == pytest.approx(0.5 * smoothed, abs=1e-3)
    assert seen == sorted(seen)
    assert ui_routing.modifier_output(router, combine.id) == pytest.approx(seen[-1], abs=1e-6)


def test_route_a_lane_here_selects_the_new_route_on_graph(rig, monkeypatch):
    """"Route a lane here…" adds the route and opens GRAPH with it selected:
    the wire it is drawn in (here its bundle, the analyzer into the shape)
    is the selection, and the side pane lists the new row first."""
    panel = rig.panel
    st = party(rig)
    before = st["bundles"]["bundle:analyzer>render:shape"].count
    target = next(p for p in st["view"].node("render:shape").ports
                  if p.param and not p.patched and rig.reg[p.param].modulatable)
    frame(panel, "view")
    with monkeypatch.context() as m:
        m.setattr(imgui, "menu_item_simple", lambda label, *a, **k: True)
        imgui.new_frame()
        imgui.begin("menu")
        ui_routing.ctx_item(panel, rig.reg[target.param])
        imgui.end()
        imgui.end_frame()
    b = rig.router.table.owner(target.param)
    assert isinstance(b, Binding) and panel.page == ui.PAGE_KEYS.index("graph")
    rows = []
    real = ui_routing._row
    monkeypatch.setattr(ui_routing, "_row", lambda pn, r, x, k: rows.append(x)
                        or real(pn, r, x, k))
    frame(panel, "graph")                            # drawn, selected
    sel = ui_graph._selection(st, st["view"])
    assert sel is not None and sel[0] == "bundle" and sel[1].count == before + 1
    assert any(c.ref is b for c in sel[1].cables) and st["focus"] is b
    rows.clear()
    frame(panel, "graph")                            # the pane: the new row first
    assert rows and rows[0] is b


def test_a_dormant_bundle_draws_faint_and_a_live_one_moves_without_a_rebuild(
        rig, monkeypatch):
    """A bundle whose every cable is dormant is drawn at the dormant alpha;
    a live one's reading follows its source frame to frame with the same
    view and the same wiring (no rebuild)."""
    st = party(rig)
    links = {}
    real = ed.link
    monkeypatch.setattr(ed, "link", lambda lid, a, b, col, thick: links.__setitem__(
        lid.id(), (col.w, thick)) or real(lid, a, b, col, thick))
    router = rig.router
    router.feed("lfo", [0.3, 0.0, 0.0, 0.0])
    frame(rig.panel, "graph")
    view, wiring = st["view"], st["wiring"]
    dormant = next(b for b in st["bundles"].values() if b.dormant)
    assert links[ui_graph._id(st, "c:" + dormant.id)][0] == pytest.approx(ui_graph.DORMANT_ALPHA)
    lfo = st["bundles"]["bundle:lfo.1>render:camera"]
    assert not lfo.dormant and lfo.live == pytest.approx(0.3)
    assert links[ui_graph._id(st, "c:" + lfo.id)][0] == 1.0
    router.feed("lfo", [0.8, 0.0, 0.0, 0.0])
    frame(rig.panel, "graph")
    assert st["view"] is view and st["wiring"] is wiring
    assert st["bundles"]["bundle:lfo.1>render:camera"].live == pytest.approx(0.8)


def test_a_bundles_menu_and_a_nodes_learn_menu_draw(rig, monkeypatch):
    """The right-click menus N7 adds, drawn once each with every submenu
    open: a bundle's (what it holds, expand both ends, delete disabled with
    the words) and a collapsed render node's learn ▸ group ▸ param."""
    import hyperspace.ui as ui_mod
    st = party(rig)
    items, menus = [], []
    monkeypatch.setattr(ui_mod.imgui, "begin_menu", lambda label, *a: menus.append(label) or True)
    monkeypatch.setattr(ui_mod.imgui, "end_menu", lambda: None)
    monkeypatch.setattr(ui_mod.imgui, "menu_item_simple",
                        lambda label, *a, **k: items.append(label) and False)
    bid = "bundle:analyzer>render:shape"
    for subject in (("cable", bid), ("node", "render:shape")):
        st["menu"] = subject
        imgui.new_frame()
        imgui.begin("menu")
        ui_graph.menu(rig.panel, st, st["view"])
        imgui.end()
        imgui.end_frame()
    assert "expand both ends" in items
    assert f"delete: {graphview.EXPAND_TO_EDIT}" in items
    assert "expand" in items and "learn" in menus
    shape = [p.param for p in st["view"].node("render:shape").ports if p.param]
    assert sum(1 for m in menus if m.partition("##")[2] in shape) == len(shape)  # each param
    assert st["open"] == set()                          # nothing picked: nothing changed


def test_the_page_draws_in_every_state(rig):
    """The page drawn once per state, for real on the node editor: all
    collapsed, a node expanded, all expanded with every port, a bundle
    selected, a modifier selected, the stub's picker open, after a tidy —
    and nothing raises; the SYSTEM line follows."""
    st = party(rig)
    view = st["view"]
    m = ui_graph.add_modifier(rig.panel, "smooth", at=(300, 40))
    frame(rig.panel, "graph")
    ui_graph.toggle_open(st, "device:apc40")
    frame(rig.panel, "graph")
    ui_graph.expand_all(st, st["view"], True)
    st["patched_only"] = False
    frame(rig.panel, "graph")
    ui_graph.expand_all(st, st["view"], False)
    st["patched_only"] = True
    frame(rig.panel, "graph")
    bid = next(iter(st["bundles"]))
    _in_editor(rig, link(st, bid))
    frame(rig.panel, "graph")
    assert ui_graph._selection(st, st["view"])[0] == "bundle"
    _in_editor(rig, lambda: (ed.clear_selection(),
                             ed.select_node(ed.NodeId(ui_graph._id(st, "n:" + m.id)))))
    frame(rig.panel, "graph")
    ui_graph.open_land(rig.panel, st, st["view"], "out:lane:2", "render:shape")
    frame(rig.panel, "graph")
    st["tidy"] = True
    frame(rig.panel, "graph")
    assert ui_graph.timing_line(rig.panel).startswith("graph page: ")
    assert view is not None
    frame(rig.panel, "system")


# ---------------------------------------------------------------- plan 33 T6: one selection

def test_selecting_an_effect_node_sets_the_shared_selection(rig):
    """Plan 33 U: the effect selected on GRAPH is the panel's one selection
    (`Panel.fx_selected`, shared with the FX page, saved nowhere), and
    `select_effect` — the FX page's "show on GRAPH" — selects that node on
    the canvas next frame (the side pane its strip) — one on its area's
    idle line (an off effect) too: the line opens to draw it."""
    st = party(rig)
    rig.reg["fx.acid.on"].set(1)                 # drawn …
    rig.reg["fx.palette.on"].set(0)              # … and off, on the shaders' idle line
    frame(rig.panel, "graph")
    view = st["view"]
    on, off = view.node("render:acid"), view.node("render:palette")
    assert not on.idle and off.idle
    assert rig.panel.fx_selected is None
    _in_editor(rig, lambda: (ed.clear_selection(),
                             ed.select_node(ed.NodeId(ui_graph._id(st, "n:" + on.id)))))
    frame(rig.panel, "graph")
    assert rig.panel.fx_selected == on.ref.effect
    ui_graph.select_effect(rig.panel, off.ref.effect)
    assert rig.panel.fx_selected == off.ref.effect
    for _ in range(3):
        frame(rig.panel, "graph")
    sel = ui_graph._selection(st, st["view"])
    assert sel is not None and sel[1].id == off.id
    assert rig.panel.fx_selected == off.ref.effect
    assert graphview.EFFECTS_AREA in st["idle_open"]


# ---------------------------------------------------------------- the owner, 2026-10-24: a node's controls

def pick(rig, st, nid):
    """Select node `nid` as a click on the canvas does — its area's idle
    line opened first if it sits there — and draw the page twice (the side
    panel reads last frame's selection)."""
    n = st["view"].node(nid)
    if n.idle:
        st.setdefault("idle_open", set()).add(n.area)
        frame(rig.panel, "graph")
    _in_editor(rig, lambda: (ed.clear_selection(),
                             ed.select_node(ed.NodeId(ui_graph._id(st, "n:" + nid)))))
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    sel = ui_graph._selection(st, st["view"])
    assert sel is not None and sel[1].id == nid
    return sel[1]


def spy_rows(monkeypatch):
    rows = []
    row = ui.Panel._row
    monkeypatch.setattr(ui.Panel, "_row", lambda self, pid, *a, **k: rows.append(pid)
                        or row(self, pid, *a, **k))
    return rows


def undo_watch(rig):
    """An undo watcher over the rig's registry and table (app.main's, without
    the marks), ticked by hand: `tick()` one frame on, `settle()` past
    `SETTLE_S`."""
    from hyperspace import undo
    u = undo.Undo(rig.reg, rig.router.table)
    t = [100.0]

    def tick(dt=1 / 60):
        t[0] += dt
        u.tick(t[0])

    def settle():
        tick(undo.SETTLE_S + 0.1)
        tick()
    return u, tick, settle


def test_a_media_nodes_params_are_rows_in_the_side_panel(rig, monkeypatch):
    """The owner (2026-10-24): a media node's ports showed its params but
    nothing edited them. Selected, the side panel draws each of its params
    as the panel's own row (`Panel._row`: the slider or the combo, its
    label's Learn menu) — rate, jog, position, loop, slot and fit."""
    st = party(rig)
    rows = spy_rows(monkeypatch)
    pick(rig, st, "render:channel.a")
    for key in ("rate", "jog", "pos", "loop", "slot", "fit"):
        assert f"media.a.{key}" in rows, key


def test_a_side_panel_row_edits_through_the_param(rig, monkeypatch):
    """A drag on the side panel's rate slider is the slider's own write
    (`Param.set_value`): the param moves, and the undo watcher makes one
    step of it, as on the MEDIA page."""
    st = party(rig)
    pick(rig, st, "render:channel.a")
    u, tick, settle = undo_watch(rig)
    settle()
    u.stack.clear()
    p = rig.reg["media.a.rate"]
    want = p.lo + 0.75 * (p.hi - p.lo)
    real = ui.imgui.slider_float
    monkeypatch.setattr(ui.imgui, "slider_float",
                        lambda label, v, *a: (True, want) if label == "##media.a.rate"
                        else real(label, v, *a))
    frame(rig.panel, "graph")
    monkeypatch.setattr(ui.imgui, "slider_float", real)
    assert p.base == pytest.approx(want)
    tick()
    settle()
    assert len(u.stack) == 1


def test_a_big_node_folds_its_groups(rig, monkeypatch):
    """The shape holds about fifty params: more than `FOLD_AT` rows, so each
    group folds under its own header — the first (primary) group and a
    group holding a patched port open, the rest closed (kept per node in the page's state) — and only the open
    groups' rows are drawn; within a group the patched ports come first."""
    st = party(rig)
    rows = []                       # every row: a slider, a combo, a toggle's checkbox
    one = ui_graph._param_row
    monkeypatch.setattr(ui_graph, "_param_row", lambda pn, pid: rows.append(pid) or one(pn, pid))
    shape = pick(rig, st, "render:shape")
    groups = ui_graph.side_groups(rig.panel, shape)
    assert sum(len(pids) for _, pids in groups) > ui_graph.FOLD_AT
    folds = st["side_open"][shape.id]
    patched = {p.group for p in shape.ports if p.param and p.patched}
    assert patched and set(folds) == {g for g, _ in groups}
    assert any(not v for v in folds.values())
    by_param = {p.param: p for p in shape.ports if p.param}
    for g, pids in groups:
        assert folds[g] == (g in patched or g == groups[0][0]), g
        drawn = [pid for pid in pids if pid in rows]
        assert drawn == (pids if folds[g] else []), g
        flags = [by_param[pid].patched for pid in pids]
        assert flags == sorted(flags, reverse=True), g



def test_the_faces_pattern_side_pane_shows_every_shader_input(rig, monkeypatch):
    """The owner, 2026-10-27: the faces pattern node's side pane showed the
    selector, the mix and the media, not the shader's own inputs. Now every
    `pattern.mod.k` (scale, glow, warp, speed, colour, sharp …) is a row on
    the pattern node's pane — after the selector and the mix, before the
    media — under `patterns.label(k)`; the shape's pane has none of them.
    party-trip routes the bands onto the eight, so their group is open."""
    from hyperspace import patterns

    st = party(rig)
    rows = []
    one = ui_graph._param_row
    monkeypatch.setattr(ui_graph, "_param_row", lambda pn, pid: rows.append(pid) or one(pn, pid))
    pat = pick(rig, st, "render:pattern")
    mods = [f"pattern.mod.{k}" for k in range(8)]
    groups = ui_graph.side_groups(rig.panel, pat)
    assert [g for g, _ in groups] == ["pattern", "media"]
    head = ["view.pattern", "view.pattern_mix"]
    assert sorted(groups[0][1]) == sorted(head + mods)    # (patched rows first)
    # the node's ports: the selector, the mix, the eight in order, the media
    order = [p.param for p in pat.ports if p.param]
    assert order[:10] == head + mods
    assert sorted(order[10:]) == sorted(groups[1][1])
    assert groups[1][1] and all(pid.startswith("view.media_") for pid in groups[1][1])
    names = {p.param: p.name for p in pat.ports if p.param}
    assert [names[pid] for pid in mods] == [patterns.label(k) for k in range(8)]
    assert all(rig.reg[pid].tip == patterns.tip(k) for k, pid in enumerate(mods))
    assert set(mods) <= set(rows)                  # drawn: the group is open (patched)
    shape = st["view"].node("render:shape")
    assert not any(p.param in mods for p in shape.ports)
    assert not any(pid in mods for _, pids in ui_graph.side_groups(rig.panel, shape)
                   for pid in pids)



def test_the_faces_pattern_group_starts_open_with_nothing_routed(rig, monkeypatch):
    """The owner, 2026-10-27: the shader's inputs must be shown. With no
    route onto the pattern node (party-trip's eight lane → pattern.mod
    routes removed), its pane is still over `FOLD_AT`: the node's primary
    group ("pattern": selector, mix, the eight) starts open, every row
    drawn; only the secondary "media" group starts folded."""
    table = rig.router.table
    st = party(rig)
    pat_ids = {p.param for p in st["view"].node("render:pattern").ports if p.param}
    table.bindings = [b for b in table.bindings if b.target not in pat_ids]
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    rows = []
    one = ui_graph._param_row
    monkeypatch.setattr(ui_graph, "_param_row", lambda pn, pid: rows.append(pid) or one(pn, pid))
    pat = pick(rig, st, "render:pattern")
    assert not any(p.patched for p in pat.ports if p.param)
    groups = dict(ui_graph.side_groups(rig.panel, pat))
    assert list(groups) == ["pattern", "media"]
    assert sum(map(len, groups.values())) > ui_graph.FOLD_AT
    assert st["side_open"][pat.id] == {"pattern": True, "media": False}
    assert set(groups["pattern"]) <= set(rows)
    assert not set(groups["media"]) & set(rows)


def test_every_nodes_side_panel_draws(rig):
    """Each node of party-trip selected in turn, its idle line opened: the
    side panel draws (its rows, its folds, its chip) without an imgui error
    — a toggle's checkbox, a trigger's chip and a combo beside the sliders."""
    st = party(rig)
    # plan 35 T5: and every frame kind and plan 34's nodes, declared (faint)
    e = graphview.Edit(graph=rig.lib.presets.graph, push=lambda label: None)
    # (plan 36 T2: the pattern is in already — the faces' wire says it;
    # T4: an echo is the look-back's pin — its item adds the look-back)
    for kind, f in (("backdrop", None), ("guide", None), ("echo", "2"),
                    ("dream", None), ("delay", None), ("resize", None), ("composite", None)):
        assert e.add_node(kind, f) is None, kind
    frame(rig.panel, "graph")
    st["idle_open"] = set(graphview.AREAS) | {graphview.OTHER}
    frame(rig.panel, "graph")
    drawn = [n.id for n in st["view"].nodes if ui_graph.drawn_node(st, n)]
    assert len(drawn) > 40
    assert {"render:copy", "render:backdrop", "render:pattern", "render:hands.guide",
            "render:lookback", "render:dream", "render:delay", "render:resize",
            "render:output.all", "render:camera"} <= set(drawn)
    for nid in drawn:
        pick(rig, st, nid)


def test_every_node_has_a_label_and_a_hover(rig):
    """Plan 35 G (V's table): every render node of every graph fixture's
    view is titled by `label_of` and hovers `HOVERS`' line with its id (and
    its params' prefix where it differs) — never `frame`, `fx`,
    `grounded` or `capture`."""
    from test_graph_areas import WIRED as fixtures
    from test_graph_areas import load_fixture
    assert graphview.label_of("hands.2") == "Hands 2"
    assert graphview.label_of("channel.a") == "Channel A"
    assert graphview.label_of("hands.2.layer") == "Hands layer 2"
    assert graphview.label_of("echo.3") == "Echo 3"
    assert graphview.label_of("copy.2", of="acid") == "copy of acid (2)"
    assert graphview.label_of("acid.2") == "acid 2"
    assert graphview.label_of("output.all") == "All outputs"
    assert graphview.label_of("output.2") == "Output 2"
    assert graphview.label_of("output.2", [NS(n=2, name="projector")]) == "projector"
    assert graphview.hover_of("lookback").endswith(" · id lookback · params dream.*")
    assert graphview.hover_of("output.2").endswith(" · id output.2")
    for fixture in fixtures:
        st = load_fixture(rig, fixture)
        for n in st["view"].nodes:
            if n.kind not in ("render", "output", "channel"):
                continue
            assert n.label and n.label not in ("frame", "fx", "grounded", "capture"), (
                fixture, n.id)
            name = n.id.partition(":")[2]
            assert n.status.endswith(f"· id {name}") or f"· id {name} · params " in n.status, (
                fixture, n.id, n.status)
            assert n.status.partition(" · id ")[0], (fixture, n.id)


def test_home_page_maps_each_node_kind(rig):
    """`home_page(node)`: the page that node's controls live on, and what to
    select there — None for a node with none (a switch, a modifier)."""
    from hyperspace import ui_media
    st = party(rig)
    view = st["view"]
    panel = rig.panel

    def home(n):
        got = ui_graph.home_page(n)
        return None if got is None else got[0]
    key, sel = ui_graph.home_page(view.node("render:channel.c"))
    assert key == "media"
    sel(panel)
    assert ui_media._state(panel)["sel"] == "c"
    key, sel = ui_graph.home_page(view.node("render:acid"))
    assert key == "fx"
    sel(panel)
    assert panel.fx_selected == "acid"
    # plan 35 G: the pattern and the backdrop are drawn where the section
    # names them (party-trip's does not): by their stand-ins
    V = graphview.VNode
    assert home(V("render:pattern", "render", "Faces pattern", ref=G.PatternNode())) == "faces"
    assert home(V("render:backdrop", "render", "Backdrop",
                  ref=G.BackdropNode("backdrop"))) == "media"
    assert home(view.node("render:shape")) == "view"
    # (plan 36 T4: party-trip draws no look-back — its stand-in, and the dream's)
    assert home(V("render:lookback", "render", "Look-back", ref=G.History("lookback"))) == \
        "lookback"
    assert home(V("render:dream", "render", "Dream", ref=G.DreamNode("dream"))) == "lookback"
    assert home(view.node("render:output.all")) == "output"
    # a copy: FX with its original selected
    key, sel = ui_graph.home_page(view.node("render:copy"))
    panel.fx_selected = None
    sel(panel)
    assert key == "fx" and panel.fx_selected == view.node("render:copy").ref.effect
    key, sel = ui_graph.home_page(view.node("lfo.3"))
    assert key == "lfo"
    sel(panel)
    assert panel._lfo_open == 3
    key, sel = ui_graph.home_page(graphview.VNode("env.7", "env", "env 7"))
    assert key == "seq"
    sel(panel)
    assert panel._seq_env == 7
    assert home(graphview.VNode(graphview.SEQ, graphview.SEQ, "sequencer")) == "seq"
    assert home(view.node("render:hands")) == "hands"
    assert home(view.node("render:output.1")) == "output"
    assert home(graphview.VNode("render:switch", "render", "switch",
                                ref=G.SwitchNode("switch"))) is None
    assert home(graphview.VNode("smooth.1", "modifier", "smooth")) is None
    assert home(view.node("macro.1")) is None
    assert all(k in ui.PAGE_KEYS for k in map(home, view.nodes) if k is not None)


def test_open_on_page_switches_page_and_selects(rig, monkeypatch):
    """The side panel's "open on MEDIA" chip: the panel turns to MEDIA with
    the node's channel selected there."""
    from hyperspace import ui_media
    st = party(rig)
    pick(rig, st, "render:channel.c")
    chips = []
    chip = ui.chip
    monkeypatch.setattr(ui, "chip", lambda label, *a, **k: chips.append(label)
                        or label.startswith("open on MEDIA") or chip(label, *a, **k))
    frame(rig.panel, "graph")
    monkeypatch.setattr(ui, "chip", chip)
    assert any(c.startswith("open on MEDIA") for c in chips)
    assert rig.panel.page == ui.PAGE_KEYS.index("media")
    assert ui_media._state(rig.panel)["sel"] == "c"
    frame(rig.panel)


def test_the_switch_block_picks_an_input_with_one_click(rig, monkeypatch):
    """The owner (2026-10-24): a switch had no control but Learn. Its side
    panel opens on a row of chips — off, then 1 … 8, each named by what
    feeds that input ("3 · Channel C", "2 · —" for nothing) — the pick lit;
    one click sets `switch.select` through the param, one undo step. The
    select row with its Learn menu sits under them, and the canvas's
    summary says the pick."""
    st = party(rig)
    e = graphview.Edit(graph=rig.lib.presets.graph, push=lambda label: None)
    assert e.add_node("switch") is None and e.added == "switch"
    assert e.wire("rout:channel.a", "rin:switch/in1") is None
    assert e.wire("rout:channel.c", "rin:switch/in3") is None
    frame(rig.panel, "graph")
    sw = st["view"].node("render:switch")
    assert ui_graph.switch_feeds(st["view"], sw)[:3] == ["Channel A", None, "Channel C"]
    rows = spy_rows(monkeypatch)
    pick(rig, st, "render:switch")
    u, tick, settle = undo_watch(rig)
    settle()
    u.stack.clear()
    labels = []
    lit = ui.lit_chip
    monkeypatch.setattr(ui, "lit_chip", lambda label, on, *a, **k: labels.append(label)
                        or label.startswith("3 · ") or lit(label, on, *a, **k))
    frame(rig.panel, "graph")
    monkeypatch.setattr(ui, "lit_chip", lit)
    shown = [x.partition("##")[0] for x in labels if "##graph.side." in x]
    assert "off" in shown and "3 · Channel C" in shown and "2 · —" in shown
    assert "1 · Channel A" in shown and len(shown) == 9
    assert rig.reg["switch.select"].value == 3
    tick()
    settle()
    assert len(u.stack) == 1
    assert "switch.select" in rows
    frame(rig.panel, "graph")
    assert "picks in3" in graphview.summary(st["view"].node("render:switch"))


def test_a_resize_nodes_params_are_rows_in_the_side_panel(rig, monkeypatch):
    """Plan 34 T5: `resize[.n].*` are rows on the resize's node
    (`OWNERS["resize"]`), not a `group:resize` node of their own: eight
    rows drawn, an edit the param's own in one undo step, no home page."""
    from test_graph_areas import load_fixture

    from hyperspace import params
    st = load_fixture(rig, "resize-crop")
    view = st["view"]
    assert view.node("group:resize") is None
    n = view.node("render:resize")
    assert ui_graph.side_groups(rig.panel, n) == [("resize", params.resize_ids("resize"))]
    assert ui_graph.home_page(n) is None
    rows = spy_rows(monkeypatch)
    pick(rig, st, "render:resize")
    drawn = list(dict.fromkeys(r for r in rows if r.startswith("resize.")))   # (two frames)
    assert drawn == params.resize_ids("resize")
    assert len(params.resize_ids("resize")) == 8
    u, tick, settle = undo_watch(rig)
    settle()
    u.stack.clear()
    p = rig.reg["resize.crop_w"]
    p.set_value(0.4)
    tick()
    settle()
    assert p.base == pytest.approx(0.4) and len(u.stack) == 1


def test_the_side_column_width_is_clamped_and_this_macs(tmp_path):
    """The owner (2026-10-27): the details column must be resizable. Its
    width is held between `SIDE_MIN` and what leaves `CANVAS_MIN` of canvas,
    laid out by `details_rect`, and remembered per Mac in ``ui.json`` —
    a missing, broken or wrong-typed file is no width at all, and a write
    keeps whatever else the file holds."""
    assert ui_graph.side_width(ui_graph.SIDE_W, 1000.0) == ui_graph.SIDE_W
    assert ui_graph.side_width(100.0, 1000.0) == ui_graph.SIDE_MIN
    assert ui_graph.side_width(900.0, 1000.0) == 1000.0 - ui_graph.CANVAS_MIN
    assert ui_graph.side_width(900.0, 300.0) == ui_graph.SIDE_MIN     # never under the minimum
    pos, size = ui_graph.details_rect((10.0, 20.0), (1000.0, 600.0), wide=True, side_w=460.0)
    assert (pos, size) == ((10.0 + 1000.0 - 460.0, 20.0), (460.0, 600.0))
    assert ui_graph.read_side(tmp_path) is None                        # no file
    (tmp_path / ui_graph.UI_FILE).write_text("{not json")
    assert ui_graph.read_side(tmp_path) is None                        # a broken one
    (tmp_path / ui_graph.UI_FILE).write_text('{"graph": {"side_w": "wide"}, "other": 1}')
    assert ui_graph.read_side(tmp_path) is None                        # not a number
    ui_graph.write_side(tmp_path, 460.25)
    assert ui_graph.read_side(tmp_path) == 460.2                       # rounded to a tenth
    doc = json.loads((tmp_path / ui_graph.UI_FILE).read_text())
    assert doc["other"] == 1 and doc["graph"]["side_w"] == 460.2       # the rest kept
    ui_graph.write_side(tmp_path / "missing" / "dir", 300.0)           # a failed write: no raise


def test_the_side_column_takes_its_width_from_this_mac_and_a_drag(rig):
    """On a wide page the details column is as wide as this Mac remembers
    (`<machine>/ui.json`, read once, clamped to the page each frame but
    never overwritten by a narrow one); the grip on its left edge, held and
    moved, resizes it, and letting go writes the width back."""
    st = party(rig)
    io = imgui.get_io()

    def sized(width: float) -> None:                    # a frame with the panel this wide
        io.display_size = imgui.ImVec2(max(width + 40.0, 820.0), 900.0)
        rig.panel.reg["ui.page"].set(ui.PAGE_KEYS.index("graph"))
        imgui.new_frame()
        imgui.set_window_size("CONTROLS", imgui.ImVec2(width, 876.0))
        rig.panel.draw(1 / 60, 60.0)
        imgui.end_frame()

    machine = rig.lib.machine
    ui_graph.write_side(machine, 460.0)
    st["side_w"] = st["machine"] = None                 # as before the file was asked
    _in_editor(rig, link(st, next(iter(st["bundles"]))))
    sized(1200.0)
    sized(1200.0)
    assert ui_graph._selection(st, rig.view) is not None
    assert st["side_w"] == 460.0 and st["machine"] == machine
    (x, y), (w, h) = st["details_rect"]
    assert w == 460.0
    # a narrow page clamps the frame's column, not the memory
    st["beside"] = True
    sized(600.0)
    assert st["details_rect"][1][0] < 460.0 and st["side_w"] == 460.0
    sized(1200.0)
    (x, y), (w, h) = st["details_rect"]
    assert w == 460.0
    # the grip: press on the column's left edge, move left, let go
    io.add_mouse_pos_event(x + ui_graph.GRIP_W / 2, y + h / 2)
    sized(1200.0)
    io.add_mouse_button_event(0, True)
    sized(1200.0)
    io.add_mouse_pos_event(x + ui_graph.GRIP_W / 2 - 60.0, y + h / 2)
    sized(1200.0)
    assert st["side_drag"] and abs(st["side_w"] - 520.0) < 1e-6
    io.add_mouse_button_event(0, False)
    sized(1200.0)
    sized(1200.0)
    assert not st["side_drag"]
    assert ui_graph.read_side(machine) == 520.0           # written when the drag let go
    assert st["details_rect"][1][0] == 520.0
