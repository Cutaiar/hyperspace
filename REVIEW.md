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
  - a key in a preset, patch, show or `bindings.json`.

  Renaming or removing one needs three things:
  - a mapping that reads an old file as it was;
  - a backup before the first rewrite, per CHECKPOINT: "a change to a file
    format backs the old file up before the first rewrite". Follow the
    pattern in `routing.backup` and `Project.write`.
  - a test that opens an old file end to end, not only a unit test of the
    converter.

  Shows store every persisted session param, so renaming a session param
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

- **No page scrolls at the control size, across or down.**
  `tests/test_ui_shell.py::test_every_page_fits_the_control_window` checks
  down only, so look across as well.
- **Widgets fit their narrowest width.** A widget fits the narrowest place
  it is drawn, such as GRAPH's side pane.
- **Text matches the current model.** Tooltips and labels describe the
  model as it is now, not one the branch replaced.

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
