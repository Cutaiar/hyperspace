# Plan 12 — Five party presets: two hands over the box, one per attraction

**After plans 08–10.** Hyperspace is performed at a party, by people who
have never seen it, with two hands in an enclosed box over an Ultraleap
camera. This plan composes five routing presets — one per main render
attraction — with the scene each expects, the desk controls that matter,
the evidence that they move the way their tables say, and a one-page card
per preset for the person at the box.

Files: `routing.py` (`PRESETS` gains `party-tumble`, `party-faces`,
`party-field`, `party-wake`, `party-trip`; `write_factory` exports them to
`library/bindings/`), `shaders/fx/zoomblur.glsl` (a new effect),
`library/fx/trip.json`, `library/dream/wake.json`,
`library/projects/party.hyp.json` (the five scenes on F1–F5),
`tools/preset_shots.py` (the evidence renderer), `tests/test_plan12_presets.py`
(the headless sweeps), `docs/plans/assets/12-presets/` (shots, sweep tables,
cards). One line changed in `tests/test_routing.py` (the set of preset names).

## 1. The five attractions, and why not the sixth

| # | preset | attraction | why it makes the cut |
|---|---|---|---|
| 1 | `party-tumble` | the polytope under six-plane rotation and 4D depth | The piece's identity. A rigid turn under a tilt of the hand reads in one second, and 4D depth under reach is the one control nothing else on the desk can put under a hand as well. |
| 2 | `party-faces` | faces with the procedural patterns | Colour and surface. It is the only attraction that reads at a party as *material* rather than *line*; on a projector it needs brightness the hands can add. |
| 3 | `party-field` | the instance field | The one big spatial gesture: raise a hand and the room fills with copies. The cheapest "wow" in the stack, and the one where one axis fanning out to three params is obviously right. |
| 4 | `party-wake` | the look-back wake with the dream worker | Motion made visible: the hand that turns the object paints its trail. The dream buffer adds the one thing nothing else has, a texture that is not the shape. |
| 5 | `party-trip` | the FX stack | The most legible per unit of movement of anything in the stack — a burst, a fold, a swirl — and the one place a beat-synced LFO chain earns its keep. |
| — | (folded in) | the audio-driven planes | Not a hands attraction. The six `lane:` → `rot.rate.*` rows are the rhythm floor under *every* preset above, and `tumble` puts their drive under a hand (left height pushes `master.gain` 1× → 8×). A preset that was only "the music drives the planes" would give the hands nothing the tumble does not already do better. |

## 2. The expressive-space survey

Three readers went through the render stack, the look-back and LFOs, and
the effect files before anything was composed. What changed the design:

**Rotation and camera.** `rot.rate.*` spans ±66.56× (`params.py:91`), so a
hand on a rate is twitchy; a hand on a **phase** is not — `rot.phase.*` wraps
±π, 1.0 of throw is a full turn, and while a hand holds it the integrator's
delta is folded into the base each frame so the spin continues underneath
and the hand's turn rides on top (`params.py:459-464`). On release the
picture returns by the offset, so a phase must be pushed from a centred
rest, never positioned. A quarter turn maps the tesseract and the 24-cell
onto themselves, so ±45° across a tilt's throw is the whole visible range
(`TURN = 0.25`). XY / XZ / YZ read as a rigid 3D tumble; XW / YW / ZW move
the inner cell through the outer one, the 4D inside-out. `view.depth4`
(1.05–13.8, exponential in D−1) is sweet from about 1.6 to 5 and goes
orthographic above 8; `camera.zoom` doubles every 0.1 of throw.

**Faces.** Per-face alpha tops out near 0.18 at brightness 1 and falls with
the face count (`render.py:585-588`), so faces need brightness 2–4 and few
big faces; the tesseract's 24 and the 16-cell's 32 are right, the torus's
560 are not. Of the pattern inputs, the *spatial* ones (HEX cell scale on
`pattern.mod.2`, CELLS density, PLAID frequencies, SPIRAL twist) are safe
under a hand; the *rate* ones enter as `t · (k + c·m)` so a wobble after
ten minutes of uptime scrambles the phase by whole cycles — the same is
true of `view.inst_rate`, `view.bmp_rate`, `fx.warp.drift` and
`fx.tripcolour.pulse`. No hand touches any of those.

**Instances.** The grid is `⌈√n⌉` wide; the zoom that fits it is about
`1 / (rows · 0.72)`, so n = 9 wants 0.46 and n = 68 wants 0.15. Tesseract
and 24-cell fields are cheap at a hundred copies; the 120-cell is not.

