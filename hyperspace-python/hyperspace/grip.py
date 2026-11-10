"""The hand rig (plan 60): the shape held by a hand, on plan 59's world.

A 6-DOF spring-damper joint (`world.Joint`) from a hand object to the shape
object, acting while a clutch is closed — by default the same hand's grab
(`hand:<side>.grab`, plan 51's clutch). As it closes the joint captures the
hand-to-shape pose, so nothing jumps; a hand lost opens it.

- **`grip.coupling`** (0–1) is the slider. 1: welded, the shape is the hand's
  pose times the captured one, its velocities the hand's. Lower: a position
  spring and a rotation spring on log(q_target · q̄), acting on the angular
  velocity, their frequency falling geometrically to `world.SPRING_HZ`'s floor
  and their damping ratio with it (`world.spring_of`), loose and bouncy at 0.
- **Let go**, the shape keeps its linear and angular velocity and coasts down
  at `grip.drag`, held to the visible box as the poi's wrist is (`World.box`).
- **`grip.inertia`** on: while a second clutch is closed (by default the other
  hand's grab) the vector between the palms shapes the inertia in the room
  (`world.shaped_inertia`, k `grip.shape`); as it opens the inertia locks into
  the body, which then precesses and nutates (I ω̇ = τ − ω × Iω).
- **`grip.skater`**: a change of inertia keeps the angular momentum, so hands
  apart slow the spin and together speed it up.

The params are a patch group (`grip`): a look's own, each deck's, saved in the
loadable patch, off in one that names none (the owner, 2026-11-10: "this really
should be per preset"). The on-air deck's grip acts on the one world. A new
look — a load writes `grip.on`, a deck switch is another `GripState` — sends a
shape away from home back there first (`Joint.homing`). Its own lanes,
`grip:held` / `flying` / `speed` / `spin` (`lanes`, `publish`), let a look's
routes follow the shape in hand or in flight. `grip.clutch` /
`grip.shape_clutch` are lane addresses; empty is the default gate, so it
follows `grip.hand`.

Imports only `world`. The registry and the lanes are duck-typed: the host hands
`apply` a `closed(address) -> bool` (`app._step_world`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from . import world as worlds

GROUP = "grip"
SIDES = ("left", "right")
DRAG = (0.0, 5.0)        # 1/s: grip.drag's range
SHAPE = (-0.75, 3.0)     # k: grip.shape's range (−: flattened along the palms' line)


@dataclass
class GripState:
    """The grip's settings, what its params read and write."""

    on: bool = False
    hand: int = 1                 # SIDES index: which hand holds
    coupling: float = 0.8
    drag: float = 0.8
    inertia: bool = False
    shape: float = 1.5
    skater: bool = True
    clutch: str = ""              # "" — the holding hand's grab
    shape_clutch: str = ""        # "" — the other hand's grab
    fresh: int = 0                # counts each `grip.on` write: a load, a toggle — a new look

    @property
    def side(self) -> str:
        return SIDES[1 if self.hand else 0]

    @property
    def other(self) -> str:
        return SIDES[0 if self.hand else 1]

    @property
    def default_clutch(self) -> str:
        return f"hand:{self.side}.grab"

    @property
    def default_shape_clutch(self) -> str:
        return f"hand:{self.other}.grab"


def clutch_of(state: GripState) -> str:
    """The holding clutch's address: `grip.clutch`, else the hand's grab."""
    return state.clutch.strip() or state.default_clutch


def shape_clutch_of(state: GripState) -> str:
    """The shaping clutch's address: `grip.shape_clutch`, else the other hand's grab."""
    return state.shape_clutch.strip() or state.default_shape_clutch


