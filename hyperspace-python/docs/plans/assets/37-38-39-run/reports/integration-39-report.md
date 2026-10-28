# Integration 39 report

**Status:** DONE_WITH_CONCERNS (minor: ruff noise in untouched files)
**Branch:** integ-39 @ 2b185ea (pushed, no PR). Base 9560027 (origin/plan-37-38-39-integration) + origin/plan-39-vision 8a56a20.

## What was done
One merge commit: `2b185ea Merge plan-39-vision into plan-37-38-39-integration: plan 39 T0–T4 (PRs #254, #252, #256, #260, #265)`.

**The conflict:** `hyperspace/preset.py`, one hunk in `GraphSection.land`. Plan 38 B3 had moved all settling into `_settle`, through `hold.keep`. Plan 39 had added `declare_mattes`, `declare_cuts` and `declare_segments` to the old inline block in `land`.
- `land` now calls only `self._settle(spec)`.
- The three declares moved into `_settle`, after `declare_resizes`. Each reads `names["matte"|"cut"|"segment"]` after `hold.keep`.
- `names()` returns `"matte"`, `"cut"` and `"segment"` both when nothing is landed (empty lists) and when a spec is (`spec.mattes`, `spec.cuts`, `spec.segments`).
- `_settle`'s no-spec dict gains the same three keys.
- Checked against each parent: the diff against 9560027 is additions only. The diff against plan-39-vision is plan 38's settling, nothing of 39's lost.

**Other lines added:**
- `hyperspace/hold.py`: `PROGRAM_IDS` gains matte, cut and segment entries (`matte_ids`, `cut_ids`, `segment_ids`).
- `hyperspace/hold.py`: `HELD_GROUPS` gains `"matte"`, `"cut"` and `"segment"`. I took this decision myself; the brief did not name it. Without it, a knob turned on a held node would move the projector. It is a draft row in the decisions file.
- `hyperspace/hotreload.py`: `"masks"` added to MODULES after `"glsl"` and before `"render"`, with a comment that `segment` stays cold (a worker module).
- `tests/test_hotreload.py`: `masks` removed from `cold`.
- `tests/test_hold.py`: four new tests:
  - a blank graph landed while held keeps the three nodes' states and params; the preview's graph has none; a save while held writes none of their ids; Take drops them;
  - a knob turned on a held node stays off the projector;
  - Drop brings the three back;
  - the kinds in `names()` (both branches) equal the keys of `PROGRAM_IDS`, and `program_only` covers the three new kinds.
- `tests/test_hold.py`, one existing test changed on purpose: `test_program_only_knows_every_kind_and_every_file_live` used `"matte"` as its example of a kind missing from `PROGRAM_IDS`. Matte is in the table now, so the example is a made-up kind, `"future"`.

## Gates
- `uv sync`: ok
- `uv run pytest -q` → `4120 passed, 2 skipped in 47.29s`
- `uv run pytest -q --all` → `4342 passed, 2 skipped in 54.23s` (nothing flaky this run, so no `-n0` re-runs)
- `uv run pytest -q --all -n0 tests/test_golden_frames.py` → `136 passed in 25.34s`; frames.json lists 789 goldens.
- Goldens against plan-39-vision: identical, no diff. Against 9560027 the only changes are plan 39's own: T1 re-recorded backdrop goldens (10968e4, 4 old PNGs gone) and new goldens added. None moved because of this merge.
- `git diff cb78963 -- tests/fixtures/frame-signatures.json`: empty.
- `uv run ruff check` on the touched files: `All checks passed!`. `ruff check .` reports 25 errors, all in files this merge did not touch: docs/plans/assets/39-vision/bench_*.py, hyperspace/media/*, tools/ingest.py, and tests/test_media_folder.py, test_sequencer.py, test_ui_desk.py, test_ui_pad.py. They are probably from the ruff version `uv sync` installed. Not fixed, since they are out of scope.

## Files changed by the resolution (beyond the clean merge)
hyperspace-python/hyperspace/preset.py, hyperspace/hold.py, hyperspace/hotreload.py, tests/test_hold.py, tests/test_hotreload.py

## Concerns
- No worker-level test of a segment under a hold, because the headless hold rig has no Renderer. The worker's survival rests on the held wiring keeping its node drawn; I read that code, I did not test it.
- The ruff errors in untouched files, above.
- Commits carry common.md's attribution, `Claude Fable 5.1`, as the brief said.

Decisions: /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/integration-39.md
