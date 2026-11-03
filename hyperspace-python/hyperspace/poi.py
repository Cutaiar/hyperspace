"""The Joy-Con as the handle of a poi — an experiment beside the totem
(plan 47, "The poi"; not a plan item).

A poi is a weight on a string; the performer holds the string's other end
in a handle and swings it. Here the Joy-Con is the handle and **the shape
is the weight**: it hangs from, swings round and flies out from the
handle, as a weight on a string would, and the scene shows it where the
weight is. Off by default (`poi.on`); nothing here runs while it is off.

**The handle.** A pad cannot say where it is, only how it turns and what
it feels. So the handle is modelled as

- a *wrist*, at the world's origin (the screen's centre), that the hand's
  push moves about: the accelerometer with gravity taken out, rotated into
  the world, drives a point held home by a critically damped spring
  (`HAND_HZ`) — a quick push or a hand circling registers, a slow drift
  (and the attitude's error, which leaks a little gravity) does not.
  `poi.hand` scales it; 0 is the wrist alone.
- the *tip*, `HANDLE` world units out of the wrist along the pad's far
  end (−z in the pad's axes, toward the screen held face up), turned by
  the pad's attitude: the gyro integrated, its tilt pulled to gravity
  while the pad is not being flung (a complementary filter). The string
  hangs from the tip, so a turn of the wrist swings it, as on a real poi,
  where small circles of the hand drive the weight round.

**The string** has a rest length (`poi.length`, world units — the shape's
own radius is 1) and pulls only when stretched, never pushes: a slack
string lets the weight fly. Its stiffness is `poi.spring` (0, a cord that
barely stretches; 1, a bungee), its pull damped a little along its line.
**The weight** (`poi.weight`) is the inertia: a heavy one stretches the
string further, carries its swing longer against the air (`poi.drag`) and
answers the hand later. Gravity is `poi.gravity` × the world's (a 1-unit
string swings at about a real poi's period); 0 is a poi in orbit.

The physics runs at a fixed `STEP_S` (semi-implicit Euler) whatever the
frame rate, at most `MAX_STEPS` a frame, so a stiff string stays stable.

**What it moves.** The weight's position, x and y, is where the shape
sits (`camera.pan`, y down); its depth (toward the eye) scales it
(`camera.zoom`, `DEPTH_OCTAVES` an octave a unit, `poi.depth`). Written as
a scene-setter (`Param.set`, as the totem's pan and the sticks' orbit):
the poi keeps the base it found (`pan_home`, `zoom_home`) and writes home
+ its offset each frame. Anyone else's write on the pan or the zoom (a
reset, a knob, a load) becomes the new home. Off, the base goes back to
home. The writes land in undo and light the preset's dirty dot, as an
orbit with the stick does — and a save while the weight is out saves it
out.

**With the totem.** Each runs on its own switch, both from the same pad.
While the poi is on it owns the pan (the totem's tilt-pan steps aside);
the totem's turn still turns the shape as it flies.

**Reset** (A, or the D-pad's down, as the totem's): the handle's attitude
from gravity now (its heading straight ahead), the wrist home, the weight
hanging still under the tip.

A leaf: the standard library only; the registry and the pad are
duck-typed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

GROUP = "poi"
RESET_BUTTON = "A"
HAT_DOWN = 4                      # GLFW's hat bit (gamepad.HAT_DOWN; a test holds them equal)
SKIP = frozenset({f"pad:{RESET_BUTTON}", "hat:DOWN"})

G_MPS2 = 9.81
UNITS_PER_M = 2.5                 # a 1-unit string is a real poi's 40 cm: the same period
G_WORLD = G_MPS2 * UNITS_PER_M    # world units / s², at poi.gravity 1
HANDLE = 0.3                      # wrist → tip, world units (a hand and a Joy-Con)
HAND_HZ = 0.7                     # the wrist's spring home: below this the hand's push fades
HAND_DEADBAND_G = 0.04            # a still pad's accel noise and the attitude's leak
STEP_S = 1.0 / 960.0              # the physics' fixed step
MAX_STEPS = 96                    # …at most this many a frame (a stall drops the rest)
K_STIFF = 3000.0                  # the string's stiffness at poi.spring 0 (mass·unit/s² per unit)
K_SOFT = 6.0                      # …and at 1, geometric between
STRING_ZETA = 0.25                # the string's damping along its line, of critical
MAX_STRETCH = 4.0                 # the string never longer than this × its length
TILT_GAIN = 2.0                   # rad/s per rad: how fast gravity pulls the attitude's tilt
TILT_TRUST_G = 0.15               # gravity is trusted while |accel| is within this of 1 g
DEPTH_OCTAVES = 0.5               # zoom octaves per world unit of depth toward the eye

DEFAULTS = {"weight": 0.3, "length": 1.0, "spring": 0.2, "gravity": 1.0,
            "drag": 0.15, "hand": 1.0}
RANGES = {"weight": (0.05, 2.0), "length": (0.2, 4.0), "spring": (0.0, 1.0),
          "gravity": (0.0, 2.0), "drag": (0.0, 1.0), "hand": (0.0, 2.0)}

Vec = list[float]


# ---------------------------------------------------------------- small vector maths

def _add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _mul(a, s: float):
    return [a[0] * s, a[1] * s, a[2] * s]


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _norm(a) -> float:
    return math.sqrt(_dot(a, a))


def _ident():
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _apply(R, v):
    """R·v (R a list of rows)."""
    return [_dot(R[0], v), _dot(R[1], v), _dot(R[2], v)]


def _apply_t(R, v):
    """Rᵀ·v."""
    return [R[0][0] * v[0] + R[1][0] * v[1] + R[2][0] * v[2],
            R[0][1] * v[0] + R[1][1] * v[1] + R[2][1] * v[2],
            R[0][2] * v[0] + R[1][2] * v[1] + R[2][2] * v[2]]


def _rodrigues(w, angle: float):
    """The rotation by `angle` about the unit axis `w`."""
    x, y, z = w
    c, s = math.cos(angle), math.sin(angle)
    t = 1.0 - c
    return [[c + x * x * t, x * y * t - z * s, x * z * t + y * s],
            [y * x * t + z * s, c + y * y * t, y * z * t - x * s],
            [z * x * t - y * s, z * y * t + x * s, c + z * z * t]]


def _matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _orthonormal(R):
    """Gram–Schmidt on the columns, so rounding never shears the attitude."""
    c0 = [R[0][0], R[1][0], R[2][0]]
    c1 = [R[0][1], R[1][1], R[2][1]]
    n0 = _norm(c0) or 1.0
    c0 = _mul(c0, 1.0 / n0)
    c1 = _sub(c1, _mul(c0, _dot(c0, c1)))
    n1 = _norm(c1) or 1.0
    c1 = _mul(c1, 1.0 / n1)
    c2 = _cross(c0, c1)
    return [[c0[0], c1[0], c2[0]], [c0[1], c1[1], c2[1]], [c0[2], c1[2], c2[2]]]


def from_gravity(up_body) -> list[list[float]]:
    """The attitude (body → world) that puts the pad's measured up
    (`up_body`, its axes) on the world's +y, with no turn about the
    vertical: the shortest rotation between them."""
    n = _norm(up_body)
    if n < 1e-6:
        return _ident()
    u = _mul(up_body, 1.0 / n)
    world_up = [0.0, 1.0, 0.0]
    axis = _cross(u, world_up)
    s, c = _norm(axis), _dot(u, world_up)
    if s < 1e-9:
        return _ident() if c > 0 else [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]]
    return _rodrigues(_mul(axis, 1.0 / s), math.atan2(s, c))


# ---------------------------------------------------------------- the state

@dataclass
class PoiState:
    """The poi's switches and dials (the `poi.*` params read and write
    them) and what it keeps between frames."""

    on: bool = False
    depth: bool = True
    weight: float = DEFAULTS["weight"]
    length: float = DEFAULTS["length"]
    spring: float = DEFAULTS["spring"]
    gravity: float = DEFAULTS["gravity"]
    drag: float = DEFAULTS["drag"]
    hand: float = DEFAULTS["hand"]
    driving: str | None = None    # the role of the pad it reads
    att: list = field(default_factory=_ident)       # the handle's attitude, body → world
    wrist: Vec = field(default_factory=lambda: [0.0, 0.0, 0.0])
    wrist_v: Vec = field(default_factory=lambda: [0.0, 0.0, 0.0])
    ball: Vec = field(default_factory=lambda: [0.0, -1.0, 0.0])
    ball_v: Vec = field(default_factory=lambda: [0.0, 0.0, 0.0])
    left: float = 0.0             # time not yet stepped (less than STEP_S)
    settled: bool = False         # the attitude has been set from gravity
    pan_home: list | None = None  # the pan's base under the poi; None: not adopted
    pan_last: list | None = None  # what the poi last wrote
    zoom_home: float | None = None
    zoom_last: float | None = None
    note: str = ""

    def say(self, note: str) -> None:
        import sys
        self.note = note
        print(f"poi: {note}", file=sys.stderr)

    def stiffness(self) -> float:
        s = min(1.0, max(0.0, self.spring))
        return K_STIFF * (K_SOFT / K_STIFF) ** s

    def tip(self) -> Vec:
        """Where the string hangs from: the wrist, and the handle along the
        pad's far end (−z in its axes)."""
        return _add(self.wrist, _apply(self.att, [0.0, 0.0, -HANDLE]))

    def hang(self) -> None:
        """The weight still under the tip, the string stretched by its
        weight (m·g / k) as it would hang."""
        sag = max(self.weight, 1e-3) * G_WORLD * self.gravity / self.stiffness()
        drop = max(self.length, 1e-3) + sag
        self.ball = _add(self.tip(), [0.0, -min(drop, MAX_STRETCH * self.length), 0.0])
        self.ball_v = [0.0, 0.0, 0.0]

    def offset(self) -> Vec:
        """The weight in the world: where the shape is drawn from home. Its
        depth is measured from the tip's at rest (`HANDLE` into the
        screen), so a weight hanging still is drawn at home's size."""
        return [self.ball[0], self.ball[1], self.ball[2] + HANDLE]


