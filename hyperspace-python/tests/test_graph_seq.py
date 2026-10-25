"""Plan 31 G1, the GRAPH page for the envelopes and the sequencer, headless.

The rig is test_plan31_wiring's: a real Registry and Router with the
clock, four LFOs, the envelope bank and the sequencer, as app.main wires
them. The view is `graphview.build`'s; the page's add / delete are
`ui_graph`'s plain functions over a bare panel, with a real `undo.Undo`
carrying the banks' membership."""

from types import SimpleNamespace

import pytest
from test_plan31_wiring import frame, rig

from hyperspace import graphview, ui_graph, undo
from hyperspace.routing import Binding


def build(r):
    return graphview.build(r.router.table, r.reg, r.router)


def collapsed_wiring(view):
    return graphview.wiring(view, lambda nid: True, shown=lambda nid: not view.node(nid).idle)


# ---- the kinds and their area ----

def test_env_and_seq_are_node_kinds_in_the_modulation_area():
    assert {"env", "seq"} <= set(graphview.KINDS)
    assert {"env", "seq"} <= set(graphview.NO_DEVICE)
    assert {"env", "seq"} <= set(graphview.IDLE_KINDS)
    assert "lane" in graphview.CABLE_KINDS
    view = build(rig())
    envs = [n for n in view.nodes if n.kind == "env"]
    assert [n.id for n in envs] == [f"env.{k}" for k in range(1, 6)]
    seq = view.node(graphview.SEQ)
    assert seq is not None and seq.kind == "seq" and seq.label == "sequencer"
    for n in (*envs, seq):
        assert n.area == graphview.MODULATION
        assert graphview.home(n) == graphview.PRESET     # the preset's layout
    # every envelope param on its envelope's node, the grid's on the sequencer
    assert view.owner("mod:env.3.decay")[0].id == "env.3"
    assert view.owner("base:env.3.fire")[0].id == "env.3"
    assert view.owner("mod:seq.2.5")[0].id == graphview.SEQ
    assert view.node("group:env") is None and view.node("group:seq") is None
    # the five trigger outputs, lane 1–5
    outs = [p for p in seq.ports if p.direction == graphview.OUT]
    assert [p.id for p in outs] == [f"out:seq:{i}" for i in range(5)]
    assert [p.name for p in outs] == [f"lane {i}" for i in range(1, 6)]
    assert {p.type for p in outs} == {graphview.TRIGGER}


def test_defaults_draw_no_placeholder_and_keep_the_new_nodes_idle():
    """With the defaults (envelopes unrouted, the grid empty, stopped) the
    envelopes and the sequencer sit idle, off the canvas, and nothing
    grey stands in for them."""
    view = build(rig())
    assert all(n.idle for n in view.nodes if n.kind in ("env", "seq"))
    assert not [n for n in view.nodes if n.placeholder or n.kind == "source"]
    assert not [c for c in view.cables if c.kind == "lane"]
    idle = [n for n in view.nodes if n.idle and n.area == graphview.MODULATION]
    words = graphview.idle_words(idle)
    assert "5 idle envelopes" in words and "1 idle sequencer" in words


# ---- a routed envelope ----

def test_a_routed_envelope_is_drawn_with_one_bundle_to_its_target():
    r = rig([Binding("env:1", "t.x", "position", 1.0),
             Binding("env:1", "t.hit", "fire", 1.0, enabled=False)])
    view = build(r)
    n = view.node("env.2")
    assert not n.idle and n.wires == 2
    assert view.node("env.1").idle                    # unrouted, still idle
    routes = [c for c in view.cables if c.kind == "route"]
    assert {c.src_port for c in routes} == {"out:env:1"}
    assert not [x for x in view.nodes if x.id.startswith(("device:", "source:"))]
    _, bundles = collapsed_wiring(view)
    mine = [b for b in bundles if b.src == "env.2"]
    assert len(mine) == 1 and mine[0].count == 2      # one wire per node pair
    assert graphview.summary(n)[0].startswith("out ")


