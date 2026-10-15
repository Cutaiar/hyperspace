# A3 report — Plan 26: the hands as a geometry node

**Status:** DONE_WITH_CONCERNS
**PR:** https://github.com/Cutaiar/hyperspace/pull/187 (into `plan-24-26-27-integration`)
**Base:** `cf7e467` (the merge of A2, PR #183). Confirmed with `git log --oneline -3`.
**Branch:** `plan-26-a3-hands-node`

## Commits
- `bcd51d3` Plan 26 A3: the hands as a geometry node — in the scene or as a layer, composited anywhere; history as wiring
- `19e9e6d` Plan 26 A3: re-record the 122 frames where the hands show; new goldens for the wirings

## What was built
- **The hands are a geometry node.**
  - `graph.Hands` (named `ghost`) settles the hands once per frame (`Ghost.settle`) through `ghost.shared_camera`, which is the eye (`eye.*`) plus `HandsIO.units`.
  - The poses are drawn by the scene (`Ghost.draw_solid`), by the hands' layer, or by the readout.
- **`graph.Wiring(hands, blend, history)`** lives on `Renderer.wiring`, and its default is today's frame. Nothing in the app sets it yet; A4 will.
- **Hands in the scene.**
  - The scene takes any number of geometries. It clears itself, draws the solid hands first, then the shape with `draw_scene(clear=False)`.
  - When the scene holds the hands, the layer splits the readout out every time. When there is no layer, a `Readout` node draws it.
- **Layers and composites.**
  - The hands' layer has a depth texture.
  - `Composite` has a `blend` (`over` / `add` / `depth`) and a `depth` port.
  - `Renderer.lay` does the work with `LAYER_FS` and `LAYER_DEPTH_BIAS` = 0.05.
  - `SceneTarget.depth_texture` resolves the scene's depth lazily, out of the MSAA target.
  - Plain over still goes through `Ghost.composite`, so its bytes are unchanged.
- **Outputs are wired.**
  - Each `Output` has `image`, `hands`, `readout` and `depth` ports.
  - A through pipeline has a `fallback` and stands down per frame (`Fx.bent`, `Output.settle`). `Frame.routes` is gone.
  - `stats["routes"]` records what each output showed. The golden tool asserts it equals `outputs.route` in every default state.
- **History is wiring.** The capture takes `scene`, or `composite(history)` when the history is wired to the scene with the hands.
- **Timing.** When the scene holds the hands, their draw is its own `ghost` line. The default SYSTEM lines are unchanged.
- **Calibration.** The default calibration now fits the padded box into a 16:9 picture (`ghost.CAL_ASPECT`). The hands land within 4 px of where they were at 960×600, and within 9 px at 1080p. A2's shorter-side square had drawn them at about ⅔ of their size.

## Goldens
- **Byte-identical: 305 of 427.** That is every frame with no hand shown. Verified by comparing the manifests: 0 hands-absent frames moved and no route fields changed.
- **Moved: 122**, for one reason: the hands now draw through the shared camera.
- **New: 117** (the `in-scene/*`, `depth/*` and `history+hands/*` states).
- **Sheet:** `hyperspace-python/docs/plans/assets/26-render-graph/a3-hands-moved.png`. I looked at it: the hands are in the same place and at the same size.

## Tests and gates
- New file `tests/test_hands_node.py` with 14 tests: front/behind in the scene, depth-aware, the glass, the guide never in the scene, a raising draw, the MSAA depth resolve, the presenter under each wiring, mirror/flip, timing, calibration and settle.
- `tests/test_graph.py`: +4 tests, and shapes updated.
- The two allowed history tests were rewritten. `test_camera`'s framing test was updated for the 16:9 fit.
- Gate results:
  - `uv run pytest -q` → 2083 passed, 2 skipped in 145.84s
  - `uv run ruff check .` → All checks passed!
- **Smoke run:** `HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES`, with `[hands] enabled = true` and `tape = synth.json` (written by `tools/hands_tape.py synth`). It exited 0 with an empty `stall.log`. It printed a note that `[hands]` is now a `[[devices]]` entry.
  - I could not see the picture. The run is headless from my side, `ghost.on` is a session param that is off by default, and no wiring is selectable in the app before A4.

## Files changed
- `hyperspace/ghost.py`, `hyperspace/graph.py`, `hyperspace/render.py`
- `tools/golden_frames.py`
- `tests/test_hands_node.py` (new), `tests/test_graph.py`, `tests/test_outputs.py`, `tests/test_render.py`, `tests/test_camera.py`, `tests/test_golden_frames.py`
- `tests/golden/frames/*`
- `docs/plans/assets/26-render-graph/a3-hands-moved.png`

## Concerns
1. **The prompt and the dispatch disagree about the goldens.** The prompt's A3 section says "the default graphs must still match A2's recordings exactly". Per the dispatch, the 122 frames where hands show moved for the camera reason; everything else is exact.
2. **Rough edges, all registered in the decisions file:**
   - Hands inside the scene ignore `ghost.alpha`, and a fading hand still writes depth.
   - On a portrait output the 16:9 calibration crops the box at the sides.
   - The depth-aware boundary is aliased (one depth sample per pixel).
   - A presenter output lays add/depth layers plain over.
   - With the hands in the scene, an output's hands switch cannot remove them from that output.
3. **The OUTPUT/LOOKBACK pages do not show the wiring in words.** I left that to A4.
4. **A4 needs per-node Ghost resources for a second hands node.** Today `Frame.hands` and `Frame.readout` are single slots and everything reaches `r.ghost`. This is listed in the decisions file §4.

## Decisions file
`/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/A3.md`: register rows, hand checks V.12–V.17, as-built notes, what A4 must change, and the moved goldens.

## Fix round 1 (commit `eb2c3de`)

### What changed
1. **Important — doubled hands in the echoes.** In `graph.default_graph` the `composite(history)` node is now built only when the hands are not in the scene (`... and layer is not None and not in_scene`). Before the fix, `Wiring(hands="scene", history="scene+hands")` with a glass output laid the hands' layer over a scene that already held the hands. `test_graph.py::test_the_history_is_wired_to_the_scene_or_the_scene_with_the_hands` gained a graph-shape assert for views `[S(), S(scene=False)]`: the `hands` layer exists, `composite(history)` does not, and the capture is wired to `scene`. No golden moved, because the `history+hands/*` goldens use the layer wiring.
2. **Calibration test bound.** It now uses the measured offsets plus a margin: 5 px at 960×600 (measured 4.3), 10 px at 1920×1080 (measured 8.4), 5 px at 1512×982 (measured 2.4). The PR body and the register row now say this.
3. **Add on a presenter output.** `Handoff.blend` ("over" or "add") is new in `outputs.py`, which still imports only `glsl`. `Presenter` honours add in step 3. `_compose(blend=)` sets it on the hand-off, and a depth-aware layer still goes over plain. Covered by the presenter test under `Wiring(blend="add")` (byte-for-byte equal to the target view) plus hand-off blend asserts.
4. **`ghost.alpha` at 0.** I documented it rather than change the code: at exactly 0, `Ghost.poses` draws nothing, so it removes the hands from the scene too, while any other value shows them solid. The register row and V.12 say so.
5. **V.12 wording.** It now says in-scene hands saturate towards white on the look-back presets, and that doubled rims are the failure mode fixed here.
6. **`_compose` annotation.** The `key: int | None` annotation and the docstring now name the int pipeline key that `Output.run` passes.
7. **Decisions file.**
   - A2's calibration row and V.11 are superseded by the 16:9 fit; A5 should merge them into one row.
   - `Hands.TIMED` is set by the consumer scene. That is fragile when one Hands node feeds both a scene and a layer, and A4 must fix it. Noted in the row and in §4.
   - A new §6 lists this fix round.

### Tests and commands
- Covering tests: `uv run pytest -q tests/test_hands_node.py tests/test_graph.py tests/test_outputs.py tests/test_render.py tests/test_golden_frames.py` → 194 passed in 40.34s
- `uv run pytest -q` → 2083 passed, 2 skipped in 193.80s
- `uv run ruff check .` → All checks passed!
- `uv run python tools/golden_frames.py` → all 544 frames match their goldens (Apple M3 Max, 4.1 Metal - 90.5)

The PR body is updated with a "Review fix round 1" section.
