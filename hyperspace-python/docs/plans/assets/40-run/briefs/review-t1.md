# Review dispatch — T1 (plan 40 P1: patches.py — read, check, lift, spawn; the patches DocKind)

Read first: `/Users/dallman/.claude/jobs/45478892/tmp/run/briefs/reviewer-common.md`.

- Worktree to read in: `/Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a27cd195fdf203588`
  (branch `plan-40-t1`; run commands from its `hyperspace-python/`). Read-only.
- Diff: `git diff 51106e1...origin/plan-40-t1` (fetch `origin/plan-40-t1` first, read-only). PR #274.
  The new module is `hyperspace/patches.py` (1155 lines) and `tests/test_patches.py` (640).
- The brief: `/Users/dallman/.claude/jobs/45478892/tmp/run/briefs/t1.md`; the common brief
  `briefs/common.md`; the spec `hyperspace-python/docs/plans/40-patches.md` — "The idea in one
  paragraph", **P1**, D5, and the map items 2–5; the build plan `40-patches-build.md` Task 1.
- The implementer's report: `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/t1-report.md`;
  decisions: `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t1.md`. It departs from the
  spec in four named places (the fixture's `mod:1` not `mod:0`; envelopes in a patch file start
  at `env.6`; `lift` returns `(doc, refused)`; the "main run" is `run_back` into
  `output.all.image`): judge each against the spec's intent and ARCHITECTURE §3.3 (a `mod:<n>`
  lane is `mod.<n>`; lane envelopes 1–5 are the sequencer's).
- Particular doubts to settle: (1) the boundary classifier is "not the patch's own" — an open
  rule, not a closed list of rig schemes; a `mod:`/`lfo:`/`env:` of an id the patch does not
  hold is a host port, with and without an `@role` qualifier on a rig source; (2) every id is
  renamed everywhere — values, wires, routes (source **and** target), desk rows, modifier
  inputs, macro subscribers (base and depth: the depth subscriber names a route by
  `(source, target)`), layout — in both `lift` and `spawn`; (3) the rename map in `spawn`
  cannot collide with the host's own ids (`acid.2` when the host already has `acid` and
  `acid.2`; `mod.<next>` by the modifier rule; `lfo.<next>` / `env.<next>` by the bank's
  high-water rule; a macro: the lowest free of eight, else a note and its subscribers not
  spawned); (4) the conflicts: a desk control the host maps (`Binding.overlaps`, qualifier
  respected), a performer source that owns a host param under a one-owner rule (which
  schemes — the decisions file says), a patch route onto a host param another performer
  owns (`Bindings.owner`); and a spawn with a conflict lands nothing (it is pure anyway —
  check `Landing` carries everything so the caller can land with choices); (5) D5: `values`
  holds only the members' params, never a host param's value; (6) the round-trip property
  test really compares `read(lift(spawn(p)))` to `read(p)` up to renames and origin, and
  names the factory presets it skips; (7) `patches.py` is a leaf (imports `graph`,
  `modifiers`, `routing`'s pure pieces only; no `ui_*`, `app`, `render`, `library`) and
  `library` imports it, not the other way; (8) `Library.read_patch` validates schema and
  shape and raises `LibraryError`; `save_patch` is atomic and trashes an old text as
  `save_as` does; `hide`/`rename`/`list` work through the kind (the `hidden.json` `"patches"`
  key the report describes — check an old `hidden.json` with no such key still reads); (9)
  the refusal list (frame singletons, outputs, clouds, camera, media channels, the sequencer,
  lane envelopes 1–5 by identity) agrees with `graph.FRAME_KINDS` and `graphview.NOT_REMOVABLE`
  by a test, without `patches` importing `graphview`; (10) the tests assert words and shapes,
  not only truthiness, and none re-derives its answer from the code under test.
- Output as reviewer-common.md says. Then write the same report to
  `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/t1-review.md`.
