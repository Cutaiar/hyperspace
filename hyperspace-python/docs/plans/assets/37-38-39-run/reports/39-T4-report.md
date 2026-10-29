# 39-T4 report: `segment`, the node and the worker (Vision, torch, motion)

**Status:** DONE_WITH_CONCERNS (minor; see Concerns)
**PR:** https://github.com/Cutaiar/hyperspace/pull/265 (`plan-39-t4-segment` → `plan-39-vision`)
**Base:** 5c3f226, confirmed. `git reset --hard FETCH_HEAD` was accepted, and the branch was renamed.
**Decisions file:** /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/39-T4.md

## Commits
- 13b341e Plan 39 T4: segment.py — the worker, the Vision and torch backends
- ceb8d1e Plan 39 T4: the segment node — pins, the worker's hand-off, motion, the flip everywhere
- 38def48 Plan 39 T4: the segment tests and the segment-motion fixture with its goldens
- 624095f Plan 39 T4: a segment has no own_size; segment.py's torch import is a function's

## What I built

### `hyperspace/segment.py` (new)

**`SegmentWorker`** follows `DreamWorker`'s shape:
- three input slots that `submit` copies into, so a rows-reversed view is fine;
- one pending job, latest wins, drops counted;
- a lock-free `latest() -> (mask, index, (w, h))`;
- errors caught into `.error` and said;
- a thread named `segment-<name>` that sleeps on a condition;
- `close()` that joins within 1 s;
- `wants()`, so the frame thread can skip a readback while a job is still waiting.

**`VisionBackend`** uses the spike's calls: the request is built per level, the CGImage comes from the frame's bytes, and the L008 pixel buffer is locked, read past its padding, and unlocked. Running the spike again showed Vision's matte is a fixed 4:3 (256×192, 512×384, 2016×1512) stretched over the whole image. The backend therefore resamples it to the frame's aspect (256×144 at 16:9). Without that, cover-fitting consumers would put it in the wrong place.

**`TorchBackend`**:
- LR-ASPP, built with `weights_backbone=None` and the state loaded, so no ImageNet download;
- fp16 on MPS;
- the spike's normalise and softmax, class 15;
- one model shared per (device, dtype), with its forward pass under a lock;
- weights from `<home>/weights`, then the hub cache, else downloaded with a stderr line.

**`pick_backend(cfg)`** returns a backend or a reason string. It finds libraries with `find_spec` rather than importing them. **`make_worker`** builds a worker from it.

### `graph.py`

- **Tables.** `SegmentAt` and every table line, as T2 and T3 added theirs.
- **Pins.**
  - `segment.fg`, `.bg` and `.mask` are in `PINS`. The instance pins (`segment.N.*`) are matched by `_SEGMENT_PIN`, through `pin_node` and the new `segment_pin`.
  - The pin kinds are `fg` and `bg` (IMAGE) and `mask` (MASK).
  - The bare `segment` is refused as a source, in its pins' words.
  - The scene-pin refusal now applies to the scene's pins alone.
- **`SegmentNode`** (OUTPUT MASK) is the matte, made once a frame by `matte()`.
  - **Person mode.**
    - It pulls `worker.latest()` into `<name>#mask` only when the index moved, smoothed per result by `segment.smooth`.
    - It submits only when the input moved and the worker would take it. The shortcut is a channel's own CPU frame, taken when the channel has pixels, is fitted by cover and has no `alpha_of`. Otherwise it uses `MaskPasses.readback`, with rows turned to top first.
    - It feathers through `MaskPasses.feather`, blurring again only when the result or the radius changes.
  - **Motion mode** uses `MOTION_FS` and `LEARN_FS` over `Renderer.motion_pair(name)`. `k` is `1 − exp(−dt/learn)`, and the first frame is learnt whole.
  - **Subject mode** is refused in words.
  - It makes no matte while off, before the first matte, with no worker (the preview), on an error, or when its input reads nothing. Each case is said.
- **`SegmentPin`** (fg/bg) is one `masks.cut` per frame. With no matte, `fg` is the input whole and `bg` is transparent and reads nothing.
- **The flip flag**, from T3's review:
  - `MaskPicture.paint` reads `mask_of` and passes `flip`.
  - The new `mask_port(node, frame)` refits a mask and turns it if needed. `MatteNode.image` and `SegmentNode.image` both use it, so `lookback.cover` is bound the right way up.

