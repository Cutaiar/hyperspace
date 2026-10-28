# Hand checks

The checks only a person at the machine can run; none has been run yet.
Each gives the steps, what passes, what fails and where in the code a
failure points, and the headless tests that show what "right" looks
like. [`../TESTING-GUIDE.md`](../TESTING-GUIDE.md) is the plain-language
version, ordered by device, and the place to start; it cites these
numbers. They run 1–393 (group AD (332–341) is plan 34's, feedback, on `plan-34-feedback` (PR #236), and runs with group AE); group Y (232–266, 272–276) is plan 28's (261–266 its N7,
272–276 its N9), 267–271, plan 30's N8 (the palette as compression), are at
the end of group X, and group Z (277–295) is two parts: 277–279 the
instanced field from `main`, renumbered from its 144–146 when main was
merged in, and 280–295 plan 31's (286–295 the APC40 page, on
`plan-31-a1`); group AA (296–316) is plan 32's, and 317 the two plans
together; group AC (318–331) is plan 33's, the free graph, on
`plan-33-free-graph`; group AE (342–352) is plan 35's, the free frame,
on `plan-34-feedback` (PR #236). Past 352: check 353 (group AF) is row 394's, group AG (354–369) is plan 36's, the WYSIWYG graph, and groups AH (370–376), AI (377–383) and AJ (384–393) are plans 37's (nodes as pictures, and the faces), 38's (hold the projector) and 39's (vision), run together and integrated on `plan-37-38-39-integration`.

## Before you start

On `main` (`git pull`, `uv sync`); group R needs plan 22, which is on
`main` (#151), and groups U (plan 24), W
(plan 27) and V (plan 26), on `plan-24-26-27-integration` until it is
merged. (V follows W in this file: plan 27's docs landed first.) Groups
X (plan 30) and Y (plan 28) need `plan-28-30-integration` until it is
merged. Group Z's 277–279 (the instanced field) are on `main`; its
plan 31 checks, 280–295, need `plan-31-integration`, and the APC40
checks 286–295 `plan-31-a1` (the page waits for Dylan's sign-off).
Group AA (plan 32) and check 317 need `plan-31-32-integration`, where
plans 31 and 32 land together, and `uv sync` for plan 32's four new
dependencies. Before
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
7. The wired Xbox 360 pad: 144–147, any time; then 171, 174, 179; with
   the Xbox pad over Bluetooth as well, 219 (copy).
   (copy) The device registry: 168 first, then 170, 173, 178, 190 on the
   laptop; 175 with the APC40 unplugged at launch; 176, 177 with a second
   MIDI controller; 169, 172, 180 with the hand camera; 181–185 with FL
   Studio over IAC; 186–189 with a phone on the same Wi-Fi.
8. Glass + projector as two outputs: 101 first, then 41, 98, 102–109,
   113 from the audience, 129; 111, 112 last.
9. The render graph (group V): 191 and 192 on the gate Mac first (the
   goldens, then every factory preset by eye), then 193, 194 and
   196–198 on the laptop; (copy) 211, 212, 215 on the laptop; 199–201 on the 1080p
   projector, 201 and 202 on the copy; with the hand camera (or the
   synthetic tape) 200, 203–205, 207, 209, 210, 214; 206 and 213 with the
   glass and the projector as two outputs (after 101), with 195 and 208; 216–218 (copy) with
   the recorded cloud (after 190).
10. Shader nodes (group X): 220, 221 and 230 on the laptop; (copy) 225,
    226, 228 and 229 on the laptop, 223 with the hand camera (or the
    synthetic tape); 222, 224, 227 and 231 (copy) with the glass and the
    projector as two outputs (after 101), 223 again there; N8's palette
    as compression: 267–269 on the projector, 270 on the laptop, 271
    (copy) on the laptop.
11. The node editor (group Y): 232–236, 240, 242, 243, 245–247, 250, 253
    and 255 on the laptop; (copy) 238, 239, 244, 257, 260 on the laptop; 237,
    241, 249 with the hand camera and music; 248, 256 with the APC40 and
    the hand camera, 258 (copy) with the APC40; 251 (copy) on the
    projector with the hand camera; 252 and 254 (copy) with the glass and
    the projector (after 101); 259 with two Macs on this build and a
    shared folder (with 139); N7's legible graph 261–264 on the laptop
    (the APC40 plugged in for 261), 265 (copy) with the hand camera and
    music, 266 with the APC40; N9's 272–276 on the laptop.

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
ghost bar rises, swell deepens with it (the same frame since plan 28; a
frame later before), nothing else moves
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

**56. (Retired 2026-10-09: the clip-stop save bar.)** The save is check 148; the hold on an empty pad is #158's. (APC40, copy)
Headless: `tests/test_midi.py::{test_a_hold_fires_once_at_the_hold_time_while_held,test_a_tap_fires_nothing,test_the_bar_is_one_control,test_the_bar_lights_while_held_and_the_new_slots_pad_blinks} tests/test_presets.py::{test_save_new_never_overwrites,test_save_new_fills_the_next_empty_slot_and_becomes_the_loaded_preset,test_save_new_on_a_full_bank_saves_to_the_list_and_says_so,test_the_new_slot_loads_from_the_preset_row,test_put_and_clear_slot_write_the_show_and_delete_no_file} tests/test_library.py::test_next_name_counts_on_from_a_trailing_number tests/test_ui_presets.py::test_a_slots_menu_offers_put_and_clear`.
What still applies — the slot menu: (g) Right-click F8 → **put preset
here…** (all presets, 12 rows then scroll) → NOITA: F8 NOITA, footer
"F8: NOITA", the other presets still listed; **clear slot** greyed when
empty; panel **save** still overwrites the loaded preset. (h) Right-click
a param → **Learn desk**, then hold an empty bank pad (#158's hold): it
saves, silently, and the learn stays armed. *Fail:* a taken slot or file
overwritten → `Project.next_empty`, `library.next_name`; the slot menu
missing → `ui_presets`.
*Historical (the clip-stop bar, retired):* steps (a)–(f) tapped and held
a clip-stop button to save a new preset (the row lit while held, the new
slot's pad blinked at 0.6 s, a full bank saved to the list, two fingers
made one preset, SHIFT stayed latched). That row no longer saves; do not
run them.

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
per output (`graph.default_graph`, `Output.settle`); echoes with hands
alone through effects → what the capture is wired to (`graph.Capture`,
`Wiring.history`).

**103. Hands over or through the effects; the guide never bent.**
Headless: `tests/test_outputs.py::{test_through_bends_the_hands_with_the_shape,test_through_with_no_effect_on_is_hands_over,test_the_guide_is_never_distorted,test_the_history_holds_what_it_is_wired_to_and_the_default_graph_wires_it_as_today,test_two_pipelines_show_the_same_echoes} tests/test_ghost.py::test_the_readout_layer_is_the_guide_apart_from_the_hands`.
Glass through on, projector off. F5 (TRIP), then F4 (WAKE). *Pass:*
glass hands bend and recolour with the shape, projector's clean; no
hand echoes or dream feed on either; same echoes on both. All effects
off: alike, glass block "through: no effect on". HANDS: Guide
BESIDE, then ON HAND, Tethers (**more ▸**) on: gauges, labels sharp, same on
both, never warped. *Fail:* hand echoes → `graph.default_graph` /
`graph.Capture` (the hands' layer is composited after the look-back
composite, before the first effect, and the capture takes the scene);
warped labels →
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
which plan 28 did not build); the turn feels 2:1 → the route's depth.

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
Then set the hue row to 170 → 230, then 200 → 200, and set Mode to
gradient. (Since plan 30 N8 the slice is hue / sat / val `from → to`,
not Centre and Width; checks 267–271.) *Pass:* at mix 0 the picture is
as it was; at the defaults (0 → 360) raising S2 changes nothing; at
170 → 230 raising S2 pulls every hue onto the blue-cyan slice; 200 → 200
is one colour; no seam anywhere; gradient paints brightness through the
grey ramp (a greyscale picture); a grey wireframe takes the slice's
`from` colour once Sat from is above 0.
*Fail:* a seam → the triangle in `palette.glsl`; the
picture changes at mix 0 → the chain's skip of a zero-mix pass; S2
refused → the fader is still the session's (153).

**167. A saved palette, and the palette's strip.** (copy)
Headless: `tests/test_fx_palette.py::test_a_saved_palette_is_an_fx_module_preset`, `tests/test_fx.py::test_the_palette_strip_fits_in_both_modes`.
Copy `tests/fixtures/palettes/fx/sunset.json` into the library's `fx/`.
FX page, open Palette: in compress mode the strip shows mode (a
picker), the "compress into" line, and hue, sat and val (each `from →
to` on one row); set Mode to gradient: it shows mode, anchors and one
row per anchor (hue, sat, val). Load **sunset** from the
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
Mac; 190 the laptop alone; 219 (B6, last in this group though numbered
after group V) both pads — the Xbox pad over Bluetooth and the wired
Afterglow.

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

**174. A second hands device is refused, and comes up when the first leaves; a second pad opens.** (copy)
Headless: `tests/test_devices.py::test_a_second_enabled_device_claiming_a_scheme_is_refused_with_a_note`, `::test_two_pads_open_each_under_its_role`.
Changed in plan 27 B6: a second pad is no longer refused (check 219 is
the two pads at work). On the list form, with the app running, add
`[[devices]] role = "leap2" kind = "hands"` and save; then add
`[[devices]] role = "pad2" kind = "gamepad"` and save. Then set the
`leap` entry's `enabled = false` and save. *Pass:* `leap2 · hands ·
error: feeds 'hand', which leap already feeds — not opened` and one note
saying the same; the first hands device works as before. `pad2 · gamepad
· lost · 22 sources` (or `connected · … · glfw 1` with a second pad
plugged in), no note; the first pad works as before. With `leap` off,
`leap2` reads `connected` (or `lost` with no camera) and the hands work
through it. *Fail:* `leap2` reads `connected` beside `leap` and the
hands fight → `devices.make`'s claimed schemes (`HandsDevice` must not
be `repeatable`); `pad2` is an `error:` line → `PadDevice.repeatable`,
`devices.primaries_of`; `leap2` stays refused → `DeviceRegistry.apply`'s
re-make.

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
tracker on) and Learn pad (a pad connected), as before. *Fail:* a scheme missing → its device's `feeds`,
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

**219. Two pads at once: the Xbox pad over Bluetooth and the wired Afterglow over USB.** (copy, both pads)
Headless: `tests/test_devices.py::{test_two_pads_open_each_under_its_role,test_a_role_listed_twice_is_refused_and_a_joystick_pins_a_pad,test_the_joystick_key_is_checked}`, `tests/test_gamepad.py::{test_two_pads_take_different_joysticks_in_list_order,test_an_unpinned_pad_whose_joystick_leaves_is_lost_then_takes_the_next_free,test_a_pinned_pad_waits_for_its_index,test_one_usb_reader_across_two_pads}`, `tests/test_pad_learn.py::{test_learn_on_a_second_pad_writes_its_qualified_rows,test_two_pads_drive_their_own_routes,test_the_camera_job_is_the_primary_pads_only}`, `tests/test_device_inputs.py::test_a_pre_run_bindings_json_means_the_first_pad_with_two_pads_listed`, `tests/test_routing.py::test_the_router_keeps_two_pads_apart`.
Plan 27 B6 (numbered after group V, which was numbered first; it sits
here with the other device checks). Pair the Xbox pad over Bluetooth; plug the Afterglow AX.1 into USB.
On the copy, write the two-pads block from
[`27-device-registry.md`](27-device-registry.md) ("The block to paste":
`pad`, then `p2`, both at the default `usb = true`) in place of the `pad` entry; save
(the app may run). SYSTEM → **devices**. Then: on the VIEW page
right-click Points → **Learn pad** and press A on the **Afterglow**;
right-click Field amp → **Learn pad** and squeeze the Afterglow's RT.
Move both pads' left sticks and press A on each. Unplug the Afterglow;
use the Xbox pad. Plug it back. Then turn the Xbox pad off and on.
*Pass:* two lines, `pad · gamepad · connected · 22 sources · glfw 0 ·
usb: lent to p2` and `p2 · gamepad · connected · 22 sources · usb: Afterglow Gamepad for
Xbox 360` (a second Bluetooth pad would read `glfw 1`: the indices
differ); the footer says `learned view.points ← pad A on p2 (into
bindings.json)`, `bindings.json` holds `pad@p2:A`, and ROUTING shows
`right trigger on p2 positions` on Field amp (its combo lists `axis@p2
…` after `axis …`). Both drive at once: the Xbox pad's A flips faces (as
ever) and its left stick orbits; the Afterglow's A flips points, its RT
rides Field amp, and its left stick does nothing (no camera job for a
second pad). Unplugged, `p2` reads `lost` within a frame and Field amp
lets go; the Xbox pad keeps working; replugged, `connected` again within
a few seconds and its rows work. The Xbox pad off: `pad` reads `lost · usb: lent to p2` (the reader
stays with `p2`), the Afterglow keeps working; on: `pad` is `connected
· glfw 0` again. Then **Learn p2** on a param with the Xbox pad off: a
press on the Afterglow completes it.
*Fail:* `p2` reads `lost` while the Xbox pad is `connected` →
`gamepad.Claims.lend` / `Pad._usb_state` (a pad reading GLFW must not
hold the reader); with the Xbox pad off, `pad` takes the Afterglow →
the lend is not sticky; both pads flip faces on A → the qualifier
(`Router.pad`'s `b.device != role`, `gamepad.learn_from(…, role=)`); the
Afterglow's stick orbits → `PadDevice.act`'s primary-only camera job;
the Xbox pad takes the Afterglow's line after a reconnect, or the two
read one joystick → `gamepad.Pad._find` / `Claims`; a learn on the
Afterglow writes `pad:A` → `PadDevice.learn`'s role.

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
191–194, 196 and 211, 212, 215 run on the laptop alone; 199–201 want the
1080p projector; 195, 206, 208 and 213 the glass and the projector as two
outputs (101).

**191. The golden frames match on the gate Mac.**
Headless: `tests/test_golden_frames.py::{test_every_golden_frame_is_drawn_byte_for_byte,test_every_factory_preset_has_every_state_recorded_and_nothing_else}`.
On the Mac the gates run on (`GL_RENDERER` "Apple M3 Max"), from
`hyperspace-python/`: `uv run python tools/golden_frames.py` (it uses a
throwaway home, never `~/Hyperspace`). Open a few PNGs under
`tests/golden/frames/png/` that `frames.json` names (party-trip, hands
present, `scene+hands+through`). *Pass:* "all 596 frames match their
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
`fx`, `capture`, `output.1`, a few ms or less and steady, and since plan
30 a line per effect that ran, just above `fx` (which itself reads 0.00:
the end runs no pass of its own, 220); the effects' lines go with the
effects off and come back within about a second (a median of 60
frames); `history` moves with the look-back; `hands` rises
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

## X. Plan 30: shader nodes

Plan 30 as built is [`30-shader-nodes.md`](30-shader-nodes.md). Every
effect is an image node; a preset's `graph` section may place one
`after` or `into` a node. No factory preset places an effect, so the
placement checks copy a fixture from `hyperspace-python/tests/fixtures/presets/`
into the copy's library — `palette-hands.json` (party-tracer, the
palette after the hands), `palette-glass.json` (party-acid, the palette
into output 2), `acid-scene.json` (party-mandala, a second acid after
the scene, the look-back on) — or a variant of one (**(copy)**; as for
group V, delete any `[library] path` line on the copy first, never copy
a fixture into the shared Drive folder). The variants, each saved under
a new name in `<home>/presets/` with its `"graph"` replaced:

- **palette-teapot.json** (from palette-hands) — `{"nodes": [{"kind":
  "effect", "file": "palette", "after": "teapot"}]}`;
- **palette-both.json** (from palette-hands) — `{"nodes": [{"kind":
  "effect", "file": "palette", "after": "hands", "into": "output.2"}]}`;
- **two-palettes.json** (from palette-glass) — `{"nodes": [{"kind":
  "effect", "file": "palette", "into": "output.1"}, {"kind": "effect",
  "file": "palette", "instance": 2, "into": "output.2"}]}`, and in
  `"values"` add `"fx.palette.2.on": true, "fx.palette.2.mix": 1.0,
  "fx.palette.2.hue_from": 0.0, "fx.palette.2.hue_to": 60.0` (the first
  palette keeps hue 170 → 230: blue-cyan; the second is orange-red).

The two-output checks use 101's rig: the glass is output 1 (the render
window) and the projector output 2, a **presenter** on its own context
— so `into: "output.2"` folds the projector, and a placement on the
hands reaches the projector through the presenter's hand-over (a
half-float texture no test has drawn on a real second window). The
hands checks need the hand camera or the synthetic tape (as in group V),
with **Ghost hands** ticked.

**220. SYSTEM times each effect that ran.**
Headless: `tests/test_graph_effects.py::test_the_system_page_times_each_effect_that_ran`, `tests/test_graph.py::test_the_timer_lists_the_graphs_nodes_and_drops_a_node_that_left`, `tests/test_golden_frames.py::test_each_node_has_a_rolling_median_in_ms`.
SYSTEM open; load ACID (F6); then on the FX page switch Kaleido on and
Acid off. *Pass:* under "gpu per node, ms", lines `acid`, `wobble`,
`deconverge` and `huecycle` before `fx`; the `fx` line itself reads
0.00 by design (the pipeline end runs no pass of its own — not "the
effects are free": their cost is the lines above it); after the switch,
`kaleido` appears and `acid` goes within a few frames; no line for an
effect that is off. The per-effect split moves from moment to moment on
the Mac's GPU (register row 218): judge that each line is there, not
its exact share. *Fail:* one `fx` line carrying the whole chain (the
run not built: `Renderer._graph_for` not passing the effects); a line
for every effect file (an off effect timed: `Effect.TIMED`).

**221. Switching effects on and off changes nothing but the picture.**
Headless: `tests/test_graph_effects.py::{test_an_off_effect_is_read_through_and_runs_no_pass,test_the_renderer_builds_the_run_from_the_stack_and_a_toggle_does_not_rebuild,test_the_run_draws_what_the_one_block_chain_drew}`, every golden.
ACID; on the FX page toggle chips quickly, drag one chip to another
place, then untick **Effects** (`fx.on`). *Pass:* each toggle is the
picture as on earlier builds (no flash, no black frame, no stall line
on SYSTEM); the drag reorders as before; bypassed, the frame is the
plain scene and SYSTEM shows no effect line. *Fail:* a black or stale
frame on a toggle (a texture read before it was written: `graph._spare`);
a stall on every toggle (the graph rebuilding: `_graph_for`'s key).

**222. Two outputs and the hands through still get their own chains.**
Headless: `tests/test_graph_effects.py::test_the_pipeline_end_still_paints_straight_into_a_frame_sized_output`, `tests/test_outputs.py` (whole), goldens `*|scene+hands+through`, `*|hands+through`.
101's rig: the projector with scene, hands and **through effects**, the
glass with scene off and hands and through on; ACID; a hand in the box;
SYSTEM open; then **Flip X** on the glass. *Pass:* the projector bends
the hands with the shape, the glass bends the hands alone, both as on
earlier builds; the flip mirrors the glass only; SYSTEM shows
`acid(scene+hands)` and `acid(hands)` lines. *Fail:* the glass showing
the projector's picture; an effect bending one pipeline twice; the flip
on both.

**223. The palette folds the hands and not the shape (palette-hands).** (copy)
Headless: `tests/test_graph_placement.py::{test_after_hands_folds_the_hands_layer_and_not_the_shape,test_a_presenter_lays_the_folded_hands_and_shows_the_folded_frame}`, goldens `palette-hands|present|*`.
Copy `palette-hands.json` into `<home>/presets/`. On the laptop first,
then on 101's rig; load PALETTE-HANDS, hands in the box, SYSTEM open.
*Pass:* the hands turn a blue-cyan slice (the ghost's pale colours read
grey-teal: **judge** whether hue 170 → 230 reads as meant) while
the 16-cell and its tracers keep their colours; the guide and labels are
not folded; on the rig the projector (a presenter) and the glass both
show the folded hands, at the ghost's opacity; SYSTEM shows a `palette`
line under `hands`; take the hands out: no palette line. *Fail:* the
whole frame blue (the palette ran in the chain: the placement lost on
load); a dark halo round the hands (the pass did not keep the ground
see-through: `opaque=0`); the hands folded on the glass but raw on the
projector (the presenter given `ghost.tex`, not the folded texture:
`Output.run`'s `hands_tex`); on an output set to **through**, see 224's
last cause (the output stood down: no effect of the run on).

**224. One output folds (palette-glass).** (copy, glass and projector)
Headless: `tests/test_graph_placement.py::{test_into_output_2_folds_one_output_only,test_a_presenter_lays_the_folded_hands_and_shows_the_folded_frame}`, golden `palette-glass|present|scene+hands+through`.
101's rig; copy `palette-glass.json` in and load PALETTE-GLASS. Then
on OUTPUT untick output 2's **scene** and **hands**; tick them again.
Then edit the copy's file to `"into": "output.1"` and load it again.
*Pass:* output 2 (the projector, a presenter) shows the acid folded to
blue-cyan while the glass keeps the full rainbow; output 2's "shows:"
line ends `· palette on this output only`; with output 2's scene and
hands off the OUTPUT page lists `dormant: palette into output.2 —
output 2 shows no picture this frame`, and ticking them brings the fold
back; with `output.1` the glass folds and the projector does not.
*Fail:* both outputs fold (the fold went into the pipeline, not the
output); output 2 black (no frame texture: the pipeline painted
direct); the projector raw where the test says folded (the presenter's
`Handoff.frame` not the folded texture, or the half-float texture
wrapped wrongly in the second context: register row 223). With output 2
on **through**, the fold gone or the hands on it unfolded: first check
that an effect of the chain is on and a hand drawn — a through output
with neither stands down; to its ground it folds nothing and says
`dormant: palette into output 2 — output 2 stands down this frame`, to
the scene it folds the scene but not the hands laid over it (row 223).

**225. A placement this build cannot honour is a note.** (copy)
Headless: `tests/test_graph_placement.py::{test_an_unknown_placement_is_a_note_and_the_default,test_both_keys_at_once_are_refused}`.
Make `palette-teapot.json` and `palette-both.json` (above); load each,
then save it (the preset strip's save) and open the file again.
*Pass:* the strip notes `graph: palette after 'teapot' — this build
places after scene, hands, hands.2 …, history, output.1 …, or an effect;
the default placement`, and for the other `graph: palette after 'hands'
and into 'output.2' at once — one of the two; the default placement`;
the palette folds the whole frame (it is back in the chain); the look
loads, the dot is clean, and after the save the file still says what you
wrote. *Fail:* the load refused; the whole graph dropped; the placement
lost on save.

**226. A dormant placement says so.** (copy)
Headless: `tests/test_graph_placement.py::test_a_placement_the_graph_lacks_is_dormant_and_said_in_words`.
PALETTE-HANDS; untick every output's **hands**; SYSTEM and OUTPUT open;
then tick one again. *Pass:* OUTPUT lists `dormant: palette after hands
— no hands layer this frame`; nothing is folded and SYSTEM has no
palette line; with a hands switch on the fold comes back. *Fail:* the
shape folds (the effect fell back into the chain).

**227. The echoes hold the bent scene (acid-scene).** (copy, projector)
Headless: `tests/test_graph_placement.py::test_after_scene_feeds_the_history_the_folded_picture`, goldens `acid-scene|present|*`.
Copy `acid-scene.json` in; on 101's rig load ACID-SCENE; LOOKBACK open.
*Pass:* the mandala heaves with the second acid on both outputs (the
projector through its presenter); the echoes trail the heaved picture,
not a straight one; LOOKBACK's line reads `history: the scene · acid 2
before the history`. *Fail:* the echoes unbent (the capture still reads
the scene).

**228. The placements in words.** (copy)
Headless: `tests/test_graph_placement.py::test_the_words_say_the_placements`, `tests/test_ui_shell.py::test_every_page_fits_the_control_window`.
Each fixture in turn; hover the OUTPUT page's "shows:" line. *Pass:*
the hover's last line names the placement: `graph: palette on the
hands`, `graph: palette on output 2 only`, `graph: acid ×2 · acid 2
before the history`; no page scrolls. *Fail:* words that disagree with
the picture.

**229. The FX page's placed chip.** (copy)
Headless: `tests/test_fx.py::{test_a_placed_effects_chip_says_where_it_sits_and_is_not_reorderable,test_the_page_fits_with_three_placed_effects,test_a_placed_effects_strip_says_its_place_wherever_it_is_drawn}`.
PALETTE-HANDS; FX page. Drag the palette's chip; drop another chip on
it. Open its strip and hover its title. Untick every output's
**hands** and hover the chip's name. Load TRIP. *Pass:* the palette's
chip sits in a second grid under the chain's, reading `Palette · after
hands`, readable from where you stand; the status line reads `nothing
in the chain · 1 placed` (party-tracer's chain is otherwise off); a drag
does nothing and a drop on it does nothing; its LED switches it and its
name opens its strip, whose title hover reads `palette.glsl · after
hands`; with the hands off the count goes and the hover says `dormant:
…`; on TRIP the palette is back in the chain's grid, last. *Fail:* the
palette in the chain's grid (the page did not get the preset's graph:
`Panel.graph_now`); a drag moving it or rewriting its order (`place`
not reaching `_chip` / `_drop`); the page scrolling.

**230. The faces target still bends the faces.**
Headless: `tests/test_render.py::{test_a_face_effect_changes_the_faces_and_nothing_else,test_a_frame_effect_runs_over_a_face_effect}`, `tests/test_fx.py::test_the_face_chain_borrows_the_frame_chains_programs`.
Any factory preset with Faces on (FACES, F2). FX page: open Warp, click
ONTO **faces**, switch it on; hover the ONTO faces chip. *Pass:* the picture
inside the faces warps and the frame does not; the hover ends "On the
faces it runs inside the shape's face drawing: the one shader run the
render graph does not show, and a placement in the preset's graph does
not move it."; the faces row lists Warp; SYSTEM has no `warp` line (its
time is inside `scene`). *Fail:* the frame warps (the target lost in the
run of effect nodes).

**231. Two palettes with different slices on two outputs.** (copy, glass and projector)
Headless: `tests/test_graph_placement.py::test_into_output_2_folds_one_output_only`, `tests/test_graph_json.py::test_a_second_acid_is_its_own_params_clock_and_place_in_the_chain` (neighbours only: no test loads this configuration, two placed instances of one file into two outputs).
101's rig; make `two-palettes.json` (above) and load TWO-PALETTES; FX
page, then ROUTING; drag Palette 2's hue turn. *Pass:* the glass folds to
blue-cyan, the projector to orange-red; the FX page shows two placed
chips, `Palette · into output 1` and `Palette 2 · into output 2`, each
with its own strip; dragging Palette 2's hue turn moves only the
projector's colours; ROUTING lists "Palette 2 …" settings; each
output's "shows:" line ends `· palette on this output only` / `·
palette 2 on this output only`. *Fail:* both outputs one colour (one
palette's values on both); a fold on the wrong output; one chip.

**267. The whole picture as shades of one red.** (projector)
Headless: `tests/test_palette.py::{test_a_red_slice_gives_only_reds,test_the_defaults_are_the_whole_cylinder_and_the_identity}`.
Any factory preset with plenty of colour (TRIP, F3); FX page, open
Palette, switch it on, raise its mix to 1 (nothing changes at the
defaults: hue 0 → 360, sat 0 → 1, val 0 → 1). Then set hue 350 → 10,
sat 0.6 → 1, val 0.3 → 1. *Pass:* on the projector the whole frame is
reds — dark reds where it was dark, bright reds where it was bright, a
pinker red where it was pale — with no green, blue or yellow anywhere
and no hard edge where one colour met another; the strip's line reads
`compress into: hue 350° → 10° · sat 0.60 → 1.00 · val 0.30 → 1.00`.
**Judge** whether that reads as "shades of a particular red". *Fail:*
colours outside red (the arc read the short way, or the hue map wrong:
`palette.glsl`); black areas still black (a clamp, not a map: the `mix`
calls); the picture changing at the defaults (the identity lost).

**268. A yellow slice and its derivations.** (projector)
Headless: `tests/test_palette.py::test_a_yellow_slice_spans_its_arc`.
As 267, then hue 45 → 75, sat 0.4 → 1, val 0.5 → 1; then widen it to
30 → 90, then 0 → 300. *Pass:* the frame is ambers through yellows to
lime-yellows — different parts of the picture different yellows
("derivations"), not one flat yellow — and widening the slice brings in
oranges and greens smoothly, with no seam; at 0 → 300 most of the wheel
is back. **Judge** the wide slices (over 180° the map slides from the
fold towards the identity: register row 292). *Fail:* one flat yellow
(the hue map collapsed: arc 0); a band of rainbow inside a red area
near 300 → 360 wider than a sliver (row 292's rough edge, larger than
it should be).

**269. A slice through red, and an inverted brightness.** (projector)
Headless: `tests/test_palette.py::{test_a_slice_through_red_wraps,test_an_inverted_val_range_turns_dark_to_bright}`.
As 267, then hue 300 → 60 (magentas through reds to oranges, through 0);
then hue back to 0 → 360 and val 1 → 0.2. *Pass:* with 300 → 60 the
frame is magenta, red and orange only — no greens, cyans or blues;
with val 1 → 0.2 the dark ground turns bright and the bright shape dim
(on an opaque window; on the overlay the clear ground stays clear).
*Fail:* 300 → 60 reading as the greens and blues between 60 and 300
(the arc taken the other way); the inversion ignored (the ends sorted).

**270. The mode is a picker; the strip reads as the slice.** (laptop)
Headless: `tests/test_palette.py::{test_mode_is_a_discrete_choice,test_the_strip_rows_are_the_slice,test_the_choice_form_is_parsed_and_refused_when_bad,test_the_gradient_mode_is_still_there}`, `tests/test_fx.py::test_the_palette_strip_fits_in_both_modes`.
FX page, open Palette. Click Mode; pick gradient, then compress. Hover
Mode, and right-click its label. Drag the hue row's small turn slider
round. *Pass:* Mode is a drop-down of two words, **compress** and
**gradient**, not a slider, and its label opens the param menu (Learn,
route…); compress shows the "compress into" line and three rows — hue,
sat, val — each two sliders with `→` between them, the hue row ending in
the turn, a thin bar of the slice's colours under it; turning moves the
whole slice round the wheel at the same width, wrapping past 360, and
the line adds `turned …°`; gradient shows the
anchors' rows instead; the page does not scroll in either. *Fail:* a
slider for Mode (the `@param choice` form not read: `fx.parse`); the
rows unpaired (`ui_fx.ROW_SUFFIXES`).

**271. An old preset with centre and width loads as the same look.** (copy)
Headless: `tests/test_palette.py::{test_centre_and_width_become_the_slice_s_ends,test_an_old_preset_loads_as_the_same_slice,test_an_old_fx_module_preset_is_read_as_the_slice}`, goldens `palette-hands|*`, `palette-glass|*`, `wired-outputs|*` (the fixtures converted, their frames unmoved).
On the copy, take `palette-glass.json` and, in its `"values"`, replace
`"fx.palette.hue_from": 170.0, "fx.palette.hue_to": 230.0` with the old
`"fx.palette.centre": 200.0, "fx.palette.width": 60.0`, and add a route
`{"source": "lane:0", "target": "fx.palette.centre", "op": "push",
"value": 0.5}`; save it as `old-glass.json` in `<home>/presets/`. Play
music. Load PALETTE-GLASS, then
OLD-GLASS; open the palette's strip; save OLD-GLASS and open the file.
*Pass:* the two look the same at rest (output 2 blue-cyan); no note on
the preset strip; the strip reads hue 170 → 230; with music the slice
swings round the wheel at the same 60° width (the route is on
`hue_turn`); the saved file has `hue_from` / `hue_to` and no `centre` /
`width`. Load any preset you saved before this build: no note. *Fail:* the old one
loads as the whole wheel or with "unknown id(s)" (`fx.palette_slice`
not on the load: `Presets.load_doc`).

## Y. Plan 28: the node editor

Plan 28 as built is [`28-node-editor.md`](28-node-editor.md). The
modulation runs in dependency order (no one-frame lag); modifiers live
in the preset; the GRAPH page (after ROUTING) draws and edits both
graphs. **No test drives a mouse on the canvas**: every drag, delete and
right-click below is unexercised by hand. No factory preset carries a
modifier, a wire or a layout, so those checks build their own on the
copy (**(copy)**: delete any `[library] path` line on the copy first,
never build a test patch in the shared Drive folder), or copy a fixture
from `hyperspace-python/tests/fixtures/` — `presets/hands-glass-only.json`
(the line hands in the scene, a second hands node wired to output 2's
hands), `presets/wired-outputs.json` (the palette wired into output 1,
a second acid into output 2), `modifiers/presets/mod-energy.json` (a
smooth on the right hand's energy times band 0 into acid mix). Two-output
checks use 101's rig: **the glass is output 1, the projector output 2**,
so `hands-glass-only`'s "glass" is the projector there; 252 says how to
aim it at the glass.

**Since N7 (checks 261–266) ROUTING draws no routes and no MODIFIERS
strip**: wherever a check above or below says "on ROUTING add a route"
or "on the MODIFIERS strip", do it on GRAPH — drag a cable from the
source onto the param's `mod` (or onto a collapsed box's stub and pick
it), right-click the canvas → modifier, click a modifier's box for its
editor (inputs, params, ×), click a route's wire for its row; or
right-click the param → Route a lane here…, which opens GRAPH. ROUTING's
desk, macros, session and sinks are as the checks say.

**232. The lag is gone on a real LFO-on-LFO patch.**
Headless: `tests/test_lfo.py::test_an_lfo_owning_another_lfos_depth_changes_its_output_the_same_frame`, `tests/test_routing.py::{test_every_factory_preset_lands_the_same_values_one_frame_earlier,test_a_macro_owned_by_a_hand_scales_a_lanes_push_the_same_frame}`, `tests/test_patch.py::test_a_param_the_pass_lands_is_applied_once_a_frame`.
TRIP (F5); LFO page. Set LFO 2's depth to 0.5; on GRAPH drop *LFO 1*'s
out stub on *LFO 2*'s in stub and pick its depth · mod, then click the
wire and set the row's op to push. Watch LFO 2's scope, then SYSTEM's frame
rate. Then, with the hand camera, raise and drop the left hand quickly
(it owns LFO 1's depth; LFO 1 drives the zoom). *Pass:* LFO 2's swing
breathes with LFO 1's wave, both ways, steady, no stutter; the zoom
pulse grows and dies with the hand, the same feel and range as before
(a frame earlier is not visible as such); the frame rate as before.
*Fail:* the scope stutters or doubles (a param applied twice: the frame
mark; an LFO stepped twice: `use_lfos` and `app.frame` both stepping);
it sticks after the hand leaves.

**233. A loop is refused in words; the rest of the preset runs.**
Headless: `tests/test_routing.py::test_a_cycle_without_a_delay_disables_its_last_cable_with_a_note`, `tests/test_patch.py::test_a_loop_of_modifiers_alone_keeps_its_last_input_off_with_a_note`.
Any preset; GRAPH: drop *LFO 1*'s out stub on *LFO 2* and pick its rate
· mod, then *LFO 2*'s out stub on *LFO 1* and pick its depth · mod (each
row's op push, from its wire). Open ROUTING for its head; back on GRAPH
expand both LFOs and hover the second cable. Delete the first route
(its cable, both ends expanded). *Pass:* a warning line under ROUTING's head, `loop: lfo:0 →
lfo.2.rate → lfo:1 → lfo.1.depth → lfo:0 needs a delay — lfo:1 →
lfo.1.depth is off until it has one`; LFO 1's depth does not move; every
other route runs; the cable's hover says "off: a loop needs a delay";
with the first route gone the note goes and LFO 2 drives LFO 1's depth.
A save writes both routes as they were. *Fail:* no note; the app
stutters (a loop run every frame); a row removed or switched off in the
file.

**234. A delay closes a loop.**
Headless: `tests/test_patch.py::{test_cycles_finds_every_loop_and_none_through_a_delay,test_a_loop_through_a_delay_runs_exactly_one_frame_late}`, `tests/test_modifiers.py::test_delay_is_one_frame_late`.
GRAPH: right-click → modifier ▸ **delay**, input `LFO 1` in its editor;
drop its out stub on *LFO 1*'s in stub and pick depth · mod (op push in
the wire's row): LFO 1 riding its own depth one frame late.
*Pass:* no loop note; LFO 1's scope swells and shrinks with itself,
smoothly. *Fail:* the loop note appears (the delay not seen as one); the
scope jumps between two shapes (two frames round the loop).

**235. Every LFO still runs with nothing routed.**
Headless: `tests/test_lfo.py::test_an_lfo_owning_another_lfos_depth_changes_its_output_the_same_frame`, `tests/test_app_boundary.py::{test_the_frame_runs_in_the_documented_order,test_main_hands_the_router_its_lfos}`.
A preset with no LFO route (TUMBLE); LFO page; tap a tempo, then ⇧B.
*Pass:* all four scopes move at their rates; ⇧B lands every synced LFO
on phase 0. *Fail:* a scope frozen (an LFO not a node of the pass) or
racing (stepped twice).

**236. Each modifier kind does what its name says.**
Headless: `tests/test_modifiers.py::{test_curve_is_linear_at_zero_bends_both_ways_and_inverts,test_scale_multiplies_offsets_and_clamps_unless_told_not_to,test_smooth_follows_with_its_attack_and_release,test_smooth_with_spring_on_overshoots_and_settles,test_combine_mul_and_cross,test_threshold_fires_once_on_the_rising_edge_and_holds,test_delay_is_one_frame_late}`.
Music playing; any preset; GRAPH. Add one modifier at a time
(right-click the canvas → modifier ▸ a kind), drop band 0 (the kick)
onto its in stub, then drop its out stub onto *shape*'s and pick
Brightness · mod; click the modifier for its editor; remove each (×
remove) before the next. *Pass:* **curve**: the response bends as
shape moves, invert flips it; **scale**: × 2 doubles it, clamp holds it
at full; **smooth**: a longer release makes the brightness fall slowly
after each kick; spring on (attack 0.2) overshoots and settles; a
**combine** of band 0 and band 3 by mul is darker than either, by cross
fades between them on balance; **threshold**: one flash per kick for the
hold; **delay**: the same as the raw route. The editor's bar (and the
node's "out" line) moves with each. *Fail:* the bar does not move (the input not live: its combo); a
threshold flashing all the time (on / off near the band's floor).

**237. A modifier whose input goes away lets its routes go; a removed one leaves them dormant.** (hand camera)
Headless: `tests/test_modifiers.py::{test_a_modifier_publishes_a_lane_a_route_can_source,test_a_modifier_whose_input_the_rig_lacks_is_dormant,test_the_mod_group_is_performance_and_its_params_come_and_go}`.
ACID (F6); GRAPH: a smooth from the picker, `right energy` dropped on
its in stub, its out stub dropped on *acid*'s and acid mix · mod picked.
Move the right hand, then take it out of the box. Then a second
modifier, a route from it, select it and × remove; ⌘Z. *Pass:* with the
hand out the smooth's editor says "dormant" and the acid mix returns to
its setting at once; back in the box, the smooth starts afresh with no
glide in; the removed modifier's route stays listed and does nothing,
and ⌘Z brings the modifier back and the route works again. *Fail:* the
mix sticks at its last value or drops to 0 (a dormant lane read as 0);
the route removed with the modifier (its wire stays, faint).

**238. A preset holds its modifiers; `bindings.json` never does.** (copy)
Headless: `tests/test_modifiers.py::{test_modifiers_live_in_the_preset_and_never_in_bindings_json,test_an_older_preset_without_the_key_loads_as_before}`.
Build two modifiers on GRAPH (the picker, then their editors); save as a new preset; load another, then
this one; open `<home>/bindings.json` and the preset's file. *Pass:* the
modifiers come back with their values; the file has a `modifiers` list
after `routes`, one entry a line, and no `mod.*` id in `values`;
`bindings.json` names no `mod`; a factory preset loads with no note and
no modifier. *Fail:* a `mod` entry in `bindings.json`; a dirty dot on a
factory preset just loaded.

**239. A template's modifier reaches every preset that uses it.** (copy)
Headless: `tests/test_modifiers.py::test_a_template_may_carry_modifiers_and_a_preset_overrides_by_id`.
Copy `tests/fixtures/modifiers/desk/mod-rig.json` into `<home>/desk/` and
`tests/fixtures/modifiers/presets/mod-templated.json` into
`<home>/presets/`; load MOD-TEMPLATED; save a copy under a new name and
give the copy's `mod.1` a longer release in its editor on GRAPH (click
its node); save. Edit the
template's smooth (its release) and load each preset again. *Pass:* both
show the template's modifiers; the copy keeps its own release; the
template's edit reaches the preset that does not override it; neither
saved file holds the template's entries it did not change. *Fail:* a
save writing the template's modifiers into the preset.

**240. Modifier edits are undo steps.**
Headless: `tests/test_modifiers.py::{test_adding_and_editing_a_modifier_are_undo_steps,test_picking_an_input_replaces_the_modifier_whole_as_one_undo_step}`.
Add a modifier, drag its release, pick another input; ⌘Z three times,
⇧⌘Z three times. *Pass:* each ⌘Z takes back one change, the last
removes the modifier; redo puts them back. *Fail:* the add not undoable;
one ⌘Z taking two changes.

**241. "Right hand energy, smoothed, times band 0, into acid mix" from the modifiers' editors.** (hand camera, music)
Headless: `tests/test_modifiers.py::{test_the_routing_page_builds_the_smoothed_energy_times_band_patch,test_the_modifiers_strip_draws_its_blocks_and_routing_points_to_graph}`.
ACID with its acid mix lowered to 0.2 (a base at the top hides a push);
GRAPH (since N7 the MODIFIERS strip is not on ROUTING): right-click the
canvas → modifier ▸ **smooth**; click it, and in its editor pick input
`hand R energy`, release 0.6; modifier ▸ **combine**, in its editor
inputs `mod 1 smooth` and `0 sub`, how mul; drop the combine's out stub
on *acid*'s in stub and pick acid mix · mod (op pos, depth 1: click the
wire to see its row). *Pass:* the acid comes in as the right hand moves
fast and pulses with the kick; it fades over about 0.6 s when the hand
stops; both editors' bars (and the nodes' "out" lines) move. *Fail:* the
combine reads 0 (an input combo not set); an input combo not offering
`mod 1` one frame after adding it.

**242. The GRAPH page shows one table.**
Headless: `tests/test_graphview.py::{test_every_route_is_one_cable_and_every_cable_one_route,test_macro_subs_are_cables_into_base_or_depth,test_the_routing_page_and_the_graph_page_show_one_table,test_the_page_draws_with_a_factory_preset_and_a_render_graph}`.
TRIP; GRAPH; **expand all**; then right-click a slider on another page
→ Route a lane here…; then **collapse all**. *Pass:* expanded, each
route is one solid cable into a param's round `mod` stub, each desk and
key row a faint cable into a square `base` stub; the head counts nodes,
wires, cables; the new route is selected on GRAPH and its row is first
in the pane; collapsed, every pair of boxes is one wire whose hover
counts its cables (one more on the new route's wire); SYSTEM shows
`graph page: … ms median (N nodes, M cables)`, near 1.3 ms collapsed.
*Fail:* a cable missing or doubled (`graphview.key` not moving); the
frame rate drops with the page open.

**243. Params sit under their render nodes.**
Headless: `tests/test_graphview.py::test_params_group_under_the_render_node_that_owns_them`.
ACID with the hands on; GRAPH, **expand all**, **patched only** off. *Pass:*
`view.*` on `shape`, `fx.acid.*` on `acid`, `dream.*` on `history`,
`camera.*` on `eye`, `tempo` and `master` on nodes of their own. *Fail:*
everything on group nodes (no render graph handed in yet).

**244. Layout and tidy.** (copy)
Headless: `tests/test_graphview.py::{test_layout_round_trips_through_the_preset_and_the_show,test_a_node_dropped_on_the_canvas_is_saved_in_its_home,test_auto_layout_gives_every_unplaced_node_a_column,test_a_tidy_is_one_undo_step,test_undoing_a_load_puts_the_earlier_layout_back}`.
A copy of TRIP saved under a new name; GRAPH. Drag `shape`; save; load
another preset and this one again. Drag an LFO. Press **tidy**, then ⌘Z,
⇧⌘Z. *Pass:* dragging `shape` dirties the preset and it comes back where
it was dropped; the preset file ends with a `layout` naming
`render:shape`; dragging the LFO dirties the show instead; tidy lays out
sources → LFOs → modifiers → macros → groups → render → outputs, and is
one undo step each way; no `NodeEditor.json` anywhere. *Fail:* a node
snapping back while dragged; a factory preset dirty on load.

**245. Hover and selection.**
Headless: `tests/test_graphview.py::test_a_route_depth_follows_its_macro_and_its_slider_without_a_rebuild`.
lfo-breathe; GRAPH; expand the route's two ends (their **+**). Hover a
route; click it; press **details beside**, then **details below**; click
an effect's node. *Pass:* the hover says from → to, the reading and the
depth (turning a depth-subscribing macro changes it); the click shows
the route's ROUTING row under the canvas (CONTROLS at 540 px); **details
beside** (there only while something is selected) moves it to a side
column and **details below** back; editing the depth there moves the
cable's thickness; an effect's node shows its FX strip. *Fail:* the
tooltip in the wrong place.

**246. Quit, ⌘R and a hot reload with GRAPH open.**
Headless: `tests/test_graphview.py::test_the_editor_context_is_made_once_kept_across_a_reload_and_destroyed_on_close`.
GRAPH open, zoomed in; save `hyperspace/ui_graph.py` unchanged (touch
it); then ⌘R; then quit. *Pass:* the page goes on drawing at its zoom;
⌘R and quit exit cleanly. *Fail:* a crash on quit (the editor context
destroyed after imgui); a second canvas.

**247. A cable dragged on the laptop screen at the control window's size.**
Headless: `tests/test_graph_edit.py::{test_connecting_a_source_to_a_mod_port_adds_the_route_learn_would,test_a_taken_param_asks_and_replace_owner_lands_the_cable,test_moving_a_cables_end_moves_the_route_and_its_depth_subs_follow,test_dropping_a_modifier_on_a_cable_inserts_it,test_cable_near_follows_the_widgets_curve}`.
The laptop alone, CONTROLS at 540 px; TRIP; GRAPH; expand the analyzer
and `shape` (their **+**) and turn **patched only** off. 1. Drag band 2's pin to `view.bright`'s
round `mod` stub. 2. Drag that cable's `mod` end (from the stub) onto
`view.speed`'s. 3. Drag a band onto a param a route already holds:
Keep, then again and Replace. 4. Right-click the canvas: **modifier ▸
smooth**; drag the new node over the band 2 cable and let go. 5. ⌘Z
four times. *Pass:* the cable appears on release and clicking it shows its
row in the pane; after 2 it ends on `view.speed`; Replace / Keep comes up; the smooth
sits between band 2 and `view.speed`; each ⌘Z takes one step back; a
drop on a wrong pin goes red with words and makes nothing. *Fail:* no
cable from a drag (`begin_create` not reached, or pins too small at this
zoom); the drop doing nothing (`pin_xy` stale, or the node patched).

**248. Learn from a port, with the APC40 and with a hand.** (APC40, hand camera)
Headless: `tests/test_graph_edit.py::{test_learn_from_a_port_lands_as_a_cable,test_a_hand_into_a_base_port_is_refused_in_words_and_a_pad_is_a_setter_row}`.
The rig with the APC40 and the Leap; GRAPH. 1. Right-click
`camera.zoom`'s `mod` stub → **Learn hand ▸ right**; lift the right
hand. 2. Right-click `view.bright`'s `mod` stub → **Learn desk**; turn a
track knob. 3. Drag a hand's pin onto a `base` stub; drag a macro onto a
`mod` stub. *Pass:* the menu is the slider's right-click menu; a cable
from `right y` lands on `camera.zoom` next frame; a faint setter cable
from the knob lands on `view.bright`'s `base` stub (a desk learn is
always a setter); step 3's heads read "a hand sets no base; aim at mod"
and "a macro sets a base or scales a depth; aim at base or a depth
stub". *Fail:* an empty menu; the cable only after the page is reopened.

**249. The hand-energy patch built on the canvas, felt with a real hand.** (hand camera, music)
Headless: `tests/test_graph_edit.py::{test_nodes_the_picker_adds_and_delete_removes,test_the_routing_page_and_the_graph_page_show_one_table,test_undoing_an_insert_is_one_step_the_modifier_gone_the_route_as_it_was}`.
ACID, its acid mix at 0.2, a copy saved under a new name (copy);
GRAPH. Right-click: add a **smooth** and a **combine**. Drag `right
energy` onto the smooth's `in` (or its in stub, picking `in`); the
smooth's out onto the combine's `in 1`, band 0 onto `in 2`; set **how**
mul in the combine's editor (click its node); the combine's out onto
`fx.acid.mix`'s `mod` (or *acid*'s stub). Save, load another preset, load
it back. *Pass:* the acid comes in with the fast hand and pulses with the
kick, fading over the release; the two modifiers and the route (click
the combine → acid wire) come back as they were, where they were laid
out. *Fail:* the combine reads 0 (an input unset); an input combo lacks
`mod 1`.

**250. Deleting on the canvas.**
Headless: `tests/test_graph_edit.py::{test_deleting_a_cable_removes_the_route_and_undo_puts_it_back,test_deleting_a_node_dispatches_by_kind}`.
lfo-breathe; GRAPH. 1. Select the route a macro's depth cable scales;
Delete; ⌘Z. 2. Select a key's faint cable; Delete. 3. Right-click a
labelled macro's node → **delete**; ⌘Z. 4. Select a modifier node
(add one) with a route on its lane; Delete. *Pass:* 1: the route and its
macro depth cable go together, ⌘Z brings both; 2: the cable stays and
the head says it is the session's (bindings.json); 3: the macro's label
and every subscriber go, the knob stays, ⌘Z puts them back; 4: the
node goes, its route stays, dormant. *Fail:* a modifier's delete removing
the routes on its lane.

**251. "Hands as lines through the acid with tracers", by dragging, on the projector.** (projector, hand camera, copy)
Headless: `tests/test_graph_wires.py::{test_hands_as_lines_through_the_acid_with_tracers_by_wires_alone,test_dragging_an_image_cable_on_the_canvas_edits_the_spec_and_dirties_the_preset,test_an_edit_is_one_undo_step}`.
ACID with the look-back on (`dream.on`), the projector as output 1;
GRAPH. 1. Drag from `ghost`'s geometry pin onto `scene`'s geometry
port. 2. Right-click `ghost` → **draw lines**. 3. Save as a new preset.
*Pass:* after 1 the hands are inside the scene, bent by the acid, with
tracers in the echoes; after 2 they are lines; the dot is dirty after
each and ⌘Z takes each back; the file's `graph` is `{"nodes":
[{"kind": "hands", "into": "scene", "draw": "lines"}]}`; reloaded it
looks like `tests/fixtures/presets/hands-lines.json`. *Fail:* the drag
does nothing (`CREATE` not reached); solid hands (`set_node` not
landing); no tracers (the look-back off).

**252. A hands node wired to the glass alone.** (glass, projector, hand camera, copy)
Headless: `tests/test_graph_wires.py::{test_a_wire_into_an_output_overrides_its_switch_and_an_unnamed_output_keeps_them,test_hands_2_wired_to_the_glass_alone}`, goldens `hands-glass-only|present|*`.
101's rig, both outputs scene + hands. Copy `hands-glass-only.json` into
`<home>/presets/` as `hands-glass-1.json` and change its wire to
`{"from": "hands.2", "to": "output.1.hands"}` (output 1 is the glass
here); load HANDS-GLASS-1; tick **Ghost hands 2** on HANDS. Untick the
projector's hands; then put the glass on through. *Pass:* the projector
shows the line hands in the scene and no solid hands; the glass the same
plus solid hands 2 laid over; OUTPUT's line for output 1 ends `· hands 2
over output 1`; unticking the projector's hands changes nothing on the
glass; on through the glass still shows solid hands 2 once. *Fail:*
solid hands on the projector while it shows its scene (the wire leaking
to an unnamed output — but an output with the scene off lays the graph's
one layer, hands 2, by A4's rule: that is not the wire); no solid hands
on the glass (`ghost.2.on` off); hands doubled or gone on through.

**253. A wrong cable is refused in words.** (copy for step 3)
Headless: `tests/test_graph_wires.py::{test_a_wire_of_the_wrong_type_or_into_a_missing_port_is_a_note_and_the_default,test_a_cycle_of_wires_is_refused}`.
GRAPH. 1. Drag `ghost` (geometry) onto `output.1`'s image port. 2. Drag
`acid` onto `palette`'s image port, then `palette` onto `acid`'s. 3. On
the copy, add `"wires": [{"from": "teapot", "to": "output.1.image"}]` to
a preset's `graph` and load it. *Pass:* 1: the cable goes red, "wire
ghost → output.1.image — ghost makes geometry, output.1.image takes a
picture"; 2: the second is red with "that makes a loop (…)"; 3: the
strip notes "graph: wire teapot → output.1.image — … teapot …; the
default wiring", the rest of the look lands, the dot clean. *Fail:* a
refused cable lands; one bad wire costing the whole graph.

**254. Two outputs, two pictures (wired-outputs).** (glass, projector, copy)
Headless: `tests/test_graph_wires.py::test_a_wired_output_shows_its_picture_and_no_other_output_moves`, goldens `wired-outputs|present|*`.
101's rig; the projector (output 2) on through. Copy `wired-outputs.json`
in and load WIRED-OUTPUTS; open SYSTEM and FX. *Pass:* the glass (output
1) shows the acid stack folded to blue-cyan; the projector (output 2)
the scene through the second acid alone — no wobble, deconverge or hue
cycle, no hands (through overridden); output 2's "shows:" reads `acid 2
by a wire`; SYSTEM lists `wire(output.2)`; FX shows the palette's placed
chip and acid 2's. *Fail:* both outputs fold (the palette in the chain);
the projector showing the full chain (no `wire(output.2)`).

**255. The picker and delete for render nodes.**
Headless: `tests/test_graph_wires.py::{test_the_picker_adds_an_effect_instance_with_its_params,test_an_edit_is_one_undo_step}`.
GRAPH; right-click the canvas → **effect ▸ acid**; select the new
`acid.2` node → Delete; ⌘Z. Try Delete on `output.1` and on `acid`.
Select a default render cable → Delete. *Pass:* `fx.acid.2.*` appears on
FX and ROUTING at defaults, off; Delete removes it, ⌘Z brings it back;
`output.1`, `acid` (instance 1) and the default cable are refused with
words on the head. *Fail:* the params stay after the delete.

**256. The APC40 as two nodes, SHIFT latched and released.** (APC40, hand camera)
Headless: `tests/test_graphview_devices.py::{test_the_apc40_is_two_nodes_and_each_row_hangs_off_its_layers_node,test_invariant_controls_are_ports_on_the_first_node_only,test_a_drag_from_the_shift_node_into_base_is_refused_whatever_the_latch,test_the_hands_node_groups_axes_pinches_grab_and_dance}`.
The rig with the APC40; TRIP; GRAPH, **patched only** off on both desk
nodes. Press SHIFT (it latches); press it again. Drag a port of *apc40
(SHIFT)* onto a `base` stub. With the Leap on, open the hands node's
folds. *Pass:* two nodes; *apc40* lists `invariant` first (SHIFT, the
bank pads, transport, TAP, the crossfader, MASTER), then track knobs,
device knobs, knobs, faders, clip grid, buttons; *apc40 (SHIFT)* has no
invariant control; the band strip's cables (`band.sel.*`) leave the
SHIFT node, the preset's knobs *apc40*; latched, *apc40 (SHIFT)* is
bright and *apc40*'s preset ports and cables faint, its invariant ports
unchanged; released, back; the drag is refused ("… on the SHIFT node is
the session's (bindings.json): map it on ROUTING"); the desk's rings and
LEDs behave exactly as before; the hands fold as axes, pinches, grab,
presence, dance. *Fail:* nothing changes on the latch (`refresh` not
reading `layer_of`); an invariant control on both nodes
(`is_invariant` lacking a row).

**257. A templated desk on the canvas.** (copy)
Headless: `tests/test_graphview_devices.py::{test_a_templated_desk_is_one_collapsed_node_whose_edits_write_overrides,test_a_factory_preset_draws_no_template_node}`.
Copy plan 24's fixtures (`tests/fixtures/desk-templates/desk/fixture-shape.json`
into `<home>/desk/`, `presets/templated.json` into `<home>/presets/`);
load TEMPLATED; GRAPH. 1. Find *template fixture shape*; press its
**+**. 2. Delete D1's cable. 3. Drag D3's template port onto
`view.speed`'s square `base` stub. 4. Save as a new preset and open the
file. *Pass:* collapsed, it lists 7 controls ("D1 → view.depth4" …) and
no cables; opened, 5 cables; D2 (`dream.mix`) and K3
(`view.pattern_mix`) leave *apc40*; after 2–3 the file has
`"desk_template": "fixture shape"` and a `desk` with a dark D1
(`cc:*:16`) and D3's (`cc:*:18`) override onto `view.speed`; the
template file unchanged. *Fail:* no template node; the template file
written.

**258. A SHIFT-layer cable is the session's; a preset-layer one the preset's; a missing role.** (APC40, copy)
Headless: `tests/test_graphview_devices.py::test_a_missing_role_is_a_grey_placeholder_with_dormant_cables`, `tests/test_graph_edit.py::test_deleting_a_cable_removes_the_route_and_undo_puts_it_back`.
The rig; GRAPH. 1. Select a `band.sel.*` cable on *apc40 (SHIFT)*;
Delete. 2. Select a preset knob's cable on *apc40*; Delete; ⌘Z. 3. On
the copy, unplug the pad (or add a route from `axis@p2:LX` with no
second pad). *Pass:* 1 is refused ("… is the session's (bindings.json):
edit it on ROUTING") and `bindings.json` is unchanged; 2 removes the row
from the preset (dirty dot) and ⌘Z puts it back; 3: the row hangs off a
grey node named by its role (`pad`, `p2`), faint; plugging the device in
lights it in place. *Fail:* a placeholder named after a scheme
(`axis@p2`).

**259. A patch saved on one Mac loads on the other through the shared library.** (two Macs, a shared folder)
Headless: `tests/test_modifiers.py::test_modifiers_live_in_the_preset_and_never_in_bindings_json`, `tests/test_graphview.py::test_layout_round_trips_through_the_preset_and_the_show`, `tests/test_graph_wires.py::test_a_wire_list_round_trips_and_d1_keys_read_as_wires`.
**Both Macs on this build** (`plan-28-30-integration`, or `main` once it
is merged), pointed at the same `[library] path` (as 139). On Mac A
build 249's patch, drag its nodes, add a wire (252's, to output 1), save
as a new preset. On Mac B load it; then change a modifier's release on
B and save; reload on A. *Pass:* B shows the same modifiers, routes,
wire and node positions (the look's nodes; the rig's positions are each
show's own) with no note; A sees B's change after the sync. **An older
build on either Mac** opens this preset as the default graph with a note
("graph: no key 'wires' …"), ignores its modifiers and positions with no
note, and **drops them if it saves**: never save it there (register row
277). *Fail:* a note on B on this build; positions or modifiers lost
between two Macs on this build.

**260. A preset from before this run loads with no note.** (copy)
Headless: `tests/test_modifiers.py::test_an_older_preset_without_the_key_loads_as_before`, `tests/test_graph_wires.py::{test_no_factory_preset_changes,test_the_fixtures_load_clean_through_a_scratch_library}`.
The copy's own presets, saved before this build; load each in turn,
open ROUTING and GRAPH, save one, and compare its file with the backup.
*Pass:* no note, no dirty dot; ROUTING's desk, macros and session as
before; GRAPH draws every route (expand all: one cable each); a save writes no `modifiers`, `layout` or `wires` key while
nobody added a modifier, dragged a node or wired a cable. *Fail:* a note on load; a dirty dot from a load; a new key in
a saved file.

**N7, a legible graph (2026-10-20), checks 261–266.** After the owner's first look: every node starts collapsed, one wire a
node pair while either end is collapsed, and GRAPH takes the routes and
the modifiers (ROUTING keeps its desk, macros, session and sinks). The
control window at its usual 960 × 900, CONTROLS at its usual width.

**261. The collapsed graph on party-trip reads at a glance.** (laptop, APC40)
Headless: `tests/test_graph_legible.py::{test_every_node_starts_collapsed_with_at_most_five_lines,test_the_apc40_to_one_shader_is_one_bundle_while_collapsed,test_the_page_draws_in_every_state}`.
Launch on party-trip (or load it), the APC40 plugged in; open GRAPH.
Read it from where you stand at the desk. Then SYSTEM: the `graph page:`
line. *Pass:* a column of boxes on the left (apc40, apc40 (SHIFT), pad,
leap, analyzer, key) and a handful of boxes to the right, each a title
and one to four short lines ("137 ports · 97 patched", "> L x 0.57");
from *apc40* one wire to *shape*, one to *fx*, one to *eye* — and, as
expected, one wire to every other node the desk maps into: *apc40* and
*apc40 (SHIFT)* each fan out one wire per target node, 19 between them
on party-trip, most into the group boxes (band, preset, master,
tempo …); the head reads
about "55 nodes · 64 wires · 238 cables"; the SYSTEM line about 1.3 ms
(N2's page: 2.3–2.8 ms). *Fail:* a node lists its ports before you
expand it (the collapse default); two wires between the same two boxes
on one layer (the bundling); the line over 2.3 ms (the caches). Since N9 (plan 28) the boxes stand in
the concern areas (check 272) and the head reads about "31 nodes (22
idle)": the idle macros, LFOs and off effects sit in lines (checks 273, 275).

**262. Expand the APC40 and the shape: the real cables.** (laptop, APC40)
Headless: `tests/test_graph_legible.py::{test_a_bundle_splits_into_its_cables_when_both_ends_expand,test_a_bundles_hover_and_side_pane_list_its_rows}`.
On 261's page hover the apc40 → shape wire, then click it; then click
*apc40*'s **+**, then *shape*'s **+**; then **collapse all**. *Pass:*
the hover says "24 cables: …" with ten of them and "+ 14 more"; the
click lists its cables in the pane under the canvas — these are desk
rows, so as text lines ("<control> → <param> <op>"; a bundle's routes
are ROUTING's rows, as on the analyzer → shape wire); with only *apc40* expanded it is still one wire into *shape*;
with both expanded each patched control has its own cable into the
shape's ports, and **expand all**'s chip has turned into **collapse
all**, which brings back the boxes. *Fail:* cables appear while one end
is collapsed; a wire ends in mid-air (a stub not drawn); the pane is
empty for a route bundle.

**263. A drag onto a collapsed node lands a route.** (laptop)
Headless: `tests/test_graph_legible.py::test_a_drag_onto_a_collapsed_node_offers_its_ports_and_lands_through_edit`.
Expand *analyzer* only. Drag from band 3's dot onto the little dot at
the left of *shape*'s title (its in stub); hold, read the tooltip, let
go, pick a param you know (Brightness · mod, as the menu writes it). Then right-click *shape*:
**learn ▸** a group ▸ a param ▸ Learn hand ▸ right, and move the hand.
*Pass:* the tooltip says "let go: pick one of shape's ports"; the menu
lists only what band 3 can drive (no `base` stubs); the pick makes the
route (the analyzer → shape wire's hover counts one cable more — it is
already at its full thickness — and Brightness pulses with band 3), ⌘Z takes it back; the Learn lands a hand route without expanding
*shape*. *Fail:* no menu (the drop not seen); a `base` entry offered; a
second route on a taken param without the Replace / Keep question.

**264. Tidy says what it did; the details chip.** (laptop)
Headless: `tests/test_graph_legible.py::{test_tidy_collapses_all_relays_and_says_what_it_did,test_beside_shows_only_with_a_selection}`.
On a fresh page click **tidy**. Then expand two nodes, drag one across
the canvas, click **tidy** again. Then click a wire, and the
**details beside** chip, and **details below**. *Pass:* the first tidy
says "already tidy"; the second collapses both, puts every box back in
its column, frames the canvas on them and says "laid out 55 nodes,
every one collapsed"; ⌘Z puts the dragged box back; no details chip
until something is selected, then "details beside" moves the pane to a
column and "details below" back under the canvas. *Fail:* tidy leaves a
node expanded or says nothing; the chip with nothing selected. Since N9
the second tidy puts each box back in its area and says "laid out 31
nodes in 6 areas, every one collapsed · 22 idle off the canvas" (check
274).

**265. Energy → smooth → combine → acid mix, from GRAPH alone, with a hand.** (hand camera, laptop; copy)
Headless: `tests/test_graph_legible.py::test_the_smoothed_energy_times_band_patch_from_graph_alone`.
On the copy, a preset with the acid in its chain (or party-trip with
acid on). On GRAPH only: right-click the canvas → modifier ▸ smooth, then
modifier ▸ combine; expand *leap*, drag *right energy* onto the smooth's
in stub, pick its input; drag the smooth's out onto the combine's stub,
pick in 1; expand *analyzer*, drag band 0 onto the combine, pick in 2;
click the combine: in the side pane set **how** to mul; drag the
combine's out onto *acid*'s stub, pick acid mix · mod. Dance with the
right hand to music. *Pass:* nothing needed ROUTING; the combine's
pane shows its inputs, its params and its live bar; the acid mix swells
with the hand's energy, smoothed, and pumps with the bass; the hand
leaves and the mix settles back. *Fail:* a step that cannot be done on
GRAPH; the pane cut off at the column's width.

**266. ROUTING points to GRAPH; its desk section as before.** (APC40)
Headless: `tests/test_graph_legible.py::test_routing_no_longer_draws_routes_or_modifiers_but_their_functions_stay`, `tests/test_ui_routing.py::test_the_routing_page_is_one_page_over_the_loaded_preset`.
Open ROUTING with the APC40 plugged in; click a desk control on the
diagram; right-click a desk line → Learn; move a knob. Click the line
"routes and modifiers: the GRAPH page". Then right-click any slider
elsewhere → Route a lane here…. *Pass:* no route rows and no MODIFIERS
strip on ROUTING; the desk section, the macros, the session and the
sinks exactly as before (a click frames the control's line, Learn lands
a desk row, the filter filters them); the pointer opens GRAPH; "Route a
lane here…" opens GRAPH with the new route there. *Fail:* any change in
the desk section's lines or Learn; the pointer does nothing.

### The graph by concern (plan 28, N9)

After the owner's second look (2026-10-20): the canvas in titled areas —
controllers, audio (other under it), modulation, geometry, shaders —
and a node with nothing in and nothing out (an unused macro, an
unpatched LFO, a group no cable reaches, a lost device) off the canvas,
in one idle line an area. The control window at its usual 960 × 900.

**272. The three concern areas at a glance on party-trip.** (laptop, APC40)
Headless: `tests/test_graph_areas.py::{test_every_node_has_one_area_and_the_three_concerns_are_separate,test_auto_layout_stacks_each_area_and_keeps_saved_positions,test_area_titles_draw}`.
Launch on party-trip, open GRAPH, click **tidy** once if anything was
moved. Read the canvas, then pan right along it; zoom out about four
times with the wheel. *Pass:* faint titles over the columns, left to
right: CONTROLLERS, AUDIO (OTHER under it), MODULATION, GEOMETRY,
SHADERS; the analyzer, *band*, *tempo*, *master*, *audio* and *scene*
boxes under AUDIO and nowhere else; *shape*, *ghost*, *eye*, *hands*,
*scene* and *cover* under GEOMETRY; *history*, the effects and the
outputs under SHADERS; every wire leaves a box on its right and lands on
a box further right — none loops back, but inside SHADERS the one wire
a pipeline from a row's end down to the next row's start (the chain wraps
in rows of four); an LFO into a modifier runs right too. *Fail:* a band or tempo box among
the geometry or the shaders (`graphview.AREA`); a wire running back to
the left (`_columns`); no titles (`ui_graph._titles`).

**273. An idle macro appears when patched and goes when unpatched.** (laptop)
Headless: `tests/test_graph_areas.py::{test_an_idle_macro_is_not_drawn_and_a_connected_one_is,test_the_idle_macros_line_expands_to_show_them_and_the_picker_still_offers_them}`.
On 272's page read the small box under MODULATION; click its **+**, then
**−**. Click **+** again and drag *Macro 3*'s out dot onto *shape*'s in
stub, pick Brightness · base; click **−**. Then expand *Macro 3* and
*shape*, click the new cable and press Delete. Right-click the canvas:
**macro ▸**. *Pass:* the box says "8 idle macros · 3 idle LFOs"; **+**
shows them under it, **−** takes them off; patched, *Macro 3* is a box of
its own above the line with one wire into *shape*, and the line says "7
idle macros · 3 idle LFOs"; after the Delete it is back in the line; the
picker lists macro.1–macro.8. *Fail:* a macro with no wire drawn with the
line shut (`is_idle`); a patched macro still hidden; the picker missing
the idle macros.

**274. Tidy lays out into the areas.** (laptop)
Headless: `tests/test_graph_areas.py::test_tidy_relays_into_areas_and_says_so`.
Drag *shape* far down the canvas, open MODULATION's idle line, expand
*apc40*; click **tidy**; then ⌘Z. *Pass:* every box collapsed, the idle
line shut, *shape* back under GEOMETRY, the canvas framed on it all; the
head says "laid out 31 nodes in 6 areas, every one collapsed · 22 idle
off the canvas" (numbers as your rig has them); ⌘Z puts *shape* where
you dropped it. *Fail:* the idle macros left drawn; a box outside its
area; tidy says nothing.

**275. The off effects are one line; the chain reads through them.** (laptop)
Headless: `tests/test_graph_areas.py::test_an_off_effect_with_no_cable_is_idle_and_a_through_wire_spans_it`.
On party-trip open GRAPH and click **SHADERS**. Hover the faint red wire
from *history*; press Delete on it. Then on the FX page switch *warp* on
and come back; switch it off. Then click the SHADERS line's **+**.
*Pass:* only the effects that are on (plasma, kaleido, zoomblur,
huecycle) are boxes; the line under them says "9 off effects"; the faint
wire's hover names the effects it runs over, and Delete says "a through
wire stands for off effects …" and deletes nothing; *warp* switched on
is a box in the chain next frame, off it is in the line again; **+**
draws every effect in its place and the faint wires go. *Fail:* an
effect a pad toggles hidden (a desk row is a cable); the chain broken
with no faint wire (`throughs`); warp not appearing (`graphview.key`).

**276. Five chips frame the areas; the shaders in rows of four.** (laptop)
Headless: `tests/test_graph_areas.py::{test_the_area_chips_and_a_title_click_frame_an_area,test_the_shader_chain_wraps_in_rows_of_four}`.
On party-trip, GRAPH: click **tidy**, then each chip in turn —
**CONTROLLERS**, **AUDIO**, **MODULATION**, **GEOMETRY**, **SHADERS** —
then click the faint GEOMETRY title on the canvas. Then open the
SHADERS line (**+**) and click **SHADERS** again. *Pass:* after tidy the
whole canvas fits with its titles readable (CTRL · AUDIO · MOD ·
GEOMETRY · SHADERS); each chip brings that area's boxes to fill the
canvas, close enough to read their titles; the title click does the
same; the shaders sit in four columns, each row left to right, with one
wire per pipeline from a row's end back to the next row's start.
*Fail:* a chip that frames nothing or the wrong boxes; the shaders in one
long row (`SHADER_ROW`).

## Z. The instanced field (from `main`); plan 31: the step sequencer

### The instanced field: thousands of copies, 3D lattices, Fit (from `main`)

VIEW page, the 120-cell (or any heavy shape), faces on. The tests draw
on Mesa's software rasteriser, so they pin what is drawn, not how fast.

**277. Four thousand copies hold the frame rate.**
Headless: `tests/test_render.py::{test_thousands_of_copies_upload_one,test_a_zoomed_in_field_draws_only_what_it_shows}`.
Instances to the top (4096), GRID, then CUBIC; scroll out until the
whole field shows, faces on, then off. *Pass:* the SYSTEM page's frame
rate stays near the screen's (60) with lines and points, and usable with
faces; zoomed back in, it is back at full speed. *Fail:* the rate drops
with the count at a fixed zoom → the instanced draws (`render.draw_scene`,
`field.cull`); only with faces → the pattern's per-fragment cost (try
FLAT).

**278. Fit leaves no copy cut by the edge.**
Headless: `tests/test_render.py::test_fit_leaves_no_copy_cut_by_the_edge tests/test_field.py`.
12 copies, GRID, Fit on, in the window and fullscreen on the projector;
then 7, 19 on HEX and 200 on FCC. Scroll in and out, right-drag. *Pass:*
12 is four by three, evenly spaced, nothing touching an edge; zooming in
jumps between whole copies (never half a shape at the edge) and the drag
moves a copy at a time; a lattice stays whole and centred. *Fail:* a
shape cut → `field._field_snapped` / `field._framed` (and `PAD_PX` for a
point poking out).

**279. The lattices read as 3D.**
Headless: `tests/test_field.py::{test_every_lattice_has_its_neighbours_one_cell_apart,test_a_lattice_is_drawn_far_to_near_through_its_perspective}`.
300 copies of the tesseract; each 3D layout in turn; orbit the camera
with the mouse; Field depth 0, 0.5, 1; a field motion on. *Pass:* the
field turns as one solid, near copies larger and brighter and drawn over
far ones; depth 0 flattens the sizes; motions swing the copies in depth
too. Say whether the default depth (0.5) and the far fade (to a quarter)
are right. *Fail:* far copies drawn over near ones → the sort in
`field._field_3d`.

### Plan 31: the step sequencer

Plan 31 as built is [`31-step-sequencer.md`](31-step-sequencer.md): the
LFOs a bank of up to 16 by stable id, AHDSR envelopes (`env:`), a step
sequencer of five lanes × eight steps read off the clock (`seq:`), the
SEQ page, GRAPH's envelope and sequencer nodes, `hyperspace.preset/3`
and the factory `seq-demo`. On `plan-31-integration`. The control
window at its usual 960 × 900. `seq-demo` loads stopped: press **run**
on the SEQ page (the transport is never in a preset). Checks 286–295 are
the APC40 page and need **`plan-31-a1`** (`git checkout plan-31-a1`),
which waits for Dylan's sign-off: run them with him, on the copy.

**280. The LFO page at 7 and at 16 LFOs.** (laptop)
Headless: `tests/test_ui_lfo.py::{test_the_page_draws_n_strips_and_gaps,test_four_lfos_do_not_fold_and_still_fit,test_sixteen_lfos_scroll_and_one_is_open,test_add_is_refused_at_the_cap,test_add_and_remove_through_the_chips_are_undoable}`, `tests/test_modbank.py::test_removing_lfo_2_keeps_lfo_3_on_lfo_2`.
On the copy, load LFO BREATHE; open LFO. Click **+ lfo** three times (7
LFOs); click a folded strip's chevron; then **×** on LFO 2; then ⌘Z.
Then click **+ lfo** until it greys (16) and hover it; scroll the page;
watch SYSTEM's frame time. *Pass:* at four nothing folds and the page is
as before; from five, every strip but one is one line (thumbnail, name,
a live bar, a chevron) and the open one has the full scope; the
chevron opens that strip and folds the last; × removes LFO 2 and the
others keep their numbers (LFO 3 still "LFO 3"), its routes still on
ROUTING but dormant; ⌘Z brings LFO 2 back with its knobs; at 16 the chip
is grey with "16 LFOs, the most there can be…" on hover, the page
scrolls, the frame time is near what it was at four, and legible at
arm's length. *Fail:* the numbers shuffle after a ×
(`modbank.Bank.remove`); two strips open; a hitch at 16 (`ui_lfo`'s
scopes).

**281. The SEQ page reads from a distance.** (laptop)
Headless: `tests/test_ui_seq.py::{test_the_default_page_fits_the_control_window,test_the_playhead_column_follows_the_sequencer,test_columns_past_length_are_inert,test_the_cells_use_the_apc_palette,test_the_lane_selection_opens_its_envelope}`.
Load `seq-demo`, open SEQ, press **run**. Stand two metres back. Then
click step number **6** over the grid; click lane 2's **M**; click lane
3's number; click a cell; ⌘Z. *Pass:* no scroll at 960 × 900; green
cells for the kick (1, 5), snare (3, 7) and hats (every step) are
told apart from the dark ones at distance; the playhead's red-framed
column marches in time and a lit cell under it is yellow, readable
against green; after length 6, columns 7–8 are dim and a click on them
does nothing; muted lane 2's cells are red; clicking lane 3's number
opens env 3's strip; the click toggles and ⌘Z undoes it; the envelope
strips' small text (stage, out) is readable at least up close. *Fail:*
yellow and green hard to tell apart at distance (`ui_seq.YELLOW`,
`GREEN`); the page scrolls; a dim column toggles.

**282. `seq-demo` feels tight at 120–175 BPM.** (laptop, music, a projector helps)
Headless: `tests/test_plan31_wiring.py::{test_a_step_fires_its_envelope_at_the_steps_exact_time_and_it_comes_back,test_seq_demo_is_the_pattern_and_plays_once_play_is_pressed,test_a_step_releases_a_gate_mode_envelope_after_half_a_step}`, `tests/test_sequencer.py::test_each_step_fires_exactly_once_at_irregular_dt`.
Play a track at about 120 BPM; tap the tempo in (TAP or the LFO page);
⇧B on a downbeat; load `seq-demo`, press **run**. Then a track near 175
BPM, re-tap, ⇧B. On env 1's strip switch **mode** to gate. *Pass:* the
kick lights the picture on the beat, the snare punches the zoom on 2 and
4 of each half bar, the hats split the colours on every 16th; nothing
drifts over a minute; at 175 the hats still read as separate hits, not
a smear; with env 1 in gate mode the kick still lets go within half a
step (`seq.gate`). *Fail:* hits late or early against the music after a
good tap (`Sequencer.time_of`); a hit doubled or skipped when the frame
rate dips; a gate-mode kick that holds.

**283. The global trigger re-aligns the grid; restart does not move the LFOs.** (laptop)
Headless: `tests/test_plan31_wiring.py::test_the_global_trigger_fires_step_0_the_same_frame`, `tests/test_sequencer.py::{test_the_clock_trigger_fires_step_zero_that_call_at_the_trigger_time,test_seq_trigger_keeps_its_offset_until_the_clock_trigger_clears_it}`.
On `seq-demo`, running, set LFO 1 to sync **1 bar** and route it onto
something visible (ROUTING or GRAPH). Press ⇧B (the trigger) off the
beat, a few times; then the SEQ page's **restart** off the beat; then ⇧B
again. *Pass:* each ⇧B puts the playhead on step 1 and LFO 1 at the top
of its cycle on the same frame, and the kick fires there; **restart**
puts the playhead on 1 while LFO 1 runs on; the next ⇧B lines both up
again. *Fail:* the grid ignores ⇧B (`Clock.epoch`); a burst of steps on a
trigger; restart moves the LFOs.

**284. GRAPH's lane cables.** (laptop)
Headless: `tests/test_graph_seq.py::{test_a_lane_with_a_step_on_is_a_binding_cable_to_its_envelope,test_a_lane_rebinds_by_a_drag_onto_an_envelopes_fire_and_cannot_be_deleted,test_a_lane_bound_to_a_removed_envelope_draws_nothing,test_a_lane_envelope_is_refused_an_extra_one_goes}`.
On `seq-demo`, stopped, open GRAPH and frame MODULATION; expand
*sequencer* and *env 1*–*env 3* (open MODULATION's idle line to see
*env 4*). Press run on SEQ and come back; mute lane 2. Drag lane 1's pin
onto *env 4*'s `fire` stub; ⌘Z. Select a lane cable, press Delete.
Right-click *env 1* → delete; right-click the canvas → **envelope**, then
delete the new one. *Pass:* three cables "lane 1 fires env 1" … "lane 3
fires env 3", faint "(stopped)" until run, bright while running, lane 2's
faint "(muted)"; lanes 4 and 5 (no steps) have none; the drag rebinds
lane 1 to env 4 (SEQ's picker says env 4) and ⌘Z puts it back; Delete
says "a lane always fires an envelope: drag its pin onto another
envelope's fire to rebind it" and keeps it; env 1's delete is greyed
("… is a sequencer lane's envelope: it stays"); the new envelope is env 6
and goes. *Fail:* a lane cable deleted; a drag making a route instead
(`Edit._binding`); env 1 removable.

**285. A `/3` preset between two Macs.** (two Macs, the copy)
Headless: `tests/test_plan31_wiring.py::{test_an_untouched_preset_saves_as_2_without_an_envelope_or_a_step,test_anything_an_older_build_would_lose_saves_as_3,test_this_build_reads_both_and_an_older_build_refuses_a_3}`.
On this build, save TRIP untouched under a new name, then turn one step
on and save again under another; open both files in a text editor. Point
a build from before plan 31 at the same library and load each.
*Pass:* the untouched one says `"schema": "hyperspace.preset/2"` and has
no `env.` or `seq.` value; the other says `/3` and holds the pattern; the
older build loads the first and refuses the second with "schema … is not
a hyperspace.preset", the file untouched. *Fail:* an untouched preset
written as /3 (`preset.schema_of`); the older build loading the /3 file
and saving it without its pattern.

### The APC40 sequencer page (plan 31 A1, on `plan-31-a1`, pending Dylan)

The APC40 mk1 plugged in, `plan-31-a1` checked out, on the copy (its
`bindings.json` gets SEND A through `APC_NEW_ROWS` with a backup). Load
`seq-demo` and press run on the SEQ page unless a check says otherwise.
The on-screen desk mirrors the page.

**286. SEND A enters and redraws; leaving restores the bank, SAVE and the toggles.** (APC40, the copy)
Headless: `tests/test_seq_page.py::{test_send_a_enters_and_the_grid_redraws_from_the_steps,test_leaving_restores_the_bank_the_toggles_and_save,test_the_render_toggle_comes_back_on_leaving,test_a_pad_toggles_a_step_and_loads_no_preset}`.
With a show whose bank fills rows 1, 4 and 5 (party), note the 24 bank
pads' colours, SAVE and scene 1–4's lights. Press SEND A; press a few
grid pads; press SEND A again. *Pass:* SEND A lights; the grid shows
lanes 1–3's steps in green and lanes 4–5 dark, scene 1 lit (lane 1
selected); a pad toggles its step (on screen too) and loads no preset;
SEND A again goes dark and the 24 bank pads come back exactly as noted
(green loaded, amber filled, dark empty), SAVE and the scene toggles
too. *Fail:* a bank pad left dark or a step light left on
(`MidiIO.redraw`, `page_serial`); a pad press loading a preset under the
page.

**287. Yellow over green is legible.** (APC40)
Headless: `tests/test_seq_page.py::test_an_advancing_playhead_sends_only_the_diff`.
SEND A up, `seq-demo` running at about 120 BPM, from a metre or two.
*Pass:* the playhead's yellow on a lit step is told apart from green at a
glance, on lane 3's hats every step, and red (lane 2 muted on the screen)
from both. *Fail:* yellow and green look alike on the mk1 (`apc40.SHADE`).

**288. No flicker as the playhead runs.** (APC40)
Headless: `tests/test_seq_page.py::test_an_advancing_playhead_sends_only_the_diff`.
Turn on every step of all five lanes on the screen; SEND A; run at 175
BPM with span ½ bar; then 4 bars. *Pass:* the yellow column steps
cleanly across five lit pads; no pad flickers dark between steps; the
desk log is not flooded. *Fail:* a flash of dark or a stutter (the
`last_out` gate; more than about twelve messages a step).

**289. Clip stop is the playhead and the length.** (APC40)
Headless: `tests/test_seq_page.py::test_clip_stop_sets_the_length_and_clip_stop_8_does_not_save`.
SEND A, running. Watch the clip stop row; press clip stop 5; then 8; stop
the transport. *Pass:* one clip stop is lit, moving across with the
playhead; after clip stop 5 the pattern wraps after step 5, columns 6–8
go dark and their pads do nothing, the light moves over 1–5 only; clip
stop 8 restores eight and **does not save** (it is SAVE off the page);
stopped, the clip stop row is dark. *Fail:* clip stop 8 saving a preset
under the page; a column past the length still toggling.

**290. Scene select and the mute blink.** (APC40)
Headless: `tests/test_seq_page.py::test_scene_1_selects_then_mutes_and_leaves_the_render_toggles`.
SEND A. Press scene 2; scene 2 again; scene 3; scene 2 again. *Pass:*
scene 2 lights (lane 2 selected, the desk header "SEQ · lane 2 · L=8");
the second press mutes lane 2: its scene button blinks, its pads go red,
its snare stops on the picture; scene 3 selects lane 3 and scene 2 keeps
blinking; pressing scene 2 then selects it (not unmutes); the render's
points / lines / faces / rotate do not change. *Fail:* the blink
unreadable or not blinking on an mk1 (`apc40.SHADE`, velocity 2); a
scene press toggling `view.points`.

**291. A bank pad held across SEND A does not save.** (APC40, the copy)
Headless: `tests/test_seq_page.py::test_a_bank_pad_held_across_send_a_never_saves`.
Page down. Hold an **empty** bank pad (row 4); while holding, press SEND
A; keep holding past the save time; let go. *Pass:* no preset is saved
(PRESETS and the slot unchanged), the pad does not blink, the page is up;
its release does nothing. *Fail:* a new preset in the slot
(`MidiIO._drop_page_holds`).

**292. SHIFT inside the page.** (APC40)
Headless: `tests/test_seq_page.py::test_shift_inside_the_page_moves_the_knobs_not_the_grid`.
SEND A; press SHIFT (it latches); press grid pads, scene buttons and
clip stops; turn a track knob; SHIFT again. *Pass:* with SHIFT up the
grid, the scenes and the clip stops still edit the sequencer (no band
scene, no SHIFT-layer pad action); the knobs and faders are the SHIFT
layer's; SHIFT off, back to the preset layer's knobs, the page still up.
*Fail:* a SHIFT-layer row firing under a page control (`Bindings.dispatch`).

**293. QUANT loads a preset with the page up.** (APC40)
Headless: `tests/test_seq_page.py::test_a_pad_toggles_a_step_and_loads_no_preset` (its QUANT load: the page stays, the grid redraws to the loaded pattern).
SEND A on `seq-demo`; press QUANT (next preset) a few times, then load
`seq-demo` again from the screen. *Pass:* the page stays up through
every load; the grid redraws to each preset's pattern (empty for one
with none, dark), and back to the drums on `seq-demo`; the knobs follow
each preset's desk as usual. *Fail:* a load taking the page down, or the
old pattern left lit.

**294. A power cycle re-sends the page.** (APC40)
Headless: `tests/test_seq_page.py::test_a_power_cycle_with_the_page_up_resends_the_page`.
SEND A up and running; switch the APC40 off and on (or unplug and
replug it). *Pass:* within a second or two the desk is back in the app's
mode with the page lit as it was — SEND A lit, the steps, the scene and
the moving clip stop. *Fail:* a dark grid or the bank's lights with the
page still up on screen (`midi.py`'s reconnect redraw).

**295. SEND A in a desk fallen back to Generic mode.** (APC40)
Headless: none (the fake-port rig models no Generic mode).
With the page **down**, make the desk fall back (switch it off and on
while the app runs, SETUP's "Generic mode"); press SEND A; then press it
again. Repeat with the page **up** before the fall-back. *Pass:* the app
puts the desk back in its mode within a press or two (the desk log says
"back in the app's mode"); after that SEND A toggles the page once per
press, its light agreeing with the screen; at worst the first press is
lost (press again). *Fail:* the page and SEND A's light out of step, or
SEND A latching on the device itself (in Generic mode SEND A is a
toggle the device keeps; `apc40.fell_back`).

## AA. Plan 32: media (channels, the media folder, live feeds, publishing out)

Plan 32 as built is [`32-media-channels.md`](32-media-channels.md): eight
channels `a`–`h`, each a bin of 16 sources and a `slot`; stills, video,
cameras, Syphon and NDI in; the backdrop, the faces, an effect's `aux` and
an output reading a channel; Syphon and NDI out; the MEDIA page. On
`plan-31-32-integration`, where plans 31 and 32 land together (base
`plan-28-30-integration`). Run on the copy
(`export HYPERSPACE_HOME=~/Hyperspace-try`), after `uv sync` (four new
dependencies). Pictures and clips to try go in `~/Hyperspace-try/media/`
(a still, an iPhone `.heic`, an `.mp4` of about 30 s with motion, a
`.gif`). A shared folder needs `[library] path` set to the cloud folder.
Group AA assumes the control window at its usual 960 × 900. None of these
has been run by a person; the loopback tests (our sender into our
receiver) are the only evidence for 304–309.

**296. A still as a backdrop.** (laptop)
Headless: `tests/test_media_render.py::{test_backdrop_under_scene,test_backdrop_history_toggle,test_an_effect_after_the_scene_sits_after_the_backdrop_too,test_the_echoes_show_over_a_bright_backdrop,test_a_static_backdrop_in_the_history_keeps_its_brightness}`, `tests/test_golden_frames.py` (`backdrop-still`).
MEDIA page: pick the still in the library (This Mac), click bin cell 1 of
channel A, then set **Backdrop** channel to A and its alpha to 1. Turn the
look-back on (the echoes), then **history** on and off; turn the faces'
cut-through on; place an `acid` effect after the scene on the FX page.
*Pass:* the still sits under the shape and is bent by the effects with
**history** on, and keeps its own brightness (it never brightens toward
white as the echoes build); with it off the echoes of the shape lie over
the still unbent, visible over its bright areas too; alpha 0.5 mixes; with a backdrop and cut-through on, faint fills
let the backdrop show (say whether that reads right). Setting Backdrop off
returns the picture exactly as before. *Fail:* the backdrop vanishes when an
effect is placed after the scene (`graph._place_one`), a seam or flipped
picture (`media_tex.flipped`).

**297. The faces and `aux`.** (laptop)
Headless: `tests/test_media_faces_aux.py::{test_faces_show_channel,test_aux_wired_from_channel,test_displace_moves_pixels,test_blend_modes_with_an_aux,test_unwired_aux_reads_black}`, `tests/test_golden_frames.py` (`faces-media`, `displace-luma`, `blend-luma-key`).
Set **Faces** to channel A (the still), alpha 0.8, then each path (STILL,
ORBIT, FIG-8, SWAY). Back on GRAPH, wire `media.a` to the `aux` port of
`displace`, then of `blend`; turn each on; try `blend`'s five modes and the
luma-key threshold, `displace`'s luma and red/green modes. *Pass:* the
picture sits on the faces in aspect, upright, and follows the pattern
per-face or in screen space as the bitmap did; `displace` bends the frame by
the still's brightness and mid-grey moves nothing; `blend` keys the bright
parts; unwiring `aux` leaves the effect as if it were off. *Fail:* a flipped
or stretched picture; an unwired aux that is not transparent
(`fx.py`'s aux uniforms, `_lib.glsl`).

**298. A video: rate, scrub, loop, the proxy.** (laptop)
Headless: `tests/test_media_transport.py`, `tests/test_media_video.py`, `tests/test_media_channels.py::test_transport_drives_want`.
Put the `.mp4` on channel A and the faces or backdrop on A. Watch the
SYSTEM page for a `media.a` line and the page's playhead bar. Set rate 2,
−1, 0, 0.5; loop, ping-pong, once; drag **position** while it plays and
let go; wait a minute and open it again. *Pass:* it plays at native speed
at 1; double speed at 2; backwards at −1; holds at 0; the position drag
scrubs and, let go, it plays on from there; ping-pong reverses at each end,
once holds the last frame; after the first open, `<home>/media-cache/proxies/`
holds a proxy file and scrubbing is smoother on the next open.
The frame rate holds with the clip playing (three playing clips on
three channels: say the frame time). *Fail:* the picture stalls while
scrubbing or the whole app hitches on a clip switch (`media.video`,
`channels._switch`).

**299. Jog with the cue knob.** (APC40)
Headless: `tests/test_media_transport.py::{test_jog_spins_and_coasts,test_pos_latch_scrubs_then_plays_on}`.
Select channel A on the MEDIA page. Arm Learn on **jog**, turn the APC40's
CUE knob (relative) so the route is made; then spin the knob either way and
let go, with the clip at rate 1 and at rate 0. *Pass:* a spin speeds the
playhead (or runs it backwards) and, let go, it coasts back to `rate`
within about a second, like a platter; at rate 0 it scrubs and stops. Say
whether the gain and the coast feel right. Nothing was bound by default
(row 339). *Fail:* it never settles (`transport.JOG_HZ`) or jumps
(`JOG_GAIN`).

**300. A dropped file appears.** (laptop; the cloud for the second half)
Headless: `tests/test_media_folder.py::{test_dropped_file_appears_within_a_scan,test_removed_file_is_missing,test_slow_read_is_fetching,test_dataless_flag_is_fetching}`.
With the MEDIA page open on This Mac, drop a new picture into
`~/Hyperspace-try/media/` from Finder; then delete a file that is on a
channel; then, with `[library] path` set to the Drive folder, drop a file
into `<drive>/media/` from the other Mac, and one that Drive has not yet
downloaded. *Pass:* the new file is in the list within about two seconds
with a thumbnail, no relaunch; the deleted one's channel goes black and
its status reads `missing` (the app does not hitch); the file from the
other Mac appears as `shared:…`, `fetching` while Drive streams it, then
ready. *Fail:* a stall while a placeholder downloads (`folder._probe`),
a stuck `fetching`.

**301. The missing-local banner; both Macs on `/4`.** (two Macs)
Headless: `tests/test_media_preset.py::{test_media_preset_is_v4,test_preset_without_media_is_unchanged,test_bins_round_trip,test_v2_and_v4_both_load}`, `tests/test_ui_media.py::test_banner_lists_missing`.
On Mac 1 save a preset with a `local:` clip, a `camera:` and a `shared:`
file in its bins; on Mac 2 (running this build) load it from the shared
library. Then save a preset with no media on Mac 1 and open the file.
*Pass:* on Mac 2 the MEDIA page shows the banner "`local:…` — not on this
Mac: shows black" for the local one and the camera if it has none, and the
channel is black while the shared file plays; a preset with no media is
`hyperspace.preset/2` and looks as it did. Then open that `/4` preset in a build from before plan 32 (check out
`plan-28-30-integration`, or use a Mac that has not updated) and read what it
says: it should refuse the file or note the unknown schema, and load
nothing of the media. Update both Macs before saving one. *Fail:* the
banner is missing or lists a source that is present (`channels.missing`).

**302. Junk, mid-show deletes and rapid switching.** (laptop)
Headless: `tests/test_media_folder.py::{test_junk_does_not_stop_the_scan,test_blocked_read_does_not_stall_the_scan}`, `tests/test_media_channels.py::{test_rapid_switching_with_slow_closes_stays_fast_and_balances,test_close_with_a_hung_source_returns_within_two_seconds}`, `tests/test_app_boundary.py` (the exit test).
Put a `.txt`, a truncated `.mp4`, a 0-byte `.png` and a renamed
`.jpg` that is not a picture in the media folder. Put a good clip on
channel A and, while it plays, rename it in Finder. Map `media.a.slot` to an
LFO or the sequencer at 16ths over a bin of eight clips and run it for a
minute; then quit. *Pass:* the junk is listed with `error: …` and nothing
else stops; the renamed clip's channel goes black and `missing`, the app
carries on; the slot sweep never hitches the frame rate, memory and the
thread count settle, and the app quits in about two seconds. *Fail:* a
frame-time spike at a switch (`MediaState.poll`), a hang on quit
(`MediaState.close`).

**303. The MEDIA page at distance, and a big library.** (laptop)
Headless: `tests/test_ui_media.py::{test_the_media_page_fits,test_a_big_library_costs_what_is_in_view,test_a_thumbnail_is_decoded_once_off_the_ui_thread}`.
Two metres from the screen, with 30 or more files in the library and every
channel filled. Scroll the library, click a channel's letter, assign and
empty cells, use **Add file…** and **Copy to shared**. *Pass:* the
page fits the panel with no scroll beyond the library list; the letters,
status words and selected channel's transport read from there; the
selected channel's rate, jog, position, loop, slot and fit are the
panel's own widgets (right-click for Learn); scrolling a big library does
not drop the frame rate. Say whether a transport only for the selected
channel, rather than in each of the eight columns, is acceptable.
**Add file…** opens the macOS file dialog and the file appears under This
Mac; **Copy to shared** says where it landed. *Fail:* a stutter while
scrolling (`ui_media` clipper, `UiTextures`).

**304. Syphon in.** (laptop, a Syphon app)
Headless: `tests/test_media_live.py::test_syphon_loopback`, `tests/test_media_render.py::test_a_syphon_frame_samples_through_the_fit_pass`.
Run any Syphon server (Syphon Simple Server, Resolume's, a TouchDesigner
Syphon Spout Out TOP) with a recognisable
picture; with `kind = "syphon"` in `[[devices]]`, open the MEDIA page's
Live tab, put `syphon:<app>/<server>` on a channel, then on the backdrop.
*Pass:* the server appears in under 3 s; the picture is upright, the right
way round and not scaled wrongly; quitting the server shows `lost` and,
after a second, black; restarting it brings it back with no relaunch; the
frame rate stays near 60. *Fail:* upside-down (`u_bmp_flip`,
`media_tex`), a black picture (the rectangle blit, `MediaTextures.error`).

**305. NDI in from Resolume.** (laptop, Resolume, same router)
Headless: `tests/test_media_live.py::test_ndi_loopback`.
In Resolume, turn on NDI output (Output ▸ NDI). With `kind = "ndi"` in
`[[devices]]`, find `ndi:<Resolume sender>` on the Live tab and put it on a
backdrop. *Pass:* it appears within a few seconds, runs at the source's
rate with latency you cannot see in a beat, and survives Resolume quitting
(held 1 s, then black and `lost`) and coming back. *Fail:* nothing found
(the router blocking mDNS; try `extra_ips`, check 307), tearing or lag
(`media.ndi`).

**306. NDI in from TouchDesigner on a second Mac.** (two Macs)
Headless: as 305.
On Mac 2 run TouchDesigner with an NDI Out TOP; on Mac 1 use the build
with `ndi` on. *Pass:* as 305 over the wire; say the bandwidth and the
latency you see on your network. Note the sender's name as listed
(`ndi:HOST (stream)` appears only when two hosts send one name). *Fail:*
as 305.

**307. `extra_ips`.** (two networks)
Headless: `tests/test_media_live.py::test_extra_ips_go_in_the_apps_ndi_config_before_cyndilib`.
Where mDNS is blocked (a different subnet, or turn it off on the router),
add `extra_ips = ["<the sender's address>"]` to the `ndi` entry, relaunch
and look at the SYSTEM line. *Pass:* the sender is found by address; the
status reads `extra_ips via NDI config (unverified)`. This is the one that
rests on the SDK's documentation alone: write down whether it worked. If
not, `<home>/ndi/ndi-config.v1.json` and `NDI_CONFIG_DIR` are what to
check. *Fail:* nothing found with the entry set (`media.ndi`).

**308. Syphon out into Resolume.** (laptop, Resolume)
Headless: `tests/test_media_publish.py::{test_syphon_out_loopback,test_each_published_output_hands_its_picture_to_its_publishers}`.
Add `syphon = "hs"` to `[output]`; relaunch; in Resolume add a Syphon
source and pick "hs". *Pass:* our picture arrives upright at the render
cap's size (not 4K on a retina window), SYSTEM shows `syphon out hs — 60
fps, readback 0.0 ms`, and the frame rate holds. *Fail:* upside-down or a
black frame (`SyphonOut`), a dropped frame rate.

**309. NDI out into Resolume and TouchDesigner.** (laptop, both)
Headless: `tests/test_media_publish.py::{test_ndi_out_loopback,test_ndi_out_never_blocks}`.
Add `ndi = "hs"` to `[output]` and relaunch; receive it in Resolume (NDI
source) and in TouchDesigner (NDI In TOP) on a second Mac. *Pass:* the
picture arrives the right way up, colours within NDI's compression, and the
SYSTEM line reads about 60 fps and readback around 4 ms; the frame time
rises by that ~4 ms only. Quitting the receiver does not hitch the
app; a quit takes about two seconds. *Fail:* a stall when the receiver
connects or disconnects (`media.publish.NdiOut`), a picture flipped.

**310. A publish-only output; a window resized.** (projector or a second screen)
Headless: `tests/test_media_publish.py::{test_publish_only_output_has_no_window,test_draw_render_draws_a_publish_only_output_offscreen_at_the_render_cap}`.
Make output 2 `window = false` with `syphon` and `ndi` set (the rig can send
a picture it does not show); then give output 1 an `ndi` name and drag
the render window to another screen and resize it; try `window = false`
on output 1. *Pass:* output 2 opens no window and sends at `[output]
render`; output 1 keeps publishing at the capped size through the resize
and a retina/non-retina move (this is the one T9 could not see); `window =
false` on output 1 is a note and a window. *Fail:* the sent size follows
the window up to 4K, or a black send after a resize (`render._published`).

**311. A webcam; the dependencies.** (laptop)
Headless: `tests/test_media_live.py::{test_a_refused_camera_says_where_to_allow_it,test_cameras_are_listed_by_name,test_missing_library_is_an_error_status}`.
On a Mac that has not had the camera allowed to this terminal, `uv sync`,
add `kind = "camera"`, open the Live tab, put `camera:<FaceTime HD
Camera>` on a channel. Then refuse the prompt and look at the status. *Pass:*
macOS asks once; the picture runs at about 30 fps at 1280×720 (the
author's one run, from a script, read 30.5); a refusal reads `error: camera
permission (System Settings ▸ Privacy & Security ▸ Camera)`; `uv sync` pulls
the four new libraries and `uv run hyperspace` starts with no import
error. *Fail:* a stalled picture (`camera.CameraReader`).

**312. The phone, through an NDI camera app.** (a phone, same Wi-Fi)
Headless: none (the V1 phone is an `ndi:` source).
Install an NDI camera app on the phone (NDI HX Camera, say), start its
sender, find `ndi:<phone name>` on the Live tab and put it on a backdrop.
*Pass:* it appears and runs; say the delay and the quality, and whether
it survives the phone sleeping. This is the V1 phone (row 333); the QR
page is V2. *Fail:* not found (the router, same network).

**313. A feed vanishes and comes back.** (laptop, any live source)
Headless: `tests/test_media_live.py::{test_live_holds_then_black,test_sender_returns,test_a_held_feed_that_vanishes_is_kept_and_found_again,test_a_channel_follows_its_device_remade_by_a_config_edit}`.
With a Syphon or NDI feed on the backdrop, quit the sender, wait, restart
it; then edit `config.toml` (change the `ndi` entry's `extra_ips`) while
it runs. *Pass:* the last frame holds about a second, then black, status
`lost`; the feed returns by itself; the config edit does not drop the
channel for longer than the device's remake. *Fail:* it needs a slot
switch to come back (`channels._stale`).

**314. An old bitmap preset; knob 7.** (laptop, the copy; APC40 for the knob)
Headless: `tests/test_media_preset.py::{test_bmp_file_dropped_with_note,test_bmp_alpha_is_an_alias_of_media_alpha}`.
Copy in a preset saved by the previous build with a bitmap on the faces
(a `view.bmp_file` value) and load it; turn the APC40's knob 7 on the
default desk with the faces on a media channel. *Pass:* the load note says
`bitmap file <path> is no longer read: put it on a media channel` and
the faces are plain; put the picture on a channel and set **Faces**, and
knob 7 moves its opacity as it did the bitmap's (the preset's old alpha
landed on `view.media_alpha`). *Fail:* a crash on load, or knob 7 dead
(`params`' alias rule).

**315. A frozen Syphon channel.** (laptop, a Syphon app with moving
picture)
Headless: `tests/test_media_channels.py::test_live_freeze_at_rate_zero`,
`::test_a_frozen_live_channel_says_frozen` and
`tests/test_media_render.py::test_a_frozen_rectangle_frame_is_never_copied_again`
(no real Syphon surface).
Put a moving Syphon server on a channel (backdrop), set `rate` to 0, then
watch for five seconds. *Pass:* the picture stops and the MEDIA page says
`frozen`. The held frame names Syphon's own texture, but the channel's
copy of it is made only when the frame moves, so it should hold. The one
expected exception: save a renderer file (a hot reload) while frozen — the
copy is made again from the held name, so the picture may jump to the
live one or to garbage; write down which. An NDI feed at rate 0 should
freeze exactly (`channels._freeze`, `syphon.SyphonSource.gl_poll`).

**316. A camera without a 1280×720 mode.** (a capture card or Continuity
Camera)
Headless: `tests/test_media_live.py::test_a_camera_without_720p_opens_in_a_mode_it_has`
and `::test_a_camera_with_no_mode_says_what_was_tried` (a fake `av`).
Put such a device on a channel. *Pass:* it opens (in 1920×1080, 640×480
or the device's default; `camera.MODES`). *Fail:* `error: …` — write down
the wording; a device that takes no mode says `error: no supported mode
(tried …)`.

## AB. Plans 31 and 32 together

**317. A preset with a pattern and a bin, saved and reloaded on the merged
build.** (laptop, the copy, a picture; a second Mac for the last step)
Headless: `tests/test_plan31_32_merge.py::{test_a_pattern_and_a_bin_save_as_4_and_round_trip,test_an_older_build_refuses_the_combined_4,test_a_3_only_and_a_media_free_preset_are_what_each_branch_wrote,test_media_at_the_librarys_default_is_untouched}`.
On `plan-31-32-integration`, load TRIP, turn two steps on in the SEQ grid,
put a picture in channel a's bin on the MEDIA page and make it the
backdrop; save under a new name and open the file in a text editor. Load
another preset, then the new one. Then load it on a Mac on a build from
before plan 31, or on `plan-32-media` alone. *Pass:* the file says
`"schema": "hyperspace.preset/4"` and holds the `seq.` values, the
`media` section and the backdrop values; reloaded, both steps are on and
the picture is under the scene; the other Mac refuses it ("schema … is
not a hyperspace.preset"), the file untouched. *Fail:* `/3` or `/2`
written (`preset.schema_of`), the pattern or the bin gone after the
reload, or the other Mac opening the file — `plan-32-media` alone reads
`/4` but not `/3` and would drop the pattern on a re-save (register row
340).

## AC. Plan 33: the free graph

Plan 33 as built is [`33-free-graph.md`](33-free-graph.md): effects exist
only where they are wired (no `order`, no `target`, no stack); the faces
(`shape.faces`), the pattern's media layer and the backdrop are graph
inputs; a `switch` picks one of eight pictures by a param; GRAPH adds,
inserts and reorders effects; the FX page browses the graph's effect
nodes; old presets migrate on load and save back unchanged. On
`plan-33-free-graph` (PR #235, into `plan-31-32-integration`). Run on the
copy (`export HYPERSPACE_HOME=~/Hyperspace-try`), after `uv sync`, with a
clip (`.mp4`) and a still in `~/Hyperspace-try/media/` and a camera for
318. **A free graph saves as `hyperspace.preset/5`, which an older build
refuses:** both Macs must run this build before 322's last step and 328.
Group AC assumes the control window at its usual 960 × 900. None of these
has been run by a person; the goldens were recorded on the build machine.

**318. The headline graph: a clip through two effects onto the faces, the
camera through `kaleido` behind the scene.** (laptop, the copy, a clip, a
camera)
Headless: `tests/test_graph_faces.py::{test_a_channel_through_effects_lands_on_the_faces,test_a_branch_under_the_scene,test_faces_unwired_draw_as_today}`, `tests/test_golden_frames.py` (`media-chain-faces`, `media-chain-backdrop`, `branch-two-sizes`).
Put the clip on channel A and the camera on channel B (MEDIA page). On
GRAPH right-click the canvas and add `acid` and `tripcolour`, then
`kaleido`: each appears faint, "reaches nothing". Drag `media.a` to
`acid.2.image`, `acid.2` to `tripcolour.2.image`, `tripcolour.2` to
`shape.faces`; then `media.b` to `kaleido.2.image` and `kaleido.2` to
`backdrop.image`. Turn the faces on, the look-back off, and set the
backdrop alpha to 1. *Pass:* each node loses its faint look as it is
wired; the clip plays on the faces through acid and tripcolour (on the
faces' own pattern if the clip is unwired again), the camera is bent
into a kaleidoscope behind the shape, and the SYSTEM page lists a line
for each of the three effects. Save under a new name: the file says
`"schema": "hyperspace.preset/5"`. Say whether the faces' picture reads
as a face texture or as a washed-out picture, and whether the 1024² face
picture is soft at distance. *Fail:* a wire refused that should land
(read the note), a node that stays faint when wired, black faces, or a
backdrop that does not follow `kaleido`.

**319. A switch over three channels on an APC40 knob, into the faces.**
(APC40, the copy, three channels with pictures)
Headless: `tests/test_graph_switch.py::{test_the_switch_shows_its_selected_input,test_a_route_drives_select,test_only_the_selected_input_is_made,test_select_changes_do_not_rebuild_the_graph,test_the_switch_onto_the_faces_is_a_cut}`, `tests/test_graph_edit.py::test_switch_over_the_channels_wires_all_eight_and_keeps_the_channel`, `tests/test_golden_frames.py` (`switch-faces`).
Put three different pictures on channels A, B and C. On GRAPH right-click
the canvas and choose **switch over the channels ▸ faces media**: a switch
over `media.a` … `media.h` into `pattern.media`, its `select` at the
channel that fed the faces (R28). Arm Learn on `switch.select` (the
switch's node, or the param search) and turn an APC40 knob. Sweep the
knob; set `switch.select` to `off` and to `4` (channel D, empty). On
SYSTEM watch the media uploads while on each. *Pass:* the faces show A,
B, C at `select` 1, 2, 3 (the knob's first three eighths), as a cut with
no crossfade; `off` and the empty `4` show the faces' own pattern; only
the picked channel's line is live on SYSTEM. Say whether eight positions
on a continuous knob are easy to land on and whether the cut feels
abrupt. *Fail:* a half-blended
picture, a stall when the pick changes, or an unselected channel still
uploading (`graph.Graph.pulled`).

**320. Reordering the run by dragging.** (laptop, the copy)
Headless: `tests/test_graph_edit.py::{test_reordering_the_run_is_rewiring,test_dragging_a_run_member_onto_another_cable_moves_it,test_insert_effect_on_a_render_cable}`.
Load `party-trip` (or any preset with two or three effects on). On GRAPH
open the shaders area, so the run `frame → … → fx.image` is cables. Drag
the first effect node onto the cable between the last effect and `fx`;
undo; drag a node onto empty canvas; right-click a cable and choose
"insert effect ▸ wobble". Then try to delete the cable `frame → fx.image`
when the run is empty. *Pass:* the dragged effect leaves its place, the
run closes over the gap and it sits at the new cable, and the picture
changes order at once; one undo puts it back; dropped on empty canvas it
stays where it was; the insert adds `wobble.2` into the cable; deleting
the last `frame → fx.image` cable is refused in words ("the run starts at
frame and ends at fx.image — insert effects into it"). *Fail:* a node
that duplicates, a run that breaks into two pieces, a second undo
needed, or a cable that cannot be hit (`ui_graph.dropped`,
`graphview.Edit.place_effect`).

**321. The FX page finds and plays an effect on a branch.** (laptop, the
copy)
Headless: `tests/test_fx.py::{test_groups_follow_the_wires,test_the_fx_page_lists_the_graphs_effects,test_show_on_graph_selects_the_node}`.
With 318's graph loaded, open the FX page. Find `acid.2` and `kaleido.2`,
click each, move a slider of the open one, toggle its `on`, click **Show on
GRAPH**. Open GRAPH, select another effect there, return to FX. *Pass:*
the list is grouped (**Run**, **→ faces**, **→ backdrop**, and
**reaches nothing** last), `acid.2` under **→ faces** and `kaleido.2` under
**→ backdrop**; each row's state reads `running` or the reason it is
idle; the slider changes the picture live; **Show on GRAPH** selects and
centres the node; the selection made on GRAPH is the one open on FX. The
page offers no add, remove or reorder. *Fail:* an effect missing from the
list, listed under the wrong end, or a selection that diverges between
the two pages (`Panel.fx_selected`).

**322. An old party preset loads and looks the same; saved untouched it
opens on the second Mac.** (laptop, the copy, a second Mac on `main` or
the previous integration build)
Headless: `tests/test_graph_free.py::{test_an_untouched_v4_preset_saves_byte_identical,test_a_free_fixture_saves_as_five}`, `tests/test_graph_migrate.py::{test_every_library_preset_migrates_without_a_note,test_no_library_preset_routes_an_effect_it_leaves_out}`, `tests/test_golden_frames.py` (the 661 before the plan).
On a Mac with a preset library from before this plan (a copy of the
shared folder), load each `party-*` preset and `dial`,
watching the footer. Note two or three by eye against how
they looked last week. Save one of them under its own name without
touching anything, and open both files in a diff. Then open the library on
the second Mac (on the previous build). *Pass:* no load note; the pictures
look as they did, including `dial`'s three effects that come in only when
an axis is pushed (R5); the saved file is
byte-identical to the original (a diff shows nothing); the second Mac
opens it without a note. *Fail:* a load note naming an effect left out, a
picture that differs, a diff, or an older build refusing the file — write
down which preset (`graphmigrate.legacy_values`, `Presets.document`).

**323. A channel on the faces is lost mid-show.** (laptop, any live source)
Headless: `tests/test_graph_faces.py::test_faces_fall_back_to_the_pattern_when_the_branch_reads_nothing`, `tests/test_media_live.py::test_live_holds_then_black` (a stopped feed is held 1 s, then reads nothing with the status `lost`); the first test also draws the lost-feed frame and asserts it equals the faces-unwired frame.
With 318's graph (or a camera or NDI source straight into
`pattern.media`), unplug the camera or stop the NDI sender while the
faces show it; wait five seconds; plug it back. Delete the clip file on a
second run. *Pass:* the faces show the pattern (not black, not frozen) for
the frames the branch reads nothing, the SYSTEM line for the channel says
`lost`, the show continues without a hitch, and the picture returns by
itself when the feed does; the backdrop shows nothing while its branch
reads nothing. *Fail:* black faces, a freeze, or an exception in the
stall log (`graph.Shape.faces`, `media.live`).

**324. The frame cost of two branches, the faces branch and an eight-way
switch.** (laptop; the build machine's SYSTEM page)
Headless: `tests/test_graph_switch.py::test_only_the_selected_input_is_made`, `tests/test_graph_faces.py::test_a_branch_read_at_two_sizes_is_made_once_each_and_does_not_leak`. These count makes; nothing times them.
On SYSTEM write down the frame rate, and each node's ms, on `party-trip`
with the look-back off and no branch wired. Build, in turn: two branches (a channel through two effects into an
output, a second channel through one effect into `aux` of `blend`); 318's
faces branch with three effects; and a switch with eight channels wired in
and a different effect on each. Drive the switch with an LFO. Read the
frame rate and the per-node lines for each, at the output's usual
resolution, and write the numbers down. *Pass:* the frame rate stays where
it was with no branches, and the eight-way switch costs about one branch
(only the picked path has lines on SYSTEM). *Fail:* the frame rate drops
visibly with the switch, or a branch's line keeps growing over a minute
(`Renderer._prune_sized`).

**325. The near-miss drag.** (laptop, the copy)
Headless: `tests/test_graph_edit.py::test_dragging_a_run_member_onto_another_cable_moves_it` (the drop on its own cable and on empty canvas do nothing).
On a graph with a run of two effects and a few branch cables, drag an
effect node and let go a few pixels *beside* a cable, then beside a value
cable, then onto a cable that is not a picture (a modulation cable).
Read the footer each time. *Pass:* a drop beside a cable either lands on
it (when within the hit distance) or does nothing; a drop on a
non-picture cable may say "x is no picture cable". Say whether those
refusal notes are noise or help, and whether the hit distance is too
tight or too loose. *Fail:* a node moved by a drop that was nowhere near a
cable, a run split in two, or a note on every plain drag (R22; the
ledger's T6 minor).

**326. A shader back into the faces on the GRAPH layout.** (laptop, the
copy)
Headless: `tests/test_graph_areas.py` (the four `/5` fixtures, each with no back wire), `tests/test_graphview.py`.
Load 318's graph (`media.a → acid.2 → tripcolour.2 → shape.faces`) and
press tidy, then expand the shaders area. *Pass:* the cables run left to
right: MEDIA (channel, `acid.2`, `tripcolour.2`) then GEOMETRY (the
shape), with no cable doubling back across the canvas; the two effect
nodes sit in the MEDIA area, not SHADERS; an unwired effect is faint with
"reaches nothing" and sits where it was added. Say whether the layout
reads at arm's length. *Fail:* a cable running back across areas, effects
in SHADERS that are made of the media alone, or tidy putting a faint node
in an area it does not belong to (`graphview.media_made`, `area_of`).

**327. The FX page with a big graph, at arm's length.** (laptop)
Headless: `tests/test_fx.py::{test_the_page_draws_and_fits,test_the_fx_page_lists_the_graphs_effects}`. The first draws TRIP's graph with each of its effects open and asserts the page never scrolls; a dozen-effect graph is not covered.
Build a graph with about twelve effects across the run, two branches, the
faces, the backdrop and three unreached nodes. Open the FX page and read
it from a metre and a half away. *Pass:* the group headers are legible,
the state words (`running`, `off`, why) are readable, a name is easy to
hit, the page fits without scrolling or clipping the strip, and the
**reaches nothing** group stands out from the rest. Say what you would
change (grouping, row height, a collapse). *Fail:* a row hidden, a strip
pushed off the page, or text under 12 px (`ui_fx.page`).

**328. A free graph is refused by an older build.** (two Macs, the copy)
Headless: `tests/test_graph_migrate.py::test_v5_is_refused_by_the_ladder_below`, `tests/test_graph_free.py::test_a_free_fixture_saves_as_five`.
Save 318's graph on the new build; open the file and read the `schema`.
Open the same library on the second Mac, on the build from before the
plan. Then, on the new build, open the saved preset and delete every
branch and switch so only the run is left, and save under another name.
*Pass:* the first file says `hyperspace.preset/5` and the old Mac refuses
it ("schema … is not a hyperspace.preset"), leaving the file as it was;
the second, with only a run, says `/4` (or the lowest schema that fits)
with `order` and `target` values and opens on the old Mac. *Fail:* the
old Mac opens the `/5` file or drops part of it, or the run-only file is
`/5` (`preset.schema_of`, `graphmigrate.legacy_values`).

**329. A node's controls in the side panel, and a switch by mouse.**
(laptop, the copy, a clip)
Headless: `tests/test_graph_legible.py::{test_a_media_nodes_params_are_rows_in_the_side_panel,test_a_side_panel_row_edits_through_the_param,test_a_big_node_folds_its_groups,test_open_on_page_switches_page_and_selects,test_the_switch_block_picks_an_input_with_one_click}`.
Put the clip on channel A (MEDIA page) and wire `media.a → shape.faces`.
On GRAPH click the `media.a` node: drag its **position** slider in the
side panel, then its **jog**, and right-click a label for Learn. Press
**open on MEDIA**. Back on GRAPH, add a **switch over the channels ▸ faces
media** (right-click the canvas), click the switch and press its chips
`3 · media.c`, `1 · media.a`, `off` with the mouse; click the shape.
*Pass:* the clip seeks with position and scrubs with jog as it does on
the MEDIA page, one ⌘Z undoes one drag; the chip opens MEDIA with
channel A selected; each switch chip changes the faces at once, the pick
lit, an unwired input faint, and the switch's canvas line says "picks
in3"; the shape's groups are folded, the patched ones open, and the panel
scrolls; the graph never pans. Say whether 320 px reads at arm's length.
*Fail:* a row that does not move its param, an undo that takes two
steps, the wrong page or channel, a chip that does nothing, or the
canvas moving when a node is clicked (`ui_graph._param_rows`, `home_page`,
`_switch_block`).

**330. Route from ▸ an LFO, a new LFO, and a taken param.** (laptop, the copy)
Headless: `tests/test_graph_edit.py::{test_route_from_lists_the_lfos_and_envelopes_on_a_modulatable_param,test_route_from_an_lfo_makes_the_route_a_graph_cable_makes,test_route_from_on_a_taken_param_asks_replace_or_keep,test_route_from_new_lfo_adds_one_and_routes_it,test_an_lfo_already_driving_is_checked}`.
The owner, 2026-10-24: "There is no Learn option for routing one of the
LFOs there or any of the envelopes there." On the FX page open Glimmer
and right-click its **mix**: **Route from ▸ LFO 1**. Right-click mix
again; then right-click its **speed** and pick **Route from ▸ new LFO**.
Then right-click a param a hand or a band already performs and pick
**Route from ▸ LFO 2**; press **Keep**, then do it again and press
**Replace**. Open the same menu on GRAPH's side panel and on the VIEW page.
*Pass:* mix breathes with LFO 1 and GRAPH shows the cable `LFO 1 → mix`;
the second menu shows **LFO 1** checked, and clicking it does nothing;
new LFO adds one LFO (the LFO page and GRAPH show it) that drives speed,
and one ⌘Z takes both the LFO and its route back; the taken param puts up
the Replace / Keep prompt, Keep leaves the old performer and Replace puts
LFO 2 there; the submenu is the same on every page, sits after the Learn
items and before Learn sink, and is absent on a toggle or a trigger.
*Fail:* a route that differs from the one a GRAPH drag makes (op, depth),
an undo that takes two steps for new LFO, a pick on a taken param that
replaces with no prompt, or a page whose menu lacks it
(`ui_graph.route_from_menu`, `Panel._ctx_learn`).

**331. An envelope pushes up from the base and comes back to it.** (laptop, the copy)
Headless: `tests/test_graph_edit.py::{test_an_envelope_route_is_a_push_about_the_base,test_an_envelope_on_a_toggle_stays_position,test_an_lfo_route_is_unchanged}`.
The owner, 2026-10-24: "the envelopes have no way for me to set a
baseline … they all reduce the base to 0 in between fires no matter what
I set the base to be." Wire a glimmer into the run and set its **mix** to
0.4 on the FX page. Right-click mix: **Route from ▸ env 1**. On SEQ set
envelope 1 to one-shot with a short attack and decay, and fire it (its
fire chip, or a sequencer step) a few times; watch the mix slider's
modulated mark and the picture. Then open ROUTING and read the new row.
*Pass:* between fires mix sits at 0.4 and the glints show at that level;
each fire lifts mix to the top (1.0) and it falls back to 0.4; the row
reads `push` at depth 0.60, and its op chip flips it to `pos` and back.
The same cable dragged on GRAPH from env 1's out into mix's `mod` makes
the same row. *Fail:* mix drops to 0 between fires, a fire reaches less
than the top, or the GRAPH cable makes another row (`learn.row_for`,
`graphview.Edit.route_for`).

## AD. Plan 34: feedback

Plan 34 as built is [`34-feedback.md`](34-feedback.md): a **delay** node
whose picture is last frame's input, so a loop drawn through one is legal;
the look-back's frames as pictures (`echo.1` … `echo.32`, newest first,
and `dream`); a **resize** that crops and makes a picture at a size of its
own; and loops through the faces, the backdrop or the frame refused when
the section is read, in words that point at a delay. On `plan-34-feedback`
(PR #236, with plan 35). Run on the copy
(`export HYPERSPACE_HOME=~/Hyperspace-try`), after `uv sync`, with a clip
(`.mp4`) in `~/Hyperspace-try/media/` on channel A for 338. None of these
has been run by a person; the goldens were recorded on the build machine.

**How AD and AE relate.** Both groups run on the same build, in one go.
Plan 35 renamed the nodes and made the frame wires, so every AD check
starts from a **new preset (342)** and its scene starter, or from the
factory frame, and names the wired frame's ids (`channel.a`, `lookback`,
`output.all`, `delay(write)` on SYSTEM). 334's drag is GRAPH's, as 343's
is: do them one after the other. 340 and 351 are both SYSTEM's frame cost,
so time them in one sitting. **341 is the `/5` half of 352**: a `/5` file
with a delay, opened on a plan 33 build, is read with a note; a `/6` file
there is refused (352). Both Macs run this build before 341 and 352, and
before anyone saves a delay, a resize, an echo or the dream (`/5`) or
anything that needs plan 35's vocabulary (`/6`). Group AD assumes the
control window at its usual 960 × 900. In every graph below, make the
shape show first (the scene starter, or `shape → scene.geometry`, `scene →
lookback.image`, `lookback → output.all.image`).

**332. The infinite mirror; an empty delay shows the pattern.** (laptop,
the copy)
Headless: `tests/test_graph_delay.py::{test_a_delay_shows_last_frames_picture,test_the_first_frame_reads_nothing_and_the_faces_show_the_pattern,test_a_delay_whose_input_read_nothing_reads_nothing}`, `tests/test_golden_frames.py` (`delay-faces`).
On a new preset (342) pick the scene starter, then add a `delay` from
**pictures ▸** and wire `scene → delay.image` and `delay → shape.faces`
(and turn the faces on). Watch a minute. Then delete the cable `scene →
delay.image` so the delay's input is nothing, and wait a second; wire it
back.
*Pass:* the faces show the shape within the shape, a frame deeper each
frame, with no error on the control window or SYSTEM, and no cable refused;
with the cable deleted the faces fall back to the face pattern (as they
look with `delay` unwired), not black, and come back to the mirror when it
is wired again. Judge the look, black faces included (the faces show an
opaque picture fully, and the scene's target is 8-bit).
*Fail:* a refusal on either drag, black faces after the cable is deleted,
a stale picture frozen on the faces, or an error line
(`graph.Delay`, `graph.DelayWrite.run`).

**333. Trails you can see.** (laptop, the copy)
Headless: `tests/test_graph_delay.py::test_the_trails_show_and_fade`, `tests/test_golden_frames.py` (`delay-trails`).
Build the `delay-trails` graph: a `zoomblur` (amount about 0.15, glow 0)
and a `palette` (on, mix 1, val slice to 0.6), a `composite` set to add;
wire `delay → zoomblur.2 → palette.2`, `scene → composite.2.under`,
`palette.2 → composite.2.over`, then `composite.2 → delay.image` and
`composite.2 → output.all.image`. (Or load a preset that has them.)
*Pass:* the shape leaves trails that stream toward the centre and fade
within a few frames when it moves; nothing sticks, burns to white or grows
without end; stopping the shape lets the trail die out. Compare with the
same graph minus `delay.image`: the trail is the only difference.
*Fail:* no trail at all (a picture identical to the plain frame), a
trail that never fades or saturates to white, or flicker from the delay
swapping (`DelayWrite`, `Renderer._turn_delays`).

**334. The drag: a loop is refused in words; through a delay it lands.**
(laptop, the copy)
Headless: `tests/test_graph_edit.py::{test_a_sink_loop_drag_is_refused_in_words,test_a_plain_loop_drag_points_at_a_delay}`, `tests/test_graph_feedback.py::test_each_sink_loop_is_refused_at_read`, `tests/test_graph_wired.py::test_loop_words_in_a_wired_frame`.
This is GRAPH's drag, as 343 is. With the scene starter, drag `scene`
onto `shape.faces`. Then add a `delay` and drag `delay` onto
`shape.faces`, and `scene` onto `delay.image`. Then wire a loop of effects:
`acid` and `wobble` in a row, and drag `wobble` onto `acid`'s `aux`.
*Pass:* the first drag goes red and does not land; its words say there is a
loop through the faces and to wire it through a delay; through a delay it
lands and the faces show the scene; the loop of effects goes red with words
that say to wire it through a delay (not the faces); each refusal leaves
the graph as it was.
*Fail:* a drag that lands green and then sits dormant, a refusal with no
words, or words that name the wrong node (`graph.LOOP_FACES`,
`LOOP_PLAIN`, `graph.sink_loops`).

**335. An echo on the faces, and into an output's hands.** (laptop, the
copy; the TV for the second window)
Headless: `tests/test_graph_echo.py::{test_echo_k_is_the_kth_newest_capture,test_the_ring_keeps_capturing_for_an_echo_with_the_look_back_off,test_a_res_change_empties_the_echoes,test_an_echo_into_an_outputs_hands_reads_last_frames_capture}`, `tests/test_golden_frames.py` (`echo-faces`).
Add `echo.4` from **look-back ▸** and wire `echo.4 → shape.faces`, with the
look-back off (LOOKBACK page). Change `dream.gap` and watch the cadence,
then change `dream.res`. Then put the look-back back on, delete that wire
and wire `echo.1 → output.2.hands` (or output 1 on the laptop alone).
*Pass:* the faces show the shape from four captures back, with no wake on
the picture and the look-back off; a longer `dream.gap` makes the echo move
less often; after `dream.res` changes the faces show what they show
unwired for a few commits and then the echo returns; the echo laid over the
output is one capture old and moves with the cadence, never the frame
being drawn; the echo node's words give its size and cadence.
*Fail:* a wake on the picture with the look-back off, an echo that
freezes after `dream.res` changes, an echo that shows this frame's picture
at the hands, or an error (`Lookback.echo_slot`, `graph.EchoNode`).

**336. The dream on the faces.** (laptop, the copy, the dream worker)
Headless: `tests/test_graph_echo.py::test_the_dream_reads_nothing_until_written`.
Add `dream` and wire `dream → shape.faces`. Try it with the dream worker
off and with it running (the dream in LOOKBACK).
*Pass:* without the worker the node's summary says "no dream worker: reads
nothing" and the faces show their pattern; with it, the faces show the
dream's picture once its first result lands.
*Fail:* black faces without the worker, a node with no explanation, or an
error (`graph.DreamNode`).

**337. A resize into a delay; an LFO on the crop.** (laptop, the copy)
Headless: `tests/test_graph_resize.py::{test_a_delay_through_a_resize_holds_a_small_buffer,test_a_crop_change_is_a_value_never_a_rebuild,test_nearest_keeps_hard_pixels,test_the_crop_takes_the_rect}`, `tests/test_golden_frames.py` (`resize-faces`, `resize-crop`).
Add a `resize` from **pictures ▸** and a `delay`. Wire `scene →
resize.image`, `resize → delay.image` and `delay → shape.faces`. On the
resize's side panel set `size` to 64, `aspect` to square and `filter` to
nearest. Then route an LFO (right-click the param ▸ **Route from**) to `resize.crop_w` and
`resize.crop_h`, and after that to `resize.crop_x`. Leave it running a
minute.
*Pass:* the faces show pixelated feedback (hard pixels, a coarse grid);
the LFO on the crop zooms and pans it smoothly with no hitch, no
flash, and nothing added to GRAPH or SYSTEM when it moves; the resize's
eight params are rows on its side panel and Learn works on them.
*Fail:* a flash or a hitch each time the crop moves, soft pixels with
nearest, a crop that cannot be modulated, or a rebuilt graph visible as
nodes flickering faint (`graph.ResizeNode.made`, `params.declare_resizes`).

**338. A resize before an effect makes the effect cheaper.** (laptop, the
copy, a clip on channel A)
Headless: `tests/test_graph_resize.py::{test_an_effect_after_a_resize_runs_at_its_size,test_a_resize_makes_its_own_size}`, `tests/test_golden_frames.py` (`resize-crop`).
Wire `channel.a → acid.2.image`, `acid.2 → shape.faces` and read
`acid.2`'s line on SYSTEM. Then insert a `resize` (size 256) between
`channel.a` and `acid.2` and read the line again.
*Pass:* the picture on the faces is the same look at a coarser size; the
`acid.2` line on SYSTEM is lower with the resize than without, and the
resize shows its own line; the resize sits in MEDIA or EFFECTS (MEDIA when
nothing but the media feeds it), with its cable out running forward.
*Fail:* the same `acid.2` time with and without the resize, a resize that
shows a full-size picture, or a cable running back across the areas
(`graph.Effect.own_size`, `graphview.MEDIA_MADE`).

**339. A window resize, the render cap, and a modulated resize size,
mid-feedback.** (laptop, the copy)
Headless: `tests/test_graph_delay.py::{test_a_size_change_loses_no_frame,test_a_graph_rebuild_keeps_the_delay}`, `tests/test_graph_resize.py::test_a_size_step_reallocates_once_each_way`.
Run 332's mirror. Drag the control window and the render window's edge,
and change the render cap. Then, on 337's graph, route an LFO to
`resize.size` and leave it stepping a minute; watch SYSTEM.
*Pass:* no black flash and no error through the resizes; the mirror
carries on; with `resize.size` stepping, the picture changes size at each
step with no error, and SYSTEM stays steady once each size has been seen
(the textures it left are kept for half a second and then released).
*Fail:* a black flash, an error line, a delay that restarts from nothing at
each step, or a frame time that climbs and keeps climbing under the LFO
(`render.DelayPair`, `Renderer._prune_sized`, `SIZED_KEEP_FRAMES`).

**340. The frame cost: a delay, a resize, echoes.** (laptop, then the rig;
with 351, in one sitting)
No test times a frame. Headless: none.
On SYSTEM note the frame time and the rate. Then run 332 at the render
cap and again with a `resize` (size 256) before the delay; then four
echoes wired on the faces. Write down `delay(write)`, the resize's line and
the frame time each time. Take 351's before-and-after numbers in the same
sitting.
*Pass:* the delay's cost is lower at 256 than at the cap, the resize shows
a line of its own, the four echoes cost something you can read off SYSTEM,
and the frame rate holds on the laptop; write the numbers down. Say what
the rig does.
*Fail:* a delay at 256 that costs as much as one at the cap, a hitch from
a node that is wired but unread, or a rate that drops with the look-back
off and an echo wired (`DelayWrite.held`, `Lookback.keep`).

**341. A `/5` file with a delay on a plan 33 build.** (two Macs, the copy)
Headless: `tests/test_graph_feedback.py::test_the_new_words_load_and_save_as_six`, `tests/test_presets.py::test_resize_values_save_and_load_with_the_preset`.
*Superseded by row 394 (2026-10-25): every save is `/6` now, so this file
says `/6` and a plan 33 build refuses it — see 353.* This is the `/5` half of 352. On this build load the factory frame, add a
delay in a loop (332) and save it under a new name; read its `schema`. Open
the library on a Mac on a plan 33 build.
*Pass:* the file says `hyperspace.preset/5`; the plan 33 build opens it
with a load note ("unknown node kind 'delay'") and draws its own default
graph, losing the run for that load, as expected; with both Macs on this
build the preset opens on both and the mirror runs.
*Fail:* the file says `/6` for a frame that needs nothing of plan 35's, a
plan 33 build that crashes or refuses the file, or a delay lost on this
build (`graphmigrate.uses_free_words`, `preset.schema_of`).

## AE. Plan 35: the free frame

Plan 35 as built is [`35-free-frame.md`](35-free-frame.md): the shape, the
scene, the hands (with their layer and guide), the backdrop, the look-back
and the outputs are ordinary nodes wired like an effect, each deletable on
GRAPH; an output shows what is wired into it, else **All outputs**, else
its ground; a window's `picture` and `hands` switches are the rig's mutes;
"hands through the effects" is wiring; every old preset loads as the
wiring it drew; a **new** chip on the PRESET strip starts blank; node ids
are renamed in the owner's words (`ghost` → `hands`, `history` →
`lookback`, `media.<c>` → `channel.<c>`; params unchanged). On
`plan-34-feedback` (PR #236, which also carries plan 34, group AD above).
Run on the copy (`export HYPERSPACE_HOME=~/Hyperspace-try`), after `uv sync`,
with a clip (`.mp4`) in `~/Hyperspace-try/media/`. **A preset that needs
the new vocabulary saves as `hyperspace.preset/6`, which an older build
refuses:** both Macs must run this build before anyone saves one, and
before 352. (Row 394, 2026-10-25, after this group was written: every
save is `/6`, an untouched `/4` included — see 353.) Group AE
assumes the control window at its usual 960 × 900. None of these has been
run by a person; the goldens were recorded on the build machine.

**342. A new preset: black, the factory's values, a starter.** (laptop,
the copy)
Headless: `tests/test_presets.py::{test_a_new_preset_is_factory_values_and_nothing_wired,test_a_new_preset_does_not_depend_on_what_was_loaded,test_a_new_preset_undoes_in_one_step,test_a_new_preset_saves_and_loads_back_empty,test_a_new_preset_draws_black}`, `tests/test_ui_presets.py::test_the_strip_has_a_new_chip`, `tests/test_graph_areas.py::test_a_blank_preset_draws_only_the_outputs`, `tests/test_graph_edit.py::test_the_starter_wires_the_scene_to_all_outputs`.
Load `party-trip` and change a few things (a knob, a route, a desk
button). Press **new** on the PRESET strip. Look at both windows, GRAPH,
MEDIA and the desk. Then right-click the GRAPH canvas and pick the
**scene starter**. Press undo twice.
*Pass:* both outputs are black (see-through if overlay is on); the footer
says `new preset: factory values, nothing wired — black until something is
wired to an output`; GRAPH shows only All outputs and the windows, with
the eight empty channels on MEDIA's idle line; the knobs are the factory's whatever was loaded
before, the routes are gone, and the desk is the factory preset layer;
the starter makes the shape show on both windows at once, in one undo
step; the first undo takes the starter away and the second takes `new`
back to `party-trip`. **save** on the unsaved preset asks for a name.
*Fail:* a value left from the loaded preset, a window that is not black,
a node on the canvas that is not an output, or a desk that is empty
(`Presets.new`, `graphview.render_starter`).

**343. The owner's own delete sequence.** (laptop, the copy)
Headless: `tests/test_graph_edit.py::{test_the_owners_sequence,test_every_frame_node_and_wire_deletes,test_deleting_a_window_unwires_it}`.
The owner, 2026-10-24: "there are all these error messages when I try
and delete the things I don't want in the graph." Load a party preset
with effects (`party-trip`). On GRAPH, click the cable `scene →
backdrop.scene` (or `scene → lookback.image`) and delete it; then
`lookback → ` the first effect; then each effect's cable in turn; then
the last effect's `→ output.all.image`.
*Pass:* every delete lands with no refusal, no word about "the default
graph", "a chain" or "plumbing"; the picture changes as each cable goes
(the scene leaves the look-back first, the effects go out of the chain
one by one, the backdrop is left alone) and both windows go black at
the last; a node that loses its last wire stays faint; ⌘Z puts each
back, one per step. Also delete the shape and the scene themselves and
a window.
*Fail:* any refusal that is not a type error or a loop, a node that
cannot be deleted, a cable that routes the picture somewhere else, or a
picture that does not change (`graphview.render_unwire`, `render_drop`).

**344. A channel alone on All outputs.** (laptop, the copy, a clip)
Headless: `tests/test_graph_frame.py::test_nothing_unreached_is_built`, `tests/test_golden_frames.py::test_every_golden_frame_is_drawn_byte_for_byte` (`channel-out-only`).
Put the clip on channel A. On a new preset (342) wire `channel.a →
output.all.image` (drag, or pick the channel in OUTPUT's All outputs
combo). Look at SYSTEM.
*Pass:* the clip plays full on both windows; SYSTEM lists no scene,
look-back or capture pass, only the channel's upload and the end;
deleting the cable puts both windows back to black.
*Fail:* a scene pass on SYSTEM, a window that stays black, or a window
that shows the clip while the other does not (`graph.build_graph`).

**345. A library preset by eye on both Macs, before and after.** (laptop,
the copy, the other Mac)
Headless: `tests/test_graph_migrate.py::test_every_section_loads_as_a_wired_frame`, `tests/test_graph_frame.py::test_the_wired_frame_builds_what_default_graph_builds`, `tests/test_graph_free.py::test_an_untouched_v4_preset_saves_byte_identical`, `tests/test_golden_frames.py::test_every_golden_frame_is_drawn_byte_for_byte`.
On the build from before plan 35 (a checkout of `plan-33-free-graph`
or the stack before) note how `party-trip`, `party-faces`, `dial`,
`displace-moo`, `glimmer-bug`, `moo` and a preset with a backdrop look,
on the laptop alone and with the TV. Open the same presets on this
build. Save `party-trip` untouched under its own name and diff it
against the original.
*Pass:* no load note; the pictures look the same on both windows and
both Macs; the untouched save is byte-identical; the `displace-moo`,
`glimmer-bug` and `moo` re-saves are still `/5` and open on the other
Mac.
*Fail:* a look that moved (name the preset and the window), a load note,
a changed file or an untouched preset that saves `/6`
(`graphmigrate.migrate`, `unwired`, `preset.schema_of`).

**346. The OUTPUT page: pick a picture; as All outputs; undo.** (laptop,
the copy; the TV for two windows)
Headless: `tests/test_ui_output.py::{test_the_combo_offers_the_graphs_pictures_in_area_order,test_picking_a_picture_wires_the_output,test_output_offers_a_channel_with_a_source_and_picking_wires_it,test_a_picture_put_back_saves_in_the_lowest_schema}`, `tests/test_ui_shell.py::test_the_output_page_fits_with_four_outputs_and_overlays_rows`.
Load `party-trip`. On OUTPUT open output 2's `shows:` combo and pick an
effect or a channel with a clip, then "as All outputs", then "nothing";
press **open on GRAPH**. Step undo back. With four outputs configured,
look at the page at arm's length: the block spacing is tighter than it
was (item spacing 4, was 7).
*Pass:* the combo lists "as All outputs", "nothing", then the graph's
pictures in the order MEDIA, SCENE, LOOK-BACK, EFFECTS, plus every
channel with a source; each pick changes output 2 only, writes one wire
(`channel.a → output.2.image`; "nothing" is a `ground` wire), and is one
undo step; "as All outputs" removes it; the page fits unscrolled at four
outputs and still reads at a distance; **open on GRAPH** selects that
window's node.
*Fail:* a pick that moves output 1, an undo that takes two steps, a
page that scrolls or crowds, or a combo missing a picture the graph has
(`graphview.picture_choices`, `set_picture`).

**347. The glass's picture mute, and the two owner notes.** (the rig,
a projector or the TV)
Headless: `tests/test_graph_frame.py::{test_a_mute_ignores_its_port,test_a_hands_mute_wins_over_a_stand_down}`, `tests/test_ui_output.py::test_the_mutes_are_not_the_preset`.
Turn the glass output's **picture** mute off with hands in view.
*Pass:* the glass shows the hands only (and the guide), the projector
unchanged; turning it on puts the picture back, with no hitch in the
frame. Then judge the two owner notes, which are changed meanings, not
bugs: **(a)** on a migrated preset with "hands through the effects" on
(`party-trip`'s through window), muting the **picture** now shows
nothing: a picture mute hides the through picture, where the old HANDS
route did not; **(b)** on a preset that holds the hands in the scene
(the fixture `hands-lines`, or any preset with the hands in the scene),
muting the picture shows the ground and the guide, not the hands layer,
because the migrated All outputs has no `hands` wire (the scene held
them). Say whether (a) and (b) are what you want; if not, say which
window and what you would expect. A hands mute on a through window
mutes the hands (R9).
*Fail:* a mute that rebuilds the graph (a hitch), a picture that stays
when muted, or hands left on a muted window
(`graph.Output.settle`, `outputs.Switches`).

**348. Hands through the effects on output 2.** (the rig, or the TV)
Headless: `tests/test_ui_output.py::{test_through_writes_the_wiring,test_through_needs_a_hands_layer_over_all_outputs}`, `tests/test_outputs.py::{test_through_bends_the_hands_with_the_shape,test_through_with_no_effect_on_is_hands_over}`, `tests/test_graph_frame.py::test_a_copy_chain_stands_down`.
On OUTPUT tick **hands through the effects** for output 2, with hands in
view and an effect on. Untick it. Turn every effect off.
*Pass:* output 2 shows the hands bent by the effects and output 1 the
hands laid over; unticked, output 2 is back to output 1's look; with
every effect off, output 2 looks like output 1; GRAPH shows the copies
and the composite the toggle wrote, and unticking removes them; the
toggle is disabled, with its reason, when All outputs lays no hands layer
or the window has its own picture.
*Fail:* a toggle that does nothing, copies left on the canvas after it is
unticked, or output 2 differing from output 1 with no effect on
(`graphview.set_through`, `graph.Shown`).

**349. LOOKBACK: what it records.** (laptop, the copy)
Headless: `tests/test_ui_lookback.py::test_records_says_and_sets_the_capture`, `tests/test_graph_migrate.py::test_backdrop_history_and_holds_become_the_capture_wire`.
On a preset with a backdrop and the look-back on, open LOOKBACK. Set
**records** to the backdrop, then to the scene, then to nothing. Watch
the echoes.
*Pass:* the echoes follow: with the backdrop they carry what the
backdrop shows, with the scene the shape alone, with nothing they stop
capturing; GRAPH shows the wire `→ lookback.capture` moving; each
change is one undo step; the "draws over:" line says what the look-back
is drawn over.
*Fail:* an echo that does not change, a records combo that disagrees
with GRAPH, or a look-back that stops with the capture unwired
(`graphview.set_picture`, `ui_lookback.capture_line`).

**350. The canvas at distance.** (laptop, the copy)
Headless: `tests/test_graph_legible.py::test_every_node_has_a_label_and_a_hover`, `tests/test_graph_areas.py::test_the_areas_run_by_primitive`, `tests/test_graphview.py::test_no_plumbing_words_remain`.
Load `party-trip`, press tidy and read the canvas from a metre and a half
away. Hover several nodes.
*Pass:* every node reads by its label and hover without its id (Hands,
Look-back, Backdrop, Channel A, the effect names, Output 1, All
outputs); the areas run MEDIA → SCENE → LOOK-BACK → EFFECTS →
OUTPUTS left to right with no cable running back except the capture's and
a delay's. Say what is hard to read.
*Fail:* an id where a name should be, a cable doubling back across
areas, or a node in the wrong area (`graphview.label_of`, `AREAS`).

**351. SYSTEM before and after, on the party preset.** (laptop, then the
rig)
Headless: `tests/test_graph_frame.py::test_a_mute_never_rebuilds`. No
test times a frame: the build counts no passes that it did not count.
On the build from before plan 35 and on this one, load `party-trip`
(then the rig's party preset on both screens), let it run a minute and
write down SYSTEM's frame time, the node lines and the rate. Then flick a
window's **picture** and **hands** mutes.
*Pass:* the frame time and rate are no worse than before; SYSTEM's
lines name the ends (`ends: shown(…)`), where the older build named
`fx` and the pipelines; a mute costs no hitch. Write down both numbers.
*Fail:* a slower frame, or a hitch when a mute flicks
(`graph.build_graph`, `Frame.users`).

**352. A `/6` preset on a plan 33/34 build; both Macs.** (two Macs, the
copy)
Headless: `tests/test_graph_migrate.py::test_v6_is_refused_by_the_ladder_below`, `tests/test_graph_wired.py::test_a_full_wired_frame_saves_as_it_stands`, `tests/test_graph_free.py::test_every_old_preset_saves_as_six_and_is_a_fixed_point`.
*Row 394 (2026-10-25) changes the pass: every re-save is `/6`, so the
untouched `/4` and the re-saved `/5` are `/6` too and the old Mac refuses
them as well; both Macs run this build (353).*
On this build make a preset that needs the new vocabulary (342, then wire
a clip into `output.2.image`, or pick "nothing" for output 2) and save it;
read its `schema`. Open the library on a Mac still on a plan 33/34 build.
Also open an untouched `/4` preset there, and a `/5` file re-saved by
this build. Then put both Macs on this build.
*Pass:* the new file says `hyperspace.preset/6`; the old Mac refuses it by
the ladder's words, leaving the file as it was; the untouched `/4` and the
re-saved `/5` open there; with both Macs on this build every preset
opens on both.
*Fail:* the old Mac opens or half-reads the `/6` file
(`Library.read`'s versions).

## AF. Row 394: every preset on the newest schema

The owner's decision of 2026-10-25 (register row 394): no long-term
support for old schemas — both Macs always run the newest build, so every
save is `hyperspace.preset/6` and the library is migrated once with
`tools/migrate_library.py`. On `preset-schema-6`. Every older schema still
loads.

**353. The library migrated to `/6`; both Macs on this build.** (two Macs,
the shared library)
Headless: `tests/test_migrate_library.py`, `tests/test_graph_free.py::test_every_old_preset_saves_as_six_and_is_a_fixed_point`, `tests/test_golden_frames.py::test_every_preset_resaved_as_six_draws_its_goldens`.
Put both Macs on this build. On one, run the dry run —
`uv run python tools/migrate_library.py` (it reads `[library] path`) — and
read its report; then the same with `--apply`. Note the backup folder it
prints (`~/Hyperspace/library-backup-<stamp>/`). Let the Drive sync, then
open a handful of presets on both Macs (a `/5` one — `glimmer-bug`,
`moo`, `displace-moo` — `reeeeeeeel`, a macro preset and three ordinary
ones), and save one untouched.
*Pass:* the dry run lists every preset `→ 6` with `picture: same` and
`fixed point: yes`, and writes nothing; `--apply` says where the backup is
and rewrites them, every file in `presets/` then says
`hyperspace.preset/6`, names and `hidden.json` unchanged; each preset looks
as it did on both Macs; the untouched save changes nothing (the file's
bytes are the same); a second dry run says `leave 58 untouched`.
*Fail:* a preset skipped (the report's last list says why), a look that
moved, a file renamed or lost, a write inside the backup's folder, or a
`/6` that changes when saved untouched (`headless.resave`,
`Presets.document`).

## AG. Plan 36: the WYSIWYG graph

Plan 36 as built is [`36-wysiwyg-graph.md`](36-wysiwyg-graph.md): the graph
on GRAPH is the whole truth. An output shows only its own wires and **All
outputs** is a bus of drawn, rig-owned cables; every hidden edge (pattern
to faces, cover, hands by name, clouds, depth) is a cable; nothing is
filled in at load; presets are `hyperspace.preset/7`; the look-back and
the dream are two picture-in nodes; a **new** preset starts with a shape;
GRAPH has a **preset only** chip. On `plan-36-build`. Run on the copy
(`export HYPERSPACE_HOME=~/Hyperspace-try`), after `uv sync`. Checks 354–358
are the quick wins (PR #241) that this branch is cut from. **A `/7` file
is refused by an older build:** both Macs must run this build before 368.
Register rows 396–416. None of these has been run by a person; the goldens
were recorded on the build machine. (Check 342's "black" is superseded by
362: a new preset now starts with a shape.)

**354. Insert spawns where you click.** (laptop, the copy)
Headless: `tests/test_graph_areas.py`
(`test_insert_effect_lands_where_the_cable_was_clicked`) and the picker's
placement at a point in `tests/test_graph_edit.py`
(`test_nodes_the_picker_adds_and_delete_removes`).
On GRAPH, right-click an empty place and add a node, then add one more
somewhere else.
*Pass:* each new node appears at the pointer, not at a fixed corner and
not on top of another node.
*Fail:* a node that lands elsewhere or covers another.

**355. Nothing moves by itself, and a drag does not snap.** (laptop, the
copy)
Headless: `tests/test_graph_areas.py`
(`test_auto_layout_stacks_each_area_and_keeps_saved_positions`,
`test_a_panned_canvas_moves_every_node_and_saves_where_they_lie`); no test
covers the no-snap drag — that is this check.
Load `party-trip`, open GRAPH, drag two nodes to odd places, load another
preset and come back, then resize the control window.
*Pass:* the nodes you placed stay where you put them, a drag stops exactly
where you let go (no snap to a grid), and nothing is laid out again behind
your back.
*Fail:* a node that jumps on release, on a load or on a resize.

**356. The output behind the canvas.** (laptop, the copy)
Headless: `tests/test_graph_areas.py`
(`test_backdrop_is_letterboxed_and_fixed_to_the_page`,
`test_preview_is_copied_only_on_a_frame_after_the_page_asked`) and
`tests/test_app_boundary.py`
(`test_the_graph_preview_rides_on_output_1_only_when_asked`).
Open GRAPH: **output behind** on its head is on by default. Pan and zoom
the canvas, move the alpha slider, then turn it off and on.
*Pass:* output 1's picture shows behind the nodes letterboxed (its own
aspect, never stretched) and fixed to the window — it does not pan or
zoom with the canvas — and the nodes stay legible over it; the slider
fades it; off, it goes.
*Fail:* a picture that is stretched, moves with the canvas, or hides the
nodes.

**357. The canvas is bigger.** (laptop, the copy)
Open GRAPH at the control window's usual size (960 × 900).
*Pass:* the canvas fills the window below the head and the selection pane;
no node you could place is out of reach.
*Fail:* a strip of dead space or a cut-off canvas.

**358. Trackpad pan, ⌘ zoom.** (laptop, a trackpad)
On GRAPH, scroll with two fingers; hold ⌘ and scroll.
*Pass:* two-finger scroll pans the canvas, ⌘-scroll zooms about the
pointer, and a mouse wheel still behaves as it did.
*Fail:* a scroll that zooms without ⌘, or a pan that fights the zoom.

**359. Rewire output 1 and nothing else changes.** (laptop, the TV for two
windows, the copy)
Headless: `tests/test_plan36_bus.py::test_rewiring_output_1_changes_that_one_port_and_nothing_else`.
Load `party-trip` with both windows open. On GRAPH drag a different
picture (a channel, or an effect's output) onto `output.1.image`. Watch
both windows and the hands layer. Then, with the hands muted on one window
(OUTPUT page), look at that window.
*Pass:* output 1 shows the new picture, and nothing about output 2 or
output 1's hands or guide changes; the hands layer and guide stay laid
over what they were wired to, not over the new picture unless you drag
them there; a muted window shows no hands layer in its chain.
*Fail:* output 1's hands or guide still laid over the new picture without a
cable, or output 2 changing (`graph.window_ports`, `_Build._mute_hands`).

**360. Cut a bus cable.** (laptop, the TV, the copy)
Headless: `tests/test_plan36_bus.py::{test_cutting_a_bus_cable_persists_in_the_show_and_empties_the_port,test_an_undo_puts_a_cut_bus_cable_back}`.
On GRAPH, find the cables from All outputs to the windows. Select the
`output.all.image → output.2.image` cable and press Delete. Save the show,
quit, reopen it. Then undo (⌘Z) once, and drag from All outputs' image pin
onto output 2's image port.
*Pass:* output 2 goes to its ground (black, or see-through in overlay) and
the other cables and windows are untouched; the cut is still there after
reopening; undo puts the cable back; dragging from the pin re-adds it.
*Fail:* a picture still reaching output 2, a cut that comes back on its
own, or a wire cut that you did not select (`graph.RigWires`).

**361. All outputs stays where you put it after "new".** (laptop, the copy)
Press **new**, then drag the All outputs node somewhere clearly different.
Press **new** again, load a factory preset, and load the first one back.
*Pass:* All outputs stays where you dragged it each time; the windows do
too.
*Fail:* All outputs snaps back to a default place (`_moved` in the layout
map).

**362. A new preset shows a shape.** (laptop, the copy)
Headless: `tests/test_presets.py::{test_a_new_preset_is_factory_values_and_the_scene_chain,test_a_new_preset_draws_a_shape}`.
Load `party-trip`, change a knob and a route, then press **new**.
*Pass:* both windows show the shape, plain faces, with the factory's values
and desk; GRAPH shows `shape → scene → All outputs` laid left to right
where you were looking, with the windows and their bus cables; undo takes
you back to `party-trip` in one step.
*Fail:* black windows, a value left over from the loaded preset, or a
chain placed off-screen (`Presets.new`).

**363. Each starter.** (laptop, the copy; a clip for the last)
Headless: `tests/test_graph_starters.py`.
On a new preset, right-click the canvas and pick each of the starters in
turn, undoing after each: scene chain, tracers, tracers + dream, dream on a
picture, a channel to the backdrop. Right-click a cable carrying a picture
and pick tracers and dream there.
*Pass:* each lands as one undo step at the pointer, every node and cable
visible and editable; scene chain shows the shape; tracers shows the shape
with its trail; the dream ones need the worker (check 365); the channel to
the backdrop shows the clip behind the scene. A starter that cannot start
from the cable you clicked says so.
*Fail:* a starter that wires something hidden, lands out of view, or needs
two undos.

**364. Tracers without the dream: the worker idle.** (laptop, the copy,
the dream worker on)
Headless: `tests/test_plan36_lookback_dream.py::{test_tracers_with_the_dream_off_submit_nothing,test_the_tracer_only_group_preset_leaves_the_worker_idle}`.
Load `party-trip` or pick the tracers starter. Watch the shape's trail,
and the dream worker's activity on SYSTEM (or `top`). Switch `dream.on`
off on the dream node if there is one.
*Pass:* the trail shows over the shape; with the dream off or absent the
worker does no work (no submits, no extra load) and the picture passes
through the dream node unchanged.
*Fail:* the worker busy with no dream node on, or the trail missing.

**365. The dream alone, on any picture.** (laptop, the copy, a clip, the
dream worker on)
Headless: `tests/test_plan36_lookback_dream.py::{test_the_dream_alone_on_a_channel_refreshes,test_a_second_dream_is_refused_in_words}`.
Pick **dream on a picture**, or wire a channel into a `dream` node and
the dream into a composite over the scene. Then try adding a second dream.
*Pass:* the dreamed picture refreshes at the dream's own cadence with no
look-back in the graph; with `dream.on` off the input passes through; the
second dream is refused in words and drawn faint.
*Fail:* a dream that never refreshes without a look-back, or two dreams
running.

**366. The live dream look on `party-wake`.** (laptop or the rig, the
dream worker live)
Load `party-wake` with the worker live and compare the look by eye with
how it looked on `/6` (a recording, or the other Mac on the old build).
This is plan 36's known limitation (register row 412, deferred by the
owner): the migrated dream dreams the look-back's occluded trail, not the
raw capture, and D is no longer occluded by the shape.
*Pass:* the look is recognisably the same party look, or the difference is
one you can name; write down what moved so the follow-up (a separate dream
`submit` port and an occluder after the dream) can restore it.
*Fail:* a dream that does not run, or a look you cannot live with.

**367. Preset only, on a factory preset.** (laptop, the copy)
Headless: `tests/test_graph_preset_only.py`.
Load a factory preset (`party-trip`), open GRAPH. Read the head line
(`· N hidden`), then turn **preset only** off and back on.
*Pass:* with it lit only the preset's own nodes, whatever is cabled to
them (a moving param shows its LFO or controller), and the windows with
the bus cables are drawn; the rig's binding cables and uncabled
controllers are not; off, today's canvas returns and nothing moved.
Eyeball what is hidden: **group nodes and the camera hide unless cabled to
a section node**; judge whether any of those should show. The chip stays
as set across preset loads.
*Fail:* a node you expected to see missing, a cable to a hidden node, or a
canvas that lays out again on toggle.

**368. The libraries migrated to `/7`, both Macs.** (two Macs, the shared
library)
Headless: `tests/test_migrate_library.py`.
Put both Macs on this build. On one run the dry run —
`uv run python tools/migrate_library.py` (it reads `[library] path`, the
Drive library) — and read its report; then the same with `--apply`. Note
the backup folder it prints. Let the Drive sync, then open a handful of
presets on both Macs (`party-trip`, `party-wake`, a macro preset, three
ordinary ones) and save one untouched.
What the tool proves: `round-trip picture: same` draws the old file *as
this build loads it* (through the same migration) against its written
`/7` — the save keeps what this build draws, **not** that it draws what
the `/6` build drew. That parity is by eye: for every preset with a
look-back or a dream (`party-wake`, `party-tracer`, your tracer presets)
compare live against the other Mac still on the old build (or a recording) *before*
updating it, as in 366. A preset whose load says `dream.on is driven` or
`dream.mix is driven from 0` (a pad or hand on the tracers) now draws its
trail always and the pad switches only the dream — eyeball those too. An
old file whose section was "not read" is skipped and never written.
*Pass:* the dry run lists every preset `→ 7` with `round-trip picture:
same` and `fixed point: yes`, and writes nothing; `--apply` says where the backup is
and rewrites them, every file in `presets/` then says
`hyperspace.preset/7`, names and `hidden.json` unchanged; each preset
looks as it did on the old build (the dream presets eyeballed as above); the untouched save changes nothing; a second
dry run leaves them all untouched. The build never ran this on your data.
*Fail:* a preset skipped, a look that moved, a file lost, or a `/7` that
changes when saved untouched.

**369. The nine re-recorded goldens, by eye.** (the gate Mac)
Open the pictures for the nine goldens the build re-recorded (register
rows 405, 406, 408, 414): `party-trip`, `party-noita` and `lfo-breathe`
at `|absent|hands+through`; `through-one-output|present|scene+through`;
`palette-glass|…|scene+hands+through`; `wired-outputs` at `scene+hands`,
`scene` and `scene+through` and `present|scene+hands+through`
(`tests/golden/frames/frames.json` names each; `uv run python
tools/golden_frames.py` writes a sheet).
*Pass:* each is what its wiring draws: the absent-hand ones show no hands
layer; `through-one-output` equals its `scene` picture; the `wired-outputs`
and `palette-glass` ones differ from the old ones only at the edges of
the placements, and the `acid.2` one by 1/255.
*Fail:* a picture with hands where the mute is on, or one that moved
visibly.

## AH. Plan 37: nodes as pictures, and the faces

Plan 37 as built is [`37-pictures-and-faces.md`](37-pictures-and-faces.md). On GRAPH, every node that makes a picture is drawn as that picture: a small live thumbnail is made only for nodes that are on screen and drawn. Hovering the picture gives the node's lines, the picture's size and its GPU time. A head chip, **pictures · tint cables**, is off by default and tints picture cables by what flows. An effect is laid in the area of its consumers, so `acid-scene` draws forward. The faces are a dry run: [`assets/37-faces/`](assets/37-faces/) holds a sheet of all 17 modes and the migration map, and nothing is dropped until the owner names the list.

These checks need `plan-37-pictures`. Run them on the copy (`export HYPERSPACE_HOME=~/Hyperspace-try`). Register rows 417–429 and 460. None has been run by a person. No golden moved. Check 375's second half waits for the owner's list and for P2, which follows it.

**370. Every picture node shows its picture.** (laptop, GRAPH, a party preset)
Headless: `tests/test_thumbnails.py` (`test_the_page_draws_a_thumbnail_on_every_picture_node_collapsed_or_not`, `test_a_thumbnail_is_the_pictures_aspect_and_shows_it`, `test_every_picture_kind_has_a_thumbnail_and_the_modulation_side_none`); for the tint, `tests/test_graph_hover.py` (`test_lit_a_picture_cable_takes_its_makers_hue_and_off_it_is_red_again`, `test_the_tint_always_leaves_a_red`, `test_a_real_thumbnails_hue_is_its_pictures_a_frame_later_without_a_texture_read`).
1. Load `party-trip` (or any party preset) and open GRAPH with **preset only** lit.
2. Look at each node of the frame: the channel, the pattern, the scene, the effects, the composites, the look-back and the outputs.
3. On FX, turn an effect's mix up and down.
4. Light **pictures · tint cables** on the head. Wait a second or two, then turn it off again.
*Pass:* every picture node's body is a small moving picture. An effect's picture differs from its input's and follows the mix. The shape shows the scene, faint. Output 1 shows the window, and output 2 shows its window without the hands laid on. With the switch lit, the picture cables out of a yellow-green picture lean orange and those out of a blue-violet picture lean rose. A red, cyan or grey picture's cables stay plain red. Every cable is still clearly red, and none looks like a trigger (amber) or a mask (purple). SYSTEM's fps is unchanged with the switch lit on a 20-node preset. With the switch off, every cable is plain red again.
*Fail:* a black box on a node that draws: its kind is missing from `graphview.THUMBS`, or `render.thumb_source` returned None. A picture upside down: the GL row flip in `ui_graph._thumb`. A frozen picture: the page is not wanting it (`thumb_wants`). Cables that never change: no hues read, either because the thumbnails were never copied or because `want_hues` was not called. A cable that reads as amber or purple: `TINT_SPAN` is too wide.

**371. What the thumbnails cost.** (the show Mac, GRAPH open, twenty nodes on screen)
Headless: `tests/test_thumbnails.py` (`test_graph_picture_is_asked_only_for_the_wanted_nodes`, `test_the_outputs_are_byte_identical_with_and_without_thumbnails`, `test_a_node_behind_an_unpicked_switch_input_is_not_made`).
1. With GRAPH closed, note SYSTEM's frame time and the GPU per-node lines.
2. Open GRAPH and pan until about twenty picture nodes are on screen. Read SYSTEM again: the `thumbnails · N copied · K repainted · M kept` line and the frame time.
3. Light **pictures · tint cables** and read the frame time once more.
*Pass:* N is about twenty, the frame still runs at the show's rate, and the per-node GPU lines are unchanged by the thumbnails, with the tint on or off.
*Fail:* frames dropped while K is high: painted-direct nodes are being repainted at full size (row 426), so try fewer on screen. GPU lines that grow with GRAPH open: the timer is not muted in `Renderer._thumbnails`. A stutter with the tint lit: the hue collect waiting on the GPU (row 428).

**372. Collapse and expand: the thumbnail stays.** (laptop, GRAPH)
Headless: `tests/test_thumbnails.py::test_the_page_draws_a_thumbnail_on_every_picture_node_collapsed_or_not` (its expanded half), `tests/test_graph_legible.py::test_every_node_starts_collapsed_with_at_most_five_lines` (the height).
1. Expand an effect node with **+**, then collapse it.
2. Do the same to a channel whose picture is portrait.
*Pass:* expanded, the picture sits above the ports. Collapsed, the node is the title and the picture. Either way, the column below is not overlapped. The portrait picture is letterboxed in the same 16:9 box, and the layout does not move.
*Fail:* the picture is gone when expanded (the order in `_node`). Nodes overlap (`graphview.height` and `_thumb`'s box disagree).

**373. Hover a thumbnail: the node's lines, the size, the GPU time.** (laptop, GRAPH, a party preset)
Headless: `tests/test_graph_hover.py` (`test_a_picture_nodes_hover_is_its_summary_its_size_and_its_gpu_time`, `test_the_page_finds_the_gpu_time_by_the_render_nodes_name`, `test_a_switch_and_an_unreached_node_say_so_on_hover`, `test_the_page_draws_with_the_switch_lit_and_a_thumbnail_hovered`).
1. Load `party-trip` and open GRAPH.
2. Rest the pointer on the scene node's picture, then on an effect's, then on output 2's.
3. Rest it on the scene node's title.
*Pass:* on a picture, a tooltip with the title, the node's lines ("4 picture ports", an effect's param counts), `1920×1080 picture` (the window's size), and `gpu 0.xx ms` matching SYSTEM's line for that node. On the title, the old hover (the status, or nothing).
*Fail:*
- No tooltip on the picture: `_thumb`'s `is_item_hovered` is not working inside the editor, or `st["thumb_hover"]` is being reset after the nodes are drawn. The fallback is to test the dummy's rect (`get_item_rect_min/max`) against `imgui.get_mouse_pos()` taken to canvas space (`ed.screen_to_canvas`).
- No size line: `VNode.picture` is unset (`_want_thumbs`).
- No GPU line on a timed node: the name differs from `thumb_name`. Compare with SYSTEM's lines.

**374. Hidden: its thumbnail stops being made.** (laptop, GRAPH, SYSTEM)
Headless: `tests/test_thumbnails.py` (`test_the_page_wants_the_picture_nodes_it_draws_on_screen`, `test_wanted_is_made_next_frame_and_dropped_after_a_second_unwanted`, `test_a_node_that_made_nothing_is_dimmed_then_black_after_a_second`).
1. Turn **preset only** off, get many picture nodes on screen, and read SYSTEM's `thumbnails · N copied · K repainted · M kept`.
2. Light **preset only**, or pan nodes off screen, and read the line again after a second.
3. On a switch, pick another input and watch the node behind the input you left.
*Pass:* N drops by the number of nodes no longer drawn, and M follows within a second. The node behind the unpicked input goes grey at once and black a second later. It comes back when you pick its input again.
*Fail:* N unchanged: hidden nodes are still wanted (`drawn_node`, `thumb_wants`). M never falls: `end_frame` is not dropping. The unpicked node keeps moving: the `Graph.pulled` gate in `render.thumb_source`.

**375. The faces: the owner's list, then the FACES page after P2.** (the laptop, then the show Mac)
Headless: `tests/test_faces_map.py` (the map is current); after P2, `tests/test_patterns.py` (the kept modes' table, shader and pixels) and the re-recorded goldens named in P2's commit.
1. Before P2, open `docs/plans/assets/37-faces/sheet.png` and `heart-sheet.png`, and the FACES page with music for METER, PULSE and SPEED. Name the modes to keep. With the list, answer row 417's two questions: renumber or tombstones, and the `preset.py` edit.
2. Read `migration-map.md`'s "nearest kept" for the modes you drop and say whether each is right (row 460).
3. After P2, open FACES. Only the kept modes' chips are there, in the old order, each with its swatch and its one line. The eight inputs' rows are unchanged.
4. Load each preset that the map lists as *on screen* with a dropped mode. Each shows its nearest kept mode, and its card's note says "pattern X was retired; now Y".
5. Turn the desk's pattern knob from end to end. It walks the kept modes only, with no blank stop.
6. With both Macs updated, load a preset from the Drive library that was saved before P2 with a dropped mode. It shows the nearest kept mode, never white faces or the wrong pattern.
*Pass:* every step as described. Until the list arrives, steps 1 and 2 are the whole check.
*Fail:* a dropped mode's chip on FACES: `ui_patterns` still reads the full list. A preset on the wrong pattern: the indices shifted without the value remap (P2's index step). White faces: a stale index reached the shader's fallthrough `return vec4(1.0)`.

**376. `acid-scene` on GRAPH: no cable runs backwards.** (laptop, a scratch home with no `[library]` and no devices)
Headless: `tests/test_graph_areas.py` (`test_no_cable_runs_backwards_across_areas` over every factory preset and every graph fixture, `test_a_node_is_laid_where_its_consumers_are`, and `test_auto_layout_stacks_each_area_and_keeps_saved_positions`, which shows no layout runs by itself).
1. Copy `tests/fixtures/presets/acid-scene.json` into the scratch home's `presets/`.
2. Load it and open GRAPH. If anything was saved, press **tidy** once.
3. Follow acid.2: from the scene into the look-back's picture and its occluder, and on to the composite.
4. Drag acid.2 somewhere else, wait a few frames, then reload.
5. This step shows a known rough edge. In a scratch copy of a user preset that has a saved position for an acid.2-style effect (placed in the EFFECTS region, feeding the look-back), click the LOOK-BACK chip or title.
*Pass:* acid.2 stands in LOOK-BACK, left of the look-back. Every cable out of it runs left to right, and the EFFECTS area starts with the composite. After the drag it stays where it was dropped, through later frames and after the reload. In step 5, the saved effect keeps its position in the EFFECTS region but now belongs to LOOK-BACK, so LOOK-BACK's frame reaches over to it. Judge whether that reads acceptably. One **tidy** ends it (row 429).
*Fail:* acid.2 in EFFECTS with a cable curling back into the look-back (`laid_areas` is not applied in `build`). A node that jumps back after a drag (a layout running by itself).

## AI. Plan 38: hold the projector

Plan 38 as built is [`38-hold.md`](38-hold.md): **hold** (first on GRAPH's
head, or `output.hold` on a desk button) keeps every output on the wiring
and the look as they were at the press, still moving with the music, while
every edit lands as the preview behind GRAPH's nodes, with a red-framed
PROJECTOR inset showing what the room sees; **take** cuts the preview onto
the projector, **drop** goes back to the hold point as one undo step. On
`plan-38-hold`, then `plan-37-38-39-integration`. Run on the copy
(`export HYPERSPACE_HOME=~/Hyperspace-try`), after `uv sync`. No schema,
preset or golden changes. Register rows 430–439 and 461–470. None of
these has been run by a person; the headless tests are all in
`tests/test_hold.py`.

**377. Hold keeps the projector while a new preset is started.** (the rig,
projector up, GRAPH open, music playing)
Headless: `tests/test_hold.py::test_on_gl_the_program_draws_the_held_wiring_while_a_graph_edit_lands`,
`::test_on_gl_the_projector_keeps_the_held_frame_while_the_preview_shows_the_edit`,
`::test_on_gl_a_blank_graph_landed_while_held_leaves_the_projector_whole`,
`::test_a_landing_while_held_keeps_the_programs_effects_switches_and_resizes`,
`::test_the_program_draws_the_held_look_and_the_live_one_comes_back`,
`::test_held_the_outputs_draw_the_program_and_the_preview_follows`.
1. Load a moving look that has an effect and a switch (`party-trip`).
2. Press **hold**, the first chip on GRAPH's head.
3. Press **new** on the PRESET strip.
4. Right-click near the canvas's top-right corner to open the node picker.

*Pass:* the projector keeps the old look, its effect and switch pick
included, and keeps moving with the music. GRAPH's backdrop shows the new
preset's shape. The PROJECTOR inset, framed in red in the canvas's corner,
shows the old look, oriented as output 1, and the head shows the red
`HELD 0:0x — …` line. The inset sits over the picker in step 4 (row 469:
known, judge whether it is in the way).
*Fail:* the projector goes black, which points to `Hold.program` not being
around `draw_outputs` in `app._draw_render`. The projector loses its
effect or switch pick at **new**, which points to `GraphSection._settle`
not asking `hold.keep` (`hold.section` unset in `app.main`). The inset is
missing, which points to `monitor` not wanted, or output 1 not publishing
into it.

**378. Building a scene during a hold shows only behind GRAPH.** (same)
Headless: `::test_on_gl_the_program_draws_the_held_wiring_while_a_graph_edit_lands`,
`::test_a_bus_cable_cut_after_the_hold_stays_off_the_projector`,
`::test_on_gl_a_bus_cable_cut_after_the_hold_stays_off_the_projector`,
`::test_the_canvas_reads_the_previews_graph_while_held`,
`::test_the_head_line_says_how_long_and_what_changed`; and
`tests/test_hold_thumbnails.py` (step 5: the thumbnails while held).
1. While held, wire shape → scene → All outputs.
2. Insert an effect on the scene's cable; delete one the projector shows.
3. Cut the bus cable into output 2's picture.
4. Save the preview as a new preset; load it again after Take.
5. Before Take, with GRAPH open, look at the nodes' pictures, then at
   output 1's node beside the PROJECTOR inset.

*Pass:* the backdrop shows the new scene with its effect, and the
projector does not change, not even at the delete. The head line counts
the changed settings and says "the graph changed". After step 3, output 2
is black in the preview only. The dormant and refusal lines on GRAPH talk
about the preview. The saved preset has no values for the projector's
leftover effects (no note about unknown ids on reload). In step 5 the
nodes' pictures show the preview (the new effect's node shows its own
picture), while output 1's node shows the same picture as the PROJECTOR
inset (rows 498, 499).
*Fail:* the projector shows the edit, which points to the held wiring or
held rig cables not applied in `Hold.program`. The preview still feeds
output 2 after the cut, which points to `rig_source` missing from
`hold.MIRRORED`. A new node shows a stand-in ref, which points to a read
of `panel.renderer._graph` not going through `hold.canvas_renderer`. The
reload notes unknown ids, which points to `Presets._values` not leaving
out `Hold.program_only()`. Node pictures that show the projector's look in
step 5 point to `ui_graph.picture_sources` not reading through
`hold.canvas_renderer`.

**379. Take cuts the preview onto the projector.** (same, look-back on)
Headless: `::test_on_gl_the_program_draws_the_held_wiring_while_a_graph_edit_lands`
(after Take the outputs show the edit's frame),
`::test_take_lets_go_and_the_program_is_what_is_landed`,
`::test_an_effects_clock_runs_on_through_hold_land_and_take`,
`::test_a_load_while_held_resets_the_previews_delays_and_the_projectors_at_take`.
1. After 378, turn the look-back on so that trails show.
2. Press **take**.
3. Hold a look with an echo, load another preset with GRAPH open, watch
   the projector, then press **take**.

*Pass:* the projector cuts to the new scene in one frame and the
look-back's trails carry on through the cut; the red line goes and
**hold** is back. In step 3 the projector's echo keeps trailing through
the load, and starts empty only at Take. Say whether the cut reads as
harsh (row 430).
*Fail:* a frame of black or a flash, which points to a graph rebuild on
the program renderer losing its frames. The trails restart, which points
to the look-back's history cleared on a rebuild. The projector's echo
cuts at the load, which points to `Presets.load`'s delay reset not going
through `gs.hold`.

**380. Drop goes back as one undo step.** (same)
Headless: `::test_drop_after_a_whole_new_look_is_one_undo_step_back_and_one_forward`,
`::test_drop_goes_back_to_the_hold_point_as_one_undo_step`,
`::test_drop_puts_a_bus_cable_cut_during_the_hold_back`,
`::test_drop_after_a_landing_while_held_brings_the_programs_nodes_back_whole`,
`::test_an_undo_after_take_brings_no_program_only_instance_back`.
1. Note the preset's name and dirty dot.
2. Press **hold**.
3. Turn three knobs, rewire on GRAPH and cut a bus cable.
4. Load another preset from the strip and turn a knob on it.
5. Dim the room (eye / output).
6. Press **drop**.
7. Press ⌘Z once.

*Pass:* after step 6 the canvas, the knobs, the cut cable and the strip's
name return to what the projector shows, and the dirty dot is as in step
1. The projector never changes, and the dim from step 5 stays. After step
7 the other preset comes back with its edits and its dirty dot in one
press, and the dim still stays.
*Fail:* the knobs stay moved: undo not handed to the hold (`Hold.undo`).
The dim reverts: `hold._preset_part`. ⌘Z brings back only part of the
state and needs a second press: Drop pushes more than one step.

**381. The desk buttons light while held.** (the rig, APC40)
Headless: `::test_learned_desk_buttons_light_while_held`,
`::test_the_output_controls`.
1. With no hold on, learn `output.hold` and `output.take` onto two free
   desk buttons.
2. Press the hold button.
3. Press the take button.
4. Hold again, then press **drop** on GRAPH.

*Pass:* both LEDs are on while held, and dark after take and after drop.
The press that learns a button does not hold. (A button learned *during*
a hold is unlearned by Drop: row 438. Learn before holding.)
*Fail:* the take LED stays dark while held, which points to its `lit=`
callback not read by `routing.led_lit`. A learning press engages the hold.

**382. The preview's cost while held.** (show Mac, GRAPH open, SYSTEM page)
Headless: `::test_held_with_the_page_closed_draws_no_preview`,
`::test_preview_size_keeps_the_aspect_under_both_caps`,
`::test_the_preview_renderer_reads_what_the_main_one_does`.
1. Hold with GRAPH open and note the FPS.
2. Close GRAPH and note it again.
3. Wire a Syphon or NDI input into the preview.

*Pass:* the FPS drop with GRAPH open is acceptable; the preview is at
most 1280 px on its long side. With GRAPH closed the FPS is as unheld. A
Syphon/NDI input shows in the preview (it may stutter), and the
projector's copy stays smooth.
*Fail:* the FPS falls with the page closed, which points to
`_draw_preview` running without `preview.take()`. The projector's Syphon
input stutters, which points to the second read starving the first.

**383. A band still pumps a held param.** (the rig, music)
Headless: `::test_a_modulated_param_rides_its_held_base`,
`::test_the_turns_speed_and_planes_are_not_held`.
1. Route a band to `view.bright`.
2. Press **hold**.
3. Move `view.bright`'s base on the desk.
4. Turn the speed knob.

*Pass:* the projector keeps the held brightness and still pumps with the
band. The preview shows the new base, pumping too. The speed change in
step 4 turns both, and the red line does not count it (row 431).
*Fail:* the projector stops pumping, which points to
`hold.program_value` not adding this frame's offset. The projector jumps
to the new base, which points to the param not held (`hold.held`).

## AJ. Plan 39: vision

Plan 39 as built is [`39-vision.md`](39-vision.md): `segment` (any picture
in; `segment.fg`, `segment.bg` and `segment.mask` out; Apple Vision on the
Neural Engine, torchvision behind it, a motion mode with no model),
`matte` (picture → mask) and `cut` (picture + mask → picture), the mask its
own purple wire that never rides in alpha (wired into a picture port it
reads white where it passes, black elsewhere), `edges` as an effect file,
and the cut-through blend made honest. On `plan-39-vision`. Run on the copy
(`export HYPERSPACE_HOME=~/Hyperspace-try`), after **`uv sync`** (it adds
`pyobjc-framework-vision` on macOS). The first camera open asks for camera
permission: allow it. **A preset with `segment`, `matte` or `cut` reads as
black with a note on an older build:** both Macs run this build before such
a preset is shared. Register rows 440–459 and 471–497. None of these has
been run by a person; the goldens were recorded on the build machine, and
the two real-model tests ran once each on a synthetic frame. Until GRAPH's
picker is in front of you, every node here can be added from right-click →
**media ▸** (segment) or **masks ▸** (matte, cut), or as an entry in the
preset's file (`{"kind": "segment"}`).

**384. A webcam segmented by person: the dancer over the polytope, then the
room with a person-shaped hole.** (the show Mac, the camera, the copy)
Headless: `tests/test_graph_segment.py`
(`test_fg_bg_and_mask_from_a_known_matte`,
`test_a_rows_top_first_matte_lands_the_right_way_up_everywhere`,
`test_the_shortcut_for_a_channel_with_pixels_and_the_readback_for_one_without`,
`test_before_the_first_matte_fg_is_the_picture_whole`,
`test_a_scene_through_a_segment_turned_off_shows_the_under`);
`tests/test_plan39_graph.py` (`test_the_cut_out_on_the_scene_chain`,
`test_a_second_cut_out_is_refused_nothing`,
`test_every_segment_instance_draws_its_pins_and_their_cables`);
`tests/test_segment.py::test_vision_runs_once_on_a_synthetic_frame` (live
tier: `--all`). For the hold step: `tests/test_hold.py`
(`test_a_landing_while_held_keeps_the_programs_mattes_cuts_and_segments`,
`test_a_knob_turned_on_a_held_matte_cut_or_segment_stays_off_the_projector`,
`test_drop_after_a_blank_landing_brings_the_mattes_cuts_and_segments_back`,
`test_every_kind_a_landing_settles_has_its_program_ids`), on the
integration branch.
1. Put the camera on channel a (MEDIA).
2. On GRAPH, in a preset with the scene chain, right-click empty canvas →
   starters ▸ **cut-out**. A Segment and a Composite appear left to right
   where you clicked, cabled `channel.a → segment.image`, `segment.fg →
   composite.over`, `scene → composite.under`, `composite → All outputs`;
   the status line says what fed All outputs before ("… — in place of scene
   into All outputs"). Check the picker: **media ▸** lists segment, **masks
   ▸** lists matte and cut.
3. Stand in front of the camera.
4. Rewire `segment.bg → composite.over`.
5. Wire `segment.mask → output.2.image`.
6. Turn `segment.on` off, then on.
7. Starters ▸ cut-out again: `segment.2` and `composite.2` appear with
   `segment.2`'s fg, bg and mask pins and their cables drawn. Undo once: the
   second group is gone.
8. (With plan 38 on the same build.) With step 3's look on the projector,
   press HOLD, then New (a blank graph); turn a knob on the held segment;
   press DROP; then HOLD, New, save to a scratch name, TAKE.
*Pass:* at step 3 you are over the polytope and the room is gone; the cut
sits on you, the right way up, not mirrored, not beside you, within a frame
or two; the node says `256×144 · Vision fast · a frame or two late · ~30
fps`. At step 4 the room shows with a person-shaped hole and the polytope
through it. At step 5 output 2 shows your white silhouette on black. At
step 6 the scene shows over the camera's room unchanged while off. At step
7 every node and cable is visible, nothing refused, one undo per starter.
At step 8 the projector keeps the cut person, live, until TAKE, the knob
moves only the preview, DROP brings the three nodes back with their values,
and the scratch save holds no `segment.*` ids when the live graph has none.
*Fail:* upside down (the flip flag: rows 474, 480); squashed, offset or
beside you (the aspect resample or the shortcut's cover condition: rows
480, 481); the whole picture and the node waiting or in error (the backend:
`[segment] backend`, the camera permission, `uv sync`); a segment.2 cable
missing (row 493); the scene changing when `segment.on` goes off (row 477);
at step 8 the projector going black or uncut at New (a declare outside
`_settle`: row 495), a knob moving the projector (`HELD_GROUPS`: row 496)
or the save writing the ids (`PROGRAM_IDS`: row 495).

**385. `segment.quality` fast → balanced → accurate at the machine.** (the
show Mac, the camera)
Headless: `tests/test_graph_segment.py::test_the_shortcut_for_a_channel_with_pixels_and_the_readback_for_one_without`
(a new level is a new submit); `tests/test_segment.py::test_the_levels_and_the_input_sizes`.
1. With 384 running, step `segment.quality` through its three values.
2. Watch the edge and the hair, the node's fps and the SYSTEM page's frame
   time.
*Pass:* each level gives a finer edge; the node's rate falls roughly as
measured (Vision about 4 / 14 / 36 ms a frame: about 30 / 30 / 25 fps from a
30 fps camera); the render's frame time does not move (the model runs on
the Neural Engine, off the frame thread).
*Fail:* the frame time rises with the level: the worker is blocking the
frame thread, or the readback is taken every frame (row 481).

**386. `segment.feather` and `segment.smooth` by eye: the halo and the
flicker.** (the show Mac, the projector, the camera)
Headless: `tests/test_segment.py` (the worker);
`tests/test_graph_segment.py::test_smooth_near_one_still_reaches_the_new_matte`;
no pixel test of the feather on a live matte (`tests/test_graph_masks.py::test_the_feather_widens_the_edge_in_one_channel`
is the matte's).
1. With 384 running, raise `segment.feather` from 0 to 8.
2. Raise `segment.smooth` from 0 to 0.6 and wave a hand; then to 0.95, step
   out of frame and wait.
*Pass:* at 1 the edge softens, the steps of the 256-wide matte vanish and a
halo widens; at 2 the flicker along the edge calms, at the cost of a
trailing edge on fast moves, and at 0.95 you fade out fully within some
seconds.
*Fail:* the feather does nothing (the feather pass not reached); `smooth`
leaves a frozen ghost where you stood (the matte re-quantised per result:
row 488).

**387. Motion mode on a still camera: the walker is foreground and fades in
when still.** (the show Mac, the camera on a tripod)
Headless: `tests/test_graph_segment.py::test_motion_on_two_stills_makes_the_moved_region_foreground`;
the `segment-motion` goldens (`tests/golden/frames/png/0af84155993b2d4b.png`).
1. With 384's wiring, set `segment.mode` to motion.
2. Walk through the frame.
3. Stand still for `segment.learn` seconds (3 by default).
4. Move again. Then raise `segment.sense` a little.
5. Turn a party light on and sweep it across the room.
*Pass:* at 2 the walker is foreground and the still room is cut away; at 3
you fade into the background over about `learn` seconds; at 4 you return at
once, and a higher sense drops small changes (noise, shadows); at 5 the
swept area is foreground until it is learnt (expected: row 482).
*Fail:* everything foreground and staying so (the background not learning:
`LEARN_FS`, `motion_pair` not turning); nothing ever foreground (`sense` too
high, or the first frame learnt every frame).

**388. A matte from luma on a still, a kaleido branch cut by it, over the
scene: the owner's "image as a mask".** (the dev Mac, then the show Mac)
Headless: `tests/test_graph_masks.py` (`test_luma_passes_the_bright_half`,
`test_the_key_moves_where_a_pixel_passes`,
`test_soft_widens_the_edge_and_invert_flips`,
`test_the_feather_widens_the_edge_in_one_channel`,
`test_an_asymmetric_picture_lands_the_right_way_up`,
`test_an_own_sized_mask_lands_on_the_cover_where_its_picture_shows_it`);
`tests/test_graph_cut.py` (`test_the_hole_is_transparent_before_any_composite`,
`test_the_under_shows_through_the_hole`,
`test_amount_a_half_dims_the_cut_part_by_half`,
`test_invert_keeps_the_hole_and_cuts_the_rest`,
`test_no_mask_is_the_picture_untouched`,
`test_the_mask_of_an_asymmetric_picture_lands_on_the_right_rows`,
`test_a_cut_is_transparent_to_laid_over_ness`,
`test_the_under_shows_where_a_laid_over_scene_draws_nothing`); the
`cut-out` goldens (`tests/golden/frames/png/a0abb485a6c1ca6a.png`).
1. Load the `cut-out` fixture through a scratch library
   (`tests/fixtures/presets/cut-out.json`; channel a is
   `backdrop-still.png`). Every window shows the polytope; inside the
   still's white disc (right of centre) it shows the scene through the
   kaleidoscope instead.
2. In your own preset do the same with any still from the media folder:
   the still on channel a; from masks ▸ a matte and a cut, and a composite;
   wire `channel.a → matte.image`, `matte → cut.mask`, `scene →
   kaleido.image`, `kaleido → cut.image`, `cut → composite.over`, `scene →
   composite.under`, `composite → output.all.image`.
3. Turn `matte.key`: the kaleidoscope area follows the bright parts. Raise
   `matte.soft`, then `matte.feather`: its edge greys, then softens. Set
   `matte.from` to chroma and turn `matte.hue` onto a colour in the still.
4. Turn `cut.amount` from 1 to 0.5.
5. Turn on `cut.invert`.
6. Unwire `matte → cut.mask`.
7. Optional: wire `cut → output.2.image` instead of through the composite.
*Pass:* the kaleidoscope shows only where the still is bright (or the keyed
colour), the right way up; inside the disc the scene under it shows
through the kaleidoscope's empty space, not black; at 4 the kaleidoscope
comes back at half strength over the scene outside the bright parts; at 5
it shows everywhere but the bright parts; at 6 it covers the whole window,
untouched; at 7 output 2 shows the kaleidoscope in the bright parts and
the window's black elsewhere. Every knob acts live, without a stutter.
*Fail:* the cut area upside down or mirrored (a sampler flip: row 474);
the scene not showing outside the bright parts (the cut not transparent,
or the composite not "over"); the cut area stretched against the still
(cover fit missing: row 454); black inside the disc (laid-over-ness not
passed through the cut: row 477); a knob that does nothing (the value not
landing in `ViewState.mattes` / `.cuts`); a stutter on the feather (the
blur's cost: row 455).

**389. A matte wired straight into an output shows white where it
passes.** (the dev Mac)
Headless: `tests/test_graph_masks.py`
(`test_the_promotion_is_at_the_consumers_size_by_cover`,
`test_the_promote_pass_fits_by_cover`); the `mask-as-picture` goldens
(`tests/golden/frames/png/2e75409c8ea40738.png`);
`tests/test_plan39_graph.py`
(`test_a_promoted_mask_cable_is_purple_into_a_red_port`,
`test_a_segment_s_mask_pin_is_purple_its_pictures_red`);
`tests/test_hotreload.py` (the `MODULES` order and the cold set) for the
last step.
1. Load the `mask-as-picture` fixture through a scratch library
   (`tests/fixtures/presets/`): channel a's `backdrop-still.png` → `matte`
   (luma, key 0.95, feather 4) → `output.all.image`.
2. Look at the cable from the Matte to All outputs; collapse the Matte.
3. Wire `matte → acid.2.image` (acid.2 on) and acid.2 into the output
   instead.
4. Try to wire `channel.a` straight into a cut's `mask`.
5. With the app running, change a comment in `hyperspace/masks.py` and
   save.
*Pass:* every window shows a soft white disc where the still's white
circle is, on black, opaque, filling the window by cover, the disc on the
right as in the still; the cable is purple end to end into All outputs'
red image pin (channel a → matte.image red), and stays purple collapsed;
the effect bends the disc as it would any picture; step 4 is refused in
words ("… makes a picture, cut.mask takes a mask — put a matte between");
at 5 no error line, and the matte keeps drawing. (A promoted mask wired
into `lookback.occluder` or `composite.over` is an opaque picture
everywhere, so it covers what is under it: that is not a cut — use `cut`.)
*Fail:* a red-tinted or transparent picture (the promotion reading the
mask's one channel as RGBA: row 453); a stretched disc (not cover); the
wire refused (the type rule); a red cable (the cable typed by its port: row
492); at 5 an import-order error (`masks` after `render` in
`hotreload.MODULES`: row 459).

**390. Edges on the scene, on the camera, and into a cut.** (the projector
rig or the laptop, GRAPH page)
Headless: `tests/test_fx_edges.py` (params, flat → black, a vertical edge,
threshold, glow, direction hues);
`tests/test_fx.py::test_each_effect_changes_the_frame[edges]` and
`::test_every_effect_runs_on_the_face_target[edges]`; the `edges-scene`
goldens (`tests/test_golden_frames.py`).
1. Load any scene preset. On GRAPH wire `scene → edges → output.all.image`
   and switch edges on (it is on the FX page like any effect). The
   polytope's lines show as thin white outlines on black.
2. Sweep **Threshold** 0 → 1: at 0 every soft gradient of the faces'
   pattern shows; around 0.2 only the lines; near 1 almost nothing.
3. Raise **Glow** to 4: each line gains a halo a few pixels wide, as bright
   as the line.
4. **Colour** → source: the outlines take the scene's colours (on a dark
   edge with something under it, an opaque black line: row 450). →
   direction: lines facing different ways turn different hues, and the hue
   turns as the polytope rotates.
5. Wire a camera channel into `edges` instead: the room's edges (door
   frames, furniture, people's outlines) draw as lines, steady at the
   default threshold.
6. Wire `edges → matte (luma) → cut.mask`, with `pattern → cut.image`, into
   an output: the pattern shows only along the lines.
*Pass:* 1–6 as written, no GL error on the SYSTEM page, the frame rate
unchanged (a 9-tap pass).
*Fail:* a flat area that is not black (the threshold or the
premultiplication); lines at the frame's border (`src()` mirroring broken);
direction all one hue (the `atan` arguments swapped or the glow swamping
it); camera edges sparkling everywhere (noise above the threshold: raise
it; a pre-blur is the follow-up); in 6 the pattern everywhere (the matte
reading alpha, not luma, or the promotion missing).

**391. Two cameras, two segments: both run; the frame time on the show
Mac.** (the show Mac, two cameras)
Headless: `tests/test_graph_segment.py`
(`test_a_removed_node_closes_its_worker`,
`test_several_segments_are_several_workers`);
`tests/test_plan39_graph.py::test_every_segment_instance_draws_its_pins_and_their_cables`.
1. Camera 1 on channel a, camera 2 on channel b.
2. Add `segment` and `segment.2` (media ▸ twice), with `channel.a →
   segment.image` and `channel.b → segment.2.image`, each `fg` over the
   scene on its own output.
*Pass:* both cut their own person, each node says its own rate; the frame
time stays within the show's budget (the SYSTEM page); two threads named
`segment-segment` and `segment-segment.2` exist (Activity Monitor's sample,
or `py-spy dump`).
*Fail:* one starves (the Neural Engine is shared: read both rates); the
frame time spikes (something reading back on the frame thread: row 481).

**392. Unplug the camera mid-show: the node says so, the picture passes
through whole, nothing crashes; plug it back and it resumes.** (the show
Mac, the camera)
Headless: `tests/test_graph_segment.py`
(`test_a_channel_with_no_frame_says_so`,
`test_an_error_mid_show_passes_the_picture_whole_and_says_it`);
`tests/test_segment.py` (`test_an_error_is_said_and_the_next_result_clears_it`,
`test_stop_never_waits_and_the_backend_closes_on_its_thread`).
1. Run 384.
2. Unplug the camera.
3. Plug it back.
4. Delete the segment node; then quit the app.
*Pass:* at 2 the node says `no frame on channel a: its picture through,
whole` and the output shows what channel a now gives (the empty channel's
black), with no crash and no stall; at 3 the feed and the cut return within
a second or two; at 4 the frame does not hitch and the app quits within a
second or so.
*Fail:* the app stalls (the worker or its close blocking: row 497); the
last matte frozen over a black channel (the node not checking that its
input reads: row 483); the cut not resuming (the frame-id "moved" check
stuck).

**393. A half-transparent face over a bright backdrop, cut-through on and
off.** (the projector, an opaque window)
Headless: `tests/test_media_render.py::test_a_half_transparent_scene_over_white_is_honest_on_an_opaque_window`;
`tests/test_lookback.py` (`test_cut_through_never_cuts_an_opaque_ground`,
`test_cut_through_still_cuts_in_overlay_mode`). Also open the eight
re-recorded goldens (`backdrop-still` and `media-chain-backdrop` at
`present|scene`, `scene+through`, `scene+hands`, `scene+hands+through`;
`tests/golden/frames/frames.json` names them).
1. Put a white or bright still on channel a. On GRAPH wire `channel.a →
   composite.under`, `scene → composite.over`, `composite →
   output.all.image`. For a second pass, put the same still on the
   backdrop and wire `scene → backdrop.scene` explicitly.
2. Faces on, lines and points off, a pattern with translucent fills.
3. Flip `view.cut_through` on and off a few times on the projector.
*Pass:* nothing changes; the faces sit over the white at their own
opacity, their colour readable; the eight goldens show the faces at their
own opacity over the backdrop, not washed toward white.
*Fail:* the faces wash out toward white, or brighten with the switch on:
the cut-through blend is being taken for a zero ground again
(`render.draw_scene`'s blend choice: row 448).

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
  a real screen (216–218);
- a placed effect through a presenter (223, 224, 227, 231): the tests
  prove the projector's hand-over is the folded texture by identity,
  never that a half-float texture shows right in a real second window;
  and whether the folded hands' colour reads as meant at distance (223);
- whether the palette's compression reads as the owner described it —
  the whole picture as shades of one red, a yellow slice with its
  derivations — and how slices wider than 180° look (267–269): the tests
  prove every output colour lies inside the slice on a synthetic
  rainbow, not what a person sees on a projector;
- the SYSTEM page's per-effect split (220): on the Mac's tile GPU a
  line can carry its input's work, so only "a line per effect that ran"
  is pass or fail;
- every gesture on the GRAPH page (242–258): the tests drive its
  functions and draw the real widget headless, but cannot move a mouse
  on it — a drag, a Delete, a right-click's subject, a node dropped on a
  cable;
- the lag's removal by eye (232) and a patch felt with a real hand
  (241, 249): the equivalence test proves the values a frame earlier,
  not the feel;
- two Macs on one shared library with this run's keys (259): no test
  runs an older build against a file this one saved (the review pass did,
  once, by hand: register row 277), nor a `/3` or `/4` preset (285, 301, 317);
- the frame rate of thousands of copies on the Mac's GPU (277): the tests
  draw on Mesa's software rasteriser;
- whether the sequencer *feels* tight against music (282): the tests prove
  every step fires once at its exact clock time on a deterministic clock,
  not what a person hears and sees at 175 BPM;
- the SEQ page and the 7-to-16-LFO page at distance and their frame time
  at the caps (280, 281): nothing has measured 16 LFOs and 16 envelopes;
- the APC40 sequencer page on a real mk1 (286–295, on `plan-31-a1`): the
  fake-port rig proves the messages, never the yellow, the red, the scene
  blink or the flicker, and models no Generic-mode fall-back;
- NDI and Syphon with a real Resolume or TouchDesigner, in and out, and NDI
  over a network from a second Mac (304–309): the tests run our sender into
  our receiver in one process; `extra_ips` through the app's own NDI config
  file is unverified (307);
- an NDI camera app on a real phone (312), a webcam through the macOS
  permission prompt on a second Mac (311), and a published window after a
  resize or a DPI change (310);
- the look of a backdrop under the scene with the look-back and cut-through
  (296), and `displace` and `blend` at distance (297): the goldens were
  checked by eye on one still;
- scrub and the cue knob's jog as a performer feels them (298, 299), and
  a Drive placeholder going `fetching` then `ready` (300);
- the MEDIA page at arm's length with a big library (303), and the frame
  cost of three playing clips, eight channels and NDI out's ~4 ms (298,
  303, 309): the smoke runs were on the dev machine only;
- every gesture on GRAPH that edits the free graph (318, 320, 325, 326): an
  effect dragged onto a cable, a drop beside one, the faint "reaches
  nothing" node, a right-click on a render cable; the tests drive
  `Edit` and `ui_graph.dropped` and draw the widget headless;
- a knob on `switch.select` on a real APC40 (319), and the look of a clip
  through two effects on the faces and a camera through `kaleido` behind
  the scene (318): the goldens were checked by eye on one still each;
- a lost channel on the faces (323) and the frame cost of branches, the
  faces branch and an eight-way switch (324): the tests count makes on
  Mesa and never time a tile GPU;
- the FX page with a dozen effects at arm's length (327), and a `/5` file on
  an older build (328): the ladder refusal is tested against the loader,
  not the old app;
- the wired frame at the machine (342–352): the owner's delete sequence
  with a mouse (343), a library preset by eye on both Macs (345), the
  OUTPUT page's tighter spacing at distance (346), the glass's picture
  mute and the two owner notes — a picture mute hides the through picture,
  and on an in-scene preset it shows the ground and the guide, not the
  hands layer (347) — hands through the effects on a projector (348), the
  frame cost on a tile GPU (351) and a `/6` file on an older build (352):
  the tests draw the pages headless and count passes, and the goldens pin
  741 pictures on the gate Mac;
- the owner's library on both Macs after `tools/migrate_library.py --apply`
  (353): the tool's tests run on a scratch library and its picture check
  on the golden rig, never the Drive sync or the other Mac.
- the WYSIWYG graph at the machine (354-369): the quick wins' feel with a
  trackpad (358), output 1 rewired with the hands layer watched (359), a
  cut bus cable across a save and reopen (360), the starters and the
  dream with the worker live (363-366: `party-wake`'s look against `/6`
  is the owner's deferred follow-up), what "preset only" hides (367), and
  the nine re-recorded goldens by eye (369): the tests draw the pages
  headless and the pictures were recorded on the build machine;
- the Drive library migrated to `/7` on both Macs (368): the tool's tests
  run on a scratch library, never the Drive sync or the other Mac.
- nodes as pictures at the machine (370–376). The tests copy thumbnails on a standalone context and draw the page headless. Only a person can judge:
  - how the thumbnails read at the canvas's zooms, and the faint shape (370);
  - the tint by eye (370);
  - the thumbnails' cost on the show Mac (371);
  - the hover inside `imgui_node_editor` (373), which the tests drive through a stand-in;
  - that the control window sees this frame's thumbnails (`_thumbnails` flushes);
  - the face patterns themselves (375), which only the owner can name;
  - the moved effect's area frame on a preset saved before plan 37 (376).
