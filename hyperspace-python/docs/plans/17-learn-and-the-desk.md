# Plan 17 — Learn, Unbind and seeing the desk

This plan made mapping something you can see and cannot get wrong by
accident. A right-click menu has one **Unbind** that removes what is
bound to a param, with or without a MIDI adapter. **Learn desk** and
**Learn hand ▸ left / right** each listen to one source only, so a stray
hand or knob cannot complete the wrong learn. The menu also opens from a
row's label and from every analyzer meter. The on-screen APC40 grows to
fill the room it has and names what each lit control does. A click on a
desk control picks it, and the next click on a param maps it. The
ROUTING page has a text filter.

## What was built

### One Unbind

- **At the machine.** Right-click any param. Above the items the menu
  lists one line per thing bound: a preset desk row as its glyph and
  Akai's name (`K2 (track knob 2)`, `B16 (▲) · step +3`), a route as the
  router describes it (`(off)` when disabled), and a session row in dim
  text (`SM (MASTER fader) · invariant`, `… · global layer`). **Unbind**
  appears only when it would remove something. With one kind bound it is
  a plain item. With both kinds it is a submenu with `desk — …`,
  `route — …` and `both`. A session row (invariant or global layer) is
  never removed. The menu is the same with `[midi] enabled = false`.
  An unbind is one undo step. It writes no file and lights the preset's
  dirty dot.
- **Code.** `learn.py`: `Learn.unbind(ids, *, desk, routes, name)`,
  `Learn.bound(ids)` and the module function `bound(table, ids)`. The
  last returns the preset's desk rows, the routes (never a MIDI row) and
  the session's MIDI rows. The menu lists from the same function, so its
  lines are exactly what Unbind removes. `ui.py`: `Panel._ctx_lines`,
  `_ctx_unbind`, `_row_name`, `_table`, which reads the router's table
  and never the MIDI adapter. `hands/panel.py`: `ctx_rows(panel, p, *,
  lines, gate)` draws the hand rows' lines and the `Gate: … ▸` submenu.
  `MidiIO.unbind` (`midi.py`) delegates to `Learn.unbind` with
  `routes=False`.
- **Tests.** `tests/test_learn.py`:
  `test_unbind_removes_the_presets_desk_rows_and_every_route`,
  `test_unbind_by_kind`,
  `test_unbind_is_one_undo_step_and_none_when_nothing_goes`.
  `tests/test_ui_shell.py`:
  `test_the_menu_lists_and_unbinds_with_no_midi_adapter`,
  `test_unbind_is_not_offered_on_a_session_only_param`.
  `tests/test_midi.py`:
  `test_unbind_removes_only_preset_layer_rows_and_writes_no_file`,
  `test_an_unbind_is_one_undo_step`.

### Learn that cannot pick the wrong source

- **At the machine.** The menu offers **Learn desk** on any param a desk
  control can go on. That excludes a file path and SHIFT's own
  `desk.shift`. It also offers **Learn hand ▸ left / right**, but only
  when a hand tracker is present, only on a modulatable param, and only
  for the sides the rig has.
  - **Desk learns.** A desk learn is completed by a knob or button turned
    or pressed on the APC40, or by a click on the on-screen desk. Hands
    do nothing to it.
  - **Hand learns.** A hand learn is completed only by an axis of that
    hand. A knob bumped meanwhile does its own job.
  - **Session controls during a desk learn.** An invariant control (a
    fader, SHIFT, TAP, a bank pad, the SAVE AS row) is not a candidate.
    It does its own job, and the learn stays armed.
  - **Refusals.** A desk learn on a control while the global layer is up
    is refused. The learn stays armed, and the footer shows the reason in
    the warning colour.
  - **The footer.** While a learn is armed the footer reads, in red,
    `learning <id> — <what it waits for>`, and a click on that line
    cancels the learn. ROUTING and SYSTEM show the same line, plus
    "— still learning `<id>`" after a refusal.
  - **What a learn lands as.** A desk learn lands as a preset-layer
    `abs`, `rel` or `toggle` row with the APC40's ring and LED feedback.
    A hand learn lands as a `push` at `hands.learn_depth` or as a
    `position` row, by `Learn._row`'s table.
- **Code.** `learn.py`:
  - `WANTS`, `Learn.want` and `Learn.arm(pid, want)`. `arm` raises on an
    unknown want, clears `refused` and counts `armed_n`.
  - `Learn.accepts(source)`.
  - `Learn.learn_control(source, profile)`. This is the one road onto the
    desk, and it needs no adapter.
  - `blocked(table, source)`, the invariant / global rule.
  - `Learn.said_n`.

  `midi.py`: the learning branch of `MidiIO._handle` and `_learned`.
  `hands/core.py`: `HandsIO._learn` considers only the axes the learn
  accepts. Its baseline is keyed on `(pid, want, armed_n)`, so a re-arm
  starts fresh. `ui.py`: `_ctx_learn`, `_hand_sides`, `_learn_hint`,
  `_learn_status`, the footer's armed line (`CANCEL_TIP`) and the
  `"learn"` key of `_message`. `ui_routing.py`: `_learn_line`.
