# Plan-level review dispatch — plan 40 (`plan-40-build` against `main`)

Read first: `/Users/dallman/.claude/jobs/45478892/tmp/run/briefs/reviewer-common.md`
(the binding constraints and the output format apply; this is the
**plan-level** pass the session prompt asks for after T5, over the whole
build, not one task).

- Worktree to read in: `/Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/plan-40-build`
  (branch `plan-40-build` @ **HEAD_SHA**; run commands from its
  `hyperspace-python/`). **Read-only**: do not change its working tree,
  index, HEAD or any branch.
- Diff: `git diff origin/main...HEAD` — the whole plan (T0, T1, T2, T3, T4,
  T5 and the review fixes). It is large; read it by file, `patches.py`,
  `graphview.py`, `ui_graph.py`, `ui_routing.py`, `preset.py`, `devices.py`,
  `library.py`, `routing.py` first.
- The spec: `hyperspace-python/docs/plans/40-patches.md` — **D1–D10 in the
  "the owner" column are the requirements** (D3 ask in one sheet, D4 saved
  and folded until `+`, D6 retired outright, D10 the FX page stays, D2 open
  pins + splice + the chip, D5 only the boundary, D8 control window only,
  D9 preselected to the patch); P1–P5; the eight hand checks. The build
  plan `40-patches-build.md`: "Global constraints" and every task's
  proofs. The session prompt `40-session-prompt.md`: "The rules".
- The run's records: `/Users/dallman/.claude/jobs/45478892/tmp/run/ledger.md`,
  `decisions.md` (the controller's rulings), `reports/t*-report.md`,
  `reports/t1-review.md`, `t4-review.md` and any `t2-review.md` /
  `t3-review.md`, `decisions/t*.md` (the sub-agents' rulings).

## What to verify, with the proofs the build plan names
1. **The renderer learns nothing.** `git diff origin/main...HEAD --stat --
   hyperspace/graph.py hyperspace/render.py` is empty (or names only what
   a report justified); no golden under `tests/golden/` changed;
   `tests/fixtures/frame-signatures.json` unchanged; the grouped-twin
   signature test and the grouped golden proof exist and assert equality.
2. **D4 is the only folded cable.** Count: for a folded group, drawn +
   hidden cables = the open count = the ungrouped count; nothing else in
   the diff drops a cable from the canvas; `preset_only` still shows a
   group.
3. **D2.** After a spawn from the menu or the chip, the section's wires
   equal before plus the patch's own internal wires; splice adds exactly
   the two cables and removes the one; **wire as saved** is a press, one
   undo step, refused in words when a port is taken; `patches.check`
   refuses crossing wires and `spawn` never emits one.
4. **D3 / D9.** The sheet is drawn by `ui_routing.modal` ahead of the
   Replace / Keep question; every row preselected to the patch; **keep all
   existing** flips; Spawn lands the whole `Landing` with the choices as
   **one undo step**; Cancel lands nothing and pushes no step; the hands
   learn nothing while it is up; a kept row is recorded on the group
   (`kept_by_host`) and said on the node.
5. **Through the doors, one undo step each.** Group, Ungroup, Rename, a
   title drag, a member dragged out, a spawn, a splice, wire as saved: each
   `undo.push(label, load=True)` once before the first write; every table
   write is `Bindings.add` / `bind(write=False)` / `replace_owner` /
   `add_modifier` / `set_macros`; every voice `bank.add`; values
   `lib.restore`; the section `gs.land`. No new write path onto a `Param`
   or the table (grep the diff for `.modulate(`, `._value`, direct dict
   writes into `table.`).
6. **No file written by a spawn** (the scratch-home diff test exists and
   is strict); save as patch writes one file; `bindings.json` untouched by
   any path in the diff.
7. **Dylan's files**: `git diff origin/main...HEAD --stat -- hyperspace/apc40.py
   hyperspace/midi.py hyperspace/bindings.default.json hyperspace/ui_desk*.py`
   is empty. D8: nothing spawns from the desk.
8. **Schema (D7).** `groups` writes `/8` only when non-empty; an ungrouped
   preset saves byte for byte (the test over every factory preset); the
   migration is "absent → no groups"; no factory preset or library file
   rewritten (`git diff origin/main...HEAD --stat -- hyperspace/library/`
   lists only the six removed fx files).
9. **D6 / D10.** `library/fx/` gone, `_fx_module`, `module_runs` gone,
   `ui_fx.py` untouched, the module strip hidden (ruling 9), the FX page's
   draw tests green.
10. **P4.** `wants` is pure and cheap (ruling: once per frame, no Port
    layouts); the status-change event fires `_changed` once per frame and
    the hook once per change; the MIDI relight untouched.
11. **Leaves and boundaries.** `patches.py` imports only leaves;
    `graph.py` imports only the render stack; `import hyperspace.app` pulls
    no `torch`; the AST tests exist.
12. **Tests assert things**: look for asserts that cannot fail, tests that
    re-derive the answer from the code under test, fixtures that were
    force-added and are in the tree (`git ls-files tests/fixtures/patches`).
13. **The seams between tasks**: T2's `VGroup` boundary built from T1's
    classifier (one classifier, not two); T3's sheet reading T4's words;
    the group node's status line from `wants_for`; T2's `kept_by_host`
    drawn when T3 fills it; the thumbnail on a folded group (plan 37) or
    its documented absence.

## Output
As reviewer-common.md says: spec compliance per decision D1–D10 (a line
each), strengths, issues as Critical / Important / Minor with
**file:line and a fix for each**, assessment. Then write the same report
to `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/plan-review.md`.
