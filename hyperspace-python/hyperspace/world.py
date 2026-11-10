"""World objects: the things drawn in the scene, and the registries keyed by them (plan 59).

A **world object** is a thing that is drawn: the shape (`shape`) and the two
hands (`hand.left`, `hand.right`). Each has a **home** pose — what its source
says: the `camera.*` params for the shape, the tracked palm for a hand — and
an **offset** pose, what the world's own systems add on top. The pose drawn is
``home ∘ offset``: the offset acts in the home's frame, so a turn of the offset
turns the object about its own centre.

What else an object takes part in is an **orthogonal registry** keyed by its
id, each owned by its own system (the owner, 2026-11-10: "registering an
object as a physics object, or as a clippable one, is an orthogonal
registry"):

  bodies    `Body`: velocity and drag (mass and inertia are stored, unused
            here). This plan steps free bodies only; joints and inertia
            shaping are plan 60's.
  joints    declared, empty: plan 60 fills it.
  puppets   `Palm`: a tracked palm that sets a hand object's home each frame.
  clip      declared, empty, no consumer: the API's shape, settled.

Removing an object from `bodies` leaves it drawn and still; removing it from
the world removes it from every registry.

The frame (`World.frame`, once a frame after `HandsIO.poll`): puppets, then
physics at a fixed step (`STEP_S`, at most `MAX_STEPS` a frame — the poi's
rule, so a stall drops the rest), then the renderer reads poses. Nothing else
writes them.

**The pose** (`Pose`) is a 4-vector position, a pair of unit quaternions
(qL, qR) and a scale. A point v, read as a quaternion with w as its real part,
turns as ``qL · v · q̄R``. 3D is the case qL = qR: w stays fixed and x, y, z
turn as the ordinary 3D quaternion qL turns them. Every object here is in that
case with w = 0 (the world stays 3D); the general form is stored so plan 61's
4D world changes no stored pose. Quaternions are (x, y, z, w), w the real
part, the layout of a point and of the Leap's bone rotations.

Pure: numpy and nothing from the package (the same rule as `hands/`), so any
module may import it; what it reads from the host arrives as arguments.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

GROUP = "world"
SHAPE = "shape"
HANDS = {"left": "hand.left", "right": "hand.right"}   # side → the hand object's id
KINDS = ("shape", "hand")
# the physics' fixed step and its cap a frame: poi.py's STEP_S and MAX_STEPS,
# restated (this module imports nothing from the package; tests/test_world.py
# holds them equal)
STEP_S = 1.0 / 960.0
MAX_STEPS = 96
_EPS = 1e-12


# ------------------------------------------------------------- quaternions

def qmul(a, b) -> np.ndarray:
    """The Hamilton product a·b, both (x, y, z, w)."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


def qconj(q) -> np.ndarray:
    return np.array([-q[0], -q[1], -q[2], q[3]], dtype=np.float64)


def qnorm(q) -> np.ndarray:
    """`q` made unit; the identity for a quaternion with no length."""
    q = np.asarray(q, dtype=np.float64)
    n = float(np.linalg.norm(q))
    return q / n if n > _EPS and math.isfinite(n) else np.array([0.0, 0.0, 0.0, 1.0])


def qexp(r) -> np.ndarray:
    """The unit quaternion of rotation vector `r` (axis × angle, radians):
    (sin(θ/2)·axis, cos(θ/2))."""
    r = np.asarray(r, dtype=np.float64)
    th = float(np.linalg.norm(r))
    if th < 1e-9:
        return qnorm(np.array([0.5 * r[0], 0.5 * r[1], 0.5 * r[2], 1.0]))
    s = math.sin(0.5 * th) / th
    return np.array([r[0] * s, r[1] * s, r[2] * s, math.cos(0.5 * th)])


def qlog(q) -> np.ndarray:
    """`qexp`'s inverse: the rotation vector of unit `q` (angle up to 2π, so
    −q gives the long way round and `qexp` takes it back to −q)."""
    q = np.asarray(q, dtype=np.float64)
    v = q[:3]
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        if q[3] > 0:
            return 2.0 * v / max(q[3], _EPS)
        # −1: a whole turn, about x (any axis is −1 again). Not 0: in a 4D pose
        # (−1, 1) is the central inversion, and qexp must give −1 back
        return np.array([2.0 * math.pi, 0.0, 0.0])
    return (2.0 * math.atan2(n, q[3]) / n) * v


