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

**The turn is integrated per report**, not here: each report's rate,
less a soft dead band (`gesture.TURN_DEADBAND_DPS`; a still Joy-Con reads
up to ~2 deg/s), times its own time — summed on the hid reader's thread
(`hid.Turn`), else by `gesture.Motion.step` — into an angle the totem
takes each frame (`Motion.take_turn`). A report that stalls adds no turn,
two reports between frames both count, a slow frame loses none.

**Reset** (A, or the D-pad's down on a pad that has one; a pad with a layout
of its own, a Joy-Con, has its reset there: − on the L, + on the R, and its
A goes back to its row): the registry's own `camera.reset`
(every phase, the orbit, the zoom and the pan to their rests, the 3D
switch's held pose dropped — the shape congruent with the world's axes),
then the pad's pose now becomes the reference the tilt is measured from.

**Letting go.** Off, the pan the tilt added is taken back. A pad that
stops being read for `LOST_S` (its device gone) lets the totem go: the
header says "(no pad)" and the next pad with sensors takes over. The pad
is named by its device role (`[[devices]]`'s `role`, "pad" for the
first), which every pad has its own of — not the router's qualifier,
which is "" for the primary.

While the totem drives a pad, that pad's rows on the buttons it uses
(`SKIP`) do not fire (the factory's A / B / X / Y toggles would otherwise
flip the faces and the points with every plane switch).

A leaf but for its sibling poi.py (a leaf: whether a poi owns the pan);
the registry and the pad are duck-typed.
"""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass, field

from . import poi

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

LOST_S = 0.5                      # no step from the pad it reads this long: it lets go
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
    seen: float = 0.0             # when (monotonic) the pad it reads last stepped it
    ref: tuple[float, float] | None = None    # (roll, pitch) radians at the reset
    pan_out: list[float] = field(default_factory=lambda: [0.0, 0.0])   # the pan it has added
    note: str = ""                # the last change, for the terminal and the pad window

    def say(self, note: str) -> None:
        self.note = note
        print(f"totem: {note}", file=sys.stderr)


def register(reg, state: TotemState) -> None:
    """The `totem.*` params: rig switches, never saved (persist off) and
    never a performer's (modulatable off) — an experiment touches no
    preset or show file. `reg.totem` is the state the pad device reads."""
    if f"{GROUP}.on" in reg:
        return
    reg.totem = state

    def set_on(v) -> None:
        v = bool(v)
        if v != state.on:
            state.on = v
            state.driving = None           # the next step takes over afresh
            if not v:
                _give_back_pan(state, reg)
            state.say(f"on — {readout(state)}" if v else "off")
    reg.toggle(f"{GROUP}.on", "Totem", lambda: state.on, set_on, group=GROUP,
               persist=False, modulatable=False,
               tip="The Joy-Con as a 4D totem (an experiment, plan 47): its gyro turns "
                   "three of the six rotation planes, its tilt moves the shape. X / Y / B "
                   "throw the x / y / z turn into the W planes; A (a Joy-Con's − or +) resets.")
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
        reset(state, reg)
    reg.trigger(f"{GROUP}.reset", "Totem reset", fire_reset, group=GROUP, modulatable=False,
                tip="The view's own reset (every phase, the orbit, the zoom and the pan) "
                    "and the pad's pose now the reference. The pad's A (a Joy-Con's − or +).")


def reset(state: TotemState, reg) -> None:
    """The registry's `camera.reset` — one reset, not a copy of its list —
    then the totem's angles read back from the phases it left and the tilt
    re-referenced on the next step."""
    get = reg.get if hasattr(reg, "get") else (lambda pid: None)
    phases = [q for n in PLANES if (q := get(f"rot.phase.{n}")) is not None]
    # a phase a route modulates keeps its base apart from the view: the
    # view's write would land in that base as a turn at the frame's apply
    # (Param.apply), so its object is put back and the base goes to 0
    held = {id(q): q.get() for q in phases if q.modulated}
    p = get("camera.reset")
    if p is not None:
        p.fire()
    for q in phases:
        if id(q) in held:
            q.put(held[id(q)])
        q.set(0.0)
    state.ang = [_base(reg, f"rot.phase.{n}") for n in PLANES]
    state.ref = None
    state.pan_out = [0.0, 0.0]          # the reset zeroed the pan, the totem's share with it
    state.say(f"reset — {readout(state)}")


def _give_back_pan(state: TotemState, reg) -> None:
    """Take back the pan the tilt added (off, or a pad letting go)."""
    for j, axis in enumerate("xy"):
        p = reg.get(f"camera.pan.{axis}") if hasattr(reg, "get") else None
        if state.pan_out[j] and p is not None:
            p.nudge(-state.pan_out[j])          # what was applied, so never past a stop
    state.pan_out = [0.0, 0.0]


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


def will_drive(state: TotemState | None, pad, role: str, now: float | None = None) -> bool:
    """Will the totem read the pad of `role` this frame — it reads it now,
    or it reads none (or a pad gone quiet) and this pad has sensors? What
    Learn asks before `act` runs the take-over (`step`)."""
    if state is None or not state.on or not _live(pad):
        return False                  # a pad with no live sensors is let go (`step`)
    now = time.monotonic() if now is None else now
    return state.driving is None or state.driving == role or now - state.seen > LOST_S


def reading(state: TotemState | None, now: float | None = None) -> str | None:
    """The role of the pad the totem reads, or None — off, reading none, or
    the pad it read not heard from for `LOST_S` (its device gone)."""
    if state is None or not state.on or state.driving is None:
        return None
    now = time.monotonic() if now is None else now
    return state.driving if now - state.seen <= LOST_S else None


def state_of(reg) -> TotemState | None:
    """The registry's totem state (`reg.totem`), or None — none registered,
    or a stub's something else. The one rule the pad device and the deck
    ask."""
    s = getattr(reg, "totem", None) if reg is not None else None
    return s if is_state(s) else None


def is_state(obj) -> bool:
    """Duck-typed: is `obj` a totem state? Not `isinstance` — a hot reload
    of this module makes a new class the live state is not an instance of
    (until it is re-classed); a stub registry's function is not one."""
    return (not callable(obj) and isinstance(getattr(obj, "on", None), bool)
            and hasattr(obj, "driving") and hasattr(obj, "ang"))


