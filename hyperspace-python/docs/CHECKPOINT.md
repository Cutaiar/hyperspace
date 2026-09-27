# Checkpoint — 2026-08-23

Where the Python re-platform stands after the first build days, and what to
pick up next. Ground truth for behaviour: [`ENGINEERING.md`](ENGINEERING.md);
architecture: [`BLUEPRINT.md`](BLUEPRINT.md); staged plans:
[`plans/`](plans/README.md). Everything below is committed and pushed to
`main`.

## How to pick this up

```bash
git clone github.com/Cutaiar/hyperspace && cd hyperspace
uv sync                 # whole environment, from the committed lockfile
uv run pytest           # 127 tests, ~4 s (add -m slow for 3 heavy face counts)
uv run hyperspace       # the app: ? shows the controls cheat sheet
```

Machine prerequisites: [`SETUP.md`](SETUP.md). Rig-specific values will live
in `config.toml` (not yet needed — nothing rig-specific exists until plan 04).

## Done

- **Plan 00 — golden traces.** Playwright harness recorded the HTML's exact
  behaviour: geometry (18 shapes × 3 views, byte-stable, full V/E arrays)
  and audio chain time-series for four clips including the user-supplied
  real track (music-time-aligned, noise floors 0.007–0.026, all committed).
  `hyperspace.html` never runs at runtime — it is only this test oracle.
- **Plan 01 — core parity.** `geometry.py` (18 constructions, exact to
  1e-12 with vertex order preserved), `analysis.py` (AnalyserNode-faithful
  FFT front end), `bands.py` (the entire six-band chain under its reference
  constant names — shapers, scenes, softCeil, the trim bug kept on purpose).
  Audio verified behaviourally per the user's relaxed bar; at matched
  120 fps cadence the settled band statistics match the reference to ±0.08.
- **Plan 02 — renderer.** moderngl window; CPU transforms through the
  parity-proven `project()`, GPU rasterises. Painter-order alpha-over;
  edges as screen-space quads at the reference width formula (1 px GL
  lines lost the near-edge hierarchy — comparison shots drove the fix).
  Side-by-sides vs the HTML: mean pixel delta 0.10–1.05 of 255.
- **Plan 03 — UI, scenes & audio** (renumbered: booth hardware deferred to
  04). imgui panel with meters (NOM/KNEE landmarks, over-drive
  annunciator), band strips (all 8 knobs on exact tapers,
  `unmap(map(p))==p` tested across every throw), 13 shapers, 11 scenes,
  reset-to-scene with 8 s undo, transport, tooltips, cheat-sheet overlay
  (?). Audio: sounddevice mic/loopback capture with BlackHole preselect;
  file playback (wav/mp3/flac/ogg) with reference transport semantics.
- **Expansions (user-directed, same day):**
  - *Face shading* — true 2-face extraction (cycle walk + support-plane
    filter; counts match known values for all 18 shapes), translucent
    painter-sorted fills. F key.
  - *Procedural patterns* — user-editable `hyperspace/shaders/patterns.glsl`,
    hot-reloads on save, bad edits keep the last good program and surface
    the GLSL error in the panel. Full-colour vec4 contract with hsv/palette
    helpers; five band-reactive interference patterns ship. UVs are
    face-local and perspective-correct (product of the two projection
    divisors as homogeneous w).
  - *Camera* — scroll zoom about cursor, shift-drag or right-drag pan,
    R resets. (The zoom needed a follow-up fix: imgui 1.87+ only publishes
    `io.mouse_wheel` during `new_frame()`, so the frame now starts before
    input handling.)
  - *Instances* — 1–100 synchronized copies in a grid (CPU path, measured
    51–132 fps at N=100 by the investigation agent).
  - *Panel aesthetic pass* (2026-08-23) — monospace font atlas (SF Mono
    with per-platform fallbacks, silently degrades to the imgui default),
    tracked uppercase micro-labels, detent notches at each fader's unity
    position (`Taper.unity`), meters rebuilt to the reference geometry
    (78 px bars, stacked headroom zone panes, blinking over-annunciator
    caps), and the big white cell-count readout as the panel signature.
- **Verification culture:** 127 tests green; a headless imgui smoke draws
  the whole panel per pytest run; `HYPERSPACE_FRAMES=n` gives windowed
  smoke runs; `tools/compare_render.py` regenerates HTML-vs-Python shots.
