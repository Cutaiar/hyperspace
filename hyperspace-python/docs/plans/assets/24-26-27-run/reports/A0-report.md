# A0 report — Plan 26 step 0: golden frames, GPU timing per pass, the naming rule

**Status:** DONE_WITH_CONCERNS (minor; see Concerns)
**Base:** `git log --oneline -1` after the reset showed `cd9106d Base: silence ruff S110 on the pad's optional-wheel fallback`.
**Branch:** `plan-26-a0-golden`. **PR:** https://github.com/Cutaiar/hyperspace/pull/174 (into `plan-24-26-27-integration`, not merged).

## Commits
- `040c3f8` Plan 26 A0: the naming rule for node instances (fx.acid.2.mix)
- `43aaf95` Plan 26 A0: GPU time per pass in Renderer.stats and on the SYSTEM page
- `07072c4` Plan 26 A0: golden frames for every factory preset in every output state

## What was built
1. **Golden frames.** `tools/golden_frames.py [--record] [--only …]` and `tests/golden/frames/frames.json` plus `png/` (71 quarter-size 256-colour PNGs, 920 KB in all).
   - Coverage: 23 factory presets × hands absent/present × the 8 `Switches` states drawn as 8 outputs of one frame (output 1 at 4× MSAA like the window), plus one frame of party-trip on 3840×2160 at dpr 2 under the 1080p cap. That is **369 goldens and 71 distinct pictures**, recorded on **Apple M3 Max**.
   - Settings: 960×600 at dpr 1; 8 frames at 1/60 with `t_now = 2.0 + k·dt`; the LFOs and the analyzer at rest (never stepped or fed); no dream worker; the preset's look-back kept; `ghost.on` true; render cap 1080p.
   - Stored per golden: the SHA-256 of the full-resolution RGBA frame and the route (`outputs.route`).
   - All three pipelines are reached. SCENE_HANDS / HANDS appear for party-trip, party-acid, party-mandala, party-noita, lfo-breathe and hands-fx (the presets with an effect on).
   - Every preset loaded with nothing missing and no notes, and the hands showed in every "present" rig.
   - `tests/test_golden_frames.py` compares every hash exactly and skips with a note naming the expected renderer anywhere else.
   - A diff run writes a contact sheet (golden | now | diff ×4, both sides at thumbnail resolution) under `docs/plans/assets/26-render-graph/`.
2. **GPU timing.** `render.PassTimer` times six passes (scene, cover, hands, lookback, fx, compose) with non-nested `ctx.query(time=True)`, reads them back 3 frames late, and keeps a 60-frame rolling median in `Renderer.stats["gpu_ms"]`. On a context with no timer queries, or after a query fails, timing is off and `stats["gpu_note"]` says why; the frame is byte-identical either way (tested). The existing stats keys are unchanged. The SYSTEM page shows a heading and one line per pass through `Panel.gpu_lines` / `_gpu_timing`, a helper of its own beside `_stall_status`.
3. **Naming rule.** `params.instance_id` / `instance_of`: the first instance keeps today's id, and an extra one is `<node>.<n>.<key>` with n ≥ 2 (`fx.acid.2.mix`). The rule is in `docs/ENGINEERING.md` §2 and pinned by 2 tests in `tests/test_params.py`, including one that checks every fx/ghost/dream param registered today reads back as instance 1.

## Determinism proof
The recorder ran three times from an empty `tests/golden/frames/` with different `HYPERSPACE_HOME`s, once with a fresh GL context per rig and twice with the shared context. `diff -r` against the first run printed nothing each time (IDENTICAL), covering the manifest and all PNGs. `tools/golden_frames.py` in diff mode then printed "all 369 frames match their goldens (Apple M3 Max)".

## Gates (last lines)
```
uv run pytest -q
1893 passed, 2 skipped in 130.10s (0:02:10)
uv run ruff check .
All checks passed!
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/a0scratch/smoke uv run hyperspace
dream: mps · alias copy path · fp32 · weights /tmp/a0scratch/smoke/weights
EXIT=0   (stall.log empty)
```
The test count rose from 1885 to 1893 (+6 in test_golden_frames, +2 in test_params). After the ruff fixes (import order and noqa, a `Self` annotation, parentheses), the focused modules were re-run: test_golden_frames, test_params, test_render, test_outputs and test_ui_shell, 244 passed.

