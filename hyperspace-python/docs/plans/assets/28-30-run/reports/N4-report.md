# N4 report — the render graph edited as nodes and a wire list, outputs as nodes

**Status:** DONE_WITH_CONCERNS. The concerns are below; none blocks the merge.

- **PR:** https://github.com/Cutaiar/hyperspace/pull/219, into `plan-28-30-integration`.
- **Branch:** `plan-28-n4-edit-render`.
- **Base:** `5ab9458`. `origin/plan-28-30-integration` at `d5d905f` (D2) was merged in before the PR, with no conflicts.

**Commits:**
- dba771a Plan 28 N4: the preset's graph is nodes plus a wire list, outputs as nodes
- 41dcb94 Plan 28 N4: render edits on the GRAPH page — wire, unwire, the picker, delete
- 267fc1c Plan 28 N4: the two wire fixtures, their goldens (N4 fixture, new), the tests
- 2435797 (merge of origin/plan-28-30-integration, D2)
- d7af1b3 Plan 28 N4: the FX page's placed chips say where a wire puts an effect

## What was built
The PR body and `decisions/N4.md` §3 describe it in full. In short:

- **The wire list.** `graph.Wire(src, dst)` is JSON `{"from", "to"}`, held in `GraphSpec.wires`.
- **Reading.** `read_graph` reads `wires`. Each refusal is a note ("; the default wiring") and that port keeps its default. The refusals are: a wrong type, a missing port or node, two wires into one port, an effect that D1 already places, an unfed effect wired into more than one port, and a loop.
- **D1's keys as wires.** `d1_wires` reads D1's `after` / `into` as wires. `split_wires` turns the wires D1 would write short into placements, so D1's builder does them. The rest are built as edges by `_Wiring` in `default_graph`.
- **Outputs as nodes.**
  - `output.<n>.image` shows the wired picture through `graph.Wired`, the output's own `Fx`-like end.
  - `.hands` lays the wired layer over (with its guide); `.readout` gives the wired layer's guide.
  - An output no wire names is node for node the default.
- **The graph key.** The wires ride in `Wiring`, which is the renderer's graph key.
- **Composites.** `CompositeAt` (node kind `composite`) is a composite the picker adds, fed and read by wires.
- **The editor model.** `graphview.Edit` has `wire`, `unwire`, `add_node`, `drop_node` and `set_node`, plus `spec_name` (canvas pin → the preset's name) and `picker`. Each edit is read back through `read_graph` (a refusal is the note's words, nothing changed), then one undo step, then `GraphSection.land`.
- **The canvas.** `ui_graph` opens begin_create / begin_delete through one dispatch (`CREATE` / `DELETE_CABLE` / `DELETE_NODE`). A wrong drag goes red with the note's words. Right-click opens the picker on the canvas and a menu on a node.
- **Words.**
  - OUTPUT / LOOKBACK: `output_shows`, `history_words`, `graph_words`, `wire_words`.
  - The FX page's chips: D2's `placed_chips`, extended in its one function.
  - `preset.dumps` writes one wire per line.

## The seam with N3
`ui_graph` dispatches a drag by the cable's port type:
- `CREATE[type]`: image, geometry and mask are N4's (`_create_render`).
- `DELETE_CABLE[cable kind]`: `"render"` is N4's.
- `DELETE_NODE[node kind]`: `"render"` / `"output"` are N4's.

N3 adds its value / trigger entries, cable kinds and node kinds beside these. `ends()` gives a mixed pair the render type, so the render edit words the refusal.

`graphview.Edit` is a dataclass with N4's fields (`graph`, `render`, `push`, `said`) and five thin methods, each calling a module function (`render_wire`, `render_unwire`, `render_add`, `render_drop`, `render_set`). N3's `connect` / `disconnect` / `insert_modifier` / `add_modifier` / `remove_node` go beside them, with its own fields (`table`, `reg` …) defaulted.

Expect a textual conflict at:
- `class Edit`'s header and fields;
- the `_canvas` call list (`_create`, `_delete`, `_menus`);
- `_state`'s `setdefault` lines.

I named the node delete `drop_node` so it does not collide with N3's `remove_node`. N4's methods and the module functions are separate, so resolving the conflict means keeping both sides.

## Tests
`tests/test_graph_wires.py` has 15 tests: the brief's eight, plus these seven:
- an edit lands and refuses;
- one undo step;
- the fixtures load clean;
- the words;
- a wired output's pixels (history wired into output 2 is byte for byte the chain-less frame, and output 1 is byte for byte the default);
- hands 2 on the glass (GL);
- the renderer rebuilding on an edit (GL).

`test_hands_as_lines_through_the_acid_with_tracers_by_wires_alone` builds the spec with `Edit` calls (a geometry drag `ghost → scene.geometry`, then `set_node(draw="lines")`). It asserts the same graph as `hands-lines.json`, and the same pixels over three frames with the look-back on.

