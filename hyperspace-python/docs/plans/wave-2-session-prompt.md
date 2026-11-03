# Wave 2 of the post-show plan: the opening prompt for the orchestrating session

Paste everything below the line into a fresh Claude Code session opened in
`/Users/dallman/antigrav_repos/hyperspace`. It is written for the session
that orchestrates, not for a builder: the orchestrator reads, briefs, reviews
and merges; builders build.

---

You are orchestrating **wave 2** of the Hyperspace post-show plan. The plan
is the Claude Doc "Tier 2 and 3 build order"
(https://claude.ai/artifact/VGSHyfG5sJFqxov8fgdPes). **The wave 1 session
could not open that doc** (not shared with its account), so the wave 2 list
below is reconstructed from the wave 1 prompt, the plan docs in the repo and
the owner's words; read the doc's "The PR list by wave" first and correct
the table before briefing anyone. Wave 1 is merged to `main`; the owner
(Dan) wants wave 2 run the same way: one builder agent per item in its own
worktree, one PR per item to `main`, an independent code review and a fix
round on every PR (a second pass when the fixes were large), and a union
branch proving the wave's PRs pass together before anything merges. Do not
start wave 3.

## Read first, in this order

1. `hyperspace-python/docs/DECISIONS.md` — "The preset contract (plan 43)",
   "Decks (plan 44)", "Media" (V1, V2), "Process" (row 589), the continuity
   row ("No shader multiplies time by a param", now with K2–K4 done).
2. `hyperspace-python/docs/plans/44-decks.md` — §2 (the singletons table),
   §3 **D2** and **D3** (the next two steps; D3 is schema `/10`), §8 (risks:
   hot reload, the two-Macs rule, performance).
3. `hyperspace-python/docs/plans/43-preset-contract.md` §6 ("What D3 must
   do") and §7 (the owner's answers; `ghost.mirror` stays the rig's).
4. `hyperspace-python/docs/plans/45-video-audio.md` — V3 (the analyzer
   listens to the mix) and V4 (sync with video as master; varispeed), and
   "What fights the rule".
5. `hyperspace-python/docs/plans/48-preset-folders.md` — "What stage 2
   might do".
6. `REVIEW.md`, `hyperspace-python/docs/ENGINEERING.md` §15 (hot reload)
   and §16 (testing: the tiers, the thread timeout, the live lock, why
   `glfwInit()` hangs on the Mac and the recovery), `docs/plans/merge-checklist.md`,
   `docs/ARCHITECTURE.md` §3 and §4.
7. `hyperspace-python/docs/DECISION-REGISTER.md` rows 571–589 and
   `docs/plans/11-hand-checks.md` groups AW–BC (wave 1).

## What wave 1 left you

`main` is 3b9b06d (the L1 merge, 2026-11-03; full tier 5133 passed) and carries,
merged in this order on 2026-11-03:

| PR | Item | What it did |
| --- | --- | --- |
| #331 | T0 | the test suite cannot hang the Mac: pytest-timeout's thread method for xdist workers (serial runs keep signal), `--max-worker-restart=0`, a per-account file lock for every `live` test, a child-process glfw probe (`gl_window_ok`) — row 589 |
| #327 | D1 | `hyperspace/deck.py`: one `Deck`, `Deck.build` the one construction order for `app.main` and the headless `tests/test_undo.boot`; no behaviour change — row 571; rows 556–559 answered by the owner (as recommended; 558: only the dream worker is reserved for the on-air deck, the look-back and dream knobs are per deck) |
| #325 | K2 | warp's drift and scale and tripcolour's pulse on `@clock` (the directive takes a product rate `a*b`) — row 577 |
| #328 | K3 | `view.media_rate` / `view.inst_rate` integrated by the host (`ViewState.media_phase` / `inst_phase`, `seed_phases`) — row 578 |
| #326 | K4 | RINGS' colour step; glimmer, wobble, fractals measured and left alone; `tests/test_step_continuity.py` checks every shipped knob early vs late; the shader lint's allowlist is empty — rows 579–580 |
| #329 | V2 | the mixer (`media/mixer.py`): `media.<c>.audio` and `media.<c>.gain`, one output stream reading at the transport's playhead, forward play only — rows 581–583 |
| #333 | C2 | one orbit camera: the eye is the preset's and modulatable, the pose saved (`pose` section; waits for Take under HOLD), schema `/9` on every save, `tools/migrate_library.py --apply` (backs up, runs the retaper, rewrites the library), hands calibration on the rig's reference eye — rows 572–576, 555 answered |
| #334 | L1 | preset folders stage 1 (plan 48): recursive listing, folder-qualified names, the bank by path, the trash on this Mac — rows 584–588 |

Also on `main` from the owner: #330, the Joy-Con as a 4D totem (plan 47,
`hyperspace/totem.py`, params registered in `app.main`'s panel hook).

- **Numbers taken:** plans 43–48; register rows through 589 (565–570 are
  the Joy-Con's and exist only as a `### 565–570.` section — the table rows
  were never added: a tidy for this wave); hand checks through 443;
  hand-check groups through BC. **Pre-assign** to builders: wave 2 starts
  at plan 49, row 590, check 444, group BD.
- **Owner to-dos from wave 1** (check they happened): both Macs pulled,
  `uv sync`, restarted; `uv run python tools/migrate_library.py` (dry run)
  then `--apply` on the Drive library between shows (it backs up to
  `~/Hyperspace/library-backup-<stamp>` and runs the retaper first);
  hand checks 419 and 430–443.
- **Known flakes, not any PR's** (make a small test-infra PR or assign):
  `tests/test_segment.py::test_vision_frees_each_jobs_memory` and
  `test_torch_runs_once_on_a_synthetic_frame` each crashed an xdist worker
  once under GPU contention (pass alone); `tests/test_pads_hid.py::test_an_xbox_pad_has_no_extras_and_a_simple_report_none`
  failed once under one test order (passes alone);
  `tests/test_render.py::test_shape_renders[...]` failed twice under load.
  Row 589's "Other options" records `--dist load` (the live lock now
  serialises live tests, so a crashed worker's queue could be redistributed)
  as the follow-up to decide with the owner.
- **The owner's words to carry:** the LOOKBACK page's split (look-back /
  dream / shared) is "a horrid representation of what's going on there"
  (2026-11-02) — a UI item for this or a later wave; and whether a second,
  lower-resolution dream worker could serve the panel's deck preview is to
  be measured in D4/D5 (row 558).

## The wave 2 items (verify against the plan doc)

| Id | Item | Lane | Size | Waits on |
| --- | --- | --- | --- | --- |
| D2 | Split the router's shared sources (`routing_sources.py`: feeds, labels, gates, rests, names, devices, clock, feed, felt) from its per-deck evaluator; `routing.py` re-exports; the same-state proof extended to two routers over one `Sources` (plan 44 §3 D2) | Core | L | nothing; **while open, `routing.py`, `devices.py`, `app.frame` and the adapters' `router.feed` sites are frozen for every other PR** |
| D3 | The session/performance line made mechanical: `build_session` / `build_performance`, `SessionTable` + a deck's `Bindings`, `Presets` owns `current`/dirty, `MediaSources` + `Channels`; `ghost` and `cloud` to performance, the bus cuts into the preset, desk templates inlined, no `default.json` fallback; schema **`/10`** and `hyperspace.project/3` with a one-way migration in `tools/` and a backup (plan 44 §3 D3 + plan 43 §6) | Core | L | D2 merged; land between shows, both Macs together |
| V3 | The analyzer listens to the mix: the mixer's summed block pushed into the analyzer's ring as a `mix` source beside `mic` and `file` (plan 45) | Media | S–M | nothing |
| V4 | Sync with video as master; varispeed: the callback reads sequentially from its own sample position slewed toward the transport's, resamples by the transport's speed, reverse and rate ≠ 1 sound like tape; decides the loop-wrap case (plan 45) | Media | M | V3 (same files) |
| L2 | Preset folders stage 2: move a preset between folders from the PRESETS page, make/rename a folder, `tools/move_library.py` and `tools/migrate_library.py` walk folders (plan 48 "stage 2") | Library | S–M | nothing |
| T1 | Test infra follow-ups: the flakes above (worker crashes under GPU contention: serialise torch/Vision live tests behind the live lock or an `xdist_group`), `--dist load` if the owner says so, the register tidy (rows 565–570 into the table; `###` sections in numeric order), module-scoped live fixtures under the lock (row 589's caveat) | Time/infra | S | nothing |
| U2 | Panel fold stage 2 | UI | M | Dillon's lane; do not assign unless the owner says so |

Not wave 2 unless the plan doc says so: F1 (patch, group and preset as one
format), P1–P3 (patches v2), N1–N3 (node mode), D4–D6 (deck B in render,
controllers to A / the panel to B, the playlist) — these follow D3.

Decisions the owner answers before or during this wave (ask at the start,
with the recommendations, and proceed with everything not gated): row 564
(delay loops are the trails mechanism — recorded, mark it decided or not);
plan 42's rows 544–553 and plan 46's 565–570 (pending the owner); for D3,
plan 43 §7's remaining items — `modules` labels (row 540: inert or dropped
with the default-module fallback), how many desk templates the Drive library
holds (`ls "<library>/desk/"`), and whether `ghost.mirror` stays the rig's
(the owner said yes on 2026-11-02 — confirm it is still so); the `--dist
load` follow-up (row 589).

## How to run it

1. Confirm `main` is the springboard (`git fetch`, `git log -1 origin/main`),
   the fast tier passes there (`uv run pytest -q -n 4 -p no:cacheprovider`),
   and no wave 1 builder branch is still open (`gh pr list`).
2. Brief each builder with: its row above, the files it owns and must not
   touch, its pre-assigned register rows / hand-check numbers / group
   letter / plan number, the commit trailer lines the session requires,
   the PR title and body conventions (a `## Review fixes` section is added
   later), and "do not merge; do not run any migration against
   `~/Hyperspace` or the Drive folder". Launch D2, V3, L2 and T1 together;
   V4 after V3; D3 after D2 merges.
3. **Testing on the shared Mac** (the wave 1 lesson): builders run the
   FAST tier only, `uv run pytest -q -n 4 -p no:cacheprovider`, one run at
   a time each; the orchestrator runs every `--all` (goldens included)
   itself, serially, in the builder's worktree venv; never more than two
   runs on the machine at once. If a run sits at 99% for minutes, kill it
   and read ENGINEERING §16's recovery.
4. **Reviews**: `/code-review medium <PR>` checks the PR out in the current
   directory — launch every review from a scratch worktree
   (`git worktree add --detach .claude/worktrees/review origin/main`), never
   from the owner's checkout or a builder's. Send findings back to the same
   builder (it keeps its context); a second pass when the fixes were large.
5. Keep a union branch of `main` plus every finished PR
   (`.claude/worktrees/wave2-union`), run the fast tier on it after each
   fold, push it as `origin/wave2-union` as a preview. Doc tails
   (`DECISION-REGISTER.md`, `DECISIONS.md`, `11-hand-checks.md`,
   `plans/README.md`, the `ARCHITECTURE.md` table) conflict between any
   two PRs and resolve by union; sort the register table by row number
   after each fold (a ten-line script does it).
6. Merge in this order, re-merging `main` into each PR at the head of the
   queue on an alias branch (`m/<id>`, pushed to the PR's branch), waiting
   for green CI, then `gh pr ready` + `gh pr merge --squash --delete-branch
   --auto` with a commit body that carries the trailer lines: T1, D2, V3,
   L2, V4, D3 (last: the schema move, between shows). The owner authorised
   merging-when-green for wave 1; ask again at the start of wave 2.
7. After the last merge: both Macs pull, `uv sync`, restart; the owner runs
   D3's migration; hand checks for the wave; then write the wave 3 opening
   prompt the way this one was written and stop.

## Rules that held in waves 0 and 1 and hold here

- Branch from `main`, merge to `main`; no long-lived integration branch.
- A schema move ships its migration tool and a backup; saves write the
  newest schema only; both Macs update together; land it between shows.
- Behaviour-neutral steps are tested as such (goldens unmoved plus the
  old-way/new-way state comparison plan 44 specifies).
- Restart, not hot reload, for a PR that adds a module or a field on a
  long-lived object; the PR body says which.
- Every PR adds its DECISIONS line, register row and hand-check rows; plan
  docs are updated in the PR that changes what they say.
- Report faithfully: failing tests are reported with their output; a
  skipped step is said to be skipped; a flake is named and re-run alone
  before it is called a flake.
