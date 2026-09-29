# Plan 11 — Hand checks at the machine

Everything only the owner can verify, in the order that costs the least
time at the machine: laptop alone first, then the APC40, then the camera
and the box (APC40 still plugged in for check 24), then the projector,
then IAC + FL Studio, then one back on the laptop, then plans 12 and 13's two, then plan 13's group H (plan 13 is built on `plan-13-integration`). Each check: the commands, the config, the preset,
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
Then `uv run hyperspace` once more: R resets the camera, F1 loads preset 1 (BIG BLUE WAVE),
⇧F1 saves the live state as it (a user file shadowing the factory one), ⌘R restarts without resetting the camera first, and the
cheat sheet (`/`) names all seventeen rows — R, F1–F8, ⇧F1–F8 (WP7; the
rows are the session's, in `bindings.json`; headless:
`tests/test_routing.py::test_r_and_the_f_keys_are_table_rows_that_fire_their_params`).
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
changes with the clap on the default project's startup preset (BIG
BLUE WAVE: a lane pushes each rotation rate). Plug in or enable a
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
check). A fader moved behind your back still waits for a pickup. *Fail:*
no LEDs → `apc40.mode_on` / the port name (`[midi] port`); a knob that
moves the wrong param → `apc40.DEFAULT_MAP` (and its `layer`); a knob
jumping back to its old place after a switch → check 31;
a fader jumping instead of catching → `MidiIO._apply` pickup (midi.py).

**11. Rings show the base, LEDs show the state (R6, decided (a)).**
Headless: `uv run pytest -q tests/test_midi.py::test_ring_shows_the_base_and_never_chases_a_performer tests/test_midi.py::test_select_buttons_and_led_state`.
F1 on the default project (BIG BLUE WAVE: a lane pushes each rotation
rate). Play a track.
*Pass:* the track-knob rings for view faders sit at the *setting* and do
not flicker with the audio; the scene-launch LEDs for points / lines /
faces / rotate reflect the toggles; pressing one flips the LED at once.
Under a lane-owned toggle (route `lane:0 → view.faces` push on the
ROUTING page), the FACES LED follows the audio, the panel's checkbox
shows the base — that is today's rule (R6 recommendation: keep). *Fail:*
a ring chasing the audio → `MidiIO.feedback` reading the effective value.

**12. TAP TEMPO, NUDGE ±, METRONOME, QUANT (plan 09 check 5 on the desk).**
As check 7 but on the desk: TAP TEMPO ×4 on the beat, METRONOME on the
one. *Pass:* as check 7; the METRONOME LED blinks on the beat; NUDGE +
and − move `tempo.nudge` by 0.01 and the swell with it; QUANT cycles the
preset bank (`preset.next`), the clip grid's top row picks a preset, row 2–3 a
scene (with SHIFT latched — the band scenes are the global layer's, group
H), row 4–5 a shape, STOP ALL resets the scene with the 8 s undo.
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
(no fade to minimum — that was B1). *Fail:* brightness going to 0.13× when
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

