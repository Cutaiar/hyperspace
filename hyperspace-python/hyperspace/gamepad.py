"""Xbox gamepad as a second hand on the hotkeys — polled raw through GLFW.

GLFW's bundled SDL mapping database misses this controller's Bluetooth-LE
GUID (030000005e040000130b000009050000) and a runtime mapping doesn't
take on macOS, so the pad is read through the raw joystick API with our
own index map, captured against a real Xbox Series S controller over
Bluetooth (fw 5.9.2709.0). Buttons 2/5/8/9 are unused gaps on this
firmware. Works identically over USB-C.

A pad with a Share button under the Xbox button reports it at 15 and
19 buttons after it (tools/pad_probe.py, 2026-10-15); the sixteen below
are the same, so one map reads both pads. Every other index a pad
reports has no name here: it is read and ignored.

**Every pad in one vocabulary (plan 42).** A pad is read by one of
four roads and lands in the same state — `buttons` by the indices
below (`pads.models.CANON`), the GLFW hat bits, six GLFW-style axes:

  glfw  the raw joystick API, through the map its model needs (the Xbox
        map below, or `SONY_GLFW_*` for a Sony pad over USB when hidapi
        is not there)
  hid   a DualSense or DualSense Edge over USB **or Bluetooth**
        (pads/hid.py): the face, and the touchpad, the motion sensors,
        the Edge's back and Fn buttons and every output GLFW never sees
  usb   a wired Xbox 360 pad over libusb (`UsbPad`)
  tape  a recorded hid session read back (an entry's ``tape =``)

A pad entry's ``controller =`` says which controllers it may take
(`pads.models.matches`): ``any`` (the next free one, as before), a model
(``edge``), a family (``sony``, ``xbox``) or a USB id. The touchpad and
the sensors are lanes of their own, ``touch:`` and ``motion:``
(pads/gesture.py); the outputs are `Effects` the device sends
(`send_effects`).

The Pad class mirrors app.Keys: poll once per frame, then edge-detect
with pressed(). A disconnect just makes the pad inert; reconnecting is
picked up on a later poll, no re-pairing dance in code.

Wired Xbox 360 pads (the Afterglow AX.1, 1BAD:F900, and any pad that
speaks the 360's USB protocol) are not HID: macOS has no driver for them,
so GLFW never sees one and the device sits unconfigured on the bus. With
``usb`` on, a pad GLFW cannot find is looked for over libusb instead
(`UsbPad`): its 20-byte input report is decoded into the same raw indices
the GLFW map above uses, so every binding works unchanged. GLFW wins when
it has a pad.
"""

from __future__ import annotations

import atexit
import math
import sys
import threading
import time
import warnings
from dataclasses import dataclass, replace

import glfw

from .pads import gesture, models, sony
from .pads.models import LFN, LP, RFN, RP, TOUCH

# raw button indices (captured; stick clicks follow the SDL layout). The
# Xbox button is GUIDE — captured, not in the factory table (on a
# Bluetooth pad it summons the OS overlay).
A, B, X, Y = 0, 1, 3, 4
LB, RB = 6, 7
VIEW, MENU = 10, 11
GUIDE = 12
LSTICK, RSTICK = 13, 14
SHARE = 15                  # only on a pad that has one; free of a factory row

# axes: sticks in ±1, triggers resting at −1.0. Unrouted, the left stick
# orbits, the right stick's Y zooms, its X rides the W planes' rates (the
# 4D spin) and the triggers ride depth4 (app.py)
AX_LX, AX_LY, AX_RX, AX_RY, AX_LT, AX_RT = 0, 1, 2, 3, 4, 5

# the D-pad is the hat, a GLFW bitmask
HAT_UP, HAT_RIGHT, HAT_DOWN, HAT_LEFT = 1, 2, 4, 8

DEADZONE = 0.18

# the names a row's source spells: pad:<BUTTON>, hat:<DIR>, axis:<AXIS>
BUTTONS = {"A": A, "B": B, "X": X, "Y": Y, "LB": LB, "RB": RB, "VIEW": VIEW,
           "MENU": MENU, "GUIDE": GUIDE, "LSTICK": LSTICK, "RSTICK": RSTICK,
           "SHARE": SHARE}
HATS = {"UP": HAT_UP, "RIGHT": HAT_RIGHT, "DOWN": HAT_DOWN, "LEFT": HAT_LEFT}
# what an Xbox pad lacks (plan 42), at indices no GLFW pad reaches: the
# touchpad's click, the Edge's back buttons and its Fn buttons. A pad
# lists them only when its model has them (`Pad.buttons_named`)
EXTRA_BUTTONS = dict(models.EXTRAS)
ALL_BUTTONS = {**BUTTONS, **EXTRA_BUTTONS}
assert all(models.CANON[n] == i for n, i in BUTTONS.items())   # one vocabulary

# a Sony pad over USB through GLFW's raw arrays (no hidapi): raw index →
# canonical (the Edge's descriptor: square, cross, circle, triangle, L1,
# R1, L2, R2, create, options, L3, R3, PS, touchpad, mic), and the axes'
# raw order LX LY RX L2 R2 RY as LX LY RX RY LT RT
SONY_GLFW_BUTTONS = {0: X, 1: A, 2: B, 3: Y, 4: LB, 5: RB, 8: VIEW, 9: MENU,
                     10: LSTICK, 11: RSTICK, 12: GUIDE, 13: TOUCH, 14: SHARE}
SONY_GLFW_AXES = (0, 1, 2, 5, 3, 4)
XBOX_RAW_MAX = 32          # an Xbox-mapped pad's raw buttons kept, below the extras

# the touchpad's and the sensors' schemes (plan 42), fed by the pad device
TOUCH_SCHEME, MOTION_SCHEME = "touch", "motion"
EXTRA_SCHEMES = (TOUCH_SCHEME, MOTION_SCHEME)

# the axes as continuous lanes (routing's `axis` scheme), each in [0, 1]:
# a stick rests at 0.5 with up and right high, a trigger rests at 0
AXES = ("LX", "LY", "RX", "RY", "LT", "RT")
AXIS_LABELS = ("left stick X", "left stick Y", "right stick X", "right stick Y",
               "left trigger", "right trigger")
AXIS_RESTS = (0.5, 0.5, 0.5, 0.5, 0.0, 0.0)
STICKS = frozenset(AXES[:4])      # centred: a learn on one lands a push

# how far from rest an axis must travel to complete a learn
LEARN_TRAVEL = 0.4

# the sticks' default camera job (`steer`, plan 27 B2: moved here from
# app.frame), each axis while no route names it: the left stick orbits,
# the right stick's Y zooms, its X rides the W planes' rate multipliers
# (rot.rate.*W, the 4D spin) and the triggers ride depth4
ORBIT_PER_S = 2.2     # camera.yaw / pitch, radians a second at full throw
ZOOM_OCTAVES_PER_S = 1.2
W_PLANES = ("XW", "YW", "ZW")
W_RATE_PER_S = 2.0    # rate units a second at full throw (a plane's default is 1×)
DEPTH_OCTAVES_PER_S = 2.4


