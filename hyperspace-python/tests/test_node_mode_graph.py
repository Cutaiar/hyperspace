"""Plan 53 N1b: node mode drawn. A row that acts is a cable, of its own kind and colour,
in its own bundle, on the deck whose patch says so, faint when its player is elsewhere.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from imgui_bundle import imgui
from test_graph_json import Stub
from test_midi import FakeIn, FakeOut
from test_node_desk import K1, K2, pick_node
from test_node_desk import rig as desk_rig  # noqa: F401 — the fixture, under its name
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import (
    apc40,
    devices,
    graphview,
    nodemode,
    routing,
    ui,
    ui_desk,
    ui_graph,
    ui_routing,
)
from hyperspace.midi import MidiIO
from hyperspace.routing import Binding

NM = graphview.NODE_MODE


@pytest.fixture()
def rig(desk_rig):  # noqa: F811
    return desk_rig


def view_of(deck, devs):
    return graphview.build(deck.table, deck.reg, deck.router, devs)


def cables(view):
    return [c for c in view.cables if c.kind == NM]


def test_a_cable_for_every_row_that_acts_and_none_when_nothing_points(rig):
    assert not cables(view_of(rig.one, rig.devs))
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    view = view_of(rig.one, rig.devs)
    got = cables(view)
    rows = rig.nd1.rows()
    assert len(got) == len(rows) > 0
    assert {c.dst_port for c in got} == {f"{graphview.BASE}:{b.target}" for b in rows}
    assert all(c.src_port in view.pins and c.dst_port in view.pins for c in got)
    first = next(c for c in got if c.ref[1] is rows[0])
    assert "node mode: player 1, K1 →" in first.label
    assert view.owner(first.src_port)[0].id == f"device:{rig.desk.role}"
    assert not first.dormant


def test_a_param_with_no_port_of_its_own_gets_one(rig):
    """A continuous param no route can move has no port until something reaches it."""
    node, _ = pick_node(rig.one)
    free = next(p.id for p in rig.one.reg if not p.modulatable and not p.alias
                and p.kind.name == "CONTINUOUS" and routing.meta_refusal(p.id) is None)
    assert f"{graphview.BASE}:{free}" not in view_of(rig.one, rig.devs).pins
    rig.one.loaded_patch.node_params = lambda _n: [free]
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    view = view_of(rig.one, rig.devs)
    assert f"{graphview.BASE}:{free}" in view.pins
    assert [view.owner(c.dst_port)[0].id for c in cables(view)] == [node]


def test_the_key_moves_when_the_pointing_and_the_deck_do(rig):
    def key():
        return graphview.key(rig.one.table, rig.one.reg, rig.one.router, rig.devs, None, None)
    was = key()
    assert key() == was
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    pointed = key()
    assert pointed != was
    rig.meta.point(rig.desk.role, rig.two)
    assert key() != pointed


def test_a_cable_on_the_other_deck_is_faint_and_says_so(rig):
    node, _ = pick_node(rig.two)
    rig.two.loaded_patch.point_node_mode(1, "midi", node)
    view = view_of(rig.two, rig.devs)
    got = cables(view)
    assert got and all(c.dormant and c.off and "on the other Deck" in c.label for c in got)
    graphview.refresh(view, rig.two.reg, rig.two.router, None)
    assert all(c.dormant for c in cables(view))
    rig.nd2.enter(rig.desk.role, node)
    awake = view_of(rig.two, rig.devs)
    graphview.refresh(awake, rig.two.reg, rig.two.router, None)
    assert cables(awake) and not any(c.off or "other Deck" in c.label for c in cables(awake))


def test_a_cable_reads_its_param_and_stays_lit_with_no_lane(rig):
    node, _ = pick_node(rig.one)
    rig.nd1.enter(rig.desk.role, node)
    view = view_of(rig.one, rig.devs)
    c = cables(view)[0]
    p = rig.one.reg[c.ref[1].target]
    p.set_norm(0.5)
    graphview.refresh(view, rig.one.reg, rig.one.router, None)
    assert c.live == pytest.approx(p.eff_norm)
    assert not c.dormant


def test_a_saved_row_under_a_filled_control_is_drawn_faint_and_says_so(rig):
    node, params = pick_node(rig.one)
    rig.one.loaded_patch.node_params = lambda _n: params[:1]
    t = rig.one.table
    k1 = next(b for b in t.desk() if b.source == f"cc:0:{K1}")
    k2 = next(b for b in t.desk() if b.source == f"cc:0:{K2}")
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    view = view_of(rig.one, rig.devs)
    under = next(c for c in view.cables if c.kind == "setter" and c.ref is k1)
    free = next(c for c in view.cables if c.kind == "setter" and c.ref is k2)
    assert under.off and graphview.UNDER_NODE_MODE.strip() in under.label
    assert not free.off and graphview.UNDER_NODE_MODE.strip() not in free.label


def test_node_mode_never_bundles_with_saved_rows(rig):
    """The brief's line: a mixed bundle on a collapsed node reads white."""
    node, params = pick_node(rig.one)
    t = rig.one.table
    t.bind(Binding("cc:*:20", params[0], "abs", layer="preset"), write=False)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    view = view_of(rig.one, rig.devs)
    _, bundles = graphview.wiring(view, lambda _nid: True)
    mine = [b for b in bundles if any(c.kind == NM for c in b.cables)]
    assert mine and all(all(c.kind == NM for c in b.cables) for b in mine)
    assert all(b.id.endswith("|node") for b in mine)
    saved = [b for b in bundles if b.src == mine[0].src and b.dst == mine[0].dst
             and not b.id.endswith("|node")]
    assert saved and not any(c.kind == NM for b in saved for c in b.cables)
    assert len({b.id for b in bundles}) == len(bundles)
    assert ui_graph._bundle_colour(mine[0]) is ui_graph.KIND_COLOURS[NM]
    assert ui_graph._bundle_colour(saved[0]) is not ui_graph.KIND_COLOURS[NM]


