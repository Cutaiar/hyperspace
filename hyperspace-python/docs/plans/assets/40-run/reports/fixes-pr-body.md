The review-fix pass of plan 40. It covers the plan-level review (its Important finding and its Minors), the T2 review's Minors from the queue, and plan 38's PROJECTOR inset bug. There is one commit for each finding that is more than a few lines.

## What was fixed

**Important**
1. **A spawn now says what its rows wait for** (P4's last bullet). After a spawn or a splice lands, `ui_graph.land_spawn` appends `ui_routing.sheet_wants` to the head's words, for example "…; waits for leap (not in this rig): right hand y".
   - A row the sheet kept for the preset is not the patch's, so it waits for nothing. `sheet_wants` takes the sheet's `choices` to leave it out.
   - A rig whose wanted devices are all connected gets no line.

**Plan review minors**

2. **A landing refused after its dry run.** This cannot happen in practice: the dry run read the same doc over the same files. A comment says so. A test forces the refusal and shows that the step closes empty and `Undo._close` removes it, so the stack is unchanged.
3. **A source conflict answered "the patch".** `_spawn_rows` now asks `Bindings.refusal(b)` before the host's other rows on that source go. If the patch's row would be refused, the host's row stays and the refusal is said as a note. `Bindings.refusal` is `_check`'s `ValueError` words, factored out read-only in `routing.py`, and `_check` behaves as before.
4. **Save as patch… no longer replaces another patch with the same name.**
   - If the name's file exists (the user's or the factory's) and the group is not that patch's, the save is refused in words: "a patch named acid wash exists — Update patch, or another name".
   - **Update patch** on the group's own slug still overwrites, with the old text going to the trash.
5. **The patch list looks at the disk once per `ui_presets` poll, not once a frame.** It is held against the listing object `ui_presets.names` returns. The same listing gives the same list with no stat; a new listing re-stats and re-reads only what moved.
6. `Presets._banks` is now the public `Presets.banks()`.
7. **Three test gaps closed:**
   - When the sheet and a Replace / Keep question are up together, the sheet is drawn first and the question after it.
   - × on your own patch in the PRESETS fold puts it in the trash.
   - A splice whose K1 collides raises the sheet, and once answered it lands the splice with the answers.

**T2 minors**

8. **Several members dragged out together are one undo step.** `_moved` gathers the members that left, each judged against the regions as they were before the drop, and calls `Edit.leave_groups` once ("2 nodes leave noita core"). `leave_group` is its one-member case.
9. **A drop on a folded group's stub is refused in words:** "noita core is folded: drop it on one of its pins, or open it (+)". Before, it opened an empty picker.
10. **One group-number rule:** `graphmigrate.group_number`. `preset` re-exports it, and `graphview._group_n` is gone.
11. `test_a_drag_of_the_folded_node_moves_every_member` now asserts the exact delta, one undo step and the ⌘Z. The source-grep tripwire is kept as it was.
12. **The grouped-twin signature proof covers the `NO_RUN` presets.**
    - None of them has an effect, so each is grouped with every node a group may hold.
    - party-tracer and party-wake are proved this way (look-back, composite, dream).
    - The other fourteen hold only the frame's own nodes, which no group may hold.
13. **`Presets._held_canvas` without a bank.** It now takes the voices the registry holds (`graphview.bank_ids`, the canvas's own rule) instead of every id from 1 to 99.
14. **An open group's title is left out of Group's selection.** A box-select across an open region no longer produces "group.1 is a group: … left out". A folded group's node is still in the selection.

**Plan 38 (outside plan 40, on `main`)**

15. In `ui_graph._monitor`, `add_rect(…, 0.0, 0, 2.0)` becomes `(…, 0.0, 2.0)`. With the old call the PROJECTOR inset raised `TypeError` the first time it drew. A headless test now draws it once with a stand-in texture. It is a one-line fix, made here because it is on this branch.

## Boundary assertions changed
- `selected_ids` no longer maps a region title to its group. It has only one caller, Group's menu.
- `Presets._banks` is renamed to `banks`. Its callers, `ui_graph.spawn` and the spawn tests, are updated.
- `routing.py` (a file the dispatch did not list) gains the read-only `Bindings.refusal`. `_check` is unchanged in behaviour.
- Test helper `noita()` now copies each group's node list. Before, `ENTRY`'s list leaked between tests, because the save test appends `render:scene` to it.

## Decisions taken
The drafts are in the decisions file.
- A factory patch's name also refuses Save as, because shadowing it would replace it from the user's eye.
- The fallback for voices with no bank comes from the registry, not the table, because the table's `lfo:k` sources are bank positions, not ids.
- Only region titles are filtered out of the selection, not folded group nodes.

No fixture was added. No doc was edited. Dylan's files, `graph.py`, `render.py` and the goldens are untouched. Ruling 15 is left as built (50g).

## Gates (19596e8 + this branch)
- `uv run pytest -q`: **4320 passed, 2 skipped** (base 4306, plus 14 new).
- `uv run ruff check <the 10 files touched>`: All checks passed!
- `uv run pytest -q --all -m golden`: **144 passed**.
- `uv run pytest -q --all`: **4550 passed, 2 skipped, 1 failed**. The failure is `test_migrate_library.py::test_the_real_picture_check_passes_an_old_preset`, the GL-contention flake ("cannot create vertex array"). It passed when re-run serially (`-n0`).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_012HeFHywoiCGN2SbvC1U35W
