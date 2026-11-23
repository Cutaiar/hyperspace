"""Plan 84: GRAPH's **gpu cost** chip — every render node marked by its GPU
time per frame, ranked within the frame and eased over about a second; the
frame's total and its three costliest on a line under the head; a node that
made nothing this frame said to have made nothing, not to cost nothing.

Held here: the easing and the ranking are pure (`ui_graph.ease_costs`,
`rank_costs`, `heat_rgb`, `cost_line`, `node_cost`); the renderer says what
each node made only while the chip asks (`Renderer.gpu_watch`,
`render.gpu_made`) and the outputs are the same bytes either way; the chip is
off by default, page state only, and off it asks nothing and draws nothing."""

from __future__ import annotations

import contextlib
import itertools
import json
import math
from types import SimpleNamespace as NS

import numpy as np
import pytest
from conftest import seed
from test_graph_legible import party
from test_thumbnails import SIZE, S, _px, _views, _wire
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graphview, render, ui, ui_graph


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)
    return shell_rig


# ---------------------------------------------------------------- the easing, pure

def test_a_new_node_starts_at_its_time_not_from_zero():
    assert ui_graph.ease_costs({}, {"a": 2.0, "b": 0.5}, None, 1 / 60) == {"a": 2.0, "b": 0.5}


def test_a_step_settles_in_about_a_second():
    prev = {"a": 1.0}
    for _ in range(60):                         # one second at 60 a second
        prev = ui_graph.ease_costs(prev, {"a": 3.0}, None, 1 / 60)
    # 1 − e^(−1) of the way after tau
    assert prev["a"] == pytest.approx(1.0 + 2.0 * (1 - math.exp(-1)), rel=1e-6)
    one = ui_graph.ease_costs({"a": 1.0}, {"a": 3.0}, None, 1 / 60)["a"]
    assert 1.0 < one < 1.05                     # one frame barely moves it: no flicker


def test_the_easing_does_not_depend_on_the_frame_rate():
    at30 = {"a": 0.0}
    for _ in range(30):
        at30 = ui_graph.ease_costs(at30, {"a": 1.0}, None, 1 / 30)
    at120 = {"a": 0.0}
    for _ in range(120):
        at120 = ui_graph.ease_costs(at120, {"a": 1.0}, None, 1 / 120)
    assert at30["a"] == pytest.approx(at120["a"], rel=1e-9)


def test_a_node_that_made_nothing_drops_out_and_comes_back_at_its_time():
    got = ui_graph.ease_costs({"a": 1.0, "b": 4.0}, {"a": 1.0, "b": 0.0}, {"a"}, 1 / 60)
    assert got == {"a": 1.0}                    # b ran nothing: not "0 ms"
    back = ui_graph.ease_costs(got, {"a": 1.0, "b": 0.3}, {"a", "b"}, 1 / 60)
    assert back["b"] == 0.3


def test_no_time_passed_moves_nothing():
    assert ui_graph.ease_costs({"a": 1.0}, {"a": 5.0}, None, 0.0) == {"a": 1.0}


# ---------------------------------------------------------------- the ranking, pure

def test_ranked_within_the_frame_by_share_of_the_costliest():
    got = ui_graph.rank_costs({"scene": 1.0, "blocks": 4.0, "bloom": 2.0, "out": 0.0})
    assert got == {"blocks": (1, 1.0), "bloom": (2, 0.5), "scene": (3, 0.25), "out": (4, 0.0)}


def test_a_tie_is_ranked_by_name_so_it_never_swaps():
    for _ in range(3):
        assert ui_graph.rank_costs({"b": 1.0, "a": 1.0}) == {"a": (1, 1.0), "b": (2, 1.0)}


def test_nothing_to_rank_and_nothing_costing():
    assert ui_graph.rank_costs({}) == {}
    assert ui_graph.rank_costs({"a": 0.0, "b": 0.0}) == {"a": (1, 0.0), "b": (2, 0.0)}


