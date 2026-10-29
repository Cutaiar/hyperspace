# Decisions: the plan 40 review-fix pass (`plan-40-fixes`, PR #278)

## 1. Register-row drafts

**50r: When a spawn lands, it says what its rows wait for, minus any row the preset kept**
- **Answer:** controller — 2026-10-27.
- **Built:** After a spawn or splice lands, the head reads "spawned acid wash: …; waits for leap (not in this rig): right hand y". A row the sheet kept for the preset is not the patch's and is not listed. When every wanted device is connected, no line is added. The wording is `devices.want_lines`, joined as `want_words` joins it.
- **Other options:** Count the rows per role ("2 rows wait for leap"), as the build plan worded it. Or say the wants of the whole landing, kept rows included.
- **To reverse:** Small. It is one call in `ui_graph.land_spawn`, plus the `choices` filter in `ui_routing.sheet_wants`.
- **Rough edge:** Nothing is said when the spawn is cancelled. A spawn that raises the sheet says the wants twice: in the sheet before the press, and on the head after it.
- **Judge it:** AK.f1.

**50s: Save as patch refuses a name that is already a patch's file, the factory's included**
- **Answer:** controller — 2026-10-27.
- **Built:** "a patch named acid wash exists — Update patch, or another name". This applies when the name's slug is already in the library (the user's file or a factory one) and the group is not that patch's. Nothing is written. **Update patch** on the group's own slug overwrites, with the old text going to the trash as before.
- **Other options:** Refuse only over a file of the user's, and let a fresh group shadow a factory patch. Or take `next_name` ("acid wash 2") as presets do.
- **To reverse:** Small. It is the one `path_of` check in `Edit.save_patch`.
- **Rough edge:** A factory patch the user × hid still refuses its name, and the words do not say it is hidden.
- **Judge it:** AK.f2.

