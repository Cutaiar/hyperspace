"""The Kinect's manual controls and telemetry: requests
served on the device's own thread, the snapshot it publishes, a motor that
will not open, and nothing sent that was not asked. Over a stand-in sensor
and a stand-in libfreenect: no hardware, no libfreenect."""

from __future__ import annotations

import ctypes as C
import threading
import time
from types import SimpleNamespace as NS

import numpy as np
import pytest

from hyperspace import kinect

F = 575.0
O = kinect.Options


def until(fn, s: float = 3.0) -> bool:
    end = time.monotonic() + s
    while time.monotonic() < end:
        if fn():
            return True
        time.sleep(0.005)
    return False


def depth(*pixels) -> np.ndarray:
    d = np.zeros((480, 640), np.uint16)
    for row, col, mm in pixels:
        d[row, col] = mm
    return d


class Steered:
    """A sensor that streams one picture every few ms and takes requests."""

    def __init__(self, picture=None, fail=(), gate=None, fault=None, o=None):
        self.picture = picture if picture is not None else depth((240, 320, 2000))
        self.focal = F
        self.o = o or O()
        self.applied: list[tuple[str, str, object]] = []
        self.polled = 0
        self.fail, self.gate, self.fault = set(fail), gate, fault
        self.closed = threading.Event()
        self.entered = threading.Event()

    def open(self):
        pass

    def read(self):
        time.sleep(0.004)
        return self.picture, None

    def poll(self, now):
        self.polled += 1

    def apply(self, kind, value):
        self.applied.append((threading.current_thread().name, kind, value))
        self.entered.set()
        if self.gate is not None:
            self.gate.wait(3)
        if kind in ("reconnect",) and self.fault:
            raise self.fault
        if kind in self.fail:
            return f"{kind}: libfreenect said -1"
        return ""

    def info(self):
        return {"model": "1414", "tilt": 1.0, "tilt_status": "stopped", "accel": (0.0, 9.8, 0.0),
                "frames": {"depth": 0, "video": 3}, "restarts": 2, "can": {"tilt": "", "led": ""}}

    def close(self):
        self.closed.set()


def device(*sensors, **entry):
    made = iter(sensors)
    return kinect.KinectDevice("room", entry, sensor=lambda o: next(made))


def live(d, s=None) -> None:
    assert until(lambda: d.status == "connected")
    assert until(lambda: d.telemetry.live)


def test_requests_are_served_on_the_devices_thread_in_the_order_asked():
    s = Steered()
    d = device(s)
    d.open()
    try:
        live(d)
        for kind, v in (("tilt", 10.0), ("led", 3), ("ir", 20), ("video", "ir")):
            assert d.request(kind, v) == ""
        assert until(lambda: len(s.applied) == 4)
    finally:
        d.close()
    assert [(k, v) for _, k, v in s.applied] == [("tilt", 10.0), ("led", 3), ("ir", 20), ("video", "ir")]
    assert {n for n, _, _ in s.applied} == {"kinect-room"}
    assert threading.current_thread().name not in {n for n, _, _ in s.applied}


def test_nothing_is_sent_that_was_not_asked():
    """Opening, streaming and polling the motor make no request."""
    s = Steered()
    d = device(s)
    d.open()
    try:
        live(d)
        assert until(lambda: s.polled > 2)
        time.sleep(0.1)
    finally:
        d.close()
    assert s.applied == []


def test_a_request_is_checked_before_it_is_queued():
    s = Steered()
    d = device(s)
    assert d.request("tilt", 5) == "no Kinect is connected"        # not open
    d.open()
    try:
        live(d)
        assert "not a number" in d.request("tilt", "up")
        assert "not a number" in d.request("tilt", float("nan"))
        assert "not one of" in d.request("led", 5)                   # 5 is no LED colour
        assert "not off, color, ir" in d.request("video", "uv").replace("or ", "")
        assert "not on or off" in d.request("flicker", 1)
        assert "not a Kinect request" in d.request("yaw", 3)
        time.sleep(0.05)
    finally:
        d.close()
    assert s.applied == []
    assert d.request("tilt", 1) == "no Kinect is connected"        # closed


@pytest.mark.parametrize(("kind", "value", "got"), [
    ("tilt", 99, 31.0), ("tilt", -99, -31.0), ("tilt", 4.5, 4.5),
    ("ir", 0, 1), ("ir", 80, 50), ("ir", 29.6, 30), ("exposure", 5, 100), ("exposure", 1e9, 33333)])
