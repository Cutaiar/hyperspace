"""The Joy-Con as a 4D totem (plan 47, an experiment: hyperspace/totem.py):
the gyro integrated into three of the six planes, X / Y / B throwing an
axis into W, A resetting to the world's axes, the tilt onto the pan — and
nothing at all while it is off."""

import math
from itertools import product
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace import gamepad, geometry, totem
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.devices import Context, PadDevice
from hyperspace.pads import gesture, nintendo
from hyperspace.params import build_registry
from hyperspace.view import ViewState

DT = 1 / 60
FLAT = (0.0, 1.0, 0.0)              # lying face up: +1 g out of the face


class FakePad:
    """A pad with motion sensors, as `gamepad.Pad` answers the totem."""

    def __init__(self):
        self.on = True
        self.motion = gesture.Motion()
        self.buttons_named = {"A": gamepad.A, "B": gamepad.B, "X": gamepad.X, "Y": gamepad.Y}
        self.held: set[int] = set()
        self.was: set[int] = set()
        self.hat = self.prev_hat = 0

    def has(self, cap):
        return cap == "motion"

    def motion_lanes(self):
        return self.motion.lanes()

    def lanes(self):
        return [0.5, 0.5, 0.5, 0.5, 0.0, 0.0]

    def axis(self, i):
        return 0.0

    def trigger(self, i):
        return 0.0

    def down(self, c):
        return c in self.held

    def pressed(self, c):
        return c in self.held and c not in self.was

    def released(self, c):
        return c in self.was and c not in self.held

    def hat_pressed(self, bit):
        return bool(self.hat & bit) and not (self.prev_hat & bit)

    def hat_released(self, bit):
        return bool(self.prev_hat & bit) and not (self.hat & bit)

    def frame(self, gyro=(0.0, 0.0, 0.0), accel=FLAT, hold=(), hat=0, dt=DT):
        """One report: the sensors stepped, the buttons held now."""
        self.was, self.prev_hat = self.held, self.hat
        self.held = {self.buttons_named[b] for b in hold}
        self.hat = hat
        self.motion.step(gyro, accel, dt)


def rig():
    view = ViewState()
    chain = Analyzer(Analyser())
    reg = build_registry(view, Control(chain), SimpleNamespace(chain=chain), None)
    state = totem.TotemState()
    totem.register(reg, state, view)
    return reg, state, view


def run(reg, state, pad, n, **kw):
    for _ in range(n):
        pad.frame(**kw)
        totem.step(state, pad, reg, kw.get("dt", DT))


def phase(reg, plane):
    return reg[f"rot.phase.{plane}"].value


def test_the_tables_agree_with_the_app():
    assert totem.PLANES == tuple(geometry.PLANE_NAMES)
    assert totem.HAT_DOWN == gamepad.HAT_DOWN
    # a right-hand turn about each body axis is +AXIS_SIGN in its plane, as
    # rotate4 composes it: ω × v for a small angle
    eps = 1e-4
    for i in range(3):
        for w in (False, True):
            if w:
                continue                    # a W plane has no axis in 3-space to check against
            ang = [0.0] * 6
            ang[totem.PLANES.index(totem.plane_of(i, w))] = totem.AXIS_SIGN[i] * eps
            R = geometry.rot_matrix(ang)[:3, :3]
            omega = np.zeros(3)
            omega[i] = eps
            for v in np.eye(3):
                assert np.allclose(R @ v - v, np.cross(omega, v), atol=1e-7)


def test_three_planes_out_of_six_one_per_axis_whatever_the_latches():
    for w in product((False, True), repeat=3):
        live = totem.live_planes(w)
        assert len(set(live)) == 3 and set(live) <= set(totem.PLANES)
        for i, plane in enumerate(live):
            assert plane == totem.AXIS_PLANES[i][w[i]]
    assert totem.live_planes([False] * 3) == ("YZ", "XZ", "XY")
    assert totem.live_planes([True] * 3) == ("XW", "YW", "ZW")


def test_off_by_default_and_never_saved():
    reg, state, _ = rig()
    assert reg["totem.on"].value is False and not state.on
    for p in reg:
        if p.group == "totem":
            assert not p.persist and not p.modulatable, p.id
    pad = FakePad()
    reg["rot.phase.XY"].set(0.7)
    run(reg, state, pad, 30, gyro=(0.0, 0.0, 200.0), hold=("A",))
    assert phase(reg, "XY") == pytest.approx(0.7)
    assert state.driving is None


