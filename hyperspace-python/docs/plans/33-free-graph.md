# Plan 33 — the free graph: effects where they are wired, faces and backdrop as inputs, the FX stack retired

**Status: built (2026-10-24)** on `plan-33-free-graph` (PR #235, into
`plan-31-32-integration` @ 3547a7a; 3516 tests passed, 2 skipped). Designed
with the owner on 2026-10-24 and built the same day, task by task, each
reviewed. **Effects exist only where they are wired.** There is no
`fx.<n>.order`, no `fx.<n>.target`, no `fx.select`, no faces chain and no
order-built stack: each pipeline draws the run `frame → … → fx.image` that
the preset's wires say. The faces (`shape.faces`), the pattern's media
layer (`pattern.media`) and the backdrop (`backdrop.image`) are graph
inputs, so a channel can run through its own shader branch to any of them,
to an output or into another effect's `aux`. A `switch` node picks one of
eight pictures by a modulatable `switch.select`, and only the picked one is
made. GRAPH adds, wires, inserts and reorders effects; the FX page is a
browser of the graph's effect nodes. Every preset made before this plan
loads as the graph it drew: **none of the 661 goldens before it moved**
(693 now: +24 in T4, +8 in T5). A preset the old schema can still say is
saved as before, byte for byte (38 sources in the test); anything else is
`hyperspace.preset/5`, which **an older build refuses**, so both Macs must
run this build before anyone saves a free graph. The build plan was
[`33-free-graph-build.md`](33-free-graph-build.md).

Hand checks: [`11-hand-checks.md`](11-hand-checks.md) group AC, checks
318–328. Decisions: rows 341–352 of
[`DECISION-REGISTER.md`](../DECISION-REGISTER.md) and the "Render graph
without a stack" section of [`DECISIONS.md`](../DECISIONS.md). The
build's rulings (R1–R24) are folded in below where they changed what you
see.

Commits on `plan-33-free-graph`, by task: spec and answers (0ed5929,
e25d600, c7727bd); T1 = the vocabulary (5594905); T2 = the migration and
`/5` (bb8eadd, cb686b3); T3 = the run from wires (622d74f, 5773773,
83c7013); T4 = the faces, the pattern and the backdrop (d7e1ad1); T5 =
the switch (e082929); T6 = GRAPH edits the free graph (424310c, fd17155);
T7 = the FX page and the retirement (adc10d9); T8 = this documentation.

## What was built

### T1 — the vocabulary (`graph.py`, data only)

- New wire ends: `frame` (makes `IMAGE`), `fx.image` (the pipeline end's
  input), `pattern` (makes `IMAGE`, takes `media`), `shape.faces`,
  `backdrop.image`, and `switch[.n].in1` … `in8`. `graph.RESERVED` holds
  the names no effect file may take: `frame`, `fx`, `pattern`, `shape`,
  `backdrop`, `switch`. `graph.SINKS` names the nodes a picture can end
  at (`output`, `fx`, `shape`, `pattern`, `backdrop`, `history`).
- A channel wired into an effect is a **branch**, not a refusal:
  `split_wires` shortens a wire to D1's `after` only when
  `placement_error` allows that place. `media.a → acid.2.image` is now a
  legal section that reaches nothing until something reads it.
- `wire_error` refuses a wire into `fx.image` that does not come from
  `frame` or an effect chain leading back to it, in the words the design
  gave. `SwitchAt` and `NODE_KINDS["switch"]` read a `{"kind": "switch"}`
  node; a switch must be declared before a wire may name it, as a
  composite must.
- `graph.reaches(spec)` is the set of nodes with a path to a sink (it
  also follows an output's `hands` and `readout` ports, the T1 ruling);
  `graph.run_of(spec, head="frame", end="fx.image")` reads a run from the
  explicit wire list.

*At the machine:* nothing yet; this is the words. Tests:
`tests/test_graph_free.py` (the first nine),
`tests/test_graph_json.py::test_the_new_ends_round_trip`.

### T2 — the migration and `/5` (`hyperspace/graphmigrate.py`, `preset.py`)

- `graphmigrate.migrate(doc, specs, desk=)` takes a whole old document and
  returns it with the run and the faces run written as wires, `view.media`
  and `backdrop.channel` as channel wires (or a switch), the switch
  `select` values set, rows retargeted and a list of load notes.
  `to_free` is its section half. `graphmigrate.targets(doc, desk=)` is
  the set of ids any route, desk row, macro, modifier or sequencer step
  drives.
- **Run membership (R5):** an effect is in the run when it is `on` and
  either its `mix` is above 0 or something drives one of its ids. The
  owner's row 346 was about effects toggled off; `presets/dial.json` has
  `acid`, `huecycle` and `kaleido` on at mix 0 and pushed up by axis
  routes, so they stay. An effect that is off stays out, and says so in
  a load note when something drives it.
- **A migrated section always has its head (R9):** `to_free` writes
  `frame → fx.image` even for an empty run, so a migrated section is
  recognisable and an emptied run does not re-grow on reload.
- `specs` is `{name: (@order, @mix)}` read from the effect files (R8), so
  nothing duplicates shader data in Python.
- `graphmigrate.legacy_values(section, values, specs, driven=)` inverts
  it: the `order`, `target`, `view.media` and `backdrop.channel` values a
  `/4` file would carry, or `None` when `/4` cannot say the graph.
  `graphmigrate.needs_free` asks the same of a section;
  `preset.schema_of` writes `/5` first when it is true. `VERSIONS` is
  `(2, 3, 4, 5)`, `FREE_SCHEMA` is `hyperspace.preset/5`.
- `graphmigrate.reordered` (moved here from `fx.py` in T7) keeps orders
  where they already sort right and moves the fewest.

*At the machine:* every factory preset and fixture loads with no note and
draws as before. Tests: `tests/test_graph_migrate.py` (164 tests, among
them `test_every_library_preset_migrates_without_a_note`,
`::test_no_library_preset_routes_an_effect_it_leaves_out`,
`::test_a_driven_effect_on_at_mix_zero_stays_in_the_run`,
`::test_an_empty_run_is_written_as_frame_to_fx`).

### T3 — the run from wires (`graph.py`, `render.py`, `fx.py`, `preset.py`)

- `Wiring.run` holds the run `GraphSpec.wiring()` read with `run_of`;
  `default_graph` builds each pipeline's run from it (a run member whose
  file is gone reads through and says so in `Graph.dormant`). An effect in
  no run and on no reached branch has no node (`_reached_edges`).
  `Effect.on` asks `FxState.live(name)`: `fx.on`, `fx.mix`, the effect's
  own `on` and `mix`, and that it compiled. `Renderer._graph_for` keys on
  the effect files present, not their order, so reordering rebuilds
  nothing it need not.