# ---------------------------------------------------------------- the layout
# The pad drawn on screen (ui_pad.py), the APC40's `LAYOUT` for a gamepad:
# every control a row can name, where it sits on the device, and a short
# glyph. Two bands, in a unit grid (x right, y down) that draws like an
# Xbox pad's face: the buttons, the sticks and the D-pad above, the six
# axes as lanes under them — a trigger is an axis, so LT and RT are
# lanes, not a shape of their own.
#
#   LB RB            the bumpers, over each stick
#   LS RS            a stick's click (pad:LSTICK), the well drawn round
#                    with the live stick in it
#   A B X Y          the face buttons, in their diamond
#   BACK START       pad:VIEW and pad:MENU, with the Xbox button (XBOX)
#   SHR              pad:SHARE, on a pad that has one
#   ↑ ↓ ← →          the D-pad (hat:UP …)
#   LX LY RX RY      the sticks' axes, and LT RT the triggers' — lanes


@dataclass(frozen=True)
class Control:
    """One control of the pad: its routing source (``pad:A``, ``hat:UP``,
    ``axis:LX``), its kind (button, stick, axis), its glyph, and where it
    sits (x, y, w, h in layout units)."""

    source: str
    kind: str
    glyph: str
    x: float
    y: float
    w: float
    h: float

    @property
    def name(self) -> str:
        """The control in words ("left bumper")."""
        return control_name(self.source) or self.source

    @property
    def address(self) -> str:
        return self.source.partition(":")[2]


# the buttons in words, for the hovers; a face button is "A button"
_BUTTON_NAMES = {
    "LB": "left bumper", "RB": "right bumper", "VIEW": "BACK (View)",
    "MENU": "START (Menu)", "GUIDE": "Xbox button", "SHARE": "Share",
    "LSTICK": "left stick click", "RSTICK": "right stick click",
    "TOUCH": "touchpad click", "LP": "left back button", "RP": "right back button",
    "LFN": "left Fn button", "RFN": "right Fn button",
}


def control_name(source: str) -> str | None:
    """The control a routing source names, in words ("pad:LB" → "left
    bumper", "hat:UP" → "d-pad up", "axis:LT" → "left trigger"), or None
    for a source no gamepad sends."""
    scheme, _, addr = source.partition(":")
    if scheme == "pad":
        if addr in ("A", "B", "X", "Y"):
            return f"{addr} button"
        return _BUTTON_NAMES.get(addr) if addr in ALL_BUTTONS else None
    if scheme == "hat":
        return f"d-pad {addr.lower()}" if addr in HATS else None
    if scheme == "axis":
        return LANE_LABELS[LANES.index(addr)] if addr in LANES else None
    if scheme == TOUCH_SCHEME and addr in gesture.TOUCH_LANES:
        return gesture.TOUCH_LABELS[gesture.TOUCH_LANES.index(addr)]
    if scheme == MOTION_SCHEME and addr in gesture.MOTION_LANES:
        return gesture.MOTION_LABELS[gesture.MOTION_LANES.index(addr)]
    return None


def _layout() -> list[Control]:
    out: list[Control] = []

    def btn(name: str, glyph: str, x: float, y: float, w: float, h: float) -> None:
        out.append(Control(f"pad:{name}", "button", glyph, x, y, w, h))

    # the bumpers, and the left stick's well under its own
    btn("LB", "LB", 0.3, 0.0, 2.4, 0.8)
    btn("RB", "RB", 9.8, 0.0, 2.4, 0.8)
    out.append(Control("pad:LSTICK", "stick", "LS", 0.3, 1.0, 2.4, 2.6))
    # the middle: BACK and START, the Xbox button, Share beside it
    btn("VIEW", "BACK", 3.6, 0.9, 1.5, 0.8)
    btn("MENU", "START", 5.3, 0.9, 1.5, 0.8)
    btn("GUIDE", "XBOX", 4.45, 1.75, 1.5, 0.8)
    btn("SHARE", "SHR", 6.4, 1.75, 1.3, 0.8)
    # the D-pad, as a cross between the left stick and the middle
    for name, glyph, dx, dy in (("UP", "↑", 1.15, 0.0), ("LEFT", "←", 0.0, 0.95),
                                ("RIGHT", "→", 2.3, 0.95), ("DOWN", "↓", 1.15, 1.9)):
        out.append(Control(f"hat:{name}", "button", glyph, 2.75 + dx, 2.6 + dy, 1.15, 0.9))
    # the face buttons, in their diamond, and the right stick under them
    for name, dx, dy in (("Y", 1.25, 0.0), ("X", 0.0, 1.05), ("B", 2.5, 1.05), ("A", 1.25, 2.1)):
        btn(name, name, 8.6 + dx, 0.95 + dy, 1.25, 1.0)
    out.append(Control("pad:RSTICK", "stick", "RS", 9.1, 4.2, 2.4, 2.5))
    # the axes, as lanes across the foot
    for k, name in enumerate(AXES):
        out.append(Control(f"axis:{name}", "axis", name, 0.3 + k * 2.05, 6.85, 1.95, 0.65))
    return out


LAYOUT: list[Control] = _layout()
LAYOUT_W = max(c.x + c.w for c in LAYOUT)
LAYOUT_H = max(c.y + c.h for c in LAYOUT)
_BY_SOURCE = {c.source: c for c in LAYOUT}


# ---- a pad's own face (plan 42) ----
# The layout above is the Xbox's. A pad whose model has more draws more,
# in the room the Xbox face leaves: the touchpad across the top (its click
# `pad:TOUCH`, every ``touch:`` row on it), a tilt bubble under the left
# stick (every ``motion:`` row on it), the Edge's back buttons and Fn
# buttons between the D-pad and the right stick — and every glyph its own
# face's (✕ for ``pad:A``). The rows keep the canonical names.
_EXTRA_CONTROLS = {
    "touch": Control("pad:TOUCH", "touchpad", "TOUCH", 3.0, 0.0, 6.5, 0.8),
    "motion": Control("motion:roll", "tilt", "TILT", 0.3, 3.75, 2.3, 2.9),
    "back": (Control("pad:LP", "button", "L4", 5.3, 4.6, 1.6, 0.8),
             Control("pad:RP", "button", "R4", 7.2, 4.6, 1.6, 0.8)),
    "fn": (Control("pad:LFN", "button", "LFn", 5.3, 5.55, 1.6, 0.7),
           Control("pad:RFN", "button", "RFn", 7.2, 5.55, 1.6, 0.7)),
}
_LAYOUTS: dict[str, list[Control]] = {}


def layout_for(model) -> list[Control]:
    """The controls to draw for `model` (pads.models.Model, or None: the
    Xbox face, `LAYOUT`): the Xbox layout with the model's glyphs, then
    the extras its caps name (`_EXTRA_CONTROLS`). Kept per model."""
    if not models.is_model(model) or (not model.glyphs and not model.caps):
        return LAYOUT
    got = _LAYOUTS.get(model.id)
    if got is not None:
        return got
    out: list[Control] = []
    for c in LAYOUT:
        name = c.address if c.source.startswith(("pad:", "axis:")) else ""
        if c.source.startswith(("pad:", "axis:", "hat:")) and not model.has_control(c.address):
            continue                   # a single Joy-Con: no right stick, no D-pad (plan 43)
        out.append(replace(c, glyph=models.glyph(model, name, c.glyph)) if name else c)
    for cap in ("touch", "motion", "back", "fn"):
        if model.has(cap):
            extra = _EXTRA_CONTROLS[cap]
            for c in (extra if isinstance(extra, tuple) else (extra,)):
                out.append(replace(c, glyph=models.glyph(model, c.address, c.glyph))
                           if c.kind == "button" else c)
    _LAYOUTS[model.id] = out
    return out


