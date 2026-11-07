"""WORDS (#407) renamed three strings that were never saved: `graphview.META_SECTION` from
"session", `patches.CONTROL` from "rig", a cloud cable's id prefix from "rig:". Review asked
whether any of them reaches a file, since a saved position or a cut lost to a rename would be
a format change. None does; these hold that.

The rest of the road, by reading: a cable's id goes through `ui_graph._id` to an int the
node editor holds for this run, its settings file is off (the test below), selection and
hover are those ints, and `imgui.ini` holds windows and tables, none named by a cable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import seed
from test_patches import example
from test_ui_shell import frame, rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as rgraph
from hyperspace import graphview, patches, ui_graph
from hyperspace.library import INSTALL_SCHEMA

CORPUS = Path(__file__).parent / "corpus"
OLD_CABLE, NEW_CABLE = "rig:", "cloud:"


def _strings(value):
    """Every key and string in a JSON document."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _view(rig):  # noqa: F811
    return graphview.build(rig.router.table, rig.reg, rig.router, None, None, None)


def test_a_meta_nodes_position_saved_in_a_show_lands_where_it_was(rig):  # noqa: F811
    view = _view(rig)
    node = view.node(graphview.ANALYZER)
    assert graphview.home(node) == graphview.META_SECTION
    pre, show = graphview.split(view, {node.id: (123, 456)})
    assert pre == {} and show == {node.id: [123, 456]}

    project = rig.lib.project
    project.layout.update(show)
    path = project.save("words position")
    doc = json.loads(path.read_text())
    assert doc["layout"][node.id] == [123, 456]

    project.layout.clear()
    project.load("words position")
    assert project.layout[node.id] == [123, 456]

    # no key changed: the show's own keys as they were, and the section's word in none
    assert doc["schema"] == INSTALL_SCHEMA and "tuning" in doc and "layout" in doc
    assert not {graphview.META_SECTION, graphview.PATCH_SECTION} & set(doc)
    assert graphview.META_SECTION not in set(doc["layout"])


def test_the_sections_word_changes_no_byte_of_a_saved_show(rig, monkeypatch):  # noqa: F811
    view = _view(rig)
    node = view.node(graphview.ANALYZER)
    project = rig.lib.project

    def saved() -> dict:
        _pre, show = graphview.split(view, {node.id: (7, 8)})
        project.layout.update(show)
        return json.loads(project.save("words bytes").read_text())

    now = saved()
    monkeypatch.setattr(graphview, "META_SECTION", "session")   # the word it was
    assert saved() == now


def test_a_patch_reads_the_same_whatever_controls_word_is(monkeypatch):
    """`side`'s answer is only compared; `control_rows` are the file's rows, verbatim."""
    doc = example()
    now = patches.read(doc)
    assert now.control_rows == (doc["routes"][1], doc["desk"][0])
    assert patches.CONTROL not in set(_strings(doc))
    monkeypatch.setattr(patches, "CONTROL", "rig")              # the word it was
    assert patches.read(doc) == now


def test_a_cloud_wires_cut_is_saved_by_its_ends_never_by_a_cable_id():
    cut = rgraph.BusCuts().cutting(rgraph.cloud_wire(0)).to_json()
    assert cut == {"cut": [{"from": "cloud", "to": "scene.geometry"}]}


def test_a_saved_show_holds_no_cable_id(rig):  # noqa: F811
    project = rig.lib.project
    doc = json.loads(project.save("words cables").read_text())
    said = list(_strings(doc))
    assert not [s for s in said if s.startswith((OLD_CABLE, NEW_CABLE))]


def test_no_corpus_file_holds_a_cable_id_with_either_prefix():
    files = sorted(CORPUS.rglob("*.json"))
    assert files
    held = [(f.name, s) for f in files for s in _strings(json.loads(f.read_text()))
            if s.startswith((OLD_CABLE, NEW_CABLE))]
    assert not held


@pytest.mark.parametrize("zoom", [1.0, 1.6])
def test_the_node_editor_keeps_no_settings_file(rig, monkeypatch, tmp_path, zoom):  # noqa: F811
    """So no cable or node id lands in a NodeEditor.json beside the app. Through
    real frames with nodes moved, which is what makes the editor want to save:
    it writes nothing anywhere, it holds no file from its first `begin` on, and
    the one file a start zoom reads holds a view alone and is gone after."""
    spare, here = tmp_path / "spare", tmp_path / "here"
    spare.mkdir()
    here.mkdir()
    monkeypatch.setattr(ui_graph.tempfile, "tempdir", str(spare))
    monkeypatch.chdir(here)         # a relative NodeEditor.json would land here
    read, held = [], []

    def begin(*a, _begin=ui_graph.ed.begin):
        got = _begin(*a)
        path = ui_graph.ed.get_config(ui_graph._state(rig.panel)["editor"]).settings_file
        if path:                    # the start view, as this very `begin` read it
            read.append(json.loads(Path(path).read_text()))
        return got

    def end(*a, _end=ui_graph.ed.end):     # what the editor could save into, as it would
        held.append(ui_graph.ed.get_config(ui_graph._state(rig.panel)["editor"]).settings_file)
        return _end(*a)
    monkeypatch.setattr(ui_graph.ed, "begin", begin)
    monkeypatch.setattr(ui_graph.ed, "end", end)

    rig.panel.graph_start_zoom = zoom
    seed(rig.lib.home)
    rig.lib.load("loadable", "party-trip")
    for _ in range(3):
        frame(rig.panel, "graph")
    st = ui_graph._state(rig.panel)
    view = st["view"]
    for _ in range(3):              # every drawn node moved: the settings dirty
        for n in view.nodes:
            if ui_graph.drawn_node(st, n):
                st["applied"].pop(n.id, None)
        st["pan"] = (st["pan"][0] + 40.0, st["pan"][1] + 40.0)
        frame(rig.panel, "graph")
    ui_graph.close(rig.panel)       # (the editor's last chance to save)

    assert list(spare.iterdir()) == [] and list(here.iterdir()) == []
    assert held and set(held) == {""}
    if zoom == 1.0:
        assert read == []
    else:
        assert read == [{"nodes": {}, "selection": None,
                         "view": {"scroll": {"x": 0, "y": 0}, "zoom": zoom,
                                  "visible_rect": {"min": {"x": 0, "y": 0}, "max": {"x": 0, "y": 0}}}}]
