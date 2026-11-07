"""Plan 36 T5 (W5): a new loadable patch that starts somewhere, and the picker's
starters.

**new** on the PRESET strip makes the scene chain — `shape →
scene.geometry`, `scene → output.all.image`, plain faces — laid left to
right in the loadable patch's layout map where the GRAPH page is looking
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

from hyperspace import graphview, loadable, ui_graph, ui_loadable, undo
from hyperspace.library import Marks

ALL = "output.all.image"
CHAIN = {("shape", "scene.geometry"), ("scene", ALL)}
SCENE = {"frame": "wired", "wires": [{"from": "shape", "to": "scene.geometry"},
                                     {"from": "scene", "to": ALL}]}


@pytest.fixture()
def page(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)         # (the corpus: the loadable patches the tests load by slug)
    return shell_rig


def _entries(rig) -> list[dict]:
    """The section's node entries, less the hands entry every frame writes."""
    return [e for e in rig.loaded_patch.graph.spec.to_json().get("nodes", [])
            if e.get("kind") != "hands"]


# ---------------------------------------------------------------- new

def test_new_is_the_scene_chain_laid_out_where_you_look(tmp_path):
    """New: the section is the scene chain alone and the layout map holds
    its three nodes, left to right on one row from `at`."""
    rig, _, _ = wired_rig(tmp_path, {"frame": "wired",
                                     "wires": [{"from": "channel.b", "to": ALL}]})
    assert rig.loaded_patch.new((120.0, -40.0)) == [loadable.NEW_SAID]
    spec = rig.loaded_patch.graph.spec
    assert wired_wires(rig) == CHAIN and len(spec.wires) == 2
    assert _entries(rig) == []                          # no pattern, nothing else
    lay = rig.loaded_patch.layout
    assert lay == {"render:shape": [120, -40],
                   "render:scene": [120 + graphview.COL_W, -40],
                   "render:output.all": [120 + 2 * graphview.COL_W, -40]}
    doc = rig.loaded_patch.document(loadable.UNTITLED_PATCH)
    assert doc["layout"] == lay
    assert doc["graph"] == spec.to_json()


def test_new_undoes_its_section_and_layout_in_one_step(tmp_path):
    rig, _, _ = wired_rig(tmp_path, SCENE)
    u = undo.Undo(rig.reg, rig.router.table, marks=Marks(rig.lib))
    undo.install(u)
    try:
        rig.loaded_patch.layout = {"render:scene": [5, 5]}
        u.tick(1.0)
        u.tick(2.0)
        was = rig.loaded_patch.graph.spec.to_json()
        rig.loaded_patch.new((0.0, 0.0))
        assert u.stack[-1].label == "new preset"
        assert len(rig.loaded_patch.layout) == 3
        assert u.undo()
    finally:
        undo.install(None)
    assert rig.loaded_patch.graph.spec.to_json() == was
    assert rig.loaded_patch.layout == {"render:scene": [5, 5]}


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
    frame(panel, "loadable")
    frame(panel)
    at = ui_graph.in_view(panel)            # (GRAPH is always drawn: as it sees it now)
    _click(panel, ui_loadable._state(panel)["rects"]["strip.loadable.new"])
    assert page.lib.current("loadable") == loadable.UNTITLED_PATCH
    assert page.lib.loaded_patch.layout["render:shape"] == list(at)
    assert wired_wires(page.lib) == CHAIN


# ---------------------------------------------------------------- the starters

def test_the_starters_are_their_own_submenu_first():
    assert graphview.PICKER_GROUP["starter"] == "starters"
    assert graphview.PICKER_GROUPS[0] == "starters"
    assert [w for _, w in graphview.STARTERS] == [
        "scene chain", "tracers", "tracers + dream", "dream on a picture",
        "feedback",                                     # (wave 0 E1: the delay loop)
        "channel to backdrop", "cut-out"]               # (plan 39 T5: the cut-out)


