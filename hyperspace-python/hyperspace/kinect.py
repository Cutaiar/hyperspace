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
(false: colour streams take USB bandwidth, and a dark room has none) and
`motor` (true: false leaves the motor part unopened).

**Threads.** One thread per device (``kinect-<role>``) opens the sensor,
pumps libfreenect's events, makes the frames and publishes each by one
reference swap; `poll` takes the newest. Every libfreenect call is made on
that thread and nowhere else: the pane's wishes are `request`s, a FIFO the
thread serves between two reads, and what it shows is `telemetry`, a frozen
snapshot the thread swaps in about four times a second. The thread opens the
camera and the motor (the tilt, the LED and the accelerometer are the motor
part); a motor that will not open is said in the telemetry and costs the
camera nothing. The audio is never claimed. A sensor that is missing, busy
or stops is said in `status` and tried again every `RETRY_S`.

**Nothing moves by itself.** The motor is read on open and a few times a
second, never driven: a tilt, an LED colour or an infrared brightness is
sent only for a `request`, and a request that was waiting when the sensor
went away or the device closed is dropped, not sent to the next connection.
The entry's `near`, `far`, `centre`, `step` and `mirror` can be changed for
this run (`place`); they are never written back (`devicelist` keeps a
role's entry as it is).

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
import queue
import sys
import threading
import time
from dataclasses import asdict, dataclass, field, replace

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

_RES_MEDIUM, _VIDEO_RGB, _VIDEO_IR_8BIT, _DEPTH_REGISTERED, _DEPTH_MM = 1, 0, 2, 4, 5
_MOTOR, _CAMERA, _LOG_ERROR = 0x01, 0x02, 1
IR_H = 488           # libfreenect's 8-bit infrared picture is 640 × 488
STATS_S = 0.25       # the telemetry is made this often at most
TILT_POLL_S = 0.3    # the motor's state is read this often at most (a blocking control transfer)
REQUESTS_PER_READ = 8    # requests served between two reads: the events keep being pumped
TILT_MAX = 31.0      # libfreenect clamps the target to ±31°
IR_MIN, IR_MAX = 1, 50
EXPOSURE_MIN, EXPOSURE_MAX = 100, 33_333     # µs: this panel's bounds (libfreenect's own sample is 33 333)
USB_VENDOR, USB_CAMERA = 0x045E, 0x02AE      # the Xbox NUI Camera
BCD_1414 = 267                               # its bcdDevice on a model 1414
# freenect_led_options: 5 is not one
LEDS = (("off", 0), ("green", 1), ("red", 2), ("yellow", 3), ("blink green", 4),
        ("blink red / yellow", 6))
# freenect_flag
FLAGS = {"auto_exposure": 1 << 14, "flicker": 1 << 7, "white_balance": 1 << 1}
VIDEO = ("off", "color", "ir")
TILT_STATUS = {0: "stopped", 1: "limit", 4: "moving"}
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
    motor: bool = True
    infrared: bool = False      # not the entry's: this run's video choice (`colors` and this exclude each other)

    @property
    def video(self) -> str:
        """The one video stream that runs: colour and infrared exclude each other."""
        return "color" if self.colors else "ir" if self.infrared else "off"

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
                flag("mirror", True), flag("colors", False), flag("motor", True))
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
    """A video picture as RGBA, mirrored as the cloud is: H×W×3 colour, or
    H×W infrared (8-bit grey)."""
    if rgb.ndim == 2:
        rgb = rgb[:, :, None]
    out = np.full((*rgb.shape[:2], 4), 255, np.uint8)
    out[..., :3] = rgb[:, ::-1] if o.mirror else rgb
    return out