### `masks.py`
- `PROMOTE_FS` takes `u_flip`. `promote(flip=)` and `fit(flip=)` were added, and `fit` always runs a pass when the mask must be turned.
- New: `MOTION_FS`, `LEARN_FS`, `DOWN_FS`, `MOTION_SOFT`, and the methods `feather`, `motion`, `learn` and `readback`. `readback` uses a trilinear sampler, which is released with the passes.

### `render.py`
- `segment_cfg = None` by default. `segmenter(name)` takes an optional `segment_factory` hook for tests; otherwise it lazily calls `segment.make_worker`.
- `motion_pair(name)`, which is a `DelayPair`.
- `_tend_segments(graph)`, called in `_draw_frame` after `_idle_rings`: a worker or pair is closed or released `SIZED_KEEP_FRAMES` after its node goes.
- `close()` closes this renderer's own workers only.
- `media_now(c)`: `media_texture` keeps the `MediaFrame` it read.

### `app.py`
`renderer.segment_cfg = cfg.get("segment", {})` and `segmenters = _Closer(renderer.close)` sit beside the dream's lines. `segmenters` is added to both `close_all` calls, at quit and restart. Nothing near `_draw_render` changed.

### Params, view and preset
- `params.declare_segments` declares `mode` and `quality` (choices, not modulatable), `feather`, `smooth`, `on`, `sense` and `learn`, in group `segment`, after `cut`.
- `view.SegmentState` holds the defaults: person, fast, feather 0, smooth 0, on, sense 0.1, learn 3 s. `ViewState.segments` and `Frame.segments` carry them.
- The preset's landing, deferral, new-preset exclusion and `NO_MODULE` handling follow the cut's.