def left_matrix(q) -> np.ndarray:
    """L(q), 4×4: L(q) @ v is q·v, for v (x, y, z, w)."""
    x, y, z, w = q
    return np.array([[w, -z, y, x], [z, w, -x, y], [-y, x, w, z], [-x, -y, -z, w]])


def right_matrix(q) -> np.ndarray:
    """R(q), 4×4: R(q) @ v is v·q, for v (x, y, z, w)."""
    x, y, z, w = q
    return np.array([[w, z, -y, x], [-z, w, x, y], [y, -x, w, z], [-x, -y, -z, w]])


def quat_of(m) -> np.ndarray:
    """The unit quaternion of a 3×3 proper rotation `m` (Shepperd's method)."""
    m = np.asarray(m, dtype=np.float64)
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0.0:
        s = 2.0 * math.sqrt(tr + 1.0)
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = 2.0 * math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2])
        q = [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = 2.0 * math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2])
        q = [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = 2.0 * math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1])
        q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]
    return qnorm(q)


# -------------------------------------------------------------------- pose

_ID = (0.0, 0.0, 0.0, 1.0)


@dataclass
class Pose:
    """A rigid placement with a scale: p ↦ position + scale · (qL · p · q̄R).

    `position` (x, y, z, w); `ql`, `qr` unit quaternions (x, y, z, w); `scale`
    > 0. A Pose is a value: every operation returns a new one."""

    position: np.ndarray = field(default_factory=lambda: np.zeros(4))
    ql: np.ndarray = field(default_factory=lambda: np.array(_ID))
    qr: np.ndarray = field(default_factory=lambda: np.array(_ID))
    scale: float = 1.0

    def __post_init__(self) -> None:
        p = np.zeros(4)
        given = np.asarray(self.position, dtype=np.float64).ravel()
        p[:len(given)] = given[:4]            # a 3-vector is w = 0
        self.position = p
        self.ql = np.asarray(self.ql, dtype=np.float64).copy()
        self.qr = np.asarray(self.qr, dtype=np.float64).copy()
        self.scale = float(self.scale)

    # ---- makers
    @classmethod
    def identity(cls) -> Pose:
        return cls()

    @classmethod
    def turn3(cls, q, position=(0.0, 0.0, 0.0), scale: float = 1.0) -> Pose:
        """A 3D pose: the unit quaternion `q` as the pair (q, q)."""
        q = qnorm(q)
        return cls(position, q, q, scale)

    @classmethod
    def from_matrix3(cls, m, position=(0.0, 0.0, 0.0), scale: float = 1.0) -> Pose:
        """A 3D pose from a 3×3 proper rotation."""
        return cls.turn3(quat_of(m), position, scale)

    # ---- what it is
    def is_identity(self) -> bool:
        """Exactly the identity: no tolerance, so the renderer's old path is
        taken only when the offset has never moved (or was reset)."""
        return (self.scale == 1.0 and not self.position.any()
                and tuple(self.ql) == _ID and tuple(self.qr) == _ID)

    def is_3d(self, tol: float = 1e-9) -> bool:
        """qL = qR (up to the pair's shared sign) and no w in the position:
        a pose of the 3D world."""
        same = min(np.abs(self.ql - self.qr).max(), np.abs(self.ql + self.qr).max())
        return bool(same <= tol and abs(self.position[3]) <= tol)

    # ---- maths
    def rotation4(self) -> np.ndarray:
        """The 4×4 rotation: R @ v is qL · v · q̄R (v as (x, y, z, w))."""
        return left_matrix(self.ql) @ right_matrix(qconj(self.qr))

    def turn(self, points) -> np.ndarray:
        """`points` (n, 4) or (4,) through the rotation alone: qL · v · q̄R."""
        return np.asarray(points, dtype=np.float64) @ self.rotation4().T

    def apply(self, points) -> np.ndarray:
        """`points` (n, 4) or (4,) — a 3-vector is w = 0 — through the whole
        pose: position + scale · (qL · v · q̄R)."""
        p = np.asarray(points, dtype=np.float64)
        if p.shape[-1] == 3:
            p = np.concatenate([p, np.zeros(p.shape[:-1] + (1,))], axis=-1)
        return self.position + self.scale * self.turn(p)

    def compose(self, other: Pose) -> Pose:
        """self ∘ other: `other` first, then `self` (as matrices multiply)."""
        return Pose(self.position + self.scale * self.turn(other.position),
                    qmul(self.ql, other.ql), qmul(self.qr, other.qr),
                    self.scale * other.scale)

    def inverse(self) -> Pose:
        s = 1.0 / self.scale
        ql, qr = qconj(self.ql), qconj(self.qr)
        back = left_matrix(ql) @ right_matrix(qconj(qr))
        return Pose(-s * (back @ self.position), ql, qr, s)

    def model3(self) -> np.ndarray:
        """The 3D homogeneous model matrix, 4×4 (column vectors): x, y, z of
        `apply`. Exact for a 3D pose (`is_3d`), which every pose here is."""
        m = np.eye(4)
        m[:3, :3] = self.scale * self.rotation4()[:3, :3]
        m[:3, 3] = self.position[:3]
        return m

    def renormalized(self) -> Pose:
        return Pose(self.position, qnorm(self.ql), qnorm(self.qr), self.scale)

    def log(self) -> np.ndarray:
        """The pose as a tangent vector, 11: position (4), qL's and qR's
        rotation vectors (3 each), ln scale (1). For springs (plan 60)."""
        return np.concatenate([self.position, qlog(self.ql), qlog(self.qr),
                               [math.log(self.scale)]])

    @classmethod
    def exp(cls, v) -> Pose:
        """`log`'s inverse."""
        v = np.asarray(v, dtype=np.float64)
        return cls(v[:4], qexp(v[4:7]), qexp(v[7:10]), math.exp(float(v[10])))

    def slerp(self, other: Pose, t: float) -> Pose:
        """The way from self (t 0) to other (t 1): the position straight, the
        scale geometric, each quaternion the short way round. (qL, qR) and
        (−qL, −qR) are one rotation (but not (−qL, qR)), so other's pair is
        flipped together when that is the shorter way for the two at once."""
        t = float(t)
        ol, orr = other.ql, other.qr
        if float(np.dot(self.ql, ol) + np.dot(self.qr, orr)) < 0.0:
            ol, orr = -ol, -orr
        turn = lambda a, b: qnorm(qmul(qexp(t * qlog(qnorm(qmul(b, qconj(a))))), a))
        return Pose(self.position + t * (other.position - self.position),
                    turn(self.ql, ol), turn(self.qr, orr),
                    self.scale ** (1.0 - t) * other.scale ** t)


