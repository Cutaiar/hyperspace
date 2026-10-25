# N1 report — modifier nodes, in the preset

**Status:** DONE_WITH_CONCERNS (the concerns are below; none blocks the work)
**Branch:** `plan-28-n1-modifiers`, base 5d18192 (`git log --oneline -1` after the reset: `5d18192 Merge plan-28-30-prompt …`). The integration branch had not moved when I re-fetched before the PR.
**PR:** see the end of this file.

## What I built
These are the files in the order the N1 section lists them. The full detail is under "As-built" in `decisions/N1.md`.
- `hyperspace/modifiers.py` (new leaf: imports `motion` and `tapers` only; in `hotreload.MODULES` after `motion`, before `routing`):
  - `Modifier`, with `to_json` / `from_json`.
  - `KINDS`, `PARAMS` (`Spec` per param), `INPUTS`, `OUT`.
  - `ModState`, `step`, `next_id`, `number`, `id_of`, `param_id`.
- `routing.py`:
  - `declare_modifiers(reg, mods)`.
  - On `Bindings`: `modifiers` (a tuple; class default `()`, so it survives a hot reload), `modifiers_serial`, `modifier`, `modifiers_doc(reg)`, `set_modifiers(doc, reg)`, `add_modifier`, `remove_modifier`.
  - On `Router`: `_reading`, `_step_modifier(mid, dt, lanes)`, `_publish_modifiers`, `lane_kinds`, `_step_modifiers`.
  - `Router.modulate` gains exactly one line at its top: `self._step_modifiers(analyzer, dt)`.
  - `to_json` and `is_session_row` are untouched.
- `params.py`: `"mod"` appended to `PERFORMANCE_GROUPS`.
- `preset.py`:
  - New: `MODIFIERS_KEY`, `NO_MODULE`, `merge_modifiers`, `Presets._values`, `_mods_at_load`, `_modifiers_part`.
  - Changed: `load_doc`, `document`, `signature`, `dumps`.
- `undo.py`: `TABLE_GROUPS`; `_mods`; a seventh fingerprint element (compared with `alike`); `State.modifiers`; the restore through `set_modifiers`.
- `learn.py`: `accepts` handles `mod:`.
- `ui_routing.py`: the strip (`modifiers`) and its plain functions; `_sources` skips blank-labelled lanes; `found` counts modifiers.
- `ui_presets.py`: `OVERVIEW_GROUPS` leaves `mod` out.
- `tests/test_modifiers.py` (25 tests) and four fixtures under `tests/fixtures/modifiers/` (force-added).

## How I tested it
```
uv run pytest -q tests/test_modifiers.py        25 passed
uv run pytest -q                                2263 passed, 2 skipped in 267.85s   (base: 2238 passed, 2 skipped)
uv run ruff check .                             All checks passed!
uv run pytest tests/test_golden_frames.py -q    7 passed in 47.61s
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=.sdd/smoke-home (all four devices disabled, no [library]) uv run hyperspace -ApplePersistenceIgnoreState YES
    -> ran 120 frames and exited clean (last line: "dream: mps · alias copy path · fp32 · weights …")
git diff --stat 5d18192 -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py tests/golden/   -> empty
```
The tests the section names are all present:
- one per kind: curve, scale, smooth, spring smooth, combine mul and cross, threshold, delay
- `test_a_modifier_publishes_a_lane_a_route_can_source`
- `test_modifiers_live_in_the_preset_and_never_in_bindings_json`
- `test_a_route_onto_a_missing_modifier_is_dropped_with_a_note`
- `test_a_template_may_carry_modifiers_and_a_preset_overrides_by_id`
- `test_the_routing_page_builds_the_smoothed_energy_times_band_patch`
- `test_an_older_preset_without_the_key_loads_as_before`

I added these:
- dormant input
- id-order stepping
- a modifier's param as a route target
- threshold as trigger and gate
- a bad entry
- undo
- Learn
- a real imgui draw of the strip (its position on the page, its texts, no duplicate ids)

## Self-review findings, and what I fixed
- `load_doc` read `tmods` under a conditional before it was always bound. It is now initialised to None.
- The `mod` vector is now published through `Router.feed`.
- The ROUTING-page test cleared the house startup preset's routes first, so the saved document equals the fixture.

