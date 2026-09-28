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
the oracle the golden traces were recorded from.

**Run it:** `uv sync`, `uv run pytest` (628 tests, ~15 s), `uv run
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
(yaw / pitch) → perspective project 3D→2D (`geometry.project_h`,
`geometry.py:818-844`; `project` is the same maths kept as the parity
oracle for the tests). It runs on the CPU; the GPU rasterises. Geometry is
exact to 1e-12 against the traces (`tests/test_core.py:33-53`).

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
- `view.cut_through` (default on) keeps the old blend for face fills; off
  uses separate alpha (ONE, ONE_MINUS_SRC_ALPHA) so in overlay mode a
  fill does not let the desktop through (`render.py:566-574`; PR #26).
  On an opaque window it is invisible.

### 2.2 Faces, patterns, bitmap

True 2-face extraction (cycle walk + support-plane filter) gives
translucent painter-sorted fills; counts match the known values for all
polytopes (`tests/test_control.py:184-196`; the 3D shapes' faces in
`tests/test_shapes3d.py`). UVs are face-local and
perspective-correct (`geometry.face_uvs`).

`shaders/patterns.glsl` is user-editable and hot-reloads on save by mtime
(`render.py:434-444`); a bad edit keeps the last good program and shows
the GLSL error on the panel. Contract: `vec4 pattern(int mode, vec2 uv,
float fid)`, reading `u_time` and `u_mod[8]` — the eight `pattern.mod.k`
params, which any source may drive. Eleven patterned modes ship (plus flat, mode 0); their names live in
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
- **The worker** (`dream.DreamWorker`, optional `[dream]` extra, torch on
  MPS) is temporal: one running buffer blended with each new echo, a few
  gradient-ascent steps per submit, back to the compositor a frame or two
  later. `submit` never blocks; the latest finished result wins; `step ×
  steps / k` is clamped to `STABLE_RATIO` so a preset cannot run away
  (`tests/test_dream.py`). It reads the `dream.*` params on the frame thread
  inside `submit`, never from the worker thread. The performance spike
  behind these numbers is `docs/plans/assets/06-lookback-perf.md`.

### 2.4 FX

One GLSL file per effect under `shaders/fx/`. Every `// @param` uniform
becomes a registry param `fx.<file>.<key>`, plus `on mix speed blend
order` per file; `fx.on` and `fx.mix` govern the chain (`fx.py:114-164, 284-327`). Effects hot-reload by polling the folder every 30 frames; a
parse error keeps the last spec, a compile error skips the pass, all
broken is a copy. Off is bit-identical (`tests/test_fx.py:268`). The
blend modes are arithmetic in the shader, not GL blend state, and a pass
never leaves alpha below its brightest channel. Eleven effects ship,
Noita's `post_final.frag` maths among them; the factory presets are
`library/fx/*.json`. **New effects are new `.glsl` files, not Python.**

### 2.5 Two windows

`app.py` opens the render window (vsync, 4× MSAA, transparent framebuffer)
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
binds. The rig's placement comes from `[output]` in `config.toml`
(`config.py`); a `[overlay]` section is the same thing under its pre-split
name, still read and merged under `[output]`, with a note on stderr asking
for the rename. A `config.toml` that will not parse keeps the defaults and
shows its error on the SYSTEM page.

## 3. Audio sources

Two, both through `AudioEngine._attach` (`audio.py:132-140`):

- **A capture device** (`start_mic(index)`): a `sounddevice.InputStream`,
  mono, at the engine's rate, callback → ring buffer. The device list is
  every input-capable device (`input_devices`); a loopback driver
  (BlackHole, Soundflower, anything named "loopback") is recognised by
  name, pre-selected in the panel's combo, and labelled `System · …`
  (`audio.py:29-52, 157`). That is the one system-audio route: with the
  Mac's output on a Multi-Output Device, everything arrives through the
  plain input path. **Nothing captures at launch** — capture starts when
  `audio.mic` is toggled (`M`), and the device list is read once at panel
  construction, so a device plugged in later needs a restart (audit A3).
- **A file** (`start_file(path)`; wav / mp3 / flac / ogg through
  `soundfile`): mono mean, played through an `OutputStream` at the
  **track's** sample rate, and the analyser is rebuilt at that rate
  (`audio.py:165-191`).

The callbacks only copy samples into the ring; the FFT and the chain run
on the frame loop in `audio.step(dt)` (`audio.py:235-242`). `audio.chain`
is a fresh `Analyzer` on every attach, sharing the old per-band `Params`
objects and copying the layout and master faders, so a source switch
keeps the user's settings and restarts only the trackers and the warm-up
(`tests/test_analyzer.py:412`).

## 4. Audio chain

One chain runs: `analyzer.Analyzer`, the six-band reference chain reshaped
for N bands (1–16). `bands.py` is its parts bin — every constant under its
reference name, `soft_ceil`, the shapers, the per-band `Params`, the scene
rows — and `bands.Chain` is an alias to `Analyzer`. The reference chain
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
routing preset — `lane:i → rot.rate.<plane>` pushes with depth
`dir · ROT_DEPTH` scaled by `master.gain` on rate bases of 0 — which the
parity test drives (`tests/test_routing.py:103`). The factory `default`
table has the same rows on bases of **1**, so the idle spin stays and audio
rides on top. `bands.BANDS` still holds the reference table for those two
uses and the meter tooltip.

