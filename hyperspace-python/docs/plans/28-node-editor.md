# Plan 28 — the node editor: the modulation as a graph, both graphs on one canvas

The modulation is now **a graph evaluated in dependency order**, so the
one-frame lag is gone: an LFO owning another LFO's depth, a macro
scaling a push, a `scale` that is itself modulated all land **this
frame**, and every factory preset lands the same values as before, a
frame earlier where it was late. A loop runs only through a `delay`
modifier; any other loop keeps its last cable off, with a note.
**Modifiers** — `curve`, `scale`, `smooth`, `combine`, `threshold`,
`delay` — live in the preset beside its routes, each publishing a lane
`mod:<n>` a route can source; ROUTING had a MODIFIERS strip (GRAPH since N7). A new page,
**GRAPH**, draws both graphs on one `imgui_node_editor` canvas — the
devices, the analyzer, the LFOs, the modifiers, the macros, the params
under the render node that owns them, the render graph's own image
cables, the outputs — and edits them: a cable dragged into a param's
`mod` stub is the route a Learn would make, a modifier dropped on a
cable is inserted into it, Learn starts from a port, and an image cable
dragged between two ports is a **wire** in the preset's `graph` section,
whose outputs are now nodes a preset may wire. The APC40 is drawn as two
nodes, *apc40* and *apc40 (SHIFT)*, a preset's desk template as one
collapsible node, a device this rig lacks as a grey placeholder named by
role. After the owner's first look, **N7** made it legible: every node
starts collapsed (a title and a few lines), two nodes are one wire
however many params are mapped between them, and the routes and the
modifiers are edited on GRAPH (ROUTING points there). **Every one of the 580 goldens recorded before stream N's render
work matched unchanged**; N4 added 16 for its two fixtures (596).

