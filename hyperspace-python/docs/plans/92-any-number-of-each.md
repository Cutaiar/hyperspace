# Plan 92 — any number of scenes, shapes, backdrops and patterns

**A design, not a build** (2026-11-28). Nothing here is built. **Revised the same day
(§6, §7):** the owner's answers — one world, a scene a camera onto it, a point cloud a
geometry like any other — overrule §3–§5 where they differ. Tags: **[V]** read in the
code, **[M]** measured in this session, **[Rec]** a recommendation.

The owner, 2026-11-28, asked whether a spawn should be able to *replace* the host's scene,
shape, backdrop or pattern (wave 3 P2's row, left with no kind by plan 90 H3):

> "i do not want to have rules like 'you can only have one' for things like
> shape/scene/pattern/background."

So the replace row is retired (register row 1200, DECISIONS "No spawn replaces a node of
the host"). This plan removes `patches.ONE_PER_FRAME` the way effects, delays, resizes and
mattes already work: a second one is `shape.2`, and a spawn into a host that has `shape`
lands its own as `shape.2`. Nothing needs replacing.

## 1. Why there is one of each today [V]

None of it is a GPU limit. Each kind was written as *the* one, in four places.

**The name (all four).** `graph._wired_kind` knows `scene`, `shape`, `backdrop` and
`pattern` only as bare names; `scene.2` is no node. The frame builder makes
`Shape("shape")`, `Scene("scene")`, `Composite(BACKDROP)` and the pattern by fixed name
(`graph.py`, `_make`). Their entries are `_FrameAt` (`n` is always 1). `patches.spawn`
cannot rename one (`patches.py`, "never renumbered"), hence `Landing.taken`.

**Shape.**
- Its params have no instance segment and are bound to the one `ViewState`
  (`params.py`, 44 `_attr(view, …)` bindings): `rot.rate.*` / `rot.phase.*` (the 4D
  spin), the shape keys of `view.*` (which polytope, faces, edges, points, brightness …),
  `fx.face_map`, and `camera.*` (its world pose). Two shapes would read the same knobs.
- The renderer holds one set of per-pass face state (`Renderer._face_verts`, `_copies`,
  `_cover_cells`, `_pic`, `_face_layer`, the faces' picture `_face_picture`).
- The CPU half (rotate, project, painter-sort, upload: `Renderer.draw_scene`) runs once.

**Pattern.**
- One bank of params: `pattern.*` (the selector, the eight mod inputs, mix, media) and
  `view.pattern*`, `view.media_*` (`patches.is_pattern_view_key`).
- One face layer and one painted picture (`Renderer._pattern_into`, `_pattern_picture`,
  `_face_layer`).

**Scene.**
- It draws into the renderer's one `SceneTarget` (`Renderer.scene`: colour, MSAA, depth)
  and sets renderer-wide fields while it runs (`scene_ground`, `_pic`, `_face_layer`).
- Its pins are fixed ids (`graph.PINS`: `scene.cover`, `scene.depth`); `COVER` is one node.
- The eye (`eye.*`) is "the first scene's" (`graphview._eye_owner`).
- It has no params of its own: `scene.*` is the band scene's (a shared meta group), so
  `scene.2` collides with no param id.

**Backdrop.** The weakest tie: a `Composite(BACKDROP, over=scene, under=image)`. One
`backdrop.alpha` (`view.backdrop_alpha`), the deck's one backdrop channel
(`back_channel` in the frame builder), and the scene asking whether it is laid over *the* backdrop
(`laid_over("scene")`, which sets its ground alpha).

## 2. What a second one costs [M]

Allowing several costs nothing per frame until a second one exists: the build makes only
what a wire names. Each extra copy then costs what the first does, since it is the same
work again.

Real hardware, from `docs/plans/assets/24-26-27-run/reports/routing-fps-report.md`
(the Mac, 2026-10-15): the whole scene pass, the shape and its pattern inside it, about
**0.5 ms** of GPU a frame against 8.3 ms at 120 fps.

In the container, offscreen 1280×720, per-node `PassTimer` medians and frame wall time on
llvmpipe (a software rasteriser, ~10× the Mac; read the ratios):

| What | Tesseract | 600-cell |
|---|---|---|
| Scene + shape, plain faces (no pattern) | 2.1 ms | 11.2 ms |
| Scene + shape + pattern on the faces | 3.9 ms | 25.7 ms |
| Pattern's share (on the faces) | +1.8 ms | +14 ms |
| Pattern drawn straight to an output | ~1 ms | ~1 ms |
| Backdrop, nothing under it | 2.9 ms | 3.4 ms |
| Pattern fed into the backdrop's image | +11 ms frame time (not under any node's timer) | +9.5 ms |
| CPU of `draw_scene` (cProfile, 600-cell) | — | 1–2.5 ms |

Memory of a second scene's target: colour + depth at output size, ~26 MB at 1080p
single-sampled, ~75 MB at 4× MSAA.

Reading: a backdrop is one full-screen blend (an effect's weight); a scene costs what it
draws; a shape's cost grows with its polytope and has a CPU half a faster GPU does not
shrink; a pattern costs the face pixels it shades. Two extra scene + shape + pattern sets of
ordinary polytopes fit a 120 fps frame on the Mac; a dense polytope under a busy pattern is
where it starts to bite. **Hand check:** on the Mac, GRAPH's **gpu cost** chip over a
600-cell with a pattern, then with a backdrop, to replace these estimates.

## 3. The design [Rec]

**Ids.** Instance n ≥ 2 is `<kind>.<n>` (`scene.2`, `shape.2`, `backdrop.2`,
`pattern.2`), entries `{"kind": "shape", "instance": 2}` as a delay's. The first keeps its
bare name, so **no saved file, param id or binding moves** (`params.instance_id`'s rule:
the first instance keeps today's id).

**Params.** `params.instance_id` on each group a kind's params live in, as every other
numbered node (owner, Q2, §6): shape 2's are `rot.2.*`, `view.2.<shape key>`,
`camera.2.*`; pattern 2's `pattern.2.*`, `view.2.<pattern key>`; backdrop 2's
`backdrop.2.alpha`. Declared and dropped as the frame names them (`params.declare_delays`'s shape),
each over its own state object (a `ShapeState` / `PatternState` cut from `ViewState`, the
first instance's still the `ViewState`'s fields). `graphview.OWNERS` and
`patches._param_rows` learn the numbered owners.

**Renderer.** Per-instance state where it is per-instance today:
- a `SceneTarget` per scene (`Renderer.scenes[name]`), its ground per scene;
- the shape's per-pass face state moved onto the `Shape` node or a per-shape record, so
  two shapes in one scene, or in two scenes, do not overwrite each other;
- a face layer / painted picture per pattern;
- `scene.<n>.cover`, `scene.<n>.depth` pins (`graph.PINS` as a pattern, as segments' are).

**Spawn.** `ONE_PER_FRAME` empties kind by kind as each phase lands; when it is `()`,
`Landing.taken`, `refusal` and `TAKEN_WORDS` go, and DECISIONS' "A spawn never makes a
second …" row is rewritten.

**An older build.** A file with `shape.2` is one an older build cannot draw. Per REVIEW
("what a build from before makes of a file this branch writes"): `scene.2` is no node to
it, so it would not draw it. Either a schema bump or a DECISIONS row saying why not (the
precedent: both Macs run one build) — to settle in phase 1, checking what an older
`read_graph` does with an unknown frame name before choosing.

## 4. Build order [Rec] — one PR each

1. **Backdrop.** Numbered composite; `backdrop.<n>.alpha`; `back_channel` per backdrop;
   `laid_over` asked per scene. Smallest; proves the id, param and spawn path.
2. **Scene.** A target per scene, numbered pins and cover, ground per scene, the eye per
   scene or shared (Q1).
3. **Shape and pattern together.** Per-instance state and params; the renderer's face state
   per shape; a layer per pattern. A second pattern is only useful with a second shape (or as
   a picture), so they land as one.
4. **Retire the rule.** `ONE_PER_FRAME`, `Landing.taken`, `TAKEN_WORDS`; the DECISIONS row;
   hand checks on the Mac (two scenes side by side, two shapes in one scene, the gpu cost
   chip).

## 5. Questions for the owner

- **Q1. The eye.** Does `scene.2` see through its own eye (its own `eye.2.*`), or through
  the first scene's? [Rec: its own, defaulting to a copy of the first's at the add.]
- **Q2. Param names for the second shape.** `rot.2.*` / `view.2.*` (today's groups, numbered)
  or `shape.2.*` / `pattern.2.*` (one prefix per node, the first keeping its old ids)?
  [Rec: one prefix per node; `view.*` mixes the shape's and the pattern's keys today.]
- **Q3. A second shape's pose.** `camera.*` is the shape's world pose: does each shape carry
  its own place in the world (so two shapes in one scene stand apart)? [Rec: yes.]
- **Q4. Defaults when added from the canvas.** A new `shape.2` with no pattern wired has
  plain faces, as `shape` does unwired. [Rec: as is; the add menu offers "shape + pattern".]

## 6. The owner's answers (2026-11-28) — overrule §3–§5 where they differ

> "there should be one rectified world model, but you can have multiple cameras within
> that world. Maybe what a scene is is kind of the formalization of a camera and a frustum,
> and the geometries that should be allowed to be seen by that camera."
>
> "I don't want to end up with multiple world concepts where world objects are either a
> member of one or the other … world objects should be a part of the world, and a scene is a
> view into that world."
>
> "The second shape settings … need to be generalized the same way that all of our other
> nodes were generalized. Yes, each shape should have its own position in the world. I think
> a newly added shape should just default to a tesseract."

| Q | Answer |
|---|---|
| Q1 the eye | Each scene is a camera: its own eye and frustum (`eye.2.*` for `scene.2`). |
| Q2 param names | As every other numbered node: `params.instance_id` on today's groups (`rot.2.*`, `view.2.*`, `camera.2.*`, `pattern.2.*`), not a new prefix per node. |
| Q3 a shape's pose | Each shape has its own place in the world. |
| Q4 a new shape | A tesseract. |

### 6.1 One world, scenes as cameras [Rec]

**What changes in meaning.** Today a scene *is* the world: what is wired into
`scene.geometry` is drawn in it, posed by the one `camera.*`. After this plan:

- **The world** is every geometry node the frame holds — shapes, hands, the clouds — each
  with its own pose (`camera.*` for the first shape, `camera.2.*` for shape 2; hands and
  clouds keep the poses they have). There is one world per frame and no node belongs to a
  scene.
- **A scene** is a camera onto it: an eye (`eye.*`, `eye.2.*` …), a frustum, its target and
  pins, and **which world objects it may see**. A wire `shape.2 → scene.geometry` stays
  the way that is said, but it now reads "scene may see shape 2", not "shape 2 is in
  scene". A geometry with no wire into any scene is still in the world, just unseen.
- **The same object seen twice.** A shape wired into two scenes is one object: its 4D turn,
  projection and sort (the CPU half of `draw_scene`) run once a frame, and each scene draws
  that result through its own eye. The cost of a second scene is then its draw (§2), not a
  second shape's CPU.

**What the renderer needs.** Split `Renderer.draw_scene` into a per-object "pose and
project once" step and a per-scene "draw through this eye" step; a `SceneTarget` and per-pass face
state per scene (§3); depth-testing between objects is per scene, as now. The first scene
keeps `eye.*` and today's ids, so every saved show draws as it does.

**Defaults.** A new shape is a tesseract at the world's origin, faces plain until a
pattern is wired (Q4). A new scene sees what the first sees at the moment it is added
(its wires copied), its eye a copy of the first's — then each is its own (Q5 below).

### 6.2 Build order, revised

1. **Backdrop** — unchanged (§4.1).
2. **The world and a second camera.** Split pose/project from draw; `scene.<n>` with its
   own eye, target and pins; one shape seen by two scenes as the proof (two outputs, two
   angles on one tesseract).
3. **Shape and pattern instances.** `shape.<n>` (a tesseract, its own `rot.<n>`,
   `view.<n>`, `camera.<n>`), `pattern.<n>`; the renderer's face state per shape.
4. **Retire the rule** — unchanged (§4.4).

### 6.3 New questions

- **Q5. A new scene's sight.** When a scene is added from the canvas, does it start seeing
  every world object (wires made for each), or nothing until wired? [Rec: what the first
  scene sees, copied at the add; an empty scene reads as broken.]
- **Q6. The clouds.** Today every scene draws the meta controller's point clouds without a
  wire (the frame builder's `clouds`, added to every `Scene`). As world objects, are they seen by every camera, or only by those
  wired to them? [Rec: every camera, as today, until someone asks otherwise — they have no
  canvas node to wire.]
- **Q7. `camera.*` is a shape's pose.** With scenes as cameras, the name reads wrong:
  `camera.yaw` turns the shape, `eye.*` is the camera. Renaming is a file-format change
  (REVIEW: a mapping, a backup, an end-to-end test). [Rec: keep the ids, relabel on the
  panel ("Shape yaw"), and leave the rename for later.]

## 7. The owner's second answers (2026-11-28) — overrule §6 where they differ

> "The newly added scene should just have its camera pointing at the world origin. I think
> your recommendation is fine for what it sees."
>
> "point clouds need to be treated like any other piece of geometry, and they should have a
> canvas node … Not every camera should draw them. Point clouds should act like instanced
> geometry, just like all of the other shapes do. The relabeling for eye-related stuff is
> fine."

| Q | Answer |
|---|---|
| Q5 a new scene | Its eye aims at the world origin (not a copy of the first's). It sees what the first scene sees, its wires copied at the add. |
| Q6 the clouds | Ordinary geometry: a canvas node, seen only by the scenes wired to it, instanced like a shape. |
| Q7 `camera.*` | Keep the ids; relabel on the panel ("Shape yaw" …). |

### 7.1 The point cloud today [V]

There is a **Point cloud** node on the canvas (`graphview` kind `cloud`, a geometry out),
but it is the meta controller's, not the show's:

- **One per listed cloud device**, made by the rig (`graph.cloud_name`: `cloud`,
  `cloud.2` … by the device's place in the list), never added, deleted or saved in a patch
  (`patches.FIXTURE_NODES`, `NOT_REMOVABLE`).
- **Its wire into the scene is the meta controller's too** (`graph.cloud_wire`,
  `is_cloud_wire`, `is_fixture_wire`): `cloud → scene.geometry` stands by itself until the
  show cuts it (`bus_cuts`), so every scene of today's one sees it. Its description says
  "drawn in every scene".
- **One set of knobs for every cloud**: `cloud.size`, `cloud.scale`, `cloud.bright`,
  `cloud.colors` are bound to the one `ViewState` and shown on the first cloud
  (`graphview._cloud_owner`). Its pose is a uniform scale about the world origin; it has no
  position, turn or copies of its own.

### 7.2 What it becomes [Rec]

- **A node the show owns.** Added from the canvas like a shape, numbered (`cloud`,
  `cloud.2` …), saved in the frame and in patches, deleted like any node. It names **its
  source** — which cloud device it reads (`role`, a pick on its node, as a channel node
  names its channel) — so two nodes may read one device, and a node whose device is absent
  draws nothing, said on its node.
- **Seen only where wired.** No standing meta-controller wire: `cloud.<n> → scene.<m>.geometry`
  is a wire like a shape's, one per camera that should see it.
- **Its own params, numbered as every node** (Q2): `cloud.<n>.size`, `.scale`, `.bright`,
  `.colors`, plus a **world pose** like a shape's (position, turn, scale) and the shape's
  **instancing** (its copies, `Renderer._copies_of`'s rule), so a cloud lays out as a shape's
  copies do.
- **Old shows.** A show saved with the meta controller's standing cloud wire is migrated to
  an explicit `cloud → scene.geometry` wire and a cloud node per device it listed, so it
  draws as before (REVIEW: the mapping, a backup before the first rewrite, an end-to-end
  test of an old show). A cut cloud wire (`bus_cuts`) stays cut, which is: no wire.

### 7.3 Build order, revised again

1. **Backdrop** (§4.1).
2. **The world and a second camera** (§6.2.2); a new scene's eye on the origin.
3. **Shape and pattern instances** (§6.2.3).
4. **The point cloud as geometry**: the show's node, its source pick, numbered params, a
   world pose and copies; the meta controller's cloud wire retired with its migration.
5. **Retire the rule** (§4.4), and the panel relabel of `camera.*` (Q7).

### 7.4 New questions

- **Q8. A device with no node.** When a cloud device connects and no cloud node reads it,
  is a node added for it (wired to the first scene, as today), or nothing until the show adds
  one? [Rec: nothing added to a saved show; a fresh show's starter frame has one cloud node
  per listed device, wired to its scene, so a new rig still sees its camera at once.]
- **Q9. A cloud's instancing.** Does a cloud take every copy knob a shape has (the copies'
  layout, spin, spread), or only position and count? [Rec: the shape's whole set — one rule
  for "instanced geometry".]
