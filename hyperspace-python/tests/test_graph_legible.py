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

import math
from types import SimpleNamespace as NS

import numpy as np
import pytest
from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed
from test_graphview import _in_editor, views
from test_graphview_devices import rig_devices
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import graphview, modifiers, ui, ui_graph, ui_routing
from hyperspace.app import CONTROL_SIZE
from hyperspace.bands import CEIL
from hyperspace.outputs import Switches
from hyperspace.routing import Binding

DT = 1 / 60


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def party(rig):
    """party-trip on the page: its rows, a render graph with effects, the
    APC40 listed. Returns the page's state after two frames."""
    rig.lib.load("presets", "party-trip")
    rig.panel.renderer = NS(_graph=G.default_graph(views(Switches(), Switches(through=True)),
                                                   effects=("acid", "palette")))
    rig.panel.devices = rig_devices(rig)
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    return ui_graph._state(rig.panel)


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
    assert graphview.summary(view.node("render:shape"))[0].startswith("51 params · ")
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
    assert all(c.kind == "render" for c, _, _ in singles)   # only render cables stay single
    # on the page: that bundle is what is drawn, and none of its cables
    assert b.id in st["bundles"]
    assert ui_graph.bundle_thickness(b.count) == ui_graph.BUNDLE_MAX
    assert ui_graph.bundle_thickness(1) == ui_graph.WIRE
    # a render cable with a collapsed end lands on that node's stub
    wire = next(c for c, _, _ in singles if c.dst_port.startswith("rin:output.1"))
    assert next(x for x in singles if x[0] is wire)[2] == "nin:render:output.1"


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
    view = st["view"]
    b = st["bundles"]["bundle:analyzer>render:shape"]
    assert b.count > 10 and all(c.kind == "route" for c in b.cables)
    tip = graphview.bundle_tip(view, b)
    head, body = tip.split("\n")[:2]
    assert head == "analyzer  →  shape"
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
    assert got["accepted"] == 1 and got["tip"] == "let go: pick one of shape's ports"
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
    rig.lib.presets.layout["render:eye"] = [900, 40]
    frame(rig.panel, "graph")
    assert st["applied"]["render:eye"] == (900.0, 40.0)
    st["tidy"] = True
    frame(rig.panel, "graph")
    assert st["said"] == ui_graph.TIDIED.format(n=len(view.nodes))
    assert st["open"] == set() and rig.lib.presets.layout == {}
    auto = ui_graph.layout_of(st, view)
    assert all(st["applied"][n.id] == auto[n.id] for n in view.nodes)
    assert st["applied"]["render:eye"] != (900.0, 40.0)


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


def test_the_smoothed_energy_times_band_patch_from_graph_alone(rig, monkeypatch):
    """N1's patch — right hand energy, smoothed, times band 0, into acid
    mix — built from the GRAPH page's own functions alone (the twin of
    test_modifiers' ROUTING test): two modifiers from the picker, their
    inputs by cables (one landed on a collapsed node's stub), the combine's
    `how` on the side pane's editor, and the cable into acid mix; then
    played, it is what N1's is."""
    panel, reg, router = rig.panel, rig.reg, rig.router
    rig.lib.load("presets", "party-trip")
    router.table.set_routes([])                     # a preset with no routes yet
    hands(router, 0.0)
    frame(panel, "graph")
    st = ui_graph._state(panel)
    smooth = ui_graph.add_modifier(panel, "smooth", at=(300, 40))
    frame(panel, "graph")
    # the hand's energy dropped on the collapsed smooth's stub: its input picked
    choices = ui_graph.open_land(panel, st, st["view"], "out:hand:right.energy", smooth.id)
    ok = [pin for pin, _, _, why in choices if why is None]
    assert ok[0] == f"in:{smooth.id}.0"             # its input, then its params' mod stubs
    assert set(ok[1:]) == {f"mod:{smooth.id}.{k}" for k in ("attack", "release", "spring")}
    ui_graph.land(panel, "out:hand:right.energy", f"in:{smooth.id}.0")
    combine = ui_graph.add_modifier(panel, "combine", at=(300, 200))
    frame(panel, "graph")
    assert not isinstance(ui_graph.connect(panel, f"out:{smooth.address}",
                                           f"in:{combine.id}.0"), graphview.Refusal)
    assert not isinstance(ui_graph.connect(panel, "out:lane:0", f"in:{combine.id}.1"),
                          graphview.Refusal)
    # the side pane of the selected combine: the strip's editor, its `how`
    blocks = []
    block = ui_routing.modifier_block
    monkeypatch.setattr(ui_routing, "modifier_block",
                        lambda pn, r, m, **k: blocks.append(m.id) or block(pn, r, m, **k))
    frame(panel, "graph")
    view = st["view"]
    _in_editor(rig, lambda: ed.select_node(ed.NodeId(ui_graph._id(st, "n:" + combine.id))))
    frame(panel, "graph")
    assert ui_graph._selection(st, view)[1].id == combine.id and blocks[-1] == combine.id
    reg[f"{combine.id}.how"].set(modifiers.HOW.index("mul"))   # what its combo sets
    b = ui_graph.connect(panel, f"out:{combine.address}", "mod:fx.acid.mix")
    assert isinstance(b, Binding) and router.table.owner("fx.acid.mix") is b
    assert [m.inputs for m in router.table.modifiers] == [
        ("hand:right.energy",), (smooth.address, "lane:0")]
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
