# 39-T0 report — `edges.glsl`

**Status**: DONE_WITH_CONCERNS (minor: three existing tests needed bookkeeping edits, and the fixture is also a `WIRED_FIXTURES` entry; see Concerns)

- **Base**: `cb78963` (plan-39-vision), confirmed with `git log --oneline -1` after the reset. Branch `plan-39-t0-edges`.
- **Commit**: `4c68ab2` Plan 39 T0: edges.glsl — Sobel as an effect file
- **PR**: https://github.com/Cutaiar/hyperspace/pull/254 (into `plan-39-vision`)

## What was built
- `hyperspace-python/hyperspace/shaders/fx/edges.glsl`:
  - A Sobel on the luma of `src`: eight taps at `1/u_res`, the gradient divided by 4.
  - `u_threshold` (0 1 0.2) is a ramp from the threshold up to full.
  - `u_glow` (0 4 0) is a second Sobel 3 px out, added at `glow/4`.
  - `u_colour` is a choice [white|source|direction], default 0.
  - The output is premultiplied over transparent black.
  - It carries `@label Edges`, `@blend mix` and `@order 75`.
- `hyperspace-python/tests/fixtures/presets/edges-scene.json`:
  - A `/7` wired frame: `scene → edges → output.all.image`, plus hands-fx's hands wires.
  - Edges is at its defaults.
  - No route moves fx.
- Goldens: 8 new entries in `tests/golden/frames/frames.json` (+186/−0) and 3 new PNGs. The 757 from before are untouched.
- `hyperspace-python/tests/test_fx_edges.py` (new, 15 cases):
  - The three params with their ranges and defaults.
  - A flat picture comes out black. This is asserted after the alpha tail on a see-through ground (opaque=0), and the docstring says so.
  - A hard vertical edge gives a bright 2-column line and nothing elsewhere (white and source modes).
  - The threshold drops a weak edge.
  - The glow widens the line to 6 columns.
  - Direction gives a vertical edge red and a horizontal one chartreuse.
- The FX page lists `edges` like any file. Nothing needed doing.

## Files changed
- `hyperspace-python/hyperspace/shaders/fx/edges.glsl` (new)
- `hyperspace-python/tests/fixtures/presets/edges-scene.json` (new; not gitignored, so no `-f` needed)
- `hyperspace-python/tests/golden/frames/frames.json` and 3 PNGs (additions)
- `hyperspace-python/tests/test_fx_edges.py` (new)
- `hyperspace-python/tools/golden_frames.py`: `edges-scene` added to `FIXTURE_PRESETS` and `WIRED_FIXTURES`
- `hyperspace-python/tests/test_golden_frames.py`: the count goes up by 8, and `GOLDENS_SINCE` gains `edges-scene`
- `hyperspace-python/tests/test_plan12_presets.py`: `edges` is on `EFFECTS_IN_NO_PRESET`
- `hyperspace-python/tests/test_graph_free.py`: a `/7` is allowed among the fixture sources

## Gates (from `hyperspace-python/`)
```
uv run pytest -q          → 2 failed, 3975 passed, 2 skipped in 143.24s
   failures: test_media_render::test_render_thread_never_waits, test_media_video::test_close_during_long_decode_is_quick
   (load-flaky timing; `-n0` on test_media_render/video/folder → 59 passed)
uv run ruff check .       → Found 26 errors before my fix of my own RUF100; now 25, every one in files this
   PR does not touch (docs/plans/assets/39-vision/bench_*.py, hyperspace/media/*, tests/test_media_folder.py,
   test_sequencer.py, test_ui_desk.py, test_ui_pad.py, tools/ingest.py). Touched files: All checks passed!
uv run pytest -q --all tests/test_golden_frames.py → 130 passed in 6.60s
uv run pytest -q --all    → 1 failed, 4190 passed, 2 skipped in 104.94s
   failure: test_dream::test_end_to_end_offscreen (load-flaky; `--all -n0 tests/test_dream.py` → 19 passed)
```
Count delta against base (fast tier 3958 / full 4170): +19 / +20. That is the 15 new edges tests plus the `[edges]` cases of the parametrized every-effect tests in test_fx.py (`test_each_effect_changes_the_frame`, `test_every_effect_runs_on_the_face_target`, the parse/compile sweeps). Both of those pass for edges.

## Self-review
- The 757 goldens are byte-identical: `git diff --numstat frames.json` shows 186 added and 0 removed, and the digest test passes. `frame-signatures.json` is unchanged at 125. The `--signatures` run wrote no new case, because a wired fixture has none.
- I looked at the PNGs: the polytope's lines draw as thin white double outlines on black, and with hands, the hands' outlines too.
- Boundaries: no Python under `hyperspace/` was touched, the choice param works through `fx.py` unchanged, and no preset under `hyperspace/library/` was touched.

## Concerns
1. **`WIRED_FIXTURES`**. I first recorded the fixture as a plain `FIXTURE_PRESETS` entry. `--signatures` then raised: a wired frame has no old section, and it read as a duplicate wire. So it is a `WIRED_FIXTURES` entry and its goldens were re-recorded under that rule: states drawn as the windows' mutes, the same as `through-one-output` and `resize-faces`. Only its own 8 goldens moved between the two recordings, and both recordings were within this commit.
2. **Three existing tests edited** (bookkeeping, not behaviour): the golden count and `GOLDENS_SINCE`, the plan 12 allow-list, and test_graph_free's set of schemas. The brief said "touch nothing but … your tests", and these could not be avoided with a `/7` fixture and a new effect file. T4/T5's `/7` fixtures will rely on the test_graph_free relaxation too.
3. **Source mode alpha**: I used `src × m` with alpha included (the spec named `src.rgb × m`). The dark side of an edge is therefore an opaque black line. This is honest coverage, and it is drafted in the register row.
4. Load-flaky media and dream tests under `-n auto` on a busy machine; all of them pass serially.

## Decisions file
`/Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/39-T0.md` holds:
- Two row drafts: the Sobel, threshold, glow and hue; and `@order 75`.
- AJ.7 with *Pass* and *Fail*.
- As-built notes and deviations.

## Fix report (review: approved, minors only)
1. `tests/test_golden_frames.py`: reworded the GOLDENS_SINCE comment to "the fixtures named in `GOLDENS_SINCE`, added since the digest". Commit 57d2916, pushed. Nothing was re-recorded. `uv run pytest -q tests/test_golden_frames.py --all -n0` → 130 passed in 23.98s.
2. decisions/39-T0.md: the Sobel row's "Other options" now includes the literal `vec4(src(uv).rgb * m, 0.0)` for source mode (the line as light: a black source edge comes out transparent), to be judged at AJ.7 step 4. `src * m` stays as built.
3. PR #254 body: added a sentence saying the fixture also carries hands-fx's hands wires and the `hand:left.y → view.bright` route.
