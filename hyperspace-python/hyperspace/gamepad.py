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

import glfw

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

# the axes as continuous lanes (routing's `axis` scheme), each in [0, 1]:
# a stick rests at 0.5 with up and right high, a trigger rests at 0
AXES = ("LX", "LY", "RX", "RY", "LT", "RT")
AXIS_LABELS = ("left stick X", "left stick Y", "right stick X", "right stick Y",
               "left trigger", "right trigger")
AXIS_RESTS = (0.5, 0.5, 0.5, 0.5, 0.0, 0.0)
STICKS = frozenset(AXES[:4])      # centred: a learn on one lands a push

# how far from rest an axis must travel to complete a learn
LEARN_TRAVEL = 0.4

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
    except Exception:  # noqa: BLE001 — optional wheel; fall through
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


class Pad:
    """Edge detection and analog reads over polled pad state. `usb`: look
    for a wired 360 pad over libusb when GLFW has none (`UsbPad`)."""

    def __init__(self, usb: bool = False):
        self.jid: int | None = None
        self.buttons: list = []
        self.prev_buttons: list = []
        self.hat = 0
        self.prev_hat = 0
        self.axes: list[float] = [0.0] * 6
        self.usb = usb
        self.usb_pad: UsbPad | None = None
        self.source: str | None = None     # "glfw", "usb" or None
        self.dial_modes = dict(DIAL_DEFAULT)       # stick → "petal" / "blend"
        self.dial_lanes: list[float] = [0.0] * len(DIAL_LANES)
        self.dial_sectors: dict[str, int | None] = dict.fromkeys(DIAL_STICKS)

    @property
    def on(self) -> bool:
        return getattr(self, "source", None) is not None

    def poll(self) -> None:
        source = getattr(self, "source", None)
        if self.jid is None or not glfw.joystick_present(self.jid):
            self.jid = next(
                (j for j in range(glfw.JOYSTICK_1, glfw.JOYSTICK_LAST + 1)
                 if glfw.joystick_present(j)),
                None,
            )
        state = None if self.jid is not None else self._usb_state()
        new = "glfw" if self.jid is not None else "usb" if state is not None else None
        if new != source:      # a pad came, went or changed road: no stale edges
            self.buttons, self.hat, self.axes = [], 0, [0.0] * 6
        self.source = new
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        if new == "glfw":
            self.buttons = _unwrap(glfw.get_joystick_buttons(self.jid))
            hats = _unwrap(glfw.get_joystick_hats(self.jid))
            self.hat = hats[0] if hats else 0
            ax = _unwrap(glfw.get_joystick_axes(self.jid))
            if len(ax) >= 6:
                self.axes = ax
        elif new == "usb":
            self.buttons, self.hat, self.axes = state

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


def learn_from(pad: Pad, learn, dials=frozenset) -> bool:
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
    learn's, so the router lets that frame's button rows be."""
    if learn is None or getattr(learn, "learning", None) is None or not pad.on:
        return False
    target = learn.target_for(learn.learning)
    for name, i in BUTTONS.items():
        if pad.pressed(i) and learn.accepts(f"pad:{name}"):
            learn.learn_pad_button(f"pad:{name}")
            return True
    for name, bit in HATS.items():
        if pad.hat_pressed(bit) and learn.accepts(f"hat:{name}"):
            learn.learn_pad_button(f"hat:{name}")
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
        if math.hypot(x, y) >= DEADZONE + LEARN_TRAVEL and learn.accepts(f"axis:{name}"):
            learn.learn_source(f"axis:{name}")
            return False
    taken = {a for s in sticks for a in DIAL_STICKS[s]}
    for i, (name, u, rest) in enumerate(zip(AXES, pad.lanes(), AXIS_RESTS)):
        if i in taken:
            continue
        if abs(u - rest) >= LEARN_TRAVEL and learn.accepts(f"axis:{name}"):
            learn.learn_source(f"axis:{name}", centred=name in STICKS)
            return False        # an axis has no button row to hold back
    return False
