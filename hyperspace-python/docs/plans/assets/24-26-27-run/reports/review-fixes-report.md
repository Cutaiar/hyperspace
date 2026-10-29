# Review fixes report — plans 24/26/27

Branch `plan-24-26-27-review-fixes`, base 3a0b60d (reset onto origin/plan-24-26-27-integration, confirmed). PR https://github.com/Cutaiar/hyperspace/pull/194 into `plan-24-26-27-integration`.

## Commits
- 8946084 Review: the bridge arms no Learn (wants = ()), and its known-fault docs
- 32aef3a Review: import numpy.random at load, not on the render thread's first frame
- f89b79d Review: slew_demo reads pan in world units, not px
- 5bb015d Review: pin a second hands node on a presenter glass
- b198be3 Review: the renderer sets _cloud_gl; a cloud upload sizes its buffer as float32
- 84869e3 Review: retire check 56's clip-stop bar; group R's plan 22 is on main
- 3279d3a Review: register the presenter's readout alpha, the grab hold and the dance rows' tether

## Per item
- **Important 1.** `hyperspace/devices.py` BridgeDevice: `wants: tuple[str, ...] = ()` under `feeds`, with comment. New test `tests/test_devices.py::test_a_bridge_on_or_off_arms_no_learn` (BridgeDevice("bridge", io=...) + OffDevice("b2", "bridge") -> `reg.wants() == ()`). Docs: DECISION-REGISTER row 151 title + rough edge rewritten ("wants = (), fixed in the review pass"); 27-device-registry.md bullet deleted; 11-hand-checks check 178 "Known" sentence deleted; TESTING-GUIDE "Known" paragraph deleted; CHECKPOINT Known-faults clause dropped; ENGINEERING sentence + bullet deleted; ARCHITECTURE.md bullet deleted; handoff item marked "Done in the review pass". ARCHITECTURE.html has no such bullet (grep for Learn bridge / inherits / row 151 / R14 finds nothing: the HTML lags the .md), so nothing to edit there.
- **Important 2.** `hyperspace/geometry.py:14` `from numpy.random import default_rng`; `_is_boundary_face` calls `default_rng(1)` (geometry.py:809). test_golden/test_core/test_shapes4d: 167 passed; ruff clean.
  Smoke: stream B config from the smoke report, knot.npz copied, fresh scratch homes `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B2/run1/home` and `.../B2/run2/home`; command `env -u VIRTUAL_ENV HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<home> uv run hyperspace -ApplePersistenceIgnoreState YES`. run1: exit=0, `stall.log` 0 bytes. run2: exit=0, `stall.log` 0 bytes. Logs `.../smoke/B2/run1.log`, `run2.log` (only the ApplePersistenceIgnoreState line). Caveat: "cold" = new process + fresh home; the OS disk cache was not purged (needs sudo), and this worktree's .venv had already run pytest.
- **Minor 3.** `tools/slew_demo.py`: comment :131, lines 225/243/247/249/253/273 -> `.2f` units (273's `was` too), axis label "units" (:319), grid `400` -> `2` at :302 and the range at :314 (the brief said :312), `slow_turn(PAN, K_PAN, "units", ".3f")` (:359). Ran it to scratch output: transcript reads "one detent is 0.240 units", plot grid 0/2/4/6. Committed plan-18 transcript/PNG untouched.
- **Minor 4.** `tests/test_hands_node.py::test_a_second_hands_node_on_a_presenter_glass_matches_the_target`, on the module's own `ctx` fixture, `rig`, `S`, `G.GhostState`, `HandsAt` (import added); passes.
- **Minor 6.** `render.py` Renderer.__init__: `self._cloud_gl = None` after `self._ghosts`; `graph.py` `_CloudGL.upload`: `arr = np.ascontiguousarray(data, dtype=np.float32); buf.orphan(max(arr.nbytes, 12)); buf.write(arr)`.
- **Minor 7.** Check 56 retitled "(Retired 2026-10-09: the clip-stop save bar.) The save is check 148; the hold on an empty pad is #158's"; `test_desk.py::test_the_clip_stop_row_is_invariant` dropped (every other Headless name verified to exist); body = (g) slot menu and (h); (a)-(f) summarised as historical. (h) originally held the retired row; reworded to hold an empty bank pad (#158) with Learn desk armed. Bank pads are invariant rows (apc40.py ~481), so the learn does not take the press and the save happens. Flagging the rewording.
- **Docs only.** 26-render-graph.md Known rough edges: the presenter readout-alpha line + plan 28 `readout_alpha`. 24-party-fixes.md Known rough edges: grab holds on a palm-only frame; routed_rows gives the dance rows no tether. 11-hand-checks.md:12: plan 22 is on main (#151).

## Gates
```
uv run pytest -q                              2192 passed, 2 skipped in 162.00s
uv run ruff check .                           All checks passed!
uv run pytest tests/test_golden_frames.py -q  7 passed (frames.json: 556 goldens, Apple M3 Max; byte-for-byte test ran, not skipped)
uv run pytest tests/test_golden.py tests/test_core.py tests/test_shapes4d.py -q   167 passed
git diff --stat main -- hyperspace/library/   (empty)
git diff --name-only 3a0b60d -- tests/golden hyperspace/library   (empty)
```
~/Hyperspace and ~/My Drive/Hyperspace never touched.
