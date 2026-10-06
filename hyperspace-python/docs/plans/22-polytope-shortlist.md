# Plan 22 A5 — which 4-polytopes are cheap to add

This is an assessment only. Nothing here is in `SHAPES`, and the owner
picks what gets built in a later plan. It ranks the second-tier
4-polytopes by what it would cost to add each one to
`hyperspace/geometry.py` as it stands after A1 (`44d8cdc`), and says
which of them break the face pipeline's assumption that every face is a
simple, planar polygon.

**How it was checked.** I wrote a throwaway script, which is not
committed. It generated every candidate by a Wythoff construction
(reflecting a seed point in the root system of A4, B4, F4 or H4). For
each one it ran the real `edges_by_min_dist` rule, `_planar_cycles`,
`_is_boundary_face`, `_tri_cycle` and `volume_ratio` (72 steps of each
of XW, YW and ZW, from rest and from `GENERIC_POSE`, as
`test_every_4d_shape_clears_the_volume_floor` does). It checked every
count against a face lattice taken from a convex hull (scipy, in a
throwaway environment; scipy is not a dependency). Where a table says
**verified**, V, E, F and C came out of that run and match the
reference values. Where my remembered values were wrong, the measured
ones are given. Every `expand` recipe below was also checked against
its Wythoff set: same V, and the same multiset of pairwise distances
(V and E only for the omnitruncated 24-cell). The timings are from this container and include
`_planar_cycles` plus `_is_boundary_face`.

**Picture.** [`assets/22-polytope-shortlist/candidates.png`](assets/22-polytope-shortlist/candidates.png)
shows 22 candidates and 4 existing shapes for reference. The real
renderer drew them offscreen at `GENERIC_POSE` with faces on, after the
script appended the candidates to `SHAPES` in its own process only.

## What the machinery takes, in practice

- **Vertices.** `expand(base, "all"|"even")` covers every form in the
  tesseract/16-cell (B4) family with one call, and every 24-cell (F4)
  form with one to three calls (tables below). The 5-cell family does
  not fit `expand`, because its coordinates are permutations of a
  5-tuple. A 6-line helper covers all of it: `Σ c[k]·simplex5()[σ(k)]`
  over every permutation σ, deduplicated by `kkey`. I checked this for
  all seven forms; it returned the right V and E every time. The 120/600
  (H4) forms need 6 to 17 `expand` classes each, which is not
  practical by hand. A ~30-line generic `wythoff(roots, rings)` helper
  would be needed for those.
- **Edges.** `auto()` gave exactly the hull's edges for **every uniform
  polytope tested**: all of A4, B4 and F4, every H4 form, the snub
  24-cell and the grand antiprism. All their edges have one length, and
  no non-edge pair is that short. It fails on the Catalan duals (two to
  six edge lengths) and on the duoantiprisms.
- **Faces.** `_planar_cycles` + `_is_boundary_face` found exactly the
  hull's F for every convex candidate. That includes the grand
  antiprism's 20 pentagons, which are mixed in with its 700 triangles,
  and every Catalan dual once its edges were supplied. The support test
  is the step that breaks: it is valid only for convex polytopes, and on
  the star polytopes it rejected every star face.
- **Triangulation.** Every convex candidate has convex faces (regular,
  or kites and irregular triangles for the duals), and `_tri_cycle` fans
  them correctly. The {5/2} pentagram is the exception, covered under
  the stars below.
- **The size envelope is soft, not hard.** `render.py` reserves buffers
  for 1200 edges and 600 points, but `orphan(nbytes)` grows them every
  frame, so a bigger shape draws anyway. The ≤600 V / ≤1200 E limit is
  asserted only for the 3D family (`test_shapes3d.py`). What actually
  grows with size:
  - Line brightness compensation, `dens = clamp(340 / m, 0.42, 1)`. It
    hits its floor at about 810 edges, so anything denser than the
    120-cell just gets brighter and foggier.
  - Face alpha falls as `24 / nfaces`.
  - **The first draw with faces on stalls.** `face_triangles` is
    computed lazily inside `draw`. Today the 600-cell takes 1.7 s and
    the 120-cell 0.8 s.
  - `_planar_cycles` work grows with V × degree² × face length.
    `_is_boundary_face` costs O(V) per candidate cycle, so on big
    shapes it dominates and the total is roughly O(F·V): 33 s for the
    omnitruncated 120-cell, of which the walks took 10 s.
    `edges_by_min_dist` is O(V²) in pure Python: 0.5 s at 720 V, 1.2 s
    at 1152 V, and an estimated ~3 min at 14 400 V.
