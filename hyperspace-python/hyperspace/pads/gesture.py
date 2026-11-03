"""The touchpad's and the motion sensors' lanes (plan 42).

Two schemes beside a pad's ``axis`` lanes, each lane in [0, 1] like
every routing lane, published by the pad device under the pad's role
(``touch@p2:x`` for a second pad):

``touch:``  ``x``, ``y`` the first finger (up and right high, as the
            sticks); ``down`` while it is on (a gate a row's ``when`` can
            wait on); ``x2``, ``y2``, ``down2`` the second; ``pinch`` the
            two fingers' spread since they landed (rest 0.5, apart high,
            two octaves of spread to the end); ``twist`` how far they
            have turned (rest 0.5, clockwise high, half a turn to the
            end); ``tap`` one frame at 1 when a quick touch lifts (a
            trigger: a route to a trigger param fires it). A finger that
            is not down reads NaN: its routes let go.
``motion:`` ``roll`` (right side down high) and ``pitch`` (the far
            edge up high) from gravity, ±`TILT_DEG` to the ends; ``yaw`` the
            turn about the vertical (to the right high), the gyro integrated and leaking back
            to centre over `YAW_LEAK_S`; ``spin.roll``, ``spin.pitch``,
            ``spin.yaw`` the turning speed, ±`SPIN_DPS` to the ends;
            ``shake`` one frame at 1 on a jolt over `SHAKE_G` (a
            trigger, refractory `SHAKE_GAP_S`); ``energy`` how hard the
            pad is being moved, smoothed, 0 still.

The sensors' axes: x right, y up out of the face, z toward the player
(SDL's convention). Which raw axis is which, and its sign, is the
`AxisMap`; its default held on a real Edge over USB and Bluetooth
(2026-11-02, the probe's tilt test).

A leaf: the standard library only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

NAN = math.nan

TOUCH_LANES = ("x", "y", "down", "x2", "y2", "down2", "pinch", "twist", "tap")
TOUCH_LABELS = ("touch x", "touch y", "touch down", "second touch x", "second touch y",
                "second touch down", "pinch", "twist", "tap")
TOUCH_RESTS = (0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0)
TOUCH_BIPOLAR = frozenset({"x", "y", "x2", "y2", "pinch", "twist"})
TOUCH_TRIGGERS = frozenset({"tap"})
TOUCH_GATES = ("down", "down2")

MOTION_LANES = ("roll", "pitch", "yaw", "spin.roll", "spin.pitch", "spin.yaw", "shake", "energy")
MOTION_LABELS = ("tilt roll", "tilt pitch", "turn yaw", "spin roll", "spin pitch", "spin yaw",
                 "shake", "motion energy")
MOTION_RESTS = (0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0, 0.0)
MOTION_BIPOLAR = frozenset({"roll", "pitch", "yaw", "spin.roll", "spin.pitch", "spin.yaw"})
MOTION_TRIGGERS = frozenset({"shake"})

PINCH_OCTAVES = 2.0       # spread ×4 (or ÷4) reaches the end
TWIST_END = math.pi       # half a turn
TAP_S = 0.25              # a touch shorter than this …
TAP_TRAVEL = 0.06         # … that moved less than this (of the pad's width) is a tap

TILT_DEG = 60.0
SPIN_DPS = 360.0
YAW_DEG = 90.0
YAW_LEAK_S = 3.0          # the yaw lane's way back to centre (a time constant)
SHAKE_G = 1.4             # a jolt this far from 1 g (high-passed) is a shake
SHAKE_GAP_S = 0.18
ENERGY_DPS = 400.0        # spin that reads as full energy …
ENERGY_G = 1.5            # … or this much jolt
ENERGY_S = 0.15           # its smoothing
GRAVITY_S = 0.25          # the accel's low-pass, so shake leaves gravity alone


def _u(v: float, end: float) -> float:
    """−end…+end onto 0…1, centred at 0.5, clamped."""
    return min(1.0, max(0.0, 0.5 + 0.5 * v / end)) if math.isfinite(v) else NAN


def _ease(dt: float, tau: float) -> float:
    return 1.0 - math.exp(-dt / tau) if tau > 0 else 1.0


@dataclass
class Touchpad:
    """The touch lanes from the pad's two contacts, frame by frame.
    `step(touches, dt)` with each contact as (down, id, x, y) in [0, 1]
    (x right, y down — the pad's own way up), then `lanes()`."""

    x: list[float] = field(default_factory=lambda: [NAN, NAN])
    y: list[float] = field(default_factory=lambda: [NAN, NAN])
    pinch: float = NAN
    twist: float = NAN
    tap: float = 0.0
    _start: tuple | None = None          # (spread, angle) when two fingers landed
    _turn: float = 0.0                   # the twist so far (unwrapped)
    _last_angle: float = 0.0
    _first: tuple | None = None          # (id, time held, x0, y0, travelled) of the first finger
    _ids: tuple = (None, None)

    def step(self, touches, dt: float) -> None:
        self.tap = 0.0
        pts = [(bool(d), i, float(x), float(y)) for d, i, x, y in touches][:2]
        while len(pts) < 2:
            pts.append((False, None, 0.0, 0.0))
        for k, (d, _i, x, y) in enumerate(pts):
            self.x[k] = x if d else NAN
            self.y[k] = (1.0 - y) if d else NAN
        self._tap(pts[0], dt)
        both = pts[0][0] and pts[1][0]
        if not both:
            self._start, self.pinch, self.twist = None, NAN, NAN
            self._ids = (pts[0][1] if pts[0][0] else None, None)
            return
        dx, dy = pts[1][2] - pts[0][2], pts[1][3] - pts[0][3]
        spread = max(math.hypot(dx, dy), 1e-3)
        angle = math.atan2(dy, dx)
        ids = (pts[0][1], pts[1][1])
        if self._start is None or ids != self._ids:
            self._start, self._turn, self._last_angle = (spread, angle), 0.0, angle
            self._ids = ids
        d = angle - self._last_angle
        d = (d + math.pi) % (2 * math.pi) - math.pi        # the short way round
        self._turn += d
        self._last_angle = angle
        self.pinch = _u(math.log2(spread / self._start[0]), PINCH_OCTAVES)
        self.twist = _u(self._turn, TWIST_END)

    def _tap(self, p, dt: float) -> None:
        down, i, x, y = p
        f = self._first
        if down:
            if f is None or f[0] != i:
                self._first = (i, 0.0, x, y, 0.0)
            else:
                self._first = (i, f[1] + dt, f[2], f[3], max(f[4], math.hypot(x - f[2], y - f[3])))
            return
        if f is not None and f[1] < TAP_S and f[4] < TAP_TRAVEL:
            self.tap = 1.0
        self._first = None

    def lanes(self) -> list[float]:
        d1 = 0.0 if math.isnan(self.x[0]) else 1.0
        d2 = 0.0 if math.isnan(self.x[1]) else 1.0
        return [self.x[0], self.y[0], d1, self.x[1], self.y[1], d2,
                self.pinch, self.twist, self.tap]


@dataclass(frozen=True)
class AxisMap:
    """Which raw sensor axis is the pad's x (right), y (up out of the
    face) and z (toward the player), each with a sign — for the gyro
    and the accel. The default is SDL's reading of the DualSense; the
    probe's tilt test says whether it holds."""

    accel: tuple[tuple[int, float], ...] = ((0, 1.0), (1, 1.0), (2, 1.0))
    gyro: tuple[tuple[int, float], ...] = ((0, 1.0), (1, 1.0), (2, 1.0))

    @staticmethod
    def pick(raw, spec) -> tuple[float, float, float]:
        return tuple(raw[i] * s for i, s in spec)


def axis_map_of(override, reader) -> AxisMap:
    """The one rule for whose axes a pad's sensors are read through (plan
    46): a map set on the pad (`override`, None when none was) — the
    default map set on purpose counts, so an entry can force the identity
    onto a pad whose built map is wrong; else the reader's own (a Joy-Con's,
    per side); else the default. The app, the pad window and the probe all
    ask here, so they never disagree."""
    if override is not None:
        return override
    own = getattr(reader, "axis_map", None)
    return own if own is not None else AxisMap()


@dataclass
class Motion:
    """The motion lanes from calibrated readings: `step(gyro_dps, accel_g,
    dt)` in the pad's axes (`AxisMap` applied by the caller), then
    `lanes()`. Gravity is the accel low-passed (`GRAVITY_S`); roll and
    pitch are its angle, so they never drift; yaw has no gravity to hold
    it, so it is the gyro integrated, leaking home."""

    gravity: tuple[float, float, float] | None = None
    roll: float = 0.0       # degrees
    pitch: float = 0.0
    yaw: float = 0.0
    spin: tuple[float, float, float] = (0.0, 0.0, 0.0)     # deg/s about z (roll), x (pitch), y (yaw)
    gyro: tuple[float, float, float] = (0.0, 0.0, 0.0)     # the last reading, deg/s about x, y, z (totem.py)
    accel: tuple[float, float, float] = (0.0, 1.0, 0.0)    # the last reading, g along x, y, z (poi.py)
    shake: float = 0.0
    energy: float = 0.0
    _since_shake: float = 1e9

    def step(self, gyro, accel, dt: float) -> None:
        dt = max(0.0, float(dt))
        ax, ay, az = (float(v) for v in accel)
        gx, gy, gz = (float(v) for v in gyro)
        self.gyro = (gx, gy, gz)
        self.accel = (ax, ay, az)
        g = self.gravity
        if g is None:
            g = (ax, ay, az)
        else:
            k = _ease(dt, GRAVITY_S)
            g = tuple(a + (b - a) * k for a, b in zip(g, (ax, ay, az), strict=True))
        self.gravity = g
        # lying flat the accel reads +1 g up out of the face; right side
        # down tips that reading toward −x, the far edge up toward −z
        self.roll = math.degrees(math.atan2(-g[0], g[1]))
        self.pitch = math.degrees(math.atan2(-g[2], g[1]))
        # right-hand turns: about z (toward the player) the right side rises,
        # about x the far edge rises, about y (up) the pad turns left
        self.spin = (-gz, gx, -gy)
        k_yaw = _ease(dt, YAW_LEAK_S)
        self.yaw = (self.yaw - gy * dt) * (1.0 - k_yaw)
        jolt = math.dist((ax, ay, az), g)
        self._since_shake += dt
        self.shake = 0.0
        if jolt > SHAKE_G and self._since_shake >= SHAKE_GAP_S:
            self.shake, self._since_shake = 1.0, 0.0
        rate = math.sqrt(gx * gx + gy * gy + gz * gz)
        e = max(rate / ENERGY_DPS, jolt / ENERGY_G)
        self.energy += (min(1.0, e) - self.energy) * _ease(dt, ENERGY_S)

    def lanes(self) -> list[float]:
        return [_u(self.roll, TILT_DEG), _u(self.pitch, TILT_DEG), _u(self.yaw, YAW_DEG),
                _u(self.spin[0], SPIN_DPS), _u(self.spin[1], SPIN_DPS), _u(self.spin[2], SPIN_DPS),
                self.shake, min(1.0, max(0.0, self.energy))]


def not_live(n: int) -> list[float]:
    """A scheme's lanes while the pad has nothing to say on them."""
    return [NAN] * n
