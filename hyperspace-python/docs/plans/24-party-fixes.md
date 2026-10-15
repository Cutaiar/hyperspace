# Plan 24 — the party fixes

The fixes the party asked for that need no new foundation,
built as stream C of the run in
[`24-26-27-orchestrator-prompt.md`](24-26-27-orchestrator-prompt.md),
from the owner's intent in [`24-party-wishlist.md`](24-party-wishlist.md):
a desk you can trust (a two-handed save, loads that relight the whole
desk, the render toggles on both layers, a desk log), the track faders
freed for presets, a coverage report and desk templates, faster mapping
at the screen, the hands' dance sources and a grab switch, and the
palette fold. **The mechanisms only: no preset was edited or added**
(owner, 2026-10-14). Every file under `hyperspace/library/` is
byte-identical to the run's base; every proof is a fixture under
`tests/fixtures/` loaded through a scratch library. The fader sets, the
hand mappings, the dance presets, the templates and the palettes are the
owners' creative pass, after this.

Hand checks: [`11-hand-checks.md`](11-hand-checks.md) group U, checks
148–167 (and group T, 144–147, for the pad's four checks PR #161 left
unnumbered). Open decisions: [`DECISION-REGISTER.md`](../DECISION-REGISTER.md)
rows 110–139. The owner's decisions for this plan are in
[`DECISIONS.md`](../DECISIONS.md) with Who "owner".

