# Plan 34 — feedback: a delay node, look-back frames as sources, a resize node, loops refused at read

**Status: built (2026-10-25)** on `plan-34-feedback` (PR #236, which also
carries plan 35; cut from `plan-33-free-graph` @ 052d889: 3550 tests
passed, 2 skipped, 693 goldens. Now 3953 passed, 2 skipped, 757 goldens:
plan 34 adds 40 of them, 24 of those in plan 35's base). Built in two
halves around plan 35: T1–T3 on plan 33's model, a pause, then T4–T6 on
plan 35's. The owner said "build" on 2026-10-24; the decisions below
(rows 353–371) are recommendations the build took as given. None waits
for the owner. The build plan is
[`34-feedback-build.md`](34-feedback-build.md). Hand checks
[`11-hand-checks.md`](11-hand-checks.md) group AD, checks 332–341; register
rows 353–371 of [`DECISION-REGISTER.md`](../DECISION-REGISTER.md) and the
"Feedback (plan 34)" section of [`DECISIONS.md`](../DECISIONS.md).

What this plan adds to the free graph (plan 33):

- **`delay`**: a picture node whose output is last frame's input (z⁻¹). A
  loop drawn on GRAPH is legal when it passes through one.
- **The look-back's frames as sources**: `echo.1` … `echo.32` (newest
  first) and `dream`, wireable into any picture port.
- **`resize`**: a node that crops and downsamples (or upsamples) its input
  to a size of its own, so a delay fed through it holds a small buffer and
  an effect after it runs small.
- **The loop-refusal fix**: every wire that would make a loop through the
  faces, the backdrop or the frame is refused when the section is read, in
  plain words. Today such a wire lands and then sits dormant.

Base: branch `plan-33-free-graph` @ 052d889. Preset schema stays
`hyperspace.preset/5`. Register rows from 353; hand checks from 332
(group AD).

**Amended 2026-10-25 for plan 35.** T1–T3 were built (54b7495..ce0b0c6),
and then the plan was paused for plan 35, "the frame as wires"
([`35-free-frame.md`](35-free-frame.md)), which is built on the same
branch (51ef105..6193cb7). T4–T6 resume on plan 35's model:
- there is no default graph, `frame`, `fx` or pipeline;
- `graph.build_graph` builds only what the wires reach;
- the node ids are the owner's (`lookback`, `hands.layer`, `channel.<c>`);
- the schema is `/6` for the new vocabulary, and a save writes the lowest
  schema that loses nothing (plan 35 R10).

