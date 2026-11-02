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
        "echo",                                         # (wave 0 E1: the delay loop)
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


# ---------------------------------------------------------------- the echo (wave 0 E1, 2026-11-02)
#
# A delay loop with a blend, spliced onto a picture cable by the insert
# table: `picture → composite.over`, `composite → dst`, `composite →
# delay.image`, `delay → palette.image`, `palette → composite.under`, the
# palette's val slice shut to `ECHO_FEEDBACK` as the decay. Many allowed.

ECHO_LOOP = {("composite", "delay.image"), ("delay", "palette.image"),
             ("palette", "composite.under")}
ECHOED = CHAIN - {("scene", ALL)} | {("scene", "composite.over"), ("composite", ALL)} | ECHO_LOOP


def test_the_echo_is_a_starter_a_picture_cable_offers():
    assert ("echo", "echo") in graphview.STARTERS
    assert "echo" in graphview.CABLE_STARTERS
    assert graphview.ECHO_FILE == "palette" and graphview.ECHO_FEEDBACK == 0.75


def test_echo_on_a_cable_splices_a_delay_loop_with_a_blend(tmp_path):
    """From a picture cable's menu: the composite goes onto the cable as
    insert ▸ composite (over) would, the loop round it through a new delay
    and a new palette, one undo step; the palette on, at mix 1, its val_to
    the feedback, in the same step; the three laid left to right."""
    from hyperspace import graph as G
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("echo", ("scene", ALL)) is None
    assert wired_wires(rig) == ECHOED
    spec = rig.presets.graph.spec
    assert {"kind": "composite"} in _entries(rig)            # (laid over)
    assert {"kind": "delay"} in _entries(rig)
    assert G.EffectAt("palette", 1) in spec.effects
    assert pushed == ["starter: echo"]
    assert e.placed == ("delay", "palette", "composite") and e.added == "composite"
    assert e.said == graphview.ECHO_SAID.format(
        src="scene", dst=ALL, comp="composite", delay="delay", fx="palette",
        fb=graphview.ECHO_FEEDBACK) == (
        "echo: scene → composite over → output.all.image; composite → delay → palette → "
        "composite under — palette val to 0.75 is the feedback")
    assert rig.reg["fx.palette.on"].value is True
    assert rig.reg["fx.palette.mix"].value == 1.0
    assert rig.reg["fx.palette.val_to"].value == 0.75


def test_two_echoes_in_one_graph(tmp_path):
    """A second echo is never refused (unlike tracers): the first echo's
    picture echoed again is its own composite, delay and palette."""
    rig, e, pushed = wired_rig(tmp_path, SCENE)
    assert e.starter("echo", ("scene", ALL)) is None
    assert e.starter("echo", ("composite", ALL)) is None
    assert e.placed == ("delay.2", "palette.2", "composite.2")
    assert wired_wires(rig) == ECHOED - {("composite", ALL)} | {
        ("composite", "composite.2.over"), ("composite.2", ALL),
        ("composite.2", "delay.2.image"), ("delay.2", "palette.2.image"),
        ("palette.2", "composite.2.under")}
    assert pushed == ["starter: echo", "starter: echo"]
    assert rig.reg["fx.palette.2.val_to"].value == 0.75
    assert rig.reg["fx.palette.val_to"].value == 0.75
    assert "already" not in e.said


