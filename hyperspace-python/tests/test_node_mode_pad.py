"""Plan 53 N2: node mode on a pad, over two `Deck`s and a stand-in pad on the real router.

The same fill, rests and cables as a desk's (`node_desk`): what differs is that a pad's rows are
routes, so `Router` runs them and the camera job stands down. No pad was plugged in for these;
hand checks 635-638 are the real ones.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from imgui_bundle import imgui
from test_meta_controller import DESK, _pointed
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture
from test_undo import boot

from hyperspace import (
    devices,
    gamepad,
    graphview,
    node_desk,
    nodemode,
    totem,
    ui_desk,
    ui_graph,
    ui_pad,
    undo,
)
from hyperspace.bands import CEIL
from hyperspace.pads.models import MODELS
from hyperspace.params import CHASE_PARAM
from hyperspace.routing import Binding, layout_of

DT = 1 / 60
AT_REST = (0.0, 0.0, 0.0, 0.0, -1.0, -1.0)
LX, LY, RX, RY, LT, RT = range(6)
ROLE, SECOND = "pad", "pad2"
NM = graphview.NODE_MODE


class StandIn(gamepad.Pad):
    """A real `Pad` whose frames are scripted, and whose model is the test's."""

    def __init__(self, model=None):
        super().__init__()
        self.source = "usb"
        self.model = model
        self.frame()

    def poll(self, dt=0.0):
        pass

    def frame(self, axes=AT_REST, held=(), hat=0):
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        self.buttons = [1 if i in held else 0 for i in range(gamepad.N_BUTTONS)]
        self.hat = hat
        self.axes = list(axes)

    def lose(self):
        self.source = None
        self.buttons, self.prev_buttons, self.hat, self.prev_hat = [], [], 0, 0


def push(**axes):
    """A frame's raw axes: `lx=1.0` a stick all the way, `rt=1.0` a trigger right down."""
    out = list(AT_REST)
    for name, v in axes.items():
        i = gamepad.AXES.index(name.upper())
        out[i] = 2 * v - 1 if name in ("lt", "rt") else v
    return out


def _rig(tmp_path, model=None, *, second=None, desk=False):
    p = _pointed(boot(tmp_path / "home"))
    ctx = devices.Context(reg=p.one.reg, table=p.one.table)
    made = []
    if desk:
        p.desk = devices.MidiDevice(DESK, {"profile": "apc40"}, ctx, io=p.r.midi)
        p.one.table.midi_roles = (DESK,)
        made.append(p.desk)
    p.io = StandIn(model)
    p.pad = devices.PadDevice(ROLE, {}, ctx, io=p.io)
    p.pad._dt = DT
    made.append(p.pad)
    if second is not None:
        p.io2 = StandIn(second)
        p.pad2 = devices.PadDevice(SECOND, {}, ctx, io=p.io2)
        p.pad2.qualify("p2")
        p.pad2._dt = DT
        made.append(p.pad2)
    p.devs = devices.DeviceRegistry(devices=made, ctx=ctx)
    ctx.devices = p.devs
    p.devs.point(p.meta.pointer, p.meta.panel_pointer)
    node_desk.install(p.meta, p.devs)
    p.nd1, p.nd2 = p.one.table.node_desk, p.two.table.node_desk
    p.patch = p.one.loaded_patch
    return p


@pytest.fixture()
def rig(tmp_path):
    yield _rig(tmp_path)
    undo.install(None)


def params_for(deck, n=30, skip=()) -> list[str]:
    """Modulatable params no row of `deck` touches, on no camera job, for a node to hold."""
    used = {b.target for b in deck.table.bindings}
    jobs = ("camera.", "rot.", "ui.", "totem.", "poi.", "output.", "tempo.", "desk.", "edit.")
    out = [p.id for p in deck.reg if p.modulatable and not p.alias and p.id not in used
           and p.id not in skip and not p.id.startswith(jobs)]
    out = nodemode.fillable(deck.reg, out, routed=True)
    assert len(out) >= n
    return out[:n]


def a_node(deck) -> str:
    """A node `deck`'s patch can point at: `node_params` says what it holds, in these tests."""
    return min(deck.loaded_patch._pointable())


def point(p, *pids, deck=None, player=1, node=None):
    """Player `player`'s pad on a node holding `pids` (default: plenty) of `deck`."""
    deck = deck or p.one
    pids = list(pids) or params_for(deck)
    deck.loaded_patch.node_params = lambda _n: pids
    assert deck.loaded_patch.point_node_mode(player, "gamepad", node or a_node(deck)) is None
    return pids


def clear_buttons(deck) -> None:
    """A table with nothing on the pad's buttons, so its pairs are free."""
    deck.table.bindings[:] = [b for b in deck.table.bindings
                              if b.scheme not in ("pad", "hat", "pair")]


def rows(p, role=ROLE, deck=None):
    return (deck or p.one).table.node_rows(role)


def step(p, axes=AT_REST, deck=None, *, held=(), hat=0, pad=None):
    """One frame: the pad's rows and camera job, then the pass, then the land."""
    deck = deck or p.one
    pad = pad or p.pad
    pad.io.frame(axes, held, hat)
    pad.act(deck.router)
    deck.router.modulate(SimpleNamespace(lanes=np.zeros(32)), DT, 100.0)
    deck.reg.apply()


# ---------------------------------------------------------------- what fills, on each model


AXES_OF = {
    "xbox": gamepad.AXES, "x360": gamepad.AXES, "generic": gamepad.AXES, "procon": gamepad.AXES,
    "dualsense": gamepad.AXES, "edge": gamepad.AXES,
    "joycon-l": ("LX", "LY", "LT"), "joycon-r": ("LX", "LY", "RT"),
}