## Files changed
- `hyperspace-python/hyperspace/render.py` (PassTimer, timed passes, the `_draw_frame` → `_frame_passes` wrapper)
- `hyperspace-python/hyperspace/ui.py` (`gpu_lines`, `_gpu_timing`, one call on the SYSTEM page)
- `hyperspace-python/hyperspace/params.py` (`instance_id`, `instance_of`)
- `hyperspace-python/docs/ENGINEERING.md` (§2 naming rule)
- `hyperspace-python/tools/golden_frames.py` (new, executable)
- `hyperspace-python/tests/test_golden_frames.py` (new)
- `hyperspace-python/tests/test_params.py` (+2 tests)
- `hyperspace-python/tests/golden/frames/` (new: frames.json + 71 PNGs)

`hyperspace/library/` is untouched. No fixtures were added. No existing assertion changed.

## Self-review findings
- `_draw_frame`'s body moved into `_frame_passes`, and `_draw_frame` became a wrapper with a `finally` that fills `gpu_ms`. Nothing outside render.py calls either name.
- A hot-reloaded Renderer without `timer` gets one lazily (`_pass_timer`).
- `_Timed` swallows begin/end failures and turns timing off; covered by a test with a broken query.
- The tool sets `HYPERSPACE_HOME` to a temp folder unless one other than `~/Hyperspace` is already set, and each rig's library home is its own TemporaryDirectory.

## Concerns
1. The goldens prove pixels only on "Apple M3 Max"; anywhere else the test skips by design.
2. The tool uses one standalone context with `gc_mode="auto"` for the whole process. A fresh context per rig was cleaner, but `release()` left no context current and broke the GL tests after it. The hashes are identical either way.
3. A1 should keep `outputs.route` (or an equivalent), because the manifest names each state's route.
4. Commit trailers use "Claude Opus 5.5" (the session's attribution reminder) rather than the brief's "Claude Fable 5.1".
5. The SYSTEM GPU lines were only drawn headlessly. Hand check V.2 covers the live app.

Decisions file: `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/A0.md` (7 register-row drafts, hand checks V.1–V.3, as-built notes, deviations).

---

# Fix report — review round 1 (commit `af6f952`, pushed; PR body updated)

## What changed
1. **Single-output goldens (important).** `tools/golden_frames.py` adds `SOLO` and `SOLO_FX`, each rendered as output 1 alone (4× MSAA), so the pipeline is drawn direct into the multisampled target and the hands' readout split is decided by that one output.
   - `solo` (the default `Switches()`, which is already scene+hands) for every preset × hands: 46 frames.
   - `solo-scene+hands+through` for the six effect-on presets (party-trip, party-acid, party-mandala, party-noita, lfo-breathe, hands-fx) × hands: 12 frames.
   - A separate `solo-scene+hands` was not added because it is the same `Switches` as `solo`.
   - Totals are now **427 goldens and 73 distinct pictures**. The 369 earlier goldens are unchanged (checked hash by hash against the first recording).
   - Three hands-absent solo frames differ from their eight-output twin by 1 LSB in a single pixel: party-wake solo; hands-fx solo and solo-through. A probe showed a 2-output frame in which output 1's SCENE has one user equals the solo frame, so this is the direct MSAA path against the texture path, and both are now pinned.
   - The manifest lists `solo_states` / `solo_fx_only`. The `--record` summary shows the solo columns, and `test_every_factory_preset_has_every_state_recorded_and_nothing_else` requires them all (exact count 23·2·9 + 6·2 + 1) along with their routes.
2. **Fixture teardown.** The module fixture now yields and runs `gc.collect()` while the tool context is still current.
3. **`PassTimer._off`** releases every query in `_frame`, `_pending` and `_free` (guarded).
4. **Comments** on the construction probe's one sync per Renderer, and on `q.elapsed` blocking after LAG frames because there is no availability query.
5. **`GL_VERSION`** ("4.1 Metal - 90.5") is stored in the manifest. The test's skip and failure messages and the tool's diff output name renderer and version, and the tool prints a note when the versions differ.
6. **The manifest `about`** and the `summary()` header explain why few pictures are distinct.
7. **The `Rig` docstring** is corrected (the tool's one context, a renderer per rig).
8. **`params.instance_of`** has a comment that an explicit `.1.` reads as a key by design, pinned in `tests/test_params.py`. The decisions file notes that `FxState.declare` should guard decimal `@param` keys in A4.

## Determinism
Recorded twice from empty `tests/golden/frames/` (homes `/tmp/a0scratch/home5` and `home6`); `diff -r` printed nothing (`RUN2-IDENTICAL`).

## Commands and output
```
uv run pytest -q tests/test_golden_frames.py tests/test_render.py tests/test_outputs.py tests/test_params.py
190 passed in 29.46s
uv run ruff check .
All checks passed!
uv run pytest -q
1893 passed, 2 skipped in 122.11s (0:02:02)
```
The windowed smoke run was not repeated: the only render.py change is in `PassTimer._off` and comments, and ui.py is unchanged.
