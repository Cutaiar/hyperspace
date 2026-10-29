# Review fix: the ROUTING page rebuilt two lists every frame

Branch `review-routing-fps` off `plan-24-26-27-integration` (a661fa0 or
later). PR title: `Review: the ROUTING page caches its source list and its
unmapped controls (35 fps → full rate)`. Commits titled `Review: <what>`.
This lands on PR #195's branch before the owner merges it. No behaviour
change: the page shows exactly what it shows today; it just stops
recomputing it.

## The finding (the investigator's, measured; report at
`/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/reports/routing-fps-report.md`,
its measurement scripts under `/Users/dallman/.claude/jobs/b8e1c57e/tmp/routing-fps/tools/`)
On the branch, 600 frames with party-trip: the panel costs 17.7 ms a frame
on ROUTING (48 fps on the laptop, 35 on the rig) against 1.05 ms on any
other page; CPU, not GPU. Main already spent 12.0 ms. Two per-frame
rebuilds of lists that only change when the table changes:
1. `ui_routing.unmapped()` (ui_routing.py:1071, called from `desk()` at
   :1124) → `preset_controls()` → `Bindings.is_invariant()`
   (routing.py:1932) → `Binding.overlaps()` (routing.py:705): about 4,400
   pairwise compares a frame, each reparsing source strings. 9.5 ms.
2. `ui_routing._sources()` (ui_routing.py:513) rebuilt once per route row
   from `_row` at :692, 21 times a frame; each call scans all 209 bindings
   per scheme. 5.15 ms.
With both cached in the investigator's script the page cost 3.2 ms.

## The fix (approved by the owner, 2026-10-15)
- Build `_sources` **once per page draw** and pass it into `_row` (or
  stash it on the page's `_state` for the frame). Same list, same order.
- Memoize `unmapped()` / `preset_controls()` on a cheap **table
  signature** that changes with any edit that could change the answer: the
  profile, and for every binding its source, layer, enabled flag, target
  and device (the investigator suggested
  `(profile, tuple((b.source, b.layer, b.enabled) for b in bindings))`;
  check `overlaps()` and `is_invariant()` to see which fields matter and
  include every one of them — a stale list of dark controls after a row
  edit, a Learn, a template apply, a load or a layer flip is the failure
  mode; row **identity** changes (a new Binding object with the same
  fields) must not matter, field changes must). Keep it simple: a tuple
  compared each frame is fine; do not reach for a dirty flag threaded
  through the router unless the signature cannot be made correct.
- If `Bindings` already has a change counter or serial (grep `serial`,
  `version`, `_rev`, `layer_serial` in routing.py / midi.py), prefer
  keying on that plus the profile, and say so.

## Tests first (TDD)
In `tests/test_ui_routing.py` (read its existing harness: how it draws
the page headless with the imgui stub, and how a Router with a table is
built):
- Draw ROUTING twice with N route rows: `_sources` runs once per draw
  (count calls with monkeypatch), not once per row.
- `preset_controls` (or whatever the memoized unit is) runs once across
  two draws with an unchanged table; runs again after (a) a desk row is
  added via the same path Learn uses, (b) a row's `enabled` is flipped,
  (c) a preset load replaces the table, (d) the profile changes; and the
  unmapped list is correct after each (compare with an uncached call).
- The existing ROUTING tests all pass unchanged.
Then the measurement: run the investigator's script (or your own, from
its tools folder) before and after on the branch and paste the ms/frame
on ROUTING and on CAMERA in the report; the target is under 4 ms on
ROUTING with party-trip at 960×600 and no devices.

## Rules
Common brief: `hyperspace-python/docs/plans/assets/24-26-27-run/briefs/common.md`
(the workspace paths are replaced by the ones here; your own session's
attribution). Never touch `~/Hyperspace` or `~/My Drive/Hyperspace`; every
run uses a scratch `HYPERSPACE_HOME` under
`/Users/dallman/.claude/jobs/b8e1c57e/tmp/routing-fps/`; a windowed run
needs `-ApplePersistenceIgnoreState YES`. `hyperspace/library/` byte-
identical; no golden moves (the page is not in a golden; run the golden
test anyway). No sub-agents.

Also append one line to
`hyperspace-python/docs/plans/assets/24-26-27-run/progress.md` under a new
`## After the final PR (2026-10-15)` heading: the owner's first launch
passed, the ROUTING page's cost, the root cause and this fix.

## Setup
```
git fetch origin plan-24-26-27-integration
git reset --hard FETCH_HEAD           # HEAD must be a661fa0 or later
git branch -m review-routing-fps
```
Run from `<worktree>/hyperspace-python`.

## Gates
```
uv run pytest -q                      # 2193 + yours
uv run ruff check .
uv run pytest tests/test_golden_frames.py -q
```

## Report and PR
Report to `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/reports/routing-fps-fix-report.md`
(fallback `<worktree>/.sdd/…`): the signature you chose and why it is
complete against `overlaps()`/`is_invariant()`, the tests, the before/after
ms, the gate lines. PR into `plan-24-26-27-integration`. Reply with ONLY
(under 12 lines): Status; base SHA; commits; PR URL; before/after ms on
ROUTING; gate lines; concerns; report path.
