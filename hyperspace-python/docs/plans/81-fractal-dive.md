# Plan 81: an endless, centred fractal dive

**Status: built (2026-11-22); the owner chose "cell" (row 1012, 2026-11-23).**
Wave 1 of the post-install wave (`plans/66-post-install` on its branch, §1 row
81). Register rows 1010–1019 (1018–1019 the follow-up, §7); hand checks 810–815, group FB. Read with
[plan 64](64-recursive-geometry.md) and [its part 2](64-depth-dependent-grab.md).

## 1. The two problems

Making loadable patches from plan 64's fractals turned up two:

1. **A plain zoom dive drifts toward an edge.** camera.zoom scales the view
   about p (`fractal.walk`: a point x of the shape is at zoom · x M + p),
   and inside a fractal p is where the rooted cell's middle sits, not the
   middle of the screen. Each re-root moves p to another cell's middle. So
   the zoom pulled the picture away from a point off to one side, the side
   changing with each level, and over a few levels part of the screen went
   empty.
2. **There was no endless dive.** A saw LFO on camera.zoom jumps at each
   wrap, so patches dived in and back out on a triangle.

## 2. What is built

### 2.1 The zoom and the turn about the middle of the screen (D4, row 1010)

`fractal.step` now runs in two halves:

- **`fractal.centre`**: the dive rate's zoom for this frame, then, inside,
  whatever changed the zoom or the turn since the last step or move (the
  view as it was left is kept in `Dive.seen`) is applied about the middle
  of the screen. A pan made since is kept as a move on top. With an offset
  drawn after the shape (a crossing's room placement), the middle is the
  point drawn at the middle.
- **The re-root**, as before. Every point is drawn where it was, at every
  re-root and every crossing, in 3D and 4D, grabbed or not. The 0.000 px
  tests stand (`test_fractal_grab.py::test_nothing_jumps_going_in_down_and_out`,
  `test_fractal.py::test_a_reroot_moves_nothing_in_the_world`). They now
  apply the zoom about the middle (`fractal.centre`) before taking "before",
  since the zoom is not a re-root.

Outside (the shape is an object, plan 64 part 2) nothing changed: the zoom
is about the shape's own middle, as for every shape.

- **A pan or a flight made during a dive stays made** (Devin's review,
  2026-11-23). The performer's framing is kept apart from the settle
  (`Dive.frame`, world units). The dive steers each new cell's middle to
  where the pan put it, not back to the screen's middle. A climb out to the
  top clears it.
- **An undo or redo** writes zoom and pan back together. The deck's restore
  (`deck._unseen`) drops the dive's reference (`Dive.seen`), so the next step
  takes the restored camera as it is, not as a zoom about the middle.

### 2.2 What a dive settles onto (row 1012: "cell", the owner's)

Zooming about the middle of the screen keeps the point under it in place.
**A point of a fractal has holes of every size beside it.** The sponge's
tunnels and the dust's gaps are about as big as the cell the point is in, at
every level. A dive that holds one point frames those holes, and the screen
goes emptier than before, not fuller. If the point is in a hole (the middle
of the sponge is one), the dive goes into nothing. The old dive looked full
because its zoom was about a cell's middle, which has all that cell's
children around it. That is also why it drifted.

So a dive also **settles** onto what it dives into (`fractal.settle`). Each
step, most of the way per level, it brings one of two things to the middle:

| `SETTLE_ON` | What comes to the middle | The point under the middle | The screen |
| --- | --- | --- | --- |
| **`"cell"`** (built as the default) | the middle of the cell the view is rooted in | moves: the view steers to each new cell's middle as it goes in (about a screen a level on the sponge, half on the tetrahedron). The picture repeats level after level, so the steer doesn't read as drift | full: as full as before or fuller, and centred |
| `"point"` (D4 to the letter) | the fractal's point the eye sees there (a search down the cells along the middle of the screen); held for good once on the fractal | stays put: 0.000 of the screen a level | 5–67 % covered on the dense shapes |

Measured as `tools/fractal_dive_demo.py` measures it: an 8 × 8 grid of
tiles, the share with something drawn in them. Each row is six frames 2 s
apart, from 6 s to 16 s into a dive at one level a second, 480 × 270,
offscreen in a cloud session, mean / least:

| Fractal | Before (main) | `"cell"` | `"point"` |
| --- | --- | --- | --- |
| Menger sponge | 0.88 / 0.78 | **1.00 / 1.00** | 0.67 / 0.62 |
| Menger sponge, spinning | 0.97 / 0.91 | **1.00 / 0.98** | 0.54 / 0.48 |
| Sierpinski tetrahedron | 0.94 / 0.91 | 0.92 / 0.89 | 0.62 / 0.42 |
| Octahedron flake | 1.00 / 1.00 | 1.00 / 1.00 | 0.58 / 0.36 |
| Cantor dust | 0.85 / 0.73 | **0.98 / 0.98** | 0.24 / 0.05 |
| Vicsek cross | 0.97 / 0.97 | 0.97 / 0.97 | 0.97 / 0.97 |
| Sierpinski 5-cell | 0.86 / 0.78 | 0.82 / 0.69 | 0.59 / 0.48 |
| 4D Cantor dust | 0.83 / 0.70 | **0.98 / 0.98** | 0.22 / 0.22 |

The brief's D4 wants both: the point stays put *and* the screen stays full.
For a fractal you can't have both. **`"cell"` is built as the default**
because the problem reported was the screen going empty. `"point"` is one
constant away (`fractal.SETTLE_ON`; a hot reload takes it). The demo
videos show both.

How each is kept steady:

- **On the cell's middle** a re-root picks the child holding the nearest
  point of the fractal to the middle of the screen (`fractal.nearest`), and
  the steer begins at once toward that child's middle.
- **On a point**, a float holds a point of a fractal only so far. A
  1e-5 error is a whole cell 11 levels down the sponge. So once settled
  (`Dive.settled`) the dive keeps nudging the point back onto the fractal,
  a fraction of a pixel a frame (under 1e-4 of the zoom). The re-root roots
  in the cell whose children hold it, so the nudge reads the same cells
  every frame. A pan, a flight, a crossing or a load clears the latch.

### 2.3 The dive rate (`view.frac_dive`, row 1011)

A velocity on the zoom in **levels a second**, signed, −2 to +2: one level
is × 1 / ratio (× 3 on the sponge, × 2 on the tetrahedron).
`fractal.dive_zoom` integrates it in float64, as the Mandelbrot's drives
do, and the re-root keeps the zoom in its band, so it never ends going in.
Going out it stops at the whole shape (zoom 1, the path empty, eased to the
middle) and pulls no further.

- **Where it lives:** a fractal's own param in the `view` group, next to
  `view.frac_additive`. A level is a fractal's: on any other shape it does
  nothing. It is not a camera param, since a "level" means nothing to a
  polytope.
- **Saved** as the FRACTAL section's Detail, Reach and Near are (row 902):
  persisted (undo, the dirty dot and an export hold it), and written as
  `"dive"` under the loadable patch's optional `fractal` key, only while the
  shape is a fractal (`loadable.FRACTAL_IDS`). No other look's file
  changes. A file with no key, or a key from before plan 81, loads it at 0.
- **Routable:** an LFO (any shape: a saw no longer jumps, since it drives a
  velocity), a hand or a knob. `ViewState.reroot(reg, off, dt)` takes the
  frame's seconds; `app._reroot` passes them, on air and off.
- **Drawn** as **Dive**, the first slider of the FRACTAL section, above
  Detail (`ui_fractal.spec`, row 1015). The section (#466) merged into `main`
  while this was built. It was drawn in VIEW until then; the merge moved it.

### 2.4 An endless dive's path (row 1014)

A saved dive's path is at most `MAX_PATH` (4096) cells. Past that, the
outermost levels go. They are never drawn (`ABOVE` keeps about five
levels up), and the cell the view stands in is a copy of the whole shape,
so no picture changes. Only how far out the top is changes: climbing out
of a trimmed dive stops at the whole shape 4096 levels up.

## 3. Tests

`tests/test_fractal_dive.py`:

- **every fractal**, sixty levels at a fixed rate: no re-root moves a point
  (under 1e-9 of the zoom), the zoom stays in its band, and the cell's
  middle ends each level within half its reach of the screen's middle;
  with `"point"` the point under the middle never leaves it;
- **hundreds of levels** (300, the sponge and the 5-cell, both settles):
  the same, with the numbers bounded;
- spinning (the turn about the middle), the rate's speed, a rate of 0, a
  pan kept, a plain zoom about the middle, an offset's middle;
- **a negative rate climbs out** to the whole shape, zoom 1, centred, and
  stays there;
- a **grabbed** shape (moved and turned) dived into: across its crossing
  and every re-root after, every point where it was (3D and 4D);
- the param: routable (a source on it dives; camera.zoom's base follows),
  saved in a loadable patch and loaded back;
- the CPU and GPU paths draw deep in a dive, 3D and 4D; `MAX_PATH` holds.

`test_fractal_gpu.py`'s float32 tolerance moved from 2e-5 to 3e-5 of a cell's
size. The 5-cell's dive now ends where its smallest cells lie farthest out,
2.1e-5 off.

## 4. The demo

`tools/fractal_dive_demo.py` renders a Menger sponge dive offscreen
(drive-the-app §1) with a cross at the middle and the coverage in the
corner. Run from a worktree of `main` in `--mode zoom` for the before, and
from this branch in `--mode rate`. In
[`assets/81-fractal-dive/`](assets/81-fractal-dive/):

- `before.mp4` / `.png`: `main`, camera.zoom grown at one level a second;
- `after.mp4` / `.png`: the dive rate at one level a second, `"cell"`;
- `after-point.mp4` / `.png`: the same with `"point"`, the alternative.

The demo's own count, 960 × 540, every frame after the first 3 s of a 23 s
dive (22 levels), mean / least: before **91 % / 61 %**, after **96 % / 84 %**,
the alternative **68 % / 56 %**. The faint lines don't survive the video
encoder well at a thumbnail's size: judge it full screen. Software GL in a
cloud session, not the rig.

## 5. Files outside the row, and the goldens

Plan 81's row owns `fractal.py`, `view.py`'s `reroot` and
`tests/test_fractal*.py`. It also needed these, each kept small:

- `params.py`: the `view.frac_dive` param;
- `view.py`: the `frac_dive` field;
- `app.py`: `_reroot` and the off-air reroot pass the frame's seconds;
- `ui_fractal.py`: the slider, one row;
- `loadable.py`: `"dive"` in `FRACTAL_IDS` / `FRACTAL_OWN`;
- `deck.py`: the undo's restore also calls `_unseen`;
- `tools/fractal_dive_demo.py`: the demo;
- `tests/test_deck_fade.py` (a stand-in view's `reroot` takes the new
  arguments), `tests/test_graph_legible.py` (the shape node has 47 params)
  and `tests/test_fractal_grab.py::test_the_fractal_controls_are_the_looks_own`
  (the `fractal` key holds `"dive"` too).

No loadable patch that is not a fractal saves differently. The corpus and
every fixture are byte for byte as they were.

**Goldens.** None should move. No corpus loadable's shape is a fractal, and
the golden harness draws one frame without stepping a dive. Only a fractal,
after a step inside it, draws differently. The new param's default (0)
changes no picture, and it isn't saved for a look that isn't a fractal. A golden that moves is a fault: stop and report.

## 6. Restart or hot reload

**Restart.** There are new fields on live objects (`ViewState.frac_dive`,
`Dive.seen`, `Dive.settled`), a new param, and `ViewState.reroot` and
`app._reroot` take the frame's seconds. After the restart, `fractal.py`
hot-reloads as before. The settle constants (`SETTLE_ON`, `SETTLE`) take
effect on a reload.

## 7. Follow-up: the framing and undo (rows 1018–1019)

Five fixes after the review, each with a test in `tests/test_fractal_dive.py`:

1. **A grab that only turns leaves no framing.** `fold_flight` moved the
   framing by how far the flight moved p, so a turn of an off-centre cell
   read as a pan. The framing now moves rigidly, as the flight moves the
   point it frames: `frame[:3] = R · frame[:3] + u`, w left
   (`test_a_flight_that_only_turns_leaves_no_framing`,
   `test_a_flight_moves_its_framing_rigidly`).
2. **An off-air climb drops the framing.** Off air nothing runs
   `app._space`, so `go_outside` never cleared it. `fractal.step` now drops
   it once the path is empty and the view has eased home (zoom ≤ `Z_HOME`),
   on air and off air alike (`test_an_off_air_climb_out_drops_the_framing`,
   `test_a_climb_on_air_and_off_air_ends_the_same`).
3. **A saved dive keeps its framing.** `Dive.to_json` writes an optional
   `"frame"` (four finite numbers) when there is one; `from_json` checks it
   as it checks `shift` and reads none from a file without it. No schema bump
   (plan 64's optional-key precedent, row 889)
   (`test_a_saved_dive_keeps_its_framing`, `test_a_dive_with_no_framing_saves_as_before`,
   `test_a_framing_that_cannot_land_refuses_the_dive_whole`).
4. **Undoing a pan takes its framing back.** An undo step holds the framing
   beside the camera (`deck.DiveFrame`, `Undo(beside=)`), put back only when
   the restore writes camera.zoom or camera.pan
   (`test_undoing_a_pan_takes_its_framing_back`,
   `test_an_unrelated_undo_leaves_the_framing`).
5. **A running dive no longer merges undo steps** (option (a), row 1018,
   pending the owner). `Param.follow` keeps how far it has moved a base
   (`_drift`), and undo reads a base less that, so the dive's writes neither
   open a step nor keep one open. A restore puts back what the user set with
   the follows since put on (`undo.own`), so an undo does not yank the dive
   back (`test_two_edits_during_a_dive_are_two_steps`,
   `test_a_running_dive_makes_no_step`). Option (b), the dive as a
   modulation on camera.zoom, was not taken: it would change what a saved
   dive holds and how every route on camera.zoom rides.

Devin's review of #474 found four more, each fixed with a test:

- **Undoing a load** carried the loaded dive's motion onto the old camera.
  `Dive.lives` (bumped by every `reset`) marks a dive's life; undo keeps the
  follows only within one, and only while the dive runs or has re-rooted
  since (`deck.DiveFrame.continues`). Otherwise the camera goes back exactly
  (`test_undoing_a_load_puts_the_camera_back_as_it_was`,
  `test_undoing_a_zoom_in_a_paused_dive_puts_the_cell_back`).
- **A restore cleared the dive's reference** (`_unseen` on every restore), so a
  zoom undone in a running dive left the cell where the zoom had put it. Now
  `DiveFrame.put` keeps the reference's zoom when the follows are kept, so the
  restored zoom is taken about the middle, as the edit was; the whole camera
  is taken as it is otherwise.
- **The wheel's pivot stacked on `centre`'s** inside a dive. The wheel now adds
  only the move from the middle to the cursor there (`fractal.about_middle`)
  (`test_a_wheel_zoom_at_the_middle_inside_a_dive_is_about_the_middle`).
- **Off air, the re-root ignored a loaded dive's room placement.**
  `app._reroot_off_air` passes `shapeframe.drawn_offset`
  (`test_an_off_air_dive_centres_where_its_room_placement_draws_it`).

Devin's second review found three more, each fixed with a test:

- **Undoing a pause jumped the camera.** A step held the framing from the last
  quiet frame but the camera's bases from the last closed step, which a
  running dive had left far behind. The camera's bases and drift are now
  taken on the same quiet frame (`Undo._quiet_take`)
  (`test_undoing_a_pause_resumes_from_the_paused_view`).
- **A route on the pan made an undone pan's framing come back reversed.** The
  restore read the pan before `apply` landed it. The dive now takes the
  restored pan at its next step (`Dive.seen` with no p)
  (`test_undoing_a_pan_with_a_route_on_it_leaves_no_framing`).
- **The wheel notch that takes the view back outside lost the middle's
  pivot.** `app._space` runs `fractal.centre` before deciding a crossing; a
  second call in the frame now moves nothing at all
  (`test_a_wheel_notch_that_takes_the_view_back_outside_holds_the_middle`).

Devin's third review found two more, each fixed with a test:

- **Two loads within the settle time:** the second's step held the camera
  from before both. An action now takes the camera as it is when pushed
  (`test_two_loads_within_the_settle_time_undo_one_at_a_time`).
- **The early `centre` in `_space` split a frame's zoom** from the dive rate's,
  so a zoom in that only slowed a climb still settled. `_space` now previews
  the crossing (`app._crosses_out`) and takes the pivot early only on a
  frame that crosses out
  (`test_a_zoom_in_that_only_slows_a_climb_is_about_the_middle`). That one
  verdict, on the centred pose, also decides the crossing itself, so an orbit
  where only the uncentred pose fits stays inside (Devin's fourth review,
  `test_a_crossing_out_goes_by_the_centred_pose`).

**Restart:** `Deck.build` wires the undo's `beside` once, at launch; `Dive.lives`
is a new field.

## 8. Open

- The cost of the settle on the rig (hand check 815). In a cloud session
  `fractal.step` takes a median 0.3 ms and up to about 4 ms on a re-root
  frame of the 5-cell or the dust. The rig is faster, but it is new work
  each frame.
