# 37-C3 report: the backward wire

**Status:** DONE_WITH_CONCERNS (the concern is a deliberate departure from the dispatch's tie-break, below)
**Branch:** `plan-37-c3-backward-wire`, base cb78963 (verified with `git log --oneline -1`)
**PR:** https://github.com/Cutaiar/hyperspace/pull/253, into `plan-37-pictures`
**Commit:** 7847a60, "Plan 37 C3: an effect is laid where its consumers are, so no cable runs back across areas"

## What I built
- `hyperspace/graphview.py`:
  - `area_column`: an area's place left to right on the canvas.
  - `laid_areas(view)`: applied in `build` right after `area_of`, before `_columns`.
  - `kept(c, b)`: factored out of `returns`, with no change in behaviour.
- The rule: an EFFECTS-area frame node (an effect, copy, composite or resize) whose consumers sit left of the effects is laid in the leftmost consumer area that is not left of what feeds it. Kept wires (into a look-back's or delay's `image`, or an old D1 `after`) do not count as consumers.
- How it is computed: two passes, each run to a fixed point. The first finds the leftmost area each node may sit in, given what feeds it. The second gives each node the leftmost of its consumers' areas, taking consumers as already laid, so a chain moves as a whole.
- `tests/test_graph_areas.py`:
  - `test_no_cable_runs_backwards_across_areas`, parametrised over 25 factory presets and 22 graph fixtures, each loaded as the preset. Only the loops by design in `graphview.returns` are exempt.
  - `test_a_node_is_laid_where_its_consumers_are`, which covers:
    - acid-scene's acid.2 moves to LOOK-BACK, left of the look-back.
    - A saved position wins.
    - An effect fed by nothing that feeds the faces moves to SCENE.
    - A chain of two into the look-back's occluder moves to LOOK-BACK whole.
    - An effect fed by the look-back and kept into it stays in EFFECTS.
  - N9's sweep is tightened: its acid-scene exemption is removed.

## What failed before, exactly
- Only `fixture:acid-scene` failed: `wire:acid.2>lookback/occluder` ran from EFFECTS back into LOOK-BACK.
- `echo-faces`' `lookback → shape.faces` also runs backwards, but it is the taken-back return by design, so it is exempt.

## Departures from the dispatch (decide)
1. **Tie-break.** The dispatch says "a node with consumers in several areas keeps today's area". acid.2's consumers are the look-back (`image`, `occluder`) and `composite.under` (EFFECTS), so that tie-break would leave the wire in place. I built "the leftmost consumer area" instead. For a node with one consumer area it gives the same answer as D5. To reverse it, restrict `laid_areas` to nodes whose consumers share one area.
2. **The preset.** There is no factory `acid-scene`. It exists only as the test fixture `tests/fixtures/presets/acid-scene.json` (`/2`, migrated on load). The effect feeds the look-back, not `shape.faces`. It has no saved positions, so step 3 does not apply. No preset edited.
3. **Saved positions.** "Only for nodes with no saved position" holds for *positions*: `build` names the area, and `layout` skips every placed node. A placed effect's *area* (which chip frames it) does follow the rule.
4. **No layout runs by itself.** The test that guards this is `test_graph_areas.py::test_auto_layout_stacks_each_area_and_keeps_saved_positions`. It is green.

## Gates (from `hyperspace-python/`)
- `uv run pytest -q`: `1 failed, 4005 passed, 2 skipped in 217.01s`. The failure is `test_media_render.py::test_render_thread_never_waits`, a timing test; load average was 217. It passes serially (`1 passed in 4.24s`). 4006 = 3958 + 48 new.
- `uv run ruff check hyperspace/graphview.py tests/test_graph_areas.py`: `All checks passed!` The whole tree, `ruff check .`, reports `Found 25 errors.` All are in files I did not touch (the 39-vision benches, `hyperspace/media/*`, `tools/ingest.py`, three tests), so they are not C3's.
- `uv run pytest -q --all tests/test_golden_frames.py`: `128 passed in 47.53s`. No golden moved, none recorded.
- `uv run pytest -q --all`: `4 failed, 4214 passed, 2 skipped in 201.97s`. The failures were `test_dream::test_end_to_end_offscreen`, `test_media_channels::test_rapid_switching_with_slow_closes_stays_fast_and_balances` and `test_migrate_library::test_the_real_picture_check_passes_an_old_preset` (4 failures from 3 names), all at load average about 225. `pytest --all -n0 --lf` gives `4 passed in 21.57s`. 4218 = 4170 + 48.

## Files changed
- `hyperspace-python/hyperspace/graphview.py`
- `hyperspace-python/tests/test_graph_areas.py`

## Self-review
- `laid_areas` maps a move into OTHER back to AUDIO, through the column index. Unreachable in practice, since effects never feed OTHER.
- Both passes are capped at len(free)+1 iterations.
- A moved effect is not wrapped in the effects' rows of four.

## Decisions file
`/Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/37-C3.md`: row 4xx-a, hand check AH.7, as-built notes.

## Fix report (review minors)
- Commit c38df60, pushed to PR #253.
- Changes:
  1. `laid_areas` docstring: a kept cable is not counted as a consumer, but it still counts in `makers` as a feed that bounds the taker.
  2. A comment on the two caps: for a chain without a loop, both passes settle before the cap; a hit cap leaves the result partial.
  3. Decisions file, row 4xx-a: the rule reduces to D5 only when the consumer area is left of EFFECTS, and an effect whose consumers are all to its right never moves. AH.7 gains step 5 for the saved-position chip/frame rough edge.
- Tests and lint:
  - `uv run pytest -q tests/test_graph_areas.py tests/test_graphview.py -n0`: 97 passed, 1 deselected.
  - `uv run ruff check hyperspace/graphview.py`: All checks passed!
