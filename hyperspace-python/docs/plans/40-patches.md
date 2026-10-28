# Plan 40 — patches: a group of nodes and its boundary, saved once, spawned anywhere

**Status: spec (2026-10-27), awaiting the owner's decisions D1–D8.** From
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
the seams. Build plan to follow the decisions, as 37A's did.

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
 "routes": [{"source": "mod:0", "target": "fx.wobble.amount", "op": "push", "value": 0.3},
            {"source": "lane:0", "target": "fx.acid.speed", "op": "push", "value": 0.1, "scale": "master.gain"}],
 "desk":   [{"source": "cc:0:48", "target": "fx.acid.speed", "op": "abs", "feedback": "ring"}],
 "macros": {}, "lfos": [], "envs": [],
 "ports":  [{"id": "in",  "type": "image", "to": "acid.image",   "was": "scene"},
            {"id": "out", "type": "image", "from": "delay",      "was": "output.all.image"}],
 "layout": {"render:acid": [0, 0], "render:wobble": [260, 0], "render:delay": [520, 0], "mod.1": [0, 200]}}
```

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
  **save as patch**.
- **`patches.spawn(doc, host_spec, host_table, host_banks, at) → Landing`**:
  a `Landing` is the rename map (`acid` → `acid.2` by `_new_instance`'s
  rule, `mod.1` → `mod.<next>`, `lfo.1` → `lfo.<next>` by the bank's
  high-water rule, `macro.N` → a free macro or a refusal), the rewritten
  nodes, wires, values, modifiers, routes, desk rows, subscribers, the
  layout moved to `at`, the group (P2) and the notes. **Pure**: it writes
  nothing. The app lands it through today's doors (P3).
- **Round trip**: `lift(spawn(p))` is `p` again up to ids and position, a
  property test over every factory patch and over a patch cut from each
  factory preset's effect run.

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
  confirm it against the hard rule.**
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
  right-click menu gains **Spawn ▸** with the list.
- **Spawn** lands `patches.spawn`'s `Landing` as **one undo step**
  through today's doors, in load order: the group's render nodes and
  internal wires by `gs.land` of the re-read section (so their params
  exist), the voices by `bank.add(n)`, the modifiers by `add_modifier`,
  the values by `lib.restore`, the routes by `Bindings.add` (a performer
  conflict handled by D3), the desk rows by `bind(write=False)` (a knob
  conflict handled by D3), the subscribers by `set_macros`, the group and
  its layout at the drop point. The preset's dirty dot lights; no file is
  written until a save.
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
  ports collide (one knob, one param) and D3 says who wins; the second's
  losing rows land dormant-by-conflict and are said.

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
  nothing is a surprise.

### P5 — the fx module presets become factory patches (D6)

`library/fx/acid.json`, `mandala`, `noita-tripping`,
`noita-heavily-tripping`, `noita-tripping-balls`, `trip` are rewritten as
factory patches (their effect runs as nodes and wires, one `image` inlet
and outlet, their values), the fx fold of "more · module presets" is the
patches list, `Presets._fx_module` and `graphmigrate.module_runs` go, a
show or preset that still names an fx module in `modules` keeps the label
and nothing loads (D3 of the desk already says a label never chain-loads).
`band/` (the analyzer's scenes, session) and `dream/` stay as they are.
Every golden unmoved: no preset changes.

## Decisions for the owner

| # | question | recommendation |
|---|---|---|
| D1 | The word. `patch.py` is the modulation graph's order (map item 7). Call the new thing **patch** and rename the module, or call the new thing something else (**block**, **rack**, **module**, **macro-node**)? | **Patch**, the owner's word and the modular word for exactly this. Rename `patch.py` → `modgraph.py` (`patchmod` → `modgraph`, `build_patch` → `build_modgraph`, `patch_notes` → `modgraph_notes`) as the mechanical T0: three files, no behaviour. "k patched" on a node summary stays, it is the same sense. |
| D2 | Where a spawn's host ports land: open pins only; open pins, plus **splice** when dropped on a matching cable, plus a one-press **wire as saved** chip (P3); or attach by the saved names automatically when the host has them? | **Open pins + splice + the chip.** Automatic attachment is a hidden edge by another name and the hard rule forbids it; splice is the same gesture as insert, and the chip is one press with its result drawn. |
| D3 | A spawn's rig port collides with the host (K1 already on `view.bright`; `hand:right.y` already owns a param): the **patch wins** and the displaced row is said; the **host wins** and the patch's row lands dormant and said; or **ask** per conflict (the Replace / Keep prompt, once per row)? | **The patch wins, said, one undo step.** You asked for the patch and its knob is part of it; ⌘Z puts the host's row back. The browser's sheet lists the conflicts before the press, so it is not a surprise. Asking per row makes a six-knob patch six prompts. |
| D4 | The group node: saved in the preset (`groups`) and drawn collapsed with its internal cables folded away — confirm against the hard rule — or a session-only fold saved nowhere, like collapsed nodes? | **Saved, collapsed by default**, and the rule holds in spirit: nothing is added, nothing is laid out, and `+` shows exactly what is inside. The owner asked for the node; a fold the preset forgets is not a node. |
| D5 | What a patch may hold beyond its nodes: **only the boundary** (a host param is reached by a port, never carried as a value), or also **values of host params** (`view.bright: 0.8` as part of the patch)? | **Only the boundary.** A patch that sets the shape's brightness is a preset; a patch that *drives* it is a patch. Keeps lift ⇄ spawn a clean round trip and two patches from fighting over a singleton. |
| D6 | The fx module presets: converted to factory patches and the mechanism retired (P5), or left beside patches? | **Converted and retired.** The owner's "didn't really work" is the mandate; six files, one fold, two functions. `band/` and `dream/` stay: they are session scenes and one-group moods, not compositions. |
| D7 | The schema: `groups` is a new key — `/8`, taken with the rule that both Macs update together (row 394)? 37B also claims `/8`. | **Whichever of 37B and this lands second takes `/9`**; the migration is "the key is absent → no groups", nothing else. |
| D8 | The desk: the browser and spawn stay on the control window, or a bank of patches on APC40 pads too? | **Control window only.** The desk and the faders are Dylan's; a pad that spawns at a party is a pad that spawns twice. |

## Order of work

| task | what | proves |
|---|---|---|
| T0 | D1's rename, `patch.py` → `modgraph.py` | the suite unmoved |
| T1 | P1: `patches.py` (`read`, `check`, `lift`, `spawn`), the `DocKind`, `<library>/patches/`, the rename rules, the boundary classifier | the round trip over every factory preset's effect run; a patch with a macro and no free macro is refused in words; a lift that names `scene` refuses it and keeps the rest |
| T2 | P2: `groups` in the preset (D7's schema), the group node collapsed / open / ungroup / group-from-selection, the tinted region, undo marks | a grouped preset's `build_graph` signature equals its ungrouped twin's; goldens unmoved; a preset without `groups` saves byte for byte |
| T3 | P3: save as patch / update patch, the browser (GRAPH chip, PRESETS fold, Spawn ▸), spawn through the doors as one step, splice on a cable, **wire as saved** | spawning `acid-wash` into `party-trip` lands `acid.2`, `wobble.2`, `delay.2`, `mod.<n>`, K1's row and the hand's row; ⌘Z removes all of it; spliced on `scene → warp.image` the run reads `scene → acid.2 → wobble.2 → delay.2 → warp` |
| T4 | P4: `devices.wants`, the chips, the SYSTEM lines, the registry's status-change event and the arrival line | a preset wanting `leap` on a rig without one reports "not in this rig: 3 rows"; a `MidiDevice` going lost → connected fires the listeners once and says the count |
| T5 | P5: the six fx modules as factory patches, the fold, the hook retired | each converted patch spawned into **new** draws what the module loaded onto **new** drew (a golden per patch, six new) |
| T6 | docs: this spec's "as built", ARCHITECTURE §3 (a "Patches" subsection beside the desk templates), DECISIONS "Presets and the desk", register rows, hand checks group AJ, `plans/README.md` | — |

T0 first; T1 alone; T2 needs T1's reader; T3 needs T1 and T2; T4 is
independent of T2 and T3 and can land first as its own PR if the owner
wants the "waits for apc40" line sooner; T5 needs T3.

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

## Hand checks (written into `11-hand-checks.md` by T6, group AJ, numbered after the last group in the file when this lands)

1. **Group and ungroup.** Load `party-noita`, open GRAPH, select
   `warp`, `doublevision` and `fractals` and Group. One node with a
   picture in, a picture out and the knobs that have cables. `+` opens it
   in place; nothing on the projector changed. Ungroup; nothing changed.
2. **Save and spawn.** Save it as "noita core". Load **new**, Spawn ▸
   noita core at the right of the scene: three nodes in a tinted region
   with two open pins. Drag `scene` to its in and its out to `output.all`.
   The picture is noita's middle. ⌘Z twice, then ⌘Z once more: the group
   is gone with everything it brought.
3. **Splice.** Load `party-trip`, drag "noita core" from the browser onto
   the cable `scene → trip.image`: the run reads scene → the three →
   trip, said on the nodes, seen on the projector.
4. **The knobs come with it.** Save a patch from a group whose effect has
   K1 and the right hand on it. Spawn it into `party-acid`, where K1 is
   something else: the sheet says "K1 is on view.bright — the patch takes
   it"; after the spawn K1 turns the patch's knob and the ring agrees;
   ⌘Z gives K1 back.
5. **Not connected, said.** With the APC40 unplugged, load a preset with
   that patch: the group node reads "waits for apc40 (lost): K1"; the
   GRAPH head shows **1 device missing**; SYSTEM lists it. Plug the desk
   in: the footer says "apc40 connected — 1 control live", the ring
   lights, K1 turns the knob. Nothing was pressed.
6. **Not in this rig, said.** On the laptop config (no Leap), the same
   preset: "leap (not in this rig): right hand y"; the grey placeholder
   node as before.
7. **The factory patches.** On **new**, spawn each of the six converted
   patches wired scene → in, out → output.all, and compare by eye with
   the fx module of the same name loaded on `main`'s build.
8. **Twice.** Spawn "noita core" twice into one preset: two groups,
   `.2` and `.3` ids on their hovers, the second's K1 row said as dormant.

## Follow-ups (not in this plan)

- Nested groups.
- A patch's **exposed knobs**: the group node offering a member param as
  a pin by the owner's choice, not only where a cable already crosses.
- Patches in a show's bank (slots that spawn, not load) — only if D8
  turns.
- A patch that carries a media channel's *source list* (not the files).
