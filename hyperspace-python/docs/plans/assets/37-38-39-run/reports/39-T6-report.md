# 39-T6 report — plan 39 docs

**Status:** DONE_WITH_CONCERNS (numbering seams with plans 37 and 38 for the integrator)
**PR:** https://github.com/Cutaiar/hyperspace/pull/268 (`plan-39-t6-docs` → `plan-39-vision`)
**Base:** 505739f, confirmed with `git log --oneline -1` after `git reset --hard FETCH_HEAD`, which was accepted. The branch was renamed to `plan-39-t6-docs`, and `uv sync` was run.
**Commit:** b18b10e Plan 39 T6: docs — rows 440–459 and 471–497, checks 384–393 (AJ), ARCHITECTURE, DECISIONS, README. It carries common.md's attribution lines (Fable 5.1), as the dispatch asked.
**Decisions file:** /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/39-T6.md

## What was written (`hyperspace-python/docs/`)
- **DECISION-REGISTER.md**:
  - the header sentence;
  - 47 answer-sheet rows;
  - the section "Plan 39 — vision (rows 440–459, 471–497)".
  - Rows 440–447 are the owner's D1–D8, each with what was built.
  - Rows 448–459 and 471–497 are the rulings from T0–T5, the reviews and integration rulings 12–14.
  - The overflow is 27 rows, from 471.
- **plans/11-hand-checks.md**:
  - group AJ, 384–393: the spec's ten in order, each with `Headless:`, steps, and *Pass:*/*Fail:* lines that cite the register row a failure points to;
  - the header line;
  - a placeholder comment for AH and AI.
  - 384 takes T5's canvas steps and the integration's hold check.
  - 389 takes the purple cable and the `masks.py` hot reload.
  - 388 takes T3's AJ.5b.
- **ARCHITECTURE.md**:
  - §1: the Render stack, Graph, Media (the CPU-frame shortcut) and Host rows, with their boundaries and tests.
  - The near-leaves (`masks`).
  - §2: a MASK row in the frame diagram, and the port-types paragraph: the owner's meaning of a mask and the one-way promotion.
  - §2: a new paragraph, "Masks and vision", covering matte, cut, segment, the input path, orientation, laid-over-ness, the window's cut-through and the hold.
  - The golden count is now 789.
  - §4: the `masks.py` and `segment.py` rows, plus new names on the `graph.py` and `render.py` rows, and the hot-reload row.
  - §5: the `segment-<name>` thread row, a "Vision" paragraph, and hot reload.
- **ARCHITECTURE.html**: the render-stack modules, the Graph card, a new "Masks & vision" card, 789 goldens, and the boundaries paragraph.
- **DECISIONS.md**: "Masks are their own wire (plan 39)", with both owner sentences verbatim, D1–D8 one line each and a row for the hold seams. The T1 blend rule is the last row of "Render and outputs".
- **plans/39-vision.md**:
  - the status is now built, with the counts;
  - the hand-checks heading now points at 384–393;
  - a new "What changed in the build" section, in plan 36's shape, covers:
    - tests and counts; the hand checks; both Macs and `uv sync`;
    - every departure: the mask-port refit; `MaskPicture` with no own_size; fg/bg at the frame's size; Vision's resample; the flip flag; the eight goldens; the signature rule for wired fixtures; segment-motion's two stills; the integration lines;
    - the out-of-table edits, the media-test flakes, what no person has verified (what T5 left for the machine), and the rough edges.
- **plans/README.md**: plan 39 is built; the spike's line says "now plan 39".
- **CHECKPOINT.md**: plan 39's paragraph, including "both Macs on this build before a preset with segment/matte/cut is shared". AJ and rows 440–497 are listed under what is left.
- **TESTING-GUIDE.md**:
  - order item 21;
  - the live tier note, covering the two real-model tests and how to run them;
  - summary rows and entries L182–L188, in plain words (the camera, a dancer, the party light, two cameras, unplugging, the cut-through), citing 384–393.
- **SETUP.md**: `uv sync` picks up `pyobjc-framework-vision`; the camera permission; the torch fallback's weights line, mirroring the dream's; a `[segment]` example.

## How I checked it
- Every `test_…` name cited in the new checks and rows was grepped in `tests/`. The only misses are module names and the four `test_hold.py` tests. Those four exist on `origin/plan-37-38-39-integration`; I checked with `git show FETCH_HEAD:…/test_hold.py`.
- Code names (`MaskPasses` methods, `SegmentWorker` methods, `[segment] device`'s "auto" default, `SEGMENT_PINS`, `mask_of`/`mask_port`, `Renderer.segmenter`'s lazy import) were read in the source.
- Gates:
  - No docs tests exist.
  - `uv run pytest -q` → `1 failed, 4104 passed, 2 skipped in 95.23s`. The failure is `test_analyzer.py::test_strip_order_does_not_change_the_math` (an EOFError under xdist load). `uv run pytest -q -n0 tests/test_analyzer.py` → `34 passed, 1 deselected`. The diff is docs only.

## Files changed
- hyperspace-python/docs/DECISION-REGISTER.md
- hyperspace-python/docs/plans/11-hand-checks.md
- hyperspace-python/docs/ARCHITECTURE.md
- hyperspace-python/docs/ARCHITECTURE.html
- hyperspace-python/docs/DECISIONS.md
- hyperspace-python/docs/plans/39-vision.md
- hyperspace-python/docs/plans/README.md
- hyperspace-python/docs/CHECKPOINT.md
- hyperspace-python/docs/TESTING-GUIDE.md
- hyperspace-python/docs/SETUP.md

The helper scripts and drafts are in `<worktree>/.run/t6/` (not committed).

## Concerns
1. **Overflow.** There are 27 rows past 459 (471–497), more than twenty. Several drafts were merged to keep the count down; the decisions file has the map.
2. **TESTING-GUIDE numbering collides with the other plans.** Plans 37 and 38 both took L174+, so I used L182–L188 and order item 21. Item 21 may collide with plan 37's. The integrator orders them.
3. **Some lines describe the integration branch.** Rows 459, 495 and 496, 384's hold step and ARCHITECTURE's hot-reload words describe 2b185ea's lines (HELD_GROUPS, PROGRAM_IDS, `_settle`, `masks` hot), not `plan-39-vision`'s. Each says "at the integration merge". On this branch `masks` is still cold.
4. **The answer-sheet rows and the new section are appended right after plan 36's.** Plans 37 and 38 rows (417–439, 460–470) are slotted in by the integrator.
