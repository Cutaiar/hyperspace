"""A Kinect's side pane: what GRAPH shows when the
Kinect's device node (``device:<role>``, an entry of kind ``kinect``) is
selected. Manual state control and telemetry, and nothing else: nothing here
drives the sensor by itself, and nothing moves it when the pane opens.

**Controls** (each a `KinectDevice.request`, served on the device's own
thread; the pane never touches libfreenect and never waits):

- *tilt*: a target (±31°, libfreenect's clamp), sent when the slider is let
  go, by **go**, or as 0 by **level**: never while it is being dragged. There
  is a tilt motor and no yaw motor.
- *LED*: off, green, red, yellow, blink green, blink red / yellow.
- *infrared*: the IR camera's brightness, 1–50, sent on release.
- *video*: off, colour or infrared (one stream: they exclude each other);
  auto exposure, auto white balance and auto flicker; and, with auto
  exposure off, the exposure time.
- *streams*: **restart** (every stream stopped and started) and **reconnect**
  (the sensor closed and opened again).
- *placement*: the entry's `near`, `far`, `centre`, `step` and `mirror`, for
  this run (`KinectDevice.place`). They are the sensor's place, the entry's
  and no param's or patch's, and they are **not saved**: `devicelist` never
  rewrites a role's entry, and the entry is a file two Macs share. The pane
  says so; to keep a placement, edit the entry.

A control the device cannot use now is drawn disabled, with the word why
beside it (`Telemetry.can`). **Telemetry**: the model, the status, the
rates, the counts, how much of the picture read, the nearest and median
depth, the tilt, its motor, the accelerometer and libfreenect's last line.
The pictures themselves stay on the MEDIA page (`kinect:<role>/depth`).

View state only (`_state`): a slider's value while it is being edited. Ids
are `kinect.*`, after the ``##``."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from imgui_bundle import imgui

from . import ui
from .dkit.tokens import SPACE
from .kinect import (
    EXPOSURE_MAX,
    EXPOSURE_MIN,
    FOCAL,
    IR_MAX,
    IR_MIN,
    LEDS,
    RADAR_COLS,
    RADAR_RANGE,
    TILT_MAX,
)

KEY = "kinect.pane"
TILT_STEP = 0.5                     # the tilt slider's detent, degrees
NOT_SAVED = ("for this run: they are the entry's, and an entry in the device list is "
             "never rewritten. Edit the entry to keep them.")
NO_SENSOR = "no Kinect is connected"
DRIVEN = "driven by a sink row (ROUTING, sinks): it is the route's now"
HOLD_TIP = "sent when you let go"

RADAR_ID = "kinect.radar"
RADAR_ASPECT = 0.7                  # the radar's height over its width
RADAR_MAX_H = 260.0                 # ... capped
RADAR_PAD = 4.0                     # px inside the frame
SENSOR_W = 640                      # the depth picture's width, pixels
SPEC_RANGE = (0.8, 4.0)             # metres: Microsoft's working range for the Xbox 360 Kinect
RADAR_TIP = ("The Kinect from above, the sensor at the bottom. The grey fan is what its depth camera "
             "sees (its own calibration; the lines across it are its working range). The white dots are what it "
             "reads now, the nearest thing in each direction, as libfreenect gives it in millimetres. "
             "The red wireframe is your near / far / centre: what the cloud keeps. Mirror flips it as "
             "it flips the cloud.")

VIDEO_LABELS = (("off", "off"), ("color", "colour"), ("ir", "infrared"))


def is_kinect_node(n) -> bool:
    """Is `n` a Kinect's device node?"""
    ref = getattr(n, "ref", None)
    # a disabled entry is an `OffDevice` that keeps the kind and has no panel to draw: it stays on the generic pane
    return (getattr(n, "kind", "") == "device" and getattr(ref, "kind", "") == "kinect"
            and hasattr(ref, "telemetry") and callable(getattr(ref, "request", None)))


def _state(panel, role: str) -> dict:
    all_ = panel.__dict__.setdefault(KEY, {})
    return all_.setdefault(role, {"tilt": None, "ir": None, "exposure": None, "held": set()})


def _gap(n: float = 2) -> None:
    imgui.dummy(imgui.ImVec2(0, SPACE[n]))


