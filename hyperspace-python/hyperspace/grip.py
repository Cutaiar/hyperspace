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

The params are a shared meta group (`grip`): one world, one grip, every deck
(register row 852's rule), saved in the show, a module preset strip of their
own (the HANDS page), an APC40 knob learnable onto any of them. Off by default.
`grip.clutch` / `grip.shape_clutch` are lane addresses; empty is the default
gate, so it follows `grip.hand`.

Imports only `world`. The registry and the lanes are duck-typed: the host hands
`apply` a `closed(address) -> bool` (`app._step_world`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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
    if not state.on:
        world.joints.pop(shape, None)
        world.bodies.pop(shape, None)
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
    j.shaping = bool(closed(shape_clutch_of(state)))
    j.coupling = float(state.coupling)
    j.inertia, j.shape, j.skater = bool(state.inertia), float(state.shape), bool(state.skater)


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
    """The `grip.*` params on `reg` (the meta controller's): saved in the show,
    learnable (a knob onto the coupling, say)."""
    if f"{GROUP}.on" in reg:
        return
    reg.grip = state

    def setter(key: str, cast):
        return lambda v: setattr(state, key, cast(v))

    reg.toggle(f"{GROUP}.on", "Grip", lambda: state.on, setter("on", bool), group=GROUP,
               tip="Hold the shape in your hand: close the holding hand's clutch near the "
                   "shape and it follows the hand; open it and it flies on. Off: the shape "
                   "stays where it was left (Reset world puts it home).")
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
