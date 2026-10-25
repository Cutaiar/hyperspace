# Plan 35 — the free frame: every node of the frame an ordinary node, outputs that show what is wired, a blank preset

**Status: built (2026-10-25)** on `plan-34-feedback` (PR #236; cut at plan
34 T3, ce0b0c6, 717 goldens; 3925 tests passed, 2 skipped, 741 goldens: the
717 unmoved and 24 new). Designed with the owner on 2026-10-24 and built
task by task, each reviewed. **Plan 34 was paused after its T3** and
resumed on this model: its T4–T6 (the resize, GRAPH, the docs) are built
(a78bb4a..; "What changes for plan 34"), 3953 tests passed, 2 skipped and
757 goldens with plan 34's T4 (the 741 below are plan 35's own count; T4
adds 16). Preset schema is
`hyperspace.preset/6` for the new vocabulary (the node ids are renamed);
a save writes the lowest schema that loses nothing, so an untouched `/4`
preset is byte for byte as before and `/5` stays `/5` where it can (R10).
**An older build refuses a `/6` file, so both Macs must run this build
before anyone saves one.** Hand checks [`11-hand-checks.md`](11-hand-checks.md)
group AE, checks 342–352; register rows 372–393 of
[`DECISION-REGISTER.md`](../DECISION-REGISTER.md) and the "The frame as
wires" section of [`DECISIONS.md`](../DECISIONS.md). The owner answered the
three questions on 2026-10-24: row 373 "approve, but rename ids too",
rows 374 and 387 approved as proposed. Every other decision was a
recommendation the build took. The build plan is
[`35-free-frame-build.md`](35-free-frame-build.md).

What this plan does:

- **The frame is wires.** The shape, the scene, the hands, their layer
  and guide, the backdrop, the look-back and the outputs are ordinary
  nodes, wired like an effect. Each one can be deleted and rewired on
  GRAPH. The only refusals left are type errors, loops, and the rig's own
  nodes (a window, a cloud device, the camera). `frame`, `fx`, `grounded`,
  `capture`, the pipelines and their per-pipeline copies stop being
  nodes.
- **An output shows what is wired into it.** Its `image` port is its
  picture, `hands` is laid over that, and `guide` goes over everything.
  An output with nothing wired shows its ground: black, or see-through in
  overlay. A new node, **All outputs** (`output.all`), is what every
  output shows unless its own port is wired. One preset then looks right
  on the laptop (one window) and on the rig (two).
- **Old presets migrate** to the explicit wiring that `default_graph`
  builds for them today. Every golden stays put, and an untouched `/4`
  preset saves byte for byte as before.
- **A new preset button** on the PRESET strip starts at the factory
  values with an empty graph, so it draws black until something is wired
  to an output.
- **Names a performer reads.** Every node gets an id, a display name and
  a one-line hover in the owner's primitives (scene, hands, look-back,
  backdrop, faces, channels, effects, outputs): `history` is `lookback`,
  `ghost` is `hands`, the hands' layer `hands.layer`, the readout
  `hands.guide`, `media.a` is `channel.a`. Params keep their ids. The
  canvas is grouped by those primitives.

## What was built

Built task by task on `plan-34-feedback` (T1–T7, each reviewed; T3, T5
and T6 took a fix round). Commits, by task: spec and answers (51ef105);
T1 = the wired frame as words (ab7caf2); T2 = the builder and today's
frame as wires, proved node for node (0cbbc15); T3 = every preset loads as
a wired frame, `/6`, the golden states as wiring (e86cacd, fixes 4d1d570);
T4 = the pipelines retired (3c97aa4); T5 = GRAPH deletes anything, names
and areas by primitive (3b3f7f4, 2ea5c8f, fixes 9d0cec9, 983495b); T6 =
OUTPUT and LOOKBACK as views of the wires (18b1215, fix 13a1633); T7 = the
new preset (5226e5e); T8 = this documentation. 3925 tests passed, 2
skipped (the base was 3608). **None of the 717 goldens before the plan
moved; 24 are new (741).** Plan 34 was paused after its T3 (ce0b0c6) and
resumed on this model ("What changes for plan 34" below); it is built, and
with its T4 the goldens are 757.

The owner's answers on 2026-10-24: row 373, "approve, but rename ids
too" (done: `ghost` → `hands`, the layer → `hands.layer`, `readout` →
`hands.guide`, `history` → `lookback` with `capture` merged in,
`media.<c>` → `channel.<c>`, `eye` → `camera`; params keep their ids,
`graph.param_prefix`); row 374, the per-output switches, as proposed
(picture and hands are each window's mutes, "through" is wiring); row
387, the new preset, as proposed (outputs only, nothing wired, plus a
"scene starter" item).

### T1 — the wired frame as words (`graph.py`, `graphmigrate.py`)

- The marker `"frame": "wired"` (`graph.FRAME_KEY`, `WIRED_FRAME`), read
  by `read_graph`; the frame kinds (`scene`, `shape`, `backdrop`,
  `pattern`, `lookback`, `hands`, `hands.N.layer`, `hands.N.guide`) as
  ordinary node entries (`graph.FRAME_KINDS`); `copy` (`CopyAt`, with its
  `of`); `output.all` and the ports `image`, `hands`, `guide`; `ground`,
  a source word that goes only into output ports.
- The ids and their two-way map: `graph.new_id` / `old_id` /
  `param_prefix`, `NEW_IDS` / `OLD_IDS`. An old id in a wired frame is
  refused in words (`OLD_ID_IN_A_WIRED_FRAME`). `frame` and `fx` are
  "gone in a wired frame" (`GONE_IN_A_WIRED_FRAME`); `holds` and `into`
  are wires (`HOLDS_IS_A_WIRE`, `INTO_IS_A_WIRE`).
- Several wires into `scene.geometry` stand in section order. Geometry
  goes only into the scene (`GEOMETRY_INTO_SCENE`; R3: into an output
  port it gets the type words instead).
- `graph.reaches` in a wired frame runs from every sink port: an output's
  `image`, `hands` and `guide`, `output.all`'s, and `lookback.capture`.
  The capture is a sink and closes no loop (R6). `HIDDEN_EDGES` is
  `(shape, pattern)` and `(lookback, scene)` (row 393).
- R5: an explicit loop refuses every wire on the cycle, as `wire_loops`
  does. R7: a wire naming `hands.N` needs its entry, and a frame kind or
  copy outside a wired frame is refused (`FRAME_KIND_UNWIRED`).

*Tests:* `tests/test_graph_wired.py` (17).

### T2 — the builder (`graph.py`, `graphmigrate.py`, `render.py`)

- `graph.build_graph(views, wiring, clouds, effects)` builds **only what
  the wires reach**, in the default graph's node order (so D1's
  placements land as they did). One `Shown` per distinct picture (it
  carries the direct paint, the stand-down and the copies), one
  `Output` per window, and the internal `Capture`, which runs once after
  every `Shown`, every delay's write and every output's hands and guide
  source. `Copy` draws an instance on another picture with the original's
  knobs and clock. `Graph.key` is `(len(views),)`.
- `graphmigrate.frame_wires` writes today's frame for the default
  switches in one canonical order (nine groups), and `output_wires`
  mirrors the old `default_graph` output loop and `_put` rules for each
  golden state. `renamed` maps every id.
- **The proof.** `graph.signature(g)` is a structural fingerprint: per
  output the chain behind `image`, `hands`, `guide`, `depth` and the
  stand-down, then the order of the nodes a frame can show. 92 cases
  were first proved equal to the live `default_graph`, node for node;
  the cases are recorded in `tests/fixtures/frame-signatures.json` (125
  by T3).
- R8: the signature keeps only nodes an output, the capture or a delay
  write reads; `Copy` counts as an `Effect` and the old no-op
  `BackdropNode` sink is skipped. R9: **a hands mute wins over a
  stand-down** (`Output.settle`), so a mute mutes.

*Tests:* `tests/test_graph_frame.py`.

### T3 — every preset a wired frame; `/6` (`graphmigrate.py`, `preset.py`)

- `graphmigrate.migrate` runs plan 33's steps, then `renamed`, then
  `wired_section`; every readable section comes out `"frame": "wired"` in
  the new ids and `output.all` carries the frame. `backdrop.history`
  retires into the capture wire (a route or desk row on it is dropped
  with a note). The renderer builds the new graph only.
- **The schema ladder.** `preset.WIRED_SCHEMA` is
  `hyperspace.preset/6`; `VERSIONS` is `(2, 3, 4, 5, 6)`. A save writes the
  lowest schema that loses nothing: `graphmigrate.unwired` takes a wired
  frame back to the words of `/4` or `/5` when it round-trips to the same
  read (`legacy_section`, `legacy_values`), and **R10 (supersedes row 385's
  "nothing writes `/5` again"): a section that round-trips into `/5`
  words saves as `/5`** (the file's kept section when untouched). `/6`
  only when the new vocabulary is needed. That keeps the other Mac working
  on re-saves of `displace-moo`, `glimmer-bug` and `moo`.
- R11: "hands through the effects" applies the OUTPUT toggle only where
  All outputs already lays a hands layer; a blank frame's through
  outputs get no hands.
- The golden tool writes each state's wires (`output_wires`) with the
  window mutes all on (`View(Switches(), …)`). Three `/6` fixtures:
  `blank-frame`, `channel-out-only`, `through-one-output`; **24 new
  goldens** (741). `tools/golden_frames.py --names` rewrites the
  fixtures' recorded node names alone and asserts the `goldens` list is
  unchanged (`test_renaming_moved_no_golden`).
- Proof: the 38-source `/4` byte test passes untouched; the 58 presets
  in the owner's Drive library re-save byte-identically (checked in the
  T3 fix round; the first cut turned three `/5` files into `/6`).