def test_a_route_from_a_sequencer_lane_leaves_the_sequencer_node():
    view = build(rig([Binding("seq:2", "t.hit", "fire", 1.0)]))
    c = next(c for c in view.cables if c.addr == "seq:2" and c.kind != "lane")
    assert c.src_port == "out:seq:2" and view.owner(c.src_port)[0].id == graphview.SEQ
    assert c.type == graphview.TRIGGER
    assert not view.node(graphview.SEQ).idle
    assert not [n for n in view.nodes if n.placeholder or n.kind == "source"]


# ---- the sequencer's bindings ----

def test_a_lane_with_a_step_on_is_a_binding_cable_to_its_envelope():
    r = rig()
    k0 = graphview.key(r.router.table, r.reg, r.router, None, None, None)
    r.reg["seq.1.3"].set(True)
    k1 = graphview.key(r.router.table, r.reg, r.router, None, None, None)
    assert k1 != k0                                   # the page rebuilds
    view = build(r)
    lanes = [c for c in view.cables if c.kind == "lane"]
    assert len(lanes) == 1
    c = lanes[0]
    assert (c.src_port, c.dst_port, c.ref) == ("out:seq:0", "base:env.1.fire", (0, 1))
    assert c.off and c.dormant and "stopped" in c.label   # stopped: drawn, dormant
    assert not view.node("env.1").idle and not view.node(graphview.SEQ).idle
    assert view.node("env.2").idle
    _, bundles = collapsed_wiring(view)
    b = next(b for b in bundles if (b.src, b.dst) == (graphview.SEQ, "env.1"))
    assert b.type == graphview.TRIGGER and b.count == 1
    # running: every bound lane counts, and lane 1's cable is live
    r.reg["seq.run"].set(True)
    frame(r, 0.5)                                     # the sequencer publishes its lanes
    view = build(r)
    lanes = {c.ref: c for c in view.cables if c.kind == "lane"}
    assert set(lanes) == {(i, i + 1) for i in range(5)}
    assert not lanes[(0, 1)].off and not lanes[(0, 1)].dormant
    # a muted lane's binding is dormant
    r.reg["seq.2.mute"].set(True)
    view = build(r)
    c = next(c for c in view.cables if c.kind == "lane" and c.ref == (1, 2))
    assert c.off and "muted" in c.label


def test_a_lane_rebinds_by_a_drag_onto_an_envelopes_fire_and_cannot_be_deleted():
    r = rig()
    r.reg["seq.1.1"].set(True)
    view = build(r)
    e = graphview.Edit(r.router.table, r.reg, r.router, view)
    assert e.refusal("out:seq:0", "base:env.3.fire") is None
    assert e.connect("base:env.3.fire", "out:seq:0") == (0, 3)     # either end
    assert r.reg["seq.1.env"].value == 3 and r.seq.lanes[0].env == 3
    assert not r.router.table.bindings                              # no row
    assert e.refusal("out:seq:0", "base:env.3.fire") == graphview.LANE_BOUND.format(
        lane=1, env=3)
    view = build(r)
    c = next(c for c in view.cables if c.kind == "lane")
    assert c.dst_port == "base:env.3.fire"
    e = graphview.Edit(r.router.table, r.reg, r.router, view)
    assert e.disconnect(c) == graphview.LANE_NO_DELETE
    # onto `mod` it is a route, as from any trigger lane
    row = e.connect("out:seq:0", "mod:env.4.fire")
    assert isinstance(row, Binding) and row.source == "seq:0"


def test_a_lane_bound_to_a_removed_envelope_draws_nothing():
    r = rig()
    n = r.envs.add()
    r.reg["seq.4.env"].set(n)
    r.reg["seq.4.2"].set(True)
    assert any(c.ref == (3, n) for c in build(r).cables if c.kind == "lane")
    r.envs.remove(n)
    assert not [c for c in build(r).cables if c.kind == "lane"]


# ---- ids with gaps ----