def test_echo_from_the_picker_takes_the_scene_s_picture(tmp_path):
    """The picker's starters ▸ echo (no cable): the scene's one picture, as
    the tracers; with no scene the loop is made and its open ends said; a
    scene feeding two ports gets the echo's over and the words say what is
    left."""
    rig, e, _ = wired_rig(tmp_path, SCENE)
    assert e.add_node("starter", "echo") is None
    assert wired_wires(rig) == ECHOED
    rig, e, _ = wired_rig(tmp_path / "b", {"frame": "wired"})
    assert e.starter("echo") is None
    assert wired_wires(rig) == ECHO_LOOP
    assert e.said == graphview.ECHO_LOOP_SAID.format(
        comp="composite", delay="delay", fx="palette", fb=0.75) + graphview.ECHO_UNWIRED.format(
        comp="composite")
    assert e.placed == ("delay", "palette", "composite")
    two = {"frame": "wired", "wires": [*SCENE["wires"], {"from": "scene", "to": "output.2.image"}]}
    rig, e, _ = wired_rig(tmp_path / "c", two)
    assert e.starter("echo") is None
    assert wired_wires(rig) == CHAIN | {("scene", "output.2.image"), ("scene", "composite.over")} \
        | ECHO_LOOP
    assert e.said.endswith(graphview.ECHO_UNWIRED_PICTURE.format(src="scene"))


def test_picture_feeds_names_the_cables_an_echo_goes_after(tmp_path):
    """`graphview.picture_feeds`: a picture node's cables out (the node
    menu's "add echo after"); [] for one feeding nothing; None for a
    geometry, a window and a node whose picture is a pin."""
    section = {"frame": "wired", "nodes": [{"kind": "composite"}, {"kind": "segment"}],
               "wires": [*SCENE["wires"], {"from": "scene", "to": "lookback.image"}]}
    _, e, _ = wired_rig(tmp_path, section)
    assert graphview.picture_feeds(e, "scene") == [("scene", ALL), ("scene", "lookback.image")]
    assert graphview.picture_feeds(e, "composite") == []
    assert graphview.picture_feeds(e, "shape") is None
    assert graphview.picture_feeds(e, "output.all") is None
    assert graphview.picture_feeds(e, "segment") is None


def test_echo_undoes_in_one_step(tmp_path):
    """One ⌘Z takes the three nodes, the loop and the palette's values back."""
    from test_undo import settle
    rig, e, pushed = wired_rig(tmp_path, SCENE, undo_rig=True)
    was = rig.presets.graph.spec.to_json()
    assert e.starter("echo", ("scene", ALL)) is None
    assert rig.reg["fx.palette.val_to"].value == 0.75
    settle(rig)
    assert pushed == ["starter: echo"]
    assert rig.undo.undo()
    assert rig.presets.graph.spec.to_json() == was
    assert wired_wires(rig) == CHAIN
    assert "fx.palette.val_to" not in rig.reg or rig.reg["fx.palette.val_to"].value != 0.75


# ---------------------------------------------------------------- the echo on the page

def test_add_echo_after_from_the_node_menu_lays_the_loop_below(page):
    """`ui_graph.add_echo_after` (the node menu's item): the echo starter on
    the cable out of the node, its three nodes laid left to right a node's
    height below where the menu opened, one undo step."""
    lib = page.lib
    lib.presets.new((0.0, 0.0))
    u = undo.Undo(page.reg, page.router.table, marks=Marks(lib))
    undo.install(u)
    try:
        u.tick(1.0)
        u.tick(2.0)
        was = (lib.presets.graph.spec.to_json(), dict(lib.presets.layout))
        st = ui_graph._state(page.panel)
        st["pan"], st["menu_at"] = (0.0, 0.0), (400.0, 300.0)
        assert ui_graph.add_echo_after(page.panel, "scene", ALL) is None
        assert wired_wires(lib) == ECHOED
        lay, y = lib.presets.layout, 300 + ui_graph.ECHO_BELOW
        assert lay["render:delay"] == [400, y]
        assert lay["render:palette"] == [400 + graphview.COL_W, y]
        assert lay["render:composite"] == [400 + 2 * graphview.COL_W, y]
        assert len(lay) == len(was[1]) + 3
        assert st["said"].startswith("echo: scene → composite over → output.all.image")
        assert u.stack[-1].label == "starter: echo"
        assert u.undo()
    finally:
        undo.install(None)
    assert (lib.presets.graph.spec.to_json(), dict(lib.presets.layout)) == was


