"""Ultraleap hands — two tracked hands as twelve axes and eight switches.

The hands are the performing surface; the APC40 stays on presets and
master controls. Each hand gives the palm's rigid-body pose — six axes by
default — and every axis is an analog signal (signal.py): calibrated,
smoothed, shaped (dead zone, curve), enveloped (attack, decay), sprung
back to a rest value when the hand leaves, and glided back onto the hand
when it returns. The output y ∈ [0, 1] goes two ways:

  * inside Hyperspace, as ``hand:<i>`` sources in the routing table
    (routing.py) at float precision: right-click → Learn writes a
    `position` route (the hand is the fader), and the ROUTING page can
    `push` or `position` anything with it — one performer per param, the
    table's referee asks before a hand takes over. No MIDI in between,
    so no 7-bit steps and no channel shared with the APC40.
  * outside, to a MIDI port for a DAW (a virtual "Hyperspace Hands" port
    unless [hands] out names another): per axis 7-bit CC, 14-bit CC,
    pitch bend or channel pressure on any channel, rate-limited, plus a
    presence note per hand, and a note per pinch switch.

What Ultraleap reports (LeapC through the ``leap`` Python bindings; units
are the SDK's, coordinates right-handed with the origin at the camera, +y
away from it, +z toward the performer in desktop mode):

  feature     source                            native unit    default range
  x y z       palm.position                     mm             calibrated per hand
  roll        palm.normal    atan2(n.x, −n.y)   degrees        ±90
  pitch       palm.direction atan2(d.y, −d.z)   degrees        ±60
  yaw         palm.direction atan2(d.x, −d.z)   degrees        ±45
  grab        grab_strength                     0–1            0–1
  pinch       pinch_strength                    0–1            0–1
  grab_angle  grab_angle                        rad → degrees  0–180
  pinch_mm    pinch_distance                    mm             15–100
  pinch_index thumb tip → index tip  ÷ palm.width  ×palm        0.15–1.00
  pinch_middle  … middle                                       0.15–1.05
  pinch_ring    … ring                                         0.20–1.10
  pinch_pinky   … pinky                                        0.25–1.15

The four pinches are ratios, not distances: dividing by palm width makes
one threshold fit every hand. Each also drives a switch (`Gate`) — eight
more signals, on top of the analog axes: a Schmitt trigger so they don't
chatter where the fingers hover, then a debounce so one noisy frame
can't flip them. The switches work whether or not the ratios were chosen
as dofs, and go out as the last eight hand lanes and as note on/off
(`[hands] pinch_note`). Thumb-index is by far the most reliable; ring
and pinky are weaker — occlusion when the palm turns away, and the two
fingers don't move independently, so a thumb-ring pinch tends to bring
the pinky with it.

Roll and yaw are anatomical, not room-relative: thumb-up roll and
fingers-outward yaw read as increasing on both hands, so the hands are
mirror images. x stays room-relative (left → right on both hands).

Where things live: every per-axis setting and the few global ones are
registry params in the ``hands`` group (`register`), so the library's
preset strip saves and loads a *setup*, a project carries it, and an
APC40 knob can be learned onto, say, the smoothing. The calibrated
ranges belong to the box, not to a setup: they live in
``<home>/hands.json`` (the HANDS page's calibrate button, or
tools/hands_probe.py --calibrate). Rig choices — tracking mode, which
features, the MIDI port — are the ``[hands]`` section of config.toml.

The tracking service calls back on its own thread; `LeapSource` keeps
the newest frame under a lock and the render loop reads it once per
frame (`HandsIO.poll`), so nothing from the SDK thread touches the
registry.
"""

from __future__ import annotations

import json
import math
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import mido

from .signal import (
    FULL,
    HYST_14,
    OUTS,
    RESTS,
    Follower,
    describe,
    encode,
    quantize,
    shape,
    valid,
)

SIDES = ("left", "right")
LEARN_MOVE = 0.25        # y an axis must travel to win a learn
STALE_S = 0.25           # no tracking frame for this long: no hands
CAL_FILE = "hands.json"
CAL_SCHEMA = "hyperspace.hands/1"
CAL_MIN_SAMPLES = 30
GROUP = "hands"