**Look-back.** The echo composite is stateless — every fader re-weights the
stored frames at once, so `echo_mix`, `decay`, `darken`, `contrast`,
`occlude`, `echoes` are all instant under a hand. `mix`, `hue`, `sat`, the
tints act only on the dream buffer, which exists only with the worker
(torch, `[dream] enabled`, on this machine). `every`, `res` and `layer`
rebuild things; never routed.

**FX.** Every effect's `on / mix / speed / blend / order` and each `@param`
is a param; `fx.mix` scales every pass's wet/dry, so at half mix a warp is a
double image rather than half a warp — ride an effect's *amount*, not the
mix. `kaleido.segments` is an integer (a hand snaps it); `warp.drift` and
`tripcolour.pulse` are the rate hazards above.

**LFOs.** Output `0.5 + 0.5 · depth · wave`, rest 0.5; a hand positioning
`lfo.N.depth` from 0 opens and closes the swing without touching the phase;
the swing lands one frame late (the LFOs step before `Router.modulate`).
Synced divisions need the clock: before the first METRONOME press a tap
re-pins the downbeat on every tap (audit B2).

## 3. The design principles applied

1. **Six degrees of freedom, no pinches.** Every hand row is on x, y, z,
   roll, pitch or yaw. No preset names a `when` gate. Pinches are free for
   the performer's own Learn on top.
2. **Height means more, tilt means direction, reaching in means deeper.**
   Every `y` row pushes something *up* from the scene's base; every roll /
   pitch / yaw row is centred (a level hand adds nothing); every `z` row
   makes "in" the deeper reading — 4D depth toward 1, the camera closer, the
   kaleidoscope tighter, the trail longer.
3. **Push from the axis's own rest, so a still or absent hand is the
   scene.** With audit B1 open a `position` row keeps positioning a hand
   that has left the box at its rest value. So: every height row is a push
   from rest 0 (left alone, it adds nothing); every tilt row is a push from
   rest 0.5; the three `position` rows are on params whose scene base *is*
   the axis's rest value — `dream.hue` 0, `fx.kaleido.swirl` 0 and
   `lfo.1.depth` 0 — so the hand leaving the box lands the base today and
   after the fix alike. `tests/test_plan12_presets.py` holds that rule and
   sweeps every row with the real hand chain: level = base, ends in the
   row's sign, monotonic, base back when the hand leaves, base when it was
   never seen. **No preset depends on the B1 fix**; the fix only lets a
   knob move a position row's return value later.
4. **One axis, one coherent gesture; chaining for depth.** The field's
   right height fans out to three params (more copies, camera back, a touch
   brighter) so the crowd stays in frame; the trip's left height owns an
   LFO's depth and the LFO owns the camera zoom, so the picture beats only
   while that hand is up.
5. **Coarse and dialled-in-once goes to the desk or the panel.** Shape,
   pattern, plane set, base brightness / speed / zoom, effect and dream
   settings are in the scene (a theme on F1–F5); the routing preset's
   `values` carry only the bases its rows push from (macros, plus what the
   lfo-breathe precedent already carries — audit R1 applies, see §7).
6. **The same hand does the same job across presets.** The left hand grips
   the object in tumble, faces and wake (roll → XY, pitch → YZ, yaw → XZ,
   ±45°). The right hand plays the attraction. Height on either hand is
   always "more".

## 4. The presets

Lane numbers: `hand:0–5` left x, y, z, roll, pitch, yaw; `hand:6–11` right;
12–13 presence; 14–21 the pinch switches (pinned to `hands/core.py` by the
tests). *u* is the axis's shaped 0–1: height 0 at the bottom of the box,
the centred axes 0.5 level, thumb-up / fingers-up / fingers-out toward 1.
Every preset also carries the six `lane:` → `rot.rate.*` rows (× the drive
fader) and the `lane:` → `pattern.mod.*` rows, on bases of 1.

### 4.1 `party-tumble` — the polytope (F1 TUMBLE)

Scene: the 24-cell, lines on, faces on with CELLS at mix 0.7, brightness
2.0, speed 0.30, 4D depth 2.6, zoom 1.3, planes XW / YW / ZW on (the music
turns it inside out), XY / XZ / YZ off (the hand's planes: a static pose
that springs back).