## Gates
```
uv run pytest -q                                2342 passed, 2 skipped in 175.31s
uv run ruff check .                             All checks passed!
uv run pytest tests/test_golden_frames.py -q    7 passed in 22.10s
uv run python tools/golden_frames.py (before recording)   16 of 596 frames moved — all 16 "no golden" (the new fixtures); the 580 matched
git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py   (empty)
```
After recording, `frames.json` has insertions only (335 lines), and there are 4 new PNGs. No existing hash changed.

## Files changed
- **Modified:**
  - `hyperspace/graph.py`, `graphview.py`, `ui_graph.py`, `preset.py`, `ui.py`, `render.py` (docstring only);
  - `tools/golden_frames.py`;
  - `tests/test_golden_frames.py` (the count), `tests/test_graphview.py` (the read-only test, now the dispatch test);
  - `tests/golden/frames/frames.json`.
- **New:**
  - `tests/test_graph_wires.py`;
  - `tests/fixtures/presets/hands-glass-only.json`, `wired-outputs.json` (force-added);
  - 4 PNGs under `tests/golden/frames/png/`.

## Concerns
1. **The golden route for a wired output reads `none`.** `test_golden_frames` allows only `NAMES` or `none`, and the prompt lets that test change only by its count, so the tool maps a `Wired` key to `none`. The manifest's fixture `graph` says what the wire is. This is registered as a rough edge.
2. **One assertion outside my files changed.** N2's `test_the_page_is_read_only` is now `test_the_page_edits_only_through_its_dispatch` (N2's docstring said "N3 and N4 open them"). N3 will meet the same test: its create / delete calls must sit in `_create` / `_delete` / `new_link` or a handler named in the allowed set. N3 may need to add its handler's name there.
3. **No real-mouse verification.** The canvas drag is tested with the widget's `new_link` / `begin_create` stubbed, because a headless node editor cannot be dragged. A real-mouse check is Y.1. The windowed smoke run was not done; the dispatch did not ask for one, and it belongs to stream N after N3.
4. **This binding's `end_create` / `end_delete` assert unless `begin_*` returned True.** They are called inside the `if`, and a code comment says so. N3 should follow the same pattern.
5. **`ghost.2.on` defaults off at the machine.** In `hands-glass-only`, hands 2 shows only once ghost.2 is switched on (HANDS). The golden tool switches it on.
6. **The prompt's `default_graph(…, wires)` signature was not used.** D0 had taken the fourth argument (`effects`), so the wires ride in `Wiring`. The design's intent holds: the graph key changes with the wires.

