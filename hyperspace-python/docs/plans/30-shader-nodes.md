# Plan 30 — shader nodes: every effect an image node, the palette anywhere

Every effect file is now an **image node** in the render graph: bitmap
in, bitmap out, one node per effect instance. The effect chain is no
longer one block inside a single `Fx` node: each pipeline is a **run of
effect nodes** in the stack's order, ending in a thin pipeline-end node
that keeps the old end's jobs. An effect that is off is read through:
no pass, no texture. A preset's `graph` section may **place** an effect
on any image edge by name: `after` a node (every consumer of that
node's picture reads the effect) or `into` one (that node's `image`
input alone). So the palette can fold the hands' layer only, or one
output only, or the scene before the history and the dream. The FX page
shows a placed effect's chip apart from the chain with where it sits.
SYSTEM times each effect that ran. A fourth port type, `VALUE`, is
declared for the palette's lights-out and camera-in ports, which are
designed and not built. **Every one of the 556 goldens recorded before
this plan matched unchanged** after each WP; D1 added 24 for its three
fixtures (580).

Built as stream D of the run in
[`28-30-orchestrator-prompt.md`](28-30-orchestrator-prompt.md), from the
design agreed with the owner on 2026-10-16 (the wishlist's palette
"sync", [`24-party-wishlist.md`](24-party-wishlist.md)). No preset was
edited or added (decision 4): every file under `hyperspace/library/` is
byte-identical, no factory preset carries a placement, and every proof
is a fixture under `tests/fixtures/presets/` loaded through a scratch
library.

Hand checks: [`11-hand-checks.md`](11-hand-checks.md) group X, checks
220–231. Open decisions: [`DECISION-REGISTER.md`](../DECISION-REGISTER.md)
rows 214–232. The owner's decisions for this plan (1–5 of the launch
prompt and the render parts of 16) are in [`DECISIONS.md`](../DECISIONS.md)
with Who "owner".

