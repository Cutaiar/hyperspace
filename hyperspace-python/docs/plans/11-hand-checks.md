# Hand checks

The checks only a person at the machine can run; none has been run yet.
Each gives the steps, what passes, what fails and where in the code a
failure points, and the headless tests that show what "right" looks
like. [`../TESTING-GUIDE.md`](../TESTING-GUIDE.md) is the plain-language
version, ordered by device, and the place to start; it cites these
numbers.

## Before you start

On `main` (`git pull`, `uv sync`); group R needs plan 22, on
`plan-22-integration` until it is merged, and groups U (plan 24), W
(plan 27) and V (plan 26), on `plan-24-26-27-integration` until it is
merged. (V follows W in this file: plan 27's docs landed first.) Before
any launch of this build:

```
cp -R ~/Hyperspace ~/Hyperspace-backup-<date>     # the one to keep
cp -R ~/Hyperspace ~/Hyperspace-try               # the one to play on
```

Checks marked **(copy)** run in a terminal with
`export HYPERSPACE_HOME=~/Hyperspace-try`: the app then uses only the
copy, its `config.toml` included. `<home>` is the home in use. Run a
"Headless" line as `uv run pytest -q <nodes>` (`file::{a,b}` is the
shell's brace expansion: one node each). Edit `config.toml` with the app
closed and put back what a check changes. On a fail, note the check
number and what you saw.

**Order.**
1. (copy) First launch: keep its output
   (`uv run hyperspace 2>&1 | tee ~/first-launch.txt`) for 57 and 84;
   then 81, 83.
2. Laptop alone: 120 and 121 first (the Mac's fonts and compiler); then
   1–9, 30, 33, 38, 40, 44, 46, 48, 50, 58–64, 68, 69, 71, 91–97, and 99
   and 100 before any `[[output.screens]]` edit; 113–116, 117's keys,
   119, 122–126, 128, 130–132, 137, 138, 154, 155, 157, 166 (without
   the fader); (copy) 86–89, 118, 127, 156, 167; FL Studio over IAC: 27,
   28.
3. APC40: 31 first, then 10–12, 34–36, 39, 45, 49, 51, 54–56, 62, 69, 70,
   78, 82, 85, 117's cue knob, 149–151, 166's fader; (copy) 153 on the
   copy's first launch of plan 24, then 148, 152; (copy) 133–136, the
   macro listening session (36, 56, 82, 85 on the copy).
4. (copy) 90, last on the copy.
5. Hand camera: 72 first, nobody else in view; then 13–21, 23–25, 29,
   42, 52, 66, 73, 75–77, 80, 100, 158, 160–163; (copy) 159, 164; APC40
   in: 22, 65, 67, 74, 79, 110.
6. One projector: 26, 43, 61, 96; with the hand camera, 165.
7. The wired Xbox 360 pad: 144–147, any time; then 171, 174, 179.
   (copy) The device registry: 168 first, then 170, 173, 178, 190 on the
   laptop; 175 with the APC40 unplugged at launch; 176, 177 with a second
   MIDI controller; 169, 172, 180 with the hand camera; 181–185 with FL
   Studio over IAC; 186–189 with a phone on the same Wi-Fi.
8. Glass + projector as two outputs: 101 first, then 41, 98, 102–109,
   113 from the audience, 129; 111, 112 last.
9. The render graph (group V): 191 and 192 on the gate Mac first (the
   goldens, then every factory preset by eye), then 193–198 on the
   laptop; (copy) 211, 212, 215 on the laptop; 199–201 on the 1080p
   projector, 201 and 202 on the copy; with the hand camera (or the
   synthetic tape) 200, 203–205, 207, 209, 210, 214; 206 and 213 with the
   glass and the projector as two outputs (after 101); 216–218 (copy) with
   the recorded cloud (after 190).

## A. Laptop alone

**1. Start, run, quit; the keys.**
Headless: `tests/test_app_boundary.py::test_the_frame_runs_in_the_documented_order tests/test_routing.py::test_r_and_the_f_keys_are_table_rows_that_fire_their_params tests/test_ui_shell.py::test_the_cheat_sheet_matches_the_tables_and_the_loop_keys`.
`HYPERSPACE_FRAMES=3 uv run hyperspace`. *Pass:* both windows, three
frames, clean exit, stderr only adapter one-liners. `uv run hyperspace`.
*Pass:* party show (PRESETS: SHOW `party`) on TUMBLE; R resets view
(rotation phases, orbit, zoom, pan); F1 loads slot 1 (TUMBLE); ⇧F1
saves to `<home>/presets/tumble.json` (overrides factory TUMBLE; ×
trashes it), rewrites `<home>/projects/party.hyp.json`; `T` inert
(needs `[output] overlay = true`); ⌘R restarts, view kept; `/` cheat
sheet (off at launch): "R" ("reset view + camera"), "F1–F8" ("load
preset · ⇧ saves"), "Cmd+Z" ("undo · ⇧ redo (or Ctrl+Z)"), "Home"
("home preset (fn ←)"). *Fail:* traceback/no exit → `app.frame` /
`app.Host`; stray adapter note → its `_open_*` gate; missing row/key →
`routing.LOOP_KEY_ROWS`, ⌘R edge claim in `app.frame`.

**2. The config rename note and a bad file.**
Headless: `tests/test_config.py::test_overlay_is_an_alias_merged_under_output_and_noted_once tests/test_ui_shell.py::test_system_page_shows_a_config_error_and_notes`.
Config with `[overlay]`; launch; SYSTEM. *Pass:* one note,
"config: [overlay] is now [output] — rename the section in …"; keys
apply. Quit; `output = 3` on the **first line** (above every
`[section]`); launch. *Pass:* app runs; SYSTEM, warning colour:
"config: [output] must be a table, not 3", rest read — or, with an
`[output]` section too, a parse error, all defaults. Remove the line;
move `[overlay]` keys under `[output]`, delete `[overlay]`: note gone.
*Fail:* no note, or crash → `config.load`.

**3. Sound from the microphone.**
Headless: `tests/test_audio.py`.
AUDIO: inputs list MacBook mic (BlackHole if installed, chosen, as
"● BlackHole…"; source `System ·` once capturing). `M`; clap. *Pass:*
one macOS mic prompt; ANALYZER: six white input columns jump and
settle, red output columns follow. House show (PRESETS → show ▾ →
`house`), F1 (BIG BLUE WAVE, lane per rotation rate): rotation moves
on a clap. Enable another input (USB mic or BlackHole's), **rescan**:
it appears, choice kept. *Fail:* no prompt, flat meters →
`AudioEngine.start_mic` / callback (`audio.py`); meters pinned, warning
blinking, quiet room → analyzer warm-up; choice lost →
`AudioEngine.rescan`.

**4. Every page fits and reads from a distance.**
Headless: `tests/test_ui_shell.py::test_every_page_fits_the_control_window`;
`uv run python tools/control_shots.py` (then `--hands`, `--bands`)
writes PNGs, prints where. All fourteen pages from two metres. *Pass:*
all readable; no page scrollbar (ROUTING's row list scrolls in its
box); HANDS fits, tracker on (check 14). *Fail:* scrollbar → layout in
`ui.py` / `hands/panel.py`; unreadable → `ui.load_fonts` / palette.

**5. The effects by eye.**
Headless: `tests/test_fx.py::test_every_factory_effect_compiles`,
`uv run pytest -q tests/test_plan12_presets.py -k effect`;
`uv run python tools/fx_shots.py`: PNG per effect.
FX strip: `acid`, `noita-tripping`, `noita-heavily-tripping`; toggle
**Effects**; **FX mix** 0. Running: save an edit to a
`shaders/fx/*.glsl`, then a syntax error, then `git checkout`. Party:
F6, F7, F8; turn one extra effect on, same F-key again. *Pass:* Effects
off = plain; presets distinct; FX mix 0 = off; edit shows within a
second; syntax error keeps last good picture, error on page. F6 (ACID)
lights exactly acid, wobble, deconverge, hue cycle; F7 (MANDALA)
plasma, kaleidoscope, fractals, glimmer; F8 (NOITA) trip warp, trip
colour, fractals, double vision; F-key again drops the extra; note under
status: preset load resets the stack. Factory presets aim every effect
at the frame (faces: check 91). *Fail:* presets alike →
`library/fx/*.json`; chip wrong → preset values
(`preset.party_*_values`, generated); compile error blanks frame →
`FxChain` (`fx.py`) or `_common.glsl` (broken one falls back to
shipped, noted on LOOKBACK).

**6. Cut-through, and no see-through window.**
Headless: `tests/test_lookback.py::{test_cut_through_never_cuts_an_opaque_ground,test_cut_through_still_cuts_in_overlay_mode}`.
White page full screen behind. `F`; FACES: a pattern; VIEW: toggle
**Cut-through**, windowed and OUTPUT → **Fullscreen**. *Pass:* solid:
black ground, faces lit, no desktop. Quit; `overlay = true` under
`[output]`; launch; `T`; toggle Cut-through. *Pass:* window floats;
on: desktop where faces overlap; off: faces opaque, ground see-through
(OUTPUT → **Ground**, 0 clear … 1 black); `T` again: window back.
Remove the line. *Fail:* desktop through faces, windowed/fullscreen →
`bg_alpha < 1` rule in `render.py` `draw_scene`, or an FX pass
(`FxChain.opaque`); no difference in overlay → blend in `render.py`;
desktop through, off, overlay → separate-alpha path.

**7. The LFO page, B and ⇧B.**
Headless: `tests/test_tempo.py::test_three_taps_at_140_read_140 tests/test_lfo.py::{test_a_tap_does_not_move_a_running_synced_lfo_but_the_trigger_does,test_a_trigger_after_this_frames_step_lands_phase_zero_on_the_next_step}`.
PRESETS: `lfo-breathe`; LFO. Music (`K` plays AUDIO's file) or 140
metronome. `B` ×4 on the beat, `⇧B` on the "one". *Pass:* 140 ± 1 BPM;
beat light on beat; LFO 1 one sine a bar, brightness swelling from ⇧B;
further `B` taps move the reading, never the swell (before or after
first ⇧B); trigger chip = ⇧B. *Fail:* swell jumps on tap → `Clock.tap`
/ `set_bpm` (`tempo.py`); BPM off > 1 → burst maths; no swell →
`lfo:0 → view.bright` on ROUTING (on?).

**8. Code edits take effect while running.**
Headless: `tests/test_hotreload.py::{test_every_package_module_but_the_cold_core_is_watched,test_reloading_params_keeps_kind_identity}`.
Running: `hyperspace/lfo.py` `wave()`:
`return math.sin(2 * math.pi * x)` → `4 * math.pi * x`; save. *Pass:*
LFO 1 doubles within a second; SYSTEM "hot reload: watching".
`git checkout hyperspace/lfo.py`. `touch hyperspace/params.py`: `F`,
`P`, `L` still switch; SYSTEM no error, no "restart" line. *Fail:* no
change → `hotreload.MODULES`; dead switch → `HotReloader` enum
preservation; "restart" with no enum changed → its sticky-note logic.

**9. Tuning the dream; the rare stall; the trail in seconds.**
Headless: `tests/test_dream.py`, `uv run pytest -q tests/test_lookback.py -k "trail or per_frame"`;
`uv run python tools/dream_shots.py --layer conv3_3 --frames 90` (then
`--layer conv4_3`, and `--preset party-wake`).
`[dream] enabled = true` (default). LOOKBACK: DREAM status names a
device ("dream worker on", not "echoes only: no worker"). Strip:
`default`, `tracer-only`; **Look-back** on; music. Try layers from the menu,
**passes**, **strength**, **speed**, colour cells (hue, saturation,
tint, tint from); save two or three keepers to `<home>/dream/` to ship.
*Pass:* dream in own colours, re-tinted by the cells, echoes not;
**shape hides** keeps dream off shape. Ten minutes of footer frame
rate: rare stall (~1 in 300) is one dropped frame. PRESETS: TRACER,
then F4 (WAKE); hover **fade time**, **time apart**, **count**: each
explains in seconds; TRACER's ECHOES note
"24 × 67 MS · THE TRAIL REACHES 1.60 S", trail a clear fan behind the
shape; WAKE's trail past the faces, dream painted in. 120 Hz screen →
60 Hz (System Settings → Displays): same trail length. *Fail:* stall >
a frame, or every few seconds → `DreamWorker.submit` blocking
(`dream.py`); no dream → `[dream]` gate, SYSTEM note (`_open_dream`);
half trail at 120 Hz → look-back clock not ticked
(`Renderer._draw_frame` → `Lookback.tick`); your look-back preset
changed → `lookback.migrate_values` (old kept as
`<file>.bak-v2-frames`).

## B. APC40

**10. Mode, knobs, rings, pickup.**
Headless: `tests/test_bridge.py::test_a_port_that_stays_missing_is_looked_for_less_often`.
`uv run python tools/midi_probe.py` (prints messages, lights desk),
Ctrl-C. App, ANALYZER. *Pass:* mode 0x42 at launch (LEDs laid out,
rings lit); K1–K8 move VIEW faders; D1–D8 do the preset's job (TUMBLE:
D1–D4 4D depth, yaw, pitch, pattern; D5–D8 dark, check 85), SHIFT
latched: open band strip; S1–S8 move band post drive, either layer;
after G7·1–G7·8 changes band, ring redraws, knob continues from it
(check 31); fader waits until it passes the value. On-screen desk
(control window bottom-left) lights each control. Quit, unplug,
launch, wait twenty seconds, plug in: lit within ten seconds (five
tries two seconds apart, then every ten). *Fail:* no LEDs →
`apc40.enter` / `[midi] port`; wrong param → `apc40.DEFAULT_MAP` (its
`layer`); knob jumps back → check 31; fader jumps → pickup in
`MidiIO._apply`; late desk never found → `midi.retry_after`.

**11. Rings show the setting, LEDs show the state.**
Headless: `tests/test_midi.py::{test_ring_shows_the_base_and_never_chases_a_performer,test_select_buttons_and_led_state}`.
House, F1 (BIG BLUE WAVE), music. *Pass:* track rings steady at
setting; scene-launch LEDs (points, lines, faces, rotate) show switches,
flip at once. ROUTING: `lane:0 → view.faces`, push: FACES LED follows
sound, panel tick shows setting. Delete route. *Fail:* ring chases
sound → `MidiIO.feedback` reading effective value.

**12. TAP TEMPO, NUDGE, METRONOME, QUANT and the pad grid.**
Headless: `tests/test_presets.py::test_a_step_or_cycle_on_the_bank_skips_empty_slots`.
Check 7 on the desk: TAP TEMPO (B20) ×4, METRONOME (B12) on the "one".
*Pass:* as check 7; METRONOME LED on beat; NUDGE + (B22) / − (B21)
`tempo.nudge` ±0.01, swell follows; QUANT (B10) next filled slot; row 1
(G1·1–G1·8) slots 1–8, rows 4–5 slots 9–24, both layers (check 82);
SHIFT: row 2 + row 3 pads 1–3 pick one of eleven band scenes; no SHIFT:
row 3 pads 5–8 field motion; cue knob steps shape; STOP ALL (G6·9)
resets bands to selected scene, again within 8 s undoes (ANALYZER
button relabels). *Fail:* METRONOME LED steady → `lfo.trigger`'s `lit`
(`tempo.py` `on_beat`); button on an older job → old row kept in
`bindings.json` (`remap_factory` moves only unused sources), listed in
ROUTING's session section; delete it by hand.

## C. Hand camera

**13. Real hands through the probe.**
`uv run python tools/hands_probe.py`. *Pass:* hands appear within a
second; every axis's native, shaped, MIDI values move; `pinch_*` gaps
live; Ctrl-C exits cleanly. *Fail:* no frames → Ultraleap Hand Tracking
service, or `LEAPSDK_INSTALL_LOCATION`; hand seen only very high →
`[hands] mode` (desktop vs screentop).

**14. The HANDS page and the angle signs.**
HANDS. *Pass:* dots (left white, right red) track palms; roll
thumb-up, pitch fingers-up, yaw fingers-outward read up, both hands;
eight switches close on pinch, show gap; page fits (switches beside
box, feel knobs two a row). *Fail:* wrong sign → `features()` in
`hands/core.py`; meanwhile flip that axis's invert, note it.

**15. Calibrate the box** — run as check 72.

**16. The default feel, saved as the factory setup.**
Headless: `tests/test_hands.py::test_follower_catches_a_returning_hand_instead_of_jumping`.
PRESETS: `hands-play`. Raise/lower right hand; watch brightness.
Defaults: Steadiness 1 Hz, Response 4, Catch 150 ms, Return 500 ms,
bounce 0.15, dead zone 0.04 (centred axes). Tune. *Pass:* no shimmer
at rest, no lag fast, re-entry glides. Save from HANDS strip as
`factory` (`<home>/hands/factory.json`), hand over to ship. *Fail:*
shimmer → Steadiness too high; lag → Response too low.

**17. Tilt and turn held apart from height.**
PRESETS: `hands-fx`. Right hand still; tilt (pitch), turn (yaw).
*Pass:* `fx.acid.twist` (tilt), `fx.acid.bend` (yaw) move; `fx.mix`
(height) within a few percent. *Fail:* height moves → widen right y
dead zone, or note as feel finding (palm pose, not fingertips').

**18. The thumb-to-ring pinch.**
HANDS; watch ring gap. Pinch thumb to ring deliberately; open. *Pass:*
gap < Pinch close (0.34 × palm), switch closes; past 0.46 releases.
*Fail:* never below 0.34 → note the gap (global `hands.pinch_close`,
not per finger).

**19. A hand Learn on a performed param asks first.**
Headless: `tests/test_ui_routing.py::test_the_replace_prompt_swaps_the_owner_or_leaves_the_table tests/test_hands.py::{test_a_learn_on_a_performed_param_is_held_for_the_prompt,test_a_hand_learn_needs_no_midi_adapter}`.
PRESETS: `hands-play` (R height positions Brightness). VIEW: right-click
Brightness → **Learn hand ▸ left**; move left hand. *Pass:* footer
"learning view.bright — move the left hand…" on every page, left hand
only; prompt ("ONE PERFORMER PER PARAMETER",
"Brightness is already performed by R height positions.",
"L height positions asks for it.", **Replace** / **Keep**) on any page;
nothing more learnt while up. **Keep**: ROUTING unchanged. Again,
**Replace**: row "L height positions", ends "moved from view.speed"
(preset's left-height Speed row gone, check 77), unsaved dot lit,
`<home>/bindings.json` untouched. Tilt moved most → "pushes +0.25"
(check 75): pass too. Optional: `[midi] enabled = false`, relaunch,
repeat: works; restore. *Fail:* no prompt → `Learn.learn_source`
(`learn.py`) / `Bindings.add`; wrong axis → `_learn` (live axis moved
furthest).

**20. `hands-pinch`: pinch zoom while scrolling.**
Headless: `tests/test_routing.py::test_audit_1_a_relative_writer_on_the_base_holds_under_modulation`.
PRESETS: `hands-pinch`. Pinch L middle, move left hand: zoom follows.
Keep pinching; scroll render window (wheel/trackpad). *Pass:* no
runaway; release: zoom at scroll's value, not hand's. *Fail:* drift →
`Mouse.poll` reading effective (`Param.scale` must read base); jump to
hand's value → gate / `Registry.apply`.

**21. The right hand deepens `lfo-breathe`'s swell.**
PRESETS: `lfo-breathe`; LFO. Raise right hand. *Pass:* LFO 1 depth
ghost bar rises, swell deepens a frame later, nothing else moves
(speed, zoom, effects); hand down/out: depth 0.6. *Fail:* other
movement → route in preset (ROUTING); depth stuck → `Follower.live`.

**22. A knob on a hand-owned param.** (APC40)
Headless: `tests/test_routing.py::test_audit_3_a_knob_moves_the_return_value_under_a_hand tests/test_hands.py::{test_a_hand_leaving_the_box_releases_its_position_row,test_a_hand_outside_the_box_releases_its_rows_and_the_base_returns}`.
PRESETS: `hands-play`; right hand in box (owns Brightness). Turn K1.
*Pass:* setting moves (readout base, ring), gliding with knob
smoothing (80 ms at launch); picture doesn't; hand out (past its faces,
check 73): brightness at knob's value at once, no fade to minimum.
"pushes" rows likewise. *Fail:* 0.13× on leaving → `NaN` rule in
`HandsIO.lanes` (`hands/core.py`); knob dead, hand in → base written
under a hand.

**23. A gated row on a second pinch at another height.**
Headless: `tests/test_hands.py::test_pinch_gate_needs_the_wider_gap_to_let_go`.
`hands-pinch`: pinch R index low (dark), open, raise, pinch. *Pass:*
new height at once (hands grab, never yield); base back on open. Judge
whether the jump wants the 150 ms catch glide on gate open.

**24. A hand leaving the box, and `hold`.**
Headless: `tests/test_hands.py::{test_hold_shapes_the_daw_output_but_never_latches_a_row,test_a_returning_hand_glides_its_row_back_on_through_the_catch}`.
`hands-play`, HANDS. Right hand out. *Pass:* its rows dim,
"DAW only; lane —"; brightness at base that frame. Right height
**On exit** *hold*: DAW holds, picture returns. Re-enter: row glides
on. *Fail:* parked at rest value → `Follower.live`.

**25. Hand-to-picture delay.**
`hands-play`. Phone-film box and render window at 120 fps; flick a hand
up; count frames to brightness change. *Pass:* < ~4 frames at 60 fps
(camera ~8 ms + render frame + follower attack); unmeasured target.
*Fail:* more → axis attack or Steadiness; hand-to-DAW also
`[hands] rate`.

## D. Projector

**26. Choosing the screen; overlay shut by the config.**
Headless: `tests/test_overlay.py::{test_follow_window_is_the_first_choice_and_reads_back_as_itself,test_overlay_refuses_every_road_while_the_config_shuts_it} tests/test_app_boundary.py::test_the_render_window_is_transparent_only_when_the_config_asks`.
Projector in before launch. OUTPUT: **Screen** lists "follow window",
then screens by name; projector, **Fullscreen** on. *Pass:* render
window fills projector at its DPI (edges laptop-sharp); control window
on laptop; no `overlay` key: Overlay greyed, note
"overlay off in the config: set [output] overlay = true in config.toml",
`T` and MASTER select (G7·9) inert (crossfader = master dim, check 55);
"follow window", Fullscreen off: a window. `[output] monitor = 1`,
`fullscreen = true`, relaunch: straight to projector. Screen/Fullscreen
are output 1's; `[[output.screens]]` overrides (check 101). *Fail:*
wrong screen → `overlay.Output.apply` (GLFW order); blurry → `dpr` in
`Renderer.draw_outputs` / `_draw_frame`; see-through or `T` floats
without `overlay = true` → `app._overlay_allowed` /
`Output._set_overlay`.

## E. IAC and FL Studio

Audio MIDI Setup → IAC Driver: "Device is online", one bus.

**27. The bridge out, and its line on SYSTEM.**
Headless: `tests/test_bridge.py tests/test_ui_shell.py::test_system_page_shows_the_bridge`.
`[bridge] enabled = true, out = "IAC"`. *Pass:* SYSTEM bridge line:
port, `pitch`, 16 lanes, `sent` rising with music; FL Studio (IAC in,
Fruity Formula or Peak Controller on pitch bend, channel 1) follows
band 0. *Fail:* "bridge: no port" → IAC name (`out` is a substring);
no line → `panel.bridge` unset (`app.py`). Restore `enabled = false`.

**28. External lanes in (`ext:`).**
`[bridge] in = "IAC"` (second bus, or FL's MIDI out). ROUTING:
`ext:0 → view.bright`, push, depth 0.5. FL pitch bend, channel 1.
*Pass:* brightness follows; FL stopped: base within a frame. *Fail:*
nothing → `[bridge] encoding` both ends, or row off. Delete route.

**29. The hands' own DAW port.** (hand camera)
Headless: `tests/test_hands.py::{test_a_lost_daw_port_is_looked_for_again_and_the_daw_resynced,test_a_daw_port_that_stays_missing_is_looked_for_less_often}`.
FL sees "Hyperspace Hands" (app's virtual port); right height = CC 109,
channel 16 (`[hands] cc = 102`, six per hand). Rejoin: `[hands] out =
"IAC"`, launch, IAC bus offline, back; restore `out`. *Pass:* rejoined,
presence notes re-sent: within 2 s if back within ten seconds, else
10 s (five tries two seconds apart, then every ten). *Fail:* no rejoin
→ `HandsIO._open`.

## F. An old mapping file

**30. A backup before an old `bindings.json` is converted.**
Headless: `tests/test_routing.py::test_a_backup_is_kept_before_every_rewrite_and_never_over_a_hand_made_one tests/test_migration.py::test_a_home_with_no_project_keeps_its_routes_in_a_migrated_preset`.
Needs hand-made `~/Hyperspace/bindings.json.bak-plan09` (else skip).
`mkdir -p /tmp/h && cp ~/Hyperspace/bindings.json.bak-plan09
/tmp/h/bindings.json`, then `HYPERSPACE_HOME=/tmp/h HYPERSPACE_FRAMES=3
uv run hyperspace`, twice. *Pass:* run 1 prints sort, remaps,
"backup: bindings.json kept as bindings.json.bak-v1", three `migrate:`
lines; `/tmp/h/` has `bindings.json` (session controls),
`bindings.json.bak-v1` (old), `presets/migrated.json` (routes, knobs,
macros as MIGRATED), `projects/mine.hyp.json` on it. Run 2 writes
nothing. Real home's hand-made backups untouched. *Fail:* no `.bak-v1`
→ `routing.backup` (`preset.migrate_home`); backup overwritten →
dated-copy path in `backup`. Delete `/tmp/h`.

## G. The desk's knobs; the party presets

**31. The APC40's knobs re-base from the host.**
No headless twin. House show, F1 (BIG BLUE WAVE, brightness 1.25×); K1
to ~¼; F2 (EMBER ORBIT, 1.5×); nudge K1. *Pass:* ring jumps to the
preset's brightness; turn continues from there. *Fail:* first turn
snaps to the knob → encoder ignores host CC; knobs need soft pickup
(`midi.py` `_apply`); check 35's knob half fails too.

32 — covered by check 41.

## H. Presets and the two-layer desk

**33. The older home conversion lost nothing.**
Headless: `tests/test_migration.py`.
Launch, read stderr, diff `ls -la ~/Hyperspace` with the backup (if
already converted, no `migrate:` line; check the result). *Pass* (if it
converts now): a `migrate:` line per rewritten file naming its backup
(`projects/<name>.hyp.json.bak-v1`, `bindings.json.bak-v2`, or dated)
and one per preset written. *Pass* (either way): `<home>/presets/` has
a preset per filled slot per show (factory-equal slot points at it;
taken name → `<name> 2`); shows open on their old look ("starts on":
equal slot or `<SHOW> SAVED`); converted `default` is `mine`;
`bindings.json` holds only your keys, pad, MIDI rows (no route,
preset-layer knob or macros), band-strip device knobs
`"layer": "global"`; learned hand rows and knobs in the startup preset
(ROUTING routes, DESK); `<home>/bindings/` intact plus `NOT-READ.txt`;
hand backups untouched. Second launch: silent, no file changes.
*Fail:* slot missing → `preset.migrate_project`; learned row gone →
`routing.Bindings.carried`, `preset.migrate_home`; backup overwritten →
`routing.backup`.

**34. SHIFT latches and lights.** (APC40)
Headless: `tests/test_desk.py::{test_shift_latches_the_layer_and_lights_its_led,test_shift_release_never_reevaluates_a_held_button}`.
Tap SHIFT. *Pass:* LED stays lit; device knobs move the open band strip
(ANALYZER); K1–K5 = Steadiness, Response, Catch, selected axis's Return
(HANDS), BPM; K6–K8 dark, dead. SHIFT again: LED off, preset meanings
back. Hold a filled row-4 pad, tap SHIFT, release: one load only.
*Fail:* LED dark latched or lit only held → latch in `MidiIO._handle`;
knob keeps preset meaning → row's `layer` (`apc40.DEFAULT_MAP`, your
`bindings.json`); action on release → read modifier at press.

**35. A layer switch: the knobs jump, the faders pick up.** (APC40)
Headless: `tests/test_desk.py::{test_a_layer_switch_rebases_the_knobs_and_leaves_the_faders_to_pick_up,test_a_preset_load_clears_the_faders_catch}`.
After check 31 (failed → skip knob half). K1 to ¼; SHIFT (K1 =
Steadiness); nudge; SHIFT. *Pass:* ring jumps to each layer's value;
turns continue from it. ANALYZER: mouse SUB's drive to top; raise S1
from bottom: inert until it passes, then follows. *Fail:* knob snaps
back → check 31; fader jumps → pickup in `MidiIO._apply`.

**36. An unmapped control is dark and does nothing.** (APC40, copy)
Headless: `tests/test_desk.py::test_an_unmapped_control_is_dark_and_does_nothing`.
Factory F1 (TUMBLE). *Pass:* D1–D4 lit (4D depth, Yaw, Pitch, Pattern;
check 85); D5–D8 rings off, dead; ROUTING's DESK · PRESET LAYER lists
them dimmed, "D5  unmapped — dark" to "D8" (hover: "device knob 5 · …");
on-screen desk dark too. SHIFT latched: all device knobs lit (device
and screen, ⇧ red), moving the band strip; ROUTING head DESK LAYER:
GLOBAL. Own TUMBLE saved before D1–D4 mapped: all eight dark. *Fail:*
lit unmapped ring → dark rule in `MidiIO.redraw`; band strip moves
without SHIFT → global fall-through (`MidiIO._handle`); dead knob
unlisted → `ui_routing.unmapped`.

37 — covered by check 65.

**38. A preset load lands every base and replaces every route.**
Headless: `tests/test_presets.py::{test_a_preset_load_lands_every_base_and_replaces_every_route,test_a_preset_load_never_touches_a_session_param}`.
Party show, F5 (TRIP: effects on); tap `B` ×8 at ~100 BPM; F1 (TUMBLE).
*Pass:* all effects off (FX), look-back default, ROUTING has TUMBLE's
rows, no `fx.*` row; BPM ~100; band scene unchanged. F6 (ACID) → F1:
same. F8 (NOITA) → F4 (WAKE): effects off, WAKE's look-back on (24
echoes, fade 0.60 s) with dream, no extra step. *Fail:* effect on → a
group `Presets.load_doc` missed; BPM reset → `tempo` classed performance
(`params.SESSION_GROUPS`); `fx.*` row left → route replacement.

**39. One macro, two directions.** (APC40)
Headless: `tests/test_macros.py::test_base_subscribers_of_opposite_polarity_move_opposite_ways tests/test_presets.py::test_lfo_breathes_macro_moves_brightness_up_and_speed_down`.
PRESETS: `lfo-breathe` (knob at bottom: brightness 1×, speed 0.25×).
Sweep D1 (macro 1, "Breathe") up and back. *Pass:* brightness 1× → 2×
as spin slows 0.25× → ~0.06×, smoothly together; LFO's effect-mix
breathing deepens from zero; ROUTING MACROS: knob 1 "Breathe", two
`base` lines (param, `from`, `to`; `from` above `to` runs reversed), one
`depth` line naming the LFO route. *Fail:* same direction → `from → to`
(`preset.BREATHE_BRIGHT` / `BREATHE_SPEED`; regenerate:
`python -m hyperspace.preset`); nothing → base-follow (`routing.py`) or
desk row (`preset.lfo_breathe_desk`).

**40. What the show starts on.**
Headless: `tests/test_presets.py::test_the_startup_preset_loads_on_launch tests/test_ui_presets.py::test_starts_on_is_labelled_and_saved_when_set tests/test_party_show.py`.
Launch. *Pass:* party show (full name, "factory", no unsaved dot) on
TUMBLE. PRESETS: STARTS ON / HOME → WAKE (saved at once; first write of
a factory show makes `<home>/projects/party.hyp.json`). Relaunch.
*Pass:* WAKE, desk lit for it, status line says so. **show ▾** →
`house`; relaunch: house opens (`<home>/last_show`). Reopen party, set
"starts on" to TUMBLE. *Fail:* dark desk or wrong look →
`Project.startup`, startup load in `app.main`; pick lost →
`ui_presets.set_starts_on`; wrong show → `Library._open_default` /
`last_show`.

**41. The party presets on the rig.** (glass, projector, camera, APC40)
Headless: `tests/test_plan12_presets.py::{test_the_party_presets_load_by_f_key_as_presets,test_wake_and_trip_device_knobs_move_their_bases}`;
`uv run python tools/preset_shots.py` writes pose sheets, prints where.
Party show: F1 TUMBLE, F2 FACES, F3 FIELD, F4 WAKE, F5 TRIP, F6 ACID,
F7 MANDALA, F8 NOITA; TRACER from list (slot 9). Hands per card:
`docs/plans/assets/12-presets/party-*.md`. TRIP: TAP TEMPO ×8,
METRONOME once first. *Pass:* (a) faces at 2.5× (FACES), 2.0× (TUMBLE,
WAKE) read in the room; left-hand headroom to 4× usable, no white-out;
(b) ±45° tilt feels held; half-second spring on leaving reads "let
go", not a slip; (c) thumb up = up, fingers out = out, reach in = away,
every row (cards' words); (d) FIELD, right hand top (69 copies, faces
on): frame rate holds; 0.65-cell swing a look, not a mess; (e) WAKE +
dream: right roll turns dream hue, fingers up bring dream in, wake reads
past faces; (f) TRIP: left height opens an on-beat pump; right-top
burst light, not glare; (g) ACID, MANDALA, NOITA, TRACER: black ground,
no hand in box (MANDALA plasma only with right fingers up); (h) device
knobs, rings showing values: WAKE — Echo brightness, Echo fade time,
Darken, Contrast, Shape hides wake, Dream brightness, Dream saturation,
Dream speed; TRIP — FX mix, Plasma level, Kaleidoscope segments,
Kaleidoscope zoom, Zoom burst amount, Zoom burst glow, Hue cycle paint,
Hue cycle spread; ACID — FX mix, Acid bend, Acid twist, Acid reach,
Acid breathe, Wobble amount, Deconverge amount, Hue cycle spread;
MANDALA — FX mix, Plasma level, Kaleidoscope segments, Kaleidoscope
zoom, Fractals amount, Fractals ground, Glimmer amount, Glimmer ground;
NOITA — FX mix, Trip warp amount, Trip warp scale, Trip colour amount,
Fractals amount, Fractals size, Double vision amount, Double vision
ghost; TRACER — Echo brightness, Echo fade time, Echo count, Echo time
apart, Darken, Contrast, Shape hides wake, 4D depth; TUMBLE, FACES,
FIELD: D1–D4 4D depth, yaw, pitch, pattern, D5–D8 dark; TUMBLE's left
height pushes audio drive, ROUTING row "session". *Fail:* (a)
`view.bright` in `library/presets/party-*.json`; (b) `preset.TURN`
(0.25; try 0.35), axes' Return; (c) depth sign in
`preset.party_*_routes`; flipped on every preset → mounting:
`hands.<axis>.invert` (HANDS, saved as hands setup); (d)
`view.instances` push depth (0.6), `view.inst_amp` (0.5) in
`party_field_routes`; (e) `[dream] enabled`, LOOKBACK worker line; (f)
pump hiccups on re-tap → `Clock.tap`; glare → `fx.zoomblur.glow` in
`library/fx/trip.json`; (h) `preset.WAKE_KNOBS` / `TRIP_KNOBS` /
`ACID_KNOBS` / `MANDALA_KNOBS` / `NOITA_KNOBS` / `TRACER_KNOBS`. Edit
the generator (`python -m hyperspace.preset`), not the files.

**42. Hand routes follow the axis by name.** (hand camera)
Headless: `tests/test_hand_names.py`.
`[hands] dofs = ["yaw", "pitch", "roll", "y", "x", "z"]` (default
reversed); launch; `hands-play`. *Pass:* right height → Brightness,
left height → Speed, right tilt → 4D depth; ROUTING: "R y positions",
"L y positions", "R pitch positions"; sources `hand R y` / `hand L y` /
`hand R pitch`; `hands-pinch`: right index pinch picks Brightness. Then
`dofs = ["x", "y", "z"]`; launch; `hands-play`: right tilt row inert (no
`right.pitch`), heights work. Remove `dofs`. *Fail:* wrong axis →
`Router.lane` / `HandsIO._publish` (`router.names["hand"]`); raw
`hand:<i>` → `ui_routing._sources` / `Router.address`.

## I. An opaque window, the stall log, the on-screen desk

**43. A black window on the projector.** (projector)
Headless: `uv run pytest -q tests/test_lookback.py -k opaque`.
White page fullscreen on projector; render window fullscreen over it
(OUTPUT: projector's Screen, Fullscreen on). `F`; F1–F5, toggling
**Cut-through** each. *Pass:* never any desktop; lit on black, either
Cut-through state, with effects (TRIP) and look-back (WAKE). Two outputs
(check 101): each; outputs after the first always opaque. *Fail:*
desktop through faces/faint lines → `render.py` `draw_scene`
(`bg_alpha < 1` rule) or `FxChain.opaque`; whole ground → overlay mode
(OUTPUT says) or `app._windows` transparent-framebuffer hint.

**44. The stall log.**
Headless: `tests/test_watchdog.py`.
Launch; other terminal: `kill -USR1 $(pgrep -f "bin/hyperspace")`.
*Pass:* `<home>/stall.log` gains thread stacks (main ends in `app.py`
`main`); app runs on; SYSTEM shows "stall log: <path> (1 raw dump)". On
any freeze or red render-error/stall banner, keep `stall.log`: entries
name kind (`stall`, `render error`, `render stall`, `stranded target`,
`non-finite`, `warning`), time, loaded preset, all stacks. *Fail:* no
or empty file → `watchdog.Watchdog.start` (error on SYSTEM); app quits
→ `faulthandler.register` not run.

**45. The on-screen desk matches the device.** (APC40)
Headless: `tests/test_ui_desk.py`.
Party show, F5 (TRIP), ROUTING; H for big desk (check 69). *Pass:*
drawing is the device face: 8 × 5 clip grid, scene-launch column right;
clip-stop row with STOP ALL; track select with MASTER; activator, solo,
rec-arm rows; cue knob in master column; nine faders at bottom; right:
eight track knobs (2 × 4) with PAN · SEND A · B · C, bank-select arrows
with TAP TEMPO, NUDGE − / + and SHIFT, eight device knobs and buttons,
PLAY · STOP · REC, crossfader. Mouse over each control, device
alongside: hover names it Akai's way, same place. Lit/dark match
device; clip grid same colours (filled bank pad amber — velocity 5 —
half strength with preset name; empty dark, glyph only; loaded green);
D1's arc follows its ring. SHIFT latched: ⇧ red, header GLOBAL LAYER ·
SHIFT, D1–D8 and K1–K5 lit, K6–K8 dark, device too. Take a glyph from
ROUTING DESK (e.g. D4), find on drawing and device, turn: its param
moves. *Fail:* misplaced → `apc40._layout`; lit mismatch → screen
`Bindings.active` vs device `MidiIO.redraw` must agree (`ui_desk.lit`);
wrong glyph → `apc40.glyph`.

**46. WAKE without the dream worker still draws.**
Headless: `tests/test_render.py::test_a_look_back_frame_with_no_worker_leaves_the_window_bound tests/test_lookback.py::test_capture_off_the_cadence_with_no_source_puts_the_target_back`.
`[dream] enabled = false`; launch; party, F4 (WAKE). *Pass:* picture
moves a minute and through F1–F5 back to F4 (shape turns, echoes
trail); red banner "WAKE turns the dream on, but there is no dream
worker ([dream] enabled = false in config.toml); the look-back shows
the echoes only" until **dismiss**; `stall.log` has the warning, no
`stranded target`. Restore `enabled = true`. *Fail:* frozen picture,
live panel → framebuffer left bound (`Renderer.draw`'s `finally`,
`Lookback.capture`'s, `ctx.screen.use()` atop `app.draw_render`);
`stall.log` names it.

## J. Ghost hands

47 — covered by check 108 (with 103, 109 and 110).

## K. Undo, home, the master dim, save-as on the desk

**48. Undo takes back one slider drag.**
Headless: `tests/test_undo.py::{test_a_slider_drag_is_one_step_and_undo_sets_only_that_param,test_a_pause_longer_than_the_settle_time_makes_a_second_step} tests/test_routing.py::test_a_chord_fires_only_its_own_row tests/test_ui_shell.py::test_the_footer_says_what_was_undone`.
VIEW: drag Brightness once, release, wait 1 s, ⌘Z (or Ctrl+Z). *Pass:*
only Brightness reverts; footer "undid Brightness … → …" ~4 s; ⌘⇧Z
redoes ("redid …"). Drag Brightness, wait, Speed, wait, ⌘Z ×2: Speed,
then Brightness. ROUTING route depth: ⌘Z restores. In a text field (a
macro's label) ⌘Z edits text only. Empty stack: "nothing to undo" every
press. Drag, hold still 1 s button down, drag on: **two** steps (say if
it should be one). *Fail:* nothing reverts → `Host.undo` not ticking
(`app.frame`) or key rows missing (`routing.LOOP_KEY_ROWS`, check 57);
two presses per drag → `undo.SETTLE_S`; ⌘⇧Z undoes → chord rule in
`Router.keys`; no footer → `Panel._message` / `Panel._footer`.

**49. Undo takes back one knob turn.** (APC40)
Headless: `tests/test_undo.py::{test_a_knob_turn_on_the_desk_is_one_step,test_undo_of_a_slider_does_not_rerun_a_load}`.
F5 (TRIP). Sweep D1 (FX mix) across, wait, ⌘Z. *Pass:* mix and ring
revert; next turn continues from ring. Latch SHIFT, nudge S1, wait, ⌘Z:
drive reverts, SHIFT lit, S1 inert until it passes the value. *Fail:*
SHIFT dropped or fader holds lost → restore did a desk replacement
(`Undo._restore`, `Bindings.set_desk`'s `load`); ring lags →
`MidiIO.feedback`.

**50. Undo a preset load.**
Headless: `tests/test_undo.py::{test_a_preset_load_is_one_step_by_every_road,test_undo_of_a_load_puts_back_the_values_the_routes_the_desk_the_macros_and_the_name,test_save_after_undoing_a_load_writes_the_earlier_preset}`.
F1 (TUMBLE); change brightness, shape, faces on (dot lights); F5
(TRIP); ⌘Z. *Pass:* TUMBLE with your changes; PRESETS TUMBLE, dot lit;
F1 lit; ROUTING TUMBLE's routes and desk; footer "undid load TRIP".
⌘⇧Z: TRIP, clean. ⌘Z, F5 by hand: nothing to redo. Load from PRESETS
list, and with QUANT (APC40): one ⌘Z each. *Fail:* look back, name
TRIP → `library.Marks`, `push(load=True)` in `Presets.load_doc`; two
presses → double push; routes missing → `Bindings.set_routes` in
restore.

**51. Undo a Learn and an Unbind.** (APC40)
Headless: `tests/test_learn.py::test_a_learn_is_one_undo_step tests/test_midi.py::test_an_unbind_is_one_undo_step tests/test_ui_routing.py::test_a_route_delete_and_a_replace_are_undo_steps tests/test_undo.py::test_a_row_that_undo_brings_back_picks_up_afresh`.
F5 (TRIP), ROUTING. `ls -l <home>/presets`. Right-click Brightness →
**Learn desk**, turn D3. *Pass:* DESK: D3 on `view.bright`, old param
gone, line ends "; K1 let go". ⌘Z: D3 restored, K1 Brightness, footer
"undid learn view.bright", dot unchanged. Right-click a desk-knob param
→ **Unbind** (submenu desk / route / both if routed); ring dark; ⌘Z:
row, ring back ("both" one ⌘Z). Delete a route (×); ⌘Z: back with
depth, gate. `ls -l`: no times changed. *Fail:* row missing → push
before edit (`Learn.learn_control`, `Learn.unbind`, `ui_routing.page`);
ring dark → `redraw_serial` in `set_desk(load=False)`.

**52. A hand moving makes no undo step.** (hand camera)
Headless: `tests/test_undo.py::{test_a_performer_moving_makes_no_step,test_an_idle_app_makes_no_step}`.
F1 (TUMBLE). VIEW: drag Brightness, wait 1 s. Play 30 s, both hands,
music on. ⌘Z. *Pass:* Brightness reverts; no hand/band/LFO move made a
step. *Fail:* "undid Speed …" (any hand param) with last-digit diffs →
`undo.REL_TOL`; `rot.phase` or BPM named → `undo.watched`.

**53. A saved-over or deleted preset goes to the trash.** — run as check
88, which covers it.

**54. Home, from any preset, on either layer.** (APC40 for the desk half)
Headless: `tests/test_presets.py::{test_home_loads_what_the_show_starts_on,test_home_with_no_starts_on_says_so_and_loads_nothing,test_home_is_one_undo_step} tests/test_desk.py::test_overdub_is_home_on_both_layers_and_is_lit`.
Party; STARTS ON / HOME = TUMBLE; OVERDUB (B11) lit. F5, edit, OVERDUB.
*Pass:* TUMBLE, desk lit; ⌘Z: edited TRIP ("undid home → TUMBLE"). F7,
SHIFT, OVERDUB: TUMBLE, SHIFT dropped (loads drop to preset layer). F3,
fn+← (Home): TUMBLE. "starts on" → "— none": OVERDUB dark, loads
nothing; each press footers "home: this show names no 'starts on'
preset — pick one on the PRESETS page"; reset: line clears. Right-click
a param → **Learn desk**, OVERDUB: TUMBLE loads silently, learn stays
armed (in TUMBLE); cancel via footer. *Fail:* OVERDUB dark/dead → its
row (`apc40.DEFAULT_MAP`; your `bindings.json`, check 57); other action
under SHIFT → row has a layer; fn+← dead → `key:HOME` in
`routing.LOOP_KEY_ROWS`, or laptop sends no Home (say so; rebindable).

**55. The crossfader is the master dim.** (APC40)
Headless: `uv run pytest -q tests/test_render.py -k dim`, then `tests/test_midi.py::test_the_crossfader_dims_with_soft_pickup tests/test_desk.py::test_the_crossfader_keeps_its_hold_across_a_preset_load tests/test_ui_shell.py::test_the_dim_is_first_on_output_and_the_footer_says_so_while_dimmed`.
Quit; crossfader hard left; launch. *Pass:* (a) full; OUTPUT row 1,
Master dim, 100%. (b) nudge from left: nothing. (c) right then left:
catches at right end, dims smoothly to black at left; footer "dim …%"
(warning colour), "dim black" at end; back right: full, readout gone.
(d) F5, F4 (look-back), ghost hands, at half: shape, effects, trail,
hands all half. (e) at half: F1, F5, OVERDUB: stays, next move
continues. (f) works with SHIFT latched. (g) quit at half, launch:
full. Two outputs: master × own (check 104). *Fail:* dark at launch →
`output.dim` saved/seeded (`Output.register`, `persist`); black at
right → direction (row `abs`; CC 0 = left unverified on device); jump
on first touch → pickup (`MidiIO._apply`); dead after load until
crossed → `MidiIO.redraw(load=True)`; hands/effect undimmed → pass not
last (`Renderer._draw_frame`); line under Master dim, no dimming →
driver refused program (`Renderer.dim_error`); preset moves it →
preset/show lands a rig param.

**56. A hold on the clip-stop row saves a new preset; a tap does not.** (APC40, copy)
Headless: `tests/test_midi.py::{test_a_hold_fires_once_at_the_hold_time_while_held,test_a_tap_fires_nothing,test_the_bar_is_one_control,test_the_bar_lights_while_held_and_the_new_slots_pad_blinks} tests/test_presets.py::{test_save_new_never_overwrites,test_save_new_fills_the_next_empty_slot_and_becomes_the_loaded_preset,test_save_new_on_a_full_bank_saves_to_the_list_and_says_so,test_the_new_slot_loads_from_the_preset_row,test_put_and_clear_slot_write_the_show_and_delete_no_file} tests/test_library.py::test_next_name_counts_on_from_a_trailing_number tests/test_ui_presets.py::test_a_slots_menu_offers_put_and_clear tests/test_desk.py::test_the_clip_stop_row_is_invariant`.
PRESETS: right-click F8 → **clear slot**: F8 "—", footer "F8: cleared —
NOITA is still in the preset list" (it is). F5 (TRIP); change the
look. (a) Tap a clip-stop button. *Pass:* row lit while held, nothing
else: no preset, no file in `<home>/presets`. (b) Hold one. *Pass:* at
0.6 s row and clip row 1 pad 8 blink 1.5 s, TRIP's pad off; release:
row dark, pad 8 green; F8 **TRIP 2**, lit; PRESETS strip TRIP 2, no
dot; footer "saved TRIP 2 → F8"; `<home>/presets/trip-2.json` exists.
(c) Pad 1 (TUMBLE), pad 8: your look. (d) Change look, hold another
button: factory party (TRACER slot 9) → slot 10, row 4 pad 2 blinks,
"saved TRIP 3 → slot 10"; own show, slot 9 free → row 4 pad 1, "→ slot
9". TRIP 2 unchanged. All twenty-four full: "saved … — the bank is
full: it is in the preset list" (row blinks, no pad). (e) Two fingers,
5 s: one preset. (f) SHIFT latched: same, stays latched. (g)
Right-click F8 → **put preset here…** (all presets, 12 rows then
scroll) → NOITA: F8 NOITA, footer "F8: NOITA", TRIP 2/3 listed; **clear
slot** greyed when empty; panel **save** still overwrites loaded
preset. (h) Right-click param → **Learn desk**, hold row: saves, silent,
learn armed. Not fails: on-screen bar lights but doesn't blink; cheat
sheet omits the bar. *Fail:* tap saves → `midi.HOLD_S`,
`MidiIO._handle`; taken slot/file overwritten → `Project.next_empty`,
`library.next_name`; no blink → `apc40.blink_of`, blink in
`MidiIO.feedback` (if clip-stop LEDs never light/blink, note behaviour:
Akai-table velocities, unseen on mk1; footer line is the sign); dark at
0.6 s, no blink or preset → save failed (`Project.save_new`; reason on
PRESETS, `bank_error`); two presets per hold → `MidiIO._fire_holds`; row
dead → its rows (`apc40.DEFAULT_MAP`; your `bindings.json`, check 57).

**57. The first launch brings `bindings.json` up to date, with a backup.** (copy, first launch)
Headless: `uv run pytest -q tests/test_routing.py -k "older_file or old_crossfader"`, `tests/test_routing.py::test_old_midi_map_migrates_into_bindings_json`.
`ls -la $HYPERSPACE_HOME`; launch keeping stderr (Before you start,
step 1). *Pass:* "backup: bindings.json kept as bindings.json.bak-v3
before the rewrite" (or dated `.bak-v3-<stamp>`), then per change
"bindings: <path>: …":
`remapped cc:0:15: overlay.bg → output.dim (the APC40 map of plan 15)`;
`added note:0:64 → preset.home (…)`; with plan 24,
`added note:7:52 → desk.save (…)` (SAVE) and the four scene-launch
toggles, and check 153's eight "moved cc:k:7 … to the SHIFT layer";
`added key:… → edit.undo` / `edit.redo` / `preset.home` (plans 09, 11,
15 keys) per missing loop key; check 84's sixteen bank-pad lines; then
"bindings: updated <path> (N rows changed)". Earlier launches' changes
not repeated. SYSTEM: same, one line. ROUTING session, under "invariant
· both layers": X → `output.dim`, B11 → `preset.home`, G6·8 →
`desk.save`, scene launch 1–4 → the four toggles (an old file's
clip-stop `preset.save_new` hold rows, retired 2026-10-09, are dropped
with a note). Hand-edited crossfader, OVERDUB, clip-stop, pad
rows and keys on those chords kept. Relaunch: silent (but "SAVE not
added …" when clip stop 8 is yours), no file times move. Note: rows are
added where **nothing uses the control**, so deleted OVERDUB/SAVE rows
return; disable via `"enabled": false`. A `bindings.json` freshly
converted from an old `midi_map.json` gets OVERDUB/SAVE rows on second
launch (which says so). *Fail:* no
backup → `routing.backup` in `Bindings.load`; your row replaced →
`routing.remap_factory` (swaps only exact factory rows, including an
identical crossfader row of yours; backup has it); lines every launch →
remap not finding its rows.

## L. The cheat sheet, the FX chips, window placement, instances, the dream's layer

**58. The cheat sheet is off at launch.**
Headless: `tests/test_ui_shell.py::{test_the_cheat_sheet_is_off_at_launch_and_the_desk_is_on,test_slash_still_toggles_the_cheat_sheet} tests/test_ui_desk.py::test_the_desk_does_not_jump_when_the_sheet_comes_up`.
Launch. *Pass:* no key legend; desk drawing bottom-left; `/` shows the
legend, drawing above it, in place on frame one (no
flicker); `/` again hides it,
drawing drops back; SYSTEM's "Cheat sheet" box follows (hover: `/`
toggles); APC40 DETAIL (B9) same, LED dark at launch. Quit with legend
up, launch: off. *Fail:* legend at launch → `Panel.__init__`; drawing
gone/floating → `ui_desk.room`; drawing jumps on first `/` →
`Panel._draw_cheatsheet`'s `_sheet_h`; `/` dead → `key:SLASH` row.

**59. An FX chip opens without switching.**
Headless: `tests/test_fx.py::{test_a_chip_click_selects_and_never_toggles,test_the_chips_led_toggles_and_never_selects,test_selection_is_by_name_and_survives_a_reorder,test_selection_survives_a_preset_load}`.
F5 (TRIP), FX page: chips three per row, dot (on) or ring (off) at left
(diamond if aimed at faces, check 91). Click an off effect's name.
*Pass:* strip opens (blend, target, order on blend row), white outline,
still off. Click ring: on (red chip, filled dot), strip unchanged; dot
hover: "on — click to
switch off". Kaleidoscope: drag order end to end; strip stays its own.
F6, F5: same effect open. Only the two longest names cut. *Fail:* name
click switches → `ui_fx._chip`; strip jumps → `FxState.selected` /
`sel_name`; dot hard to hit or stealing name clicks → say so; names cut
that matter → `ui_fx.CHIPS_PER_ROW`.

**60. An effect that is not running says why.**
Headless: `tests/test_fx.py::{test_an_off_effects_strip_says_so_and_turn_on_switches_it_on,test_a_bypassed_stack_says_so_on_the_strip,test_the_idle_strips_controls_stay_live,test_why_idle_names_faces_off,test_the_page_fits_with_the_tightest_strip_idle}`.
FX page, open an off effect. *Pass:* "off — nothing below shows
until it is on" + **turn on** chip; "on" box full strength; faders
dimmed but live, right-click menu full strength; **turn on** clears
line and dimming. Untick **Effects**: "the whole stack is bypassed" +
**effects on**. FX mix 0: "FX mix is at 0". Own mix 0: "its mix is
at 0", fader undimmed. Faces-aimed, Faces off: "aimed
at the faces, and Faces is off" + **faces on**. No scrolling. Dimming
legible from a step back? *Fail:* no/wrong line → `ui_fx.why_idle`;
dead faders → strip disabled not dimmed; dimmed menu → veil over popup
(`ui_fx._dim`); page scrolls → the line's row.

**61. The windows open where you left them.** (laptop, then projector)
Headless: `tests/test_placement.py tests/test_app_boundary.py::{test_the_windows_open_where_placement_says,test_the_exits_save_the_windowed_rects,test_a_config_screen_that_cannot_be_used_is_minus_one_and_one_note} tests/test_config.py::test_a_screen_that_is_not_a_number_is_minus_one_and_a_note`.
No `[[output.screens]]` (two outputs: check 101). (a) Laptop: move and
resize both windows, Esc, launch. *Pass:* same place and size;
`<home>/windows.json` has one `control` and one `render` entry.
(b) Projector in: render window onto it, Esc, launch: there, controls on
laptop. (c) `[output] fullscreen = true` (no `monitor`), launch:
fullscreen on projector; Esc: `windows.json` keeps windowed size.
(d) Unplug projector, launch: render on laptop, default spot; terminal
and SYSTEM: 'placement: the render window was last on "<projector>", which is
not connected — opening on "<laptop>"'. Restore `fullscreen`.
(e) Projector in; `[output] monitor = 0`, `control_monitor = 1`: windows
swap regardless of file. `monitor = 7`: SYSTEM and terminal: "config: [output] monitor = 7, but 2 screens are connected
(0–1) — using the last position"; last position used. `monitor = "left"`:
launches, with "config: [output] monitor = 'left'
is not a screen index — using the last position". Remove both keys.
(f) Delete `windows.json`, launch: render top-left, controls flush
right, primary screen, full size (overlap on small screens). (g) ⌘R with
a window moved: it stays. An index not connected **at launch** is
ignored for the run: plug projector in first. *Fail:* off-screen or
misplaced → `placement.place` / `usable`; wrong screen for index →
`placement.screens` (GLFW's order); fullscreen size saved →
`Output.windowed_rect`; no file after Esc → `app._save_windows`; no
launch with `"left"` → `placement.read` / `config.load`. Window out of
reach: delete `windows.json`.

**62. Instances to zero.**
Headless: `tests/test_render.py::{test_zero_instances_draws_only_the_ground,test_zero_instances_still_runs_the_look_back_and_the_effects} tests/test_plan12_presets.py::test_no_factory_hand_row_blanks_the_scene tests/test_params.py::test_instances_read_nothing_drawn_at_zero tests/test_undo.py::test_a_count_taken_to_zero_is_undone`.
F1 (TUMBLE), VIEW: Instances fully left. *Pass:* "0 · nothing drawn",
black; ⌘Z restores; 1 by hand: shape back. K3 fully left: same, not one
copy (too easy to land on?). F4 (WAKE), 0: trail fades over black, no cut.
F5 (TRIP), Plasma level up, 0: self-painting effects show. Hand camera,
F3 (FIELD): right hand at box bottom 9 copies, never none; top 69; ghost
hands draw at 0. Faces-aimed effect: FX faces row "(no copies to show
them)" at 0. Know: own route pushing Instances both ways (LFO, count 1)
blanks half the cycle. *Fail:* one copy at 0 →
`Renderer.draw_scene`'s clamp; traceback/frozen → same (red banner,
`stall.log`); FIELD blank with low hand → the row's rest.

**63. The dream's layer cannot be performed.**
Headless: `tests/test_lookback.py::{test_dream_params_declared,test_a_route_on_the_dream_layer_is_dormant} tests/test_presets.py::test_a_saved_route_onto_a_setting_is_dropped_with_a_note`.
LOOKBACK, DREAM: right-click the layer menu. *Pass:* "not
modulatable" where others offer "Route a lane here…"; ROUTING add-route
targets lack "Dream layer"; the menu, presets, learned knobs still change
it. Load your preset routing onto it (if any): route dropped, footer
"preset <NAME>: dropped <source> → dream.layer: not
modulatable", file untouched. *Fail:* route offered/landed → flag on
`dream.layer` (`params.py`), drop in `Presets.load_doc`.

## M. Learn, Unbind and the on-screen desk

A hand Learn lands as "positions" or "pushes +0.25" by axis and param
(checks 75, 76), taking the axis's other rows (check 77).

**64. One Unbind, with or without the desk.** (APC40 unplugged)
Headless: `tests/test_learn.py::{test_unbind_removes_the_presets_desk_rows_and_every_route,test_unbind_is_one_undo_step_and_none_when_nothing_goes} tests/test_ui_shell.py::{test_the_menu_lists_and_unbinds_with_no_midi_adapter,test_unbind_is_not_offered_on_a_session_only_param}`.
`[midi] enabled = true`. F1 (TUMBLE), VIEW, right-click Speed. *Pass:*
under id: "K2 (track knob 2)", right-hand height route ("R height
pushes …", tracker on); **Learn desk**; **Learn hand ▸** (left, right;
tracker on); one **Unbind ▸** ("desk — K2", "route — R
height", "both"); (tracker on) "Gate: none"; "Route a lane
here…". **both**: lines and Unbind gone, preset dot lit, footer "unbound view.speed
from K2 (track knob 2) and R height pushes …"; ⌘Z restores both
("undid unbind view.speed"). Brightness (knob + step buttons, no
route): "K1 (track knob 1)", "B16 (▲) · step +3", "B17
(▼) · step -3", plain Unbind. `[midi] enabled = false`, relaunch,
repeat: same. AUDIO, Input trim (S8's param): "S8 (track fader 8) · invariant",
dim, no Unbind. Restore `enabled = true`. *Fail:* no desk line, MIDI off
→ `Panel._ctx_lines` / `Panel._table` reading `self.midi`; Unbind only
refuses → `Panel._ctx_unbind`; ⌘Z restores half → `Learn.unbind` pushed
twice or late; line left or wrongly removed → `learn.bound`.

**65. A desk Learn listens only to the desk; the session's controls work through it.** (APC40, hand camera)
Headless: `tests/test_midi.py::test_an_invariant_control_works_through_a_desk_learn tests/test_hands.py::test_the_hands_never_complete_a_desk_learn tests/test_learn.py::{test_learn_refuses_the_global_layer_and_invariant_controls,test_a_knob_learn_writes_a_desk_row_into_the_loaded_preset,test_a_hand_learn_writes_a_route_into_the_loaded_preset} tests/test_ui_shell.py::test_the_footer_says_what_a_learn_waits_for_and_what_it_did`.
F1 (TUMBLE), VIEW, right-click 4D depth → **Learn desk**. *Pass:* red
frame; red footer on every page "learning
view.depth4 — turn a knob or press a button on th…" (hover: full, ends
"(click to cancel)"). Hands through box 5 s: armed, no route (TUMBLE's
route still moves depth). S3: band 3 drive moves, armed. TAP TEMPO
taps. SHIFT: LED on, header GLOBAL LAYER. K2: warning-colour footer, 4 s,
"K2 (track knob 2)
is on the global layer (the session's) — latch SHIFT off to learn into
the preset", then armed again; Response unmoved (armed under SHIFT,
everything but session controls is swallowed: trap?). SHIFT off, D5:
"learned view.depth4 ← D5 (device knob 5) (into the preset); D1 let
go" (D1 had it); D5 ring lit and following; frame, red line gone.
Re-arm, press a clip row 1 pad: preset loads, still armed in it; cancel
via footer. *Fail:* hands took it → `Learn.accepts`
(`HandsIO._learn`'s guard); fader/TAP ended it or SHIFT unlatched →
learning branch of `MidiIO._handle`; disarmed after K2 line →
`Learn.learn_control` took before refusing; no footer → `Panel._footer`
/ `"learn"` key of `Panel._message`; `bindings.json` written → learn
wrote the session file (belongs in preset).

**66. A hand Learn listens to one hand.** (hand camera, after 72)
Headless: `tests/test_hands.py::{test_a_hand_learn_listens_to_one_hand,test_a_rearm_starts_a_fresh_baseline} tests/test_learn.py::test_accepts_by_want`.
F1 (TUMBLE). Left hand still in box; right on trackpad: CAMERA,
right-click Zoom → **Learn hand ▸ left**. Wave right hand over box 5 s.
*Pass:* nothing learned; footer "learning camera.zoom — move the
left hand… (click to cancel)". Raise left slowly: "learned
camera.zoom ← hand left.y positions (into the preset; moved from
master.gain)" (fader, check 76; TUMBLE's left-height audio drive row
leaves, check 77); ROUTING lists "L height"; Zoom follows left only. A
tilt that travelled furthest is named instead ("hand left.roll pushes
+0.25"): any left axis passes. ⌘Z (drive row back); repeat **Learn
hand ▸ right**, hands swapped. Arm **left**, cancel via footer, re-arm
at once, hands still: nothing until left moves. *Fail:* right hand took
it → `moved` list in `HandsIO._learn`, or `Learn.accepts` (`hand:left.`
must be the prefix `HandsIO.address` writes); learned on arming →
baseline key (`_learn_key`: the param, the side and `Learn.armed_n`);
repeatedly the wrong right-hand axis → note it (picked by travel).

**67. A knob bumped during a hand Learn does its own job.** (APC40, hand camera)
Headless: `tests/test_midi.py::test_a_knob_bump_during_a_hand_learn_does_its_own_job`.
F5 (TRIP), hands out. VIEW, right-click Speed → **Learn hand ▸ right**.
Turn D1, cue knob; press a filled row 4 pad (factory party show: first
is TRACER) and an empty one. *Pass:* D1 moves FX mix; cue knob changes
shape; filled pad loads its preset (still armed, in it); empty says
"slot N: an empty slot"; footer still "learning view.speed — move the right hand…";
no new ROUTING desk line, K2 keeps Speed. Click on-screen desk control:
nothing. Click footer's red line: cancelled, frame gone. *Fail:* D1
drives Speed → `MidiIO._handle` skipped `Learn.accepts`; desk click
mapped → `ui_desk.click` / `Learn.learn_control`'s `accepts`; footer
line unclickable → `Panel._footer` (no test clicks it).

**68. The menu opens from a label and from every meter.**
Headless: `tests/test_ui_shell.py::{test_a_rows_label_opens_its_params_menu,test_every_meter_has_the_band_select_menu,test_the_menu_offers_learn_desk_and_learn_hand}`.
Hand tracking off. Right-click: CAMERA word ZOOM; VIEW word BRIGHTNESS
above its fader; ANALYZER fourth meter → **Learn desk**, cancel via
footer; BITMAP file name; HANDS Steadiness. *Pass:* label opens its
param's menu (same as slider's) at mouse, value unmoved; meter opens
`band.select`'s menu without selecting (left click selects); while
armed every meter framed red; file name: no Learn, dim "not modulatable";
tracker off: no "Learn hand"; HANDS settings: "Learn
desk", never "Learn hand". Known, not fails: page-drawn labels open
nothing (FX "blend", LOOKBACK's "from", "scene", "path"); LFO nudge
chips' menu lists items twice. *Fail:* label dead → `Panel._ctx_label`
(must build the same id as the widget's `_ctx`, `Panel._ctx_id`);
two-finger click not a right-click → say so, with page.

**69. The big desk, from a step back.** (laptop; APC40 for the last part)
Headless: `tests/test_ui_desk.py::{test_the_desk_takes_the_room_it_has,test_the_big_desk_labels_every_lit_control_and_never_scrolls,test_the_small_desk_draws_glyphs_only,test_a_controls_text}`.
F5 (TRIP). Panel open: desk fills column left of it (384 × 431 at
960 × 900 control size), glyphs only. H (or DEVICE ON/OFF, B6, or `big`
chip in desk header). *Pass:* panel gone, desk fills window; lit
controls named, glyph small in corner; dark ones glyph only; top pads
TUMBLE … NOITA, TRIP green; rows 4–5: filled slots amber half strength,
named (G4·1 reads TRACER on the factory party show), empty dark,
unlabelled; track knobs Brightness, Speed, Instances, Pattern mix,
Field amp, Field rate, Bitmap alpha, Zoom; device knobs FX mix, Plasma
level, Kaleidoscope segments, Kaleidoscope zoom, Zoom burst amount,
Zoom burst glow, Hue cycle paint, Hue cycle spread; clip-stop row "Save as
a new preset" once across; session names (faders, bank rows, band rows,
Tap tempo, Shift) grey, preset's white. No overlap or scrollbar. Two
paces back: which names read? (at 960 × 900 most 13 px, some 11 px, a
few cut with "…", e.g. ▲ ▼'s "Brightness +3" / "Brightness -3"). Hover:
"D3 ·
fx.kaleido.segments · Kaleidoscope segments · preset layer", Akai's
name, click action. APC40 SHIFT: header GLOBAL LAYER · SHIFT red; K1–K5
Steadiness, Response, Catch, Return, BPM; D1–D8 band strip; rows 2–3
scenes; preset controls dark. `panel` chip (or H) restores panel. Names
beside the open panel need a ~1200 px wide control window: widen, then
drag panel to right edge (placed once, at launch) or relaunch. `/`,
panel hidden: desk beside cheat sheet. *Fail:* names cut to nothing →
`ui_desk.wrap` / `ui_desk.label_px`; desk under panel →
`Panel._panel_x` (`Panel._draw`) or `ui_desk.room`; desk overlaps cheat
sheet → `Panel._sheet_w` / `room`; unreadable at two paces → control
window size, or `ui_desk.LABEL_PX`.

**70. Click a control, then a param.** (APC40)
Headless: `tests/test_ui_desk.py::{test_a_click_picks_and_a_second_click_lets_go,test_a_pick_lets_go_by_itself,test_a_click_completes_an_armed_desk_learn} tests/test_learn.py::{test_pick_then_param_maps_through_the_learn,test_a_pick_on_an_invariant_control_or_the_global_layer_maps_nothing} tests/test_ui_shell.py::{test_a_click_on_a_param_maps_the_picked_control,test_a_picked_control_dims_every_page_but_routing,test_the_footer_says_what_is_picked_and_a_click_lets_go} tests/test_ui_routing.py::test_goto_scrolls_the_rows_child_to_the_controls_line`.
F1 (TUMBLE), ROUTING open. (a) Click drawn D6. *Pass:* D6 red; ROUTING
rows (not page) scroll to "D6
unmapped — dark", framed red; ROUTING undimmed; footer counts down
"D6 picked (20 s): click a param on any other page". (b) VIEW: dimmed,
inert (no slider, no menu); rail and footer work; footer "D6 picked (… s): click a param to put it here (click to let go)".
Speed hover: red frame, "click: put D6 on Speed". Click: "learned view.speed ← D6 (device knob
6) (into the preset); K2 let go" (full on hover and ROUTING head); Speed
unmoved; page bright; D6 ring lit, moves Speed; K2 dark. ⌘Z: as before.
(c) Pick D6, open VIEW, idle: countdown, page returns, "D6
let go — no click for 20 s"; any click restarts it. (d) Pick D6 then
click it again / the ground between controls / the footer line: each
lets go at once. (e) H, click D6: panel back, VIEW dimmed. Click without
moving: nothing (maps only after 12 px from the pick); Speed, click:
mapped. ⌘Z. (f) S2: header "S2 (track fader 2) is invariant (the session's): BASS
Post-drive", VIEW undimmed, ROUTING to S2's line under "session". Latch
SHIFT, K1: "K1 (track knob 1) is on the global
layer (the session's) — latch SHIFT off to map into the preset:
Steadiness", undimmed. (g) SHIFT off: Brightness → **Learn desk**,
click drawn D7: "learned view.bright ← D7 (device
knob 7) (into the preset); K1 let go", K1 dark (▲ ▼ keep Brightness).
⌘Z. (h) APC40 cable out, map D8 both ways: same lines, dot lit. Does
dimming read "waiting for a click" (imgui's plain disabled look)? 20 s
enough? Should the click open ROUTING? *Fail:* slider moved → disabled
wrap in `Panel._draw`; no map/frame → `Panel._ctx_pick`
(`allow_when_disabled`, `ui_desk.armed`); (e)'s second click mapped →
`ui_desk.armed` / `PICK_MOVE`; page never returns → `ui_desk.tick`
(`PICK_S`); whole ROUTING page scrolls → `set_scroll_here_y` outside
`##routes` child (`ui_routing._mark_line`); map under SHIFT or onto a
fader → `learn.blocked`.

**71. The ROUTING filter.**
Headless: `tests/test_ui_routing.py::{test_the_filter_matches_glyph_param_and_source,test_a_filtered_page_draws_only_matching_lines_and_keeps_its_ids,test_the_filter_is_ui_state,test_typing_in_the_filter_is_imguis_keyboard_not_the_apps,test_a_line_in_use_is_not_filtered_away_under_the_hand,test_a_desk_click_clears_a_filter_that_has_the_keyboard}`.
F7 (MANDALA), ROUTING. Click "filter" (counts line, left of `+ route`),
type `kaleido`. *Pass:* only kaleidoscope lines: R depth →
`fx.kaleido.zoom`, R roll → `fx.kaleido.swirl`, desk D3, D4; MACROS
and SESSION "no row matches"; red "n of m rows"; × beside field; typed
keys do nothing else (B, F, R, numbers). `d3`: one desk line; `r roll`:
that route; F5 (TRIP) `lfo 1`: LFO 1's route (LFO 2's would show too,
source `lfo:1`: matters?). `kaleido` + F5: filter stays over TRIP.
Filtered `+ route`: new route shows only if matching; red count only
sign (trap?). Drag a filtered route's depth or retype a macro label out
of the match: line stays until release. ×: all back. Filter typed,
caret in field, click desk control: filter clears, rows scroll to its
line. Esc, backspace, ⌘Z in field: report each. *Fail:* × deletes
another row → `_row`'s `k` (its place in the unfiltered list); page
scrolls → `ui_routing.page`; filter back after desk click →
`ui_routing._find_field`'s `unfind`; typed key fires shortcut →
`app.Keys` (`typing`).

## N. The interaction box, a hand Learn's default, knob smoothing, `hands-orbit`

All with the hand camera; 74, 78 and 79 also need the APC40. 72 first.

**72. Calibrate, and the box it draws.**
Headless: `tests/test_hands.py::{test_the_sweep_sets_the_box_with_its_margin_and_a_symmetric_x,test_an_old_hands_json_reads_as_before_and_is_not_rewritten_at_load,test_the_first_rewrite_of_an_old_file_keeps_a_backup,test_two_still_hands_held_apart_are_not_a_sweep}`.
Launch, HANDS. First: `<home>/hands.json` without a box → its own
ranges, no inner rectangle, "box open" under each axis range. Only you
in view (box off during sweep; any hand counts). **feel &
calibration** → **calibrate 20 s** (or
`uv run python tools/hands_probe.py --calibrate 20`); sweep both hands
side to side, low to high, near to far, each tilt end to end; one hand
travels more than 12 cm each direction. *Pass:* "calibrated 12 axes ·
box W × H × D mm · the old file kept as hands.json.bak-v1" (last part
only if a file existed); inner rectangle and gauge bracket appear; dots
stay inside wherever you played; `hands.json` has
`"schema": "hyperspace.hands/2"` and `box`; every axis reaches both row
ends (box 40 mm beyond sweep). *Fail:* ", N not reached" → resweep
those; "box: x open (not swept)" → sweep wider there; "box left as it was (too few palm samples)"
→ tracker barely saw a hand; resting hand off-centre → 2nd / 98th
percentile in `_finish_calibration`; no rectangle →
`HandsIO._sweep_box` (`hands/core.py`); no `.bak-v1` →
`HandsIO.save_ranges` / `_keep`. Rectangle on the view edge = box drawn
clamped: legible?

**73. A hand outside the box reads absent; the edge does not flicker.**
Headless: `tests/test_hands.py::{test_a_hand_outside_the_box_reads_absent_everywhere,test_the_boxs_edge_has_hysteresis,test_a_hand_re_entering_the_box_is_caught_not_jumped,test_a_dip_in_confidence_does_not_evict_a_hand_in_the_edge_band}`.
`hands-play` (R height positions Brightness). Right hand mid-height,
slowly out the right face. *Pass:* 1–2 cm past the rectangle: hollow dim
ring, status `R◌` (hover "tracked, but outside the box"), axis rows dim,
brightness at base that frame. Wobble 1 cm at edge: no flicker. Back
in: row glides on, no jump. Repeat up past the bracket and out the near
face. `◌` vs `●`/`○` at arm's length? *Fail:* performs far outside →
`HandsIO.box` is `None` (check 72) or presence line in `poll`; flicker →
`BOX_EDGE` / `HandsIO._in_box`; jump on re-entry → Catch at 0, or lane
`NaN` during catch (`Follower.live`).

**74. A hand on the desk does not perform; the ghost; reset.** (APC40)
Headless: `tests/test_ghost.py::{test_the_camera_frames_the_interaction_box_when_one_is_set,test_a_hand_outside_the_box_fades_out} tests/test_hands.py::test_reset_ranges_opens_the_box`.
`hands-play`, APC40 in show position. Right hand turns a knob, left
away. *Pass:* only the knob moves brightness; right mark hollow (or
gone) throughout. Filled dot on the desk = desk inside box: move it or
redo 72 clear of it. Ghost hands on (HANDS): a hand leaving the box
fades at frame edge; frame shows whole box. **reset ranges**. *Pass:*
rectangle, bracket gone; "ranges back to the defaults, box open"; hands
present wherever tracked. Redo 72. *Fail:* ghost outside →
`HandsIO._skeletons`; frame not the box → `ghost.box_of`.

**75. A tilt learned onto speed and rotation is gentle.**
Headless: `tests/test_learn.py::test_a_centred_axis_learns_as_a_push_about_the_base_at_the_learn_depth tests/test_hands.py::{test_learn_passes_the_axiss_centredness_and_the_sessions_depth,test_learn_depth_changes_only_the_next_learn}`.
`hands-play`. VIEW, Speed → **Learn hand ▸ right**, roll right hand; L
height performs Speed, so prompt: **Replace**. *Pass:* "R roll pushes +0.25";
level: preset speed; full roll: ~half / ~double, not stop / flat out.
Same onto XY rate (VIEW, rotation) with right yaw: level keeps plane
turning as set, small turn nudges. Lower **Learn depth** (HANDS, feel &
calibration; 0.10 is ±6.7× on a rate), learn right pitch onto XZ: new
depth on that row, earlier two keep 0.25, line ends "moved from view.depth4"
(preset's R pitch row left, check 77). Same axis onto same param again
changes only the gate, never "pushes" / "positions" or depth. *Fail:*
"positions" on a tilt → `HandsIO._learn` not passing `centred`
(`hands/core.py`), or `Learn._row`'s table; param jumps on hand entry →
row has its own `rest`.

**76. Height is still the fader where that makes sense.**
Headless: `tests/test_learn.py::{test_a_one_sided_axis_on_a_one_sided_param_is_still_the_fader,test_a_one_sided_axis_on_a_zero_centred_range_pushes_up_from_the_base,test_a_discrete_target_keeps_the_position_row,test_a_whole_number_param_keeps_the_position_row,test_existing_rows_are_never_rewritten}`.
`hands-play` after 75. Left height onto unperformed Pattern mix.
*Pass:* "L height positions": low none, high full. Onto unperformed YZ
rate: "L height pushes +0.25" (or your Learn depth), Pattern mix row
gone (77); low: turns as set; raising speeds up; never backwards or
stopped. Tilt onto Faces: "positions", flips past middle. Onto
Instances: "positions". Load `hands-play`, `hands-pinch`, F1–F8,
ROUTING each: factory rows unchanged. *Fail:* factory row changed →
preset file regenerated or load converting rows (neither allowed).

**77. A Learn moves the axis.**
Headless: `tests/test_learn.py::{test_a_learned_axis_drives_one_param,test_a_learn_is_one_undo_step,test_the_same_axis_again_only_refreshes_the_gate_whatever_the_op}`.
F1 (TUMBLE): right roll turns XW. **Learn hand ▸ right** on
Brightness, roll. *Pass:* "learned view.bright
← hand right.roll pushes +0.25 (into the preset; moved from
rot.phase.XW)"; no XW row; roll moves only brightness. Learn removes
the preset's rows on that axis, switched-off too. ⌘Z once: XW back,
brightness row gone. Should learn add a row and keep the old? (one
condition in `Learn._place`).

**78. Knob smoothing: judge 80 ms.** (APC40)
Headless: `tests/test_app_boundary.py::test_the_app_starts_with_knob_smoothing_at_80_ms_and_a_show_keeps_its_own tests/test_midi.py::{test_smoothing_is_off_by_default_and_every_write_is_immediate,test_a_smoothed_knob_arrives_in_a_straight_line_and_rests_on_the_detent,test_the_ring_shows_where_the_knob_is_going}`.
F3 (FIELD). SYSTEM, "midi": **Knob smoothing** "80 ms", show dot clean.
K8 (Zoom) slowly. *Pass:* zoom glides, settles within a blink; ring
where fingers left it; fast spin no noticeable lag or overshoot; ring
never crawls back; next turn continues. "off": picture steps, show dot
lights (saved with show). Try 50, 200 ms; keep what feels right. Fader
(S1) and crossfader glide; uncaught fader still waits. Cue knob, pads:
one step per click. *Fail:* knob fights or ring lags →
`MidiIO._ring_norm` / `_rebase` (check 31 if ring misbehaves unsmoothed);
never settles → `MidiIO._glide`'s landing; "off" at launch on a show
that never saved it → `app._desk_table` after `library.attach`.

**79. A smoothed knob with everything else.** (APC40)
Headless: `tests/test_desk.py::{test_a_layer_switch_leaves_a_glide_to_finish,test_a_preset_load_stops_a_glide_on_a_performance_param_and_not_on_the_dim} tests/test_undo.py::{test_a_smoothed_knob_turn_is_one_step,test_undo_during_a_glide_holds} tests/test_midi.py::{test_a_glide_on_a_hand_owned_param_moves_the_return_value,test_a_load_from_a_pad_ends_a_glide_before_it_steps}`.
Knob smoothing 250 ms (max). Spin K1 + F5 together, then + F5's pad.
*Pass:* TRIP's look and brightness, not the knob's. Spin K1 + latch
SHIFT: brightness arrives; K1 ring shows global layer. Sweep K1, wait,
⌘Z: back in **one** press, footer naming the landed value. Sweep, ⌘Z
mid-glide: goes back, stays. `hands-play`, hand in box, K1: picture
still; hand out: brightness at knob's value. Crossfader to dim, F2
mid-slide: dim completes. Reset smoothing to 78's value. *Fail:* knob
beats a load → `redraw(load=True)`, or `poll`'s order (`_glide` after
`_follow_table`); two presses per sweep → `SLEW_MAX_S` vs
`undo.SETTLE_S`.

**80. Two hands on the camera: `hands-orbit`.**
Headless: `tests/test_presets.py::{test_hands_orbit_is_five_pushes_onto_the_camera,test_an_absent_or_level_hand_leaves_the_orbit_camera_alone,test_each_orbit_axis_moves_its_camera_param_as_its_row_says}`.
PRESETS: `hands-orbit` (listed, no slot). Five pushes: R x → yaw,
R pitch → pitch, L x → pan x, L z → pan y, L y → zoom. Right hand level
mid-box: still. Left/right: ~quarter-turn orbit each way; fingers up:
looks down on shape. Left hand: sideways and reach pan; raise: zoom to
~2.2× at top. Both out: camera where mouse left it. *Pass:* one move,
one effect; still hand calm; teachable in a sentence. Judge directions
(right turns scene as expected? reach pans up or down? fingers-up "look
down"?) and zoom depth (0.12; untried by hand); changes are numbers in
`preset.hands_orbit_routes`. R with hand tilted: snaps to reset view.
Known: reset writes base minus the hand's push, so on hand exit the
camera lands that far past reset: matters? Hide preset (check 86) if
unwanted.

## O. Twenty-four presets, the desk's bank, the list, the trash, git

On the copy. 81–84 from the first launch (Before you start, step 1);
APC40 for 82, 83, 85; 90 last.

**81. An eight-slot show opens untouched; the page holds twenty-four.**
Headless: `tests/test_library.py::{test_an_eight_slot_show_loads_and_is_not_rewritten,test_the_first_write_past_slot_eight_keeps_the_eight_slot_file} tests/test_ui_presets.py::{test_twenty_four_slots_fit_the_page_with_more_open,test_a_far_slot_reads_its_number_and_name_and_has_the_slot_menu}`.
Before launch: `ls -l $HYPERSPACE_HOME/projects/`. Launch (keep
stderr), open your show (PRESETS → show ▾), F1–F8, quit; `ls -l` again.
*Pass:* show files' size and time unchanged; your presets on F1–F8;
below, sixteen small buttons, four a row, "9" to "24", "—" if empty
(factory party show: 9 reads TRACER); no scrollbar, "more" open too.
Right-click 12 → **put preset here…** → one of yours. *Pass:* button
"12" plus name; footer "slot 12: <name>"; `projects/` holds
`<show>.hyp.json.bak-v2-bank8`, the old file (none for a factory show
opened as shipped: its first change makes your copy). Slot 20: no
second backup. Known: with "more" open, a warning line (empty far slot:
"slot 13: an empty slot") pushes the page down 11 px; say if a
nuisance. *Fail:* file changed by opening → `Project._take` / `write`;
scrollbar, no warning → `ui_presets.preset_bank` (`FAR_COLS`,
`FAR_GAP`); no backup → `Project.write`, `library._kept`.

**82. Rows 4 and 5 are presets, on both layers.** (APC40)
Headless: `tests/test_desk.py::{test_rows_four_and_five_load_slots_nine_to_twenty_four_on_both_layers,test_the_bank_pads_are_invariant} tests/test_midi.py::test_a_bank_pad_is_green_loaded_amber_filled_and_dark_empty tests/test_ui_desk.py::test_a_filled_pad_is_amber_and_an_empty_one_has_no_label`.
Preset on slot 12 (check 81). *Pass:* row 1: one green (loaded), amber
on other filled slots; row 4 pad 4 amber; empty dark (velocities 1
green, 5 amber, 0 dark). On-screen desk: same pads amber at half
strength, named; empty bank pad: glyph only. Press row 4 pad 4: green,
old one amber, picture changes, slot 12's PRESETS button lit. Empty far
pad: no load, "slot 16: an empty slot". Latch SHIFT: same pads and
lights; a filled far pad loads, SHIFT drops. Cue knob steps all 26
shapes; no pad shows which (VIEW does). Param → **Learn desk**, press a
far pad: preset loads, learn stays armed. *Fail:* amber unreadable from
green, or none → `apc40.filled_of` (say what you see; fallback
green-or-dark, `filled_of` returning `None`); pad changes shape → old
row in `bindings.json` (check 84); nothing under SHIFT → rows have a
layer.

**83. A preset saved before loads without a fuss; save-as goes past F8.** (APC40)
Headless: `tests/test_presets.py::{test_an_old_preset_loads_without_its_shape_pads_and_its_file_is_untouched,test_the_next_save_of_an_old_preset_writes_the_desk_without_the_pads} tests/test_midi.py::test_save_as_blinks_the_new_pad_on_row_four tests/test_library.py::test_save_as_lands_on_slot_nine_once_the_f_keys_are_full`.
`ls -l $HYPERSPACE_HOME/presets/`; load three presets from an earlier
build. *Pass:* no warning, no unsaved dot, no file time moved; old
shape-pad rows leave the live desk quietly, stay in the file until
saved, then the old file goes to `trash/presets/`, the new has none. A
learn on a row 4–5 pad warns: "dropped note:3:56 → …: that control is
invariant, the session's (plan 13 D6)"; off the live desk, in the file
until saved. Save-as: party show, F8 → clear slot, change the look,
hold the clip-stop row. *Pass:* at 0.6 s bar and F8's pad blink; "saved
… → F8". Change, hold again: bar and next empty far pad blink 1.5 s —
factory party show: row 4 pad 2, "saved … → slot 10"; your show, slot 9
free: row 4 pad 1, "→ slot 9" (plus `.bak-v2-bank8`, check 81).
*Fail:* warning every load → `routing.RETIRED_DESK_ROWS`; file time
moves on load → `Presets.load_doc`; blink on row 1 only →
`apc40.blink_of`; "the bank is full" after F8 → bank not 24 long
(`Project._take`).

**84. The session's file was brought along, with a backup.**
Headless: `tests/test_routing.py::{test_an_older_file_gets_the_bank_pads_with_a_backup,test_a_second_launch_writes_nothing_and_says_nothing,test_a_row_the_owner_put_on_a_bank_pad_is_left_alone,test_a_remap_whose_backup_fails_writes_nothing}`.
First launch's stderr. *Pass:* one "backup: bindings.json kept as
bindings.json.bak-v3 before the rewrite" (`.bak-v3-<stamp>` if taken);
sixteen "bindings: <path>: added note:0:56 → preset.select (the APC40
map of plan 19)" through `note:7:56` and `note:0:57` through `note:7:57`
("remapped note:<k>:56: view.shape → preset.select (…)" over old
shape-pad rows); then "bindings: updated <path> (N rows changed)" — 16,
more with check 57 in the same launch. SYSTEM: "bindings.json updated
(N rows changed), the old file kept as bindings.json.bak-v3 — each
change is on stderr". `grep -c preset.select
$HYPERSPACE_HOME/bindings.json` prints 24. Your hand-edited row on a
row 4–5 pad: kept, works, no bank row added. Relaunch: no bindings
lines on stderr or SYSTEM; `bindings.json` time unmoved. *Fail:*
changed, no backup → `Bindings.load` (no backup, no rewrite); SYSTEM
"bindings.json NOT rewritten (N rows changed): no backup could be made
— in memory only, the next launch tries again" → folder refused the
copy; lines every launch → `remap_factory` not finding its rows.

**85. The device knobs on each preset.** (APC40)
Headless: `tests/test_plan12_presets.py::test_no_factory_knob_is_dead tests/test_midi.py::test_a_knob_on_the_pattern_steps_through_every_pattern tests/test_presets.py::test_a_users_desk_is_untouched_by_the_recut`.
F1 (TUMBLE), D1–D4. *Pass:* D1 4D depth, D2 yaw, D3 pitch, D4 face
pattern, a step each (faces on); rings follow; D5–D8 dark, dead.
TUMBLE white (yours, pre-knobs): knobs as saved, dark — correct; use a
house mood (dim) instead. TRIP, WAKE, ACID: their eight (check 41).
`hands-fx`: D1 FX mix, D2–D6 Acid bend, twist, reach, breathe, speed,
D7 4D depth, D8 yaw. `hands-pinch`: D1 FX mix, D2–D3 hue cycle paint
and spread, D4–D7 depth, yaw, pitch, pattern, D8 dark. `lfo-breathe`:
D1 Breathe, D2 FX mix, D3 Plasma level, D4 LFO 1 depth, D5–D7 depth,
yaw, pitch, D8 dark. Name knobs you wanted but found dark or useless
(K7, Bitmap alpha, does nothing on a factory preset; scene presets lack
echo and effect knobs). *Fail:* lit knob, no effect → preset's row in
`preset.py`; one knob, two things → `knob_desk`; D4 skips →
`MidiIO._apply`'s `set_norm` on an enum.

**86. Hide presets from the list.**
Headless: `tests/test_library.py::{test_hiding_a_factory_preset_takes_it_off_the_list_and_nothing_else,test_a_deleted_preset_says_which_slots_still_name_it} tests/test_ui_presets.py::{test_the_list_has_a_cross_on_every_preset_and_rename_on_yours,test_a_slot_whose_preset_is_gone_says_so}`.
PRESETS → preset strip's name → list (scrolls past twelve). Every row
has ×; yours (white) **rename** too. × `legacy6`, unwanted `hands-*`, a
house mood. *Pass:* gone; footer "hidden legacy6 — show hidden in the
list brings it back" ("hidden … — F3 still loads it" if on a slot);
list ends "show hidden (n)"; `$HYPERSPACE_HOME/hidden.json` lists their
stems. **show hidden**: back, struck, dimmer, with **unhide**. Slots
and pads still load hidden presets. × **your** preset on a slot.
*Pass:* gone; footer in warning colour "<name> is in the trash — F6
still names it; restore it from the trash, or clear the slot"; slot
button warning colour, hover says where to look; pad stays amber,
press: "F6: no preset '<name>'" (restore: check 88). *Fail:* hidden
preset won't load from slot → `Library.list(hidden=)` leaking into
`path_of`; × on a factory preset in a module strip's list ("more") →
`_list_row`.

**87. Rename a preset.**
Headless: `tests/test_library.py::{test_rename_updates_every_show_and_keeps_each_old_file,test_rename_refuses_a_taken_name_and_a_factory_preset,test_renaming_the_loaded_preset_keeps_its_unsaved_edit} tests/test_presets.py::test_rename_and_trash_are_no_undo_step`.
Your preset, on a slot in two of your shows. List: **rename** → type →
Enter. *Pass:* footer "renamed TRIP 3 → SUNRISE (2 shows updated)"
(your names); list, slot, "starts on" (if that one) and the other show update
at once; `ls $HYPERSPACE_HOME/trash/presets
$HYPERSPACE_HOME/trash/projects`: old preset file and each show as was.
Taken name: refused ("library: …: that name is taken — pick another"),
no change. Factory: no rename (save a copy). Loaded preset with unsaved
change: dot stays lit. ⌘Z doesn't undo; rename back. *Fail:* slot says
"no preset" after → `Library.rename`'s `_repoint`.

**88. The trash.**
Headless: `uv run pytest -q tests/test_library.py -k trash`, `tests/test_library.py::{test_restore_never_overwrites,test_empty_trash_removes_only_the_trash,test_the_trash_lists_only_what_it_kept} tests/test_ui_presets.py::test_empty_asks_once_and_disarms`.
Load your preset (or **as…**: "CHECK 53"). Brightness, **save**; save
unchanged; × it. *Pass:* `ls $HYPERSPACE_HOME/trash/presets/`: two
`check-53.<date>-<time>.json` (pre-save look, deleted one), none for
the unchanged save; no "trash" strip under "more". List → **trash (n)
▸**. *Pass:* "trash · n files", newest first, folder, name, time ("Oct
4 01:12"), **restore**; scrolls past twelve. Restore check 86's preset:
"restored <name>", listed, slot loads, warning colour gone. Save over a
preset twice, restore the older: "restored as TRIP 4 — TRIP 3 is taken"
(next free name), newer untouched. **empty trash…** once, wait: "delete
n files for good? — click again" in warning colour, rests after 4 s,
nothing deleted; click then elsewhere: disarmed; twice: "trash: n files
deleted for good", "trash ▸" gone, `$HYPERSPACE_HOME/trash` empty (the
one delete with no copy). *Fail:* trash empty → `library.to_trash` in
`Library.save_as` / `Library.delete`; "trash" under "more" →
`Library.groups`; restore overwrote → `restore_trash` (backup has it);
one click empties → `_trash_popup`.

**89. The unsaved dot from a step back.**
Headless: `tests/test_ui_presets.py::{test_the_dot_is_a_twelve_pixel_disc_and_save_is_lit_while_dirty,test_save_reads_save_copy_on_a_factory_preset,test_the_preset_strip_has_no_reset_and_does_not_overlap} tests/test_ui_routing.py::test_the_head_has_the_same_dot_and_label`.
Factory preset, no copy (dim), on a slot; arm's length; move a fader.
*Pass:* visible without leaning in: save chip solid red, red disc by
name, small white disc on slot button; chip **save copy**, no reset;
press: "save", dot gone, listed once, white. ROUTING head: same disc
and label. Your presets read "save". Known: under "more" a module
strip's save chip overlaps its name. *Fail:* unreadable → `ui.DOT_R`,
or say what would read.

**90. The home in git.** Retired by plan 25 (2026-10-14): the home-as-git
switch was removed; presets are shared through a cloud-synced
folder instead — checks 139–143.

## P. Effects on the faces, reordering, the LOOKBACK page, instance layouts

**91. An effect aimed at the faces.**
Headless: `tests/test_render.py::{test_a_face_effect_changes_the_faces_and_nothing_else,test_per_face_turns_with_the_shape_and_screen_stays_still,test_screen_mapping_is_a_cover_fit_window_onto_the_picture} tests/test_fx.py::{test_the_status_reads_per_target,test_the_strips_onto_chips_move_an_effect_between_chains,test_a_chip_aimed_at_the_faces_is_marked,test_why_idle_names_faces_off}`.
F2 (FACES); BITMAP: load a picture. FX: status under "Effects" one
line. Kaleidoscope on; on its strip's title line, **ONTO** **frame** →
**faces**. *Pass:* wireframe unfolded, face pictures folded;
status two rows, `frame  …` and `faces
Kaleidoscope`, the second with chips **per face** (lit), **screen**;
chip shows filled diamond (outlined off), hover "on the faces".
**screen**: faces are windows onto one upright folded picture, shape
turning across it; **per face**: turns with the shape. Unload bitmap,
pattern FLAT, Plasma on faces: faces glow, gaps black. VIEW Faces off:
row `faces (Faces is off)` in warning colour, strip "aimed at the
faces, and Faces is off", **faces on** chip. Instances 0: `faces  (no
copies to show them)`. Running on the faces, the strip reads "faint on
the translucent faces — Brightness lifts them". ⌘Z after **faces**, after map chip: one
step each. From a step back: diamond distinct from dot? Subtle per-face
effects (Double vision, Deconverge, Trip colour, Wobble) visible?
Strong ones (Hue cycle, Kaleidoscope) should be. All faces same
picture (face 0's) is expected; say if it matters. *Fail:* faces
unchanged → faces row (`faces: …` error is `Renderer.face_error`),
`Renderer._face_picture`; whole frame folds → frame chain
(`FxState.chain`, `fx._target`); flipped/mirrored → `FACE_PX`'s
`1.0 − q.y`, screen branch of `FACE_FS_TAIL`; dead chips →
`ui_fx.page` / `_faces_row`.

**92. Nothing aimed at the faces changes nothing.**
Headless: `tests/test_render.py::{test_nothing_aimed_at_the_faces_is_the_old_frame_exactly,test_the_face_target_costs_nothing_while_unused,test_the_old_frame_holds_under_frame_effects_the_hands_and_the_dim}`.
F1–F8. *Pass:* each as known; FX status one line, no `frame` prefix;
frame rate as before. F5 (TRIP): its four (Plasma, Kaleidoscope, Zoom
burst, Hue cycle) to faces: no visible frame-rate drop. F5 again: back
on frame (load sets every target; none given = all `frame`, per face).
*Fail:* preset differs → face fragment's `u_pic_on == 0` branch; rate
drop → `render.FACE_PIC`; name the machine.

**93. The echoes and the dream carry the faces' effects.**
Headless: `tests/test_render.py::{test_the_echoes_carry_the_faces_effects,test_a_frame_effect_runs_over_a_face_effect}`.
F4 (WAKE), dream on. Hue cycle on, at faces. *Pass:* trail has the
faces' cycling colours, dream grows from them; `frame` effects never in
trail. *Fail:* old colours → face pass after capture
(`Renderer._draw_frame`: face picture precedes scene pass).

**94. Drag an effect to reorder.** (trackpad, then a mouse)
Headless: `tests/test_fx.py::{test_a_drop_reorders_selects_and_is_one_undo_step,test_reordered_always_sorts_to_the_sequence_asked_for,test_a_click_without_a_drag_still_only_opens,test_a_drop_moves_the_effect_the_drag_began_on,test_the_order_slider_still_reorders}`.
F5 (TRIP), FX. Drag Hue cycle **by its name** onto Plasma. *Pass:*
name floats with mouse, white bar at target chip's left edge; on drop
Hue cycle first, status starts with it, picture changes (colour before
fold), strip opens. ⌘Z: one press, "undid reorder effects". Drop on the
**right half of the last chip's name**: bar at right edge, effect last.
Click, or press-slip-release on one name: opens only; dot only
switches; order slider still works; drag never changes target or
switch. Known: 2 px dot–name gap takes no drop; floating name may clip
at window edge. *Fail:* click drags, or no drag → use order slider, say
so; wrong order → `fx.reordered`; wrong effect → `ui_fx._dragged` /
`panel._fx_drag`; two ⌘Z → push in `ui_fx._drop`.

**95. The LOOKBACK page reads.**
Headless: `tests/test_ui_shell.py::test_the_look_back_page_fits_with_thumbnails tests/test_lookback.py::{test_the_page_has_three_sections_and_every_dream_param_once,test_the_layer_is_one_menu_of_every_layer,test_saved_layers_keep_their_meaning,test_spacing_is_called_time_apart,test_the_routing_page_lists_the_new_labels}`.
F4 (WAKE), LOOKBACK, dream on. *Pass:* below the switch: **ECHOES**
(brightness, fade time, count, time apart, thumbnails; "24 × 50 MS ·
THE TRAIL REACHES 1.20 S"; time apart `50 ms`, fade time `0.60 s`),
**DREAM** (status ≤ three lines, rest on hover; the layer menu, reading
"conv3_3 · small loops, the classic"; brightness, speed, strength,
passes, linger, jitter, scales, hue, saturation, tint, tint from, tint
hue, tint sat, tint swatch), **BOTH** (darken, contrast, shape hides,
detail). No scroll with thumbnails; labels clear without hover (name
any not). ROUTING: "Echo time apart", "Dream brightness", "Shape hides
wake". Right-click the layer menu: "not modulatable". Open it: VGG16's
13 layers, then GoogLeNet's 12, each name with a few words, readable at
a pace; hover one for more. Pick a layer from each net and several deep
ones; the status names it at once within a net (the first of a net
takes a moment). Do the words match what you see — which would you
rename? Are 25 too many to choose from? Do the "slower" ones drop the
frame rate or only the dream's? *Fail:* scrolls → `ui_lookback.SECTIONS`
/ `STATUS_LINES`; a layer won't load → its `dream.TRUNKS` row; words →
`lookback.LAYER_INFO`; label cut → `ui_lookback.LABEL_W`.

**96. Dream speed.** (laptop; then on the projector)
Headless: `tests/test_lookback.py::{test_dream_speed_is_dream_k,test_the_speed_readout_is_the_half_life_in_frames}`.
F4 (WAKE), DREAM **speed** (opens "8.3 frames"); sweep it as the shape
moves. *Pass:* right is faster: fast end keeps up, lets go at once,
shallower; slow end trails, deeper. Readout in dream frames: "≈23
frames" slow, "≈14 frames" build default, one decimal under ten ("1.9
frames" fast); past ~17 frames status says "step clamped". Is this the
"speed" you meant; is one knob enough (faster = shallower, by design)?
Projector: compare at the same number; it counts worker frames, not
seconds — report a different feel.

**97. Instance layouts.**
Headless: `tests/test_render.py::{test_grid_layout_is_the_frame_it_was,test_hex_neighbours_are_one_cell_apart,test_ring_is_one_circle_with_neighbours_one_cell_apart,test_zero_and_one_are_the_same_in_every_layout} tests/test_ui_shell.py::{test_the_view_page_fits_with_a_field_in_motion,test_the_field_row_and_the_rate_cells_keep_their_menus}`.
F3 (FIELD, GRID, ORBIT), VIEW. *Pass:* no scroll. Instances > 1: one
row: **layout** (GRID, HEX, RING), **motion** (STILL, ORBIT, WAVE,
RIPPLE), unless STILL **amp**, **rate**; six rotation rates in three
rows of two, by plane ("XY"). House F1 (lane per rate): rate cell
`base → effective` in full. HEX 7: one centre, six round; 19: two
rings; slow raise: existing copies stay. RING 12: one circle; ORBIT
waves round, RIPPLE breathes. Count to 1, 0: one centred copy, then
none, every layout (row hides at 1). ⌘Z restores layout. Right-click
layout list, rate cell: own menus. ROUTING, Learn: "Field motion",
"Field amp", "Field rate". HEX + ORBIT, amp ~0.35: neighbours overlap
(ORBIT phase uneven on a honeycomb) — look or fault? *Fail:* GRID
changed → `inst_positions`' GRID branch; HEX copies jump →
`_hex_spiral`; scrolls → `Panel._page_view`; HEX + ORBIT unusable →
motion block of `draw_scene`.

**98. Effects on the faces, on the projector and the glass.**
Headless: `tests/test_render.py::{test_screen_mapping_is_a_cover_fit_window_onto_the_picture,test_the_face_target_keeps_an_opaque_grounds_alpha}`.
Check 91's looks, projector then glass (Kaleidoscope on faces with a
bitmap, per face and screen; Plasma on faces over FLAT). *Pass:* screen
mapping sharp at room size, unstretched (wide output crops top and
bottom); per face, near faces unblocky; no desktop or grey through the
faces on glass. From the audience: do face effects read at face
brightness, esp. per face, or need pattern mix/brightness up (which
preset)? *Fail:* soft/blocky → `render.FACE_PIC`; squashed → cover fit
in `FACE_FS_TAIL`; see-through on glass → face fragment's alpha.

## Q. Two outputs, hands through effects, the ghost hands

99, 100 on the laptop before any `[[output.screens]]` edit; 101–109 on
glass and projector; camera 102–110; APC40 104, 110; 111, 112 last.

**99. One output is as it was.**
Headless: `tests/test_outputs.py::test_one_default_output_is_todays_frame_byte_for_byte tests/test_app_boundary.py::test_one_output_draws_the_view_renderer_draw_would tests/test_ui_shell.py::test_the_output_page_with_one_output_has_no_dim_of_its_own tests/test_overlay.py::test_one_output_has_no_dim_of_its_own`.
No `[[output.screens]]`. Camera, or recorded hands:
`uv run python tools/hands_tape.py synth /tmp/hands.json` and `[hands]
enabled = true, tape = "/tmp/hands.json"` (remove `tape` after).
Launch. *Pass:* two windows, render where it was; OUTPUT under Master
dim: one block "1", **scene**, **hands** ticked, **through effects**
not, no own dim row (master is its dim), "shows: scene" ("shows: scene
+ hands over the effects" with ghost on, hand drawn); Screen,
Fullscreen, overlay rows below. HANDS Ghost hands on, F5 (TRIP): clean
hands over warped shape. *Fail:* picture changed →
`Renderer.draw_outputs`' direct rule; dim row on one output →
`overlay.register_switches` (only config `dim` under 1 adds one).

**100. The HANDS page explains a bad setting.**
Headless: `tests/test_hands_tape.py::test_a_bad_tape_path_is_a_note_the_pages_show tests/test_ui_shell.py::{test_the_hands_page_says_why_the_ghost_or_the_tracker_is_off,test_the_hands_page_says_the_ghost_axes_are_unmeasured,test_the_hands_page_fits_with_every_ghost_line} tests/test_render.py::test_a_raising_hands_pass_still_dims tests/test_ghost.py::{test_a_failed_label_build_writes_no_param,test_a_failed_target_build_is_all_or_nothing,test_one_reload_round_rebuilds_the_ghost_once}`.
(a) `[hands] tape = "/tmp/no-such-tape.json"`, launch. *Pass:* SYSTEM
note starting `hands: ` ("hands: [Errno 2] No such file or directory:
…"); HANDS shows it, warning colour, in place of "tracker off". Remove
key. (b) Camera, `[hands] mode = "screentop"`, launch, Ghost hands on.
*Pass:* the ghost's chip reads **! more ▸** in warning colour; open it:
"ghost axes for screentop are unmeasured: left/right and up may be
wrong — Mirror flips left for right" (desktop: **more ▸**, nothing); no
scroll with all ghost controls, nothing drawn over the **Ghost hands**
label. Restore `mode`. Rest of headless line (raising hands pass, failed
label build, one reload round): tests only. *Fail:* "tracker off", no
reason → the registry's `hands:` note (`DeviceRegistry._open`); no unmeasured line →
`hands.panel.ghost_notes`; scrolls or overlaps → `hands.panel._ghost`.

**101. Two outputs open where the config says.**
Headless: `tests/test_config.py::{test_no_screens_list_is_one_output_as_today,test_a_screens_list_wins_over_the_scalar_keys_with_a_note,test_a_config_dim_cannot_launch_an_output_black} tests/test_app_boundary.py::{test_one_window_per_listed_output,test_the_exits_save_one_rect_per_output,test_the_switches_are_registered_from_the_configs_launch_values} tests/test_overlay.py::test_the_output_switches_are_rig_settings`.
Glass, projector plugged in. Read numbers from OUTPUT's **Screen** list
(main first; they shift on plug-in). `config.toml` `[output]`:
`control_monitor` = laptop; drop `monitor`, `fullscreen` (else ignored,
one note); add, your numbers:

```toml
[[output.screens]]         # output 1: the glass — sets the frame size, paces the loop
name = "glass"
monitor = 1
fullscreen = true

[[output.screens]]         # output 2: the projector
name = "projector"
monitor = 2
fullscreen = true
dim = 0.6                  # optional: its own dim at launch (never under 0.1)
```

Launch. *Pass:* both fullscreen, same picture, controls on laptop, no
config note on SYSTEM. OUTPUT: "1  glass", "2  projector", three ticks
and **dim** row each (100%, 60%), then "paced by output 1 · frame W×H ·
below: output 1's window". Relaunch: same; `<home>/windows.json` two
`render` entries, list order. Larger screen listed first: frame is
output 1's size. *Fail:* one window → `config.screens` /
`app._windows` (later entry's index absent: check 111); swapped → list
order; no second rect → `app._save_windows`.

**102. The eight states, on each output.**
Headless: `tests/test_outputs.py::{test_route,test_each_of_the_eight_states_shows_its_picture,test_outputs_that_differ_run_one_chain_per_distinct_input,test_the_presenter_shows_what_a_target_view_shows}`.
Ghost hands on, hand in box, F5 (TRIP). OUTPUT: walk output 1 through
the eight, then output 2:

| scene | hands | through effects | the output shows |
|---|---|---|---|
| on | on | off | the scene with its effects, the hands clean on top (the default) |
| on | on | on | the scene and the hands, both bent by the effects |
| on | off | off | the scene with its effects |
| on | off | on | the same as the row above |
| off | on | off | the hands alone on black |
| off | on | on | the hands alone through the effects; an effect that makes its own light lights the ground |
| off | off | off | black |
| off | off | on | black |

*Pass:* that output only changes; "shows:" matches. All effects off:
through changes nothing; Ghost hands off: hands leave every output.
*Fail:* `outputs.route`; other output changes → pipelines not keyed
per output (`Renderer._draw_frame`); echoes with hands alone through
effects → `Renderer._pipeline`.

**103. Hands over or through the effects; the guide never bent.**
Headless: `tests/test_outputs.py::{test_through_bends_the_hands_with_the_shape,test_through_with_no_effect_on_is_hands_over,test_the_guide_is_never_distorted,test_the_history_holds_what_it_is_wired_to_and_the_default_graph_wires_it_as_today,test_two_pipelines_show_the_same_echoes} tests/test_ghost.py::test_the_readout_layer_is_the_guide_apart_from_the_hands`.
Glass through on, projector off. F5 (TRIP), then F4 (WAKE). *Pass:*
glass hands bend and recolour with the shape, projector's clean; no
hand echoes or dream feed on either; same echoes on both. All effects
off: alike, glass block "through: no effect on". HANDS: Guide
BESIDE, then ON HAND, Tethers (**more ▸**) on: gauges, labels sharp, same on
both, never warped. *Fail:* hand echoes → `Renderer._pipeline` (hands
enter after look-back composite, before first effect); warped labels →
`Ghost.layer(…, readout=True)` / `Ghost.composite_readout`; echoes
differ → capture's place (`Renderer._draw_frame`).

**104. The dims.**
Headless: `tests/test_outputs.py::{test_each_output_dims_by_master_times_its_own,test_an_opaque_grounds_alpha_is_untouched_in_every_state} tests/test_undo.py::test_the_output_switches_are_left_alone_by_undo_presets_and_shows`.
Crossfader mid: both dim. Output 2 dim half: projector dims further,
"shows:" ends in the product ("· 30%" at master 60%). Crossfader left:
both black, footer "dim black". Toggle a switch, ⌘Z: not undone. F1,
show load: switches, dims stay. Relaunch: master full, projector dim
60% (config), switches per config. Glass ground opaque black at every
dim. White page behind each output: check 43 on both. *Fail:* wrong
product → `Renderer._compose` / `Presenter.present`; switch moved by ⌘Z
or preset → `persist` in `overlay.register_switches`; desktop through
glass → `Renderer.dim_pass`.

**105. Black is never a mystery.**
Headless: `tests/test_ui_shell.py::{test_the_output_page_says_what_each_output_shows,test_the_footer_names_a_black_output,test_the_output_page_fits_with_four_outputs_and_overlays_rows}`.
OUTPUT, one output at a time: scene and hands off; scene off, hands on,
no hand; scene on, own dim 0; crossfader left. *Pass:* "shows:" in
warning colour, in turn: "black — nothing switched on", "black — the
scene is off and no hand shows", "black — dim 0", "black — master
dim"; first three add footer "·  output 2 black" ("·  outputs 1, 2
black" for both), master only "dim black". Ghost hands off, output's
hands ticked: "hands: ghost hands are off (HANDS page)" under ticks
("hands: no tracker" without tracker); through, no effect: "through: no
effect on". *Fail:* `ui.output_shows`, `Panel._output_blocks`,
`Panel.black_outputs`.

**106. An output of another shape.**
Headless: `tests/test_outputs.py::{test_fit,test_an_output_of_another_aspect_is_letterboxed_and_the_hands_stay_registered}`.
Screens differ in shape: watch output 2; else its `fullscreen = false`,
launch, drag window tall and narrow. *Pass:* whole frame centred, black
bars, circles round, no crop, hands on the same part of the shape as on
glass. Restore `fullscreen`. *Fail:* `outputs.fit`; hands misplaced →
`Renderer._compose`, `Presenter.present`.

**107. The frame rate and tearing with two screens.**
Headless: `tests/test_app_boundary.py::{test_only_the_first_output_waits_for_the_screen,test_the_rendering_context_is_flushed_before_a_presenter}`.
Only output 1's swap waits; pacing of two real screens unknown
(one-screen scripted runs: unpaced, 270–380 fps). Both fullscreen, F5,
hand in box, output 1 through on, output 2 off. Note both refresh rates
(System Settings → Displays). *Pass:* footer FPS at glass refresh; no
projector tearing in fast rotation; no new `stall.log` entry after five
minutes. Note what you see either way. *Fail:* half rate → second
waiting swap (`glfw.swap_interval`: 1 for output 1 in `app.main`, 0 in
`app._open_presenters`); projector tears → it may need to wait too, or
pace by it; far above refresh → swap not waiting on this machine.

**108. The ghost hands follow the real ones.**
Headless: `tests/test_ghost.py tests/test_ghost.py::{test_desktop_keeps_left_on_the_left_and_mirror_flips_it,test_a_hand_that_leaves_fades_out_where_it_was_and_comes_back_up,test_the_camera_frames_the_interaction_box_when_one_is_set} tests/test_hands_tape.py tests/test_hands_tape.py::test_every_recorded_tape_replays_through_the_ghost tests/test_hands_leap.py`
(the tape test skips until a tape is committed).
Glass. HANDS: **Ghost hands** on, Opacity ~60 %, Style HANDS (others:
check 109). Performer's seat, both hands in. *Pass:* (a) **not
swapped** — raise left only: near-white hand, picture left, moves;
light red is right. (b) **fingers** — spread, fist, thumb to each
finger, point: all follow, thumb correct side, no backward bends. (c)
**directions** — performer's view: right is right, up is up, toward
screen goes away, palm down shows back; then **Mirror** (in **more ▸**) on, view
as audience: save the rig's choice in the show. (d) **no lag** —
shake: ghost stays on, no smoothing trail; still: no shimmer. (e) **the
box fills the frame** — each calibrated corner: hand in frame, near
edge. (f) **leaving** — pull out: fades in place in ~⅓ s, fades back on
return; no freeze or jump. (g) **off is off** — Ghost hands off:
picture as before. (h) **the guide** — Guide BESIDE: right hand
straight right, up, toward screen: one ball moves each (red, green,
blue), others still; fingers up, out, roll thumb-up: red arc's dot
rises, green's goes out, blue's turns to palm facing, none leave their
arc; pinch each finger: bead lights; fist: grab ring shrinks round a
full ball. Route some left axes, none right: left routed axes keep
colour, right grey, smaller, moving. ON HAND: gauge rides palm.
**Tethers** (in **more ▸**): each routed left axis, a line in its colour to a
left-edge label naming its param; lines still while balls move; off:
gauges stay. Rig on `screentop`: redo (c) there (unmeasured, check
100). Effects on hands: check 103. Then record the reference tape:
`uv run python tools/hands_tape.py record
tests/fixtures/hands/rig.json --seconds 6` — both hands, open, fist,
pinches, in and out of box — commit it. *Fail:* swapped/mirrored →
`ghost.MODES` / `ghost.mirror`; wrong digit, backward bend →
`hands.core.skeleton` (bone order); lag → skeleton smoothed (must be
raw).

**109. The five styles, at distance.**
Headless: `tests/test_ghost.py::{test_every_style_draws_from_the_same_poses,test_a_style_never_draws_the_guide,test_a_palm_only_hand_draws_in_every_style,test_hands_is_the_old_geometry_byte_for_byte,test_the_guide_on_the_hand_reads_the_same_in_every_style_but_hands} tests/test_outputs.py::test_every_style_behaves_as_the_hands_in_every_state tests/test_ui_shell.py::test_the_ghost_style_is_on_the_hands_page_while_the_ghost_is_on`.
HANDS, Ghost hands on: **Style** leads ghost line 2. From the
audience, both hands in: **HANDS** (capsules), **JOINTS** (bead per
joint, biggest at tips, one at palm), **PALMS** (palm orb swelling as
hand opens, ring in palm plane, spoke where fingers point), **CAGE**
(wire octahedron turning with palm, breathing with grip, small solid
one inside), **MARIONETTE** (fingertip beads on strings from a bar
above). *Pass:* no lag; orb and cage track grip (tuned on synthetic
hands: say if a real fist or open hand reads wrong); leaving hand fades
in all; Guide ON HAND drawn on top in the four new styles, partly
behind palm in HANDS; frame rate unchanged; style kept on relaunch. Say
which to keep. *Fail:* `ghost.PARTS`, `ghost.openness`; style hides
guide → `Ghost.layer`'s guide-over pass.

**110. A hand cannot learn a ghost setting.** (camera, APC40)
Headless: `tests/test_learn.py::test_a_hand_learn_onto_a_setting_is_refused_in_words tests/test_presets.py::test_a_saved_route_onto_a_setting_is_dropped_with_a_note tests/test_ghost.py::test_the_params_are_session_off_by_default_and_learnable`.
HANDS: right-click Guide, Style, and in **more ▸** Mirror, Tethers. *Pass:*
**Learn desk**, no **Learn hand ▸**; Ghost hands, Opacity keep Learn
hand. Learn desk Mirror, press a pad: pad flips mirror. OUTPUT
ticks: Learn desk, no Learn hand. A hand Learn armed another way on
these four: no row, footer "Ghost mirror can't follow a hand (not
modulatable) — not learned; Learn desk puts it on a button". Your
preset routing to `ghost.mirror`, `.guide` or `.tethers` loads with
"dropped <source> → ghost.mirror: not modulatable", file not
rewritten. *Fail:* Learn hand item present →
`Panel._ctx_learn`'s `p.modulatable` test; row made →
`Learn.learn_source`; load fails → `Presets.load_doc`.

**111. A screen not plugged in at launch.**
Headless: `tests/test_app_boundary.py::test_a_later_output_whose_screen_is_absent_is_not_opened tests/test_placement.py::test_what_names_a_later_output_in_the_notes`.
Check 101's config; quit, unplug projector, launch. *Pass:* glass only;
OUTPUT: output 1's block, disabled line "2  projector — screen 2 is
not connected"; SYSTEM and terminal: "config: output 2 (projector):
monitor = 2, but 2 screens are connected (0–1) — not opened" (your
counts). Plug in while running: nothing; ⌘R (or relaunch) opens it.
*Fail:* third window on laptop → `app._later_rect`; output 2's params
present → `overlay.register_switches`.

**112. Unplug the projector mid-run.** (last)
Headless: `tests/test_app_boundary.py::test_a_raising_presenter_does_not_stop_the_frame tests/test_watchdog.py::{test_one_dark_output_of_two_is_a_warning_not_a_stall,test_no_output_presenting_is_the_stall}`.
Both running: pull projector cable, wait 10 s, replug. Each later
output presents in its own `try`: a raise is that output's error on
OUTPUT plus "output 2 (projector): its picture failed — …"; 2 s without
a present while glass presents: "output 2 (projector): no picture for 2 s —
…"; loop continues. *Pass:* glass never stops or freezes; loop
lives; controls name output 2 if it failed; replugged projector shows
the frame (else say what — maybe ⌘R); note what macOS did to the
window. *Fail:* loop dies → `app._draw_render`'s per-output `try`;
glass freezes → presenter left context or framebuffer bound
(`Presenter.present`, `finally` in `app._draw_render`); projector
window over laptop controls → note it.

## R. Plan 22: the shapes in four dimensions, the face patterns

**Stream A (113–119), the shapes.** All on the laptop; 117's desk part
on the APC40; 113 again on the glass
when it is up. A shape is picked in VIEW's **Shape** list (or ← / →).
To watch one W plane alone: VIEW plane keys, all off but that one; F1
(TUMBLE)'s rate bases keep a plane turning with no music. 119 needs no
app.

**113. Each lifted shape tumbles without reading as a sheet.**
Headless: `tests/test_shapes4d.py::{test_every_shape_past_the_polytopes_is_lifted_or_masked,test_a_lifted_or_masked_shape_keeps_its_volume_through_each_w_plane,test_a_lifted_or_masked_shape_never_turns_much_of_itself_edge_on,test_every_4d_shape_clears_the_volume_floor} tests/test_shapes3d.py::test_shape3d_valid`.
F1 (TUMBLE). For each of Star, Rose, Torus, Trefoil knot, Starfruit,
Möbius strip, Klein bottle: XW alone a full turn, then YW, then ZW;
then all six keys on, with music. Faces on, then off. Compare the
Clifford torus. *Pass:* no angle draws a flat sheet, a line or a
ribbon; each bends and swaps sides through W as the Clifford torus
does; VIEW alias "4D lift · …" (Klein bottle "4D · one-sided bottle, no
self-crossing"). Say which read best and worst. On the glass: the same
from the audience. *Fail:* flat at 90° / 270° → `Shape.w` not "lift" or
the lift dropped (`geometry._build_*`); reads as a folded sheet though
not flat → the lift is even under a mirror (the rules above
`geometry._build_heart`); a seam or pole opens → the lift disagrees
across the weld (`_mesh3` merge).

**114. The masked Heart answers SUB, BASS and MIDB, as bright as a
polytope.**
Headless: `tests/test_shapes4d.py::{test_a_masked_shape_turns_in_3d_where_its_w_planes_would_have_turned_it,test_the_renderer_draws_a_masked_shape_through_view_angles,test_a_masked_shape_cues_depth_toward_the_camera_however_the_camera_turns,test_masking_a_flat_surface_lifts_it_over_the_floor,test_no_shape_but_a_masked_one_has_its_angles_touched}`.
Shape Heart (VIEW: "3D · classic heart curve, extruded"). XW alone,
then YW, then ZW; then F1's routes with music that has sub and bass.
Switch to the Tesseract and back. *Pass:* XW spins the heart about the
vertical (it turns side-on), YW tumbles it about the horizontal, ZW
rolls it in the screen plane; never flat; with music it visibly
answers the bass bands; lines as bright and as deep-looking (near
edges brighter and thicker) as the Tesseract's. Known: the XW / YW / ZW
keys and `rot.phase.*` keep counting the W planes. Say whether BASS's
spin reads as BASS. *Fail:* flat at a quarter turn → `Shape.w` not
"mask" or `Renderer.draw_scene` not drawing through `view_angles`;
faint, flat lines → the depth cue reading w (`draw_scene`'s `pd`);
another shape moves differently after the Heart → the fold wrote
`ViewState.ang` (it must not).

**115. The Star, Starfruit, Rose and Möbius strip by eye.**
Headless: `tests/test_shapes4d.py::test_a_lifted_cap_is_triangulated_over_its_own_outline tests/test_shapes3d.py::{test_shape3d_faces,test_mobius_seam_merges,test_rose_pinches_at_origin}`.
FACES on with a pattern. **Star**: XW to 90° and 270° (it becomes a
box, a lantern of its walls); the two pentagram caps patterned.
**Starfruit**: at rest, all planes off — five ridges. **Rose**: at rest
and turning (depth 0.12 → 0.16). **Möbius strip**: at rest (width
0.45 → 0.55). *Pass:* lantern acceptable; caps patterned whole, no hole,
tear or overlapping triangle; Starfruit recognisable; Rose still a
delicate flower; Möbius not too wide; Rose pinch and Möbius seam
closed. Say what to change. *Fail:* torn or folded cap →
`geometry._face_xy`'s least-squares branch; open seam or pinch → the
lift disagrees there (`_build_mobius`, `_build_rose`); too fat or thin
→ the depth / width in the builder (rows 94, 95).

**116. The Klein bottle reads as a bottle; the neck never crosses.**
Headless: `tests/test_shapes3d.py::{test_the_klein_bottle_is_appended_after_the_mobius_strip,test_the_klein_bottle_seam_welds_into_a_closed_grid,test_the_klein_bottle_crosses_itself_in_3d_and_not_in_4d}`.
Shape Klein bottle (26). At rest, all planes off; then XW, YW, ZW each
alone, slowly (Speed down); faces on and off. *Pass:* at rest a bottle
— a body, a neck curling over and back in (the orchestrator saw more a
curled horn or loop: say what you see); in every turn the neck passes
beside the body, never through it; no gap or sliver at the seam; the
neck's 16 lines dense enough. *Fail:* the neck through the body at some
angle → the lift's sin 2u term (`_build_klein`); a gap at the seam →
the v → π − v weld (`kkey`, nv even); too sparse → the 37 × 16 grid.

**117. Stepping to shape 26 on the keys, the pad and the desk.**
Headless: `tests/test_params.py::test_enum_norm_and_stepping tests/test_midi.py::test_relative_encoder_steps_shape tests/test_render.py::test_shape_renders tests/test_golden.py::test_the_engineering_table_matches_the_code`.
VIEW. → from the Möbius strip (25), → again, ← back. Pad (if any): RB,
LB. APC40:
the cue knob right past the end, then left. (copy) Save a preset on
the Klein bottle, load another, load it back. *Pass:* → reaches "KLEIN
BOTTLE", "576V 1152E · χ=0 · one side" (the χ drawn, not a box), and
stops there; RB and the cue knob the same, one step per click, no wrap;
the preset comes back on the Klein bottle. *Fail:* stops at 25 →
`view.shape`'s names (`params.py`, from `SHAPES`); wraps to the 5-cell
→ `Param.step`; a box for χ → the sym text's glyph (`Shape.sym`).

**118. The presets that show a changed shape.**
Headless: `tests/test_shapes4d.py::test_every_shape_draws_what_it_drew_before_the_lift_existed`.
Load factory `plasma-heart` (Heart), `spiral-silk` (Trefoil knot),
`inverse-halo` (Starfruit); then your shared `hi-frek-variation-1` and
`light-realm-variation-1` (Möbius strip, from your library). Music on. *Pass:* each still does what it was made for; note any
that now looks wrong. *Fail:* not a code fault: say which, and whether
to re-tune the preset or overturn row 89 / 94 for that shape.

**119. The turntable sheets.** (no app)
Headless: `tests/test_shapes4d.py::test_a_flat_shape_collapses_at_a_quarter_turn_of_each_w_plane`.
Open `docs/plans/assets/22-flat-shapes/`: `before-18-heart.png` …
`before-24-mobius-strip.png`, then `after-18-heart.png` …
`after-25-klein-bottle.png`, and a few 4D `before-*` (Tesseract,
Clifford torus). Optionally re-measure: `uv run python
tools/turntable.py --prefix check --no-png`, compare
`check-ratios.csv` with `after-ratios.csv`, delete the `check-*` files.
*Pass:* every before sheet of shapes 19–25 red at 90° and 270° in each
row; no after tile red; the numbers match the table in
`22-flat-shapes-and-face-patterns.md`; the after tiles look like the
shapes you know. Say which sheet looks worst. *Fail:* a red after tile
or numbers that differ → a geometry change since the sheets
(`git log hyperspace/geometry.py`); re-run the tool.

**Stream B (120–138), the face patterns.** 120 and 121 first, on the
Mac: they are what this container cannot check. Then on the laptop with
music: 122–128, 130–132, 137, 138; METER and PULSE on the rig (129); the
macro candidates with the APC40 (133–136, the listening session). FACES
is a page on the control window's rail. A house preset is one of the
house show's (PRESETS: SHOW `house`).

**120. The FACES page fits the control window on the Mac.**
Headless: `tests/test_ui_patterns.py::test_the_page_fits_with_every_row_driven_and_flat_or_the_longest_mode tests/test_ui_shell.py::test_every_page_fits_the_control_window`.
**These tests do not settle it.** They measure in the machine's own font
metrics, and in the cloud container those are not the Mac's: test_fx's
own two fit tests fail there by 18 px. The 18 px the FACES test leaves
spare there is not evidence. (copy) Launch, FACES. Pick KALEIDO, then
FLAT, then EMBER. Then the worst case: on ROUTING put a route on every
input (FACES' **+ SUB** … **+ LFO 2**), name a macro "a long macro name"
with a depth subscriber on one of them, untick Faces, and break
`patterns.glsl` (an undeclared name; save; put it back after). Then,
with Faces on and no error, FLAT and CAUSTIC: a pattern's own line
wrapping is the tallest case. *Pass:*
no scroll bar at the control size on any pattern; all seventeen chips
inside the page, their names inside the chips; every row's two lines on
screen, the driver's text cut short with "…" rather than over the edge;
nothing drawn over anything except the known dirty dot on the preset
strip's ▶. *Fail:* a scroll bar or a row off the page → `ui_patterns`'
`CELL_H`, `GRID_GAP`, `ROWS_GAP` (say how many px are missing); a name
out of its chip → `_mode_chip`.

**121. `patterns.glsl` compiles on Apple GL with every pattern.**
Headless: `tests/test_patterns.py::{test_the_face_shaders_pass_the_reference_compiler,test_the_shader_has_a_case_for_every_mode_in_the_table,test_every_input_moves_every_mode_from_1_to_2_6}`;
`uv run python tools/check_glsl.py`. Mesa (the tests' driver) and the
Khronos `glslangValidator` accept every mode; **neither is Apple's
compiler**. Launch on the Mac, faces on, FACES: click each of the
seventeen chips in turn, then **all neutral**, then F5 (TRIP), which
aims effects at the faces (the seed program). *Pass:* every pattern
draws; no "GLSL:" line on FACES and none on SYSTEM; every chip's swatch
shows a picture. *Fail:* a "GLSL:" line → Apple's compiler refuses
something Mesa allowed: note the line and column, then
`shaders/patterns.glsl` near it (an int where a float is wanted, a
dynamic array index — `band(i)` must stay an if-chain).

**122. One routing set on every pattern, with music.**
Headless: `tests/test_patterns.py::{test_the_factory_routes_put_lane_i_on_input_i,test_every_input_moves_every_mode_from_1_to_2_6,test_the_factory_depth_reads_on_loud_music_and_never_pins_an_input}`.
A house preset (its inputs at 1 and the six factory routes), a track
with a clear kick, snare and hats. On FACES step through every pattern
with › and leave each for a few bars. *Pass:* on every pattern the
same: the sub swells it (SCALE), the kick flashes it (GLOW), the low mids
bend it (WARP; on straight patterns only when loud), the mids keep it
moving (SPEED), the snare flares the colour (COLOUR), the hats sharpen
it (SHARP); quiet passages still move it, loud ones never pin it white
or black. Say which pattern reads worst. *Fail:* an input that does
something else on one pattern → that mode's case in `patterns.glsl`
(it must read inputs through the accessors only); everything pinned →
the route depths (`routing.PATTERN_DEPTH`).

**123. SPEED never jumps over a long set.**
Headless: `tests/test_patterns.py::{test_moving_speed_changes_the_rate_and_never_jumps_the_clock,test_speed_at_0_is_frozen,test_pulses_hats_still_sparkle_hours_into_a_set}`.
A house preset, music, RINGS, then PLASMA, ten minutes or more (the
jump grew with time on the old clock). Watch for a pattern snapping to
another place when the music changes. If the app has been up an hour
or more, also look at PULSE and EMBER. *Pass:* it speeds up and slows
down with the mids and never snaps; after an hour PULSE's hats still
twinkle and EMBER still drifts (EMBER is known to stop after about
12 h). *Fail:* a snap → `Renderer._pattern_clock` (it must integrate,
not multiply); PULSE's hats gone → the wrapped step in `pulse()`;
EMBER still within the hour → float32 precision of `u_ptime`.

**124. HUE on an LFO and SPREAD on a knob, on the 120-cell.**
Headless: `tests/test_patterns.py::{test_hue_turns_the_palette_and_keeps_the_shape,test_spread_at_0_plays_every_face_in_unison}`.
Shape 120-cell, faces on, CELLS. FACES: **+ LFO 1** on HUE (give LFO 1 a
slow rate and some depth on the LFO page); right-click SPREAD → Learn
desk onto a knob (or drag its slider). *Pass:* the palette turns slowly
round the wheel, the pattern's shapes unchanged; SPREAD at 0 every face
plays the same, at 1 as designed, at 2.6 each face its own phase and
colour. *Fail:* the shapes change with HUE → that mode's colour path
(HUE belongs in `finish()`); faces apart at 0 → the mode's face offset
(`face_rad` / `face_turn`).

**125. A first-time user on FACES.**
Headless: `tests/test_ui_patterns.py::{test_every_mode_has_a_chip_and_its_line,test_the_eight_rows_are_named_and_say_what_each_does_in_this_mode,test_a_rows_slider_hover_says_what_the_input_means,test_flat_says_it_reads_no_input}`.
Someone who has not seen the app, the patterns or the code; music on.
Ask them to open FACES and find a look they like, then say what each of
the eight inputs does on that pattern and what is moving it. Do not help;
note where they stall. *Pass:* they find a look without opening a
`.glsl` file, can say what the inputs do and what drives them, and find
"all neutral". *Fail:* note the words that confused them → the phrases
in `patterns.py` or the page's lines (`ui_patterns`).

**126. The swatches.**
Headless: `tests/test_ui_patterns.py::test_the_page_asks_the_renderer_for_swatches_and_draws_them tests/test_ui_patterns.py::test_swatches_draw_only_while_the_page_asks_and_leave_the_frame_as_it_was tests/test_ui_patterns.py::test_a_broken_save_keeps_the_last_good_swatches_and_is_compiled_once`.
FACES open, music, a busy shape (the 600-cell). Note the footer's FPS;
switch to VIEW, note it again. Move SCALE and COLOUR. Then, FACES still
open, break `patterns.glsl` (an undeclared name), save, wait ten
seconds, put it back and save. *Pass:* no stutter while it is broken
and the swatches keep their last good look; the fix lands; and each chip
shows a recognisable small picture of its pattern, moving; the swatches
follow the inputs; the FPS with FACES open is within a frame or two of
VIEW's. Say whether the swatches are legible at the size they are.
*Fail:* blank chips → `Renderer.swatch_error`; a frame-rate drop only
with FACES open → `Renderer._swatch_step` (one 64² swatch a frame).

**127. "+ SUB", the driver link, and undo.**
Headless: `tests/test_ui_patterns.py::{test_an_undriven_input_offers_the_conventions_source_and_stays_here,test_a_routed_input_shows_its_source_and_a_click_opens_routing,test_the_driver_line_names_the_macro_desk_and_base_subscribers,test_a_session_control_on_an_input_is_named_and_nothing_is_offered}`.
(copy) A house preset. FACES: on HUE, which no factory route drives,
click **+ LFO 1**; ⌘Z. On SCALE, click "SUB pushes +0.35". *Pass:* "+ LFO
1" becomes "LFO 1 pushes +0.35", the page stays on FACES and the preset's
dirty dot lights; ⌘Z takes the route back ("+ LFO 1" again); the SUB link
opens ROUTING showing only `pattern.mod.0`'s rows. *Fail:* the page jumps
to ROUTING → `ui_patterns`' offer; no undo → the route did not go
through the table (`ui_routing.add_route`).

**128. "all neutral" is one undo step.**
Headless: `tests/test_ui_patterns.py::test_neutral_puts_one_input_back_and_all_neutral_every_one`.
Drag four inputs off 1, wait a second between each. **all neutral**, then
⌘Z once. Then click a single input's **1**. *Pass:* all neutral puts
every slider at 1.00 in one go; one ⌘Z brings all four back ("undid
neutral pattern inputs"); **1** resets only its input. With every input
already at 1, all neutral does nothing and makes no step. *Fail:* ⌘Z
takes back one input at a time → `ui_patterns.neutral_all` (it must push
its own step first).

**129. METER and PULSE with real music on the rig.**
Headless: `tests/test_patterns.py::test_only_meter_and_pulse_read_the_bands_and_they_show_them`.
Glass (or projector), music through the real analyzer, the default
six-band layout. METER, then PULSE; then stop the music. *Pass:* METER:
one wedge per band, SUB's at twelve o'clock and the rest clockwise,
each lit outward as its band reads; the kick lights SUB and BASS, the
hats AIR. PULSE: the kick swells the magenta disc and throws a ring, the
snare shoots yellow rays, the hats sparkle. In silence METER shows dim
tracks and PULSE an idle heartbeat. Say whether each reads from the
audience. *Fail:* nothing moves → `app._bands` (the analyzer off?) or
`band(i)`; the wrong wedge lit → the band order in `meter()`.

**130. MARBLE's cost on the Mac.**
Headless: none (`uv run python tools/pattern_cost.py` times every mode
against FLAT; in software GL MARBLE is 4.19× FLAT on the 600-cell, CELLS
3.13×). Launch, the 600-cell, faces on, footer FPS: FLAT, CELLS, MARBLE;
then MARBLE with instances at 7. *Pass:* MARBLE holds the screen's
frame rate, or note by how much it drops against CELLS. *Fail:* a
visible drop → MARBLE's `fbm3` octaves in `patterns.glsl` (say the FPS).

**131. KALEIDO and TRUCHET as art.**
Headless: `tests/test_patterns.py::{test_new_modes_are_appended_so_preset_indices_keep_their_patterns,test_every_input_moves_every_mode_from_1_to_2_6}`.
KALEIDO and TRUCHET on a few shapes (tesseract, 24-cell, Clifford torus),
with music, faces' mix full. *Pass:* a judgement: KALEIDO's flat pop
colour and six mirrored wedges, TRUCHET's maze with its current. Keep,
change, or drop? Also: KALEIDO is six-fold on every face, whatever its
sides. *Fail:* not a code fault — say what to change.

**132. The house and party presets at depth 0.35.**
Headless: `tests/test_patterns.py::test_the_factory_depth_reads_on_loud_music_and_never_pins_an_input tests/test_routing.py::{test_factory_files_match_the_code,test_every_factory_preset_names_real_params_with_one_owner}`.
Music with quiet and loud passages. Two or three house presets
(hex-engine, ember-orbit, spiral-silk), then the party show's FACES and
TRIP. Then one of your own (from Dan's snapshot, in his library) with faces on.
*Pass:* quiet music visibly moves the faces; loud music is legible, no
input stuck at an end (EMBER not black, SPIRAL not blown out); yours
(still at depth 1) shows the difference. Say whether to re-save your
sixteen depth-1 presets at 0.35. *Fail:* too still → raise
`routing.PATTERN_DEPTH` and regenerate (`uv run python -m
hyperspace.preset`); pinned → lower it.

**133. The macro candidates: MACRO PERFORMANCE.** (APC40, listening)
Headless: `tests/test_macro_candidates.py::{test_each_candidate_loads_with_no_note_and_keeps_every_row,test_turning_a_macro_moves_its_bases_and_scales_its_routes}`.
PRESETS: load MACRO PERFORMANCE from your library. A
track with a clear kick and hats; the macros are D1–D8 (or ROUTING's
macro sliders). Follow
[`22-macro-candidates.md`](22-macro-candidates.md): each knob end to
end and back to rest (noon; 7 and 8 at zero), with music and in
silence. Then a breakdown on 7 over 8–16 bars and the drop on 7 down, 8
up. *Pass:* a judgement per macro: does it do its line? INTENSITY ×
DROP together reaches about ×4 on the lane routes: too much? *Fail:* a
knob that does nothing → the file's subscribers (ROUTING's macros
section); a load note → `Presets.load_doc`.

**134. The macro candidates: MACRO STREAMS.** (APC40, listening)
Headless: as 133. Load MACRO STREAMS. With a track playing, take each of
D1–D6 to zero and back; then D7 and D8. *Pass:* a band's knob at zero
stills only that band's plane and its pattern input; at full it doubles
them; D7 swings the palette, D8 the faces from unison to scattered. Say
which to keep. *Fail:* another band changes → the depth subscribers'
routes in the file.

**135. The macro candidates: MACRO INTENSITY.** (APC40, listening)
Headless: as 133. Load MACRO INTENSITY. D1, D2 and D3 one at a time, each
back to noon, with music and in silence. *Pass:* a judgement: which
INTENSITY is right — both (1), only the music's grip (2, nothing in
silence), only the resting look (3)? 1 and 3 share two bases: the last
turned wins.

**136. The macro candidates: MACRO BREAKDOWN DROP.** (APC40, listening)
Headless: as 133. Load MACRO BREAKDOWN DROP. D1 alone through a
breakdown and drop; then D2 and D3 as a pair (not with D1: they share
bases). *Pass:* a judgement: one knob or a pair? Is D1's top (brightness
4.0) too hot? Do INTENSITY and DROP still feel like their names at the
new depth (their routes sit at 0.35 now, the multipliers unchanged)?

**137. `legacy6` in silence.**
Headless: `tests/test_routing.py::{test_legacy6_reproduces_planedrive_and_u_bands,test_the_legacy6_preset_replaces_routes_and_lands_bases}`.
PRESETS: load `legacy6`; faces on, pick RINGS; no music, then music.
*Pass:* in silence the shape stands still (its rates sit at 0 — the
reference's parity) and the pattern shows as designed (inputs at 1); with
music the planes turn and the pattern moves as on any factory preset.
Say whether a still shape in silence is acceptable for the parity
anchor. *Fail:* a small, dim, grey, frozen pattern in silence → its
pattern bases are not 1 (`preset.legacy6_values`).

**138. WARP at 2.6 on HEX.**
Headless: `tests/test_patterns.py::test_every_input_moves_every_mode_from_1_to_2_6`.
HEX, then PLAID and KALEIDO; WARP from 0 to 2.6 by hand. *Pass:* 0 to
1 stays straight; above 1 it bends; at 2.6 still a honeycomb. Say
whether 2.6 is too strong. *Fail:* bends below 1 → that mode's `warp(p,
own)` (`own` 0 for a straight design); too strong → the `0.07` in
`warp()`.

## S. Plan 25: the shared library

Two Macs, both on this build, both with `[library] path` pointing at the
same cloud-synced folder ([`../SETUP.md`](../SETUP.md), "Share presets
with someone"). 141 runs on a scratch home (`HYPERSPACE_HOME` set to a
temp folder), never the real one.

**139. A save on one Mac appears on the other.**
Headless: `tests/test_shared_library.py::test_a_save_lands_in_the_library_and_last_show_in_the_machine_home tests/test_library.py`.
On A, save a new preset (**as…**). *Pass:* on B it appears in the
PRESETS list without a restart, within a couple of seconds of the sync
(the library watcher). *Fail:* never arrives → the cloud client first
(iCloud "Keep Downloaded", Dropbox "Available offline"), then
`Library.poll` / `_scan`.

**140. A re-save on one Mac re-applies on the other.**
Headless: `tests/test_library.py` (the watcher's re-apply tests).
On B, load a preset; on A, change it and save it again. *Pass:* B
re-applies it, as a hand edit of the file does. *Fail:* B keeps the old
look → `Library.poll`.

**141. A missing folder: said, saves off, nothing created.**
Headless: `tests/test_shared_library.py::{test_a_missing_library_is_said_and_never_created,test_every_write_into_a_missing_library_is_refused}`.
Scratch home: `[library]` `path = "/tmp/nowhere-hyperspace"` (a folder
that does not exist); launch. *Pass:* a warning on the footer ("shared
library not found at …"); the SYSTEM page's library line is red, "NOT
FOUND, saves are off (restart once it is there)"; a save says "not
saved"; `ls /tmp/nowhere-hyperspace` fails. *Fail:* the folder exists →
`Library.__init__` / `_write_text`.

**142. Machine files stay home.**
Headless: `tests/test_shared_library.py::test_the_migration_reads_machine_files_and_writes_documents_to_the_library`.
Note the dates of `config.toml`, `bindings.json` and `windows.json` in
the home; save a preset. *Pass:* none changed; none is in the shared
folder. *Fail:* → `app.main`'s `bindings_path(home)` and placement.

**143. A cloud conflict shows both entries.**
Headless: `tests/test_shared_library.py::test_a_cloud_conflict_copy_is_listed_beside_its_file`.
Take B offline; save the same preset on both Macs; reconnect and wait
for the sync. *Pass:* both entries show in the list (one under the
conflict copy's file name); each loads; delete one. *Fail:* one hides
the other → `Library._index`.

## T. The wired Xbox 360 pad

The pad's four checks from PRs #160 and #161, written into
[`../TESTING-GUIDE.md`](../TESTING-GUIDE.md) §(f) before they had numbers
here. A wired Xbox 360 pad (the Afterglow AX.1) on USB, no other pad.

**144. A wired Xbox 360 pad is found; the factory layout.**
Headless: `tests/test_gamepad.py::{test_usb_pad_when_glfw_has_none,test_decode_buttons_land_on_the_glfw_indices,test_decode_sticks_and_triggers}`, `tests/test_pad_learn.py::{test_the_factory_pad_walks_the_list_and_the_desk_the_bank,test_start_and_back_are_free_and_a_learned_start_hold_saves,test_the_right_stick_click_resets_the_4d_spin}`.
Launch from a terminal. *Pass:* the terminal says `gamepad: Afterglow
Gamepad for Xbox 360 over USB`; the ring lights one quarter (player 1)
instead of blinking; B / X step to the next / previous preset of the
PRESETS page's list (by name, wrapping; a preset saved a moment ago is
in it — not the desk's bank); A flips faces and Y lines; LB / RB step
the shape; the D-pad steps brightness (up / down) and speed (left /
right); START and BACK do nothing; the left stick orbits (up tilts the
camera up; held, it tumbles over the top and keeps going round) and its
click resets the camera; the right stick's up / down zooms and its
right / left speeds up / slows (through zero into reverse) the spin in
the XW, YW and ZW planes, and its click stops those three and turns them
back to 0°; RT pushes the 4D depth in and LT out. *Fail:* no line →
`gamepad.UsbPad` (libusb, the pad's ids); a button doing another's job
→ `gamepad.decode`'s index map; a stick backwards → the factory pad
rows in `routing.py`.

**145. Learn pad — a button.**
Headless: `tests/test_pad_learn.py::{test_a_button_learns_a_session_row_by_the_params_kind,test_a_button_learn_replaces_the_buttons_row_and_keeps_the_params_others,test_the_learning_press_does_not_fire_the_old_row,test_a_desk_learn_ignores_the_pad}`.
VIEW page: right-click Points → **Learn pad**, press Y. Then right-click
Brightness → **Learn pad**, press the D-pad's down. Afterwards put Y
back (Lines → **Learn pad**, Y). *Pass:* the footer says `learned
view.points ← …(into bindings.json); view.lines let go`; Y now flips
points; the D-pad's down still dims, one detent a press; `bindings.json`
holds `pad:Y` → `view.points`; pressing Y during the learn did not also
flip the lines. *Fail:* the press does nothing; Y does two things; a
desk knob turned during the learn completes it → `Learn.learn_pad_button`.

**146. Learn pad — a stick and a trigger.**
Headless: `tests/test_pad_learn.py::{test_a_stick_learns_a_push_route_into_the_preset,test_a_trigger_on_a_one_sided_fader_is_its_position,test_a_routed_axis_drives_its_param_and_is_claimed}`.
CAMERA page: right-click Pan X → **Learn pad**, push the right stick
left. Then VIEW page: right-click Field amp → **Learn pad**, squeeze RT.
*Pass:* ROUTING shows `right stick X pushes` on the first and `right
trigger positions` on the second; the first swings about its value and
comes back when the stick is let go; the second follows the trigger and
RT no longer rides the 4D depth, while LT still does; saved and
reloaded, both routes are there. *Fail:* the stick still orbits after
its route is made → `router.claimed("axis")`; letting go leaves the
setting moved → the route's rest.

**147. Momentary and hold on a pad button.**
Headless: `tests/test_pad_learn.py::{test_momentary_holds_a_toggle_while_the_button_is_down,test_hold_fires_once_after_hold_s,test_the_hold_times_agree}`.
In `bindings.json` change the `pad:Y` row's op to `"momentary"` and the
`pad:B` row (`preset.list.next`) to `"hold"`; ⌘R. *Pass:* lines show
only while Y is held; B steps the preset only after about 0.6 s held,
once per press; a tap does nothing. *Fail:* lines stay on after Y is
let go; B fires on a tap or repeats while held → the pad's hold timing
(`gamepad`, `midi.HOLD_S`).

## U. Plan 24: the party fixes

Plan 24 as built is [`24-party-fixes.md`](24-party-fixes.md). No preset
was edited or added: the checks that need a preset with fader rows, a
template, a grab mapping or a palette use the fixtures under
`tests/fixtures/`, copied into the copy's library (**(copy)**). The desk
checks run on the APC40; 154–157, 166 and 167 run on the laptop alone.

**148. The two-handed save, ten times in a row.** (copy, APC40)
Headless: `tests/test_desk_trust.py::{test_the_two_handed_save_works_ten_times_in_a_row,test_save_held_and_a_filled_pad_tapped_saves_a_new_preset_and_keeps_the_old,test_save_held_and_an_empty_pad_tapped_saves_into_that_slot,test_the_save_button_is_track_eights_clip_stop_invariant_and_lit_while_held,test_a_save_tap_does_not_load_or_start_a_hold}`.
Load TRIP (F5). Ten times, alternating: hold track 8's clip stop (G6·8,
SAVE; it lights) and tap a pad — an empty one (rows 4–5) and a filled
one (row 1) in turn, with SHIFT latched for every other save. Then press
SAVE alone and let go. *Pass:* each save makes a new preset (TRIP 2 …
TRIP 11); the tapped pad blinks and then stays green; the footer names
the new preset and its slot, and on a filled pad says the old preset is
still in the preset list — and it is, with no slot pointing at it;
`<home>/trash` is unchanged; SAVE alone changes nothing; the layer is as
it was. *Fail:* the pad loads instead → SAVE's light did not come on,
so the row is missing (`routing.APC_NEW_ROWS`, the SYSTEM line "SAVE not
added …") or the note differs (`apc40.SAVE`); the old preset overwritten
or trashed → `library.Project._save_new`; no blink → `MidiIO._save_tap`,
`apc40.blink_of`.

**149. Points, lines, faces and rotate on both layers.** (APC40)
Headless: `tests/test_desk_trust.py::{test_the_render_toggles_are_invariant_and_their_leds_show_the_live_state,test_an_older_presets_toggle_rows_drop_quietly_and_an_owners_row_with_a_note,test_every_factory_file_still_holds_the_toggle_rows_and_loads_quietly}`.
Press scene launch 1–4 (points, lines, faces, rotate) on the preset
layer, then with SHIFT latched. Toggle Points from the VIEW page. Load
TUMBLE from a pad, once with SHIFT up and once with it latched. *Pass:*
each button toggles its layer on both desk layers, and its light is the
live state: it follows the panel, and right after each load shows the
new preset's values (TUMBLE: points dark, the other three lit). No
"dropped" note on any factory preset's load. *Fail:* dark under SHIFT →
the session file lacks the invariant rows (`APC_NEW_ROWS`); a note on
load → `routing.TOGGLE_DESK_ROWS`.

**150. A load relights the whole desk.** (APC40)
Headless: `tests/test_desk_trust.py::{test_every_load_relights_the_whole_desk,test_a_load_lets_go_of_every_fader_the_preset_binds}`.
Light a button nothing maps (with `tools/midi_probe.py`), quit it, start
the app and load a preset. Move the crossfader through a few loads.
*Pass:* after the load every light is a mapped control's state or off;
nothing is left lit from before; the crossfader and MASTER keep working
through loads with no pickup gap. *Fail:* a stale light →
`MidiIO._dark_desk`; the crossfader dead after a load → the session
faders' rule in `MidiIO.redraw` (row 44).

**151. The desk log says what a press did.** (APC40)
Headless: `tests/test_desk_trust.py::{test_the_desk_log_keeps_the_last_twenty_presses,test_the_desk_log_lines_have_a_time_a_control_what_and_a_layer,test_the_system_page_helper_reads_the_log}`.
SYSTEM page → **midi** → open "desk log". Press a bank pad, a toggle, an
unmapped button, SHIFT, a band scene under SHIFT, SAVE + a pad, and hold
a filled pad. *Pass:* one line per press, newest first, each naming the
control, what it did (the preset loaded, "nothing (no row on the preset
layer)", "saved into slot …", "held: nothing saved (a filled pad only
loads)") and the layer ([preset], [global], [both]); never more than
twenty lines. *Fail:* no fold → `Panel._desk_log`; a wrong layer →
`MidiIO._handle`.

**152. Faders on the preset layer: a preset's rows and a learned one.** (copy, APC40)
Headless: `tests/test_desk_faders.py::{test_a_preset_with_fader_rows_lights_s1_s8_and_drives_them,test_the_fader_rows_round_trip_through_save_and_load,test_every_factory_preset_leaves_the_faders_dark_and_shift_lights_the_audio,test_a_track_fader_is_learnable_on_the_preset_layer}`.
Copy `tests/fixtures/desk-faders/faders.json` into the library's
`presets/`. Load FADERS (PRESETS list) and look at the on-screen desk;
move each fader. Save as FADERS 2 and reload it. Load TRIP: pull S1–S8.
Then on TRIP, VIEW page: right-click Lines opacity → **Learn desk**,
move S1; move it again, and feel where it takes hold. *Pass:* FADERS
shows S1–S8 labelled (points opacity, lines opacity, pattern mix, bitmap
alpha, brightness, speed, field amp, dream mix) and each moves its param
once it reaches the value; FADERS 2 has the same eight. TRIP's S1–S8 are
dark and do nothing. The learn lands ("learned view.lines_alpha ← S1 …
(into the preset)"), TRIP's dot lights, and S1 then drives the lines'
opacity after catching it. *Fail:* a fader dark on FADERS → the session
still holds it on both layers (the `bindings.json` move did not run:
`routing.FADER_SHIFT_ROWS`); TRIP's faders lit → `preset.fresh_desk`;
the learn refused as invariant → the same move.

**153. The audio strip under SHIFT; faders pick up across the latch.** (copy, APC40)
Headless: `tests/test_desk_faders.py::{test_a_fader_picks_up_its_own_param_across_the_latch,test_a_fader_on_its_value_when_the_layer_switches_is_caught_at_once,test_a_power_up_forgets_where_a_fader_was_on_every_layer,test_an_older_session_file_moves_the_fader_rows_to_shift_once}`.
First launch of this build on the copy: read the SYSTEM page's bindings
line. FADERS loaded (152): pull S1 to the top (points opacity 1). Latch
SHIFT; pull S1 a little, then sweep it through SUB's post-drive (the
ANALYZER page shows it). Unlatch and move S1 a little. Move MASTER and
the crossfader on both layers. *Pass:* the first launch says
`bindings.json` was updated, with `bindings.json.bak-v3` kept; under
SHIFT S1 does nothing until it reaches the band's value, then drives
it; back on the preset layer the opacity does not jump but waits for
the fader to come back to it; S7 and S8 under SHIFT are dynamics and
trim; MASTER and the crossfader do the same job on both layers. *Fail:*
the band jumps on the first move after a latch → `MidiIO.redraw`'s
switch block; no audio strip under SHIFT → `remap_factory`,
`FADER_SHIFT_ROWS`.

**154. Lines and points opacity.**
Headless: `tests/test_desk_faders.py::{test_lines_and_points_opacity_are_performance_params_at_one,test_an_opacity_at_zero_takes_its_layer_away_and_one_changes_nothing}`, `tests/test_golden_frames.py`.
VIEW page, a shape with points and lines on: move **Points opacity** and
**Lines opacity** from 1 down to 0 and back. Route an LFO to Lines
opacity (ROUTING, `+ route`). *Pass:* at 1 the picture is as before;
going down the layer fades evenly, its depth shading kept, and is gone
at 0; the LFO pulses it. *Fail:* a faint layer left at 0 → the factor
was put before the floor in `Renderer.draw_scene`.

**155. The coverage report against what you see as dark.**
Headless: `tests/test_desk_coverage.py::{test_the_committed_report_is_fresh_and_regenerates_byte_identical,test_the_preset_layer_is_the_three_strips_and_the_maps_preset_controls,test_every_factory_presets_numbers_are_in_the_report,test_cannot_show_is_the_rule_by_group}`.
Open [`assets/24-party-fixes/desk-coverage.md`](assets/24-party-fixes/desk-coverage.md).
Load TRIP, then hands-orbit, and compare the big on-screen desk (panel
hidden) with each one's row in "Preset × control". *Pass:* every lit
preset control is ● in the row and every dark one ·, S1–S8 included;
K7 (bitmap opacity) is ✕ on TRIP and turning it shows nothing; on
hands-orbit K4 and D4 (pattern mix, pattern) are ✕ with the faces off,
and come alive when Faces (scene launch 3) is pressed. Say whether
"dead" matches what you call dark, and which presets to fix first.
*Fail:* a lit control shown dark → `layer_controls`, `coverage_of`; a
control that visibly works marked ✕ → `learn.cannot_show`; then
`uv run python tools/desk_coverage.py --check` (a stale report fails).

**156. A desk template and a preset that names it.** (copy)
Headless: `tests/test_desk_templates.py::{test_a_preset_naming_a_template_loads_its_rows_with_the_overrides_on_top,test_a_save_round_trips_the_reference_not_the_expanded_rows,test_a_missing_template_is_a_note_and_the_overrides_alone,test_a_template_fixed_after_the_load_changes_no_override_on_save}`.
Copy `tests/fixtures/desk-templates/desk/fixture-shape.json` into the
library's `desk/` and `tests/fixtures/desk-templates/presets/templated.json`
into its `presets/`. (1) Load TEMPLATED. (2) Save as TEMPLATED 2 and
open its file. (3) Add a D5 row to the template file; load TEMPLATED 2
again. (4) Load TEMPLATED; change the template's D3 to `camera.zoom`;
without reloading, save as TEMPLATED 3, open its file, then load it.
(5) Move the template file out and load TEMPLATED. *Pass:* (1) D1 4D
depth, D2 dream mix, D3 pitch, D4 pattern, K1 brightness, K2 dark, K3
pattern mix, S1 lines opacity. (2) the file says `"desk_template":
"fixture shape"` and holds three desk rows, not the seven of the expanded desk. (3) D5 lights.
(4) TEMPLATED 3 holds the same three override rows as TEMPLATED, with
no D3 row; loaded, D3 is camera zoom. (5) the footer says "desk template
'fixture shape' not loaded …" and only D2 and K3 are lit. *Fail:* the
saved file holds every row → `Presets._desk_part`; D5 missing →
`Library.desk_template` read a stale file; a D3 override in TEMPLATED 3
→ the save compacted against the edited template (`Presets._at_load`).

**157. Click a control: this preset's params first.**
Headless: `tests/test_desk_coverage.py::{test_a_picked_control_is_offered_this_presets_params_and_a_click_maps_it,test_no_offer_for_a_control_that_cannot_be_mapped,test_ranked_puts_the_presets_own_params_first_in_tiers,test_the_offer_covers_no_control}`.
Load TRIP and click D5 on the on-screen desk, at the default size and
then with the panel hidden (the big desk). Read the list under the
transport row; open the chip ("all ▾" or "all params ▾"). Click an item.
Click SM, and D5 with SHIFT latched. Pick D5, open the chip's popup and
wait more than 20 s. *Pass:* the list starts with TRIP's routed params,
then its moved ones, then its effects' (no look-back param: it is off);
the chip shows the same list, then a menu per group; the click maps D5
("learned … ← D5"), the desk labels it, one undo step; the page click
on a param still maps as before; SM and D5-under-SHIFT show no list;
after 20 s the pick lets go and the panel takes clicks again. Say
whether an effect's blend, order and target belong in the list. *Fail:*
no list → `ui_desk._offer`; a dead param first → `learn.ranked`; the
list covers a control → `ui_desk.OFFER`.

**158. The dance sources on the HANDS page and in ROUTING.** (hand camera)
Headless: `tests/test_hands_dance.py::{test_the_hands_page_shows_every_new_source,test_the_routing_page_offers_the_new_sources_by_name,test_the_new_lanes_follow_the_switches_and_no_older_lane_moves}`.
HANDS page: the column right of the axis rows. Hands out of the box;
one hand in; both. ROUTING: open a row's source combo. *Pass:* the bars
hollow with no hand, filled for the hand in view, gap and twist only
with both; hover shows `hand:right.curl.index: 0.xxx`; the combo lists
`hand L curl thu` … `hand R flick`, `hands gap` and `hands twist`; the
twelve axes read as before. *Fail:* bars there but frozen → the tracker
gives no skeleton (curls and spread need it; energy and flick do not);
the page scrolls → `panel._dance`.

**159. Curl and energy, learned onto params.** (copy, hand camera)
Headless: `tests/test_hands_dance.py::{test_an_open_hand_is_uncurled_and_a_fist_is_curled,test_every_new_source_moves_its_param_through_a_scratch_library}`.
On a scratch preset, ROUTING: route `hand:right.curl.index` →
Brightness (positions) and `hand:right.energy` → Speed (a hand Learn
offers only the axes). Open hand still; slowly curl the index alone;
make a fist; shake the hand; hold still. *Pass:* a relaxed open hand
reads near 0 on every curl, a fist near 1, the index moves first (the
others follow a little); energy near 0 when still, high while shaking,
falling over about a second. *Fail:* an open hand well above 0 → raise
`CURL_RANGE_FINGER`'s low end; a fist under about 0.8 → lower its high
end; a still hand shows energy → raise `ENERGY_RANGE`'s floor.

**160. Spread.** (hand camera)
Headless: `tests/test_hands_dance.py::test_spread_is_the_fan_and_a_fist_does_not_fan`.
Route `hand:right.spread` → Brightness. Palm down, fingers together;
fanned wide; a fist. *Pass:* together ≈ 0, wide ≈ 1, a fist 0. *Fail:*
wide never reaches 1 → lower `SPREAD_RANGE`'s high end; together reads
over 0.2 → raise its low end.

**161. Flick.** (hand camera)
Headless: `tests/test_hands_dance.py::{test_a_flick_spikes_to_its_strength_holds_its_peak_and_decays,test_every_new_source_moves_its_param_through_a_scratch_library}`.
Route `hand:right.flick` → Brightness (push, depth 1). Flick the
fingers sharply, softly, and move the hand slowly across the box.
*Pass:* a sharp flick flashes and fades in a few tenths of a second, a
harder one brighter; a slow pass does nothing; one flick, one flash.
*Fail:* nothing on a real flick → lower `FLICK_ON`; flashes on ordinary
moves → raise it; double flashes → widen the gap to `FLICK_OFF`.

**162. Gap and twist.** (hand camera)
Headless: `tests/test_hands_dance.py::{test_twist_reads_level_for_mirror_hands_and_up_for_a_clockwise_wheel,test_gap_is_the_palms_distance}`.
Route `hands:gap` → Zoom and `hands:twist` → Yaw (CAMERA). Both hands
in: together and apart; hold a wheel and turn it clockwise and back; the
clap position. *Pass:* gap follows the distance smoothly, ≈ 0 with the
palms nearly touching, ≈ 1 at arm's width; twist level with mirror
hands and in the clap, up clockwise, down anticlockwise; one hand out →
both let go. *Fail:* twist backwards → the sign in `hands.twist`; gap
full too early → widen `GAP_RANGE`.

**163. The grab switch.** (hand camera)
Headless: `tests/test_hands_grab.py::{test_the_hands_page_shows_the_grab_switches,test_the_routing_page_offers_the_grab_as_a_gate,test_the_grab_lanes_follow_every_older_lane,test_the_grab_lane_closes_with_a_fist_and_holds_through_noise}`.
HANDS page: each hand's curl row ends in "grab ○". Open hand; slowly
close it; hold; loosen it halfway; open it; flash a fist for a split
second; take the hand out as a fist. ROUTING: a row's gate combo.
*Pass:* "grab ●" lights red once the fist is made (hover: fist ≥ 0.65),
stays lit loosened halfway, goes dark when open; a split-second fist
does nothing; a fist leaving the box goes dark at once; the gate combo
lists "L grab" and "R grab" after the eight pinches. *Fail:* never lit
on a real fist → hover and read the fist level; if it tops out under
0.65, lower `GRAB_CLOSE`; lit on a relaxed hand → raise it; flicker
half-closed → widen the gap to `GRAB_OPEN`; never lit and the curl bars
hollow → no skeleton.

**164. Grab to steer the shape.** (copy, hand camera)
Headless: `tests/test_hands_grab.py::{test_the_shape_follows_the_hand_only_while_it_is_closed,test_the_fixture_is_the_owners_grab_mapping}`.
Copy `tests/fixtures/grab-follow/grab-follow.json` into the library's
`presets/` and load GRAB FOLLOW (or, on a scratch preset, add three
`position` rows on ROUTING: `hand:right.yaw` → `camera.yaw`,
`hand:right.pitch` → `camera.pitch`, `hand:right.roll` → `rot.phase.XY`,
each gated "R grab"). Open hand: turn it. Make a fist and turn it; open
it mid-turn. *Pass:* the open hand moves nothing; with a fist the shape
turns with the hand; opening lets go and the shape returns to where its
params sit. Say whether the shape should rather be caught where it is
(see *Fail*). *Fail:* the shape jumps when the fist closes → `position`
is absolute by design (catching it where it is needs a relative op,
plan 28); the turn feels 2:1 → the route's depth.

**165. Hands on the projector at the rig.** (projector, hand camera)
Headless: none (a config line).
In the rig's config (the owner's `~/Hyperspace/config.toml.rig`, which
this run did not touch), the projector's `[[output.screens]]` entry:
add `hands = true` (see [`../SETUP.md`](../SETUP.md)). Launch on the rig,
hands in the box. *Pass:* the ghost hands show on the projector, and
the OUTPUT page's hands tick for that output is on. *Fail:* no hands →
that entry says `hands = false`, the ghost hands are off (HANDS page),
or the output is not the one you think (screen indices move after an
HDMI re-sync).

**166. The palette fold on a fader.** (APC40 for the fader; the rest on the laptop)
Headless: `tests/test_fx_palette.py::{test_the_defaults_leave_every_frame_byte_identical,test_a_turned_up_mix_changes_the_picture,test_the_grey_ramp_is_a_greyscale_and_a_coloured_one_is_not,test_every_palette_param_takes_a_route,test_a_raised_floor_does_not_light_a_see_through_ground}`.
Any preset. FX page: the Palette chip is last; switch it on (nothing
changes); right-click its **Mix** → **Learn desk**, move S2; sweep S2.
Then move Centre, Width, and set Mode to 1. *Pass:* at mix 0 the
picture is as it was; raising S2 pulls every hue onto a slice around
Centre; Width 0 is one colour; Centre sweeps the slice with no seam;
Mode 1 paints brightness through the grey ramp (a greyscale picture);
a grey wireframe takes the slice's edge colour once Sat low is above 0.
*Fail:* a seam as Centre sweeps → the triangle in `palette.glsl`; the
picture changes at mix 0 → the chain's skip of a zero-mix pass; S2
refused → the fader is still the session's (153).

**167. A saved palette, and the palette's strip.** (copy)
Headless: `tests/test_fx_palette.py::test_a_saved_palette_is_an_fx_module_preset`, `tests/test_fx.py::test_the_palette_strip_fits_in_both_modes`.
Copy `tests/fixtures/palettes/fx/sunset.json` into the library's `fx/`.
FX page, open Palette: in Mode 0 the strip shows mode, centre, width,
sat (low and high on one row) and val; set Mode 1: it shows mode,
anchors and one row per anchor (hue, sat, val). Load **sunset** from the
FX page's preset strip (under its title), change an anchor, save it as
your own (**as…**), load another, load yours back. *Pass:* the page does not scroll in
either mode; only the open mode's rows show; sunset paints violet →
magenta → orange → cream; your palette comes back with its anchors.
*Fail:* a row cut off or the page scrolls → `ui_fx.strip_rows`,
`HIDDEN_BY_MODE`; a mode's rows never appear → the `mode` param; anchors
missing after a load → the ids.

## W. Plan 27: the device registry

Plan 27 as built is [`27-device-registry.md`](27-device-registry.md):
its "The block to paste" section has the exact `[[devices]]` blocks these
checks use (today's rig, a phone, the recorded cloud). Run them on the
copy (**(copy)**): several edit `config.toml` while the app runs — the
registry re-reads the device list within about half a second of a save,
so these checks are the exception to "edit `config.toml` with the app
closed". Put back what each changes. 168–175 need nothing but the rig as
it is; 176–177 a second USB MIDI controller; 181–185 FL Studio (or MIDI
Monitor.app) over the IAC bus; 186–189 a phone on the same Wi-Fi as the
Mac; 190 the laptop alone.

**168. The SYSTEM page lists every device, and an un-renamed config says so.** (copy)
Headless: `tests/test_ui_shell.py::test_system_page_shows_one_line_per_device`, `tests/test_config.py::test_no_devices_list_translates_the_old_tables_with_one_note_each`, `tests/test_devices.py::test_todays_rig_as_a_devices_list_equals_the_old_tables`.
Launch with the copy's `config.toml` as it is (old `[midi]` / `[gamepad]`
/ `[hands]` / `[bridge]` tables), APC40 and pad plugged in. SYSTEM page →
**devices**. Then replace the old tables with the "today's rig" block
(the hands' keys moved onto the `leap` entry if the hands are on) and
relaunch. *Pass:* one line per device, in order — `pad · gamepad ·
connected · 21 sources · …` (the road, `usb: <name>` for the wired
pad), `apc40 · midi · connected · 137 sources
· Akai APC40 · N bindings`, `leap · hands · off · 0 sources` (or
`connected · 42 sources` with the hands on, followed by `hands-daw ·
midi-out · …`), `bridge · bridge · off · 0 sources` — and one "config:
[midi] is now a [[devices]] entry …" note per old table the file holds;
the desk, the pad and the hands work as before. After the paste: the
same lines and no note. *Fail:* a line missing → `config._translate` /
`DEVICE_TABLES`; a note for a table the file does not hold → `_translate`;
a note after the paste → an old table left in the file ("… is ignored").

**169. A hands entry carries the hands setup.** (copy, hand camera)
Headless: `tests/test_config.py::test_a_devices_list_wins_and_is_checked_per_entry`.
On the list form, put the rig's `[hands]` keys (`mode`, `dofs`, `out`,
`calibration`, …) on the `leap` entry with `enabled = true`, and delete
the `[hands]` table. Launch. *Pass:* the HANDS page shows the same axes
and calibration as with the old table; the tracker connects; `hand:`
routes work. *Fail:* the page shows the default axes → the fold-back of
the first hands entry into `cfg["hands"]` (`config._devices`).

**170. A device that raises does not take the frame down.** (copy)
Headless: `tests/test_devices.py::test_one_devices_exception_never_stops_the_frame`, `tests/test_app_boundary.py::test_a_raising_adapter_is_a_note_that_survives_the_frame`.
APC40 plugged in, the app running. In `hyperspace/midi.py` add `raise
RuntimeError("x")` as the first line of `MidiIO.poll` and save. Then
remove it and save. *Pass:* the hot-reload toast reads `midi:
RuntimeError: x` and the apc40 line `error: RuntimeError: x` in the
warning colour, while the picture, the pad and the hands go on; after
the second save the toast clears and the line reads `connected` again.
*Fail:* the window freezes or the other devices stop →
`DeviceRegistry._guard`; the error stays after the fix → the clean-poll
clear in `_guard`.

**171. ⌘R with the USB pad.** (pad)
Headless: `tests/test_devices.py::test_pad_close_stops_the_usb_reader_and_forgets_the_pad`, `tests/test_app_boundary.py::test_the_host_close_list_is_every_adapter_in_shutdown_order`.
The wired Xbox 360 pad on USB (T, 144). Press ⌘R three times, a few
seconds apart. *Pass:* each new image finds the pad within a few
seconds: its ring lights one quarter, the sticks orbit; the pad line on
SYSTEM reads `connected`. *Fail:* the pad is dead after a restart (the
ring blinks) → `Pad.close` / `UsbPad.close`, the reader thread's join.

**172. A device whose open failed is retried; a tracker comes back on its own.** (copy, hand camera)
Headless: `tests/test_devices.py::test_the_registry_retries_a_failed_open_and_a_lost_device_reconnects_itself`, `tests/test_hands_tape.py::test_a_bad_tape_path_is_a_note_the_pages_show`.
On the `leap` entry set `enabled = true` and `tape = "missing.json"` (no
such file) and launch. After a few seconds copy a real tape
(`tools/hands_tape.py record`) to `<home>/missing.json`. Then remove the
`tape` key, save, and once the camera's hands show, unplug the Leap;
plug it back. *Pass:* the leap line reads `error: …No such file…` with
one "hands: …" note on SYSTEM and in the terminal and no more notes;
within about 10 s of the copy the line reads `connected` with no
relaunch and the HANDS page plays the tape. Unplugged, the line reads
`error: no camera` (the tracker's own words) and nothing new appears in
the notes; plugged back, it reads `connected` on its own, with no
relaunch. *Fail:* it stays `error` after the file appears →
`DeviceRegistry._open`'s schedule; a note every 2 s → the first-miss
guard; the hands never come back after a replug → the Leap SDK's thread
(`LeapSource`), not the registry.

**173. Editing `[[devices]]` lands without a relaunch; a bad edit does not.** (copy)
Headless: `tests/test_devices.py::test_the_config_list_is_watched_every_30_frames_and_a_bad_edit_keeps_the_old_list`, `tests/test_config.py::test_read_devices_reports_problems_and_prints_nothing`.
On the list form, with the app running: set the `bridge` entry's
`enabled = true` and save. Then write `role = "a:b"` on any entry and
save. Fix it and save again. *Pass:* within a second "devices: bridge
changed — reopened" appears on SYSTEM and the bridge line reads
`connected` or `lost` (not `off`); the bad edit gives one "config:
[[devices]] not applied — … — the old list stands" note and nothing else
moves; the fixed file is followed again. *Fail:* nothing happens after a
save → the mtime watch (`DeviceRegistry.watch`, `WATCH_FRAMES`); the
whole app reloads or a window moves → something other than the device
list was re-read.

**174. A second pad is refused, and comes up when the first leaves.** (copy)
Headless: `tests/test_devices.py::test_a_second_enabled_device_claiming_a_scheme_is_refused_with_a_note`.
On the list form, with the app running, add `[[devices]] role = "pad2"
kind = "gamepad"` and save. Then set the first pad's `enabled = false`
and save. *Pass:* `pad2 · gamepad · error: feeds 'axis', which pad
already feeds — not opened` and one note saying the same; the first pad
works as before. With the first pad off, `pad2` reads `connected` (or
`lost` with no pad plugged in) and the sticks orbit through it. *Fail:*
both read `connected` and the sticks fight → `devices.make`'s claimed
schemes; `pad2` stays refused → `DeviceRegistry.apply`'s re-make.

**175. The APC40 plugged in after launch lights up.** (APC40)
Headless: `tests/test_device_inputs.py::test_a_missing_desk_is_lost_its_rows_wait_and_it_comes_up_with_its_feedback`.
Unplug the APC40 and launch. Look at SYSTEM and the on-screen desk;
press a bank pad on the on-screen desk. Plug the APC40 in; wait ten
seconds. Move the crossfader and a knob; load a preset from a pad.
*Pass:* the apc40 line reads `lost` (not an error), the on-screen desk
still works; within about ten seconds of plugging in, the line reads
`connected`, the desk wakes (its power-up), every light shows the loaded
preset's state (the scene-launch toggles the live state), and the
crossfader and the knobs act at once with no relaunch. *Fail:* the line
reads `error` → the desk's own retry (`midi.Ports.retry`), not the
registry's; the desk stays dark after connecting → the reconnect's
redraw in `MidiIO.poll`.

**176. A second controller maps on Learn desk with no code.** (copy, APC40, a second USB MIDI controller)
Headless: `tests/test_device_inputs.py::{test_two_desks_open_each_with_its_profile_and_its_own_rows,test_a_generic_desk_maps_on_the_desks_learn_with_no_code,test_the_desk_whose_profile_wrote_the_table_owns_the_unqualified_rows}`.
Plug in any knob box. With the app running, add `[[devices]] role =
"launch"  kind = "midi"  profile = "generic"  port = "<part of its
name>"` (after the APC40's entry is best) and save. Right-click
Field amp (VIEW, the field row) → **Learn desk**, turn a knob on the
box; turn it through the slider's value. Turn the APC40 knob that has
the same CC number. Save the preset as a copy, load another, load it
back. *Pass:* `launch · midi · connected · 0 sources · <its port> · 0
bindings`; the box's lights do nothing new (nothing is sent to it); the
footer says "learned view.inst_amp ← MIDI CC n ch1 on launch (into the
preset)" and the preset's dot lights; the knob takes hold once it
crosses the value, then drives it; the APC40's same CC does not move it,
and an APC40 knob already on the param still works; after the reload
the box's knob still works. *Fail:* `error: … matches no port` → the
entry has no `port`; the row is `cc:0:n` with no `@launch` →
`MidiIO.qualifier`, `DeviceRegistry.midi_roles`; the box's lights
flicker → `generic.FEEDBACK`, `MidiIO._send`.

**177. SHIFT is the APC40's; the second desk keeps its layer.** (copy, APC40, the second controller)
Headless: `tests/test_device_inputs.py::{test_the_latch_is_per_role,test_an_unqualified_row_is_the_first_midi_roles,test_shift_on_the_apc40_leaves_the_second_desks_caught_rows_caught}`.
176's rig. Latch SHIFT on the APC40. Turn the box's learned knob;
right-click another param → **Learn desk** → turn another box knob; then
try **Learn desk** with an APC40 knob. Unlatch; load a preset with SHIFT
latched again. *Pass:* the box's knob keeps driving its param under
SHIFT; the second learn lands; the APC40 learn is refused ("… is on the
global layer (the session's) — latch SHIFT off to learn into the
preset") and stays armed; the box's caught knob
does not have to be caught again after SHIFT flips; the load drops the
APC40 to the preset layer. *Fail:* the box goes dead under SHIFT →
`Bindings.dispatch`'s `layer_of(role)`; the box's learn is refused →
`learn.blocked`.

**178. The pages offer what the rig lists.** (copy)
Headless: `tests/test_device_inputs.py::test_schemes_wants_and_row_schemes_come_from_the_registry`, `tests/test_ui_lfo.py::test_the_lfos_are_offered_as_routing_sources`.
ROUTING page → a row's source combo; a modulatable param's right-click
menu, with and without a bridge entry in the list. *Pass:* the combo
lists the analyzer's lanes, then LFO 1–4, then the pad's axes, the
hands, then `ext` (when the bridge is listed or a route names it), in
the `[[devices]]` order; the menu offers Learn desk, Learn hand ▸ (a
tracker on) and Learn pad (a pad connected), as before. **Known:** with
a bridge listed (on or off, which includes every un-renamed config) the
menu also offers **Learn bridge**, and no move completes it — cancel it
(register row 151). *Fail:* a scheme missing → its device's `feeds`,
`DeviceRegistry.continuous_schemes`.

**179. The sticks still steer; a routed stick does not.** (pad)
Headless: `tests/test_device_inputs.py::test_the_pad_runs_on_the_registry_rows_axes_and_its_camera_job`, `tests/test_app_boundary.py::{test_the_relative_writers_run_with_the_setters_and_move_the_base,test_a_routed_right_stick_leaves_the_w_rates_alone,test_the_sticks_camera_job_reads_through_the_pads_feel}`.
The left stick orbits, the right stick's Y zooms and X rides the 4D
spin, the triggers ride 4D depth — with `desk.pad.feel` (SYSTEM →
gamepad) on follow and on spring; then **Learn pad** a stick onto a
param. *Pass:* exactly as before plan 27 (144, 146); the learned stick
drives its param and stops orbiting. *Fail:* nothing moves →
`PadDevice.act`, `gamepad.steer`; a routed stick still orbits →
`gamepad.publish` (no names, so `claimed` is empty).

**180. The hands on the registry.** (copy, hand camera)
Headless: `tests/test_device_inputs.py::test_the_hands_run_on_the_registry_through_hands_device`, `tests/test_devices.py::test_the_hands_shims_ports_are_the_layout`.
Hands on (the camera, or a tape). *Pass:* SYSTEM shows `leap · hands ·
connected · 42 sources · …` (the forty `hand` lanes with six axes a
hand, then gap and twist); the HANDS page, hand routes, a hand Learn
and the ghost hands on the projector all as before; after ⌘R the hands
come back. *Fail:* `error: no hands setup …` → `Context.hand_settings`;
the ghost gone → the registry listener's `renderer.ghost.source`
(`app.point_at_devices`).

**181. A param's effective value goes out on the bridge.** (copy, FL Studio or MIDI Monitor, IAC)
Headless: `tests/test_sinks.py::{test_a_param_routed_to_the_bridge_sends_its_effective_value_after_apply,test_a_sink_row_is_a_session_row_never_a_performer_and_round_trips}`.
Bridge on (`role = "bridge"  kind = "bridge"  out = "IAC"`), a MIDI
monitor on the IAC bus. Right-click Brightness → **Learn sink ▸** →
`bridge:6 · pitch ch7`; give Brightness a moving performer (Learn hand,
or an LFO push). Load another preset. *Pass:* the footer says "sent
view.bright → bridge:6 (into bindings.json)"; the monitor shows pitch
bend on channel 7 following the **moving** brightness (the setting plus
the hand or LFO), not the slider alone, and nothing while it holds
still; `bindings.json` has the row; the other preset leaves it in place.
*Fail:* the bend follows only the slider → the sink read before
`reg.apply` (`app.frame`'s `devs.send`); nothing on channel 7 →
`BridgeDevice.send`, `table.sinks("bridge")`.

**182. The bridge's `send` list becomes rows once, seen in the DAW.** (copy, FL Studio, IAC)
Headless: `tests/test_sinks.py::{test_the_bridges_send_list_becomes_sink_rows_once_with_one_note,test_rows_deleted_on_routing_never_come_back_the_translation_is_marked,test_the_system_line_of_a_sink_says_what_it_sends,test_the_bridge_publishes_its_ext_labels_and_rests}`.
A copy whose bridge has never been on: set `[bridge]` (or the bridge
entry) to `enabled = true`, `out = "IAC"`, `send = ["lane:*",
"param:view.bright"]`, and launch. FL Studio takes IAC as input (L46).
Relaunch. Then × every bridge row on ROUTING → sinks, edit
`config.toml` (any change), relaunch. *Pass:* one note "bindings:
[bridge] send is now sink rows in bindings.json (lane:* → bridge:0,
param:view.bright → bridge:6) …" on SYSTEM and in the terminal; ROUTING →
sinks lists "every lane → bridge:0" and "param view.bright → bridge:6";
SYSTEM: `bridge · bridge · connected · 16 sources · 2 sinks · …`; FL
receives the lanes as before (pitch bend from channel 1) and brightness
on channel 7; the source combo lists `ext ext 0` … `ext ext 15`. The
second launch: no note. After the deletion: no row comes back
(`bindings.json` holds `"sinks_seeded": ["bridge"]`). **Check FL's channel
map once:** an entry after `lane:*` lands at channel 6 (seven, 1-based)
whatever the band count; with more or fewer than six bands, a mapping
from before may need its channel moved. *Fail:* the note every launch,
or rows back after the deletion → `_seed_sinks`' `sinks_seeded` mark;
the lanes stop → `sink_values`' `lane:*`.

**183. Learn sink never asks Replace / Keep.** (copy)
Headless: `tests/test_sinks.py::test_learn_sink_on_a_param_lands_a_session_row_with_no_question`, `tests/test_ui_routing.py::test_the_routing_page_lists_the_sink_rows_with_the_others`.
The bridge on. Put an LFO push on Brightness (or Learn a hand onto it).
Right-click Brightness → **Learn sink ▸** any port; then right-click
Speed → **Learn sink ▸** the same port. Right-click Speed → **Unbind**.
*Pass:* no prompt either time; the LFO (or hand) still performs
brightness; the second learn says "…; param:view.bright let go"; Speed's
menu lists "→ bridge:N" dim; Unbind leaves that row; the preset's dot
stays clean. *Fail:* a Replace / Keep prompt → the row went through the
referee; a dirty dot → the row reached the preset (`is_session_row`).

**184. The hands' DAW out works as before, from the `hands-daw` sink.** (copy, hand camera or a tape, FL Studio)
Headless: `tests/test_hands.py::{test_a_lost_daw_port_is_looked_for_again_and_the_daw_resynced,test_a_daw_port_that_stays_missing_is_looked_for_less_often,test_a_virtual_port_is_made_again_when_it_fails,test_the_hands_daw_sink_sends_what_the_instrument_made_and_no_port_is_opened}`, `tests/test_sinks.py::test_the_hands_daw_sink_on_the_registry_sends_what_handsio_sent`.
Hands on with `out = "IAC"` (a named bus, so a loss can be tested), FL
listening to it. Raise the right hand. Take the IAC bus offline in Audio
MIDI Setup for a few seconds, then back. *Pass:* SYSTEM shows the leap
line and right after it `hands-daw · midi-out · connected · 0 sources ·
0 sinks · IAC Driver Bus 1 · leap's DAW out · cc … ch16`; FL's mapped
knobs follow the hands, presence and pinch notes arrive; offline, the
line reads `lost`, and within about 2 s of the bus coming back it reads
`connected` and FL's knobs jump to where the hands are (the resync). FL's
port list holds no second "Hyperspace Hands". *Fail:* no messages →
`MidiOutDevice.send`, `carries`; no resync → `MidiOutDevice.poll`; a
second port → something still opens one (`HandsIO` must not).

**185. `[hands] out` on a list, and an explicit `midi-out`.** (copy)
Headless: `tests/test_sinks.py::test_hands_out_becomes_the_hands_daw_entry_with_a_note_when_written`, `tests/test_config.py::test_a_devices_list_wins_and_is_checked_per_entry`.
On the list form with the hands on, put `out = "IAC"` on the `leap`
entry and launch. Then remove it and add `[[devices]] role = "daw"  kind
= "midi-out"  port = "IAC"  carries = "leap"`; relaunch. *Pass:* one note
"config: [hands] out is now a [[devices]] entry (role = 'hands-daw', … ,
carries = 'leap')" and a `hands-daw` line naming the bus; with the
explicit entry, no derived `hands-daw` line and the `daw` line carries
the hands. *Fail:* two lines both carrying leap → `config._daw`'s
"already carried" test.

**186. A phone's fader drives a param, with no code.** (copy, a phone on the same Wi-Fi)
Headless: `tests/test_osc.py::{test_an_osc_entry_alone_adds_the_device_and_a_fader_moves_a_routed_param,test_only_osc_py_and_the_kind_table_name_the_osc_device,test_a_learn_armed_for_the_role_takes_a_hit_as_a_row_and_a_fader_as_a_route}`.
Install an OSC controller app (TouchOSC, or any); set its host to the
Mac's LAN address (System Settings → Wi-Fi → Details) and its outgoing
port to 9000; note the addresses its first two faders send (TouchOSC's
simple layout: `/1/fader1`, `/1/fader2`). With the app running, add the
phone block with `axes = ["/1/fader1", "/1/fader2"]` and save.
Right-click Yaw (CAMERA) → **Learn phone**, move fader 1 a good way.
*Pass:* within a second `phone · osc · lost · 2 sources · UDP
0.0.0.0:9000` (macOS may ask once whether Python may accept incoming
connections: allow); a fader move makes it `connected · … · /1/fader1
0.42`; the learn lands ("learned camera.yaw ← …") and the yaw then moves
with the fader; ROUTING's source combo lists `phone` with `1/fader1` and
`1/fader2`. *Fail:* the line stays `lost` → the app's host or port, or
the firewall prompt was denied (System Settings → Network → Firewall); no
"Learn phone" item → the device's `wants`; `error: OSError … in use` →
another program on 9000 (189).

**187. A phone's button fires a row.** (copy, the phone)
Headless: `tests/test_osc.py::{test_a_hit_with_velocity_fires_its_rows,test_a_learn_armed_for_the_role_takes_a_hit_as_a_row_and_a_fader_as_a_route}`.
186's rig: add the app's first push button's address to `hits`
(TouchOSC: `/1/push1`) and save. Right-click **Faces** (VIEW) → **Learn
phone** → press the button; then press it a few times. *Pass:* the learn
lands as a row in `bindings.json` (`phone:1/push1` → `view.faces`); each
press toggles the faces once and the release does nothing. *Fail:* each
press toggles twice → the app sends a non-zero release (set the button's
off value to 0); nothing → the address is not in `hits` (the line's last
message shows what arrives).

**188. A silence reads `lost`; the faders keep their place.** (copy, the phone)
Headless: `tests/test_osc.py::{test_lost_after_the_timeout_and_back_on_the_next_message,test_hold_false_lets_the_routes_go_in_a_silence}`.
With 186's route acting, leave the phone alone for ten seconds, then
move the fader. Add `hold = false` to the entry, save, and repeat.
*Pass:* about 5 s after the last message the line reads `lost` and the
yaw stays where the fader left it; one move and the line reads
`connected` and the yaw follows again. With `hold = false`, after 5 s
the yaw returns to its setting. *Fail:* the yaw snaps back with `hold`
unset → `OscDevice.feed`; the line never reads `lost` → the app streams
continuously (an accelerometer page: expected).

**189. A busy port is a line, not a crash, and comes up when it frees.** (copy, the phone)
Headless: `tests/test_osc.py::test_a_busy_port_is_an_error_line_and_comes_up_when_it_frees`.
Quit the app. In a terminal, hold port 9000: `python3 -c "import
socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);
s.bind(('0.0.0.0', 9000)); input()"`. Launch with the phone entry, then
press Return in that terminal. *Pass:* `phone · osc · error: OSError: …
Address already in use` and one note; the rest of the app runs; within
about 10 s of Return the line reads `lost`, then `connected` on the
phone's next message. *Fail:* the app stalls → `osc.Server` is blocking;
the line stays `error` after the port frees → the registry's retry
schedule.

**190. The recorded cloud plays at its own rate.** (copy)
Headless: `tests/test_clouds.py::{test_a_cloud_entry_publishes_the_recording_at_its_own_rate,test_a_missing_recording_is_an_error_line_and_comes_up_when_it_appears,test_a_cloud_is_on_the_registry_not_the_router}`.
Copy `hyperspace-python/tests/fixtures/clouds/knot.npz` into
`<home>/clouds/` and add the cloud block. Watch SYSTEM for a few seconds.
Then rename the file and add `loop = false` to the entry (an edit, so it
reopens); rename the file back. *Pass:* `scan · cloud · connected · 1
source · knot.npz · frame n/16 · … points · 12 fps`, the frame counting
through 16 at 12 frames a second (one loop about every 1⅓ s) and
starting again; the scene shows the knot as dots in the shape's world
(plan 26's `cloud` node draws it; its own checks are 216–218). Renamed:
`error: FileNotFoundError …`; back: `connected`
within about 10 s, and with `loop = false` the frame stops at 16/16.
*Fail:* the frame number follows the app's frame rate →
`CloudDevice.poll`.

## V. Plan 26: the render graph

Plan 26 as built is [`26-render-graph.md`](26-render-graph.md). No
factory preset carries a `graph` section, so the checks that need one
copy the fixture `hyperspace-python/tests/fixtures/presets/hands-lines.json`
(the hands in the scene as lines, through the acid, the history holding
them) into the copy's library, or a variant of it made by editing the
copy's own file (**(copy)**). **The copy's library must be the copy**:
if `~/Hyperspace-try/config.toml` has a `[library] path` line, delete
that line on the copy first, so the library is `<home>` — never copy a
fixture into the shared Drive folder. A preset file in `<home>/presets/`
appears in the PRESETS list by its file name. The variants, each a copy
of `hands-lines.json` saved under a new name in `<home>/presets/` with
its `"graph"` replaced:

- **hands-solid.json** — `{"nodes": [{"kind": "hands", "into": "scene"},
  {"kind": "history", "holds": "scene+hands"}]}` (the hands in the scene,
  solid);
- **hands-depth.json** — `{"nodes": [{"kind": "hands", "laid": "depth"}]}`
  (the hands' layer, depth-aware);
- **two-acids.json** — `{"nodes": [{"kind": "effect", "file": "acid",
  "instance": 2}]}`, and in `"values"` add `"fx.acid.2.on": true,
  "fx.acid.2.twist": 0.3` (the first acid keeps the file's 0.9);
- **two-hands.json** — `{"nodes": [{"kind": "hands", "into": "scene"},
  {"kind": "hands", "instance": 2}]}`.

The hands checks need the hand camera, or the synthetic tape
(`uv run python tools/hands_tape.py synth /tmp/hands.json`, then `enabled
= true` and `tape = "/tmp/hands.json"` on the hands entry, as in
TESTING-GUIDE L44), with **Ghost hands** ticked on the HANDS page.
191–196 and 211, 212, 215 run on the laptop alone; 199–201 want the 1080p
projector; 206 and 213 the glass and the projector as two outputs (101).

**191. The golden frames match on the gate Mac.**
Headless: `tests/test_golden_frames.py::{test_every_golden_frame_is_drawn_byte_for_byte,test_every_factory_preset_has_every_state_recorded_and_nothing_else}`.
On the Mac the gates run on (`GL_RENDERER` "Apple M3 Max"), from
`hyperspace-python/`: `uv run python tools/golden_frames.py` (it uses a
throwaway home, never `~/Hyperspace`). Open a few PNGs under
`tests/golden/frames/png/` that `frames.json` names (party-trip, hands
present, `scene+hands+through`). *Pass:* "all 556 frames match their
goldens (Apple M3 Max, 4.1 Metal - 90.5)" (on a newer GL_VERSION, a note
naming both); the PNGs show the preset with the two synthetic hands (the
left open, the right a fist) over it, or bent through the effects in the
through states. *Fail:* a `MOVED …` list and a contact sheet
`docs/plans/assets/26-render-graph/golden-diff-all.png` (delete it after
looking; do not commit it). Likely causes: a render change that moved
pixels; a macOS or driver update (re-record with the reason, plan file
"How to re-record"); something in the frame reading the wall clock.

**192. Every factory preset against its golden, by eye, on the Mac.**
Headless: `tests/test_golden_frames.py::test_every_golden_frame_is_drawn_byte_for_byte`.
The goldens prove the pixels on the gate Mac's GL, not that they look
right; the new vertex path (edges and points as quads with depth, the
eye's matrix) has met Apple's shader compiler only headlessly. List each
preset's golden (output 1 alone, no hands) from `hyperspace-python/`:
`uv run python -c "import json; [print(g['preset'], 'tests/golden/frames/' + g['png']) for g in json.load(open('tests/golden/frames/frames.json'))['goldens'] if g['hands'] == 'absent' and g['state'] == 'solo']"`.
Launch with no sound playing, and load each of the 23 presets in turn
from the PRESETS list, its PNG open beside the render window. *Pass:*
each looks like its golden — the shape's size and place, its line
weight and dots, its faces and colours, its effects (the pose differs:
the golden is 8 frames in, with the LFOs at rest; the live shape keeps
turning). *Fail:* a preset blank, black or wrong where its golden is not
→ the scene's shaders on Apple's compiler (`LINE_VS`, `POINT_VS`,
`FACE_VS` in `render.py`; SYSTEM shows a render error and `stall.log` a
`render error`); strokes heavier or lighter than the golden → **Screen
strokes** ticked (198).

**193. The naming rule.**
Headless: `tests/test_params.py::{test_the_first_instance_keeps_todays_id_and_extras_carry_a_marker,test_every_node_param_today_reads_as_its_first_instance}`.
Read ENGINEERING §2, "Node instances: the naming rule"; then, with 212's
preset loaded, look at ROUTING's param list. *Pass:* the rule reads
clearly, and `fx.acid.2.mix` ("Acid 2 mix") reads right as the second
acid's mix. *Fail:* the owner prefers another marker — say so before a
preset of yours uses one (register row 169: after that it is a
migration).

**194. The per-node times on SYSTEM while an effect is toggled.**
Headless: `tests/test_golden_frames.py::{test_each_node_has_a_rolling_median_in_ms,test_no_timer_queries_means_a_note_and_the_same_pixels,test_the_gpu_lines_on_the_system_page}`, `tests/test_graph.py::{test_the_default_graph_for_one_default_view_is_todays_frame_in_order,test_the_timer_lists_the_graphs_nodes_and_drops_a_node_that_left}`.
Launch, load TRIP (F5), open SYSTEM. On the FX page untick **Effects**,
wait two seconds, tick it again. On LOOKBACK switch **Look-back** on and
off. On OUTPUT tick output 1's **through effects**, then untick it.
*Pass:* under the stall status "gpu per node, ms (median of the last
frames):" and one line each for `scene`, `cover`, `hands`, `history`,
`fx`, `capture`, `output.1`, a few ms or less and steady; `fx` falls
near 0 with the effects off and comes back within about a second (a
median of 60 frames); `history` moves with the look-back; `hands` rises
while the ghost hands show; with through on, `composite(scene+hands)` and
`fx(scene+hands)` join the list (0.00 until a hand shows with an effect
on) and leave it within a few frames of unticking. *Fail:* no lines (no
frame was timed); "gpu: no GPU timer queries on this context …" on the
Mac (the driver refused `GL_TIME_ELAPSED`); a line that stays after its
switch went → the graph not rebuilt (`Renderer._graph_for`) or the timer
not handed the graph's names.

**195. Every picture is what it was before the graph.**
Headless: `tests/test_golden_frames.py::test_every_golden_frame_is_drawn_byte_for_byte`, `tests/test_outputs.py` (whole), `tests/test_graph.py::test_a_pipeline_no_view_routes_to_this_frame_does_not_run`.
The party rig: the glass with hands over, the projector with hands
through, an effect on, the look-back on, the crossfader half down.
*Pass:* the hands over the effects on the glass, bent through them on
the projector, echoes behind the shape, both outputs dimmed alike; a
hand entering the box changes the projector's picture (through) and not
the glass's; closing the projector leaves the glass as it was. *Fail:* a
visible change from the last build on either output (a painted node
drawn through a texture; a pipeline run for the wrong output); an output
on its ground (`View.error` on the OUTPUT page names the pipeline).

**196. The shape sits where it always did; the eye on CAMERA.**
Headless: `tests/test_camera.py::{test_the_default_eye_lands_every_vertex_within_half_a_pixel_of_project_h,test_each_point_is_drawn_where_project_h_puts_it,test_the_eye_params_are_the_rooms_and_default_to_the_old_view}`.
Fresh launch; load LEGACY 6 then PLASMA HEART on the laptop and on the
projector; open CAMERA. *Pass:* LEGACY 6 looks exactly as before (same
size, same place, same dots); CAMERA has an **eye** section ("the
room's camera, not the preset's") with Eye field of view 47.6° and Eye
distance 3.78; a preset load never moves them. *Fail:* the shape offset
or another size at zoom 1 (the eye's defaults, the matrix order); dots a
pixel bigger (the point rounding).

**197. Zoom grows the shape in the world; the hands stay.**
Headless: `tests/test_camera.py::{test_zoom_scales_the_shape_about_the_world_origin_and_pan_moves_it,test_a_shape_through_the_eye_draws_without_error}`, `tests/test_stroke_space.py::test_world_space_scales_the_width_and_radius_by_the_zoom`.
Ghost hands on, a hand in the box, **Screen strokes** (VIEW) unticked as
it rests. Wheel the zoom from 0.3× to 5×; then load EMBER ORBIT and HEX
ENGINE. *Pass:* only the shape grows — the hands neither move nor
scale; a big zoom shows a deeper perspective (the near side grows
faster), and past about 4× the eye passes inside the shape with no
streak across the screen; the edges and dots grow and shrink with the
shape (world space); the zoomed-out fields' copies are spaced as before,
small dots and fine edges as on earlier builds. *Fail:* the hands scaling
with the zoom (a matrix reached the ghost); a stroke sweeping the screen
with the eye inside (the near-clip in `LINE_VS`); strokes not changing
with the zoom (198).

**198. Screen strokes: world space by default, the switch holds the weight.**
Headless: `tests/test_stroke_space.py::{test_the_default_is_world_space_a_preset_performance_switch,test_at_zoom_1_both_modes_draw_the_same_frame,test_the_switch_is_in_a_saved_preset_and_loads_back,test_world_space_scales_the_width_and_radius_by_the_zoom}`, `tests/test_camera.py::test_strokes_keep_their_weight_whatever_the_zoom`, `tests/test_desk_coverage.py::test_cannot_show_is_the_rule_by_group`.
Load PARTY FIELD, then HEX ENGINE (both zoomed out); compare with the
middle column of `docs/plans/assets/26-render-graph/a2b-moved.png`.
**Screen strokes** (VIEW, under the opacities) rests unticked. Wheel the
zoom (or the pad's right stick) from about 0.3× to 3×; tick **Screen
strokes** and wheel again; load LEGACY 6 (zoom 1) and flip the switch.
*Pass:* PARTY FIELD's edges and HEX ENGINE's red dots have their weight
from before plan 26 (small dots, fine edges); unticked, zooming in
fattens edges and dots and zooming out thins them, with the shape;
ticked, they keep one pixel size whatever the zoom; on LEGACY 6 the
switch changes nothing at all; the ghost hands never change weight with
it. *Fail:* strokes fixed while unticked (the `sz` line in `draw_scene`,
or a preset storing it on); dots changing size at zoom 1 (CAMERA's zoom
not exactly 1, or the zoom applied after the rounding); the switch
missing from a saved preset (its group is not `view`).

**199. A hand across the box pans as far as it did (`hands-orbit`).**
Headless: `tests/test_presets.py::test_each_orbit_axis_moves_its_camera_param_as_its_row_says`, `tests/test_camera.py::test_the_pan_range_keeps_a_routed_pan_as_far_as_it_was`.
The projector at 1920×1080; load HANDS ORBIT, left hand in the box; move
it from the box's left edge to its right, then from near to far. Then the
same with PARTY FIELD (it carries the same `hand:left.x/z →
camera.pan.x/y` push of 0.1). *Pass:* the shape's centre (PARTY FIELD's
whole field) travels about ±390 px — about a fifth of the projector's
width each way, as far as before plan 26 (±400 px) — sideways for x, up
and down for reach; level and centred, the shape is where the mouse left
it. *Fail:* the shape barely moves or flies off (`params.PAN_RANGE`);
moves the wrong way up and down (pan.y's sign).

**200. `hands-orbit` turns only the shape; the hands stay put.**
Headless: `tests/test_presets.py::test_each_orbit_axis_moves_its_camera_param_as_its_row_says`, `tests/test_camera.py::test_zoom_scales_the_shape_about_the_world_origin_and_pan_moves_it`, `tests/test_hands_node.py::test_the_ghost_settles_its_hands_once_through_the_shared_camera`.
Ghost hands on; load HANDS ORBIT; with both hands in the box, orbit
(right hand sideways), tip (fingers up), pan and zoom (left hand
sideways, reaching, raised). *Pass:* the shape orbits, tips, pans and
grows; the ghost hands stay exactly over where your hands are — they do
not turn, move or scale with the shape. *Fail:* the hands swinging with
the yaw or pitch, or moving with the pan or zoom (a camera param reached
`ghost.shared_camera`).

**201. A preset saved before plan 26 with a pan looks the same on the projector.** (copy)
Headless: `tests/test_camera.py::{test_a_preset_2_pan_in_px_is_read_in_world_units,test_a_saved_preset_says_its_pan_is_in_world_units_and_loads_as_saved,test_every_factory_pan_lands_inside_the_new_range,test_an_old_camera_module_loads_at_its_converted_pan}`.
The projector at 1080p; load PARTY MANDALA (its file stores pan.x = 190
px); open CAMERA. Then save it as your own preset, load another, and load
it back. Then any preset of yours saved before this build with the shape
off-centre. *Pass:* the mandala sits where it did on the projector (190
px right of centre); CAMERA shows Pan X `+0.59`; the saved file carries
`"units": {"camera.pan": "world"}` and loads to the same place with no
dirty dot; your older preset sits where it did on the projector (on the
laptop it sits nearer the centre: expected). *Fail:* the mandala off by
a factor (the reference screen, `geometry.PAN_REF_PX`); a re-loaded save
drifting (the key not written or not read).

**202. `hands.json` gains the calibration and keeps the old file.** (copy)
Headless: `tests/test_camera.py::{test_units_round_trip_through_hands_json,test_an_older_or_bad_units_entry_is_from_the_box,test_a_2_file_is_kept_beside_itself_before_the_first_save}`, `tests/test_hands.py::test_the_first_rewrite_of_an_old_file_keeps_a_backup`.
A copy whose `hands.json` was written by an earlier build (schema
`hyperspace.hands/2`); launch; HANDS page → **calibrate 20 s** and sweep.
*Pass:* `hands.json.bak-v2` appears beside it, identical to the old
file; the new file says `hyperspace.hands/3` with `"units": {"mm": null,
"origin": null, "tilt": 32.0}`; the ranges and the box are as swept; the
ghost hands are about where and as big as before (203). *Fail:* no
backup (the schema compare in `hands/core.py` `_keep`); the hands far
from where they were (203's causes).

**203. The hands are where the performer is (the calibration).**
Headless: `tests/test_hands_node.py::test_the_default_calibration_puts_the_hands_where_the_ghost_camera_did`, `tests/test_camera.py::test_the_shared_camera_frames_the_padded_box_like_the_ghost_camera`.
The laptop and the 1080p projector, real hands, ghost on; compare with
`docs/plans/assets/26-render-graph/a3-hands-moved.png` (before | after);
reach to each corner of the box. *Pass:* the ghost hands are the size
and in the place they were before plan 26, with a slightly stronger
perspective (fingers nearer the eye a touch bigger); reaching to the
box's edges reaches the picture's edges on the projector. *Fail:* hands
smaller by a third (the square fit came back); a hand leaving the frame
on a landscape screen (`ghost.CAL_ASPECT`); on a portrait or square
output leaving at the sides is expected (register row 187).

**204. Hands inside the scene are solid.** (copy)
Headless: `tests/test_hands_node.py::{test_hands_in_the_scene_are_solid_and_in_front_of_or_behind_the_shape,test_the_scene_holds_the_hands_so_the_effects_bend_them_and_the_history_keeps_them,test_the_guide_never_rides_the_scene}`.
HANDS-SOLID (above: its look-back is on and holds the hands), ghost on,
guide BESIDE; push a hand into the shape and through it, then hold it
still; drag Ghost opacity to 0.3, then to 0.
*Pass:* the hand is solid at any opacity above 0, and gone at exactly 0;
it moves with the acid's bend like the shape; it leaves echoes, and a
held hand saturates towards white as its echoes stack (expected); the
guide stays crisp and unbent beside it. *Fail:* the hand see-through at
the opacity (the alpha rule, register row 191); the guide bent by the
effect (the readout not split); doubled hand rims in the echoes with a
glass output also open (`composite(history)` built under in-scene
hands).

**205. A hand passes between the shape's edges.** (copy)
Headless: `tests/test_camera.py::{test_the_shapes_depth_is_its_nearest_visible_surface,test_the_scene_target_carries_a_depth_attachment}`, `tests/test_hands_node.py::test_hands_in_the_scene_are_solid_and_in_front_of_or_behind_the_shape`.
HANDS-SOLID (a wireframe at brightness 2), Effects unticked so nothing
bends; push one hand slowly into the shape from the front until it is
through. *Pass:* near edges draw over the hand, far ones are hidden by
it, and the line between them moves through the hand as it goes in;
faint far edges never cut a hole in it. *Fail:* the hand always on top
(the scene's depth not used: the hands drawn as a layer — the graph did
not land, check the strip's warning); faint edges cutting it
(`render.DEPTH_ALPHA` too low).

**206. The hands in the scene on the projector and a clean layer on the glass, at once.** (copy, glass and projector)
Headless: `tests/test_graph.py::test_the_hands_in_the_scene_are_its_first_geometry_and_a_glass_still_gets_the_layer`, `tests/test_hands_node.py::test_a_glass_without_the_scene_still_gets_the_hands_layer`.
Two outputs: the projector with **scene** and **hands** on, the glass
with **scene** off and **hands** on (OUTPUT page). Load HANDS-SOLID, an
effect on; move both hands through the shape. *Pass:* the projector shows
the hands inside the shape (in front of and behind its edges, bent with
it); the glass shows the same hands alone, clean, unbent, on black; the
OUTPUT page says "scene + hands: in the scene" for the projector.
*Fail:* the glass blank (the layer not drawn for an output without the
scene: `default_graph`'s `layered`); the hands twice on the projector (a
layer laid over a scene that holds them).

**207. A separate hands layer goes behind the shape (depth-aware).** (copy)
Headless: `tests/test_hands_node.py::{test_a_depth_aware_layer_goes_behind_the_shape,test_the_scenes_depth_resolves_out_of_the_multisampled_target}`, `tests/test_graph.py::test_depth_aware_wiring_hands_each_composite_and_output_the_scenes_depth`.
HANDS-DEPTH (above); one output with scene and hands on; move a hand
through the shape. *Pass:* the hand, drawn at its Ghost opacity, vanishes
behind near edges and bright faces and reappears in front of them, with
no flicker at the edges beyond a pixel; the OUTPUT page says "·
depth-aware". *Fail:* the hand cut where nothing is in front
(`render.LAYER_DEPTH_BIAS` too small, or the far-plane rim); never
hidden (the scene's depth not resolved).

**208. The OUTPUT switches still mean what they meant.**
Headless: `tests/test_outputs.py` (whole), `tests/test_graph.py::test_the_default_graph_has_a_pipeline_per_reachable_route_and_hands_only_when_shown`.
The party rig: the glass with hands over, the projector with hands
through, an effect on; switch the effect off, then take your hands out
of the box; then step through the eight states on one output (D2).
*Pass:* exactly as before the graph: through with no effect is hands
over, no hand shows nothing extra, each state as TESTING-GUIDE D2 lists.
*Fail:* hands drawn twice, or missing on one output (`Output.settle`,
`Fx.fallback`).

**209. The history can hold the hands.** (copy)
Headless: `tests/test_outputs.py::test_the_history_holds_what_it_is_wired_to_and_the_default_graph_wires_it_as_today`, `tests/test_render.py::test_the_default_graphs_history_holds_what_todays_does_never_the_dim`, `tests/test_graph.py::test_the_history_is_wired_to_the_scene_or_the_scene_with_the_hands`.
Load PARTY WAKE and wave a hand; then HANDS-LINES and wave again; pull the
crossfader half down. *Pass:* PARTY WAKE: no hand echoes (the default);
HANDS-LINES: the hand trails echoes; the LOOKBACK page says "history:
the scene" then "history: the scene · with the hands"; the crossfader
dims the picture evenly, echoes included, and back at full the echoes
are at once as bright as before (the dim is never captured). *Fail:*
hand echoes on PARTY WAKE (the default wiring changed); echoes that stay
dark after the crossfader comes back (the dim in the history).

**210. The hands' own line on SYSTEM.** (copy)
Headless: `tests/test_hands_node.py::test_the_hands_have_their_own_line_when_the_scene_draws_them`, `tests/test_graph_json.py::test_one_hands_node_feeding_a_scene_and_a_layer_is_timed_by_its_scene`.
SYSTEM page; load TRIP, then HANDS-LINES, a hand in the box. *Pass:*
TRIP: the lines as in 194 (`hands` is the layer; no `ghost` line);
HANDS-LINES: `ghost` then `scene`, and `readout` (the guide alone) in
place of `hands`. *Fail:* a dead `ghost 0.00` line on TRIP.

**211. A preset says its graph in data.** (copy)
Headless: `tests/test_graph_json.py::{test_the_proof_preset_loads_its_graph_from_a_scratch_library,test_an_unknown_node_kind_is_a_note_and_the_default_graph,test_no_factory_preset_carries_a_graph_and_each_loads_as_before,test_undoing_a_load_puts_the_graph_back_before_the_values}`, goldens `hands-lines|present|*`.
Copy `hands-lines.json` into `<home>/presets/`; ghost on; load
HANDS-LINES; then a party preset; then ⌘Z. Then edit the copy's
`hands-lines.json` so its first node reads `"kind": "teapot"`, load it,
save it, and open the file. *Pass:* HANDS-LINES shows the hands inside
the shape as wire hands, bent with the acid, leaving tracers, with a
clean strip and no warning; the party preset is its usual picture; ⌘Z
brings HANDS-LINES and its graph back. The teapot: the strip's warning
line says "graph: unknown node kind 'teapot' (this build knows effect,
hands, history); the default graph", the preset still loads (hands as a
layer), and after the save the teapot is still in the file. *Fail:* the
hands drawn as a layer over the shape on HANDS-LINES (the graph did not
land); a crash or a refused load on the teapot; the teapot gone after
the save.

**212. Two acids in one chain.** (copy)
Headless: `tests/test_graph_json.py::{test_a_second_acid_is_its_own_params_clock_and_place_in_the_chain,test_a_preset_says_two_acids_in_data_and_carries_the_seconds_values,test_two_acids_run_in_one_chain_on_one_program}`.
TWO-ACIDS (above); open the FX page and ROUTING; then load TRIP. *Pass:*
two chips, "Acid" and "Acid 2", each with its own strip and twist
(0.9 and 0.3); dragging one's slider moves only it; ROUTING lists
`fx.acid.2.*` as "Acid 2 …"; TRIP has one acid chip and no `fx.acid.2.*`.
*Fail:* one chip, both moving together, or the second acid's values on
the first.

**213. Two hands nodes: one in the scene, one over the glass.** (copy, glass and projector)
Headless: `tests/test_graph_json.py::{test_two_hands_nodes_one_in_the_scene_one_over_the_glass,test_a_second_hands_node_gets_its_own_session_params_and_state,test_a_second_hands_node_is_its_own_ghost_on_the_glass,test_a_second_hands_nodes_settings_survive_reopening_the_show}`.
The rig of 206; TWO-HANDS (above); SYSTEM open. On ROUTING (or by Learn
desk) switch **Ghost 2 hands** (`ghost.2.on`) on — off by default, like
every new switch — and set `ghost.2.mirror` on and `ghost.2.style` to
CAGE. Load TRIP, then TWO-HANDS again; save the show, quit, relaunch and
load TWO-HANDS.
*Pass:* the projector shows solid hands inside the shape; the glass shows
mirrored cage hands alone; SYSTEM lists `ghost`, `scene`, `hands.2`,
`readout` with times; TRIP takes the glass back to the first node's
layer and `hands.2` leaves SYSTEM; TWO-HANDS brings the mirror and the
cage back; after the relaunch they are still there and the show is
clean. *Fail:* the same hands on both outputs; the glass mirrored on the
projector too; a stale `hands.2` line; the cage lost after the relaunch
(the show's held-back `ghost.2.*`).

**214. Hands as lines.** (copy)
Headless: `tests/test_graph_json.py::test_hands_as_lines_draw_their_edges`, goldens `hands-lines|present|*`.
HANDS-LINES on the laptop and on the 1080p projector, each ghost style in
turn; one output with the scene off and hands on. *Pass:* wire hands in
the shape and as a wire layer on the scene-less output; the guide stays
solid; the shape's own lines unchanged. **Judge:** whether the hatching
of the capsules' triangles reads as "lines", or bone lines are wanted
(register row 201). *Fail:* the shape drawn in wireframe too (the
wireframe left on); hands invisible on a 2× screen (one-pixel lines:
registered).

**215. The wiring in words.** (copy)
Headless: `tests/test_graph_json.py::{test_the_wiring_in_words,test_the_output_pages_shows_line_says_the_wiring,test_the_lookback_page_says_what_the_history_holds}`, `tests/test_ui_shell.py::test_every_page_fits_the_control_window`.
OUTPUT and LOOKBACK with TRIP, then HANDS-LINES, then TWO-HANDS on the
rig of 206; hover each "shows:" line. *Pass:* TRIP: "shows:" as before,
LOOKBACK "history: the scene"; HANDS-LINES: "scene + hands: in the scene
as lines", LOOKBACK "history: the scene · with the hands"; TWO-HANDS: the
glass's line names "(2)"; the hover names the graph ("graph: …"). No page
scrolls. *Fail:* words that disagree with the picture.

**216. The recorded cloud in the scene, in the shape's world.** (copy)
Headless: `tests/test_cloud_node.py::{test_the_node_draws_the_fixtures_points_where_the_shared_camera_puts_them,test_a_point_in_front_of_the_shape_hides_it_and_one_behind_is_hidden,test_a_listed_cloud_is_the_scenes_first_geometry_and_none_listed_changes_nothing}`, goldens `cloud/scene`, `cloud/scene+hands`.
Copy `hyperspace-python/tests/fixtures/clouds/knot.npz` into
`<home>/clouds/` and add the recorded-cloud block
([`27-device-registry.md`](27-device-registry.md), "The block to
paste") to the copy's device list; load LEGACY 6. Wheel the mouse's zoom
and drag a pan; then CAMERA → eye, move Eye field of view; put it back.
*Pass:* a knot of dots (blue low, warm high) turning slowly about the
vertical, about the shape's size, threaded through the tesseract; where a
dot is nearer than an edge it hides the edge, where it is behind, the
edge draws over it; the knot neither tumbles with the shape nor moves
with the zoom or pan; the eye's field of view changes both together.
*Fail:* dots always on top (no depth); dots tumbling with the shape (the
shape's model matrix); nothing at all with SYSTEM's `scan` line
`connected` (the registry not handed to the renderer:
`renderer.cloud_source` in `app.main`).

**217. The cloud's look.** (copy)
Headless: `tests/test_cloud_node.py::{test_the_cloud_params_are_session_and_default_to_a_cloud_at_the_shapes_size,test_the_node_draws_the_fixtures_points_where_the_shared_camera_puts_them}`.
216's rig. Learn desk a knob each onto Cloud point size, Cloud scale and
Cloud brightness (from ROUTING's param list — there is no panel row),
and a button onto Cloud colours; then load another preset. *Pass:* size
grows the dots in whole pixels; scale grows the knot about the centre
(past about 3× it reaches the eye and the near dots vanish); brightness 0
turns the dots black (they still hide the shape behind them); colours
off: white dots; a preset load leaves all four as set. *Fail:* a load
resets them (not session); shimmering fractional sizes.

**218. No cloud, no change; the cloud's cost on SYSTEM.** (copy)
Headless: `tests/test_cloud_node.py::{test_a_missing_cloud_draws_nothing_and_raises_nothing,test_the_buffer_is_uploaded_only_when_the_frame_id_moves,test_the_per_node_timer_names_the_cloud,test_a_hot_reload_rebuilds_the_clouds_program_and_the_picture_is_the_same}`, `tests/test_golden_frames.py::test_every_golden_frame_is_drawn_byte_for_byte`.
216's entry with the file not yet copied in (or renamed away); launch;
SYSTEM open; copy the file in. Then remove the entry. *Pass:* before the
copy the picture is exactly as with no entry, the `scan` line says
`error: …` and the GPU lines show `cloud 0.00` above `scene`; within
about 10 s of the copy the knot appears with no relaunch and the `cloud`
line shows a small time; with the entry gone, no `cloud` line. *Fail:*
an error toast or a stall while the file is missing; a `cloud` line with
no entry.

## What no test covers

Only a person can settle these:
- the dream's look (9) and the default hand feel (16);
- the hand-to-picture delay (25): a target, not a measurement;
- the frame rate and tearing with two real screens (107): the tests pin
  which swap waits, not what the screens do;
- what macOS does to a window whose screen is unplugged mid-run (112);
- whether a lifted shape reads as a solid and the masked Heart as moved
  by the bass (113, 114): the tests pin the volume ratio and the
  edge-on share, not what a person sees;
- the FACES page's fit and `patterns.glsl` on the Mac (120, 121): the
  tests run with another machine's fonts and Mesa's compiler;
- the macro candidates (133–136): a listening session, by design;
- a real cloud client between two Macs (139, 140, 143): the tests write
  the folder directly;
- the real APC40 under the two-handed save, the relight and the fader
  pickup (148–153): the tests use fake ports, and the blink velocity and
  the whole-desk dark pass (about 100 messages a load) have never met an
  mk1;
- whether "dead" in the coverage report is what the owner calls dark
  (155): the rule reads the preset's bases, not what is on screen;
- every dance source's range and time constant, and the grab's
  thresholds, on real hands (158–163): all were tuned on synthetic
  hands;
- the palette fold by eye on a projector (166): the tests prove only
  that mix 0 is today's picture and that a raised mix changes it;
- every device of plan 27 on real hardware (168–190): the tests use a
  fake MIDI bus, stub devices and `pythonosc`'s client on localhost —
  never a real APC40 replugged under the registry (175), two real desks
  at once (176, 177), a DAW receiving a sink row or the hands through
  `hands-daw` (181–185), a phone app on Wi-Fi or the macOS firewall
  prompt (186–189), or a real editor's save while the config is watched
  (173);
- every factory preset by eye on the Mac (192): the goldens pin the
  bytes on the gate Mac's GL, not whether the picture looks right, and
  the new vertex path has met Apple's shader compiler only headlessly;
- real hands through the shared camera (200, 203–207, 213, 214): every
  hands picture the tests and goldens draw is one synthetic pose or a
  synthetic tape — the calibration's fit, a hand between the edges, the
  depth-aware boundary and the wire hands have never been seen with a
  real hand;
- the zoom's feel in world and in screen space (197, 198), an old
  preset's pan on the real 1080p projector (201), and the point cloud on
  a real screen (216–218).

