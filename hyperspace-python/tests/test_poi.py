"""The Joy-Con as a poi's handle (plan 47, the poi: hyperspace/poi.py):
the shape is the weight on a string — it hangs, swings and flies as one
would, the string's length, the weight and the springiness change how —
and nothing at all while it is off."""

import math

import pytest
from test_totem import DT, FakePad, ShimRouter, real_reports
from test_totem import rig as totem_rig

from hyperspace import gamepad, poi, totem
from hyperspace.devices import Context, PadDevice
from hyperspace.pads import nintendo

FLAT = (0.0, 1.0, 0.0)


def rig(**cfg):
    reg, _, view = totem_rig()
    state = poi.PoiState()
    poi.register(reg, state, cfg)
    return reg, state, view


def run(reg, state, pad, n, **kw):
    for _ in range(n):
        pad.frame(**kw)
        poi.step(state, pad, reg, kw.get("dt", DT))


def on(reg, state, pad, settle=60):
    reg["poi.on"].set(True)
    run(reg, state, pad, settle)


def pan(reg):
    return reg["camera.pan.x"].value, reg["camera.pan.y"].value


class Truth:
    """Where a real pad would be: its attitude turned by the gyro it is fed,
    so its accelerometer reads gravity as a turned pad does (a fake pad fed
    a turn but a fixed accel would read a push that is not there)."""

    def __init__(self):
        self.R = poi._ident()

    def frame(self, pad, gyro, dt, push=(0.0, 0.0, 0.0)):
        w = [math.radians(v) for v in gyro]
        a = math.sqrt(sum(v * v for v in w)) * dt
        if a > 1e-12:
            self.R = poi._matmul(self.R, poi._rodrigues([v * dt / a for v in w], a))
        up = [0.0 + push[0], 1.0 + push[1], 0.0 + push[2]]     # specific force, world, in g
        pad.frame(gyro=gyro, accel=tuple(poi._apply_t(self.R, up)), dt=dt)


def circle(reg, state, pad, seconds, f=0.8, amp=150.0, dt=DT, t0=0.0, truth=None):
    """The wrist circling: the far end traces a cone (gyro about x and z
    in quadrature) — what drives a poi round. The pad's accel turns with
    it (`Truth`)."""
    truth = truth if truth is not None else pad.__dict__.setdefault("truth", Truth())
    for i in range(int(seconds / dt)):
        t = t0 + i * dt
        w = 2 * math.pi * f * t
        truth.frame(pad, (amp * math.cos(w), 0.0, amp * math.sin(w)), dt)
        poi.step(state, pad, reg, dt)


def reach(state):
    """How far the weight is from the wrist, across the screen."""
    return math.hypot(state.ball[0] - state.wrist[0], state.ball[1] - state.wrist[1])


def test_the_tables_agree_with_the_app():
    assert poi.HAT_DOWN == gamepad.HAT_DOWN
    assert poi.RESET_BUTTON == totem.RESET_BUTTON
    assert poi.SKIP <= totem.SKIP                     # one reset button for both


def test_off_by_default_and_never_saved():
    reg, state, _ = rig()
    assert not state.on and reg["poi.on"].value is False
    for pid in ("poi.on", "poi.weight", "poi.length", "poi.spring", "poi.gravity",
                "poi.drag", "poi.hand", "poi.depth", "poi.reset"):
        p = reg[pid]
        assert not p.persist and not p.modulatable and p.group == "poi", pid
    pad = FakePad()
    reg["camera.pan.x"].set(0.4)
    run(reg, state, pad, 30, gyro=(200.0, 0.0, 200.0))
    assert pan(reg) == (pytest.approx(0.4), pytest.approx(0.0))
    assert state.driving is None


def test_the_config_gives_the_dials_their_start_clamped():
    _, state, _ = rig(length=2.5, weight=9.0, spring="soft", depth=False)
    assert state.length == 2.5
    assert state.weight == poi.RANGES["weight"][1]
    assert state.spring == poi.DEFAULTS["spring"]
    assert state.depth is False


def test_a_still_pad_hangs_the_shape_under_the_handle_and_it_does_not_creep():
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad, settle=120)
    x, y = pan(reg)
    sag = state.weight * poi.G_WORLD / state.stiffness()
    assert x == pytest.approx(0.0, abs=1e-6)
    assert y == pytest.approx(state.length + sag, rel=0.02)       # pan.y is down
    assert reg["camera.zoom"].value == pytest.approx(1.0, abs=1e-3)
    before = list(state.ball)
    run(reg, state, pad, 600)                                     # ten seconds still
    assert math.dist(before, state.ball) < 1e-3


