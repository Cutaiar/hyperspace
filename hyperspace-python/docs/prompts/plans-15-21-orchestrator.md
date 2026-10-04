# Orchestrator prompt — write and build plans 15 to 21, unattended

Paste everything below the line into a new Claude Code session started in
`/Users/dallman/antigrav_repos/hyperspace`. It is self-contained: it says
what to read, what is decided, how each plan is written and built, how to
run the subagents, and what the owner finds when they come back.

---

You are the orchestrator for **plans 15 to 21** of Hyperspace, in
`/Users/dallman/antigrav_repos/hyperspace`. The Python app is in
`hyperspace-python/` (uv, pytest, ruff). You coordinate; subagents in
their own git worktrees write the plan documents and the code. The work
comes from one night at the machine (Dan and Dillon, 2026-10-03/04): a
long wishlist, read against the code, ordered into seven plans, and
answered by the owner, in `hyperspace-python/docs/plans/15-21-roadmap.md`.
That roadmap is your brief.

**Nobody is watching this run.** The owner (Dan) has answered everything
that could be asked in advance and will not be there to answer more. You
do not stop to ask, to get a plan approved, or to get a merge. You decide,
build, record what you decided where the owner will find it, and go on to
the next thing. Your job ends when all seven plans are on the
`finish-line` branch with tests green, the documents describe the code,
and the owner has one PR to read and one list of checks to run at the
machine.

Two people own this rig. **Dan** is the owner this prompt speaks for.
**Dillon** (GitHub `Cutaiar`) opened draft PR #78 (ghost hands); the owner
has said to finish it as part of this run (§0, plan 21).

## 0. Before anything

- Work in a git worktree (EnterWorktree). Never edit the shared checkout.
- **Never push to, merge into or rebase main.** Everything lands on one
  branch, `finish-line`. The owner merges it to main themselves.
- Confirm main is at or after **fa9b3a1** (plan 14 merged) and that
  `uv run pytest -q` passes (1003 at fa9b3a1) and `uv run ruff check .` is
  clean, both run from `hyperspace-python/`. If main has moved, read the
  new commits first.
- Create `finish-line` from main. If PR #79 (branch `plans-15-21-roadmap`:
  the roadmap, the register rows, this prompt) is not on main, merge that
  branch into `finish-line` first.
- **Merge PR #78's branch** (`claude/ghost-hands-mesh-qq0j00`) into
  `finish-line` next, before any plan. It touches `render.py`, `params.py`,
  `hands/core.py`, `app.py` and the document tables every later plan
  edits, and it is off by default. Get the suite and ruff green on the
  result; fix what the merge breaks. Do not push to Dillon's branch and do
  not merge or close #78 itself: its code reaches main when `finish-line`
  does. If the branch has moved again later in the run, merge it again.
- Open one **draft PR, `finish-line` → main**, straight away. Its body is
  the run's status page (§9). Keep it current; it is how the owner learns
  what happened.
- **Never read from, write to or launch against the owner's real
  `~/Hyperspace`.** It holds presets saved that night that may have no
  backup. You and every subagent run the app and the tests with
  `HYPERSPACE_HOME` set to a temp folder. Any work package that changes a
  file format or moves a file backs up first, as `routing.backup` does,
  and proves it on a copy.

## 1. Read, in this order

1. `hyperspace-python/docs/plans/15-21-roadmap.md`, whole. §1 is the
   constraints, §2 is what the session got wrong about the system (do not
   build those), §3 the order, §4 the scope of each plan, §5 the contracts
   between plans, §6 what is deferred, §7 the owner's answers.
2. `hyperspace-python/docs/ARCHITECTURE.md`. §3 is the control model and
   is canonical: scene-setters write the base, exactly one performer per
   parameter writes an offset through `Router.modulate`, `Registry.apply()`
   lands both once per frame, the render stack only reads; `hands/core.py`,
   `hands/signal.py`, `lfo.py` and `tempo.py` import nothing from the
   package. Nothing in plans 15–21 may break it.
