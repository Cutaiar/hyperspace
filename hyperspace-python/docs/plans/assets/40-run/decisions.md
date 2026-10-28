# Decisions the controller made where the spec was silent (plan 40 run)

Each a candidate register row (471–495, after D1–D10), with how the owner
reverses it.

1. **`main` @ f984d3b (PR #266) was not under the base; it came in with
   the docs merge.** The build plan says PR #266 "is under" the
   integration branch @ 2b185ea; it was not (`git merge-base
   --is-ancestor` says no). `plan-40-patches` was cut from `main` @
   f984d3b, so merging it as the first commit (f10f281) brought #266's
   `ui_graph.py` / `test_graph_legible.py` along, auto-merged clean. The
   build branch therefore holds the integration branch + #266 + the plan
   40 docs, which is what the build plan assumed. *Reverse:* none needed;
   the later `main` merge (before T2) is the same content.
2. **Sub-agents run on Opus** (`DECISIONS.md` "Process": agents in a run
   work on Opus or Sonnet, never Fable). *Reverse:* none.
3. **Task PRs go into `plan-40-build`**; the controller runs each task's
   tests itself, reviews (a reviewer sub-agent on T1–T4; T0 and T5 by the
   controller's own read), and merges; one plan-level review after T5 as
   the prompt says; the final PR is `plan-40-build` → `main`. *Reverse:*
   none needed — the records are the PRs.
4. **T0's symbol rename reaches the live docs, not the run records.**
   `ARCHITECTURE.md`, `ENGINEERING.md`, `DECISIONS.md`,
   `DECISION-REGISTER.md`, `28-node-editor.md` and
   `28-30-orchestrator-prompt.md` get the sed (symbol names only); the
   historical `assets/28-30-run/` briefs, reports and decisions keep the
   old names, as a record of what was true then. *Reverse:* a sed.
5. **T0 renamed the classes too** (`Patch`/`PatchNode`/`PatchEdge` →
   `ModGraph`/`ModNode`/`ModEdge`, `patch_cut`, the privates; sub-agent's
   47a), beyond the build plan's listed symbols. Accepted: D1's goal is
   that `patch` means the owner's thing and nothing else, and a class
   named `Patch` in `modgraph.py` would not. *Reverse:* a sed.
6. **The modgraph docstring says "was named `patch`", not `patch.py`**
   (47b), so the build plan's proof grep stays empty. Accepted.
7. **Sub-agents' commit trailers name the model that ran them** (Opus
   5.5), per the harness each sub-agent runs under; the controller's own
   commits carry Fable 5.1 and this session's URL. *Reverse:* none; both
   are true.
8. **T0 left two doc files for T6** — `11-hand-checks.md` (three `test_patch.py`
   references) and `30-shader-nodes.md` (two `patch.py`) — because the
   common brief forbids editing them outside the docs task. T6's brief
   names them.
