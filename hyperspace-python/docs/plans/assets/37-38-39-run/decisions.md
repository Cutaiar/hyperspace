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
9. **39-T1's eight fixture goldens re-recorded** (2026-10-27). The honest
   cut-through blend (the window's `bg_alpha`, not a laid-over ground's)
   moves `backdrop-still|present|*` and `media-chain-backdrop|present|*`
   (four states each): a scene laid over the **backdrop** also clears to a
   zero ground (plan 32 R), which the spike missed by looking only at
   composites. The old pictures show the faces washed toward white (the
   sheet: `reports/39-T1-golden-diffs/`); the new ones draw them at their
   own opacity. Not a factory preset. The prompt's "pictures don't move"
   names only plan 37 P2 as an exception, but plan 39 T1 is written as a
   behaviour fix the owner asked for ("alpha must be honest"), and
   narrowing it to composites would keep two rules for one ground. Ruled
   as plan 36's ruling 5 was: the rule beats "goldens unmoved". *Reverse:*
   revert T1's blend commit; the old goldens return with the old blend.
   Register row drafted by T1; hand check AJ.10 is the eye's judgement.
10. **37-C4 (dry run) merged as is; two questions queued for the owner
    with D1.** (a) Presets store `view.pattern` as an index, so dropping
    modes either renumbers (and remaps every preset's value, both Macs on
    this build) or keeps the retired indices as tombstones mapped at
    load; the controller's lean is **tombstones** (no schema change, the
    FACES page lists only the kept, a retired index reads as its nearest
    kept with a note). (b) The migration needs `preset.py` (the four
    `view_pattern=` factory presets) and `tests/fixtures/factory-sources/`,
    which plan 37's ownership row does not give it: the controller allows
    that edit when P2 runs. *Reverse:* P2 has not run; both are choices
    for the owner's list.
11. **37-C3's area rule as built, not the brief's tie-break.** The brief
    said "a node with consumers in several areas keeps today's area";
    that could not fix P3's own wire (`acid.2` in the `acid-scene` fixture
    feeds the look-back *and* a composite in EFFECTS). Built: an
    effect-area node is laid in the leftmost consumer area not left of
    what feeds it; only effect-area nodes move; a node whose consumers are
    all to its right never moves; a saved or already-drawn position never
    moves (no layout runs by itself). The reviewer traced that it cannot
    place a node left of its feeders and cannot loop. *Reverse:* one
    function (`graphview.laid_areas`); D5's row (417–429) is the owner's
    to overturn.
12. **Plan 38 may edit `preset.py`'s land block (and one line at the
    delay reset)** to fix B3's Critical: every `GraphSection.land`
    re-settles the effect instances (`fx.hold(names)`), the switch and
    resize states (and plan 39's mattes/cuts/segments on the same
    pattern), so a load or a GRAPH edit during a hold strips the program's
    nodes. The fix is a hold-side hook the land block consults ("names to
    keep while held": the landed set ∪ the held program's), cleared at
    Take (which re-settles to the live set) and at Drop (the revert
    lands the hold point). The ownership table gave 38 nothing in
    `preset.py`; the seam is a few lines in one block and generic over
    every declare, so plan 39's declares inherit it at integration.
    `fx.py`/`params.py` untouched. The delay reset on a load
    (`preset.py` ~1047, `gs.renderer.reset_delays()`) goes to the preview
    while held, the program's at Take if a load happened. *Reverse:*
    the hook defaults to identity; removing the hold removes it.
13. **Seams recorded for the other streams** (B3's I2, I3): plan 38
    provides `hold`'s "the renderer the canvas reads" helper (the preview
    while held and drawn, else the main renderer); plan 37's integration
    rebase routes `thumbs.want`/`_graph` reads through it (the controller
    does this at the 37 merge, or a small follow-up). Plan 39 T4: the
    preview renderer gets **no** segment workers (the node passes through
    and says "no worker in the preview"), `Renderer.close` closes only
    its own workers (the preview shares media, hands, look-back state,
    fx state), and the app's close list adds the preview's close. Added
    to T4's brief before dispatch.
12b. **Ruling 12 extends to `Presets._values`**: a save during a hold
    leaves out the instances kept only for the projector (else dead ids
    land in the library). One line; the hook's twin. *Reverse:* with 12.
14. **`matte`, `cut` and `segment` are held groups** (`hold.HELD_GROUPS`,
    added by the plan 39 integrator): a knob turned on a held node moves
    the preview, not the projector, like `resize`/`switch`. Also at that
    merge: the three declares inside `GraphSection._settle` through
    `hold.keep`; `PROGRAM_IDS` entries; `masks` hot-reloadable, `segment`
    cold (live threads, as the dream). *Reverse:* remove the three names
    from `HELD_GROUPS` (then a held segment's feather follows the live
    knob on the projector).