def check(kind: str, value) -> tuple[object, str]:
    """A request's value made right, or why it is refused: ``(value, "")`` or
    ``(None, why)``. A tilt, an infrared brightness and an exposure are
    clamped (a drag lands on the edge); anything else not understood is
    refused by name."""
    def num(v) -> float | None:
        ok = isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)
        return float(v) if ok else None

    if kind == "tilt":
        v = num(value)
        return (None, f"tilt {value!r} is not a number") if v is None else (
            max(-TILT_MAX, min(TILT_MAX, v)), "")
    if kind == "led":
        if value in dict(LEDS).values():
            return value, ""
        return None, f"led {value!r} is not one of {', '.join(f'{n} = {c}' for n, c in LEDS)}"
    if kind in ("ir", "exposure"):
        v = num(value)
        lo, hi = (IR_MIN, IR_MAX) if kind == "ir" else (EXPOSURE_MIN, EXPOSURE_MAX)
        return (None, f"{kind} {value!r} is not a number") if v is None else (
            int(max(lo, min(hi, round(v)))), "")
    if kind == "video":
        return (value, "") if value in VIDEO else (None, f"video {value!r} is not {', '.join(VIDEO)}")
    if kind in FLAGS:
        return (value, "") if isinstance(value, bool) else (None, f"{kind} {value!r} is not on or off")
    if kind in ("restart", "reconnect"):
        return None, ""
    return None, f"{kind!r} is not a Kinect request"


def model_name(bcd: int | None) -> str:
    """The sensor's model from its USB camera's bcdDevice (267 is the 1414)."""
    if bcd is None:
        return "unknown"
    return "1414" if bcd == BCD_1414 else f"not a 1414 (bcdDevice {bcd})"


# ---------------------------------------------------------------- libfreenect

class _Mode(C.Structure):
    _fields_ = [("reserved", C.c_uint32), ("resolution", C.c_int), ("format", C.c_int32),
                ("bytes", C.c_int32), ("width", C.c_int16), ("height", C.c_int16),
                ("data_bits", C.c_int8), ("padding_bits", C.c_int8),
                ("framerate", C.c_int8), ("is_valid", C.c_int8)]


class _Timeval(C.Structure):
    _fields_ = [("tv_sec", C.c_long),
                ("tv_usec", C.c_int32 if sys.platform == "darwin" else C.c_long)]


class _UsbDescriptor(C.Structure):      # libusb_device_descriptor
    _fields_ = [("bLength", C.c_uint8), ("bDescriptorType", C.c_uint8), ("bcdUSB", C.c_uint16),
                ("bDeviceClass", C.c_uint8), ("bDeviceSubClass", C.c_uint8),
                ("bDeviceProtocol", C.c_uint8), ("bMaxPacketSize0", C.c_uint8),
                ("idVendor", C.c_uint16), ("idProduct", C.c_uint16), ("bcdDevice", C.c_uint16),
                ("iManufacturer", C.c_uint8), ("iProduct", C.c_uint8),
                ("iSerialNumber", C.c_uint8), ("bNumConfigurations", C.c_uint8)]


_FRAME_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_uint32)
_LOG_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_int, C.c_char_p)


def usb_cameras() -> list[int]:
    """The bcdDevice of every Xbox NUI Camera on the bus, in libusb's order
    (the one libfreenect counts its devices in); [] where libusb cannot be
    had. Reads descriptors only: nothing is opened."""
    names = [p for p in ("/opt/homebrew/lib/libusb-1.0.dylib", "/usr/local/lib/libusb-1.0.dylib")
             if os.path.exists(p)]
    if found := ctypes.util.find_library("usb-1.0"):
        names.append(found)
    for n in names:
        try:
            u = C.CDLL(n)
        except OSError:
            continue
        break
    else:
        return []
    p = C.c_void_p
    u.libusb_init.argtypes, u.libusb_init.restype = [C.POINTER(p)], C.c_int
    u.libusb_exit.argtypes, u.libusb_exit.restype = [p], None
    u.libusb_get_device_list.argtypes = [p, C.POINTER(C.POINTER(p))]
    u.libusb_get_device_list.restype = C.c_ssize_t
    u.libusb_free_device_list.argtypes, u.libusb_free_device_list.restype = [C.POINTER(p), C.c_int], None
    u.libusb_get_device_descriptor.argtypes = [p, C.POINTER(_UsbDescriptor)]
    u.libusb_get_device_descriptor.restype = C.c_int
    ctx, out = p(), []
    if u.libusb_init(C.byref(ctx)) < 0:
        return []
    try:
        lst = C.POINTER(p)()
        n = u.libusb_get_device_list(ctx, C.byref(lst))
        for i in range(max(n, 0)):
            d = _UsbDescriptor()
            if (u.libusb_get_device_descriptor(lst[i], C.byref(d)) == 0
                    and d.idVendor == USB_VENDOR and d.idProduct == USB_CAMERA):
                out.append(int(d.bcdDevice))
        if n >= 0:
            u.libusb_free_device_list(lst, 1)
    finally:
        u.libusb_exit(ctx)
    return out


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
    # what the controls use: one a build lacks disables its control, it does not stop the camera
    for name, res, args in (
            ("enabled_subdevices", i, [p]), ("set_tilt_degs", i, [p, C.c_double]),
            ("update_tilt_state", i, [p]), ("get_tilt_state", p, [p]),
            ("get_tilt_degs", C.c_double, [p]), ("get_tilt_status", i, [p]),
            ("get_mks_accel", None, [p, dbl, dbl, dbl]), ("set_led", i, [p, i]),
            ("set_flag", i, [p, i, i]), ("get_exposure", i, [p, C.POINTER(C.c_int)]),
            ("set_exposure", i, [p, i]), ("get_ir_brightness", i, [p]),
            ("set_ir_brightness", i, [p, C.c_uint16])):
        fn = getattr(lib, f"freenect_{name}", None)
        if fn is not None:
            fn.restype, fn.argtypes = res, args
    return lib


