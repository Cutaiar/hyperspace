# Plan 22 B5 — macro candidates to audition

Four presets of macro configurations, ready to try. **None of them has
been judged.** Deciding which macros feel right is a listening session
with the owner; nothing here was tuned by eye. Each macro has a line
saying what it is meant to do, so you can tell whether it does it.

## Where they live and how to load them

They are in `shared/plan-22-macro-candidates/presets/`, the repo's
folder for presets people share (`shared/README.md`). They are not in
the factory folder. `tests/test_presets.py` pins that folder to 23 files
with the generator's macros, and the factory shows' banks name only
factory presets, so adding files there would change the factory list
and fail those tests. Installed into a home, the candidates show up in
the PRESETS page's list and take no bank slot.

```
cd hyperspace-python
uv run python tools/shared_presets.py install shared/plan-22-macro-candidates
```

This copies into `~/Hyperspace/presets/` (or `HYPERSPACE_HOME`) and never
writes over a file. The running app picks them up within a couple of
seconds.

**To audition:** open PRESETS and load `MACRO PERFORMANCE` (or one of the
others). Play a track with a clear kick and hats. Then turn macro N.
Each file puts its macros on the APC40's **device knobs** (D1–D8 =
macro 1–8). Without the desk, use the macro sliders on the ROUTING page
(the *macros* section), which also shows each macro's subscribers. Bring
each knob back to its resting position before you try the next one:
noon (0.5) for most, zero for BREAKDOWN and DROP.

## The scene they share

All four files load the same scene, so differences you hear and see come
from the macros:

- the 24-cell, faces and lines, the CELLS pattern (it reads all eight
  inputs), all six planes on, every plane's rate 1.0, speed 0.3, 4D
  depth 2.6, brightness 2.0, zoom 1.3
- every pattern input at 1.0 (as designed)
- the **legacy6 routes** the house presets carry: lane *i* (SUB BASS
  MIDB MID UPR AIR) pushes its plane's rate (× the drive fader) and
  pattern input *i*, the latter at the factory depth 0.35
  (`routing.PATTERN_DEPTH`, plan 22 B3: a band at nominal level lifts its
  input by 0.35, a hard transient by about 0.87). These are the routes
  the depth subscribers scale, so a multiplier reads against 0.35: × 1.8
  (INTENSITY's top) is depth 0.63, × 2.2 (DROP's) is 0.77 — only then do
  loud transients reach the inputs' 2.6 end.
- **LFO 1** (sine, 4 bars) pushes HUE (±0.2 of a turn). **LFO 2**
  (triangle, 2 bars) pushes SPREAD (±0.39). Inputs 6 and 7 are left free
  for exactly this.
- a light FX chain, mix 0.4: zoom burst 0.2, deconverge 2, trip warp 0.5,
  hue cycle paint 0.3

Resting the macros lands exactly this scene (the test checks it), so a
knob at rest changes nothing.

## Base or depth: which the macros use and why

- A **base subscriber** is a scene-setter. As the knob turns it sets a
  param's resting value along `from → to`, measured on that param's own
  fader. It changes the picture **with no music playing**. Use it for
  what a scene *is*: its scale, speed, colour, spin, FX amounts.
- A **depth subscriber** scales one route. The route's depth is
  multiplied by `from → to`. It changes only **how hard the music (or
  an LFO) drives** the picture, and does nothing in silence. Use it for
  the music's grip: intensity, per-band gain, breakdowns.

Per-band gain is done with depth subscribers on the lane routes. The
analyzer's own band gains (`band.N.pre / post / trim`) and its attack and
gate (`band.N.atk / thr`) are **session** params. A preset never moves
them (plan 13 D9), and a base subscriber on one is dropped at load. So
"band attack and gate depth" is out of a preset macro's reach. TIGHT
gets its punch from the fast bands' route depths instead.

Ranges are given in the param's units. "Lane routes" means all twelve
legacy6 rows; "rate routes" the six onto `rot.rate.*`; "pattern routes"
the six onto `pattern.mod.0–5`.

## `macro-performance.json` — MACRO PERFORMANCE

Eight knobs that between them cover a whole set. No param takes its base
from two macros, so they can all be played together. Depth subscribers
multiply, so INTENSITY × DROP stacks.