def test_scene_chain_on_a_blank_loadable(tmp_path):
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
    was = rig.loaded_patch.graph.spec.to_json()
    why = e.starter(which)
    assert why is not None and "in the graph already" in why
    assert pushed == [] and rig.loaded_patch.graph.spec.to_json() == was and e.placed == ()


def test_a_cable_starter_is_only_a_picture_one(tmp_path):
    _, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("scene", ("scene", ALL)) == graphview.NO_CABLE_STARTER.format(
        label="scene chain")
    assert e.starter("nope") is not None and pushed == []


# ---------------------------------------------------------------- the page

def test_a_starter_lands_at_the_point_as_one_undo_step(page):
    """From the picker on the panned canvas: the new nodes left to right
    from the menu's point, in the loadable patch's layout (canvas units less the
    pan), and one ⌘Z takes the wires and the places back."""
    lib = page.lib
    lib.loaded_patch.new((0.0, 0.0))
    u = undo.Undo(page.reg, page.router.table, marks=Marks(lib))
    undo.install(u)
    try:
        u.tick(1.0)
        u.tick(2.0)
        was = (lib.loaded_patch.graph.spec.to_json(), dict(lib.loaded_patch.layout))
        ui_graph._state(page.panel)["pan"] = (100.0, -50.0)
        e = ui_graph.render_edit(page.panel)
        assert ui_graph.add_render(page.panel, e, "starter", "tracers", (400.0, 300.0)) is None
        lay = lib.loaded_patch.layout
        assert lay["render:lookback"] == [300, 350]
        assert lay["render:composite"] == [300 + graphview.COL_W, 350]
        assert len(lay) == len(was[1]) + 2              # nothing else placed or moved
        assert u.stack[-1].label == "starter: tracers"
        assert u.undo()
    finally:
        undo.install(None)
    assert (lib.loaded_patch.graph.spec.to_json(), dict(lib.loaded_patch.layout)) == was


# ---------------------------------------------------------------- feedback (wave 0 E1, 2026-11-02)
#
# A delay loop with a blend, spliced onto a picture cable by the insert
# table: `picture → composite.over`, `composite → dst`, `composite →
# delay.image`, `delay → fade.image`, `fade → composite.under`, the fade's
# level `FEEDBACK_LEVEL` the decay (colour and alpha alike). Many allowed.

LOOP = {("composite", "delay.image"), ("delay", "fade.image"), ("fade", "composite.under")}
FED_BACK = CHAIN - {("scene", ALL)} | {("scene", "composite.over"), ("composite", ALL)} | LOOP
FB_SAID = ("feedback: scene → composite over → output.all.image; composite → delay → fade → "
           "composite under — fade level 0.75 is how much of last frame stays")


def test_feedback_is_a_starter_a_picture_cable_offers():
    """Its key names no node kind (`echo` is the look-back's frame): the
    starter is "feedback", its decay the `fade` effect."""
    from hyperspace import graph as G
    assert ("feedback", "feedback") in graphview.STARTERS
    assert "feedback" in graphview.CABLE_STARTERS
    assert "feedback" not in G.NODE_KINDS and "echo" in G.NODE_KINDS   # (why not "echo")
    assert graphview.label_of("echo.1").startswith("Echo")
    assert graphview.FEEDBACK_FILE == "fade" and graphview.FEEDBACK_LEVEL == 0.75


def test_feedback_on_a_cable_splices_a_delay_loop_with_a_blend(tmp_path):
    """From a picture cable's menu: the composite goes onto the cable as
    insert ▸ composite (over) would, the loop round it through a new delay
    and a new fade, one undo step; the fade on at its level, in the same
    step; the three laid left to right."""
    from hyperspace import graph as G
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("feedback", ("scene", ALL)) is None
    assert wired_wires(rig) == FED_BACK
    spec = rig.loaded_patch.graph.spec
    assert {"kind": "composite"} in _entries(rig)            # (laid over)
    assert {"kind": "delay"} in _entries(rig)
    assert G.EffectAt("fade", 1) in spec.effects
    assert pushed == ["starter: feedback"]
    assert e.placed == ("delay", "fade", "composite") and e.added == "composite"
    assert e.said == graphview.FEEDBACK_SAID.format(
        src="scene", dst=ALL, comp="composite", delay="delay", fx="fade",
        level=graphview.FEEDBACK_LEVEL) == FB_SAID
    assert rig.reg["fx.fade.on"].value is True
    assert rig.reg["fx.fade.mix"].value == 1.0                # (the file's default)
    assert rig.reg["fx.fade.level"].value == 0.75


