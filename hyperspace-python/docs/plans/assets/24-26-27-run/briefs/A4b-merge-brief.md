# A4b merge round — merge the integration branch into `plan-26-a4b-points`

PR #190 "Plan 26 A4b: the point-cloud geometry node — B4's recorded cloud
drawn in the shared camera" (branch `plan-26-a4b-points`, head a624947, off
3fa2f88) is **reviewed and approved** with minors only. It was built in
parallel with A4 (PR #191, now merged into `plan-24-26-27-integration` at
de63356), and both edit `hyperspace/graph.py`, `render.py`,
`tests/test_golden_frames.py` and `tools/golden_frames.py`. Your job is one
round: merge `origin/plan-24-26-27-integration` into A4b's branch, resolve
the overlaps as the orchestrator rules below, run the gates, push, and
report. You write no new feature.

## Setup (from your worktree root)
```
git fetch origin plan-26-a4b-points plan-24-26-27-integration
git reset --hard origin/plan-26-a4b-points      # HEAD must be a624947
git branch -m plan-26-a4b-points
git merge --no-ff origin/plan-24-26-27-integration
```
Resolve, commit the merge, then run from `<worktree>/hyperspace-python`.

## The resolution rules (the orchestrator's; A4's reviewer confirmed the shape)
Keep both WPs' work; never revert a line of either.
- `graph.py`: keep A4b's `default_graph(views, wiring, clouds=())` with the
  clouds as the scene's **first** geometries; A4 rewrote the scene line
  with per-instance hands, so the merged scene list is
  `[*points, *(geo[h.n] for h in inside), shape]` (A4b's line referred to a
  `hands` variable A4 removed — rewrite it in A4's terms). Keep A4b's
  `Graph.clouds` field and `CLOUD_KIND`; A4's JSON loader (`GraphSection`
  / the spec → graph builder) must also set `Graph.clouds` (else
  `_graph_for` rebuilds every frame when a cloud is listed). Keep A4b's
  `cloud_roles(...)` in `_graph_for`'s key and its `.graph` import of
  `cloud_roles` in `render.py`. The two `on_reload` additions
  (`drop_ghosts`, `_cloud_gl.release`) sit side by side.
- **Ruling: clouds follow the device list, not the preset's graph
  section.** Do not add a `cloud` kind to A4's `NODE_KINDS`; a JSON graph
  that names `{"kind": "cloud", …}` is an unknown kind (a note and the
  default graph), as A4 built it. So there is no "two nodes for one role"
  case in this run. The second cloud: a second cloud role shares `cloud.*`
  today — leave it, and write it in your report as a rough edge for plan
  28 (A4's naming rule would give it `cloud.2`).
- `tests/test_golden_frames.py` / `tools/golden_frames.py`: both WPs add
  states and manifest keys — the completeness count must be the union
  (A4's 552 + A4b's 4 = **556**), and the manifest must carry A4's landed
  `graph` section text *and* A4b's cloud keys.
- Anything else that conflicts: keep both; if a line cannot be both, stop
  and report BLOCKED with the hunk.

## Gates (from `hyperspace-python/`)
```
uv run pytest -q                          # expect 2174 + A4b's tests
uv run ruff check .
uv run pytest tests/test_golden_frames.py -q   # 556 frames, all match
```
**Re-record nothing.** If a golden fails after the merge, that is a wrong
resolution, not a frame to re-record: find it. (A2b's stroke change is
not on the integration branch yet; it merges after you.)
`hyperspace/library/` stays byte-identical; never touch `~/Hyperspace` or
`~/My Drive/Hyperspace`.

## Report
Append a "Merge round" section to
`/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/reports/A4b-report.md`
(fallback `<worktree>/.sdd/A4b-merge-report.md`): each conflicted file and
what you kept from each side, the gate lines, the rough edge. Push the
branch (`git push origin plan-26-a4b-points`); the PR updates itself. Reply
with ONLY: Status; the merge commit SHA; the conflicted files and one line
each on the resolution; the gate lines; concerns; the report path.
