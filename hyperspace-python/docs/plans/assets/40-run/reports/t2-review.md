# T2 review — PR #276 (plan-40-t2 @ 865d0b3 against d08a363)

### Spec compliance
✅ compliant with the T2 brief, P2, D4, D7 and D2. Every one of the dispatch's doubts settles in the PR's favour:

1. **The renderer learns nothing.** `git diff --stat d08a363...origin/plan-40-t2` is empty for:
   - `graph.py` and `render.py`;
   - `tests/golden/` and `tests/fixtures/frame-signatures.json`;
   - `hyperspace/library/`, `apc40.py` and `midi.py`;
   - every doc.

   Both proofs compare against the ungrouped twin, not against themselves:
   - `test_a_grouped_preset_builds_the_graph_of_its_ungrouped_twin` (test_graph_groups.py:188) computes `want` from the flat load, then asserts `spec.to_json()` equality and `G.signature(build_graph(...)) == want`.
   - `test_every_preset_with_its_main_run_grouped_draws_its_goldens` (test_golden_frames.py:+434) compares against the recorded golden sha256s, or, off the gate Mac, against the ungrouped file's own picture.
2. **D4 is the only fold.** In `graphview.wiring`, the only new drop is `gs is not None and gs is gd`: both ends are in one folded group, decided by node membership and nothing else.
   - Any other cable with a folded end is re-ended, at its `ends` pin or else at the group's drawn stubs. That includes throughs, rig cables and kinds `_boundary` does not classify, so a cable can never lose an end.
   - `_drawn_id` returns True for a group id, because `view.node` is None, so `shown` cannot drop a re-ended cable.
   - The count test (test_graph_groups.py:222) is real. `folded + len(g.inside) == flat` checks the classifier's `inside` against the structural drop, and the open count equals flat.
   - `preset_only` adds the members (graphview.py:+2618), and the test asserts it.
3. **D7.**
   - `groups` is written after `layout` only when `live_groups()` is non-empty, and only then as `/8`.
   - An ungrouped preset is `/7` byte for byte, checked over every factory preset in `test_the_fixture_twin_resaves_byte_for_byte`.
   - The migration is `graphmigrate.groups_of` (absent → []).
   - An older build *refusing* an `/8` file is the ladder's existing rule. `Library` checks `int(v) not in kind.versions` (library.py:1978), which is exactly how a pre-plan-36 build treated `/7`, and `/6` and `/3` before it. The report's description is accurate. The only thing that is wrong is the spec's phrase "an older build drops the key on its save": no build ever gets that far, so the docs task should correct that sentence.
4. **One classifier.**
   - `patches.select`, `crossing`, `wire_type`, `touches`, `side`, `sub_side` and `input_side` are factored out of `lift` and `read`.
   - `lift` and `read` now call them. I checked that `read`'s macro and modifier branches are behaviour-identical: `m` holds the doc's macros, and `input_side` with `own_m` reduces to the old test.
   - `graphview._boundary` and `attach_groups` call only these, and `Edit.group` calls `select`. There is no second classifier.
