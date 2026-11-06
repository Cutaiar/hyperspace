"""Wave 3 P3 (row 524, the owner's yes): the take-over chip beside **wire as
saved**.

The plain chip never takes a port over. The second chip is drawn only while a
press of the first would refuse a taken port it could take; its label names
what is cut; one press, one undo step, the cut said after. A cut's source stays
on the canvas, not re-wired. A chip that no longer holds refuses in words.
"""

from __future__ import annotations

import pytest
from imgui_bundle import imgui_node_editor as ed
from test_graph_groups import rig, spawned, state, trip, watch, wires  # noqa: F401
from test_graphview import _in_editor
from test_ui_pane import _only, _spills, _tall_driver
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import graphview, ui_graph, undo
from hyperspace.graphview import TakeOver

GID = "group.1"
HUECYCLE = ("huecycle", "output.all.image")
THROUGH = ("delay", "output.all.image")


def edit(rig):  # noqa: F811
    return ui_graph.group_edit(rig.panel)


def press(rig, gid=GID):  # noqa: F811
    """The chip's press on what it would say now."""
    return ui_graph.take_over(rig.panel, edit(rig).take_over_of(gid))


def press_plan(rig, plan):  # noqa: F811
    return ui_graph.take_over(rig.panel, plan)


def open_ids(rig, gid=GID) -> list[str]:  # noqa: F811
    pre = rig.lib.loaded_patch
    entry = next(g for g in pre.groups if g["id"] == gid)
    return [p["id"] for p in graphview.open_ports(pre.graph.spec, entry)]


class Section:
    """The `gs` an `Edit` lands through, with no rig: for hosts no preset has."""

    def __init__(self, doc):
        self.spec = G.read_graph(doc)
        self.landed = 0

    def files(self):
        return None

    def land(self, spec, _doc):
        self.spec = spec
        self.landed += 1


def on_section(doc, *ports, nodes=("render:warp",)):
    """An `Edit` over section `doc` with one group holding `ports`."""
    gs = Section({"frame": "wired", **doc})
    pushed = []
    e = graphview.Edit(graph=gs, push=pushed.append)
    entry = {"id": GID, "name": "g", "nodes": list(nodes), "ports": list(ports)}
    e.loaded_patch = type("P", (), {"groups": [entry], "layout": {}})()
    return e, gs, pushed


def into(gs, port) -> list[str]:
    return [w.src for w in gs.spec.all_wires() if w.dst == port]


OUT = {"id": "out", "type": "image", "from": "warp", "was": "output.all.image"}
EFFECTS = [{"kind": "effect", "file": "warp"}, {"kind": "effect", "file": "acid"}]


# ---------------------------------------------------------------- one press

def test_the_chip_names_the_cut_and_one_press_takes_it_and_one_undo_gives_it_back(rig):  # noqa: F811
    st = trip(rig)
    spawned(rig)
    before, u = state(rig), watch(rig)
    try:
        plan = edit(rig).take_over_of(GID)
        assert plan.lines == ("wire as saved, replacing", "huecycle → All outputs")
        assert state(rig) == before                             # (asking moves nothing)
        n = len(u.stack)
        assert ui_graph.take_over(rig.panel, plan) is None
        assert len(u.stack) == n + 1
        assert u.stack[-1].label == "wire acid wash as saved, replacing huecycle → All outputs"
        got = wires(rig)
        assert THROUGH in got and ("scene", "acid.image") in got and HUECYCLE not in got
        assert st["said"] == ("wired as saved: scene → acid.image, delay → output.all.image; "
                              "cut huecycle → All outputs")
        assert st["note"] == ""
        assert open_ids(rig) == []
        assert edit(rig).take_over_of(GID) is None              # the chip is gone
        frame(rig.panel, "graph")
        cables = {(c.ref.src, c.ref.dst) for c in st["view"].cables if c.kind == "render"}
        assert THROUGH in cables and HUECYCLE not in cables     # its result is drawn
        assert u.undo()
        assert state(rig) == before and HUECYCLE in wires(rig)
        assert edit(rig).take_over_of(GID) is not None
    finally:
        undo.install(None)


def test_what_was_cut_stays_on_the_canvas_and_is_not_rewired(rig):  # noqa: F811
    st = trip(rig)
    spawned(rig)
    assert press(rig) is None
    frame(rig.panel, "graph")
    assert "huecycle" in graphview.frame_names(rig.lib.loaded_patch.graph.spec)
    assert st["view"].node("render:huecycle") is not None
    assert not [w for w in wires(rig) if w[0] == "huecycle"]