| Macro | Meant to do | Base subscribers | Depth subscribers | Rests |
|---|---|---|---|---|
| 1 INTENSITY | One knob from calm to wild: how much the music moves everything, the glow and the FX | GLOW 0.6 → 1.4; `fx.mix` 0 → 0.8 | all 12 lane routes × 0.2 → 1.8 | 0.5 |
| 2 SCALE | Small and many to big and few; the camera comes in with it | SCALE 0.3 → 1.7; `camera.zoom` 0.7 → 2.41 | SUB → SCALE × 0.5 → 1.5 (the sub's swell grows with the scale) | 0.5 |
| 3 TEMPO | Half-time to double-time feel: every motion slower or faster together | `view.speed` 0.12 → 0.75; SPEED 0.4 → 1.6; `fx.warp.speed` 0.3 → 1.7; `fx.huecycle.speed` 0.05 → 0.45 | MID → SPEED × 0.5 → 1.5 | 0.5 |
| 4 HUE WALK | Walk the palette once round the wheel; colour gets richer as it goes | HUE 0 → 2 (a full turn); COLOUR 0.6 → 1.4; `fx.huecycle.paint` 0 → 0.6 | — | 0.5 |
| 5 TIGHT | Loose, soft and smeared to crisp and punchy | SHARP 0.4 → 1.6; `fx.zoomblur.amount` 0.4 → 0; `fx.deconverge.amount` 4 → 0 | BASS → GLOW and AIR → SHARP × 0.6 → 1.4; SUB → SCALE × 1.4 → 0.6 | 0.5 |
| 6 SPACE | A 3D tumble to a deep turn through W | `view.depth4` 6 → 1.51; XW YW ZW rates 0.2 → 1.8; XY XZ YZ rates 1.8 → 0.2 | the three W rate routes × 0.2 → 1.8; the three 3D rate routes × 1.8 → 0.2 | 0.5 |
| 7 BREAKDOWN | Up pulls everything back and dims it; down releases it | `view.bright` 2.0 → 0.7; `view.pattern_mix` 0.85 → 0.35 | all 12 lane routes × 1.0 → 0.1 | 0 |
| 8 DROP | Up slams every route and scatters the faces | SPREAD 1.0 → 2.4; `fx.warp.amount` 0.5 → 1.6 | all 12 lane routes × 1.0 → 2.2 | 0 |

To try: INTENSITY first, end to end. Then SCALE, TEMPO and SPACE with
the music playing and stopped (their base subscribers should read in
silence too). For a breakdown, ride 7 up over 8–16 bars, then at the
drop pull 7 down and push 8 up together.

## `macro-streams.json` — MACRO STREAMS

One macro per stream: the six analyzer lanes and the two LFOs. It works
like a mixer for what drives the picture. Mostly depth: this is the
music's grip, band by band.

| Macro | Meant to do | Base subscribers | Depth subscribers | Rests |
|---|---|---|---|---|
| 1 SUB | The sub's share: off at zero, as designed at noon, double at full | — | SUB → ZW rate and SUB → SCALE × 0 → 2 | 0.5 |
| 2 BASS | The kick's share | — | BASS → XW rate and BASS → GLOW × 0 → 2 | 0.5 |
| 3 MIDB | The low mids' share | — | MIDB → YW rate and MIDB → WARP × 0 → 2 | 0.5 |
| 4 MID | The mids' share | — | MID → XY rate and MID → SPEED × 0 → 2 | 0.5 |
| 5 UPR | The upper mids' share | — | UPR → XZ rate and UPR → COLOUR × 0 → 2 | 0.5 |
| 6 AIR | The hats' share | — | AIR → YZ rate and AIR → SHARP × 0 → 2 | 0.5 |
| 7 HUE LFO | How far LFO 1 swings the palette: still, up to ±0.4 of a turn | — | LFO 1 → HUE × 0 → 2 | 0.5 |
| 8 SPREAD LFO | How far LFO 2 breathes SPREAD, and the faces from unison to scattered | SPREAD 0.2 → 1.8 | LFO 2 → SPREAD × 0 → 2 | 0.5 |

To try: with a track playing, take each of 1–6 to zero and back. You
should see that band's plane stop and its pattern input go still, and
nothing else change.

## `macro-intensity.json` — MACRO INTENSITY

The same idea built three ways, to find out which is right. D4–D7 keep
the scene knobs (4D depth, yaw, pitch, pattern).

| Macro | Meant to do | Base subscribers | Depth subscribers | Rests |
|---|---|---|---|---|
| 1 INTENSITY | Both: the music's grip and the resting glow and FX (as in MACRO PERFORMANCE) | GLOW 0.6 → 1.4; `fx.mix` 0 → 0.8 | all 12 lane routes × 0.2 → 1.8 | 0.5 |
| 2 INT DEPTH | Only how hard the music drives; with no music, nothing changes | — | all 12 lane routes × 0.2 → 1.8 | 0.5 |
| 3 INT SCENE | Only the resting look: spin, speed, glow and FX; the music's share stays the same | GLOW 0.6 → 1.4; `fx.mix` 0 → 0.8; `view.speed` 0.12 → 0.75; all six rates 0.4 → 1.6 | — | 0.5 |

Macros 1 and 3 share two bases (GLOW, `fx.mix`), and whichever was
turned last wins. Turn one at a time and bring it back to noon.

## `macro-breakdown-drop.json` — MACRO BREAKDOWN DROP

Pull back and release: one knob against two. D4–D7 keep the scene knobs.

| Macro | Meant to do | Base subscribers | Depth subscribers | Rests |
|---|---|---|---|---|
| 1 BREAK/DROP | The whole arc on one throw: down is the breakdown, noon is as is, up is the drop | `view.bright` 1.0 → 4.0; SPREAD 0.4 → 1.6; `fx.warp.amount` 0 → 1.0 | all 12 lane routes × 0.1 → 1.9 | 0.5 |
| 2 BREAKDOWN | Up pulls everything back and dims it; down releases it (as in MACRO PERFORMANCE) | `view.bright` 2.0 → 0.7; `view.pattern_mix` 0.85 → 0.35 | all 12 lane routes × 1.0 → 0.1 | 0 |
| 3 DROP | Up slams every route and scatters the faces (as in MACRO PERFORMANCE) | SPREAD 1.0 → 2.4; `fx.warp.amount` 0.5 → 1.6 | all 12 lane routes × 1.0 → 2.2 | 0 |

Play 1 on its own, or 2 and 3 as a pair, not both. They share bases, and
whichever was turned last wins.

## Changing them

The files are ordinary `hyperspace.preset/2` presets. Edit one on the
ROUTING page and save it, or edit the JSON: a base subscriber's
`from` / `to` are **positions on the target's fader (0–1)**, not values.
`tests/test_macro_candidates.py` loads each file through the real loader
and checks that it loads with no note and no dropped row, that every
subscriber names a real param or a route in the file, that resting the
macros lands the file's own values, and that each macro moves its bases
and scales its routes. It does not judge whether any macro looks good.
