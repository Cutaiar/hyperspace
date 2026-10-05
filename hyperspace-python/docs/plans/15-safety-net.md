# Plan 15 — Safety net and the bank

This plan gives the app a way back from mistakes. ⌘Z / Ctrl+Z undoes the
last gesture or load, ⌘⇧Z / Ctrl+⇧Z redoes it, and a preset file that a save
or a delete would destroy is copied to a trash folder first. One press (the
Home key, or OVERDUB on the APC40) goes back to the show's "starts on"
preset. The crossfader dims the finished picture. On the desk, holding the
clip-stop row saves the live state as a new preset into the next empty slot
and never overwrites one. On the PRESETS page, right-clicking a slot offers
"put preset here…" and "clear slot".

## What was built

### Undo and redo

**At the machine.** ⌘Z or Ctrl+Z takes back the last step; ⌘⇧Z or Ctrl+⇧Z
redoes it. A step is one gesture or one replacing action:

- A gesture is a slider drag, a knob sweep, a typed value or a toggle. It
  ends after 0.4 s with no change.
- A replacing action is a preset or show load by any road, a Learn
  landing, an Unbind, a route, desk-row or macro-subscriber ×, Replace in
  the Replace / Keep prompt, home, or an effect reorder.

The footer shows "undid …", "redid …" or "nothing to undo" for 4 s on every
page. Nothing a hand, a band or an LFO moves makes a step. Undoing a load
also brings back the loaded preset's name, its routes, its desk rows and
its macros. Then Save writes the earlier preset, not the one you undid.
Undo never writes a file. While an imgui text field is typing, Ctrl+Z
belongs to the field.

**Code.** All in `hyperspace/undo.py`, which imports nothing from the
package:

- **`Undo.tick(now)`** runs once a frame in `app.frame`, after
  `router.follow_macros` and before the hands poll. It compares a
  fingerprint with last frame's. The fingerprint holds:
  - the bases of the watched params (`watched`: persisted, not an alias,
    not a trigger, not in `EXCLUDED_GROUPS`, which is `tempo`);
  - the performer rows and the preset-layer rows (`ROW_FIELDS`);
  - `Bindings.macros_doc`.

  Floats count as equal within `REL_TOL` / `ABS_TOL`. Constants:
  `SETTLE_S` 0.4, `LIMIT` 100 steps, `ABSORB_FRAMES` 2, `PASSES` 3.
- **`undo.push(label, *, load=False)`** is called before each replacing
  action: `Presets.load_doc`, `Project.load`, `Project.new`,
  `Project.home`, `Library._apply_doc`, `Library.reset`,
  `Learn.learn_control`, `Learn.learn_source`, `Learn._place`,
  `Learn.unbind`, `ui_routing.answer` / `desk` / `macros` / `page`, and
  the FX page's reorder drop (`ui_fx.REORDER`). If a site does not push,
  the watcher still makes the step, with a label built from the
  difference.
- **A restore** (`Undo._restore`) puts back only what differs, in this
  order:
  1. `Bindings.set_routes`;
  2. `Bindings.set_desk(rows, load=False)`, which keeps the layer that is
     up and the faders' catch;
  3. `set_macros`;
  4. the bases through `Registry.restore`;
  5. `Router.sync_macros`;
  6. on a load step, the library's marks (`library.Marks`,
     `Project.mark` / `remark` / `same_show`).
- **Band layouts.** Adding, removing or moving a band is not a step. A
  strip's stored values go back only onto the band layout they were made
  on. Otherwise the status says the strips were left.
- **The app.**
  - `app.main` builds the `Undo` after the startup preset, so a launch
    starts with an empty stack.
  - The keys are the `LOOP_KEY_ROWS` `SUPER+Z`, `SHIFT+SUPER+Z`,
    `CONTROL+Z` and `CONTROL+SHIFT+Z`. They fire the triggers `edit.undo`
    and `edit.redo` (`params.build_registry`, group `ui`, not modulatable).
  - `routing.MODIFIERS` includes `CONTROL` (`app.Keys.control`).
    `Router.keys` fires a row only when its modifiers equal the held
    modifiers that some row on that key names, so ⌘⇧Z fires redo alone.
  - The footer line is `Panel._message` (`ui.MESSAGE_S` = 4 s).