def test_an_expanded_end_draws_each_cable_and_a_folded_view_keeps_them_apart(rig):
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    view = view_of(rig.one, rig.devs)
    singles, bundles = graphview.wiring(view, lambda _nid: False)
    assert not [b for b in bundles if b.id.endswith("|node")]
    assert sum(1 for c, _a, _b in singles if c.kind == NM) == len(rig.nd1.rows())


def test_a_node_mode_cable_with_no_row_is_passed_over_by_a_group(rig):
    """`node_mode_cable`'s `ref` defaults to None, as `refresh` and the menus allow."""
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    view = view_of(rig.one, rig.devs)
    bare = cables(view)[0]
    bare.ref = None
    graphview.attach_groups(view, [{"id": "g1", "name": "g", "nodes": [node], "open": False}],
                            rig.one.table)
    assert bare.id not in view.groups[0].ends


def test_a_route_at_rest_says_so_and_comes_back(rig):
    """The owner, row 711: the cable's words, and it is faint while it rests."""
    node, params = pick_node(rig.one)
    route = Binding("lane:0", params[0], "push", 0.5)
    rig.one.table.set_routes([*rig.one.table.routes(), route])

    def cable():
        view = view_of(rig.one, rig.devs)
        return next(c for c in view.cables if c.kind == "route" and c.ref is route)
    assert graphview.NODE_MODE_HOLDS not in cable().label
    was = graphview.key(rig.one.table, rig.one.reg, rig.one.router, rig.devs, None, None)
    rig.nd1.enter(rig.desk.role, node)
    assert graphview.key(rig.one.table, rig.one.reg, rig.one.router, rig.devs, None, None) != was
    c = cable()
    assert c.off and graphview.NODE_MODE_HOLDS in c.label
    h = next(x for x in rig.nd1.held() if x.role == rig.desk.role)
    assert ui_graph.RESTING.format(n=1, s="") in ui_graph.node_mode_words(rig.nd1, h, node)
    rig.nd1.leave(rig.desk.role)
    c = cable()
    assert not c.off and graphview.NODE_MODE_HOLDS not in c.label


