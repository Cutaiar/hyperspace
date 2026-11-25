"""GRAPH's slim head (2026-11-24): the deck row, then one row of the canvas's
own with the areas and the canvas's toggles in two menus."""

from __future__ import annotations

import pytest
from imgui_bundle import imgui
from test_save_live import _graph
from test_ui_shell import build_rig, frame, head_menu
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import devices, graphview, ui, ui_graph

IN_CANVAS = ("expand all##graph", "patched only##graph", "patch only##graph",
             "output behind##graph", ui_graph.TINT_LABEL, ui_graph.COST_LABEL)


def _all_drawn(monkeypatch) -> list[str]:
    seen: list[str] = []
    for name in ("chip", "lit_chip"):
        real = getattr(ui, name)
        monkeypatch.setattr(ui, name, lambda label, *a, _r=real, **k:
                            seen.append(label) or _r(label, *a, **k))
    return seen


def test_a_closed_menu_builds_nothing(shell_rig, monkeypatch):  # noqa: F811
    seen = _all_drawn(monkeypatch)
    frame(shell_rig.panel, "graph")
    assert ui_graph.AREAS_LABEL in seen
    assert any(x.endswith("##graph.canvas") for x in seen)
    assert not set(seen) & set(IN_CANVAS)
    assert not [x for x in seen if x.endswith("##area")]


def test_every_verb_is_in_a_menu_under_its_own_id(shell_rig, monkeypatch):  # noqa: F811
    seen = _all_drawn(monkeypatch)
    head_menu(shell_rig.panel)
    seen.clear()
    frame(shell_rig.panel, "graph")
    assert set(IN_CANVAS) <= set(seen)


def test_the_chip_says_what_is_on_without_opening(shell_rig):  # noqa: F811
    frame(shell_rig.panel, "graph")
    st = ui_graph._state(shell_rig.panel)
    for k, _ in ui_graph.CANVAS_TOGGLES:
        st[k] = False
    assert ui_graph.canvas_words(st) == "canvas"
    for k, words in ui_graph.CANVAS_TOGGLES:
        st[k] = True
        assert ui_graph.canvas_words(st) == f"canvas: {words}"
        st[k] = False


@pytest.mark.parametrize("mark", ["tint", "cost"])
def test_a_mark_lights_the_chip(shell_rig, monkeypatch, mark):  # noqa: F811
    frame(shell_rig.panel, "graph")
    st = ui_graph._state(shell_rig.panel)
    lit: dict[str, bool] = {}
    real = ui.lit_chip
    monkeypatch.setattr(ui, "lit_chip", lambda label, on, *a, **k:
                        lit.__setitem__(label.split("##")[-1], on) or real(label, on, *a, **k))
    frame(shell_rig.panel, "graph")
    assert lit["graph.canvas"] is False
    st[mark] = True
    frame(shell_rig.panel, "graph")
    assert lit["graph.canvas"] is True


def test_the_mouse_toggles_and_jumps_in_two_clicks(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        d = _graph(r, monkeypatch)
        d.run(d.wait(2))
        st = ui_graph._state(r.panel)
        top, was = d.rects["graph.canvas"], st["patch_only"]
        d.run(d.click("graph.canvas", frames=2), d.wait(2))
        assert d.rects["patch only##graph"][1] > top[3]          # under its chip
        d.run(d.click("patch only##graph", frames=2))
        assert st["patch_only"] is not was
        d.run(d.click(ui_graph.COST_LABEL, frames=2))            # still open
        assert st["cost"] is True
        d.run(d.key(imgui.Key.escape), d.wait(2))
        assert ui_graph.COST_LABEL not in d.rects

        asked = []
        monkeypatch.setattr(ui_graph, "frame_area",
                            lambda st_, view, area: asked.append(area) or [])
        d.run(d.click("graph.areas", frames=2), d.wait(2))
        label = f"{graphview.TITLES[graphview.SCENE_AREA]}##area"
        d.run(d.click(label, frames=2), d.wait(2))
        assert asked == [graphview.SCENE_AREA]
        assert label not in d.rects                              # and it shut


@pytest.mark.parametrize("width", [1600, 820, 540, 480])
def test_every_head_chip_is_inside_the_page(tmp_path, monkeypatch, width):
    """With every mark lit and a device missing, whatever the width: the row
    this replaced ran its last chips past a narrow page's edge."""
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(width, 820)
        monkeypatch.setattr(devices, "missing_chip", lambda ws: "2 devices missing")
        rects: dict[str, tuple[float, float, float]] = {}
        for name in ("chip", "lit_chip"):
            real = getattr(ui, name)

            def spy(label, *a, _r=real, **k):
                hit = _r(label, *a, **k)
                rects[label] = (imgui.get_item_rect_min().x, imgui.get_item_rect_max().x,
                                imgui.internal.get_current_window().clip_rect.max.x)
                return hit
            monkeypatch.setattr(ui, name, spy)
        frame(r.panel, "graph")
        st = ui_graph._state(r.panel)
        for key, _ in ui_graph.CANVAS_TOGGLES:          # every word the chip can say
            st[key] = True
        frame(r.panel, "graph")
        rects.clear()
        frame(r.panel, "graph")
        head = {k: v for k, v in rects.items()
                if k.endswith(("##graph", "##graph.areas", "##graph.canvas", "##wants"))}
        assert {"2 devices missing##wants", ui_graph.AREAS_LABEL, ui_graph.TIDY_CHIP,
                } <= set(head)
        said = [k.split("##")[0] for k in head if k.endswith("##graph.canvas")]
        full = ui_graph.canvas_words(st)
        assert said in ([full], [f"canvas: {len(ui_graph.CANVAS_TOGGLES)} on"])
        assert said == [full] or width < 820          # shortened only where it must be
        for k, (x0, x1, right) in head.items():
            assert 0 <= x0 and x1 <= right, (k, x0, x1, right)


NOTES = ["no", ("a refusal long enough that no row of a narrow page could ever hold it beside "
         "the chips that are there already, whole, to its last word, on a page of 1600 px or "
         "one of 540 px, however many devices are missing from the patch: it wraps")]


@pytest.mark.parametrize("width", [1600, 540])
@pytest.mark.parametrize("note", NOTES)
def test_a_warning_is_drawn_whole_inside_the_page(tmp_path, monkeypatch, width, note):
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(width, 820)
        frame(r.panel, "graph")
        st = ui_graph._state(r.panel)
        seen: list[tuple[float, float]] = []
        real = imgui.text_colored

        def spy(col, text):
            real(col, text)
            if text == note:
                seen.append((imgui.get_item_rect_min().x, imgui.get_item_rect_max().x))
        monkeypatch.setattr(ui_graph.imgui, "text_colored", spy)
        st["note"] = note
        frame(r.panel, "graph")
        assert seen and all(0 <= a and b <= width for a, b in seen), seen


@pytest.mark.parametrize("width", [1600, 820, 540])
def test_a_message_moves_no_node(tmp_path, width):
    """The canvas starts where it did, whatever the width."""
    with build_rig(tmp_path) as r:
        imgui.get_io().display_size = imgui.ImVec2(width, 900)
        frame(r.panel, "graph")
        frame(r.panel, "graph")
        st = ui_graph._state(r.panel)
        y = r.panel.canvas_px[0][1]
        for key in ("note", "said"):
            st[key] = "cables: 2 cut"
            frame(r.panel, "graph")
            assert r.panel.canvas_px[0][1] == y, key
            st[key] = ""