def test_a_longer_string_hangs_lower_a_softer_or_heavier_one_stretches_further():
    def hang(**dials):
        reg, state, _ = rig(**dials)
        pad = FakePad()
        on(reg, state, pad, settle=600)
        return pan(reg)[1]
    assert hang(length=2.0) == pytest.approx(2 * hang(length=1.0), rel=0.05)
    stiff, soft = hang(spring=0.0), hang(spring=0.8)
    assert soft > stiff + 0.1
    light, heavy = hang(spring=0.6, weight=0.1), hang(spring=0.6, weight=1.0)
    assert heavy > light + 0.1


def test_circling_the_wrist_swings_the_weight_round_and_the_string_holds_it():
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    seen_x, peak = [], 0.0
    for k in range(10):
        circle(reg, state, pad, 0.5, t0=k * 0.5)
        seen_x.append(pan(reg)[0])
        peak = max(peak, reach(state))
    assert peak > 0.8 * state.length                  # out to the string's length
    assert peak <= poi.MAX_STRETCH * state.length + poi.HANDLE + 1e-6
    assert max(seen_x) - min(seen_x) > 0.6           # round: a wide swing across the hand


def test_a_slack_string_never_pushes_and_without_gravity_the_weight_floats():
    reg, state, _ = rig(gravity=0.0, drag=0.0)
    pad = FakePad()
    on(reg, state, pad, settle=2)
    state.ball = [0.2, -0.1, poi.HANDLE]            # inside the string's reach
    state.ball_v = [0.0, 0.0, 0.0]
    run(reg, state, pad, 120)
    assert state.ball == pytest.approx([0.2, -0.1, poi.HANDLE], abs=1e-9)
    state.ball_v = [0.5, 0.0, 0.0]                    # thrown: it coasts until the string bites
    run(reg, state, pad, 30)
    assert state.ball[0] > 0.2 + 0.2


def test_the_air_takes_the_swing_out_and_a_heavy_weight_keeps_it_longer():
    def after(weight):
        reg, state, _ = rig(weight=weight, drag=0.3)
        pad = FakePad()
        on(reg, state, pad)
        state.ball = [state.length, state.tip()[1], poi.HANDLE]   # held out level, let go
        state.ball_v = [0.0, 0.0, 0.0]
        run(reg, state, pad, 300)
        return reach(state), abs(state.ball[0])
    _, light = after(0.1)
    _, heavy = after(1.5)
    assert heavy > light


def test_the_hands_push_moves_the_handle_and_none_with_the_hand_at_zero():
    def shoved(hand):
        reg, state, _ = rig(hand=hand)
        pad = FakePad()
        on(reg, state, pad)
        x0 = state.ball[0]
        run(reg, state, pad, 12, accel=(0.8, 1.0, 0.0))          # a shove to the right
        run(reg, state, pad, 20)
        return state.ball[0] - x0, state.wrist
    moved, _ = shoved(1.0)
    assert moved > 0.05
    still, wrist0 = shoved(0.0)
    assert still == pytest.approx(0.0, abs=1e-9) and wrist0 == [0.0, 0.0, 0.0]


def carry(reg, state, pad, metres, seconds=1.0, axis=0, dt=DT):
    """The pad carried `metres` along a world axis in `seconds`, held level:
    a push one way for half the time, the other way for the rest (a
    triangle of speed, starting and ending still)."""
    a_mps2 = 4.0 * metres / seconds ** 2
    half = int(seconds / dt / 2)
    for sign in (1.0, -1.0):
        for _ in range(half):
            push = [0.0, 0.0, 0.0]
            push[axis] = sign * a_mps2 / poi.G_MPS2
            pad.frame(accel=(push[0], 1.0 + push[1], push[2]), dt=dt)
            poi.step(state, pad, reg, dt)


