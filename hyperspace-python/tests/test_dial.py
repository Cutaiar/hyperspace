"""The sticks as dials (gamepad.dial, a prototype): a stick's angle picks
one of eight sectors clockwise from straight up, its distance from centre
is how far that sector's `axis` lane reads — petal (hard sectors, a sticky
border) or blend (neighbours crossfade) — and a route on a dial lane plays
like any other `axis` route, taking its whole stick off the camera job."""

import math

import pytest
from conftest import seed
from test_pad_learn import ScriptedPad, rig  # noqa: F401 — the fixture, re-exported
from test_routing import rig as full_rig

import hyperspace.gamepad as gp
from hyperspace import app
from hyperspace.params import Registry
from hyperspace.preset import Presets
from hyperspace.routing import Binding, Bindings, Router


def at(deg: float, r: float = 1.0) -> tuple[float, float]:
    """(x, y) — right and up — of a stick `deg` clockwise from straight up."""
    t = math.radians(deg)
    return r * math.sin(t), r * math.cos(t)


def lane(name: str) -> int:
    return gp.LANES.index(name)


# ---- the clock ----

def test_at_rest_every_lane_is_zero():
    for mode in gp.DIAL_MODES:
        assert gp.dial(0.0, 0.0, mode) == ([0.0] * gp.DIAL, None)
        assert gp.dial(*at(30, gp.DEADZONE * 0.9), mode) == ([0.0] * gp.DIAL, None)


def test_sectors_run_clockwise_from_straight_up():
    for k, deg in enumerate(range(0, 360, 45)):
        vals, sector = gp.dial(*at(deg), "petal")
        assert sector == k and vals[k] == pytest.approx(1.0), gp.COMPASS[k]
    assert gp.COMPASS[gp.dial(1.0, 0.0)[1]] == "E"         # right is three o'clock


def test_the_radius_runs_zero_to_one_past_the_deadzone_and_stops_at_the_rim():
    half = gp.DEADZONE + 0.5 * (1 - gp.DEADZONE)
    assert gp.dial(*at(0, half))[0][0] == pytest.approx(0.5)
    assert gp.dial(1.0, 1.0)[0][1] == pytest.approx(1.0)    # a square gate's corner


def test_petal_gives_the_whole_push_to_one_sector():
    vals, sector = gp.dial(*at(60, 0.8), "petal")
    assert sector == 1 and [v > 0 for v in vals].count(True) == 1


def test_a_petal_border_is_sticky():
    """22.5° is the border between N and NE: held on N, a stick a little
    past it stays N, one well past it is NE — and NE is as sticky back."""
    assert gp.dial(*at(25), "petal", held=0)[1] == 0
    assert gp.dial(*at(25), "petal", held=None)[1] == 1
    assert gp.dial(*at(35), "petal", held=0)[1] == 1
    assert gp.dial(*at(20), "petal", held=1)[1] == 1
    assert gp.dial(*at(-25), "petal", held=0)[1] == 0      # and across the wrap
    assert gp.dial(*at(-35), "petal", held=0)[1] == 7


def test_blend_crossfades_neighbours_and_sums_to_the_radius():
    vals, _ = gp.dial(*at(0), "blend")
    assert vals[0] == pytest.approx(1.0) and sum(vals) == pytest.approx(1.0)
    vals, _ = gp.dial(*at(22.5), "blend")                    # halfway N → NE
    assert vals[0] == pytest.approx(0.5) and vals[1] == pytest.approx(0.5)
    vals, _ = gp.dial(*at(-11.25, 0.6), "blend")             # a quarter into NW
    assert vals[0] > vals[7] > 0 and sum(vals) == pytest.approx(gp.dial(*at(0, 0.6))[0][0])


# ---- the pad ----

def test_the_dial_lanes_follow_the_axes():
    pad = ScriptedPad()
    pad.frame(axes=[0.0, -1.0, 1.0, 0.0, -1.0, -1.0])      # left up, right to the right
    lanes = pad.lanes()
    assert len(lanes) == len(gp.LANES) == len(gp.LANE_RESTS) == len(gp.LANE_LABELS)
    assert lanes[lane("L.N")] == pytest.approx(1.0) and lanes[lane("R.E")] == pytest.approx(1.0)
    assert sum(lanes[6:]) == pytest.approx(2.0)
    pad.frame()
    assert pad.lanes()[6:] == [0.0] * len(gp.DIAL_LANES)


