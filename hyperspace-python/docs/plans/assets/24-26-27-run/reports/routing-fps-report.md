# ROUTING page frame-rate drop: root cause

Investigation only. No source file was changed and no PR was opened. The worktree branch
`routing-fps-investigation` is reset to `origin/plan-24-26-27-integration` at **a661fa0**,
and `git status` is clean. Main was measured from `git archive origin/main` (56c7d44),
extracted to a scratch folder outside the repo, so the branch was never checked out over.
Machine: this Mac, 2026-10-15. Neither `~/Hyperspace` nor `~/My Drive/Hyperspace` was touched.

## Verdict

- **The drop reproduces, and it is all CPU.** On ROUTING the control panel's `Panel.draw`
  takes **17.6 ms** a frame on the branch. On CAMERA and SYSTEM it takes **1.05 ms**. The
  frame goes from 8.3 ms (120 fps, vsync) to 20.9 ms (**48 fps**). The per-node GPU timers
  are the same on every page (scene about 0.5 ms, fx about 0.7 ms).
- **The cost was already on main, and the branch makes it worse.** On main, ROUTING's panel
  takes **12.0 ms** a frame (14.4 ms frame, 69 fps). The branch adds about 5.7 ms (+47%).
- **Root cause.** The ROUTING page rebuilds two derived lists from the binding table on every
  frame. Both scan the table pairwise, and every `Binding` property reparses the source
  string each time it is read.
  1. `ui_routing.unmapped()` (ui_routing.py:1071), through `preset_controls()` (:1057) and
     `Bindings.is_invariant()` (routing.py:1932). It compares 125 factory desk rows against
     67 invariant rows and then against the 30 desk rows: about 4,400 `Binding.overlaps()`
     calls (routing.py:705) a frame, each splitting and partitioning strings. It costs
     **9.5 ms/frame on the branch and 7.3 ms on main.** `desk()` calls it at :1124 on every
     frame, and its result changes only when the table changes.
  2. `ui_routing._sources()` (ui_routing.py:513) is called **once per route row** from
     `_row()` (:692), so 21 times a frame with an identical result each time. Every call
     walks all 209 bindings twice for each source scheme (`used =`, `named =` at :534–535).
     It costs **5.15 ms/frame on the branch and 1.77 ms on main.**