| hand axis | parameter | op · depth · rest | what the performer feels (from the sweep) |
|---|---|---|---|
| L roll | `rot.phase.XY` | push +0.25 from 0.5 | thumb up rolls the object 45° clockwise on the screen, thumb down the other way; level, nothing |
| L pitch | `rot.phase.YZ` | push +0.25 from 0.5 | fingers up tips it away 45°, fingers down toward you |
| L yaw | `rot.phase.XZ` | push +0.25 from 0.5 | fingers out turns it 45° about the vertical |
| L height | `master.gain` | push +0.375 from 0 | the music's grip: 1× at the bottom, 2.8× halfway, 8× at the top; the planes kick harder |
| R height | `view.speed` | push +0.45 from 0 | 0.30 rad/s at the bottom, 1.0 halfway, 3.6 at the top |
| R reach (z) | `view.depth4` | push +0.35 from 0.5 | reach in: 4D depth 2.6 → 1.6, the inner cell swells through the outer; pull back: 5.2, nearly flat |
| R roll | `rot.phase.XW` | push +0.25 from 0.5 | a 45° turn in XW on top of the music's spin |
| R yaw | `rot.phase.ZW` | push +0.25 from 0.5 | the same in ZW |

Desk: MASTER fader = the drive the left hand pushes from; track knobs 1–2
(brightness, speed) set what the right hand adds to; knob 8 zoom; clip row
4 / 5 shape; activator buttons pick the planes. All in `DEFAULT_MAP`.

### 4.2 `party-faces` — faces and patterns (F2 FACES)

Scene: the tesseract, faces on with HEX at mix 0.5, brightness 2.5, speed
0.20, 4D depth 2.4, zoom 1.1, planes XW / YW on (the cells pass through
each other), lines on, points off.

| hand axis | parameter | op · depth · rest | what the performer feels |
|---|---|---|---|
| L roll / pitch / yaw | `rot.phase.XY / YZ / XZ` | push +0.25 from 0.5 | the grip, as in tumble |
| L height | `view.bright` | push +0.14 from 0 | the faces glow: 2.5× at the bottom, 3.2× halfway, 4× (the stop) at the top |
| R height | `view.pattern_mix` | push +0.6 from 0 | flat white cells → the full hex pattern at the top |
| R reach (z) | `camera.zoom` | push −0.3 from 0.5 | reach in: 1.1× → 3.0×, the faces fill the frame; pull back: 0.4× |
| R roll | `pattern.mod.2` | push +0.7 from 0.5 | the hex cells' scale (lane 2 leaves this input alone here); thumb up finer, thumb down coarser |
| R pitch | `camera.pitch` | push +0.5 from 0.5 | fingers up: look down onto it (±45°) |

Desk: knob 1 brightness, knob 4 pattern mix (the bases), knob 8 zoom, the
shape rows. The pattern choice itself is on the VIEW page — a candidate
for the desk (§6).

### 4.3 `party-field` — the instance field (F3 FIELD)

Scene: nine 24-cells in ORBIT (amp 0.15, rate 1.2), faces on with EMBER,
brightness 1.6, speed 0.5, 4D depth 3.0, zoom 0.42, planes XY / XW / ZW.

| hand axis | parameter | op · depth · rest | what the performer feels |
|---|---|---|---|
| R height | `view.instances` | push +0.6 from 0 | 9 copies at the bottom, 39 halfway, 68 at the top |
| R height | `camera.zoom` | push −0.15 from 0 | 0.42× → 0.15×: the camera pulls back exactly enough that the 9×9 grid still fits |
| R height | `view.bright` | push +0.1 from 0 | 1.6× → 2.3×, so the small copies still read |
| R roll | `rot.phase.XW` | push +0.25 from 0.5 | every copy turns 45° in XW at once |
| R yaw | `rot.phase.ZW` | push +0.25 from 0.5 | the same in ZW |
| L x | `camera.pan.x` | push +0.1 from 0.5 | the field follows the hand sideways, ±400 px |
| L reach (z) | `camera.pan.y` | push +0.1 from 0.5 | reach in and the field moves up and away, ±400 px |
| L height | `view.inst_amp` | push +0.5 from 0 | how far the copies swing: 0.15 of a cell → 0.65 (they start to collide past 0.5) |

Desk: knob 3 instances, knob 5 grid amp, knob 6 grid rate, knob 8 zoom;
clip row 3 buttons 5–8 pick STILL / ORBIT / WAVE / RIPPLE. The desk covers
this preset completely.

### 4.4 `party-wake` — the look-back wake and the dream (F4 WAKE)

Scene: the 16-cell on PLASMA faces, brightness 2.0, speed 0.35, 4D depth
2.2, zoom 0.9, planes XW / YW / ZW; look-back on with 16 echoes every 2
frames, decay 0.93, echo mix 0.3, darken 0.25, contrast 1.1, occlude 1
(the wake fills the space the shape leaves), dream mix 0.5 on conv3_3 with
2 octaves (the `wake` dream preset).

