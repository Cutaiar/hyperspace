"""Plan 36 T5 (W5): a new preset that starts somewhere, and the picker's
starters.

**new** on the PRESET strip makes the scene chain — `shape →
scene.geometry`, `scene → output.all.image`, plain faces — laid left to
right in the preset's layout map where the GRAPH page is looking
(`ui_graph.in_view`). The picker's **starters ▸** each add a pre-wired
group (`graphview.STARTERS`) in one undo step, its new nodes laid left to
right from where the menu opened; a picture cable's menu has the tracers
and dream ones, on its picture. A starter whose picture is not one thing
wires what it can and says what is left unwired."""

from __future__ import annotations

import pytest
from conftest import seed
from test_graph_edit import wired_rig, wired_wires
from test_ui_shell import _click, frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graphview, preset, ui_graph, ui_presets, undo
from hyperspace.library import Marks

ALL = "output.all.image"
CHAIN = {("shape", "scene.geometry"), ("scene", ALL)}
SCENE = {"frame": "wired", "wires": [{"from": "shape", "to": "scene.geometry"},
                                     {"from": "scene", "to": ALL}]}


@pytest.fixture()
def page(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)         # (the corpus: the presets the tests load by slug)
    return shell_rig


def _entries(rig) -> list[dict]:
    """The section's node entries, less the hands entry every frame writes."""
    return [e for e in rig.presets.graph.spec.to_json().get("nodes", [])
            if e.get("kind") != "hands"]


# ---------------------------------------------------------------- new

def test_new_is_the_scene_chain_laid_out_where_you_look(tmp_path):
    """New: the section is the scene chain alone and the layout map holds
    its three nodes, left to right on one row from `at`."""
    rig, _, _ = wired_rig(tmp_path, {"frame": "wired",
                                     "wires": [{"from": "channel.b", "to": ALL}]})
    assert rig.presets.new((120.0, -40.0)) == [preset.NEW_SAID]
    spec = rig.presets.graph.spec
    assert wired_wires(rig) == CHAIN and len(spec.wires) == 2
    assert _entries(rig) == []                          # no pattern, nothing else
    lay = rig.presets.layout
    assert lay == {"render:shape": [120, -40],
                   "render:scene": [120 + graphview.COL_W, -40],
                   "render:output.all": [120 + 2 * graphview.COL_W, -40]}
    doc = rig.presets.document(preset.UNTITLED_PRESET)
    assert doc["layout"] == lay
    assert doc["graph"] == spec.to_json()


def test_new_undoes_its_section_and_layout_in_one_step(tmp_path):
    rig, _, _ = wired_rig(tmp_path, SCENE)
    u = undo.Undo(rig.reg, rig.router.table, marks=Marks(rig.lib))
    undo.install(u)
    try:
        rig.presets.layout = {"render:scene": [5, 5]}
        u.tick(1.0)
        u.tick(2.0)
        was = rig.presets.graph.spec.to_json()
        rig.presets.new((0.0, 0.0))
        assert u.stack[-1].label == "new preset"
        assert len(rig.presets.layout) == 3
        assert u.undo()
    finally:
        undo.install(None)
    assert rig.presets.graph.spec.to_json() == was
    assert rig.presets.layout == {"render:scene": [5, 5]}


def test_new_from_the_strip_lays_out_at_the_page_s_view(page):
    """The strip's new passes `ui_graph.in_view`: the canvas point at the
    view's corner (`st["seen"]`, which the page records as it draws), in
    by the margin, less the pan."""
    panel = page.panel
    frame(panel, "graph")
    st = ui_graph._state(panel)
    assert isinstance(st["seen"], tuple)
    st["seen"], st["pan"] = (300.0, 200.0), (50.0, -10.0)
    at = ui_graph.in_view(panel)
    assert at == (300 + ui_graph.IN_VIEW_MARGIN[0] - 50, 200 + ui_graph.IN_VIEW_MARGIN[1] + 10)
    frame(panel, "presets")
    st["seen"] = (300.0, 200.0)             # (as the GRAPH page last saw it)
    frame(panel)
    _click(panel, ui_presets._state(panel)["rects"]["strip.presets.new"])
    assert page.lib.current("presets") == preset.UNTITLED_PRESET
    assert page.lib.presets.layout["render:shape"] == list(at)
    assert wired_wires(page.lib) == CHAIN


# ---------------------------------------------------------------- the starters

def test_the_starters_are_their_own_submenu_first():
    assert graphview.PICKER_GROUP["starter"] == "starters"
    assert graphview.PICKER_GROUPS[0] == "starters"
    assert [w for _, w in graphview.STARTERS] == [
        "scene chain", "tracers", "tracers + dream", "dream on a picture",
        "channel to backdrop", "cut-out"]               # (plan 39 T5: the cut-out)


def test_scene_chain_on_a_blank_preset(tmp_path):
    rig, e, pushed = wired_rig(tmp_path, {"frame": "wired"})
    assert e.add_node("starter", "scene") is None
    assert wired_wires(rig) == CHAIN and _entries(rig) == []
    assert pushed == ["starter: scene chain"]
    assert e.placed == ("shape", "scene")               # (All outputs stays where it sits)
    assert e.said == graphview.STARTER_SAID


TRACED = CHAIN - {("scene", ALL)} | {
    ("scene", "lookback.image"), ("scene", "lookback.occluder"),
    ("scene", "composite.under"), ("lookback", "composite.over"), ("composite", ALL)}