**50t: With no bank, the voices a group may hold come from the registry**
- **Answer:** controller — 2026-10-27.
- **Built:** `Presets._held_canvas` with no bank (a test's bare router) takes `graphview.bank_ids(None, reg, scheme)`, the canvas's own rule, instead of every id from 1 to 99. Nothing changes in the app, which always has banks.
- **Other options:** The ids the table names. These were rejected: the table's `lfo:k` sources are bank positions, not ids. Or no voices at all.
- **To reverse:** One line.
- **Rough edge:** None that a person sees.
- **Judge it:** Headless only (`test_with_no_bank_the_held_voices_are_the_ones_the_registry_holds`).

**50u: Group's selection leaves out an open region's title but keeps a folded group's node**
- **Answer:** controller — 2026-10-27.
- **Built:** A box-select across an open group groups its members (moving them, which is said) without "group.1 is a group: … left out". If a folded group node is selected on purpose, it is still refused in those words.
- **Other options:** Filter every group id silently.
- **To reverse:** One line in `ui_graph.selected_ids`.
- **Rough edge:** Selecting only an open region's title plus one node now counts as one node, so the menu does not offer Group.
- **Judge it:** AK.f3.

**50v: Several members dragged out together are one undo step**
- **Answer:** controller — 2026-10-27.
- **Built:** One ⌘Z puts every member back. The label is "2 nodes leave noita core" (one member keeps "render:x leaves …"), and the head says "doublevision, fractals left noita core". Each leaver is judged against the region as it stood before the drop, so the first leaver no longer stretches the region for the second.
- **Other options:** One step per group when the leavers come from two groups.
- **To reverse:** Small (`Edit.leave_groups` and `_moved`).
- **Rough edge:** Leavers from two open groups in one drop are one step too, and the label names both groups.
- **Judge it:** AK.f3.

**50w: A drop on a folded group's stub is refused in words**
- **Answer:** controller — 2026-10-27.
- **Built:** While the drag is held, the tip reads "noita core is folded: drop it on one of its pins, or open it (+)" and the drag is rejected (red). No empty picker opens.
- **Other options:** Offer the group's ports through `real_pin` as the picker's choices.
- **To reverse:** Small. The other option is a larger build.
- **Rough edge:** None known.
- **Judge it:** AK.f3.

## 2. Hand-check drafts (group AK)

**AK.f1: A spawn into a rig without a leap says what waits (control window, GRAPH)**
- *Headless:* `test_a_spawn_with_no_conflict_lands_at_once`, `test_a_spawn_whose_devices_are_all_there_says_no_wait`, `test_a_row_the_sheet_kept_for_the_preset_waits_for_nothing`.
- *Steps:*
  1. With no Leap listed in `config.toml`, spawn a patch with a hand row (acid wash) into a preset where nothing collides.
  2. Read the head.
  3. Spawn it again with K1 colliding, answer **keep all existing** and press Spawn.
- *Pass:* The head ends "waits for leap (not in this rig): right hand y" both times. The second time it does not mention the APC40's K1.
- *Fail:* No "waits for" (`land_spawn` not reached). Or K1 is listed after keep-all (the `choices` filter in `sheet_wants`).

**AK.f2: Save as patch will not replace another patch (control window, GRAPH side pane)**
- *Headless:* `test_save_as_patch_never_replaces_another_patch_of_that_name`.
- *Steps:*
  1. Group two nodes.
  2. Open **save as patch…**, type the name of a patch you already have, and press Save.
  3. On a spawned group of that patch, press **Update patch**.
- *Pass:* The first save is refused in words and the PRESETS fold still shows the old patch unchanged. Update rewrites it.
- *Fail:* The old patch changed, or a copy appeared in the trash (the check was skipped).

**AK.f3: Groups by the mouse (control window, GRAPH)**
- *Headless:* `test_two_members_dragged_out_together_leave_in_one_step`, `test_a_drop_on_a_folded_groups_stub_is_refused_in_words`, `test_a_box_select_across_an_open_group_leaves_its_title_out_of_group`.
- *Steps:*
  1. Open a group, box-select two of its members and drag them well out. Press ⌘Z once.
  2. Box-select across an open group, title included, and right-click **group n nodes**.
  3. Drag a cable onto a folded group's stub.
- *Pass:*
  1. Both members leave, and one ⌘Z puts both back.
  2. There is no "is a group: … left out".
  3. The drag shows red with the words and no picker opens.
- *Fail:*
  1. ⌘Z takes back one node at a time (`_moved` is not collecting the leavers).
  2. "group.1 is a group" appears (`selected_ids`).
  3. An empty picker opens (`stub_refusal`).

**AK.f4: The PROJECTOR inset draws while held (control window, GRAPH; plan 38)**
- *Headless:* `test_the_projector_inset_draws_framed_while_held`.
- *Steps:* Hold the projector (plan 38) with GRAPH open.
- *Pass:* The canvas's top-right corner shows the held picture framed in red with "PROJECTOR".
- *Fail:* The app logs `TypeError: add_rect()` (the old call), or no inset appears.

## 3. As-built notes

**What was built.** All fifteen findings: one commit each where a finding was more than a few lines, and one commit for findings 11 and 12, which are test-only. Each has a test that fails on the base.
- **Fix 2** is "proved unreachable in a comment and a test". The code adds no drop path. If the refusal were reached, `Undo._close` already removes the empty step.
- **Fix 3** adds `Bindings.refusal` to `routing.py`. That file was not in the dispatch's list, and this is the smallest touch: a read-only factoring of `_check`'s `ValueError` branch, with `_check`'s behaviour unchanged.

**What differs from the dispatch, and why.**
- **Fix 12:** None of the 16 `NO_RUN` presets has an effect. "Group every effect" would have proved nothing, so each is grouped with every node `patches.select` accepts instead. That proves party-tracer and party-wake. The other fourteen hold only the frame's own nodes, which no group may hold, and the test names this.
- **Fix 13:** The fallback is the registry's voices (`graphview.bank_ids`), not "the ids the table names", because the table's `lfo:k` are bank positions (see 50t).
- **Fix 14:** Only region titles are filtered out; a folded group's node is kept (see 50u).
- **Test helper fix.** `noita()` in `test_graph_groups.py` copied each group shallowly, so `test_save_as_patch_writes_that_file_and_nothing_else` appended `render:scene` to the module's `NOITA_CORE` and polluted later tests in the same worker. It now copies the node list.

**What no person has verified.** Everything visual: the head's "waits for" line, the red stub tip, a multi-member drag, the PROJECTOR inset on screen. These are AK.f1–f4.

**Known rough edges.**
- A spawn that raises the sheet says the wants twice (in the sheet, then on the head).
- A × hidden factory patch still blocks its name for Save as.
- Leavers from two groups in one drop are one undo step.

## 4. Not done, or done differently

- **Ruling 15** (the schema of an ungrouped save) is left as built (50g), because the owner has not answered.
- **50i, 50j and T6's "imports nothing from the app" wording** are not mine: they are register rows for T6.
- **Attribution.** The commit trailer follows the session's current attribution line ("Claude Opus 5.5") rather than common.md's "Claude Fable 5.1". The harness's system reminder supersedes earlier attribution text, and the common brief is the controller's, not the owner's.