| hand axis | parameter | op · depth · rest | what the performer feels |
|---|---|---|---|
| L roll / pitch / yaw | `rot.phase.XY / YZ / XZ` | push +0.25 from 0.5 | the grip — turning the object is what paints the wake |
| L height | `view.speed` | push +0.4 from 0 | 0.35 → 3.2 rad/s: the trail stretches |
| R height | `dream.echo_mix` | push +0.7 from 0 | the echoes: 0.3 at the bottom, 1.0 at the top |
| R reach (z) | `dream.decay` | push −0.12 from 0.5 | reach in: decay 0.93 → 0.99, the trail lasts; pull back: 0.87, it snaps off |
| R roll | `dream.hue` | position | the dream's colours round the whole circle; level = as the net painted them |
| R pitch | `dream.mix` | push +0.5 from 0.5 | fingers up: the dream buffer to 0.75; down: 0.25 |

Desk: knob 1 brightness, knob 2 speed. The dream and echo bases have no
desk control today (§6); they are on the LOOKBACK page. `hue` and `mix`
do nothing until the worker runs.

### 4.5 `party-trip` — the effect stack (F5 TRIP)

Scene: the 24-cell on PLASMA faces, brightness 1.5, speed 0.4, zoom 0.8,
planes YZ / XW / ZW; the `trip` fx preset: plasma screened under the
scene (level 0.2), the six-wedge kaleidoscope, the new **zoom burst** at
0.1, the hue cycle at spread 0.8; LFO 1 a quarter-note sine at depth 0.

| hand axis | parameter | op · depth · rest | what the performer feels |
|---|---|---|---|
| R height | `fx.zoomblur.amount` | push +0.8 from 0 | the burst: 0.1 at the bottom, 0.9 at the top — light shoots out from the centre |
| R reach (z) | `fx.kaleido.zoom` | push −0.5 from 0.5 | reach in: 1 → 2, the fold tightens; pull back: 0.5, more of the frame in each wedge |
| R roll | `fx.kaleido.swirl` | position | −2 … +2 radians of twist across the roll; level = none |
| R yaw | `fx.huecycle.spread` | push +0.4 from 0.5 | fingers out: 0.8 → 1.6, the rainbow bands tighten; in: 0 |
| R pitch | `fx.plasma.level` | push +0.4 from 0.5 | fingers up: the plasma floods (0.2 → 0.4); down: gone |
| L height | `lfo.1.depth` | position | opens the pump: 0 at the bottom, 1 at the top |
| `lfo:0` | `camera.zoom` | push +0.08 from 0.5 | the quarter-note sine pumps the zoom ±0.04 of throw (about ±6 %) at full depth |
| L x | `fx.zoomblur.cx` | push +0.8 from 0.5 | the burst's centre follows the hand sideways |
| L reach (z) | `fx.zoomblur.cy` | push −0.8 from 0.5 | reach in and the burst rises to the top of the frame |

Desk: TAP TEMPO ×4–8 then METRONOME once (the downbeat; until then a tap
re-pins it — audit B2, the one place a preset feels it). `fx.mix` and the
effect amounts have no desk control (§6).

## 5. Evidence

All under `docs/plans/assets/12-presets/`, produced by
`uv run python tools/preset_shots.py` (headless: standalone moderngl, fake
hands through the real `HandsIO`, no audio, no dream worker):

- `party-<name>-sheet.png` and `party-<name>/*.png` — the scene under each
  pose: no hands, both level, then one axis at a time at the end of its
  throw. 960×600, the pose held 1.5 s.
- `party-<name>-sweep.md` — every hand row's target at u = 0, ¼, ½, ¾, 1,
  then the hand gone, then never seen. These are the numbers in §4.
- `tests/test_plan12_presets.py` — the same sweep as assertions (19 tests):
  lane numbers pinned to the hands package; every theme, fx and dream file
  names only real ids; the B1 rest rule; level = base, ends in sign,
  monotonic, base back when the hand leaves, base when never seen; the
  field's three-param gesture; the trip's LFO chain from depth 0.

What the shots show and do not: the grip and 4D rows change a still image
little on the symmetric shapes (the sweep tables carry those numbers);
the wake's hue and dream rows do nothing without torch, so those tiles
equal "R up"; the FX rows read directly (burst, zoom, swirl, spread,
plasma, the centre following the left hand).

## 6. What the desk needs — a proposal, not built

`DEFAULT_MAP` already covers `tumble`, `faces` and `field` (the view
faders on the track knobs, shapes and grid motion on the clip grid, planes
on the activators, the clock in the transport corner). It has nothing for
what `wake` and `trip` push from — the echo and dream bases, `fx.mix`, the
effect amounts — nor for the pattern choice, and MIDI rows live in the
user's `bindings.json`, not in a routing preset.

