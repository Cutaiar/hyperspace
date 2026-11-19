# Plan 64, part 2: what a grab holds, outside a fractal and inside it

**Status: built (2026-11-19), on `plan-64-recursive-geometry` with plan 64.**
It replaced that branch's first re-root compensation (row 887). It needs
plans 59 and 60, both built. Register row 887; hand checks 684 and 685.

The owner (2026-11-19):
- "Rely on as little cludgery as possible"; "don't cargo cult in behaviors
  that do not make semantic sense".
- Then: "have sane default behavior … dragging inside the fractal … is
  traveling through the 4D space of the fractal … these are things that
  we're going to figure out once we actually play with it". The defaults
  below are those; they are meant to be tuned by playing.

The proof: [`assets/64-recursive-geometry/grab-dive.mp4`](assets/64-recursive-geometry/grab-dive.mp4)
(`tools/fractal_grab_demo.py`). In each of three segments, a fractal the
grip has turned (and in one, moved) is dived into and flown through. Every
crossing and every re-root is measured: 0.000 px of jump.

## 1. The question

What does a grab hold when the shape is a fractal? Three readings were on
the table:

- the whole shape;
- one piece of it;
- a change to the rule it is made by.

The hand rig (plan 60) holds the world object `shape`. It writes one rigid
pose, the **offset**, which the renderer composes as home ∘ offset, home
being camera.zoom and pan (plan 59). For a bounded shape in front of you
that is right. For a fractal you have dived into, it is not:

- the home is re-rooted at every level;
- the shape's centre is astronomically far away;
- there is nothing whole left to hold.

## 2. The answer: the hand holds the same thing; what that thing is changes

**The hand's rule never changes: a closed fist holds what it grabbed,
where it grabbed it.** Welded, the point under the fist stays under the
fist. On a spring it follows loosely. Let go, it coasts at the drag. What
changes with depth is what the fist has hold of.

| | **Outside: an object** (the shape fits the rig's box) | **Inside: the space** (it doesn't, or the view is in a cell) |
| --- | --- | --- |
| What is held | the fractal, a bounded thing with a centre | the space you are in; there is no object |
| The grip's pose | the world's offset on the shape, drawn home ∘ offset (plan 59, unchanged) | the space's flight: the shape object's offset, its home the identity, folded into the view each frame (`fractal.fold_flight`), never drawn as an offset |
| A turn turns about | the shape's own centre | the middle of the screen |
| A move | moves the object in the room | travels through the fractal's own space, before the 4D divide (the owner) |
| camera.zoom | scales the shape about its centre (and a moved shape's offset with it, row 853, as every shape) | dives: scales about the cell under the eye |
| The rig's box | keeps the shape whole on screen | none: you can't keep on screen the space you are in |
| Shaped inertia, the skater | yes | no: the space has no body. Its inertia is even, and the shaping clutch is ignored |
| Grip off, a new look, Reset world | the offset springs home | the same rule: the flight springs to the identity, and the view un-turns and comes back with it |
| `grip:*` lanes | the shape's speed and spin | the space's (the speed of your flight) |

This is a split of meaning, not of mechanism. The joint, the spring, the
coast and the drag are the same code on the same offset. Only the two parts
that make sense for an object, the box and the inertia's shape, are off
inside.

### Why not the other two readings

- **A piece of the fractal** breaks self-similarity and needs per-cell
  state, against the owner's decision 1 (row 882).
- **The rule** (twisting each child against its parent) is a creative
  control, not a grab: its own param in its own plan, if wanted.

## 3. When you are inside

**Inside ⇔ the shape no longer fits the rig's box, or the view has entered
one of its cells (or is about to: zoom ≥ `Z_IN`).** `fractal.wants_inside`:

1. **Fits** means every corner of the whole shape, projected (through the
   4D divide, then the offset drawn after it), is within the rig's box:
   half the view across and up at depth 0 (`World.box`, `poi.box_for`). The
   fractal lies within its own corners' convex hull, and the divide keeps a
   hull a hull, so this is exact, not a bound. At the default eye a centred
   Menger sponge stops fitting at a zoom of about 1.6.
2. **Entered a cell** is `Dive.path` not empty. At the default eye this
   comes later, but a long `eye.distance` can reverse the order, so either
   one is enough.

Out again only when every corner is within 90% of the box (`FIT_OUT`) and
the view is at the top. A zoom riding the edge doesn't flip it.

The result is the invariant the design rests on: **an object is never
re-rooted.** Every re-root happens inside, where nothing composed after
the walk moves with the camera, so no re-root needs making up for.

## 4. The crossing: an exact re-expression, nothing moves

Let A be the object's offset's turn and t its move (home frame), and pan
and zoom the camera. **Inward** (`fractal.go_inside`, `World.to_space`):

- The view takes the offset in.
  - Its turn becomes the view's own (`Dive.turn`): A turns the walk's
    points about the middle of the screen before the 4D divide, where a
    turn commutes with it. The camera turns with it.
  - The rest becomes `Dive.shift` = (I − A)·pan + zoom·t: the room
    placement, a move in world units after the divide, drawn as an offset
    of shift ÷ zoom (`shapeframe.drawn_offset`).
  - camera ∘ offset equals shift ∘ (the view turned), for 3D and 4D alike.
- The world's shape becomes the space: home and offset the identity,
  `bounded` False.
- A body's motion is re-expressed: the same rigid motion of what is drawn,
  taken about the world's origin (v − ω × c, c the drawn centre it turned
  about). It is unboxed, and its inertia goes even with the spin kept.