- **Tests.** `tests/test_learn.py`: `test_accepts_by_want`,
  `test_learn_control_needs_no_adapter`,
  `test_learn_refuses_the_global_layer_and_invariant_controls`.
  `tests/test_hands.py`: `test_a_hand_learn_listens_to_one_hand`,
  `test_the_hands_never_complete_a_desk_learn`,
  `test_a_rearm_starts_a_fresh_baseline`. `tests/test_midi.py`:
  `test_a_knob_bump_during_a_hand_learn_does_its_own_job`,
  `test_an_invariant_control_works_through_a_desk_learn`.
  `tests/test_ui_shell.py`:
  `test_the_menu_offers_learn_desk_and_learn_hand`,
  `test_the_footer_says_what_a_learn_waits_for_and_what_it_did`,
  `test_the_click_wording_is_switched_on`. `tests/test_desk.py`:
  `test_the_clip_stop_row_is_invariant`.

### The menu where it was missing

- **At the machine.** Right-clicking a row's label, such as the word ZOOM
  or a fader's name, opens that param's menu. Each analyzer meter opens
  `band.select`'s menu. A learn armed from a meter frames every meter.
- **Code.** `ui.py`: `Panel._ctx_id`, `Panel._ctx_label` (called by
  `_row` and `_fader`), `_meters` (`_ctx(reg["band.select"], f".{i}")`),
  and `ui_routing.desk_target(p)`, the one "can a desk control go here"
  rule.
- **Tests.** `tests/test_ui_shell.py`:
  `test_a_rows_label_opens_its_params_menu`,
  `test_every_meter_has_the_band_select_menu`.

### The ROUTING filter

- **At the machine.** The ROUTING page's counts line has a text field
  (hint "filter"), left of `+ route`. Every space-separated word must
  appear in a line for that line to show:
  - a route matches on its description, source, target and the target's
    label;
  - a desk or session line matches on its glyph, Akai's name, source,
    and (when mapped) its target and label;
  - a macro matches on its id, its label and its subscribers.

  While the filter is set, the counts read "N of M rows" in red and a ×
  chip clears it. A section with nothing to show says "no row matches".
  A line someone is editing stays drawn until it is let go. The filter
  is UI state only: it is not saved, survives a preset load, and is
  cleared by × or by a click on a desk control.
- **Code.** `ui_routing.py`: `_state(panel)["find"]`, `FIND_W`,
  `matches`, `route_hay`, `control_hay`, `macro_hay`, `found`, `_shown`,
  `_find_field`, `NO_MATCH`.
- **Tests.** `tests/test_ui_routing.py`:
  `test_the_filter_matches_glyph_param_and_source`,
  `test_a_filtered_page_draws_only_matching_lines_and_keeps_its_ids`,
  `test_the_filter_is_ui_state`,
  `test_typing_in_the_filter_is_imguis_keyboard_not_the_apps`,
  `test_a_line_in_use_is_not_filtered_away_under_the_hand`.

### The big desk

- **At the machine.** The desk window sits bottom-left, in the room left
  of the panel (above the cheat sheet when that is on). Hiding the panel
  makes the desk fill the control window. You can hide the panel with
  `H`, the APC40's DEVICE ON/OFF, or the desk header's `big` chip (which
  then reads `panel`).
  - **Labels.** Once a layout unit is at least `LABEL_UNIT` (44 px) wide
    and `LABEL_UNIT_H` (32 px) tall, every lit control carries a label:
    - a `set` row on an enum shows the value's name (bank pads show
      preset names);
    - a `step` row shows the label and the amount;
    - any other row shows the param's label.

    Labels wrap to two lines. A label that would be cut is drawn at
    11 px.
  - **Ink.** Bright labels are the up layer's rows. Grey labels are
    invariant.
  - **Smaller sizes.** Below that size the desk draws glyphs only.
  - **Hiding it.** `ui.desk` (SYSTEM page) hides the desk at any size.
  - **Scrolling and widgets.** The window never scrolls, and its only
    widget is the chip.
- **Code.** `ui_desk.py`: `room(display, panel_x, sheet)`, `MIN_W`,
  `MIN_H`, `LABEL_UNIT`, `LABEL_UNIT_H`, `LABEL_PX`, `LABEL_LINES`,
  `text(reg, b)`, `wrap`, `label_px`, `label` (the hover). `ui.py`:
  `Panel._draw` records `_panel_x`, and the cheat sheet records
  `_sheet_w`.
- **Tests.** `tests/test_ui_desk.py`:
  `test_the_desk_takes_the_room_it_has`,
  `test_the_big_desk_labels_every_lit_control_and_never_scrolls`,
  `test_the_small_desk_draws_glyphs_only`, `test_a_controls_text`,
  `test_the_diagram_draws_on_both_layers_and_hides`.

