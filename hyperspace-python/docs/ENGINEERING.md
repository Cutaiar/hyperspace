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

**Run it:** `uv sync`, `uv run pytest` (1178 tests with plan 16; 1276
on `plan-18-integration`, which holds plans 17 and 18; about a minute
and a half), `uv run hyperspace`. `?` in the app shows the controls cheat
sheet, which is off at launch since plan 16.

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

`Renderer.draw` (`render.py`, `_draw_frame`) is seven stages, and with
look-back, FX and the ghost hands off and the master dim at 1 the output
is bit-identical to the scene pass alone (`tests/test_render.py:306`,
`tests/test_ghost.py`, `tests/test_render.py::test_dim_at_one_is_the_old_frame_exactly`):

1. **Scene pass** into an MSAA RGBA target (`draw_scene`, `render.py:498`):
   zoom and pan about the cursor; the instance grid with motion; face
   fills through `patterns.glsl` and the optional bitmap layer; edges;
   points. Painter order on w-depth. With `view.instances` at **0**
   (plan 16 WP5; the range is 0–100, the readout "0 · nothing drawn") the
   pass clears to the ground and draws nothing — no faces, lines or
   points, no vertex buffer written — and every stage below still runs:
   the coverage mask sees no faces, the look-back composites and
   captures (so the echoes already there fade out over the empty scene),
   an effect that paints on its own still paints, the ghost hands draw,
   the dim dims. At 1 the frame is bit for bit the one it was
   (`tests/test_render.py::test_zero_instances_draws_only_the_ground`,
   `::test_zero_instances_still_runs_the_look_back_and_the_effects`,
   `::test_one_instance_is_the_frame_it_was`).
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
6. **Ghost hands** — when `ghost.on` and a hand is in view, both hands
   over the finished target in their own pass and camera (§2.7). Nothing
   before it sees them.
7. **Master dim** (plan 15 WP3, decision 28) — when `Renderer.dim` is
   under 1, one full-screen triangle that multiplies what is on the
   target by the factor (`Renderer.dim_pass`). It reads no texture and
   draws nothing: the fragment is `vec4(0, 0, 0, factor)` and the blend
   function does the multiply. Window and fullscreen (an opaque ground):
   colour × factor, alpha left exactly as it was, so the ground stays
   opaque black at any dim. Overlay (a see-through ground): colour and
   alpha both scale, so the render fades off the desktop. The scene, the
   look-back, every effect and the ghost hands dim alike; the look-back's
   history and the dream worker are fed before it and never hold a dim.
   The multiply is linear in the framebuffer's values (0.5 is half the
   8-bit value, not half the perceived brightness); a curve would go on
   `factor` inside `dim_pass`. At 1 the pass does not run. A driver that
   refuses its program leaves the frame undimmed, is not asked again
   until a reload, and the reason is on `Renderer.dim_error` and under
   the dim's row on the OUTPUT page (`tests/test_render.py`, the seven
   `dim` tests). Seen offscreen and in a scripted launch on a laptop
   window; not on the projector or the glass (hand check 55).

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
Pepper's Ghost rig), **and there is no overlay unless the config asks**
(decision 21 (a), plan 14 WP2). With `[output] overlay = false`, the
default, the render window is created without `TRANSPARENT_FRAMEBUFFER`
(`app._windows(overlay)`), `output.overlay` refuses to switch on
(`Output._set_overlay`: the `T` key and MASTER select `note:0:80` bind the
`overlay.on` alias, the panel draws the toggle disabled with the reason,
a preset cannot carry it), and `Output.mode` never reads overlay, so the
ground (`output.bg`, alias `overlay.bg`; the crossfader's until plan 15
WP3, now set from the OUTPUT page only) and `output.alpha` do nothing; `on_start` is
ignored with a note on stderr (`tests/test_overlay.py::test_overlay_refuses_every_road_while_the_config_shuts_it`,
`::test_the_ground_and_opacity_do_nothing_while_shut`,
`tests/test_app_boundary.py::test_the_render_window_is_transparent_only_when_the_config_asks`).
With `overlay = true` the framebuffer keeps alpha for overlay mode, so the
compositor shows the desktop wherever the final alpha is below 1. In
window and fullscreen mode the
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
it is a plain age-faded tracer. `dream.*` params: `on mix echo_mix fade
darken contrast occlude hue sat tint tint_from tint_hue tint_sat res
echoes gap steps step k layer octaves mask_decay jitter` — all
presettable, all modulatable but `gap` and `res`.

- **Echo time is seconds** (plan 14 WP6). The ring keeps its own clock,
  advanced once a frame by the renderer's time (`Lookback.tick`); an echo's
  weight is `echo_mix · ½^(age / fade)` with its age in seconds, and a
  capture is committed every `gap` seconds (a frame within half a frame of
  its due time is on time). So the trail is the same on a 60 Hz and a
  120 Hz screen (`tests/test_lookback.py::test_the_same_preset_gives_the_same_trail_at_60_and_120_hz`).
  A tick whose time did not move counts as one 60 Hz frame, so a test or
  tool drawing at a fixed `t` sees the old frames. The old per-frame
  `dream.decay` / `dream.every` are read as 60 Hz frames
  (`lookback.migrate_values` / `migrate_row`): the factory files are
  converted, the launch rewrites a user preset or look-back module preset
  once (`preset.migrate_echo_home`, each kept as `<file>.bak-v2-frames`),
  and a preset file still naming them loads in seconds with a note. The
  dream worker's own `k` and `mask_decay` are still per submitted frame.

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
never leaves alpha below its brightest channel. Twelve effects ship,
Noita's `post_final.frag` maths among them; the factory presets are
`library/fx/*.json`. **New effects are new `.glsl` files, not Python.**

