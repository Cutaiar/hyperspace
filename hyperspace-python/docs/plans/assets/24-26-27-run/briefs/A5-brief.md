# A5 — plan 26's docs: the render graph as built (the last docs WP of the run)

Branch `plan-26-a5-docs`. PR title:
`Plan 26 A5: docs — the render graph as built, register rows 169–N, hand checks V 191–M`.

## Where this fits
Plans 24, 26 and 27 were run together on `plan-24-26-27-integration`. Two
docs WPs have landed before you: **C7** (plan 24: register rows 110–139,
hand checks T 144–147 and U 148–167) and **B5** (plan 27: rows 140–168,
group W 168–190). You are the third and last: **plan 26**, the render
graph. The code you document is A0 (goldens, GPU timing, the naming rule),
A1 (the graph in code), A2 (one camera), A2b (the stroke-space toggle, an
owner decision taken after A2), A3 (the hands as a geometry node), A4 (the
graph in the preset as JSON, node instances) and A4b (the point-cloud
node). All are merged on the integration branch you branch from. You write
docs only: **no code, no test, no fixture, no golden changes.** If a doc
would have to claim something the code does not do, write what the code
does and list the gap in your report.

## Numbering (fixed by the orchestrator; do not renumber anything that exists)
- Register rows: yours start at **169** (`docs/DECISION-REGISTER.md`), under
  a `## The render graph (plan 26)` section, and on the answer sheet.
- Hand checks: group **V**, numbered from **191** in
  `docs/plans/11-hand-checks.md`. Group W (168–190) sits before V in the
  file: that is deliberate (B5 landed before you); the letters stay as the
  launch prompt assigned them. Append V after W.
- The code WPs' drafts are numbered `V.n` (A0–A3), `V.A2b.1`, `V.A4.n`,
  `V.A4b.n` in their decisions files; you assign the real numbers. Two
  folds the WPs asked for: **A0's V.2 is folded into A1's V.4** (one check,
  not two; A1's decisions file says why); **A2's calibration row and A3's
  16:9-fit row become one register row** (A3's decisions file says how),
  and V.11 is reworded accordingly.

## What you write (every item; the launch prompt's "What the docs WPs must produce" at `docs/plans/24-26-27-orchestrator-prompt.md` lines 1246–1323 is the authority)
1. **`docs/plans/26-render-graph.md`** (new), in the shape of
   `docs/plans/21-outputs-and-the-hands.md`: what was built by WP (A0, A1,
   A2, A2b, A3, A4, A4b), at the machine / code / tests, what no person has
   verified, known rough edges, the hand-check group and register rows
   named in the intro; the goldens (how many, which WPs moved which and
   why, the contact sheets under `docs/plans/assets/26-render-graph/`); how
   to re-record; the graph JSON's shape with one example (A4's fixture
   `tests/fixtures/presets/hands-lines.json`); the naming rule with
   instance ids; the `[[devices]]`-side of the cloud is B5's — link to
   `27-device-registry.md` rather than repeat it.
2. **`docs/DECISION-REGISTER.md`**: rows 169–N from the decisions files'
   drafts (A0, A1, A2, A2b, A3, A4, A4b), corrected against the code on the
   branch (B5 and C7 both found drafts that had drifted: check every id,
   test name, number and file path you copy). Mark superseded rows the way
   plan 25 marked 78 and 108 (row 79 "where the hands go in"; the
   `placement`/`ghost` rows whose text no longer matches; A2's "strokes
   keep their pixel weight" sentence is superseded by A2b's row — write A2's
   zoom row so the register is true today, with a note). Answer sheet rows.
3. **`docs/DECISIONS.md`**: the owner decisions 1–9, 15 and the render parts
   of 16, 22–24 from the prompt's "Decisions already made" (lines
   975–1072) as rows with Who `owner` where B5/C7 have not already written
   them (read what is there first; do not duplicate); the A2b toggle with
   Who `owner` (the owner asked for it on 2026-10-14; A2b's decisions file
   has the draft); your own as `row N`. Rows about the render stack whose
   text is now wrong (where the hands go in, the three pipelines, the 2D
   zoom, the history never holding hands) rewritten.
4. **`docs/plans/11-hand-checks.md`**: group V from 191, in the existing
   format (bold number and title; `Headless:` tests; setup; *Pass:* /
   *Fail:*). At least the prompt's list for plan 26: every factory preset
   against its golden contact sheet by eye on the Mac; the hands in the
   scene on the projector and as a clean layer on the glass at once; a hand
   passing between the shape's edges; `hands-orbit` turning only the
   shape; a saved pre-run preset with a non-zero `camera.pan` looking the
   same; the per-node times on SYSTEM while an effect is toggled; plus the
   WPs' drafts (the stroke toggle, the graph section loading, two acid
   effects, two hands layers, the cloud node drawing the recorded cloud).
   README's "numbered 1–N" line follows.
5. **`docs/TESTING-GUIDE.md`**: the same checks in plain words in Part 1
   (the render ones), each ending with its check numbers; summary/order/
   judge/glossary lines where B5 and C7 added theirs.
