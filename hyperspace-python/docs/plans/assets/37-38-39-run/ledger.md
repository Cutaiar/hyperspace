# Run ledger — plans 37, 38 and 39: `docs/plans/37-38-39-orchestrator-prompt.md`

Orchestrator session: https://claude.ai/code/session_012HeFJ3coaFYJ9durdEgBjC
(Fable 5.1); every task a sub-agent on Opus 5.5 (the owner's word for
this run; `DECISIONS.md` "Process": agents in a run work on Opus or
Sonnet). Workspace while the run is live:
`/Users/dallman/.claude/jobs/9679624d/tmp/run/` (briefs/, reports/,
decisions/, logs/); copied into `docs/plans/assets/37-38-39-run/` on the
integration branch as the run goes.

## Base
- 2026-10-27: `main` @ f2351a0 (#247 after plan 36's #245/#246), verified.
  PR #248 (`worktree-vision-spike`, docs only: the three plans, the spike,
  the run prompt) was **open, not merged**, so the integration branch
  `plan-37-38-39-integration` was cut from `main` and `worktree-vision-spike`
  merged into it (`--no-ff`): **cb78963**, pushed. The spike branch already
  contained `main`, so the merge is the eight doc files and nothing else.
- Gates on cb78963 (this Mac, Apple M3 Max, uv's Python 3.14): fast tier
  **3958 passed, 2 skipped** (57 s); full suite `--all` **4170 passed, 2
  skipped** — two media tests (`test_media_channels.py::test_rapid_switching_with_slow_closes_stays_fast_and_balances`,
  `test_media_core.py::test_bad_file_is_an_error`) failed under `-n auto`
  and pass serially: load-flaky, pre-existing, not the run's; goldens
  **757** (24 factory presets, 23 fixtures in the manifest).
- Plan branches cut from cb78963 and pushed: `plan-37-pictures`,
  `plan-39-vision`. `plan-38-hold` is made by B1 (the cherry-pick of
  `output-hold` @ 3959f57 onto cb78963).
- Numbers (the prompt's): 37 → rows 417–429, checks 370–376 (AH); 38 →
  430–439, 377–383 (AI); 39 → 440–459, 384–393 (AJ). Code tasks draft
  `4xx` / `AH.n`–`AJ.n`; each plan's docs task numbers them.

## Pre-flight rulings
See `decisions.md`.

## Tasks

| task | branch | base | status | tests | review | rows / checks |
|---|---|---|---|---|---|---|
| 39-T0 edges.glsl | `plan-39-t0-edges` | cb78963 | dispatched | | | |
| 39-T1 alpha honest | `plan-39-t1-alpha` | cb78963 | dispatched | | | |
| 39-T2 mask wire + matte | `plan-39-t2-matte` | cb78963 | dispatched | | | |
| 39-T3 cut | | after T2 | waiting | | | |
| 39-T4 segment + worker | | after T3 | waiting | | | |
| 39-T5 GRAPH + pages | | after T4 | waiting | | | |
| 39-T6 docs | | last | waiting | | | 440–459 / 384–393 |
| 38-B1 rebase | `plan-38-hold` | cb78963 | dispatched | | | |
| 38-B2 hand-check readiness | | after B1 | waiting | | | |
| 38-B3 review | | after B2 | waiting | | | |
| 38-B4 docs | | after B3 | waiting | | | 430–439 / 377–383 |
| 37-C1 thumbnails | `plan-37-c1-thumbnails` | cb78963 | dispatched | | | |
| 37-C2 hover + head switch | | after C1 | waiting | | | |
| 37-C3 backward wire | `plan-37-c3-backward-wire` | cb78963 | dispatched | | | |
| 37-C4 faces (dry run) | `plan-37-c4-faces-sheets` | cb78963 | dispatched | | | waits for the owner's list |
| 37-C5 review + docs | | after C1–C3 | waiting | | | 417–429 / 370–376 |

## Merges into the integration branch
(38 → 39 → 37; counts after each.)

## Log

- **39-T1** DONE_WITH_CONCERNS → PR #252 (`plan-39-t1-alpha`, 3 commits: test
  392056f, blend 57f48b4, re-record 10968e4). The honest blend moved 8
  fixture goldens (`backdrop-still`, `media-chain-backdrop`, 4 states
  each): ruled re-record (decisions 9). Fast 3959/2 skipped; goldens 128
  passed; `--all` under load: serial re-run left `test_ndi_out_never_blocks`
  (a 0.05 s limit) and `test_dream::test_end_to_end_offscreen`, both pass
  alone. Reviewer dispatched.
- **37-C4** DONE_WITH_CONCERNS → PR #250, **merged** into `plan-37-pictures`
  @ 45d7a4d. `tools/faces_sheets.py` (17 tiles on `party-faces`' tesseract
  + a Heart sheet), `docs/plans/assets/37-faces/` (sheet.png, one PNG per
  mode, `migration-map.md` generated and checked by `tests/test_faces_map.py`).
  Nothing removed, no preset edited. Usage: HEX 11 on screen, PLASMA 6,
  RINGS 5, EMBER 3; PLAID/BLOOM/METER/PULSE/MARBLE/TRUCHET/KALEIDO on no
  preset. Two questions for the owner recorded (decisions 10).
- **37-C3** DONE_WITH_CONCERNS → PR #253 (`plan-37-c3-backward-wire`,
  7847a60). Rule as built: an effect-area node is laid in the leftmost
  consumer area not left of what feeds it (= D5 with one consumer area;
  `acid.2` in the `acid-scene` fixture feeds the look-back and a
  composite). `acid-scene` is a fixture, not a factory preset; no saved
  positions. Fast 4005/2 skipped (a sweep over every preset + fixture);
  goldens unmoved. Reviewer dispatched.