def shown_model(pad):
    """The model the on-screen pad draws: the one read now, else the one
    the entry's ``controller =`` names, else None (the Xbox face)."""
    m = getattr(pad, "model", None) if getattr(pad, "on", False) else None
    if models.is_model(m):
        return m
    spec = models.parse_spec(getattr(pad, "controller", "any") or "any")
    return models.MODELS.get(spec) if spec else None


def control_in(layout: list[Control], source: str) -> Control | None:
    """The control of `layout` a source names: as `control`, and every
    ``touch:`` row on the touchpad, every ``motion:`` row on the tilt —
    unqualified sources only, as the layout's own are."""
    scheme, _, _addr = source.partition(":")
    if scheme in (TOUCH_SCHEME, MOTION_SCHEME):
        kind = "touchpad" if scheme == TOUCH_SCHEME else "tilt"
        return next((c for c in layout if c.kind == kind), None)
    c = control(source)
    if c is not None:
        return next((d for d in layout if d.source == c.source), c)
    return next((d for d in layout if d.source == source), None)


def control(source: str) -> Control | None:
    """The layout's control a routing source names, or None. An axis row
    may address its lane by number (``axis:4``, what an older file holds),
    which names the same control as ``axis:LT``."""
    c = _BY_SOURCE.get(source)
    if c is not None:
        return c
    scheme, _, addr = source.partition(":")
    if scheme == "axis" and addr.isdigit() and int(addr) < len(AXES):
        return _BY_SOURCE.get(f"axis:{AXES[int(addr)]}")
    return None


def glyph(source: str) -> str | None:
    """The glyph of the control a source names ("pad:LB" → "LB",
    "hat:UP" → "↑"), None for a source no gamepad sends."""
    c = control(source)
    return c.glyph if c is not None else None


def named(source: str) -> str | None:
    """A control in the words a message uses: the glyph, then its name
    ("LB (left bumper)"), or None when the pad has no such control."""
    c = control(source)
    return f"{c.glyph} ({c.name})" if c is not None else None

# ---- the dial (prototype): each stick also read as a clock face ----
# A stick's angle picks one of DIAL equal sectors — sector 0 straight up,
# then clockwise — and its distance from centre, 0 at rest to 1 at the
# rim, is how far that sector's lane reads. Every lane rests at 0, so a
# stick let go pushes nothing: the scene sits on its bases, sane, and each
# direction pushes one parameter of its own up from there. The lanes are
# more `axis` lanes after the six above (`Pad.lanes`), named
# ``<stick>.<compass>`` — ``axis:L.N`` up on the left stick, ``axis:R.SE``
# down-right on the right — so a route reads them like any other lane, and
# a route on one takes its stick off the camera job (`claims`).
#
# Two readings of the same clock, per stick (`Pad.dial_modes`):
#   petal  hard sectors: the sector the stick points into reads the whole
#          radius, every other 0. A border is sticky (DIAL_STICKY of a
#          sector's width past it) so a stick held on one does not flicker
#          between two parameters.
#   blend  soft sectors: each lane is a triangle about its own direction,
#          so a sweep round the rim crossfades one parameter into the next;
#          at any angle two neighbours share the radius between them.
DIAL = 8
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
DIAL_MODES = ("petal", "blend")
DIAL_STICKY = 0.15
DIAL_STICKS = {"L": (AX_LX, AX_LY), "R": (AX_RX, AX_RY)}
DIAL_LANES = tuple(f"{s}.{c}" for s in DIAL_STICKS for c in COMPASS)
DIAL_LABELS = tuple(f"{'left' if s == 'L' else 'right'} dial {c}"
                    for s in DIAL_STICKS for c in COMPASS)
DIAL_DEFAULT = {"L": "petal", "R": "blend"}

# every axis lane in `Pad.lanes` order: the six, then the dial's
LANES = AXES + DIAL_LANES
LANE_LABELS = AXIS_LABELS + DIAL_LABELS
LANE_RESTS = AXIS_RESTS + (0.0,) * len(DIAL_LANES)


def dial(x: float, y: float, mode: str = "petal", held: int | None = None,
         deadzone: float = DEADZONE) -> tuple[list[float], int | None]:
    """A stick at (x, y) — raw ±1, right and *up* positive — as DIAL lanes
    and the sector it points into (None inside the deadzone). The radius
    is cut by `deadzone` on the stick's distance, not per axis, so the
    angle is the stick's own, rescaled to reach 1 at the rim and clamped
    there (a pad's square gate reads past 1 on the diagonals). `held` is
    the sector a petal dial was in last frame: it is kept until the stick
    is DIAL_STICKY of a sector past its border."""
    out = [0.0] * DIAL
    r = math.hypot(x, y)
    if r < deadzone:
        return out, None
    r = min(1.0, (r - deadzone) / (1.0 - deadzone))
    a = (math.atan2(x, y) / math.tau * DIAL) % DIAL     # sectors, clockwise from up
    k = round(a) % DIAL
    if mode == "blend":
        for j in range(DIAL):
            d = abs((a - j + DIAL / 2) % DIAL - DIAL / 2)
            if d < 1.0:
                out[j] = r * (1.0 - d)
        return out, k
    if held is not None and abs((a - held + DIAL / 2) % DIAL - DIAL / 2) < 0.5 + DIAL_STICKY:
        k = held
    out[k] = r
    return out, k


def claims(lanes) -> set[int]:
    """The stick and trigger axes (AX_*) that routed `axis` lanes take off
    the camera job: a lane of the six is its own axis; a dial lane takes
    both of its stick's."""
    out = set()
    for i in lanes:
        if 0 <= i < len(AXES):
            out.add(i)
        elif len(AXES) <= i < len(LANES):
            out.update(DIAL_STICKS[LANES[i].partition(".")[0]])
    return out


def _unwrap(ret) -> list:
    """pyGLFW's raw joystick getters return a (pointer, count) pair."""
    if not ret:
        return []
    ptr, n = ret
    return [ptr[i] for i in range(n)]


# ---- wired Xbox 360 pads over USB ----

# the 360 protocol's interface: vendor class, subclass 0x5D, protocol 1
XINPUT_IFACE = (0xFF, 0x5D, 0x01)

# input report byte 2 / byte 3 bits → our raw button index; byte 2's low
# nibble is the D-pad → our hat bits
_B2_BTN = ((0x10, MENU), (0x20, VIEW), (0x40, LSTICK), (0x80, RSTICK))
_B3_BTN = ((0x01, LB), (0x02, RB), (0x04, GUIDE), (0x10, A), (0x20, B), (0x40, X), (0x80, Y))
_B2_HAT = ((0x01, HAT_UP), (0x02, HAT_DOWN), (0x04, HAT_LEFT), (0x08, HAT_RIGHT))
# the raw layout's width: every named index fits, SHARE's included — a 360
# pad has no Share button, so that one stays 0 in every report it sends
N_BUTTONS = 16

# the "you are player 1" ring: without it a 360 pad blinks all four quarters
LED_PLAYER_1 = bytes((0x01, 0x03, 0x06))


def _stick(lo: int, hi: int, flip: bool = False) -> float:
    v = int.from_bytes(bytes((lo, hi)), "little", signed=True) / 32767.0
    v = max(-1.0, min(1.0, v))
    return -v if flip else v


