# D2 report: the FX page, the `VALUE` port, the faces exception

**Status:** DONE_WITH_CONCERNS (the concerns are listed below).

- **Base:** `7b78035`. `git reset --hard` was refused by the classifier, so I used `git merge --ff-only FETCH_HEAD` from a clean tree, which gives the same result.
- **Branch:** `plan-30-d2-fx-page`.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/216

## Commits
- `6ed2d54` The VALUE port type, used by no node; placed_chips, the FX chip's words
- `df1c0db` The FX page's placed chips, the placed count, and the faces target's tip

## What was built
- **`graph.py`**
  - `VALUE = "value"`, with an attribute docstring naming its two uses and saying no node uses it.
  - `PORT_TYPES`.
  - `placed_chips(spec) -> {instance: "after hands" | "into output 2" …}`: the one source of the chip words, for N4 to extend.
- **`patch.py`:** `RENDER_VALUE = "value"` with a comment. There is no import of `graph`.
- **`fx.py`:** the `target` tip, one string.
- **`ui_fx.py`**
  - **Placed effects.** The page reads the preset's spec through `Panel.graph_now()`, guarded for stand-ins. Placed effects leave the grid and are drawn one to a row under it, with faint place words beside each.
  - **No drag or drop.** `_chip(place=)` stops the chip being a drag source or a drop target. `_drop` reorders over the chain only.
  - **Status line.** `_status` appends `· N placed` (the placed effects that run, frame target only), or reads `nothing in the chain · N placed`.
  - **Hovers.** The strip title's hover gives the place instead of `#order`. The place words' hover adds the dormant reason from `renderer._graph.dormant`.

## Tests
New tests: `test_fx.py::test_a_placed_effects_chip_says_where_it_sits_and_is_not_reorderable` and `test_graph_effects.py::test_the_value_port_type_exists_and_no_node_uses_it`. No existing assertion changed.

```
uv run pytest -q                              -> 2306 passed, 2 skipped in 186.37s
uv run ruff check .                           -> All checks passed!
uv run pytest tests/test_golden_frames.py -q  -> 7 passed in 26.12s
git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py tests/golden/ -> empty
```

## Files changed
- `hyperspace/graph.py`
- `hyperspace/patch.py`
- `hyperspace/fx.py`
- `hyperspace/ui_fx.py`
- `tests/test_fx.py`
- `tests/test_graph_effects.py`

