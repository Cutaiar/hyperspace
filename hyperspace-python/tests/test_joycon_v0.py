"""Version 0 of the Joy-Con (the owner, 2026-11-04): its buttons and stick, the
gyro and shake, with its sensors moving no position, and every other pad as it
was. Real bytes from the owner's tapes (`joycon-bt-excerpt.jsonl`,
`joycon-v0-moves.jsonl`)."""

import dataclasses
import json
import math
from pathlib import Path

import pytest
import test_pads_joycon_real as real
from test_pads_nintendo import joycon_pad
from test_poi import rig as poi_rig
from test_totem import DT, FakePad, ShimRouter, phase
from test_totem import rig as totem_rig

from hyperspace import gamepad, params, poi, routing, totem
from hyperspace.devices import Context, PadDevice
from hyperspace.pads import gesture, hid, models, nintendo

HERE = Path(__file__).resolve().parent
TAPE = HERE / "fixtures" / "pads" / "joycon-v0-moves.jsonl"
FINDINGS = HERE.parent / "docs" / "plans" / "assets" / "46-joycon" / "joycon-findings.json"
amap = nintendo.AXIS_MAP
JOYCON, EDGE = models.MODELS["joycon-l"], models.MODELS["edge"]


def calibration(offset_counts=0):
    found = json.loads(FINDINGS.read_text())
    records = {int(a, 16): bytes.fromhex(h) for a, h in found["flash"].items()}
    cal = nintendo.calibration(records, "l")
    if offset_counts:     # a pad whose rest reads off: the flash's origin is that far wrong
        gyro = tuple((o - offset_counts, s) for o, s in cal.gyro)
        cal = nintendo.Calibration(cal.left, cal.right, gyro, cal.accel, cal.nominal, cal.user_stick)
    return cal


def windows():
    rows = [json.loads(ln) for ln in TAPE.read_text().splitlines() if ln.strip()]
    out, name = {}, None
    for d in rows[1:]:
        if "note" in d:
            name = d["note"]
            out[name] = []
        else:
            out[name].append((d["t"], bytes.fromhex(d["r"])))
    return out


def turned(reports, cal, turn):
    """The reader's turn over `reports`, degrees about the sensor's axes."""
    total = [0.0, 0.0, 0.0]
    for t, r in reports:
        samples = nintendo.gyro_of(r, None)
        if samples is not None:
            turn.add(samples, t, cal, nintendo.report_clock(r))
        got, _ = turn.take()
        total = [a + b for a, b in zip(total, got, strict=True)]
    return total


def shakes_of(reports, cal):
    m, last, fired = gesture.Motion(), None, []
    for t, r in reports:
        f = nintendo.decode(r, "l", cal)
        if f is None or not f.full:
            continue
        dt = 0.0 if last is None else min(0.25, t - last)
        last = t
        m.step(amap.pick(cal.gyro_dps(f.gyro), amap.gyro), amap.pick(cal.accel_g(f.accel), amap.accel), dt)
        if m.shake:
            fired.append(t)
    return fired


def driven(name, totem_on=False):
    """One of the owner's button and stick recordings through the real pad
    and the pad device, as a frame runs them: the registry, the buttons seen
    down, the rows' last keywords."""
    reg, _, _ = totem_rig()
    pad, reader = joycon_pad()
    reader.calibration = real.calibration()
    dev = PadDevice("joy", {}, Context(reg=reg), io=pad)
    dev._dt = DT
    router = ShimRouter(reg)
    reg["totem.on"].set(totem_on)
    down: set[str] = set()
    for _t, r in real.windows()[name]:
        reader._take(r)
        pad.poll(dt=DT)
        down |= {n for n, code in pad.buttons_named.items() if pad.down(code)}
        dev.act(router)
    return reg, down, router.calls[-1]


# ---------------------------------------------------------------- buttons and the stick

@pytest.mark.parametrize("button", ["A", "Y", "B", "X", "LP", "RP", "LB", "VIEW", "SHARE", "LSTICK"])
def test_every_real_button_press_reaches_the_pad(button):
    _, down, _ = driven(button)
    assert button in down


