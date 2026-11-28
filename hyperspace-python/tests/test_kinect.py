"""The Kinect device (`kinect.py`): depth to points, and the device
over a stand-in sensor. No libfreenect and no hardware."""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace as NS

import numpy as np
import pytest

from hyperspace import devices, kinect
from hyperspace import graph as G
from hyperspace.media import ids
from hyperspace.media.source import READY

F = 575.0
O = kinect.Options


def until(fn, s: float = 3.0) -> bool:
    end = time.monotonic() + s
    while time.monotonic() < end:
        if fn():
            return True
        time.sleep(0.005)
    return False


def depth_at(*pixels, shape=(480, 640)) -> np.ndarray:
    d = np.zeros(shape, np.uint16)
    for row, col, mm in pixels:
        d[row, col] = mm
    return d


class FakeSensor:
    """Frames from a list, then nothing (or the fault it is given)."""

    def __init__(self, frames, fault=None, open_fault=None):
        self.frames, self.fault, self.open_fault = list(frames), fault, open_fault
        self.focal = F
        self.closed = threading.Event()

    def open(self):
        if self.open_fault:
            raise self.open_fault

    def read(self):
        if self.frames:
            return self.frames.pop(0)
        if self.fault:
            raise self.fault
        time.sleep(0.005)
        return None

    def close(self):
        self.closed.set()


def test_a_pixel_becomes_the_point_it_was_seen_at():
    """The pinhole run backwards: the axis is (0, 0), an offset pixel is
    (u − cx)·z/f out, up is up, and nearer is a larger z with `centre` at 0."""
    d = depth_at((240, 320, 2000), (240, 320 + 115, 2000), (240 - 115, 320, 1000))
    pts, cols = kinect.deproject(d, F, O(step=1, mirror=False))
    assert cols is None and pts.dtype == np.float32 and pts.flags.c_contiguous
    assert np.allclose(pts, [[0, 0.2, 1.0], [0, 0, 0], [0.4, 0, 0]], atol=1e-6)
    mirrored, _ = kinect.deproject(d, F, O(step=1))
    assert np.allclose(mirrored * [-1, 1, 1], pts)


def test_no_reading_and_out_of_range_are_dropped_and_the_edges_kept():
    d = depth_at((0, 0, 0), (0, 2, 499), (0, 4, 500), (0, 6, 4500), (0, 8, 4501))
    pts, _ = kinect.deproject(d, F, O(step=1))
    assert np.allclose(2.0 - pts[:, 2], [0.5, 4.5])
    # `near = 0` still reads 0 as no reading
    assert len(kinect.deproject(depth_at(), F, O(step=1, near=0.0))[0]) == 0


def test_a_step_samples_pixels_and_moves_none():
    d = np.full((480, 640), 2000, np.uint16)
    full, _ = kinect.deproject(d, F, O(step=1))
    half, _ = kinect.deproject(d, F, O(step=2))
    assert len(full) == 480 * 640 and len(half) == 240 * 320
    assert np.allclose(half, full.reshape(480, 640, 3)[::2, ::2].reshape(-1, 3))


def test_colours_are_the_points_own():
    rgb = np.zeros((480, 640, 3), np.uint8)
    rgb[240, 320] = (255, 0, 51)
    _, cols = kinect.deproject(depth_at((240, 320, 2000)), F, O(step=2), rgb)
    assert np.allclose(cols, [[1.0, 0.0, 0.2]])


def test_the_depth_picture_is_near_white_far_grey_unread_black_and_mirrored():
    px = kinect.depth_picture(depth_at((0, 0, 500), (0, 1, 4500)), O())
    assert px.shape == (480, 640, 4) and (px[..., 3] == 255).all()
    assert px[0, 639, 0] == 255 and px[0, 638, 0] == 40 and px[0, 0, 0] == 0


@pytest.mark.parametrize("entry", [
    {"near": 3, "far": 1}, {"near": -1}, {"step": 0}, {"step": 1.5}, {"index": True},
    {"far": float("inf")}, {"mirror": 1}, {"centre": "2"}])
def test_a_bad_entry_is_refused_by_name(entry):
    with pytest.raises(ValueError, match=next(iter(entry))):
        O.of(entry)


def device(sensors, **entry):
    made = iter(sensors)
    return kinect.KinectDevice("room", entry, sensor=lambda o: next(made))


def test_frames_become_the_devices_cloud_and_a_held_picture():
    d1, d2 = depth_at((240, 320, 2000)), depth_at((240, 320, 2000), (0, 0, 1000))
    sensor = FakeSensor([(d1, None)])
    d = device([sensor])
    assert d.sources[0].address == "cloud:room" and d.feeds == ()
    d.open()
    try:
        assert until(lambda: d.status == "connected")
        d.poll(1 / 60, 7.0)
        assert d.cloud.n == 1 and d.cloud.t == 7.0 and d.cloud.frame == 0
        same = d.cloud
        d.poll(1 / 60, 8.0)
        assert d.cloud is same                    # no new frame: not uploaded again
        src = d.media_sources()["kinect:room/depth"]
        assert src.latest() is None               # nobody held it
        src.open()
        sensor.frames.append((d2, None))
        assert until(lambda: src.latest() is not None) and src.status == READY
        d.poll(1 / 60, 9.0)
        assert d.cloud.n == 2 and d.cloud.frame == 1
    finally:
        d.close()
    assert sensor.closed.is_set() and d.cloud is None and d.status == "lost"
    assert d.media_sources() == {}