- **Load** (`Presets.load_doc`) runs `graphmigrate.migrate` on every
  document. **Save** (`Presets.document`): when the section needs `/5`,
  the free section is written; otherwise `legacy_values` is laid over the
  values and `legacy_section` strips every plan-33 word, so a build from
  before this plan never meets `frame` or `fx.image` (R10). An untouched
  `/4`, `/3` or `/2` preset saves **byte-identical**: the test covers 38
  sources (`tests/fixtures/plan33-v4-saves/`, recorded once from the base
  at 3547a7a, force-added because `tests/fixtures/` is ignored).
- **An fx module load replaces the run (R12).** Loading
  `library/fx/<name>.json` migrates the module and replaces the loaded
  graph's main run (and its faces run, if the module has one) with the
  module's, keeping every other wire and branch
  (`graphmigrate.module_runs`, `Presets._fx_module`, `Library.on_apply`).
  The owner's model is "a module is this look's run".
- **Switching an effect on that is in no run adds nothing to the picture
  (R13)** and a later save is `/5`. No factory binding does this.

*At the machine:* a preset looks as it did; toggling a wired effect
changes the picture and nothing else. Tests:
`tests/test_graph_free.py::{test_the_run_order_is_the_wire_order,test_only_wired_effects_have_nodes,test_an_unreached_effect_is_never_run,test_an_untouched_v4_preset_saves_byte_identical,test_loading_an_fx_module_replaces_the_run}`.

### T4 — the faces, the pattern, the backdrop; branches at their size (`graph.py`, `render.py`)

- `PatternNode` (`pattern`: `media` in, a picture out), `BackdropNode`
  (`image` in, the sink) and `Shape.INPUTS = {"faces": IMAGE}`.
  `shape.faces` unwired, wired straight from `pattern`, or fed a source
  that reads nothing draws the faces as before, per face, with no 1024²
  pass. Wired from `pattern` through effects it is the old face-chain
  path: the pattern painted into the first half-float texture
  (`PAINTS`), the effects in turn, the last into `face_pic`
  (`FACE_PIC`² = 1024², now defined in `graph.py`). Wired from anything
  else, that picture at 1024² is `u_pic`.
- A channel wired straight into `pattern.media` is read raw, as
  `view.media` was; a branch is made at its head's size (the channel's
  texture size, else 1024²). A channel straight into `backdrop.image`
  becomes `Wiring.backdrop` and is plan 32's `MediaNode` under the scene
  byte for byte; a branch is laid under the scene in `grounded` by a
  `Composite(under_alpha_of="backdrop_alpha")`.
- **Branches are made once a frame at the size their consumer asks.**
  `Frame.at(size)` is the frame at another size, with its own pool
  (`Renderer.pool_at`) and data keyed `(name, size)`;
  `Node.size_for(port, frame)` (R15) says what a port asks.
  `Graph.at_frame` stops an effect only the faces read being folded at
  the frame's size too. `Renderer._prune_sized` releases a pool or
  texture the last frame did not use.
- A wired effect's clock keeps running in frames its picture is not made
  (R17), the rule placed effects already had.
- `render._face_media` no longer reads `view.media`; the faces' effect
  chain draws nothing (the object itself went in T7).

*At the machine:* the headline graph (`media.a → acid.2 → tripcolour.2 →
shape.faces`; `media.b → kaleido.2 → backdrop.image`) draws. Tests:
`tests/test_graph_faces.py` (nine), `tests/test_media_faces_aux.py`; 24 new
goldens (`media-chain-faces`, `media-chain-backdrop`, `branch-two-sizes`).

### T5 — the switch (`graph.py`, `params.py`, `render.py`)

- `SwitchNode`: eight `IMAGE` inputs `in1` … `in8`, one out, no pass and
  no texture of its own. `index(frame)` is 0–8 from `Frame.selects`
  (out-of-range counts as off); `selected(frame)` is the picked input's
  node, or `None` when off or unwired. Its `image`, `paint`, `alpha`,
  `depth` and `reads` pass the pick through: a **cut**.
