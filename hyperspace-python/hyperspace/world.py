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

  bodies    `Body`: velocity, drag and an inertia fixed in the body.
  joints    `Joint` (plan 60, the hand rig): a 6-DOF spring-damper from a
            hand object to the body's object, acting while its clutch is
            closed, and the gate that shapes the body's inertia.
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

**The rig's physics** (plan 60; `grip.py` sets the joint from its params and
gates). A body with a joint is a rigid body: its angular momentum L is what
carries over, ω = I⁻¹ L with I = R · I_body · Rᵀ, so an uneven inertia fixed
in the body precesses and nutates (I ω̇ = τ − ω × Iω, integrated as L) and a
change of inertia keeps L (the skater) or ω. While the joint's clutch is
closed the body is pulled to the hand's pose times the pose captured as it
closed (`Joint.rel`), welded at `coupling` 1, else by a spring whose frequency
and damping ratio fall with the coupling; let go, it coasts at its drag. Its
position is held to the visible box (`World.box`, as the poi's): the physics
runs on past the edge (`Body.place`) and the drawn shape does not.

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
# plan 60, the hand rig's joint: the spring's natural frequency (Hz) at coupling 0
# and just under 1 (geometric between; 1 is welded), its damping ratio
# (linear between: loose and bouncy at the bottom)
SPRING_HZ = (0.3, 30.0)
SPRING_ZETA = (0.2, 1.0)
MAX_SPIN = 2.0 * math.pi * 6.0      # rad/s: angular speed held under six turns a second
INERTIA_RATIO = (0.25, 4.0)         # a shaped inertia's principal ratio, clamped
HOME_HZ = 2.5                       # a grip turned off springs its body home: critically
                                    # damped at this, settled in about 0.3 s
SETTLED = 1e-4                      # …and within this (units, rad, per second) it is home
INERTIA_RATE = 6.0                  # how fast an inertia may change: its log, a second
SPAN = 4.0                          # the palms' spread, world units, that shapes fully
                                    # with no box (else the box's width)


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


def rot3(q) -> np.ndarray:
    """The 3×3 rotation of unit quaternion `q`: R @ v is q · v · q̄."""
    x, y, z, w = (float(c) for c in q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def short(q, near) -> np.ndarray:
    """`q` or −q (one 3D turn), whichever is nearer `near`."""
    return q if float(np.dot(q, near)) >= 0.0 else -q


def spring_of(coupling: float) -> tuple[float, float]:
    """(ωn rad/s, ζ) of the joint's spring at `coupling` in [0, 1): the
    frequency geometric from SPRING_HZ[0] to [1], the damping ratio linear."""
    c = min(1.0, max(0.0, float(coupling)))
    lo, hi = SPRING_HZ
    return 2.0 * math.pi * lo * (hi / lo) ** c, SPRING_ZETA[0] + (SPRING_ZETA[1] - SPRING_ZETA[0]) * c


def shaped_inertia(d, k: float, span: float = SPAN) -> np.ndarray:
    """The inertia in the room from the vector `d` between the palms (plan 60
    §2): 𝟙 + k · m · n nᵀ, n its direction and m its length over `span`
    (at most 1), the principal ratio clamped to INERTIA_RATIO. No length:
    even."""
    d = np.asarray(d, dtype=np.float64)[:3]
    ln = float(np.linalg.norm(d))
    if not ln > 1e-9 or not math.isfinite(ln):
        return np.eye(3)
    n = d / ln
    m = min(1.0, ln / max(float(span), 1e-9))
    lam = min(INERTIA_RATIO[1], max(INERTIA_RATIO[0], 1.0 + float(k) * m))
    return np.eye(3) + (lam - 1.0) * np.outer(n, n)


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
    """A body (bodies registry): it moves its object's offset. `velocity`
    (4, world units/s), `spin_l` / `spin_r` the angular velocity of qL and qR
    (rad/s, rotation vectors in the world's axes; equal for a 3D body,
    `Body.spin3`), each decaying at its drag (1/s). `inertia` is fixed in the
    body (3×3, the identity even): stepped as a rigid body when it is uneven or
    a joint holds the body (plan 60). `boxed`: held to `World.box`, the
    physics' own position in `place` (offset units, None until it first steps)."""

    mass: float = 1.0
    inertia: np.ndarray = field(default_factory=lambda: np.eye(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(4))
    spin_l: np.ndarray = field(default_factory=lambda: np.zeros(3))
    spin_r: np.ndarray = field(default_factory=lambda: np.zeros(3))
    drag: float = 0.0
    angular_drag: float = 0.0
    boxed: bool = False
    place: np.ndarray | None = None

    def spin3(self, omega) -> Body:
        """A 3D angular velocity (rad/s about x, y, z): both halves alike."""
        self.spin_l = np.asarray(omega, dtype=np.float64).copy()
        self.spin_r = self.spin_l.copy()
        return self

    def still(self) -> None:
        self.velocity = np.zeros(4)
        self.spin_l, self.spin_r = np.zeros(3), np.zeros(3)
        self.place = None

    def even(self) -> bool:
        i = self.inertia
        return bool(np.allclose(i, i[0, 0] * np.eye(3), rtol=0.0, atol=1e-12))


@dataclass
class Joint:
    """The hand rig's joint (plan 60), keyed by the body's object: a 6-DOF
    spring-damper from hand object `hand` to it, acting while `closed` (the
    clutch, set each frame by `grip.apply`; a hand not present opens it).
    `rel` is hand → the drawn object, captured as it closes (None: open);
    `prev` the hand's pose the frame before, blended across the fixed steps.
    `coupling` 1 is welded. The inertia: `inertia` False is even; True, it is
    shaped while `shaping` (the second clutch) by the vector from `hand` to
    `other` (`shaped_inertia`, k `shape`), and locked into the body when it
    opens; `skater` keeps L, not ω, when it changes."""

    hand: str
    other: str
    closed: bool = False
    coupling: float = 1.0
    rel: Pose | None = None
    prev: Pose | None = None
    shaping: bool = False
    inertia: bool = False
    shape: float = 1.0
    skater: bool = True
    homing: bool = False          # the grip off: spring the body home (`HOME_HZ`)

    def release(self) -> None:
        self.rel = self.prev = None


@dataclass
class Palm:
    """A puppet: a tracked palm sets its object's home each frame. `side`
    "left" / "right"; `velocity` and `spin` (3D, rad/s) its frame-to-frame
    difference, zero on the frame it arrives — what the hand rig's target moves
    at (plan 60, `World._target`), never fed into a body as such (the puppet
    sets the home; a body moves the offset)."""

    side: str
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(4))
    spin: np.ndarray = field(default_factory=lambda: np.zeros(3))
    last: Pose | None = None


class World:
    """The drawn objects and the registries keyed by them (module docstring)."""

    def __init__(self) -> None:
        self.objects: dict[str, WorldObject] = {}
        self.bodies: dict[str, Body] = {}
        self.joints: dict[str, Joint] = {}        # plan 60, the hand rig
        self.puppets: dict[str, Palm] = {}
        self.clip: dict[str, object] = {}         # no consumer yet
        self.left = 0.0                           # time not yet stepped (< STEP_S)
        # half the box (x, y, z, world units about the screen's centre) a boxed
        # body's object is drawn in (`poi.box_for`, set by the renderer); None: no box
        self.box: tuple[float, float, float] | None = None
        self.note = ""                            # the last NaN reset, said once
        # (plan 60) whose grip, and which of its looks, last set the shape's joint
        # (`grip.apply`): a new one sends the shape home before it acts
        self.grip_key: tuple | None = None

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
        for j in self.joints.values():
            out.append((j, "world", "Joint"))
            out += [(p, "world", "Pose") for p in (j.rel, j.prev) if p is not None]
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
        """Every offset back to the identity, every body still, its inertia
        even, every joint let go (`world.reset`; a clutch still closed takes
        hold again from home)."""
        for obj in self.objects.values():
            obj.offset = Pose()
        for b in self.bodies.values():
            b.still()
            b.inertia = np.eye(3)
        for j in self.joints.values():
            j.release()
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

    def joint(self, oid: str, joint: Joint) -> Joint:
        self._known(oid)
        self.joints[oid] = joint
        return joint

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
        renormalized each step. First the joints' frame (`_joints`: a clutch
        closing captures, one opening lets go; the inertia shaped). A body with
        no joint and an even inertia steps as plan 59's free body; any other as
        a rigid body (`_rigid`). Returns the steps taken."""
        dt = min(max(0.0, float(dt)), MAX_STEPS * STEP_S)
        self.left += dt
        n = min(MAX_STEPS, int(self.left / STEP_S))
        self.left -= n * STEP_S
        self._joints(n * STEP_S)
        if not n or not self.bodies:
            return n
        for oid, b in self.bodies.items():
            obj = self.objects[oid]
            j = self.joints.get(oid)
            if j is None and b.even():
                self._free(obj, b, n)
            else:
                self._rigid(obj, b, j, n)
            if not self._finite(obj, b):
                self._nan(oid, obj, b, j)
        return n

    # ---- the steps
    def _start(self, obj: WorldObject, b: Body) -> np.ndarray:
        """Where the physics has the body: its own place if boxed, else the offset's."""
        return (b.place.copy() if b.boxed and b.place is not None
                else obj.offset.position.copy())

    def _land(self, obj: WorldObject, b: Body, p, ql, qr) -> None:
        """The offset from the physics' position and turn, held to the box."""
        if b.boxed:
            b.place = np.asarray(p, dtype=np.float64).copy()
            p = self._boxed(obj, p)
        obj.offset = Pose(p, ql, qr, obj.offset.scale)

    def _boxed(self, obj: WorldObject, p) -> np.ndarray:
        """Offset position `p` with the drawn centre (home ∘ it) held to the box,
        inset across the screen by the shape's own radius (its unit circumradius
        times the home's scale, the zoom), so a shape parked at the edge stays
        whole on screen — a box grown to take the home in, so a home outside it
        is not pulled."""
        box = self.box
        if box is None:
            return np.asarray(p, dtype=np.float64)
        home = obj.home
        at = home.apply(np.asarray(p, dtype=np.float64))
        h = home.position
        r = abs(float(home.scale))
        half = (max(box[0] - r, 0.0), max(box[1] - r, 0.0), box[2])
        lo = np.array([min(-half[0], h[0]), min(-half[1], h[1]), min(-half[2], h[2])])
        hi = np.array([max(half[0], h[0]), max(half[1], h[1]), max(half[2], h[2])])
        held = at.copy()
        held[:3] = np.minimum(hi, np.maximum(lo, at[:3]))
        if np.array_equal(held, at):
            return np.asarray(p, dtype=np.float64)
        return home.inverse().apply(held)

    def _free(self, obj: WorldObject, b: Body, n: int) -> None:
        """Plan 59's free body: velocity and spin under drag."""
        off = obj.offset
        p, ql, qr = self._start(obj, b), off.ql.copy(), off.qr.copy()
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
        self._land(obj, b, p, ql, qr)

    def _held(self, obj: WorldObject, j: Joint | None):
        """The joint's hand, if it holds `obj` this frame: (hand now, hand a
        frame ago, its velocity (3), its spin (3)), else None."""
        if j is None or j.rel is None:
            return None
        hand = self.objects.get(j.hand)
        if hand is None or not hand.present:
            return None
        pup = self.puppets.get(j.hand)
        v = pup.velocity[:3] if pup is not None else np.zeros(3)
        w = pup.spin if pup is not None else np.zeros(3)
        return hand.home, (j.prev if j.prev is not None else hand.home), v, w

    @staticmethod
    def _target(j: Joint, home_inv: Pose, prev: Pose, now: Pose, f: float,
                dq, v_h, w_h, q_near):
        """The joint's target at fraction `f` of the frame, in the offset's terms:
        (position (4), turn q, velocity (4), spin (3)). The hand is blended from
        `prev` to `now` (`dq` the turn between, the short way), times `rel`."""
        rel = j.rel if j.rel is not None else Pose()             # (held: never None)
        p_h = prev.position + f * (now.position - prev.position)
        q_h = qnorm(qmul(qexp(f * dq), prev.ql))
        at = p_h + turn3(q_h, rel.position)                      # the target in the world
        q_t = short(qnorm(qmul(home_inv.ql, qmul(q_h, rel.ql))), q_near)
        x_t = home_inv.apply(at)
        # the hand's own velocity, and its turn carrying the shape round it
        v_w = np.zeros(4)
        v_w[:3] = v_h + np.cross(w_h, (at - p_h)[:3])
        v_t = home_inv.scale * home_inv.turn(v_w)
        w_t = rot3(home_inv.ql) @ w_h
        return x_t, q_t, v_t, w_t

    def _rigid(self, obj: WorldObject, b: Body, j: Joint | None, n: int) -> None:
        """A rigid body (3D: qL = qR): its angular momentum L in the world is
        what carries over, ω = (R I_body Rᵀ)⁻¹ L; a joint holding it pulls it
        to its target, welded or by its spring; free, it coasts at its drag."""
        off = obj.offset
        p, q = self._start(obj, b), off.ql.copy()
        v, w = b.velocity.copy(), b.spin_l.copy()
        ib = b.inertia
        held = self._held(obj, j)
        if j is not None and j.homing:
            self._home(obj, b, n)
            return
        if held is not None and j is not None:
            now, prev, v_h, w_h = held
            home_inv = obj.home.inverse()
            dq = qlog(short(qnorm(qmul(now.ql, qconj(prev.ql))), np.array(_ID)))
            if j.coupling >= 1.0:                       # welded: the target, exactly
                x_t, q_t, v_t, w_t = self._target(j, home_inv, prev, now, 1.0,
                                                  dq, v_h, w_h, q)
                b.velocity, b.place = v_t, x_t.copy()
                b.spin3(_held_spin(w_t))
                self._land(obj, b, x_t, q_t, q_t)
                j.prev = now
                return
            wn, zeta = spring_of(j.coupling)
            k, c = wn * wn, 2.0 * zeta * wn
            r = rot3(q)
            mom = r @ ib @ r.T @ w
            for i in range(n):
                x_t, q_t, v_t, w_t = self._target(j, home_inv, prev, now, (i + 1) / n,
                                                  dq, v_h, w_h, q)
                v = v + (k * (x_t - p) + c * (v_t - v)) * STEP_S
                p = p + v * STEP_S
                err = qlog(short(qnorm(qmul(q_t, qconj(q))), np.array(_ID)))
                mom = mom + (k * err + c * (w_t - w)) * STEP_S      # the torque, I₀ = 1
                r = rot3(q)
                w = _spin_of(r, ib, mom)
                mom = r @ ib @ r.T @ w                              # (held under MAX_SPIN)
                q = qnorm(qmul(qexp(w * STEP_S), q))
            j.prev = now
        else:
            if j is not None:
                j.prev = None
            kd, ka = math.exp(-b.drag * STEP_S), math.exp(-b.angular_drag * STEP_S)
            r = rot3(q)
            mom = r @ ib @ r.T @ w
            for _ in range(n):
                v = v * kd
                p = p + v * STEP_S
                mom = mom * ka
                r = rot3(q)
                w = _spin_of(r, ib, mom)
                mom = r @ ib @ r.T @ w
                q = qnorm(qmul(qexp(w * STEP_S), q))
        r = rot3(q)
        w = _spin_of(r, ib, mom)
        b.velocity = v
        b.spin3(w)
        self._land(obj, b, p, q, q)

    def _home(self, obj: WorldObject, b: Body, n: int) -> None:
        """A grip turned off (plan 60): the body springs home, critically damped at
        HOME_HZ, its inertia even; once within SETTLED of home and still, the
        offset is exactly the identity again (the renderer's matrix of before)."""
        p, q = self._start(obj, b), obj.offset.ql.copy()
        v, w = b.velocity.copy(), b.spin_l.copy()
        wn = 2.0 * math.pi * HOME_HZ
        k, c = wn * wn, 2.0 * wn
        ident = np.array(_ID)
        for _ in range(n):
            v = v + (-k * p - c * v) * STEP_S
            p = p + v * STEP_S
            err = qlog(short(qnorm(qconj(q)), ident))
            w = _held_spin(w + (k * err - c * w) * STEP_S)
            q = qnorm(qmul(qexp(w * STEP_S), q))
        b.inertia = np.eye(3)
        if (max(float(np.abs(p).max()), float(np.linalg.norm(qlog(short(q, ident)))),
                float(np.abs(v).max()), float(np.abs(w).max())) < SETTLED):
            obj.offset = Pose()
            b.still()
            return
        b.velocity = v
        b.spin3(w)
        self._land(obj, b, p, q, q)

    # ---- the joints' frame
    def _joints(self, t: float) -> None:
        """Once a frame, before the steps: each joint's clutch (closing captures
        hand → the drawn object, so nothing jumps; opening, or its hand lost,
        lets go and the body keeps its velocities), then its inertia (`_shape`)."""
        for oid, j in self.joints.items():
            obj, b = self.objects.get(oid), self.bodies.get(oid)
            hand = self.objects.get(j.hand)
            if obj is None or b is None:
                continue
            acting = j.closed and hand is not None and hand.present
            if not acting:
                if j.rel is not None:
                    j.release()
            elif j.rel is None and hand is not None:
                # (its scale is the zoom's, which the target never reads: the
                # hand moves and turns the shape, the home sizes it)
                j.rel = hand.home.inverse().compose(obj.pose)
                j.prev = hand.home
                b.place = obj.offset.position.copy()   # the physics from what is drawn
            self._shape(obj, b, j, t)

    def _shape(self, obj: WorldObject, b: Body, j: Joint, t: float) -> None:
        """The body's inertia this frame (plan 60 §2–3). Off: even. While the
        shaping clutch is closed with both hands seen: `shaped_inertia` of the
        palms' vector, in the room, taken into the body's frame; else what it
        holds stays locked. A change goes at most INERTIA_RATE a second, so it
        cannot spike; `skater` keeps L across it (ω = I⁻¹ L), else ω."""
        if not j.inertia:
            want = np.eye(3)
        else:
            hand, other = self.objects.get(j.hand), self.objects.get(j.other)
            if not (j.shaping and hand is not None and other is not None
                    and hand.present and other.present):
                return
            span = 2.0 * self.box[0] if self.box is not None else SPAN
            room = shaped_inertia(other.home.position - hand.home.position, j.shape, span)
            r = rot3(obj.offset.ql)
            want = r.T @ room @ r
        cur = b.inertia
        d = want - cur
        if not np.abs(d).max() > 1e-12:
            return
        size = float(np.linalg.norm(np.linalg.solve(cur, d)))
        room_t = INERTIA_RATE * max(float(t), 0.0)
        if size > room_t:
            if room_t <= 0.0:
                return
            d = d * (room_t / size)
        new = cur + d
        new = 0.5 * (new + new.T)
        if j.skater:
            r = rot3(obj.offset.ql)
            b.spin3(_spin_of(r, new, r @ cur @ r.T @ b.spin_l))
        b.inertia = new

    # ---- safety
    def _finite(self, obj: WorldObject, b: Body) -> bool:
        off = obj.offset
        return all(np.isfinite(a).all() for a in (off.position, off.ql, off.qr, b.velocity,
                                                   b.spin_l, b.spin_r, b.inertia))

    def _nan(self, oid: str, obj: WorldObject, b: Body, j: Joint | None) -> None:
        """A NaN anywhere: the body home and still, its inertia even, its joint
        let go; said once (`note`, stderr)."""
        obj.offset = Pose()
        b.still()
        b.inertia = np.eye(3)
        if j is not None:
            j.release()
        if not self.note:
            import sys

            self.note = f"world: {oid} went non-finite; put home"
            print(self.note, file=sys.stderr)


def turn3(q, v) -> np.ndarray:
    """`v` (4, w kept) turned by the 3D quaternion `q`."""
    out = np.asarray(v, dtype=np.float64).copy()
    out[:3] = rot3(q) @ out[:3]
    return out


def _spin_of(r, ib, mom) -> np.ndarray:
    """ω = (R I_body Rᵀ)⁻¹ L, held under MAX_SPIN."""
    w = r @ np.linalg.solve(ib, r.T @ mom)
    return _held_spin(w)


def _held_spin(w) -> np.ndarray:
    s = float(np.linalg.norm(w))
    return w * (MAX_SPIN / s) if s > MAX_SPIN else w


def register(reg, world: World) -> None:
    """`world.reset` on `reg` (anything with `.trigger`): every offset back to
    the identity. A shared meta param: one world, every deck."""
    if f"{GROUP}.reset" in reg:
        return
    # through a lambda, not the bound method: a hot reload re-classes the world
    # (`World.targets`), and the trigger then runs the new `reset`
    reg.trigger(f"{GROUP}.reset", "Reset world", lambda: world.reset(), group=GROUP,
                tip="Every world object back where its source puts it: the shape where "
                    "the camera params say, the hands on the palms — wherever a grip "
                    "left it, still, its inertia even.")