def apply(world, state: GripState, closed: Callable[[str], bool]) -> None:
    """Once a frame before `World.frame`: the shape's body and joint as the
    params say, and the two clutches. Off: neither — the offset stays where it
    is. A change of hand lets go (a new joint)."""
    shape = worlds.SHAPE
    if shape not in world:
        return
    key = (id(state), state.fresh)
    fresh = world.grip_key != key        # a look loaded, the grip toggled, a deck switch
    world.grip_key = key
    if not state.on:
        _off(world, shape)
        return
    hand, other = worlds.HANDS[state.side], worlds.HANDS[state.other]
    j = world.joints.get(shape)
    if j is None or j.hand != hand:
        j = world.joint(shape, worlds.Joint(hand, other))
    b = world.bodies.get(shape)
    if b is None:
        b = world.body(shape, worlds.Body(boxed=True))
    b.boxed = True
    b.drag = b.angular_drag = float(state.drag)
    j.closed = bool(closed(clutch_of(state)))
    if fresh and not _home_and_still(world[shape], b):
        j.release()
        j.homing = True                  # the new look starts with the shape at home…
    if j.homing and (j.closed or _home_and_still(world[shape], b)):
        j.homing = False                 # …unless a hand takes it first
    j.shaping = bool(closed(shape_clutch_of(state)))
    j.coupling = float(state.coupling)
    j.inertia, j.shape, j.skater = bool(state.inertia), float(state.shape), bool(state.skater)


def _off(world, shape: str) -> None:
    """The grip off — a patch without it loaded, or its switch turned off: a
    shape still away from home springs back (`Joint.homing`, `world.HOME_HZ`), so a
    throw never leaks into the next look; once home, the body and joint leave the
    registries and nothing steps."""
    obj = world[shape]
    b, j = world.bodies.get(shape), world.joints.get(shape)
    if _home_and_still(obj, b):
        world.joints.pop(shape, None)
        world.bodies.pop(shape, None)
        return
    if j is None:
        j = world.joint(shape, worlds.Joint(worlds.HANDS["right"], worlds.HANDS["left"]))
    if b is None:
        b = world.body(shape, worlds.Body(boxed=True))
    j.release()
    j.homing, j.closed, j.shaping = True, False, False


def _home_and_still(obj, b) -> bool:
    return obj.offset.is_identity() and (b is None or not (b.velocity.any() or b.spin_l.any()))


# ---------------------------------------------------------------- the lanes

SCHEME = "grip"
LANES = ("held", "flying", "speed", "spin")
INDEX = {name: i for i, name in enumerate(LANES)}      # (one dict: the router caches on it)
GATES = [(INDEX["held"], "grip held"), (INDEX["flying"], "grip flying")]
RESTS = [0.0] * len(LANES)
FLYING = 0.05            # world units/s or rad/s: under both, a let-go shape has landed
SPEED_FULL = 4.0         # world units/s: `grip:speed` reads 1 here and over
SPIN_FULL = worlds.MAX_SPIN


def lanes(world, state: GripState) -> list[float] | None:
    """This frame's `grip:*` lanes, None while the grip is off (dormant, as a
    hand away): `held` 1 while the holding clutch has the shape; `flying` 1
    while a let-go shape still moves; `speed`, `spin` the shape's own speed
    in the world and its angular speed, 0–1 of `SPEED_FULL` / `SPIN_FULL` —
    the shape's, not the hand's, so they read on after a throw."""
    shape = worlds.SHAPE
    if not state.on or shape not in world:
        return None
    b, j = world.bodies.get(shape), world.joints.get(shape)
    if b is None or j is None:
        return [0.0, 0.0, 0.0, 0.0]
    held = j.rel is not None and not j.homing
    v = float(np.linalg.norm(b.velocity[:3])) * abs(float(world[shape].home.scale))
    w = float(np.linalg.norm(b.spin_l))
    flying = not held and not j.homing and (v > FLYING or w > FLYING)
    return [1.0 if held else 0.0, 1.0 if flying else 0.0,
            min(1.0, v / SPEED_FULL), min(1.0, w / SPIN_FULL)]