## Decisions file
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N4.md` has:
- 7 register-row drafts;
- hand checks Y.1–Y.5;
- as-built notes;
- departures from the documents.

## Fix round 1 (review of d7af1b3; head now 6a8e1ee)

Commits:
- f85d29f merges `origin/plan-28-30-integration` at d94115e (N3), resolved as the review said.
- 6a8e1ee "Review: N4 round 1 — wired hands laid as their node, a through output's hands replaced, minors".

### IMPORTANT 1: a wire into `output.N.hands` from anything but a hands layer
- **The fix.** `Output.run` now lays through the node whenever `laid[0]` is not a `HandsLayer`, and a presenter gets `hands_tex = laid[0].image(frame)`. `wire_error` refuses `history → output.N.hands`.
- **Test:** `test_a_composite_wired_into_an_outputs_hands_is_laid_as_its_own_picture`. It wires a composite of the scene under and the hands over into output 2's hands, on an output with scene and hands off, and checks:
  - output 2's pixels are within 2 of output 1's (scene with the hands over);
  - a presenter's `handoff.hands` is the composite's own frame texture, not `r.ghost.tex`;
  - the history refusal's words.

### IMPORTANT 2: a hands wire on a through output
- **The fix.** `_Wiring._put`'s hands branch walks any folds on the image port. If the picture is a through end (an `Fx` whose source lays a layer), the picture is moved to that end's fallback: the scene's end, or the ground. The wired node alone is then laid over.
- **Test:** `test_a_hands_wire_on_a_through_output_replaces_the_switch_hands`, with `S(through=True)` and `S(scene=False, through=True)` and warp on. It checks:
  - in the graph, output 2 reads `fx` with hands over, and output 3 reads the ground with hands over;
  - output 2 is byte for byte output 1 (`S()`);
  - the routes are `[(SCENE, True), (None, True)]`;
  - `chain_runs == 1`.
- **Register row:** "A `hands` wire on a through output replaces the switch's hands".

### IMPORTANT 3: the merge, resolved exactly as instructed
- **`graphview.Edit`.**
  - It is N3's class, with its positional `(table, reg, router, view, profile)`; `table` and `reg` default to None.
  - It takes keyword-only `graph`, `render` and `push`, and sets `self.said = ""`.
  - It has N4's `wire` (with `dry`), `wire_refusal`, `unwire`, `add_node`, `drop_node`, `remove_render_node = drop_node` and `set_node`.
  - My dataclass `Edit` and my duplicate `RENDER_TYPES` are gone.
  - `_render` wraps a plain `str` result as a `Refusal`.
  - `edit_of` passes `graph` and `render` (with `push=None`).
- **`ui_graph` tables.**
  - `CREATE` is N3's dict, with the three render types on `_create_render`. `_create_render` orders the pins itself (`Edit.ordered`).
  - There is one `_create`, N3's, which now asks `new_link()`, so the drag test can stub it.
  - `DELETE` is N3's name: `"render"` → `_delete_render_cable`.
  - `DELETE_NODE`: `"render"` / `"output"` → `_delete_render_node`.
  - Unknown kinds → `_unknown_cut` (rejects).
  - `_render_drag`, `_render_cut` and `_render_node_cut` are gone.
- **The delete contract is N3's.** The handlers accept or reject the item themselves:
  - `_delete_render_node` calls `accept_deleted_item(False)` on success, and records the node in `st["dropped"]`. `_delete` resets that set each time it opens.
  - `_delete_render_cable` accepts a cable of a node just dropped, saying nothing, so the node's note is not overwritten.
- **Undo.** Render handlers do not go through `_act`. `render_edit`'s `Edit` pushes `undo.push(label, load=True)` only after the read-back accepts the edit.
- **Menus.** There is one N3 `MENU` popup. My two popups and the second pair of `show_*_context_menu` calls are gone.
  - N3's `picker` calls `render_picker`: `effect ▸ <file>`, `hands`, `composite`.
  - `_node_menu` calls `render_node_menu` for render and output nodes: draw solid / lines, a composite's blend, delete.
  - `_cable_menu`'s delete on a render cable is `unwire`.
  - `st["menu_node"]` is removed.
- **The head line.** Refusals go to `st["note"]` (WARN). `st["said"]` is the success line, shown when there is no note. `_state` uses N3's `EDIT_STATE` plus `said`.
- **The call list.** `_canvas` calls `_create`, `_delete`, `_menus`, `_hover`, `_moved` once each, in N3's order.
- **`graphview.spec_name`.** It now refuses the frame's own nodes by name (`shape`, `fx…`, `capture`, `readout…`, `composite(…)`) when there is no built graph to ask. Without this, `render:shape` read as an effect called "shape".
- **Tests.**
  - My `test_the_page_edits_only_through_its_dispatch` is gone. Its asserts are folded into N3's `test_create_and_delete_open_only_in_the_typed_dispatch`, with the allowed sets widened (`new_link`, `_create_render`, `_unknown_cut`, `_delete_render_cable`, `_delete_render_node`).
  - N3's `test_render_pins_are_n4s_and_refused_in_words_until_then` is now `test_render_pins_reach_n4s_methods_and_refuse_as_a_refusal`. It checks that render pins reach N4's methods and that refusals come back as a `Refusal`, including an input-first drag that lands, an unwire, a default-edge refusal and a node refusal.
  - N3's `test_deleting_a_node_dispatches_by_kind` now expects N4's words.

### Minors
1. `Panel.black_outputs` now passes `n=sl.n`.
2. In `tools/golden_frames.py`, only a `wire(...)` key reads route `none`, and any other unknown key raises (`NAMES[key]`). Wired entries carry `"wired": "<from>"`. I re-recorded `wired-outputs` only; the manifest diff is the one inserted key (`"wired": "acid.2"`), and no hash moved.
3. Y.2 is fixed: its fail cause now names A4's layer rule (hands.2 on any scene-off output that lays a layer). The rough edge is added.
4. `test_no_factory_preset_changes` now checks two things:
   - no library file has a `graph` key;
   - over five switch sets, the default graph has no `Wired` end or wire-made composite, no effect placed, nothing dormant, no notes, and every output's image is a pipeline end or the ground.
5. `render_drop` refuses instance 1 of an effect whether it is placed or not ("unwire it to put it back in the chain"). The picker test now covers the placed case.
6. `GraphSection.read` calls `self.files()`.
7. The hands-as-lines test's docstring now says it uses a geometry drag (setting `into`) plus `set_node(draw="lines")`, not image wires. The name keeps the brief's words.

### Gates
```
uv run pytest tests/test_graph_wires.py tests/test_graph_edit.py tests/test_graphview.py tests/test_graph_placement.py tests/test_graph_effects.py tests/test_graph_json.py tests/test_outputs.py tests/test_fx.py -q   295 passed in 16.90s
uv run ruff check .                             All checks passed!
uv run pytest -q                                2360 passed, 2 skipped in 170.18s
uv run pytest tests/test_golden_frames.py -q    7 passed in 20.54s   (596: 580 + 16, none moved)
git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py   (empty)
```
The decisions file has a new row (the through rule), N3-as-merged seam text, an updated Y.2, and new rough edges.