def _head(text: str) -> None:
    _gap(2)
    ui._micro(text)


def _why(text: str) -> None:
    """The word a disabled control gives, under it, quiet and wrapped."""
    imgui.push_style_color(imgui.Col_.text, ui.FAINT)
    imgui.text_wrapped(text)
    imgui.pop_style_color()


def _kv(label: str, value: str) -> None:
    """A telemetry row: the label in the label column, the value fitted to what is left."""
    imgui.text_colored(ui.DIM, label)
    imgui.same_line(ui.LABEL_W)
    room = imgui.get_content_region_avail().x
    imgui.text_colored(ui.TEXT, ui.fit_text(value, room))


def _num(v, fmt: str = "{:.2f}", unit: str = "") -> str:
    return "—" if v is None else fmt.format(v) + unit


def _tip(text: str) -> None:
    if text and imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        ui.tooltip(text)


def body(panel, dev) -> None:
    """The selected Kinect's pane. `dev` is its `KinectDevice` (or anything with
    `telemetry`, `request`, `place`, `options` and `status`)."""
    st = _state(panel, str(getattr(dev, "role", "kinect")))
    watch = getattr(dev, "watch", None)
    if watch is not None:
        watch()                     # the thread measures for the radar and telemetry only while this is called
    t = dev.telemetry
    live = bool(t.live)

    driven = getattr(dev, "driven", frozenset())

    def why(key: str) -> str:
        base = t.can.get(key, "") if live else NO_SENSOR
        return base or (DRIVEN if key in ("ir", "exposure") and key in driven else "")

    _status(dev, t)
    _radar(dev, t)
    _tilt(dev, t, st, why("tilt"))
    _led(dev, t, why("led"))
    _infrared(dev, t, st, why("ir"))
    _video(dev, t, st, why)
    _streams(dev, why("restart"), why("reconnect"))
    _placement(dev)
    _telemetry(t)


@dataclass(frozen=True)
class RadarView:
    """The radar's lines in screen points. The cloud keeps a reading by its depth along the
    sensor's axis, not its distance from the sensor (`deproject`), and the radar plots a
    reading at that depth, so every limit is a straight line across the fan at one depth:
    the fan's two edge rays and its far end (`rim`), your `near` and `far` and the two edge
    rays between them, the `centre` tick (None beyond the range), and the sensor's working
    range as `spec` lines."""

    apex: tuple[float, float]
    fan: tuple[tuple[float, float], tuple[float, float]]
    rim: tuple[tuple[float, float], tuple[float, float]]
    near_line: tuple[tuple[float, float], tuple[float, float]]
    far_line: tuple[tuple[float, float], tuple[float, float]]
    edges: tuple[tuple[tuple[float, float], tuple[float, float]], ...]
    centre: tuple[tuple[float, float], tuple[float, float]] | None
    spec: tuple[tuple[tuple[float, float], tuple[float, float]], ...] = ()


def half_angle(focal: float, width: float = SENSOR_W) -> float:
    """The view's half-angle, radians: atan((W/2)/focal)."""
    return math.atan((width / 2) / (focal if focal > 0 else FOCAL))


def radar_scale(focal: float, w: float, h: float, rng: float = RADAR_RANGE) -> float:
    """Pixels per metre that fit the whole fan to `w` x `h` with `RADAR_PAD` around."""
    side = max(rng * math.tan(half_angle(focal)), 1e-6)
    return max(min((h - 2 * RADAR_PAD) / rng, (w / 2 - RADAR_PAD) / side), 1.0)


def radar_geometry(focal: float, near: float, far: float, centre: float, scale: float,
                   ox: float, oy: float, rng: float = RADAR_RANGE,
                   spec: tuple[float, ...] = SPEC_RANGE) -> RadarView:
    """The radar's lines, pure: the sensor at (ox, oy), straight ahead up the screen,
    `scale` pixels per metre of depth, a line at depth z reaching z · tan(half-angle) to
    each side. `near` and `far` are kept inside 0..rng and in order."""
    reach = math.tan(half_angle(focal))
    far = min(max(far, 0.0), rng)
    near = min(max(near, 0.0), far)

    def line(z: float) -> tuple[tuple[float, float], tuple[float, float]]:
        y, dx = oy - z * scale, z * reach * scale
        return (ox - dx, y), (ox + dx, y)

    n, f = line(near), line(far)
    tick = None
    if 0.0 <= centre <= rng:
        y = oy - centre * scale
        tick = ((ox - 4.0, y), (ox + 4.0, y))
    top = line(rng)
    return RadarView((ox, oy), top, top, n, f, ((n[0], f[0]), (n[1], f[1])), tick,
                     tuple(line(z) for z in spec if z <= rng))


