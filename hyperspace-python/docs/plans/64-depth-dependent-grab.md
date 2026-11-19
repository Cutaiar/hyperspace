# Plan 64, part 2: what a grab holds, outside a fractal and inside it

**Status: planned, not built (2026-11-19).** It follows plan 64 (the draft
PR on `plan-64-recursive-geometry`) and replaces that branch's re-root
compensation (row 887) when it lands. It needs plans 59 and 60, both built.
Register rows and hand checks: none taken yet; numbered when it is
scheduled.

The owner (2026-11-19): go with a depth-dependent grab, "rely on as little
cludgery as possible", and "don't cargo cult in behaviors that do not make
semantic sense".

## 1. The question

What does a grab hold when the shape is a fractal? Three readings were on
the table:

- the whole shape;
- one piece of it;
- a change to the rule it is made by.

Today the hand rig (plan 60) holds the **world object** `shape`. It writes
one rigid pose, the **offset**, which the renderer composes as
home ∘ offset, home being camera.zoom and pan (plan 59). For a bounded shape
in front of you that is right. For a fractal you have dived into, it is
not:

- the home is re-rooted at every level;
- the shape's centre is astronomically far away;
- there is nothing whole left to hold.

## 2. The answer: the hand holds the same thing; what that thing is changes

**The hand's rule never changes: a closed fist holds what it grabbed,
where it grabbed it.** Welded, the point under the fist stays under the
fist. On a spring it follows loosely. Let go, it coasts at the drag. What
changes with depth is what the fist has hold of.