Plan 34's own ids (`delay`, `resize`, `echo.k`, `dream`) are unchanged. The
sections written before plan 35 ("Why the graph cannot do it today", "The
words", L, D, E) describe plan 33's model, which T1–T3 were built on. Z, G,
"Not in this plan", Risks, rows 359, 370 and 371, and the hand checks are
amended below. Where they differ from the earlier sections, they win.

## What was built

Built task by task on `plan-34-feedback` (T1–T6, each reviewed; T2 and T3
took fix rounds, T3 two, and T4 one). Commits, by task: T1 = the words and
the loop refusal (d27f7ef); T2 = the delay (6a2fa41, fixes 0a3b1e5); T3 =
the look-back's echoes and dream (72f59c7, fixes 2bdb55a, ce0b0c6); **the
pause for plan 35** (51ef105..6193cb7, the owner's ruling R8 on
2026-10-24: "the frame as wires" was more pressing), after which T4–T6 were
rewritten for its model (a78bb4a); T4 = the resize (772e48f, fix 1fca6ae);
T5 = GRAPH (875a44d); T6 = this documentation. 3953 tests passed, 2
skipped (the base was 3550; plan 35's base for T4 was 3925). **757
goldens**: the 693 before the plan, 24 recorded by T1–T3 (`delay-faces`,
`delay-trails`, `echo-faces`, 8 each), 24 by plan 35 (`blank-frame`,
`channel-out-only`, `through-one-output`, 8 each) and 16 by T4
(`resize-faces`, `resize-crop`). So plan 34's own are 40 (5 fixtures × 8
states), 24 of them in plan 35's base of 741. None of the 741 moved when
T4 and T5 landed (`tests/test_golden_frames.py::test_renaming_moved_no_golden`
holds the digest over them).

**The delay** (T2; rows 353–358, `graph.Delay`, `graph.DelayWrite`,
`render.DelayPair`). A node `delay` (`delay.2` …) whose picture is last
frame's input. The renderer holds a half-float ping-pong pair per delay
name (`Renderer.delay_pair`), swapped at the start of the frame
(`Renderer._turn_delays`), kept across graph rebuilds and released
`SIZED_KEEP_FRAMES` frames after the delay leaves the graph. The delay
itself has no inputs, so a loop through it is no dependency. Its other
half, `DelayWrite` (`delay(write)` on SYSTEM), paints the delay's `image`
into the write side at its input's own size, else the frame's. Under plan
35 `_Build.build` adds each *reached* delay's write before the internal
`Capture`, so a delay is written whether or not
anything shows the look-back. It reads nothing on the first frame, so the
faces show the pattern (`tests/test_graph_delay.py::test_the_first_frame_reads_nothing_and_the_faces_show_the_pattern`).
Rulings that changed behaviour: **R7**, a write whose input read nothing
leaves the pair unwritten, so the next frame the delay reads nothing and
the faces fall back to the pattern (plan 33's rule), where the brief had
said black (`::test_a_delay_whose_input_read_nothing_reads_nothing`);
**R5**, `PassTimer` treats a time query inside another as a no-op, because
GL allows one active query and `delay(write)` wraps the effect passes
(`::test_a_query_inside_another_is_a_no_op`; the write's SYSTEM time
includes the nested effects' time); **R6**, the `delay-trails` fixture shows
a trail: `delay → zoomblur.2 → palette.2` (val slice to 0.6), added over the
scene by `composite.2`, the result into the delay and `output.1`, with a
test that its frame differs from `party-faces` and that the trail fades
(`::test_the_trails_show_and_fade`).

**The echoes and the dream** (T3; rows 360–363, `graph.EchoNode`,
`graph.DreamNode`, `Lookback.echo_slot`). `echo.1` … `echo.32` (1 the
newest commit) and `dream` are picture sources, declared by a node entry.
They read nothing before k commits, after the ring is remade and with no
ring; the ring keeps capturing for them with the look-back off
(`Graph.reads_ring` → `Lookback.keep`). **R9**: `echo_slot` also reads
nothing while `dream.res` differs from the ring's, because the ring is
remade inside the capture, after the echoes are read, so a resolution
change costs one frame of no echo
(`tests/test_graph_echo.py::test_a_res_change_empties_the_echoes`,
`::test_a_res_change_to_the_same_size_keeps_the_echoes`). **R11**: an echo
wired to an output's `hands` is read before the capture like one at its
`image` (it joins the capture's `after`), so it shows the frame before,
not the frame being drawn; one whose ring a failed remake released reads
nothing (`::test_an_echo_into_an_outputs_hands_reads_last_frames_capture`,
`::test_an_echo_into_hands_reads_nothing_when_the_ring_failed_to_rebuild`).
An echo cannot go to an output's `guide`: that port takes a hands layer's
guide and the wire is refused at read. **R10**: with the scene and the
hands both captured the node's words say "the scene + hands" (the wording
is plan 35's to name).

**The loop refusal** (T1, T5; row 359, `graph.sink_loops`, `loop_words`).
A wire that closes a loop through the faces, the backdrop or (on an old
section) the frame is refused when the section is read, in words
(`LOOP_FACES`, `LOOP_BACKDROP`, `LOOP_FRAME`) that say to wire it through a
delay; an edge into a delay is no dependency. **R3**: where a wire is both
a `frame` source and a loop, the loop words win. **R4**:
`graphmigrate.legacy_values` returns None for any of delay, resize, echo
or dream, so such a preset cannot be written below `/5`. **Plan 35 rewrote
the scope** (row 393): `FRAME_SOURCE_REFUSAL` and `LOOP_FRAME` are not
read in a wired frame, and `HIDDEN_EDGES` (two edges) stands in for
`FRAME_EDGES`, which **is kept for reading an old section before it
migrates**; T4 did not remove it. **T5** gave a wired frame's *other*
loops (`acid → wobble → acid.aux`) `LOOP_PLAIN`, which points at a delay
too (`tests/test_graph_edit.py::test_a_plain_loop_drag_points_at_a_delay`,
`tests/test_graph_wired.py::test_loop_words_in_a_wired_frame`).

**The resize** (T4; rows 364–369, `graph.ResizeNode`, `params.declare_resizes`,
`view.ResizeState`). Built by `_Build._make` only where the wires reach it,
its params from its entry (`resize[.n].size`, `aspect`, `fit`, `filter`,
`crop_x`, `crop_y`, `crop_w`, `crop_h`, group `resize`, a preset's values,
all modulatable). Unfed, it is dormant: "resize is fed by nothing here:
wire its input". Its picture is a half-float target of its own size,
`Node.own_size`, drawn by `Renderer._refit` (cover, contain or stretch;
linear with the input's mipmaps past a 2× shrink, or nearest). A delay
fed through it holds that size (`DelayWrite.held`) and an effect after it
runs at it. A crop or size change is a value, never a graph rebuild
(`tests/test_graph_resize.py::test_a_crop_change_is_a_value_never_a_rebuild`);
a size step makes one target each way and keeps both
(`::test_a_size_step_reallocates_once_each_way`). **R12**: `REFIT_FS` draws
a crop past the source's edge as transparent black, as the plan says; the
earlier callers' crops stay inside [0,1] and their output did not move
(`::test_a_crop_past_the_edge_is_transparent`). **R13**: GRAPH's stand-in
`ResizeNode` is replaced by the real node and the resize joins
`MEDIA_MADE` (`graphview.py`), which the areas test needed. **R14**: the
loop test seeds the delay red, since an empty loop stays empty
(`::test_a_loop_through_a_resize_and_a_delay_is_legal`), and a filtering
test asserts the mipmaps with a spy on `_refit`. The fix round made
`declare_resizes` keep a live state when `view` is hot-reloaded
(`::test_resize_knobs_survive_a_hot_reload_of_view`). `resize-faces` and
`resize-crop` are `/6` wired frames, the factory frame's wires plus the
resize's, each drawn under the window's mutes.

**GRAPH** (T5, on plan 35's G; rows 370). The areas are plan 35's
(row 389): delay in MEDIA, echo and dream in LOOK-BACK, the resize in
EFFECTS, or MEDIA when `media_made` says it is made of the media alone
(`tests/test_graph_areas.py::test_a_resize_sits_by_what_it_is_made_of`).
The cable into a delay's image runs back by design. T5 added a resize's
eight params as side-panel rows through `OWNERS["resize"]`
(`tests/test_graph_legible.py::test_a_resize_nodes_params_are_rows_in_the_side_panel`)
and a node's `said` as the first line of its summary, after the switch
pick, before the faint word (`tests/test_graphview.py::test_a_render_nodes_said_is_its_first_line`).

**The schema** (row 371, amended by 385, R10). Plan 34's words are `/5`
words (`graphmigrate.uses_free_words`), so a wired frame that round-trips
through them saves `/5`; one that needs plan 35's vocabulary saves `/6`.
The fixtures `delay-faces`, `delay-trails` and `echo-faces` are `/5`,
`resize-faces` and `resize-crop` are `/6`
(`tests/test_graph_feedback.py::test_the_new_words_are_v5_only`,
`tests/test_presets.py::test_resize_values_save_and_load_with_the_preset`).

**The rulings.**

| | Ruling | Folded into |
|---|---|---|
| R1 | tasks committed in sequence on the one branch | — |
| R2 | the pre-flight scan was each task's review | — |
| R3 | the loop words win over `FRAME_SOURCE_REFUSAL` | the refusal |
| R4 | `legacy_values` is None for the four kinds | the schema |
| R5 | a time query inside another is a no-op | the delay |
| R6 | `delay-trails` must show a trail | the delay, check 333 |
| R7 | a write that read nothing leaves the pair unwritten | the delay |
| R8 | pause for plan 35 (the owner) | the order of the build |
| R9 | an echo reads nothing while `dream.res` differs from the ring's | the echoes |
| R10 | "the scene + hands" in the words | the echoes |
| R11 | an echo into `hands` is read before the capture | the echoes |
| R12 | a crop past the edge is transparent black | the resize |
| R13 | the real `ResizeNode` replaces GRAPH's stand-in; `MEDIA_MADE` | GRAPH |
| R14 | the loop test seeds the delay; the filter test spies `_refit` | the resize |

(Plan 35 has its own R10; "R10" in plan 34's rows means row 385's.)

## What no person has verified

Every headless test passes (3953 passed, 2 skipped on the build machine,
an M3 Max, with the 757 goldens); no person has run any of it. The
checks are group AD (332–341), and they share a sitting with plan 35's
group AE (see `11-hand-checks.md`). In particular:

- **The look of the infinite mirror and of the trails** (332, 333). The
  goldens pin the pictures, and a test asserts the trail differs from
  `party-faces` and fades; nobody has judged whether it looks good, or
  whether black faces under an opaque scene are tolerable.
- **The drag on GRAPH** (334): the dry run is tested through `Edit`, not
  with a mouse.
- **The ring's cadence and the dream worker** (335, 336).
- **A resize animated by an LFO**, and a resize size modulated across its
  steps (337, and the second half of 339): the tests change a value
  between frames; nothing has run a real LFO for a minute.
- **The frame cost** (338, 340): no test times a frame. Whether a resize
  before an effect pays for its refit, and what a 1080p delay costs
  against a 256² one, is for SYSTEM.
- **A window resize and a render-cap change mid-feedback** (339).
- **A `/5` file with a delay on a plan 33 build** (341): the ladder is
  tested against the loader, not the old app.

## Known rough edges

Behaviour the owner will meet:

- **Feedback through the scene is 8-bit.** The scene's target is RGBA8, so
  `scene → delay → shape.faces` quantises once a loop, and a decay below
  1 leaves a faint floor rather than fading to black. A loop of effects
  alone is half-float throughout.
- **The faces show an opaque picture fully.** Last frame's black
  background shows as black faces, not see-through ones (check 332).
- **A `/5` save of plan 34's words is read by a plan 33 build with a
  note.** It fails the graph section ("unknown node kind 'delay'"), draws
  that build's default graph and loses the run and every branch for that
  load. Both Macs on this build before anyone saves one (check 341). A
  `/6` file is refused there outright (check 352).
- **`FRAME_EDGES` stays** for reading an old section before it migrates;
  plan 35's row 393 first said T4 would remove the last of it, and it did
  not.
- **A resolution change costs one frame of no echo** (R9), and a feed lost
  to a delay costs one frame of pattern before the faces settle (R7).
- **A modulated resize size remakes the delay pair and the effect pools
  downstream at every step** it crosses (16 to 2048, powers of two). It is
  bounded: `SIZED_KEEP_FRAMES` keeps the textures it left, so a size that
  swings between two steps allocates once each way
  (`tests/test_graph_resize.py::test_a_size_step_reallocates_once_each_way`).
  A crop modulated by an LFO builds no new graph
  (`::test_a_crop_change_is_a_value_never_a_rebuild`); nothing has
  counted its allocations. Checks 337, 339.
- **`delay(write)`'s SYSTEM time includes the effects painted inside it**
  (R5).
- **An echo cannot be wired to an output's `guide`**, and a delay's
  picture, like an echo's, is laid onto a consumer of another shape by
  cover (`OWN_FIT`).
- **The resize reads a crop from a sampler on a shared texture**; a linear
  shrink of more than 2× builds its input's mipmaps (the scene's, a pool
  texture's) and leaves the mip levels allocated.

Code the next person will meet (deferred minors from the reviews):

- An effect's root-size `#fit` texture stays allocated after the effect
  leaves the graph, until a size change or a reload (T2).
- `Renderer.on_reload` does not drop `_refit_prog` and `_refit_vao`, so an
  edit to `REFIT_FS` will not land live (T2; T4 changed `REFIT_FS`).
- The comment on `FEEDBACK_FIXTURES` in `tools/golden_frames.py` still
  describes the old trails graph (`delay → zoomblur.2 → composite.under`),
  not the one R6 gave it (T2).
- No test of `wire_loops` alone skipping a wire into a delay; the combined
  test covers it (T1).
- No test combining a switch pick, a node's `said` and the faint word in
  one summary (T5).
- The spec's D section was written before R7 (a write that read nothing)
  and R5 (the nested timer); "What was built" above is what holds.

## The design, as agreed (2026-10-24), amended 2026-10-25 for plan 35

The text below is the design as written before the build, amended for
plan 35 where a paragraph says so. Where it differs from "What was built"
above, that is what happened: the schema rule is row 385's (R10), a wired
frame has no `frame`, `fx` or default graph, and row 359's `FRAME_EDGES`
is `HIDDEN_EDGES` there.

## What the owner wants (2026-10-24)

> Do we have support for recursive rendering right now? Could I take the
> output of a shader chain, or … the frame that we're about to draw, or …
> the previous frame that we have drawn and target it onto the faces of the
> thing for the next frame? I understand that would be technically a graph
> cycle, but I kind of see it more as a per-frame recursive history via a
> cycle in a graph.

After seeing the options (A, a `delay` node; B, look-back frames as
sources):

> yeah build A with the loop refusal fix. i also want to be able to do b.
> also, we should be able to downsample arbitrarily, so add a downsampler
> node as well so we can avoid writing a 1080p buffer into all the faces
> for no reason. downsampler should be able to crop as well.

## Why the graph cannot do it today

Read off the base (`plan-33-free-graph` @ 052d889):

- **Nothing holds last frame's picture as a node.** `Graph` sorts once and
  `evaluate` runs each node once a frame (`graph.py` `Graph.evaluate`). The
  faces are painted inside the scene's pass: `Scene._run` calls
  `Shape.prepare` before it draws. So `scene → shape.faces` asks the scene
  to finish before it starts, and GL would sample its own target. A loop
  needs a node whose output this frame is its input from the frame before.
- **Every wire from the scene's picture into its own inputs lands dormant.**
  The loop check in `read_graph` (`wire_loops`) sees only the wires. The
  default graph's own hidden edges are not wires: the faces are drawn in
  the scene, the history reads the scene and the backdrop, and `frame` is
  the history's picture. So these wires pass the read and are refused only
  when the graph is built:

  | Wire | Today | Where |
  |---|---|---|
  | `scene → shape.faces` | dormant: "scene is drawn from the faces: that makes a loop" | `_Wiring._sink` |
  | `history → shape.faces` | dormant, the same words | `_Wiring._sink` |
  | `frame → shape.faces` | dormant: "no frame this frame" | `_Wiring._lacks` |
  | `frame → acid.image`, `acid → fx.image`, `acid → shape.faces` | the last dormant: "acid is drawn from the faces: that makes a loop" | `_Wiring._sink` |
  | `pattern → acid.image`, `acid → shape.faces`, `scene → acid.aux` | the aux dormant: "acid feeds scene: that makes a loop" | `_Wiring.aux` |
  | `history → backdrop.image` | dormant: "history is drawn from what lies on the backdrop: that makes a loop" | `_Wiring._sink` |

  On GRAPH such a drag goes green, lands, and then shows the wire dormant.
  No test pins the "drawn from the faces" words.
- **The look-back's frames are held but not exposed.** One RGBA8 atlas of
  `MAX_ECHOES` (32) slots, each `dream.res` (128–384) px on its short
  side, is committed every `dream.gap` seconds (`lookback.py`
  `Lookback._capture`, `_due_now`). A dream buffer the same size sits
  beside it. Nothing reads a slot but the history's composite, and the
  ring captures only while `dream.on` is on.
- **No node chooses its own size.** Under plan 33 a branch is made at the
  size its consumer asks (`Node.size_for`, `Frame.at`). Nothing can say
  "make this 256²", so anything wired into the faces is painted at
  `FACE_PIC`² (1024²), and a delay would hold whatever its consumer asks.

Kept from plan 33 and earlier: branches, the run, the switch and
`Graph.pulled`, `Frame.at` and the sized pools, `_prune_sized` with
`SIZED_KEEP_FRAMES`, the fit pass's `fit_scale`, the GRAPH picker's
add-unwired pattern, and `_param_rows` for every node's params.

## The words

- **Delay** — a node `delay`, `delay.2` … with one picture input
  (`delay.image`). Its picture is what came into that input **last frame**.
  On the first frame, and while nothing came in last frame, it reads
  nothing.
- **Loop** — a path of wires and hidden edges that leads a node back to
  its own picture. It is legal only when it passes through a delay, since a
  delay's picture never depends on this frame's input.
- **Hidden edge** — a dependency the default graph adds that no wire says
  (`FRAME_EDGES`). The faces are drawn inside the scene (`scene` reads
  `shape`). The faces read the pattern's layer (`shape` reads `pattern`).
  The history composites the scene, and the backdrop under it (`history`
  reads `scene` and `backdrop`). `frame` is the history's picture (`frame`
  reads `history`).
- **Echo** — `echo.k`, the look-back ring's k-th newest committed frame,
  k from 1 to 32. **Dream** — `dream`, the look-back's dream buffer.
- **Resize** — a node `resize`, `resize.2` … that crops its input to a
  normalised rect and makes the result at a size of its own.
- **Own size** — the size a node makes its picture at whatever its
  consumer asks (`Node.own_size`): a resize's, a delay's held size, an
  echo's. Every node before this plan has none: its consumer decides. A
  consumer of another size gets the picture **fitted by cover** about the
  centre (`OWN_FIT`).

## The shape in one paragraph

Two halves of one z⁻¹. The **`Delay`** node has no inputs: its picture is
a half-float texture the renderer holds under the delay's name. The
**`DelayWrite`** node, `delay(write)`, takes `delay.image`, runs before
the capture and paints its input into the pair's other texture. At the
start of every frame the renderer swaps the two (`Renderer._turn_delays`).
So `scene → delay.image` with `delay → shape.faces` draws the faces with
last frame's scene: the infinite mirror. A loop check that counts the
default graph's hidden edges, and skips every edge into a delay, refuses
`scene → shape.faces` at read in words that point at the delay. **`echo.k`**
and **`dream`** are source nodes that paint one slot of the ring, or the
dream buffer, fitted into whatever reads them. Like a switch, each is
declared by a node entry. The ring keeps capturing while one is read, even
with the look-back off. **`resize`** crops its input to `crop_x/y/w/h`
and makes it at `size` (the long side, 16–2048 px) × its aspect (the
input's, or square). That size is its own. A delay fed through one holds
that size, and an effect after one runs at it. The owner's case is
`scene → resize → delay → shape.faces`, a 64² or 256² feedback on every
face instead of 1024².

## Components

### L — the words and the loop check (`graph.py`, data only)

- **New node kinds** (`NODE_KINDS`):
  - `{"kind": "delay"}` / `{"kind": "delay", "instance": 2}` → `DelayAt(n)`.
  - `{"kind": "resize"}` / `{"kind": "resize", "instance": 2}` → `ResizeAt(n)`.
  - `{"kind": "echo", "index": k}` → `EchoAt(k)`, with k from 1 to
    `MAX_ECHOES`. Its name is `echo.<k>`.
  - `{"kind": "dream"}` → `DreamAt()`, named `dream`. There is one only.

  Each is a frozen dataclass like `SwitchAt` and rides in
  `GraphSpec.others`. A wire may name one only when the section declares it,
  as for a switch: "no delay.2 node in this graph (add one: {"kind":
  "delay"})".
- **Wire ends.** `WIRE_MAKES`: `delay`, `resize`, `echo` and `dream` make
  `IMAGE`. `WIRE_TAKES`: `delay` and `resize` take `{"image": IMAGE}`;
  `echo` and `dream` take nothing. `RESERVED` gains `delay`, `resize`,
  `echo` and `dream`, so no effect file may take those names. None does
  today.
- **The loop check counts the hidden edges.** `wire_loops` (explicit
  loops) keeps its words and refuses every wire on such a loop, as today.
  It now skips each edge into a delay. A new pass, `sink_loops`, runs after
  it on the wires that stand. It walks the wires in the section's order,
  over `FRAME_EDGES` plus the wires already accepted, and refuses a wire
  that would close a loop. Earlier wires stand, so the wire a drag
  appended is the one refused. Edges into a delay are not dependencies.
  The words say which hidden edge the loop runs through (the faces, the
  backdrop, the frame) and point at a delay.
- **`frame` feeds the run only.** `wire_error` refuses a wire out of
  `frame` into anything but an effect's `image` port or `fx.image`, in
  words that say where the picture before and after the effects comes from
  (`history`; the run's last effect).
- **`reaches`** counts a delay's `image` port as a sink only when the
  delay itself reaches one. A delay that feeds nothing is unreached: faint,
  "reaches nothing", never built, and it holds no buffer.
- `graphmigrate.uses_free_words` is true for any of the four kinds, and
  `legacy_section` strips them. A section that uses them is `/5`.

### D — the delay (`graph.py`, `render.py`)

- **Two nodes.** `Delay(name)` has no inputs, outputs `IMAGE`, is not
  `MAKES` and is not timed. Its picture is the read side of the pair. It
  reads nothing until the pair holds a frame. `DelayWrite(f"{name}(write)",
  image=src)` takes `image`, makes nothing and is timed (a SYSTEM line
  `delay(write)`). Every `DelayWrite` runs before the capture
  (`Capture.after`, as a `Wired` end does). Echoes are then taken after the
  delays have read the history, and an echo read this frame is last
  frame's capture.
- **The pair.** `render.DelayPair` holds two RGBA half-float (`f2`)
  textures, LINEAR, clamped and cleared to transparent black when made.
  `Renderer.delay_pair(name)` makes one on first ask and keeps it under
  `Renderer._delays`. It is kept by name across graph rebuilds, so an edit
  elsewhere on GRAPH does not cut the feedback. It is released once no
  graph has held that delay for `SIZED_KEEP_FRAMES` frames. At the start of
  each frame (`Renderer._turn_delays`), a pair written last frame swaps its
  sides and holds a frame. A pair not written last frame holds nothing:
  strict z⁻¹, never a stale picture.
- **What it holds, and at what size.** `DelayWrite.held(frame)` is its
  input's own size (`own_size`: a resize's, an echo's, another delay's),
  else the frame's. It paints its input into the write side at that size,
  cleared to transparent black first. At the frame's size it paints in the
  frame itself; at another size it paints in `frame.at(held)`. A size
  change (the window, a cap, a resize's `size`) remakes the write side only,
  so the next frame still reads the frame before at its old size, fitted. No
  frame goes blank but the very first. An input that reads nothing this
  frame (`reads`) leaves the pair unwritten (ruling R7, T2): next frame the
  delay reads nothing, and the faces fall back to the pattern, as for a
  channel with nothing on it.
- **What a consumer gets.** `Delay.paint(frame, dst)` lays the read side
  into `dst` by the refit pass (`Renderer._refit`, cover). `Delay.image(frame)`
  is the read side when it is the frame's size. Otherwise it refits it once
  a frame into a half-float frame target of its own (`name#fit`), so the
  `IMAGE` contract (a picture at the frame's size) holds for every
  consumer. A loop of effects alone (`delay → zoomblur.2 → composite.under`,
  `composite → delay.image`) is half-float throughout.
- **No params.** Decay, mix and tint are an effect's or a composite's job
  after the delay (`blend`, `huecycle`, a composite at an opacity). The
  delay is exact: a frame late, nothing else.
- **The own-size rule.** `Node.own_size(frame) -> tuple[int, int] | None`
  is None on every node before this plan.

  | Node | `own_size` |
  |---|---|
  | `Delay` | its read side's size while it holds a frame |
  | `ResizeNode` | its computed size |
  | `EchoNode`, `DreamNode` | the ring's echo size while they read |
  | `Effect` | its `image` input's, through it |
  | `SwitchNode` | its pick's |

  An `Effect` whose own size is not its frame's size makes its pass at
  `frame.at(own)` (that size's pool) and refits the result into its
  consumer. That is how "an effect after a resize runs small" works. Every
  node of plan 33 has none, so nothing it draws changes: no golden moves.
- **The refit pass.** `render.REFIT_FS` takes a texture, a crop rect in its
  uv, a scale from `media_tex.fit_scale` and a clamp rect. Outside the crop
  or the fit it writes transparent black. Inside, it passes the
  premultiplied colour through. A sampler object sets the filter (linear,
  trilinear from mipmaps, or nearest), so a shared texture's own filter is
  never changed. `Renderer._refit(tex, dst, crop=(0, 0, 1, 1), fit=COVER,
  filter="linear", clamp=None)` is used by the delay, the echoes, the dream
  and the resize.
- **Fit onto square faces.** A delay of the frame (16:10 at 960×600) wired
  into `shape.faces` (1024²) is cover-fitted. The centre square shows,
  per face, as any picture on the faces does. For the faces in screen space
  (`fx.face_map`) to line up with the window, put a `resize` with
  `fit = contain` and `aspect = square` before the delay. Then the square
  holds the whole frame letterboxed, and the screen-space mapping (which
  covers the longer side) puts it back where it was.

### E — the look-back's frames as sources (`graph.py`, `lookback.py`)

- **`EchoNode(name, k)`** (`echo.<k>`) has no inputs and outputs `IMAGE`.
  It paints ring slot `Lookback.echo_slot(k)`, which is
  `_captures[-k]`'s slot, the k-th newest commit. The crop is the slot's
  rect in the atlas, the clamp half a texel inside it so no neighbour
  bleeds, and the fit is cover. **`DreamNode("dream")`** paints the dream
  buffer while `Lookback.dream_frame >= 0` (a worker's result has landed).
  Both have `own_size` = `Lookback.echo` while they read.
- **What it reads nothing for** (`reads` False; the faces show the
  pattern, an output its ground, an effect transparent black):
  - an echo the ring does not hold yet: fewer than k commits since the
    ring was made;
  - the ring being remade, for a `dream.res` change or a frame size change
    (`_ensure` clears the captures). The echoes come back one commit at a
    time;
  - the ring not being made at all (`ring_error`);
  - the dream with no worker attached, or before its first result.
- **The ring keeps capturing while the graph reads it.** `Lookback.keep`
  is set each frame by the renderer from `Graph.reads_ring` (any
  `EchoNode` or `DreamNode` in the graph). `_capture` goes idle only when
  `dream.on` is off and `keep` is false. The wake (the composite's echoes
  and dream) still shows only with `dream.on`, so an echo on the faces does
  not also smear the picture.
- **Honest words** (`Node.said`, set in `run`, read by GRAPH's summary):

  | Node | Words |
  |---|---|
  | echo | `408×256 · every frame · the scene`; `408×256 · every 0.10 s · the scene + hands` |
  | echo, not held | `not held yet: the ring holds 3 of 32` |
  | dream | `408×256 · the dream worker's, a frame or two late` |
  | dream, no worker | `no dream worker: reads nothing` |

  What the echo holds is what the capture takes: the scene, the scene with
  the hands (`history.holds`), or the scene over the backdrop with
  `backdrop.history`. It is 8-bit, at `dream.res` on its short side.
- **No loop check is needed.** An echo is read before this frame's
  capture writes, and its node has no inputs.

### Z — the resize (`graph.py`, `view.py`, `params.py`, `preset.py`)

- **The name is `resize`.** Not `scale`: GRAPH's picker already offers a
  `scale` modifier (mul, offset, clamp on a value), and `view.media_scale`
  is the layer's size on a face. Not `crop` or `downsample`: the node's
  point is the size it makes, which may also be up, and crop is a param.
- **Its params** (per instance, `resize[.<n>].<p>`, group `resize`, a
  preset's values, all modulatable, declared from the graph by
  `params.declare_resizes`):

  | param | kind | values | default |
  |---|---|---|---|
  | `size` | enum | `16 32 64 128 256 512 1024 2048` (the long side, px) | `256` |
  | `aspect` | enum | `input`, `square` | `input` |
  | `fit` | enum | `cover`, `contain`, `stretch` (crop into the output) | `cover` |
  | `filter` | enum | `linear`, `nearest` | `linear` |
  | `crop_x` | continuous | 0–1, the crop's centre, from the left | 0.5 |
  | `crop_y` | continuous | 0–1, the crop's centre, from the top | 0.5 |
  | `crop_w` | continuous | 0.01–1, the crop's width, of the input's | 1.0 |
  | `crop_h` | continuous | 0.01–1, the crop's height, of the input's | 1.0 |

- **Size model: pixels, stepped, not a factor.** The output is `size` px
  on its long side. The short side follows the input's aspect (`aspect =
  input`: 256 of a 1920×1080 frame is 256×144), or equals it (`square`:
  256²). It is never a factor of the input, for three reasons. First, the
  owner's numbers are pixels ("64/128/256/512"). Second, a factor would make
  a delay's buffer follow the window and the render cap: the rig at 1080p
  and the laptop at 960×600 would hold different feedback. Third, a factor
  modulated smoothly would remake textures every frame. The steps are
  powers of two, so a route on `size` steps through eight sizes, and
  `SIZED_KEEP_FRAMES` keeps the textures it left. A crop never changes the
  output size: `fit` decides how a crop of another shape fills it, as
  `media.<c>.fit` does a channel.
- **Crop as a centre and a size.** `crop_x` and `crop_y` are the rect's
  centre, `crop_w` and `crop_h` its size, all normalised on the input, y
  from the top. A zoom is one route on `crop_w` and `crop_h`; a pan is one
  on `crop_x` or `crop_y`. Any of them can be animated by an LFO, an
  envelope or a knob without a rebuild, since the params are values, not
  the graph. A rect past the input's edge reads transparent black there.
- **Filtering.** `linear` samples bilinearly. When the crop shrinks by more
  than 2× on either axis, the input's mipmaps are built and sampled
  trilinearly, as the look-back's downsample does, so 1080p into 64²
  shimmers no more than the echoes do. `nearest` samples nearest,
  unmipmapped: hard pixels. It stays nearest when the resize's picture is
  laid onto a bigger consumer, so `resize (64, nearest) → shape.faces` is
  pixelated faces.
- **Its own size, on purpose.** `ResizeNode.own_size` is its computed
  size whatever its consumer asks. It asks its input for the input's own
  size, else the root frame's (`size_for`). Its picture is a half-float
  target `(name#own, size)` made once a frame when pulled, then pruned by
  `_prune_sized`. The pull is lazy, like a channel's. A delay fed by it
  holds that size. An effect after it runs at that size (the `Effect`
  own-size rule, D). A consumer of another size gets it fitted by cover,
  with the resize's filter.
- **How it composes:**
  - `scene → resize → delay → shape.faces`: feedback at 64²–256² on the
    faces. The delay holds `size`², not 1080p.
  - `channel.a → resize → acid.2 → shape.faces`: a clip's effect run at
    256×144 rather than 1024².
  - `delay → resize → delay.image`: each loop of feedback is cropped. A
    crop of 0.9 is a zoom-in tunnel that the delay compounds.
  - `resize → switch.in3`: a switch's pick still makes only what it picks
    (`Graph.pulled`).
  - `resize → pattern.media`: the layer takes the resize's size as its head
    size (`PatternNode.size_for`).
  - `resize → output.2.image`: a low-resolution output, with `nearest`
    for a pixel look.
- **Under plan 35** (amended 2026-10-25). The node is made by
  `build_graph`'s `_Build._make`; plan 33's `MAKERS` and `_Wiring` are
  gone.
  - A resize no wire takes to an output's port, All outputs' or
    `lookback.capture` is not built. It is drawn faint, and its params stay
    while its entry does (`declare_resizes` follows `GraphSpec.resizes`,
    not the reach), as a switch's `select` does.
  - A resize reached with no input is dormant, "resize is fed by nothing
    here: wire its input".
  - `resize → delay.image` is made into the delay's write by `_Build.build`,
    before the internal `Capture`, at the resize's size
    (`DelayWrite.held`).
  - Its goldens (`resize-faces`, `resize-crop`) are `/6` wired frames, the
    factory frame's six wires plus the resize's. Each is drawn under the
    window's mutes, as plan 35's wired fixtures are (`WIRED_FIXTURES`).

### G — GRAPH (`graphview.py`, `ui_graph.py`)

Amended 2026-10-25: plan 35's GRAPH (its G) built most of this section.
What it built, and what is left to T5, follows.

- **The picker** (built by plan 35) adds `delay` and `resize` under
  **pictures ▸**, and `echo.1 (newest)`, `echo.2` … `echo.32 (oldest)` and
  `dream` under **look-back ▸**. Each lands unwired, faint and "reaches
  nothing", with the section given the wired-frame marker if it has none
  (`_with_frame`). An echo or the dream already in the section is drawn
  disabled, and a second add is refused in words. Delete removes the
  node's entry and its wires (plan 35: delete works on everything).
- **One node per delay** (built by plan 35). The canvas draws the
  section, and a delay's `image` port is its pin `rin:<delay>/image`.
  Nothing internal, `delay(write)` included, is drawn.
- **Areas** (built by plan 35, row 389):

  | Node | Area |
  |---|---|
  | `delay` | MEDIA, beside the channels: a picture that starts a branch |
  | `echo.k`, `dream` | LOOK-BACK: the ring's pictures |
  | `resize` | EFFECTS, or MEDIA when made of the media alone (`media_made`; T5 adds the resize to `MEDIA_MADE`) |

  **The cable into a delay's image runs back by design** (`returns`, as
  is the cable into `lookback.capture`): it is the picture kept for next
  frame. The original's "a delay, an echo and the dream count as heads in
  `media_made`" is dropped. Each sits left of EFFECTS already, so what it
  feeds runs right.
- **The side panel** (T5). A resize's eight params are rows through
  `_param_rows`, with no new code: `OWNERS["resize"]` puts `resize[.n].*` on
  its node, and Learn and Unbind come with the label. The canvas takes the
  render `ResizeNode` (its stand-in class is deleted). A node's `said` is
  its summary's first line, after "reaches nothing" when faint.
  `home_page` sends an echo and the dream to LOOKBACK (built). A delay and
  a resize have no page.
- **A loop drag is refused, red, in words** (built: T1 and plan 35). The
  canvas's dry run (`Edit.refusal` → `_land` → `read_graph`) sees the loop
  at read. So `scene → shape.faces`, a loop through `shape →
  scene.geometry`, is refused before it lands, in `LOOP_FACES`' words,
  which say to put a delay between. T5 gives a wired frame's other loops
  (`acid → wobble → acid.aux`) the same pointer (`LOOP_PLAIN`).

## Not in this plan

- **The composed output as a source** (`fx`, or `output.N`, into a
  delay). *Amended for plan 35: there is no `frame` or `fx`. The picture
  an output shows is whatever is wired into its `image` (All outputs'
  else), and that source can be wired into a delay as well. The rest of
  this bullet is the plan 33 model T1 was built on, and still holds for an
  old section's read.* The picture after the run is its last effect's (`acid → delay`).
  Before the run it is `history`. `frame` stays the run's head only.
  A wire out of `frame` into anything but an effect's `image` or
  `fx.image` (`frame → delay.image`, `frame → acid.aux`, `frame →
  output.2.image`) is refused at read, in words that name `history` and
  the run's last effect (`FRAME_SOURCE_REFUSAL`, T1). Today it lands
  dormant ("no frame this frame"). `frame → acid.2.image` on a branch that
  never reaches `fx.image` stays dormant at build, as today. The window's
  own composited frame (the hands laid over at the output, the dim) is not
  a node.
- **Per-delay decay, mix or fit params.** These are effects after the
  delay and a `resize` before it.
- **A delay of more than one frame** (`delay.frames`). Chain delays
  (`delay → delay.2.image`), or read the ring (`echo.k`).
- **Echoes at their own resolution or bit depth.** The ring stays one
  RGBA8 atlas at `dream.res`. A full-resolution history is a delay chain.
- **Per-instance faces** (plan 33's next step), the other pages as views
  of the graph, and the default graph's compositing order: as plan 33
  left them.
- `apc40.py`, `midi.py`, `bindings.default.json` and the desk are
  untouched (Dylan's). No factory preset gains a delay, a resize or an
  echo.

## Risks

- **The goldens are the contract.** Every node before this plan has no
  own size, so the `Effect` own-size path and the refit pass never run for
  a factory preset or a plan-33 fixture. All 693 must match after T1–T5,
  and a miss is a bug, not a re-record. *Amended for plan 35: T1–T3's 24
  goldens are in plan 35's base, which has 741 in all, and T4 adds 16
  (757). Plan 35's signature cases must also still match.* The new fixtures add 40 goldens (5
  fixtures × 8 states): `delay-faces`, `delay-trails`, `echo-faces`,
  `resize-faces` and `resize-crop`. The golden rig is new per shot and draws
  `FRAMES` (8) frames, so a delay golden is seven feedback steps from a
  cleared buffer, deterministic on the recording GPU.
- **A plan-34 `/5` preset on a plan-33 build** fails its graph section
  ("unknown node kind 'delay'"). That build then draws the default graph
  with a load note, losing the run and every branch for that load. The
  schema stays `/5` (the constraint), so both Macs must run this build
  before anyone saves a delay, a resize, an echo or the dream. This is the
  same rule as plan 33's `/5`, one step further. Check 341. *Amended for
  plan 35: a wired frame that round-trips into `/5` words, plan 34's
  among them, still saves `/5` (R10), and this risk stands for it. A frame
  that needs plan 35's vocabulary saves `/6`, which a plan 33 build
  refuses outright (check 352).*
- **Feedback through the scene is 8-bit there.** The scene's target is
  RGBA8, so `scene → delay → shape.faces` quantises once a loop. A decay
  below 1 by an effect leaves a faint floor rather than fading to black.
  A loop of effects alone (`delay → … → delay.image`) is half-float
  throughout. The faces' picture (`face_pic`, RGBA8, mipmapped) is
  display only.
- **The faces show an opaque picture fully.** The scene's picture on an
  opaque ground has alpha 1. On the faces (`shade = 2.8 · a`) last frame's
  black background then shows as black faces, not see-through ones. That
  is the nature of a picture on the faces since plan 33. Check 332 judges
  it.
- **Frame cost.** A 1080p delay is 2 × 16.6 MB (f2) and one paint of its
  input a frame. A 256² one is 2 × 0.5 MB. A resize is one refit pass at
  its size (mipmaps built when it shrinks more than 2×). An echo is one
  refit pass per consumer size. Check 340 times them on SYSTEM.
- **Mipmaps on a shared texture.** A linear resize of more than 2× builds
  its input's mipmaps (the scene's, a pool texture's). The texture's own
  filter is put back and the resize samples through a sampler object, so
  every other reader samples as before. The mip levels' memory stays
  allocated.
- **The loop check's hidden edges are conservative** (an old section's
  read; in a wired frame the wires say these edges, and only
  `HIDDEN_EDGES` are hidden, row 393). `history` reads
  `scene` even where the history's image is wired from something else, and
  `frame` reads `history` on every pipeline. A wire that would loop on the
  scene's pipeline is refused even if the only output is the hands-only
  pipeline. A loop the build would have allowed is never refused: such
  wires are dormant at build today.

## Decisions

Rows 353–371 of [`DECISION-REGISTER.md`](../DECISION-REGISTER.md) (written
by T6). "(rec)" is a recommendation the build takes. The owner said
"build" on 2026-10-24. None is flagged as needing the owner. Every one is
cheap to reverse before a preset that uses it is saved, and the expensive
one (row 371, the schema) was the constraint given.

353. **A `delay` picture node, z⁻¹** (owner, 2026-10-24: "build A"): its
     picture is last frame's input. A loop through one is legal.
354. **Delay buffers are the renderer's**: a ping-pong pair per delay
     name, RGBA half-float, swapped at the frame's start, kept by name
     across graph rebuilds, released `SIZED_KEEP_FRAMES` frames after the
     delay leaves the graph (rec). Others: RGBA8 (feedback with a decay
     below 1 sticks); a pair per graph (an edit elsewhere cuts the
     feedback).
355. **A delay has no params**: decay, mix and tint are an effect's or a
     composite's after it; the fit is a resize's before it (rec). Others:
     `delay.mix`, `delay.decay`, `delay.fit`.
356. **Strict z⁻¹**: reads nothing on the first frame and after a frame in
     which it was not written; a size change remakes only the write side,
     so no frame is lost (rec). Other: hold the last picture while the
     input is absent (a freeze).
357. **A delay holds its input at the input's own size, else the frame's**
     (rec). Others: always the frame's; always `FACE_PIC`².
358. **A picture of its own size laid into a consumer of another shape is
     fitted by cover, about the centre** (`OWN_FIT`); another fit is the
     resize's `fit` (rec). Others: stretch; a fit per consumer port.
359. **The loop refusal at read**: the default graph's hidden edges
     (`FRAME_EDGES`) join the loop check (`sink_loops`), an edge into a
     delay is no dependency, the later wire in the section's order is the
     one refused, and the words name the faces, the backdrop or the frame
     and point at a delay (owner, 2026-10-24: "with the loop refusal fix";
     the words and the order rule rec). Other: refuse every wire on the
     loop, as `wire_loops` does (a drag would be refused by the run's own
     wire's words). *Amended for plan 35: in a wired frame `FRAME_EDGES` is
     superseded by row 393's `HIDDEN_EDGES`, and an explicit loop refuses
     every wire on it (plan 35 R5). `FRAME_EDGES` stands for reading an old
     section before it migrates. A wired frame's other loops point at a
     delay too (`LOOP_PLAIN`, T5).*
360. **Echoes and the dream are declared by a node entry**
     (`{"kind": "echo", "index": k}`, `{"kind": "dream"}`), as a switch is
     (owner, 2026-10-24: "i also want to be able to do b"; the entry rec).
     Other: undeclared wire names like `media.a` (an unwired echo would
     have no place on the canvas).
361. **An echo the ring does not hold reads nothing**: before k commits,
     after the ring is remade (`dream.res`, the frame size), or with no
     ring; the dream before its worker's first result (rec). Others: the
     oldest held; opaque black.
362. **The ring keeps capturing while the graph reads an echo or the
     dream, with the look-back off**; the wake shows only with `dream.on`
     (rec). Other: an echo needs `dream.on` (and its wake, or
     `dream.echo_mix` 0).
363. **Echoes are what the capture holds, at the ring's size, cadence and
     8 bits, said in the node's words on GRAPH** (rec). Other: a ring of
     their own at the frame's size.
364. **The downsampler is named `resize`** (rec): not `scale` (GRAPH's
     `scale` modifier), not `crop` (a param of it).
365. **Resize size: the long side in pixels, 16–2048 in powers of two,
     with aspect `input` or `square`, never a factor of the input** (rec).
     Others: width × height free; a factor; aspect following the crop
     (the size would move with an animated crop).
366. **Resize crop: centre x, y (y from the top) and width, height,
     normalised on the input, modulatable; past the edge is transparent;
     `fit` (cover, contain, stretch) fills the output** (rec). Other: a
     corner rect (a zoom would need two routes).
367. **Resize filter: `linear` (trilinear from mipmaps past a 2×
     shrink) or `nearest` (hard pixels, kept when laid on a bigger
     consumer)** (rec). Other: always linear, no mipmaps.
368. **A resize's, a delay's and an echo's size is their own**, breaking
     plan 33's "the consumer decides" on purpose; an effect after one runs
     at its size (owner, 2026-10-24: "avoid writing a 1080p buffer into
     all the faces"; the effect rule rec). Other: the effect at its
     consumer's size (the resize's saving lost after it).
369. **Resize params are per instance, declared from the graph
     (`params.declare_resizes`, as `declare_switches`), group `resize`, a
     preset's values, no module** (rec).
370. **GRAPH: delay, echo and dream in MEDIA, resize in SHADERS or MEDIA
     by `media_made`, the cable into a delay a return by design, the
     resize's params side-panel rows** (rec). *Amended for plan 35 (row
     389's areas): delay in MEDIA, echo and dream in LOOK-BACK, resize in
     EFFECTS or MEDIA by `media_made`.*
371. **The schema stays `/5`**: the new words are `/5`-only by
     `uses_free_words`, and a plan-33 build reads such a section as
     unknown and draws the default graph with a note. Both Macs on this
     build before saving one (the constraint given for this plan). Other:
     `/6` with its own ladder refusal. *Amended by plan 35's row 385
     (R10): `/6` exists now, for plan 35's vocabulary. Plan 34's words are
     `/5` words, so a wired frame using them that round-trips saves as `/5`
     and this row holds for it.*

## Hand checks (group AD, 332–341; as the spec listed them, written into `11-hand-checks.md` by T6)

Amended 2026-10-25 for plan 35: the ids are the wired frame's. Run them on
the plan 35 build, after group AE's 342 (a new preset and its scene
starter) or on the factory frame.

- **332.** The infinite mirror: `scene → delay → shape.faces` on the
  laptop. The faces show the shape within the shape, a frame deeper each
  frame. Judge the look, black faces included.
- **333.** Trails: the `delay-trails` fixture's graph, as it migrates
  (`delay → zoomblur.2 → palette.2` with palette.2's val slice to 0.6,
  `scene → composite.2.under`, `palette.2 → composite.2.over`,
  `composite.2 → delay.image` and `output.1.image`; ruling R6, T2). Trails
  stream toward the centre and fade within a few frames; nothing sticks or
  burns to white.
- **334.** The drag: `scene → shape.faces` on GRAPH goes red with the
  faces words, and does not land. Through a delay it lands, and the faces
  show the scene. A loop of effects (`acid → wobble → acid.aux`) goes red
  with words that say to wire it through a delay.
- **335.** `echo.4 → shape.faces` with the look-back off. No wake on the
  picture. Change `dream.gap` and see the cadence; change `dream.res` and
  the faces go back to what they show unwired for four commits.
- **336.** `dream → shape.faces` with the dream worker running. Without
  it, the node says "no dream worker: reads nothing".
- **337.** `scene → resize (64, square, nearest) → delay → shape.faces`.
  Pixelated feedback; an LFO on `resize.crop_w` and `crop_h` zooms it
  without a hitch.
- **338.** `channel.a → resize (256) → acid.2 → shape.faces` against
  `channel.a → acid.2 → shape.faces`. `acid.2`'s SYSTEM line drops.
- **339.** A window resize, and the render cap changed, mid-feedback. No
  black flash and no error.
- **340.** The frame cost on SYSTEM: `delay(write)` at 1080p against 256²,
  a resize, four echoes on the faces (with 351, in one sitting).
- **341.** A preset with a delay on the factory frame, saved on this build
  (it saves `/5`, R10) and opened on a plan-33 build: a load note and
  that build's default graph, as expected. A frame that needs plan 35's
  vocabulary is 352's case instead: refused there. Both Macs on this
  build.
