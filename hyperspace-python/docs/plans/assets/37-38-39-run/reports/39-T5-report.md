# 39-T5 report: GRAPH and the pages

**Status:** DONE_WITH_CONCERNS (minor; see Concerns)
**PR:** https://github.com/Cutaiar/hyperspace/pull/267 (`plan-39-t5-graph` → `plan-39-vision`)
**Base:** 8a56a20, confirmed. I used `git merge --ff-only FETCH_HEAD` from a clean tree, then ran `uv sync`.
**Decisions file:** /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/39-T5.md

## Commits
- b2ac105 Plan 39 T5: GRAPH — segment under media, a masks group, the cut-out starter, mask cables purple
- 442cd89 Plan 39 T5: the GRAPH tests — picker, cut-out starter, mask cable, segment.N pins, words, /7 round trip

Both commits end with common.md's lines (Claude Fable 5.1), as the dispatch said.

## What I built (`hyperspace/graphview.py` only)
1. **The picker.**
   - `PICKER_GROUP`: `segment` is under "media", a new heading, because W6 names MEDIA and the picker had none. `matte` and `cut` are under "masks".
   - The picker has an item for each of the three.
   - `render_add` has a branch for each (`ADD_SAID` gives the words). `_fresh` names each new node past any instance a wire already names.
2. **The cut-out starter.** It wires `channel.a → <seg>.image`, `<seg>.fg → <comp>.over`, `scene → <comp>.under` and `<comp> → output.all.image`.
   - It makes a new segment and a new composite each time and is never refused.
   - It is laid out left to right from where you clicked: the scene first if it is new, then the segment, then the composite.
   - Its words name what fed All outputs before (`STARTER_REPLACED`, via `_was_into`). The scene chain now does the same (plan 36's follow-up).
   - When no shape is wired into the scene, the words say `scene.geometry` is left unwired. No shape is added.
3. **Cable colour.** A section wire's `VCable.type` is MASK when its source pin is a mask, so a promoted cable is purple into a red port. `ui_graph` is untouched.
4. **`segment.N` pins.** There is a `segment` case for every instance's `fg`/`bg`/`mask` pins. The `PINS` loop skips segments, so instance 1's ports are unchanged.
5. **`said` for stand-ins.** `_stand_in` gives the matte, cut and segment their words (`STAND_IN_SAID`) from the wires into them. A built node keeps its own words. `summary` is unchanged.
6. **FX page.** Nothing to do: `edges` is an effect file like any other. A test checks the picker and `ui_fx.groups`.

`LABELS`, `HOVERS`, `OWNERS` and `FRAME_CLASS` were already complete from T2–T4. A test now checks `OWNERS` (params as ports) for `matte`, `cut.2` and `segment.2`.

## Tests
`tests/test_plan39_graph.py` has 20 tests:
- the picker groups;
- each add, for the three kinds;
- skipping a name a wire already says;
- the cut-out starter: on the scene chain, on a blank preset, a second use refused nothing, and placement;
- the scene chain naming what it replaced;
- the purple promoted cable, and segment.mask purple with fg red;
- `segment.2`'s pins and cables;
- `segment`'s pins drawn once;
- `OWNERS`;
- the stand-in words, unwired and wired-but-unreached;
- a built node's own words;
- the `/7` round trip of matte, cut, segment and segment.2 with values;
- `edges` on the FX page.

Changed tests, one reason each:
- `test_graph_edit::test_the_picker_groups_by_primitive`: the list gains the three, and the groups gain media and masks.
- `test_graph_starters::test_the_starters_are_their_own_submenu_first`: gains cut-out.
- `test_graph_segment::test_the_canvas_knows_the_segment`: the group is media.

Gates:
- `uv run pytest -q` → `4104 passed, 2 skipped in 46.39s` (base 4084 + 20)
- `uv run ruff check .` → `Found 25 errors.`: the base's own. Every touched file passes ("All checks passed!").
- `uv run pytest -q --all tests/test_golden_frames.py` → `136 passed in 8.86s`. No golden moved or added.
- `uv run pytest -q --all` → `1 failed, 4325 passed, 2 skipped in 81.98s`. The failure is `test_migrate_library::test_the_real_picture_check_passes_an_old_preset` ("cannot create vertex array"): GL under xdist load. Run alone, `uv run pytest -q --all -n0 tests/test_migrate_library.py` → `9 passed`.

## Files changed
- hyperspace-python/hyperspace/graphview.py
- hyperspace-python/tests/test_plan39_graph.py (new)
- hyperspace-python/tests/test_graph_edit.py
- hyperspace-python/tests/test_graph_starters.py
- hyperspace-python/tests/test_graph_segment.py

## Self-review
- No file outside the ownership table is touched. `graph.py`, `hold.py`, `app.py`, `ui_graph.py`, `_node`, `_head` and `summary` are untouched.
- The WYSIWYG rule holds. The starter wires only W6's four wires, and every wire is drawn, including those of `segment.N`. Nothing is filled in: no shape is added on a blank preset, and the words say so.
- Instance 1's segment pins keep their ids, labels and order (`test_segment_one_s_pins_are_drawn_once`).

## Concerns
1. **A mask cable is no longer IMAGE-typed** (row 4td). `ui_graph` keys "insert effect ▸", "starters ▸" and drop-onto-cable on `c.type == IMAGE`, so a promoted mask cable into a picture port loses those menus. The backward-wire layout rule (`graphview` `c.type == IMAGE`) also skips it. This follows from the brief's rule. If the menus are wanted on it, the change is in `ui_graph` (plan 37/38's file).
2. **The media ▸ heading is new and holds only the segment.** The channels' switch stays under pictures ▸ (row 4ta).
3. **`ui_graph.render_picker`'s docstring** does not mention media ▸ or masks ▸ (a plan 37/38 file). Left as is.
4. **The cut's stand-in says "through, whole"**, the repo's word, not the brief's "through, untouched" (row 4tf).

