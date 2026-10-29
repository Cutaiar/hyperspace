# 38-B2 report: the hold's hand-check readiness

**Status: DONE_WITH_CONCERNS.** The concerns are minor:
- Writes to the orchestrator's workspace were refused, so this report and the decisions file are at the worktree fallback paths.
- Two load-flaky `--all` failures, neither from plan 38.

- **Branch:** `plan-38-b2-checks`, base `plan-38-hold` @ 397b7ba (confirmed with `git log --oneline -1`).
  - `git reset --hard` was refused by the harness. The worktree was clean on main f2351a0, which is an ancestor of the plan branch, so `git merge --ff-only FETCH_HEAD` reached the same base.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/257, into `plan-38-hold`.
- **Commit:** `a4ea685` "Plan 38 B2: the hold's hand checks, three of them as tests". The PR title follows the dispatch ("two of them as tests"); the commit counts the check-5 test too.
- **Decisions file:** /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a1428b8a891a98b63/.run/38-B2-decisions.md (not committed). It holds:
  - the seven-check status table
  - one register-row draft: what Drop's one step restores and what it leaves
  - AI.1–AI.7 drafted in the hand-checks format
  - as-built notes

## What was built
Three tests in `hyperspace-python/tests/test_hold.py`, taking it from 19 to 22.

1. **`test_on_gl_the_program_draws_the_held_wiring_while_a_graph_edit_lands`** (GL, `empty_frame`). This is the prompt's (a), covering AI.1, AI.2 and AI.3's cut.
   - Setup: W1 is landed through a real `preset.GraphSection` on a real `Renderer`.
   - Hold, then the GRAPH page's edit `graphview.Edit(graph=gs).insert_effect(("scene","output.all.image"),"kaleido")` lands W2.
   - The outputs drawn inside `Hold.program` match W1's frame drawn alone before the hold, byte for byte.
   - The preview via `Hold.draw_preview` matches W2's frame drawn alone after Take, byte for byte.
   - W1's and W2's frames differ.
   - Mutation check: with `r.wiring = self.wiring` removed from `Hold.program`, the test fails. I reverted the mutation with `git checkout -- hyperspace/hold.py`; hold.py is unchanged in the diff.
2. **`test_drop_after_a_whole_new_look_is_one_undo_step_back_and_one_forward`** (headless, `test_undo.boot`). This is the prompt's (b), AI.4.
   - Hold on a clean TUMBLE. While held: three params, a GRAPH landing, TRIP loaded, macros set and a route removed on it, `eye.fov` moved.
   - Drop: `same_look` with the hold point, and the wiring is back. It is TUMBLE with a clean dot. `eye.fov` is kept. The stack grew by exactly one (`"drop the preview"`), and nothing re-lands after settling.
   - One undo: TRIP is back, edited and dirty, with the edited wiring. `eye.fov` is still kept, and the stack is back to its pre-Drop depth.
3. **`test_learned_desk_buttons_light_while_held`** (AI.5).
   - `output.hold` and `output.take` are learned through `MidiIO` + `Learn` onto APC40 notes 0x3C and 0x3D on channel 0, which are free on the startup desk.
   - LEDs from the fake out port: both on while held, both off after take and after drop. The learning press does not fire.

Check by check:
- **AI.6** (FPS, Syphon/NDI): machine-only.
- **AI.7**: already pinned by `test_a_modulated_param_rides_its_held_base`.
- **AI.3**: trail continuity through Take stays machine-only.

## Tests (from `hyperspace-python/`)
```
uv run pytest -q tests/test_hold.py                  22 passed in 3.09s
uv run pytest -q                                     3980 passed, 2 skipped in 35.45s   (base 3977 + 3)
uv run ruff check .                                  Found 25 errors.   (same 25 as the base; test_hold.py: All checks passed!)
uv run pytest -q --all tests/test_golden_frames.py   128 passed in 6.07s   (none moved, none recorded)
uv run pytest -q --all                               2 failed, 4190 passed, 2 skipped in 50.97s
uv run pytest -q --all -n 0 <the 2 failures + test_dream::test_end_to_end_offscreen>   3 passed in 7.24s
```
- The two `--all` failures were `test_media_channels::test_rapid_switching_with_slow_closes_stays_fast_and_balances` and `test_media_core::test_bad_file_is_an_error`. Both pass serially, so they are load-flaky.
- The count matches the base: 4187 + 3 = 4190.
- The dream test that fails on the base passed this time.

## Files changed
- `hyperspace-python/tests/test_hold.py` only.

## Self-review
- The GL test pins the preview's clock with an instance override (`pr.now = lambda t_now=None: T`), because `draw_preview` passes no `t_now`. This is test-only and adds no seam.
- The "drawn alone" references come from the same renderers before the hold and after Take, not from fresh renderers. Kaleido's instance params live on the shared registry and `FxState`.
- The drop test leans on `test_undo.look` / `same_look`, which compare the registry's performance snapshot, routes, desk and macros. It also checks the name and the dirty dot separately.

## Concerns
- The workspace paths were refused ("Edit the worktree copy"). The report and decisions are at `<worktree>/.run/`, as common.md allows.
- Commit attribution uses common.md's `Claude Fable 5.1` line, as the dispatch requires. This differs from B1, which used Opus 5.5.
- A rough edge worth B3/B4's eye, drafted as a register row: a desk learn made during a hold lands in the preset layer, so Drop takes it back too.
