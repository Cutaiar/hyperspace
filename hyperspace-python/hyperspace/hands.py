"""Ultraleap hands → MIDI: two tracked hands as twelve performance axes.

The hands are the performing surface; the APC40 stays on presets and
master controls. Each hand gives a set of degrees of freedom (six by
default, the palm's rigid-body pose), every one smoothed, normalized
against a calibrated range and quantized onto the 0–127 MIDI scale. The
result goes three ways, all optional:

  * into the MIDI adapter (midi.py ``MidiIO.inject``) as control changes
    on their own channel, so right-click → Learn and bindings.json treat
    a hand axis exactly like an APC40 knob;
  * out of a MIDI port (a virtual one by default) for a DAW;
  * into the routing table as ``hand:<i>`` lanes — the same axis at full
    float precision, for ``mod`` / ``replace`` routes where 7-bit steps
    would show on a slow visual param.

What Ultraleap reports (LeapC via the ``leap`` Python bindings; units are
the SDK's, coordinates right-handed with the origin at the camera, +y
away from it, +z toward the performer in desktop mode):

  feature     source                           native unit   default range
  x y z       palm.position                    mm            calibrated per hand
  roll        palm.normal   atan2(n.x, −n.y)   degrees       ±90
  pitch       palm.direction atan2(d.y, −d.z)  degrees       ±60
  yaw         palm.direction atan2(d.x, −d.z)  degrees       ±45
  grab        grab_strength                    0–1           0–1
  pinch       pinch_strength                   0–1           0–1
  grab_angle  grab_angle                       rad → degrees 0–180
  pinch_mm    pinch_distance                   mm            15–100

Roll and yaw are anatomical, not room-relative: thumb-up roll and
fingers-outward yaw read as increasing on both hands, so the hands are
mirror images and a symmetric mapping needs no per-hand sign. x stays
room-relative (left → right increases on both hands).

Per axis, per tracking frame: the raw value is normalized to
u = (v − lo) / (hi − lo) (flipped when `invert`), smoothed by a One Euro
filter (Casiez et al. 2012 — a low-pass whose cutoff rises with speed: a
still hand does not shimmer, a moving one does not lag), clamped to
[0, 1] and quantized to round(u · 127) with hysteresis, so a hand held
on a step boundary does not flicker between two values. A CC is sent
only when that value changes. When a hand leaves, its CCs hold their last
value (nothing is sent), its lanes go dark (the routes let go) and its
presence note goes off; the filter restarts on return so the first value
is where the hand is, not a smear from where it left.

Learn: moving a hand moves all of its axes at once, so while the MIDI
adapter is learning only the one axis that has moved furthest since the
learn began (at least LEARN_MOVE) is forwarded. `solo` does the same by
hand for the out port — a DAW's own learn — and the probe tool.

Calibration (``<home>/hands.json``, written by tools/hands_probe.py
--calibrate): per axis ``lo``, ``hi`` and ``invert``; what is missing
takes the defaults above. Config is the ``[hands]`` section (config.py).

The tracking service calls back on its own thread; `LeapSource` keeps
the newest frame under a lock and the render loop reads it once per
frame (`poll`), so nothing from the SDK thread touches the registry.
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

SIDES = ("left", "right")
MIDI_MAX = 127
LEARN_MOVE = 0.25        # u an axis must travel to win a learn
STALE_S = 0.25           # no tracking frame for this long: no hands
CAL_FILE = "hands.json"
CAL_SCHEMA = "hyperspace.hands/1"

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
}
# each hand works its own side of the camera
X_RANGE = {"left": (-220.0, 20.0), "right": (-20.0, 220.0)}

DEFAULT_DOFS = ["x", "y", "z", "roll", "pitch", "yaw"]

DEFAULTS: dict = {
    "enabled": False,
    "mode": "desktop",       # desktop | screentop | hmd — where the camera looks from
    "dofs": DEFAULT_DOFS,    # per hand, in CC order
    "channel": 15,           # 0-based: MIDI channel 16, clear of the APC40's 0–8
    "cc": 102,               # left hand cc … cc+n−1, right hand cc+n … cc+2n−1
    "presence": True,        # note on/off as each hand enters / leaves
    "note": 120,             # left hand's presence note; right is note+1
    "out": "",               # MIDI out for a DAW: an existing port by substring,
                             # else a virtual port of that name ("" = none)
    "min_confidence": 0.1,
    "min_cutoff": 1.0,       # One Euro: Hz at rest — lower is steadier
    "beta": 4.0,             # One Euro: cutoff gain with speed — higher is snappier
    "hysteresis": 0.35,      # in MIDI steps beyond the half-step
    "calibration": CAL_FILE,
}


# config mode → leap.TrackingMode member
TRACKING_MODES = {"desktop": "Desktop", "screentop": "ScreenTop", "hmd": "HMD"}


# ------------------------------------------------------------- features

def _side(hand) -> str:
    t = getattr(hand.type, "name", None) or str(hand.type)
    return "left" if t.rsplit(".", 1)[-1].lower() == "left" else "right"


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
    }


# --------------------------------------------------------------- filter

class OneEuro:
    """The One Euro filter over a scalar; `reset` forgets the history."""

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


def quantize(u: float, last: int | None, hysteresis: float) -> int:
    """u ∈ [0, 1] → 0–127, holding `last` until u is clearly past the step."""
    v = u * MIDI_MAX
    q = round(v)
    if last is None or q == last:
        return q
    return q if abs(v - last) >= 0.5 + hysteresis else last


# ----------------------------------------------------------------- axes

@dataclass
class Axis:
    side: str
    feature: str
    cc: int
    lo: float
    hi: float
    invert: bool = False
    filt: OneEuro = field(default_factory=OneEuro, repr=False)
    u: float | None = None        # this frame's smoothed reading; None: hand absent
    sent: int | None = None       # last 7-bit value sent
    raw: float | None = None      # last native value, for the probe and calibration

    @property
    def name(self) -> str:
        return f"{self.side}.{self.feature}"

    @property
    def label(self) -> str:
        return f"{self.side[0].upper()} {self.feature}"

    def norm(self, v: float) -> float:
        span = self.hi - self.lo
        u = (v - self.lo) / span if span else 0.0
        return 1.0 - u if self.invert else u


def load_calibration(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    try:
        return dict(json.loads(path.read_text()).get("axes", {}))
    except (OSError, ValueError, AttributeError) as e:
        print(f"hands: {path}: {e}", file=sys.stderr)
        return {}


def save_calibration(path: Path, axes: list[Axis]) -> None:
    data = {"schema": CAL_SCHEMA,
            "axes": {a.name: {"lo": round(a.lo, 3), "hi": round(a.hi, 3), "invert": a.invert}
                     for a in axes}}
    path.write_text(json.dumps(data, indent=1) + "\n")


def make_axes(cfg: dict, cal: dict[str, dict] | None = None) -> list[Axis]:
    """The axes in CC order: left hand's dofs, then the right hand's."""
    dofs = list(cfg.get("dofs", DEFAULT_DOFS))
    bad = [d for d in dofs if d not in FEATURES]
    if bad:
        raise ValueError(f"unknown hand dofs {bad}; known: {', '.join(FEATURES)}")
    cc0 = int(cfg.get("cc", DEFAULTS["cc"]))
    if cc0 < 0 or cc0 + 2 * len(dofs) - 1 > MIDI_MAX:
        raise ValueError(f"hands: cc {cc0} + {2 * len(dofs)} axes runs past 127")
    cal = cal or {}
    axes = []
    for s, side in enumerate(SIDES):
        for k, feat in enumerate(dofs):
            lo, hi = X_RANGE[side] if feat == "x" else FEATURES[feat][1:]
            c = cal.get(f"{side}.{feat}", {})
            axes.append(Axis(side, feat, cc0 + s * len(dofs) + k,
                             float(c.get("lo", lo)), float(c.get("hi", hi)),
                             bool(c.get("invert", False)),
                             OneEuro(float(cfg.get("min_cutoff", DEFAULTS["min_cutoff"])),
                                     float(cfg.get("beta", DEFAULTS["beta"])))))
    return axes


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

class HandsIO:
    """Polled once per frame: source → axes → CCs, presence notes, lanes.

    `source` is anything with ``latest()`` (tests pass a fake); `out` an
    object with ``send()``, else the port `cfg["out"]` names is opened.
    """

    def __init__(self, cfg: dict | None = None, *, source=None, out=None,
                 cal_path: Path | None = None, clock=time.monotonic):
        self.cfg = {**DEFAULTS, **(cfg or {})}
        self.cal_path = cal_path
        self.axes = make_axes(self.cfg, load_calibration(cal_path))
        self.channel = int(self.cfg["channel"])
        self.hyst = float(self.cfg["hysteresis"])
        self.min_conf = float(self.cfg["min_confidence"])
        self.clock = clock
        self.source = source if source is not None else LeapSource(self.cfg["mode"], clock)
        self.out = out if out is not None else _open_out(self.cfg.get("out") or "")
        self.present = {s: False for s in SIDES}
        self.solo: int | None = None      # axis index: only it speaks
        self.last = ""                    # status line
        self._seq = -1
        self._learn_base: list[float | None] | None = None

    @property
    def lane_names(self) -> list[str]:
        return [a.label for a in self.axes]

    @property
    def status(self) -> str:
        return getattr(self.source, "status", "")

    def lanes(self) -> list[float]:
        """Every axis's u, NaN where its hand is absent (its routes let go)."""
        return [math.nan if a.u is None else a.u for a in self.axes]

    # ---- per frame ----

    def poll(self, sink=None, router=None) -> list[mido.Message]:
        """Read the newest frame; send what changed. `sink` is a MidiIO
        (its inject() routes like its own port), `router` a routing.Router
        (fed the ``hand`` lanes). Returns the messages, for tests and the probe."""
        seq, t, hands = self.source.latest()
        msgs: list[mido.Message] = []
        fresh = seq != self._seq
        self._seq = seq
        for s, side in enumerate(SIDES):
            h = hands.get(side)
            here = h is not None and h[1] >= self.min_conf
            if here != self.present[side]:
                self.present[side] = here
                if self.cfg["presence"]:
                    msgs.append(mido.Message(
                        "note_on" if here else "note_off", channel=self.channel,
                        note=int(self.cfg["note"]) + s, velocity=MIDI_MAX if here else 0))
            for i, a in enumerate(self.axes):
                if a.side != side:
                    continue
                if not here:
                    a.u = None
                    a.filt.reset()
                    continue
                if not fresh and a.u is not None:
                    continue              # no new tracking frame: hold
                a.raw = h[0][a.feature]
                a.u = min(1.0, max(0.0, a.filt(a.norm(a.raw), t)))
                q = quantize(a.u, a.sent, self.hyst)
                if q != a.sent:
                    a.sent = q
                    msgs.append(mido.Message("control_change", channel=self.channel,
                                             control=a.cc, value=q))
        msgs = self._gate(msgs, sink)
        for m in msgs:
            if self.out is not None:
                _send(self, m)
            if sink is not None:
                sink.inject(m)
        if router is not None:
            router.feed("hand", self.lanes() if getattr(self.source, "on", True) else None)
            if not hasattr(router, "labels"):   # a Router from before a hot reload
                router.labels = {}
            router.labels["hand"] = self.lane_names
        if msgs:
            m = msgs[-1]
            self.last = (f"cc {m.control} = {m.value}" if m.type == "control_change"
                         else f"{m.type} {m.note}")
        return msgs

    def _gate(self, msgs: list[mido.Message], sink) -> list[mido.Message]:
        """Learn and solo: let one axis through (the solo one, or while the
        sink learns, the one that has moved furthest since the learn began)."""
        learning = sink is not None and getattr(sink, "learning", None) is not None
        if not learning:
            self._learn_base = None
            if self.solo is None:
                return msgs
            cc = self.axes[self.solo].cc
            return [m for m in msgs if m.type == "control_change" and m.control == cc]
        if self._learn_base is None:
            self._learn_base = [a.u for a in self.axes]
        moved = [abs(a.u - b) if a.u is not None and b is not None else 0.0
                 for a, b in zip(self.axes, self._learn_base)]
        # a hand that entered after the learn began has no base: take it now
        self._learn_base = [b if b is not None else a.u
                            for a, b in zip(self.axes, self._learn_base)]
        best = max(range(len(moved)), key=moved.__getitem__)
        if moved[best] < LEARN_MOVE:
            return []
        a = self.axes[best]
        self._learn_base = None
        return [mido.Message("control_change", channel=self.channel,
                             control=a.cc, value=a.sent or 0)]

    # ---- calibration ----

    def axis(self, name: str) -> int:
        """Index of "left.pitch" etc.; ValueError when there is none."""
        return [a.name for a in self.axes].index(name)

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


def _send(io: HandsIO, m: mido.Message) -> None:
    try:
        io.out.send(m)
    except Exception as e:  # noqa: BLE001 — port yanked mid-frame
        io.last = f"send: {e}"[:120]
        io.out = None