def test_the_menus_offer_the_echo(page, monkeypatch):
    """The node menu: "add echo after" on a picture node that feeds one
    port, a submenu per port on one that feeds several, disabled with why
    on one that feeds nothing, absent on a geometry; the cable menu's
    starters ▸ has echo."""
    from imgui_bundle import imgui
    panel = page.panel
    page.lib.presets.new((0.0, 0.0))
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
    assert menus == [ui_graph.ECHO_AFTER]
    assert ("→ output.all.image", True) in items and ("→ lookback.image", True) in items
    drawn(lambda: ui_graph.render_node_menu(panel, view.node("render:lookback")))
    assert (ui_graph.ECHO_AFTER, True) in items and menus == []
    drawn(lambda: ui_graph.render_node_menu(panel, view.node("render:composite")))
    assert (f"{ui_graph.ECHO_AFTER}: {graphview.ECHO_FEEDS_NOTHING}", False) in items
    drawn(lambda: ui_graph.render_node_menu(panel, view.node("render:shape")))
    assert not [label for label, _ in items if label.startswith(ui_graph.ECHO_AFTER)]
    cable = next(c for c in view.cables if c.dst_port == "rin:output.all/image")
    drawn(lambda: ui_graph._cable_menu(panel, view, cable, (0.0, 0.0)))
    assert "starters" in menus and ("echo", True) in items


# ---------------------------------------------------------------- the echo draws

ECHO_PAIRS = [("scene", "composite.over"), ("composite", "output.1.image"), *ECHO_LOOP]
ECHO_NODES = [{"kind": "composite"}, {"kind": "delay"}]
ECHO_VALUES = {"palette": {"on": True, "mix": 1.0, "val_to": graphview.ECHO_FEEDBACK}}


def test_the_echo_draws_and_its_trail_fades(ctx):
    """The starter's graph on a renderer, headless: it draws with no GL
    error; laid over (the default) the shape's frames stay calmer than the
    same loop laid add (a see-through face brightens towards its own full
    colour, never past it; add piles up to 1/(1 − 0.75) = 4×); after the
    shape goes the trail shows and each frame is strictly darker than the
    last, gone within twenty."""
    from itertools import pairwise

    from test_graph_delay import _frame
    from test_graph_faces import _empty, _faces, _fbo, _renderer

    from hyperspace.outputs import Switches, View
    size = (160, 120)
    r = _renderer(ctx, None, ECHO_PAIRS, ECHO_NODES, None, ECHO_VALUES)
    add = _renderer(ctx, None, ECHO_PAIRS, [{"kind": "composite", "blend": "add"}, ECHO_NODES[1]],
                    None, ECHO_VALUES)
    vs = [View(Switches(), size, target=_fbo(ctx, *size))]
    va = [View(Switches(), size, target=_fbo(ctx, *size))]
    (first,) = _frame(ctx, r, _faces(), vs, size, 0)
    assert int(first[..., :3].max()) > 0 and "palette" in r.stats["effects"]
    for k in range(1, 8):
        (over,) = _frame(ctx, r, _faces(), vs, size, k)
        (piled,) = _frame(ctx, add, _faces(), va, size, k)
    assert int(over[..., :3].sum()) < int(piled[..., :3].sum())
    assert (over[..., :3] == 255).mean() < (piled[..., :3] == 255).mean()  # fewer burnt pixels
    sums = []
    for k in range(8, 30):
        (px,) = _frame(ctx, r, _empty(), vs, size, k)
        sums.append(int(px[..., :3].sum()))
    assert sums[0] > 0, sums                                    # the trail shows
    assert all(b < a for a, b in pairwise(sums[:10])), sums     # and fades, frame on frame
    assert all(b <= a for a, b in pairwise(sums)), sums         # (8-bit rounding at the tail)
    assert int(px[..., :3].max()) <= 2, int(px[..., :3].max())  # gone