def shape_home(zoom: float, pan) -> Pose:
    """The shape's home from `camera.zoom` / `camera.pan` (`geometry.model_matrix`'s
    reading: pan.y positive down the screen, world y up). No turn: `camera.yaw` /
    `.pitch` turn the points on the CPU before the world (`geometry.world_points`)."""
    return Pose(np.array([float(pan[0]), -float(pan[1]), 0.0, 0.0]), scale=float(zoom))


# ---------------------------------------------------------------- registries

@dataclass
class WorldObject:
    """A thing drawn in the scene. `present` False: a hand its tracker lost —
    still registered, its pose where it was last seen."""

    id: str
    kind: str
    home: Pose = field(default_factory=Pose)
    offset: Pose = field(default_factory=Pose)
    present: bool = True

    @property
    def pose(self) -> Pose:
        """What is drawn: home ∘ offset."""
        return self.home.compose(self.offset)


@dataclass
class Body:
    """A free body (bodies registry): it moves its object's offset. `velocity`
    (4, world units/s), `spin_l` / `spin_r` the angular velocity of qL and qR
    (rad/s, rotation vectors; equal for a 3D body, `Body.spin3`), each decaying
    at its drag (1/s). `mass` and `inertia` are stored for plan 60."""

    mass: float = 1.0
    inertia: np.ndarray = field(default_factory=lambda: np.eye(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(4))
    spin_l: np.ndarray = field(default_factory=lambda: np.zeros(3))
    spin_r: np.ndarray = field(default_factory=lambda: np.zeros(3))
    drag: float = 0.0
    angular_drag: float = 0.0

    def spin3(self, omega) -> Body:
        """A 3D angular velocity (rad/s about x, y, z): both halves alike."""
        self.spin_l = np.asarray(omega, dtype=np.float64).copy()
        self.spin_r = self.spin_l.copy()
        return self

    def still(self) -> None:
        self.velocity = np.zeros(4)
        self.spin_l, self.spin_r = np.zeros(3), np.zeros(3)


@dataclass
class Palm:
    """A puppet: a tracked palm sets its object's home each frame. `side`
    "left" / "right"; `velocity` and `spin` (3D, rad/s) its frame-to-frame
    difference, zero on the frame it arrives — kept for plan 60's throws, never
    fed into a body (the puppet sets the home; a body moves the offset)."""

    side: str
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(4))
    spin: np.ndarray = field(default_factory=lambda: np.zeros(3))
    last: Pose | None = None