def test_two_feedbacks_in_one_graph(tmp_path):
    """A second is never refused (unlike tracers): the first loop's picture
    fed back again is its own composite, delay and fade."""
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("feedback", ("scene", ALL)) is None
    assert e.starter("feedback", ("composite", ALL)) is None
    assert e.placed == ("delay.2", "fade.2", "composite.2")
    assert wired_wires(rig) == FED_BACK - {("composite", ALL)} | {
        ("composite", "composite.2.over"), ("composite.2", ALL),
        ("composite.2", "delay.2.image"), ("delay.2", "fade.2.image"),
        ("fade.2", "composite.2.under")}
    assert pushed == ["starter: feedback", "starter: feedback"]
    assert rig.reg["fx.fade.2.level"].value == 0.75
    assert rig.reg["fx.fade.level"].value == 0.75
    assert "already" not in e.said


def test_feedback_from_the_picker_takes_the_scene_s_one_picture(tmp_path):
    """The picker's starters ▸ feedback (no cable): the scene's one picture,
    as the tracers; with no scene the loop is made and its open ends said;
    a scene feeding several picture ports is refused in words — no dead
    wire is added (review 2026-11-02, 8)."""
    rig, e, _ = wired_rig(tmp_path, SCENE)
    assert e.add_node("starter", "feedback") is None
    assert wired_wires(rig) == FED_BACK
    rig, e, _ = wired_rig(tmp_path / "b", {"frame": "wired"})
    assert e.starter("feedback") is None
    assert wired_wires(rig) == LOOP
    assert e.said == graphview.FEEDBACK_LOOP_SAID.format(
        comp="composite", delay="delay", fx="fade", level=0.75) + graphview.FEEDBACK_UNWIRED.format(
        comp="composite")
    assert e.placed == ("delay", "fade", "composite")
    two = {"frame": "wired", "wires": [*SCENE["wires"], {"from": "scene", "to": "output.2.image"}]}
    rig, e, pushed = wired_rig(tmp_path / "c", two)
    was = rig.loaded_patch.graph.spec.to_json()
    assert e.starter("feedback") == graphview.FEEDBACK_MANY_FEEDS.format(src="scene", n=2) == (
        "scene feeds 2 picture ports: say which — starters ▸ feedback on that cable, or add "
        "feedback after on scene")
    assert rig.loaded_patch.graph.spec.to_json() == was and pushed == [] and e.placed == ()
    assert graphview.picture_feeds(e, "scene") == [("scene", ALL), ("scene", "output.2.image")]


def test_the_tracers_share_the_scene_feed_rule(tmp_path):
    """`_scene_feed` is the one rule for a picker starter's picture: the
    tracers and dream branch says the count it returns (review 4)."""
    assert graphview._scene_feed({"frame": "wired"}) == (None, None, 0)
    assert graphview._scene_feed(SCENE) == ("scene", ALL, 1)
    two = {"frame": "wired", "wires": [*SCENE["wires"], {"from": "scene", "to": "output.2.image"}]}
    assert graphview._scene_feed(two) == ("scene", None, 2)
    _, e, _ = wired_rig(tmp_path, two)
    assert e.starter("dream") is None
    assert "left unwired: the composite's picture (the scene feeds 2 ports)" in e.said


