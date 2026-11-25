"""An Xbox 360 Kinect as a device (plan 29): a live point cloud and its
depth picture, through libfreenect.

A ``kind = "kinect"`` entry publishes ``cloud:<role>`` (`devices.PointCloud`,
drawn by the render graph's point-cloud node) and the pictures
``kinect:<role>/depth`` (near white, far dark, no reading black) and, with
`colors`, ``kinect:<role>/color``. It feeds the Router nothing.

**Where the work is.** The sensor does the hard part: it projects an
infrared dot pattern and matches it on board, and sends one 11-bit
disparity a pixel. libfreenect turns that into millimetres by a lookup
table made from the sensor's own factory calibration. What is left is
`deproject`: a pinhole camera run backwards, one multiply a pixel for x and
for y, then a crop and a move into the cloud's frame. No stereo matching,
no meshing, no filtering in time.

**The frame.** Metres. The sensor looks along −z, x to the right and y up,
and `centre` metres in front of it is the origin: a nearer point has a
larger z, towards the eye. `mirror` (on by default) flips x, so a person
facing the sensor sees themselves as in a mirror. This is the sensor's
placement, so it is the entry's and no patch's; how big the cloud is drawn
is `cloud.scale`.

**The entry** (all optional): `index` (which Kinect, default 0), `near` and
`far` (metres; outside is dropped; 0.5, 4.5), `centre` (2.0), `step` (every
n-th pixel and row; 2 is at most 76 800 points), `mirror` (true), `colors`
(false: colour streams take USB bandwidth, and a dark room has none).

**Threads.** One thread per device (``kinect-<role>``) opens the sensor,
pumps libfreenect's events, makes the frames and publishes each by one
reference swap; `poll` takes the newest. It opens the camera part alone:
the motor and the audio are never claimed. A sensor that is missing, busy
or stops is said in `status` and tried again every `RETRY_S`.

A stream that starts may say nothing at all, with no error: with both on,
the colour (or the depth, if it starts second) came up in about 4 of 10
tries on a 1414 under macOS 26 (2026-11-24), in libfreenect's own example
too. Stopping and starting the silent stream brings it up, so `Sensor` does
that every `QUIET_S` until it speaks.

libfreenect is not a Python package (``brew install libfreenect``); it is
loaded inside the thread, so importing the app needs none of it."""

from __future__ import annotations

import contextlib
import ctypes as C
import ctypes.util
import math
import os
import sys
import threading
import time
from dataclasses import dataclass

import numpy as np

from . import devices
from .media.frame import MediaFrame
from .media.live import SharedSource

W, H = 640, 480
RETRY_S = 2.0        # a sensor that would not open, or stopped, is tried again after this long
STALL_S = 5.0        # no depth frame for this long: closed and opened again
QUIET_S = 1.0        # no frame of a stream for this long: that stream is started again
JOIN_S = 2.0         # closing waits this long for the thread
PUMP_US = 50_000     # one wait for USB events: how soon a close is seen
LIBS = ("/opt/homebrew/lib/libfreenect.dylib", "/usr/local/lib/libfreenect.dylib")

_RES_MEDIUM, _VIDEO_RGB, _DEPTH_REGISTERED, _DEPTH_MM = 1, 0, 4, 5
_CAMERA, _LOG_ERROR = 0x02, 1
_FAR_GREY, _NEAR_GREY = 40, 255     # the depth picture's shades at `far` and at `near`


class Fault(Exception):
    """Said as it is on the status line."""