### Elsewhere
- **`graphview.py`**: table entries only: OWNERS, LABELS, HOVERS, FRAME_CLASS, PICKER_GROUP ("pictures") and `_node_name`.
- **`ui_presets.py`**: one word (`segment` added to the overview's exclusions).
- **`pyproject.toml`**: `pyobjc-framework-vision>=12.2 ; sys_platform == 'darwin'`. Then `uv lock` and `uv sync`; the lock adds `pyobjc-framework-coreml` and `-vision` 12.2.2.

### Fixture
`tests/fixtures/presets/segment-motion.json` (`/7`):
- `scene → composite.over`, `channel.a → composite.under`, `composite → segment.image` (motion, feather 2), `segment.fg → output.all.image`.
- It has 8 goldens with one new PNG, `png/0af84155993b2d4b.png`. I checked it by eye: the polytope on black, with the still's disc cut away.
- It was recorded with `--only segment-motion` and `HYPERSPACE_HOME` set to a scratch folder with an empty `config.toml`.
- The fixture was not ignored, so it was added normally with no `-f`.

## How I tested it
- **`tests/test_segment.py`** (10 tests, 2 of them live) covers:
  - latest-wins with drops counted; the submit copying, and never waiting;
  - an error said and then cleared; a backend that will not open being said;
  - the thread sleeping, and `close` joining within a second (mid-run too);
  - a reason-string worker; `pick_backend` with missing libraries and with an unknown name;
  - the levels and input sizes, and the resample.

  The live tests ran Vision and torch once each on a synthetic frame.
- **`tests/test_graph_segment.py`** (23 tests) covers:
  - identity and tables; the round trip; a segment must be declared; the pins' type rules;
  - the build: one segment under its pins, and a segment fed nothing or reached by nothing is not built;
  - `graph.py` does not import segment, Vision or torch;
  - the canvas tables, the params, the registry and the `/7` round trip; a new preset holds no `segment.*`;
  - in GL:
    - before the first matte;
    - fg, bg and mask from a known matte, through a composite too;
    - the shortcut versus the readback, counted on each path; the readback's rows are top first, and not-moved means not fed;
    - orientation on a cut, on a window and on `lookback.cover`;
    - on off; subject; an error mid-show; a channel with no frame;
    - a removed node closing its worker;
    - the preview (no `segment_cfg`) making no worker, and closing it leaving the program's alive;
    - motion on two stills.

Gate outputs:
- `uv run pytest -q` → `4079 passed, 2 skipped in 39.17s` (base 4046).
- `uv run ruff check .` → `Found 25 errors.` These are the base's own. Every touched file gives `All checks passed!`.
- `uv run pytest -q --all tests/test_golden_frames.py` → `136 passed in 13.66s`. There are 789 goldens (781 + 8); `frames.json` has insertions only, so none moved.
- `uv run pytest -q --all` → `4301 passed, 2 skipped in 65.50s (0:01:05)`.
  - The first `--all` run found two real failures, fixed in 624095f:
    - `test_nothing_of_plan_33_has_an_own_size`: `SegmentNode.own_size` was removed.
    - `test_dream::test_core_does_not_import_the_worker`: the text check now reads `segment.py`'s top-level imports by AST.
  - That run also had one load-flaky failure, `test_migrate_library::test_the_real_picture_check_passes_an_old_preset`. `uv run pytest -q --all -n0 tests/test_migrate_library.py` gives `9 passed`, and it passed in the later full run.

## Files changed
- **New:** `hyperspace/segment.py`, `tests/test_segment.py`, `tests/test_graph_segment.py`, `tests/fixtures/presets/segment-motion.json`, `tests/golden/frames/png/0af84155993b2d4b.png`
- **Modified source:** `hyperspace/graph.py`, `masks.py`, `render.py`, `app.py`, `params.py`, `preset.py`, `view.py`, `graphview.py`, `ui_presets.py`
- **Modified build:** `pyproject.toml`, `uv.lock`
- **Modified tests:** `tests/golden/frames/frames.json`, `tests/test_golden_frames.py`, `tools/golden_frames.py`, `tests/test_app_boundary.py`, `tests/test_graph.py`, `tests/test_hotreload.py`, `tests/test_dream.py`

## Self-review
- `graph.py` reaches the worker only through `frame.r.segmenter`, `frame.r.media_now`, `frame.r.motion_pair` and `frame.r.mask_passes()`. A test checks it does not import segment, Vision or torch. No node method is named apply, modulate, snapshot or set_value.
- The render stack reads params and never writes one.
- The WYSIWYG rule holds:
  - the shortcut changes only where the worker reads;
  - a segment no wire reaches is not built, so its worker never starts;
  - its pins are drawn wires.
- Alpha is not a mask: only `SegmentPin` (fg/bg) writes the matte into a picture's alpha, which is its job, through `CUT_FS`.
- No plan-36 node changed behaviour. `MatteNode.image` now goes through `mask_port`, which is identical for a matte because its flip is False. All 136 golden jobs pass.
- The readback runs only when the worker has nothing pending and the input moved. A result is uploaded only when its index changes. The feather is redone only when the result or the radius changes.

## Concerns
1. **`segment.2`'s pins are not drawn on GRAPH.**
   - The canvas draws pins from `graph.PINS`, which lists instance 1.
   - Wires from `segment.2.fg` work, but their cables are not drawn.
   - The fix is code in `graphview` around line 1435 (a `segment` case beside the look-back's echo pins). That is outside the table entries, so it is T5's. See row 4xab.
2. **The fixture's "two stills"** is the scene's motion over the one still in `tests/golden/media`. The literal two-stills case is a GL unit test. There is no frame-signature case, because wired fixtures are left out (row 4ya).
3. **`fg` and `bg` are made at the frame's size, not the input's own size.**
4. **Vision's matte is stretched over the image.** I inferred this from the API: it returns a fixed 4:3 size for a 16:9 input. Nobody has checked it with a person on camera (AJ.1).
5. **For the controller at integration:**
   - `segment` is cold for hot reload. That is fine as the end state, since the workers outlive a reload.
   - `masks` still needs T2's move onto `MODULES`.
   - Plan 38's `hold.mirror` must leave `segment_cfg` None. That is the default for a new `Renderer`; `mirror` must not copy it.
6. **Commit attribution.** Commits use the session's `Claude Opus 5.5` lines, as T2 and T3 did, rather than common.md's `Fable 5.1`.
7. **Out-of-table edits.**
   - `view.py`: `SegmentState` and the constants, beside T2's and T3's.
   - `ui_presets.py`: one word.
   - `test_dream.py`: the torch-import check now reads `segment.py`'s top level by AST.
   - `masks.py`: `fit()`'s early return now requires `not flip`.

---

## Fix report (review round 1)

**Commit:** dd48e12 Plan 39 T4 review: smooth in float, laid-over through a segment, stop never waits (pushed to `plan-39-t4-segment`, PR #265)

**Important 1 (smooth ghost).**
- **Fix.** `SegmentNode._pull` keeps `_prev` as float32, mixes `prev·k + new·(1−k)`, and uploads `round(prev)` as uint8. `k` is still clamped to at most 0.99, because 1 would freeze the matte.
- **Test.** `test_smooth_near_one_still_reaches_the_new_matte`: at smooth 0.99 a 255 → 0 step reaches 0, and the way back reaches 255. It runs 1000 results through `_pull` over a stand-in texture.
- **Row.** 4yc.

**Important 2 (laid-over through a segment).**
- **Fix.** `_Build.laid_over` recurses through `kind == "segment" and w.port == "image"` when `<seg>.fg` or `<seg>.bg` is laid over. It also covers `segment.N`.
- **Tests.**
  - `test_a_scene_through_a_segment_laid_over_keeps_its_see_through_ground`: fg, bg and `segment.2` give ground 0, and a pin straight into a window gives None.
  - `test_a_scene_through_a_segment_turned_off_shows_the_under` (GL): scene → segment (off) → fg → composite.over, with blue under, shows the blue.
- **Goldens.** None moved. `segment-motion` feeds a composite into the segment, so `git status tests/golden` is clean and 136 jobs pass.
- **Row.** 4yd.

**Minors.**
1. Register row 4yb records that fg/bg are made at the frame's size and the input is read through `OWN_FIT`.
2. `SegmentWorker.said` now gives the reason alone when one is set ("Vision would not open: …"). The test is updated.
3. `_tend_segments` now calls `worker.stop()` and never joins.
   - The thread closes its backend itself after any run in hand: the backend's close moved into `_run`'s `finally`.
   - Stopped workers are kept in `_stopped` until their threads end.
   - New test: `test_stop_never_waits_and_the_backend_closes_on_its_thread`.
4. `Renderer.close(timeout=1.0)` stops every worker, including the earlier-stopped ones, then joins them all against one shared deadline. `SegmentWorker.close(timeout)` and `stop()` are new.
5. The two real-backend tests moved from decorators into `conftest._LIVE_TESTS`, which applies `live` plus `xdist_group("live")`. The Vision test keeps its darwin `skipif`. `conftest.py` is outside the ownership table; the change is two lines.
6. New test: `test_several_segments_are_several_workers`. It covers two nodes, two workers by name, each fed its own channel, and both closed by `Renderer.close`.
7. The decisions file gains the T5 notes and the controller note:
   - for T5: `segment.2`'s pins are not drawn (around `graphview` line 1434), and whether "pictures" is the MEDIA heading W6 names;
   - for the controller: `hold.PROGRAM_IDS` needs `segment`, `matte` and `cut` entries.

**Gates.**
- `uv run pytest -q -n0 --all tests/test_segment.py tests/test_graph_segment.py tests/test_graph_frame.py tests/test_graph_cut.py` → `225 passed`
- `tests/test_graph_segment.py` → `27 passed`
- `uv run pytest -q --all tests/test_golden_frames.py` → `136 passed`; no golden changed.
- `uv run pytest -q` → `4084 passed, 2 skipped`
- `uv run ruff check .` → `Found 25 errors.` These are the base's own. Every touched file gives `All checks passed!`.
- The live tests, once: `--all -n0` on the two → `2 passed`. Without `--all` they are deselected (`9 passed, 2 deselected`).

**Attribution.** This commit again ends with the session's `Claude Opus 5.5` lines rather than common.md's `Fable 5.1`. The session's system-level attribution instruction names this model, and an agent message does not override it. The controller can amend at merge if wanted.
