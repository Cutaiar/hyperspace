# Run ledger — plan 40, patches: `docs/plans/40-session-prompt.md`

Controller session: https://claude.ai/code/session_012HeFHywoiCGN2SbvC1U35W
(Fable 5.1); every task a sub-agent on Opus (`DECISIONS.md` "Process":
agents in a run work on Opus or Sonnet, never Fable). Workspace while the
run is live: `/Users/dallman/.claude/jobs/45478892/tmp/run/` (briefs/,
reports/, decisions/, logs/); copied into `docs/plans/assets/40-run/` on
`plan-40-build` as the run goes.

## Base
- 2026-10-27: `origin/plan-37-38-39-integration` @ **2b185ea** verified
  (plan 38 and plan 39 T0–T4 on it; plan 37 and plan 39 T5 not yet; no
  final PR to `main` open). `main` @ f984d3b (PR #266) was **not** under
  2b185ea, contrary to the build plan's note.
- `plan-40-build` cut from 2b185ea; first commit **f10f281** = merge of
  `origin/plan-40-patches` (the three plan 40 docs, PR #264) — which also
  carries `main` @ f984d3b, so PR #266's side pane is on the build branch
  as the build plan assumed. One conflict, `docs/plans/README.md`: both
  lines kept. Pushed.
- Gates on f10f281 (this Mac, Apple M3 Max, uv's Python 3.14): see "Log".
- Numbers: register rows 471–495; hand checks 394–401, group AK (plan 38
  ended at row 470; plan 39's AJ ends at check 393).

## Pre-flight rulings
See `decisions.md`.

## Tasks

| task | branch | base | status | tests | review | rows / checks |
|---|---|---|---|---|---|---|
| T0 the word (D1) | `plan-40-t0` | f10f281 | **merged** 51106e1 (PR #269) | fast 4122/2 skipped, goldens 136 | controller | — |
| T1 patches.py + DocKind | `plan-40-t1` | 51106e1 | dispatched | | | |
| T4 devices.wants + arrival | `plan-40-t4` | 51106e1 | dispatched | | | |
| T5 fx modules retired | `plan-40-t5` | 51106e1 | dispatched | | | |
| T2 the group node | | after T1 and main merged | waiting | | | |
| T3 save / browse / spawn | | after T2 | waiting | | | |
| review | | after T5 | waiting | | | |
| T6 docs | | last | waiting | | | 471–495 / 394–401 |

## Merges into `plan-40-build`
(counts after each.)

## Log
- **Base gates on f10f281** (2026-10-27): fast tier **4122 passed, 2
  skipped** (4121 + `test_media_render.py::test_render_thread_never_waits`,
  which failed under `-n auto` on a busy machine and passes serially:
  load-flaky, pre-existing). `uv run ruff check .` has **25 pre-existing
  errors** on the integration base (media/*.py S110/F401/I001,
  tools/ingest.py, the plan 39 bench scripts, four tests) — none in a
  file plan 40 touches; the gate for this run is ruff clean on the files a
  task touches. Goldens (`--all -m golden`): **136 passed**, none moved.
- **T0** dispatched (Opus, own worktree, branch `plan-40-t0` off f10f281).
- **T0** DONE → PR #269 (`plan-40-t0`, 3 commits: 3884d64, 2e54b4d,
  fa4da2d). 20 files; the proof grep empty; Dylan's files untouched; went
  wider than the listed symbols (`Patch`/`PatchNode`/`PatchEdge` →
  `ModGraph`/`ModNode`/`ModEdge`, `patch_cut` and privates) — accepted
  under D1 ("patch means the owner's thing and nothing else"). Sub-agent's
  gates: fast 4121 + 1 load-flaky (= base), ruff the base's 25, goldens 136,
  `--all` 4342 passed + 2 load-flaky (pass serially). Left for T6:
  `11-hand-checks.md` (3 refs to `test_patch.py`), `30-shader-nodes.md` (2
  refs to `patch.py`). Merged `--no-ff` into `plan-40-build` as **51106e1**;
  controller's fast tier: see below.
  Controller's fast tier on 51106e1: **4122 passed, 2 skipped** (29.7 s).
  Pushed. PR #269 closes by the merge.
- **T1, T4, T5** dispatched in parallel (Opus, own worktrees, branches
  `plan-40-t1` / `plan-40-t4` / `plan-40-t5` off 51106e1).