def test_a_source_a_cut_mentions_last_keeps_its_entry():
    e, gs, _ = on_section({"nodes": EFFECTS, "wires": [{"from": "acid", "to": "output.all.image"}]},
                          OUT)
    assert e.wire_taking_over(e.take_over_of(GID)) is None
    assert into(gs, "output.all.image") == ["warp"]
    assert "acid" in graphview.frame_names(gs.spec)


def test_the_plain_chip_is_unmoved_it_never_cuts_and_the_chip_stays_beside_it(rig):  # noqa: F811
    trip(rig)
    spawned(rig)
    assert edit(rig).take_over_of(GID) is not None
    assert ui_graph.wire_as_saved(rig.panel, GID) == "output.all.image is taken"
    assert HUECYCLE in wires(rig) and THROUGH not in wires(rig)
    assert ui_graph.wire_as_saved(rig.panel, GID) == "output.all.image is taken"  # again: the same
    assert HUECYCLE in wires(rig)
    plan = edit(rig).take_over_of(GID)                # (the chip after a plain press: only the cut)
    assert plan.lines[-1] == "huecycle → All outputs" and plan.wires == ("delay → output.all.image",)
    assert ui_graph.take_over(rig.panel, plan) is None
    assert THROUGH in wires(rig) and HUECYCLE not in wires(rig)


# ---------------------------------------------------------------- when there is no chip

def test_no_chip_with_nothing_taken_or_nothing_open():
    free = {**OUT, "was": "output.1.image"}
    e, gs, pushed = on_section({"nodes": EFFECTS}, free)
    assert e.take_over_of(GID) is None                # the port is free: the plain chip's
    assert e.wire_as_saved(GID) is None and pushed == ["wire g as saved"]
    assert into(gs, "output.1.image") == ["warp"]
    assert e.take_over_of(GID) is None                # no pin open
    assert e.take_over_of("group.9") is None


def test_no_chip_for_a_pin_refused_for_another_reason():
    port = {"id": "out", "type": "image", "from": "warp", "was": "tripcolour.image"}
    e, _, pushed = on_section({"nodes": EFFECTS}, port)
    assert e.take_over_of(GID) is None
    assert e.wire_as_saved(GID) == "no node tripcolour" and not pushed


def test_a_cut_cannot_take_a_port_the_read_would_refuse():
    """Taking `acid.image` for warp closes a loop with the hand's warp's feed,
    so there is no chip: the plain chip's "taken" stands."""
    doc = {"nodes": EFFECTS, "wires": [{"from": "shape", "to": "scene.geometry"},
                                       {"from": "scene", "to": "acid.image"},
                                       {"from": "acid", "to": "warp.image"}]}
    port = {"id": "out", "type": "image", "from": "warp", "was": "acid.image"}
    e, _, pushed = on_section(doc, port)
    assert e.take_over_of(GID) is None
    assert e.wire_as_saved(GID) == "acid.image is taken" and not pushed


def test_a_taken_inlet_is_no_open_pin_and_a_hands_wire_is_not_cut(rig):  # noqa: F811
    st = trip(rig)
    spawned(rig)
    assert ui_graph._render_said(rig.panel, ui_graph.render_edit(rig.panel),
                                 lambda e: graphview.render_wire(e, "rout:huecycle",
                                                                 "rin:acid/image")) is None
    assert open_ids(rig) == ["out"]
    plan = edit(rig).take_over_of(GID)
    assert plan.cuts == (HUECYCLE,)                   # the outlet's alone
    assert ui_graph.take_over(rig.panel, plan) is None
    assert ("huecycle", "acid.image") in wires(rig) and ("scene", "acid.image") not in wires(rig)
    assert st["said"].startswith("wired as saved: delay → output.all.image; cut huecycle")


def test_a_pin_refused_for_another_reason_stays_refused_beside_a_take_over():
    no_node = {"id": "out.2", "type": "image", "from": "acid", "was": "tripcolour.image"}
    e, gs, pushed = on_section(
        {"nodes": [*EFFECTS, {"kind": "effect", "file": "huecycle"}],
         "wires": [{"from": "huecycle", "to": "output.all.image"}]},
        OUT, no_node, nodes=("render:warp", "render:acid"))
    plan = e.take_over_of(GID)
    assert plan.refused == ("no node tripcolour",)
    assert e.wire_taking_over(plan) == "no node tripcolour"
    assert into(gs, "output.all.image") == ["warp"] and len(pushed) == 1