def test_picture_feeds_names_the_cables_feedback_goes_after(tmp_path):
    """`graphview.picture_feeds`: a picture node's cables out (the node
    menu's "add feedback after"), read off the spec's wires with no copy
    of the section (review 3); [] for one feeding nothing; None for a
    geometry, a window and a node whose picture is a pin."""
    section = {"frame": "wired", "nodes": [{"kind": "composite"}, {"kind": "segment"}],
               "wires": [*SCENE["wires"], {"from": "scene", "to": "lookback.image"}]}
    _, e, _ = wired_rig(tmp_path, section)
    import copy as copy_mod
    deep, real = [], copy_mod.deepcopy
    copy_mod.deepcopy = lambda x, *a, **k: (deep.append(1), real(x, *a, **k))[1]
    try:
        assert graphview.picture_feeds(e, "scene") == [("scene", ALL), ("scene", "lookback.image")]
    finally:
        copy_mod.deepcopy = real
    assert deep == []
    assert graphview.picture_feeds(e, "composite") == []
    assert graphview.picture_feeds(e, "shape") is None
    assert graphview.picture_feeds(e, "output.all") is None
    assert graphview.picture_feeds(e, "segment") is None


def test_set_after_landing_is_the_one_post_landing_setter(tmp_path):
    """`_switch_on` and the feedback's level go through
    `_set_after_landing` (review 5): a value set only where the registry
    has the param, nothing with no registry."""
    rig, e, _ = wired_rig(tmp_path, SCENE)
    assert e.add_node("effect", "fade") is None
    graphview._set_after_landing(e, "fade", on=True, level=0.5, nope=1)
    assert rig.reg["fx.fade.on"].value is True and rig.reg["fx.fade.level"].value == 0.5
    assert "fx.fade.nope" not in rig.reg
    bare = graphview.Edit()
    graphview._set_after_landing(bare, "fade", on=True)      # no registry: nothing to do


def test_feedback_undoes_in_one_step(tmp_path):
    """One ⌘Z takes the three nodes, the loop and the fade's values back."""
    from test_undo import settle
    rig, e, pushed = wired_rig(tmp_path, SCENE, undo_rig=True)
    was = rig.loaded_patch.graph.spec.to_json()
    assert e.starter("feedback", ("scene", ALL)) is None
    assert rig.reg["fx.fade.level"].value == 0.75
    settle(rig)
    assert pushed == ["starter: feedback"]
    assert rig.undo.undo()
    assert rig.loaded_patch.graph.spec.to_json() == was
    assert wired_wires(rig) == CHAIN
    assert "fx.fade.level" not in rig.reg or rig.reg["fx.fade.level"].value != 0.75


# ---------------------------------------------------------------- feedback on the page

def test_add_feedback_after_lays_the_loop_below_the_node_s_box(page):
    """`ui_graph.add_feedback_after` (the node menu's item): the starter on
    the cable out of the node, its three nodes laid left to right under
    the node's real box as the editor draws it (review 6), one undo step;
    with no box drawn, from where the menu opened."""
    from imgui_bundle import imgui_node_editor as ed
    lib = page.lib
    lib.loaded_patch.new((0.0, 0.0))
    frame(page.panel, "graph")
    frame(page.panel, "graph")
    st = ui_graph._state(page.panel)
    ed.set_current_editor(st["editor"])
    nid = ed.NodeId(ui_graph._id(st, "n:render:scene"))
    pos, size = ed.get_node_position(nid), ed.get_node_size(nid)
    assert size.y > 0
    below = ui_graph.node_below(st, "render:scene")
    assert below == (pos.x, pos.y + size.y + graphview.GAP)
    u = undo.Undo(page.reg, page.router.table, marks=Marks(lib))
    undo.install(u)
    try:
        u.tick(1.0)
        u.tick(2.0)
        was = (lib.loaded_patch.graph.spec.to_json(), dict(lib.loaded_patch.layout))
        st["pan"], st["menu_at"] = (0.0, 0.0), (400.0, 300.0)
        assert ui_graph.add_feedback_after(page.panel, "scene", ALL) is None
        assert wired_wires(lib) == FED_BACK
        lay, (x, y) = lib.loaded_patch.layout, below
        assert lay["render:delay"] == [round(x), round(y)]
        assert lay["render:fade"] == [round(x + graphview.COL_W), round(y)]
        assert lay["render:composite"] == [round(x + 2 * graphview.COL_W), round(y)]
        assert len(lay) == len(was[1]) + 3
        assert st["said"].startswith("feedback: scene → composite over → output.all.image")
        assert u.stack[-1].label == "starter: feedback"
        assert u.undo()
    finally:
        undo.install(None)
    assert (lib.loaded_patch.graph.spec.to_json(), dict(lib.loaded_patch.layout)) == was
    assert ui_graph.node_below(st, "render:nowhere") is None  # no box: the menu's point


