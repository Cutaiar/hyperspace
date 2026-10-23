# N6 report — plan 28's docs

**Final N = 277 (register rows 233–277), M = 260 (hand checks Y 232–260).**

- Branch `plan-28-n6-docs`, base 327e646 (`git reset --hard FETCH_HEAD` worked here). Commit 31f2f1d. PR https://github.com/Cutaiar/hyperspace/pull/222 into `plan-28-30-integration`.
- Docs only: no code, test, preset or fixture touched.
- Gates: `uv run pytest -q` → `2368 passed, 2 skipped in 186.37s`; `uv run ruff check .` → `All checks passed!`. The docs give the suite as 2373 (with PR #221) or "about 2370".

## Rows: draft → number
- **N0:** patch types → 233; which params land / the mark → 234; cache key (plus the +5 µs cost) → 235; loop cut and note → 236 (*folds* "loop of modifiers alone"); delay's place + delay closing a loop → 237 (*fold*: two drafts); LFOs inside the pass (plus the three tools) → 238; the oracle's shape → 239.
- **N1:** kinds → 240; mod lane / NaN → 241; ids and removal → 242; params in the entry → 243; template's modifiers → 244; undo → 245; Learn and `mod:` → 246; the strip → 247.
- **N2:** ids → 248; OWNERS → 249; what's drawn (plus 2.78 ms and route_said) → 250; layout maps and tidy → 251; tidy columns → 252; editor context → 253; selection pane → 254.
- **N3:** into `mod` → 255; into `base` → 256; move → 257; insert → 258; picker → 259; macro onto `mod` → 260; macro node delete → 261 (now cites check 250's step 3); cable deletes → 262; N3/N4 seam → *folded* into 268.
- **N4:** wire keys → 263; wireable ports → 264; D1 as wires → 265; outputs as nodes → 266 (*folds* the through-output hands wire); refusals → 267; picker and edits → 268; fixtures' look → 269.
- **N5:** two nodes plus SHIFT refusal → 270; port groups → 271; latch → 272; shadowed row → 273; template subgraph → 274 (*folds* "an edit inside is an override"); placeholders → 275; hands groups → 276.
- **Review pass:** Important 1 → new row 277. Back-references added to 219 and 222.

### Superseded or amended
- Row 196's "wiring choices, not a graph" rough edge is superseded in part by 263 and 266, marked in its text and on the answer sheet.
- **No register row held the lag rule.** The lag lived only in DECISIONS' "Decided not to build" line, which I removed, and in ARCHITECTURE. A new owner row in DECISIONS, under "The control model", states the dependency-order rule.

### Review "Register" items
1. Older builds → row 277, plus check 259, L43 and L122.
2. `into` on a stood-down through output → row 223 rough edge and checks 223/224 Fail text, with both sentences from the coordinator, in the register and the plan 30 file.
3. `_program` twice → row 218.
4. `modulate` +5 µs → row 235.
5. ±inf through an early delay → row 237.
6. The three tools → row 238 and plan 28's rough edges.
7. `route_said` per frame → row 250 and plan 28.
8. D2's `_placed` twice → plan 30's rough edges.
9. N4's head words → fixed by #221, so they are described as fixed (rows 262/268), not as rough edges.
10. `null` reads `None` → row 221.
11. N3 housekeeping → done.
12. The test-order dependence → ENGINEERING §16.
13. The oracle → row 239.

## Hand checks: draft → number
- **N0:** Y.n1 → 232 (plus the smoke run's LFO-on-LFO patch); Y.n2 → 233; Y.n3 → 234; Y.n4 → 235.
- **N1:** Y.1+Y.2 → 236 (merged); Y.3+Y.4 → 237 (merged); Y.5 → 238; Y.6 → 239; Y.7 → 240; Y.8 → 241.
- **N2:** Y.1 → 242; Y.2 → 243; Y.3 → 244; Y.4 → 245; Y.5 → 246.
- **N3:** Y.6 → 247; Y.7 → 248; Y.8 → 249; Y.9 → 250 (adds the macro-node delete and the modifier delete).
- **N4:** Y.1 → 251; Y.2 → 252 (a variant aimed at output 1, because on 101's rig the glass is output 1); Y.3 → 253; Y.4 → 254 (outputs named for 101's rig); Y.5 → 255.
- **N5:** Y.10 → 256; Y.11 → 257; Y.12 → 258.
- **New:** 259 (a patch between two Macs; both on this build; what an older build does) and 260 (a pre-run preset loads with no note).
- **TESTING-GUIDE:** L103–L122, A34–A36, B41–B45, C8, D24, D25, each with its check number. Also updated: the summary rows, the order item 13, the branch line, the GRAPH page in the page list, "fifteen pages", L43's both-Macs sentence, two "judge" items and two glossary entries.

## Doc statements corrected (false at head)
- `ARCHITECTURE.md` "*modulation* is not a graph: the one-frame lag above stands": removed and replaced with the wires paragraph.
- ARCHITECTURE §3.9, LFO knobs "last frame's … the one-frame lag": rewritten.
- ARCHITECTURE §3.4, "in table order": now the patch's order.
- `ENGINEERING.md` "the frame's wall time unchanged": now "1.34 → 1.44 ms, about +0.1 ms". Plan 30's measured line and row 218 now carry the same figures.
- ENGINEERING §2, "the modulation graph is not evaluated this way … until plan 28": rewritten.
- ENGINEERING §2, "`cloud` is an unknown kind until plan 28": plan 28 added none.
- ENGINEERING §17, the "wiring choices, not cables" limit: rewritten.
- "fourteen pages" in three docs: now fifteen.
- 580 goldens: now 596 in DECISIONS, ARCHITECTURE, ENGINEERING, TESTING-GUIDE, hand check 2706 and the HTML.
- Check 21, "deepens a frame later": now the same frame.
- Check 164, "a relative op, plan 28": plan 28 did not build one.
- DECISIONS rows that still said "plan 28" in the future tense (two ports, layers): rewritten.

## Not fixed (code, outside a docs WP)
- `graphview.py`'s docstring says it imports routing/params/graph/patch/modifiers. It imports `learn` too. Listed as a rough edge.

## Masthead counts (ARCHITECTURE.html)
- **Old:** 56 / 41,792 / 46,985 / 80 / 26 / 13.
- **New:** 60 modules, 48,909 app lines, 52,720 test lines, 90 test files, 26 shapes, 13 effects. The footer adds 17 patterns.
- **How measured:**
  - `git ls-files hyperspace | grep -c '\.py$'`
  - `… | xargs cat | wc -l`, the same for `tests`
  - `git ls-files tests | grep -c '^tests/test_.*\.py$'`
  - `shaders/fx/*.glsl` except `_lib`
  - `geometry.SHAPES`, `patterns.MODES` via `uv run python`
- **Goldens:** 596 hashes and 140 distinct, by grep on `frames.json`.

## Notes and concerns
- `docs/plans/README.md` names `assets/28-30-run/`, as the brief worded it. **That folder does not exist yet**: the orchestrator must add it with the final PR, or the line needs changing.
- The decisions files in the workspace were edited for housekeeping (outside the repo):
  - N3.md: the `_pin_menu` / `_ctx_learn_block` line, `DELETE_NODE`, and the macro-delete Judge-it.
  - N5.md: its two fixed edges marked fixed.
- **Two places to check after #221 merges:**
  - Row 223 and checks 223/224 describe its `Graph.stood` word, which is not on 327e646.
  - The hand checks and guide take the GRAPH head's words as fixed by #221 (rows 262/268).
- The hand checks' fixture claims are taken from N4's drafts and were not run: hands-glass-1's `· hands 2 over output 1` wording, and `wire(output.2)` shown on SYSTEM.

## Fix round 1 (commit b826d56, pushed to `plan-28-n6-docs`, PR #222)

1. `docs/CHECKPOINT.md`, "Where the code stands", first paragraph:
   - Removed "`main` is at `56c7d44`" and the "PR #189 … open" clause.
   - `main` is now described as everything through plan 25 plus the fixes merged since (#197, #201, #206, among others).
   - Plans 24, 26 and 27 are on `plan-24-26-27-integration`, awaiting #195.
   - The plans 28 and 30 paragraph now says it awaits the run's final PR into `plan-24-26-27-integration`, then the owner's merge.
2. `docs/ARCHITECTURE.html` footer: now "re-measured after plan 28 on plan-28-30-integration, at 327e646". `ARCHITECTURE.md` has no masthead counts, so nothing to change there.
3. `docs/plans/11-hand-checks.md`, order item 11: check 257 moved to the "(copy) … on the laptop" list. 258 stays with the APC40.

Gates: `uv run ruff check .` → All checks passed!; `uv run pytest -q` → 2368 passed, 2 skipped. The repo has no separate docs tests.
