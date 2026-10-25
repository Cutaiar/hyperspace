# A1 report — plan 26 step 1: the graph in code, today's three pipelines pixel for pixel

**Status:** DONE
**PR:** https://github.com/Cutaiar/hyperspace/pull/179 (into `plan-24-26-27-integration`)
**Branch:** `plan-26-a1-graph`, base `plan-24-26-27-integration` at `bf41438` (A0 + C6), confirmed with `git log --oneline -1` after `git reset --hard FETCH_HEAD`.
**Decisions file:** `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/A1.md`

## Commits

- `57a2159` Plan 26 A1: graph.py — nodes, typed ports, the evaluator, the default graphs
- `bf8c82b` Plan 26 A1: Renderer._draw_frame builds or reuses the graph and evaluates it
- `3de9115` Plan 26 A1: tests for the graph — imports, ports, order, reuse, routing, timer

## What was built

- `hyperspace/graph.py` (new, ~520 lines): `Frame` (the frame as the nodes see it), `Node` (unique name, `INPUTS` port → type, `OUTPUT` type, `after` ordering deps, `run` / `image` / `paint`), the seven kinds — `Shape` (Geometry: `prepare` = the face picture, `draw` = `draw_scene`), `Scene` (geometries into `SceneTarget`, resolve), `Cover` (the faces' coverage mask, a Layer, only while the look-back occludes), `HandsLayer` (`Ghost.layer`, its own camera until A3), `History` (`Lookback.tick/pull` in `run`, `Lookback.composite` painted into each consumer), `Capture` (`Lookback.capture` once, after every pipeline end; the effects' clocks when no chain ran), `Composite` (the hands onto the history's picture or onto the ground, before the chain), `Fx` (the chain per pipeline; pass-through with no effect on; the pipeline's end: direct into the one output at the frame size, unflipped, on this context, else once into the frame texture), `Output` (`Renderer._compose` per view, `output.N`) — `Graph` (add with wiring checks, order by DFS with dependencies first and ties in insertion order, `timed`, `evaluate`), `graph_key`, `pipelines_of`, `default_graph`.
- `hyperspace/render.py`: `_draw_frame` settles size/dpr under the cap, `fx.tick()`/`fx.opaque`, `stats`, a `Frame`, then `_graph_for(views)` (reuse while `graph_key` matches) and `graph.evaluate(frame)`; `PassTimer` per node (`end_frame(names)`, pending frames carry their names, medians in graph order, names that left drop out), `GPU_PASSES` removed; `Renderer._graph`; `on_reload` drops it. `_frame_passes` and `_pipeline` removed; unused imports (`HANDS, NAMES, PIPELINES, SCENE, route`) removed; the passes themselves untouched.
- `hyperspace/hotreload.py`: `graph` in `MODULES` after `view`, before `render`.
- `hyperspace/ui.py`: heading "gpu per node, ms (median of the last frames):".
- Untouched: `outputs.py`, `lookback.py`, `fx.py`, `ghost.py`, `app.py`, every file under `hyperspace/library/`.

## How it was tested

```
uv run pytest tests/test_golden_frames.py tests/test_outputs.py tests/test_render.py -q
2 failed, 162 passed        # before the two A0 timing tests were rewritten: goldens + outputs + render all green

uv run pytest -q
1915 passed, 2 skipped in 150.95s (0:02:30)        # base: 1904 passed, 2 skipped; +11 new

uv run ruff check .
All checks passed!

uv run python tools/golden_frames.py
all 427 frames match their goldens (Apple M3 Max, 4.1 Metal - 90.5)

HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/hs-a1-home uv run hyperspace -ApplePersistenceIgnoreState YES
dream: mps · alias copy path · fp32 · weights /tmp/hs-a1-home/weights
exit 0; /tmp/hs-a1-home/stall.log empty; no config.toml (so no [library]) in the scratch home
```

The first smoke attempt without `-ApplePersistenceIgnoreState YES` hung at the macOS "reopen windows?" alert (as C1 found) and was killed; the flag got past it.

## Files changed

- `hyperspace-python/hyperspace/graph.py` (new)
- `hyperspace-python/hyperspace/render.py`
- `hyperspace-python/hyperspace/hotreload.py`
- `hyperspace-python/hyperspace/ui.py`
- `hyperspace-python/tests/test_graph.py` (new, 11 tests)
- `hyperspace-python/tests/test_golden_frames.py` (two A0 timing tests rewritten for per-node keys and the heading; module docstring)