def test_the_buttons_latch_on_the_press():
    reg, state, _ = rig()
    reg["totem.on"].set(True)
    pad = FakePad()
    run(reg, state, pad, 2)
    assert state.driving == "" and totem.readout(state) == "YZ · XZ · XY"
    run(reg, state, pad, 10, hold=("B",))             # held: one flip, not ten
    assert state.w == [False, False, True] and reg["totem.w.z"].value is True
    run(reg, state, pad, 2)
    run(reg, state, pad, 1, hold=("X", "Y"))
    assert totem.readout(state) == "XW · YW · ZW"
    run(reg, state, pad, 1)
    run(reg, state, pad, 1, hold=("B",))
    assert totem.readout(state) == "XW · YW · XY"


def test_a_constant_turn_integrates_and_a_flip_carries_on_in_w():
    reg, state, _ = rig()
    reg["totem.on"].set(True)
    pad = FakePad()
    run(reg, state, pad, 1)
    dps = 90.0
    run(reg, state, pad, 60, gyro=(0.0, 0.0, dps))     # 1 s about z
    want = math.radians(dps - totem.DEADBAND_DPS)       # the dead band is soft: it subtracts
    assert want - 0.03 < phase(reg, "XY") < want        # less the smoothing's lag
    for other in ("XZ", "YZ", "XW", "YW", "ZW"):
        assert phase(reg, other) == pytest.approx(0.0, abs=1e-9)
    xy = phase(reg, "XY")
    # B mid-stream: the turn goes on in ZW from its own 0, XY stays put
    run(reg, state, pad, 1, gyro=(0.0, 0.0, dps), hold=("B",))
    run(reg, state, pad, 29, gyro=(0.0, 0.0, dps))
    assert phase(reg, "XY") == pytest.approx(xy, abs=1e-9)
    assert phase(reg, "ZW") == pytest.approx(math.radians(dps - totem.DEADBAND_DPS) * 0.5,
                                             abs=0.01)


def test_a_still_pad_does_not_drift_and_the_totem_holds_the_spin():
    reg, state, view = rig()
    reg["totem.on"].set(True)
    pad = FakePad()
    view.planes = [True] * 6                           # every plane spinning on its own
    run(reg, state, pad, 1)
    before = [phase(reg, n) for n in totem.PLANES]
    for _ in range(120):
        pad.frame(gyro=(1.5, -2.0, 2.5))               # a still Joy-Con's noise
        totem.step(state, pad, reg, DT)
        view.integrate(DT)                             # the host's spin, after the devices
    totem.step(state, pad, reg, DT)
    after = [phase(reg, n) for n in totem.PLANES]
    assert after == pytest.approx(before, abs=1e-9)


def test_taking_over_adopts_the_phases_so_nothing_jumps():
    reg, state, _ = rig()
    reg["rot.phase.YZ"].set(1.0)
    reg["rot.phase.XW"].set(-0.5)
    reg["totem.on"].set(True)
    pad = FakePad()
    run(reg, state, pad, 5)
    assert phase(reg, "YZ") == pytest.approx(1.0) and phase(reg, "XW") == pytest.approx(-0.5)


def test_the_tilt_pans_and_levelling_brings_it_back():
    reg, state, _ = rig()
    reg["totem.on"].set(True)
    pad = FakePad()
    run(reg, state, pad, 30)                           # level: the reference
    assert reg["camera.pan.x"].value == pytest.approx(0.0, abs=1e-6)
    s = math.sin(math.radians(30))
    c = math.cos(math.radians(30))
    run(reg, state, pad, 120, accel=(-s, c, 0.0))      # right side down 30°
    assert reg["camera.pan.x"].value == pytest.approx(totem.PAN_PER_RAD * math.radians(30), abs=0.02)
    run(reg, state, pad, 120, accel=(0.0, c, -s))      # the far end up 30°
    assert reg["camera.pan.y"].value == pytest.approx(-totem.PAN_PER_RAD * math.radians(30), abs=0.02)
    assert reg["camera.pan.x"].value == pytest.approx(0.0, abs=0.02)
    run(reg, state, pad, 120)
    assert reg["camera.pan.y"].value == pytest.approx(0.0, abs=0.02)
    # the pan is a relative move: someone else's pan stays under it
    reg["camera.pan.x"].set(2.0)
    run(reg, state, pad, 120, accel=(-s, c, 0.0))
    assert reg["camera.pan.x"].value == pytest.approx(2.0 + totem.PAN_PER_RAD * math.radians(30),
                                                      abs=0.02)


