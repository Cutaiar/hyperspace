# 39-T1 report: alpha is honest (BLOCKED, two test-fixture goldens moved)

**Status: BLOCKED.** The fix is built and its test passes, but 8 golden frames of two test fixtures moved. Per the brief I did not re-record them and did not open a PR. The orchestrator decides.

## Base
- Worktree reset to `origin/plan-39-vision` @ cb78963. Branch `plan-39-t1-alpha`, pushed. No PR (see Blocked).

## What was built
1. **The test:** `tests/test_media_render.py::test_a_half_transparent_scene_over_white_is_honest_on_an_opaque_window`.
   - It lives in this file because the composite/media harness (`_renderer`, `_draw`, `Still`) is here.
   - Setup: the scene's translucent faces (lines and points off) go into `composite.over` over a white still on `channel.a` in `composite.under`. The window is opaque (`bg_alpha` 1). The test draws with cut-through off, then on, and reads back both the scene texture and the output.
   - It asserts:
     - (a) The scene and the output are equal between the two draws (≤1 level).
     - (b) The output equals `face + 255·(1 − face.a)` within 3 levels everywhere a face is partly there, and at the frame's centre.
   - On cb78963 it **failed** (scene alpha off by 39/255 with cut-through on), as the spike predicted.
2. **The fix:** `render.draw_scene` now decides the cut-through blend on the window's `bg_alpha < 1`, not on the local `bg_alpha = self._scene_ground()`. The clear still uses the scene ground. The change is one condition plus a `# plan 39 T1` comment.
3. The two existing cut-through tests are in `tests/test_lookback.py`, not `test_render.py` as the brief said. Both are untouched and green.

## Commits
- 392056f Plan 39 T1: test — a translucent scene laid over white is honest on an opaque window
- 57f48b4 Plan 39 T1: the cut-through blend is the window's, not a laid-over ground's

## Gates
- `uv run pytest -q`: **3959 passed, 2 skipped** in 63.58s. That is the base 3958 plus the new test. The goldens are not in the fast tier.
- `uv run ruff check .`: 25 errors, all already on cb78963 and none in my files: `docs/plans/assets/39-vision/bench_*.py` from the spike, plus `media/*`, `tools/ingest.py` and a few tests. `uv run ruff check hyperspace/render.py tests/test_media_render.py` → All checks passed!
- `uv run pytest -q tests/test_golden_frames.py`: without `--all` → "no tests ran". With `--all`: **4 failed, 124 passed**. On cb78963 without my render.py change: 128 passed.
- `uv run pytest -q --all`: not run, because the goldens gate already fails.

## Blocked: goldens that moved
- Frames:
  - `backdrop-still|present|{scene, scene+through, scene+hands, scene+hands+through}`
  - `media-chain-backdrop|present|` the same four states
- Failing tests: `test_every_golden_frame_is_drawn_byte_for_byte[...|present]` and `test_every_preset_resaved_as_seven_draws_its_goldens[...]` for each fixture.
- Both are **test fixtures** (`tests/fixtures/presets/`), not factory presets. No factory preset golden moved.
- Cause: the spike only considered a composite's `over`. A scene laid over the **backdrop** (`graph._Build.laid_over`, `backdrop.scene`, plan 32 R) uses the same zero ground, and these fixtures draw translucent faces over the backdrop.
- Contact sheets (columns: golden | now | |diff|×4): `/Users/dallman/.claude/jobs/9679624d/tmp/run/reports/39-T1-golden-diffs/golden-diff-backdrop-still.png` and `…/golden-diff-media-chain-backdrop.png`.
  - The golden shows the faces washed toward white over the backdrop. In media-chain-backdrop the box of faces reads as a near-white rectangle brighter than the grey under it.
  - "Now" shows the faces at their own opacity over it.
  - The new frames are the honest ones. This is the "brightening" AJ.10 is about.
- Options for the orchestrator:
  - (1) Re-record these two fixtures' goldens with the reason in the commit, and re-pin the goldens digest if the test needs it.
  - (2) Narrow the fix to the composite path only. That keeps two rules for one ground and leaves the backdrop scene dishonest.
  - Recommendation: (1).

## Files changed
- `hyperspace-python/hyperspace/render.py` (the blend choice in `draw_scene` only)
- `hyperspace-python/tests/test_media_render.py` (one new test)

## Self-review
- Overlay mode is unchanged: there the window's `bg_alpha` < 1, so a scene with a zero ground in overlay still cuts, as before.
- `getattr(self, "bg_alpha", 1.0)` mirrors the existing pattern in render.py.
- In the test, `face` is read from the scene texture with cut-through off. After the fix both reads are equal, which assertion (a) checks.

## Decisions file
`/Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/39-T1.md`: register row 4xx, hand check AJ.10, as-built notes.

## Fix report: orchestrator decision 9 (re-record), DONE

- Ran `HYPERSPACE_HOME=<scratch> uv run python tools/golden_frames.py --record --only backdrop-still,media-chain-backdrop`.
  - 4 distinct PNGs replaced 4 (each one is shared by 2 states), so 8 entries in all.
  - The recorder also rewrote the `route`/`hands_over` labels on four `+through` entries, including `hands+through`, whose hash did not move. That is drift unrelated to T1, so I dropped it: `frames.json` was rebuilt from HEAD with only the 8 sha256/png pairs swapped (16 lines).
- `test_renaming_moved_no_golden` needed `GOLDENS_DIGEST` re-pinned. It is now `ac516263…`, with a comment in the precedent's style. This is in the same commit.
- Commit: 10968e4 Plan 39 T1: re-record the eight backdrop goldens the honest blend moves
- Gates:
  - `uv run pytest -q`: 3959 passed, 2 skipped
  - `uv run ruff check hyperspace/render.py tests/test_media_render.py tests/test_golden_frames.py`: All checks passed!
  - `uv run pytest -q tests/test_golden_frames.py --all`: 128 passed
  - `uv run pytest -q --all`: 7 failed, 4164 passed, 2 skipped (-n auto, machine loaded).
    - `--lf -n0`: 5 passed, 2 failed (`test_media_publish::test_ndi_out_never_blocks`, a timing bound of 0.068 against 0.05; `test_dream::test_end_to_end_offscreen`).
    - Those two run alone: 2 passed. They are load-sensitive and not related to T1.
- PR: https://github.com/Cutaiar/hyperspace/pull/252 (into plan-39-vision)
- The decisions file is updated: the row says the eight goldens were re-recorded and why, and the as-built notes have the line.

## Fix report 2: review minors (approved), DONE
- render.py: the blend comment now names the backdrop case (`backdrop.scene`, plan 32 R) beside the composite's `over`. Comment only. Commit e5bcf74, pushed to PR #252.
- decisions/39-T1.md:
  - The register row's "Rough edge" now says that in overlay mode with cut-through on, a laid-over scene's alpha is still squared (as the spec asks), and that `cut`/`matte` inherit this.
  - AJ.10's second pass now wires `scene → backdrop.scene` explicitly.
- Checks:
  - `uv run pytest -q tests/test_media_render.py tests/test_lookback.py -n0`: 104 passed, 2 deselected.
  - `uv run ruff check hyperspace/render.py`: All checks passed!
- Attribution: the commit uses the session's line (Claude Opus 5.5), as the earlier T1 commits do, not common.md's "Fable 5.1".