def test_the_mode_is_per_stick():
    pad = ScriptedPad()
    pad.dial_modes = {"L": "blend", "R": "petal"}
    x, y = at(22.5)
    pad.frame(axes=[x, -y, x, -y, -1.0, -1.0])
    lanes = pad.lanes()
    assert lanes[lane("L.N")] == pytest.approx(0.5)          # blend: shared
    assert {lanes[lane("R.N")], lanes[lane("R.NE")]} == {0.0, 1.0}   # petal: one


def test_a_dial_lane_claims_its_whole_stick():
    assert gp.claims({lane("L.SW")}) == {gp.AX_LX, gp.AX_LY}
    assert gp.claims({lane("R.N"), gp.AX_LT}) == {gp.AX_RX, gp.AX_RY, gp.AX_LT}
    assert gp.dialed({lane("R.N"), gp.AX_LX}) == {"R"}


# ---- routes and learn ----

def test_a_dial_route_pushes_its_param_from_the_base(rig):  # noqa: F811
    pad, r = ScriptedPad(), rig.router
    gp.publish(r)                    # the pad's lane names (the pad device does it first)
    rig.table.add(Binding("axis:L.E", "view.inst_amp", "push", 1.0))
    assert gp.claims(r.claimed("axis")) == {gp.AX_LX, gp.AX_LY}
    assert r.describe(rig.table.owner("view.inst_amp")).startswith("left dial E")
    amp = rig.reg["view.inst_amp"]
    base = amp.value
    pad.frame()
    r.pad(pad)
    r.modulate()
    rig.reg.apply()
    assert amp.value == pytest.approx(base)                  # at rest: the base
    pad.frame(axes=[0.5 + 0.5 * gp.DEADZONE, 0.0, 0.0, 0.0, -1.0, -1.0])   # halfway right
    r.pad(pad)
    r.modulate()
    rig.reg.apply()
    assert amp.value == pytest.approx(base + 0.5 * (amp.hi - amp.lo))


def test_a_dialed_stick_learns_the_sector_it_points_into(rig):  # noqa: F811
    pad, lrn = ScriptedPad(), rig.learn
    pad.frame()
    lrn.arm("view.inst_amp", "pad")
    x, y = at(135)
    pad.frame(axes=[x, -y, 0.0, 0.0, -1.0, -1.0])            # down-right
    gp.learn_from(pad, lrn, dials=lambda: {"L"})
    assert [(b.source, b.target) for b in rig.table.routes()] == [("axis:L.SE", "view.inst_amp")]


def test_a_stick_that_is_no_dial_still_learns_its_axis(rig):  # noqa: F811
    pad, lrn = ScriptedPad(), rig.learn
    pad.frame()
    lrn.arm("view.inst_amp", "pad")
    pad.frame(axes=[1.0, 0.0, 0.0, 0.0, -1.0, -1.0])
    gp.learn_from(pad, lrn)
    assert [b.source for b in rig.table.routes()] == ["axis:LX"]


def test_the_dial_preset_fills_both_clocks(tmp_path):
    seed(tmp_path)                        # the corpus: DIAL among the shipped presets
    r = full_rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings())
    assert Presets(r.lib, r.reg, router).load("DIAL") == []
    assert router.table.dropped == []
    dialed = {b.source for b in router.table.routes() if b.scheme == "axis"}
    assert dialed == {f"axis:{n}" for n in gp.DIAL_LANES}
    assert router.table.owner("fx.wobble.speed").source == "axis:L.N"
    assert router.table.owner("fx.wobble.amount").source == "axis:L.NE"


# ---- the session params ----

def test_the_readings_are_session_params_and_swap():
    reg, pad = Registry(), gp.Pad()
    app._register_dial(reg, pad)
    assert pad.dial_modes == gp.DIAL_DEFAULT
    reg["desk.pad.dial.left"].set(1)
    assert pad.dial_modes["L"] == "blend"
    reg["desk.pad.dial.swap"].fire()
    assert pad.dial_modes == {"L": "blend", "R": "blend"}
    reg["desk.pad.dial.right"].set(0)
    reg["desk.pad.dial.swap"].fire()
    assert pad.dial_modes == {"L": "petal", "R": "blend"}
    assert not reg["desk.pad.dial.left"].persist


