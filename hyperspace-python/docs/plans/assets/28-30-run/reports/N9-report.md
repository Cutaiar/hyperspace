# N9 report — the GRAPH page organised by concern; idle macros off the canvas

Status: DONE_WITH_CONCERNS. Final register row **304**, hand check **274**.
Base 980bdd9 (confirmed: `git log` at 980bdd9 after reset; `merge --ff-only` was refused as diverging from the auto branch, `reset --hard origin/plan-28-30-integration` on the clean tree worked). Branch `plan-28-n9-graph-by-concern`, PR https://github.com/Cutaiar/hyperspace/pull/227.

Commits: `6e9f55e` GRAPH by concern: the canvas in titled areas, idle nodes off it (plan 28 N9); `51ba26d` Docs for N9: the graph by concern (rows 299-304, checks 272-274).

## What I found (before changing anything)
Today's layout (`COLUMN` by kind): sources 0, LFOs 1, modifiers 2, macros 3, every `group:` node 4, render nodes from 5 by depth, outputs last. The `group:` nodes mix concerns in one column: band/tempo/master/audio/scene (audio) beside preset/ui/desk/missing (app), hands/cloud (geometry), output (shaders), lfo (modulation). The analyzer sits with the devices at column 0; the eye at 5 beside the shape.

Concern map, party-trip (headless rig, party graph with acid+palette; 48 nodes, 229 cables):
- controllers: device:apc40, device:apc40/global, device:leap (grey), device:pad (grey), source:key
- audio: analyzer, group:band (88 params), group:tempo, group:master, group:audio, group:scene (band scenes)
- other: group:preset, group:ui, group:desk, group:missing (audio.play/stop/restart, no param)
- modulation: lfo.1–4, macro.1–8, group:lfo (lfo.trigger)
- geometry: render:shape (view/rot/pattern), render:ghost (Hands), render:eye (camera), render:scene, render:hands (HandsLayer), render:cover, group:hands, group:cloud
- shaders: render:capture, render:history (dream), render:acid, render:palette, render:fx, render:composite(scene+hands), its acid/palette/fx, render:output.1/2, group:output

No wire at all: macro.1–8, lfo.2–4, group:cloud = 12 of 48. Idle-macro counts over all 23 factory presets: **8 on every preset except lfo-breathe (7)**; idle LFOs 4 (party-trip 3, lfo-breathe 2); group:cloud idle everywhere. In the real app also the disabled bridge device (0 ports).
The real app's party-trip graph has a 14-effect scene pipeline (plasma … huecycle, palette, fx): N2's "13 effects make a wide canvas".