Recommendation: give the eight **device knobs** a second meaning, chosen by
the loaded routing preset — `band.sel.*` today, or a per-preset set of
eight bases: for `wake` echo mix · decay · darken · contrast · occlude ·
dream mix · dream sat · dream k; for `trip` fx mix · plasma level · kaleido
segments · kaleido zoom · burst amount · burst glow · hue paint · hue
spread. Mechanically that is a `desk` block in a routing preset file (eight
target ids) that `load_preset` applies by rewriting the eight `cc:*:16–23`
rows, with the band strip as the default block — a small change to
`routing.py` and `ui_routing.py`, plus a "DEVICE = band | preset" note on
the ROUTING page. Alternative: leave the device knobs alone and put these
bases on the panel only, which is where they are today. I recommend the
first; it is the one change that makes `wake` and `trip` playable from the
desk without the panel, and it keeps MIDI rows out of the routing preset
(the preset carries *which bases*, the user's file still carries *which
knobs*).

## 7. Asks, dependencies, and what waits on eyes

**Code changes I did not make, and want:**

- `library.Project.list()` lists only `~/Hyperspace/projects/`, so the
  factory `party.hyp.json` is not in the load ▾ combo. One line to include
  factory projects (user files shadowing, as every other group does). Until
  then the cards say: copy the file into `~/Hyperspace/projects/` once.
- The desk block of §6.
- `tests/test_routing.py:1372` — the one line I did change: the set of
  preset names `write_factory` exports.

**Audit items this plan touches:**

- **B1** (a hand leaving the box keeps positioning): designed around, §3.3.
  Nothing depends on the fix. After it, the three position rows may have
  their bases moved by a knob and the hand-out landing spot will follow.
- **B2** (a tap re-pins the downbeat before the first trigger): only
  `party-trip`'s pump feels it; the card says METRONOME once after tapping.
- **R1** (a routing preset writing theme state): `party-trip`'s `values`
  carry `lfo.1.sync / shape / depth` the way `lfo-breathe` does, and
  `party-wake`'s carry four `dream.*` bases; the themes carry the same
  numbers, so a preset loaded onto its own scene changes nothing. If R1 is
  resolved by dropping such values, drop them here too — the scenes hold.
- The preset files ride on `hands/core.py`'s default dofs; the sign of
  each axis in the box's actual mounting (plan 08's open check) is what
  the cards' "thumb up", "reach in" assume.

**From the code review, noted rather than built** (each is a change
outside the preset files):

- The `hand:<i>` lane numbers bake in the default dofs order, as the
  `hands-*` files always have; a user `[hands] dofs` list scrambles every
  shipped preset silently. The right fix is a named address
  (`hand:left.roll`) resolved by the adapter, or a warning from `HandsIO`
  when its lane names differ from the default — plan 11 material.
- A theme resets a whole group by naming one id in it (`rot.rate.XY: 1.0`,
  `fx.on: false`, …), which the project note explains and nothing else
  guards; a slot-level "groups to reset" list in `Presets.load` would say
  it outright.
- The fake-hand harness now exists in `tests/test_hands.py`,
  `tools/control_shots.py`, `tools/preset_shots.py` and
  `tests/test_plan12_presets.py`; one shared fixture beside `hands/core.py`
  would do.

**What only the projector and the box can judge:**

1. Brightness on the projector: faces at 2.5× (faces) and 2.0× (wake,
   tumble) against a party room; the left hand's headroom to 4×.
2. The feel of ±45° on a tilt — whether `TURN` wants 0.35, and whether the
   0.5 s return spring on release reads as "let go" or as "slipped".
3. Whether the axis signs match the mounting: thumb up = up, fingers out =
   out, reach in = away from the performer. A flipped sign is a sign flip
   on the row's depth.
4. The field at 68 copies: the collision at swing 0.65, and the frame rate
   with EMBER faces on 68 24-cells (measured cheap offscreen; the window
   and the panel add cost).
5. The wake with the worker running: hue and dream mix under the right
   hand, the conv3_3 texture against 16 echoes, and whether the user's own
   `loud` dream preset (20 echoes every 3, k 0.12, inception 4e) is the
   better base — it is one number away in `wake.json`.
6. The trip's pump at ±6 % zoom on the quarter note, against a real BPM,
   and whether the burst at 0.9 is too much light on a projector.
7. How far each pinch stays usable on top: every pinch lane is free for a
   Learn, but none of the five needs one.
