# Plan 92 — any number of scenes, shapes, backdrops and patterns

**A design, then a build** (2026-11-28). Phase 1 is built (§8), phase 2 (§9). **Revised the same day
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
> "Turning a Point cloud node from a rig-scoped node to a show-scoped node should not be in
> this plan. That should just be its own work that we can independently execute and pick up
> working on this plan once that is finished and merged into main."

| Q | Answer |
|---|---|
| Q5 a new scene | Its eye aims at the world origin (not a copy of the first's). It sees what the first scene sees, its wires copied at the add. |
| Q6 the clouds | Not this plan: the point cloud becomes a show's geometry node in its own work (below), merged to main first. |
| Q7 `camera.*` | Keep the ids; relabel on the panel ("Shape yaw" …). |

### 7.1 First, apart: the point cloud as a show's node

Today the **Point cloud** node is the rig's: one per listed cloud device (`graph.cloud_name`),
never added, deleted or saved in a patch (`patches.FIXTURE_NODES`), wired into the scene by
the meta controller (`graph.cloud_wire`, standing until cut), its knobs one shared set
(`cloud.size`, `.scale`, `.bright`, `.colors` on the one `ViewState`). Its own work, merged
to `main` before this plan builds, makes it the show's: added and saved like any node,
naming its device by hand (nothing picked when a device connects), seen only where wired,
numbered params, and — the owner: "a point cloud is literally just a list of vertices, the
same way a shape would be … a special type of shape that has no edges, only vertices" — the
shape's pose and copies.

This plan then treats a cloud as one more world object (§6.1): a camera sees it where it is
wired, as a shape.

### 7.2 Build order, revised again

1. **Backdrop** (§4.1).
2. **The world and a second camera** (§6.2.2); a new scene's eye on the origin.
3. **Shape and pattern instances** (§6.2.3).
4. **Retire the rule** (§4.4), and the panel relabel of `camera.*` (Q7).

Starts once §7.1's work is on `main`.

## 8. Phase 1 built: any number of backdrops (2026-11-28, row 1215)

- **The section.** `graph.BackdropAt(n)`: `backdrop` is declared by a wire, as before;
  `backdrop.<n>` by its entry `{"kind": "backdrop", "instance": n}` (`entry_declares`,
  `NUMBERED_FRAME_KINDS`, which phases 2–3 extend). A wire to an undeclared one says
  `no backdrop.2 node in this graph (add one: {"kind": "backdrop", "instance": 2})`.
- **The build.** Every backdrop by the first's path (the first unchanged node for node):
  its own `scene` over its own `image`; a channel straight in its own keyed channel node
  (`channel.a(backdrop.2)`, `_back_channel`), any other picture laid at its alpha — the
  first's `ViewState.backdrop_alpha`, a later one's read by `graph.alpha_of` from
  `Frame.backdrops`. A scene into any backdrop's `scene` is laid over (`laid_over`), its
  ground see-through. (Devin on #527: a keyed channel's holes stay see-through.)
- **The params.** `backdrop.alpha` stays the view's; `params.declare_backdrops` declares
  `backdrop.<n>.alpha` on a `view.BackdropState`, from the landing (`loadable._settle`),
  sorted on load and on a new patch as a matte's (`is_backdrop_id`). Each sits on its node
  (`graphview.OWNERS["backdrop"]`), and node mode lists only its own (`graphview.param_ids`
  skips a later instance's ids, for every numbered kind — Devin on #527).
- **GRAPH and patches.** The picker, the backdrop starter and the cable menu add the next
  (`graphview.next_backdrop`; `ONCE` lost `backdrop`); a delete joins its scene on as before.
  A patch's backdrop spawns as the next one, its alpha renamed (`ONE_PER_FRAME` lost
  `backdrop`).
- **No schema bump.** An older build refuses a section holding `backdrop.2` in words
  ("backdrop node: no key 'instance'"); both Macs run one build.
- **Tests.** `tests/test_backdrops_numbered.py`; hand check 982.

Next: phase 2, the one world and a second camera.

## 9. Phase 2: the one world and a second camera (2026-11-28, rows 1216–1219)

### 9.1 The build note [V]

What changes, read in the code before building:

- **The section.** `scene` is declared by a wire, as today; `scene.<n>` by its entry,
  `{"kind": "scene", "instance": n}` (`graph.SceneAt(n)`, `NUMBERED_FRAME_KINDS` gains
  `scene`, `entry_declares`). Its pins are `scene.<n>.cover` and `scene.<n>.depth`
  (`graph.scene_pin`, `pin_node`); its `geometry` takes several wires in their order
  (`graph.is_many_port`, which the four `in MANY_PORTS` sites in `graphview` and `patches`
  now ask). A wire to an undeclared one says `no scene.2 node in this graph (add one: …)`.
- **The renderer.** The per-scene state that was renderer-wide moves onto a
  `render.ScenePass` per scene: its `SceneTarget`, its `CoverTarget`, the face state its
  shape's draw leaves for its cover (`_face_verts`, `_copies`, the copies' rows, `_scene_mats`,
  `_cover_cells`), what the shape's `prepare` hands it (`_pic`, `_face_layer`,
  `_face_plain`), its ground (`scene_ground`) and its eye. `Renderer.scene_pass(name)`
  makes one current for a scene's run and its cover's; the renderer's old fields are the
  current pass's (properties), the first scene's outside any run — so every caller that
  read `r.scene` or `r._pic` reads the scene being drawn, and nothing else moved.
