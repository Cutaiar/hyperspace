"""The touch and motion lanes (pads/gesture.py) and the model table
(pads/models.py): pure maths, no controller."""

import math

import pytest

from hyperspace.pads import gesture as ge
from hyperspace.pads import models

DT = 1 / 60


def lanes(tp) -> dict[str, float]:
    return dict(zip(ge.TOUCH_LANES, tp.lanes(), strict=True))


def test_a_finger_is_x_and_y_up_high_and_lifting_lets_go():
    tp = ge.Touchpad()
    tp.step([(True, 1, 0.25, 0.1), (False, 0, 0, 0)], DT)
    got = lanes(tp)
    assert got["x"] == 0.25 and got["y"] == pytest.approx(0.9) and got["down"] == 1.0
    assert math.isnan(got["x2"]) and got["down2"] == 0.0
    assert math.isnan(got["pinch"]) and math.isnan(got["twist"])
    tp.step([(False, 1, 0, 0), (False, 0, 0, 0)], DT)
    got = lanes(tp)
    assert math.isnan(got["x"]) and got["down"] == 0.0     # not live: its routes let go


def test_pinch_and_twist_start_at_rest_and_follow_the_two_fingers():
    tp = ge.Touchpad()
    tp.step([(True, 1, 0.4, 0.5), (True, 2, 0.6, 0.5)], DT)
    assert lanes(tp)["pinch"] == 0.5 and lanes(tp)["twist"] == 0.5
    tp.step([(True, 1, 0.3, 0.5), (True, 2, 0.7, 0.5)], DT)   # twice as far apart: one octave
    assert lanes(tp)["pinch"] == pytest.approx(0.75)
    tp.step([(True, 1, 0.5, 0.3), (True, 2, 0.5, 0.7)], DT)   # a quarter turn (y down: clockwise)
    assert lanes(tp)["twist"] == pytest.approx(0.75)
    # a new second finger starts the gesture afresh
    tp.step([(True, 1, 0.5, 0.3), (True, 9, 0.5, 0.9)], DT)
    assert lanes(tp)["pinch"] == 0.5 and lanes(tp)["twist"] == 0.5


def test_a_quick_still_touch_is_a_tap_and_a_drag_is_not():
    tp = ge.Touchpad()
    for _ in range(5):
        tp.step([(True, 1, 0.5, 0.5)], DT)
        assert lanes(tp)["tap"] == 0.0
    tp.step([(False, 1, 0, 0)], DT)
    assert lanes(tp)["tap"] == 1.0
    tp.step([(False, 1, 0, 0)], DT)
    assert lanes(tp)["tap"] == 0.0                          # one frame
    for k in range(5):
        tp.step([(True, 2, 0.1 + 0.1 * k, 0.5)], DT)
    tp.step([(False, 2, 0, 0)], DT)
    assert lanes(tp)["tap"] == 0.0


def motion_lanes(m) -> dict[str, float]:
    return dict(zip(ge.MOTION_LANES, m.lanes(), strict=True))


def settle(m, gyro, accel, n=120):
    for _ in range(n):
        m.step(gyro, accel, DT)


def test_tilt_reads_gravity_with_the_documented_signs():
    m = ge.Motion()
    settle(m, (0, 0, 0), (0.0, 1.0, 0.0))                   # flat, face up
    got = motion_lanes(m)
    assert got["roll"] == pytest.approx(0.5) and got["pitch"] == pytest.approx(0.5)
    t = math.radians(30)
    settle(m, (0, 0, 0), (-math.sin(t), math.cos(t), 0.0))   # right side down 30°
    assert motion_lanes(m)["roll"] == pytest.approx(0.5 + 0.5 * 30 / ge.TILT_DEG, abs=1e-3)
    settle(m, (0, 0, 0), (0.0, math.cos(t), -math.sin(t)))   # far edge up 30°
    assert motion_lanes(m)["pitch"] == pytest.approx(0.5 + 0.5 * 30 / ge.TILT_DEG, abs=1e-3)


def test_spin_yaw_leaks_home_and_a_jolt_is_one_shake():
    m = ge.Motion()
    settle(m, (0, 0, 0), (0, 1, 0), 10)
    m.step((0.0, -180.0, 0.0), (0, 1, 0), 0.25)              # turning right at 180°/s
    got = motion_lanes(m)
    assert got["spin.yaw"] == pytest.approx(0.75) and got["yaw"] > 0.5
    turned = motion_lanes(m)["yaw"]
    settle(m, (0, 0, 0), (0, 1, 0), 60 * 3)                  # one time constant still
    assert motion_lanes(m)["yaw"] - 0.5 == pytest.approx((turned - 0.5) / math.e, rel=0.05)
    settle(m, (0, 0, 0), (0, 1, 0), 60 * 30)
    assert motion_lanes(m)["yaw"] == pytest.approx(0.5, abs=1e-3)
    m.step((0, 0, 0), (0.0, 3.0, 0.0), DT)                   # a 2 g jolt
    assert motion_lanes(m)["shake"] == 1.0 and motion_lanes(m)["energy"] > 0
    m.step((0, 0, 0), (0.0, 3.0, 0.0), DT)
    assert motion_lanes(m)["shake"] == 0.0                   # refractory
    settle(m, (0, 0, 0), (0, 1, 0), 60)
    assert motion_lanes(m)["energy"] < 0.05


def test_models_ids_specs_and_glfw_guids():
    edge = models.MODELS["edge"]
    assert models.by_ids(0x054C, 0x0DF2) is edge
    assert models.by_ids(0x045E, 0x0B13).id == "xbox"        # any Microsoft pad
    assert models.by_ids(0x1234, 0x5678).id == "generic" and models.by_ids(None, None).id == "generic"
    assert models.glfw_ids("030000004c050000f20d000000010000") == (0x054C, 0x0DF2)
    assert models.glfw_ids("030000005e040000130b000009050000") == (0x045E, 0x0B13)
    assert models.glfw_ids(None) == (None, None) and models.glfw_ids("78696e70757401") == (None, None)
    assert models.parse_spec(" Edge ") == "edge" and models.parse_spec("054C:0DF2") == "054c:0df2"
    assert models.parse_spec("wiimote") is None and models.parse_spec(3) is None
    for spec, ok in (("any", True), ("edge", True), ("sony", True), ("dualsense", False),
                     ("xbox", False), ("054c:0df2", True), ("054c:0ce6", False)):
        assert models.matches(spec, edge, 0x054C, 0x0DF2) is ok, spec
    assert edge.has("back") and not models.MODELS["dualsense"].has("back")
    assert edge.outputs == {"light", "rumble", "triggers", "players", "mic"}
    assert models.N_CANON > max(models.CANON.values())
    assert models.is_model(edge) and not models.is_model(object())
