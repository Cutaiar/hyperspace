# Wave 3 of the post-show plan: the opening prompt for the orchestrating session

Paste everything below the line into a fresh Claude Code session opened in
`/Users/dallman/antigrav_repos/hyperspace`. It is written for the session
that orchestrates, not for a builder: the orchestrator reads, briefs, reviews
and merges; builders build.

---

You are orchestrating **wave 3** of the Hyperspace post-show plan. The plan
is `hyperspace-python/docs/plans/tier-2-3-build-order.md` (the owner's
export of the Claude Doc "Tier 2 and 3 build order"; the doc itself cannot
be opened by a session's connectors — never retry it; the repo copy is the
reference). Read its "The PR list by wave" (rows 3.1–3.9) first. Waves 0, 1
and 2 are merged to `main`; the owner (Dan) wants wave 3 run the same way:
one builder agent per item in its own worktree, **on Opus** (`model:
"opus"`), one PR per item to `main`, an independent code review and a fix
round on every PR (a second pass when the fixes were large, a third when the
second was), and a union branch proving the wave's PRs pass together before
anything merges. Do not start wave 4.

## Read first, in this order

1. `hyperspace-python/docs/plans/wave-2-session-prompt.md` — how wave 2 was
   run (the checkpoint section, the rules, the testing and review lessons),
   and `docs/plans/tier-2-3-build-order.md` "Rules every PR follows".
2. `hyperspace-python/docs/DECISIONS.md` — "The preset contract (plan 43)",
   "Decks (plan 44)" (D1–D3 built), "Patches and groups (plan 40)" and the
   plan 50 rows, "Media" (V1–V3), "UI" (plan 49 stages 1–2), "Process".
3. `hyperspace-python/docs/plans/44-decks.md` §3 **D4** (deck B offscreen
   and the `output.xfade` mix pass), §4 (hold becomes copy A into B — D5,
   wave 4), §5 (the crossfader stays the dim), §8 (the performance rules:
   the panel's deck at `preview_size`, one dream worker lent, the render cap
   on both renderers, each media channel read once a frame), and the D1–D3
   "built" notes (what changed: `routing_sources.py`, the lead deck, the
   session registry and table held by reference, the one clock).
4. `hyperspace-python/docs/plans/50-one-format.md` (F1: two names over one
   shape, `patch/2`, module presets as patches of one group, groups hold any
   node the preset saves with the full rule at save) and
   `docs/plans/40-patches.md` for **P1** (frame kinds in groups and
   patches), **P2** (replace the host's dream; the dream owning its params)
   and **P3** (wire-as-saved take-over, register row 524).
5. `hyperspace-python/docs/plans/45-video-audio.md` — **V4** (sync with
   video as master; varispeed: the callback reads sequentially from its own
   sample position slewed toward the transport's, resamples by the
   transport's speed, reverse and rate ≠ 1 sound like tape; decides the
   loop-wrap case) and "What fights the rule".
6. `hyperspace-python/docs/plans/49-pane-fold.md` — **U3** (stage 3: the
   rail goes, the page param becomes "focus section"; what stages 1–2 built
   and the notes they left).
7. The triage's base chase (**B1**: the verb "while held, commit the
   performer into the base" on the param model, as a deck operation; B2 the
   gamepad row is wave 4) and the Ultraleap orbit camera (**O1** room-frame
   palm orientation lanes; **O2** a clutch and routes onto the one camera)
   — the build-order doc's "From asks to PRs" rows; plan 43 C2 for the one
   camera and the hands' calibration (row 575).
8. `REVIEW.md`, `docs/ENGINEERING.md` §15 (hot reload) and §16 (testing:
   the tiers, `--dist load` with a restart cap of 4, the live lock outside
   the timeout, why `glfwInit()` hangs on the Mac and the recovery),
   `docs/ARCHITECTURE.md` §3–§4, `docs/DECISION-REGISTER.md` rows 590–647,
   `docs/plans/11-hand-checks.md` groups BD–BM (wave 2).

