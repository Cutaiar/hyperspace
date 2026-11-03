"""Plan 49, stage 1: GRAPH's side pane is always on and holds folding
sections — selection, presets, lookback, faces, analyzer — each drawing
what its page draws, found by the panel driver by the ids its page uses;
the fold state is this Mac's, in ui.json beside the pane's width."""

import json

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace import ui_graph, ui_pane
from hyperspace.ui import PAGE_KEYS, Panel

WIDE = (1600, 900)      # a page wider than ui_graph.WIDE: the pane beside the canvas

# a control each section draws, by the id its page draws it under
SECTION_IDS = {
    "presets": "new##new",           # the preset strip's new chip (ui_presets.strip)
    "lookback": "dream.on",
    "faces": "view.faces",
    "analyzer": "scene.select",
}


@pytest.fixture()
def pane(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.desk = False                     # the panel the whole window
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        d = Driver(step=lambda: frame(r.panel, "graph"))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        yield r, d


def _st(r):
    return ui_graph._state(r.panel)


def _inside(rect, box) -> bool:
    (x, y), (w, _h) = box
    x0, y0, x1, _y1 = rect
    return x <= x0 and x1 <= x + w + 1 and y <= y0


def test_the_pane_is_on_with_nothing_selected_and_says_so(pane, monkeypatch):
    r, d = pane
    st = _st(r)
    assert r.panel.graph_selected is None
    assert st["details_rect"] is not None            # the pane, with nothing selected
    assert {"pane.selection", "pane.presets", "pane.lookback", "pane.faces",
            "pane.analyzer"} <= set(d.rects)
    said: list[str] = []
    real = imgui.text_wrapped
    monkeypatch.setattr(imgui, "text_wrapped", lambda s, *a: (said.append(s), real(s, *a)))
    d.run(d.wait(1))
    assert ui_pane.NOTHING in said
    assert st["pane_drawn"] == ["selection", "presets"]      # the defaults (rec)


@pytest.mark.parametrize("key", sorted(SECTION_IDS))
def test_each_section_opens_by_a_click_and_its_controls_are_found_by_id(pane, key):
    r, d = pane
    st = _st(r)
    pid = SECTION_IDS[key]
    if key == "presets":                             # open by default: fold it first
        d.run(d.click("pane.presets"), d.park())
        assert "presets" not in st["pane_drawn"]
    else:
        assert "pane." + key in d.rects and key not in st["pane_drawn"]
        with pytest.raises(KeyError):
            d.rect(pid)
    if key != "presets":
        d.run(d.click("pane.presets"), d.park())     # room for the one under test
    d.run(d.click("pane." + key), d.park(), d.wait(1))
    assert key in st["pane_drawn"]
    assert _inside(d.rect(pid), st["details_rect"])   # drawn in the pane, under its page's id


def test_a_click_in_a_section_moves_the_param_as_on_its_page(pane):
    r, d = pane
    d.run(d.click("pane.faces"), d.park(), d.wait(1))
    was = bool(r.reg["view.faces"].base)
    d.run(d.click("view.faces"), d.park())
    assert bool(r.reg["view.faces"].base) is (not was)
    d.run(d.click("pane.lookback"), d.park(), d.wait(1))
    was = bool(r.reg["dream.on"].base)
    d.run(d.click("dream.on"), d.park())
    assert bool(r.reg["dream.on"].base) is (not was)


def test_a_selection_shows_in_the_selection_section(pane):
    r, d = pane
    st = _st(r)
    view = ui_graph.view_of(r.panel)
    node = next(n for n in view.nodes if n.kind != "modifier")
    r.panel.select_graph_node(node.id)
    d.run(d.wait(3))
    assert r.panel.graph_selected == node.id
    assert ui_graph.sel_key(ui_graph._selection(st, st["view"])) == ("node", node.id)
    assert "selection" in st["pane_drawn"]


def test_a_new_selection_unfolds_the_selection_section(pane):
    r, d = pane
    st = _st(r)
    d.run(d.click("pane.selection"), d.park())
    assert "selection" not in st["pane_drawn"]
    view = ui_graph.view_of(r.panel)
    r.panel.select_graph_node(view.nodes[0].id)
    d.run(d.wait(3))
    assert "selection" in st["pane_drawn"]


def test_the_fold_state_round_trips_through_this_macs_ui_json(pane):
    r, d = pane
    st = _st(r)
    machine = r.lib.machine
    d.run(d.click("pane.analyzer"), d.park(), d.click("pane.presets"), d.park())
    doc = json.loads((machine / ui_pane.UI_FILE).read_text())
    assert doc["pane"]["open"]["analyzer"] is True and doc["pane"]["open"]["presets"] is False
    assert ui_pane.read_open(machine) == dict(ui_pane.DEFAULT_OPEN, analyzer=True,
                                              presets=False)
    # a fresh page state (a relaunch) reads it back
    st.pop("pane_open")
    d.run(d.wait(2))
    assert st["pane_drawn"] == ["selection", "analyzer"]
    # the width beside it is kept by a drag's write, and the fold by a click's
    ui_graph.write_side(machine, 400.0)
    doc = json.loads((machine / ui_pane.UI_FILE).read_text())
    assert doc["graph"]["side_w"] == 400.0 and doc["pane"]["open"]["analyzer"] is True
    ui_pane.write_open(machine, ui_pane.read_open(machine))
    assert ui_graph.read_side(machine) == 400.0


def test_a_bad_ui_json_costs_only_the_memory(tmp_path):
    assert ui_pane.read_open(tmp_path) == ui_pane.DEFAULT_OPEN          # no file
    (tmp_path / ui_pane.UI_FILE).write_text("[1, 2]")
    assert ui_pane.read_open(tmp_path) == ui_pane.DEFAULT_OPEN          # not an object
    (tmp_path / ui_pane.UI_FILE).write_text(
        '{"pane": {"open": {"faces": true, "analyzer": "yes", "nope": true}}, "x": 1}')
    got = ui_pane.read_open(tmp_path)
    assert got["faces"] is True and got["analyzer"] is False and "nope" not in got
    ui_pane.write_open(tmp_path, got)
    assert json.loads((tmp_path / ui_pane.UI_FILE).read_text())["x"] == 1   # the rest kept
    ui_pane.write_open(tmp_path / "missing" / "dir", got)                # no raise
    assert ui_pane.read_open(None) == ui_pane.DEFAULT_OPEN


def test_open_bodies_share_the_pane():
    assert ui_pane.body_height(600.0, 2) == 300.0
    assert ui_pane.body_height(200.0, 3) == ui_pane.MIN_BODY_H
    assert ui_pane.body_height(600.0, 0) == 0.0


def test_every_section_open_draws_with_no_conflicting_ids(pane, monkeypatch):
    """All five open at once: each widget its own imgui id (the label
    hashed under the id stack), though the sections reuse their pages'
    labels and two of them draw preset strips."""
    r, _d = pane
    st = _st(r)
    st["pane_open"] = dict.fromkeys(ui_pane.KEYS, True)
    view = ui_graph.view_of(r.panel)
    r.panel.select_graph_node(view.nodes[0].id)

    def tall() -> None:                 # a window tall enough for every body unscrolled
        imgui.get_io().display_size = imgui.ImVec2(1600, 2400)
        imgui.new_frame()
        imgui.set_window_size("CONTROLS", imgui.ImVec2(1576, 2376))
        r.panel.draw(1 / 60, 60.0)
        imgui.end_frame()
    for _ in range(3):
        tall()
    assert st["pane_drawn"] == list(ui_pane.KEYS)
    ids: list[tuple[int, str]] = []
    for fn in ("button", "checkbox", "slider_float", "slider_int", "combo",
               "invisible_button", "small_button", "selectable"):
        real = getattr(imgui, fn)

        def rec(label, *a, _real=real, **k):
            ids.append((imgui.get_id(label), label))
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    tall()
    seen = [i for i, _ in ids]
    dup = {lb for i, lb in ids if seen.count(i) > 1}
    assert not dup, f"conflicting ids {sorted(dup)}"


def test_the_pages_still_draw_their_bodies(pane):
    """The rail and the pages are untouched: each page whose body a
    section shares still draws it, at full height."""
    r, _d = pane
    for key in ("presets", "lookback", "faces", "analyzer"):
        frame(r.panel, key)
        frame(r.panel, key)
        assert PAGE_KEYS[r.panel.page] == key
    assert Panel._page_presets is not Panel.presets_body
    frame(r.panel, "graph")
