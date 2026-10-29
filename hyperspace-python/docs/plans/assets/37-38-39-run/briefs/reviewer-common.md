# Reviewer brief — plans 37, 38 and 39 (every reviewer reads this first)

You are reviewing one task's PR in Cutaiar/hyperspace (the Python app
under `hyperspace-python/`): first whether it matches its requirements,
then whether it is well built. This is a task-scoped gate; a plan-level
review happens later on the plan branch.

Your review is **read-only**: do not change the working tree, the index,
HEAD or any branch. Do not dispatch sub-agents. Do not re-run the full
suite (the implementer's report carries its evidence); run a focused test
only when reading the code raises a specific doubt, and only from the
worktree your dispatch points at.

## Inputs (paths in your dispatch)
- The task's requirements: its brief (`briefs/<task>.md`), the common
  brief (`briefs/common.md`), the plan's spec and build plan sections the
  brief names, and `docs/plans/37-38-39-orchestrator-prompt.md` (the rules
  and the file-ownership table).
- The implementer's report and decisions file.
- The diff: `git diff <base>...<head>` in the worktree you are pointed at
  (the dispatch gives both SHAs). Read it once; it is your view of the
  change. Inspect code outside it only to judge a concrete risk you can
  name, one focused check per risk, and say what you checked.

Treat the report as unverified claims and verify them against the diff.

## The binding constraints
- **The graph on GRAPH is the whole truth**: no default graph, no hidden
  edge, no auto layout, nothing filled in at load; a hold never fills in a
  wire; a thumbnail or a worker's shortcut changes where something is
  read, never what is wired.
- **Alpha is not a mask**: a mask travels on `mask` wires or through plan
  39's one-way promotion; no node writes a mask into a picture's alpha
  except `cut` and `segment.fg`/`.bg`.
- **No golden re-recorded**; new fixtures add goldens; the frame-signature
  fixture gains cases, loses none. **No preset edited** under
  `hyperspace/library/`. Never touches `~/Hyperspace` or the Drive library.
- The ownership table: the task touched only its stream's files, and
  another stream's only in the way the table allows, and said so.
- `graph.py` imports only the render stack; `masks.py` is a leaf;
  `import hyperspace.app` imports no `torch`/`Vision`/`objc`; the render
  stack never writes a param; every new param defaults to today's picture.
- Every choice the task took itself is a register-row draft in its
  decisions file, with a hand-check draft where a person must judge it.
- No doc the docs tasks own was edited (DECISIONS, DECISION-REGISTER,
  11-hand-checks, TESTING-GUIDE, ARCHITECTURE.*, CHECKPOINT, plans/README,
  plans/3*.md) except where the brief allows.

## The review pass's eye
A texture read while still written; a per-frame cost paid for a node
nobody looks at; a worker thread that blocks the frame or outlives its
node; an error from a backend or a camera that escapes as an exception
instead of words on the node; a mask sampled upside down; a held copy
that reaches for a default; an undo step that is not one step; a test
that asserts nothing; a golden that moved; a preset edited; a boundary
test weakened.

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
