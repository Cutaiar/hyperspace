# Checkpoint — 2026-08-21

Where the Python re-platform stands after the first build day, and what to
pick up next. Ground truth for behaviour: [`ENGINEERING.md`](ENGINEERING.md);
architecture: [`BLUEPRINT.md`](BLUEPRINT.md); staged plans:
[`plans/`](plans/README.md). Everything below is committed and pushed to
`main` (through `85f5e02`).

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
  - *Camera* — scroll zoom about cursor, right-drag pan, R resets.
  - *Instances* — 1–100 synchronized copies in a grid (CPU path, measured
    51–132 fps at N=100 by the investigation agent).
- **Verification culture:** 127 tests green; a headless imgui smoke draws
  the whole panel per pytest run; `HYPERSPACE_FRAMES=n` gives windowed
  smoke runs; `tools/compare_render.py` regenerates HTML-vs-Python shots.

## Not done — in rough priority order

1. **First real audio capture.** Every live path is code-complete but no
   human has pressed "Listen to mic" on real hardware yet (macOS mic
   permission prompt included). One click plus a clap. (Plan 03 exit note /
   plan 04 checklist.)
2. **Plan 04 — booth hardware.** Blocked on access: the pure-Python
   Pro DJ Link spike against the CDJ-3000/XDJ-AZ (BLT+OSC is the standing
   fallback), ESP32+BNO055 IMU ingest (packet format specced in BLUEPRINT
   §3.4), Δt delay compensation + metronome calibration.
3. **Aesthetic pass on the panel.** Semantics are ported; the look is
   imgui-default-ish: monospace font atlas, uppercase micro-labels, detent
   notches on gain faders, tighter meters, the big cell-count readout.
   (Divergences listed in plan 03 Results.)
4. **Instanced GPU field.** For a *live* field: per-instance rotation
   phases and true instancing (agent prototype measured 621–845 fps at
   N=100; 1–2 days). Current synchronized-grid mode is the v1.
5. **Plan 05 — DAW bridge** (optional, after 04): MIDI/OSC out with 14-bit
   CC pairs + pitch-bend lanes, MIDI clock from deck BPM, inbound control,
   FL-side fuser script. Nothing in the core may depend on it.
6. **Plan 06 — divergence:** freeze/tag the HTML; **fix the trim
   non-monotonicity** (three candidate fixes in plan 06 / ENGINEERING §9 —
   needs the user's choice; the auto/manual switch is the one to propose);
   tempo-locked shapers once DJ Link exists; saveable scenes as JSON;
   per-band LFO knobs; real harmonic detection; scrub bar.
7. **Ideas parked:** per-cell (3-cell) grouping for cell-wise
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
