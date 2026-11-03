# Wave 1 of the post-show plan: the opening prompt for the orchestrating session

Paste everything below the line into a fresh Claude Code session opened in
`/Users/dallman/antigrav_repos/hyperspace`. It is written for the session
that orchestrates, not for a builder: the orchestrator reads, briefs, reviews
and merges; builders build.

---

You are orchestrating **wave 1** of the Hyperspace post-show plan. The plan
is the Claude Doc "Tier 2 and 3 build order"
(https://claude.ai/artifact/VGSHyfG5sJFqxov8fgdPes); read its sections
"The ordering rule", "From asks to PRs", "The PR list by wave", "Decisions
that gate a wave", "Rules every PR follows" and "Wave 0 status" before
anything else. Wave 0 is merged to `main`; the owner (Dan) wants wave 1 run
the same way: one builder agent per item in its own worktree, one PR per
item to `main`, an independent code review and a fix round on every PR, and
a union-branch proof that the wave's PRs pass together before anything
merges. Do not start wave 2.

## Read first, in this order

1. `hyperspace-python/docs/DECISIONS.md` (the preset contract, plan 43; the
   deck rows; the continuity rule; the tapers row; the media clock row).
2. `hyperspace-python/docs/plans/43-preset-contract.md` — the audit with the
   C2 and D3 worklists. Note: schema `/8` is plan 40's, so **C2 is `/9` and
   D3 is `/10`**, and the hands' default calibration is fitted to the eye
   (`ghost.calibration` with `mm = null`), which C2 must handle.
3. `hyperspace-python/docs/plans/44-decks.md` — the singleton inventory and
   D1–D6. D1 is the first code step and the conflict magnet.
4. `hyperspace-python/docs/plans/45-video-audio.md` — V1's API for V2
   (`Soundtrack.enable()/disable()/read(at, n)`, `status`, mono at −3 dB).
5. `REVIEW.md` (repo root), `hyperspace-python/docs/ENGINEERING.md` (hot
   reload contract), `hyperspace-python/docs/plans/merge-checklist.md`,
   `hyperspace-python/docs/ARCHITECTURE.md` §3 and §4.
6. `hyperspace-python/docs/DECISION-REGISTER.md` rows 554–570 and
   `docs/plans/11-hand-checks.md` groups AQ–AV (wave 0 and the Joy-Con).

## What wave 0 left you

- `main` carries plan 43 and 44 (docs), the GRAPH canvas as a media source
  (`panel:graph`), the `@clock` directive and the shader lint
  (`tests/test_shader_time_lint.py` with an allowlist of four offenders),
  exponential speed and log amount tapers with a `units: {"fx.depth":
  "taper"}` marker on every row holder (presets, patches, desk templates,
  `bindings.json`), V1's lazy audio decode, group hygiene (a `group_high`
  floor, now the ninth field of the library's Marks, and settle hooks
  `Bindings.on_modifiers` / `Bank.on_change`), and the **feedback** starter
  (renamed from echo; a new `fade.glsl` effect scales premultiplied colour
  and alpha). The Joy-Con is plan 46 (#315).
- The owner runs `tools/retaper_routes.py --write` on the library once
  (backs up to `~/Hyperspace/library-backup-<stamp>`). Until then old files
  convert at load. **C2's migration tool must run the retaper first or
  refuse an unmarked library**, so one bump moves everything.
- Note on wave 0's history: K1 (#318) landed inside #322's squash (35ad814) because #322's branch had merged it to share one `fx.py` hunk; `git log` shows no commit titled for K1, but every K1 file is on `main`.
- Numbers already taken: plans 43–46; register rows through 570; hand
  checks through 429; hand-check groups through AV. **Pre-assign** numbers
  to builders in their briefs (wave 1 starts at plan 47, row 571, check 430,
  group AW) so their doc tails do not collide on content, only on position.
- Doc tails (`DECISION-REGISTER.md`, `DECISIONS.md`, `11-hand-checks.md`,
  `plans/README.md`, and the `ARCHITECTURE.md` module table) conflict
  between any two PRs. They resolve by union; a small script that sorts the
  register rows by number and the README by plan number makes the result
  tidy. Expect to re-merge `main` into each PR when it reaches the head of
  the merge queue; the base-branch policy needs a green CI run on the
  pushed branch, so queue with `gh pr merge --squash --delete-branch --auto`
  and wait, one PR at a time.
- Merging may be refused by the auto-mode permission classifier ("Merge
  Without Review") unless the owner has said this session may merge. Ask
  before the first merge; do not work around a refusal.

## The wave 1 items (from the plan's PR list)

Each is its own PR to `main`, branch `wave1/<id>`, built by one builder in
an isolated worktree, with the tests, docs rows and hand checks the plan's
rules require, the fast tier (`uv run pytest -q`) and `uv run ruff check .`
clean, and no golden moved unless the PR body says which and why.

| Id | Item | Lane | Size | Waits on |
| --- | --- | --- | --- | --- |
| D1 | The `Deck` object: bundle registry, view, routing table, router, banks, presets, learn, undo, marks, renderer, hold into `hyperspace/deck.py` with **no behaviour change**; `Deck.build` replaces the construction order `tests/test_undo.boot` copies; the proof test in plan 44 §D1 | Core | L | nothing; **while it is open, `params.py`, `routing.py`, `library.py`, `preset.py`, `undo.py`, `hold.py` and `app.main` are frozen for every other PR** |
| C2 | One orbit camera: `camera.*` and `eye.*` become one preset group, schema `/9`, a `tools/` migration that stamps each library preset's eye after running the retaper, the hands fitted to the rig's reference eye, optional saved pose | Core | M | **owner's yes on register row 555** (one camera in the preset overturns "the camera is the rig"); rebase on D1 |
| K2 | Port warp (drift, scale) and tripcolour (pulse) onto `@clock`; shrink the lint allowlist; flip the strict xfails in `tests/test_fx_clock.py` | Time | S | nothing |
| K3 | `view.media_rate` and `view.inst_rate` integrated by the host | Time | S | nothing (touches `view`/media transport, not fx) |
| K4 | The RINGS pattern's colour step (`m_colour` in `patterns`) and the spatial faults in glimmer, wobble, fractals; the lint does not catch "param scales space", so this PR needs its own rule or a UV-harness check | Time | S–M | nothing |
| V2 | The mixer: per-channel gain, a per-video play-audio toggle that calls `Soundtrack.enable()`, one output stream; the transport is the clock | Media | M | nothing (V1 merged) |
| L1 | Preset folders 1: recursive listing under presets, folder-qualified names, bank references by relative path, trash in `~/Hyperspace/trash` (never synced) | Library | M | touches `library.py`: **start after D1 merges**, or build it in a new module and leave `library.py` edits to a follow-up |
| U1 | Panel fold stage 1 (pane always on with selection, presets, dream, faces, analyzer sections) | UI | M | Dillon's lane; do not assign it to a builder unless the owner says so |

Decisions the owner answers before or during this wave (ask at the start,
with the plan's recommendations, and proceed with everything not gated):
row 555 one camera (gates C2); rows 556–559 the deck rows (558, what is
shared and lent, shapes D1's membership; the plan recommends: dream worker
lent, segment per renderer, media sources shared with channel state per
deck, analyzer and clock shared); row 564 delay loops are the trails
mechanism (recorded, not decided).

## How to run it

1. Confirm `main` is the springboard (`git fetch`, `git log -1 origin/main`),
   that the fast tier passes there, and that no builder branch from wave 0
   is still open.
2. Brief each builder with: the item's row above, the files it owns and the
   files it must not touch, its pre-assigned register row / hand-check
   number / group letter / plan number, the commit trailer lines the
   session requires, the PR title and body conventions (a "Review fixes"
   section is added later), and "do not merge; do not run any migration
   against `~/Hyperspace` or the Drive folder". Launch D1, K2, K3, K4 and V2
   together; launch C2 when row 555 is answered; launch L1 after D1 merges.
3. When a builder reports: run `/code-review medium <PR>`, send the findings
   back to the same builder (it keeps its context), and re-review once more
   when the fixes were large. Keep a union branch of `main` plus every
   finished PR, run the fast tier on it after each fold, and push it as
   `origin/wave1-union` as a preview, never to merge.
4. Merge in this order, re-merging `main` into each PR at the head of the
   queue: D1, C2, K2, K3, K4, V2, L1. D1 first because every later Core PR
   rebases on it; C2 before anything else touches the camera.
5. After the last merge: both Macs pull, `uv sync`, restart; the owner runs
   the retaper (if not yet) and C2's migration; hand checks for the wave;
   then write the wave 2 opening prompt the way this one was written and
   stop.

## Rules that held in wave 0 and hold here

- Branch from `main`, merge to `main`; no long-lived integration branch.
- A schema move ships its migration tool and a backup; saves write the
  newest schema only; both Macs update together; land it between shows.
- Behaviour-neutral steps are tested as such (goldens unmoved plus the
  old-way/new-way state comparison plan 44 specifies for D1).
- Restart, not hot reload, for a PR that adds a module or a field on a
  long-lived object; the PR body says which.
- Every PR adds its DECISIONS line, register row and hand-check rows; plan
  docs are updated in the PR that changes what they say.
- Report faithfully: failing tests are reported with their output; a
  skipped step is said to be skipped.
