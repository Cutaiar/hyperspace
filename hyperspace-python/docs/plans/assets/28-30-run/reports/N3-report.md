# N3 report — editing the modulation on the canvas, Learn from a port

**Status:** DONE_WITH_CONCERNS. The concerns are below; nothing has been dragged on a real canvas.

- **PR:** https://github.com/Cutaiar/hyperspace/pull/217, into `plan-28-30-integration`.
- **Base:** 5ab9458.
  - `git reset --hard` and `git merge --ff-only FETCH_HEAD` were both refused.
  - `git -C <worktree> merge --ff-only origin/plan-28-30-integration` worked.
  - `origin/plan-28-30-integration` at d5d905f (D2) was merged in before the PR. It does not touch any file N3 edits.
- **Commits:**
  - 33d69ea Plan 28 N3: the hand learn's row as one function, learn.row_for
  - 0001874 Plan 28 N3: editing the modulation on the canvas, Learn from a port
  - 695a9b3 Merge remote-tracking branch 'origin/plan-28-30-integration' into plan-28-n3-edit-modulation

## What was built
The PR body and `decisions/N3.md` §3 describe it in full.

- **`graphview.Edit`** has these requests: `connect`, `refusal`, `disconnect`, `insert_modifier`, `add_modifier`, `remove_node`, `show_macro`, `move`.
  - Each one returns one of three things: the table method's own return value; a `Refusal`, which is a `str` holding the words to show; or an `Ask(old, new, commit)`, which becomes ROUTING's prompt via `ui_routing.ask`.
  - Every edit is made through the table's own methods: `add`, `replace_owner`, `move_route`, `remove`, the learns' `learn_control` / `learn_pad_button` (which use `bind`), `add_modifier` / `set_modifiers` / `remove_modifier`, and the macros' subs (the same two lines ROUTING uses).
- **`learn.row_for`** is the hand learn's op/depth table, moved out of `Learn._row`, which now just calls it.
- **`ui_graph`** has:
  - `_create` / `_delete`, dispatched by type through the `CREATE` / `DELETE` dicts;
  - `_menus`, the four right-click menus;
  - `_pin_menu`, which reuses `Panel._ctx_learn`;
  - `picker`;
  - `dropped`, which inserts a modifier dropped onto a cable;
  - page functions that each name one undo step;
  - the last refusal shown on the page's head.
- **New state keys** are added with `setdefault`: `note`, `pin_xy`, `menu`, `menu_at`.

## The seam with N4
- **In `graphview.Edit`:** any request touching a render pin type (`rout:` / `rin:`, or `image` / `geometry` / `mask`), a `render` cable, or a render/output node calls N4's methods **by name** through `Edit._render`. Until those methods exist the request is refused with "render cables: not yet". The names are:
  - `wire(src, dst)`
  - `unwire(cable)`
  - `remove_render_node(nid)`
  - optionally `wire_refusal(src, dst)`, for the words shown during a drag
- **In `ui_graph`:** these entries point at refusing handlers, and N4 replaces them:
  - `CREATE[graphview.IMAGE | GEOMETRY | MASK]` → `_render_drag`
  - `DELETE["render"]` → `_render_cut`
- **Node delete:** the node branch of `_delete` accepts only modifier and macro nodes. N4 extends that branch for render nodes.
- **N3's own functions:** none of them needs to change when N4 lands.

## Tests
`tests/test_graph_edit.py` has 14 tests:
- the eight named in the brief;
- `test_render_pins_are_n4s_and_refused_in_words_until_then`
- `test_nodes_the_picker_adds_and_delete_removes`
- `test_the_page_draws_with_its_editing_menus`
- `test_cable_near_follows_the_widgets_curve`
- `test_create_and_delete_open_only_in_the_typed_dispatch`
- `test_a_route_from_the_canvas_is_a_performer_row_in_the_preset`

N2's `test_the_page_is_read_only` is removed (its own docstring said N3/N4 open create/delete). It is replaced by the dispatch-pin test above.

## Gate results
```
uv run pytest -q                              2340 passed, 2 skipped in 166.53s   (2336 before merging D2)
uv run ruff check .                           All checks passed!
uv run pytest tests/test_golden_frames.py -q  7 passed in 20.42s
windowed smoke: HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<worktree>/.sdd/home (every [[devices]] off, no [library], dream off)
  uv run python .sdd/smoke_edit.py -ApplePersistenceIgnoreState YES   (wraps app.main; GRAPH opened on frame 2;
  ui_graph.connect / insert_modifier / a refused connect called in the live draw loop)
  N3 smoke: [('connect', 'Binding', "Binding(source='lane:1', target='view.bright', op='position'"),
             ('insert', 'Modifier', "Modifier(id='mod.1', kind='smooth', inputs=('lane:1',), para"),
             ('refused', 'Refusal', 'a band sets no base; aim at mod')]
  N3 smoke: frames 120; stall.log empty
git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py   (empty)
```

