# Review-fix pass (plan 40) — fix the findings in place on `plan-40-build`

You are the implementer of the **review-fix pass** of plan 40. Read first, in full:
`/Users/dallman/.claude/jobs/45478892/tmp/run/briefs/common.md` (the hard rules, the gates, the
report contract; the "do not edit the docs" rule holds — T6 is next).

## Dispatch
- Base branch: `plan-40-build`. Base SHA: **19596e8** (T0–T5 all merged; `main` @ 026989e under
  it). Your branch: `plan-40-fixes`.
- First commands: `git fetch origin plan-40-build`, `git reset --hard FETCH_HEAD`,
  `git branch -m plan-40-fixes`.
- PR into `plan-40-build`, titled `Plan 40 review fixes: a spawn says what waits, the T2 and T3
  minors, plan 38's hold inset`.
- Base counts (19596e8): fast tier **4306 passed, 2 skipped**; goldens **144 passed**; `--all`
  **4536 passed, 2 skipped** (+ one GL-contention flake that passes serially).
- Workspace: decisions → `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/fixes.md`;
  report → `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/fixes-report.md`.
- **One commit per finding** where a finding is more than a few lines, else one commit for the
  small ones; each commit subject names the finding ("Plan 40 review fix: …"). Each fix gets a
  test that could fail without it.

## Read
- `/Users/dallman/.claude/jobs/45478892/tmp/run/reports/plan-review.md` (the plan-level review:
  the Important, the Minors, the T3 (a)–(i) findings) and `reports/t2-review.md` (its Minors).
- `/Users/dallman/.claude/jobs/45478892/tmp/run/fixes-queue.md` (the queue).
- The spec `hyperspace-python/docs/plans/40-patches.md` P2–P4, D2–D4, D9; the build plan Task 3
  §3–4 and Task 4 §3 ("A spawn's notes line says '2 rows wait for leap'").
- The code the findings name: `graphview.py` (`Edit.spawn` ~4354–4442, `wire_as_saved` ~4536,
  `save_patch` ~4558, `_group_n` ~191), `ui_graph.py` (`land_spawn`, `spawn` ~2197, the patch
  list ~2338, `_moved` / `_left_group`, `_stub_drag` / `open_land`, `_monitor` ~1157),
  `ui_routing.py` (`sheet_wants`, `modal`, `settle_sheet`), `preset.py` (`group_number`,
  `_held_canvas` ~1471, `_banks`), `patches.py`, `learn.py` (`hold`), and their tests
  (`tests/test_graph_groups.py`, `test_ui_routing.py`, `test_graph_legible.py`,
  `test_patches.py`, `test_presets.py`, `test_hold.py`).

## The fixes (do every one; say in the report where you did not and why)

**Important**
1. **A spawn says what waits** (plan review Important 1; P4's last bullet). In
   `ui_graph.land_spawn`, after a successful spawn or splice, append the wants line to the
   head's note (`e.said`) — reuse `ui_routing.sheet_wants(panel, landing)` or word it as the
   build plan's "2 rows wait for leap" (`devices.want_words` over `Landing.wants` through
   `devices.wants_for`). Assert the exact line in `test_a_spawn_with_no_conflict_lands_at_once`
   (that rig has no apc40 and no leap, so the words are fixed) and that a spawn whose wants are
   all connected adds no line.

**Plan review minors (code)**
2. A failed landing leaves an empty undo step (`Edit.spawn` ~4401–4404): drop the step on a
   refusal after the dry run, or prove it unreachable in a comment and a test.
3. A source conflict answered "the patch" removes the host's rows before `replace_owner`
   (~4477–4480); if `replace_owner` raises, the rows are gone. Validate before removing, or
   call `replace_owner` first; test the failing path leaves the table whole.
