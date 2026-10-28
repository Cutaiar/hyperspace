# Review dispatch — T2 (plan 40 P2: the group node — groups in the preset, folded by default, Group / Ungroup; D4, D7)

Read first: `/Users/dallman/.claude/jobs/45478892/tmp/run/briefs/reviewer-common.md`.

- Worktree to read in: `/Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a7a8c6ddbaacfd50d`
  (branch `plan-40-t2`; run commands from its `hyperspace-python/`). Read-only.
- Diff: `git diff d08a363...origin/plan-40-t2` (fetch `origin/plan-40-t2` first, read-only). PR #276.
  14 files, +2383: `graphview.py` (+536), `ui_graph.py` (+501), `preset.py` (+152), `patches.py`
  (+214: the one classifier shared with T1's lift), `graphmigrate.py`, `library.py`,
  `tests/test_graph_groups.py` (560), a grouped fixture, 8 grouped-twin golden proofs.
- The brief: `/Users/dallman/.claude/jobs/45478892/tmp/run/briefs/t2.md`; the common brief
  `briefs/common.md`; the spec `hyperspace-python/docs/plans/40-patches.md` **P2**, **D4** (the
  owner: saved, folded until `+` — the one sanctioned exception to the WYSIWYG rule), **D7**,
  D2; the build plan `40-patches-build.md` Task 2 and "Running beside plans 37–39" (the
  `preset.py` seams: `GraphSection._settle` / `names` / `_values` are plans 38/39's).
- The implementer's report: `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/t2-report.md`;
  decisions: `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t2.md` (50a–50h, AK.n1–n4).
- Particular doubts to settle: (1) **the renderer learns nothing**: `graph.py`, `render.py`,
  `tests/golden/`, `frame-signatures.json` untouched (confirmed by stat — verify the grouped-twin
  signature test and the golden proof assert equality against the ungrouped twin, not against
  themselves); (2) **D4 is the only fold**: a folded group hides its members and the cables with
  both ends inside, re-ends crossing render cables at typed pins and value cables at boundary-param
  rows, and nothing else is dropped — look for a cable-count test (folded drawn + hidden = open =
  ungrouped) and for any other path in the diff that leaves a cable undrawn; `preset_only` still
  draws a group; (3) **D7**: `groups` written after `layout` only when non-empty; the schema the
  save writes is `/8` only for a grouped preset and an ungrouped one saves byte for byte (the
  test over every factory preset); the migration is "absent → no groups"; the report says an
  older build *refuses* an `/8` file rather than dropping the key — judge whether that is the
  ladder's existing rule (it is for `/3`, `/6`, `/7`) and say so; (4) **one classifier**: T2's
  `VGroup` boundary comes from the classifier in `patches.py` that `lift` also uses — not a second
  one in `graphview`; (5) **one undo step each**: Group, Ungroup, Rename, Open/Fold, a title
  drag, a member dragged out — each `undo.push(load=True)` once; Group-then-⌘Z restores the
  signature; (6) `Edit.group` applies `patches.check`'s refusals by name in words; `id` is
  `group.<n>` one past the highest held, never reused; one group per node, no nesting — and the
  ruling the task took for grouping a member of another group; (7) `load_doc` drops a member the
  graph lacks with the note and drops an empty group; `Marks.take` / `put` carry `groups` so undo
  of a load restores them; (8) the status line uses T4's `wants_for` / `want_words`, the
  thumbnail uses plan 37's want list (or its absence is said), the `_group_chips` hook exists for
  T3, `kept_by_host` is drawn if present; (9) the `preset.py` diff stays out of
  `GraphSection._settle` / `names` / `_values`; (10) the tests assert counts, words and bytes,
  not truthiness; the headless widget tests drive the real editor as `test_graph_legible` does.
- One side question, outside the task: the implementer says plan 38's `ui_graph._monitor`
  (`dl.add_rect(ImVec2, ImVec2, col, 0.0, 0, 2.0)`, ~line 1137 on the base) raises a `TypeError`
  the first time the hold inset draws. Check the imgui_bundle `add_rect` signature in the venv
  (`uv run python -c "from imgui_bundle import imgui; help(imgui.ImDrawList.add_rect)"`) and say
  whether the call is wrong and what the fix is — the controller will fix it in the review pass.
- Output as reviewer-common.md says. Then write the same report to
  `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/t2-review.md`.