# ---------------------------------------------------------------- scene.geometry

def test_scene_geometry_has_nothing_to_cut_and_keeps_its_draw_order():
    doc = {"nodes": [*EFFECTS, {"kind": "shape"}, {"kind": "hands", "instance": 2}],
           "wires": [{"from": "hands.2", "to": "scene.geometry"},
                     {"from": "scene", "to": "output.all.image"}]}
    inlet = {"id": "in", "type": "geometry", "to": "scene.geometry", "was": "shape",
             "before": "hands.2"}
    e, gs, _ = on_section(doc, inlet, OUT)
    plan = e.take_over_of(GID)
    assert plan.cuts == (("scene", "output.all.image"),)      # never the geometry's
    assert e.wire_taking_over(plan) is None
    assert into(gs, "scene.geometry") == ["shape", "hands.2"]
    assert into(gs, "output.all.image") == ["warp"]


def test_an_outlet_into_scene_geometry_is_the_plain_chips():
    port = {"id": "out", "type": "geometry", "from": "hands.2", "was": "scene.geometry"}
    doc = {"nodes": [*EFFECTS, {"kind": "hands", "instance": 2}],
           "wires": [{"from": "shape", "to": "scene.geometry"},
                     {"from": "scene", "to": "output.all.image"}]}
    e, gs, _ = on_section(doc, port, nodes=("render:hands.2",))
    assert e.take_over_of(GID) is None
    assert e.wire_as_saved(GID) is None
    assert sorted(into(gs, "scene.geometry")) == ["hands.2", "shape"]


# ---------------------------------------------------------------- several cuts

def several(n: int, name="a", port="c"):
    cuts = tuple((f"{name}{k}", f"{port}{k}.image") for k in range(n))
    return TakeOver(gid=GID, name="g", spec=None, cuts=cuts, wires=(),
                    words=tuple(f"{a} → {b}" for a, b in cuts))


def test_a_chip_names_every_cut_or_says_the_count_and_the_hover_has_them_all():
    assert several(3).lines == ("wire as saved, replacing", "a0 → c0.image", "a1 → c1.image",
                                "a2 → c2.image")
    many = several(4)
    assert many.lines == ("wire as saved, replacing", "4 cables")
    assert all(w in many.tip for w in many.words)


def test_the_hover_says_the_wires_and_what_stays_refused_too():
    e, _, _ = on_section(
        {"nodes": [*EFFECTS, {"kind": "effect", "file": "huecycle"}],
         "wires": [{"from": "huecycle", "to": "output.all.image"}]},
        OUT, {"id": "out.2", "type": "image", "from": "acid", "was": "output.all.image"},
        nodes=("render:warp", "render:acid"))
    tip = e.take_over_of(GID).tip
    assert "huecycle → All outputs" in tip                 # the cut
    assert "warp → output.all.image" in tip                # which of the two outlets wins
    assert "output.all.image is taken" in tip              # and the other


def test_the_words_are_the_canvases():
    assert graphview.port_said("output.all.image") == "All outputs"
    assert graphview.port_said("output.all.hands") == "All outputs hands"
    assert graphview.port_said("output.1.image") == "Output 1"
    assert graphview.port_said("output.1.image", {1: "Projector"}) == "Projector"
    assert graphview.port_said("composite.over") == "Composite over"
    assert graphview.source_said("acid.2") == "acid 2"
    assert graphview.source_said("scene.cover") == "Scene cover"


def test_two_cuts_are_one_press_and_both_said():
    doc = {"nodes": [*EFFECTS, {"kind": "effect", "file": "wobble"},
                     {"kind": "effect", "file": "huecycle"}],
           "wires": [{"from": "wobble", "to": "output.all.image"},
                     {"from": "huecycle", "to": "output.1.image"}]}
    e, gs, pushed = on_section(
        doc, OUT, {"id": "out.2", "type": "image", "from": "acid", "was": "output.1.image"},
        nodes=("render:warp", "render:acid"))
    plan = e.take_over_of(GID)
    assert plan.words == ("wobble → All outputs", "huecycle → Output 1")
    assert e.wire_taking_over(plan) is None
    assert len(pushed) == 1 and gs.landed == 1
    assert into(gs, "output.all.image") == ["warp"] and into(gs, "output.1.image") == ["acid"]
    assert "cut wobble → All outputs, huecycle → Output 1" in e.said


