"""Plan 36 T6 (W6, D4): the **preset only** head chip, on by default.

On, the canvas draws the loadable patch section's nodes, what is wired to them
(less the controllers and the modulation), whatever feeds those, the
windows and (2026-10-31) the eight media channels; off, today's canvas. A
drawing choice only: the state outlives a loadable patch load, and hiding a node
lays nothing else out. A node the picker added this session stays drawn
(`ui_graph.reveal_node`): never saved, forgotten when it is deleted."""

from __future__ import annotations

import pytest
from conftest import seed
from test_graph_legible import party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graphview, ui_graph


@pytest.fixture(autouse=True)
def _lit(monkeypatch):
    monkeypatch.setattr(ui_graph, "PATCH_ONLY", True)     # (the app's default)


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)         # (the corpus: the loadable patches the tests load by slug)
    return shell_rig


def drawn(st):
    return {n.id for n in st["view"].nodes if ui_graph.drawn_node(st, n)}


def upstream(view, seeds):
    """`seeds` and whatever feeds them, to full depth (what `patch_only`
    walks since 2026-10-31)."""
    feeds = {}
    for c in view.cables:
        a, b = (graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port))
        feeds.setdefault(b, set()).add(a)
    out, todo = set(seeds), list(seeds)
    while todo:
        for x in feeds.get(todo.pop(), ()):
            if view.node(x) is not None and x not in out:
                out.add(x)
                todo.append(x)
    return out


def test_on_by_default_the_drawn_set_is_the_sections_and_what_it_reaches(rig):
    st = party(rig)
    view = st["view"]
    assert st["patch_only"] is True
    section = {f"render:{n}" for n in graphview.frame_names(view.spec)}
    assert section and section <= {n.id for n in view.nodes}
    near = set()
    for c in view.cables:
        a, b = (graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port))
        for x, y in ((a, b), (b, a)):
            if x in section and view.node(y) is not None:
                near.add(y)
    fed = upstream(view, section | near)
    want = fed | {n.id for n in view.nodes if n.kind in ("output", "channel")}
    idle = {n.id for n in view.nodes if n.idle}
    assert drawn(st) == want - idle      # (an off effect sits on its idle line)
    for n in view.nodes:        # a controller / modulator is drawn only if cabled to the section
        if n.kind in ("device", "lfo", "env", "macro", "modifier", "source", "analyzer"):
            assert (n.id in drawn(st)) == (n.id in fed and not n.idle)
    assert any(n.kind == "device" for n in view.nodes)        # they exist, only not drawn
    assert any(n.kind == "output" and ui_graph.drawn_node(st, n) for n in view.nodes)
    assert " hidden" in ui_graph.head_line(st, view)


def test_off_is_todays_canvas_and_the_view_is_untouched(rig):
    st = party(rig)
    view = st["view"]
    cables = [c.id for c in view.cables]
    hidden = len(st["hide"])
    assert hidden
    st["patch_only"] = False
    frame(rig.panel, "graph")
    assert st["hide"] == frozenset()
    assert drawn(st) == {n.id for n in view.nodes if not n.idle}
    assert " hidden" not in ui_graph.head_line(st, view)
    st["patch_only"] = True
    frame(rig.panel, "graph")
    assert [c.id for c in view.cables] == cables and len(st["hide"]) == hidden


def test_state_survives_a_loadable_load(rig):
    st = party(rig)
    st["patch_only"] = False
    rig.lib.load("loadable", "party-trip")
    frame(rig.panel, "graph")
    assert ui_graph._state(rig.panel)["patch_only"] is False
    st["patch_only"] = True
    rig.lib.load("loadable", "party-trip")
    frame(rig.panel, "graph")
    assert ui_graph._state(rig.panel)["patch_only"] is True


def test_hiding_lays_nothing_out(rig):
    """The layout still runs over the whole view: toggling moves no node."""
    st = party(rig)
    st["patch_only"] = False
    frame(rig.panel, "graph")
    open_sat = dict(st["sat"])
    st["patch_only"] = True
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    assert {k: v for k, v in st["sat"].items() if k in open_sat} == open_sat


def test_default_is_on():
    assert ui_graph.PATCH_ONLY is True


def test_a_routed_lfo_is_drawn_and_an_unrouted_one_is_hidden(rig):
    st = party(rig)
    view = st["view"]
    target = next(p for p, (nid, _) in view.pins.items()
                  if nid == "render:scene")
    for k in (8, 9):
        view.nodes.append(graphview.VNode(f"lfo.{k}", "lfo", f"LFO {k}"))
        view.pins[f"out:lfo.{k}"] = (f"lfo.{k}", "out")
    view.cables.append(graphview.VCable("c.lfo9", "out:lfo.9", target))
    keep = graphview.patch_only(view)
    assert "lfo.9" in keep and "lfo.8" not in keep