def test_the_ramp_runs_black_to_white_always_brighter():
    assert ui_graph.heat_rgb(0.0) == (0.0, 0.0, 0.0)
    assert ui_graph.heat_rgb(1.0) == (1.0, 1.0, 1.0)
    lum = [sum(ui_graph.heat_rgb(k / 100)) for k in range(101)]
    assert all(b > a for a, b in itertools.pairwise(lum))
    assert ui_graph.heat_rgb(-1) == (0.0, 0.0, 0.0) and ui_graph.heat_rgb(2) == (1.0, 1.0, 1.0)


def test_the_head_line_is_the_total_and_the_three_costliest():
    ms = {"scene": 0.6, "blocks": 2.1, "bloom": 0.9, "output.1": 0.1}
    line = ui_graph.cost_line(ms, {"blocks": "Blocks", "bloom": "Bloom", "scene": "scene"})
    assert line == "gpu 3.70 ms in nodes  ·  Blocks 2.10  ·  Bloom 0.90  ·  scene 0.60"
    assert ui_graph.cost_line({}, {}) == "gpu: measuring…"
    assert ui_graph.cost_line({}, {}, "no GPU timer queries") == "gpu: no GPU timer queries"


def test_a_badge_says_its_rank_for_the_top_three_and_nothing_for_nothing():
    assert ui_graph.Cost(2.104, 1, 1.0).words == "#1 · 2.10 ms"
    assert ui_graph.Cost(0.05, 4, 0.02).words == "0.05 ms"
    assert ui_graph.NOTHING.words == "made nothing"


# ---------------------------------------------------------------- a node's mark, pure

def _node(nid, kind="render", faint=False):
    return graphview.VNode(id=nid, kind=kind, label=nid, faint=faint)


def test_each_kind_of_node_gets_its_mark():
    st = {"cost": True, "cost_ms": {"kaleido": 2.0, "scene": 1.0},
          "cost_rank": ui_graph.rank_costs({"kaleido": 2.0, "scene": 1.0}),
          "cost_made": {"gpu_ran": frozenset({"kaleido", "scene", "output.1"}),
                        "gpu_free": frozenset({"switch.1"}),
                        "gpu_built": frozenset({"kaleido", "scene", "output.1", "switch.1",
                                                "acid"})}}
    assert ui_graph.node_cost(st, _node("render:kaleido")) == ui_graph.Cost(2.0, 1, 1.0)
    assert ui_graph.node_cost(st, _node("render:scene")) == ui_graph.Cost(1.0, 2, 0.5)
    # built, ran no pass: an effect switched off
    assert ui_graph.node_cost(st, _node("render:acid")) is ui_graph.NOTHING
    # not built: unreached, drawn faint
    assert ui_graph.node_cost(st, _node("render:wave", faint=True)) is ui_graph.NOTHING
    # ran, but its median is not read back yet: nothing said
    assert ui_graph.node_cost(st, _node("output:output.1", kind="output")) is None
    # no pass of its own: its time is its consumer's
    assert ui_graph.node_cost(st, _node("render:switch.1")) is None
    # the modulation side has no GPU time
    assert ui_graph.node_cost(st, _node("lfo:lfo.1", kind="lfo")) is None
    # the chip off: no mark at all
    assert ui_graph.node_cost({**st, "cost": False}, _node("render:kaleido")) is None
    # before the renderer reported: only the timed ones
    early = {**st, "cost_made": None}
    assert ui_graph.node_cost(early, _node("render:acid")) is None


# ---------------------------------------------------------------- the renderer's read side