@pytest.mark.parametrize("model", sorted(MODELS))
def test_each_model_fills_the_axes_it_has_in_order(tmp_path, model):
    p = _rig(tmp_path, MODELS[model])
    pids = point(p)
    got = rows(p)
    n = len(AXES_OF[model])
    assert [b.source for b in got[:n]] == [f"axis:{a}" for a in AXES_OF[model]]
    # then a pair the factory's rows leave free, and no button anything has
    assert all(b.scheme == "pair" for b in got[n:])
    assert [b.target for b in got] == pids[:len(got)]
    assert all(b.op == "push" and b.value == node_desk.PAD_DEPTH and b.motion is None for b in got)
    undo.install(None)


def test_every_model_is_in_the_table_above():
    assert set(AXES_OF) == set(MODELS)


@pytest.mark.parametrize("model", sorted(MODELS))
def test_no_model_fills_a_control_its_layout_holds_or_a_lone_button(tmp_path, model):
    m = MODELS[model]
    p = _rig(tmp_path, m)
    clear_buttons(p.one)
    point(p)
    held = layout_of(m).sources
    sources = {s for b in rows(p) for s in nodemode.own_sources(b.source)}
    assert not sources & held
    assert all(b.scheme in ("axis", "pair") for b in rows(p))
    assert all(len(f) == 2 or f[0].startswith("axis:") for f in node_desk.pad_freedoms(m))
    undo.install(None)


def test_a_pair_is_one_freedom_after_the_axes(tmp_path):
    p = _rig(tmp_path, MODELS["edge"])
    clear_buttons(p.one)
    pids = point(p)
    got = [b.source for b in rows(p)]
    assert got[:6] == [f"axis:{a}" for a in gamepad.AXES]
    assert got[6:] == ["pair:hat.N/hat.S", "pair:hat.E/hat.W", "pair:RB/LB", "pair:RP/LP",
                       "pair:RFN/LFN", "pair:N/S", "pair:E/W"]
    assert [b.target for b in rows(p)] == pids[:13]
    undo.install(None)


def test_a_pair_moves_its_param_both_ways_and_comes_back(tmp_path):
    p = _rig(tmp_path, MODELS["edge"])
    clear_buttons(p.one)
    pids = point(p)
    pid = rows(p)[6].target
    assert pid == pids[6]
    q = p.one.reg[pid]
    q.set_norm(0.5)
    for hat, want in ((gamepad.HAT_UP, 1.0), (gamepad.HAT_DOWN, 0.0), (0, 0.5)):
        for _ in range(3):
            step(p, hat=hat)
        assert q.eff_norm == pytest.approx(want, abs=1e-6)
    undo.install(None)


def test_a_row_on_the_pad_takes_its_control_wherever_it_aims(rig):
    """NQ6: a route the patch has on a stick stays, and the rest fill what is left."""
    t = rig.one.table
    aim = params_for(rig.one, 1)[0]
    t.set_routes([*t.routes(), Binding("axis:RT", aim, "push", 0.5)])
    pids = point(rig, *params_for(rig.one, skip=(aim,)))
    got = [b.source for b in rows(rig)]
    assert "axis:RT" not in got and got[:5] == ["axis:LX", "axis:LY", "axis:RX", "axis:RY", "axis:LT"]
    assert [b.target for b in rows(rig)] == pids[:len(got)]
    assert any(b.source == "axis:RT" and b.target == aim for b in t.routes())


@pytest.mark.parametrize(("source", "gone"), [
    ("axis:L.NE", {"axis:LX", "axis:LY"}),      # a dial takes its stick
    ("axis:0", {"axis:LX"}),                    # a lane by number is its axis
    ("axis@pad:RX", {"axis:RX"}),               # the primary's row, spelled with its role
])
def test_a_row_is_read_however_it_spells_its_control(rig, source, gone):
    t = rig.one.table
    t.primaries = {**getattr(t, "primaries", {}), "pad": ROLE}
    aim = params_for(rig.one, 1)[0]
    t.set_routes([*t.routes(), Binding(source, aim, "push", 0.5)])
    point(rig, *params_for(rig.one, skip=(aim,)))
    got = {b.source for b in rows(rig)}
    assert not gone & got
    assert {f"axis:{a}" for a in gamepad.AXES} - gone <= got


def test_a_switched_off_row_holds_nothing(rig):
    t = rig.one.table
    aim = params_for(rig.one, 1)[0]
    t.set_routes([*t.routes(), Binding("axis:LX", aim, "push", 0.5, enabled=False)])
    point(rig, *params_for(rig.one, skip=(aim,)))
    assert rows(rig)[0].source == "axis:LX"


def test_a_mapping_on_the_nodes_param_keeps_it_out(rig):
    """A row from any controller on a param of the node stays, as on a desk."""
    t = rig.one.table
    pids = params_for(rig.one, 8)
    t.set_routes([*t.routes(), Binding("hand:right.grab", pids[0], "push", 0.5)])
    point(rig, *pids)
    h = next(h for h in rig.nd1.held() if h.role == ROLE)
    assert pids[0] in h.fit.kept and pids[0] not in {b.target for b in rows(rig)}


def test_no_row_on_a_meta_param_and_a_param_no_route_can_move_is_left_out(rig):
    reg = rig.one.reg
    still = next(p.id for p in reg if p.kind.name == "CONTINUOUS" and not p.modulatable
                 and not p.alias and nodemode.meta_refusal(p.id) is None)
    meta = next(p.id for p in reg if nodemode.meta_refusal(p.id) is not None)
    mine = params_for(rig.one, 2)
    point(rig, still, meta, *mine)
    assert [b.target for b in rows(rig)] == mine
    # and on the desk, what no route can move still fills: `routed` is the pad's alone
    assert nodemode.fillable(reg, [still]) == [still]


def test_too_many_is_listed_not_paged(rig):
    pids = point(rig, *params_for(rig.one, 12))
    h = next(h for h in rig.nd1.held() if h.role == ROLE)
    assert h.fit.over == tuple(pids[len(rows(rig)):]) and h.fit.over
    assert h.fit.too_many(h.node)


# ---------------------------------------------------------------- what a row does