def test_a_drag_that_overshoots_lands_on_the_edge(kind, value, got):
    assert kinect.check(kind, value) == (got, "")


def test_a_failed_request_is_said_and_the_stream_goes_on():
    s = Steered(fail={"led"})
    d = device(s)
    d.open()
    try:
        live(d)
        d.request("led", 1)
        assert until(lambda: "led: libfreenect said -1" in d.telemetry.said)
        d.request("tilt", 3)
        assert until(lambda: d.telemetry.said == "sent tilt 3.0")
        n = d.telemetry.frames
        assert until(lambda: d.telemetry.frames > n) and d.status == "connected"
    finally:
        d.close()


def test_the_snapshot_is_whole_and_swapped_in_not_edited():
    s = Steered(depth((10, 10, 1000), (12, 12, 3000), (14, 14, 2000)))
    d = device(s)
    d.open()
    try:
        live(d)
        assert until(lambda: (d.watch() or True) and d.telemetry.share is not None)
        one = d.telemetry
        assert until(lambda: d.telemetry is not one and d.telemetry.seq > one.seq)
        assert until(lambda: d.telemetry.depth_fps > 0)        # a rate is of the last second
        t = d.telemetry
        assert t.model == "1414" and t.live and t.video_frames == 3 and t.restarts == 2
        assert t.tilt == 1.0 and t.tilt_status == "stopped" and t.accel == (0.0, 9.8, 0.0)
        assert t.nearest == pytest.approx(1.0) and t.median == pytest.approx(2.0)
        assert t.share == pytest.approx(3 / (480 * 640))
        assert t.points == 3 and t.frames > 0 and t.depth_fps > 0
        with pytest.raises(AttributeError):
            t.frames = 0                          # frozen
    finally:
        d.close()
    assert not d.telemetry.live


def test_close_with_requests_waiting_drops_them():
    gate = threading.Event()
    s = Steered(gate=gate)
    d = device(s)
    d.open()
    live(d)
    d.request("tilt", 1.0)
    assert s.entered.wait(2)                       # the thread is inside the first, held
    for k in (2.0, 3.0, 4.0):
        assert d.request("tilt", k) == ""
    closer = threading.Thread(target=d.close)
    closer.start()
    assert until(lambda: d._stop.is_set())
    gate.set()
    closer.join(5)
    assert not closer.is_alive() and s.closed.is_set()
    assert [v for _, _, v in s.applied] == [1.0]   # the others were never sent
    assert d.request("tilt", 5.0) == "no Kinect is connected"


def test_a_reconnect_does_not_send_what_was_waiting_to_the_next_sensor(monkeypatch):
    monkeypatch.setattr(kinect, "RETRY_S", 0.05)
    first = Steered(fault=kinect.Fault("reconnecting, as asked"))
    second = Steered()
    d = device(first, second)
    d.open()
    try:
        live(d)
        d.request("reconnect")
        d.request("tilt", 20.0)
        d.request("led", 2)
        assert until(lambda: first.closed.is_set())
        assert until(lambda: d.telemetry.live and second.polled > 0)
        time.sleep(0.1)
        assert d.telemetry.reconnects == 1
    finally:
        d.close()
    assert [k for _, k, _ in first.applied] == ["reconnect"]
    assert second.applied == []


def test_counts_go_on_across_a_reconnect(monkeypatch):
    monkeypatch.setattr(kinect, "RETRY_S", 0.05)
    first, second = Steered(fault=kinect.Fault("x")), Steered()
    d = device(first, second)
    d.open()
    try:
        live(d)
        d.request("reconnect")
        assert until(lambda: second.polled > 0 and d.telemetry.live)
        assert until(lambda: d.telemetry.restarts == 4 and d.telemetry.video_frames == 6)
    finally:
        d.close()


def test_a_sensor_with_no_requests_is_said_not_crashed():
    class Plain(Steered):
        apply = None
    s = Plain()
    d = device(s)
    d.open()
    try:
        live(d)
        d.request("tilt", 1)
        assert until(lambda: "takes no requests" in d.telemetry.said)
        assert d.status == "connected"
    finally:
        d.close()