Branch `plan-28-30-integration`, in merge order: D0 (PR #208), D1
(#213), D2 (#216), D3 (this file). Stream N (plan 28,
[`28-node-editor.md`](28-node-editor.md)) merged on the same branch in
between; its GRAPH page draws the effect nodes and the placed ones as
any render node.

## What the owner wants (2026-10-16)

> For shaders, and generally the effects tab we have now, there has to
> be a concept of a **shader node** in this graph. You need to be able
> to have **multiple instances** of these shader nodes. You need to be
> able to apply them **anywhere it makes sense**. What I don't want is
> one single point in the render graph that contains all the shaders
> and is not flexible beyond that. You need to be able to apply these
> things basically anywhere there are **bitmap-in, bitmap-out**
> exchanges between nodes.

## What was built

### D0 — the effect node, and the chain as a run of them

- **At the machine.** Nothing on screen changes but the SYSTEM page: the
  one `fx` time is now **a line per effect that ran this frame**
  (`acid`, `wobble`, `deconverge`, `huecycle` on PARTY-ACID), above the
  end's own `fx` line, which reads 0.00 by design (the end runs no pass
  of its own; the effects' cost is on their lines). With the hands
  through and two pipelines running, `acid(scene+hands)` and
  `acid(hands)` appear too. Switching an effect on or off rebuilds
  nothing; its line comes or goes within a few frames.
- **The effect node.** `graph.Effect(name, *, image=None, node=None)`:
  kind `effect`, one `IMAGE` port in, `IMAGE` out. `effect` is the
  instance's name as `FxState` knows it (`acid`, `acid.2`, `palette`);
  its params are the existing `fx.<effect>.*`; its program and uniforms
  come from `FxChain` as before, so hot reload is untouched. Whether it
  runs is asked once a frame (`Effect.on`): in the frame chain's
  `FxState.chain(FRAME)` this frame and compiled (`FxChain.ready`).
  - **Off** (switched off, mix 0, the stack bypassed, aimed at the
    faces, or a file that never compiled): `paint` paints its input
    straight into its consumer's framebuffer and `image` is its input's.
    No pass, no texture.
  - **On:** it paints its input into a texture of the effects' pool
    (`graph._spare`) and runs `FxChain.run_one` from there into its
    consumer's framebuffer, under `frame.timed(name)`, and records
    itself in `frame.stats["effects"]`.
  - **Read by more than one node** (`Graph.readers`): made once into a
    pool texture held for the frame and shown 1:1 into each reader
    (`Effect._make(frame, avoid=dst)`: never the consumer's own target).
  - `run` does nothing in the chain: the pass runs when its consumer
    pulls it.
- **The chain is a run.** `default_graph(views, wiring, clouds,
  effects)` builds, in place of each old `Fx` block, one `Effect` per
  instance in `FxState.names()` (every instance in the stack's order, on
  or off, whatever its target) between the pipeline's source (the
  history, or the composite laying the hands on) and its end. Node
  names (`graph.effect_node_name`): the effect's own in the scene's
  pipeline (`acid`, `acid.2`, `palette`: the word a placement names),
  the pipeline's suffix in the others (`acid(scene+hands)`,
  `acid(hands)`); a name another node has (`scene`, `capture`,
  `output.2`, the ends' `fx…`) takes the params' prefix (`fx.scene`,
  `fx.fx(scene+hands)`).
- **The pipeline end keeps its class name, `Fx`.** Its input is the last
  effect of its run; `Fx.effects`, `source`, `layer` and `bent` walk
  back through the run; `paint` moves the effects' clocks once a frame
  (`FxState.advance_to`), paints its input and counts
  `stats["chain_runs"]`; `run` keeps every job it had: straight into the
  one output at the frame's size, unflipped, on this context, else once
  into the pipeline's frame texture; a through pipeline standing down to
  its fallback (`Output.settle` reads the composite through
  `end.source`); a raise marks its views.
- **The pool.** `FxChain.pool(size, n)` hands out the chain's half-float
  textures (as `begin` made them); `begin`, which the faces' chain still
  uses with `FxChain.run`, hands out the pool's first framebuffer, asking for at least the textures it already holds (two at the least). `Graph.pool` is 0 with
  no effect node, else 2 plus one per held texture. A straight run
  alternates the two however long it is. A new graph that needs fewer
  releases the pool (`FxChain.fit_pool`); a size change makes all of
  them again.
- **Rebuilds.** `Renderer._graph_for`'s key gains `FxState.names()`: an
  order, an instance or a file changed rebuilds the graph, a toggle does
  not. A new graph fits the pool. The timer is handed
  `Graph.timed_in(frame)`: the timed nodes plus the effects that ran
  (`Effect.TIMED` is False, so `Graph.timed` and the golden manifest's
  `nodes` lists are as before).
- **Measured** (party-acid, headless, 1920×1080, 4× MSAA, 180 frames,
  three rounds). The old `fx` line's median was 0.225 ms; the new
  per-effect lines sum to 0.089 ms (acid 0.003–0.026, wobble
  0.001–0.015, deconverge 0–0.005, huecycle 0.055–0.093; the end `fx` 0).
  Frame wall time 1.69 ms before, 1.76 after: within noise. The review
  pass measured again, base tree against the head (three alternating
  rounds): the old line 0.225 ms, the effects' lines summing to 0.078 ms;
  the frame's wall time 1.34 → 1.44 ms median, about +0.1 ms, inside the
  base's spread but higher in two rounds of three.
  `run_one` ran exactly 4.0 times a frame (the four on effects); the
  nine off effects ran 0 passes. On Apple's tile GPU a query is charged
  for whatever is flushed inside it, so the split is indicative.
- **Code.** `graph.py`: `Effect`, `Fx` (rewritten as the end),
  `effect_node_name`, `_chain_now`, `_spare`, `Graph.readers` / `pool` /
  `effects` / `timed_in`, `default_graph(…, effects)`. `fx.py`:
  `FxChain.pool`, `fit_pool`, `ready`, `run_one`, `_uniforms` /
  `_opaque` (shared with `run`). `render.py`: `_graph_for`'s key and
  `fit_pool`, `stats["effects"]`, the timer's names. `ui.py`: the
  docstring of `Panel.gpu_lines` (its code already showed whatever the
  timer keyed).
- **Tests.** `tests/test_graph_effects.py` (new), notably
  `::test_the_default_graph_holds_one_effect_node_per_instance_in_chain_order`,
  `::test_an_off_effect_is_read_through_and_runs_no_pass`,
  `::test_two_instances_of_one_effect_are_two_nodes_on_one_program`,
  `::test_the_system_page_times_each_effect_that_ran`,
  `::test_the_pipeline_end_still_paints_straight_into_a_frame_sized_output`,
  `::test_the_renderer_builds_the_run_from_the_stack_and_a_toggle_does_not_rebuild`,
  `::test_a_held_effect_read_through_the_pool_is_never_its_consumers_target`,
  and `::test_the_run_draws_what_the_one_block_chain_drew`, which
  compares the run byte for byte with the pre-D0 `Fx.paint` (copied
  verbatim) through all three pipelines. Changed on purpose: the
  timer-list tests gain the effect's own line (decision 5:
  `tests/test_graph.py::test_the_timer_lists_the_graphs_nodes_and_drops_a_node_that_left`,
  `tests/test_golden_frames.py::test_each_node_has_a_rolling_median_in_ms`),
  and three tests spy on or break `FxChain.run_one` instead of `run`
  because the frame chain no longer calls `run`
  (`tests/test_render.py::test_one_clock_reaches_the_patterns_and_the_effects`,
  `::test_a_frame_effect_runs_over_a_face_effect`,
  `tests/test_outputs.py::test_a_raising_pipeline_leaves_its_views_on_the_ground_and_the_rest_drawn`).
  `tests/test_render.py::test_the_render_stack_imports_no_registry` is
  untouched.

