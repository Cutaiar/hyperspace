# Review fixes: plans 28 and 30

- Branch: `plan-28-30-review-fixes`.
- Base: 327e646. I fast-forwarded with `git merge --ff-only FETCH_HEAD`, and `git log --oneline -1` printed 327e646.
- PR: https://github.com/Cutaiar/hyperspace/pull/221, into `plan-28-30-integration`.

## Commits
| Commit | Subject |
|---|---|
| 7f834e4 | Review: the wire-built check sees composite instance 1 |
| 99c217a | Review: into output N says it when output N stands down to its ground |
| c467522 | Review: the GRAPH page's docstring says it edits |
| 14ceb6e | Review: a test for the same-pick no-op of set_modifier_input |
| a288a3f | Review: a redo test for tidy |
| 4c3260e | Review: the GRAPH head's words follow the last edit |

## Per item

**1. The composite predicate** (`tests/test_graph_wires.py`)
- The new helper `_wire_built(n)` is true for a `Wired` or `Composite` node named exactly `composite`, or starting with `wire(` or `composite.`.
- `test_no_factory_preset_changes` now uses it.
- New test `test_the_wire_built_check_sees_a_wired_composite`:
  - A section with composite 1 and composite 2, both wired, reads with no note. `_wire_built` flags both.
  - A plain default graph with a through output does contain `composite(scene+hands)`, and `_wire_built` flags none of its nodes.
  - So the check is shown to fire, and to fire only on what a wire builds.

**2. The dormant word for `into` on a stood-down through output** (`hyperspace/graph.py`)
- `Graph.stood: set[str]` is new.
- `Graph.evaluate` first pops last frame's `stood` keys out of `Graph.dormant`, then clears `stood`.
- In `Output.run`, when `folds and end is None`, the new `Output._stood_down` records each fold effect's words. It writes `<effect> into output N — output N stands down this frame` into `frame.graph.dormant` and adds the key to `stood`, but skips any key the build already set.
- Readers are unchanged:
  - `ui.dormant_lines` (OUTPUT's `dormant:` lines) and `graph_words` (the hover) show it.
  - `ui_fx._dormant` reads the same dict, so the FX page's chip also shows the effect as dormant for that frame and leaves it out of the count. That is accurate, because the effect runs nowhere that frame.
- Pixels: none change. The fold was already skipped, no render path reads `dormant`, and the build-time checks against `dormant` (`_place`, `_place_one`, `_Wiring`) only run on a new `Graph`, whose `stood` is empty.
- Test `tests/test_graph_placement.py::test_into_a_through_output_standing_down_to_its_ground_is_dormant_for_the_frame` (GL). Setup: views `S()` and `S(scene=False, hands=True, through=True)`, palette `into: output.2`, no effect of the run on. It asserts:
  - the folds are `["palette"]`;
  - `stats["routes"][1] == (None, True)`, so `settle` gave the ground with the hands over;
  - `palette` is not among the effects that ran;
  - both outputs are byte-equal to the same frames with no placement;
  - `g.dormant == {"palette": said}`;
  - the `dormant_lines` and `graph_words` text.

  It then turns warp on and runs one more frame: the route has an end, palette runs, and the word and `stood` are gone.

**3. The docstring** (`hyperspace/ui.py`): `_page_graph` now reads "Both graphs on one canvas, edited through `graphview.Edit` (ui_graph.py, plan 28 N2; the edits N3 and N4)."

**4. N1's same-pick no-op**
- Test: `tests/test_modifiers.py::test_picking_the_input_a_modifier_already_reads_changes_nothing`.
- I put it in `test_modifiers.py` rather than `test_ui_routing.py` because that file holds the existing `set_modifier_input` undo test and its rig.
- Four calls change nothing: the same input picked again, index 1 and index -1 (both out of range), and `mod.99` (no such modifier). The undo stack length, `modifiers_serial`, the modifier's identity, its inputs and its param are all unchanged.

**5. N2's tidy redo** (`tests/test_graphview.py::test_a_tidy_is_one_undo_step`)
- After the undo, `redo()` returns true, the status ends `tidy the graph`, and both maps are `{}` again.
- The preset then reads clean, because the saved preset holds no positions either.

**6. N4's head words** (`hyperspace/ui_graph.py`)
- The new `_note(st, why)`:
  - always clears `st["said"]`;
  - sets `st["note"]` to the refusal, or `""`;
  - while `st["held"]` is true (a refusal already shown in this delete), changes nothing more;
  - sets `held` to true on the first refusal while the key is present.
- Callers: `_settle` (Ask, Refusal, success), `_render_said` (which sets `said` again after a landing), `_value_cut`'s session-row refusal and `_rig_node_cut`.
- `_delete` sets `st["held"] = False` before its two query loops and pops it in a `finally`.
- I kept the loops inside `_delete`. `test_create_and_delete_open_only_in_the_typed_dispatch` pins `query_deleted_link` to `_delete`, and I left that assertion unchanged.
- Tests in `tests/test_graph_edit.py`:
  - `test_a_render_edit_s_line_goes_at_the_next_edit_or_refusal`: a render landing, then four clears in turn: `add_modifier` (a value edit that lands), `_settle(Refusal)`, a render refusal, and `_rig_node_cut`.
  - `test_a_selection_delete_keeps_its_first_refusal_s_words`: `ed.begin_delete`, `NodeId` and the `query_deleted_*` calls are faked. The selection is shape (refused), a modifier (removed) and LFO 1 (refused), and the note stays as shape's words. Without the fix it would end on the LFO's words. `held` is gone afterwards, and a second delete holding only a modifier clears an old note.

**7. Tests asserting nothing**
- The review pass's issue list names only the vacuous composite check (Minor 3, N4's "vacuous half"). Item 1 fixed it and added the test that proves it fires.
- It names no other test that asserts nothing.

## Gates (from `hyperspace-python`)
- `uv run pytest -q` → `2373 passed, 2 skipped in 191.41s (0:03:11)`. The base had 2368, and this wave adds 5 tests.
- `uv run ruff check .` → `All checks passed!`
- `uv run pytest tests/test_golden_frames.py -q` → `7 passed in 20.49s`. All 596 frames match, and `git status` is clean, so `tests/golden/` has no diff.
- `git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py tests/golden/` → empty.

## Files changed
- `hyperspace-python/hyperspace/graph.py`, `hyperspace/ui.py`, `hyperspace/ui_graph.py`
- `hyperspace-python/tests/test_graph_wires.py`, `test_graph_placement.py`, `test_modifiers.py`, `test_graphview.py`, `test_graph_edit.py`

## Concerns
- None blocking.
- Item 2's word also marks the effect dormant on the FX page for that frame, through the shared dict. That is accurate, but it is a small UI change beyond OUTPUT.
- The case where an output falls back to the scene pipeline (the hands laid at the output are not folded) stays as row 223 describes it. It gets no word, because the fold does run there.
- For N6's register: row 223's rough edge can now say "said on OUTPUT as `… stands down this frame`".
- Commits carry the session's Opus 5.5 attribution lines (the harness's current attribution), not common.md's Fable 5.1.