def _live(pad) -> bool:
    has = getattr(pad, "has", None)
    lanes = getattr(pad, "motion_lanes", None)
    return (bool(getattr(pad, "on", False)) and has is not None and has("motion")
            and lanes is not None and lanes() is not None)


def step(state: TotemState | None, pad, reg, dt: float, role: str = "",
         now: float | None = None) -> None:
    """One frame of the pad of device role `role` (gamepad.Pad,
    duck-typed): the buttons, the turn since the last frame into the three
    live planes, the tilt onto the pan. Nothing while the totem is off, or
    reads another pad heard from within `LOST_S` (`now`, monotonic)."""
    if state is None or not state.on:
        return
    now = time.monotonic() if now is None else now
    if state.driving is not None and now - state.seen > LOST_S:
        # the pad it read went quiet (its device gone): let go — the same
        # pad coming back takes over afresh, as any other would
        state.say(f"{state.driving or 'the pad'} went quiet")
        state.driving = None
        _give_back_pan(state, reg)                # …and the shape comes back meanwhile
    if state.driving is not None and state.driving != role:
        return                                    # another pad holds it
    if not _live(pad):
        if state.driving == role:
            state.driving = None
            _give_back_pan(state, reg)
            state.say("the pad's sensors went quiet")
        return
    motion = pad.motion
    take = getattr(motion, "take_turn", None)
    turn = take() if take is not None else (0.0, 0.0, 0.0)
    if state.driving is None:                     # taking over: nothing jumps
        _give_back_pan(state, reg)
        state.driving = role
        state.ang = [_base(reg, f"rot.phase.{n}") for n in PLANES]
        state.ref = None
        turn = (0.0, 0.0, 0.0)                    # what it turned before is not ours
        state.say(f"reading {role or 'the pad'} — {readout(state)}")
    state.seen = now
    _buttons(state, pad, reg)
    dt = max(0.0, float(dt))
    for i in range(3):                            # degrees, dead-banded per report
        p = PLANES.index(plane_of(i, state.w[i]))
        state.ang[p] = _fold(state.ang[p] + AXIS_SIGN[i] * math.radians(float(turn[i])))
    for p, name in enumerate(PLANES):
        _set(reg, f"rot.phase.{name}", state.ang[p])
    _pan(state, motion, reg, dt, pad)


def _own_layout(pad) -> bool:
    return bool(getattr(getattr(pad, "model", None), "totem_layout", False))


def skip_of(pad) -> frozenset:
    """The rows held off `pad` while the totem reads it: `SKIP`, less the
    reset for a pad whose layout has its own."""
    return SKIP - {f"pad:{RESET_BUTTON}"} if _own_layout(pad) else SKIP


def _buttons(state: TotemState, pad, reg) -> None:
    named = getattr(pad, "buttons_named", {}) or {}
    for i, b in enumerate(W_BUTTON):
        code = named.get(b)
        if code is not None and pad.pressed(code):
            p = reg.get(f"{GROUP}.w.{AXES[i]}")
            if p is not None:
                p.set(not state.w[i])
    if _own_layout(pad):
        return                                    # its reset is a row of its layout
    code = named.get(RESET_BUTTON)
    if (code is not None and pad.pressed(code)) or pad.hat_pressed(HAT_DOWN):
        p = reg.get(f"{GROUP}.reset")
        if p is not None:
            p.fire()


def _pan(state: TotemState, motion, reg, dt: float, pad=None) -> None:
    """The tilt against the reference onto camera.pan, as a relative move
    of what the totem added last frame: x right for the right side down,
    up (pan.y −) for the far end up. Off, while a poi owns the pan (poi.py),
    or for a pad whose sensors move no position (`poi.no_position`, a
    Joy-Con), what it added is taken back."""
    want = [0.0, 0.0]
    if state.pan and not poi.owns_pan(reg) and not poi.no_position(pad):
        roll, pitch = math.radians(motion.roll), math.radians(motion.pitch)
        if state.ref is None:
            state.ref = (roll, pitch)
        dr = _fold(roll - state.ref[0])
        dp = _fold(pitch - state.ref[1])
        want = [max(-PAN_MAX, min(PAN_MAX, PAN_PER_RAD * dr)),
                max(-PAN_MAX, min(PAN_MAX, -PAN_PER_RAD * dp))]
        k = _ease(dt, PAN_SMOOTH_S)
        want = [o + (t - o) * k for o, t in zip(state.pan_out, want, strict=True)]
    # pan_out is what the nudges applied — at the pan's stop less than
    # asked — so giving it back returns the pan exactly where it was
    out = list(state.pan_out)
    for j, axis in enumerate("xy"):
        d = want[j] - out[j]
        p = reg.get(f"camera.pan.{axis}")
        if d and p is not None:
            out[j] += p.nudge(d)
    state.pan_out = out


def configured_on(cfg) -> bool:
    """`[totem] on = true` in config.toml? (config.load keeps only a table
    and reports a scalar `totem = true` in cfg["error"].)"""
    section = cfg.get("totem")
    return isinstance(section, dict) and section.get("on") is True