**Tests.**
- `tests/test_undo.py` covers the core, among them:
  - `test_a_slider_drag_is_one_step_and_undo_sets_only_that_param`
  - `test_a_knob_turn_on_the_desk_is_one_step`
  - `test_a_performer_moving_makes_no_step`
  - `test_a_preset_load_is_one_step_by_every_road`
  - `test_save_after_undoing_a_load_writes_the_earlier_preset`
  - `test_an_idle_app_makes_no_step`
  - `test_an_action_that_changes_nothing_keeps_the_redo`
  - `test_a_row_that_undo_brings_back_picks_up_afresh`
  - `test_a_load_right_after_another_action_is_its_own_step`
  - `test_undoing_a_scene_pick_names_the_band_preset_it_was_on`
- Elsewhere:
  - `test_learn.py::test_a_learn_is_one_undo_step`
  - `test_midi.py::test_an_unbind_is_one_undo_step`
  - `test_ui_routing.py::test_a_route_delete_and_a_replace_are_undo_steps`
  - `test_desk.py::test_undoing_a_desk_row_redraws_and_keeps_the_layer_and_the_faders_catch`
  - `test_routing.py::test_a_chord_fires_only_its_own_row`
  - `test_routing.py::test_an_older_file_gets_the_undo_keys_where_they_are_free`
  - `test_ui_shell.py::test_the_footer_says_what_was_undone`
- `test_app_boundary.py` `ORDER` holds `undo.tick` after
  `router.follow_macros`.

**Demo.** `uv run python tools/undo_demo.py` runs headless on a temp home.
It covers a drag, a knob sweep, two hands, a load, undo and redo, the trash
and the tick's cost. `tools/undo_shot.py` shows the footer line in a hidden
window.

### The trash

**At the machine.** A preset is copied to `<home>/trash/<folder>/` before a
save overwrites it or a delete removes it. The copy is named
`<stem>.<YYYYMMDD-HHMMSS>[-n].json`. Saving with nothing changed trashes
nothing. The preset list on the PRESETS page shows the trash and can
restore or empty it; plan 19's record covers that.

**Code.** `library.to_trash(path, root)` creates each copy exclusively, so
nothing in the trash is overwritten. `Library.save_as` and `Library.delete`
call it.

- If the copy fails on a save, the save still happens and
  `Library.warning` says the old file was not kept.
- If the copy fails on a delete, the delete is refused (`LibraryError`).
- `Library.groups()` skips `trash` (`library.TRASH`).
- Saves and deletes are not undo steps: the trash is their safety net.

**Tests.** In `test_library.py`:
- `test_a_save_over_a_preset_keeps_the_old_file_in_the_trash`
- `test_a_delete_keeps_the_file_in_the_trash_or_does_not_delete`
- `test_a_save_that_changes_nothing_trashes_nothing`
- `test_two_trashings_in_one_second_do_not_collide`
- `test_the_trash_is_no_group_and_is_never_watched`

### Home

**At the machine.** The Home key (fn+← on a laptop) or OVERDUB (B11) on the
APC40 loads the show's "starts on" preset. OVERDUB does this on both desk
layers, and its LED is lit while the show names a "starts on". Home is one
undo step, labelled "home → <name>". With no "starts on" set, it loads
nothing and the footer says "home: this show names no 'starts on' preset —
pick one on the PRESETS page". On the PRESETS page the picker is labelled
"starts on / home".

**Code.**
- `Project.home()` (`library.py`). The warning text is
  `library.HOME_UNSET`, said through `Library.say`. Home pushes an undo
  step only when the preset file exists, then calls `load_startup()`.
- The trigger `preset.home` is in `params.build_registry`: group `preset`,
  modulatable, `lit` while `bank.startup` is set.
- The key row is `("HOME", "preset.home", "fire")` in
  `routing.LOOP_KEY_ROWS`.
- On the desk, `_note("preset.home", N_OVERDUB)` in `apc40.DEFAULT_MAP`
  has no layer, so it is invariant: Learn refuses it, and a preset's desk
  row on it is dropped.
- `ui_presets.starts_on` draws the picker; `set_starts_on` writes it.

