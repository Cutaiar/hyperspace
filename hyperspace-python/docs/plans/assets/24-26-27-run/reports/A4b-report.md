# A4b report — the point-cloud geometry node

**Status: DONE_WITH_CONCERNS** (the concerns are minor; see below)
**PR:** https://github.com/Cutaiar/hyperspace/pull/190, from `plan-26-a4b-points` into `plan-24-26-27-integration`
**Base:** `3fa2f88`, the merge of PR #187 (A3). `git log --oneline -3` at the start showed `3fa2f88` / `eb2c3de` / `19e9e6d`. The integration branch had not moved when I pushed.

## Commits
- `7c5e1db` Plan 26 A4b: the point-cloud geometry node — a cloud device's frames as points in the shared camera
- `a624947` Plan 26 A4b: golden frames of the recorded cloud — cloud/scene and cloud/scene+hands

## What was built
- **`graph.py`, a delimited block "point cloud (plan 26 A4b)":**
  - `CLOUD_KIND = "cloud"`: the kind name A4's loader maps to `PointCloud(name, role)`.
  - `CLOUD_VS` / `CLOUD_FS`: A2's point-quad arithmetic, instanced, with per-point colour.
  - `cloud_roles(source)`.
  - `_CloudGL`: the program, the quad corners and per-node buffers. It uploads only on a new (frame, t) and releases on reload.
  - `PointCloud`: a geometry, SOLID, drawn depth-tested and depth-written before the shape. It is timed under its own name. A missing or raising source draws nothing.
  - `cloud_nodes`.
- **`graph.py`, outside the block:**
  - `Graph.clouds`.
  - `default_graph(..., clouds=())` adds the nodes as the scene's first geometries.
  - The imports and one docstring line.
- **`render.py`:**
  - `Renderer.cloud_source = None`.
  - `_graph_for` is keyed on `cloud_roles(cloud_source)`.
  - `on_reload` releases `_cloud_gl`.
- **`app.py`:** one line, `renderer.cloud_source = rig`.
- **`view.py` and `params.py`:** four `cloud.*` session params (size, scale, bright, colors) and `"cloud"` added to `SESSION_GROUPS`.
- **`tools/golden_frames.py`:**
  - `CLOUD_CONFIG` / `CLOUDED`.
  - `Rig.list_devices`: a scratch `config.toml` in the rig's home, read by `config.load`, with the real registry on the pinned clock, polled in `Rig.frame`.
  - The manifest's `cloud_states`.
- **Goldens:** 4 new (legacy6 and party-faces × `cloud/scene` and `cloud/scene+hands`, hands present). The 544 existing goldens are byte-identical.

## Tests
New: `tests/test_cloud_node.py` (9 tests):
- the graph shape with and without clouds;
- `cloud_roles`;
- the params;
- the fixture's points where the CPU projection through `eye_matrix` puts them, sampled pixel by pixel with their colours, the ground elsewhere, and colours off;
- a missing cloud is byte-identical to no registry, no node without a cloud device, and a raising source draws nothing;
- one upload per recorded frame, kept across a graph rebuild;
- depth against the shape in both directions;
- the timer's `cloud` line;
- hot reload.

Changed: `tests/test_golden_frames.py::test_every_factory_preset_has_every_state_recorded_and_nothing_else` asserts `cloud_states`, includes the `cloud/*` keys and raises the count by 4. These are additions only.

```
uv run pytest -q                          → 2142 passed, 2 skipped in 257.17s (0:04:17)
uv run ruff check .                       → All checks passed!
uv run python tools/golden_frames.py      → all 548 frames match their goldens (Apple M3 Max, 4.1 Metal - 90.5)
```

