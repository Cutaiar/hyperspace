# N2 — the GRAPH page, read-only (plan 28, stream N)

You are the implementer of work package **N2**. Read first, in full:
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your rules and your
first three git commands: fetch `origin plan-28-30-integration`, `git reset --hard
FETCH_HEAD`, `git branch -m plan-28-n2-graph-page`; one plain git command per shell
call). Your base must be the SHA in your dispatch or later (D0, N1 and N0 are merged).

Then, in your worktree under `hyperspace-python/`:
- `docs/plans/28-30-orchestrator-prompt.md` lines 279–345 (stream N today), 346–476
  (N0, N1 — built; what you draw), **477–533 (your section N2)**, 534–575 (N3) and
  576–628 (N4) only to leave them room (they edit on your canvas: your `graphview`
  model and `ui_graph` page must be designed so N3 adds `Edit` requests and
  `begin_create`/`begin_delete` without a rewrite), 629–666 (N5: device nodes get
  layers later — keep the device-node builder one function), 673–763, 764–839,
  840–900.
- `docs/plans/28-node-editor.md` §3 and "Where the code is today".
- The as-built notes and decisions of D0, N0 and N1 in
  `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/{D0,N0,N1}.md` and their
  reports in `.../reports/`.
- `hyperspace/routing.py` (`Bindings`: `routes`, `macros`, `modifiers`, `owner`,
  `depth_subs`; `Router`: `patch`, `build_patch`, `feed`/the fed lanes, `lfos`),
  `hyperspace/patch.py`, `hyperspace/modifiers.py`, `hyperspace/params.py`
  (`Registry`, `Param.group`, `part_of`, `PERFORMANCE_GROUPS`/`SESSION_GROUPS`),
  `hyperspace/graph.py` (`Graph.nodes`, each node's `INPUTS`/inputs, `Effect`,
  placements if D1 has landed), `hyperspace/render.py` (`Renderer.graph` /
  `_graph_for`), `hyperspace/devices.py` (`DeviceRegistry`, `Device.sources`, port
  groups, `MidiDevice.layers`), `hyperspace/hands/device.py` (port groups),
  `hyperspace/ui.py` (`PAGES`, `Panel._page_<key>`, the panel's close/restart path,
  the param menu's Learn items), `hyperspace/ui_routing.py` (`_row`, `_sources`),
  `hyperspace/ui_fx.py` (the effect strip), `hyperspace/preset.py` (`load_doc`,
  `document`, the keys), the show file writer/reader (`library.py` / `show`),
  `hyperspace/hotreload.py`, `hyperspace/app.py` (the control window: plain imgui
  over GLFW; how the panel is created and destroyed on quit and ⌘R),
  `tests/test_ui.py` (the headless imgui harness pattern), `tests/test_hotreload.py`.
- `imgui_bundle.imgui_node_editor` (imgui-bundle 1.92.9): `Config`
  (`settings_file`), `create_editor`, `set_current_editor`, `destroy_editor`,
  `begin`/`end`, `begin_node`/`end_node`, `begin_pin(id, PinKind)`/`end_pin`,
  `link(id, from, to, color, thickness)`, `get_node_position`/`set_node_position`,
  selection and hover queries, zoom. Nothing in the package imports it yet.
  Check what the headless test harness can and cannot drive (an editor context
  needs an imgui context; if the canvas cannot draw headless, say so and test the
  model fully plus a draw-once smoke under whatever the harness allows).

Build exactly what N2's section says: `hyperspace/graphview.py` (the model; imports
`routing`, `params`, `graph`, `devices`, `patch`, `modifiers` — **no imgui**) with
`build(table, reg, router, registry_of_devices, render_graph, spec) -> View`
(`VNode`: id, kind, label, ports (`VPort`: id, name, direction, type in `value
trigger image geometry mask`, group, patched, live), `VCable`: id, src_port,
dst_port, type, live, dormant, ref); node kinds and grouping per the design's §3
(device nodes by role from the registry's open devices with their port groups,
lost devices grey; the analyzer; each LFO with knobs as input ports; modifiers;
macros as bus nodes; **params grouped by the render node that owns them** —
`shape`, each hands node, `scene`, each effect, `history`, `eye`/`camera`, each
output — the group→render-node mapping one table in `graphview`; a node per
remaining group; the render graph's own image/geometry/mask cables from
`render_graph`, placed effects among them); each param port with a `base` stub and
a `mod` stub; a route = one cable, a macro sub = a cable into `base` or `depth`;
`graphview.auto_layout(view)` giving every unplaced node a column by kind (devices
→ LFOs, modifiers, macros → render nodes → outputs, left to right).
`hyperspace/ui_graph.py` (`imgui`, `imgui_node_editor`, `graphview`):
`page(panel, dt)` on one canvas; `Config.settings_file = ""`; cables coloured by
type, a value cable's thickness following `live`; collapsed nodes show patched
ports only (per-node toggle and a page-wide "patched only"); hover shows the
reading and the depth; selection shows the ROUTING row (`ui_routing._row`) or the
effect's strip in a side column; **read-only** (no `begin_create`/`begin_delete`);
a **tidy** button. The editor context is created on first draw and destroyed in
the panel's close and on ⌘R; a hot reload of `ui_graph` must not leak a context
(hold it where the reload does not recreate it, or destroy and recreate it on
reload — decide, test, register). `ui.PAGES` gains `("graph", "GRAPH", <the
routing page's group>)` after `routing`, with `Panel._page_graph`. Layout:
`preset["layout"] = {"<node id>": [x, y]}` for preset nodes (modifiers, macros, the
params' render nodes), the show's `layout` for session nodes (devices, outputs,
LFOs); read on load, written on save, applied with `set_node_position`; a preset
without the key loads with no note and no dirt; `preset.LAYOUT_KEY = "layout"`.
Add `graphview` and `ui_graph` to `hotreload.MODULES` in import order.

Tests (`tests/test_graphview.py`, headless): at least the seven named in your
section, plus the page drawn once under the test harness asserting it draws
without error with a factory preset loaded (or, if the node editor cannot run
headless, the nearest proof and a hand-check draft saying so). Measure the page's
draw time at the control window's size (SYSTEM's panel line) in a windowed smoke
run with a factory preset and put it in the PR body (`HYPERSPACE_HOME=<scratch>`,
no `[library]`, APC40 disabled, `-ApplePersistenceIgnoreState YES`).

Decisions you take (the grouping table for params with no render node, the
`layout` map's shape and where session nodes' positions live, the tidy columns,
the context's lifetime across a hot reload, port ids' form, …) go as register-row
drafts into `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N2.md` with
hand-check drafts (Y.n) and as-built notes; report to
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/N2-report.md`.

PR: `gh pr create --base plan-28-30-integration` titled `Plan 28 N2: the GRAPH
page, both graphs drawn read-only`. Reply with the short contract from common.md.