# feature → (unit, default lo, default hi); x has a per-hand default below
FEATURES: dict[str, tuple[str, float, float]] = {
    "x": ("mm", -120.0, 120.0),
    "y": ("mm", 100.0, 350.0),
    "z": ("mm", -100.0, 100.0),
    "roll": ("deg", -90.0, 90.0),
    "pitch": ("deg", -60.0, 60.0),
    "yaw": ("deg", -45.0, 45.0),
    "grab": ("0-1", 0.0, 1.0),
    "pinch": ("0-1", 0.0, 1.0),
    "grab_angle": ("deg", 0.0, 180.0),
    "pinch_mm": ("mm", 15.0, 100.0),
    # thumb tip to each finger tip, over palm width: hand-size independent
    "pinch_index": ("×palm", 0.15, 1.00),
    "pinch_middle": ("×palm", 0.15, 1.05),
    "pinch_ring": ("×palm", 0.20, 1.10),
    "pinch_pinky": ("×palm", 0.25, 1.15),
}
# the four thumb-to-finger pinches, in the order they are reported
PINCHES = ("index", "middle", "ring", "pinky")
PALM_W = 85.0            # mm, the fallback when the SDK reports no palm width
# each hand works its own side of the camera
X_RANGE = {"left": (-220.0, 20.0), "right": (-20.0, 220.0)}
# shaped about their middle: a neutral hand reads 0.5
BIPOLAR = {"x", "z", "roll", "pitch", "yaw"}

DEFAULT_DOFS = ["x", "y", "z", "roll", "pitch", "yaw"]

# [hands] in config.toml — the rig, not the performance
DEFAULTS: dict = {
    "enabled": False,
    "mode": "desktop",       # desktop | screentop | hmd — where the camera looks from
    "dofs": DEFAULT_DOFS,    # per hand, in axis order
    "out": "Hyperspace Hands",   # MIDI out for a DAW: an existing port by
                                 # substring, else a virtual port ("" = none)
    "channel": 16,           # 1-based: the default channel every axis starts on
    "cc": 102,               # left hand cc … cc+n−1, right hand cc+n … cc+2n−1
    "presence": True,        # note on/off to the DAW as each hand enters / leaves
    "note": 120,             # left hand's presence note; right is note+1
    "min_confidence": 0.1,
    "calibration": CAL_FILE,
    "pinch_gates": True,     # the eight thumb-to-finger switches
    "pinch_notes": True,     # each one as a note on/off to the DAW
    "pinch_note": 100,       # left index…pinky = note…note+3, right = note+4…note+7
}
# config mode → leap.TrackingMode member
TRACKING_MODES = {"desktop": "Desktop", "screentop": "ScreenTop", "hmd": "HMD"}


# ------------------------------------------------------------- features

def _side(hand) -> str:
    t = getattr(hand.type, "name", None) or str(hand.type)
    return "left" if t.rsplit(".", 1)[-1].lower() == "left" else "right"


def _tip(digit):
    """The fingertip: the far end of the distal bone."""
    return digit.distal.next_joint


def pinches(hand) -> dict[str, float]:
    """Thumb tip to each finger tip, divided by palm width.

    A ratio, not a distance, so one threshold fits every hand: a big hand
    and a small hand touching read alike. Empty when the bindings gave no
    digits (the palm-only namespaces the tests build).
    """
    thumb = getattr(hand, "thumb", None)
    if thumb is None:
        return {}
    t = _tip(thumb)
    scale = float(getattr(hand.palm, "width", 0.0) or 0.0) or PALM_W
    out = {}
    for f in PINCHES:
        d = _tip(getattr(hand, f))
        out[f"pinch_{f}"] = math.dist((t.x, t.y, t.z), (d.x, d.y, d.z)) / scale
    return out


def features(hand) -> dict[str, float]:
    """Every feature of one ``leap`` Hand in its native unit (see the table).

    Duck-typed on the bindings' attribute names, so tests pass plain
    namespaces. Rotations are already mirrored for the left hand.
    """
    palm = hand.palm
    p, n, d = palm.position, palm.normal, palm.direction
    roll = math.degrees(math.atan2(n.x, -n.y))
    pitch = math.degrees(math.atan2(d.y, -d.z))
    yaw = math.degrees(math.atan2(d.x, -d.z))
    if _side(hand) == "right":
        roll = -roll         # thumb-up is −roll on the right hand
    else:
        yaw = -yaw           # fingers-outward is −x on the left hand
    return {
        "x": float(p.x), "y": float(p.y), "z": float(p.z),
        "roll": roll, "pitch": pitch, "yaw": yaw,
        "grab": float(hand.grab_strength), "pinch": float(hand.pinch_strength),
        "grab_angle": math.degrees(float(hand.grab_angle)),
        "pinch_mm": float(hand.pinch_distance),
        **pinches(hand),
    }