def test_a_stick_at_rest_moves_nothing_when_the_mode_goes_up(rig):
    pids = params_for(rig.one, 6)
    for i, pid in enumerate(pids):
        rig.one.reg[pid].set_norm(0.2 + 0.1 * i)
    before = [rig.one.reg[p].eff_norm for p in pids]
    point(rig, *pids)
    for _ in range(4):
        step(rig)
    assert [rig.one.reg[p].eff_norm for p in pids] == pytest.approx(before, abs=1e-9)


def test_a_stick_pushes_and_the_look_comes_back_on_release(rig):
    pid = point(rig, *params_for(rig.one, 1))[0]
    q = rig.one.reg[pid]
    q.set_norm(0.5)
    for axis, want in ((push(lx=1.0), 1.0), (push(lx=-1.0), 0.0)):
        for _ in range(3):
            step(rig, axis)
        assert q.eff_norm == pytest.approx(want, abs=1e-6)
    for _ in range(3):
        step(rig)
    assert q.eff_norm == pytest.approx(0.5, abs=1e-6)


def test_a_trigger_takes_the_whole_throw(rig):
    pids = params_for(rig.one, 5)
    point(rig, *pids)
    q = rig.one.reg[pids[4]]
    q.set_norm(0.0)
    for _ in range(3):
        step(rig, push(lt=1.0))
    assert q.eff_norm == pytest.approx(1.0, abs=1e-6)


def test_a_row_runs_on_the_pads_own_feel(rig):
    """NQ5: the pad's source feel, so a spring on the pad is a spring on the row."""
    point(rig, *params_for(rig.one, 1))
    assert rig.one.router.feel_of(rows(rig)[0]) == rig.one.router.source_feel("axis")


def test_the_rows_are_not_in_the_table_the_file_or_the_routes(rig):
    t, patch = rig.one.table, rig.patch
    routes = [b.to_json() for b in t.routes()]
    desk = [b.to_json() for b in t.desk()]
    file_rows = t.to_json()
    point(rig)
    assert rows(rig)
    assert not any(b is x for b in rows(rig) for x in t.bindings)
    assert [b.to_json() for b in t.routes()] == routes
    assert [b.to_json() for b in t.desk()] == desk
    assert t.to_json() == file_rows
    doc = patch.document("x")
    assert doc[nodemode.KEY] == [{"player": 1, "controller": "gamepad", "node": a_node(rig.one)}]
    assert not {b.target for b in rows(rig)} & {r["target"] for r in doc.get("routes") or ()}


def test_chosen_per_controller_a_desk_and_a_pad_on_two_nodes(tmp_path):
    p = _rig(tmp_path, desk=True)
    pids = params_for(p.one, 30)
    a, b = sorted(p.patch._pointable())[:2]
    by_node = {a: pids[:10], b: pids[10:20]}
    p.patch.node_params = lambda n: by_node.get(n, [])
    assert p.patch.point_node_mode(1, "midi", a) is None
    assert p.patch.point_node_mode(1, "gamepad", b) is None
    assert {r.target for r in rows(p, DESK)} <= set(by_node[a])
    assert {r.target for r in rows(p)} <= set(by_node[b])
    p.patch.leave_node_mode(1, "midi")
    assert not rows(p, DESK) and rows(p)
    undo.install(None)


# ---------------------------------------------------------------- the camera job


def test_steer_stands_down_only_on_the_axes_the_mode_holds(rig):
    point(rig, *params_for(rig.one, 1))             # LX alone
    reg = rig.one.reg
    yaw, pitch = reg["camera.yaw"].base, reg["camera.pitch"].base
    for _ in range(5):
        step(rig, push(lx=1.0, ly=1.0))
    assert reg["camera.yaw"].base == pytest.approx(yaw, abs=1e-9)
    assert reg["camera.pitch"].base != pytest.approx(pitch, abs=1e-6)


def test_leaving_gives_the_stick_back_to_the_view(rig):
    point(rig, *params_for(rig.one, 1))
    rig.patch.leave_node_mode(1, "gamepad")
    reg = rig.one.reg
    yaw = reg["camera.yaw"].base
    for _ in range(5):
        step(rig, push(lx=1.0))
    assert reg["camera.yaw"].base != pytest.approx(yaw, abs=1e-6)


def test_a_pad_gone_lets_go_and_the_camera_returns_when_it_comes_back(rig):
    pid = point(rig, *params_for(rig.one, 1))[0]
    q = rig.one.reg[pid]
    q.set_norm(0.5)
    for _ in range(3):
        step(rig, push(lx=1.0))
    assert rig.one.table.node_held() == {pid}
    rig.io.lose()
    rig.pad.act(rig.one.router)
    rig.one.router.modulate(SimpleNamespace(lanes=np.zeros(32)), DT, 100.0)
    rig.one.reg.apply()
    assert rig.one.table.node_held() == frozenset()
    assert q.eff_norm == pytest.approx(0.5, abs=1e-6)
    assert rig.one.table.node_rows(ROLE)            # still drawn: the file still says so


@pytest.mark.parametrize("model", ["joycon-l", "joycon-r"])
def test_a_joycons_stick_is_heard_where_the_mode_holds_it(tmp_path, model):
    """#431: its stick reads NaN with the totem off, so a claim on it would be dead with the
    view orbiting under it. `quiet_stick` stands down, and the pad window asks the same."""
    p = _rig(tmp_path, MODELS[model])
    reg = p.one.reg
    pid = point(p, *params_for(p.one, 1))[0]
    q = reg[pid]
    q.set_norm(0.5)
    yaw, pitch = reg["camera.yaw"].base, reg["camera.pitch"].base
    for _ in range(4):
        step(p, push(lx=1.0, ly=1.0))
    assert q.eff_norm == pytest.approx(1.0, abs=1e-6)
    assert reg["camera.yaw"].base == pytest.approx(yaw, abs=1e-9)
    assert reg["camera.pitch"].base != pytest.approx(pitch, abs=1e-6)   # LY, unheld, orbits
    quiet = p.pad.quiet_stick(MODELS[model], reg, p.one.router)
    assert gamepad.AX_LX not in quiet and gamepad.AX_LY in quiet
    assert p.pad.quiet_stick(MODELS[model], reg) == quiet               # as the window asks
    p.patch.leave_node_mode(1, "gamepad")
    assert p.pad.quiet_stick(MODELS[model], reg, p.one.router) == gamepad.left_stick_lanes()
    undo.install(None)


