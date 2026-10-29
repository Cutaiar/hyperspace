# C6 report

Base cd9106d (plan-24-26-27-integration). Branch plan-24-c6-palette, commit d64e73b, PR https://github.com/Cutaiar/hyperspace/pull/173

Built `hyperspace/shaders/fx/palette.glsl` (fold + gradient map, 21 params + the 6 own), `@mix` directive in `fx.py`. Tests: new `tests/test_fx_palette.py` (7), fixture `tests/fixtures/palettes/fx/sunset.json` (force-added); adjusted `test_fx.py` (13th effect: orders, page tests run without palette, a page-scroll test for it, two per-effect tests set mix 1) and `test_plan12_presets.py` (allow-list).

Gates: pytest 1895 passed, 2 skipped; ruff All checks passed; smoke run exit 0 (palette off, scratch home /tmp/c6home). `git diff --stat -- hyperspace/library/` empty.

Concerns: the FX page now scrolls (13 chips wrap to a 5th row, palette strip has 21 rows); decisions in decisions/C6.md. Self-review: palette-on smoke not exercised in the windowed run (only headless GL tests).

## Fix round 1
Changed: removed `without_palette` from `fxpage` (only the drag tests use the new `fxpage_twelve`); the fit tests now run with the palette. `ui_fx.py`: gaps removed (wins the 15 px), `strip_rows` packs lo/hi and hue/sat/val onto one row, `HIDDEN_BY_MODE` hides the other mode's rows for the palette. `palette.glsl`: tip shortened, result scaled by alpha when `u_opaque == 0`. Tests: removed the old scroll test; added `test_the_palette_strip_fits_in_both_modes` and `test_a_raised_floor_does_not_light_a_see_through_ground`. Fit-test worst spare: 7 px (zoomblur, face error).
Commands: `uv run pytest -q` -> 1896 passed, 2 skipped; `uv run ruff check .` -> All checks passed. Smoke with the fold on (scratch /tmp/c6home): exit 0.