def test_the_placement_changes_this_run_and_the_entry_stays():
    entry = {"role": "room", "kind": "kinect", "near": 0.5}
    d = kinect.KinectDevice("room", entry, sensor=lambda o: Steered())
    d.open()
    try:
        live(d)
        assert d.place(near=1.0, far=3.0, centre=1.5, step=4, mirror=False) == ""
        o = d.options
        assert (o.near, o.far, o.centre, o.step, o.mirror) == (1.0, 3.0, 1.5, 4, False)
        assert entry == {"role": "room", "kind": "kinect", "near": 0.5}     # never written
        assert "near" in d.place(near=9.0) and d.options.near == 1.0          # near < far, as the entry's
        assert "not a placement setting" in d.place(colors=True)
        assert d.options.colors is False
        assert until(lambda: d._fresh is not None and d._fresh[1].shape[0] == 1)    # 2 m, in 1–3
        assert d.place(near=2.5) == ""
        assert until(lambda: d._fresh[1].shape[0] == 0)                              # …and out of 2.5–3
    finally:
        d.close()
    d.open()                                                                  # opened again: the entry's
    try:
        assert d.options.near == 0.5 and d.options.step == 2
    finally:
        d.close()


# ---------------------------------------------------------------- the real Sensor over a stand-in libfreenect

class Lib:
    """freenect_* functions that record their calls. `motor_opens`: whether
    a device opened with the motor part takes."""

    def __init__(self, motor_opens=True, enabled=3, accel=(-0.38, 9.44, 0.2), tilt=1.0):
        self.calls: list[tuple] = []
        self.motor_opens, self.enabled, self.accel, self.tilt = motor_opens, enabled, accel, tilt
        self.subs = 0
        self.missing: set[str] = set()
        self.status = 0

    def __getattr__(self, name):
        if not name.startswith("freenect_") or name.removeprefix("freenect_") in self.missing:
            raise AttributeError(name)

        def call(*a):
            self.calls.append((name.removeprefix("freenect_"), *a))
            return getattr(self, "_" + name.removeprefix("freenect_"), lambda *a: 0)(*a)
        return call

    def _select_subdevices(self, ctx, sub):
        self.subs = sub

    def _num_devices(self, ctx):
        return 1

    def _open_device(self, ctx, dev, i):
        return -1 if (self.subs & 1 and not self.motor_opens) else 0

    def _camera_to_world(self, dev, x, y, z, bx, by):
        bx._obj.value, by._obj.value = 0.5, 0.5

    def _enabled_subdevices(self, ctx):
        return self.enabled

    def _get_tilt_state(self, dev):
        return 1

    def _get_tilt_degs(self, st):
        return self.tilt

    def _get_tilt_status(self, st):
        return self.status

    def _get_mks_accel(self, st, bx, by, bz):
        bx._obj.value, by._obj.value, bz._obj.value = self.accel

    def _get_ir_brightness(self, dev):
        return 30

    def _get_exposure(self, dev, b):
        b._obj.value = 10000
        return 0

    def named(self, *names):
        return [c for c in self.calls if c[0] in names]


@pytest.fixture()
def lib(monkeypatch):
    lib = Lib()
    monkeypatch.setattr(kinect, "_load", lambda: lib)
    monkeypatch.setattr(kinect, "usb_cameras", lambda: [267])
    return lib


MOVES = ("set_tilt_degs", "set_led", "set_ir_brightness", "set_flag", "set_exposure")


def test_the_model_is_read_from_the_cameras_bcd_device():
    assert kinect.model_name(267) == "1414"
    assert kinect.model_name(None) == "unknown"
    assert "bcdDevice 272" in kinect.model_name(272)


def test_opening_reads_the_motor_and_the_camera_and_moves_nothing(lib):
    s = kinect.Sensor(O())
    s.open()
    assert lib.named(*MOVES) == []
    assert lib.subs == 0x03                       # camera and motor; never the audio (0x04)
    i = s.info()
    assert i["model"] == "1414" and i["motor_why"] == ""
    assert i["tilt"] == 1.0 and i["tilt_status"] == "stopped"
    assert i["accel"] == (-0.38, 9.44, 0.2)
    assert i["ir"] == 30 and i["exposure"] == 10000
    assert lib.named("start_depth") and not lib.named("start_video")