def test_two_outlets_on_one_taken_port_cut_one_cable_and_the_second_is_refused():
    doc = {"nodes": EFFECTS + [{"kind": "effect", "file": "huecycle"}],
           "wires": [{"from": "huecycle", "to": "output.all.image"}]}
    e, gs, _ = on_section(doc, OUT, {"id": "out.2", "type": "image", "from": "acid",
                                     "was": "output.all.image"},
                          nodes=("render:warp", "render:acid"))
    plan = e.take_over_of(GID)
    assert plan.cuts == (("huecycle", "output.all.image"),)
    assert plan.refused == ("output.all.image is taken",)
    assert e.wire_taking_over(plan) == "output.all.image is taken"
    assert into(gs, "output.all.image") == ["warp"]


def test_the_rigs_bus_cable_is_not_a_cut():
    """A window's port the rig's bus cable feeds is free as ever: the preset's
    wire stands in front of it, and the chip names nothing."""
    port = {"id": "out", "type": "image", "from": "warp", "was": "output.1.image"}
    e, _, _ = on_section({"nodes": EFFECTS, "wires": [{"from": "acid", "to": "output.all.image"}]},
                         port)
    assert e.take_over_of(GID) is None


def test_taking_another_groups_cable_opens_that_groups_pin(rig):  # noqa: F811
    """Two copies: the second takes All outputs from the first. The first's pin
    is open again, and drawn; its chip would take it back. Nothing re-wires."""
    trip(rig)
    spawned(rig)
    assert press(rig) is None
    spawned(rig, at=(100.0, 300.0), keep=True)
    second = rig.lib.loaded_patch.groups[-1]["id"]
    assert press(rig, second) is None
    assert ("delay.2", "output.all.image") in wires(rig) and THROUGH not in wires(rig)
    assert open_ids(rig) == ["out"]
    assert edit(rig).take_over_of(GID).words == ("Delay 2 → All outputs",)


# ---------------------------------------------------------------- the plain chip's path (row 665)

def test_the_plain_chip_lands_on_a_free_all_outputs():
    e, gs, pushed = on_section({"nodes": EFFECTS}, OUT)
    assert e.wire_as_saved(GID) is None and len(pushed) == 1
    assert into(gs, "output.all.image") == ["warp"]


def test_a_member_feeding_another_port_leaves_its_other_pin_open():
    """One member, two host ports: the plain press lands the free one, and the
    taken one is still a pin, still on offer. The plain chip cuts nothing."""
    two = ({"id": "out", "type": "image", "from": "warp", "was": "output.1.image"},
           {"id": "out.2", "type": "image", "from": "warp", "was": "output.all.image"})
    e, gs, _ = on_section({"nodes": EFFECTS, "wires": [{"from": "acid", "to": "output.all.image"}]},
                          *two)
    assert e.wire_as_saved(GID) == "output.all.image is taken"
    assert into(gs, "output.1.image") == ["warp"]
    assert into(gs, "output.all.image") == ["acid"]           # never cut
    entry = e.loaded_patch.groups[0]
    assert [p["id"] for p in graphview.open_ports(gs.spec, entry)] == ["out.2"]
    plan = e.take_over_of(GID)
    assert plan.cuts == (("acid", "output.all.image"),)
    assert e.wire_taking_over(plan) is None
    assert into(gs, "output.all.image") == ["warp"]
    assert graphview.open_ports(gs.spec, entry) == []


@pytest.mark.parametrize("was", [{}, {"was": ""}], ids=["absent", "empty"])
def test_an_outlet_saying_nothing_it_fed_closes_once_its_member_feeds_outside(was):
    """No `was` to match: the old rule. Wired by hand, the pin closes, and a press
    has no "the patch says nothing it was wired to" left to repeat."""
    port = {"id": "out", "type": "image", "from": "warp", **was}
    e, gs, _ = on_section({"nodes": EFFECTS}, port)
    entry = e.loaded_patch.groups[0]
    assert [p["id"] for p in graphview.open_ports(gs.spec, entry)] == ["out"]
    assert e.wire_as_saved(GID) == graphview.NO_WAS.format(port="out")
    gs.spec = G.read_graph({"frame": "wired", "nodes": EFFECTS,
                            "wires": [{"from": "warp", "to": "acid.image"}]})
    entry["nodes"] = ["render:warp", "render:acid"]
    assert [p["id"] for p in graphview.open_ports(gs.spec, entry)] == ["out"]  # inside: still open
    entry["nodes"] = ["render:warp"]
    assert graphview.open_ports(gs.spec, entry) == []                          # outside: closed
    assert e.wire_as_saved(GID) == graphview.NOTHING_OPEN.format(name="g")