**The FX page** (`ui_fx.py`; plan 16 WP2 and WP3). The chain's bypass
and mix, then one chip per effect in stack order, **three to a row**
(`CHIPS_PER_ROW`; at four the LED's square cut seven of the twelve names
short). A chip is two click targets: the **LED** at its left end
(`##led.fx.<name>.on`, a filled dot while the effect is on, a ring while
off) switches the effect and never opens it; the **name**
(`##chip.fx.<name>.on`) opens the effect's strip and never switches it.
Both parts are red while the effect is on, and the open chip has an
outline round both. Which strip is open is a **name**
(`FxState.sel_name`, through `FxState.select(name)` / `selected()` —
the contract plan 20's chain view drives), not a place in the stack:
dragging an effect's order, a preset, module-preset or show load, and an
effect file added or removed never change it; an open effect whose file
goes away falls back to the first and is open again when the file
returns. `fx.select` is a view onto the name, in no preset or file, and
opening a strip is not an undo step. An open effect that is **not
running says why** (`ui_fx.why_idle`, the four conditions of
`FxState.chain()`, first reason only): "off — nothing below shows until
it is on" with a **turn on** chip, "the whole stack is bypassed" with
**effects on**, "FX mix is at 0", "its mix is at 0". Under the line the
strip's rows are dimmed by a veil drawn over them (`ui_fx._dim`) and
stay live — an effect can be set up dark, and a row's right-click menu
opens at full strength; the "on" check is never dimmed, nor the effect's
own mix fader when that is the reason. The two chips write the base
(`Param.set`), one undo step each
(`tests/test_fx.py::test_a_chip_click_selects_and_never_toggles`,
`::test_the_chips_led_toggles_and_never_selects`,
`::test_selection_is_by_name_and_survives_a_reorder`,
`::test_why_idle_names_the_first_reason`,
`::test_the_idle_strips_controls_stay_live`,
`::test_the_page_fits_with_the_tightest_strip_idle`). The clicks in those
tests are simulated mouse events on the real page.

### 2.5 Two windows

`app.py` opens the render window (vsync, 4× MSAA, a framebuffer with alpha
only when `[output] overlay = true` — decision 21; opaque in every mode
but overlay, §2) — reading the config first, since the hint is a
creation-time one —
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
binds, and `Output.allowed` (the config's `overlay`) is the gate every one
of them passes. `output.dim` (the **master dim**, plan 15 WP3) is the one
`output.*` param that is not a window-system setting: 0 is black, 1 is
full, the renderer multiplies the finished frame by it (§2, stage 7), and
`app.frame` hands it over each frame beside the ground. It is a rig
setting — not persisted, not modulatable, no `[output]` key, no alias —
so a launch always starts at full and no preset or show can move it. It
is the OUTPUT page's first row, reading "black" at 0, "100%" only at
full and 1–99 % between; the APC40's crossfader drives it (§5).
`output.monitor` offers *follow window* — the screen the window is
on, config `monitor = -1` — and then each screen by name.

**Where the windows open** (plan 16 WP4; `placement.py`, asked by
`app._windows`). Two sources, in this order. First `[output] monitor`
(the render window; the same key still says which screen fullscreen
covers) and `[output] control_monitor` (the control window): a screen
index in `glfw.get_monitors()` order, the primary first; at 0 or above
the window opens on that screen. Then `<home>/windows.json`
(`hyperspace.windows/1`): the control window's rect and a list of render
rects — one entry today — as they were at the last quit, always the
rect of the plain window, never a fullscreen or overlay cover (whether a
launch is fullscreen is `[output] fullscreen`'s say and is never
remembered). The file fills in what the config leaves at −1, and on a
configured screen it still supplies the spot when the last position was
on that screen. With neither, the windows open where they always did:
render top-left of the primary screen's work area, controls flush right,
16 px in, at their full sizes (on a small screen they overlap and may
overhang). A remembered rect is used only when at least 120 × 80 px of
it, and its top edge, are on a connected screen's work area; a
projector that is gone, a hand-edited file or a rect off every screen
falls back to the default spot with a note on stderr and on the SYSTEM
page (`cfg["notes"]`), so no window opens out of reach. A remembered
size is clipped to the screen it lands on and never opens under
320 × 240. The file is written by `app._save_windows` on quit and on
Cmd+R only — not while running, so a crash costs one drag — and a window
minimised at the quit keeps its old entry; a failed write costs only the
memory. Delete the file to forget; no setting turns it off. It is
machine-specific, like `last_show`. A config index no connected screen
has, or a value that is not a number (`monitor = "left"`), is −1 with
one note and the app launches (`placement.read`, `config.load`; plan 16
WP7); the index then stays −1 for the run, so a screen plugged in after
the launch is picked on the OUTPUT page, not by the config
(`tests/test_placement.py`,
`tests/test_app_boundary.py::test_the_windows_open_where_placement_says`,
`::test_the_exits_save_the_windowed_rects`,
`::test_a_config_screen_that_cannot_be_used_is_minus_one_and_one_note`,
`tests/test_config.py::test_a_screen_that_is_not_a_number_is_minus_one_and_a_note`).
All of it was run with fake screens and on one real screen; it has not
met a second screen (hand check 61).

Quitting, Cmd+R
and the panel's restart button all run `app.close_all`: every open
adapter (MIDI, the bridge, the hands tracker, the dream worker) then the
audio stream, best-effort, so a broken port never blocks an exit. The
SYSTEM page shows each adapter's state — MIDI, the bridge (port,
encoding, messages sent, or why it is off) — beside the hot-reload and
config notices. The optional adapters and the gamepad are config gates
(`[midi]`, `[gamepad]` and `[dream]` on by default — torch is an ordinary
dependency since decision 23, §2.3 — `[bridge]` and `[hands]` off); `hyperspace/config.py` documents every key. The rig's placement comes from `[output]` in `config.toml`
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

### 2.7 Ghost hands

`ghost.py`: both tracked hands drawn as generic 3D hands that follow the
Ultraleap skeleton, the way VR hands follow a headset's tracking — a
display for the performer and for newcomers, not a control source.

- **The data.** `LeapSource._frame` (SDK thread) copies each hand's
  skeleton beside its features (`hands.core.skeleton`): palm position,
  normal, direction and width; for each of the five digits its four
  bones' `prev_joint`, `next_joint`, width and rotation; the arm when the
  bindings give one — all plain floats, nothing the SDK owns. The same
  lock, the same staleness rule (`STALE_S`) and the same more-confident-
  hand-per-side rule as the features (`LeapSource.skeletons`).
  `HandsIO.poll` keeps the skeletons of the hands present this frame
  (`min_confidence`) in `HandsIO.skeleton`. It never passes through an
  axis — no One Euro, dead zone, envelope or rest spring — so the ghost
  neither lags nor drifts; it is drawn raw. Fingers stay display-only:
  no lane, no route, no MIDI (decision: twelve axes, eight switches).
- **The pass.** Last in `Renderer._draw_frame`, onto the target after
  the FX chain: the hands draw opaque with a depth buffer into their own
  framebuffer (4× MSAA where the context has it), and one composite lays
  that over the target at `ghost.alpha`, premultiplied — so a
  translucent hand shows none of its own overlaps. On an opaque ground
  the composite's alpha blend is (0, 1): the target's alpha is left
  exactly as it was (plan 14 WP1). In overlay the hands add their
  coverage to the ground's alpha so they show on the desktop. Off, with
  no tracker, or with no hand fading, the pass touches no GL state and
  the frame is bit-identical; the target is bound again on every exit.
- **The camera.** Fixed perspective (38° vertical), independent of the
  4D view's camera, zoom and instances. Leap mm go through the tracking
  mode's basis (`ghost.MODES`) into the stage — x right, y up, z toward
  the performer — then, with `ghost.mirror`, x flips (a mirror or a
  Pepper's Ghost glass). The camera stands behind the performer's hands,
  32° above them, at the distance where every corner of the palm box —
  the union of both hands' x / y / z ranges from `hands.json` (the
  defaults for an axis the setup lacks) — padded by 60 mm for the
  fingers fills the frame. Since plan 18 WP1, where `hands.json` holds
  an interaction box (§5) the palm box is that box, coordinate by
  coordinate (`ghost.box_of`; a coordinate the box leaves open uses the
  ranges as before): the frame is then exactly where a hand counts, and
  a hand leaving the box fades out at the frame's edge, because a hand
  outside the box has no skeleton kept. During a calibration sweep the
  frame still shows the old box. Desktop is the table in `hands/core.py`;
  screentop and HMD are not measured (see `MODES`).
- **The geometry.** `CapsuleHands`: a sphere per joint, a capsule per
  bone, a palm (the four finger metacarpals' bases and knuckles, and the
  thumb web), lit with one light and a rim, both hands near-white (left
  faintly cool, right a light red, as the HANDS page's dots — pale, so
  the guide's red x axis stays its own). A palm-only
  skeleton draws the palm as an ellipse. `HandPose` is the data path —
  stage-space joints plus the bones' raw rotations and the basis — so a
  skinned mesh can replace `CapsuleHands` behind the same
  `draw(poses, view_proj, eye)`.
- **The guide** (`ghost.guide`: OFF, BESIDE, ON HAND; off by default) —
  what each hand is doing, drawn in the same pass: a gauge low on the
  hand's side of the frame, or about its palm. Three axis lines (x red,
  y green, z blue) each carry a ball at its value, −1 to +1 along the
  line, so a hand moved only right moves only the x ball. Three arcs,
  coloured by the axis they turn about, each carry a dot: pitch and yaw
  where the fingers point, roll where the palm faces (a tick at neutral:
  fingers forward, palm down). Each arc spans the axis's range —
  calibrated, else the default — and no more, so it draws the hand's
  reach: roll's ±90° is the lower half only, pitch and yaw never go
  behind the hand. Four beads under the gauge light while the pinch
  switches are closed, and a grab ring beside them closes as the hand
  does. Everything always shows (`guide_values`): an axis the setup has
  at its shaped output, any other feature from the native reading over
  the default range. What a routing row drives keeps its colour at full
  size: an enabled performer row reads it (`routed_names`, by name or
  lane index). The rest is grey, thinner and smaller (`UNROUTED_RGB`,
  `UNROUTED_SIZE`) and still moves.
- **Tethers** (`ghost.tethers`, off by default; only with a guide on) —
  what each hand is wired to. From each routed mark a thin line in its
  colour runs to a label at the frame edge on the hand's side naming the
  params its rows drive ("Brightness · Speed", the registry labels,
  `routed_rows`). A tether starts at a fixed point of the gauge — an
  axis line's outer end, an arc's neutral tick, a pinch bead, the grab
  ring — never the moving ball, so the lines hold still while the balls
  move. The labels stack in the order of their anchors' height so no two
  lines cross, inside the frame. They are drawn flat into the hands'
  framebuffer after the hands (`TetherLabels`: PIL rasterises each label
  once into a texture — the panel's system face where there is one, else
  the Roboto in imgui_bundle), so they fade and composite with the hands
  and keep the target's alpha.
- **Leaving the box.** A hand no longer reported fades out over 0.3 s
  where it was last seen; one that comes back fades in over 0.1 s.
- **Params.** `ghost.on` (default off), `ghost.alpha` (0.6),
  `ghost.mirror`, `ghost.guide` — the `ghost` group, a **session** group
  (`params.PARTS`): the hands are the room's display, like the output's
  placement, so a preset load never turns them off mid-set. Ordinary
  params otherwise: on the HANDS page, learnable to a button or knob.
- **Without a camera.** `tools/hands_tape.py record` keeps a few seconds
  of real frames — features, confidence, skeleton — as a tape
  (`hands/tape.py`); `[hands] tape = "<path>"` plays one in the app
  instead of the camera, `hands_tape.py shots` renders one through the
  ghost offscreen, and every tape under `tests/fixtures/hands/` is
  replayed by `tests/test_hands_tape.py`.

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
  **Home** (plan 15 WP2, decision 27) is the `startup` preset again: the
  Home key (fn ← on a laptop) and the APC40's OVERDUB fire `preset.home`
  → `Project.home`, a load like any other and one undo step ("home →
  TUMBLE"); a show that names no "starts on" loads nothing and says
  "home: this show names no 'starts on' preset — pick one on the PRESETS
  page". **Save-as on the desk** (plan 15 WP4, PR #87, decision 29): a
  hold of 0.6 s (`midi.HOLD_S`) anywhere on the APC40's clip-stop row
  fires `preset.save_new` → `Project.save_new`, which saves the live
  state as a **new** user preset named from the loaded one with the next
  free number (TRIP → TRIP 2 → TRIP 3; a name ending in a number counts
  on from it; with nothing loaded, PRESET 1; `library.next_name`). The
  name is counted against the file stems in both preset folders (as
  slugs, so a file in another case counts), the listed names and the
  bank, so it never overwrites a file and never hides a factory preset.
  The new preset becomes the loaded one with a clean dot and goes into
  the next empty bank slot, the show written at once: "saved TRIP 2 →
  F6". A full bank still saves, to the preset list, and warns "saved
  TRIP 3 — the bank is full: it is in the preset list" (no slot is lit;
  the warning goes when the bank next changes). If the preset saves but
  the show's file cannot be written, the slot is put back and the
  warning is "saved TRIP 2 — the show could not be written: it is in the
  preset list". If the preset itself cannot be saved nothing changes and
  the reason is on the PRESETS page. A tap does nothing. The desk never
  overwrites: plain **save** on the panel and ⇧F1–F8 still do, and what
  they replace goes to the trash first (below). On the PRESETS page a
  slot's right-click menu has **put preset here…** (a list of every
  preset, twelve rows tall before it scrolls; "F6: TRIP 3") and **clear
  slot** (greyed on an empty slot; "F6: cleared — ACID is still in the
  preset list") — `Project.put_slot` / `clear_slot`: they write the show
  at once (a factory show's first write makes your copy), delete no
  file, and put the slot back if the show cannot be written. None of the
  three is an undo step: the bank is the show file's.
- **The party show opens** (decision 22, plan 14 WP3). The panel calls a
  project a **show** (plan 14 §3; the code keeps `Project`). The factory
  shows are `party` (`library.DEFAULT_PROJECT`: TUMBLE, FACES, FIELD,
  WAKE, TRIP on F1–F5) and `house` (the eight house moods, the factory
  default until plan 14); there is no factory `default`. A launch opens
  the show opened last — its name in `<home>/last_show`, written by every
  show load, save as and "starts on" pick (`Library.remember`) — else the
  party, the user's copy of either if there is one (`Library._open_default`).
  Once, for a home plan 13 migrated: a user `projects/default.hyp.json`
  (MIGRATED and the house moods) is renamed `projects/mine.hyp.json`,
  named `mine`, bank and startup as they were, backed up first as
  `default.hyp.json.bak-v2` (a dated copy if that name is taken), said on
  stderr and on the PRESETS page's warning line; a `mine` already there
  leaves both files alone; once settled, `projects/RENAMED.txt` says so and it
  never runs again, so a show you later save as "default" stays yours;
  `last_show` holds the show's file name, not the name inside it
  (`library.unshadow_default`, run by `Library()`
  and after plan 13's migration converts a schema-1 `default`; plan 13's
  MIGRATED now lands in `mine`, made from `house`)
  (`tests/test_party_show.py`).
- **The PRESETS page** (plan 14 WP4), top to bottom: **SHOW** — the
  show's name on its own line, never covered, a dim "factory" beside a
  factory show, then show ▾ (factory shows dim) · save · save as · new;
  **starts on / home ▾** (the label since plan 15 WP2: the preset the
  show opens with is also the one Home and OVERDUB load, and the tooltip
  says so) — labelled, and written into the show the moment it is
  picked (`ui_presets.set_starts_on` → `Project.write`; a factory show's
  write makes your copy); the eight **preset buttons**, two a row, each
  its F-key and its preset's name (elided to the button), the live one
  lit, click loads, ⇧click saves; the **preset strip** (the loaded
  preset, its dot, save / as… / reset — save on a factory preset writes
  your copy); and **more**, folded, a module-preset strip per group; the
  library's warning, error and status lines under all of it (the status
  and the warning also show in the footer's message slot, on every page:
  below). One word per
  thing: show, preset, starts on, module preset, factory. The rail's
  dirty dots and the footer's mark compare against the loaded preset or
  show, floats within undo's tolerance (`undo.alike`, 1e-9 relative;
  plan 16 WP7) — a performer taking a param leaves its base changed in
  the last bits, and that lights no dot, while one detent does
  (`tests/test_undo.py::test_a_performers_round_off_lights_no_dot`): a preset that names no module preset for a group leaves the group
  clean as it landed (`Library.label(g, None)`), a show load keeps the
  performance groups' references and marks the session groups it names
  no module for clean as it left them (`Project._apply`), and a factory
  show opened as shipped is not unsaved (`Project.factory`), so loading a
  factory preset or show shows everything clean (`tests/test_ui_presets.py`).