class World:
    """The drawn objects and the registries keyed by them (module docstring)."""

    def __init__(self) -> None:
        self.objects: dict[str, WorldObject] = {}
        self.bodies: dict[str, Body] = {}
        self.joints: dict[str, object] = {}       # plan 60
        self.puppets: dict[str, Palm] = {}
        self.clip: dict[str, object] = {}         # no consumer yet
        self.left = 0.0                           # time not yet stepped (< STEP_S)

    @classmethod
    def default(cls) -> World:
        """The scene as it is: the shape, and each hand puppeted by its palm.
        No bodies: nothing moves an offset."""
        w = cls()
        w.add(SHAPE, "shape")
        for side, oid in HANDS.items():
            w.add(oid, "hand", present=False)
            w.puppet(oid, Palm(side))
        return w

    def registries(self) -> tuple[dict, ...]:
        return self.bodies, self.joints, self.puppets, self.clip

    def targets(self) -> list[tuple[object, str, str]]:
        """The live objects a hot reload re-classes, as (object, module, class):
        the world, its objects with their poses, the bodies and the puppets.
        Re-evaluated each swap (the poses are values, replaced as they move)."""
        out: list[tuple[object, str, str]] = [(self, "world", "World")]
        for obj in self.objects.values():
            out += [(obj, "world", "WorldObject"), (obj.home, "world", "Pose"),
                    (obj.offset, "world", "Pose")]
        out += [(b, "world", "Body") for b in self.bodies.values()]
        for p in self.puppets.values():
            out.append((p, "world", "Palm"))
            if p.last is not None:
                out.append((p.last, "world", "Pose"))
        return out

    # ---- the drawn things
    def add(self, oid: str, kind: str, home: Pose | None = None, *,
            present: bool = True) -> WorldObject:
        if kind not in KINDS:
            raise ValueError(f"world: no kind {kind!r} (one of {', '.join(KINDS)})")
        if oid in self.objects:
            raise ValueError(f"world: {oid} is already registered")
        obj = WorldObject(oid, kind, home if home is not None else Pose(), present=present)
        self.objects[oid] = obj
        return obj

    def remove(self, oid: str) -> WorldObject | None:
        """Out of the world, and so out of every registry."""
        for r in self.registries():
            r.pop(oid, None)
        return self.objects.pop(oid, None)

    def __contains__(self, oid: str) -> bool:
        return oid in self.objects

    def __getitem__(self, oid: str) -> WorldObject:
        return self.objects[oid]

    def pose(self, oid: str) -> Pose:
        return self.objects[oid].pose

    def home(self, oid: str, pose: Pose) -> None:
        """Set an object's home (its source's say: the params, a puppet)."""
        if oid in self.objects:
            self.objects[oid].home = pose

    def offset_matrix(self, oid: str) -> np.ndarray | None:
        """The object's offset as a 3D model matrix, or None while it is the
        identity — so the renderer builds the matrix it always did, exactly."""
        obj = self.objects.get(oid)
        if obj is None or obj.offset.is_identity():
            return None
        return obj.offset.model3()

    def reset(self) -> None:
        """Every offset back to the identity, every body still (`world.reset`)."""
        for obj in self.objects.values():
            obj.offset = Pose()
        for b in self.bodies.values():
            b.still()
        self.left = 0.0

    # ---- the orthogonal registries: keyed by a registered object
    def _known(self, oid: str) -> None:
        if oid not in self.objects:
            raise KeyError(f"world: no object {oid!r}")

    def body(self, oid: str, body: Body | None = None) -> Body:
        self._known(oid)
        self.bodies[oid] = body if body is not None else Body()
        return self.bodies[oid]

    def puppet(self, oid: str, puppet: Palm) -> Palm:
        self._known(oid)
        self.puppets[oid] = puppet
        return puppet

    # ---- the frame
    def frame(self, dt: float, palms: dict | None = None) -> None:
        """Once a frame: the puppets, then the physics. `palms` is side →
        (position (3), rotation 3×3) in the world, or None for a hand not seen
        (`app.palms_in_world`)."""
        self.step_puppets(dt, palms or {})
        self.step(dt)

    def step_puppets(self, dt: float, palms: dict) -> None:
        for oid, pup in self.puppets.items():
            obj = self.objects[oid]
            seen = palms.get(pup.side)
            if seen is None:              # no data: writes nothing, the hand is absent
                obj.present, pup.last = False, None
                pup.velocity, pup.spin = np.zeros(4), np.zeros(3)
                continue
            position, rot = seen
            now = Pose.from_matrix3(rot, position)
            if pup.last is not None and dt > 0.0:
                pup.velocity = (now.position - pup.last.position) / dt
                # q and −q are one 3D turn, and `quat_of` keeps no sign from frame to
                # frame: the difference is taken the short way round, or a degree's
                # turn across the sign reads as nearly a whole one
                rel = qnorm(qmul(now.ql, qconj(pup.last.ql)))
                pup.spin = qlog(rel if rel[3] >= 0.0 else -rel) / dt
            else:
                pup.velocity, pup.spin = np.zeros(4), np.zeros(3)
            pup.last = now
            obj.home, obj.present = now, True

    def step(self, dt: float) -> int:
        """The physics: fixed steps of STEP_S for `dt` (at most MAX_STEPS; a
        stall drops the rest), semi-implicit Euler, the quaternions
        renormalized each step. Returns the steps taken."""
        dt = min(max(0.0, float(dt)), MAX_STEPS * STEP_S)
        self.left += dt
        n = min(MAX_STEPS, int(self.left / STEP_S))
        self.left -= n * STEP_S
        moving = [(self.objects[oid], b) for oid, b in self.bodies.items()]
        if not n or not moving:
            return n
        for obj, b in moving:
            off = obj.offset
            p, ql, qr = off.position.copy(), off.ql.copy(), off.qr.copy()
            # drag in closed form a step (exp), so a free body decays at its
            # rate whatever the frame rate; then the position on the new velocity
            k, ka = math.exp(-b.drag * STEP_S), math.exp(-b.angular_drag * STEP_S)
            v, wl, wr = b.velocity, b.spin_l, b.spin_r
            for _ in range(n):
                v, wl, wr = v * k, wl * ka, wr * ka
                p = p + v * STEP_S
                ql = qnorm(qmul(qexp(wl * STEP_S), ql))
                qr = qnorm(qmul(qexp(wr * STEP_S), qr))
            b.velocity, b.spin_l, b.spin_r = v, wl, wr
            obj.offset = Pose(p, ql, qr, off.scale)
        return n


def register(reg, world: World) -> None:
    """`world.reset` on `reg` (anything with `.trigger`): every offset back to
    the identity. A shared meta param: one world, every deck."""
    if f"{GROUP}.reset" in reg:
        return
    # through a lambda, not the bound method: a hot reload re-classes the world
    # (`World.targets`), and the trigger then runs the new `reset`
    reg.trigger(f"{GROUP}.reset", "Reset world", lambda: world.reset(), group=GROUP,
                tip="Every world object back where its source puts it: the shape where "
                    "the camera params say, the hands on the palms. Nothing moves them "
                    "off it yet (plan 59).")