5. **One undo step each.**
   - `Edit._step` → `undo.push(label, load=True)` runs once before the first write in `group`, `ungroup`, `rename_group`, `set_open`, `move_group` and `leave_group`.
   - `land_group` pushes nothing (T3's seam).
   - Drops are gated on mouse-up (`_moved`), so a title drag is one `move_group`.
   - Group then ⌘Z restores the signature, and redo works. Both are tested.
6. **Group refusals and ids.**
   - Refusals are by name, in words, with "nothing to group".
   - The id is `group.<n>` with n = highest held + 1.
   - Grouping a member of another group moves it, and the head says so (ruling 50a).
   - Nesting is refused ("group.7 is a group: …").
   - All of this is tested.
7. **Load and undo marks.**
   - `read_groups` drops absent, refused and duplicate members with notes, and drops empty groups.
   - `Marks.take` carries `groups` at index 7, and `put` restores it after the layout.
8. **Status, thumbnail and seams.**
   - The status line is `devices.want_words(devices.wants_for(table, rig, group_params(g)))`, cached per frame.
   - The thumbnail uses plan 37's `thumb_wants` plus `_thumb`.
   - `_group_chips(panel, group)` exists and is called in place.
   - `kept_by_host` is drawn on the node and in the side pane, carried by `group_entry` and read back by `read_groups`.
9. The `preset.py` diff touches only:
   - `GROUPS_KEY` and its constants, `VERSIONS`, `group_number`, `group_entry` and `read_groups`;
   - one key in `dumps`, plus `__init__`;
   - `load_doc` step 6½, `document`, `signature`, and the new `_held_canvas`, `_groupable` and `live_groups`.

   It does not touch `GraphSection._settle`, `names` or `_values`.
10. The tests assert counts, exact words, bytes and positions. The widget tests drive the real editor through `frame` and `_in_editor`, as `test_graph_legible` does.

⚠️ **Cannot verify from the diff:**
- Every visual: the region's tint, the title's live follow while held, the folded node's layout with its thumbnail, the side pane's input. These are hand checks 394 and AK.n1–n4.
- The gate counts (4294 / 144 / 4525). I did not re-run the suites.

⚠️ **Owner tension, recorded rather than hidden.** Ruling 50g writes `/7` whenever a preset has no groups. That brings back the "lowest schema that loses nothing" rule, which the owner's row 394 ("every save is the newest schema") superseded. The controller's brief demanded it for byte-for-byte saves, and it is written down as 50g. The docs task must put it in front of the owner as a deliberate exception to row 394, not bury it.

### Strengths
- The D4 fold is structural, so it cannot drift from the classifier unnoticed: the count test ties the two together. Unclassified cables fall back to the group's drawn stubs instead of vanishing.
- The classifier was factored out cleanly. T1's `lift` and `read` keep their exact behaviour, and the new pure tests pin every side function.
- The golden proof runs through `tools/golden_frames.picture` on a scratch library and never touches a factory file. The fixture is force-added under `tests/fixtures/groups/`.
- A deleted member is dropped lazily (50c), and that is the right call: value-node deletes carry no marks, so editing the list on delete would make undo lose the membership.
- The report is candid: it covers the extra pins (50h), the `/8` refusal, the attribution line, and the plan 38 bug.

### Issues
#### Critical (must fix)
None.

#### Important (should fix)
None.

#### Minor
1. **Dragging several members out at once makes several undo steps** (ui_graph.py `_moved` → `_left_group`, one `leave_group` per node).
   - Box-select two or more members of an open group and drag them out, and each member pushes its own step ("render:x leaves …"), so ⌘Z undoes one node at a time. If all of them leave, the group's removal is buried in the last step.
   - This bends "each gesture one undo step".
   - Fix: collect the leavers in `_moved` and apply them under one `push`, for example `Edit.leave_group(gid, [nids], ats)`, or push once in `_moved` and let later calls skip `_step`.
2. **A drag dropped on a folded group's stub opens an empty picker.**
   - `_stub_drag` → `open_land(…, nid="group.1")` → `land_choices` returns `[]` because `view.node` is None.
   - It is harmless, but it is a dead end with no words.
   - Fix: either refuse in `stub_refusal` when the stub's node is a group ("open the group, or drop on one of its pins"), or offer the group's `ports` (through `real_pin`) as the choices.
3. **Two group-number helpers that are near-duplicates:** `preset.group_number` (preset.py:+650) and `graphview._group_n` (graphview.py:+191).
   - `preset` imports `graphview`, so one module cannot simply import the other's helper.
   - Fix: put a single helper in `patches` or `graphmigrate`, which are leaves both modules already import.
4. **Some weak tests.**
   - `test_a_drag_of_the_folded_node_moves_every_member` (test_graph_groups.py:~418) asserts only that the members are now in the layout. Fix: assert the exact delta, as the title test does, and that the move is one undo step.
   - `test_patches_select_is_the_one_rule_for_lift_and_group` greps source text. It works as a tripwire, but it proves nothing behavioural; the classifier's real cover is the count test and `test_crossing_and_the_sides…`.
5. **The proof covers 9 of 25 factory presets.** Sixteen are skipped as `NO_RUN`, which the brief allows, and they are named.
   - Fix: a cheap strengthening is to group *every effect* (not just the main run) for the 16, at least in the signature proof.
6. **`Presets._held_canvas` falls back to `range(1, 100)`** for LFO and envelope ids when the router has no bank (preset.py:+1471).
   - This is only for test routers, but it means "held" stops meaning held there.
   - Fix: return no voices instead, and the tests would show whether any test relied on this.
7. **The ids rule partly contradicts the brief's own wording.** The brief says "never reused in the file". Under 50f (highest + 1), the number of an ungrouped highest group comes back.
   - The brief also says "(the modifier rule)", so it contradicts itself. 50f records this. It needs the owner's eye in the docs pass, not a code change.
8. **The open region's title node is selectable**, so a box-select across an open group adds the group id to `menu_sel`. Grouping then says "group.1 is a group: … left out" alongside the real result. This is noise only.

**Side question: plan 38's `_monitor`.** It is confirmed wrong.
- imgui_bundle's signature is `add_rect(p_min, p_max, col, rounding=0.0, thickness=1.0, flags=0)`.
- In this venv, I opened a frame and called `dl.add_rect(a, b, col, 0.0, 0, 2.0)`, and it raised `TypeError: add_rect(): incompatible function arguments`. The call `(a, b, col, 0.0, 2.0)` worked.
- The bug is in `hyperspace/ui_graph.py:1157` on the PR head (≈1137 on the base). The fix:
  ```python
  dl.add_rect(imgui.ImVec2(*a), imgui.ImVec2(*b), imgui.get_color_u32(ui.RED), 0.0, 2.0)
  ```
- It was not caught because no headless test draws the held projector's inset with a live texture (`tex.glo == 0` returns early). Add one that does, with a stub texture.

### Assessment
**Task quality: Approved.** The renderer is untouched, and both proofs compare a grouped twin against its flat original. D4 is the single, structural fold, and it is counted. One classifier serves `lift`, `read` and the group node. Every verb is one undo step through the existing door. The minor items (the multi-node drag-out undo, the empty picker on a group stub, the duplicated helper, a few thin tests) can go into the review pass or T3. The 50g exception to row 394 must be put in front of the owner by the docs task.
