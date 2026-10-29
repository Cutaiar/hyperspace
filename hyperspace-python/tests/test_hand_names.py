"""Hand routes addressed by name (plan 13 WP5b, decision register row 20,
audit N7): ``hand:right.roll`` reads the right roll wherever `[hands] dofs`
puts it; a name the rig lacks is dormant, never another lane; ``hand:<i>``
still reads the lane at index i."""

import math
from types import SimpleNamespace as NS

import numpy as np
import pytest
from test_hands import _frame, hand, make_app, rig, run

from hyperspace import hands
from hyperspace.routing import Binding, Bindings, Router

ROLL45 = (-math.sin(math.radians(45)), -math.cos(math.radians(45)), 0.0)   # right palm


@pytest.fixture()
def app(tmp_path):
    return make_app(tmp_path)


def _roll(r, app, normal=ROLL45, **kw):
    run(r, 2, hand(pos=(0.0, 200.0, 0.0), normal=normal, **kw), router=app.router)
    _frame(app)


def test_a_named_hand_route_follows_its_axis_whatever_the_dofs_order(app):
    """One preset row, two rigs: the default six dofs (right roll is lane 9)
    and a trimmed, reordered list (right roll is lane 5). The row follows the
    right roll on both — through the same router, so a republished layout
    re-resolves the cached address."""
    app.table.add(Binding("hand:right.roll", "view.inst_amp", "position"))
    p = app.reg["view.inst_amp"]
    p.set_norm(0.2)
    seen = []
    for dofs in (["x", "y", "z", "roll", "pitch", "yaw"], ["yaw", "y", "roll"]):
        r = rig(dofs=dofs)
        _roll(r, app, normal=(0.0, -1.0, 0.0))                      # level: roll reads 0.5
        assert p.eff_norm == pytest.approx(0.5, abs=1e-4)
        _roll(r, app)                                               # right roll 45°
        k = r.io.axis("right.roll")
        seen.append(k)
        assert app.router.names["hand"]["right.roll"] == k
        assert app.router.lane("hand:right.roll") == ("hand", k)
        assert p.eff_norm == pytest.approx(0.75, abs=1e-3)          # (45 + 90) / 180
        assert p.norm == pytest.approx(0.2)                         # the base never moves
        run(r, 2, router=app.router)                                # the hand leaves
        _frame(app)
        assert not p.modulated and p.norm == pytest.approx(0.2)
    assert seen == [9, 5]                                           # two different lanes


def test_a_name_the_rig_lacks_leaves_the_row_dormant(app):
    """A rig without roll: `hand:right.roll` does nothing — not the lane
    that sits where the default layout's roll would. With no map published
    at all (no hands adapter), every named row is dormant too."""
    r = rig(dofs=["x", "y", "z"])
    app.table.add(Binding("hand:right.roll", "view.inst_amp", "position"))
    app.table.add(Binding("hand:right.nosuch", "view.bright", "push", 0.5))
    inst, bright = app.reg["view.inst_amp"], app.reg["view.bright"]
    _roll(r, app, tips=(10.0, 60.0, 60.0, 60.0), palm_w=100.0)
    assert "right.roll" not in app.router.names["hand"]
    assert app.router.lane("hand:right.roll") == ("hand", -1)
    assert len(r.io.lanes()) > 9                           # lane 9 exists: a switch here
    assert not inst.modulated and not bright.modulated
    # no hands adapter: a fed vector but no names — named rows stay dormant
    router = Router(app.reg, Bindings([Binding("hand:left.y", "view.inst_amp", "position")]))
    router.feed("hand", np.full(22, 0.9))
    router.modulate()
    app.reg.apply()
    assert not inst.modulated
    assert router.lane("hand:left.y") == ("hand", -1) and router.rest_of("hand:left.y") == 0.0


def test_a_numeric_hand_route_still_reads(app):
    """`hand:<i>` is the lane at index i — a saved user preset with numbers
    works as it did, with or without the adapter's map."""
    r = rig()
    app.table.add(Binding("hand:9", "view.inst_amp", "position"))          # right.roll
    p = app.reg["view.inst_amp"]
    _roll(r, app)
    assert p.eff_norm == pytest.approx(0.75, abs=1e-3)
    assert app.router.describe(app.table.owner("view.inst_amp")) == "R roll positions"
    assert app.router.rest_of("hand:9") == app.router.rest_of("hand:right.roll") == 0.5
    router = Router(app.reg, Bindings([Binding("hand:1", "view.bright", "position")]))
    router.feed("hand", np.full(22, 0.25))                                 # no names published
    router.modulate()
    app.reg.apply()
    assert app.reg["view.bright"].eff_norm == pytest.approx(0.25)