def test_a_hand_carried_a_metre_stays_there_and_a_resets_it_home():
    """The owner, 2026-11-03: the Joy-Con moved a metre to one side moves
    the shape that far and it stays — no pull back to the centre."""
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    carry(reg, state, pad, 1.0)
    there = state.wrist[0]
    assert there == pytest.approx(poi.UNITS_PER_M, rel=0.1)       # a metre, in world units
    run(reg, state, pad, 300)                                      # five seconds still
    assert state.wrist[0] == pytest.approx(there, abs=1e-6)
    assert pan(reg)[0] == pytest.approx(there + state.ball[0] - state.wrist[0], abs=1e-6)
    carry(reg, state, pad, -0.4)                                   # back a way: it follows
    assert state.wrist[0] == pytest.approx(there - 0.4 * poi.UNITS_PER_M, rel=0.1)
    pad.frame(hold=("A",))
    poi.step(state, pad, reg, DT)
    assert math.hypot(*state.wrist) < 1e-2


def test_a_still_pad_with_a_leaking_tilt_does_not_drift_away():
    """A still pad whose attitude is a few degrees off reads a little of
    gravity as a push. Still, its velocity is zeroed: the hand holds."""
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    off = math.radians(3.0)
    run(reg, state, pad, 600, accel=(math.sin(off), math.cos(off), 0.0))
    assert math.hypot(*state.wrist) < 0.05


def test_the_hand_is_held_at_its_limit():
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    carry(reg, state, pad, 20.0, seconds=2.0)
    assert math.hypot(*state.wrist) <= poi.HAND_LIMIT + 1e-9


def test_a_stalled_pad_pushes_nothing():
    """No new reading (the pad's reports stopped): its last accel is not
    integrated on and on."""
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    pad.frame(accel=(0.5, 1.0, 0.0))
    poi.step(state, pad, reg, DT)
    v = list(state.wrist_v)
    for _ in range(60):                      # the same reading, frame after frame
        poi.step(state, pad, reg, DT)
    assert math.hypot(*state.wrist_v) <= math.hypot(*v) + 0.5 * poi.STALL_S * poi.G_WORLD


def test_the_poi_and_the_totem_each_get_every_degree():
    from hyperspace.pads import gesture
    m = gesture.Motion()
    m.take_turn("poi")
    m.add_turn((10.0, 0.0, 0.0))
    m.add_turn((5.0, 1.0, 0.0))
    assert m.take_turn() == (15.0, 1.0, 0.0)            # the totem's
    assert m.take_turn("poi") == (15.0, 1.0, 0.0)       # the poi's, the same degrees
    assert m.take_turn("poi") == (0.0, 0.0, 0.0)


def test_the_stiffest_string_on_the_lightest_weight_stays_finite_under_a_violent_pad():
    reg, state, _ = rig(spring=0.0, weight=poi.RANGES["weight"][0], drag=0.0)
    pad = FakePad()
    on(reg, state, pad)
    for i in range(600):
        g = 2000.0 if (i // 7) % 2 else -2000.0
        pad.frame(gyro=(g, -g, g), accel=(3.0 * (i % 3 - 1), 1.0, -2.0))
        poi.step(state, pad, reg, DT)
        assert all(math.isfinite(v) for v in state.ball + state.ball_v)
        assert math.dist(state.ball, state.tip()) <= poi.MAX_STRETCH * state.length + 1e-6
    assert all(math.isfinite(v) for v in pan(reg))


def test_the_swing_does_not_depend_on_the_frame_rate():
    def track(dt):
        reg, state, _ = rig()
        pad = FakePad()
        reg["poi.on"].set(True)
        run(reg, state, pad, int(1.0 / dt), dt=dt)
        circle(reg, state, pad, 2.0, dt=dt)
        return list(state.ball)
    slow, fast = track(1 / 30), track(1 / 120)
    assert math.dist(slow, fast) < 0.15


def test_the_handles_tilt_settles_on_gravity_however_it_started():
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad, settle=2)
    state.att = poi._ident()                           # wrong: the pad is tipped
    tipped = (math.sin(0.5), math.cos(0.5), 0.0)
    run(reg, state, pad, 300, accel=tipped)
    assert poi._apply_t(state.att, [0.0, 1.0, 0.0]) == pytest.approx(list(tipped), abs=0.01)


def test_the_start_takes_the_pads_tilt_from_gravity():
    up = (math.sin(0.4), math.cos(0.4), 0.0)
    R = poi.from_gravity(up)
    assert poi._apply(R, list(up)) == pytest.approx([0.0, 1.0, 0.0], abs=1e-9)
    assert poi.from_gravity((0.0, -1.0, 0.0))[1][1] == pytest.approx(-1.0)


