# Reviewer brief — plan 40, patches (every reviewer reads this first)

You are reviewing one task's PR in Cutaiar/hyperspace (the Python app
under `hyperspace-python/`): first whether it matches its requirements,
then whether it is well built. This is a task-scoped gate; a plan-level
review of `plan-40-build` against `main` happens after T5.

Your review is **read-only**: do not change the working tree, the index,
HEAD or any branch. Do not dispatch sub-agents. Do not re-run the full
suite (the implementer's report carries its evidence); run a focused test
only when reading the code raises a specific doubt, and only from the
worktree your dispatch points at.

## Inputs (paths in your dispatch)
- The task's requirements: its brief (`briefs/t<n>.md`), the common brief
  (`briefs/common.md`), the spec `docs/plans/40-patches.md` (the P-section
  and the decisions the brief names — **every decision D1–D10 is the
  owner's; the "the owner" column is the requirement**, not the
  recommendation) and `docs/plans/40-patches-build.md` ("Global
  constraints" and the task).
- The implementer's report and decisions file.
- The diff: `git diff <base>...<head>` in the worktree you are pointed at
  (the dispatch gives both SHAs). Read it once; it is your view of the
  change. Inspect code outside it only to judge a concrete risk you can
  name, one focused check per risk, and say what you checked.

Treat the report as unverified claims and verify them against the diff.

## The binding constraints
- **The graph on GRAPH is the whole truth** (plan 36): no default graph,
  no hidden edge, no auto layout, nothing filled in at load; a spawn
  attaches nothing by itself (D2); a patch's layout is its own, placed at
  the click. **The one exception is D4**: a collapsed group folds its
  internal cables until `+`. Nothing else may hide a cable.
- **The renderer learns nothing**: `graph.build_graph`, `graph.signature`,
  `render.py` and the goldens see the flat graph; **no golden
  re-recorded**; `tests/fixtures/frame-signatures.json` not re-recorded.
- **Through the doors**: every write to the table, the banks, the graph
  section and the values goes through the calls that exist; no new write
  path onto a `Param` or the table; a spawn, a group, an ungroup, a "wire
  as saved" each **one undo step**.
- **No file written by a spawn**; a patch save writes
  `<library>/patches/<slug>.json` and nothing else; `bindings.json` never
  touched. **Dylan's files untouched**: `apc40.py`, `midi.py`,
  `bindings.default.json`, the desk diagram, `ui_desk*.py`. **No preset
  edited** under `hyperspace/library/` (T5's six fx files removed is the
  one sanctioned change). Never touches `~/Hyperspace` or the Drive
  library.
- New modules are leaves (`patches.py` imports nothing from the app);
  `graph.py` imports only the render stack; `import hyperspace.app`
  imports no `torch`; the render stack never writes a param; every new
  param defaults to today's picture.
- The brief's file list: the task touched only the files it owns, and
  another's only in the way the brief allows, and said so.
- Every choice the task took itself is a register-row draft in its
  decisions file, with a hand-check draft where a person must judge it.
- No doc the docs task owns was edited (DECISIONS, DECISION-REGISTER,
  11-hand-checks, TESTING-GUIDE, ARCHITECTURE.*, ENGINEERING, SETUP,
  CHECKPOINT, plans/README, plans/40-*.md) except where the brief allows
  (T0's symbol sed).

## The review pass's eye
An id renamed in one place and not another (values, wires, routes, desk
rows, modifier inputs, subscribers, layout); a rename map that collides
(`acid.2` taken by the host's own second acid); a boundary cable
classified by a closed list of schemes; a port whose `was` is attached
automatically; a conflict missed (a desk control the host maps under a
`@role` qualifier; a hand axis that already owns another param); an undo
step that is two; a file written by a spawn; a test that asserts nothing
or that re-derives the answer from the code under test; a golden that
moved; a preset edited; a boundary test weakened; a per-frame cost paid
on the head for a chip nobody needs; a registry hook that fires every
frame; a listener fired per device instead of once per frame.

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
