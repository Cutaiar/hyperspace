# T5 report: the fx module presets retired (plan 40, P5, D6, D10)

**Status:** DONE_WITH_CONCERNS. The one concern is that the FX page's own fx strip is now hidden; see "Concerns".
**Base:** 51106e1 (confirmed). **Branch:** `plan-40-t5`. **PR:** https://github.com/Cutaiar/hyperspace/pull/271 (into `plan-40-build`, not merged).

## Commits
- 305499a Plan 40 T5: the fx module presets retired outright (D6, D10)
- 6591744 Plan 40 T5: fx_shots shoots the effects alone, times the trip inline

## What was built
- `git rm hyperspace/library/fx/*.json` (all six).
- `preset.py` (module hooks only, plus the generator):
  - removed `_watch_fx_modules` (both calls), `_fx_module` and `_held_retired`;
  - `NO_MODULE` gains `FX_GROUP`, and `RETIRED_MODULES` (imported from library) lets `load_doc` keep an fx label quietly, with no note and labelled in step 6, while `document` drops it;
  - `fx_module()` is replaced by inline `ACID_FX` / `MANDALA_FX` / `NOITA_FX`, so the party presets generate byte-identically.
- `graphmigrate.py`: removed `module_runs`, `_wired_module_runs`, and the helpers only they used (`_entry`, `RUN_ENDS`, `_run_entries`, `_chain_into`, `held_retired`, `landed_retired`, `_is_number`, `_as`).
- `library.py`:
  - `RETIRED_MODULES = ("fx",)`;
  - `groups()` leaves it out;
  - `default_name("fx")` is None, so `defaults("fx")` is the fresh values even over an old `fx/default.json`;
  - two comments and docstrings updated (`on_apply`, `_apply_doc`).
- `ui_presets.py`: the fold lists no fx (through `groups()`), and `strip()` returns early for a retired group (this hides the FX page's strip; see Concerns).
- `tools/fx_shots.py`: the preset loop is removed, and the timing uses inline "tripping balls" values.
- `ui_fx.py`: untouched (D10).

## Spec vs build
- **The spec says "Nothing on [the FX page] referred to the module presets". That is wrong.** `ui_fx.page` draws `panel._section("effects", "fx", …)`, which is the fx module-preset strip (◀ name ▶ save as… reset). I hid it via `ui_presets.strip` (no `ui_fx.py` edit). Reversible in one condition. Register draft 47a.
- **The dispatch's "filter at the library (no folder → not a group)" would also remove view/rot/camera** (their strips come from params, not folders). I named the retired group instead (47b).
- **Files outside the dispatch list:**
  - `tools/fx_shots.py`, needed for the DONE grep;
  - `tests/fixtures/palettes/fx/sunset.json`, removed; it was the fixture of a removed test;
  - `ui_presets.strip`, outside "the fold only".
- **No factory preset names an fx module** (all `"modules": {}`). The byte-identical round trip test needed no change, so no ruling was needed there.

## Tests
- **New** (in `tests/test_presets.py`, where the module-label tests live):
  - `test_an_old_fx_label_loads_quietly_and_saves_without_it`;
  - `test_the_fx_presets_are_retired`: no factory folder, not in `groups()`, fresh defaults even over a user `fx/default.json`, no hook or migration names left, no apply hook for fx.
- **Changed:**
  - `test_ui_presets::test_more_opened_…`: fx asserted absent from the fold, headless;
  - `test_presets` module-label and round-trip tests: moved to dream/wake;
  - `test_plan12_presets`: checks the inline `*_FX`;
  - `test_graph_migrate`: `FILES` without the fx folder, and `test_mandala_keeps_kaleido_first` reads `MANDALA_FX`.
- **Removed with what they tested:**
  - five R12 tests plus `_module_run` in `test_graph_free`;
  - `test_fx::test_factory_presets_name_only_real_params`;
  - `test_palette::test_an_old_fx_module_preset_is_read_as_the_slice`;
  - `test_plan36_lookback_dream::test_an_fx_module_before_any_preset_fills_nothing_in`;
  - `test_fx_palette::test_a_saved_palette_is_an_fx_module_preset`.
- **Every factory preset loads with no note and round-trips byte-identically:** `test_plan36_seven::test_every_factory_preset_is_its_sources_seven_and_round_trips`, unchanged, passes.
- **`tools/golden_frames.py`** is unchanged (byte-identical).

## Gates (from `hyperspace-python/`)
```
uv run pytest -q                  4097 passed, 2 skipped in 44.16s
   base 4122 − 8 removed tests − 18 fx-file parametrizations (test_graph_migrate FILES × 3) − 1 palette test + 2 new = 4097
uv run ruff check <14 touched .py files>   All checks passed!
uv run pytest -q --all -m golden  136 passed in 66.28s   (nothing re-recorded, no PNG moved)
uv run pytest -q --all            1 failed, 4318 passed, 2 skipped in 122.28s
   failed: tests/test_dream.py::test_end_to_end_offscreen. It is timing-bound
   (worker.drain(10.0), stats ms < 60) under -n auto, and passes serially:
   `uv run pytest -q --all -n0 tests/test_dream.py::test_end_to_end_offscreen` → 1 passed in 7.65s.
   It touches nothing this task changed.
FX page headless: uv run pytest -q -n0 tests/test_fx.py -k "page or strip" → 10 passed
```
- `ls hyperspace/library/fx` fails.
- `grep -rn "module_runs\|_fx_module\|library/fx" hyperspace/ tests/ tools/` finds nothing.
- `git diff --stat 51106e1..HEAD`: 21 files, only the ones listed above.

## Self-review
- Dead-code sweep: every helper removed from graphmigrate was grep-checked for other callers in hyperspace/, tests/ and tools/ (`_chain` and `_wired_effects` stay; others use them).
- The hot-reload case: an old `Presets` whose `__init__` registered the fx apply hook would, after a re-class, call a missing `_fx_module` on an fx module load. That is unreachable now, because no UI loads an fx module, so I left it.
- `_module_values`'s fx branch and `headless.SHARED_FOLDERS`' `"fx"` stay. Both are harmless, and the second is in a file this task does not own.

## Concerns
1. **Ruling 47a, the FX page strip.** The controller may prefer the strip kept, since the dispatch said "draws as before". It is one condition to revert. If kept, the fx module-preset save road stays live on that page.
2. **Stale wording in the factory notes.** The notes of `party-acid` and `party-mandala` mention "the `acid` / `mandala` fx module preset". They are left as preset data (no preset may change).
3. **Docs for T6.** The P5 sentence about the FX page, R12 in plan 33, and the fx examples in DECISIONS/ARCHITECTURE need updating.

Decisions file: `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t5.md`.
