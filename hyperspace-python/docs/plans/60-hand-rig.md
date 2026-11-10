# Plan 60: the hand rig — coupling, precession, the skater effect

**Status: planned (2026-11-10).** Needs plan 59 merged: it adds joints and
inertia to plan 59's world. Plans 61 and 62 are not needed.

The owner, 2026-11-10: *a slider that controls the momentum damping of the
geometry the hands are rigged to. At maximum damping, the geometry is fixed
directly to the tracking data. As the damping weakens, it keeps its velocity on
all six axes, with both rotational and linear energy kept. If I swing my
hands around wildly on low damping, the geometry should be almost like a spring
connected to my hands for position, and like gyroscopic springs for rotation.*

The precession, and the skater effect, are the owner's picks from the same
conversation: *inertia frozen into the body, controlled with a gesture-based
clutch*, and *the skater effect as a separate thing*.

## 1. The joint

A 6-DOF spring-damper joint (plan 59's `joints` registry) between a hand
object and the shape object.

- **Clutch:** the joint acts while its gate is closed. By default the gate is
  the same hand's grab (`hand:<side>.grab`), the plan 51 clutch. When it
  closes, the joint captures the hand-to-shape relative pose, so nothing jumps.
  A lost hand opens the clutch (plan 51 §5's rule).
- **Coupling** (`rig.coupling`, 0–1) is the slider:
  - **1, welded:** the shape's pose is the hand's pose times the captured
    relative pose, exactly, and its velocities are taken from the hand.
  - **Below 1:** a position spring and a rotation spring toward that target.
    Coupling sets the natural frequency on a log scale (from welded down to
    about 0.3 Hz), with the damping ratio falling as it does, so it is loose
    and bouncy at the bottom.
  - **Rotation spring:** the error is `log(q_target · q̄)`, a 3-vector because
    every pose is in the qL = qR case. Torque = k · error − c · (ω − ω_hand).
    It acts on the angular velocity vector, not on Euler angles, so turns
    combine correctly and there is no gimbal problem.
- **Release:** the joint lets go and the body keeps its linear and angular
  velocity, slowed by `rig.drag` (linear and angular). You can throw it. It is
  held to the visible box as the poi's wrist is (`poi.box_for`): the physics
  runs on past the edge and the shape does not.
- **The `turn` rows still work.** They write the shape's home pose (the
  `camera.*` params) and the rig writes its offset, so the two compose.

## 2. Inertia, shaped by the hands

Gyroscopic effects (precession, nutation) come from ω × Iω, which exists only
when uneven inertia is fixed **to the body** and turns with it. So the inertia
is shaped in the room and then frozen into the body:

- **Inertia clutch:** a second gate. By default it is the **other** hand's
  grab, so one hand holds the shape and the other shapes it.
- **While the inertia clutch is closed**, the vector between the two palms sets
  the inertia in the room: n its direction (heading and depression), m its
  length, normalized by the calibrated box. I = I₀ · (𝟙 + k · m · n nᵀ), with
  k = `rig.shape` (negative: flattened along n; positive: elongated). The
  ratio between the principal inertias is clamped to [0.25, 4].
- **When it opens**, the inertia locks into the body's frame,
  I_body = Rᵀ · I · R, and from then on the body is a true rigid body:
  I ω̇ = τ − ω × Iω in the body frame. Precession under the joint's torque, and
  when free, nutation.
- **`rig.inertia`** off gives even inertia: no gyroscopic term at all.
- **A vector gives a body symmetric about one axis**, so it precesses cleanly
  but never does the unstable "wingnut" tumble, which needs three different
  inertias. Using the shaping hand's palm normal as a second axis would give
  that. It is a follow-on, not in this plan.

## 3. The skater effect

`rig.skater` (on by default): when the inertia changes, **angular momentum is
conserved**, not angular velocity. Each step, L = I ω carries over and ω = I⁻¹ L.
So while the inertia clutch is closed, moving your hands apart slows the
spin and bringing them together speeds it up. This changes the energy, as it
does for a real skater. Off: ω carries over and only the inertia changes.

## 4. Params

All in a `rig` group, so the library's preset strip saves a setup and an APC40
knob can be learned onto any of them.

| Param | What |
| --- | --- |
| `rig.on` | The rig acts at all (off: the world's offset stays where it is) |
| `rig.hand` | Which hand holds: left or right |
| `rig.coupling` | 0–1, the slider (1 welded) |
| `rig.drag` | Linear and angular, how fast a released shape coasts down |
| `rig.inertia` | Off (even) or shaped by the hands |
| `rig.shape` | k, how strongly the hands' vector shapes the inertia (signed) |
| `rig.skater` | Conserve angular momentum when inertia changes |

`rig.clutch` and `rig.shape_clutch` hold the two gates as lane addresses
(defaults as above), so a preset can pick a pinch or a button instead.

## 5. Safety

The physics runs at plan 59's fixed step. Angular speed is clamped (a few turns
a second, a constant). An inertia change too large in one step is spread over
several, so the skater effect cannot spike. A NaN anywhere resets the body to
its home and logs it once.

## 6. Tests

All tape-driven (`hands/tape.py`) or pure, nothing on a real sensor:

- **Welded:** with coupling 1 the shape's pose equals the hand's pose times
  the captured offset, every frame.
- **No jump:** closing the clutch at any pose moves nothing on that frame.
- **Coasting:** a release at known velocity decays at the drag's closed-form
  rate, the same at 30, 60 and 144 fps.
- **Spring:** a step of the hand settles in the time the coupling's frequency
  and damping ratio predict.
- **Precession:** a torque-free body symmetric about one axis, spinning
  slightly off that axis, precesses at the analytic rate
  Ω = (I₃ − I₁) / I₁ · ω₃.
- **Skater:** halving the inertia doubles ω, and L is unchanged.
- **Even inertia** gives no gyroscopic term (ω constant when free and undragged).

## 7. Optional item: poi on the world

Move `poi.py`'s string and weight onto plan 59's world as a distance joint plus
gravity, keeping its behaviour (`tests/test_poi*.py` pass unchanged). Separate
commit; drop it if it grows.

## 8. Out of scope

4D inertia (a 6×6 over the six planes), three different inertias (the follow-on
above), and two hands holding one shape at once.

## 9. Hand checks

Next free numbers and group in `11-hand-checks.md`. On the real sensor: the feel
of the coupling's range, whether a throw reads, whether precession is visible
on the shapes, whether the skater effect is playable, and which gates suit the
tracker best (plan 51's check 518 asked the same of the clutch).
