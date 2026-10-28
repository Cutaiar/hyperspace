# Decisions the controller made in the owner's absence (plans 37/38/39 run)

Each with how the owner reverses it.

1. **PR #248 unmerged → integration branch = `main` + the spike merged.**
   `plan-37-38-39-integration` is f2351a0 + `worktree-vision-spike`
   (docs only), cb78963. *Reverse:* merge #248 to main whenever; the
   integration branch then rebases or merges main cleanly (same content).
2. **Task PRs go into the plan branches** (`plan-37-pictures`,
   `plan-38-hold`, `plan-39-vision`), the controller merges each after its
   review; the plan branches merge into the integration branch in the
   prompt's order; the final PR is the integration branch → `main`.
   *Reverse:* none needed — the records are the PRs.
3. **39-T2 starts with T0 and T1**, not after them: its files (`graph.py`,
   new `masks.py`, `params.py`, `preset.py`, `graphview` tables) do not
   overlap T0's (`shaders/fx/edges.glsl`, a fixture) or T1's
   (`render.draw_scene`, `test_render.py`). Merge order into
   `plan-39-vision` stays T0, T1, T2. *Reverse:* none; a merge conflict
   would be resolved by the controller.
4. **37-C3 and 37-C4 start with C1**: C3 is `graphview`'s area rules,
   C4 is a tool and assets; C1 is `ui_graph._node` + `PreviewTextures`.
   C2 waits for C1. *Reverse:* none.
5. **Plan 37's D1–D5 taken as recommended** (the prompt's instruction):
   D1 drop nothing until the list; D2 thumbnails always; D3 plain red,
   tint behind a head switch; D4 faces per instance after; D5 the area
   rules. *Reverse:* each is a register row (417–429) the owner can
   overturn; D5's rule is one function in `graphview`.
6. **Sub-agents run on Opus 5.5** (the owner's instruction for this run).
7. **Implementers run the full suite (`--all`) before DONE** (the owner's
   standing rule for this run), not only the fast tier as plan 36's
   ruling 409 allowed. Cost: ~1 min per task on this Mac.
8. **The two load-flaky media tests are not the run's**: they pass
   serially on the base; a task whose `--all` shows only those two is
   green. If they fail serially on a task branch, that task owns it.