@lru_cache(maxsize=8)
def _lateral(focal: float, mirror: bool) -> tuple[float, ...]:
    """Per radar column, (x − W/2) / focal, x the column's pixel: a reading z metres
    out lies z times this to the side. Flipped when mirrored."""
    step = SENSOR_W // RADAR_COLS
    sign = -1.0 if mirror else 1.0
    return tuple(sign * (i * step + step // 2 - SENSOR_W / 2) / focal for i in range(RADAR_COLS))


def radar_points(profile, focal: float, mirror: bool, scale: float, ox: float, oy: float,
                 rng: float = RADAR_RANGE) -> list[list[tuple[float, float]]]:
    """The readings as screen points, pure: `profile` is `kinect.radar_profile`'s mm a
    column. Runs of neighbouring columns that read something within `rng`; a gap
    (nothing read, or too far) ends a run, so a line is never drawn across one."""
    k = _lateral(focal if focal > 0 else FOCAL, bool(mirror))
    runs: list[list[tuple[float, float]]] = []
    run: list[tuple[float, float]] = []
    for i, mm in enumerate(profile[:RADAR_COLS]):
        z = mm * 0.001
        if 0.0 < z <= rng:
            run.append((ox + k[i] * z * scale, oy - z * scale))
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    return runs


def _pts(points) -> list[imgui.ImVec2Like]:
    return [imgui.ImVec2(x, y) for x, y in points]


def _radar(dev, t) -> None:
    """The top-down radar: read-only, asks for nothing. Not live: the sensor's fan and your
frustum, no readings."""
    w = max(imgui.get_content_region_avail().x, 40.0)
    h = min(w * RADAR_ASPECT, RADAR_MAX_H)
    imgui.invisible_button(f"##{RADAR_ID}", imgui.ImVec2(w, h))
    hovered = imgui.is_item_hovered()
    r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    dl = imgui.get_window_draw_list()
    dl.add_rect(r0, r1, ui.u32(ui.LINE))
    live = bool(t.live)
    o = dev.options
    focal = t.focal if t.focal > 0 else FOCAL
    scale = radar_scale(focal, w, h)
    ox, oy = (r0.x + r1.x) / 2, r1.y - RADAR_PAD
    g = radar_geometry(focal, o.near, o.far, o.centre, scale, ox, oy)
    line = ui.u32(ui.LINE)          # the theoretical fan: the one grey line, live or not
    apex = imgui.ImVec2(ox, oy)
    if live and t.radar is not None:
        dots = ui.u32(ui.TEXT)
        for run in radar_points(t.radar, focal, o.mirror, scale, ox, oy):
            if len(run) > 1:
                dl.add_polyline(_pts(run), dots, 1.0, 0)
            for x, y in run:
                dl.add_circle_filled(imgui.ImVec2(x, y), 1.6, dots, 6)
    for a, b in (*g.spec, g.rim):
        dl.add_line(imgui.ImVec2(*a), imgui.ImVec2(*b), line, 1.0)
    dl.add_line(apex, imgui.ImVec2(*g.fan[0]), line, 1.0)
    dl.add_line(apex, imgui.ImVec2(*g.fan[1]), line, 1.0)
    strong = ui.u32(ui.RED)          # your frustum: the one accent, over the grey sensor's
    for a, b in (g.near_line, g.far_line):
        dl.add_line(imgui.ImVec2(*a), imgui.ImVec2(*b), strong, 1.5)
    for a, b in g.edges:
        dl.add_line(imgui.ImVec2(*a), imgui.ImVec2(*b), strong, 1.5)
    if g.centre:
        dl.add_line(imgui.ImVec2(*g.centre[0]), imgui.ImVec2(*g.centre[1]), strong, 2.0)
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    room = w / 2 - RADAR_PAD - 2
    for r in (min(o.near, RADAR_RANGE), min(o.far, RADAR_RANGE)):
        text = ui.fit_text(f"{r:g} m", room)
        y = max(oy - r * scale - imgui.get_text_line_height(), r0.y + 1)
        dl.add_text(imgui.ImVec2(ox + 3, y), ui.u32(ui.DIM), text)
    imgui.pop_font()
    if hovered:
        ui.tooltip(RADAR_TIP)


def _ask(dev, kind: str, value=None) -> None:
    dev.request(kind, value)


def _status(dev, t) -> None:
    imgui.text_wrapped(f"{dev.status}")
    if t.said:
        imgui.push_style_color(imgui.Col_.text, ui.DIM)
        imgui.text_wrapped(t.said)
        imgui.pop_style_color()


def _slider_row(label: str, key: str, st: dict, shown, lo, hi, fmt: str, *, whole: bool,
                ident: str, why: str):
    """A slider that sends nothing while it is dragged: (its value, let go?).
    It follows what the sensor reports while it is not being edited."""
    held = st["held"]
    if key not in held and shown is not None:
        st[key] = shown
    if st[key] is None:
        st[key] = lo if lo > 0 else 0 if whole else 0.0
    imgui.begin_disabled(bool(why))
    imgui.set_next_item_width(-1)
    if whole:
        changed, v = imgui.slider_int(f"##{ident}", int(st[key]), int(lo), int(hi), fmt)
    else:
        changed, v = imgui.slider_float(f"##{ident}", float(st[key]), lo, hi, fmt)
    active = imgui.is_item_active()
    let_go = imgui.is_item_deactivated_after_edit()
    imgui.end_disabled()
    _tip(why or label)
    if changed:
        st[key] = v
    if active:
        held.add(key)
    else:
        held.discard(key)
    return st[key], let_go


def _tilt(dev, t, st: dict, why: str) -> None:
    _head("tilt")
    seed = t.target if t.target is not None else t.tilt
    if st["tilt"] is None and seed is not None:
        st["tilt"] = round(seed / TILT_STEP) * TILT_STEP
    v, let_go = _slider_row("tilt target, degrees: " + HOLD_TIP, "tilt", st, None,
                            -TILT_MAX, TILT_MAX, "%.1f°", whole=False, ident="kinect.tilt", why=why)
    if let_go:
        _ask(dev, "tilt", v)
    imgui.begin_disabled(bool(why))
    if ui.chip("go##kinect.tilt.go"):
        _ask(dev, "tilt", v)
    _tip(why or "send the target now")
    imgui.same_line()
    if ui.chip("level##kinect.tilt.level"):
        st["tilt"] = 0.0
        _ask(dev, "tilt", 0.0)
    _tip(why or "tilt to 0°")
    imgui.end_disabled()
    if why:
        _why(why)


def _led(dev, t, why: str) -> None:
    _head("LED")
    names = [n for n, _ in LEDS]
    now = names.index(t.led) if t.led in names else -1
    imgui.begin_disabled(bool(why))
    imgui.set_next_item_width(-1)
    changed, i = imgui.combo("##kinect.led", max(now, 0), names)
    imgui.end_disabled()
    _tip(why or ("the light on the front; the sensor cannot say which it shows"
                 if now < 0 else "the light on the front"))
    if changed:
        _ask(dev, "led", LEDS[i][1])
    if why:
        _why(why)


def _infrared(dev, t, st: dict, why: str) -> None:
    _head("infrared brightness")
    v, let_go = _slider_row("the IR camera's brightness, 1–50: " + HOLD_TIP, "ir", st, t.ir,
                            IR_MIN, IR_MAX, "%d", whole=True, ident="kinect.ir", why=why)
    if let_go:
        _ask(dev, "ir", int(v))
    if why:
        _why(why)


def _video(dev, t, st: dict, why) -> None:
    _head("video")
    imgui.begin_disabled(bool(why("video")))
    hit = ui.chip_group([f"{words}##kinect.video.{key}" for key, words in VIDEO_LABELS],
                        lit=[t.video == key for key, _ in VIDEO_LABELS],
                        tips=["no video stream", "the colour stream (it joins the cloud's colours)",
                              "the infrared picture"])
    imgui.end_disabled()
    if hit is not None and VIDEO_LABELS[hit][0] != t.video:
        _ask(dev, "video", VIDEO_LABELS[hit][0])
    if why("video"):
        _why(why("video"))
    for key, label in (("auto_exposure", "auto exposure"), ("white_balance", "auto white balance"),
                       ("flicker", "auto flicker")):
        w = why(key)
        imgui.begin_disabled(bool(w))
        changed, on = ui.checkbox(f"{label}##kinect.{key}", bool(t.flags.get(key, key == "auto_exposure")))
        imgui.end_disabled()
        _tip(w or ("what was last sent: libfreenect cannot read it back"
                   if key not in t.flags else ""))
        if changed:
            _ask(dev, key, on)
    if why("auto_exposure"):
        _why(f"auto settings: {why('auto_exposure')}")
    w = why("exposure")
    v, let_go = _slider_row("exposure time, µs: " + HOLD_TIP, "exposure", st, t.exposure,
                            EXPOSURE_MIN, EXPOSURE_MAX, "%d µs", whole=True,
                            ident="kinect.exposure", why=w)
    if let_go:
        _ask(dev, "exposure", int(v))
    if w and w != why("auto_exposure"):
        _why(f"exposure time: {w}")


def _streams(dev, why_restart: str, why_reconnect: str) -> None:
    _head("streams")
    imgui.begin_disabled(bool(why_restart))
    if ui.chip("restart##kinect.restart"):
        _ask(dev, "restart")
    _tip(why_restart or "stop every stream and start it again")
    imgui.end_disabled()
    imgui.same_line()
    imgui.begin_disabled(bool(why_reconnect))
    if ui.chip("reconnect##kinect.reconnect"):
        _ask(dev, "reconnect")
    _tip(why_reconnect or "close the sensor and open it again")
    imgui.end_disabled()


def _placement(dev) -> None:
    _head("placement")
    o = dev.options
    settings = (("near", o.near, 0.0, max(o.far - 0.05, 0.0), "%.2f m"),
                ("far", o.far, o.near + 0.05, 8.0, "%.2f m"),
                ("centre", o.centre, 0.0, 8.0, "%.2f m"))
    said = ""
    for name, v, lo, hi, fmt in settings:
        imgui.text_colored(ui.DIM, name)
        imgui.same_line(ui.LABEL_W)
        imgui.set_next_item_width(-1)
        changed, nv = imgui.slider_float(f"##kinect.{name}", float(v), float(lo), float(hi), fmt)
        if changed:
            said = dev.place(**{name: nv}) or said
    imgui.text_colored(ui.DIM, "step")
    imgui.same_line(ui.LABEL_W)
    imgui.set_next_item_width(-1)
    changed, step = imgui.slider_int("##kinect.step", int(o.step), 1, 16, "%d")
    if changed:
        said = dev.place(step=step) or said
    changed, mirror = ui.checkbox("mirror##kinect.mirror", bool(o.mirror))
    if changed:
        said = dev.place(mirror=mirror) or said
    if said:
        _why(said)
    _why(NOT_SAVED)


def _telemetry(t) -> None:
    _head("telemetry")
    _kv("model", t.model or "—")
    _kv("depth", f"{t.depth_fps:.0f} fps · {t.frames} frames")
    _kv("video", f"{t.video_fps:.0f} fps · {t.video_frames} frames" if t.video != "off" else "off")
    _kv("restarts", f"{t.restarts} streams · {t.reconnects} reconnects")
    _kv("read", _num(None if t.share is None else t.share * 100, "{:.0f}", " % of pixels"))
    _kv("nearest", _num(t.nearest, "{:.2f}", " m"))
    _kv("median", _num(t.median, "{:.2f}", " m"))
    _kv("points", f"{t.points}")
    if t.motor_why:
        _kv("motor", "not open")
        _why(t.motor_why)
    else:
        _kv("tilt", f"{_num(t.tilt, '{:.1f}', '°')} · {t.tilt_status or '—'}")
        a = t.accel
        _kv("accel", "—" if a is None else f"{a[0]:.2f} {a[1]:.2f} {a[2]:.2f} m/s²")
    if t.log:
        _why(f"libfreenect: {t.log}")