### D1 — placement in the preset

- **At the machine.** Nothing a factory preset does changes. A preset's
  `graph` section may place an effect:

  ```json
  "graph": {"nodes": [
   {"kind": "effect", "file": "palette", "after": "hands"},
   {"kind": "effect", "file": "palette", "instance": 2, "into": "output.2"},
   {"kind": "effect", "file": "acid", "instance": 2, "after": "scene"}
  ]}
  ```

  `after: "hands"` folds the hands' layer only; `into: "output.2"` folds
  one output's picture; `after: "scene"` folds the scene before the
  history and the capture, so the echoes and the dream hold the bent
  scene. SYSTEM lists a placed effect under its source (`palette` under
  `hands`). The OUTPUT page's "shows:" line and the LOOKBACK page say
  the placements in words; a placement the built graph cannot honour
  this frame is listed under the output blocks as `dormant: …`.
- **The keys** (`graph.EffectAt(file, n, after=None, into=None)`, with
  `name`, `placed`, `where`, `unplaced()`). One of the two, never both.
  A placed effect may name instance 1 (`{"kind": "effect", "file":
  "palette", "after": "hands"}`), which takes the file itself out of the
  chain; an unplaced instance 1 is still refused ("2 or more", as plan
  26 A4). The section writes instance 1 by its file alone and an extra
  instance with `instance`, and `after` / `into` as the file had them.
