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
15. **Schema of an ungrouped save — pending the owner.** T2's ruling 50g
    writes `/7` for a preset with no groups and `/8` only for a grouped one
    (the build plan's "a preset without `groups` saves byte for byte as
    before" and "the factory presets and the library are not rewritten",
    which the T2 brief carried). The T2 reviewer notes this revives "the
    lowest schema that loses nothing" (R10), which the owner overturned on
    2026-10-25 with row 394 ("every save is the newest schema; migrate the
    library forward"). D7 cites row 394, so the spec's intent is likelier
    the newest schema. **Controller's recommendation:** follow row 394 —
    every save writes `/8`, reading `/7` is the identity, the factory files
    and the Drive library are migrated forward by `tools/migrate_library.py`
    as plan 36 did (a schema-line rewrite only; backups as before). Built
    as 50g until the owner answers; the review-fix pass flips it on his
    word. *Reverse:* one rule in `preset.schema_of` and a migration run.
16. **T3's task-scoped review is folded into the plan-level review** (the
    session prompt's one review after T5): T3 is the last code task, its
    diff is the last thing the plan review reads, and a separate pass
    would read the same lines twice. The plan review's brief names T3's
    doubts (a)–(i) explicitly. *Reverse:* none.
17. **"Wire as saved" refuses a port the host already feeds** (T3's 50j;
    "output.all.image is taken"), as D2's text says ("if the host has
    those nodes and the ports are free, refused in words otherwise").
    Taking the port over would cut the host's run silently. **For the
    owner**: whether a separate, explicit take-over chip ("wire as saved,
    replacing huecycle → All outputs") should exist — without it, in any
    host whose run already feeds All outputs the outlet always refuses.
    No code now; a register row.
18. **A spawned group's open pins and its rename map last the session**
    (T3's 50i): a save drops them, so after a reload a group whose pins
    were never wired shows no in / out pins, while P2 says "one pin per
    host port … or open". Reasoned (the file keeps what the graph holds;
    an open pin is a session affordance); **for the owner**, a register
    row beside 17.
19. **T3's spawn tests use `party-trip`'s real contents**: it holds none of
    the spec's acid / wobble / delay / warp, so a first spawn keeps bare
    ids by the instance rule, the second spawn proves `.2`, and the splice
    proof is on `scene → plasma.image`; the hand reaches the patch through
    `mod.1`'s input. T6 corrects the build plan's examples in "as built".