- `params.declare_switches(r, names)` declares `switch[.n].select` per
  switch the graph names (enum: off, 1–8; modulatable; group `switch`),
  undeclares those no longer named, and returns the ids that changed. The
  picks live in `ViewState.switch`, read once a frame.
- **Only the selected input runs.** `Graph.pulled(frame)` walks from every
  node with no readers, following each switch's pick only, cached per
  tuple of picks (bounded at 256); `Graph.evaluate` skips a `MAKES` node
  or `Effect` that is not pulled. A channel no picked path reads is not
  uploaded. Changing `select` rebuilds nothing.
- A switch that picks a channel feeding `pattern.media` reads that channel
  raw, exactly as a channel wired straight in; a switch under the scene
  that is off or on an unwired input paints nothing, so the backdrop shows
  nothing.
- **A route onto the old channel choice becomes a switch (R14, R19).** An
  old preset whose `view.media` or `backdrop.channel` is driven loads
  with a switch (`media.a … media.h` into `in1 … in8`, the switch into
  `pattern.media`), the pick at the old value and the rows retargeted to
  `switch.select`. Saving it writes `/5`, since `/4` cannot say a switch.
  Two fixtures (`tests/fixtures/plan33-driven/`) hold this; the other 38
  stay byte-identical.

*At the machine:* a knob on `switch.select` changes which channel the
faces show, as a knob on `view.media` did. Tests:
`tests/test_graph_switch.py` (twelve, among them
`::test_only_the_selected_input_is_made`,
`::test_select_changes_do_not_rebuild_the_graph`,
`::test_a_route_drives_select`); 8 new goldens (`switch-faces`).

### T6 — GRAPH edits the free graph (`graphview.py`, `ui_graph.py`)

- The canvas draws `frame` (a stand-in, whenever the run comes from the
  section's wires), `pattern` and `backdrop` (always, like the channels),
  the switches, and the `shape.faces` port. Each pipeline's picture enters
  `frame` on a display-only `feeds` cable. Areas: `pattern` in GEOMETRY;
  `backdrop` and `switch` in MEDIA; `frame` and `fx` in SHADERS. An
  effect or switch made of the media alone (`media_made`) is placed in
  MEDIA, so `media.a → acid.2 → huecycle.2 → shape.faces` runs MEDIA →
  GEOMETRY and the layout rule "no cable runs back" holds (a shader back
  into the faces included).
- The right-click picker adds an effect or a switch **unwired**, where the
  menu opened: faint, "reaches nothing" (`REACHES_NOTHING`). An effect
  dropped on a render cable is **inserted** (`Edit.insert_effect(cable,
  file)`); right-click on a render cable offers "insert effect ▸ <file>".
  **Reordering is dragging an effect onto another cable** (R22):
  `Edit.place_effect(cable, name)` lifts it out of where it is (the run
  closes over the gap) and puts it on the new cable, in one undo step. A
  node dropped back where it was, or on empty canvas, does nothing.
- Deleting a run cable lifts the effect it led into; the run closes up.
  **Deleting `frame → fx.image` is refused (R20)** in words: "the run
  starts at frame and ends at fx.image — insert effects into it".
- **An unwired instance 1 stays in the section (R21)**:
  `{"kind": "effect", "file": f}` with no instance key. Taking `acid` out
  of the run leaves it faint and "reaches nothing", not gone, and the
  section saves as `/5`; one undo puts it back.
- A compile error colours the effect node's title and is its hover.
  `ui_graph.select_effect(panel, name)` and `Panel.fx_selected` are the
  one selection shared with the FX page.

*At the machine:* all of the above, by mouse. Tests:
`tests/test_graph_edit.py::{test_insert_effect_on_a_render_cable,test_reordering_the_run_is_rewiring,test_an_instance_one_effect_taken_out_of_the_run_stays_faint,test_dragging_a_run_member_onto_another_cable_moves_it}`,
`tests/test_graph_areas.py` (the four `/5` fixtures back in),
`tests/test_graphview.py`.

### T7 — the FX page browses the graph; the stack retired (`ui_fx.py`, `fx.py`, `graph.py`)

- `ui_fx.groups(spec)` lists every effect instance in the loaded graph,
  grouped by where its path ends: **Run** (wire order), **→ faces**,
  **→ pattern media**, **→ backdrop**, **→ output N**, **→ <effect>
  aux**, any other end (history, a D1 `after`), and **reaches nothing**
  last. An effect that ends in two places is listed in each. Each row is
  a name, an `on` check, a small `mix` and one state word (`running`,
  `off`, the `why_idle` reason, or `error: …`). Clicking a name opens its
  strip; **Show on GRAPH** selects and centres it. The `→ faces` header
  carries `fx.face_map`. The page edits no structure. With nothing in the
  graph it says "no effects in the graph — add one on GRAPH (right-click
  the canvas)".
- **Removed from `fx.py`:** the `order` and `target` params,
  `fx.select`, `TARGETS`, `FRAME`, `FACES`, `chain()`, `FxChain.run`,
  `begin`, `active`, the faces chain's program borrowing. `@order` is
  still parsed (`EffectSpec.order`), read only by the migration; the
  module docstring and `_lib.glsl` say so. `RESERVED` keeps `order` and
  `target` so an old preset's `fx.<n>.order` is not read as a uniform.
  Removed from the FX page: the chip grid and its drag, the placed grid,
  the order slider, the ONTO chips, the faces line.