def test_the_motor_is_polled_slowly_and_only_read(lib):
    s = kinect.Sensor(O())
    s.open()
    n = len(lib.named("update_tilt_state"))
    t = time.monotonic()
    s.poll(t + 0.01)                              # too soon
    assert len(lib.named("update_tilt_state")) == n
    s.poll(t + kinect.TILT_POLL_S + 0.01)
    assert len(lib.named("update_tilt_state")) == n + 1
    lib.status, lib.tilt = 4, 12.0
    s.poll(t + 2 * kinect.TILT_POLL_S + 0.1)
    assert s.info()["tilt_status"] == "moving" and s.info()["tilt"] == 12.0
    assert lib.named(*MOVES) == []


def test_a_motor_that_will_not_open_costs_the_camera_nothing(monkeypatch, lib):
    lib.motor_opens = False
    s = kinect.Sensor(O())
    s.open()
    i = s.info()
    assert "motor would not open" in i["motor_why"] and "camera runs without it" in i["motor_why"]
    assert [c[2] for c in lib.named("select_subdevices")] == [0x03, 0x02]    # tried, then camera alone
    assert lib.named("start_depth") and s.focal > 0                          # and it streams
    assert i["tilt"] is None and i["accel"] is None
    assert "motor would not open" in s.can()["tilt"] and "motor would not open" in s.can()["led"]
    assert s.can()["ir"] == ""                                               # the camera's own stay
    assert "motor would not open" in s.apply("tilt", 5)
    assert lib.named(*MOVES) == []
    s.poll(time.monotonic() + 5)
    assert lib.named("update_tilt_state") == []                              # and is not asked


def test_a_camera_that_will_not_open_is_still_the_cameras_fault(lib):
    lib.motor_opens = False
    lib._open_device = lambda ctx, dev, i: -1
    with pytest.raises(kinect.Fault, match="would not open"):
        kinect.Sensor(O()).open()


def test_an_entry_can_leave_the_motor_alone(lib):
    s = kinect.Sensor(O(motor=False))
    s.open()
    assert lib.subs == 0x02 and "motor = false" in s.motor_why


def test_a_model_whose_motor_stays_closed_is_said(lib):
    lib.enabled = 0x02
    s = kinect.Sensor(O())
    s.open()
    assert "closed" in s.motor_why and s.tilt is None


def test_a_libfreenect_without_a_call_disables_that_control_only(lib):
    lib.missing = {"set_ir_brightness", "get_ir_brightness"}
    s = kinect.Sensor(O())
    s.open()
    assert "no freenect_set_ir_brightness" in s.can()["ir"] and s.can()["tilt"] == ""
    assert s.ir is None


def test_a_tilt_is_clamped_and_sent_only_when_asked(lib):
    s = kinect.Sensor(O())
    s.open()
    assert s.apply("tilt", 99) == ""
    assert lib.named("set_tilt_degs")[-1][2] == 31.0 and s.info()["target"] == 31.0
    assert s.apply("tilt", -3.5) == ""
    assert [c[2] for c in lib.named("set_tilt_degs")] == [31.0, -3.5]
    s.poll(time.monotonic() + 5)
    assert len(lib.named("set_tilt_degs")) == 2
    lib._set_tilt_degs = lambda dev, deg: -1
    assert "libfreenect said -1" in s.apply("tilt", 1)
    assert s.info()["target"] == -3.5               # a refused one is not the target


def test_the_led_has_six_colours_and_five_is_not_one(lib):
    s = kinect.Sensor(O())
    s.open()
    sent = []
    for name, code in kinect.LEDS:
        assert s.apply("led", code) == ""
        sent.append((s.info()["led"], lib.named("set_led")[-1][2]))
    assert sent == [("off", 0), ("green", 1), ("red", 2), ("yellow", 3), ("blink green", 4),
                    ("blink red / yellow", 6)]


def test_the_infrared_brightness_is_clamped_and_read_back(lib):
    s = kinect.Sensor(O())
    s.open()
    assert s.apply("ir", 80) == ""
    assert lib.named("set_ir_brightness")[-1][2] == 50
    assert s.info()["ir"] == 30                    # what the sensor says, not what was asked


def test_video_is_one_stream_and_a_change_stops_and_starts_them(lib):
    s = kinect.Sensor(O())
    s.open()
    assert s.apply("video", "color") == ""
    names = [c[0] for c in lib.calls]
    tail = names[names.index("stop_depth"):]
    assert tail[:2] == ["stop_depth", "find_depth_mode"] or "stop_depth" in tail
    assert lib.named("find_depth_mode")[-1][2] == 4            # registered depth beside colour
    assert lib.named("find_video_mode")[-1][2] == 0 and lib.named("start_video")
    assert s.o.colors and not s.o.infrared and s.info()["restarts"] == 1
    assert s.apply("video", "ir") == ""
    assert lib.named("find_video_mode")[-1][2] == 2            # IR 8-bit, not both
    assert lib.named("find_depth_mode")[-1][2] == 5
    assert not s.o.colors and s.o.infrared and s._heard.keys() == {"depth", "video"}
    n = len(lib.calls)
    assert s.apply("video", "ir") == "" and len(lib.calls) == n    # already so: nothing sent
    assert s.apply("video", "off") == ""
    assert list(s._heard) == ["depth"]