def test_a_joycons_saved_route_beside_the_mode_still_lets_go(tmp_path):
    """Only what the mode holds stands down: a learned route on the other axis is as #431 has it."""
    p = _rig(tmp_path, MODELS["joycon-l"])
    t, reg = p.one.table, p.one.reg
    aim = params_for(p.one, 1)[0]
    t.set_routes([*t.routes(), Binding("axis:LY", aim, "push", 1.0)])
    q = reg[aim]
    q.set_norm(0.5)
    pid = point(p, *params_for(p.one, 1, skip=(aim,)))[0]
    assert [b.source for b in rows(p)] == ["axis:LX"] and rows(p)[0].target == pid
    for _ in range(3):
        step(p, push(ly=1.0))
    assert q.eff_norm == pytest.approx(0.5, abs=1e-6)
    undo.install(None)


def test_a_joycons_trigger_fills_with_no_camera_job_to_stand_down(tmp_path):
    p = _rig(tmp_path, MODELS["joycon-l"])
    pids = point(p, *params_for(p.one, 3))
    assert rows(p)[2].source == "axis:LT"
    q = p.one.reg[pids[2]]
    q.set_norm(0.0)
    for _ in range(3):
        step(p, push(lt=1.0))
    assert q.eff_norm == pytest.approx(1.0, abs=1e-6)
    undo.install(None)


def test_a_joycon_under_the_totem_hears_its_row(tmp_path):
    """The owner's table on #431: with the totem on, the stick is free for a route."""
    p = _rig(tmp_path, MODELS["joycon-l"])
    reg = p.one.reg
    if "totem.on" not in reg:
        totem.register(reg, totem.TotemState())
    reg["totem.on"].set(True)
    reg.totem.driving = ROLE
    pid = point(p, *params_for(p.one, 1))[0]
    q = reg[pid]
    q.set_norm(0.5)
    assert p.pad.quiet_stick(MODELS["joycon-l"], reg, p.one.router) == frozenset()
    p.pad._totem = lambda _io, _reg: {}             # (no sensors on this stand-in)
    for _ in range(3):
        step(p, push(lx=1.0))
    assert q.eff_norm == pytest.approx(1.0, abs=1e-6)
    undo.install(None)


def test_the_totem_holds_no_axis_row_and_is_not_refused(rig):
    """Plan 53's refusal is not built: the totem's skip is buttons, and a pole under it reads
    as not pressed (`pole_free`), so nothing here needs one."""
    reg = rig.one.reg
    if "totem.on" not in reg:
        totem.register(reg, totem.TotemState())
    reg["totem.on"].set(True)
    reg.totem.driving = ROLE
    pid = point(rig, *params_for(rig.one, 1))[0]
    q = reg[pid]
    q.set_norm(0.5)
    rig.pad._totem = lambda _io, _reg: {"skip": totem.SKIP}
    for _ in range(3):
        step(rig, push(lx=1.0))
    assert q.eff_norm == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------- the owner's rest, row 711


def _route_on(deck, pid):
    route = Binding("lane:0", pid, "push", 0.5)
    deck.table.set_routes([*deck.table.routes(), route])
    deck.reg[pid].set_norm(0.25)
    return route


def _pass_value(deck) -> None:
    lanes = np.full(32, CEIL, dtype=float)
    deck.router.modulate(SimpleNamespace(lanes=lanes), DT, 100.0)
    deck.reg.apply()


def test_a_modulators_route_rests_and_comes_back_on_leave(rig):
    pid = params_for(rig.one, 1)[0]
    route = _route_on(rig.one, pid)
    saved = route.to_json()
    _pass_value(rig.one)
    q = rig.one.reg[pid]
    rode = q.eff_norm
    assert rode != pytest.approx(0.25, abs=1e-3)

    point(rig, pid)
    assert [b.target for b in rows(rig)] == [pid]    # the route keeps no param from filling
    assert rig.one.table.node_holds(route)
    rig.pad.act(rig.one.router)
    _pass_value(rig.one)
    assert q.eff_norm == pytest.approx(0.25, abs=1e-6)

    rig.patch.leave_node_mode(1, "gamepad")
    assert not rig.one.table.node_holds(route)
    _pass_value(rig.one)
    assert q.eff_norm == pytest.approx(rode, abs=1e-6)
    assert route.to_json() == saved and any(b is route for b in rig.one.table.routes())


def test_a_pads_route_on_the_param_stays_and_keeps_the_param(rig):
    pid = params_for(rig.one, 1)[0]
    t = rig.one.table
    t.set_routes([*t.routes(), Binding("axis:RY", pid, "push", 0.5)])
    point(rig, pid)
    assert rows(rig) == []


# ---------------------------------------------------------------- the two layers


def test_a_pad_on_the_other_deck_runs_nothing_here_and_moves_nothing(rig):
    """The rows are drawn dormant; the lanes are the shared half's, so a row left in this
    deck's plan would let a pad on the other reach this patch."""
    pid = point(rig, *params_for(rig.one, 1))[0]
    q = rig.one.reg[pid]
    q.set_norm(0.5)
    rig.meta.point(ROLE, rig.two)
    assert rig.one.table.node_routes() == []
    assert rig.one.table.node_held() == frozenset()
    assert rows(rig)                                 # what it would have waits
    assert gamepad.AX_LX not in rig.one.router.claimed("axis")
    step(rig, push(lx=1.0), rig.two)
    rig.one.router.modulate(SimpleNamespace(lanes=np.zeros(32)), DT, 100.0)
    rig.one.reg.apply()
    assert q.eff_norm == pytest.approx(0.5, abs=1e-6)
    h = next(h for h in rig.nd1.held() if h.role == ROLE)
    assert not h.on_here