- **The cost of any new shape, on top of its builder:**
  - append to `SHAPES` (the index is the shape's identity; A3's Klein
    bottle takes 25, so new shapes start at 26);
  - add a row to the ENGINEERING §1 V/E table, and bump the `len(SHAPES)`
    constant in `test_golden.py::test_the_engineering_table_matches_the_code`;
  - add a row to `test_geometry.py::FACE_COUNTS`.

  The golden traces cover only shapes 0–17 and need nothing.

Effort scale:
- **S**: one builder line using existing helpers, plus the bookkeeping
  above.
- **M**: one new helper of about 5–30 lines.
- **L**: new derivation machinery (explicit edges or faces from
  incidence, duals), or past the envelope.
- **XL**: the face pipeline itself has to change.

## Ranked list

This is cheapest and best value first. Duplicates of shapes already
present are left out: the rectified 16-cell is the 24-cell; the
cantellated 16-cell is the rectified 24-cell; the cantitruncated 16-cell
is the truncated 24-cell; the rectified 5-cell and the truncated
tesseract already exist. Vol is the worst volume ratio over the W
sweeps; the floor is 0.15.

| # | Polytope | V / E / F / C | Effort | What is needed | Face risk | Visual value | Verified |
|---|---|---|---|---|---|---|---|
| 1 | Snub 24-cell s{3,4,3} | 96 / 432 / 480 / 144 | S | `auto(expand([φ,1,1/φ,0], "even"))`. These are the 600-cell's vertices minus the inscribed 24-cell. | none: 480 triangles, 0.6 s | High. Famous and non-Wythoffian; reads as a lighter, more open 600-cell. vol 1.00 | yes |
| 2 | Rectified 24-cell r{3,4,3} | 96 / 288 / 240 / 48 | S | `auto(expand([0,1,1,2], "all"))` | none: 96 {3} + 144 {4}, 0.3 s | High. Clean cuboctahedra-and-prisms lattice, and the 24-cell's natural sibling. vol 1.00 | yes |
| 3 | Bitruncated 5-cell 2t{3,3,3} (decachoron) | 30 / 60 / 40 / 10 | S once the 5-cell helper exists (M, once) | perm5 helper, c = (0,0,1,2,2) | none: 20 {3} + 20 {6} | High. 10 identical truncated tetrahedra, cell-transitive; very readable. vol 0.95 | yes |
| 4 | Omnitruncated 5-cell | 120 / 240 / 150 / 30 | S (with the perm5 helper) | c = (0,1,2,3,4) | none: 90 {4} + 60 {6} | High. The 4D permutohedron, an open honeycomb of hexagons. vol 0.98 | yes |
| 5 | Grand antiprism | 100 / 500 / 720 / 320 | M | The 600-cell minus two completely orthogonal great decagons. It needs a ~10-line plane filter, because the decagons are not coordinate planes in these coordinates. Then `auto()`. | none: 700 {3} + 20 {5}; `_planar_cycles` finds the pentagons. 0.8 s | High. Famous; two visible decagonal channels through a 600-cell texture. vol 0.99 | yes |
| 6 | Runcinated tesseract t0,3{4,3,3} | 64 / 192 / 208 / 80 | S | `expand([1,1,1,1+√2], "all")` | none: 64 {3} + 144 {4} | Medium–high. A cube lattice wrapped round a tesseract. vol 0.99 | yes |
| 7 | Bitruncated tesseract 2t{4,3,3} | 96 / 192 / 120 / 24 | S | `expand([0,1,2,2], "all")` | none: 32 {3}, 24 {4}, 64 {6} | Medium–high. Open, hexagon-dominated. vol 0.98 | yes |
| 8 | Disphenoidal 288-cell (dual of the bitruncated 24-cell) | 48 / 336 / 576 / 288 | M | Vertices: `expand([1,1,0,0])/√2 ∪ expand([1,0,0,0]) ∪ expand([½,½,½,½])` (the 24-cell plus its dual, all at radius 1). Edges are the **two** shortest distance classes, which needs a 5-line `edges_by_classes(V, 2)`; `auto()` gives only 144. | none once E is given: 576 isosceles triangles (0.765, 0.765, 1.0), 0.8 s. UVs frame non-equilateral triangles. | High. The one Catalan dual that is crisp and cheap. vol 1.00 | yes |
| 9 | Truncated 16-cell t{3,3,4} | 48 / 120 / 96 / 24 | S | `expand([0,0,1,2], "all")` | none: 64 {3} + 32 {6} | Medium. vol 0.96 | yes |
| 10 | Rectified tesseract r{4,3,3} | 32 / 96 / 88 / 24 | S | `expand([0,1,1,1], "all")` | none: 64 {3} + 24 {4} | Medium. Sparse, close in feel to the 24-cell. vol 0.96 | yes |
| 11 | Runcinated 5-cell t0,3{3,3,3} | 20 / 60 / 70 / 30 | S (perm5) | c = (0,1,1,1,2) | none | Medium. Small and clear. vol 0.97 | yes |
| 12 | Cantellated tesseract rr{4,3,3} | 96 / 288 / 248 / 56 | S | `expand([1,1,1+√2,1+√2], "all")` | none | Medium. vol 0.97 | yes |
| 13 | Bitruncated 24-cell 2t{3,4,3} | 288 / 576 / 336 / 48 | S | `expand([1,1+√2,1+√2,3+2√2]) ∪ expand([0,2+√2,2+√2,2+2√2])`, both "all" | none: 192 {3} + 144 {8}, 0.3 s | Medium. 48 truncated cubes; the octagons read well even at this size. vol 1.00 | yes |
| 14 | Runcinated 24-cell t0,3{3,4,3} | 144 / 576 / 672 / 240 | S | `expand([0,0,√2,2+√2]) ∪ expand([1,1,1+√2,1+√2])`, both "all" | none, 0.7 s | Medium–low. Busy. vol 1.00 | yes |
| 15 | Truncated 24-cell t{3,4,3} | 192 / 384 / 240 / 48 | S | `expand([0,1,2,3], "all")` | none | Medium. vol 1.00 | yes |
| 16 | Truncated / cantellated / cantitruncated / runcitruncated 5-cell | 20/40/30/10, 30/90/80/20, 60/120/80/20, 60/150/120/30 | S each (perm5) | c = (0,1,2,2,2), (0,1,1,2,2), (0,1,2,3,3), (0,1,2,2,3) | none | Medium–low. Variations on #3/#4. vol 0.78–0.92 | yes |
| 17 | Cantitruncated / runcitruncated tesseract; runcitruncated 16-cell | 192/384/248/56; 192/480/368/80; 192/480/368/80 | S | `expand` of [1,1+√2,1+2√2,1+2√2]; [1,1+√2,1+√2,1+2√2]; [1,1,1+√2,1+2√2], all "all" | none | Low–medium. Hard to tell from each other at screen size. vol 0.97–1.00 | yes |
| 18 | Omnitruncated tesseract | 384 / 768 / 464 / 80 | S | `expand([1,1+√2,1+2√2,1+3√2], "all")` | none, 0.3 s | Low–medium. Dense; past `heavy` (>500 E). vol 0.98 | yes |
| 19 | Cantellated 24-cell rr{3,4,3} | 288 / 864 / 720 / 144 | S | `expand([1,1,1+√2,3+√2]) ∪ expand([0,2,2+√2,2+√2])`, both "all" | none, 0.7 s | Low. Past the line-density floor. vol 1.00 | yes |
| 20 | Cantitruncated 24-cell | 576 / 1152 / 720 / 144 | S | `expand([1,1+√2,1+2√2,3+3√2]) ∪ expand([0,2+√2,2+2√2,2+3√2])` | none, 0.5 s | Low. At the envelope; reads as a mesh ball. vol 1.00 | yes |
| 21 | Runcitruncated / omnitruncated 24-cell | 576/1440/1104/240; 1152/2304/1392/240 | S–L | two or three `expand` classes | none, 0.8 s / 1.0 s | Low. Over 1200 E. | yes |
| 22 | Second-tier 120/600 forms (rectified 600-cell and up) | smallest is 720 / 3600 / 3600 / 720 | L | 6–17 `expand` classes each, or a `wythoff` helper; `auto()` 0.5 s+ | Faces correct but slow: first-draw stall 4–13 s at 720–3600 V, 33 s for the omnitruncated 120-cell | Low. All of them read as fog (see the rectified 600-cell tile). vol 1.00 | yes |
| 23 | Stars with triangle or convex-pentagon faces | see stars | L | explicit E (one distance class) and explicit F | needs explicit F; triangulation is fine | Low: white-out (see tiles) | yes |
| 24 | Other Catalan duals | see duals | L | explicit E from facet incidence | faces fine once E is known | Low–medium | yes |
| 25 | Stars with {5/2} faces | see stars | XL | explicit F plus a triangulation that adds points | fights `_tri_cycle` / UVs | Low | yes |

