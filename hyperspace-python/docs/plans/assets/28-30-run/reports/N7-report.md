# N7 report — a legible graph

**Final register row N = 290, final hand check M = 266.** PR #225: https://github.com/Cutaiar/hyperspace/pull/225. Branch `plan-28-n7-legible-graph`, based on c4a854b. `git merge --ff-only` was refused because the branch had diverged: the auto-branch was cut from `origin/main`, 419c292. No work was on it, so I ran `git reset --hard origin/plan-28-30-integration`. The base is confirmed as c4a854b.

## Commits
- a3cefe3 GRAPH: every node collapsed by default, one wire per node pair, the routes and modifiers on GRAPH
- ac495ad GRAPH: a collapsed node reads only what its lines show; the wiring and the columns kept while nothing moves them
- fd64796 GRAPH: the + clear of a node's out stub; an expanded node's chip line counted in its column
- 541511f Docs: plan 28 N7 — the owner's three decisions, register rows 278-290, hand checks 261-266

## What I built
### A. Collapsed by default
- `graphview.summary` gives each node at most five lines, the same count every frame.
- Every node has `nin:` / `nout:` stub pins.
- `ui_graph` keeps the expanded set in `st["open"]`. It is the same set N5's template open used, so `is_open` and `toggle_open` are unchanged.
- New functions: `collapsed`, `full` (N2's "patched only" inside an expanded node, with the per-node **all ports / patched only** chip) and `expand_all`. The head has an **expand all / collapse all** chip.
- `graphview.height(collapsed=)` and `auto_layout(collapsed=)` stack collapsed nodes at the height of their lines.

### B. Bundles
- `graphview.VBundle` and `wiring` fold every value and trigger cable that has a collapsed end into one bundle per (source node, target node) pair. `readings` refreshes them.
- Render cables stay single and are re-ended on a collapsed node's stub.
- `bundle_tip` gives the first ten cables, then "+ k more".
- `ui_graph._bundle` sets thickness to 2.5 + 0.6 per cable, capped at 7 px.
- Selecting a bundle puts its routes in the side pane through `route_rows`, using ROUTING's `_row`.
- `delete_bundle` refuses with "expand a node to edit its cables". The bundle's menu offers "expand both ends".
- Stub drags: `_stub_drag`, `open_land`, `land` and `_land_menu`, with `graphview.land_choices`. The landing goes through `Edit.connect` (or `Edit.wire` for render ports), unchanged.
- The node menu offers **learn ▸** for each param, through N3's `_pin_menu`.

### C. Tidy and the details chip
- `ui_graph.tidy` collapses every node, then calls `forget`, re-lays out and frames the canvas (`navigate_to_content`). It sets `said` to "laid out N nodes, every one collapsed" or "already tidy".
- `beside_chip` decides the chip: it shows only with a selection on a page narrower than WIDE, labelled "details beside" or "details below".

### D. GRAPH takes the routes
- `ui_routing.page` now has a pointer line, `POINTER`, which opens GRAPH when clicked. The filter field stays.
- The routes child and the MODIFIERS call are gone from the page. `found` no longer counts routes or modifiers, and `_find_w` no longer reserves room for "+ route".
- `modifier_block`, with a stacked option, is factored out of `modifiers`. The side pane uses it for a selected modifier.
- `ctx_item` now opens GRAPH.
- Desk, macros, session and sinks: not edited.

### Performance
- `refresh(collapsed=)` skips the unpatched input ports of collapsed nodes.
- The wiring and the auto layout are cached on the page state.
- `View.node` uses a dict index.

## Draw time
The real app ran on party-trip at 960×900, with the smoke patch from probe_N (an LFO on another LFO's depth, two modifiers and a route), 80 draws per state.

| State | Median | p90 | Wires / cables |
|---|---|---|---|
| Collapsed | **1.27 ms** | 1.40 | 64 / 238 |
| All expanded, patched only | 2.66 ms | 2.82 | 238 / 238 |
| Tidied | 1.29 ms | — | — |
| N2 | 2.32–2.78 ms | — | — |

Before the caches, the collapsed page drew in 2.18 ms. The probe is `<worktree>/.sdd/probe_n7.py` and is not committed. Screenshots `graph-80.png` and `graph-160.png` are in the same folder.

## Tests
`tests/test_graph_legible.py` has 11 tests: the ten the brief named plus `test_the_page_draws_in_every_state`.

Changed assertions, each with its reason:
- **test_graphview**, page test: the nodes are expanded before a route is selected.
- **test_graph_edit**:
  - The one-table test: ROUTING draws no rows or strip now. The row is drawn by GRAPH's side pane.
  - The dispatch AST test: `_stub_drag` and `delete_bundle` are added to the allowed handlers.
- **test_ui_routing**, row-widget tests: these now draw the rows through `ui_graph.route_rows`, using a `rows()` helper.
  - Ghost bar.
  - Scale chips: the ghost count is split 1 + 1.
  - Conflicting ids: checked in two frames.
  - One-page test: the pointer, then the rows.
  - The session mark.
  - Undo for the route ×.
  - Feel line.
  - Sources built once per draw.
- **test_ui_routing**, filter tests: the counts no longer include routes or modifiers.
  - Filtered page: 3 of N. The filtered-route × part is removed, and the swirl preview is gone.
  - UI state: 4 becomes 2.
  - Line in use: no "+ route", and the pointer replaces the counts.
  - "Route a lane here": now opens GRAPH.
- **test_ui_shell** scroll test: it now measures at the end of the child (sinks), with `_row` never called.
- **test_modifiers** strip test: renamed. It draws `modifiers()` on its own, and ROUTING's pointer comes before DESK.

## Gates (last lines)
```
2384 passed, 2 skipped in 169.04s
ruff: All checks passed!
golden frames: 7 passed in 19.45s (596 match)
windowed gate run (scratch .sdd/home, APC40 enabled=false, no [library]): exit 0, stall.log 0 bytes
git diff --stat base -- library/ apc40.py midi.py: empty
```

## Files
- **Code:** `hyperspace/graphview.py`, `ui_graph.py`, `ui_routing.py`.
- **Tests:** `tests/test_graph_legible.py` (new); `test_graphview.py`, `test_graph_edit.py`, `test_ui_routing.py`, `test_ui_shell.py`, `test_modifiers.py` (changed).
- **Docs:** `DECISIONS.md`, `DECISION-REGISTER.md`, `ENGINEERING.md`, `TESTING-GUIDE.md`, `CHECKPOINT.md`, `plans/11-hand-checks.md`, `plans/28-node-editor.md`, `plans/README.md`.
- **Decisions:** `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N7.md`.

## Self-review / concerns
- **The APC40 is still two boxes collapsed.** This follows owner decision 12. The hand check says "the APC40 one box"; what the owner will see is *apc40* plus *apc40 (SHIFT)*, each with one wire to each node it maps into.
- **The older hand checks 232–260 say "on ROUTING add a route".** I added a note at the head of group Y and of the guide's node-editor section saying to do those steps on GRAPH. Each check was not rewritten.
- **"+ route" is gone.** New routes come from a canvas drag, a Learn, or "Route a lane here…".
- **The stub drop has never been exercised with a real mouse.** No test can drag on the widget. The tests monkeypatch `new_link` / `accept_new_item` as N4's did.
- **The `ui_routing` diff touches the shared page and filter code.** That is `page`, `found`, `_find_w` and a `dummy` that ends the filter's line, which "+ route" used to consume; without it the child was clipped on the second frame. None of the desk, macros, session or sinks functions was edited.
- **Commit trailers.** They use this session's attribution (Opus 5.5, session 01MNHn…), as the system reminder specified, not common.md's Fable line.

## Fix round 1 (review of PR #225, head 541511f → c1da145)

Commits: c4d1aee (code + tests), c1da145 (docs).

- **I1 stub-to-stub (check 265):** `graphview.stub_pin` — a node's `nout:` stub with exactly one output pin (modifier, LFO, macro) stands for that pin; `_create` resolves both ends through it before the stub dispatch, so a collapsed modifier's out dropped on another collapsed node's in opens that node's picker. `test_the_smoothed_energy_times_band_patch_from_graph_alone` now does all four hops of check 265 through the page's drop path (`drop()` monkeypatching the widget's create query, as N4's test does) with every node collapsed, then `land()`; a two-stub drop with no single output (`nout:analyzer`) is still refused with `BOTH_STUBS`.
- **I2 older checks:** rewritten GRAPH-first — 232, 233, 234, 236, 237, 238, 239, 241 (test id fixed to `…_draws_its_blocks_and_routing_points_to_graph`), 242, 243, 245, 247, 249, 260; TESTING-GUIDE L103–L105, L107, L109–L111, L113, L117, L121, B41 (Keep wording), B42–B44, the node-editor intro and the glossary.
- **I3:** row 247 marked superseded in part (rows 288, 289) on the answer sheet and in its body.
- **I4 reveal:** `ctx_item` sets `ui_routing._state(panel)["reveal"] = b`; `_canvas` (after the wires are drawn) calls `ui_graph.reveal`: selects the wire the route is in (its bundle or its own cable), `navigate_to_selection`, `st["focus"] = b`; the bundle pane lists the focused row first; another selection clears the focus. Test `test_route_a_lane_here_selects_the_new_route_on_graph`.
- **Minors:** `BUNDLE_STEP` 0.5 (cap reached at ten); picker label "<port> · <stub>"; check 263 uses the hover count; "one to four lines"; the APC40 fan-out (19 bundles: apc40 14, SHIFT 5) in check 261 / L123 and row 280; stale docstrings (`ui_routing` filter paragraph, `_find_field`, `_land_menu`); the pointer under a filter said in row 288 and ENGINEERING §9; README's plan 28 entry; row 282 (a preset load keeps the set); setter bundles' text lines in row 281 and check 262 / L124. New tests `test_a_dormant_bundle_draws_faint_and_a_live_one_moves_without_a_rebuild`, `test_a_bundles_menu_and_a_nodes_learn_menu_draw`.

Commands and output:
```
uv run pytest tests/test_graph_legible.py tests/test_graphview.py tests/test_graph_edit.py tests/test_ui_routing.py tests/test_modifiers.py -q   109 passed in 5.69s
uv run ruff check .                            All checks passed!
uv run pytest -q                               2387 passed, 2 skipped in 169.31s
uv run pytest tests/test_golden_frames.py -q   7 passed (596 frames)
```
Final N = 290, M = 266 (unchanged).
