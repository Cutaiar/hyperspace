# N9 — the GRAPH page organised by concern; idle macros off the canvas (plan 28)

You are the implementer of work package **N9**, from the owner's second look (2026-10-20).
Read first, in full: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your
rules; your first git commands: `git fetch origin plan-28-30-integration`, `git merge --ff-only
FETCH_HEAD` (or `git -C <worktree> merge --ff-only origin/plan-28-30-integration` if refused),
`git branch -m plan-28-n9-graph-by-concern`; one plain git command per shell call). Base
**980bdd9** (N7 merged: collapsed by default, bundles; gates: 2387 passed, 2 skipped; ruff
clean; 596 goldens match). **Exception to common.md: the docs WPs are done, so you write your
own docs (below).**

## The owner's words (2026-10-20, after N7)
> The graph looks better. The graph needs to be organized better in terms of the concerns: all
> things audio need to live in one area; all things geometry should be grouped in another area;
> all things shader should be grouped in another area. Currently, they all sit clustered
> together in some pattern that I don't really understand. Also, there are macros sitting there
> that don't connect to anything. We're getting closer, but there are still those usability
> concerns that need to be addressed.

## Investigate first (write what you find in your report before you change anything)
- `hyperspace/graphview.py`: `auto_layout`, `COLUMN` (today: sources → LFOs → modifiers →
  macros → groups → render + depth → outputs — by node KIND), `OWNERS` (param group → render
  node), the group nodes (`group:<g>`), `home` (preset vs show positions), `summary`, the
  bundles (N7), `tidy`; `hyperspace/ui_graph.py`: `_place`, the tidy chip, how saved positions
  override the auto layout, the "patched only" and expand state; N2's, N5's and N7's decisions
  (`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N2.md`, `N5.md`, `N7.md`) and the
  register rows 248–254, 270–276, 278–290 on layout, tidy, columns, placeholders.
- What is on the canvas for party-trip and for two or three other factory presets (a headless
  `graphview.build` over a scratch library): every node by kind and by the concern it belongs
  to — **audio** (the analyzer, `band.*`, `audio.*`, `tempo`, `master`, the LFOs? — decide
  whether LFOs are audio-side (tempo-synced sources) or their own "modulation" area with the
  modifiers and macros), **geometry** (`shape`, `rot`, `view`, `pattern`, `camera`/`eye`, the
  hands nodes, a cloud), **shaders** (each effect node, `history`/`dream`, the outputs), and
  **controllers** (the devices, the keys, placeholders). Which param groups today land in a
  `group:` node and where those sit. Which macros have no subscribers and no cables in the
  factory presets (count them per preset).
- `docs/plans/28-node-editor.md`'s N2/N7 sections and ENGINEERING §6 for what the layout
  promises today.

## Build
**A. Areas by concern.** `auto_layout` lays the canvas in **labelled areas**, left to right or
top to bottom (decide by what reads at 960×900; register): **controllers** (devices, keys,
placeholders) → **modulation** (LFOs, modifiers, macros) → **audio** (the analyzer, band/tempo/
master/audio group nodes) · **geometry** (shape, rot, view, pattern, camera/eye, hands, cloud)
· **shaders** (the effect nodes, history/dream, the outputs) — the owner named audio, geometry
and shaders as the three areas that must each be one place; controllers and modulation are the
sources feeding them (place them so the wires read left to right into the three). Each area has
a faint title drawn on the canvas (an `imgui` draw-list label behind the nodes or the widget's
group node if it has one — decide) and its nodes stacked inside it; a node's area comes from
one table (`AREA` by node kind / param group / render node, one place in `graphview`), with
any group that fits none going to a small "other" area. Saved positions still win over the
auto layout (N2's `layout` key, the undo marks); tidy re-lays into the areas and says so. The
wires between areas should not cross back: check party-trip's picture and say what you see.
**B. Idle macros.** A macro with no subscribers and no cable (nothing in, nothing out) is **not
drawn** by default; the modulation area gets one small "n idle macros" line (or a collapsed
"macros" node) that expands to show them so the owner can still patch one; a macro with any
connection is drawn as now; the picker's "add macro" still offers idle macros (N3). Register
the rule. Apply the same to any other node kind that sits with nothing in and nothing out
(an unpatched group node? a lost device with no rows?) — decide per kind, register.
**C. Legibility check.** Measure the draw time on party-trip at 960×900 collapsed (N7: 1.27 ms)
after your change; take a screenshot of the page in a windowed run (scratch home, APC40
disabled) and look at it yourself: three concern areas readable at a glance, wires flowing one
way, no idle macros. Put the screenshot path in the report.

## Tests (`tests/test_graph_areas.py`, headless)
`test_every_node_has_one_area_and_the_three_concerns_are_separate` (no audio node in a
geometry/shader column and so on, over every factory preset), `test_auto_layout_stacks_each_area_and_keeps_saved_positions`,
`test_tidy_relays_into_areas_and_says_so`, `test_an_idle_macro_is_not_drawn_and_a_connected_one_is`,
`test_the_idle_macros_line_expands_to_show_them_and_the_picker_still_offers_them`,
`test_area_titles_draw`, plus the page drawn once. Existing `test_graphview.py`/`test_graph_legible.py`
assertions on columns change only to the new areas (name each, never weaken). Goldens unmoved.

## Docs (yours, in the same PR)
- `docs/DECISIONS.md` "UI": the owner's decision (the canvas organised by concern — audio,
  geometry, shaders each one area; idle macros not drawn by default; Who `owner (2026-10-20)`).
- `docs/DECISION-REGISTER.md`: a `## The graph by concern (plan 28, N9)` section, rows from
  **291** (the areas and their order; where LFOs/modifiers/macros sit; the titles; the idle rule
  per kind; the "other" area), on the answer sheet; the tidy/columns rows (253, 285 and N7's) amended.
- `docs/plans/11-hand-checks.md` group **Y** from **267**: the three areas at a glance on
  party-trip; an idle macro appearing when patched and vanishing when unpatched; tidy into
  areas. `docs/TESTING-GUIDE.md` the same; `docs/plans/28-node-editor.md` an N9 section;
  `docs/ENGINEERING.md` §6; README/CHECKPOINT ranges.
- `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N9.md` and
  `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/N9-report.md` (what you found — the
  concern map of party-trip's nodes and the idle-macro counts; what you built; the screenshot;
  the draw time; every changed assertion; your final N and M).

Another WP (N8, the palette) runs in parallel on `palette.glsl`/`fx.py`/`ui_fx.py`/`preset.py`
and the register from the same next row; you touch `graphview.py`/`ui_graph.py` and the docs.
If N8 lands first, the orchestrator will tell you to renumber your rows/checks after its last
ones. Hard limits: `apc40.py`, `midi.py`, `ui_routing.py`'s desk section, `hyperspace/library/`
untouched; every edit on the canvas still through N3's `Edit`; goldens unmoved.

PR: `gh pr create --base plan-28-30-integration` titled `Plan 28 N9: the GRAPH page organised by
concern; idle macros off the canvas`. Reply with the short contract, its first line your final N
and M.