def test_the_plain_chip_never_cuts_whatever_feeds_the_port():
    for src in ("acid", "scene"):
        e, gs, pushed = on_section(
            {"nodes": EFFECTS, "wires": [{"from": src, "to": "output.all.image"}]}, OUT)
        assert e.wire_as_saved(GID) == "output.all.image is taken"
        assert into(gs, "output.all.image") == [src] and not pushed and gs.landed == 0


def test_a_cut_outlets_pin_opens_though_its_member_feeds_another_port():
    e, gs, _ = on_section(
        {"nodes": EFFECTS, "wires": [{"from": "warp", "to": "output.1.image"},
                                     {"from": "warp", "to": "output.all.image"}]},
        {"id": "x", "type": "image", "from": "warp", "was": "output.all.image"})
    entry = e.loaded_patch.groups[0]
    assert graphview.open_ports(gs.spec, entry) == []
    e.graph.spec = G.read_graph({"frame": "wired", "nodes": EFFECTS, "wires": [
        {"from": "warp", "to": "output.1.image"}, {"from": "acid", "to": "output.all.image"}]})
    assert [p["id"] for p in graphview.open_ports(gs.spec, entry)] == ["x"]


# ---------------------------------------------------------------- a chip that no longer holds

def test_a_press_after_the_preset_moved_refuses_in_words_and_cuts_nothing(rig):  # noqa: F811
    st = trip(rig)
    spawned(rig)
    plan = edit(rig).take_over_of(GID)
    u = watch(rig)
    try:
        # the same group and port, another cable feeding it
        assert ui_graph._render_said(rig.panel, ui_graph.render_edit(rig.panel),
                                     lambda e: graphview.render_wire(e, "rout:scene",
                                                                     "rin:output.all/image")) is None
        wired, n = wires(rig), len(u.stack)
        why = ui_graph.take_over(rig.panel, plan)
        assert why == graphview.TAKE_OVER_STALE.format(name="acid wash")
        assert st["note"] == why and st["said"] == ""
        assert wires(rig) == wired and len(u.stack) == n
        assert edit(rig).take_over_of(GID).words == ("Scene → All outputs",)
    finally:
        undo.install(None)


def test_a_press_after_a_reload_of_the_same_preset_refuses(rig):  # noqa: F811
    trip(rig)
    spawned(rig)
    plan = edit(rig).take_over_of(GID)
    rig.lib.load("presets", "party-trip")
    assert ui_graph.take_over(rig.panel, plan) is not None
    assert HUECYCLE in wires(rig)


def test_a_press_once_the_group_is_gone_refuses(rig):  # noqa: F811
    trip(rig)
    spawned(rig)
    plan = edit(rig).take_over_of(GID)
    rig.lib.loaded_patch.groups = []
    assert press_plan(rig, plan) == graphview.TAKE_OVER_STALE.format(name="acid wash")
    assert HUECYCLE in wires(rig)


def test_a_press_once_the_plan_is_gone_refuses():
    e, gs, pushed = on_section({"nodes": EFFECTS,
                                "wires": [{"from": "acid", "to": "output.all.image"}]}, OUT)
    plan = e.take_over_of(GID)
    e.loaded_patch.groups[0]["ports"] = []
    assert e.wire_taking_over(plan) == graphview.TAKE_OVER_STALE.format(name="g")
    assert not pushed and gs.landed == 0


# ---------------------------------------------------------------- the chip, by the mouse

@pytest.fixture()
def driven(rig, monkeypatch):  # noqa: F811
    rig.panel.desk = False                      # the panel the whole window
    st = trip(rig)
    spawned(rig)
    d = _tall_driver(rig, monkeypatch)          # (a pane tall enough for the whole selection)
    d.run(d.wait(2))
    _in_editor(rig, lambda: ed.select_node(ed.NodeId(ui_graph._id(st, "n:" + GID))))
    _only(st, "selection")
    d.run(d.wait(3))
    return rig, d, st


