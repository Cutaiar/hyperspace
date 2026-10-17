# C3 report: the desk coverage report, desk templates, click-to-map ranked

- **Status:** DONE
- **PR:** https://github.com/Cutaiar/hyperspace/pull/182, into `plan-24-26-27-integration`
- **Branch:** `plan-24-c3-coverage`
- **Base:** `6af4c65`, "Merge plan 24 C2: the faders freed … (PR #180)", confirmed with `git log --oneline -3`
- **Decisions file:** `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/C3.md` (register rows, hand checks U.8–U.10, as-built notes, coverage numbers)

## Commits
- `4faadbc` Plan 24 C3: desk templates — a desk group, a preset's desk as a template plus overrides
- `396570b` Plan 24 C3: click-to-map offers the preset's own params first, ranked
- `d5e6858` Plan 24 C3: the desk coverage report and its committed output

## What was built

**Coverage report.** `tools/desk_coverage.py` builds a headless app rig on a temporary scratch home. While it runs, `HYPERSPACE_HOME` also points at that home. The rig loads every preset and marks each of the 38 preset-layer controls as mapped, dark or dead:
- The 38 controls are D1–D8, K1–K8 and S1–S8, plus the factory map's other preset-layer controls, less any invariant control.
- "Dead" is defined by `learn.cannot_show`.

The output is committed at `docs/plans/assets/24-party-fixes/desk-coverage.md`. The text is deterministic: there are no dates, and every list follows the layout or name order. The flags:
- `--check` exits 1 when the committed file is stale.
- `--stdout` prints the report and writes nothing.
- `--library DIR` copies a library's `presets/` and `desk/` into the scratch home; the source is only read.

**Desk templates.**
- `Library.desk_template` reads `hyperspace.desk/1` files from the `desk` group.
- A preset names a template with `desk_template` and keeps its overrides in `desk`; a dark row unmaps a template control.
- `expand_desk` builds the desk on load, and `compact_desk` writes the reference plus overrides on save.
- The reference is read from the loaded preset's file, so it survives an undo.
- A missing template gives a note, and the overrides alone become the desk.
- The plain-desk path is unchanged.

**Click-to-map, ranked.** `learn.ranked` is a pure function. It orders params in four tiers: routed, then moved off the group default, then of a module that is on, then already on the desk. A dead param is never offered as one of the preset's own, and the rest are grouped by group.

`ui_desk` draws the offer for a picked, mappable control on the desk's empty ground under the transport row (`OFFER`; a test proves it covers no control). It is a child window, not a popup, so the existing pick and let-go clicks and the page click keep working. A chip, "all params ▾", opens a popup with this preset's params and then a menu per group. Clicking an item calls `Learn.map_picked`.

## Files changed
- `hyperspace/library.py`, `hyperspace/preset.py`, `hyperspace/learn.py`, `hyperspace/ui_desk.py`
- New: `tools/desk_coverage.py`, `docs/plans/assets/24-party-fixes/desk-coverage.md`, `tests/test_desk_coverage.py`, `tests/test_desk_templates.py`
- Force-added fixtures: `tests/fixtures/desk-templates/desk/fixture-shape.json` and `tests/fixtures/desk-templates/presets/templated.json`
- `hyperspace/library/` is untouched (`git diff --stat 6af4c65 -- hyperspace/library/` is empty). No `.gitkeep` was needed, because an empty group lists `[]` without a folder.

## Tests and gates
```
$ uv run pytest -q
2022 passed, 2 skipped in 180.72s (0:03:00)
$ uv run ruff check .
All checks passed!
$ uv run python tools/desk_coverage.py --check; echo rc=$?
rc=0
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/c3scratch/home uv run hyperspace -ApplePersistenceIgnoreState YES
(the scratch home's config.toml was `[midi] enabled = false`, with no [library]; the fixture preset and template were in it)
ApplePersistenceIgnoreState: Existing state will not be touched. …
config: [midi] is now a [[devices]] entry (role = 'apc40', kind = 'midi') — see config.py
dream: mps · alias copy path · fp32 · weights /tmp/c3scratch/home/weights
exit=0
```
The suite went from 2002 to 2022 passed (20 new tests). No existing test or golden was changed.

## Coverage numbers
0 of 23 presets meet the bar of at most 4 dark or dead.
- The best are ACID, MANDALA, NOITA, TRIP and WAKE at 9 (29 mapped / 8 dark / 1 dead).
- The worst are hands-orbit, hands-play, legacy6 and WOVEN LATTICE at 15.
- S1–S8 are dark on every preset (8 each).
- K7 (`view.bmp_alpha`) is dead on all 23: either no bitmap file, or the faces are off.

The full table is in the PR body and the decisions file. Nothing was remapped.