def test_exposure_waits_for_auto_exposure_to_be_off_and_for_colour(lib):
    s = kinect.Sensor(O())
    s.open()
    assert "colour stream" in s.apply("exposure", 5000)
    assert "colour stream" in s.apply("auto_exposure", False)
    s.apply("video", "color")
    assert "auto exposure is on" in s.apply("exposure", 5000)
    assert s.apply("auto_exposure", False) == ""
    assert lib.named("set_flag")[-1][2:] == (1 << 14, 0)
    assert s.apply("flicker", False) == "" and lib.named("set_flag")[-1][2:] == (1 << 7, 0)
    assert s.apply("white_balance", True) == "" and lib.named("set_flag")[-1][2:] == (1 << 1, 1)
    assert s.apply("exposure", 5000) == ""
    assert lib.named("set_exposure")[-1][2] == 5000
    assert s.info()["flags"] == {"auto_exposure": False, "flicker": False, "white_balance": True}


def test_a_stream_restart_stops_and_starts_each_and_is_counted(lib):
    s = kinect.Sensor(O(colors=True))
    s.open()
    before = len(lib.named("start_depth"))
    assert s.apply("restart", None) == "" and s.info()["restarts"] == 1
    assert len(lib.named("start_depth")) == before + 1 and len(lib.named("start_video")) == 2
    with pytest.raises(kinect.Fault, match="reconnecting"):
        s.apply("reconnect", None)


def test_the_silent_stream_restart_is_counted_and_a_silent_colour_still_let_go(lib):
    s = kinect.Sensor(O(colors=True))
    s.open()
    s._rgb = np.zeros((480, 640, 3), np.uint8)
    s._heard["video"] -= kinect.QUIET_S + 1
    s._wake()
    assert s._rgb is None and s.restarts == 1


def test_a_video_frame_is_the_modes_shape(lib):
    s = kinect.Sensor(O(infrared=True))
    s.open()
    buf = (C.c_uint8 * (kinect.IR_H * kinect.W))(*([7] * (kinect.IR_H * kinect.W)))
    s._got_video(None, C.cast(buf, C.c_void_p), 0)
    assert s._rgb.shape == (kinect.IR_H, kinect.W) and s.frames["video"] == 1
    px = kinect._rgba(s._rgb, O())
    assert px.shape == (kinect.IR_H, kinect.W, 4) and px[0, 0, 0] == 7 and px[0, 0, 3] == 255


def test_the_video_choice_reaches_the_devices_options_and_pictures():
    s = NS()
    d = kinect.KinectDevice("room", {}, sensor=lambda o: Steered())
    d.open()
    try:
        live(d)
        assert set(d.media_sources()) == {"kinect:room/depth"}
        s.o = O(infrared=True)
        d._video_began(s)
        assert d.options.infrared and set(d.media_sources()) == {"kinect:room/depth", "kinect:room/ir"}
        s.o = O(colors=True)
        d._video_began(s)
        assert d.options.colors and not d.options.infrared and "kinect:room/color" in d.media_sources()
    finally:
        d.close()


def test_the_radar_profile_is_the_nearest_millimetres_a_column_in_the_band_round_the_axis():
    d = depth((240, 4, 2500), (250, 4, 1800), (100, 12, 500), (240, 636, 3000), (240, 20, 0))
    p = kinect.radar_profile(d)
    assert len(p) == kinect.RADAR_COLS
    assert p[0] == 1800                              # the nearer of two, in column 4 (the first)
    assert p[1] == 0                                 # the 100th row is outside the band: the floor and ceiling are not read
    assert p[79] == 3000 and p[2] == 0               # nothing read is 0
    assert kinect.radar_profile(depth()) == (0,) * kinect.RADAR_COLS
    assert all(isinstance(v, int) for v in p)