@dataclass(frozen=True)
class Options:
    """An entry's settings, checked."""

    index: int = 0
    near: float = 0.5
    far: float = 4.5
    centre: float = 2.0
    step: int = 2
    mirror: bool = True
    colors: bool = False

    @classmethod
    def of(cls, entry: dict) -> Options:
        def number(key: str, default: float) -> float:
            v = entry.get(key, default)
            if isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v):
                raise ValueError(f"{key} = {v!r} is not a number")
            return float(v)

        def whole(key: str, default: int, lo: int, hi: int) -> int:
            v = entry.get(key, default)
            if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
                raise ValueError(f"{key} = {v!r} is not a whole number from {lo} to {hi}")
            return v

        def flag(key: str, default: bool) -> bool:
            v = entry.get(key, default)
            if not isinstance(v, bool):
                raise ValueError(f"{key} = {v!r} is not true or false")  # noqa: TRY004
            return v

        o = cls(whole("index", 0, 0, 15), number("near", 0.5), number("far", 4.5),
                number("centre", 2.0), whole("step", 2, 1, 16),
                flag("mirror", True), flag("colors", False))
        if not 0.0 <= o.near < o.far:
            raise ValueError(f"near = {o.near:g} and far = {o.far:g}: 0 <= near < far")
        return o


def deproject(depth: np.ndarray, focal: float, o: Options,
              rgb: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray | None]:
    """A depth picture (H×W uint16 millimetres, 0 no reading) as N×3 float32
    points in the cloud's frame, and their N×3 colours from `rgb` (H×W×3
    uint8, aligned to the depth) or None. `focal` is the camera's focal
    length in pixels of the full picture, square pixels, centred on (W/2,
    H/2), which is libfreenect's own model (`freenect_camera_to_world`)."""
    h, w = depth.shape
    s = o.step
    d = depth[::s, ::s].astype(np.float32) * np.float32(0.001)
    keep = (d > 0.0) & (d >= o.near) & (d <= o.far)
    rows, cols = np.nonzero(keep)
    z = d[rows, cols]
    k = z / np.float32(focal)
    x = (cols.astype(np.float32) * s - w / 2) * k
    pts = np.empty((len(z), 3), np.float32)
    pts[:, 0] = -x if o.mirror else x
    pts[:, 1] = (h / 2 - rows.astype(np.float32) * s) * k     # picture rows run down
    pts[:, 2] = o.centre - z
    if rgb is None:
        return pts, None
    return pts, rgb[::s, ::s][rows, cols].astype(np.float32) / np.float32(255.0)


def depth_picture(depth: np.ndarray, o: Options) -> np.ndarray:
    """The depth as H×W×4 uint8: `near` white, `far` dark grey, nothing read
    (or outside them) black; mirrored as the cloud is."""
    d = depth.astype(np.float32) * np.float32(0.001)
    keep = (d > 0.0) & (d >= o.near) & (d <= o.far)
    t = (o.far - d) / (o.far - o.near)
    g = np.where(keep, _FAR_GREY + (_NEAR_GREY - _FAR_GREY) * t + 0.5, 0.0).astype(np.uint8)
    return _rgba(g[:, :, None], o)


def _rgba(rgb: np.ndarray, o: Options) -> np.ndarray:
    out = np.full((*rgb.shape[:2], 4), 255, np.uint8)
    out[..., :3] = rgb[:, ::-1] if o.mirror else rgb
    return out


# ---------------------------------------------------------------- libfreenect

class _Mode(C.Structure):
    _fields_ = [("reserved", C.c_uint32), ("resolution", C.c_int), ("format", C.c_int32),
                ("bytes", C.c_int32), ("width", C.c_int16), ("height", C.c_int16),
                ("data_bits", C.c_int8), ("padding_bits", C.c_int8),
                ("framerate", C.c_int8), ("is_valid", C.c_int8)]


class _Timeval(C.Structure):
    _fields_ = [("tv_sec", C.c_long),
                ("tv_usec", C.c_int32 if sys.platform == "darwin" else C.c_long)]


_FRAME_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_uint32)
_LOG_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_int, C.c_char_p)