## What wave 2 left you

`main` after wave 2 carries, merged in this order on 2026-11-03 (all by
squash, each behind a green CI run; the union tier before each):

| PR | Item | What it did |
| --- | --- | --- |
| #341 | docs | the owner's verdicts on rows 544–553, 564, 580, 585–589 (545 overturned: north / south / east / west for every four-button cluster and D-pad — an unscheduled work item); the build-order doc in the repo; the wave 2 checkpoint |
| #343 | V3 | the analyzer hears the mixer's block as a `mix` source (`audio.mix` on the AUDIO page); a stalled stream decays; rows 594–596 |
| #344 | T3 | a momentary FINE button on the APC40 (SEND B): a knob turns in tenths while held, re-based at the note-off; `desk.fine` on the rig; rows 609–610 |
| #345 | U1 | plan 49 stage 1: the GRAPH side pane always on with selection, presets, lookback, faces, analyzer sections; fold state per Mac; rows 597–601 |
| #346 | D2 | `routing_sources.py`: the shared sources split from the per-deck evaluator; per-router resolution and followers; the one clock on the sources; rows 590–593 (591–593 pending the owner) |
| #347 | I1 | `--dist load` with a restart cap of 4; the live lock outside the timeout, per holder, run id + pid; the Xbox-pad flake fixed at its source (GLFW terminated); `tools/sort_register.py`; rows 605–606 |
| #348 | T2 | Shift-drag fine mode on the panel's sliders and faders; rows 607–608 (ROUTING's own sliders and GRAPH's backdrop slider not reached yet) |
| #349 | L2 | plan 48 stage 2: a folder tree on PRESETS and in the pane, move / new / rename / remove, the library tools walk folders; rows 636–638 |
| #350 | U2 | plan 49 stage 2: media, fx, LFO, seq, audio, camera, output fold into the pane; the FX page retired (its index kept); LOOKBACK redrawn as the two picture nodes; rows 626–632 |
| #351 | D3 | the session / performance line made mechanical: `build_session` / `build_performance`, `SessionTable` + a deck's `Bindings` by reference, `Presets` owns current/dirty, `MediaSources` + `Channels`, the bus cuts the preset's, `ghost.mirror` a session key, desk templates and `modules` gone; **schema `/10`, show `/3`**, `tools/migrate_library.py` extended (backs up, every folder down); rows 611–625 |
| #352 | F1 | plan 50: one reader for presets (`/10`) and patches (`/2`, an optional `group`); module presets are patches of one group under `patches/<group>/`; a group holds any node the preset saves, the full rule at save; the migration's patch step; rows 639–647 |

(#351 and #352 merge at the owner's word, between shows, both Macs together —
check `gh pr list` and `git log origin/main` for whether they have landed
before briefing anyone; D4, P1–P3 and B1 stack on them.)

- **Numbers taken:** plans through 50; register rows through 647 (602–604,
  633–635 and 648–655 were pre-assigned and unused — reuse them); hand
  checks through 488 (480 unused); hand-check groups through BM.
  **Pre-assign** to builders: wave 3 starts at plan 51, row 648, check 489,
  group BN.
- **Owner to-dos from wave 2** (check they happened): both Macs pulled,
  `uv sync`, restarted; after #351/#352 merge, on the Mac with the library:
  `uv run python tools/migrate_library.py` (dry run), then `--apply` (it
  backs up to `~/Hyperspace/library-backup-<stamp>`, runs the retaper,
  rewrites every preset to `/10`, every show to `/3` with a `.bak-v2-look`,
  moves module presets to `patches/<group>/` and rewrites patches to `/2`);
  the CI workflow's `--dist load --max-worker-restart=4` flags (the diff is
  in #347's body; a session token lacks the `workflow` scope); hand checks
  444–488 (groups BD–BM; 476 is the two-node LOOKBACK by eye, 470 the
  wanted-window line).