def test_the_profile_is_cheap():
    d = np.random.default_rng(1).integers(500, 4500, (480, 640)).astype(np.uint16)
    kinect.radar_profile(d)
    t = time.perf_counter()
    for _ in range(100):
        kinect.radar_profile(d)
    assert (time.perf_counter() - t) / 100 < 0.002     # a few tens of µs here; 2 ms is slack for a slow runner


def test_the_radar_is_made_on_the_devices_thread_only_while_watched_and_published():
    s = Steered(picture=depth((240, 484, 2000)), o=O(mirror=False))
    seen = []
    real = kinect.radar_profile
    kinect.radar_profile = lambda *a: (seen.append(threading.current_thread().name), real(*a))[1]
    d = device(s, mirror=False)
    try:
        d.open()
        live(d)
        time.sleep(0.4)
        assert d.telemetry.radar is None and seen == []          # nobody has looked: nothing is measured
        assert until(lambda: (d.watch() or True) and d.telemetry.radar is not None)
        t = d.telemetry
        assert t.focal == F and t.radar[60] == 2000 and sum(1 for v in t.radar if v) == 1
        assert t.radar == real(s.picture)
        d.watch()
        time.sleep(kinect.WATCH_S + 0.3)                         # …and it stops when they stop
        n = len(seen)
        time.sleep(0.4)
        assert len(seen) == n
    finally:
        kinect.radar_profile = real
        d.close()
    assert seen and set(seen) == {"kinect-room"}
    assert kinect.Telemetry().radar is None and kinect.Telemetry().focal == 575.0


# ---------------------------------------------------------------- a route drives it (sinks)

class Rows:
    """A binding table's sinks, as `routing.sink_values` reads them."""

    def __init__(self, *rows):
        self.rows = rows

    def sinks(self, role=None, *, enabled=True):
        return [b for b in self.rows if b.is_sink and (role is None or b.sink[0] == role)]


def sink_row(role, k, param):
    from hyperspace import routing
    return routing.Binding(f"param:{param}", routing.sink_target(role, k), routing.SINK_OP)


class Reg:
    def __init__(self, **norm):
        self.norm = norm

    def get(self, pid):
        n = self.norm.get(pid)
        return None if n is None else NS(kind=None, eff_norm=n)


def test_the_sinks_are_the_infrared_and_the_exposure_and_the_numbers_are_kept():
    d = kinect.KinectDevice("room", {})
    assert [(p.address, p.label) for p in d.sinks] == [("room:0", "infrared brightness"),
                                                       ("room:1", "exposure time")]
    assert kinect.SINK_CHANNELS[0][0] == "ir" and kinect.SINK_CHANNELS[1][0] == "exposure"   # append-only
    assert kinect.sink_value("ir", 0.0) == 1 and kinect.sink_value("ir", 1.0) == 50
    assert kinect.sink_value("ir", 2) == 50 and kinect.sink_value("ir", float("nan")) == 1
    assert kinect.sink_value("exposure", 1.0) == kinect.EXPOSURE_MAX
    assert not any(p.name in ("tilt", "led") for p in d.sinks)          # the motor is not a modulator's


def sink_device(*rows, sensor=None):
    from hyperspace import devices
    s = sensor or Steered()
    d = kinect.KinectDevice("room", {}, devices.Context(table=Rows(*rows)), sensor=lambda o: s)
    return d, s


def test_a_sink_row_sends_its_reading_as_a_request_only_when_it_moves(monkeypatch):
    monkeypatch.setattr(kinect, "SINK_S", 0.05)
    d, s = sink_device(sink_row("room", 0, "view.bright"))
    d.open()
    try:
        live(d)
        d.send(Reg(**{"view.bright": 1.0}), None)
        assert until(lambda: [k for _, k, _ in s.applied] == ["ir"])
        assert s.applied[0][2] == 50 and d.driven == {"ir"}
        for _ in range(5):
            d.send(Reg(**{"view.bright": 1.0}), None)        # the same reading: not asked again
        time.sleep(0.1)
        assert len(s.applied) == 1
        d.send(Reg(**{"view.bright": 0.0}), None)             # a rate limit: too soon after the last
        assert len(s.applied) == 1
        time.sleep(0.06)
        d.send(Reg(**{"view.bright": 0.0}), None)
        assert until(lambda: [v for _, _, v in s.applied] == [50, 1])
    finally:
        d.close()


