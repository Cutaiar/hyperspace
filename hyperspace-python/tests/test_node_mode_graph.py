"""Plan 53 N1b: node mode drawn. A row that acts is a cable, of its own kind and colour,
in its own bundle, on the deck whose patch says so, faint when its player is elsewhere.
"""

from __future__ import annotations

import pytest
from test_node_desk import K1, K2, pick_node
from test_node_desk import rig as desk_rig  # noqa: F401 — the fixture, under its name

from hyperspace import graphview, node_desk, routing, ui_desk, ui_graph
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
    assert [c.dst_port for c in cables(view)] == [f"{graphview.BASE}:{free}"]


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


def test_a_node_mode_cable_cannot_be_deleted_only_left(rig):
    assert NM not in ui_graph.DELETE
    assert NM not in graphview.CABLE_KINDS      # nothing drops a node onto one, either


def test_the_desks_colour_is_the_cables():
    k = ui_graph.KIND_COLOURS[NM]
    assert ui_desk.NODE_INK == pytest.approx((k.x, k.y, k.z, k.w), abs=1e-5)


def test_the_words_are_the_map_then_the_kept_then_the_over(rig, monkeypatch):
    node, params = pick_node(rig.one, 4)
    t = rig.one.table
    t.bind(Binding("cc:*:20", params[0], "abs", layer="preset"), write=False)
    monkeypatch.setattr(node_desk.apc40, "degrees_of_freedom",
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
