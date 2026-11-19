# Plan 64: recursive geometry — fractals you zoom into forever

**Status: built (2026-11-19), with its part 2; the owner's answers in §5.**
Branch `plan-64-recursive-geometry`, cut from Dillon's
`claude/tender-heisenberg-knlvgq` with `main` merged in (already current:
the merge was a no-op). Register rows 882–891; hand checks 679–688, group
DZ. The owner's decisions of 2026-11-18 (rows 882–884) overrule any other
document.

## 1. What Dillon's branch built

Nine fractals you can zoom into forever with geometry alone (`fractal.py`):
in 3D the Sierpinski tetrahedron, the octahedron and icosahedron flakes, the
Menger sponge, Cantor dust and the Vicsek cross; in 4D the Sierpinski 5-cell,
4D Cantor dust and the 4D Vicsek cross.

- **Walked from the top each frame.** A cell bigger than `SPLIT` of the
  screen splits; what the eye can't see is culled (the 4D eye along w too);
  at most `BUDGET` = 30,000 edges.
- **New edges only.** A split adds only its children's edges (`new_E`); new
  detail fades in, a cell about to pass the eye fades out.
- **Re-rooting.** `fractal.step` re-roots the view into the child cell under
  the middle of the screen once the zoom passes `Z_IN` = 4, so the zoom stays
  in about [1.7, 4) and float32 never runs out. `Dive.path` is the only state.
- **Faces at every scale**, every cell a solid.

## 2. What this branch adds

### 2.1 One shape interface (`shapeframe.py`)

`render.draw_scene` asked four times whether the shape was a fractal. It
now asks no shape what it is: `shapeframe.frame(view, w, h, offset)` returns
a `ShapeFrame` for every kind.

| Provider | What `frame` returns |
| --- | --- |
| `Fixed` (a polytope, a solid, a surface, a curve) | its cached `geom`, turned by `shape_world`; with the world's offset, a 3D shape's cue turned (`turned_depth`, plan 60) |
| `Scene` | its layers, each at its own spin (the same call), the layers' weights as `style` |
| `Fractal` | `fractal.walk`, then either its geometry (`geometry_of`, sorted) or the walk itself for the GPU (additive) |

The fractal's special cases are fields now: the cue's fixed ends (`cue`),
the count the stroke density reads (`dens_m`), whether a legacy stroke
scales with the zoom (`zoom_strokes`), and the frame's own triangles, uvs
and weights (`faces()`). **A pure refactor for every non-fractal shape:**
240 offscreen frames (every shape, faces off and on, field copies, Fit,
screen strokes, a zoom and pan, a world offset) are byte for byte what they
were before it, and the only two that moved are the fractal-with-offset
frames §2.4 fixes. `tests/test_fractal_gpu.py` holds every provider field
against the calls draw_scene made, for every shape.

### 2.2 The cells on the GPU, in world space (`fractal_gl.py`)

The owner's decision 2 (row 883): a cell is world geometry like every other
shape, never a screen-space copy. `field.py`'s instances — a 2D offset, a
scale and an alpha after the projection — are not used.

- **Uploaded once per fractal:** its meshes — a split's new edges and new
  corners, the whole shape's outline and corners, the solid's triangles.
- **Uploaded each frame:** one instance row a cell, six floats: its centre
  already in the view (4D, `zoom · (o @ M) + p`, before the divide), its
  radius in the view (`zoom · s`) and its alpha (`fractal.instances`).
- **The vertex shader** (`FRAC_PLACE`) adds the cell-sized turn of the mesh
  corner, does the 4D divide, the fade along w and the depth cue, then the
  scene pass's own stroke, dot and face rules, `u_model` (camera.zoom and
  pan and the world's offset) and the eye. It is `fractal.Walk.place` in
  float32.
- **The cull and the split stay on the CPU** (`fractal.walk`), so only six
  numbers a cell go up a frame.
- **Precision.** The view's centre of a deep cell is a large number minus a
  large number (the top cell is up to `ABOVE` = 256 times the rooted one).
  That subtraction happens on the CPU in float64, so the GPU only ever adds
  a cell-sized offset. Measured against the CPU at about 22 halvings in,
  the GPU's points are within 5 × 10⁻⁶ of their cell's size and the cue
  within 6 × 10⁻⁷ (`test_the_gpu_places_every_corner_where_the_cpu_does`).
- **The field's copies** are drawn one draw each, the copy a uniform; the
  depth pass and the look-back's cover draw the same cells.

### 2.3 The line order: sorted or additive (`view.frac_additive`)

Plan 62's §3 problem is the painter sort: with the projection on the GPU the
depths are no longer on the CPU. The owner's decision 3 (row 884): render
unsorted additive blending and look before anything depends on it.

- **Sorted** (off, the default): the CPU path — `fractal.geometry_of`, the
  painter order every shape has. Correct, and the oracle.
- **Additive** (on): the GPU path, unsorted. Colour adds up
  (`SRC_ALPHA, ONE`); alpha composites as the pass's own blend, so a
  see-through window and the ground behave as before.

What additive gives up, visible in the comparison: overlapping lines and
faces brighten where they cross (dense regions go white), and the red dots
add into the white lines instead of sitting over them, so they read pink.
The toggle is not saved (row 884) and shows in VIEW only on a fractal.