def publish(router, world, state: GripState | None) -> None:
    """The `grip:*` lanes onto `router` for the next frame's routes: their
    names, labels, gates and rests once, the vector every frame (None, the
    grip off: its rows let go). After the world's step, so a route reads
    the frame before's shape, as the hands' lanes read the frame's poll."""
    if router is None:
        return
    names = getattr(router, "names", None)
    if names is not None and names.get(SCHEME) is not INDEX:
        names[SCHEME] = INDEX
        router.labels[SCHEME] = list(LANES)
        router.gates[SCHEME] = GATES
        router.rests[SCHEME] = RESTS
    router.feed(SCHEME, None if state is None else lanes(world, state))


def lane_closed(router, address: str) -> bool:
    """Is the gate at `address` closed this frame — a lane reading ≥ 0.5, as
    `Router.gated` reads a row's `when`? Not live, unknown or NaN: open."""
    if router is None or not address:
        return False
    scheme, i = router.lane(address)
    vec = router.feeds.get(scheme)
    if vec is None or not 0 <= i < len(vec):
        return False
    u = float(vec[i])
    return u >= 0.5          # NaN (a hand away) reads open


def register(reg, state: GripState) -> None:
    """The `grip.*` params on `reg` (a deck's: a patch group, saved in the
    loadable patch; the continuous ones routable). `reg.grip` is the state."""
    if f"{GROUP}.on" in reg:
        return
    reg.grip = state

    def setter(key: str, cast):
        return lambda v: setattr(state, key, cast(v))

    def set_on(v) -> None:
        state.on = bool(v)
        state.fresh += 1          # a load writes it too: the next look starts from home

    reg.toggle(f"{GROUP}.on", "Grip", lambda: state.on, set_on, group=GROUP,
               tip="This look's grip: close the holding hand's clutch near the shape and "
                   "it follows the hand; open it and it flies on. Saved with the look; off, "
                   "or a new look, and the shape springs home.")
    reg.enum(f"{GROUP}.hand", "Hand", lambda: state.hand, setter("hand", int), list(SIDES),
             group=GROUP, tip="Which hand holds the shape; the other shapes its inertia.")
    reg.continuous(f"{GROUP}.coupling", "Coupling", lambda: state.coupling,
                   setter("coupling", float), lo=0.0, hi=1.0, group=GROUP,
                   tip="1: welded to the hand. Lower: a spring, looser and bouncier down "
                       "to about 0.3 Hz at 0, for where it sits and how it turns.")
    reg.continuous(f"{GROUP}.drag", "Drag", lambda: state.drag, setter("drag", float),
                   lo=DRAG[0], hi=DRAG[1], group=GROUP,
                   tip="How fast a shape let go slows, moving and turning (1/s). 0 coasts on.")
    reg.toggle(f"{GROUP}.inertia", "Shaped inertia", lambda: state.inertia,
               setter("inertia", bool), group=GROUP,
               tip="Off: even inertia, no gyroscopic effect. On: close the other hand's "
                   "clutch and the line between your palms shapes it; open it and it "
                   "locks into the shape, which then precesses as it turns.")
    reg.continuous(f"{GROUP}.shape", "Shape", lambda: state.shape, setter("shape", float),
                   lo=SHAPE[0], hi=SHAPE[1], group=GROUP,
                   tip="How strongly the palms' line shapes the inertia: above 0 heavier "
                       "about that line, below 0 lighter. The ratio stays within 0.25–4.")
    reg.toggle(f"{GROUP}.skater", "Skater", lambda: state.skater, setter("skater", bool),
               group=GROUP,
               tip="Keep the spin's momentum when the inertia changes: hands apart slow "
                   "it, together speed it up. Off: the spin stays as it is.")
    reg.text(f"{GROUP}.clutch", "Clutch", lambda: state.clutch, setter("clutch", str),
             group=GROUP, tip="The holding gate, a lane address (hand:right.pinch.index, "
                              "pad:A). Empty: the holding hand's grab.")
    reg.text(f"{GROUP}.shape_clutch", "Shape clutch", lambda: state.shape_clutch,
             setter("shape_clutch", str), group=GROUP,
             tip="The shaping gate, a lane address. Empty: the other hand's grab.")