- **Rows pending the owner:** 546, 550–552 (plan 42), 591–593 (D2: the
  bank/modifier lanes shared until D4; `devices.poll` keeps `router=`;
  follow every live table, read none), and every "(rec)" in 594–647.
- **Rough edges recorded for this wave** (row 625 and the build notes):
  a deck whose pass runs after the lead's apply lands its session offsets
  one frame late (D4 settles the pass order); `hold._preset_part` puts
  `ghost.mirror` back with the look on Drop (D5 retires `hold.py`); the
  library's presets kind belongs to the deck built last (D5); the LFO /
  envelope / sequencer / modifier lanes publish into the shared sources
  (D4 gives each deck its own layer, row 591); T2's fine mode does not reach
  ROUTING's own sliders or GRAPH's backdrop slider (row 608); the on-screen
  desk still draws SEND B as free (row 609; the clean form moves `desk.fine`
  beside `desk.save` in `register_desk`).
- **The owner's words to carry:** the fold is ours (U3 is in this wave; it
  was Dillon's lane); the "grand cleanup pass" that normalises every preset
  to the newest format and drops old cruft is wanted some day (unscheduled);
  north / south / east / west is the controller vocabulary to build (545,
  unscheduled); the rig concept survives for now and goes away in a later
  wave.

## The wave 3 items (the doc's 3.1–3.9)

