# Plans 28 and 30 — the node editor and shader nodes (orchestrator prompt)

You are the top-level orchestrator for the second group of work from the
post-party wishlist in `Cutaiar/hyperspace` (the Python app under
`hyperspace-python/`). Two streams, each its own plan, run together:

- **Plan 30 — shader nodes (stream D).** Every effect file becomes an
  image node of the render graph — bitmap in, bitmap out, several
  instances — placeable on any image edge by name. The palette fold is
  the first one moved. Small, and it lands first.
- **Plan 28 — the node editor (stream N).** The modulation graph
  evaluated in dependency order (the one-frame lag removed), modifier
  nodes in the preset, a GRAPH page that draws both graphs, cables for
  the modulation with Learn landing as a cable, the render graph edited
  as nodes and a wire list with outputs as nodes, controllers as nodes
  and the APC40 as two nodes.

The designs are **`docs/plans/30-shader-nodes.md`** and
**`docs/plans/28-node-editor.md`** (owner, 2026-10-16). This prompt
carries everything from them an implementer needs, plus the code sites;
where this prompt and a design file differ, the design file's *intent*
wins and you say so in the report.

Work the way plans 24, 26 and 27 were worked
(`24-26-27-orchestrator-prompt.md`, its ledger in
`assets/24-26-27-run/progress.md`, its lessons in
`24-26-27-handoff.md` "How the previous session worked"): numbered work
packages, one branch and PR each, an integration branch, a review pass,
a docs WP per plan. Sub-agents, one per WP, each in its own git worktree
off a verified base.

**Read first, in full:** the two design files; `docs/CHECKPOINT.md`;
`ARCHITECTURE.md` §2 (the frame and the lag rule you are changing) and
§3; `DECISIONS.md`; `DECISION-REGISTER.md` (the last row number: you
continue it); `docs/plans/README.md`; `26-render-graph.md` (the graph as
built — stream D changes one of its nodes) and `27-device-registry.md`
(the registry — stream N draws its devices); `ENGINEERING.md` §2, §6,
§9. Then `24-26-27-handoff.md` for how the last run was orchestrated.

Code sites below are `file:line` on `plan-24-26-27-integration` at
`0742c2a` (the design commit `fe1936e` sits on it). Re-find them by
symbol if they have moved; another agent is working the desk on the same
branch (below) and lines will shift.

## The base

Cut `plan-28-30-integration` from `plan-24-26-27-integration` if PR #195
is still open, else from `main`. Verify the gates on the base before any
WP is cut: `uv run pytest -q` and `uv run ruff check .` green, and
`uv run pytest tests/test_golden_frames.py -q` with every frame matching
(the goldens match only on the gate Mac, "Apple M3 Max"; elsewhere they
skip and you say so). At `0742c2a` the integration branch measured
**2228 passed, 2 skipped** (3 min 59 s on the gate Mac); the desk work
since may have moved it — record what you measure.

**Another agent is live on the same integration branch**: the owner's
collaborator Dylan is working the desk (the faders, the APC40 map and
feel) with a session of his own. Neither of your streams touches
`apc40.py`'s map, `midi.py`'s fader handling, the desk templates'
content or the coverage report. Expected overlaps and the rule for them:
`routing.py` (N0 adds the patch evaluation to `Router.modulate` and N1
adds `Bindings.modifiers`; the desk work edits rows and layers) and
`ui_routing.py` (N1 adds a MODIFIERS strip; the desk work edits the desk
section). Merge the integration branch into a WP branch before its PR
when either file moved under it, and never revert a line you did not
write. If the desk work lands a change to `Binding`'s fields, N0 and N1
build on the new fields.

**Never touch the owner's real `~/Hyperspace`, nor the shared library it
points at (`~/My Drive/Hyperspace`).** Every run and every tool uses
`HYPERSPACE_HOME=<scratch>` with no `[library]` section. No file under
`hyperspace/library/` changes (decision 4 / 11 below): every proof is a
fixture under `tests/fixtures/` (force-added: the folder is gitignored)
loaded through a scratch library.

**Models**: implementers and task reviewers on Opus, scoped re-reviews
and small docs re-reads on Sonnet, never Fable (owner, 2026-10-14).

---

## Stream D — plan 30, shader nodes

### Where the frame is today

`graph.py` is the render graph (plan 26): typed ports `IMAGE`, `MASK`,
`GEOMETRY` (`:116`); `Node` (`:571`: `KIND`, `INPUTS` port → type,
`OUTPUT`, `run`, `image`, `paint`); `Graph` (`:1475`: `add` re-sorts by
dependency, `evaluate` runs `node.run(frame)` in order);
`default_graph(views, wiring, clouds)` (`:1575`) builds today's frame
from the outputs' switches and the preset's `Wiring`. The nodes and their
ports are tabled in `30-shader-nodes.md`. Everything downstream of
`Scene` is image in, image out — except that **`Fx` (`:1312`) runs every
enabled effect as one block**: one `Fx` node per pipeline end
(`FX_NAMES`, `:1571`: `fx`, `fx(scene+hands)`, `fx(hands)`), its `paint`
(`:1383`) calling `FxChain.begin` then `FxChain.run` (`fx.py:676`,
`:710`), which ping-pongs two `f2` textures through every effect
`FxState.chain(FRAME)` lists (`fx.py:376`, sorted by `order` then name).
`Fx.run` (`:1355`) is also the pipeline's **end**: paint straight into
the one output at the frame's size and unflipped, else into
`Renderer._frame_target(key, size)` once for every output that takes it;
`Fx.bent` / `fallback` and `Output.settle` make a through pipeline stand
down when nothing bends its layer; a raise marks the views
(`Renderer._view_failed`).

An effect is a file in `hyperspace/shaders/fx/` with a header `fx.parse`
reads (`fx.py:142`): `@label @order @blend @speed @mix @tip` and one
`// @param` per uniform. Its params are `fx.<name>.*`, declared by
`fx.declare` (`:476`): `on mix speed blend order target` (`RESERVED`,
`:79`) plus the uniforms. A second instance is `acid.2` with
`fx.acid.2.*` on the same program (`FxState.set_instances`, `:313`,
plan 26 A4). `target` (`TARGETS`, `:75`: frame, faces) aims an effect at
the frame chain (`render.py:885`, `self.fx`) or the **faces chain**
(`render.py:892`, `self.face_fx = FxChain(ctx, state, target=FACES,
programs=self.fx)`), which runs on the shape's face layer inside the
scene's drawing. The palette (`shaders/fx/palette.glsl`, `@order 95`,
`@mix 0`, twenty params, plan 24 C6) is one effect among thirteen.

The preset's `graph` section (plan 26 A4): `GraphSpec` (`:311`),
`NODE_KINDS` (`:303`: `hands`, `effect`, `history`), `read_graph`
(`:384`), `to_json` (`:352`), `EffectAt(file, n)` (`:235`);
`preset.GraphSection` (`preset.py:193`), read in `Presets.load_doc`
(`:533`), written by `Presets.document` (`:701`). An unknown kind or key
is a note on the preset strip and the default graph; the section is
kept and written back. `graph_words` (`:495`) says the spec in words for
the OUTPUT page's "shows:" line. The goldens: `tests/test_golden_frames.py`
and `tools/golden_frames.py` (`FIXTURE_PRESETS` lists the fixture
presets that have frames; 556 hashes in `tests/golden/frames/`).