_MOTOR_CALLS = ("update_tilt_state", "get_tilt_state", "get_tilt_degs", "get_tilt_status",
                "get_mks_accel", "set_tilt_degs", "set_led")


class Sensor:
    """One Kinect through libfreenect, used only on its device's thread: the
    streams, the motor, the LED and the camera's settings. `apply` serves a
    request; `poll` reads the motor; `info` is what the telemetry is made of."""

    def __init__(self, o: Options):
        self.o = o
        self.focal = 0.0
        self.model = ""
        self.motor_why = ""            # "": the motor is open and answering
        self.frames = {"depth": 0, "video": 0}
        self.restarts = 0
        self.led = ""                  # the last colour sent (it cannot be read)
        self.target: float | None = None
        self.ir: int | None = None
        self.exposure: int | None = None
        self.flags: dict[str, bool] = {}      # what was last sent: libfreenect reads none back
        self.tilt: tuple[float, str, tuple[float, float, float]] | None = None
        self._lib: C.CDLL | None = None
        self._ctx = C.c_void_p()
        self._dev = C.c_void_p()
        self._depth: np.ndarray | None = None
        self._rgb: np.ndarray | None = None
        self._said = ""
        self._heard: dict[str, float] = {}     # stream → its last frame's time
        self._next_tilt = 0.0
        self._tilt_fails = 0

    def open(self) -> None:
        self._lib = lib = _load()
        cams = usb_cameras()
        self.model = model_name(cams[self.o.index] if self.o.index < len(cams) else None)
        if lib.freenect_init(C.byref(self._ctx), None) < 0:
            raise Fault("libfreenect would not start")
        # held by self: libfreenect keeps the pointers
        self._on_log = _LOG_CB(self._log)
        self._on_depth = _FRAME_CB(self._got_depth)
        self._on_video = _FRAME_CB(self._got_video)
        lib.freenect_set_log_level(self._ctx, _LOG_ERROR)
        lib.freenect_set_log_callback(self._ctx, self._on_log)
        self._open_device()
        self._configure()
        self._start()
        x, y = C.c_double(), C.c_double()
        lib.freenect_camera_to_world(self._dev, W // 2 + 1, H // 2, 1_000_000,
                                     C.byref(x), C.byref(y))
        if not (math.isfinite(x.value) and x.value > 0):
            raise Fault("the Kinect gave no calibration")
        self.focal = 1_000_000 / x.value
        self._read_settings()
        self.poll(time.monotonic())

    def _open_device(self) -> None:
        """The camera, with the motor beside it where it will open: a motor
        that will not is said and the camera opens without it. The audio is
        never claimed."""
        lib = self._lib
        tries = (_CAMERA | _MOTOR, _CAMERA) if self.o.motor else (_CAMERA,)
        if not self.o.motor:
            self.motor_why = "the entry has motor = false"
        for sub in tries:
            lib.freenect_select_subdevices(self._ctx, sub)
            if lib.freenect_num_devices(self._ctx) <= self.o.index:
                raise Fault("no Kinect found (its 12 V adapter and USB)")
            self._said = ""
            if lib.freenect_open_device(self._ctx, C.byref(self._dev), self.o.index) >= 0:
                break
            self._dev = C.c_void_p()
            if sub == _CAMERA:
                if "ERROR_ACCESS" in self._said or "ERROR_BUSY" in self._said:
                    raise Fault("another app holds the Kinect (Logitech G Hub does)")
                raise Fault(self._said or "the Kinect would not open")
            self.motor_why = (f"the motor would not open ({self._said or 'no reason given'}); "
                              "the camera runs without it")
        if sub & _MOTOR:
            opened = self._fn("enabled_subdevices")
            if opened is not None and not opened(self._ctx) & _MOTOR:
                self.motor_why = "libfreenect leaves this model's motor closed"
            elif any(self._fn(n) is None for n in _MOTOR_CALLS):
                self.motor_why = "this libfreenect has no motor calls"

    def _fn(self, name: str):
        return getattr(self._lib, f"freenect_{name}", None)

    def _configure(self) -> None:
        """The depth and video modes of `o`, set while the streams are stopped."""
        lib, v = self._lib, self.o.video
        fmt = _DEPTH_REGISTERED if self.o.colors else _DEPTH_MM
        mode = lib.freenect_find_depth_mode(_RES_MEDIUM, fmt)
        self._ok(lib.freenect_set_depth_mode(self._dev, mode), "depth mode")
        lib.freenect_set_depth_callback(self._dev, self._on_depth)
        if v != "off":
            vmode = lib.freenect_find_video_mode(
                _RES_MEDIUM, _VIDEO_RGB if v == "color" else _VIDEO_IR_8BIT)
            self._ok(lib.freenect_set_video_mode(self._dev, vmode), f"{v} mode")
            lib.freenect_set_video_callback(self._dev, self._on_video)

    def _start(self) -> None:
        lib = self._lib
        self._ok(lib.freenect_start_depth(self._dev), "depth start")
        if self.o.video != "off":
            self._ok(lib.freenect_start_video(self._dev), "video start")
        self._heard = dict.fromkeys(("depth", "video") if self.o.video != "off" else ("depth",),
                                    time.monotonic())

    def _stop(self) -> None:
        lib = self._lib
        if self.o.video != "off":
            lib.freenect_stop_video(self._dev)
        lib.freenect_stop_depth(self._dev)

    def _read_settings(self) -> None:
        """What the camera can say of itself, once: nothing is sent."""
        get = self._fn("get_ir_brightness")
        if get is not None:
            v = get(self._dev)
            self.ir = v if v > 0 else None
        self._read_exposure()

    def _read_exposure(self) -> None:
        get = self._fn("get_exposure")
        if get is not None:
            us = C.c_int()
            self.exposure = us.value if get(self._dev, C.byref(us)) >= 0 else None

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
        self.frames["depth"] += 1

    def _got_video(self, _dev, data, _t) -> None:
        shape = (IR_H, W) if self.o.video == "ir" else (H, W, 3)
        self._rgb = np.ctypeslib.as_array(C.cast(data, C.POINTER(C.c_uint8)), shape).copy()
        self._heard["video"] = time.monotonic()
        self.frames["video"] += 1

    def read(self) -> tuple[np.ndarray, np.ndarray | None] | None:
        """The next depth picture and the newest video one (None until
        there is one; H×W×3 colour or H×W infrared), or None with no new
        depth within `PUMP_US`."""
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
                self.restarts += 1

    # -- motor ---------------------------------------------------------------

    def poll(self, now: float) -> None:
        """The motor's angle, status and the accelerometer, at most every
        `TILT_POLL_S`: a blocking control transfer, and a read only."""
        if self.motor_why or now < self._next_tilt:
            return
        self._next_tilt = now + TILT_POLL_S
        lib = self._lib
        if lib.freenect_update_tilt_state(self._dev) < 0:
            self._tilt_fails += 1
            if self._tilt_fails >= 3:
                self.motor_why, self.tilt = "the motor stopped answering", None
            return
        self._tilt_fails = 0
        st = lib.freenect_get_tilt_state(self._dev)
        if not st:
            return
        x, y, z = C.c_double(), C.c_double(), C.c_double()
        lib.freenect_get_mks_accel(st, C.byref(x), C.byref(y), C.byref(z))
        self.tilt = (float(lib.freenect_get_tilt_degs(st)),
                     TILT_STATUS.get(int(lib.freenect_get_tilt_status(st)), "?"),
                     (x.value, y.value, z.value))

    def can(self) -> dict[str, str]:
        """Each control's reason it cannot be used now, "" where it can."""
        def lacks(name: str) -> str:
            return "" if self._fn(name) is not None else f"this libfreenect has no freenect_{name}"

        motor = self.motor_why
        colour = "" if self.o.video == "color" else "needs the colour stream"
        auto = self.flags.get("auto_exposure", True)
        return {
            "tilt": motor or lacks("set_tilt_degs"), "led": motor or lacks("set_led"),
            "ir": lacks("set_ir_brightness"), "video": "", "restart": "", "reconnect": "",
            "auto_exposure": colour or lacks("set_flag"),
            "white_balance": colour or lacks("set_flag"),
            "flicker": colour or lacks("set_flag"),
            "exposure": colour or lacks("set_exposure") or ("auto exposure is on" if auto else ""),
        }

    def info(self) -> dict:
        """What the telemetry reads of the sensor."""
        t = self.tilt
        return {"model": self.model, "motor_why": self.motor_why,
                "tilt": None if t is None else t[0], "tilt_status": "" if t is None else t[1],
                "accel": None if t is None else t[2], "led": self.led, "target": self.target,
                "ir": self.ir, "exposure": self.exposure, "flags": dict(self.flags),
                "video": self.o.video, "log": self._said, "frames": dict(self.frames),
                "restarts": self.restarts, "can": self.can()}

    # -- requests ------------------------------------------------------------

    def apply(self, kind: str, value) -> str:
        """One request, on the device's thread: "" when it was sent, else
        why not. A fault (the streams left stopped, a reconnect asked) is
        raised, as a stream's own would be."""
        why = self.can().get(kind)
        if why:
            return f"{kind}: {why}"
        fn = getattr(self, f"_do_{kind if kind not in FLAGS else 'flag'}", None)
        if fn is None:
            return f"{kind}: not a Kinect request"
        return fn(kind, value) or ""

    def _sent(self, r: int, what: str) -> str:
        return "" if r >= 0 else f"{what}: libfreenect said {r}{f' ({self._said})' if self._said else ''}"

    def _do_tilt(self, _kind, deg: float) -> str:
        deg = max(-TILT_MAX, min(TILT_MAX, float(deg)))
        said = self._sent(self._lib.freenect_set_tilt_degs(self._dev, deg), "tilt")
        if not said:
            self.target = deg
            self._next_tilt = 0.0           # the next poll shows it going
        return said

    def _do_led(self, _kind, code: int) -> str:
        said = self._sent(self._lib.freenect_set_led(self._dev, int(code)), "led")
        if not said:
            self.led = next(n for n, c in LEDS if c == code)
        return said

    def _do_ir(self, _kind, level: int) -> str:
        level = int(max(IR_MIN, min(IR_MAX, level)))
        said = self._sent(self._lib.freenect_set_ir_brightness(self._dev, level), "ir")
        if not said:
            got = self._fn("get_ir_brightness")
            v = got(self._dev) if got is not None else -1
            self.ir = v if v > 0 else level
        return said

    def _do_flag(self, kind: str, on: bool) -> str:
        said = self._sent(self._lib.freenect_set_flag(self._dev, FLAGS[kind], 1 if on else 0), kind)
        if not said:
            self.flags[kind] = bool(on)
            self._read_exposure()
        return said

    def _do_exposure(self, _kind, us: int) -> str:
        us = int(max(EXPOSURE_MIN, min(EXPOSURE_MAX, us)))
        said = self._sent(self._lib.freenect_set_exposure(self._dev, us), "exposure")
        if not said:
            self._read_exposure()
            if self.exposure is None:
                self.exposure = us
        return said

    def _do_video(self, _kind, mode: str) -> str:
        """Colour, infrared or none: the streams stopped, their modes set and
        started again (depth is the registered one with colour)."""
        if mode == self.o.video:
            return ""
        self._stop()
        self.o = replace(self.o, colors=mode == "color", infrared=mode == "ir")
        self._rgb = self._depth = None
        self.flags = {}                          # (a stream that began again has its defaults)
        self._configure()
        self._start()
        self.restarts += 1
        return ""

    def _do_restart(self, _kind, _value) -> str:
        """Every stream stopped and started again, as `_wake` does one."""
        lib = self._lib
        for name in self._heard:
            getattr(lib, f"freenect_stop_{name}")(self._dev)
        for name in self._heard:
            self._ok(getattr(lib, f"freenect_start_{name}")(self._dev), f"{name} start")
        now = time.monotonic()
        self._heard = dict.fromkeys(self._heard, now)
        self._rgb = None
        self.restarts += 1
        return ""

    def _do_reconnect(self, _kind, _value) -> str:
        raise Fault("reconnecting, as asked")

    def close(self) -> None:
        lib = self._lib
        if lib is None:
            return
        dev, ctx = self._dev, self._ctx
        self._dev, self._ctx = C.c_void_p(), C.c_void_p()
        if dev:
            if self.o.video != "off":
                lib.freenect_stop_video(dev)
            lib.freenect_stop_depth(dev)
            lib.freenect_close_device(dev)
        if ctx:
            lib.freenect_shutdown(ctx)


