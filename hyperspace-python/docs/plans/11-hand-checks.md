# Plan 11 — Hand checks at the machine

Everything only the owner can verify, in the order that costs the least
time at the machine: laptop alone first, then the APC40, then the camera
and the box (APC40 still plugged in for check 24), then the projector,
then IAC + FL Studio. Each check: the commands, the config, the preset,
what to do, what a pass and a fail look like, and which audit item or
code path a fail points at. Where a check can be simulated headless, the
pytest node or `tools/` command that shows the expected behaviour is
listed first — run it before touching hardware so you know what "right"
looks like. Written against `plan-11-integration` (772 tests).

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
changes with the clap on the `default` routing. Plug in or enable a
device and press **rescan** beside the combo: it appears, the selection
by name survives. *Fail:* no prompt and flat meters → `AudioEngine.start_mic`
/ the callback (`audio.py`); meters at the ceiling with the blinking
annunciator on a quiet room → the analyzer's warm-up (ENGINEERING §4);
rescan loses the selection → `AudioEngine.rescan` (PR #51).

**4. The restyle by eye (PR #24) and every page fits (U1).**
Headless: `uv run pytest -q tests/test_ui_shell.py::test_every_page_fits_the_control_window`
and `uv run python tools/control_shots.py --hands --bands` (writes one
PNG per page under `docs/plans/assets/`; look at them). In the app, walk
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

**6. Cut-through by eye (PR #26).**
Press `T` (overlay mode over the desktop), `F` for faces, FACES page:
pick a pattern. VIEW page: toggle `view.cut_through`. *Pass:* on, face
fills let the desktop show through where they overlap; off, the lowest
face layer hides it and only the window's ground (`overlay.bg`, the
crossfader) is see-through. `T` again returns the window. *Fail:* no
visible difference in overlay mode → the blend in `render.py` (§2.1);
the desktop showing through with cut-through off → the separate-alpha
path.

**7. The LFO page, B and ⇧B (plan 09 check 5, keys only).**
Headless: `uv run pytest -q tests/test_tempo.py::test_three_taps_at_140_read_140 tests/test_lfo.py::test_a_tap_does_not_move_a_running_synced_lfo_but_the_trigger_does tests/test_lfo.py::test_a_trigger_after_this_frames_step_lands_phase_zero_on_the_next_step`.
ROUTING page: load `lfo-breathe`. LFO page. Play a track (`K`, a file
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
eight device knobs move the open band strip; the track knobs move the
view faders; a channel fader moves that band's post drive; after
switching band with the track-select buttons a device knob does nothing
until it sweeps through the current value (pickup), then catches. *Fail:*
no LEDs → `apc40.mode_on` / the port name (`[midi] port`); a knob that
moves the wrong param → `apc40.DEFAULT_MAP`; a knob jumping instead of
catching → `MidiIO._apply` pickup (midi.py).

**11. Rings show the base, LEDs show the state (R6, pending decision).**
Headless: `uv run pytest -q tests/test_midi.py::test_ring_shows_the_base_and_never_chases_a_performer tests/test_midi.py::test_select_buttons_and_led_state`.
ROUTING page: `default` (a lane pushes each rotation rate). Play a track.
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
theme (`theme.next`), the clip grid's top row picks a theme, row 2–3 a
scene, row 4–5 a shape, STOP ALL resets the scene with the 8 s undo.
*Fail:* METRONOME LED steady → `lfo.trigger`'s `lit` (tempo.py
`on_beat`); a button doing what it did before plan 09 → your
`bindings.json` kept an old row (`remap_factory` only moves rows where
nothing uses the source): check the ROUTING page and delete the stale
row.

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
ROUTING: load `hands-play`. Raise and lower the right hand; watch
brightness. Tune on the HANDS page: Steadiness 1 Hz, Response 4, Catch
150 ms, return 500 ms, bounce 0.15, dead zone 0.04 on the centred axes
are the defaults. *Pass:* a still hand does not shimmer, a fast one does
not lag, a hand re-entering glides on rather than jumping. Save the
result from the HANDS strip as `factory` (user file, `~/Hyperspace/hands/`)
and say so in the plan's As built so it can be copied into the repo.
*Fail:* shimmer at rest → `smooth` too high; lag → `response` too low.

**17. Yaw and pitch held independently of x and y (plan 08).**
ROUTING: `hands-fx`. Hold the right hand still and tilt (pitch), then
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
ROUTING: `hands-play` (R height positions `view.bright`). VIEW page:
right-click the brightness fader → **Learn**; move the *left* hand up
and down. *Pass:* the prompt "Brightness is already performed by R
height positions — Replace / Keep" appears on whatever page you are on;
*Keep* leaves the table (ROUTING page unchanged); repeat and *Replace*:
the row now reads L height and `~/Hyperspace/bindings.json` changed.
While the prompt is up, moving hands learns nothing more. Optional: set
`[midi] enabled = false`, relaunch, repeat — Learn still works (B3, PR
#50); put it back. *Fail:* the learn lands with no prompt → `Learn.learn_source`
(learn.py) / `Bindings.add`; the wrong axis learned → `_learn` picks the
axis that moved furthest among *live* axes (WP1).

**20. Plan 09 check 4 — `hands-pinch` zoom under pinch + scroll.**
Headless: `uv run pytest -q tests/test_routing.py::test_audit_1_a_relative_writer_on_the_base_holds_under_modulation`.
ROUTING: `hands-pinch`. Pinch L middle, move the left hand: zoom follows.
Keep pinching and scroll the mouse wheel in the render window a few
notches. *Pass:* zoom does not run away while scrolling under the hand;
open the pinch: zoom lands on the scroll-set value (the base), not where
the hand left it. *Fail:* drift while scrolling → `Mouse.poll` reading
the effective value (`Param.scale` must read the base); a jump to the
hand's last value on release → the gate / `Registry.apply` return.

**21. Plan 09 check 6 — the right hand deepens `lfo-breathe`'s swell.**
ROUTING: `lfo-breathe`; LFO page in view. Raise the right hand. *Pass:*
LFO 1's depth fader's ghost bar rises with the hand, the brightness swell
deepens one frame later, nothing else moves (speed, zoom, fx untouched);
lower the hand: depth returns to its base (0.6 from the preset's values)
— note R1 pending: the preset also sets `lfo.1.sync` to 1 bar, which
dirties the LFO group's dot on purpose (recommendation: keep). *Fail:*
something else moving → a stale row in your `bindings.json`; depth not
returning when the hand leaves → B1 (`Follower.live`, PR #40).

**22. Plan 09 check 7 — a knob on a hand-owned param (B1 fixed).**
Headless: `uv run pytest -q tests/test_routing.py::test_audit_3_a_knob_moves_the_return_value_under_a_hand tests/test_hands.py::test_a_hand_leaving_the_box_releases_its_position_row`.
ROUTING: `hands-play`. Right hand in the box: it owns brightness. Turn
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
`hands-pinch`: pinch R index low (brightness dark), open, raise the hand,
pinch again. *Pass:* brightness takes the hand's new height at once —
hands grab, they never yield (decision 4) — and the base returns on open.
This is a feel check, not a design question; note whether the jump wants
the catch glide (150 ms) applied on gate open too.

**24. A hand leaving the box, and `hold` (B1, N6).**
Headless: `uv run pytest -q tests/test_hands.py::test_hold_shapes_the_daw_output_but_never_latches_a_row tests/test_hands.py::test_a_returning_hand_glides_its_row_back_on_through_the_catch`.
`hands-play`, HANDS page open. Take the right hand out. *Pass:* its axis
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

## F. After WP8 merges

**30. R12: `.bak` before a migration rewrite** — placeholder; WP8 writes
`bindings.json.bak-<schema>` once before the first rewrite and never
overwrites an existing `.bak-*` (your hand-made `.bak-plan09` and
`.bak-2026-09-26` stay). The check: put a schema-1 file in a scratch home,
launch with `HYPERSPACE_HOME=/tmp/h uv run hyperspace`, see the `.bak`.

## What this list does not ground

Two checks have no headless twin because they are the eye's: the dream
grade (9) and the default feel (16). Check 25's number is a target, not
a measurement anyone has made. Everything else names a test or a tool.