def test_no_row_means_no_request_and_the_pane_keeps_the_hand_on_it():
    d, s = sink_device()
    d.open()
    try:
        live(d)
        d.send(Reg(), None)
        time.sleep(0.05)
        assert s.applied == [] and d.driven == frozenset()
    finally:
        d.close()


def test_a_sink_row_with_no_sensor_is_tried_again_when_one_is_there(monkeypatch):
    monkeypatch.setattr(kinect, "SINK_S", 0.0)
    d, s = sink_device(sink_row("room", 1, "p"))
    d.send(Reg(p=1.0), None)                                   # not open: refused, nothing queued
    assert d.driven == {"exposure"} and s.applied == []
    d.open()
    try:
        live(d)
        d.send(Reg(p=1.0), None)
        assert until(lambda: [(k, v) for _, k, v in s.applied] == [("exposure", kinect.EXPOSURE_MAX)])
    finally:
        d.close()


def test_a_row_on_a_channel_the_kinect_has_not_is_ignored():
    d, s = sink_device(sink_row("room", 7, "p"))
    d.open()
    try:
        live(d)
        d.send(Reg(p=1.0), None)
        time.sleep(0.05)
        assert s.applied == [] and d.driven == frozenset()
    finally:
        d.close()


def test_a_refused_sink_request_is_asked_again_when_the_setting_opens_up(monkeypatch):
    """A route steady on exposure while auto exposure is on is refused; when manual exposure becomes
    available it is sent, though the reading never moved (the value counts as sent only once taken)."""
    monkeypatch.setattr(kinect, "SINK_S", 0.02)
    s = Steered(fail={"exposure"})
    d, s = sink_device(sink_row("room", 1, "p"), sensor=s)
    d.open()
    try:
        live(d)
        reg = Reg(p=1.0)
        for _ in range(4):
            d.send(reg, None)
            time.sleep(0.03)
        assert until(lambda: len([a for a in s.applied if a[1] == "exposure"]) >= 2)   # tried, refused, tried again
        assert d.telemetry.said.startswith("exposure:")
        s.fail.clear()                                      # auto exposure turned off
        n = len(s.applied)
        assert until(lambda: (d.send(reg, None) or True) and len(s.applied) > n and not d.telemetry.said.startswith("exposure:"))
        m = len(s.applied)
        for _ in range(5):
            d.send(reg, None)
            time.sleep(0.03)
        assert len(s.applied) == m                          # taken: not asked again
    finally:
        d.close()


def test_a_route_that_stops_driving_a_setting_sends_it_again_when_it_resumes(monkeypatch):
    monkeypatch.setattr(kinect, "SINK_S", 0.02)
    d, s = sink_device(sink_row("room", 0, "p"))
    d.open()
    try:
        live(d)
        d.send(Reg(p=1.0), None)
        assert until(lambda: [v for _, k, v in s.applied if k == "ir"] == [50])
        rows, d.ctx.table.rows = d.ctx.table.rows, ()       # the row deleted or disabled: not driven
        d.send(Reg(p=1.0), None)
        assert d.driven == frozenset()
        assert d.request("ir", 7) == ""                     # the pane's hand on it
        assert until(lambda: [v for _, k, v in s.applied if k == "ir"] == [50, 7])
        time.sleep(0.03)
        d.ctx.table.rows = rows
        d.send(Reg(p=1.0), None)                            # the same route back: it takes over again
        assert until(lambda: [v for _, k, v in s.applied if k == "ir"] == [50, 7, 50])
    finally:
        d.close()


def test_the_motor_is_asked_for_only_of_a_1414_so_the_audio_is_never_claimed(monkeypatch, lib):
    """libfreenect 0.7.5 drops the motor part of a camera whose bcdDevice is not 267 and claims
    its AUDIO interface to move the motor; this never opens the audio."""
    for bcd, subs, why in ((267, 0x03, ""), (272, 0x02, "audio interface"), (None, 0x02, "could not be read")):
        lib.calls.clear()
        monkeypatch.setattr(kinect, "usb_cameras", lambda bcd=bcd: [] if bcd is None else [bcd])
        s = kinect.Sensor(O())
        s.open()
        assert [c[2] for c in lib.named("select_subdevices")] == [subs], bcd
        assert (why in s.motor_why) if why else s.motor_why == "", (bcd, s.motor_why)
        assert not any(c[2] & 0x04 for c in lib.named("select_subdevices"))     # never the audio bit
        assert "motor" in s.can()["tilt"] or not why                            # and the tilt says so