def _renderer(ctx):
    """The scene through kaleido to output 1, acid wired in after it but
    switched off, wave fed by the scene and reaching nothing."""
    r = render.Renderer(ctx)
    r.ghost.state.on = False
    for n in ("kaleido", "wave", "acid"):
        r.fx.state.values[n].update(on=True, mix=1.0)
    r.fx.state.values["acid"]["on"] = False
    assert not r.fx.compile_all()
    r.wiring = _wire(("shape", "scene.geometry"), ("scene", "kaleido.image"),
                     ("kaleido", "acid.image"), ("acid", "output.1.image"),
                     ("scene", "wave.image"),
                     nodes=({"kind": "effect", "file": "kaleido"},
                            {"kind": "effect", "file": "wave"},
                            {"kind": "effect", "file": "acid"}))
    return r


def test_unasked_the_renderer_says_nothing_more(ctx):
    r, views = _renderer(ctx), _views(ctx)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    assert not {"gpu_ran", "gpu_free", "gpu_built"} & set(r.stats)


def test_asked_it_says_what_each_node_made_for_one_frame(ctx):
    r, views = _renderer(ctx), _views(ctx)
    r.gpu_watch = True
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    ran, free, built = r.stats["gpu_ran"], r.stats["gpu_free"], r.stats["gpu_built"]
    assert {"kaleido", "scene", "output.1"} <= ran
    assert "acid" in built and "acid" not in ran and "acid" not in free     # off: made nothing
    assert "wave" not in built                                              # unreached: unbuilt
    assert "shape" in free or "shape" in ran      # a geometry: its scene's time, or its own
    assert r.gpu_watch is False                   # asked again each frame, or it stops
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    assert "gpu_ran" not in r.stats


def test_the_outputs_are_the_same_bytes_asked_or_not(ctx):
    plain, asked = _renderer(ctx), _renderer(ctx)
    pv, av = _views(ctx), _views(ctx)
    for k in range(3):
        t = 2.0 + k / 60
        plain.draw_outputs(S, *SIZE, 1.0, pv, t_now=t)
        asked.gpu_watch = True
        asked.draw_outputs(S, *SIZE, 1.0, av, t_now=t)
        assert ctx.error == "GL_NO_ERROR"
        for a, b in zip(pv, av, strict=True):
            assert np.array_equal(_px(a.target), _px(b.target)), k
        assert plain.stats["effects"] == asked.stats["effects"]
    assert "wave" not in asked._graph.nodes       # still never built


def test_a_frame_whose_picks_cannot_be_read_marks_nothing_made():
    def boom(_frame):
        raise RuntimeError("no frame")
    got = render.gpu_made(NS(pulled=boom, order=[], timed=[]), None, [])
    assert got == {"gpu_ran": frozenset(), "gpu_free": frozenset(), "gpu_built": frozenset(),
                   "gpu_owner": {}}


def _graph(*nodes, timed=()):
    """A stand-in graph: every node pulled, `timed` the names the timer lists."""
    order = [NS(name=n, MAKES=False) for n in nodes]
    return NS(order=order, pulled=lambda _f: frozenset(nodes), timed=list(timed))


def test_a_listed_node_that_asked_for_no_query_made_nothing():
    """Devin's finding on #470: a segment switched off is still in the timer's
    list (its median 0) but runs no pass. What ran is what asked the timer,
    not what the timer lists."""
    got = render.gpu_made(_graph("scene", "segment.1", "switch", timed=("scene", "segment.1")),
                          None, {"scene"})
    assert got["gpu_ran"] == {"scene"}
    assert "segment.1" not in got["gpu_ran"] and "segment.1" not in got["gpu_free"]
    assert got["gpu_free"] == {"switch"}                # no pass of its own: not a cost
    st = {"cost": True, "cost_ms": {}, "cost_rank": {}, "cost_made": got}
    assert ui_graph.node_cost(st, _node("render:segment.1")) is ui_graph.NOTHING


