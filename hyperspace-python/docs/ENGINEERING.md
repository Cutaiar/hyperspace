# Hyperspace — the manual

How to run, configure, operate and change the Python app. Structure — the
parts, the frame, the control model and who may write a parameter — is
[`ARCHITECTURE.md`](ARCHITECTURE.md); the reasons behind the choices are
[`DECISIONS.md`](DECISIONS.md) and [`DECISION-REGISTER.md`](DECISION-REGISTER.md);
setting up a new Mac is [`SETUP.md`](SETUP.md); what a person still has to
check by hand is [`TESTING-GUIDE.md`](TESTING-GUIDE.md) and
[`plans/11-hand-checks.md`](plans/11-hand-checks.md).

Contents: 1 Geometry · 2 Rendering · 3 Running it · 4 The home folder ·
5 `config.toml` · 6 The control window · 7 Keys and the gamepad · 8 The
APC40 · 9 Learn, Unbind and routing · 10 Presets, shows and the bank ·
11 Undo · 12 Hands · 13 Audio · 14 Outputs · 15 Hot reload and the
watchdog · 16 Testing · 17 Known limits.

---

## 1. Geometry

**Shapes** (`geometry.py`). The slider index is the identity saved files
and the golden traces use, so the list is append-only and the vertex
order of the first eighteen never changes. `tests/test_golden.py` reads
this table and checks every V and E against the code, so keep it in this
form under this heading.

| # | Shape | Cells | V | E |
|---|---|---|---|---|
| 1 | 5-cell | 5 | 5 | 10 |
| 2 | 3,3-duoprism | 6 | 9 | 18 |
| 3 | Cubic pyramid | 7 | 9 | 20 |
| 4 | Tesseract | 8 | 16 | 32 |
| 5 | Rectified 5-cell | 10 | 10 | 30 |
| 6 | 4,8-duoprism | 12 | 32 | 64 |
| 7 | 6,6-duoprism | 12 | 36 | 72 |
| 8 | 16-cell | 16 | 8 | 24 |
| 9 | 10,10-duoprism | 20 | 100 | 200 |
| 10 | Icosahedral prism | 22 | 24 | 72 |
| 11 | 24-cell | 24 | 24 | 96 |
| 12 | Truncated tesseract | 24 | 64 | 128 |
| 13 | 12,12-duoprism | 24 | 144 | 288 |
| 14 | Dodecahedral prism | 32 | 40 | 80 |
| 15 | 20,20-duoprism | 40 | 400 | 800 |
| 16 | 120-cell | 120 | 600 | 1200 |
| 17 | 600-cell | 600 | 120 | 720 |
| 18 | Clifford torus (32×16) | — | 512 | 1024 |
| 19 | Heart | — | 128 | 192 |
| 20 | Star | — | 20 | 30 |
| 21 | Rose | — | 186 | 285 |
| 22 | Torus | — | 512 | 1024 |
| 23 | Trefoil knot | — | 576 | 1152 |
| 24 | Starfruit | — | 522 | 1080 |
| 25 | Möbius strip | — | 320 | 576 |
| 26 | Klein bottle | — | 576 | 1152 |

Cells "—" (`Shape.cells == 0`) marks a surface, not a polytope. It does
not mean 3D: the Clifford torus (18) is a surface native to 4D. Shapes
19–26 are surfaces from trig equations, each built with its own face
cycles.

**4D or 3D** (`Shape.dims`, 4 or 3; any other value raises — plan 28,
which replaced plan 22's lifts and masks). A shape says honestly what it
is:

| `Shape.dims` | Means | Shapes |
|---|---|---|
| 4 | real w-extent: a 4-polytope or a 4D surface. Every plane turns it, the W planes through w | 1–18, Hopf fibration, Celestial tesseract |
| 3 | a 3D shape at w = 0, nothing invented for a w it does not have. XY, XZ and YZ turn it; XW, YW and ZW — and whatever drives them — do nothing to it | Heart … Klein bottle, and the rest of the catalog |

`geometry.view_angles(i, ang)` returns `ang` itself for a 4D shape and,
for a 3D one, the view's 3D angles with every W angle at 0; nothing
writes the result back, so `ViewState.ang`, the integrator and every
`rot.*` param are untouched. A 3D shape's depth cue (`pd`: the line
fade, width and draw order) reads its depth toward the 3D camera —
`geometry.view_depth`, z after the camera's yaw and pitch — since its w
is 0. On the VIEW page the header says 3D or 4D, the Shape menu lists
the 4D shapes and then the 3D ones under their own headings (the index
stays the identity), and the W plane keys dim while they can do nothing.

So a preset on a 3D shape moves only through its 3D planes: in the test
corpus, `plasma-heart` (XZ, YZ), `spiral-silk` (YZ) and `inverse-halo`
(XZ) keep turning; their bass → W routes no longer move them.

Plan 22 lifted seven of these shapes into w (each builder took a lift of
its own parameters) and folded the Heart's W planes onto 3D planes, so
the bass bands, which drive the W planes, would move them without
flattening them. Plan 28 took both out: a 3D shape is simply 3D. The
Rose (0.16 deep) and the Möbius band (0.55 wide) keep the proportions
plan 22 gave them.

**The volume measures.** `project3(V, ang)` is the rotated, divided 3D
cloud the camera views. `volume_ratio(P)` is its smallest singular value
over its largest, centred: 1 a ball, 0 a plane or a line.
`sweep_ratios(i, plane, steps=72, pose=None)` measures it round one full
turn of one plane, the others at `pose`, through `view_angles` as the
renderer draws. `edge_on_share` is the share of face area drawn at under
a tenth of its 4D area, and `sweep_edge_on` its sweep.

**`VOLUME_FLOOR = 0.15`.** Every 4D shape keeps at least this ratio
through a full turn of each W plane, from rest and from `GENERIC_POSE`
(`tests/test_shapes4d.py::test_every_4d_shape_clears_the_volume_floor`):
cubic pyramid 0.30, 4,8-duoprism 0.53, dodecahedral prism 0.64, 5-cell
0.65, tesseract 0.94, Clifford torus 0.97, 24-cell, 120-cell and
600-cell 1.00 (single-plane sweeps reach the same worst case as 2000
random poses of all six planes). A 3D shape is the same at every W angle
(`::test_a_3d_shape_is_the_same_through_every_w_plane`).

**The turntable** (`tools/turntable.py`) is the same sweep with
pictures:

```bash
uv run python tools/turntable.py --prefix after              # every 4D shape, numbers and sheets
uv run python tools/turntable.py --prefix check --shapes 0-17 --no-png
```

It writes `<prefix>-ratios.json` / `.csv` (per shape, plane and pass:
the minimum ratio and its angle, the maximum edge-on share and its
angle) and one sheet per shape — rows XW, YW, ZW, `--frames` tiles
(12) across a turn, drawn offscreen by the real renderer, each tile
labelled with its angle and ratio, red under the floor — into
`docs/plans/assets/22-flat-shapes/`. A run overwrites files of the same
prefix there. `--shapes` takes indices (`18-24`, `17,21`); `--steps`
the sweep's resolution (72 = 5°).

**Faces.** A face of more than four corners that is not planar is
framed by its least-squares plane, where the outline stays simple and
the ear clip tiles it exactly; every planar face keeps its basis
(`geometry._face_xy`).

**The Klein bottle** (26). `_klein_xyz(u, v)` is the classic "bottle"
immersion, u ∈ [0, π], v ∈ [0, 2π): the body swells up from the base,
the neck curls over and comes back down through the body's side, where
in 3D the surface must cross itself — and does. The seam u = π meets
u = 0 with v flipped to π − v and welds by `kkey` like the Möbius
strip's: 37 × 16 samples, 36 × 16 vertices, 576 quads, every edge on two
faces, V − E + F = 0. It is centred on its bounding box
(`tests/test_shapes3d.py::test_the_klein_bottle_seam_welds_into_a_closed_grid`,
`::test_the_klein_bottle_crosses_itself_in_3d`).

**The catalog** (plan 28, an art-direction spike — see
[`plans/28-catalog-and-scenes.md`](plans/28-catalog-and-scenes.md)). After
the Klein bottle: closed 3D solids, mathematical toys, scenes, and every
4-polytope plan 22's shortlist drew or gave a recipe for
([`plans/22-polytope-shortlist.md`](plans/22-polytope-shortlist.md)) —
the 5-cell family through one `perm5` helper, the tesseract and 24-cell
families through `expand`, the snub 24-cell and grand antiprism, the
rectified 600-cell (the 600-cell's edge midpoints; its faces, the
slowest to build, take under a second), the disphenoidal 288-cell
(`edges_by_classes`: two edge lengths) and the dual runcinated 5-cell
(its cells' polar points), four star polychora on the 600-cell's and
120-cell's corners (`_star`: one distance class; the two with {5/2}
pentagram faces drawn as lines only, since a pentagram needs points the
face pipeline does not have), and more duoprisms and prisms. A solid's
faces come from the polytope extraction; a star (drawn as what shows: its
spikes, the core buried) or a compound brings its own. A curve (the toys
with F 0) draws no points: its samples are not corners.

**The warm-up.** `geometry.warm_all`, started in `app.main` after the
startup preset, builds every shape's `geom`, `faces`, `face_triangles`
and `face_uvs` on a daemon thread, the startup shape first, so the first
switch to a big shape does not stutter. Each shape has its own lock: a
frame that reaches a shape the warmer is on waits for it, one that wants
another builds it itself.

**Families and the Shape menu.** Every shape has a `Shape.family`, and
`geometry.MENU` orders them into the menu's sections: **4D** (regular
polytopes; the 5-cell, tesseract, 24-cell and 600-cell families;
Catalan duals; star polychora; prisms and pyramids; surfaces and
fibrations), **3D** (surfaces, Platonic, Archimedean and
Catalan solids, star polyhedra, compounds, mathematical toys) and
**Scenes**. `geometry.menu()` lists them; within a family, index order.
The index stays the identity, so the menu's order never reaches a preset
(`tests/test_catalog.py::test_the_menu_holds_every_shape_once_by_kind`).

| # | Shape | Family | F | V | E |
|---|---|---|---|---|---|
| 27 | Tetrahedron | Platonic solids | 4 | 4 | 6 |
| 28 | Cube | Platonic solids | 6 | 8 | 12 |
| 29 | Octahedron | Platonic solids | 8 | 6 | 12 |
| 30 | Dodecahedron | Platonic solids | 12 | 20 | 30 |
| 31 | Icosahedron | Platonic solids | 20 | 12 | 30 |
| 32 | Cuboctahedron | Archimedean solids | 14 | 12 | 24 |
| 33 | Truncated octahedron | Archimedean solids | 14 | 24 | 36 |
| 34 | Rhombicuboctahedron | Archimedean solids | 26 | 24 | 48 |
| 35 | Snub cube | Archimedean solids | 38 | 24 | 60 |
| 36 | Icosidodecahedron | Archimedean solids | 32 | 30 | 60 |
| 37 | Truncated icosahedron | Archimedean solids | 32 | 60 | 90 |
| 38 | Rhombic dodecahedron | Catalan solids | 12 | 14 | 24 |
| 39 | Rhombic triacontahedron | Catalan solids | 30 | 32 | 60 |
| 40 | Small stellated dodecahedron | Star polyhedra | 60 | 32 | 90 |
| 41 | Great stellated dodecahedron | Star polyhedra | 60 | 32 | 90 |
| 42 | Moravian star | Star polyhedra | 96 | 50 | 144 |
| 43 | Starburst | Star polyhedra | 60 | 32 | 90 |
| 44 | Stella octangula | Compounds | 8 | 8 | 12 |
| 45 | Five tetrahedra | Compounds | 20 | 20 | 30 |
| 46 | Five cubes | Compounds | 30 | 20 | 60 |
| 47 | Cube + octahedron | Compounds | 14 | 14 | 24 |
| 48 | Dodecahedron + icosahedron | Compounds | 32 | 32 | 60 |
| 49 | Hopf fibration | Surfaces and fibrations | 0 | 864 | 864 |
| 50 | Armillary sphere | Mathematical toys | 0 | 374 | 384 |
| 51 | Geodesic sphere | Mathematical toys | 180 | 92 | 270 |
| 52 | Sierpinski tetrahedron | Mathematical toys | 256 | 130 | 384 |
| 53 | Lissajous knot | Mathematical toys | 0 | 240 | 240 |
| 54 | Loxodrome | Mathematical toys | 0 | 240 | 240 |
| 55 | Orbit | Mathematical toys | 0 | 64 | 64 |
| 56 | Celestial tesseract | Scenes | 84 | 912 | 986 |
| 57 | Celestial cube | Scenes | 66 | 414 | 486 |
| 58 | Mysterium Cosmographicum | Scenes | 50 | 744 | 794 |
| 59 | Snub 24-cell | 24-cell family | 480 | 96 | 432 |
| 60 | Rectified 24-cell | 24-cell family | 240 | 96 | 288 |
| 61 | Bitruncated 5-cell | 5-cell family | 40 | 30 | 60 |
| 62 | Omnitruncated 5-cell | 5-cell family | 150 | 120 | 240 |
| 63 | Grand antiprism | 600-cell family | 720 | 100 | 500 |
| 64 | Disphenoidal 288-cell | Catalan duals | 576 | 48 | 336 |
| 65 | Truncated 5-cell | 5-cell family | 30 | 20 | 40 |
| 66 | Cantellated 5-cell | 5-cell family | 80 | 30 | 90 |
| 67 | Runcinated 5-cell | 5-cell family | 70 | 20 | 60 |
| 68 | Cantitruncated 5-cell | 5-cell family | 80 | 60 | 120 |
| 69 | Runcitruncated 5-cell | 5-cell family | 120 | 60 | 150 |
| 70 | Rectified tesseract | Tesseract family | 88 | 32 | 96 |
| 71 | Truncated 16-cell | Tesseract family | 96 | 48 | 120 |
| 72 | Cantellated tesseract | Tesseract family | 248 | 96 | 288 |
| 73 | Runcinated tesseract | Tesseract family | 208 | 64 | 192 |
| 74 | Bitruncated tesseract | Tesseract family | 120 | 96 | 192 |
| 75 | Cantitruncated tesseract | Tesseract family | 248 | 192 | 384 |
| 76 | Runcitruncated tesseract | Tesseract family | 368 | 192 | 480 |
| 77 | Runcitruncated 16-cell | Tesseract family | 368 | 192 | 480 |
| 78 | Omnitruncated tesseract | Tesseract family | 464 | 384 | 768 |
| 79 | Truncated 24-cell | 24-cell family | 240 | 192 | 384 |
| 80 | Cantellated 24-cell | 24-cell family | 720 | 288 | 864 |
| 81 | Runcinated 24-cell | 24-cell family | 672 | 144 | 576 |
| 82 | Bitruncated 24-cell | 24-cell family | 336 | 288 | 576 |
| 83 | Cantitruncated 24-cell | 24-cell family | 720 | 576 | 1152 |
| 84 | Rectified 600-cell | 600-cell family | 3600 | 720 | 3600 |
| 85 | Dual runcinated 5-cell | Catalan duals | 60 | 30 | 70 |
| 86 | Grand 600-cell | Star polychora | 1200 | 120 | 720 |
| 87 | Great 120-cell | Star polychora | 720 | 120 | 720 |
| 88 | Small stellated 120-cell | Star polychora | 0 | 120 | 1200 |
| 89 | Great grand stellated 120-cell | Star polychora | 0 | 600 | 1200 |
| 90 | 3,4-duoprism | Prisms and pyramids | 19 | 12 | 24 |
| 91 | 5,5-duoprism | Prisms and pyramids | 35 | 25 | 50 |
| 92 | 3,8-duoprism | Prisms and pyramids | 35 | 24 | 48 |
| 93 | 5,10-duoprism | Prisms and pyramids | 65 | 50 | 100 |
| 94 | 8,8-duoprism | Prisms and pyramids | 80 | 64 | 128 |
| 95 | Pentagonal antiprism prism | Prisms and pyramids | 44 | 20 | 50 |
| 96 | Heptagonal antiprism prism | Prisms and pyramids | 60 | 28 | 70 |
| 97 | Octagonal antiprism prism | Prisms and pyramids | 68 | 32 | 80 |
| 98 | Icosidodecahedral prism | Prisms and pyramids | 124 | 60 | 150 |
| 99 | Truncated icosahedral prism | Prisms and pyramids | 154 | 120 | 240 |

**Scenes** (`Shape.layers`, `geometry.Layer`). A scene is several shapes
in one frame sharing a centre — a glome round a tesseract round a star.
Each layer names a shape and has its own scale, line / face / point
weights, line width, tint and **spin** (a multiple of the view's angles:
−1 counter-turns, 0 holds still). A layer keeps its shape's `dims`, so
a 3D star turns in 3D inside a tesseract turning in 4D; a scene is 4D
when any layer is.
`geometry.shape_view` is what the renderer projects through: one shape is
`project_h` at `view_angles` (the old path, to the bit); a scene projects
each layer at its own angles. The scene's geometry is its layers' rows in
order (`geom()["layers"]`, `["style"]`); its faces are the layers' own.
Each edge's line density is its own layer's, so a 864-edge glome thins
out without thinning the star inside it.

**The 3D switch** (`view.three_d`, VIEW page "3D"). Holds a 4D shape's
4D pose and turns it as a rigid 3D body. The renderer draws a 4D shape
as R(ang)·body — `ViewState.body` a 4×4 turn applied first, None for
none — and, while the switch holds it (`ViewState.held`), as T(ang)·body,
T the 3D planes alone (`view_angles(i, ang, flat=True)`). On the frame
the switch changes, `ViewState.integrate` folds the pose into the body so
it is the same either side: going on, body ← T(ang)ᵀ·R(ang)·body; going
off, body ← R(ang)ᵀ·T(ang)·body. While it holds, every corner keeps its
w, so the 4D divide scales it by a fixed factor and the 3D turn is
rigid; the W planes stop, and a route on a W angle moves nothing. Off,
the shape goes on in 4D from where it is. Nothing jumps either way
(`tests/test_shapes4d.py::test_the_3d_switch_never_jumps_on_or_off`,
`::test_while_it_holds_a_4d_shape_turns_rigidly_in_3d`). Holding the W
angles alone would not do: the engine turns the 3D planes before the W
planes, so a 3D turn under held W angles still moves w. `camera.reset`
and `rot.reset_w` take the body back out. A 3D shape is the same with
the switch on or off.

**A new shape** goes at the end of `SHAPES` (the index is its identity),
says whether it is 4D or 3D (`dims`), and gets a row in the V/E table
above. A 3D shape is built at w = 0; a 4D one must clear `VOLUME_FLOOR`
through each W plane. Record its digest with `uv run python
tests/test_shapes4d.py --record`, and say so in the commit; a polytope's
digest must never move.

## 2. Rendering

**The transform** (plan 26, one camera): the CPU rotates the shape in
4D across six planes (`rot.*`), projects 4D→3D and applies the
`camera.yaw` / `camera.pitch` turntable — the shape's world pose
(`geometry.world_points`); the vertex shaders take it to the screen
through one shared 4×4: the shape's world transform `u_model`
(`geometry.model_matrix`: `camera.zoom` a scale about the world origin,
then `camera.pan`) and the eye `u_vp` (`geometry.eye_matrix`). Edges are
quads expanded in the vertex shader from their two 3D ends, whose width
and alpha follow w-depth (the near half glows), with brightness
compensated for edge count so the 120-cell does not clip to a blob;
points are red quads, each a whole number of pixels across. Both carry a
real depth. `geometry.project` / `project_h`, the old CPU path to 2D,
stay the parity oracle.

**The eye** is a fixed perspective camera on the world's +z axis looking
at the origin: `eye.fov` (47.6°, `geometry.EYE_FOV`, across the
picture's shorter side; 10–120°) and `eye.distance` (3.78 shape radii,
`EYE_DISTANCE`; 1.5–40), on the CAMERA page under **eye**. They are
session params (group `eye`: no preset moves them) and not modulatable
(the camera is the rig; the shape is what moves). The defaults are
`project_h`'s old 3D divide: at zoom 1 and pan 0 every vertex lands
within 2.3e-13 px of `project_h` in float64 and 1.1e-4 px in float32,
against a bar of half a pixel
(`tests/test_camera.py::test_the_default_eye_lands_every_vertex_within_half_a_pixel_of_project_h`).
Clip planes 0.05 / 1000 (`EYE_NEAR` / `EYE_FAR`): depth only. An edge end
behind the eye is slid along the edge to just in front of it (`EYE_W`);
a point behind it is dropped — reachable only past zoom ≈ 3.8, where the
eye is inside the shape.

**Zoom and pan are the shape's, in the world.** `camera.zoom` scales the
shape about the world origin (the whole-frame 2D zoom is gone): a scaled
shape has its own perspective, and copies (`view.instances`) are copies
in the world, a cell `render.CELL` = 2.4 radii apart before the zoom.
`camera.pan.x/y` are in world units — shape radii, ±12
(`params.PAN_RANGE`), y positive down the screen as it always was. A
preset, camera module or `camera/default.json` without `"units":
{"camera.pan": "world"}` stored logical px: `params.pan_world` divides
them by `geometry.PAN_REF_PX` = 324 (the default eye's px per unit at
1080p, the render cap and the party projector) at load, so an old
preset sits where it did on the 1080p projector (nearer the centre on a
smaller window); every save writes the marker, and the schema stays
`hyperspace.preset/2`. The mouse pans by cursor px / px-per-unit and the
wheel zooms about the point under the cursor (`app._px_per_unit`). The
ghost hands and a point cloud never follow `camera.*`: only the shape
moves.