- **The desk** (plan 13 §3). The APC40 has two layers under a latched
  SHIFT, whose LED is lit while the global layer is up. The faders, the
  preset row, SHIFT, the clock corner, the transport and the track buttons
  are **invariant**: one meaning on both layers. Plan 15 adds three to
  the invariant list (the owner, 2026-10-04): the **crossfader is the
  master dim** (`output.dim`: left black, right full, soft pickup — a
  launch is at full, so a crossfader parked at the left does nothing
  until it is brought up to the value; that CC 0 is the left end is not
  hand-checked), **OVERDUB is home** (lit while the show names a "starts
  on"), and the **clip-stop row is one save-as bar** (WP4, PR #87: dark
  at rest; the whole bar lit while any of it is held; at 0.6 s, if a
  preset was saved, the bar and the new slot's pad blink for 1.5 s and
  then the bar is dark and the pad green — on a full bank only the bar
  blinks, and if nothing was saved nothing blinks; a tap does nothing;
  two fingers save once, and a button still down saves nothing more).
  The blink velocities are Akai's table as `apc40.blink_of` reads it,
  never seen on the device. The on-screen desk shows the bar lit while
  held but does not blink, and the cheat sheet does not name the bar. None of them can be learned, mapped by a click or unbound; since
  plan 17 each keeps doing its one job while a learn is armed (below),
  and a preset's desk
  row on one is dropped at load with a note. The **global** layer is
  the session's (the band strip on the device knobs, hand feel and BPM on
  track knobs 1–5, the band scenes on clip rows 2–3); the **preset** layer
  is the loaded preset's (the factory default: the view faders on the
  track knobs, the shape grid, the render toggles). A control the up layer
  does not map is dark and does nothing. Knobs continue from their ring
  after a switch; faders soft-pick-up (hand check 31 is the hardware
  assumption). **A fader keeps its catch through a preset load unless
  the load moved its param** (plan 15 WP3; `MidiIO.redraw(load=True)`):
  the catch is cleared when the param is gone, when the adapter has no
  last write for it or the fader no last reading, or when the param is
  more than `PICKUP_TOL` from the adapter's last write or from where
  that fader last was. Before, every load cleared every fader's catch,
  and a fader was then dead until it came back within `PICKUP_TOL` of
  the value or crossed it. So the crossfader, S1–S8 and SM (session
  params, which a preset never moves) carry on from where they are after
  a load, and a fader whose base the load did move picks up as before.
  Not covered (audit R13): a fader moved while its row is disabled stays
  caught and jumps on its next applied message (until plan 17 an armed
  Learn took one message the same way; an invariant control, which every
  factory fader is, is now dispatched through a learn). A macro is a knob with subscribers: each sets a param's
  base or scales a route's depth over its own `from → to`; a hand on a
  macro moves only the depths.
