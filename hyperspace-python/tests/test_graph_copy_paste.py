"""⌘C / ⌘V on the GRAPH canvas (ui_graph._copy_paste): an effect, or a copy
of one, is copied; paste adds a copy of that effect under it."""

from types import SimpleNamespace as NS

import pytest

from hyperspace import graph as rgraph
from hyperspace import ui_graph


def node(ref, nid="render:acid"):
    return NS(ref=ref, id=nid)


@pytest.fixture
def rig(monkeypatch):
    keys = {"c": False, "v": False}
    monkeypatch.setattr(ui_graph, "_chord",
                        lambda k: keys["c"] if k == ui_graph.imgui.Key.c else keys["v"])
    out = NS(keys=keys, added=[], selected=[], sel=None)
    monkeypatch.setattr(ui_graph, "_selection", lambda st, view: out.sel)
    monkeypatch.setattr(ui_graph, "node_below", lambda st, nid: (1.0, 2.0))
    monkeypatch.setattr(ui_graph, "render_edit", lambda panel: NS(added="copy"))

    def add(panel, e, kind, file, at):
        out.added.append((kind, file, at))
    monkeypatch.setattr(ui_graph, "add_render", add)
    monkeypatch.setattr(ui_graph, "select_node", lambda panel, name: out.selected.append(name))
    return out


def press(rig, key):
    rig.keys[key] = True
    st = {}
    ui_graph._copy_paste(None, st, None)
    rig.keys[key] = False
    return st


def test_copy_then_paste_adds_a_copy_of_the_effect_under_it_and_selects_it(rig):
    rig.sel = ("node", node(rgraph.Effect("acid", node="acid")))
    st = {}
    rig.keys["c"] = True
    ui_graph._copy_paste(None, st, None)
    rig.keys["c"] = False
    assert st["clip"]["of"] == "acid" and "acid copied" in st["said"]
    rig.keys["v"] = True
    ui_graph._copy_paste(None, st, None)
    assert rig.added == [("copy", "acid", (1.0, 2.0))]
    assert rig.selected == ["copy"] and st["clip"]["nid"] == "render:copy"


def test_a_copy_of_a_copy_copies_the_same_effect(rig):
    rig.sel = ("node", node(rgraph.Copy("copy", "acid"), "render:copy"))
    st = press(rig, "c")
    assert st["clip"]["of"] == "acid"


def test_copying_what_has_no_copies_says_so(rig):
    rig.sel = ("node", node(NS()))
    st = press(rig, "c")
    assert "clip" not in st and st["note"] == ui_graph.COPY_NOTHING


def test_paste_with_nothing_copied_says_so(rig):
    st = press(rig, "v")
    assert st["note"] == ui_graph.PASTE_NOTHING and rig.added == []