class OneEuro:
    """The One Euro filter (Casiez et al. 2012) over a scalar: a low-pass
    whose cutoff rises with speed — a still hand does not shimmer, a moving
    one does not lag. `reset` forgets the history."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 4.0, d_cutoff: float = 1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.reset()

    def reset(self) -> None:
        self.x: float | None = None
        self.dx = 0.0
        self.t = 0.0

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: float, t: float) -> float:
        if self.x is None:
            self.x, self.t = x, t
            return x
        dt = t - self.t
        if dt <= 0.0:
            return self.x
        self.t = t
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx += a_d * ((x - self.x) / dt - self.dx)
        a = self._alpha(self.min_cutoff + self.beta * abs(self.dx), dt)
        self.x += a * (x - self.x)
        return self.x


# ------------------------------------------------------------- settings

class Gate:
    """A pinch as a switch: Schmitt trigger, then a debounce.

    Two thresholds, not one — a bare ``d < k`` chatters where the fingers
    hover at k. It closes under `close`, and only lets go above `open_`,
    which is deliberately the wider gap. A candidate edge then has to hold
    for `hold` seconds before it counts, so a single noisy frame cannot
    flip the switch.
    """

    __slots__ = ("_edge", "_since", "on")

    def __init__(self) -> None:
        self.on = False
        self._edge: bool | None = None    # the flip being timed, if any
        self._since = 0.0

    def reset(self) -> None:
        """The hand left: drop the switch and forget any pending edge."""
        self.on = False
        self._edge = None

    def step(self, d: float | None, t: float, *, close: float, open_: float,
             hold: float) -> bool:
        if d is None or math.isnan(d):
            return self.on
        want = d < close if not self.on else not d > max(open_, close)
        if want == self.on:
            self._edge = None
        else:
            if self._edge != want:
                self._edge, self._since = want, t
            if t - self._since >= hold:
                self.on = want
                self._edge = None
        return self.on


@dataclass
class AxisSettings:
    """What a setup says about one axis — every field is a registry param."""

    side: str
    feature: str
    invert: bool = False
    bipolar: bool = True
    deadzone: float = 0.0       # bipolar: half-width about the middle; else at the bottom
    curve: float = 0.0          # −1 … 1, the exponent 4^c
    attack: float = 0.0         # s, rising
    decay: float = 0.0          # s, falling
    rest: str = "return"        # "hold" | "return" when the hand leaves
    rest_value: float = 0.5
    return_s: float = 0.5       # spring settle time back to rest
    bounce: float = 0.15        # 0 critically damped … 1 rings
    out: str = "cc"             # OUTS
    channel: int = 16           # 1-based
    number: int = 102

    @property
    def name(self) -> str:
        return f"{self.side}.{self.feature}"

    @property
    def label(self) -> str:
        return f"{self.side[0].upper()} {self.feature}"


@dataclass
class HandSettings:
    """A whole setup: the axes plus the global feel."""

    axes: list[AxisSettings] = field(default_factory=list)
    smooth: float = 1.0          # One Euro min cutoff, Hz — lower is steadier at rest
    response: float = 4.0        # One Euro beta — higher follows fast moves closer
    catch_s: float = 0.15        # glide onto a returning hand
    rate: int = 200              # MIDI messages a second per axis at most (0 = no cap)
    steady: float = 0.35         # 7-bit hysteresis, in steps past the half-step
    pinch_close: float = 0.34    # ×palm: tips closer than this close the switch
    pinch_open: float = 0.46     # ×palm: it only lets go past this — the wider gap
    pinch_hold: float = 0.04     # s an edge must hold before it counts

    @classmethod
    def from_config(cls, cfg: dict | None = None) -> HandSettings:
        cfg = {**DEFAULTS, **(cfg or {})}
        dofs = list(cfg["dofs"])
        bad = [d for d in dofs if d not in FEATURES]
        if bad:
            raise ValueError(f"unknown hand dofs {bad}; known: {', '.join(FEATURES)}")
        cc0, ch = int(cfg["cc"]), int(cfg["channel"])
        if cc0 < 0 or cc0 + 2 * len(dofs) - 1 > 127:
            raise ValueError(f"hands: cc {cc0} + {2 * len(dofs)} axes runs past 127")
        if cfg["pinch_gates"] and cfg["pinch_notes"]:
            n0, n1 = int(cfg["pinch_note"]), int(cfg["pinch_note"]) + 2 * len(PINCHES) - 1
            note = int(cfg["note"])
            if n0 < 0 or n1 > 127:
                raise ValueError(f"hands: pinch_note {n0} + 8 switches runs past 127")
            if cfg["presence"] and n0 <= note + 1 and note <= n1:
                raise ValueError(f"hands: pinch notes {n0}–{n1} collide with the "
                                 f"presence notes {note}–{note + 1}")
        axes = []
        for s, side in enumerate(SIDES):
            for k, feat in enumerate(dofs):
                bi = feat in BIPOLAR
                axes.append(AxisSettings(side, feat, bipolar=bi, deadzone=0.04 if bi else 0.0,
                                         rest_value=0.5 if bi else 0.0, channel=ch,
                                         number=cc0 + s * len(dofs) + k))
        return cls(axes)


def register(reg, settings: HandSettings) -> None:
    """Every setting as a param in the ``hands`` group — what a setup
    preset saves. Not modulatable: a lane shouldn't bend the instrument."""
    if f"{GROUP}.smooth" in reg:
        return

    def cont(pid, label, obj, attr, lo, hi, *, tip, fmt=None, integer=False, log=False):
        reg.continuous(pid, label, lambda: getattr(obj, attr),
                       lambda v: setattr(obj, attr, int(v) if integer else float(v)),
                       lo=lo, hi=hi, integer=integer, log=log, fmt=fmt, group=GROUP,
                       tip=tip, modulatable=False)

    def choice(pid, label, obj, attr, names, tip):
        reg.enum(pid, label, lambda: names.index(getattr(obj, attr)),
                 lambda i: setattr(obj, attr, names[int(i)]), names, group=GROUP, tip=tip,
                 modulatable=False)

    def flag(pid, label, obj, attr, tip):
        reg.toggle(pid, label, lambda: getattr(obj, attr),
                   lambda v: setattr(obj, attr, bool(v)), group=GROUP, tip=tip,
                   modulatable=False)

    secs = lambda v: f"{v * 1000:.0f} ms" if v < 1 else f"{v:.2f} s"
    g = settings
    cont(f"{GROUP}.smooth", "Steadiness", g, "smooth", 0.1, 10.0, log=True,
         fmt=lambda v: f"{v:.2f} Hz",
         tip="Smoothing at rest (One Euro cutoff). Lower: a held hand is stiller; "
             "higher: less lag on slow moves.")
    cont(f"{GROUP}.response", "Response", g, "response", 0.0, 20.0,
         tip="How much fast moves open the smoothing up. Higher: quick gestures "
             "track closer; lower: steadier but laggier.")
    cont(f"{GROUP}.catch", "Catch", g, "catch_s", 0.0, 1.0, fmt=secs,
         tip="When a hand comes back, glide onto it over this long instead of jumping.")
    cont(f"{GROUP}.rate", "MIDI rate", g, "rate", 0, 1000, integer=True,
         fmt=lambda v: "no cap" if v <= 0 else f"{int(v)}/s",
         tip="Most messages a second per axis to the DAW port (0: no cap). "
             "The last value always gets through.")
    cont(f"{GROUP}.steady", "Hysteresis", g, "steady", 0.0, 2.0,
         tip="How far past a 7-bit step a value must go before it's sent — "
             "stops a still hand flickering between two values.")
    ratio = lambda v: f"{v:.2f}×palm"
    cont(f"{GROUP}.pinch_close", "Pinch close", g, "pinch_close", 0.1, 1.0, fmt=ratio,
         tip="How close thumb and fingertip must come to close a pinch switch, "
             "as a fraction of palm width — so it fits any hand.")
    cont(f"{GROUP}.pinch_open", "Pinch release", g, "pinch_open", 0.1, 1.5, fmt=ratio,
         tip="How far they must part again to let go. Keep it above Pinch close: "
             "the gap between the two is what stops the switch chattering.")
    cont(f"{GROUP}.pinch_hold", "Pinch debounce", g, "pinch_hold", 0.0, 0.5, fmt=secs,
         tip="How long a pinch must hold before it counts, so one noisy frame "
             "can't flip the switch.")
    for a in g.axes:
        p = f"{GROUP}.{a.name}"
        flag(f"{p}.invert", "Invert", a, "invert", "Flip the axis end for end.")
        flag(f"{p}.bipolar", "Centred", a, "bipolar",
             "Shape about the middle (a tilt, a sideways move): the dead zone sits "
             "at neutral. Off: at the bottom (height).")
        cont(f"{p}.deadzone", "Dead zone", a, "deadzone", 0.0, 0.5,
             tip="A flat band where the output doesn't move — at neutral when "
                 "centred, else at the bottom. The rest of the throw still "
                 "reaches both ends.")
        cont(f"{p}.curve", "Curve", a, "curve", -1.0, 1.0,
             tip="+: fine near neutral, fast at the ends. −: the reverse. 0: linear.")
        cont(f"{p}.attack", "Attack", a, "attack", 0.0, 2.0, fmt=secs,
             tip="Time constant while the output rises.")
        cont(f"{p}.decay", "Decay", a, "decay", 0.0, 2.0, fmt=secs,
             tip="Time constant while the output falls.")
        choice(f"{p}.rest", "On exit", a, "rest", RESTS,
               "When the hand leaves: hold the last value, or spring back to rest.")
        cont(f"{p}.rest_value", "Rest", a, "rest_value", 0.0, 1.0,
             tip="Where the output returns to when the hand leaves.")
        cont(f"{p}.return", "Return", a, "return_s", 0.05, 3.0, fmt=secs,
             tip="How long the spring takes to settle at rest.")
        cont(f"{p}.bounce", "Bounce", a, "bounce", 0.0, 1.0,
             tip="0: glides home. Higher: overshoots and rings like a spring.")
        choice(f"{p}.out", "MIDI out", a, "out", OUTS,
               "What goes to the DAW port: 7-bit CC, 14-bit CC (MSB n, LSB n+32), "
               "pitch bend or channel pressure (one axis per channel), or nothing.")
        cont(f"{p}.channel", "Channel", a, "channel", 1, 16, integer=True,
             tip="MIDI channel, 1–16.")
        cont(f"{p}.number", "CC", a, "number", 0, 127, integer=True,
             tip="CC number (0–31 for 14-bit).")


