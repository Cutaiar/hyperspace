# Plan 40 — patches: a group of nodes and its boundary, saved once, spawned anywhere

**Status: built (2026-10-28)** on `plan-40-build` (T0–T5 and the review
fixes: PRs #269, #274, #272, #271, #276, #277, #278; T6, these docs, its own
PR into `plan-40-build`); it goes to `main` in the final PR, which the owner
merges. At e0675a6: the fast tier 4320 passed, 2 skipped; the full suite
(`--all`) 4551 passed, 2 skipped; the goldens 144 passed (the 136 before and
8 grouped-twin proofs), none moved, none re-recorded;
`tests/fixtures/frame-signatures.json` unchanged. Register rows 501–536
(501–510 are D1–D10 as built; 511–536 the build's rulings, two of them, 521
and 524, waiting for the owner; 25 rows were assigned, so the overflow is
526–536). Hand checks 394–401, group AK. **Both Macs on this build before a
preset with `groups` is shared**: an older build refuses an `/8` file.
"What changed in the build" at the end says where the build differs from
the text above.

**Agreed 2026-10-27.** Every decision is the owner's,
answered the same day in the session that wrote this; D1–D10 below carry
his words. The build plan follows, as 37A's did. From
the owner's ask of 2026-10-27, while plans 37–39 are in flight: "the
concept of patches … group some nodes together and then save that grouping
of nodes and the connections between them (crucially, the connections
coming in from the outside of that group and the connections going out of
that group) as a template … that we can just arbitrarily spawn in a new
preset." And: "if there's a bunch of bindings that are coming from the
APC40 going into one of these template group things, and then the APC40
isn't connected, the system should gracefully tell you … should you
connect the controller, it should automatically set up those bindings."
And: "a node that represents a grouping of other nodes." The goal in his
words: "compose effects together, compose interesting things that we like
together, and then easily and quickly be able to add them into presets."

The old answer — a module preset per param group, then a whole preset —
"didn't really work because they weren't really composable." This plan
says why in the map below, and replaces it with one noun.

Independent of plans 37A, 37B, 38 and 39; "Independence" at the end lists
the seams.

A side ask from the same session, its own PR and not part of this plan:
the GRAPH page's side pane (the one that opens when a node is clicked)
must be resizable — "for some UI, the little sidebar … is just not wide
enough." Built and merged the same day: PR #266 (`main` @ f984d3b), a
grip on the column's edge, the width kept per Mac in `<machine>/ui.json`.

## What is there today (the map, `main` @ f2351a0)

File and line references drift; the names hold.

1. **Two reusable fragments exist, and neither carries the graph.** A
   *desk template* (`<library>/desk/<slug>.json`, `hyperspace.desk/1`,
   plan 24 C3) carries preset-layer desk rows and, since plan 28,
   modifiers; a preset names it (`desk_template`) and keeps only its
   overrides (`preset.expand_desk` 595, `compact_desk` 608). An *fx
   module preset* (`library/fx/*.json`, `hyperspace.preset/1`) carries the
   `fx.*` values of one group, and since plan 33 R12 a loaded one
   replaces the loaded graph's main run (`Presets._fx_module` 1260,
   `graphmigrate.module_runs`). Neither carries graph nodes, wires,
   routes, macros, LFO or envelope membership, or layout; the fx module
   cannot keep two effects it chains apart from a third the preset had,
   and it cannot say where it goes. That is the "not composable".
2. **The preset is already a fragment's vocabulary.** A `/7` preset is
   `graph` (`nodes` entries and `wires` `{"from": "<node>[.<pin>]", "to":
   "<node>.<port>"}`), `values`, `routes`, `desk`, `modifiers`, `macros`,
   `lfos` / `envs`, `layout`, `media` (`Presets.document` 1151). Every
   node kind a patch would hold is one that can exist twice and is named
   by the instance rule — `acid`, `acid.2` (`graph.instance_name` 405),
   `composite.2`, `switch.2`, `delay.2`, `resize.2`, `copy.2`,
   `hands.2`; `mod.<n>` (`modifiers.next_id` 212, one past the highest
   held); `lfo.<n>` / `env.<n>` (`modbank.next_id` 129: never reused in a
   session); `macro.1`–`macro.8` (eight, fixed).
3. **A node's params are declared when the graph lands**, not by the
   editor: `fx.declare` makes `fx.acid.2.*` (fx.py 470), `declare_switches`
   and `declare_resizes` theirs (params.py 962, 1038), `declare_modifiers`
   `mod.<n>.*` (routing.py 1578), the banks their voices'. Removing a node
   removes its params; **a route onto an id that goes away stays, dormant**
   (fx.py 471, modifiers "a route on its lane stays, dormant", routing.py
   2557). So an id can be renamed by removing and declaring, and the table
   never breaks.
4. **Every edit is one door.** The canvas lands a render edit by re-reading
   the section as a preset would, one undo step, then `gs.land`
   (`graphview.Edit._land` 3733); a modulation edit is the table's own
   call (`Bindings.add` / `bind` / `move_route` / `add_modifier`,
   `bank.add`, a macro subscriber). A batch of routes goes through the
   referee (first performer per target wins, the rest to `table.dropped`
   with a reason; `routing.referee` 1114); a desk row through `bind`
   replaces every same-layer row on the overlapping control and says "let
   go" (routing.py 2362). One `undo.push(label, load=True)` before a batch
   makes it one step (`undo.py` 390; the marks carry the graph section,
   `library.Marks.take` 1372).