**Measured where my memory was wrong:** the truncated 600-cell is 1440
V / **4320 E** / **3600 F** (2400 {3} + 1200 {6}) / 720 C, not
3600 E / 2400 F.

### The 120/600 family in full (all verified, `auto()` exact, faces exact)

| Form | V / E / F / C | faces + time |
|---|---|---|
| rectified 600-cell | 720 / 3600 / 3600 / 720 | 3600 {3}, 7.9 s |
| rectified 120-cell | 1200 / 3600 / 3120 / 720 | 2400 {3} + 720 {5}, 3.9 s |
| truncated 600-cell | 1440 / 4320 / 3600 / 720 | 2400 {3} + 1200 {6}, 3.5 s |
| truncated 120-cell | 2400 / 4800 / 3120 / 720 | 2400 {3} + 720 {10}, 2.7 s |
| runcinated 120-cell | 2400 / 7200 / 7440 / 2640 | 7.1 s |
| cantellated 600-cell | 3600 / 10800 / 8640 / 1440 | 11.8 s |
| cantellated 120-cell | 3600 / 10800 / 9120 / 1920 | 12.8 s |
| bitruncated 120-cell | 3600 / 7200 / 4320 / 720 | 3.9 s |
| cantitruncated 120-cell | 7200 / 14400 / 9120 / 1920 | 11.4 s |
| cantitruncated 600-cell | 7200 / 14400 / 8640 / 1440 | not run |
| runcitruncated 120-cell / 600-cell | 7200 / 18000 / 13440 / 2640 (both) | not run |
| omnitruncated 120-cell | 14400 / 28800 / 17040 / 2640 | 32.8 s |