4. **Save as patch…** silently replaces another patch of the same slug (~4558 →
   `library.save_patch`): refuse in words when the group's `patch` is not that slug and the file
   exists ("a patch named acid wash exists — Update patch, or another name"); test it. **Update
   patch** on the group's own slug still overwrites (trash as before).
5. The patch list is rebuilt every frame the canvas's right-click menu is open and every frame
   of a drag (~2338, a listing + a `stat` per file): list once per menu open / per drag start,
   or cache on `ui_presets`' poll; test that two frames with the menu open list once.
6. `ui_graph.spawn` calls the private `pre._banks()` (~2197): a public `Presets.banks()` or fold
   it into `parts()`.
7. Test gaps: the sheet and a Replace / Keep question up together draws the sheet first; the
   PRESETS fold's × on the user's own patch trashes it; a splice that raises the sheet lands the
   splice with the choices.

**T2 minors (from `t2-review.md`, also in the queue)**
8. Several members dragged out of an open group at once push several undo steps (`_moved` →
   `_left_group` per node): collect the leavers and apply them under one push; test with two
   members.
9. A drop on a folded group's stub opens an empty picker (`_stub_drag` → `open_land(group id)` →
   `land_choices` is `[]`): refuse in words via `stub_refusal` ("drop it on the group's pin, not
   its stub" or similar), or offer the group's ports mapped through `real_pin`; test.
10. `preset.group_number` and `graphview._group_n` duplicate: keep one (in `patches` or
    `graphmigrate`, both leaves) and call it from both.
11. Thin tests: `test_a_drag_of_the_folded_node_moves_every_member` asserts the exact delta and
    one undo step; keep the source-grep tripwire as is.
12. The signature proof covers the 9 presets with a main run: also group every effect of the 16
    `NO_RUN` presets (cheap) in the grouped-twin signature test.
13. `Presets._held_canvas` falls back to `range(1, 100)` without a bank (~1471): make it the
    voice ids the table names, and say so.
14. The open region's title node is selectable: a box-select across an open group puts the
    group id in `menu_sel`, so Group says "group.1 is a group: … left out" — filter group ids
    out of the selection before `Edit.group`; test.

**Plan 38, on `main`, confirmed by two reviewers**
15. `ui_graph._monitor` (~1157): `dl.add_rect(ImVec2(*a), ImVec2(*b), col, 0.0, 0, 2.0)` raises
    `TypeError` in a frame — imgui_bundle's signature is `add_rect(p_min, p_max, col,
    rounding=0.0, thickness=1.0, flags=0)`. Fix to `(…, 0.0, 2.0)`. Add a headless test that
    draws the inset once with a stub texture (`tex.glo != 0`, as the hold tests build one) so
    the call is reached. Its own commit, subject "Plan 38 fix: the PROJECTOR inset's add_rect
    call (TypeError the first time it drew)"; say in the report that it is outside plan 40 and
    one line.

**Not yours (the docs task's; do not build)**
- Ruling 15 (an ungrouped save writes `/7` vs row 394) — **unless** the controller's dispatch
  message says the owner answered "newest"; then: every save writes `/8`, reading `/7` is the
  identity, `tools/migrate_library.py` gains the `/7 → /8` step, the factory presets are
  rewritten to `/8` by that tool (the one sanctioned library change, said in the commit), and
  the byte-for-byte test compares all but the schema line against the `/7` original. If the
  message says nothing, leave 50g as built.
- 50j (wire as saved refuses a fed port; a take-over chip is the owner's call), 50i (open pins
  last the session), T6's "imports nothing from the app" wording — register rows for T6.

## Before reporting DONE
The gates in common.md (fast tier, ruff on your files, goldens `--all -m golden`, `--all`
once); the fast-tier count is the base's plus your new tests; goldens unmoved; no doc edited;
`git diff --stat` against the base lists only the code and test files the findings name;
Dylan's files untouched; `graph.py` / `render.py` untouched. Report: one line per finding
(fixed / where / the test), the counts, the PR URL, the short contract.