def test_the_timer_notes_every_name_that_asks_only_while_watched(ctx):
    timer = render.PassTimer(ctx)
    with timer.time("scene"):
        pass
    assert getattr(timer, "watch", None) is None        # unwatched: nothing noted
    timer.watch = set()
    with timer.time("scene"):
        timer._active = True                            # a pass inside another's query
        with timer.time("bloom"):
            pass
        timer._active = False
    assert timer.watch == {"scene", "bloom"}            # the inner ran too
    timer.watch = None
    timer.end_frame(["scene"])


def test_a_pass_under_a_name_of_its_own_is_its_owners():
    """Devin's finding on #470: a delay's write and a look-back's capture are
    timed under names no canvas node carries; their time is their node's."""
    ms = {"delay(write)": 8.0, "scene": 1.0, "lookback": 0.5, "lookback(capture)": 0.25}
    owner = {"delay(write)": "delay", "lookback(capture)": "lookback"}
    assert ui_graph.fold_owners(ms, owner) == {"delay": 8.0, "scene": 1.0, "lookback": 0.75}
    assert ui_graph.fold_owners(ms, {}) == ms


def test_the_renderer_names_each_passes_owner(ctx):
    from test_thumbnails import _renderer as stateful
    from test_thumbnails import _views as two_views
    r, views = stateful(ctx), two_views(ctx)
    for t in (2.0, 2.1):
        r.gpu_watch = True
        r.draw_outputs(S, *SIZE, 1.0, views, t_now=t)
    owner = r.stats["gpu_owner"]
    writes = [n for n in r._graph.nodes if n.endswith("(write)")]
    captures = [n for n in r._graph.nodes if n.endswith("(capture)")]
    assert writes and captures
    assert {owner[n] for n in writes} == {"delay"}
    assert {owner[n] for n in captures} == {"lookback"}
    assert "delay" in r.stats["gpu_ran"]                # its write ran: it made something


# ---------------------------------------------------------------- the page

def test_the_chip_is_off_by_default_and_last_on_the_head(rig, monkeypatch):
    st = party(rig)
    assert st["cost"] is False
    labels: list[str] = []
    lit = ui.lit_chip
    monkeypatch.setattr(ui, "lit_chip", lambda label, on, *a, **k:
                        labels.append(label) or lit(label, on, *a, **k))
    frame(rig.panel, "graph")
    head = [x for x in labels if x.endswith("##graph")]
    assert head[-1] == ui_graph.COST_LABEL
    assert head.index(ui_graph.TINT_LABEL) < head.index(ui_graph.COST_LABEL)


@pytest.mark.parametrize("width", [820, 540])
def test_the_chip_stays_inside_a_narrow_page(rig, monkeypatch, width):
    """Devin's finding on #470: on a narrow controls panel the head's row of
    chips runs past the page's right edge; the chip takes a row of its own
    (`ui.beside`) rather than a place nobody can click."""
    from imgui_bundle import imgui
    party(rig)
    imgui.get_io().display_size = imgui.ImVec2(width, 820)
    seen: list[tuple[float, float]] = []
    lit = ui.lit_chip

    def spy(label, on, *a, **k):
        hit = lit(label, on, *a, **k)
        if label == ui_graph.COST_LABEL:
            right = imgui.get_window_pos().x + imgui.get_window_size().x
            seen.append((imgui.get_item_rect_max().x, right))
        return hit
    monkeypatch.setattr(ui, "lit_chip", spy)
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    assert seen
    for x1, right in seen:
        assert x1 <= right, (x1, right)


def test_off_it_asks_nothing_and_draws_nothing_extra(rig, monkeypatch):
    st = party(rig)
    badges: list[str] = []
    monkeypatch.setattr(ui_graph, "_cost_badge", lambda st_, n: badges.append(n.id))
    pushes: list[str] = []
    for verb in ("push_style_color", "push_style_var"):
        real = getattr(ui_graph.ed, verb)
        monkeypatch.setattr(ui_graph.ed, verb, lambda *a, _r=real, _v=verb, **k:
                            pushes.append(_v) or _r(*a, **k))
    frame(rig.panel, "graph")
    off_pushes = list(pushes)
    # the same frame with the marks taken out altogether: not one push more
    monkeypatch.setattr(ui_graph, "_cost_style", lambda st_, n: contextlib.nullcontext())
    pushes.clear()
    frame(rig.panel, "graph")
    assert pushes == off_pushes
    assert badges == []
    assert not getattr(rig.panel.renderer, "gpu_watch", False)
    assert "cost_line" not in st and st["cost_ms"] == {}