def test_the_menus_offer_feedback(page, monkeypatch):
    """The node menu: "add feedback after" on a picture node that feeds one
    port, a submenu per port on one that feeds several, disabled with why
    on one that feeds nothing, absent on a geometry; the cable menu's
    starters ▸ has feedback."""
    from imgui_bundle import imgui
    panel = page.panel
    page.lib.loaded_patch.new((0.0, 0.0))
    e = ui_graph.render_edit(panel)
    assert e.add_node("composite") is None                  # feeds nothing
    assert e.wire("scene", "lookback.image") is None        # the scene feeds two
    assert e.wire("lookback", "composite.over") is None     # the look-back feeds one
    frame(panel, "graph")
    view = ui_graph._state(panel)["view"]
    items: list[tuple[str, bool]] = []
    menus: list[str] = []
    monkeypatch.setattr(imgui, "menu_item_simple",
                        lambda label, *a, **k: items.append((label, k.get("enabled", True)))
                        and False)
    monkeypatch.setattr(imgui, "begin_menu", lambda label, *a, **k: menus.append(label) or True)
    monkeypatch.setattr(imgui, "end_menu", lambda: None)

    def drawn(fn):
        items.clear()
        menus.clear()
        imgui.new_frame()
        imgui.begin("menu")
        fn()
        imgui.end()
        imgui.end_frame()
    drawn(lambda: ui_graph.render_node_menu(panel, view.node("render:scene")))
    assert menus == [ui_graph.FEEDBACK_AFTER]
    assert ("→ output.all.image", True) in items and ("→ lookback.image", True) in items
    drawn(lambda: ui_graph.render_node_menu(panel, view.node("render:lookback")))
    assert (ui_graph.FEEDBACK_AFTER, True) in items and menus == []
    drawn(lambda: ui_graph.render_node_menu(panel, view.node("render:composite")))
    assert (f"{ui_graph.FEEDBACK_AFTER}: {graphview.FEEDBACK_FEEDS_NOTHING}", False) in items
    drawn(lambda: ui_graph.render_node_menu(panel, view.node("render:shape")))
    assert not [label for label, _ in items if label.startswith(ui_graph.FEEDBACK_AFTER)]
    cable = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    drawn(lambda: ui_graph._cable_menu(panel, view, cable, (0.0, 0.0)))
    assert "starters" in menus and ("feedback", True) in items


# ---------------------------------------------------------------- feedback draws

FB_PAIRS = [("scene", "composite.over"), ("composite", "output.1.image"), *LOOP]
FB_NODES = [{"kind": "composite"}, {"kind": "delay"}]
FB_VALUES = {"fade": {"on": True, "mix": 1.0, "level": graphview.FEEDBACK_LEVEL}}