5. **A binding on a device the rig lacks is already dormant, never
   dropped**, and already comes alive by itself. A performer row on a
   scheme no device feeds waits (`routing.is_continuous` 346, "decision
   11"; `Router.feed(scheme, None)` 2889; a name the map lacks is lane −1,
   2666). A preset-layer desk row is kept whatever is plugged in
   (`Bindings.set_desk` 2236 never asks the registry) and nothing
   dispatches it until the port is there; when the APC40 appears,
   `midi.Ports.retry` → `MidiIO._connected` → `_enter` relights the whole
   desk from the table (midi.py 412–439). A hands row reads the moment
   the feed is live. **What is missing is the saying**: the SYSTEM page
   lists listed devices (`apc40 · midi · lost`), GRAPH greys a device
   node that is not connected and draws a grey placeholder for a role
   the rig does not list (`graphview.PLACEHOLDER_STATUS` 639, "not in
   this rig: its cables wait for it", `SCHEME_ROLE` 631), the ROUTING
   bar says "source not live" on hover — but nothing names, for the
   loaded preset, *which devices it wants and does not have*, and nothing
   says anything when one arrives. The registry's listeners fire on
   `open_all`, on a retried `open()` and on a `config.toml` change
   (`DeviceRegistry._changed` 1538), **not** when a `lost` device's
   hardware comes back, because that happens inside the adapter.
6. **The canvas has selection but no group.** `imgui_node_editor`'s native
   multi-select is there and Delete walks it (`ui_graph._delete` 2575);
   `_selection` returns one node (1606). Collapsed is a per-session fold
   saved nowhere (plan 28 N7). The desk template node `template:<name>` is
   the one subgraph drawn as a node: collapsed by default, `+` opens its
   rows as cables, an edit inside writes an override (graphview 605–620,
   ui_graph 434–446). The `group:` kind is a node per param group
   (`group:tempo`), not a grouping. Areas are drawing only and stored
   nowhere (`graphview.AREAS` 1837). Positions are the preset's `layout`
   for the look's nodes, the show's for the rig's (`graphview.home`
   2393).
7. **The word is taken.** `hyperspace/patch.py` is the *modulation graph
   as data and its evaluation order* (plan 28 N0): `Router.build_patch`,
   `router.patch_notes`, `graphview` imports it as `patchmod`. No user
   sees the word but as "k patched" on a node summary.
8. **The hard rule (plan 36, 2026-10-26).** The graph is WYSIWYG: no default
   graph, no hidden edges, no auto layout. A patch obeys it or does not
   land.

## The idea in one paragraph

A **patch** is a preset fragment with a boundary: the nodes of a region
of the graph, their values, the wires among them, the routes and
subscribers among them — and every cable that crosses the region's edge,
recorded as a **port**. A port that crosses to the *rig* (a knob, a
hand axis, an audio band, a pad stick, an OSC fader) is kept as the
absolute address it is, because that is what it means: *this* knob, *that*
hand. A port that crosses to the *host preset's* graph (the scene coming
in, the outputs going out, an LFO onto the shape's brightness) is kept as
its type and the name it was attached to, because the next host may or
may not have that node. Spawning a patch lands its nodes under fresh
ids, lands its rig-side bindings verbatim (dormant where the rig lacks
the device, and said), and leaves its host-side ports as open pins on a
**group node** — or splices them, when you dropped the patch on a cable.
A group node is a fold of the canvas, not a node of the renderer:
`build_graph` sees the flat nodes it always saw, so no golden moves and
the renderer learns nothing. Group, save as patch, spawn, ungroup: four
verbs.

## What this plan does

### P1 — the patch as data (`patches.py`, pure)

A new leaf module, `hyperspace/patches.py`, pure data and pure functions
like `graph.py`'s reader and `graphmigrate.py`.

**The file.** `<library>/patches/<slug>.json`, `hyperspace.patch/1`,
factory ones in `hyperspace/library/patches/`, the user's shadowing them
by slug like any group, listed and written by `library.Library` as a
registered `DocKind` (library.py 581) through the cloud folder of plan
25. The keys are **the preset's own**, so `Presets` parsing is reused,
plus one:

```json
{"schema": "hyperspace.patch/1", "name": "acid wash",
 "note": "acid → wobble through a delay; K1 the speed, the right hand the amount",
 "nodes":  [{"kind": "effect", "file": "acid"}, {"kind": "effect", "file": "wobble"},
            {"kind": "delay"}],
 "wires":  [{"from": "acid", "to": "wobble.image"}, {"from": "wobble", "to": "delay.image"}],
 "values": {"fx.acid.on": true, "fx.acid.speed": 0.4, "fx.wobble.on": true, "fx.wobble.amount": 0.3},
 "modifiers": [{"id": "mod.1", "kind": "smooth", "in": ["hand:right.y"], "attack": 0.05}],
 "routes": [{"source": "mod:1", "target": "fx.wobble.amount", "op": "push", "value": 0.3},
            {"source": "lane:0", "target": "fx.acid.speed", "op": "push", "value": 0.1, "scale": "master.gain"}],
 "desk":   [{"source": "cc:0:48", "target": "fx.acid.speed", "op": "abs", "feedback": "ring"}],
 "macros": {}, "lfos": [], "envs": [],
 "ports":  [{"id": "in",  "type": "image", "to": "acid.image",   "was": "scene"},
            {"id": "out", "type": "image", "from": "delay",      "was": "output.all.image"}],
 "layout": {"render:acid": [0, 0], "render:wobble": [260, 0], "render:delay": [520, 0], "mod.1": [0, 200]}}
```

(Corrected in the build: the first route's source read `mod:0`. A
modifier's lane is `mod:<n>` for `mod.<n>` (`modifiers.Modifier.address`),
so `mod.1`'s is `mod:1`; `mod:0` is no lane and the route would have lain
dormant. `tests/fixtures/patches/acid-wash.json` is this example with
`mod:1`; register row 512.)

- `nodes`, `wires`, `values`, `modifiers`, `macros`, `lfos`, `envs`,
  `layout` are a preset's, read by the same code, with the patch's own ids
  (`acid`, `mod.1`, `lfo.1`: the lowest, as if the patch were alone).
  `layout` is relative to the patch's own origin.
- **The boundary is classified at read, not stored twice.** A route or
  desk row whose source is a rig scheme (`cc:`, `note:`, `pitch:`, `key:`,
  `pad:`, `hat:`, `axis:`, `hand:`, `hands:`, `lane:`, `ext:`, `seq:`, an
  OSC role; everything but the patch's own `mod:` / `lfo:` / `env:` lanes
  and macros) is a **rig port**, kept verbatim. A route whose target is
  not a patch param (`view.bright`), a macro `base` subscriber onto one,
  a modifier input from a host lane (`lfo:0` of a host LFO) is a **host
  port** and is written in `ports` with `was`. `patches.read(doc)` returns
  the fragment and both lists; `patches.check(doc)` the refusals.