def test_nothing_drops_a_node_onto_a_node_mode_cable():
    assert NM not in graphview.CABLE_KINDS


def test_a_bundle_says_leave_not_expand(rig, monkeypatch):
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    _, bundles = graphview.wiring(view_of(rig.one, rig.devs), lambda _nid: True)
    mine = next(b for b in bundles if b.id.endswith("|node"))
    assert ui_graph._node_mode_roles(mine) == [rig.desk.role]
    monkeypatch.setattr(ui_graph.ed, "reject_deleted_item", lambda: None)
    st = {}
    assert ui_graph.delete_bundle(st, mine) == graphview.LEAVE_WORDS == st["note"]
    other = next(b for b in bundles if not b.id.endswith("|node"))
    assert ui_graph.delete_bundle({}, other) == graphview.EXPAND_TO_EDIT


def test_a_node_of_a_copy_gets_its_cables_on_the_copy(rig):
    """The pane says the copy's name, and its params' ports live on the original."""
    node, params = pick_node(rig.one)
    view0 = view_of(rig.one, rig.devs)
    other = next(n.id for n in view0.nodes if n.id.startswith("render:") and n.id != node
                 and view0.pins.get(f"{graphview.BASE}:{params[0]}", ("",))[0] != n.id)
    rig.one.loaded_patch.pointable = lambda _n: True
    rig.one.loaded_patch._pointable = lambda *_a: {other, node}
    rig.one.loaded_patch.node_params = lambda n: params[:2] if n == other else params
    assert rig.one.loaded_patch.point_node_mode(1, "midi", other) is None
    view = view_of(rig.one, rig.devs)
    got = cables(view)
    assert got and all(view.owner(c.dst_port)[0].id == other for c in got)
    assert got[0].dst_port == f"{graphview.NODE_PIN}:{other}|{params[0]}"
    port = view.owner(got[0].dst_port)[1]
    assert port.param == params[0] and port.patched
    graphview.refresh(view, rig.one.reg, rig.one.router, None)
    # …which takes no drag: nothing can wire a row onto a pin only node mode lands on
    before = list(rig.one.table.bindings)
    edit = graphview.Edit(rig.one.table, rig.one.reg, rig.one.router, view)
    got_said = edit.connect(got[0].src_port, got[0].dst_port)
    assert isinstance(got_said, graphview.Refusal)
    assert list(rig.one.table.bindings) == before


def test_the_desks_colour_is_the_cables_and_faint_when_the_desk_is_elsewhere(rig):
    k = ui_graph.KIND_COLOURS[NM]
    here, away = ui_desk._node_ink(False), ui_desk._node_ink(True)
    assert (here.x, here.y, here.z, here.w) == (k.x, k.y, k.z, k.w)
    assert away.w == pytest.approx(ui_desk.NODE_FAINT)
    node, _ = pick_node(rig.one)
    rig.nd1.enter(rig.desk.role, node)
    row = rig.nd1.rows()[0]
    assert rig.one.table.node_row_away(row) is False
    rig.meta.point(rig.desk.role, rig.two)
    assert rig.one.table.node_row_away(row) is True
    saved = next(b for b in rig.one.table.desk())
    assert rig.one.table.node_row_away(saved) is None


def test_the_panel_asks_once_a_selection_not_once_a_frame(rig, monkeypatch):
    """`refusal` and `pointable` are each frame's while a node is selected; the scan is not."""
    node, _ = pick_node(rig.one)
    scans = []
    real = graphview.param_ids
    monkeypatch.setattr(graphview, "param_ids", lambda *a, **k: (scans.append(1), real(*a, **k))[1])
    for _ in range(5):
        assert rig.nd1.refusal(rig.desk.role, node) is None
        assert rig.nd1.pointable(node)
    assert len(scans) == 1
    rig.nd1.deck.reg.serial += 1                    # a param added: asked again
    rig.nd1.refusal(rig.desk.role, node)
    assert len(scans) == 2