**Tests.**
- `test_presets.py::test_home_loads_what_the_show_starts_on`
- `test_presets.py::test_home_with_no_starts_on_says_so_and_loads_nothing`
- `test_presets.py::test_home_is_one_undo_step`
- `test_desk.py::test_overdub_is_home_on_both_layers_and_is_lit`
- `test_routing.py::test_an_older_file_gets_home_where_it_is_free`
- `test_ui_presets.py::test_starts_on_reads_starts_on_home`

**Demo.** `uv run python tools/home_demo.py`.

### Master dim on the crossfader

**At the machine.**
- The crossfader dims the finished picture: the scene, the look-back,
  every effect and the ghost hands together. Left is black and right is
  full.
- Every launch starts at full. A preset load never moves the dim. The
  crossfader has soft pickup: if it is parked at the left at launch, it
  does nothing until you bring it up to the current value.
- The OUTPUT page's first row is "Master dim".
- While the dim is under full, every page's footer reads `dim 40%` (or
  `dim black`) in the warning colour.

**Code.**
- **The param.** `output.dim` is registered in `Output.register`
  (`overlay.py`): range 0–1, group `output`, `persist=False`,
  `modulatable=False`, no config key. Its text comes from
  `Output._dim_text`, which reads "black" only at 0 and "100%" only at 1.
- **The pass.** `app.frame` copies the value into `Renderer.dim`.
  `Renderer._compose` (`render.py`) runs `dim_pass` last for each view,
  with the factor master × that output's own `output.N.dim`. At 1 the pass
  does not run.
  - On an opaque ground the colour scales and the alpha is left as it
    was.
  - On overlay's see-through ground the colour and the alpha both scale.
  - If the driver refuses the dim's program, `Renderer.dim_error` is set
    and the OUTPUT page says the picture is not dimmed.
- **The crossfader row.** `_cc("output.dim", CC_XFADE, 0, ring=0)` has no
  layer, so it is invariant.
  - When an older `bindings.json` still has the factory row
    `cc:0:15 → overlay.bg`, `routing.APC_REMAP` swaps it for this row.
    `routing.backup` saves a copy of the file first.
- **The faders on a load.** `MidiIO.redraw(load=True)` clears a fader's
  catch only in these cases:
  - the param is gone;
  - the fader has no last write or no last reading (`Binding.last_hw`);
  - the param is more than `PICKUP_TOL` from either of them.

  So the crossfader, S1–S8 and SM keep their hold through a preset load.

**Tests.**
- In `test_render.py`:
  - `test_dim_at_one_is_the_old_frame_exactly`
  - `test_dim_scales_the_colour_and_leaves_an_opaque_grounds_alpha`
  - `test_dim_at_zero_is_black_and_opaque`
  - `test_dim_is_after_the_effects_and_the_ghost_hands`
  - `test_dim_fades_a_see_through_ground`
  - `test_the_history_never_holds_the_dim`
  - `test_a_dim_program_the_driver_refuses_leaves_the_frame_and_says_why`
- Elsewhere:
  - `test_overlay.py::test_dim_is_a_rig_setting_that_starts_bright`
  - `test_midi.py::test_the_crossfader_dims_with_soft_pickup`
  - `test_desk.py::test_the_crossfader_keeps_its_hold_across_a_preset_load`
  - `test_routing.py::test_an_old_crossfader_row_moves_to_the_dim_with_a_backup`
  - `test_ui_shell.py::test_the_dim_is_first_on_output_and_the_footer_says_so_while_dimmed`

**Demo.** [`assets/15-safety-net/dim.png`](assets/15-safety-net/dim.png)
shows one offscreen frame at dim 1, 0.5, 0.15 and 0. It is written by
`uv run python tools/dim_shots.py`.

### Save-as on the desk; "put preset here…" and "clear slot"

**At the machine.**
- **Hold.** Hold any of the eight clip-stop buttons (G6·1–G6·8, the
  SAVE AS bar) for 0.6 s and the live state is saved as a new preset:
  - The name comes from the loaded preset: TRIP → TRIP 2, TRIP 2 → TRIP 3.
  - It goes into the next empty slot of the twenty-four-slot bank.
  - It becomes the loaded preset.
- **Tap.** A tap does nothing. The bar lights while it is held.
- **Lights after a save.** The bar and the new slot's pad blink for
  1.5 s.
- **Footer.** It says `saved TRIP 2 → F6`, or `→ slot 12` for a far slot.
- **Full bank.** The preset is still saved, and the footer says "the bank
  is full: it is in the preset list".
