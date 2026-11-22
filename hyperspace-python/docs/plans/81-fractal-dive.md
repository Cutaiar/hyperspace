# Plan 81: an endless, centred fractal dive

**Status: built (2026-11-22), one owner decision pending (row 1012).**
Wave 1 of the post-install wave (`plans/66-post-install` on its branch, §1 row
81). Register rows 1010–1017; hand checks 810–815, group FB. Read with
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

### 2.2 What a dive settles onto (row 1012, pending the owner)

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
- **Saved like any param:** persisted, so a loadable patch's `values` hold
  it (`"view.frac_dive": 0.75`). An older file without it loads at 0. Every
  loadable patch saved from now on carries the key, as with any new param
  (the no-old-schema rule).
- **Routable:** an LFO (any shape: a saw no longer jumps, since it drives a
  velocity), a hand or a knob. `ViewState.reroot(reg, off, dt)` takes the
  frame's seconds; `app._reroot` passes them, on air and off.
- **Drawn** in VIEW under Screen strokes, beside Additive, on a fractal only
  (`ui_view.spec`, `Panel._view_stock`). The FRACTAL side-pane section
  (`claude/serene-davinci-cgtewx`, unmerged on 2026-11-22: Detail, Reach,
  Near, To the top) should take it when it merges, as it takes Additive.
  This branch adds nothing that duplicates that one (row 1015).

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
- `ui_view.py`, `ui.py`: one line each, the slider beside Additive;
- `tools/fractal_dive_demo.py`: the demo;
- the corpus loadables (`tests/corpus/loadable/*.json`, 25) and
  `tests/fixtures/groups/party-noita-grouped.json`: each resaved through the
  loader, which adds exactly one line, `"view.frac_dive": 0.0`. A new
  saved param is in every save, as with `ghost.material` (#449);
- `tests/test_deck_fade.py` (a stand-in view's `reroot` takes the new
  arguments) and `tests/test_graph_legible.py` (the shape node has 43
  params, not 42).

**Goldens.** None should move. No corpus loadable's shape is a fractal, and
the golden harness draws one frame without stepping a dive. Only a fractal,
after a step inside it, draws differently. The new param's default (0)
changes no picture. A golden that moves is a fault: stop and report.

## 6. Restart or hot reload

**Restart.** There are new fields on live objects (`ViewState.frac_dive`,
`Dive.seen`, `Dive.settled`), a new param, and `ViewState.reroot` and
`app._reroot` take the frame's seconds. After the restart, `fractal.py`
hot-reloads as before. The settle constants (`SETTLE_ON`, `SETTLE`) take
effect on a reload.

## 7. Open

- **Row 1012:** `"cell"` or `"point"` (§2.2). Hand check 812.
- The cost of the settle on the rig (hand check 815). In a cloud session
  `fractal.step` takes a median 0.3 ms and up to about 4 ms on a re-root
  frame of the 5-cell or the dust. The rig is faster, but it is new work
  each frame.