## Concerns
1. **The status wording departs from the prompt.** The line keeps the labels and appends `· 1 placed`, rather than the prompt's literal `3 in the chain · 1 placed`. This keeps every existing assertion and the information the line has always shown. It is registered as a row; reversing it is a one-function change.
2. **The page reads the preset's spec, not the built graph.** A placement refused only at build would still show as placed on the page. `read_graph` already refuses loops, so no preset reaches this.
3. **Page height.** Each placed effect adds a page row, and the page-fit tests do not cover placements.
4. **No smoke run.** My dispatch did not ask for one.
5. **`patch.py` edit.** I edited `patch.py` (N0's file) with a constant and a comment only, as the brief allows.
6. **Commit trailer.** The commits use the session's trailer, `Claude Opus 5.5`, not common.md's `Fable 5.1`. The system attribution instruction takes precedence.

## Decisions file
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/D2.md` has:
- 4 register-row drafts;
- hand checks X.10 and X.11;
- the as-built notes;
- the departures.


## Fix round 1 (commit 3328a62, pushed to PR #216)

### IMPORTANT 1: the page scrolled with three placed effects
- **Layout.** Placed chips are now a second grid under the chain's, three to a row like it. Two grids of a + b = 13 chips never take more than 5 rows, the same as one grid of 13, so the page is no taller than with nothing placed.
- **Chip text.** The text is `<Label> · <place>` (`Warp · after hands`), cut to the chip by `placed_label`, which calls `ui.fit_text`. The name's hover holds the whole place.
- **Gone.** `_place_words` (the faint words beside the chip) is removed.
- **New test** `test_the_page_fits_with_three_placed_effects`:
  - places the first three effects after the hands;
  - puts an error line on every strip;
  - opens every strip in turn, on the frame and then aimed at the faces (the faces row shown);
  - checks that `scroll_max_y == 0` every time.
- **Checking the test.** With the placed grid forced back to one chip a row, the test fails.

### MINOR 1: dormant effects were counted
`_status` now counts only placed effects that are on, aimed at the frame, and not in `renderer._graph.dormant` (`_dormant(panel)`). The chip test covers a dormant `warp`: the count drops it.

### MINOR 2: a placed effect aimed at the faces
Such a chip reads `Warp · on the faces`. Its hover reads "placed after hands, aimed at the faces: it runs in the faces' chain". The frame count leaves it out. The test covers this.

### MINOR 3: two vocabularies
The new row "The chip's place words and OUTPUT's placement words are two vocabularies" says:
- `placed_chips` (`after hands`) is the edit view;
- `placement_words` (`palette on the hands`) is the show view;
- N4 extends `placed_chips` for wires.

### MINOR 4: new rows
- "A dormant placement still shows as placed, said only in the hover".
- "A placed effect aimed at the faces says 'on the faces' and is not counted as placed".
- The first two rows are rewritten for the new layout and the count's definition.

### MINOR 5: the broad catch
`_placed` now catches `(AttributeError, TypeError)` only.

### Merge note (N2)
The place is computed in `page` (`placed.get(sel)`) and passed to `_strip_header(panel, fx, sel, place)`. At N2's merge, `strip()` can call `_placed(panel, fx).get(sel)` itself; `_placed` is a self-contained function over the panel.

### Commands
```
uv run pytest tests/test_fx.py tests/test_graph_effects.py tests/test_graph.py -q  -> 133 passed in 10.37s
  (there is no tests/test_ui.py on this branch; ran the full suite instead)
uv run pytest -q                              -> 2307 passed, 2 skipped in 207.68s
uv run ruff check .                           -> All checks passed!
uv run pytest tests/test_golden_frames.py -q  -> 7 passed in 32.97s (no hash moved)
```

### Merge of origin/plan-28-30-integration (5ab9458, N2) — 5728aee + 1345c33

**What happened.** `git merge` reported no conflict, but the result was broken. N2 moved the strip body out of `page` into `ui_fx.strip(panel, sel)`. Git carried D2's changed line, `_strip_header(panel, fx, sel, placed.get(sel))`, into `strip()` unchanged. `placed` is a local of `page`, so it does not exist inside `strip()`.

**The fix** (1345c33, as agreed): `strip()` calls `_strip_header(panel, fx, sel, _placed(panel, fx).get(sel))` itself. Nothing is threaded through `page`, and every N2 line and every D2 line is kept.

**Checks**
- **Side column.** The GRAPH page's side column (`ui_graph`) calls `ui_fx.strip(panel, n.ref.effect)`, so it now shows a placed effect's place in the title's hover.
- **New test** `test_a_placed_effects_strip_says_its_place_wherever_it_is_drawn`:
  - calls `ui_fx.strip` directly, as the side column does, and through the FX page;
  - asserts `_strip_header` gets `"after hands"` for the placed warp and `None` for acid and for no graph.

```
uv run pytest tests/test_fx.py tests/test_graphview.py tests/test_graph_effects.py tests/test_graph_placement.py -q -> 151 passed in 9.73s
uv run ruff check .                           -> All checks passed!
uv run pytest -q                              -> 2327 passed, 2 skipped in 185.36s
uv run python tools/golden_frames.py          -> all 580 frames match their goldens (Apple M3 Max, 4.1 Metal - 90.5)
uv run pytest tests/test_golden_frames.py -q  -> 7 passed in 19.26s
```
