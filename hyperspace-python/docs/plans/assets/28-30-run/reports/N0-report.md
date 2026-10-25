# N0 report — the modulation graph in dependency order

**Status:** DONE_WITH_CONCERNS. Base confirmed 5d18192. Branch `plan-28-n0-patch`. PR https://github.com/Cutaiar/hyperspace/pull/210

**Commits:**
- 6750877 patch.py, the modulation graph as data
- 2f8f5bd Router.modulate in dependency order, with its tests
- 0e4de20 ARCHITECTURE §2 draft

## What was built
- `hyperspace/patch.py`, a new leaf module. It is in `hotreload.MODULES` before `routing`.
- `Router` gains `use_lfos`, `_patch_key`, `build_patch`, a cached `patch` (the loop cut plus the evaluation plan), `patch_notes`, `patch_cut`, and the N1 seam `_step_modifier(mid, dt, lanes)`. `modulate(analyzer, dt, now)` now walks the plan in order, and the LFOs step inside it.
- `Param.apply(mark)` is idempotent within a frame. `Registry` gains `serial`, `frame`, `landed` and `begin_frame`. `Registry.apply` skips the params the pass already applied.
- `LFOs` gains `begin` and `step_one`, and `LFO.at`. A per-LFO reset is late only if that LFO has already stepped this frame.
- `app.frame` no longer steps or publishes the LFOs; it calls `router.modulate(chain, dt, now)`. `main` calls `use_lfos`.
- ROUTING's head shows the loop notes (2 lines in `ui_routing.head`).
- `docs/ARCHITECTURE.md` §2: the lag rule is redrafted.

The full PR body (assertions changed, decisions, timings) is on the PR. Decisions, hand checks and as-built notes are in `decisions/N0.md`.

## How it was tested
- **Reference copy checked first.** Before any change, I checked the base-build copy `_lagged_modulate` bit-for-bit against the real base `Router.modulate` over all 23 factory presets. That was a temporary test, since removed.
- **Gates:**
  - `uv run pytest -q`: 2247 passed, 2 skipped in 159.18s
  - `uv run ruff check .`: All checks passed!
  - `uv run pytest tests/test_golden_frames.py -q`: 7 passed in 19.68s
  - `git diff --stat 5d18192` over `library/`, `apc40.py`, `midi.py` and `tests/golden/`: empty

## Concerns
1. **More test changes than the prompt named.** Three more tests had to change because they pinned the lag or the frame's `lfos.step`:
   - `test_macros::test_a_performer_on_a_macro_moves_only_its_depth_subscribers` (decision 7)
   - the two raising-step tests in `test_app_boundary` and `test_app_bands`, which now raise in `router.modulate`

   All three are named in the PR.
2. **The equivalence test is not the prompt's literal wording.** It holds the analyzer's lanes still and keeps LFO 1 on a held square wave, so the shift comes out exact. A param a performer drives directly is asserted identical, not shifted; only params downstream of a lagged read are shifted, by their computed lag. The design's intent wins.
3. **Only read params land early.** The pass applies only the params a later node reads; leaf params are applied in `reg.apply()`. The values are identical, and no trigger fires in the middle of the pass.
4. **N1 integration needs care.**
   - N1 calls `_step_modifiers` at the top of `modulate`; drop that call and keep N1's `_step_modifier(mid, dt, lanes)` body.
   - A delay that closes a loop runs first. With N1's stateful delay that gives two frames, so it should emit its input's lane as it stands.
   - An LFO that owns its own depth is now refused as a loop until a delay modifier exists.
5. **`Router.modulate` is slower.** On party-trip with the hand tape, the base build takes about 28 µs plus 3 µs for the LFOs, about 31 µs per frame. N0 takes about 36.5 µs per frame. The extra is mostly the per-frame cache-key check.
6. **Docs outside §2.** ARCHITECTURE §3.6 and §3.9 still describe the lag. They are outside §2, so they are left for N6.

## Fix round 1 (head 9df0e8e)

**A. Merged `origin/plan-28-30-integration` (634f408, N1).**
- **Conflict resolution.** The imports keep both sides. In `Router.modulate`, N1's `_step_modifiers(analyzer, dt)` call is removed, and `_step_modifiers` itself is deleted (nothing else used it). All of N1's other methods are kept.
- **Wiring.** The plan calls `_step_modifier(mid, dt, lanes, early=, cut=)` at each modifier node. `_sync_modifiers` runs `_publish_modifiers` and prunes states whenever `modifiers_serial` moves, and on the first pass.
- **Patch edges and cache.** An empty input makes no edge. `modifiers_serial` is now in the patch key.
- **Delay closing a loop.** It emits its input's lane as it stands (its rest on the first frame), so the loop is exactly one frame late. This is tested end to end in `test_a_loop_through_a_delay_runs_exactly_one_frame_late`.
- **N1 concern 4.** It vanishes under the new order, as asserted in `test_a_modifier_node_runs_in_order_and_its_params_land_first`.
- **N1 test flipped.** `test_a_modifier_reads_another_in_id_order` became `…the_same_frame_whatever_its_id` (decision 7).

**B. A loop with no cable.** It keeps the last modifier's input off (in id order) with a note, and the cut continues to the next loop. Tests:
- the patch-level case added to `test_cycles_…`
- `test_a_loop_of_modifiers_alone_keeps_its_last_input_off_with_a_note`, which also checks that a second, cable loop is still cut

**C. Minors:**
1. `("party-tumble", "rot.rate.ZW")` is added to the not-vacuous guard.
2. The raising test now asserts `"reg.apply" not in log`.
3. `test_a_loop_through_a_scale_or_a_macro_depth_sub_is_cut` is added.
4. `Registry.apply` reads `p._bad` directly.
5. `test_main_hands_the_router_its_lfos` is added (an AST check of `app.main`).
6. The three tools are named in the as-built notes.
7. The cycle test's source grep is replaced by `tests/test_ui_routing.py::test_the_routing_head_names_a_loop_the_patch_keeps_off`, which checks the drawn text.
8. The register-row draft for the oracle's shape is in the decisions file.
9. The `routing.py` docstring now names `output.apply`.

**Commands and results:**
- Focused set (the 9 files named, plus `test_ui_routing`): 285 passed
- `uv run ruff check .`: All checks passed!
- `uv run pytest -q`: 2291 passed, 2 skipped in 243.73s
- `uv run pytest tests/test_golden_frames.py -q`: 7 passed in 20.34s
- The library, `apc40.py`, `midi.py` and goldens diff against the integration branch is empty.
- `Router.modulate` on party-trip: 37.9 µs/frame

Pushed to `plan-28-n0-patch`, PR #210.