def _load() -> C.CDLL:
    names = [p for p in LIBS if os.path.exists(p)]
    found = ctypes.util.find_library("freenect")
    if found:
        names.append(found)
    for n in names:
        try:
            lib = C.CDLL(n)
        except OSError:
            continue
        break
    else:
        raise Fault("libfreenect not installed (brew install libfreenect)")
    p, i, dbl = C.c_void_p, C.c_int, C.POINTER(C.c_double)
    for name, res, args in (
            ("init", i, [C.POINTER(p), p]), ("shutdown", i, [p]),
            ("num_devices", i, [p]), ("select_subdevices", None, [p, i]),
            ("set_log_level", None, [p, i]), ("set_log_callback", None, [p, _LOG_CB]),
            ("open_device", i, [p, C.POINTER(p), i]), ("close_device", i, [p]),
            ("find_depth_mode", _Mode, [i, i]), ("find_video_mode", _Mode, [i, i]),
            ("set_depth_mode", i, [p, _Mode]), ("set_video_mode", i, [p, _Mode]),
            ("set_depth_callback", None, [p, _FRAME_CB]),
            ("set_video_callback", None, [p, _FRAME_CB]),
            ("start_depth", i, [p]), ("start_video", i, [p]),
            ("stop_depth", i, [p]), ("stop_video", i, [p]),
            ("process_events_timeout", i, [p, C.POINTER(_Timeval)]),
            ("camera_to_world", None, [p, i, i, i, dbl, dbl])):
        fn = getattr(lib, f"freenect_{name}")
        fn.restype, fn.argtypes = res, args
    return lib


