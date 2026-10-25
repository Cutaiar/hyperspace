# C1 report — Plan 24 C1: the desk you can trust

**Status:** DONE_WITH_CONCERNS (the concerns are below; none blocks the merge)
**Base:** `cd9106d` (after `git fetch origin plan-24-26-27-integration && git reset --hard FETCH_HEAD`), branch renamed to `plan-24-c1-desk-trust`.
**PR:** https://github.com/Cutaiar/hyperspace/pull/175 into `plan-24-26-27-integration`
**Decisions file:** `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/C1.md` (five register-row drafts, hand checks U.1–U.4, as-built notes, docs left stale for C7). The PR body is also saved beside it as `C1-pr-body.md`.

## Commits

- `5bc6521` Plan 24 C1: the two-handed save, loads that relight, toggles on both layers, a desk log
- `6121d75` Plan 24 C1: the map-shape and migration assertions follow the moved rows
- `4d4c64b` Plan 24 C1: tests for the desk you can trust, with a force-added fixture

## What was built

1. **The two-handed save.**
   - SAVE is track 8's clip stop (`apc40.SAVE = (N_CLIPSTOP, 7)`): an invariant `momentary` row on a new session param, `routing.SAVE_PARAM = "desk.save"`, registered in `register_desk`.
   - `MidiIO._save_tap` turns a bank pad's tap into `Param.save_into(k)` while SAVE is held. The pad does not load and no hold starts. On success the pad blinks for `BLINK_S`.
   - `library.Project.save_into(k)` now saves into filled slots as well. It writes a new preset named by `next_name` from the loaded preset, and the slot points at it. The old file is untouched and still listed; the trash is untouched.
   - `Project.save_empty(k)` is #158's hold (empty slots only) and is now `preset.select`'s `held`.
   - `_save_new` restores the old slot when the show can't be written.
   - `_enter` (power-up or reconnect) releases SAVE.
2. **Every load relights the whole desk.** In `MidiIO.redraw(load=…, whole=…)`:
   - `_dark_desk` sends dark every layout control no active row draws, on loads and at power-up.
   - Preset-layer faders always let go on a load. This changes register row 44.
   - Fresh rows are seeded with the control's last physical position (`_hw`).
   - Session faders keep row 44's rule.
3. **The render toggles on both layers.**
   - `apc40.TOGGLES` rows are invariant.
   - `routing.TOGGLE_DESK_ROWS` is added to `RETIRED_DESK_ROWS`, so the old factory toggle rows drop at load without a note.
   - `APC_NEW_ROWS` adds the four toggles and SAVE to a session file once.
   - `preset.file_desk` keeps the generator writing the toggle rows, so every factory file stays byte-identical (decision 23).
4. **The desk event log.** `midi.DeskEvent` and `midi.DeskLog` (20 entries) record presses, hold fires, saves and learns, each with its layer ("both" for invariant controls). The SYSTEM page shows it in a fold through `ui.desk_log_lines` / `Panel._desk_log`.

## Files changed

- Code: `hyperspace/{apc40,routing,library,params,midi,preset,ui}.py`, `hyperspace/bindings.default.json` (regenerated; it is outside `library/`).
- Tests changed: `tests/{test_desk,test_midi,test_routing,test_presets,test_plan12_presets,test_ui_desk,test_ui_routing}.py`.
- New: `tests/test_desk_trust.py` and `tests/fixtures/desk-trust/old-desk.json` (force-added).
- `git diff --stat cd9106d -- hyperspace/library/` is empty.

## Tests and gates

```
$ uv run pytest -q
1904 passed, 2 skipped in 105.73s (0:01:45)          # base: 1885 passed, 2 skipped
$ uv run ruff check .
All checks passed!
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/c1-smoke-home uv run python -c "import sys; sys.argv=['hyperspace']; from hyperspace.app import main; sys.exit(main())" -ApplePersistenceIgnoreState YES
exit=0   (stderr: "dream: mps · alias copy path · fp32 · weights /tmp/c1-smoke-home/weights")
```

The scratch home's config.toml has `[midi] enabled = false` and no `[library]` section; the fixture preset is in its presets folder.

The first plain `uv run hyperspace` hung. `sample` showed `glfwInit` blocked in AppKit's crash-history "reopen windows?" modal (`NSPersistentUIRestorer promptToIgnorePersistentState`), an environment issue from earlier Python crashes on this Mac. The workaround is the `-ApplePersistenceIgnoreState YES` launch argument, which changes no user defaults. Another agent's smoke run (worktree `agent-a0ba8845…`) looked stuck the same way when I checked; I did not touch it.

## Assertions consciously changed (all from decision 18's moved rows, or 23's file desk)

- `test_desk.py`:
  - `test_the_default_map_is_sorted_as_plan_13_says`: scene launch 1–4 are invariant, and SAVE is a new row.
  - `test_the_clip_stop_row_is_free`: clip stops 1–7 are free, and 8 is SAVE.
  - Three tests used scene launch 1–4 as their example preset-only control; they now use scene launch 5 or activator 1.
  - `test_invariant_controls_mean_one_thing_on_both_layers` is **untouched**.