- A joint holding it takes its hold again on the pose as now written, so
  the hand's target is unchanged.

**Outward** (`fractal.go_outside`, `World.to_object`) is the inverse with
the camera of that moment:
- the view's turn and room placement are handed back as the object's
  offset;
- the body's motion is re-referenced to the object's drawn centre and put
  in the home's units;
- the hold is retaken.

By §3 the shape fits the box then, so the box can't move it.

**Inside, each frame** (`app._fly`, after the world's step), what the
grip's physics did to the space is folded into the view
(`fractal.fold_flight`). The turn goes onto `Dive.turn`, about the middle
of the screen. The move goes onto camera.pan and `Dive.z`, before the 4D
divide. The room placement turns with the space, so a turn is rigid about
the middle of the screen. The flight pose itself is never drawn, so however
far you fly, the drawn numbers stay those of the cell under the eye.

So **no rule about mid-grab crossings is needed**. A fist closed outside
and still closed as the zoom carries you in goes on holding the same point.

## 5. What this removed from plan 64 as first pushed

Row 887's re-root compensation existed because an object-frame offset
was being re-rooted. With §3's invariant that never happens. These are
gone:

- `fractal.step`'s pan-and-depth solve and its edge-on threshold;
- `World.rebase`;
- the 4D drift;
- `tools/fractal_reroot_demo.py` and its video.

`step` keeps only the offset drawn after the shape, to find the cell under
the eye.

## 6. Where it lives

- **`fractal.py`:**
  - the `Dive` fields `inside`, `turn`, `shift`, `flown` (the flight
    already folded; None after a reset or a load);
  - `wants_inside`, `drawn_corners`, `go_inside`, `go_outside`,
    `fold_flight`;
  - `turn(s)` applies `Dive.turn` after the camera's yaw and pitch.
- **`world.py`:** `WorldObject.bounded`, `World.to_space`,
  `World.to_object`.
- **`app.py`:** `_space` (the crossing, before the re-root), `_reroot`
  (the cell under the eye), `_fly` (after the world's step). The shape
  object's home is the camera only while it is bounded.
- **`shapeframe.drawn_offset`:** what the scene pass composes after the
  shape: the room placement inside, the world's offset while it is an
  object, nothing while the world's shape is the space.
- **`grip.apply`:** the box and shaped inertia for an object only.
- **`loadable.py`:** the dive is saved (row 889), its turn and room
  placement with it. A load always replaces the view's dive.

Non-fractal shapes are bounded always and never cross: their frames are
byte for byte as before.

## 7. What is deliberately not carried inside

Each of these fails a "what would it mean?" test inside:

- **The box:** it keeps a shape whole on screen; the space can't be.
- **Shaped inertia, precession, the skater:** properties of a body; the
  space you fly through has none.
- **"The shape's centre"** as a pivot: deep inside it is far away and
  meaningless. The pivot is the middle of the screen.
- **A zoom-scaled offset:** inside, camera.zoom is the dive, not the
  shape's size.

**Kept outside, though questionable:** plan 59's moved-object offset
sliding outward under zoom (row 853). It applies to every shape alike, so
changing it is not this plan's business.

## 8. Limits

- **One world, two decks** (row 852). The crossing follows the on-air view.
  A deck off air re-roots with no offset and draws the world's offset only
  while the world's shape is an object. Its preview of a grabbed fractal
  can be off while the decks disagree.
- **Inside a 4D fractal, a move travels through its 4D space** (the
  owner). A point nearer or farther along w moves by more or less, so the
  point under the fist can slip off it. A turn is exact. Going deeper in
  4D stays camera.zoom's job.
- **The hand can't scale.** No two-hand zoom is added.
- **A scaled offset** (none today: the grip doesn't scale) crosses exactly
  only for a 3D fractal.
- **The panel** doesn't grey out Shaped inertia, Shape and the skater
  inside; they simply do nothing there.

## 9. Tests

`tests/test_fractal_grab.py`:

- **Nothing jumps:** going in, down and back out, the app's own steps each
  frame, every fractal × four offsets (none, moved, turned, turned and
  moved in depth). The deliberate ease home on the way out is left out.
- **An object is never re-rooted.**
- **The box's edge:** in once it doesn't fit, out only within 90%.
- **The flight inside:**
  - a 3D one turns and moves what is drawn rigidly;
  - a 4D one travels (camera.pan and `Dive.z`);
  - the room placement turns with it.
- **A crossing keeps** the body's drawn velocity field and the joint's
  hold.
- **The grip inside:** no box and no shaped inertia.
- **Reset view and another shape** bring the space home.
- **The saved dive:** round trip; a file from before; none written when
  not inside; refusals; each fractal's cell order frozen.

## 10. Defaults to tune by playing (the owner, 2026-11-19)

- **The boundary:** inside past the box, out within 90% of it.
- **Grip off and a new look inside:** the flight springs back to the
  identity, as outside.
- **Inside a 4D fractal:** travel through its space (chosen); dragging the
  picture you see is the alternative.
- **The pivot of a turn inside:** the middle of the screen. The point
  under the fist is the alternative.