- **What a patch may hold**: what can be made twice — effects, composites,
  switches, delays, resizes, copies, hands instances, modifiers, LFO and
  envelope voices, macros. **Refused at lift**: the frame's singletons
  (`scene`, `shape`, `pattern`, `backdrop`, `lookback`, `hands.layer`,
  `hands.guide`; `graph.FRAME_KINDS` 992), the outputs and `output.all`,
  the clouds and the camera (the rig's, `graphview.NOT_REMOVABLE` 2740),
  media channels (a channel is a bin of the Mac's files; a patch may read
  one through a port: `was: "channel.a"`), the sequencer, the lane
  envelopes 1–5 by *identity* (a patch may carry an envelope; it spawns as
  6+). A patch that is nothing but routes and modifiers is legal: "a
  breathing LFO, smoothed, onto brightness" is a patch of one LFO, one
  modifier and one host port.
- **`patches.lift(spec, table, reg, layout, node_ids) → doc`**: cut a
  patch out of the loaded preset. Renames the members to the lowest ids,
  rebases the layout, classifies every crossing cable. The pure half of
  **save as patch**. (Corrected in the build: it is `lift(spec, table,
  values, layout, node_ids) → (doc, refused)`; its third argument is the
  registry's performance snapshot, a dict, so it stays pure, and the
  refusals come back in words beside the file; row 515.)
- **`patches.spawn(doc, host_spec, host_table, host_banks, at) → Landing`**:
  a `Landing` is the rename map (`acid` → `acid.2` by `_new_instance`'s
  rule, `mod.1` → `mod.<next>`, `lfo.1` → `lfo.<next>` by the bank's
  high-water rule, `macro.N` → a free macro or a refusal), the rewritten
  nodes, wires, values, modifiers, routes, desk rows, subscribers, the
  layout moved to `at`, the group (P2) and the notes. **Pure**: it writes
  nothing. The app lands it through today's doors (P3). (Corrected in the
  build: the host is one argument, `spawn(doc, host, at, *, patch)`, with
  `patches.Host.of(spec, table, banks, held)` reading the host's names,
  bank room and used macros; a patch's envelopes are `env.6` and up in the
  file too, row 512.)
- **Round trip**: `lift(spawn(p))` is `p` again up to ids and position, a
  property test over every factory patch and over a patch cut from each
  factory preset's effect run. (Corrected in the build: no factory patch
  ships, and the "effect run" of a `/7` preset is its main run into All
  outputs, `graph.run_back(spec, "output.all.image")`; 9 factory presets
  have one and round-trip, the other 16 are named in the test.)

### P2 — the group node (the preset's, drawn on GRAPH)

- A **group** is a region of the loaded preset: `{"id": "group.1",
  "name": "acid wash", "patch": "acid-wash", "nodes": ["render:acid.2",
  "render:wobble.2", "render:delay.2", "mod.3"], "open": false}`, in a new
  preset key `groups` beside `layout`. `patch` is provenance (the slug it
  was spawned from, or absent for a group made by hand); nothing re-reads
  the file. **Decision D4.**
- **Not a render node.** `graph.build_graph`, `signature`, the goldens
  and the frame-signature fixture see the flat graph; the renderer never
  learns the word. A group is a fold on the canvas and a list in the file.
- **Collapsed** (the default, as every node is since N7), the group node
  draws: its name; one pin per host port (typed: an `image` inlet, an
  `image` outlet, a `geometry` inlet …), each carrying the cable the host
  attached there, or open; one value pin per **boundary param** — a
  member's param that a rig-side row or a host-side route lands on — with
  its cable; and, when 37A is in, the thumbnail of its last picture
  outlet. Its status line is P4's ("waits for apc40, leap"). Internal
  cables are not drawn while it is collapsed: **this is the one place
  cables are not on screen, and the owner asked for it; `+` is one press
  away and nothing inside differs from what `+` shows. D4 asks him to
  confirm it against the hard rule.** (He did: D4. Corrected in the build:
  an *open* host pin is drawn only for a group spawned this session — the
  file keeps what the graph holds, so after a save and a reload a pin
  never wired is gone and `+` shows the member's own port, row 523. The
  folded node also has an out pin per member lane leaving it and a row per
  member modifier input read from outside, so every crossing cable has a
  pin, row 522.)
- **Open** (`+`, as the template node opens), the members are drawn in
  place at their own positions inside a titled, tinted region with the
  group's name, every internal cable drawn, every member editable as
  before: a route added inside is the group's, a member deleted leaves the
  group (an empty group is removed). The region moves as one when its
  title is dragged; a member dragged out of the region leaves the group
  (**ungroup one**). `-` folds it.
- **Group** (right-click on a multi-selection → **Group**): makes a group
  of the selected members that the lift rule allows, refusing the rest in
  words ("scene is the frame's; left out"). **Ungroup** (right-click on the
  group) deletes the list and nothing else. Both are one undo step.
- `preset_only` keeps showing the section's nodes; a group is of the
  section, so it shows.
- The group's own position is its members'; `layout` keeps member
  positions as today, so a preset from before this plan opens unchanged
  and an ungrouped preset is byte for byte what it was.

### P3 — save as patch, the browser, spawn (the app's half)

- **Save as patch**: right-click on a group → **Save as patch…** (name,
  note) → `patches.lift` → `Library.save_patch`. A group with a `patch`
  slug offers **Update patch** too (the file rewritten, the old text
  trashed as `save_as` does, library.py 2135). Saving does not touch the
  preset.
