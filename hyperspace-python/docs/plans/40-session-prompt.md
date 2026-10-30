# Plan 40 — patches (session prompt)

You are the controller for plan 40 in `Cutaiar/hyperspace` (the Python
app under `hyperspace-python/`): **patches** — a group of nodes and its
boundary, saved once, spawned anywhere. The spec is
[`40-patches.md`](40-patches.md) (agreed 2026-10-27; **every decision
D1–D10 is the owner's**, in the "the owner" column — build those, not the
recommendations where they differ: D3 the conflict sheet, D4 the folded
group, D6 no conversion, D10 the FX page stays). The build plan is
[`40-patches-build.md`](40-patches-build.md): seven tasks, T0–T6, with
their tests and proofs. Work the way plans 37–39 were worked
([`37-38-39-orchestrator-prompt.md`](37-38-39-orchestrator-prompt.md) is
the model): one sub-agent per task in its own git worktree off a verified
base, a review pass, a docs task last. The owner merges the final PR.

**Read first, in full:** the spec, the build plan, `docs/CHECKPOINT.md`,
`ARCHITECTURE.md` (§2 the render graph, §3 the control model — 3.3 to
3.8 above all, the registry, one performer per param, the binding file),
`DECISIONS.md` ("Presets and the desk", "Undo"), `36-wysiwyg-graph.md`
(the rule), `28-node-editor.md` (the canvas, the template node, which
is the one subgraph drawn as a node today), `24-party-fixes.md` C3 (desk
templates, the nearest thing to a reusable fragment), and
`docs/plans/README.md`.

## The rules

- **The graph on GRAPH is the whole truth** (plan 36): no default graph,
  no hidden edge, no auto layout, nothing filled in at load. A spawn
  attaches nothing by itself. **The one exception is the owner's (D4)**:
  a folded group hides its internal cables until `+`. Nothing else may.
- **The renderer learns nothing.** No golden moves; the signature fixture
  is not re-recorded; `build_graph` sees the flat graph.
- **Through the doors**, one undo step each; no file written by a spawn.
- **Dylan's files** untouched: `apc40.py`, `midi.py`,
  `bindings.default.json`, the desk diagram, `ui_desk*.py`.
- **Both Macs on this build** before a preset with `groups` is shared:
  an older build drops the key on its save. (Corrected in the build: an
  older build refuses an `/8` file outright, the schema ladder's rule, so
  it never reads the groups to drop them.)
- Sub-agents never push to `main`, never merge, never rebase a branch
  another task is on, never dispatch their own sub-agents; commits end
  with the attribution lines the session gives.

## The base

**`plan-37-38-39-integration` @ 2b185ea or later** (plan 38 and plan 39
T0–T4 are on it; `main` @ f984d3b with PR #266 is under it — corrected
in the build: it was not; it came in with the plan 40 docs merge). If that
branch's final PR has already merged to `main`, cut from `main` instead.
Verify the base before cutting anything; re-check it before each
worktree. Branch **`plan-40-build`** cut from there; each task's worktree
`plan-40-t<n>` cut from `plan-40-build` as it stands when the task
starts. Merge each task into `plan-40-build` when its report says DONE
with the numbers and you have run its tests yourself.

**The order, because plans 37 and 39 are still landing** (the build
plan's "Running beside plans 37–39" says why): T0 first, alone; then T1,
T4 and T5 in parallel; **T2 and T3 only after the integration branch's
final PR has merged to `main`** — merge `main` into `plan-40-build`
once, run the fast tier, then cut T2; T3 after T2; review; T6 last. If
the owner says to go sooner, T2 may cut once plan 37 is on the
integration branch, and the controller merges that head instead. Do not
start T2 against a base without plan 37's `ui_graph.py` and
`graphview.py`: that is the one conflict worth waiting for.

Numbers: register rows **471–495**, hand checks **394–401, group AK**
(the build plan says why). If plan 37A or 37B has taken rows past 470 by
then, take the next free and say so in the ledger. (As built: rows
501–536, plans 37–39 and PR #275 having taken through 500.)

## The ledger

`docs/plans/assets/40-run/`: `ledger.md` (one line per task: branch,
base commit, state, test counts), `briefs/t<n>.md` (what you handed each
sub-agent: the build plan's task verbatim plus the global constraints
and the base), `reports/t<n>.md` (what came back), `decisions.md` (every
ruling you made where the spec was silent, each a candidate register
row). The docs task reads them.

## Briefing a task

Each brief carries: the task's section of the build plan verbatim; the
global constraints; the base commit; the spec's relevant P-section and
the decisions it builds on; the files it owns and the files it must not
touch; the tests to add and the proofs; "before reporting DONE". The
sub-agent reports: what it built, where the spec and the build differ
and why, the test numbers (fast tier, goldens), the files touched, and
any ruling it had to make (into `decisions.md`).

## Review

After T5: a reviewer sub-agent reads `plan-40-build`'s diff against
`main` with the spec open — D1–D10, the rules above, the build plan's
proofs — and lists findings with file:line and a fix for each. Fix them
in place on `plan-40-build` (a worktree, one commit per finding or one
for all small ones). Then T6.

## Finishing

Run the full suite once (`uv run pytest -q --all`) and the goldens on
`plan-40-build`; record the numbers in the spec header. Open the PR
`plan-40-build` → `main` with: the decisions as built, the test numbers,
the hand checks to run at the machine (394–401), what both Macs must do
(update together before a preset with `groups` is shared), and the
rulings in `decisions.md`. Do not merge it.
