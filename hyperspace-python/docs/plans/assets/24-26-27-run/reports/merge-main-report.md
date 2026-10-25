# Merge main (2026-10-15) into plan-24-26-27-integration

Branch `merge-main-20261015`, reset to origin/plan-24-26-27-integration at a661fa0, merged origin/main 6682036 (#196 02cf7eb, #197 07dc2bd). Merge commit **d30d074**.

## Files

- **hyperspace/routing.py** (auto-merged; checked by hand). Main's `PAD_NEW_ROWS` table, the dropped `PAD_REMAP` row for `pad:MENU → preset.save_new`, the `padmap()` row and the `remap_factory` loop all landed next to the branch's `FADER_SHIFT_ROWS` branch (plan 24 C2) and its device-qualified MIDI model (plan 27 B2). The loop runs after APC_NEW_ROWS and before KEY_NEW_ROWS, and it checks `used` (the sources of the table after the remaps). Pad rows on the branch carry no device qualifier: only MIDI rows take `@role` (`Binding.device` is "" for `pad:`), and `bindings.default.json`'s pad rows are plain `pad:<BUTTON>`. So main's new row `{"source": "pad:MENU", "target": "preset.save_new", "op": "hold"}` already has the branch's form. Nothing changed in source.
- **hyperspace/bindings.default.json, gamepad.py, ui.py** (auto-merged). The factory file has the `pad:MENU` row. gamepad.py has SHARE = 15, BUTTONS["SHARE"] and N_BUTTONS = 16. The CHEATSHEET line `("hold START", ...)` sits in the branch's ui.py at line 453. The branch's desk SAVE (two-handed, `note:7:52 → desk.save`) and main's pad START hold both stay as factory rows.
- **tests/test_routing.py** (the only textual conflict, 4 hunks). Both sides' assertions are kept and summed:
  - factory table: `len(t.of("pad")) == 9` (main) and `len(t.midi()) == 113+6+1+4+1` (branch, + plan 24's SAVE row).
  - schema-1 migration: the branch's plan-24 note asserts are kept, `migrated … (2 rows dropped, 86 rows changed)` (branch 85 + main's START row; main had 73 = base 72 + 1), and `len(t.notes) == 9+17+26+4+2+16+5+8+1`.
  - `remap_factory` unit test: main's `("pad:MENU", "preset.save_new") in by` is kept, with `["added"] * (17+4+2+16+5+1)`.
- **tests/test_ui_shell.py** (auto-merged). Main's `_PADS["hold START"]` is kept. The branch's SYSTEM-page assertion `pad · gamepad · lost · 21 sources` is now **22 sources**, because #197 added SHARE to `gamepad.BUTTONS` and `PadDevice.sources` lists every button.
- **tests/test_devices.py** (semantic overlap, not touched by main). For the same reason, `make(gamepad).sources == 21` and the `connected · 21 sources · usb: AX.1` line are now **22**.
- **tests/test_pad_learn.py** (auto-merged, main's side as is).
- **tools/pad_probe.py** (new from main). It uses only `gp.Pad`, `gp.AXES`, `gp.BUTTONS` and `gp.HATS`, and all of them exist on the branch. `uv run python tools/pad_probe.py --help` prints its usage.
- hyperspace/library/: no diff against either parent.

## Changed assertions and why

1. test_routing: pad count 8 → 9, migration "rows changed" 85 → 86, notes sum + 1, remap_factory added + 1. Main's START row joins the branch's counts.
2. test_ui_shell `test_system_page_shows_one_line_per_device`: 21 → 22 sources (SHARE in gamepad.BUTTONS).
3. test_devices `test_the_kinds_table_maps_each_kind_and_make_sorts_an_entry`: 21 → 22 (SHARE).
4. test_devices `test_lines_and_the_system_pages_text`: 21 → 22 (SHARE).

## Gates (hyperspace-python/)

- `uv run pytest -q` → 2194 passed, 2 skipped
- `uv run ruff check .` → All checks passed!
- `uv run pytest tests/test_golden_frames.py -q` → 7 passed; `uv run python tools/golden_frames.py` → all 556 frames match their goldens (Apple M3 Max). Nothing re-recorded.

## Smoke run

The scratch home `/Users/dallman/.claude/jobs/b8e1c57e/tmp/smoke/merge-main/home` was set up as in stream C: a config.toml with no [library] section, `[dream] enabled = false`, and only the pad listed (`enabled = false`). Its `bindings.json` is the factory file at the merge base 56c7d44 (schema 3, 153 rows, before plan 24 and before #196). It was saved at `../bindings.before.json`. No test fixture of a pre-run file exists: test_device_inputs' "pre-run" file is today's factory file.

`HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES` exited 0. stall.log is empty and there was no error. stderr (`../smoke.log`) shows:
- a backup kept as bindings.json.bak-v3
- 8 rows "moved cc:N:7 → … to the SHIFT layer (the APC40 map of plan 24 …)"
- 5 rows "added note:0:82–85 / note:7:52 … (the APC40 map of plan 24)"
- "added pad:MENU → preset.save_new (the pad layout of 2026-10-14)"
- "updated … (14 rows changed)"

The rewritten file has 159 rows, and its row set equals today's bindings.default.json exactly. It has no duplicate (source, layer) and exactly one `pad:MENU` row. A second run of 60 frames printed nothing: no migration, no note.

## Concerns

- No hardware hand check: held START on a real pad, and SHARE on a pad that has one.
- A file where the owner already put `pad:MENU` on something keeps that row (`remap_factory` skips a used source; main's intent).