def test_the_real_stick_orbits_the_view_with_the_totem_off_and_zl_is_free():
    reg, _, _ = driven("rest")
    assert reg["camera.yaw"].base == pytest.approx(0.0, abs=1e-3)      # at rest: nothing
    assert reg["camera.pitch"].base == pytest.approx(0.0, abs=1e-3)
    reg, _, _ = driven("stick right")
    assert abs(reg["camera.yaw"].base) > 1e-3
    reg, _, _ = driven("stick up")
    assert abs(reg["camera.pitch"].base) > 1e-3
    reg, _, _ = driven("axis:LT")
    assert reg["view.depth4"].base == pytest.approx(totem_rig()[0]["view.depth4"].base, abs=1e-9)


def test_with_the_totem_on_the_real_stick_is_free():
    reg, _, _ = driven("stick right", totem_on=True)
    assert reg["camera.yaw"].base == pytest.approx(0.0, abs=1e-9)
    reg, _, _ = driven("stick up", totem_on=True)
    assert reg["camera.pitch"].base == pytest.approx(0.0, abs=1e-9)


def test_with_the_totem_on_it_takes_three_arrows_and_gives_the_down_arrow_back():
    _, _, call = driven("rest", totem_on=True)
    skip = call["skip"]
    assert {"pad:B", "pad:X", "pad:Y"} <= skip and "pad:A" not in skip


# ---------------------------------------------------------------- the Joy-Con's own layout

def layout_rig(model=JOYCON, table_rows=()):
    """A real router and table over the factory's pad rows, and a pad of
    `model` that holds what `press` says."""
    reg, state, _ = totem_rig()
    table = routing.Bindings([
        routing.Binding("pad:A", "view.faces", "toggle"),
        routing.Binding("pad:LB", "view.shape", "step", -1.0),
        routing.Binding("pad:RB", "view.shape", "step", 1.0),
        routing.Binding("pad:VIEW", "tempo.tap", "fire"),
        routing.Binding("pad:LSTICK", "view.points", "toggle"),     # an old row: not heard
        routing.Binding("pad:LP", "view.lines", "toggle"),          # the ridiculous one
        routing.Binding("pad:MENU", "view.lines", "toggle"),
        *table_rows,
    ])
    router = routing.Router(reg, table)
    pad = FakePad()
    pad.model = model
    pad.buttons_named = {**gamepad.BUTTONS, "LP": models.LP, "RP": models.RP}
    return reg, state, router, pad


def press(router, pad, name):
    pad.frame(hold=(name,))
    router.pad(pad, buttons=True)
    pad.frame()
    router.pad(pad, buttons=True)


@pytest.mark.parametrize("model", [JOYCON, models.MODELS["joycon-r"]])
@pytest.mark.parametrize("totem_on", [False, True])
def test_sl_and_sr_step_the_shape_in_both_modes(model, totem_on):
    reg, _, router, pad = layout_rig(model)
    reg["totem.on"].set(totem_on)
    start = reg["view.shape"].base
    press(router, pad, "RP")
    assert reg["view.shape"].base == start + 1
    press(router, pad, "LP")
    assert reg["view.shape"].base == start


def test_skip_holds_a_layout_row_off_too():
    """`Router.pad(skip=)` is the one door for holding a button off a pad, so a
    later page key on SR can take it from the layout's row."""
    reg, _, router, pad = layout_rig()
    start = reg["view.shape"].base
    pad.frame(hold=("RP",))
    router.pad(pad, buttons=True, skip=frozenset({"pad:RP"}))
    assert reg["view.shape"].base == start


def test_the_old_rows_on_those_controls_are_not_heard():
    reg, _, router, pad = layout_rig()
    lines, points = reg["view.lines"].value, reg["view.points"].value
    for name in ("LP", "RP", "LSTICK"):
        press(router, pad, name)
    assert reg["view.lines"].value == lines and reg["view.points"].value == points


@pytest.mark.parametrize(("model", "reset", "switch"), [(JOYCON, "VIEW", "SHARE"),
                                                        (models.MODELS["joycon-r"], "MENU", "GUIDE")])
def test_minus_resets_the_totem_and_capture_switches_it(model, reset, switch):
    reg, state, router, pad = layout_rig(model)
    assert reg["totem.on"].value is False
    press(router, pad, switch)
    assert reg["totem.on"].value is True
    state.ang[0] = 1.0
    press(router, pad, reset)
    assert state.ang == [0.0] * 6
    press(router, pad, switch)
    assert reg["totem.on"].value is False