- **38-B1** DONE_WITH_CONCERNS → draft PR #251 (`plan-38-hold` →
  integration; e4d3af4 the cherry-pick with the owner's words, 3e89e0a
  the rig's bus cables held + the preview renderer given the show's
  cables (it drew every bus cable standing — a filled-in wire, against
  plan 36), 397b7ba tooltips/imports). `test_hold.py` 19; fast 3977/2
  skipped; goldens unmoved; headless smoke hold/edit/take and
  hold/edit/drop/undo as the spec says. `test_dream::test_end_to_end_offscreen`
  fails on this Mac even on the base while the run loads it (torch on
  MPS): re-check at the plan merge. Clouds and effect files stay shared
  between program and preview (B1's row, for B3). B2 dispatched off 397b7ba.
- Sub-agents' commits carry "Co-Authored-By: Claude Opus 5.5" (their own
  harness's line) rather than the brief's Fable line; the controller's
  merge commits carry the session's. Not rewritten.
- **39-T0** DONE_WITH_CONCERNS → PR #254 (`plan-39-t0-edges`, 4c68ab2 +
  review 57d2916). `shaders/fx/edges.glsl` (`@order 75`), fixture
  `edges-scene` (+8 goldens, 3 PNGs; carries hands-fx's hands wires too),
  `tests/test_fx_edges.py`; bookkeeping in `test_golden_frames`
  (`GOLDENS_SINCE`), `test_plan12` (allow-list), `test_graph_free` (`/7`
  fixture tolerated), `tools/golden_frames.py` (`WIRED_FIXTURES`). Review:
  **Approved, stands alone** (`reviews/39-T0-review.md`); source mode's
  alpha a taste call for AJ.7.
- **Reviews** of T1 (`reviews/39-T1-review.md`, Approved) and C3
  (`reviews/37-C3-review.md`, Approved; tie-break accepted, decisions 11).
- **Merged into `plan-39-vision`**: #254 (095ce8b) then #252 (4ea92bb), no
  conflicts. Gates on 4ea92bb: fast **3978 passed, 2 skipped**; goldens
  **130 passed** (765 pictures: 757 − 0 + 8; eight re-recorded under
  decision 9). Pushed.
- **Merged into `plan-37-pictures`**: #250 (45d7a4d, via gh) then #253
  (455c972, local, after a reset: the local branch had been stale at
  cb78963 — the first attempt was redone on origin's head). Focused tests
  `test_graph_areas` + `test_graphview` + `test_faces_map`: 100 passed.
  Pushed. The fast tier on this head runs at the C1 merge.
- **37-C1** DONE_WITH_CONCERNS → PR #255 (`plan-37-c1-thumbnails`, 4d684e7
  `PreviewTextures` (in `outputs.py`, a 16-tap downsample with its own
  sampler, `THUMB_PX` 192, dropped after 1 s unwanted, dim 0.45 then
  black after 1 s), e47c50d the GRAPH draw (`graphview.THUMBS` +
  `thumb_of`; a fixed 16:9 box at the node's width, the picture
  letterboxed) + SYSTEM line). Review `reviews/37-C1-review.md`: **Needs
  fixes** — the `pulled` gate missed non-MAKES kinds (a composite behind an
  unpicked switch was painted and its channel uploaded). Fixed in f0cfaf7
  (gate every kind + test; `kept` counts textures; a flush inside
  `_thumbnails`, `app.py` untouched; stateful kinds in the byte-identity
  test; `· K repainted` on SYSTEM; output 1 never dims recorded as a rough
  edge; `_body_of`). Fast 3973/2 skipped. **Merged** into
  `plan-37-pictures` @ 761aef3 (clean). An attempted merge in the wrong
  worktree (plan-38-hold) was aborted; it showed the expected integration
  conflict: plan 38's `ui_graph.py` head vs C1's `_canvas`/`_node` —
  reconciled when 37 merges last.
- **38-B2** DONE_WITH_CONCERNS → PR #257 (`plan-38-b2-checks`, a4ea685,
  `tests/test_hold.py` 19 → 22: the program draws the held wiring byte
  for byte while a GRAPH edit lands (proven by breaking the swap); drop is
  one undo step (values, graph, routes, desk, macros, name, dirty dot;
  rig untouched); learned buttons lit while held). AI.1–AI.7 drafted; AI.3
  (trails through Take) and AI.6 need the machine. **Merged** into
  `plan-38-hold` @ 2f85f4f; `test_hold.py` 22 passed; pushed. B3
  (plan-level review) dispatched on cb78963...2f85f4f.