Tests consciously changed (named in the PR body): `test_each_pass_has_a_rolling_median_in_ms` → `test_each_node_has_a_rolling_median_in_ms` (node names from `r._graph.timed`, `GPU_PASSES` gone); `test_the_gpu_lines_on_the_system_page` (heading "gpu per node", sample line `output.1`). `tests/test_hotreload.py` needed no change (its pinning tests are derived from the package and pass with `graph` listed). `tests/test_outputs.py` and `tests/test_render.py` untouched and green.

## Self-review findings

- Pixel parity is exact (427/427) because every painted node draws into the same framebuffer today's pass drew into, in the same order; the only reordering is `FxChain.tick()` (the folder watch) to the top of the frame, needed so `fx_on` is known before the hands' layer (its `readout` split) and the routes. Recorded as a rough edge in the register row; no golden or test sees it.
- The route stays per frame in A1 (an Output picks among the graph's pipeline ends after the hands' layer drew, since a hand showing is only known then). The node set is static per switches, so an output with hands-through on lists `composite(scene+hands)` / `fx(scene+hands)` at 0.00 with no hand or no effect. This is what A3 turns into wiring.
- Graph nodes are not hot-reload targets; they hold no GL resources, and a saved graph.py reloads render.py after it so `Renderer.on_reload` rebuilds the graph. Pinned by `test_the_graph_is_built_once_per_set_of_switches_and_reused` (including a renderer with no `_graph` attribute).
- `stats` keeps every key the tests and the golden tool read (`pipelines` in `PIPELINES` order, `chain_runs`, `direct`, `captures`, `layer`, `readout`, `gpu_ms`, `gpu_note`).

## Concerns

- None blocking. The per-node SYSTEM lines have only been seen headlessly (hand check V.4 drafted).
- Expected integration overlap: `hotreload.MODULES` with B1's `devices` (I added `graph` only).

---

## Fix report — review round 1 (commit `11443be`, pushed; PR body updated)

**What changed.**
1. *Important — the timer across a live reload.* `Renderer.timer` is not a hot-reload target, so a reload from A0's code to A1's kept an A0 `PassTimer` whose `end_frame()` takes no names: `timer.end_frame(graph.timed)` raised `TypeError` in `_draw_frame`'s `finally` on every frame. `hyperspace/render.py`: new `Renderer._drop_timer` (frees the old timer's queries through its own `_off`, best-effort, then `self.timer = None`); `on_reload` calls it beside dropping the graph; `_pass_timer` also replaces a timer whose class is not this module's `PassTimer` (a re-classed renderer that never got `on_reload`). `tests/test_graph.py::test_the_graph_is_built_once_per_set_of_switches_and_reused` gains the case: an old-shaped stand-in timer (A0's `end_frame(self)`, raising if ever used) through `on_reload` and without it — the frames draw, the stand-in is freed, `type(r.timer) is PassTimer`.
2. `hyperspace/graph.py` `Frame.routes()`: a comment naming the dependency it relies on (`Fx` after the hands' layer via `after=gate`; `Output` via its `layer` port).
3. `tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`: the "outputs.py never imports graph" assertion now walks the imports with `ast` (no substring check).
4. Decisions file (`decisions/A1.md`): rough edges now name the `lb.tick`/`pull` move (after the hands' layer) and the `target.viewport` move, both pixel-neutral, and the timer fix; a "What A3/A4 must change" section (`Scene.INPUTS` one fixed port; `Composite.paint` ignoring `over`; `Output`'s decorative ports; `Fx`'s pipeline `key`; nodes reaching renderer singletons rather than owning resources; `Frame.routes` ordering); A0's V.2 marked superseded by V.4.

**Covering tests.**
```
uv run pytest tests/test_graph.py tests/test_golden_frames.py tests/test_render.py tests/test_outputs.py tests/test_hotreload.py -q
190 passed in 28.56s

uv run pytest -q
1915 passed, 2 skipped in 142.43s (0:02:22)

uv run ruff check .
All checks passed!

uv run python tools/golden_frames.py
all 427 frames match their goldens (Apple M3 Max, 4.1 Metal - 90.5)
```