def test_the_sticks_click_resets_the_view_and_the_totem_keeps_the_rotation():
    reg, state, router, pad = layout_rig()
    reg["totem.on"].set(True)
    state.ang[0] = 1.0
    reg["camera.zoom"].set(2.0)
    press(router, pad, "LSTICK")
    assert reg["camera.zoom"].value == 1.0 and state.ang[0] == 1.0


def test_the_shoulder_holds_the_chase_on_both_joycons():
    assert ("LB", params.CHASE_PARAM, "momentary", 1.0) in JOYCON.layout
    assert ("RB", params.CHASE_PARAM, "momentary", 1.0) in models.MODELS["joycon-r"].layout
    reg, _, router, pad = layout_rig()
    shape = reg["view.shape"].base
    press(router, pad, "LB")
    assert reg["view.shape"].base == shape                  # the factory's shape row: not heard


def test_a_layout_rows_momentary_press_holds_until_the_release():
    """A row of the layout is a row: whatever lets go of a press whose row has
    gone has to count these, or the chase drops on the next frame."""
    model = dataclasses.replace(JOYCON, id="test-momentary",
                                layout=(("LB", "view.points", "momentary", 1.0),))
    reg, _, router, pad = layout_rig(model)
    reg["view.points"].set(False)
    for _ in range(5):
        pad.frame(hold=("LB",))
        router.pad(pad, buttons=True)
        assert reg["view.points"].value is True
    pad.frame()
    router.pad(pad, buttons=True)
    assert reg["view.points"].value is False
    pad.frame(hold=("LB",))
    router.pad(pad, buttons=True)
    assert reg["view.points"].value is True
    pad.on = False                                          # the pad gone: it lets go
    router.pad(pad, buttons=True)
    assert reg["view.points"].value is False


def test_a_hidden_table_row_on_the_same_param_lets_nothing_go():
    """The generic chase on − sits under the layout's on L: same param, and it
    must not end L's press."""
    model = dataclasses.replace(JOYCON, id="test-hidden",
                                layout=(*JOYCON.layout[:3], ("VIEW", "totem.reset", "fire", 1.0),
                                        ("LB", "view.points", "momentary", 1.0)))
    reg, _, router, pad = layout_rig(model, [routing.Binding("pad:VIEW", "view.points", "momentary")])
    reg["view.points"].set(False)
    for _ in range(3):
        pad.frame(hold=("LB",))
        router.pad(pad, buttons=True)
        assert reg["view.points"].value is True


def saved(reg):
    """Counts `preset.save_new` firing, in place of the real save."""
    fired = []
    p = reg.get("preset.save_new")
    if p is None:
        reg.trigger("preset.save_new", "Save new", lambda: fired.append(1), group="preset")
    else:
        p.fire = lambda: fired.append(1)
    return fired


def hold_menu(router, pad, seconds):
    pad.frame(hold=("MENU",))
    router.pad(pad, now=100.0, buttons=True)
    pad.frame(hold=("MENU",))
    router.pad(pad, now=100.0 + seconds, buttons=True)
    pad.frame()
    router.pad(pad, now=100.0 + seconds + 0.01, buttons=True)


def test_hold_to_save_is_in_the_edges_layout_once_and_only_when_held():
    reg, _, router, pad = layout_rig(EDGE, [routing.Binding("pad:MENU", "preset.save_new", "hold")])
    fired = saved(reg)
    hold_menu(router, pad, 0.05)
    assert fired == []                                      # a brush saves nothing
    hold_menu(router, pad, routing.HOLD_S + 0.1)
    assert fired == [1]                                     # the old table row is not a second save


def test_an_edge_on_any_table_saves_and_no_other_pad_gets_it_from_the_layout():
    reg, _, router, pad = layout_rig(EDGE)
    router.table.bindings = [b for b in router.table.bindings if b.source != "pad:MENU"]
    fired = saved(reg)
    hold_menu(router, pad, routing.HOLD_S + 0.1)
    assert fired == [1]
    assert not models.MODELS["dualsense"].layout and not models.MODELS["x360"].layout