def test_bank_ids_keep_their_gaps():
    r = rig([Binding("lfo:2", "t.x", "position", 1.0)])
    r.lfos.remove(2)
    n = r.envs.add()
    r.envs.add()
    r.envs.remove(n)
    view = build(r)
    assert [x.id for x in view.nodes if x.kind == "lfo"] == ["lfo.1", "lfo.3", "lfo.4"]
    assert [x.id for x in view.nodes if x.kind == "env"] == [f"env.{k}" for k in (1, 2, 3, 4, 5, 7)]
    assert graphview.bank_ids(r.router, r.reg, "env") == [1, 2, 3, 4, 5, 7]
    # a bare router reads the ids off the registry
    assert graphview.bank_ids(None, r.reg, "lfo") == [1, 3, 4]
    c = next(c for c in view.cables if c.kind == "route")
    assert view.owner(c.src_port)[0].id == "lfo.3"   # lfo:2 is LFO 3, its id unmoved


# ---- the page: delete and add, undoable ----

@pytest.fixture()
def page():
    r = rig([Binding("lfo:1", "t.x", "position", 1.0)])
    u = undo.Undo(r.reg, r.router.table, banks=lambda: r.router._banks())
    undo.install(u)
    t = [0.0]

    def settle():
        for _ in range(3):
            t[0] += 1.0
            u.tick(t[0])

    panel = SimpleNamespace(router=r.router, reg=r.reg, library=None, midi=None)
    settle()
    yield SimpleNamespace(r=r, u=u, settle=settle, panel=panel)
    undo.install(None)


def test_the_menu_deletes_an_lfo_through_its_bank_one_undo_step(page):
    r, panel = page.r, page.panel
    ui_graph.view_of(panel)
    assert ui_graph.remove_node(panel, "lfo.2") is None
    assert r.lfos.ids() == [1, 3, 4] and "lfo.2.depth" not in r.reg
    view = ui_graph.view_of(panel)
    assert view.node("lfo.2") is None
    c = next(c for c in view.cables if c.kind == "route")
    assert c.dormant                                  # the route stays, dormant
    page.settle()
    assert page.u.undo() and r.lfos.ids() == [1, 2, 3, 4] and "lfo.2.depth" in r.reg
    assert ui_graph.view_of(panel).node("lfo.2") is not None


def test_a_lane_envelope_is_refused_an_extra_one_goes(page):
    r, panel = page.r, page.panel
    ui_graph.view_of(panel)
    depth = len(page.u.stack)
    assert ui_graph.remove_node(panel, "env.1") == graphview.LANE_ENV_KEPT.format(label="env 1")
    assert r.envs.ids() == [1, 2, 3, 4, 5] and len(page.u.stack) == depth   # no step
    assert ui_graph.voice_refusal(ui_graph.view_of(panel).node("env.5")) is not None
    nid = ui_graph.add_voice(panel, "env", at=(10, 20))
    assert nid == "env.6" and r.envs.ids() == [1, 2, 3, 4, 5, 6]
    page.settle()
    assert ui_graph.view_of(panel).node("env.6").kind == "env"
    assert ui_graph.voice_refusal(ui_graph.view_of(panel).node("env.6")) is None
    assert ui_graph.remove_node(panel, "env.6") is None and 6 not in r.envs
    page.settle()
    assert page.u.undo() and r.envs.ids() == [1, 2, 3, 4, 5, 6]
    page.settle()
    assert page.u.undo() and r.envs.ids() == [1, 2, 3, 4, 5]


def test_the_picker_adds_an_lfo_up_to_the_cap(page):
    r, panel = page.r, page.panel
    assert ui_graph.add_refusal(panel, "lfo") is None
    assert ui_graph.add_voice(panel, "lfo") == "lfo.5"
    page.settle()
    assert page.u.undo() and r.lfos.ids() == [1, 2, 3, 4]
    while r.lfos.can_add():
        r.lfos.add()
    why = graphview.BANK_FULL.format(k=r.lfos.MAX, what="LFOs")
    assert ui_graph.add_refusal(panel, "lfo") == why
    assert ui_graph.add_voice(panel, "lfo") == why and len(r.lfos) == r.lfos.MAX
    # a rig with no bank says so
    bare = SimpleNamespace(router=SimpleNamespace(table=r.router.table), reg=r.reg)
    assert ui_graph.add_refusal(bare, "env") == graphview.NO_BANK.format(what="envelope")