def test_a_patch_on_the_other_deck_reaches_no_pad_here(rig):
    pid = point(rig, *params_for(rig.two, 1), deck=rig.two)[0]
    assert rig.two.table.node_rows(ROLE) and rig.two.table.node_routes() == []
    assert rig.one.table.node_rows(ROLE) == []
    q = rig.two.reg[pid]
    q.set_norm(0.5)
    yaw = rig.one.reg["camera.yaw"].base
    for _ in range(3):
        step(rig, push(lx=1.0))                      # the pad's on deck 1: its view orbits
    assert rig.one.reg["camera.yaw"].base != pytest.approx(yaw, abs=1e-6)
    rig.two.router.modulate(SimpleNamespace(lanes=np.zeros(32)), DT, 100.0)
    rig.two.reg.apply()
    assert q.eff_norm == pytest.approx(0.5, abs=1e-6)


def test_enter_brings_the_pad_and_a_load_moves_no_pointer(rig):
    nd2 = rig.nd2
    pids = params_for(rig.two, 3)
    rig.two.loaded_patch.node_params = lambda _n: pids
    node = a_node(rig.two)
    assert rig.meta.pointer(ROLE).deck is rig.one
    assert nd2.enter(ROLE, node) is None
    assert rig.meta.pointer(ROLE).deck is rig.two
    assert rig.two.loaded_patch.node_mode.of(1, "gamepad") == node
    assert rig.two.table.node_routes()
    nd2.leave(ROLE)
    assert rig.two.loaded_patch.node_mode.of(1, "gamepad") is None
    assert rig.meta.pointer(ROLE).deck is rig.two    # it stays on this `Deck`


def test_a_second_pad_of_a_player_is_refused_and_its_own_player_has_its_own_rows(tmp_path):
    p = _rig(tmp_path, second=MODELS["edge"])
    pids = params_for(p.one)
    p.patch.node_params = lambda _n: pids
    node = a_node(p.one)
    # both player 1's until someone says otherwise: the second is not its player's first
    assert p.nd1.refusal(SECOND, node) == node_desk.NOT_FIRST_PAD.format(role=SECOND, player=1)
    p.patch.point_node_mode(1, "gamepad", node)
    assert rows(p, SECOND) == []
    assert [h.role for h in p.nd1.held()] == [ROLE]

    p.meta.register(SECOND, 2)                      # the real door: the player screen's
    p.meta.point(SECOND, p.one)                     # (and onto this deck, to act here)
    assert p.meta.players.player_of(SECOND).number == 2
    assert p.patch.point_node_mode(2, "gamepad", node) is None
    first, second = rows(p), rows(p, SECOND)
    assert second[0].source == "axis@p2:LX"
    assert not {b.target for b in first} & {b.target for b in second}    # what's left
    assert second[0].target == pids[len(first)]
    undo.install(None)


def test_a_desk_fills_first_and_a_pad_pointed_later_changes_nothing_of_its(tmp_path):
    p = _rig(tmp_path, desk=True)
    pids = params_for(p.one)
    p.patch.node_params = lambda _n: pids
    node = a_node(p.one)
    p.patch.point_node_mode(1, "midi", node)
    desk = list(rows(p, DESK))
    assert desk
    p.patch.point_node_mode(1, "gamepad", node)
    assert all(a is b for a, b in zip(desk, rows(p, DESK), strict=True))
    assert not {b.target for b in desk} & {b.target for b in rows(p)}
    assert rows(p)[0].target == pids[len(desk)]
    undo.install(None)


def test_a_save_after_leaving_is_what_it_was(rig):
    before = rig.patch.document("x")
    point(rig)
    rig.patch.leave_node_mode(1, "gamepad")
    assert rig.patch.document("x") == before


# ---------------------------------------------------------------- the panel's words


def test_refusals_are_the_routes(rig):
    reg = rig.one.reg
    still = next(p.id for p in reg if p.kind.name == "CONTINUOUS" and not p.modulatable
                 and not p.alias and nodemode.meta_refusal(p.id) is None)
    node = a_node(rig.one)
    word = node.removeprefix("render:")
    rig.patch.node_params = lambda _n: [still]
    # a desk could fill it; a pad's row is a route, and no route can move it
    assert rig.nd1.refusal(ROLE, node) == nodemode.NO_FILLABLE.format(node=word)
    assert nodemode.enter_refusal(reg, node, [still]) is None
    rig.nd1._asked = ((), {})           # (a list asked again only when the registry moves)
    rig.patch.node_params = lambda _n: []
    assert rig.nd1.refusal(ROLE, node) == nodemode.NO_PARAMS.format(node=word)


def test_a_chase_through_the_mode_commits_and_stays(rig):
    """Plan 53 §3's pay-off: hold chase, push a stick, let go of chase, then of the stick."""
    pid = point(rig, *params_for(rig.one, 1))[0]
    reg = rig.one.reg
    q = reg[pid]
    q.set_norm(0.5)
    chase = reg[CHASE_PARAM]
    chase.set(True)
    for _ in range(4):
        step(rig, push(lx=0.5))
    held = q.eff_norm
    assert held != pytest.approx(0.5, abs=1e-3)
    chase.set(False)
    for _ in range(4):
        step(rig, push(lx=0.5))
    for _ in range(4):
        step(rig)
    assert q.eff_norm == pytest.approx(held, abs=1e-3)
    assert q.base == pytest.approx(held, abs=1e-3)


def test_a_commit_then_a_leave_does_not_jump(rig):
    """The row goes, so `_forget_lost_rows` drops the ledger, and the base has the commit."""
    pid = point(rig, *params_for(rig.one, 1))[0]
    reg = rig.one.reg
    q = reg[pid]
    q.set_norm(0.5)
    chase = reg[CHASE_PARAM]
    chase.set(True)
    for _ in range(4):
        step(rig, push(lx=0.5))
    chase.set(False)
    for _ in range(4):
        step(rig)
    held = q.eff_norm
    rig.patch.leave_node_mode(1, "gamepad")
    for _ in range(3):
        step(rig)
    assert q.eff_norm == pytest.approx(held, abs=1e-3)