def test_a_layout_alone_gives_a_pad_none_of_the_totems_gates():
    """The Edge has rows of its own and keeps its camera job and its A reset."""
    assert EDGE.layout and not EDGE.totem_layout
    assert JOYCON.totem_layout and models.MODELS["joycon-r"].totem_layout
    reg, _, _, pad = layout_rig(EDGE)
    dev = PadDevice("edge", {}, Context(reg=reg), io=pad)
    assert dev._quiet_stick(pad, reg) == frozenset()
    assert dev._no_camera_job(pad, reg) == ()
    assert totem.skip_of(pad) == totem.SKIP
    assert dev._totem_skip(reg, pad) == {"pad:MENU"}        # a learn leaves its save alone


def test_a_learn_ignores_the_layouts_controls_and_takes_a_free_one():
    reg, _, _, pad = layout_rig()
    dev = PadDevice("joy", {}, Context(reg=reg), io=pad)
    skip = dev._totem_skip(reg, pad)
    assert {"pad:LP", "pad:RP", "pad:LSTICK", "pad:VIEW", "pad:SHARE"} <= skip
    assert "pad:LB" in skip and "pad:A" not in skip


def stick_rig(model=JOYCON):
    """A route on the stick, a stick pushed right, the real router and device."""
    reg, _, router, pad = layout_rig(model, [routing.Binding("axis:0", "camera.pan.x", "push")])
    pad.axis = lambda i: 1.0 if i == gamepad.AX_LX else 0.0
    pad.lanes = lambda: [1.0, 0.5, 0.5, 0.5, 0.0, 0.0]
    dev = PadDevice("joy", {}, Context(reg=reg), io=pad)
    dev._dt = DT
    return reg, router, pad, dev


def lane(router):
    return float(router.sources.feeds["axis"][gamepad.AX_LX])


def test_a_stick_route_is_heard_only_with_the_totem_on_and_the_stick_orbits_with_it_off():
    reg, router, pad, dev = stick_rig()
    pad.frame()
    dev.act(router)
    assert math.isnan(lane(router))                           # off: the route lets go…
    yaw = reg["camera.yaw"].base
    assert yaw != pytest.approx(0.0, abs=1e-6)                # …and the stick orbits
    reg["totem.on"].set(True)
    pad.frame()
    dev.act(router)
    assert lane(router) == 1.0                                # on: the route hears it…
    assert reg["camera.yaw"].base == pytest.approx(yaw, abs=1e-9)   # …and nothing orbits
    reg["totem.on"].set(False)
    pad.frame()
    dev.act(router)
    assert math.isnan(lane(router))


def test_the_edges_stick_route_is_heard_as_ever():
    reg, router, pad, dev = stick_rig(EDGE)
    pad.frame()
    dev.act(router)
    assert lane(router) == 1.0
    assert reg["camera.yaw"].base == pytest.approx(0.0, abs=1e-9)   # the route took it off the job


def test_the_stick_lanes_are_the_left_sticks_and_its_dials():
    lanes = gamepad.left_stick_lanes()
    assert gamepad.AX_LX in lanes and gamepad.AX_LY in lanes and gamepad.AX_RX not in lanes
    assert gamepad.LANES.index("L.NE") in lanes and gamepad.LANES.index("R.NE") not in lanes


def test_the_pad_window_says_the_layout_and_leaves_the_edge_its_table():
    from hyperspace import ui_pad
    _, _, router, _ = layout_rig()
    said = ui_pad.source_rows(router.table, JOYCON)
    assert said["pad:RP"].target == "view.shape" and said["pad:SHARE"].target == "totem.on"
    assert said["pad:VIEW"].target == "totem.reset"
    assert said["pad:LB"].target == params.CHASE_PARAM
    assert ui_pad.source_rows(router.table, EDGE)["pad:MENU"].target == "preset.save_new"
    edge = ui_pad.source_rows(router.table, EDGE)
    assert edge["pad:VIEW"].target == "tempo.tap" and edge["pad:LB"].target == "view.shape"
    assert ui_pad.rows(router.table, JOYCON)["pad:LSTICK"].target == "camera.reset"


