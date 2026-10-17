## What was built

Plan 24 C1, "the desk you can trust" (decisions 18 and 23, owner).

- **The two-handed save.** SAVE is **track 8's clip stop** (`apc40.SAVE`, a `momentary` row on the new session param `desk.save`, invariant, free since #158). Hold SAVE and tap a bank pad (rows 1, 4, 5), and the live state is saved into that pad's slot:
  - **empty slot:** #158's save;
  - **filled slot:** a **new** preset, named the way `save_new` names them (TRIP → TRIP 2). The slot points at the new preset, and the old preset keeps its file byte for byte and stays in the list, unpadded.
  - In both cases nothing is overwritten and nothing goes to the trash. The pad blinks, and the new preset is the loaded one.
  - A SAVE press with no pad does nothing. Everything works the same under SHIFT (SAVE and the pads are invariant). A tap under SAVE neither loads the pad nor starts its hold.
  - Code: `library.Project.save_into` grows the filled case, and `Project.save_empty` is #158's hold (empty slots only), which stays beside it. The new `Param.save_into` is wired on `preset.select`, and the adapter side is one handler, `MidiIO._save_tap`.
  - A reconnect releases SAVE in case its note-off was lost.
- **Every load relights the whole desk** (`MidiIO.redraw`). On every load and at power-up, every control of `apc40.LAYOUT` that no active row draws is sent dark (`_dark_desk`), not only the controls some row once named. **This changes register row 44:** every fader the new preset binds (a preset-layer row) lets go on a load whether or not the load moved its param. A fresh row starts from where its control physically is (`_hw`), so a fader already sitting on the value catches on its first move. The session's faders keep row 44's rule.
- **The render toggles on both layers.** Points, lines, faces and rotate (scene launch 1–4) are invariant rows (D6's list grows by four). Their LEDs show the live state on either layer, right after a load too. Scene launch 5 (reset view) stays on the preset layer.
  - An older preset's four factory toggle rows drop at load **without a note** (`routing.TOGGLE_DESK_ROWS` ⊂ `RETIRED_DESK_ROWS`). An owner's own row on one of those controls drops **with** the usual note.
  - A `bindings.json` gains the five new rows once (`APC_NEW_ROWS`, "the APC40 map of plan 24"), only where nothing already uses the control.
- **A desk event log** (`midi.DeskLog`, its own small class). It keeps the last twenty desk events: the press, what it did, and the layer it was read on ("both" for an invariant control). Holds that fired and two-handed saves are logged too. It shows on the SYSTEM page under **midi** as a fold, through its own helper (`ui.desk_log_lines` / `Panel._desk_log`).

## No library file changed (decision 23)

`git diff --stat -- hyperspace/library/` is empty. The factory files still hold the four toggle rows, so the generator keeps writing them: `preset.file_desk` is the fresh desk plus those rows, and it is `Factory.desk`'s default and `write_factory`'s fallback. `fresh_desk` (what a load leaves) loses them. `hyperspace/bindings.default.json` (outside `library/`) is regenerated with the five rows.

## Boundary assertions consciously changed (all from decision 18's moved rows)

- `tests/test_desk.py::test_the_default_map_is_sorted_as_plan_13_says`: scene launch 1–4 are sorted invariant, and SAVE is a new invariant row (decision 18).
- `tests/test_desk.py::test_the_clip_stop_row_is_free`: clip stops 1–7 stay free, and 8 is SAVE (decision 18).
- `tests/test_desk.py`: `test_shift_release_never_reevaluates_a_held_button`, `test_a_control_that_loses_its_row_goes_dark` and `test_an_unmapped_control_is_dark_and_does_nothing` used scene launch 1–4 as their example preset-only control. They now use scene launch 5 or activator 1. Same meaning (decision 18).
- `tests/test_desk.py::test_invariant_controls_mean_one_thing_on_both_layers`: **untouched**.
- `tests/test_midi.py`: the learned SAVE AS bar is seven buttons (`BAR`), since track 8's clip stop is SAVE. `test_a_knob_bump_during_a_hand_learn_does_its_own_job` uses activator 1 for its preset pad. `test_holding_an_empty_bank_pad_saves_into_that_slot` sees SAVE as the one clip-stop row (decision 18).
- Outside the two named files (not on the protected list, named here for the record):
  - `tests/test_routing.py`: the map's MIDI row count is +1 (SAVE), and the migration notes/counts include the five new rows. `RETIRED_DESK_ROWS` now also holds `TOGGLE_DESK_ROWS`. Two examples moved off view.lines and the clip-stop 8 control (decision 18).
  - `tests/test_presets.py` and `tests/test_plan12_presets.py`: the factory files are compared through `file_desk`, and a loaded factory desk is the file's less the toggle rows (decision 23). The sample desk row is on scene launch 5 (decision 18).
  - `tests/test_ui_desk.py` / `tests/test_ui_routing.py`: G6·8 is SAVE, and the sample row is on scene launch 5 (decision 18).

## Decisions I took (drafts in the decisions file)

1. SAVE is a momentary row on a session param, `desk.save`, rather than a note the adapter tracks. That lets the on-screen desk draw it and lets B2 carry it as a port. A reconnect releases it.
2. A filled slot's new preset is named from the **loaded** preset, as `save_new` does.
3. The four factory toggle rows drop quietly. The generator keeps writing them (`file_desk`) until the owner's creative pass regenerates the files.
4. Row 44 changes: preset-layer faders always let go on a load, and fresh rows are seeded with the control's physical position. The session faders keep row 44's rule.
5. The whole-layout dark pass runs on loads and at power-up, not on SHIFT.
6. The desk log's shape: presses, hold fires and two-handed saves, but not knob or fader moves. It keeps twenty, in a fold on the SYSTEM page.
7. A failed two-handed save blinks nothing and is logged. A hold on a filled pad is logged as "nothing saved (a filled pad only loads)".

## Review fixes (round 1, `77efecb`)

- **SAVE can never be latched.**
  - `desk.save` is no desk target: `ui_routing.desk_target` excludes it beside SHIFT, which covers ROUTING's combo, "Learn desk" and "Learn pad".
  - `Learn.learn_control` and `learn_pad_button` refuse it (`learn.SAVE_REFUSAL`).
  - `routing.save_refusal` refuses any non-`momentary` row on it:
    - `Bindings._check` and `bind` raise `ValueError`;
    - `set_desk` drops such a row with a note;
    - a hand-edited `bindings.json` loses it with a note and is written back once.
- **A failed save blinks nothing.** When the show file cannot take the slot, a two-handed save (or the hold) into it now answers False from `Project._save_new`. Nothing blinks, and the log says "did not land there". `save_new` (the next empty slot) is unchanged.
- **Reconnect.** `MidiIO._enter` forgets every fader position (`_hw`) on a (re)connect.
- **SAVE's absence is said.** When the owner's `bindings.json` holds track 8's clip stop, "SAVE not added: note:7:52 is yours (…)" goes to stderr and the SYSTEM page line (`routing.save_missing`) at every launch. It is never written into the file.
- **Hover text.** `ui_presets.slot_tip` names SAVE + pad on both empty and filled slots. Its two assertions in `tests/test_ui_presets.py` are updated.
- **New tests:**
  - `test_desk_trust.py::{test_nothing_can_latch_save,test_save_not_added_is_said,test_a_reconnect_forgets_where_the_faders_were}`;
  - `test_ui_routing.py::test_neither_shift_nor_save_is_a_desk_target`;
  - the failed-save test now asserts that nothing blinks.

## Fixtures

`tests/fixtures/desk-trust/old-desk.json` is **force-added** (`git add -f`; `tests/fixtures/` is gitignored). It is a preset saved before C1, loaded through a scratch library.

## Gates

```
uv run pytest -q            1908 passed, 2 skipped in 110.07s   (base cd9106d: 1885 passed, 2 skipped; round 1)
uv run ruff check .         All checks passed!
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/c1-smoke-home   exit 0
```

About the smoke run: the scratch home's config.toml has `[midi] enabled = false` and no `[library]` section, and the fixture is in its presets folder. Run plainly, the app sat at a macOS "reopen windows?" crash-history alert inside `glfwInit`, an environment issue. It was run as `uv run python -c "…main()" -ApplePersistenceIgnoreState YES` with `sys.argv` reset, which touches no user defaults.

Not done: the acceptance "ten times in a row on the real APC40" is a hand check (U.1 in the decisions file). The tests prove the same thing ten times with fake ports.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01B185QGNNV4gpnBQEBD6k3z