class Sensor:
    """One Kinect through libfreenect, used only on its device's thread."""

    def __init__(self, o: Options):
        self.o = o
        self.focal = 0.0
        self._lib: C.CDLL | None = None
        self._ctx = C.c_void_p()
        self._dev = C.c_void_p()
        self._depth: np.ndarray | None = None
        self._rgb: np.ndarray | None = None
        self._said = ""
        self._heard: dict[str, float] = {}     # stream → its last frame's time

    def open(self) -> None:
        self._lib = lib = _load()
        if lib.freenect_init(C.byref(self._ctx), None) < 0:
            raise Fault("libfreenect would not start")
        # held by self: libfreenect keeps the pointers
        self._on_log = _LOG_CB(self._log)
        self._on_depth = _FRAME_CB(self._got_depth)
        self._on_video = _FRAME_CB(self._got_video)
        lib.freenect_set_log_level(self._ctx, _LOG_ERROR)
        lib.freenect_set_log_callback(self._ctx, self._on_log)
        lib.freenect_select_subdevices(self._ctx, _CAMERA)
        if lib.freenect_num_devices(self._ctx) <= self.o.index:
            raise Fault("no Kinect found (its 12 V adapter and USB)")
        if lib.freenect_open_device(self._ctx, C.byref(self._dev), self.o.index) < 0:
            self._dev = C.c_void_p()
            if "ERROR_ACCESS" in self._said or "ERROR_BUSY" in self._said:
                raise Fault("another app holds the Kinect (Logitech G Hub does)")
            raise Fault(self._said or "the Kinect would not open")
        fmt = _DEPTH_REGISTERED if self.o.colors else _DEPTH_MM
        mode = lib.freenect_find_depth_mode(_RES_MEDIUM, fmt)
        self._ok(lib.freenect_set_depth_mode(self._dev, mode), "depth mode")
        lib.freenect_set_depth_callback(self._dev, self._on_depth)
        if self.o.colors:
            vmode = lib.freenect_find_video_mode(_RES_MEDIUM, _VIDEO_RGB)
            self._ok(lib.freenect_set_video_mode(self._dev, vmode), "colour mode")
            lib.freenect_set_video_callback(self._dev, self._on_video)
        self._ok(lib.freenect_start_depth(self._dev), "depth start")
        if self.o.colors:
            self._ok(lib.freenect_start_video(self._dev), "colour start")
        x, y = C.c_double(), C.c_double()
        lib.freenect_camera_to_world(self._dev, W // 2 + 1, H // 2, 1_000_000,
                                     C.byref(x), C.byref(y))
        if not (math.isfinite(x.value) and x.value > 0):
            raise Fault("the Kinect gave no calibration")
        self.focal = 1_000_000 / x.value
        self._heard = dict.fromkeys(("depth", "video") if self.o.colors else ("depth",),
                                    time.monotonic())

    def _ok(self, r: int, what: str) -> None:
        if r < 0:
            raise Fault(f"{what}: {self._said or r}")

    def _log(self, _ctx, _level, msg) -> None:
        self._said = (msg or b"").decode("utf-8", "replace").strip()

    # libfreenect reuses its buffer once a callback returns: copied here
    def _got_depth(self, _dev, data, _t) -> None:
        self._depth = np.ctypeslib.as_array(
            C.cast(data, C.POINTER(C.c_uint16)), (H, W)).copy()
        self._heard["depth"] = time.monotonic()

    def _got_video(self, _dev, data, _t) -> None:
        self._rgb = np.ctypeslib.as_array(
            C.cast(data, C.POINTER(C.c_uint8)), (H, W, 3)).copy()
        self._heard["video"] = time.monotonic()

    def read(self) -> tuple[np.ndarray, np.ndarray | None] | None:
        """The next depth picture and the newest colour one (None until
        there is one), or None with no new depth within `PUMP_US`."""
        tv, lib = _Timeval(0, PUMP_US), self._lib
        if lib is None:
            raise Fault("the Kinect is closed")
        if lib.freenect_process_events_timeout(self._ctx, C.byref(tv)) < 0:
            raise Fault("the Kinect went away")
        self._wake()
        d, self._depth = self._depth, None
        return None if d is None else (d, self._rgb)

    def _wake(self) -> None:
        """Start again any stream with no frame for `QUIET_S`; a silent colour
        stream's last picture is let go."""
        now = time.monotonic()
        for name, t in self._heard.items():
            if now - t > QUIET_S:
                if name == "video":
                    self._rgb = None          # no moving point wears a stopped picture
                getattr(self._lib, f"freenect_stop_{name}")(self._dev)
                self._ok(getattr(self._lib, f"freenect_start_{name}")(self._dev),
                         f"{name} start")
                self._heard[name] = now

    def close(self) -> None:
        lib = self._lib
        if lib is None:
            return
        dev, ctx = self._dev, self._ctx
        self._dev, self._ctx = C.c_void_p(), C.c_void_p()
        if dev:
            if self.o.colors:
                lib.freenect_stop_video(dev)
            lib.freenect_stop_depth(dev)
            lib.freenect_close_device(dev)
        if ctx:
            lib.freenect_shutdown(ctx)


# ---------------------------------------------------------------- the device

class Picture(SharedSource):
    """One of the sensor's pictures as a media source: the device's thread
    fills it while a channel holds it."""

    def __init__(self, sid: str, clock=time.monotonic):
        super().__init__(sid, kind="kinect", clock=clock)
        self._n = 0

    def put(self, px: np.ndarray) -> None:
        self._n += 1
        self._publish(MediaFrame(px, self.clock(), self._n))


