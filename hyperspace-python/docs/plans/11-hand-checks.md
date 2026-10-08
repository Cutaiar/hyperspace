# Hand checks

The checks only a person at the machine can run; none has been run yet.
Each gives the steps, what passes, what fails and where in the code a
failure points, and the headless tests that show what "right" looks
like. [`../TESTING-GUIDE.md`](../TESTING-GUIDE.md) is the plain-language
version, ordered by device, and the place to start; it cites these
numbers.

## Before you start

On `main` (`git pull`, `uv sync`); group R needs plan 22, on
`plan-22-integration` until it is merged. Before any launch of this build:

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
   119, 122–126, 128, 130–132, 137, 138; (copy) 86–89, 118, 127; FL
   Studio over IAC: 27, 28.
3. APC40: 31 first, then 10–12, 34–36, 39, 45, 49, 51, 54–56, 62, 69, 70,
   78, 82, 85, 117's cue knob; (copy) 133–136, the macro listening
   session (36, 56, 82, 85 on the copy).
4. (copy) 90, last on the copy.
5. Hand camera: 72 first, nobody else in view; then 13–21, 23–25, 29,
   42, 52, 66, 73, 75–77, 80, 100; APC40 in: 22, 65, 67, 74, 79, 110.
6. One projector: 26, 43, 61, 96.
7. Glass + projector as two outputs: 101 first, then 41, 98, 102–109,
   113 from the audience, 129; 111, 112 last.

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
`added note:0:64 → preset.home (…)`; eight
`added note:<k>:52 → preset.save_new (…)` (clip-stop);
`added key:… → edit.undo` / `edit.redo` / `preset.home` (plans 09, 11,
15 keys) per missing loop key; check 84's sixteen bank-pad lines; then
"bindings: updated <path> (N rows changed)". Earlier launches' changes
not repeated. SYSTEM: same, one line. ROUTING session, under "invariant
· both layers": X → `output.dim`, B11 → `preset.home`, G6·1–G6·8 →
`preset.save_new  hold`. Hand-edited crossfader, OVERDUB, clip-stop, pad
rows and keys on those chords kept. Relaunch: silent, no file times
move. Note: rows are added where **nothing uses the control**, so
deleted OVERDUB/clip-stop rows return; disable via `"enabled": false`.
A `bindings.json` freshly converted from an old `midi_map.json` gets
OVERDUB/clip-stop rows on second launch (which says so). *Fail:* no
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

**90. The home in git.** (last on the copy)
Headless: `tests/test_homegit.py tests/test_library.py::test_hide_rename_and_restore_each_ask_for_a_commit tests/test_config.py::test_library_git_is_off_by_default_and_a_switch`.
`git -C $HYPERSPACE_HOME rev-parse --show-toplevel`: "not a git
repository" (a folder above the copy: git refused by design, one note,
nothing written). Copy's `config.toml`: `[library]` `git = true`;
launch. *Pass:* SYSTEM library line ends "· git"; no `.git` yet. Save
(**as…**). *Pass:* `git -C $HYPERSPACE_HOME log --oneline`: one commit
"Hyperspace: the home as it was when git was switched on", body (`log
-1 --format=%b`) names your save; `.gitignore` present. Save changed,
rename, ×, × a factory preset, fill a slot: a commit each — "save
preset …", "rename preset … → …" ("show …: bank" in body or next
commit), "trash preset …", "hide preset …", "show …: bank". `git -C
$HYPERSPACE_HOME status --short` empty; `git -C $HYPERSPACE_HOME
ls-files | grep -c -e weights -e trash -e last_show -e windows.json -e
.bak-` prints 0; `git -C $HYPERSPACE_HOME remote` prints nothing.
`touch $HYPERSPACE_HOME/.git/index.lock`, save: instant, on disk,
"git: not committed (git add exited 128: …); saves are not affected";
save again: silent. `rm` lock, save: one commit, all three saves (`show
--stat HEAD`). Emptying trash: no commit. *Fail:* save waits →
`homegit.Committer.request`; `.git` before first save →
`app._open_homegit`. Keep off on the real home unless wanted (local
history only; sharing is `shared/` and `tools/shared_presets.py`).

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
reason → `app._open_hands`' note; no unmeasured line →
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
Headless: `tests/test_outputs.py::{test_through_bends_the_hands_with_the_shape,test_through_with_no_effect_on_is_hands_over,test_the_guide_is_never_distorted,test_the_history_never_holds_the_hands_in_any_state,test_two_pipelines_show_the_same_echoes} tests/test_ghost.py::test_the_readout_layer_is_the_guide_apart_from_the_hands`.
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
`light-realm-variation-1` (Möbius strip; if they are not in your
home, on the copy: `uv run python tools/shared_presets.py install
shared/dan-2026-10-04`). Music on. *Pass:* each still does what it was made for; note any
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
TRIP. Then one of your own from `shared/dan-2026-10-04` with faces on.
*Pass:* quiet music visibly moves the faces; loud music is legible, no
input stuck at an end (EMBER not black, SPIRAL not blown out); yours
(still at depth 1) shows the difference. Say whether to re-save your
sixteen depth-1 presets at 0.35. *Fail:* too still → raise
`routing.PATTERN_DEPTH` and regenerate (`uv run python -m
hyperspace.preset`); pinned → lower it.

**133. The macro candidates: MACRO PERFORMANCE.** (APC40, listening)
Headless: `tests/test_macro_candidates.py::{test_each_candidate_loads_with_no_note_and_keeps_every_row,test_turning_a_macro_moves_its_bases_and_scales_its_routes}`.
(copy) `uv run python tools/shared_presets.py install
shared/plan-22-macro-candidates`. PRESETS: load MACRO PERFORMANCE. A
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
- the macro candidates (133–136): a listening session, by design.

