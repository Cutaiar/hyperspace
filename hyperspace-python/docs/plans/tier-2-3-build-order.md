# Tier 2 and 3 build order

> Exported from the Claude Doc of the same name
> (https://claude.ai/artifact/VGSHyfG5sJFqxov8fgdPes) by the owner on
> 2026-11-03, since the orchestrating sessions' connectors cannot open
> it. From here the repo copy is the reference; the doc's schedule
> figure did not export. Wave 2's checkpoint against it is in
> [`wave-2-session-prompt.md`](wave-2-session-prompt.md).

## Where we are

**Last updated 2026-11-07.** **Waves 0–3 are merged. Most of wave 4 is merged, including the rename; of what's left, some waits on the owner's hand checks and some has no gate. Wave 5 is running beside it, in three tracks.** The sections below are the original plan of 2026-11-02, kept as written; where they disagree with this section, this section is right. **The wave 5 orchestrator updates this section whenever an item changes state** (`wave-5-session-prompt.md`, "Reporting").

Nothing in waves 4 or 5 has been tried on real hardware. Hand checks from 419 on are unrun, but for 425.

| Wave | State | PRs |
| --- | --- | --- |
| 0 | **Merged** 2026-11-02 | #313, #316, #317, #319, #320, #321, #322, #324, #315 the Joy-Con, #323. See below |
| 1 | **Merged** 2026-11-03 | D1 #327, C2 #333, K2 #325, K3 #328, K4 #326, V2 #329, L1 #334, plus #331 |
| 2 | **Merged** 2026-11-04 | D2 #346, D3 #351, F1 #352, U1 #345, U2 #350, L2 #349, T2 #348, T3 #344, V3 #343, I1 #347 |
| 3 | **Merged** 2026-11-04 | U3 #360, V4 #357, O1 #358, O2 #362, D4 #359, B1 #356, P1 #355, P2 #361, P3 #364, plus #366 |
| 4 | **Most merged; the rest below** | Below |
| 5 | **Running** since 2026-11-06, in three tracks | Below; [`58-wave-5.md`](58-wave-5.md), [`wave-5-session-prompt.md`](wave-5-session-prompt.md) |

**Wave 4 as it changed.** The owner's answers replaced much of rows 4.1–4.7: two fixed `Deck`s and a DJ crossfader instead of hold-as-copy, named players, node mode saved in the patch, N3 gone. Authority is [`wave-4-session-prompt.md`](wave-4-session-prompt.md), "The owner's answers".

| Item | State |
| --- | --- |
| Plan #367; AZ #368, MR #371, B2 #369, PA #372, CI #363, PC #375 | Merged |
| D5a #370, D5b #373, PL #376, D5c #378, PS #379, NM0 #377, **D5d #380** (HOLD, TAKE and DROP gone) | Merged |
| UL undo latch #386; PC2 pair consent #387; glossary signed #384 | Merged |
| **SEM** #388 and #389 (`preset.py` is `loadable.py`, `Presets` is `LoadedPatch`, `RigWires` is `BusCuts`) | Merged |
| D5e words #393; D6a + D6b playlist #392, #400; #287's rewrite #395 (the original #287 is still open, for the owner to close); test undo leak #394; cursor-in-a-field fix #398; H1 doc tails #391 | Merged |
| N1a #396 + N1b #397, node mode on the APC | The owner's row 711 reversal is built and reviewed twice, with a real bug fixed (a committed look came back wrong after a visit). **Waits on hand checks 506–509,** then `main` merged in, `--all`, #396 before #397 |
| #365 Joy-Con v0 | Another session's. **Waits on the owner's check 520–521, which needs the Joy-Con charged** (its PR: flat until the charger arrives). It also **conflicts with `main`** (register, `devices.py`, `routing.py`, `ui_pad.py`), which must be resolved before it lands |
| N2a + N2b node mode on pads; then NSEW | N2 built on `wave5/n2`, rows 820–823, checks 635–638; NSEW after it |
| WORDS: "session" and "rig" leave the panel | Merged #407. "Preset" becomes "patch" in the panel with the migration |
| Row 740, a player's moves on the meta stack | Merged, #417 |
| The PC words pass, row 668 | Its small remainder merged, #417 |
| **The one migration:** `/11`, `loadable/`, shows into install files, trash deleted (`57-format-lane.md` §7, §7a) | Not written; after NSEW. The owner runs it, with Hyperspace quit on both Macs. Then both Macs update and launch once (`58-wave-5.md` §2a), which is the cleanup's gate. It should also carry the `overlay.*` aliases on the `bindings/4` road (plan 58 §9) |

**Wave 5: live table.** Numbers: rows from 770, checks from 600, groups from DA.

| Stage | Item | PR | State |
| --- | --- | --- | --- |
| Done | H1 doc tails | #391 | Merged |
| 1 | H2 test truth; `tools/wait_green.py` | #403 | Merged |
| 1 | SM1 poi probe | #410 | Merged. Shows the hand running away on the owner's tape: row 786 asks |
| 1 | SC1 screens by name | #404 | Merged. Nothing replugged; checks 600, 601 |
| 1 | LY1 one mirror, closing a leak between looks | #408 | Merged. Row 773 asks about two hands mirrored apart |
| 1 | LY2 honest flags, unsaved half | #409 | Merged |
| 1 | SM2 graph zoom | #411 | Merged. Row 787 asks about the show's display and resizing |
| 1 | SM3 matte thumbnails | #405 | Merged |
| 1 | TY1 type ratchet | #412 | Merged; baseline 1,554. An optional CI step is a patch in its body, for the owner |
| 1 | TY2 audit as the record | #413 | Merged; #273 closed |
| 2 | **SC3a** the picture stops depending on one display | #420 | Merged. Windows byte-identical to the old build, pacing within noise, on this Mac. Row 782 asks about 240 fps while locked. Checks 607-610 |
| 3 | SM4 audit faults: R15, U9, U10 fixed; R14 moot; V8 closed in SC3a | #414 | Merged |
| 3 | LY3 the toggle says it | #416 | Merged |
| 3 | SM5 row 740, and row 668's remainder | #417 | Merged. Row 800 asks about what ⌘Z reaches |
| 3 | CT1 controllers set up in the app | #418 | Merged. Rows 796-799 ask. Not met real hardware or a real Drive |
| 3 | HR hot reload, broken since #370 (not in the plan) | #421 | Merged |
| 3 | A test of CT1's flaking on `main`; a quit saves its own files (row 803) | #423 | Merged |
| 3 | HR's rule's import order, flaking on `main` (row 812) | #427 | Merged |
| 3 | SC2 a row per display | #424 | Merged. Pictures byte-identical to `main`. Rows 804-807 |
| 4 | **SC3b** hot-plug | #425 | Merged. **Not done: no real cable has been unplugged.** On merged `main` it passed end to end with a private virtual display on a locked Mac: only the app's half. Hand check 629 goes first; RT1 waits on it. Rows 813-816 ask |
| New | **Library's reads off the frame thread:** `Library` and its scan read the Drive on the main thread (`library.py:1944`, `:3649`), so a stalled Drive can hang launch or freeze frames; and `Library()` opens the home on a `config.toml` that won't parse (`app.py`, `sharedfile.library_root` is the fix). Found by CT1 and SC2; not in plan 58 | | Not started; after the migration, which owns `library.py` until then |
| 5 | TY3, then TY4, annotations only: last, after the cleanup, so they annotate what survived | | Not started |
| Gated | CL2, then CL1 after the owner's dry run; CL3, after CT1's defaults; CL4, once `fx/` is deleted | | **Gate:** the owner says the migration ran and both Macs have opened the new library |
| Gated | RT1 | | The same gate, plus SC3b's real unplug and CT1 |
| After the migration | SM6 a cart starts by itself; LY2's saved half; SC2's move of `output.bg`, `.alpha` | | Not started |

**Waiting on the owner now:** hand checks 506–509 (group BS, the panel fold: they gate node mode, they don't test it; node mode's own checks 541–545 come in with #396 and #397), the Joy-Con check 520–521 (group BW, written on #365's branch, not yet on `main`), and the per-face render check (the last box under "Decisions that gate a wave"). The first two hold up the end of wave 4, then the migration, then the cleanup, and so TY3 and TY4. They don't hold up the rest of wave 5. **Also:** the real unplug, hand check 629. And the owner's answers on rows 773, 782, 786, 787, 796-799, 805-807 and 813-816, built as recommended meanwhile; the parts of rows 779 and 800 still marked; and one choice inside row 711, on #397: a knob's value after a chase commit across a node mode visit. **#419, Dillon's, also says row 802,** which HR took: it must renumber before it lands. **Everything left in Track W5 waits on the migration:** TY3 and TY4, after the cleanup; SM6, LY2's saved half, SC2's move of `output.bg` and `.alpha`, and the library's reads. The owner runs the migration, with Dylan's Mac.

Nov 2, 2026 · @Robert

Branch from `main` at 72da1ed. Dillon's two PRs from last night (#306 controllers, #312 pad readouts) are merged there, their branches are deleted, and the fast suite passes on that commit (4410 tests). No integration branch is needed: every PR below branches from `main` and merges to `main`. Our own open PR #313 needs a two-file rebase and goes first. The twelve remaining tier 2 and tier 3 asks become 39 PRs in six lanes over five waves. The two refactors with the most gravity, the Deck object and the preset contract, open wave 1, and they turn out to be one line: what belongs to a look is what belongs to a deck.

## The springboard

Everything Dillon built in the last 18 hours is on `main`. Plan 42 (#306, any controller in any role, the DualSense Edge over USB and Bluetooth) merged at 02:25 and its follow-up (#312, the pad window's four NanoVG readouts) at 05:14 on 2026-11-02; both source branches are deleted. The local checkout, `origin/main` and HEAD all sit at 72da1ed, and the fast tier passed there: 4410 passed, 2 skipped, 34 s. Note that #306 added `hidapi`, so `uv sync` before the first run of this build.

| PR | Author | State | Merges onto 72da1ed? | What to do |
| --- | --- | --- | --- | --- |
| #313 GRAPH canvas as a media source (`panel:graph`) | us | open, CI green, awaiting Dan | two conflicts with #312: the hot-reload order in `hotreload.py` (add `media.panel`) and `Panel.close` in `ui.py` (close the canvas tap beside NanoVG). Both are unions. | rebased on main 2026-11-02 (4453 passed); awaiting a human merge click, restart after |
| #314 Plan 42 lab: ideas 8–13, six Edge patches | Dillon, draft, marked hold | open | clean | merged 2026-11-02 at Dan's say (cf96377) so the Joy-Con lab work shares one base; the ideas stay unvetted on a real pad and the patches carry no pad rows until the one-format work |
| #287 the dial's readings are the preset's, pad node shows them | Dillon, draft since 2026-10-29 | open | clean | Dillon's call; it is the preset contract in miniature (`pad.dial.*` into the preset) and the pane layout belongs with fold stage 1 |
| #308 CHANGELOG v1.2 (Devin) | bot | open | clean | merge or close at will; no code |
| #299 `--laptop` / `--single` launch flag | us | open since 2026-10-30 | clean | merge or close; independent |
| #273 structural audit docs | us, draft | open | n/a | reference only; its five-phase order informs the deck series |
| #223 venues | Dillon, draft since 2026-10-17 | open | 10 files conflict (config, app, placement, ui, docs) | Dillon's; outside this plan, rebase when wanted |

No integration branch. The previous integration branches turned into the very mega-merges you want to avoid (#195 carried 21 work packages, #224 carried plans 28 and 30). Every PR in this plan branches from `main` and merges to `main` on its own; a PR that depends on an unmerged one stacks on that branch and retargets when the parent lands, as #168 did on #167. Dillon's own note on #314 already assumes this: it waits for "the coming app-wide refactor" and rebases onto it.

## Wave 0 status, 2026-11-02 evening

Wave 0 is merged (2026-11-02, night, at Dan's word). Merged in order: #317, #320, #313, #322 (whose squash also carried K1, so #318 was closed as landed), #316, #321, #319, #324 (a V1 test-race fix), #315 the Joy-Con, and #323 the wave 1 opening prompt. Each PR had an independent code review and a fix round by its builder, two passes for #313, #316 and #315. Every PR appends to the same register tail, so each was re-merged with `main` at the head of the queue, its doc tails unioned, the fast tier run, then squash-merged behind a green CI run. `main` after the wave: 4669 passed, ruff clean. The wave0-union preview branch is deleted. The wave 1 opening prompt is `hyperspace-python/docs/plans/wave-1-session-prompt.md`.

| PR | Item | Review | State |
| --- | --- | --- | --- |
| #317 | C1 plan 43, the preset contract and its audit (docs) | read | ready. Found `/8` already taken by plan 40's groups, so C2 is `/9` and D3 `/10`; found the hands' default calibration is fitted to the eye, which C2 must handle |
| #320 | D0 plan 44, decks (docs) | read | ready. 28 singletons, 16 per deck, 11 shared, the dream worker lent; register rows 556–559 pending Dan |
| #313 | GRAPH canvas as a media source | two passes, 18 findings fixed | ready. Leased texture pool, exact rate-0 hold, texture generations on the frame, a shared `SharedSource` base, `off page` status, import-time backend check |
| #318 | K1 `@clock` directive, shader lint, UV harness | one pass, 9 fixed | ready. Allowlist holds warp drift, warp scale, tripcolour pulse and the RINGS pattern's colour step; hand check 419 (group AR) |
| #322 | T1 tapers and the depth migration | one pass, 9 fixed | ready. Presets, patches, desk templates and `bindings.json` all migrate under one `units` marker; `tools/retaper_routes.py` NOT yet run on the library (Dan runs it at the checkpoint); hand check 420 (AT) |
| #316 | V1 video audio decode | two passes, 18 fixed, timing hardening pending | ready bar one push. Lazy (`enable()`), nothing read until V2 asks; float32 stereo 48 kHz; mono lands at −3 dB from the resampler; hand check 421 (AQ) |
| #321 | G0 group hygiene | one pass, 8 fixed | ready. Settle hooks on the mechanism (`Bindings.on_modifiers`, `Bank.on_change`), the id floor in the Marks (a ninth field, which D1 must know), a refused load no longer wipes groups; hand check 422 (AU) |
| #319 | E1 the feedback starter (was "echo") | one pass, 8 fixed | ready. Renamed to avoid the look-back's `echo` pins; decay is a new `fade` effect scaling premultiplied colour and alpha; hand check 423 (AS) |

Beside wave 0, the Joy-Con session opened draft PR #315 (plan 46, group AV, rows 565–570); it stays out of this order until its real-controller check runs.

The checkpoint, in order:

1. Done 2026-11-02: every PR above is merged. Every other PR adds rows to the same register tail, so after each click I rebase the rest (the conflicts are unions; the only real ones are `fx.py` between K1 and T1 and one ARCHITECTURE row, both already resolved on the union).
2. Done 2026-11-02, in the order listed above.
3. On both Macs: `git pull`, `uv sync`, restart (new modules and fields). Then on the Mac with the library: `uv run python tools/retaper_routes.py` to read the plan, then `--write` (it backs up to `~/Hyperspace/library-backup-<stamp>` first). Until this runs, old presets convert at load and nothing is lost.
4. Hand checks 419–423 at the machine when convenient; 419 waits for K2.
5. Decisions wave 1 needs: one camera in the preset (row 555), and the four deck rows 556–559.

What changed in the plan from building it: schema numbers (`/9`, `/10`, `/11`); the echo starter is the feedback starter; T1 grew from "tapers plus route depths" to every row holder (presets, patches, desk templates, session table) under one marker; V1's decode is off until V2 asks, so it costs nothing in a show today; G0 touched `routing.py`, `modbank.py` and `library.py`'s Marks, which D1 must read before it bundles them.

## The ordering rule

A PR goes as early as it can without being rewritten later. That puts work in two groups: the refactors that move the ground (the Deck object, the preset contract, the one saved format, the panel fold) go first and serially within their lane; everything that would sit on moved ground waits behind the move. Work that touches none of that ground (shader clocks, tapers, video audio, folder listing) runs in parallel from day one, because no later refactor rewrites it.

The decks and the preset contract are one series, not two. The deck plan's third step is "split session params from per-deck performance params", and the contract's whole job is to draw the line between what a look owns and what the rig owns. Those are the same line: what belongs to a look is what belongs to a deck. So the Deck object is built first as a pure bundling of today's singletons (registry, routing table, router, hold bases, undo, the library's current), then the contract migration moves the renderables (eye, spin pose, hands look, bus cuts, inlined desk template) across that line once, as the per-deck half. Built apart, the eye would move twice.

The one format waits for the contents. Patch, group and preset become one format with one loader and one conflict sheet, but only after the contract has settled what a preset holds; otherwise the loader is written for a preset whose shape is about to change. Patches v2 (frame kinds, replace the host's dream) then lands on the one format, and Dillon's held #314 rebases there, since its patches must carry pad rows.

The surfaces that point at a deck go last. Node mode, the scheduler and "controllers to A, panel to B" all need a deck to point at and a folded side pane to draw into, so they close the plan. The panel fold itself is Dillon's lane and runs the whole way alongside, because it moves UI ground that node mode and the folder tree sit on.

What changed against the triage doc:

- **Dropped:** spring on APC faders and knobs (owner, 2026-11-02). Insert any node and drag any node are already merged (#307).
- **Folded:** camera into the preset becomes the one orbit camera, the first contract PR. The hold hotfix is skipped; hold becomes "copy A into B" in the deck series, and a stopgap now would be a third partial snapshot to remove later. Harden node groups splits into pure hygiene now (ids never reused, membership at once, a corpus property test) and "a group holds any node" inside the one format.
- **Split:** the deck work becomes six behaviour-neutral PRs, video audio four, continuity one framework plus three ports, coarse and fine control one taper migration plus two surfaces, node mode three, folders two.
- **Added:** two docs-only gates (the contract line with its ownership audit, and the deck plan) so the two big series start from a written line rather than from the first diff.

## From asks to PRs

Every tier 2 and 3 row of the triage doc, plus the three tier 1 rows that never shipped, mapped to the PRs it becomes. Sizes are the triage doc's: S a day or less, M a few days, L a week or two.

| Triage item | Tier | Becomes | Grouped or split | Wave |
| --- | --- | --- | --- | --- |
| Parameter continuity (Trip warp and friends) | 2 | **K1** `@clock` directive integrated in `fx.py`, a lint over every shader ("no shader multiplies time by a param"), the UV-field test harness (M); **K2** warp and tripcolour ported (S); **K3** `view.media_rate` and `view.inst_rate` integrated (S); **K4** glimmer, wobble, fractals grid fixes (S) | split: one rule, then ports | 0, 1 |
| Coarse and fine control | 2 | **T1** signed-exp speed taper, zero-safe log amount taper, and the route-depth migration over the Drive library in the same PR (M); **T2** shift-drag fine mode in the panel (S); **T3** momentary fine button on APC knobs (S) | split: the taper change is a migration, the surfaces are not | 0, 2 |
| Insert any node, drag any node | 2 | merged as #307 | done | — |
| GRAPH canvas as a media source | 2 | **#313** rebased onto 72da1ed and merged | done bar the rebase | 0 |
| Base chase modifier | 2 | **B1** the verb "while held, commit the performer into the base" on the param model, as a deck operation (M); **B2** the gamepad row, once a button is chosen (S) | split: the verb before the binding; the verb waits for D3 so it is written once against the per-deck registry | 3, 4 |
| Preset folders | 2 | **L1** recursive listing under presets, folder-qualified names, bank references by relative path, trash in `~/Hyperspace/trash` (M); **L2** the tree in the PRESETS section of the folded pane (S–M) | split: storage before the tree; L2 waits for fold stage 1 | 1, 2 |
| Preset scheduler | 2 | **D6** a playlist document and a ticker that advances the on-air deck through the one mix pass (M) | folded into the deck series; its fade is D4's crossfade | 4 |
| Spring on APC faders and knobs | 2 | dropped by the owner 2026-11-02 | — | — |
| Harden node groups | 2 | **G0** ids never reused after ungroup, membership updated at once, a property test over the corpus (S); the rest, "a group holds any node, checked at save", is **F1** below | split: bug fixes now, the rule inside the one format | 0, 2 |
| Video audio | 2 | **V1** decode the audio track to memory, with "the transport is the one clock" written into the plan (M); **V2** mixer with per-channel gain and a per-video audio toggle (M); **V3** the analyzer picks the mix as a source (M); **V4** video as master, varispeed resampling (M–L) | split as the triage said | 0, 1, 2, 3 |
| Camera into the preset (tier 1 leftover) | 1 | **C2** one orbit camera: `camera.*` and `eye.*` merged into one preset group, schema /9 (plan 40 already took /8 for groups), a migration stamping each library preset's eye; optional saved pose | folded into the contract series; the first schema move | 1 |
| Echo / reverb starter (tier 1 leftover) | 1 | **E1** "echo" starter on the cable menu and "add echo after" on the node menu (S) | stands alone once the trails decision is made | 0 |
| Hold honesty hotfix (tier 1 leftover) | 1 | skipped; **D5** makes hold "copy A into B" | folded into decks | 4 |
| Preset as the self-contained unit | 3 | **C1** the contract line in DECISIONS.md plus an audit table of everything that crosses it today (docs, S); **C2** above; **D3** the migration: per-deck versus rig, moving spin pose, hands look, bus cuts and the inlined desk template into the preset, schema /10 (L) | merged with deck step 3: the same line | 0, 1, 2 |
| Patches v2 | 3 | **F1** one format: patch = group not yet saved = preset with no open pins, one loader, one conflict sheet, module presets and desk templates retired as separate ideas (L); **P1** frame kinds allowed in groups and patches (M); **P2** "replace the host's dream" in the conflict sheet, the dream owning its own params (M); **P3** wire-as-saved take-over, register row 524 (M) | split: format first, then the three capabilities | 2, 3 |
| Graph always on, pages fold into the side pane | 3 | **U1** stage 1: pane always on with selection, presets, dream, faces, analyzer sections (M); **U2** stage 2: media, fx, LFO, sequencer, audio, camera, output fold in; the FX page is retired (L); **U3** stage 3: the rail goes, the page param becomes "focus section" (M) | split as the triage said; Dillon's lane | 0–1, 2, 3 |
| A/B decks with crossfade | 3 | **D0** plan 44 written: what is per-deck and what is shared (dream worker, media channels, tempo, analyzer), the six steps (docs, S–M); **D1** the Deck object bundling registry, routing table, router, hold bases, undo and the library's current, no behaviour change (L); **D2** the router split: shared sources versus the per-deck evaluator (M–L); **D3** above; **D4** deck B rendered offscreen and `output.xfade` as the one mix pass, APC crossfader stays dim (M); **D5** controllers to A, panel to B, dirty dot and undo per deck, hold = copy A into B (L); **D6** above | split into behaviour-neutral steps; D3 is shared with the contract | 0, 1, 2, 3, 4 |
| Node mode per controller | 3 | **N1** APC knobs to the selected node's continuous params, drawn as a temporary page of cables from the controller node (M); **N2** gamepad page in the pad router, overlay axis rows, camera steer suppressed (L); **N3** "keep this one" = promote the cable to the preset through the Learn prompt (M) | split as the triage said; waits for D5 (a deck to point at) and U2 (one surface for params) | 4 |
| Ultraleap orbit camera | 3 | **O1** room-frame palm orientation lanes (M); **O2** a clutch and routes onto the one camera (M) | split; waits for C2 | 3 |

That is 39 PRs: 9 in wave 0, 7 in wave 1, 8 in wave 2, 9 in wave 3, 6 in wave 4, plus Dillon's two rebases (#314, #287) in wave 4.

## The schedule

&#91;embedded content: build order · 6 lanes, 5 waves, 4 gates\]

Read each lane left to right. Core carries the deck series and the contract; Format carries groups, patches and the one saved format; UI is Dillon's panel fold and the surfaces that land in it; Time, Media and Library are the lanes that no refactor rewrites, so they start now and run at their own pace. A wave is not a sprint, it is a dependency level: a PR may start as soon as its gate is merged, and lanes do not wait for each other. Wave 0 holds nine PRs that can all open this week.

## The PR list by wave

Within a wave every row is independent unless "waits on" says otherwise, so each wave is a parallel batch. The Core lane is serial by design: D1 is the conflict magnet, and while it is open nothing else in Core or Format touches `params.py`, `routing.py`, `library.py`, `undo.py` or `hold.py`; the other four lanes keep moving.

| # | PR | Lane | Size | Waits on | Why here |
| --- | --- | --- | --- | --- | --- |
| 0.1 | #313 canvas source, rebased | Format | S | nothing | already built; two union conflicts with #312 |
| 0.2 | C1 contract line + ownership audit (docs) | Core | S | nothing | the line D3 and F1 are built to |
| 0.3 | D0 plan 44: decks, per-deck vs shared, six steps (docs) | Core | S–M | nothing | the gate for D1 |
| 0.4 | K1 `@clock` directive, shader lint, UV-field test | Time | M | nothing | touches `fx.py` and shaders only |
| 0.5 | T1 tapers + route-depth migration | Time | M | nothing | changes what depths mean; better before anything reads depths anew |
| 0.6 | V1 decode the audio track | Media | M | nothing | `media/` only |
| 0.7 | G0 group hygiene | Format | S | nothing | bug fixes with no format question |
| 0.8 | E1 echo starter | Format | S | trails decision | menu entries only |
| 0.9 | U1 fold stage 1 | UI | M | nothing | Dillon; spans waves 0–1 |
| 1.1 | D1 the Deck object, behaviour-neutral | Core | L | 0.2, 0.3 merged | the biggest diff; everything in Core and Format rebases on it |
| 1.2 | C2 one orbit camera, schema /9 + migration; the hands' default calibration is fitted to the eye (ghost.calibration), so C2 fits them to the rig's reference eye | Core | M | owner yes; rebase on D1 | first schema move, small enough to run beside D1 |
| 1.3 | K2 warp + tripcolour on `@clock` | Time | S | 0.4 |  |
| 1.4 | K3 media rate + instance rate integrated | Time | S | 0.4 |  |
| 1.5 | K4 glimmer, wobble, fractals | Time | S | 0.4 |  |
| 1.6 | V2 mixer, per-channel gain, audio toggle | Media | M | 0.6 |  |
| 1.7 | L1 folders: listing, names, bank paths, trash to home | Library | M | nothing | touches `library.py` listing only; rebase on D1 if it lands first |
| 2.1 | D2 router split: shared sources vs per-deck evaluator | Core | M–L | 1.1 |  |
| 2.2 | D3 the line: per-deck vs rig, renderables into the preset, schema /10 | Core | L | 2.1, 1.2 | the contract migration, done once |
| 2.3 | F1 one format: patch = group = preset, one loader, one conflict sheet | Format | L | 2.2 | needs the preset's contents settled |
| 2.4 | U2 fold stage 2, FX page retired | UI | L | 0.9 | Dillon |
| 2.5 | L2 folder tree in the PRESETS section | UI | S–M | 0.9, 1.7 |  |
| 2.6 | T2 shift-drag fine mode in the panel | Time | S | 0.5 |  |
| 2.7 | T3 momentary fine button on APC knobs | Time | S | 0.5 |  |
| 2.8 | V3 the analyzer picks the mix | Media | M | 1.6 |  |
| 3.1 | D4 deck B offscreen + `output.xfade` | Core | M | 2.2 | the one mix pass |
| 3.2 | P1 frame kinds in groups and patches | Format | M | 2.3 |  |
| 3.3 | P2 replace the host's dream; dream owns its params | Format | M | 3.2 |  |
| 3.4 | P3 wire-as-saved take-over | Format | M | 2.3, row 524 |  |
| 3.5 | B1 base chase verb on the param model | Core | M | 2.2 | written once against the per-deck registry |
| 3.6 | U3 fold stage 3, rail removed | UI | M | 2.4 | Dillon |
| 3.7 | V4 sync, video as master, varispeed | Media | M–L | 2.8 |  |
| 3.8 | O1 room-frame palm lanes | Core (hands) | M | 1.2 |  |
| 3.9 | O2 clutch + routes onto the one camera | Core (hands) | M | 3.8 |  |
| 4.1 | D5 controllers to A, panel to B, hold = copy A into B | Core | L | 3.1 | retires `hold.py`'s second graph |
| 4.2 | D6 playlist advancing the on-air deck | Library | M | 4.1 |  |
| 4.3 | N1 node mode, APC slice, drawn as cables | Core + UI | M | 4.1, 2.4 |  |
| 4.4 | N2 node mode, gamepad page | Core + UI | L | 4.3 |  |
| 4.5 | N3 "keep this one" through the Learn prompt | Core + UI | M | 4.3 |  |
| 4.6 | B2 base chase gamepad row | Core | S | 3.5, button decision |  |
| 4.7 | #314 and #287 rebased (Dillon) | Format, UI | — | 2.3, 2.4 | pad rows ride in patches; dial readings are the preset's |

## Decisions that gate a wave

Each of these blocks one PR, and the wave it sits in. None blocks wave 0 except the echo starter's.

- [x] **One camera in the preset** (gates 1.2, C2; yes, #333). Merge `camera.*` and `eye.*` into one orbit camera owned by the preset. Overturns the recorded "camera is the rig" decision. Recommend yes; it is also the first contract step.
- [x] **Skip the hold hotfix** (shapes 1.1 and 4.1; skipped, and hold is gone, #380). Recommend yes: hold becomes "copy A into B" in D5, and a stopgap now is a third partial snapshot to remove later. Until D5 lands, hold leaks as it did on 2026-10-30.
- [x] **What is per-deck and what is shared** (settled in 0.3, plan 44, before 1.1). Recommend: one dream worker and one segment worker shared, lent to the on-air deck; media channels and the analyzer shared; tempo shared; everything that renders per deck. The deck bench already said one dream per on-air deck is the limit.
- [x] **Delay loops are the trails mechanism** (gates 0.8, E1; landed as the feedback starter, #319). The look-back keeps the dream, so the two never compete.
- [x] **Register row 521, schema on every save** (touches 2.3, F1; closed by row 576). Recommend every save writes the newest schema; that is already the rule since 2026-10-25.
- [x] **Register row 524, wire-as-saved take-over** (gates 3.4, P3). Free ports only, or a take-over chip. Owner, 2026-11-04: yes, the take-over chip.
- [x] **Which gamepad button is base chase** (gates 4.6, B2; BACK, #369). GUIDE is free but opens the OS overlay over Bluetooth; plan 42's `pad:LP` / `RP` back buttons on the Edge are the obvious candidates now.
- [x] **The APC crossfader stays dim** (overturned: the crossfader crossfades and MASTER dims, #380) (assumed by 3.1, D4) until dim has another home.
- [x] **Plan 42 D1–D10** (answered or bulk accepted, 2026-11-06) (register rows 544–553) are still "(rec), pending the owner" after last night's merges. Not a gate here, but they are Dillon's and open.
- [x] **Dillon's #287** (rewritten by us on `main` after SEM, owner 2026-11-06) (dial readings into the preset): merge after 1.2 as a contract step, or fold its pane layout into U1. Dillon's call.
- [ ] **Render check at the machine** (still not run; in plan 58) before anyone touches face code: flip the face map on a dragonfly preset and unwire the backdrop on logo-wobble. Tier 4, but it is the only way the per-face question gets answered.

## Rules every PR follows

- **Branch from `main`, merge to `main`.** No long-lived integration branch. A PR that depends on an unmerged one stacks on that branch and retargets to `main` when the parent lands.
- **One PR, one concern, its own tests, the fast tier green** (`uv run pytest`, about 35 s on this Mac). The deep review before merge, as #312 had.
- **A schema move ships its migration.** Each of C2 (/9), D3 (/10) and F1 (/11, if the one format needs it; plan 40 already took /8 for groups) bumps once and ships a `tools/` script that rewrites the Drive library forward after a backup under `~/Hyperspace`, as `calm_lanes.py` and the /7 migration did. Saves write the newest schema only; no old-schema support. Both Macs pull before the next session on the new schema, so land schema moves between shows, not the night before one.
- **Behaviour-neutral steps are tested as such.** D1 and D2 ship with the corpus goldens unmoved and a test that the registry, routing table and undo stack reach the same state through the Deck as they did before.
- **File ownership while a wave runs.** Core owns `params.py`, `routing.py`, `library.py`, `undo.py`, `hold.py`, `preset.py`, `learn.py`. Format owns `patches.py` and the group code in `graph.py`. UI owns `ui.py` and every `ui_*.py`; Core touches a page only in D5 and N1–N3, and then through the published selection and the deck pointer. Time owns `fx.py` and the shaders. Media owns `media/`. A PR that must cross a wall says so in its body and goes after the owning lane's open PR.
- **Docs land with the code.** Each PR adds its DECISIONS line, its register row and its hand-check rows (the next free numbers after 418), and the plan docs (plan 43 the contract audit, plan 44 decks, plan 45 video audio; the Joy-Con session has plan 46, register rows from 565 and hand checks from 424) are updated in the PR that changes what they say.
- **Restart, not hot reload,** for any PR that adds a module or a field on a long-lived object; the PR body says which.
- **Dillon's held PRs are rebased by Dillon** when their gates merge; this plan only schedules the gates.
