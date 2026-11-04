"""The palm's orientation in the room's frame: lanes that mean the same
thing whatever the sensor's mount and whatever the camera does (plan 51).

The room is x to the performer's right, y up, z toward the performer. A
palm is three axes in it (`palm_axes`: the same on both hands, so they read
alike rather than mirrored), and three angles `Ry(yaw) · Rx(pitch) ·
Rz(roll)`, right-handed about the room's axes (`angles`): a level palm with
the fingers pointing away reads all zero; yaw + swings the fingers left,
pitch + raises them, roll + raises the palm's right side.

A lane is the whole circle, `0.5 + degrees / 360`, in [0, 1). `Palm` filters
each angle unwrapped and wraps after, so crossing ±180° steps the lane once
and never sweeps through the middle. Like core.py and signal.py, this imports
nothing from the host; it knows no camera, so an orbit cannot reach it.
"""

from __future__ import annotations

import math

from .signal import OneEuro, dot

ROOM = ("roll", "pitch", "yaw")     # each hand's lanes, in this order
ROOM_REST = 0.5                     # a level palm
# fingers this near vertical: yaw and roll are one turn, so yaw holds. It lets
# go only past POLE_EXIT_DEG, so a hand hovering on the edge does not flicker
# (BOX_EDGE's rule), and a first reading waits for the same margin
POLE_DEG = 8.0
POLE_EXIT_DEG = 11.0
_POLE = math.sin(math.radians(POLE_DEG))
_POLE_EXIT = math.sin(math.radians(POLE_EXIT_DEG))
_EPS = 1e-6

Vec = tuple[float, float, float]
Mat = tuple[Vec, Vec, Vec]          # rows

