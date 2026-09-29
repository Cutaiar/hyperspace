"""Hand routes addressed by name (plan 13 WP5b, decision register row 20,
audit N7): ``hand:right.roll`` reads the right roll wherever `[hands] dofs`
puts it; a name the rig lacks is dormant, never another lane; ``hand:<i>``
still reads the lane at index i."""

import math

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


def test_the_default_addresses_are_the_generators():
    """The names the factory generator and the migration write are the
    default layout's (`hands.default_addresses`, `DEFAULTS`' dofs)."""
    names = hands.default_addresses()
    assert names[:6] == [f"left.{a}" for a in hands.DEFAULTS["dofs"]]
    assert names[12:14] == ["left.present", "right.present"]
    assert names[14:] == [f"{s}.pinch.{f}" for s in hands.SIDES for f in hands.PINCHES]