def test_config_picks_where_each_stick_starts():
    """The gamepad entry's `dial_left` / `dial_right` (plan 27's
    [[devices]]; the old [gamepad] table's keys translate) set where each
    stick's reading starts; a value that is no reading leaves the default."""
    from hyperspace import config, devices

    entry = {"role": "pad", "kind": "gamepad", **config._kind_defaults("gamepad"),
             "dial_left": "blend", "dial_right": "nonsense"}
    dev = devices.make(entry)
    dev.open()
    try:
        assert dev.io.dial_modes == {"L": "blend", "R": "blend"}
    finally:
        dev.close()
    assert config._kind_defaults("gamepad")["dial_left"] == "petal"


def test_the_readings_follow_the_current_pad():
    """In the app the readings sit on whichever pad is the primary now
    (the device registry may replace it on a config edit): a callable."""
    reg, pads = Registry(), [gp.Pad()]
    app._register_dial(reg, lambda: pads[-1])
    reg["desk.pad.dial.left"].set(1)
    pads.append(gp.Pad())
    assert reg["desk.pad.dial.left"].value == 0          # the new pad's own reading
    reg["desk.pad.dial.swap"].fire()
    assert pads[-1].dial_modes == {"L": "blend", "R": "petal"} and pads[0].dial_modes["L"] == "blend"


# ---- the panel ----

def test_the_system_page_draws_both_clocks(tmp_path, monkeypatch):
    from test_ui_shell import build_rig, frame

    from hyperspace.ui import Panel
    faces = []
    draw = Panel._dial
    monkeypatch.setattr(Panel, "_dial", lambda self, vals, names, *a:
                        faces.append((list(vals), names)) or draw(self, vals, names, *a))
    with build_rig(tmp_path) as r:
        pad = ScriptedPad()
        r.panel.pad = pad
        app._register_dial(r.reg, pad)
        frame(r.panel, "system")                 # no dial routes: the hint
        assert [k for k in Presets(r.lib, r.reg, r.router).load("DIAL")
                if not k.startswith(("env.", "seq."))] == []  # (plan 36 T3: the `/7`'s envelope ids, this rig has none)
        x, y = at(100)
        pad.frame(axes=[x, -y, -x, y, -1.0, -1.0])
        for _ in range(2):
            frame(r.panel, "system")
        left, right = faces[-2:]
        assert left[1][0] == "Wobble speed" and right[1][0] == "4D depth"
        assert left[0][2] > 0 and right[0][6] > 0   # 100°: E on the left, W on the right
        pad.source = None                        # unplugged: empty faces
        frame(r.panel, "system")
        assert faces[-1][0] == [0.0] * gp.DIAL


def test_picking_a_reading_on_the_panel_sets_it(tmp_path, monkeypatch):
    """The readings, and the stick feel above them, are enums: the panel
    offers their choices, and picking one sets it — it once drew them as
    sliders, whose write (`set_value`) an enum refuses with a TypeError."""
    from imgui_bundle import imgui
    from test_ui_shell import build_rig, frame

    pick = {"desk.pad.dial.left": 1, "desk.pad.dial.right": 0, "desk.pad.feel": 2}

    def chosen(label, cur, *a, **kw):
        pid = label.rpartition("##")[2]
        return (pid in pick, pick.get(pid, cur))

    def slid(label, v, *a, **kw):
        return (label.rpartition("##")[2] in pick, 1.0)

    monkeypatch.setattr(imgui, "combo", chosen)
    monkeypatch.setattr(imgui, "slider_float", slid)
    with build_rig(tmp_path) as r:
        pad = ScriptedPad()
        r.panel.pad = pad
        app._register_dial(r.reg, pad)
        frame(r.panel, "system")
        assert pad.dial_modes == {"L": "blend", "R": "petal"}
        assert r.reg["desk.pad.feel"].text() == "spring"
