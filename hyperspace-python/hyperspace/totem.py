"""The Joy-Con as a 4D totem — an experiment (plan 47, not a plan item).

A pad with motion sensors (a Joy-Con, a DualSense) held in the hand turns
the shape: its gyro, integrated, drives **three of the six rotation
planes**, and its tilt holds the shape off centre. Off by default
(`totem.on`), and nothing here runs while it is off.

**The planes.** A turn about one of the pad's axes is a turn in the plane
that leaves that axis out. The pad's axes (pads/gesture.py: x right, y up
out of the face, z toward the player) are the world's (geometry.world_points:
x right, y up, z toward the eye) when the pad is held face up, pointing at
the screen. So by default

    about x → YZ      about y → XZ      about z → XY

and each axis can be thrown into the fourth dimension instead (`totem.w.x`
/ `.y` / `.z`, latched by the pad's X / Y / B):

    about x → XW      about y → YW      about z → ZW

Three planes are live at once, always one per axis; a plane an axis leaves
keeps its angle and the plane it takes continues from its own. The angles
are written as the app already composes them — `rot.phase.<plane>`, which
`geometry.rotate4` applies in its fixed order XY, XZ, YZ, XW, YW, ZW — so
three integrated angles composed in that order are not a general path
through SO(4): a big turn about two axes at once lands where Euler angles
do, not where the pad is. Fine for a test.

**While it is on the totem owns the turn**: each frame it writes all six
`rot.phase.*` from its own angles (adopted from the phases when it took
over, so nothing jumps), so the planes' own spin (`view.plane.*`, the
integrator) is held where the totem has it. A performer route on a phase
(a hand) still adds its offset on top: the totem writes the base, as a
scene-setter does (`Param.set`), and adds no writer path (ARCHITECTURE
§3.2). Off, the integrator carries on from where the totem left it.

**Position.** The sensors cannot give one: the accelerometer integrated
twice drifts away in seconds. The stand-in is tilt — the pad's roll and
pitch from gravity (`gesture.Motion`), against the pose at the last reset —
moved onto `camera.pan` (`PAN_PER_RAD` world units a radian, at most
`PAN_MAX`), smoothed: right side down moves the shape right, the far end
up moves it up, and levelling the pad brings it back. Written as a
relative move on the base (`Param.nudge`, as the sticks' orbit), so it
composes with whatever else sets the pan, and it lands in undo as an
orbit does. Note the coupling: tipping the pad to turn the shape about x
or z also tilts it, so the shape slides as it turns (`totem.pan` off
for the turn alone).

**Reset** (A, or the D-pad's down on a pad that has one — on a Joy-Con (L)
held sideways these are the same arrow): every phase to 0, the pan to 0,
the camera's orbit (yaw, pitch) to 0 and the 3D switch's held pose
dropped — the shape congruent with the world's axes — and the pad's pose
now becomes the reference the tilt is measured from.

While the totem drives a pad, that pad's rows on the buttons it uses
(`SKIP`) do not fire (the factory's A / B / X / Y toggles would otherwise
flip the faces and the points with every plane switch).

A leaf: the standard library only; the registry and the pad are
duck-typed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

GROUP = "totem"
# the six planes in the app's order (geometry.PLANES; a test holds them equal)
PLANES = ("XY", "XZ", "YZ", "XW", "YW", "ZW")
AXES = ("x", "y", "z")
# body axis → (its 3-space plane, its W plane)
AXIS_PLANES = (("YZ", "XW"), ("XZ", "YW"), ("XY", "ZW"))
# rotate4 turns axis a toward axis b by +angle in plane (a, b): a right-hand
# turn about +x takes y toward z (YZ +), about +z takes x toward y (XY +),
# about +y takes z toward x (XZ −). A W plane takes its axis's sign
AXIS_SIGN = (1.0, -1.0, 1.0)
W_BUTTON = ("X", "Y", "B")        # the button that throws each axis into W
RESET_BUTTON = "A"
HAT_DOWN = 4                      # GLFW's hat bit (gamepad.HAT_DOWN; a test holds them equal)
# the pad's rows the totem holds off while it drives (`Router.pad(skip=)`)
SKIP = frozenset({*(f"pad:{b}" for b in (*W_BUTTON, RESET_BUTTON)), "hat:DOWN"})

DEADBAND_DPS = 3.0                # a still Joy-Con reads up to ~2 deg/s (the real tape)
SMOOTH_S = 0.02                   # the gyro's one-pole smoothing (0: none)
PAN_PER_RAD = 1.5                 # world units of pan per radian of tilt
PAN_MAX = 3.0                     # …and no further each way
PAN_SMOOTH_S = 0.08


def _fold(a: float) -> float:
    return math.remainder(a, 2 * math.pi)


def _ease(dt: float, tau: float) -> float:
    return 1.0 - math.exp(-dt / tau) if tau > 0 else 1.0


def plane_of(axis: int, w: bool) -> str:
    """The plane a turn about body axis `axis` (0 x, 1 y, 2 z) drives."""
    return AXIS_PLANES[axis][1 if w else 0]


def live_planes(w) -> tuple[str, str, str]:
    """The three planes the gyro drives, one per axis."""
    return tuple(plane_of(i, bool(w[i])) for i in range(3))


def readout(state: TotemState) -> str:
    """The live mode in a few characters: ``YZ · XZ · ZW``."""
    return " · ".join(live_planes(state.w))


@dataclass
class TotemState:
    """The totem's switches (the `totem.*` params read and write them) and
    what it keeps between frames."""

    on: bool = False
    w: list[bool] = field(default_factory=lambda: [False, False, False])
    pan: bool = True
    ang: list[float] = field(default_factory=lambda: [0.0] * 6)   # radians, PLANES order
    driving: str | None = None    # the role of the pad it reads, None while it reads none
    rate: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])   # rad/s, body axes
    ref: tuple[float, float] | None = None    # (roll, pitch) radians at the reset
    pan_out: list[float] = field(default_factory=lambda: [0.0, 0.0])   # the pan it has added
    note: str = ""                # the last change, for the terminal and the pad window

    def say(self, note: str) -> None:
        import sys
        self.note = note
        print(f"totem: {note}", file=sys.stderr)


def register(reg, state: TotemState, view=None) -> None:
    """The `totem.*` params: rig switches, never saved (persist off) and
    never a performer's (modulatable off) — an experiment touches no
    preset or show file. `reg.totem` is the state the pad device reads;
    `view` (render.ViewState), when given, has its 3D-held pose dropped
    on a reset."""
    if f"{GROUP}.on" in reg:
        return
    reg.totem = state

    def set_on(v) -> None:
        v = bool(v)
        if v != state.on:
            state.on = v
            state.driving = None           # the next step takes over afresh
            state.say(f"on — {readout(state)}" if v else "off")
    reg.toggle(f"{GROUP}.on", "Totem", lambda: state.on, set_on, group=GROUP,
               persist=False, modulatable=False,
               tip="The Joy-Con as a 4D totem (an experiment, plan 47): its gyro turns "
                   "three of the six rotation planes, its tilt moves the shape. X / Y / B "
                   "throw the x / y / z turn into the W planes; A resets.")
    for i, axis in enumerate(AXES):
        def set_w(v, i=i, axis=axis) -> None:
            v = bool(v)
            if v != state.w[i]:
                state.w[i] = v
                state.say(f"{axis} → {plane_of(i, v)}  ({readout(state)})")
        reg.toggle(f"{GROUP}.w.{axis}", f"Totem {axis} in W",
                   lambda i=i: state.w[i], set_w, group=GROUP,
                   persist=False, modulatable=False,
                   tip=f"A turn about the pad's {axis} drives {plane_of(i, True)} instead of "
                       f"{plane_of(i, False)}. The pad's {W_BUTTON[i]} latches it.")
    reg.toggle(f"{GROUP}.pan", "Totem tilt pans", lambda: state.pan,
               lambda v: setattr(state, "pan", bool(v)), group=GROUP,
               persist=False, modulatable=False,
               tip="The pad's tilt (from gravity) moves the shape off centre; level, it "
                   "comes back. The stand-in for a position the sensors cannot give.")

    def fire_reset() -> None:
        reset(state, reg, view)
    reg.trigger(f"{GROUP}.reset", "Totem reset", fire_reset, group=GROUP, modulatable=False,
                tip="The shape to the world's axes (every phase, the pan and the orbit "
                    "to 0) and the pad's pose now the reference. The pad's A.")


def reset(state: TotemState, reg, view=None) -> None:
    """Every phase, the pan and the orbit to 0, the 3D switch's held pose
    dropped; the tilt re-referenced on the next step."""
    state.ang = [0.0] * 6
    state.rate = [0.0, 0.0, 0.0]
    state.ref = None
    state.pan_out = [0.0, 0.0]
    for name in PLANES:
        _set(reg, f"rot.phase.{name}", 0.0)
    for pid in ("camera.pan.x", "camera.pan.y", "camera.yaw", "camera.pitch"):
        _set(reg, pid, 0.0)
    if view is not None and hasattr(view, "body"):
        view.body = None
    state.say(f"reset — {readout(state)}")


def _set(reg, pid: str, v: float) -> None:
    p = reg.get(pid) if hasattr(reg, "get") else None
    if p is not None:
        p.set(v)


def _base(reg, pid: str) -> float:
    p = reg.get(pid) if hasattr(reg, "get") else None
    return float(p.base) if p is not None else 0.0


def drives(state: TotemState | None, role: str) -> bool:
    """Is the totem reading the pad of `role` now?"""
    return state is not None and state.on and state.driving == role


def _live(pad) -> bool:
    has = getattr(pad, "has", None)
    lanes = getattr(pad, "motion_lanes", None)
    return (bool(getattr(pad, "on", False)) and has is not None and has("motion")
            and lanes is not None and lanes() is not None)


def step(state: TotemState | None, pad, reg, dt: float, role: str = "") -> None:
    """One frame of the pad of `role` (gamepad.Pad, duck-typed): the
    buttons, the gyro into the three live planes, the tilt onto the pan.
    Nothing while the totem is off, or reads another pad."""
    if state is None or not state.on:
        return
    if state.driving is not None and state.driving != role:
        return                                    # another pad holds it
    if not _live(pad):
        if state.driving == role:
            state.driving = None
            state.say("the pad's sensors went quiet")
        return
    if state.driving is None:                     # taking over: nothing jumps
        state.driving = role
        state.ang = [_base(reg, f"rot.phase.{n}") for n in PLANES]
        state.rate = [0.0, 0.0, 0.0]
        state.ref, state.pan_out = None, [0.0, 0.0]
        state.say(f"reading {role or 'the pad'} — {readout(state)}")
    _buttons(state, pad, reg)
    dt = max(0.0, float(dt))
    motion = pad.motion
    gyro = getattr(motion, "gyro", (0.0, 0.0, 0.0))
    k = _ease(dt, SMOOTH_S)
    for i in range(3):
        v = float(gyro[i])
        v = math.copysign(max(0.0, abs(v) - DEADBAND_DPS), v)   # a soft dead band
        state.rate[i] += (math.radians(v) - state.rate[i]) * k
        p = PLANES.index(plane_of(i, state.w[i]))
        state.ang[p] = _fold(state.ang[p] + AXIS_SIGN[i] * state.rate[i] * dt)
    for p, name in enumerate(PLANES):
        _set(reg, f"rot.phase.{name}", state.ang[p])
    _pan(state, motion, reg, dt)


def _buttons(state: TotemState, pad, reg) -> None:
    named = getattr(pad, "buttons_named", {}) or {}
    for i, b in enumerate(W_BUTTON):
        code = named.get(b)
        if code is not None and pad.pressed(code):
            p = reg.get(f"{GROUP}.w.{AXES[i]}")
            if p is not None:
                p.set(not state.w[i])
    code = named.get(RESET_BUTTON)
    if (code is not None and pad.pressed(code)) or pad.hat_pressed(HAT_DOWN):
        p = reg.get(f"{GROUP}.reset")
        if p is not None:
            p.fire()


def _pan(state: TotemState, motion, reg, dt: float) -> None:
    """The tilt against the reference onto camera.pan, as a relative move
    of what the totem added last frame: x right for the right side down,
    up (pan.y −) for the far end up. Off, what it added is taken back."""
    want = [0.0, 0.0]
    if state.pan:
        roll, pitch = math.radians(motion.roll), math.radians(motion.pitch)
        if state.ref is None:
            state.ref = (roll, pitch)
        dr = _fold(roll - state.ref[0])
        dp = _fold(pitch - state.ref[1])
        want = [max(-PAN_MAX, min(PAN_MAX, PAN_PER_RAD * dr)),
                max(-PAN_MAX, min(PAN_MAX, -PAN_PER_RAD * dp))]
        k = _ease(dt, PAN_SMOOTH_S)
        want = [o + (t - o) * k for o, t in zip(state.pan_out, want, strict=True)]
    for j, axis in enumerate("xy"):
        d = want[j] - state.pan_out[j]
        p = reg.get(f"camera.pan.{axis}")
        if d and p is not None:
            p.nudge(d)
    state.pan_out = want