def test_a_colour_picture_is_published_once_and_a_silent_colour_stream_is_let_go():
    """Colour that stops while depth goes on is not live: the
    same picture is never published again, and a stream silent for `QUIET_S`
    gives its last one up, so no moving point wears it."""
    depth, rgb = depth_at((240, 320, 2000)), np.full((480, 640, 3), 9, np.uint8)
    sensor = FakeSensor([(depth, None)])
    d = device([sensor], colors=True)
    d.open()
    try:
        assert until(lambda: d.status == "connected")
        src = d.media_sources()["kinect:room/color"]
        src.open()
        sensor.frames += [(depth, rgb), (depth, rgb), (depth, rgb)]
        assert until(lambda: d._fresh[0] == 3)
        assert src.latest().frame == 1
        sensor.frames.append((depth, rgb.copy()))
        assert until(lambda: src.latest().frame == 2)
    finally:
        d.close()
    s = kinect.Sensor(O(colors=True))
    s._lib = NS(freenect_process_events_timeout=lambda c, tv: 0,
                freenect_stop_video=lambda v: 0, freenect_start_video=lambda v: 0)
    s._rgb, now = rgb, time.monotonic()
    s._heard = {"depth": now, "video": now}
    s.read()
    assert s._rgb is rgb
    s._heard["video"] = now - kinect.QUIET_S - 0.1
    s.read()
    assert s._rgb is None


def test_a_sensor_that_stops_is_said_its_cloud_goes_and_it_comes_back(monkeypatch):
    monkeypatch.setattr(kinect, "RETRY_S", 0.3)
    f = (depth_at((240, 320, 2000)), None)
    first = FakeSensor([f], fault=kinect.Fault("the Kinect went away"))
    d = device([first, FakeSensor([f])])
    d.open()
    try:
        assert until(lambda: d.status == "error: the Kinect went away")
        d.poll(1 / 60, 1.0)
        assert d.cloud is None and first.closed.is_set()
        assert until(lambda: d.status == "connected")
        d.poll(1 / 60, 2.0)
        assert d.cloud.frame == 1                 # ids count on, so the GPU takes it
    finally:
        d.close()


def test_a_silent_sensor_is_reopened(monkeypatch):
    monkeypatch.setattr(kinect, "STALL_S", 0.05)
    d = device([FakeSensor([])])
    d.open()
    try:
        assert until(lambda: "stopped sending" in d.status)
    finally:
        d.close()


def test_a_stream_that_starts_silent_is_started_again():
    """The colour stream that came up mute: the sensor stops and
    starts that one, leaves the other, and gives it `QUIET_S` again."""
    calls = []
    s = kinect.Sensor(O(colors=True))
    s._lib = NS(
        freenect_process_events_timeout=lambda c, tv: 0,
        freenect_stop_video=lambda d: calls.append("stop video") or 0,
        freenect_start_video=lambda d: calls.append("start video") or 0)
    now = time.monotonic()
    s._heard = {"depth": now, "video": now - kinect.QUIET_S - 0.1}
    assert s.read() is None
    assert calls == ["stop video", "start video"]
    s.read()
    assert len(calls) == 2
    s._lib.freenect_start_video = lambda d: -1
    s._heard["video"] = now - 10
    with pytest.raises(kinect.Fault, match="video start"):
        s.read()


def test_opening_waits_for_nothing_and_a_busy_sensor_is_said():
    d = device([FakeSensor([], open_fault=kinect.Fault("another app holds the Kinect"))])
    t = time.monotonic()
    d.open()
    assert time.monotonic() - t < 0.5
    try:
        assert until(lambda: d.status == "error: another app holds the Kinect")
    finally:
        d.close()


def test_the_kind_the_graph_and_the_media_ids_know_it():
    assert devices.kinds()["kinect"] is kinect.KinectDevice
    assert G.cloud_roles([NS(kind="kinect", role="room"), NS(kind="midi", role="m")]) == ("room",)
    assert ids.parse("kinect:room/depth") == ("kinect", "room/depth")


def test_the_registry_publishes_its_cloud_and_its_picture(monkeypatch):
    frame = (depth_at((240, 320, 2000)), None)
    monkeypatch.setattr(kinect.KinectDevice.__init__, "__kwdefaults__",
                        {"io": None, "sensor": lambda o: FakeSensor([frame])})
    reg = devices.DeviceRegistry([{"role": "room", "kind": "kinect"}], devices.Context())
    reg.open_all()
    try:
        assert until(lambda: reg.poll(1 / 60, 1.0) or "cloud:room" in reg.clouds)
        assert list(reg.media_feeds()) == ["kinect:room/depth"]
    finally:
        reg.close()
    assert reg.clouds == {}