- **Knob smoothing** (plan 18 WP2; `desk.slew`, "Knob smoothing", first
  under "midi" on the SYSTEM page; off, or up to 250 ms). A knob or
  fader that sets a value directly (`abs`) used to land it at once on
  one of the param's detents — 100 across an untapered range — so a slow
  turn moved the picture a detent at a time: 80 px of pan, 1.33× of a
  rotation rate, 6.9 % of zoom. With smoothing on, each value arrives
  over that long in a straight line, written between the detents, and
  comes to rest on the very detent it rested on before; the line always
  ends `desk.slew` after the last message. **The running app starts at 80 ms**
  (`routing.SLEW_DEFAULT_S`, set by `app._desk_table` before the show
  lands): a show that saved the number keeps it, "off" included; one
  that did not opens at 80 ms and is clean; changing it marks the show
  unsaved. A bare table (every test rig) is at 0, and at 0 nothing new
  runs: every base and every MIDI message is the one from before.
  What is smoothed: `cc` and `pitch` rows with op `abs` on a continuous,
  non-integer param — the track and device knobs, S1–S8, SM and the
  crossfader, wherever the row's target is such a param. What is not: the cue knob and every other `rel` row (one
  detent a click, on purpose), buttons, and an `abs` row on an enum, a
  toggle, a trigger or a whole-number param (`view.instances`). A param
  that moves by itself (`rot.phase.*` while its plane turns) is written
  at once after its first message. While a value arrives, **the ring
  shows where the knob is sending it**, the message the desk sent before
  there was smoothing, so the encoder is re-based at the fingers and
  never behind them. A value someone else sets meanwhile (the panel, a
  key, an undo) stands and the glide stops; a preset load ends every
  glide but a session param's (the crossfader's dim arrives through a
  load); a layer switch ends none; setting it to off, unplugging the
  desk or quitting lands every value at once. A fader's soft pickup is
  tested as before, and a fader that is caught stays caught through its
  own glide. A knob on a hand-owned param glides the return value under
  the hand. One knob turn is still one undo step: the longest setting,
  250 ms, is held under undo's 0.4 s settle time by a test, and two
  turns merge when closer than the settle time plus the smoothing
  (0.48 s at 80 ms). A preset never moves the setting (D9), and it is on
  no desk knob (decision register rows 54, 55). Never tried on an
  APC40: shown against fake ports and an injected clock
  (`tools/slew_demo.py`), and it leans on hand check 31; hand checks 78
  and 79.
- **The desk's glyphs and diagram** (plan 14 WP7, decision 25). Every
  control has a short glyph (`apc40.LAYOUT`): K1–K8 the track knobs,
  D1–D8 the device knobs, S1–S8 the faders, SM the master, X the
  crossfader, C the cue knob, Gr·c the button field (rows 1–5 clip
  launch, 6 clip stop, 7 track select, 8 activator, 9 solo, 10 rec-arm;
  column 9 scene launch, STOP ALL, MASTER), B1–B22 the other buttons, ⇧
  SHIFT. A ROUTING row, a Learn message and the cheat sheet use the
  glyph; Akai's name stays in the tooltip. The control window draws the
  desk in its bottom-left corner, above the cheat sheet when that shows
  (`ui_desk.py`, `ui.desk`): the layer that is
  up lit exactly as the device is (`Bindings.active`, `routing.led_lit`),
  the rest dark, ⇧ red on the global layer; it reads the table, so it
  works with no device plugged in. A new control in the protocol gets a
  `LAYOUT` entry, or `tests/test_ui_desk.py` fails.
- **The desk's size and labels** (plan 17 WP4; decision register row
  57). There is no DESK page: the one desk window takes the room it has
  (`ui_desk.room`). With the panel open it is the column left of it —
  384 × 431 at the 960 × 900 control size, where it was a fixed 380 ×
  290 — above the cheat sheet when that shows. With the panel hidden
  (`ui.panel`: H, the APC40's DEVICE ON/OFF, or the one chip in the
  desk's header, `big` / `panel`) it is the whole control window, 936 ×
  876, beside the cheat sheet when that shows. It never scrolls. Once a
  layout unit is 44 px wide and 32 px tall (`LABEL_UNIT`,
  `LABEL_UNIT_H`: a desk about 620 px wide) **every lit control carries
  what it does** (`ui_desk.text`): the param's label; for a `set` row on
  an enum that value's name (the bank row reads TUMBLE … NOITA, the
  shape pads the shapes, a scene pad its scene); for a step the label
  and the amount ("Brightness +3"); the id for a param with no label
  (`audio.play`, `audio.stop`, `audio.restart`). The glyph moves to the
  cell's top-left corner, small and dim. **Bright ink is a row of the
  layer that is up, grey an invariant one**; a dark control has its
  glyph alone (D8). The type is 0.2 of a unit, kept between 11 and
  18 px (13 px at the control size), on at most two lines broken at
  spaces (`ui_desk.wrap`); a label that would be cut at that size is
  drawn at 11 px instead, and one still too long ends in "…" (a step
  keeps its amount: "Brightne… +3"). Adjacent pads of a row that say the
  same share one label (the clip-stop bar reads "Save as a new preset"
  once). Under that size the drawing is the glyphs alone, as before. The
  hover reads "D3 · fx.kaleido.segments · Kaleidoscope segments · preset
  layer", Akai's name, and what a click would do. The panel is placed
  once, at launch (`Cond_.once`), so widening the window afterwards
  widens the desk only once the panel is dragged right. At 960 × 900
  with TRIP: 105 labels, about a dozen at 11 px, five cut. Seen only as
  read-backs from a hidden window (`tools/desk_shots.py`,
  `docs/plans/assets/17-learn-and-the-desk/desk-big.png`); whether it
  reads from a step back is hand check 69.
