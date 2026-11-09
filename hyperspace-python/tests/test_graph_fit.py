"""GRAPH opens with every node in view, and every load brings them into view
again: framed in what the side pane leaves of the canvas, centred there,
never closer than the display's start zoom (Dillon, 2026-11-07)."""

import copy

import pytest
from conftest import seed
from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed
from test_ui_shell import build_rig, frame

from hyperspace import ui_graph

WIDE = (1600, 900)


def _visible(box, canvas, pane):
    """The screen rect, from the canvas's left, that `box` lands on when the
    editor fits it to `canvas` (the box's aspect is the canvas's)."""
    x0, y0, x1, y1 = box
    k = canvas[0] / (x1 - x0)
    assert k == pytest.approx(canvas[1] / (y1 - y0))
    return k, (lambda x, y: ((x - x0) * k, (y - y0) * k))


@pytest.mark.parametrize("content", [(0, 0, 2000, 400), (0, 0, 300, 900), (-50, 10, 950, 610)])
def test_the_box_puts_the_content_in_the_middle_of_whats_left_beside_the_pane(content):
    canvas, pane = (1500.0, 800.0), ("beside", 300.0)
    box = ui_graph.fit_box(content, canvas, pane, 10.0)
    _k, at = _visible(box, canvas, pane)
    (a, b), (c, d) = at(content[0], content[1]), at(content[2], content[3])
    assert 0 <= a + 1e-6 and c <= 1200 + 1e-6 and 0 <= b + 1e-6 and d <= 800 + 1e-6
    assert (a + c) / 2 == pytest.approx(600)            # the middle of the 1200 px left
    assert (b + d) / 2 == pytest.approx(400)


def test_the_box_under_a_band_and_never_closer_than_the_start_zoom():
    canvas = (1000.0, 900.0)
    box = ui_graph.fit_box((0, 0, 400, 100), canvas, ("below", 300.0), 10.0)
    _k, at = _visible(box, canvas, None)
    (a, b), (c, d) = at(0, 0), at(400, 100)
    assert (a + c) / 2 == pytest.approx(500) and (b + d) / 2 == pytest.approx(300)
    assert d <= 600 + 1e-6
    small = ui_graph.fit_box((0, 0, 50, 20), canvas, ("beside", 200.0), 1.3)
    k, _at = _visible(small, canvas, None)
    assert k == pytest.approx(1.3)                     # three nodes: not blown up


def _rects(monkeypatch) -> dict:
    """Each frame: every drawn node's screen rect, read while the editor draws."""
    seen: dict = {}
    real = ui_graph._moved

    def moved(panel, st, view):
        seen.clear()
        for n in view.nodes:
            if not ui_graph.drawn_node(st, n):
                continue
            k = ed.NodeId(ui_graph._id(st, "n:" + n.id))
            p, z = ed.get_node_position(k), ed.get_node_size(k)
            a, b = ed.canvas_to_screen(p), ed.canvas_to_screen(imgui.ImVec2(p.x + z.x, p.y + z.y))
            seen[n.id] = (a.x, a.y, b.x, b.y)
        return real(panel, st, view)
    monkeypatch.setattr(ui_graph, "_moved", moved)
    return seen