## Concerns
1. **Dormant reads NaN, not 0.** The prompt says a dormant modifier's lane "stays at its rest, 0". I publish NaN, with the rest at 0. With 0, a `position` route on a dormant smooth would pin its target at 0 instead of handing the base back. The design's intent ("dormant, as a dormant route is today") is what NaN gives. This is register draft "address form", and it is easy to flip.
2. **The N0 merge.** N0 rewrites the body of `Router.modulate`. My hook there is one line, `self._step_modifiers(analyzer, dt)`. N0 should:
   - replace that line with a `modifier` patch node that calls `self._step_modifier(mid, dt, lanes)`;
   - call `_publish_modifiers` when `table.modifiers_serial` changes (as `_step_modifiers` does now);
   - read each modifier's inputs from `table.modifiers[*].inputs`.

   `delay`'s `step` reads its held value and then stores the new input in one call. To break a cycle, N0 may want to emit the held value before the input is evaluated (a peek, then a push). `ModState.held` is there for that.
3. Undo's fingerprint now calls `table.modifiers_doc(reg)` once a frame, and `Presets.signature` does too. With no modifiers this is an empty list, so it is cheap; with a handful it builds a few small dicts a frame.
4. `Bindings.set_modifiers` re-declares every `mod.*` param on every change, including an add, a remove and an undo restore. A performer riding a modifier's param picks it up again the next frame.
5. Commit trailer: `common.md` says "Claude Fable 5.1", but this session's system attribution says "Claude Opus 5.5". I followed the system attribution.

## Files changed
`hyperspace-python/hyperspace/{modifiers.py (new), hotreload.py, routing.py, params.py, undo.py, learn.py, preset.py, ui_presets.py, ui_routing.py}`, `hyperspace-python/tests/test_modifiers.py` (new), `hyperspace-python/tests/fixtures/modifiers/{presets/mod-energy.json, presets/mod-missing.json, presets/mod-templated.json, desk/mod-rig.json}` (new, force-added).

Decisions file: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N1.md`.

## PR
https://github.com/Cutaiar/hyperspace/pull/209 (into plan-28-30-integration; not merged). Final full run on the pushed head ab7a7e7: 2263 passed, 2 skipped in 193.87s; ruff: All checks passed!

## Fix round 1 (review of ab7a7e7) — commit dc3ea30
1. `Router._step_modifier`: a non-finite output now pops the modifier's state as well as writing NaN, so the next finite reading starts afresh. Test: `test_a_non_finite_output_drops_the_memory_and_the_next_reading_starts_afresh`.
2. decisions/N1.md, dormancy row: written down — a `threshold` whose input returns above `on` fires at once (a rising edge); a `smooth` takes its first reading as it is, no glide; a non-finite output counts as dormant and drops the memory.
3. decisions/N1.md, template row: corrected to id order (`set_modifiers` sorts by id).
4. decisions/N1.md, kinds row: `scale`'s clamp is on by default.
5. `ui_routing.set_modifier_input` now replaces the modifier whole (`modifiers_doc` → edit `in` → `set_modifiers`, params at their bases) and pushes `undo.push("modifier input <id>")`; an unchanged pick does nothing. Test: `test_picking_an_input_replaces_the_modifier_whole_as_one_undo_step`. The undo row in the decisions file names the step.
6. The strip draw test now asserts ROUTES < MODIFIERS < "DESK  ·  PRESET LAYER".
7. Left as is: removing the second `analyzer.lanes / CEIL` would mean moving a line inside `modulate`'s body, which N0 rewrites; the extra divide happens only while modifiers exist.

Commands:
```
uv run ruff check .        All checks passed!
uv run pytest tests/test_modifiers.py tests/test_routing.py tests/test_presets.py tests/test_undo.py tests/test_ui_routing.py tests/test_routing_boundary.py -q
                           239 passed in 24.58s   (test_modifiers.py alone: 27 passed)
```
(`tests/test_preset.py` doesn't exist; the preset tests are in `tests/test_presets.py`.) Pushed to `plan-28-n1-modifiers`, which updates PR #209.