- **Click a control, then a param** (plan 17 WP4; decision register row
  58). The desk window is hit-tested, with no widget per control. A left
  click on a control (`ui_desk.click`): with "Learn desk" armed it
  completes the learn, as a knob bump would; with a hand learn armed it
  does nothing; on the picked control it lets go; otherwise it **picks**
  the control (`Learn.control`). A picked control is framed red on the
  desk and on its ROUTING line, the rows of ROUTING scroll to that line
  — at once if the page is open, else when it is next opened; the page
  is never changed for you — the ROUTING filter is cleared, and a hidden
  panel comes back. If the control can be mapped (not invariant, SHIFT
  not latched: `ui_desk.mappable`) **the open page is drawn disabled —
  dimmed, and taking no input at all — on every page but ROUTING**; the
  rail, the footer and the desk still work. The widget or row label
  under the mouse is framed, with "click: put D3 on Speed", and a left
  click on it maps (`Panel._ctx_pick` → `Learn.map_picked`): the knob
  learn's row, refusals, undo step and message ("learned view.speed ← D3
  (device knob 3) (into the preset); K2 let go"). The widget does not
  move. A file path and `desk.shift` are not targets. An invariant
  control, or any control under SHIFT, is picked for the frame and the
  scroll only; the desk's header says why and what it does ("S3 (track
  fader 3) is invariant (the session's): MIDB Post-drive") and nothing
  dims. The desk's header and the footer say what is picked and count
  down: **a pick lets go by itself after 20 s with no click anywhere in
  the control window** (`ui_desk.PICK_S`, `ui_desk.tick`), saying "D3
  let go — no click for 20 s"; any click restarts the count. It is also
  let go by a click on the picked control, on the desk's empty ground or
  on the footer's line, by picking another control, by arming a learn
  and by a map that lands; not by Esc (which quits) and not by a preset
  load. **No click maps until the mouse has moved 12 px from the click
  that picked** (`PICK_MOVE`, `ui_desk.armed`): on the big desk that
  click brings the panel back under the mouse. On ROUTING, which is
  never dimmed, both lines say to click a param on any other page. An
  armed learn, unlike a pick, never times out. Every click here has been
  an imgui event fed by a test or by `tools/desk_shots.py`; no mouse has
  made one (hand check 70).
- **The right-click menu** (plan 17 WP1–WP3; decision register rows
  59, 60). It opens from a param's widget, from **a row's label**
  (`Panel._ctx_label`: the label of a slider row, of a half row and of a
  fader) and from **every analyzer meter** (`band.select`'s menu; a
  label a page draws by itself, the band ◀ ▶ and the load buttons open
  nothing). It reads the table, never the MIDI adapter, so it is the
  same with `[midi] enabled = false`. Under the id and the "modulated:"
  line it lists what is bound: each of the preset's desk rows as glyph
  and Akai's name ("K2 (track knob 2)", "B16 (▲) · step +3"), each route
  in the router's words ("R height pushes +0.45", "(off)" when
  disabled), each session row dim ("S8 (track fader 8) · invariant", "…
  · global layer"). Then the items. **Learn desk** — wherever a desk row
  can go (`ui_routing.desk_target`: not a file path, not SHIFT's own
  param), device or no device. **Learn hand ▸ left / right** — only with
  a tracker, on a param a hand can drive, for the sides the rig's axes
  have. While this param is armed: the hint in red and **Cancel learn**.
  **Unbind** — drawn only when it would remove something: a plain item
  when the param has desk rows or routes, a submenu ("desk — K2", "route
  — R height, LFO 1", "both") when it has both; it removes the preset's
  desk rows and every route on the param, whatever drives it, as one
  undo step (`Learn.unbind`), and never a session row. Then the hand
  rows' "Gate: … ▸" and "Route a lane here…". "Unbind hand" and the
  "performed by …" line are gone. Shown by tests that answer the popup
  and by fed right-clicks; never opened with a real one (hand checks 64,
  68).
- **A learn listens to one source** (plan 17 WP2; decision register
  rows 60–62). A learn armed as "Learn hand ▸ left" can be completed
  only by an axis of the left hand: the right hand may move freely, and
  a knob, button or fader touched meanwhile does its own job. A learn
  armed as "Learn desk" can be completed only by the desk — a knob, a
  button, or a click on the on-screen desk — and no hand. **The
  session's controls work through an armed desk learn**: a fader moves
  its param, SHIFT latches, TAP taps, a preset pad loads its preset,
  OVERDUB goes home, the clip-stop bar saves, and the learn stays armed
  (to land, after a preset pad, in the preset just loaded). With SHIFT
  latched, any other control is refused — "K2 (track knob 2) is on the
  global layer (the session's) — latch SHIFT off to learn into the
  preset" — and swallowed, **and the learn stays armed**: unlatch SHIFT
  and the same learn lands. A learn that lands on a control says what
  let go ("learned view.bright ← D3 (device knob 3) (into the preset);
  K1 let go"). The row-making is `Learn.learn_control`, in `learn.py`,
  so a click makes the same row with no MIDI adapter at all. Synthetic
  hands and fake ports only (hand checks 65–67).
- **Learn and the ROUTING page write into the loaded preset** (plan 13
  §3.3). Right-click → Learn desk, then a knob: a preset-layer row;
  right-click → Learn hand ▸ left / right, then that
  hand: a route naming the axis that moved, `hand:right.pitch` (decision
  register row 20: hand routes are addressed by name, so a rig that
  reorders `[hands] dofs` keeps every preset on its axes; a name the rig
  lacks is dormant; the Replace / Keep prompt as ever). **What that
  route is** (plan 18 WP3; decision register rows 52, 53): until plan 18
  it was always "positions" — the hand was the param's fader end to end,
  and the param's own setting was ignored while the hand was in. Now a
  tilt, or a hand moving sideways or in (an axis whose "Centred" is on),
  lands "pushes +0.25": it adds to the setting, a quarter of the throw
  over the hand's whole travel, and nothing while level. Height (rests
  at the bottom) pushes the same way onto a range centred on zero (a
  rotation rate, a camera angle, a pan, the hue) and is still the fader
  on anything else (brightness, a mix, speed). A toggle, a list, a
  trigger or a whole-number param keeps the fader from any axis. The
  0.25 is **Learn depth** (`hands.learn_depth`, 0.05–1, on the HANDS
  page under "feel & calibration" after Catch; a session setting, saved
  with the show and with a hands setup); changing it changes only the
  next learn. Measured on a synthetic palm: a learned roll on
  `rot.rate.XY` set at 1× read 0× when level and ±66.56× at the ends
  before, and reads 1× when level and −15.64× … +17.64× now
  (`docs/plans/assets/18-hand-and-knob-feel/learn-default.txt`). A
  learn takes the axis's other routes with it, pushes and positions
  alike, switched on or off — on a factory preset that is the preset's
  own row on that axis — and the learn line says "moved from …"; one ⌘Z
  puts them back. Learning the same axis onto the same param again only
  refreshes the pinch: it never changes a row's op or depth. Rows that
  exist and every preset file are untouched; nothing is refused or
  flagged, a rate under a hand included. No real hand has felt it (hand
  checks 75–77). With SHIFT latched
  a knob learn is refused and stays armed (above); the reason shows in
  the footer for 4 s on every page and, with "— still learning <id>", on
  the SYSTEM page's learn line and the ROUTING head. The ROUTING page is
  one page over the loaded preset — head (the preset, its dot, save /
  as…, the layer, said "desk layer: preset" or "desk layer: global"), routes, the desk with its dark controls, the macros
  and their subscribers, the session's MIDI rows read-only. Nothing there
  writes `bindings.json`; the preset's dirty dot shows the edit until a
  save (the head, the PRESETS strip, ⇧F). Right-click → Unbind removes
  the loaded preset's desk rows on the param and its routes (above), and
  is not offered where only a session row is bound. **The page has a
  filter** (plan 17 WP5; decision register row 63): one field on the
  counts line, left of `+ route`. While it holds text only the lines
  that say every typed word are drawn, in all four sections — a route by
  its sentence ("R roll pushes …"), its source, its target and the
  target's label; a desk, dark or session line by its glyph, Akai's
  name, its source and (when mapped) its target and label; a macro by
  its id, its label and its subscribers, drawn whole. Case does not
  matter; a word is matched anywhere in those strings, raw addresses
  included, so "lfo 1" also finds LFO 2 (`lfo:1`). The counts read "4 of
  176 rows" in red and a × beside the field clears it; a section with
  nothing to show says "no row matches". A line a widget is in use on
  stays until the widget is let go. The filter is UI state — no param,
  not saved, no undo step, empty at launch — and **a preset load leaves
  it**; only emptying it, its × and a click on a desk control clear it.
  A row added while it is set (`+ route`, "Route a lane here…", a Learn)
  shows only if it matches. Nobody has typed in the field in the real
  window (hand check 71). A click on a desk control scrolls the rows —
  their own child, never the page — to that control's line and frames it
  while it is picked (`ui_routing.goto`). A route's `scale` is a session param only (the
  drive fader; decision register row 18 (a)); a route may perform a
  session param, marked "session" on its row (row 19 (a)).
- **The hands' interaction box** (plan 18 WP1; decision register rows
  50, 51). A hand counts only while its palm is inside a box: three
  ranges in the Leap's millimetres (x across, y up, z toward the
  performer; the origin is the camera), one box for both hands, x the
  same distance either side of the camera. A hand the tracker sees
  outside it is **absent to everything**: its axes read nothing, so
  every route on them lets go and the settings return that frame, its
  pinch switches drop, its presence lane and note go off, its ghost
  fades. Before plan 18 "in the box" was only the tracker's confidence,
  so a hand reaching for the APC40, or a passer-by's, performed.
  - *Setting it.* The HANDS page's **calibrate 20 s** sweep sets it,
    with each axis's range: the box is where the palms went (2nd–98th
    percentile, both hands together) plus 40 mm, the margin that lets a
    hand hold an axis at its end stop. A direction is bounded only if
    one hand travelled more than 12 cm along it; otherwise it is left
    open and the note says so ("box: x open (not swept)"). **The box is
    off for the whole sweep** (or it could never be swept wider), so
    any hand in view then performs and is counted: calibrate with
    nobody else in view. **reset ranges** opens the box and puts every
    range back to its default. There is no other control: no switch, no
    sliders, no dragging; the file can be edited by hand.
  - *The edge.* A hand that is in stays in until its palm is 15 mm past
    a face; one that is out comes in only inside the face. The state is
    the palm's own, kept through a frame the confidence floor drops. A
    hand coming back in is caught and glided onto over Catch, like one
    the tracker lost.
  - *The file.* `hands.json`, schema `hyperspace.hands/2`: `"axes"` as
    before and `"box": {"x": [lo, hi], "y": [lo, hi], "z": null}` — a
    `null` coordinate is open, a `null` or missing `box` is no box. A
    schema-1 file (no box) is read as it is and **never rewritten at
    launch**; the first time a sweep or "reset ranges" rewrites it, it
    is first copied beside itself as `hands.json.bak-v1` (a dated name
    if that is taken; nothing there is overwritten; a copy that cannot
    be made is said in the note and the save goes on). A pair that is
    not two finite numbers with lo < hi opens that coordinate and says
    so once on stderr: a bad box opens, it never hides the hands.
  - *The page.* Inside the same 190 × 92 frame as before:

    ```
       the box from above (x across, z down)            height
     ┌──────────────────────────────────────────────┐   ┌──┐
     │                                              │   │  │
     │      ┌──────────────────────────────┐        │   │┬ │  y hi
     │      │                              │        │   ││ │
     │      │     ●            ●           │    ○   │   │● │  right hand
     │      │   left    ·    right         │        │   │● │  left hand
     │      │        (camera)              │        │   ││ │
     │      └──────────────────────────────┘        │   │┴ │  y lo
     │                  performer                   │   │  │
     └──────────────────────────────────────────────┘   └──┘
            inner rectangle: the box's x and z            bracket: the box's y
            ● in the box      ○ tracked, outside it (hollow, dim)
    ```

    The view from above is 174 px wide at a fixed scale (x over
    ±260 mm, z over ±160 mm) and the gauge maps 80–400 mm; a box wider
    than the scale has its faces drawn clamped just inside the frame,
    with an outside hand's ring kept clear of them. With no box there
    is no rectangle and no bracket. The status line shows each hand as
    `●` in the box, `◌` tracked but outside it, `○` not seen; under the
    selected axis's range a line gives the box's three ranges, or "box
    open"; the box view's tooltip says the same.
  - Never seen by a camera: synthetic hands, a hidden-window picture
    (`docs/plans/assets/18-hand-and-knob-feel/box-hands-page.png`) and a
    headless transcript (`box-demo.txt`). Hand checks 72–74.
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
  `.bak-*` already there), and stderr names each backup. The first
  launch of plan 15's build rewrites `bindings.json` once more, the same
  way (`remap_factory`, ARCHITECTURE §3.8): the crossfader's old factory
  row becomes the master dim's, and rows are added for OVERDUB, the
  clip-stop row, Home and the four undo keys wherever the control
  or chord is free; a row you changed is left as you had it. A row of
  these that you delete from the file comes back on the next launch; to
  switch one off, keep it with `"enabled": false`. Since plan 16 the
  home also holds `windows.json`, where the two windows were at the last
  quit (§2.5): machine-specific, like `last_show`, and safe to delete.
  Since plan 18, `hands.json` (the hands' calibrated ranges) also holds
  the interaction box and is schema 2; launching does not rewrite an
  older one, and the first sweep or "reset ranges" that does keeps it
  beside itself as `hands.json.bak-v1`. A show now also saves
  `desk.slew` (knob smoothing) and `hands.learn_depth` with its session
  values.
- **The trash** (plan 15 WP1; `library.to_trash`). The home's layout
  gains `trash/<group>/<slug>.<YYYYMMDD-HHMMSS>.json`: a **user** preset
  file as it was, copied there before a save overwrites it or a delete
  removes it — the preset strip's save and as…, ⇧F1–F8, a module
  strip's save, the list's × (`Library.save_as`, `Library.delete`). A
  second copy in the same second gets `-2`, `-3`; the copy is created
  exclusively, so nothing in the trash is ever overwritten. A save
  trashes only when the text on disk differs from what is about to be
  written, so saving twice with no change adds nothing; if the copy
  fails the save goes on and the warning line says the old file was not
  kept. A delete whose copy fails is **refused** (the file stays). To
  get a preset back, copy the file into `<home>/<group>/` under its
  plain name; the file watch lists it within a couple of seconds.
  `trash` is no module group and is never watched; factory files are
  never written, so never trashed; show files and `bindings.json` keep
  their own `.bak-*` backups instead. Nothing empties the trash and no
  page shows it yet (plan 19).
- **The cheat sheet** (`ui.CHEATSHEET`) is the canonical human list of the
  keys; `test_the_cheat_sheet_matches_the_tables_and_the_loop_keys` parses
  its key column against `routing.keymap()`, `padmap()` and the keys the
  loop still handles itself (`app.LOOP_KEYS`). It is **off at every
  launch** (plan 16 WP1): `/`, the pad's MENU and the APC40's DETAIL
  toggle it (`ui.cheatsheet`; DETAIL's LED is dark until then), the
  SYSTEM page's checkbox says so in its hover, and it is not remembered.
  The desk diagram stays on and is already in its place on the first
  frame the sheet shows
  (`tests/test_ui_shell.py::test_the_cheat_sheet_is_off_at_launch_and_the_desk_is_on`,
  `::test_slash_still_toggles_the_cheat_sheet`,
  `tests/test_ui_desk.py::test_the_desk_does_not_jump_when_the_sheet_comes_up`).
- **The keys plan 15 added**, all table rows (`routing.LOOP_KEY_ROWS`),
  so they rebind in `bindings.json` like any other: **⌘Z** and
  **Ctrl+Z** undo, **⌘⇧Z** and **Ctrl+⇧Z** redo (§5b), **Home** (fn ←
  on a laptop) loads the show's "starts on" preset. `CONTROL` is a third
  modifier a key row may name, beside `SHIFT` and `SUPER`. **A press
  fires only its own chord**: a row fires when its modifiers are exactly
  the held ones that some row on that key names, so ⌘⇧Z redoes and does
  not also undo, and a modifier no row on the key names is ignored.
  (Until plan 15 a modified row fired whenever its modifiers were among
  those held. A hand-made bare `key:Z` row therefore no longer fires
  with ⇧, ⌘ or Ctrl held.) From the control window, a key pressed while
  imgui is typing is the text field's own.
- **The footer** (`Panel._footer`), on every page: the frame rate; one
  **message slot**; `dim 40%` (or `dim black`) in the warning colour
  while the master dim is under full, so a dark picture is never a
  mystery; the show's name and dirty mark, flush right. Since plan 17
  the slot also carries the learn: what the last learn or unbind did
  ("unbound view.speed from K2 (track knob 2) and R height pushes
  +0.45"), a refusal in the warning colour, each for the same 4 s; and
  when nothing newer is up, **an armed learn's line in red** — "learning
  camera.zoom — move the left hand… (click to cancel)", a click on it
  cancels — or **a picked desk control's** — "D3 picked (20 s): click a
  param to put it here (click to let go)", a click on it lets go. The
  words in brackets are on the line where they fit and on its hover
  otherwise; the desk learn's hint is cut at the control size ("turn a
  knob or press a button on th…")
  (`tests/test_ui_shell.py::test_the_footer_says_what_a_learn_waits_for_and_what_it_did`,
  `::test_the_footer_says_what_is_picked_and_a_click_lets_go`). The message
  slot (plan 15 WP1; `Panel._message`) shows the newest of its lines
  for 4 s after it changes (`ui.MESSAGE_S`): the undo's status ("undid
  Brightness 2.00× → 2.96×", "redid load FACES", "nothing to undo"),
  the library's status ("show: party starts on TUMBLE", "saved TRIP 2 →
  F6", "F6: cleared — ACID is still in the preset list") and the
  library's warning (in the warning colour: an empty F-key's note, home
  with no "starts on", "saved TRIP 3 — the bank is full: it is in the
  preset list") — so none of them needs the PRESETS page open. It is cut
  with an ellipsis to the room left of the show's name, the whole line
  on hover; while it shows, the hot reloader's status gives way to it.
  The undo's line shows on every press. A library line shows when its
  text changes, **or** when it was set through `Library.say`, which
  counts each call (`Library.said`). Since plan 16 WP7 every line that
  reports something that just happened is set through `say` — the
  bank's lines, an empty F-key's note, home with no "starts on", a slot
  naming no file, a load, a save — so the same press giving the same
  words shows them again. A plain assignment of the line is only for
  clearing it and is not counted, so nothing that assigned the same
  words every frame could hold the slot open (no site does). One line
  is said only when it changes: the band scene landed by `scene.select`
  (`Library.adopt`), which a knob sets many times in one turn. A launch
  says nothing
  (`tests/test_ui_shell.py::test_the_footer_says_what_was_undone`,
  `::test_the_dim_is_first_on_output_and_the_footer_says_so_while_dimmed`,
  `tests/test_ui_presets.py::test_the_footer_says_a_library_line_again`,
  `::test_a_line_said_twice_shows_twice`,
  `::test_a_line_assigned_every_frame_does_not_pin_the_footer`).
- The large cell-count readout at the top of the view page is still the
  signature element. Keep new UI consistent with this.

## 5b. Undo

Plan 15 WP1, decision 26 (`undo.py`; where it sits in the frame and the
control model is ARCHITECTURE §2 and §3.2). ⌘Z or Ctrl+Z takes back the
last step; with ⇧, redoes it. The footer says what it did.

**What a step is.** One *gesture* — a slider drag, a knob turn on the
desk, a typed value, a toggle, a key or pad press that sets something, a
mouse orbit, a field edited on the ROUTING page — or one *replacing
action*: a preset load by any road (F-key, the clip row, QUANT, the
pad's B, the strip, the file watch), a show load or a new show, home, a
module preset load or reset, a Learn landing, an Unbind, a route's or
desk row's or macro subscriber's ×, Replace in the Replace / Keep
prompt. Nothing tells undo that a parameter was written: once a frame
`Undo.tick` compares a fingerprint of what the user sets with last
frame's. A change opens a step holding the state as it was; the step
stays open while changes keep coming and closes after **0.4 s of quiet**
(`SETTLE_S`), named from what differs ("Brightness 2.00× → 2.96×", "3
view settings", "routes", "5 changes"). A replacing action calls
`undo.push(label)` before it changes anything, so its step is named by
the caller ("load TRIP", "learn view.bright", "home → TUMBLE") and what
the action then changes over the next frames joins that one step. The
stack keeps 100 steps (`LIMIT`); a launch starts with none.

The settle time is the only boundary. A slider moved within 0.4 s of a
load joins the load's step. A drag held still for more than 0.4 s with
the mouse down and then moved again is two steps (decision register row
43). Plan 18's knob slew must stay under it.

**What is watched.** The **base** of every param that is persisted, not
an alias, not a trigger and not in the `tempo` group (455 of the 532
params on the party show), and the loaded preset's part of the table:
the performer rows, the desk's preset layer and the macros. So the
performance params, and the session ones too — the hands' feel, the band
strips, the master faders, `scene.select`, the ghost hands, the
overlay's ground and opacity — and the camera (an orbit or R is a step).

**What is left out.** A performer: a hand, a band or an LFO writes an
offset, never the base, so it makes no step however long it plays; the
frame it takes or leaves a param the base can move in its last bits, and
floats within 1e-9 relative are the same value. The rotation phases
(`rot.phase.*`, integrated every frame). The clock: `tempo.bpm` and
`tempo.nudge`, so a tap or a typed BPM is not undone, and undoing a show
load leaves the tempo where it is. Every trigger. Selections and the
panel's own state (`band.select`, `fx.select`, `preset.select`,
`desk.shift`, `ui.*`), transport (`audio.mic` / `device` / `play`), and
the rig's output settings — monitor, fullscreen, overlay, passthrough
and the **master dim**. The session's rows of the table (keys, pad,
invariant and global-layer MIDI rows), which are `bindings.json`'s. A
band added, removed or moved: it is not a step, and it re-declares every
`band.*` param, so a strip's values are put back only onto the band
layout they were taken on — with another layout up the rest of the step
lands and the footer adds "(the bands have changed: their strips were
left)". The 8-second "Reset all" undo on the band strips is unchanged
beside all this.

**What a restore does and does not touch.** It puts back only what
differs between the step and now: each differing base through
`Registry.restore` (which ends in `Param.set`), and the routes, the
preset layer or the macros through the table's own calls, each only if
it differs. Undoing one slider sets one param: no load runs, the desk
layer that is up stays up, the faders keep their catch, the LFOs keep
their phase. A desk row an undo brings back picks up afresh; one that
never left keeps its catch. A step pushed as a load also puts back what
the library calls loaded — every group's name and clean reference, the
band layout (first, so the strips' params exist before their values
land), the loaded preset's notes — so after undoing a load the PRESETS
page names the earlier preset and **save** writes that one, not the
later file. Undoing a show load puts the show's own fields back.
Otherwise the bank and "starts on" are left alone: they are written to
the show's file the moment they change. A restore writes **no file**,
and the dirty dots follow honestly, since they compare the live state
with the loaded reference. A save or a delete is not a step: its net is
the trash (§5). Redo is the mirror; a new gesture clears it at once, an
action when it has actually changed something (a refused unbind or a
failed load does not cost the redo). An edit made in the two frames
after a restore is absorbed into it.

**The cost.** `Undo.tick` runs every frame, after the scene-setters and
before the hands. Measured headless by `tools/undo_demo.py` on the party
show (532 params, 20 routes, 42 desk rows), on a laptop: **about 80 µs
median per frame** (idle: median 81 µs, 99th percentile 136 µs, max
305 µs over 1200 frames; during a drag: median 79 µs), against a 16.7 ms
frame at 60 Hz. A raise inside undo never fails a load or a frame: it is
printed and shown on the status line.

Shown by `tests/test_undo.py` (twenty-seven tests, one of them the real
`app.frame` over a real host for some 2,500 frames with hands, audio and the
renderer running: the stack ends as the eight loads it made and nothing
else), by `tools/undo_demo.py` (`docs/plans/assets/15-safety-net/undo-demo.txt`)
and by a scripted launch of the app on a laptop. Not yet by a person at
the keys: hand checks 48–52.

## 6. Testing

`uv run pytest` — 1121 tests and 1 skipped (the hands tape, until one is
recorded) on `plan-15-integration` with plan 15 whole, about 70 s; 1276
and the same 1 skipped on `plan-18-integration` (plans 16, 17 and 18),
about 85 s. `ruff`
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
- **The safety net** (plan 15): undo — one step per gesture and per
  action, a performer making none, a restore setting only what differs,
  the marks, the band-layout tag, an idle app making no step
  (`tests/test_undo.py`), its push sites (`test_learn.py`,
  `test_midi.py`, `test_ui_routing.py`, `test_desk.py`), the chord rule
  and the keys added to an older file (`test_routing.py`), the footer's
  line (`test_ui_shell.py`); the trash (`tests/test_library.py`, the five
  `trash` tests); home (`test_presets.py` `test_home_*`,
  `test_desk.py::test_overdub_is_home_on_both_layers_and_is_lit`); the
  master dim — the pass (`test_render.py`, the `dim` tests), the param
  (`test_overlay.py::test_dim_is_a_rig_setting_that_starts_bright`),
  the crossfader's pickup and its hold through a load (`test_midi.py`,
  `test_desk.py`); save-as on the desk — the hold on a fake clock, a tap,
  the bar as one control, the velocities sent and when (`test_midi.py`,
  the four `hold` / `tap` / `bar` tests), the row invariant
  (`test_desk.py::test_the_clip_stop_row_is_invariant`), the name and
  the bank (`test_library.py::test_next_name_counts_on_from_a_trailing_number`,
  `test_presets.py` `test_save_new_*`, `::test_put_and_clear_slot_write_the_show_and_delete_no_file`),
  the slot menu through real imgui mouse events
  (`test_ui_presets.py::test_a_slots_menu_offers_put_and_clear`). Every test also runs with no `Undo` left installed
  by the one before it (`tests/conftest.py`), and `HYPERSPACE_HOME` is
  set in `os.environ` itself, so a test that calls `monkeypatch.undo()`
  cannot fall back to the real home.
- **Learn, Unbind and the desk** (plan 17): what a learn accepts, the
  one road onto the desk, the refusals that leave it armed, Unbind by
  kind and as one step, pick-then-param (`tests/test_learn.py`); one
  hand, a fresh baseline on a re-arm, no hand on a desk learn
  (`tests/test_hands.py`); a knob through a hand learn and the invariant
  controls through a desk learn (`tests/test_midi.py`,
  `tests/test_desk.py::test_the_clip_stop_row_is_invariant`); the menu's
  lines and items, the label and the meters, the footer's learn and pick
  lines, the dimmed page and the click on a param
  (`tests/test_ui_shell.py`); the desk's room, labels, click and timeout
  (`tests/test_ui_desk.py`); the filter and `goto`
  (`tests/test_ui_routing.py`). Where these click, right-click or type,
  the event is fed to imgui by the test at the rect the item was drawn
  at; no test moves a real mouse.
- **Boundaries**: the core never imports `midi` / `bridge` / `dream`
  (`tests/test_params.py:286`, `tests/test_bridge.py:381`,
  `tests/test_dream.py:55`); `hands/core.py`, `hands/signal.py`, `lfo.py`,
  `tempo.py` and `undo.py`
  (`tests/test_undo.py::test_undo_imports_nothing_from_the_package`)
  import nothing from the package, and `routing.py` nothing
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
- **Plan 15 at the machine**: undo, the trash, home, the master dim and
  save-as on the desk have been shown by tests, offscreen renders and
  scripted launches on a laptop, and by nobody at the rig. Group K of
  the hand checks (48–57), 57 first: it is the launch that rewrites
  `bindings.json`. The decisions the unattended run took on its own
  recommendation wait in `DECISION-REGISTER.md` rows 34–44.
- **Plan 16 at the machine**: the cheat sheet off at launch, the FX
  chips and the idle strip, window placement, instances to zero and the
  dream's layer have been shown by tests, pictures from a hidden window
  or an offscreen render, and scripted launches on a one-screen laptop,
  and by nobody at the rig. Group L of the hand checks (58–63); check 61
  is the first time window placement meets a second screen. Rows 45–49
  of `DECISION-REGISTER.md` wait the same way as 34–44.
- **Plan 17 at the machine**: one Unbind, Learn desk / hand, the menu
  on labels and meters, the big clickable desk and the ROUTING filter
  have been shown by tests with fed mouse and keyboard events, pictures
  from a hidden window and scripted launches on a laptop. Nobody has
  clicked, right-clicked or typed in the real control window, no APC40
  has been learned onto or mapped by a click, and no real hand has
  completed a hand learn. Group M of the hand checks (64–71, after check
  72). Rows 57–64 of `DECISION-REGISTER.md` wait the same way.
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