**Bands.** Each band is a centre frequency, a Q and a weighting curve
(rect = the reference's bins, triangular, gaussian, butterworth), then the
existing knobs (`analyzer.py:105-186`). Bands can be added, removed and
reordered at runtime; strip order never changes the maths
(`tests/test_analyzer.py:207`); retuning f / q / curve keeps the trackers.
The `band.{i}.*` params are rebuilt on every layout change through the
`Control.on_layout` hook that `build_registry` installs (`control.py:36-45`).

**Headroom.** Nothing hard-clamps the fader path. Four landmarks: `NOM =
1.0` (a band working normally), `KNEE = 1.25` (where the soft ceiling
starts to bend), `HEAD = CEIL = 2.6` (the asymptote). `soft_ceil(x, knee,
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
(`tests/test_core.py:111-124`). Note `master.dyn`'s fader runs to 4× while
the chain clamps it to 1 for the window blend and uses it raw in the
expansion ratio (audit A7).

**Input trim** (`band.{i}.trim` and `master.trim`, dB) is the mixer-style
input stage: off, then −60 dB to +12 dB at 1 dB/step with a detent at 0,
tagged LIN because dB is already a logarithm. It is applied twice — added
to `db` before `u` is formed (so it moves the band against the references
that do *not* adapt: the gate `thr`, `CONF_LO`, `PK_MIN`) and again as `t_db
/ U_SPAN` onto the fader signal after the trackers. The second application
exists because the window normaliser is a two-point auto-calibration and
by construction removes any static gain in front of it: pre-envelope trim
alone is a placebo (`analyzer.py:504-508, 556`).

> ⚠️ **Known limitation, kept on purpose.** On real material from a
> settled state, BASS trim is non-monotonic through the range you would
> reach for: cutting 6–12 dB makes the band drive *harder*, and it only
> attenuates from around −20 dB (measured on the reference: 0 dB → out
> 0.87; −6 → **1.03**; −12 → **1.01**; −20 → 0.75). A hard off (−60 dB)
> correctly produces exactly 0. The cause is the trim's calibration
> depending on harmonic coupling, which the ceiling work moved. It is
> ported as-is and frozen by the parity test; the structural fix is plan
> 06's one open decision (§8) — bias the adaptive window in proportion to
> trim, apply trim as a post-normaliser multiplier, or a per-band manual
> mode that bypasses adaptive normalisation.

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
threshold, contrast, transient and trim: Balanced, Kick & Sizzle, Glacial
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
kHz, log), `q` (0.1–20) and `curve`.

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
228`, `tests/test_control.py:126-146`). Restart is return-to-zero preserving
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
  spinning plane, the active theme slot. A checked box is a red square with
  a white tick.
- **Faders.** Every slider fills red from its origin (zero on a signed
  range) to its value, so position reads at a glance. A slider with its
  readout inside has no knob, only a red edge under the text. A performed
  param shows a **white** ghost bar at the effective value and names its
  owner in the tooltip.
- **Layout.** No page scrolls at `app.CONTROL_SIZE` (`tests/test_ui_shell.py:92`
  holds it for the pages that rig can fill; ROUTING's rows scroll in a
  child by design). Right-aligned groups are measured with `ui.chip_w` /
  `ui.button_w`, never hard-coded offsets. Every widget has its own imgui
  id (`tests/test_ui_lfo.py:86`).
- The large cell-count readout at the top of the view page is still the
  signature element. Keep new UI consistent with this.

## 6. Testing

`uv run pytest` — 634 tests, 11 skipped without torch, about 20 s. `ruff`
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
  (`tests/test_routing.py:1029-1095`), the referee, migration, macros,
  relative writers under modulation (`tests/test_app_relative.py`), rings
  never chasing a performer (`tests/test_midi.py:272`).
- **Boundaries**: the core never imports `midi` / `bridge` / `dream`
  (`tests/test_params.py:286`, `tests/test_bridge.py:381`,
  `tests/test_dream.py:55`); `hands/core.py`, `hands/signal.py`, `lfo.py`,
  `tempo.py` import nothing from the package (`tests/test_*_boundary.py`).
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
frame order in `app.py`, `Keys` and `Mouse`, the `_open_*` config gates,
`audio.py`'s streams, `analysis.py` on its own, `LeapSource` (audit).

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

- **Plan 09's hand checks at the machine** (CHECKPOINT): the prompt from a
  real Learn, `hands-pinch` zoom under pinch + scroll, TAP TEMPO then
  METRONOME, `lfo-breathe` under the right hand, a knob on a hand-owned
  param. Audit B1 predicts the last one fails as documented.
- **The trim decision** (plan 06): the owner picks one of the three fixes
  above; the oracle is re-frozen after.
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
