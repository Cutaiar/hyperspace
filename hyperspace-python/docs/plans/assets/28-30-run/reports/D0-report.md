# D0 report — the effect node, and the chain as a run of them

**Status:** DONE_WITH_CONCERNS. The one concern is the timer's per-effect split on this GPU (see Concerns).

- Base: `5d18192`, confirmed with `git log --oneline -1` after the reset.
- Branch: `plan-30-d0-effect-nodes`.
- PR: https://github.com/Cutaiar/hyperspace/pull/208

## What was built

- **`graph.Effect(name, *, image=None, node=None)`**: kind `effect`, one `IMAGE` in, `IMAGE` out.
  - `effect` is the instance name. `name` is the node name, from `effect_node_name`: `acid` in the scene pipeline, `acid(scene+hands)` / `acid(hands)` in the others, with an `fx.` prefix when the name collides with another node.
  - **Off:** reads its input through. `paint` paints the input into the consumer's framebuffer and `image` is the input's, so no pass runs and no texture is taken.
  - **On:** paints its input into a pool texture (`graph._spare`), then runs `FxChain.run_one` into `dst` under `frame.timed(name)`. The pass is recorded in `frame.stats["effects"]`.
  - With more than one reader it is made once into a held texture and shown 1:1 into each reader.
- **`graph.Fx`** stays as the pipeline end.
  - Its input is the last effect. `effects`, `source`, `layer` and `bent` walk back through the run, and `Output.settle` uses `end.source.blend`.
  - `paint` moves the clocks, paints its input, and counts `chain_runs`. `run` is unchanged.
- **`graph.Graph`** gains `readers`, `pool`, `effects` and `timed_in(frame)`. `default_graph(..., effects=())` builds the runs.
- **`fx.FxChain`** gains `pool`, `fit_pool`, `ready` and `run_one`, plus `_uniforms` / `_opaque`, which `run` now shares. `begin` now goes through the pool. `run` is kept for the faces chain.
- **`render.Renderer`**: the `_graph_for` key now includes `FxState.names()`, and a new graph calls `fit_pool`. `stats["effects"]` is added, and the timer is handed `timed_in(frame)`.
- **`ui.Panel.gpu_lines`**: docstring only. The lines come from `gpu_ms` already.

## Tests

`tests/test_graph_effects.py` has 11 tests:

- the five named in the WP section;
- `an_effect_named_like_another_node_is_kept_apart`
- `an_effect_node_takes_an_image_and_makes_one`
- `the_renderer_builds_the_run_from_the_stack_and_a_toggle_does_not_rebuild`
- `an_effect_read_by_two_runs_once_into_a_held_texture`
- `the_run_draws_what_the_one_block_chain_drew`, which runs twice (parametrised). It compares the new run byte for byte against the pre-D0 `Fx.paint`, copied verbatim, through all three pipelines.

Changed assertions (named in the PR body):

- **The timer's list gains the effect line** (decision 5):
  - `test_graph.py::test_the_timer_lists_the_graphs_nodes_and_drops_a_node_that_left`
  - `test_golden_frames.py::test_each_node_has_a_rolling_median_in_ms`
- **Spy on or break `run_one` instead of `run`**, because the frame chain no longer calls `run`:
  - `test_render.py::test_one_clock_reaches_the_patterns_and_the_effects`
  - `test_render.py::test_a_frame_effect_runs_over_a_face_effect`
  - `test_outputs.py::test_a_raising_pipeline_leaves_its_views_on_the_ground_and_the_rest_drawn`

Untouched: `test_render.py::test_the_render_stack_imports_no_registry`, the import test in `test_graph.py`, and every golden hash. The goldens' recorded `said.nodes` still match because `Graph.timed` is unchanged.

### Gate outputs

```
uv run pytest -q                       -> 2249 passed, 2 skipped in 253.33s (base 2238 + 11 new)
uv run ruff check .                    -> All checks passed!
uv run pytest tests/test_golden_frames.py -q -> 7 passed in 26.22s (all 556 goldens byte for byte, Apple M3 Max)
windowed smoke (HYPERSPACE_FRAMES=120, scratch home, [midi] enabled=false, no [library]) -> exit 0
git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py -> empty
```

Windowed smoke run:
`HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<worktree>/.sdd/home uv run hyperspace -ApplePersistenceIgnoreState YES`

- It exited 0.
- The log holds only the config migration note (`[midi]` became a `[[devices]]` entry, with `enabled = false` honoured) and the dream line.
- The scratch `config.toml` is just `[midi] enabled = false`, with no `[library]`.

### Measurement: party-acid, headless

The run used the golden tool's rig with the same scratch home. Settings: 1920×1080, 4× MSAA, 180 frames, 3 alternating rounds. The script is `<worktree>/.sdd/scripts/measure.py`.

**GPU timer lines (ms):**

| Line | Median | Rounds |
|---|---|---|
| Old `fx` line | 0.225 | 0.242 / 0.225 / 0.215 |
| New sum of lines | 0.089 | 0.134 / 0.083 / 0.089 |

The new per-effect medians across the rounds:

| Effect | Rounds (ms) |
|---|---|
| `acid` | 0.021 / 0.003 / 0.026 |
| `wobble` | 0.015 / 0.001 / 0.008 |
| `deconverge` | 0.005 / 0 / 0 |
| `huecycle` | 0.093 / 0.079 / 0.055 |
| end `fx` | 0 |