- **R23:** with the order-built stack gone, `Wiring.run is None` means
  the empty run (`frame → fx.image`). Rigs and tools that relied on the
  fallback get their run through `graphmigrate.wiring_for` (the same path
  a load takes), and the golden tool's states keep the run the load
  migrated. Three demo tools of the retired UI were deleted:
  `tools/fx_page_demo.py`, `tools/face_target_shots.py`,
  `tools/fx_faces_scene_shots.py`.
- `view.media` and `backdrop.channel` are no longer params. Their readers
  follow the wires (`graph.source_into`, `graph.channel_into`, through a
  switch's pick): the FACES page tiles, the MEDIA page (its pickers row is
  words such as "channel C (switch)", with "wired on GRAPH" in its note)
  and Learn (`learn.cannot_show`). An old preset's two values still
  migrate, and a `/4` save writes them back where the base build put them
  (`graphmigrate.landed_retired`, `with_retired`).
- `render_drop("acid")` no longer says "always in the chain": instance 1 is
  dropped like any instance. GRAPH's picker on a section with no run gives
  it the bare `frame → fx.image` (`graphview._with_run`).
- 30 stack-only tests were deleted (named in adc10d9's message) and 17
  added; the pure-wire behaviour that survived was rewritten, not dropped.

*At the machine:* the FX page is a list to pick from and play. Tests:
`tests/test_fx.py::{test_groups_follow_the_wires,test_the_fx_page_lists_the_graphs_effects,test_show_on_graph_selects_the_node,test_the_retired_ids_are_gone,test_an_old_preset_loads_its_retired_ids_without_a_note,test_an_old_preset_saves_its_retired_ids_back_where_they_were}`.

## What no person has verified

Every headless test passes (3516 passed, 2 skipped on the build machine,
an M3 Max, with the 693 goldens); no person has run any of it. In
particular:

- **Every gesture on GRAPH** (318, 320, 325, 326): a drag onto a cable, a
  near miss beside one, a right-click's subject, the faint node's look.
  The tests drive `Edit` and `ui_graph.dropped` and draw the widget
  headless; none moves a mouse.
- **The headline graph by eye** (318): the goldens were checked on one
  still each; the look of a clip through two effects on the faces, and a
  camera through `kaleido` behind the scene, is for the owner.
- **A knob on `switch.select` on a real APC40** (319): the test drives a
  route from a synthetic LFO. The feel of a cut on a knob, and whether
  eight positions on a continuous knob are easy to hit, is not tested.
- **The FX page at distance with a big graph** (327), and its grouping
  read against the GRAPH canvas.
- **An old party preset by eye and on the second Mac** (322, 328): the
  goldens pin 661 pictures on the gate Mac's GL and the byte test pins
  the save; nobody has opened a `/5` file on an older build (the ladder
  refusal is tested with the loader, not the old app).
- **A channel lost mid-show** (323): the tests make a source read nothing;
  a real NDI feed or camera going away, and the faces falling back to the
  pattern for that frame, have not been seen.
- **The frame cost** (324): two branches, the faces branch (a 1024² pass
  per effect) and an eight-way switch were counted in makes, never timed
  on a tile GPU.
- **Hot reload of a registry from before T5** (R24): switches read off
  until a restart; a developer matter only.

## Known rough edges

Behaviour the owner will meet:

- **A pad or key that switches on an effect in no run does nothing (R13)**
  and a later save is `/5`. No factory binding does it. The FX page lists
  only the graph's effects, so there is nowhere to find such an effect.
- **A person's own preset that drives a channel choice saves `/5` after
  its first re-save (R19)** and is unreadable on an older build then. None
  is in the library.
- **An fx module load replaces the run (R12)**; it does not append. A
  look-module applied over a hand-built run loses that run (branches and
  placements survive). Undo restores it.
- **Deleting `frame → fx.image` is refused (R20).** To empty the run, take
  the effects out one at a time.
- **A wired effect's clock runs while its picture is not made (R17)**,
  so a long-idle effect jumps phase when it comes back. An unpulled
  effect behind an unselected switch input is different: its clock stands
  still. The two rules differ (T5 minor, undecided).
- **A near-miss drag (R22)** can surface refusal notes such as "x is no
  picture cable" in the footer. Check 325 asks whether that is noise.
- **`render_add` numbers `max(existing) + 1`**, so re-adding a dropped
  instance 1 makes `acid.2`.
- **A backdrop branch has one extra reader**, so one extra pool texture a
  frame (T4 minor). A branch is never over 1080p (R18: plan 32's caps
  decode files at 1920×1080 and live at 1280×720).
- **A `/4` save after a reorder writes the moved effect's `order` as an
  int among floats.** Reads back the same.
- **A pattern layer's first upload** is no longer in the scene's timing
  line on SYSTEM.

Code the next person will meet (deferred minors from the reviews):

- `wire_error`'s port-list truncation is keyed on `len(takes) < 4`
  rather than on the switch (T1). `run_of` returns `()` both for no run
  and for an empty `frame → fx.image` run (T1).
- `test_no_existing_preset_changes_schema` has a weakening `or` clause
  (T2). `_watch_fx_modules()` is called from `load_doc` on every load, and
  its hot-reload test simulates rather than exercising `test_hotreload`
  (T3).
- `Renderer._frame_target` / `pool_at` use `__dict__.setdefault` where the
  file otherwise uses `getattr`; a solid geometry's draw raising between
  `prepare` and `draw` leaves a stale `r._face_layer` (T4).
- `Graph.pulled` treats an `after`-only reader as a root (conservative; to
  be commented); no test that a route or desk row on a removed
  `switch.<n>.select` goes dormant without raising; `MAKERS` sits
  mid-file (T5).
- `graphview.cable_near` reuses `d` for an id and then a distance and
  shadows `a`, `b`; `returns()` has a long `and`/`or` condition (T6).
- `ui_fx` imports the private `graph._PICTURE_PORTS` and `preset` the
  private `library._module_values` (public aliases wanted);
  `ui_fx.groups()` is computed twice a frame (the page and the strip's
  `_where`) and again in GRAPH's side pane; `learn.cannot_show`'s
  media-`None` fallback reads `off("view.media")`, dead in practice (T7).
- `tests/test_presets.py::test_active_follows_the_loaded_preset_from_one_place`
  failed once in the middle of T7 while `ruff --fix` ran over the tests;
  it passes alone and in the final run. Watch for a flake.

## The design, as agreed (2026-10-24), corrected where the build differs

Where the build differs from the text below:

- **Reserved names** are `frame`, `fx`, `pattern`, `shape`, `backdrop` and
  `switch` (the design named the first three).
- **Instance 1 can be unwired** (R21): the design's "instance 1 is the
  file itself, always there" belonged to the retired stack.
- **Run membership** is `on` and (`mix > 0` or driven), not `on` and
  `mix > 0` (R5).
- **A module load replaces the run** (R12); the design did not say.
- **The retired values are not only dropped:** a save below `/5` writes
  them back where the base build put them (`with_retired`), which is what
  keeps the 38 sources byte-identical.
- **`backdrop.alpha`'s owner** on GRAPH is the `backdrop` node, not the
  composite.
- The risk "about 31 of `test_fx.py`'s tests are rewritten, not deleted":
  30 were deleted as tests of removed UI or of the stack alone (named in
  adc10d9), the rest rewritten.
- The design's wire `frame → fx.image` for an empty run is always present
  (R9, R20), so a section with no effect still has one wire.

The render graph stops being "today's frame, patched". An effect exists
where it is **wired** and nowhere else: no `order`, no `target`, no
implicit stack every effect file sits in. The **faces** on the geometry
and the **backdrop** become graph inputs, so a channel can run through
its own shader branch and land on the faces, behind the scene, on an
output, or into another effect's `aux`. A **switch** node picks one of
its inputs by a param, so a knob still chooses which channel the faces or
the backdrop read. The FX page's linear stack is retired: GRAPH is where
effects are added, wired and reordered, and the FX page becomes a
**browser of the effect nodes in the graph** — a list, grouped by where
each one sits, to pick one and play its params. Every preset made before
this plan loads as the graph it always drew: **no existing golden moves**.

Design agreed with the owner on 2026-10-24 (this file); the build plan
is [`33-free-graph-build.md`](33-free-graph-build.md). Base: branch
`plan-31-32-integration` @ 3547a7a (plans 31 and 32 together, preset
schema `/4`, 661 goldens, register rows to 340, hand checks to 317).

This is also the plan 32 spec's "plan 33" (the compositing
reconciliation, row 330): once the frame is wires, the compositing order
*is* the default graph, and changing it is a graph edit. Settling the
factory default order with the owner stays a session of its own (Not in
this plan).