class KinectDevice(devices.Base):
    """A Kinect (see the module docstring). `sensor` makes the thing with
    `open`, `read`, `close` and `focal`; a test passes its own."""

    kind = "kinect"

    def __init__(self, role: str, entry: dict | None = None,
                 ctx: devices.Context | None = None, *, io=None, sensor=Sensor):
        super().__init__(role, entry, ctx, io=io)
        self._make = sensor
        self.cloud: devices.PointCloud | None = None
        self._fresh: tuple | None = None       # the thread's newest frame, not yet polled
        self._pictures: dict[str, Picture] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._fault = ""
        self._live = False
        self._fps = 0.0
        self._shown: np.ndarray | None = None     # the colour picture published last

    def open(self) -> None:
        """The entry checked and the thread started; nothing here waits."""
        o = Options.of(self.entry)
        names = ("depth", "color") if o.colors else ("depth",)
        self._pictures = {f"kinect:{self.role}/{n}": Picture(f"kinect:{self.role}/{n}")
                          for n in names}
        self._fault, self._live, self.cloud, self._fresh, self._fps = "", False, None, None, 0.0
        prev, self._stop = self._thread, threading.Event()
        self._thread = threading.Thread(target=self._run, args=(o, self._stop, prev),
                                        name=f"kinect-{self.role}", daemon=True)
        self._thread.start()

    @property
    def status(self) -> str:
        if self.error:
            return f"error: {self.error}"
        if self._fault:
            return f"error: {self._fault}"
        return "connected" if self._live else "lost"

    @property
    def last(self) -> str:
        c = self.cloud
        return f"{c.n} points  ·  {self._fps:.0f} fps" if c is not None else ""

    @property
    def sources(self) -> tuple[devices.Port, ...]:
        return (devices.Port(self.role, "point cloud", kind="cloud",
                             scheme=devices.CLOUD_SCHEME),)

    def media_sources(self) -> dict[str, Picture]:
        return self._pictures

    def poll(self, dt: float, now: float) -> None:
        fresh = self._fresh
        if fresh is None:
            self.cloud = None        # a lost sensor leaves no frozen person behind
        elif self.cloud is None or self.cloud.frame != fresh[0]:
            n, pts, cols = fresh
            self.cloud = devices.PointCloud(pts, now, n, cols)

    def close(self) -> None:
        """The thread stopped and waited for within `JOIN_S`: a sensor left
        streaming may need its power pulled."""
        self._stop.set()
        t = self._thread
        if t is not None:
            t.join(JOIN_S)
            if not t.is_alive():
                self._thread = None
        self._live, self.cloud, self._fresh, self._pictures = False, None, None, {}
        super().close()

    # -- the thread ----------------------------------------------------------

    def _run(self, o: Options, stop: threading.Event, prev: threading.Thread | None) -> None:
        if prev is not None:
            prev.join()              # the last connection lets go before this one opens
        n = 0                        # counts on across reconnects
        while not stop.is_set():
            s = self._make(o)
            try:
                s.open()
                for depth, rgb in self._frames(s, stop):
                    self._made(n, s, o, depth, rgb)
                    n += 1
            except Exception as e:  # noqa: BLE001 — said on the SYSTEM page, tried again
                if not stop.is_set():
                    self._fault = str(e) if isinstance(e, Fault) else f"{type(e).__name__}: {e}"
                    self._live, self._fresh = False, None
            finally:
                with contextlib.suppress(Exception):
                    s.close()
            stop.wait(RETRY_S)

    def _frames(self, s, stop: threading.Event):
        heard = since = time.monotonic()
        count = 0
        while not stop.is_set():
            got = s.read()
            t = time.monotonic()
            if got is None:
                if t - heard > STALL_S:
                    raise Fault("the Kinect stopped sending")
                continue
            heard = t
            count += 1
            if t - since >= 1.0:
                self._fps, count, since = count / (t - since), 0, t
            if not stop.is_set():
                yield got

    def _made(self, n: int, s, o: Options, depth: np.ndarray, rgb: np.ndarray | None) -> None:
        pts, cols = deproject(depth, s.focal, o, rgb if o.colors else None)
        for a in (pts, cols):
            if a is not None:
                a.flags.writeable = False    # `PointCloud` takes a frozen array as it is
        self._fresh = (n, pts, cols)
        for sid, pic in self._pictures.items():
            if not pic.held:
                continue
            if sid.endswith("/depth"):
                pic.put(depth_picture(depth, o))
            elif rgb is not None and rgb is not self._shown:
                # each once: `Picture.put` stamps it now, so one put again never goes stale
                self._shown = rgb
                pic.put(_rgba(rgb, o))
        self._live, self._fault = True, ""