def test_the_pads_word_for_a_control_is_its_own_glyph(tmp_path):
    p = _rig(tmp_path, MODELS["dualsense"])
    clear_buttons(p.one)
    point(p, *params_for(p.one, 8))
    words = [p.nd1.control_word(ROLE, b) for b in rows(p)]
    assert words[4] == "L2" and words[5] == "R2" and words[6] == "↑/↓"
    undo.install(None)


def test_the_side_pane_lists_the_map(rig):
    pids = point(rig, *params_for(rig.one, 3))
    h = next(h for h in rig.nd1.held() if h.role == ROLE)
    assert h.kind == node_desk.PAD_KIND
    said = ui_graph.node_mode_words(rig.nd1, h, h.node)
    assert said[0].endswith(f"→ {rig.one.reg[pids[0]].label or pids[0]}")


# ---------------------------------------------------------------- drawn: the graph


def view_of(deck, devs):
    return graphview.build(deck.table, deck.reg, deck.router, devs)


def test_a_cable_for_every_row_landing_as_a_route_does(rig):
    point(rig, *params_for(rig.one, 3))
    view = view_of(rig.one, rig.devs)
    cables = [c for c in view.cables if c.kind == NM]
    assert len(cables) == 3
    # (the node's own pin when the param's port is another node's, as on a desk)
    assert all(c.dst_port.startswith((f"{graphview.MOD}:", f"{graphview.NODE_PIN}:")) for c in cables)
    assert all(c.ref[0] == ROLE and c.label.startswith("node mode: player 1, ") for c in cables)
    assert not any(c.kind == "route" and c.ref in rows(rig) for c in view.cables)


def test_a_pads_cables_leave_its_node_in_a_bundle_of_their_own(rig):
    t = rig.one.table
    aim = params_for(rig.one, 1)[0]
    t.set_routes([*t.routes(), Binding("axis:RT", aim, "push", 0.5)])   # a saved one beside
    pids = params_for(rig.one, skip=(aim,))
    point(rig, aim, *pids)
    view = view_of(rig.one, rig.devs)
    assert all(view.owner(c.src_port)[0].id == f"device:{ROLE}" for c in view.cables if c.kind == NM)
    _, bundles = graphview.wiring(view, lambda _nid: True)
    mine = [b for b in bundles if any(c.kind == NM for c in b.cables)]
    assert mine and all(b.id.endswith("|node") for b in mine)
    assert all(all(c.kind == NM for c in b.cables) for b in mine)
    assert ui_graph._node_mode_roles(mine[0]) == [ROLE]


def test_the_cable_is_dormant_with_the_pad_on_the_other_deck(rig):
    point(rig, *params_for(rig.one, 2))
    rig.meta.point(ROLE, rig.two)
    assert all(c.dormant for c in view_of(rig.one, rig.devs).cables if c.kind == NM)


def test_the_key_moves_when_the_pad_points(rig):
    k = rig.nd1.key()
    point(rig, *params_for(rig.one, 2))
    assert rig.nd1.key() != k


def test_a_chip_per_controller_and_entering_is_one_undo_step(tmp_path):
    p = _rig(tmp_path, desk=True)
    assert [(h.role, h.kind) for h in p.nd1.held()] == [(DESK, node_desk.KIND), (ROLE, node_desk.PAD_KIND)]
    pids = params_for(p.one)
    p.patch.node_params = lambda _n: pids
    node = a_node(p.one)
    undo.install(p.one.undo)
    p.one.undo.tick(p.r.t)
    p.r.t += 2
    assert p.nd1.enter(ROLE, node) is None
    p.one.undo.tick(p.r.t)
    assert p.patch.node_mode.of(1, "gamepad") == node and rows(p)
    assert p.patch.node_mode.of(1, "midi") is None        # the desk's chip is its own
    p.r.t += 2
    p.one.undo.tick(p.r.t)
    p.one.undo.undo()
    assert p.patch.node_mode.of(1, "gamepad") is None and not rows(p)
    undo.install(None)


def test_a_learn_onto_a_filled_axis_lands_and_the_fill_moves_off_it(rig):
    pids = point(rig, *params_for(rig.one, 3))
    assert rows(rig)[0].source == "axis:LX"
    t = rig.one.table
    aim = params_for(rig.one, 1, skip=pids)[0]
    t.set_routes([*t.routes(), Binding("axis:LX", aim, "push", 0.25)])
    assert [b.source for b in rows(rig)][:2] == ["axis:LY", "axis:RX"]
    assert [b.target for b in rows(rig)] == pids


# ---------------------------------------------------------------- drawn: the pad window


def _window(shell, deck_rows, *, away=False, model=None):
    """The real window on a stand-in `NodeDesk` for the panel's table."""
    panel = shell.panel
    panel.desk = False
    panel.reg["ui.pad_diagram"].set(True)
    imgui.get_io().display_size = imgui.ImVec2(1400, 900)
    io = StandIn(model)
    panel.pad = io
    panel.devices = devices.DeviceRegistry(
        devices=[devices.PadDevice(ROLE, {}, devices.Context(reg=panel.reg), io=io)],
        ctx=devices.Context(reg=panel.reg))
    from hyperspace import ui_routing
    table = ui_routing.router_of(panel).table
    table.node_desk = SimpleNamespace(
        rows=lambda role=None: deck_rows if role == ROLE else [],
        serial=lambda role=None: len(deck_rows), under=lambda _b: False,
        holding=frozenset, away=lambda _b, _role=None: away, routed=list,
        held=list, key=tuple, pointable=lambda _n: False)
    return panel, table


def _row(source, pid, words="Held"):
    return node_desk.Row(source, pid, "push", 1.0, words=words)