def test_a_folded_group_gives_each_node_mode_cable_its_boundary_pin(rig):
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    view = view_of(rig.one, rig.devs)
    entries = [{"id": "g1", "name": "g", "nodes": [node], "open": False}]
    graphview.attach_groups(view, entries, rig.one.table)
    g = view.groups[0]
    mine = [c for c in cables(view) if c.id in g.ends]
    assert mine and all(g.ends[c.id][1] for c in mine)
    _, bundles = graphview.wiring(view, lambda _nid: True, folded=graphview.folded(view))
    assert any(b.dst == g.id and b.id.endswith("|node") and b.in_pin for b in bundles)


def test_the_words_are_the_map_then_the_kept_then_the_over(rig, monkeypatch):
    node, params = pick_node(rig.one, 4)
    t = rig.one.table
    t.bind(Binding("cc:*:20", params[0], "abs", layer="preset"), write=False)
    monkeypatch.setattr(apc40, "degrees_of_freedom",
                        lambda: [(f"cc:0:{K1}",), ("cc:*:20",), (f"cc:0:{K2}",)])
    rig.nd1.enter(rig.desk.role, node)
    h = next(x for x in rig.nd1.held() if x.role == rig.desk.role)
    words = ui_graph.node_mode_words(rig.nd1, h, node)
    assert words[0].startswith("K1 → ") and words[1].startswith("K2 → ")
    assert words[2] == f"mapped already: {params[0]}"
    assert words[3].startswith(f"{node.removeprefix('render:')} has too many params")
    assert ui_graph.node_mode_words(rig.nd1, h, "render:other") == []
    rig.meta.point(rig.desk.role, rig.two)
    h = next(x for x in rig.nd1.held() if x.role == rig.desk.role)
    assert ui_graph.node_mode_words(rig.nd1, h, node)[-1] == ui_graph.ASLEEP.format(
        role=rig.desk.role)