@pytest.fixture()
def fitted(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.desk, r.panel.graph_fit = False, True
        r.panel.graph_start_zoom = 1.3
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        seed(r.lib.home)
        r.lib.load("loadable", "party-trip")
        rects = _rects(monkeypatch)
        for _ in range(4):
            frame(r.panel, "graph")
        yield r, ui_graph._state(r.panel), rects


def _in_view(r, st, rects) -> None:
    """Every node inside the canvas left of the pane, the lot centred there."""
    (px, py), (_pw, ph) = st["details_rect"]
    (cx, _cy), _size, *_ = r.panel.canvas_px
    assert rects
    x0 = min(a for a, *_ in rects.values())
    y0 = min(b for _, b, *_ in rects.values())
    x1 = max(c for *_, c, _ in rects.values())
    y1 = max(d for *_, d in rects.values())
    assert cx - 1 <= x0 and x1 <= px + 1                 # left of the pane
    assert py - 1 <= y0 and y1 <= py + ph + 1
    assert abs((x0 + x1) / 2 - (cx + px) / 2) < 0.1 * (px - cx)     # centred there


def test_graph_opens_with_every_node_in_view_left_of_the_pane(fitted):
    r, st, rects = fitted
    _in_view(r, st, rects)
    assert "fit" not in st
    assert 1 / st["zoom"] <= r.panel.graph_start_zoom + 1e-3


def test_a_load_brings_every_node_back_into_view(fitted):
    r, st, rects = fitted
    st["pan"] = (4000.0, 3000.0)                        # dragged well away
    for _ in range(3):
        frame(r.panel, "graph")
    (px, _py), _ = st["details_rect"]
    (cx, _cy), *_ = r.panel.canvas_px
    assert any(a > px or c < cx for a, _b, c, _d in rects.values())   # out of sight
    r.lib.load("loadable", "party-noita")
    for _ in range(30):                                 # (a glide, then still)
        frame(r.panel, "graph")
    _in_view(r, st, rects)


def test_a_save_as_or_an_edit_leaves_the_view_as_it_is(fitted):
    r, st, _rects = fitted
    lp = r.lib.loaded_patch
    lp.save_as("party-trip copy")                       # the name alone
    for _ in range(6):
        frame(r.panel, "graph")
    assert "fit" not in st and not st.get("fit_moved")
    lp.graph.spec = copy.copy(lp.graph.spec)            # the graph alone: a new object
    for _ in range(6):
        frame(r.panel, "graph")
    assert "fit" not in st


def test_a_fit_keeps_the_selection(fitted):
    r, st, _rects = fitted
    view = ui_graph.view_of(r.panel)
    nid = next(n.id for n in view.nodes if ui_graph.drawn_node(st, n) and n.kind != "modifier")
    r.panel.select_graph_node(nid)
    for _ in range(3):
        frame(r.panel, "graph")
    assert r.panel.graph_selected == nid
    ui_graph.ask_fit(st, instant=True)
    for _ in range(4):
        frame(r.panel, "graph")
    assert "fit" not in st and r.panel.graph_selected == nid


def test_tidy_frames_in_what_the_pane_leaves(fitted, monkeypatch):
    r, st, rects = fitted
    st["pan"] = (-3000.0, 0.0)
    for _ in range(3):
        frame(r.panel, "graph")
    ui_graph.tidy(r.panel, st, ui_graph.view_of(r.panel))
    for _ in range(30):                                 # (a glide, then still)
        frame(r.panel, "graph")
    _in_view(r, st, rects)


def test_off_in_the_rig_the_canvas_opens_as_measured(tmp_path):
    """`Panel.graph_fit` off (the canvas tests' rig): no fit asked at all."""
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        for _ in range(3):
            frame(r.panel, "graph")
        assert "fit" not in ui_graph._state(r.panel)


def test_a_fit_keeps_a_selected_cable(fitted, monkeypatch):
    """The selection kept is the selection, a cable's too (review, 2026-11-09):
    `clear_selection` clears links as well as nodes."""
    r, st, _rects = fitted
    view = ui_graph.view_of(r.panel)
    ids = {c.id for c in view.cables} | set(st["bundles"])
    cid = next(k[2:] for k in st["ids"] if k.startswith("c:") and k[2:] in ids)
    real = ui_graph._fit_when_asked
    once = {"done": False}

    def select_then_draw(panel, st_, v, lay, size):
        if not once["done"]:                            # (inside the editor)
            ed.select_link(ed.LinkId(ui_graph._id(st_, "c:" + cid)))
            once["done"] = True
        return real(panel, st_, v, lay, size)
    monkeypatch.setattr(ui_graph, "_fit_when_asked", select_then_draw)
    for _ in range(3):
        frame(r.panel, "graph")
    before = ui_graph._selection(st, st["view"])
    assert before is not None and before[0] in ("cable", "bundle")
    ui_graph.ask_fit(st)
    for _ in range(4):
        frame(r.panel, "graph")
    after = ui_graph._selection(st, st["view"])
    assert after is not None and (after[0], getattr(after[1], "id", None)) == \
        (before[0], getattr(before[1], "id", None))