6. **`docs/ENGINEERING.md` §2 Rendering** (you own it): the graph, the node
   kinds and ports, evaluation in dependency order, the camera (`eye.*`,
   `camera.*` as the world transform, pan in world units and the 1080p
   reference, the calibration), the stroke-space toggle, the naming rule
   (A0 wrote it; keep and extend for A4's instances), the goldens and how
   to re-record them, the per-node timing, the graph JSON in the preset,
   the point-cloud node. Keep C7's Effects paragraph inside §2 (C7 wrote it
   for the palette). §16 Testing: the golden-frame tool.
7. **`docs/ARCHITECTURE.md` and `docs/ARCHITECTURE.html` together**: §1's
   component map gets a **Graph** row in the render stack; §2's drawing
   subsection becomes the graph's evaluation (B5 renumbered the frame
   table to 16 steps and changed two numerals in the drawing subsection —
   13 for the integrator, 5 for the dim's hand-over — keep them consistent
   with the table after your rewrite); §5's render parts; the final
   masthead and closing-stat counts **re-measured on your branch** (B5's
   method, in its report under "Measured HTML counts": modules, test
   files, effects, shapes, patterns, app lines, test lines — B5 measured
   56 / 76 / 13 / 26 / 17 / 39,835 / 45,290 before A4, A4b and A2b). SVG
   colours in CSS classes, never `var()` in presentation attributes; the
   three token blocks (light, dark media, dark attribute) in step.
8. **`docs/CHECKPOINT.md`**: stale on `main`. Rewrite "Where the code
   stands" and "What is left" to be true at the end of this run (the
   register rows 34–168 → 34–N, the hand checks 1–143 → 1–M, the plans
   list 15-… to 27-…, plans 28/29 as what is left, the owner's creative
   pass). Keep it short.
9. **The three places B5 says "nothing on screen draws the cloud yet;
   plan 26's point-cloud node, A4b, does"** (ARCHITECTURE §5, ENGINEERING
   §5, hand check 190 / register row 166, and TESTING-GUIDE L76): A4b is
   now in, so say what draws it (the `cloud` geometry node) and where its
   check lives.
10. **`docs/plans/README.md`**: your entry for `26-render-graph.md`; the
    orchestrator-prompt entry's "plans 26 and 27 follow" becomes "all
    three built"; the wishlist entry's `26-render-graph.md` and
    `27-device-registry.md` become links; the "numbered 1–N" line.
11. **`docs/plans/24-party-wishlist.md`**: only the priority paragraph's
    links (`26-render-graph.md`, `27-device-registry.md`) become real
    links to the files that now exist. Nothing else changes (it is the
    owner's record).
12. **`docs/plans/24-26-27-handoff.md`**: add one line at the top saying
    the run finished (date, the final PR) so no one re-runs it.

## Read, in this order (paths relative to `hyperspace-python/`)
1. `docs/plans/assets/24-26-27-run/briefs/common.md` (the rules; the
   "Do not edit" list does not apply to you — you are the docs WP; the
   paths at the end of this brief replace its workspace paths; use your
   own session's commit attribution).
2. The launch prompt `docs/plans/24-26-27-orchestrator-prompt.md`: lines
   81–387 (stream A: where the frame was, A0–A4), 929–1115, 1116–1176,
   1177–1245, **1246–1323 (what the docs WPs must produce)**.
3. `docs/plans/assets/24-26-27-run/decisions/A0.md`, `A1.md`, `A2.md`,
   `A2b.md`, `A3.md`, `A4.md`, `A4b.md` — the drafts; and the matching
   `reports/A*-report.md` for the gate numbers, the goldens moved and the
   concerns. `progress.md` in the same folder is the run's ledger: the
   rulings in it that concern stream A are facts to record (A3's 122
   hands frames moving for the 47.6° vs 38° reason; the docs order).
4. `docs/plans/27-device-registry.md` and `24-party-fixes.md` (B5's and
   C7's files: your file matches their shape and never contradicts them),
   and the reports `B5-report.md` §"Concerns" item 3 and `C7-report.md`
   (what each left for A5).
5. The docs you edit, as they are on the branch. Then the code: `graph.py`,
   `render.py`, `geometry.py` (the eye), `ghost.py`, `preset.py` (the
   `graph` section), `fx.py` (instances), `lookback.py`, `outputs.py`,
   `tools/golden_frames.py`, `tests/test_golden_frames.py`,
   `tests/test_graph.py`, `tests/test_hands_node.py`, `tests/test_camera.py`
   — verify every claim you write against them.

## Rules
- Docs only. `git diff --stat -- hyperspace/ tests/ tools/` must be empty.
- Never touch `~/Hyperspace` or `~/My Drive/Hyperspace`. Measuring counts
  and running `pytest --collect-only` on the test ids you cite is fine
  (from `hyperspace-python/`; tests use a scratch home).
- Every test name you cite must collect: run `uv run pytest --collect-only -q <ids>` over
  all of them once and paste the count in your report.
- No sub-agents.

## Report and decisions
Report to `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/reports/A5-report.md`
(fallback `<worktree>/.sdd/A5-report.md`): N and M (the last row and check
numbers), every file changed, the measured counts and how, what a document
says the code does not do (and what you wrote instead), the test ids
cited and their collect count, the gate lines (`uv run pytest -q`,
`uv run ruff check .` — they cannot move, but run them), the PR URL.

The PR goes into `plan-24-26-27-integration`. Reply with ONLY (under 15
lines): Status; base SHA; commits; PR URL; N and M; concerns; report path.
