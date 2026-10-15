# Plan 26 — the render graph

The frame is now a **render graph**: nodes with typed ports — geometry
(the shape, the hands, a point cloud), the scene, layers, composites,
the effect chain, the look-back's history and the outputs — evaluated
once a frame in an order settled when the graph is built. The shape and
the hands share **one camera**: a fixed perspective eye (`eye.*`) with a
depth buffer, `camera.zoom` / `camera.pan` the shape's scale and
position in that world, and the Leap's millimetres calibrated into it.
So the hands can be drawn **inside the scene** (in front of or behind
the shape's edges) or as **their own layer** laid over, added or
depth-aware, and the same hands can be in the scene on the projector and
a clean layer on the glass at once. The look-back's history is wiring: it
holds the scene, or the scene with the hands. A preset may say its graph
in **data** — a `graph` section in its JSON: where each hands node goes,
solid or as lines, how its layer is laid on, what the history holds, an
effect more than once in the chain, a second hands node with its own
settings. A recorded **point cloud** listed in the config is drawn in
the same world. Before any of it, **556 golden frames** pin every
factory preset in every output state to the byte, and the SYSTEM page
times every node on the GPU.

Built as stream A of the run in
[`24-26-27-orchestrator-prompt.md`](24-26-27-orchestrator-prompt.md)
(F2 in [`24-party-wishlist.md`](24-party-wishlist.md)). No preset was
edited or added (decision 23): every file under `hyperspace/library/` is
byte-identical, no factory preset carries a `graph` section, and every
proof is a fixture under `tests/fixtures/` loaded through a scratch
library.

Hand checks: [`11-hand-checks.md`](11-hand-checks.md) group V, checks
191–218. Open decisions: [`DECISION-REGISTER.md`](../DECISION-REGISTER.md)
rows 169–209. The owner's decisions for this plan (1–9, 15, the render
parts of 16, and 22–24 of the launch prompt, plus the stroke-space
toggle of 2026-10-14) are in [`DECISIONS.md`](../DECISIONS.md) with Who
"owner". The `[[devices]]` side of the point cloud — the source type,
the file, the `cloud` device — is plan 27's: see
[`27-device-registry.md`](27-device-registry.md).

