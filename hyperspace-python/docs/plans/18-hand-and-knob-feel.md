# Plan 18 — Hand and knob feel

This plan changed how the hands and the desk's knobs feel. A hand counts
only inside an interaction box kept in `hands.json`, which the
calibration sweep sets and "reset ranges" opens. A hand Learn lands as a
gentle `push` about the param's base at a session depth wherever that is
the softer reading, instead of making the hand the whole fader. A desk
knob or fader glides between the param's detents instead of stepping
(knob smoothing, 80 ms in the running app). And a factory preset,
`hands-orbit`, puts the camera under two hands.

## What was built

### The interaction box

**At the machine.** HANDS page → "feel & calibration" → calibrate: a 20 s
sweep sets the axis ranges and, from where the palms went, the box.
"reset ranges" puts the ranges back to the defaults and opens the box. A
hand whose palm is outside the box reads absent everywhere: its axes
read `NaN` so its rows let go and the base returns, its presence lane
and note go off, its pinch switches drop, and its ghost hand fades out.
The HANDS page's box (190 × 92 px) shows the view from above with the
box as an inner rectangle, a height gauge with the box's y as a bracket,
and a hand tracked but outside as a hollow ring. The status line shows
each hand as `●` (in the box), `◌` (tracked, outside) or `○` (not seen),
with a tooltip. Under the selected axis's range a disabled line gives
the box's three ranges, or "box open". The sweep's note reads e.g.
`calibrated 6 axes · box 419 × 290 × 270 mm`, `box: x open (not swept)`,
`box: open (not swept)` or `box left as it was (too few palm samples)`.

**How it works.** `hands/core.py`: `load_box`, `inside`,
`save_calibration(path, ranges, box)`, and on `HandsIO` the `box`,
`outside` and `_in_box` state. In `HandsIO.poll` a hand is present when
the tracker has it at or above `[hands] min_confidence` **and** there is
no box, or a sweep is running, or its palm is in the box. The edge has
hysteresis kept per palm (`_in_box`): a hand that is out comes in at a
face, one that is in leaves `BOX_EDGE` (15 mm) past it; a one-frame dip
in confidence does not reset it. During a sweep the box is not applied,
and every tracked palm is sampled whatever the rig's `dofs`.
`HandsIO._sweep_box` makes the box from the samples: per coordinate the
2nd–98th percentile of both hands pushed out by `BOX_MARGIN` (40 mm),
`x` symmetric about the camera; a coordinate no single hand swept over
`BOX_MIN_SPAN` (120 mm) is left open; fewer than `CAL_MIN_SAMPLES`
samples leaves the old box. `ghost.box_of` frames the ghost hands on
the box when one is set, else on the union of the axis ranges.
`hands/panel.py`: `_box`, `_status`, `_calibrate`.

**The file.** `hands.json` in the library home (`[hands] calibration`):
`{"schema": "hyperspace.hands/2", "axes": {...}, "box": {"x": [lo, hi],
"y": [lo, hi], "z": [lo, hi]}}`, millimetres from the camera. `box`
`null`, or a coordinate `null`, is open. An older file with no `box`
loads as no bounds and is not rewritten at load. A bad pair or a missing
key opens that coordinate and says so once on stderr (a bad box never
hides the hands). The first time a running app overwrites a file that is
not schema 2, `save_ranges` first copies it beside itself
(`_keep`: `hands.json.bak-v1`, or `-<YYYYmmdd-HHMMSS>`, `-2`, … when that
name is taken), once per adapter; a copy that cannot be made is said in
the note and never stops the save.

**Tests.** `tests/test_hands.py`: `test_no_box_is_todays_presence`,
`test_a_hand_outside_the_box_reads_absent_everywhere`,
`test_a_hand_outside_the_box_releases_its_rows_and_the_base_returns`,
`test_the_boxs_edge_has_hysteresis`,
`test_a_dip_in_confidence_does_not_evict_a_hand_in_the_edge_band`,
`test_a_hand_re_entering_the_box_is_caught_not_jumped`,
`test_the_sweep_sets_the_box_with_its_margin_and_a_symmetric_x`,
`test_two_still_hands_held_apart_are_not_a_sweep`,
`test_the_box_is_not_applied_during_a_sweep`,
`test_reset_ranges_opens_the_box`,
`test_an_old_hands_json_reads_as_before_and_is_not_rewritten_at_load`,
`test_the_first_rewrite_of_an_old_file_keeps_a_backup`,
`test_a_backup_that_cannot_be_made_never_stops_the_save`,
`test_a_save_that_fails_does_not_copy_the_old_file_again`,
`test_a_malformed_box_opens_and_says_so`,
`test_the_box_round_trips_through_the_file`,
`test_a_frame_without_a_whole_palm_is_no_sample`,
`test_hands_page_draws_the_box_and_a_hand_outside_it`.
`tests/test_ghost.py`: `test_the_camera_frames_the_interaction_box_when_one_is_set`,
`test_a_hand_outside_the_box_fades_out`.