def readout(state: PoiState) -> str:
    """The dials in a few characters: ``1.00 · 0.30 · 0.20`` (length,
    weight, springiness)."""
    return f"{state.length:.2f} · {state.weight:.2f} · {state.spring:.2f}"


# ---------------------------------------------------------------- the params

def register(reg, state: PoiState, cfg: dict | None = None) -> None:
    """The `poi.*` params: rig switches, never saved (persist off) and
    never a performer's (modulatable off), as the totem's. `cfg`, the
    config's `[poi]` table, gives the dials' starting values (the only
    way they outlast a launch). `reg.poi` is the state the pad reads."""
    if f"{GROUP}.on" in reg:
        return
    reg.poi = state
    cfg = cfg if isinstance(cfg, dict) else {}
    for key, (lo, hi) in RANGES.items():
        v = cfg.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
            setattr(state, key, min(hi, max(lo, float(v))))
    if isinstance(cfg.get("depth"), bool):
        state.depth = cfg["depth"]

    def set_on(v) -> None:
        v = bool(v)
        if v == state.on:
            return
        if not v:
            _release(state, reg)
        state.on = v
        state.driving = None
        state.say(f"on — {readout(state)}" if v else "off")
    reg.toggle(f"{GROUP}.on", "Poi", lambda: state.on, set_on, group=GROUP,
               persist=False, modulatable=False,
               tip="The Joy-Con as the handle of a poi (an experiment, plan 47): the shape "
                   "is the weight on its string, swung by the pad. A resets.")

    tips = {
        "weight": ("Poi weight", "{:.2f}", True,
                   ("The weight on the string: heavier stretches the string further, "
                    "carries its swing longer and answers the hand later.")),
        "length": ("Poi string length", "{:.2f}", True,
                   "The string's rest length, in the shape's radii."),
        "spring": ("Poi springiness", "{:.2f}", False,
                   "0, a cord that barely stretches; 1, a bungee that bounces."),
        "gravity": ("Poi gravity", "{:.2f}×", False,
                    "Gravity on the weight, × the world's; 0 is a poi in orbit."),
        "drag": ("Poi air drag", "{:.2f}", False,
                 "How fast the air takes the swing out."),
        "hand": ("Poi hand push", "{:.2f}×", False,
                 ("How much the hand's push (the accelerometer) moves the handle; 0 is "
                  "the wrist's turn alone.")),
    }
    for key, (label, f, log, tip) in tips.items():
        lo, hi = RANGES[key]

        def put(v, key=key, lo=lo, hi=hi) -> None:
            v = float(v)
            if math.isfinite(v):
                setattr(state, key, min(hi, max(lo, v)))
        reg.continuous(f"{GROUP}.{key}", label, lambda key=key: getattr(state, key), put,
                       lo=lo, hi=hi, log=log, fmt=lambda v, f=f: f.format(v), group=GROUP,
                       persist=False, modulatable=False, tip=tip)
    reg.toggle(f"{GROUP}.depth", "Poi depth zooms", lambda: state.depth,
               lambda v: setattr(state, "depth", bool(v)), group=GROUP,
               persist=False, modulatable=False,
               tip="The weight swinging toward the eye grows the shape, away shrinks it.")

    def fire_reset() -> None:
        reset(state)
    reg.trigger(f"{GROUP}.reset", "Poi reset", fire_reset, group=GROUP, modulatable=False,
                tip="The handle's heading straight ahead from where the pad is, the weight "
                    "hanging still. The pad's A.")