- **Never overwrites.** The desk never writes over a preset.
- **PRESETS page.** Right-click any slot for:
  - **put preset here…**: a scrolling list of every preset;
  - **clear slot**: empties the slot; the preset stays in the list.

  Both write the show file at once and delete no preset file.

**Code.**
- **The rows.** `apc40.DEFAULT_MAP` has
  `_note("preset.save_new", N_CLIPSTOP, k, op="hold")` for k = 0–7. They
  have no layer, so they are invariant.
  - `hold` is in `routing.OPS`, and `routing.act` ignores it.
  - For an older `bindings.json`, `routing.APC_NEW_ROWS` adds these rows,
    and the OVERDUB row, wherever nothing else uses the source.
- **The hold** (`midi.py`).
  - Timing: `HOLD_S` 0.6 and `BLINK_S` 1.5.
  - `MidiIO._handle` records a press in `_holds`, and `_light_bars` lights
    the bar.
  - `_fire_holds` is called from `poll`. It fires the target once per
    target while the button is still held.
  - Then `_blinks` makes `feedback` send `apc40.blink_of(number, on)`.
  - If the save returns False, nothing blinks.
- **The save.** The trigger is `preset.save_new` (group `preset`, not
  modulatable).
  - `library.next_name(base, taken)` builds the name. `Project.save_new()`
    passes it `taken`: the slugs of the file stems, every listed name and
    the bank's names.
  - `Project.next_empty()` reads the bank's own length.
  - `Project.put_slot` and `clear_slot` go through `_set_slot`. If the
    show file cannot be written, `_set_slot` restores the slot as it was.
  - The bank-full warning (`library.BANK_FULL`) is withdrawn by `_room`
    the next time the bank changes.
- **The menu.** `ui_presets._slot_menu` draws it through
  `Panel._ctx(..., extra=)`. Its list is at most `PUT_ROWS` = 12 rows tall
  before it scrolls.

**Tests.**
- In `test_midi.py`:
  - `test_a_hold_fires_once_at_the_hold_time_while_held`
  - `test_a_tap_fires_nothing`
  - `test_the_bar_is_one_control`
  - `test_the_bar_lights_while_held_and_the_new_slots_pad_blinks`
- `test_desk.py::test_the_clip_stop_row_is_invariant`
- In `test_library.py`:
  - `test_next_name_counts_on_from_a_trailing_number`
  - `test_next_empty_reads_the_banks_own_length`
- In `test_presets.py`:
  - `test_save_new_never_overwrites`
  - `test_save_new_fills_the_next_empty_slot_and_becomes_the_loaded_preset`
  - `test_save_new_on_a_full_bank_saves_to_the_list_and_says_so`
  - `test_the_new_slot_loads_from_the_preset_row`
  - `test_put_and_clear_slot_write_the_show_and_delete_no_file`
  - `test_the_bank_calls_are_no_undo_step`
- `test_routing.py::test_an_older_file_gets_the_save_bar_where_it_is_free`
- In `test_ui_presets.py`:
  - `test_a_slots_menu_offers_put_and_clear`
  - `test_the_footer_says_a_library_line_again`

**Demo.** `uv run python tools/save_as_demo.py` runs on fake ports and
prints the LED velocities.

## Not verified by a person

No key, APC40 control, projector or glass has been tried at the machine.
That is hand checks 48–57 (group K) in
[`11-hand-checks.md`](11-hand-checks.md); see also
[`../TESTING-GUIDE.md`](../TESTING-GUIDE.md). These are still open:

- whether CC 0 is the crossfader's left end (check 55);
- the mk1's blink velocities;
- whether fn+← reaches the app as Home.

## Known rough edges

- Undoing a show load does not restore the tempo, because the clock is not
  watched (decision register row 36). The show's dirty dot can then light.
- A clip-stop or OVERDUB row deleted from `bindings.json` comes back on the
  next launch (`APC_NEW_ROWS`). To turn one off, keep its row with
  `"enabled": false`.
- The on-screen desk lights the SAVE AS bar while it is held but does not
  blink, and the cheat sheet does not mention the bar.
- A `bindings.json` migrated from a pre-plan-09 `midi_map.json` gets the
  OVERDUB and clip-stop rows one launch later
  (`test_routing.py::test_old_midi_map_migrates_into_bindings_json`).