def test_what_feeds_the_section_is_drawn_to_full_depth_downstream_one_hop(rig):
    """2026-10-31: LFO → modifier → param draws the LFO (two hops up);
    what a controller bound to the section also drives (two hops, down)
    is not pulled in."""
    st = party(rig)
    view = st["view"]
    target = next(p for p, (nid, _) in view.pins.items() if nid == "render:scene")
    for nid, kind in (("lfo.8", "lfo"), ("mod.9", "modifier"), ("dev.x", "device"),
                      ("lfo.7", "lfo")):
        view.nodes.append(graphview.VNode(nid, kind, nid))
        view.pins[f"out:{nid}"] = (nid, "out")
        view.pins[f"in:{nid}"] = (nid, "in")
    view.cables += [graphview.VCable("c.1", "out:lfo.8", "in:mod.9"),
                    graphview.VCable("c.2", "out:mod.9", target),
                    graphview.VCable("c.3", "out:dev.x", target),
                    graphview.VCable("c.4", "out:dev.x", "in:lfo.7")]
    keep = graphview.patch_only(view)
    assert {"lfo.8", "mod.9", "dev.x"} <= keep
    assert "lfo.7" not in keep


def test_the_channels_are_always_in_the_loadable_only_view(rig):
    """The owner, after the show of 2026-10-30: with no channel wired to
    the faces "you can't actually spawn one, it just doesn't exist". The
    eight channels are drawn like the outputs, wired or not, filled or
    empty."""
    st = party(rig)
    view = st["view"]
    channels = {n.id for n in view.nodes if n.kind == "channel"}
    assert channels == {f"render:channel.{c}" for c in "abcdefgh"}
    assert channels <= graphview.patch_only(view)
    assert not channels & st["hide"]
    unwired = {n.id for n in view.nodes if n.kind == "channel" and not n.wires}
    assert unwired, "party-trip leaves channels unwired"
    assert unwired <= graphview.patch_only(view)


def test_picking_a_channel_selects_it_and_makes_nothing(rig):
    """media ▸ channel a (`ui_graph.pick_channel`): the node is drawn and
    selected, put where the menu opened — and no node or cable is made:
    the channels always exist."""
    st = party(rig)
    view = st["view"]
    nid = "render:channel.b"
    n = view.node(nid)
    assert n is not None and n.idle and not n.wires        # empty, unwired: on the idle line
    assert nid not in drawn(st)
    nodes = {x.id for x in view.nodes}
    cables = [c.id for c in view.cables]
    rows = len(rig.router.table.bindings)
    ui_graph.pick_channel(rig.panel, "b", at=(300.0, 200.0))
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    assert nid in drawn(st) and nid in st["revealed"]
    assert ui_graph._selection(st, st["view"])[1].id == nid
    assert {x.id for x in st["view"].nodes} == nodes
    assert [c.id for c in st["view"].cables] == cables
    assert len(rig.router.table.bindings) == rows
    assert rig.lib.loaded_patch.layout[nid] == [300, 200]
    # a channel the layout already places keeps its place
    ui_graph.pick_channel(rig.panel, "b", at=(50.0, 50.0))
    assert rig.lib.loaded_patch.layout[nid] == [300, 200]


def test_a_picker_added_node_is_drawn_before_it_has_a_cable(rig):
    """A modifier from the picker has no cable yet, so preset only would
    hide it — and a node that is not drawn cannot be cabled. It stays
    drawn (`reveal_node`) until it is deleted; the reveal is the page's,
    never the loadable patch's."""
    st = party(rig)
    m = ui_graph.add_modifier(rig.panel, "threshold", at=(100.0, 100.0))
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    n = st["view"].node(m.id)
    assert n is not None and not n.wires
    assert m.id in st["revealed"] and m.id in drawn(st) and m.id not in st["hide"]
    assert m.id not in graphview.patch_only(st["view"])     # the reveal alone draws it
    saved = rig.lib.loaded_patch.save_as("fresh-node").read_text()
    assert m.id in saved and "revealed" not in saved
    assert not isinstance(ui_graph.remove_node(rig.panel, m.id), graphview.Refusal)
    assert m.id not in st["revealed"]
    frame(rig.panel, "graph")
    assert st["view"].node(m.id) is None



def test_the_outputs_stay_drawn_with_nothing_wired_into_them(rig):
    """The owner, 2026-10-27: cutting the wire into the outputs made All
    outputs and every window vanish, and nothing could be wired back.
    The outputs are where a picture is wired to: preset only draws them
    whatever reaches them."""
    st = party(rig)
    view = st["view"]
    outs = {n.id for n in view.nodes if n.kind == "output"}
    assert outs and outs <= drawn(st)
    into = [c for c in view.cables if c.kind == "render"
            and view.node(graphview.node_of(view, c.dst_port)).kind == "output"
            and view.node(graphview.node_of(view, c.src_port)).kind != "output"]
    assert into
    for c in into:                              # unwired on the canvas, as the owner did
        assert ui_graph._render_said(rig.panel, ui_graph.render_edit(rig.panel),
                                     lambda e, c=c: e.unwire(c)) is None
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    assert outs <= drawn(st)