---

## Fix report (review round 1)

**Commit:** ee302ed Plan 39 T5 review: a promoted mask runs back into a taker like a picture; _fresh dropped. It carries common.md's attribution lines and is pushed to PR #267.

1. **`returns()`.** The `TAKEN_BACK` rule now accepts `c.type in (IMAGE, MASK)`. New test: `test_a_promoted_mask_into_a_switch_left_of_it_runs_back_by_design`. It wires `lookback → matte → switch.in1`, with the matte in the effects area and the switch in media, and checks that the cable is one of `returns`.
2. **The `_fresh` test.**
   - A wire-only name does not survive loading: `read_graph` drops a wire to an undeclared `segment.2` as a note. So `_fresh`'s skip loop was dead code.
   - I removed `_fresh`. The adds and the cut-out starter now use `_next`, as the composite does.
   - The test is renamed `test_a_new_one_is_past_the_highest_instance_declared`. It checks that the next add is segment.3 when segment.2 is declared, and that a wire-only `segment.4.fg` lands as a note with no wire.
3. **Decisions file.**
   - Row 4td now says that insert-effect, the starters and drop-onto-cable on a promoted mask cable need two changes: `graphview._cable_ends` (which refused these even before T5) and ui_graph's `c.type` checks. It is marked as a row for the docs task.
   - It notes the `returns` fix.
   - §4 notes that `render_picker`'s docstring lacks media ▸ and masks ▸ (docs task or a later pass), and records why `_fresh` was dropped.
   - Row 4ta's wording is updated to say `_next`.

**Tests:**
- `uv run pytest -q -n0 tests/test_plan39_graph.py tests/test_graphview.py tests/test_graph_areas.py tests/test_graph_starters.py` → `87 passed, 1 deselected`
- `uv run ruff check hyperspace/graphview.py tests/test_plan39_graph.py` → `All checks passed!`
- `uv run pytest -q` → `4105 passed, 2 skipped`