def test_tracers_lay_the_trail_on_the_scene_where_it_went(tmp_path):
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("tracers") is None
    assert wired_wires(rig) == TRACED
    assert {"kind": "composite", "blend": "add"} in _entries(rig)
    assert pushed == ["starter: tracers"] and e.placed == ("lookback", "composite")
    assert "left unwired" not in e.said


def test_tracers_and_dream(tmp_path):
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("tracers+dream") is None
    assert wired_wires(rig) == TRACED - {("lookback", "composite.over")} | {
        ("lookback", "dream.image"), ("dream", "composite.over")}
    assert pushed == ["starter: tracers + dream"]
    assert e.placed == ("lookback", "dream", "composite")


def test_dream_on_a_picture(tmp_path):
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("dream") is None
    assert wired_wires(rig) == CHAIN - {("scene", ALL)} | {
        ("scene", "dream.image"), ("scene", "composite.under"),
        ("dream", "composite.over"), ("composite", ALL)}
    assert {"kind": "composite"} in _entries(rig)         # (blend over)
    assert pushed == ["starter: dream on a picture"] and e.placed == ("dream", "composite")


def test_channel_to_backdrop(tmp_path):
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("backdrop") is None
    assert wired_wires(rig) == CHAIN | {("channel.a", "backdrop.image")}
    assert pushed == ["starter: channel to backdrop"] and e.placed == ("backdrop",)
    assert "left unwired: backdrop.scene" in e.said


def test_tracers_on_a_cable_take_its_picture(tmp_path):
    """From a picture cable's menu: its source is the picture, the
    composite goes where the cable went."""
    section = {"frame": "wired", "wires": [*SCENE["wires"][:1],
                                           {"from": "scene", "to": "acid.image"},
                                           {"from": "acid", "to": ALL}]}
    rig, e, pushed = wired_rig(tmp_path, section)
    assert e.starter("tracers", ("acid", ALL)) is None
    assert wired_wires(rig) == {
        ("shape", "scene.geometry"), ("scene", "acid.image"),
        ("acid", "lookback.image"), ("acid", "lookback.occluder"),
        ("acid", "composite.under"), ("lookback", "composite.over"), ("composite", ALL)}
    assert pushed == ["starter: tracers"]


def test_no_scene_wires_what_it_can_and_says_the_rest(tmp_path):
    rig, e, pushed = wired_rig(tmp_path, {"frame": "wired"})
    assert e.starter("tracers") is None
    assert wired_wires(rig) == {("lookback", "composite.over")}
    assert "left unwired: lookback.image, lookback.occluder, composite.under" in e.said
    assert "the composite's picture" in e.said
    assert e.placed == ("lookback", "composite") and len(pushed) == 1


def test_a_scene_feeding_two_ports_leaves_the_composite_unwired(tmp_path):
    section = {"frame": "wired", "wires": [*SCENE["wires"],
                                           {"from": "scene", "to": "output.2.image"}]}
    rig, e, _ = wired_rig(tmp_path, section)
    assert e.starter("dream") is None
    got = wired_wires(rig)
    assert ("scene", ALL) in got and ("scene", "output.2.image") in got
    assert not [w for w in got if w[0] == "composite"]
    assert "left unwired: the composite's picture (the scene feeds 2 ports)" in e.said


@pytest.mark.parametrize("which,section", [
    ("tracers", {"frame": "wired", "nodes": [{"kind": "lookback"}]}),
    ("dream", {"frame": "wired", "nodes": [{"kind": "dream"}]}),
    ("backdrop", {"frame": "wired", "nodes": [{"kind": "backdrop"}]}),
])
def test_one_of_each_is_refused_in_words(tmp_path, which, section):
    rig, e, pushed = wired_rig(tmp_path, section)
    was = rig.presets.graph.spec.to_json()
    why = e.starter(which)
    assert why is not None and "in the graph already" in why
    assert pushed == [] and rig.presets.graph.spec.to_json() == was and e.placed == ()


def test_a_cable_starter_is_only_a_picture_one(tmp_path):
    _, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("scene", ("scene", ALL)) == graphview.NO_CABLE_STARTER.format(
        label="scene chain")
    assert e.starter("nope") is not None and pushed == []


# ---------------------------------------------------------------- the page

def test_a_starter_lands_at_the_point_as_one_undo_step(page):
    """From the picker on the panned canvas: the new nodes left to right
    from the menu's point, in the preset's layout (canvas units less the
    pan), and one ⌘Z takes the wires and the places back."""
    lib = page.lib
    lib.presets.new((0.0, 0.0))
    u = undo.Undo(page.reg, page.router.table, marks=Marks(lib))
    undo.install(u)
    try:
        u.tick(1.0)
        u.tick(2.0)
        was = (lib.presets.graph.spec.to_json(), dict(lib.presets.layout))
        ui_graph._state(page.panel)["pan"] = (100.0, -50.0)
        e = ui_graph.render_edit(page.panel)
        assert ui_graph.add_render(page.panel, e, "starter", "tracers", (400.0, 300.0)) is None
        lay = lib.presets.layout
        assert lay["render:lookback"] == [300, 350]
        assert lay["render:composite"] == [300 + graphview.COL_W, 350]
        assert len(lay) == len(was[1]) + 2              # nothing else placed or moved
        assert u.stack[-1].label == "starter: tracers"
        assert u.undo()
    finally:
        undo.install(None)
    assert (lib.presets.graph.spec.to_json(), dict(lib.presets.layout)) == was
