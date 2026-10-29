# 38-B3 fixes report

**Status: DONE.** The review's C1, I1, I2, M1, M3, M5 and M8 are fixed. M2, M4, M6, M7 and the plan 39 seam are drafted as register rows in `decisions/38-B3.md`.

- **Branch:** `plan-38-b3-fixes`, cut from `plan-38-hold` @ 2f85f4f.
- **Commit:** b4ebba9.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/259 (into `plan-38-hold`).

## What changed
- **`hyperspace/preset.py`** (ruling 12):
  - `GraphSection.hold` (None, or the hold), `names(spec)`, `settle()`, and `_settle(spec)`, which runs the four declares through `hold.keep`.
  - `put` asks `keep` for its `fx.hold`.
  - `Presets.load`'s delay reset goes through `gs.hold` while held (one line).
  - Beyond the ruling's letter: `Presets._values` drops `hold.program_only()`, so a save or dirty check during a hold does not carry the projector's leftover instances. Without it, `new` while holding TRIP would make the new preset's values include TRIP's effect and switch params.
- **`hyperspace/hold.py`:**
  - `section=`, `kept`, `loaded`, `keep()`, `reset_delays()`, `program_only()`, `_release()`, `_settle()`.
  - Take: release, settle to the live graph, let go, then reset the program's delays if a load happened.
  - Drop: release first. Its revert lands the hold point; with no undo it settles itself.
  - `canvas_renderer(panel)`; `_cut()` for `rewired`.
  - `ONE_FOR_BOTH` gains `view.speed`, and the new `ONE_FOR_BOTH_PREFIXES` covers `view.plane.*`.
- **`hyperspace/app.py`:** `hold.section = presets.graph`. `_draw_preview` takes output 1's switches at dim 1.0.
- **`hyperspace/ui_graph.py`** (3 reads) and **`hyperspace/ui.py`** (2 reads + an import): `_graph` is read through `hold.canvas_renderer`. `_canvas` and `_node` are untouched.
- **`tests/test_hold.py`:** fixture passes `section=`. New tests: the landing keeps effects, switches and resizes, and they are not the preset's values; phase through hold/land/take; Drop brings them back; the GL test (program frame equals the look alone after a blank graph lands, black after Take, and the effect visibly matters); the delay resets; `canvas_renderer`; raise/undo/dirty (M5); speed and planes unheld; the preview's switches (M3). The four C1 tests fail with `keep` made an identity (checked by a temporary probe, since removed).

## Gates (from `hyperspace-python/`)
```
uv run pytest -q tests/test_hold.py                  30 passed
uv run pytest -q                                     3988 passed, 2 skipped in 31.67s
uv run ruff check <6 touched files>                  All checks passed!
uv run pytest -q --all tests/test_golden_frames.py   128 passed in 33.08s (none moved)
uv run pytest -q --all                               4200 passed, 2 skipped in 46.72s
```
The dream end-to-end test that failed during B1 passes now: B1's failure was machine load.

## Concerns
- `Presets._values` filter: that line is outside the land block ruling 12 allowed. I judged it necessary (otherwise a save during a hold writes dead ids into the library). The controller may want it as its own ruling.
- Plan 37's thumbnails must route through `hold.canvas_renderer` at integration.
- `38-hold.md` still says a removed effect "reads through" during a hold; B4 should correct it.
- Attribution on b4ebba9 uses common.md's `Claude Fable 5.1` lines, as the coordinator asked. B1's commits used Opus 5.5.

## Verification follow-up (c834e74, pushed to plan-38-b3-fixes / PR #259)

- **I-a:** while held, `GraphSection.mark()` records the landed spec's own `effect_names()`, not `fx.held`. New test `test_an_undo_after_take_brings_no_program_only_instance_back`: hold, then land blank, then land straight, then Take, then ⌘Z. After it, `fx.specs` equals the spec's names, and neither `_values()` nor the registry has any `fx.kaleido.*`. The test fails without the mark fix (checked).
- **M-a:** `Hold.program_only` now uses the `hold.PROGRAM_IDS` table (kind to ids). A kind the landing settles that the table lacks raises `KeyError`. The list of what plan 39 must add is in `decisions/38-B3.md`.
- **M-c:** a live `fx` of None (every file exists) makes no effect program-only. Both M-a and M-c are tested in `test_program_only_knows_every_kind_and_every_file_live`.
- **M-d:** a rough-edge line added to the C1 row.

Gates:
```
uv run pytest -q tests/test_hold.py              32 passed in 2.97s
uv run pytest -q                                 3990 passed, 2 skipped in 23.75s
uv run ruff check hyperspace/hold.py hyperspace/preset.py tests/test_hold.py   All checks passed!
```