- **Pose once, draw per eye.** `Renderer.draw_scene` is split: `pose_shape` (the CPU half —
  `shapeframe.frame`, the 4D turn and projection, the painter sort, the depth cue, every
  vertex array) and `draw_posed` (the eye's matrix, the copies it sees, the clear, the
  draws, the depth pass). `graph.Shape.posed` makes the pose on the first ask of a frame and
  keeps it in the root frame's data; each scene draws it through its own eye, uploading the
  vertices once (`Renderer._in_bufs`). `draw_scene` is the two in a row, so every caller
  of it (the wire thumbnail, the tests) is as before.
- **The eye.** `geometry.eye_matrix` takes `yaw` / `pitch`, an orbit about the world
  origin, still looking at it (`eye_turn`, `eye_position`); at 0, 0 it is the matrix it always
  was. A scene past the first has an `EyeState` (`view.py`; `ViewState.eyes`, `Frame.eyes`)
  and four params, `eye.<n>.fov`, `.distance`, `.yaw`, `.pitch`
  (`params.declare_scenes`, declared from the landing as a matte's, sorted on load by
  `is_eye_id`). A new one is the default eye: on the world's origin (§7, Q5). The first
  keeps `eye.fov` and `eye.distance` and gains nothing (row 1217).
- **World objects through each eye.** The hands are settled once a frame
  (`Ghost.settle`), then drawn through the scene's eye (`ghost.Settled.through`, from the
  calibration it keeps); a point cloud's matrix is the scene's eye (`graph.eye_of_frame`).
- **GRAPH.** `scene` leaves `graphview.ONCE`: the picker adds the next scene
  (`next_scene`), its geometry wires copied from the first's in their order
  (`_seen_copied`), its eye on the origin. A delete is any node's. `eye.<n>.*` sits on its
  scene's node (`graphview._eye_owner`, `param_ids`).
- **Patches.** `scene` leaves `patches.ONE_PER_FRAME`; a patch's scene spawns as the next
  number (the ordinary rename), a numbered scene carrying its `eye.<n>.*` renamed with it
  (`patches._param_rows`, `_Renamer.param`). The first scene carries no param, as before:
  `eye.*` is the look's.
- **The file format: no bump** (row 1219). No saved id moves: the first scene's every id
  (`eye.fov`, `eye.distance`, `scene.cover`, `scene.depth`) is as it was, and no
  show gains a value on re-save (the corpus round-trips byte for byte). What an older build
  makes of a file this branch writes: a section holding `scene.2` is refused in words
  ("scene node: no key 'instance' (it takes nothing)"), drawn black as any section it cannot
  read; both Macs run one build.

### 9.2 Still open

- **The first eye's orbit** (row 1217). `eye.yaw` / `eye.pitch` would be two new saved ids
  on every show; left out, so the first camera stands where it always stood. A later
  change can add them (a re-save then writes them: a format addition, no rename).
- **The see-through order from another side** (row 1218). The painter sort is the shape's
  own (the 4D `w` of a 4D shape, the default eye's depth of a 3D one), made once — the owner's
  "its sort runs once". Seen from behind, a 3D shape's see-through faces keep the front's
  order. A fractal's walk is cut for the first scene's eye. The rig's box (`world.box`,
  the poi) is the first scene's.
- **The hands' own pictures through a second eye** (row 1218, Devin on #528). Solid hands in
  a scene go through its eye; a hands layer or guide is one picture, made through the first
  eye, so laid over `scene.2` (or depth-composited with `scene.2.depth`) it is from the
  other camera. Which consumer's eye a shared layer takes is still to decide.
- **Hand checks 983–984** on the Mac, and GRAPH's **gpu cost** chip over two scenes.

### 9.3 Built

As §9.1. **The proof:** `tests/test_scenes_numbered.py::test_two_outputs_show_one_tesseract_from_two_angles_posed_once`
— one tesseract seen by `scene` and `scene.2`, each into its own output: two different
pictures, the first the one-scene frame pixel for pixel, the second what the first scene's
eye draws standing at the same orbit, and `Renderer.stats["posed"]` 1 for the frame.

- **The picture.** [`assets/92-phase2/two-cameras.png`](assets/92-phase2/two-cameras.png): one tesseract, posed once, through `eye.*` and `eye.2.*` (yaw 60°, pitch 25°).
- **Tests.** `tests/test_scenes_numbered.py`; the spies on the scene pass in
  `tests/test_render.py`, `test_graph_faces.py` and `test_graph_switch.py` watch
  `draw_posed` (what the graph's shape calls now); `test_patches_frame_kinds.py` expects
  the scene to land as `scene.2`. Hand checks 983, 984.
- **Devin on #528.** A keyed scene's cover masks its own pass (`Cover.of_scene`); a lift or
  spawn never makes a numbered scene the first; GRAPH draws every scene's pins.
- **Restart** after pulling: the renderer's per-scene state and the view's `eyes` are new
  fields on live objects.

Next: phase 3, shape and pattern instances.