def test_the_on_screen_desk_shows_the_row_and_rebuilds_on_a_change(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    before = ui_desk._key(t)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert ui_desk._key(t) != before
    b = ui_desk.lit(t)["K1"]
    assert b is rig.nd1.rows()[0] and b.target == params[0]
    assert ui_desk.text(rig.one.reg, b) == b.words == rig.one.reg[params[0]].label
    assert ui_desk.mappable(t, next(c for c in ui_desk.apc40.LAYOUT if c.glyph == "K1")) is None


# ---------------------------------------------------------------- the chips, in a real frame


@pytest.fixture()
def panel_rig(shell_rig):  # noqa: F811
    return shell_rig


def _block(panel, nd, monkeypatch, chips, press=None):
    """`node_mode_block` drawn on a stand-in desk; `press`: the chip label to press."""
    monkeypatch.setattr(ui_graph, "_node_desk", lambda _p: nd)

    def chip(label, size=None):
        chips.append(label.split("##")[0])
        return press is not None and label.startswith(press)
    monkeypatch.setattr(ui, "chip", chip)
    monkeypatch.setattr(ui, "lit_chip", lambda label, lit, color=None, size=None: chip(label))
    imgui.new_frame()
    imgui.begin("t")
    ui_graph.node_mode_block(panel, SimpleNamespace(id="render:acid"))
    imgui.end()
    imgui.end_frame()


def _nd(**kw):
    h = SimpleNamespace(role="apc40", player=1, node="render:acid", on_here=False,
                        fit=nodemode.Fit(), rows=())
    h.__dict__.update(kw)
    entered = []
    return SimpleNamespace(pointable=lambda _n: True, held=lambda: [h], refusal=lambda *_a: None,
                           enter=lambda *a: entered.append(a), leave=lambda _r: None,
                           control_word=lambda *_a: "K1", entered=entered)


def test_a_bring_that_is_refused_says_so_and_a_grey_chip_does_nothing(panel_rig, monkeypatch):
    p = panel_rig.panel
    said = []
    monkeypatch.setattr(p.library, "say", lambda **k: said.append(k["warning"]))
    nd = _nd()
    nd.enter = lambda *_a: "no such node"
    _block(p, nd, monkeypatch, [], press="bring")
    assert said == ["no such node"]
    nd = _nd()
    nd.refusal = lambda *_a: "because"
    _block(p, nd, monkeypatch, [], press="bring")
    assert nd.entered == []


def test_what_did_not_fit_is_listed_whole_at_any_width(panel_rig, monkeypatch):
    p = panel_rig.panel
    over = tuple(f"fx.long.param.number.{k}" for k in range(12))
    nd = _nd(fit=nodemode.Fit(over=over), on_here=True)
    lines = []
    monkeypatch.setattr(imgui, "text_wrapped", lambda s: lines.append(s))
    _block(p, nd, monkeypatch, [])
    assert any(all(x in line for x in over) for line in lines)


def test_the_chip_says_point_move_bring_and_leave(panel_rig, monkeypatch):
    p = panel_rig.panel
    for h, want in (({"node": None, "on_here": True}, ["point apc40 here"]),
                    ({"node": "render:b", "on_here": True}, ["move apc40 here"]),
                    ({"on_here": True}, ["apc40 on this node · leave"]),
                    ({"on_here": False}, ["apc40 on this node · leave", "bring apc40 here"])):
        chips = []
        _block(p, _nd(**h), monkeypatch, chips)
        assert chips == want


# ---------------------------------------------------------------- review at e17cb81c


def _header_words(panel, table, monkeypatch) -> tuple[list[str], list[str]]:
    """`ui_desk._header` drawn, wide: what it says, and what it says in the micro face."""
    said, micro = [], []
    real, real_micro = imgui.text_colored, ui._micro
    monkeypatch.setattr(imgui, "text_colored", lambda c, s: (said.append(s), real(c, s))[1])
    monkeypatch.setattr(ui, "_micro", lambda s, *a: (micro.append(s), real_micro(s, *a))[1])
    imgui.new_frame()
    imgui.set_next_window_size(imgui.ImVec2(1600, 80))
    imgui.begin("probe")
    try:
        ui_desk._header(panel, table)
    finally:
        imgui.end()
        imgui.end_frame()
    return said, micro


@pytest.mark.parametrize("node_away", [False, True])
def test_the_head_keeps_the_decks_clause_with_node_mode_up(panel_rig, monkeypatch, node_away):
    """The node mode block is no reason for "deck 1 · True", or to lose what the desk plays."""
    panel = panel_rig.panel
    table = ui_routing.router_of(panel).table
    row = Binding(f"cc:0:{K1}", "view.bright", "abs", layer="preset")
    monkeypatch.setattr(table, "node_rows", lambda role=None: [row])
    monkeypatch.setattr(table, "node_row_away", lambda b: node_away)
    monkeypatch.setattr(ui_desk, "_deck_words",
                        lambda p, t: ("deck 1 · on air", "the desk plays deck 2", True))
    said, micro = _header_words(panel, table, monkeypatch)
    assert "deck 1 · on air · the desk plays deck 2" in said
    assert not any("True" in s or "False" in s for s in said)
    assert ("node · 1 · other deck" if node_away else "node · 1") in micro


def _second_desk(rig, node) -> None:
    """A second desk, player 2's, pointed at `node` of deck 1."""
    t = rig.one.table
    io2 = MidiIO(rig.one.reg, t, inp=FakeIn(), out=FakeOut(), learner=rig.one.learn, role="launch")
    second = devices.MidiDevice("launch", {"profile": "apc40"},
                                devices.Context(reg=rig.one.reg, table=t), io=io2)
    rig.devs.devices.append(second)
    t.midi_roles = (rig.desk.role, "launch")
    rig.meta.players.hold("launch", 2)
    second.point(rig.meta.pointer("launch"), rig.meta.panel_pointer)
    assert rig.nd1.enter("launch", node) is None


def test_the_pane_counts_this_desks_routes_that_come_back(rig):
    node, params = pick_node(rig.one)
    patch = rig.one.loaded_patch
    other = next(n for n in sorted(patch._pointable())
                 if n != node and rig.nd1.refusal(rig.desk.role, n) is None
                 and not set(patch.node_params(n)) & set(params)
                 and not any(b.target in patch.node_params(n) for b in rig.one.table.bindings))
    theirs = nodemode.fillable(rig.one.reg, patch.node_params(other))[0]
    off = Binding("lane:1", params[1], "push", 0.5)
    off.enabled = False
    rig.one.table.set_routes([*rig.one.table.routes(), Binding("lane:0", params[0], "push", 0.5),
                              off, Binding("lane:0", theirs, "push", 0.5)])
    _second_desk(rig, other)
    rig.nd1.enter(rig.desk.role, node)
    assert theirs in rig.one.table.node_held()      # held, by the other desk, on the other node
    h = next(x for x in rig.nd1.held() if x.role == rig.desk.role)
    assert ui_graph.RESTING.format(n=1, s="") in ui_graph.node_mode_words(rig.nd1, h, node)


def _route_cable(rig, route):
    view = view_of(rig.one, rig.devs)
    return next(c for c in view.cables if c.kind == "route" and c.ref is route)


def test_a_switched_off_route_is_promised_nothing(rig):
    node, params = pick_node(rig.one)
    route = Binding("lane:0", params[0], "push", 0.5)
    route.enabled = False
    rig.one.table.set_routes([*rig.one.table.routes(), route])
    rig.nd1.enter(rig.desk.role, node)
    assert rig.one.table.node_holds(route)
    c = _route_cable(rig, route)
    assert c.off and graphview.NODE_MODE_HOLDS not in c.label


def test_a_route_a_loop_will_cut_is_promised_nothing(rig):
    """A loop closed by the route node mode holds is open while it is held, so the live cut
    does not name it. It says what it will be, read with no desk holding, and refresh agrees."""
    route = Binding("lfo:0", "lfo.1.rate", "push", 0.5)     # the voice's output onto its own knob
    router, t = rig.one.router, rig.one.table
    t.set_routes([*t.routes(), route])
    key = (route.source, route.target)
    assert key in router.modgraph_cut and key in router.modgraph_stays_cut
    assert rig.nd1.enter(rig.desk.role, "lfo.1") is None
    assert t.node_holds(route)
    assert key not in router.modgraph_cut and key in router.modgraph_stays_cut
    view = view_of(rig.one, rig.devs)
    c = next(x for x in view.cables if x.kind == "route" and x.ref is route)
    for _ in range(2):
        assert c.off and graphview.NODE_MODE_HOLDS not in c.label
        assert "a loop needs a delay" in c.label
        graphview.refresh(view, rig.one.reg, router, None)
    h = next(x for x in rig.nd1.held() if x.role == rig.desk.role)
    assert not any("at rest" in w for w in ui_graph.node_mode_words(rig.nd1, h, "lfo.1"))
    rig.nd1.leave(rig.desk.role)
    assert key in router.modgraph_cut                       # …as it said
    assert key in router.modgraph_stays_cut


def test_with_nothing_held_what_stays_cut_is_what_is_cut(rig):
    t, router = rig.one.table, rig.one.router
    t.set_routes([*t.routes(), Binding("lfo:0", "lfo.1.rate", "push", 0.5)])
    assert router.modgraph_stays_cut == router.modgraph_cut != set()


def test_a_frame_reads_who_holds_what_the_same_however_many_routes(rig, monkeypatch):
    """`refresh` is each frame's: `holding` scans the desks, so it is asked once, not per route."""
    node, params = pick_node(rig.one)
    t = rig.one.table
    rig.nd1.enter(rig.desk.role, node)
    calls = []
    real = rig.nd1.holding
    monkeypatch.setattr(rig.nd1, "holding", lambda: (calls.append(1), real())[1])

    def asked() -> int:
        view = view_of(rig.one, rig.devs)
        calls.clear()
        graphview.refresh(view, rig.one.reg, rig.one.router, None)
        return len(calls)
    few = asked()
    t.set_routes([*t.routes(), *(Binding(f"lane:{k}", params[0], "push", 0.1) for k in range(1, 20))])
    assert asked() == few
    h = next(x for x in rig.nd1.held() if x.role == rig.desk.role)
    calls.clear()
    ui_graph.node_mode_words(rig.nd1, h, node)
    assert len(calls) <= 2      # `routes_held`'s, and the router's own `_modgraph_key`


def test_the_desk_asks_once_a_draw_not_once_a_control(panel_rig, monkeypatch):
    panel = panel_rig.panel
    table = ui_routing.router_of(panel).table
    row = next(iter(ui_desk.lit(table).values()))
    asked = []
    monkeypatch.setattr(table, "node_rows", lambda role=None: (asked.append("rows"), [row])[1])
    monkeypatch.setattr(table, "node_row_away", lambda b: (asked.append("away"), True)[1])
    edges = []
    real = ui_desk._edge
    monkeypatch.setattr(ui_desk, "_edge", lambda f, b, on: (edges.append((b, f.get(id(b)))),
                                                            real(f, b, on))[1])
    imgui.new_frame()
    imgui.set_next_window_size(imgui.ImVec2(1200, 800))
    imgui.begin("probe")
    try:
        ui_desk._body(panel, table)
    finally:
        imgui.end()
        imgui.end_frame()
    assert len(edges) == len(apc40.LAYOUT)
    assert [away for b, away in edges if b is row] and all(
        away is True for b, away in edges if b is row)
    assert all(away is None for b, away in edges if b is not row)
    # the head's and the draw's, and the map's as it is first made (`lit_cached`)
    assert asked.count("away") <= 2 and asked.count("rows") <= 3


# …a real copy, made as the picker makes one


def _real_copy(rig) -> tuple[str, str, object]:
    """An effect and a copy of it in deck 1's section, by the picker's own verb."""
    gs = rig.one.loaded_patch.graph
    gs.attach(Stub())
    e = graphview.Edit(graph=gs, push=lambda _label: None)
    assert e.add_node("effect", "acid") is None
    original = f"render:{e.added}"
    assert e.add_node("copy", e.added) is None
    return original, f"render:{e.added}", gs.spec


def _grouped(rig, spec, members: list[str]):
    view = graphview.build(rig.one.table, rig.one.reg, rig.one.router, rig.devs, None, spec)
    graphview.attach_groups(view, [{"id": "g1", "name": "g", "nodes": members, "open": False}],
                            rig.one.table)
    return view, view.groups[0]


def test_a_real_copys_cables_land_on_the_copy(rig):
    original, copy, spec = _real_copy(rig)
    assert rig.nd1.enter(rig.desk.role, copy) is None
    rows = rig.nd1.rows()
    assert rows and all(b.target.startswith("fx.acid") for b in rows)
    view = graphview.build(rig.one.table, rig.one.reg, rig.one.router, rig.devs, None, spec)
    got = cables(view)
    assert len(got) == len(rows) and {view.owner(c.dst_port)[0].id for c in got} == {copy}
    assert all(c.dst_port.startswith(f"{graphview.NODE_PIN}:{copy}|") for c in got)
    assert original != copy


def test_a_group_holding_only_the_copy_gives_its_cables_a_pin(rig):
    """The params are the original's, whom the group does not hold: where it lands decides."""
    _original, copy, spec = _real_copy(rig)
    rig.nd1.enter(rig.desk.role, copy)
    view, g = _grouped(rig, spec, [copy])
    got = cables(view)
    assert got and all(c.id in g.ends and g.ends[c.id][1] for c in got)
    pin = g.ends[got[0].id][1]
    # the pin stands for where the cable lands, which takes no drag, not the original's param
    assert graphview.real_pin(view, pin) == got[0].dst_port
    assert view.owner(graphview.real_pin(view, pin))[0].id == copy


def test_a_group_holding_only_the_original_leaves_the_copys_cables_alone(rig):
    """No dangling port: nothing of this group is on the end of them."""
    original, copy, spec = _real_copy(rig)
    rig.nd1.enter(rig.desk.role, copy)
    view, g = _grouped(rig, spec, [original])
    got = cables(view)
    assert got and not any(c.id in g.ends or c.id in g.inside for c in got)
    assert not any(p.param in {c.ref[1].target for c in got} for p in g.ports)


def test_a_group_holding_both_keeps_the_two_desks_pins_apart(rig):
    """Two desks, one on the original and one on its copy: one param, two ends."""
    original, copy, spec = _real_copy(rig)
    rig.nd1.enter(rig.desk.role, original)
    _second_desk(rig, copy)
    view, g = _grouped(rig, spec, [original, copy])
    got = cables(view)
    to_copy = [c for c in got if c.dst_port.startswith(f"{graphview.NODE_PIN}:")]
    to_original = [c for c in got if c not in to_copy]
    assert to_copy and to_original
    assert {g.ends[c.id][1] for c in to_copy}.isdisjoint(g.ends[c.id][1] for c in to_original)


# …the side pane's words


def _pane(panel, view, sel, monkeypatch, nd, press=None) -> list[str]:
    """`ui_graph._side` drawn in a real frame: everything it says, as it is shown."""
    said = []
    with monkeypatch.context() as m:
        m.setattr(ui_graph, "_node_desk", lambda _p: nd)
        real_micro, real_wrapped, real_dis = ui._micro, imgui.text_wrapped, imgui.text_disabled
        m.setattr(ui, "_micro", lambda s, *a: (said.append(s.upper()), real_micro(s, *a))[1])
        m.setattr(imgui, "text_wrapped", lambda s: (said.append(s), real_wrapped(s))[1])
        m.setattr(imgui, "text_disabled", lambda s: (said.append(s), real_dis(s))[1])

        def chip(label, lit, color=None, size=None):
            said.append(label.split("##")[0])
            return press is not None and label.startswith(press)
        m.setattr(ui, "lit_chip", chip)
        ui_graph._state(panel)["view"] = view
        imgui.new_frame()
        imgui.begin("t")
        try:
            ui_graph._side(panel, {}, view, sel)
        finally:
            imgui.end()
            imgui.end_frame()
    return said


def test_a_selected_bundle_says_leave_and_offers_it(rig, panel_rig, monkeypatch):
    node, _ = pick_node(rig.one)
    rig.nd1.enter(rig.desk.role, node)
    view = view_of(rig.one, rig.devs)
    _, bundles = graphview.wiring(view, lambda _nid: True)
    mine = next(b for b in bundles if b.id.endswith("|node"))
    said = _pane(panel_rig.panel, view, ("bundle", mine), monkeypatch, rig.nd1)
    assert graphview.LEAVE_WORDS in said
    assert not any(graphview.EXPAND_TO_EDIT in s for s in said)
    assert f"{rig.desk.role}: leave node mode" in said
    assert rig.nd1.rows()
    _pane(panel_rig.panel, view, ("bundle", mine), monkeypatch, rig.nd1,
          press=f"{rig.desk.role}: leave")
    assert not rig.nd1.rows()


def test_a_saved_bundle_in_the_pane_still_says_expand(rig, panel_rig, monkeypatch):
    view = view_of(rig.one, rig.devs)
    _, bundles = graphview.wiring(view, lambda _nid: True)
    other = next(b for b in bundles if not ui_graph._node_mode_roles(b))
    said = _pane(panel_rig.panel, view, ("bundle", other), monkeypatch, rig.nd1)
    assert any(graphview.EXPAND_TO_EDIT in s for s in said)
    assert graphview.LEAVE_WORDS not in said


def test_a_selected_cable_says_node_mode_in_words_and_offers_leave(rig, panel_rig, monkeypatch):
    node, _ = pick_node(rig.one)
    rig.nd1.enter(rig.desk.role, node)
    view = view_of(rig.one, rig.devs)
    c = cables(view)[0]
    said = _pane(panel_rig.panel, view, ("cable", c), monkeypatch, rig.nd1)
    assert "NODE MODE" in said and "NODE_MODE" not in said
    assert graphview.LEAVE_WORDS in said
    assert f"{rig.desk.role}: leave node mode" in said
    _pane(panel_rig.panel, view, ("cable", c), monkeypatch, rig.nd1,
          press=f"{rig.desk.role}: leave")
    assert not rig.nd1.rows()
