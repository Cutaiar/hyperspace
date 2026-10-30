# T6 report — plan 40 docs

**Status:** DONE_WITH_CONCERNS (the concerns are about choices in the docs, listed below; there are no failures).
**Base:** e0675a6, confirmed with `git log --oneline -1` after the reset. **Branch:** `plan-40-t6`.
**PR:** https://github.com/Cutaiar/hyperspace/pull/279 (into `plan-40-build`, not merged).
**Commits:** 6dd8200 Plan 40 T6: docs (the spec as built, rows 501–536, checks 394–401), plus a follow-up commit that adds this report to `docs/plans/assets/40-run/reports/`.

## What I wrote
- **`docs/plans/40-patches.md`**
  - **Status block:** built 2026-10-28, with the PRs and the counts at e0675a6: fast 4320 passed / 2 skipped; `--all` 4551 / 2 skipped; goldens 144 (136 plus 8 grouped-twin proofs), none moved; signatures unchanged. It also gives rows 501–536 with 521/524 pending, hand checks 394–401 (AK), and the both-Macs `/8` line.
  - **Corrections, each marked "(corrected in the build)":**
    - P1's `mod:0` is now `mod:1`.
    - The `lift` and `spawn` signatures.
    - The round trip, which runs over the main run into All outputs (9 presets, 16 named).
    - The browser chip's place, and where the PRESETS fold sits.
    - P4's wait line.
    - P5's "nothing referred to the module presets", which was wrong: the strip did.
    - P2's open pins, which last the session only; the extra pins.
    - The T3 proofs about party-trip.
    - Hand checks 2 (the spawn lands folded), 3 (`scene → plasma.image`), 5 (the count is the preset's) and 8 (`.2`/`.3` only in party-noita; noita core has no K1).
    - The T6 row's "group AJ".
  - **New "What changed in the build":**
    - Tests and fixtures.
    - Hand checks and the both-Macs `/8` note, with the session prompt's "drops the key" corrected.
    - As built per task: T0, T1, T4, T5, T2, T3, the review fixes, and the plan 38 inset.
    - "`patches.py` is a leaf over the pure pieces", as the plan review asked.
    - The process rulings.
    - What no person has verified, and the known rough edges.
- **`40-patches-build.md`:** the party-trip examples and the f984d3b "is under" note are corrected.
- **`40-session-prompt.md`:** "drops the key", f984d3b and the row numbers are corrected.
- **`DECISION-REGISTER.md`**
  - Two header paragraphs and 36 answer-sheet rows.
  - A new section "Plan 40 — patches (rows 501–536)" with 36 rows in the 461–500 format.
  - 501–510 are D1–D10, answered "owner — 2026-10-27", with his words.
  - 511–536 are the rulings and drafts, merged; the merge map is in `decisions/t6.md`.
  - **521 and 524 are "pending the owner"**, each with the controller's recommendation or case stated.
- **`plans/11-hand-checks.md`**
  - Group AK, 394–401, the spec's eight with every AK draft folded in. T2's n1–n4 and fixes' f3 went to 394; T3's 5–7, T1's 4 and fixes' f2 to 395; T1's 1–3 to 397; T4's n1–n2 to 398; fixes' f1 to 399; T5's note to 400.
  - Fixes' f4, plan 38's inset, went into check 377's Headless line.
  - The header now reads 1–401, plus a line for AK.
  - The three `test_patch.py` references are now `test_modgraph.py`.
- **`TESTING-GUIDE.md`:** L189–L194 and A49–A50 (summary rows and entries), order item 24, and two glossary entries (Group, Patch).
- **`DECISIONS.md`**
  - "Presets and the desk": D3 amended (fx is excepted), plus a new "Patches and groups" run with D1–D10 in the owner's words and two rows for the doors and the wants.
  - "The WYSIWYG graph": the one sanctioned exception, with the owner's quote.
  - "Library and persistence": the patch file, `/8` and 521.
  - The palette row: a saved palette *was* an fx module preset.
- **`ARCHITECTURE.md`**
  - §1's Library row.
  - §3.6 gets a pointer to §3.11.
  - §3.7 gets two rows: spawn, and group / ungroup.
  - **§3.11 Patches and groups** is new. The brief said to put it "beside the desk templates paragraph", but §3 has no such paragraph (desk templates are one sentence in §3.6). §3.11 avoids renumbering anything.
  - §4 gets a `patches.py` row; `modgraph.py` is noted as "named `patch.py` until plan 40"; the library, preset and devices rows are updated.
- **`ARCHITECTURE.html`:** four `patch` module names are now `modgraph`, `patches` is on the Library card, and there is one paragraph on patches and groups. Plans 37–39 also kept the `.html` in step.
- **`ENGINEERING.md`**
  - §2: the palette as an fx module preset and plan 33's `module_runs` paragraph now describe the mechanism as retired.
  - §4: rows for `patches/`, `hidden.json`'s `"patches"` and `ui.json`; the `<group>` row loses fx; the rewrite table and the both-Macs bullet are updated.
  - §6: a new "Groups and patches" block, the PRESETS row, and "FX has no module strip".
  - §10: the `groups` key.
- **`SETUP.md`:** what the shared library holds (`patches/`) and what stays per Mac (`ui.json` and the rest).
- **`CHECKPOINT.md`:** a plan 40 paragraph; "What is left" gets AK and rows 501–536 (521/524 pending); the both-Macs bullet; the stale "1–276" and "rows 34–310" are updated.
- **`plans/README.md`:** the 40-patches line rewritten as built; new lines for the build plan and the session prompt; "1–328" changed to "1–401".
- **T0's leftovers (ruling 8):** `30-shader-nodes.md` now says `modgraph.py` twice. Also `33-free-graph.md` R12 gets a "retired by plan 40" note (T5 named it).
- **`docs/plans/assets/40-run/`:** refreshed from the workspace (briefs, decisions, reports, `ledger.md`, `decisions.md`, `fixes-queue.md`), plus `decisions/t6.md` and this report. `logs/` and `t4-scripts/` were left out: the dispatch lists neither.

## Tests
```
uv run pytest -q     4320 passed, 2 skipped in 51.81s
```
- **Not run:** ruff, goldens and `--all`, because no code changed.
- **Checks made:**
  - Every heading `### 501.`–`### 536.` and answer-sheet row `| 501 |`–`| 536 |` exists.
  - Checks `**394.**`–`**401.**` exist.
  - Every row number cited in the docs is within 501–536.
  - There is no TODO.
  - Every test node cited in AK was grepped against the test files.

## Files changed
22 files, all under `hyperspace-python/docs/` (+1908/−70 in 6dd8200).

## Concerns
1. **36 rows, not 25.** The overflow is 526–536, as the dispatch allows, and is said in the register, the spec and the PR. The PR title keeps the dispatch's "rows 501–525" verbatim; the body says 501–536.
2. **Process rulings are not register rows:** 1–3, 7, 8, 12, 14, 16, 19 and 21. The dispatch says "one row per controller ruling". I judged these to be no owner's choice and put them in the spec's "Process" paragraph instead. They can become rows if the controller wants.
3. **Hand checks 397 and 398 use the test fixture** `tests/fixtures/patches/acid-wash.json`, copied into the copy's `patches/`. The AK intro and TESTING-GUIDE tell the owner to comment out `[library] path` in the copy's `config.toml` first, so nothing reaches the Drive.
4. **Two counts are approximate.**
   - The "about 26 controls" in 398 and in the spec's correction comes from T4's fake-bus test on the factory table, not from a count on each party preset.
   - Check 394's row list (D2, D3, D5–D8 and the hand axes) is derived from `party-noita`'s file, not from a drawn node.
5. **Stale lines not rewritten.** Older stale lines near my edits (ARCHITECTURE's `preset.py` row "/2 or /3", ENGINEERING's "always `/6`") are left as they were; plan 40's facts are added beside them.

## Rulings
See `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t6.md`.
