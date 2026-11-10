"""Node mode on the hands (the Leap): the pad's road, with the hand axes as the freedoms.

A stand-in tracker on the real `HandsIO` and the real router, over two `Deck`s. No Leap was
plugged in for these.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from test_meta_controller import _pointed
from test_node_mode_pad import StandIn, a_node, params_for, view_of
from test_undo import boot

from hyperspace import devices, graphview, node_desk, ui_graph, undo
from hyperspace.hands import HandSettings, HandsIO
from hyperspace.routing import Binding

DT = 1 / 60
ROLE = "leap"
SETTINGS = HandSettings.from_config({})
AXES = tuple(a.name for a in SETTINGS.axes)       # "left.x" … "right.yaw"


class Tracker:
    """A tracker that is connected and sees no hand: the lanes are the test's."""

    status, on = "tracking", True

    def latest(self):
        return 0, 0.0, {}, {}


def _rig(tmp_path, *, pad=False):
    p = _pointed(boot(tmp_path / "home"))
    ctx = devices.Context(reg=p.one.reg, table=p.one.table, hand_settings=SETTINGS)
    made = []
    if pad:
        p.pad = devices.PadDevice("pad", {}, ctx, io=StandIn())
        made.append(p.pad)
    p.io = HandsIO(SETTINGS, {"out": ""}, source=Tracker())
    p.hands = devices.HandsDevice(ROLE, {}, ctx, io=p.io)
    made.append(p.hands)
    p.devs = devices.DeviceRegistry(devices=made, ctx=ctx)
    ctx.devices = p.devs
    p.devs.point(p.meta.pointer, p.meta.panel_pointer)
    node_desk.install(p.meta, p.devs)
    for deck in (p.one, p.two):     # nothing on the hand lanes, so every axis is free
        t = deck.table
        t.bindings[:] = [b for b in t.bindings
                         if b.scheme not in ("hand", "hands") and (b.when or "")[:4] != "hand"]
    p.nd1, p.nd2 = p.one.table.node_desk, p.two.table.node_desk
    return p


@pytest.fixture()
def rig(tmp_path):
    yield _rig(tmp_path)
    undo.install(None)


def point(p, *pids, deck=None, kind="hands", node=None):
    deck = deck or p.one
    pids = list(pids) or params_for(deck)
    deck.loaded_patch.node_params = lambda _n: pids
    assert deck.loaded_patch.point_node_mode(1, kind, node or a_node(deck)) is None
    return pids


def rows(p, role=ROLE, deck=None):
    return (deck or p.one).table.node_rows(role)


def step(p, lanes=None, deck=None):
    """One frame: the hands' lanes (default: at rest), then the pass, then the land."""
    deck = deck or p.one
    r = deck.router
    p.io._publish(r)
    vec = list(p.io.rests()) if lanes is None else lanes
    r.feed("hand", vec)
    r.modulate(SimpleNamespace(lanes=np.zeros(32)), DT, 100.0)
    deck.reg.apply()


def lanes(**at):
    """The rests, with axis `left_roll=1.0` and so on moved."""
    out = list(HandsIO(SETTINGS, {"out": ""}, source=Tracker()).rests())
    for name, v in at.items():
        out[AXES.index(name.replace("_", "."))] = v
    return out


def test_the_hands_are_a_controller_a_patch_can_point(rig):
    held = rig.nd1.held()
    assert [(h.role, h.kind) for h in held] == [(ROLE, "hands")]
    node = a_node(rig.one)
    rig.one.loaded_patch.node_params = lambda _n: params_for(rig.one)
    assert rig.nd1.refusal(ROLE, node) is None
    assert rig.nd1.enter(ROLE, node) is None
    assert rig.one.loaded_patch.node_mode.of(1, "hands") == node


def test_the_hand_axes_fill_in_lane_order_as_pushes(rig):
    pids = point(rig)
    got = rows(rig)
    assert [b.source for b in got] == [f"hand:{a}" for a in AXES]
    assert [b.target for b in got] == pids[:len(AXES)]
    assert all(b.op == "push" and b.value == node_desk.HAND_DEPTH for b in got)


def test_too_many_is_listed_not_paged(rig):
    pids = point(rig)
    fit = rig.nd1.held()[0].fit
    assert fit.over == tuple(pids[len(AXES):])


def test_an_axis_a_row_reads_is_no_freedom(rig):
    t = rig.one.table
    aim = params_for(rig.one, 1)[0]
    t.set_routes([*t.routes(), Binding("hand:left.roll", aim, "push", 0.5)])
    point(rig, *params_for(rig.one, skip=(aim,)))
    got = [b.source for b in rows(rig)]
    assert "hand:left.roll" not in got
    assert len(got) == len(AXES) - 1


def test_a_hand_at_rest_moves_nothing_and_a_roll_pushes(rig):
    pids = point(rig)
    roll = AXES.index("right.roll")
    q = rig.one.reg[pids[roll]]
    q.set_norm(0.5)
    for _ in range(3):
        step(rig)
    assert q.eff_norm == pytest.approx(0.5, abs=1e-6)
    for _ in range(120):
        step(rig, lanes(right_roll=1.0))
    assert q.eff_norm > 0.9
    for _ in range(120):
        step(rig)
    assert q.eff_norm == pytest.approx(0.5, abs=1e-3)


def test_the_rows_are_routes_run_here_and_in_no_file(rig):
    point(rig)
    assert rig.one.table.node_routes() == rows(rig)
    assert not any(b.source.startswith("hand:") and b in rig.one.table.bindings for b in rows(rig))
    assert rig.nd1.holding() == {b.target for b in rows(rig)}


def test_a_pad_fills_first_and_the_hands_take_what_is_left(tmp_path):
    p = _rig(tmp_path, pad=True)
    pids = params_for(p.one)
    point(p, *pids, kind="gamepad")
    point(p, *pids)
    pad_targets = [b.target for b in rows(p, "pad")]
    hand_targets = [b.target for b in rows(p)]
    assert pad_targets and hand_targets
    assert not set(pad_targets) & set(hand_targets)
    undo.install(None)


def test_leaving_drops_the_rows(rig):
    point(rig)
    assert rows(rig)
    rig.nd1.leave(ROLE)
    assert rows(rig) == [] and rig.one.table.node_routes() == []


def test_the_word_for_a_control_is_the_lanes_label(rig):
    point(rig)
    b = rows(rig)[0]
    labels = {p.name: p.label for p in rig.hands.sources}
    assert rig.nd1.control_word(ROLE, b) == labels[AXES[0]]


def test_the_chip_says_what_the_hands_fill():
    assert ui_graph.FILLS["hands"] == "hand axes"


def test_a_cable_for_every_row(rig):
    point(rig, *params_for(rig.one, 3))
    view = view_of(rig.one, rig.devs)
    cables = [c for c in view.cables if c.kind == graphview.NODE_MODE]
    assert len(cables) == 3
    assert all(c.ref[0] == ROLE and c.addr.startswith("hand:") for c in cables), [(c.ref[0], c.addr) for c in cables]
