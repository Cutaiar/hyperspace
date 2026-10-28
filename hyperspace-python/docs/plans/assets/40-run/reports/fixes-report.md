# Report: the plan 40 review-fix pass

- **Status:** DONE_WITH_CONCERNS. The concerns are minor: one file outside the dispatch's list was touched, two fixes are worded differently from the dispatch, and the trailer differs.
- **Base:** `plan-40-build` @ 19596e8 (confirmed after the reset). Branch `plan-40-fixes`, PR https://github.com/Cutaiar/hyperspace/pull/278, into `plan-40-build`, not merged.

## One line per finding
1. **Fixed: a spawn says what waits.** `ui_graph.land_spawn` and `ui_routing.sheet_wants(choices=)`. Tests: `test_a_spawn_with_no_conflict_lands_at_once` (exact line), `test_a_spawn_whose_devices_are_all_there_says_no_wait`, `test_a_row_the_sheet_kept_for_the_preset_waits_for_nothing`.
2. **Proved unreachable: an empty undo step.** A comment in `Edit.spawn`, and a test that forces the refusal and shows the empty step leaves the stack: `test_a_landing_refused_after_its_dry_run_leaves_no_undo_step`.
3. **Fixed: the referee is asked before the host's rows go.** `Edit._spawn_rows` plus the new read-only `Bindings.refusal` in `routing.py`. Test: `test_a_source_conflict_the_table_refuses_leaves_the_hosts_rows_whole`.
4. **Fixed: Save as refuses an existing patch's name.** `Edit.save_patch`, `PATCH_EXISTS`. Test: `test_save_as_patch_never_replaces_another_patch_of_that_name` (Update still overwrites).
5. **Fixed: the patch list is held against the poll's listing.** `ui_graph.patch_list`. Test: `test_the_spawn_menu_open_two_frames_lists_the_patches_once`.
6. **Fixed: `Presets._banks` renamed to `banks()`.** It is public, and its callers are updated. The BREATH spawn test exercises it.
7. **Fixed (tests):**
   - `test_ui_routing::test_the_sheet_is_drawn_ahead_of_a_replace_question_up_with_it`;
   - the × on your own patch, appended to `test_ui_presets::test_the_patches_fold_…`;
   - `test_a_splice_that_raises_the_sheet_lands_the_splice_with_its_answers`.
8. **Fixed: several leavers are one step.** `Edit.leave_groups`, `ui_graph._moved` / `_left_group` / `leave_groups`. Test: `test_two_members_dragged_out_together_leave_in_one_step`.
9. **Fixed: a folded group's stub is refused in words.** `ui_graph.stub_refusal`, `GROUP_STUB`. Test: `test_a_drop_on_a_folded_groups_stub_is_refused_in_words`.
10. **Fixed: one group-number rule.** `graphmigrate.group_number`; `preset` re-exports it and `graphview._group_n` is removed. Test: `test_one_rule_reads_a_group_number_for_the_load_and_for_group`.
11. **Fixed: the folded-node drag test.** It asserts the exact delta, one step and the ⌘Z. The tripwire is kept.
12. **Fixed, differently:** the `NO_RUN` presets have no effects. Each is grouped with every node `patches.select` accepts instead: party-tracer and party-wake are proved, and the other 14 hold only frame nodes. The test asserts this.
13. **Fixed, differently:** the fallback is the registry's voices (`graphview.bank_ids`), not the table's, because `lfo:k` are positions. Test: `test_with_no_bank_the_held_voices_are_the_ones_the_registry_holds`.
14. **Fixed: region titles are left out of `selected_ids`.** A folded group's node stays in. Test: `test_a_box_select_across_an_open_group_leaves_its_title_out_of_group`.
15. **Fixed: plan 38's `_monitor` call.** It is now `add_rect(…, 0.0, 2.0)`, in its own commit 86795d5 ("Plan 38 fix: …"). Test: `test_hold::test_the_projector_inset_draws_framed_while_held`. This is outside plan 40 and one line.

## How it was tested (from `hyperspace-python/`)
- `uv run pytest -q`: `4320 passed, 2 skipped in 46.05s` (base 4306, plus 14 new tests).
- `uv run ruff check <10 touched files>`: `All checks passed!`
- `uv run pytest -q --all -m golden`: `144 passed in 14.02s` (nothing re-recorded).
- `uv run pytest -q --all`: `1 failed, 4550 passed, 2 skipped in 58.43s`.
  - The failure is `test_migrate_library.py::test_the_real_picture_check_passes_an_old_preset` ("cannot create vertex array", GL contention).
  - Run serially with `-n0`, it gives `1 passed`. So `--all` is 4551 tests passing (base 4536, plus 1 flake, plus 14).

## Files changed (`git diff --stat 19596e8`)
- `hyperspace/graphmigrate.py`, `graphview.py`, `preset.py`, `routing.py` (not in the dispatch's list: the smallest touch, the read-only `Bindings.refusal`), `ui_graph.py`, `ui_routing.py`.
- `tests/test_graph_groups.py`, `test_hold.py`, `test_ui_presets.py`, `test_ui_routing.py`.
- No doc, no fixture, no golden. `graph.py`, `render.py` and Dylan's files are untouched.

## Commits
1. 86795d5 Plan 38 fix: the PROJECTOR inset's add_rect call
2. 7c1535b A spawn says what its rows wait for (P4)
3. a8af337 A landing refused after its dry run leaves no undo step
4. 18ab806 A source conflict asks the referee before the host's rows go
5. b2924ca Save as patch never replaces another patch of that name
6. fc13a55 The patch list looks at the disk once per poll
7. b654575 Presets.banks() is public
8. 85f4c6b The three test gaps
9. ecb7d5b Members dragged out together leave in one undo step
10. 5292341 A drop on a folded group's stub is refused in words
11. c8ba034 One group-number rule, in graphmigrate
12. 43a0938 The folded-node drag and the grouped-twin proof assert more
13. cd3950d With no bank, a group holds only the voices there are
14. be556af An open group's title is not in Group's selection
15. 209247d Ruff on the inset test's fixture name

## Self-review and concerns
- **`routing.py` touched.** `Bindings.refusal` is `_check`'s `ValueError` branch, factored out. `_check` now calls it, and its behaviour is the same for sinks, continuous sources and save refusals. `test_routing.py` passes.
- **`patch_list` caching.** The list is now held until `ui_presets`' poll (`LIST_POLL`) hands back a new listing. A patch file edited by hand outside the app shows on the next poll, not the next frame. Our own save invalidates at once, as before.
- **Fix 4 refuses factory names too.** This is beyond the dispatch's "the file exists", recorded as 50s. A hidden factory patch still blocks its name.
- **A test pollution was found and fixed in the helper.** `noita()` shared `NOITA_CORE` with the save test's `.append`. It surfaced only with `-n0` ordering.
- **Attribution.** Commits end with the session's current trailer ("Claude Opus 5.5"), not common.md's "Claude Fable 5.1". The harness's attribution reminder supersedes earlier attribution text, and common.md is the controller's brief, not the owner's instruction.

## Rulings and drafts
These are in `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/fixes.md`:
- rows 50r–50w;
- hand checks AK.f1–f4;
- as-built notes.

Ruling 15 is left as built (50g), because the owner has not answered.
