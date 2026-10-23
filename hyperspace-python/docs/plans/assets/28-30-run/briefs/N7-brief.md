# N7 — a legible graph: collapsed by default, one wire per node pair, GRAPH takes the routes (plan 28)

You are the implementer of work package **N7**, added after the owner's first look at the
GRAPH page (2026-10-20). Read first, in full:
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your rules; your first git
commands: `git fetch origin plan-28-30-integration`, `git merge --ff-only FETCH_HEAD` (or
`git -C <worktree> merge --ff-only origin/plan-28-30-integration` if refused), `git branch -m
plan-28-n7-legible-graph`; one plain git command per shell call). Your base is **c4a854b**
(every WP of plans 28 and 30 merged; gates: 2373 passed, 2 skipped; ruff clean; 596 goldens
match). **Exception to common.md's "do not edit the docs" rule: the docs WPs are done, so you
write your own docs (below).**

## The owner's words (2026-10-20), verbatim where it matters
> It looks good. It's very messy. By default, we can't show every single control generator or
> automatable control in a given node. The graph is borderline illegible when we just have the
> APC40 alone. … By default, a node needs to be minimized or have maybe less than 5 visible
> lines of text in the node, and then it should be one wire. Even if you have multiple
> parameters mapped to multiple controls on a controller, what you end up seeing is one virtual
> cable for every single parameter automated. If the APC is talking to a specific shader, even
> if multiple parameters are automated, by default you should only see one line going between
> them, especially when the APC is in the minimized state, which should be the default. … The
> graph was meant to replace the routing tab. … I clicked the tidy button, and nothing
> happened. … I clicked the beside toggle, and I don't know if it did anything.

Decisions (owner, 2026-10-20; record them in DECISIONS.md with Who `owner`):
1. **Every node is collapsed by default**: a title and at most five short lines; nothing per
   port until expanded.
2. **One wire between two nodes while either end is collapsed**, however many parameters are
   mapped between them; the real cables appear when both ends are expanded.