- **Control registry + MIDI (2026-09-08).** `params.py` gives every
  settable thing a stable id and one normalized interface (continuous /
  enum / toggle / trigger; tapered params quantize to their throw). The
  panel, `KEYMAP`/`PADMAP` and the MIDI map are all binding tables over it.
  `midi.py` (mido + python-rtmidi, config-gated, core never imports it)
  routes CC/note/pitch-bend with soft pickup, sends ring and LED feedback
  change-gated every frame, and learns bindings from a right-click on any
  panel control into `midi_map.json`. `apc40.py` is the first device
  profile (mode SysEx, LED colours, a 109-binding default layout); the
  numbers were checked against the desk's APC40, which dumps its fader
  positions on mode entry exactly as mapped. 208 tests.
- **Plan 09 executed (2026-09-26; PRs #33–#37).** One
  path for every live source (`Router.modulate`; `drive` / `glide` /
  `abs`-on-a-lane gone), one performer per parameter with the referee
  (`Owned`) and the Replace / Keep prompt, two ops (`push` about the
  source's rest, `position`), eight macro knobs as routing-layer state,
  a tap-tempo clock (`B`, TAP TEMPO) with the global LFO trigger (`⇧B`,
  METRONOME), four tempo-aware LFOs on their own page, `lfo-breathe`,
  bindings schema 2 with the v1 migration and the factory remap. The
  user's `~/Hyperspace/bindings.json` migrated on this machine: 7 rows
  remapped or added, nothing dropped, six performers kept. 627 tests.
  **Hand checks still owed** (plan 09, "Exit criteria"): the prompt from
  a real Learn (3); `hands-pinch` zoom under pinch + scroll (4); TAP TEMPO
  ×4 at ~140 then METRONOME on the one — `tempo.bpm` within ±1 and the
  swell on the bar, a re-tap moves the readout not the swell (5); the
  right hand deepening `lfo-breathe`'s swell alone (6); an APC knob on a
  hand-owned param moving the base that shows when the hand leaves (7);
  plus the METRONOME LED cadence and the LFO page by eye. **Plan 10 —
  the architecture and documentation pass — is next**, once those pass.

## Not done — in rough priority order

1. **First real audio capture.** Every live path is code-complete but no
   human has pressed "Listen to mic" on real hardware yet (macOS mic
   permission prompt included). One click plus a clap. (Plan 03 exit note /
   plan 04 checklist.)
2. **Plan 04 — booth hardware.** Blocked on access: the pure-Python
   Pro DJ Link spike against the CDJ-3000/XDJ-AZ (BLT+OSC is the standing
   fallback), ESP32+BNO055 IMU ingest (packet format specced in BLUEPRINT
   §3.4), Δt delay compensation + metronome calibration.
3. **Instanced GPU field.** For a *live* field: per-instance rotation
   phases and true instancing (agent prototype measured 621–845 fps at
   N=100; 1–2 days). Current synchronized-grid mode is the v1.
4. **Plan 05 — DAW bridge** (optional, after 04): MIDI/OSC out with 14-bit
   CC pairs + pitch-bend lanes, MIDI clock from deck BPM, inbound control,
   FL-side fuser script. Nothing in the core may depend on it.
5. **Plan 06 — divergence:** freeze/tag the HTML; **fix the trim
   non-monotonicity** (three candidate fixes in plan 06 / ENGINEERING §9 —
   needs the user's choice; the auto/manual switch is the one to propose);
   tempo-locked shapers once DJ Link exists; saveable scenes as JSON;
   per-band LFO knobs; real harmonic detection; scrub bar.
6. **Ideas parked:** per-cell (3-cell) grouping for cell-wise
   colour/pattern assignment; bitmap textures (UV + perspective plumbing
   already built for patterns, so this is now mostly texture upload).

## Decisions that govern future work

- Full Python re-platform; the HTML is a frozen reference, never executed
  at runtime (BLUEPRINT §5). FL Studio connects only via the optional
  bridge (§3.6).
- Parity bar (user, during plan 01): geometry exact; audio behavioural;
  visuals judged by the user's eye.
- Plans 03/04 swapped (user, hardware unavailable). DJ Link spike is the
  first thing to do when deck access exists — it is the only genuine
  unknown in the stack.
