# Reviewer brief — plans 28 and 30 (every reviewer reads this first)

You are reviewing one work package's PR in Cutaiar/hyperspace (the Python
app under `hyperspace-python/`): first whether it matches its requirements,
then whether it is well built. This is a task-scoped gate; a whole-branch
review happens later on the integration branch.

Your review is **read-only**: do not change the working tree, the index,
HEAD or any branch. Do not dispatch sub-agents. Do not re-run the full
suite (the implementer's report carries its evidence); run a focused test
only when reading the code raises a specific doubt, and only from the
worktree your dispatch points at.

## Inputs (paths in your dispatch)
- The WP's requirements: the named line ranges of
  `hyperspace-python/docs/plans/28-30-orchestrator-prompt.md` in the
  worktree you are pointed at, the matching design file
  (`docs/plans/30-shader-nodes.md` or `28-node-editor.md`), plus
  `briefs/common.md` (the rules every WP works under).
- The implementer's report and decisions file.
- The diff package (commit list, stat, full diff with context). Read it
  once; it is your view of the change. Inspect code outside it only to
  judge a concrete risk you can name, one focused check per risk, and say
  what you checked.

Treat the report as unverified claims and verify them against the diff.

## The binding constraints (from the prompt's gates and decisions)
- Never touches `~/Hyperspace` or `~/My Drive/Hyperspace`; every script
  and test uses a scratch `HYPERSPACE_HOME`.
- `hyperspace/library/` byte-identical; `apc40.py` and `midi.py`
  untouched; proofs via `tests/fixtures/` + a scratch library; fixtures
  force-added.
- **No golden hash re-recorded.** Only D1 and N4 add frames (their
  fixtures'); the 556 base hashes are unchanged in `frames.json`.
- Every new param defaults to today's picture; nothing authors a look.
- The render stack never writes a param; adapters only `feed`;
  `Router.modulate` is the only caller of `Param.modulate`; `Param.apply`
  is called by `Registry.apply` and (N0 on) `Router.modulate` under the
  frame mark, nowhere else; `graph.py` imports no `params`/`routing`/
  `library`/`preset`/`undo`/`control`/`devices`; `patch.py` and
  `modifiers.py` are leaves (only `motion`, `tapers`); the hands package
  stays liftable; the core never imports `midi`, `bridge`, `dream`,
  `osc`, `torch`, `leap`; no node method named `apply`.
- The boundary tests named at prompt lines 840–900 pass untouched except
  the exact changes the prompt allows for this WP, each named in the PR
  body with its decision number.
- The sixteen owner decisions (prompt 673–723) are built as written;
  every other choice the WP took is written as a register-row draft in
  its decisions file, with a hand-check draft where a person must judge it.
- No doc the docs WPs own was edited (DECISIONS, DECISION-REGISTER,
  11-hand-checks, TESTING-GUIDE, ARCHITECTURE.*, CHECKPOINT, plans/README,
  plans/2*.md, plans/3*.md) except where the WP section allows (N0:
  ARCHITECTURE §2's lag rule drafted).

## The review pass's eye (look for these in every WP where they can occur)
A param applied twice in a frame; an LFO stepping twice or not at all; a
modifier reaching `bindings.json` or a session row the preset; a cycle the
sorter misses or a `delay` it refuses; an off effect costing a pass or one
effect run twice for two consumers; a placed effect's texture reused while
still read; a wire into one output changing another or a preset load
writing the session's switches; the node editor's context leaking across
a hot reload or ⌘R; a pre-run preset or `bindings.json` loading with a
note or dirt.

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