### 2.4 The cull reads the offset; what a grab holds is part 2

Plan 59's offset (a grabbed or moved shape) composes into the model matrix
as home ∘ offset, home being camera.zoom and pan.

- **The cull.** The walk culled as if the offset were the identity, so a
  grabbed fractal lost cells at the screen's edge and kept ones off it.
  Now `fractal.walk(…, off)` moves each cell's centre by the offset drawn
  after the shape (`shapeframe.drawn_offset`) before the frustum, range and
  size tests, its reach scaled by the offset's own scale. The depth cue
  reads where a point is drawn (`Walk.place`; the shader reads `u_off`).
- **The re-root.** As first pushed, `fractal.step` ignored the offset, so a
  moved or turned fractal jumped at every level (0.61 world units for an
  offset of 0.3). A compensation was pushed next, and a 4D fractal still
  drifted off its cells. The owner chose a depth-dependent grab instead,
  built as [part 2](64-depth-dependent-grab.md):
  - outside (the shape fits the rig's box) the fist holds an object, as
    plan 59;
  - inside it holds the space, whose flight is folded into the view.

  An object is never re-rooted, so nothing has to make up for an offset
  across a re-root, and the compensation is gone. Every crossing and
  re-root draws every point where it was, for 3D and 4D alike.

### 2.5 The dive is saved (row 889, the owner's, 2026-11-19)

`ViewState.dive` was runtime state, so a loaded look started at the top of
its fractal at the saved zoom and pan, which are a rooted cell's: a
different picture from the one saved. A load also kept whatever dive the
view was in, under the new look's camera.

Now a loadable patch saved while its view is inside a fractal writes an
optional key (`loadable.DIVE_KEY`, `fractal.Dive.to_json`):
`"dive": {"shape": "<fractal's name>", "path": [k, …], "z", "w", "turn", "shift"}`.
`turn` and `shift` are part 2's: the space's own turn and its room
placement. A load puts the dive back for the shape it names
(`Dive.from_json`). A file with none, or one for another shape, starts at
the top: a load always replaces the dive.

- **Validated whole on load.** It is refused, with a note, for any of:
  - a cell index outside the fractal;
  - a path over 4096;
  - a number that is not finite;
  - a turn that is not one.
- **No schema bump**, by the node-mode precedent (#377: an optional key).
  A build from before ignores the key and shows the top of the shape at
  the saved zoom: a different picture, nothing broken. Both Macs run one
  build (DECISIONS).
- **Byte for byte as before.** Every other loadable patch writes no key.
- **`centres`' order is a file format now.** A path indexes it, and
  `tests/test_fractal_grab.py::test_each_fractals_cells_keep_their_order`
  freezes each fractal's.

### 2.6 The comparison, the demo and the bench

- `tools/fractal_compare.py`: the same dive (tetrahedron, Menger sponge,
  5-cell), four views in lockstep — faces off and on, sorted and additive —
  as one still and one 10 s video each, in
  [`assets/64-recursive-geometry/`](assets/64-recursive-geometry/).
  Rendered offscreen on Mesa's llvmpipe in a cloud session, not the rig.
- `tools/fractal_grab_demo.py` (part 2): a grabbed fractal dived into and
  flown through. Each crossing's and re-root's jump is measured; all read
  0.000 px
  ([`grab-dive.mp4`](assets/64-recursive-geometry/grab-dive.mp4)).
- `tools/fractal_bench.py`: every fractal at 0, 3, 8 and 16 levels in,
  faces off and on, sorted and additive. It times the walk, each path's CPU
  build, the whole `draw_scene` wall time (GPU waited on) and its GPU time
  (a timer query, as `PassTimer` times a node). Cloud numbers mean nothing;
  hand check 686 runs it on the rig.

## 3. Restart or hot reload

**Restart.** There are new fields on live objects (`ViewState.frac_additive`,
`Dive`'s, `WorldObject.bounded`), two new modules (`shapeframe`,
`fractal_gl`, in `hotreload.MODULES` after `fractal`), a new param, and new
frame steps (`app._space`, `app._fly`). A hot reload after the restart
rebuilds the GPU path's programs (`Renderer.on_reload` drops `_cells`).

## 4. Tests

`tests/test_fractal_gpu.py` (part 2's tests and the saved dive's are in
`tests/test_fractal_grab.py`):

- the provider gives every non-fractal shape exactly what draw_scene made,
  with and without an offset;
- the switch leaves a fixed shape's frame byte-identical;
- the GPU places every corner where the CPU does, every fractal, deep;
- the instance rows of a known dive;
- the cull with an offset: moved off screen, turned, the cue reading it,
  and draw_scene handing the offset over;
- an additive frame draws the sorted frame's pixels, with copies too.

## 5. The owner's answers (2026-11-19), and what is open

- **Sorted stays the default** (row 884). Additive stays as a switch,
  unsaved.
- **The dive is saved** as an optional key (row 889, §2.5).
- **Grab:** depth-dependent, with sane defaults to tune by playing
  ([part 2](64-depth-dependent-grab.md) §10). Inside a 4D fractal a drag
  travels through its 4D space.
- **Open:** the frame times on the rig (hand checks 686–687), and whether
  the GPU path is worth its weight at the depths a show uses.