## Self-review findings and concerns
- **Desk group name.** `desk` is also the name of a session *param* group (`desk.slew`, `desk.pad.*`). The template folder therefore sits where that group's (unused, strip-less) module presets would go. Templates are read only through `Library.desk_template`. I did not register a `Library.kind`, because doing so would change the session group's project-load bookkeeping. I flagged this as a register row; the alternative is a differently named folder.
- **Offer size.** At the default control-window size the offer is small, about 108×80 px with two or three items scrolling. It is larger on the big desk. No one has looked at it by eye.
- **Template editing.** There is no UI to write a template. Editing a template on disk does not re-apply the loaded preset; reloading it does.
- **Dead rule.** The rule reads bases, not live state: a faces-off preset's pattern knob is "dead" even though Faces is one invariant button away. This is the owner's own example, so it is kept.
- **Commit trailer.** It uses the session's attribution line (Claude Opus 5.5), following the system attribution reminder, rather than the brief's "Claude Fable 5.1".
- **For C7.** `ENGINEERING.md` §8 and the preset format text need the template key, the offer and the tool.

---

# Fix report, review round 1 (commit `af09547`, pushed; PR body updated)

## What changed

1. **The offer fits the small desk** (Important 1). File: `hyperspace/ui_desk.py`.
   - The offer child gets 4×3 px padding, 11 px type on the small desk (the labels' size on the big one) and 4×1 px item spacing.
   - The new `_offer_chip` draws the chip with 5×0 px padding, one line tall. It reads "all params ▾" beside the "D5 ON" head if that fits, else "all ▾" (`OFFER_SHORT`) beside it, else "all ▾" on its own line. It is never wider than the child.
   - The child's rect and the chip's rect are recorded in the desk state (`offer_box`, `offer_chip`).
   - Measured at `CONTROL_SIZE` with TRIP loaded and D5 picked:
     - the child spans x 280–387, y 771–850;
     - the chip is "all ▾" at x 328–356, y 774–785;
     - items are 12 px tall from y 788, so five show whole.
   - `test_a_picked_control_is_offered_this_presets_params_and_a_click_maps_it` now asserts that the small desk is up, that the chip lies inside the child, and that the first three items lie inside it.

2. **A save compacts against the template as the load read it** (Important 2). File: `hyperspace/preset.py`.
   - `Presets._at_load()` maps each preset name to (template name, the template rows the load expanded).
   - `_desk_part(name)` compacts against the held rows when the reference matches, else against the library's current file. It then records the same rows under the name being written, so a save-as followed by a save-over stays consistent.
   - The hand check now has a step for this: U.9 step 4.
   - New test `tests/test_desk_templates.py::test_a_template_fixed_after_the_load_changes_no_override_on_save`. It loads TEMPLATED, edits the template on disk (D3 changed, D5 added), polls the library, then:
     - saves as TEMPLATED 2 and checks the overrides equal the fixture's;
     - saves over TEMPLATED 2 and checks they are unchanged;
     - loads TEMPLATED 2 and checks the fix is there.
   - The test was confirmed to **fail with the cache disabled** (1 failed), then restored.

3. **Encoding** (minor 3). File: `tools/desk_coverage.py`. A new `read_report()` reads the committed report as UTF-8 with `newline=""`, and the write uses `encoding="utf-8", newline="\n"`. The test compares against `tool.read_report()`.

4. **`--check` takes no other output flag** (minor 4). File: `tools/desk_coverage.py`. `--check` combined with `--library` or `--stdout` is now an argparse error (exit 2). The freshness test asserts both combinations are refused.

5. **No default for the `desk` group** (minor 5). File: `hyperspace/library.py`. `Library.default_name(DESK)` returns None. New test `test_a_template_named_default_is_no_group_default`: a template named "default" leaves `defaults("desk")` at the fresh values with no error, and is still readable as a template.

6. **Docs notes.**
   - `compact_desk`'s docstring now names the case it loses: two spellings on one knob.
   - The decisions file gains rough edges for:
     - the as-loaded compaction;
     - `default_name`;
     - the two-spellings loss;
     - plan 13's `same()` seeing overrides (a note for C7);
     - the "on" tier's `.blend` / `.order` / `.target` (flagged as an owner call in U.10).
   - U.10 gains a step: open the chip's popup, wait past `PICK_S`, and check the panel still takes hover and clicks.

## Commands and output
```
$ uv run pytest -q tests/test_desk_templates.py tests/test_desk_coverage.py tests/test_ui_desk.py tests/test_presets.py tests/test_learn.py
123 passed in 13.34s
$ uv run pytest -q
2024 passed, 2 skipped in 138.69s (0:02:18)
$ uv run ruff check .
All checks passed!
$ uv run python tools/desk_coverage.py --check; echo rc=$?
rc=0
$ git diff --stat 6af4c65 -- hyperspace/library/
(empty)
```
The committed report is unchanged: the fixes change nothing it says.