SHAPE_KEYS = ("invert", "bipolar", "deadzone", "curve", "attack", "decay", "rest",
              "rest_value", "return_s", "bounce")


def mirror(settings: HandSettings, name: str) -> AxisSettings | None:
    """Copy an axis's feel (shape, dynamics, rest — not its MIDI out) to
    the same axis on the other hand, so both hands answer alike."""
    src = next((a for a in settings.axes if a.name == name), None)
    if src is None:
        return None
    other = "right" if src.side == "left" else "left"
    dst = next((a for a in settings.axes if a.side == other and a.feature == src.feature),
               None)
    if dst is not None:
        for k in SHAPE_KEYS:
            setattr(dst, k, getattr(src, k))
    return dst


def conflicts(settings: HandSettings) -> dict[str, str]:
    """axis name → why its MIDI output is a problem, for the page."""
    out: dict[str, str] = {}
    seen: dict[tuple, str] = {}
    for a in settings.axes:
        why = valid(a.out, a.number)
        if why:
            out[a.name] = why
            continue
        if a.out == "off":
            continue
        if a.out in ("pitch", "pressure"):
            keys = [(a.out, a.channel)]
        elif a.out == "cc14":
            keys = [("cc", a.channel, a.number), ("cc", a.channel, a.number + 32)]
        else:
            keys = [("cc", a.channel, a.number)]
        for k in keys:
            if k in seen:
                out[a.name] = f"shares its output with {seen[k]}"
            else:
                seen[k] = a.name
    return out


