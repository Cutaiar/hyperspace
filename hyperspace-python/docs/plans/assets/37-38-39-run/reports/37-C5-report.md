# 37-C5 report: plan 37's docs

**Status:** DONE_WITH_CONCERNS. The concerns are the row count (fourteen rows, so row 460 was used) and the attribution line, both explained below.
**PR:** https://github.com/Cutaiar/hyperspace/pull/261 (`plan-37-c5-docs` → `plan-37-pictures`)
**Base:** 48b263e, confirmed with `git log`. I reached it with `git merge --ff-only FETCH_HEAD` from a clean tree, then renamed the branch to `plan-37-c5-docs`.
**Commit:** 9ffcd27 "Plan 37 C5: docs — rows 417–429 and 460, checks 370–376 (AH), ARCHITECTURE, DECISIONS, README, CHECKPOINT, TESTING-GUIDE"

## What was written (all under `hyperspace-python/docs/`)
- **`DECISION-REGISTER.md`**
  - A header sentence on 417–429 and 460.
  - Fourteen answer-sheet lines after 416.
  - A "Plan 37" section after row 416, in the format of rows 396–416:
    - 417 is D1, **open**. It states the two questions for the owner: renumber or tombstones, and the `preset.py` edit.
    - 418–421 are D2–D5, each "(rec) — accepted by the controller 2026-10-27".
    - 422–429 are the rulings: thumb size and downsample; drop and dim; the mapping table; the 16:9 box; cost; hover; tint and switch; the area rule (decision 11).
    - 460 covers the sheets, the nearest-kept ranking and the generated map.
- **`plans/11-hand-checks.md`**
  - Group AH, checks 370–376, after AG and before "What no test covers". Each check has its `Headless:` line.
  - A sentence in the header's coverage line, and a "What no test covers" bullet.
- **`ARCHITECTURE.md`**
  - A "Nodes as pictures (plan 37)" paragraph after the GRAPH page paragraph.
  - Additions to the `outputs.py`, `render.py` and `graphview`/`ui_graph` module rows.
- **`ARCHITECTURE.html`**: one phrase on the UI line. It has no GRAPH paragraph to update.
- **`DECISIONS.md`**: a "Nodes as pictures (plan 37)" table covering the thumbnail rule, D2, D3, D5, the pending list (D1) and D4 after. Also a line in the Who list.
- **`plans/37-pictures-and-faces.md`**
  - Status changed to built (P1, P3; P2 a dry run) on `plan-37-pictures`, 2026-10-27, with the PRs, counts and asset links.
  - The D table gains an answer/row column, and the hand checks are now 370–376.
  - A "What changed in the build" section: as built, the differences from the spec (1–8), P2's steps for when the list arrives, what is not verified, the rough edges and the follow-ups (rulings 10, 13).
- **`plans/README.md`**: plan 37's line.
- **`CHECKPOINT.md`**: plan 37's paragraph, and a "What is left" bullet for the owner's list and AH.
- **`TESTING-GUIDE.md`**: order item 21; table rows L174–L178; a "Plan 37" section with L174–L178 in plain words, citing 370–376; and a "judge" bullet.

## Tests
- Docs tests: none exist (`grep -rl "DECISION-REGISTER\|11-hand-checks" tests/` is empty).
- `uv run pytest -q`: `4035 passed, 2 skipped in 42.53s`, the same as the base.

## Concerns
1. **Fourteen rows for thirteen slots.** As the brief allows, the last row is 460. Plan 39's docs task should start at 440 and must not take 460.
2. **Attribution.** The commit says "Claude Opus 5.5", the model that ran this task. common.md's lines say "Claude Fable 5.1". Amend the commit if the run's records must match.
3. **Stale lines left alone.** CHECKPOINT's general lines (rows 34–310, checks 1–276) predate plan 37 and were already out of date. I left them.
4. **Integration conflicts to expect.** When plan 38's B4 and plan 39's T6 land their own sections in the same docs, register and hand-check files will need ordering at the integration merge. AH sits after AG, and AI and AJ go after it.

## Files
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-ab57e16e277c01761/hyperspace-python/docs/ (the nine files above)
- Decisions: /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/37-C5.md
- PR body (uncommitted): /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-ab57e16e277c01761/.run/37-C5-pr-body.md