3. `hyperspace-python/docs/DECISIONS.md`, whole. **Do not re-litigate any
   row** except the ones the owner changed on 2026-10-04 (§2 below). The
   ones this work leans on: a preset load replaces everything (D2); module
   presets are labels (D3); the global desk layer is fixed and never
   Learned into (D5); invariant controls mean one thing on both layers
   (D6); an unmapped control is dark and dead (D8); factory presets are
   read-only and a user file shadows one; the render window has no imgui;
   overlay only when the config asks; tap-only tempo; twelve hand axes, no
   gesture vocabularies.
4. `hyperspace-python/docs/DECISION-REGISTER.md`: Part A4 (rows 26 on) and
   the answer sheet. This is where your own decisions go (§5).
5. `hyperspace-python/docs/plans/14-party-rig.md` (the last plan: its
   shape is the shape of the plans you will write, and its §7 "As built"
   says what the code is now) and `13-preset-and-session.md` §2.
6. `hyperspace-python/docs/plans/README.md` "Conventions that apply to
   every plan", including the two worktree traps.
7. `hyperspace-python/docs/ENGINEERING.md` (behaviour; update the sentence
   you change), `docs/plans/11-hand-checks.md` (the owner's machine-side
   list; every plan adds a group to it) and `docs/CHECKPOINT.md`.
8. PR #78's description and diff (`gh pr view 78`, `gh pr diff 78`).

## 2. What is decided (summary; the roadmap is authoritative)

- **The order**: #78 merged in → 15 safety net and the bank → 16 paper
  cuts → 17 Learn, Unbind and seeing the desk, with 18 hand and knob feel
  beside it → 19 presets and the desk layout, with 20 FX, dream and looks
  beside it → 21 outputs and the hands. All seven are in scope.
- **No timetable.** The owner needs the software by Friday 2026-10-09 and
  has said not to plan around dates. Do not cut scope, skip review or
  thin the tests to go faster. If the run ends early for any reason, what
  is on `finish-line` must work and the order above is what got done
  first.
- **"We don't want to drown in the number of parameters."** Every work
  package that adds a param, a menu item or a page states what it replaces
  or why nothing. Reject a design that solves a complaint with a new knob
  when a default, a label or an existing concept would do.
- **Undo reaches single edits** (decision 26). One gesture is one step: a
  slider drag, a knob turn, a typed value, a toggle, a routing edit, or a
  replacing action. It is built without a write hook: a per-frame
  fingerprint of every param's base and of the routing tables, a settle
  time, and a restore that puts back only what differs. Performers write
  offsets, so a moving hand makes no step. Roadmap §4, plan 15 WP1, has
  the whole design. `undo.push(label)` is the contract every later plan
  calls before a replacing action.
- **Home** is the show's "starts on" preset, on the Home key and the
  APC40's OVERDUB button (27). **The crossfader is master dim** on both
  layers, left is black (28).
- **The desk never overwrites a preset** (29, as the owner changed it): a
  hold on the clip-stop row saves the live state as a new preset, named
  from the preset it grew from plus a number, into the next empty bank
  slot. Plain Save on the panel overwrites.
- **Rate-type params under a hand are allowed.** Nothing flags, warns
  about or refuses them.
- **Twenty-four presets on the desk** (plan 19): clip row 1 and clip rows
  4–5, invariant. This extends D6's list of invariant controls, with the
  owner's go-ahead, as do the OVERDUB button and the clip-stop row.
- **The faces are their own effect target** (plan 20): each effect is
  aimed at the frame or at the faces; the faces' effects run into a
  texture the faces show, mapped per face or in screen space.
- **Outputs** (plan 21): the Pepper's Ghost glass and the projector are
  each a render output showing the same frame, each with its own dim and
  its own on/off for the scene and for the hands; the laptop is the
  control view. This replaces the "two windows" decision. **PR #78 is the
  hand HUD**, finished here, with what is drawn swappable for other
  objects.
- **Deferred, do not build**: auto BPM, preset folders, drag-to-map, a
  blackout switch.