**Strokes in world space or screen space** (`view.screen_strokes`,
"Screen strokes" on the VIEW page, a performance switch, off by
default; the owner's toggle of 2026-10-14). Off — world space — the
edges' width and the dots' radius are × `camera.zoom`, the pre-plan-26
feel: strokes grow and shrink with the shape, a sub-pixel width folding
into alpha. On — screen space — they keep their pixel weight whatever
the zoom. At zoom 1 both draw the same frame byte for byte. One line in
`draw_scene` (`sz`); the hands' strokes never change with it.

**Depth.** The scene's target (`render.SceneTarget`) has a depth
attachment. The see-through shape is painter-sorted as always and never
depth-tested against itself; it is depth-tested against the solid
geometry already drawn (hands, a point cloud), and its visible surface —
fragments with alpha over `render.DEPTH_ALPHA` = 0.25 — is written to
depth after its colour (`Renderer._depth_pass`), so a hand can pass
between its edges.

**Faces** are the true 2-faces, translucent and painter-sorted, with
face-local UVs. `shaders/patterns.glsl` paints them: `vec4 pattern(int
mode, vec2 uv, float fid)` (`.rgb` the colour, `.a` the intensity; `uv`
face-local, (0.5, 0.5) the centre, circumradius 0.5; `fid` the face's
index). Seventeen patterns (`view.pattern`, `params.PATTERNS` =
`patterns.NAMES`): FLAT, RINGS, PLAID, MOIRE, BLOOM, CAUSTIC, HEX,
SPIRAL, CELLS, PLASMA, WEAVE, EMBER, METER, PULSE, MARBLE, TRUCHET,
KALEIDO. Shared colour helpers (`hsv`, `pal`, `hue_rotate`, `luma`, `TAU`,
`PI`) are `shaders/_common.glsl`, prepended. Both files hot-reload on
save; a broken edit keeps the last good program and shows the GLSL error
on the FACES page. The **bitmap** layer textures faces from a file; a bad
file leaves the plain faces. **Cut-through** matters only in overlay
mode.

**The eight pattern inputs** are `pattern.mod.0`–`.7`, the shader's
`u_mod[8]`: range 0–2.6, **1.0 the pattern as designed**. Each means one
kind of change on every pattern, so a route that feels right on one
reads the same on the next:

| k | Input | Registry label | 0 | 1 | 2.6 | Shader | Factory source |
|---|---|---|---|---|---|---|---|
| 0 | SCALE | Pattern scale | small and many (0.59×) | as designed | big and few (2.3×) | `k_size()` | SUB |
| 1 | GLOW | Pattern glow | dim (0.3× light) | as designed | white-hot (2.4×) | `finish()` | BASS |
| 2 | WARP | Pattern warp | straight | as designed | heavily warped | `warp(p, own)` | MIDB |
| 3 | SPEED | Pattern speed | frozen | as designed | 2.6× as fast | `u_ptime` (the renderer's) | MID |
| 4 | COLOUR | Pattern colour | grey | as designed | more hues, stronger | `finish()`, `spread_hue()` | UPR |
| 5 | SHARP | Pattern sharp | soft and broad | as designed | thin and crisp | `sharpen()`, `k_edge()` | AIR |
| 6 | HUE | Pattern hue | half a turn back | as designed | four fifths of a turn on | `finish()` | — (an LFO) |
| 7 | SPREAD | Pattern spread | every face in unison | as designed | each face its own phase and colour | `face_rad`, `face_turn`, `face_gold`, `face_k1` | — (a macro or knob) |

The order is for the factory routes, lane *i* → input *i*: the sub
swells, the kick flashes, the low mids bend, the mids set the pace, the
upper mids flare the colour, the air sharpens. A straight design stays
straight from WARP 0 to 1 and bends above 1; a design whose faces play
in unison stays in step from SPREAD 0 to 1 and parts above. GLOW keeps
30% of the light at 0. BLOOM has seven petals, SPIRAL five arms and
KALEIDO six wedges, whatever the inputs. FLAT reads none.

- **`hyperspace/patterns.py`** is where the convention lives, as data,
  importing nothing: `INPUTS` (`name`, `meaning`, `why`), the index
  constants `SCALE` … `SPREAD`, `MODES` (`name`, `about`, and `does`: what
  each input does in that mode in a few words, `""` where it reads none),
  `NAMES`, `effect(mode, k)`, `ignores(mode)`, `label(k)` and `tip(k)`.
  `params` takes the mode names and each input's label and tip from it;
  the FACES page takes the per-mode phrases (29 characters at most, so
  each fits a row).
- **In the shader** a mode reads its inputs only through the accessors
  `m_scale()` … `m_spread()` and the helpers on them; GLOW, HUE and
  COLOUR's grey end are one `finish()` over every mode, each term the
  identity at 1.0. Mode bodies are in `design()` or a function of their
  own (`meter`, `pulse`, …); `pattern()` is `finish(design(...))`.
- **`u_ptime`** is the patterns' clock: the renderer integrates wall
  seconds × SPEED (`Renderer._pattern_clock`), once per frame, so a
  moving SPEED changes the rate and never jumps the phase. `u_time`
  (seconds since launch) is still uploaded; no mode reads it.
- **`u_levels[8]`, `u_nlevels`** are the analyzer's lanes, out / CEIL
  (0–1, low band first), and how many there are (0 with no audio): the
  app sets `Renderer.bands` each frame (`app._bands`). Read them through
  `band(i)`, an if-chain, never `u_levels[i]` (a constant index on every
  compiler). Only METER and PULSE do; every other mode is moved by the
  music only through its routed inputs.
- **A new mode** is a case in `design()` (or a function of its own) that
  reads the inputs only through the accessors and helpers, **plus** a
  `Mode` entry at the end of `patterns.MODES` — appended, never inserted,
  since a preset holds the mode as an index — with its one line and
  eight phrases. The tests hold the shader's cases, accessors and header
  to the table.
- **Checking the shader.** `uv run python tools/check_glsl.py` compiles
  the face, seed and tile shaders exactly as `render.py` assembles them
  with the Khronos reference compiler, `glslangValidator` (on the PATH;
  `glslang-tools` on Debian), which holds `#version 330` to the letter.
  It is an extra net: Mesa (the tests' driver) and glslang are both more
  lenient than Apple's GL in places, so only a launch on the Mac proves
  a mode compiles there.
- **The factory depth.** The factory lane → pattern routes push at
  `routing.PATTERN_DEPTH` = 0.35 on a base of 1, so an input rises by
  0.35 × the band's out: about 1.1 for a quiet band, 1.35 at nominal,
  about 1.86 on a kick; at depth 1 a loud band pinned its input at 2.6.
- **Pictures.** `tools/pattern_sheet.py` draws a sheet per mode
  (`mode-NN-*`), a sheet per input across every mode (`input-K-*`) and the
  old modes (`before-NN-*`) into `docs/plans/assets/22-face-patterns/`;
  `tools/pattern_cost.py` times every mode offscreen against FLAT
  (`b3-cost.txt`; software GL: ratios only — MARBLE is the dearest,
  4.19× FLAT on the 600-cell); `tools/faces_page_shots.py` shoots the
  FACES page from a hidden real window. `Renderer.pattern_tile(s, size,
  t_now, fid)` renders one face's pattern alone, for tools and tests.

**Instances** (`view.instances`, 0–4096 on a count taper: every count
to 64 one detent apart, then 40 detents a doubling): copies laid out by
`view.inst_layout` and moved by `view.inst_motion` (STILL, ORBIT, WAVE,
RIPPLE) with `inst_amp` and `inst_rate`. At 0 nothing is drawn but the
ground, the echoes, the effects and the hands carry on.

- *Flat layouts*, in the screen's plane: **GRID** (rows of ⌈√n⌉),
  **HEX** (a honeycomb spiral from the centre; a copy never moves as the
  count grows), **RING** (one circle, neighbours one cell apart).
- *3D lattices*, nearest neighbours one cell apart: **CUBIC**, **BCC**
  (body-centred), **FCC** (face-centred), **HCP** (hexagonal
  close-packed), **HEX PRISM** (stacked honeycombs) and **DIAMOND**.
  The camera's yaw and pitch turn the lattice as they turn each copy;
  `view.inst_persp` (Field depth, 0–1) is the field's own perspective —
  0 every copy one size, 1 the nearest drawn 2.5× the middle's. Far
  copies draw first and fade to a quarter. Fit off, a lattice grows as a
  ball from the centre; motion runs in 3D.
- `view.inst_spacing` (0.5–4 cells, log): the room between neighbours.
- **Fit** (`view.inst_fit`): every copy whole on the screen, none cut by
  its edge. A grid or honeycomb takes the rows and columns that give a
  copy the most room at the screen's aspect (a full rectangle when one is
  nearly as roomy — 12 is 4 × 3 at 16:9; a part row is centred) and
  partitions the screen into even cells, a copy in each. Zoom past 1
  snaps to whole cells — the screen shows k columns by j rows, its edges
  on cell boundaries — and pan moves the window a whole cell at a time;
  zoom below 1 shows the whole field. A ring or a lattice is framed whole
  and centred (a lattice as a brick of the screen's shape); zoom past 1
  magnifies it. One copy with Fit on fills the screen.

The copies are GPU instances (`field.py` places them, `render.py` draws
them): the shape is projected once a frame and each copy is one vec4 —
its centre, scale and alpha — so 4096 copies of the 120-cell upload what
one does (~0.4 MB a frame; 100 copies were 28 MB before) and copies wholly
off screen are not drawn. Edge widths and point sizes scale per copy and
fold into alpha below a pixel.

**The frame is a render graph** (`graph.py`, plan 26). `Renderer.draw_outputs`
settles the frame's size under the render cap, ticks the effect folder,
then builds or reuses the graph for this frame's outputs and evaluates
it; each render output gets its picture (§14). The node kinds:

| Kind | Classes (node names) | Takes | Makes |
|---|---|---|---|
| **Geometry** | `Shape` (`shape`), `Hands` (`ghost`, `ghost.2` …), `PointCloud` (`cloud`, `cloud.2` …) | its params | draw calls in the shared camera; no framebuffer of its own |
| **Scene** | `Scene` (`scene`) | any number of geometries (`geometry`, `geometry.2` … ports) | one colour + depth target: the solid geometries first (the hands, a cloud: depth written), then the see-through shape, painter-sorted and depth-tested against them |
| **Layer** | `HandsLayer` (`hands`, `hands.2`), `Readout` (`readout`), `Cover` (`cover`) | one geometry (the cover: the scene) | its own target: the hands alone with their own colour and depth; the guide and tethers' labels; the faces' coverage mask (`mask`) |
| **Composite** | `Composite` (`composite(scene+hands)`, `composite(hands)`, `composite(history)`) | `under`, `over` (and the scene's `depth`) | `over` laid on `under`: over, add or depth-aware |
| **Effect** | `Effect` (`acid`, `acid.2`, `palette` … in the scene's pipeline; `acid(scene+hands)`, `acid(hands)` in the others) | an image | one effect instance's pass (`fx.FxChain.run_one`) over its input; off this frame, its input read through (plan 30) |
| **Pipeline end** | `Fx` (`fx`, `fx(scene+hands)`, `fx(hands)`) | an image (the last effect of its run) | where the pipeline's picture lands: straight into its one output, or once into a frame texture; the stand-down, the error path |
| **History** | `History` (`history`), `Capture` (`capture`) | an image (+ the cover) | the echoes and the dream laid over its input; the capture into the ring, once a frame after every pipeline |
| **Output** | `Output` (`output.1` …) | `image`, `hands`, `readout`, `depth` | `Renderer._compose`: fit, flips, the hands over, the readout, the dim — or the five-step `outputs.Handoff` for a later output |

Ports are typed (`image`, `mask`, `geometry`, and `value`, declared and
used by no node: below); the graph refuses a wrong
type, an unknown port, a dependency outside the graph and a duplicate
name when it is built. A Scene or Layer *makes* a texture
(`image(frame)`, and `depth`); History, Composite and an Effect *paint*
(`paint(frame, dst)`) into the framebuffer their consumer hands them, so
the look-back composites straight into the first effect's half-float
input and the last effect writes straight into the window — no texture
quantises the picture between them. A pipeline's end (`Fx`) decides where the picture
lands: straight into its one output when that output is at the frame's
size, unflipped and on this context; otherwise once into a frame texture
every output of it shows. Node methods are `run`, `paint`, `draw`,
`image`, `depth`, never `apply`, `modulate`, `snapshot` or `set_value`,
and `graph.py` imports `moderngl`, `numpy`, `geometry` and `outputs` only
(`tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`).

**Evaluation.** `Graph.order` is dependency order — a depth-first walk,
dependencies first, ties in insertion order — computed when the graph is
built, never per frame; `Graph.evaluate` runs every node once.
`Renderer._graph_for` keeps the last graph and builds a new one
(`graph.default_graph`) only when its key changes: each output's scene /
hands / through switches (`graph_key`), the renderer's `Wiring` (below;
its placements included), the roles of the listed `cloud` devices and
the effect files present (`frozenset(fx.state.specs)`: an instance or a
file changed; an order change no longer exists, plan 33). What is per
frame: whether an effect of a run is on (`frame.fx_on`: a placed effect
does not count), which inputs each switch picks (`Frame.selects`), whether
each effect runs, and whether a hand drew decide which pipeline end each
output takes (`Output.settle`); a pipeline no output takes is skipped and
its nodes read 0 ms. Evaluating the frame this way moved no pixel of A0's
427 goldens. (Since plan 28 the *modulation* is a graph evaluated in
dependency order too, in `Router.modulate`: ARCHITECTURE §2.) For one default
output the order is `shape → ghost → scene → cover → hands → history →
plasma → acid → kaleido → … → huecycle → palette → fx → capture →
output.1`: one effect node per instance in the run the preset wires from
`frame` to `fx.image` (plan 33; in wire order, on or off), and none for an
effect the graph does not wire.

**The default graph** is today's frame, wired from each output's
switches: **scene** on, its `image` is the SCENE chain (`history → the
effects' run → fx`);
**hands** on, the hands' layer is laid over at the output, and its
readout on top; **through** with scene and hands, the layer is
composited onto the history before the effects (`composite(scene+hands)
→ fx(scene+hands)`), or with the scene off, alone through them
(`composite(hands) → fx(hands)`). With no effect on, or no hand drawn,
a through pipeline stands down for its fallback with the layer over
(`Fx.fallback`, `Output.settle`) — `outputs.route`'s table, as wiring.
The capture takes the scene. The renderer's `Wiring` (`graph.Wiring`,
`Renderer.wiring`, default today's) changes the rest, renderer-wide:

- `hands`: `layer` (today) or `scene` — the hands drawn inside the scene,
  solid; an output showing the scene shows them there (its hands switch
  then wires only the readout), and an output with the scene off still
  gets the layer. So the same hands can be in the scene on the projector
  and a clean layer on the glass. Inside the scene the hands are at full
  opacity (`ghost.alpha` sets only the layer; at 0 the hands are drawn
  nowhere), and the guide and tethers stay the readout, laid on at the
  outputs.
- `blend`: `over`, `add` or `depth` — how the layer is laid on. Depth-aware
  drops a layer texel where the scene's visible surface is nearer by more
  than `render.LAYER_DEPTH_BIAS` = 0.05 shape radii (both depths
  linearised; the scene's resolved out of its MSAA target on the first
  ask, `SceneTarget.depth_texture`). A later output's presenter lays a
  depth-aware layer plain over.
- `history`: `scene` (today) or `scene+hands` — the capture takes the
  layer laid on the scene (`composite(history)`); with the hands in the
  scene, the scene already holds them.
- `draw` and `extra`: the first hands node drawn `solid` or as `lines`,
  and the hands nodes after it (below).

Nothing in the app sets `Wiring` but a preset's `graph` section. The
OUTPUT page's "shows:" line says it in words ("scene + hands: in the
scene as lines", "· depth-aware"), its hover the loaded graph in one
line, and the LOOKBACK page "history: the scene · with the hands"
(`graph.hands_words`, `graph_words`, `history_words`).

**The hands** (`graph.Hands`, the `ghost.*` params' node) are `ghost.py`'s
five styles as geometry in the shared camera: `ghost.shared_camera`
takes the Leap's millimetres into the world through the calibration in
`hands.json` (§12) and the eye. A frame's poses are settled once
(`Ghost.settle`) for every draw of them. A hands node is timed by its
consumer: inside a scene its draw is its own SYSTEM line (`ghost`); its
layer's draw is the layer's line (`hands`).

**The graph in a preset** (`graph.read_graph`, `GraphSpec`,
`preset.GraphSection`). A preset may carry a `graph` section, before
`values`: the nodes that differ from the default graph, one JSON object
each, one per line. `tests/fixtures/presets/hands-lines.json` (a test
fixture) puts the hands in the scene as lines
and the history on the scene with the hands:

```json
"graph": {"nodes": [
 {"kind": "hands", "into": "scene", "draw": "lines"},
 {"kind": "history", "holds": "scene+hands"}
]}
```

| Kind | Keys | Left out |
|---|---|---|
| `hands` | `instance` (1, 2 …), `into` (`layer` / `scene`), `draw` (`solid` / `lines`), `laid` (`over` / `add` / `depth`, only on the node that makes the layer) | hands 1, a solid layer laid over |
| `effect` | `file`, `instance` (2 or more; 1 allowed when placed), `after` or `into` (a node's name: below) | every effect file once, in the chain |
| `history` | `holds` (`scene` / `scene+hands`) | the scene |
| `composite` (plan 28 N4) | `instance` (1, 2 …), `blend` (`over` / `add` / `depth`) | none: built only once a wire feeds it |

The kinds are `graph.NODE_KINDS` — the one place a kind is named. No
section, or `{"nodes": []}`, is the default graph; nothing that is a
param goes in it (an effect's on / mix / order, `ghost.*`, `dream.*` stay
in `values` or the show); a save writes it back in a fixed order. A
section this build cannot read — an unknown kind, a key a node does not
take, a value out of its choices, two nodes of one instance, two layers
— is a note on the preset strip and the default graph, and the section is
kept as the file had it and written back on save. (A placement it cannot
honour costs only that effect its place: below.) A point cloud is not a
kind here: clouds follow the device list (below), and `{"kind":
"cloud"}` is an unknown kind (plan 28 added none). Since plan 28 the
section may also carry a `wires` list (below). Undoing a load puts the
loaded preset's graph back before its values (`library.Marks`).

**Two of a node.** `{"kind": "effect", "file": "acid", "instance": 2}`
adds a second acid: the effect `acid.2` in `FxState`
(`set_instances`), its params `fx.acid.2.*` ("Acid 2 mix", performance
params in the preset's `values`), its own clock and place in the chain,
on the acid file's one compiled program. `{"kind": "hands", "instance":
2}` adds a second hands node `ghost.2`: its own `Ghost`
(`Renderer.ghost_of`) over its own state, its own session params
`ghost.2.on/alpha/mirror/guide/tethers/style` (`ghost.2.on` starts off),
its layer `hands.2` and its lone readout `readout.2`. Every `into:
"scene"` node is in the scene; the `into: "layer"` node (else the first)
makes the one layer, laid on the outputs without the hands in their
scene. A show holds `ghost.<n>.*` back until a preset's graph declares
the node, then seeds it. `draw: "lines"` draws a style's meshes as their
triangles' edges, one pixel wide (`ctx.wireframe`); the guide stays
solid.

**The effect nodes** (`graph.Effect`, plan 30 D0). Every effect instance
is an image node: one `image` port in, an image out, its params
`fx.<name>.*`, its pass `FxChain.run_one` on the file's one compiled
program (hot reload as before). Each pipeline's chain is a **run** of
them, one per instance in `Wiring.run` — every instance of the run, on or
off — between the pipeline's source and its end, so switching an effect
on or off changes no node and rebuilds nothing. Whether an effect runs is
asked once a frame (`Effect.on`: `FxState.live(name)` — `fx.on`, `fx.mix`,
its own `on` and `mix`, and that it compiled; no target, no order). **Off**, it is read through: it
paints its input straight into its consumer's framebuffer and its
`image` is its input's — no pass, no texture. **On**, it paints its
input into a texture of the effects' pool and runs its pass from there
into its consumer's framebuffer; read by two nodes, its picture is made
once into a pool texture held for the frame and shown 1:1 into each.
The pool (`FxChain.pool`, `Graph.pool`) is the chain's half-float
textures: none without an effect node, two for straight runs (they
alternate however long the run), one more per held picture; a held
texture is never handed to a consumer that paints into it
(`graph._spare`, `Effect._make(frame, avoid=dst)`). `FxChain.fit_pool`
releases it when a new graph needs fewer. The pipeline's **end**, `Fx`,
keeps the old node's name and jobs: it moves the clocks once a frame,
paints its input, counts `chain_runs`, and decides where the picture
lands (above). The faces' effect chain that plan 30 left inside the shape's
face drawing (`render.face_fx`, `FxChain.run`) is gone (plan 33): the
faces' effects are nodes on a branch into `shape.faces`.

**Placement** (plan 30 D1). An effect entry may say where it sits:
`after` a node — on that node's picture, every consumer of it reading
the effect — or `into` one — on that node's `image` input alone; one of
the two, never both. A placed entry may name instance 1 (the file
itself, then out of the chain). The proof fixtures (test fixtures):

```text
{"kind": "effect", "file": "palette", "after": "hands"}                  // palette-hands.json
{"kind": "effect", "file": "palette", "into": "output.2"}                // palette-glass.json
{"kind": "effect", "file": "acid", "instance": 2, "after": "scene"}      // acid-scene.json
```

- **The names** (`graph.placement_error`): `scene`, `hands`, `hands.<n>`,
  `history`, `output.<n>` and an effect instance this build has (a file
  on disk, or an extra instance the same section declares). `into`
  takes only the history, an output or an effect (the scene's and a
  layer's inputs are geometry); `after: "output.<n>"` means `into`; an
  effect never sits after or into itself.
- **Refusals** — both keys, a non-string (`null` included), a name
  outside the vocabulary, a loop of placed effects
  (`graph.placement_loops`, at read and again at build) — are a note on
  the preset strip ending "; the default placement" (`graph: palette
  after 'teapot' — this build places after scene, hands, hands.2 …,
  history, output.1 …, or an effect; the default placement`): that effect
  goes back to the chain at its order, the rest of the graph lands, and
  the section is kept as written (`GraphSpec.notes`).
- **Dormant.** A placement on a node the built graph lacks this frame
  (no hands layer, output 3 with two outputs, an output showing nothing,
  a file not on disk) builds no node and says why in `Graph.dormant`
  (`palette after hands — no hands layer this frame`); it never falls
  back into the chain, and the OUTPUT page lists it under the output
  blocks (`dormant: …`).
- **How it sits.** A placed effect is not in the run. After the scene or
  a layer it folds that texture once in its own `run`, before any
  pipeline paints, into a held pool texture every consumer reads; on a
  layer its pass keeps the ground see-through (`run_one(…, opaque=0)`),
  it is laid on at the layer's `ghost.alpha` with the layer's depth, and
  the layer's readout is split always (the guide and labels are never
  folded). Into an output, the output folds the frame texture it settled
  on (`Output.folds`) and that pipeline is never painted direct. After
  the history or an effect of the run it paints like any effect (one
  placed node per pipeline after a run's effect). `after` leaves the
  ports that read something else of the node alone (`Node.REFS`). A
  presenter is handed the folded hands or frame — possibly a half-float
  pool texture (the `Handoff` docstring). `frame.fx_on` is "an effect
  of a chain run is on" (`Graph.placed_names` left out), so a placed
  effect alone bends no pipeline: a through output stands down.
- **The words.** The OUTPUT "shows:" line adds the placements on what
  each output shows (`· palette on this output only`), its hover the
  graph line (`graph: palette on the hands`, `graph: acid ×2 · acid 2
  before the history`, or the dormant words), and the LOOKBACK line those
  on the history's way (`history: the scene · acid 2 before the
  history`) — `graph.placement_words`, `output_placement_words`,
  `history_words`, `graph_words(spec, dormant)`. The FX page's group
  headers say where an effect ends (`ui_fx.groups`: `→ faces`, `→ output 2`).

**The wire list; outputs as nodes** (plan 28 N4). A section may carry
`wires` beside `nodes`, one `{"from": "<node>", "to": "<node>.<port>"}`
per line, kept in the file's order:

```json
"graph": {"nodes": [
 {"kind": "hands", "into": "scene", "draw": "lines"},
 {"kind": "hands", "instance": 2}
],
"wires": [
 {"from": "hands.2", "to": "output.2.hands"}
]}
```

`from` is a node's one output — `scene`, `hands`, `hands.<n>`,
`history`, an effect instance (`palette`, `acid.2`), a composite; `to`
is one of the ports a preset may wire: `output.<n>.image`, `.hands`,
`.readout`, `history.image`, an effect's `image`, a composite's `under`
/ `over` (`graph.WIRE_TAKES`; geometry and mask ports are typed but not
wireable — a hands node's place stays its `into`). D1's placements are
the same wires written short (`after X` = `X → E.image`, `into Y` = `E
→ Y.image`); a section with only those is still written short, byte for
byte, and one read as wires is written as wires. **An output is a
node**: a wire into `output.<n>.image` shows that picture through the
output's own end (`graph.Wired`, `wire(output.<n>)` on SYSTEM), ignoring
its scene and through switches; into `.hands` it lays that node over
(depth-aware when the blend says so; on a through output it replaces the
switch's hands, which the effects then no longer bend); into `.readout`
that layer's guide. **An output no wire names keeps the session's
switches** — the rig's, not the look's — and a load never writes a
switch. The wires ride in `Wiring.wires`, so `Renderer._graph_for`
rebuilds when they change. A refused wire (a port of another type, a
node or port that does not exist, two wires into one port, the history
into `.hands`, a loop) is a note — `graph: wire ghost → output.1.image —
ghost makes geometry, output.1.image takes a picture; the default
wiring` — and that port keeps its default; the rest stands and the
section is kept as written. A malformed wire is an unreadable section
(the default graph). A wire on a node this frame lacks is dormant and
said. The canvas edits it (§6, the GRAPH page). An older build refuses
the `wires` key, and D1's keys, and opens such a preset as the default
graph with a note (register row 277).

**The `VALUE` port** (`graph.VALUE = "value"`, plan 30 D2): a fourth port
type, a scalar or small float vector a node publishes once a frame, for
the palette's two designed ports — a value out (the slice's hue, sat
and val ends, the anchors) for a lights sink (plan 29), and an
image-in `sample` port that would set its params from a bitmap. **No
node publishes or reads one**
(`tests/test_graph_effects.py::test_the_value_port_type_exists_and_no_node_uses_it`);
`modgraph.RENDER_VALUE` names it on the modulation side.

**The point cloud** (`graph.PointCloud`, plan 26 A4b). `app.main` hands
the renderer the device registry (`Renderer.cloud_source`); each listed
`cloud` device (§5) adds a node `cloud` (`cloud.2` …) as the default
scene's first geometry. It draws the latest frame of `cloud:<role>` as
one instanced quad per point through the eye — a hard round dot, alpha
1, depth tested and written, a whole number of pixels across — before
the see-through shape, so a dot in front of an edge hides it and an edge
in front of a dot is drawn over it. Its world transform is one uniform
scale about the world origin, `cloud.scale`; the shape's `camera.*` and
`rot.*` do not move it. The look is the session group `cloud`:
`cloud.size` (radius, logical px, 0.5–12, 2), `cloud.scale` (0.01–10,
0.3: the fixture knot at about the shape's size), `cloud.bright` (0–2,
1), `cloud.colors` (the source's colours, on; off or none, white) — no
panel row: Learn and ROUTING reach them. The points are uploaded only
when the cloud's (frame id, publish time) moves; a listed device whose
file is missing keeps its node, which draws nothing. With no `cloud`
entry the graph is node for node the one before.

In the frame's terms: the face picture (only while an effect is aimed at
the faces, made by the shape before the scene's target is bound) → the
scene → the coverage mask (when the look-back occludes) → the hands'
layer → the look-back composite → the frame's effects → the capture →
each output's picture, the hands over it, the readout and the master
dim. With the look-back, effects and ghost off and the dim at full, the
output is bit-identical to the scene pass alone. The renderer re-binds
its target on every exit, a raise included, so a failing node never
strands a framebuffer.

**The look-back** (`lookback.py`, LOOKBACK page) keeps an atlas of
downsampled echoes of past frames and one dream buffer, and composites
the scene over its own wake. **ECHOES**: brightness (`dream.echo_mix`),
fade time (`fade`, seconds), count (`echoes`), time apart (`gap`,
seconds), thumbnails, and how far back the trail reaches; echo time is
in seconds, so a trail is the same at 60 and 120 Hz. **DREAM**: the
worker's status, the layer as one menu (every conv layer of VGG16 and
every block of GoogLeNet, 25, grouped by net shallow → deep, each with a
short description and a longer one on hover — `lookback.LAYER_INFO`),
brightness (`mix`), speed (`k`, shown as frames to halve), strength
(`step`), passes (`steps`), linger (`mask_decay`), jitter, scales
(`octaves`), hue, saturation, tint, tint from, tint hue, tint sat, and a
swatch of the tint. **BOTH**: darken, contrast, shape hides (`occlude`),
detail (`res`). The page uses short labels; ROUTING, learn lines and the
desk use the registry's ("Echo time apart", "Dream speed"). All
`dream.*` params are presettable and modulatable except `gap`, `res` and
`layer`.

**The dream worker** (`dream.py`, torch, MPS when available) runs a few
gradient-ascent steps per submitted echo on its own thread; `submit`
never blocks and the latest result wins; `step × steps / k` is clamped so
a preset cannot run away. The weights (one file per net, VGG16 528 MB or
GoogLeNet 50 MB, whichever net the layer belongs to) are read from
`weights_dir`, then torch's hub cache, and downloaded there on first use.
A net is read once a run: every layer of it is a cut of the same loaded
stack, so a change between layers of one net is instant (the first layer
of a net takes about 1.5 s for VGG16). The deepest layers cost about half
again what conv3_3 does per frame and say "slower" in the menu.
If the worker cannot start, the reason is on the SYSTEM page, the
LOOKBACK page and the red banner, and the look-back runs echoes only; a
preset that asks for the dream with no worker is a warning, once.

**Effects** (`fx.py`, FX page, GRAPH). One GLSL file per effect in
`shaders/fx/` — thirteen ship: acid, deconverge, doublevision, fractals,
glimmer, huecycle, kaleido, palette, plasma, tripcolour, warp, wobble,
zoomblur (`_lib.glsl` is shared). **A new effect is a new `.glsl` file, not
Python**: every `// @param` uniform becomes `fx.<file>.<key>`, plus
`on mix speed blend` per effect (plan 33 removed `order` and `target`);
`// @mix <value>` sets the effect's default wet/dry (1 when absent);
`fx.on` bypasses every effect and `fx.mix` scales them. `// @order <n>`
is still parsed (`EffectSpec.order`) and read only by `graphmigrate`, to
give an old preset's effect without a saved order its place in that
preset's run; where an effect sits now is its wires. A new effect file
needs no `@order`.

**The palette** (plan 24, `shaders/fx/palette.glsl`, `@order 95` (read only by the migration, which puts it last in an old preset's run),
so, unplaced, last in the chain, after the look-back and before the dim — and
before the hands unless an output sends them through the effects; plan
30: a preset's graph may place it on the hands' layer only, one output
only, or the scene before the history). Off and at `@mix 0` by default, so switching it on changes
nothing until its mix is raised. `mode` is a `@param choice` (an enum,
drawn as a picker). **compress** (plan 30 N8, the owner's colour
compression) maps the whole HSV cylinder onto the closed slice `hue_from`
→ `hue_to` (degrees, up the wheel, through 360 when `to` < `from`;
`from = to` one hue, 0 → 360 the whole wheel) turned by `hue_turn`
(added to both ends, wraps — what a hand sweeping the hue rides),
`sat_from` → `sat_to`,
`val_from` → `val_to`: saturation and value by a linear map, never a
clamp (`from > to` inverts); the hue by the triangle fold (red on
`from`, cyan on `to`, no seam) for arcs up to 180°, its peak sliding
towards the far red above that so 360° is the identity. The defaults are
the whole cylinder, so on at mix 1 changes nothing on an opaque ground
(on a see-through one the premultiplied colour is scaled by alpha once
more). A document with the fold's old ids (`centre`/`width`,
`sat_lo`/`_hi`, `val_lo`/`_hi`) — values, routes, desk rows, macros — is
read as the slice on load (`palettecompat.palette_slice`, a leaf, from
`Presets.load_doc` and `library._module_values`; a row on the centre
goes to `hue_turn`). **gradient** maps brightness through the
first `anchors` (2–4) of four anchor colours, `a1`–`a4` hue / sat / val,
a grey ramp by default.
On a see-through ground the result is scaled by the pixel's alpha. A
palette is kept in a preset's values, or in a patch with its node (plan
40); until plan 40 a saved palette was an `fx` module preset, and the fx
module presets (`library/fx/*.json`) are retired (D6: no factory folder,
no strip on the FX page, `library.RETIRED_MODULES`; an old
`<library>/fx/` folder is ignored, its files untouched). The effects folder
is polled every 30 frames; a parse error keeps the last version, a compile
error skips the pass.

- **The page** (plan 33, rows 341 and 348): a browser of the effect nodes
  in the loaded graph, not a place structure lives. Bypass (`fx.on`) and
  mix (`fx.mix`) at the head. `ui_fx.groups(spec)` lists every effect
  instance, grouped by where its path ends: **Run** (in wire order),
  **→ faces**, **→ pattern media**, **→ backdrop**, **→ output N**,
  **→ <effect> aux**, any other end (the history, a D1 `after`), and
  **reaches nothing** last; an effect that ends in two places is listed
  under each. A row is the name (click to open its strip), an `on`
  check, a small `mix` and one state word: `running`, `off`, the
  `why_idle` reason ("the whole stack is bypassed", "FX mix is at 0",
  "its mix is at 0", "it ends on the faces, and Faces is off", "reaches
  nothing") or `error: …`. The `→ faces` header carries `fx.face_map`.
  Below the list, **Show on GRAPH** (`ui_graph.select_effect`) selects and
  centres the node, and the open **strip** is every param of that node
  (`ui_fx.strip`). The selection, `Panel.fx_selected`, is one name shared
  with GRAPH's side pane and saved nowhere. The strip packs params that
  share a stem and end `_lo`/`_hi` or `_hue`/`_sat`/`_val` onto one row
  (`ui_fx.strip_rows`), and the palette shows only its open mode's rows
  (`ui_fx.HIDDEN_BY_MODE`; the hidden ones stay routable). With nothing in
  the graph: "no effects in the graph — add one on GRAPH (right-click the
  canvas)". The page adds, removes, wires and reorders nothing; the chip
  grid and its drag, the placed grid, the order slider, the ONTO chips and
  the faces row are gone.
- **Adding, wiring and ordering are on GRAPH.** The right-click picker
  adds an effect (`acid.2`, …) or a switch **unwired**, faint and "reaches
  nothing", where the menu opened. An effect dropped on a render cable is
  **inserted** into it (`graphview.Edit.insert_effect(cable, file)`; the
  cable's right-click menu offers "insert effect ▸ <file>"). Dragging an
  effect already in the graph onto another cable moves it
  (`Edit.place_effect(cable, name)`: lifted out, the run closes over the
  gap, put on the cable; one undo step; a drop on its own cable or on
  empty canvas does nothing). Deleting a run cable lifts the effect it
  led into; deleting the last `frame → fx.image` is refused. An instance 1
  taken out of the run is kept unwired (`{"kind": "effect", "file": f}`),
  faint, and the section saves `/5`.
- **Where the faces get their picture.** `shape.faces` unwired, or wired
  straight from `pattern`, draws the pattern per face as before. Wired
  from `pattern` through effects, the pattern is painted into the first
  half-float texture, the effects run in turn and the last writes the
  1024² `face_pic` (`graph.FACE_PIC`); wired from anything else that
  picture is `u_pic`. `fx.face_map` (per face, or screen) says how the
  faces show it. The faces are translucent, so an effect reads faint
  there; Brightness lifts them. With a picture wired in, every face
  shows face 0's pattern phase; the echoes and the dream carry the
  faces' picture, never the frame's effects. The faces' effects are graph
  nodes: SYSTEM times each one on its own line, and a source that reads
  nothing (a lost channel) makes the faces show the pattern for that
  frame.
- **Where the pattern's media layer and the backdrop get theirs.**
  `pattern.media` wired straight from a channel is the raw channel
  texture (`Renderer._channel_layer`), as `view.media` was; from a branch
  it is the branch's picture at its head's size. `backdrop.image` wired
  straight from a channel is plan 32's `MediaNode` under the scene; from
  a branch it is laid under the scene in `grounded` at the frame size with
  `backdrop.alpha` applied (`Composite(under_alpha_of="backdrop_alpha")`).
  `view.media` and `backdrop.channel` are not params; `graph.source_into`
  and `graph.channel_into` read which channel a port is fed, through a
  switch's pick, for the FACES and MEDIA pages and Learn.

**The switch** (plan 33, rows 350 and 352; `graph.SwitchNode`,
`params.declare_switches`). Kind `switch`, instances `switch`, `switch.2`
(the naming rule below). Eight `IMAGE` inputs `in1` … `in8` and one out;
its picture is the selected input's, passed through at the size its
consumer asks: no pass, no texture of its own, a cut. `switch[.n].select`
is an enum (off, 1–8, modulatable, group `switch`) declared per switch
the graph names and saved with the preset's values; the picks live in
`ViewState.switch` and reach the frame as `Frame.selects`. **Only the
selected input runs:** `Graph.pulled(frame)` walks from every node with
no readers and follows each switch's pick only (cached per tuple of picks,
at most 256); `Graph.evaluate` skips `run` for a `MAKES` node or an
`Effect` that is not pulled, and a channel no pulled path reads is not
uploaded. Changing `select` rebuilds nothing. A pick of off, or of an
unwired input, reads nothing: the faces show the pattern, the backdrop
nothing. A switch that picks a channel feeding `pattern.media` reads it
raw, as a wire straight in would. The switch sits in GRAPH's MEDIA area.

**Branches and sizes** (plan 33). A picture is made once a frame per
**size** its consumers ask: the frame-size consumers (an output, a
composite, the backdrop, the history, `fx`, an `aux`) the frame's,
`shape.faces` 1024², `pattern.media` its head's own. `Frame.at(size)` is
the frame at another size, with its own pool (`Renderer.pool_at`) and
data keyed `(name, size)`; `Node.size_for(port, frame)` says what a port
asks. `Graph.at_frame` stops an effect only the faces read from being
folded at the frame's size too. Once a frame `Renderer._prune_sized`
releases any pool or sized texture the last frame did not use. A wired
effect's clock advances in frames its picture is not made (as a placed
effect's always did), so it can jump phase when it comes back; an
effect behind an unselected switch input stands still.

**Presets and the free graph** (plan 33, rows 343 and 346–347;
`hyperspace/graphmigrate.py`, `preset.py`). **Load:** `Presets.load_doc`
runs `graphmigrate.migrate(doc, specs, desk=)` on every document. A
section with no `frame`/`fx.image` run is given one: the effects that are
`on` and either at `mix > 0` or driven by a route, desk row, macro,
modifier or step (`graphmigrate.targets`), in `(@order or saved order,
name)` order; the effects aimed at the faces as `pattern → … →
shape.faces`; `view.media = k` and `backdrop.channel = k` as channel
wires; a route onto either as a switch with the old pick and the rows
retargeted to `switch.select`. An effect left out was off, so the
picture is the same; one something drives says so in a load note. (Until
plan 40, loading an fx module replaced the loaded graph's run with it —
`graphmigrate.module_runs`, `Presets._fx_module`; the fx module presets
are retired and those are gone. A reusable run is a patch now: §6, "Groups
and patches".) Switching on an effect that is in no run adds nothing to
the picture.
**Save:** always `hyperspace.preset/6` since row 394 (below, "Presets and
the wired frame"). Until then plan 33 wrote the lowest schema that lost
nothing — `/5` only for a graph `/4` could not say, else the section
stripped of the free graph's words and the retired values laid back so an
untouched `/2`–`/4` preset saved byte-identical; that save side
(`schema_of`, `needs_free`, `legacy_section`, `legacy_values`,
`with_retired`, `reordered`) is gone. The bytes those older builds wrote
(`tests/fixtures/plan33-v4-saves/`, `plan35-v5-saves/`) are kept as old
files to load. A person's own preset that drives a channel choice loads
with a switch.

**Presets and the wired frame** (plan 35, rows 372–393;
`graphmigrate.py`, `preset.py`, `graph.py`). **The marker.** A graph
section that says `"frame": "wired"` is a wired frame: its nodes and
wires are everything the renderer builds (`graph.build_graph`), and the
key is the section's own marker (`read_graph` knows no schema). Every
readable section becomes one on load: `Presets.load_doc` runs
`graphmigrate.migrate`, which runs plan 33's steps, then `renamed`, then
`wired_section`, and writes the frame `frame_wires` gives (today's frame
for the default switches) once into `output.all`. A window's mutes are
not in the file. `backdrop.history` is retired into the capture wire
(`lookback.capture`); a route or desk row on it is dropped with a note.
**The ids** are renamed in one table (`graph.NEW_IDS` / `OLD_IDS`,
`new_id` / `old_id`): `ghost` → `hands`, the hands layer → `hands.layer`,
`readout` → `hands.guide`, `history` → `lookback`, `media.<c>` →
`channel.<c>`, `output.N.readout` → `output.N.guide`, `eye` → `camera`.
**Params keep their ids** (`ghost.*`, `dream.*`, `media.<c>.*`, `eye.*`;
`graph.param_prefix` maps a node to its prefix), so no route, desk row or
binding moves. Old ids are read for good; an old id in a wired frame is
refused in words, and saved canvas positions follow the rename
(`graphmigrate.renamed_layout`; a dissolved node's position — `render:frame`,
`render:fx`, `render:capture` … — is dropped, so a re-read is the
identity). **Save (row 394, the owner, 2026-10-25: "anytime we update a
schema, both machines will comply with that"):** every performance preset
save is `hyperspace.preset/6` (`preset.WIRED_SCHEMA`; `Presets.document`)
in today's words — the wired frame the load or the GRAPH page landed (with
nothing loaded, the factory frame `graphmigrate.wired_of(Wiring())`),
today's node and canvas ids, every value the registry holds (the media
family, the envelopes and the sequencer included), the `media` section,
no retired id. An untouched `/2`–`/5` file therefore saves as `/6`, and
the `/6` is a fixed point: loaded and saved untouched again it is the same
bytes (`tests/test_graph_free.py::test_every_old_preset_saves_as_six_and_is_a_fixed_point`,
every corpus preset and fixture, `/2` to `/6`, the older builds'
recorded saves among them), drawing exactly its goldens
(`tests/test_golden_frames.py::test_every_preset_resaved_as_six_draws_its_goldens`).
Every reader stays: `VERSIONS = (2, 3, 4, 5, 6)`, each migrated on load.
What wrote older words — D1's lowest-schema rule (`schema_of`), R10's
round trip (`unwired`, `legacy_section`, `legacy_values`, `with_retired`,
`with_history`), R15's old canvas ids (`old_layout`) — is removed. **An
older build refuses a `/6` file by the ladder's words**, so both Macs run
the newest build (row 394 assumes it). **Migrating a library:**
`tools/migrate_library.py` (dry run by default; `--apply` backs the
library up to `~/Hyperspace/library-backup-<stamp>/` first, then rewrites
each preset in place, atomically, through `headless.resave` — the app's
own load and save — only where it loads, its `/6` is a fixed point and it
draws the same picture on the golden rig (`golden_frames.picture`);
`--force NAME` writes one anyway). **A new preset**
(`Presets.new`) is the library's fresh values, routes cleared, the desk
written as the default preset layer (`fresh_desk()`), and
`{"frame": "wired"}`; it is named `untitled` and dirty until saved. **Tools:**
`tools/golden_frames.py` writes each golden state as the output's own
wires with the mutes all on; `--signatures` adds a missing case to
`tests/fixtures/frame-signatures.json` from `build_graph` alone (never
re-records an existing one), and `--names` rewrites only the fixtures'
recorded node names and asserts the `goldens` list is unchanged.

**Feedback: the delay, the echoes and the resize** (plan 34, rows
353–371; `graph.Delay`, `graph.EchoNode`, `graph.ResizeNode`,
`params.declare_resizes`). Four node kinds, each added on GRAPH
(right-click ▸ pictures ▸ **delay** / **resize**, look-back ▸ **echo.k** /
**dream**) and saved as an entry in the section (`{"kind": "delay"}`,
`{"kind": "echo", "index": k}`, `{"kind": "dream"}`), instance names
`delay`, `delay.2` …. **The delay** is last frame's input (z⁻¹): a
half-float picture the renderer keeps under its name, at its input's own
size, so a loop drawn through one is legal (`scene → delay →
shape.faces` is an infinite mirror) and a loop through none is refused when
the section is read, in words that say to wire it through a delay. It has
no params: a decay, mix or tint is an effect or a composite after it. It
reads nothing on the first frame and after a frame its input read
nothing, and the faces then show the pattern. SYSTEM times it as
`delay(write)`. **The echoes** are the look-back's commits as pictures,
`echo.1` the newest, to `echo.32`; at the ring's size, cadence
(`dream.gap`) and 8 bits, which the node's words say; **the ring keeps
capturing for one with the look-back off**, and an echo past what the ring
holds, or one after `dream.res` changed, reads nothing for a frame or
more. `dream` is the dreamed picture, "no dream worker: reads nothing"
without the worker. **The resize** crops and makes a picture at a size of
its own, so a delay fed through it holds a small buffer and an effect after
it runs small. **`resize[.n].*` are a preset's values** (group `resize`,
declared from the section's entries, kept while the entry is, all
modulatable, in no module): `size` (the long side, 16–2048 in powers of
two; default 256), `aspect` (`input`, `square`), `fit` (`cover`,
`contain`, `stretch`), `filter` (`linear`, with mipmaps past a 2× shrink,
or `nearest`) and `crop_x`, `crop_y`, `crop_w`, `crop_h` (the rect's
centre and size, normalised on the input, y from the top; past the edge is
transparent). A crop is a value: an LFO on it rebuilds nothing. A size is
stepped, and a route on it remakes the delay pair and the effect pools
after the resize at each step, bounded by `SIZED_KEEP_FRAMES`. A loop
drag on GRAPH is refused red in `LOOP_FACES`, `LOOP_BACKDROP` or (any
other loop in a wired frame) `LOOP_PLAIN`. **Both Macs:** a graph with
a delay, resize, echo or dream saves `/6` like every preset (row 394),
which a plan 33/34 build refuses; both run the newest build. No factory
preset has a delay, resize, echo or dream. The nodes' internals (`delay(write)`) are not on the canvas.

**Node instances: the naming rule** (plan 26 A0; `params.instance_id`,
`params.instance_of`, pinned by `tests/test_params.py`). A render node's
params are `<node>.<key>`, where `<node>` is the node's prefix —
`fx.<file>` for an effect, `ghost` for the hands, `dream` for the
look-back. **The first instance of a node keeps today's ids**
(`fx.acid.mix`, `ghost.alpha`, `dream.mix`). Only an extra instance is
marked, and the marker is its number, 2 or more, as a segment **right
after the prefix**: `fx.acid.2.mix`, `ghost.2.alpha`, `dream.3.mix`.
The marker is never a new first segment: the first segment is the
group, the group decides whether a param is in a preset (`part_of`),
and an extra instance belongs where its first does. So a graph with one
instance of everything — every preset and binding written before the
graph — never migrates. No effect file and no param key may be purely
decimal, or it would read as a marker.

The rule as built (plan 26 A4): `fx.<file>.<n>.*` for an effect (the
effect named `acid.2` in `FxState`), `ghost.<n>.*` for a hands node,
its layer `hands.<n>` and readout `readout.<n>` (node names, not param
prefixes), and a point cloud's nodes `cloud.<n>` (which share `cloud.*`
for now). No `dream` instance exists yet. A load sorts the instance ids
in a preset's `values` (`params.is_instance_id`) against the graph it
lands, so an id whose node is not in the graph is an unknown id with a
note. `fx.parse` refuses a `@param` key of digits alone, and
`FxState.load` an effect file whose stem has a dot or is digits alone
(`acid.2.glsl` would read as an instance). The pipeline nodes
`fx(scene+hands)` and `composite(hands)` are names only, never param
prefixes.

**GPU time per node** (`render.PassTimer`): one `GL_TIME_ELAPSED` query
around each node a frame (a node that runs several times is summed; one
that did not run counts 0; queries never nest), read 3 frames late
(`LAG`) so the CPU never waits on the GPU, kept as a rolling median over
60 frames (`WINDOW`) in `Renderer.stats["gpu_ms"]`, in the graph's
order. The SYSTEM page shows "gpu per node, ms (median of the last
frames):" and one line per node (`Graph.timed`: every node that times
itself and every solid geometry a scene draws) plus, since plan 30, one
per effect that ran a pass that frame (`Graph.timed_in(frame)`, from
`frame.stats["effects"]`: `acid`, `huecycle` …, a placed one under its
source); a node that leaves the graph, or an effect switched off, leaves
the list a few frames later. The pipeline end's own `fx` line reads 0.00:
it runs no pass of its own, and its effects' time is on their lines. On
Apple's tile GPU a query is charged for whatever is flushed inside it,
so the per-effect split is indicative (party-acid: the old `fx` line
0.225 ms, the effects' lines summing to 0.078–0.089 ms; the frame's
wall time 1.34 → 1.44 ms median, about +0.1 ms, within the base's
spread but not nothing). Without timer queries `stats["gpu_note"]` says
why ("gpu: no GPU timer queries on this context …") and the pixels are
the same. Apple's driver reads some tiny nodes as 0.00; the figures are
GPU time, not the CPU's.

**Golden frames** (`tools/golden_frames.py`, `tests/golden/frames/`).
Every corpus preset (`golden_frames.CORPUS_PRESETS`: the twenty-four
presets the build shipped until 2026-10-28, kept as test data under
`tests/corpus/presets/`) is copied into a throwaway home and loaded
through the real `Presets`, with two synthetic hands
(`tests/fake_hands.py`: the left open, the right a fist) present or
absent through the real `HandsIO`, the ghost on, the LFOs and the
analyzer at rest (never stepped, never fed), the dream off, the preset's
own look-back kept, and drawn for 8 frames at 1/60 s on a pinned clock at
960×600, dpr 1: the eight `Switches` states as eight outputs of one
frame (output 1 4× MSAA like the window); `solo` (output 1 alone, drawn
direct) and, for the presets with an effect on,
`solo-scene+hands+through`; party-trip once at 3840×2160 (2×, 1080p
logical) under the 1080p cap; the other wirings (`in-scene/…`,
`depth/…`, `history+hands/…`); the fixture presets, hands present, in
the eight states (`FIXTURE_PRESETS`: `hands-lines` and plan 30's three
placements, `palette-hands`, `palette-glass`, `acid-scene`, and plan
28's two wire fixtures, `hands-glass-only` and `wired-outputs`); and a
recorded cloud listed in a scratch config (`cloud/…`). A golden is the
SHA-256 of the full-resolution RGBA frame, with a quarter-size PNG per
distinct picture and the route each state reached (a wired output's
route reads `none`, with a `"wired"` key naming its source): **596
goldens, 140 distinct pictures** (556 before plan 30, which recorded 24
for its fixtures, and plan 28's N4 16 for its own; neither moved one
recorded before it), recorded on `GL_RENDERER` "Apple
M3 Max" (GL_VERSION "4.1 Metal - 90.5"). `tests/test_golden_frames.py`
compares every hash exactly there and skips with a note on any other
renderer. The tool:

```bash
uv run python tools/golden_frames.py                          # diff; "all 596 frames match their goldens (…)"
uv run python tools/golden_frames.py --only party-trip,legacy6 # those presets only
uv run python tools/golden_frames.py --record                 # re-record every golden
uv run python tools/golden_frames.py --only hands-lines --record   # re-record those, keep the rest
```

A diff that finds moved frames prints `MOVED …` per frame and writes a
contact sheet (golden | now | difference ×4) to
`docs/plans/assets/26-render-graph/golden-diff-<presets or all>.png`; it
refuses to diff on another renderer. Re-record only what a change moved,
on the gate Mac, and name each moved frame and its one reason in the
commit and the PR; a moved frame for a change that should move nothing
means the change is wrong. Which WPs moved which frames, and why, is in
[`plans/26-render-graph.md`](plans/26-render-graph.md) (plan 30's and
plan 28's, none: [`plans/30-shader-nodes.md`](plans/30-shader-nodes.md),
[`plans/28-node-editor.md`](plans/28-node-editor.md)).

## 3. Running it

```bash
cd hyperspace-python
uv sync                 # every dependency, torch for the dream included
uv run hyperspace       # the render window and the control window
```

Two windows open: the **render window** (pure output, for the projector
or the glass; the mouse orbits, ⇧-drag or right-drag pans, scroll zooms
about the cursor) and the **control window** (the panel, the desk
diagram, the cheat sheet). Keys work from both, and from every extra
render output; while a text field in the panel is being typed into, keys
go to the field. More render outputs come from `[[output.screens]]` (§14).

- **Quit:** Esc or Q, or close any window.
- **Restart in place:** Cmd+R or the SYSTEM page's *Restart process*
  (`os.execv`: same PID, same terminal). Every open adapter (MIDI, the
  bridge, the hands, the dream worker) and then the
  audio stream are closed first, best effort, so a broken port never
  blocks an exit.
- **The cheat sheet** (`ui.CHEATSHEET`, the canonical list of keys) is
  off at every launch: `/` (or `?`), the gamepad's MENU or the APC40's
  DETAIL shows it.

Environment variables:

| Variable | Effect |
|---|---|
| `HYPERSPACE_HOME` | The home folder (§4). Default `~/Hyperspace`. |
| `HYPERSPACE_FRAMES` | Run that many frames, then exit (a windowed smoke test). |
| `PYGLFW_LIBRARY` | Which GLFW dylib to load; `app.py` sets it to the bundled one when unset. |
| `LEAPSDK_INSTALL_LOCATION` | Read by Ultraleap's `leap` package when the hand-tracking software is not at its default path (see SETUP). |

## 4. The home folder

Everything the app writes lives in two places that are one folder unless
you say otherwise: the **home**, `$HYPERSPACE_HOME` (default
`~/Hyperspace`), created on the first launch, holds this machine's own
files; the **library** holds the presets and shows. The library is the
home too, unless `[library] path` in `config.toml` points it at another
folder — typically a cloud-synced one shared with someone (see "The
shared library" below). The library has one tier (2026-10-28): nothing
ships with the app, every file in it is yours. All formats are plain JSON with a `schema`
string, and the library is watched: edit a file in an editor (or let a
cloud client sync one in) while the app runs and the loaded preset or show
follows within a couple of seconds. In code, `Library.home` is the library
root and `Library.machine` the home.

**The library** (`Library.home`):

| Path | What it is | Format |
|---|---|---|
| `presets/<slug>.json` | Your presets (§10). | `hyperspace.preset/2`, or `/3` when it uses plan 31's sequencer, envelopes or LFO count (below) |
| `projects/<slug>.hyp.json` | Your shows (the code calls them projects). | `hyperspace.project/2` |
| `patches/<slug>.json` | Your patches (plan 40): a group of GRAPH nodes and its boundary, spawned into a preset, never loaded. Written only by **save as patch…** / **update patch**. | `hyperspace.patch/1` |
| `<group>/<slug>.json` | Module presets, one registry group each (`band/`, `dream/`, `hands/`, `view/` …). An `fx/` folder from before plan 40 is ignored: the fx module presets are retired (`library.RETIRED_MODULES`). | `hyperspace.preset/1` |
| `trash/<group>/<slug>.<YYYYMMDD-HHMMSS>.json` | Copies of your files taken before an overwrite, delete or rename. Never watched. | as the original |

**The home** (`Library.machine`; never in a shared folder):

| Path | What it is | Format |
|---|---|---|
| `config.toml` | The rig's settings (§5). Optional. | TOML |
| `bindings.json` | The session's controls only: keys, gamepad, and the APC40's invariant and global-layer rows. Delete it to get `hyperspace/bindings.default.json` back. | `hyperspace.bindings/3` |
| `hands.json` | The hands' calibrated ranges and the interaction box (§12). | `hyperspace.hands/2` |
| `windows.json` | Where the control window and each render output were at the last quit (§14). Machine-specific; safe to delete. | `hyperspace.windows/1` |
| `ui.json` | This Mac's panel settings: the GRAPH page's side-pane width (`graph.side_w`, PR #266), written when its grip is let go. Safe to delete. | plain JSON |
| `last_show` | One line: the file name of the show opened last on this machine. | text |
| `stall.log` | The watchdog's log (§15). | text |
| `weights/` | The dream's pretrained network weights, downloaded on first use. | binary |
| `media/` | This Mac's media files, ids `local:<relative path>` (plan 32; the shared ones are `<library>/media/`). Subfolders are groups. | any picture or video |
| `media-cache/thumbs/`, `media-cache/proxies/` | 160 px thumbnails and the MJPEG scrub proxies of clips ≤ 600 s, keyed by id + size + mtime. Never in the shared folder; safe to delete (made again). | PNG, MJPEG |
| `ndi/ndi-config.v1.json` | Written only when an `ndi` device lists `extra_ips`; NDI reads it through `NDI_CONFIG_DIR`. | NDI's JSON |

A `midi_map.json` or `config.toml` left in the working directory from an
old build is copied in on the first run; a `midi_map.json` in the home is
read once, only when `bindings.json` does not exist yet. A `bindings/`
folder of old routing presets is no longer read.

### What the app may rewrite, move or delete

| File | When | Kept first |
|---|---|---|
| `presets/<name>.json`, `patches/<name>.json`, `<group>/<name>.json` | A save over it, ⇧F1–F8, × on the PRESETS page (its list or its patches fold), a rename, **update patch**. Never a load or a spawn. | A copy in `trash/<group>/`. A save goes on if the copy fails (and says so); a × or a rename is refused. A save that writes the same text adds nothing. |
| `projects/<show>.hyp.json` | A pad change, save; a rename of a preset it names. Never a load. | The first write that puts a preset past slot 8: `<show>.hyp.json.bak-v2-bank8` (no copy, no write). A rename: a copy in `trash/projects/`. |
| `bindings.json` | At launch, when a newer build adds factory rows (the bank pads, OVERDUB, the clip-stop row, Home, the undo keys) where the control or key is free. A row you changed is left as you had it. | `bindings.json.bak-v<schema>` (`.bak-v3` for today's files; a dated name if that exists, never over any `.bak-*`). No copy, no rewrite: the table runs from memory for the session and the next launch tries again. |
| `hands.json` | A calibration sweep or "reset ranges". A schema-1 file is read as it is and never rewritten at launch. | The first rewrite of a schema-1 file: `hands.json.bak-v1`. |
| `<group>/…` | Restore from the trash. | Nothing to keep: a restore never writes over a file — a taken name restores as the next free name. |
| `trash/**` | **Empty trash.** | **Nothing. Emptying the trash is the one action in the app that keeps no copy.** It deletes exactly the files its popup lists, after a second click. |
| `windows.json`, `last_show` | Every quit and Cmd+R / every show load and save as. | Nothing (machine state). |

Every library write is atomic: the text goes to a dot-named temp file
beside the target (never `*.json`) and replaces it in one step, so a cloud
client never syncs a half-written preset.

### The trash

`library.to_trash` copies a file exclusively (a second copy in the same
second gets `-2`, `-3`), so nothing in the trash is ever overwritten.
Restore from the PRESETS page's **trash (n) ▸** popup, or copy a file back
into `<home>/<group>/` under its plain name.

### The shared library

`[library] path` (plan 25) points the library at a folder of its own —
typically one in a cloud drive (Dropbox, iCloud Drive, Google Drive,
Syncthing; the app does not care which) that two people share, so a
preset either of them saves shows up on the other's machine. The machine
files above stay in the home. Unset or `""` is the home, as always.
`tools/move_library.py DEST` copies an existing library into the folder
once (never over a file) and prints the two lines to add;
[SETUP.md](SETUP.md) has the steps.

- **Missing folder.** If the folder is not there at launch (a drive not
  mounted, a typo), the app never creates it and never falls back: a
  warning says so, the SYSTEM page's library line reads "NOT FOUND, saves
  are off" in red, nothing lists, and every save, delete, rename or
  restore is refused with "shared library not found at … — not saved".
  Fix the folder or the path and restart.
- **Conflict copies.** When both machines save the same preset while one
  is offline, the cloud client keeps both, e.g.
  `hi-frek (Dan's conflicted copy 2026-10-14).json` with the same name
  inside. The file whose stem is the name's slug keeps the name; the other
  is listed under its file stem. Load both, keep one, delete the other.
- **History.** The cloud service keeps file versions; there is no git in
  the library (the old home-as-git switch and the repo's snapshot
  folder were removed in plan 25 — a `.git` inside a cloud folder is a
  known corruption risk).
- **iCloud / Dropbox.** Mark the folder "Keep Downloaded" / "Available
  offline": an evicted file is invisible to the app.
- **Both Macs on one library run the newest build** (row 394, the
  owner's 2026-10-25 decision). Every save is `hyperspace.preset/6`; an
  older build refuses it with "schema … is not a hyperspace.preset" rather
  than load it and strip what it does not know on its next save. This build
  reads every older schema (`/2`–`/5`) and migrates it on load. To move a
  whole library at once: `uv run python tools/migrate_library.py` (a dry
  run), then `--apply`. Since plan 40 a preset with a group (GRAPH's
  **Group**) is `hyperspace.preset/8` and one without stays `/7` (register
  row 521, pending the owner); a build from before plan 40 refuses an `/8`.

The macro candidates to audition (plan 22) are in the owner's library;
[`plans/22-macro-candidates.md`](plans/22-macro-candidates.md) says what
each macro is meant to do.

## 5. `config.toml`

Optional, in the home. Every key has a default; `hyperspace/config.py`
(`DEFAULTS`, `SCREEN`) and `hyperspace/hands/core.py` (`DEFAULTS`) are the
source. A file that does not parse keeps the defaults and shows its error
on the SYSTEM page; a value of the wrong kind is its default with a note
on stderr and the SYSTEM page — never a dead launch.

```toml
[[devices]]             # the rig's devices (plan 27, devices.py), one table each, in poll order
role = "apc40"          # the name rows and the SYSTEM page use; unique; no ":"
kind = "midi"           # midi · gamepad · hands · bridge · midi-out · osc · cloud
enabled = true          # false: listed as `off`, nothing opened, its adapter never imported
port = "APC40"          # …then the kind's own keys (below)

[midi]                  # the MIDI table: still read when there is no [[devices]] list
enabled = true          # false: no MIDI at all (Learn's menus still work)
# port = "APC40"        # substring of the port name; unset = the profile's ("APC40")
profile = "apc40"       # device profile: hyperspace/apc40.py, or "generic" (generic.py)
map = "midi_map.json"   # an old map, read once when bindings.json does not exist

[output]                # output 1 and the control window
overlay = false         # true allows overlay mode; false: always opaque, T does nothing
monitor = -1            # screen index for the render window (and fullscreen); -1 = where it was last
control_monitor = -1    # screen index for the control window; -1 = where it was last
fullscreen = false
on_start = false        # launch straight into overlay (needs overlay = true)
passthrough = true      # overlay: clicks go to the window underneath
bg = 0.0                # overlay: ground, 0 see-through … 1 black
alpha = 1.0             # overlay: whole-window opacity

[[output.screens]]      # optional; one table per render output, at most 4 (§14)
name = "glass"
monitor = 1
fullscreen = true
scene = true            # launch values of this output's switches
hands = true
through = false
dim = 1.0               # under 0.1 is 0.1, with a note

[gamepad]
enabled = true          # an Xbox-layout pad over GLFW; inert when absent
usb = true              # no pad in GLFW: look for a wired Xbox 360 pad over libusb

[bridge]                # the analyzer's lanes out / external lanes in (bridge.py)
enabled = false
out = "IAC"             # port substring for the lanes out ("" = none)
in = ""                 # port substring for lanes in ("" = none); never the bus `out` uses
encoding = "pitch"      # "pitch": lane i → pitch bend on channel+i; "cc14": CC pairs
channel = 0             # 0-based
cc = 16                 # cc14: first MSB controller (0–31)
rate = 100              # messages a second per lane at most (0 = every frame)
send = ["lane:*"]       # "lane:*", "lane:3", "param:<id>", in lane order — read once,
                        # into bindings.json's sink rows (§13)
in_lanes = 16

[dream]                 # the look-back's dream worker (dream.py, torch)
enabled = true          # false: torch is never imported
device = "auto"         # "auto" (MPS when there, else CPU), "mps", "cpu"
precision = "fp32"      # or "fp16"
weights_dir = ""        # "" = <home>/weights

[hands]                 # Ultraleap hands (hands/)
enabled = false         # true opens the tracker; off, `leap` is never imported
mode = "desktop"        # camera looks up; "screentop" looks down; "hmd"
dofs = ["x", "y", "z", "roll", "pitch", "yaw"]   # per hand; also grab, pinch,
                        # grab_angle, pinch_mm, pinch_index … pinch_pinky
out = "Hyperspace Hands"   # MIDI out for a DAW: port substring, else a new virtual port ("" = none);
                           # becomes the `hands-daw` midi-out entry at load (§12)
channel = 16            # 1-based
cc = 102                # left hand cc…cc+n−1, right cc+n…cc+2n−1
presence = true         # a note on/off as each hand enters / leaves
note = 120              # left hand's presence note; right is note+1
min_confidence = 0.1
calibration = "hands.json"   # relative to the home
pinch_gates = true      # the eight thumb-to-finger switches
pinch_notes = true      # each as a note on/off to the DAW
pinch_note = 100        # left index…pinky = note…note+3, right note+4…note+7
tape = ""               # a recorded hand tape to play instead of the camera

[library]
path = ""               # "" = the home; else the shared library folder (§4)
```

Rules worth knowing:

- An `[overlay]` section is the old name of `[output]`: still read,
  merged under `[output]` (which wins), with a note asking for the rename.
- A `monitor` that is not a number, or an index no connected screen has,
  is −1 with a note (but see §14 for later outputs).
- With an `[[output.screens]]` list, output 1's entry supplies `monitor`
  and `fullscreen`; the scalar ones are ignored with a note. `overlay`,
  `on_start`, `passthrough`, `bg` and `alpha` stay scalar and belong to
  output 1 alone. An unknown key in an entry is a note; entries past the
  fourth are dropped.
- `[library] path` is expanded (`~`) and a relative path is relative to
  the config's folder; anything but text is `""` with a note. A leftover
  `git` key in `[library]` is ignored with a note asking you to remove it.
- `[hands] calibration` and `tape` are relative to the config's folder.

### Media

Plan 32. Pictures, videos and live feeds go onto eight channels (`a`–`h`);
the MEDIA page is where they are picked, and
[`plans/32-media-channels.md`](plans/32-media-channels.md) is the design
as built.

- **Folders.** `<library>/media/` is the shared folder (the plan 25 cloud
  folder, so both Macs see a file dropped into it; with no `[library]
  path` there is none) and `<home>/media/` is this Mac's. Both are scanned
  every 2 s: a dropped file appears without a relaunch, a removed one is
  `missing`, a cloud placeholder is `fetching`. A file added from anywhere
  (**Add file…**) is `file:<absolute path>`; **Copy to shared** turns it
  into `shared:`. A preset that names a `local:`, `file:` or live source
  this Mac lacks loads, shows black for it, and the MEDIA page's banner
  lists it.
- **Formats.** Stills: png, jpg, webp, bmp, tiff, heic. Video: mp4, mov,
  m4v, webm, mkv, avi, gif (see `media.adapters.VIDEO_EXT`).
  Files are decoded to at most 1920×1080, live feeds to 1280×720.
  There is no sound.
- **Live feeds** are `[[devices]]` entries; the factory template lists all
  three, commented: `kind = "ndi"` (optional `extra_ips = ["10.0.0.5"]` for
  a sender on another subnet; it is written to `<home>/ndi/ndi-config.v1.json`
  before `cyndilib` loads, which has not been verified against a real second
  subnet, and a change after NDI was first loaded needs a restart),
  `kind = "syphon"` and `kind = "camera"` (macOS asks for the camera on the
  first open; a refusal is `error: camera permission (System Settings ▸
  Privacy & Security ▸ Camera)`). NDI over a venue's Wi-Fi is hungry (full
  NDI ~100 Mb/s at 1080p): bring your own router.
- **Publishing.** `syphon = "<server name>"` and `ndi = "<sender name>"`
  on `[output]` or an `[[output.screens]]` entry publish that output's
  picture (a window at the render cap, `[output] render`); `window = false`
  on a later output makes it publish-only (no window). Output 1 always
  has a window. One SYSTEM line per publisher: `ndi out <name> — 60 fps,
  readback 4.0 ms`, in the warning colour with the error on a failure.
- **Dependencies** (all in the default install, imported only when a
  source opens): `av` (PyAV, bundles FFmpeg), `pillow-heif`,
  `syphon-python[opengl]` and `pyobjc-framework-avfoundation` (macOS
  only), `cyndilib` (its macOS wheel carries `libndi`; check the NDI SDK's
  licence before shipping a build). A live kind whose library is missing
  says so in its status (`cyndilib not installed`) instead of raising.
- **Both Macs on the newest build** (row 394): every preset saves
  `hyperspace.preset/6` — the free graph (plan 33), feedback (plan 34),
  the wired frame and its renamed node ids (plan 35) and the media section
  (plan 32) all in it — and an older build refuses it by the ladder's
  words. See "Presets and the wired frame" in §2. A pre-plan-32 preset's
  `view.bmp_*` values are dropped on load with a note
  (`bitmap file <path> is no longer read: put it on a media channel`); put
  the picture on a channel instead. The APC40's knob 7 still moves the faces'
  media opacity.

### The device list

Every input and output is a `[[devices]]` entry (plan 27). Without a
list, nothing changes: the four device tables above — `[gamepad]`,
`[midi]`, `[hands]`, `[bridge]`, with their defaults — become the
equivalent entries at load, in that order, as roles `pad`, `apc40` (the
MIDI profile's name), `leap` and `bridge` (`config._translate`), with
**one note per table the file holds** ("config: [midi] is now a
[[devices]] entry (role = 'apc40', kind = 'midi') — see config.py"),
on stderr and the SYSTEM page, until the file is renamed. With a list,
the list says, and each of those tables left in the file is ignored
with a note ("config: [[devices]] is listed, so [midi] is ignored — its
midi entry says"). The first entry of each of those kinds is folded back
into its table (`cfg["midi"]`, `cfg["hands"]`, …), so code that still
reads them reads the entry. `[dream]` stays a table: it is a worker, not
a device. Today's rig as a list (this exact block equals the old tables,
`tests/test_devices.py::test_todays_rig_as_a_devices_list_equals_the_old_tables`):

```toml
[[devices]]
role = "pad"
kind = "gamepad"

[[devices]]
role = "apc40"
kind = "midi"
port = "APC40"

[[devices]]
role = "leap"
kind = "hands"
enabled = false

[[devices]]
role = "bridge"
kind = "bridge"
enabled = false
```

Every entry has `role` (required, unique, no `:`), `kind` (required)
and `enabled` (true unless false; anything else is true with a note), and
then its kind's own keys, each defaulting as the old table does
(`config._kind_defaults`) — except `osc` and `cloud`, which have no old
table: their defaults live in `osc.py` (`DEFAULT_HOST`, `DEFAULT_PORT`,
`TIMEOUT_S`, `Layout`) and `devices.CloudDevice`, and config passes their
keys through unchecked:

| Kind | Its keys (defaults) |
|---|---|
| `midi` | `port` (a substring; required for `generic`), `profile` (`"apc40"` or `"generic"`), `map` |
| `gamepad` | `usb` (`true`; the one USB reader is lent to the first `usb = true` pad with no GLFW joystick), `joystick` (none: the next free GLFW joystick; `0`–`15` pins that index — anything else is a note and dropped) |
| `hands` | the whole `[hands]` table (`hands/core.py` `DEFAULTS`); a relative `calibration` or `tape` is the config's folder's |
| `bridge` | `out` (`"IAC"`), `in` (`""`), `encoding` (`"pitch"`), `channel` (0), `cc` (16), `rate` (100), `send` (`["lane:*"]`, read once into sink rows, §13), `in_lanes` (16) |
| `midi-out` | `port` (required), `virtual` (`true`: make a virtual port of that name when none matches), `carries` (a hands role whose DAW messages it sends), `encoding`, `channel`, `cc`, `rate` (its sink rows' wire, as the bridge's; `config.MIDI_OUT`) |
| `osc` | `host` (`"0.0.0.0"`), `port` (9000), `axes` (OSC addresses, `["/x", "/y"]`; none by default), `hits` (addresses; none), `rest` (a number, or a table per address; 0), `range` (`[0, 1]`), `timeout` (5 s), `hold` (`true`) — checked by `osc.Layout` when the device opens |
| `cloud` | `file` (required; relative to the home), `rate` (the file's), `loop` (`true`) |

A missing or bad `role`, a role listed twice, or no `kind` drops the
entry with a note; an unknown kind is kept as an `error: unknown kind
'x'` line. A kind's keys are checked when the device opens: a bad value
is an `error: …` line on SYSTEM and one note, never a dead launch.
**`[hands] out`** — on the old table or on a hands entry — becomes a
`midi-out` entry right after the first enabled hands entry (`role =
"hands-daw"`, `port` = the old `out`, `carries` = the hands' role),
unless the list already has a `midi-out` carrying that role; one note
only when the file wrote `out` itself (`config._daw`).

**The list is watched.** Every 30 frames (`devices.WATCH_FRAMES`) the
registry looks at `config.toml`'s mtime; when it moved it re-reads the
device list only (`config.read_devices`; nothing else in the file is
re-applied). A parse error or an entry that would be dropped is one note
— "config: [[devices]] not applied — … — the old list stands" — and
nothing changes; otherwise an unchanged entry keeps its device, a
changed one is closed and opened again ("devices: apc40 changed —
reopened"), a new one opens ("added"), one that left closes ("removed").
Everything else in `config.toml` still needs a relaunch.

**A device that fails** to open (a missing tape or recording, a busy UDP
port, a bad key) is an `error: …` line and one note, tried again every
2 s five times, then every 10 s, and comes up with no relaunch; one whose
hardware is simply absent is `lost` and looks for it itself. A device
that raises on a frame shows the error on its line and the hot-reload
toast; the frame and every other device go on. The registry claims
(scheme, role), not scheme (plan 27 B6): **two pads** both open — the
first enabled `gamepad` entry is the primary (its rows unqualified,
`pad:A`, `axis:LX`), each later one publishes under its role
(`pad@p2:A`, `axis@p2:LX`) — but two enabled entries of a kind that
cannot qualify are not: a second hands device is `error: feeds 'hand',
which leap already feeds — not opened` (two Leaps are plan 29's). Each
pad reads its own controller: the next present GLFW joystick no other
pad has taken, in list order, or the entry's `joystick = n`; one whose
joystick leaves is `lost` and takes the next free one that appears (a
pinned one waits for its index; two entries pinned to one index: the
second is dropped with a note). **The libusb reader is one, lent, not
owned** (`gamepad.Claims.lend`): each poll it goes to the pad holding it
while that pad has `usb` on and no GLFW joystick (sticky), else to the
first `usb = true` pad in list order with no GLFW joystick; a pad that
finds a GLFW joystick hands it back that poll. So the Bluetooth pad
plus the wired Afterglow work with both entries at the default `usb =
true`: the Bluetooth pad's line says `glfw 0  ·  usb: lent to p2`. The
reader closes when the last pad that could borrow it closes.

**A recorded point cloud** (`kind = "cloud"`, `file =
"clouds/knot.npz"`): a `devices.write_clouds` file (version-1 `.npz`:
`rate`, ragged `offsets`, `points`, optional `colors`) played at its own
rate against the frame clock (`loop = false` holds the last frame). It
publishes a `devices.PointCloud` — read-only N×3 float32 points, `t`, a
counting `frame`, `bounds`, optional colours — on the registry as
`cloud:<role>` (`DeviceRegistry.clouds`), never through the router;
the renderer's point-cloud node draws it in the scene (§2, "The point
cloud").
`tools/cloud_fixture.py`
writes the test fixture `tests/fixtures/clouds/knot.npz`.

## 6. The control window

The panel is built to be read from a few feet back in a dark room. A
rail of sixteen pages (`ui.PAGES`); the rail shows a red dirty dot
beside a page whose group has moved off its loaded preset. No page
scrolls at the control size (2372 × 900, `app.CONTROL_SIZE`;
`tests/test_ui_shell.py::test_every_page_fits_the_control_window`).
The window is two 4:3 panes: the panel opens at `ui.panel_w`, leaving
the desk diagram left of it a 4:3 slice of the height and the panel
the rest (never under `ui.PANEL_W`, 540). On a screen narrower than
that the window opens as wide as the screen (`placement.default_rect`),
the panel at 540 and the desk takes what is left.

| Page | What is on it |
|---|---|
| OUTPUT | The master dim; one block per render output (scene / hands / through ticks, its dim, what it shows in words); the screen and fullscreen of output 1; overlay and its click-through, ground and opacity (greyed, with the reason, unless `[output] overlay = true`). |
| VIEW | The cell-count readout and shape name, the shape, the six rotation planes, points / lines / rotate / faces, brightness, speed, 4D depth, instances (0–4096) with Fit beside it and, above one copy, the field rows: layout, motion, amp, rate; spacing, and a lattice's field depth; the six plane rates. |
| FACES | Faces, cut-through and the pattern mix; every pattern as a chip with a live swatch; the pattern on show and its line, ‹ ›; the eight pattern inputs by name, each with what it does on this pattern and what drives it (below). |
| BITMAP | A bitmap textured onto the faces: file, opacity, scale, mode. |
| CAMERA | Zoom (0.005–200×, log, so 1× sits at the knob's noon — far enough out to frame a field of thousands), yaw, pitch, pan, reset. |
| LOOKBACK | The look-back switch and three sections: ECHOES, DREAM, BOTH (§2). |
| FX | The effect stack (§2). |
| AUDIO | Listen to mic / Load track / Stop, the device and **rescan**, the transport, the master faders (gain, dynamics, trim). |
| ANALYZER | The band scene and Reset all, the meters, the band editor (spectrogram with the bands over it, the selected band's strip). |
| ROUTING | One page over the loaded preset: a pointer to GRAPH (where the routes and the modifiers are edited since plan 28 N7), desk rows, macros, the session's MIDI rows read-only, the sinks, and a filter (§9). |
| GRAPH | Both graphs on one canvas — devices, the analyzer, LFOs, modifiers, macros, params under their render nodes, the render graph, the outputs — laid out in titled areas by concern, every node collapsed by default, one wire a node pair, the idle macros off the canvas; the routes and the modifiers are edited here (below). |
| LFO | The tap-tempo clock and the LFOs (four by default, up to 16: `+ lfo`, `×`; above four all but the open strip fold to a line; plan 31). |
| SEQ | The step sequencer (plan 31, `ui_seq.py`): run · span · restart, length and swing; the 5 × 8 grid in the APC40's LED colours (the playhead's column in red, columns past the length dimmed); each lane's select, mute and envelope; a strip per envelope, one open, `+ env` for extras. |
| HANDS | The tracker, the box, the axes and their setup, feel and calibration, the ghost hands (§12). |
| PRESETS | The preset strip (◀ name ● ▶ · new · save · as…), every preset as a list filling the page (click loads; rename, ×), the trash at its foot, your patches under **patches** (rename and ×; a click spawns nothing — spawn is GRAPH's, plan 40), and one line for the show: its name ●, open ▾, save, as…, new (§10). |
| SYSTEM | Cheat sheet and desk-diagram switches, Restart process, hot reload status, the library path, config errors and notes, the dream worker's state, the stall log's line; **devices**: one line per `[[devices]]` entry — `role · kind · status · n sources · last` (MIDI: the port, its binding count, the last message; the pad's road and its GLFW joystick (`glfw 1`, plan 27 B6); the hands' tracker; a sink's `n sinks`, port and what it sent), `error:` lines in the warning colour; **midi**: knob smoothing, the desk log, the learn line; **gamepad**: the sticks' feel (a spring's preset beside it: snappy, smooth, bouncy, wobbly, lazy or custom, each drawn as its curve in the list), its knobs — attack and release, or a spring's perceptual duration and bounce — and beside them the feel's shape (how it carries a jump, a picture of the knobs) over the feel working live: the stick that moved most lately, as read (dim) and after the feel (white), over the last few seconds (`ui_feel.py`). |

**The FACES page** (`ui_patterns.py`), top to bottom:

- **Faces**, **Cut-through** and the pattern **mix**.
- **The patterns**: a chip per pattern, four to a row, each with a small
  live swatch of that pattern on the inputs as they are now; the one on
  show is solid red. Hover: the pattern's one line. Click: show it (one
  undo step). Right-click: `view.pattern`'s menu, to learn a knob that
  steps the patterns. The renderer draws the swatches, one a frame, only
  while the page is open (`Renderer.want_swatches`).
- **The pattern on show**: its name and its line, ‹ › at the right (round
  the ends). While `patterns.glsl` does not compile the line is the GLSL
  error (in full on hover; the last good version keeps drawing); while
  Faces is off it is "Faces is off" and a **faces on** chip.
- **INPUTS · <PATTERN>** with **all neutral** (every input back to 1.0, one
  undo step), and the pattern group's preset strip.
- **Eight inputs, two lines each.** First: the name, what it does on this
  pattern, and at the right what drives it — "SUB pushes +0.35", "K3 sets
  it", "macro.4 sets its base", "(off)" — a link to ROUTING filtered to
  that input. An input nothing drives offers **+ SUB** … **+ AIR**
  (inputs 0–5), **+ LFO 1** (HUE) or **+ LFO 2** (SPREAD): a click adds a
  push route at the factory depth into the loaded preset and stays on
  FACES; ⌘Z takes it back. Second: the slider (`base → effective` while
  driven, a white bar at the effective value) and a **1** chip back to
  neutral. On FLAT every row reads "FLAT reads no input", dimmed but
  live.
- A faint last line: "right-click an input: learn a knob or a hand".

Its fit at the control size is held by
`tests/test_ui_patterns.py::test_the_page_fits_with_every_row_driven_and_flat_or_the_longest_mode`,
but in font metrics that are not the Mac's (hand check 120).

**The GRAPH page** (`ui_graph.py` over the model `graphview.py`, plan
28; `imgui_bundle.imgui_node_editor`, its settings file off). One canvas
for the modulation and the render graph, rebuilt from the live table,
registry, Router, device registry and render graph whenever one changes
(`graphview.key`), its readings refreshed each frame. ROUTING and GRAPH
show one table: GRAPH edits the routes and the modifiers, ROUTING keeps
the desk, the macros, the session's rows and the sinks until it is
retired (plan 28 N7, the owner's decision of 2026-10-20).

- **Collapsed by default** (N7). Every node starts collapsed: its title
  and at most five short lines (`graphview.summary`: "137 ports · 97
  patched", its loudest patched port "> right y 0.83", its layer, "51
  params · 32 patched", a modifier's kind and output, a macro's knob), no
  row per port, an ``in`` stub at the left of its title and an ``out``
  stub at its right. Its **+** expands it (N2's ports: **patched only**
  on the head and the node's own **all ports / patched only** chip within;
  its port groups fold); **−** collapses it; the head's **expand all** /
  **collapse all** does every node. Which nodes are expanded is UI state
  only (not in the preset or the show; every node collapsed at launch).
- **One wire a node pair** (N7). While either end is collapsed, every
  value and trigger cable from one node to another is one wire
  (`graphview.VBundle`, `graphview.wiring`) from stub to stub: coloured
  by what it carries (trigger only when all are), 2.5 px plus 0.5 px a
  cable up to 7 px, faint while every cable is dormant. Hover: "<n>
  cables: <source port> → <param>, …" (ten, then "+ k more"). Selected,
  the side pane lists its rows (each route as ROUTING's row); Delete is
  refused: "expand a node to edit its cables". Both ends expanded, the
  real cables. Render cables stay one each, ending on a collapsed node's
  stub. On party-trip at 960 × 900: 64 wires for 238 cables, 1.27 ms.
- **Patching a collapsed node** (N7): drag a cable onto its stub; let go
  and pick one of its ports from the menu (only what `Edit.refusal` lets
  through), and it lands through `Edit.connect` as any drag. Right-click
  a node: expand / collapse and **learn ▸** its params, by group.

- **By concern** (N9, the owner's decision of 2026-10-20). The auto
  layout lays the canvas in five areas, left to right, each titled
  faintly on the canvas behind its boxes (30 canvas units, kept 18 px on
  screen zoomed out, no wider than the area): **CONTROLLERS** (devices,
  keys, placeholders, a desk template), **AUDIO** (the analyzer and the
  band, tempo, master, audio and band-scene params; **OTHER** — the
  preset, ui and desk params, the missing ones — under it in its
  column), **MODULATION** (LFOs, modifiers, macros), **GEOMETRY** (the
  shape, the hands, a cloud, the eye, and the scene, cover and hands'
  layer that draw them) and **SHADERS** (capture, history, effects,
  composites, outputs last), the render nodes by their depth within
  theirs and every other area by its own depth (an LFO or macro fed by
  nothing first, a modifier one past what feeds it), the shaders' chain
  wrapped in rows of four — so every wire runs left to right but a row's
  return. One table, `graphview.AREA`. The head's area chips
  (**CONTROLLERS · AUDIO · MODULATION · GEOMETRY · SHADERS**) and a click
  on a canvas title frame that area. A title stays 18 px on screen
  zoomed out, never under 12 px, a short word (CTRL, MOD …) when the
  long one will not fit before the next. A node with nothing in
  and nothing out (`graphview.is_idle`: a macro with no label and no
  subscriber, an LFO or a group node no cable reaches, a lost or off
  device, an effect switched off that no cable reaches — the chain then
  shows a half-faint through wire over it, which Delete only explains;
  never a modifier, the analyzer or another render node) is not drawn: its
  area shows one small box ("8 idle macros · 3 idle LFOs") whose **+**
  draws them under it to patch one; the picker still offers every idle
  macro. The head counts "31 nodes (22 idle)" on party-trip.
- **Nodes**, left to right: each listed device by role — the APC40 as
  *apc40* (every control, the invariant ones first) and *apc40 (SHIFT)*
  (the global layer's, faint unless SHIFT is latched), the hands folded
  as axes, pinches, grab, presence, dance; a device the rig lacks a grey
  placeholder named by role, its cables waiting; a preset's desk template
  one collapsed node (**+** opens it); the keys; the analyzer (a port per
  band); each LFO (its knobs as input ports); the modifiers; the macros
  (bus nodes); a node per param group no render node owns (`tempo`,
  `master` …); the render nodes with their params as input ports
  (`graphview.OWNERS`: `view` / `rot` / `pattern` on `shape`, `fx.acid.*`
  on `acid`, `dream.*` on `history`, `camera.*` on `eye`); the outputs.
- **Ports and cables.** A param has a round `mod` stub (one performer: a
  route's solid cable) and a square `base` stub (the setters: desk, pad
  and key rows, faint; a macro's base subscriber), and a `depth` stub
  while a route lands on it. Render cables join typed image / geometry /
  mask ports. Colour by kind, thickness by reading, faint when dormant.
  Hover: from → to, the reading, the depth, the `scale` and the gate; a
  cable a loop keeps off says so.
- **The head**: **expand all** / **collapse all**, **patched only**,
  **tidy** — every node collapsed, the idle lines shut, every position
  forgotten (one undo step), laid out again in the areas and the canvas
  framed on them; it says "laid out 31 nodes in 6 areas, every one
  collapsed · 22 idle off the canvas", or "already tidy" — and,
  only while something is selected on a page narrower than 720 px,
  **details beside** / **details below** (where the selection's pane
  goes; CONTROLS at 540 px puts it under the canvas, a page 720 px wide
  beside); then the counts (nodes, wires drawn, cables, live) and the
  last edit's or refusal's words.
- **Selection**: a route shows its ROUTING row, a bundle its rows, an
  effect's node its FX strip, a modifier's node the MODIFIERS strip's
  editor for it, stacked (`ui_routing.modifier_block`: inputs, params,
  live output, × remove).
- **Editing the modulation.** Drag a source onto a `mod` stub: the route
  a Learn would make (push or position, `learn.row_for`), Replace / Keep
  if the param is taken. A desk control onto a `base` stub: a desk learn
  (a preset-layer row); a pad button: the pad learn's session row. A
  macro onto `base` or a `depth` stub: a subscriber. A lane onto a
  modifier's `in`: its input. Drag from a patched input pin to another
  input pin to move a cable's end. Refused in words on the head: "a hand
  sets no base; aim at mod", "a macro sets a base or scales a depth; aim
  at base or a depth stub", "keys are the session's rows: map them on
  ROUTING", a SHIFT-node port into `base`. A free modifier let go over a
  cable is inserted into it (or a cable's right-click **insert ▸**).
- **Editing the render graph**: an image cable between two ports is a
  wire in the preset (§2), red with the file's words while it is wrong;
  a geometry cable from a hands node into the scene or layer sets its
  `into`.
- **Right-click**: on a `mod` stub, the param menu's Learn items (Learn
  desk, hand ▸, pad, a role, sink) — the completed row is a cable next
  frame; on a cable, insert and delete; on a node, delete (a modifier,
  a macro, an extra effect / hands node / composite), `draw solid` /
  `draw lines`, `laid over` / `add` / `depth`; on the canvas, the picker:
  **modifier ▸** a kind, **effect ▸** a file, **hands**, **composite**,
  **macro ▸** an idle one. Delete takes the selection: a session row's
  cable and the rig's nodes are refused in words; a default render cable
  too. Every edit is one undo step and dirties the preset.
- **Positions**: where a node is dropped is saved — in the preset's
  `layout` for the look's nodes (modifiers, macros, render nodes,
  performance groups, the template), in the show's for the rig's
  (devices, the analyzer, LFOs, outputs, session groups); an unplaced
  node takes its column by kind (a collapsed node its lines' height).
  SYSTEM shows `graph page: X ms median (N nodes, M cables)` (1.27 ms on
  party-trip at 960 × 900, collapsed; 2.66 ms with every node expanded;
  N2's page drew 2.3–2.8 ms).
- **The editor context** is held on the panel (a hot reload of
  `ui_graph` keeps it) and destroyed on quit and ⌘R before imgui; no
  `NodeEditor.json` is written.

**Groups and patches** (plan 40; `graphview.VGroup`, `ui_graph._group_node`,
`_region`, `_group_side`; `patches.py`; register rows 501–536).

- **Group.** With two or more nodes selected, the canvas's and a node's
  right-click menu offer **group N nodes** (`Edit.group`, one undo step).
  What a group may hold is `patches.select`'s rule, the same one a lift
  uses: effects, composites, switches, delays, resizes, copies, extra
  hands, mattes, cuts, segments, modifiers, LFO and envelope voices,
  macros — never the frame's singletons, an output, the camera, a cloud, a
  media channel or the sequencer, each refused in words on the head
  ("scene is the frame's; left out"). A node in another group moves, said;
  a group never holds a group. The group is `group.<n>` (one past the
  highest), named "group n", saved in the preset's `groups` (`/8`).
- **Folded** (the default, D4): one node at its members' top-left with no
  position of its own — its name, "group · n nodes · from <patch>", its
  status line (`devices.want_words` over the rows on its members:
  "waits for apc40 (lost): K1"), plan 37's thumbnail of its last picture
  outlet, then its pins: one typed pin per picture cable crossing in or
  out, an out pin per member lane leaving, one row per member param a rig
  row or crossing route lands on and per member modifier input read from
  outside (`VGroup.ports`, `ends`, `real`). Its internal cables are not
  drawn — **the one sanctioned exception to "no hidden edges"**; every
  crossing cable is re-ended at a pin, so folded drawn + hidden = open =
  ungrouped (`graphview.wiring(folded=)`). A drag onto a pin lands on the
  member's pin behind it (`real_pin`); a drop on the plain stub is refused
  in words. The head's "N hidden" counts folded members.
- **Open** (`+`; `−` folds; both one undo step and a preset edit): the
  members at their own positions inside a tinted region drawn under them
  on the canvas's draw list, its title an editor node over the band so it
  can be dragged (the members follow live, `_place_groups`; one step on
  release). A member dropped wholly outside the region it had leaves the
  group; several dropped out together are one step; the last to leave
  removes the group. A member deleted while grouped leaves the list at the
  next save (`Presets.live_groups`).
- **The group's menu**: open / fold, rename… (the side pane's name field),
  **save as patch…**, **update patch** (a group spawned from one), ungroup
  (`Edit.ungroup`: the list goes, every node and cable stays). Delete on a
  group node is refused in words.
- **The side pane** of a selected group: the name, its provenance, the
  status, a chip per member (a click opens the group and selects it), the
  boundary in words, the rows kept by the preset, and the chips **wire as
  saved** (a spawned group with open pins; free ports only, refused in
  words otherwise, one step), **save as patch…** and **update patch**,
  with the name / note form.
- **The browser**: **patches**, GRAPH's head's first chip after the hold
  chips, opens the list (every patch, by name), each
  line its name, note and boundary in words ("in: picture · out: picture ·
  wants: K1, right hand y"); a click spawns at the canvas's centre, and
  the canvas's right-click picker has **spawn ▸** at the click. A line
  dragged out of the list lights the nearest picture cable it can splice
  into (one inlet and one outlet of the cable's type; the section's cables,
  not the rig's bus), and letting go splices it in (`Edit.splice`). The
  list is re-read when the library's poll hands back a new listing.
- **Spawn** (`ui_graph.spawn` → `patches.spawn` → `Edit.spawn`): fresh ids
  by the instance rule (`acid` → `acid.2`), `mod.<next>`, the banks' next
  voices (envelopes from 6), a free macro; the landing goes through the
  doors in load order as one undo step, folded, its host ports open pins
  ("in · open (was scene)") for the session, the rename map on the hover
  ("spawned as acid → acid.2"). With conflicts, **the sheet** (in
  `ui_routing.modal`, ahead of Replace / Keep): one row per conflict, each
  on the patch to start, **keep all existing** / **take all**, the patch's
  wants, **Spawn** / **Cancel**; `Learn.hold` while it is up. A row the
  preset keeps lands in the group's `kept_by_host` and is said ("K1 kept
  by the preset"). After the landing the head says what its rows wait for
  ("waits for leap (not in this rig): right hand y"). No file is written.
- **Save as patch** (`Edit.save_patch` → `patches.lift` over
  `Presets.parts()` → `Library.save_patch`): refused on a member a patch
  may not hold or on another patch's name; writes
  `<library>/patches/<slug>.json` and nothing else; sets the group's
  `patch` (one step).
- **The wants chip.** GRAPH's head and the PRESET strip show **N devices
  missing** when a device the loaded preset's rows name is lost, off or
  not in the rig, its hover one line per role ("apc40 (lost): K1, K2, …");
  SYSTEM lists "wanted by the preset: leap — not in this rig; 3 rows wait".
  `devices.wants` is asked once a frame for all three
  (`ui_graph.panel_wants`). The footer says a device's coming and going
  ("apc40 connected — n controls live", "apc40 lost — n controls wait").

Every page that is a registry group carries a preset strip for its
module presets — except FX since plan 40: the fx module presets are
retired, so `ui_presets.strip` draws nothing for that group.

**Widgets.** A fader fills red from its origin to its value. A param a
performer (a hand, a band, an LFO) is driving shows its *setting* as the
handle and the effective value as a white ghost bar, and its hover names
the performer. Right-click any param, a row's label or an analyzer meter
for the menu (§9).

**The footer**, on every page: the frame rate; one message slot; `dim
40%` (or `dim black`) in the warning colour while the master dim is under
full; "· output 2 black" while an output shows nothing for another
reason; the show's name and its unsaved mark. The message slot shows the
newest line for 4 s (`ui.MESSAGE_S`): an undo's status, the library's
status and warnings ("saved TRIP 2 → F6", "F6: an empty slot"), what a
learn or unbind did, and — while nothing newer is up — an armed learn's
line or a picked desk control's line in red (a click on it cancels).

**The red banner** across the bottom of the control window names a live
render error or render stall, a render error that recovered, the
watchdog's warnings and why the dream worker is off; what is not live
stays until **dismiss**.

**The desk diagram** (`ui_desk.py`) draws the APC40 in the control
window's bottom-left, lit exactly as the device is, from the table — so
it works with no device. With the panel hidden (H, the APC40's DEVICE
ON/OFF, or the chip in the desk's header) it fills the control window.
Once it is big enough every lit control carries what it does (the
param's label, a bank pad's preset name, a step's amount); bright ink is
the layer that is up, grey an invariant control.

**Click a desk control, then a param.** A left click on a control in the
diagram picks it: it is framed on the desk and on its ROUTING line, and
every page but ROUTING is dimmed and takes no input except a click on a
param, which puts the control on that param in the loaded preset (one
undo step). A pick lets go by itself after 20 s with no click
(`ui_desk.PICK_S`), or on a click on it, the desk's empty ground or the
footer line. No click maps until the mouse has moved 12 px from the click
that picked. An invariant control, or any control while SHIFT is
latched, is picked only to show its line; the header says why. With
"Learn desk" armed, a click on the diagram completes the learn as a
knob would. **While a mappable control is picked, the desk offers this
preset's params** (plan 24) in a list on its empty ground under the
transport row (`ui_desk.OFFER`, which covers no control), ranked by
`learn.ranked` in four tiers — routed (a route or macro moves it), moved
(its base is off the group default), on (it belongs to an effect, the
look-back, the faces, the points or the lines, and that is on), on the
desk — never offering one the preset cannot show (`learn.cannot_show`).
A chip, "all params ▾" ("all ▾" on the small desk), opens the same list
and a menu per group of the rest. A click on an item maps the control
there through `Learn.map_picked`, the same road as a click on a page.

## 7. Keys and the gamepad

Every key and pad button is a row in `bindings.json` (factory rows in
`hyperspace/bindings.default.json`), so each rebinds there; the five
loop keys — Cmd+R, ↑, ↓, Esc, Q (`app.LOOP_KEYS`) — are the app's own.

| Key | Does |
|---|---|
| ← → | previous / next shape |
| Space | pause / resume rotation |
| P / L / F | points / lines / faces |
| 1–6 | toggle planes XY XZ YZ XW YW ZW |
| ↑ ↓ | 4D depth (hold accelerates) |
| [ ] · , . | brightness down / up · speed down / up |
| M | microphone on / off |
| K · 0 | play / pause the track · restart it |
| R | reset the view and camera |
| F1–F8 · ⇧F1–F8 | load pad 1–8 · save the live state as that pad's preset |
| B · ⇧B | tap tempo · the global LFO trigger |
| Cmd+Z or Ctrl+Z · with ⇧ | undo · redo |
| Home (fn ← on a laptop) | home: load the show's startup preset |
| H · / or ? | hide / show the panel · the cheat sheet |
| T · G | overlay on / off (only with `[output] overlay = true`) · overlay click-through |
| Cmd+R · Esc / Q | restart · quit |

**A press fires only its own chord**: a row fires when its modifiers are
exactly the held ones that some row on that key names (`SHIFT`, `SUPER`,
`CONTROL`), so ⌘⇧Z redoes and does not also undo; a modifier no row on
the key names is ignored.

**Gamepad** (Xbox layout, Bluetooth or USB; `gamepad.py` keeps its own
button map; the factory rows in `bindings.default.json`): A faces · Y
lines · B / X next / previous preset in the PRESETS list · LB / RB
previous / next shape · d-pad brightness (↑↓) and speed (←→) · left
stick orbit, its click resets the camera · right stick ↕ zoom, ↔ the
spin of the W planes, its click resets the 4D spin · LT / RT 4D depth
out / in · hold START to save the live state as a new preset. BACK is
free; Learn pad puts anything on it.

**The pad diagram** (`ui_pad.py`) draws that, live, instead of asking
anyone to trust this table: the pad at the top of the desk's column —
the switch is on the SYSTEM page, off at every launch — every control
where it sits on the device, lit where a row maps it and, once a unit is
40 × 28 px, carrying what it does. A grey label is one of the six axes
with no route on it, where the app's own hand is (orbit, zoom, the 4D
spin, the depth); a bright one is a row of `bindings.json`. The live pad
shows through it — a held button fills red, each stick sits in its well,
each axis fills its lane — and the picture is the same with no pad
plugged in. It is read-only: the hover names the control, its param and
its source, and Learn pad (right-click a param) is still the way onto a
control.

**The pad is a device** (plan 27): a `[[devices]] kind = "gamepad"`
entry (`role = "pad"` from the old `[gamepad]` table). It finds a pad
itself every poll — GLFW first, then a wired 360 pad over libusb with
`usb = true` — so absent it is `lost`, never an error; ⌘R and quit
close it, stopping the USB reader (`Pad.close`). In the scene-setter
slot it is polled, offered to an armed **Learn pad**
(`gamepad.learn_from`), delivers its rows (`Router.pad`: the `axis`
lanes fed, with names, labels and rests from `gamepad.publish`, then the
button and d-pad rows), then runs the sticks' default camera job
(`gamepad.steer`): every stick or trigger no route names moves its
camera param through `nudge` / `scale`, through the pad's feel
(`desk.pad.*`, SYSTEM → gamepad). **Several pads** (plan 27 B6): each
`gamepad` entry is a pad device reading its own controller (§5). The
first enabled one is the primary: the factory pad rows, every row
written before B6 and the sticks' camera job are its. A second pad
(`role = "p2"`) feeds `axis@p2` and fires only `pad@p2:…` / `hat@p2:…`
rows; it starts with none and gets them from Learn pad (which completes
on whichever pad moves) or ROUTING, where its axes are listed as
`axis@p2 left stick X`; its unrouted sticks do nothing. One feel for
every pad. Its SYSTEM line names the joystick it reads (`glfw 1`).

**A phone, or any OSC sender** (plan 27, `osc.py`): one `[[devices]]
kind = "osc"` entry, no code. Its role is its scheme: `axes = ["/x",
"/y"]` are the sources `phone:x`, `phone:y` (the address without its
`/`; `/1/fader3` is `phone:1/fader3`), routable like a hand axis and
offered on ROUTING; `hits = ["/hit"]` are buttons, `phone:hit`, whose
rows act when the velocity (the message's first number, 0–1, or 1 with
none) is above 0 — `abs` lands the velocity, `momentary` holds a toggle
until a 0 comes. An axis's value is the message's first number mapped
from `range` (default `[0, 1]`) and clamped; until a message arrives it
reads nothing, so no route moves at launch. The line reads `connected`
while a message came within `timeout` (5 s), `lost` otherwise; while
lost the axes hold their values unless `hold = false`. **Learn phone**
on a param's menu takes the next fader moved a quarter of its travel (a
route) or button pressed (a session row). The socket (UDP, `0.0.0.0:9000`
by default) is read without a thread in the scene-setter slot, at most
512 datagrams a frame; a datagram that is not OSC is counted on the line;
a port another program holds is an `error:` line, retried until it
frees. macOS asks once whether Python may accept incoming connections:
allow it. A role that is a row kind or a built-in scheme (`cc`, `pad`,
`lane`, `lfo`, `cloud`, …) is refused on open. Only a message's first
number is read; there is no OSC output yet.

**The sticks as dials** (a prototype — [`plans/28-gamepad-dial.md`](plans/28-gamepad-dial.md)).
Each stick is also read as a clock face of eight sectors, `N` straight up
then clockwise to `NW`: the angle picks the sector, the distance from
centre (0 at rest, 1 at the rim, the deadzone cut on the distance) is how
far that sector's lane reads. The lanes are `axis:L.N` … `axis:L.NW` and
`axis:R.N` … `axis:R.NW`, resting at 0, so a `push` route on one adds
nothing while the stick is let go. A route on any dial lane takes its
whole stick off the camera job. Two readings, per stick: **petal** (hard
sectors, the whole push to the one pointed into, a sticky border) and
**blend** (each lane a triangle about its own direction, so a sweep round
the rim crossfades one route into the next). The gamepad entry's `dial_left` /
`dial_right` (`[[devices]]`, or the old `[gamepad]` table) set where a launch starts (petal / blend); SYSTEM → gamepad
draws both faces, names each sector's route, and has the two readings and
**Swap dials** (`desk.pad.dial.*`, never saved). The **DIAL** factory
preset fills both clocks. With a Learn armed for the pad, a stick that
already has a dial route learns the sector it points into.

## 8. The APC40

Plug in an Akai APC40 (mk1) and it is found by name on launch and after
an unplug. On open it is put in Alternate Ableton Live mode (every LED
and knob ring is the host's); on close it is put back to generic mode.
The protocol, the default map (`DEFAULT_MAP`) and the glyphs are
`hyperspace/apc40.py`. `uv run python tools/midi_probe.py [port]`
echoes what a controller sends and lights an APC40, without the app.

**Glyphs** (`apc40.LAYOUT`), used on ROUTING rows, learn messages and the
diagram: K1–K8 track knobs, D1–D8 device knobs, S1–S8 track faders, SM
master fader, X crossfader, C cue knob, Gr·c the button field (rows 1–5
clip launch, 6 clip stop, 7 track select, 8 activator, 9 solo, 10
rec-arm; column 9 scene launch 1–5, STOP ALL, MASTER select), B1–B22 the
other buttons, ⇧ SHIFT. Akai's name is in each hover.

**Two layers under a latched SHIFT.** SHIFT's LED is lit while the
**global** layer (the session's) is up; otherwise the **preset** layer
(the loaded preset's own desk) is up. A control the up layer does not map
is dark and does nothing. **Invariant** controls mean the same on both
layers; none of them can be learned, mapped by a click or unbound, a
preset's desk row on one is dropped at load with a note, and each keeps
doing its job while a learn is armed.

| Control | Layer | Does |
|---|---|---|
| SM | invariant | master gain (the audio drive) |
| X (crossfader) | invariant | **master dim**: left black, right full |
| Clip row 1 (G1·1–8) | invariant | pads 1–8 (as F1–F8) |
| Clip rows 4–5 (G4·*, G5·*) | invariant | pads 9–16 and 17–24 |
| Clip stop 8 (G6·8) | invariant | **SAVE**: held, a bank pad's tap saves into its slot (lit while held) |
| Clip stops 1–7 (G6·1–7) | free | nothing by default (dark); Learn them for toggles |
| Scene launch 1–4 (G1·9–G4·9) | invariant | points, lines, faces, rotate (each LED the live state) |
| OVERDUB | invariant | **home** (lit while the show names a startup preset) |
| QUANT | invariant | next filled pad |
| SHIFT | invariant | latch the global layer |
| TAP TEMPO · NUDGE + / − · METRONOME | invariant | tap · shift the downbeat by a hundredth of a beat · the global LFO trigger (blinks on the beat) |
| PLAY · STOP · REC · CLIP/TRACK | invariant | track play · stop · microphone · restart the track |
| Track select · solo · rec-arm (G7, G9, G10; columns 1–6) | invariant | select that band · step its transfer function · reset it |
| ◀ ▶ | invariant | previous / next band |
| STOP ALL | invariant | Reset all bands |
| DEVICE ON/OFF · DETAIL | invariant | panel · cheat sheet |
| MASTER select · PAN | invariant | overlay · overlay click-through |
| D1–D8 | global | the selected band's strip: trim, contrast, transient, pre, post, attack, decay, threshold |
| K1–K5 | global | hand steadiness, response, catch, the selected axis's return, BPM (K6–K8 dark) |
| S1–S6 · S7 · S8 | global | band 1–6 post-drive · master dynamics · master trim (`apc40.SHIFT_FADERS`) |
| Clip row 2 · row 3, columns 1–3 | global | band scenes 1–8 · 9–11 |
| K1–K8 | preset (factory default) | brightness, speed, instances, pattern mix, field amp, field rate, bitmap opacity, zoom |
| D1–D4 | preset (factory default) | 4D depth, camera yaw, camera pitch, pattern (D5–D8 dark) |
| S1–S8 | preset | the preset's own fader rows; **none by default**, so dark unless the preset binds one |
| C (cue knob) | preset | step the shape, one click a shape |
| Activator (G8), columns 1–6 | preset | toggle planes ZW, XW, YW, XY, XZ, YZ |
| Row 3, columns 5–8 | preset | field motion STILL, ORBIT, WAVE, RIPPLE |
| Scene launch 5 (G5·9) | preset | reset view |
| ▲ ▼ | preset | brightness up / down |

The preset rows above are what a fresh preset starts with
(`apc40.SCENE` on D1–D4); a factory or user preset with knobs of its own
replaces all eight device knobs, and a preset with an empty desk has
every preset-layer control dark. D4 steps through the seventeen
patterns, which show only where faces are drawn. **The track faders are
the preset's** (plan 24): a preset binds them in its desk like the knobs
(`preset.track_fader(k, target)`), nothing is inherited, and a preset
that binds none leaves them dark. A preset file from before plan 24 may
still carry four scene-launch toggle rows; a load drops exactly those
four without a note (`routing.TOGGLE_DESK_ROWS`), and any other preset
row on an invariant control with the usual note.

**Desk templates** (plan 24). A template is a named binding set,
`<library>/desk/<slug>.json` (`{"schema": "hyperspace.desk/1", "name",
"note"?, "desk": [rows]}`), read by `Library.desk_template`; they sit
in the library, so a shared `[library] path` shares them. A preset that
says `"desk_template": "<name>"` keeps only its overrides in `"desk"`: a
row replaces every template row on the same control, and `{"source": …,
"dark": true}` leaves a template control unmapped. A load expands it
(`preset.expand_desk`: the template's rows not overridden, then the
overrides); a save writes the name and the rows that differ from the
template as the load read it (`compact_desk`), so a template edited on
disk reaches every preset that uses it at its next load and never turns
into overrides. A missing template is a note and the overrides alone. A
preset with no `desk_template` loads and saves as before. No UI writes a
template yet; `preset.template_doc` and a text editor do.

**The coverage report.** `uv run python tools/desk_coverage.py` loads
every preset in a scratch home and marks each of the preset layer's 38
controls (D1–D8, K1–K8, S1–S8 and the factory map's other preset-layer
controls) **mapped**, **dark** or **dead** — a row whose param the
preset cannot show (`learn.cannot_show`: a pattern knob with the faces
off, a bitmap knob with no bitmap, an effect's knob with it off, …). It
writes [`plans/assets/24-party-fixes/desk-coverage.md`](plans/assets/24-party-fixes/desk-coverage.md);
`--check` says whether that file is stale, `--stdout` prints it, and
`--library DIR` prints a report that adds that library's presets and
templates (copied, never written; the committed file is untouched). The
owner's bar for the authoring pass is at most four dark or dead per
preset; today no preset meets it.

**Bank pad lights** (rows 1, 4, 5): green while its preset is the loaded
one, amber while its slot holds another preset (velocity 5, Akai's
"yellow"; `apc40.filled_of`), dark when empty. The diagram draws amber at
half strength with the preset's name.

**Save on the desk: the two-handed save** (plan 24). Hold **SAVE**
(track 8's clip stop, `apc40.SAVE`) and tap a bank pad (clip rows 1, 4
and 5), on either layer: the live state is saved as a **new** user
preset named from the loaded one with the next free number (moo → moo
2; with nothing loaded, PRESET 1; it never overwrites a file), it
becomes the loaded preset and goes into
*that* pad's slot, and the show is written at once ("saved TRIP 2 →
F6", or "→ slot 10"); the pad blinks for 1.5 s (`midi.BLINK_S`). **A
filled pad takes the new preset too**: the slot points at it, and the
preset it named keeps its file and stays in the list, unpadded ("… (TRIP
2 is still in the preset list)"). Nothing is overwritten and nothing
goes to the trash (`library.Project.save_into`). The tap never loads the
pad; SAVE alone does nothing. SAVE is a `momentary` row on the session
param `desk.save`, lit while held: it is never latched or learned, a
reconnect lets go of it, and where the owner's `bindings.json` already
holds clip stop 8 it is not added and every launch says so. **Holding an
empty bank pad** for 0.6 s (`midi.HOLD_S`) still saves into it the same
way (`Project.save_empty`); holding a filled pad just loads it. To free
a pad, right-click its slot on the PRESETS page → **free this pad
(keeps the preset)**. (Until 2026-10-09 the clip-stop row was a SAVE AS
bar into the next empty slot.)

**Every load relights the whole desk** (plan 24). On a preset load, and
at power-up, every control of the layout that no active row draws is
sent dark (`MidiIO._dark_desk`), not only those a row once named, so a
light another program left on goes out.

**The desk log** (SYSTEM page, under **midi**, the fold "desk log"):
the last twenty presses (`midi.DESK_LOG_SIZE`), newest first, each with
the time, the control ("G1·5 (clip 1·5)"), what it did ("Preset →
TRIP", "nothing (no row on the preset layer)", "saved into slot 15: TRIP
2", "held: nothing saved (a filled pad only loads)") and the layer it
was read on ([preset], [global], or [both] for an invariant control).
Button presses, holds that fired and two-handed saves are logged; knob
and fader moves are not. It is in memory only.

**Knobs and faders.** The track and device knobs are endless encoders:
the app sets their position with the ring's CC, so a knob continues from
its ring after a layer switch or a preset load. The faders are real pots
with **soft pickup**: after a change they do nothing until moved through
the param's value. **A load lets go of every fader the new preset
binds**, so each picks up from the new preset; a fresh row starts from
where its fader physically is (the last value it sent), so a fader
already on the value catches on its first move. The session's faders —
the crossfader, MASTER and the band strip under SHIFT — keep their catch
through a load unless the load moved their param, so they carry on from
where they are. **On a layer switch** each layered fader starts again
from where it physically is and is caught only when its param already
sits there, so a fader moved on one layer never jumps the other layer's
param (the preset's on S1–S8, the band's under SHIFT). A fader not moved
since launch or a reconnect has no position, and catches only on a move
that lands on the value. A fader moved while its row is disabled, or
while an armed learn takes its messages, picks up again from where it is
(`MidiIO._passed_over`) rather than jumping. An older `bindings.json`
moves its eight invariant track-fader rows to the SHIFT layer once,
with a backup (`routing.FADER_SHIFT_ROWS`).

**Knob smoothing** (`desk.slew`, "Knob smoothing", SYSTEM page under
**midi**; off to 250 ms; the running app starts at **80 ms**,
`routing.SLEW_DEFAULT_S`, unless the show saved its own value). A knob
or fader row with op `abs` on a continuous, non-integer param glides to
each new value over that long instead of landing a detent at a time, and
comes to rest on the same detent it would have. Not smoothed: the cue
knob and every other relative row, buttons, and an `abs` row on an enum,
toggle, trigger or whole-number param. A value set meanwhile by anything
else stands and the glide stops; a preset load ends every glide but a
session param's; off, an unplug or a quit lands every value at once. The
setting is saved with the show, never with a preset, and is on no knob.

**Reconnect.** With no desk connected the app looks for it every 2 s
five times, then every 10 s (`midi.RECONNECT_S`, `RECONNECT_FAST`,
`RECONNECT_SLOW_S`); a desk that vanishes is looked for at the fast pace
again. Meanwhile its SYSTEM line reads `lost` and its rows wait; when it
comes, it gets its power-up and every light. `enabled = false` on its
entry (or `[midi] enabled = false` in the old form) stops all of it.

**Several desks** (plan 27). Each `[[devices]] kind = "midi"` entry is a
desk of its own — its `role`, its `port` and its `profile`: `apc40`, or
`generic` (`generic.py`: plain CC, note and pitch; the app sends it
nothing at all; every CC absolute with soft pickup, a note a toggle;
no layout, so its line counts 0 sources; the entry must name a `port`).
`bindings.json`'s top-level `"profile"` only says which profile its
unqualified rows were written for; the entry's profile is the desk's.
**One desk owns the unqualified rows** — every row in `bindings.json`
and in every preset before plan 27 (`cc:0:48`): the first MIDI entry
whose profile is `bindings.json`'s (`apc40`), else the first MIDI entry
listed (`DeviceRegistry.midi_roles`). **Any other desk's rows carry its
role** after `@` on the kind — `cc@launch:0:21`, `note@launch:0:40`,
`pitch@launch:3` (`routing.QUALIFIER`) — and Learn desk writes that form
for you; ROUTING and the footer say "MIDI CC 21 ch1 on launch". A knob
on one desk never moves another desk's row. **SHIFT** (`desk.shift`) is
the owning desk's latch; every other desk has a layer of its own
(`Bindings.layer_of(role)`), the preset layer, and no SHIFT — so with
the APC40 on SHIFT a second desk's rows still act and a learn on it
still lands; a preset load drops every desk to the preset layer; a
layer switch re-arms only that desk's faders. A desk learn replaces the
param's knob on the same desk only (one knob per param per desk). The
on-screen desk, the desk log and the panel's knob hints are the first
open MIDI desk's (`ui_desk.py` draws the APC40 only): list the APC40
first. A second APC40-profile desk gets its power-up and the lights of
its own rows but no SHIFT.

**Macros** (`macro.1`–`macro.8`) are knobs with subscribers: each
subscriber sets a param's base or scales a route's depth over its own
`from → to`. A hand on a macro moves only the depths.

## 9. Learn, Unbind and routing

The control model — the parameter registry, bases and effective values,
routes (`push` / `position`), one performer per param, the referee — is
[ARCHITECTURE.md](ARCHITECTURE.md) §3. What follows is
how it is operated.

**The right-click menu** opens on a param's widget, on a row's label and
on every analyzer meter. It lists what is bound — the preset's desk rows
("K2 (track knob 2)"), each route in words ("R height pushes +0.45"), the
session's rows dim — then:

- **Learn desk** — wherever a desk row can go, device plugged in or not.
  Completed only by the desk: a knob, a button, a fader, or a click on
  the diagram. The invariant controls keep working meanwhile (a fader
  moves, a bank pad loads — the learn then lands in the preset just
  loaded). With SHIFT latched any other control is refused in words
  and the learn stays armed: unlatch and the same learn lands.
- **Learn hand ▸ left / right** — only with a tracker, on a param a hand
  can drive (not a setting such as `ghost.mirror`), for the sides the
  rig's axes have. Completed only by an axis of that hand; the other
  hand and the desk do their own jobs meanwhile.
- **Learn pad** — while a pad is connected, wherever Learn desk is: a
  button or the d-pad makes a session row in `bindings.json` (written
  at once), a stick or a trigger a route in the preset (§7).
- **Learn <role>** — on a modulatable param, for any other listed device
  that feeds (plan 27; an OSC phone: "Learn phone"): completed only by
  that device — an OSC fader moved a quarter of its travel lands a
  route, a button a session row. What the menu offers is "desk" plus the
  devices' `wants` (`Learn.wants`).
- **Learn sink ▸** `<role>:<channel>` — on any param but a trigger, for
  every sink port the rig lists (`bridge:3 · pitch ch4`): sends the
  param's effective value out on that port (§13). It lands at once, as a
  session row in `bindings.json` — no question, no undo step, no preset
  dirt — and takes the port from whatever sent on it before.
- **Cancel learn** while this param is armed.
- **Unbind** — shown only when there is something to remove; a submenu
  ("desk — K2", "route — R height, LFO 1", "both") when there are both.
  Removes the preset's desk rows and every route on the param, as one
  undo step; never a session row.
- The hand rows' "Gate: … ▸" and "Route a lane here…".

**A learn writes into the loaded preset** — never `bindings.json` — and
lights its dirty dot until a save. A desk learn makes a preset-layer row;
the line says what let go ("learned view.bright ← D3 (device knob 3)
(into the preset); K1 let go"). A hand learn makes a route naming the
axis by name (`hand:right.pitch`), so a rig that reorders `[hands] dofs`
keeps its presets; a name the rig lacks is dormant. What it lands as:
a tilt, or a sideways or in/out move on an axis whose "Centred" is on,
**pushes** by `hands.learn_depth` (default 0.25, 0.05–1, HANDS page,
saved with the show) — it adds to the setting and is nothing while the
hand is level; height pushes onto a range centred on zero (a rate, an
angle, a pan, hue) and is the fader (`position`) on anything else; a
toggle, list, trigger or whole-number param always gets the fader. A
learn takes that axis's other routes with it (the line says "moved
from …"; one ⌘Z puts them back). An armed learn never times out.

**The ROUTING page** is one page over the loaded preset: its head (the
preset, its dirty dot, save / as…, which desk layer is up), then a
pointer line, "routes and modifiers: the GRAPH page" (a click opens
GRAPH: since plan 28 N7 the routes and the MODIFIERS strip are drawn and
edited there, ROUTING's own `_row` in GRAPH's side pane; their functions
stay in `ui_routing`; while the filter holds text its red count takes the
pointer's place), the desk with its dark controls, the macros and
their subscribers, the session's MIDI rows read-only, and the **sinks**
(plan 27: each sink row with a checkbox and a ×, both writing
`bindings.json`). "Route a lane here…" adds its route and opens GRAPH. A
route's source list (its row's combo) is the analyzer's lanes, LFO 1–4,
then each listed device's sources in the `[[devices]]` order
(`Router.schemes()`; a scheme a route names is offered too). **The
filter** (on the pointer line) keeps only the lines that contain every
typed word, matched anywhere — a desk line's glyph, Akai's name and
target; a macro's id, label and subscribers; a session or sink row. It is UI state:
not saved, no undo step, empty at launch, left alone by a preset load;
its × and a click on a desk control clear it. A route's `scale` can only
be a session param; a route may perform a session param, marked
"session" on its row.

**The order the routes run in** (plan 28 N0). `Router.modulate` runs
the table as a graph (`modgraph.py`, ARCHITECTURE §2), each node after
everything it reads: the LFOs step inside it, a `scale`, a macro's depth
or an LFO knob a route moves lands before the route that reads it, so an
LFO on another LFO's depth, a macro scaling a push or a hand on a
modifier's release act **the same frame** — there is no one-frame lag.
A **loop** through no delay modifier (`lfo:0 → lfo.2.rate` and `lfo:1 →
lfo.1.depth`; an LFO pushing its own depth) keeps its last cable in table
order off: a warning line under ROUTING's head names it, `loop: lfo:0 →
lfo.2.rate → lfo:1 → lfo.1.depth → lfo:0 needs a delay — lfo:1 →
lfo.1.depth is off until it has one`; the row stays in the table (its
checkbox still on) and in the file, and the rest runs. Put a `delay`
modifier in the loop and it runs, one frame late.

**Modifiers** (plan 28 N1, `modifiers.py`): value nodes between a source
and a route, saved in the preset beside its routes (never in
`bindings.json`). Each publishes a lane `mod:<n>` that a route sources
like any other.

| Kind | Inputs | Params (default) | Out |
|---|---|---|---|
| `curve` | 1 | `shape` −1…1 (0 straight; + slow to start, − fast), `invert` | value |
| `scale` | 1 | `mul` −4…4 (1), `offset` −1…1 (0), `clamp` (on) | value |
| `smooth` | 1 | `attack` 0…2 s (0.05), `release` 0…4 s (0.35), `spring` (off: a spring at ω = 1/attack) | value |
| `combine` | 2 | `how` add · mul · min · max · cross, `balance` (0.5, the crossfade) | value |
| `threshold` | 1 | `on` 0.6, `off` 0.4, `hold` 0…2 s (0.1): 1 on the rising edge for the hold | trigger (also a gate) |
| `delay` | 1 | — | last frame's input |

Their params `mod.<n>.<p>` are performance params (the `mod` group),
routable and modulatable. A modifier whose input is not live (a hand out
of the box, a device the rig lacks, no input picked) is **dormant**: its
lane reads absent, so a route on it lets go and the base returns.
Removing one leaves the routes on its lane, dormant; ids are one past
the highest (`mod.1`, `mod.2` …). A desk template may carry a
`modifiers` list; a preset that names it gets them, its own overriding
by id.

**The MODIFIERS strip** (`ui_routing.modifiers`; since plan 28 N7 not
drawn on ROUTING — a modifier is added from GRAPH's right-click picker
and edited in GRAPH's side pane, the strip's own block stacked): a
kind combo and **+ modifier**; per modifier `MOD n`, its kind, a combo
per input (the route sources and the other modifiers' lanes), its live
output ("dormant" while not live) and ×, then its params as ordinary
widgets (right-click for Learn); a smooth's block, stacked, ends in its
feel's shape and its feel working live — its input as read, its output
after the feel (`ui_feel.py`, `modifiers.smooth_motion`). Each add, remove, input picked and
param drag is an undo step. "Right hand energy, smoothed, times band 0,
into acid mix": + smooth on `hand R energy`; + combine on `mod 1 smooth`
and `0 sub`, how mul; + route from `mod 2 combine` onto `fx.acid.mix`.
On GRAPH (§6): the picker's smooth and combine, cables into their
inputs (or onto their collapsed stubs, picking the input), the combine's
how in its side pane, a cable from it onto acid's `fx.acid.mix` mod.

## 10. Presets, shows and the bank

A **preset** (`presets/<slug>.json`) is one whole performance moment:
the performance groups' values (`view rot camera pattern dream fx lfo
macro mod`, `params.PERFORMANCE_GROUPS`), the performer routes, the
desk's preset layer, the macros and the module labels — and, when it has
them, a `graph` section (§2: its nodes and, since plan 28, its `wires`),
its `modifiers` (after `routes`: one entry each, `{"id": "mod.1",
"kind": "smooth", "in": ["hand:right.energy"], "attack": 0.05,
"release": 0.6}`, its params at their bases; no `mod.*` id in `values`)
and its `layout` (last: `{"<node id>": [x, y]}` for the GRAPH page's
nodes the preset holds, whole canvas units, sorted, written only for a
node dropped by hand). None of the three is written when empty, so a
preset without them saves byte for byte as before, and none bumps the
schema. The show keeps the rig's nodes' positions in its own `layout`.
Since plan 40 a preset may end with `groups` (after `layout`, one group a
line: `{"id": "group.1", "name": "acid wash", "patch": "acid-wash",
"nodes": ["render:acid.2", "mod.3"], "open": false}`, and a
`kept_by_host` list when a spawn's sheet kept rows for the preset); it is
written only when a group exists, and then the file is
`hyperspace.preset/8` (§6, "Groups and patches").
A build from before plans 28 and 30 ignores `modifiers` and `layout` with no
note and **drops them when it saves**, and opens a `graph` with wires or
placements as the default graph with a note: keep both Macs of a shared
library on the same build (register row 277). **A load replaces all of
it** — every performance param lands from the file or its group default,
every route and preset-layer row is replaced — and never touches a
session param (`tempo hands ghost band master scene audio output overlay
ui desk`): a tapped BPM, the hands' feel and the ghost hands survive any
preset. Anything a file names that it may not (a session id, an unknown
id, a route onto a param that is not modulatable, a desk row on an
invariant control, a route onto a modifier the file does not hold, a
`mod.*` id in `values`, an unreadable `layout` entry) is dropped with a
note and the file is left as it is.

**One tier** (2026-10-28, the owner's: "no factory presets, nothing
hidden, nothing dim, nothing I cannot delete"). Nothing ships with the
app. Every preset in the library is yours — listed, loaded, renamed and
trashed alike — and a fresh library is empty: the app starts on a blank
preset (`new`) in an unsaved show. The twenty-five presets the build
used to ship (TUMBLE, FACES, BIG BLUE WAVE, legacy6, seq-demo…), their
generator and the `party` / `house` shows left the app that day; the
files live on only as the golden frames' corpus (`tests/corpus/`, §16)
and nothing in the app reads them. The eleven band **scenes** are code
data (`hyperspace/scenes/band/`, §13), not presets.

A **show** (`projects/<slug>.hyp.json`; the code says *project*) is the
room the presets play in: the session's values, the module presets of
the session groups (the band layout and scene), the **pads** (the bank,
below), the rig's own wires (the bus cables cut on GRAPH, §2) and a
`startup` preset. A launch opens the show opened last (`last_show`) if
its file is there; otherwise, and on **new**, an unsaved show called
`untitled` with every pad empty, which **save** writes into the library.

**The pads** (the bank: twenty-four preset names, `library.SLOTS`) are
the desk's. The APC40's clip row 1 loads pads 1–8 (F1–F8 too), clip rows
4–5 pads 9–24. ⇧F1–F8 save the live state as that pad's preset
(`PRESET <n>` for an empty one); on the desk, hold **SAVE** and tap a pad,
or hold an empty pad, to save a **new** preset into it (§8). QUANT and
the gamepad's B step to the next **filled** pad; a learned step or knob
on `preset.select` also skips empty ones. An empty pad or a name with no
file loads nothing and says so ("slot 13: an empty slot"). A show file
holds the bank only as far as its last filled pad, never fewer than eight
entries, and **a load never rewrites a show**. A pad change is written to
the show the moment it happens and is not an undo step. Nothing on the
panel assigns a pad: the page shows no pads (below).

**Home** — the Home key or the APC40's OVERDUB loads the show's `startup`
preset, as a load like any other (one undo step, "home → moo"). A show
that names none loads nothing and says so ("home: this show names no
startup preset"). Nothing on the panel sets `startup` since 2026-10-28:
a show file keeps what it says, a new show says nothing.

**The PRESETS page** (`ui_presets.page`), top to bottom: **the preset
strip** — ◀ the loaded preset's name ● ▶ (the name is a readout; the
arrows step the list by name), **new** (a blank preset: default values,
shape → scene → All outputs, named `untitled` and dirty until saved),
**save** (over the loaded preset's file; on `untitled` it asks for a
name) and **as…**; **the list** — every preset by name, case folded,
filling the page (never shorter than three rows, scrolling past the room
it has), the loaded one selected: a click loads, **rename** turns the
row into a name field, **×** sends the file to the trash; **trash (n) ▸**
at the list's foot, only while the trash holds something — every file in
it, newest first, each with **restore**, then **empty trash…**, which
asks "delete N files for good? — click again" for 4 s; **patches ▸**,
folded — every patch, rename and × (a patch is spawned on GRAPH, never
loaded here); **show** — one line saying what a show is ("the desk's
pads, the session, the rig's wires"), then its name ● (red while it
differs from its file), **open ▾** (your shows), **save**, **as…**,
**new**; then the library's warning, error and status lines. Nothing
drops down but **open ▾**, nothing is dim, no row is special.

**The dirty dot** (`ui.dirty_dot`) is a red disc on every strip, on
ROUTING's head and on the rail; while there is something to save the
save chip is solid red. It compares the live state with the loaded
preset or show within undo's float tolerance, so a performer's round-off
lights nothing. Nothing asks before a save.

**× and rename** work on every preset. × copies the file to the trash
first and refuses the delete if it cannot (a full disk never makes a
delete unrecoverable); pads that name it keep the name, and the line says
what still points at it, so a restore makes them work again. **rename**
renames the file, the name inside and every show that names it (each
copied to the trash first; a taken name is refused). Neither is an undo
step: the trash is their net.

**Module presets** (one group each, `hyperspace.preset/1`) replace only
their group; each module's strip is on its own page (band on AUDIO,
patterns on FACES…) with its popup list, save, as… and reset — the
PRESETS page shows none of them. The analyzer's **scenes** are not module
presets since 2026-10-28: they are the eleven files under
`hyperspace/scenes/band/`, read by the scene combo (§13); a band preset
you save is yours, in `band/`, and never stands in for a scene.

## 11. Undo

Cmd+Z or Ctrl+Z undoes; with ⇧, redoes (`undo.py`). The footer says what
it did ("undid Brightness 2.00× → 2.96×", "nothing to undo").

**A step** is one gesture — a slider drag, a desk knob turn, a typed
value, a toggle, a key or pad press that sets something, a mouse orbit,
an edit on ROUTING — or one replacing action: a preset load by any road,
a show load or new show, home, a module preset load or reset, a learn
landing, an Unbind, a ×, Replace in the Replace / Keep prompt. Once a
frame `Undo.tick` compares a fingerprint of what the user sets; a change
opens a step that closes after **0.4 s of quiet** (`undo.SETTLE_S`), so a
slider moved within 0.4 s of a load joins the load's step. The stack
keeps 100 steps; a launch starts empty.

**Watched:** the base of every persisted param that is not an alias, a
trigger or in the `tempo` group — performance and session alike, the
camera included — and the loaded preset's routes, preset layer and
macros.

**Not a step:** a performer (a hand, a band, an LFO writes an offset,
never the base); the rotation phases; the tempo (a tap is never undone);
triggers; selections and panel state (`band.select`, `Panel.fx_selected`,
`preset.select`, `desk.shift`, `ui.*`); the transport; the rig's output
settings (screen, fullscreen, overlay, the master dim, every
`output.N.*` switch); `bindings.json`'s session rows; a band added,
removed or moved (a step's band strips land only on the layout they were
taken on); a save, a delete, a pad change (their net is the trash and
the show file).

**A restore** puts back only what differs, through `Param.set` and the
table's own calls: undoing one slider sets one param — no load runs, the
desk layer stays, faders keep their catch, LFOs keep their phase. Undoing
a load also puts back what the library calls loaded, so the PRESETS page
names the earlier preset and **save** writes that one. A restore writes
no file. The band strips' 8-second "Reset all → Undo" is separate.

## 12. Hands

Ultraleap hands (`hyperspace/hands/`), off until the hands entry says
`enabled = true` (`[[devices]] kind = "hands"`, or the old `[hands]`
table). Each hand gives its palm's pose — six axes by default, from the
features in `hands/core.py` (`FEATURES`: x y z in mm, roll pitch yaw in
degrees, grab, pinch, grab angle, pinch distance, four thumb-to-finger
ratios) — plus eight pinch switches. Each axis is calibrated, smoothed,
shaped (dead zone, curve), enveloped (attack, decay), sprung back to a
rest value when the hand leaves and glided back onto it when it returns
(Catch). Inside the app the axes are `hand:<side>.<name>` sources for
routes; outside they go to a MIDI port for a DAW (`[hands] out`).
`uv run python tools/hands_probe.py` shows every axis live without the
app (`--calibrate 20` runs the sweep, `--solo right.pitch` sends one axis
to the DAW).

**On the device registry** (plan 27). The hands are a device:
`hands/device.py`'s `HandsDevice` owns the `HandsIO` (it and
`hands/panel.py` are the only files of the package that know the host;
`core.py`, `signal.py`, `tape.py` import nothing from it). It makes the
instrument's one call, `HandsIO.poll(dt, learn, router)`, in the
registry's feed slot — after the audio step, before the LFOs — which
reads the tracker, feeds `hand` and `hands`, completes a hand Learn and
makes the frame's DAW messages. Its SYSTEM line counts the instrument's
lanes as sources (42 with six axes a hand) and reads `connected` while
the tracker gives frames, `lost` while it connects, and the tracker's
own words otherwise (`error: no camera`, `error: service lost`) — the
Leap SDK's thread reconnects by itself. A hands entry whose `open`
fails (a missing tape) is retried on the registry's schedule. **The DAW
out is a sink**: `HandsIO` opens no MIDI port; its messages wait in
`HandsIO.outbox` and the `hands-daw` device (`kind = "midi-out"`,
derived from `out` at load, §5) carries them after `reg.apply`
(`HandsIO.carry`), looks for a lost port again on the MIDI schedule, and
on its return sends `HandsIO.resync()` first, so the DAW catches up with
where the hands are. Its line: `hands-daw · midi-out · connected · 0
sources · 0 sinks · Hyperspace Hands · leap's DAW out · cc 102 = 64
ch16`.

**The HANDS page** (`hands/panel.py`): the setup strip (a setup is every
per-axis and global hand setting, a module preset of the `hands` group);
the status (tracker, each hand — ● in the box, ◌ tracked but outside it,
○ not seen — the DAW port, the last MIDI sent); the pinch switches with
their live gaps; the box from above with a height gauge; one row per
axis (click to edit); the selected axis's transfer plot and settings
(invert, centred, dead zone, curve, attack, decay, on exit, rest,
return, bounce, MIDI out, mirror, solo); **feel & calibration** —
steadiness, response, catch, MIDI rate, hysteresis, pinch thresholds,
**Learn depth**, **calibrate 20 s**, **reset ranges**; and, under the
box, the ghost hands: the **Ghost hands** tick; while it is on,
**Opacity** and a **more ▸** chip on its line and **Style** and
**Guide** on the next. **more ▸** opens Mirror, Tethers (with a guide
on) and the ghost's notes — an error, or the unmeasured-mode note; while
there is one the chip reads **! more ▸** in the warning colour and its
hover says it. A narrower panel wraps a group onto the next line.
Beside the axis rows, a column shows the dance sources and the grab
(below) live, hollow while one reads nothing, its address and value on
hover.

**The dance sources and the grab** (plan 24, `hands/core.py`). Beside
the twelve axes, each hand publishes `hand:<side>.curl.thumb` …
`.curl.pinky` (how bent each finger is: the summed bend of its joints),
`.spread` (the index–pinky fan in the palm's plane; a fist reads 0),
`.energy` (the mean speed of the palm and the five tips, quick up and
slow down) and `.flick` (a spike to the hit's strength when the fastest
tip passes 1500 mm/s, decaying over about 0.15 s; a lane until a trigger
kind exists), and `hand:<side>.grab`, 1 while the hand is a fist (the
mean curl of the four fingers through a Schmitt gate: closes past 0.65,
opens under 0.45, 0.05 s debounce). A second scheme, `hands:`, has
`hands:gap` (the palms' distance) and `hands:twist` (the right roll less
the left, 0.5 for mirror-image hands), live only with both hands in.
Curl, spread and the grab need the skeleton; energy and flick fall back
to the palm. Every range and time constant is a constant in the `DANCE`
block of `hands/core.py`, tuned on synthetic hands. The `hand` vector is
the axes, two presence lanes, the eight pinches, then the sixteen dance
lanes, then the two grabs (40 with six axes a hand), so no older lane
index moves; `Layout` holds every index and count. The published gates
are the pinches then the two grabs. The new sources are picked on
ROUTING (source or gate combo); a hand Learn still offers only the
axes, none of them goes to the DAW port, and none has settings of its
own.

**The interaction box.** A hand counts only while its palm is inside a
box in the camera's millimetres (x across, y up, z toward the
performer), one box for both hands. A hand outside it is **absent to
everything**: its routes let go and the settings return that frame, its
switches drop, its presence note goes off, its ghost fades. A hand that
is in stays in until its palm is 15 mm past a face. The **calibrate 20 s**
sweep sets the box and every axis's range: the box is where the palms
went (2nd–98th percentile) plus 40 mm; a direction swept less than 12 cm
is left open and the note says so. The box is off during the sweep, so
calibrate with nobody else in view. **reset ranges** opens the box and
restores the default ranges. There is no other control; `hands.json`
can be edited by hand: `"box": {"x": [lo, hi], "y": [lo, hi], "z":
null}`, `null` meaning open; a pair that is not two finite numbers with
lo < hi opens that coordinate with a note.

**Ghost hands** (`ghost.py`): both tracked hands drawn over the render,
following the skeleton raw (no smoothing), a display only.

| Param | Default | Notes |
|---|---|---|
| `ghost.on` | off | modulatable |
| `ghost.alpha` | 0.6 | modulatable |
| `ghost.mirror` | off | flip left for right (a mirror or a Pepper's Ghost glass) |
| `ghost.guide` | OFF | OFF · BESIDE · ON HAND: per hand, a ball per axis, an arc per rotation, the pinch beads and a grab ring; what a route reads is bright, the rest grey |
| `ghost.tethers` | off | with a guide: a line from each routed mark to a label naming the params it drives |
| `ghost.style` | HANDS | HANDS (capsules), JOINTS (beads), PALMS (an orb that swells as the hand opens, a ring, a spoke), CAGE (a wire octahedron), MARIONETTE (fingertips on strings from a bar) |

All six are in the `ghost` group, a session group: saved with the show,
never moved by a preset. `mirror`, `guide`, `tethers` and `style` are
settings — a hand learn onto one is refused in words, and a preset's
route onto one is dropped at load. The ghost hands are drawn in the
shape's camera (plan 26, §2): the eye, and the calibration in
`hands.json` — `"units": {"mm": null, "origin": null, "tilt": 32.0}`,
"from the box" by default, which fits the padded box (or, with no box,
the calibrated ranges) into a 16:9 picture of the eye, seen from 32°
above; an `mm` or `origin` written there wins. `hands.json` is
`hyperspace.hands/3`; an older file is kept as `hands.json.bak-v2` before
the first rewrite. A hand leaving fades out over 0.3 s and one coming
back fades in over 0.1 s. Desktop is
the only tracking mode whose axes have been measured; with `screentop`
or `hmd` and the ghost on, the HANDS page says so (in **! more ▸**). Where the hands show
on each output, and whether the effects bend them, is §14.

**Without a camera.** `tools/hands_tape.py record <file>` keeps a few
seconds of real frames as a tape; `[hands] tape = "<path>"` (with
`enabled = true`) plays one in the app instead of the camera; `shots`,
`synth`, `styles` and `info` render, make or describe tapes. A missing
or malformed tape is a note on the SYSTEM and HANDS pages.

## 13. Audio

**Sources** (`audio.py`). Nothing captures at launch. **A capture
device**: M or *Listen to mic*; mono, 48 kHz. The device combo lists
every input; a loopback driver (BlackHole, Soundflower, anything named
"loopback") is recognised by name, pre-selected, and labelled `System ·
…` — that is how the Mac's own output is captured (SETUP). **rescan**
reads the device list again. **A file** (*Load track*; wav, mp3, flac,
ogg): played through an output stream at the track's rate, the analyser
built at that rate. Pause keeps the stream running on silence, so the
bands decay on their own time; K plays / pauses, 0 restarts. Stopping a
capture lets every lane go at once.

**The chain** (`analyzer.Analyzer`; `bands.py` holds the constants and
shapers): N bands (1–16), each a centre frequency, a Q and a weighting
curve (rect, triangular, gaussian, butterworth). Per band:

```
FFT bins → weighted power under the band's curve → dB → u (1.0 nominal)
  ├─ LEVEL: attack / decay envelope → peak / valley window + gate
  │         → upward expansion about the band's running mean   (contrast)
  └─ TRANSIENT: fast env − slow env, peak-normalised            (transient)
  → blend → harmonic coupling → soft ceiling          ← the INPUT meter (white)
  → pre-drive → soft ceiling → transfer function → post-drive → soft ceiling
                                                      ← the OUTPUT meter (red)
  → lane i
```

The chain ends at the lanes; a lane reaches a rotation plane or anything
else only as a route. Nothing hard-clamps: three soft ceilings bend from
1.25 towards 2.6. The FFT is 4096 points, Blackman window, smoothing
0.15 (the band envelopes do the smoothing). Harmonic coupling boosts a
band by its coherence with the next band up — a proxy, not true
harmonic detection. `master.dyn` scales the dynamics recovery (valley
tracker, expansion, transient path), which brings back motion a limiter
took from a brickwalled master; it runs to 4×. A meter column pinned
near the ceiling for half a second lights a blinking annunciator.

**Input trim** (`band.{i}.trim`, `master.trim`; off, then −60 to +12 dB)
is applied before the trackers and again after them, because the
window normaliser removes any static gain in front of it. **AUTO /
MANUAL** (`band.{i}.norm`, the chip on the strip): AUTO, the default, is
the reference chain, where trim is not monotonic through the useful
range; MANUAL bypasses the window, expansion and warm-up for that band,
so its level is the envelope and the trim a plain gain — at the cost of
the dynamics recovery. `uv run python tools/trim_sweep.py --manual`
prints a sweep.

**Thirteen transfer functions**: LIN SQRT SQ CUBE CURV GATE INV HOLD STAC
CHOP TREM S&H SLEW (CHOP, TREM and S&H run at fixed rates, not the
tempo clock).

**Eleven scenes**: Balanced, Kick & Sizzle, Glacial Drift, Strobe Cage,
Bass Engine, Air & Lace, Inverse World, Percussive, Tremolo Web,
Harmonic Bloom, Slow Bass / Fast Air. A scene is a band document shipped
with the code (`hyperspace/scenes/band/*.json`, `control.SCENES_DIR`),
never a library preset since 2026-10-28 — a band preset you save is yours
alone. The scene combo, the APC40's scene pads and
**Reset** re-tune the bands you have from the scene; the band preset
strip loads a file whole, layout included. **Reset all** relabels to
**Undo** for 8 s.

**Faders** are integer positions on tapers that map exactly both ways
(`tapers.py`): logarithmic for gains and time constants, linear where
the quantity is already even; the tag is in each knob's tooltip.

**The tempo clock** (LFO page; B or TAP TEMPO taps, NUDGE shifts the
downbeat) drives the four LFOs. It syncs to nothing outside the app.

**The bridge** (`[[devices]] kind = "bridge"`, or the old `[bridge]`
table; `bridge.py`) sends the lanes (or any param) out as 14-bit MIDI —
pitch bend per channel, or CC pairs — rate-limited and only on change,
and turns the same messages coming in on `in` into `ext:<i>` sources for
routes, published with labels ("ext 0" …) and rests (0). Use two buses:
IAC echoes. It is one device with two halves: in the feed slot it
receives and publishes `ext`; after `reg.apply` it sends its **sink
rows** (`bridge.Sender`: quantise, change-gate, rate-limit, encode), so
what goes out is this frame's effective value. Its SYSTEM line: `bridge ·
bridge · connected · 16 sources · 2 sinks · IAC Driver Bus 1 · pitch, 16
lanes · 41 sent`.

**Sink rows** (plan 27). What a sink sends is rows in `bindings.json`
(the session's: sinks are rig), `{"source": "param:view.bright",
"target": "bridge:6", "op": "send"}` — a source `param:<id>` (the
param's effective norm), `lane:<i>` (the lane as a route reads it) or
`lane:*` (every lane from the row's channel on), a target `<role>:<k>`
(the sink's lane k: with `encoding = "pitch"` the pitch bend on channel
`channel + k + 1`, with `cc14` the CC pair `cc + k` / `cc + k + 32`). An
explicit row wins its channel over a `lane:*`; a trigger or an unknown id
sends 0. Make one with the param menu's **Learn sink ▸**, or on ROUTING →
sinks; a sink row is never a performer, never in a preset, never asks
Replace / Keep, and Unbind never removes it. **The old `send` list
becomes rows once**: the first launch an entry with a `send` list (the
bridge's default `["lane:*"]` included) is on and its role has no sink
row, the list is written into `bindings.json` (slot k → `<role>:k`;
`lane:*` takes the default layout's six channels before the next entry)
with one note — "bindings: [bridge] send is now sink rows in
bindings.json (lane:* → bridge:0, param:view.bright → bridge:6) — the
rows say from here on; edit them on ROUTING (sinks)" — and the file's
top-level `"sinks_seeded": ["bridge"]` marks it done, so rows you delete
never come back and `send` is not read again. To translate an edited
`send`, remove the role from `"sinks_seeded"`. A `midi-out` entry is a
sink alone: its own port (§12) and its own sink rows on its role.

## 14. Outputs

**One output** by default: the render window, from `[output] monitor` /
`fullscreen`. **Several** from `[[output.screens]]` (§5), up to four
(`outputs.MAX_OUTPUTS`), numbered by their place in the list whether or
not they opened. Output 1 is made as the single render window always is
(4× MSAA; transparent only with `[output] overlay = true`), sets the
frame's size and paces the loop (its swap waits for its screen; later
outputs' swaps do not). Later outputs are opaque, never overlay, and
their screen and fullscreen come only from the config (the OUTPUT page's
Screen and Fullscreen rows move output 1). A later output whose
`monitor` names no connected screen **is not opened**, with a note
("output 2 (projector): monitor = 2, but 2 screens are connected (0–1) —
not opened"); output 1 always opens. A later output of another shape
shows the whole frame letterboxed, the hands registered on it. Each
later output is drawn from the shared textures in its own context
(`outputs.Presenter`); a failing present marks that output and the rest
go on.

**Per-output switches** (`overlay.register_switches`): `output.N.scene`,
`output.N.hands`, `output.N.through` ("Hands through effects") and, with
two or more outputs or a lone entry whose `dim` is under 1,
`output.N.dim` (multiplied by the master dim). They are **rig settings**:
set from the config entry at every launch and Cmd+R (defaults scene on,
hands on, through off, dim 1), never saved, never in a preset, show or
undo step; a switch flipped mid-set lasts until the restart. They can be
learned onto a desk button.

| Scene | Hands | Through | The output shows |
|---|---|---|---|
| on | on | off | the scene with its effects, the hands clean on top (default) |
| on | on | on | the scene and the hands, both through the effects |
| on | off | — | the scene with its effects |
| off | on | off | the hands alone on the ground |
| off | on | on | the hands alone, through the effects |
| off | off | — | black |

"Hands shown" also needs `ghost.on` and a hand drawn this frame; with no
effect on, "through" changes nothing. The echoes and the dream do not
hold the hands unless a preset's graph wires the history to the scene
with the hands (§2). With the guide on, its gauges and labels are drawn over
the hands after the effects, so they are never bent. The OUTPUT page
says in words what each output shows ("scene + hands through the
effects · 64%", "black — the scene is off and no hand shows").

**The master dim** (`output.dim`, the crossfader, the OUTPUT page's first
row) multiplies the finished frame — scene, look-back, effects and
hands — on every output: 0 black, 1 full. It is a rig setting: not
saved, not modulatable, not in any preset, show or undo step, so every
launch starts at full. On an opaque ground the ground stays opaque black;
in overlay the render fades off the desktop.

**Overlay** is possible only with `[output] overlay = true`; without it
the render window is always opaque and T, MASTER select and the panel's
toggle do nothing (the OUTPUT page greys it and says why). With it, T
puts output 1 over the desktop: no frame, above everything, clearing to
see-through, clicks passing through (G or PAN takes them back);
`output.bg` and `output.alpha` set the ground and opacity. The
`overlay.*` ids are aliases of `output.*`.

**Where windows open** (`placement.py`): a configured `monitor` /
`control_monitor` index first, then `windows.json` (the last quit's
rects — always the plain window's, never a fullscreen cover), else the
render window top-left of the primary screen and the controls flush
right; two later outputs with no memory open 40 px apart. A remembered
rect is used only when enough of it is on a connected screen; otherwise
the default spot, with a note. `windows.json` is written on quit and
Cmd+R only.

## 15. Hot reload and the watchdog

**Hot reload** (`hotreload.py`). Save a module on `hotreload.MODULES`
while the app runs and live objects pick up the new code in place; a
broken save keeps the last good version and shows the error on the
SYSTEM page. `app.py`, `hotreload.py`, `offline.py` and `watchdog.py`
are cold: changing them needs Cmd+R. A changed `__init__` does not
re-run on live objects. Shaders (`patterns.glsl`, `_common.glsl`,
`shaders/fx/`) and the library's JSON files reload too. Plan 28's
modules are on the list in dependency order: `modifiers` after
`motion`, `modgraph` before `routing`, `graphview` after `osc`, `ui_graph`
before `ui`; `ui_feel`, the live feel plots, before `ui_routing`. A reload of `ui_graph` keeps the GRAPH page's editor
context (it is held on the panel, not in the module), so the page goes
on drawing with its zoom and selection.

**The watchdog** (`watchdog.py`) appends to `<home>/stall.log` a `===
<kind>` header — the time, the loaded preset, what happened — and every
thread's stack, for:

- `stall` — no frame completed for 2 s;
- `render error` — the render draw raised (the panel lives on; the
  render window holds its last frame), once per distinct error;
- `render stall` — no render output presented for 2 s while the loop
  runs (minimised, occluded, another Space…), with the window's state;
- `warning` — one output not presenting while another does, an output's
  present that raised, or a preset asking for the dream with no worker;
- `stranded target` — a frame that began on an offscreen framebuffer;
- `non-finite` — a param that dropped a NaN or inf.

`kill -USR1 <pid>` dumps every thread on demand, and a stall that holds
the GIL is caught by faulthandler's timer. The SYSTEM page shows the
log's line once it has entries. Nothing in the watchdog can stop the
show: a log that will not open is kept as an error and the loop goes on.

## 16. Testing

```bash
uv run pytest -q          # the fast tier, in parallel (~17 s)
uv run pytest --all -q    # every tier: golden, slow, live (~55 s)
uv run ruff check .
```

- Tiers: `golden`, `slow` and `live` are markers `tests/conftest.py`
  applies by name (see "Running the automated tests" in
  `TESTING-GUIDE.md`); the default run is `-n auto` without them. Run
  `--all` before a merge and after touching rendering or presets.

- Every test runs against its own temporary home: `tests/conftest.py`
  sets `HYPERSPACE_HOME` to the test's `tmp_path` in `os.environ`
  itself, so no test can read or write `~/Hyperspace`.
- No test reaches the machine's MIDI: the autouse fixture
  `_no_real_midi` makes the port lists empty and every open raise,
  unless a test patches `mido` itself.
- One test is skipped:
  `tests/test_hands_tape.py::test_every_recorded_tape_replays_through_the_ghost`,
  because no real hand tape has been recorded into
  `tests/fixtures/hands/` (`tools/hands_tape.py record` on the rig).
- The parity net: `tests/golden/` traces recorded from the retired HTML
  app (`tools/record_golden.py`, which needs Playwright's Chromium) hold
  geometry exact and the audio chain's behaviour; `tests/legacy_chain.py`
  is a frozen copy of the reference chain that the analyzer's "Legacy 6"
  layout must match bit for bit. Re-freeze it only when the maths
  changes on purpose.
- GL and imgui run headless: every shape renders offscreen, every panel
  page draws and fits, every factory effect compiles. Extra windows and
  screens are fake GLFW window systems (`tests/test_app_boundary.py`).
  `HYPERSPACE_FRAMES=n uv run hyperspace` is a windowed smoke run.
- The patterns: `tests/test_patterns.py` holds the shader to
  `patterns.py`'s table and checks every input moves every mode;
  `test_the_face_shaders_pass_the_reference_compiler` runs
  `glslangValidator` and skips where it is missing. Fit tests measure in
  this machine's font metrics: in the cloud container test_fx's own two
  fit tests miss by 18 px, so a pass or a fail there says nothing about
  the Mac.
- The golden frames: `tests/test_golden_frames.py` compares 596
  full-resolution frames — every corpus preset in every output state,
  hands absent and present, the other wirings, the fixture presets and a
  recorded cloud — to the byte, on `GL_RENDERER` "Apple M3 Max" only
  (anywhere else it skips with a note). `tools/golden_frames.py` diffs
  them and writes a contact sheet of what moved; `--record` re-records
  (`--only` a few presets). How, when and why to re-record: §2, "Golden
  frames". The render graph's own tests: `tests/test_graph.py`,
  `tests/test_camera.py`, `tests/test_hands_node.py`,
  `tests/test_graph_json.py`, `tests/test_cloud_node.py`,
  `tests/test_stroke_space.py`.
- The modulation graph and the node editor (plan 28), all headless:
  `tests/test_modgraph.py` (the sort, the loops, the edges the design
  names, a param applied once a frame), `tests/test_modifiers.py` (each
  kind on a scripted input, the preset key, templates, undo, the
  MODIFIERS strip), `tests/test_graphview.py` (the model with no imgui,
  and the page drawn once on the real `imgui_node_editor` under the test
  imgui harness), `tests/test_graph_edit.py` (every edit through the
  page's functions — no test can drag a mouse on the widget),
  `tests/test_graph_wires.py` (the wire list, outputs as nodes, the
  canvas's render edits) and `tests/test_graphview_devices.py` (the
  APC40's two nodes, templates, placeholders). **The equivalence test**,
  `tests/test_routing.py::test_every_factory_preset_lands_the_same_values_one_frame_earlier`,
  plays every corpus preset with a synthetic hand tape through the base
  build's `modulate` (kept verbatim as `_lagged_modulate`) and through
  today's, and asserts every modulatable param identical or exactly as
  many frames earlier as the base was late.
- A test-order dependence from before plan 28:
  `tests/test_app_boundary.py::test_a_broken_adapter_is_a_note_not_a_crash`
  fails when `tests/test_dream.py` runs before it (its
  `monkeypatch.setitem(sys.modules, "hyperspace.dream", …)` is bypassed
  once `hyperspace.dream` is an attribute of the package). The full
  suite's alphabetical order hides it; it reproduces on the base build.
- The shapes: `tests/test_shapes4d.py` holds every shape to its
  recorded digest (`tests/golden/shape_digests.json`, floats rounded to
  1e-9) and every 4D shape to `VOLUME_FLOOR` through each W plane;
  `tools/turntable.py` draws the same sweeps (§1).
- Fixtures: `tests/fixtures/` holds the test-only presets, templates
  and palettes a test copies into a scratch library (plan 24's
  `desk-trust/`, `desk-faders/`, `desk-templates/`, `dance-sources/`,
  `grab-follow/` and `palettes/`, plan 27's `osc/` and `clouds/`, plan
  26's `presets/hands-lines.json` and `camera/`, plan 30's
  `presets/palette-hands.json`, `palette-glass.json`, `acid-scene.json`,
  plan 28's `presets/hands-glass-only.json`, `wired-outputs.json` and
  `modifiers/`, and `macro-candidates/`). The folder
  is gitignored at the repo root, so a new fixture is added with
  `git add -f`. No test proves a mechanism by editing a corpus preset.
- The desk coverage report: `tests/test_desk_coverage.py` regenerates
  `docs/plans/assets/24-party-fixes/desk-coverage.md` with
  `tools/desk_coverage.py` and fails when the committed file differs by
  a byte; after a change to a desk, a preset or `learn.cannot_show`, run
  `uv run python tools/desk_coverage.py` and commit the report
  (`--check` tells you whether it is stale).
- Import boundaries are tests: the core never imports `midi`, `bridge`
  or `dream`; importing `app` imports none of `midi`, `bridge`, `dream`,
  `osc`, `leap`, `torch`, `pythonosc` (`devices.py` imports each inside
  its device's `open`); `hands/core.py`, `hands/signal.py`, `lfo.py`,
  `tempo.py`, and `undo.py` import nothing from the package; only
  `osc.py` and `devices.kinds()` name the OSC device; `library.py` never
  imports `config`.
- The devices: `tests/test_devices.py` (the protocol and the registry
  over fakes), `tests/test_device_inputs.py` (two desks, the pad and the
  hands on the registry, over a fake MIDI bus), `tests/test_sinks.py`,
  `tests/test_osc.py` (`pythonosc`'s client to 127.0.0.1 on a port the
  device bound itself) and `tests/test_clouds.py`.
  `tests/test_app_boundary.py`'s `ORDER` pins the three device slots.

What only a person at the machine can check is
[`TESTING-GUIDE.md`](TESTING-GUIDE.md) and the numbered list in
[`plans/11-hand-checks.md`](plans/11-hand-checks.md).

## 17. Known limits

- **A screen plugged in after launch is not used** until a relaunch
  (Cmd+R): a later output that did not open stays closed, and output 1's
  configured screen stays −1 for the run.
- **Frame pacing with two screens has never been observed by a person.**
  Output 1 waits for its screen and later outputs do not; whether that
  paces the loop on two real screens, and whether a non-waiting
  fullscreen output tears, is unknown.
- **With no desk connected the app keeps looking** — every 2 s five
  times, then every 10 s. Each look creates a CoreMIDI client; `enabled
  = false` on the desk's entry (or `[midi] enabled = false`) stops it.
- **At most one hands node makes the layer.** Since plan 28 a preset's
  `graph` section can wire which output gets which hands node and which
  effects it alone takes (§2, the wire list); an output no wire names
  keeps the session's switches.
- **No mouse drag on the GRAPH page has been tested**: the tests drive
  its functions and draw the real widget headless, never a real drag
  (plan 28's hand checks 247–258).
- **A build from before plans 28 and 30 loses this build's `modifiers` and
  `layout` on a save** and opens a wired or placed `graph` as the
  default graph: both Macs sharing a library must run the same build.
- **Media (plan 32)**: two Macs sharing a library must both run the build
  that writes `hyperspace.preset/4`; Resolume and TouchDesigner have never
  sent us or received a frame, `extra_ips` is unverified, the phone's own
  page is V2, and output 1 cannot be publish-only (see "Media" in §4 and
  the plan's "Known rough edges").
- **The golden frames prove pixels only on "Apple M3 Max"**; on any
  other Mac the test skips.
- **On a 3D shape, the W planes' readouts keep counting**: `rot.phase.*`
  and ROUTING show the W planes turning though the shape does not; only
  the VIEW page's dimmed W keys say they do nothing.
- **The FACES page's fit and `patterns.glsl` on Apple's GL are
  unverified**: both were checked only in a container with Mesa and
  other font metrics (hand checks 120, 121).
- The amber "filled" pad light and the save-as blink use Akai's
  documented velocities and have not been confirmed on an APC40 mk1.
- Open findings in [`AUDIT-2026-09.md`](AUDIT-2026-09.md): R13, R14,
  R15, U9, U10, P6, V8.