### Click a control, then a param

- **At the machine.** A left click on a desk control does one of four
  things:
  - With **Learn desk** armed, it completes the learn (the same refusals
    and undo as a knob).
  - With a hand learn armed, it does nothing.
  - On the picked control, it lets go.
  - Otherwise, it picks the control. The pick is framed red, and ROUTING
    scrolls its `##routes` child to the control's line and frames it.
    ROUTING scrolls now if it is open, or the next time it is opened; the
    page is not changed. The pick also clears the ROUTING filter and
    brings a hidden panel back.

  While a mappable control is picked, every page except ROUTING is drawn
  dimmed (disabled), and a click on a param's widget or label maps the
  control there. A click does not map until the mouse has moved
  `PICK_MOVE` (12 px) from the click that made the pick.
  - **Unmappable picks.** An invariant control, or any control while the
    global layer is up, is picked for the look only. The header says why,
    and nothing dims.
  - **Letting go.** The pick lets go on a click on it, on the desk's
    empty ground or on the footer's line, or after `PICK_S` (20 s) with
    no click in the window. Any click restarts the count. The header and
    the footer count down ("D3 picked (20 s): …").
  - **One road.** A map takes the same road as a knob learn: one undo
    step, and the control's old row and the param's previous row in the
    same role are let go and named.
- **Code.** `learn.py`: `Learn.control`, `Learn.pick`,
  `Learn.map_picked`. A map that does not land keeps the pick and leaves
  no learn armed. `ui_desk.py`: `click`, `mappable`, `picked`, `picking`,
  `armed`, `tick`, `let_go`, `left`, `first_sight`, `pick_line`,
  `footer_line`, `rect`. `ui.py`: `_ctx_pick`, `_frame_item`, and the
  disabled page in `_draw`. `ui_routing.py`: `goto`, `_pick_row`,
  `is_line_of`, `_mark_line`.
- **Tests.** `tests/test_ui_desk.py`:
  `test_a_click_picks_and_a_second_click_lets_go`,
  `test_a_click_completes_an_armed_desk_learn`,
  `test_a_pick_lets_go_by_itself`. `tests/test_learn.py`:
  `test_pick_then_param_maps_through_the_learn`,
  `test_a_pick_on_an_invariant_control_or_the_global_layer_maps_nothing`.
  `tests/test_ui_shell.py`:
  `test_a_picked_control_dims_every_page_but_routing`,
  `test_a_click_on_a_param_maps_the_picked_control`,
  `test_the_footer_says_what_is_picked_and_a_click_lets_go`.
  `tests/test_ui_routing.py`:
  `test_goto_scrolls_the_rows_child_to_the_controls_line`,
  `test_a_desk_click_clears_a_filter_that_has_the_keyboard`.

### Demos

The scripts below regenerate pictures and transcripts into
`docs/plans/assets/17-learn-and-the-desk/` from a temp home. The folder
holds no output now, so run a script to see the app as it is.

- `tools/desk_shots.py` (and `desk_shots.py map`): the big desk, the
  picked state and ROUTING's goto.
- `tools/learn_shot.py`: the menus.
- `tools/learn_demo.py unbind` / `learn`: menu and learn transcripts.
- `tools/label_menu_shot.py`: the menu opened from a label.
- `tools/routing_filter_shot.py`: the ROUTING filter.

## Not verified by a person

No real click, right-click, keystroke, hand or APC40 has been used with
any of this. Hand checks 64–71 (group M of
[`11-hand-checks.md`](11-hand-checks.md)) cover it. See also
[`../TESTING-GUIDE.md`](../TESTING-GUIDE.md). These calls were built on
the plan's recommendation and wait for the owner in
[`DECISION-REGISTER.md`](../DECISION-REGISTER.md) rows 57–64.

## Known rough edges

- **SHIFT during a desk learn.** A desk learn armed while SHIFT is
  latched swallows every non-invariant control, each refused for the
  global layer, until SHIFT is unlatched or the learn is cancelled
  (register row 61).
- **Bank pad during a learn.** A bank pad pressed during a learn loads
  its preset (it is invariant), and the learn then lands in that preset.
- **Gate under a hand learn.** Under Learn hand ▸ left, the other hand's
  pinch may still gate the row (register row 64).
- **Rows hidden by the filter.** A row added while a filter is set can
  be hidden by it, and the red count is the only sign. A digit or
  one-letter word matches widely: "lfo 1" also matches `lfo:1`, which is
  LFO 2 (register row 63).
- **Labels that open nothing.** A label a page draws itself, not through
  `_row` or `_fader` (FX "blend", "scene", "path"), opens no menu.
- **Nudge chips.** The LFO page's two nudge chips share one popup id, so
  their menu draws its items twice (audit U9).