def reset(state: PoiState) -> None:
    """The handle re-levelled from gravity on the next step, the wrist
    home, the weight hanging still."""
    state.settled = False
    state.att = _ident()
    state.wrist, state.wrist_v = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    state.left = 0.0
    state.hang()
    state.say(f"reset — {readout(state)}")


def configured(cfg) -> dict:
    """The config's `[poi]` table, or {} (a scalar `poi = true` is no table)."""
    section = cfg.get("poi") if isinstance(cfg, dict) else None
    return section if isinstance(section, dict) else {}


def drives(state: PoiState | None, role: str) -> bool:
    """Is the poi reading the pad of `role` now?"""
    return state is not None and state.on and state.driving == role


def will_drive(state: PoiState | None, pad, role: str) -> bool:
    """Will the poi read the pad of `role` this frame — it reads it now, or
    reads none and this pad has sensors? What Learn asks before `act`."""
    if state is None or not state.on or not _live(pad):
        return False
    return state.driving is None or state.driving == role


def state_of(reg) -> PoiState | None:
    """The registry's poi state (`reg.poi`), or None."""
    s = getattr(reg, "poi", None) if reg is not None else None
    return s if is_state(s) else None


def is_state(obj) -> bool:
    """Duck-typed, as `totem.is_state`: a hot reload of this module makes a
    new class the live state is not an instance of (until re-classed)."""
    return (not callable(obj) and isinstance(getattr(obj, "on", None), bool)
            and hasattr(obj, "driving") and hasattr(obj, "ball"))


