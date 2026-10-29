# The review pass's fix wave — plans 24, 26 and 27

Branch `plan-24-26-27-review-fixes` off `plan-24-26-27-integration` at
3a0b60d. PR title: `Review: the fix wave of plans 24, 26 and 27's review pass`.
Every commit is titled `Review: <what was fixed>`. One implementer, every
item below, in order. Nothing else.

## Setup (from your worktree root)
```
git fetch origin plan-24-26-27-integration
git reset --hard FETCH_HEAD          # HEAD must be 3a0b60d
git branch -m plan-24-26-27-review-fixes
```
Run everything from `<worktree>/hyperspace-python`. Rules: the common
brief at `docs/plans/assets/24-26-27-run/briefs/common.md` (its workspace
paths are replaced by the ones at the end; use your own session's commit
attribution). Never touch `~/Hyperspace` or `~/My Drive/Hyperspace`;
`hyperspace/library/` byte-identical; **no golden may move** (run the
golden test after the code changes: 556 must match; if one moves, the
change is wrong — do not re-record).

## The findings (the reviewer's text; file:line as of 3a0b60d)

### Important 1 — "Learn bridge" is offered and never completes
- **Where:** `hyperspace/devices.py:594–596` (`BridgeDevice`).
- **What's wrong:** `feeds = ("ext",)` makes `Base.wants` return
  `("bridge",)`. The class has no `learn`, so every modulatable param menu
  on a rig that lists a bridge (on or off) offers an item nothing can
  complete.
- **Code fix:** add `wants: tuple[str, ...] = ()` under `feeds = ("ext",)`,
  with a comment that the bridge feeds but cannot complete a Learn, the
  same as `MidiOutDevice:701`. `OffDevice` reads `cls.__dict__["wants"]`,
  so an off bridge then offers nothing too.
- **Test:** add one to `tests/test_devices.py`:
  ```python
  reg = devices.DeviceRegistry(devices=[devices.BridgeDevice("bridge"), devices.OffDevice("b2", "bridge")])
  assert reg.wants() == ()
  ```
  (adapt the constructor to the real signatures; the assertion is the point:
  a rig with an on bridge and an off bridge wants nothing).
- **Docs** (all on 3a0b60d; re-find by text if lines drift):
  - `docs/DECISION-REGISTER.md:145`: drop the "(…never completes)" title.
  - `docs/DECISION-REGISTER.md:2355–2360`: replace the Rough edge with a
    line saying the bridge has `wants = ()`, fixed in the review pass.
  - `docs/plans/27-device-registry.md:423–429`: delete the bullet.
  - `docs/plans/11-hand-checks.md:2465–2468`: delete the "**Known:** …
    (register row 151)." sentence in check 178.
  - `docs/TESTING-GUIDE.md:1635–1638`: delete the "**Known:** …" paragraph
    (L75).
  - `docs/CHECKPOINT.md:70–71`: drop the Learn bridge clause from Known
    faults.
  - `docs/ENGINEERING.md:1450–1451`: delete the sentence.
  - `docs/ENGINEERING.md:2038–2041`: delete the bullet.
  - `docs/ARCHITECTURE.md:775–778` and the same bullet in
    `docs/ARCHITECTURE.html`: delete or reword it.
  - Mark the item done in `docs/plans/24-26-27-handoff.md:128`.

### Important 2 — the first-frame stall the smoke gate logged
- **Where:** `hyperspace/geometry.py:808` (`_is_boundary_face`).
- **What's wrong:** the line calls `np.random.default_rng(1)`, which
  triggers numpy's lazy `__getattr__` import of `numpy.random` on the
  render thread: the 2.2 s stall on the cold run (the smoke report,
  `docs/plans/assets/24-26-27-run/reports/smoke-report.md`, stream B). It
  is the package's only `np.random` use.
- **Fix:** add `from numpy.random import default_rng` after
  `import numpy as np` (geometry.py:13) and call `default_rng(1)` at :808.
- **Check:** the same generator and seed, so `tests/test_golden.py`,
  `test_core.py` and `test_shapes4d.py` digests cannot move. Run them and
  ruff. Then **re-run the stream B smoke run** exactly as the smoke report
  did it (its config.toml and command are in the report; use a fresh
  scratch home under `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/B2/`;
  `-ApplePersistenceIgnoreState YES`), twice from cold, and paste the
  stall log (it must be empty) in your report.

### Minor 3 — `tools/slew_demo.py` still labels pan readings "px"
Since A2, `camera.pan` is world units with `PAN_RANGE` 12, so the `:.0f`
readings print 0 or 1 and the plot's 400-step grid collapses.
- Change "px" to "units" and `.0f` to `.2f` at :131 (comment), :225, :243,
  :247, :249, :253 and :273. Line :319: "px" → "units". Lines :302 and
  :312: grid step `400` → `2`. Line :359:
  `slow_turn(PAN, K_PAN, "px", ".1f")` → `"units", ".3f"`.