def decode(report: bytes) -> tuple[list[int], int, list[float]] | None:
    """A 360 pad's input report as (buttons, hat, axes) in this module's raw
    layout; None for any other message (LED and status reports). The
    sticks' Y is flipped to GLFW's sense (up is −1); triggers rest at −1."""
    if len(report) < 14 or report[0] != 0x00 or report[1] != 0x14:
        return None
    b2, b3 = report[2], report[3]
    buttons = [0] * N_BUTTONS
    for byte, table in ((b2, _B2_BTN), (b3, _B3_BTN)):
        for bit, i in table:
            if byte & bit:
                buttons[i] = 1
    hat = 0
    for bit, h in _B2_HAT:
        if b2 & bit:
            hat |= h
    axes = [_stick(report[6], report[7]), _stick(report[8], report[9], flip=True),
            _stick(report[10], report[11]), _stick(report[12], report[13], flip=True),
            report[4] / 127.5 - 1.0, report[5] / 127.5 - 1.0]
    return buttons, hat, axes


def _backend():
    """A libusb backend: the libusb-package wheel's, else a system libusb
    (Homebrew's included). None when there is none."""
    try:
        import libusb_package
        be = libusb_package.get_libusb1_backend()
        if be is not None:
            return be
    except Exception:  # noqa: BLE001, S110 — optional wheel; fall through
        pass
    try:
        import usb.backend.libusb1 as lb
    except ImportError:
        return None
    be = lb.get_backend()
    for path in ("/opt/homebrew/lib/libusb-1.0.dylib", "/usr/local/lib/libusb-1.0.dylib"):
        if be is not None:
            break
        be = lb.get_backend(find_library=lambda _, p=path: p)
    return be


def _xinput_interface(cfg):
    return next((i for i in cfg if (i.bInterfaceClass, i.bInterfaceSubClass,
                                    i.bInterfaceProtocol) == XINPUT_IFACE), None)


def _is_xinput(dev) -> bool:
    try:
        return any(_xinput_interface(cfg) is not None for cfg in dev)
    except Exception:  # noqa: BLE001 — a device that will not describe itself is not ours
        return False


class UsbPad:
    """One wired 360 pad read on its own thread: found (and found again
    after a replug) every RESCAN seconds, configured, its ring set to
    player 1, then read. `latest` is the last decoded report, None with no
    pad; `note` says why there is none. Never raises into the frame loop."""

    RESCAN = 2.0

    def __init__(self, start: bool = True):
        self._lock = threading.Lock()
        self._latest: tuple | None = None
        self._stop = threading.Event()
        self.name = ""
        self.note = ""
        self._thread = threading.Thread(target=self._run, name="usb-pad", daemon=True)
        if start:
            self._thread.start()

    def latest(self):
        with self._lock:
            return self._latest

    def close(self) -> None:
        self._stop.set()

    def _set(self, state) -> None:
        with self._lock:
            self._latest = state

    def _run(self) -> None:
        try:
            import usb.core
            import usb.util
        except ImportError:
            self.note = "usb pad: pyusb is not installed"
            return
        be = _backend()
        if be is None:
            self.note = "usb pad: no libusb found"
            return
        atexit.register(self.close)     # after libusb's own: runs before it
        while not self._stop.is_set():
            try:
                dev = next((d for d in usb.core.find(find_all=True, backend=be)
                            if _is_xinput(d)), None)
            except usb.core.USBError as e:
                self.note, dev = f"usb pad: {e}", None
            if dev is not None:
                try:
                    self._serve(dev, usb)
                except usb.core.USBError as e:
                    if self._stop.is_set() or sys.is_finalizing():
                        return      # libusb torn down under a pending read at exit
                    if self.name:
                        print(f"gamepad: {self.name} gone ({e})", file=sys.stderr)
                    self.note = f"usb pad: {e}"
                finally:
                    self._set(None)
                    self.name = ""
                    usb.util.dispose_resources(dev)
            self._stop.wait(self.RESCAN)

    def _serve(self, dev, usb) -> None:
        try:
            dev.get_active_configuration()
        except usb.core.USBError:   # nobody configured it — macOS never does
            dev.set_configuration()
        intf = _xinput_interface(dev.get_active_configuration())
        usb.util.claim_interface(dev, intf.bInterfaceNumber)
        ep_in = next(e for e in intf if e.bEndpointAddress & 0x80)
        ep_out = next((e for e in intf if not e.bEndpointAddress & 0x80), None)
        if ep_out is not None:
            try:
                ep_out.write(LED_PLAYER_1, timeout=200)
            except usb.core.USBError:
                pass            # the ring keeps blinking; input still works
        try:
            self.name = usb.util.get_string(dev, dev.iProduct) or "360 pad"
        except Exception:  # noqa: BLE001 — a name is a nicety
            self.name = "360 pad"
        self.note = ""
        print(f"gamepad: {self.name} over USB", file=sys.stderr)
        while not self._stop.is_set():
            try:
                state = decode(bytes(ep_in.read(32, timeout=100)))
            except usb.core.USBTimeoutError:
                continue
            if state is not None:
                self._set(state)


class Claims:
    """What the pad devices share (plan 27 B6: several pads at once), one
    per device registry (devices.Context.pads): which GLFW joystick each
    pad reads (`taken`, jid → the `Pad`), which indices a pad is pinned to
    (`pinned`, an entry's ``joystick = n`` — no unpinned pad takes one),
    the pads in attach order (`order`, the list's), the one libusb reader
    (`reader`, made the first time a pad borrows it) and the pad it is lent
    to now (`usb`). The reader is **lent, not owned** (ruling 3 as
    amended): each poll it goes to its holder while that pad still has
    `usb` on and no GLFW joystick (sticky), else to the first pad in
    `order` with `usb` on and no GLFW joystick. A `Pad` no device attached
    has none of this: it reads the first present joystick and its own
    reader."""

    def __init__(self):
        self.taken: dict[int, Pad] = {}
        self.pinned: dict[int, Pad] = {}
        self.order: list[Pad] = []
        self.reader: UsbPad | None = None
        self.usb: Pad | None = None
        self.hub = None        # pads.hid.HidHub, made the first time a `hid` pad looks (plan 42)

    def lend(self) -> Pad | None:
        """Who holds the reader this poll: the holder while it still may
        (attached, `usb` on, no GLFW joystick, no hid pad), else the first
        such pad in list order; None when no pad may."""
        def may(p: Pad) -> bool:
            return (p in self.order and getattr(p, "usb", False) and p.jid is None
                    and getattr(p, "hid_pad", None) is None
                    and models.matches(getattr(p, "controller", "any"), models.MODELS["x360"]))
        if self.usb is not None and may(self.usb):
            return self.usb
        return next((p for p in self.order if may(p)), None)

    def release(self, pad: Pad) -> None:
        """Everything `pad` held: its joystick, its pin, the USB reader,
        its hid pad."""
        for d in (self.taken, self.pinned):
            for j in [j for j, p in d.items() if p is pad]:
                del d[j]
        if self.usb is pad:
            self.usb = None
        if self.hub is not None:
            self.hub.release(pad)

    def hid_hub(self):
        """The one hub every `hid` pad borrows from (pads.hid), made on
        first ask; None where hidapi cannot be imported."""
        if self.hub is None:
            if self.__dict__.get("no_hid"):
                return None
            from .pads import hid
            if not hid.available():
                self.no_hid = True     # asked once: no import retried every frame
                return None
            self.hub = hid.HidHub(start=False)
            self.hub.scan()            # the pads there now, before the first poll looks
            self.hub.start()
        return self.hub


JOYSTICKS = range(glfw.JOYSTICK_1, glfw.JOYSTICK_LAST + 1)   # GLFW's indices, 0–15