### The work packages

Serial: D0 → D1 → D2 → D3. Branches `plan-30-d0-effect-nodes`,
`plan-30-d1-placement`, `plan-30-d2-fx-page`, `plan-30-d3-docs`.

### D0 — the effect node, and the chain as a run of them

**Files.** Modify `hyperspace/graph.py` (`Fx`, `default_graph`,
`FX_NAMES`), `hyperspace/fx.py` (`FxChain`), `hyperspace/render.py`
(`_graph_for`, the SYSTEM stats), `hyperspace/ui.py` (the SYSTEM page's
per-node lines). Create `tests/test_graph_effects.py`.

**Build.**

- `graph.Effect(name: str, *, image: Node | None = None)`: `KIND =
  "effect"`, `INPUTS = {"image": IMAGE}`, `OUTPUT = IMAGE`. `name` is the
  effect's instance name as `FxState` knows it (`acid`, `acid.2`,
  `palette`). `run` does nothing GPU-side; `image(frame)` returns, when
  the effect is **off** this frame, its input's image (**no pass, no
  texture**: the consumer reads straight through), else a texture the
  effect painted its input into. The pass runs once a frame however many
  consumers read it, under `frame.timed(self.name)` so SYSTEM shows one
  line per effect that ran.
- `FxChain.run_one(name: str, src: moderngl.Texture, dst:
  moderngl.Framebuffer, t: float) -> None`: one effect's program over
  `src` into `dst`, uniforms set as `run` sets them. `FxChain.run` stays
  for the faces chain (`render.face_fx`) and anything else that still
  calls it; the frame chain's work moves to the nodes. The ping-pong
  textures (`begin`) become the pool the `Effect` nodes paint into
  (two are enough for a straight run; a placed effect (D1) may need a
  third — size the pool by the graph, release with it).
- `default_graph` builds, in place of each `Fx` node, a **run** of
  `Effect` nodes in `FxState.chain(FRAME)` order (every instance, on or
  off — an off node is a pass-through, so the graph's shape does not
  change when a chip is toggled and `_graph_for` need not rebuild), then
  the pipeline **end** node, whose input is the last effect. The end
  node keeps `Fx.run`'s jobs exactly — direct-to-output, the frame
  texture, `bent` / `fallback`, the error path. Whether it keeps the
  class name `Fx` is yours (register it); its `paint` becomes "paint my
  input". `frame.stats["chain_runs"]`, `frame.fx_on` and
  `FxState.advance_to` keep their meaning (the clocks advance once a
  frame whatever runs).
