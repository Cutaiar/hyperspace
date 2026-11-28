"""GRAPH's node widgets (+ / -, **all ports**, the groups' folds) are drawn as
widgets only on a node that is hovered, selected, being pressed, or while the
keys or a pad move the focus (`ui_graph.hot`); off it their words alone, where
they say something, and the node the same size."""

from __future__ import annotations

import pytest
from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed
from test_graph_legible import party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture
from ui_driver import Driver

from hyperspace import ui_graph


class Canvas:
    """The page driven by the mouse: each frame's node boxes (screen px, and
    size in canvas units), and who drew which buttons (node id → labels)."""

    def __init__(self, rig, st, monkeypatch):
        self.panel, self.st = rig.panel, st
        self.box: dict[str, tuple] = {}
        self.size: dict[str, tuple] = {}
        self.buttons: dict[str, list[str]] = {}
        self.at: dict[tuple[str, str], tuple[float, float]] = {}    # a button's middle, screen px
        self.text: dict[str, list[str]] = {}
        self.now = None
        node, small, moved = ui_graph._node, ui_graph.ui.small_button, ui_graph._moved
        words = ui_graph._hot_button

        def in_node(st_, n, drawn):
            self.now = n.id
            self.buttons[n.id], self.text[n.id] = [], []
            node(st_, n, drawn)
            self.now = None

        def button(label):
            hit = small(label)
            if self.now is not None:
                self.buttons[self.now].append(label)
                a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
                p = ed.canvas_to_screen(imgui.ImVec2((a.x + b.x) / 2, (a.y + b.y) / 2))
                self.at[self.now, label] = (p.x, p.y)
            return hit

        def said(label, live):
            self.text[self.now].append(label)
            return words(label, live)

        def after(panel, st_, view):
            for n in view.nodes:
                if n.id not in self.buttons:
                    continue
                k = ed.NodeId(ui_graph._id(st_, "n:" + n.id))
                p, z = ed.get_node_position(k), ed.get_node_size(k)
                a = ed.canvas_to_screen(p)
                b = ed.canvas_to_screen(imgui.ImVec2(p.x + z.x, p.y + z.y))
                self.box[n.id], self.size[n.id] = (a.x, a.y, b.x, b.y), (z.x, z.y)
            return moved(panel, st_, view)

        monkeypatch.setattr(ui_graph, "_node", in_node)
        monkeypatch.setattr(ui_graph.ui, "small_button", button)
        monkeypatch.setattr(ui_graph, "_hot_button", said)
        monkeypatch.setattr(ui_graph, "_moved", after)
        self.d = Driver(step=lambda: frame(self.panel, "graph"))
        self.d.record(monkeypatch.setattr)
        self.d.run(self.d.park(), self.d.wait(3))

    def clear(self) -> str:
        """A node whole in the window, off the pane, under no other node."""
        left = self.st["details_rect"][0][0] if self.st.get("details_rect") else 1e9
        size = imgui.get_io().display_size
        pad = 24
        for nid, (x0, y0, x1, y1) in self.box.items():
            if not (pad < x0 and x1 < min(left, size.x) - pad and 140 < y0 and y1 < size.y - 60):
                continue
            if all(o == nid or x1 + pad < a or c + pad < x0 or y1 + pad < b or e + pad < y0
                   for o, (a, b, c, e) in self.box.items()):
                return nid
        raise AssertionError(f"no node in the clear: {self.box}")

    def over(self, nid: str):
        x0, y0, x1, y1 = self.box[nid]
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    def select(self, nid: str | None) -> None:
        ed.set_current_editor(self.st["editor"])
        ed.clear_selection()
        if nid is not None:
            ed.select_node(ed.NodeId(ui_graph._id(self.st, "n:" + nid)))
        self.d.run(self.d.wait(3))

    def live(self) -> set[str]:
        return {nid for nid, b in self.buttons.items() if b}