class Pad:
    """Edge detection and analog reads over polled pad state. `usb`: look
    for a wired 360 pad over libusb when GLFW has none (`UsbPad`).

    Several pads at once (plan 27 B6): a pad its device `attach`es to the
    registry's shared `Claims` reads the next present GLFW joystick no
    other pad has taken (the devices poll in list order, so the first
    listed pad takes the first), or — pinned (`joystick`) — that index
    only, waiting while it is absent. A pad whose joystick leaves is
    `lost` and lets it go; unpinned, it takes the next free one that
    appears."""

    def __init__(self, usb: bool = False, hid: bool = False, controller: str = "any",
                 tape=None):
        self.jid: int | None = None
        # plan 42: which controllers this pad may take, the hid road, a tape
        self.controller = controller or "any"
        self.hid = hid
        self.tape = tape                   # a path: read this recording instead
        self.hid_pad = None                # the pads.hid reader (or tape) read now
        self.model: models.Model | None = None
        self.report: sony.Frame | None = None  # the last hid frame (touch, sensors, battery)
        self.touchpad = gesture.Touchpad()
        self.motion = gesture.Motion()
        self.axis_map: gesture.AxisMap | None = None   # set: the sensors' axes, over the reader's own
        self.effects: sony.Effects | None = None   # what the device asks the pad to show
        self._t: float | None = None
        self._guids: dict[int, tuple] = {}         # jid → (vid, pid, model) while present
        self._own_hub = None                       # a hub of its own, with no claims
        self.buttons: list = []
        self.prev_buttons: list = []
        self.hat = 0
        self.prev_hat = 0
        self.axes: list[float] = [0.0] * 6
        self.usb = usb
        self.usb_pad: UsbPad | None = None
        self.source: str | None = None     # "glfw", "hid", "tape", "usb" or None
        self.claims: Claims | None = None  # shared with the other pads (`attach`)
        self.role = ""
        self.joystick: int | None = None   # pinned GLFW index, or None
        self.dial_modes = dict(DIAL_DEFAULT)       # stick → "petal" / "blend"
        self.dial_lanes: list[float] = [0.0] * len(DIAL_LANES)
        self.dial_sectors: dict[str, int | None] = dict.fromkeys(DIAL_STICKS)

    def attach(self, claims: Claims, role: str = "", joystick: int | None = None) -> None:
        """Join the other pad devices (plan 27 B6): `claims` is the
        registry's shared `Claims`, `role` this pad's entry, `joystick` a
        pinned GLFW index. Attach order is list order: it decides who the
        one libusb reader is lent to (`Claims.lend`)."""
        self.claims, self.role, self.joystick = claims, role, joystick
        if joystick is not None:
            claims.pinned.setdefault(joystick, self)
        if self not in claims.order:
            claims.order.append(self)

    @property
    def usb_note(self) -> str:
        """Why this pad with `usb` on is not reading USB: the reader is
        lent to another pad (``usb: lent to p2``); "" otherwise, the reader
        idle included."""
        claims = getattr(self, "claims", None)
        holder = getattr(claims, "usb", None)
        if not getattr(self, "usb", False) or holder is None or holder is self:
            return ""
        return f"usb: lent to {holder.role or 'another pad'}"

    def _find(self) -> int | None:
        """The joystick this pad reads this frame: the one it has while it
        is present (and still its own), else the next free one — or, pinned,
        its index once present. None: no joystick for it now."""
        claims = getattr(self, "claims", None)
        jid = self.jid
        if jid is not None and glfw.joystick_present(jid) and self._may_read(jid) and (
                claims is None or (claims.taken.get(jid, self) is self
                                   and claims.pinned.get(jid, self) is self)):
            if claims is not None:
                claims.taken[jid] = self
            return jid
        if jid is not None and claims is not None and claims.taken.get(jid) is self:
            del claims.taken[jid]          # gone: free for whoever finds it next
        pin = getattr(self, "joystick", None)
        cands = JOYSTICKS if pin is None else ([pin] if pin in JOYSTICKS else [])
        for j in cands:
            if not glfw.joystick_present(j):
                continue
            if not self._may_read(j):
                continue                   # another model, or a Sony pad hid reads
            if claims is not None:
                if claims.taken.get(j, self) is not self:
                    continue               # another pad reads it
                if pin is None and claims.pinned.get(j, self) is not self:
                    continue               # pinned to another pad
                claims.taken[j] = self
            return j
        return None

    def _glfw_ids(self, j: int) -> tuple:
        """(vid, pid, model) of GLFW joystick `j`, from its GUID, asked once
        while it is present (`_guids`)."""
        cache = self.__dict__.setdefault("_guids", {})
        hit = cache.get(j)
        if hit is None:
            try:
                with warnings.catch_warnings():    # GLFW not up (a test): no GUID, no noise
                    warnings.simplefilter("ignore")
                    guid = glfw.get_joystick_guid(j)
            except Exception:  # noqa: BLE001 — a GUID is a nicety: no GUID, the Xbox map
                guid = None
            if isinstance(guid, bytes):
                guid = guid.decode("ascii", "replace")
            vid, pid = models.glfw_ids(guid)
            hit = cache[j] = (vid, pid, models.by_ids(vid, pid))
        return hit

    def _kept(self) -> bool:
        """Is the joystick this pad read last frame still its to read?"""
        jid, claims = self.jid, getattr(self, "claims", None)
        return (jid is not None and glfw.joystick_present(jid) and self._may_read(jid)
                and (claims is None or (claims.taken.get(jid, self) is self
                                        and claims.pinned.get(jid, self) is self)))

    def _may_read(self, j: int) -> bool:
        """May this pad take GLFW joystick `j`? Not when it is a Sony pad
        the hid road reads (the same pad twice), nor when its model is not
        one ``controller =`` names. The GUID is asked only when it matters."""
        spec = getattr(self, "controller", "any") or "any"
        hub = self._hub(make=False)
        if spec == "any" and (hub is None or not hub.readers):
            return True
        vid, pid, model = self._glfw_ids(j)
        if hub is not None and vid == models.SONY_VID and hub.holds(vid, pid):
            return False
        return models.matches(spec, model, vid, pid)

    def _hub(self, make: bool = True):
        """The hid hub this pad borrows from: the registry's (`Claims`), or
        one of its own for a pad no device attached; None with `hid` off or
        no hidapi."""
        if not getattr(self, "hid", False) or not models.may_be_hid(
                getattr(self, "controller", "any")):
            return None                # an Xbox-only entry opens (and seizes) no hid pad
        claims = getattr(self, "claims", None)
        if claims is not None:
            return claims.hid_hub() if make else claims.hub
        own = self.__dict__.get("_own_hub")
        if own is None and make and not self.__dict__.get("no_hid"):
            from .pads import hid
            if hid.available():
                own = self._own_hub = hid.HidHub(start=False)
                own.scan()
                own.start()
            else:
                self.no_hid = True
        return own

    def _hid_reader(self):
        """The hid reader (or tape) this pad reads this poll, or None."""
        tape = getattr(self, "tape", None)
        if tape:
            r = self.__dict__.get("hid_pad")
            if r is None or getattr(r, "road", "") != "tape":
                import os
                try:
                    stamp = (tape, os.stat(tape).st_mtime)
                except OSError:
                    stamp = (tape, None)
                if self.__dict__.get("_tape_failed") == stamp:
                    return None        # the same bad file: said once, not re-read each frame
                from .pads import hid
                try:
                    r = hid.TapePad(tape)
                except Exception as e:  # noqa: BLE001 — a missing or bad tape is said, not raised
                    self.__dict__["tape_note"] = f"tape: {type(e).__name__}: {e}"[:120]
                    self.__dict__["_tape_failed"] = stamp
                    return None
            return r
        hub = self._hub()
        if hub is None:
            return None
        return hub.take(self, getattr(self, "controller", "any"))

    @property
    def on(self) -> bool:
        return getattr(self, "source", None) is not None

    def has(self, cap: str) -> bool:
        """Does the pad read now have `cap` ("touch", "motion", "light" …)?"""
        m = getattr(self, "model", None)
        return m is not None and m.has(cap)

    @property
    def buttons_named(self) -> dict[str, int]:
        """The buttons this pad has, by name: the Xbox face, and the extras
        its model has (the touchpad's click; the Edge's back and Fn)."""
        out = dict(BUTTONS)
        if self.has("touch"):
            out["TOUCH"] = TOUCH
        if self.has("back"):
            out.update(LP=LP, RP=RP)
        if self.has("fn"):
            out.update(LFN=LFN, RFN=RFN)
        m = getattr(self, "model", None)
        if models.is_model(m) and m.controls is not None:    # a single Joy-Con: less than a face
            out = {n: i for n, i in out.items() if m.has_control(n)}
        return out

    @property
    def status(self) -> str:
        """The device line's word (plan 27 B2): `connected` while a pad is
        read (GLFW or USB), `lost` while none is — the pad looks for one
        itself on every poll, so it is never an error."""
        return "connected" if self.on else "lost"

    def open(self) -> None:
        """Nothing to open: a pad is looked for on every `poll` (GLFW's
        joysticks, then libusb when `usb` is on). Here so the pad answers
        the device protocol's `open` / `poll` / `close` itself."""

    def publish(self, router, scheme: str = "axis") -> None:
        """The axes' names, labels and rests on the router (`publish`),
        under `scheme` (a second pad's ``axis@p2``)."""
        publish(router, scheme)

    def poll(self, dt: float | None = None) -> None:
        """Read the pad for this frame: a tape when the entry names one,
        else a GLFW joystick, else a hid pad, else the libusb reader
        (plan 42's roads, in that order). `dt` the frame's time, for the
        touch and motion lanes (None: the clock's since the last poll)."""
        source = getattr(self, "source", None)
        now = time.monotonic()
        last = self.__dict__.get("_t")
        self._t = now
        if dt is None:
            dt = self.__dict__.pop("dt_hint", None)       # the device's frame time
        if dt is None:
            dt = 0.0 if last is None else min(0.25, now - last)
        reader, frame, state = None, None, None
        if getattr(self, "tape", None) or (
                not self._kept() and getattr(self, "joystick", None) is None):
            # a tape, or a Sony pad hid lends this entry — never in place of a
            # joystick it is reading (plugging an Edge in mid-show moves no
            # one), nor for a pad pinned to a GLFW index
            reader = self._hid_reader()
        if reader is not None:
            # hid first: GLFW sees the same pad (over USB and Bluetooth) but not
            # its extras; a lent pad not reporting yet (connecting, a BT gap)
            # is still this entry's — no other road for it meanwhile
            self.jid = None
            claims = getattr(self, "claims", None)
            if claims is not None:
                for j in [j for j, p in claims.taken.items() if p is self]:
                    del claims.taken[j]
            frame = reader.latest()
        elif getattr(self, "tape", None):
            self.jid = None            # a tape entry reads its tape or nothing
        else:
            self.jid = self._find()
        self.hid_pad = reader
        claims = getattr(self, "claims", None)
        if claims is not None and claims.usb is self and (self.jid is not None or frame is not None):
            claims.usb, self.usb_pad = None, None    # reading GLFW or hid: the reader goes back
        if self.jid is None and reader is None and not getattr(self, "tape", None):
            state = self._usb_state()      # no joystick, no hid pad lent: the libusb reader
        new = ("glfw" if self.jid is not None else
               ("tape" if getattr(reader, "road", "") == "tape" else "hid") if frame is not None else
               "usb" if state is not None else None)
        if new != source:      # a pad came, went or changed road: no stale edges
            self.buttons, self.hat, self.axes = [], 0, [0.0] * 6
            self.touchpad, self.motion = gesture.Touchpad(), gesture.Motion()
            self.report = None
        self.source = new
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        if new == "glfw":
            # the model from the GUID (kept while the joystick is there): a
            # Sony pad reads through its own map, hid or no hid
            self.model = self._glfw_ids(self.jid)[2]
            self._read_glfw()
        elif new in ("hid", "tape"):
            self.model = reader.model
            self.buttons, self.hat, self.axes = frame.buttons, frame.hat, list(frame.axes)
            self._extras(frame, reader, dt)
        elif new == "usb":
            self.model = models.MODELS["x360"]
            self.buttons, self.hat, self.axes = state
        else:
            self.model = None
        guids = self.__dict__.setdefault("_guids", {})
        for j in [j for j in guids if j != self.jid and not glfw.joystick_present(j)]:
            del guids[j]                   # a joystick gone: asked afresh when one comes

    def _read_glfw(self) -> None:
        raw = _unwrap(glfw.get_joystick_buttons(self.jid))
        hats = _unwrap(glfw.get_joystick_hats(self.jid))
        self.hat = hats[0] if hats else 0
        ax = _unwrap(glfw.get_joystick_axes(self.jid))
        m = getattr(self, "model", None)
        if m is not None and m.family == "sony":
            out = [0] * models.N_CANON
            for i, c in SONY_GLFW_BUTTONS.items():
                if i < len(raw) and raw[i]:
                    out[c] = 1
            self.buttons = out
            if len(ax) >= 6:
                self.axes = [ax[i] for i in SONY_GLFW_AXES]
            return
        self.buttons = raw[:XBOX_RAW_MAX]
        if len(ax) >= 6:
            self.axes = ax

    def _extras(self, frame: sony.Frame, reader, dt: float) -> None:
        """The touch and motion lanes from a hid frame (a Bluetooth simple
        report has neither: its lanes stay as they were, not live)."""
        self.report = frame
        if not frame.full:
            return
        w, h = sony.TOUCH_W - 1, sony.TOUCH_H - 1
        self.touchpad.step([(t.down, t.id, t.x / w, t.y / h) for t in frame.touches], dt)
        cal = getattr(reader, "calibration", None) or sony.Calibration()
        amap = gesture.axis_map_of(self.__dict__.get("axis_map"), reader)   # the one rule
        gyro = amap.pick(cal.gyro_dps(frame.gyro), amap.gyro)
        accel = amap.pick(cal.accel_g(frame.accel), amap.accel)
        self.motion.step(gyro, accel, dt)

    def touch_lanes(self) -> list[float] | None:
        """The ``touch:`` lanes (gesture.TOUCH_LANES), or None while the
        pad read has no touchpad or says nothing on it."""
        f = self.__dict__.get("report")
        if not self.on or not self.has("touch") or f is None or not f.full:
            return None
        return self.touchpad.lanes()

    def motion_lanes(self) -> list[float] | None:
        """The ``motion:`` lanes (gesture.MOTION_LANES), or None."""
        f = self.__dict__.get("report")
        if not self.on or not self.has("motion") or f is None or not f.full:
            return None
        return self.motion.lanes()

    def send_effects(self, effects: sony.Effects) -> None:
        """Ask the pad to show `effects` (light, LEDs, rumble, triggers):
        handed to the hid reader, which writes only what changed. A pad
        with no outputs keeps it, unsent."""
        self.effects = effects
        r = self.__dict__.get("hid_pad")
        if r is not None and self.on and hasattr(r, "send"):
            r.send(effects)

    @property
    def link(self) -> str:
        """How the pad read now is connected — "usb", "bluetooth", "tape",
        "glfw" — for the SYSTEM line."""
        if self.source in ("hid", "tape"):
            return getattr(self.hid_pad, "transport", "") or self.source
        return self.source or ""

    def close(self) -> None:
        """Stop the USB reader thread, when one was started (plan 27 B1:
        the pad is on the one close list, so a restart's new image finds
        the device free), and forget the pad: a later `poll` would find
        it again. Never raises."""
        usb = getattr(self, "usb_pad", None)
        self.usb_pad = None
        claims = getattr(self, "claims", None)
        if claims is not None:
            claims.release(self)       # its joystick, its pin, the USB reader (plan 27 B6)
            if self in claims.order:
                claims.order.remove(self)
            # the shared reader closes only when no pad left could borrow it
            usb = None
            if claims.reader is not None and not any(
                    getattr(p, "usb", False) for p in claims.order):
                usb, claims.reader = claims.reader, None
        self.jid, self.source = None, None
        self.buttons, self.prev_buttons, self.hat, self.prev_hat = [], [], 0, 0
        r, self.hid_pad = self.__dict__.get("hid_pad"), None
        if getattr(r, "road", "") == "tape":
            r.close()
        own = self.__dict__.pop("_own_hub", None)
        if own is not None:
            own.close()
        if claims is not None and claims.hub is not None and not any(
                getattr(p, "hid", False) for p in claims.order):
            claims.hub.close()             # no pad left to lend to
            claims.hub = None
        if usb is not None:
            usb.close()
            thread = getattr(usb, "_thread", None)
            if thread is not None and thread.is_alive():
                thread.join(0.5)        # (a read in flight ends within its 100 ms timeout)
    def dials(self) -> list[float]:
        """The dial lanes (DIAL_LANES order) for the sticks as they read
        now. A petal dial's sticky border is state, so the dials move only
        when the sticks or a mode do: `lanes`, read several times a
        frame, gets the same answer each time."""
        modes = self.__dict__.setdefault("dial_modes", dict(DIAL_DEFAULT))
        sectors = self.__dict__.setdefault("dial_sectors", dict.fromkeys(DIAL_STICKS))
        seen = (tuple(self.axes[:4]), tuple(modes.items()))
        if self.__dict__.get("_dial_seen") == seen:
            return self.dial_lanes
        lanes: list[float] = []
        for stick, (ax, ay) in DIAL_STICKS.items():
            x = self.axes[ax] if ax < len(self.axes) else 0.0
            y = -self.axes[ay] if ay < len(self.axes) else 0.0
            vals, sectors[stick] = dial(x, y, modes.get(stick, "petal"), sectors.get(stick))
            lanes += vals
        self.dial_lanes, self._dial_seen = lanes, seen
        return lanes

    def _usb_state(self):
        """The USB pad's latest report; starts its reader the first time
        GLFW has nothing. Kept on the instance, so a hot reload of this
        module never starts a second reader fighting for the device."""
        if not getattr(self, "usb", False):
            return None
        claims = getattr(self, "claims", None)
        if claims is not None:              # several pads: one reader, lent (plan 27 B6)
            if claims.lend() is not self:
                return None
            claims.usb = self
            if claims.reader is None:
                claims.reader = UsbPad()
            self.usb_pad = claims.reader
            return claims.reader.latest()
        if getattr(self, "usb_pad", None) is None:
            self.usb_pad = UsbPad()
        return self.usb_pad.latest()

    def down(self, b: int) -> bool:
        return b < len(self.buttons) and bool(self.buttons[b])

    def pressed(self, b: int) -> bool:
        was = b < len(self.prev_buttons) and bool(self.prev_buttons[b])
        return self.down(b) and not was

    def released(self, b: int) -> bool:
        was = b < len(self.prev_buttons) and bool(self.prev_buttons[b])
        return was and not self.down(b)

    def hat_pressed(self, bit: int) -> bool:
        return bool(self.hat & bit) and not (self.prev_hat & bit)

    def hat_released(self, bit: int) -> bool:
        return bool(self.prev_hat & bit) and not (self.hat & bit)

    def lanes(self) -> list[float]:
        """The axes as routing lanes in LANES order, each in [0, 1]: the six
        (sticks about 0.5, deadzone cut out, up and right high; triggers
        from 0), then the dial's, resting at 0."""
        sticks = [0.5 + 0.5 * self.axis(AX_LX), 0.5 - 0.5 * self.axis(AX_LY),
                  0.5 + 0.5 * self.axis(AX_RX), 0.5 - 0.5 * self.axis(AX_RY)]
        return sticks + [self.trigger(AX_LT), self.trigger(AX_RT)] + self.dials()

    def axis(self, i: int) -> float:
        """Stick axis with the deadzone cut out and the rest rescaled to ±1."""
        v = self.axes[i] if i < len(self.axes) else 0.0
        if abs(v) < DEADZONE:
            return 0.0
        s = 1.0 if v > 0 else -1.0
        return s * (abs(v) - DEADZONE) / (1.0 - DEADZONE)

    def trigger(self, i: int) -> float:
        """Trigger travel in [0, 1] (raw axis rests at −1)."""
        v = (self.axes[i] + 1.0) / 2.0 if i < len(self.axes) else 0.0
        return v if v > 0.02 else 0.0