def test_the_edge_keeps_its_table_its_a_reset_and_its_camera_job():
    reg, state, router, pad = layout_rig(EDGE)
    start, lines = reg["view.shape"].base, reg["view.lines"].value
    press(router, pad, "LB")
    assert reg["view.shape"].base != start                  # the factory's row
    press(router, pad, "LP")
    assert reg["view.lines"].value != lines
    assert totem.skip_of(pad) == totem.SKIP
    dev = PadDevice("edge", {}, Context(reg=reg), io=pad)
    reg["totem.on"].set(True)
    state.driving = "edge"
    assert dev._no_camera_job(pad, reg) == ()
    state.ang[0] = 1.0
    pad.frame(hold=("A",))
    totem.step(state, pad, reg, DT, "edge")
    assert state.ang[0] == pytest.approx(0.0, abs=1e-6)     # A resets the Edge's totem


# ---------------------------------------------------------------- shake

def test_a_real_thrust_and_swing_fire_shake_and_a_real_rest_does_not():
    moves, cal = windows(), calibration()
    assert shakes_of(moves["rest"], cal) == []
    assert len(shakes_of(moves["thrust"], cal)) >= 3
    assert len(shakes_of(moves["swing"], cal)) >= 3


def test_one_jolt_is_a_shake_as_ever():
    m = gesture.Motion()
    m.step((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), DT)
    m.step((0.0, 0.0, 0.0), (0.0, 3.0, 0.0), DT)
    assert m.shake == 1.0


# ---------------------------------------------------------------- the gyro

def test_a_real_rest_turns_nothing():
    total = turned(windows()["rest"], calibration(), hid.Turn(learn=True))
    assert max(abs(v) for v in total) < 0.01


def test_a_joycon_whose_rest_reads_past_the_dead_band_stops_turning_within_seconds():
    """Rest read 8 deg/s off, past the 3 deg/s band: unlearned, the shape
    would spin at that rate for ever."""
    reports, cal = windows()["rest"], calibration(round(8.0 / 0.061))
    split = reports[0][0] + 3.0
    turn = hid.Turn(learn=True)
    early = turned([x for x in reports if x[0] <= split], cal, turn)
    assert max(abs(v) for v in early) < 30.0
    late = turned([x for x in reports if x[0] > split], cal, turn)
    assert max(abs(v) for v in late) < 0.05


def test_a_real_moving_hand_is_never_learned_as_an_offset():
    for move in ("carry", "swing", "thrust"):
        turn = hid.Turn(learn=True)
        turned(windows()[move], calibration(), turn)
        assert max(abs(v) for v in turn.offset) < 1.0, move


def test_only_a_joycons_reader_learns_an_offset():
    joycon = hid.HidPad({"vendor_id": 0x057E, "product_id": 0x2006}, start=False)
    assert joycon._turn.learn is True
    edge = hid.HidPad({"vendor_id": 0x054C, "product_id": 0x0DF2}, start=False)
    assert edge._turn.learn is False
    plain = hid.Turn()
    turned(windows()["rest"], calibration(round(8.0 / 0.061)), plain)
    assert plain.offset == [0.0, 0.0, 0.0]


# ---------------------------------------------------------------- no position from a Joy-Con; the Edge as it was

def flung(model):
    """A tilted, flung pad of `model` under the totem."""
    reg, state, _ = totem_rig()
    pad = FakePad()
    pad.model = model
    reg["totem.on"].set(True)
    for i in range(100):
        pad.frame(gyro=(0.0, 0.0, 90.0), accel=(2.0 * math.sin(i), 1.0, -1.0))
        totem.step(state, pad, reg, DT)
    return reg


def test_a_joycons_sensors_turn_the_shape_and_move_no_position():
    reg = flung(JOYCON)
    assert reg["camera.pan.x"].value == 0.0 and reg["camera.pan.y"].value == 0.0
    assert abs(phase(reg, "XY")) > 1.0


def test_the_edges_tilt_still_pans_under_the_totem():
    reg = flung(EDGE)
    assert reg["camera.pan.x"].value != 0.0 or reg["camera.pan.y"].value != 0.0


def test_the_poi_reads_no_joycon_and_still_reads_an_edge():
    for model, reads in ((JOYCON, False), (EDGE, True)):
        reg, state, _ = poi_rig()
        pad = FakePad()
        pad.model = model
        reg["poi.on"].set(True)
        for _ in range(60):
            pad.frame()
            poi.step(state, pad, reg, DT)
        assert (state.driving is not None) is reads
        assert (reg["camera.pan.y"].value != 0.0) is reads