- `test_midi.py`: the learned bar is 7 buttons (`BAR`), the knob-bump test uses activator 1, and the hold test sees SAVE as the one clip-stop row.
- `test_routing.py`: the row count is +1, migration notes and counts include the five rows (77 changed rows), `RETIRED_DESK_ROWS` includes `TOGGLE_DESK_ROWS`, and two examples moved.
- `test_presets.py` / `test_plan12_presets.py`: the factory files are compared via `file_desk`, and a loaded desk is the file's less the toggle rows.
- `test_ui_desk.py` / `test_ui_routing.py`: G6·8 is SAVE, and the sample row moved to scene launch 5.

## Self-review findings

- The fixes from review were all in my own new tests: a wrong glyph (slot 15 is G4·7), a loads check that `on_load` also fires on save, and a hold test that released the pad too early. The code needed none.
- The rows a load creates are fresh objects, so in practice preset-layer faders were already released on a real load. The row 44 change mostly makes that explicit and adds the position seed. I recorded this honestly in the row draft.

## Concerns

1. **Row 44's change is my reading of "every load relights the whole desk".** It is defined as: dark every undrawn layout control on load and power-up, release every preset-layer fader on load, and keep the session faders' hold. The orchestrator may have meant something else for the faders. It is easy to reverse (one condition in `redraw`).
2. **Outside the two named test files.** `tests/test_routing.py`, `test_presets.py`, `test_plan12_presets.py`, `test_ui_desk.py` and `test_ui_routing.py` changed assertions that follow mechanically from the moved rows and from decision 23. None is on the protected list. All are named in the PR body.
3. **Stale docs for C7.** `docs/ENGINEERING.md` §8 (the desk table, "Save on the desk", the fader-catch sentence), `DECISIONS.md` D6, the "desk never overwrites" row and the row 44 line are now stale. Per the brief they are left for C7 (listed in the decisions file §4).
4. **Smoke run.** It ran with MIDI disabled, so the SAVE path was not exercised in the app, only in the fake-port tests.
5. **Commit attribution.** My commit trailers use the session attribution in force for me (`Claude Opus 5.5`); the common brief's template says `Claude Fable 5.1`. Say if the orchestrator wants them amended.

## For B2

The new logic is in bounded pieces that B2 should carry with `MidiIO`:

- `MidiIO._save_tap` (the save) and `_log_press` / `_log`.
- `MidiIO.redraw` (`whole=`, `_dark_desk`, the `_hw` seed, the row 44 condition).
- `MidiIO._enter` releasing `desk.save`.
- `midi.DeskLog`.
- The model side: `Project.save_into` / `save_empty` and `Param.save_into`.

---

# Fix report — review round 1 (commit `77efecb`, pushed; PR #175 body updated)

## What changed

1. **(Important) SAVE can never be latched.**
   - `ui_routing.desk_target` excludes `SAVE_PARAM` beside `SHIFT_PARAM`. This covers ROUTING's target combo, "Learn desk" and "Learn pad".
   - `Learn.learn_control` and `Learn.learn_pad_button` refuse `desk.save` with `learn.SAVE_REFUSAL`. The learn stays armed, as with other refusals.
   - New `routing.save_refusal(b)`: only a `momentary` row may target `desk.save`.
     - `Bindings._check` (which `add`, `enable` and `replace_owner` go through) and `Bindings.bind` raise `ValueError`.
     - `set_desk` drops such a row with a note.
     - `Bindings.from_json` drops it with a note and marks the table changed, so a hand-edited `bindings.json` is written back once without it. A note, never a crash.
2. **A failed save blinks nothing.** When the show write fails, `Project._save_new` now returns `at is None`. `save_new` keeps True (the preset is in the list); a save into slot k answers False because the slot still names the old preset. `MidiIO._save_tap` then neither blinks nor logs success; it logs "save into slot k: did not land there". The failed-save test asserts no blink, the log line, and `save_into(2) is False`.
3. **Reconnect.** `MidiIO._enter` clears `_hw`.
4. **SAVE's absence is said.** New `routing.save_missing(rows)`: when no SAVE row exists and an owner's row holds `note:7:52`, `Bindings.load` prints "SAVE not added: note:7:52 is yours (<target>) — …" to stderr and appends it to `said`, the SYSTEM page line. This happens every launch and is not written to the file. (Not put in `notes`, which would force a rewrite on every launch.)
5. **Hover text.** `ui_presets.slot_tip` names SAVE + pad for empty and filled slots. Its four exact-text assertions in `tests/test_ui_presets.py` are updated.

New tests:
- `test_desk_trust.py::test_nothing_can_latch_save`, `::test_save_not_added_is_said`, `::test_a_reconnect_forgets_where_the_faders_were`
- `test_ui_routing.py::test_neither_shift_nor_save_is_a_desk_target`

The decisions file's as-built notes gained the lines for items 1 and 4.

## Covering tests

```
$ uv run pytest -q tests/test_desk_trust.py tests/test_desk.py tests/test_midi.py tests/test_ui_routing.py tests/test_learn.py tests/test_ui_presets.py tests/test_routing.py
259 passed in 14.92s
$ uv run pytest -q
1908 passed, 2 skipped in 110.07s (0:01:50)
$ uv run ruff check .
All checks passed!
$ git diff --stat cd9106d -- hyperspace/library/
(empty)
```