def dialed(lanes) -> set[str]:
    """The sticks ("L", "R") that routed `axis` lanes use as a dial."""
    return {LANES[i].partition(".")[0] for i in lanes if len(AXES) <= i < len(LANES)}


def learn_from(pad: Pad, learn, role: str = "", dials=frozenset) -> bool:
    """The pad completes an armed learn (learn.Learn, duck-typed — this
    module imports nothing from the package): the first button or D-pad
    press this frame lands a button row (`Learn.learn_pad_button`), else
    the first axis LEARN_TRAVEL from rest a route (`Learn.learn_source`;
    a stick is centred, so a push). A stick in `dials()` — the sticks a
    route already reads as a dial (`dialed`), asked only once a learn is
    armed — lands the sector it points into instead, ``axis:L.NE``,
    resting at 0, so a dial is filled one direction at a time. On a
    setting no performer may drive
    (not modulatable) only a button can: the axes are not asked, so a
    nudged stick never ends the learn. True when the press was the
    learn's, so the router lets that frame's button rows be. `role` is a
    second pad's qualifier (plan 27 B6): its rows read ``pad@p2:A``,
    ``hat@p2:UP``, ``axis@p2:LX``; "" (the primary pad) leaves them bare."""
    if learn is None or getattr(learn, "learning", None) is None or not pad.on:
        return False
    target = learn.target_for(learn.learning)
    q = f"@{role}" if role else ""          # routing.QUALIFIER (nothing imported here)
    named = getattr(pad, "buttons_named", None)      # plan 42: the extras the pad has
    for name, i in (named if isinstance(named, dict) else BUTTONS).items():
        if pad.pressed(i) and learn.accepts(f"pad{q}:{name}"):
            learn.learn_pad_button(f"pad{q}:{name}")
            return True
    for name, bit in HATS.items():
        if pad.hat_pressed(bit) and learn.accepts(f"hat{q}:{name}"):
            learn.learn_pad_button(f"hat{q}:{name}")
            return True
    if target is None or not target.modulatable:
        return False
    sticks = dials()
    pad.dials()                 # the sectors as the sticks read now
    sectors = pad.dial_sectors
    for stick in sticks:
        k = sectors.get(stick)
        if k is None:
            continue
        name = f"{stick}.{COMPASS[k]}"
        x, y = (pad.axes[a] if a < len(pad.axes) else 0.0 for a in DIAL_STICKS[stick])
        if math.hypot(x, y) >= DEADZONE + LEARN_TRAVEL and learn.accepts(f"axis{q}:{name}"):
            learn.learn_source(f"axis{q}:{name}")
            return False
    taken = {a for s in sticks for a in DIAL_STICKS[s]}
    for i, (name, u, rest) in enumerate(zip(AXES, pad.lanes(), AXIS_RESTS)):
        if i in taken:
            continue
        if abs(u - rest) >= LEARN_TRAVEL and learn.accepts(f"axis{q}:{name}"):
            learn.learn_source(f"axis{q}:{name}", centred=name in STICKS)
            return False        # an axis has no button row to hold back
    got = _learn_extra(pad, learn)
    if got is not None:
        scheme, name, centred = got
        if learn.accepts(f"{scheme}{q}:{name}"):
            learn.learn_source(f"{scheme}{q}:{name}", centred=centred)
    return False