- **39-T2** DONE_WITH_CONCERNS → PR #256 (`plan-39-t2-matte`, 4 commits:
  `masks.py`, the promotion + `MatteNode` + `declare_mattes`, the
  `mask-as-picture` fixture (+8 goldens), a matte's size = `size_for`'s).
  Fast 3996/2 skipped. Concerns for T5/controller: `masks` not yet on
  `hotreload.MODULES` (plan 38's file); a promoted cable draws red (T5);
  one word in `ui_presets.py`. Reviewer dispatched.
- Gates on `plan-37-pictures` @ 761aef3 (C4 + C3 + C1): fast **4024 passed,
  2 skipped**; goldens **128 passed**, 757 unmoved. Pushed; C2 dispatched
  off it.
- **39-T2 review** (`reviews/39-T2-review.md`): **Needs fixes** — the
  mask-port binding must refit a non-frame-sized mask (the look-back
  fetches its cover 1:1); `on_reload` must drop the mask passes. Sent
  back with the merge of `plan-39-vision` (T0+T1) into its branch.
- **39-T2** fixed (52121a0: a mask port gets the mask refitted to the
  frame's size, promotion and cut fit the original by cover, `on_reload`
  releases the passes, `own_size` passes through; 19bf4d4 the merge of
  T0+T1 into its branch, bookkeeping only). **Merged** into
  `plan-39-vision` @ 06db42b; goldens + `test_graph_masks`: 171 passed
  (132 golden jobs, 773 pictures). Pushed. T3 dispatched off 06db42b.
- **37-C2** DONE_WITH_CONCERNS → PR #258 (`plan-37-c2-hover`: 68335cf the
  hue read, e1a05e4 the hover + switch, a233deb review fixes). Review
  `reviews/37-C2-review.md`: Needs fixes — the hue read was a synchronous
  `tex.read()` (a GPU wait per reading frame); fixed as a 16×16 pass into
  a pixel buffer collected next frame; the lean now 20°·sin(hue − red)
  (no flip at cyan); reads stop when the switch goes off. **Merged** into
  `plan-37-pictures` @ 48b263e: fast **4035 passed, 2 skipped**; goldens
  **128**, 757 unmoved. Pushed. C5 (docs) dispatched off 48b263e.
- **38-B3 review** (`reviews/38-B3-review.md`): **Needs fixes** — Critical:
  a landing during a hold strips the program's effects/switches/resizes
  (every `GraphSection.land` re-settles them); Important: the delay reset
  on a load hits the program renderer; GRAPH reads the held graph while
  drawing the preview; seams for plans 37 (the canvas renderer helper)
  and 39 (no segment workers in the preview). Rulings 12–13; fixes with
  the B1 agent on `plan-38-b3-fixes`.