- **The vocabulary** (`graph.placement_error`, `PLACE_WORDS`): `scene`,
  `hands`, `hands.<n>`, `history`, `output.<n>`, and an effect instance
  this build has (a file on disk, or an extra instance the same section
  declares). `into` takes only the history, an output or an effect: the
  scene's and a layer's inputs are geometry, so `into: "scene"` is
  refused ("its inputs are geometry, not a picture: after 'scene' folds
  its picture"). An effect cannot sit after or into itself. `after:
  "output.<n>"` is accepted and means `into` (an output has no picture
  of its own to come after).
- **Refusals cost that effect its place, not the graph.** Both keys at
  once, a non-string (an explicit `null` included), a name outside the
  vocabulary, or a loop of placed effects (`graph.placement_loops`, at
  read and again at build in `Graph.notes`) is a note on the preset
  strip — `graph: palette after 'teapot' — this build places after
  scene, hands, hands.2 …, history, output.1 …, or an effect; the
  default placement` — and that effect goes back to the chain at its
  order (an extra instance) or is the file in the chain (instance 1).
  The rest of the graph lands and the section is kept as written.
  `read_graph(section, effects=)` returns these in `GraphSpec.notes`;
  `preset.GraphSection.read` is an instance method that passes the
  effect files on disk. Anything else unreadable is A4's note and the
  default graph, as before.
- **Dormant.** A placement on a node the built graph lacks this frame
  builds no node and says why in `Graph.dormant`: `palette after hands —
  no hands layer this frame`, `palette.2 into output.3 — no output 3
  this frame`, `… — output 2 shows no picture this frame`, `… — no
  kaleido effect in this build`, `warp after palette — palette is
  dormant this frame`. A dormant effect does not fall back into the
  chain. The graph follows the switches, so the node comes back as soon
  as its target exists.
- **How an effect sits on its edge.**
  - After the scene or a hands layer (`Node.MAKES`), or after such an
    effect, the effect folds that texture once, in its own `run`,
    before any pipeline paints, into a held pool texture (`Effect.makes`,
    `_made`); every consumer reads that one picture, and a source with
    no picture this frame (no hand drawn) leaves it none. Made in `run`,
    the held texture can never be a consumer's target.
  - On a layer (`Effect.see_through`, walked back to the source) the pass
    keeps a see-through pixel see-through (`run_one(…, opaque=0)`), and
    the effect is laid on at the layer's `ghost.alpha` with the layer's
    depth (`Effect.alpha`, `depth`, `ghost`). The layer's readout is
    split always, so the guide and labels are never folded.
  - Into an output (`Output.folds`): the output folds the frame texture
    it settled on into a held pool texture and shows that; that
    output's pipeline is never painted direct.
  - After or into a painted node (the history, an effect of the run): D0's
    paint path, held when it has two readers.
  - `after` rewires every consumer's image port except those that read
    something else of the node (`Node.REFS`: the cover's face buffer, a
    depth, the readout). After an effect of the run there is one placed
    node per pipeline (`palette`, `palette(scene+hands)` …).
  - A placed node is listed right after its source (`Graph.insert`, which
    also refuses an edge that would make a loop), so SYSTEM shows it
    under its source.
  - The pool is 2, plus one per held effect, plus one per placed effect
    that folds a made texture or an output.
- **Presenters.** Every output after the first is a presenter on its own
  context. An output laying a folded layer hands `_compose` the folded
  texture (`hands_tex`), so a presenter's `Handoff.hands` is the folded
  layer, at its own Ghost's opacity (`Effect.ghost` passes through to
  the layer's: ghost 2's for `hands.2`). An output folded by `into`
  hands its presenter the folded frame. Either may be a half-float pool
  texture; `Presenter._ext` wraps every name as "f1", which declares only
  the wrapper's dtype (the `Handoff` docstring says so).
- **`fx_on`.** The renderer's "an effect is on" is now "an effect of a
  chain run is on": `chain(FRAME)` minus `Graph.placed_names`
  (`stats["fx_on"]`, which the OUTPUT page reads). With only placed
  effects on, a through output stands down as with none: no SCENE+HANDS
  run, `chain_runs` 0. The placed effect still runs, and its clock moves
  in `run_one` or through the capture.
- **The words.** `graph.placement_words`: `palette on the hands` (`on
  hands 2`), `acid 2 before the history` (after the scene), `acid 2 into
  the history only`, `palette after the history`, `palette 2 on output 2
  only`, `palette after acid 2`, `palette before warp`.
  `graph_words(spec, dormant)` appends them, or the dormant words.
  `output_placement_words` adds to each output's "shows:" line the
  placements on what that output shows (`· palette 2 on this output
  only`); `history_words` adds those on the history's way in or after
  it (`history: the scene · acid 2 before the history`).
- **The three fixtures** (each the factory preset's `values`, `routes`
  and `macros`, no `desk` or `modules`, like `hands-lines`; force-added):
  - `tests/fixtures/presets/palette-hands.json`: party-tracer's look,
    the palette `after: "hands"`, on, mix 1, centre 200, width 60, and
    `fx.on: true` (party-tracer bypasses the stack).
  - `tests/fixtures/presets/palette-glass.json`: party-acid, the palette
    `into: "output.2"`, the same palette values.
  - `tests/fixtures/presets/acid-scene.json`: party-mandala, a second
    acid `after: "scene"` with party-acid's acid values (bend 0.04, twist
    0.9, reach 10, breathe 0.35), on, mix 1, and `dream.on: true`
    (party-mandala has the look-back off).
- **Code.** `graph.py`: `EffectAt`, `PLACE_KEYS`, `PLACE_WORDS`,
  `instance_name`, `placement_error`, `placement_loops`,
  `GraphSpec.notes`, `Wiring.placed`, `read_graph(…, effects)`,
  `Node.MAKES` / `REFS`, `Effect` (`placed`, `makes`, `see_through`,
  `run`, `alpha`, `depth`, `ghost`, `_made`, `fold`, `_one`), `Output.folds`,
  `Graph.insert` / `folds` / `dormant` / `notes` / `placed_names`,
  `_place`, `_place_one`, `_consumers`, `placement_words`,
  `output_placement_words`, `history_words`, `graph_words(…, dormant)`.
  `fx.py`: `run_one(…, opaque=)`. `preset.py`: `GraphSection.read`.
  `render.py`: `fx_on` after the graph, `stats["fx_on"]`,
  `_compose(hands_tex)`. `outputs.py`: the `Handoff` docstring. `ui.py`:
  `output_shows(…, n=)`, `dormant_lines`, the OUTPUT page's hover.
  `tools/golden_frames.py`: `FIXTURE_PRESETS` (four).
- **Tests.** `tests/test_graph_placement.py` (13), notably
  `::test_after_hands_folds_the_hands_layer_and_not_the_shape` (the scene
  and layer textures byte-identical with and without, the output
  different only under the layer, one pass a frame with `opaque=0`),
  `::test_into_output_2_folds_one_output_only`,
  `::test_after_scene_feeds_the_history_the_folded_picture` (the
  capture's source is the effect's texture),
  `::test_a_placed_effect_is_not_in_the_chain_run`,
  `::test_an_unknown_placement_is_a_note_and_the_default`,
  `::test_a_placement_the_graph_lacks_is_dormant_and_said_in_words`,
  `::test_both_keys_at_once_are_refused`,
  `::test_the_section_round_trips_with_its_placements`,
  `::test_no_factory_preset_changes_and_the_default_graph_is_identical`,
  `::test_a_presenter_lays_the_folded_hands_and_shows_the_folded_frame`,
  `::test_a_placed_effect_alone_bends_no_pipeline`,
  `::test_the_words_say_the_placements`.
  `tests/test_golden_frames.py`'s completeness count gains `+ 3 * 8`.

### D2 — the FX page, the `VALUE` port, the faces exception

- **At the machine.** On the FX page an effect the loaded preset places
  leaves the chain's chip grid for a second grid under it, three to a
  row like the first: its chip reads `Palette · after hands`, `Palette ·
  into output 2`, `Acid 2 · after scene`, cut with an ellipsis to fit.
  It cannot be dragged and nothing drops on it; its LED switches it and
  its name opens its strip (any effect's, order slider included), whose
  title hover reads `palette.glsl · after hands` in place of the order.
  The name's hover gives the place whole, "placed by the preset's graph,
  not in the chain: moved in the preset's JSON, not by a drag", and
  `dormant: …` while the built graph has it dormant. The status line
  keeps the chain's labels and adds the count of placed effects that
  run: `Acid → Palette · 1 placed`, or `nothing in the chain · 1
  placed`. A placed effect aimed at the faces reads `Warp · on the
  faces`, is listed on the faces row and is not counted. Two grids of a
  and b chips take at most one row more than one grid of a + b, so the
  page never scrolls at the control size.
- **The chip's words** come from one function, `graph.placed_chips(spec)`
  (instance → `after hands`, `into output 2`, `after scene`, `into
  history`, `after acid 2`): the edit view, worded like the JSON.
  OUTPUT and LOOKBACK keep D1's `placement_words` (the show view:
  `palette on the hands`). Plan 28's N4 extends `placed_chips` for wires.
- **`graph.VALUE = "value"`**, the fourth port type beside `IMAGE`,
  `MASK` and `GEOMETRY` (`graph.PORT_TYPES` holds all four): a scalar or
  a small float vector a node publishes once a frame. Its docstring
  names its two uses — the palette's `palette` value out (centre, width,
  the sat and val ranges, the ramp's anchors) for a lights sink (plan
  29), and an image-in `sample` port on the palette that would set its
  params from a bitmap. **No node publishes or reads one.** On the
  modulation side, `patch.RENDER_VALUE = "value"` names it as a future
  source whose id is the node's port (`palette:palette`); `patch.py`
  does not import the graph.
- **The faces target stays an inner chain.** `target = faces` runs
  inside the shape's face drawing (`render.face_fx`, `FxChain.run`), not
  on a graph edge. The `fx.<name>.target` tip (hover an ONTO chip) now
  ends: "On the faces it runs inside the shape's face drawing: the one
  shader run the render graph does not show, and a placement in the
  preset's graph does not move it."
- **Code.** `graph.py`: `VALUE`, `PORT_TYPES`, `placed_chips`.
  `patch.py`: `RENDER_VALUE`. `fx.py`: the `target` tip. `ui_fx.py`:
  `page` (the second grid), `_chip(…, place=, dormant=)`, `placed_label`,
  `_placed`, `_dormant`, `_status(…, placed, dormant)`,
  `_drop(…, placed)`, `_strip_header(…, place)`, `strip` (computes the
  place itself, so the GRAPH page's side column shows it too); `PLACED`,
  `NO_CHAIN`, `PLACED_TIP`, `ON_FACES`.
- **Tests.** `tests/test_fx.py::test_a_placed_effects_chip_says_where_it_sits_and_is_not_reorderable`
  (the grid, the words, no drag, the count, dormant and faces-aimed
  chips), `::test_the_page_fits_with_three_placed_effects`,
  `::test_a_placed_effects_strip_says_its_place_wherever_it_is_drawn`;
  `tests/test_graph_effects.py::test_the_value_port_type_exists_and_no_node_uses_it`
  (every Node class and the built default graph). No existing assertion
  changed.

## The goldens

**580 goldens, 136 distinct pictures**, on "Apple M3 Max" (GL_VERSION
"4.1 Metal - 90.5"). **The 556 recorded before this plan matched byte
for byte after D0, after D1 and after D2** (decision 5): the run of
effect nodes, the pool and placement moved no default pixel. D1 recorded
24 new, once, with the reason "D1 fixture, new": the three fixtures,
hands present, in the eight output states. D1's review round changed
only two manifest fields of palette-hands (`route` / `hands_over` of
`scene+hands+through` and `hands+through`, which now stand down because
a placed effect alone bends no pipeline); no hash moved, and those two
states were already the same picture as their stood-down routes.
`tools/golden_frames.py` diffs said "all 580 frames match their goldens"
at the end of stream D; plan 28's N4 then added 16 for its two wire
fixtures, none of these 580 moved (596 today,
[`28-node-editor.md`](28-node-editor.md)). How to diff and re-record is in
[`26-render-graph.md`](26-render-graph.md), "How to re-record".

## What no person has verified

Everything visible. Every proof is headless: the tests, the goldens, and
one windowed smoke run of 120 frames with palette-hands as a show's
startup preset (no hand tape: the palette's line under `hands` is proven
by the graph's order and `timed_in`, not seen). In particular:

- **The three placements on the real projector and glass** (223, 224,
  227), and through a presenter: the rig's later outputs get the folded
  hands or frame as a half-float pool texture wrapped "f1" in a second
  context, which no test draws on a real second window.
- **Two palettes with different centres on two outputs** (231): no test loads two placed instances of one file into two outputs.
- **The folded hands' colour at distance**: the ghost's colours are
  low-saturation, so centre 200 reads grey-teal more than vivid blue
  (223).
- **The FX page's placed chip** and its words at the control window's
  size (229).
- **The faces target still bending the faces** after the run of nodes
  (230).
- **The SYSTEM per-effect lines** in the live app at the rig's 1080p cap
  (220).
- **A hot reload** of `fx.py` or `graph.py` mid-show with effects on: the
  existing `on_reload` drops the graph, but no test drives a reload with
  a run.

## Known rough edges

- **The SYSTEM per-effect split is indicative on Apple's tile GPU**: a
  query is charged for whatever is flushed inside it, so an effect's line
  can carry its input's work or read 0.00, and the split moves between
  rounds. **The end node's own `fx` line always reads 0.00**: its paint
  runs no pass of its own (timing around its input would nest queries).
  It does not mean the effects are free; their cost is on their lines.
- **The pool's `avoid` rule is load-bearing.** A held effect's texture
  must never be the framebuffer its consumer paints into (a GL feedback
  loop). `_spare` never hands out `dst` or a held texture, and `_make`
  passes the consumer's target as `avoid`; a placed effect after a
  texture-maker folds in `run`, before any pipeline paints. Pinned by
  `test_a_held_effect_read_through_the_pool_is_never_its_consumers_target`;
  a new node that holds a pool texture must keep the rule.
- **A presenter's `Handoff.frame` / `hands` may be a half-float pool
  texture**, not RGBA8: plan 26's hand-over contract widened, verified
  by texture identity in the tests, never on a real second window.
- **`into: output.<n>` on a through output that stands down** (no effect
  of its run on, or no hand drawn): falling back to its ground, the fold
  is skipped and, since the review pass's fixes (#221), says so for that
  frame — `palette into output 2 — output 2 stands down this frame`
  (`Graph.stood`, on OUTPUT's dormant lines and the FX chip); falling
  back to the scene pipeline, the fold runs on the scene alone, the hands
  laid over at the output unfolded, and nothing says so (row 223).
- **A build from before plans 28 and 30 refuses `after` / `into`**: a preset
  with a placement opens there as the default graph with one note, so
  both Macs sharing a library must run this build (row 277).
- **The faces target is an inner chain** the graph and the GRAPH page do
  not show; SYSTEM times it inside `scene`. An effect both placed and
  aimed at the faces runs in the faces' chain, not on its edge (its chip
  says "on the faces"); placement is not checked against `target`.
- **`FxChain._program` is built twice a frame per on effect** (`Effect.on`
  asks `ready`, then `run_one` asks again: a few KB of string work).
  Left: a per-frame cache would need a frame counter the tests' direct
  `run` / `poll` calls never tick.
- **Two vocabularies for one placement**: the FX chip says `after hands`,
  OUTPUT says `palette on the hands`.
- **Thirteen effect nodes per pipeline whatever is on** (up to 39 with
  the three pipelines); `repr(graph)` is long.
- **A file that fails to compile reads through** rather than the old
  block's copy through a half-float texture (`run_one` still copies if
  ever asked).
- **Dormancy follows the switches, not a hand in the box**: with the
  hands switch on and no hand, the palette's node exists and has nothing
  to fold. `hands.<n>` is placeable only on the node that makes the
  layer (one layer per graph); otherwise it is dormant.
- **Every member of a loop is refused**, not only the last named. A
  refused placement is written back unchanged on save (by design); a
  person fixes it in the JSON or on plan 28's GRAPH page.
- **`fx.active()` still counts a placed effect** (`FxChain.active`, the
  golden manifest's `effects_on`); the renderer's `fx_on` and the OUTPUT
  page do not.
- **The FX page reads the preset's spec** (`Panel.graph_now`), not the
  built graph: a placement refused only at build would still show as
  placed (none reaches it: `read_graph` refuses loops first). A dormant
  placement's chip looks like a running one but for the hover and the
  count. A long label and place is cut (`Kaleidoscope · aft…`). The page
  asks `_placed` twice a frame.
- **The words**: LOOKBACK reads `history: the scene · acid 2 before the
  history` (a little redundant); a placed extra instance still counts in
  `palette ×2` on the graph line.
- **The fixtures carry no desk**, so loaded at the machine they have no
  APC40 rows (the desk is Dylan's).
- **The palette-hands goldens** for `scene+hands` and
  `scene+hands+through` are the same picture (the through output stands
  down).

## Decisions

The owner's (2026-10-16), built as written:

1. **Shaders are nodes**: an effect file is an image node, bitmap in,
   bitmap out, several instances, placeable on any image edge. No single
   point in the graph holds "the shaders".
2. **The palette is the first shader node moved**, with a fixture per
   placement; its fold and gradient map (plan 24 C6) are unchanged.
3. **Auxiliary ports are separate concerns**: the palette's value out
   and image in are designed (the `VALUE` port type), not built.
4. **No preset is edited or added**; every proof is a fixture through a
   scratch library.
5. **The default graph is pixel-identical**: every golden passed
   unchanged, and SYSTEM gained a line per effect.

What the run decided where those left a choice (register rows 214–232):
the end keeps the name `Fx` (214); an off effect read through (215);
the pool on `FxChain`, sized by the graph (216); the effect node's name
(217); a SYSTEM line only for an effect that ran (218); both keys kept,
`after` and `into` (219); the vocabulary (220); a refusal costing only
that effect its place, loops refused twice (221); dormancy (222); how an
effect sits on an edge, presenters included (223); the words (224); the
fixtures' extra values (225); the placed chips' grid (226) and the
status count (227); two vocabularies (228); a dormant chip (229); a
faces-aimed placed chip (230); the `VALUE` port's shape (231); the faces
target kept as an inner chain (232).

**What the launch prompt asked for that was built otherwise.** The run
is `FxState.names()` (every instance, every target), with
`chain(FRAME)` the per-frame on-test: `chain()` lists only the on ones.
The pool lives on `FxChain` and is fitted to each graph rather than
owned by the graph object. The end's own SYSTEM line is kept but reads
0.00. An uncompiled effect reads through instead of the old copy. D1
touched `fx.py` (`run_one`'s `opaque`), `render.py` and `outputs.py`
(the presenter fix), not in its file list; the LOOKBACK words live in
`graph.history_words`, which `ui_lookback` already called. "Note and
default" for a refused placement is that effect's default placement,
the graph kept. The words read `palette on the hands` / `acid 2 before
the history`, not the node words. The FX status keeps the chain's labels
and appends `· N placed`, not `3 in the chain · 1 placed`. `VALUE` is
the fourth port type, not the third (`MASK` already existed). The
fixtures add `fx.on` (palette-hands) and `dream.on` (acid-scene).
