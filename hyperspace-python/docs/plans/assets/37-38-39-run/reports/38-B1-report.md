# 38-B1 report: rebase plan 38's hold onto the integration branch

**Status: DONE_WITH_CONCERNS.** The concerns are two full-suite failures that this branch did not cause; details below.

- **Branch:** `plan-38-hold`, base `plan-37-38-39-integration` @ cb78963 (confirmed with `git log --oneline -1` after the reset).
- **Draft PR:** https://github.com/Cutaiar/hyperspace/pull/251 (into `plan-37-38-39-integration`).
- **Worktree:** /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a6bd5c2cdfec59dc3

## Commits
- `e4d3af4` "Plan 38: hold the projector while the next look is built": the cherry-pick of 3959f57. The owner's message is kept and my attribution lines are appended below the existing trailers.
- `3e89e0a` "Plan 38 B1: hold the rig's bus cables too, on plan 36's explicit graph".
- `397b7ba` "Plan 38 B1: the hold's tooltips wrap like the head's, imports sorted".

## What was built
1. **Conflicts.**
   - `ui_graph.py`: only the import line conflicted. The result is plan 36's `pinch`/`ui_pad` line plus `from . import hold as holdmod`. Everything else in the head merged cleanly. `_hold_chips` is first in `_head`, before collapse/expand, patched only, tidy, preset only and output behind. The red `HELD` line sits under `_area_chips`. `_backdrop` is forced on while held, and `_monitor` draws the inset.
   - `README.md`: both lines are kept, with plan 38's directly after plan 36's.
2. **The proof found a real gap.** Plan 36 feeds windows through the rig's bus cables (`graph.RigWires` via `Renderer.rig_source`, part of `_graph_for`'s key). The first cut held only `wiring`, so on the rebased branch a bus cable cut during a hold reached the projector. Separately, `mirror` did not pass `rig_source`, so the preview renderer drew every bus cable standing (a filled-in default). The fix is in `hold.py`:
   - `Hold.rig` is captured at engage.
   - `program` swaps in a `_HeldRig` stand-in for `rig_source` and restores the live one after.
   - `rewired()` also compares the rig.
   - `MIRRORED` gains `rig_source`.
   - `hold.py` still imports no graph: the rig is read duck-typed, the way `graph.rig_of` reads it.
3. **New tests in `tests/test_hold.py`** (19 now):
   - `test_a_bus_cable_cut_after_the_hold_stays_off_the_projector`
   - `test_drop_puts_a_bus_cable_cut_during_the_hold_back`
   - `test_on_gl_a_bus_cable_cut_after_the_hold_stays_off_the_projector`, which runs on GL with `@pytest.mark.empty_frame` so the app's own empty-frame Renderer is used. It shows the program frame is byte-identical with the same graph object, the preview is black with `pr._graph.rig == show.rig`, and after Take the outputs are black.
   - The mirror test now covers `rig_source`.
   - The fixture's stand-in renderer is now plan 36's (`G.EMPTY`, `rig_source = lib.project`).
   - `fx.warp.amount` is changed to `fx.mix`: plan 36 declares an effect's params only when wired.

   The three rig tests fail on the unfixed `hold.py` (checked).
4. **Nothing in `hold.py` constructs a `Wiring()` or reaches for a default wire.** Checked by reading it, and pinned by the empty-frame GL test.
5. **Spec:** `38-hold.md` gains a "Rebased onto plan 36" paragraph, and program step 1 now mentions the rig cables.

## Tests (from `hyperspace-python/`)
```
uv run pytest -q tests/test_hold.py                      19 passed in 5.26s
uv run pytest -q                                         3977 passed, 2 skipped in 111.17s   (base 3958 + 19)
uv run ruff check <the 6 touched .py files>              All checks passed!
uv run ruff check .                                      Found 25 errors.   (all already on the base, none in touched files)
uv run pytest -q --all tests/test_golden_frames.py       128 passed in 53.31s   (757 pictures, none moved, none recorded)
uv run pytest -q --all                                   2 failed, 4187 passed, 2 skipped in 177.68s
```
The two `--all` failures:
- `test_app_boundary.py::test_the_app_exits_within_two_seconds_with_reads_and_a_transcode_stuck` passes serially (`-n 0`). It is load-flaky.
- `test_dream.py::test_end_to_end_offscreen` fails serially too (`worker.drain(10.0)` times out), and it fails identically with the base's files put back in the working tree. So it is failing on cb78963 on this Mac right now, probably torch/MPS under load from other agents. Dream, render and lookback are untouched.
- Counted against the base's 4170 + 19 = 4189: 4187 passed + these 2 = 4189. Consistent.

**Headless smoke** (`.run/smoke.py`, HYPERSPACE_HOME=/tmp/h38smoke/home, scratch, no library): hold → bright 0.3 + bus cut. The program read bright 2.0 with no cut while live showed 0.3 with the cut; `changed=['view.bright']`, `rewired=True`. Take let go. Hold → 0.9 + rejoin → drop gave back 0.3 with the cut. Undo of the drop gave back 0.9 with no cut.

## Files changed (vs cb78963)
- `hyperspace-python/hyperspace/hold.py` (new, plus the B1 fix)
- `hyperspace-python/hyperspace/app.py`
- `hyperspace-python/hyperspace/ui_graph.py`
- `hyperspace-python/hyperspace/undo.py`
- `hyperspace-python/hyperspace/hotreload.py`
- `hyperspace-python/tests/test_hold.py`
- `hyperspace-python/docs/plans/38-hold.md`
- `hyperspace-python/docs/plans/README.md`

Nothing outside the cherry-pick's files.

## Self-review
- In `program`, `r.rig_source` is restored in `finally` unconditionally. On a renderer with no attribute it ends up as `None`, which `rig_of` reads the same as before.
- The program's graph cache is not thrashed: its key stays the held wiring and held rig throughout the hold. The GL test asserts `r._graph is graph`.
- Drop reverting a bus cut comes from the undo mark (plan 36 T1 put the rig in the show's mark). It is consistent with "the projector never moved", and pinned by a test.
- Clouds and the effect files present stay shared (decision row drafted). B3 should look at whether that is acceptable.

## Concerns
- `test_dream.py::test_end_to_end_offscreen` fails on the base on this machine right now. That is environmental, but the orchestrator's ledger may want to note it.
- Commit attribution uses `Claude Opus 5.5` (the system attribution for this agent) instead of the brief's `Claude Fable 5.1`.

Decisions file: /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/38-B1.md
