# Orchestrator prompt — build plan 13 with subagents

Paste everything below the line into a new Claude Code session started in
`/Users/dallman/antigrav_repos/hyperspace`. It is self-contained: it says
what to read, what is already decided, how to split the work, how to run
the subagents, and what the owner expects back.

---

You are the orchestrator for **plan 13, preset and session**, in
`/Users/dallman/antigrav_repos/hyperspace`. The Python app is in
`hyperspace-python/` (uv, pytest, ruff). You coordinate; subagents in
their own git worktrees write the code. Your job ends when every plan 13
work package is merged on main, the documents describe the code, and the
owner has a short list of checks only they can run at the machine.

## 0. Before anything

- Work in a git worktree (EnterWorktree). Never edit the shared checkout.
- Confirm `main` is at or after **4bffa9d** (plans 11 and 12 merged, PR
  #58 and #59 in) and that `uv run pytest -q` passes (808 at 4bffa9d) and
  `uv run ruff check .` is clean. If main has moved, read the new commits
  first.
- Another session may be authoring presets in `hyperspace/library/`
  (`bindings`, `fx`, `dream`, `projects`) and new `shaders/fx/*.glsl`.
  Touch factory preset files only where a work package requires it (WP5
  re-cuts the five `party-*` presets), keep those edits minimal, and
  rebase on main often.

## 1. Read, in this order

1. `hyperspace-python/docs/ARCHITECTURE.md`. §3 is the control model and
   is canonical: scene-setters write the base, exactly one performer per
   parameter writes an offset through `Router.modulate` (the only
   performer path), `Registry.apply()` lands both once per frame, the
   render stack only reads; hands and LFOs import nothing from the
   package. Nothing in plan 13 may break it. If a work package seems to
   need that, it is a decision for the owner (§5 below).
2. `hyperspace-python/docs/plans/13-preset-and-session.md`: the design.
   D1–D12 and §2.4 (the unified macro) are decided; §7 lists the work
   packages; §8 says what was settled after it was written.
3. `hyperspace-python/docs/DECISIONS.md`, especially "Presets and the
   desk" and every 2026-09-28 row. **Do not re-litigate any of them.**
4. `hyperspace-python/docs/DECISION-REGISTER.md`: every decision the owner
   made for plans 11–13, context-free, with the answer sheet. All rows are
   answered. It is the owner's one place to decide; any new fork goes here.
5. `hyperspace-python/docs/ENGINEERING.md` (behaviour; update the sentence
   you change) and `hyperspace-python/docs/AUDIT-2026-09.md` (the register
   plan 11 closed; mark new rows the same way).
6. `hyperspace-python/docs/plans/11-remediation.md` §5 "As built": what plan
   11 changed underneath plan 13's text (the library's document kinds,
   `learn.py`, `Router.apply_doc`, `routing.backup`, the keys as rows,
   `band.N.norm`). Plan 13 was written before most of it merged.
7. `hyperspace-python/docs/plans/12-presets.md` §7 and the performer cards
   in `docs/plans/assets/12-presets/`: what WP5 re-cuts.
8. `hyperspace-python/docs/plans/11-hand-checks.md`: the owner's
   machine-side list; plan 13 adds to it.

## 2. What is decided (summary; the documents above are authoritative)

- **Two nouns.** A *preset* (`hyperspace.preset/2`) holds every performance
  parameter's base, the performer routes, the APC40's preset layer, the
  macros with their subscribers, and a label per module. A *session* holds
  the rig: the analyzer (D9), the desk's global layer, the startup preset
  (D11), the bank. "Theme", "routing preset" and the UI word "scene" go.
- **A load replaces everything** (D2), with no exception: routes-only
  files become full presets in the migration; "partial" means only a
  module preset (D3, labels only).