- **Introduced by.** The structure is old: `unmapped`/`preset_controls` came with plan 13 WP4
  (ef888f0), and the per-row `_sources` with plan 09 WP4 (dafd614) / WP5b (c5f4296). The
  branch's +5.7 ms comes from two places:
  - **Plan 27 B2 (8315371).** `Binding.scheme` now goes through `base_scheme()` (one extra
    `partition` on every read). `overlaps()` now also compares `.device` (two more parses).
    `_sources` loops over `source_schemes(router)` (registry schemes plus each route's scheme).
  - **Plan 24 C4 (a610ff0 / 604e860).** The `hand` lanes went from 22 to 40, a `hands` scheme
    was added, and the combo grew from 32 to 52 sources.
- **Why the owner saw 35 fps and not 48.** The owner's rig carries more per-frame work than
  this scratch run: an APC40 desk, `[dream]` enabled, more devices and a 1080p output. The
  same 17–18 ms of CPU on top of that heavier frame lands at about 28 ms (35 fps). The
  mechanism is the same.

## Method and commands

The probe is `/Users/dallman/.claude/jobs/b8e1c57e/tmp/routing-fps/tools/probe.py`. It runs
the real `hyperspace.app.main()` unchanged and wraps `ui.Panel.draw` to do four things:
- set `ui.page` to the chosen page on the first frame;
- time `Panel.draw` and the frame period, skipping the first 60 frames;
- read `Renderer.stats["gpu_ms"]` at frame 300;
- optionally run cProfile over `Panel.draw` (`PROBE_PROFILE`), time named `ui_routing`
  functions (`PROBE_SPLIT`), or apply a probe-side cache that estimates the fix (`PROBE_CACHE`).

The runner is `/Users/dallman/.claude/jobs/b8e1c57e/tmp/routing-fps/tools/run2.sh <tag> <home> <page>`.
It amounts to:

```
cd <tree>/hyperspace-python; unset VIRTUAL_ENV
HYPERSPACE_FRAMES=600 HYPERSPACE_HOME=<scratch home> PROBE_PAGE=<page> \
  uv run python .../tools/probe.py -ApplePersistenceIgnoreState YES
```

The scratch homes (no `[library]` section in either) are:
- **branch:** `/Users/dallman/.claude/jobs/b8e1c57e/tmp/routing-fps/branch/home`, built by
  `tools/setup.py`. Its `config.toml` sets `[dream] enabled=false`, a `[[devices]]` hands
  entry playing `synthetic.json` (from `tools/hands_tape.py synth`) with `out=""`, and the
  gamepad with `enabled=false`.
- **main:** `.../routing-fps/main/home`. It has the same tape and project, written as main's
  table format: `[hands] enabled=true tape="synthetic.json" out=""`, `[gamepad] enabled=false`.
- **both:** the show `fps` is the factory `party` show with `startup = "TRIP"` (party-trip),
  and `last_show` is `fps`.

No MIDI device was attached to either run. The desk rows and the factory profile are in the
table either way, so `unmapped()` does its full work.

## Numbers (600 frames, mean over frames 61–600)

| build | page | panel ms/frame | frame ms | fps |
|---|---|---|---|---|
| branch a661fa0 | ROUTING | **17.71** (p95 19.1) | 20.69 | **48.3** |
| branch a661fa0 | CAMERA | 1.07 | 8.35 | 119.8 (vsync) |
| branch a661fa0 | SYSTEM | 1.05 | 8.34 | 119.9 (vsync) |
| main 56c7d44 | ROUTING | **12.04** (p95 12.8) | 14.66 | **68.2** |
| main 56c7d44 | CAMERA | 0.97 | 8.33 | 120.0 (vsync) |
| branch + probe-side cache (estimate of the fix) | ROUTING | **3.19** | 8.33 | 120.0 (vsync) |

GPU on ROUTING vs CAMERA (branch, ms): scene 0.45 vs 0.52, fx 0.39 vs 0.68. That is no
difference, so the cost is CPU.

### Split, wall ms per frame in `ui_routing` functions (PROBE_SPLIT)

`_row` includes `_sources`, and `desk` includes `unmapped`, which includes `preset_controls`.

| function | branch | main |
|---|---|---|
| `desk` | 9.70 | 7.51 |
| `unmapped` | 9.47 | 7.29 |
| `preset_controls` (inside `unmapped`) | 7.16 | 5.68 |
| `_row` (×21) | 5.77 | 2.33 |
| `_sources` (×21, inside `_row`) | **5.15** | 1.77 |
| `head` | 0.91 | 0.93 |
| `macros` + `session` + `sinks` | 0.36 | 0.33 |

### Table sizes at frame 100

| | branch | main |
|---|---|---|
| bindings | 209 | 208 |
| routes | 21 | 21 |
| desk rows | 30 | 34 |
| invariant rows | 67 | 70 |
| `factory_desk` rows | 125 | 124 |
| sources in combo | **52** | 32 |
| labels | lane 6, hand **40**, hands 2, lfo 4 | lane 6, hand 22, lfo 4 |

## Profile (branch, cProfile over `Panel.draw`, 240 frames, sorted by cumulative)

cProfile inflates everything by about 3.5×, but the proportions hold.

```
 ncalls   cumtime  function
    240   14.403   ui.py:1942(_page_routing)
    240   14.272   ui_routing.py:1459(page)
    240    8.600   ui_routing.py:1099(desk)
    240    8.344   ui_routing.py:1071(unmapped)
1048080    8.040   routing.py:705(overlaps)
15517396   7.642   routing.py:595(scheme)
    240    6.269   ui_routing.py:1057(preset_controls)
  11760    6.218   routing.py:1932(is_invariant)
 799680    6.039   routing.py:1942(<genexpr>)        # any(x is not b and b.overlaps(x) for x in inv)
   5040    5.039   ui_routing.py:675(_row)
   5040    4.704   ui_routing.py:513(_sources)
5763203    3.552   routing.py:627(is_midi)
15530401   3.036   routing.py:305(base_scheme)
1980480    2.876   routing.py:636(channel)
2238754    2.868   routing.py:631(kind)
3880800    2.274   ui_routing.py:534(<genexpr>)      # used = any(b.scheme == scheme for b in bindings)
21312984   1.905   {str.split}
16589281   1.115   {str.partition}
```

`Binding.scheme` is read about 65,000 times a frame, and each read does a `split` plus a
`partition`. Main's profile has the same shape, without `base_scheme` and the `.device`
compare, and with about a third of `_sources`.

Not found hot: `devices.kinds()`, `learn.cannot_show`, click-to-map ranking,
`registry.schemes()`/`wants()` (`source_schemes` is cheap; the cost is the binding scans
inside `_sources`), `sinks()` at 0.01 ms, and per-lane label formatting (small next to the
scans).

## Root cause statement

`ui_routing.unmapped()` (ui_routing.py:1071, called from `desk()` at :1124 on every frame)
recomputes the dark preset-layer controls. It does this through `preset_controls()` → 
`Bindings.is_invariant()` (routing.py:1932–1942) → `Binding.overlaps()` (routing.py:705):
about 4,400 pairwise compares, each reparsing source strings, for **9.5 ms/frame** (7.3 ms on
main). `ui_routing._sources()` (ui_routing.py:513) is rebuilt **once per route row** (21× a
frame, from `_row` at :692), scanning all bindings for each scheme, for **5.15 ms/frame**
(1.77 ms on main). Neither result changes from one frame to the next unless the table changes.

## Proposed smallest fix (not implemented)

1. In `page()` / `_row()`, compute `sources = _sources(panel, router)` once per page draw and
   pass it to `_row`. This removes about 4.9 ms.
2. Memoize `unmapped(table)` (and `preset_controls`) on a cheap table signature, for example
   `(table.profile, tuple((b.source, b.layer, b.enabled) for b in table.bindings))` (about
   200 tuples, well under 0.1 ms). Alternatively key it on `desk_serial`/`redraw_serial` plus
   a table edit counter. This removes about 9.4 ms.

Measured estimate with both applied probe-side (a per-frame `_sources` and a once-only
`unmapped`): ROUTING panel **17.7 → 3.2 ms**, frame back to vsync (120 fps).

Optional follow-up, not needed for the fix: make `Binding.scheme`/`device`/`channel`/`number`
cheap by parsing once when `source` is set (a property setter that caches the parts). That
cuts every remaining scan by about 3×.

## Test that would pin it

Add this to `tests/test_ui_routing.py`, using the headless `frame(panel, "routing")` helper
pattern from `tests/test_ui_shell.py:113`. With a rig holding 20 or more routes:
- monkeypatch counters onto `ui_routing._sources` and `ui_routing.preset_controls`;
- draw the ROUTING page twice;
- assert `_sources` ran **once per frame**, whatever the row count;
- assert `preset_controls` ran **once across both frames** while the table was unchanged;
- then edit one desk row (or load a preset), draw again, and assert it re-ran (no stale cache).

## Concerns

- These timings come from a scratch home with no APC40, `dream` off and a synthetic hands
  tape. The owner's absolute 35 fps includes a heavier frame, but the 17–18 ms on ROUTING is
  independent of it.
- The cache key must cover in-place row edits (a row's target, layer or enabled changed from
  the page) and preset loads, or the dark-control list goes stale. The test above checks it.
- `unmapped()` also feeds the filter's hay list (ui_routing.py:339, only while a find string
  is typed). The same memo covers it.
