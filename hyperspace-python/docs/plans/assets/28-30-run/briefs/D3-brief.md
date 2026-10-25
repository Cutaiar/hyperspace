# D3 — plan 30's docs (stream D)

You are the implementer of work package **D3**, the docs of plan 30 as built. Read
first, in full: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your
rules; your first git commands: fetch `origin plan-28-30-integration`, `git reset
--hard FETCH_HEAD` or `git merge --ff-only FETCH_HEAD` from the clean tree, `git
branch -m plan-30-d3-docs`; one plain git command per shell call). Your base is the
SHA in your dispatch (D0, D1, D2 merged). **You are a docs WP: the "do not edit"
list in common.md does not apply to you — these files are yours to write.** Edit no
code; change no test.

Then, in your worktree under `hyperspace-python/`:
- `docs/plans/28-30-orchestrator-prompt.md` lines 81–278 (stream D), 673–763
  (the decisions), 901–957 (**"What the docs WPs must produce"** — your contract),
  958–983 (what the report needs from you).
- `docs/plans/30-shader-nodes.md` (the design, which you rewrite as built, in the
  shape of `docs/plans/26-render-graph.md` — read that file first for the shape:
  intro with the hand-check group and register rows, "What was built" by WP, "What
  no person has verified", "Known rough edges", the decisions).
- The raw material: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/D0.md`,
  `D1.md`, `D2.md` (register-row drafts `2xx`, hand-check drafts `X.n`, as-built
  notes, departures) and `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/D0-report.md`,
  `D1-report.md`, `D2-report.md` (what was built, measured numbers, fix rounds). The
  ledger `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/progress.md` has every ruling
  (search "Ruling").
- The code as merged, to check every sentence you write against it: `hyperspace/graph.py`
  (`Effect`, `Fx`, `VALUE`, `EffectAt`, `placed_chips`, `placement_words`,
  `default_graph`), `hyperspace/fx.py` (`run_one`), `hyperspace/ui_fx.py`,
  `hyperspace/render.py`, `tests/test_graph_effects.py`, `tests/test_graph_placement.py`,
  `tests/fixtures/presets/{palette-hands,palette-glass,acid-scene}.json`,
  `tests/golden/frames/frames.json` (580 hashes: 556 base + 24 D1).
- The docs you edit, each read in full first: `docs/DECISIONS.md`,
  `docs/DECISION-REGISTER.md` (the answer sheet at the top, the row format of rows
  196–213, the last row 213), `docs/plans/11-hand-checks.md` (the last check 219;
  the group format, e.g. group V), `docs/TESTING-GUIDE.md`, `docs/ENGINEERING.md` §2
  Rendering, `docs/ARCHITECTURE.md` §2 "Drawing" and §5, `docs/ARCHITECTURE.html`
  (the same content as a diagrammed page — keep it in step with the .md),
  `docs/plans/README.md`, `docs/plans/24-party-wishlist.md`, `docs/CHECKPOINT.md`.

**Numbering**: register rows from **214** upward, in D0 → D1 → D2 order; hand checks
group **X** from **220** upward. N6 (plan 28's docs) comes after you and continues
from your last numbers — put your final N (rows) and M (checks) in your report's
first line.

Produce, per the prompt's "What the docs WPs must produce" for plan 30:
1. `docs/plans/30-shader-nodes.md` rewritten as built (D0–D2), in `26-render-graph.md`'s
   shape; the "Not built" line gone; what no person has verified (every hand
   check X); the rough edges (the per-effect SYSTEM lines indicative on a tile GPU
   and the end node's `fx` line 0.00; the pool's `avoid` rule; a half-float
   Handoff texture on a presenter unverified at the machine; the faces target an
   inner chain; `_program` built twice a frame; the two vocabularies; …).
2. `docs/DECISION-REGISTER.md`: a `## Shader nodes (plan 30)` section with your
   rows 214–N, each in the file's format (title; **Built**; **Other options**; **To
   reverse**; **Rough edge**; **Judge it**), folded where two drafts say one thing
   (say which drafts folded into which row in your report); the answer sheet
   extended. Rows superseded by this plan (plan 26's `Fx` node row 177 "one FX node
   per pipeline over the one chain" and whatever else the drafts name) marked the
   way plan 25 marked 78 and 108 — read how.
3. `docs/DECISIONS.md`: the five owner decisions of plan 30 (prompt lines 673–723,
   numbers 1–5 and 16 as they apply) as rows with Who `owner` in "Render and
   outputs" / "Effects and the look-back"; your own choices with Who `row N`; the
   `Fx`-node row rewritten (the `Effect` node, the end node); the intro's "row N"
   sentence extended ("rows 214–N in plan 30 on 2026-10-17").
4. `docs/ARCHITECTURE.md` §2's drawing subsection (the effect nodes, the pipeline
   end, placement, the `VALUE` type), the Graph row in §1 if it names `Fx`, §5's
   render parts; **and `ARCHITECTURE.html`** to match. Leave §2's frame table and
   the lag rule to N6 (N0 drafted them).
5. `docs/ENGINEERING.md` §2 Rendering: the effect node, the chain as a run,
   placement (`after`/`into`, the vocabulary, refusals, dormancy), the presenter
   path, the goldens (580; the three fixtures), SYSTEM's per-effect lines, the FX
   page's placed chips.
6. `docs/plans/11-hand-checks.md`: group **X** (plan 30) from 220: at least the three
   placements on the real projector and glass (through a presenter — the half-float
   Handoff), two palettes with different centres on two outputs, the FX page's
   placed chip, the faces target still bending the faces, the SYSTEM lines per
   effect; each in the existing format with `Headless:` naming the tests behind it.
7. `docs/TESTING-GUIDE.md`: the same checks in plain words, by hardware (the render
   ones in Part 1), each ending with its check numbers.
8. `docs/plans/README.md`: the `30-shader-nodes.md` entry says **built**; the
   `28-30-orchestrator-prompt.md` entry becomes "the launch prompt plans 28 and 30
   were run from" (plan 28 "being built" until N6 lands — N6 finishes it); the
   hand-checks line's count.
   `docs/plans/24-party-wishlist.md`: the palette / shader-node line points here and
   says built.
9. `docs/CHECKPOINT.md`: only the plan 30 parts of "Where the code stands" (N6
   rewrites it whole afterwards): keep it short.

Every claim checked against the code; where a document says something the code
does not do, fix the document and list it in your report. Nothing under
`hyperspace/library/`, no test, no code changes. Gates: `uv run pytest -q` (docs
tests, e.g. hand-check numbering, may exist) and `uv run ruff check .` green.

Report to `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/D3-report.md`: the
rows you numbered (draft → row), the folds, the checks you numbered (X.n → number),
every doc statement you corrected, your final N and M. PR:
`gh pr create --base plan-28-30-integration` titled `Plan 30 D3: the docs — shader
nodes as built, register rows 214–N, hand checks X`. Reply with the short contract.