- **38-B3 fixes** → PR #259 (`plan-38-b3-fixes`, b4ebba9 + c834e74):
  the `hold.keep(kind, names)` hook in `GraphSection._settle` (ruling
  12; `_values` twin 12b), the delay reset to the preview while held,
  `hold.canvas_renderer` over five reads, M1/M3/M5/M8; verification
  (`reviews/38-B3-fixes-review.md`) found I-a (undo marks taken while
  held re-created program-only instances after Take) → fixed; `PROGRAM_IDS`
  table raises on an unknown kind. `test_hold.py` 32. **Merged** into
  `plan-38-hold` @ cd56b6f: full suite **4201 passed, 2 skipped** (one
  load-flaky media test, passes serially); fast 3990. Pushed. B4 (docs)
  dispatched off cd56b6f.
- **39-T3** DONE_WITH_CONCERNS → PR #260 (`plan-39-t3-cut`): `CutNode`,
  the flip flag (`graph.mask_of`), `declare_cuts`, the cut-out fixture
  (+8 goldens, 781). Review `reviews/39-T3-review.md`: **Needs fixes** — a
  cut must be transparent to laid-over-ness (`_Build.laid_over` recurses
  through `cut.image` as through an effect), the cut-out goldens
  re-recorded in the same task. Sent back.