Branch `plan-24-26-27-integration`: C1 (PR #175), C4 (#176), C6 (#173),
C5 (#178), C2 (#180), C3 (#182).

## What was built

### C1 — the desk you can trust

- **At the machine.** Hold **SAVE** — track 8's clip stop, the last
  button of the row under the grid — and tap any bank pad (clip rows 1,
  4, 5) to save the live state into that pad's slot. An empty pad gets a
  new preset; so does a filled pad (TRIP → TRIP 2), whose old preset
  keeps its file and stays in the list with no pad. The pad blinks; SAVE
  is lit while held; the tap never loads; SAVE alone does nothing; the
  same with SHIFT latched. Nothing is ever overwritten or trashed from
  the desk. Holding an empty pad still saves into it (#158), and holding
  a filled pad still only loads. Scene launch 1–4 (points, lines, faces,
  rotate) work and light the same on both layers, their LEDs always the
  live state. Every load darkens every control the new preset does not
  draw, and lets go of every fader it binds. SYSTEM → **midi** → "desk
  log" lists the last twenty presses: the control, what it did, the
  layer.
- **Code.** `apc40.SAVE`, `apc40.TOGGLES` and their invariant rows in
  `DEFAULT_MAP`; `routing.SAVE_PARAM` (`desk.save`, registered in
  `register_desk`), `routing.save_refusal`, `save_missing`,
  `TOGGLE_DESK_ROWS` (part of `RETIRED_DESK_ROWS`), five rows in
  `APC_NEW_ROWS`; `library.Project.save_into` (filled slots too),
  `save_empty` (#158's hold), `_save_new`; `Param.save_into` on
  `preset.select`; `midi.MidiIO._save_tap`, `_log_press`, `_dark_desk`,
  `redraw(whole=)`, the `_hw` position seed; `midi.DeskEvent`,
  `DeskLog`, `DESK_LOG_SIZE`; `ui.desk_log_lines`, `Panel._desk_log`;
  `preset.file_desk` (the fresh desk plus the four old toggle rows, so
  the generator still writes byte-identical factory files);
  `learn.SAVE_REFUSAL`; `ui_routing.desk_target` leaves SAVE out;
  `ui_presets.slot_tip` names SAVE. `bindings.default.json` regenerated.
- **Saved and not saved.** `desk.save` is never saved, not modulatable,
  and a reconnect lets go of it. A `bindings.json` gains SAVE and the
  four toggles once, with a backup, where their controls are free; where
  the owner's own row holds clip stop 8, SAVE is not added and every
  launch says "SAVE not added: note:7:52 is yours (…)". A preset's four
  old toggle rows drop at load without a note and leave no dirt.
- **Tests.** `tests/test_desk_trust.py` (22: fake ports, a scratch
  library), notably
  `::test_the_two_handed_save_works_ten_times_in_a_row`,
  `::test_save_held_and_a_filled_pad_tapped_saves_a_new_preset_and_keeps_the_old`,
  `::test_a_save_tap_does_not_load_or_start_a_hold`,
  `::test_a_failed_save_into_a_filled_slot_leaves_the_slot_and_blinks_nothing`,
  `::test_nothing_can_latch_save`,
  `::test_the_render_toggles_are_invariant_and_their_leds_show_the_live_state`,
  `::test_every_factory_file_still_holds_the_toggle_rows_and_loads_quietly`,
  `::test_every_load_relights_the_whole_desk`,
  `::test_a_load_lets_go_of_every_fader_the_preset_binds`,
  `::test_the_desk_log_keeps_the_last_twenty_presses`;
  `tests/test_ui_routing.py::test_neither_shift_nor_save_is_a_desk_target`.
  Fixture `tests/fixtures/desk-trust/old-desk.json`.

### C2 — the faders freed

- **At the machine.** With SHIFT up the track faders S1–S8 belong to the
  loaded preset. No factory preset binds them, so they are dark until
  the owner authors fader sets. A preset whose desk binds them lights
  them and drives its params, and a fader can be learned onto any param
  from the desk like a knob. Latch SHIFT and S1–S6 are the bands'
  post-drive, S7 the master dynamics, S8 the master trim — the audio one
  latch away. MASTER is still the audio drive and the crossfader the
  master dim, on both layers. Each fader picks up its own param after a
  latch: one moved on one layer never jumps the other's. The VIEW page
  has **Points opacity** and **Lines opacity**, both at 1.
- **Code.** `apc40.TRACK_FADERS`, `SHIFT_FADERS` and the eight
  global-layer fader rows; `routing.FADER_SHIFT_ROWS` and its branch in
  `remap_factory` (an older `bindings.json` moves its eight exact fader
  rows to the SHIFT layer once, with a backup); `MidiIO.redraw(switch=)`
  re-arms every layered fader from where it physically is;
  `apc40.feedback_for` gives a learned fader no light;
  `preset.track_fader`, `knob_desk(…, faders=())`; `ViewState.lines_alpha`
  / `points_alpha`, `view.lines_alpha` / `view.points_alpha` (performance,
  modulatable, 1 by default), one factor on each of two existing alpha
  lines in `Renderer.draw_scene`, after the floor; the slider pair in
  `Panel._page_view`. `bindings.default.json` regenerated.
- **Tests.** `tests/test_desk_faders.py` (13), notably
  `::test_a_preset_with_fader_rows_lights_s1_s8_and_drives_them`,
  `::test_the_fader_rows_round_trip_through_save_and_load`,
  `::test_every_factory_preset_leaves_the_faders_dark_and_shift_lights_the_audio`,
  `::test_a_fader_picks_up_its_own_param_across_the_latch`,
  `::test_a_power_up_forgets_where_a_fader_was_on_every_layer`,
  `::test_a_track_fader_is_learnable_on_the_preset_layer`,
  `::test_an_older_session_file_moves_the_fader_rows_to_shift_once`,
  `::test_an_opacity_at_zero_takes_its_layer_away_and_one_changes_nothing`;
  the golden frames all match (opacity 1 is the old picture). Fixture
  `tests/fixtures/desk-faders/faders.json` (FADERS: S1–S8 on points
  opacity, lines opacity, pattern mix, bitmap alpha, brightness, speed,
  field amp, dream mix). About twenty older tests that used S1 or S3 as
  "an invariant fader" now use MASTER or the crossfader.

### C3 — coverage, templates, ranked click-to-map

- **At the machine.**
  [`assets/24-party-fixes/desk-coverage.md`](assets/24-party-fixes/desk-coverage.md)
  shows, for every factory preset, which of the 38 preset-layer controls
  are mapped (●), dark (·) or dead (✕: a row whose param the preset
  cannot show), why each dead one is dead, and the bar.
  `uv run python tools/desk_coverage.py` rewrites it, `--check` says
  whether it is stale, and `--library DIR` prints a report with that
  library's presets and templates too, copying them and never writing
  there (not yet run against the owner's library). A preset file may say `"desk_template": "<name>"` and keep
  only its overrides in `desk`; templates live in the library's `desk/`
  folder. Clicking a control on the on-screen desk lists this preset's
  params first, ranked, under the transport row, with an "all params ▾"
  chip for the rest; a click on one maps the control there.
- **Code.** `tools/desk_coverage.py` (`layer_controls`, `coverage_of`,
  `build`, `read_report`); `learn.cannot_show`, `learn.ranked` and the
  tiers `ROUTED`, `MOVED`, `ON`, `DESKED`; `library.DESK`,
  `DESK_SCHEMA`, `Library.desk_template` (and no group default for
  `desk`); `preset.TEMPLATE_KEY`, `DARK`, `is_dark_row`, `template_doc`,
  `expand_desk`, `compact_desk`, the template branch in
  `Presets.load_doc`, `Presets._desk_part`, `template_of_loaded`,
  `_at_load`; `ui_desk.OFFER`, `OFFER_ALL`, `OFFER_SHORT`, `_offer`.
- **Tests.** `tests/test_desk_coverage.py` (11), notably
  `::test_the_committed_report_is_fresh_and_regenerates_byte_identical`,
  `::test_cannot_show_is_the_rule_by_group`,
  `::test_ranked_puts_the_presets_own_params_first_in_tiers`,
  `::test_the_offer_covers_no_control`,
  `::test_a_picked_control_is_offered_this_presets_params_and_a_click_maps_it`
  (real mouse clicks on a hidden window);
  `tests/test_desk_templates.py` (11), notably
  `::test_the_desk_group_ships_empty_and_lists_the_users_templates`,
  `::test_a_template_in_the_shared_library_is_found`,
  `::test_a_save_round_trips_the_reference_not_the_expanded_rows`,
  `::test_a_missing_template_is_a_note_and_the_overrides_alone`,
  `::test_a_template_fixed_after_the_load_changes_no_override_on_save`,
  `::test_every_factory_preset_loads_and_saves_its_plain_desk_as_before`.
  Fixtures `tests/fixtures/desk-templates/desk/fixture-shape.json` and
  `…/presets/templated.json`.

**The coverage, as reported** (preset layer = 38 controls; the owner's
bar for the authoring pass is at most 4 dark or dead; **no preset was
remapped to meet it**):

| preset | mapped | dark | dead | dark + dead |
| --- | ---: | ---: | ---: | ---: |
| ACID | 29 | 8 | 1 | 9 |
| BIG BLUE WAVE | 25 | 12 | 1 | 13 |
| EMBER ORBIT | 25 | 12 | 1 | 13 |
| FACES | 25 | 12 | 1 | 13 |
| FIELD | 25 | 12 | 1 | 13 |
| hands-fx | 28 | 8 | 2 | 10 |
| hands-orbit | 23 | 12 | 3 | 15 |
| hands-pinch | 26 | 9 | 3 | 12 |
| hands-play | 23 | 12 | 3 | 15 |
| HEX ENGINE | 25 | 12 | 1 | 13 |
| INVERSE HALO | 25 | 12 | 1 | 13 |
| legacy6 | 23 | 12 | 3 | 15 |
| lfo-breathe | 27 | 9 | 2 | 11 |
| MANDALA | 29 | 8 | 1 | 9 |
| NOITA | 29 | 8 | 1 | 9 |
| PLASMA HEART | 25 | 12 | 1 | 13 |
| SPIRAL SILK | 25 | 12 | 1 | 13 |
| STROBE CAGE | 25 | 12 | 1 | 13 |
| TRACER | 28 | 8 | 2 | 10 |
| TRIP | 29 | 8 | 1 | 9 |
| TUMBLE | 25 | 12 | 1 | 13 |
| WAKE | 29 | 8 | 1 | 9 |
| WOVEN LATTICE | 23 | 12 | 3 | 15 |

0 of 23 meet the bar. S1–S8 are dark on every preset (eight each, since
C2 gave the faders to the presets and no preset binds them yet). K7
(bitmap opacity) is dead on all 23 (no bitmap file, or the faces off);
K4 and D4 (pattern mix, pattern) are dead where the faces are off.

### C4 — the dance sources (H2)

- **At the machine.** Nothing changes until a route names one: no
  preset uses them. The HANDS page has a column beside the axis rows:
  per hand five curl bars, spread, energy and flick; then gap and twist.
  ROUTING's source combo offers each by name ("hand R curl ind", "hands
  gap"). The twelve axes are as they were.
- **Code.** `hands/signal.py`: `unit`, `Smooth`, `Flick`.
  `hands/core.py`: the `DANCE` constants (`CURL_RANGE`,
  `CURL_RANGE_FINGER`, `SPREAD_RANGE`, `ENERGY_RANGE`, `FLICK_ON`, …,
  `GAP_RANGE`, `TWIST_FULL`, `PAIR_RESTS`); `bend`, `curls`, `spread`,
  `points`, `gap`, `twist`; `Dance` (one hand's state); `addresses` and
  `Layout` put eight lanes per hand after the pinch switches; the
  two-hand `hands` scheme (`pair_addresses`, `HandsIO.pair_lanes`,
  `pair_rests`), published and fed beside `hand`. `hands/panel.py`:
  `_dance`. The hands package still imports nothing from the host. With
  plan 27's B2 the hands device declares both schemes
  (`hands/device.py`).
- **Tests.** `tests/test_hands_dance.py` (18), notably
  `::test_an_open_hand_is_uncurled_and_a_fist_is_curled`,
  `::test_spread_is_the_fan_and_a_fist_does_not_fan`,
  `::test_a_flick_spikes_to_its_strength_holds_its_peak_and_decays`,
  `::test_twist_reads_level_for_mirror_hands_and_up_for_a_clockwise_wheel`,
  `::test_the_new_lanes_follow_the_switches_and_no_older_lane_moves`,
  `::test_every_new_source_moves_its_param_through_a_scratch_library`
  (a fixture preset with all eighteen routed, played from a synthetic
  tape: every param moves, every row lets go when the hands leave, no
  base moves), `::test_the_routing_page_offers_the_new_sources_by_name`,
  `::test_the_hands_page_shows_every_new_source`. Fixture
  `tests/fixtures/dance-sources/dance-sources.json`. The lane-count
  assertions in `test_hands_boundary.py`, `test_hands.py` and
  `test_hand_names.py` moved from 22 to the new count, and nothing else
  in them.

### C5 — the grab, and the hands on the projector (H1)

- **At the machine.** A fist lights "grab ●" (red) at the end of that
  hand's curl row on the HANDS page; hover it for the fist level against
  the two thresholds. "L grab" and "R grab" are in every gate picker
  after the eight pinches. Nothing moves until a route is gated on one:
  no preset uses it. SETUP.md's projector entry says `hands = true`.
- **Code.** `hands/core.py`: `GRAB_FINGERS`, `GRAB_CLOSE` (0.65),
  `GRAB_OPEN` (0.45), `GRAB_HOLD_S` (0.05 s), `fist`, `step_grab`,
  `grab_name`; two grab lanes after the dance lanes (the `hand` vector
  is 40 with six axes a hand); `Layout.gates` lists the pinches then the
  grabs; `HandsIO.grab`, one `Gate` per side. `hands/panel.py`: `_grab`.
  `docs/SETUP.md`: the projector entry's `hands = true`.
- **Tests.** `tests/test_hands_grab.py` (11), notably
  `::test_a_fist_reads_1_an_open_hand_0_and_the_thumb_is_left_out`,
  `::test_the_grab_is_a_schmitt_trigger_with_a_debounce`,
  `::test_the_grab_lane_closes_with_a_fist_and_holds_through_noise`,
  `::test_a_palm_only_source_never_grabs`,
  `::test_the_shape_follows_the_hand_only_while_it_is_closed`,
  `::test_the_routing_page_offers_the_grab_as_a_gate`. Fixture
  `tests/fixtures/grab-follow/grab-follow.json` (GRAB FOLLOW: the right
  hand's yaw, pitch and roll onto `camera.yaw`, `camera.pitch` and
  `rot.phase.XY` as `position` rows, each `when hand:right.grab` — the
  owner's described mapping, as a proof, not a preset).

### C6 — the palette fold

- **At the machine.** The **Palette** chip is last on the FX page, off,
  at mix 0: switching it on changes nothing until its mix is raised.
  Mode 0 folds every hue onto a slice of the wheel (`centre`, `width`)
  with saturation and value rescaled (`sat_lo`/`sat_hi`,
  `val_lo`/`val_hi`); mode 1 maps brightness through two to four anchor
  colours (a grey ramp by default). Every param is `fx.palette.*`, so a
  fader, a knob, a hand, an LFO or a band reaches it as any effect's.
  The strip shows only the open mode's rows, with `lo`/`hi` and
  `hue`/`sat`/`val` packed one row each, and the FX page fits without
  scrolling. A saved palette is an `fx` module preset; none ships.
- **Code.** `shaders/fx/palette.glsl` (`@order 95`, `@mix 0`; twenty
  params of its own); `fx.py`: the `// @mix` header directive
  (`EffectSpec.mix`, 1 when absent); `ui_fx.strip_rows`,
  `ROW_SUFFIXES`, `HIDDEN_BY_MODE`, and the page's spacing tightened.
- **Tests.** `tests/test_fx_palette.py` (8):
  `::test_the_defaults_leave_every_frame_byte_identical`,
  `::test_a_turned_up_mix_changes_the_picture`,
  `::test_the_grey_ramp_is_a_greyscale_and_a_coloured_one_is_not`,
  `::test_every_palette_param_takes_a_route`,
  `::test_a_saved_palette_is_an_fx_module_preset`,
  `::test_a_raised_floor_does_not_light_a_see_through_ground`,
  `::test_the_file_hot_reloads`; `tests/test_fx.py::test_the_palette_strip_fits_in_both_modes`.
  Fixture `tests/fixtures/palettes/fx/sunset.json`.

## Not verified by a person

Nothing of this plan has met the APC40, a real hand, the projector or
the owner's library; every proof is a headless test with fake ports, a
synthetic tape or an offscreen frame. In particular:

- **The two-handed save on the real desk, ten times in a row** (check
  148): SAVE's light, the blink velocity on a pad (`apc40.blink_of`),
  and whether the mk1 keeps up with the whole-desk dark pass (about 100
  messages a load, check 150).
- **The faders' pickup after a load and across a latch** (152, 153),
  and how the audio strip feels one SHIFT away.
- **Whether "dead" is what the owner calls dark** (155); the
  `--library` run against the owner's library.
- **The click-to-map list's legibility** at the default window size
  (157): about 107 × 79 px, five items.
- **Every dance-source range and time constant, and the grab's
  thresholds, on real Leap hands** (158–164): a relaxed hand may idle
  above 0 on the curls, a real fist may not reach 1, and the flick
  floor is a guess at the camera's jitter.
- **The palette fold by eye** (166): only that mix 0 is the old picture
  and a raised mix changes it is proven.

## Known rough edges

- The factory preset files still carry the four old toggle rows (no
  library file changed); a load drops them quietly. After the creative
  pass, `Factory.desk` and `write_factory` can point at `fresh_desk` and
  the files be regenerated.
- A fader not moved since launch or a reconnect has no position: its
  first move after a load or a latch must land within the pickup
  tolerance, or wait to cross the value.
- The desk log is in memory only, and only with the APC40 adapter up.
- An owner's row on clip stop 8 in a preset's desk drops with D6's note;
  in `bindings.json` it keeps the control and SAVE is not added.
- No UI writes or edits a desk template; editing one on disk does not
  re-apply a loaded preset (reload it). Two spellings of one knob in a
  hand-edited desk (`cc:*:16`, `cc:0:16`) lose the any-channel one on a
  round trip. An older build refuses a template's dark row. Plan 13's
  migration comparison (`same()`) sees a templated preset's overrides,
  not its expanded desk: harmless, the migration has run on both homes.
- The coverage counts the factory session's invariant controls, not the
  owner's `bindings.json`; the dead rule reads bases, so a pattern knob
  on a faces-off preset is "dead" though Faces is one button away.
- The click-to-map list is ranked at the moment of the pick, and its
  "on" tier includes an effect's blend, order and target.
- Flick and energy both fire on any fast move (closing a fist fast
  included); twist reads roll only; spread is index–pinky only; the new
  hand sources have no settings, no DAW output and no hand Learn — they
  are picked on ROUTING.
- The grab mapping uses `position`, which is absolute: a closing fist
  snaps the shape to the hand's pose rather than catching it where it
  is (that needs a relative op, plan 28).
- The palette's `mode` is a whole-number 0/1 param, the other mode's
  strip rows are hidden until it flips, and "on" at mix 0 can look
  broken (the tip says why). The FX page fits with 7 px to spare at
  worst.
- **What the launch prompt asked for that was not done as written.**
  `config.toml.rig` was not edited: it is the owner's file in
  `~/Hyperspace`, outside the repo, which this run never touches; the
  line is in SETUP.md and check 165 asks the owner to add it. The WP
  table's "two named palettes" in `library/fx/` were not shipped
  (decision 23 and C6's own text say none); one fixture proves the
  mechanism. A flick is a decaying lane, not yet a trigger kind (plan
  27's signal kinds). `hands/signal.py` was not needed for the grab: it
  reuses core's `Gate`.