3. **GRAPH replaces ROUTING** — scoped for this WP as **routes only, now**: the GRAPH page
   takes over the routes and the modifiers; the ROUTING page keeps its desk, macros, session
   and sinks sections untouched (the desk is Dylan's work in flight — **do not edit
   `ui_routing.py`'s desk section, `apc40.py`, `midi.py`**); a later pass retires ROUTING.

## Read, in your worktree under `hyperspace-python/`
- `docs/plans/28-node-editor.md` (as built — N2 §"The GRAPH page", N3, N5), the N2/N3/N5
  decisions and reports in `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/` and
  `.../reports/` (the `View` model, `VNode`/`VPort`/`VCable`, `collapsed`/`patched only`,
  `auto_layout`, tidy, `beside`, the `Edit` requests, the dispatch tables, the APC40's two
  nodes, the smoke report's "55 nodes, 239 cables" on party-trip).
- `hyperspace/graphview.py`, `hyperspace/ui_graph.py`, `hyperspace/ui_routing.py` (the routes
  section, `_row`, `add_route`, the MODIFIERS strip, `modifiers(panel, router)`; the desk
  section you leave alone), `hyperspace/ui.py` (`PAGES`, the page tuples), `tests/test_graphview.py`,
  `tests/test_graph_edit.py`, `tests/test_graphview_devices.py`, `tests/test_ui_routing.py`,
  `tests/test_modifiers.py`, `tests/test_hands_dance.py` (tests that drive ROUTING's functions —
  the functions stay; only the drawing of the routes section goes).
- `docs/ENGINEERING.md` §6 (the GRAPH page) and §9 (ROUTING), `docs/DECISIONS.md` "UI" and
  "The control model", `docs/DECISION-REGISTER.md` (rows 248–262 — N2/N3's rows on collapse,
  layout, tidy, beside, the side pane; the last row is 277), `docs/plans/11-hand-checks.md`
  (group Y, last check 260), `docs/TESTING-GUIDE.md`, `docs/plans/README.md`, `docs/CHECKPOINT.md`.

## Build
**A. Collapsed by default.** Every node starts collapsed. A collapsed node draws its title and
at most five lines: e.g. for a device "48 ports · 31 patched", the live reading of its loudest
patched port; for a render node its params' count and how many are patched; for a modifier its
kind and live output; for a macro its knob. No per-port rows. One pin pair per node (an `in`
and an `out` stub) carries the bundled wires. Expanding (click the title's chip, or a per-node
`+`) shows the ports as N2 drew them (with N2's "patched only" filter still available inside
the expanded view); a page-wide "expand all / collapse all" chip. The collapse state is
per-node UI state (not saved in the preset; decide whether it goes in the show's `layout` —
register it). Measure the page on party-trip at the control window's size: collapsed by default
it must read as a handful of boxes and wires, and draw faster than N2's 2.3–2.8 ms (report the
number).

**B. Bundled wires.** `graphview` gains bundles: for every pair (source node, target node) whose
cables are value/trigger cables and where either end is collapsed, one `VBundle` (id, src node,
dst node, type, count, the cables it holds, live = the max |live| of its cables, dormant if all
are). Drawn as one wire, thickness following `count` (capped), colour by type, hover listing
"<n> cables: <source port> → <param>, …" (first ten, then "+ k more"), selection selecting the
bundle and the side pane listing its rows (reuse `ui_routing._row` per row — the one table).
Render cables (image/geometry/mask) are few and stay as they are, drawn to the node's single
stub while collapsed. When both ends are expanded the bundle splits into the real cables (N3's
drag/edit paths unchanged). Editing a bundle: delete is refused in words ("expand a node to
edit its cables"); a drag onto a collapsed node's stub opens a picker of that node's ports to
land on (the `mod` stubs of its params, or its `in`/`base` ports), then goes through N3's
`Edit.connect` unchanged — so you can patch without expanding. Learn from a collapsed render
node: right-click → its params → Learn (N3's `_pin_menu` per param).

**C. Tidy and beside made legible.** Tidy always does something visible: it re-lays every node
by column (positions cleared, as now), **collapses all**, and says in the head line what it did
("laid out 55 nodes") — or "already tidy" when nothing moved. The `beside` chip is shown only
while something is selected and is labelled by what it does ("details beside" / "details
below"); on a canvas ≥ `WIDE` the pane sits beside without the chip. Register both.

**D. GRAPH takes the routes.** ROUTING's routes section (the rows list, the add-route line) and
the MODIFIERS strip are no longer drawn on ROUTING; a one-line pointer "routes and modifiers:
the GRAPH page" takes their place at the top. Their functions (`add_route`, `_row`,
`add_modifier`, `set_modifier_input`, `_sources`, `_targets`, …) stay where they are and keep
working (the canvas and the tests call them). On GRAPH: the side pane shows the selected
route's `_row` (as N2 did) and, for a selected modifier node, the MODIFIERS strip's editor for
that modifier (kind, inputs from `_sources`, params, remove, live output), so "right hand
energy, smoothed, times band 0, into acid mix" can be built from GRAPH alone (one test, the
twin of N1's ROUTING test). The referee prompt and Learn already live on the canvas (N3). ROUTING's
desk, macros, session and sinks sections are untouched — do not edit those functions or their
drawing; if the page's layout code must change to drop the two sections, keep the diff to the
section list. `ui.PAGES` keeps both pages (ROUTING is retired later).

## Tests (`tests/test_graph_legible.py`, headless, the test harness N2/N3 used)
`test_every_node_starts_collapsed_with_at_most_five_lines`,
`test_the_apc40_to_one_shader_is_one_bundle_while_collapsed`,
`test_a_bundle_splits_into_its_cables_when_both_ends_expand`,
`test_a_bundles_hover_and_side_pane_list_its_rows`,
`test_a_drag_onto_a_collapsed_node_offers_its_ports_and_lands_through_edit`,
`test_deleting_a_bundle_is_refused_in_words`,
`test_tidy_collapses_all_relays_and_says_what_it_did`,
`test_beside_shows_only_with_a_selection`,
`test_routing_no_longer_draws_routes_or_modifiers_but_their_functions_stay`,
`test_the_smoothed_energy_times_band_patch_from_graph_alone`,
plus the page drawn once per state. Existing tests: `test_graphview.py`/`test_graph_edit.py`
assertions about per-port drawing may need the node expanded first — change them by expanding,
never by weakening; `test_ui_routing.py` assertions on the routes section's drawing change to
the pointer line (name each in the PR body). Goldens unmoved (`uv run pytest
tests/test_golden_frames.py -q`, 596). Base gates: 2373 passed, 2 skipped; ruff clean.

## Docs (yours, in the same PR)
- `docs/DECISIONS.md` "UI": the three owner decisions above with Who `owner (2026-10-20)`;
  the row that says ROUTING and GRAPH are two views of one table amended ("GRAPH edits the
  routes and modifiers; ROUTING keeps the desk, macros, session and sinks until it is retired").
- `docs/DECISION-REGISTER.md`: a `## A legible graph (plan 28, N7)` section with your own
  choices as rows from **278** (what a collapsed node's five lines are; the bundle's thickness
  cap and hover; where the collapse state lives; the picker on a collapsed stub; tidy's
  words; beside's rule; …), on the answer sheet; rows 248–262 amended where superseded (N2's
  collapse = "patched ports only", the `beside` chip, tidy's behaviour) the way plan 25 marked
  78/108.
- `docs/plans/11-hand-checks.md` group **Y** from **261**: the collapsed graph on party-trip at
  the control window (legible at a glance? the APC40 one box, one wire to each shader); expand
  the APC40 and see the cables; a drag onto a collapsed node landing a route; tidy's words;
  the energy → smooth → combine → acid-mix patch from GRAPH alone with a real hand; ROUTING
  showing the pointer and its desk section unchanged with the real APC40. `docs/TESTING-GUIDE.md`
  the same in plain words with the numbers. `docs/plans/28-node-editor.md`: an N7 section
  ("What was built", rough edges, what no person has verified), the intro's rows/checks ranges.
  `docs/ENGINEERING.md` §6 (collapsed nodes, bundles, tidy, beside) and §9 (ROUTING's pointer).
  `docs/plans/README.md` and `docs/CHECKPOINT.md`: the ranges (rows 214–N, checks 220–M).
- `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N7.md` with the drafts you then
  numbered, and `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/N7-report.md` (what you
  built, the page's draw time collapsed vs expanded, the tests, every changed assertion with
  its reason, your final N and M).

PR: `gh pr create --base plan-28-30-integration` titled `Plan 28 N7: a legible graph —
collapsed by default, one wire per node pair, GRAPH takes the routes`. Reply with the short
contract, its first line your final N and M.