- Leave the committed plan-18 transcript and PNG alone; they are history.

### Minor 4 — pin the presenter with a second hands node
Commit the reviewer's scratch test as
`tests/test_hands_node.py::test_a_second_hands_node_on_a_presenter_glass_matches_the_target`.
The reviewer's scratch file is at
`/Users/dallman/.claude/jobs/b8e1c57e/tmp/rv/scratch/test_scratch_presenter.py`
(it passed on HEAD with `PYTHONPATH=tests -p conftest`); lift it into the
test module's own fixtures. Its shape:
```python
r = rig(ctx, effects=(), guide=1, dim=0.8)
r.ghost_states = {"ghost.2": GhostState(on=True, alpha=0.25, guide=1)}
r.wiring = Wiring(hands="scene", extra=(HandsAt(2),))
pairs = [(S(dim=0.5), (640, 400)), (S(scene=False), (640, 400)),
         (S(scene=False, through=True), (640, 300))]
```
For each pair, `np.array_equal(target, presented)`; also assert
`r.ghost_of("ghost.2") is not r.ghost`, and that the glass is lit.

### Minor 6 — A4b's two lines
- `Renderer.__init__` (render.py, near `self._ghosts` at :920) never sets
  `_cloud_gl`. Add `self._cloud_gl = None`; the getattr guards stay for hot
  reload.
- `_CloudGL.upload` (graph.py:845–848) sizes the orphaned buffer from
  `data.nbytes` before converting to float32. Convert first, then orphan
  and write: `arr = np.ascontiguousarray(data, dtype=np.float32);
  buf.orphan(max(arr.nbytes, 12)); buf.write(arr)`.

### Minor 7 — check 56
`docs/plans/11-hand-checks.md:691` still describes the clip-stop SAVE AS
bar retired on 2026-10-09; its Headless list names
`tests/test_desk.py::test_the_clip_stop_row_is_invariant`, which no longer
exists. Retitle it: "**56. (Retired 2026-10-09: the clip-stop save bar.)**
The save is check 148; the hold on an empty pad is #158's". Drop the dead
test name; cut the body down to the steps that still apply (the slot
menu, steps (g) and (h)) and mark the rest historical.

### Docs lines the orchestrator rules in (no code)
- **Minor 5, registered, not built:** a presenter lays the readout at the
  laid ghost's alpha (`Handoff.alpha` = `gh.state.alpha`, outputs.py:355)
  where the local path uses the readout ghost's own (`rg`); they differ
  only when a JSON graph makes a node other than ghost 1 the first
  in-scene hands node. Add one line to `docs/plans/26-render-graph.md`'s
  "Known rough edges" saying exactly that, and that plan 28 (which lets a
  graph say it) should add `readout_alpha` to `Handoff`.
- **C5's grab hold:** a closed grab holds while the skeleton is missing
  (a palm-only frame leaves `fist` None, so the gate holds;
  `hands/core.py:1557`). Add one line to `docs/plans/24-party-fixes.md`'s
  "Known rough edges".
- **C4's tether:** `ghost.routed_rows` gives the dance rows no tether on
  the ghost (cosmetic, no wrong value). One line in the same list.
- `docs/plans/11-hand-checks.md:13` still says group R needs plan 22 "on
  `plan-22-integration` until it is merged"; plan 22 is on `main` (#151).
  Fix the sentence.
- Append to `docs/plans/26-render-graph.md`'s "What no person has
  verified" (or the rough edges, wherever it fits) nothing else: the
  review pass's other triage calls are already registered where the
  reviewer says they are.

## Gates before the PR (from `hyperspace-python/`)
```
uv run pytest -q                                   # 2190 + your new tests
uv run ruff check .
uv run pytest tests/test_golden_frames.py -q       # 556 match, none re-recorded
uv run pytest tests/test_golden.py tests/test_core.py tests/test_shapes4d.py -q
git diff --stat main -- hyperspace/library/        # empty
```
And the stream B smoke run twice from cold with an empty stall log
(Important 2).

## Report and PR
Report to `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/reports/review-fixes-report.md`
(fallback `<worktree>/.sdd/review-fixes-report.md`): per item what
changed (file:line), the tests, the gate lines, the smoke stall logs. PR
into `plan-24-26-27-integration` with the title above; body = the items,
one line each, and the gates. Reply with ONLY (under 15 lines): Status;
base SHA; commits; PR URL; gate lines; the smoke stall-log result;
concerns; report path.