### Catalan duals (duals of uniform polychora)

The vertices are the primal's cell centres, scaled to 1 / (the cell
plane's distance), and they sit on two to four radii. Edges connect
cells that share a 2-face. Faces correspond to the primal's edges and
are convex but not regular. Once explicit E was supplied,
`_planar_cycles` + `_is_boundary_face` found exactly the primal's E as
faces for every dual tried (all A4, B4 and F4, and the small H4 ones).
Edges are the real problem:

- **`auto()` already works:** the dual of the runcinated 5-cell
  (30 / 70 / 60 / 20, 60 rhombic faces, two radii).
- **The k shortest distance classes are exactly the edges** (an
  `edges_by_classes(V, k)` helper is enough):
  - the dual of the bitruncated 5-cell (10 / 40 / 60 / 30);
  - the disphenoidal 288-cell (#8);
  - the dual of the truncated 16-cell (24 / 96 / 120 / 48);
  - the dual of the runcinated 24-cell (240 / 672 / 576 / 144);
  - the duals of the rectified and truncated 600-cell (720 V; over the
    envelope).
- **Everything else** (rectified, truncated, cantellated, cantitruncated,
  runcitruncated and omnitruncated duals) has edge lengths that do not
  form a prefix of the distance classes. These need E from facet
  incidence: a polar-dual helper that finds the primal's facets. Without
  scipy, that means deriving the facets from the Wythoff construction
  (L). The most familiar of them, the tetrakis-style duals of the
  rectified and truncated tesseract (24 / 88 / 96–128 / 32–64), fall in
  this group.

### Cheap extras (all verified; `prism()` and `duoprism()` as they are)

- **Other duoprisms.** `duoprism(n, m)` with no changes. Faces were
  verified for 3,4, 5,5, 3,8, 5,10 and 8,8 (vol 0.40–0.97).
- **Antiprism prisms** (n = 5, 7, 8). `prism()` of a uniform antiprism
  (height √(1 − (2r·sin(π/2n))²)) works with `auto()`. 4n V; faces
  {3}/{4}/{n}. Vol drops as n grows (0.71 → 0.47).
- **Other uniform polyhedral prisms.** Example: the icosidodecahedral
  prism, 60 / 150 / 124 / 34, vol 0.55, vertices
  `cyc3(0,0,φ) + cyc3(½,φ/2,φ²/2)`. The truncated icosahedral prism is
  120 / 240 / 154 / 34, vol 0.36.
- **Duoantiprisms** (the 2p,2q-duoprism alternated). They are not
  uniform: with equal radii the ring and cross edges differ (1.732 vs
  1.414 for 3-3), so `auto()` finds only the cross edges (36 of 72 for
  3-3; 64 of 128 for 4-4). The builder knows its own edges, as
  `duoprism()` does, so this is M. Hull counts at equal radii:
  3-3 is 18 / 72 / 84 / 30 and 4-4 is 32 / 128 / 144 / 48. I did not
  run faces on them.

## Tiers

- **Cheap now (fits the machinery as is):**
  - every A4 and B4 form, and the F4 forms up to the cantitruncated
    24-cell;
  - the snub 24-cell and the grand antiprism (one small vertex filter);
  - the duoprisms and polyhedral and antiprism prisms;
  - the dual of the runcinated 5-cell.

  The A4 forms need the one perm5 helper. In this tier `auto()` is
  exact, the faces are exact, triangulation is correct, and the first
  face build takes ≤ 1 s.
- **Needs explicit edges or faces:**
  - the Catalan duals (explicit E; faces then extract correctly);
  - the duoantiprisms (explicit E);
  - the stars whose faces are triangles or convex pentagons ({3,5/2,5},
    {3,3,5/2}, {5,5/2,5}, {5,3,5/2}, {5,5/2,3}): explicit E from one
    distance class, and explicit F because the support test rejects
    every star face. Their faces are simple, planar and regular, so
    `_tri_cycle` and `face_uvs` handle them.
- **Over the envelope, correct but slow and foggy:** everything in the
  120/600 family past the two regular ones, and the runcitruncated and
  omnitruncated 24-cell.
- **Fights the face pipeline:** the four stars with {5/2} faces
  ({5/2,5,3}, {5/2,3,5}, {5/2,5,5/2}, {5/2,3,3}).

## The stars

All ten Schläfli–Hess polychora are star polytopes drawn on the
vertices of the 600-cell (nine of them) or the 120-cell (the great grand
stellated 120-cell). The renderer draws only vertices, edges and 2-faces,
never cells, so a star is fully described here by its vertex set, its
edge distance class and its face type. At unit circumradius, the
600-cell's vertex pairs fall into eight distance classes:

| class | 0.618 | 1.000 | 1.176 | 1.414 | 1.618 | 1.732 | 1.902 | 2 |
|---|---|---|---|---|---|---|---|---|
| neighbours per vertex | 12 | 20 | 12 | 30 | 12 | 20 | 12 | 1 |

Each star's edge degree is the vertex count of its vertex figure. I ran
`_planar_cycles` on each class's graph and classified the 5-cycles by
winding number:
- **0.618:** 1200 triangles and 720 convex pentagons.
- **1.000:** 720 pentagrams and 720 convex pentagons, plus 2400
  triangles, 1800 squares and 200 hexagons that are not star faces.
- **1.618:** 1200 triangles and 720 pentagrams.
- **1.176, 1.732 and 1.902:** only cycles through the centre.
- **The 120-cell's vertex set, class 1.851 (degree 4):** 720 pentagrams.

Each star matches exactly one of these. Which class carries which star
is deduced from the degree and the face type; the reference counts
agree, and only the assignment of the two triangle-faced classes rests
on my memory:

| Star | V / E / F / C | edges | faces | in this renderer |
|---|---|---|---|---|
| icosahedral 120-cell {3,5,5/2} | 120 / 720 / 1200 {3} / 120 | 0.618 | the 600-cell's triangles | **identical to the 600-cell** (even `faces()` finds them) |
| great 120-cell {5,5/2,5} | 120 / 720 / 720 {5} / 120 | 0.618 | convex pentagons | the 600-cell's wireframe plus pentagon fog |
| grand 120-cell {5,3,5/2} | 120 / 720 / 720 {5} / 120 | 0.618 | same pentagons | identical to the great 120-cell |
| great icosahedral 120-cell {3,5/2,5} | 120 / 720 / 1200 {3} / 120 | 1.618 | triangles | new wireframe; faces white out |
| grand 600-cell {3,3,5/2} | 120 / 720 / 1200 {3} / 600 | 1.618 | same triangles | identical to the great icosahedral 120-cell |
| great stellated 120-cell {5/2,3,5} | 120 / 720 / 720 {5/2} / 120 | 1.618 | pentagrams | same wireframe as the two above |
| grand stellated 120-cell {5/2,5,5/2} | 120 / 720 / 720 {5/2} / 120 | 1.618 | same pentagrams | identical to the great stellated 120-cell |
| small stellated 120-cell {5/2,5,3} | 120 / 1200 / 720 {5/2} / 120 | 1.000 | pentagrams | new wireframe |
| great grand 120-cell {5,5/2,3} | 120 / 1200 / 720 {5} / 120 | 1.000 | convex pentagons | same wireframe as the one above |
| great grand stellated 120-cell {5/2,3,3} | 600 / 1200 / 720 {5/2} / 120 | 1.851 on the 120-cell set | pentagrams | new wireframe; a white fuzzball |

So the ten stars give **three new wireframes**: class 1.000, class
1.618, and the 120-cell set's 1.851. With faces on, they give six new
pictures and one exact duplicate of the 600-cell. Every star has
vol 1.00, because the vertex sets are the 600-cell's and the 120-cell's.

**Where they fight the pipeline:**
- **Faces.** `_is_boundary_face` passed **0** star faces in every class
  except 0.618's triangles. A star's faces pass through the interior,
  so the half-plane support test has no meaning for them. Every star
  needs explicit `F`. That much is cheap: filter `_planar_cycles` by
  length and winding, at 1.5–6 s per class.
- **Pentagram triangulation.** The turn test in `_tri_cycle` sees a
  {5/2} cycle turn the same way at every corner and calls it convex, so
  it fans it from `cyc[0]`. On a 801² grid, that fan covered the whole
  star but also 45% more area outside it (the five notches), and it
  covered 146k cells twice. It renders as a filled pentagon with a
  brighter pentagonal core. No set of triangles on the pentagram's own
  five vertices is exact: every such triangle either has a pentagon side
  and takes in its notch, or does not exist (the five diagonals contain
  no triangle). A correct fill needs the five inner crossing points as
  extra vertices. Because `face_triangles` indexes `V`, those points
  would either join `V` and be hidden from the point and edge passes, or
  need a separate face-vertex path. That is a change to the face
  pipeline (XL). The projection is projective, so crossing points
  computed in 4D stay on the crossings after projection; the geometry
  is sound and only the plumbing is missing.
- **UVs.** `_face_xy` and `face_uvs` take the cycle's own vertex order
  as the polygon outline. For a pentagram, the UV polygon is the star
  path, and the fan's triangles sample UVs across the notches.
- **How they look, even with correct faces.** 720–1200 large faces cut
  through the middle of the shape and overlap. At this app's scale and
  face alpha, the sheet's tiles are white-outs. Lines only is the more
  readable way to show a star.

**The overlap with A2.** This is the risk area A2 probes with lifted
Heart and Star caps: `_face_xy`, `_tri_cycle` and `face_uvs` assume a
near-planar simple polygon. The Star shape's cap is safe as built,
because its 10-point outline is simple, so it ear-clips correctly. It
breaks in two ways that match the stars here. A lift that is not affine
over a cap makes the cap non-planar, and `_face_xy` then projects it
best-effort onto a plane where the ear-clip can overlap. A face given as
a self-intersecting cycle is wrongly classed as convex and fanned. If
the stars are ever wanted with faces, the fix (Steiner points, or
triangles given explicitly by the builder) would serve both.

## Recommendation

My recommendation; the owner decides. These four give the most new
looks for the least machinery, and none touches the face pipeline:

1. **Snub 24-cell.** A one-line builder.
2. **Rectified 24-cell.** A one-line builder.
3. **The 5-cell family through one perm5 helper.** Start with the
   **bitruncated 5-cell** and the **omnitruncated 5-cell**; the other
   five forms then cost one line each.
4. **Grand antiprism.** A ~10-line decagon filter on the 600-cell.

A fifth, if a dual is wanted: the **disphenoidal 288-cell**, which needs
a 5-line two-class edge rule. All five are under 500 edges and build
their faces in under a second. The two most distinct from what the app
already has are #3/#4 (hexagon-dominated) and the 288-cell.

Not recommended for now: the 120/600 second tier (fog, and 4–33 s
first-face stalls) and the stars (one is a duplicate, three repeat
wireframes, the pentagram faces need the XL triangulation change, and
all of them white out with faces on).
