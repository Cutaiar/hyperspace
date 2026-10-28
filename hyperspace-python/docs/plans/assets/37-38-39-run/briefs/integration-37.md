# Integration — plan 37 into the integration branch (with plans 38 and 39)

You are the integrator merging `plan-37-pictures` (C1–C5, @ **d2ffa7c**)
into `plan-37-38-39-integration` (plans 38 and 39 in, @ **2b185ea**).
Read first, in full: `/Users/dallman/.claude/jobs/9679624d/tmp/run/briefs/common.md`
(the rules; your commits end with its attribution lines).

## Dispatch
- Worktree: cut from `origin/plan-37-38-39-integration` (`git fetch
  origin plan-37-38-39-integration`, `git merge --ff-only FETCH_HEAD`
  from a clean tree if reset is refused), branch `integ-37`.
- **First** `git fetch origin plan-39-vision` and `git merge --no-ff
  origin/plan-39-vision` (@ **2a57af6**: T5's graphview work and T6's
  docs on top of what is already in; message `Merge plan-39-vision into
  plan-37-38-39-integration: plan 39 T5–T6 (PRs #267, #268)` + the
  attribution lines). Expected conflicts: the docs that B4 also wrote
  (register rows after 416, hand-check groups, README, CHECKPOINT,
  DECISIONS, ARCHITECTURE, TESTING-GUIDE) — keep both sides, in numeric
  order; `graphview.py` should merge clean. Run the fast tier once.
- **Then** `git fetch origin plan-37-pictures` and `git merge --no-ff
  origin/plan-37-pictures` (message: `Merge plan-37-pictures into
  plan-37-38-39-integration: plan 37 C1–C5 (PRs #250, #253, #255, #258,
  #261)` + the attribution lines). Expected conflicts: `hyperspace/ui_graph.py`
  (plan 38's head chips / HELD line / backdrop-forced-on / PROJECTOR
  inset vs C1's `_canvas` want list and `_node` thumbnail draw and C2's
  one `_tint_chip` line), and the docs the three docs tasks all touched
  (`DECISION-REGISTER.md` rows after 416, `11-hand-checks.md` groups
  AH/AI/AJ, `README.md`, `CHECKPOINT.md`, `DECISIONS.md`, `ARCHITECTURE.md`,
  `TESTING-GUIDE.md`). Possibly `graphview.py` (plan 39's table entries vs
  C1's `THUMBS`/`summary`/`VNode` and C3's `laid_areas`) and `outputs.py`.
- Push `integ-37`; no PR; reply with the short contract. The orchestrator
  fast-forwards the integration branch to your head.
- Report → `/Users/dallman/.claude/jobs/9679624d/tmp/run/reports/integration-37-report.md`;
  decisions → `.../decisions/integration-37.md`.

## Read (after the merge attempt)
- `/Users/dallman/.claude/jobs/9679624d/tmp/run/reviews/38-B3-review.md`
  (I2 and the plan 37 seam), `.../reviews/38-B3-fixes-review.md`
  ("Integration notes": `st["thumbs"] = panel.renderer.thumbs` and the
  timing line must read through `hold.canvas_renderer`; the preview
  renderer then has its own `PreviewTextures`), `.../decisions/38-B3.md`,
  `.../reviews/37-C1-review.md`, `.../reviews/37-C2-review.md`,
  `.../decisions.md` ruling 13.
- `hyperspace/hold.py` (`canvas_renderer`, `mirror`, `MIRRORED`,
  `preview_renderer`), `hyperspace/ui_graph.py` (both sides' `_head`,
  `_canvas`, `_node`, `_backdrop`, `_monitor`, the hover), `hyperspace/outputs.py`
  (`Preview`, `PreviewTextures`), `hyperspace/render.py` (`_thumbnails`,
  `_thumbs()`, `thumb_source`, `_for_the_panel`), `tests/test_hold.py`,
  `tests/test_thumbnails.py`, `tests/test_graph_hover.py`.

## Do
1. Resolve `ui_graph.py` so that: the head reads **hold chips first**
   (plan 38), then plan 36's chips, then C2's `_tint_chip(st)` last; the
   HELD line, the backdrop-forced-on and the PROJECTOR inset are plan
   38's as merged; `_canvas` wants the thumbnails (C1) and `_node` draws
   them (C1/C2's hover); nothing of either side lost (diff each side
   against the result).
2. **Thumbnails during a hold** (B3's I2 / the plan 37 seam): the ids the
   page wants and the textures it draws come from **the renderer the
   canvas reads** — `hold.canvas_renderer(panel)` (the preview while held
   and drawn, else the main renderer): route `st["thumbs"] = …` and the
   timing/GPU-time read through it; the preview renderer makes its own
   `PreviewTextures` lazily (check `_thumbs()` does; `MIRRORED` must not
   share the main one's), and the hue read follows the same renderer.
   Output 1's thumbnail while held stays the **program's** picture (the
   PROJECTOR is what output 1 shows) — say so in a comment and a row.
   Tests: while held with the page drawn, the wanted ids go to the
   preview's `PreviewTextures` and the main renderer copies none; after
   Take/Drop they go back to the main one; a hold with the page closed
   makes no thumbnail at all.
3. Docs: the register rows in numeric order (417–429, 430–439, 440–459,
   460, 461–470, then plan 39's overflow if any), the hand-check groups in
   order AH (370–376), AI (377–383), AJ (384–393), one header line
   naming all three; README's three plan lines; CHECKPOINT's three
   paragraphs merged into one coherent "Where the code stands" (the
   three plans on `plan-37-38-39-integration`, the one final PR) and one
   "What is left" (the owner's list for P2; AH/AI/AJ; the register rows);
   DECISIONS' three tables; ARCHITECTURE's paragraphs each kept.
4. Gates: `uv sync`; `uv run pytest -q`; `uv run pytest -q --all` (the
   known load-flaky tests pass serially — say which); goldens `--all -n0
   tests/test_golden_frames.py` (expect plan 39's job count, 789
   pictures, none moved beyond what each plan recorded); the signature
   fixture unchanged against cb78963 except plan 39's additions (there
   are none — the wired-fixture rule); ruff on touched files. Report
   the counts.

## Docs numbering to reconcile (from the three docs tasks' reports)
- Register rows: plan 37 **417–429 + 460**; plan 38 **430–439 + 461–470**;
  plan 39 **440–459 + 471–497**. Order them numerically in one file; the
  header paragraph gets one sentence covering 417–497 (which plan took
  which). Rows 459, 495, 496 (plan 39) describe integration-only lines
  (`HELD_GROUPS`, `PROGRAM_IDS`, `_settle`, `masks` hot) — they are true
  on the integration branch; drop their "at the integration merge" hedge.
- Hand checks: AH 370–376 (plan 37), AI 377–383 (plan 38), AJ 384–393
  (plan 39), in that order after AG; each docs task left placeholder
  comments for the others — remove them; one header line names all three.
- TESTING-GUIDE: plans 37 and 38 both took L174 up; plan 39 used L182–188;
  renumber so the L-lines are unique and in order; the order items too.
- README: three plan lines + the prompt's line; CHECKPOINT one coherent
  "Where the code stands" and "What is left"; DECISIONS three tables;
  ARCHITECTURE every paragraph kept (the hold's, the GRAPH page's, the
  port types / node table / thread table / boundaries).