def test_home_is_kept_anyone_elses_write_is_the_new_home_and_off_puts_it_back():
    reg, state, _ = rig()
    pad = FakePad()
    reg["camera.pan.x"].set(0.5)
    reg["camera.zoom"].set(2.0)
    on(reg, state, pad, settle=120)
    assert pan(reg)[0] == pytest.approx(0.5, abs=1e-6)
    assert pan(reg)[1] == pytest.approx(state.length, rel=0.05)
    assert reg["camera.zoom"].value == pytest.approx(2.0, rel=1e-3)
    reg["camera.pan.x"].set(-1.0)                      # a knob, a reset, a load
    run(reg, state, pad, 2)
    assert state.pan_home[0] == pytest.approx(-1.0)
    assert pan(reg)[0] == pytest.approx(-1.0, abs=1e-6)
    reg["poi.on"].set(False)
    assert pan(reg) == (pytest.approx(-1.0), pytest.approx(0.0, abs=1e-3))
    assert reg["camera.zoom"].value == pytest.approx(2.0, rel=1e-3)


def test_depth_toward_the_eye_grows_the_shape_and_the_switch_turns_it_off():
    reg, state, _ = rig(gravity=0.0, drag=0.0)
    pad = FakePad()
    on(reg, state, pad, settle=2)
    state.ball = [0.0, 0.0, 1.0 + poi.HANDLE]
    state.ball_v = [0.0, 0.0, 0.0]
    run(reg, state, pad, 1)
    assert reg["camera.zoom"].value == pytest.approx(2 ** poi.DEPTH_OCTAVES, rel=0.01)
    reg["poi.depth"].set(False)
    run(reg, state, pad, 1)
    assert reg["camera.zoom"].value == pytest.approx(1.0, rel=1e-6)


def test_a_resets_the_weight_to_hang_still_and_the_wrist_home():
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    circle(reg, state, pad, 2.0)
    assert reach(state) > 0.3 and math.hypot(*state.ball_v) > 0.1
    pad.frame(hold=("A",))
    poi.step(state, pad, reg, DT)
    assert math.hypot(*state.wrist) < 0.01                  # home (this frame's push after)
    tip = state.tip()                                        # hanging under the tip
    assert math.hypot(state.ball[0] - tip[0], state.ball[2] - tip[2]) < 0.02
    assert math.hypot(*state.ball_v) < 0.2
    pad.frame(hat=gamepad.HAT_DOWN)                    # the D-pad's down too
    state.ball_v = [1.0, 0.0, 0.0]
    poi.step(state, pad, reg, DT)
    assert math.hypot(*state.ball_v) < 0.2


def test_the_pad_device_steps_it_only_while_on_and_holds_its_reset_off_the_rows():
    reg, _, _ = rig()
    dev = PadDevice("pad", {}, Context(reg=reg), io=FakePad())
    dev._dt = DT
    router = ShimRouter(reg)
    dev.io.frame()
    dev.act(router)
    assert "skip" not in router.calls[-1]
    reg["poi.on"].set(True)
    for _ in range(30):
        dev.io.frame()
        dev.act(router)
    assert router.calls[-1]["skip"] == poi.SKIP
    assert pan(reg)[1] > 0.5                           # hanging
    reg["totem.on"].set(True)                          # both: the totem's buttons too
    dev.io.frame()
    dev.act(router)
    assert router.calls[-1]["skip"] == totem.SKIP | poi.SKIP
    reg["poi.on"].set(False)
    reg["totem.on"].set(False)
    dev.io.frame()
    dev.act(router)
    assert "skip" not in router.calls[-1]
    assert pan(reg) == (pytest.approx(0.0, abs=1e-6), pytest.approx(0.0, abs=1e-6))


def test_while_the_poi_swings_the_totems_tilt_pan_steps_aside_and_its_turn_still_turns():
    reg, state, _ = rig()
    tstate = reg.totem
    pad = FakePad()
    reg["totem.on"].set(True)
    reg["poi.on"].set(True)
    tipped = (math.sin(0.4), math.cos(0.4), 0.0)       # right side down: tilt-pan would go right
    for _ in range(60):
        pad.frame(gyro=(0.0, 0.0, 90.0), accel=tipped)
        poi.step(state, pad, reg, DT)
        totem.step(tstate, pad, reg, DT)
    assert tstate.pan_out == [0.0, 0.0]
    assert abs(reg["rot.phase.XY"].value) > 0.3
    assert pan(reg)[0] == pytest.approx(state.pan_home[0] + state.offset()[0], abs=1e-6)


