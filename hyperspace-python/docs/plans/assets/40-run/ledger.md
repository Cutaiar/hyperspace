# Run ledger — plan 40, patches: `docs/plans/40-session-prompt.md`

Controller session: https://claude.ai/code/session_012HeFHywoiCGN2SbvC1U35W
(Fable 5.1); every task a sub-agent on Opus (`DECISIONS.md` "Process":
agents in a run work on Opus or Sonnet, never Fable). Workspace while the
run is live: `/Users/dallman/.claude/jobs/45478892/tmp/run/` (briefs/,
reports/, decisions/, logs/); copied into `docs/plans/assets/40-run/` on
`plan-40-build` as the run goes.

## Base
- 2026-10-27: `origin/plan-37-38-39-integration` @ **2b185ea** verified
  (plan 38 and plan 39 T0–T4 on it; plan 37 and plan 39 T5 not yet; no
  final PR to `main` open). `main` @ f984d3b (PR #266) was **not** under
  2b185ea, contrary to the build plan's note.
- `plan-40-build` cut from 2b185ea; first commit **f10f281** = merge of
  `origin/plan-40-patches` (the three plan 40 docs, PR #264) — which also
  carries `main` @ f984d3b, so PR #266's side pane is on the build branch
  as the build plan assumed. One conflict, `docs/plans/README.md`: both
  lines kept. Pushed.
- Gates on f10f281 (this Mac, Apple M3 Max, uv's Python 3.14): see "Log".
- Numbers: register rows 471–495; hand checks 394–401, group AK (plan 38
  ended at row 470; plan 39's AJ ends at check 393).

## Pre-flight rulings
See `decisions.md`.

## Tasks

| task | branch | base | status | tests | review | rows / checks |
|---|---|---|---|---|---|---|
| T0 the word (D1) | `plan-40-t0` | f10f281 | **merged** 51106e1 (PR #269) | fast 4122/2 skipped, goldens 136 | controller | — |
| T1 patches.py + DocKind | `plan-40-t1` | 51106e1 | **merged** 44eb753 (PR #274) | fast 4167/2 skipped, goldens 136 | reviewed, 2 Important fixed | 471x–479x drafts, AK.1–4 |
| T4 devices.wants + arrival | `plan-40-t4` | 51106e1 | **merged** b0b23f3 (PR #272) | fast 4139/2 skipped, goldens 136 | reviewed, 1 Important fixed | 47a–47f drafts |
| T5 fx modules retired | `plan-40-t5` | 51106e1 | **merged** 3094691 (PR #271) | fast 4097/2 skipped, goldens 136 | controller | rulings 9–11 |
| T2 the group node | `plan-40-t2` | d08a363 | **merged** f8d2e73 (PR #276) | fast 4294/2 skipped, goldens 144 | approved; minors to the fix pass | 50a–50h drafts, AK.n1–n4 |
| T3 save / browse / spawn | `plan-40-t3` | f8d2e73 | built, PR #277; merged locally 19596e8 | fast 4306/2 skipped, goldens 144, --all 4537 | in the plan review | 50i–50s drafts, AK.5–7 |
| plan review | `plan-40-build` @ 19596e8 vs `main` | — | done: D1–D10 ✅, 1 Important, minors | — | `reports/plan-review.md` | rulings 17–19 |
| review fixes | `plan-40-fixes` | 19596e8 | **merged** e0675a6 (PR #278) | fast 4320/2 skipped, goldens 144 | — | 50r–50w drafts, AK.f1–f4; rulings 20–22 |
| T6 docs | `plan-40-t6` | e0675a6 | **merged** b8e8de1 (PR #279) | fast 4320/2 skipped | — | 501–536 / 394–401 |

## Merges into `plan-40-build`
(counts after each.)

## Log
- **Base gates on f10f281** (2026-10-27): fast tier **4122 passed, 2
  skipped** (4121 + `test_media_render.py::test_render_thread_never_waits`,
  which failed under `-n auto` on a busy machine and passes serially:
  load-flaky, pre-existing). `uv run ruff check .` has **25 pre-existing
  errors** on the integration base (media/*.py S110/F401/I001,
  tools/ingest.py, the plan 39 bench scripts, four tests) — none in a
  file plan 40 touches; the gate for this run is ruff clean on the files a
  task touches. Goldens (`--all -m golden`): **136 passed**, none moved.
- **T0** dispatched (Opus, own worktree, branch `plan-40-t0` off f10f281).
- **T0** DONE → PR #269 (`plan-40-t0`, 3 commits: 3884d64, 2e54b4d,
  fa4da2d). 20 files; the proof grep empty; Dylan's files untouched; went
  wider than the listed symbols (`Patch`/`PatchNode`/`PatchEdge` →
  `ModGraph`/`ModNode`/`ModEdge`, `patch_cut` and privates) — accepted
  under D1 ("patch means the owner's thing and nothing else"). Sub-agent's
  gates: fast 4121 + 1 load-flaky (= base), ruff the base's 25, goldens 136,
  `--all` 4342 passed + 2 load-flaky (pass serially). Left for T6:
  `11-hand-checks.md` (3 refs to `test_patch.py`), `30-shader-nodes.md` (2
  refs to `patch.py`). Merged `--no-ff` into `plan-40-build` as **51106e1**;
  controller's fast tier: see below.
  Controller's fast tier on 51106e1: **4122 passed, 2 skipped** (29.7 s).
  Pushed. PR #269 closes by the merge.
- **T1, T4, T5** dispatched in parallel (Opus, own worktrees, branches
  `plan-40-t1` / `plan-40-t4` / `plan-40-t5` off 51106e1).
- **T5** DONE_WITH_CONCERNS → PR #271 (`plan-40-t5`, 305499a, 6591744).
  21 files, −712/+159: the six fx files, `Presets._fx_module` /
  `_watch_fx_modules`, `graphmigrate.module_runs` and its helpers gone;
  `library.RETIRED_MODULES = ("fx",)`; the FX page's module strip hidden
  through `ui_presets.strip` (`ui_fx.py` untouched); the party generator's
  fx values inline (factory presets byte-identical); `tools/fx_shots.py`
  and an orphan palette fixture outside the list, both justified. Fast
  4097/2 skipped (−25 removed tests, +2), goldens 136, `--all` 4318 + 1
  load-flaky (`test_dream::test_end_to_end_offscreen`, passes alone).
  Rulings 9–11 in `decisions.md`. Merged `--no-ff` as **3094691**;
  controller's fast tier: see below.
  Controller's fast tier on 3094691: **4097 passed, 2 skipped** (45 s).
  Pushed.
- **T4** DONE_WITH_CONCERNS → PR #272 (`plan-40-t4`, 20aec1a, 6aea053).
  8 files, +858: `devices.wants` / `Want` / `wants_for` / `want_words`,
  `SCHEME_ROLE` moved to `devices`, `routing.row_words`, the registry's
  status-change event + `said` hook (`app.py` 2 lines), the chip on GRAPH
  and the PRESET strip, the SYSTEM lines; `ui_graph.py` + `graphview.py`
  34 changed lines; Dylan's files untouched. Fast 4137/2 skipped (+15),
  goldens 136, `--all` 4358 + 1 timing-flaky (`test_ndi_out_never_blocks`,
  passes serially). Concerns: with the APC40 unplugged every desk preset
  shows "1 device missing" on the laptop (correct, constant); the PRESET
  strip chip may crowd a narrow panel. **Reviewer dispatched**
  (`briefs/review-t4.md`). Integration branch now 07885a2 with **PR #270
  open** to `main` (not merged): T2 waits.
- **T1** DONE_WITH_CONCERNS → PR #274 (`plan-40-t1`, 6677797). 7 files,
  +1923: `patches.py` (1155 lines: `Patch`, `Landing`, `Host`, `Conflict`,
  `read`, `check`, `lift` → `(doc, refused)`, `spawn`), the `PATCHES`
  `DocKind` + `read_patch` / `save_patch`, `hide` / `rename` extended to
  the kind (`hidden.json` gains a `"patches"` key, written only when one
  is hidden), `hotreload.MODULES` + `patches`, fixture
  `tests/fixtures/patches/acid-wash.json` (force-added). Departures from
  the spec, each reasoned: `mod:1` not `mod:0` in the fixture (a `mod:<n>`
  lane is `mod.<n>`); patch envelopes start at `env.6`; the "main run"
  is `run_back` into `output.all.image` (`run_of` is empty in a /7 preset;
  16 factory presets have no run and are named, 9 round-trip). Fast
  4163/2 skipped (+41), goldens 136, `--all` 4384 + 1 timing-flaky
  (`test_ndi_out_never_blocks`, passes alone). Concern: spawning a cut
  back into its own preset lists every shared hand axis as a conflict
  (correct by the one-axis-one-param rule; a noisy sheet). **Reviewer
  dispatched** (`briefs/review-t1.md`).
- **T4 review** (`reports/t4-review.md`): compliant; Important: `wants`
  calls `registry.lines()` per call, which rebuilds every MidiDevice's Port
  layout (0.23 of 0.29 ms); minors (a register row for the extra
  role-resolution steps, the retry path's per-device `_changed`, two
  `graphview` comment edits, one empty assert). Sent back to the T4
  implementer for fixes.
- **T4 fixes** DONE (5189232): `_rig` reads each device's `status`
  directly (no Port layouts; 0.29 → 0.060 ms per call), `ui_graph.panel_wants`
  once a frame shared by the head, the strip and SYSTEM; row 47f for the
  role-resolution order; the retry path's per-device `_changed` noted; the
  `graphview` comment block restored; the empty assert dropped; a literal
  count in the coming-back test. Fast 4139/2 skipped, goldens 136. Merged
  `--no-ff` as **b0b23f3** (on top of T5's 3094691, clean); controller's
  fast tier: see below.
  Controller's fast tier on b0b23f3: **4114 passed, 2 skipped** (4097 +
  T4's 17). Pushed.
- **T1 review** (`reports/t1-review.md`): the classifier, renames, D5,
  the kind and the round trip approved; the four spec departures judged
  right; **two Important**: (1) `check` let a crossing wire through when a
  port "covered" it and `spawn` landed it — an automatic attachment (D2);
  (2) with a full bank a non-spawned voice's lane leaked into modifier
  inputs and depth subs (the test could not fail). Minors: `Host.of`
  without `banks`, `room` vs `modbank.MAX_ID`, 474x must say a one-owner
  source read through a modifier is no conflict (the spec's D3 example),
  the dormant-row revival sentence, a D5 filter in `spawn`, unused
  `Host.params`. Sent back to the T1 implementer.
- **T1 fixes** DONE (4ac3a1d): `check` refuses any wire with an end
  outside the patch ("wire scene → acid.image crosses the edge: a port
  says it") and `spawn` lands only the patch's own wires whatever the file
  says (D2); a voice that does not spawn (bank full or past
  `modbank.MAX_ID`) reads nothing — its modifier input blanked and named
  in the note, its subscribers dropped; `Host.of` without banks starts
  past every voice id the table names; `spawn` keeps only members' values
  (D5 without `check`); `Host.params` gone; 474x / AK.1 say a hand axis
  read through a modifier is no conflict (the spec's D3 example, for the
  owner) and that the lowest-free instance can wake dormant host rows.
  `patches.py` now also imports `modbank`, `lfo`, `envelope` constants
  (leaves; the AST test holds). Fast 4167/2 skipped (+45), goldens 136;
  `--all` not re-run by the implementer — the controller runs it on the
  merge. Merged `--no-ff` as **44eb753** (clean beside T5's `library.py`).
  Controller's gates on 44eb753: fast tier **4159 passed, 2 skipped**;
  `--all` **4379 passed, 2 skipped, 2 failed** — `test_migrate_library::
  test_the_real_picture_check_passes_an_old_preset` and `test_media_core::
  test_bad_file_is_an_error`, both pass serially (load-flaky, pre-existing);
  goldens **136 passed**, none moved. Pushed. T0, T1, T4, T5 are on
  `plan-40-build`; T2 waits for PR #270 → `main`.
- **Dry run of the integration head** (07885a2) into `plan-40-build`: one
  conflicted file, `ui_graph.py`, three both-sides hunks (imports, `st`
  defaults, the chip order) — keep both. Schema: nothing writes `/8`, so
  `groups` is `/8` (ruling 13). **Register rows renumbered to 501–525**
  (PR #270's docs took through 499; ruling 12); hand checks 394–401 stand.
  Run records committed to `docs/plans/assets/40-run/` (75a9af5, pushed).
  **Waiting on PR #270 → `main`** before T2; or the owner's word to cut
  T2 against the integration head.
- **PR #270 merged** to `main` 2026-10-28 05:19 (plans 37/38/39) and
  **#275** 05:20 (the pattern node's side pane). `main` @ 026989e merged
  into `plan-40-build` as **d08a363**: one conflict, `ui_graph.py`'s head
  chips (T4's wants chip kept, plan 37's tint chip last). Fast tier
  **4269 passed, 2 skipped**; goldens **136**; ruff clean on `ui_graph.py`.
  Pushed. Register's last row on `main` is now **500** → plan 40 takes
  **501–525** (ruling 12 amended). Schema: nothing writes `/8` → `groups`
  is `/8`.
- **T2** dispatched (Opus, own worktree, branch `plan-40-t2` off d08a363).
- **T2** DONE_WITH_CONCERNS → PR #276 (`plan-40-t2`, 7f8ff80, 865d0b3).
  14 files, +2383: `preset.GROUPS_KEY` + `/8`, `graphmigrate`'s step,
  `Marks` carry `groups`, the one boundary classifier in `patches.py`
  shared with `lift`, `graphview.VGroup` + `Edit.group` / `ungroup` /
  rename / move / leave, `ui_graph._group_node` / `_region` / the menus /
  the side pane with the `_group_chips` hook, `tests/test_graph_groups.py`
  (560 lines), a grouped `party-noita` fixture, 8 grouped-twin golden
  proofs. `graph.py`, `render.py`, `tests/golden/`, `frame-signatures.json`
  untouched. Fast 4294/2 skipped (+25), goldens 144 (136 + 8 proofs, none
  re-recorded), `--all` 4525 (one GL flake in `test_migrate_library` on
  the first run, passes alone). Concerns: no person has seen the drawing;
  **plan 38's `ui_graph._monitor` `add_rect(..., 0.0, 0, 2.0)` raises a
  TypeError the first time the hold inset draws** (on `main`; for the
  review-fix pass); an older build refuses an `/8` file rather than
  dropping the key (the ladder's rule; T6 says so). Merged `--no-ff` as
  **f8d2e73** locally (not pushed until the reviewer and the controller's
  tests agree). **Reviewer dispatched** (`briefs/review-t2.md`).
  Controller's gates on f8d2e73: fast tier **4294 passed, 2 skipped** (4293
  + `test_media_folder::test_a_file_still_downloading_is_not_opened_until_it_is_ready`,
  which failed under `-n auto` and passes serially; T2 touches no media
  file); goldens **144 passed**. Push waits for the T2 review.
- **T2 review** (`reports/t2-review.md`): **Approved**, no Critical or
  Important; all ten doubts settle for the PR. Minors for the review-fix
  pass: multi-member drag-out = several undo steps; a drop on a folded
  group's stub opens an empty picker; `preset.group_number` /
  `graphview._group_n` duplicate; two thin tests; proofs cover the 9
  presets with a main run (the 16 `NO_RUN` named); `_held_canvas`'s
  `range(1, 100)` fallback; ids reusable after ungroup (50f); the open
  region's title selectable. **Plan 38's `_monitor` bug confirmed**:
  imgui_bundle's `add_rect(p_min, p_max, col, rounding, thickness, flags)`
  — the call passes `0.0, 0, 2.0` and raises `TypeError` in a frame; fix
  `(…, 0.0, 2.0)` at `ui_graph.py` ~1157; no headless test reaches it
  (`tex.glo == 0` returns early) — a stub-texture test for the fix pass.
  **Tension flagged**: ruling 50g (ungrouped saves `/7`) vs the owner's row
  394 (every save the newest schema) — put to the owner (ruling 15).
  f8d2e73 **pushed**.
- **T3** dispatched (Opus, own worktree, branch `plan-40-t3` off f8d2e73).
- **T3** DONE_WITH_CONCERNS → PR #277 (`plan-40-t3`, 9915a63, 7cba583).
  9 files, +1608: `Edit.spawn` / `splice` / `wire_as_saved` / `save_patch`
  on the edit layer, `ui_graph` browser chip + **Spawn ▸** + the cable drop
  target + the side pane chips, `ui_routing.modal`'s conflict sheet,
  `ui_presets`' patches fold, `Learn.hold`, `Presets.parts()`. Dylan's
  files, the renderer, goldens, library untouched. Fast 4306/2 skipped
  (+12), goldens 144, `--all` 4537/2 skipped. Rulings 50i–50s; concerns:
  nothing seen by a person; **wire as saved refuses a fed port** (50j, for
  the owner); the spec's examples do not match `party-trip` (no acid /
  wobble / delay / warp), so the tests use the second spawn for `.2` and
  splice on `scene → plasma.image`. Merged `--no-ff` as **19596e8**
  locally; controller's gates running. **Plan-level review dispatched**
  (`briefs/review-plan.md`, T3's task review folded in — ruling 16).
  Controller's gates on 19596e8: fast tier **4306 passed, 2 skipped**;
  goldens **144 passed**; `--all` **4536 passed, 2 skipped, 1 failed** —
  `test_migrate_library::test_the_real_picture_check_passes_an_old_preset`
  ("cannot create vertex array": GL contention under `-n auto`), passes
  serially. Pushed.
- **Plan review** (`reports/plan-review.md`, over 19596e8 vs `main`):
  **D1–D10 all compliant**; the thirteen proofs settle; T3 (a)–(i) all
  ✅. No Critical; **one Important**: a spawn with no conflicts never says
  which devices its rows wait for (`Landing.wants` read by nothing; the
  words exist in `ui_routing.sheet_wants`). Minors: an empty undo step on
  a landing refused after the dry run; a source conflict removes the
  host's rows before `replace_owner`; Save as patch… replaces a same-slug
  patch silently; the patch list rebuilt every frame of a menu / drag;
  `pre._banks()` private; three test gaps; for the owner: 50j (a take-over
  chip for a fed port) and 50i (open pins last the session); T6: do not
  say `patches.py` "imports nothing from the app" (through `routing` it
  reaches `apc40`, `params`; through `graph`, `moderngl`). **Fix pass
  dispatched** (`briefs/fixes.md`: the Important, the minors, T2's eight,
  plan 38's `_monitor` bug; branch `plan-40-fixes` off 19596e8).
- **Review fixes** DONE_WITH_CONCERNS → PR #278 (`plan-40-fixes`, 15
  commits 86795d5…209247d; the plan 38 `add_rect` fix its own, 86795d5).
  10 files, +511/−99: a spawn says what waits; the empty undo step on a
  refused landing; `replace_owner` validated before the host's rows move
  (a read-only `Bindings.refusal` factored out of `_check` in
  `routing.py`, behaviour unchanged); Save as patch… refuses another
  patch's slug (a factory one too); the patch list listed once per menu /
  drag; `Presets.banks()`; the three test gaps; T2's eight minors (fix 12
  groups every holdable node of the 16 `NO_RUN` presets — none has an
  effect — proving `party-tracer` and `party-wake`, the other 14 hold only
  frame nodes; fix 13's fallback is the registry's voices via
  `graphview.bank_ids`; fix 14 leaves only open-region titles out of
  Group's selection); plan 38's inset with a stub-texture test in
  `test_hold.py`; a pollution bug in the `noita()` test helper. Fast
  4320/2 skipped (+14), goldens 144, `--all` 4550 + the GL flake. Rulings
  50r–50w, AK.f1–f4. Merged `--no-ff` as **e0675a6**; controller's gates
  running (the counts for the spec header).
  Controller's gates on e0675a6: fast tier **4320 passed, 2 skipped**;
  goldens **144 passed** (136 the base's + 8 grouped-twin proofs, none
  re-recorded); `--all` **4551 passed, 2 skipped**, no failure; ruff the
  base's 25 pre-existing, none in a plan 40 file. Pushed.
- **T6** dispatched (Opus, own worktree, branch `plan-40-t6` off e0675a6).
- **T6** DONE_WITH_CONCERNS → PR #279 (`plan-40-t6`, 6dd8200, b9ee2c5).
  23 files, +1999, docs only: the spec as built (header, "What changed in
  the build", the four corrections marked), register rows **501–536** (36
  rows: D1–D10 as 501–510, then the rulings; 15 and 17 as rows 521 and 524
  "pending the owner"; the process rulings in the spec's "Process"
  paragraph, not rows), hand checks 394–401 as group AK, ARCHITECTURE
  §3.11 "Patches and groups" (no desk-templates paragraph existed; a
  pointer from §3.6) + §4's table + §3.7's rows, DECISIONS, ENGINEERING,
  SETUP, CHECKPOINT, TESTING-GUIDE, plans/README, T0's leftovers. Fast
  4320/2 skipped. Merged `--no-ff` as **b8e8de1**; controller's fast tier
  4320/2 skipped. **Final**: `plan-40-build` → `main` PR opened (see the
  ledger's head). Rows 501–536 supersede "501–525" above.

## Final state (2026-10-28)
`plan-40-build` @ b8e8de1 + this records commit. Gates on e0675a6 (the
last code commit): fast tier 4320 passed, 2 skipped; `--all` 4551 passed,
2 skipped; goldens 144, none re-recorded; ruff clean on every plan 40 file.
Hand checks 394–401 (AK) pending at the machine; rows 501–536 for the
owner, 521 and 524 pending his answer. Both Macs update together before a
preset with `groups` is shared.