Branch `plan-24-26-27-integration`, in merge order: A0 (PR #174), A1
(#179), A2 (#183), A3 (#187), A4 (#191), A4b (#190), A2b (#192).

## What was built

### A0 — step 0: golden frames, GPU timing, the naming rule

- **At the machine.** Nothing on screen changes but the SYSTEM page,
  which gained a GPU-time block (one line per node since A1, below). The
  goldens are a developer's tool.
- **Golden frames.** `tools/golden_frames.py` loads every factory preset
  (`preset.FACTORY_PRESETS`, 23) through the real `Presets` into a
  throwaway home, with two synthetic hands (`tests/fake_hands.py`: the
  left open at (−90, 210, 0) mm, the right a fist at (90, 200, 10))
  present or absent through the real `HandsIO`, the ghost on, the LFOs
  and the analyzer at rest (never stepped, never fed), the dream off, the
  preset's own look-back kept, the clock pinned, and draws **8 frames at
  1/60 s at 960×600, dpr 1**. The eight `Switches` states (scene × hands
  × through) are eight outputs of one `draw_outputs` call (output 1 4×
  MSAA like the window); `solo` is output 1 alone (drawn direct), and
  `solo-scene+hands+through` the same for the six presets with an effect
  on; one more frame is party-trip on a 2× HiDPI 1080p screen
  (3840×2160) under the 1080p render cap. A golden is the SHA-256 of the
  full-resolution RGBA frame plus a quarter-size PNG for a person, with
  the route each state reached. `tests/test_golden_frames.py` compares
  every hash exactly on the renderer they were recorded on
  (`GL_RENDERER` "Apple M3 Max", GL_VERSION "4.1 Metal - 90.5") and
  skips with a note anywhere else.
- **GPU timing.** `render.PassTimer`: one `GL_TIME_ELAPSED` query per
  node a frame (queries never nest; a node that runs several times is
  summed), read **3 frames late** (`LAG`) so the CPU never waits, kept as
  a **median over the last 60 frames** (`WINDOW`) in
  `Renderer.stats["gpu_ms"]`; without timer queries, `stats["gpu_note"]`
  says why and the pixels are the same. The SYSTEM page shows "gpu per
  node, ms (median of the last frames):" and one line per node.
- **The naming rule** (`params.instance_id`, `params.instance_of`; in
  [`ENGINEERING.md`](../ENGINEERING.md) §2): the first instance of a node
  keeps today's ids (`fx.acid.mix`, `ghost.alpha`); an extra instance
  carries its number right after the node's prefix (`fx.acid.2.mix`,
  `ghost.2.alpha`). The first segment — the group — never changes, so no
  preset or binding migrates.
- **Code.** `tools/golden_frames.py` (new), `tests/golden/frames/`
  (`frames.json` + `png/`); `render.PassTimer`, `_Timed`,
  `Renderer.timer` / `_pass_timer` / `_timed`; `ui.Panel.gpu_lines`;
  `params.instance_id` / `instance_of`.
- **Tests.** `tests/test_golden_frames.py` (7 today), notably
  `::test_every_golden_frame_is_drawn_byte_for_byte`,
  `::test_every_factory_preset_has_every_state_recorded_and_nothing_else`,
  `::test_each_node_has_a_rolling_median_in_ms`,
  `::test_no_timer_queries_means_a_note_and_the_same_pixels`,
  `::test_the_gpu_lines_on_the_system_page`;
  `tests/test_params.py::test_the_first_instance_keeps_todays_id_and_extras_carry_a_marker`,
  `::test_every_node_param_today_reads_as_its_first_instance`.

### A1 — the graph in code

- **At the machine.** Nothing visible changes: **every one of A0's 427
  goldens was drawn byte for byte** by the graph — evaluating the frame
  in dependency order moved no pixel. The SYSTEM page's lines became one
  per node: `scene`, `cover`, `hands`, `history`, `fx`, `capture`,
  `output.1` for one default output; `output.2` with a second output;
  `composite(scene+hands)` and `fx(scene+hands)` (or `composite(hands)`
  and `fx(hands)`) while an output has hands-through on. A node that
  leaves the graph leaves the list.
- **The graph.** `hyperspace/graph.py` (new, in the render stack: it
  imports `moderngl`, `numpy`, `geometry` and `outputs`, never `params`,
  `routing`, `library`, `preset`, `undo`, `control` or `devices`). The
  owner's four kinds — **Geometry** (`Shape`, `Hands`, `PointCloud`),
  **Scene**, **Layer** (`HandsLayer`, `Readout`, `Cover`), **Composite**
  — and three that wrap what exists: **FX** (`Fx`, over `fx.FxChain`,
  one node per pipeline), **History** (`History` lays the echoes and the
  dream over its input; `Capture` puts its input into the ring after
  every composite of the frame) and **Output** (`Output`, exactly
  `Renderer._compose`, so a later output still gets the five-step
  `outputs.Handoff`). A Scene or Layer *makes* a texture
  (`image(frame)`); History, Composite and FX *paint* into the
  framebuffer their consumer hands them (`paint(frame, dst)`), so the
  look-back composites straight into the chain's half-float input and
  the chain straight into the window, as before; geometries are drawn by
  their scene or layer. The graph refuses a wrong port type, an unknown
  port, a dependency outside the graph and a duplicate name when it is
  built. Node methods are `run`, `paint`, `draw`, `image`, `depth` —
  never `apply`, `modulate`, `snapshot` or `set_value`.
- **Evaluation.** `Graph.order` is dependency order (a depth-first walk,
  dependencies first, ties in insertion order), computed when the graph
  is built, never per frame; `Graph.evaluate` runs each node once.
  `Renderer._draw_frame` is now "settle the frame's size under the cap,
  tick the chain, build or reuse the graph, evaluate it, close the
  timer's frame". `Renderer._graph_for` keeps the last graph and builds a
  new one (`graph.default_graph`) only when its key changes: each view's
  scene / hands / through switches (`graph_key`), the renderer's
  `Wiring` (A3) and the listed clouds (A4b). A pipeline no output takes
  this frame is skipped and its nodes read 0.
- **Code.** `graph.py`: `Frame`, `Node`, `Graph`, `graph_key`,
  `pipelines_of`, `default_graph`, `FX_NAMES`, `COMPOSITE_NAMES`.
  `render.py`: `_draw_frame`, `_graph_for`; `PassTimer` per node
  (`end_frame(names)`); `on_reload` drops the graph and the timer.
  `hotreload.MODULES` gains `graph`. `outputs.py`, `lookback.py`,
  `fx.py`, `ghost.py` needed no change.
- **Tests.** `tests/test_graph.py` (15 today), notably
  `::test_graph_imports_only_the_render_stack_and_names_no_write`,
  `::test_the_default_graph_for_one_default_view_is_todays_frame_in_order`,
  `::test_ports_are_typed_and_the_graph_checks_its_wiring`,
  `::test_order_puts_dependencies_first_and_ties_in_insertion_order`,
  `::test_the_graph_is_built_once_per_set_of_switches_and_reused`,
  `::test_a_pipeline_no_view_routes_to_this_frame_does_not_run`,
  `::test_the_timer_lists_the_graphs_nodes_and_drops_a_node_that_left`.

### A2 — one camera

- **At the machine.** At the defaults the shape lands where it always
  did. **The default eye's largest vertex error against `project_h` is
  2.3e-13 px in float64 and 1.1e-4 px in float32** (the GPU's
  arithmetic), against a bar of 0.5 px, over every shape at the three
  golden views and five window sizes. What changes: `camera.zoom` grows
  the shape **in the world** (its own perspective — a big zoom is
  deeper), and a field of copies is copies in the world; `camera.pan` is
  in shape radii (CAMERA shows `+0.59`, not `+190 px`) and an old
  preset's pixel pan lands where it did on the 1080p projector; the
  CAMERA page has an **eye** section ("the room's camera, not the
  preset's"); `hands.json` is `hyperspace.hands/3` and keeps the old file
  as `hands.json.bak-v2`. The whole-frame 2D zoom is gone.
- **The transform.** The CPU still takes the shape to 3D
  (`geometry.world_points`: the six-plane 4D tumble `rot.*`, the 4D
  divide, the `camera.yaw` / `camera.pitch` turntable — the shape's
  world pose, ids unchanged); the vertex shaders take it to the clip
  through `u_model` (`geometry.model_matrix`: `camera.zoom` a scale about
  the world origin, then `camera.pan`) and `u_vp` (`geometry.eye_matrix`,
  the eye). Edges and points are quads expanded in the vertex shader
  from 3D ends, so they carry a real depth; an edge end behind the eye is
  slid to just in front of it (`EYE_W`). `SceneTarget` has a depth
  attachment; the see-through shape is still painter-sorted and never
  depth-tested against itself, and its visible surface (alpha above
  `render.DEPTH_ALPHA` = 0.25) is written to depth after its colour
  (`Renderer._depth_pass`). A point's quad is a whole number of pixels
  across.
- **The eye.** `eye.fov` 47.6° (`geometry.EYE_FOV`, across the shorter
  side) and `eye.distance` 3.78 shape radii (`EYE_DISTANCE` = CAM3 / 0.9),
  ranges 10–120° and 1.5–40; group `eye`, a session group (no preset
  moves it); not modulatable.
- **Pan.** World units, ±12 (`params.PAN_RANGE`), y positive down the
  screen as it always was. A document without `"units": {"camera.pan":
  "world"}` stored logical px and is divided by `geometry.PAN_REF_PX` =
  324 (the default eye's px per unit at 1080p) at load — presets, camera
  module presets and `camera/default.json` alike (`params.pan_world`);
  every save writes the marker. The schema stays `hyperspace.preset/2`.
- **The Leap calibration.** `hands.core.Units(mm, origin, tilt)` in
  `hands.json`: `"units": {"mm": null, "origin": null, "tilt": 32.0}`,
  "from the box" by default; a `/2` file is kept as `hands.json.bak-v2`
  by the first save. Nothing drew the hands through it until A3.
- **Code.** `geometry.py`: `SCALE`, `EYE_*`, `PAN_REF_PX`,
  `world_points`, `model_matrix`, `eye_matrix`, `eye_project`,
  `px_per_unit`, `pan_px_to_world` (`project` / `project_h` untouched:
  the parity oracle). `render.py`: the scene shaders, `EYE_W`,
  `DEPTH_ALPHA`, `CELL`, `SceneTarget` depth, `draw_scene` rewritten,
  `_depth_pass`. `view.py`: `eye_fov`, `eye_distance`. `params.py`:
  `PAN_RANGE`, `EYE_*_RANGE`, `pan_world`, `UNITS`. `preset.py` (load
  step 0, the marker on save), `library.py` (camera modules).
  `hands/core.py`: `CAL_SCHEMA` /3, `Units`. `ghost.py`: `calibration`,
  `shared_camera`. `app.py`: the mouse's pan and zoom-about-the-cursor in
  world units. `ui.py`: the CAMERA page's eye section.
- **Tests.** `tests/test_camera.py` (28 today), notably
  `::test_the_default_eye_lands_every_vertex_within_half_a_pixel_of_project_h`,
  `::test_each_point_is_drawn_where_project_h_puts_it`,
  `::test_zoom_scales_the_shape_about_the_world_origin_and_pan_moves_it`,
  `::test_the_pan_range_keeps_a_routed_pan_as_far_as_it_was`,
  `::test_a_preset_2_pan_in_px_is_read_in_world_units`,
  `::test_a_saved_preset_says_its_pan_is_in_world_units_and_loads_as_saved`,
  `::test_an_old_camera_module_loads_at_its_converted_pan`,
  `::test_the_shapes_depth_is_its_nearest_visible_surface`,
  `::test_units_round_trip_through_hands_json`. One boundary assertion
  changed on purpose:
  `tests/test_app_boundary.py::test_mouse_orbits_pans_and_zooms_on_the_base`
  (the drag pans by px / px-per-unit).

### A2b — strokes in world space or screen space (the owner's toggle)

- **At the machine.** The owner looked at A2's zoomed-out looks (dots
  2–2.5× bigger, heavier edges, because A2 stopped scaling strokes with
  the zoom) and asked on 2026-10-14 for a switch, with the old feel as
  the default. **Screen strokes** on the VIEW page (under the lines and
  points opacities) rests **unticked: world space** — the edges' width
  and the dots' radius are × `camera.zoom` again, the pre-A2 formula, so
  strokes grow and shrink with the shape and the zoomed-out factory looks
  (ember-orbit, hex-engine, party-field) have their old weight. Ticked:
  A2's screen space, the same pixel weight whatever the zoom. At
  `camera.zoom = 1` both draw the same frame byte for byte. The shape's
  strokes only: the hands' tubes are world-sized and never follow the
  zoom, and A4's hand lines are always one pixel.
- **Code.** `view.screen_strokes` (`ViewState.screen_strokes = False`;
  group `view`, a performance switch, modulatable);
  `render.draw_scene`'s one line `sz = 1.0 if screen_strokes else zoom`
  applied to the width before the 1 px floor and to the radius before the
  whole-pixel rounding; the VIEW page's checkbox;
  `learn.cannot_show` calls it dead while both points and lines are off.
- **Tests.** `tests/test_stroke_space.py` (7), notably
  `::test_the_default_is_world_space_a_preset_performance_switch`,
  `::test_at_zoom_1_both_modes_draw_the_same_frame`,
  `::test_world_space_scales_the_width_and_radius_by_the_zoom`;
  `tests/test_camera.py::test_strokes_keep_their_weight_whatever_the_zoom`
  now draws with the switch on.

### A3 — the hands as a geometry node

- **At the machine.** Nothing switchable changes from the app's pages
  (a preset's graph selects the new wirings, A4). The ghost hands now
  draw through the shape's eye: about where and as big as they were
  (≤ 4 px at 960×600, ≤ 9 px at 1080p, against the old ghost camera)
  with the eye's slightly stronger perspective (47.6° across the shorter
  side, where the ghost camera had 38° vertical, refitted per output).
  Every frame without a hand showing is byte-identical to A2's.
- **The hands node.** `graph.Hands` (named `ghost`, the `ghost.*`
  params' node): `Ghost`'s five styles in the shared camera
  (`ghost.shared_camera`: the eye and the calibration, whose box is now
  fitted into a 16:9 picture, `ghost.CAL_ASPECT`), its poses settled once
  a frame (`Ghost.settle`) for every draw of them. It feeds the hands'
  layer (`HandsLayer`, named `hands`, its own colour and depth target),
  the scene, or both.
- **In the scene** (`Wiring(hands="scene")`): the scene clears, draws the
  solid geometry first (the hands, depth written), then the see-through
  shape painter-sorted and depth-tested against them, so a hand in front
  of the shape hides it and the shape's strokes and fills lie over a hand
  behind. Hands inside the scene are solid: `ghost.alpha` does not apply
  there (at exactly 0 it removes them everywhere). The guide and the
  tethers never go into the scene: the readout is laid on at the outputs
  (`Readout`, `readout`).
- **As a layer, composited anywhere.** `Composite` lays its `over` image
  on its `under` — **over**, **add** or **depth-aware** (a layer texel
  is dropped where the scene's visible surface is nearer by more than
  `render.LAYER_DEPTH_BIAS` = 0.05 shape radii). Today's "through" is the
  layer composited onto the history before the effects; "over" is the
  layer laid on at the output.
- **The OUTPUT switches are the default graph's wiring**: each output's
  `scene` / `hands` / `through` pick which pipeline end feeds its
  `image` port and whether the layer is laid over it. `outputs.route`'s
  per-frame collapse (no effect on, or no hand drawn: through is over)
  is wiring too — a through pipeline "stands down" for its fallback
  (`Fx.fallback`, `Output.settle`); the golden tool asserts the graph's
  settled route equals `outputs.route` for every default state.
- **The history is wiring**: `Wiring(history="scene")` (the default:
  the capture takes the scene) or `"scene+hands"` (the capture takes the
  hands' layer laid on the scene, `composite(history)`; with the hands in
  the scene, the scene already holds them).
- **`Wiring`** (`hands` layer / scene, `blend` over / add / depth,
  `history` scene / scene+hands; A4 adds `draw` and `extra`) is held by
  `Renderer.wiring`; its default is today's frame. Nothing in the app
  sets it but a preset's graph section (A4).
- **Code.** `graph.py`: `Wiring`, `Hands`, `Scene` (any number of
  geometries, solid first, its own clear), `HandsLayer`, `Readout`,
  `Composite` (`blend`, a `depth` port), `Fx.fallback` / `bent`,
  `Output.settle`, `default_graph(views, wiring)`. `ghost.py`:
  `CAL_ASPECT`, `calibration(…, aspect)`, `Ghost.settle`, `draw_solid`,
  `depth`. `render.py`: `LAYER_FS`, `LAYER_DEPTH_BIAS`,
  `SceneTarget.depth_texture` (resolved lazily), `Renderer.wiring`,
  `lay`. `outputs.py`: `Handoff.blend` ("add" reaches a presenter).
- **Tests.** `tests/test_hands_node.py` (14), notably
  `::test_the_default_calibration_puts_the_hands_where_the_ghost_camera_did`,
  `::test_hands_in_the_scene_are_solid_and_in_front_of_or_behind_the_shape`,
  `::test_the_scene_holds_the_hands_so_the_effects_bend_them_and_the_history_keeps_them`,
  `::test_the_guide_never_rides_the_scene`,
  `::test_a_depth_aware_layer_goes_behind_the_shape`,
  `::test_the_hands_have_their_own_line_when_the_scene_draws_them`;
  `tests/test_graph.py::test_the_hands_in_the_scene_are_its_first_geometry_and_a_glass_still_gets_the_layer`,
  `::test_the_history_is_wired_to_the_scene_or_the_scene_with_the_hands`.
  The two history tests the prompt allowed were rewritten:
  `tests/test_outputs.py::test_the_history_holds_what_it_is_wired_to_and_the_default_graph_wires_it_as_today`
  and
  `tests/test_render.py::test_the_default_graphs_history_holds_what_todays_does_never_the_dim`.

### A4 — the graph in the preset

- **At the machine.** Nothing a factory preset does changes. A preset
  written by hand (or a fixture copied into a scratch library) may carry
  a `graph` section: the hands inside the scene, solid or as lines; the
  hands' layer laid over, added or depth-aware; the history holding the
  hands; an effect more than once in the chain; a second hands node with
  its own settings on the outputs without the scene. The OUTPUT page's
  "shows:" line and the LOOKBACK page say the wiring in words; the
  OUTPUT page's hover gives the loaded graph in one line
  (`graph: hands 1 in the scene as lines · history with the hands`).
  The existing switches still set the default graph's wiring; there is
  no editor (plan 28).
- **The graph JSON** (`graph.GraphSpec`, `graph.read_graph`,
  `preset.GraphSection`). A list of the nodes that differ from the
  default graph, one object per node, before `values` in the file, one
  node per line:

  ```json
  "graph": {"nodes": [
   {"kind": "hands", "into": "scene", "draw": "lines"},
   {"kind": "history", "holds": "scene+hands"}
  ]}
  ```

  That is the proof preset,
  [`tests/fixtures/presets/hands-lines.json`](../../tests/fixtures/presets/hands-lines.json)
  (a fixture, never a factory preset): the hands drawn in the scene as
  lines, through the acid effect (`fx.acid.on` in its `values`), with the
  look-back wired to hold them — party-tracer's look with party-acid's
  acid. The kinds (`graph.NODE_KINDS`, the one place a kind is named):

  | Kind | Keys | Default (left out) |
  |---|---|---|
  | `hands` | `instance` (1, or 2 …), `into` (`layer` / `scene`), `draw` (`solid` / `lines`), `laid` (`over` / `add` / `depth`, only on the node that makes the layer) | hands 1, a solid layer laid over |
  | `effect` | `file` (an effect file's name), `instance` (2 or more) | every effect file once |
  | `history` | `holds` (`scene` / `scene+hands`) | the scene |

  A node left out is the default one, so no section and `{"nodes": []}`
  are both the default graph, and a save writes the section back in a
  fixed order (hands by instance, effects by file and instance, the
  history). Nothing that is a param goes in it: an effect's on, mix and
  order, `ghost.*`, `dream.*` stay in `values` or the show. A section
  this build cannot read — an unknown kind, a key a node does not take,
  a value out of its choices, two nodes of one instance, two layers —
  is a note on the preset strip ("graph: unknown node kind 'teapot'
  (this build knows effect, hands, history); the default graph"), the
  values, routes and desk land as ever, and the section is kept as the
  file had it and written back on save. **A `cloud` kind is such an
  unknown kind**: clouds follow the device list, not the preset's graph
  (the orchestrator's ruling; plan 28 may add the kind).
- **Node instances.** A second acid is the effect named `acid.2` in
  `FxState` (`set_instances`), its params `fx.acid.2.*` ("Acid 2 mix"),
  performance params a preset's `values` carry, its own clock and order,
  on the file's one compiled program. A second hands node is `ghost.2`
  with `ghost.2.on/alpha/mirror/guide/tethers/style` (session params,
  like `ghost.*`), its own `Ghost` (`Renderer.ghost_of`), its layer
  `hands.2` and its lone readout `readout.2`. `ghost.2.on` starts off
  (decision 24). A show holds `ghost.<n>.*` back until a preset's graph
  declares the node, then seeds it, so the glass comes up as saved.
  `fx.parse` refuses a purely decimal `@param` key and `FxState.load` an
  effect file named like an instance (`acid.2.glsl`).
- **Where two hands nodes go.** Every `into: "scene"` node is in the
  scene; the `into: "layer"` node (else the first) is the layer, laid on
  every output whose hands switch is on and whose scene does not hold
  hands. So `ghost` in the scene and `ghost.2` the layer: the projector
  (scene + hands) shows `ghost` in its scene, the glass (scene off, hands
  on) shows `ghost.2`'s own picture.
- **Hands as lines.** `draw: "lines"` draws the style's own meshes as
  their triangles' edges (`ctx.wireframe`), one pixel wide; the guide
  stays solid.
- **Undo.** `library.Marks` carries the graph: undoing the load of a
  preset with a second acid removes `fx.acid.2.*`, redo brings them back.
- **Code.** `graph.py`: `HandsAt`, `EffectAt`, `HistoryAt`, `GraphError`,
  `NODE_KINDS`, `GraphSpec` (`wiring`, `effect_counts`, `to_json`),
  `read_graph`, `hands_words` / `layer_words` / `history_words` /
  `graph_words`, `Wiring.draw` / `extra`, `Graph.timed` by the consumer
  edge. `preset.py`: `GRAPH_KEY`, `GraphSection`, `load_doc` steps 0 / 1 /
  1½, `document`, `signature`, `dumps`. `fx.py`: `set_instances`,
  `instance_of_name`. `ghost.py`: `prefix`, `register(…, n)`,
  `Geometry.draw(lines=)`. `render.py`: `ghost_states`, `ghost_of`,
  `drop_ghosts`. `library.py`: `Marks`, `Project._held_back`. `ui.py`:
  `output_shows(…, wiring)`; `ui_lookback.history_line`.
  `tools/golden_frames.py`: `FIXTURE_PRESETS`.
- **Tests.** `tests/test_graph_json.py` (41), notably
  `::test_a_graph_section_reads_and_writes_itself_plainly`,
  `::test_the_proof_preset_loads_its_graph_from_a_scratch_library`,
  `::test_an_unknown_node_kind_is_a_note_and_the_default_graph`,
  `::test_no_factory_preset_carries_a_graph_and_each_loads_as_before`,
  `::test_a_second_acid_is_its_own_params_clock_and_place_in_the_chain`,
  `::test_two_acids_run_in_one_chain_on_one_program`,
  `::test_two_hands_nodes_one_in_the_scene_one_over_the_glass`,
  `::test_a_second_hands_nodes_settings_survive_reopening_the_show`,
  `::test_undoing_a_load_puts_the_graph_back_before_the_values`,
  `::test_hands_as_lines_draw_their_edges`, `::test_the_wiring_in_words`.

### A4b — the point-cloud geometry node

- **At the machine.** Nothing changes unless `config.toml` lists a
  `cloud` device (plan 27's block, in
  [`27-device-registry.md`](27-device-registry.md) "The block to
  paste"). With one listed, the scene shows the recording's points as
  solid round dots in the shape's world — the fixture knot at about the
  shape's size, threaded through it, playing at the file's 12 fps — and
  the SYSTEM page gains a `cloud` line above `scene`.
- **The node.** `graph.PointCloud` (kind `cloud`, `SOLID`): the latest
  frame of `cloud:<role>` (`DeviceRegistry.clouds`) as one instanced
  quad per point through the eye (A2's point expansion), a hard round
  dot, alpha 1, depth tested and written — drawn with the hands, before
  the see-through shape. Its world transform is a uniform scale about the
  world origin (`cloud.scale`); the shape's `camera.*` and `rot.*` do not
  move it, the eye does. The buffer is uploaded only when the cloud's
  (frame id, publish time) moves. A listed device whose file is missing
  keeps its node, which draws nothing.
- **How it gets in.** `app.main` hands the renderer the device registry
  (`renderer.cloud_source = rig`, one line); `graph.cloud_roles` reads
  the roles of the listed `cloud` devices (duck-typed: `graph.py` never
  imports `devices`), and `default_graph(…, clouds)` adds one node per
  role (`cloud`, `cloud.2` …) as the scene's first geometries. With no
  `cloud` entry the graph is the one before, node for node.
- **The look.** `cloud.size` (radius, logical px, 0.5–12, default 2),
  `cloud.scale` (0.01–10, default 0.3), `cloud.bright` (0–2, default 1),
  `cloud.colors` (the source's colours, default on): group `cloud`, a
  session group. No panel row yet: Learn and ROUTING reach them.
- **Code.** `graph.py`'s point-cloud block (`CLOUD_KIND`, `CLOUD_VS` /
  `CLOUD_FS`, `cloud_roles`, `_CloudGL`, `PointCloud`, `cloud_nodes`),
  `Graph.clouds`; `render.py`: `Renderer.cloud_source`, `_graph_for`'s
  key, `on_reload`; `params.py` / `view.py`: the four `cloud.*`.
- **Tests.** `tests/test_cloud_node.py` (9), notably
  `::test_a_listed_cloud_is_the_scenes_first_geometry_and_none_listed_changes_nothing`,
  `::test_the_node_draws_the_fixtures_points_where_the_shared_camera_puts_them`,
  `::test_a_point_in_front_of_the_shape_hides_it_and_one_behind_is_hidden`,
  `::test_a_missing_cloud_draws_nothing_and_raises_nothing`,
  `::test_the_buffer_is_uploaded_only_when_the_frame_id_moves`,
  `::test_the_per_node_timer_names_the_cloud`.

## The goldens

**556 goldens, 130 distinct pictures**, recorded on "Apple M3 Max"
(GL_VERSION "4.1 Metal - 90.5"), in `tests/golden/frames/frames.json`
with one PNG per distinct picture under `png/`:

| Set | Count | Recorded by |
|---|---|---|
| 23 factory presets × hands absent / present × the eight states, at 960×600 | 368 | A0 |
| `solo` (output 1 alone, the default state) × 23 × 2 | 46 | A0 |
| `solo-scene+hands+through` × the six presets with an effect on × 2 | 12 | A0 |
| party-trip at 3840×2160 (2×, 1080p logical) under the 1080p cap | 1 | A0 |
| `in-scene/…` (3 states) and `depth/…` (2 states) × 23, hands present | 115 | A3 |
| `history+hands/scene+hands` for party-wake and party-tracer | 2 | A3 |
| the fixture `hands-lines`, hands present, the eight states | 8 | A4 |
| `cloud/scene`, `cloud/scene+hands` for legacy6 and party-faces | 4 | A4b |

So A0 recorded 427, A3 brought the total to 544, A4 to 552 and A4b to
556. Far fewer pictures than goldens are distinct by design: with hands
absent the hands and through switches change nothing, with no effect on
through is over, and every state with no scene and no hand is the same
black ground.

**What moved, and why.** Only three WPs re-recorded existing frames,
each for one named reason; every other merge after A0's recording — A1,
A4, A4b, and stream B's and C's (C2's opacities, B4 among them) — drew
every golden byte for byte. (C6's palette merged into the integration
branch just before A0 did, and A0's goldens held there: at mix 0 it moves
none.)

- **A2: 184 of 427** — `camera.zoom` as the shape's world scale (its own
  perspective), copies in the world (ember-orbit, hex-engine,
  party-field), party-mandala's 190 px pan converted through the 1080p
  reference (105 px at the goldens' 960×600), and float32 face positions
  (sub-pixel shimmer on patterned faces seen edge-on: party-noita,
  party-faces, hex-engine). Only states that show the scene moved; every
  zoom-1 / pan-0 / one-copy preset without faces stayed byte-identical.
  Nothing moved for "depth-tested overlap": the see-through shape is
  never depth-tested against itself. Sheet:
  [`a2-moved.png`](assets/26-render-graph/a2-moved.png) (each moved
  preset's solo frame with hands: before | after | difference ×4; its
  "after" strokes are A2's screen space, which A2b then reversed by
  default).
- **A3: 122 of 427** (of A2's), one reason: the hands now draw through
  the shared camera — the eye's 47.6° across the shorter side and the
  16:9 calibration — instead of the ghost camera's 38° vertical refitted
  per output. Every frame where a hand shows: 23 × hands present ×
  {`scene+hands`, `scene+hands+through`, `hands`, `hands+through`,
  `solo`}, the six `solo-scene+hands+through`, and the cap frame. The
  launch prompt said A3's default graphs must match A2's recordings
  exactly; the orchestrator sanctioned this one move for the one camera
  reason (A2 had shown no similarity calibration can turn one
  perspective into the other) — every frame without a hand (305) did
  match. Sheet: [`a3-hands-moved.png`](assets/26-render-graph/a3-hands-moved.png)
  (each preset's solo: A2 | A3 | difference ×4).
- **A2b: 218 of 556** — strokes back in world space by default (the
  owner's decision, 2026-10-14): every scene-showing state of the 15
  factory presets at zoom ≠ 1 with lines or points on, hands-orbit with
  the hands present (its zoom route), and — after A4 and A4b merged —
  the fixture hands-lines' 4 scene frames (zoom 0.9) and party-faces' 2
  cloud frames (zoom 1.1: the shape's edges among the points; the cloud's
  own points never scale). That is 212 at A2b's first recording plus 6
  after the merge. No zoom-1 frame moved. Sheet:
  [`a2b-moved.png`](assets/26-render-graph/a2b-moved.png).

**How to re-record.** Only on the Mac the gates run on (`GL_RENDERER`
"Apple M3 Max"); anywhere else the test skips and the tool refuses to
diff.

```bash
uv run python tools/golden_frames.py                          # diff: "all 556 frames match their goldens (…)"
uv run python tools/golden_frames.py --only party-trip,legacy6 # diff those presets only
uv run python tools/golden_frames.py --record                 # re-record every golden
uv run python tools/golden_frames.py --only party-trip --record   # re-record those, keep the rest
```

A diff that finds moved frames lists each (`MOVED <preset>|<hands>|<state>`)
and writes a contact sheet (golden | now | difference ×4) to
`docs/plans/assets/26-render-graph/golden-diff-<presets or all>.png`.
The tool never reads or writes `~/Hyperspace`. Re-record only what a
change moved, say so in the commit, and list each changed frame in the
PR with its one reason; a golden that moves for a change that should
move nothing means the change is wrong. The tool's own sheet of a big
move runs to 13–14 MB: commit a compact one instead, as A2, A3 and A2b
did. A new GL_VERSION on the same renderer prints a note naming both.

## Not verified by a person

Everything visible. Every proof is headless: the goldens, the tests,
and three smoke runs (A1 120 frames; A4 240 frames with the fixture as
a show's startup preset and a synthetic tape, read back by a probe —
wire hands inside the shape, bent by the acid, with tracers; A4b 240
frames with the recorded cloud, 96 → 144 points over the knot's frames,
the `cloud` line at about 0 ms). No screenshot of the live window was
possible (macOS refused screen recording to the shell). In particular:

- **Every factory preset by eye on the Mac** against its golden (192):
  the goldens prove the pixels on the gate Mac's GL, not that they look
  right.
- **The SYSTEM page's per-node lines** in the live app (194, 210, 218).
- **Real hands through the shared camera** — size, place, the 47.6°
  perspective, a hand between the shape's edges, the projector and the
  glass at once (203–207): every hands picture is the synthetic pose or
  tape.
- **The zoom's feel** in world space and screen space, and the restored
  stroke weight (197, 198).
- **An old preset's pan** on the real 1080p projector (201).
- **The wire hands, two hands nodes on two real outputs, the words on
  the pages** at the control window's size (211–215).
- **The point cloud** on the real window and projector (216–218).

## Known rough edges

- **The graph section is wiring choices for the default graph, not a
  graph.** The outputs stay the session's switches, so a preset cannot
  say which output gets which hands node; at most one hands node makes
  the layer; a through pipeline that "stands down" per frame is a wire
  sometimes not taken. Plan 28's editor needs outputs as nodes, a wire
  list, several layers and per-output choice (A4's decisions file lists
  them).
- **Hands inside the scene ignore `ghost.alpha`** (solid; 0 removes them
  everywhere); a fading hand writes depth for its 0.3 s fade-out; with
  the look-back on, in-scene hands echo and a held hand saturates
  towards white. With the hands in the scene, an output's hands switch
  cannot remove them from that output's scene.
- **The depth-aware boundary is aliased** (one depth sample of four at a
  silhouette: a 1 px stair-step, a 1 px rim behind the shape); a
  presenter output lays a depth-aware layer plain over (the depths stay
  in output 1's context; "add" does reach it).
- **The 16:9 calibration crops a portrait or square output's box** at
  the sides; the hands are a touch more foreshortened than under the old
  camera.
- **A pan converts exactly only on 1080p**: on the laptop window an old
  preset's pan sits proportionally nearer the centre (party-mandala's
  190 px is 105 px at 960×600). Off-centre, the shape is seen slightly
  from the side.
- **World-space strokes at a big zoom are fat**, and zoomed far out the
  far edges fold into alpha (as on `main`); a flip of Screen strokes
  under a lane jumps the weight in one frame; at zoom 1 the switch shows
  nothing.
- **Past zoom ≈ 3.8 the eye is inside the shape** (strokes behind the eye
  are slid or dropped). Moving `eye.*` off its defaults moves the whole
  picture; no golden covers it.
- **The depth pass re-draws** edges, points and bright fills for depth
  (measured within run-to-run noise on the M3 Max).
- **Hands as lines are a dense hatching** of the capsules' triangles,
  one pixel whatever the dpr (thin on a 2× screen) — not a skeleton of
  bone lines; the owner judges (214).
- **`ghost.2.*` have no page of their own** (ROUTING, Learn and the desk
  reach them); `ghost.2.on` starts off; an `fx` module preset saved with
  a second acid holds `fx.acid.2.*`, unknown where the graph has one acid.
- **A section that fell back** is not marked dirty and saves back
  unread; the note is the only sign. A refused load still pushes a no-op
  undo step.
- **The point cloud:** hard-edged dots of one pixel size at any depth; a
  scale-only world transform (a sensor's cloud centred away from its
  origin sits off-centre until plan 29 calibrates it); only `kind =
  "cloud"` devices are found; a second cloud node shares `cloud.*`; no
  panel row; an unlisted node's buffers are kept until a reload;
  `stats["cloud_error"]` is on no page.
- **The goldens prove pixels only on "Apple M3 Max"**; lfo-breathe's
  golden is its bases (the LFOs at rest); one synthetic pose per preset.
  Tiny nodes can read 0.00 ms on Apple's driver; the times are GPU time,
  not the CPU's.
- **The modulation graph is not evaluated in dependency order**: the
  one-frame lag of ARCHITECTURE §2 stands, untouched by this plan (plan
  28's).
- **What the launch prompt asked for that was built otherwise.** The
  per-pass GPU text is one line per node under a heading, not one
  dot-separated line. The goldens feed full fake-hand frames (features
  and skeletons) through `HandsIO`, not `preset_shots`' feature dicts,
  so the hands both drive the routes and draw. Nothing moved for
  "depth-tested overlap", and no preset schema bump (a `units` key marks
  the pan). "Line width no longer scaling with zoom" is now the
  non-default Screen strokes (the owner's toggle). A3 moved 122 frames
  the prompt said must not move (above). The point-cloud node is its own
  WP (A4b), and a `cloud` kind is not in the graph JSON. The OUTPUT
  page's wiring words ride its existing "shows:" line (a line per output
  overflowed the window with four outputs); the pages show the wiring,
  they do not pick it. The renderer's hand-over is
  `Renderer.cloud_source`, not `clouds`.