**26. `[output] monitor`, fullscreen, "follow window" (P3, plan 07 WP1).**
Headless: `uv run pytest -q tests/test_overlay.py::test_follow_window_is_the_first_choice_and_reads_back_as_itself`.
Plug the projector in. OUTPUT page: `output.monitor` combo lists "follow
window" first, then each screen by name; pick the projector,
`output.fullscreen` on. *Pass:* the render window covers the projector at
its own DPI (edges the same weight as on the laptop), the control window
stays on the laptop; `T` overlay on the projector, `G` passthrough; back
to "follow window" and fullscreen off returns a window. Set
`[output] monitor = 1, fullscreen = true`, relaunch: straight to the
projector. *Fail:* the wrong screen → `overlay.Output.apply` (the GLFW
monitor list order); blurry edges → `dpr` in `app.frame`'s draw.

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
`projects/default.hyp.json` starting on it; run it again: no new backup,
nothing rewritten. Your real home's hand-made `.bak-plan09` and
`.bak-2026-09-26` are never touched. *Fail:* no `.bak-v1` → `routing.backup`
(`preset.migrate_home`, PR #66); an existing `.bak-*` overwritten → the dated
copy path in `backup`.

## G. Plans 12 and 13 — added 2026-09-28, after the rest

**31. The APC40's knobs re-base from the host (plan 13 D7; the one hardware assumption the two-layer desk rests on).**
No headless twin: it is the device's behaviour. Desk plugged in, the app
on the default project (F1, BIG BLUE WAVE, brightness 1.25×). Turn track knob 1 (brightness) to about a
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
each tile expects. Projector and box on; PRESETS page → project → load ▾
→ `party`; then per preset its F-key alone — F1 TUMBLE … F5 TRIP (plan 13 WP2)
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
project) in its first empty slot — so the first launch opens on the
same picture as the last one; `bindings.json` keeps your keys, pad and MIDI rows and
nothing else — no route, no preset-layer knob, no `macros`, no `values`
— the band strip's eight device knobs now `"layer": "global"`; your
learned hand rows and knobs are in the startup preset (ROUTING page:
the routes, the DESK section); `~/Hyperspace/bindings/` is as it was,
with a `NOT-READ.txt` in it; every `.bak-*` you made by hand is
untouched (`ls -la ~/Hyperspace` against the copy). A home with no
project of its own gets a `MIGRATED` preset holding bindings.json's
routes, desk and macros, the startup of a new `default` project. Launch
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
the button: one shape change, nothing else. *Fail:* the LED dark while
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
desk rows as "device knob 1 … unmapped — dark" (through "device knob 8");
with SHIFT latched they light and move the band strip, and the ROUTING
head reads LAYER GLOBAL. *Fail:* a lit ring on an unmapped knob → the dark
rule in `MidiIO.redraw`; a device knob moving the band strip without SHIFT
→ a fall-through to the global layer, which D8 forbids (`MidiIO._handle`);
a knob that does nothing but is not listed → `ui_routing.unmapped`.