- **Bank slots name preset files.** F1–F8 and the APC40's preset row load a
  slot; ⇧F1–F8 saves the live state as that preset into the user folder.
  The F-keys are already table rows (`routing.LOOP_KEY_ROWS`, PR #58)
  pointing at `theme.load.N` / `theme.save.N`; plan 13 retargets them.
- **The desk** (D4–D8, D12): two layers under a latched SHIFT (note 0x62)
  with its LED; the global layer is fixed in the session and never
  Learned into; invariant controls (faders, preset-select row, SHIFT, TAP
  TEMPO, METRONOME, NUDGE ±, transport) mean one thing on both layers; on
  a layer switch the knobs jump (endless encoders re-based by the ring
  message) and the faders soft-pick-up; an unmapped control does nothing
  and shows dark; a modifier is read at the press.
- **Global track knobs**, a first cut the owner expects to revise: four
  hand-feel settings (smoothing, response, catch, the selected axis's
  return) plus `tempo.bpm`, three knobs free. Build it so the list is data
  in the session file, not code.
- **One macro concept** (D10, §2.4): `macro.1–8` each has subscribers; a
  subscriber sets a param's **base** or scales a route's **depth**, over
  its own `from → to` range, so polarity is per subscriber. Base
  subscribers are scene-setters. A performer on a macro moves only its
  depth subscribers; base subscribers follow the macro's base. Routes lose
  `scale`; migration turns `scale: macro.N` into a depth subscriber
  `from 0, to 1`. The separate multi-target desk row is gone: a desk
  control that moves several things maps to one macro.
- **The ROUTING page** is one page over the loaded preset: its routes, its
  desk rows and macros, then the session's invariant and global rows
  read-only.
- **Sequencing:** plan 11 is merged, PR #47 is merged as is; plan 13 now
  runs from WP1 and re-cuts the five `party-*` presets in WP5.

## 3. First deliverable: bring plan 13 current, then start

Before any code, one docs-only PR that the owner can read in five minutes:

- A short "Against main" section in plan 13 mapping each §2–§7 claim onto
  the code as it now is (which module owns presets today, what
  `Library` document kinds already give you, what `learn.py` and
  `Router.apply_doc` already do), and correcting any sentence plan 11 made
  stale.
- **Exit criteria** for plan 13 (it has none): headless ones held by named
  tests, and machine ones added to `11-hand-checks.md` as a new group H,
  in the same format as the existing checks (commands, config keys,
  preset, gesture, pass, fail, which code a fail points at, and the
  headless test that shows the expected behaviour first). At minimum:
  SHIFT latch and its LED; knobs jump and faders pick up on a layer
  switch; an unmapped control is dark and dead; Learn refuses the global
  layer and invariant controls; a preset load lands every base and
  replaces every route; a macro with two opposite-polarity base
  subscribers; the startup preset; the five re-cut party presets.
- The work-package split you will run (§4), with the files each owns and
  the contracts between them.
- Any fork you find that is the owner's (§5), filed in the register.

Post it, then start work on everything that does not depend on an
answer. Do not wait for approval of the plan unless it contains a fork.

## 4. The work packages

Plan 13 §7 lists six. Suggested waves (adjust once you have read the code;
say why in the plan):

| Wave | WP | What | Depends on |
|---|---|---|---|
| 1 | WP1 | Performance / session split in `params.py`; snapshot and restore over it; session values in the session file | — |
| 2 | WP2 | Preset schema 2: loader, saver, referee, the one preset strip, the bank as file pointers, F-keys and the APC40 preset row retargeted, module presets unchanged | WP1 |
| 2 | WP3 | The desk: `layer` on MIDI rows, SHIFT latch and LED, invariant set, redraw on switch and load, fader catch reset, the global layer from the session; the unified macro (§2.4) with `scale` migrated | WP1; the preset shape of §2.1 as a contract with WP2 |
| 3 | WP4 | Learn writes into the loaded preset; refusals on the global layer and invariant controls; the ROUTING page as one page | WP2, WP3 |
| 4 | WP5 | One-time migration of project, bindings and factory files (with `routing.backup`-style `.bak` before any rewrite, never over a hand-made `.bak-*`); the five `party-*` presets re-cut; the routes-only factory files turned into full presets | WP2–WP4 |
| 4 | WP6 | Docs: ARCHITECTURE §3 and §3.8 and the file table, ENGINEERING, DECISIONS statuses from "decided, not built" to "standing", the register's notes, plan 12's cards ("press F-key"), CHECKPOINT, plans README row 13 | alongside WP5, last to merge |

Also file, do not build, two audit rows plan 12's review left in no
register (as new rows in `AUDIT-2026-09.md`, dated, with a Fix and a
Size): **named hand addresses** (`hand:left.roll` resolved by the adapter,
so a custom `[hands] dofs` list cannot silently scramble shipped presets),
and an **explicit groups-to-reset list** on a preset instead of "naming
one id resets its group". If WP5's re-cut makes the first one cheap to do
there, bring it to the owner as a fork rather than doing it.

## 5. Decisions that are the owner's

Anything that would change the control model in ARCHITECTURE §3, reverse
a DECISIONS row, change what a performer feels at the desk or the box, or
choose between designs with real trade-offs, is the owner's. For each:

- add an entry to `docs/DECISION-REGISTER.md` in the same shape as the
  existing ones (what it is, what the code does today, options in a
  table with the trade-off per option, a recommendation and why, what
  changes once answered) and a row to its answer sheet;
- add the same row to plan 13 and a pending line to DECISIONS.md;
- if the Claude Docs tools are available, mirror the entry into the
  owner's phone copy of the register,
  https://claude.ai/code/artifact/d24a5ece-f873-4020-838a-53d5a0ba3571
  (read it first; keep the file the canonical copy);
- tell the owner in one message: the id, one sentence of context, the
  options, your recommendation. Then keep working on everything that does
  not depend on it.

When the owner answers: record it the same day in all three places, then
build it.

## 6. Running the subagents

Use the Agent tool with `isolation: "worktree"` for each work package,
several in one message when they are independent. Each subagent prompt
must be self-contained and include, in this order:

1. **Setup.** `git fetch origin && git checkout -B plan-13-wpN-<slug>
   origin/main` (or `origin/<the branch it stacks on>`, then `git merge`
   of each dependency branch, resolving conflicts keeping both sides),
   and a check that the features it needs exist; stop and report if not.
   Then `uv run pytest -q` and `uv run ruff check .` green before any
   edit.
2. **The ids it closes and the decisions it implements**, quoted by
   number, with the files it owns and the files it must not touch
   (other agents' areas).
3. **Behaviour to build**, precise enough that the agent needs nothing
   else; the contracts with sibling packages (names, file shapes).
4. **Tests** it must add, by what they prove.
5. **Docs in the same PR**: the ARCHITECTURE / ENGINEERING / DECISIONS /
   plan / register lines it changes.
6. **Commits and PR.** Small commits; every commit message ends with the
   attribution lines your system prompt gives you. Push, `gh pr create`
   (not draft) with the ids in the title and the PR body ending with the
   attribution your system prompt gives. Then run the code-review skill
   on the PR (`Skill`, skill `code-review`, args `<PR number> high`), fix
   confirmed findings in its own diff, push. **Never merge.**
7. **Report back**: PR URL, what changed, tests by name, review findings
   and what it did with each, and any deviation from the plan for an
   "As built" section.

While they run:

- A review finding that lands in a *stacked* branch's code belongs to the
  agent that owns that branch: relay it with SendMessage to that agent
  (it resumes with its context) rather than fixing it yourself.
- Keep a `plan-13-integration` branch: every open WP branch merged in
  stacking order, the seams between them fixed there (a test that imports
  a name another WP renamed, a docs table row two WPs both edited), and
  the full suite run on it after each merge. Report its test count. Open
  it as one PR against main when the waves are done, and say that merging
  it marks the WP PRs merged. Merging them one by one hits the same
  document-table conflicts.
- Document tables (ARCHITECTURE, ENGINEERING, AUDIT, the plan's decision
  table, the register's answer sheet) conflict constantly. Resolve them
  row by row, three-way: for each row keyed by its first cell, take the
  side that changed it from the merge base; when both changed it, merge
  the two by hand. A small script for this, written to
  `$CLAUDE_JOB_DIR/tmp`, pays for itself on the second merge.

## 7. Harness notes learned the hard way

- In a worktree-isolated session, git commands must be plain and target
  the worktree: no `git -C`, no `for` loops or compound pipelines around
  git, no heredocs piped into `uv run python`. Write a Python script to
  `$CLAUDE_JOB_DIR/tmp` and run it with `uv run python <path>` or
  `python3 <path>` from `hyperspace-python/`.
- `gh pr merge` can fail with "Base branch was modified" right after a
  push; check `git log` on main, and if nothing landed, retry.
- A branch checked out in a subagent's worktree cannot be checked out in
  yours; send the change to that agent instead.
- `uv run` warns about `VIRTUAL_ENV`; it is harmless.

## 8. Rules

- **Nothing here is a redesign.** The control model stands; decided rows
  stand.
- **Merge only when the owner says so**, per PR. The owner's merge answer
  for one PR does not cover the next.
- One PR per work package, not draft, ids in the title, tests for every
  behaviour it changes, pytest and ruff green, docs updated in the same
  PR.
- Every document you touch describes the code as it is after the PR.
- Rebase on main often; another session may be merging presets.

## 9. How to talk to the owner

- **Bottom line first.** After each work package lands: what closed, what
  is waiting on the owner, what is next. A few lines, not a report.
- **One document to decide from.** Every open decision is in
  `docs/DECISION-REGISTER.md`, readable in an IDE, mirrored to the phone
  Doc. Never scatter decisions across chat, plans and PR bodies. If the
  owner asks "what do I need to decide", the answer is that file, current.
- Each decision stands on its own: no audit ids or plan jargon without the
  sentence that explains them, options in a table with their trade-offs,
  one recommendation with its reason.
- Hardware is easier with a picture. When a decision is about the APC40,
  the box or the projector, draw it (the APC40 factory map drawing in the
  phone Doc, under decision 7, is the model).
- Do not ask permission for reversible work that follows from the plan.
  Stop only for the owner's decisions and for merges.
- When the owner is frustrated, act; do not explain the process.

## 10. Done means

- Every plan 13 work package merged on main, by the owner.
- Plan 13's exit criteria (§3) ticked on merged main; its "As built"
  section written.
- DECISIONS rows for plan 13 read "standing"; the register's notes say
  where each answer was built.
- `11-hand-checks.md` group H written and every check grounded in a
  command or a test.
- The two audit rows (§4) filed.
- A final message to the owner: what shipped, what only they can check at
  the machine, in the order to run the checks, and any fork still open.
