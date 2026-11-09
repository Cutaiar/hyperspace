# Reviewing a change

What a reviewer checks before a branch merges, whether the reviewer is a
person, Claude or a review bot. The project's rules are in
`hyperspace-python/docs/`:

- [`ARCHITECTURE.md`](hyperspace-python/docs/ARCHITECTURE.md): who owns
  what, who may write a parameter, and which modules may import which.
- [`DECISIONS.md`](hyperspace-python/docs/DECISIONS.md): the decisions in
  force.
- [`CHECKPOINT.md`](hyperspace-python/docs/CHECKPOINT.md): the working
  rules.

This file applies those rules to a diff. A finding names the rule it
breaks or a concrete failure: an input, a file or a click, and what goes
wrong. Taste is not a finding.

In Claude Code, `/deep-review` runs this review on the current branch
([`.claude/skills/deep-review`](.claude/skills/deep-review/SKILL.md)).

## Files on disk are a format

- **A saved id or key is part of a file format.** The same applies to any
  change in a stored value's units. Ids and keys means:
  - a `persist=True` param's id;
  - a key in a loadable patch, patch, show or `bindings.json`.

  Renaming or removing one needs three things:
  - a mapping that reads an old file as it was;
  - a backup before the first rewrite, per CHECKPOINT: "a change to a file
    format backs the old file up before the first rewrite". Follow the
    pattern in `routing.backup` and `Project.write`.
  - a test that opens an old file end to end, not only a unit test of the
    converter.

  Shows store every persisted shared meta param, so renaming a shared meta param
  reaches every saved show. PR #289 renamed the stick spring's
  `desk.pad.hz` to `desk.pad.duration` and was caught here.
- **What a build from before makes of a file this branch writes.** Either
  bump the schema, or add a DECISIONS row saying why not. The precedent
  for "why not" is that both Macs sharing a library run one build.
- **Conversions at their edges:** 0, ±1, infinity, NaN, and old values
  outside a new control's range. A clamp on load changes a value without
  saying so.

## Architecture

- Layering is as ARCHITECTURE describes:
  - The panel writes only bases and never calls `modulate`.
  - The Router keeps no state for the UI's sake. Read-only accessors are
    fine.
  - Leaves import nothing from the package.
- A new module goes into `hotreload.MODULES` in dependency order.
- A decision the owner made gets a DECISIONS row.
- ARCHITECTURE's component table names new public functions.

## Every frame, and hot reload

- **Per-frame code** (anything the panel or the frame runs every frame)
  does no scans of a whole history and no cache rebuilds.
- **Module-level caches** survive their module being reloaded.
- **New fields on live objects** (a dataclass held across frames) don't
  reach those objects by hot reload. When a branch adds them, the PR says
  "restart".

## The panel

- **A section stays inside the pane; it may scroll down.** There are no
  pages (plan 49): a section scrolls in its body, and no control passes the
  pane's right edge beside the canvas at `SIDE_MIN` and `SIDE_W` or in the
  narrow band (`tests/test_ui_pane.py::test_every_section_focused_lands_in_view_and_inside_the_pane`,
  which checks controls, so look at long text as well).
- **Widgets fit their narrowest width.** A widget fits the narrowest place
  it is drawn, such as GRAPH's side pane.
- **`ui.PAGE_KEYS` is append-only.** A binding's `set` on `ui.page` stores an
  index into it.
- **Text matches the current model.** Tooltips and labels describe the
  model as it is now, not one the branch replaced.
- **A colour and a measurement are named, not inline.** `ui.py` holds the
  palette (`RED`, `TEXT`, `DIM`, `FAINT`, `LINE`) and the panel's metrics
  (`LABEL_W`, `LABEL_GAP`, `ROUND`, `DOT_R`); a new one goes there and the
  other modules read it, as `ui_graph.py` already does. An `ImVec4(0.7, 0.7,
  0.72, 1)` written at a draw site is `DIM` spelled so nothing can find it.
- **Space is a scale, not a pitch.** A gap, a padding and a row pitch come
  from one set of steps. Written out per site they stop agreeing: dkit's
  demo laid rows out as `i * 27` around 24px controls — a 3px gutter — while
  its card header used 20px where the component it copied uses 4. Nothing in
  the code said either number was wrong, because no number said what it was.
  The fix is not better constants; it is not writing constants
  (`tools/dkit/box.py`, `tools/dkit/tokens.py:SPACE`).

## The base

- **The branch is on current `main`.** `git fetch origin main`, then
  `git merge-base --is-ancestor origin/main HEAD` must succeed. If it
  doesn't, the branch is rebased and its tests rerun before anything else
  is reviewed: a stale base reads as reverting whatever merged since.

## Leftovers

When a branch went through several designs, search its diff for anything
from the designs it dropped: words, tooltips, docstrings, tests and
constants.

## Tests

- **Compare with the base branch, not with zero.** Run the changed
  packages' tests and compare the failures with the base branch's. On
  Linux some UI tests fail before any change, because the macOS fonts are
  missing.
- **Fixes come with tests.** A fix comes with the test that would have
  caught it.

## How to review

- **The reviewer isn't anchored.** The reviewer gets the diff and these
  rules, not the author's account of the change.
- **Reproduce first.** Reproduce a finding, with a script or a failing
  test, before acting on it.
- **Rank the findings.** Report what must be fixed before merge,
  separately from what can be a follow-up and what was checked and found
  fine.
