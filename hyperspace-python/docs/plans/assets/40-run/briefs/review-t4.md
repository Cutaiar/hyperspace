# Review dispatch — T4 (plan 40 P4: devices.wants, the chips, the SYSTEM lines, the arrival)

Read first: `/Users/dallman/.claude/jobs/45478892/tmp/run/briefs/reviewer-common.md`.

- Worktree to read in: `/Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a4148d70404778a58`
  (branch `plan-40-t4`; run commands from its `hyperspace-python/`). Read-only.
- Diff: `git diff 51106e1...origin/plan-40-t4` (fetch `origin/plan-40-t4` first, read-only). PR #272.
- The brief: `/Users/dallman/.claude/jobs/45478892/tmp/run/briefs/t4.md`; the common brief
  `briefs/common.md`; the spec `hyperspace-python/docs/plans/40-patches.md` **P4** and
  "What is there today" item 5; the build plan `40-patches-build.md` Task 4.
- The implementer's report: `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/t4-report.md`;
  decisions: `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t4.md`.
- Particular doubts to settle: (1) `DeviceRegistry.poll` calls `_changed()` **once per frame**
  on a status change, not per device, and nothing fires over 100 steady frames; the hook
  fires once per change with the counts; (2) the MIDI relight path (`midi.py`, Dylan's,
  untouched) still runs as before — the event adds a saying, not a second poll; (3) `wants`
  is pure and cheap enough to call every frame from the head chip (no per-frame allocation
  storm; or cached on a serial); (4) the role resolution order: `@role` qualifier, else the
  primary MIDI role for `cc:`/`note:`/`pitch:`, else `SCHEME_ROLE` — and `SCHEME_ROLE` is
  now defined in `devices.py` with `graphview` importing it (the placeholder node's words
  unchanged); (5) `routing.row_words` does not import `apc40.py` into `routing`; (6) the
  `ui_graph.py` / `graphview.py` touches are the few lines the brief allows (plan 37 is
  landing on those files); (7) `wants` never names a built-in scheme (`lane`, `lfo`, `env`,
  `seq`, `mod`); (8) the tests assert the words and the states, not only truthiness.
- Output as reviewer-common.md says. Then write the same report to
  `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/t4-review.md`.
