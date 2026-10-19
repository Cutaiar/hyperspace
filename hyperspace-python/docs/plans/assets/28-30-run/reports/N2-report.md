# N2 report — the GRAPH page, read-only

**Status:** DONE_WITH_CONCERNS. The concerns are minor and listed below.

- **PR:** https://github.com/Cutaiar/hyperspace/pull/215, into `plan-28-30-integration`.
- **Base:** acc0f7e.
- **Commits:**
  - 2784f53 Plan 28 N2: a layout key in the preset and the show, read on load, written on save
  - 501cdec Plan 28 N2: the GRAPH page, both graphs drawn read-only

## What was built
The PR body and `decisions/N2.md` §3 describe it in full. In short:
- `graphview.py` is the model. It has no imgui. `OWNERS` is the one table that decides which render node owns a param, and `device_node` is the single function that turns a device into a node (N5 extends it).
- `ui_graph.py` is the page, drawn on `imgui_node_editor`.
- `preset.LAYOUT_KEY` and `library.LAYOUT` hold node positions, in the preset and in the show.
- `Panel.close` and `Panel._page_graph` are new, and the page is added to `PAGES`.
- `ui_fx.strip` was factored out of the FX page.
- SYSTEM gets a line with the GRAPH page's draw time.
- `hotreload.MODULES` gains the two new modules.
- The panel was added to both close lists in `app.py`.

## Headless
`imgui_node_editor` runs fine under the test harness: it lays out nodes, and answers selection and position queries. So the page is drawn for real in:
- `test_ui_shell::test_every_page_draws_with_a_library`, which now includes GRAPH;
- six page tests in `tests/test_graphview.py`: selection, drag-to-layout, tidy, reload, close, and read-only.

## Tests
`tests/test_graphview.py` has 14 tests: the seven named in the brief, plus page draw, dropped-node layout, the context lifetime across a reload and close, "one table", read-only, page order, and no imgui import.

## Gate results
```
uv run pytest -q                              2305 passed, 2 skipped in 170.49s
uv run ruff check .                           All checks passed!
uv run pytest tests/test_golden_frames.py -q  7 passed in 20.05s
windowed smoke (.sdd/smoke_graph.py wrapping app.main, GRAPH page open, 240 frames,
  scratch home with every device disabled, no [library]): exit clean, stall.log empty,
  graph page median 2.32 ms / p90 2.40 / max 2.51 (53 nodes, 228 cables)
diff --stat on library/, apc40.py, midi.py: empty
```

## Files changed
- new: `hyperspace/graphview.py`, `hyperspace/ui_graph.py`, `tests/test_graphview.py`
- modified: `hyperspace/ui.py`, `ui_fx.py`, `preset.py`, `library.py`, `app.py`, `hotreload.py`

## Concerns
1. **Expected integration overlaps.** D1 also edits `preset.py` and `ui.py`. My changes there are additive: the `LAYOUT_KEY` block, load step 6½, the tail of `document`, the `signature` tuple, the `PAGES` row, `close`, `_page_graph`, and the SYSTEM line. I also factored `ui_fx.strip` out of the bottom of `ui_fx.page`. D2 edits the status line at the top of that same function, so there may be a nearby text conflict, but the edits do not overlap.
2. **Selection pane placement.** The selection pane sits beside the canvas only when the page is at least 720 px wide; otherwise it goes below the canvas. The design says "side column". I deviated because the default page is about 420 px wide.
3. **Not drawn.** Sink rows are not drawn. A route's `scale` and `when` appear in its hover text, not as cables. The `setter` cables from the APC40 desk are numerous; N5 is the work package that splits the desk into two nodes.
4. **Not undoable.** Undo does not restore node positions.
5. **Not yet verified.** The stream-N smoke run (an LFO owning another LFO's depth, two modifiers, a dragged cable) is for after N3. N2 ran with a factory preset only.
6. **`devices` import.** `graphview` does not import `devices`; it reads devices through the protocol. The brief listed `devices` among its imports.


## Fix round 1 (review of 501cdec; head now 69de19a)

Commits: 449467b (the merge of `origin/plan-28-30-integration` at 7b78035), 69de19a (`Review: N2 round 1 …`).

- **A. Merge.** `origin/plan-28-30-integration` (7b78035, with D1) was merged in plainly. It auto-merged with no conflicts in `preset.py` or `ui.py`; both sides are kept and no line of theirs was touched. New test: `test_a_d1_placed_effect_from_a_real_spec_is_an_effect_node_with_image_cables`. It reads `tests/fixtures/presets/palette-hands.json` → `read_graph` → `default_graph(spec.wiring())` and checks four things:
  - `render:palette` is an `Effect` with `placed == "after"`;
  - its input is `rout:hands` → `rin:palette/image`;
  - its output cables are image cables;
  - `fx.palette.mix` sits on it.
- **B. Layout in the undo marks.**
  - `library.Marks.take` gains a sixth element, a copy of `Presets.layout`; `put` restores it.
  - `Project.mark` gains `layout` and `_saved_layout` as elements 10–11; `remark` restores them, and still reads a 10-element mark.
  - `Marks.put` also gives the same show its layout back. That is what lets a tidy be undone.
  - Test: `test_undoing_a_load_puts_the_earlier_layout_back`. For a preset load and for a show load, undo leaves `layout == {}` and nothing dirty.
- **C1/C2.** New functions `route_said` and `sub_said`. `refresh` now recomputes each route's depth and hover words, and each subscriber's words, every frame. `key` no longer includes `b.value`. Test: `test_a_route_depth_follows_its_macro_and_its_slider_without_a_rebuild`.
- **C3.** New `graphview.visible` and `grouped`. `height(n, full, folds)` and `auto_layout(view, placed, expanded=, folds=)` count a node's own expand and folds, and the page passes its state in. Test: `test_an_expanded_node_pushes_its_column_down`.
- **C4.** New **beside** chip (`st["beside"]`): the selection pane goes below the canvas by default and beside it when the chip is on or the page is at least 720 px wide. Y.4 now says CONTROLS is 540 px and must be widened to give both room. The register row is updated.
- **C5.** Tidy is one undo step: `ui_graph.forget` → `undo.push("tidy the graph", load=True)`, with no confirm. Test: `test_a_tidy_is_one_undo_step`.
- **C6.** One line in the row: setter cables are faint, not dashed, because `ed.link` cannot dash.
- **C7.** `_state` now fills each of its keys with `setdefault`.
- **C8.** `test_ui_shell.build_rig` calls `panel.close()` in its teardown, before the imgui context goes. That covers every test on that rig, `test_graphview` included.
- **C9.** `render:eye` stays in the preset map. Its ports are `camera.*`, which are performance params; `eye.*` is session and not modulatable. This is stated in the row.

Gates:
```
uv run pytest tests/test_graphview.py tests/test_ui_shell.py tests/test_undo.py tests/test_presets.py tests/test_fx.py tests/test_graph_placement.py tests/test_library.py -q   341 passed
uv run ruff check .                            All checks passed!
uv run pytest -q                               2323 passed, 2 skipped in 174.55s
uv run pytest tests/test_golden_frames.py -q   7 passed (580 goldens match)
```
`tests/test_ui.py` does not exist; the shell harness is `tests/test_ui_shell.py`, which was run instead.
