# Run ledger — plans 37, 38 and 39: `docs/plans/37-38-39-orchestrator-prompt.md`

Orchestrator session: https://claude.ai/code/session_012HeFJ3coaFYJ9durdEgBjC
(Fable 5.1); every task a sub-agent on Opus 5.5 (the owner's word for
this run; `DECISIONS.md` "Process": agents in a run work on Opus or
Sonnet). Workspace while the run is live:
`/Users/dallman/.claude/jobs/9679624d/tmp/run/` (briefs/, reports/,
decisions/, logs/); copied into `docs/plans/assets/37-38-39-run/` on the
integration branch as the run goes.

## Base
- 2026-10-27: `main` @ f2351a0 (#247 after plan 36's #245/#246), verified.
  PR #248 (`worktree-vision-spike`, docs only: the three plans, the spike,
  the run prompt) was **open, not merged**, so the integration branch
  `plan-37-38-39-integration` was cut from `main` and `worktree-vision-spike`
  merged into it (`--no-ff`): **cb78963**, pushed. The spike branch already
  contained `main`, so the merge is the eight doc files and nothing else.
- Gates on cb78963 (this Mac, Apple M3 Max, uv's Python 3.14): fast tier
  **3958 passed, 2 skipped** (57 s); full suite `--all` **4170 passed, 2
  skipped** — two media tests (`test_media_channels.py::test_rapid_switching_with_slow_closes_stays_fast_and_balances`,
  `test_media_core.py::test_bad_file_is_an_error`) failed under `-n auto`
  and pass serially: load-flaky, pre-existing, not the run's; goldens
  **757** (24 factory presets, 23 fixtures in the manifest).
- Plan branches cut from cb78963 and pushed: `plan-37-pictures`,
  `plan-39-vision`. `plan-38-hold` is made by B1 (the cherry-pick of
  `output-hold` @ 3959f57 onto cb78963).
- Numbers (the prompt's): 37 → rows 417–429, checks 370–376 (AH); 38 →
  430–439, 377–383 (AI); 39 → 440–459, 384–393 (AJ). Code tasks draft
  `4xx` / `AH.n`–`AJ.n`; each plan's docs task numbers them.

## Pre-flight rulings
See `decisions.md`.

## Tasks

| task | branch | base | status | tests | review | rows / checks |
|---|---|---|---|---|---|---|
| 39-T0 edges.glsl | `plan-39-t0-edges` | cb78963 | dispatched | | | |
| 39-T1 alpha honest | `plan-39-t1-alpha` | cb78963 | dispatched | | | |
| 39-T2 mask wire + matte | `plan-39-t2-matte` | cb78963 | dispatched | | | |
| 39-T3 cut | | after T2 | waiting | | | |
| 39-T4 segment + worker | | after T3 | waiting | | | |
| 39-T5 GRAPH + pages | | after T4 | waiting | | | |
| 39-T6 docs | | last | waiting | | | 440–459 / 384–393 |
| 38-B1 rebase | `plan-38-hold` | cb78963 | dispatched | | | |
| 38-B2 hand-check readiness | | after B1 | waiting | | | |
| 38-B3 review | | after B2 | waiting | | | |
| 38-B4 docs | | after B3 | waiting | | | 430–439 / 377–383 |
| 37-C1 thumbnails | `plan-37-c1-thumbnails` | cb78963 | dispatched | | | |
| 37-C2 hover + head switch | | after C1 | waiting | | | |
| 37-C3 backward wire | `plan-37-c3-backward-wire` | cb78963 | dispatched | | | |
| 37-C4 faces (dry run) | `plan-37-c4-faces-sheets` | cb78963 | dispatched | | | waits for the owner's list |
| 37-C5 review + docs | | after C1–C3 | waiting | | | 417–429 / 370–376 |

## Merges into the integration branch
(38 → 39 → 37; counts after each.)