**Smoke run:** a scratch home at `/tmp/a4b-smoke`, whose `config.toml` holds only the cloud `[[devices]]` block and no `[library]`, with the fixture copied to `clouds/knot.npz`.
- Command: `HYPERSPACE_FRAMES=240 HYPERSPACE_HOME=/tmp/a4b-smoke uv run hyperspace -ApplePersistenceIgnoreState YES`. It exited 0 with an empty `stall.log`.
- macOS refused `screencapture` ("could not create image from display").
- Instead, a probe (`/tmp/a4b-probe/probe.py`, not committed) wrapped `Renderer._draw_frame` in the real app for 200 frames:
  - timed lines `['cloud', 'scene', 'cover', …]` on every frame;
  - `stats["clouds"]` went `{'cloud': 96}`, then `112`, …, then `144` (the knot's frames at 12 fps);
  - no `cloud_error`;
  - the GPU median for `cloud` was 0.00 ms;
  - the back buffer at frame 150 held 509 warm-coloured pixels, the knot's upper half.
- What I saw on the golden contact sheet: in LEGACY 6 the knot's dots (blue low, orange high) thread through the tesseract, with the near edges drawing over the dots behind them. In PARTY FACES the knot is mostly hidden behind the bright faces and shows at the sides.

## Files changed
`hyperspace/graph.py`, `hyperspace/render.py`, `hyperspace/app.py`, `hyperspace/view.py`, `hyperspace/params.py`, `tools/golden_frames.py`, `tests/test_cloud_node.py` (new), `tests/test_golden_frames.py`, `tests/golden/frames/frames.json` and 4 PNGs under `tests/golden/frames/png/`. Nothing under `hyperspace/library/`. No fixture was added: B4's `knot.npz` is reused.

## Self-review / concerns
1. **Files outside the dispatch's list:** `params.py` and `view.py`, needed to register the `cloud.*` params. `ghost.*` lives in `ghost.py`, but the cloud has no state object of its own. A4 does not touch these two files, so I expect no conflict.
2. **Commit trailer:** my commits carry `Co-Authored-By: Claude Opus 5.5`, from the session's attribution instruction. The common brief's template said `Claude Fable 5.1`. Say if they should be amended.
3. **A4 overlap:**
   - `default_graph` gains a `clouds` parameter, and `Graph` gains a `clouds` attribute.
   - `_graph_for` gains a third key component.
   - If A4 replaces `_graph_for` or `default_graph` with a JSON-built graph, whoever lands second must keep the cloud roles in the key and keep the cloud nodes in the default scene.
   - The kind name is `cloud`.
4. **Rough edges, all registered:**
   - Dots have hard edges and a constant pixel size.
   - The world transform is scale-only.
   - Only devices of kind `cloud` are found (plan 29's sensors need one line).
   - A second cloud node shares `cloud.*`.
   - There is no panel row for `cloud.*`.
   - An unlisted node's buffers are kept until a reload.
5. **Depth test thresholds:** the depth test checks a few points in each direction (3 and 4 at the measured setup). The counts are deterministic but small.
6. **Unverified:** nobody has looked at it on a screen.

## Decisions file
`/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/A4b.md`: six register-row drafts, hand checks V.A4b.1–3, the as-built notes, and where the code differs from the dispatch (`cloud_source` rather than `clouds`, the params' location, no UI row).

## Merge round (origin/plan-24-26-27-integration into plan-26-a4b-points)

Merge commit a47d795 (pushed to plan-26-a4b-points; the local branch name was held by A4b's original worktree, so the merge was made on the session branch and pushed as HEAD:plan-26-a4b-points).

Conflicted files and resolution:
- hyperspace/graph.py: module docstring merged (A4's per-instance hands + A4b's point cloud); imports are the union (`math`, `re`, `replace`); A4b's whole point-cloud block and A4's `ghost_of` both kept; `default_graph` docstring keeps A4's paragraph then A4b's; scene line rewritten in A4's terms: `[*points, *(geo[h.n] for h in inside), shape]`. `Graph.clouds` and `CLOUD_KIND` kept. A4's JSON graph section reaches the graph only as a `Wiring` passed to `default_graph`, so `Graph.clouds` is set on every graph (no other builder exists). No `cloud` kind added to `NODE_KINDS` (ruling); the `CLOUD_KIND` comment that said "A4's graph JSON names it" was reworded to state the ruling.
- hyperspace/render.py: `__init__` keeps `cloud_source` and A4's `ghost_states`/`_ghosts`; `on_reload` releases `_cloud_gl` then calls `drop_ghosts()`; `_graph_for` keys on `clouds` and calls `default_graph(views, wiring, clouds)` then A4's `drop_ghosts({...ghost.*})`. `cloud_roles` import kept.
- tests/test_golden_frames.py: completeness subtracts both `clouded` and `fixture`; count `... + 2 + 2 * 2 + 8` = 556.
- tools/golden_frames.py: docstring, `CLOUDED` and `FIXTURES`/`FIXTURE_PRESETS`, the per-preset `CLOUDED` loop and A4's outer fixture loop, and the manifest's `cloud_states` + `fixture_states`/`fixtures` all kept. tests/golden/frames/frames.json auto-merged: 556 unique goldens, both `cloud_states` and A4's `fixture_states`/`fixtures`/graph text present. Nothing re-recorded.

Gates (from hyperspace-python/):
- uv run pytest -q → 2183 passed, 2 skipped
- uv run ruff check . → All checks passed!
- uv run pytest tests/test_golden_frames.py -q → 7 passed; uv run python tools/golden_frames.py → all 556 frames match their goldens (Apple M3 Max)
- hyperspace/library/ byte-identical to both parents.

Rough edge for plan 28: a second listed cloud role gets node `cloud.2` (A4's naming rule) but still reads the shared `cloud.*` params; its own params are not declared.
