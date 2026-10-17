# Plan 28 — the catalog, scenes and the 3D switch (art-direction spike)

**Status: spike, built as a proof of concept.** Three directions explored
with as little new surface as possible: no new page, one new toggle, and
everything else reached through the existing **Shape** menu.

1. **Several shapes in one frame.** A *scene* is a shape whose geometry is
   other shapes, sharing a centre: a sphere round a hypercube round a
   star. Each layer keeps its own scale, weights, colour and spin.
2. **The third dimension.** A catalog of closed 3D solids, and a **3D**
   switch that takes the fourth dimension out of any shape.
3. **Mathematical toys.** Geometric diagrams as shapes: the Hopf
   fibration, an armillary sphere, a geodesic sphere, the Sierpinski
   tetrahedron, a Lissajous knot, a loxodrome, Kepler's nested solids.

Pictures and the demo video: [`assets/28-catalog/`](assets/28-catalog/)
(`demo.mp4`, `catalog.png`, `scene-*.png`, `three-d-*.png`), redrawn by
`tools/catalog_demo.py`; the GIFs are cuts of `demo.mp4` (ffmpeg), and
`view-page.png` is the VIEW page from a hidden real window.

## What was built

**32 shapes, appended** after the Klein bottle (index is identity), each
with a `Shape.family`. The V/E table is ENGINEERING §1.

| Family | Shapes |
|---|---|
| Platonic | tetrahedron, cube, octahedron, dodecahedron, icosahedron |
| Archimedean | cuboctahedron, truncated octahedron, rhombicuboctahedron, snub cube, icosidodecahedron, truncated icosahedron |
| Catalan | rhombic dodecahedron, rhombic triacontahedron |
| Star | small and great stellated dodecahedron (Kepler–Poinsot), Moravian star, starburst |
| Compound | stella octangula, five tetrahedra, five cubes, cube + octahedron, dodecahedron + icosahedron |
| Toy | Hopf fibration (4D), armillary sphere, geodesic sphere, Sierpinski tetrahedron, Lissajous knot, loxodrome, orbit |
| Scene | Celestial tesseract (4D), Celestial cube, Mysterium Cosmographicum |

- **The solids are `mask`**: rigid 3D bodies whose W planes turn them in
  3D planes, as the Heart already did. Convex solids get their faces from
  the polytope extraction unchanged; stars and compounds bring their own.
- **A star is drawn as what is seen.** A Kepler–Poinsot star's faces are
  {5/2} pentagrams that cross each other; what shows is each pentagram's
  five tips (`geometry._pentagram_tips`), the inner pentagon buried. So the
  face pipeline keeps getting simple triangles, and V − E + F = 2.
- **A curve draws no points** (`geom()["curve"]`): a toy drawn as a curve
  has samples, not corners, and red dots on every sample buried it.
- **Scenes** (`geometry.Layer`, `Shape.layers`, `geometry.shape_view`).
  The renderer projects through `shape_view`: one shape is the old path
  to the bit (`tests/test_catalog.py::test_a_shape_that_is_not_a_scene_is_drawn_as_before`);
  a scene projects each layer at the view's angles, masked as its shape
  is, times its spin. A scene's edges carry their layer's colour, width,
  weight and line density; its points and faces their layer's weight. The
  line and point buffers gained a colour per vertex (white and red, as
  before, for every shape that is not a tinted layer).
- **The 3D switch**: `view.three_d`, "3D" on the VIEW page, beside Faces.
  `geometry.w_masked(i, flat)` / `view_angles(i, ang, flat)`: every shape
  masked. A 4D shape holds the shadow it casts at rest and turns it
  rigidly.

### The scenes

- **Celestial tesseract** (4D): the Hopf fibration in ice blue (the
  3-sphere the tesseract is inscribed in, its fibres turning at 0.4×),
  the tesseract with faces, and a gold small stellated dodecahedron at
  0.62 counter-turning (−0.7×) in 3D. Its twelve points reach past the
  tesseract's inner cube (`::test_the_star_pokes_through_the_tesseract`)
  and slide through its cells as it tumbles.
- **Celestial cube** (3D): the armillary sphere, a cube with faces, and a
  gold great stellated dodecahedron at 0.82 whose twelve off-axis points
  break out through the cube's faces.
- **Mysterium Cosmographicum**: Kepler's 1596 model — the five Platonic
  solids nested between six planetary spheres, each radius set by the
  solid's insphere over its circumsphere; the orbits are tinted per
  planet and the inner shells turn faster. Mercury is 0.07 of Saturn, so
  it wants the zoom (the demo flies in to 6.5×).

## What it does not do (yet)

- **No scene editor.** Scenes are code (`geometry.SHAPES`); a layer list in
  a preset would be the obvious next step if the direction holds.
- **Faces do not occlude lines.** The faces stay translucent fills under
  the whole wireframe, so a star's points "shine through" a cube's faces
  by being drawn over them, not by passing through a surface. Interleaving
  faces and lines by depth would sell it harder.
- **The scene's depth cue mixes kinds.** A 4D layer cues on w, a masked
  layer on its depth to the 3D camera; the painter's sort runs over both.
- **The Shape menu is long** (58 entries, no grouping). `Shape.family` is
  there to group it by if the catalog stays.
- **Zooming thickens the lines.** Line width scales with the camera's zoom,
  as it always has, so Kepler's inner shells at 6.5× draw chunky. A
  scene may want its widths in world units.
- **Not judged at the machine.** Brightness and widths were tuned on
  offscreen software-GL renders; the look on the projector is unchecked.

## Checks

`tests/test_catalog.py` — textbook V/E/F for every solid, regularity of
the Platonic solids, every star closed like a sphere, compounds sharing
corners, dual compounds crossing at edge midpoints, the Hopf fibres great
circles on S³, a scene's rows its layers', each layer at its own angles,
and the 3D switch. The shape digests gained the new rows only
(`tests/golden/shape_digests.json`); `test_shapes3d` covers the trig
family as before; `test_shapes4d`'s gates take the masked catalog in
(the orbit, a single ring, is flat by what it is and exempt from the
volume floor).
