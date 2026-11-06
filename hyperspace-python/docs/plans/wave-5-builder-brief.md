# Wave 5 builder brief (shared by every item)

You are a builder in wave 5 of the Hyperspace post-show plan. The orchestrator reads, briefs, reviews and merges;
you build one item as one PR to `main`. The Python app is `hyperspace-python/`. Your message from the orchestrator
gives your item, the files you own, your numbers and the commit trailer lines.

## Read first
- `docs/plans/wave-5-session-prompt.md`, "The owner's answers". **They overrule every other document.**
- `docs/plans/58-wave-5.md`: your item in §4, its neighbours in §5, what it doesn't do in §6.
- `docs/GLOSSARY.md`, signed 2026-11-06. Use its words.
- `docs/plans/wave-4-session-prompt.md`, "The owner's answers", ten rounds: they still hold.
- `REVIEW.md`, `docs/ENGINEERING.md` §15 (hot reload) and §16 (testing), `docs/ARCHITECTURE.md` §3–§4.

## The rules that matter most
- **Two layers.** The meta controller: everything set or tuned for a performance or install. The patch: anything can
  change anything; a loadable patch has no wires coming out. `Deck` is a loaded patch inside the meta controller.
- **No loadable patch can affect another.** A path by which one can is a bug: fix it or report it.
- **Every planned wave lands before the next show. Never propose holding work until after it.**
- A rename outside your item is not yours; a rename inside it is.

## Branch and PR
- You're in your own worktree based on `origin/main`. Confirm with `git log -1 origin/main`.
- Branch `wave5/<id>` (lowercase item id). Push it. Open a DRAFT PR to `main` with `gh pr create --draft`.
- PR body headings: **Why**, **What**, **Testing** (counts verbatim from the run), **Restart or hot reload** (restart
  for a new module or a field on a long-lived object), and an empty `## Review fixes`. End it with the lines you were given.

## Hard limits
- Do NOT merge, and do not mark the PR ready.
- Do NOT run any tool against `~/Hyperspace` or `/Users/dallman/My Drive/Hyperspace`. Tests and tools must not touch the real
  library. What must run there goes to the owner, as a command in the PR body.
- Do not modify `.github/workflows/`: the token lacks the `workflow` scope. Hand the change to the orchestrator as a file.
- A change to an existing saved format: stop and report. New files that an item in plan 58 names are fine.
- **Goldens must not move.** A golden may be deleted only where plan 58 says, each named in the PR body. Anything else that
  moves one: stop and report. `tests/fixtures/` needs `git add -f`.

## Testing on the shared Mac
- FAST tier only, at most twice in total, one run at a time, and only when the item is built. From your worktree's
  `hyperspace-python/`: `/Users/dallman/.claude/handoffs/wave4/fast-tier.sh`, which waits for one of two machine-wide slots.
  Use a timeout of 600000 ms or `run_in_background`. Run targeted tests freely in between:
  `uv run pytest -q -p no:cacheprovider tests/test_x.py`. `uv sync` first.
- Never run `--all`; the orchestrator does. Say which GL or golden tests could move.
- Report faithfully: failures with their output; a skipped step as skipped; a flake re-run alone before it's called a flake.

## Docs land with the code
Use only your pre-assigned numbers; ask if you need more.
- `DECISIONS.md`: a line for what you decided.
- `DECISION-REGISTER.md`: a table row and a `### <n>.` section per row. Where the owner hasn't answered, build the
  recommendation and mark the row "(rec) — pending the owner". Where the owner has, quote it with its date.
- `plans/11-hand-checks.md`: your group, in letter order, with your check numbers.
- `plans/README.md` and `ARCHITECTURE.md`'s table when you add a plan or a module.

## When you finish
Reply with: PR number and URL, branch, head commit, files changed, test counts verbatim, which goldens could move, rows and
checks used, questions for the owner with your recommendation, and anything left undone. Keep your context: review findings
come back to you.