## 3. The loop for each plan

Run this for plan 15, then 16, then 17 and 18 together, then 19 and 20
together, then 21.

**a. Write the plan.** One subagent per plan, given the roadmap section,
the contracts in roadmap §5 that touch it, and the instruction to read the
code it names before writing. It produces `docs/plans/NN-<slug>.md` in
plan 14's shape:

- what the owner hit and what it is, each row citing the code (file and
  function) as it stands on `finish-line`;
- the work packages: what, size, the files each owns, the files it must
  not touch, the contracts between packages (names, signatures, file
  shapes);
- what the plan does not change (the DECISIONS rows it leans on);
- exit criteria: headless ones as named tests, machine ones as a new group
  in `11-hand-checks.md` in the existing format (commands, config keys,
  preset, gesture, pass, fail, which code a fail points at, the headless
  test that shows the expected behaviour first);
- every fork it found, each with options, trade-offs and a
  recommendation (§5);
- an empty "As built".

Read the plan yourself before anything is built from it. Check three
things: every claim about existing code is true (open the file), no work
package contradicts a DECISIONS row the owner has not changed, and the
parameter count went up only where the plan says why. Settle its forks
(§5). Commit it to the plan's integration branch and start building.

**b. Build the work packages** with subagents in worktrees (§6), in the
waves the plan gives. Independent packages go out in one message.

**c. Integrate.** Keep `plan-NN-integration`, branched from `finish-line`:
every WP branch merged in stacking order, the seams between them fixed
there, the full suite and ruff run after each merge. Then launch the real
app once against a temp home and drive it past the first frames and
through the plan's new behaviour where a script can reach it (a small
script in `$CLAUDE_JOB_DIR/tmp`; a stubbed test hid a first-frame crash on
main for a week in September). What you saw yourself and what an agent
reported are different things; keep them apart in the status.

**d. Land it.** When the integration branch is green, reviewed and
smoke-launched, merge it into `finish-line` with a merge commit (in plan
15, one merge commit per feature), push, and update the status page.
Then start the next plan from the new `finish-line`.

**e. Close the plan.** In the same push or the next: the plan's "As
built" (what differs from the plan and why), DECISIONS rows for what was
decided, the register's notes saying where each answer was built,
CHECKPOINT's pick-up list, the plans README row.

## 4. The plans, in one table

The roadmap §4 has the scope. This is only what you need to schedule.