# tracking mode → Leap axes in room axes: room = M · leap. ghost.MODES's table
# (the instrument imports nothing from the host; tests/test_hands_room.py pins
# the two together). Screentop and HMD are as unmeasured here as there
MODES: dict[str, Mat] = {
    "desktop": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "screentop": ((-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "hmd": ((-1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, -1.0, 0.0)),
}


def _cross(a, b) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a) -> Vec | None:
    n = math.sqrt(dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n) if n > _EPS and math.isfinite(n) else None


def _apply(m: Mat, v) -> Vec:
    return (dot(m[0], v), dot(m[1], v), dot(m[2], v))


def wrap(deg: float) -> float:
    """Degrees into [−180, 180)."""
    return (deg + 180.0) % 360.0 - 180.0


def stage(mode: str) -> Mat:
    """Leap → the tracking mode's stage (desktop when unknown)."""
    return MODES.get(str(mode).lower(), MODES["desktop"])


def mode_name(mode: str) -> str:
    """The tracking mode as `MODES` spells it (desktop when unknown)."""
    m = str(mode).lower()
    return m if m in MODES else "desktop"


def frame(mode: str, level: Mat | None = None) -> Mat:
    """Leap → room: the tracking mode's stage, then the levelling (`level`,
    stage → room) when the room has one."""
    m = stage(mode)
    if level is None:
        return m
    cols = tuple(zip(*m))
    return tuple(tuple(dot(row, c) for c in cols) for row in level)


def palm_axes(normal, direction, m: Mat) -> Mat | None:
    """The palm's axes through `m`, as (right, up, back): back is −direction,
    up is −normal made square to it, right = up × back. None for vectors that
    give no frame (zero, parallel, not finite)."""
    back = _unit(tuple(-c for c in _apply(m, direction)))
    if back is None:
        return None
    n = _apply(m, normal)
    k = -dot(n, back)
    up = _unit((-n[0] - k * back[0], -n[1] - k * back[1], -n[2] - k * back[2]))
    if up is None:
        return None
    return (_cross(up, back), up, back)


def angles(axes: Mat, last_yaw: float | None = None,
           in_pole: bool = False) -> tuple[float, float, float, bool] | None:
    """(roll, pitch, yaw, pole) in degrees from `palm_axes`. With no
    `last_yaw` it is the plain reading, pitch within ±90°, or None for a hand
    first seen inside the pole's margin, whose yaw would be a guess. With one,
    the yaw holds inside the cone (entered at POLE_DEG; `in_pole` says it is
    in, and it stays in until POLE_EXIT_DEG), and otherwise is whichever of
    the two solutions lies nearer it: pitch then runs on past ±90° and no lane
    flips. Pitch and roll are always read given the yaw, so the three stay one
    rotation."""
    x, y, z = axes
    pole = math.hypot(z[0], z[2]) < (_POLE_EXIT if in_pole or last_yaw is None else _POLE)
    if pole and last_yaw is None:
        return None
    if pole:
        a = last_yaw
    else:
        a = math.degrees(math.atan2(z[0], z[2]))
        if last_yaw is not None and abs(wrap(a - last_yaw)) > 90.0:
            a = wrap(a + 180.0)
    r = math.radians(a)
    c, s = math.cos(r), math.sin(r)
    # Ry(−a) · the palm = Rx(pitch) · Rz(roll); a row of that is all each needs
    roll = math.degrees(math.atan2(-(y[0] * c - y[2] * s), x[0] * c - x[2] * s))
    pitch = math.degrees(math.atan2(-z[1], z[0] * s + z[2] * c))
    return roll, pitch, a, pole


def level_of(normal, direction, mode: str) -> Mat | None:
    """The levelling that makes this palm the room's axes: stage → room, whose
    rows are the palm's axes in the stage (each row then reads its own axis as
    1). None when they give no frame."""
    return palm_axes(normal, direction, stage(mode))


def is_rotation(m) -> bool:
    """Is `m` three rows of three finite numbers making a proper rotation?"""
    try:
        rows = [tuple(float(c) for c in r) for r in m]
    except (TypeError, ValueError):
        return False
    if len(rows) != 3 or any(len(r) != 3 for r in rows):
        return False
    if not all(math.isfinite(c) for r in rows for c in r):
        return False
    ok = all(abs(dot(rows[i], rows[j]) - (i == j)) < 1e-3 for i in range(3) for j in range(3))
    return ok and dot(_cross(rows[0], rows[1]), rows[2]) > 0.0


class Palm:
    """One hand's three angles at run time — never saved. `deg` is the
    filtered reading by name, wrapped, empty while the hand is away or first
    seen inside the pole's margin; `pole` says the fingers are inside the cone
    where yaw holds."""

    __slots__ = ("_filt", "_turn", "_yaw", "deg", "pole")

    def __init__(self) -> None:
        self._filt = {k: OneEuro() for k in ROOM}
        self.reset()

    def reset(self) -> None:
        """The hand left: every reading forgets, so it returns with no glide."""
        for f in self._filt.values():
            f.reset()
        self._turn: dict[str, float] = {}
        self._yaw: float | None = None
        self.deg: dict[str, float] = {}
        self.pole = False

    def step(self, axes: Mat, t: float, smooth: float, response: float) -> None:
        """One tracking frame: each angle's shortest step onto its running
        turn, the filter on that (in half turns, as a ±90° axis is shaped),
        wrapped only after."""
        read = angles(axes, self._yaw, self.pole)
        if read is None:
            return
        roll, pitch, self._yaw, self.pole = read
        for k, raw in zip(ROOM, (roll, pitch, self._yaw)):
            turn = self._turn.get(k, raw)
            turn += wrap(raw - turn)
            self._turn[k] = turn
            f = self._filt[k]
            f.min_cutoff, f.beta = smooth, response
            self.deg[k] = wrap(f(turn / 180.0, t) * 180.0)

    def value(self, k: str) -> float:
        """The lane: the whole circle, 0.5 level; NaN while away."""
        d = self.deg.get(k)
        return math.nan if d is None else ROOM_REST + d / 360.0
