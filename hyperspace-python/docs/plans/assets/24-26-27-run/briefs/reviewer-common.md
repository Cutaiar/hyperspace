# Reviewer brief — plans 24, 26 and 27 (every reviewer reads this first)

You are reviewing one work package's PR in Cutaiar/hyperspace (the Python
app under `hyperspace-python/`): first whether it matches its requirements,
then whether it is well built. This is a task-scoped gate; a whole-branch
review happens later on the integration branch.

Your review is **read-only**: do not change the working tree, the index,
HEAD or any branch. Do not dispatch sub-agents. Do not re-run the full
suite (the implementer's report carries its evidence); run a focused test
only when reading the code raises a specific doubt.

## Inputs (paths in your dispatch)
- The WP's requirements: the named line ranges of
  `hyperspace-python/docs/plans/24-26-27-orchestrator-prompt.md` in the
  worktree you are pointed at, plus `briefs/common.md` (the rules every WP
  works under).
- The implementer's report and decisions file.
- The diff package (commit list, stat, full diff with context). Read it
  once; it is your view of the change. Inspect code outside it only to
  judge a concrete risk you can name, one focused check per risk, and say
  what you checked.

Treat the report as unverified claims and verify them against the diff.

## The binding constraints (from the prompt's gates and decisions)
- Never touches `~/Hyperspace` or `~/My Drive/Hyperspace`; every script
  and test uses a scratch `HYPERSPACE_HOME`.
- `hyperspace/library/` byte-identical; proofs via `tests/fixtures/` +
  a scratch library; fixtures force-added.
- Every new param defaults to today's picture; nothing authors a look.
- The render stack never writes a param; adapters only `feed`;
  `Router.modulate` is the only caller of `Param.modulate`; the hands
  package stays liftable; the core never imports `midi`, `bridge`,
  `dream`, `osc`, `torch`, `leap`; no node method named `apply`.
- The boundary tests named at prompt lines 1177–1245 pass untouched
  except the exact changes the prompt allows for this WP, each named in
  the PR body with its reason.
- The 24 owner decisions (prompt 975–1072) are built as written; every
  other choice the WP took is written as a register-row draft in its
  decisions file, with a hand-check draft where a person must judge it.
- No doc the docs WPs own was edited (DECISIONS, DECISION-REGISTER,
  11-hand-checks, TESTING-GUIDE, ARCHITECTURE.*, CHECKPOINT, plans/README,
  plans/2*.md) except where the WP section allows.

## Output (your final message is the report; no preamble)
### Spec compliance
✅ compliant | ❌ issues (missing / extra / misunderstood, with file:line)
⚠️ cannot verify from diff: …
### Strengths
### Issues
#### Critical (must fix)  #### Important (should fix)  #### Minor
Each: file:line, what is wrong, why it matters, the fix if not obvious.
Important = cannot be trusted until fixed (wrong or fragile behaviour, a
missed requirement, swallowed errors, tests asserting nothing, verbatim
duplication). Polish is Minor.
### Assessment
**Task quality:** Approved | Needs fixes — with one or two sentences why.
