# Plan-level review: plan 40 (patches), `plan-40-build` @ 19596e8 against `origin/main` @ 026989e

This covers the whole-build pass (T0–T5 plus the T1/T4 review fixes) and T3's first task-scoped review (PR #277, `f8d2e73...19596e8`). Everything was read-only. I ran no suites; the controller's counts and the implementers' counts are taken as reported.

### Spec compliance

**Decisions (the owner's column)**
- **D1 ✅** `patch.py` became `modgraph.py`. The proof grep (`patch\.py|patchmod` over `hyperspace/` and `tests/`) is empty. The doc edits against `main` are symbol-only (DECISIONS, DECISION-REGISTER, ARCHITECTURE, ENGINEERING, plan 28 docs), which T0 was allowed to make.
- **D2 ✅** Nothing is attached by itself:
  - `patches.check` refuses crossing wires, and `spawn` lands only the patch's own wires (T1 fix).
  - `Edit.spawn` adds `landing.wires` only (graphview.py:4354–4400). The test asserts the section's wires = before + the patch's two (test_graph_groups.py, `test_spawn_lands_through_the_doors…`).
  - Splice: `_splice` removes the one cable (and any D1 placement into that port) and adds exactly `s → inlet` and `outlet → d`, in the same step.
  - **wire as saved** is one press and one step, and refuses in words.
- **D3 ✅** Ask, in one sheet. `ui_routing.modal` (ui_routing.py:592) draws `panel.spawn_question` first, in the same `PROMPT` popup at `SHEET_W`, ahead of Replace / Keep. It has one row per conflict, **keep all existing** / **take all**, the wants, and Spawn / Cancel. Spawn is one step; Cancel lands nothing and pushes no step (both tested).
- **D4 ✅** Saved and folded until `+`. This is T2's structural fold, and it is counted (T2 review). T3 adds pins to the folded node (`_open_pins`) but drops no cable. Nothing else in the diff hides a cable.
- **D5 ✅** Only the boundary. `lift` keeps members' values only, and `spawn` filters to members whatever the file says (patches.py `values = {… if m.owns(k)…}`).
- **D6 ✅** Retired outright:
  - `library/fx/*.json` (the six), `_fx_module`, `_watch_fx_modules` and `module_runs` are gone (grep empty), and `RETIRED_MODULES = ("fx",)`.
  - The tests that went are only module-preset tests.
- **D7 ✅ with one open question.**
  - `groups` writes `/8` only when non-empty (preset.py:1375–1379), and the migration is absent → no groups.
  - `hyperspace/library/` changes only by the six removals.
  - Ruling 15 (an ungrouped save stays `/7`, versus row 394's "newest schema always") is still pending the owner, and is recorded.
- **D8 ✅** `apc40.py`, `midi.py`, `bindings.default.json` and `ui_desk*.py` are absent from the diff stat. Nothing spawns from the desk.
- **D9 ✅** Every row is preselected to the patch (`{k: PATCH_SIDE …}`, ui_graph.py:2171ff). A row with no answer defaults to the patch in `_spawn_rows`. Tested: `choices == {0: "patch"}`.
- **D10 ✅** `ui_fx.py` is untouched (empty stat). The module strip is hidden through `ui_presets.strip` (ruling 9).

**The thirteen checks**
1. **The renderer learns nothing.**
   - `graph.py` differs only in one docstring word (`patch.py` → `modgraph.py`). `render.py`, `tests/golden/` and `frame-signatures.json` have an empty stat.
   - The grouped-twin signature test and the 8 grouped golden proofs compare against the flat original (T2 review, confirmed in `test_golden_frames.py` +45).
2. **D4 is the only fold.** See above. `preset_only` keeps groups (T2).
3. **D2 proofs exist and are strict.** Wires before / after, splice wires and run, wire-as-saved refusal and one step.
4. **D3 / D9.** Covered above. `kept_by_host` is written, carries the words ("K1"), is saved by `group_entry` and is drawn by T2's node and side pane. `Learn.hold` holds while the sheet is up.
5. **Through the doors.**
   - A grep of the whole diff for `.modulate(`, `._value`, `.value =`, `table.x[`, `table.x =` and direct list writes finds only `table.redraw_serial`, which the build plan sanctions.
   - Each verb has one `_step` before the first write. `land_group`, `lib.restore` and the table's calls push nothing (checked).
6. **No file is written by a spawn.**
   - The spawn test byte-diffs every file under the rig's home. That home is `tmp_path`, which also holds `bindings.json`.
   - The save test shows `patches/noita-core.json` as the only new file, with the rest byte-identical.
7. **Dylan's files.** Empty stat.
8. **Schema.** See D7.
9. **D6 / D10.** See above.
10. **P4.** `_rig` reads `d.status` directly and `panel_wants` runs once a frame (T4 fix). The event fires `_changed` once a frame and the hook once per change. `midi.py` is untouched.
11. **Leaves.**
    - `patches.py` imports `graph`, `routing`'s pure names, `modifiers`, `modbank`, `lfo` and `envelope`, and its AST test bans the app modules.
    - `graph.py` imports only the render stack.
    - `test_app_boundary.py` (the no-torch boundary) is untouched.
12. **Tests assert things.** The fixtures `tests/fixtures/patches/acid-wash.json` and `tests/fixtures/groups/party-noita-grouped.json` are tracked. Thin spots are listed below.
13. **Seams.**
    - `VGroup`'s boundary comes from T1's one classifier (`patches.select` / `crossing`).
    - The sheet's wants are `devices.wants` / `want_lines` (`ui_routing.sheet_wants`).
    - The group status comes from `wants_for`.
    - `kept_by_host` is drawn when T3 fills it.
    - The thumbnail uses plan 37's `thumb_wants` (T2).

**T3's task review, (a)–(i)**
- **(a) ✅** `Edit.spawn` (graphview.py:4354) works in this order:
  1. stale check (no write);
  2. dry `_land`;
  3. **one** `_step` (4401);
  4. `_land_quiet`, which holds `_land`'s own push;
  5. `bank.add`, `add_modifier`, `lib.restore`, `_spawn_rows` (`add` / `replace_owner` / `bind(write=False)`), `set_macros`, `land_group` and the layout.

  Nothing after the step pushes again. Cancel calls `cancelled()` only, and the test asserts that `len(u.stack)` is unchanged.
- **(b) ✅** Wires = before + internal. Splice adds two and removes one, in one step. **wire as saved** refuses a fed port: "output.all.image is taken" (graphview.py:4536).

  **On 50j:** refusing is right under D2 as written. The spec says the chip lands the cables "if the host has those nodes and the ports are free, refused in words otherwise". Taking the port over would cut the host's run as a side effect of a chip whose result is described as "lands those two cables", which is a hidden edit.

  **The owner should rule** on whether he wants a separate, explicit take-over. That could be a second chip, "wire as saved, replacing huecycle → All outputs", one press, its result drawn. The case for it: in every host whose run already feeds All outputs (most of them), the out pin always refuses, so the chip is half-useful there and splice is the real path. Put this as a register row beside 50j, not a code change now.
- **(c) ✅** The sheet is drawn in `modal` ahead of Replace / Keep, with the rows preselected, keep all / take all, the wants beneath, and Spawn / Cancel. `kept_by_host` is written and said ("K1 kept by the preset", "1 row kept by the preset").

  The `Learn.hold` flag works as follows:
  - `accepts` returns False while held (learn.py:484). Every completer (desk, hands, pad, OSC, the desk diagram) goes through `accepts`.
  - `modal` re-syncs the flag every frame, and `settle_sheet` releases it on both buttons.
  - The test proves the armed learn survives and no row lands.
- **(d) ✅** The scratch-home diff is strict: every file and its bytes are compared, before and after spawn and undo. Save as patch writes exactly one file.
- **(e) ✅** The cable becomes a drop target only during a browser drag, via `cable_near(kinds=("render",))` + `splice_target`:
  - `_cable_ends` accepts picture cables of the section only, and not the bus.
  - `splice_refusal` requires exactly one inlet and one outlet of that type.

  `_patch_drop` calls `spawn(…, splice=c)` directly. `open_land`'s only caller is still `_stub_drag` (ui_graph.py:3771).
- **(f) ✅** `patches_fold` reuses `_list_row` with `PATCHES`. A pick is suppressed (`picked and not patch`). × calls `hide` / trash and rename calls `rename`, both through `Library` with the group. Nothing spawns from there.
- **(g) ✅** The second spawn gets `.2` ids, `mod.2` and `group.2`. The K1 collision with the first copy raises the sheet, the kept row is said, and the hover lists the renames.
- **(h) ✅, with the substitution.** party-trip holds no acid / wobble / delay / warp, so the first spawn keeps the bare ids by `_new_instance`'s rule, and the `.2` proof comes from the second spawn. Splice on `scene → plasma.image` is asserted by the explicit wires and two calls: `run_of(…, "scene", "delay.image") == ("acid", "wobble")` and `run_back(output.all.image)` unchanged.

  Together these prove what the build plan's proofs ask: ids by the instance rule, the run spliced, and the downstream run intact. "The hand row" reaches the patch through `mod.1`'s input, which is no route (474x); the test asserts that input. T6 should correct the build plan's example in "as built".
- **(i) ✅** `Presets.parts()` is 14 lines, read-only, and is exercised by the save test. `Learn.hold` / `held` is 13 lines and is tested. T3 changed nothing in `patches.py`.

⚠️ **Cannot verify from the diff:**
- Every visual: the sheet at `SHEET_W`, the drag from the popup onto a cable (whether the popup stays up, the highlight), the open pins on the folded node, the side pane form and the PRESETS fold. These are hand checks 395–398 / 401 and AK.5–7.
- The gate counts. I did not re-run them.

### Strengths
- The landing follows `load_doc`'s order through the real doors, and the one-step property is enforced structurally: a dry `_land`, then exactly one `_step`, then `_land_quiet` with the push held.
- The undo test compares the full state tuple (signature, layout, groups, section, every binding, modifiers, macros) before and after, so it cannot pass vacuously. The LFO/macro test runs on `headless.make_app` with the real banks.
- `Learn.hold` is a better choice than clearing `learning`, because it keeps the user's armed learn. Gating it in `accepts` covers every completer through one gate.
- `_spawn_refusal` (50p) makes a second Spawn of the same landing harmless, and that is tested.
- Across the plan:
  - One classifier, shared by `lift`, `read`, `Group` and the group node.
  - The renderer is untouched, with twin proofs over every grouped main run.
  - Dylan's files are untouched.
  - The fx retirement has no factory byte moved.
  - The T1 and T4 Important findings were fixed and verified in the records.

### Issues

#### Critical (must fix)
None.

#### Important (should fix)
1. **A spawn never says the devices its rows wait for. P4's last bullet and Task 4 §3 are not built.** graphview.py:4406–4442 (`Edit.spawn`'s `notes`) and ui_graph.py `land_spawn`.
   - **What is wrong:** the spec says "A spawn into a rig that lacks a device says it at the spawn (the notes line: '2 rows wait for leap')". Task 4 §3 says "T3 reads `Landing.wants` through `devices.wants`". `notes` holds only `landing.notes` (macro and voice notes), and `Landing.wants` is read by nothing. 50o admits that a conflict-free spawn into a rig lacking a device says nothing at the spawn.
   - **Why it matters:** no sheet is shown when there are no conflicts, so there the wants are never read before or at the press. That is the "gracefully tell you" half of the owner's ask, at the moment it matters.
   - **Fix:** in `ui_graph.land_spawn`, after a successful `e.spawn` / `e.splice`, append `ui_routing.sheet_wants(panel, landing)` to `e.said`. That function is already written and tested, and it yields "leap (not in this rig): right hand y". Alternatively, word a count per role ("2 rows wait for leap"). Then assert the line in `test_a_spawn_with_no_conflict_lands_at_once`; the rig there has no apc40 or leap, so the words are deterministic.

#### Minor
1. **A failed post-dry-run land leaves an empty undo step.** graphview.py:4401–4404: `_step(label)` runs before `_land_quiet`. If the latter refuses (the dry run says it cannot), the step stays with nothing in it. Fix: on `why is not None`, pop the step (`undo` has a drop for an unchanged mark), or note it as unreachable.
2. **A source conflict answered "patch" removes the host's rows before `replace_owner`.** graphview.py:4477–4480. If `replace_owner` then raises `ValueError`, the host's rows are gone, no patch row is added, and only a note says so. Everything stays inside the one step, so ⌘Z restores it. Fix: call `replace_owner` first, or check `Binding` validity before removing.
3. **Save as patch… silently replaces another patch with the same slug.** graphview.py:4558 → library.py:2013. A fresh group named like an existing user patch overwrites it, with the old text going to the trash. That is recoverable but unasked. Fix: when `g.patch != slug` and the file exists, refuse in words ("a patch named X exists: update it from its group, or pick another name"), or take `next_name` as presets do.
4. **`patch_list` runs every frame the canvas picker is open.** ui_graph.py:2338 calls `_spawn_menu` → `patch_list` before `begin_menu`, which means `ui_presets.names` plus a `stat` per patch file each frame. The drag path does the same each frame. Fix: list once per open, or gate on `begin_menu` and cache on `ui_presets`' poll only.
5. **`ui_graph.spawn` reaches into `pre._banks()`** (ui_graph.py:2197). Fix: expose it as a public `Presets.banks()`, or fold it into `parts()`.
6. **Test gaps:**
   - Nothing tests the sheet and a Replace / Keep question up together (the "ahead of" ordering).
   - The fold's × on *your* patch (trash) is untested; only the factory hide is.
   - The splice is not tested with a conflict (sheet → `land_spawn` with the splice cable). Its path differs only by the closure, but it is a seam.
7. **Open pins and wire as saved are session-only (50i).** After save and reload, a spawned group whose pins were never wired shows no in/out pin, whereas the spec's P2 says "one pin per host port … or open". This is recorded and reasoned (no hidden "where it was" data, plan 36). The owner should see it in T6's register row beside 50j.
8. **`patches.py`'s leaf test checks direct imports only.** Through `routing` it pulls `apc40`, `params` and `modgraph`, and through `graph` it pulls `moderngl`, which is the same as `graphmigrate`'s precedent. This is acceptable, but T6 should say "leaf over the pure pieces of routing", not "imports nothing from the app".
9. **Carried from earlier reviews (already in `fixes-queue.md`; listed so they are not lost):**
   - T2's items 1–8: multi-member drag-out undo, the empty picker on a group stub, the duplicated group-number helper, thin tests, the NO_RUN presets, the `_held_canvas` fallback, the selectable region title, ids reused after ungroup.
   - Plan 38's `_monitor` `add_rect(…, 0.0, 0, 2.0)` TypeError (ui_graph.py, about line 1157). It is on this branch, so fix it with a stub-texture test.
   - Ruling 15 (`/7` for an ungrouped save versus row 394) is for the owner.

### Assessment
**Task quality: Needs fixes.**

The plan is sound and faithful to the owner's column, and nothing is Critical:
- The renderer learns nothing, and D4 is the only fold.
- Every verb is one step through the existing doors, no spawn writes a file, and Dylan's files are untouched.
- T3 in particular lands correctly in load order, with strict tests.

The one Important gap is that a spawn does not say the devices its rows wait for: P4's notes line, which Task 4 §3 assigned to T3. It is a few lines in `land_spawn` that reuse `sheet_wants`, and it should go into the review-fix pass with the Minor items above and the existing queue. 50j (refuse a fed port) is correct under D2 as written. Whether to offer an explicit take-over is the owner's call and should be recorded as a register row.