def test_feedback_draws_and_its_trail_fades_to_clear(ctx):
    """The starter's graph on a renderer over a see-through ground,
    headless: it draws with no GL error; laid over (the default) the
    shape's frames stay calmer than the same loop laid add; after the
    shape goes the trail shows and fades frame on frame — its alpha too
    (review 1: a trail that kept alpha 1 was an opaque black ghost), gone
    within twenty."""
    from itertools import pairwise

    from test_graph_delay import _frame
    from test_graph_faces import _empty, _faces, _fbo, _renderer

    from hyperspace.outputs import Switches, View
    size = (160, 120)
    r = _renderer(ctx, None, FB_PAIRS, FB_NODES, None, FB_VALUES)
    add = _renderer(ctx, None, FB_PAIRS, [{"kind": "composite", "blend": "add"}, FB_NODES[1]],
                    None, FB_VALUES)
    vs = [View(Switches(), size, target=_fbo(ctx, *size))]
    va = [View(Switches(), size, target=_fbo(ctx, *size))]
    (first,) = _frame(ctx, r, _faces(), vs, size, 0)
    assert int(first[..., :3].max()) > 0 and "fade" in r.stats["effects"]
    for k in range(1, 8):                                   # (on the opaque ground, a window's)
        (over,) = _frame(ctx, r, _faces(), vs, size, k)
        (piled,) = _frame(ctx, add, _faces(), va, size, k)
    assert int(over[..., :3].sum()) < int(piled[..., :3].sum())
    assert (over[..., :3] == 255).mean() < (piled[..., :3] == 255).mean()  # fewer burnt pixels
    r = _renderer(ctx, None, FB_PAIRS, FB_NODES, None, FB_VALUES)
    r.bg_alpha = 0.0                                        # the see-through ground (cut through)
    vs = [View(Switches(), size, target=_fbo(ctx, *size))]
    for k in range(8):
        _frame(ctx, r, _faces(), vs, size, k)
    rgb, alpha = [], []
    for k in range(8, 30):
        (px,) = _frame(ctx, r, _empty(), vs, size, k)
        rgb.append(int(px[..., :3].sum()))
        alpha.append(int(px[..., 3].sum()))
    assert rgb[0] > 0 and alpha[0] > 0, (rgb, alpha)            # the trail shows, and covers
    assert all(b < a for a, b in pairwise(rgb[:10])), rgb       # and fades, frame on frame
    assert all(b < a for a, b in pairwise(alpha[:10])), alpha   # alpha with it: towards clear
    assert all(b <= a for a, b in pairwise(rgb)) and all(b <= a for a, b in pairwise(alpha))
    assert int(px.max()) <= 2, int(px.max())                    # gone, alpha included


def test_a_fringe_and_an_interior_fade_at_one_rate(ctx):
    """Review 7: a half-covered pixel decays as fast as a covered one. A
    still on channel a — white, opaque on the left, half see-through on
    the right — fed back for four frames, then nothing: each column's
    picture falls by the same fraction a frame (0.75: the palette's
    `rgb *= c.a` made the fringe fall by 0.75·a)."""
    import numpy as np
    from test_graph_delay import _frame
    from test_graph_faces import Still, _fbo, _media, _renderer, _rgba

    from hyperspace.media.frame import MediaFrame
    from hyperspace.outputs import Switches, View
    size = (64, 48)
    px0 = _rgba(16, 8, (255, 255, 255))
    px0[:, 8:, 3] = 128                                      # the right half: a fringe
    still = Still(px0)
    pairs = [("media.a", "composite.over"), ("composite", "output.1.image"), *LOOP]
    r = _renderer(ctx, _media(a=still), pairs, FB_NODES, None, FB_VALUES)
    r.bg_alpha = 0.0
    vs = [View(Switches(), size, target=_fbo(ctx, *size))]
    for k in range(4):
        _frame(ctx, r, _faces_off(), vs, size, k)
    still.f = MediaFrame(np.zeros((8, 16, 4), np.uint8), 1.0, 4)   # the still gone: clear
    (gone,) = _frame(ctx, r, _faces_off(), vs, size, 4)
    left, right = gone[24, 8], gone[24, 56]                  # one interior, one fringe pixel
    assert left[3] > right[3] > 20, (left, right)
    (later,) = _frame(ctx, r, _faces_off(), vs, size, 5)
    ratios = [later[24, x, 3] / gone[24, x, 3] for x in (8, 56)]
    assert all(abs(q - graphview.FEEDBACK_LEVEL) < 0.06 for q in ratios), ratios
    ratios = [later[24, x, 0] / gone[24, x, 0] for x in (8, 56)]
    assert all(abs(q - graphview.FEEDBACK_LEVEL) < 0.06 for q in ratios), ratios


def _faces_off():
    from test_graph_faces import _empty
    return _empty()