| Id | Item | Lane | Size | Waits on |
| --- | --- | --- | --- | --- |
| D4 | Deck B rendered offscreen and `output.xfade` as the one mix pass; the APC crossfader stays the dim; the panel's deck at `preview_size`, one dream worker lent, each media channel read once a frame and both renderers handed the same frame; the pass order settled so a deck's session offsets are not a frame late; each deck its own modifier/bank lane layer (rows 591, 625) (plan 44 §3 D4, §5, §8; doc 3.1) | Core | M | D3 merged; **while open, `deck.py`, `render.py`'s renderer construction, `outputs.py` and `app.frame` are frozen for every other PR** |
| B1 | The base chase verb on the param model: while held, commit the performer into the base, as a deck operation (doc 3.5) | Core | M | D3 merged; not `deck.py` / `app.frame` while D4 is open (the verb lives in `params.py`) |
| P1 | Frame kinds allowed in groups and patches (doc 3.2; plan 40, plan 50's `RIG_KINDS` rule says which stay refused) | Format | M | F1 merged |
| P2 | "Replace the host's dream" in the conflict sheet; the dream owning its own params (doc 3.3) | Format | M | P1 |
| P3 | Wire-as-saved take-over (doc 3.4; **register row 524 gates it: free ports only, or a take-over chip** — ask) | Format | M | F1 merged; row 524 |
| U3 | Panel fold stage 3: the rail goes, the page param becomes "focus section" (doc 3.6; plan 49) | UI | M | nothing (U2 is merged); ours |
| V4 | Sync with video as master; varispeed (doc 3.7; plan 45 V4) | Media | M–L | nothing (V3 is merged) |
| O1 | Room-frame palm orientation lanes (doc 3.8) | Core (hands) | M | nothing (C2 is merged); `hands/` only |
| O2 | A clutch and routes onto the one camera (doc 3.9) | Core (hands) | M | O1 |

Not wave 3 (the doc's wave 4): D5, D6, N1–N3, B2, Dillon's #314 and #287
rebases.

Decisions the owner answers before or during this wave (ask at the start,
with the recommendations, and proceed with everything not gated): row 524
(gates P3); "the APC crossfader stays dim" is assumed by D4 (confirm);
rows 591–593 (D4 changes 591's answer); whether a second, lower-resolution
dream worker should serve the panel's deck's preview (row 558: to be
measured in D4 — report the measurement, do not decide); merge authority
for the wave (ask again).

## How to run it

1. Confirm `main` is the springboard (`git fetch`, `git log -1 origin/main`;
   #351 and #352 merged), the fast tier passes there
   (`uv run pytest -q -n 4 -p no:cacheprovider`), and no wave 2 builder
   branch is still open (`gh pr list`).
2. Brief each builder with: its row above, the files it owns and must not
   touch, its pre-assigned register rows / hand-check numbers / group
   letter / plan number, the commit trailer line
   (`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`), the PR
   title and body conventions (Why / What / Testing with counts verbatim /
   Restart or hot reload / an empty `## Review fixes` heading, ending with
   the Claude Code line), and "do not merge; do not run any tool against
   `~/Hyperspace` or `/Users/dallman/My Drive/Hyperspace`". Launch D4, U3,
   V4, O1 and P1 together (stagger the first fast-tier runs); B1 beside D4
   once its files are agreed; P2 and O2 after their parents' fix rounds,
   stacked on the parent branch and retargeted when it merges (as D3 on D2
   and F1 on D3 were); P3 after row 524 is answered.
3. **Testing on the shared Mac**: builders run the FAST tier only, at most
   twice each, one run at a time; the orchestrator runs every `--all`
   (goldens included) itself, serially — wave 2 never ran the goldens on
   the Mac, so **run `--all` once on the union before the first merge of
   this wave** (D4 moves the renderer; the goldens are the proof) and read
   ENGINEERING §16 first. If a run sits at 99 % for minutes, kill it and
   read the recovery.
4. **Reviews**: `/code-review medium <PR>` checks the PR out in the current
   directory — run every review from a scratch worktree of your own (a
   branch from `origin/main` under `.claude/worktrees/`), never from the
   owner's checkout or a builder's; reviews are one at a time in that
   checkout. Send findings back to the same builder (it keeps its context);
   a second pass (`low`) when the fixes were large; a third when the second
   found real bugs (D2 and D3 needed three).
5. **The union**: a session cannot run git inside another worktree it made
   — hand the union to a **keeper agent** in its own worktree: it folds each
   review-complete PR onto `origin/main`, resolves the doc tails by union
   (`DECISION-REGISTER.md` with `tools/sort_register.py`, keeping the `## `
   heading groups; `11-hand-checks.md` groups in letter order;
   `DECISIONS.md`; `plans/README.md`; `ARCHITECTURE.md`'s table), runs the
   fast tier, pushes `origin/wave2-union`'s successor `origin/wave3-union`,
   and does the merge-queue step (an alias branch `m/<id>` = the PR +
   `origin/main`, pushed onto the PR's branch). **Standing rule:** a squash
   merge of a branch that predates a docs fix on main can revert it (D2
   reverted the owner's verdicts on rows 585–589; T2's queue step restored
   them) — the owner's verdict wording wins on every fold.
6. Merge in dependency order, each with `gh pr ready` +
   `gh pr merge --squash --delete-branch --auto` and a commit body that
   carries the trailer line and the review and union counts: U3, V4, O1,
   D4, B1, P1, O2, P2, P3. Watch each merge land before the next queue step
   (CI is case-sensitive Linux: L2's case-rename test failed there once).
7. After the last merge: both Macs pull, `uv sync`, restart; hand checks for
   the wave; then write the wave 4 opening prompt the way this one was
   written and stop.

## Rules that held in waves 0–2 and hold here

- Branch from `main`, merge to `main`; no long-lived integration branch; a
  PR that depends on an unmerged one stacks on that branch and retargets.
- A schema move ships its migration tool and a backup; saves write the
  newest schema only; both Macs update together; land it between shows.
  (None is expected in wave 3; P1 may need `patch/3` — say so early.)
- Behaviour-neutral steps are tested as such (goldens unmoved plus the
  old-way/new-way state comparison plan 44 specifies; D4's same-state test
  extends D1–D3's).
- Restart, not hot reload, for a PR that adds a module or a field on a
  long-lived object; the PR body says which.
- Every PR adds its DECISIONS line, register row(s) with a `### <n>.`
  section each, and hand-check rows; plan docs are updated in the PR that
  changes what they say.
- Report faithfully: failing tests are reported with their output; a
  skipped step is said to be skipped; a flake is named and re-run alone
  before it is called a flake.
