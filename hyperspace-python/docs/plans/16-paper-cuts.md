# Plan 16 — Paper cuts

Small fixes from a session at the machine, none of which adds a registry
param, page or menu item. The cheat sheet is off at launch. An effect chip
on the FX page has two parts: a switch, and a name that opens the effect
without switching it. An open effect that is not running says why. Both
windows open where they were last time, or on the screen the config
names. The instance count goes down to zero. The dream's layer cannot be
the target of a route. And four smaller fixes: a footer line said twice
shows twice, round-off no longer lights the dirty dot, the desk diagram
no longer jumps, and a config screen value that is not a number is read
as −1 with a note.

## What was built

### The cheat sheet is off at launch

The control window opens with no key legend. The APC40 diagram sits in the
bottom-left corner, and moves up above the sheet while the sheet shows.
`/` (printed "H / ?" on the sheet), the gamepad's MENU and the APC40's
DETAIL button all toggle the one param `ui.cheatsheet`. The SYSTEM page
has its checkbox, whose hover says "/ toggles it". DETAIL's LED follows
the param, so it is dark at launch. Nothing remembers the setting and no
config key sets it.

- Code: `Panel.__init__` sets `self.cheatsheet = False` (`ui.py`), and
  the toggle is declared in `_register_panel_params`. The rows are
  `("SLASH", "ui.cheatsheet", "toggle")` and
  `("pad:MENU", "ui.cheatsheet", "toggle")` (`routing.py`), and
  `_note("ui.cheatsheet", N_DETAIL)` (`apc40.py`). The diagram's place is
  set in `ui_desk.py` from `panel.cheatsheet`. `Panel._draw_cheatsheet`
  measures the sheet's height from the rows it has just laid out, so the
  diagram does not jump on the frame the sheet first shows.
- Tests: `test_the_cheat_sheet_is_off_at_launch_and_the_desk_is_on`,
  `test_slash_still_toggles_the_cheat_sheet` (`tests/test_ui_shell.py`);
  `test_the_diagram_draws_on_both_layers_and_hides`,
  `test_the_desk_does_not_jump_when_the_sheet_comes_up`
  (`tests/test_ui_desk.py`).
- Pictures: `uv run python tools/sheet_shots.py` writes `launch-no-sheet.png`
  and `launch-sheet-on.png` into `docs/plans/assets/16-paper-cuts/`.

### An FX chip: the LED switches, the name opens

Each chip on the FX page has two parts side by side.

- **The LED**, a chip-height square at the left end. It shows a filled
  dot while the effect is on and a ring while it is off; an effect aimed
  at the faces gets a diamond instead. A click toggles `fx.<name>.on` and
  never changes which strip is open. Its hover reads "on — click to switch
  off" or "off — click to switch on".
- **The name.** A click opens the effect's strip and never switches the
  effect. The name is also the handle for dragging the chip to reorder
  the stack.

While the effect is on, both parts are solid red. The open chip has a
2 px outline in `ui.TEXT` round both parts. Right-clicking either part
opens the `fx.<name>.on` menu (Learn and so on). Chips are laid out three
to a row (`CHIPS_PER_ROW = 3`). The strip keeps its own "on" check.

Which strip is open is stored as a **name**, not a place in the stack.
Dragging an order slider, moving a chip, loading a preset, or another
effect moving past it never changes which effect is open. If the open
effect's file goes away, the first effect opens instead, and the effect
opens again when its file comes back. Opening a strip is not an undo step,
and the selection is saved in no preset, show or file.

- Code: `FxState.sel_name`, `FxState.select(name)` and
  `FxState.selected()` (`fx.py`). `selected()` never writes; it reads
  `getattr(self, "sel_name", None)` so that an `FxState` from before a hot
  reload still works. `fx.select` keeps its id (`persist=False`,
  `modulatable=False`) and is now a view onto the name: reading it gives
  the open effect's index in `names()`, and writing index `i` selects
  `names()[i]`, with `i` clamped (`_sel_index`, `_sel_set`). The chip is
  `ui_fx._chip`, made of the items `##led.fx.<name>.on` and
  `##chip.fx.<name>.on`. The first time the page shows the first effect,
  it pins it by name (`ui_fx.page`).
- Tests (`tests/test_fx.py`): `test_selection_is_by_name_and_survives_a_reorder`,
  `test_selection_survives_a_preset_load`,
  `test_a_removed_effect_falls_back_and_comes_back`,
  `test_fx_select_is_a_view_onto_the_name`,
  `test_a_chip_click_selects_and_never_toggles`,
  `test_the_chips_led_toggles_and_never_selects`,
  `test_selecting_an_effect_is_not_an_undo_step`,
  `test_the_first_effect_is_held_by_name_once_it_is_shown`,
  `test_the_leds_hover_says_what_a_click_does`,
  `test_the_page_has_no_conflicting_ids`.
- Demo: `uv run python tools/fx_page_demo.py` prints a transcript in which
  the open effect stays put through reorders and preset loads.

### An open effect that is not running says why