## Files changed
- `hyperspace/graphview.py`
- `hyperspace/ui_graph.py`
- `hyperspace/learn.py`
- `tests/test_graphview.py` (one test removed)
- `tests/test_graph_edit.py` (new)

No fixtures were added and no docs were edited.

## Self-review findings and concerns
1. **No real drag yet.** The live widget gestures have not been exercised. These are:
   - `query_new_link` filling the two `PinId`s;
   - `query_deleted_node` / `_link` looping;
   - the context menus;
   - `imgui.get_mouse_pos()` inside the editor read as canvas units;
   - a node dropped on a cable.

   They run every frame in the tests and the smoke run without a drag and raise nothing. One widget rule was learned that way: `end_create` / `end_delete` assert unless their `begin_*` returned true. Hand checks Y.6–Y.9 cover the rest.
2. **Deviations from the prompt's letter.** Each is recorded in `decisions/N3.md` §4:
   - A pad into `base` uses the pad learn's row (the session's, `bindings.json` written, no undo step) instead of the literal `"abs", layer="preset"`.
   - A `mod` cable follows `learn._row`'s full table, so a centred param gets a push from any source.
   - A macro onto `mod` is refused.
   - The picker labels idle macros, because every macro is already a node.
3. **Moving a cable's end is a convention of mine.** A drag from a patched input pin to another input pin moves the cable, because the widget cannot pick up a link. The source end cannot be moved by dragging.
4. **Small model edits.** `graphview` now imports `learn`, and `VPort` gains `bipolar`. These are small additive edits to N2's model that N4 may touch nearby.
5. **The private Learn's success words are lost.** The canvas's setter path uses its own `Learn` instance so it does not disturb the panel's armed learn. As a result, its "learned …" words are not shown anywhere.

## Fix round 1 (review of 695a9b3; head now d125859)

Commit: d125859 `Review: N3 round 1 — one road for a modifier's input and a macro's removal, node deletes by kind`.

1. **decisions/N3.md**: two register-row drafts added. One is "A macro dropped on `mod` is refused in words"; it records the departure from the design's first sentence and why. The other is "Deleting a macro node clears its label and every subscriber".
2. **`Bindings.set_modifier_input(mid, k, source, reg)`** is new in `routing.py`. Both `ui_routing.set_modifier_input` and `graphview.Edit.set_input` call it; the undo push stays with the callers.
3. **New test `test_undoing_an_insert_is_one_step_the_modifier_gone_the_route_as_it_was`**. On the `test_undo` boot rig, one step undoes the insert: the modifier is gone and the route's source, op, depth and `rest` (None) are back.
4. **A macro node's delete** goes through `table.set_macros({k: v for k, v in macros_doc().items() if k != nid}, reg)`. Covered in `test_deleting_a_node_dispatches_by_kind`.
5. **`ui_graph._delete`'s node branch** now dispatches through `DELETE_NODE` by kind:
   - `modifier` and `macro` go to `_value_node_cut`;
   - `render` and `output` go to `_render_node_cut`, which says "render cables: not yet". N4 replaces these entries.
   - any other kind goes to `_rig_node_cut`, which says NOT_REMOVABLE.

   The test is `test_deleting_a_node_dispatches_by_kind`. The dispatch-pin test is updated: `accept_deleted_item` is called only in `_value_cut` and `_value_node_cut`.
6. **`Edit._cable_at`**: on a `mod` stub it now prefers the cable of `table.owner(pid)`. Test: `test_a_move_picks_up_the_performer_not_a_sleeping_route`.
7. **New `Panel._ctx_learn_block(a, p)`** in `ui.py` holds the "no learn" / armed hint + Cancel / `_ctx_learn` block. The param menu and `ui_graph._pin_menu` both call it. The redundant `getattr(table, "redraw_serial", 0)` is gone (now `table.redraw_serial += 1`).

Gates:
```
uv run pytest tests/test_graph_edit.py tests/test_graphview.py tests/test_ui_routing.py tests/test_modifiers.py tests/test_undo.py tests/test_learn.py -q   155 passed in 21.84s
uv run ruff check .                            All checks passed!
uv run pytest -q                               2343 passed, 2 skipped in 171.40s
uv run pytest tests/test_golden_frames.py -q   7 passed in 19.66s
```