# ----------------------------------------------------------- calibration

def default_range(side: str, feature: str) -> tuple[float, float]:
    return X_RANGE[side] if feature == "x" else FEATURES[feature][1:]


def load_calibration(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    try:
        return dict(json.loads(path.read_text()).get("axes", {}))
    except (OSError, ValueError, AttributeError) as e:
        print(f"hands: {path}: {e}", file=sys.stderr)
        return {}


def save_calibration(path: Path, ranges: dict[str, tuple[float, float]]) -> None:
    data = {"schema": CAL_SCHEMA,
            "axes": {k: {"lo": round(lo, 3), "hi": round(hi, 3)}
                     for k, (lo, hi) in ranges.items()}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n")


# --------------------------------------------------------------- source

class LeapSource:
    """The Ultraleap tracking service through the ``leap`` bindings.

    Connects on a thread (the service may be slow or absent; the show
    must not wait), sets the tracking mode, and keeps the newest frame.
    `latest()` is what the render loop reads.
    """

    def __init__(self, mode: str = "desktop", clock=time.monotonic):
        import leap  # optional: only here, only when [hands] is enabled

        self.clock = clock
        self.status = "connecting"
        self._lock = threading.Lock()
        self._hands: dict[str, tuple[dict, float]] = {}
        self._seq = 0
        self._t = -1.0
        src = self

        class _Listener(leap.Listener):
            def on_connection_event(self, event):
                src.status = "connected"

            def on_connection_lost_event(self, event):
                src.status = "service lost"

            def on_device_event(self, event):
                src.status = "tracking"

            def on_device_lost_event(self, event):
                src.status = "no camera"

            def on_tracking_event(self, event):
                src._frame(event.hands)

            def on_error(self, error):
                # the SDK's poll thread reports anything that raised in a
                # callback here — _frame included — and otherwise drops it,
                # so a hand that never shows would have no reason given
                src.status = f"error: {type(error).__name__}: {error}"[:120]

        self.conn = leap.Connection()
        self.conn.add_listener(_Listener())
        tmode = getattr(leap.TrackingMode, TRACKING_MODES.get(mode.lower(), "Desktop"))

        def connect():
            try:
                self.conn.connect(auto_poll=True)
                self.conn.set_tracking_mode(tmode)
            except Exception as e:  # noqa: BLE001 — service missing / refused
                self.status = f"{type(e).__name__}: {e}"[:120]

        threading.Thread(target=connect, name="leap-connect", daemon=True).start()

    def _frame(self, hands) -> None:
        """SDK thread: one tracking frame. Two hands of one side (rare,
        briefly, on a crossover) keep the more confident."""
        out: dict[str, tuple[dict, float]] = {}
        for h in hands:
            side, conf = _side(h), float(h.confidence)
            if side not in out or conf > out[side][1]:
                out[side] = (features(h), conf)
        with self._lock:
            self._hands, self._seq, self._t = out, self._seq + 1, self.clock()

    def latest(self) -> tuple[int, float, dict[str, tuple[dict, float]]]:
        """(frame seq, receipt time, side → (features, confidence))."""
        with self._lock:
            seq, t, hands = self._seq, self._t, self._hands
        if self.clock() - t > STALE_S:
            hands = {}
        return seq, t, hands

    @property
    def on(self) -> bool:
        return self.status in ("connected", "tracking")

    def close(self) -> None:
        try:
            self.conn.disconnect()
        except Exception:  # noqa: BLE001, S110
            pass


# -------------------------------------------------------------- adapter

@dataclass
class AxisState:
    """One axis at run time — never saved."""

    lo: float
    hi: float
    filt: OneEuro = field(default_factory=OneEuro, repr=False)
    follow: Follower = field(default_factory=Follower, repr=False)
    raw: float | None = None      # native value, last frame the hand was seen
    u: float | None = None        # normalized + smoothed, before shaping
    target: float | None = None   # shaped; None while the hand is away
    q: int | None = None          # last value sent to the DAW
    next_ok: float = 0.0          # rate limit: when the next send may go

    @property
    def y(self) -> float | None:
        return self.follow.y

    def norm(self, v: float) -> float:
        span = self.hi - self.lo
        return (v - self.lo) / span if span else 0.0


class HandsIO:
    """Polled once per render frame: source → axes → hand lanes, DAW MIDI.

    `source` is anything with ``latest()`` (tests pass a fake); `out` an
    object with ``send()``, else the port `cfg["out"]` names is opened.
    """

    def __init__(self, settings: HandSettings, cfg: dict | None = None, *, source=None,
                 out=None, cal_path: Path | None = None, clock=time.monotonic):
        self.settings = settings
        self.cfg = {**DEFAULTS, **(cfg or {})}
        self.cal_path = cal_path
        self.clock = clock
        cal = load_calibration(cal_path)
        self.state = []
        for a in settings.axes:
            lo, hi = default_range(a.side, a.feature)
            c = cal.get(a.name, {})
            self.state.append(AxisState(float(c.get("lo", lo)), float(c.get("hi", hi))))
        self.min_conf = float(self.cfg["min_confidence"])
        self.source = source if source is not None else LeapSource(self.cfg["mode"], clock)
        self.out = out if out is not None else _open_out(self.cfg.get("out") or "")
        self.out_name = getattr(self.out, "name", "") if self.out is not None else ""
        self.present = {s: False for s in SIDES}
        # the eight pinch switches, whether or not the ratios are axes
        self.gates = {s: {f: Gate() for f in PINCHES} for s in SIDES}
        self.frame: dict[str, dict | None] = {s: None for s in SIDES}  # native features
        self.solo: int | None = None      # axis index: only it goes to the DAW
        self.last = ""                    # the last MIDI sent, for the status line
        self.error = ""
        self._seq = -1
        self._learn_base: list[float | None] | None = None
        # calibration sweep in progress: axis name → raw samples
        self._cal: dict[str, list[float]] | None = None
        self._cal_until = 0.0
        self.cal_note = ""

    @property
    def axes(self) -> list[AxisSettings]:
        return self.settings.axes

    @property
    def lane_names(self) -> list[str]:
        return ([a.label for a in self.axes]
                + [f"{s[0].upper()} in" for s in SIDES]
                + [f"{s[0].upper()} {f[:3]}" for s in SIDES for f in PINCHES])

    @property
    def status(self) -> str:
        return getattr(self.source, "status", "")

    def axis(self, name: str) -> int:
        """Index of "left.pitch" etc.; ValueError when there is none."""
        return [a.name for a in self.axes].index(name)

    def gate_lane(self, side: str, finger: str) -> int:
        """Lane index of one pinch switch — what a `when` address names."""
        return (len(self.axes) + len(SIDES)
                + SIDES.index(side) * len(PINCHES) + PINCHES.index(finger))

    def held_gate(self, side: str | None = None) -> str | None:
        """The pinch being held right now as a source address, or None.

        This is what lets a learn started while pinching wear the pinch:
        the hand that learned the axis gets asked first, so a left-hand
        move gated by a left-hand thumb is the natural reading.
        """
        order = ([side] + [s for s in SIDES if s != side]) if side else list(SIDES)
        for s in order:
            for f in PINCHES:
                if self.gates[s][f].on:
                    return f"hand:{self.gate_lane(s, f)}"
        return None

    def lanes(self) -> list[float]:
        """Each axis's output y (NaN before its hand was ever seen), then
        one presence lane per hand (1 in view, 0 not), then the eight
        pinch switches. The switches come last so that a saved binding to
        ``hand:<i>`` keeps meaning the axis it always did."""
        ys = [math.nan if st.y is None else st.y for st in self.state]
        return (ys
                + [1.0 if self.present[s] else 0.0 for s in SIDES]
                + [1.0 if self.gates[s][f].on else 0.0 for s in SIDES for f in PINCHES])

    # ---- per frame ----

    def poll(self, dt: float, midi=None, router=None) -> list[mido.Message]:
        """One render frame. `midi` is the MidiIO whose learn state a hand
        can complete; `router` the routing.Router fed the ``hand`` lanes.
        Returns what went to the DAW port (for tests and the probe)."""
        g = self.settings
        seq, t, hands = self.source.latest()
        now = self.clock()
        fresh = seq != self._seq
        self._seq = seq
        msgs: list[mido.Message] = []
        for s, side in enumerate(SIDES):
            h = hands.get(side)
            here = h is not None and h[1] >= self.min_conf
            self.frame[side] = h[0] if here else None
            if here != self.present[side]:
                self.present[side] = here
                if self.cfg["presence"] and self.solo is None:
                    msgs.append(mido.Message(
                        "note_on" if here else "note_off",
                        channel=int(self.cfg["channel"]) - 1,
                        note=int(self.cfg["note"]) + s, velocity=127 if here else 0))
            msgs += self._pinches(side, s, here, t)
        for i, (a, st) in enumerate(zip(self.axes, self.state)):
            h = hands.get(a.side) if self.present[a.side] else None
            if h is None:
                if st.target is not None:
                    st.filt.reset()       # a returning hand starts fresh
                st.target = None
            elif fresh or st.target is None:
                st.raw = h[0][a.feature]
                st.filt.min_cutoff, st.filt.beta = g.smooth, g.response
                u = st.norm(st.raw)
                u = min(1.0, max(0.0, st.filt(1.0 - u if a.invert else u, t)))
                st.u = u
                st.target = shape(u, bipolar=a.bipolar, deadzone=a.deadzone, c=a.curve)
                if self._cal is not None:
                    self._cal[a.name].append(st.raw)
            y = st.follow.step(dt, st.target, attack=a.attack, decay=a.decay,
                               catch_s=g.catch_s, rest=a.rest, rest_value=a.rest_value,
                               return_s=a.return_s, bounce=a.bounce)
            if y is None or a.out == "off" or (self.solo is not None and self.solo != i):
                continue
            if valid(a.out, a.number) or now < st.next_ok:
                continue
            full = FULL[a.out]
            q = quantize(y, st.q, g.steady if full == 127 else HYST_14, full)
            if q != st.q:
                st.q = q
                st.next_ok = now + (1.0 / g.rate if g.rate > 0 else 0.0)
                msgs += encode(a.out, a.channel - 1, a.number, q)
        self._finish_calibration(now)
        if self.out is not None:
            for m in msgs:
                self._send(m)
        if msgs:
            self.last = describe(msgs[-1])
        if router is not None:
            live = getattr(self.source, "on", True)
            router.feed("hand", self.lanes() if live else None)
            router.labels["hand"] = self.lane_names
            # the switches, so the routing UI can offer them without
            # knowing anything about hands
            router.gates["hand"] = [(self.gate_lane(s, f), f"{s[0].upper()} {f[:3]}")
                                    for s in SIDES for f in PINCHES]
            # where each lane idles — the axis's own configured rest, so a
            # push row centred on it pushes nothing from an absent hand
            # whatever the setup says rest is; presence and pinches 0
            router.rests["hand"] = ([float(a.rest_value) for a in self.axes]
                                    + [0.0] * (len(SIDES) + len(SIDES) * len(PINCHES)))
        if midi is not None:
            self._learn(midi)
        return msgs

    def _pinches(self, side: str, s: int, here: bool, t: float) -> list[mido.Message]:
        """Step one hand's four pinch switches; note on/off on each edge.

        The ratios are read straight off the frame rather than through an
        axis, so the switches work whether or not they were chosen as
        dofs. A hand that leaves drops its switches (and sends the note
        off), so nothing is left hanging on in the DAW.
        """
        g, cfg = self.settings, self.cfg
        if not cfg["pinch_gates"]:
            return []
        feats = self.frame[side] or {}
        msgs: list[mido.Message] = []
        for k, f in enumerate(PINCHES):
            gate = self.gates[side][f]
            was = gate.on
            if not here:
                gate.reset()
            else:
                gate.step(feats.get(f"pinch_{f}"), t, close=g.pinch_close,
                          open_=g.pinch_open, hold=g.pinch_hold)
            if gate.on != was and cfg["pinch_notes"] and self.solo is None:
                msgs.append(mido.Message(
                    "note_on" if gate.on else "note_off",
                    channel=int(cfg["channel"]) - 1,
                    note=int(cfg["pinch_note"]) + s * len(PINCHES) + k,
                    velocity=127 if gate.on else 0))
        return msgs

    def _learn(self, midi) -> None:
        """While the MIDI adapter is learning a param, the axis that has
        moved furthest (≥ LEARN_MOVE) since the learn began takes it —
        a hand moves all its axes at once, so first-to-move won't do."""
        if getattr(midi, "learning", None) is None:
            self._learn_base = None
            return
        ys = [st.y for st in self.state]
        if self._learn_base is None:
            self._learn_base = ys
            return
        moved = [abs(y - b) if y is not None and b is not None else 0.0
                 for y, b in zip(ys, self._learn_base)]
        # an axis first seen after the learn began gets its base now
        self._learn_base = [b if b is not None else y for y, b in zip(ys, self._learn_base)]
        best = max(range(len(moved)), key=moved.__getitem__)
        if moved[best] >= LEARN_MOVE:
            self._learn_base = None
            # pinched while learning: the pinch becomes the row's gate, so
            # the same movement means this only while the thumb agrees
            gate = self.held_gate(self.axes[best].side)
            if gate is None:
                midi.learn_source(f"hand:{best}")
            else:
                midi.learn_source(f"hand:{best}", when=gate)

    def _send(self, m: mido.Message) -> None:
        try:
            self.out.send(m)
        except Exception as e:  # noqa: BLE001 — port yanked mid-frame
            self.error = f"send: {e}"[:120]
            self.out = None

    # ---- calibration ----

    @property
    def calibrating(self) -> float:
        """Seconds left in a sweep, 0 when none is running."""
        return max(0.0, self._cal_until - self.clock()) if self._cal is not None else 0.0

    def start_calibration(self, seconds: float = 20.0) -> None:
        self._cal = {a.name: [] for a in self.axes}
        self._cal_until = self.clock() + seconds
        self.cal_note = "sweep every axis end to end"

    def cancel_calibration(self) -> None:
        self._cal = None
        self.cal_note = "calibration cancelled"

    def _finish_calibration(self, now: float) -> None:
        if self._cal is None or now < self._cal_until:
            return
        seen, self._cal = self._cal, None
        done = 0
        for a, st in zip(self.axes, self.state):
            v = sorted(seen[a.name])
            if len(v) < CAL_MIN_SAMPLES:
                continue
            lo, hi = v[int(0.02 * (len(v) - 1))], v[int(0.98 * (len(v) - 1))]
            if hi - lo > 1e-6:
                st.lo, st.hi = lo, hi
                done += 1
        missed = len(self.axes) - done
        self.cal_note = f"calibrated {done} axes" + (f", {missed} not reached" if missed else "")
        self.save_ranges()

    def reset_ranges(self) -> None:
        for a, st in zip(self.axes, self.state):
            st.lo, st.hi = default_range(a.side, a.feature)
        self.save_ranges()
        self.cal_note = "ranges back to the defaults"

    def save_ranges(self) -> None:
        if self.cal_path is None:
            return
        try:
            save_calibration(self.cal_path, {a.name: (st.lo, st.hi)
                                             for a, st in zip(self.axes, self.state)})
        except OSError as e:
            self.cal_note = f"save: {e}"[:120]

    def close(self) -> None:
        if self.out is not None and hasattr(self.out, "close"):
            try:
                self.out.close()
            except Exception:  # noqa: BLE001, S110
                pass
        if hasattr(self.source, "close"):
            self.source.close()


def _open_out(name: str):
    """An existing port matching `name`, else a virtual one called `name`."""
    if not name:
        return None
    try:
        hit = next((n for n in mido.get_output_names() if name.lower() in n.lower()), None)
        return mido.open_output(hit) if hit else mido.open_output(name, virtual=True)
    except Exception as e:  # noqa: BLE001 — no backend / virtual ports unsupported
        print(f"hands: out {name!r}: {e}", file=sys.stderr)
        return None