## What the owner wants (2026-10-24)

> A really common use case that we're going to have here is to take an
> arbitrary piece of media from the media bus (like one of the lettered
> channels) and then pipe that through its own shader pipeline. Then take
> the image output from that and feed it into somewhere, whether it be
> the faces on geometry or whatever the interface outside of the graph
> makes. […] The graph itself is trying to represent the kind of linear
> workflow model that we have with all the old control panel stuff. […]
> The FX tab has a linear shader setup in it. That is kind of the
> antithesis of what I want here because it's very rigid. It doesn't let
> me just compose shaders together onto arbitrary bitmaps.

> Retire the main chain fx stack, we can edit it directly in the graph.
> And I'm fine with one input for all faces right now, per instance is
> the next place I would go with this though.

> If a switch node would be the right solution for long-term use, it can
> be added to this plan. Effects that are toggled off right now really
> are not used in any presets. […] I think the FX page can stay. It
> should be used as an easy way to view all the parameters for a given
> FX, like a given node in the graph that would be under the FX umbrella
> today. That tab should be where you can go and look at a list of the
> existing nodes in the graph that are "FX", and then choose which one
> you want to mess with and control it that way. That's what I see this
> control panel being more of: a kind of dynamic representation of the
> things that are in the graph. It's kind of like a file explorer way of
> exploring what is in the graph.

## Why the graph cannot do it today

Read off the base, so the build knows what it is replacing:

- **The frame is fixed; the preset patches it.** `graph.default_graph`
  builds scene → look-back → effect run → pipeline end (`fx`) → outputs
  from `Wiring`; a preset's `graph` section adds placements, wires and
  composites to that. Every effect file (and every instance) has a node in
  every pipeline's run at its `fx.<n>.order` whether it is on or not
  (`default_graph`'s `run(key, src)`); `Effect.on` asks
  `FxState.chain(FRAME)`.
- **A channel cannot feed an effect on its own.** `split_wires` reads an
  effect with one wire in and none out as D1's `after <src>`, and
  `placement_error` refuses `media.a` as a place: `media.a → acid.2.image`
  is a `GraphError` and the whole section falls back to the default graph
  with a note. (A wire on to `output.N.image` gets past this; nothing else
  does.)
- **The faces are not a graph input.** `Renderer._face_media` draws the
  raw texture of the channel `view.media` names; `_face_picture` runs the
  one faces chain (`face_fx`, every effect whose `target` is `faces`, in
  `order`) over the pattern + media seed into a 1024² picture
  (`FACE_PIC`). One chain, global, not wireable.
- **The backdrop is a param.** `backdrop.channel` → `Wiring.backdrop` →
  `MediaNode(alpha_of="backdrop_alpha")` under the scene in the
  `grounded` composite.

Already there and kept: effects as image nodes with an `aux` port (plans
30, 32), wires and composites in the preset (plan 28 N4), a media node
that materialises once a frame when read (`MediaNode.MAKES`), painted vs
made pictures and the `_spare` pool, the GRAPH canvas with its render
cables, undo for graph edits, the per-pipeline runs.

## The words

- **Run** — the effects wired one after another from `frame` into
  `fx.image`. Each pipeline (scene, scene+hands, hands) draws the run on
  its own picture, as each draws the chain today.
- **Branch** — any other wired path of effects and composites: from a
  channel, the `pattern`, the scene, the history, another effect.
- **Sink** — a node that takes a picture and puts it somewhere outside the
  graph: an output, the faces (`shape.faces`), the pattern's media layer
  (`pattern.media`), the backdrop (`backdrop.image`), the history, the
  pipeline end (`fx.image`).
- **Unreached** — an effect or composite no path leads from to a sink. It
  is kept in the preset, drawn faint on the canvas with "reaches nothing",
  and never run.
- **Switch** — a node with eight picture inputs and one `select` param
  (off, 1–8): its picture is the selected input's, passed through.

## The shape in one paragraph

Four new wire ends turn the old params and the stack into wires. `frame`
is a source: the pipeline's picture before its effects (the look-back's
composite on the scene pipelines, the hands' layer on the hands one).
`fx.image` is the pipeline end's input. A preset's main run is
`frame → acid.image`, `acid → wobble.image`, `wobble → fx.image`; with no
run, `frame` goes straight to `fx`. `pattern` is a new node: the face
pattern (and its media layer) as a picture, with an `image` input `media`
where `view.media` used to choose a channel. `shape.faces` is the faces'
one input: unwired, the faces draw the pattern as today. `backdrop` is a
new node whose `image` input takes the place of `backdrop.channel`. The
owner's headline graph is then `media.a → acid.2 → tripcolour.2 →
shape.faces`, or `media.b → kaleido.2 → backdrop.image`, and any branch
may also feed an effect's `aux`, a composite or an output. To choose the
faces' channel from the desk, the eight channels go into a `switch` and
the switch into `pattern.media`; a knob on `switch.select` does what a
knob on `view.media` did.

## Components

### G — the vocabulary (`graph.py`, data only)

- **New wire ends.** `frame` (makes `IMAGE`); `fx.image` (takes `IMAGE`;
  the scene pipeline's end is already named `fx`, `FX_NAMES`);
  `pattern` (makes `IMAGE`, takes `media: IMAGE`); `shape.faces` (takes
  `IMAGE`); `backdrop` (takes `image: IMAGE`, makes nothing). `frame`,
  `pattern` and `backdrop` are reserved names (no effect file may take
  them; there is none today).
- **No wire shortens to a placement any more** when its source is not a
  D1 place: `media.a → acid.2.image` alone is a branch (unreached until
  something reads it), not a refusal. D1's `after` / `into` keep their
  meaning for files that use them.
- **Into `fx.image`** only from `frame` or from an effect whose `image`
  chain leads back to `frame` (an `aux` may come from anywhere). Anything
  else is refused in words: "fx.image takes the run from frame; to replace
  an output's picture wire it into output.N.image".
- **One place per effect instance**: an instance has one `image` input,
  so it sits in the run or on one branch, never both (as today).
- **Loops** are refused in words, as today's `wire_loops`.
- `reaches(spec) -> set[str]`: the nodes with a path to a sink, for the
  render and the canvas's faint drawing.

### R — the render side (`graph.py`, `render.py`, `fx.py`)

- **The run from wires.** `default_graph` builds each pipeline's run from
  the wires `frame → … → fx.image`, not from `FxState.names()`; an effect
  in no run and on no reached branch has no node. `Effect.on` asks only
  `fx.on`, `fx.mix`, the effect's own `on` and `mix` and that it compiled
  (`FxState.live(name)`): no target, no order. The graph's rebuild key
  takes the effect files present, not their order.
- **Branches are made once a frame** at the size their consumer asks, and
  shared: `Frame.data` keyed by `(name, size)`; a node read at two sizes
  is made at each. The frame-size consumers (an output, a composite, the
  backdrop, the history, `fx`, an `aux`) ask the frame size; `shape.faces`
  asks `FACE_PIC`²; `pattern.media` asks its head's own size (a channel's
  texture size, aspect kept as `view.media_scale` expects). An effect asks
  its input for the size its own consumer asked.
- **The faces.** `shape.faces` unwired, or wired straight from `pattern`:
  the faces draw as today, per face, with no 1024² pass (every golden
  without a face effect draws this way). Wired from `pattern` through
  effects: today's face-chain path (`pattern` made at `FACE_PIC`, the
  effects one after another, the result bound as `u_pic`, mapped per face
  or in screen space by `fx.face_map`). Wired from anything else: that
  picture at `FACE_PIC`² as `u_pic`. A head that reads nothing (a missing
  or lost channel) makes transparent black, and the faces show the pattern
  for that frame instead of going black.
- **The pattern's media layer.** `pattern.media` wired straight from a
  channel: the raw channel texture as today (`_face_media`). From a branch:
  the branch's picture at its head's size. `view.media_alpha / scale /
  mode / amp / rate` stay the layer's params.
- **The backdrop.** `backdrop.image` wired straight from a channel: today's
  `MediaNode(alpha_of="backdrop_alpha")` under the scene (byte for byte).
  From a branch: the branch's picture at the frame size, laid under the
  scene in `grounded` with `backdrop.alpha` applied by the composite.
  `backdrop.alpha` and `backdrop.history` stay params.
- **The faces chain as a separate one-block ping-pong goes**
  (`FxChain.run`, `face_fx`, `chain(FACES)`): the faces' effects are graph
  nodes like any other.

### S — the switch (`graph.py`, `params.py`, `render.py`)

- **The node.** Kind `switch`, instances `switch`, `switch.2`, … by the
  naming rule (ENGINEERING §2). Eight `IMAGE` inputs `in1` … `in8`
  (`switch.2.in3` as a wire's end), one `IMAGE` out. Its picture is the
  selected input's, passed through at the size its consumer asks: no pass,
  no texture of its own. A **cut**, no crossfade (row 352).
- **The param.** `switch[.n].select`: an enum, off / 1–8, modulatable —
  a route, a desk row, a macro, an LFO or a sequencer step can drive it
  like any param. Declared per instance from the preset's graph, as the
  effect instances are (`set_instances`); saved with the preset's values.
- **Only the selected input runs.** A branch behind an unselected input
  is not made that frame, and a channel no selected path reads is not
  uploaded (plan 32's upload rule holds through a switch). Changing
  `select` never rebuilds the graph. The selected input unwired, or
  `select` off, reads nothing: the faces show the pattern, the backdrop
  shows nothing.
- On GRAPH the inputs are the node's port rows, the selected one marked;
  the switch sits in the MEDIA area beside the channels.

### M — the old presets (`hyperspace/graphmigrate.py`, `preset.py`)

- **Load.** A preset whose `graph` section has no `frame`/`fx` run is
  given one from its values: the effects aimed at the frame, not placed or
  wired by the section, that are **on with mix > 0**, in today's
  `(order, name)` order (row 346: effects that are off are not used by any
  preset, and nothing binds them). The same for the effects aimed at the
  faces, as `pattern → … → shape.faces`. `view.media = k` becomes
  `media.<c> → pattern.media`, `backdrop.channel = k` becomes
  `media.<c> → backdrop.image`. An effect left out was off, so it drew
  nothing: the picture is the same.
- **A route onto a channel choice becomes a switch.** When anything (a
  route, a desk row, a macro, a modifier, a sequencer step) drives
  `view.media`, the migration wires `media.a … media.h` into a new
  switch's `in1 … in8`, the switch into `pattern.media`, sets
  `switch.select` to the old value and retargets those rows to
  `switch.select`; the same for `backdrop.channel` with its own switch.
  None in the library does this; the migration exists so a person's own
  preset keeps its knob.
- **Retired values** (`fx.<n>.order`, `fx.<n>.target`, `fx.select`,
  `view.media`, `backdrop.channel`) are read by the migration and then
  dropped.
- **Save: the lowest schema that loses nothing** (row 340's rule). A graph
  `/4` can say — one run from `frame`, at most one faces run from
  `pattern`, `pattern.media` and `backdrop.image` fed straight by a
  channel or not at all, no unreached node, no effect switched on outside
  a run — is written as `/4` (or lower) with `order` / `target` /
  `view.media` / `backdrop.channel` values and no new vocabulary, the orders
  kept where they already sort right (`fx.reordered`). Anything else is
  `hyperspace.preset/5`. A `/4` preset loaded and saved untouched is
  byte-identical.
- No file under `hyperspace/library/` is edited (as plans 26–32): the
  factory presets go through the same load. `mandala`'s
  `fx.kaleido.order = 8` is read there.

### U — the panel (`ui_fx.py`, `ui_graph.py`, `graphview.py`)

The owner's direction for the control panel: **a page is a view of what
is in the graph**, a file explorer over its nodes, not a second place the
structure lives. This plan does it for the FX page; the other pages keep
their shape (Not in this plan).

- **The FX page: a browser of the effect nodes in the graph.** It lists
  every effect instance in the loaded graph — in the run, on a branch,
  unreached — grouped by where its path ends: **Run** (in wire order),
  **→ faces**, **→ pattern media**, **→ backdrop**, **→ output N**,
  **→ <effect> aux**, **reaches nothing** last. An effect that feeds two
  places is listed under each. Each row: its name, an `on` toggle, a small
  `mix`, and its state in a word (running, off, idle — why, as
  `ui_fx.why_idle` says now — or the compile error). Clicking a row opens
  its **strip** below the list: every param of that node (`on`, `mix`,
  `speed`, `blend` and each uniform). **Show on GRAPH** selects and
  centres it on the canvas. The selection is one panel state shared with
  GRAPH's side pane, so picking a node on either page picks it on both.
  The head keeps `fx.on` and `fx.mix`; the **→ faces** group's header
  carries `fx.face_map`. The page adds, removes, wires and reorders
  nothing: that is GRAPH's.
- **Gone from the FX page:** the chip grid and its drag-to-reorder, the
  placed grid, the order slider, the ONTO chips, the faces lines,
  `fx.select`.
- **On GRAPH:** `frame`, `fx`, `pattern`, `backdrop`, the switches and the
  faces port are drawn like the other render nodes (`pattern` and
  `backdrop` always, as the media channels are). The right-click picker
  adds an effect or a switch **unwired** (faint, "reaches nothing") where
  the menu opened. An effect node dropped on a render cable is
  **inserted** into it (as a modifier dropped on a value cable is,
  `ui_graph.dropped`); right-click on a render cable offers "insert effect
  ▸ <file>". Reordering the run is rewiring or dragging a node to another
  cable. A selected effect's side pane is the same strip as the FX page's.
  A compile error colours the effect's node title and is its hover.

## Not in this plan

- **Per-instance faces** (the owner's next step): a picture per shape
  instance or per face group. The port is named `shape.faces` so a later
  plan can add `shape.faces.<k>` or an assignment node without a schema
  change; wires are already a list.
- **The other pages as views of the graph** (the owner's direction, U):
  MEDIA, FACES, LOOKBACK and OUTPUT listing their nodes the way the FX
  page will. Each is its own small plan once this one shows the pattern.
- **A crossfading switch** (a `fade` time on the switch): a cut first.
- **The compositing order** of the default graph (look-back, backdrop,
  effects, hands) with the owner: a session of its own on top of this.
  The default graph keeps plan 32's order.
- New effects, the `VALUE` port, desk / APC40 defaults (`apc40.py`,
  `midi.py` untouched; the desk and faders are Dylan's).

## Risks

- **The goldens are the contract.** Every factory preset and fixture must
  migrate to a graph that draws the same pixels; the build runs all 661
  after each render task. A miss is a migration bug, not a re-record.
- **Two Macs, one library.** A `/5` preset refuses to open on an older
  build (the schema ladder does its job); the save rule keeps every preset
  that does not need `/5` readable there.
- **An off effect a preset does switch on.** The owner's reading is that
  none does (row 346); a test fails the build if any library preset
  routes an effect the migration leaves out, so a surprise is found, not
  shipped. A person's own preset with such a route loses that effect and
  says so in a load note.
- **A switch must not make what it does not show.** The cost win of a
  switch over eight wired channels depends on unselected branches not
  running; a test counts the makes.
- **Frame cost.** A branch is one more made texture per frame per size;
  the faces through a branch add today's 1024² face-chain cost. Fewer
  effect nodes overall (only the wired ones, not 13 per pipeline).
- **Tests built on the stack.** About 31 of `test_fx.py`'s 68 tests and
  20 of `test_render.py`'s face-chain tests assert order, target or the FX
  page. They are rewritten against wires, not deleted, where the
  behaviour survives.

## Decisions

Rows 341–352 of [`DECISION-REGISTER.md`](../DECISION-REGISTER.md), with what
was built against each. "(owner)" is answered in the owner's words;
"(rec)" is a recommendation **accepted by the owner on 2026-10-24**
("accept the rest of the recs, start building").

341. **Retire the FX stack** (owner, 2026-10-24): no `order`, no `target`,
     no FX page; effects are edited on GRAPH.
342. **One picture input for all faces** (owner, 2026-10-24):
     `shape.faces`. Per instance is the next plan.
343. **The run is wires from `frame` to `fx.image`, drawn by every
     pipeline** (rec). Other: a run per pipeline in the preset.
344. **A `pattern` node with a `media` input replaces `view.media`;
     `shape.faces` unwired draws as today** (rec). Other: the media layer
     dropped, a composite over the pattern instead (loses the layer's
     scale and orbit).
345. **A `backdrop` node with an `image` input replaces `backdrop.channel`;
     `backdrop.alpha` and `backdrop.history` stay params** (rec).
346. **The migration keeps only the effects that are on (mix > 0)**
     (owner, 2026-10-24: "effects that are toggled off right now really
     are not used in any presets"). Others: also keep those a route can
     turn on; keep every effect, off ones read through.
347. **Save writes the lowest schema that loses nothing; `/5` only for a
     graph `/4` cannot say** (rec). Other: always `/5` (both Macs must
     update at once).
348. **The FX page stays as a browser of the effect nodes in the graph**,
     grouped by where each sits, a row picked to play its params; it edits
     no structure (owner, 2026-10-24: "a file explorer way of exploring
     what is in the graph"). Other: remove the page, the strip in GRAPH's
     side pane only.
349. **An unreached effect is kept in the preset, drawn faint, never
     run** (rec). Other: drop it on save.
350. **A switch node in this plan**: eight inputs, `switch.select`
     modulatable; a route on `view.media` or `backdrop.channel` migrates to
     one (owner, 2026-10-24: "it can be added to this plan"). Other: no
     switch, such routes dropped.
351. **The default graph keeps plan 32's compositing order** (rec); the
     reconciliation is its own session.
352. **The switch is a cut, eight inputs, only the selected one runs**
     (rec). Others: a crossfade time; a variable input count.