def owns_pan(reg) -> bool:
    """Is a poi swinging the shape (the totem's tilt-pan steps aside)?"""
    state = state_of(reg)
    return state is not None and state.on


def _live(pad) -> bool:
    has = getattr(pad, "has", None)
    lanes = getattr(pad, "motion_lanes", None)
    return (bool(getattr(pad, "on", False)) and has is not None and has("motion")
            and lanes is not None and lanes() is not None)


# ---------------------------------------------------------------- one frame

def step(state: PoiState | None, pad, reg, dt: float, role: str = "") -> None:
    """One frame of the pad of `role` (gamepad.Pad, duck-typed): the reset
    button, the handle from the sensors, the weight on its string, the
    shape where the weight is. Nothing while the poi is off or reads
    another pad."""
    if state is None or not state.on:
        return
    if state.driving is not None and state.driving != role:
        return
    if not _live(pad):
        if state.driving == role:
            state.driving = None
            state.say("the pad's sensors went quiet")
        return
    if state.driving is None:
        state.driving = role
        reset(state)
        state.say(f"reading {role or 'the pad'} — {readout(state)}")
    _buttons(state, pad, reg)
    dt = min(max(0.0, float(dt)), MAX_STEPS * STEP_S)
    motion = pad.motion
    gyro = [math.radians(float(v)) for v in getattr(motion, "gyro", (0.0, 0.0, 0.0))]
    accel = [float(v) for v in getattr(motion, "accel", None) or
             getattr(motion, "gravity", None) or (0.0, 1.0, 0.0)]
    if not state.settled:
        state.att = from_gravity(getattr(motion, "gravity", None) or accel)
        state.settled = True
        state.hang()
    _attitude(state, gyro, accel, dt)
    push = _push(state, accel)
    state.left += dt
    n = min(MAX_STEPS, int(state.left / STEP_S))
    state.left -= n * STEP_S
    for _ in range(n):
        _physics(state, push, STEP_S)
    _write(state, reg)