When the open effect is not running, its strip shows one line in
`ui.WARN` below the effect's tip and error line and above its "on" row.
The first reason that applies is the one shown:

| Reason (`why_idle`) | Line | Chip |
|---|---|---|
| `off` | "off — nothing below shows until it is on" | **turn on** → `fx.<name>.on` |
| `faces off` | "aimed at the faces, and Faces is off" | **faces on** → `view.faces` |
| `bypassed` | "the whole stack is bypassed" | **effects on** → `fx.on` |
| `fx mix 0` | "FX mix is at 0" | none |
| `mix 0` | "its mix is at 0" | none |

Below the line, the strip's rows are **dimmed but still live**. A veil in
the window's background colour is drawn over them, and 45 % of each row
shows through (`IDLE_ALPHA`). You can still move the controls, and
right-click → Learn still works on every row. The "on" check is not
dimmed. At "its mix is at 0" the effect's own mix fader is not dimmed
either, because it is the control the line names. A row armed for Learn
has its learn frame drawn again over the veil. Each chip calls
`Param.set` on the base, so each click is one undo step. `why_idle`
reads the effective values. If a routed source holds the switch off,
**turn on** sets the base but the line stays, and the chip's hover names
the source.

- Code: `ui_fx.why_idle`, `IDLE`, `_idle_line`, `_dim` and
  `_relearn_frame`.
- Tests (`tests/test_fx.py`): `test_why_idle_names_the_first_reason`,
  `test_an_off_effects_strip_says_so_and_turn_on_switches_it_on`,
  `test_a_bypassed_stack_says_so_on_the_strip`,
  `test_the_idle_strips_controls_stay_live`,
  `test_the_page_fits_with_the_tightest_strip_idle`,
  `test_turn_on_is_one_undo_step`,
  `test_an_armed_rows_learn_frame_is_drawn_over_the_veil`.

### Where the windows open at launch

Each window opens on the screen the config names. If the config does not
name one, it opens where it was at the last quit. If neither applies, it
opens at the old default spot: the render window at the primary screen's
top-left, and the control window flush right, both inset 16 px.

`config.toml`, `[output]`:

- `monitor` (default −1): the screen the render window opens on, and the
  screen fullscreen covers. If `[[output.screens]]` is listed, its first
  entry's `monitor` is used instead.
- `control_monitor` (default −1): the screen the control window opens
  on.

−1 means "where it was last time, otherwise the primary screen". A
config index beats the remembered position. The remembered rect is still
used when its centre is on the screen the config names.

If an index names a screen that is not connected, it is treated as −1,
with a note on stderr and on the SYSTEM page. The config then holds −1
for the rest of the run. A value that is not a number (`monitor =
"left"`) is also −1 with a note (`config.load`).

`<home>/windows.json` (schema `hyperspace.windows/1`) holds the control
window's rect and a `render` list with one entry per render output. Each
entry has `x, y, w, h` and the name of the screen it was on. It is
written on quit and on ⌘R only, through a per-process temp file and a
rename. What it records:

- **The windowed rect.** A fullscreen or overlay window is saved as the
  rect it would go back to (`Output.windowed_rect`). Whether a launch is
  fullscreen is decided by the config, never by this file.
- **Minimised windows.** A minimised window keeps its old entry.

A remembered rect is used only if at least 120 × 80 px of it is on a
connected screen and its top edge is inside that screen's work area.
Its size is clipped to that screen and is never smaller than 320 × 240.
A file that is not JSON or has another schema is ignored. A bad entry,
or a rect that is on no screen, falls back to the default spot with a
note that names the screen it was last on. A failed write is said on
stderr. Delete the file to forget the positions.

- Code: `placement.py` imports nothing from the package (`screens`,
  `load`, `save`, `usable`, `default_rect`, `read`, `index`, `place`).
  It is called from `app._windows`, and `app._save_windows` runs at the
  end of `main` and in `_restart`. `overlay.Output.windowed_rect` and
  `config.DEFAULTS["output"]` are the other pieces. `hotreload.MODULES`
  lists `"placement"`.
- Tests: in `tests/test_placement.py`, `test_first_launch_places_as_before`,
  `test_a_remembered_rect_is_restored`,
  `test_a_rect_on_a_screen_that_is_gone_falls_back`,
  `test_an_off_screen_rect_falls_back`,
  `test_a_config_monitor_beats_the_remembered_screen`,
  `test_a_remembered_rect_on_the_configured_screen_is_kept`,
  `test_a_config_monitor_that_is_not_there_is_a_note`,
  `test_a_remembered_size_is_clipped_to_its_screen`,
  `test_save_round_trips_and_render_is_a_list`,
  `test_a_none_keeps_the_old_entry`, `test_a_bad_file_is_ignored`,
  `test_a_bad_file_is_ignored_entry_by_entry`,
  `test_an_unwritable_home_costs_only_the_memory`,
  `test_screens_reads_the_work_areas_in_monitor_order` and
  `test_placement_imports_nothing_from_the_package`. Elsewhere:
  `test_windowed_rect_is_the_saved_rect_while_fullscreen_or_overlay`
  (`tests/test_overlay.py`);
  `test_the_windows_open_where_placement_says`,
  `test_the_exits_save_the_windowed_rects` and
  `test_a_config_screen_that_cannot_be_used_is_minus_one_and_one_note`
  (`tests/test_app_boundary.py`);
  `test_a_screen_that_is_not_a_number_is_minus_one_and_a_note`
  (`tests/test_config.py`).
