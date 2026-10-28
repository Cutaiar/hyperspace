"""Plan 36 T6 (W6, D4): the **preset only** head chip, on by default.

On, the canvas draws the preset section's nodes, what is wired to them
(less the controllers and the modulation) and the windows those reach;
off, today's canvas. A drawing choice only: the state outlives a preset
load, and hiding a node lays nothing else out."""

from __future__ import annotations

import pytest
from conftest import seed
from test_graph_legible import party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graphview, ui_graph


@pytest.fixture(autouse=True)
def _lit(monkeypatch):
    monkeypatch.setattr(ui_graph, "PRESET_ONLY", True)     # (the app's default)


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)         # (the corpus: the presets the tests load by slug)
    return shell_rig


def drawn(st):
    return {n.id for n in st["view"].nodes if ui_graph.drawn_node(st, n)}


def test_on_by_default_the_drawn_set_is_the_sections_and_what_it_reaches(rig):
    st = party(rig)
    view = st["view"]
    assert st["preset_only"] is True
    section = {f"render:{n}" for n in graphview.frame_names(view.spec)}
    assert section and section <= {n.id for n in view.nodes}
    near = set()
    for c in view.cables:
        a, b = (graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port))
        for x, y in ((a, b), (b, a)):
            if x in section and view.node(y) is not None:
                near.add(y)
    want = section | near | {n.id for n in view.nodes if n.kind == "output"}
    idle = {n.id for n in view.nodes if n.idle}
    assert drawn(st) == want - idle      # (an off effect sits on its idle line)
    for n in view.nodes:        # a controller / modulator is drawn only if cabled to the section
        if n.kind in ("device", "lfo", "env", "macro", "modifier", "source", "analyzer"):
            assert (n.id in drawn(st)) == (n.id in near and not n.idle)
    assert any(n.kind == "device" for n in view.nodes)        # they exist, only not drawn
    assert any(n.kind == "output" and ui_graph.drawn_node(st, n) for n in view.nodes)
    assert " hidden" in ui_graph.head_line(st, view)


def test_off_is_todays_canvas_and_the_view_is_untouched(rig):
    st = party(rig)
    view = st["view"]
    cables = [c.id for c in view.cables]
    hidden = len(st["hide"])
    assert hidden
    st["preset_only"] = False
    frame(rig.panel, "graph")
    assert st["hide"] == frozenset()
    assert drawn(st) == {n.id for n in view.nodes if not n.idle}
    assert " hidden" not in ui_graph.head_line(st, view)
    st["preset_only"] = True
    frame(rig.panel, "graph")
    assert [c.id for c in view.cables] == cables and len(st["hide"]) == hidden


def test_state_survives_a_preset_load(rig):
    st = party(rig)
    st["preset_only"] = False
    rig.lib.load("presets", "party-trip")
    frame(rig.panel, "graph")
    assert ui_graph._state(rig.panel)["preset_only"] is False
    st["preset_only"] = True
    rig.lib.load("presets", "party-trip")
    frame(rig.panel, "graph")
    assert ui_graph._state(rig.panel)["preset_only"] is True


def test_hiding_lays_nothing_out(rig):
    """The layout still runs over the whole view: toggling moves no node."""
    st = party(rig)
    st["preset_only"] = False
    frame(rig.panel, "graph")
    open_sat = dict(st["sat"])
    st["preset_only"] = True
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    assert {k: v for k, v in st["sat"].items() if k in open_sat} == open_sat


def test_default_is_on():
    assert ui_graph.PRESET_ONLY is True


def test_a_routed_lfo_is_drawn_and_an_unrouted_one_is_hidden(rig):
    st = party(rig)
    view = st["view"]
    target = next(p for p, (nid, _) in view.pins.items()
                  if nid == "render:scene")
    for k in (8, 9):
        view.nodes.append(graphview.VNode(f"lfo.{k}", "lfo", f"LFO {k}"))
        view.pins[f"out:lfo.{k}"] = (f"lfo.{k}", "out")
    view.cables.append(graphview.VCable("c.lfo9", "out:lfo.9", target))
    keep = graphview.preset_only(view)
    assert "lfo.9" in keep and "lfo.8" not in keep


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