- **The browser**: a **patches** chip on the GRAPH head beside **new** and
  the starters, opening the list (factory then the owner's, by name, hidden
  ones out, as the PRESETS list is), each line its name, its note and its
  **boundary in words** ("in: picture · out: picture · wants: K1, right
  hand, audio band 1"). The PRESETS page gains the same list under a
  **patches** fold where "more · module presets" is today. The canvas's
  right-click menu gains **Spawn ▸** with the list. (Corrected in the
  build: GRAPH's head has no **new** chip — **new** is on the PRESET strip
  and the starters are in the canvas's picker — so **patches** is the
  head's first chip after plan 38's hold chips, row 529; the PRESETS fold
  sits after "more · module presets", which stays for the other groups.)
- **Spawn** lands `patches.spawn`'s `Landing` as **one undo step**
  through today's doors, in load order: the group's render nodes and
  internal wires by `gs.land` of the re-read section (so their params
  exist), the voices by `bank.add(n)`, the modifiers by `add_modifier`,
  the values by `lib.restore`, the routes by `Bindings.add` or
  `replace_owner`, the desk rows by `bind(write=False)`, the subscribers
  by `set_macros`, the group and its layout at the drop point. The
  preset's dirty dot lights; no file is written until a save.
- **The conflict sheet** (D3, the owner's words: "a pop-up that says,
  hey, these are the conflicts; choose a resolution for each one: the
  patch or the existing preset"). Before anything lands, `patches.spawn`'s
  `Landing` lists every rig port that collides with the host: a knob or
  button the host's preset layer already maps (`Binding.overlaps`), a
  performer source that already owns a host param, a patch route onto a
  host param another performer owns (`Bindings.owner`). If the list is
  empty the spawn lands at once. Otherwise one modal, drawn where the
  Replace / Keep prompt is drawn (`ui_routing.modal`, first in
  `Panel.draw`), lists each conflict in words — "K1: `view.bright` (the
  preset) or `fx.acid.2.speed` (the patch)" — with a two-way choice per
  row, **every row preselected to the patch** (D9), a **keep all
  existing** button that flips them, and **Spawn** / **Cancel**. Spawn
  lands the whole `Landing` with the choices applied as one undo step; a
  row the preset keeps lands the patch's row dormant-by-conflict and
  said on the group node ("K1 kept by the preset"). Cancel lands
  nothing. While the sheet is up the hands learn nothing, as with the
  Replace / Keep prompt. The sheet also lists the patch's wants (P4)
  beneath the conflicts, so a device the rig lacks is read before the
  press.
- **Where it lands** (D2): spawned from the right-click menu, the group's
  members appear at the click with the patch's relative layout — the
  patch's own, not an auto layout — and every host port is an **open pin
  on the group node**; dropped from the browser **onto a cable** whose
  type matches the patch's one inlet and one outlet, the patch is
  **spliced in** exactly as **insert** splices an effect
  (`graphview.render_insert` 4374). The side pane of a freshly spawned
  group shows one chip, **wire as saved** — "scene → in, out → output.all"
  — that lands those two cables if the host has those nodes and the ports
  are free, refused in words otherwise. **Nothing is attached by itself.**
- **Fresh ids are said**: the group's hover lists the rename map ("acid →
  acid.2") for the session.
- **A patch twice** in one preset is two groups with two id sets; its rig
  ports collide (one knob, one param) and the sheet asks, row by row;
  the losing rows land dormant-by-conflict and are said.

### P4 — what the preset wants and the rig lacks; the arrival

The owner's "gracefully tell you" and "automatically set up those
bindings". The second half is true today (map item 5); this plan builds
the first and the one missing signal.

- **`devices.wants(table, registry) → [Want]`**: for the loaded preset's
  routes, desk rows and modifier inputs, every rig-side source grouped by
  the device role that would feed it (a row's `@role` qualifier, else the
  primary MIDI role for `cc:`/`note:`/`pitch:`, else `graphview.SCHEME_ROLE`'s
  map, which moves to `devices` and `graphview` reads it there), each
  with its state: **connected**, **lost** (listed, hardware away), **off**
  (listed, `enabled = false`), **not in this rig** (no entry), and the
  rows it covers in words ("K1, K2, pad A", "right hand y", "band 1").
  Pure; tested against a bare registry.
- **Where it shows**: the group node's status line and hover ("waits for
  apc40 (lost): K1, K2 · leap (not in this rig): right hand y"); the GRAPH
  head and the PRESET strip, one chip **2 devices missing** with the same
  hover (nothing when all are there); the SYSTEM page, one line per wanted
  role the rig lacks under the device lines ("wanted by the preset:
  leap — not in this rig; 3 rows wait"). The grey placeholder node and
  the faint cables stay as they are: they are the same fact drawn.
- **The arrival.** `DeviceRegistry.poll` compares each device's `status`
  to last frame's and, on a change, calls the listeners and
  `lib.say("apc40 connected — 6 controls live")` / `"apc40 lost — 6
  controls wait"`; a device added to `config.toml` says the same through
  the `apply` path that already fires. The counts are `wants`'. The MIDI
  relight, the feeds and the placeholder's replacement are unchanged: the
  bindings were never gone.
- A **spawn into a rig that lacks a device says it at the spawn** (the
  notes line: "2 rows wait for leap"), and the sheet that P3's browser
  shows before the spawn lists the patch's wants with the same words, so
  nothing is a surprise. (Corrected in the build: the line names the rows,
  as the sheet does — "spawned acid wash: …; waits for leap (not in this
  rig): right hand y" — and leaves out a row the sheet kept for the
  preset; row 528.)

### P5 — the fx module presets are retired outright (D6, D10)

The owner, 2026-10-27: "I don't want factory patches from the 6 FX module
presets … The FX module should probably be retired outright. It is not a
useful representation of shaders anymore." And, asked whether that took
the FX page with it: "I meant only the module presets. I forgot that we
did a UI pass on the FX tab a while ago."

- **The fx module presets go**: `library/fx/*.json` (the six), the fx
  entry of "more · module presets" on the PRESETS page, the load hook
  `Presets._fx_module` and `graphmigrate.module_runs`, `FX_GROUP`'s
  defaults as a module (`Library.defaults("fx")` is the fresh values).
  Nothing is converted. A show or preset that still names an fx module in
  `modules` keeps the label, which never loaded anything (desk D3), and
  the label is dropped on its next save. `band/` (the analyzer's scenes,
  session) and `dream/` stay as they are.
- **The FX page stays as it is** (D10): the browser of the graph's effect
  nodes by where each ends (plan 33 U), its strip, `Panel.fx_selected`.
  ~~Nothing on it referred to the module presets.~~ (Corrected in the
  build: one thing did. `ui_fx.page` draws `panel._section("effects",
  "fx", …)`, whose strip under the page's title is the fx module-preset
  strip — ◀ name ▶ · save · as… · reset. It is the retired mechanism's UI,
  so `ui_presets.strip` draws nothing for a retired group; `ui_fx.py` is
  untouched and the rest of the page is as it was; row 533.)
- Every golden unmoved: no preset, graph or shader changes.

## Decisions (the owner's, 2026-10-27)

| # | question | recommendation | the owner |
|---|---|---|---|
| D1 | The word. `patch.py` is the modulation graph's order (map item 7). Call the new thing **patch** and rename the module, or call the new thing something else (**block**, **rack**, **module**, **macro-node**)? | **Patch**, the owner's word and the modular word for exactly this. Rename `patch.py` → `modgraph.py` (`patchmod` → `modgraph`, `build_patch` → `build_modgraph`, `patch_notes` → `modgraph_notes`) as the mechanical T0: three files, no behaviour. "k patched" on a node summary stays, it is the same sense. | "Calling this a patch and renaming the other module is fine." |
| D2 | Where a spawn's host ports land: open pins only; open pins, plus **splice** when dropped on a matching cable, plus a one-press **wire as saved** chip (P3); or attach by the saved names automatically when the host has them? | **Open pins + splice + the chip.** Automatic attachment is a hidden edge by another name and the hard rule forbids it; splice is the same gesture as insert, and the chip is one press with its result drawn. | as recommended |
| D3 | A spawn's rig port collides with the host (K1 already on `view.bright`; `hand:right.y` already owns a param): the **patch wins** and the displaced row is said; the **host wins** and the patch's row lands dormant and said; or **ask** per conflict? | (the patch wins, said) | **Ask, in one sheet**: "a pop-up that says, hey, these are the conflicts; choose a resolution for each one: the patch or the existing preset." Built as P3's conflict sheet. |
| D4 | The group node: saved in the preset (`groups`) and drawn collapsed with its internal cables folded away — confirm against the hard rule — or a session-only fold saved nowhere, like collapsed nodes? | **Saved, collapsed by default**, and the rule holds in spirit: nothing is added, nothing is laid out, and `+` shows exactly what is inside. | **Saved, folded until `+`**: "a good middle ground. I know it goes against the no hidden edges rule, but this is an explicit place where we want to say, okay, we want to encapsulate complexity." The one sanctioned exception to the rule, recorded as such. |
| D5 | What a patch may hold beyond its nodes: **only the boundary** (a host param is reached by a port, never carried as a value), or also **values of host params** (`view.bright: 0.8` as part of the patch)? | **Only the boundary.** A patch that sets the shape's brightness is a preset; a patch that *drives* it is a patch. | as recommended |
| D6 | The fx module presets: converted to factory patches and the mechanism retired, or left beside patches? | (converted and retired) | **No conversion; retired outright.** "I don't want factory patches from the 6 FX module presets … The FX module should probably be retired outright. It is not a useful representation of shaders anymore." P5. |
| D7 | The schema: `groups` is a new key — `/8`, taken with the rule that both Macs update together (row 394)? 37B also claims `/8`. | **Whichever of 37B and this lands second takes `/9`**; the migration is "the key is absent → no groups", nothing else. | as recommended |
| D8 | The desk: the browser and spawn stay on the control window, or a bank of patches on APC40 pads too? | **Control window only.** The desk and the faders are Dylan's; a pad that spawns at a party is a pad that spawns twice. | control window only |
| D9 | The conflict sheet's default: every row preselected to the patch, to the existing preset, or unselected so each needs a click? | **Preselected to the patch**, with one **keep all existing** button. | as recommended |
| D10 | "The UI that is present in that FX module … needs to go away": does the FX **page** (`ui_fx.page`, the browser of effects by where each ends) go with the module presets? | (the page goes, the strip stays) | **No — the page stays.** "I meant only the module presets. I forgot that we did a UI pass on the FX tab a while ago." |

## Order of work

| task | what | proves |
|---|---|---|
| T0 | D1's rename, `patch.py` → `modgraph.py` | the suite unmoved |
| T1 | P1: `patches.py` (`read`, `check`, `lift`, `spawn`), the `DocKind`, `<library>/patches/`, the rename rules, the boundary classifier | the round trip over every factory preset's effect run; a patch with a macro and no free macro is refused in words; a lift that names `scene` refuses it and keeps the rest |
| T2 | P2: `groups` in the preset (D7's schema), the group node collapsed / open / ungroup / group-from-selection, the tinted region, undo marks | a grouped preset's `build_graph` signature equals its ungrouped twin's; goldens unmoved; a preset without `groups` saves byte for byte |
| T3 | P3: save as patch / update patch, the browser (GRAPH chip, PRESETS fold, Spawn ▸), spawn through the doors as one step, the **conflict sheet** (D3, D9), splice on a cable, **wire as saved** | spawning `acid-wash` into `party-trip` lands `acid.2`, `wobble.2`, `delay.2`, `mod.<n>`, K1's row and the hand's row; ⌘Z removes all of it; spliced on `scene → warp.image` the run reads `scene → acid.2 → wobble.2 → delay.2 → warp`; a spawn whose K1 collides opens the sheet, and "keep all existing" then Spawn lands the patch's K1 row dormant and said |
| T4 | P4: `devices.wants`, the chips, the SYSTEM lines, the registry's status-change event and the arrival line | a preset wanting `leap` on a rig without one reports "not in this rig: 3 rows"; a `MidiDevice` going lost → connected fires the listeners once and says the count |
| T5 | P5: the fx module presets retired (the six files, the fx entry of the fold, the hook, `module_runs`); the FX page untouched (D6, D10) | goldens unmoved; every factory preset loads with no note; the FX page draws as before; no test or page imports what went |
| T6 | docs: this spec's "as built", ARCHITECTURE §3 (a "Patches" subsection beside the desk templates), DECISIONS "Presets and the desk", register rows, hand checks group AK (corrected in the build: AJ is plan 39's), `plans/README.md` | — |

T0 first; T1 alone; T2 needs T1's reader; T3 needs T1 and T2; T4 is
independent of T2 and T3 and can land first as its own PR if the owner
wants the "waits for apc40" line sooner; T5 is independent of all. The
side ask (the resizable side pane) is merged: PR #266, `main` @ f984d3b.

(Corrected in the build: T3's proofs name what `party-trip` does not
hold. It has no `acid`, `wobble`, `delay` or `warp`, so a first spawn of
`acid-wash` keeps the bare ids by the instance rule and the second takes
`acid.2`, `wobble.2`, `delay.2`, `mod.2`; the splice is proved on `scene →
plasma.image` (the run then reads `scene → acid → wobble → delay →
plasma`); "the hand's row" reaches the patch through `mod.1`'s input, which
is no route. The tests assert the rules as they are; ruling 19 in the run
records.)

## What it does not do

- It does not change evaluation. The renderer, `build_graph`, the
  signature fixture and every golden see the flat graph; a group is a
  list.
- It does not nest: a group holds nodes, not groups (a patch spawned into
  an open group joins the canvas beside it). Nesting is a follow-up if the
  owner wants racks of racks.
- It does not carry media: a channel is this Mac's files; a patch reads a
  channel through a port.
- It does not touch `bindings.json`: a patch's rig ports are preset-layer
  desk rows and performer routes, the loaded preset's, as a Learn's are. A
  session row (a pad button, a sink) is never in a patch.
- It does not put anything on the desk (D8).

## Independence from plans 37A, 37B, 38, 39

| | this plan touches | they touch |
|---|---|---|
| `graphview.py`, `ui_graph.py` | the group node, the region, the menu, the browser chip, `SCHEME_ROLE` read from `devices` | 37A: `_node`, `_cable`, colours, `height`, `summary`; 38: the head's hold chip and the backdrop |
| `preset.py` | the `groups` key, `Presets.document` / `load_doc` one step each, `signature` | 37B: the pattern by name (`/8`) |
| `devices.py` | `wants`, the status-change event in `poll`, `SCHEME_ROLE` | 39: the segment and camera devices, if any |
| `library.py` | the `patches` `DocKind`, `save_patch`, the fx fold | — |
| `ui_fx.py`, `ui.py`, `ui_presets.py`, `ui_routing.py` | `ui_fx.py` nothing; the fx entry leaves the PRESETS fold; `ui_routing.modal` gains the conflict sheet | 37A: nothing; 38: the head |
| `render.py`, `graph.py` | nothing (a reader of `FRAME_KINDS`, `instance_name`, `GraphSpec.to_json`) | 37A: `Thumbs`, `frame.made`; 37B: `Shape`, `PatternNode` |
| schema | `/8` or `/9` (D7) | 37B `/8` |

The seams: the schema number (D7) and the thumbnail on a collapsed group
(37A's `Thumbs.want` is asked for the group's last outlet; whoever merges
second adds one name to the wanted list).

## Size

`patches.py` ~500 lines, most of it the two pure functions and the
classifier; `graphview.py` + `ui_graph.py` ~900 (the group node, the
region, the menus, the browser); `preset.py` ~120; `devices.py` ~150;
`library.py` ~100; `ui.py` / `ui_presets.py` ~120. Tests: a new
`tests/test_patches.py` (the round trip, the renames, the refusals, the
spawn through the doors on a headless rig as `test_ui_shell.build_rig`
does it), `test_graph_groups.py` (the canvas), `test_device_wants.py`;
six goldens. About plan 36's size.

## Hand checks (written into `11-hand-checks.md` by T6 as group AK, 394–401)

1. **Group and ungroup.** Load `party-noita`, open GRAPH, select
   `warp`, `doublevision` and `fractals` and Group. One node with a
   picture in, a picture out and the knobs that have cables. `+` opens it
   in place; nothing on the projector changed. Ungroup; nothing changed.
2. **Save and spawn.** Save it as "noita core". Load **new**, Spawn ▸
   noita core at the right of the scene: three nodes in a tinted region
   with two open pins. Drag `scene` to its in and its out to `output.all`.
   The picture is noita's middle. ⌘Z twice, then ⌘Z once more: the group
   is gone with everything it brought. (Corrected in the build: a spawn
   lands **folded** — one group node with its two open pins, "in · open
   (was scene)" and "out · open (was tripcolour.image)"; `+` shows the
   three nodes in the tinted region. A drag onto an open pin lands on the
   member's port.)
3. **Splice.** Load `party-trip`, drag "noita core" from the browser onto
   the cable `scene → trip.image`: the run reads scene → the three →
   trip, said on the nodes, seen on the projector. (Corrected in the
   build: `party-trip` has no `trip` node; its run is `scene → plasma →
   kaleido → zoomblur → huecycle → All outputs`, so the cable is `scene →
   plasma.image` and the run reads scene → the three → plasma.)
4. **The knobs come with it, and the sheet asks.** Save a patch from a
   group whose effect has K1 and the right hand on it. Spawn it into
   `party-acid`, where K1 is something else: the sheet lists "K1:
   view.bright (the preset) · fx.acid.2.speed (the patch)" preselected to
   the patch; Spawn, and K1 turns the patch's knob and the ring agrees;
   ⌘Z gives K1 back. Spawn again, press **keep all existing**, Spawn: K1
   still turns brightness and the group node says "K1 kept by the
   preset". Cancel on a third spawn lands nothing.
5. **Not connected, said.** With the APC40 unplugged, load a preset with
   that patch: the group node reads "waits for apc40 (lost): K1"; the
   GRAPH head shows **1 device missing**; SYSTEM lists it. Plug the desk
   in: the footer says "apc40 connected — 1 control live", the ring
   lights, K1 turns the knob. Nothing was pressed. (Corrected in the
   build: the count is every control the loaded preset wants of the desk,
   not the patch's alone — "apc40 connected — n controls live", n being
   every desk control the preset maps, about 26 on a factory party
   preset.)
6. **Not in this rig, said.** On the laptop config (no Leap), the same
   preset: "leap (not in this rig): right hand y"; the grey placeholder
   node as before.
7. **The fx modules are gone, the FX page is not.** "more · module
   presets" on PRESETS lists no fx entry; the FX tab draws as before;
   every factory preset loads with no note in the footer.
8. **Twice.** Spawn "noita core" twice into one preset: two groups,
   `.2` and `.3` ids on their hovers, the second's K1 row said as dormant.
   (Corrected in the build: `.2` and `.3` only in a host that already
   holds `warp`, `doublevision` and `fractals` — `party-noita`; elsewhere
   the first copy keeps the bare names and the second takes `.2`, by the
   instance rule. "noita core" carries no K1: its desk rows are D2, D3 and
   D5–D8 and its hand axes, so the second spawn's sheet lists those
   against the first copy's, and with **keep all existing** the second
   group says "n rows kept by the preset".)

## Follow-ups (not in this plan)

- Nested groups.
- A patch's **exposed knobs**: the group node offering a member param as
  a pin by the owner's choice, not only where a cable already crosses.
- Patches in a show's bank (slots that spawn, not load) — only if D8
  turns.
- A patch that carries a media channel's *source list* (not the files).

## What changed in the build

The plan above is the design; this is where the build differs from it, or
chose within it. Every ruling was made by the controller on 2026-10-27 or
2026-10-28 and has a row in
[`DECISION-REGISTER.md`](../DECISION-REGISTER.md): 501–510 are D1–D10 as
built (the owner's), 511–536 the build's rulings, each the owner's to keep
or overturn. Two are open and marked **pending the owner**: row 521 (the
schema of an ungrouped save) and row 524 (a take-over chip for "wire as
saved"). Built on `plan-40-build` in six code tasks and one fix pass, each
in its own worktree, each reviewed before it merged: T0 the word (PR #269),
T1 the patch as data (#274), T4 the wants and the arrival (#272), T5 the fx
module presets retired (#271), T2 the group node (#276), T3 save, browse
and spawn (#277), then the plan-level review's fixes (#278). This page is
T6. The run's ledger, briefs, rulings, reports and reviews are in
[`assets/40-run/`](assets/40-run/).

**Tests.** At e0675a6 (everything merged): the fast tier `uv run pytest -q`
**4320 passed, 2 skipped** (4122 at the base, f10f281); the full suite
`uv run pytest -q --all` **4551 passed, 2 skipped**; the goldens
`uv run pytest -q --all -m golden` **144 passed** — the 136 before, none
moved or re-recorded, and 8 new proofs that a grouped twin of each manifest
preset with a main run draws that preset's recorded goldens;
`tests/fixtures/frame-signatures.json` unchanged. New test files:
`tests/test_patches.py` (the file, `check`, `read`, `lift`, `spawn`, the
round trip, the library kind), `tests/test_graph_groups.py` (the preset's
`groups`, the group node, the drags, spawn, splice, wire as saved, save as
patch, the browser), `tests/test_device_wants.py` (`wants`, the chips, the
arrival). Added to: `test_ui_routing.py` (the conflict sheet),
`test_ui_presets.py` (the patches fold), `test_presets.py` (the fx label,
the retired group), `test_golden_frames.py` (the 8 proofs), `test_hold.py`
(plan 38's inset). Two fixtures, force-added because `tests/fixtures/` is
ignored: `tests/fixtures/patches/acid-wash.json` (the P1 example) and
`tests/fixtures/groups/party-noita-grouped.json`. ruff is clean on every
file the plan touched (the base's 25 pre-existing errors are in `media/`,
`tools/ingest.py`, plan 39's bench scripts and four tests).

**Hand checks** 394–401, group AK in
[`11-hand-checks.md`](11-hand-checks.md): the eight above in order (AK.1 is
394 … AK.8 is 401), with the tasks' own additions folded into the nearest
one. None has been run by a person.

**Both Macs.** A preset with a group is `hyperspace.preset/8`. An older
build refuses an `/8` file outright ("is not a hyperspace.preset", the
ladder's rule since row 394), so both Macs run this build before such a
preset is shared. (Corrected in the build: the session prompt said an
older build "drops the key on its save"; it never reads the file.)

**As built, by task.**

- **T0, the word (D1).** `hyperspace/patch.py` is `modgraph.py`, and the
  rename is wider than the build plan's four symbols: `Patch`, `PatchNode`,
  `PatchEdge` are `ModGraph`, `ModNode`, `ModEdge`, `Router.patch_cut` is
  `modgraph_cut`, and the private names followed, so "patch" means the
  owner's thing and nothing else (row 511). The live docs got the symbol
  sed; the run records of plans 28–30 keep the old names as history.
- **T1, the patch as data (P1, D5).** `hyperspace/patches.py` (`check`,
  `read` → `Patch`, `lift` → `(doc, refused)`, `Host`, `spawn` → `Landing`,
  `Conflict`), the `patches` document kind in `library.py` (`read_patch`,
  `save_patch`; `hide` and `rename` widened to it, a hidden factory patch
  under `hidden.json`'s `"patches"` key, row 516). Departures, each a row:
  the example's lane is `mod:1` (corrected above); a patch's envelopes are
  `env.6` and up in the file (row 512); `lift` returns `(doc, refused)`
  over the registry's snapshot (row 515); the round trip runs over each
  factory preset's main run into All outputs (`graph.run_back`), because a
  `/7` frame has no `frame → fx.image` run — 9 presets have one, the 16
  that do not are named. A macro is "in use" by a label, a subscriber or a
  row, never by its value (row 513). The conflict kinds: a desk control by
  `Binding.overlaps`, a `hand:` or `axis:` source that already drives
  another param, a route onto a param another performer owns (row 514).
  After review, `check` refuses any wire with an end outside the patch and
  `spawn` lands only the patch's own wires (D2), and a voice that does not
  spawn (a full bank) leaves its lane reading nothing.
- **T4, the wants and the arrival (P4).** `devices.wants` / `Want` /
  `wants_for` / `want_words` / `want_lines` / `missing_chip` /
  `wanted_lines` / `arrival`, `SCHEME_ROLE` moved into `devices`,
  `routing.row_words` (the words of a row, which `graphview.cable_words`
  now calls), and the registry's status-change event with its `said` hook
  (app.py's two lines). The role of an unqualified row outside MIDI is the
  scheme's primary, then the first listed publisher (an off one counts),
  then `SCHEME_ROLE`'s name (row 531). An error on an open device is no
  coming or going, and the launch says nothing (row 530). After review
  `wants` reads each device's `status` directly (0.06 ms, no MIDI port
  layouts built) and `ui_graph.panel_wants` asks it once a frame for the
  head, the PRESET strip and SYSTEM.
- **T5, the fx module presets retired (P5, D6, D10).** The six
  `library/fx/*.json`, `Presets._fx_module`, `_watch_fx_modules` and
  `graphmigrate.module_runs` with its helpers are gone;
  `library.RETIRED_MODULES = ("fx",)` names the retired group (row 534);
  the FX page's module strip is hidden through `ui_presets.strip` (row 533,
  P5 corrected above); an `fx` label in an old file loads quietly and the
  next save drops it; the party generator keeps the three families' values
  inline (`preset.ACID_FX`, `MANDALA_FX`, `NOITA_FX`), so the factory files
  are byte-identical (row 535); `tools/fx_shots.py` no longer shoots
  presets.
- **T2, the group node (P2, D4, D7).** `preset.GROUPS_KEY` after `layout`,
  read at load step 6½ (a member the preset lacks, one a group may not hold
  or one already in a group is left out with a note), in the undo marks and
  the signature; `/8` is written **only when a group exists** (row 521,
  pending the owner); `graphview.VGroup` and the `Edit` verbs `group`,
  `ungroup`, `rename_group`, `set_open`, `move_group`, `leave_groups`, each
  one undo step; one boundary classifier in `patches` (`select`,
  `crossing`, `side`) shared by `lift`, Group and the drawn pins. The
  folded node draws its pins, rows, status line and plan 37's thumbnail of
  its last picture outlet; the open region is a tinted rectangle with an
  editor node over its title band, so the title can be dragged and the
  members follow live. Departures: the folded node has out pins for member
  lanes and rows for modifier inputs read from outside (row 522); dragging
  the folded node moves every member (row 520); open / fold is a preset
  edit (row 518); a deleted member leaves the list lazily (row 519);
  grouping a member of another group moves it, said (row 517).
- **T3, save, browse, spawn (P3, D2, D3, D9).** `Edit.spawn` lands a
  `Landing` in `load_doc`'s order through the doors (`gs.land` of the
  re-read section, `bank.add`, `add_modifier`, `lib.restore`,
  `Bindings.add` / `replace_owner`, `bind(write=False)`, `set_macros`, the
  group and its layout) behind one `_step`; `Edit.splice`,
  `Edit.wire_as_saved`, `Edit.save_patch`; the conflict sheet in
  `ui_routing.modal` ahead of Replace / Keep, every row preselected to the
  patch; `Learn.hold`, so nothing learns while the sheet is up (row 527);
  the **patches** chip and **spawn ▸**; the drag from the browser onto a
  picture cable (row 529); the PRESETS fold. Departures: "wire as saved"
  is a re-read of the section (`render_add` adds nodes, not cables) and
  takes only free ports (row 524); open pins and the rename map last the
  session (row 523); a kept row is stored with its words ("K1", row 526);
  save as patch refuses a member a patch may not hold and any existing
  patch's name (row 525).
- **The review fixes (#278).** The plan-level review found one Important:
  a spawn with no conflicts never said which devices its rows wait for —
  now the head says "…; waits for leap (not in this rig): right hand y",
  less any row the sheet kept (row 528). And the minors: a landing refused
  after its dry run leaves no undo step; a source conflict asks the
  referee (`Bindings.refusal`, a read-only factoring of `_check` in
  `routing.py`) before the host's rows go; save as patch never replaces
  another patch; the patch list is read once per library poll;
  `Presets.banks()` public; several members dragged out are one step; a
  drop on a folded group's stub is refused in words; one group-number rule
  (`graphmigrate.group_number`); an open region's title is left out of
  Group's selection; the 16 presets with no main run get a grouped-twin
  proof too (none has an effect, so each is grouped with every node a group
  may hold: `party-tracer` and `party-wake` prove it, the other 14 hold only
  the frame's nodes).
- **Plan 38's inset (row 536).** `ui_graph._monitor` passed `add_rect(…,
  0.0, 0, 2.0)`, which imgui_bundle's signature (`rounding, thickness,
  flags`) refuses with a TypeError: the PROJECTOR inset never drew on
  `main`. One line, its own commit (86795d5), with a stub-texture test, rides
  on this plan's PR.

**`patches.py` is a leaf over the pure pieces.** It imports `graph`'s
names, `routing`'s `Binding` and scheme split, `modifiers`, `modbank`,
`lfo` and `envelope` — no app module directly (an AST test holds it). Through
`routing` it reaches `apc40` and `params`, and through `graph` `moderngl`,
as `graphmigrate` does: its docstring's "nothing of the app" means no
direct import, not an empty import closure.

**Process** (rulings 1–3, 7, 8, 12, 14, 16, 21, in the run records, not
rows). The base was `plan-37-38-39-integration` @ 2b185ea plus the plan 40
docs merge (f10f281), which also carried `main` @ f984d3b — the build plan
said that commit was already under the base; it was not (corrected in the
build plan). T2 and T3 waited for PR #270 (plans 37–39) to reach `main`,
which was merged into the build branch once (d08a363, one conflict in
`ui_graph.py`'s head chips, both sides kept). Register rows are 501–536,
not the prompt's 471–495, which plans 37–39 and PR #275 had taken. T3's
own review was folded into the plan-level review. The sub-agents ran on
Opus; their commits carry its trailer.

**Not verified by any person.** Every drawing: the folded node, its pins,
rows, status line and thumbnail; the tinted region and its title's live
follow; the side pane's name input, chips and save form; the conflict
sheet at its width; the drag from the browser's popup onto a cable and
the cable's highlight; the open pins; the PRESETS fold; the
"N devices missing" chip on a narrow PRESET strip; the footer when a real
APC40 comes back; the FX page without its module strip; the PROJECTOR
inset on screen. No mouse drag on GRAPH has been driven by a test: the
drags call the same functions the tests call.

**Known rough edges.**
- With the APC40 unplugged, every factory preset with desk rows lights
  **1 device missing** ("apc40 (lost): 26 controls"): correct, and
  constant on the laptop.
- A spawned group's open pins and its **wire as saved** chip are gone
  after a reload (row 523); in any host whose run feeds All outputs, the
  chip refuses the outlet, "output.all.image is taken" (row 524).
- A patch read through a modifier input on a hand axis is no conflict,
  even where the host's own row on that axis drives a param — the spec's
  D3 example names that very case (row 514, for the owner). Spawning a
  cut back into its own preset lists every shared hand axis: correct by
  the one-axis rule, a noisy sheet.
- A spawn that raises the sheet says its wants twice: in the sheet, then
  on the head. Nothing is said when a spawn is cancelled.
- A × hidden factory patch still blocks its name for **save as patch…**
  (no factory patch ships yet).
- `party-acid` and `party-mandala`'s notes still say "the `acid` /
  `mandala` fx module preset" (preset data, unchanged by this plan).
- User fx module files on the Drive library stay on disk, unreachable
  from the UI; nothing deletes them.
- The head's "N hidden" count includes a folded group's members; ids are
  reused after the highest group is ungrouped (row 517).
- The status line of a group asks `devices.wants` once a frame per group.