| | **Outside: an object** (the shape is held whole in view) | **Inside: the space** (it isn't) |
| --- | --- | --- |
| What is held | the fractal, a bounded thing with a centre | the space you are in; there is no object |
| The offset composes | home ∘ offset: the camera places the shape, the offset moves it from there (plan 59, unchanged) | offset ∘ camera: the camera's zoom and pan are the dive's view, and the offset moves the whole space, in world units |
| A coasting turn turns about | the shape's own centre | the world's origin, the point the eye looks at |
| camera.zoom | scales the shape about its centre (and a moved shape's offset with it, row 853, as every shape) | dives: scales about the cell under the eye, as with no offset |
| The rig's box (keeps the shape whole on screen) | yes | no: you can't keep on screen the space you are in |
| Shaped inertia, the skater | yes: a body has an inertia to shape | no: the space has no body. Its inertia is even |
| Grip off, a new look, Reset world | the offset springs home | the same: the offset springs to the identity, the space as the camera frames it. Both draw the same target |
| `grip:*` lanes | the shape's speed and spin | the space's (the speed of your flight) |

This is a split of meaning, not of mechanism. The joint, the spring, the
coast and the drag are the same code on the same offset. Two parts only
make sense for an object, the box and the inertia's shape, and inside they
are off rather than carried over.

### Why not the other two readings

- **A piece of the fractal** (grab one cell and move it) breaks
  self-similarity. It needs per-cell state keyed by the dive path, and the
  owner's decision 1 keeps the fractal stateless (row 882).
- **The rule** (a hand turn twisting each child against its parent) is a
  good creative control, but it is not a grab. If it is wanted, it is its
  own param on a knob or a hand axis, in its own plan.

## 3. When you are inside

**Inside ⇔ the shape can't be held whole in view, or the view has entered
one of its cells.**

1. **Held whole.** The shape's reach (its circumradius × camera.zoom,
   through the 4D divide's bound for a 4D fractal) is under half the view
   at its depth across the shorter side. This is the rig box's own test
   (`World._boxed` insets the box by the same reach): the box exists to keep
   a shape whole on screen, and when the inset is empty the shape can't be.
   At the default eye this ends at a zoom of about 1.6.
2. **Entered a cell.** `Dive.path` is not empty: the view is rooted in a
   part of the shape. At the default eye this comes later (zoom 4), but a
   longer `eye.distance` can reverse the order, so either one is enough.

With hysteresis: in once the reach exceeds the view, back out only when it
is under 90% of it and the path is empty. Nothing else decides it: not the
re-root's constants, not the hand, not a param.

The result is an invariant the code can rely on: **an object is never
re-rooted.** Every re-root happens inside, where the offset is in world
units and a re-root can't move it. That is what removes the compensation
(§5).

## 4. The crossing: an exact re-expression, nothing moves

Crossing in or out changes how the offset is written down, never what is
drawn. Let C be the camera as a similarity (scale zoom, then move to pan).

- **Inward:** O_space = C ∘ O_object ∘ C⁻¹, so offset ∘ camera draws exactly
  what camera ∘ offset drew. Outward is the inverse with the camera of that
  moment. This holds for 3D and 4D alike: C acts after the 4D divide, and
  so does the offset.
- **What the joint captured** is re-expressed the same way:
  rel_space = rel_object ∘ C⁻¹. A fist closed across the crossing keeps
  holding the same point.
- **The body's motion** is the same rigid motion of the drawn shape, taken
  about the new reference point:
  - its velocity: the old velocity × zoom, plus the spin's sweep from the
    object's centre (drawn at pan) to the world's origin;
  - its spin: unchanged;
  - its box place: re-expressed like the offset.

  The grip gives the body equal linear and angular drag, so a coasting
  shape continues exactly as it was.
- **Inward, the inertia goes even** with the spin kept. A body that was
  precessing stops precessing; nothing jumps.
- **Outward, the box comes back.** By §3 the crossing happens only when the
  shape fits the box, so the box can't move it.
- **The homing target** (the identity offset) draws the same picture in
  both forms, so a shape springing home crosses without noticing.

So **no rule about mid-grab crossings is needed**. A fist closed outside
and still closed as the zoom carries you in goes on holding: the point
under the hand stays there. Only the box and the inertia stop applying,
because there is no object any more.

## 5. What this removes from plan 64 as pushed

Row 887's re-root compensation exists because an object-frame offset was
being re-rooted. With §3's invariant that never happens. These go:

- `fractal.step`'s `follow` and its 3×3 pan-and-depth solve, the 0.2
  edge-on threshold, and the `(k, g)` it returns;
- `World.rebase` and its velocity and place rescaling;
- the 4D drift limit (open in row 887): gone, because inside the offset is
  in world units for 3D and 4D alike.

These stay, made simpler:

- **The cull and the cue** take one world-frame transform W, which maps the
  walk's world to where it is drawn: W = C ∘ O ∘ C⁻¹ outside, W = O
  inside. `fractal_gl`'s `u_off` becomes this W.
- **The re-root's choice of cell:** the middle of the screen is W⁻¹(origin).
- **`app._reroot`** hands the view W. `field.takes_offset` (is the offset
  drawn at all) stays.

## 6. The changes, by module

- **`world.py`:**
  - `WorldObject.bounded` (True for every object today).
  - `World.cross(oid, camera, bounded)`: §4's re-expression of the offset,
    `Joint.rel`, `Body.velocity`, `.spin_l` / `.spin_r` and `.place`,
    the inertia going even inward.
  - `_boxed` and the shaped inertia act only on a bounded object.

  No change to how a pose is composed: inside, the shape object's home is
  the identity (§ next), so pose = home ∘ offset = offset, and the joint,
  spring and coast run unchanged.
- **`app._step_world`:** the shape object's home is the camera
  (`shape_home(zoom, pan)`) while bounded and the identity while inside.
  Inside, the camera is the dive's view, not the shape's placement. The
  crossing test (§3) runs first, once a frame, on the on-air view, and calls
  `World.cross` when it flips.
- **`fractal.py`:** `held_whole(s, w, h)` (§3, with the walk's own 4D
  bound); `walk` and `step` take W (§5).
- **`render.draw_scene` / `shapeframe`:** the model matrix is
  `home @ offset` for a bounded shape and `offset @ home` for an unbounded
  one, read from the world object. It is built on the CPU in float64, so a
  long flight inside (a large offset, a far pan) cancels there before it
  reaches the GPU.
- **`grip.py`:**
  - `apply` sets `boxed` from `bounded`.
  - `apply` leaves `inertia`, `shape` and the shaping clutch out while
    unbounded.
  - The panel shows those three as inert inside, with the reason in their
    tip, as VIEW shows the W planes on a 3D shape.
- **Loads (the prerequisite):** a load resets the view's dive
  (`Dive.reset`). Today only Reset view does, so a look loaded while deep
  in a fractal puts its saved zoom and pan inside whatever cell the old
  dive was in. The dive only means something under the camera it was
  made with.

Non-fractal shapes are bounded always and never cross: their frames are
byte for byte as before, and the 240-frame digest check holds them there.

## 7. What is deliberately not carried inside

Each of these would be cargo culted in if kept. Each fails a "what would
it mean?" test:

- **The box:** it keeps a shape whole on screen; the space can't be.
- **Shaped inertia, precession, the skater:** properties of a body; the
  space you fly through has none.
- **"The shape's centre"** as a pivot: deep inside it is far away and
  meaningless. The pivot is the world's origin, where the eye looks.
- **A zoom-scaled offset:** inside, camera.zoom is the dive, not the shape's
  size, so the offset is in world units and the zoom leaves it alone.

**Kept outside, though questionable:** plan 59's moved-object offset
sliding outward under zoom (row 853). It applies to every shape alike, so
changing it is not this plan's business. It is listed here so it isn't
mistaken for a fractal rule.

## 8. Limits

- **One world, two decks** (row 852). The crossing follows the on-air view.
  A deck off air draws the world's offset in whatever form it is in, so its
  preview of a moved fractal can be off while the two decks disagree about
  inside and outside. This is the same class of limit plan 59 already has.
- **A 4D fractal's inside drag moves its shadow,** the picture you see,
  rigidly with the hand. It does not translate through 4D space, where
  points at different w would move by different amounts and the point
  under the fist would slip. Going deeper in 4D stays camera.zoom's job.
- **The hand can't scale.** No two-hand zoom is added, inside or out: it
  would be a new control, not a grab.

## 9. Tests

- **Every crossing redraws nothing:** in and out, at rest, held, flying,
  springing home; every fractal, 3D and 4D. Drawn points, the joint's
  captured pose and the drawn velocity field are compared before and after.
- **The invariant:** bounded ⇒ the dive's path is empty, over random zooms,
  pans, eye distances and fovs.
- **Inside, a re-root moves nothing,** with no compensation code: every
  fractal, 4D included, under a turned and moved offset. A turned dive
  stays centred. These are plan 64's tests, kept, with the 4D drift case
  now required to pass.
- **Welded inside:** the point under the fist stays under it across
  re-roots and through a zoom.
- **An outward crossing** never moves the shape through the box.
- **A load** resets the dive.
- **Grip off and Reset world inside** reach the same drawn target as
  outside.
- **Non-fractal shapes** never cross; the digest check is byte-identical.
- **A proof video** like plan 64's re-root demo: a grab held across the
  crossing, a flight inside a 3D and a 4D fractal, the jump at each
  re-root measured (it should read 0).

## 10. Hand checks (numbered when scheduled)

1. **Hold, then dive.** Hold a fractal and zoom in with the other
   controller. Nothing jumps at the crossing or at any level, and the
   point under the fist stays under it.
2. **Fly.** Inside, grab and pull, turn, let go. The space follows the
   fist and coasts on at the drag; it turns about the point you look at.
   Does that read as flying?
3. **A 4D fractal inside.** The same as 2 on the 5-cell. The picture under
   the fist moves with it; the dive stays centred.
4. **Back out.** Zoom all the way out after a flight. The shape comes back
   whole, wherever the flight left it relative to you, and Reset world
   sends it home.
5. **Object only outside.** Shaped inertia and the skater work outside and
   show as inert inside. The box keeps a thrown shape on screen outside
   and doesn't act inside.
6. **A load mid-dive** starts at the top of the new look.

## 11. Open for the owner

1. **The boundary's margins:** in at 100% of the view, out at 90%. Feel it
   in hand check 1.
2. **Grip off inside:** the space springs back to how the camera frames it
   (recommended: the same rule as outside). The alternative is that the
   space stays where the flight left it, like a camera move.
3. **Inside a 4D fractal:** drag the shadow (recommended, §8) or travel
   through 4D.
4. **Plan 64's re-root compensation:** delete it when this lands
   (recommended), or keep the 3D half as a fallback (not recommended: two
   mechanisms for one job).

## 12. Order and size

Size **M**, one branch on top of plan 64's:

1. The prerequisite: a load resets the dive.
2. `held_whole` and the invariant's test.
3. `World.cross` and its exactness tests.
4. The composition rule in `draw_scene` and the home in `_step_world`.
5. W through the walk, the shader and the re-root; delete row 887's
   compensation.
6. The grip's gating and the panel's inert controls.
7. The proof video, the docs, and the register rows and hand checks then
   assigned.
