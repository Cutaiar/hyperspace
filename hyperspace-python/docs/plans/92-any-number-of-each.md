# Plan 92 — any number of scenes, shapes, backdrops and patterns

**A design, not a build** (2026-11-28). Nothing here is built. Tags: **[V]** read in the
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

**Params.** `params.instance_id` for each kind's params: `rot.2.rate.xy`,
`view.2.<key>` … — or, cleaner, a prefix per kind for n ≥ 2 (`shape.2.*`, `pattern.2.*`,
`backdrop.2.alpha`), with the first keeping its old ids by alias. [Rec: the per-kind prefix;
see Q2.] Declared and dropped as the frame names them (`params.declare_delays`'s shape),
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