## What I built
- `graphview`: `AREA` (one table), `area_of`, `AREAS`/`ORDER`/`SHARES`, `TITLES`, `TITLE_H`, `IDLE_KINDS`, `is_idle`, `idle_words`, `idle_id`, `VNode.area`/`.idle` (set in `build`), `_columns` by area (render nodes by depth from the area's shallowest; outputs the shaders' last), `Layout` + `layout(...)` (positions, title places, idle-line places, idle ids, spans); `auto_layout` = `layout(...).nodes` (+ `idle_open`). `COLUMN` removed.
- `ui_graph`: `drawn_node`, `toggle_idle`, `st["idle_open"]`, `areas_of`, `layout_of` kept, `tidied`, `TIDIED` with areas + `TIDIED_IDLE`, `titles`/`title_size`/`_titles` (draw-list text before the nodes; editor zoom read via `ed.get_current_zoom()`, which is canvas units per pixel), `_idle_line` (an editor node `n:idle:<area>` with +/−), `_place` caches the Layout and positions idle lines, `_moved` skips undrawn nodes, `expand_all` drawn only, `head_line` "40 nodes (13 idle)".
- Order decided: controllers → audio → modulation → geometry → shaders (row 300: the analyzer is a source the modulation reads; the brief's sketch had modulation first). Left to right, not bands (row 299).
- Result on all 23 factory presets: **0 cables run back or within a column** (test asserts it).

## Legibility check
Real app, scratch home `<worktree>/.sdd/home` (APC40/pad/bridge disabled, no [library], synthetic hands tape), probe `<worktree>/.sdd/probe_n9.py` (not committed), party-trip, 960×900:
| State | Median | p90 | drawn/nodes, wires/cables |
|---|---|---|---|
| Collapsed | **1.30 ms** | 1.40 | 40/53, 59/233 |
| Framed on the four left areas | 1.36 | 1.47 | same |
| Idle line open | 1.38 | 1.45 | 51/53 |
| Tidied | 1.35 | 1.48 | 40/53 |
(N7: 1.27 ms.) Tidy said "laid out 40 nodes in 6 areas, every one collapsed · 13 idle off the canvas".

Screenshots (I looked at each): `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/n9-graph-80.png` (default 1:1: CONTROLLERS and AUDIO titles, the devices then analyzer/master/scene/audio/tempo/band, "1 lost device" line, wires left to right), `n9-graph-120.png` (zoom 4× on the four left areas: AUDIO, OTHER, GEOMETRY read; CONTROLLERS/MODULATION small; every wire runs right; no idle macros), `n9-graph-160.png` (idle line open: the 8 macros + 3 LFOs stacked under MODULATION), `n9-graph-200.png` (after tidy, whole canvas framed at 16×: a thin strip, only GEOMETRY/SHADERS titles legible).

What I see: the three concerns are each one place and the wires flow one way; at 1:1 and at 4× the areas read. **Not** readable at a glance as a whole on the 420-px page: the 14-effect shader chain makes the canvas ~23 columns wide, so tidy's framing is unreadable. Pre-existing (N2 rough edge), not fixed: wrapping the chain would make wires run back inside it.

## Tests
`tests/test_graph_areas.py` (8): the six the brief named + `test_idle_rule_per_kind` + `test_the_page_draws_with_the_areas_in_every_state`.
Changed assertions (named in the PR): `test_graphview.py::test_auto_layout_gives_every_unplaced_node_a_column` (areas, not kinds); `test_graphview.py::test_a_node_dropped_on_the_canvas_is_saved_in_its_home` (drags lfo.1: lfo.2 is idle); `test_graph_legible.py::test_tidy_collapses_all_relays_and_says_what_it_did` (`ui_graph.tidied`). None weakened.

Gates:
- `uv run pytest -q` → `2395 passed, 2 skipped in 183.91s`
- `uv run ruff check .` → `All checks passed!`
- `uv run pytest tests/test_golden_frames.py -q` → `7 passed in 19.64s` (goldens unmoved)
- `git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py hyperspace/ui_routing.py` → empty
- windowed probe run: 230 frames, clean exit.

## Docs
DECISIONS "UI" (owner row + rows 299–304 row); register section "The graph by concern (plan 28, N9)" rows 299–304 + answer sheet, rows 252/285/290 amended (the brief said 253; the columns row is 252); hand checks Y 272–274 (+ notes on 261, 264); TESTING-GUIDE L129–L131; plan 28 N9 section + intro ranges; ENGINEERING §6; plans/README and CHECKPOINT ranges (rows 214–304, checks 220–274 — the orchestrator resolves against N8's). Decisions file: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N9.md`.

## Concerns
1. The whole canvas is not legible at a glance on the narrow page with the real 14-effect chain (tidy frames to a 16× strip). Options for a follow-up: wrap the shaders chain (wires run back inside it), or let GRAPH widen CONTROLS.
2. One-column area titles (CONTROLLERS, MODULATION) are capped to a box's width, so they shrink when zoomed out.
3. Hiding idle LFOs (and group:cloud, lost devices) goes beyond "macros"; registered as row 302 for the owner to keep or overturn.
4. Commit trailers use the session's attribution (Opus 5.5, session 01MNHn1…) per the harness reminder, not common.md's Fable 5.1 lines.

## Fix round 1

Commits: `95160ad` N9 review round 1: off effects idle, the shader chain in rows of four, area chips; `ca9e880` Merge plan-28-30-integration (N8) into N9. Pushed to PR #227. Final register row **310**, hand check **276**.

What changed, by finding:
1. **Off effects idle.** `graphview.effect_off` (`fx.<effect>.on` false when the view is built, not `Effect.on(frame)`); idle when no value cable reaches any node of that effect (`build`'s `cabled` set, so a desk row on the switch keeps it). `key` holds `effect_switches(reg)`. `graphview.throughs` makes display-only `through` wires over each hidden run (no `ref`, not in `view.cables`, so `cable_near`/insert never sees them); `ui_graph.delete_through` refuses Delete in words (`THROUGH_NO_DELETE`), the hover names the skipped effects, drawn at half alpha. SHADERS' idle line ("9 off effects" in the app) opens the full chain. Row 305, check 275.
2. **Z wrap.** `_grid` wraps the shaders' depths into rows of `SHADER_ROW` = 4; each row starts under the tallest column of the one before; `graphview.returns(view, lay)` lists the row returns, the only wires the no-back-wire test excuses. App party-trip: canvas **10 columns** (was 23), shaders 4 columns × 2 rows, the whole canvas framed at **6.7×** (was 16×). Row 306, check 276.
3. **Area framing.** `_area_chips` (the five chips under the head, wrapped to the page) and `_title_click` (a background click inside a title's rect) set `st["frame_area"]`; `frame_area` selects the area's drawn nodes and its idle line, `navigate_to_selection(True)`, clears the selection. Row 307, check 276.
4. **Depth inside every area.** `_depths`: the longest path over each area's own cables (DFS in view order drops a loop's closing edge). LFO → modifier, smooth → combine, macro → LFO knob, LFO → LFO depth all run right; analyzer → band groups the same. Row 308.
5. **Titles.** `title_room` (to the next title on its row, less `TITLE_GAP`), `title_fit` (18 px on screen zoomed out, floor `TITLE_FLOOR` 12 px, then `graphview.SHORT_TITLES` CTRL/AUD/OTH/MOD/GEO/SHD). The whole canvas framed reads CTRL · AUDIO · MOD · GEOMETRY · SHADERS. Row 309.
6. **Tests.** `back_wires` uses the laid-out x and excuses only `returns`; the test runs over every factory preset on party-trip's graph **and** party-trip on the real chain (`FxState().names()`, 13 effects) wired by each graph fixture under `tests/fixtures/presets` (acid-scene, hands-glass-only, hands-lines, palette-glass, palette-hands, wired-outputs), with every idle line shut and open. New tests: `test_an_off_effect_with_no_cable_is_idle_and_a_through_wire_spans_it`, `test_the_shader_chain_wraps_in_rows_of_four`, `test_the_modulation_has_its_own_depth` (check 265's patch + a curve on LFO 1, an LFO on LFO 2's depth, a macro on LFO 3's rate), `test_the_area_chips_and_a_title_click_frame_an_area`; `test_area_titles_draw` covers `title_room`/`title_fit` (12 tests in the file).
7. **Docs.** Rows 305–310 (310 an owner question, no build: GRAPH taking the whole control window), checks 275–276, TESTING-GUIDE renumbered L131–L135 (272→L131, 273→L132, 274→L133, 275→L134, 276→L135), the range lines and run orders, README/CHECKPOINT ranges. Minors: `IDLE_NOUNS` names an off device apart from a lost one (by status); `_place` skips `set_node_position` (and `tidy` its moved count) for undrawn idle nodes; L132 and check 273 both say "7 idle macros · 3 idle LFOs"; the tidy tests compare with the literal words.

Changed existing assertions (round 1): `test_graphview.py::test_auto_layout_gives_every_unplaced_node_a_column` (lfo-breathe's acid is off with no cable, so idle: the order uses `render:fx`, and a through wire from history to fx is asserted); `test_graphview.py::test_the_page_draws_with_a_factory_preset_and_a_render_graph` (switches `fx.acid.on` on so the acid it selects is drawn; every *drawn* node placed); `test_graph_legible.py::test_tidy_collapses_all_relays_and_says_what_it_did` (the literal words; drawn nodes placed); `test_graph_edit.py::test_create_and_delete_open_only_in_the_typed_dispatch` (admits `delete_through` beside `delete_bundle`).

Draw time, real app, party-trip, 960×900 (53 nodes, 31 drawn, 22 idle: 1 off device, 8 macros, 3 LFOs, the cloud, 9 off effects; 50 wires, 233 cables): **1.42 ms** collapsed (p90 1.53), 1.71 ms whole canvas framed, 1.59 ms SHADERS framed, 1.61 ms tidied.

Screenshots (looked at each): `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/n9-r1-graph-80.png` (1:1, the area chips on the head, "1 off device" line), `n9-r1-graph-120.png` (whole canvas framed at 6.7×: titles CTRL · AUDIO · MOD · GEOMETRY · SHADERS readable, OTHER under AUDIO, shaders 4 columns in 2 rows, the wires flow right), `n9-r1-graph-160.png` (SHADERS chip at 3.1×: four boxes a row, the row return, box titles readable), `n9-r1-graph-200.png` (after tidy, as 120).

Merge of N8 (`0a09618`): conflicts only in docs. Kept both sides, N8's first: register intro (N8's clause, then N9's), the answer sheet (291–298, then 299–310), the appended sections (N8's, then N9's); TESTING-GUIDE line 34–35 (N8's L129, L130, C9–C11 with plan 30; L103–L128 and L131–L135 with plan 28), the table and the entries (L129–L130, then L131–L135), the section heading; 11-hand-checks intro line 8; README (my plan-28 line, N8's plan-30 line, the hand-checks bullet with both); CHECKPOINT ranges (rows 34–310, checks 1–276, "220–276 (N8's … 267–271, N9's … 272–276)", "214–310 (N7's 278–290, N8's 291–298, N9's 299–310)"). No N8 line dropped.

Gates after the merge:
- `uv run pytest -q` → `2423 passed, 2 skipped in 172.52s` (N8's 2411 + 12)
- `uv run ruff check .` → `All checks passed!`
- `uv run pytest tests/test_golden_frames.py -q` → `7 passed in 20.18s` (596 frames unmoved)
- the diff of `hyperspace/library/`, `apc40.py`, `midi.py`, `ui_routing.py`, `fx.py`, `ui_fx.py` against `origin/plan-28-30-integration` → empty

Remaining concerns: on the 540 px CONTROLS panel the whole canvas reads its titles, not its boxes (row 310 asks the owner); a row return crosses its row (two with two pipelines); switching an effect on re-stacks the chain; the PR body still describes the first pass (round 1 is in the commits and this report).