*Tests:* `tests/test_graph_migrate.py`, `tests/test_graph_free.py`,
`tests/test_presets.py`, `tests/test_graph_frame.py`.

### T4 — the pipelines retired (`graph.py`, `outputs.py`, `overlay.py`, `render.py`)

- `default_graph`, `pipelines_of`, `Fx`, `Wired`, `_Wiring`, `MAKERS`,
  the pipeline composites and `outputs.route` are deleted. `wired()`
  returns a wired wiring as it is and converts an unwired one the way a
  load would (`graphmigrate.wired_of`; `Wiring()` is the factory frame).
- A window has two mutes, `output.N.scene` (labelled **picture**) and
  `output.N.hands`; `output.N.through` is gone, and a config's `through`
  is noted once (`config.THROUGH_IS_WIRING`). A mute never rebuilds the
  graph (`test_a_mute_never_rebuilds`).
- **R12:** a wire into `output.N` with N past the window count builds
  nothing and is reported dormant ("no output 3 this frame"); a wire to a
  window not yet open does nothing until it opens.
- The SYSTEM page's `pipelines` line is `stats["ends"]`
  (`test_stats_name_the_ends`); the render names follow the new ids.
- Owner note, recorded in check 347: muting the **picture** on an
  in-scene preset shows the ground and the guide, not the hands layer
  (the migrated All outputs has no `hands` wire; the scene held them).

*Tests:* `tests/test_graph.py::{test_the_pipelines_are_gone,test_no_preset_draws_the_factory_frame}`,
`tests/test_overlay.py::test_output_switches_are_picture_and_hands`,
`tests/test_config.py::test_a_through_key_is_said_once`.

### T5 — GRAPH deletes anything (`graphview.py`, `ui_graph.py`)

- The canvas **is** the section: one node per name in the section's
  entries and wire ends, one cable per wire, All outputs and each window
  always drawn, the eight channels (an empty one sits on MEDIA's idle
  line), the rig's clouds and the camera. Nothing internal is drawn: no
  `Shown`, cover, capture, `frame`, `fx` or `grounded`. `PLUMBING`,
  `RUN_KEPT`, `FEEDS_NO_DELETE` and `FrameNode` are deleted; the only
  refusals left are type errors, loops, the camera and a cloud
  (`NOT_REMOVABLE`).
- Every node has a label and a hover (`graphview.LABELS`, `HOVERS`,
  `label_of`, `hover_of`); the areas run MEDIA, SCENE, LOOK-BACK,
  EFFECTS, OUTPUTS (`AREAS`). The picker groups by primitive (scene ▸,
  look-back ▸, pictures ▸, effects ▸, copy of ▸) and has a top-level
  **scene starter** (`Edit.starter`, `render_starter`: shape → scene →
  All outputs).
- **R13:** a `ground → output.N` wire is drawn as a small "Ground" source
  node (`graphview.GroundNode`) and deletes. **R14:** saved layout
  positions under the old ids follow the rename
  (`graphmigrate.renamed_layout`). **R15:** an effect with no input reads
  nothing, is drawn faint and keeps its outs; no refusal. **R16:**
  deleting an effect also deletes the copies of it in the same landing,
  and the note says so ("acid deleted, and its copy").
- A GRAPH edit lands the frame in its canonical wire order
  (`_frame_order`), so an edit back to a migrated shape saves in the
  lowest schema again.

*Tests:* `tests/test_graph_edit.py::{test_every_frame_node_and_wire_deletes,test_the_owners_sequence,test_deleting_an_effect_takes_its_copies,test_a_ground_wire_deletes}`,
`tests/test_graph_areas.py::test_the_areas_run_by_primitive`.

### T6 — OUTPUT and LOOKBACK as views (`ui.py`, `ui_lookback.py`, `graphview.py`)