def test_a_named_gate_opens_on_its_pinch(app):
    """`when: hand:right.pinch.index` opens on the right thumb-index pinch
    and on nothing else; a gate name the rig lacks holds the row shut."""
    r = rig()
    app.table.add(Binding("hand:right.y", "view.inst_amp", "position",
                          when="hand:right.pinch.index"))
    app.table.add(Binding("hand:right.roll", "view.bright", "position",
                          when="hand:left.pinch.index"))                   # the other hand's
    app.table.add(Binding("hand:right.pitch", "view.speed", "position",
                          when="hand:right.pinch.thumb"))                  # no such switch
    inst, bright, speed = (app.reg[k] for k in ("view.inst_amp", "view.bright", "view.speed"))
    inst.set_norm(0.5)
    wide = {"tips": (60.0, 60.0, 60.0, 60.0), "palm_w": 100.0}
    shut = {"tips": (10.0, 60.0, 60.0, 60.0), "palm_w": 100.0}
    run(r, 2, hand(pos=(0.0, 300.0, 0.0), **wide), router=app.router)
    _frame(app)
    assert not inst.modulated
    run(r, 2, hand(pos=(0.0, 300.0, 0.0), **shut), router=app.router)
    _frame(app)
    assert inst.eff_norm == pytest.approx(0.8, abs=1e-4) and inst.norm == pytest.approx(0.5)
    assert not bright.modulated and not speed.modulated
    row = app.table.owner("view.inst_amp")
    assert app.router.describe(row) == "R y positions while R ind"
    assert app.router.describe(app.table.owner("view.speed")) == (
        "R pitch positions while hand:right.pinch.thumb")
    assert app.router.address("hand", r.io.gate_lane("right", "index")) == (
        "hand:right.pinch.index")


def test_the_default_addresses_are_the_default_layouts():
    """The names a hand route is written with are the default layout's
    (`hands.default_addresses`, `DEFAULTS`' dofs)."""
    names = hands.default_addresses()
    assert names[:6] == [f"left.{a}" for a in hands.DEFAULTS["dofs"]]
    assert names[12:14] == ["left.present", "right.present"]
    assert names[14:22] == [f"{s}.pinch.{f}" for s in hands.SIDES for f in hands.PINCHES]


def test_the_routing_page_offers_and_writes_names(app):
    """The ROUTING page's source and gate combos offer the hand lanes by
    name — what a pick writes — and find an older numeric row's lane among
    them, so `hand:7` shows as the right height rather than a stray entry."""
    from hyperspace import ui_routing

    r = rig()
    run(r, 1, hand(), router=app.router)
    panel = NS(audio=NS(chain=NS(band_names=["sub", "bass"])))
    srcs = ui_routing._sources(panel, app.router)
    hand_srcs = [s for s, _ in srcs if s.startswith("hand:")]
    assert hand_srcs == [f"hand:{n}" for n in hands.default_addresses()]
    assert ("hand:right.roll", "hand R roll") in srcs
    gates = ui_routing._gates(app.router)
    assert gates[0] == ("hand:left.pinch.index", "L ind")
    assert gates[7] == ("hand:right.pinch.pinky", "R pin")
    assert gates[-1] == ("hand:right.grab", "R grab")       # then the grabs (plan 24 C5)
    addrs = [s for s, _ in srcs]
    assert ui_routing._at(app.router, addrs, "hand:7") == addrs.index("hand:right.y")
    assert ui_routing._at(app.router, addrs, "hand:right.nosuch") == -1
    assert ui_routing._at(app.router, [None, *(a for a, _ in gates)], "hand:18") == 5


def test_a_learn_knows_a_numbered_row_is_the_same_axis(app):
    """Review of PR #70: a preset saved with numbers keeps `hand:7`; a learn
    writes `hand:right.y`. Learn compares the lanes, not the strings: a
    learn onto the same param refreshes the gate with no Replace / Keep
    question, and a learn of the right height elsewhere moves the numbered
    row (one axis, one param)."""
    r = rig()
    run(r, 1, hand(), router=app.router)                          # the map published
    old = app.table.add(Binding("hand:7", "fx.mix", "position"))  # right.y, by number
    app.learn.arm("fx.mix")
    app.learn.learn_source("hand:right.y", when="hand:right.pinch.index")
    assert app.learn.pending is None and app.table.owner("fx.mix") is old
    assert old.when == "hand:right.pinch.index"                   # refreshed, not asked
    app.learn.arm("view.bright")
    app.learn.learn_source("hand:right.y")
    assert old not in app.table.bindings                          # moved: one axis, one param
    assert app.table.owner("view.bright").source == "hand:right.y"
    assert app.learn.last.endswith("(into the preset; moved from fx.mix)")
    # plan 18 WP3: the same holds whatever the numbered row's op — a
    # numbered push keeps its op and depth through a learn by name, and
    # moves like any other row of the axis
    push = app.table.add(Binding("hand:3", "view.speed", "push", 0.4))   # left.roll, by number
    app.learn.arm("view.speed")
    app.learn.learn_source("hand:left.roll", when="hand:left.pinch.index", centred=True)
    assert app.learn.pending is None and app.table.owner("view.speed") is push
    assert (push.op, push.value, push.when) == ("push", 0.4, "hand:left.pinch.index")
    app.learn.arm("camera.yaw")
    app.learn.learn_source("hand:left.roll", centred=True, depth=0.25)
    assert push not in app.table.bindings
    yaw = app.table.owner("camera.yaw")
    assert (yaw.source, yaw.op, yaw.value) == ("hand:left.roll", "push", 0.25)
    assert app.learn.last.endswith("(into the preset; moved from view.speed)")
    assert app.learn.same_source("hand:7", "hand:right.y")
    assert not app.learn.same_source("hand:right.nosuch", "hand:-1")
