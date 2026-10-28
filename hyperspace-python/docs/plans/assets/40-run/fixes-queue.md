# Review-fix queue (plan 40) — carried into the fix pass after the plan-level review

From the T2 review (`reports/t2-review.md`, Minor):
1. `ui_graph._moved` → `_left_group`: several members dragged out of an open group at once
   push several undo steps; collect the leavers and apply them under one `push`.
2. `_stub_drag` → `open_land(nid="group.N")`: a drop on a folded group's stub opens an empty
   picker (`land_choices` returns `[]`); refuse in words via `stub_refusal`, or offer the
   group's ports mapped through `real_pin`.
3. `preset.group_number` and `graphview._group_n` duplicate; keep one in `patches` or
   `graphmigrate` (both leaves) and call it from both.
4. Thin tests: `test_a_drag_of_the_folded_node_moves_every_member` asserts only membership
   — assert the exact delta and one undo step; `test_patches_select_is_the_one_rule…` greps
   source only (keep as a tripwire; add a behavioural assertion if cheap).
5. The signature proof covers the 9 presets with a main run; group every effect of the 16
   `NO_RUN` presets too (cheap).
6. `Presets._held_canvas` falls back to `range(1, 100)` without a bank (test routers only) —
   make it the ids the table names, or document.
7. The open region's title node is selectable: box-select adds the group id to `menu_sel`
   and Group says "group.1 is a group: … left out" — filter group ids out of the selection
   before `Edit.group`.
8. (docs, T6) ids reusable after ungroup (50f) — the owner's eye; and 50g vs row 394
   (controller ruling 15).

Plan 38 bug on `main` (confirmed by the T2 reviewer):
9. `ui_graph._monitor` (~line 1157 on f8d2e73): `dl.add_rect(ImVec2, ImVec2, col, 0.0, 0, 2.0)`
   raises `TypeError` in a frame — imgui_bundle's signature is
   `add_rect(p_min, p_max, col, rounding=0.0, thickness=1.0, flags=0)`; fix to
   `(…, 0.0, 2.0)`; add a headless test with a stub texture (`tex.glo != 0`) that draws the
   inset once. Outside plan 40's scope but on the branch and one line; say so in the commit
   and the PR body (the hold inset never drew on `main`).

From the T1 review, left as noted (no code): `hidden.json`'s `"patches"` key is dropped by an
older build's rewrite (both Macs update together).

From the T4 review: nothing left.

To add after the T3 review and the plan review: their findings.