Built as stream N of the run in
[`28-30-orchestrator-prompt.md`](28-30-orchestrator-prompt.md), from the
design agreed with the owner on 2026-10-16 (the wishlist's "Node based
editor" and "Controllers as nodes", [`24-party-wishlist.md`](24-party-wishlist.md)).
No preset was edited or added (decision 4): every file under
`hyperspace/library/` is byte-identical, `apc40.py` and `midi.py` are
untouched (the desk is Dylan's), and every proof is a fixture under
`tests/fixtures/` loaded through a scratch library.

Hand checks: [`11-hand-checks.md`](11-hand-checks.md) group Y, checks
232–266 (N7's 261–266). Open decisions: [`DECISION-REGISTER.md`](../DECISION-REGISTER.md)
rows 233–290 (N7's 278–290). The owner's decisions for this plan (6–16 of the launch
prompt) are in [`DECISIONS.md`](../DECISIONS.md) with Who "owner".

Branch `plan-28-30-integration`, in merge order: N1 (PR #209), N0
(#210), N2 (#215), N3 (#217), N4 (#219), N5 (#220), the review pass's
fixes (#221), N6 (this file), N7 (a legible graph, 2026-10-20). Stream D (plan 30,
[`30-shader-nodes.md`](30-shader-nodes.md)) merged on the same branch in
between; the GRAPH page draws its effect nodes and placed effects as
any render node, and N4's wires extend its placements. The suite went
from 2238 tests (the base, 5d18192) to 2368 at N5's merge (327e646) and
2373 with the review pass's fixes (PR #221), 2 skipped. The review
pass's fixes also made the GRAPH head's words follow the last edit (a
render edit's words go at the next value edit; a delete of several
things keeps its first refusal's words).

## What the owner wants (2026-10-12, scope 2026-10-16)

One patch-cable editor for both the modulation and the visual pipeline:

| Stage | What it adds |
| --- | --- |
| N1 — modifier nodes | Routes become chains: source → modifiers → param. Curve, scale/offset, smooth, combine two sources (+, ×, min, max), threshold-to-trigger |
| N2 — read-only graph view | A page that draws what is wired to what: devices, routes, modifiers, params, render nodes |
| N3 — edit the modulation | Drag cables between sources, modifiers and params; Learn still works and lands as a cable |
| N4 — edit the render graph | The same editor on the render graph: geometry, hands, materials, effect placement, palette, outputs |

With it: each controller a node, each degree of freedom a port; roles,
not serials; two input ports per param (`base` many, `mod` one under the
referee); values and triggers two signal kinds; the APC40 as two nodes;
evaluation in dependency order removing the one-frame lag; loops only
through a one-frame delay; both graphs in the preset as plain JSON;
today's routes converting one-to-one. Rejected: GLSL in the graph, a
general TouchDesigner.

## What was built

### N0 — the modulation graph in dependency order

- **At the machine.** Nothing looks different. A param downstream of
  something the old pass read stale — party-trip's camera zoom under LFO
  1 (whose depth the left hand owns), lfo-breathe's brightness, party-tumble's
  plane rates under the MASTER drive `scale` — moves a frame earlier.
  A loop that passes through no delay (`lfo:0 → lfo.2.rate` and `lfo:1 →
  lfo.1.depth`, or an LFO pushing its own depth) shows one warning line
  under ROUTING's head, `loop: lfo:0 → lfo.2.rate → lfo:1 → lfo.1.depth
  → lfo:0 needs a delay — lfo:1 → lfo.1.depth is off until it has one`;
  that cable does nothing, its row stays in the table (its checkbox still
  on) and in the file, and the rest of the preset runs.
- **The graph as data.** `hyperspace/patch.py`, a leaf (imports nothing
  from the package; in `hotreload.MODULES` before `routing`):
  `PatchNode(id, kind, delay=False)` with kinds `source lfo modifier
  macro param` — a source's, an LFO's or a modifier's id is the address
  a row names (`lane:0`, `lfo:0`, `mod:3`), a param's or a macro's its
  param id, so the two never meet; `PatchEdge(src, dst, port, cable,
  enabled)` with ports `mod` (a performer row), `when` (its gate),
  `depth` (a `scale` param or a macro's depth subscriber, into the
  cable's target), `base` (a macro's base subscriber: drawn, never
  ordered — the subscribers run at step 3), `in` (a modifier's input)
  and the LFO knobs `shape rate sync depth phase reset` plus `trigger`
  (`lfo.trigger` → every LFO); a modifier's own param edge is named by
  its param. `order(patch)` is a stable topological sort (dependencies
  first, ties in insertion order, `Graph._sort`'s walk); `cycles(patch)`
  lists every elementary loop once over the ordering edges (capped at
  256).
- **The pass.** `Router.build_patch()` makes the graph from the table
  (each performer row, each macro subscriber, each `scale`, each LFO's
  knob params, each modifier's inputs and params); `Router.patch` caches
  it with its evaluation plan and is rebuilt only when `_patch_key`
  moves (every performer row by identity and its `source target op
  enabled scale when`, the macros, the modifiers' ids, kinds and inputs,
  the LFO count, `Registry.serial`). `Router.modulate(analyzer, dt,
  now)` walks the plan: at an LFO's node it steps that LFO; at a
  modifier's it steps the modifier and writes its lane; at a param's it
  runs today's row arithmetic, unchanged, for the rows into its `mod`
  port (the one `p.modulate` call site) and, **only when a later node
  reads that param** (a `scale`, a macro behind a depth subscriber, an
  LFO knob, a modifier's own param), lands it there and then
  (`Param.apply` under the frame's mark). Every other param lands in
  `reg.apply()` in registry order, as before.
- **`Param.apply` is idempotent within a frame.** `Registry.begin_frame()`
  (called by `Router.modulate`) opens a mark; `Param.apply(mark)` returns
  at once if called again under the same mark; `Registry.apply()` passes
  it and closes it. An `apply()` with no pass before it (the tests,
  `Registry.remove`) lands everything as it always did.
- **The LFOs step inside the pass.** `app.main` calls
  `router.use_lfos(lfos, clock)` once; `app.frame` no longer steps or
  publishes them. `Router.modulate` calls `LFOs.begin` (a held trigger
  lands) and `LFOs.publish`, then `LFOs.step_one` at each LFO's node.
  Every LFO is a node whether or not a cable touches it, so each steps
  once a frame. A reset is held for the next step only if its LFO has
  already stepped at this time (`LFO.at`).
- **Loops.** A loop through no delay is broken at its **last cable in
  table order** among those on it: that cable's edges are disabled in
  the patch, the row is untouched. A loop of modifiers alone keeps its
  last modifier's input on the loop off, in id order (that modifier is
  dormant, `loop: mod:1 → mod:2 → mod:1 needs a delay — mod.2's input
  mod:1 is off until it has one`). Loops are cut one at a time and
  listed again after each cut. A delay that closes a loop runs first and
  emits its input's lane as it stood (last frame's), so the loop is
  exactly one frame late; on its first frame it emits its rest (0).
- **Measured** (party-trip, 21 routes, the synthetic hand tape, 2000
  frames × 5 rounds after warm-up, twice): `Router.modulate` 31.4 / 30.5
  µs a frame on the base (the LFOs stepped outside it), 37.2 / 35.0 µs
  now — about 5 µs more, most of it `_patch_key`'s per-frame tuple and
  undo's fingerprint of the modifiers; 0.2% of a 60 Hz frame.
- **Code.** `patch.py`; `routing.py` `Router.use_lfos`, `_patch_key`,
  `build_patch`, `patch`, `patch_notes`, `patch_cut`, `_rebuild_patch`,
  `modulate`; `params.py` `Param._mark`, `Param.apply(mark=None)`,
  `Registry.serial` / `frame` / `landed` / `begin_frame`; `lfo.py`
  `LFO.at`, `LFOs.begin`, `step_one` (`step` is both); `app.py` the
  frame; `ui_routing.head` the loop notes.
- **Tests.** `tests/test_patch.py` (9), notably
  `::test_order_puts_dependencies_first_and_keeps_insertion_order_for_ties`,
  `::test_cycles_finds_every_loop_and_none_through_a_delay`,
  `::test_a_route_a_macro_sub_and_a_scale_are_the_edges_the_design_names`,
  `::test_a_param_the_pass_lands_is_applied_once_a_frame`,
  `::test_a_loop_through_a_delay_runs_exactly_one_frame_late`;
  `tests/test_routing.py::test_every_factory_preset_lands_the_same_values_one_frame_earlier`
  (below), `::test_a_cycle_without_a_delay_disables_its_last_cable_with_a_note`,
  `::test_sinks_still_send_after_apply`;
  `tests/test_app_boundary.py::test_main_hands_the_router_its_lfos`.
  Changed on purpose (decision 7): the two lag tests became
  `tests/test_lfo.py::test_an_lfo_owning_another_lfos_depth_changes_its_output_the_same_frame`
  and `tests/test_routing.py::test_a_macro_owned_by_a_hand_scales_a_lanes_push_the_same_frame`;
  `tests/test_macros.py::test_a_performer_on_a_macro_moves_only_its_depth_subscribers`
  (the depth subscriber reads the hand's 0.9 the same frame);
  `tests/test_app_boundary.py`'s `ORDER` lost the LFOs' two entries
  (the only change), and two raising-step tests now raise inside
  `router.modulate`, where the LFOs step.

**The lag's removal, over every factory preset.** The base build's
`Router.modulate` is kept verbatim in `tests/test_routing.py` as
`_lagged_modulate` (checked bit for bit against the base build before
the change). All 23 factory presets are played through a scratch library
with the synthetic hand tape, the analyzer's lanes held, LFO 1 on a held
square wave; every modulatable param's effective value and every LFO's
output is recorded per frame on both. **Every param no lagged read
reaches is identical frame for frame** (every one a performer moves
directly among them); **the params downstream of a lagged read are the
same sequence exactly as many frames earlier as the base was late** —
party-trip's `camera.zoom` and lfo-breathe's `view.bright` (LFO 1, whose
depth a hand owns) and party-tumble's `rot.rate.ZW` (the `scale` path)
among them. No sequence differed in any other way.

### N1 — modifier nodes, in the preset

- **At the machine.** ROUTING gains a **MODIFIERS** strip between the
  routes and the desk: a kind combo and **+ modifier** on its title
  line; per modifier a line — `MOD n`, its kind, a combo per input (the
  route sources plus the other modifiers' lanes, never its own), the
  live output as a bar and a number ("dormant" while its input is not
  live), × — and a line of its params as the panel's own widgets, so
  Learn, "Route a lane here…" and base → effective come with them. A
  route's source combo lists `mod 2 combine` the frame after it is
  added. "Right hand energy, smoothed, times band 0, into acid mix" is
  built from this page alone.
- **The kinds** (`hyperspace/modifiers.py`, a leaf: `motion`, `tapers`):
  `curve` (`shape` −1…1, y = x^(4^shape), 0 straight; `invert`),
  `scale` (`mul` −4…4, `offset` −1…1, `clamp` on by default), `smooth`
  (`attack` 0…2 s, `release` 0…4 s, a `motion.follow` about 0; `spring`
  on: a `motion.spring` with ω = 1/attack, damping 0.6), `combine` (two
  inputs; `how` add · mul · min · max · cross, `balance` for the
  crossfade; add unclamped), `threshold` (`on` 0.6, `off` 0.4, `hold`
  0.1 s: 1 on the rising edge and while the hold lasts — a **trigger**
  lane, also offered as a gate), `delay` (last frame's input, 0 on its
  first). `step(m, inputs, state, dt)` is pure but for its `ModState`.
- **Ids, params, lanes.** `mod.1`, `mod.2` … (`next_id`: one past the
  highest). Params `mod.<n>.<p>` in the new performance group `mod`,
  modulatable (a hand can drive a smooth's release), declared when a
  modifier is added and dropped when it goes (`routing.declare_modifiers`,
  the `fx.declare` pattern). The output is the lane `mod:<n>` (the lane
  index is n; index 0 unused), labelled `<n> <kind>`, rest 0. A modifier
  whose input is not live this frame (a scheme never fed, a hand out of
  the box, an input not chosen) is **dormant: its lane reads NaN**, so a
  route on it lets go as a route on that source would; its memory starts
  afresh when the input comes back.
- **In the preset.** `"modifiers": [{"id": "mod.1", "kind": "smooth",
  "in": ["hand:right.energy"], "attack": 0.05, "release": 0.6}]`, after
  `routes`, written only when there is one; each param at its base, an
  enum by name, a toggle as a bool; `values` never holds a `mod.*` id.
  `load_doc` reads them before the routes; a route onto a missing
  `mod:<n>` is dropped with a note. A desk template may carry a
  `modifiers` list; a preset naming the template gets them, its own
  overriding by id, and a save writes only the entries that differ from
  the template's as loaded. Never in `bindings.json` (`is_session_row`
  untouched). Undo watches them as one table part (`undo.TABLE_GROUPS =
  ("mod",)`): an add, a remove, an input picked and a param's drag are
  each a step.
- **Learn.** `Learn.accepts` takes a `mod:` lane for a learn armed for
  anything or for "mod"; no menu entry learns one (nothing physical
  moves a modifier).
- **Code.** `modifiers.py`; `routing.py` `declare_modifiers`,
  `Bindings.modifiers` / `modifiers_serial` / `modifier` /
  `modifiers_doc` / `set_modifiers` / `add_modifier` / `remove_modifier`
  / `set_modifier_input`, `Router._step_modifier`, `_sync_modifiers`,
  `lane_kinds`; `params.py` `"mod"` in `PERFORMANCE_GROUPS`; `preset.py`
  `MODIFIERS_KEY`, `NO_MODULE`, `merge_modifiers`; `undo.py`;
  `learn.py`; `ui_routing.py` `modifiers` and its plain functions;
  `ui_presets.py` (the overview leaves `mod` out). Fixtures (force-added):
  `tests/fixtures/modifiers/presets/mod-energy.json`, `mod-missing.json`,
  `mod-templated.json`, `tests/fixtures/modifiers/desk/mod-rig.json`.
- **Tests.** `tests/test_modifiers.py` (27), one per kind on a scripted
  input (`::test_curve_is_linear_at_zero_bends_both_ways_and_inverts` …
  `::test_delay_is_one_frame_late`) and
  `::test_a_modifier_publishes_a_lane_a_route_can_source`,
  `::test_a_modifier_reads_another_the_same_frame_whatever_its_id`,
  `::test_modifiers_live_in_the_preset_and_never_in_bindings_json`,
  `::test_a_route_onto_a_missing_modifier_is_dropped_with_a_note`,
  `::test_a_template_may_carry_modifiers_and_a_preset_overrides_by_id`,
  `::test_the_routing_page_builds_the_smoothed_energy_times_band_patch`,
  `::test_an_older_preset_without_the_key_loads_as_before`.

### N2 — the GRAPH page

- **At the machine.** A page **GRAPH** after ROUTING. Its head: the
  counts (`55 nodes · 239 cables · 50 live` on party-trip), the last
  refusal or a hint, and three chips — **patched only** (every node
  collapsed to its patched ports), **tidy**, **beside**. One canvas,
  left to right: the devices (by role), the keys, the analyzer (a port
  per band), the LFOs (their knobs as input ports), the modifiers, the
  macros (bus nodes), the params' nodes, the render nodes, the outputs.
  A route is a solid cable into a param's round `mod` stub, a desk / pad
  / key row a faint one into its square `base` stub, a macro subscriber
  a cable into `base` or into a route's `depth` stub; render cables join
  image / geometry / mask ports. Cables are coloured by kind, a value
  cable's thickness follows its reading, a dormant one is faint, a cable
  a loop keeps off says so on hover. Hover a cable: from → to, its
  reading, its depth, its `scale` and gate. Click a route: its ROUTING
  row in a pane **under** the canvas (CONTROLS is 540 px; **beside**, or
  a page 720 px wide, puts it in a side column); click an effect's node:
  its FX strip. SYSTEM gains `graph page: 2.78 ms median (55 nodes, 239
  cables)` once the page has drawn.
- **The model** (`hyperspace/graphview.py`, no imgui): `build(…) ->
  View` of `VNode`s (`device`, `template`, `source`, `analyzer`, `lfo`,
  `modifier`, `macro`, `render`, `output`, `group`), `VPort`s and
  `VCable`s (`route`, `setter`, `sub`, `input`, `render`), from the
  table, the registry, the Router, the device registry (read through
  `Device`'s protocol) and the render graph the renderer last built.
  Params sit on the render node that owns them by one table, `OWNERS`
  (`view` / `rot` / `pattern` → `shape`, `ghost[.<n>]` → that hands node,
  `dream` → `history`, `fx.<effect>.*` → that effect's node, `camera` /
  `eye` → `render:eye`, `output.<n>.*` → that output); every other group
  is a node of its own (`group:tempo`, `group:master`). Drawn: every
  modulatable param plus any a row names. Not drawn: sink rows; a
  route's `scale` and `when` (said on its hover). `key` says when to
  rebuild; `refresh` moves only the readings each frame.
- **The page** (`hyperspace/ui_graph.py`): `page(panel, dt)` on
  `imgui_bundle.imgui_node_editor` (no new dependency), the widget's
  settings file off (`Config.settings_file = ""`): no `NodeEditor.json`
  anywhere. The editor context lives on the panel (`panel._graph`), so
  a hot reload of `ui_graph` keeps drawing on it; `Panel.close` destroys
  it, on quit and on ⌘R, before imgui shuts down.
- **Layout.** Positions are whole canvas units in two maps:
  `preset["layout"]` (`{"<node id>": [x, y]}`, written sorted, one node
  a line, last in the file, only when non-empty) for the look's nodes —
  modifiers, macros, the render nodes (outputs aside), `render:eye`, a
  performance group's node — and the show's `layout` for the rig's —
  devices, sources, the analyzer, LFOs, outputs, a session group's node
  (`graphview.home`). A node is written only when it is dropped; an
  unplaced one takes `auto_layout`'s column (sources, LFOs, modifiers,
  macros, groups, the render nodes by depth, outputs). A drop dirties
  the preset or the show; **tidy** forgets every position on the canvas
  and lays all out again as one undo step. The library's marks carry
  both maps, so undoing a load puts the earlier positions back.
- **Code.** `graphview.py`, `ui_graph.py`; `ui.py` `PAGES` (`("graph",
  "graph", None)` after routing), `Panel._page_graph`, `Panel.close`, the
  SYSTEM line; `ui_fx.strip` (factored out of the FX page unchanged);
  `preset.py` `LAYOUT_KEY`, `Presets.layout`; `library.py` `LAYOUT`,
  `read_layout`, `Project.layout`; `app.py` the panel in both close
  lists; `hotreload.MODULES` (`graphview` after `osc`, `ui_graph`
  before `ui`).
- **Tests.** `tests/test_graphview.py` (18), headless, notably
  `::test_every_route_is_one_cable_and_every_cable_one_route`,
  `::test_macro_subs_are_cables_into_base_or_depth`,
  `::test_params_group_under_the_render_node_that_owns_them`,
  `::test_device_nodes_come_from_the_registry_with_their_port_groups`,
  `::test_the_render_graphs_edges_are_image_cables_including_a_placed_effect`,
  `::test_layout_round_trips_through_the_preset_and_the_show`,
  `::test_auto_layout_gives_every_unplaced_node_a_column`,
  `::test_the_page_draws_with_a_factory_preset_and_a_render_graph` (the
  real widget, headless), `::test_the_editor_context_is_made_once_kept_across_a_reload_and_destroyed_on_close`,
  `::test_graphview_imports_no_imgui`.

### N3 — editing the modulation on the canvas

- **At the machine.** Drag from a source's pin to a param's round `mod`
  stub: the route a Learn would make (`learn.row_for`, `Learn._row`'s
  table moved out unchanged: a **push** for a centred source or a param
  centred on zero, at `hands.learn_depth` for a hand, else the
  **position** fader at depth 1). A taken param brings up ROUTING's
  Replace / Keep. A desk control dropped on a `base` stub is a desk
  learn (a preset-layer row, the same refusals); a pad button or the
  D-pad the pad learn's session row. Refused in words on the page's head
  and on the drag: "a hand sets no base; aim at mod" (and the same for
  a band, an LFO, a modifier, a stick), "a desk knob sets a base, not a
  performer; aim at base", "keys are the session's rows: map them on
  ROUTING", "a macro sets a base or scales a depth; aim at base or a
  depth stub", "join an output to an input". A drag that starts on a
  patched input pin and ends on another input pin **moves** that cable
  (`move_route`: same op and depth, its depth subscribers follow). A
  macro's `bus` onto a `base` stub is a base subscriber, onto a route's
  `depth` stub a depth subscriber; onto a modifier's `in` an input.
- **Insert.** A modifier node with no cables let go over a route or a
  modifier-input cable (its centre within 14 canvas units of the curve
  the widget draws, `graphview.cable_near`) is inserted: the cable's
  source becomes its first input, its lane the cable's source; a push
  keeps its old source's rest. A cable's right-click **insert ▸
  <kind>** does the same with a new modifier.
- **The picker and delete.** Right-click the canvas: **modifier ▸
  curve · scale · smooth · combine · threshold · delay** and **macro ▸**
  the idle macros (labelled "macro N" when picked), landing where the
  menu opened. Delete (the key, or a right-click **delete**): a route
  goes with its depth subscribers, a preset-layer desk row goes, a macro
  subscriber leaves its macro, a modifier input is unset; a session row's
  cable (keys, the pad, an invariant or global-layer desk row) is
  refused: "<source> is the session's (bindings.json): edit it on
  ROUTING". A modifier node's delete leaves its lane's routes, dormant; a
  macro node's clears its label and every subscriber, the knob staying.
  The rig's nodes are refused ("<label>: the rig's, not the preset's").
  Each edit is one named undo step through the table's own calls.
- **Learn from a port.** Right-click a `mod` stub: the param menu's
  Learn items (`Panel._ctx_learn_block`, the same function the widgets
  call: desk, hand ▸ left / right, pad, a role, sink); the completed row
  is a cable next frame, because the view is rebuilt from the table.
- **Code.** `graphview.py` `Edit` (`connect`, `refusal`, `connect_value`,
  `route_for`, `subscribe`, `set_input`, `move`, `disconnect`,
  `insert_modifier`, `add_modifier`, `show_macro`, `remove_node`),
  `Refusal`, `Ask`, the words, `bezier`, `cable_near`; `learn.row_for`;
  `ui_graph.py` the dispatch tables `CREATE` (by pin type),
  `DELETE` (by cable kind), `DELETE_NODE` (by node kind), the menus, the
  picker, `dropped`; `routing.Bindings.set_modifier_input` (shared with
  ROUTING); `ui.Panel._ctx_learn_block` (shared with the widgets' menu).
- **Tests.** `tests/test_graph_edit.py` (17), notably
  `::test_connecting_a_source_to_a_mod_port_adds_the_route_learn_would`,
  `::test_a_taken_param_asks_and_replace_owner_lands_the_cable`,
  `::test_moving_a_cables_end_moves_the_route_and_its_depth_subs_follow`,
  `::test_a_hand_into_a_base_port_is_refused_in_words_and_a_pad_is_a_setter_row`,
  `::test_dropping_a_modifier_on_a_cable_inserts_it`,
  `::test_deleting_a_cable_removes_the_route_and_undo_puts_it_back`,
  `::test_learn_from_a_port_lands_as_a_cable`,
  `::test_the_routing_page_and_the_graph_page_show_one_table`,
  `::test_create_and_delete_open_only_in_the_typed_dispatch` (which
  replaced N2's `test_the_page_is_read_only`, as that test's docstring
  said it would).

### N4 — the render graph edited: nodes and a wire list, outputs as nodes

- **At the machine.** An image cable dragged between two typed ports is
  a wire in the loaded preset's `graph` section, type-checked while it
  is dragged: a wrong one goes red with the words a file would get. A
  geometry cable from a hands node into the scene or the layer sets that
  node's `into`. Right-click the canvas: **effect ▸** each effect file
  (a new instance at its defaults, off, in the chain at its order),
  **hands** (a new hands node), **composite**; right-click a render node:
  `draw solid` / `draw lines` (hands), `laid over` / `add` / `depth` (a
  composite), **delete**. The Delete key on a wire unwires it; on a
  default cable it is refused ("… is the default graph's: no wire says
  it …"). Instance 1 of an effect, hands 1, the scene, the history and
  the outputs cannot be deleted. Every edit is one undo step and dirties
  the preset; the renderer builds the graph again. The OUTPUT page says
  a wired output in words (`acid 2 by a wire`, `· hands 2 over output
  2`); SYSTEM shows a wired output's own end, `wire(output.2)`.
- **The wire list.** `"graph": {"nodes": [...], "wires": [{"from":
  "hands.2", "to": "output.2.hands"}, {"from": "palette", "to":
  "output.1.image"}]}`. `from` is a node (its one output: `scene`,
  `hands`, `hands.<n>`, `history`, an effect instance, a composite);
  `to` is `<node>.<port>`. A preset may wire `output.<n>.image`,
  `.hands`, `.readout`, `history.image`, an effect's `image`, a
  composite's `under` / `over`; geometry and mask ports are typed but
  not wireable. Kept in the file's order, one wire a line; no wires
  writes no key. D1's placements are the same wires written short
  (`after X` is `X → E.image`, `into Y` is `E → Y.image`) and a D1-only
  section is still written short, byte for byte; an edit on the canvas
  writes wires.
- **Outputs as nodes.** A wire into `output.<n>.image` overrides that
  output's switch-derived picture through an end of its own
  (`graph.Wired`, `wire(output.<n>)`); into `.hands` it lays that node
  over (depth-aware when the blend says so), and on a through output it
  replaces the switch's hands; into `.readout` that layer's guide. An
  output no wire names is node for node the default graph's, following
  the session's switches; a load never writes a switch. So a preset may
  say which output gets which hands node and which effects it alone
  takes — plan 26's "wiring choices, not a graph" rough edge, closed.
- **Refusals cost that wire, not the graph.** A wire into a port of
  another type, a missing node or port, two wires into one port, a node
  that makes nothing (an output), the history into `.hands`, a loop: one
  note each, `graph: wire ghost → output.1.image — ghost makes geometry,
  output.1.image takes a picture; the default wiring`; that port keeps
  its default (or D1's placement), the rest stands, the section is kept
  as written. A malformed wire (not two strings, or twice) is an
  unreadable section: the default graph. A wire on a node this frame
  lacks is dormant and said (`wire hands → output.3.hands — no output 3
  this frame`).
- **Two fixtures** (force-added), goldens recorded once, "N4 fixture,
  new": `tests/fixtures/presets/hands-glass-only.json` (hands-lines'
  values, `ghost` in the scene as lines, `ghost.2` the layer, wired to
  `output.2.hands` only) and `wired-outputs.json` (palette-glass's
  values, the palette wired into `output.1.image`, a second acid after
  the history into `output.2.image`). `tools/golden_frames.py` switches
  on any `ghost.<n>.on` a fixture declares; a wired output's manifest
  route reads `none`, with a `"wired"` key naming its source.
- **Code.** `graph.py` `Wire`, `CompositeAt`, `WIRE_MAKES` /
  `WIRE_TAKES` / `TYPE_WORDS`, `wire_error`, `wire_loops`,
  `split_wires`, `d1_wires`, `GraphSpec.wires` / `all_wires()`,
  `Wiring.wires` / `composites`, `Wired`, `_Wiring`, `Graph.relink`,
  `wire_words`, `output_wires`, `placed_chips` extended; `preset.py`
  `GraphSection.read` / `files`, `dumps`; `ui.py` `output_shows`;
  `graphview.py` `spec_name`, the render edits (`Edit.wire`,
  `wire_refusal`, `unwire`, `add_node`, `drop_node`, `set_node`),
  `picker`; `ui_graph.py` `render_edit`, the render handlers in N3's
  tables, the picker and node menus.
- **Tests.** `tests/test_graph_wires.py` (17), notably
  `::test_a_wire_list_round_trips_and_d1_keys_read_as_wires`,
  `::test_a_wire_into_an_output_overrides_its_switch_and_an_unnamed_output_keeps_them`,
  `::test_a_wire_of_the_wrong_type_or_into_a_missing_port_is_a_note_and_the_default`,
  `::test_a_cycle_of_wires_is_refused`,
  `::test_dragging_an_image_cable_on_the_canvas_edits_the_spec_and_dirties_the_preset`,
  `::test_the_picker_adds_an_effect_instance_with_its_params`,
  `::test_hands_as_lines_through_the_acid_with_tracers_by_wires_alone`
  (hands-lines' picture from a spec built by `Edit` calls),
  `::test_no_factory_preset_changes`,
  `::test_a_hands_wire_on_a_through_output_replaces_the_switch_hands`.
  `tests/test_golden_frames.py`'s completeness count gains `+ 2 * 8`.

### N5 — controllers as nodes; the APC40 as two nodes

- **At the machine.** The APC40 is two nodes: *apc40* (every control,
  the invariant ones first in an `invariant` group: SHIFT, the
  crossfader and MASTER, the bank pads, transport, TAP …; then `track
  knobs`, `device knobs`, `knobs`, `faders`, `clip grid`, `buttons`),
  drawing the preset layer's rows and the invariant rows, and *apc40
  (SHIFT)* (every control but the invariant ones), drawing the global
  layer's (`bindings.json`). Latch SHIFT and *apc40 (SHIFT)* is bright,
  *apc40*'s preset ports and cables faint, its invariant ports as they
  were; release, and back. A drag from a SHIFT-node port into a `base`
  stub is refused whatever the latch ("… on the SHIFT node is the
  session's (bindings.json): map it on ROUTING"). The hands' node folds
  as axes, pinches, grab, presence, dance. A preset naming a desk
  template draws it as one collapsed node, *template <name>*, listing
  its controls ("D1 → view.depth4" …) and no cables; its **+** opens it
  and its rows are cables; an edit inside is an override in the preset
  (the template file is never written), and the edited row's cable then
  leaves *apc40*. A row from a role this rig lists no device for hangs
  off a grey node named by the role, its cables faint, until the device
  arrives in its place. **Presentation only**: the rows, their homes,
  D1, D4–D6 and D12, `apc40.py` and `midi.py` are untouched.
- **How.** `graphview.device_nodes` makes one node per entry of
  `Device.layers` (`device:apc40`, `device:apc40/global`); invariance is
  the table's own `Bindings.is_invariant`; the latch is
  `Bindings.layer_of(role)`, the value `MidiIO` itself reads, set in
  `refresh` each frame (a flip rebuilds nothing). A layered row on an
  invariant control never acts (D6): its cable is drawn off, on
  *apc40*'s invariant port. The template node's rows are the load's
  (`Presets.template_at_load()`); a live preset-layer row still the
  template's is a cable from it. A placeholder's role: the row's
  qualifier, else the desk's first role for MIDI, else the kind's usual
  role from `config.py`'s example list, else the scheme.
- **Code.** `graphview.py` the controllers section (`desk_group`,
  `hand_group`, `device_nodes`, `template_rows`, `DESK_GROUPS`,
  `SCHEME_ROLE`, the layered and template pins, `refresh`'s latch);
  `ui_graph.py` `template_of`, `is_open`, `toggle_open`, `drawn_cable`;
  `preset.py` `Presets.template_at_load`. `devices.py` unchanged.
- **Tests.** `tests/test_graphview_devices.py` (8):
  `::test_the_apc40_is_two_nodes_and_each_row_hangs_off_its_layers_node`,
  `::test_invariant_controls_are_ports_on_the_first_node_only`,
  `::test_a_drag_from_the_shift_node_into_base_is_refused_whatever_the_latch`,
  `::test_a_templated_desk_is_one_collapsed_node_whose_edits_write_overrides`,
  `::test_a_missing_role_is_a_grey_placeholder_with_dormant_cables`,
  `::test_the_hands_node_groups_axes_pinches_grab_and_dance`. One N2
  assertion changed: the hands' `switches` group is `pinches` / `grab`.
  `git diff --stat` of `apc40.py` and `midi.py` against the base: empty.

### N7 — a legible graph: collapsed by default, one wire per node pair, GRAPH takes the routes

Added after the owner's first look at the GRAPH page (2026-10-20): "It
looks good. It's very messy … borderline illegible when we just have the
APC40 alone … by default you should only see one line going between
them … The graph was meant to replace the routing tab … I clicked the
tidy button, and nothing happened … I clicked the beside toggle, and I
don't know if it did anything." The owner's three decisions (DECISIONS
"UI", Who "owner (2026-10-20)"): every node collapsed by default; one
wire between two nodes while either end is collapsed; GRAPH replaces
ROUTING — the routes and the modifiers now, the rest later.

- **At the machine.** GRAPH opens as a handful of boxes: each node's
  title and one to four short lines ("137 ports · 97 patched", "> L x
  0.57", "preset layer · up"; "51 params · 32 patched" on *shape*; "smooth
  · out 0.42" on a modifier), an in dot at the left of its title and an
  out dot at the right, and **one wire** from *apc40* to *shape*, one to
  *fx*, one to *eye* — 64 wires for party-trip's 238 cables. A wire is as
  thick as it is many (capped at ten); its hover lists ten of its cables
  and "+ k more"; clicked, its rows are in the pane (routes as ROUTING's
  rows); Delete says "expand a node to edit its cables". A box's **+**
  expands it (N2's ports, **patched only** within); both ends expanded,
  the real cables. **expand all / collapse all** on the head. A cable
  dropped on a collapsed box's in dot opens a list of what it can land
  on (a collapsed modifier's, LFO's or macro's out dot is its one output,
  so its out dropped on another collapsed box opens that box's list);
  right-click a box for **learn ▸** any of its params. **tidy**
  collapses everything, lays it out again, frames it and says "laid out
  55 nodes, every one collapsed" (or "already tidy"). The details chip
  shows only with a selection on the narrow page, as **details beside** /
  **details below**. A modifier's box selected shows its editor (inputs,
  params, live bar, × remove). ROUTING has a line "routes and modifiers:
  the GRAPH page" (a click opens it) where its routes and MODIFIERS strip
  were; its desk, macros, session and sinks are unchanged; "Route a lane
  here…" opens GRAPH with the new route's wire selected, its row first in
  the pane.
- **How.** `graphview.summary` (the lines), `stub_in` / `stub_out`
  (`nin:` / `nout:` pins), `wiring` (cables drawn as they are, render
  cables re-ended on a collapsed node's stub, the rest folded into
  `VBundle`s per node pair), `bundle_tip`, `land_choices` (a stub's
  picker, each pin with `Edit.refusal`'s words); `refresh(collapsed=…)`
  reads only what a collapsed node shows; `View.node` an index.
  `ui_graph`: the expanded set `st["open"]` (the template's N5 open set,
  now every node's), `collapsed`, `full`, `expand_all`, `_stub`,
  `_bundle` / `bundle_thickness`, `_stub_drag` / `open_land` / `land` /
  `_land_menu`, `delete_bundle`, `_bundle_menu`, `learn_params`, `tidy`,
  `beside_chip`, `head_line`, `route_rows`, the wiring and the columns
  cached on the state. `ui_routing`: the pointer line in `page` (the two
  sections' drawing dropped, the filter's count without them),
  `modifier_block` factored out of `modifiers` (its `stacked` form for
  GRAPH's pane), "Route a lane here…" to GRAPH. Every edit still goes
  through `graphview.Edit` and the table's own calls.
- **Draw time**, the real app on party-trip at the control window's
  960 × 900, the smoke run's patch (an LFO on LFO 2's depth, two
  modifiers, a route on the combine), 80 draws each: **1.27 ms median
  collapsed** (p90 1.40; 55 nodes, 64 wires, 238 cables), 2.66 ms with
  every node expanded (patched only: N2's default view), 1.29 ms after a
  tidy — against N2's 2.32–2.78 ms. Before the caches the collapsed page
  drew in 2.18 ms.
- **Tests.** `tests/test_graph_legible.py` (14; review round 1 added the
  reveal, the dormant / live bundle and the menus, and made the energy
  patch four drops through the page's drop path with every node
  collapsed):
  `::test_every_node_starts_collapsed_with_at_most_five_lines`,
  `::test_the_apc40_to_one_shader_is_one_bundle_while_collapsed`,
  `::test_a_bundle_splits_into_its_cables_when_both_ends_expand`,
  `::test_a_bundles_hover_and_side_pane_list_its_rows`,
  `::test_a_drag_onto_a_collapsed_node_offers_its_ports_and_lands_through_edit`,
  `::test_deleting_a_bundle_is_refused_in_words`,
  `::test_tidy_collapses_all_relays_and_says_what_it_did`,
  `::test_beside_shows_only_with_a_selection`,
  `::test_routing_no_longer_draws_routes_or_modifiers_but_their_functions_stay`,
  `::test_the_smoothed_energy_times_band_patch_from_graph_alone`,
  `::test_the_page_draws_in_every_state`,
  `::test_route_a_lane_here_selects_the_new_route_on_graph`,
  `::test_a_dormant_bundle_draws_faint_and_a_live_one_moves_without_a_rebuild`,
  `::test_a_bundles_menu_and_a_nodes_learn_menu_draw`. Changed: `test_graphview.py`'s
  page test expands every node before selecting a route (by expanding);
  `test_graph_edit.py`'s one-table test finds the cable's row in GRAPH's
  side pane, and its dispatch test admits `_stub_drag` and
  `delete_bundle`; `test_ui_routing.py`'s row tests draw the rows as
  GRAPH's pane does (`ui_graph.route_rows`), its filter tests count
  without routes, and its "Route a lane here" test opens GRAPH;
  `test_ui_shell.py`'s scroll test measures the child with the desk;
  `test_modifiers.py`'s strip test draws the strip's function and checks
  ROUTING's pointer.

## The goldens

**596 goldens, 140 distinct pictures**, on "Apple M3 Max". The 556 of
the base and D1's 24 matched byte for byte after every N WP: the
dependency order, the modifiers and the GRAPH page moved no pixel (the
goldens are recorded at rest, the LFOs and analyzer never stepped). N4
recorded 16 new, once, "N4 fixture, new": its two fixtures, hands
present, in the eight output states (4 new pictures). The review pass
diffed every hash against the base's manifest: all 556 identical, 40
new entries (8 per fixture, five fixtures), nothing else changed but one
`"wired"` key.

## What no person has verified

Everything on the canvas. Every proof is headless: the tests drive the
page's functions and the real widget headless (drawn, menus opened), but
**no test can drag the mouse on the widget**, so how `imgui_node_editor`
reports a real drag, a Delete, a right-click's subject and a node let go
over a cable is unexercised. One windowed smoke run (party-trip, the
hand tape, 120 frames) added an LFO-on-LFO route, two modifiers and a
cable from the live loop: the route landed the same frame on all 115
frames, the modifiers' lanes moved, ROUTING listed the canvas's cable,
and the page drew in 2.78 ms. In particular:

- **The lag gone on a real LFO-on-LFO patch**, by eye (232), and every
  LFO's scope after the move (235).
- **A cable dragged on the laptop screen** at the control window's size
  (247): pin size, zoom, the red refusal, the drop of a modifier on a
  cable.
- **Learn from a port** with the APC40 and with a hand (248).
- **The hand-energy patch** built on ROUTING, then on the canvas, felt
  with a real hand (241, 249).
- **"Hands as lines through the acid with tracers" by dragging**, seen on
  the projector (251); **a hands node wired to the glass alone** (252):
  the wired layer through a presenter on a real second window.
- **The APC40 as two nodes** with the real desk, SHIFT latched and
  released (256).
- **A patch saved on one Mac loading on the other** through the shared
  library (259), and an owner's preset from before this run loading with
  no note (260) — the review pass loaded the pre-run fixtures and every
  factory preset clean; the owner's own files have not been tried.
- The canvas's legibility at distance: the pin glyphs, the faint
  setters, the APC40's long port lists, the narrow page's pane.
- **N7's collapsed graph** (261–266): whether party-trip reads at a
  glance at the desk; a real drag onto a collapsed node's stub (the
  widget reporting a drop on a stub pin, the picker opening there);
  tidy's framing; the energy patch built on GRAPH alone with a real
  hand; ROUTING's desk section with the real APC40 after the change. Two
  windowed runs (the timing probe) drew the page collapsed, expanded and
  tidied with no stall and took the numbers above; nobody has looked at
  it but a screenshot.

## Known rough edges

- **An older build and this run's keys.** A preset saved here with a
  placement or a wire opens on a build from before this run as the
  default graph with one note (the section kept on its save); its
  `modifiers` and `layout` are ignored there with no note and **dropped
  by a save on that build**; a `mod:` route is a dormant row there. The
  shared library syncs presets between two Macs: both must run this
  build before patches are shared (row 277).
- **A delay closing a loop emits its rest, not NaN, when the loop's other
  source goes away**, and passes ±inf through (harmless: `Param.modulate`
  drops non-finite, a modifier reading it drops its memory).
- **A loop's cut cable still reads on** on ROUTING; only the note (and
  the cable's hover on GRAPH) says it is off. The note uses node ids
  (`lfo:1 → lfo.1.depth`), not labels. An LFO owning its own depth,
  which ran before with a frame of lag, is now refused until a delay
  sits in it.
- **`Router.modulate` is about 5 µs a frame dearer** (31 → 36 µs on
  party-trip), mostly `_patch_key`'s tuple.
- **The equivalence test holds the lanes and LFO 1 still** (a lagged term
  times a moving one is not a pure shift), and no factory preset carries
  a modifier or a delay: those are proven by `test_patch` and
  `test_modifiers` only. The oracle shares the Router's helpers, so it
  proves timing and order, not the helpers.
- **Three tools keep the old frame shape**: `tools/preset_shots.py`,
  `tools/undo_demo.py` and `tools/faces_page_shots.py` step the LFOs
  themselves and never call `use_lfos`, so they still lag a frame on an
  LFO-on-LFO patch (harmless for stills; no double step).
- **Modifiers**: a combine with one dormant input is wholly dormant; a
  combine `add` is unclamped (a `position` route clamps it, a `push`
  does not); a spring smooth has no release; a threshold whose input
  returns already above `on` fires at once; removing the highest
  modifier and adding again reuses its number, and a route left on that
  lane wakes on the new node; a preset cannot remove a template's
  modifier (no "none" entry); short sliders on a narrow strip.
- **A drag on its own is not an undo step**: positions come back only
  with the undo of a load or a tidy, and undoing an earlier load puts the
  show's positions back as they were then, losing a later drag of a rig
  node. A render node a later plan renames loses its saved position.
- **The selection pane sits below the canvas** at CONTROLS' 540 px; it is
  beside only with **beside** or a page 720 px wide. Selection is read a
  frame late.
- **The page's own cost**: 2.78 ms median at 960 × 900 on party-trip (55
  nodes, 239 cables, patched only), about 3.8 ms with every node
  expanded (headless); `route_said` runs per route per frame and `key`
  builds a tuple over every binding each frame. The canvas is wide with
  thirteen effects a pipeline.
- **Setter cables are faint, not dashed** (`ed.link` draws no dash): only
  the square `base` stub tells a setter from a route. The APC40's ~100
  desk rows make many base cables.
- **Editing**: the source end of a cable cannot be dragged (delete and
  draw again, or insert); a modifier already patched is never inserted by
  a drop (use **insert**); drop detection uses last frame's pin centres;
  a pad setter writes `bindings.json` at once and is not an undo step
  (as the pad learn); a source the registry does not list is never read
  as centred; the private Learn's "learned …" words are not shown, only
  refusals; picking a macro labels it "macro N", which dirties the
  preset, and deleting a macro node loses a label the owner typed (⌘Z
  brings it back).
- **The render edits**: a loaded section that carried a refused wire or
  placement is kept, but the first canvas edit writes the accepted spec
  and drops the refused part; a wire list's order counts for equality (a
  rebuild, nothing more); every wire into a doubly wired port is refused,
  and every wire on a loop; a drag's red words are a tooltip, not a note;
  D1's `into: <effect>` has no wire spelling; two
  spellings for "hands in the scene" (a geometry drag, `into` in the
  JSON); on a through output a hands wire means the effects no longer
  bend the hands.
- **The fixtures**: at the machine `ghost.2.on` starts off (switch it on
  on HANDS); in `hands-glass-only` hands 2 is also on any output whose
  switches lay a layer with the scene off (A4's one-layer rule); a wired
  output's golden route reads `none`. Their name assumes the glass is
  output 2; on the hand checks' two-screen rig the glass is output 1.
- **Controllers**: the global layer's rows are edited on ROUTING only; an
  invariant fader (the crossfader) sits in `invariant`, not `faders`; a
  second MIDI desk with no latch is one node and never faint; a collapsed
  template's targets show a patched `base` stub with no visible cable
  (its hover names the template); after an edit inside a template the
  cable jumps to *apc40*; with no desk listed the placeholder is one
  node; `SCHEME_ROLE` guesses from `config.py`'s example names, so a rig
  that calls its hands role otherwise gets a placeholder `leap`;
  `presence` is a fifth hands group the design did not name.
- **N7**: the APC40 is still two nodes (decision 12), so the desk reaches
  a node it maps on both layers over two wires; the keys' node fans out
  to about ten group nodes; two render cables between the same collapsed
  pair overlap; a desk row in a bundle has no editor in the pane
  (ROUTING's desk section edits it); "+ route" is gone (a drag, a Learn
  or "Route a lane here…" makes a route); the collapse state is not
  saved, and a tidy's undo brings the positions back but not the
  expanded nodes; a placed node can be overlapped by one expanded above
  it; the stub's picker on *shape* is long (about fifty params, by
  group); older hand checks that say "on ROUTING add a route" are done
  on GRAPH (a note at the top of group Y says so).
- **The docstring of `graphview.py`** says it imports `routing`,
  `params`, `graph`, `patch`, `modifiers`: since N3 it imports `learn`
  too.

## Decisions

The owner's (2026-10-12 and 2026-10-16), built as written (the launch
prompt's 6–16):

6. **One editor for both graphs; N1–N4 in one plan**, with controllers
   as nodes.
7. **Evaluation in dependency order removes the one-frame lag**; loops
   only through a one-frame delay node.
8. **Modifiers live in the preset**, beside `routes`; a desk template
   may carry them.
9. **Two input ports per param**: `base` many (last touch wins), `mod`
   one under the referee; combining two performers is an explicit
   `combine` node.
10. **Values and triggers are two signal kinds**, crossed by `threshold`
    and `smooth`; encoder vs fader behaviour is the port's, set by the
    device profile.
11. **Roles, not serials**; a missing device's cables wait.
12. **The APC40 is two nodes**, *APC40* and *APC40 (SHIFT)*, no layer
    view; D1, D4–D6 and D12 hold; invariant controls on *APC40* only;
    the faders and the APC40's map and feel are Dylan's and untouched.
13. **Both graphs live in the preset as plain JSON**; today's routes
    convert one-to-one into cables.
14. **Rejected**: GLSL written in the graph; a general TouchDesigner.
15. **The editor is `imgui_node_editor` from imgui-bundle**; no new
    dependency.
16. **The processes in force** (the render stack writes no param,
    `graph.py`'s imports, the hands package liftable, the core's
    imports; agents on Opus / Sonnet, never Fable).

The owner's after the first look (2026-10-20), built in N7: **every node
collapsed by default** (a title and at most five short lines, nothing
per port until expanded); **one wire between two nodes while either end
is collapsed**, the real cables when both are expanded; **GRAPH replaces
ROUTING** — the routes and the modifiers now, ROUTING keeping its desk,
macros, session and sinks until a later pass retires it.

What the run decided where those left a choice (register rows 233–290):
`patch.py`'s types (233); which params the pass lands and the frame's
mark (234); the patch's cache key (235); a loop's cut and its note
(236); a delay's place in the order (237); the LFOs inside the pass
(238); the equivalence oracle's shape (239); the modifier kinds' params
(240); the `mod` lane and a dormant modifier (241); ids and a removal
(242); a modifier's params in its entry (243); a template's modifiers
in a save (244); undo over the modifiers (245); Learn and a `mod:` lane
(246); the MODIFIERS strip (247); node and pin ids (248); the `OWNERS`
table (249); what the canvas draws (250); the two layout maps and tidy
(251); the tidy columns (252); the editor context on the panel (253);
the selection pane (254); a cable into `mod` (255); a cable into `base`
(256); moving a cable's end (257); a modifier dropped on a cable (258);
the node picker (259); a macro onto `mod` refused (260); a macro node's
delete (261); cable deletes (262); the wire list's keys (263); the
wireable ports (264); D1's keys as wires (265); outputs as nodes (266);
a wire's refusals (267); the render picker and how edits land (268);
the wire fixtures' look (269); the APC40's two nodes (270); the desk's
port groups (271); the latch read from the table (272); a layered row
on an invariant control (273); a template as a subgraph (274); grey
placeholders by role (275); the hands' groups (276); an older build and
this run's keys (277). N7: a collapsed node's lines (278); the stubs (279); a
bundle (280); a bundle selected and its refused Delete (281); the
collapse state as UI state (282); the picker on a stub (283); Learn from
a node's menu (284); tidy (285); the details chip (286); expand all and
patched only within (287); ROUTING's pointer (288); a modifier's pane
(289); the readings and caches (290).

**What the launch prompt asked for that was built otherwise.**
- **"A `param` node … then applies that param now"**: only the params a
  later node reads land in the pass; the rest land in `reg.apply()`, so
  no trigger fires mid-pass and registry order holds for the leaves.
  The values are identical.
- **"The new sequence equals the old shifted by one frame for every
  param a performer moves"**: a param a performer moves directly was
  never late, so it is asserted identical; only the params downstream of
  a lagged read are shifted, by the base's lag.
- **"A dormant modifier's lane stays at its rest, 0"**: it reads NaN (not
  live), so a route on it lets go and the base returns, as on any absent
  source. `curve`'s S-shape is not built (the exponent only; the table
  option was out of scope).
- **The LFO's ports `depth rate phase`**: every knob is a port (`shape
  sync reset` too) and `lfo.trigger` feeds every LFO; a `when` port
  orders a row's gate.
- **`graphview` imports `devices`**: it reads the device registry through
  `Device`'s protocol and imports no `devices`; it imports `learn` (N3).
- **A pad cable into `base` as `Binding(src, pid, "abs",
  layer="preset")`**: it is the pad learn's own session row (an `abs` row
  on a button does nothing, and `is_session_row` would class it as the
  session's anyway). A cable into `mod` follows `learn._row`'s whole
  table, not "push only for a hand axis".
- **"From a macro → a Sub" and "a macro port to a `mod` port →
  `Bindings.add`"**: a macro onto `mod` is refused (no scheme publishes a
  macro's knob); it lands only on `base` or a `depth` stub. Every macro
  is already a node, so the picker offers the idle ones.
- **The selection "in a side column"**: below the canvas by default,
  beside on **beside** or a wide page. SYSTEM had no panel line, so the
  page added its own.
- **`default_graph(views, wiring, clouds, wires)`**: D0 had taken the
  fourth slot (`effects`), so the wires ride in `Wiring`; the graph key
  moves with them through the comparison `_graph_for` already does.
  Geometry edits are a hands node's `into` (A4's JSON), not wires.
- **The hands' groups "axes, pinches, dance, grab"**: `presence` is kept
  too; `hands/device.py` is unchanged (its `switches` relabelled by
  address).
- **The APC40 nodes' "each port sending only while its layer is up …
  rings and LEDs follow the node that is up"**: that is the desk's own
  behaviour, unchanged; N5 draws it (lit or faint ports, dormant cables).