TOUCH_LEARN_TRAVEL = 0.25      # a finger dragged this far (of the pad) lands x or y
GESTURE_LEARN = 0.2            # pinch / twist / tilt this far from rest lands it


def _learn_extra(pad, learn=None) -> tuple[str, str, bool] | None:
    """The touch or motion lane a Learn pad lands (plan 42), or None: a
    finger dragged `TOUCH_LEARN_TRAVEL` along x or y (whichever it went
    further), a pinch or a twist `GESTURE_LEARN` from rest, a tap; a tilt
    `GESTURE_LEARN` in roll or pitch, a shake. The spin and energy lanes
    are not learned — a hand moving to press something would land them;
    they are routed on GRAPH. (scheme, lane, centred)."""
    touch = pad.touch_lanes() if hasattr(pad, "touch_lanes") else None
    if touch is not None:
        t = dict(zip(gesture.TOUCH_LANES, touch, strict=True))
        for name in ("pinch", "twist"):
            if math.isfinite(t[name]) and abs(t[name] - 0.5) >= GESTURE_LEARN:
                return TOUCH_SCHEME, name, True
        first = getattr(getattr(pad, "touchpad", None), "_first", None)
        if first is not None and first[4] >= TOUCH_LEARN_TRAVEL and math.isfinite(t["x"]):
            dx = abs(t["x"] - first[2])
            dy = abs((1.0 - t["y"]) - first[3])
            return TOUCH_SCHEME, "x" if dx >= dy else "y", False
        if t["tap"]:
            return TOUCH_SCHEME, "tap", False
    motion = pad.motion_lanes() if hasattr(pad, "motion_lanes") else None
    if motion is not None:
        m = dict(zip(gesture.MOTION_LANES, motion, strict=True))
        if m["shake"]:
            return MOTION_SCHEME, "shake", False
        # a tilt counts from where the pad was held when the learn was armed
        # (a pad in the hand is never level): a fresh baseline per arm, as
        # the hands' (`armed_n`)
        key = (getattr(learn, "learning", None), getattr(learn, "want", None),
               getattr(learn, "armed_n", None))
        base = pad.__dict__.get("_learn_tilt")
        if base is None or base[0] != key:
            pad._learn_tilt = (key, m["roll"], m["pitch"])
            return None
        for name, b in (("roll", base[1]), ("pitch", base[2])):
            if abs(m[name] - b) >= GESTURE_LEARN:
                return MOTION_SCHEME, name, True
    return None