**Demo.** [`assets/18-hand-and-knob-feel/box-demo.txt`](assets/18-hand-and-knob-feel/box-demo.txt),
from `tools/box_demo.py` (synthetic hands): an old `hands.json` left
byte for byte, a sweep making a box and the backup, a hand walking out
through a face and back, "reset ranges". `tools/box_shot.py` renders a
screenshot of the HANDS page with a box set into the same folder.

### A learn's default

**At the machine.** Right-click a param → Learn hand ▸ left / right, then
move the hand. What lands (`Learn._row` in `learn.py`):

| The target | A centred axis | A one-sided axis (height) |
|---|---|---|
| continuous, range centred on zero | `push`, depth D | `push`, depth D |
| any other continuous param | `push`, depth D | `position`, depth 1 |
| an enum, a toggle, a trigger, a whole-number param | `position`, depth 1 | `position`, depth 1 |

D is **Learn depth** (`hands.learn_depth`, 0.25, range 0.05–1.0), on HANDS
under "feel & calibration" after Catch; it is a session setting saved
with a hands setup and the show, and changes only the next learn. A
learned push carries no `rest`, so it is centred where the axis rests: a
level hand, or a height at the bottom, leaves the preset's value alone.
"Centred" is the axis's own **Centred** switch (`hands.<axis>.bipolar`)
at the moment of the learn (`HandsIO._learn` passes
`centred=bool(axis.bipolar)` and the depth). "Range centred on zero" is
`learn.centred_target` (continuous, no taper, not log, `lo == -hi`).
Nothing is refused or flagged by id or group. Learning an axis onto a
param removes that axis's other `push` / `position` rows, switched on or
off (`Learn._place`); the status line names the params they were on and
one ⌘Z brings them back. Learning the axis that already performs the
target only refreshes its gate, whatever the op. Rows that already exist
are never rewritten.

**Tests.** `tests/test_learn.py`:
`test_a_centred_axis_learns_as_a_push_about_the_base_at_the_learn_depth`,
`test_a_one_sided_axis_on_a_one_sided_param_is_still_the_fader`,
`test_a_one_sided_axis_on_a_zero_centred_range_pushes_up_from_the_base`,
`test_a_discrete_target_keeps_the_position_row`,
`test_a_whole_number_param_keeps_the_position_row`,
`test_centred_target_reads_the_declared_range`,
`test_no_target_is_refused_or_flagged`,
`test_the_same_axis_again_only_refreshes_the_gate_whatever_the_op`,
`test_existing_rows_are_never_rewritten`,
`test_the_two_default_depths_agree` (`learn.PUSH_DEPTH` equals
`HandSettings.learn_depth`), `test_a_learned_axis_drives_one_param`.
`tests/test_hands.py`:
`test_learn_passes_the_axiss_centredness_and_the_sessions_depth`,
`test_learn_depth_changes_only_the_next_learn`,
`test_learn_takes_the_axis_that_moved_as_a_push_about_the_base`.

**Demo.** [`assets/18-hand-and-knob-feel/learn-default.txt`](assets/18-hand-and-knob-feel/learn-default.txt),
from `tools/learn_default_demo.py` (a synthetic palm through the real
`HandsIO`): a roll learned onto `rot.rate.XY` from a base of 1× reads 1×
level and −15.64× … +17.64× at the ends (a depth-1 `position` row would
read 0× level and ±66.56×); height on brightness stays the fader; Learn
depth at 0.1 carried by the next learn; an axis moved to a second param
and back with ⌘Z.

### Knob smoothing

**At the machine.** SYSTEM page, first row under "midi": **Knob
smoothing** (`desk.slew`), off to 250 ms; 80 ms when the app starts on
a show that does not name it. A show that saved
a number keeps it (0 included). With it on, a desk knob or fader on a
continuous, non-integer param glides to its value in a straight line
written between the detents, and lands on the same detent it would with
smoothing off. Buttons, relative encoders and discrete or whole-number
targets are not smoothed. The ring sent back during a glide is the value
the knob is setting, never the base in flight. One knob turn is one undo
step.

**How it works.** `routing.py`: `SLEW_PARAM`, `SLEW_MAX_S` (0.25),
`SLEW_DEFAULT_S` (0.08), `Bindings.slew`, and `register_desk` declaring
`desk.shift` and `desk.slew` (group `desk`, in `params.SESSION_GROUPS`,
so a preset load never moves it). `app._desk_table` declares them and
sets 80 ms before `library.attach`, so the show's saved value lands on
them; a bare `Bindings` (tests, probes) is 0. `midi.py`: in
`MidiIO._apply`'s `abs` branch, `_aim` starts or re-aims a `Slew`;
`_glide` steps every glide once a poll with `Param.set` and lands it with
`Param.set_norm`; `_landing` is the detent's norm; `_ring_norm` is what
`feedback` and `redraw(load=True)` read; `_land_all` lands every glide on
close or a lost port. A param someone else writes during a glide keeps
their value. A param that moves on its own (`rot.phase.*` while its plane
turns) is written at once from then on (`_restless`). A preset load
drops every glide except a session param's. The slew can never outlast
`undo.SETTLE_S`.

