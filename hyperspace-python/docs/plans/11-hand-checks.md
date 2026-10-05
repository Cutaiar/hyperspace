# Plan 11 — Hand checks at the machine

Everything only the owner can verify, in the order that costs the least
time at the machine: laptop alone first, then the APC40, then the camera
and the box (APC40 still plugged in for check 24), then the projector,
then IAC + FL Studio, then one back on the laptop, then plans 12 and 13's two, then plan 13's group H (plan 13 is built on `plan-13-integration`), then plan 14's group I and the ghost hands' group J, then plan 15's group K (undo, home, the master dim, save-as on the desk; built on `finish-line`), then plan 16's group L (the cheat sheet off at launch, the FX chips, an idle effect's strip, where the windows open, instances to zero, the dream's layer; checks 58–63, the projector for 61), then plan 17's group M (one Unbind, Learn desk / Learn hand ▸ left / right, the menu on a label and on every meter, the desk big and clickable, the ROUTING filter; checks 64–71, the APC40 for 65, 67 and 70, the camera for 65–67 — run it **after check 72**, which sets the box its hand checks sit in), then plan 18's group N (the interaction box, what a hand Learn lands with, knob smoothing, `hands-orbit`; checks 72–80, the camera for all of it, **calibration first**: check 72 sets the box every later hand check now sits in), then plan 19's group O (twenty-four presets, rows 4–5 of the desk as the bank and their lights, the device knobs re-cut, hide / rename / the trash, the dirty dot and "save copy", the home in git; checks 81–90, **on a copy of `~/Hyperspace`**, the APC40 for 82, 83 and 85), then plan 20's group P (effects aimed at the faces, per face or in screen space; dragging an effect's chip to reorder; the look-back page as ECHOES, DREAM and BOTH; dream speed; instance layouts; checks 91–98, the projector and the glass for 98). Each check: the commands, the config, the preset,
what to do, what a pass and a fail look like, and which audit item or
code path a fail points at. Where a check can be simulated headless, the
pytest node or `tools/` command that shows the expected behaviour is
listed first — run it before touching hardware so you know what "right"
looks like. Written against `plan-11-integration` (778 tests); revised
for plan 13 on `plan-13-integration` (872 tests): F1–F8 load the open
project's bank of **presets**, the ROUTING page is one page over the
loaded preset, and `bindings.json` holds only the session's controls.

**Before you start.** `git pull`, `uv sync`, `uv run pytest -q`. Your
`~/Hyperspace/config.toml` today has `[midi] enabled = true`, `[output]`
commented out, four keys under `[overlay]`, `[bridge] enabled = false`,
`[dream] enabled = true`, `[hands] enabled = true, mode = "desktop"`. Keep
it; checks that need a change say so, and say to put it back. Log a fail
as a new AUDIT row dated with plan 11, with the check number.

## A. Laptop alone (nothing plugged in) — about 40 minutes

**1. Windowed smoke after the frame refactor (P5).**
Headless first: `uv run pytest -q tests/test_app_boundary.py::test_the_frame_runs_in_the_documented_order`.
Then `HYPERSPACE_FRAMES=3 uv run hyperspace`. *Pass:* both windows open,
three frames, clean exit, nothing on stderr but the adapters' one-line
notes. *Fail:* a traceback, or the process not exiting → `app.frame` /
`app.Host` (WP14, PR #48); a stderr note from an adapter that should be
silent → that adapter's `_open_*` gate.
Then `uv run hyperspace` once more: the rig opens the party show (PRESETS
page: SHOW `party`, starts on TUMBLE — plan 14 WP3), R resets the camera,
F1 loads preset 1 (TUMBLE), ⇧F1 saves the live state as it (a user file
shadowing the factory one), `T` does nothing (overlay is off unless
`[output] overlay = true`, decision 21), ⌘R restarts without resetting the camera first, and the
cheat sheet (`/` — press `/` first: it is off at launch since plan 16,
check 58) names all twenty-two rows — R, F1–F8, ⇧F1–F8 (WP7),
and since plan 15 ⌘Z / ⌘⇧Z / Ctrl+Z / Ctrl+⇧Z on its "Cmd+Z" line
("undo · ⇧ redo (or Ctrl+Z)") and Home on its "Home" line ("home preset
(fn ←)") (the rows are the session's, in `bindings.json`; headless:
`tests/test_routing.py::test_r_and_the_f_keys_are_table_rows_that_fire_their_params`,
`tests/test_ui_shell.py::test_the_cheat_sheet_matches_the_tables_and_the_loop_keys`).
What ⌘Z and Home do is group K's (checks 48 and 54).
A fail → `routing.LOOP_KEY_ROWS` / the ⌘R edge claim in `app.frame`.

**2. The config rename note and a bad TOML (L4).**
Headless: `uv run pytest -q tests/test_config.py::test_overlay_is_an_alias_merged_under_output_and_noted_once tests/test_ui_shell.py::test_system_page_shows_a_config_error_and_notes`.
`uv run hyperspace`, SYSTEM page. *Pass:* one note asking for `[overlay]`
to be renamed `[output]`, the four values still in effect (OUTPUT page:
passthrough on, bg 0, alpha 1). Then quit, add a line `output = 3` to the
file, relaunch: SYSTEM shows the error in WARN, the app runs on defaults;
remove the line. *Fail:* no note, or a crash on the bad line →
`config.load` (PR #41). When you are done, move the four keys under
`[output]` and delete `[overlay]`; the note goes away.

**3. First real audio capture (CHECKPOINT item 2; A3).**
Headless: `uv run pytest -q tests/test_audio.py`. Then in the app, AUDIO
page: the input combo lists the MacBook microphone (and BlackHole if
installed, pre-selected and labelled `System ·`). Press `M`. *Pass:*
macOS asks for microphone access once; the INPUT meters (white) move on a
clap and settle; the six OUTPUT meters (red) follow; the shape's rotation
changes with the clap on the house show's first preset (PRESETS → show ▾
→ `house`, F1 BIG BLUE WAVE: a lane pushes each rotation rate; the party
show that opens is played by hand). Plug in or enable a
device and press **rescan** beside the combo: it appears, the selection
by name survives. *Fail:* no prompt and flat meters → `AudioEngine.start_mic`
/ the callback (`audio.py`); meters at the ceiling with the blinking
annunciator on a quiet room → the analyzer's warm-up (ENGINEERING §4);
rescan loses the selection → `AudioEngine.rescan` (PR #51).

**4. The restyle by eye (PR #24) and every page fits (U1).**
Headless: `uv run pytest -q tests/test_ui_shell.py::test_every_page_fits_the_control_window`
and `uv run python tools/control_shots.py` (every page, one PNG each,
under `docs/plans/assets/07-shell/`), then `… --hands` (the HANDS page
and a gated ROUTING page, under `08-hands/`) and `… --bands` (the band
editor with a filled spectrogram); look at them. In the app, walk
the fourteen rail pills. *Pass:* from six feet, every label and number
readable; no page shows a scrollbar (ROUTING's row list scrolls inside
its own child, by design); the HANDS page (re-laid out by WP13) fits with
the tracker on: switches beside the box, feel knobs two per row. *Fail:*
a page scrollbar → that page's layout in `ui.py` / `hands/panel.py`
(U1); a value you cannot read → `ui.load_fonts` / the palette (§5).

**5. The FX stack by eye (PR #25).**
Headless: `uv run pytest -q tests/test_fx.py::test_every_factory_effect_compiles` and
`uv run python tools/fx_shots.py` (one PNG per effect). FX page: load
`acid`, then `noita-tripping`, then `noita-heavily-tripping` from the
strip; toggle `fx.on`. *Pass:* off is the plain scene; each preset is
visibly its own look; `fx.mix` at 0 is off; editing a `shaders/fx/*.glsl`
file while running changes the frame within a second and a deliberate
syntax error keeps the last pass and shows the error on the page.
*Fail:* a preset that looks like another → `library/fx/*.json` values;
a compile error that takes the frame down → `FxChain` (fx.py) or, since
WP10, `_common.glsl` — a broken common file falls back to the shipped
copy and says so on the LOOKBACK page.
*Plan 14 WP5:* every effect is now in a party preset
(`uv run pytest -q tests/test_plan12_presets.py -k "effect"`): on the
`party` show press F6 (ACID: acid, wobble, deconverge, hue cycle), F7
(MANDALA: plasma, kaleidoscope, fractals, glimmer), F8 (NOITA: trip warp,
trip colour, fractals, double vision) and watch the FX page's chips light
for exactly those. The page's faint line says a preset load resets the
stack. *Pass:* each F-key lights its four and no other; switching on one
more effect by hand and pressing the same F-key turns it off again.
*Fail:* a chip left dark → the preset's values (`preset.party_*_values`,
generated); a stray chip → a value the preset should name.
*Plan 20:* an effect is aimed at the frame or at the faces (the combo on
the open strip's blend row); every factory preset aims every effect at
the frame, so this check reads as before. The "preset load resets this
stack" note is one line now. Effects on the faces are check 91; the
order by drag is check 94.

**6. Cut-through by eye (PR #26; rewritten by plan 14 WP1).**
Headless: `uv run pytest -q tests/test_lookback.py::test_cut_through_never_cuts_an_opaque_ground tests/test_lookback.py::test_cut_through_still_cuts_in_overlay_mode`.
First in window mode, then fullscreen: `F` for faces, FACES page: pick a
pattern, with a bright window (a white page) behind the render window.
VIEW page: toggle `view.cut_through` on and off. *Pass (window and
fullscreen):* the picture is opaque with cut-through on **and** off —
the black ground and every face stay black-and-lit, nothing of the
desktop shows anywhere. Then press `T` (overlay mode over the desktop)
and toggle again. *Pass (overlay):* on, face fills let the desktop show
through where they overlap; off, the lowest face layer hides it and only
the window's ground (`overlay.bg`, the crossfader) is see-through. `T`
again returns the window. Cut-through is visible **only** in overlay
mode. *Fail:* the desktop through the faces in window or fullscreen →
the `bg_alpha < 1` rule in `render.py` `draw_scene`, or an FX pass
(`FxChain.opaque`); no visible difference in overlay mode → the blend in
`render.py` (ENGINEERING §2.1); the desktop showing through with
cut-through off in overlay → the separate-alpha path.

**7. The LFO page, B and ⇧B (plan 09 check 5, keys only).**
Headless: `uv run pytest -q tests/test_tempo.py::test_three_taps_at_140_read_140 tests/test_lfo.py::test_a_tap_does_not_move_a_running_synced_lfo_but_the_trigger_does tests/test_lfo.py::test_a_trigger_after_this_frames_step_lands_phase_zero_on_the_next_step`.
PRESETS page: load the preset `lfo-breathe` from the preset strip. LFO page. Play a track (`K`, a file
from the AUDIO page) or use a metronome app at 140. Tap `B` four times on
the beat, press `⇧B` on the "one". *Pass:* `tempo.bpm` reads 140 ± 1;
the beat light blinks on the beat; LFO 1's scope shows a one-bar sine
and brightness swells with it from that press; tapping `B` again without
`⇧B` changes the readout and **not** the swell; the panel's trigger chip
does the same as `⇧B` (WP4). **B2 is pending:** today, until the first
`⇧B` of the session, a tap *also* re-pins the downbeat — so before the
first `⇧B` the swell jumps on each tap; after it, never. If the owner
picks "never" (recommended), a tap never jumps it, even at launch.
*Fail:* the swell jumps on a re-tap *after* `⇧B` → `Clock.tap` /
`set_bpm` (tempo.py); the BPM off by more than 1 → the burst maths;
brightness not swelling at all → the `lfo:0 → view.bright` row on the
ROUTING page (is it enabled? who owns `view.bright`?).

**8. Hot reload of the post-07 modules (H1, H2).**
Headless: `uv run pytest -q tests/test_hotreload.py::test_every_package_module_but_the_cold_core_is_watched tests/test_hotreload.py::test_reloading_params_keeps_kind_identity`.
With the app running, edit `hyperspace/lfo.py` (change `LIT`'s neighbour,
say the sine to `math.sin(4 * math.pi * x)`), save. *Pass:* LFO 1's scope
doubles its frequency within a second; SYSTEM shows "hot reload:
watching". Revert. Then save `hyperspace/params.py` untouched (touch it):
toggles still toggle (`F`, `P`, `L`) and SYSTEM shows no error. *Fail:*
no change on saving lfo.py → `hotreload.MODULES` (PR #43); a toggle that
stops working after the params save → `HotReloader`'s enum preservation
(H2); a "restart" line on SYSTEM after a save that changed no enum → the
sticky note logic.

**9. WP6c: dream tuning and the GL stall (plan 07).**
Headless: `uv run pytest -q tests/test_dream.py` and
`uv run python tools/dream_shots.py --layer conv3_3 --frames 90` (then
`--layer conv4_3`; PNGs under `docs/plans/assets/`). `[dream] enabled =
true` is already set. LOOKBACK page: load `default`, then `tracer-only`;
`dream.on`; play a track. Sweep `dream.layer`, `steps`, `step`, `k`, and
the grade (`hue`, `sat`, `tint`, `tint_from`) by eye with real audio and
save two or three presets to `~/Hyperspace/dream/` as factory candidates.
*Pass:* the wake dreams in its own colours and is re-tinted by the grade;
echoes are not; `occlude` keeps the wake off the shape. Watch the fps
readout for ten minutes with `dream.on`: the ~1-in-300 stall shows as a
single dropped frame. *Fail:* the stall lasting more than a frame or
recurring every few seconds → `DreamWorker.submit` blocking (dream.py);
the dream not appearing at all with torch installed → `[dream]` gate and
the note on SYSTEM (`_open_dream`).
*Plan 14 WP6 — the dream with no extra step, and echoes you can read:*
a plain `uv sync` and `uv run hyperspace`, nothing else; the LOOKBACK
page's worker line names the device (no "no worker"). Headless:
`uv run python tools/dream_shots.py --preset party-wake` (WAKE's poses
with the worker on, `docs/plans/assets/12-presets/party-wake-dream-sheet.png`)
and `uv run pytest -q tests/test_lookback.py -k "trail or per_frame"`.
Load TRACER from the PRESETS list, then F4 (WAKE). Hover the look-back's
Fade, Spacing and Echoes: each tooltip says what it does in seconds; the
history line says how far back the trail reaches (TRACER: 24 echoes, one
every 67 ms, 1.6 s back, halving every 0.76 s). If the laptop or the
projector runs at 120 Hz, compare with a 60 Hz screen (System Settings →
Displays → refresh rate). *Pass:* TRACER's trail reads at a glance, a
clear fan of copies behind the turning shape; WAKE's wake reads past the
faces, the dream painted into it; the trail is as long at 120 Hz as at
60 Hz. *Fail:* a trail half as long at 120 Hz → the renderer not ticking
the look-back's clock (`Renderer._draw_frame` → `Lookback.tick`); a
saved look-back preset of yours that looks different → the migration
(`lookback.migrate_values`; the old file is kept as
`<file>.bak-v2-frames`).
*Plan 20:* the LOOKBACK page is three sections, ECHOES, DREAM and BOTH,
and the knobs named above are relabelled (ids unchanged): Fade is
**fade time**, Spacing is **time apart**, Echoes is **count**; the
layer is a row of six chips, `steps` is **passes**, `step` is
**strength**, `k` is **speed** (read in dream frames), `occlude` is
**shape hides**; the grade (`hue`, `sat`, `tint`, `tint from`) is under
DREAM. The history line is the ECHOES section's note ("24 × 67 MS · THE
TRAIL REACHES 1.60 S" on TRACER). Since plan 20 an effect aimed at the
faces is in the scene the history captures, so the trail can carry it
(check 93); one on the frame still never is. The page itself is check
95; speed is check 96.

## B. APC40 plugged in — about 15 minutes

**10. Mode, knobs, rings, pickup (plan 05; R6 context).**
First `uv run python tools/midi_probe.py` (echoes every message; lights
the desk), Ctrl-C. Then the app, ANALYZER page. *Pass:* on launch the
desk enters mode 0x42 (the LEDs light in the layout, rings show); the
track knobs move the view faders; the device knobs are dark and do
nothing until SHIFT is latched (plan 13 WP3: the band strip is the global
layer's), then move the open band strip; a channel fader moves that
band's post drive on either layer; after switching band with the
track-select buttons a device knob's ring redraws and the knob continues
from it (the ring re-bases the encoder — group H, check 31, is that
check). A fader moved behind your back still waits for a pickup. (The
glyphs, plan 14 WP7: the track knobs are K1–K8, the device knobs D1–D8,
the channel faders S1–S8, the track-select buttons G7·1–G7·8 — the
on-screen desk, bottom-left of the control window, lights each as you use it.) *Fail:*
no LEDs → `apc40.mode_on` / the port name (`[midi] port`); a knob that
moves the wrong param → `apc40.DEFAULT_MAP` (and its `layer`); a knob
jumping back to its old place after a switch → check 31;
a fader jumping instead of catching → `MidiIO._apply` pickup (midi.py).

**11. Rings show the base, LEDs show the state (R6, decided (a)).**
Headless: `uv run pytest -q tests/test_midi.py::test_ring_shows_the_base_and_never_chases_a_performer tests/test_midi.py::test_select_buttons_and_led_state`.
F1 on the house show (PRESETS → show ▾ → `house`; BIG BLUE WAVE: a lane
pushes each rotation rate). Play a track.
*Pass:* the track-knob rings for view faders sit at the *setting* and do
not flicker with the audio; the scene-launch LEDs for points / lines /
faces / rotate reflect the toggles; pressing one flips the LED at once.
Under a lane-owned toggle (route `lane:0 → view.faces` push on the
ROUTING page), the FACES LED follows the audio, the panel's checkbox
shows the base — that is today's rule (R6 recommendation: keep). *Fail:*
a ring chasing the audio → `MidiIO.feedback` reading the effective value.

**12. TAP TEMPO, NUDGE ±, METRONOME, QUANT (plan 09 check 5 on the desk).**
As check 7 but on the desk: TAP TEMPO (B20) ×4 on the beat, METRONOME
(B12) on the one. *Pass:* as check 7; the METRONOME LED blinks on the
beat; NUDGE + (B22) and − (B21) move `tempo.nudge` by 0.01 and the swell
with it; QUANT (B10) cycles the preset bank (`preset.next`), the clip
grid's top row (G1·1–G1·8) picks a preset, rows 2–3 a scene (with SHIFT
latched — the band scenes are the global layer's, group H), rows 4–5 a
shape, STOP ALL (G6·9) resets the scene with the 8 s undo.
**Superseded in part by plan 19** (check 82; register row 73): rows
4–5 are the bank's slots 9–24, on both layers; the shape is the cue
knob's alone.
*Fail:* METRONOME LED steady → `lfo.trigger`'s `lit` (tempo.py
`on_beat`); a button doing what it did before plan 09 → your
`bindings.json` kept an old row (`remap_factory` only moves rows where
nothing uses the source): the ROUTING page's session section lists it
(read-only); delete the stale row from `bindings.json` by hand.

## C. Camera and box (APC40 still plugged in) — about 45 minutes

**13. Real hands through the probe (plan 08).**
`uv run python tools/hands_probe.py`. *Pass:* both hands appear within a
second of entering the box; every axis's native reading, shaped output
and MIDI value change as you move; `pinch_*` gaps print live; Ctrl-C
exits cleanly. *Fail:* "no service" / no frames → Ultraleap Hand Tracking
not running, or `LEAPSDK_INSTALL_LOCATION` (plan 08 Install); a hand
seen only when very high → `[hands] mode` (desktop vs screentop).

**14. The HANDS page and the angle signs (plan 08).**
`uv run hyperspace`, HANDS page. *Pass:* the box view shows two dots
(left white, right red) that track the palms; roll thumb-up reads *up*
on both hands, pitch fingers-up reads up, yaw fingers-outward reads up
(plan 08's table); the eight switches close on a pinch and show the gap.
*Fail:* a sign the wrong way in this mounting → `hands/core.py`'s
`features()` (the atan2 forms in plan 08's table) — flip it with
`hands.<axis>.invert` for now and file the sign.

**15. Calibrate the box (plan 08).**
HANDS page: **calibrate 20 s** (or `uv run python tools/hands_probe.py
--calibrate 20`); sweep every axis end to end. *Pass:* the note says
"calibrated 12 axes"; `~/Hyperspace/hands.json` is written; every axis
now reaches both 0 and 1 in its row. *Fail:* "N not reached" → sweep
those again; ranges that make a resting hand read off-centre → the 2nd /
98th percentile in `_finish_calibration`.
**Since plan 18 the sweep also sets the interaction box** (check 72 is
this check with the box, and replaces this pass text): the note reads
"calibrated 12 axes · box W × H × D mm", the HANDS page's box view gains
an inner rectangle and its height gauge a bracket, `hands.json` holds
`"schema": "hyperspace.hands/2"` and a `box`, and a file that was there
before is kept beside it as `hands.json.bak-v1`. A hand outside that box
reads absent from then on, so sweep everything the hands should reach,
with nobody else in the camera's view.

**16. The default feel, saved as the factory setup (plan 08).**
Headless reference: `uv run pytest -q tests/test_hands.py::test_follower_catches_a_returning_hand_instead_of_jumping`.
PRESETS: load the preset `hands-play`. Raise and lower the right hand; watch
brightness. Tune on the HANDS page: Steadiness 1 Hz, Response 4, Catch
150 ms, return 500 ms, bounce 0.15, dead zone 0.04 on the centred axes
are the defaults. *Pass:* a still hand does not shimmer, a fast one does
not lag, a hand re-entering glides on rather than jumping. Save the
result from the HANDS strip as `factory` (user file, `~/Hyperspace/hands/`)
and say so in the plan's As built so it can be copied into the repo.
*Fail:* shimmer at rest → `smooth` too high; lag → `response` too low.

**17. Yaw and pitch held independently of x and y (plan 08).**
PRESETS: the preset `hands-fx`. Hold the right hand still and tilt (pitch), then
turn it (yaw). *Pass:* `fx.acid.twist` (tilt) and `fx.acid.bend` (yaw)
move while `fx.mix` (height) stays within a few percent. *Fail:* height
moving with a tilt → widen `hands.right.y.deadzone` or file it as a
feel finding; the axes are palm pose, not fingertip, by decision.

**18. The thumb-ring threshold (plan 08).**
HANDS page, watch the ring switch's gap. Pinch thumb to ring deliberately.
*Pass:* the gap drops below `pinch_close` (0.34 × palm by default) and
the switch closes; opening past `pinch_open` (0.46) lets go. *Fail:* the ring never below 0.34
on a deliberate pinch (plan 08 measured 0.39) → the thresholds are
global (`hands.pinch_close`), not per finger; file it (plan 08's open
question) with the gap you read.

**19. Plan 09 check 3 — Learn on a performed param prompts.**
Headless: `uv run pytest -q tests/test_ui_routing.py::test_the_replace_prompt_swaps_the_owner_or_leaves_the_table tests/test_hands.py::test_a_learn_on_a_performed_param_is_held_for_the_prompt tests/test_hands.py::test_a_hand_learn_needs_no_midi_adapter`.
PRESETS: the preset `hands-play` (R height positions `view.bright`). VIEW page:
right-click the brightness fader → **Learn**; move the *left* hand up
and down. *Pass:* the prompt "Brightness is already performed by R
height positions — Replace / Keep" appears on whatever page you are on;
*Keep* leaves the table (ROUTING page unchanged); repeat and *Replace*:
the row now reads L height and the preset's dirty dot lights —
`~/Hyperspace/bindings.json` is not written (plan 13 WP4: a learn goes
into the loaded preset; ⇧F or the strip's save keeps it).
Since plan 18: the new row still reads "L height positions" (height onto
brightness is the fader, as before), and the preset's own L height row
on Speed is gone — a learn moves the axis, and the learn line ends
"moved from view.speed" (check 77). Had a tilt moved furthest instead
(roll, pitch, yaw, or the hand sliding sideways or in), the row would
read "pushes +0.25": a tilt now learns as a push about the base (check
75).
Since plan 17 the menu has no plain "Learn": choose **Learn hand ▸
left**. Only the left hand's axes can then complete it, whatever the
right hand does (check 66), and the footer reads "learning view.bright —
move the left hand…" on every page until it lands.
While the prompt is up, moving hands learns nothing more. Optional: set
`[midi] enabled = false`, relaunch, repeat — Learn still works (B3, PR
#50); put it back. *Fail:* the learn lands with no prompt → `Learn.learn_source`
(learn.py) / `Bindings.add`; the wrong axis learned → `_learn` picks the
axis that moved furthest among *live* axes (WP1).

**20. Plan 09 check 4 — `hands-pinch` zoom under pinch + scroll.**
Headless: `uv run pytest -q tests/test_routing.py::test_audit_1_a_relative_writer_on_the_base_holds_under_modulation`.
PRESETS: the preset `hands-pinch`. Pinch L middle, move the left hand: zoom follows.
Keep pinching and scroll the mouse wheel in the render window a few
notches. *Pass:* zoom does not run away while scrolling under the hand;
open the pinch: zoom lands on the scroll-set value (the base), not where
the hand left it. *Fail:* drift while scrolling → `Mouse.poll` reading
the effective value (`Param.scale` must read the base); a jump to the
hand's last value on release → the gate / `Registry.apply` return.

**21. Plan 09 check 6 — the right hand deepens `lfo-breathe`'s swell.**
PRESETS: the preset `lfo-breathe`; LFO page in view. Raise the right hand. *Pass:*
LFO 1's depth fader's ghost bar rises with the hand, the brightness swell
deepens one frame later, nothing else moves (speed, zoom, fx untouched);
lower the hand: depth returns to its base (0.6 from the preset's values;
the preset sets `lfo.1.sync` to 1 bar too — R1, dissolved by plan 13: a
preset carries every performance value). *Fail:* something else moving
→ a route in the loaded preset (ROUTING page); depth not
returning when the hand leaves → B1 (`Follower.live`, PR #40).

**22. Plan 09 check 7 — a knob on a hand-owned param (B1 fixed).**
Headless: `uv run pytest -q tests/test_routing.py::test_audit_3_a_knob_moves_the_return_value_under_a_hand tests/test_hands.py::test_a_hand_leaving_the_box_releases_its_position_row`.
PRESETS: the preset `hands-play`. Right hand in the box: it owns brightness. Turn
the APC40's brightness knob (track knob, VIEW fader `view.bright`).
*Pass:* the fader's *setting* moves (the readout's base; the ring
follows the knob), the picture does not; take the hand out of the box
with the tracker still on: brightness lands on the knob's value at once
(no fade to minimum — that was B1). Since plan 18: with knob smoothing
on (80 ms at launch) the setting glides to the knob's value instead of
stepping, still under the hand; "out of the box" also means past the
interaction box's faces (check 73); and a row a learn made that reads
"pushes" lets go the same way as this one that "positions"
(`tests/test_hands.py::test_a_hand_outside_the_box_releases_its_rows_and_the_base_returns`
holds both). *Fail:* brightness going to 0.13× when
the hand leaves → `HandsIO.lanes` NaN rule (`hands/core.py`); the knob
dead while the hand is in → a `drive`-style base write somewhere (must
not exist since plan 09).

**23. A gated row on a second pinch at a different height (plan 08).**
Headless: `uv run pytest -q tests/test_hands.py::test_pinch_gate_needs_the_wider_gap_to_let_go`.
Preset `hands-pinch`: pinch R index low (brightness dark), open, raise the hand,
pinch again. *Pass:* brightness takes the hand's new height at once —
hands grab, they never yield (decision 4) — and the base returns on open.
This is a feel check, not a design question; note whether the jump wants
the catch glide (150 ms) applied on gate open too.

**24. A hand leaving the box, and `hold` (B1, N6).**
Headless: `uv run pytest -q tests/test_hands.py::test_hold_shapes_the_daw_output_but_never_latches_a_row tests/test_hands.py::test_a_returning_hand_glides_its_row_back_on_through_the_catch`.
Preset `hands-play`, HANDS page open. Take the right hand out. *Pass:* its axis
rows dim and say "DAW only; lane —"; brightness is back at its base the
same frame. Set `hands.right.y.rest` to *hold*: the DAW value holds, the
picture still returns. Re-enter: the row glides onto the hand (the
catch). *Fail:* the param parked at the rest value → `Follower.live`.

**25. End-to-end latency (plan 08).**
Film the box and the render window at 120 fps (a phone), flick a hand
up; count frames from the hand's move to brightness changing. *Pass:*
under ~4 frames at 60 fps (camera ~8 ms + one render frame + the
follower's attack). *Fail:* more → `hands.<axis>.attack` or the One Euro
`smooth`; hand-to-DAW adds `[hands] rate` limiting.

## D. Projector (second monitor) — about 5 minutes

**26. `[output] monitor`, fullscreen, "follow window"; overlay behind the config (P3, plan 07 WP1; rewritten by plan 14 WP2).**
Headless: `uv run pytest -q tests/test_overlay.py::test_follow_window_is_the_first_choice_and_reads_back_as_itself tests/test_overlay.py::test_overlay_refuses_every_road_while_the_config_shuts_it tests/test_app_boundary.py::test_the_render_window_is_transparent_only_when_the_config_asks`.
Plug the projector in. OUTPUT page: `output.monitor` combo lists "follow
window" first, then each screen by name; pick the projector,
`output.fullscreen` on. *Pass:* the render window covers the projector at
its own DPI (edges the same weight as on the laptop), the control window
stays on the laptop; with no `overlay` key in `config.toml` (the default,
decision 21 (a)) the Overlay toggle is greyed with "overlay off in the
config: set [output] overlay = true in config.toml", and `T`, the APC40's
MASTER select and the crossfader change nothing — the window stays opaque;
back to "follow window" and fullscreen off returns a window. Set
`[output] monitor = 1, fullscreen = true`, relaunch: straight to the
projector. (Since plan 16 `monitor` also says which screen the render
window *opens* on, `control_monitor` does the same for the control
window, and both windows otherwise open where they were at the last
quit: that is check 61, which also covers an index with no screen.)
Then, for a laptop demo only, add `overlay = true` under
`[output]` and relaunch: `T` floats the render over the screen, `G` is
passthrough, the crossfader darkens the ground; remove the line after.
*Fail:* the wrong screen → `overlay.Output.apply` (the GLFW monitor list
order); blurry edges → `dpr` in `app.frame`'s draw; the desktop through
the window, or `T` floating it, with no `overlay = true` →
`app._overlay_allowed` / `Output._set_overlay`.

## E. IAC + FL Studio — about 15 minutes

**27. The bridge on, and its line on SYSTEM (P3, plan 05).**
Headless: `uv run pytest -q tests/test_bridge.py tests/test_ui_shell.py::test_system_page_shows_the_bridge`.
Audio MIDI Setup: IAC Driver online with one bus. `[bridge] enabled =
true, out = "IAC"`. *Pass:* SYSTEM's bridge line reads the port, the
encoding (`pitch`), 16 lanes and a rising `sent` count while a track
plays; FL Studio (IAC as input, a Fruity Formula or Peak Controller on
pitch bend channel 1) moves with band 0. *Fail:* "bridge: no port" → the
IAC name (`out` is a substring); the line missing entirely → `panel.bridge`
not set (`app.py`).

**28. External lanes in (`ext:`).**
`[bridge] in = "IAC"` (a second bus, or FL's own MIDI out). ROUTING page:
add a row `ext:0 → view.bright`, push, depth 0.5. Send pitch bend on
channel 1 from FL. *Pass:* brightness follows the wheel; stop FL:
brightness returns to base within a frame. *Fail:* nothing → the
encoding on both ends (`[bridge] encoding`), or the row disabled.

**29. The hands' own DAW port.**
With hands on: FL sees a "Hyperspace Hands" input; right-hand height
shows on CC 109 channel 16 (`[hands] cc = 102`, six per hand). Unplug the
IAC bus while running, plug it back: within 2 s the port is rejoined and
the presence note re-sent (N4, PR #49). *Fail:* no rejoin → `HandsIO._open`.

## F. Back on the laptop — 3 minutes

**30. R12: a `.bak` before every migration rewrite.**
Headless: `uv run pytest -q "tests/test_routing.py::test_a_backup_is_kept_before_every_rewrite_and_never_over_a_hand_made_one" tests/test_migration.py::test_a_home_with_no_project_keeps_its_routes_in_a_migrated_preset`.
Then, in a scratch home: `mkdir -p /tmp/h && cp ~/Hyperspace/bindings.json.bak-plan09 /tmp/h/bindings.json`
(a schema-1 file) and `HYPERSPACE_HOME=/tmp/h HYPERSPACE_FRAMES=3 uv run hyperspace`.
*Pass* (since plan 13 WP5 the file holds a preset's part — its hand and
lane rows — so the first launch's migration does the rewrite): stderr
names the sort, the remaps, `backup: bindings.json kept as
bindings.json.bak-v1` and three `migrate:` lines; `/tmp/h/` holds
`bindings.json` (`hyperspace.bindings/3`, the session's controls only)
beside `bindings.json.bak-v1` (the file as it was), `presets/migrated.json`
(its routes, knobs and macros as the preset `MIGRATED`) and
`projects/mine.hyp.json` (the house show's bank one slot along, since
plan 14 WP3) starting on it; run it again: no new backup,
nothing rewritten. Your real home's hand-made `.bak-plan09` and
`.bak-2026-09-26` are never touched. *Fail:* no `.bak-v1` → `routing.backup`
(`preset.migrate_home`, PR #66); an existing `.bak-*` overwritten → the dated
copy path in `backup`.

## G. Plans 12 and 13 — added 2026-09-28, after the rest

**31. The APC40's knobs re-base from the host (plan 13 D7; the one hardware assumption the two-layer desk rests on).**
No headless twin: it is the device's behaviour. Desk plugged in, the app
on the house show (PRESETS → show ▾ → `house`; F1, BIG BLUE WAVE, brightness 1.25×). Turn track knob 1 (brightness) to about a
quarter; press F2 (EMBER ORBIT, brightness 1.5×). *Pass:*
the knob's ring jumps to the preset's brightness at once, and the next
turn of the knob continues from *there* — no jump back toward the
quarter, no pickup. *Fail:* the first turn after F2 snaps brightness to
where the knob physically was → the encoder keeps its own value and
ignores the host's CC; plan 13 D7 then needs soft pickup on the knobs
as well as the faders (`midi.py` `_apply`), and §3.1's "knobs jump" line
is wrong. Either way, note it on plan 11 §2 row 12.

**32. Plan 12's five party presets by eye (plan 12 §7, "what only the projector and the box can judge").**
Headless first: `uv run pytest -q tests/test_plan12_presets.py` and
`uv run python tools/preset_shots.py`, then look at
`docs/plans/assets/12-presets/party-*-sheet.png` so you know the pose
each tile expects. Projector and box on; the party show is what the rig
opens (PRESETS page: SHOW `party`; if another show is up, show ▾ →
`party`); then per preset its F-key alone — F1 TUMBLE … F5 TRIP (plan 13 WP2)
(the cards under `docs/plans/assets/12-presets/` say which). *Pass*, one
line each — **(a)** faces at 2.5× (FACES) and 2.0× (TUMBLE, WAKE) read
on the projector in the room, and the left hand's headroom to 4× is
usable rather than a white-out; **(b)** a tilt's ±45° feels like holding
the object and the half-second spring on leaving reads as "let go", not
a slip; **(c)** thumb up is up, fingers out is out, reaching in is away
from you on every row (the cards' words); **(d)** FIELD at the right
hand's top (68 copies, faces on) holds frame rate and the swing at 0.65
of a cell is a look, not a mess; **(e)** WAKE with the dream worker on:
the right roll turns the dream's hue round the wheel and fingers up
brings the dream in, over sixteen echoes; **(f)** TRIP after TAP TEMPO ×8
and METRONOME once: the left hand's height opens a pump on the beat and
the burst at the right hand's top is light, not glare. *Fail* points:
(a) the preset's `view.bright` in `library/presets/party-*.json`; (b)
`preset.TURN` (0.25 → try 0.35) and the axes' `return` on the HANDS
page; (c) the row's depth sign in `preset.party_*_routes` — a flipped
axis is one sign; (d) `view.instances`' push depth (0.6) and
`view.inst_amp`'s (0.5) in `party_field_routes`; (e) `[dream] enabled`
and the worker line on the LOOKBACK page — without the worker those two
rows do nothing by design; (f) B2 (plan 11 §2 row 1) if the pump hiccups
on a re-tap, `fx.zoomblur.glow` in `library/fx/trip.json` if it glares.
Anything that fails here is a number in a preset file, not code, unless
(c) reveals the box's mounting flips an axis for every preset — then
`hands.<axis>.invert` on the HANDS page, saved as the hands setup, is the
fix and the cards stand.

## H. Plan 13 — one preset, a two-layer desk — added 2026-09-28

Run after plan 13 is merged, APC40 plugged in, in this order (33 is the
first launch on the new code, so it goes first; 41 needs the projector
and the box, 42 the box and a `config.toml` edit). About 40 minutes. The
headless tests named are the ones plan
13's work packages add (plan 13 §10); run them first.

**33. The first launch migrates your home folder, and loses nothing (plan 13 §6, WP5).**
Headless: `uv run pytest -q tests/test_migration.py`. Before launching,
`cp -R ~/Hyperspace ~/Hyperspace-before-13`. Then `uv run hyperspace` and
read stderr. *Pass:* one `migrate:` line per rewritten file naming its
backup — `projects/<name>.hyp.json.bak-v1` for each schema-1 project,
`bindings.json.bak-v2` (or `bindings.json.bak-v2-<date>` when that name
was already taken) — and one per preset written;
`~/Hyperspace/presets/` holds one preset per filled slot of each project
(named by the slot; a slot equal to a factory preset is pointed at, not
copied, and a name a preset of yours already has gets `<name> 2`) and
one per user routing preset (named by its `name`, its effects switched
on); each project is `hyperspace.project/2` naming them, an empty slot
pointing at the house preset its F-key used to load; the look a project
restored on open is its `startup` — the slot whose values it equals, or
else a preset `<PROJECT> SAVED` (`DEFAULT SAVED` for your default
project) in its first empty slot — so opening that show brings back the
picture it had (since plan 14 WP3 a converted `default` is renamed
`mine`, `default.hyp.json.bak-v2` first, and the launch opens the party
show; show ▾ → `mine` for yours); `bindings.json` keeps your keys, pad and MIDI rows and
nothing else — no route, no preset-layer knob, no `macros`, no `values`
— the band strip's eight device knobs now `"layer": "global"`; your
learned hand rows and knobs are in the startup preset (ROUTING page:
the routes, the DESK section); `~/Hyperspace/bindings/` is as it was,
with a `NOT-READ.txt` in it; every `.bak-*` you made by hand is
untouched (`ls -la ~/Hyperspace` against the copy). A home with no
project of its own gets a `MIGRATED` preset holding bindings.json's
routes, desk and macros, the startup of a new `mine` show. Launch
again: stderr says nothing and no file's time moves. *Fail:* a slot
missing → the project migration (`preset.migrate_project`); a learned
row gone → `routing.Bindings.carried` and `preset.migrate_home`; a
backup overwritten → `routing.backup`. Keep `~/Hyperspace-before-13`
until H is done.

**34. SHIFT latches and lights (plan 13 D4, D12; WP3).**
Headless: `uv run pytest -q tests/test_desk.py::test_shift_latches_the_layer_and_lights_its_led tests/test_desk.py::test_shift_release_never_reevaluates_a_held_button`.
Press SHIFT once and let go. *Pass:* the SHIFT LED lights and stays lit;
the device knobs now move the open band strip (ANALYZER page); track knobs
1–5 move the hands' steadiness, response, catch, the selected axis's
return (HANDS page) and the BPM; track knobs 6–8 are dark and do nothing.
Press SHIFT again: LED off, the preset's meanings back. Then hold a shape
button (clip row 4), press and release SHIFT while holding it, let go of
the button: one shape change, nothing else. (**Since plan 19** clip
row 4 is the bank's slots 9–16: hold a filled one instead — one preset
load, nothing else.) *Fail:* the LED dark while
latched, or lit only while held → the latch in `MidiIO._handle`; a knob
keeping its preset meaning under SHIFT → the row's `layer`
(`apc40.DEFAULT_MAP`, your `bindings.json`); a second action on release →
D12, the modifier read at the press.

**35. On a layer switch the knobs jump and the faders pick up (plan 13 D7; WP3).**
Headless: `uv run pytest -q tests/test_desk.py::test_a_layer_switch_rebases_the_knobs_and_leaves_the_faders_to_pick_up tests/test_desk.py::test_a_preset_load_clears_the_faders_catch`.
Run check 31 first; if it failed, stop and note it on plan 13 §12 — D7
then needs pickup on the knobs too. Turn track knob 1 (brightness) to a
quarter; SHIFT (knob 1 is now steadiness); turn it a little; SHIFT back.
*Pass:* each switch moves the ring at once to that layer's value, and the
next turn continues from the ring, no jump. Then on the ANALYZER page drag
SUB's drive to the top with the mouse and move track fader 1 from the
bottom: nothing until it passes the new value, then it follows. *Fail:* a
knob snapping back to where it physically was → the encoder ignores the
host's CC (check 31's fail); a fader jumping → pickup in `MidiIO._apply`.

**36. An unmapped control is dark and does nothing (plan 13 D8; WP3).**
Headless: `uv run pytest -q tests/test_desk.py::test_an_unmapped_control_is_dark_and_does_nothing`.
F1 (TUMBLE, whose desk leaves the device knobs free). *Pass:* the eight
device-knob rings are off; turning one changes nothing on the panel; the
ROUTING page's DESK · PRESET LAYER section lists them, dimmed, under the
desk rows as "D1  unmapped — dark" (through "D8"; hover one for "device
knob 1"), and the on-screen desk (bottom-left) draws D1–D8 dark;
with SHIFT latched they light (on the device and on screen, where ⇧ turns
red) and move the band strip, and the ROUTING head reads LAYER GLOBAL.
**Superseded in part by plan 19** (check 85; register row 75): a
factory TUMBLE now has 4D depth, yaw, pitch and pattern on D1–D4, so
only D5–D8 are dark (a TUMBLE of yours saved before plan 19 keeps all
eight dark). *Fail:* a lit ring on an unmapped knob → the dark
rule in `MidiIO.redraw`; a device knob moving the band strip without SHIFT
→ a fall-through to the global layer, which D8 forbids (`MidiIO._handle`);
a knob that does nothing but is not listed → `ui_routing.unmapped`.

**37. Learn refuses the global layer and the invariant controls (plan 13 D5, D6; WP4).**
Headless: `uv run pytest -q tests/test_learn.py::test_learn_refuses_the_global_layer_and_invariant_controls tests/test_learn.py::test_a_knob_learn_writes_a_desk_row_into_the_loaded_preset tests/test_learn.py::test_a_hand_learn_writes_a_route_into_the_loaded_preset`.
Note `bindings.json`'s time (`ls -l ~/Hyperspace/bindings.json`). Open
the ROUTING page. Right-click Brightness → Learn, move track fader 1.
*Pass:* refused — the ROUTING head (and the SYSTEM page's learn line)
reads, in the warning colour, "learn: S1 (track fader 1) is invariant
(the session's) — not learned"; nothing changes, the fader still drives
SUB's drive. Latch SHIFT, Learn again, turn track knob 6: "learn: K6
(track knob 6) is on the global layer (the session's) — latch SHIFT off
to learn into the preset". Unlatch SHIFT, Learn again, turn device knob
3: "learn: learned view.bright ← D3 (device knob 3) (into the preset)" —
the knob now moves brightness, the DESK section shows "D3 view.bright
abs" and K1 (brightness's old knob) as "unmapped — dark", the on-screen
desk lights D3 and darkens K1, the
head's dot (and the PRESETS strip's) is lit, and `bindings.json`'s time
has not moved. Load the preset again (F1) to throw the learn away: the
dot goes out, track knob 1 is brightness again.
**Superseded in part by plan 17** (check 65 is this check as it now
runs; register row 61). The menu item is **Learn desk**. A fader is no
longer refused: it is not a candidate at all, so moving track fader 1
drives SUB's drive as always, **nothing is said, and the learn stays
armed** (the refusal "S1 (track fader 1) is invariant (the session's) —
not learned" is now met only by clicking S1 on the on-screen desk while
a desk learn is armed). SHIFT latches through an armed learn, so "Learn
again" is not needed: the K6 refusal shows in the footer as well, the
learn is still armed after it, and after unlatching SHIFT the same learn
lands on device knob 3. The message ends "; K1 let go". **Since plan
19** D3 on a factory preset with no knobs of its own is the camera's
pitch (register row 75): the learn takes D3 from it. *Fail:* a learn on a
fader or under SHIFT → `Learn.learn_control` (`learn.blocked`) and the
learning branch of `MidiIO._handle`; `bindings.json`
rewritten → a learn still writing the session file; no dot → the desk in
`Presets.signature`.

**38. A preset load lands every base and replaces every route (plan 13 D2, D9; WP2).**
Headless: `uv run pytest -q tests/test_presets.py::test_a_preset_load_lands_every_base_and_replaces_every_route tests/test_presets.py::test_a_preset_load_never_touches_a_session_param`.
Project `party`. F5 (TRIP): the effect stack is on. Tap B (or TAP TEMPO)
×8 at about 100 BPM. F1 (TUMBLE). *Pass:* every effect is off (FX page),
the look-back is back to its default, the ROUTING page shows TUMBLE's rows
and no `fx.*` row, the BPM still reads about 100, the band scene has not
changed. *Fail:* an effect still on → a group `Presets.load_doc` did not
land; the BPM reset → `tempo` classed as performance
(`params.SESSION_GROUPS`); an `fx.*` row left → the route replacement.
*Plan 14 WP5–WP6:* the same from F6 (ACID) to F1, and from F8 (NOITA) to
F4 (WAKE): every effect off and WAKE's look-back (24 echoes, fade 0.60 s)
on, with no extra step for the dream.

**39. One macro, two directions (plan 13 D10, §2.4; WP3, WP5).**
Headless: `uv run pytest -q tests/test_macros.py::test_base_subscribers_of_opposite_polarity_move_opposite_ways`.
Headless too: `uv run pytest -q tests/test_presets.py::test_lfo_breathes_macro_moves_brightness_up_and_speed_down`.
PRESETS page → the preset strip → `lfo-breathe`; it loads with the knob
at the bottom (brightness 1×, speed 0.25×). Turn device knob 1 (macro 1,
"Breathe", its ring from the preset's desk) from bottom to top. *Pass:*
the picture brightens from 1× to 2× while the spin slows from 0.25× to a
crawl (about 0.06×), together, and the LFO's breathing of the effect mix
deepens from nothing; bottom to top and back is smooth, no step; the ROUTING page's
MACROS section shows knob 1 labelled "Breathe" with three subscriber
lines — two `base` lines (a param, `from`, `to`; the one whose `from` is
above its `to` runs the other way) and one `depth` line naming the LFO's
route. *Fail:* both moving the same way → a
subscriber's `from → to` (`preset.BREATHE_BRIGHT` / `BREATHE_SPEED`;
the file is generated: `python -m hyperspace.preset`); nothing moving →
the macro's base-follow step (`routing.py`) or the desk row
(`preset.lfo_breathe_desk`, `cc:*:16 → macro.1`).

**40. What the show starts on (plan 13 D11; WP2; rewritten by plan 14 WP3, WP4).**
Headless: `uv run pytest -q tests/test_presets.py::test_the_startup_preset_loads_on_launch tests/test_ui_presets.py::test_starts_on_is_labelled_and_saved_when_set tests/test_party_show.py`.
Launch: the party show opens (SHOW `party`, its name in full, "factory"
beside it, no unsaved dot) on TUMBLE. PRESETS page, "starts on ▾" → WAKE
— no save: it is written the moment it is picked (a factory show's first
write makes your copy, `~/Hyperspace/projects/party.hyp.json`). Quit
(Esc) and relaunch. *Pass:* the party show comes up on WAKE, its desk lit
(the device-knob rings at WAKE's values), the status line says so. Then
show ▾ → `house`, quit, relaunch: the house show opens (the last show
opened is remembered, `~/Hyperspace/last_show`). Put party's "starts on"
back to TUMBLE and open party again afterwards. *Fail:* a dark desk or
the wrong look → `Project.startup` and the startup load in `app.main`;
a pick that does not survive the relaunch → `ui_presets.set_starts_on`;
the wrong show → `Library._open_default` / `last_show`.

**41. The party presets, re-cut (plan 12 §7, plan 13 WP5; plan 14 WP5–WP6).**
Headless: `uv run pytest -q tests/test_plan12_presets.py` (the F-keys,
`test_the_party_presets_load_by_f_key_as_presets`; the knobs,
`test_wake_and_trip_device_knobs_move_their_bases`) and
`uv run python tools/preset_shots.py`. Projector and box on. As check 32,
but each preset is one F-key — F1 TUMBLE, F2 FACES, F3 FIELD, F4 WAKE,
F5 TRIP, F6 ACID, F7 MANDALA, F8 NOITA on the `party` show, which the rig opens — one step,
nothing else to load; then TRACER from the PRESETS list (it is on no
F-key). Each card (`docs/plans/assets/12-presets/party-*.md`) says what
each hand does. *Plan 14:* on the glass, ACID, MANDALA, NOITA and TRACER
keep a black ground with no hand in the box (MANDALA's plasma comes in
only with the right hand's fingers up); WAKE's wake reads beyond the
faces, the dream in it; each of the four's device knobs 1–8 sets its
card's eight bases. *Pass:* check 32's (a)–(f) hold as
before; WAKE's device knobs 1–8 set echo mix · fade · darken · contrast ·
occlude · dream mix · dream sat · dream k, and TRIP's set fx mix · plasma
level · kaleido segments · kaleido zoom · burst amount · burst glow · hue
paint · hue spread (plan 12 §6) — device knobs 1–8 are `cc:*:16`–`23`, absolute —
each ring showing its value; on TUMBLE, FACES and FIELD the device
knobs are dark (SHIFT brings the band strip) — **since plan 19** D1–D4
are 4D depth, yaw, pitch and pattern there and D5–D8 dark (check 85). TUMBLE's left height
still pushes the drive (row 19 (a)), its ROUTING row marked "session".
*Fail:* a look → the values in `library/presets/party-*.json` (data)
or a route in `preset.party_*_routes` (generated: change the generator,
`python -m hyperspace.preset`, not the file); a knob on the wrong base
→ `preset.WAKE_KNOBS` / `TRIP_KNOBS` / `ACID_KNOBS` / `MANDALA_KNOBS` /
`NOITA_KNOBS` / `TRACER_KNOBS`; anything check 32 lists → the same
place it lists.

**42. Hand routes by name survive a reordered `dofs` (plan 13 WP5b,
decision register row 20).** Headless: `uv run pytest -q
tests/test_hand_names.py`. Camera and box on. In `config.toml` set
`[hands] dofs = ["yaw", "pitch", "roll", "y", "x", "z"]` (the default
list reversed) and relaunch. Load `hands-play`: the right height still
positions brightness, the left height speed, the right tilt 4D depth; the
ROUTING page's rows read "R y positions", "L y positions", "R pitch
positions" and their source combos show `hand R y` / `hand L y` /
`hand R pitch`. Load `hands-pinch`: a right index pinch still picks
brightness. Now set `dofs = ["x", "y", "z"]` and relaunch: `hands-play`'s
right tilt row does nothing (no `right.pitch` on this rig) while both
heights still work. Put `dofs` back afterwards. *Pass:* every row stays on
the axis its words name; the missing axis's row is dormant, never on
another axis. *Fail:* a row moving with the wrong axis → `Router.lane` /
`HandsIO._publish` (`router.names["hand"]`); the combos showing raw
`hand:<i>` → `ui_routing._sources` / `Router.address`.

## I. Plan 14 WP1 — an opaque window, the stall log — added 2026-09-29

Run on the plan 14 WP1 branch (PR, not merged). 43 needs the projector;
44 and 46 run on the laptop alone; 45 (plan 14 WP7) needs the APC40.
About 25 minutes. The headless tests named are the ones each WP adds;
run them first.

**43. Pepper's Ghost: an opaque black window (plan 14 WP1).**
Headless: `uv run pytest -q tests/test_lookback.py -k opaque`.
Projector connected. Put a bright desktop behind the render window on the
projector — a white browser page full screen on that display. Fullscreen
the render window on the projector (OUTPUT page: the projector's screen,
`output.fullscreen` on), `F` for faces, then load each party preset
F1–F5 and turn `view.cut_through` on and off on each. *Pass:* no desktop
shows anywhere, ever: the ground is black, the faces and lines are lit on
black, at every preset, cut-through on or off, with FX on (TRIP) and the
look-back on (WAKE). *Fail:* the desktop through the faces or the faint
lines → `render.py` cut-through (`draw_scene`: the `bg_alpha < 1` rule)
or an FX pass (`FxChain.opaque`); through the whole ground → the window
is in overlay (`T` or the APC40's MASTER select — check the OUTPUT page)
or `app._windows`' transparent-framebuffer hint (decision register row
21, pending).

**44. The stall log: `kill -USR1` writes a dump (plan 14 WP1).**
Headless: `uv run pytest -q tests/test_watchdog.py`. Launch
`uv run hyperspace`. From another terminal: `kill -USR1 $(pgrep -f
"bin/hyperspace")`. *Pass:* `~/Hyperspace/stall.log` gains a block of
thread stacks (the main thread's ends in `app.py` `main`), the app keeps
running, and the SYSTEM page shows `stall log: …/stall.log (1 raw
dump)`. If the render ever freezes, or the red banner at the bottom of
the control window names a render error or a render stall, keep
`stall.log`: each entry's header names the kind (`stall`, `render
error`, `render stall`, `stranded target`, `non-finite`, `warning`), the
time and the loaded preset, then every thread's stack. *Fail:* no file or
an empty one → `watchdog.Watchdog.start` (its `error` is on the SYSTEM
page); the app quitting on the signal → the `faulthandler.register` call
did not run (the default action of SIGUSR1 is to terminate).

**45. The on-screen desk matches the device, control by control (plan 14 WP7, decision 25).**
Headless: `uv run pytest -q tests/test_ui_desk.py`. APC40 plugged in;
launch, open the `party` project, F5 (TRIP), ROUTING page. The desk is
drawn at the bottom left of the control window — in the corner since
plan 16, above the cheat sheet once `/` shows that
(SYSTEM page: `Desk diagram` hides and shows it). *Pass:* the picture is
the device's face — the 8 × 5 clip grid with the scene-launch column on
its right, then the clip-stop row with STOP ALL, track select with MASTER,
activator, solo and rec-arm rows, the cue knob in the master column, the
nine faders along the bottom; on the right the eight track knobs (two
rows of four) with PAN · SEND A · B · C under them, the bank-select arrows
with TAP TEMPO, NUDGE − / + and SHIFT beside them, the eight device knobs
with their eight buttons, PLAY · STOP · REC and the crossfader. Walk the
desk with the mouse: every hover names the control Akai's way on its
second line and it is the one at that place on the device (anything out
of place: note it with its glyph). Every control lit on screen is lit on
the device and every dark one dark (the clip grid in the same colours);
turn D1: its arc moves with its ring. Latch SHIFT: ⇧ turns red, the
header says GLOBAL LAYER · SHIFT, D1–D8 and K1–K5 stay lit with the band
strip and the hand feel, K6–K8 go dark — on the device the same. Pick
any row of the ROUTING page's DESK section, read its glyph (say "D4"),
find D4 on the diagram, then the same place on the device, and turn it:
that row's param moves.
**Superseded in part by plan 17** (check 69; register row 57): the desk
is no longer a fixed 380 × 290. It takes the room left of the panel (384
× 431 at the control size), and with the panel hidden (H, DEVICE ON/OFF,
the header's `big` chip) it fills the control window and every lit
control carries its param's name, the glyph small in the corner. The
walk above is easier at that size. A click on a control now picks it
(check 70): click it again, or the ground between controls, to let go.
**Superseded in part by plan 19** (checks 82 and 85; register rows 73,
75): clip rows 4–5 are the bank's slots 9–24 on both layers — a filled
slot's pad amber at half strength with its preset's name, an empty
one dark with its glyph only, the loaded one green — and on a preset
with no knobs of its own D1–D4 are lit (4D depth, yaw, pitch, pattern).
The device's amber is velocity 5.
*Fail:* a control drawn in the wrong place →
`apc40._layout` (its x, y); lit on screen but dark on the device, or the
reverse → the screen reads `Bindings.active` and the device
`MidiIO.redraw` — they must agree (`ui_desk.lit`); a glyph that names
another control than the one you turned → `apc40.glyph`.

**46. WAKE without the dream worker still draws (plan 14 WP1, the freeze).**
Headless: `uv run pytest -q tests/test_render.py::test_a_look_back_frame_with_no_worker_leaves_the_window_bound tests/test_lookback.py::test_capture_off_the_cadence_with_no_source_puts_the_target_back`.
In `config.toml` set `[dream] enabled = false` and relaunch. Open the
`party` project and press F4 (WAKE): `dream.on`, an echo every 50 ms,
and no worker. *Pass:* the render window keeps moving — the shape turns,
the echoes trail it — for a minute and through F1–F5 and back to F4; the
red banner says "WAKE turns the dream on, but there is no dream worker
(…)" until **dismiss**; `stall.log` has that `warning` and no `stranded
target`. Put `[dream]` back afterwards. *Fail:* the render window
freezing on one picture while the panel goes on → a framebuffer left
bound (`Renderer.draw`'s `finally`, `Lookback.capture`'s, and the
`ctx.screen.use()` at the top of `app.draw_render`) — `stall.log` then
has a `stranded target` entry naming it.

## J. Ghost hands — added 2026-10-04

Run on the ghost-hands branch. Camera and projector (or the laptop
screen); about 15 minutes. First, headless:
`uv run pytest -q tests/test_ghost.py tests/test_hands_tape.py tests/test_hands_leap.py`.
`[hands] enabled = true`; calibrate the box first (15) if
`~/Hyperspace/hands.json` is old.

**47. The ghost hands follow the real ones.**
Launch, HANDS page, tick **Ghost hands** (`ghost.on`), opacity about
60 %. Sit where you perform, both hands in the box. *Pass:* (a) **left
and right not swapped** — raise only your left hand: the hand on the left
of the render moves (the near-white one); the right hand, light red, is
on the right.
(b) **Fingers track** — spread, close to a fist, pinch thumb to each
finger in turn, point with one finger: every finger follows, the thumb
on the correct side of each hand, nothing bending backwards. (c)
**Mirroring looks right from the performer's side** — move a hand
right, it moves right; lift it, it rises; push it toward the screen, it
goes away from you; with your palm down you see the back of the ghost
hand. Then tick **Ghost mirror** and look at the render the way the
audience will (in the mirror or the Pepper's Ghost glass): the hands
should read correctly there; note which setting the rig wants. (d)
**Latency feels immediate** — shake a hand fast: the ghost stays on it
with no lag you can feel and no trailing smoothing; hold still: no
shimmer. (e) **The box fills the frame** — reach to each calibrated
corner: the hand stays in frame, near the edge. (f) **Leaving** — pull
a hand out of the box: it fades out where it was in about a third of a
second, and fades back in when you return; nothing freezes or jumps.
(g) **Effects never touch it** — F5 (TRIP) and F4 (WAKE): the shape
warps, colours and trails; the hands do not. (h) **Off is off** —
untick it: the render is as before. (i) **The guide** — `ghost.guide`
BESIDE: move the right hand straight right, then straight up, then
toward the screen: each time one ball moves (red, green, blue) and the
others stay put; tilt fingers up, turn them outward, roll thumb-up: the
red arc's dot rises, the green arc's goes out, the blue arc's turns
toward the palm's new facing, and no dot ever leaves its arc; pinch each finger: its bead lights; close
to a fist: the grab ring shrinks round a full ball. Route a few left-hand
axes and none on the right (ROUTING page): the left gauge's routed axes
keep their colour, everything on the right is grey and smaller but
still moves. ON HAND: the
same gauge rides the palm. Tick **Ghost tethers**: each routed left-hand
axis gets a line in its colour to a label at the left edge naming the
param it drives (the ROUTING page's target); the lines hold still while
the balls move; untick it and the gimbals stay. Repeat (c) once in `screentop` if
the rig ever uses it: those axes are a guess (`ghost.MODES`). *Fail:*
swapped or mirrored hands → `ghost.MODES` / `ghost.mirror`; a finger on
the wrong digit or bending wrongly → `hands.core.skeleton` (the bones'
order); lag → something smoothing the skeleton (it must be raw); the
hands warped or trailing → the pass order in `Renderer._draw_frame`.
Then record a tape for everyone else: `uv run python tools/hands_tape.py
record tests/fixtures/hands/rig.json --seconds 6` — both hands, open,
fist, pinches, in and out of the box — and commit it.

## K. Plan 15 — undo, home, the dim, save-as on the desk — added 2026-10-04

Run on `finish-line` once plan 15 is merged into it (PRs #81 the dim,
#82 undo and the trash, #83 home, #87 save-as). 48, 50 and 53
run on the laptop alone; 49, 51 and 54–57 need the APC40; 52 needs the
camera and the box. About 35 minutes. The headless tests named are the
ones each package adds; run them first. None of this has been tried by a
person: it was shown by tests, offscreen renders and scripted launches on
a laptop (`15-safety-net.md` §8). Before the first launch:
`cp -R ~/Hyperspace ~/Hyperspace-2026-10-04`, and do 57 first.

**48. Undo takes back one slider drag (plan 15 WP1, decision 26).**
Headless: `uv run pytest -q tests/test_undo.py::test_a_slider_drag_is_one_step_and_undo_sets_only_that_param tests/test_undo.py::test_a_pause_longer_than_the_settle_time_makes_a_second_step tests/test_routing.py::test_a_chord_fires_only_its_own_row tests/test_ui_shell.py::test_the_footer_says_what_was_undone`.
Launch, VIEW page. Note Brightness. Drag it somewhere else in one move
and let go. Wait a second. Press ⌘Z (Ctrl+Z does the same). *Pass:*
Brightness is back where it was, nothing else moved, and the footer says
"undid Brightness … → …" for about four seconds. ⌘⇧Z: it goes forward
again ("redid …"). Now drag Brightness, wait a second, drag Speed, wait,
press ⌘Z twice: Speed comes back first, then Brightness. Change a
route's depth on the ROUTING page and ⌘Z: it comes back. Click in a text
field (a macro's label) and press ⌘Z there: only the text changes. With
nothing left the footer says "nothing to undo", again on every press.
Drag a slider, hold the mouse still for a full second with the button
down, then drag on: that is **two** steps (decision register row 43);
say if it should be one. *Fail:* nothing comes back → the tick is not
running (`app.frame`, `Host.undo`) or the key rows are missing
(`routing.LOOP_KEY_ROWS`; they are in your `bindings.json` after check
57); two presses needed for one drag → the settle time
(`undo.SETTLE_S`); ⌘⇧Z undoes instead of redoing → the chord rule in
`Router.keys`; no footer line → `Panel._message` / `Panel._footer`.

**49. Undo takes back one knob turn on the desk (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_undo.py::test_a_knob_turn_on_the_desk_is_one_step tests/test_undo.py::test_undo_of_a_slider_does_not_rerun_a_load`.
APC40 in, F5 (TRIP). Turn D1 (the effect mix) from where it is to the
other end in one sweep. Wait a second. ⌘Z. *Pass:* the mix and D1's ring
are back; the next turn of D1 carries on from the ring, no jump. Latch
SHIFT, move S1 (SUB's drive) a little, wait, ⌘Z: the drive is back,
SHIFT is still lit, and S1 does nothing until it passes the value again
(pickup). *Fail:* SHIFT dropped or every fader lost its hold → the
restore ran a desk replacement (`Undo._restore`, `Bindings.set_desk`'s
`load`); the ring not following → `MidiIO.feedback`.

**50. Undo after an F-key load (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_undo.py::test_a_preset_load_is_one_step_by_every_road tests/test_undo.py::test_undo_of_a_load_puts_back_the_values_the_routes_the_desk_the_macros_and_the_name tests/test_undo.py::test_save_after_undoing_a_load_writes_the_earlier_preset`.
F1 (TUMBLE). Change three things (brightness, the shape, switch faces
on) so the preset's dot is lit. F5 (TRIP). ⌘Z, once. *Pass:* the look is
TUMBLE with your three changes, the PRESETS page says TUMBLE with its dot
lit, F1's button is lit, the ROUTING page shows TUMBLE's routes and
desk, and the footer says "undid load TRIP". ⌘⇧Z: TRIP again, clean. ⌘Z
again, then press F5 by hand: redo is gone (a new action clears it).
Repeat the load from the PRESETS list, and with QUANT (next preset): one
⌘Z each. *Fail:* the look back but the name still TRIP → the marks
(`library.Marks`, `push(load=True)` in `Presets.load_doc`); two presses
for one load → a second push in the same action; routes not back →
`Bindings.set_routes` in the restore.

**51. Undo after a Learn, and after an Unbind (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_learn.py::test_a_learn_is_one_undo_step tests/test_midi.py::test_an_unbind_is_one_undo_step tests/test_ui_routing.py::test_a_route_delete_and_a_replace_are_undo_steps tests/test_undo.py::test_a_row_that_undo_brings_back_picks_up_afresh`.
F5 (TRIP), ROUTING page. Right-click Brightness → Learn, turn D3. The
DESK section shows "D3 view.bright" and D3's old param is gone from it.
⌘Z. *Pass:* D3 drives what it drove before, the row is back, the
footer says "undid learn view.bright", the preset's dot is as it was.
Right-click a param a desk knob drives → Unbind; its ring goes dark; ⌘Z:
the row and the ring are back. Delete a route with its ×; ⌘Z: it is back
with its depth and its gate. `ls -l ~/Hyperspace/presets` before and
after: no file's time moved. Since plan 17: the item is **Learn desk**;
the footer's line after the learn ends "; K1 let go" (K1 had
Brightness), and the one ⌘Z gives K1 its row back too; **Unbind** on a
param with a knob and a route is a submenu (desk / route / both), and
"both" is still one ⌘Z (check 64). *Fail:* a row not back → the push before
the edit (`Learn.learn_control`, `Learn.unbind`, `ui_routing.page`); the
ring staying dark → `redraw_serial` in `set_desk(load=False)`.

**52. A hand moving makes no undo step (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_undo.py::test_a_performer_moving_makes_no_step tests/test_undo.py::test_an_idle_app_makes_no_step`.
Camera and box on, F1 (TUMBLE). On the VIEW page drag Brightness and
wait a second. Now play: both hands in the box for half a minute, in and
out several times, the music on. Press ⌘Z once. *Pass:* Brightness goes
back: the one thing you did by hand. Nothing a hand, a band or an LFO
moved made a step. *Fail:* the footer says "undid Speed …" (or any param
a hand route drives) with values that differ only in the last digits →
the tolerance in the fingerprint (`undo.REL_TOL`); it names a
`rot.phase` or the BPM → `undo.watched`.

**53. A saved-over or deleted preset is in the trash (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_library.py -k trash`.
PRESETS page. Load a preset of yours (make one with "as…" if you have
none: `CHECK 53`). Change the brightness; press **save**. Then open the
preset list and press × beside it. *Pass:* `ls ~/Hyperspace/trash/presets/`
shows two files, `check-53.<date>-<time>.json`, the first holding the
look before the save and the second the look that was deleted; copying
one back into `~/Hyperspace/presets/` as `check-53.json` brings the
preset back into the list within a couple of seconds. Press save twice
with no change in between: no new file in the trash. The PRESETS page's
"more" lists no module called "trash". **Superseded in part by plan
19** (check 88; register row 76): the trash has a view — the preset
list's "trash (n) ▸", with restore (never over a file) and a two-click
"empty trash…" — so copying a file back by hand is no longer needed,
though it still works. *Fail:* nothing in the trash →
`library.to_trash` in `Library.save_as` / `Library.delete`; a "trash"
strip under "more" → `Library.groups`.

**54. Home, from any preset, on either layer (plan 15 WP2, decision 27).**
Headless: `uv run pytest -q tests/test_presets.py::test_home_loads_what_the_show_starts_on tests/test_presets.py::test_home_with_no_starts_on_says_so_and_loads_nothing tests/test_presets.py::test_home_is_one_undo_step tests/test_desk.py::test_overdub_is_home_on_both_layers_and_is_lit`.
The party show; the PRESETS page reads "starts on / home ▾ TUMBLE".
OVERDUB (B11, beside METRONOME) is lit. F5 (TRIP), change a few things.
Press OVERDUB. *Pass:* TUMBLE is up, its desk lit. ⌘Z: TRIP with your
changes is back (the footer: "undid home → TUMBLE"). F7, latch SHIFT,
press OVERDUB: TUMBLE again, and SHIFT has dropped (a load drops to the
preset layer). F3, then fn+← on the laptop: TUMBLE. Set "starts on" to —
none: OVERDUB goes dark, and pressing it loads nothing; the footer says
"home: this show names no 'starts on' preset — pick one on the PRESETS
page" once (a second press shows nothing new in the footer: the line is
still on the PRESETS page). Set it back to TUMBLE: that line goes.
Right-click any control → Learn, press OVERDUB: refused ("B11 (OVERDUB)
is invariant (the session's) — not learned"), and nobody is sent home.
**Superseded in part by plan 17** (register row 61): with **Learn desk**
armed, OVERDUB does its job — the show's "starts on" preset loads — no
refusal is said, and the learn stays armed, to land in that preset on
the next knob. Cancel it from the footer's line.
*Fail:* OVERDUB dark or dead → its row (`apc40.DEFAULT_MAP`; in your
`bindings.json` after check 57); doing something else under SHIFT → the
row has a layer; fn+← nothing → `key:HOME` in `routing.LOOP_KEY_ROWS`,
or the laptop not sending Home for fn+← (say so: the row rebinds).

**55. The crossfader is the master dim (plan 15 WP3, decision 28).**
Headless: `uv run pytest -q tests/test_render.py -k dim`, then `uv run pytest -q tests/test_midi.py::test_the_crossfader_dims_with_soft_pickup tests/test_desk.py::test_the_crossfader_keeps_its_hold_across_a_preset_load tests/test_ui_shell.py::test_the_dim_is_first_on_output_and_the_footer_says_so_while_dimmed` (two commands: a `-k` filters every file on its line).
Quit. Push the crossfader hard left. Launch. *Pass (a), starts bright:*
the picture is at full brightness, and the OUTPUT page's Master dim, its
first row, reads 100%. *(b), cannot dim by accident:* nudge the
crossfader a little from the left: nothing happens. *(c), takes hold at
the value:* slide it all the way right, then back left: from the right
end it has the picture, which dims smoothly to **black** at the left,
the footer reading "dim …%" in the warning colour and "dim black" at the
end; back right, full, and the readout goes. *(d), everything dims:*
with F5 (TRIP), the look-back on (F4) and the ghost hands on, at half
way the shape, the effects, the trail and the hands are all half as
bright; on the glass the ground stays black, never grey, and nothing
behind shows through. *(e), survives a load:* leave it at half; press
F1, F5, OVERDUB: the picture stays at half through each; the next move
of the crossfader carries on from half with no jump. *(f), both layers:*
latch SHIFT: the crossfader still dims. *(g):* quit at half, relaunch:
full again. *Fail:* dark at launch → `output.dim` is being saved or
seeded (`Output.register`, `persist`); right is black → the fader's
direction (the row is `abs`; say so, it is one line — that CC 0 is the
left end was read from a comment, never from the device); a jump when
first touched → pickup on the row (`MidiIO._apply`); dead after a load
until brought back across the value → the catch rule in
`MidiIO.redraw(load=True)`; the hands or an effect not dimming → the
pass is not last (`Renderer._draw_frame`); the desktop showing through
on the glass → the opaque blend in `Renderer.dim_pass`; the fader moving
and the picture not, with a line under Master dim on the OUTPUT page →
the driver refused the dim's program (`Renderer.dim_error`); a preset
moving it → a preset or show landing a rig param.

**56. A hold on the clip-stop row saves a new preset; a tap does not (plan 15 WP4, decision 29).**
Headless: `uv run pytest -q tests/test_midi.py::test_a_hold_fires_once_at_the_hold_time_while_held tests/test_midi.py::test_a_tap_fires_nothing tests/test_midi.py::test_the_bar_is_one_control tests/test_midi.py::test_the_bar_lights_while_held_and_the_new_slots_pad_blinks tests/test_presets.py::test_save_new_never_overwrites tests/test_presets.py::test_save_new_fills_the_next_empty_slot_and_becomes_the_loaded_preset tests/test_presets.py::test_save_new_on_a_full_bank_saves_to_the_list_and_says_so tests/test_presets.py::test_the_new_slot_loads_from_the_preset_row tests/test_library.py::test_next_name_counts_on_from_a_trailing_number`.
Then `uv run pytest -q tests/test_presets.py::test_put_and_clear_slot_write_the_show_and_delete_no_file tests/test_ui_presets.py::test_a_slots_menu_offers_put_and_clear tests/test_desk.py::test_the_clip_stop_row_is_invariant`; what the desk should send, and when, is `docs/plans/assets/15-safety-net/save-as-demo.txt`.
Make room first: PRESETS page, right-click F8's button → **clear slot**
(F8 reads "—"; the footer says "F8: cleared — NOITA is still in the
preset list", and it is). F5 (TRIP); change the
look. Tap any clip-stop button, quickly. *Pass (a):* the row lights
while your finger is down and nothing else happens: no new preset in the
list, no file in `~/Hyperspace/presets`. *(b):* hold any clip-stop
button. After a little over half a second the whole row and pad 8 of
clip row 1 blink for about a second and a half, and pad 5 (TRIP's) goes
out; let go. The row is dark again and pad 8 stays green. F8's button
reads **TRIP 2** and is lit, the
PRESETS strip says TRIP 2 with no dot, the footer says "saved TRIP 2 →
F8", and `~/Hyperspace/presets/trip-2.json` exists. *(c), the new slot
loads from the desk:* press pad 1 (TUMBLE), then pad 8: your look is
back. *(d), it never overwrites:* change the look, hold the row again
(a different button of it): the footer says, in the warning colour,
"saved TRIP 3 — the bank is full: it is in the preset list"; the row
blinks, no pad does, and pad 8 goes out (TRIP 3 is loaded and no slot
names it); TRIP 2 is unchanged (load it). Hold once more: TRIP 4, and
the footer says the same line again. *(e), one bar:* lay two fingers on
the row and hold: one new preset, not two; keep holding for five
seconds: still one.
*(f):* latch SHIFT and hold the row: it saves the same way. *(g):*
right-click F8 → **put preset here…** (a list of every preset, twelve
rows tall at most, scrolling past that) → NOITA: F8 is NOITA again, the
footer says "F8: NOITA", the "bank is full" line has gone from the
PRESETS page, and TRIP 2, TRIP 3 and TRIP 4 are still in the list.
**clear slot** is greyed on an empty slot. Plain **save** on the panel
still writes over the loaded preset (check 53). *(h):* right-click any
control → Learn, then hold a clip-stop button: refused ("G6·5 (clip stop
5) is invariant (the session's) — not learned"), nothing saved.
**Superseded in part by plan 17** (register row 61): with **Learn desk**
armed, a hold on the bar saves a new preset as it always does, no
refusal is said, and the learn stays armed
(`tests/test_desk.py::test_the_clip_stop_row_is_invariant`). Two
things this build does **not** do, so they are not fails: the on-screen
desk lights the bar while it is held but does not blink, and the cheat
sheet does not name the bar. **Superseded in part by plan 19** (check
83; register row 72): the bank is twenty-four, so **the next empty slot
may be a far one** — after F8 the save goes to slot 9 (slot 10 on the
factory party show, where TRACER holds 9), the new slot's pad on clip
row 4 or 5 blinks, and the footer says "→ slot 10"; (d)'s "the bank is
full" comes only once all twenty-four are filled. *Fail:* a tap saving →
the hold time (`midi.HOLD_S`, `MidiIO._handle`); a save into a taken slot
or over a file → `Project.next_empty`, `library.next_name`; no blink →
`apc40.blink_of` and the blink in `MidiIO.feedback` (if the clip-stop
LEDs never light or never blink on this device, note what they do
instead: the velocities are from Akai's table, never seen on the mk1;
the save does not depend on them, and the footer's line is the sign);
the row going dark at 0.6 s with no blink and no new preset → the save
itself failed, by design shown that way (`Project.save_new` returned
False; the reason is on the PRESETS page, `bank_error`); two presets
from one hold → the bar rule in `MidiIO._fire_holds`; the row doing
nothing → its rows (`apc40.DEFAULT_MAP`; your `bindings.json` after
check 57).

**57. The first launch brings your `bindings.json` up to date, with a backup (plan 15 WP1–WP4).**
Headless: `uv run pytest -q tests/test_routing.py -k "older_file or old_crossfader"`.
Before the first launch of this build, `ls -la ~/Hyperspace`. Launch and
read stderr. *Pass:* one `backup:` line naming `bindings.json.bak-v3`
(or a dated name if you already had one), and one line per change:
`remapped cc:0:15: overlay.bg → output.dim (the APC40 map of plan 15)`;
`added note:0:64 → preset.home (the APC40 map of plan 15)`; eight lines
`added note:0:52 → preset.save_new (the APC40 map of plan 15)` …
`note:7:52` for the clip-stop buttons; and `added key:… (the keys of
plans 09, 11 and 15)` for ⌘Z, ⌘⇧Z, Ctrl+Z, Ctrl+⇧Z and Home. The ROUTING
page's session section lists X → `output.dim`, B11 → `preset.home`, and
G6·1–G6·8 → `preset.save_new  hold` under "invariant · both layers". A
crossfader, OVERDUB or clip-stop row you had changed by hand is left as
you had it (and that control then does what you set, not this plan's
job); a key you had already put on one of those chords keeps yours.
Launch again: stderr says nothing and no file's time moves. One thing to
know: a row is added wherever **nothing uses the control**, so if you
later *delete* the OVERDUB row or a clip-stop row from `bindings.json`
it comes back on the next launch (as METRONOME's does); to switch a
button off, keep its row and add `"enabled": false`. **If your
`bindings.json` was itself made on this launch from a pre-plan-09
`midi_map.json`**, the first launch only converts the old file, and the
OVERDUB row and the eight clip-stop rows are added on the *second* launch,
which says so on stderr
(`tests/test_routing.py::test_old_midi_map_migrates_into_bindings_json`;
METRONOME's row always arrived this way). Then load
each preset you saved on the night: if one had learned a control onto
OVERDUB or a clip-stop button, that row is dropped at the load, the
ROUTING head says "desk: dropped … that control is invariant", and the
row is gone from the preset when you next save it (the old file goes to
the trash, check 53). **Superseded in part by plan 19** (check 84;
register rows 73, 74): the first launch of a build with plan 19 adds
**sixteen more rows** — `added note:0:56 → preset.select (the APC40
map of plan 19)` through `note:7:57`, the bank's pads on clip rows 4–5
— in the same rewrite with the same backup, wherever no MIDI row of
yours is on the pad; the summary is also one line on the SYSTEM page
("bindings.json updated (N rows changed), the old file kept as
bindings.json.bak-v3 — each change is on stderr"); and if the backup
cannot be made the file is **not** rewritten at all (the line then
says so, and the next launch tries again). The shape pads in your
presets drop at load **without** a note (check 83). *Fail:* no backup → `routing.backup` in
`Bindings.load`; a row of yours replaced → `routing.remap_factory` (it
may only swap the exact factory row — one caveat: a crossfader row of
yours that was *identical* to the old factory row cannot be told from it
and is swapped; the backup has it); the notes every launch → the remap
is not finding its own rows.

## L. Plan 16 — paper cuts — added 2026-10-04

Run on `finish-line` once plan 16 is merged into it (PRs #89 the cheat
sheet, #84 the FX chips, #86 the idle strip, #85 window placement, #90
instances and the dream's layer, #92 four follow-ups). Laptop first
(58–60, 62, 63), then the projector (61). About 20 minutes. First,
headless: `uv run pytest -q tests/test_fx.py tests/test_placement.py tests/test_ui_shell.py tests/test_render.py`.
No config change unless a check says so. None of this has been tried by
a person: it was shown by tests, pictures from a hidden window or an
offscreen render, and scripted launches on a one-screen laptop
(`16-paper-cuts.md` §7). Decision register rows 45–49 are the calls
these checks let you confirm or overturn.

**58. The cheat sheet is off at launch (plan 16 WP1).**
Headless: `uv run pytest -q tests/test_ui_shell.py::test_the_cheat_sheet_is_off_at_launch_and_the_desk_is_on tests/test_ui_shell.py::test_slash_still_toggles_the_cheat_sheet tests/test_ui_desk.py::test_the_desk_does_not_jump_when_the_sheet_comes_up`.
`uv run hyperspace`. *Pass:* the control window opens with no key legend;
the APC40 diagram sits in the bottom-left corner; `/` shows the legend
with the diagram above it, already in its place on the first frame (no
flicker of the diagram somewhere else); `/` again hides it and the
diagram drops back; the SYSTEM page's "Cheat sheet" box follows, and its
hover says `/` toggles; with the APC40 in, DETAIL (B9) does the same and
its LED is dark at launch. Quit and relaunch with the legend showing:
it is off again (it is not remembered). *Fail:* the legend showing at
launch → `Panel.__init__`; the diagram gone, or floating with a gap
under it → `ui_desk.diagram`'s `below`; the diagram jumping on the first
`/` → `Panel._draw_cheatsheet`'s `_sheet_h`; `/` dead → the `key:SLASH`
row (`routing.py`, your `bindings.json`).

**59. An FX chip opens without switching (plan 16 WP2, register row 45).**
Headless: `uv run pytest -q tests/test_fx.py::test_a_chip_click_selects_and_never_toggles tests/test_fx.py::test_the_chips_led_toggles_and_never_selects tests/test_fx.py::test_selection_is_by_name_and_survives_a_reorder tests/test_fx.py::test_selection_survives_a_preset_load`.
F5 (TRIP), FX page. The chips are **three to a row** (four rows for the
twelve effects), each with a dot or a ring at its left end. Click the
name of an effect that is off. *Pass:* its strip opens, the chip gains a
white outline round the whole chip, and it stays off (not red, a ring at
its left end, the render unchanged). Click the ring at the chip's left
end: the effect switches on, the chip goes red and the ring becomes a
filled dot, and the strip that is open does not change. Hover the dot:
"on — click to switch off". Open the kaleidoscope and drag its order
slider end to end: the strip stays the kaleidoscope's the whole way
while its chip moves along the rows. Press F6, then F5: the same effect
is still open. Read the names: only the two longest should be cut short.
*Fail:* a click on the name switching the effect → `ui_fx._chip` (the
name's item); the strip jumping to another effect while the order moves
or on an F-key → `FxState.selected` / `sel_name`; the dot hard to hit
from where you stand, or hit by mistake when you meant the name → fork
F1, say so (register row 45); names cut short that matter, or the fourth
row costing too much of the page → `ui_fx.CHIPS_PER_ROW`.
*Plan 20:* a chip whose effect is aimed at the faces has a diamond where
the dot or ring is (filled while on); the name is also what a chip is
dragged by — a click still only opens it (check 94); dragging the order
slider is now one of two ways to reorder. The open strip's blend row is
blend, **target**, order. The "preset load resets this stack" note under
the status is one line, where plan 16's pictures
(`assets/16-paper-cuts/`) show two.

**60. An effect that is not running says why (plan 16 WP3, register row 46).**
Headless: `uv run pytest -q tests/test_fx.py::test_an_off_effects_strip_says_so_and_turn_on_switches_it_on tests/test_fx.py::test_a_bypassed_stack_says_so_on_the_strip tests/test_fx.py::test_the_idle_strips_controls_stay_live`.
FX page, open an effect that is off. *Pass:* under its description a
line reads "off — nothing below shows until it is on" with a **turn on**
chip; the "on" box is at full strength and the faders under it are
dimmed (a veil over them) but still move, and right-click → Learn on one
of them opens a menu at full strength; **turn on** switches the effect
on and the line and the dimming go. Untick "Effects" at the top: the
open strip reads "the whole stack is bypassed" with **effects on**. Pull
FX mix to 0: "FX mix is at 0". Pull the effect's own mix to 0: "its mix
is at 0", and that one fader is not dimmed. No page scrolls in any of
these. Say whether the dimming reads from a step back: too faint to
notice, or so strong the values cannot be read. *Fail:* no line, or the
wrong reason → `ui_fx.why_idle`; the faders dead while dimmed → the
strip was disabled, not dimmed (fork F2); a dimmed menu → the veil is
being drawn over a popup (`ui_fx._dim`); the page scrolling → the line's
row, `tests/test_fx.py::test_the_page_fits_with_the_tightest_strip_idle`.
*Plan 20:* one more reason, after "off" and before "bypassed": an effect
aimed at the faces while Faces is off reads "aimed at the faces, and
Faces is off" with a **faces on** chip (check 91;
`tests/test_fx.py::test_why_idle_names_faces_off`).

**61. The windows open where you left them (projector; plan 16 WP4, register row 48).**
Headless: `uv run pytest -q tests/test_placement.py tests/test_app_boundary.py::test_the_windows_open_where_placement_says tests/test_app_boundary.py::test_the_exits_save_the_windowed_rects tests/test_app_boundary.py::test_a_config_screen_that_cannot_be_used_is_minus_one_and_one_note tests/test_config.py::test_a_screen_that_is_not_a_number_is_minus_one_and_a_note`.
**This is the first time any of it meets a second screen**: the build
machine had one, so everything about two screens — which index is the
projector, a window opening on it, its coordinates — was exercised with
made-up screens only.
(a) Laptop alone: drag and resize both windows, Esc. Relaunch. *Pass:*
both where and as big as they were; `~/Hyperspace/windows.json` exists
with one `control` entry and one entry in `render`.
(b) Plug the projector in. Drag the render window onto it, Esc,
relaunch: it opens on the projector, the control window on the laptop.
(c) Set `[output] fullscreen = true` (leave `monitor` at −1), relaunch:
fullscreen on the projector with no drag. Esc, open `windows.json`: the
render entry is still the windowed size, not the projector's.
(d) Unplug the projector, relaunch: the render window opens on the
laptop at the default spot, and the terminal and the SYSTEM page name
the screen it was last on. Put `fullscreen` back.
(e) Projector in again. Set `[output] monitor = 0`, `control_monitor =
1`, relaunch: the windows are swapped — render on screen 0, controls on
screen 1 — whatever the file said. Set `monitor = 7`: the SYSTEM page
and the terminal say "monitor = 7, but 2 screens are connected (0–1) —
using the last position", and the last position is used. Set `monitor =
"left"`: the app still launches, and the note reads "monitor = 'left' is
not a screen index — using the last position". Remove both keys.
(f) Delete `windows.json`, relaunch: the placement of before — render
top-left, controls flush right, on the primary screen, at their full
sizes (on a small laptop screen they overlap and may overhang it, as
they always did).
(g) ⌘R with a window moved: after the restart it is where you moved it.
One thing to know: a screen index that is not there **at launch** is
ignored for the whole run, so with `monitor = 1` in the config, plug the
projector in *before* launching (or pick it on the OUTPUT page's Screen
combo).
*Fail:* a window off every screen, or not where it was →
`placement.place` / `usable`; the wrong screen for an index →
`placement.screens` (GLFW's monitor order, as check 26); the fullscreen
size in the file → `Output.windowed_rect`; no file after Esc →
`app._save_windows` at the end of `app.main`; the app not launching with
`monitor = "left"` → `placement.read` / `config.load`; a window that
cannot be reached at all → delete `windows.json`, and log it.

**62. Instances to zero (plan 16 WP5, register row 47).**
Headless: `uv run pytest -q tests/test_render.py::test_zero_instances_draws_only_the_ground tests/test_render.py::test_zero_instances_still_runs_the_look_back_and_the_effects tests/test_plan12_presets.py::test_no_factory_hand_row_blanks_the_scene tests/test_params.py::test_instances_read_nothing_drawn_at_zero tests/test_undo.py::test_a_count_taken_to_zero_is_undone`.
F1 (TUMBLE), VIEW page: drag Instances to the left end. *Pass:* it reads
"0 · nothing drawn" and the render is black; ⌘Z brings the count back;
back to 1 by hand, the shape is there. With the APC40: track knob 3 (K3)
fully left does the same — **the bottom of that knob is now nothing
drawn, not one copy**; say if that is too easy to land on. F4 (WAKE):
take the count to 0 — the trail fades out over black rather than
cutting. F5 (TRIP), count 0: the effects that paint on their own
(plasma, with its level up) still show. F3 (FIELD) with a hand in the
box: right hand at the bottom of the box is nine copies, never none; at
the top the room fills as before (69 copies, one more than before).
With ghost hands on, they still draw at 0. *Fail:* one copy still drawn
at 0 → `Renderer.draw_scene`'s clamp; a traceback or a frozen render at
0 → the same function (the red banner and `stall.log` will say); FIELD
blanking with a low hand → the row's rest
(`tests/test_plan12_presets.py`). Not a fail, and for you to know: a
route of your own that pushes both ways (an LFO onto Instances with the
count at 1) now blanks the scene for half its cycle.
*Plan 20:* above one copy the VIEW page shows one field row under the
count — layout, motion and, while moving, amp and rate — and 0 and 1
copy are the same in every layout (check 97). With an effect aimed at
the faces, the FX page's faces row reads "(no copies to show them)" at
0.

**63. The dream's layer cannot be performed (plan 16 WP5, register row 49).**
Headless: `uv run pytest -q tests/test_lookback.py::test_dream_params_declared tests/test_lookback.py::test_a_route_on_the_dream_layer_is_dormant`.
LOOKBACK page, right-click the Layer combo. *Pass:* the menu reads "not
modulatable" where other controls offer "Route a lane here…"; on the
ROUTING page, adding a route, `dream.layer` is not in the target list;
the combo itself, a preset and a learned knob still change the layer.
If one of your saved presets had a route onto the layer, load it: the
row is still listed on the ROUTING page and does nothing; hovering its
target says "dream.layer is not modulatable — the row is dormant", and
nothing says so when the preset loads. *Fail:* a route offered or listed → the flag on
`dream.layer` (`params.py`).
*Plan 20:* the Layer combo is now a row of six chips in the LOOKBACK
page's DREAM section (right-click any of them for the menu), and the
param is called "Dream layer" on ROUTING and in a Learn's line (check
95).

## M. Plan 17 — Learn, Unbind and seeing the desk — added 2026-10-04

Run on `finish-line` once plans 17 and 18 are merged into it (PRs #93
one Unbind, #96 Learn desk / hand, #99 the menu on labels and meters,
#91 the ROUTING filter, #102 the desk big and clickable). 64, 68, 69 and
71 run on the laptop alone; 65, 67 and 70 need the APC40; 65, 66 and 67
need the camera and the box, so **run check 72 (calibration) before
them**. About 35 minutes. Use a copy of the home: `cp -R ~/Hyperspace
~/Hyperspace-2026-10-04` if that copy does not exist yet. **None of this
has been tried by a person, and nobody has clicked, right-clicked or
typed in the real control window**: it was shown by tests that feed
imgui its mouse and keyboard events, pictures from a hidden window, and
scripted launches on a laptop with no desk and no camera
(`17-learn-and-the-desk.md` §7). Decision register rows 57–64 are the
calls these checks let you confirm or overturn. Since plan 18 a hand
learn lands as "pushes +0.25" or "positions" by its own table (checks
75, 76) and takes the axis's other rows with it (check 77); the lines
quoted below allow for both.

**64. One Unbind, with or without the desk (plan 17 WP1, register row 59).**
Headless: `uv run pytest -q tests/test_learn.py::test_unbind_removes_the_presets_desk_rows_and_every_route tests/test_learn.py::test_unbind_is_one_undo_step_and_none_when_nothing_goes tests/test_ui_shell.py::test_the_menu_lists_and_unbinds_with_no_midi_adapter tests/test_ui_shell.py::test_unbind_is_not_offered_on_a_session_only_param`.
APC40 unplugged, `[midi] enabled = true`. F1 (TUMBLE). VIEW page,
right-click Speed. *Pass:* under the id the menu lists "K2 (track knob
2)" and the right hand's height route in ROUTING's words (with the
tracker on, "R height pushes …"), then **Learn desk**, **Learn hand** (a
submenu: left, right; only with the tracker on), one **Unbind** that
opens a submenu — "desk — K2", "route — R height", "both" — then, with
the tracker on, "Gate: none", and "Route a lane here…". There is no "Unbind hand" and no "performed by …" line. Choose
**both**: on the next right-click the two lines are gone and so is
Unbind, the preset's dot is lit, and the footer said "unbound view.speed
from K2 (track knob 2) and R height pushes …". ⌘Z: both are back
("undid unbind view.speed"). Right-click Brightness (a knob and the two
step buttons, no route): the lines read "K1 (track knob 1)", "B16 (▲) ·
step +3", "B17 (▼) · step -3" and Unbind is a plain item, no submenu.
Now set `[midi] enabled = false`, relaunch, and do it again: the same
lines and the same items. AUDIO page, right-click Input trim (S8's
param): the line reads "S8 (track fader 8) · invariant", dim, and there
is no Unbind. (The drive fader is not the one to try on TUMBLE: the left
hand's height is routed onto it, so its menu rightly offers Unbind for
that route.) Put `[midi] enabled` back. *Fail:* no desk line with MIDI
off → `Panel._ctx_lines` / `Panel._table` reading `self.midi`; an Unbind
that only refuses → the offer rule in `Panel._ctx_unbind`; ⌘Z brings
back half → `Learn.unbind` pushed twice or after the change; a line the
Unbind did not remove, or the reverse → `learn.bound`.

**65. A desk learn listens only to the desk, and the session's controls work through it (plan 17 WP2, register rows 60–62; this is check 37 as it now runs).**
Headless: `uv run pytest -q tests/test_midi.py::test_an_invariant_control_works_through_a_desk_learn tests/test_hands.py::test_the_hands_never_complete_a_desk_learn tests/test_learn.py::test_learn_refuses_the_global_layer_and_invariant_controls tests/test_ui_shell.py::test_the_footer_says_what_a_learn_waits_for_and_what_it_did`.
APC40 in, camera on, F1. VIEW page, right-click 4D depth → **Learn
desk**. *Pass:* its control is framed red and the footer reads, in red,
"learning view.depth4 — turn a knob or press a button on th…" (cut to
the room it has; the whole line, ending "…or click one on the diagram…
(click to cancel)", is on its hover) on every page. Wave both hands
through the box for five seconds: the learn is still armed and no new
route appears on ROUTING (TUMBLE's own right-hand route still moves the
depth; that is the preset, not the learn). Move S3 a little: the third
band's drive moves, nothing is said, the learn is still armed. Tap TAP
TEMPO: it taps. Press SHIFT: its LED lights and the desk's header says
GLOBAL LAYER. Turn K2: the footer says, in the warning colour, "K2
(track knob 2) is on the global layer (the session's) — latch SHIFT off
to learn into the preset" for four seconds, then the red "learning …"
line is back — **still armed**; K2 did not move Response (while a desk
learn is armed under SHIFT every control but the session's own is
swallowed this way: say if that is a trap). Press SHIFT again, turn D5:
"learned view.depth4 ← D5 (device knob 5) (into the preset)", D5's ring
lights and follows, the frame and the red line go. One more thing to
know, and to try once: arm **Learn desk** again and press a preset pad
on clip row 1 — **the preset loads and the learn is still armed**, so
the next knob lands in the preset you just loaded (no test presses a
preset pad mid-learn; this is from reading `MidiIO._handle`). Click the
footer's red line to cancel. *Fail:* the hands took it →
`HandsIO._learn`'s guard (`Learn.accepts`); the fader or TAP ended the
learn, or SHIFT did not latch → the learning branch of
`MidiIO._handle`; the learn gone after the K2 refusal →
`Learn.learn_control` took before refusing; no line in the footer →
`Panel._footer` / the `"learn"` key of `Panel._message`.

**66. A hand learn listens to one hand (plan 17 WP2 — the session's "wrong hand"; register row 60).**
Headless: `uv run pytest -q tests/test_hands.py::test_a_hand_learn_listens_to_one_hand tests/test_hands.py::test_a_rearm_starts_a_fresh_baseline tests/test_learn.py::test_accepts_by_want`.
Camera and box, calibrated (check 72). F1. Keep the left hand still in
the box. With the right hand on the trackpad, CAMERA page, right-click
Zoom → **Learn hand ▸ left**. Now bring the right hand back over the box
and move it about freely for five seconds. *Pass:* nothing is learned;
the footer reads "learning camera.zoom — move the left hand… (click to
cancel)". Raise the left hand slowly: the footer says "learned
camera.zoom ← hand left.y positions (into the preset; moved from
master.gain)" — height onto zoom is the fader (check 76), and TUMBLE's
own left-height row on the audio drive goes with it (check 77; one ⌘Z
brings it back) — ROUTING lists the new route as "L height", and Zoom
follows the left hand only. (Had a tilt travelled furthest the line
would name it, "hand left.roll pushes +0.25" or the like: any
left-hand axis is a pass.) ⌘Z, then repeat with **Learn hand ▸
right** and the hands swapped. Then arm **Learn hand ▸ left**, click
the footer's line to cancel, arm it again at once and keep both hands
still: nothing is learned until the left hand moves. *Fail:* the right
hand took it → the `moved` list in `HandsIO._learn`, or `Learn.accepts`
on the address (`hand:left.` must be the prefix `HandsIO.address`
writes); learned at once on arming → the baseline's key (`_learn_key`:
the param, the want and `Learn.armed_n`); the wrong *axis* of the right
hand, again and again → say so: that is fork 11 (register row 64), not a
fail of this check.

**67. A knob bump during a hand learn does its own job (plan 17 WP2, register row 60).**
Headless: `uv run pytest -q tests/test_midi.py::test_a_knob_bump_during_a_hand_learn_does_its_own_job`.
APC40 and camera, F5 (TRIP), hands out of the box. VIEW page,
right-click Speed → **Learn hand ▸ right**. Turn D1 and press a clip pad
of row 4. *Pass:* FX mix moves with D1 and the shape changes; the footer
still reads "learning view.speed — move the right hand…"; ROUTING's desk
has no new line and K2 still has Speed. (**Since plan 19** a pad of
row 4 is a bank slot: a filled one loads its preset — the learn still
armed, now in that preset — and an empty one says "slot N: an empty
slot"; turn the cue knob for the shape instead.) Click a control on the on-screen
desk: nothing happens (a hand learn is armed). Click the footer's red
line: the learn is cancelled and the frame goes. *Fail:* D1 now drives
Speed → `MidiIO._handle` did not ask `Learn.accepts`; the desk click
mapped something → `ui_desk.click` / `Learn.learn_control`'s own
`accepts`; the footer's line does not take the click → `Panel._footer`
(`imgui.is_item_clicked` on a text item: no test clicks it).

**68. The menu opens from the label and from every meter (plan 17 WP3).**
Headless: `uv run pytest -q tests/test_ui_shell.py::test_a_rows_label_opens_its_params_menu tests/test_ui_shell.py::test_every_meter_has_the_band_select_menu tests/test_ui_shell.py::test_the_menu_offers_learn_desk_and_learn_hand`.
Laptop alone. CAMERA page: right-click the word ZOOM. VIEW page:
right-click the word BRIGHTNESS above its fader. ANALYZER page:
right-click the fourth meter, choose Learn desk, then cancel it from the
footer. BITMAP page: right-click the file's name. *Pass:* the first two
open that param's menu at the mouse, the same menu its slider opens, and
the value does not move; the meter opens `band.select`'s menu without
selecting the band (a left click still selects it), and while it is
armed every meter is framed red; the file's name offers no Learn item at
all, over a dim "not modulatable". With the tracker off there is no
"Learn hand" anywhere; on the HANDS page's own settings (Steadiness,
say) there is "Learn desk" and never "Learn hand". Known and not a fail:
a label a page draws by itself opens nothing (FX "blend", LOOKBACK's
"from", "scene", "path"), and on the LFO page the two nudge chips' menu
lists its items twice (audit U9). *Fail:* nothing opens on a label →
`Panel._ctx_label` (it and the widget's `_ctx` must build the same id,
`Panel._ctx_id`, inside the same id scope); a two-finger click on the
trackpad does not count as a right-click → say so, with the page.

**69. The desk from a step back (plan 17 WP4, register row 57; this is check 45 at the new size).**
Headless: `uv run pytest -q tests/test_ui_desk.py::test_the_desk_takes_the_room_it_has tests/test_ui_desk.py::test_the_big_desk_labels_every_lit_control_and_never_scrolls tests/test_ui_desk.py::test_the_small_desk_draws_glyphs_only tests/test_ui_desk.py::test_a_controls_text`.
F5 (TRIP). With the panel open the desk fills the column left of it,
glyphs only. Press H (or DEVICE ON/OFF, B6, on the APC40, or the `big`
chip at the right of the desk's header). *Pass:* the panel goes and the
desk fills the control window; every lit control carries a name with its
glyph small in the top-left corner, and a dark control only its glyph;
the bank row reads TUMBLE … NOITA with TRIP lit green; the track knobs
read Brightness, Speed, Instances, Pattern mix, Grid amp, Grid rate,
Bitmap alpha, Zoom; the device knobs FX mix, Plasma level, Kaleidoscope
segments, Kaleidoscope zoom, Zoom burst amount, Zoom burst glow, Hue
cycle paint, Hue cycle spread; the clip-stop row reads "Save as a new
preset" once across the bar; the names of the faders, the bank row, the
band rows, Tap tempo and Shift are grey (the session's, the same on both
layers) and the preset's are white. Nothing overlaps and the window has
no scrollbar. Step back two paces and say which names you can read: at
960 × 900 most are 13 px, about a dozen are 11 px (the duoprisms, the
two Kaleidoscope knobs, Click-through, Control panel, audio.restart),
five are cut with an ellipsis (three duoprisms, and ▲ ▼ as "Brightne…
+3 / −3"), and three buttons show an id (audio.play, audio.stop,
audio.restart: they have no name of their own). Hover a control: "D3 ·
fx.kaleido.segments · Kaleidoscope segments · preset layer", Akai's
name, and what a click would do. With the APC40: press SHIFT — the
header reads GLOBAL LAYER · SHIFT in red, K1–K5 read Steadiness,
Response, Catch, Return, BPM, D1–D8 the band strip, clip rows 2–3 the
scenes, and every preset control is dark. The `panel` chip (or H) brings
the panel back. Labels beside the open panel need a desk about 620 px
wide, so a control window about 1200 px wide: the panel is placed once,
at launch, so after widening the window drag the panel to the right edge
(or quit and relaunch: the size is remembered, check 61) — the desk left
of it then carries its names. Press `/` with the panel hidden: the desk
moves over to sit beside the cheat sheet. Hold the APC40 beside the
screen: each control is where the drawing says (check 45's walk).
**Since plan 19** (register row 73) clip rows 4–5 are bank pads too: a
filled one amber at half strength with its preset's name in the bright
ink (on the factory party show G4·1 reads TRACER), an empty one dark with
no label — the same on both layers. *Fail:*
names cut to nothing → `ui_desk.wrap` / `ui_desk.label_px`; the desk
under the panel → `Panel._panel_x` not recorded (`Panel._draw`) or
`ui_desk.room`; the desk and the cheat sheet overlapping →
`Panel._sheet_w` / `room`; not readable at two paces at 960 × 900 → say
so: the remedy is the control window's size (plan 16's placement), or
`ui_desk.LABEL_PX`.

**70. Click a control; click a param (plan 17 WP4, register rows 58 and 62).**
Headless: `uv run pytest -q tests/test_ui_desk.py::test_a_click_picks_and_a_second_click_lets_go tests/test_ui_desk.py::test_a_pick_lets_go_by_itself tests/test_ui_desk.py::test_a_click_completes_an_armed_desk_learn tests/test_learn.py::test_pick_then_param_maps_through_the_learn tests/test_learn.py::test_a_pick_on_an_invariant_control_or_the_global_layer_maps_nothing tests/test_ui_shell.py::test_a_click_on_a_param_maps_the_picked_control tests/test_ui_shell.py::test_a_picked_control_dims_every_page_but_routing tests/test_ui_shell.py::test_the_footer_says_what_is_picked_and_a_click_lets_go tests/test_ui_routing.py::test_goto_scrolls_the_rows_child_to_the_controls_line`.
**The first real clicks any of this gets.** APC40 in, F1, ROUTING page
open. *(a)* Click D6 on the desk. *Pass:* D6 is framed red on the desk;
ROUTING's rows scroll (the rows only, not the page) to D6's line — "D6
unmapped — dark" or its row — framed red; ROUTING is **not** dimmed and
the footer reads "D6 picked (20 s): click a param on any other page",
counting down. *(b)* Open VIEW: the page is dimmed and **takes no
input** — no slider moves, no menu opens; the rail and the footer still
work. The footer reads "D6 picked (… s): click a param to put it here
(click to let go)". Move the mouse over Speed: it is framed red, with
"click: put D6 on Speed". Click it: "learned view.speed ← D6 (device
knob 6) (into the preset); K2 let go" (cut in the footer; whole on its
hover and on ROUTING's head); Speed did not move; the page is bright
again; D6's ring on the device lights and turning it moves Speed; K2 is
dark. ⌘Z: D6 is as it was and K2 has Speed. *(c)* The 20 seconds: click
D6 again, open VIEW and take your hands off. The count runs down, the
page comes back by itself and the footer says "D6 let go — no click for
20 s". Any click anywhere in the window starts the count again. *(d)*
Letting go by hand: pick D6 and click it again; pick it and click the
ground between two controls; pick it and click the footer's line. Each
lets go at once. *(e)* The big desk: press H, click D6. The panel comes
back with VIEW dimmed and something under the mouse. **Click again
without moving the mouse: nothing is mapped and nothing moves** — a
click maps only once the mouse has moved about 12 px from where it
picked. Now move to Speed and click: mapped. ⌘Z. *(f)* Click S2: the
desk's header reads "S2 (track fader 2) is invariant (the session's):
BASS Post-drive", VIEW is not dimmed, ROUTING scrolls to S2's line under
"session". Latch SHIFT, click K1: "K1 (track knob 1) is on the global
layer (the session's) — latch SHIFT off to map into the preset:
Steadiness", not dimmed. *(g)* With SHIFT off: right-click Brightness →
**Learn desk**, then click D7 on the desk instead of turning it:
"learned view.bright ← D7 (device knob 7) (into the preset); K1 let go",
and K1 goes dark (▲ and ▼ keep Brightness). ⌘Z. *(h)* Pull the APC40's
cable and map D8 the same two ways: the same lines, the dot lit.
Say, for the register: whether the dimming reads as "the page is
waiting for a click" (it is imgui's plain disabled look), whether 20 s
is too short to change page and find a param, and whether you would
rather the click opened ROUTING. *Fail:* the click on Speed moved the
slider → the disabled wrap in `Panel._draw`; nothing maps, or no frame
under the mouse → `Panel._ctx_pick` (`allow_when_disabled`,
`ui_desk.armed`); the second click in *(e)* mapped → `ui_desk.armed` /
`PICK_MOVE`; the page never came back → `ui_desk.tick` (`PICK_S`);
ROUTING's whole page scrolled → `set_scroll_here_y` called outside the
`##routes` child (`ui_routing._mark_line`); a map landed under SHIFT or
on a fader → `learn.blocked`.

**71. The ROUTING filter (plan 17 WP5, register row 63).**
Headless: `uv run pytest -q tests/test_ui_routing.py::test_the_filter_matches_glyph_param_and_source tests/test_ui_routing.py::test_a_filtered_page_draws_only_matching_lines_and_keeps_its_ids tests/test_ui_routing.py::test_the_filter_is_ui_state tests/test_ui_routing.py::test_typing_in_the_filter_is_imguis_keyboard_not_the_apps tests/test_ui_routing.py::test_a_line_in_use_is_not_filtered_away_under_the_hand tests/test_ui_routing.py::test_a_desk_click_clears_a_filter_that_has_the_keyboard`.
**Nobody has typed in this field.** F7 (MANDALA), ROUTING page. Click
the field that says "filter", on the counts line left of `+ route`, and
type `kaleido`. *Pass:* only the kaleidoscope's lines remain — the two
right-hand routes (R depth → `fx.kaleido.zoom`, R roll →
`fx.kaleido.swirl`) and the desk lines D3 and D4; MACROS and SESSION
each say "no row matches" unless a macro subscribes to one of them; the
counts read "n of m rows" in red, m being every line of the page (some
170); a × chip sits beside the field. While typing, no key does anything
else (B, F, R, the number keys). Clear it and type `d3`: one desk line.
Type `r roll`: that route. Type `lfo 1` on F5 (TRIP): LFO 1's route —
and any route from LFO 2 would show too (its source is `lfo:1`); say if
that matters. With `kaleido` typed, press F5: the filter is still there,
now over TRIP's rows. With a filter set, press `+ route`: **the new
route may not be shown** (it shows only if it matches); the red count is
the only sign — say if that is a trap. Drag a filtered route's depth, or
retype a macro's label so it stops matching: the line stays under your
hand until you let go. Click the ×: every row is back. Type a filter
again and, with the caret still in the field, click a control on the
desk: the filter clears and the rows scroll to that control's line. Also
try Esc, backspace and ⌘Z with the caret in the field and say what each
did (none was tried). *Fail:* a row deleted with × was not the one shown
→ the row's index (`_row`'s `k` must be its place in the unfiltered
list); the page scrolls → the field added a line (`ui_routing.page`);
the filter comes back after a desk click → `ui_routing._find_field`'s
`unfind`; a key typed in the field also fired its shortcut → `app.Keys`
(`typing`).

## N. Plan 18 — the box, a learn's default, knob smoothing, two hands on the camera — added 2026-10-04

Run on `finish-line` once plan 18 is merged into it (PRs #94 the
interaction box, #98 knob smoothing, #100 what a hand Learn lands with,
#97 `hands-orbit`). All of it needs the camera and the box; 74, 78 and
79 also need the APC40. About 40 minutes. Whether the rig was calibrated
on Oct 3 is not known, so **72 comes first** and everything after it
assumes its box. Before the first launch: `cp -R ~/Hyperspace
~/Hyperspace-2026-10-04` if that copy does not exist yet. None of this
has been tried by a person or seen by a camera: it was shown by tests on
synthetic hands and fake MIDI ports, pictures from a hidden window,
offscreen renders, and scripted launches on a laptop with no camera and
no desk (`18-hand-and-knob-feel.md` §7). Decision register rows 50–56
are the calls these checks let you confirm or overturn. The Learn items
named below ("Learn hand ▸ left / right") are plan 17's menu; its own
checks are group M's.

**72. Calibrate, and the box it draws (plan 18 WP1, register row 50; replaces the pass text of check 15).**
Headless: `uv run pytest -q tests/test_hands.py::test_the_sweep_sets_the_box_with_its_margin_and_a_symmetric_x tests/test_hands.py::test_an_old_hands_json_reads_as_before_and_is_not_rewritten_at_load tests/test_hands.py::test_the_first_rewrite_of_an_old_file_keeps_a_backup tests/test_hands.py::test_two_still_hands_held_apart_are_not_a_sweep`.
Launch, HANDS page. Before touching anything: if `~/Hyperspace/hands.json`
existed, the page's ranges are the ones it held and the box view shows
**no inner rectangle** (an old file has no box); under "feel &
calibration" the line under the axis's range reads "box open".
**Clear the camera's view of everyone but you**: the box is off for the
whole sweep, so for those 20 seconds any hand the tracker sees performs
and is counted into the new box. Open "feel & calibration", press
**calibrate 20 s**, and move both hands through everything they should
reach: side to side, low to high, near to far, and each tilt end to end.
Each hand has to travel more than 12 cm in a direction for that
direction to get a bound; two hands held still and apart do not count as
a sweep. *Pass:* the note reads "calibrated 12 axes · box W × H × D mm
· the old file kept as hands.json.bak-v1" (the last part only if the
file existed before); the box view now has an inner rectangle and the
height gauge a bracket; both hands' dots are inside it wherever you
played; `hands.json` holds `"schema": "hyperspace.hands/2"` and a `box`;
if the file existed before, `hands.json.bak-v1` beside it is the old
one. Every axis still reaches both ends of its row (the box stands 40 mm
outside what you swept, so a hand at an end stop is still in). *Fail:*
"x open (not swept)" → sweep wider than 12 cm on that direction with one
hand and run it again; "box left as it was (too few palm samples)" → the
tracker barely saw a hand; no rectangle → `HandsIO._sweep_box`
(`hands/core.py`); no `.bak-v1` → `HandsIO.save_ranges` / `_keep`; the
rectangle hard against the frame's edge → the box is wider than the
view's scale and its faces are drawn clamped (not a fail: say whether it
reads).

**73. A hand outside the box reads absent, and the edge does not flicker (plan 18 WP1, register rows 50–51).**
Headless: `uv run pytest -q tests/test_hands.py::test_a_hand_outside_the_box_reads_absent_everywhere tests/test_hands.py::test_the_boxs_edge_has_hysteresis tests/test_hands.py::test_a_hand_re_entering_the_box_is_caught_not_jumped tests/test_hands.py::test_a_dip_in_confidence_does_not_evict_a_hand_in_the_edge_band`.
PRESETS: `hands-play` (R height positions brightness). Right hand in the
box, mid height. Move it slowly out through the right face. *Pass:* a
centimetre or two past the rectangle its dot turns into a hollow, dim
ring, the status line shows `R◌` (hover it: "tracked, but outside the
box"), its axis rows dim, and brightness is back at its base that frame.
Hold the hand right at the edge and wobble it a centimetre: brightness
does not flicker between the two. Bring it back in: the row glides onto
the hand (the catch), no jump. Repeat upward past the gauge's bracket
and toward yourself past the near face. Say whether `◌` can be told from
`●` and `○` at arm's length (it comes from another font and is smaller).
*Fail:* still performing far outside → `HandsIO.box` is `None` (72) or
the presence line in `poll`; flicker at the edge → `BOX_EDGE` /
`HandsIO._in_box`; a jump on re-entry → `hands.catch` is 0, or the lane
read `NaN` during the catch (`Follower.live`).

**74. A hand on the desk does not perform; the ghost; reset (plan 18 WP1, register rows 50–51).**
Headless: `uv run pytest -q tests/test_ghost.py::test_the_camera_frames_the_interaction_box_when_one_is_set tests/test_ghost.py::test_a_hand_outside_the_box_fades_out tests/test_hands.py::test_reset_ranges_opens_the_box`.
With `hands-play` still loaded and the APC40 where it will stand for the
show, reach for it and turn a knob with the right hand, the left hand
out of the way. *Pass:* brightness moves only by the knob; the right
hand's mark is a hollow ring (or gone) the whole time. If the dot is
filled while your hand is on the desk, the desk stands inside the swept
box: move it, or run 72 again keeping the sweep clear of it. With ghost
hands on (HANDS page), a hand leaving the box fades out at the frame's
edge and the frame shows the whole box. *Fail:* the ghost still drawn
outside → `HandsIO._skeletons`; the frame not matching the box →
`ghost.box_of`. Last: press **reset ranges**. *Pass:* the rectangle and
the bracket go, the note reads "ranges back to the defaults, box open",
and a hand is present wherever the tracker sees it, as before this plan.
Then run 72 again to put the box back.

**75. A tilt learned onto speed and rotation is gentle (plan 18 WP3, register row 52).**
Headless: `uv run pytest -q tests/test_learn.py::test_a_centred_axis_learns_as_a_push_about_the_base_at_the_learn_depth tests/test_hands.py::test_learn_passes_the_axiss_centredness_and_the_sessions_depth tests/test_hands.py::test_learn_depth_changes_only_the_next_learn`.
PRESETS: `hands-play` (it has no band rows on the rotation rates). VIEW
page: right-click Speed → Learn hand ▸ right, and roll the right hand.
Speed is already performed by L height, so the prompt asks: **Replace**.
*Pass:* the ROUTING row reads "R roll pushes +0.25"; **with the hand
level the speed is the preset's** (a learned roll reads the base when
level); a full roll either way takes it to about half and about double,
not to stop and flat out. Now the same onto a rotation rate (VIEW page,
"rotation", the XY rate) with the right hand's yaw: level leaves the
plane turning as the preset set it; a small turn nudges it. If rotation
is still more than you want, lower **Learn depth** on the HANDS page
under "feel & calibration" (0.10 is ±6.7× on a rate) and learn the right
hand's pitch onto another rate (XZ): that row carries the new number,
the two earlier rows kept their 0.25, and the learn line ends "moved
from view.depth4" — the preset's own R pitch row went with it (77).
Learning the same axis onto the same param again changes only its gate:
it never changes a row's "pushes" / "positions" or its depth, so a
full-range row you already have is tamed on ROUTING, or by Unbind and a
fresh learn. *Fail:* "positions" on a tilt → `HandsIO._learn` is not
passing `centred` (`hands/core.py`) or `Learn._row`'s table
(`learn.py`); the param jumps when the hand enters → the row has a
`rest` of its own.

**76. Height is still the fader where that makes sense (plan 18 WP3, register row 52).**
Headless: `uv run pytest -q tests/test_learn.py::test_a_one_sided_axis_on_a_one_sided_param_is_still_the_fader tests/test_learn.py::test_a_one_sided_axis_on_a_zero_centred_range_pushes_up_from_the_base tests/test_learn.py::test_a_discrete_target_keeps_the_position_row tests/test_learn.py::test_a_whole_number_param_keeps_the_position_row tests/test_learn.py::test_existing_rows_are_never_rewritten`.
Still on `hands-play` as 75 left it. Learn the left hand's **height**
onto a fader nothing performs yet (Pattern mix, say). *Pass:* "L height
positions": low is none, high is full, the hand is the fader as before.
Learn the left hand's height onto a rotation rate nothing performs (YZ):
"L height pushes +0.25" (or your Learn depth), and the Pattern mix row
is gone (77); with the hand low the plane turns as the preset set it,
and raising it speeds it up; it never runs backwards at the bottom, and
it can no longer stop the plane either. Learn any tilt onto a toggle
(Faces): "positions", and tilting past the middle flips it. Learn a tilt
onto Instances (a whole-number count): "positions" too. Load
`hands-play`, `hands-pinch` and F1–F8 in turn and open ROUTING on each:
every factory row reads as it did before this plan. *Fail:* a factory
row changed → a preset file was regenerated or a load converted rows
(neither may happen).

**77. A learn moves the axis (plan 18 WP3, register row 53).**
Headless: `uv run pytest -q tests/test_learn.py::test_a_learned_axis_drives_one_param tests/test_learn.py::test_a_learn_is_one_undo_step tests/test_learn.py::test_the_same_axis_again_only_refreshes_the_gate_whatever_the_op`.
F1 (TUMBLE): right roll turns the XW plane. Learn right roll onto
Brightness (Learn hand ▸ right, roll). *Pass:* the learn line says
"learned view.bright ← … pushes +0.25 (into the preset; moved from
rot.phase.XW)", ROUTING no longer has the XW row, and roll moves
brightness only. **That was the factory preset's own row: a learn on a
factory preset takes the preset's rows on that axis out**, switched-off
ones too. ⌘Z once: the XW row is back and the brightness row is gone.
Say here whether you would rather a learn *added* (the old row staying):
that is register row 53, one condition in `Learn._place`.

**78. Knob smoothing: judge 80 ms (plan 18 WP2, register row 54).**
Headless: `uv run pytest -q tests/test_app_boundary.py::test_the_app_starts_with_knob_smoothing_at_80_ms_and_a_show_keeps_its_own tests/test_midi.py::test_smoothing_is_off_by_default_and_every_write_is_immediate tests/test_midi.py::test_a_smoothed_knob_arrives_in_a_straight_line_and_rests_on_the_detent tests/test_midi.py::test_the_ring_shows_where_the_knob_is_going`.
APC40 in, F3 (FIELD) so a pan or zoom step is easy to see. SYSTEM page,
under "midi": **Knob smoothing** reads "80 ms" and the show's dot is
clean. Turn K8 (zoom) slowly. *Pass:* the zoom glides; when you stop it
settles within a blink and the ring sits where your fingers left it; a
fast spin neither lags behind noticeably nor overshoots; the ring never
crawls backwards under your fingers and the next turn carries on from
it. Drag Knob smoothing to "off" and turn K8 slowly again: the picture
moves in steps, as it always did (and the show's dot lights: the number
is the show's). **Judge 80 ms; turn it down or off on SYSTEM → Knob
smoothing if a knob feels late**; try 50 and 200 ms and leave it where
it feels right. That number is saved with the show. Move a fader (S1)
and the crossfader: they glide too, and a fader that had not been picked
up still does nothing until it reaches its value. Turn the cue knob
(shapes) and press a clip button: unchanged, one step a click. *Fail:*
the knob fights you or the ring runs behind → `MidiIO._ring_norm` /
`_rebase` (and check 31 if the ring misbehaves with smoothing off too);
a value that never settles → `MidiIO._glide`'s landing; "off" at launch
on a show that never saved the number → `app._desk_table` running after
`library.attach`. Set it to "off" and the desk is as it was before this
plan.

**79. A smoothed knob with everything else (plan 18 WP2, register row 54).**
Headless: `uv run pytest -q tests/test_desk.py::test_a_layer_switch_leaves_a_glide_to_finish tests/test_desk.py::test_a_preset_load_stops_a_glide_on_a_performance_param_and_not_on_the_dim tests/test_undo.py::test_a_smoothed_knob_turn_is_one_step tests/test_undo.py::test_undo_during_a_glide_holds tests/test_midi.py::test_a_glide_on_a_hand_owned_param_moves_the_return_value tests/test_midi.py::test_a_load_from_a_pad_ends_a_glide_before_it_steps`.
Knob smoothing at 250 ms (the maximum, to see it). Spin K1 (brightness)
and press F5 at once, then the same with F5's pad on the desk. *Pass:*
the look is TRIP's, with TRIP's brightness, not the knob's. Spin K1 and
latch SHIFT at once: brightness still arrives; K1's ring now shows the
global layer's value. Sweep K1 once, wait a second, ⌘Z: brightness is
back where it was before the sweep in **one** press, and the footer
names the value the sweep landed on. Sweep K1 and press ⌘Z while it is
still moving: it goes back and stays back. With a hand owning brightness
(`hands-play`, hand in the box), turn K1: the picture does not move;
take the hand out and brightness is where the knob put it. Slide the
crossfader to dim and press F2 mid-slide: the dim finishes arriving.
*Fail:* the knob's value winning over a load → `redraw(load=True)`'s
rule, or `poll`'s order (`_glide` after `_follow_table`); two presses to
undo one sweep → `SLEW_MAX_S` against `undo.SETTLE_S`. Put Knob
smoothing back where 78 left it.

**80. Two hands on the camera (plan 18 WP4, register row 56).**
Headless: `uv run pytest -q tests/test_presets.py::test_hands_orbit_is_five_pushes_onto_the_camera tests/test_presets.py::test_an_absent_or_level_hand_leaves_the_orbit_camera_alone tests/test_presets.py::test_each_orbit_axis_moves_its_camera_param_as_its_row_says`.
PRESETS: `hands-orbit` (in the list, on no F-key). Right hand in, level,
mid box: nothing moves. Slide it left and right: the camera orbits,
about a quarter turn each way. Tip the fingers up: it looks down onto
the shape. Left hand: side to side and reaching in pan; raising it zooms
in, to a little over double at the top (2.2×). Take both hands out: the
camera is back where the mouse left it. *Pass:* each move does the one
thing, a still hand is calm, and it can be taught in a sentence. **Judge
the directions** — nobody has: does a hand going right turn the scene
the way you expect, does reaching in pan up or down, is fingers-up
"look down" — and **judge the zoom**: its depth is 0.12 because the
plan's 0.3 (7.4× at the top) put the frame inside the shape, near black,
in an offscreen picture; 0.12 has not been felt either. Note any depth
or sign that wants changing (the five numbers in
`preset.hands_orbit_routes`), and whether this is the "orbit" you meant:
the version where the two hands turn the scene between them needs a new
axis and was not built (register row 56). Press R with a hand in the
box and say whether the camera resets (a review suspected it does not;
headless it did). If the preset is not wanted, hide it (plan 19).

## O. Plan 19 — twenty-four presets, the knobs, the list, the trash, git — added 2026-10-04

**Copy `~/Hyperspace` first, and run every check on the copy.** This is
the plan that renames, hides and trashes files in that folder, and the
presets saved on the night may have no other backup.

```
cp -R ~/Hyperspace ~/Hyperspace-before-19          # the one to keep
cp -R ~/Hyperspace ~/Hyperspace-try-19             # the one to play on
export HYPERSPACE_HOME=~/Hyperspace-try-19
```

Run on `finish-line` once plan 19 is merged into it (PRs #104 the bank
of twenty-four, #110 rows 4–5 of the desk, #115 the device knobs, #114
the dirty dot, #117 hide / rename / the trash, #119 the home in git).
Every check below runs in a terminal with that variable set; the app
then reads and writes only the copy (its `config.toml` included). Only
when 81–90 pass, open a new terminal without it and launch on the real
home; keep `~/Hyperspace-before-19` until a party has been played.
**81 and 84 are the first launch** — keep its stderr (`uv run hyperspace
2>&1 | tee ~/first-launch-19.txt`) — then 82, 83 and 85 with the APC40,
then 86–89 on the laptop, and 90 last (it turns git on in the copy).
About 40 minutes. Run the headless tests named first. None of this has
been tried by a person or been on the APC40: it was shown by tests (the
panel driven by imgui events a test feeds it, the desk through fake
MIDI ports), hidden-window renders and scripted launches on a laptop
(`19-presets-and-the-desk.md` §7). **Amber at velocity 5, the pads of
rows 4–5, the knobs' new choices and every popup are unseen.** Decision
register rows 72–78 are the calls these checks let you confirm or
overturn.

**81. An eight-slot show opens untouched, and the page holds twenty-four (plan 19 WP1; register row 72).**
Headless: `uv run pytest -q tests/test_library.py::test_an_eight_slot_show_loads_and_is_not_rewritten tests/test_library.py::test_the_first_write_past_slot_eight_keeps_the_eight_slot_file tests/test_ui_presets.py::test_twenty_four_slots_fit_the_page_with_more_open tests/test_ui_presets.py::test_a_far_slot_reads_its_number_and_name_and_has_the_slot_menu`.
Before the first launch: `ls -l $HYPERSPACE_HOME/projects/`. Launch
(keeping stderr, above), open your show (PRESETS → show ▾), press F1–F8,
quit. `ls -l` again. *Pass:* every show file has the same size and time
as before; your eight presets are on F1–F8; under them are sixteen
smaller buttons four a row, "9" to "24", each "—" where empty (on the
factory party show 9 reads TRACER); the page has no scrollbar, with
"more" open as well. Right-click 12 → **put preset here…** → one of
yours. *Pass:* the button reads "12" and the name; the footer says
"slot 12: <name>"; in `projects/` there is now
`<show>.hyp.json.bak-v2-bank8`, the file as it was (a factory show
opened as shipped has no file to keep: its first write makes your
copy). Put another preset on slot 20: no second backup. One thing to
know, not a fail: with "more" open, **a warning line on top of the
status line scrolls the page by 11 px** (measured; pressing an empty
far slot makes one — "slot 13: an empty slot"); say if that is a
nuisance (register row 72: the fallback is the far slots eight a row).
*Fail:* a show file changed by opening it → `Project._take` / `write`;
a scrollbar with no warning showing → `ui_presets.preset_bank`
(`FAR_COLS`, `FAR_GAP`); no backup → `Project.write`, `library._kept`.

**82. Rows 4 and 5 are presets, on both layers (plan 19 WP2; register row 73).**
Headless: `uv run pytest -q tests/test_desk.py::test_rows_four_and_five_load_slots_nine_to_twenty_four_on_both_layers tests/test_desk.py::test_the_bank_pads_are_invariant tests/test_midi.py::test_a_bank_pad_is_green_loaded_amber_filled_and_dark_empty tests/test_ui_desk.py::test_a_filled_pad_is_amber_and_an_empty_one_has_no_label`.
APC40 in. With a preset on slot 12 (81): look at the grid. *Pass:* row 1
has one green pad (the loaded preset) and **amber** on the other filled
slots; row 4's fourth pad is amber; empty slots are dark (the
velocities sent are 1 green, 5 amber, 0 dark). On the on-screen desk
(H for the big one) the same pads are amber at half strength with
their presets' names, and an empty bank pad shows only its glyph. Press
row 4's fourth pad: it turns green, the old one amber, the picture
changes, and slot 12's button on the PRESETS page is lit. Press an
empty far pad: nothing loads, the footer says "slot 16: an empty slot".
Latch SHIFT: the same pads, the same lights; press another filled far
pad: it loads, and SHIFT drops (a load drops to the preset layer). Turn
the cue knob: the shape changes, through all 25 — **the lit pad no
longer shows which shape is up** (the VIEW page's shape combo does).
Right-click a param → Learn desk, press a far pad: the pad loads its
preset and the learn stays armed (invariant). *Fail:* amber that cannot
be told from green, or no amber → `apc40.filled_of` (the velocity) —
say what you see; the fallback is green-or-dark, `filled_of` returning
`None`; a pad that changes the shape → an old row in `bindings.json`
(84); nothing under SHIFT → the rows have a layer.

**83. A preset you saved before loads without a fuss, and save-as goes past F8 (plan 19 WP1, WP2; register rows 72, 73).**
Headless: `uv run pytest -q tests/test_presets.py::test_an_old_preset_loads_without_its_shape_pads_and_its_file_is_untouched tests/test_presets.py::test_the_next_save_of_an_old_preset_writes_the_desk_without_the_pads tests/test_midi.py::test_save_as_blinks_the_new_pad_on_row_four tests/test_library.py::test_save_as_lands_on_slot_nine_once_the_f_keys_are_full`.
`ls -l $HYPERSPACE_HOME/presets/`. Load three presets saved on the night
from the list. *Pass:* no warning about dropped rows, no dirty dot, and
`ls -l` shows no preset file's time moved: the sixteen old shape pads
each file carries are dropped from the live desk quietly, and stay in
the file until you save that preset — then the old file goes to
`trash/presets/` (check 53) and the new one has no shape pads. (If you
had learned something onto a pad of rows 4–5, there **is** a warning
naming it — "dropped note:3:56 → …: that control is invariant, the
session's (plan 13 D6)": that mapping is gone from the live desk and
still in the file until you save.) The orchestrator loaded the
seventeen presets in `shared/dan-2026-10-04/` this way on a temp home:
none said anything. Now the save-as: open the factory **party** show,
right-click F8 → clear slot, change the look, and hold the clip-stop
row. *Pass:* at about 0.6 s the bar and F8's pad blink; "saved … → F8".
Change the look and hold again: the bar and **row 4's second pad**
blink for a second and a half and the footer says "saved … → slot 10"
(TRACER holds slot 9). On a show of yours from before this build the
first far save lands "→ slot 9" and that show gets its
`.bak-v2-bank8` (81). *Fail:* a warning on every load →
`routing.RETIRED_DESK_ROWS`; a preset file's time moving on a load →
`Presets.load_doc`; the blink on row 1 only → `apc40.blink_of`; "the
bank is full" after F8 → the show's bank is not 24 long (`Project._take`).

**84. The session's file was brought along, with a backup (plan 19 WP2; register rows 73, 74).**
Headless: `uv run pytest -q tests/test_routing.py::test_an_older_file_gets_the_bank_pads_with_a_backup tests/test_routing.py::test_a_second_launch_writes_nothing_and_says_nothing tests/test_routing.py::test_a_row_the_owner_put_on_a_bank_pad_is_left_alone tests/test_routing.py::test_a_remap_whose_backup_fails_writes_nothing`.
Read the first launch's stderr (81). *Pass:* one line "backup:
bindings.json kept as bindings.json.bak-v3 before the rewrite" (a
dated `.bak-v3-<stamp>` name if one was there already), then **sixteen
lines** "bindings: …/bindings.json: added note:0:56 → preset.select
(the APC40 map of plan 19)" through `note:7:56` and `note:0:57` through
`note:7:57`, then "bindings: updated …/bindings.json (16 rows
changed)". If this copy's file had never been opened by a build with
plan 15 (check 57), the same launch also prints check 57's lines, and
the count is the sum. The SYSTEM page shows the same as **one line**:
"bindings.json updated (16 rows changed), the old file kept as
bindings.json.bak-v3 — each change is on stderr". `grep -c
preset.select $HYPERSPACE_HOME/bindings.json` says 24. A row of yours
on a pad of rows 4–5 (a hand edit of the file) is still there, that pad
does what your row says, and no bank row was added for it (its slot is
reached from the PRESETS page). Launch again: stderr says nothing about
bindings, the SYSTEM page has no such line, and `bindings.json`'s time
does not move. *Fail:* no backup and a changed file → `Bindings.load`
(no backup, no rewrite); "NOT rewritten … no backup could be made" on
SYSTEM → the folder refused the copy: the file is as it was and the
next launch tries again; the sixteen lines on every launch →
`remap_factory` is not finding its own rows.

**85. The knobs that were dark (plan 19 WP3; register row 75).**
Headless: `uv run pytest -q tests/test_plan12_presets.py::test_no_factory_knob_is_dead tests/test_midi.py::test_a_knob_on_the_pattern_steps_through_every_pattern tests/test_presets.py::test_a_users_desk_is_untouched_by_the_recut`.
F1 (TUMBLE): turn D1–D4. *Pass:* D1 4D depth, D2 the camera's yaw, D3
its pitch, D4 the face pattern — one pattern a step, every ring
following; D5–D8 dark and dead. **If TUMBLE is white in the list (your
own, saved before this build), its knobs stay as you saved them — dark —
and that is right**: load a house mood from the list instead (dim, the
factory's), which has the same four. A house mood: the same four. TRIP,
WAKE, ACID: their eight, as before. `hands-fx` from the list: D1 FX
mix, D2–D6 the Acid shader (bend, twist, reach, breathe, speed), D7 4D
depth, D8 yaw. `hands-pinch`: D1 FX mix, D2–D3 the hue cycle's paint
and spread, then depth, yaw, pitch, pattern. `lfo-breathe`: D1 still
Breathe. D4 changes nothing you can see on a preset with faces off (the
pattern is drawn on the faces). Then say which knobs you reached for and
found dark or useless: K7 (Bitmap alpha) does nothing on a factory
preset, and the scene presets have no echo or effect knob (register
row 75, fork 7). *Fail:* a lit knob that moves nothing → that preset's
row in `preset.py`; one knob doing two things → `knob_desk`; D4 skipping
patterns → `MidiIO._apply`'s `set_norm` on an enum.

**86. Cull the list (plan 19 WP4; register row 76).**
Headless: `uv run pytest -q tests/test_library.py::test_hiding_a_factory_preset_takes_it_off_the_list_and_nothing_else tests/test_library.py::test_a_deleted_preset_says_which_slots_still_name_it tests/test_ui_presets.py::test_the_list_has_a_cross_on_every_preset_and_rename_on_yours tests/test_ui_presets.py::test_a_slot_whose_preset_is_gone_says_so`.
PRESETS → click the preset strip's name → the list (twelve rows, then
it scrolls). Every row has ×; yours (white) also have **rename**. × on
`legacy6`, on the `hands-*` you do not want, on a house mood. *Pass:*
each goes; the footer says "hidden legacy6 — show hidden in the list
brings it back" (or "… — F3 still loads it" for one on a slot); the foot
of the list reads "show hidden (n)"; `cat $HYPERSPACE_HOME/hidden.json`
lists their file stems. Click "show hidden": they are back, struck
through and dimmer, each with **unhide**. An F-key or a pad that named a
hidden preset still loads it. × on one of **your** presets that is on a
slot: *Pass:* it goes; the footer says, in the warning colour, "<name>
is in the trash — F6 still names it; restore it from the trash, or
clear the slot"; that slot's button is in the warning colour and its
hover says where to look; its pad stays amber, and pressing it says
"F6: no preset '<name>'". *Fail:* a hidden preset that will not load
from its slot → `Library.list(hidden=)` leaked into `path_of`; a
module strip's list (under "more") with × on a factory preset → it
should have none (`_list_row`).

**87. Give "TRIP 3" a real name (plan 19 WP4; register row 76).**
Headless: `uv run pytest -q tests/test_library.py::test_rename_updates_every_show_and_keeps_each_old_file tests/test_library.py::test_rename_refuses_a_taken_name_and_a_factory_preset tests/test_library.py::test_renaming_the_loaded_preset_keeps_its_unsaved_edit tests/test_presets.py::test_rename_and_trash_are_no_undo_step`.
Put a preset of yours on a slot in two different shows of yours. In the
list: **rename** → the row becomes a name field → type a name → Enter.
*Pass:* the footer says "renamed TRIP 3 → SUNRISE (2 shows updated)";
the list, the slot and "starts on" (if it was that one) show the new
name at once; open the other show: its slot has the new name too.
`ls $HYPERSPACE_HOME/trash/presets $HYPERSPACE_HOME/trash/projects`: the
old preset file and each show as it was. Rename it to a name another
preset has: refused ("library: …: that name is taken — pick another"),
nothing changes. A factory preset has no rename (save copy, then rename
the copy). Rename the loaded preset while it has an unsaved change: the
dot stays lit. ⌘Z does not undo a rename (no undo step): rename it back.
*Fail:* a slot that says "no preset" after a rename → step 5 of
`Library.rename` (`_repoint`).

**88. The trash (plan 19 WP4; register row 76).**
Headless: `uv run pytest -q tests/test_library.py::test_restore_never_overwrites tests/test_library.py::test_empty_trash_removes_only_the_trash tests/test_library.py::test_the_trash_lists_only_what_it_kept tests/test_ui_presets.py::test_empty_asks_once_and_disarms`.
The list → **trash (n) ▸**. *Pass:* a second popup, "trash · n files",
every file the trash holds — older versions saves replaced (check 53),
what 86 and 87 put there, the shows from 87 — newest first, each with
its folder, name and time ("Oct 4 01:12") and **restore**; past twelve
rows it scrolls. Restore the preset from 86: the footer says "restored
<name>", it is in the list, its slot loads again and the warning colour
is gone. Save over a preset twice, then restore the older copy: *Pass:*
"restored as TRIP 4 — TRIP 3 is taken" (the next free name), and the
newer one is untouched. Click **empty trash…** once and wait: *Pass:*
it reads "delete n files for good? — click again" in the warning colour,
then after 4 s goes back to rest, and nothing was deleted. Click it,
then click anything else: disarmed. Click, then click again: "trash: n
files deleted for good"; the "trash ▸" line is gone from the list;
`ls $HYPERSPACE_HOME/trash` is empty. **Empty trash is the one action in
the app that deletes with no copy kept** (register row 76). *Fail:* a
restore that replaced a preset → `restore_trash` (tell us at once:
`~/Hyperspace-before-19` has it); one click emptying → `_trash_popup`.

**89. The dot from a step back (plan 19 WP5; register row 77).**
Headless: `uv run pytest -q tests/test_ui_presets.py::test_the_dot_is_a_twelve_pixel_disc_and_save_is_lit_while_dirty tests/test_ui_presets.py::test_save_reads_save_copy_on_a_factory_preset tests/test_ui_presets.py::test_the_preset_strip_has_no_reset_and_does_not_overlap tests/test_ui_routing.py::test_the_head_has_the_same_dot_and_label`.
Load a factory preset you have no copy of (dim in the list) that is on a
slot, stand at arm's length, move a fader. *Pass:* you can see it is
unsaved without leaning in: the save chip is solid red, a red disc sits
by the name, the slot's button has a small white disc. The chip reads
**save copy** and the strip has no reset; press it: it reads "save",
the dot goes, the list shows the preset once, white (yours). ROUTING's
head shows the same disc and label. A preset of yours reads "save".
Under "more", a module strip's save chip overlaps the right end of its
name: known and not this plan's (audit U10). *Fail:* cannot be read from
there → `ui.DOT_R`, or say what would read.

**90. The home in git, if you want it (plan 19 WP6; register row 78).**
Headless: `uv run pytest -q tests/test_homegit.py tests/test_library.py::test_hide_rename_and_restore_each_ask_for_a_commit tests/test_config.py::test_library_git_is_off_by_default_and_a_switch`.
First `git -C $HYPERSPACE_HOME rev-parse --show-toplevel`: it should say
"not a git repository" (if it names a folder above the copy, your home
folder is itself a repository and git will refuse, by design — one note
on the warning line, nothing written). In `$HYPERSPACE_HOME/config.toml`
add `[library]` and under it `git = true`. Launch. *Pass:* SYSTEM's
library line reads "library: … · git"; `ls -a $HYPERSPACE_HOME` shows no
`.git` yet. Save a preset (as…). *Pass:* `git -C $HYPERSPACE_HOME log
--oneline` shows one commit, "Hyperspace: the home as it was when git
was switched on", whose body (`git -C $HYPERSPACE_HOME log -1
--format=%b`) names your save; `.gitignore` is there. Save it again
after a change, rename it, × it, × a factory preset, put a preset on a
slot: a commit each, in the library's words — "save preset …",
"rename preset … → …" (when the open show named it, its "show …: bank"
is in that commit's body, or is the very next commit if the worker had
already started), "trash preset …", "hide preset …", "show …: bank". `git -C $HYPERSPACE_HOME
status --short` is empty; `git -C $HYPERSPACE_HOME ls-files | grep -c -e
weights -e trash -e last_show -e windows.json -e .bak-` says 0; `git -C
$HYPERSPACE_HOME remote` prints nothing. Now `touch
$HYPERSPACE_HOME/.git/index.lock` and save: *Pass:* the save is instant,
the preset is on disk, the warning line says "git: not committed (git
add exited 128: …); saves are not affected"; save again: nothing more is
said. `rm $HYPERSPACE_HOME/.git/index.lock` and save once more: one
commit in that save's words, holding all three files (`git -C
$HYPERSPACE_HOME show --stat HEAD`); the words of the two saves made
while it failed are not in the log. Emptying the trash makes no commit
(the trash is ignored). *Fail:* a save that waits → `homegit.Committer.request`;
a `.git` before the first save → `app._open_homegit`. Leave the key off
on the real home unless you want it: it is one home's local history,
not a way to share presets — that is `shared/` and
`tools/shared_presets.py`.

## P. Plan 20 — the faces as an effect target, the chain view, the look-back page, layouts — added 2026-10-04

Run on `finish-line` once plan 20 is merged into it (PRs #101 the face
target, #106 the FX page, #108 drag to reorder, #105 the look-back page,
#107 dream speed, #111 instance layouts). Laptop first (91–97), then the
projector (98). About 30 minutes. First, headless:
`uv run pytest -q tests/test_fx.py tests/test_render.py tests/test_lookback.py tests/test_ui_shell.py`.
No config change. None of this has been tried by a person: it was shown
by tests (offscreen frames, and the panel driven by imgui events a test
feeds it), offscreen and hidden-window renders, and scripted launches on
a laptop (`20-fx-dream-looks.md` §7). **Nobody has seen a face effect on
a projector or the glass, dragged a chip with a real mouse, or judged
the dream at any speed.** Decision register rows 65–71 are the calls
these checks let you confirm or overturn.

**91. An effect aimed at the faces (plan 20 WP1, WP2; register rows 65, 66, 68).**
Headless: `uv run pytest -q tests/test_render.py::test_a_face_effect_changes_the_faces_and_nothing_else tests/test_render.py::test_per_face_turns_with_the_shape_and_screen_stays_still tests/test_render.py::test_screen_mapping_is_a_cover_fit_window_onto_the_picture tests/test_fx.py::test_the_status_reads_per_target tests/test_fx.py::test_the_strips_target_combo_moves_an_effect_between_chains tests/test_fx.py::test_a_chip_aimed_at_the_faces_is_marked tests/test_fx.py::test_why_idle_names_faces_off`.
F2 (FACES). On the BITMAP page load any picture. FX page: the status
under "Effects" is one line, as before. Open Kaleidoscope, switch it on
(its dot), and on the strip's blend row set the combo between blend and
order from `frame` to `faces`. *Pass:* the wireframe is no longer
folded and the picture inside every face is; the status is now two
rows, `frame  …` and `faces  Kaleidoscope`, the second ending in two
chips, **per face** (lit) and **screen**; Kaleidoscope's chip has a
filled **diamond** where the dot was (switch it off: an outlined
diamond), and its hover says "on the faces". Click **screen**: the faces
become windows onto one folded picture that stays put, upright, while
the shape turns across it. Back to **per face**: it turns with the shape
again. Unload the bitmap, pattern FLAT, aim Plasma at the faces too: the
faces glow with the plasma and the space between them stays black. Turn
Faces off on the VIEW page: the faces' row reads `faces  (Faces is off)`
in the warning colour, and Kaleidoscope's open strip reads "aimed at the
faces, and Faces is off" with a **faces on** chip that puts them back.
Take Instances to 0: the row reads `faces  (no copies to show them)`.
⌘Z after the combo and after a map chip: each is one step. Judge from a
step back whether the diamond reads apart from the dot. **Per face, an
effect may read faint**: the faces are drawn at a few percent alpha and
overlap, so in the build's own renders a strong re-colour (Hue cycle,
Kaleidoscope) showed and a subtle one (Double vision, Deconverge, Trip
colour, Wobble) was hard to tell from none — judge it here and again on
the glass (98). *Fail:* nothing changing in the faces → the faces' row
(a `faces: …` error there is `Renderer.face_error`) and
`Renderer._face_picture`; the whole frame still folding → the effect is
still in `chain(FRAME)` (`FxState.chain`, `fx._target`); the picture
upside down or mirrored against the bitmap → `FACE_PX`'s `1.0 − q.y` and
the screen branch of `FACE_FS_TAIL`; the strip's combo or the map chips
doing nothing → `ui_fx.page` / `_faces_row`. Every face showing the same
pattern where it used to vary is expected (register row 65: the picture
is face 0's); say whether it matters.

**92. With nothing aimed at the faces, nothing changed (plan 20 WP1; register row 65).**
Headless: `uv run pytest -q tests/test_render.py::test_nothing_aimed_at_the_faces_is_the_old_frame_exactly tests/test_render.py::test_the_face_target_costs_nothing_while_unused tests/test_render.py::test_the_old_frame_holds_under_frame_effects_the_hands_and_the_dim`.
F1 through F8 in turn, as you know them. *Pass:* every preset looks as
it did before this build, the FX page's status is one line with no
`frame` prefix, and the frame rate in the control window's footer is
what it was. Then F5 (TRIP): aim its four effects (Plasma,
Kaleidoscope, Zoom burst, Hue cycle) at the faces: the frame rate does
not drop by anything you can read (on the build laptop, four effects on
the faces cost about 0.1–0.15 ms offscreen). F5 again puts them back on
the frame (a preset load lands every target; a preset saved before plan
20 loads as all `frame`, per face). *Fail:* any preset looking different
with every effect on `frame` → the face fragment's `u_pic_on == 0`
branch; a drop in frame rate with effects on the faces →
`render.FACE_PIC` (register row 65), and say which machine.

**93. The echoes and the dream carry the faces' effects (plan 20 WP1; register row 65).**
Headless: `uv run pytest -q tests/test_render.py::test_the_echoes_carry_the_faces_effects tests/test_render.py::test_a_frame_effect_runs_over_a_face_effect`.
F4 (WAKE), with the dream worker running. Aim Hue cycle at the faces
and switch it on. *Pass:* the trail behind the shape has the cycling
colours of the faces it came from, and the dream grows out of them; an
effect left on `frame` still does not appear in the trail (it never
did). *Fail:* a trail in the old colours → the face pass running after
the capture (`Renderer._draw_frame`'s order: the face picture is step 1,
before the scene pass).

**94. Drag an effect to reorder (plan 20 WP3; register rows 67, 68).**
Headless: `uv run pytest -q tests/test_fx.py::test_a_drop_reorders_selects_and_is_one_undo_step tests/test_fx.py::test_reordered_always_sorts_to_the_sequence_asked_for tests/test_fx.py::test_a_click_without_a_drag_still_only_opens tests/test_fx.py::test_a_drop_moves_the_effect_the_drag_began_on tests/test_fx.py::test_the_order_slider_still_reorders`.
F5 (TRIP), FX page. **Drag the Hue cycle chip by its name** (not its
dot) and drop it on the Plasma chip. *Pass:* while you drag, the chip's
name floats with the mouse and a white bar shows on the left edge of the
chip you are over; on the drop Hue cycle is the first chip, the status
line now starts with it, the picture changes (the colour is applied
before the fold), and the strip opens on **Hue cycle**. ⌘Z: the order is
back in one press and the footer says "undid reorder effects". Drag a
chip onto the **right half of the last chip's name**: the bar moves to
that chip's right edge, and the drop puts the dragged effect at the
end. A plain click on a name still only opens it; a press that slips a
little and is let go on the same name opens it too; the dot still only
switches. The order slider in the strip still works. Do it on the
trackpad and with a mouse. A drag never changes a target or a switch.
Three things the build left, to notice: a 2 px gap between a chip's dot
and its name takes no drop (hover again); the floating name can be cut
at the window's right edge; past a hundred effects a drop can be
refused. *Fail:* a click starting a drag, or a drag that cannot be
started → use the order slider in the strip and say so (register row
67); the order wrong after a drop → `fx.reordered`; a different effect
moved than the one you picked up → `ui_fx._dragged` /
`panel._fx_drag`; two presses of ⌘Z needed → the push in `ui_fx._drop`.

**95. The look-back page reads (plan 20 WP4; register row 69).**
Headless: `uv run pytest -q tests/test_ui_shell.py::test_the_look_back_page_fits_with_thumbnails tests/test_lookback.py::test_the_page_has_three_sections_and_every_dream_param_once tests/test_lookback.py::test_the_layer_is_a_row_of_chips tests/test_lookback.py::test_spacing_is_called_time_apart tests/test_lookback.py::test_the_routing_page_lists_the_new_labels`.
F4 (WAKE), LOOKBACK page, with the dream worker running. *Pass:* under
the page's own switch, three sections: **ECHOES** (brightness, fade
time, count, time apart, then the thumbnails; on WAKE its note reads
"24 × 50 MS · THE TRAIL REACHES 1.20 S"), **DREAM** (the worker's status, at
most three lines, the rest on its hover; a row of six layer chips;
brightness, speed, strength, passes, linger, jitter, scales, hue,
saturation, tint, tint from, tint hue, tint sat, and **the tint**, the
swatch, in its own cell) and **BOTH** (darken, contrast, shape hides,
detail). The page does **not** scroll with the thumbnails showing (it
did, by a few pixels, before this build). Every label says what the knob
does without the hover: read them out and name any that does not. "time
apart" is the old "Spacing" and reads `50 ms` on WAKE; "fade time"
reads `0.60 s`; "shape hides" is the old "Occlude"; "detail" is the old
resolution combo. On the ROUTING page a route's target says the
registry's longer names ("Echo time apart", "Dream brightness", "Shape
hides wake"). **The six layer chips — grain, swirl, blot, 3b, 4c, 4e —
were named from the param's tooltip, not from looking**: click each in
turn, wait for the worker to load it (its status line says so), and say
whether grain, swirl and blot are the right names for the first three
and what 3b, 4c and 4e should be called (about five letters fit).
Right-click a chip: "not modulatable", as before. *Fail:* the page
scrolling → `ui_lookback.SECTIONS` / `STATUS_LINES`; a chip not loading
its layer → the click's `Param.set`; a name wrong →
`ui_lookback.LAYER_CHIPS`, one line each; a label cut → `LABEL_W`.

**96. Dream speed (plan 20 WP5; register row 70).**
Headless: `uv run pytest -q tests/test_lookback.py::test_dream_speed_is_dream_k tests/test_lookback.py::test_the_speed_readout_is_the_half_life_in_frames`.
F4 (WAKE), DREAM section, **speed** (beside brightness). Move a hand
through the box and drag speed end to end. *Pass:* right is faster: at
the fast end the dream keeps up with the shape and lets go of where it
was almost at once, and is shallower; at the slow end it trails well
behind and grows deeper. The readout is in dream frames: "≈23 frames" at
the slow end, "≈14 frames" at the default, and under ten frames one
decimal ("6.6 frames", "1.9 frames" at the fast end); slower than about
17 frames the worker's status says "step clamped". Say whether this is
the "speed" you meant, whether one knob is enough (faster is also
shallower, by design), and whether the dream feels the same speed here
as on the laptop screen at the same number — it counts the worker's
frames, not seconds. *Fail:* the wrong quantity → register row 70, say
which you meant; a different feel on the rig than on the laptop at the
same number → row 70's per-second follow-up.

**97. Instance layouts (plan 20 WP6; register row 71).**
Headless: `uv run pytest -q tests/test_render.py::test_grid_layout_is_the_frame_it_was tests/test_render.py::test_hex_neighbours_are_one_cell_apart tests/test_render.py::test_ring_is_one_circle_with_neighbours_one_cell_apart tests/test_render.py::test_zero_and_one_are_the_same_in_every_layout tests/test_ui_shell.py::test_the_view_page_fits_with_a_field_in_motion tests/test_ui_shell.py::test_the_field_row_and_the_rate_cells_keep_their_menus`.
F3 (FIELD), VIEW page. *Pass:* the field looks as it did, and the page
does not scroll (it did, with more than one copy, before this build).
Under Instances one row: **layout**, **motion**, and while the motion is
not STILL its **amp** and **rate**; the six rotation rates are three
rows of two, each labelled with its plane alone ("XY"). On the house
show's first preset (a lane on each rate) a rate cell reads `base →
effective` whole. Set **layout** to HEX with 7 copies: one in the middle
and six round it; 19: two rings; raise the count slowly: the copies
already there do not move. RING with 12: one circle; ORBIT sends a wave
round it, RIPPLE makes it breathe as one. Take the count to 1 and to 0
in each layout: one copy at the centre, then nothing. ⌘Z after a layout
change puts it back. **HEX with ORBIT, amp up to about 0.35: neighbours
overlap** (ORBIT's phase does not step evenly on a honeycomb, so
neighbours orbit out of step; the motion maths is unchanged from the
grid's) — judge whether that is a look or a fault. Right-click the
layout combo and a rate cell: each opens its own menu. ROUTING and a
Learn say "Field motion", "Field amp", "Field rate" where they said
"Grid …". *Fail:* the grid different from before → `inst_positions`'
GRID branch; copies jumping as the count rises in HEX → `_hex_spiral`;
the page scrolling → `Panel._page_view`; HEX + ORBIT unusable → register
row 71 (the motion block of `draw_scene`, not the layout).

**98. On the projector and the glass (plan 20 WP1; register row 65).**
Headless: `uv run pytest -q tests/test_render.py::test_screen_mapping_is_a_cover_fit_window_onto_the_picture tests/test_render.py::test_the_face_target_keeps_an_opaque_grounds_alpha`.
With the render on the projector, then on the Pepper's Ghost glass,
check 91's looks again (Kaleidoscope on the faces with a bitmap, per
face and screen; Plasma on the faces over FLAT). *Pass:* in screen
mapping the picture behind the faces is sharp enough at the size the
room sees it, and not stretched (it is cropped top and bottom on a wide
output); per face, a face close to the camera does not show blocks; the
glass shows no desktop or grey through the faces. From where the
audience stands, **say whether the faces' effects read at all at the
faces' brightness**, per face especially, or need the pattern mix or
the brightness up. *Fail:* soft or blocky → `render.FACE_PIC` (register
row 65); the picture squashed → the cover fit in `FACE_FS_TAIL`
(register row 65); see-through faces on the glass → the face fragment's
alpha (`test_the_face_target_keeps_an_opaque_grounds_alpha`); too faint
to read is a look to tune in a preset, not a fault: say which preset.

## What this list does not ground

Two checks have no headless twin because they are the eye's: the dream
grade (9) and the default feel (16). Check 25's number is a target, not
a measurement anyone has made. Everything else names a test or a tool.
