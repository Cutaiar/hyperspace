# Plan 07 — The overhaul: two windows, presets, N-band analyzer, one control concept

**Status (2026-09-19):** everything below WP6c is on `main` — WP0 (#9),
WP1 (#10/#16), WP2 (#11), WP4a (#12), WP4b (#13, with the `replace` op),
WP4c (#14), WP6-0 (#15), WP5a (#17), WP6a (#18), WP5b (#19), WP6b (#20).
423 tests. Each work package was one branch, one worktree, one PR.
Left: **WP6c** (tuning at the machine) and the hand checks listed in
`CHECKPOINT.md`'s successor — second monitor / DPI (WP1), APC40
plug/unplug (WP4c's `Ports`), IAC + FL Studio (WP4c), mouse feel of the
band editor and routing matrix (WP5b), the dream look (WP6b).

## Why

Four asks, one theme — Hyperspace becomes a renderer with a single unified
control concept, and everything else (a hardware controller, the audio
analyzer, a DAW) is a *source* driving it:

1. **Two windows.** The render target on a projector/TV, the controls on
   the laptop. Today one GLFW window draws both.
2. **Controls overhaul.** Logical grouping, meaningful defaults, and
   per-group presets to flip through.
3. **Save states.** The Ableton model: a *project* saves everything; each
   *module* (view, camera, a band, the analyzer…) has its own preset
   library you can browse, save to and edit as files.
4. **Audio as a source, not a special case.** The six-band chain becomes an
   N-band (1–16) graphic-EQ-style analyzer — per band: centre frequency,
   Q/width, weighting curve, then the existing envelope/transient/shaper
   chain — whose N lanes can modulate **any** registry parameter. Plane
   drive and the shader band inputs stop being special.

## Decisions (settled with the user — don't re-litigate)

- The analyzer stays **in-process** on the frame loop; MIDI in/out is an
  adapter, never the only path.
- Library home is a folder under the user's home: default `~/Hyperspace`,
  overridable by `HYPERSPACE_HOME` / config. Factory presets ship in the
  repo and are read-only.
- The render window has **no imgui at all**. Cheat sheet, error toast,
  everything: control window.
- **Any registry param is a modulation target** (subject to its
  `modulatable` flag — output monitor, UI state and the like opt out).
  Routes are additive with signed depth; a base of 0 plus depth
  reproduces today's "audio replaces the constant" plane drive.
- Enums, toggles and triggers are modulatable, with hysteresis (params.py
  `MOD_ON/MOD_OFF/MOD_DEADBAND`). MIDI-style pad toggles (`trigger` /
  `momentary` note modes in midi.py) stay as they are.
- Keys, gamepad, MIDI and audio lanes become **one binding table**,
  persisted with the project (WP4b).
- The band editor shows a live **spectrogram heat map** with the band
  curves drawn over it, so a band can be shaped against real signal.
- Rotation phase (`rot.phase.*`) is a param but never persisted: a theme
  changes the look, not where the spin is.

## The foundation everyone builds on (WP0, done)

`params.py` is the contract. What a fresh agent needs to know:

- `Param` has `persist` (belongs in a preset), `modulatable` (a lane may
  drive it) and `alias` (a view onto another param; neither). `Kind.TEXT`
  exists for paths. Triggers never persist.
- **Base vs. effective.** `p.value` is the live object (what the renderer
  reads). `p.base` / `p.norm` / `p.position()` / `p.text()` are the user's
  *setting*. They are equal unless a source is modulating the param.
- **Modulation.** A source calls `p.modulate(u)` every frame it is routed
  to `p` (u is an offset in the param's normalized space; call with 0 to
  hold). `Registry.apply()` runs once per frame (app.py, after
  `audio.step`, before `integrate`/`draw`) and writes `base + Σ offsets`
  to the object — float-mapped through the taper (no detents), wrapped for
  circular params, with hysteresis for enum/toggle/integer, rising-edge
  for triggers. Param-level setters write the base while modulated; a raw
  write to the object is adopted as a delta on the base (that is how the
  rotation integrator and a phase-offset lane coexist); the frame no
  source calls, the base is written back.
- **Persistence.** `Registry.snapshot(group=None, ids=None) → {id: base}`
  and `Registry.restore(dict) → missing ids` are the only serialization.
  `remove(pid)` / `remove_prefix(prefix)` let bands come and go; every
  adapter already treats an unknown id as a no-op.
- New ids: `rot.rate.<XY…ZW>` (signed multiplier, base 1), `rot.phase.<…>`
  (wrap, not persisted), `pattern.mod.0–7` (what patterns.glsl reads as
  `u_bands` for now, base 1), `camera.pan.x/y`, `view.bmp_file` (TEXT).
- `ViewState.rate[6]` and `ViewState.pattern_mod[8]` back those; `integrate`
  multiplies by `rate[p]`; `draw` falls back to `pattern_mod` when no
  `bands` are passed. The legacy `planedrive` path is untouched until WP4b.

Tests: `tests/test_modulation.py`, `tests/test_params.py`.

## Work packages

Sizes are agent-sessions. Each package: its own worktree and branch off
`main`, `uv run pytest` and `uv run ruff check` green, a draft PR. Own only
the files listed; touch others minimally and say so in the PR.

### WP1 — Two windows: render target + control surface · M · parallel

Owns `app.py`, `overlay.py`, `tests/test_overlay.py`; light touch on `ui.py`.

- Second GLFW window sharing the GL context (`glfw.create_window(...,
  share=render_win)`), its own imgui context and `GlfwRenderer`;
  `imgui.set_current_context()` before each window's frame. Render window:
  pure GL, no imgui — which also removes the `want_capture_*` juggling
  from the input code.
- Keys work in both windows; mouse orbit/pan/zoom only on the render
  window (pan/zoom go through `camera.pan.*` / `camera.zoom`, already).
- `overlay.py`'s monitor / fullscreen / frameless / always-on-top /
  transparent logic becomes the *render window's output settings*
  (`output.monitor`, `output.fullscreen`, `output.overlay`…; keep the
  existing `overlay.*` ids working or migrate them with a note). The
  control window stays an ordinary window on the laptop. Separate
  `imgui.ini` per window.
- Cheat sheet and the hot-reload error toast move to the control window.
- Two DPIs (retina laptop vs 1080p projector): `fbw/w` per window.
- Headless tests via the injectable backend in overlay.py. The one thing
  that needs a human is the two-context imgui GLFW backend on macOS with
  a second monitor attached — say so in the PR.

### WP2 — Preset & project library · M–L · parallel · headless

Owns `presets.py` (rewrite on top of the new module), new `library.py`,
`config.py`, `hotreload.py` (watch JSON too), `tests/test_presets.py`,
new `tests/test_library.py`, factory presets under `hyperspace/library/`.

- **Module preset** file: `{"schema": "hyperspace.preset/1", "group":
  "<registry group>", "name": "...", "values": {id: base}}` — one JSON per
  preset, human-editable, produced by `Registry.snapshot(group)`.
- **Project** file (`*.hyp.json`): `{"schema": "hyperspace.project/1",
  "name", "values": <full snapshot>, "modules": {group: preset-ref |
  inline}, "bank": [8 snapshots], "io": {midi profile/map, audio device or
  track}}`. The F1–F8 slot bank keeps its exact behaviour but lives inside
  the project. Today's 8 seeded themes become factory projects (or bank
  seeds of the default project); today's `bands.PRESETS` scenes become
  factory presets for the analyzer module.
- **Library layout:** factory in `hyperspace/library/<group>/*.json`
  (read-only); user library at `$HYPERSPACE_HOME` (default `~/Hyperspace`)
  with the same tree plus `projects/`; `config.toml` and `midi_map.json`
  move there (migrate from the working directory on first run, with a
  message). Overlay: user file shadows factory file of the same name.
- **Live editing:** the library is watched like source; editing a preset
  JSON in a text editor reflects in the running app.
- **Versioning:** `schema` string + a migration table; unknown ids on
  restore are reported, not fatal. The analyzer's preset must carry its
  *layout* (n bands, per-band f/Q/curve) — coordinate the schema with WP4a
  early (see Contracts).
- **API for the UI (WP5a):** `library.list(group)`, `next/prev`, `load`,
  `save_as`, `overwrite`, `rename`, `delete`, `is_dirty(group)`,
  `project.save/load/new`, and "reset group to its default preset".

### WP4a — Analyzer: N-band graphic-EQ front end · L · parallel · headless

Owns `bands.py` (refactor), `analysis.py`, `control.py`, band declarations
in `params.py` (`band.*` only), `tests/test_core.py`, `tests/test_golden.py`,
new `tests/test_analyzer.py`.

- `Analyzer.step(dt) → lanes[N]` (N ∈ 1..16). Per band: `f` (centre Hz),
  `q` (or lo/hi edges — pick one and expose the other as a derived
  readout), `curve` (bin weighting: rect = today, plus triangular /
  gaussian / butterworth-slope), then the existing `atk dec thr exp trn
  trim fn pre post`. Keep the chain math; change its shape.
- Band→plane mapping and `dir` **leave** the chain (they become routes in
  WP4b). Output is N lanes in `[0, CEIL]`. Harmonic coupling generalizes
  from `min(i+1, 5)` to the next band in frequency order.
- Add/remove/reorder bands at runtime: `band.{i}.*` params are
  (re)registered via `Registry.remove_prefix` + `build`; the `band.sel.*`
  aliases keep following the selection.
- **Spectrum history** for the heat map (WP5b): a ring of the last ~4 s of
  spectra, log-spaced (~256 bins) × ~240 columns, exposed as a numpy array
  plus a method to rasterize each band's weighting curve over the same
  axis.
- **Parity guard:** a factory preset "Legacy 6" (the reference edges, rect
  curve, today's per-band values) must reproduce the current `Chain`
  bit-for-bit on the golden traces. `test_golden.py` / `test_core.py` keep
  passing against it — that is the regression net for the refactor.
- Performance is a non-issue (one 4096-pt FFT per frame already; N bands
  is N dot products) — but say what 16 bands costs in the PR.

### WP4b — Routing: modulation bus + unified binding table · L · after WP4a

Owns new `routing.py` (or `modbus.py`), `render.py` (`u_bands` →
`u_lanes[16]` + `u_nlanes`), `shaders/patterns.glsl`, the glue in `app.py`,
`midi.py` (bindings become one kind of route), new tests.

- One `Binding` model: `source ∈ {key, pad, midi cc/note/pitch, lane,
  ext-midi-lane}`, `op ∈ {set/abs, step, toggle, fire, mod(depth)}`,
  target = param id. `KEYMAP`/`PADMAP`/`HATMAP` in app.py and
  `midi_map.json` migrate into it; factory default in the repo; persisted
  with the project (WP2's `io`/`bindings` section).
- `mod` routes call `param.modulate(depth · lane)` every frame; the
  default routing preset reproduces today's `BANDS[i].plane/dir` table
  exactly through `rot.rate.*` (base 0 + signed depth) and lane *i* →
  `pattern.mod.i`. Then delete the `planedrive` path.
- A lane may modulate the analyzer's own params. Allowed; fixed frame
  order is analyzer.step → routes → `reg.apply()` → integrate → draw.

### WP4c — MIDI lanes in / out · M · after WP4b

Plan 05 task 1 as written: outbound lanes to a virtual port (IAC) as
14-bit CC pairs or per-channel pitch bend (natively 14-bit; 16 channels =
the 16-lane cap), rate-limited and change-gated; inbound the same
messages are `ext-midi-lane` sources. Reuse `MidiIO`'s port handling.

### WP5a — Controls shell · M · after WP1 + WP2

Owns `ui.py` (rewrite of `draw()` and neighbours; keep the widget helpers
and the instrument-panel style).

- Tabbed / sectioned pages by registry group: Output · View · Faces &
  Pattern · Bitmap · Camera · Audio Source · Analyzer · Routing · Presets ·
  MIDI/System.
- Every section header gets a preset strip (◀ name ▶ · save · save-as ·
  dirty dot) on WP2's API; "meaningful defaults" = the factory preset a
  group resets to.
- Modulated params draw the base with a ghost marker at the effective
  value (`p.base` vs `p.value` / `p.eff_norm`).

### WP5b — Band / EQ editor · M · after WP4a + WP4b (+ WP5a's shell)

Owns new `ui_bands.py`.

- implot heat map (time × log-frequency, magnitude as colour) from WP4a's
  spectrum history, band weighting curves drawn over it, draggable
  centre/Q handles, add/remove band, and a drag-a-box-on-the-spectrogram
  gesture that sets f/Q from the box.
- Per-band strip below; routing matrix (lanes → params) from WP4b.

### WP6 — Look-back pipeline: Deep-Dreamed frame history · after WP5 · L total

The ask: keep a history of rendered frames, run them through a Deep Dream
pass on the GPU asynchronously (arriving a few frames late is fine), and
composite the dreamed history over the current frame, mostly transparent
and darker, faded in proportion to age — a tracer where only the
high-contrast regions of the scene leave a visibly dreamed wake.

Decided (2026-09-19): the dream is **temporal**, not per-frame. One
running buffer `D`: each frame `D ← blend(D, frame, k)`, then a few
gradient-ascent steps on `D`, then `D` goes back to the compositor.
Persistent content (silhouettes, edges) accumulates dozens of steps over
a second and dreams deep; content that moved fades at `k` — which *is*
the age-proportional tracer. dream-server's 60-step recipe on a single
frame (~300–450 ms on an M3 Max) is neither feasible at the budget nor
needed. Measured step cost on the M3 Max, MPS: VGG16→conv3_3 5.3 ms at
256 px, →conv4_3 7.6 ms; MobileNetV2→block 7 4.3 ms; GL→torch→GL
staging 3.4 ms. Nothing is fixed yet — resolution, net, layer, steps,
octaves, history depth and the copy path are what WP6-0 decides.

- **WP6-0 — performance spike (research, M).** Branch off `main`, a
  `tools/dream_bench/` harness plus a report in
  `docs/plans/assets/06-lookback-perf.md` with measured tables and sample
  images. Questions: where the time goes on the GL↔GPU-compute copy path
  and how it scales with resolution (sync `glReadPixels` vs async PBO,
  pinned memory, unified memory); whether a zero-copy path exists from
  Python on macOS (IOSurface-backed textures shared between OpenGL and
  Metal via PyObjC; MLX's unified-memory arrays; a GLSL ping-pong
  implementation of the conv forward/backward that never leaves
  moderngl); GPU contention against the real render loop at 60 fps and
  the levers that relieve it (resolution, layer depth, steps per frame,
  dream every N frames, fp16, temporal octaves); net/layer choices that
  produce the classic dream look (VGG16 conv layers, GoogLeNet/Inception
  mixed layers, MobileNetV2, ResNet18) at each budget; temporal
  stability (flicker, jitter, gradient normalization, blend `k`); and the
  practical limit on history depth (memory and composite cost per layer
  are both tiny — it is an aesthetic limit). Outputs the recommended
  configuration space for WP6a/6b and the parameter ranges.
- **WP6a — look-back core (M, no new dependency).** `render.py` draws the
  scene to an FBO; new `lookback.py` keeps the history ring and the
  age-weighted composite pass (must preserve scene alpha for the overlay
  mode); `dream.*` params in the registry — `on mix decay darken contrast
  steps step_size layer res every echoes octaves` — all presettable and
  modulatable. With no dream worker this is a plain age-faded tracer,
  headless-testable with the offscreen harness.
- **WP6b — dream worker (M, `hyperspace[dream]` optional extra).**
  `dream.py`, config-gated like midi/bridge, nothing in the core imports
  it; missing torch/MLX degrades to the plain tracer with a note. Worker
  thread (kernels release the GIL), double-buffered hand-off, latest
  finished result wins; the copy path and framework are whatever WP6-0
  found fastest. Reuses dream-server's hook/step code minus the octave
  loop.
  - *Chroma (2026-09-20, follow-up).* The net paints in its own primaries
    — red/green/blue activation blobs whatever the scene's palette — so
    the compositor now re-colours `D` on its way in (`lookback.py`,
    `chroma()`): `dream.hue` / `dream.sat` on the net's own colours (sat 0
    is greyscale), then `dream.tint` cross-fades to luminance × one
    colour — `dream.tint_hue` / `dream.tint_sat`, or with
    `dream.tint_from` on "scene" the hue of the scene's mean colour, read
    off the newest echo at capture (free with a worker attached: the
    copy path reads those pixels anyway). All six are presettable and
    modulatable; the echoes pass untouched. Defaults are neutral.
- **WP6c — tuning at the machine (S, needs the user).** Layer/steps/grade
  by eye with real audio, the GPU-contention number on the real scene,
  two or three factory presets.

## Dependency graph

```
WP0 (done)
 ├─► WP1 two windows ─────────────────────────────┐
 ├─► WP2 presets/library ─────────────────┐       ├─► WP5a shell
 └─► WP4a analyzer ─► WP4b routing ─► WP4c MIDI lanes ─► WP5b band editor
                                                              └─► WP6 look-back
WP6-0 (the spike) is independent and may run any time.
```

Merge order for the first round: WP1 → WP2 → WP4a (WP4a's registry
changes are the largest, so it rebases last).

## Contracts between packages

- **Analyzer preset schema (WP2 ↔ WP4a):** `values` holds the flat
  `band.{i}.*` ids *and* a `layout` key: `{"bands": [{"f", "q", "curve"},
  …]}`. Restore applies layout first (rebuilding params), then values.
- **Lane interface (WP4a ↔ WP4b):** `analyzer.lanes` — a numpy array of
  length N in `[0, CEIL]`, valid after `analyzer.step(dt)`; `analyzer.n`;
  `analyzer.band_names`.
- **Spectrum history (WP4a ↔ WP5b):** `analyzer.history()` → `(spec[T, F]
  in dB, freqs[F] Hz log-spaced)`; `analyzer.band_curve(i, freqs)` → weights.
- **Output params (WP1 ↔ WP5a):** ids under `output.*`; `overlay.*` kept as
  aliases or migrated with a note in the PR.
- **Library API (WP2 ↔ WP5a):** listed under WP2.

## Sharp edges already resolved in WP0 (for the record)

Params had no storage of their own (fixed: base/effective); tapers
quantized to detents (fixed: float map for modulation); plane drive was a
multiplier audio *replaced* (fixed: `rot.rate.*`, additive with base 0);
shader inputs were raw chain output (fixed: `pattern.mod.*`); aliases and
UI state shared the address space with real controls (fixed: flags); pan,
bitmap path and phase were not params (fixed). Still open and assigned:
three binding tables (WP4b), band→plane in the chain (WP4a/4b), scenes vs
themes vs slots (WP2).