- Demo: `uv run python tools/placement_demo.py` walks `place` through
  fake screens.

### Instances down to zero

`view.instances` runs from 0 to 100: an integer, linear, default 1. At 0
it reads "0 · nothing drawn", and the scene pass clears to the ground and
draws no faces, lines or points. Everything after it runs as usual: the
look-back's echoes fade out over the empty scene, generator effects such
as plasma still paint, and the ghost hands still draw. You can reach 0
from the VIEW page slider's left end, or from track knob 3 at its bottom
on a fresh preset's desk (`cc 0x32`, `apc40.py`).

- Code: `Renderer.draw_scene`, `n_inst = max(0, int(s.instances))` with
  an early return at 0 (`render.py`), and the `view.instances`
  declaration (`params.py`).
- Tests: `test_raw_ranges_clamp_int_and_log` and
  `test_instances_read_nothing_drawn_at_zero` (`tests/test_params.py`);
  `test_zero_instances_draws_only_the_ground`,
  `test_zero_instances_still_runs_the_look_back_and_the_effects` and
  `test_one_instance_is_the_frame_it_was` (`tests/test_render.py`);
  `test_no_factory_hand_row_blanks_the_scene`
  (`tests/test_plan12_presets.py`); `test_a_count_taken_to_zero_is_undone`
  (`tests/test_undo.py`).
- Picture: [`instances-zero.png`](assets/16-paper-cuts/instances-zero.png)
  shows, left to right: count 1; count 0; 0 with plasma on; 0 with the
  look-back on, 3 and 12 frames after the count left 1. It is an
  offscreen render; regenerate it with `uv run python tools/instances_shots.py`.

### The dream's layer is not a modulation target

`dream.layer` is `modulatable=False`, like `dream.gap` and `dream.res`,
because changing it makes the dream worker load another network trunk.
It is still persisted, and the LOOKBACK page, a preset and a desk row can
still set it. A route onto it is a dormant row. Its right-click menu reads
"not modulatable", and it does not appear among the ROUTING page's
targets.

- Tests: `test_dream_params_declared`,
  `test_a_route_on_the_dream_layer_is_dormant` (`tests/test_lookback.py`).

### A footer line said twice shows twice

Every library line that reports something that just happened goes
through `Library.say`, which counts it in `Library.said`. Because of the
count, `Panel._message` shows the same words again: an empty F-key
pressed twice, Home pressed twice with no "starts on", a show saved
twice. A plain assignment to `lib.status` or `lib.warning` is only for
clearing a line, and it is not counted.

- Tests: `test_a_line_said_twice_shows_twice`,
  `test_a_line_assigned_every_frame_does_not_pin_the_footer`
  (`tests/test_ui_presets.py`).

### Round-off does not light the dirty dot

`undo.alike(a, b)` compares nested values exactly, except that floats
only have to agree within undo's `REL_TOL` / `ABS_TOL`. A preset's dirty
dot (`Library.is_dirty`) and a show's (`Project.is_dirty`) compare
through it. As a result, the last bits of float error a performer's
hands leave on a value do not mark the preset unsaved, while a real
change of one detent does.

- Tests: `test_a_performers_round_off_lights_no_dot`,
  `test_alike_is_exact_but_for_float_round_off` (`tests/test_undo.py`).
- Demo: `uv run python tools/followups_demo.py` prints the footer, the
  dirty-dot and the config-screen fixes, before and after.

## Not verified by a person

None of this has been tried at the machine. That includes the keys and
the DETAIL LED, a real mouse on the chip's LED, the dimmed strip seen
from a step back, windows on a second screen or projector, and K3 at the
bottom. Hand checks 58–63 (group L of
[`11-hand-checks.md`](11-hand-checks.md)) and
[`TESTING-GUIDE.md`](../TESTING-GUIDE.md) cover them. Decision register
rows 45–49 ([`DECISION-REGISTER.md`](../DECISION-REGISTER.md)) are still
waiting for the owner to confirm or overturn them.

## Known rough edges

- If a screen named in the config is not connected at launch, the index
  becomes −1 for the whole run, so a projector plugged in later has to be
  picked by hand on the OUTPUT page. Audit P6 (open).
- `monitor = true` or `monitor = 1.9` is read as `int()` reads it (1),
  with no note (`placement.read`).
- A user's route that pushes both ways (an LFO) on a count of 1 takes
  `view.instances` to 0 for part of its cycle. No factory row does this.
  Register row 47.
- The idle-strip veil assumes the page's background is the window's
  background colour (`ui_fx._dim`).
