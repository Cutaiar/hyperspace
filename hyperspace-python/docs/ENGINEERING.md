# Hyperspace — engineering

How the Python app behaves and why it is built that way. This is the
working reference for anyone — human or agent — about to change it: what
the chain does, what has already been tried, how to verify a change, and
what is still open. Structure (the parts, the frame, who may write what) is
in [`ARCHITECTURE.md`](ARCHITECTURE.md); the reasons behind the calls are
in [`DECISIONS.md`](DECISIONS.md); what is currently drifting is in
[`AUDIT-2026-09.md`](AUDIT-2026-09.md).

Refreshed by plan 10 against `main` ef299ef (2026-09-27; line numbers as of
plan 10's docstring commit 488c445): every sentence
below was read against its module. Where plan 09 changed behaviour the
paragraph says so. The HTML-era sections (browser sandbox, deploy) are
gone; `hyperspace-web/hyperspace.html` is frozen and matters here only as
the oracle the golden traces were recorded from. Revised for plan 13
(presets, the session, the two-layer desk) on `plan-13-integration`.

**Run it:** `uv sync`, `uv run pytest` (886 tests, ~35 s), `uv run
hyperspace`. `?` in the app shows the controls cheat sheet.

---

## 1. Geometry

Shapes are built once, lazily, by `geometry.geom(i)` and cached
(`geometry.py:511-527`): vertices as an `(n, 4)` float64 array, edges as an
`(m, 2)` int32 array, normalised to unit circumradius, plus explicit face
cycles for the curved 3D shapes. Three more caches hold faces, triangles
and UVs.

Vertices come from exact standard constructions. Edges are recovered by
`edges_by_min_dist` (every pair at the minimum vertex distance) for the
rectified 5-cell, 24-cell, truncated tesseract, 120-cell and 600-cell; the
5-cell, cubic pyramid, tesseract, 16-cell, the duoprisms and the prisms
build their edge lists explicitly (`geometry.py:160-245`). Helpers:
`expand(base, mode)` applies all-or-even index permutations × all sign
changes with dedup; `cyc3` does the 3D cyclic equivalent for the seed
solids; `prism(V3)` extrudes a 3D solid along w; `duoprism(n, m)` spins
two polygons in orthogonal planes.

The first 18 shapes, ordered by cell count (cells are the 4D analogue of
faces, which is how the original "number of faces" request was honoured).
**The slider index is the identity the golden traces key on — this list
is append-only and the vertex order of these 18 never changes**
(`tests/test_core.py:33`, `tests/test_shapes3d.py:16`).

| # | Shape | Cells | V | E |
|---|---|---|---|---|
| 1 | 5-cell (hypertetrahedron) | 5 | 5 | 10 |
| 2 | 3,3-duoprism | 6 | 9 | 18 |
| 3 | Cubic pyramid | 7 | 9 | 20 |
| 4 | Tesseract (hypercube · hyperhexahedron) | 8 | 16 | 32 |
| 5 | Rectified 5-cell | 10 | 10 | 30 |
| 6 | 4,8-duoprism | 12 | 32 | 64 |
| 7 | 6,6-duoprism | 12 | 36 | 72 |
| 8 | 16-cell (hyperoctahedron) | 16 | 8 | 24 |
| 9 | 10,10-duoprism | 20 | 100 | 200 |
| 10 | Icosahedral prism | 22 | 24 | 72 |
| 11 | 24-cell | 24 | 24 | 96 |
| 12 | Truncated tesseract | 24 | 64 | 128 |
| 13 | 12,12-duoprism | 24 | 144 | 288 |
| 14 | Dodecahedral prism | 32 | 40 | 80 |
| 15 | 20,20-duoprism | 40 | 400 | 800 |
| 16 | 120-cell (hyperdodecahedron) | 120 | 600 | 1200 |
| 17 | 600-cell (hypericosahedron) | 600 | 120 | 720 |
| 18 | Clifford torus (32×16) | — | 512 | 1024 |

Appended after the polytopes is a family of recognisable 3D shapes built
from trig equations — polar curves r(θ), parametric curves (x(t), y(t)),
spherical functions r(θ, φ), and (u, v) surface patches. They live in the
w = 0 hyperplane of the same pipeline; the XW/YW/ZW rotation planes tumble
them through the fourth dimension, which reads as a perspective breathing
(toggle the W planes off for a plain 3D spin). Curved surfaces have no
planar edge cycles for the polytope face extraction to find, so these
builders return explicit face cycles, and nonconvex caps (heart, star) are
ear-clipped at triangulation time. Helpers: `polar_prism`, `curve_prism`,
`ring_prism` extrude a closed outline into a slab; `spherical_surface`
samples r(θ, φ); `param_surface` samples any (u, v) patch; `tube` sweeps a
ring along a closed 3D curve with parallel-transport frames.

| # | Shape | Equation | V | E |
|---|---|---|---|---|
| 19 | Heart | x=16 sin³t, y=13 cos t − 5 cos 2t − 2 cos 3t − cos 4t, extruded | 128 | 192 |
| 20 | Star | {5/2} pentagram outline in polar vertices, extruded | 20 | 30 |
| 21 | Rose | r = cos 2θ, extruded (no caps — the outline self-intersects) | 186 | 285 |
| 22 | Torus | (R + r cos v)·e^{iu}, R=1, r=0.45, 32×16 | 512 | 1024 |
| 23 | Trefoil knot | tube around ((2+cos 3t)e^{2it}, 1.5 sin 3t), 72×8 | 576 | 1152 |
| 24 | Starfruit | r(θ, φ) = 1 + ½ cos 5θ sin⁵φ, 40×15 | 522 | 1080 |
| 25 | Möbius strip | half-twist band; the flipped seam column merges by `kkey` | 320 | 576 |

Every row above was recomputed from `geom(i)` in the plan-10 audit; all 25
match. Two naming notes settled with the owner: "hyper hexahedron" and
"hypercube" are the same object (the tesseract); "hyper dodecagon" was
read as the 120-cell, and a 12,12-duoprism was added so the literal
dodecagon reading is covered too.

## 2. Rendering

The transform is the reference's, exactly: rotate in 4D across six planes →
perspective project 4D→3D (`D4 / (D4 − w)`) → apply drag orientation
(yaw / pitch) → perspective project 3D→2D (`geometry.project_h`; the
parity oracle `project` is that function without the homogeneous divisor,
pinned equal to it on every shape — plan 11, V1). It runs on the CPU; the
GPU rasterises. Geometry is exact to 1e-12 against the traces
(`tests/test_core.py:33-53`). `ViewState`, the dataclass the renderer
draws, lives in `view.py` so nothing needs moderngl to hold a view.

`Renderer.draw` (`render.py:446-481`) is five stages, and with look-back
and FX off the output is bit-identical to the scene pass alone
(`tests/test_render.py:306`):

1. **Scene pass** into an MSAA RGBA target (`draw_scene`, `render.py:498`):
   zoom and pan about the cursor; the instance grid with motion; face
   fills through `patterns.glsl` and the optional bitmap layer; edges;
   points. Painter order on w-depth.
2. **Coverage mask** — the faces again, solid, when the look-back is on
   and occluding, so the wake fills the space between shapes rather than
   glowing over them (`render.py:293-318, 467`).
3. **Look-back** — `lookback.pull()` takes a finished dream result;
   composite, then capture the scene into the history (§2.3).
4. **FX chain** — the enabled effect passes, ping-pong, after the
   composite (§2.4). The history never sees effected pixels
   (`render.py:475-478`).
5. To the window. All post passes run with GL blending off and write
   premultiplied colour.

**The target is bound explicitly** (plan 14 WP1). `Renderer.draw` draws
into whatever framebuffer is bound when it is called; it captures that
target once and binds it again — with its viewport and blending — on
every exit, a raise included, and `Lookback.capture` binds its own target
on every return. `app.draw_render` binds the window (`ctx.screen.use()`)
at the start of every render frame. Before this, a frame that ended on an
offscreen framebuffer made every later frame draw into it while the
window swapped a stale picture, with no error anywhere — the owner's
freeze: WAKE (`dream.on`, `every = 2`) with no dream worker left the
look-back's atlas bound on each frame off the cadence, and any one
exception inside the draw stranded a framebuffer the same way
(`tests/test_render.py::test_a_look_back_frame_with_no_worker_leaves_the_window_bound`,
`::test_one_raising_frame_does_not_strand_the_next`). A frame that still
starts on an offscreen framebuffer is logged (§2.6).

**The window is opaque unless it is the overlay** (plan 14 WP1, the
Pepper's Ghost rig). The render window's framebuffer keeps alpha — it is
created with `TRANSPARENT_FRAMEBUFFER` for overlay mode, in every mode,
pending decision register row 21 — so the compositor shows the desktop
wherever the final alpha is below 1. In window and fullscreen mode the
ground clears to alpha 1, cut-through is off whatever `view.cut_through`
says, and every FX pass writes alpha 1 (`FxChain.opaque`, set by the
renderer each frame; a multiply-blend effect dropped it to 0); the
look-back's composite keeps `scene.a ∪ wake.a`, which is 1 on an opaque
ground. Every factory preset, and one with faces, cut-through, points,
the look-back and every effect on, renders with every pixel at alpha 255
(`tests/test_lookback.py::test_every_factory_preset_renders_opaque_in_window_mode`).
Measured before the fix, offscreen, window mode: TUMBLE 23 % of pixels
below 255 (lowest 94), HEX ENGINE 40 %, and every factory preset some.

### 2.1 Edges, points, brightness

- Edges are screen-space quads, not GL lines: 1 px lines lost the
  near-edge hierarchy the reference has. Width `(0.5 + 1.5·t)`, or
  `(0.35 + 0.85·t)` for shapes over 500 edges, × a brightness scale × zoom;
  sub-pixel width folds into alpha (`render.py:557-560, 637-662`).
- Edge alpha is `(0.10 + 0.90·t²)·B`, clipped to `[0.015, 1]`, where `t` is
  normalised w-depth: the near half glows, the far half recedes
  (`render.py:546-553`).
- `B = brightness · density compensation`, `dens = clamp(340 / edges,
  0.42, 1)` (`render.py:550-551`). Without that term the 120-cell's 1200
  edges clip to a solid blob at the slider position that leaves the 5-cell
  invisible.
- Points are red; radius and alpha are depth-cued, radius also × dpr ×
  zoom with a smaller base for heavy shapes (`render.py:665-669`).
- `view.cut_through` (default on) matters **only in overlay mode**: on a
  see-through ground it keeps the old blend, so a faint fill lowers the
  window's alpha and the desktop shows through it; off uses separate alpha
  (ONE, ONE_MINUS_SRC_ALPHA), so a fill never drops alpha below the
  ground's (PR #26). On an opaque ground — window and fullscreen — the
  renderer never cuts, whatever the toggle (plan 14 WP1;
  `tests/test_lookback.py::test_cut_through_never_cuts_an_opaque_ground`,
  `::test_cut_through_still_cuts_in_overlay_mode`).

### 2.2 Faces, patterns, bitmap

True 2-face extraction (cycle walk + support-plane filter) gives
translucent painter-sorted fills; counts match the known values for all
polytopes (`tests/test_geometry.py`; the 3D shapes' faces in
`tests/test_shapes3d.py`). UVs are face-local and
perspective-correct (`geometry.face_uvs`).

`shaders/patterns.glsl` is user-editable and hot-reloads on save by mtime
(`render.py`, `_maybe_reload_patterns`); a bad edit keeps the last good
program and shows the GLSL error on the panel, with the line numbered as
in the file. Contract: `vec4 pattern(int mode, vec2 uv, float fid)`,
reading `u_time` and `u_mod[8]` — the eight `pattern.mod.k` params, which
any source may drive. The colour helpers (`TAU`, `LUMA`, `hsv`, `pal`,
`hue_rotate`) come from `shaders/_common.glsl`, which `glsl.py` prepends
to the patterns, every effect and the look-back's post pass alike, and
which hot-reloads the same way (a broken edit there shows on the panel;
the post pass, which every frame goes through, falls back to the copy as
shipped); the pattern file keeps its own 2-D hashes, on which its
cellular modes were tuned. Eleven patterned modes ship (plus flat, mode 0); their names live in
`params.PATTERNS`, and a new mode needs both the GLSL case and the name.
The bitmap layer (`view.bmp_*`) textures faces from a file; a bad file
never raises and leaves the plain faces (`tests/test_render.py:147`).

### 2.3 Look-back and the dream

`lookback.Lookback` keeps an atlas of downsampled echoes of past frames
plus one dream buffer `D`, and composites the scene over its own wake,
age-weighted, premultiplied (`lookback.py:326-600`). With no dream worker
it is a plain age-faded tracer. `dream.*` params: `on mix echo_mix decay
darken contrast occlude hue sat tint tint_from tint_hue tint_sat res
echoes every steps step k layer octaves mask_decay jitter` — all
presettable, all modulatable.

- **Chroma.** The net paints in its own primaries whatever the scene's
  palette, so `D` is re-coloured on its way in: `hue` / `sat` on the net's
  own colours, then `tint` cross-fades to luminance × one colour, with
  `tint_from = scene` taking the hue of the newest echo's mean. Echoes pass
  untouched (`tests/test_lookback.py:405`).
- **Occlude.** The render covers the wake where it drew: coverage is
  `max(brightness × 4, the faces' mask)`. Face fills draw at 1–6 % alpha,
  so brightness alone barely covered — hence the mask pass
  (`tests/test_lookback.py:353`).
- **The worker** (`dream.DreamWorker`, the optional `dream` extra, torch
  on MPS) is temporal: one running buffer blended with each new echo, a few
  gradient-ascent steps per submit, back to the compositor a frame or two
  later. `submit` never blocks; the latest finished result wins; `step ×
  steps / k` is clamped to `STABLE_RATIO` so a preset cannot run away
  (`tests/test_dream.py`). It reads the `dream.*` params on the frame thread
  inside `submit`, never from the worker thread. The performance spike
  behind these numbers is `docs/plans/assets/06-lookback-perf.md`.
- **Setup.** torch and the dream stack are ordinary dependencies
  (decision register row 23 (a), 2026-09-29): `uv sync` installs them and
  `[dream] enabled` defaults to on. If the worker cannot start (an unsynced
  environment without torch, missing weights), `app._open_dream` keeps the
  reason (`dream_error`) and the panel shows it: the
  SYSTEM page, the LOOKBACK page's worker line, and the red banner. A
  preset that asks for the dream (`dream.on`, `dream.mix` > 0) with no worker is a banner warning (until dismissed) and a
  stall-log entry, once (the look-back then shows the echoes only).
- **The ring fits the driver.** 32 slots stacked can pass
  `GL_MAX_TEXTURE_SIZE` on a portrait window at `res` 384; the slot shrinks
  to fit (`lookback.fit_atlas`), and if the textures cannot be made
  nothing is captured and `ring_error` says why on the LOOKBACK page.

### 2.4 FX

One GLSL file per effect under `shaders/fx/`. Every `// @param` uniform
becomes a registry param `fx.<file>.<key>`, plus `on mix speed blend
order` per file; `fx.on` and `fx.mix` govern the chain (`fx.py:114-164, 284-327`). Every effect is compiled behind `_common.glsl` and `fx/_lib.glsl`, and
runs on the renderer's one clock (`Renderer.now`). Effects hot-reload by polling the folder every 30 frames (the shared helper files count); a
parse error keeps the last spec, a compile error skips the pass, all
broken is a copy. Off is bit-identical (`tests/test_fx.py:268`). The
blend modes are arithmetic in the shader, not GL blend state, and a pass
never leaves alpha below its brightest channel. Eleven effects ship,
Noita's `post_final.frag` maths among them; the factory presets are
`library/fx/*.json`. **New effects are new `.glsl` files, not Python.**

### 2.5 Two windows

`app.py` opens the render window (vsync, 4× MSAA, a framebuffer with alpha
for overlay mode — opaque in every other mode, §2)
and the control window (opaque, no MSAA, vsync off so it paces off the
render swap) in one GLFW share group, each with its own moderngl context;
the only imgui context lives on the control window (`app.py:136-167, 396-419`). The render window has no imgui at all. Mouse orbit / pan / zoom
are taken from the render window only; keys from both, with the control
window deferring to imgui typing. `imgui.new_frame()` runs before input
handling on purpose: with the 1.87+ event queue, `want_capture_keyboard`
only holds this frame's value after it. `overlay.Output` places the render
window (window · fullscreen · overlay with passthrough and opacity) from
the `output.*` params, applied once a frame through an injectable backend
(`tests/test_overlay.py`); `overlay.*` are aliases the factory table
binds. `output.monitor` offers *follow window* — the screen the window is
on, config `monitor = -1` — and then each screen by name. Quitting, Cmd+R
and the panel's restart button all run `app.close_all`: every open
adapter (MIDI, the bridge, the hands tracker, the dream worker) then the
audio stream, best-effort, so a broken port never blocks an exit. The
SYSTEM page shows each adapter's state — MIDI, the bridge (port,
encoding, messages sent, or why it is off) — beside the hot-reload and
config notices. The optional adapters and the gamepad are config gates
(`[midi]` and `[gamepad]` on by default, `[bridge]`, `[dream]`, `[hands]`
off; `[dream]` also needs the `dream` extra, §2.3); `hyperspace/config.py` documents every key. The rig's placement comes from `[output]` in `config.toml`
(`config.py`); a `[overlay]` section is the same thing under its pre-split
name, still read and merged under `[output]`, with a note on stderr asking
for the rename. A `config.toml` that will not parse keeps the defaults and
shows its error on the SYSTEM page.

### 2.6 The stall log and the red banner

`watchdog.py` (cold, like `app.py`: a reload never touches it) writes
`<home>/stall.log`. Each entry is a `=== <kind>` header — the wall time,
the loaded preset, what happened — then every thread's stack
(`faulthandler.dump_traceback(all_threads=True)`):

- `stall` — no frame completed for 2 s. A daemon thread watches; the loop
  pets it once a frame with a float write. Once per stall.
- `render error` — `renderer.draw` raised (`app.frame` guards it, so the
  panel lives on while the render window holds its last frame): the full
  traceback, once per distinct error.
- `render stall` — no render frame *presented* for 2 s while the loop
  runs: the draw did not complete, or the window was hidden, minimised,
  occluded (macOS occlusion, another Space) or had no framebuffer. The
  entry lists the window's attributes (`GlfwBackend.window_state`).
- `stranded target` — a render frame started on an offscreen framebuffer
  (the freeze's signature, §2), with its `glo` and the last render error.
- `non-finite` — a param dropped a NaN / inf (`Registry.nonfinite`; §5's
  modulation rule drops them, and `tapers.clamp` lands NaN on its low end).
- `warning` — a preset that asks for the dream (`dream.on`, `dream.mix` > 0) with no worker.

`kill -USR1 <pid>` dumps every thread into the same file on demand, and
a stall that holds the GIL — the thread cannot run to see it — is caught
by faulthandler's C timer, which the thread re-arms every look; both are
"raw dumps", with no header. The
SYSTEM page shows `stall log: <path> (N stalls, …)` once the file has
entries. The control window's red banner, across its bottom and in front
of every other window, names a live render error or render stall, a
render error that recovered (its last message, time and count), the
warnings and why the dream worker is off; what is not live stays until
**dismiss**. Nothing in the watchdog may stop the show: a log that will
not open, a platform without SIGUSR1, a write that fails — each is kept
on `error` and the loop goes on (`tests/test_watchdog.py`).

## 3. Audio sources

Two, both through `AudioEngine._attach` (`audio.py:132-140`):

- **A capture device** (`start_mic(index)`): a `sounddevice.InputStream`,
  mono, at the engine's capture rate (`sr`, 48 kHz), callback → ring
  buffer. The device list is every input-capable device
  (`input_devices`); a loopback driver (BlackHole, Soundflower, anything
  named "loopback") is recognised by name, pre-selected by the one
  heuristic `audio.preselect` (the first loopback, else the first
  device), and labelled `System · …`. That is the one system-audio route:
  with the Mac's output on a Multi-Output Device, everything arrives
  through the plain input path. **Nothing captures at launch** — capture
  starts when `audio.mic` is toggled (`M`). The device list is read once,
  on first use (`AudioEngine.devices`, which `audio.device` chooses from);
  the **rescan** button beside the combo (`audio.rescan`) reads it again
  for an interface plugged in later, keeping the selection by name
  (`tests/test_audio.py`).
- **A file** (`start_file(path)`; wav / mp3 / flac / ogg through
  `soundfile`): mono mean, played through an `OutputStream` at the
  **track's** sample rate. The analyser is built **once**, at that rate
  (`AudioEngine._attach(mode, label, rate)`), and the source line on the
  audio page shows the analyser's rate (`AudioEngine.rate`), not the
  capture rate.

The callbacks only copy samples into the ring; the FFT and the chain run
on the frame loop in `audio.step(dt)` (`audio.py:235-242`). `audio.chain`
is a fresh `Analyzer` on every attach, sharing the old per-band `Params`
objects and copying the layout and master faders, so a source switch
keeps the user's settings and restarts only the trackers and the warm-up
(`tests/test_analyzer.py:412`).

## 4. Audio chain

One chain runs: `analyzer.Analyzer`, the six-band reference chain reshaped
for N bands (1–16). `bands.py` is its parts bin — every constant under its
reference name, `soft_ceil`, the shapers, the per-band `Params` and the
one default table `default_params()` (the Balanced scene file is pinned to
it by `test_balanced_is_the_default_table_and_the_reference_edges`).
Two reference constants live where they are used rather than in the
chain: `DRIVE` (fader → rotation rate) is `params.DRIVE`, the meters'
nominal line is `ui.NOM`. The analyzer is constructed by its own name
everywhere (the `bands.Chain` alias is gone). The reference chain
survives as the frozen oracle `tests/legacy_chain.py`, and the "Legacy 6"
layout reproduces it **bit for bit** on the golden fixtures at 60 and 120
fps, dyn 0 and 1 (`tests/test_analyzer.py:63-83`). That test is the
regression net for everything below; re-freeze the oracle only when the
maths changes on purpose.

Per band, in order (`analyzer.py:478-577`):

```
FFT bins → weighted power mean under the band's curve → dB → u (0..2.5; 1.0 nominal, 56 dB window)
  ├─ LEVEL:     asymmetric one-pole (per-band attack / decay)
  │               → peak / valley window + confidence + gate
  │               → upward expansion about the band's running mean
  └─ TRANSIENT: fast env − slow env → relative flux, peak-normalised
  → blend(level, transient) per band          ← the `trn` knob
  → harmonic coupling → soft ceiling          ← this is the INPUT meter (white)
  → pre-drive → soft ceiling → transfer function → post-drive → soft ceiling
                                              ← this is the OUTPUT meter (red)
  → lanes[i] = out[i]  in [0, CEIL)
```

**What changed in plan 07 and 09.** The chain ends at `lanes`. There is no
`PLANEDRIVE` and no band → plane table in the chain: a lane reaches a
rotation plane, a pattern input or anything else as a **route**
(ARCHITECTURE §3). The reference's `dir · out · 3.2 · gain` is the `legacy6`
preset (a routing preset until plan 13 WP5 made it a full one) —
`lane:i → rot.rate.<plane>` pushes with depth `dir · ROT_DEPTH` scaled by
`master.gain` on rate bases of 0 — which the parity test drives through
the code that generates it (`preset.generated`, `tests/test_routing.py`).
The house presets carry the same rows on bases of **1**, so the idle spin
stays and audio rides on top. `bands.BANDS` still holds the reference table for those two
uses and the meter tooltip.

**Bands.** Each band is a centre frequency, a Q and a weighting curve
(rect = the reference's bins, triangular, gaussian, butterworth), then the
existing knobs (`analyzer.py:105-186`). Bands can be added, removed and
reordered at runtime; strip order never changes the maths
(`tests/test_analyzer.py:207`); retuning f / q / curve keeps the trackers.
The `band.{i}.*` params are rebuilt on every layout change through the
`Control.on_layout` hook that `build_registry` installs (`control.py:36-45`).

**Headroom.** Nothing hard-clamps the fader path. Four landmarks: `NOM =
1.0` (a band working normally — a meter landmark, `ui.NOM`), `KNEE = 1.25`
(where the soft ceiling starts to bend), `HEAD = CEIL = 2.6` (the
asymptote; one value, `HEAD` kept as the reference's name for it on the
input and transfer stages). `soft_ceil(x, knee,
ceil)` is the identity below the knee and `knee + r·t/√(1+t²)` above it —
slope 1 at the knee, a t⁻³ tail, strictly increasing
(`tests/test_core.py:58-64`). There are three of them, after coupling, after
pre-drive and after post-drive, as in the reference. The point: a flat top
is not "loud", it is zero dynamics, and the old `clamp(x, 0, HEAD)`
flat-topped four bands at once.

The clipping the owner once reported was manufactured inside the chain:
the expander's makeup had no gain-staging discipline (`DEV_AIM`,
attenuate-only now) and harmonic coupling multiplied an already-clamped
value and clamped again. Coupling now multiplies the *uncoupled* copy and
is followed by the ceiling (`analyzer.py:550-568`). The Python bar for this
is `tests/test_core.py:127-151`: nothing at or above the asymptote, settled
spread within 0.08 of the golden trace.

`WARM_F` (60 frames) fades the expander in (`dev *= min(1, warm / WARM_F)`);
the first three frames use a seed instead of a mean and frames before 60 a
fast 0.25 s mean, because expanding against a stale mean threw every bar
at the ceiling for the opening half second of every track
(`analyzer.py:491-492, 553`). `warm` restarts on every
source attach.

**Meters** read 0..`CEIL` with the nominal line at 38.5 % and the knee at
48.1 %, two stacked tints so working / headroom / knee read as three
shades (`ui.py:869-903`). The bar top is an asymptote, so a column that sits
against `PIN_AT = 0.92·CEIL` for `PIN_HOLD = 0.5 s` is genuinely over-driven
and lights a blinking annunciator — "full" and "wrong" look different.

**Dynamics recovery.** A brickwalled master carries almost no level
variation, so a fixed-floor normaliser maps it to a flat 1.0 and the
rotation becomes a constant rate. Three parts undo that: a **valley
tracker** (the window has a moving floor as well as a moving ceiling),
**upward expansion** about the band's running mean scaled by how squashed
the band already is, and a **transient path** (fast minus slow envelope —
a limiter flattens level but cannot flatten change). Global `master.dyn`
scales the lot; per-band `Contrast` (`exp`) and `Transient` (`trn`) sit at
the top of the strip. A band with genuinely no dynamics stays flat — this
recovers what a limiter took, it does not invent motion
(`tests/test_core.py:111-124`). `master.dyn`'s fader runs to 4× on
purpose: up to 1× it blends from the absolute to the windowed normaliser
and grows the expansion ratio; past 1× the blend is full and only the
expansion keeps growing (owner, 2026-09-28, audit A7; the parity oracle
is frozen at 0 and 1, where the two agree).

**Input trim** (`band.{i}.trim` and `master.trim`, dB) is the mixer-style
input stage: off, then −60 dB to +12 dB at 1 dB/step with a detent at 0,
tagged LIN because dB is already a logarithm. It is applied twice — added
to `db` before `u` is formed (so it moves the band against the references
that do *not* adapt: the gate `thr`, `CONF_LO`, `PK_MIN`) and again as `t_db
/ U_SPAN` onto the fader signal after the trackers. The second application
exists because the window normaliser is a two-point auto-calibration and
by construction removes any static gain in front of it: pre-envelope trim
alone is a placebo (`analyzer.py:504-508, 556`).

**AUTO and MANUAL normalisation** (`band.{i}.norm`, the chip on the band
strip; plan 11 WP15, audit A10). AUTO — every band's default, and every
scene or preset that does not name the key — is the reference chain above,
bit for bit, trim applied twice. It keeps the reference's known behaviour:
on the real track from a settled state, BASS trim is non-monotonic through
the range you would reach for (0 dB → out 0.87; −6 → **1.03**; −12 →
**1.01**; −20 → 0.75; −60 → exactly 0), because the trim's calibration
depends on harmonic coupling. MANUAL is the fix the owner chose
(2026-09-28): for that band the window, the confidence gating of `dyn`, the
expansion and the warm-up are bypassed; the level is the envelope itself in
`u` (1.0 = nominal), which carries the trim once, as a plain gain; the
transient knob blends toward the peak-normalised flux scaled by that level;
the gate, coupling, drives, shaper and ceilings are unchanged. The trackers
keep running, so switching back resumes where the window would have been.
Measured on the brickwalled fixture, BASS settled, MANUAL: 0 dB → 1.63; −6
→ 1.51; −12 → 1.34; −20 → 1.05, non-increasing on every band
(`test_manual_normalisation_makes_trim_monotonic`; `uv run python
tools/trim_sweep.py --manual` prints a sweep). A MANUAL band gives up the
limiter-undoing dynamics recovery; that is the trade.

**Analyser** (`analysis.py`): `FFT_SIZE = 4096`, Blackman window, 1/N
normalisation, `SMOOTHING = 0.15` (the Web Audio smoothing constant) —
deliberately low, the
per-band envelopes do the smoothing and the analyser's own would fight the
attack / decay knobs. It smooths once per `Analyzer.step`, so the spread is
cadence-sensitive (60 vs 120 fps, `tests/test_core.py:114`). The same call
feeds the 4 s log-frequency spectrum history the band editor draws.

**Harmonic coupling** boosts a band by the geometric-mean coherence with
the *next band in frequency order* (the top band reads itself), so
overtone-rich sources drive harder than pure tones (`analyzer.py:364-371, 561-568`). It is a proxy, not integer-multiple peak detection — stated
plainly to the owner. It sits on the input side because it characterises
the signal rather than shaping it.

**13 transfer functions** (`SHAPERS`), each with per-band scratch state so
envelopes and their built-in oscillators hold between frames: `LIN` `SQRT`
`SQ` `CUBE` `CURV` (smoothstep) `GATE` `INV` `HOLD` (peak hold, 0.7 s fall)
`STAC` (4 ms / 75 ms) `CHOP` (5 Hz square) `TREM` (6 Hz sine, 70 % depth)
`S&H` (180 ms) `SLEW` (800 ms). Changing a band's function resets that
band's scratch state. `CHOP`, `TREM` and `S&H` are fixed-rate and unaware of
the tempo clock (plan 09's LFOs are the clock-aware oscillators; audit).

**11 scenes** snapshot every band's function, drives, attack, decay,
threshold, contrast, transient and trim (and, since plan 11, the AUTO /
MANUAL switch, AUTO when a file does not name it): Balanced, Kick & Sizzle, Glacial
Drift, Strobe Cage, Bass Engine, Air & Lace, Inverse World, Percussive,
Tremolo Web, Harmonic Bloom, Slow Bass / Fast Air. A scene **is** a band
preset — the one store is `library/band/*.json`, whose layout carries the
band names; `control.SCENES` only fixes the combo order, because the
APC40's clip grid and saved projects address scenes by index (plan 11,
audit A1). Two ways in: the scene combo, the grid and Reset *re-tune the
bands you have* from the scene's values (`Analyzer.apply_scene`; rows past
the scene's take the default strip) and tell the strip which preset is
current; the preset strip loads the file *whole*, layout included, and
moves the combo when the file is a scene. A user file of the same name
shadows the factory scene for both. A band preset saved from the strip
carries the current layout, names included (`Library.extra`, audit A2).

**Per-band knobs** (`tapers.KNOBS`, registered as `band.{i}.*` and as the
`band.sel.*` aliases that follow the selection): contrast 1:1–1:5,
transient 0–100 %, pre-drive and post-drive off / 0.06–8×, attack 0.5 ms–
2.05 s, decay 5 ms–20.5 s, threshold 0–0.6, trim; plus centre `f` (20 Hz–20
kHz, log), `q` (0.1–20), `curve`, and `norm` (AUTO / MANUAL, a scene
setting, never a performer's).

**Fader tapers.** Every fader is an integer position; a `Taper` owns both
directions and `unmap(map(p)) == p` exactly over the whole throw
(`tests/test_control.py:27`), which is what keeps a scene load from walking
a fader sideways. `exp_zero(u, n)` is exponential with a hard zero at
position 0 and unity at `u`; `exp_pure` has no zero; `exp_time(v0, n)` is a
time constant; `lin_t(d, n)` is `p/d`; `lin_db` is the trim. LOG for every
gain and time constant (equal travel, equal ratio); LIN only where the
quantity is already perceptually even. The LOG / LIN tag is in each knob's
tooltip. For modulation the same taper maps floats without snapping, and a
sub-detent base survives under a performer (ARCHITECTURE §3.1).

**Reset** resolves to the *currently selected scene* (`Control.scene`),
never to hard-coded defaults; on Balanced the two coincide. It re-tunes
the bands loaded and never changes the layout. Reset-all is
guarded by an 8 s **undo** (the button relabels itself) rather than a
confirm; the undo snapshot carries the layout too and is discarded on a
scene change — a strip load included — or any structural change, because
it belongs to the old scene (`control.py`, `tests/test_control.py:74-112`,
`tests/test_analyzer.py` "reset_all_re_tunes").

## 4b. Transport

A file plays through one `OutputStream` that stays open for the life of
the source. **Pause does not tear anything down**: the callback keeps
running and emits silence, so the ring keeps filling and the bands decay
on their own time constants — the shape coasts to rest rather than
freezing. Position is `_offset + _played`, where `_played` counts the
frames the callback has handed to PortAudio (so it leads the DAC by the
buffer latency), folded by the track length for the loop (`audio.py:193-
228`, `tests/test_audio.py` `test_transport_position_math`). Restart is return-to-zero preserving
the play / pause state. Keys, as table rows: `K` play / pause (`audio.play`),
`0` restart, `M` capture on / off. In capture mode `stop()` closes the
stream and `audio.on` goes false, so the chain freezes and every lane row
lets go at once — the bases return that frame.

## 5. Control-surface conventions

The panel is operated mid-set, from a few feet back, in a dark room:
**legibility at a distance comes first.** The reference was a square,
hairline instrument panel; the Python panel keeps its palette and its
signature and softened the rest in September 2026 (PR #24) after it proved
unreadable at a party.

- **Palette.** Black ground, red `#ff2b2b` as the only accent (it matches
  the vertex colour), three greys of text: `TEXT` for values and names,
  `DIM` for labels and idle state, `FAINT` for notes. Nothing a user needs
  to read goes below `FAINT`.
- **Type.** Weight carries it. SF Rounded Medium (16 px) for words, SF
  Rounded Bold uppercase with light tracking (12.5 px) for field labels, SF
  Mono Semibold (16 px) for every number, so a moving readout never
  jitters. The SF faces are variable fonts; `ui.load_fonts` picks the named
  weight through FreeType's face index and falls back off macOS.
- **Shape.** Rounded frames (8 px), pill chips (`ui.chip`) in place of small
  buttons, a solid red pill for anything lit: the open page on the rail, a
  spinning plane, the active preset slot. A checked box is a red square with
  a white tick.
- **Faders.** Every slider fills red from its origin (zero on a signed
  range) to its value, so position reads at a glance. A slider with its
  readout inside has no knob, only a red edge under the text. A performed
  param shows a **white** ghost bar at the effective value and names its
  owner in the tooltip.
- **Layout.** No page scrolls at `app.CONTROL_SIZE`
  (`test_every_page_fits_the_control_window` in `tests/test_ui_shell.py`
  measures every page with a hands setup, an `Output` and a routed table;
  ROUTING's routes, desk, macros and session rows scroll in a child by
  design, and `test_the_routing_rows_scroll_in_their_own_child` and
  `test_the_routing_page_fits_over_a_loaded_preset_and_a_full_desk` hold
  that). The
  HANDS page puts its switches beside the box and its feel knobs two to a
  row beside the transfer plot for that reason. Right-aligned groups are measured
  with `ui.chip_w` / `ui.button_w`, never hard-coded offsets. Every widget
  has its own imgui id (`tests/test_ui_lfo.py:86`). One grey (`ui.LINE`)
  for every rule and frame, one `ui.u32`, one `Panel.half` for a slider
  in a half-width cell.
- **Presets and the bank** (plan 13 §2, §5). A **preset**
  (`<home>/presets/<slug>.json`, `hyperspace.preset/2`, factory ones in
  `hyperspace/library/presets/` shadowed by name) is the whole
  performance: the performance groups' values (`view rot camera pattern
  dream fx lfo macro`), the performer routes, the desk's preset layer,
  the macros and the module labels. A load **replaces everything** (D2):
  every performance param lands from the file or its group default,
  every performer row, the preset layer and the macros are replaced, and
  a session param (`tempo`, `hands`, the analyzer's `band` / `master` /
  `scene` / `audio`, `output`, `overlay`, `ui`) is never touched — a
  tapped BPM survives any preset. What a file names that it may not
  (a session id, an unknown id, a non-performer route, a second
  performer, a desk row on an invariant control) is noted on the panel
  and ignored. A module label is recorded, never chain-loaded (D3). The
  **project** (`hyperspace.project/2`) is the session's values, a
  `startup` preset loaded on launch (D11), and a **bank** of eight preset
  names: F1–F8 and the APC40's clip row 1 load slot k (an empty slot or
  a dangling name loads nothing and says so), ⇧F1–F8 save the live state
  as that slot's preset into the user folder (`PRESET <n>` for an empty
  one), QUANT and pad B step to the next filled slot (`preset.next`). The
  PRESETS page's preset strip lists, loads, saves and deletes them;
  module presets keep their own strips and replace only their group.
- **The desk** (plan 13 §3). The APC40 has two layers under a latched
  SHIFT, whose LED is lit while the global layer is up. The faders, the
  preset row, SHIFT, the clock corner, the transport and the track buttons
  are **invariant**: one meaning on both layers. The **global** layer is
  the session's (the band strip on the device knobs, hand feel and BPM on
  track knobs 1–5, the band scenes on clip rows 2–3); the **preset** layer
  is the loaded preset's (the factory default: the view faders on the
  track knobs, the shape grid, the render toggles). A control the up layer
  does not map is dark and does nothing. Knobs continue from their ring
  after a switch; faders soft-pick-up (hand check 31 is the hardware
  assumption). A macro is a knob with subscribers: each sets a param's
  base or scales a route's depth over its own `from → to`; a hand on a
  macro moves only the depths.
- **Learn and the ROUTING page write into the loaded preset** (plan 13
  §3.3). Right-click → Learn, then a knob: a preset-layer row; then a
  hand: a route naming the axis that moved, `hand:right.pitch` (decision
  register row 20: hand routes are addressed by name, so a rig that
  reorders `[hands] dofs` keeps every preset on its axes; a name the rig
  lacks is dormant; the Replace / Keep prompt as ever). With SHIFT latched,
  or on an invariant control, a knob learn is refused and the reason shows
  on the SYSTEM page's learn line and the ROUTING head. The ROUTING page is
  one page over the loaded preset — head (the preset, its dot, save /
  as…, the layer), routes, the desk with its dark controls, the macros
  and their subscribers, the session's MIDI rows read-only. Nothing there
  writes `bindings.json`; the preset's dirty dot shows the edit until a
  save (the head, the PRESETS strip, ⇧F). Right-click → Unbind removes
  the loaded preset's desk rows on the param, and refuses a session row
  the way Learn does. A route's `scale` is a session param only (the
  drive fader; decision register row 18 (a)); a route may perform a
  session param, marked "session" on its row (row 19 (a)).
- **The home folder** (`~/Hyperspace`). `bindings.json` holds only the
  session's controls — keys, pad, the invariant and global-layer MIDI
  rows; the routes, the preset layer and the macros are the presets'
  (plan 13 §2.2). The routing presets are gone (decision 10): the
  factory ones are presets, and a user's `bindings/*.json` were made
  presets once and are no longer read. The first launch of this build
  migrates an older home once (`preset.migrate_home`, ARCHITECTURE
  §3.8): schema-1 projects become presets and schema-2 projects,
  `bindings.json` gives its preset part to them (a `MIGRATED` preset
  when no project takes it), every rewritten file is kept first as
  `<file>.bak-v<n>` (a dated copy when the name is taken, never over a
  `.bak-*` already there), and stderr names each backup.
- **The cheat sheet** (`ui.CHEATSHEET`) is the canonical human list of the
  keys; `test_the_cheat_sheet_matches_the_tables_and_the_loop_keys` parses
  its key column against `routing.keymap()`, `padmap()` and the keys the
  loop still handles itself (`app.LOOP_KEYS`).
- The large cell-count readout at the top of the view page is still the
  signature element. Keep new UI consistent with this.

## 6. Testing

`uv run pytest` — 886 tests, 11 skipped without torch, about 35 s. `ruff`
is the linter. Every test runs with `HYPERSPACE_HOME` pointed at its own
`tmp_path` (`tests/conftest.py`), so no test can touch `~/Hyperspace`.
What holds what:

- **Golden traces** (`tests/golden/`, recorded once from the HTML by
  `tools/record_golden.py`): geometry exact to 1e-12 with vertex order,
  the audio chain's settled statistics at matched cadence
  (`tests/test_core.py`, `tests/test_golden.py`). The relaxed parity bar
  (DECISIONS): geometry exact, audio behavioural, visuals by eye.
- **The frozen chain** (`tests/legacy_chain.py`) against the analyzer's
  legacy layout, bit-exact (`tests/test_analyzer.py:63`).
- **The control model**: the four plan-09 audit simulations
  (`tests/test_routing.py:1029-1095`), the referee, migration,
  relative writers under modulation (`tests/test_app_relative.py`), rings
  never chasing a performer (`tests/test_midi.py:272`); the APC40's two
  layers — the latch, no fall-through, the release read at the press, the
  knobs re-based and the faders picking up, the sorted map and an older
  file's one-time sort (`tests/test_desk.py`); the macros' base and depth
  subscribers, a performer on a macro moving only its depths, the `scale`
  migration and refusal (`tests/test_macros.py`); the one-time migration
  of an owner-like home — presets, backups, nothing lost, a second
  launch that changes nothing, every hand lane it carries named by the
  rig's layout (`tests/test_migration.py`); hand routes by name — a
  named row follows its axis whatever the dofs order, a name the rig
  lacks is dormant, a number still reads, the gates and the ROUTING combos
  by name (`tests/test_hand_names.py`).
- **Presets and the session** (plan 13): every persisted param in exactly
  one part (`tests/test_params.py`,
  `test_every_persisted_group_is_performance_or_session`); a preset load
  landing every performance base and replacing every route, never
  touching a session param, the bank's slots, ⇧F, the startup preset and
  module labels (`tests/test_presets.py`); Learn into the loaded preset
  and its refusals (`tests/test_learn.py`); the ROUTING page as one page
  over the loaded preset (`tests/test_ui_routing.py`); plan 12's five
  party presets loading by F-key and keeping their rules, WAKE's and
  TRIP's device knobs (`tests/test_plan12_presets.py`).
- **Boundaries**: the core never imports `midi` / `bridge` / `dream`
  (`tests/test_params.py:286`, `tests/test_bridge.py:381`,
  `tests/test_dream.py:55`); `hands/core.py`, `hands/signal.py`, `lfo.py`,
  `tempo.py` import nothing from the package, and `routing.py` nothing
  above it — no panel, host or adapter (`tests/test_*_boundary.py`);
  `config.py` reads the hands rig defaults from `hands/core.py` (the one table),
  never the reverse.
- **Hot reload**: every module but `app.py`, `hotreload.py` and `offline.py`
  is on the watch list in dependency order (leaves first), an optional
  adapter that was never imported is skipped, every swap target `app.py`
  registers is defined in a watched module, and an Enum a reloaded module
  defines keeps its identity, so live params still recognise their `Kind`
  (`tests/test_hotreload.py`; plan 11 WP2).
- **Headless GL and imgui**: every shape renders offscreen; post passes off
  are bit-identical; every panel page draws headless and fits; every
  factory effect compiles and changes the frame.
- **Windowed smoke**: `HYPERSPACE_FRAMES=n uv run hyperspace` runs n frames
  and exits.
- **Screenshots** for the docs: `tools/control_shots.py` (every panel
  page), `tools/fx_shots.py`, `tools/lookback_shots.py`, `tools/dream_shots.py`.
  Probes: `tools/midi_probe.py` (echoes a controller, lights an APC40),
  `tools/hands_probe.py` (every hand axis live; `--calibrate`).

Untested today, and worth knowing before trusting a change there: the
panel being a leaf (no engine module imports `ui*`, by convention). The
frame order, `Keys`, `Mouse`, the `_open_*` gates and the host's
import boundary are `tests/test_app_boundary.py` (the frame runs over
stubs; the boundary in a subprocess); `audio.py`'s streams and
`analysis.py` run headless over a fake `sounddevice`
(`tests/test_audio.py`, the stack's boundary in `tests/test_audio_boundary.py`);
`LeapSource` and the DAW port's open and retry run against a fake `leap`
(`tests/test_hands_leap.py`); the loop-order and Learn paths in
`tests/test_learn.py`. What only the machine can verify is
[`plans/11-hand-checks.md`](plans/11-hand-checks.md).

## 7. Process

Work packages run as parallel agents in worktrees under `.claude/worktrees/`,
one branch and one PR each; the owner merges; each code PR gets a
`/code-review` before merge. Two traps have already cost a round each:

- **Worktree agents branch from the commit HEAD was at when the session
  started**, not from current `main`. Open every agent prompt with `git
  merge main --no-edit` plus a check that the features it needs exist, and
  have the agent stop and report rather than edit if any are missing.
- **An agent's measurements only describe its own branch.** Two agents
  touching one subsystem can each be right and the merge still wrong —
  that is how the trim's non-monotonicity got in. Re-measure the merged
  build before reporting anything as working, and keep it clear which
  numbers are first-hand.

Documents: ARCHITECTURE for structure, this file for behaviour, DECISIONS
for why, CHECKPOINT for the pick-up list. When a change moves a boundary,
the frame order or the control model, the ARCHITECTURE line changes in the
same PR; when it changes behaviour, the line here does.

## 8. Open threads

- **The hand checks at the machine** — plan 09's five, plan 08's
  unverified list, plan 07's WP6c tuning, the first capture, the APC40,
  the second monitor, IAC + FL Studio and the eyeballing owed for PRs #24–#26:
  one numbered list with commands, presets, pass and fail in
  [`plans/11-hand-checks.md`](plans/11-hand-checks.md). Audit B1 (a hand
  leaving the box did not release its rows) was fixed by plan 11 WP1
  before these are run.
- **The trim** (plan 06): decided 2026-09-28 — the per-band AUTO / MANUAL
  switch, built in plan 11 WP15; the oracle was not re-frozen.
- **First real capture on this machine.** Every live path is code-complete;
  no session has recorded a human pressing `M` on real hardware with the
  macOS microphone prompt. One click plus a clap.
- **Booth hardware** (plan 04): Pro DJ Link, IMU, delay compensation —
  blocked on access. The tempo clock deliberately does not sync to
  anything (DECISIONS).
- **WP6c tuning**: dream layer / steps / grade by eye with real audio;
  factory dream presets; the ~1-in-300 GL stall with the worker on a
  vsynced projector.
- The audit's plan 11 list, in cost order, is the end of
  [`AUDIT-2026-09.md`](AUDIT-2026-09.md).
