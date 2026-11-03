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
WIDE = [50.0, 50.0, 50.0]        # a box no swing reaches: the physics on its own


def wide(state):
    state.box = list(WIDE)
    return state


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
                "poi.drag", "poi.hand", "poi.home", "poi.depth", "poi.reset"):
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
        wide(state)
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
    wide(state)
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
    a push one way rising and falling, then the other way (a sine over the
    move, as a hand does it: it starts and ends still, and the push never
    holds steady — a steady push reads as a resting pad)."""
    amp = 2.0 * math.pi * metres / seconds ** 2            # m/s²: ∫∫ A sin = A T² / 2π
    n = int(seconds / dt)
    for i in range(n):
        push = [0.0, 0.0, 0.0]
        push[axis] = amp * math.sin(2.0 * math.pi * (i + 0.5) / n) / poi.G_MPS2
        pad.frame(accel=(push[0], 1.0 + push[1], push[2]), dt=dt)
        poi.step(state, pad, reg, dt)


def shove(reg, state, pad, seconds=2.0, axis=0, g=0.5, dt=DT):
    """A push one way only, rising and falling (a hump), never steady:
    the farthest the wrist, the weight and the pan got along `axis` (the
    sign of `g`), and the farthest the weight got toward the eye."""
    n = int(seconds / dt)
    far = [0.0, 0.0, 0.0, 0.0]
    sign = 1.0 if g >= 0 else -1.0
    for i in range(n):
        push = [0.0, 0.0, 0.0]
        push[axis] = g * (1.0 - math.cos(2.0 * math.pi * (i + 0.5) / n)) / 2.0
        pad.frame(accel=(push[0], 1.0 + push[1], push[2]), dt=dt)
        poi.step(state, pad, reg, dt)
        p = pan(reg)
        far = [max(far[0], sign * state.wrist[axis]), max(far[1], sign * state.ball[axis]),
               max(far[2], sign * p[axis]) if axis < 2 else far[2],
               max(far[3], state.ball[2])]
    return far


def test_a_carry_lands_most_of_the_way_and_the_hand_eases_home_or_stays():
    """The Joy-Con carried a metre to one side moves the shape most of a
    metre (the velocity bleeds, `HAND_BLEED_S`: the drift a move gathers
    dies with it). With `poi.home` off (0) it stays where it landed —
    the 2026-11-03 frame, within the screen; with the default it eases
    back to the centre over those seconds. A puts it home at once."""
    reg, state, _ = rig(home=0.0)
    wide(state)
    pad = FakePad()
    on(reg, state, pad)
    carry(reg, state, pad, 1.0)
    run(reg, state, pad, 60)                                       # a second: the hand comes to rest
    there = state.wrist[0]
    assert 0.5 * poi.UNITS_PER_M < there <= poi.UNITS_PER_M            # most of a metre
    run(reg, state, pad, 300)                                      # five seconds still
    assert state.wrist[0] == pytest.approx(there, abs=1e-6)       # home off: it stays
    assert pan(reg)[0] == pytest.approx(state.ball[0], abs=1e-6)  # the weight, from home 0
    carry(reg, state, pad, -0.4)                                   # back a way: it follows
    run(reg, state, pad, 60)
    assert state.wrist[0] < there - 0.2 * poi.UNITS_PER_M
    pad.frame(hold=("A",))
    poi.step(state, pad, reg, DT)
    assert math.hypot(*state.wrist) < 1e-2

    reg, state, _ = rig()                                          # the default: eases home
    wide(state)
    pad = FakePad()
    on(reg, state, pad)
    assert state.home == poi.DEFAULTS["home"] > 0
    carry(reg, state, pad, 1.0)
    run(reg, state, pad, 30)
    there = state.wrist[0]
    assert there > 0.4 * poi.UNITS_PER_M
    run(reg, state, pad, int(2 * state.home / DT))                 # two time constants
    assert 0 < state.wrist[0] < 0.2 * there


def test_sensor_samples_with_no_gravity_in_them_push_nothing_and_settle_nothing():
    """The tape's first second and a half: the sensor not yet on reads
    zeros. The first build took them for a 1 g push and the hand hit its
    limit before gravity arrived."""
    reg, state, _ = rig()
    pad = FakePad()
    reg["poi.on"].set(True)
    run(reg, state, pad, 90, accel=(0.0, 0.0, 0.0))               # 1.5 s of nothing
    assert not state.settled and state.wrist == [0.0, 0.0, 0.0]
    run(reg, state, pad, 30, accel=(0.0, 0.0, 0.0))
    assert math.hypot(*state.wrist) < 1e-9                        # …then more of it
    tipped = (math.sin(0.3), math.cos(0.3), 0.0)
    run(reg, state, pad, 60, accel=tipped)                         # gravity arrives: settled from it
    assert state.settled
    assert poi._apply_t(state.att, [0.0, 1.0, 0.0]) == pytest.approx(list(tipped), abs=0.02)
    assert math.hypot(*state.wrist) < 0.05
    on_before = list(state.wrist)
    run(reg, state, pad, 30, accel=(0.0, 0.0, 0.0))               # a glitch mid-run: ignored
    assert state.wrist == pytest.approx(on_before, abs=1e-6)


def test_a_still_pad_whose_attitude_is_six_degrees_off_recovers_and_the_hand_holds():
    """The tape's dead-lock: the pad dead still, the attitude 6° off, so
    the push through it read 0.11 g — "not still" — and only a still pad
    was corrected; the hand flew ten units in four seconds. Still is now
    judged from the sensors alone and the tilt is always pulled in."""
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    off = math.radians(6.0)
    state.att = poi._rodrigues([0.0, 0.0, 1.0], off)               # wrong by 6° about z
    run(reg, state, pad, 90)                                       # 1.5 s still
    up = poi._apply(state.att, [0.0, 1.0, 0.0])
    assert math.degrees(math.acos(up[1])) < 0.5
    assert state.still >= poi.STILL_S and state.wrist_v == [0.0, 0.0, 0.0]
    assert math.hypot(*state.wrist) < 0.1


def test_the_one_g_this_pad_reads_is_learned_so_its_calibration_is_no_push():
    """The owner's Joy-Con reads 1.022 g at rest: a fixed 1.0 made the
    extra a push whenever the pad moved. Learned while still, taken out."""
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad, settle=240, )
    run(reg, state, pad, 240, accel=(0.0, 1.022, 0.0))
    assert state.g_mag == pytest.approx(1.022, abs=0.003)
    assert poi._push(state, [0.0, 1.022, 0.0]) == [0.0, 0.0, 0.0]


def test_a_still_pad_with_a_leaking_tilt_does_not_drift_away():
    """A still pad whose attitude is a few degrees off reads a little of
    gravity as a push. Still, its velocity is zeroed: the hand holds."""
    reg, state, _ = rig()
    pad = FakePad()
    on(reg, state, pad)
    off = math.radians(3.0)
    run(reg, state, pad, 600, accel=(math.sin(off), math.cos(off), 0.0))
    assert math.hypot(*state.wrist) < 0.05


def test_the_hand_and_the_weight_are_held_on_the_screen():
    """The box (`box_for`: what the eye sees at depth 0 through the
    output, set by the guide each frame): a carry past the edge stops at
    it — the wrist, the weight, so the pan — and the weight's depth stops
    an octave of zoom each way. Home off, so nothing eases back."""
    reg, state, _ = rig(home=0.0)
    pad = FakePad()
    on(reg, state, pad)
    hx, hy, hz = state.box
    assert state.box == poi.DEFAULT_BOX and hx > hy > 1.0
    wrist, ball, panned, _ = shove(reg, state, pad)                # shoved right, hard
    assert wrist == pytest.approx(hx, abs=1e-9)                    # to the edge, not past it
    assert ball <= hx + 1e-9 and panned <= hx + 1e-9
    reg["camera.reset"].fire()
    wrist, ball, panned, _ = shove(reg, state, pad, axis=1, g=-0.5)     # …down (pan.y is down)
    assert wrist == pytest.approx(hy, abs=1e-9) and panned <= hy + 1e-9
    reg["camera.reset"].fire()
    zooms = []
    for _ in range(int(2.0 / DT)):                                 # …toward the eye: an octave, no more
        pad.frame(accel=(0.0, 1.0, 0.5), dt=DT)
        poi.step(state, pad, reg, DT)
        zooms.append(reg["camera.zoom"].value)
    assert max(zooms) <= 2.0 ** (hz * poi.DEPTH_OCTAVES) + 1e-6
    assert state.ball[2] <= poi.HANDLE + hz + 1e-9
    reg["camera.reset"].fire()
    reg["camera.pan.x"].set(1.0)                                   # a home off centre: the same screen
    run(reg, state, pad, 2)
    _, _, panned, _ = shove(reg, state, pad)
    assert panned == pytest.approx(hx, abs=1e-6)


def test_the_box_is_what_the_eye_sees_and_the_default_is_a_16_by_9_output():
    from hyperspace import geometry
    for w, h in ((1920, 1080), (1280, 1024), (800, 600)):
        ppu = geometry.px_per_unit(w, h, geometry.EYE_FOV, geometry.EYE_DISTANCE)
        box = poi.box_for(w, h, geometry.EYE_FOV, geometry.EYE_DISTANCE)
        assert box[0] == pytest.approx(w / 2 / ppu - poi.BOX_MARGIN, abs=1e-9)
        assert box[1] == pytest.approx(h / 2 / ppu - poi.BOX_MARGIN, abs=1e-9)
        assert box[2] == poi.DEPTH_HALF
    want = poi.box_for(1920, 1080, geometry.EYE_FOV, geometry.EYE_DISTANCE)
    assert poi.DEFAULT_BOX == pytest.approx(want, abs=1e-6)
    # the eye frames the shorter side the same whatever the output: that
    # side is always the same height in world units, the other its aspect
    short = poi.box_for(10, 10, geometry.EYE_FOV, geometry.EYE_DISTANCE)
    assert short[1] == pytest.approx(want[1], abs=1e-9) and short[0] == short[1]


def test_a_view_reset_puts_the_hand_home_too():
    """The registry's camera.reset (the panel's Reset view): with the hand
    out, the shape drew home for one frame and the poi put it back out."""
    reg, state, _ = rig(home=0.0)
    pad = FakePad()
    on(reg, state, pad)
    carry(reg, state, pad, 0.5)
    assert state.wrist[0] > 0.5
    reg["camera.reset"].fire()
    assert state.wrist == [0.0, 0.0, 0.0] and not state.settled
    run(reg, state, pad, 120)
    assert pan(reg)[0] == pytest.approx(0.0, abs=0.05)             # hanging under home (a sway)
    reg["poi.on"].set(False)                                       # off: a view reset is the view's alone
    state.wrist = [1.0, 0.0, 0.0]
    reg["camera.reset"].fire()
    assert state.wrist == [1.0, 0.0, 0.0]


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
