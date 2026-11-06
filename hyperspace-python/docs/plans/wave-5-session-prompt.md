# Wave 5 of the post-show plan: the opening prompt for the orchestrating session

Paste everything below the line into a fresh Claude Code session opened in
`/Users/dallman/antigrav_repos/hyperspace`. It is written for the session that orchestrates: the
orchestrator reads, briefs, reviews and merges; builders build. Planned 2026-11-06.

---

You are orchestrating **wave 5** of the Hyperspace post-show plan: the cleanup, the rig's last piece, and
cheaper changes. The plan is `hyperspace-python/docs/plans/58-wave-5.md`. The Python app is
`hyperspace-python/`. Enter a scratch worktree before anything else (EnterWorktree); never run reviews or
checkouts in the owner's checkout.

## First: check that you may start

Stop and tell the owner plainly if any of these is not true. Do not start around them.

1. **Wave 4 is merged:** SEM, D5e, N1, N2, D6, #287's content (rewritten by us, so the original PR may close unmerged), #365, NSEW, the one migration. Check with
   `git log` and `gh pr list`. If not, wave 4's remainder comes first, by `docs/plans/wave-4-session-prompt.md`
   and the handoff at `~/.claude/handoffs/wave4/HANDOFF.md`. Say so and ask whether to finish it.
2. **The owner says they ran the migration, and that both Macs have opened the new library.** Only the owner
   can say this, so ask. They coordinate the other Mac. Stage 1 removes the code that reads old files;
   this is the one gate you must never assume.

H1, H2 and SM1 need none of this.

## Read first, in this order

1. **"The owner's answers" below: they overrule every other document.**
2. `docs/plans/58-wave-5.md`, all of it.
3. `docs/GLOSSARY.md`, signed 2026-11-06. New code uses its words. After SEM, the code does too.
4. `docs/plans/wave-4-session-prompt.md`: "The owner's answers" (ten rounds), which still hold, and "Lessons
   from wave 3".
5. `docs/plans/57-format-lane.md` for what the migration did. `REVIEW.md`, `docs/ENGINEERING.md` §15–§16,
   `docs/ARCHITECTURE.md` §3–§4.
6. Your memory: `wave-4-run`, `wave-5-plan`, `all-waves-before-show`, `no-old-schema-support`.

## The owner's concept, in brief

- **Two layers only.** The **meta controller** is everything set or tuned for a performance or install. The
  **patch** is where anything can change anything; a **loadable patch** has no wires coming out. `Deck` is a
  loaded patch inside the meta controller; exactly two, on air and off air.
- **Absolute: no loadable patch can affect another.** Any path that does is a bug. A patch wired into its host
  drives it; that is what its wires are for.
- **Every planned wave lands before the next show. The owner will not change their mind; never propose holding
  work for after it, and don't re-raise show timing.**
- The owner judges recommendations quickly: give a recommendation with each question, and accept "as
  recommended". Be plain and short with them, and use no project jargon in a question.

## The owner's answers

Given 2026-11-06. These overrule every other document.

- **Screens:** "It needs to be extremely easy for us to just quickly set up the screens for the thing that we're doing. I
  don't think we need a whole configuration layer called venues for it." The output tab "shouldn't be a dropdown. Each
  connected display should get its own row there, and you should be able to choose what targets that display, like the
  control window or any of our renders."
- **"Share the screen memory between Macs. We want to make this thing as interoperable as possible."**
- **Hot-plug is required:** if a display "gets accidentally unplugged and then plugged back in, we cannot restart the app in
  order to pick up that change. It has to be hot-pluggable."
- **A new controller** waits until it is dragged to a player.
- **Video sound** reaching the off-air look through the analyzer is accepted; say so on the toggle.
- **Old files:** the reader goes only once the owner says both Macs have opened the new library. They coordinate that.
- **Trash:** "Just delete the trash items." Done in the migration, not converted.
- **Scope is right:** no new looks or controllers. **`dkit` is orthogonal:** "we don't need to worry about that", so no UI
  preparation in this wave.
- **Merge on green holds** for this wave.

- **A display has one target, and a target may go to several displays.**
- **Rows pending the owner were bulk accepted,** and marked so. All 17 face patterns stay; SEND B stays FINE; creating a pair
  over an existing mapping asks (wave 4).

## Synopsis

Delete what only existed to read old files. Close the last ways one look reaches another. Give every display its own row,
remembered by name and shared by both Macs, surviving an unplug with no restart. Set up controllers in the app. Stop doc
conflicts, and stop the type errors growing.

## The work