**Frame wall time (ms, `ctx.finish` around each frame):**

| Version | Median | Rounds |
|---|---|---|
| Old | 1.69 | 1.95 / 1.68 / 1.69 |
| New | 1.76 | 2.04 / 1.56 / 1.76 |

The two are the same within noise.

**Off effects:** `run_one` ran 4.0 times per frame, which is exactly the 4 on effects (acid, wobble, deconverge, huecycle). The 9 off effects ran 0 passes.

## Files changed

- `hyperspace-python/hyperspace/graph.py`
- `hyperspace-python/hyperspace/fx.py`
- `hyperspace-python/hyperspace/render.py`
- `hyperspace-python/hyperspace/ui.py` (docstring)
- `hyperspace-python/tests/test_graph_effects.py` (new)
- `hyperspace-python/tests/test_graph.py`
- `hyperspace-python/tests/test_golden_frames.py`
- `hyperspace-python/tests/test_render.py`
- `hyperspace-python/tests/test_outputs.py`

## Self-review findings

- **Pixel identity.** The last on effect writes the end's `dst` directly, as the old last pass did. Earlier passes alternate the same `f2` textures. BLEND is disabled around each pass rather than once around the block, and nothing draws between passes. All 556 goldens pass, and the byte-for-byte test against the old block passes on any GL.
- **Ping-pong with recursion.** An effect's source is "a pool texture that is not `dst` and not held". The effect before it writes that texture from `dst`'s twin before `dst` is written, so two textures suffice. The test `the_run_draws_what_the_one_block_chain_drew`, with off effects between on ones, exercises this.
- **Timer nesting.** Each effect's query brackets only its pass, after its input has painted. The end does not time around its input, so its line is 0.
- **Clocks.** `advance_to` runs in `Fx.paint` and in `run_one`. It is idempotent per `t`, so the clocks move once a frame. Capture's fallback is unchanged.
- **Graph shape.** A toggle keeps the graph object (tested). An order, instance or file change rebuilds it, which costs about 55 nodes once.
- **Not done.** A hot reload mid-show with a run is not tested. It relies on the existing `on_reload` dropping `_graph`.

## Concerns

1. **The per-effect lines are indicative, not exact.** On Apple's tile-based GPU a query is charged for whatever is flushed inside it. The new lines sum to less than the old `fx` line, never more (the review flag is the other way), but the split moves between rounds. Wall time is unchanged.
2. **Two departures from the prompt, both written down in `decisions/D0.md` §4:**
   - The run is `FxState.names()`, every instance and every target. `chain(FRAME)` is used only as the per-frame on-test, because `chain()` lists on effects only.
   - The pool lives on `FxChain` and is fitted to each graph, rather than owned by the graph object.
3. **Compile failures.** An effect whose file never compiled now reads through. The old block copied the picture through a half-float texture instead.

Decisions file: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/D0.md`, with 5 row drafts, hand checks X.1–X.3, and as-built notes.


## Fix round 1 (commit 6c67ef2, pushed to PR #208)

- **IMPORTANT 1: held effect aliasing.**
  - What changed in `graph.py`: `Effect.paint`'s held branch now calls `Effect._make(frame, avoid=dst)`. `_make` picks the held texture with `_spare(frame, dst, hold=True)`, so it is never the consumer's `dst` and never a texture already held. `image()` calls `_make(frame, None)`.
  - Why later consumers are safe: a held texture is never handed out again that frame, so no later consumer's `dst` can be it.
  - Pool size is unchanged: 2 plus one per held effect.
  - New test `test_a_held_effect_read_through_the_pool_is_never_its_consumers_target`: an on `kaleido` reads a `warp` that has two readers, through the pool. It checks that no pass reads the texture it writes, that warp's pass wrote into the held texture, that kaleido's source is not the held texture, that exactly one texture is held, and that the pixels equal the straight run's byte for byte.
  - I confirmed the test fails with the old code by temporarily passing `None` as `avoid`: `assert <Texture> is not <Texture>`. Then I restored the fix.
- **MINOR 1: reserved names.** The collision rule in `default_graph.run` now reserves `("capture", *FX_NAMES.values())`, so an effect named `fx` becomes `fx.fx` and `fx.fx(scene+hands)`. This is asserted in `test_an_effect_named_like_another_node_is_kept_apart`.
- **MINOR 2: fragment source built twice.** Left as is and recorded as a rough edge, with the reason, in `decisions/D0.md`.
- **MINOR 3: decisions file.**
  - Row 1 and check X.1 now say plainly that the `fx` line reads 0.00 by design and that this does not mean the effects are free.
  - Row 3's rough edge now names the dst-aliasing constraint and the fix D1 inherits.
- **PR body.** It names the `test_each_node_has_a_rolling_median_in_ms` change as forced by decision 5, as ruled, and gained a "Review round 1" section.

### Tests

```
uv run pytest tests/test_graph_effects.py tests/test_graph.py tests/test_render.py tests/test_fx.py -q  -> 218 passed in 18.03s
uv run ruff check .                                                                                    -> All checks passed!
uv run pytest tests/test_golden_frames.py -q                                                           -> 7 passed in 18.76s (every frame matches)
```