- The SYSTEM page: the one `fx` time becomes a line per effect that ran
  this frame (`ui.py`'s per-node lines from plan 26 A0), the end node's
  own line kept for the paint.

**Tests** (`tests/test_graph_effects.py`), at least:
`test_the_default_graph_holds_one_effect_node_per_instance_in_chain_order`,
`test_an_off_effect_is_read_through_and_runs_no_pass` (count GL passes
through the stats or a counting stub), `test_two_instances_of_one_effect_are_two_nodes_on_one_program`,
`test_the_system_page_times_each_effect_that_ran`,
`test_the_pipeline_end_still_paints_straight_into_a_frame_sized_output`.
**Every golden passes unchanged** (`uv run pytest
tests/test_golden_frames.py -q`): a moved frame is a bug, not a
re-record. `tests/test_render.py::test_the_render_stack_imports_no_registry`
untouched (no node method named `apply`).

### D1 — placement in the preset

**Files.** Modify `hyperspace/graph.py` (`EffectAt`, `GraphSpec`,
`read_graph`, `to_json`, `default_graph`, `graph_words`),
`hyperspace/preset.py` (`GraphSection` if its validation lists keys),
`hyperspace/ui.py` (OUTPUT "shows:", LOOKBACK's history line),
`tools/golden_frames.py` (`FIXTURE_PRESETS`),
`tests/test_golden_frames.py` (the completeness count). Create
`tests/fixtures/presets/palette-hands.json`,
`tests/fixtures/presets/palette-glass.json`,
`tests/fixtures/presets/acid-scene.json`, `tests/test_graph_placement.py`.

**Build.**

- `EffectAt` gains `after: str | None = None` and `into: str | None =
  None` (exactly one, or neither). JSON keys `after` / `into`, as the
  design shows. `read_graph` refuses both at once, a non-string, or a
  name outside the **placeable vocabulary**: `scene`, `hands`,
  `hands.<n>`, `history`, `output.<n>`, and any effect instance name —
  with the existing note-and-default behaviour ("graph: palette after
  'teapot' — this build places after scene, hands, hands.2 …, history,
  output.1 …, or an effect; the default placement").
- `default_graph` honours placement: `after: X` inserts the effect on
  X's output (every consumer of X is rewired to read the effect);
  `into: Y` inserts it on Y's `image` input alone (`output.<n>` means
  that output's `image` port). A placed effect is **not** in the chain
  run. A name the built graph lacks this frame (`output.3` with two
  outputs; `hands` with no layer) leaves the effect **dormant**: no pass,
  and the words say so ("palette after hands — no hands layer this
  frame"). A placement that would make a cycle is refused at build with
  the same note shape and the default placement.
- `graph_words` / the OUTPUT page's "shows:" line and the LOOKBACK page
  say placements in words (`palette on the hands · acid 2 before the
  history · palette 2 on output 2 only`).
- The three fixtures, each a copy of a factory preset plus a `graph`
  section and the effect's `on` and `mix` in `values`:
  `palette-hands.json` (party-tracer's values; palette `after: "hands"`,
  centre 200, width 60, mix 1), `palette-glass.json` (party-acid; palette
  `into: "output.2"`), `acid-scene.json` (party-mandala; `acid` instance
  2 `after: "scene"`, so the dream echoes the bent scene). Each gets its
  golden across the output states `tools/golden_frames.py` records for
  fixture presets, recorded once with the reason "D1 fixture, new".

**Tests** (`tests/test_graph_placement.py`), at least:
`test_after_hands_folds_the_hands_layer_and_not_the_shape` (pixels of
the layer texture vs the scene texture on a synthetic pose),
`test_into_output_2_folds_one_output_only`,
`test_after_scene_feeds_the_history_the_folded_picture` (the capture's
source is the effect),
`test_a_placed_effect_is_not_in_the_chain_run`,
`test_an_unknown_placement_is_a_note_and_the_default`,
`test_a_placement_the_graph_lacks_is_dormant_and_said_in_words`,
`test_both_keys_at_once_are_refused`,
`test_the_section_round_trips_with_its_placements`,
`test_no_factory_preset_changes_and_the_default_graph_is_identical`.
Goldens: the 556 unchanged, plus the fixtures' new frames.

### D2 — the FX page, the `VALUE` port, the faces exception

**Files.** Modify `hyperspace/ui_fx.py` (`page`, `_chip`, `strip_rows`),
`hyperspace/graph.py` (`VALUE`), `hyperspace/fx.py` (the `target`
param's tip). Tests in `tests/test_fx.py` and `tests/test_graph_effects.py`.

**Build.**

- The FX page stays the editor of the **default chain**. A placed
  instance's chip shows where it sits ("after hands", "into output 2")
  and is not draggable in the order; its strip is as any effect's. The
  page's status line counts placed effects separately ("3 in the chain ·
  1 placed").
- `graph.VALUE = "value"`: a third port type, declared beside `IMAGE`,
  `MASK`, `GEOMETRY`, with a docstring naming its two intended uses — a
  palette's value out (centre, width, sat and val ranges, the ramp
  anchors) for a lights sink (plan 29), and an image-in `sample` port
  that would set a palette's params from a bitmap — **and no node
  publishes or reads one in this plan**. Stream N's `modgraph.py` is told
  the type name so a `VALUE` port can be a modulation source later.
- `fx.<name>.target`'s tip says the faces target still runs inside the
  shape's face drawing and is the one shader run the graph does not
  show; draft the register row (the lift, "faces as a layer", as the
  other option).

**Tests**: `test_a_placed_effects_chip_says_where_it_sits_and_is_not_reorderable`,
`test_the_value_port_type_exists_and_no_node_uses_it`.

### D3 — plan 30's docs

See "What the docs WPs must produce". Lands after D2; before or after
stream N's docs, whichever is ready (the shared files are edited by
whichever lands later, on the integration branch).

---

## Stream N — plan 28, the node editor

### Where the modulation is today

`routing.py`: `Binding` (`:577`; fields in `28-node-editor.md`), `OPS`
(`:346`), `MOD_OPS` (`:330`, the performer ops), `SINK_OP` (`:344`),
`is_continuous` (`:324`), `QUALIFIER` (`:307`); `Sub` (`:1254`) and
`Macro` (`:1280`, `MACRO_PREFIX` `:368`); `Owned` (`:564`), `referee`
(`:1068`); `is_session_row` (`:1590`); `Bindings` (`:1616`: `mods`
`:1914`, `routes` `:1918`, `owner` `:1931`, `depth_subs` `:2161`,
`move_route` `:2167`, `_check` `:2201`, `bind` `:2225`, `add` `:2286`,
`replace_owner` `:2294`, `remove` `:2338`, `set_routes` `:2346`,
`to_json` `:1871`, `bindings_path` `:968`); `Router` (`:2359`: `schemes`
`:2426`, `address` `:2485`, `follow_macros` `:2512`, `feed` `:2679`,
`gated` `:2684`, `source_feel` `:2717`, `feel_of` `:2724`, `_move`
`:2746`, `modulate` `:2762`). `params.py`: `PERFORMANCE_GROUPS` /
`SESSION_GROUPS` (`:109–110`), `Kind` (`:143`), `Param` (`:153`;
`modulate` `:510`, `apply` `:531`), `part_of` (`:584`), `Registry`
(`:642`; `apply` `:712`, `snapshot` `:729`, the constructors `:773–816`),
`build_registry` (`:898`). `motion.py`: `Motion` (`:97`), `Follower`
(`:141`). `lfo.py`: `LFO` (`:99`; `step` `:130`), every knob a registry
param (`lfo.<n>.depth` …), the docstring at `:36` naming the lag.

The frame (`app.frame`, `app.py:846`; `ARCHITECTURE.md` §2 table): keys
`:872`, devices poll, `follow_macros` `:901`, …, `devices.feed`,
`lfos.step` / `lfos.publish` `:948–949`, `router.modulate` `:953`,
`reg.apply` `:954`, `devices.send`, render, panel. **The one-frame
lag** (`ARCHITECTURE.md:103–117`): a `scale` param, a macro's depth
subscriber and an LFO's own knobs read what `apply()` wrote last frame;
pinned by `tests/test_lfo.py:369` and `tests/test_routing.py:1907`;
`tests/test_app_boundary.py:393` pins the step order.

`learn.py`: `Learn` (`:292`; `wants` `:325`, `arm` `:348`, `accepts`
`:375`, `learn_control` `:401`, `learn_pad_button` `:504`, `learn_sink`
`:557`, `learn_source` `:604`, `_row` `:664`, `resolve_pending` `:690`,
`_place` `:705`). `ui_routing.py`: `add_route` (`:355`, the `Owned` →
ask → `replace_owner` prompt), `source_schemes` (`:500`), `_sources`
(`:514`), `_gates` (`:545`), `_targets` (`:603`), `_row` (`:676`),
`unmapped` (`:1088`), `macros` (`:1300`), `session` (`:1365`), `sinks`
(`:1402`), `page` (`:1483`). `ui.py`: `PAGES` (`:480`), a page is one
tuple plus `Panel._page_<key>`; the param menu offers Learn (`:14`,
`:347–355`, `:658`). `preset.py`: `SCHEMA` (`:142`), `GRAPH_KEY`
(`:190`), `load_doc` (`:533`; routes read and refereed through
`set_routes`), `document` (`:701`), `migrate_home` (`:2033`).
`devices.py`: `Port` (`:121`), `Device` (`:155`; `sources` `:191`),
`Base` (`:237`), `MidiDevice` (`:427`; `layers` `:468`, `sources`
`:498`); the registry's open devices and their roles. `hotreload.MODULES`
(`hotreload.py:56`, dependency order).

The widget: `imgui_bundle.imgui_node_editor` (imgui-bundle 1.92.9, the
pinned dependency): `Config`, `create_editor`, `set_current_editor`,
`destroy_editor`, `begin` / `end`, `begin_node` / `end_node`,
`begin_pin(id, PinKind)` / `end_pin`, `link(id, from, to, color,
thickness)`, `begin_create` / `query_new_link` / `accept_new_item` /
`end_create`, `begin_delete` / `query_deleted_link` / `end_delete`,
`get_node_position` / `set_node_position`, selection and hover queries,
zoom. Nothing in the package imports it yet; the control window is plain
`imgui` over GLFW (`app.py:62–73`).

### The work packages

N0 ‖ N1 start on day one beside D0. N2 after N0, N1 and D0. N3 ‖ N4
after N2 (N4 also after D1). N5 after N3. Then the review pass, then
N6. Branches `plan-28-n0-patch`, `plan-28-n1-modifiers`,
`plan-28-n2-graph-page`, `plan-28-n3-edit-modulation`,
`plan-28-n4-edit-render`, `plan-28-n5-controllers`, `plan-28-n6-docs`.

### N0 — the modulation graph in dependency order

**Files.** Create `hyperspace/modgraph.py` (a **leaf**: imports nothing
from the package but `motion` and `tapers`; add it to
`hotreload.MODULES` before `routing`), `tests/test_modgraph.py`. Modify
`hyperspace/routing.py` (`Router.modulate`, a `Router.modgraph` cache
rebuilt when the table, the LFO list or the registry's modulatable set
changes), `hyperspace/params.py` (`Param.apply` idempotent within a
frame — below), `hyperspace/lfo.py` (`LFOs.step_one` or equivalent so
one LFO can step inside the evaluation), `hyperspace/app.py:948–954`,
`tests/test_lfo.py:369`, `tests/test_routing.py:1907`,
`tests/test_app_boundary.py:393`, `docs/ARCHITECTURE.md:103–117`
(drafted here, finished by N6).

**Build.**

- `modgraph.py`: `ModNode(id: str, kind: str)` with kinds `source`,
  `lfo`, `modifier`, `macro`, `param`; `ModEdge(src: str, dst: str,
  port: str)` with ports `mod`, `base`, `depth`, `in`, and the LFO knobs
  (`depth`, `rate`, `phase`); `ModGraph(nodes, edges)`; `order(g) ->
  list[ModNode]` (a stable topological sort: dependencies first, ties
  in insertion order, like `Graph._sort`); `cycles(g) ->
  list[list[str]]`. Pure data and pure functions; `tests/test_modgraph.py`
  proves them without a Router.
- `Router.build_modgraph()`: from `table.routes()` (a performer row = an
  edge source → param `mod`), `table.macros` (a `Sub` with `base` = macro
  → param `base`; with `depth` = macro → that cable's `depth`), a row's
  `scale` (param → cable `depth`), each LFO's knob params (param → LFO),
  and from N1 the modifiers' inputs. **Routes convert one-to-one**: a
  cable's identity is `(source, target)`.
- `Router.modulate(analyzer, dt)` evaluates **in `order(patch)`**: a
  source node is its fed lane; an `lfo` node steps that LFO
  (`LFOs.step_one(n, dt, now, clock)`) and publishes its lane; a
  `modifier` node (N1) steps and publishes `mod:<n>`; a `macro` node
  reads its base; a `param` node runs today's row arithmetic for the
  cables into its `mod` port (depth = `value × scale.value × Π depth
  subs`, the follower, push / position) and then **applies that param
  now** (`Param.apply`), so anything downstream reads **this frame's**
  effective value. `Param.apply` becomes idempotent within a frame (a
  frame mark; `Registry.apply` at step 11 skips what `modulate` already
  landed and lands the rest exactly as today). `app.frame`: `lfos.step`
  / `lfos.publish` (`:948–949`) move inside `router.modulate`; step 9
  of the table becomes "LFOs step inside the patch"; `ORDER` in
  `tests/test_app_boundary.py:393` changes **only** by that move, named
  in the PR body.
- **Cycles**: a cycle not broken by a `delay` modifier (N1) leaves its
  last cable (in table order) **disabled with a note** on the preset
  strip ("loop: hand R x → mod 3 → … needs a delay"), the way `referee`
  drops a second performer; the rest of the patch runs. Nothing is
  removed from the file.
- The two lag tests flip to "the same frame" (`…changes_its_output_the_same_frame`,
  `…scales_a_lanes_push_the_same_frame`), each change named in the PR
  body with decision 7.

**Tests.** `tests/test_modgraph.py`: `test_order_puts_dependencies_first_and_keeps_insertion_order_for_ties`,
`test_cycles_finds_every_loop_and_none_through_a_delay`,
`test_a_route_a_macro_sub_and_a_scale_are_the_edges_the_design_names`.
In `tests/test_routing.py`: `test_every_factory_preset_lands_the_same_values_one_frame_earlier`
— play each factory preset through a scratch library with a synthetic
hand tape and an LFO on, record every modulatable param's effective
value per frame on the base build's arithmetic (today's `modulate` kept
behind a flag for the test only, or a recording committed as a fixture
with its reason) and on the new; assert the new sequence equals the old
shifted by one frame for every param a performer moves, and identical
for every param none moves. `test_a_cycle_without_a_delay_disables_its_last_cable_with_a_note`,
`test_sinks_still_send_after_apply`. The goldens are unmoved (recorded
at rest).

### N1 — modifier nodes, in the preset

**Files.** Create `hyperspace/modifiers.py` (a leaf: `motion`, `tapers`;
in `hotreload.MODULES` before `routing`), `tests/test_modifiers.py`.
Modify `hyperspace/routing.py` (`Bindings.modifiers`, `to_json` leaves
them out of the session file, `Router.feed` of `mod`), `hyperspace/params.py`
(`"mod"` appended to `PERFORMANCE_GROUPS`), `hyperspace/preset.py`
(`MODIFIERS_KEY = "modifiers"` read in `load_doc`, written by
`document` after `routes`; a desk template may carry a `modifiers`
list, expanded like its rows), `hyperspace/ui_routing.py` (a
`modifiers(panel, router)` section between `routes` and `desk`),
`hyperspace/learn.py` (`accepts` takes `mod:` as a continuous source).

**Build.**

- `modifiers.Modifier(id: str, kind: str, inputs: tuple[str, ...],
  params: dict[str, float])`, `KINDS = ("curve", "scale", "smooth",
  "combine", "threshold", "delay")` with the inputs and params the design
  tables (`curve`: `shape` −1…1 with 0 linear and a `table` option left
  out of this run, `invert`; `scale`: `mul`, `offset`, `clamp`;
  `smooth`: `attack`, `release`, `spring` 0/1; `combine`: `how` in `add
  mul min max cross`, `balance`; `threshold`: `on`, `off`, `hold`;
  `delay`: none). `step(m: Modifier, inputs: tuple[float, ...], state:
  ModState, dt: float) -> float`, pure but for `state` (the follower,
  the threshold's gate, the delay's held value). A `threshold`'s output
  is a **trigger-kind** lane: 1 on the rising edge for `hold` seconds,
  else 0 (the Router's `fire`-style rows may read it later; this run
  publishes it as a value lane and registers the kind).
- Ids by the naming rule: `mod.1`, `mod.2` … (`modifiers.next_id`).
  Params `mod.<n>.<p>` declared into the registry (group `mod`,
  performance, modulatable) when a modifier is added, dropped when it is
  removed — the way `fx.declare` adds an instance's params. Output lane
  `mod:<n>` (scheme `mod`, continuous), fed by the Router when the
  `modifier` patch node is evaluated (N0's order), so a route with
  `source: "mod:2"` needs no new Router path and ROUTING's source combo
  lists it (`source_schemes` already adds schemes a row names).
- **The preset** holds them: `"modifiers": [{"id": "mod.1", "kind":
  "smooth", "in": ["hand:right.energy"], "attack": 0.05, "release":
  0.6}]` after `routes` in `Presets.document`; `load_doc` reads them
  before the routes (a route onto a missing `mod:<n>` is dropped with a
  note, like a route onto an unknown param); a modifier whose input this
  rig lacks is kept dormant (its lane stays at its rest, 0). No schema
  bump: an older build ignores the key. `is_session_row` is untouched:
  modifiers never reach `bindings.json`. A desk template's JSON may carry
  `modifiers`; a preset using it gets them, its own overriding by id.
  `undo.tick` watches them with the table.
- **ROUTING's MODIFIERS strip**: add a kind (a combo), pick each input
  from `_sources` (plus `mod:` lanes), the params as sliders, remove;
  the live output value shown. Enough to build "right hand energy,
  smoothed, times band 0, into acid mix" from ROUTING alone.

**Tests** (`tests/test_modifiers.py`), at least: one per kind on a
scripted input (`test_smooth_follows_with_its_attack_and_release`,
`test_combine_mul_and_cross`, `test_threshold_fires_once_on_the_rising_edge_and_holds`,
`test_delay_is_one_frame_late`, …),
`test_a_modifier_publishes_a_lane_a_route_can_source`,
`test_modifiers_live_in_the_preset_and_never_in_bindings_json`,
`test_a_route_onto_a_missing_modifier_is_dropped_with_a_note`,
`test_a_template_may_carry_modifiers_and_a_preset_overrides_by_id`,
`test_the_routing_page_builds_the_smoothed_energy_times_band_patch`
(through the page's functions, as `test_hands_dance` drives ROUTING),
`test_an_older_preset_without_the_key_loads_as_before`.

### N2 — the GRAPH page, read-only

**Files.** Create `hyperspace/graphview.py` (the model: imports
`routing`, `params`, `graph`, `devices` — **no imgui**), `hyperspace/ui_graph.py`
(the drawing: `imgui`, `imgui_node_editor`, `graphview`),
`tests/test_graphview.py`. Modify `hyperspace/ui.py` (`PAGES` gains
`("graph", "GRAPH", <the routing page's group>)` after `routing`;
`Panel._page_graph`; the editor context created on first draw and
destroyed in the panel's close), `hyperspace/preset.py` (`LAYOUT_KEY =
"layout"`), the show file (session nodes' positions), `hotreload.MODULES`.

**Build.**

- `graphview.build(table, reg, router, registry_of_devices, render_graph,
  spec) -> View` where `View` holds `nodes: list[VNode]` (`id`, `kind`,
  `label`, `ports: list[VPort]` with `id`, `name`, `direction`, `type`
  in `value trigger image geometry mask`, `group` for collapsible
  groups, `patched: bool`, `live: float | None`), `cables: list[VCable]`
  (`id`, `src_port`, `dst_port`, `type`, `live`, `dormant`, `ref`: the
  `Binding` / `Sub` / render edge it stands for). Node kinds and
  grouping as the design's §3: device nodes by role from the registry's
  open devices (ports = `Device.sources` grouped by the device's port
  groups; lost devices grey), the analyzer, each LFO (knobs as input
  ports), modifiers, macros (bus nodes), **params grouped by the render
  node that owns them** (`shape`, each hands node, `scene`, each effect,
  `history`, `eye` / `camera`, each output; the mapping from a param's
  group to a render node is one table in `graphview`), a node per
  remaining group, and the render nodes' own image / geometry / mask
  cables from `render_graph` (plan 30's placed effects among them).
  Each param port draws a `base` stub and a `mod` stub.
- `ui_graph.page(panel, dt)`: one `imgui_node_editor` canvas; the
  widget's settings file off (`Config.settings_file = ""`); cables
  coloured by type, a value cable's thickness following `live`;
  collapsed nodes show patched ports only (a per-node toggle and a
  page-wide "patched only"); hover shows the reading and the depth;
  selection shows the ROUTING row (`ui_routing._row`) or the effect's
  strip in a side column; **read-only**: `begin_create` / `begin_delete`
  are not opened in this WP.
- **Layout**: `preset["layout"] = {"<node id>": [x, y]}` for preset
  nodes (modifiers, macros, params' render nodes), the show's `layout`
  for session nodes (devices, outputs, LFOs); read on load, written on
  save, applied with `set_node_position`; an unplaced node gets
  `graphview.auto_layout(view)`'s column by kind (devices → LFOs,
  modifiers, macros → render nodes → outputs, left to right); a **tidy**
  button re-lays all.

**Tests** (`tests/test_graphview.py`, headless): `test_every_route_is_one_cable_and_every_cable_one_route`,
`test_macro_subs_are_cables_into_base_or_depth`,
`test_params_group_under_the_render_node_that_owns_them`,
`test_device_nodes_come_from_the_registry_with_their_port_groups`,
`test_the_render_graphs_edges_are_image_cables_including_a_placed_effect`,
`test_layout_round_trips_through_the_preset_and_the_show`,
`test_auto_layout_gives_every_unplaced_node_a_column`; plus the page
drawn once under the test imgui harness the other pages use
(`tests/test_ui.py`'s pattern), asserting it draws without error with a
factory preset loaded.

### N3 — editing the modulation on the canvas

**Files.** Modify `hyperspace/ui_graph.py` (`begin_create` /
`begin_delete`, drag-and-drop, the node picker for modifiers and
macros), `hyperspace/graphview.py` (`Edit` requests: `connect(src_port,
dst_port)`, `disconnect(cable)`, `insert_modifier(cable, kind)`,
`add_modifier(kind)`, `remove_node(id)` — each returning what the table
method returned, or a refusal in words), `hyperspace/learn.py` (nothing
new if `arm` suffices). Create `tests/test_graph_edit.py`.

**Build.**

- `connect` into a param's `mod` port → `Bindings.add(Binding(src, pid,
  op, value))` with op and depth as `learn._row` chooses for that source
  (`push` at the hand learn's depth for a hand axis, else `position` at
  1); `Owned` → the same ask → `replace_owner` prompt `ui_routing.add_route`
  shows (reuse it). Dragging a cable's end to another port →
  `move_route`. Into a `base` port → a setter row only for a `pad` or
  MIDI source (`Binding(src, pid, "abs", layer="preset")` through
  `bind(write=False)`, as a desk learn does), else refused in words ("a
  hand sets no base; aim at mod"). From a macro → a `Sub` (`base` port:
  a base sub; a cable's `depth` stub: a depth sub). Onto a modifier's
  `in` port → that modifier's input. A modifier dropped **onto a cable**
  → `insert_modifier`: the cable's source becomes the modifier's input,
  `mod:<n>` the cable's new source (`move_route`). `disconnect` →
  `remove` (its depth subs follow). Every edit goes through the table's
  own methods so undo, dirt, the referee and the session / preset split
  are untouched.
- **Learn from a port**: right-click a `mod` port → the param menu's
  Learn items (desk, pad, hand, a role, exactly as `ui.py`'s param menu
  offers them); the completed `Binding` appears as a cable next frame
  because the view is rebuilt from the table.

**Tests** (`tests/test_graph_edit.py`): `test_connecting_a_source_to_a_mod_port_adds_the_route_learn_would`,
`test_a_taken_param_asks_and_replace_owner_lands_the_cable`,
`test_moving_a_cables_end_moves_the_route_and_its_depth_subs_follow`,
`test_a_hand_into_a_base_port_is_refused_in_words_and_a_pad_is_a_setter_row`,
`test_dropping_a_modifier_on_a_cable_inserts_it`,
`test_deleting_a_cable_removes_the_route_and_undo_puts_it_back`,
`test_learn_from_a_port_lands_as_a_cable`,
`test_the_routing_page_and_the_graph_page_show_one_table`.

### N4 — editing the render graph: nodes and a wire list

**Files.** Modify `hyperspace/graph.py` (`Wire(src: str, dst: str)`,
`GraphSpec.wires`, `to_json` / `read_graph`, `default_graph(views,
wiring, clouds, wires)`), `hyperspace/render.py` (`_graph_for` rebuilds
on a spec change), `hyperspace/graphview.py` (`Edit.wire(src_port,
dst_port)`, `unwire`, `add_node(kind, …)` for an effect instance, a
hands node, a composite), `hyperspace/ui_graph.py` (image cables
draggable between typed ports; a right-click node picker listing the
effect files, "hands", "composite"), `hyperspace/ui.py` (OUTPUT /
LOOKBACK words), `tools/golden_frames.py`, `tests/test_golden_frames.py`.
Create `tests/fixtures/presets/hands-glass-only.json`,
`tests/fixtures/presets/wired-outputs.json`, `tests/test_graph_wires.py`.

**Build.**

- The preset's `graph` section becomes **nodes plus wires**: `{"nodes":
  [...], "wires": [{"from": "hands.2", "to": "output.2.hands"}, {"from":
  "palette", "to": "output.1.image"}]}`. A wire names a node's output
  and a `node.port`; a wire absent is the default graph's; D1's `after`
  / `into` are read as wires (and still written short when a spec has
  only those). `read_graph` refuses a wire into a port of another type,
  a port that does not exist, two wires into one single-input port, and
  a cycle, each a note and the default, the section kept.
- **Outputs as nodes**: a wire into `output.<n>.image`, `.hands` or
  `.readout` overrides that output's **switch-derived** input for this
  preset; an output no wire names keeps the session's switches (the
  rig's, not the look's). So a preset may say which output gets which
  hands node and which effects it alone takes, closing plan 26's
  rough edge. `Renderer._graph_for`'s key gains the spec's wires.
- On the canvas: `begin_create` between image / geometry / mask ports
  type-checked in the drag (a wrong type refuses with the note's
  words); the picker adds an effect instance (`EffectAt(file, n+1)`),
  a hands node (`HandsAt(n+1)`), or a composite; deleting a node or a
  wire edits the spec; the preset is dirty; `Renderer` rebuilds the
  graph from the new `GraphSpec` with the same refusals.
- Fixtures: `hands-glass-only.json` (two hands nodes: `ghost` in the
  scene, `ghost.2` wired to `output.2.hands` only), `wired-outputs.json`
  (the palette wired into `output.1.image`, a second acid wired after
  the history into `output.2.image`); goldens recorded once, "N4
  fixture, new".

**Tests** (`tests/test_graph_wires.py`): `test_a_wire_list_round_trips_and_d1_keys_read_as_wires`,
`test_a_wire_into_an_output_overrides_its_switch_and_an_unnamed_output_keeps_them`,
`test_a_wire_of_the_wrong_type_or_into_a_missing_port_is_a_note_and_the_default`,
`test_a_cycle_of_wires_is_refused`,
`test_dragging_an_image_cable_on_the_canvas_edits_the_spec_and_dirties_the_preset`,
`test_the_picker_adds_an_effect_instance_with_its_params`,
`test_hands_as_lines_through_the_acid_with_tracers_by_wires_alone`
(the fixture `hands-lines.json`'s picture reproduced from a spec built
by `Edit` calls), `test_no_factory_preset_changes`. Goldens: 556 + D1's
+ these, none moved.

### N5 — controllers as nodes; the APC40 as two nodes

**Files.** Modify `hyperspace/graphview.py` (device nodes from the
registry with `Device.layers`; template subgraph nodes; role
placeholders), `hyperspace/ui_graph.py` (expand / collapse a subgraph),
`hyperspace/devices.py` only if `layers` needs exposing on `Base`.
Create `tests/test_graphview_devices.py`.

**Build.**

- A device with `layers` is **one node per layer**: the APC40 is *APC40*
  (the rows with `layer == "preset"` and the invariant rows: SHIFT, the
  crossfader, the bank pads, transport, tap) and *APC40 (SHIFT)* (the
  rows with `layer == "global"`), each port lit while its layer is up
  (`MidiIO`'s latch state read through the registry), a cable drawn
  from the node its row belongs to. **Presentation only**: the rows,
  their homes (preset / `bindings.json`) and D1, D4–D6, D12 are
  untouched; nothing in `apc40.py` or `midi.py` changes. Dylan's desk
  work is read, never rewritten: build N5 on whatever `Binding` and the
  map look like when it is cut.
- **Desk templates as subgraphs**: a preset whose `desk` is a template
  plus overrides draws the template as one collapsed node whose ports
  are its mapped controls; expanded, its rows show as cables; an edit
  inside writes the preset's overrides (through the same table methods).
- **Roles, not serials**: a cable from a device this rig lacks (a row's
  `@role` or scheme with no open device) draws from a grey placeholder
  node named by role, its cables dormant, as the ROUTING page shows a
  dormant row.
- The hands device node's port groups: axes, pinches, dance, grab, from
  `hands/device.py`'s groups (plan 27 B2's `dance` / `switches`).

**Tests**: `test_the_apc40_is_two_nodes_and_each_row_hangs_off_its_layers_node`,
`test_invariant_controls_are_ports_on_the_first_node_only`,
`test_a_templated_desk_is_one_collapsed_node_whose_edits_write_overrides`,
`test_a_missing_role_is_a_grey_placeholder_with_dormant_cables`,
`test_nothing_in_apc40_py_or_midi_py_changed` (a diff-stat gate in the
PR body, not a test).

### N6 — plan 28's docs

See "What the docs WPs must produce". Last, after the review pass.

---

## Decisions already made — do not relitigate

All the owner's: 2026-10-12 (the wishlist), 2026-10-16 (the two design
files; the Q&A that produced them).

1. **Shaders are nodes** (plan 30): an effect file is an image node,
   bitmap in, bitmap out, several instances, placeable on any image edge.
   No single point in the graph holds "the shaders".
2. **The palette is the first shader node moved**; its fold and gradient
   map are unchanged; three placements are proven with fixtures.
3. **Auxiliary ports are separate concerns**: the palette's value out
   (lights) and image in (a camera) are designed as the `VALUE` port type
   and **not built**.
4. **No preset is edited or added** in this run; `hyperspace/library/`
   stays byte-identical; every proof is a fixture through a scratch
   library.
5. **The default graph is pixel-identical**: every golden passes
   unchanged after D0 and D1; SYSTEM gains a line per effect.
6. **One editor for both graphs; N1–N4 in one plan**, with controllers
   as nodes (2026-10-16).
7. **Evaluation in dependency order removes the one-frame lag**; loops
   only through a one-frame delay node.
8. **Modifiers live in the preset** (2026-10-16, option A of three),
   beside `routes`; a desk template may carry them.
9. **Two input ports per param**: `base` many (last touch wins), `mod`
   one under the referee; combining two performers is an explicit
   `combine` node.
10. **Values and triggers are two signal kinds**, crossed by `threshold`
    and `smooth`; encoder vs fader behaviour, soft pickup included, is
    the port's, set by the device profile.
11. **Roles, not serials**; a missing device's cables wait.
12. **The APC40 is two nodes**, *APC40* and *APC40 (SHIFT)*, no layer
    view; D1, D4–D6 and D12 hold; invariant controls on *APC40* only;
    the faders and the APC40's map and feel are **Dylan's and
    untouched** by this run.
13. **Both graphs live in the preset as plain JSON**; today's routes
    convert one-to-one into cables.
14. **Rejected**: GLSL written in the graph; a general TouchDesigner.
    Nodes are a curated set of built-ins; shaders stay files with hot
    reload.
15. **The editor is `imgui_node_editor` from imgui-bundle**; no new
    dependency.
16. **The processes in force**: `DECISIONS.md` "Process"; nothing in the
    render stack writes a param; `graph.py` imports no `params`,
    `routing`, `library`, `preset`, `undo`, `control`; the hands package
    stays liftable; the core never imports `midi`, `bridge`, `dream`,
    `osc`, `torch`, `leap`; agents on Opus / Sonnet, never Fable.

When the docs WPs record these, they go into `DECISIONS.md` with
**Who** = `owner`.

## Decisions you may make yourself

Anything the designs leave open: the placement keys' final form (`after`
/ `into`, or one); the pipeline-end node's name; how an off effect is
read through; the texture pool's size; whether the faces image becomes an
edge (default: no); the `VALUE` port's shape; `modgraph.py`'s exact types;
how `Param.apply` is made idempotent within a frame; the cycle note's
words; each modifier kind's exact params and curves; the `mod` scheme's
address form; the `layout` map's shape and where session nodes'
positions live; the canvas's grouping table for params with no render
node; the wire list's exact keys; which output ports a preset may wire;
the APC40 nodes' port groups; the tidy layout's columns. When you take
your own recommendation and build it, append a row to
`docs/DECISION-REGISTER.md` from **the next free number** at the time
the docs WP lands (214 as this is written; the desk work may take some —
check the file), in its format (what was built and what the owner will
see or feel; the other option(s); the cost to reverse; the known rough
edge; the hand check that lets the owner judge it), and mark the matching
`DECISIONS.md` row's **Who** as `row N`. Never mark a row `owner`
yourself except the sixteen above.

## Out of scope for this run

- **The desk**: the faders, the APC40's map and feel, desk templates'
  content, the coverage report — Dylan's work in flight on the same
  branch. N5 presents the rows; it changes none.
- **Plan 29**, the devices: wands, drums, Kinect, DMX / sACN, bulbs, a
  generic on-screen desk, an OSC sink. The `VALUE` port is designed for
  the lights; nothing publishes one.
- The palette's auxiliary ports; a palette from a camera; saved named
  palettes in the library (the creative pass: a saved palette is already
  an `fx` module preset).
- The faces image as a graph edge (default; a decision you may take).
- Order-independent transparency; hand styles and textures; H4 contact;
  touch shows (the creative pass and later plans).
- A `curve` modifier's lookup-table option; per-pad feel (plan 29).
- The web remote, touch panel, Dante, multi-channel capture, hardware.

---

## How to orchestrate

- One sub-agent per WP, each in its own git worktree off the verified
  base — dispatched with `isolation: "worktree"` and told to `git fetch
  origin plan-28-30-integration && git reset --hard FETCH_HEAD && git
  branch -m <name>` first (sub-agents cannot write to worktrees you cut
  for them; `assets/24-26-27-run/briefs/common.md` has the exact text).
  Re-verify the base right before each worktree is cut.
- Your own git commands are plain, one per call; merge each PR with a
  local `git merge --no-ff origin/<branch>` on the integration branch
  and push (`gh pr merge` is refused by the classifier). One PR per WP
  into `plan-28-30-integration`, titled `Plan 30 D0: the effect node and
  the chain as a run` and the like; the PR body names every test
  assertion it changed with its decision number, and every golden it
  recorded with its one reason.
- Per PR: an Opus implementer, an Opus task reviewer with a diff package
  (`git log` / `diff --stat` / `diff -U10` into one file), fix rounds by
  resuming the implementer, a Sonnet scoped re-review per round, then the
  merge and the full gates on the integration branch.
- Order: D0 ‖ N0 ‖ N1 on day one. D1 after D0; N2 after N0, N1, D0. D2
  after D1; N3 ‖ N4 after N2 (N4 also after D1). N5 after N3. Docs:
  D3 after D2, N6 last. Expected overlaps: `graph.py` (D0/D1/D2 and N4:
  N4 is cut after D1 lands, so it builds on the placement code);
  `routing.py` (N0's `modulate`, N1's `modifiers`; the desk work);
  `ui_routing.py` (N1's strip; the desk work); `preset.py` (N1's
  `modifiers`, N2's `layout`, N4's `wires` — three keys, three WPs, no
  shared lines); `ui.py` (N2's page tuple and `_page_graph`; D0's SYSTEM
  lines; D1/N4's OUTPUT words); `hotreload.MODULES` and its test (N0
  `modgraph`, N1 `modifiers`, N2 `graphview` and `ui_graph`, in import
  order); `tools/golden_frames.py` / `tests/test_golden_frames.py`
  (D1 and N4 both add fixtures: the completeness count is the sum).
  Anything else colliding means a WP is mis-scoped: stop and re-cut it.
- A **review pass** over the integration branch before the final PR,
  fixes committed as `Review: <what>`. Look hard at:
  - **A golden that moved.** None may, in any WP: diff every hash in
    `tests/golden/frames/` against the base's recording and account for
    each — the only new hashes are the five fixtures' (three from D1,
    two from N4).
  - **The lag's removal changing a value, not just its timing.** The
    "same values one frame earlier" test over every factory preset is
    the gate; a param whose sequence differs other than by the shift is
    a bug.
  - **A param applied twice in a frame** (inside `modulate` and in
    `reg.apply()`): its base restored, its offsets doubled, a toggle
    flipping twice. The idempotence mark must hold for every path that
    reaches `Param.apply`.
  - **An LFO stepping twice or not at all** after the move into the
    patch; an LFO with no cables still steps (its page shows it).
  - **A modifier in `bindings.json`**, or a session row in the preset:
    `is_session_row` and the preset's keys are the two gates.
  - **A cycle the sorter misses** (through a macro's depth sub, through a
    `scale` param) or one it refuses that a `delay` breaks.
  - **The GRAPH page and ROUTING disagreeing**: one table, two views;
    add a route on one and it is on the other next frame.
  - **An off effect costing a pass**, or two consumers of one effect
    running it twice; the SYSTEM lines summing to more than the old
    `fx` line within noise.
  - **A placed effect's texture reused while still read** (the pool).
  - **A wire into an output changing another output**, or the session's
    switches being written by a preset load.
  - **The imgui node editor's context** created once, destroyed on
    close and on ⌘R (the restart path destroys the panel), never leaking
    across a hot reload of `ui_graph`.
  - **A preset or `bindings.json` from before this run** loads with no
    note and no dirt; a preset saved by this run loads on the base build
    with only the new keys ignored.
  - **`apc40.py`, `midi.py` and `hyperspace/library/`** unchanged
    (`git diff --stat <base> -- hyperspace-python/hyperspace/apc40.py
    hyperspace-python/hyperspace/midi.py hyperspace-python/hyperspace/library/`
    empty).
- **Re-measure everything on the merged branch.** A sub-agent's green run
  inside its own worktree does not survive integration.
- One final PR from `plan-28-30-integration` to the base decided above,
  titled `Plans 28 and 30: the node editor and shader nodes`. The owner
  merges.

## Gates — all green before any PR

```
uv run pytest -q
uv run ruff check .
uv run pytest tests/test_golden_frames.py -q        # the gate Mac only
HYPERSPACE_FRAMES=120 uv run hyperspace -ApplePersistenceIgnoreState YES
```

Smoke runs, one per stream, windowed, `HYPERSPACE_HOME=<scratch>` with
no `[library]` section: stream D with `palette-hands.json` as the show's
startup preset and the synthetic hand tape (the hands fold, the shape
does not; SYSTEM shows `palette` under `hands`); stream N with a factory
preset, an LFO owning another LFO's depth, two modifiers from the
MODIFIERS strip, the GRAPH page open and a cable dragged (the stall log
empty; the page's draw time on SYSTEM). On this Mac a plain `uv run
hyperspace` can block in `glfwInit` on the "reopen windows?" alert; pass
`-ApplePersistenceIgnoreState YES`.

These must keep passing **untouched**:

- `tests/test_render.py::test_the_render_stack_imports_no_registry`
  (so: no node method named `apply`; `graph.py` imports no `params`).
- `tests/test_outputs.py::test_outputs_imports_nothing_from_app_ui_or_params`.
- `tests/test_hands_boundary.py` (all of it: stream N draws the hands
  device's ports from `hands/device.py`, touching nothing in the
  package).
- `tests/test_routing_boundary.py` (`ABOVE` and `LAZY` as they are;
  `modgraph.py` and `modifiers.py` are leaves below `routing`).
- `tests/test_bridge.py::test_core_does_not_import_the_bridge`,
  `tests/test_dream.py::test_core_does_not_import_the_worker`.
- `tests/test_golden.py`, `tests/test_core.py`, `tests/test_shapes4d.py`.
- `tests/test_graph_json.py` (plan 26 A4): every test as it is; D1 and
  N4 **add** tests beside them.
- Every golden hash in `tests/golden/frames/` as recorded on the base.

These may change **only as this prompt says**, each change named in the
PR body:

- `tests/test_lfo.py:369` and `tests/test_routing.py:1907`: the two lag
  tests become "the same frame" (N0, decision 7).
- `tests/test_app_boundary.py:393` `ORDER`: only the LFOs' step moving
  inside `router.modulate` (N0).
- `tests/test_hotreload.py`: `modgraph`, `modifiers`, `graphview`,
  `ui_graph` added to the watched list in import order (N0, N1, N2).
- `tests/test_golden_frames.py`: the completeness count grows by the
  five fixtures' states (D1, N4); no hash re-recorded.
- `tests/test_fx.py`: the FX page's status line gains the placed count
  (D2).

Invariants that hold throughout: the render stack reads parameters and
never writes one; modulation is non-destructive (`Router.modulate` is
the only caller of `Param.modulate`; `Param.apply` is called by
`Registry.apply` and, from N0, by `Router.modulate` under the frame
mark, nowhere else); no new module imports `torch` outside `dream.py`;
with no `graph` section, no `modifiers` and no `layout`, every output is
byte-identical to the base's goldens, every preset loads as before, and
the only behavioural change is the lag's removal.

---

## What the docs WPs must produce

D3 writes plan 30's, N6 writes plan 28's; the shared files are edited by
whichever lands later, on the integration branch.

- `docs/plans/30-shader-nodes.md` and `docs/plans/28-node-editor.md`:
  each rewritten **as built**, in the shape of `26-render-graph.md` —
  what was built (by WP), what no person has verified, known rough
  edges, the hand-check group and register rows in the intro. Keep this
  prompt file; the docs WPs together update `docs/plans/README.md`
  (this prompt's entry becomes "the launch prompt plans 28 and 30 were
  run from"; the two entries say **built**; `24-party-wishlist.md`'s
  2026-10-16 paragraph says so too).
- `docs/ARCHITECTURE.md` **and `docs/ARCHITECTURE.html`** together: §2's
  frame table (step 9 inside the patch; the one-frame-lag rule replaced
  by the dependency-order rule, with the delay node and the sinks'
  exception restated), §2's drawing subsection (the effect nodes, the
  pipeline end, placement), the line at `:208` ("*modulation* is not a
  graph") removed, §3's control model (modifiers, the `mod` scheme, the
  patch), §5's subsystems (`modgraph`, `modifiers`, `graphview`,
  `ui_graph`); the masthead counts re-measured.
- `docs/ENGINEERING.md`: §2 Rendering (the effect node, the chain as a
  run, placement, the wire list, outputs as nodes, the goldens and the
  five fixtures), §6 The control window (the GRAPH page: nodes, cables,
  layout, tidy, editing, Learn from a port), §9 Learn and routing (the
  patch's order, modifiers, the MODIFIERS strip, the cycle note), §10
  Presets (`modifiers`, `layout`, `wires`), §15 hot reload (the new
  modules), §16 Testing (the headless `graphview` tests).
- `docs/DECISIONS.md` and `docs/DECISION-REGISTER.md`: the sixteen owner
  decisions as rows with Who `owner`; your own from the next free row,
  each under a `## Shader nodes (plan 30)` or `## The node editor (plan
  28)` section and on the answer sheet; rows now superseded (plan 26's
  "wiring choices, not a graph" rough edge; the `Fx` node row; the lag
  rule's rows) marked the way plan 25 marked 78 and 108. "Decided not to
  build" loses its plan 28 line and keeps the GLSL / TouchDesigner one.
- `docs/plans/11-hand-checks.md`: group **X** (plan 30) and **Y** (plan
  28) from the next free number (220 as this is written), in the
  existing format. At least: the three palette placements on the real
  projector and glass; two palettes with different centres on two
  outputs; the FX page's placed chip; the faces target still bending the
  faces; the lag gone on a real LFO-on-LFO patch (watch the SYSTEM or
  LFO page); a hand-energy → smooth → combine → acid-mix patch built on
  ROUTING, then on the canvas, felt with a real hand; a cable dragged on
  the laptop screen at the control window's size; Learn from a port
  completing with the APC40 and with a hand; "hands as lines through the
  acid with tracers" made by dragging and seen on the projector; a hands
  node wired to the glass alone; the APC40 as two nodes with the real
  desk, SHIFT latched and released; a patch saved on one Mac loading on
  the other through the shared library; a preset from before this run
  loading with no note.
- `docs/TESTING-GUIDE.md`: the same checks in plain words, by hardware,
  each ending with its check numbers (the render ones in Part 1; the
  desk ones under Part 2's APC40).
- `docs/CHECKPOINT.md`: "Where the code stands" and "What is left"
  rewritten to be true at the end of this run (plan 29 and the creative
  pass are what is left), short.

## Report back

When the final PR is open, report:

- What landed per WP, with the PR links, and the test count on the
  integration branch against the base's.
- **The goldens.** Confirmation that none of the base's hashes moved,
  and the five fixtures' new frames with their contact sheets' paths. If
  any base frame moved, say so first: that is a bug.
- **The lag.** The "same values one frame earlier" result over every
  factory preset: which params moved earlier, which were identical, and
  any that differed otherwise (none, or a bug named).
- **The patch's cost.** `Router.modulate`'s time per frame before and
  after on party-trip with the hands tape, and the GRAPH page's draw
  time on SYSTEM at the control window's size.
- **The effects' cost.** The SYSTEM per-effect lines summed against the
  old `fx` line on party-acid; an off effect's cost (zero).
- The register rows you opened, each with what it needs from the owner.
- The new hand check numbers and their groups (X for plan 30, Y for 28).
- Confirmation that `hyperspace/library/`, `apc40.py` and `midi.py` are
  byte-identical to the base, and how the desk work's merges were
  resolved.
- Anything you deliberately left undone, anything that contradicts this
  prompt or the design files, and anything a document says that the
  code does not do. If a document says something the code does not do,
  say so rather than quietly matching it.
