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
9. **The FX page's module-preset strip is hidden** (T5's 47a). The spec's
   P5 says nothing on the FX page referred to the module presets; it did
   (`ui_fx.page` → `_section("effects", "fx")` draws the strip: name ·
   save · as… · reset). D6 retires the mechanism, D10 keeps the page: the
   strip *is* the mechanism's UI, so `ui_presets.strip` draws nothing for
   a retired group and `ui_fx.py` is not edited. *Reverse:* one condition.
   T6 corrects P5's sentence and says it in "as built".
10. **A retired module group is named** (`library.RETIRED_MODULES`), not
    inferred from "no folder" (T5's 47b): `view`, `rot`, `camera` have no
    factory folder and keep their strips. An old `<library>/fx/` folder on
    the Drive is ignored, its files untouched. *Reverse:* empty the tuple.
11. **The party generator keeps the three fx families' values inline**
    (`preset.ACID_FX` / `MANDALA_FX` / `NOITA_FX`, T5's 47d) so
    `write_factory` is byte-identical; `party-acid` / `party-mandala`'s
    notes still say "fx module preset" — preset data, not changed by this
    run. *Reverse:* reword at the next factory regeneration.
12. **Register rows 501–525, not 471–495.** The integration branch's docs
    tasks (plans 37/38/39, PR #270) took rows through 499, and `main` @ 026989e (PR #275) row 500, so the
    prompt's 471–495 are gone; the prompt says "take the next
    free and say so in the ledger". Plan 40 takes **501–525**. Hand checks
    394–401 (group AK) still hold: plan 39's AJ ends at 393. The sub-agents'
    drafts are numbered `47x` / `50x`; T6 numbers them.
13. **`groups` is schema `/8`** (D7): nothing on `main` or the integration
    head writes `preset/8` (37B took no schema). T2 cuts on that; the
    ladder's rule keeps an ungrouped preset on `/7` byte for byte.
14. **The `main` merge before T2 conflicts only in `ui_graph.py`**, three
    both-sides hunks (the `json` / `colorsys` imports, three `st` defaults,
    the T4 wants chip beside plan 37's tint chip): keep both sides of each.
    Checked by a dry-run merge of the integration head 07885a2 on
    2026-10-27; abandoned without a commit.