CHIP = "#graph.group.take_over"


def test_the_chip_is_drawn_inside_the_pane_and_a_click_lands_it(driven):
    r, d, st = driven
    x0, _y0, x1, _y1 = d.rect(CHIP)
    (px, _py), (pw, _ph) = st["details_rect"]
    assert px <= x0 and x1 <= px + pw + 1             # no cut's name runs off the pane
    d.run(d.click(CHIP), d.park())
    assert THROUGH in wires(r) and HUECYCLE not in wires(r)
    d.run(d.wait(2))
    assert CHIP not in d.rects


def test_the_plain_chip_by_the_mouse_never_cuts(driven):
    r, d, st = driven
    d.run(d.click("wire as saved##graph.group"), d.park())
    assert HUECYCLE in wires(r) and THROUGH not in wires(r)
    assert st["note"] == "output.all.image is taken"
    d.run(d.wait(2))
    assert CHIP in d.rects                            # still on offer


def test_a_preset_changed_while_the_mouse_is_down_refuses(driven):
    """What the press is judged against is what the chip said as the mouse went
    down: the cable feeding the port moves under a held chip."""
    r, d, st = driven
    d.run(d.move(CHIP), d.press(True), d.wait(2))
    assert ui_graph._render_said(r.panel, ui_graph.render_edit(r.panel),
                                 lambda e: graphview.render_wire(e, "rout:scene",
                                                                 "rin:output.all/image")) is None
    d.run(d.press(False), d.park())
    assert st["note"] == graphview.TAKE_OVER_STALE.format(name="acid wash")
    assert ("scene", "output.all.image") in wires(r) and THROUGH not in wires(r)


def test_a_load_taking_the_group_under_a_held_chip_says_so_at_the_release(driven):
    r, d, st = driven
    d.run(d.move(CHIP), d.press(True), d.wait(2))
    assert st.get("take_over_asked") is not None
    r.lib.load("presets", "party-noita")
    d.run(d.wait(2))
    assert CHIP not in d.rects
    wired = wires(r)
    d.run(d.press(False), d.wait(1))
    assert st["note"] == graphview.TAKE_OVER_STALE.format(name="acid wash")
    assert "take_over_asked" not in st and wires(r) == wired


def test_a_port_coming_free_under_a_held_chip_says_so_at_the_release(driven):
    r, d, st = driven
    d.run(d.move(CHIP), d.press(True), d.wait(2))
    assert ui_graph._render_said(r.panel, ui_graph.render_edit(r.panel),
                                 lambda e: graphview.render_unwire(e, "rout:huecycle",
                                                                   "rin:output.all/image")) is None
    d.run(d.wait(2))
    assert CHIP not in d.rects
    d.run(d.press(False), d.wait(1))
    assert st["note"] == graphview.TAKE_OVER_STALE.format(name="acid wash")
    assert "take_over_asked" not in st and THROUGH not in wires(r)


def test_letting_go_off_the_chip_says_nothing_and_cuts_nothing(driven):
    r, d, st = driven
    d.run(d.move(CHIP), d.press(True), d.wait(1), d.move((5.0, 5.0)), d.press(False), d.wait(1))
    assert st["note"] == "" and "take_over_asked" not in st
    assert HUECYCLE in wires(r) and THROUGH not in wires(r)


@pytest.mark.parametrize("plan", [
    several(4),
    several(1, "doublevision.2", "output.1.a-rather-long-node-name-indeed"),
    several(3, "doublevision.2.a-long-source-name-for-the-wrap", "output.1"),
], ids=["count", "one-long", "three-long"])
def test_the_chip_fits_the_narrowest_pane(driven, plan):
    """REVIEW.md: a widget fits the narrowest place it is drawn (`SIDE_MIN`)."""
    r, d, st = driven
    st["side_w"] = ui_graph.SIDE_MIN
    spec = ui_graph.group_edit(r.panel).graph.spec
    st["take_over_plan"] = (spec, GID, plan)
    d.run(d.wait(3))
    assert st["details_rect"][1][0] == ui_graph.SIDE_MIN
    assert not [k for k in _spills(d, st) if k[0].endswith("take_over")]