- **39-T3** fixed (302b5cd: `laid_over` recurses through `cut.image`; two
  tests; the 4 cut-out scene goldens re-recorded in the same task — the
  under now shows inside the disc through the kaleidoscope's gaps).
  **Merged** into `plan-39-vision` @ 5c3f226: goldens **134 passed** (781
  pictures), fast **4046 passed, 2 skipped**. Pushed. T4 dispatched off
  5c3f226 with the plan 38 seam (no workers in the preview) and the flip
  flag in PROMOTE_FS/fit in its brief.
- **37-C5** DONE_WITH_CONCERNS → PR #261 (`plan-37-c5-docs`, 9ffcd27, docs
  only): rows **417–429 + 460** (fourteen: D1–D5, then the build's
  rulings; 460 the sheets/nearest-kept/map), checks **370–376 (AH)**,
  ARCHITECTURE (the GRAPH page paragraph), DECISIONS ("Nodes as pictures
  (plan 37)"), the plan file (built: P1, P3; P2 a dry run awaiting the
  owner's list), README, CHECKPOINT, TESTING-GUIDE. **Merged** into
  `plan-37-pictures` @ (see git) — **plan 37's branch is complete** bar P2.
  B4 told to overflow from 461.
- **38-B4** DONE → PR #262 (`plan-38-b4-docs`, 7d87c9f, docs only): rows
  **430–439 + 461–470** (twenty: D1–D5 (rec), then the rulings; 460 skipped
  as plan 37's), checks **377–383 (AI)**, `38-hold.md` corrected ("reads
  through" row) + "What changed in the build", ARCHITECTURE §2 + Host
  row + §4 (`hold.py`), DECISIONS table, README, CHECKPOINT, TESTING-GUIDE.
  **Merged** into `plan-38-hold` @ 24a899f — **plan 38 complete**.

## Merges into the integration branch
1. **plan 38** — `plan-38-hold` @ 24a899f → `plan-37-38-39-integration`
   @ **9560027** (clean). Gates: see below (running).
- **Offered to the owner ahead of the rest** (the prompt's §3): PR #251
  retargeted at `main`, marked ready (plan 38 + #248's docs); PR #263
  `plan-39-t0-edges → main` (T0's edges.glsl + #248's docs). If either is
  merged first, the integration branch merges `main`.
   Gates on 9560027 (plan 38 in): fast **3990 passed, 2 skipped**; full
   suite **4201 passed, 2 skipped** (one load-flaky,
   `test_migrate_library::test_the_real_picture_check_passes_an_old_preset`,
   passes serially); goldens **128 passed**, 757 pictures unmoved;
   `frame-signatures.json` unchanged. Pushed.
- **39-T4** DONE_WITH_CONCERNS → PR #265 (`plan-39-t4-segment`, 4 commits +
  review dd48e12): `segment.py` (worker, Vision + torch backends,
  `pick_backend`), `SegmentNode` + pins + motion + the flip everywhere
  (`PROMOTE_FS`/`fit`/`MaskPicture`/`mask_port`), `declare_segments`,
  `pyobjc-framework-vision`, the segment-motion fixture (+8 goldens), the
  plan 38 seam (no worker without `segment_cfg`; close closes only its
  own). Review `reviews/39-T4-review.md`: Needs fixes — `smooth` quantised
  to a permanent ghost (now float32), `laid_over` through a segment, plus
  minors (frame-thread join, shared exit deadline, live-test markers,
  rows). **Merged** into `plan-39-vision` @ 8a56a20: goldens **136 passed**
  (789 pictures), fast **4084 passed, 2 skipped**. Pushed. T5 dispatched.
2. **plan 39 (T0–T4)** — `plan-39-vision` @ 8a56a20 → integration @
   **2b185ea** (branch `integ-39`, fast-forwarded). One conflict
   (`preset.py`: the declares into `_settle` through `hold.keep`);
   `PROGRAM_IDS` + `HELD_GROUPS` gain the three kinds (decisions 14);
   `masks` on `hotreload.MODULES`. Gates: fast **4120 passed, 2 skipped**;
   full **4342 passed, 2 skipped** (no flakes this run); goldens **136
   passed, 789 pictures**, identical to `plan-39-vision`; signatures
   unchanged. T5/T6 land on `plan-39-vision` and merge after as a second
   step.
- **39-T5** DONE_WITH_CONCERNS → PR #267 (`plan-39-t5-graph`, b2ac105 +
  442cd89 + review ee302ed): picker (masks ▸ with matte/cut; media ▸
  with segment — the channels stay under pictures ▸; one word to fold
  back), the cut-out starter (exactly W6's four wires, says what it
  replaced and that the scene's geometry is unwired on a blank preset),
  mask cables purple by the maker's type, `segment.N` pins drawn, words
  on stand-ins, `/7` round trips. Review `reviews/39-T5-review.md`:
  Approved (minors: `returns()` keyed on the taker; `_fresh` removed; a
  row for insert-effect on a promoted cable). **Merged** into
  `plan-39-vision` @ 505739f: fast **4105 passed, 2 skipped**; goldens
  **136**, 789. Pushed. T6 (docs) dispatched off 505739f; rows overflow
  from 471.
- **39-T6** DONE_WITH_CONCERNS → PR #268 (`plan-39-t6-docs`, b18b10e, docs
  only): rows **440–459 + 471–497** (the eight owner decisions 440–447,
  then the rulings), checks **384–393 (AJ)**, ARCHITECTURE (port types,
  node/module/thread tables, boundaries), DECISIONS ("Masks are their
  own wire"), the plan file (built), README, CHECKPOINT, TESTING-GUIDE,
  SETUP. **Merged** into `plan-39-vision` @ 2a57af6 — **plan 39's branch
  is complete**. Final integration agent dispatched: plan 39 (T5–T6) then
  plan 37 into the integration branch, docs reconciled once.
3. **plan 39 (T5–T6) then plan 37** — branch `integ-37`: 1feddab (plan 39
   T5–T6, docs reconciled with plan 38's) then **96773ca** (plan 37
   C1–C5): `ui_graph.py` resolved (hold chips first, plan 36's, the tint
   chip last; C1's canvas/node kept); thumbnails read through
   `ui_graph.picture_sources` → `hold.canvas_renderer` (the preview has
   its own `PreviewTextures` while held; output 1's node shows the
   monitor), five tests in `tests/test_hold_thumbnails.py`; `THUMBS["cut"]`
   added, matte and segment stay text (row 500 — a follow-up); the faces
   map regenerated for plan 39's fixtures; register rows **417–500** in
   order (498–500 the integrator's), groups AH/AI/AJ, TESTING-GUIDE
   renumbered. Gates (integrator): fast **4227 passed, 2 skipped**; full
   **4449 passed, 2 skipped** (one load-flaky media test, passes serially);
   goldens **136 passed, 789 pictures**, `tests/golden` identical to
   2b185ea; signatures unchanged against cb78963. Fast-forwarded.
   Controller's own final gates below.

## Final
- Integration branch head **4a1e646** (96773ca + the run's records). The
  controller's own gates on this Mac: fast tier **4227 passed, 2 skipped**;
  full suite **4449 passed, 2 skipped** (one pre-existing load-flaky media
  timing test, `test_a_slow_close_never_holds_the_frame_thread`, failed
  under `-n auto` and passes serially); goldens **136 jobs, 789 pictures**
  (757 at the base − 0 + 32 for four new fixtures; 8 + 4 re-recorded with
  their reasons); `frame-signatures.json` unchanged; `hyperspace/library/`
  byte-identical; ruff: the base's findings only, none in files the run
  touched.
- **Final PR #270** `plan-37-38-39-integration → main`, the owner merges.
  Ahead of it, on their own: **PR #251** (plan 38) and **PR #263** (T0's
  edges.glsl), both → main; if either lands first, this branch merges
  `main`.
- Waits on the owner: plan 37 D1 (the faces' list; two questions in
  decisions 10), rows 417–500, hand checks 370–393.
