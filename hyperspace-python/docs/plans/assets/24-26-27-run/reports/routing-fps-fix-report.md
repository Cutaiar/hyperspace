# ROUTING fps fix: report

- **Status:** DONE. PR https://github.com/Cutaiar/hyperspace/pull/198 into `plan-24-26-27-integration`.
- **Base:** a661fa0. The branch is `review-routing-fps`.
- **Commits:**
  - ccff6db: the code and the tests.
  - 3e9be8a: the ledger line in `progress.md`.

## Fix

1. **The source list is built once per draw.** `page()` builds `_sources()` once before the route loop and stores it as `st["sources"]`. `_row()` reads `st.get("sources") or _sources(...)`, and `page()` clears the stash after the loop.
   - `_row`'s signature is unchanged. `test_a_filtered_page_draws_only_matching_lines_and_keeps_its_ids` replaces `_row` with a 4-argument stub, and that test had to pass without edits.
   - The list and its order are the same as before.

2. **`unmapped()` remembers its last answer.** It is memoized in a one-slot module dict `_DARK = {"sig", "rows"}` and returns a copy of the list.
   - The signature is `(table.profile, tuple(midi_roles), tuple((b.source, b.layer, b.enabled, b.target) for b in table.bindings))`.
   - Why the signature covers everything the answer depends on:
     - `factory_desk(profile)` reads the profile.
     - `is_invariant` → `is_primary(b.device)` reads `midi_roles`. In practice factory rows are always unqualified, but the field is included anyway.
     - `overlaps` compares `is_midi`, `kind`, `device`, `channel` and `number`. All of them are parsed from `source`.
     - `invariant_rows` reads `is_midi`, `layer` and `enabled`.
     - `desk()` reads `is_midi` and `layer`.
     - `target` is not read anywhere in the answer. It is included because it is cheap and conservative.
     - `table.layer`, the latch that is up, does not affect the answer: `desk()` is always the preset-layer rows.
   - The key is built from field values, never from which object a row is. A rebuilt row with the same fields is a cache hit; a changed field is a miss.
   - No serial was usable. `layer_serial`, `desk_serial` and `redraw_serial` do not move on `add`, `enable`, `remove` or a profile change.

## Tests (`tests/test_ui_routing.py`, written first; both failed before the fix)

- `test_the_routing_page_builds_its_source_list_once_a_draw`: 12 or more routes, two draws, `_sources` called exactly twice. Before the fix it was called 24 times.
- `test_the_dark_controls_are_worked_out_again_only_when_the_table_changes`:
  - `preset_controls` runs once across two draws.
  - It is not run again after `bindings` is rebuilt with `replace()` (equal copies).
  - It runs again after each of the following, and each time the result equals an uncached scan:
    - (a) `Learn.learn_control` on a dark control;
    - (b) a layer-None session row added on a dark control, then `table.enable(row, False)`;
    - (c) `lib.load` of a preset whose desk maps a dark control;
    - (d) `table.profile = "none"`, after which the dark list is empty.
- The existing ROUTING tests pass unchanged (29 in the file).

## Measurement

Investigator's `tools/run2.sh` with `TREE` set to this worktree, scratch home `routing-fps/branch/home`, party-trip, 600 frames, no devices. The "before" run used a661fa0's `ui_routing.py` put back in the same tree.

| run | page | panel ms/frame (mean) | p95 | frame ms | fps |
|---|---|---|---|---|---|
| before | ROUTING | 17.97 | 19.23 | 23.12 | 43.2 |
| after | ROUTING | **3.29** | 3.62 | 8.34 | 119.9 (vsync) |
| after | CAMERA | 1.14 | 1.26 | 8.33 | 120.1 (vsync) |

The target was under 4 ms on ROUTING; this run measured 3.29 ms.

## Gates (on ccff6db, with the ruff nit fixed in the test before the commit)

- `uv run pytest -q`: 2195 passed, 2 skipped.
- `uv run ruff check .`: All checks passed.
- `uv run pytest tests/test_golden_frames.py -q`: 7 passed. No golden images moved.
- `git diff --stat a661fa0 -- hyperspace/library/`: empty.

## Concerns

- The cached dark rows are the same `Binding` objects on every frame. Nothing on the page mutates them; they are only drawn, searched and marked. If a later feature edits a dark row in place, it will need to copy the row first.
- The module-level memo holds one slot. If two tables alternate, every call is a cache miss and the cost is the same as today. It is never wrong.
