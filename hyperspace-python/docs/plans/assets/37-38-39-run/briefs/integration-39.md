# Integration — plan 39 into the integration branch (with plan 38's hold)

You are the integrator merging `plan-39-vision` (T0–T4, @ **8a56a20**)
into `plan-37-38-39-integration` (plan 38 in, @ **9560027**). Read
first, in full: `/Users/dallman/.claude/jobs/9679624d/tmp/run/briefs/common.md`
(the rules; your commits end with its attribution lines).

## Dispatch
- Worktree: cut from `origin/plan-37-38-39-integration` (`git fetch
  origin plan-37-38-39-integration`, `git merge --ff-only FETCH_HEAD`
  from a clean tree if reset is refused), branch `integ-39`.
- Then `git fetch origin plan-39-vision` and `git merge --no-ff
  origin/plan-39-vision` (message: `Merge plan-39-vision into
  plan-37-38-39-integration: plan 39 T0–T4 (PRs #254, #252, #256, #260,
  #265)` + the attribution lines). One file conflicts: `hyperspace/preset.py`
  (one hunk near `GraphSection.land`/`_settle`, ~448–469).
- Push `integ-39`; do **not** open a PR; reply with the short contract.
  The orchestrator fast-forwards the integration branch to your head.
- Report → `/Users/dallman/.claude/jobs/9679624d/tmp/run/reports/integration-39-report.md`;
  decisions (rows for anything you chose) → `.../decisions/integration-39.md`.

## Read (in `hyperspace-python/`, after the merge attempt)
- `/Users/dallman/.claude/jobs/9679624d/tmp/run/reviews/38-B3-fixes-review.md`
  ("Integration notes") and `.../decisions/38-B3.md` (the exact list of
  what plan 39 must add), `.../reviews/39-T2-review.md` item 10 (hot
  reload), `.../reviews/39-T4-review.md` minor 8, `.../decisions/39-T4.md`
  (the controller notes), `.../decisions.md` rulings 12, 12b, 13.
- `hyperspace/hold.py` (`keep`, `PROGRAM_IDS`, `program_only`, `names()`
  snapshot at engage), `hyperspace/preset.py` (`GraphSection.names`,
  `_settle`, `land`, `settle`, `_values`), `hyperspace/params.py`
  (`declare_mattes`, `declare_cuts`, `declare_segments` and their
  `*_ids` helpers if any), `hyperspace/hotreload.py` (`MODULES`),
  `tests/test_hold.py`, `tests/test_hotreload.py`, `tests/test_graph_masks.py`,
  `tests/test_graph_cut.py`, `tests/test_graph_segment.py`.

## Do
1. Resolve `preset.py`: plan 39's `declare_mattes`, `declare_cuts` and
   `declare_segments` calls go **inside `_settle`**, each through
   `hold.keep(kind, names)` exactly as the switches and resizes are, not
   in `land`; `names()` gains the three kinds in **both** branches (no
   spec / spec) and `_settle`'s no-spec dict gains them; nothing else of
   either side is lost (diff each side against the result).
2. `hold.PROGRAM_IDS` gains `"matte"`, `"cut"` and `"segment"` entries
   (the ids each kind's params occupy, as the resize entry does), so
   `program_only` never raises on them and a save while held writes no
   projector-only matte/cut/segment ids.
3. Hot reload: `"masks"` before `"render"` in `hotreload.MODULES` (after
   `"glsl"`), removed from `cold` in `test_hotreload.py` (T2's note);
   `segment` stays cold (a worker module with live threads — say so in a
   comment and in the decisions file, as the dream is).
4. Tests, new, in `tests/test_hold.py`: a hold engaged with a matte, a
   cut and a segment (fake worker) in the program, then a blank graph
   landed → the program's three stay (their state and params), the
   preview sees none, Take settles to the live set, Drop lands the hold
   point; a save while held writes none of their ids; `program_only`
   covers all three kinds (iterate `PROGRAM_IDS` over every declared
   kind in `names()` — a test that the two tables agree so a future kind
   cannot slip).
5. Gates: `uv sync`; `uv run pytest -q` (expect ≈ 3990 + plan 39's 126 +
   yours); `uv run pytest -q --all` (the known load-flaky media/migrate
   tests pass serially — say which failed and re-run them with `-n0`);
   goldens `uv run pytest -q --all -n0 tests/test_golden_frames.py`
   (expect 136 jobs, 789 pictures, none moved beyond what each plan
   recorded); `git diff cb78963 -- tests/fixtures/frame-signatures.json`
   empty; `uv run ruff check` clean on the files you touched.
6. Report: the conflict and its resolution, the lines added, the counts.
