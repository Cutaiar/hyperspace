# Working in this repository

## Where the truth is

Read these, in this order of authority. When two disagree, the higher one
wins and the lower one is fixed in the same change.

1. **The code and its tests.** What runs is what is true.
2. [`hyperspace-python/docs/ARCHITECTURE.md`](hyperspace-python/docs/ARCHITECTURE.md):
   the parts, who owns what, which modules may import which.
3. [`hyperspace-python/docs/DECISIONS.md`](hyperspace-python/docs/DECISIONS.md):
   the decisions in force.
4. [`hyperspace-python/docs/DEBT.md`](hyperspace-python/docs/DEBT.md): every
   known shortcut, and what doing it properly would take.
5. [`hyperspace-python/docs/CHECKPOINT.md`](hyperspace-python/docs/CHECKPOINT.md)
   "Standing rules", and [`REVIEW.md`](REVIEW.md).

**`hyperspace-python/docs/plans/` is history, not truth.** A plan records
what someone intended at the time; much of it was changed, overturned or
never built. Read a plan to learn *why* something was asked for, never to
learn how the code works now or what you are allowed to do. If a plan and
the code or ARCHITECTURE disagree, the plan is out of date: do not "fix" the
code toward it. The same goes for `DECISION-REGISTER.md`, the `AUDIT-*.md`
records, and CHECKPOINT's narrative sections: check them against the code.

A fact a later agent needs goes into ARCHITECTURE, DECISIONS or DEBT. It
does not go into a plan, a source file, a test or a fixture.

## What code, tests and fixtures may contain

Source, tests and tools describe **what the code is and why it is that
way now**. They are not a log of how it got there.

- **Comments** explain what the code can't say for itself: an invariant, a
  unit, a non-obvious reason, a trap in an API you call. Write them in the
  present tense.
- **Docstrings** may be as long as the contract needs: what it does, what
  it takes and returns, what it guarantees, what it refuses.
- **Test names and test comments** say what behaviour is checked, not which
  plan asked for it.

Never in code, tests, tools or fixtures:

- **Provenance:** plan numbers, work-package ids, decision-register rows,
  PR or issue numbers, dates, "as of", "before plan N", or who asked for
  what. `git log`/`git blame` and `docs/plans/` hold that.
- **Narration to the next agent:** "beware", "future agents", "I had to",
  "for now", "the proper fix would be".
- **Justifying a shortcut.** If you take one, say so in the PR and add an
  entry to `docs/DEBT.md`: what was done, what the proper fix is, and what
  it costs while it stays. Leave at most a one-line pointer at the site:
  `# DEBT: <slug>`. Don't argue for the shortcut in the code.
- **Prose in fixtures.** A fixture is data. If a fixture is large, generate
  it from a tool rather than committing it, or keep it under 256 KB.

`tools/prose_audit.py check` runs in CI as a ratchet. No file may gain
provenance or narration markers, and no fixture may grow past the limit
without being listed. Existing markers are being removed. When you touch a
file, leave it with fewer markers, then run
`python3 tools/prose_audit.py baseline` (from `hyperspace-python/`) to lock
the lower count in. Never raise the baseline to get a change through.