def _buttons(state: PoiState, pad, reg) -> None:
    named = getattr(pad, "buttons_named", {}) or {}
    code = named.get(RESET_BUTTON)
    if (code is not None and pad.pressed(code)) or pad.hat_pressed(HAT_DOWN):
        p = reg.get(f"{GROUP}.reset") if hasattr(reg, "get") else None
        if p is not None:
            p.fire()
        else:
            reset(state)


def _attitude(state: PoiState, gyro, accel, dt: float) -> None:
    """The gyro integrated (body rates: R ← R·exp(ω dt)), the tilt pulled
    toward gravity while the pad is near 1 g (not being flung)."""
    w = list(gyro)
    a = _norm(accel)
    if a > 1e-6 and abs(a - 1.0) < TILT_TRUST_G:
        measured = _mul(accel, 1.0 / a)               # up, in the pad's axes
        predicted = _apply_t(state.att, [0.0, 1.0, 0.0])
        w = _add(w, _mul(_cross(measured, predicted), TILT_GAIN))
    rate = _norm(w)
    if rate * dt > 1e-9:
        state.att = _orthonormal(_matmul(state.att, _rodrigues(_mul(w, 1.0 / rate), rate * dt)))


def _push(state: PoiState, accel) -> Vec:
    """The hand's push in the world, world units / s²: the specific force
    turned into the world with gravity's 1 g taken out, a dead band off
    the top, × `poi.hand`."""
    lin = _sub(_apply(state.att, accel), [0.0, 1.0, 0.0])       # in g
    n = _norm(lin)
    if n <= HAND_DEADBAND_G or state.hand <= 0.0:
        return [0.0, 0.0, 0.0]
    return _mul(lin, (n - HAND_DEADBAND_G) / n * G_MPS2 * UNITS_PER_M * state.hand)