def publish(router, scheme: str = "axis") -> None:
    """The `axis` lanes' names, labels and rests on `router` (its `names`,
    `labels`, `rests` dicts, duck-typed) — the pad's to say, not the
    table's (plan 27 B2: they left `Router._publish_axes`). Once: the names
    map is published as one new dict, so the router's address cache keeps.
    `scheme` is a second pad's qualified key (``axis@p2``, plan 27 B6)."""
    if scheme in router.names:
        return
    # the six axes, then the sticks' dial lanes (LANES: `axis:L.N` …)
    router.labels[scheme] = list(LANE_LABELS)
    router.rests[scheme] = list(LANE_RESTS)
    router.names[scheme] = {n: i for i, n in enumerate(LANES)}


def ride_depth(p, octaves: float) -> None:
    """Move 4D depth by a number of octaves of (depth − 1) — the taper's
    own space (the triggers here, ↑/↓ in app.py)."""
    u = math.log2(max(p.base - 1.0, 1e-6) / 0.05)
    p.nudge(1.0 + 0.05 * 2.0 ** (u + octaves) - p.base)


def steer(pad, router, reg, dt: float, routed=None) -> None:
    """The sticks' default camera job (moved from app.frame, plan 27 B2):
    each axis **while no route names it** (`router.claimed("axis")`, an
    `axis:LX` row takes its stick off the job) writes a relative move on
    the base — the left stick orbits (`camera.yaw` / `pitch`), the right
    stick's Y zooms about centre (`camera.zoom`), its X rides the three W
    planes' rates together (the 4D spin), the triggers ride depth4 in its
    own log space (LT out, RT in). The pad's feel (`desk.pad.feel`,
    motion.py, `router.felt`) runs on the axis lanes first; off, they are
    read as they are. `reg` is the parameter registry (`reg["camera.yaw"]`,
    duck-typed); nothing here imports the package. Nothing while no pad
    is on."""
    if pad is None or not pad.on:
        return
    # a dial lane (`axis:L.NE` …) takes its whole stick off the job (`claims`);
    # `routed`, the lanes a route reads, when the caller already asked
    routed = claims(router.claimed("axis") or () if routed is None else routed)
    felt = router.felt("axis", pad.lanes(), dt)
    if felt is None:
        axis, trigger = pad.axis, pad.trigger
    else:
        def axis(ax: int) -> float:   # a lane back to the stick's ±1, up negative
            u = felt[ax] - 0.5
            return 2 * u if ax in (AX_LX, AX_RX) else -2 * u

        def trigger(ax: int) -> float:
            return felt[ax]

    def free(ax: int, v: float) -> float:
        return 0.0 if ax in routed else v
    lx = free(AX_LX, axis(AX_LX))
    ly = free(AX_LY, axis(AX_LY))
    if lx:
        reg["camera.yaw"].nudge(lx * ORBIT_PER_S * dt)
    if ly:
        reg["camera.pitch"].nudge(ly * ORBIT_PER_S * dt)
    zoom_v = free(AX_RY, axis(AX_RY))
    if zoom_v:
        reg["camera.zoom"].scale(2.0 ** (-zoom_v * ZOOM_OCTAVES_PER_S * dt))
    # right-stick X rides the three W planes' rates together (the 4D
    # spin): right speeds them up, left slows them through 0 into reverse
    w_v = free(AX_RX, axis(AX_RX))
    if w_v:
        for plane in W_PLANES:
            reg[f"rot.rate.{plane}"].nudge(w_v * W_RATE_PER_S * dt)
    d4 = free(AX_RT, trigger(AX_RT)) - free(AX_LT, trigger(AX_LT))
    if d4:
        ride_depth(reg["view.depth4"], d4 * DEPTH_OCTAVES_PER_S * dt)