- OUTPUT: All outputs' picture combo first; per window the two mutes and
  a **hands through the effects** checkbox (`graphview.set_through`,
  disabled with its reason on hover: `through_refusal`); a `shows:` combo
  (`shows_line`, `picture_choices`, `set_picture`: "as All outputs",
  "nothing", then the graph's pictures in area order) and an `open on
  GRAPH` chip (`ui_graph.select_node`). Every pick is one undo step.
- **R17:** the combo also offers every channel with a source in its bin;
  picking one wires `channel.<c> → output.N.image`.
- LOOKBACK: the `history_line` becomes `capture_line` ("records: …") and
  `draws_over_line`; a records combo writes `lookback.capture`.
- Spacing on OUTPUT is tighter (item spacing 4, was 7) so four outputs
  fit unscrolled at the control size (hand check 346).

*Tests:* `tests/test_ui_output.py`, `tests/test_ui_lookback.py`.

### T7 — the new preset (`preset.py`, `ui_presets.py`)

`Presets.new` (`preset.UNTITLED_PRESET`, `NEW_SAID`): one undo step,
the library's fresh values, routes cleared, the desk written as the
factory preset layer, `{"frame": "wired"}`, named `untitled` and dirty
with no path. A **new** chip sits before **save** on the PRESET strip
(`strip.presets.new`); **save** on the untitled preset asks for a name.

*Tests:* `tests/test_presets.py::{test_a_new_preset_is_factory_values_and_nothing_wired,test_a_new_preset_does_not_depend_on_what_was_loaded,test_a_new_preset_undoes_in_one_step,test_a_new_preset_saves_and_loads_back_empty,test_a_new_preset_draws_black}`,
`tests/test_ui_presets.py::test_the_strip_has_a_new_chip`.

### Final review fixes (plans 34 + 35, 2026-10-25)

The whole-branch review over 052d889..9bec205 ruled R15–R19 (plan 34's
ledger); each landed with a test written first. **R15** (R14 must respect
R10): a save below `/6` writes the GRAPH layout in the canvas's old ids —
the file's own keys while the layout is what the load made of them, so an
untouched `/4` or `/5` preset saves byte for byte, else every key through
`graphmigrate.old_canvas_id` (`render:channel.a` → `render:media.a`,
`render:hands.2` → `render:ghost.2`, `render:camera` → `render:eye`). The
`/4` and `/5` byte tests gain sources carrying old-id layouts
(`tests/fixtures/old-canvas-layout/faces-media-layout.json`, recorded by
3547a7a; the owner's `glimmer-bug`, recorded by 052d889), and
`tests/test_graph_free.py::test_a_moved_node_in_an_old_layout_saves_below_six_in_the_old_ids`
holds an edited one. The 58 Drive presets, copied and re-saved, are byte
for byte what 052d889 writes (the four with old-id layouts — displace-moo,
glimmer-bug, moo, reeeeeeeel — differed at 9bec205). **R17**: `Presets.new`
sets `Presets.unsaved` (a load or a save clears it, through the load hook);
**save** on the unsaved `untitled` preset opens naming even when a user
preset named `untitled` exists, and **as…** on it prefills nothing. `new`
lands through a public `Library.land_unsaved`, not the library's private
`_apply_doc`/`_landed` (`tests/test_ui_presets.py::test_new_then_save_never_writes_over_a_preset_named_untitled`;
T7's deferred check, `tests/test_presets.py::test_a_new_preset_empties_the_bins_macros_and_modifiers`).
**R18**: deleting the backdrop lifts it as an effect is — the picture into
`backdrop.scene` is wired on into every port the backdrop fed, said
("Backdrop deleted; the scene goes on to Look-back"); on glimmer-bug the
frame is not black after it
(`tests/test_graph_edit.py::test_deleting_the_backdrop_lifts_it_like_an_effect`).
Also: `BackdropNode` is documented as the canvas's stand-in only (its
`ui_graph.home_page` branch is live: the stand-in is what the canvas
draws), `graph.media_name` and `readout_name` are gone, `preset.py` names
`FRAME_KEY`/`WIRED_FRAME`, and the R10 test's through leg asserts.
`Capture.KIND` stays `history` (as `History`'s does).

## What no person has verified

Every headless test passes (3925 passed, 2 skipped on the build machine,
an M3 Max, with the 741 goldens); no person has run any of it. In
particular:

- **The owner's own delete sequence on GRAPH** (343): the tests drive
  `Edit` (the T5 review ran the sequence over 18 presets) and each cable
  and node deletes; nobody
  has dragged a cable off with a mouse, and the stage where the last
  wire goes black is for the eye.
- **A library preset by eye on both Macs** (345): the goldens pin 741
  pictures and the signature test 125 frames on the gate Mac's GL; the
  58 Drive presets are proved byte-identical on re-save, not looked at.
- **The glass's picture mute at the rig** (347), and the two owner notes
  below it: a migrated preset muted in picture shows nothing of the hands
  through the effects, and an in-scene preset muted shows the ground and
  the guide.
- **"Hands through the effects" at output 2 on a real projector** (348).
- **The OUTPUT page at distance** (346): the spacing is tighter; four
  outputs fit unscrolled in the headless draw only.
- **The canvas at distance** (350): the labels, hovers, the Ground node
  and the area order.
- **The frame cost** (351): nothing has timed a tile GPU on the party
  preset, nor a mute changed live.
- **A `/6` file on a plan 33/34 build** (352): the ladder refusal is
  tested against the loader, not the old app.
- **The new chip and a blank preset on the laptop** (342): the draw is
  tested on GL (black centre pixels on two views), not seen.

## Known rough edges

Behaviour the owner will meet:

- **A picture mute hides the through picture (owner note, T3).** In a
  migrated preset, hands through the effects with the picture muted
  shows nothing: the old HANDS route is not a mute.
- **A picture mute on an in-scene preset shows the ground and the guide**,
  not the layer (owner note, T4; the spec's risk).
- **A wire to a window that is not open does nothing until it opens
  (R12).**
- **A `/5` file keeps the old ids on disk (R10).** It still loads; it
  stays readable on the other Mac.
- **The hands layer is built and drawn while All outputs wires it, even
  when every window mutes the hands (T4).** A mute never rebuilds.
- **An old layout whose only position is `render:hands` lands on the new
  hands node (R14, accepted).**
- **OUTPUT's combo offers only pictures the graph reaches or declares,
  plus channels with a source (R17).** Any other picture must be added
  on GRAPH first.
- **Through is refused with the window's own picture** (pick "as All
  outputs" first); **"records: Composite"** reads short for a capture
  through a composite (T6; the longer words are on hover).

Code the next person will meet (deferred minors from the reviews):

- `RESERVED` gains `copy` and `ground`, so a refused hand-written wire's
  note changes its words (T1).
- `signature` no longer records `HandsLayer.readout`, `Shown.stands` and
  `Shown.copies`, nor the look-back's options: the goldens guard them by
  pixels (T4). It keeps only the nodes a frame can show (R8).
- `config.py`'s docstring example near line 89 is awkward after the cut
  (T4).
- `graphview._frame_order` puts the capture composite in group 9, the
  implementer's reading of the canonical order; if `frame_wires` writes it
  differently an edit would save `/6` where `/5` would do (T5). Effect
  hovers use an effect file's `@tip`, with a generic fallback (T5).
- T2's tests were written after a first cut of the builder, not before
  (a process note).

## The design, as agreed (2026-10-24), corrected where the build differs

The text below is the design as written before the build. Where it
differs, the section above is what happened: the schema rule is R10's
(row 385), the hands mute wins over a stand-down (R9), and a wire past
the window count is dormant (R12).

## What the owner wants (2026-10-24)

> on the graph right now, there are all these error messages when I try
> and delete the things I don't want in the graph. If I want to prevent
> the scene from going by default to the output one, I can try to delete
> the wire between it and grounded, but it says that there's something
> with the default graph. You have to connect something else to that thing
> to get it off there, but when you try and do that, it just routes it
> somewhere else or doesn't even let you do that. You can try to remove
> the cable going from the history, then the frame, then the effects, and
> then there's a cable from the effects to the output one. You can try and
> delete that, but it says FX is a chain, and its outputs take it by their
> switch. This is retarded. There's no point in having all of these things
> be in some "default graph." If I can't make them go away, it sounds like
> you either didn't migrate the presets properly, or we haven't actually
> made this thing a free graph yet.

> part of my greater concern is that there's a node called `capture`,
> there's a node called `frame`, there's a node called `grounded`, there's
> a node called `fx`, and there's a node called `output`. It's really,
> really difficult to reason about what any of them do. The primitives we
> actually are working with here are things like scenes and the dream
> subsystem and stuff like that. I think the nodes that we have on the
> graph right now that I'm seeing for this stuff are not quite the right
> abstraction. They might need to be renamed. They might need to be
> organized better. I'm not totally sure, but it just doesn't feel right
> right now.

Before that, the owner was asked about "a blank preset with no default
render graph". He chose both halves: a **new preset** button that starts
at factory defaults with an empty graph, **and** the frame as deletable
wires, so a blank preset draws black until something is wired to an
output.

The owner's direction from plan 33 still binds: **control panel pages are
views of what is in the graph**, not a second home for structure.

## Why the graph cannot do it today

Read off `plan-34-feedback` at ce0b0c6. Line numbers are as of that
commit.

### The built-in frame

`graph.default_graph` (graph.py:4363) builds the frame from each output's
`Switches` (`outputs.py:40`: `scene`, `hands`, `through`, `dim`,
`flip_x`, `flip_y`) and the preset's `Wiring` (graph.py:238). Those
switches are **rig settings**, not the preset's:
`overlay.register_switches` (overlay.py:440) declares `output.N.scene`,
`.hands`, `.through`, `.flip_x`, `.flip_y` and `.dim` with
`persist=False, modulatable=False`. They take their launch values from
`[[output.screens]]` (config.py:304, 365), and they can be learned onto
a desk button. Both of the owner's configs
(`~/Hyperspace/config.toml`, `config.toml.rig`) leave scene, hands and
through at their defaults on every output.

What it builds:

- `shape`, the hands geometry (`ghost`, `ghost.N`, built only while
  something draws them), and the point clouds. All of them go into
  `scene` (`Scene(geometries=[*points, *inside, shape])`, graph.py:4509),
  which clears see-through when there is a backdrop (graph.py:4510).
- `cover`, the face-coverage mask (graph.py:3159), which reads the
  scene's face buffer.
- The backdrop composite, `grounded` (`GROUNDED`, graph.py:181; plan 32
  R, row 330): the scene over `media.<c>`, or over a branch wired into
  `backdrop.image`, at `backdrop.alpha`. `BackdropNode` beside it is the
  sink.
- The hands' layer (`HandsLayer`, graph.py:3180), named after the node
  that makes it (`Wiring.layer_node`). Its `readout` mode is "always" or
  "through" (graph.py:4527), which decides whether the guide is split out.
  `Readout` (graph.py:3268) stands alone when only the scene holds the
  hands.
- `history` (graph.py:3311): the look-back composite, which reads
  `grounded` or `scene`, with an `occluder` (plan 32 B-I1). `capture`
  (graph.py:3355) records the scene, or `grounded` with
  `backdrop.history`, or `composite(history)` with `history.holds =
  scene+hands`. It runs after every pipeline (graph.py:4574–4584).
- **The pipelines.** `pipelines_of` (graph.py:4339) gives `SCENE`,
  `SCENE_HANDS` and `HANDS` from the switches. Each pipeline gets a
  composite laying the layer on before the effects
  (`COMPOSITE_NAMES`, graph.py:4358). Each one also gets **its own copy of
  the run** (`run`, graph.py:4551: one `Effect` node per instance per
  pipeline, `acid`, `acid(scene+hands)`, `acid(hands)`, the same params
  and the same clock), ending in its `Fx` (`FX_NAMES`, graph.py:4359).
  `SCENE_HANDS` stands down to `SCENE` while it bends nothing
  (`Fx.fallback`, `Fx.bent`, graph.py:3791; `Output.settle`,
  graph.py:3979).
- One `Output` per view (graph.py:4591), whose `image`, `hands` and
  `readout` come from the switches. A wire into `output.N.image`
  overrides them through a `Wired` end (graph.py:3908, `_Wiring._put`
  graph.py:4848). The fast path paints a pipeline straight into its one
  window (`Fx.run`'s `direct`, graph.py:3875). `Renderer._compose`
  (render.py:1863) does the rest.

Plan 33 freed the effects (the run is wires `frame → … → fx.image`), the
faces (`shape.faces`), `pattern.media`, `backdrop.image`, branches and
switches. It **kept the frame on purpose**: register row 351, "the
default graph keeps plan 32's compositing order", left the reconciliation
for later (33-free-graph.md, "Not in this plan"). Plan 34 then named the
frame's hidden edges (`FRAME_EDGES`, graph.py:951) so it could refuse
loops through them.

### The refusals the owner hit, word for word

| Where | Gesture | Words |
|---|---|---|
| `graphview.render_unwire` (graphview.py:3356) | delete `scene → grounded`, or any cable the default graph makes | `"{s} → {d} is the default graph's: no wire says it (wire something else into {d} to replace it)"` |
| `graphview.RUN_KEPT` (graphview.py:744, returned at 3334) | delete `frame → fx.image` | `"the run starts at frame and ends at fx.image — insert effects into it"` (plan 33 R20) |
| `graphview.FEEDS_NO_DELETE` (graphview.py:742; `ui_graph._feeds_cut`, ui_graph.py:2230) | delete `history → frame` | `"frame is each pipeline's picture before its effects (the history, the hands laid on): nothing to delete — insert effects after it"` |
| `graphview.PLUMBING["fx"]` (graphview.py:3083) | wire from or delete `fx` | `"fx is a chain's end: its outputs take it by their switches — wire into an output's image to show something else"`: the owner's "FX is a chain, and its outputs take it by their switch" |
| `PLUMBING["composite("]` | the pipelines' composites | `"… lays the hands on before the chain (an output's through switch), not a node a wire names"` |
| `PLUMBING["capture"]` | `capture` | `"capture holds what the history is wired to: wire into history.image"` |
| `PLUMBING["shape"]`, `["cloud"]` | `shape`, a cloud | `"shape is drawn by the scene, not wired"`, `"cloud is drawn by the scene, not wired"` |
| `PLUMBING["readout"]` | `readout` | `"readout is the hands' guide alone: wire the layer into an output's readout"` |
| `graphview._plumbing` (graphview.py:3104) | anything else of the frame | `"{name} is the frame's own, not a node a wire names"` |
| `graphview.render_drop` (graphview.py:3628, 3638) | delete hands 1; delete any frame node | `"hands 1 is the frame's own hands: it stays (switch it off on HANDS)"`; `"{name} is the frame's own: it stays"` |
| `graph.wire_error` (graph.py:1005, 1007) | a geometry or mask cable | `"a hands node's place is its into ({src} into scene or layer), not a wire"`; `"the cover is the history's own: no mask is wired"` (and `render_wire`, graphview.py:3255: `"the cover is the history's own: it is wired so already"`) |
| `graph.FX_IMAGE_REFUSAL` (graph.py:939) | into `fx.image` from off the run | `"fx.image takes the run from frame; to replace an output's picture wire it into output.N.image"` |
| `graph.FRAME_SOURCE_REFUSAL` (graph.py:944; plan 34 T1) | out of `frame` anywhere else | `"frame is the run's head: it goes into the run's first effect or fx.image — the picture before the effects is history, after them the run's last effect"` |
| `graph.wire_error` (graph.py:1030, 1033) | `history` laid over | `"the history paints into what reads it, so it is not laid over: …"` |
| `_Wiring._lacks` (graph.py:4706) | a wire whose end the switches did not build | dormant: `"no output 2 this frame"`, `"no hands layer this frame"` |

"It just routes it somewhere else" is `Wired` (graph.py:3908). A wire
into `output.1.image` puts a second end beside the pipeline, and the
pipeline is still built, still drawn on GRAPH, and still undeletable.

### Pages that hold structure

- **OUTPUT** (`ui.Panel._output_blocks`, ui.py:1804) draws the three
  switches as checkboxes (ui.py:1840–1844). Those switches *are* the
  frame's wiring, so the page is a second home for structure.
- **LOOKBACK** (`ui_lookback.history_line`, ui_lookback.py:103) says what
  the history captures, but that choice lives in `history.holds` (a node
  entry) and `backdrop.history` (a param, params.py:1214), not in a wire.
- **PRESET** (`ui_presets.strip`, ui_presets.py:310) has `◀ name ▶ · save
  · as…` and no way to start from nothing.

## The words

- **Wired frame**: a graph section with `"frame": "wired"`. Every node of
  the picture, the shape to the outputs, is in its wires or its entries.
  Nothing is built that no wire or entry says. Every section this build
  loads becomes one (Component M).
- **All outputs** (`output.all`): a node with the output ports (`image`,
  `hands`, `guide`). An output whose own port has no wire shows what
  `output.all`'s port has. It is not a window, has no params, and is
  always on the canvas.
- **Mute**: a window's own switch that ignores one of its ports this
  frame. `output.N.scene` (labelled **picture**) mutes `image`.
  `output.N.hands` mutes `hands` and `guide`. Mutes are the rig's, as
  today: a launch value from the config, never in a preset, learnable,
  never a rebuild.
- **Copy**: `copy`, `copy.2` …, the same effect instance drawn on another
  picture. A copy has its own `image` and `aux` and the knobs and clock of
  the instance it copies (`{"kind": "copy", "of": "acid"}`). It is what
  the per-pipeline run was, said as a node.
- **Stand-down**: an output whose picture is a chain of copies over a
  composite of a hands layer shows the copies' originals over the
  composite's `under`, with the layer laid over at the output, while the
  copies bend nothing (no copy live, or no hand drawn). This is today's
  `Fx.fallback`, kept as the fast path.
- **Look-back**: the node `lookback` (was `history`; labelled "Look-back"). It draws the
  echoes and the dream over its `image`, and its `capture` port is what
  the ring records. `capture` is a **sink**: what is wired there runs
  even when no output shows the look-back.
- **Ground**: what an output shows where nothing is drawn. It is today's
  clear, `(0, 0, 0, View.bg_alpha)`: black on an opaque window,
  see-through in overlay. **`ground`** is also a source word: wired into
  an output's port (`ground → output.2.image`), that port shows nothing
  although All outputs has something there. It has no node, goes only
  into output ports, and is how "scene off on this output" is said in a
  preset.

## The shape in one paragraph

A section says `"frame": "wired"` and lists its wires. The renderer
builds **only** what they reach (`build_graph`). A reach is a path to an
output's port, to `output.all`'s, or to `lookback.capture`. The scene
draws the geometry wired into `scene.geometry` (`shape`, `hands`,
`hands.2` …, in wire order). The backdrop lays `backdrop.scene` over
`backdrop.image`. The look-back draws over `lookback.image` and records
`lookback.capture`. Effects run where wired, a copy draws an instance
again on another picture, and each output shows its own wires, else
`output.all`'s, through its mutes. An old preset is migrated to the very
wiring today's `default_graph` builds for the default switches, written
once into `output.all`, so every preset looks as it did on both rigs. A
golden state (scene off, hands through …) becomes that output's own
wires, which the golden tool writes, so every golden stays. A new preset
is `{"frame": "wired"}` with nothing else: black. The OUTPUT and
LOOKBACK pages read and write these wires, and `through` stops being a
switch: it is a composite before the effects.

## Components

### V — the vocabulary (`graph.py`, `graphview.py`)

Every node on today's canvas is kept, renamed (its label), merged into
another, or dissolved (it stops being a node because the free frame no
longer needs it). The owner approved this table on 2026-10-24 and asked
for the **ids to be renamed too** (row 373): the "After" column gives
each node's new id, and V2 below is the rule.

| Today (id / canvas title) | After | Label | Hover (one line) | Why |
|---|---|---|---|---|
| `shape` | kept, wireable: `shape → scene.geometry` | Shape | The polytope. Its faces show the faces pattern, or the picture wired into `faces`. | The owner's first primitive. Today it cannot be unwired. |
| `scene` | kept | Scene | Draws the shape and any hands wired into it, through the camera. | A primitive. Its geometry is now its wires. |
| `ghost`, `ghost.N` (hands geometry) | renamed **`hands`**, `hands.N` (params stay `ghost[.N].*`) | Hands | The tracked hands as geometry: wire them into a scene, or draw them alone as a hands layer. | "Hands" is the owner's word; `ghost` was the old renderer's. |
| `hands`, `hands.N` (HandsLayer) | renamed **`hands.layer`**, `hands.N.layer` | Hands layer | The hands drawn alone, to lay over a picture or put through effects. | Laid over or through: a picture, not plumbing. |
| `readout`, `readout.N` | renamed **`hands.guide`**, `hands.N.guide`; the output port `readout` is `guide` | Hands guide | The hands' labels and tethers, laid over last and never bent. | The guide must stay unbent. A port of its own keeps that wireable. |
| `cloud` (PointCloud) | kept (`cloud`), the rig's | Point cloud | A listed cloud device, drawn in every scene. | A device, like a controller: listed in the config, not the preset. |
| `cover` | **dissolved** into the look-back | — | — | A mask only the look-back reads. It was never wireable. |
| `grounded` | **merged** into `backdrop` | — | — | "The scene over the backdrop" is what the backdrop is for. |
| `backdrop` | kept (`backdrop`), gains `scene` | Backdrop | Lays the scene over a picture, at backdrop alpha. | It was a sink beside `grounded`. Now it is the composite itself. |
| `history` | renamed **`lookback`** (params stay `dream.*`), merged with `capture` | Look-back | Echoes and the dream of past frames, over its picture; records what is wired into capture. | The dream subsystem as one primitive, input and output. |
| `capture` | **merged**: `lookback.capture` | — | — | Half of the look-back: what the ring records. |
| `composite(history)` | **dissolved** into an explicit `composite.N` | — | — | "Scene + hands" in the echoes is a composite into `capture`. |
| `frame` | **dissolved** | — | — | The first effect takes its picture straight from a wire (`lookback → acid.image`). |
| `fx`, `fx(scene+hands)`, `fx(hands)` | **dissolved** | — | — | An output takes its picture straight from a wire. |
| `composite(scene+hands)`, `composite(hands)` | **dissolved** into an explicit `composite.N` | — | — | "Hands through the effects" is a composite before them. |
| `acid(scene+hands)`, `acid(hands)` | **dissolved** into a `copy.N` | copy of acid | The same effect, with its knobs, on another picture. | Replication said as a node, only where one is wanted. |
| `wire(output.N)` (Wired) | **dissolved** (an internal end) | — | — | It was the end of a wire into an output; now every output's picture is a wire. |
| `output.N` | kept (`output.N`) | its config name ("ghost", "projector"), else "Output N" | A window: shows its picture, the hands over it, the guide over all. | A primitive. |
| — | **new** `output.all` | All outputs | What every output shows unless its own port is wired. | One preset, any number of windows. |
| `pattern` | kept (`pattern`: `faces` would clash with the port `shape.faces`) | Faces pattern | What the faces show unless a picture is wired into them, and its media layer. | A primitive (the faces). |
| `media.<c>`, `media.<c>(wire)` | renamed **`channel.<c>`** (params stay `media.<c>.*`), one node per channel | Channel A … H | A clip, still or live feed. | A primitive. |
| effect instances | kept | the file's name (`acid`, `acid 2`) | The effect's own `@description`. | |
| `composite.N`, `switch.N` | kept | Composite, Switch | Lays one picture over another; picks one of eight. | |
| `delay.N`, `resize.N`, `echo.k`, `dream` | kept: no clash (`dream` takes no port, so `dream.*` stays the look-back's params) | Delay, Resize, Echo k, Dream | Last frame's picture; a crop at its own size; the k-th newest look-back frame; the dream buffer. | Plan 34's. |
| `delay(write)` | internal (plan 34 T5: the delay's `image` port) | — | — | |
| `render:eye` | renamed **`camera`** (canvas id `render:camera`; params stay `eye.*` and `camera.*`), the rig's | Camera | The shared eye every scene draws through. | |

### V2 — the ids (`graph.py`, `graphmigrate.py`)

The owner, 2026-10-24: "approve, but rename ids too". The ids a preset's
graph section writes are the owner's words:

| Old id (`/2`–`/5`) | New id (`/6`) | Its params (unchanged) |
|---|---|---|
| `ghost`, `ghost.N` | `hands`, `hands.N` | `ghost.*`, `ghost.N.*` |
| `hands`, `hands.N` (the layer) | `hands.layer`, `hands.N.layer` | the hands node's |
| `readout`, `readout.N` | `hands.guide`, `hands.N.guide` | the hands node's |
| `history` (and entry kind `history`) | `lookback` (entry kind `lookback`) | `dream.*` |
| `capture` (render node) | `lookback.capture` (a port) | — |
| `media.<c>` | `channel.<c>` | `media.<c>.*` |
| `output.N.readout` (port) | `output.N.guide` | — |
| `render:eye` (canvas only) | `render:camera` | `eye.*`, `camera.*` |
| `shape`, `scene`, `pattern`, `backdrop`, `output.N`, `cloud`, effects, `composite.N`, `switch.N`, `delay.N`, `resize.N`, `echo.k`, `dream` | unchanged | unchanged |
| `frame`, `fx`, `grounded`, `cover`, the pipeline nodes, `wire(output.N)` | none (dissolved) | — |

- **Params never change id.** `ghost.*`, `dream.*`, `media.<c>.*`,
  `eye.*`, `camera.*`, `fx.*`, `pattern.*`, `backdrop.*`, `output.N.*`
  are the desk's, the routes', the bindings' and every preset's values;
  renaming them would churn every binding (`bindings.default.json` and
  the desk are Dylan's). A node finds its params by
  `graph.param_prefix(id)`: `hands.2` → `ghost.2`, `lookback` → `dream`,
  `channel.a` → `media.a`, `camera` → `eye`, an effect `acid.2` →
  `fx.acid.2`, anything else its own id. The side panel's header says it
  ("Look-back · lookback · params dream.*"), and so does each hover, so a
  performer who reads `dream.fade` under a node called `lookback` sees
  why.
- **Render node names follow the ids.** The SYSTEM lines and the hovers
  say `lookback`, `lookback(capture)`, `lookback(cover)`, `hands.layer`,
  `hands.guide`, `channel.a`. The golden manifest's recorded node names
  are rewritten by T4 (`--names`), and no golden hash moves.
- **The migration.** `graphmigrate.renamed(section)` maps every old id to
  its new one (`NEW_IDS`: whole wire ends, D1's `after` / `into`, the
  entry kind `history`, the port `output.N.readout`). It runs inside
  `migrate`, after plan 33's steps and before `wired_section`, for every
  `/2`–`/4` file and for plan 33/34 `/5` sections. Old ids stay readable
  for good, so every file ever saved loads. In a wired frame an old id is
  refused in words (`OLD_ID_IN_A_WIRED_FRAME`).
- **The schema: `hyperspace.preset/6`** (row 385). A new save names
  `hands` for what a `/5` reader calls `ghost` and `hands.layer` for its
  `hands`, so a plan 33/34 build reading such a section would mistake one
  for the other. The marker alone would fail the section there, but the
  ladder is the honest place: `/6` is `/5` plus the wired frame in the new
  ids. `VERSIONS` becomes `(2, 3, 4, 5, 6)`, and a plan 33/34 build
  refuses a `/6` file by its ladder's own words rather than loading its
  values over a default frame. Saves write the lowest schema that loses nothing (ruling R10, T3
  review, superseding "nothing writes `/5` again"): `/4` or below when the
  round trip says so; `/5` when the frame round-trips into plan 33/34's
  words but `/4` cannot say them (an untouched `/5` file byte for byte, an
  edit sayable there as its round trip in the old ids); `/6` only for the
  wired frame's own words. `/5` stays readable.
- **The byte-identical `/4` save still holds.** `legacy_section` strips
  the wired frame by round trip (M) and maps every id back through
  `OLD_IDS`, so an untouched `/4` preset writes the same bytes. The 38
  sources' test is unchanged.

### F — the wired frame in data (`graph.py`, data half)

- **The marker.** `read_graph` takes a third top-level key, `"frame"`,
  whose one value is `"wired"` (`FRAME_KEY`, `WIRED_FRAME`). Any other
  value is a `GraphError`. `GraphSpec.wired: bool` carries it, and
  `to_json` writes it first.
- **Entries for an unwired frame node.** A frame node exists when a wire
  names it **or** an entry declares it. An entry is how GRAPH keeps one
  unwired (faint, "reaches nothing"):
  `{"kind": "scene"}`, `{"kind": "shape"}`, `{"kind": "backdrop"}`,
  `{"kind": "pattern"}`, `{"kind": "lookback"}`,
  `{"kind": "layer"[, "instance": n]}` (`hands.layer`, `hands.n.layer`) and
  `{"kind": "guide"[, "instance": n]}` (`hands.guide`, `hands.n.guide`).
  In a wired frame, `lookback`'s
  `holds` key is a `GraphError` (`HOLDS_IS_A_WIRE`). Hands entries keep
  `draw` and `laid`, but not `into`, which is a wire now (`INTO_IS_A_WIRE`).
- **Copies.** `{"kind": "copy", "of": "<instance>"[, "instance": n]}`
  becomes `CopyAt(n, of)`, named `copy` / `copy.n`. `of` must name an
  effect instance the section holds. It takes `image` and `aux` and makes
  `IMAGE`. `RESERVED` gains `copy` and `ground`.
- **New and changed ports** (`WIRE_TAKES`, `WIRE_MAKES`):

  | Node | Takes | Makes |
  |---|---|---|
  | `scene` | `geometry` (GEOMETRY, **several wires**, in wire order) | IMAGE |
  | `shape` | `faces` | GEOMETRY |
  | `hands`, `hands.n` | — | GEOMETRY |
  | `hands.layer`, `hands.n.layer` | — | IMAGE |
  | `lookback` | `image`, `capture`, `occluder` | IMAGE |
  | `channel.a` … `channel.h` | — | IMAGE |
  | `backdrop` | `image`, `scene` | IMAGE |
  | `hands.guide`, `hands.n.guide` | — (its hands node's, by name) | IMAGE |
  | `copy`, `copy.n` | `image`, `aux` | IMAGE |
  | `output.N`, `output.all` | `image`, `hands`, `guide` | — |
  | `ground` | — | IMAGE (nothing), into output ports only |

  The hands layer `hands.n.layer` draws `hands.n`, and the guide
  `hands.n.guide` likewise, by name: no geometry wire. `scene.geometry` is the one port
  that takes several wires (`MANY_PORTS`). A `cover` port is not
  wireable.
- **Words retired in a wired frame.** A wire naming `frame` or `fx` is
  refused (`GONE_IN_A_WIRED_FRAME`). So are a geometry wire anywhere but
  `scene.geometry`, and a wire out of `lookback` into a `hands` or `over`
  port. That last one keeps its plan-28 words: it is a real rule (the
  history paints into its reader).
- **Reach.** `reaches(spec)` in a wired frame is a fixpoint from the
  sink ports. Those are every output port (`output.N.*`, `output.all.*`)
  and `lookback.capture`. A node reaches when its picture or geometry goes
  into a port of a reached node or a sink port. The one implicit edge is
  the shape reading the faces pattern while `shape.faces` is unwired
  (`IMPLICIT_EDGES`). Plan 34's rule for `delay.image` stands: a delay's
  input is reached only when the delay is.
- **Loops.** The explicit wires now carry most of plan 34's hidden edges
  (`shape → scene.geometry`, `scene → backdrop.scene`, `backdrop →
  lookback.image`). So `wire_loops` finds those loops, and `loop_words`
  gives `LOOP_FACES` for a loop through a `scene.geometry` wire and
  `LOOP_BACKDROP` for one through `backdrop.scene`. Two edges stay
  hidden (`HIDDEN_EDGES`): `("shape", "pattern")`, and
  `("lookback", "scene")` (the cover reads the scene's face buffer).
  `sink_loops` walks only those.

### B — the builder (`graph.py`, render half)

`build_graph(views, wiring, clouds, effects) -> Graph` builds a wired
frame. In T2 it replaces `default_graph` for a wired section, and in T4
for every section. The wiring now holds everything (`Wiring.wired`,
`Wiring.wires`).

- **Nodes from wires.** One node per name the reached wires use, made
  once what it reads exists. This is plan 28's `_Wiring` loop,
  generalized to every kind, with no node made before the wires:
  - `Shape` and `Hands` are geometry. `Scene(geometries=[*clouds, …the
    scene.geometry wires' sources in wire order])`, with
    `ground=0.0` when a `backdrop.scene` wire reads the scene (a scene
    lying on a backdrop is drawn see-through, as today).
  - `BackdropNode` becomes the composite that was `grounded`. `over` is
    `backdrop.scene`'s source, `under` is `backdrop.image`'s, laid on at
    `backdrop.alpha` (`Composite(under_alpha_of="backdrop_alpha")`). A
    channel straight into `backdrop.image` keeps
    `MediaNode(alpha_of="backdrop_alpha")`, node for node.
  - `History` reads `lookback.image`, and `lookback.occluder` when that is
    wired. It makes its `Cover` itself while the look-back occludes,
    from the graph's one scene (no scene, no cover). `lookback.capture`
    makes the internal `Capture`, which runs after every end and every
    `DelayWrite`, exactly once a frame, as today. With no capture wire
    the ring records nothing, and `Lookback.keep` (plan 34) is unchanged.
  - `HandsLayer(hands.n.layer)` and `Readout(hands.n.guide)` draw `hands.n`. Its
    guide is split out when `hands.n` is also in the scene, or an
    effect is placed on the layer (today's "always"), or the layer
    reaches a live effect this frame (today's "through": `fx_on` and a
    through view). `HandsLayer.split(frame)` decides once a frame.
  - `Effect`, `Copy` (an `Effect` whose `effect` is the original's
    name and whose node name is the copy's), `Composite`, `SwitchNode`,
    `MediaNode`, `PatternNode`, plan 34's nodes: as today.
  - D1 placements (`after`, `into`) are placed on the built graph by
    `_place`, unchanged.
- **Ends.** One `Shown` node per distinct source that an output's
  `image` takes (its own wire, else `output.all`'s). This is `Fx` and
  `Wired` made one. Every output showing that source shares it, so the
  frame texture is painted once. The fast path is kept as it is:
  `Shown.run` paints straight into its one user's window when exactly one
  output takes it this frame at the frame's size, unflipped, with no tap
  and no fold, and otherwise once into a frame texture. **Users are
  counted per frame through the mutes**, so muting one of two windows puts
  the other back on the direct path with no rebuild.
- **Stand-down** (`Shown.fallback`). When an end's source is a chain of
  copies over a composite whose `over` is a hands layer, the builder
  makes the fallback. That is the copies' originals over the composite's
  `under` (an end of its own, run only when an output settles on it), or
  the ground when `under` is unwired. `Shown.bent` and `Output.settle`
  keep today's rule word for word: not bent means the output shows the
  fallback with the layer laid over at the output. A chain of originals
  over a hands composite (a person's own "through") has no fallback. It
  draws the composite, whose look is the same with nothing live.
- **Outputs.** `Output(output.N)` reads, for each of `image`, `hands` and
  `guide`, its own wire, else `output.all`'s. Then the mutes apply each
  frame (`v.switches.scene`, `v.switches.hands`). `blend` is the laid
  layer's hands entry's `laid`, and `depth` is the scene when that is
  `depth`. An output with nothing is the ground (`_compose`'s
  `key is None` path).
- **The graph key** loses the switches. `graph_key(views)` becomes the
  views' count, so a mute never rebuilds. The wiring, the clouds and the
  effect files stay in `Renderer._graph_for`'s comparison.
- **Signature.** `graph.signature(g) -> tuple`: per output, what it shows
  (its end's source chain as (class, effect) pairs back to a source, its
  hands, guide, blend, depth, fallback). Then the order of the
  non-output nodes as (class, effect, ports wired). Node names are not in
  it (`fx` and `shown(lookback)` are one end). The equivalence test
  compares `default_graph` and `build_graph` by this.

### M — the migration (`graphmigrate.py`, `preset.py`)

- **`frame_wires(spec: GraphSpec) -> tuple[list[dict], list[dict]]`**
  gives the frame `default_graph` builds today for the **default
  switches** (`Shows()`: picture, hands, not through; `Shows` is the migration's own word for a switch state, since `Switches.through` goes in T4), as
  (entries, wires) written to `output.all`:
  - `shape → scene.geometry`, after each in-scene hands node
    (`hands[.n] → scene.geometry`, instance order; the clouds stay
    implicit).
  - With a backdrop: `scene → backdrop.scene` and `backdrop →
    lookback.image`, else `scene → lookback.image`. Plan 33's channel or
    branch wire into `backdrop.image` stays.
  - `lookback.occluder ← scene` exactly where today's `History` gets
    `occluder=scene` (a backdrop, without `backdrop.history`).
  - The run: `frame → e1 → … → en → fx.image` becomes
    `lookback → e1.image`, …, `en → output.all.image`. An empty run is
    `lookback → output.all.image`.
  - The layer: `hands[.n].layer → output.all.hands` and `→ output.all.guide`
    where today's default switches lay it over. With the hands in the
    scene: `hands[.n].guide → output.all.guide` (or the layer's, when it is
    the same node, as `scene_readout` is).
  - The capture: `scene → lookback.capture`; `backdrop →
    lookback.capture` with `backdrop.history`; and with `holds =
    scene+hands`, a `composite.k` (the next free instance, its blend the
    layer's `laid`) with `under` the former and `over` the layer, `→
    lookback.capture`.
  - The section's own wires into `output.N.*` stay as they are: they are
    overrides of `output.all`.
- **`output_wires(spec: GraphSpec, n: int, shows: Shows) -> list[dict]`**
  gives the wires `default_graph` gives output `n` under `shows`,
  as overrides of `output.all`. That is `_Wiring._put`'s output rules
  included: a picture by a wire drops the readout where the hands had
  gone through. A port that shows nothing is a `ground` wire. "Through" always writes (an empty run gives no copies) a `composite.k`
  (`lookback` under, the layer over, the hands' `laid` blend, depth when
  `depth`) and a chain of copies of the run `→ output.n.image`. Scene off
  with hands through writes the same over an unwired `under`. The golden
  tool and the OUTPUT page's "hands through the effects" use this
  (Component U).
- **`migrate`** runs plan 33's own steps, then `renamed` (V2: old ids →
  new), then adds the marker and `frame_wires`, for every section this
  build loads (`/2`–`/4`, and plan 33/34 `/5` sections, which have a run
  and no marker). A plan 33/34 `/5` run `frame → … → fx.image` is
  rewritten as above. Plan 34's `delay`, `resize`, `echo.k` and `dream`
  keep their ids.
- **Retired** (`RETIRED` gains them; `with_retired` writes them back
  below `/6`):
  - `backdrop.history` (the param, params.py:1214) is now the capture
    wire. A route on it is dropped with a load note
    (`DRIVEN_RETIRED_NOTE`); no library preset drives it, and a test
    holds that.
  - `history.holds` (the entry key) is now the capture wire.
  - `output.N.through` (the rig param) and the config's `through` key
    are now the output's wiring. The config key is read and said once
    (`THROUGH_IS_WIRING`).
- **Below `/6`: a round trip.** `legacy_section` strips a wired frame
  only when its frame is **exactly** the one `frame_wires` would write
  for the `/4` section that is left. The marker goes, the frame wires go,
  every id goes back through `OLD_IDS`, `into` and `holds` come back, and
  `backdrop.history` returns through
  `with_retired`. Any edit to the frame fails the round trip, so the
  section is `/6`. The 38-source byte test stays
  (`test_an_untouched_v4_preset_saves_byte_identical`).

### O — the outputs, the hands, the look-back (what each switch becomes)

| Today | In the wired frame |
|---|---|
| `output.N.scene` (rig) | a **mute** on the output's `image` port, labelled "picture" (the id is kept for bindings) |
| `output.N.hands` (rig) | a mute on `hands` and `guide` |
| `output.N.through` (rig) | **retired**. "Hands through the effects" is wiring: a composite before the effects. OUTPUT's toggle writes `output_wires(…, Shows(through=True))` into the preset as that output's overrides, in one undo step |
| `output.N.dim`, `flip_x`, `flip_y`; publish; the fit | unchanged params of the window (rig) |
| `SCENE` / `SCENE_HANDS` / `HANDS` pipelines and their run copies | gone. Each output is wired to what it shows; a copy is a node, made only where a through is wired |
| `Fx.fallback`, `Output.settle` | kept, as the stand-down of a copy chain (B) |
| "hands over" | `hands.layer → output.all.hands` (the layer laid at the output, after every effect) |
| "hands through" | `lookback → composite.k.under`, `hands.layer → composite.k.over`, `composite.k → (effects) → output.N.image` |
| hands in the scene | `hands → scene.geometry`; the guide `hands.guide → output.*.guide` |
| depth-aware | the hands entry's `laid: depth`; the output's or composite's `depth` is the scene |
| the guide over everything | `output.*.guide`, laid last, never bent, as today |
| `history.holds`, `backdrop.history` | the wire into `lookback.capture` |
| the dream | reads the capture, as today; `dream` (plan 34) is a picture source |

**Why mutes stay the rig's** (row 374). The library is shared by two
Macs with different windows. A switch in the preset would make the
laptop's preset wrong on the rig. A switch in the session that builds
structure is the second home for structure the owner ruled out. A mute
builds nothing: it is the window ignoring a wire, like its dim. So the
preset holds all structure, the window decides only whether to show it,
and the party's "glass shows the hands only" is still one launch value.

### U — the pages as views (`ui.py`, `ui_lookback.py`, `ui_presets.py`)

- **OUTPUT** (`_output_blocks`), one block per window:
  - "shows: <its image's source in words>" (own, or "as All outputs").
    A combo lists "as All outputs", "nothing" and the graph's pictures
    (`picture_sources(spec)`). Picking a picture is `render_wire(…,
    "output.N.image")`, "nothing" is `ground → output.N.image`, and "as
    All outputs" removes the override.
  - The two mutes, "picture" and "hands".
  - "hands through the effects" (view + edit, above).
  - dim and flips as today, and "open on GRAPH" with the output
    selected.
  - One extra block for **All outputs**: the same combo, no mutes.
- **LOOKBACK**: the `history_line` becomes "records: <the capture's
  source>", with a combo of the same pictures writing `lookback.capture`.
  "draws over: <lookback.image's source>" is read-only words.
- **PRESET** strip: a **new** chip before `save` (Component N).

### N — the new preset (`preset.py`, `ui_presets.py`)

- **`Presets.new() -> list[str]`**, in one undo step ("new preset"):
  - every persisted performance param goes to the library's fresh
    values (`Library._fresh_all()` limited to the performance groups, as
    `Project.new` resets its groups, library.py:1197). These are the
    build's factory values, so the blank preset never depends on what was
    loaded before;
  - the routes are emptied (the router's preset rows);
  - **the desk is written explicitly as the factory preset layer**
    (`desk_json(fresh_desk())`, preset.py:377). `load_doc` resets
    everything a file leaves out *except* the desk: a missing `desk` key
    gives `fresh_desk()`, and `"desk": []` gives an empty layer. So the
    blank preset says its desk rather than relying on the default. The
    desk is Dylan's; this keeps his factory map;
  - the session (rig) params are untouched;
  - the graph section is `{"frame": "wired"}`.

  The preset is unsaved, named `untitled`, with the dirty dot; `save`
  acts as `as…` until it has a name. Every output shows its ground:
  black.
- **What "empty" means** (row 387, owner-approved 2026-10-24): **nothing
  at all**. The canvas shows the outputs and All outputs, unwired; each
  empty channel sits on MEDIA's idle line (G). The picker has
  one first item, **scene starter**, which adds `shape → scene.geometry`
  and `scene → output.all.image` in one step: two deletable wires, not a
  default.

### G — GRAPH (`graphview.py`, `ui_graph.py`)

- **Delete works on everything.** `render_drop` takes any node of the
  section: its entry and every wire touching it go, one undo step. Hands
  1 is no exception: deleting `hands` takes its wires, its layer and its
  guide, and
  its params stay in the registry. `render_unwire` removes any wire, and
  the run's own cables are ordinary. What stays refused:
  - an output window: delete removes its wires (it shows its ground)
    and says `OUTPUT_UNWIRED`, since the window is the rig's;
  - a cloud device and the camera: `NOT_REMOVABLE` (exists);
  - type errors (`wire_error`'s port and type words) and loops
    (`wire_loops`, `sink_loops`, plan 34's words).
- **Deleted:** `PLUMBING`, `_is_plumbing`, `_plumbing`, `RUN_KEPT` (R20
  is retired with the run's ends), `FEEDS`, `FEEDS_NO_DELETE`,
  `FrameNode`, `ui_graph._feeds_cut`, the "is the default graph's: no
  wire says it" words, `spec_name`'s `FX_NAMES` and `Wired` mapping,
  `_with_run` (replaced by `_with_frame`: a section given the marker).
- **Labels and hovers.** `graphview.LABELS` and `graphview.HOVERS`, by
  wire kind, give each node's title and hover (V's table). A node's
  title is its label (an effect's own name, a window's config name).
  Its id shows only in the side panel's header and on hover.
- **Areas by primitive.** `AREAS` becomes `CONTROLLERS, AUDIO,
  MODULATION, MEDIA, SCENE_AREA, LOOKBACK_AREA, EFFECTS_AREA,
  OUTPUTS_AREA`, left to right:
  - MEDIA: channels, delay, faces pattern, a switch;
  - SCENE: shape, hands, hands layer, hands guide, point cloud, camera,
    scene, backdrop;
  - LOOK-BACK: look-back, echoes, dream;
  - EFFECTS: effects, copies, composites, resize;
  - OUTPUTS: All outputs, then each window.

  `media_made` still moves a media-only branch into MEDIA, and the "no
  cable runs back" rule holds left to right. A cable into
  `lookback.capture` and into `delay.image` runs back by design
  (`returns`).
- **The picker**, grouped: **scene starter**; **scene ▸** (scene, shape,
  hands, hands layer, hands guide, backdrop); **look-back ▸** (look-back,
  look-back frame ▸ echo.1 … echo.32, dream); **pictures ▸** (faces
  pattern, composite, switch, switch over the channels ▸, resize,
  delay); **effects ▸** (every file); **copy of ▸** (each effect instance
  in the section). A frame node already in the section (the scene, the
  shape, the look-back, the backdrop, the pattern) is drawn disabled.
  There is one of each.
- **The unwired** (`unreached`) covers every kind: a declared or wired
  node that reaches nothing is faint, "reaches nothing", and never built.
- **Idle channels and stand-ins.** Today the eight channels are drawn
  whatever the render graph holds (graphview.py:1039–1052), and `pattern`
  and `backdrop` are always drawn as stand-ins (graphview.py:1060–1063),
  with `group:backdrop` in `ALWAYS_DRAWN` (graphview.py:1576). On a blank
  preset that is eleven nodes of clutter. In a wired frame:
  - a channel with no wire from it and an empty bin (`channel_empty`,
    graphview.py:1590) sits on MEDIA's idle line, as an idle macro does
    (plan 28 N9's `is_idle`: `IDLE_KINDS` takes the channels' node kind,
    and the line says "8 empty channels"). A channel with a source in its
    bin, or any wire, is drawn as now;
  - `pattern` and `backdrop` are drawn only when the section wires or
    declares them, and `ALWAYS_DRAWN` is emptied (the backdrop group node
    idles like any group);
  - the rig's desk and session binding cables are out of scope: another
    session's filter handles them after T5.

## What changes for plan 34

Plan 34 resumed and is **built** (2026-10-25): T1–T3 were built on the
base, and T4 (772e48f, 1fca6ae), T5 (875a44d) and T6 (the docs) were
rebased onto this plan as below. [`34-feedback.md`](34-feedback.md) has
"What was built". The 741 goldens above are this plan's own count; plan
34's T4 adds `resize-faces` and `resize-crop` (16), so **757 with plan
34's T4**. Row 393 said plan 34's T4 would remove the last of
`FRAME_EDGES`; it did not, and it stays for reading an old section.

- **T1's words**: `FRAME_SOURCE_REFUSAL` and `LOOP_FRAME` are retired
  (there is no `frame`), and `FRAME_EDGES` becomes `HIDDEN_EDGES`
  (two edges) in a wired frame. `LOOP_FACES` and `LOOP_BACKDROP` keep
  their words and now also name explicit loops through `scene.geometry`
  and `backdrop.scene`. The test rows of
  `test_each_sink_loop_is_refused_at_read` are rewritten for wired
  sections, with the same words.
- **T2's delay and T3's echoes**: unchanged nodes. `DelayWrite` and the
  echoes' "read before the capture" ride on the internal `Capture`, as
  before. The fixtures `delay-faces`, `delay-trails` and `echo-faces` are
  `/5` with a run, and migrate on load like any other. Their goldens do
  not move.
- **T4 (resize)**: its fixtures are written as wired frames
  (`"frame": "wired"`, `lookback → … → output.all.image`), not with
  `frame → fx.image`, in the new ids and `/6` (`resize-crop`'s channel is
  `channel.a → resize.image`). `MAKERS` is the builder's. Plan 34's own
  ids (`delay`, `resize`, `echo.k`, `dream`) are unchanged: none clashes
  with V2.
- **T5 (GRAPH)**: `_with_run` becomes `_with_frame`. The picker items go
  into V's groups, with echo and dream under **look-back ▸** in
  LOOKBACK_AREA, not MEDIA. `MAKER_KINDS` and `unreached` are the
  generalized ones. The drag test `test_a_sink_loop_drag_is_refused_in_words`
  keeps its words.
- **T6 (docs)**: rows 353–371 stand. Row 359's `FRAME_EDGES` is said as
  superseded by row 393.

## Not in this plan

- **Per-instance faces** (`shape.faces.<k>`), and the MEDIA and FACES
  pages as views of the graph. OUTPUT and LOOKBACK are in, because they
  held frame structure.
- **A second scene or a second look-back.** One of each, as today (the
  look-back's ring and the dream worker are one subsystem). The words do
  not forbid a second later.
- **Renaming params.** Node ids change (V2); param ids (`ghost.*`,
  `dream.*`, `media.<c>.*`, `eye.*`) never do.
- **A crossfading output**, a per-output effect chain on the window
  itself, or wiring a window's composited picture back in (plan 34's "not
  in this plan").
- Factory presets are not edited. They migrate on load. `hyperspace/library/`,
  `apc40.py`, `midi.py`, `bindings.default.json` and the desk are
  untouched.

## Risks

- **The goldens are the contract.** All 717 (and plan 34 T4's 16 once
  rebased) must match after every task. Two layers of proof:
  - a structural test (`signature`) over every factory preset and
    fixture × the eight states × the WIRED variants, so a mismatch is
    found as a named node before any pixel;
  - the golden suite.

  The subtle cases: the in-scene hands (the readout's source, the layer
  on a scene-off output), `Wired`'s readout rule, a `hands` wire on a
  through output (`_put` makes its picture the fallback), the depth-aware
  layer, `holds = scene+hands`, and the backdrop's occluder.
  `output_wires` mirrors `default_graph`'s output loop and `_put` line by
  line. A miss is a bug, not a re-record.
- **The byte-identical `/4` save hangs on a canonical frame.**
  `frame_wires` must be deterministic: fixed order, fixed composite
  instance choice, exact id mapping back. Otherwise an untouched preset
  saves as `/6` and becomes unreadable on an older build. The round-trip test covers the
  38 sources and every fixture.
- **One library, two Macs.** A `/6` preset opened on a plan 33/34 build
  is refused whole by the schema ladder (values too). Both Macs must be
  on this build before anyone saves one (check 352). An untouched `/4`
  preset stays readable everywhere.
- **The renamed ids.** `hands` meant the layer before and means the
  hands geometry now, so a missed rename silently swaps the two. The
  rename runs in one place (`renamed`), it is tested both ways
  (`new_id` / `old_id`), and an old id in a wired frame is refused in
  words.
- **SYSTEM's lines and stats change.** `fx`, `fx(scene+hands)` and
  `wire(output.N)` disappear, and `history`, `hands`, `readout`,
  `media.a` are now `lookback`, `hands.layer`, `hands.guide`,
  `channel.a`. The golden manifest's recorded node names are rewritten
  (T4 `--names`); no hash moves. `stats["pipelines"]` becomes the ends' source
  names, and `stats["routes"]` changes with it. The SYSTEM page and
  `tools/golden_frames.py`'s `route` assertion are rewritten in T4.
- **A mute on an in-scene preset.** Today a scene-off window with the
  hands in the scene still gets the layer over. Under a mute it shows the
  ground and the guide, because the migrated `output.all` has no
  `hands` wire (the scene held them). No rig config mutes a picture
  today. Check 347.
- **Plan 34 rebase churn.** Its T4/T5 touch the same functions
  (`_Wiring._make`, the picker, `unreached`). The rebase notes above
  name each one.
- **Frame cost.** It is the same or less. Nothing unreached is built (a
  blank preset runs no scene pass, no look-back and no capture). A mute
  no longer rebuilds the graph. One end is shared by every output showing
  one picture. A through output's copies cost what its pipeline did.
  Check 351 compares SYSTEM before and after on the party preset.

## Decisions

Rows 372–393 of [`DECISION-REGISTER.md`](../DECISION-REGISTER.md). The three put to the owner were answered on
2026-10-24 and come first. The rest are "(rec)": recommendations the
build takes, each cheap to reverse before a preset using it is saved.

**Answered by the owner (2026-10-24):**

373. **The vocabulary** (owner 2026-10-24: approve, rename ids too). The
     before → after table (V) stands: frame / fx / grounded / capture /
     cover / the pipeline composites and copies stop being nodes, and the
     labels and hovers are V's. The ids are renamed too (V2): `ghost` →
     `hands`, the layer `hands` → `hands.layer`, `readout` →
     `hands.guide`, `history` → `lookback`, `media.<c>` → `channel.<c>`,
     the port `output.N.readout` → `output.N.guide`, `render:eye` →
     `render:camera`. Params keep their ids (`param_prefix`). Old ids are
     read for good and renamed on load; `/4` writes them back. The schema
     follows (row 385).
374. **The per-output switches** (owner 2026-10-24: approved as
     proposed). Picture and hands stay each window's own on/off (the
     rig's, as now, nothing built), "through" becomes wiring (a composite
     before the effects), and a preset wires All outputs once with
     per-output overrides. Others were: switches as wires in the preset
     (a laptop preset leaves the glass black on the rig); switches kept
     building structure.
387. **What a new preset's "empty" is** (owner 2026-10-24: approved as
     proposed). Only the outputs, nothing wired (black), plus a "scene
     starter" picker item that wires shape → scene → All outputs. Empty
     channels sit on MEDIA's idle line. The blank preset's desk is
     written explicitly as the factory preset layer (`fresh_desk()`),
     since a file with no `desk` key gets that layer and one with
     `"desk": []` an empty one. Its values are the library's fresh values,
     whatever was loaded before.

**Recommendations:**

372. **The frame is wires** (owner, 2026-10-24): every node of the frame
     is ordinary, a section says `"frame": "wired"`, and nothing is built
     that no wire or entry says.
375. **All outputs (`output.all`)**: what every output shows unless its
     own port is wired; an old preset's frame is written there once
     (rec). Other: every output wired one by one (`output.1` …
     `output.4`).
376. **An unwired output shows its ground**: black on an opaque window,
     see-through in overlay (rec). Other: always opaque black.
377. **No pipelines. An effect on a second picture is a `copy`** with the
     instance's knobs and clock (rec). Other: a second instance with
     routes linking its params (two clocks).
378. **The stand-down is kept for a copy chain over a hands composite**
     (`Shown.fallback`, `Output.settle`), the fast path and the goldens'
     exactness (rec). Other: always draw the composite (a pass more, and
     through goldens at risk).
379. **The direct paint is kept**, users counted per frame through the
     mutes; mutes never rebuild (rec).
380. **Hands**: `hands.n.layer` draws `hands.n`; any hands node may have
     a layer; `hands.n → scene.geometry` puts it in the scene; the guide
     splits when the hands are in the scene, an effect is placed on the
     layer, or the layer reaches a live effect (rec). Other: keep "one
     hands node makes the layer".
381. **The look-back is one node** (`lookback`, "Look-back") with `image`,
     `capture` and `occluder`. The capture is a sink. `holds` and
     `backdrop.history` retire into the capture wire; a route on
     `backdrop.history` is dropped with a note (rec). Other: keep
     `backdrop.history` as a look-back param.
382. **The backdrop lays `backdrop.scene` over `backdrop.image`** at
     `backdrop.alpha`; a scene read by a backdrop is drawn see-through
     (`grounded` merged) (rec). Other: a plain composite with an alpha
     param.
383. **Migration writes today's default frame for the default switches**;
     the section's own output wires stay as overrides; D1 placements stay
     entries placed on the built graph (rec).
384. **Below `/6` by round trip**: a wired frame saves as `/4` only when
     its frame is exactly what `frame_wires` writes, its ids mapped back
     (rec).
385. **The schema is `hyperspace.preset/6`** (rec, following row 373):
     `/6` is `/5` plus the wired frame in the new ids. `VERSIONS` becomes
     `(2, 3, 4, 5, 6)`; a plan 33/34 build refuses a `/6` file by its
     ladder's words; a save writes the lowest schema that loses nothing —
     `/5` where the frame round-trips into its words (ruling R10, the T3
     review, superseding "nothing writes `/5` again"); `/2`–`/5` stay readable;
     the `frame` key stays as the section's marker (`read_graph` knows no
     schema). Other: stay `/5` with the marker alone (a plan-34 build
     would then load the values over its default frame, and a `/5`
     reader could mistake `hands` the geometry for `hands` the layer).
386. **The new preset**: the library's fresh values (`_fresh_all`, as
     `Project.new`), routes cleared, the desk written as the factory
     preset layer, session untouched, `untitled` and unsaved (owner
     chose the button 2026-10-24; the details rec).
388. **GRAPH deletes everything**: the refusals left are type errors,
     loops and the rig's nodes; deleting a window unwires it; PLUMBING,
     RUN_KEPT (R20), FEEDS and `FrameNode` are deleted (rec).
389. **Areas by primitive**: MEDIA, SCENE, LOOK-BACK, EFFECTS, OUTPUTS
     (rec). Other: keep GEOMETRY / SHADERS.
390. **OUTPUT and LOOKBACK are views that edit wires**: each output's
     picture as a combo, its mutes, "hands through the effects" written
     as wiring; the look-back's capture as a combo (rec).
391. **Point clouds stay the rig's**, drawn in every scene (rec). Other:
     a cloud as a wired geometry (a preset naming a device one Mac lacks).
392. **Golden states as wiring**: the tool writes each state's per-output
     wires (`output_wires`) with the mutes all on, and the mutes have
     tests of their own (rec).
393. **Plan 34's frame words retired** (`FRAME_SOURCE_REFUSAL`,
     `LOOP_FRAME`); `FRAME_EDGES` becomes `HIDDEN_EDGES` = `(shape,
     pattern)`, `(lookback, scene)` in a wired frame (rec).

## Hand checks (group AE, 342–352; as written in `11-hand-checks.md`)

- **342.** New preset on the laptop: both outputs black, the canvas
  shows only the outputs and All outputs, the values are the factory's
  whatever was loaded before, the desk is the factory preset layer, and
  MEDIA shows only its idle line. Then "scene starter": the shape shows.
- **343.** The owner's own sequence on a party preset: delete `scene →
  backdrop.scene` (or `scene → lookback.image`), then `lookback → <first
  effect>`, then the effects, then `<last effect> → output.all.image`.
  Each goes with no refusal, and the output goes black at the last.
- **344.** `channel.a → output.all.image` alone: the clip on both windows,
  no scene pass on SYSTEM.
- **345.** A library preset by eye on both Macs, before and after: the
  same look.
- **346.** OUTPUT page: pick a picture for output 2 from the combo; "as
  All outputs" puts it back; undo steps through both.
- **347.** At the rig: the glass's "picture" mute off shows the hands
  only. Judge an in-scene preset muted (the ground and the guide, no
  layer), and a migrated preset with hands through the effects and the
  picture muted (nothing: a picture mute hides the through picture). Both
  are owner notes from the build.
- **348.** "Hands through the effects" on output 2: the hands bent by
  the effects there, over on output 1. With every effect off, output 2
  looks like output 1.
- **349.** LOOKBACK: "records" set to the backdrop, then to the scene;
  the echoes follow.
- **350.** The canvas at distance: the labels and hovers read without the
  ids. The areas run MEDIA → SCENE → LOOK-BACK → EFFECTS → OUTPUTS with
  no cable running back but the capture's and a delay's.
- **351.** SYSTEM on the party preset before and after this plan: no
  frame-time regression; muting a window costs no rebuild hitch.
- **352.** A `/6` preset opened on a plan 33/34 build: refused by the
  schema ladder in its words; an untouched `/4` preset still opens there.
  Both Macs on this build.
