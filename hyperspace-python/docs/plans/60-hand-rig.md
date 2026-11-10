# Plan 60: the hand rig — coupling, precession, the skater effect

**Status: built (2026-11-10).** `hyperspace/rig.py` (the params, the clutches),
the joint and the rigid body in `hyperspace/world.py`, the HANDS page's rig
section, the turned depth of row 856 (`geometry.turned_depth`); tests
`tests/test_rig.py`; register rows 857–866, hand checks 661–667. Built on plan
59 as merged (#442), with the amendments in §10. Plans 61 and 62 are not needed.

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

## 10. Amendments, from plan 59 as it merged (2026-11-10)

Read against `world.py` and register rows 851–856 after #442 merged. Each is
built and has a register row.

1. **The joint works in the offset's terms** (row 858). The shape is drawn as
   home ∘ offset (row 853), the home being `camera.pan` and `camera.zoom` with
   no turn; the hands are in the world. The joint captures hand → the pose
   drawn, and pulls the offset to home⁻¹ ∘ hand ∘ rel. The springs are
   mass-normalized (a frequency and a damping ratio), so the zoom changes
   nothing of how they feel.
2. **Yaw and pitch stay outside the pose** (row 864). `camera.yaw` / `.pitch`
   turn the points on the CPU before the offset, so a `turn` row turns the
   shape about its own axes on top of the rig's turn, and the locked inertia
   lives in the offset's frame.
3. **Fit and the 3D lattices take no offset** (row 851 stands; row 864): the
   rig moves nothing there. A flat field with Fit off moves as one figure.
4. **Row 856, the depth of a turned shape, is built** (row 863): while the
   offset is not the identity, a 3D shape's depth cue and painter sort read
   its depth after the offset's turn. A 4D shape keeps its w. The identity
   offset is unchanged, so are the goldens.
5. **`world.py` imports nothing**, so the gates and the box arrive from the
   host: `rig.apply` takes a `closed(address)` that `app._step_world` reads
   from the on-air router's lanes (the debounced grab, plan 51), and the
   renderer sets `World.box` from the scene drawn (`poi.box_for`, row 862).
   The box holds the shape's drawn centre, in the world, grown to take its
   home in.
6. **The step is rebuilt, not extended** (rows 860, 865). A body with a joint
   or an uneven inertia steps as a rigid body, its angular momentum carried
   (so a free body keeps L exactly); the joint's clutch, the inertia shaping
   and the skater run once a frame before the steps; a plan 59 free body steps
   as before. `World.joints` holds a `Joint` keyed by the shape, naming its
   hand. `world.reset` also lets go and evens the inertia.
7. **The hand is blended across the steps** (row 859): read once a frame, it
   moves from last frame's pose to this one's across the frame's 960 Hz steps.
8. **The params are a shared meta group, not per deck** (row 857). The review
   of plan 59 offered per deck, read from the deck on air; but a per-deck meta
   param never persists (row 746), so it could have no preset strip, which
   §4 asks for. One rig on one world: `rig.*` is shared meta, saved in the
   show. A meta param takes no route (row 775), so "a knob learned onto it"
   is a desk row that sets it.
9. **§7 is dropped** (row 866): moving the poi changes what a save holds.