**37. Learn refuses the global layer and the invariant controls (plan 13 D5, D6; WP4).**
Headless: `uv run pytest -q tests/test_learn.py::test_learn_refuses_the_global_layer_and_invariant_controls tests/test_learn.py::test_a_knob_learn_writes_a_desk_row_into_the_loaded_preset tests/test_learn.py::test_a_hand_learn_writes_a_route_into_the_loaded_preset`.
Note `bindings.json`'s time (`ls -l ~/Hyperspace/bindings.json`). Open
the ROUTING page. Right-click Brightness → Learn, move track fader 1.
*Pass:* refused — the ROUTING head (and the SYSTEM page's learn line)
reads, in the warning colour, "learn: track fader 1 is invariant (the
session's) — not learned"; nothing changes, the fader still drives SUB's
drive. Latch SHIFT, Learn again, turn track knob 6: "learn: track knob 6
is on the global layer (the session's) — latch SHIFT off to learn into
the preset". Unlatch SHIFT, Learn again, turn device knob 3: "learn:
learned view.bright ← device knob 3 (into the preset)" — the knob now
moves brightness, the DESK section shows "device knob 3 → view.bright
abs" and track knob 1 (brightness's old knob) as "unmapped — dark", the
head's dot (and the PRESETS strip's) is lit, and `bindings.json`'s time
has not moved. Load the preset again (F1) to throw the learn away: the
dot goes out, track knob 1 is brightness again. *Fail:* a learn on a
fader or under SHIFT → the refusals in `MidiIO._learned`; `bindings.json`
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

**40. The startup preset (plan 13 D11; WP2).**
Headless: `uv run pytest -q tests/test_presets.py::test_the_startup_preset_loads_on_launch`.
PRESETS page, project `party`, startup ▾ → TUMBLE; save the project. Quit
(Esc) and relaunch. *Pass:* the show comes up as TUMBLE, its desk lit (the
track-knob rings at TUMBLE's values), the status line says so. Put your
own project's startup back afterwards. *Fail:* a dark desk or the factory
look → `Project.startup` and the startup load in `app.main`.

**41. The five party presets, re-cut (plan 12 §7, plan 13 WP5).**
Headless: `uv run pytest -q tests/test_plan12_presets.py` (the F-keys,
`test_the_five_party_presets_load_by_f_key_as_presets`; the knobs,
`test_wake_and_trip_device_knobs_move_their_bases`) and
`uv run python tools/preset_shots.py`. Projector and box on. As check 32,
but each preset is one F-key — F1 TUMBLE, F2 FACES, F3 FIELD, F4 WAKE,
F5 TRIP on the `party` project — one step, nothing else to load. *Pass:* check 32's (a)–(f) hold as
before; WAKE's device knobs 1–8 set echo mix · decay · darken · contrast ·
occlude · dream mix · dream sat · dream k, and TRIP's set fx mix · plasma
level · kaleido segments · kaleido zoom · burst amount · burst glow · hue
paint · hue spread (plan 12 §6) — device knobs 1–8 are `cc:*:16`–`23`, absolute —
each ring showing its value; on TUMBLE, FACES and FIELD the device
knobs are dark (SHIFT brings the band strip). TUMBLE's left height
still pushes the drive (row 19 (a)), its ROUTING row marked "session".
*Fail:* a look → the values in `library/presets/party-*.json` (data)
or a route in `preset.party_*_routes` (generated: change the generator,
`python -m hyperspace.preset`, not the file); a knob on the wrong base
→ `preset.WAKE_KNOBS` / `TRIP_KNOBS`; anything check 32 lists → the same
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
44 and 46 run on the laptop alone. About 15 minutes. The headless tests
named are the ones WP1 adds; run them first. (45 is kept for plan 14
WP7's desk diagram.)

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
running, and the SYSTEM page shows `stall log: …/stall.log (1 on
demand)`. If the render ever freezes, or the red banner at the bottom of
the control window names a render error or a render stall, keep
`stall.log`: each entry's header names the kind (`stall`, `render
error`, `render stall`, `stranded target`, `non-finite`, `warning`), the
time and the loaded preset, then every thread's stack. *Fail:* no file or
an empty one → `watchdog.Watchdog.start` (its `error` is on the SYSTEM
page); the app quitting on the signal → the `faulthandler.register` call
did not run (the default action of SIGUSR1 is to terminate).

**46. WAKE without the dream worker still draws (plan 14 WP1, the freeze).**
Headless: `uv run pytest -q tests/test_render.py::test_a_look_back_frame_with_no_worker_leaves_the_window_bound tests/test_lookback.py::test_capture_off_the_cadence_with_no_source_puts_the_target_back`.
In `config.toml` set `[dream] enabled = false` and relaunch. Open the
`party` project and press F4 (WAKE): `dream.on`, an echo every 2 frames,
and no worker. *Pass:* the render window keeps moving — the shape turns,
the echoes trail it — for a minute and through F1–F5 and back to F4; the
red banner says "WAKE turns the dream on, but there is no dream worker
(…)" until **dismiss**; `stall.log` has that `warning` and no `stranded
target`. Put `[dream]` back afterwards. *Fail:* the render window
freezing on one picture while the panel goes on → a framebuffer left
bound (`Renderer.draw`'s `finally`, `Lookback.capture`'s, and the
`ctx.screen.use()` at the top of `app.draw_render`) — `stall.log` then
has a `stranded target` entry naming it.

## What this list does not ground

Two checks have no headless twin because they are the eye's: the dream
grade (9) and the default feel (16). Check 25's number is a target, not
a measurement anyone has made. Everything else names a test or a tool.
