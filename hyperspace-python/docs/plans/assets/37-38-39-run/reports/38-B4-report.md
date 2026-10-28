# 38-B4 report: plan 38 docs

**Status: DONE.**

- **Branch:** `plan-38-b4-docs`, base `plan-38-hold` @ cd56b6f (confirmed with `git log --oneline -1`; `git reset --hard FETCH_HEAD` worked).
- **Commit:** 7d87c9f "Plan 38 B4: docs — rows 430–439 and 461–470, checks 377–383 (AI), ARCHITECTURE, README". Attribution is common.md's Fable 5.1 lines.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/262 (into `plan-38-hold`).

## Built (`hyperspace-python/docs/`)
- **`DECISION-REGISTER.md`:** the header sentence, the answer-sheet rows, and the "Plan 38" section.
  - Rows 430–434: D1–D5 as "(rec) — accepted by the controller 2026-10-27; the owner to keep or overturn".
  - Rows 435–439: the five rulings the brief named.
  - **Overflow rows 461–470** (460 is plan 37's, per the orchestrator's note): the chips' place, keep-on-landing (ruling 12), the `_values` filter (12b), the undo mark (I-a), the delay reset, the canvas renderer (ruling 13), the preview's switches, the preview's lifetime and hot reload, the inset on the foreground list, and the plan 39 seam.
- **`plans/11-hand-checks.md`:**
  - Group AI, checks 377–383. Every `Headless:` test name was checked against `tests/test_hold.py`.
  - Placed after AG with an AH placeholder comment.
  - The header line now names AI.
- **`ARCHITECTURE.md`:**
  - A §2 paragraph "The program and the preview: a hold" after the frame diagram.
  - `hold.py` added to §1's Host row and to the §4 table.
- **`ARCHITECTURE.html`:** the Host row and step 14 only. The page carries the frame as a step list, not this paragraph.
- **`DECISIONS.md`:** a "Hold the projector (plan 38)" table with five lines.
- **`plans/38-hold.md`:**
  - Status set to built, with counts.
  - The "reads through" table row is corrected: the hold keeps the instance.
  - B3's mechanics added to "How it works", and the "never rebuilds" claim fixed.
  - The Files list gains `preset.py` and `ui.py`.
  - Hand checks now point to group AI.
  - New "What changed in the build" section: B1, B2, B3, the plan 39 integration list, what is unverified, and the rough edges.
- **`plans/README.md`, `CHECKPOINT.md`:** plan 38 marked built, with its rows and checks.
- **`TESTING-GUIDE.md`:** entries L174–L176 (Part 1) and A48 (APC40), the summary rows, and a branch note in "Before you start".

## Tests
```
uv run pytest -q tests/test_audio_boundary.py tests/test_app_boundary.py tests/test_catalog.py tests/test_desk_coverage.py tests/test_macro_candidates.py tests/test_outputs.py tests/test_patterns.py tests/test_plan12_presets.py tests/test_routing_boundary.py tests/test_render.py tests/test_routing.py tests/test_hold.py
  754 passed, 1 skipped in 17.00s
uv run pytest -q
  3990 passed, 2 skipped in 36.53s   (= base)
```
No register or hand-check numbering test exists; I checked by grep that there are no duplicate `### N.` or `**N.**` numbers.

## Concerns
- Plan 38 used 20 rows: 430–439 plus 461–470. The ledger should record the overflow.
- The answer-sheet rows 461–470 sit directly after 439. Plan 37's and 39's docs tasks will insert theirs around them, so expect a trivial merge conflict there.
- `.run/` (scratch, untracked) is in the worktree and was not committed.

Decisions: /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/38-B4.md