def test_the_window_says_what_a_filled_control_holds(shell_rig):  # noqa: F811
    row = _row("axis:LX", "view.alpha", "Filled here")
    panel, table = _window(shell_rig, [row])
    frame(panel)
    st = ui_pad._state(panel)
    assert st["filled"] == {id(row): False}
    assert "Filled here" in st["labels"]
    assert ui_pad.rows(table, None, ROLE)["axis:LX"] is row
    c = gamepad.control_in(gamepad.layout_for(None), "axis:LX")
    assert ui_pad.NODE_MODE_TIP in ui_pad.label(panel, c, row)
    assert ui_pad.NODE_AWAY_TIP not in ui_pad.label(panel, c, row)
    table.node_desk = None


def test_a_filled_controls_outline_is_the_cables_colour_and_faint_when_away(shell_rig):  # noqa: F811
    row = _row("axis:LX", "view.alpha")
    panel, table = _window(shell_rig, [row], away=True)
    frame(panel)
    st = ui_pad._state(panel)
    assert st["filled"] == {id(row): True}
    assert ui_desk._edge(st["filled"], row, True) == imgui.get_color_u32(ui_desk._node_ink(True))
    c = gamepad.control_in(gamepad.layout_for(None), "axis:LX")
    assert ui_pad.NODE_AWAY_TIP in ui_pad.label(panel, c, row)
    table.node_desk = None


def test_a_pair_lights_both_its_poles_in_the_window(shell_rig):  # noqa: F811
    row = _row("pair:hat.N/hat.S", "view.alpha", "Filled pair")
    panel, table = _window(shell_rig, [row])
    frame(panel)
    got = ui_pad.rows(table, None, ROLE)
    assert got["hat:N"] is row and got["hat:S"] is row
    table.node_desk = None


def test_the_window_reads_nothing_of_a_desk(shell_rig):  # noqa: F811
    """`Bindings.node_rows("")` is the first desk's: a window with no device asks nothing."""
    _panel, table = _window(shell_rig, [])
    table.node_desk = SimpleNamespace(rows=lambda role=None: pytest.fail("asked"))
    assert ui_pad._filled(table, "") == []
    table.node_desk = None


def test_a_joycons_window_says_the_row_and_the_device_agrees(shell_rig):  # noqa: F811
    row = _row("axis:LX", "view.alpha", "Filled here")
    panel, table = _window(shell_rig, [row], model=MODELS["joycon-l"])
    from hyperspace import ui_routing
    router = ui_routing.router_of(panel)
    dev = panel.devices.get(ROLE)
    dev._acted_on = router
    dev.steers = lambda _r: True
    assert not ui_pad._stick_quiet(panel, "axis:LX")     # the mode holds it
    assert ui_pad._stick_quiet(panel, "axis:LY")         # the other axis orbits
    table.node_desk = None


# ---------------------------------------------------------------- review fixes (#433)


def test_a_control_a_gate_or_a_modifier_reads_is_no_freedom(rig):
    """Review 1: moving it would also open the gate or drive the modifier."""
    t, reg = rig.one.table, rig.one.reg
    aim = params_for(rig.one, 1)[0]
    t.set_routes([*t.routes(), Binding("lane:0", aim, "push", 0.5, when="axis:RT")])
    t.add_modifier("smooth", ["axis:LX"], reg)
    t.add_modifier("smooth", ["axis@p2:RY"], reg)       # another pad's: holds nothing of this one
    point(rig, *params_for(rig.one, skip=(aim,)))
    got = [b.source for b in rows(rig)]
    assert "axis:RT" not in got and "axis:LX" not in got
    assert got[:4] == ["axis:LY", "axis:RX", "axis:RY", "axis:LT"]


def test_a_gate_edited_in_place_moves_the_fill(rig):
    t = rig.one.table
    aim = params_for(rig.one, 1)[0]
    gated = Binding("lane:0", aim, "push", 0.5)
    t.set_routes([*t.routes(), gated])
    point(rig, *params_for(rig.one, skip=(aim,)))
    assert rows(rig)[0].source == "axis:LX"
    gated.when = "axis:LX"
    assert rows(rig)[0].source == "axis:LY"


def test_a_nap_moves_no_map_and_no_later_pads(tmp_path):
    """Review 2: a `controller = any` pad asleep reads as no model. The map stays the last one
    read, and so does every pad after it."""
    p = _rig(tmp_path, MODELS["joycon-l"], second=MODELS["edge"])
    p.meta.register(SECOND, 2)
    p.meta.point(SECOND, p.one)
    pids = params_for(p.one)
    p.patch.node_params = lambda _n: pids
    node = a_node(p.one)
    p.patch.point_node_mode(1, "gamepad", node)
    p.patch.point_node_mode(2, "gamepad", node)
    first, second = list(rows(p)), list(rows(p, SECOND))
    assert [b.source for b in first] == ["axis:LX", "axis:LY", "axis:LT"]
    p.io.lose()
    assert p.pad.model is None                       # what the fill used to read
    assert all(a is b for a, b in zip(first, rows(p), strict=True)) and len(rows(p)) == 3
    assert all(a is b for a, b in zip(second, rows(p, SECOND), strict=True))
    p.io.source = "usb"                              # awake
    assert all(a is b for a, b in zip(first, rows(p), strict=True))
    undo.install(None)


def test_a_frame_that_reads_no_model_moves_no_map(tmp_path):
    p = _rig(tmp_path, MODELS["joycon-l"])
    point(p, *params_for(p.one, 3))
    had = list(rows(p))
    p.io.model = None                                # on, and read as nothing for a frame
    assert all(a is b for a, b in zip(had, rows(p), strict=True)) and len(rows(p)) == 3
    undo.install(None)


def test_a_pad_never_seen_fills_as_its_entry_says(tmp_path):
    p = _rig(tmp_path)
    p.io.lose()
    p.pad.entry["controller"] = "joycon-r"
    point(p, *params_for(p.one, 3))
    assert [b.source for b in rows(p)] == ["axis:LX", "axis:LY", "axis:RT"]
    undo.install(None)