def test_reset_zeroes_the_pose_and_re_references_where_the_pad_is():
    reg, state, view = rig()
    reg["totem.on"].set(True)
    pad = FakePad()
    run(reg, state, pad, 10)
    s, c = math.sin(math.radians(40)), math.cos(math.radians(40))
    run(reg, state, pad, 60, gyro=(50.0, -40.0, 30.0), accel=(-s, c, 0.0))
    run(reg, state, pad, 120, accel=(-s, c, 0.0))      # gravity's low-pass settles
    reg["camera.yaw"].set(0.4)
    view.body = np.eye(4)
    assert reg["camera.pan.x"].value > 0.5 and abs(phase(reg, "YZ")) > 0.3
    run(reg, state, pad, 1, accel=(-s, c, 0.0), hold=("A",))
    for n in totem.PLANES:
        assert phase(reg, n) == pytest.approx(0.0, abs=1e-9), n
    for pid in ("camera.pan.x", "camera.pan.y", "camera.yaw", "camera.pitch"):
        assert reg[pid].value == pytest.approx(0.0, abs=1e-9), pid
    assert view.body is None
    # held where it was reset, the pad is the new level: the pan stays at 0
    run(reg, state, pad, 60, accel=(-s, c, 0.0))
    assert reg["camera.pan.x"].value == pytest.approx(0.0, abs=1e-3)
    # D-pad down is the same reset
    run(reg, state, pad, 30, gyro=(0.0, 0.0, 60.0), accel=(-s, c, 0.0))
    assert abs(phase(reg, "XY")) > 0.3
    run(reg, state, pad, 1, accel=(-s, c, 0.0), hat=totem.HAT_DOWN)
    assert phase(reg, "XY") == pytest.approx(0.0, abs=1e-9)


class ShimRouter:
    def __init__(self, reg):
        self.reg = reg
        self.calls = []

    def pad(self, io, **kw):
        self.calls.append(kw)

    def felt(self, scheme, lanes, dt):
        return None


def test_the_pad_device_steps_it_only_while_on_and_holds_its_buttons_off_the_rows():
    reg, _, _ = rig()
    dev = PadDevice("pad", {}, Context(reg=reg), io=FakePad())
    dev.io.frame(gyro=(0.0, 0.0, 120.0))
    dev._dt = DT
    router = ShimRouter(reg)
    reg["rot.phase.XY"].set(0.25)
    dev.act(router)
    assert "skip" not in router.calls[-1]                # off: the rows as ever
    assert phase(reg, "XY") == pytest.approx(0.25)
    reg["totem.on"].set(True)
    for _ in range(10):
        dev.io.frame(gyro=(0.0, 0.0, 120.0))
        dev.act(router)
    assert router.calls[-1]["skip"] == totem.SKIP
    assert phase(reg, "XY") > 0.25 + 0.1
    reg["totem.on"].set(False)
    dev.act(router)
    assert "skip" not in router.calls[-1]


def test_a_router_skips_the_rows_it_is_told_to():
    from hyperspace.routing import Binding, Bindings, Router
    view = ViewState()
    chain = Analyzer(Analyser())
    reg = build_registry(view, Control(chain), SimpleNamespace(chain=chain), None)
    table = Bindings([Binding("pad:A", "view.faces", "toggle"),
                      Binding("pad:LB", "view.lines", "toggle")])
    router = Router(reg, table)
    pad = FakePad()
    pad.buttons_named["LB"] = gamepad.LB
    faces, lines = reg["view.faces"].value, reg["view.lines"].value
    pad.frame(hold=("A", "LB"))
    router.pad(pad, skip=totem.SKIP)
    assert reg["view.faces"].value == faces            # A: the totem's
    assert reg["view.lines"].value != lines            # LB: its row as ever


def real_reports():
    import test_pads_joycon_real as real
    return real.windows(), real.calibration()


def test_real_bytes_a_still_joycon_holds_and_a_turn_right_turns_the_shape_right():
    """The owner's Joy-Con (L) over Bluetooth (the plan 46 tape): through
    the flash's calibration and the (L)'s axis map, as the app reads it."""
    windows, cal = real_reports()
    amap = nintendo.AXIS_MAP

    def drive(names, state=None, reg=None):
        if state is None:
            reg, state, _ = rig()
            reg["totem.on"].set(True)
        pad = FakePad()
        for name in names:
            last = None
            for t, r in windows[name]:
                f = nintendo.decode(r, "l", cal)
                if f is None:
                    continue
                dt = 0.0 if last is None else t - last
                last = t
                pad.motion.step(amap.pick(cal.gyro_dps(f.gyro), amap.gyro),
                                amap.pick(cal.accel_g(f.accel), amap.accel), dt)
                totem.step(state, pad, reg, dt)
        return reg, state

    reg, _ = drive(["still"])
    assert all(abs(phase(reg, n)) < 0.01 for n in totem.PLANES)
    reg, _ = drive(["turn right"])
    # turning right about the up axis: x toward the player, the XZ plane +
    assert phase(reg, "XZ") > 0.005    # the window is the tail of the turn: weak, but its sign
    reg, _ = drive(["flat", "right down"])
    assert reg["camera.pan.x"].value > 0.3                 # right side down: the shape right
    reg, _ = drive(["flat", "far up"])
    assert reg["camera.pan.y"].value < -0.3                # the far end up: the shape up