@pytest.fixture()
def canvas(shell_rig, monkeypatch):  # noqa: F811
    st = party(shell_rig)
    shell_rig.panel.desk = False
    shell_rig.panel.graph_fit = True
    imgui.get_io().config_flags &= ~imgui.ConfigFlags_.nav_enable_keyboard
    return Canvas(shell_rig, st, monkeypatch)


def test_no_node_draws_a_widget_until_the_pointer_is_on_it(canvas):
    c, d = canvas, canvas.d
    assert len(c.box) > 5 and c.live() == set()
    nid = c.clear()
    held = dict(c.size)
    d.run(d.move(c.over(nid)))
    assert c.live() == {nid} and c.buttons[nid] == ["+"]
    assert "+" in d.rects                           # and the driver finds it by its label
    d.run(d.wait(2))
    assert c.size == held                           # nothing moved or grew
    d.run(d.park())
    assert c.live() == set()


def test_a_press_the_frame_the_pointer_arrives_works_and_the_open_node_says_it_is_open(canvas):
    c, d = canvas, canvas.d
    nid = c.clear()
    d.run(d.move(c.over(nid)))
    plus = c.at[nid, "+"]
    d.run(d.park(), d.wait(2))
    assert c.live() == set()
    imgui.get_io().config_input_trickle_event_queue = False     # the move and the press in one frame
    d.mouse = plus
    imgui.get_io().add_mouse_pos_event(*plus)
    d.run(d.press(True))
    d.run(d.press(False))
    imgui.get_io().config_input_trickle_event_queue = True
    assert ui_graph.is_open(c.st, nid)
    d.run(d.wait(2))
    d.run(d.park())
    c.select(None)
    assert not c.buttons[nid] and c.text[nid][0] == "-"     # its words, no widget


def test_an_open_nodes_folds_are_words_until_it_is_live_and_take_the_same_room(canvas):
    c, d = canvas, canvas.d
    many = next(n for n in c.st["view"].nodes
                if n.id in c.box and len({p.group for p in n.ports}) > 1)
    ui_graph.toggle_open(c.st, many.id)
    c.st["flip"] ^= {many.id}
    d.run(d.wait(3))
    said, size = list(c.text[many.id]), c.size[many.id]
    assert c.buttons[many.id] == [] and said[:2] == ["-", "patched only"] and len(said) > 2
    c.select(many.id)                               # the pointer away
    assert c.buttons[many.id] == said and c.size[many.id] == size
    c.select(None)
    assert c.buttons[many.id] == []


def test_a_press_keeps_its_button_while_the_pointer_wanders(canvas):
    c, d = canvas, canvas.d
    nid = c.clear()
    d.run(d.move(c.over(nid)))
    plus = c.at[nid, "+"]
    d.run(d.move(plus), d.press(True), d.move((plus[0], c.box[nid][3] + 60)))
    assert nid in c.live()
    d.run(d.move(plus), d.press(False))
    assert ui_graph.is_open(c.st, nid)


def test_the_keys_bring_every_nodes_widgets(canvas):
    c, d = canvas, canvas.d
    d.run(d.key(imgui.Key.down_arrow), d.wait(2))   # the keys move the focus: a ring is shown
    assert imgui.get_io().nav_visible
    assert c.live() == set(c.buttons)
    imgui.get_io().config_flags &= ~imgui.ConfigFlags_.nav_enable_keyboard
    d.run(d.move((300.0, 300.0)), d.move((310.0, 300.0)), d.park(), d.wait(2))
    assert c.live() == set()                        # the mouse has it again


def test_a_first_frame_with_the_button_held_draws(shell_rig, monkeypatch):  # noqa: F811
    """The page's state outlives a hot reload, so the first frame that asks
    `hot` may come with no `hot_held` and the mouse down; that must not raise."""
    st = party(shell_rig)
    for k in [k for k in st if k.startswith("hot_")]:
        del st[k]
    monkeypatch.setattr(ui_graph.imgui, "is_mouse_down", lambda *a: True)
    frame(shell_rig.panel, "graph")
    assert st["hot_held"] == set()