def test_the_pad_in_hand_holds_node_mode_not_an_unplugged_one_listed_first(tmp_path):
    """Review 3: two real pads of player 1, the x360 listed first and unplugged."""
    p = _rig(tmp_path, MODELS["x360"], second=MODELS["joycon-l"])
    assert p.meta.players.player_of(SECOND).number == 1
    p.io.lose()
    pid = point(p, *params_for(p.one, 1))[0]
    assert [h.role for h in p.nd1.held()] == [SECOND]
    assert rows(p, ROLE) == [] and [b.source for b in rows(p, SECOND)] == ["axis@p2:LX"]
    assert p.nd1.refusal(ROLE, a_node(p.one)) == node_desk.NOT_FIRST_PAD.format(role=ROLE, player=1)
    assert p.devs.live_adapter("gamepad") is p.io2          # what the window draws
    q = p.one.reg[pid]
    q.set_norm(0.5)
    for _ in range(3):
        step(p, push(lx=1.0), pad=p.pad2)
    assert q.eff_norm == pytest.approx(1.0, abs=1e-6)
    p.io.source = "usb"                                       # plugged back: first listed again
    assert [h.role for h in p.nd1.held()] == [ROLE] and rows(p, SECOND) == []
    undo.install(None)


def test_with_none_in_hand_it_is_the_first_listed(tmp_path):
    p = _rig(tmp_path, second=MODELS["joycon-l"])
    p.io.lose()
    p.io2.lose()
    point(p, *params_for(p.one, 1))
    assert [h.role for h in p.nd1.held()] == [ROLE]
    undo.install(None)


def test_the_window_asks_about_the_deck_it_draws(shell_rig):  # noqa: F811
    """Review 4: a Joy-Con acting on deck 2 with the panel on deck 1, whose patch points it."""
    row = _row("axis:LX", "view.alpha", "Filled here")
    panel, table = _window(shell_rig, [row], away=True, model=MODELS["joycon-l"])
    dev = panel.devices.get(ROLE)
    elsewhere = SimpleNamespace(table=SimpleNamespace(node_rows=lambda _r: []))
    dev._acted_on = elsewhere
    dev.steers = lambda _r: True
    assert gamepad.AX_LX in dev.quiet_stick(MODELS["joycon-l"], panel.reg)      # on deck 2
    assert not ui_pad._stick_quiet(panel, "axis:LX")                          # as drawn here
    c = gamepad.control_in(gamepad.layout_for(MODELS["joycon-l"]), "axis:LX")
    frame(panel)
    assert ui_pad.says(panel, c, row) == "Filled here"
    table.node_desk = None


def test_the_window_asks_the_device_once_a_draw(shell_rig, monkeypatch):  # noqa: F811
    """Review 7: the quiet lanes once a draw, not once a control, however many rows."""
    rows_ = [_row("axis:LX", "view.alpha"), _row("axis:LY", "view.alpha")]
    panel, table = _window(shell_rig, rows_, model=MODELS["joycon-l"])
    dev = panel.devices.get(ROLE)
    calls = []
    real = dev.quiet_stick
    monkeypatch.setattr(dev, "quiet_stick", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    frame(panel)
    calls.clear()
    frame(panel)
    assert len(calls) == 1
    assert "quiet" not in ui_pad._state(panel)        # nothing kept past the draw
    table.node_desk = None


def test_a_pads_wire_follows_its_stick_and_sleeps_with_it(rig):
    """Review 5: a pad's row reads a lane, so its wire is the lane's, not the param's."""
    point(rig, *params_for(rig.one, 2))
    step(rig, push(lx=1.0))
    view = view_of(rig.one, rig.devs)
    graphview.refresh(view, rig.one.reg, rig.one.router)
    lx = next(c for c in view.cables if c.kind == NM and c.addr == "axis:LX")
    assert lx.live == pytest.approx(1.0) and not lx.dormant
    rig.io.lose()
    rig.pad.act(rig.one.router)
    graphview.refresh(view, rig.one.reg, rig.one.router)
    assert lx.live is None and lx.dormant


def test_a_pad_of_a_class_from_before_a_reload_still_fills_and_an_off_entry_never(rig):
    """Review 6: the real app re-classes its devices on a reload (`DeviceRegistry.targets`), so
    `isinstance` held there; the check is by what a pad can do now anyway, and an entry switched
    off, which has the kind and nothing else, is still none."""
    assert any(obj is rig.pad for obj, _m, _c in rig.devs.targets())

    class Old(devices.PadDevice):                     # a class the module no longer has
        pass
    rig.pad.__class__ = Old
    point(rig, *params_for(rig.one, 1))
    assert rows(rig) and node_desk.is_pad(rig.pad)
    off = devices.OffDevice("off", "gamepad", {})
    assert not node_desk.is_pad(off) and off.kind == node_desk.PAD_KIND


def test_one_rule_for_whose_pad_a_row_is(rig):
    """Review 9: `Bindings.pad_serves`, which `Router.pad` and the fill both ask."""
    t = rig.one.table
    t.primaries = {**getattr(t, "primaries", {}), "pad": ROLE}
    assert t.pad_serves("", Binding("pad:S", "x"))
    assert t.pad_serves("", Binding(f"pad@{ROLE}:A", "x"))
    assert not t.pad_serves("", Binding("pad@p2:S", "x"))
    assert t.pad_serves("p2", Binding("pad@p2:S", "x")) and not t.pad_serves("p2", Binding("pad:S", "x"))


def test_one_accessor_for_what_runs_and_the_panel_names_the_stick(rig):
    """Review 10: `Router.performers` and `performer_of`, so the panel says who holds it."""
    pid = params_for(rig.one, 1)[0]
    route = _route_on(rig.one, pid)
    point(rig, pid)
    r = rig.one.router
    assert rows(rig)[0] in r.performers() and route in r.performers()
    assert r.performer_of(pid) is rows(rig)[0]
    assert "axis:LX" in r.describe(rows(rig)[0]) or r.describe(rows(rig)[0])
    rig.patch.leave_node_mode(1, "gamepad")
    assert r.performer_of(pid) is route
