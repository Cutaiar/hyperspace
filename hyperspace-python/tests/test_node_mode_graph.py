"""Plan 53 N1b: node mode drawn. A row that acts is a cable, of its own kind and colour,
in its own bundle, on the deck whose patch says so, faint when its player is elsewhere.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from imgui_bundle import imgui
from test_node_desk import K1, K2, pick_node
from test_node_desk import rig as desk_rig  # noqa: F401 — the fixture, under its name
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import apc40, graphview, nodemode, routing, ui, ui_desk, ui_graph
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