def _physics(state: PoiState, push, h: float) -> None:
    """One fixed step: the wrist on its spring home, then the weight on its
    string from the tip (semi-implicit Euler: velocities, then positions)."""
    wn = 2.0 * math.pi * HAND_HZ
    acc = _sub(push, _add(_mul(state.wrist, wn * wn), _mul(state.wrist_v, 2.0 * wn)))
    state.wrist_v = _add(state.wrist_v, _mul(acc, h))
    state.wrist = _add(state.wrist, _mul(state.wrist_v, h))

    m = max(state.weight, 1e-3)
    L = max(state.length, 1e-3)
    k = state.stiffness()
    tip = state.tip()
    d = _sub(state.ball, tip)
    dist = _norm(d)
    force = [0.0, -G_WORLD * state.gravity * m, 0.0]
    force = _sub(force, _mul(state.ball_v, state.drag))
    if dist > L and dist > 1e-9:
        u = _mul(d, 1.0 / dist)
        along = _dot(state.ball_v, u)
        c = 2.0 * STRING_ZETA * math.sqrt(k * m)
        force = _sub(force, _mul(u, k * (dist - L) + c * along))
    state.ball_v = _add(state.ball_v, _mul(force, h / m))
    state.ball = _add(state.ball, _mul(state.ball_v, h))
    d = _sub(state.ball, tip)
    dist = _norm(d)
    if dist > MAX_STRETCH * L:                        # a runaway stretch is held at the stop
        u = _mul(d, 1.0 / dist)
        state.ball = _add(tip, _mul(u, MAX_STRETCH * L))
        out = _dot(state.ball_v, u)
        if out > 0:
            state.ball_v = _sub(state.ball_v, _mul(u, out))


# ---------------------------------------------------------------- the shape where the weight is

def _param(reg, pid: str):
    return reg.get(pid) if hasattr(reg, "get") else None


def _write(state: PoiState, reg) -> None:
    """Home + the weight's offset onto the pan (x right, y down) and, with
    `poi.depth`, home × 2^(depth · DEPTH_OCTAVES) onto the zoom. A base
    that is not what the poi last wrote was written by someone else: it is
    that axis's new home."""
    px, py = _param(reg, "camera.pan.x"), _param(reg, "camera.pan.y")
    off = state.offset()
    if px is not None and py is not None:
        now = [float(px.base), float(py.base)]
        if state.pan_home is None or state.pan_last is None:
            state.pan_home = now
        else:                                         # each axis on its own
            state.pan_home = [n if abs(n - last) > 1e-6 else home for n, last, home
                              in zip(now, state.pan_last, state.pan_home, strict=True)]
        px.set(_clamp_to(px, state.pan_home[0] + off[0]))
        py.set(_clamp_to(py, state.pan_home[1] - off[1]))
        state.pan_last = [float(px.base), float(py.base)]
    zoom = _param(reg, "camera.zoom")
    if zoom is not None:
        now = float(zoom.base)
        if state.zoom_home is None or state.zoom_last is None or (
                abs(now - state.zoom_last) > 1e-9 * max(1.0, abs(now))):
            state.zoom_home = now
        factor = 2.0 ** (off[2] * DEPTH_OCTAVES) if state.depth else 1.0
        zoom.set(_clamp_to(zoom, state.zoom_home * factor))
        state.zoom_last = float(zoom.base)


def _clamp_to(p, v: float) -> float:
    lo, hi = getattr(p, "lo", -math.inf), getattr(p, "hi", math.inf)
    return min(hi, max(lo, v))


def _release(state: PoiState, reg) -> None:
    """Switched off: the pan and the zoom back to the home the poi found
    (each axis unless someone else has written it since), and forgotten."""
    px, py = _param(reg, "camera.pan.x"), _param(reg, "camera.pan.y")
    if state.pan_home is not None and state.pan_last is not None and px is not None \
            and py is not None:
        for p, home, last in zip((px, py), state.pan_home, state.pan_last, strict=True):
            if abs(float(p.base) - last) <= 1e-6:
                p.set(home)
    zoom = _param(reg, "camera.zoom")
    if (state.zoom_home is not None and state.zoom_last is not None and zoom is not None
            and abs(float(zoom.base) - state.zoom_last) <= 1e-9 * max(1.0, abs(state.zoom_last))):
        zoom.set(state.zoom_home)
    state.pan_home = state.pan_last = None
    state.zoom_home = state.zoom_last = None
