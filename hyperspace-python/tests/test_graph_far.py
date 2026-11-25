"""GRAPH zoomed out: a node's words, its widgets and its unwired pins are
left out once they are too small to read, and off the canvas its title and
picture too — its size, its place and the pins of its cables are not
(`ui_graph._node_shown`)."""

import pytest
from imgui_bundle import imgui_node_editor as ed
from test_graph_legible import party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graphview, ui_graph

NEAR, FAR = 1.0, 5.0


@pytest.fixture()
def canvas(shell_rig, monkeypatch):  # noqa: F811
    """`draw(zoom)`: one frame as the canvas reads that zoom (the editor's
    own stays 1, so near and far are compared in the same canvas units),
    every node on the canvas; what it drew."""
    st = party(shell_rig)
    monkeypatch.setattr(ui_graph, "on_screen", lambda *a: True)
    said: list[str] = []
    real_button, real_text = ui_graph.ui.small_button, ui_graph.imgui.text_disabled
    monkeypatch.setattr(ui_graph.ui, "small_button",
                        lambda s: (said.append(s), real_button(s))[1])
    monkeypatch.setattr(ui_graph.imgui, "text_disabled",
                        lambda s: (said.append(s), real_text(s))[1])
    real_hot = ui_graph._hot_button      # (off hover a widget's words alone: #505)
    monkeypatch.setattr(ui_graph, "_hot_button",
                        lambda s, live: (live or said.append(s), real_hot(s, live))[1])
    real_moved = ui_graph._moved
    boxes: dict = {}

    def moved(panel, st_, view):
        for n in view.nodes:
            if ui_graph.drawn_node(st_, n):
                k = ed.NodeId(ui_graph._id(st_, "n:" + n.id))
                p, z = ed.get_node_position(k), ed.get_node_size(k)
                boxes[n.id] = (p.x, p.y, z.x, z.y)
        return real_moved(panel, st_, view)

    monkeypatch.setattr(ui_graph, "_moved", moved)

    def draw(zoom, frames=3):
        monkeypatch.setattr(ed, "get_current_zoom", lambda: zoom)
        for _ in range(frames):
            said.clear()
            boxes.clear()
            frame(shell_rig.panel, "graph")
        return dict(boxes), dict(st["pin_xy"]), st["wires"], list(said)

    return shell_rig, st, draw


@pytest.mark.parametrize("opened", [False, True])
@pytest.mark.parametrize("every", [False, True])
def test_zoomed_out_a_node_keeps_its_size_its_place_and_its_wired_pins(canvas, opened, every):
    _rig, st, draw = canvas
    st["patched_only"] = not every
    ui_graph.expand_all(st, st["view"], opened)
    near, pins, wires, said = draw(NEAR)
    far, far_pins, far_wires, far_said = draw(FAR)
    assert st["far"] and far == near and far_wires == wires > 0
    assert set(far_pins) <= set(pins)
    for pin, xy in far_pins.items():
        assert xy == pytest.approx(pins[pin]), pin
    # (pin by pin: a param with a route has a base and a depth pin no cable ends on)
    ends = {e for c in st["view"].cables for e in (c.src_port, c.dst_port)}
    unwired = {pin for n in st["view"].nodes for p in n.ports for pin in p.pins} - ends
    assert not unwired & set(far_pins)
    if opened and every:
        assert unwired & set(pins)
    assert "all ports" not in far_said and "patched only" not in far_said
    assert len(far_said) < len(said)
    assert draw(NEAR)[:3] == (near, pins, wires)        # and back


def test_an_error_s_title_and_a_mask_s_words_stay(canvas, monkeypatch):
    """Both however far out: a title too small to read is left out, not one
    that says its effect does not compile."""
    _rig, st, draw = canvas
    draw(NEAR)
    pic = next(n for n in st["view"].nodes if n.thumb is not None and ui_graph.drawn_node(st, n))
    asked: list[str] = []
    monkeypatch.setattr(graphview, "mask_words",
                        lambda n: (asked.append(n.id), "no mask here")[1])
    monkeypatch.setattr(ui_graph, "effect_errors", lambda *a: {pic.id: "line 3"})
    titles: list[str] = []
    real = ui_graph.ui.fit_text
    monkeypatch.setattr(ui_graph.ui, "fit_text", lambda s, w: (titles.append(s), real(s, w))[1])
    draw(100.0, frames=1)
    assert st["far"] and pic.label in titles and pic.id in asked
    assert "Analyzer" not in titles
    titles.clear()
    draw(FAR, frames=1)
    assert len(titles) > 1                              # at 5: every title


def test_expanded_far_out_a_node_is_its_ports_size_at_once(canvas):
    _rig, st, draw = canvas
    draw(NEAR)
    before, _, wires, _ = draw(FAR)
    ui_graph.expand_all(st, st["view"], True)
    far, _, more, _ = draw(FAR)
    near = draw(NEAR)[0]
    assert far == near != before and more > wires


def test_off_the_canvas_a_node_keeps_its_cables_and_draws_no_body(canvas, monkeypatch):
    _rig, st, draw = canvas
    ui_graph.expand_all(st, st["view"], True)
    near, pins, wires, _ = draw(NEAR)
    bodies: list[str] = []
    monkeypatch.setattr(ui_graph, "_thumb", lambda st_, n: bodies.append(n.id))
    monkeypatch.setattr(ui_graph, "on_screen", lambda *a: False)
    off, off_pins, off_wires, _ = draw(NEAR)
    assert off == near and off_wires == wires and not bodies
    assert off_pins and all(xy == pytest.approx(pins[p]) for p, xy in off_pins.items())


def test_the_threshold_holds_between_its_two_sides_and_while_a_button_is_down():
    text = 20.0
    out, back = text / ui_graph.FAR_PX, text / ui_graph.NEAR_PX
    between = (out + back) / 2
    assert back < between < out
    assert not ui_graph.is_far(False, between, text) and ui_graph.is_far(True, between, text)
    assert ui_graph.is_far(False, out * 1.01, text) and not ui_graph.is_far(True, back * 0.99, text)
    assert not ui_graph.is_far(False, out * 2, text, held=True)     # a drag keeps its pin
    assert ui_graph.is_far(True, 1.0, text, held=True)


def test_a_pin_drawn_far_is_the_same_pin_to_the_editor(canvas, monkeypatch):
    """Its hit rect and kind as they were, so a press and a drop land."""
    _rig, _st, draw = canvas
    rects: set = set()
    real = ed.pin_rect
    monkeypatch.setattr(ed, "pin_rect",
                        lambda a, b: (rects.add((a.x, a.y, b.x, b.y)), real(a, b))[1])
    monkeypatch.setattr(ui_graph, "pin_hit_size", lambda *a, **k: (12.0, 12.0))
    draw(NEAR)
    near = set(rects)
    rects.clear()
    draw(FAR)
    assert rects and rects <= near
