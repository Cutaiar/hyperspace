# N6 — plan 28's docs (stream N), last of the run

You are the implementer of work package **N6**, the docs of plan 28 as built, and
the closer of the shared docs for both plans. Read first, in full:
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your rules; your first
git commands: fetch `origin plan-28-30-integration`, `git reset --hard FETCH_HEAD`
or `git merge --ff-only FETCH_HEAD` from the clean tree, `git branch -m
plan-28-n6-docs`; one plain git command per shell call). Your base is the SHA in
your dispatch (every code WP and D3 merged, the review pass's fixes in). **You are
a docs WP: the "do not edit" list in common.md does not apply to you.** Edit no code;
change no test.

Then, in your worktree under `hyperspace-python/`:
- `docs/plans/28-30-orchestrator-prompt.md` lines 279–672 (stream N), 673–763
  (the decisions), 901–957 (**"What the docs WPs must produce"** — your contract,
  including the shared files "edited by whichever lands later": that is you),
  958–983 (what the report needs).
- `docs/plans/28-node-editor.md` (the design, rewritten as built in the shape of
  `docs/plans/26-render-graph.md` — read that and D3's `30-shader-nodes.md` as
  built first).
- The raw material: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N0.md`,
  `N1.md`, `N2.md`, `N3.md`, `N4.md`, `N5.md` and `.../reports/N0-report.md` …
  `N5-report.md`, plus `.../reports/review-pass-report.md` and
  `review-fixes-report.md` if present; the ledger `.../progress.md` (every ruling;
  search "Ruling", "rough edge", "review pass").
- The code as merged, to check every sentence against it: `hyperspace/patch.py`,
  `modifiers.py`, `routing.py` (`build_patch`, `modulate`, `Bindings.modifiers`),
  `params.py` (`Param.apply`'s mark), `lfo.py`, `app.py` (`frame`), `graphview.py`,
  `ui_graph.py`, `graph.py` (`Wire`, `GraphSpec.wires`, outputs as nodes),
  `preset.py` (`modifiers`, `layout`, `wires`), `devices.py`, the tests
  `test_patch.py`, `test_modifiers.py`, `test_graphview.py`, `test_graph_edit.py`,
  `test_graph_wires.py`, `test_graphview_devices.py`, `test_routing.py` (the
  equivalence test), `test_app_boundary.py` (`ORDER`).
- The docs you edit, each read in full first: `docs/DECISIONS.md`,
  `docs/DECISION-REGISTER.md` (D3's plan 30 section and its last row),
  `docs/plans/11-hand-checks.md` (D3's group X and its last check),
  `docs/TESTING-GUIDE.md`, `docs/ENGINEERING.md` (§2, §6, §9, §10, §15, §16),
  `docs/ARCHITECTURE.md` (§2 — N0's draft of the frame table and the rule; §3; §5;
  the masthead counts) **and `docs/ARCHITECTURE.html`** in step, `docs/plans/README.md`,
  `docs/plans/24-party-wishlist.md`, `docs/CHECKPOINT.md`.

**Numbering**: register rows from **{{ROW_START}}** (D3's last + 1), hand checks
group **Y** from **{{CHECK_START}}** (D3's last + 1), in N0 → N5 order.

Produce, per the prompt's contract for plan 28 and the shared files:
1. `docs/plans/28-node-editor.md` as built (N0–N5): what was built by WP, what no
   person has verified (every check Y), the rough edges (from the decisions files
   and the reviews: the delay-closing-a-loop REST behaviour, the three tools on the
   old frame shape, positions not undoable after a drag, the side pane below the
   canvas at 540 px, `route_said` per frame, …), the decisions.
2. `docs/DECISION-REGISTER.md`: a `## The node editor (plan 28)` section, rows in
   the file's format, folds named in your report; the answer sheet extended; rows
   superseded (the lag rule's rows; plan 26's "wiring choices, not a graph" rough
   edge — find the rows) marked as plan 25 marked 78 and 108.
3. `docs/DECISIONS.md`: the owner decisions of plan 28 (prompt 673–723: 6–16 as
   they apply) as rows with Who `owner`, in "The control model", "Tempo and LFOs",
   "Presets and the desk", "UI", "Process"; your own with Who `row N`; the
   one-frame-lag row rewritten to the dependency-order rule; "Decided not to build"
   loses its plan 28 line and keeps the GLSL / TouchDesigner one; the intro's
   "row N" sentence extended with plan 28's range.
4. `docs/ARCHITECTURE.md` **and `.html`**: §2's frame table (step 9 "LFOs step
   inside the patch", N0's draft finished), the lag rule replaced by the
   dependency-order rule with the delay node and the sinks' exception restated,
   the line "*modulation* is not a graph" removed, §3's control model (modifiers,
   the `mod` scheme, the patch), §5's subsystems (`patch`, `modifiers`,
   `graphview`, `ui_graph`), the masthead counts re-measured (modules, test files,
   app lines, test lines, effects, shapes, patterns — say how you measured).
5. `docs/ENGINEERING.md`: §2 (the wire list, outputs as nodes, the two new
   fixtures; D3 did the effect node), §6 The control window (the GRAPH page:
   nodes, cables, layout, tidy, editing, Learn from a port, the beside pane), §9
   Learn and routing (the patch's order, modifiers, the MODIFIERS strip, the cycle
   note), §10 Presets (`modifiers`, `layout`, `wires`), §15 hot reload (the new
   modules), §16 Testing (the headless `graphview` tests, the equivalence test).
6. `docs/plans/11-hand-checks.md`: group **Y** from {{CHECK_START}}: at least the
   lag gone on a real LFO-on-LFO patch (watch SYSTEM or the LFO page); the
   hand-energy → smooth → combine → acid-mix patch built on ROUTING then on the
   canvas, felt with a real hand; a cable dragged on the laptop screen at the
   control window's size; Learn from a port completing with the APC40 and with a
   hand; "hands as lines through the acid with tracers" by dragging, seen on the
   projector; a hands node wired to the glass alone; the APC40 as two nodes with
   the real desk, SHIFT latched and released; a patch saved on one Mac loading on
   the other through the shared library; a preset from before this run loading
   with no note. The file's intro count updated.
7. `docs/TESTING-GUIDE.md`: the same in plain words by hardware (render ones in
   Part 1, the desk ones under Part 2's APC40), each ending with its check numbers.
8. `docs/plans/README.md`: the `28-node-editor.md` entry says **built** with its
   checks and rows; the `28-30-orchestrator-prompt.md` entry final ("the launch
   prompt plans 28 and 30 were run from … both built; `assets/28-30-run/` its
   ledger, briefs, decisions and reports"); the hand-checks line's count.
   `docs/plans/24-party-wishlist.md`: the node-editor and controllers-as-nodes
   lines point here and say built; its 2026-10-16 paragraph says so.
9. `docs/CHECKPOINT.md`: "Where the code stands" and "What is left" rewritten to be
   true at the end of this run (plan 29 and the creative pass are what is left;
   the hand checks 220–M; the register rows 214–N), short.

Every claim checked against the code; where a document says something the code
does not do, fix the document and list it in your report. Gates: `uv run pytest -q`
and `uv run ruff check .` green.

Report to `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/N6-report.md`: the
rows (draft → row) and folds, the checks (Y.n → number), every doc statement
corrected, the masthead counts and how measured, your final N and M. PR:
`gh pr create --base plan-28-30-integration` titled `Plan 28 N6: the docs — the node
editor as built, register rows {{ROW_START}}–N, hand checks Y`. Reply with the short
contract, its first line your final N and M.
