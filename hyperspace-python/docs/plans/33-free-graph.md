# Plan 33 — the free graph: effects where they are wired, faces and backdrop as inputs, the FX stack retired

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

Rows 341–352 of [`DECISION-REGISTER.md`](../DECISION-REGISTER.md), written
there when the build lands. "(owner)" is answered in the owner's words;
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