def test_a_reset_that_fires_both_leaves_the_pan_at_the_poi_hanging_from_zero():
    reg, state, _ = rig()
    dev = PadDevice("pad", {}, Context(reg=reg), io=FakePad())
    dev._dt = DT
    router = ShimRouter(reg)
    reg["camera.pan.x"].set(0.7)
    reg["poi.on"].set(True)
    reg["totem.on"].set(True)
    for _ in range(30):
        dev.io.frame()
        dev.act(router)
    dev.io.frame(hold=("A",))
    dev.act(router)                                    # the totem's reset zeroes the pan
    for _ in range(30):
        dev.io.frame()
        dev.act(router)
    x, y = pan(reg)
    assert x == pytest.approx(0.0, abs=1e-6)          # home is now 0, the weight under it
    assert y == pytest.approx(state.length, rel=0.05)


def test_real_bytes_a_still_joycon_hangs_the_shape_still():
    """The owner's Joy-Con (L) over Bluetooth (the plan 46 tape), as the
    app reads it: lying still, the weight hangs and does not wander."""
    windows, cal = real_reports()
    amap = nintendo.AXIS_MAP
    reg, state, _ = rig()
    reg["poi.on"].set(True)
    pad = FakePad()
    ys = []
    last = None
    for t, r in windows["still"]:
        f = nintendo.decode(r, "l", cal)
        if f is None:
            continue
        dt = 0.0 if last is None else t - last
        last = t
        pad.motion.step(amap.pick(cal.gyro_dps(f.gyro), amap.gyro),
                        amap.pick(cal.accel_g(f.accel), amap.accel), dt)
        poi.step(state, pad, reg, dt)
        ys.append(pan(reg))
    assert len(ys) > 20
    tail = ys[len(ys) // 2:]
    assert max(abs(x) for x, _ in tail) < 0.05
    assert all(abs(y - state.length) < 0.1 for _, y in tail)


def test_one_duck_typed_rule_finds_the_state_so_a_hot_reload_still_drives():
    import dataclasses
    reg, state, _ = rig()
    assert poi.state_of(reg) is state
    Reloaded = dataclasses.make_dataclass(          # a reload's new class: not PoiState
        "PoiState", [(f.name, f.type, f) for f in dataclasses.fields(poi.PoiState)],
        bases=(), namespace={k: v for k, v in vars(poi.PoiState).items()
                             if callable(v) and not k.startswith("__")})
    reg.poi = Reloaded()
    assert not isinstance(reg.poi, poi.PoiState) and poi.state_of(reg) is reg.poi
    reg.poi.on = True
    dev = PadDevice("pad", {}, Context(reg=reg), io=FakePad())
    dev._dt = DT
    router = ShimRouter(reg)
    for _ in range(30):
        dev.io.frame()
        dev.act(router)
    assert router.calls[-1]["skip"] == poi.SKIP and pan(reg)[1] > 0.5
    reg.poi = lambda: None                            # a stub's something else
    assert poi.state_of(reg) is None and not poi.owns_pan(reg)


def test_learn_ignores_the_reset_while_the_poi_will_take_the_pad():
    reg, state, _ = rig()
    dev = PadDevice("pad", {}, Context(reg=reg), io=FakePad())
    assert dev._totem_skip(reg, dev.io) == frozenset()
    reg["poi.on"].set(True)
    dev.io.frame()
    assert dev._totem_skip(reg, dev.io) == poi.SKIP       # before act takes it over
    state.driving = "other"
    assert dev._totem_skip(reg, dev.io) == frozenset()    # another pad holds it


def test_a_scalar_poi_in_the_config_is_no_table():
    assert poi.configured({"poi": True}) == {}
    assert poi.configured({"poi": {"length": 2.0}}) == {"length": 2.0}
    assert poi.configured({}) == {}


def test_fast_swings_with_no_travel_leave_the_hand_where_it_was():
    """The owner's drift: the wrist swung hard (600 deg/s, the pad turning
    about itself, not carried) gathers no travel, and held still after,
    nothing creeps."""
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    circle(reg, state, pad, 4.0, f=1.5, amp=600.0)
    after = list(state.wrist)
    assert math.hypot(*after) < 0.3
    truth = pad.truth
    for _ in range(300):                                  # held still where it ended
        truth.frame(pad, (0.0, 0.0, 0.0), DT)
        poi.step(state, pad, reg, DT)
    assert math.dist(state.wrist, after) < 0.05