| Plan | Packages (roadmap §4) | Runs |
|---|---|---|
| 15 Safety net and the bank | WP1 undo and the trash; WP2 home; WP3 master dim; WP4 save-as on the desk, "put preset here" | WP1 and WP3 at once; WP2 and WP4 stack on WP1 |
| 16 Paper cuts | cheat sheet off; FX chip selects, selection by name; an off effect says so; window placement; instances to 0 and three drifts | all at once (distinct files; the two that touch `ui_fx.py` stack) |
| 17 Learn, Unbind, the desk | one Unbind; Learn desk / Learn hand left / right; Learn where it is missing; the big clickable desk; a ROUTING filter | Unbind and Learn first, the desk view after |
| 18 Hand and knob feel | an interaction box; a learn's default op and depth; knob smoothing; the two-hand orbit as a preset | beside 17; the learn-default package after 17's Learn package is on its integration branch |
| 19 Presets and the desk layout | twenty-four slots; the factory preset layer re-cut; hide and rename; the dirty dot and save labels; the trash view; the home in git | the slots first (it is the large one and the others read the bank's size); beside 20 |
| 20 FX, dream, looks | the faces as an effect target; the chain view; ECHOES and DREAM as two sections; one dream "speed"; instance layouts | the face target first; beside 19 |
| 21 Outputs and the hands | the output list with per-output scene, hands and dim; #78 reviewed and finished; `ghost.style` and the other things to draw | outputs and the #78 review at once; styles after the review |

Keep at most four build subagents running at once. When two plans run
side by side they share the document tables; give each plan's docs edits
to one package (its last) so the tables conflict once, not six times.

## 5. Forks: you decide, and you write it down

A fork is anything that would change what a performer feels at the desk
or the box, add a concept the owner has to learn, or choose between
designs with real trade-offs. The owner's instruction for this run: take
your recommendation, build it, and log it for them to confirm or
overturn. So for each fork:

- choose the option that is cheapest to reverse among those that honour
  the roadmap's constraints, and prefer the one that adds the fewest
  things to learn;
- add an entry to `docs/DECISION-REGISTER.md` Part A4 in the shape of the
  rows already there (what it is, what the code did, the options in a
  table with the trade-off per option, what you chose and why, the cost
  to reverse) and a row to the answer sheet reading "built on the
  recommendation; confirm or overturn";
- add a dated row to DECISIONS.md marked as built on a recommendation;
- list it on the status page under "Decided for you".

A decision about the APC40, the box or the outputs comes with a drawing
(the clip-stop sketch under decision 29 is the model).

Three things you may not decide, because they are not reversible or not
yours: anything that breaks the control model in ARCHITECTURE §3 or a
boundary test; anything that rewrites or deletes a user's files without a
backup; anything outside the roadmap's scope. If a work package cannot be
built without one of these, do not build that package: write down exactly
what blocks it under "Parked" on the status page, and go on.

## 6. Running the subagents

Use the Agent tool with `isolation: "worktree"` for each work package,
several in one message when they are independent. A subagent knows only
what its prompt says. Each prompt is self-contained and includes, in this
order:

1. **Setup.** `git fetch origin && git checkout -B plan-NN-wpK-<slug>
   origin/<the branch it stacks on>`, then `git merge` of each dependency
   branch, and a `grep -c` check that the features it needs exist; stop
   and report if not. Then, from `hyperspace-python/`, `uv run pytest -q`
   and `uv run ruff check .` green before any edit. `HYPERSPACE_HOME` set
   to a temp folder for every run of the app.
2. **What it builds and why**: the row from the plan, the finding from
   the session it answers, the decisions it implements quoted by number
   with the chosen option, the files it owns and the files it must not
   touch.
3. **Behaviour to build**, precise enough that the agent needs nothing
   else; the contracts with sibling packages (names, signatures, file
   shapes); the DECISIONS rows it must not break, quoted.
4. **Tests** it must add, by what they prove. A UI change has a test that
   the page still fits the control window (`test_ui_shell.py` holds "no
   page scrolls").
5. **Docs in the same PR**: the ARCHITECTURE / ENGINEERING / DECISIONS /
   plan / hand-check lines it changes; the cheat sheet when a key row
   changes (a test holds the sheet to the tables).
6. **The demo.** A screenshot from an offscreen render or of the panel, or
   a headless script and its output, showing the behaviour, committed
   under `docs/plans/assets/NN-<slug>/` and shown in the PR body. The
   owner judges a package by its demo first.
7. **Commits and PR.** A few commits, each one a step that stands on its
   own (not one per file, not one for everything); every commit message
   ends with the attribution lines the agent's system prompt gives. Push,
   `gh pr create` against the plan's integration branch (not draft) with
   the plan and package in the title and the body ending with the
   attribution its system prompt gives. Then run the code-review skill on
   the PR (`Skill`, skill `code-review`, args `<PR number> high`), fix
   confirmed findings in its own diff, push. It does not merge.
8. **No questions.** Nobody can answer one. If the agent meets a fork, it
   takes the option cheapest to reverse, builds it, and reports the fork
   with its options so you can log it (§5).
9. **Report back**: PR URL, what changed, tests by name, the demo's path,
   review findings and what it did with each, any deviation from the plan
   for "As built", forks it settled, and anything it saw that belongs to
   another package. It says plainly what it did not verify.

While they run:

- A subagent's report describes its own branch. Re-run the suite on the
  integration branch before you record anything as working.
- You merge a WP's PR into its integration branch yourself once its
  review findings are dealt with and the suite is green there.
- A review finding that lands in a stacked branch's code belongs to the
  agent that owns that branch: relay it with SendMessage rather than
  fixing it yourself.
- **When a package will not come right**: one more attempt with a fresh
  agent and a prompt that says what the first got wrong. If that fails
  too, leave the package off the integration branch, record it under
  "Parked" with what was tried and what it blocks, and build everything
  that does not depend on it. A parked package never holds a plan.
- Document tables (ARCHITECTURE, ENGINEERING, the register's answer sheet,
  the hand checks, the plans README) conflict constantly. Resolve them row
  by row, three-way: for each row keyed by its first cell, take the side
  that changed it from the merge base; when both changed it, merge the two
  by hand.

## 7. Harness notes learned the hard way

- In a worktree-isolated session, git commands must be plain and target
  the worktree: no `git -C`, no `cd … &&` in front of git, no `for` loops
  or compound pipelines around git, no heredocs. Write a script to
  `$CLAUDE_JOB_DIR/tmp` with the Write tool and run it with
  `uv run python <path>` or `python3 <path>` from `hyperspace-python/`.
- A branch checked out in a subagent's worktree cannot be checked out in
  yours; send the change to that agent instead.
- `uv run` warns about `VIRTUAL_ENV`; it is harmless.
- The dream needs torch (an ordinary dependency since plan 14); a test
  run that skips eleven tests has no torch and is not the full suite.
- This run is long and your context will be summarised along the way.
  The status page, the plan documents' "As built" sections and the
  register are your memory: write to them as you go, and re-read the
  status page and roadmap §3–§5 whenever you are unsure where you are.
- You cannot see the rig. Nothing you build is verified on the APC40, the
  Leap, the projector or the glass until the owner runs the hand checks.
  Say so wherever you report a result; never write "works" for something
  only a test or an offscreen render has shown.

## 8. Rules

- Main is never touched. `finish-line` is the only branch that
  accumulates; nothing merges into it that is not green, reviewed and
  smoke-launched.
- Nothing here is a redesign. The control model stands; decided rows
  stand, except where the owner changed them on 2026-10-04.
- One PR per work package, with its demo, tests for every behaviour it
  changes, pytest and ruff green, docs updated in the same PR.
- Every document you touch describes the code as it is after the PR.
- No new parameter, menu item or page without the sentence that says what
  it replaces or why nothing.
- The owner's `~/Hyperspace` is never touched.
- You do not stop to ask. You decide, record, and continue.

## 9. The status page

The body of the draft PR `finish-line` → main, rewritten after every plan
lands and whenever something is parked. The owner reads this and nothing
else first, possibly on a phone, with no memory of this prompt. In this
order:

1. **Where it stands**, in two or three sentences: which plans are on
   `finish-line`, the test count you saw yourself, what is running now.
2. **To try it**: the commands to check out `finish-line` and launch,
   and the reminder to copy `~/Hyperspace` first.
3. **What each plan delivers**, one line per work package in the words
   of someone who was at the machine ("Ctrl+Z takes back one slider
   move"), with a link to its demo.
4. **Decided for you**: each fork you settled, one line, with its
   register row. These are the things to confirm or overturn.
5. **Parked**: anything not built, what blocks it, what it would take.
6. **Checks only you can run**: the new hand-check groups, in the order
   to run them, each device plugged in once.

If the Claude Docs tools are available, also mirror new register entries
into the owner's phone copy of the register,
https://claude.ai/code/artifact/d24a5ece-f873-4020-838a-53d5a0ba3571
(read it first; the file stays the canonical copy).

## 10. Done means

- Plans 15–21 on `finish-line`, each with its "As built", or parked with
  the reason on the status page.
- The suite and ruff green on `finish-line`, run by you at the end; the
  real app launched from it against a temp home.
- Every fork you settled is in the register and on the status page.
- `11-hand-checks.md` carries one new group per plan, every check
  grounded in a command or a test.
- CHECKPOINT and the plans README describe `finish-line`.
- The status page is current and the draft PR is marked ready for review.
  You do not merge it.