# ---------------------------------------------------------------- the device

@dataclass(frozen=True)
class Telemetry:
    """What the pane reads of a Kinect: one frozen snapshot, made on the
    device's thread and swapped in whole, so a reader needs no lock. The
    counts are since the device opened and go on across reconnects."""

    seq: int = 0
    live: bool = False
    model: str = ""
    depth_fps: float = 0.0
    video_fps: float = 0.0
    frames: int = 0                  # depth frames made
    video_frames: int = 0
    restarts: int = 0                # streams started again, by `_wake`, by hand, or by a change of video
    reconnects: int = 0
    share: float | None = None       # of the depth pixels, the share that read something
    nearest: float | None = None     # metres, of the pixels read
    median: float | None = None
    points: int = 0
    tilt: float | None = None        # degrees, as the motor says
    tilt_status: str = ""            # stopped / moving / limit
    accel: tuple[float, float, float] | None = None      # m/s²
    motor_why: str = ""              # "": the motor answers; else why it does not
    led: str = ""                    # the last colour sent, "" none yet
    target: float | None = None      # the last tilt sent
    ir: int | None = None
    exposure: int | None = None      # µs
    flags: dict = field(default_factory=dict)    # what was last sent (libfreenect reads none back)
    video: str = "off"
    log: str = ""                    # libfreenect's last line
    said: str = ""                   # the last request's outcome
    can: dict = field(default_factory=dict)      # control → why not ("" it can)


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
    `open`, `read`, `close` and `focal` (and, to be steered, `apply`, `poll`
    and `info`); a test passes its own."""

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
        self._requests: queue.SimpleQueue = queue.SimpleQueue()
        self._fault = ""
        self._live = False
        self._fps = 0.0
        self._shown: np.ndarray | None = None     # the video picture published last
        self._o = Options()                       # this run's: the entry's, and what `place` changed
        self._tele = Telemetry()
        self._reset_counts()

    def _reset_counts(self) -> None:
        self._made_n = 0
        self._carry = {"video": 0, "restarts": 0, "reconnects": 0}
        self._pub = 0.0
        self._win: tuple[float, int, int] | None = None
        self._rates = (0.0, 0.0)
        self._measured = 0.0
        self._points = 0
        self._look: tuple[float | None, float | None, float | None] = (None, None, None)
        self._said = ""

    def open(self) -> None:
        """The entry checked and the thread started; nothing here waits."""
        o = self._o = Options.of(self.entry)
        names = ("depth", "color") if o.colors else ("depth",)
        self._pictures = {f"kinect:{self.role}/{n}": Picture(f"kinect:{self.role}/{n}")
                          for n in names}
        self._fault, self._live, self.cloud, self._fresh, self._fps = "", False, None, None, 0.0
        self._reset_counts()
        self._tele = Telemetry()
        prev, self._stop = self._thread, threading.Event()
        q = self._requests = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run, args=(o, self._stop, prev, q),
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

    @property
    def telemetry(self) -> Telemetry:
        """The newest snapshot (any thread)."""
        return self._tele

    @property
    def options(self) -> Options:
        """This run's settings: the entry's, with what `place` changed."""
        return self._o

    def place(self, **changes) -> str:
        """Change the entry's `near`, `far`, `centre`, `step` or `mirror` for
        this run: "" when it took, else why not. The entry is not written —
        it is the device list's, which a role's is never rewritten in — so
        opening the device again starts from the entry."""
        bad = set(changes) - {"near", "far", "centre", "step", "mirror"}
        if bad:
            return f"{', '.join(sorted(bad))}: not a placement setting"
        try:
            now = {k: v for k, v in asdict(self._o).items()
                   if k in ("near", "far", "centre", "step", "mirror")}
            o = Options.of({**now, **changes})
        except ValueError as e:
            return str(e)
        self._o = replace(self._o, near=o.near, far=o.far, centre=o.centre, step=o.step,
                          mirror=o.mirror)
        return ""

    def request(self, kind: str, value=None) -> str:
        """Ask the thread for something (`check` says what): "" when it is
        queued, else why not. The thread serves requests in the order asked,
        between two reads; the outcome is `telemetry.said`. Asked of no
        connected sensor, it is refused, and what was waiting when a sensor
        went away is dropped, never sent to the next one."""
        v, why = check(kind, value)
        if why:
            return why
        if self._thread is None or self._stop.is_set() or not self._live:
            return "no Kinect is connected"
        self._requests.put((kind, v))
        return ""

    def poll(self, dt: float, now: float) -> None:
        fresh = self._fresh
        if fresh is None:
            self.cloud = None        # a lost sensor leaves no frozen person behind
        elif self.cloud is None or self.cloud.frame != fresh[0]:
            n, pts, cols = fresh
            self.cloud = devices.PointCloud(pts, now, n, cols)

    def close(self) -> None:
        """The thread stopped and waited for within `JOIN_S`: a sensor left
        streaming may need its power pulled. Requests still waiting are
        dropped."""
        self._stop.set()
        t = self._thread
        if t is not None:
            t.join(JOIN_S)
            if not t.is_alive():
                self._thread = None
        self._drop(self._requests)
        self._live, self.cloud, self._fresh, self._pictures = False, None, None, {}
        self._tele = replace(self._tele, live=False, depth_fps=0.0, video_fps=0.0, can={})
        super().close()

    # -- the thread ----------------------------------------------------------

    def _run(self, o: Options, stop: threading.Event, prev: threading.Thread | None,
             q: queue.SimpleQueue) -> None:
        if prev is not None:
            prev.join()              # the last connection lets go before this one opens
        n = 0                        # counts on across reconnects
        first = True
        while not stop.is_set():
            self._drop(q)            # nothing asked of a sensor now gone is sent to this one
            s = self._make(self._o)
            if not first:
                self._carry["reconnects"] += 1
            first = False
            try:
                s.open()
                for depth, rgb in self._frames(s, stop, q):
                    self._made(n, s, self._o, depth, rgb)
                    n += 1
                    self._made_n = n
            except Exception as e:  # noqa: BLE001 — said on the SYSTEM page, tried again
                if not stop.is_set():
                    self._fault = str(e) if isinstance(e, Fault) else f"{type(e).__name__}: {e}"
                    self._live, self._fresh = False, None
            finally:
                self._lost(s)
                with contextlib.suppress(Exception):
                    s.close()
            self._drop(q)
            stop.wait(RETRY_S)

    def _drop(self, q: queue.SimpleQueue) -> None:
        while True:
            try:
                q.get_nowait()
            except queue.Empty:
                return

    def _lost(self, s) -> None:
        """A sensor is done: its counts are carried on, and the pane sees
        nothing live of it."""
        info = s.info() if hasattr(s, "info") else {}
        self._carry["video"] += info.get("frames", {}).get("video", 0)
        self._carry["restarts"] += info.get("restarts", 0)
        self._win = None
        self._tele = replace(self._tele, live=False, depth_fps=0.0, video_fps=0.0, tilt=None,
                             tilt_status="", accel=None, can={}, seq=self._tele.seq + 1)

    def _frames(self, s, stop: threading.Event, q: queue.SimpleQueue):
        heard = since = time.monotonic()
        count = 0
        while not stop.is_set():
            self._serve(s, stop, q)
            got = s.read()
            t = time.monotonic()
            self._publish(s, t)
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

    def _serve(self, s, stop: threading.Event, q: queue.SimpleQueue) -> None:
        """The requests waiting, in order, a few at a time. One that fails is
        said and the rest go on; a fault is the sensor's, and ends this
        connection. A close drops what is left."""
        for _ in range(REQUESTS_PER_READ):
            if stop.is_set():
                return
            try:
                kind, value = q.get_nowait()
            except queue.Empty:
                return
            apply = getattr(s, "apply", None)
            try:
                said = f"{kind}: this sensor takes no requests" if apply is None else apply(kind, value)
            except Fault:
                raise
            except Exception as e:  # noqa: BLE001 — a request that failed is said, not fatal
                said = f"{kind}: {type(e).__name__}: {e}"
            self._said = said or f"sent {kind}{'' if value is None else f' {value}'}"
            if kind == "video" and not said:
                self._video_began(s)
            self._publish(s, time.monotonic(), force=True)

    def _video_began(self, s) -> None:
        """A video stream was chosen: this run's options follow the sensor's,
        and a picture to hold exists for it."""
        o = getattr(s, "o", None)
        if o is None:
            return
        self._o = replace(self._o, colors=o.colors, infrared=o.infrared)
        self._shown = None
        pics = self._pictures
        want = {"color": "color", "ir": "ir"}.get(o.video)
        sid = f"kinect:{self.role}/{want}"
        if want and sid not in pics:
            self._pictures = {**pics, sid: Picture(sid)}

    def _publish(self, s, t: float, force: bool = False) -> None:
        """The telemetry, at most every `STATS_S` (and at once after a request)."""
        if not force and t - self._pub < STATS_S:
            return
        self._pub = t
        poll = getattr(s, "poll", None)
        if poll is not None:
            poll(t)
        info = s.info() if hasattr(s, "info") else {}
        video = info.get("frames", {}).get("video", 0)
        win = self._win
        if win is None:
            self._win = (t, self._made_n, video)
        elif t - win[0] >= 1.0:
            dt = t - win[0]
            self._rates = ((self._made_n - win[1]) / dt, (video - win[2]) / dt)
            self._win = (t, self._made_n, video)
        near, med, share = self._look
        self._tele = Telemetry(
            seq=self._tele.seq + 1, live=self._live, model=info.get("model", ""),
            depth_fps=self._rates[0], video_fps=self._rates[1], frames=self._made_n,
            video_frames=self._carry["video"] + video,
            restarts=self._carry["restarts"] + info.get("restarts", 0),
            reconnects=self._carry["reconnects"], share=share, nearest=near, median=med,
            points=self._points, tilt=info.get("tilt"), tilt_status=info.get("tilt_status", ""),
            accel=info.get("accel"), motor_why=info.get("motor_why", ""), led=info.get("led", ""),
            target=info.get("target"), ir=info.get("ir"), exposure=info.get("exposure"),
            flags=info.get("flags", {}), video=info.get("video", self._o.video),
            log=info.get("log", ""), said=self._said, can=info.get("can", {}))

    def _measure(self, depth: np.ndarray) -> None:
        """What the depth picture reads, a few times a second: the share of
        pixels with a reading, and the nearest and median of those, metres.
        A view filled by something very close reads as a share that falls."""
        read = depth[depth > 0]
        self._look = ((float(read.min()) * 0.001, float(np.median(read)) * 0.001,
                       read.size / depth.size) if read.size else (None, None, 0.0))

    def _made(self, n: int, s, o: Options, depth: np.ndarray, rgb: np.ndarray | None) -> None:
        video = rgb is not None and rgb.ndim == 3
        pts, cols = deproject(depth, s.focal, o, rgb if o.colors and video else None)
        for a in (pts, cols):
            if a is not None:
                a.flags.writeable = False    # `PointCloud` takes a frozen array as it is
        self._fresh = (n, pts, cols)
        self._points = len(pts)
        t = time.monotonic()
        if t - self._measured >= STATS_S:
            self._measured = t
            self._measure(depth)
        for sid, pic in self._pictures.items():
            if not pic.held:
                continue
            if sid.endswith("/depth"):
                pic.put(depth_picture(depth, o))
            elif rgb is not None and rgb is not self._shown and (
                    (sid.endswith("/color") and rgb.ndim == 3)
                    or (sid.endswith("/ir") and rgb.ndim == 2)):
                # each once: `Picture.put` stamps it now, so one put again never goes stale
                self._shown = rgb
                pic.put(_rgba(rgb, o))
        self._live, self._fault = True, ""