def test_lit_it_asks_the_renderer_and_marks_the_render_nodes(rig, monkeypatch):
    st = party(rig)
    view = st["view"]
    r = rig.panel.renderer
    render_names = [ui_graph.thumb_name(n) for n in view.nodes
                    if n.kind in graphview.FRAME_VKINDS]
    assert len(render_names) >= 3
    ms = {name: 0.1 * (i + 1) for i, name in enumerate(render_names[:3])}
    r.stats = {"gpu_ms": ms, "gpu_ran": frozenset(ms), "gpu_free": frozenset(),
               "gpu_built": frozenset(render_names)}
    badges: list[str] = []
    real = ui_graph._cost_badge
    monkeypatch.setattr(ui_graph, "_cost_badge", lambda st_, n: badges.append(n.id) or real(st_, n))
    st["cost"] = True
    frame(rig.panel, "graph")
    assert r.gpu_watch is True
    assert st["cost_rank"][render_names[2]] == (1, 1.0)
    assert st["cost_line"].startswith("gpu 0.60 ms in nodes")
    drawn = {n.id for n in view.nodes if ui_graph.drawn_node(st, n)}
    marked = {n.id for n in view.nodes if n.id in drawn and ui_graph.node_cost(st, n) is not None}
    assert marked and marked <= set(badges)          # (`_cost_badge` passes the rest)
    # every render node the renderer built and timed but not this frame: made nothing
    for n in view.nodes:
        if n.id in drawn and ui_graph.thumb_name(n) not in ms and n.kind in graphview.FRAME_VKINDS:
            assert ui_graph.node_cost(st, n) is ui_graph.NOTHING, n.id
    # off again: forgotten, the renderer no longer asked
    st["cost"] = False
    r.gpu_watch = False
    badges.clear()
    frame(rig.panel, "graph")
    assert badges == [] and st["cost_ms"] == {} and r.gpu_watch is False


def test_a_deck_switch_starts_the_easing_again(rig):
    """Devin's finding on #470: the easing is the renderer's, not the page's —
    another deck's renderer starts from its own times, not the last deck's."""
    st = party(rig)
    st["cost"] = True
    a = NS(stats={"gpu_ms": {"scene": 20.0, "output.1": 1.0}})
    b = NS(stats={"gpu_ms": {"scene": 1.0, "output.1": 2.0}})
    rig.panel.renderer = a
    frame(rig.panel, "graph")
    assert st["cost_rank"]["scene"][0] == 1
    rig.panel.renderer = b
    frame(rig.panel, "graph")
    assert st["cost_ms"] == {"scene": 1.0, "output.1": 2.0}
    assert st["cost_rank"]["output.1"][0] == 1


def test_the_chip_reaches_neither_the_loadable_nor_the_show(rig):
    st = party(rig)
    lib = rig.lib
    plain = json.loads(lib.loaded_patch.save_as("UNCOSTED").read_text())
    lib.install.save("plain-show")
    show_plain = json.loads(lib.install.path.read_text())
    st["cost"] = True
    frame(rig.panel, "graph")
    lit = json.loads(lib.loaded_patch.save_as("COSTED").read_text())
    lib.install.save("costed-show")
    show_lit = json.loads(lib.install.path.read_text())
    for doc in (plain, lit, show_plain, show_lit):
        doc.pop("name", None)
        assert "gpu cost" not in json.dumps(doc)
    assert plain == lit
    assert show_plain == show_lit