**Tests.** `tests/test_midi.py`:
`test_smoothing_is_off_by_default_and_every_write_is_immediate`,
`test_a_smoothed_knob_arrives_in_a_straight_line_and_rests_on_the_detent`,
`test_a_glide_starts_on_the_frame_of_the_message`,
`test_a_new_message_re_aims_the_glide_from_where_it_is`,
`test_the_ring_a_glide_shows_is_the_ring_after_the_write`,
`test_a_fader_keeps_its_catch_through_a_glide_and_an_uncaught_one_writes_nothing`,
`test_someone_elses_write_stops_a_glide`,
`test_buttons_relative_knobs_and_discrete_targets_are_not_smoothed`,
`test_turning_smoothing_off_or_losing_the_port_lands_every_glide`,
`test_a_glide_on_a_hand_owned_param_moves_the_return_value`,
`test_a_load_from_a_pad_ends_a_glide_before_it_steps`,
`test_a_param_that_moves_on_its_own_is_written_at_once`,
`test_closing_the_adapter_lands_every_glide`. `tests/test_desk.py`:
`test_a_layer_switch_leaves_a_glide_to_finish`,
`test_a_preset_load_stops_a_glide_on_a_performance_param_and_not_on_the_dim`.
`tests/test_undo.py`: `test_a_smoothed_knob_turn_is_one_step`,
`test_undo_during_a_glide_holds`,
`test_the_slew_can_never_outlast_the_settle_time`.
`tests/test_app_boundary.py::test_the_app_starts_with_knob_smoothing_at_80_ms_and_a_show_keeps_its_own`.

**Demo.** [`assets/18-hand-and-knob-feel/slew-demo.txt`](assets/18-hand-and-knob-feel/slew-demo.txt)
and [`slew.png`](assets/18-hand-and-knob-feel/slew.png), from
`tools/slew_demo.py` (fake ports, a scripted clock): a slow turn on
`camera.pan.x` and `rot.rate.XY` off and at 80 ms, a fast flick, the
rings, a preset load mid-glide, and the undo step.

### Two hands on the camera: `hands-orbit`

**At the machine.** The factory preset `hands-orbit` is in the preset
list; no factory project puts it in a bank slot. Five rows, each a
`push` from its axis's own rest, no pinch (`preset.hands_orbit_routes`;
`hyperspace/library/presets/hands-orbit.json`):

| hand axis | camera param | depth | at the ends of the default range |
|---|---|---|---|
| `hand:right.x` | `camera.yaw` | +0.5 | −90° … +90° |
| `hand:right.pitch` | `camera.pitch` | +0.5 | −44° … +44° |
| `hand:left.x` | `camera.pan.x` | +0.1 | −400 px … +400 px |
| `hand:left.z` | `camera.pan.y` | +0.1 | −400 px … +400 px |
| `hand:left.y` | `camera.zoom` | +0.12 | base … base × 2.23 |

An absent or level hand leaves the camera where the mouse left it. The
two hands steering relative to each other is not built (it would need a
lane derived from two hands).

**Tests.** `tests/test_presets.py`:
`test_hands_orbit_is_five_pushes_onto_the_camera`,
`test_an_absent_or_level_hand_leaves_the_orbit_camera_alone`,
`test_each_orbit_axis_moves_its_camera_param_as_its_row_says`,
`test_the_orbit_hands_leaving_return_the_camera_to_where_the_mouse_left_it`.

**Demo.** [`assets/18-hand-and-knob-feel/orbit-sweeps.txt`](assets/18-hand-and-knob-feel/orbit-sweeps.txt)
and [`orbit.png`](assets/18-hand-and-knob-feel/orbit.png), from
`tools/orbit_demo.py` (synthetic hands, offscreen renders, default
ranges, no box).

## Not verified by a person

Nothing here has met a camera, a real hand or an APC40: hand checks
72–80 (group N) of [`11-hand-checks.md`](11-hand-checks.md), calibration
(72) first; see also [`../TESTING-GUIDE.md`](../TESTING-GUIDE.md). The
numbers (40 / 15 / 120 mm, Learn depth 0.25, 80 ms, the orbit depths)
are first cuts. Decision register rows 50–56 are open for the owner.

## Known rough edges

- The box is off for the whole 20 s sweep, so any tracked hand performs and is sampled into the new box: calibrate with nobody else in view (row 50).
- The tracker's confidence floor (`[hands] min_confidence`) has no hysteresis; only the box's edge does.
- "Centred" is read from the axis's Centred switch while a push centres on its Rest: Centred on for height without moving its Rest gives a push from the bottom (row 52).
- Learning the axis that already performs a param does not tame an existing depth-1 `position` row; Unbind first or edit the row on ROUTING (row 53).
- A preset load drops a performance param's glide without landing it, so a param the preset does not name stays between detents.
- An uncaught fader's pickup test reads the base in flight, so it can catch on a value a glide is only passing through.
- A ring can re-base the encoder one CC step from where the hand has it (the ring is drawn from the 100-detent value), smoothing on or off.
- "Knob smoothing" is offered as a route's scale on ROUTING, since `desk` is a session group (row 55).
- `hands/core.py`'s module docstring still says a Learn writes a `position` route.
