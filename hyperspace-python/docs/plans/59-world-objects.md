# Plan 59: world objects

**Status: planned (2026-11-10).** The first of four separate efforts (59–62). It
needs nothing else, and plans 60 and 61 build on it. Each plan is its own branch and PR.

| Plan | Effort | Size | Needs |
| --- | --- | --- | --- |
| **59** | World-object registry: a 3D world that holds 4D objects | S | — |
| 60 | Hand rig: coupling, precession, skater effect | S–M | 59 |
| 61 | Unified 4D world, field copies stay in 3D | M | 59 |
| 62 | 4D projection in the vertex shader | L | 61 |

The owner, 2026-11-10: *when the hands are part of the scene, they should
behave like any other geometry, puppeteered by the tracking data.* And:
*a registry of world objects, decoupled from any physics they take part in.
Registering an object as a physics object, or as a clippable one, is an
orthogonal registry. A world object is a thing that is drawn in the scene.*

## 1. Why

The hands and the shape already share one scene and one eye (plan 26 A2/A3).
But nothing models them as objects:

- **The shape's pose is five loose params**: `camera.yaw`, `camera.pitch`,
  `camera.pan.x/y` and `camera.zoom`. Despite the names they are not a
  camera: they are the shape's 3D orientation (as Euler angles) and its world
  placement (`geometry.model_matrix`). It has no z, no roll and no velocity.
- **The hands' pose** feeds only the ghost drawing (`ghost.pose`) and control
  lanes. It never meets the shape as an object.
- **Every experiment has its own physics** and writes its own subset of those
  params: `poi.py` (string and weight, fixed step, "home + offset" on pan/zoom),
  `totem.py` (gyro into `rot.phase.*`), the `turn` rows (plan 51 O2) and the
  pad stick orbit.

## 2. What this plan builds

### 2.1 The pose

`world.Pose`: a **4-vector position**, a **pair of unit quaternions (qL, qR)**
and a scale. A point v, read as a quaternion with w as its real part, turns as
`qL · v · q̄R`.

- **3D is the special case qL = qR.** That fixes w and turns x, y, z exactly as
  the ordinary 3D quaternion qL does. Every object in this plan is in that case,
  with w = 0, because the world stays 3D.
- **Storing the general 4D form now** means plan 61 can switch to a 4D world
  without changing any stored pose.
- **Helpers:** compose, inverse, apply to points, the 4×4 rotation matrix, the
  3D homogeneous model matrix, log/exp (for springs, plan 60), slerp, and
  renormalize.
- **Why this form:** it composes in about half the multiplies of a 4×4
  matrix, renormalizes by normalizing two 4-vectors, and integrates angular
  velocity as the familiar 3D quaternion update done twice. The renderer
  still gets a matrix, built once per object per frame.

### 2.2 The registries

All in `hyperspace/world.py`: pure, no GL, importing nothing from the host
(the same rule as `hands/`).

- **`World`**: the drawn things. Each `WorldObject` has an id, a kind
  (`shape`, `hand`), a **home** pose (what the params say, §2.4) and an
  **offset** pose (what the world systems add). The pose drawn is
  `home ∘ offset`. Ids: `shape`, `hand.left`, `hand.right`.
- **Orthogonal registries keyed by object id**, each owned by its own system:
  - `bodies`: mass, inertia, linear and angular velocity, linear and angular
    drag. This plan steps **free bodies only** (velocity, drag). Joints and
    inertia shaping are plan 60's.
  - `joints`: declared, empty. Plan 60 fills it.
  - `puppets`: a source that sets an object's pose each frame. This plan has
    one kind: a tracked palm.
  - `clip`: declared, empty, no consumer. It is in the plan so the shape of
    the API is settled.

  Removing an object from `bodies` leaves it drawn and still. Removing it from
  `World` removes it from every registry.

### 2.3 The frame order

Once a frame, from the render loop after `HandsIO.poll`:

1. **Puppets:** palms set the hand objects' poses, and their velocities from
   frame-to-frame differences.
2. **Physics:** a fixed step (`STEP_S` = 1/960 s and `MAX_STEPS` a frame, the
   poi's rule, so a stall drops the rest), semi-implicit Euler, quaternions
   renormalized each step.
3. **Render reads poses.** Nothing else writes them.

### 2.4 The shape object and the `camera.*` params

The params stay as they are: same ids, routes, presets, undo, knobs and pads.
They become **the shape object's home pose**. The world's offset is runtime
state on top: never saved, never undone, and identity until something moves it.

- **The offset goes into the model matrix** (`geometry.model_matrix`, with a
  rotation and z added). Yaw and pitch stay where they are, in `_camera` on the
  CPU, so a 4D shape's look does not change.
- **Identity offset must give byte-identical frames.** Build the old matrix
  exactly when the offset is identity, without multiplying by it. All golden
  images must stay unchanged.
- **The field's Fit and 3D-lattice path** sets its own identity model
  (`render.py`, `legacy`). The builder decides whether the offset composes
  there too, and records it in the register.
- **Scale stays `camera.zoom`.** The offset's scale is 1 in this plan, because
  the strokes are scaled on the CPU by zoom.
- **`world.reset`** (a trigger in the `world` group) returns every offset to identity.

### 2.5 The hands as objects

`hand.left` and `hand.right` are world objects puppeted by the palm:

- **Position:** the palm centre through the same Leap → stage → calibration →
  world transform the ghost hands use (`ghost.basis`, `ghost.calibration`,
  `hands.core.Units`), so the object sits exactly where its ghost hand is drawn.
- **Orientation:** `room.palm_axes` turned into a quaternion.
- **A lost hand:** the object stays registered, marked absent. A puppet with no
  data writes nothing.

The ghost hands keep drawing from their skeleton as today. This plan does not
change how they draw, only that their pose now also exists as an object.

## 3. Out of scope

- Joints, hand-shaped inertia, the skater effect: plan 60.
- Moving poi or totem onto the world (plan 60 may move poi, as a separate item).
- A 4D world: plan 61.
- Renaming `camera.*` to `shape.*`: it touches saved presets. Not now.
- Any panel page beyond the `world` group's params.

## 4. Tests

- **`Pose` maths:** qL = qR reproduces a 3D quaternion rotation and leaves w
  fixed; the 4×4 matrix is orthonormal with determinant 1; compose, inverse,
  log/exp and slerp round-trip; the matrix and `qL · v · q̄R` agree on random points.
- **Registries:** adding, removing, orthogonality (no body means not moved;
  removing an object clears every registry).
- **The step:** a free body under drag decays at the closed-form rate, and the
  same at 30, 60 and 144 fps.
- **Puppets:** a tape (`hands/tape.py`, `tests/fake_hands.py`) puts each hand
  object where `ghost.pose` puts its palm.
- **Render:** identity offset gives byte-identical frames (`test_golden*`
  unchanged); a known offset moves the shape by exactly that amount.

## 5. Hand checks and register

Hand checks take the next free numbers and group in `11-hand-checks.md`. The
main check: with a hand in view, nothing in the picture changes (the world is
on, but nothing moves the offset yet). Register rows take the next free numbers
in `DECISION-REGISTER.md`.
