# Review — 38-B3 (plan-level review of plan 38, the hold), branch plan-38-hold @ 2f85f4f

**Task quality: Needs fixes.** The mechanism is sound and B1/B2's work is
careful, but the hold does not hold the program's effect instances,
switch picks or resizes; a preset load during a hold resets the
projector's delays; GRAPH reads the program's graph while it draws the
preview. Fixes sent to the B1 agent (branch `plan-38-b3-fixes`), with
the controller's rulings 12–13.

## Spec compliance
- D1 cut ✅; D4 preview only behind GRAPH ✅ (`preview.want()` only from
  `ui_graph._backdrop`); D5 every output ✅ (one `draw_outputs` inside
  `hold.program`).
- D2 turn shared: `rot.*` and `view.three_d` excluded, but `view.speed`
  and `view.plane.*` are in group `view` and so held (M1).
- D3: `_preset_part` filters bases to `PERFORMANCE_GROUPS`, rig left;
  routes, desk, macros, modifiers, banks, marks restored whole (B2's
  test). Edges in M4.
- Program path ✅: `Param.put` never `set`; live values, wiring and
  `rig_source` put back in `finally`; `program_value` = held norm +
  (eff − base); the preview drawn after the `with` so `mirror` copies the
  live wiring and rig; errors to `hold.error` and the head line.
- B1's rig-cable fix is right (`_HeldRig`, `rig_source` in `MIRRORED`,
  `rewired()` compares the rig; `RigWires` frozen); B2's GL test
  mutation-checked; `checkpoint`/`revert` reuse the load path so ⌘Z after
  Drop undoes a load; ordering and cost pinned by stand-in tests; the
  three controls `persist=False`, not modulatable, tested through
  MidiIO + Learn.

## Critical
**C1. A GRAPH edit or preset load during a hold strips the program's
effects, switches and resizes** — the third "reaches for a default".
Every `GraphSection.land` (preset.py ~433) calls
`fx.hold(spec.effect_names())`; `FxState._settle` deletes unnamed
instances (specs, values, phase) and undeclares their params;
`declare_switches` pops `switch_state[name]`; `declare_resizes` dels
state (plan 39's `declare_mattes`/`cuts`/`segments` follow the pattern).
`_graph_for`'s key includes `frozenset(fx.state.specs)` → the program
graph rebuilds with those nodes dormant; a dropped switch reads 0; held
values for those ids cannot be put back. Probe: TRIP held, a blank graph
landed → `fx.specs == []`. Hand check 1 fails for any look with an
effect; deleting an effect/switch node while held too; Drop re-adopts
with phase 0. Fix (ruling 12): a hold-supplied "names to keep" hook in
the land block, generic over every declare; re-settle at Take.

## Important
- **I1.** `Presets.load` → `gs.renderer.reset_delays()` (preset.py ~1047)
  on the program renderer: a load during a hold cuts the projector's
  delay/echo feedback; the preview's are never reset. Route to the
  preview while held; the program's at Take if a load happened.
- **I2.** `ui_graph.view_of`/`render_edit`/`_edit` and `ui.graph_words`/
  `dormant_lines` read `panel.renderer._graph` = the held graph while
  held: stand-in refs for nodes added during the hold, readouts about the
  projector. Plan 37 seam: C1's thumbnails are copied from the main
  renderer's `_for_the_panel` → during a hold every thumbnail shows the
  program and output 1's shows the preview. Fix: one helper in `hold`,
  "the renderer the canvas reads"; plan 37's integration routes
  `thumbs.want`/`_graph` through it.
- **I3.** Plan 39 seams: `mirror` copies no `segment_cfg`; the preview
  renderer is on no close list; a segment node in the preview would start
  a second worker; `Renderer.close` must close only its own. Ruling 13:
  the preview gets no segment workers; T4's brief carries it.

## Minor
M1 `view.speed`/`view.plane.*` into `ONE_FOR_BOTH`; M2 B1's "the program
graph never rebuilds while held" is false (the effect set is in the key);
M3 the preview drawn with `Switches()` defaults (output 1's mutes/flips
not applied); M4 Drop edges (a show opened during the hold is reverted —
rig; rig-node layout; a desk learn) → rows; M5 the raise test asserts
values only; M6 preview sub-objects not hot-reload targets, the preview
renderer kept after Take; M7 the PROJECTOR inset on the foreground list
over popups; M8 `rewired()` compares raw `_rig`; M9 attribution lines.

## Tests (22) pin
held groups, put/restore, a raise; modulation on the held base; held
wiring, hands, rig cables, the preview reading a cut; take; drop as one
step; the controls and lights; preview size; mirror; draw ordering and
the closed page; GL byte-identity for a bus cut and an effect insert.
Not pinned: C1, I1, I2, M1, the hot reload of `hold`, anything on screen.