`58-wave-5.md` §4 has every item, with its files, size, dependency and proof, and §5 the schedule:

| Stage | Items |
| --- | --- |
| Any time | H1, H2, SM1 |
| 1 | CL2, alone among anything touching tests' builders; beside it LY1, LY2, SC1, SM2, SM3 |
| 2 | CL1, once the owner's dry run is clean; then CL3 and CL4 together; TY1, TY2; SM4 |
| 2b | SC3a, alone on the render loop, after a short spike. If the spike fails, stop and tell the owner |
| 3 | SC2, CT1, LY3, SM5 |
| 4 | SC3b, then RT1 only after SC3b's hand check with a real unplug |
| 5 | TY3, then TY4 |

**Numbers:** plan 58 is this; rows from 770, checks from 600, groups from DA. Pre-assign each item's block when
you brief it, as parallel builders collide. If wave 4's remainder ran past those, take the next free.

**Where the plan may be wrong:** it was read before wave 4's remainder landed. Before stage 1, spend one
read-only agent on re-reading §4's file and line references against `main`. SEM renames most of them. Correct the
plan in the same PR as the first item, and tell the owner only what changes scope.

## How to run it

- **One builder per item,** on Opus (`model: "opus"`), `isolation: "worktree"`, `run_in_background: true`. Give
  each the shared brief, `docs/plans/wave-5-builder-brief.md`, and its item, the files it owns, its numbers and **this
  session's commit trailer lines**. Do not use Fable for builders.
- **Every PR gets an independent review** before its merge: `/code-review medium <PR>` from your scratch worktree,
  one at a time, findings sent to the same builder. A `low` second pass when fixes were large; a third when the
  second found real bugs. Reviewers are sometimes wrong; builders verify, and a disproved finding gets a test, not
  a change.
- **A review that returns nothing is not a pass.** On 2026-11-06 a run came back empty in four seconds with one tool
  call; the replacement found four real problems. Check it read the diff. If not, brief an independent agent with
  an explicit list.
- **Testing:** builders run the fast tier only, through `~/.claude/handoffs/wave4/fast-tier.sh` (two machine-wide
  slots), or let CI be their last check once H2 lands. You run `--all` serially, `fast-tier.sh --all -rs`, on a PR's
  head before merging anything that touches the render path, the loader or `graphmigrate`. **Goldens must not move
  anywhere in this wave.** A golden that moves is a bug, or a stop-and-ask.
- **A keeper agent** in its own worktree does each queue step, as in wave 4, until H1 lands. After H1, doc tails
  merge on their own in a local merge only: GitHub's server doesn't honour the attribute (retested 2026-11-06,
  plan 58 §3), so a PR showing doc conflicts still needs main merged locally and pushed, which union then
  resolves with no hand work. Keep `tools/sort_register.py`.
- **Merging:** the owner authorised merging on green for wave 5, but for CL1, which waits for their dry run, and RT1, which waits for the unplug. `main` has no required checks, so `--auto` merges at once: wait first with
  `~/.claude/handoffs/wave4/wait-green.sh <pr> <head>`, or its replacement from H2, then call `gh pr ready` and `gh pr merge <pr>
  --squash --delete-branch --body-file <file>` directly, with the review and test counts and the trailer lines in the
  body. A wrapper around `gh pr merge` gets refused. If `gh` then errors that `main` is used by a worktree, the merge
  still happened: check with `gh pr view`, and delete the remote branch.
- **Keep git commands plain:** a worktree-isolated session refuses compound commands that mix `cd` or variables with
  git. Run them singly.
- **Don't run tools against `~/Hyperspace` or `/Users/dallman/My Drive/Hyperspace`,** except read-only counts. The
  owner runs migrations and the dry run in CL1. `.github/workflows/` needs the owner's token, so TY1's CI step goes to
  them as a file to apply.
- **A red run twice on one head isn't a flake, and a green run isn't a fix.** Report failures with their output, and
  skipped steps as skipped.

## Reporting

Nothing in wave 4 had been tried on real hardware when this was written, and CL1 is the point of no return for
old files. SC3b can only be proved by unplugging a real display, so nothing about hot-plug is done until that has happened. Say what's been tried at the machine whenever it matters. CL1's PR body must say in its first line
that old files stop opening, and what to do if a Mac hasn't updated.

**In your first status message to the owner,** ask for the per-face render check (`58-wave-5.md` §4), and list §8's "Assumed unless the owner objects", so they can object.

## After the last merge

Both Macs pull, `uv sync` and restart. List the wave's hand checks. Then write up what comes next and stop: don't
plan further without the owner.
