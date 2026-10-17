# Hyperspace — the manual

How to run, configure, operate and change the Python app. Structure — the
parts, the frame, the control model and who may write a parameter — is
[`ARCHITECTURE.md`](ARCHITECTURE.md); the reasons behind the choices are
[`DECISIONS.md`](DECISIONS.md) and [`DECISION-REGISTER.md`](DECISION-REGISTER.md);
setting up a new Mac is [`SETUP.md`](SETUP.md); what a person still has to
check by hand is [`TESTING-GUIDE.md`](TESTING-GUIDE.md) and
[`plans/11-hand-checks.md`](plans/11-hand-checks.md).

Contents: 1 Geometry · 2 Rendering · 3 Running it · 4 The home folder ·
5 `config.toml` · 6 The control window · 7 Keys and the gamepad · 8 The
APC40 · 9 Learn, Unbind and routing · 10 Presets, shows and the bank ·
11 Undo · 12 Hands · 13 Audio · 14 Outputs · 15 Hot reload and the
watchdog · 16 Testing · 17 Known limits.

---

## 1. Geometry

**Shapes** (`geometry.py`). The slider index is the identity saved files
and the golden traces use, so the list is append-only and the vertex
order of the first eighteen never changes. `tests/test_golden.py` reads
this table and checks every V and E against the code, so keep it in this
form under this heading.

| # | Shape | Cells | V | E |
|---|---|---|---|---|
| 1 | 5-cell | 5 | 5 | 10 |
| 2 | 3,3-duoprism | 6 | 9 | 18 |
| 3 | Cubic pyramid | 7 | 9 | 20 |
| 4 | Tesseract | 8 | 16 | 32 |
| 5 | Rectified 5-cell | 10 | 10 | 30 |
| 6 | 4,8-duoprism | 12 | 32 | 64 |
| 7 | 6,6-duoprism | 12 | 36 | 72 |
| 8 | 16-cell | 16 | 8 | 24 |
| 9 | 10,10-duoprism | 20 | 100 | 200 |
| 10 | Icosahedral prism | 22 | 24 | 72 |
| 11 | 24-cell | 24 | 24 | 96 |
| 12 | Truncated tesseract | 24 | 64 | 128 |
| 13 | 12,12-duoprism | 24 | 144 | 288 |
| 14 | Dodecahedral prism | 32 | 40 | 80 |
| 15 | 20,20-duoprism | 40 | 400 | 800 |
| 16 | 120-cell | 120 | 600 | 1200 |
| 17 | 600-cell | 600 | 120 | 720 |
| 18 | Clifford torus (32×16) | — | 512 | 1024 |
| 19 | Heart | — | 128 | 192 |
| 20 | Star | — | 20 | 30 |
| 21 | Rose | — | 186 | 285 |
| 22 | Torus | — | 512 | 1024 |
| 23 | Trefoil knot | — | 576 | 1152 |
| 24 | Starfruit | — | 522 | 1080 |
| 25 | Möbius strip | — | 320 | 576 |
| 26 | Klein bottle | — | 576 | 1152 |

Cells "—" (`Shape.cells == 0`) marks a surface, not a polytope. It does
not mean 3D: the Clifford torus (18) is a surface native to 4D. Shapes
19–26 are surfaces from trig equations, each built with its own face
cycles.

**How a shape fills the fourth dimension** (`Shape.w`, one of
`geometry.W_KINDS`; any other value raises):

| `Shape.w` | Means | Shapes |
|---|---|---|
| `native` | built with real w-extent: a 4-polytope or a 4D surface | 1–18 |
| `lift` | a 3D surface given w-extent by a lift of its own parameters | Star, Rose, Torus, Trefoil knot, Starfruit, Möbius strip, Klein bottle |
| `mask` | a 3D shape kept at w = 0, its W planes folded onto 3D planes where it is drawn | Heart |
| `flat` | a 3D shape at w = 0 with nothing done: a quarter turn of XW, YW or ZW carries a whole axis into w, the 4D→3D divide drops it, and the shape draws as a plane | none (the tests use it to show the collapse) |

A surface built without a lift sits at w = 0; that is what shapes 19–25
were before plan 22, and why they went flat whenever the bass bands
turned a W plane.

**A lift** is a function of the builder's own parameters, passed as
`w=`; each builder hands it to `_mesh3`, which takes 3- or 4-tuples and
merges coincident points on every coordinate given. Without a lift every
shape is what it was, vertex for vertex
(`tests/golden/shape_digests.json`).

| Builder | The lift it takes |
|---|---|
| `param_surface` | `w(u, v)`; or `fn` returns (x, y, z, w) itself |
| `spherical_surface` | `w(θ, φ)`, φ from the +y pole |
| `ring_prism`, `curve_prism`, `polar_prism` | `w(t, z)` or `w(θ, z)`: t the outline's parameter, z = ±depth/2 the cap |
| `tube` | `w(t, a)`: t along the curve, a = 2π·j/m round the tube |

The rules a lift follows (the comment above `geometry._build_heart`):

- **No linear part of x, y or z.** w = a·x only tilts the shape into
  another flat 3-space, which some W turn still flattens.
- **Odd under each mirror of the shape that flips one axis.** At a
  quarter turn of a W plane, w takes that axis's place; a lift that is
  the same on both sides folds the halves onto each other into a sheet,
  which neither measure below sees.
- **An extruded outline's lift depends on z**, or every wall goes
  edge-on at once when ZW turns z away.
- **It agrees wherever the surface welds**: poles (w independent of θ
  there), the Rose's pinch, the Möbius seam (w(2π, 1 − v) = w(0, v)). A
  lift that disagrees leaves the seam open.
- A lift cannot make a shape fatter than its own 3D proportions, since at
  rest the divide drops w; a shape too thin for the floor must change
  size (the Rose went 0.12 → 0.16 deep, the Möbius band 0.45 → 0.55
  wide).

| Shape | `Shape.w` | Lift |
|---|---|---|
| Heart | mask | — |
| Star | lift | 0.6·(z/h)·sin t, h = 0.175: the caps tip opposite ways |
| Rose | lift | z·(3 sin 4θ + sin 8θ): 0 where the petals meet |
| Torus | lift | 0.7·sin v·sin 2u |
| Trefoil knot | lift | 1.5·cos 3t |
| Starfruit | lift | 0.6·sin 2φ·sin 2θ: 0 at the poles |
| Möbius strip | lift | 0.5·sin 2u: 0 at the seam |
| Klein bottle | lift | sin 2u + ½·sin v·cos 2u |

**A mask** keeps the shape 3D. `geometry.view_angles(i, ang)` returns
`ang` itself for every shape that is not masked; for a masked one, a new
list with each W angle added onto a 3D plane (`W_REMAP`: XW → XZ,
YW → YZ, ZW → XY) and the W planes at 0. `Renderer.draw_scene` draws
through it and is its one call site; nothing writes the result back, so
`ViewState.ang`, the integrator and every `rot.*` param are untouched
and a rate or a phase route on a W plane lands on the 3D plane alike.
With the factory band map (SUB → ZW, BASS → XW, MIDB → YW) SUB rolls a
masked shape in the screen plane, BASS spins it about y and MIDB tumbles
it about x. Its depth cue (`pd`: the line fade, width and draw order)
reads its depth toward the 3D camera — `geometry.view_depth`, z after
the camera's yaw and pitch, the depth the 3D divide reads — since its w
is 0 at every angle. The VIEW page and
`rot.phase.*` still show the W planes turning.

**The volume measures.** `project3(V, ang)` is the rotated, divided 3D
cloud the camera views. `volume_ratio(P)` is its smallest singular value
over its largest, centred: 1 a ball, 0 a plane or a line.
`sweep_ratios(i, plane, steps=72, pose=None)` measures it round one full
turn of one plane, the others at `pose`, through `view_angles` as the
renderer draws. `edge_on_share` is the share of face area drawn at under
a tenth of its 4D area, and `sweep_edge_on` its sweep: a cloud can keep
its volume while its faces still read as a sheet.

**`VOLUME_FLOOR = 0.15`.** Every lifted or masked shape keeps at least
this ratio through a full turn of each W plane, from rest and from
`GENERIC_POSE`, and turns at most 0.15 of its face area edge-on
(`tests/test_shapes4d.py::test_a_lifted_or_masked_shape_keeps_its_volume_through_each_w_plane`,
`::test_a_lifted_or_masked_shape_never_turns_much_of_itself_edge_on`).
It is calibrated on the 18 native shapes, which already draw as volumes:
their worst ratios through the W planes are cubic pyramid 0.30,
4,8-duoprism 0.53, dodecahedral prism 0.64, 5-cell 0.65, tesseract 0.94,
Clifford torus 0.97, 24-cell, 120-cell and 600-cell 1.00 (single-plane
sweeps reach the same worst case as 2000 random poses of all six
planes). The floor is half the cubic pyramid's, so no surface is asked
to be rounder than a polytope is; every native shape clears it
(`::test_every_4d_shape_clears_the_volume_floor`). A flat shape reads
0.000 at 90° and 270°.

**The turntable** (`tools/turntable.py`) is the same sweep with
pictures:

```bash
uv run python tools/turntable.py --prefix after              # every shape, numbers and sheets
uv run python tools/turntable.py --prefix check --shapes 18-25 --no-png
```

It writes `<prefix>-ratios.json` / `.csv` (per shape, plane and pass:
the minimum ratio and its angle, the maximum edge-on share and its
angle) and one sheet per shape — rows XW, YW, ZW, `--frames` tiles
(12) across a turn, drawn offscreen by the real renderer, each tile
labelled with its angle and ratio, red under the floor — into
`docs/plans/assets/22-flat-shapes/`. A run overwrites files of the same
prefix there. `--shapes` takes indices (`18-24`, `17,21`); `--steps`
the sweep's resolution (72 = 5°).

**Faces on a lifted shape.** The grids' quads stay quads; a lift bends
them slightly out of plane, which `_face_xy` already framed
best-effort. A cap — the Star's two pentagram faces, which its lift
bends through w — is a polygon of more than four corners that is not
planar, and `_face_xy` frames it by its least-squares plane, where the
outline stays simple and the ear clip tiles it exactly; every planar
face keeps the basis it had
(`tests/test_shapes4d.py::test_a_lifted_cap_is_triangulated_over_its_own_outline`).

**The Klein bottle** (26). `_klein_xyz(u, v)` is the classic "bottle"
immersion, u ∈ [0, π], v ∈ [0, 2π): the body swells up from the base,
the neck curls over and comes back down through the body's side, where
in 3D the surface must cross itself. The lift sin 2u + ½·sin v·cos 2u
holds the two crossing sheets (the body at u ≈ 0.49, the neck at
u ≈ 2.56) at least 1.56 apart in w, so in 4D it never crosses; the
½·sin v·cos 2u term is odd in v, so the z-mirror cannot fold it at a
quarter turn of ZW. The seam u = π meets u = 0 with v flipped to π − v,
where the lift agrees, and welds by `kkey` like the Möbius strip's: 37 ×
16 samples, 36 × 16 vertices, 576 quads, every edge on two faces,
V − E + F = 0. It is centred on its bounding box
(`tests/test_shapes3d.py::test_the_klein_bottle_seam_welds_into_a_closed_grid`,
`::test_the_klein_bottle_crosses_itself_in_3d_and_not_in_4d`). Its own
3D ratio is 0.23; through the W planes it keeps 0.20.

**A new shape** goes at the end of `SHAPES` (the index is its identity),
says how it fills w, and gets a row in the V/E table above. A 3D shape is
`lift` or `mask`, never `flat`: the acceptance tests take it in through
`Shape.w`. Record its digest with `uv run python tests/test_shapes4d.py
--record`, and say so in the commit; a polytope's digest must never
move.

## 2. Rendering

**The transform**: rotate in 4D across six planes → project 4D→3D →
apply the drag orientation → project to 2D, on the CPU; the GPU
rasterises. Edges are screen-space quads whose width and alpha follow
w-depth (the near half glows), with brightness compensated for edge
count so the 120-cell does not clip to a blob. Points are red.

**Faces** are the true 2-faces, translucent and painter-sorted, with
face-local UVs. `shaders/patterns.glsl` paints them: `vec4 pattern(int
mode, vec2 uv, float fid)` (`.rgb` the colour, `.a` the intensity; `uv`
face-local, (0.5, 0.5) the centre, circumradius 0.5; `fid` the face's
index). Seventeen patterns (`view.pattern`, `params.PATTERNS` =
`patterns.NAMES`): FLAT, RINGS, PLAID, MOIRE, BLOOM, CAUSTIC, HEX,
SPIRAL, CELLS, PLASMA, WEAVE, EMBER, METER, PULSE, MARBLE, TRUCHET,
KALEIDO. Shared colour helpers (`hsv`, `pal`, `hue_rotate`, `luma`, `TAU`,
`PI`) are `shaders/_common.glsl`, prepended. Both files hot-reload on
save; a broken edit keeps the last good program and shows the GLSL error
on the FACES page. The **bitmap** layer textures faces from a file; a bad
file leaves the plain faces. **Cut-through** matters only in overlay
mode.

**The eight pattern inputs** are `pattern.mod.0`–`.7`, the shader's
`u_mod[8]`: range 0–2.6, **1.0 the pattern as designed**. Each means one
kind of change on every pattern, so a route that feels right on one
reads the same on the next:

| k | Input | Registry label | 0 | 1 | 2.6 | Shader | Factory source |
|---|---|---|---|---|---|---|---|
| 0 | SCALE | Pattern scale | small and many (0.59×) | as designed | big and few (2.3×) | `k_size()` | SUB |
| 1 | GLOW | Pattern glow | dim (0.3× light) | as designed | white-hot (2.4×) | `finish()` | BASS |
| 2 | WARP | Pattern warp | straight | as designed | heavily warped | `warp(p, own)` | MIDB |
| 3 | SPEED | Pattern speed | frozen | as designed | 2.6× as fast | `u_ptime` (the renderer's) | MID |
| 4 | COLOUR | Pattern colour | grey | as designed | more hues, stronger | `finish()`, `spread_hue()` | UPR |
| 5 | SHARP | Pattern sharp | soft and broad | as designed | thin and crisp | `sharpen()`, `k_edge()` | AIR |
| 6 | HUE | Pattern hue | half a turn back | as designed | four fifths of a turn on | `finish()` | — (an LFO) |
| 7 | SPREAD | Pattern spread | every face in unison | as designed | each face its own phase and colour | `face_rad`, `face_turn`, `face_gold`, `face_k1` | — (a macro or knob) |

The order is for the factory routes, lane *i* → input *i*: the sub
swells, the kick flashes, the low mids bend, the mids set the pace, the
upper mids flare the colour, the air sharpens. A straight design stays
straight from WARP 0 to 1 and bends above 1; a design whose faces play
in unison stays in step from SPREAD 0 to 1 and parts above. GLOW keeps
30% of the light at 0. BLOOM has seven petals, SPIRAL five arms and
KALEIDO six wedges, whatever the inputs. FLAT reads none.

- **`hyperspace/patterns.py`** is where the convention lives, as data,
  importing nothing: `INPUTS` (`name`, `meaning`, `why`), the index
  constants `SCALE` … `SPREAD`, `MODES` (`name`, `about`, and `does`: what
  each input does in that mode in a few words, `""` where it reads none),
  `NAMES`, `effect(mode, k)`, `ignores(mode)`, `label(k)` and `tip(k)`.
  `params` takes the mode names and each input's label and tip from it;
  the FACES page takes the per-mode phrases (29 characters at most, so
  each fits a row).
- **In the shader** a mode reads its inputs only through the accessors
  `m_scale()` … `m_spread()` and the helpers on them; GLOW, HUE and
  COLOUR's grey end are one `finish()` over every mode, each term the
  identity at 1.0. Mode bodies are in `design()` or a function of their
  own (`meter`, `pulse`, …); `pattern()` is `finish(design(...))`.
- **`u_ptime`** is the patterns' clock: the renderer integrates wall
  seconds × SPEED (`Renderer._pattern_clock`), once per frame, so a
  moving SPEED changes the rate and never jumps the phase. `u_time`
  (seconds since launch) is still uploaded; no mode reads it.
- **`u_levels[8]`, `u_nlevels`** are the analyzer's lanes, out / CEIL
  (0–1, low band first), and how many there are (0 with no audio): the
  app sets `Renderer.bands` each frame (`app._bands`). Read them through
  `band(i)`, an if-chain, never `u_levels[i]` (a constant index on every
  compiler). Only METER and PULSE do; every other mode is moved by the
  music only through its routed inputs.
- **A new mode** is a case in `design()` (or a function of its own) that
  reads the inputs only through the accessors and helpers, **plus** a
  `Mode` entry at the end of `patterns.MODES` — appended, never inserted,
  since a preset holds the mode as an index — with its one line and
  eight phrases. The tests hold the shader's cases, accessors and header
  to the table.
- **Checking the shader.** `uv run python tools/check_glsl.py` compiles
  the face, seed and tile shaders exactly as `render.py` assembles them
  with the Khronos reference compiler, `glslangValidator` (on the PATH;
  `glslang-tools` on Debian), which holds `#version 330` to the letter.
  It is an extra net: Mesa (the tests' driver) and glslang are both more
  lenient than Apple's GL in places, so only a launch on the Mac proves
  a mode compiles there.
- **The factory depth.** The factory lane → pattern routes push at
  `routing.PATTERN_DEPTH` = 0.35 on a base of 1, so an input rises by
  0.35 × the band's out: about 1.1 for a quiet band, 1.35 at nominal,
  about 1.86 on a kick; at depth 1 a loud band pinned its input at 2.6.
- **Pictures.** `tools/pattern_sheet.py` draws a sheet per mode
  (`mode-NN-*`), a sheet per input across every mode (`input-K-*`) and the
  old modes (`before-NN-*`) into `docs/plans/assets/22-face-patterns/`;
  `tools/pattern_cost.py` times every mode offscreen against FLAT
  (`b3-cost.txt`; software GL: ratios only — MARBLE is the dearest,
  4.19× FLAT on the 600-cell); `tools/faces_page_shots.py` shoots the
  FACES page from a hidden real window. `Renderer.pattern_tile(s, size,
  t_now, fid)` renders one face's pattern alone, for tools and tests.

**Instances** (`view.instances`, 0–100): copies laid out by
`view.inst_layout` — **GRID** (rows of ⌈√n⌉), **HEX** (a honeycomb
spiral from the centre; a copy never moves as the count grows), **RING**
(one circle, neighbours one cell apart) — and moved by
`view.inst_motion` (STILL, ORBIT, WAVE, RIPPLE) with `inst_amp` and
`inst_rate`. At 0 nothing is drawn but the ground, the echoes, the
effects and the hands carry on.

**The frame** (`render.py`, `Renderer.draw_outputs`), once per frame:
the face picture (only while an effect is aimed at the faces) → the
scene → the coverage mask (when the look-back occludes) → the look-back
composite → the frame's effects → the hands → the master dim; then each
render output gets its picture (§14). With the look-back, effects and
ghost off and the dim at full, the output is bit-identical to the scene
pass alone. The renderer re-binds its target on every exit, a raise
included, so a failing pass never strands a framebuffer.

**The look-back** (`lookback.py`, LOOKBACK page) keeps an atlas of
downsampled echoes of past frames and one dream buffer, and composites
the scene over its own wake. **ECHOES**: brightness (`dream.echo_mix`),
fade time (`fade`, seconds), count (`echoes`), time apart (`gap`,
seconds), thumbnails, and how far back the trail reaches; echo time is
in seconds, so a trail is the same at 60 and 120 Hz. **DREAM**: the
worker's status, the layer as one menu (every conv layer of VGG16 and
every block of GoogLeNet, 25, grouped by net shallow → deep, each with a
short description and a longer one on hover — `lookback.LAYER_INFO`),
brightness (`mix`), speed (`k`, shown as frames to halve), strength
(`step`), passes (`steps`), linger (`mask_decay`), jitter, scales
(`octaves`), hue, saturation, tint, tint from, tint hue, tint sat, and a
swatch of the tint. **BOTH**: darken, contrast, shape hides (`occlude`),
detail (`res`). The page uses short labels; ROUTING, learn lines and the
desk use the registry's ("Echo time apart", "Dream speed"). All
`dream.*` params are presettable and modulatable except `gap`, `res` and
`layer`.

**The dream worker** (`dream.py`, torch, MPS when available) runs a few
gradient-ascent steps per submitted echo on its own thread; `submit`
never blocks and the latest result wins; `step × steps / k` is clamped so
a preset cannot run away. The weights (one file per net, VGG16 528 MB or
GoogLeNet 50 MB, whichever net the layer belongs to) are read from
`weights_dir`, then torch's hub cache, and downloaded there on first use.
A net is read once a run: every layer of it is a cut of the same loaded
stack, so a change between layers of one net is instant (the first layer
of a net takes about 1.5 s for VGG16). The deepest layers cost about half
again what conv3_3 does per frame and say "slower" in the menu.
If the worker cannot start, the reason is on the SYSTEM page, the
LOOKBACK page and the red banner, and the look-back runs echoes only; a
preset that asks for the dream with no worker is a warning, once.

**Effects** (`fx.py`, FX page). One GLSL file per effect in
`shaders/fx/` — twelve ship: acid, deconverge, doublevision, fractals,
glimmer, huecycle, kaleido, plasma, tripcolour, warp, wobble, zoomblur
(`_lib.glsl` is shared). **A new effect is a new `.glsl` file, not
Python**: every `// @param` uniform becomes `fx.<file>.<key>`, plus
`on mix speed blend order target` per effect; `fx.on` bypasses the stack
and `fx.mix` scales it. The folder is polled every 30 frames; a parse
error keeps the last version, a compile error skips the pass. Factory
effect presets are `library/fx/*.json`.

- **The page.** Bypass and mix, the chain in words (`frame  Plasma → Hue
  cycle`, and a `faces` row while anything is aimed at the faces), then
  one chip per effect, three to a row, in stack order. A chip's **LED**
  switches the effect; its **name** opens its strip. An open effect
  that is not running says why first ("off", "faces off", "the whole
  stack is bypassed", "FX mix is at 0", "its mix is at 0") with a chip
  to fix it; its controls stay live under a veil. **Drag a chip by its
  name** onto another to put it before that one (or onto the right half
  of the last to move it to the end): one undo step.
- **Aimed at the faces.** Each effect's `fx.<name>.target` is `frame`
  (the default) or `faces`: the **ONTO frame · faces** chips at the
  right end of the open strip's title line, the lit one where it runs
  (not modulatable). The faces are translucent, so an effect on them
  reads faint — the strip says so while it runs there; Brightness lifts
  them. Effects aimed at the faces run first over a 1024²
  picture of what a face shows, and the faces show that picture — per
  face (at each face's own UV, turning with the shape) or screen (one
  still picture seen through the faces), `fx.face_map`. A chip aimed at
  the faces has a diamond LED. With an effect on the faces, every face
  shows face 0's pattern phase; the echoes and the dream carry the
  faces' effects, never the frame's.

## 3. Running it

```bash
cd hyperspace-python
uv sync                 # every dependency, torch for the dream included
uv run hyperspace       # the render window and the control window
```

Two windows open: the **render window** (pure output, for the projector
or the glass; the mouse orbits, ⇧-drag or right-drag pans, scroll zooms
about the cursor) and the **control window** (the panel, the desk
diagram, the cheat sheet). Keys work from both, and from every extra
render output; while a text field in the panel is being typed into, keys
go to the field. More render outputs come from `[[output.screens]]` (§14).

- **Quit:** Esc or Q, or close any window.
- **Restart in place:** Cmd+R or the SYSTEM page's *Restart process*
  (`os.execv`: same PID, same terminal). Every open adapter (MIDI, the
  bridge, the hands, the dream worker) and then the
  audio stream are closed first, best effort, so a broken port never
  blocks an exit.
- **The cheat sheet** (`ui.CHEATSHEET`, the canonical list of keys) is
  off at every launch: `/` (or `?`), the gamepad's MENU or the APC40's
  DETAIL shows it.

Environment variables:

| Variable | Effect |
|---|---|
| `HYPERSPACE_HOME` | The home folder (§4). Default `~/Hyperspace`. |
| `HYPERSPACE_FRAMES` | Run that many frames, then exit (a windowed smoke test). |

Command line:

| Flag | Effect |
|---|---|
| `--venue <name>` | Lay `<library>/venues/<name>.toml` over `config.toml`, and remember it (§5). |

A screen is named or numbered: `monitor` takes a case-blind piece of a screen's name (`"MStar"` finds `MStar Demo`), an index (the primary is 0), or −1 for wherever that window was last. Names travel between machines; indices do not (decision 111).
| `--no-venue` | `config.toml` alone, and forget the remembered venue. |
| `PYGLFW_LIBRARY` | Which GLFW dylib to load; `app.py` sets it to the bundled one when unset. |
| `LEAPSDK_INSTALL_LOCATION` | Read by Ultraleap's `leap` package when the hand-tracking software is not at its default path (see SETUP). |

## 4. The home folder

Everything the app writes lives in two places that are one folder unless
you say otherwise: the **home**, `$HYPERSPACE_HOME` (default
`~/Hyperspace`), created on the first launch, holds this machine's own
files; the **library** holds the presets and shows. The library is the
home too, unless `[library] path` in `config.toml` points it at another
folder — typically a cloud-synced one shared with someone (see "The
shared library" below). Factory files ship read-only in
`hyperspace/library/` in the same tree; a user file of the same name
shadows the factory one. All formats are plain JSON with a `schema`
string, and the library is watched: edit a file in an editor (or let a
cloud client sync one in) while the app runs and the loaded preset or show
follows within a couple of seconds. In code, `Library.home` is the library
root and `Library.machine` the home.

**The library** (`Library.home`):

| Path | What it is | Format |
|---|---|---|
| `presets/<slug>.json` | Your presets (§10). | `hyperspace.preset/2` |
| `projects/<slug>.hyp.json` | Your shows (the code calls them projects). | `hyperspace.project/2` |
| `<group>/<slug>.json` | Module presets, one registry group each (`band/`, `dream/`, `fx/`, `hands/`, `view/` …). | `hyperspace.preset/1` |
| `hidden.json` | Factory presets taken off the preset list. | `hyperspace.hidden/1` |
| `venues/<name>.toml` | One place's settings — its screens — laid over `config.toml` by `--venue <name>` (§5). Shared, so two people playing the same place share it. Optional. | TOML |
| `trash/<group>/<slug>.<YYYYMMDD-HHMMSS>.json` | Copies of your files taken before an overwrite, delete or rename. Never watched. | as the original |

**The home** (`Library.machine`; never in a shared folder):

| Path | What it is | Format |
|---|---|---|
| `config.toml` | The rig's settings (§5). Optional. | TOML |
| `last_venue` | One line: the venue the last launch used. Machine state — the venues themselves are shared. Delete it, or `--no-venue`, to go back to `config.toml` alone. | text |
| `bindings.json` | The session's controls only: keys, gamepad, and the APC40's invariant and global-layer rows. Delete it to get `hyperspace/bindings.default.json` back. | `hyperspace.bindings/3` |
| `hands.json` | The hands' calibrated ranges and the interaction box (§12). | `hyperspace.hands/2` |
| `windows.json` | Where the control window and each render output were at the last quit (§14). Machine-specific; safe to delete. | `hyperspace.windows/1` |
| `last_show` | One line: the file name of the show opened last on this machine. | text |
| `stall.log` | The watchdog's log (§15). | text |
| `weights/` | The dream's pretrained network weights, downloaded on first use. | binary |

A `midi_map.json` or `config.toml` left in the working directory from an
old build is copied in on the first run; a `midi_map.json` in the home is
read once, only when `bindings.json` does not exist yet. A `bindings/`
folder of old routing presets is no longer read.

### What the app may rewrite, move or delete

| File | When | Kept first |
|---|---|---|
| `presets/<name>.json`, `<group>/<name>.json` (yours) | A save over it, ⇧F1–F8, × in the preset list, a rename. Never a load. | A copy in `trash/<group>/`. A save goes on if the copy fails (and says so); a × or a rename is refused. A save that writes the same text adds nothing. |
| `projects/<show>.hyp.json` | A bank change, "starts on", save; a rename of a preset it names. Never a load. | The first write that puts a preset past slot 8: `<show>.hyp.json.bak-v2-bank8` (no copy, no write). A rename: a copy in `trash/projects/`. |
| `bindings.json` | At launch, when a newer build adds factory rows (the bank pads, OVERDUB, the clip-stop row, Home, the undo keys) where the control or key is free. A row you changed is left as you had it. | `bindings.json.bak-v<schema>` (`.bak-v3` for today's files; a dated name if that exists, never over any `.bak-*`). No copy, no rewrite: the table runs from memory for the session and the next launch tries again. |
| `hands.json` | A calibration sweep or "reset ranges". A schema-1 file is read as it is and never rewritten at launch. | The first rewrite of a schema-1 file: `hands.json.bak-v1`. |
| `hidden.json` | × on a factory preset; unhide. | An unreadable one is kept as `hidden.json.bak-v0` before it is replaced. |
| Your presets and module presets naming the old per-frame echo keys (`dream.decay`, `dream.every`) | Once, at launch, converted to seconds. | `<file>.bak-v2-frames` |
| A home from before presets existed (schema-1 projects, a `projects/default.hyp.json`) | Once, at launch: converted to presets and shows; `default` is renamed `mine`. | `.bak-v1` / `.bak-v2` beside each rewritten file; stderr names each backup. |
| `<group>/…` | Restore from the trash. | Nothing to keep: a restore never writes over a file — a taken name restores as the next free name. |
| `trash/**` | **Empty trash.** | **Nothing. Emptying the trash is the one action in the app that keeps no copy.** It deletes exactly the files its popup lists, after a second click. |
| `windows.json`, `last_show` | Every quit and Cmd+R / every show load and save as. | Nothing (machine state). |

Every library write is atomic: the text goes to a dot-named temp file
beside the target (never `*.json`) and replaces it in one step, so a cloud
client never syncs a half-written preset.

Factory files are never written, so never trashed. Saving over a factory
preset writes your copy into the home (the save chip says **save copy**).

### The trash

`library.to_trash` copies a file exclusively (a second copy in the same
second gets `-2`, `-3`), so nothing in the trash is ever overwritten.
Restore from the preset list's **trash (n) ▸** popup, or copy a file back
into `<home>/<group>/` under its plain name.

### The shared library

`[library] path` (plan 25) points the library at a folder of its own —
typically one in a cloud drive (Dropbox, iCloud Drive, Google Drive,
Syncthing; the app does not care which) that two people share, so a
preset either of them saves shows up on the other's machine. The machine
files above stay in the home. Unset or `""` is the home, as always.
`tools/move_library.py DEST` copies an existing library into the folder
once (never over a file; `hidden.json` as the union of both lists) and
prints the two lines to add; [SETUP.md](SETUP.md) has the steps.

- **Missing folder.** If the folder is not there at launch (a drive not
  mounted, a typo), the app never creates it and never falls back: a
  warning says so, the SYSTEM page's library line reads "NOT FOUND, saves
  are off" in red, only the factory presets list, and every save, delete,
  rename, hide or restore is refused with "shared library not found at …
  — not saved". Fix the folder or the path and restart.
- **Conflict copies.** When both machines save the same preset while one
  is offline, the cloud client keeps both, e.g.
  `hi-frek (Dan's conflicted copy 2026-10-14).json` with the same name
  inside. The file whose stem is the name's slug keeps the name; the other
  is listed under its file stem. Load both, keep one, delete the other.
- **History.** The cloud service keeps file versions; there is no git in
  the library (the old home-as-git switch and the repo's snapshot
  folder were removed in plan 25 — a `.git` inside a cloud folder is a
  known corruption risk).
- **iCloud / Dropbox.** Mark the folder "Keep Downloaded" / "Available
  offline": an evicted file is invisible to the app.

The macro candidates to audition (plan 22) are in the owner's library;
[`plans/22-macro-candidates.md`](plans/22-macro-candidates.md) says what
each macro is meant to do.

## 5. `config.toml`

Optional, in the home. Every key has a default; `hyperspace/config.py`
(`DEFAULTS`, `SCREEN`) and `hyperspace/hands/core.py` (`DEFAULTS`) are the
source. A file that does not parse keeps the defaults and shows its error
on the SYSTEM page; a value of the wrong kind is its default with a note
on stderr and the SYSTEM page — never a dead launch.

```toml
[midi]                  # the MIDI adapter (midi.py)
enabled = true          # false: no MIDI at all (Learn's menus still work)
# port = "APC40"        # substring of the port name; unset = the profile's ("APC40")
profile = "apc40"       # device profile: hyperspace/apc40.py
map = "midi_map.json"   # an old map, read once when bindings.json does not exist

[output]                # output 1 and the control window
overlay = false         # true allows overlay mode; false: always opaque, T does nothing
monitor = -1            # screen index for the render window (and fullscreen); -1 = where it was last
control_monitor = -1    # screen index for the control window; -1 = where it was last
fullscreen = false
on_start = false        # launch straight into overlay (needs overlay = true)
passthrough = true      # overlay: clicks go to the window underneath
bg = 0.0                # overlay: ground, 0 see-through … 1 black
alpha = 1.0             # overlay: whole-window opacity

[[output.screens]]      # optional; one table per render output, at most 4 (§14)
name = "glass"
monitor = 1
fullscreen = true
scene = true            # launch values of this output's switches
hands = true
through = false
dim = 1.0               # under 0.1 is 0.1, with a note

[gamepad]
enabled = true          # an Xbox-layout pad over GLFW; inert when absent

[bridge]                # the analyzer's lanes out / external lanes in (bridge.py)
enabled = false
out = "IAC"             # port substring for the lanes out ("" = none)
in = ""                 # port substring for lanes in ("" = none); never the bus `out` uses
encoding = "pitch"      # "pitch": lane i → pitch bend on channel+i; "cc14": CC pairs
channel = 0             # 0-based
cc = 16                 # cc14: first MSB controller (0–31)
rate = 100              # messages a second per lane at most (0 = every frame)
send = ["lane:*"]       # "lane:*", "lane:3", "param:<id>", in lane order
in_lanes = 16

[dream]                 # the look-back's dream worker (dream.py, torch)
enabled = true          # false: torch is never imported
device = "auto"         # "auto" (MPS when there, else CPU), "mps", "cpu"
precision = "fp32"      # or "fp16"
weights_dir = ""        # "" = <home>/weights

[hands]                 # Ultraleap hands (hands/)
enabled = false         # true opens the tracker; off, `leap` is never imported
mode = "desktop"        # camera looks up; "screentop" looks down; "hmd"
dofs = ["x", "y", "z", "roll", "pitch", "yaw"]   # per hand; also grab, pinch,
                        # grab_angle, pinch_mm, pinch_index … pinch_pinky
out = "Hyperspace Hands"   # MIDI out for a DAW: port substring, else a new virtual port ("" = none)
channel = 16            # 1-based
cc = 102                # left hand cc…cc+n−1, right cc+n…cc+2n−1
presence = true         # a note on/off as each hand enters / leaves
note = 120              # left hand's presence note; right is note+1
min_confidence = 0.1
calibration = "hands.json"   # relative to the home
pinch_gates = true      # the eight thumb-to-finger switches
pinch_notes = true      # each as a note on/off to the DAW
pinch_note = 100        # left index…pinky = note…note+3, right note+4…note+7
tape = ""               # a recorded hand tape to play instead of the camera

[library]
path = ""               # "" = the home; else the shared library folder (§4)
```

Rules worth knowing:

- An `[overlay]` section is the old name of `[output]`: still read,
  merged under `[output]` (which wins), with a note asking for the rename.
- A `monitor` that is not a number, or an index no connected screen has,
  is −1 with a note (but see §14 for later outputs).
- With an `[[output.screens]]` list, output 1's entry supplies `monitor`
  and `fullscreen`; the scalar ones are ignored with a note. `overlay`,
  `on_start`, `passthrough`, `bg` and `alpha` stay scalar and belong to
  output 1 alone. An unknown key in an entry is a note; entries past the
  fourth are dropped.
- `[library] path` is expanded (`~`) and a relative path is relative to
  the config's folder; anything but text is `""` with a note. A leftover
  `git` key in `[library]` is ignored with a note asking you to remove it.
- `[hands] calibration` and `tape` are relative to the config's folder.

## 6. The control window

The panel is built to be read from a few feet back in a dark room. A
rail of fourteen pages (`ui.PAGES`); the rail shows a red dirty dot
beside a page whose group has moved off its loaded preset. No page
scrolls at the control size (960 × 900, `app.CONTROL_SIZE`;
`tests/test_ui_shell.py::test_every_page_fits_the_control_window`).

| Page | What is on it |
|---|---|
| OUTPUT | The master dim; one block per render output (scene / hands / through ticks, its dim, what it shows in words); the screen and fullscreen of output 1; overlay and its click-through, ground and opacity (greyed, with the reason, unless `[output] overlay = true`). |
| VIEW | The cell-count readout and shape name, the shape, the six rotation planes, points / lines / rotate / faces, brightness, speed, 4D depth, instances (0–100) and, above one copy, the field row: layout, motion, amp, rate; the six plane rates. |
| FACES | Faces, cut-through and the pattern mix; every pattern as a chip with a live swatch; the pattern on show and its line, ‹ ›; the eight pattern inputs by name, each with what it does on this pattern and what drives it (below). |
| BITMAP | A bitmap textured onto the faces: file, opacity, scale, mode. |
| CAMERA | Zoom, yaw, pitch, pan, reset. |
| LOOKBACK | The look-back switch and three sections: ECHOES, DREAM, BOTH (§2). |
| FX | The effect stack (§2). |
| AUDIO | Listen to mic / Load track / Stop, the device and **rescan**, the transport, the master faders (gain, dynamics, trim). |
| ANALYZER | The band scene and Reset all, the meters, the band editor (spectrogram with the bands over it, the selected band's strip). |
| ROUTING | One page over the loaded preset: routes, desk rows, macros, the session's MIDI rows read-only, and a filter (§9). |
| LFO | The tap-tempo clock and the four LFOs. |
| HANDS | The tracker, the box, the axes and their setup, feel and calibration, the ghost hands (§12). |
| PRESETS | The show, "starts on / home", the bank of twenty-four, the preset strip and preset list, module presets under **more** (§10). |
| SYSTEM | Cheat sheet and desk-diagram switches, Restart process, hot reload status, the library path, config errors and notes, the dream worker's state, the stall log's line; **midi**: knob smoothing, the port's state, the learn line; **bridge**: port, encoding, messages sent or why it is off. |

**The FACES page** (`ui_patterns.py`), top to bottom:

- **Faces**, **Cut-through** and the pattern **mix**.
- **The patterns**: a chip per pattern, four to a row, each with a small
  live swatch of that pattern on the inputs as they are now; the one on
  show is solid red. Hover: the pattern's one line. Click: show it (one
  undo step). Right-click: `view.pattern`'s menu, to learn a knob that
  steps the patterns. The renderer draws the swatches, one a frame, only
  while the page is open (`Renderer.want_swatches`).
- **The pattern on show**: its name and its line, ‹ › at the right (round
  the ends). While `patterns.glsl` does not compile the line is the GLSL
  error (in full on hover; the last good version keeps drawing); while
  Faces is off it is "Faces is off" and a **faces on** chip.
- **INPUTS · <PATTERN>** with **all neutral** (every input back to 1.0, one
  undo step), and the pattern group's preset strip.
- **Eight inputs, two lines each.** First: the name, what it does on this
  pattern, and at the right what drives it — "SUB pushes +0.35", "K3 sets
  it", "macro.4 sets its base", "(off)" — a link to ROUTING filtered to
  that input. An input nothing drives offers **+ SUB** … **+ AIR**
  (inputs 0–5), **+ LFO 1** (HUE) or **+ LFO 2** (SPREAD): a click adds a
  push route at the factory depth into the loaded preset and stays on
  FACES; ⌘Z takes it back. Second: the slider (`base → effective` while
  driven, a white bar at the effective value) and a **1** chip back to
  neutral. On FLAT every row reads "FLAT reads no input", dimmed but
  live.
- A faint last line: "right-click an input: learn a knob or a hand".

Its fit at the control size is held by
`tests/test_ui_patterns.py::test_the_page_fits_with_every_row_driven_and_flat_or_the_longest_mode`,
but in font metrics that are not the Mac's (hand check 120).

Every page that is a registry group carries a preset strip for its
module presets.

**Widgets.** A fader fills red from its origin to its value. A param a
performer (a hand, a band, an LFO) is driving shows its *setting* as the
handle and the effective value as a white ghost bar, and its hover names
the performer. Right-click any param, a row's label or an analyzer meter
for the menu (§9).

**The footer**, on every page: the frame rate; one message slot; `dim
40%` (or `dim black`) in the warning colour while the master dim is under
full; "· output 2 black" while an output shows nothing for another
reason; the show's name and its unsaved mark. The message slot shows the
newest line for 4 s (`ui.MESSAGE_S`): an undo's status, the library's
status and warnings ("saved TRIP 2 → F6", "F6: an empty slot"), what a
learn or unbind did, and — while nothing newer is up — an armed learn's
line or a picked desk control's line in red (a click on it cancels).

**The red banner** across the bottom of the control window names a live
render error or render stall, a render error that recovered, the
watchdog's warnings and why the dream worker is off; what is not live
stays until **dismiss**.

**The desk diagram** (`ui_desk.py`) draws the APC40 in the control
window's bottom-left, lit exactly as the device is, from the table — so
it works with no device. With the panel hidden (H, the APC40's DEVICE
ON/OFF, or the chip in the desk's header) it fills the control window.
Once it is big enough every lit control carries what it does (the
param's label, a bank pad's preset name, a step's amount); bright ink is
the layer that is up, grey an invariant control.

**Click a desk control, then a param.** A left click on a control in the
diagram picks it: it is framed on the desk and on its ROUTING line, and
every page but ROUTING is dimmed and takes no input except a click on a
param, which puts the control on that param in the loaded preset (one
undo step). A pick lets go by itself after 20 s with no click
(`ui_desk.PICK_S`), or on a click on it, the desk's empty ground or the
footer line. No click maps until the mouse has moved 12 px from the click
that picked. An invariant control, or any control while SHIFT is
latched, is picked only to show its line; the header says why. With
"Learn desk" armed, a click on the diagram completes the learn as a
knob would.

## 7. Keys and the gamepad

Every key and pad button is a row in `bindings.json` (factory rows in
`hyperspace/bindings.default.json`), so each rebinds there; the five
loop keys — Cmd+R, ↑, ↓, Esc, Q (`app.LOOP_KEYS`) — are the app's own.

| Key | Does |
|---|---|
| ← → | previous / next shape |
| Space | pause / resume rotation |
| P / L / F | points / lines / faces |
| 1–6 | toggle planes XY XZ YZ XW YW ZW |
| ↑ ↓ | 4D depth (hold accelerates) |
| [ ] · , . | brightness down / up · speed down / up |
| M | microphone on / off |
| K · 0 | play / pause the track · restart it |
| R | reset the view and camera |
| F1–F8 · ⇧F1–F8 | load bank slot 1–8 · save the live state as that slot's preset |
| B · ⇧B | tap tempo · the global LFO trigger |
| Cmd+Z or Ctrl+Z · with ⇧ | undo · redo |
| Home (fn ← on a laptop) | home: load the show's "starts on" preset |
| H · / or ? | hide / show the panel · the cheat sheet |
| T · G | overlay on / off (only with `[output] overlay = true`) · overlay click-through |
| Cmd+R · Esc / Q | restart · quit |

**A press fires only its own chord**: a row fires when its modifiers are
exactly the held ones that some row on that key names (`SHIFT`, `SUPER`,
`CONTROL`), so ⌘⇧Z redoes and does not also undo; a modifier no row on
the key names is ignored.

**Gamepad** (Xbox layout, Bluetooth or USB; `gamepad.py` keeps its own
button map): A pause rotation · B next preset · X points · Y faces ·
LB / RB previous / next shape · d-pad brightness (↑↓) and speed (←→) ·
left stick orbit, right stick zoom, a stick click resets · LT / RT 4D
depth out / in · VIEW panel · MENU cheat sheet.

## 8. The APC40

Plug in an Akai APC40 (mk1) and it is found by name on launch and after
an unplug. On open it is put in Alternate Ableton Live mode (every LED
and knob ring is the host's); on close it is put back to generic mode.
The protocol, the default map (`DEFAULT_MAP`) and the glyphs are
`hyperspace/apc40.py`. `uv run python tools/midi_probe.py [port]`
echoes what a controller sends and lights an APC40, without the app.

**Glyphs** (`apc40.LAYOUT`), used on ROUTING rows, learn messages and the
diagram: K1–K8 track knobs, D1–D8 device knobs, S1–S8 track faders, SM
master fader, X crossfader, C cue knob, Gr·c the button field (rows 1–5
clip launch, 6 clip stop, 7 track select, 8 activator, 9 solo, 10
rec-arm; column 9 scene launch 1–5, STOP ALL, MASTER select), B1–B22 the
other buttons, ⇧ SHIFT. Akai's name is in each hover.

**Two layers under a latched SHIFT.** SHIFT's LED is lit while the
**global** layer (the session's) is up; otherwise the **preset** layer
(the loaded preset's own desk) is up. A control the up layer does not map
is dark and does nothing. **Invariant** controls mean the same on both
layers; none of them can be learned, mapped by a click or unbound, a
preset's desk row on one is dropped at load with a note, and each keeps
doing its job while a learn is armed.

| Control | Layer | Does |
|---|---|---|
| S1–S6 | invariant | band 1–6 post-drive |
| S7 · S8 · SM | invariant | master dynamics · master trim · master gain |
| X (crossfader) | invariant | **master dim**: left black, right full |
| Clip row 1 (G1·1–8) | invariant | bank slots 1–8 (as F1–F8) |
| Clip rows 4–5 (G4·*, G5·*) | invariant | bank slots 9–16 and 17–24 |
| Clip-stop row (G6·1–8) | free | nothing by default (dark); Learn it for toggles |
| OVERDUB | invariant | **home** (lit while the show names a "starts on") |
| QUANT | invariant | next filled bank slot |
| SHIFT | invariant | latch the global layer |
| TAP TEMPO · NUDGE + / − · METRONOME | invariant | tap · shift the downbeat by a hundredth of a beat · the global LFO trigger (blinks on the beat) |
| PLAY · STOP · REC · CLIP/TRACK | invariant | track play · stop · microphone · restart the track |
| Track select · solo · rec-arm (G7, G9, G10; columns 1–6) | invariant | select that band · step its transfer function · reset it |
| ◀ ▶ | invariant | previous / next band |
| STOP ALL | invariant | Reset all bands |
| DEVICE ON/OFF · DETAIL | invariant | panel · cheat sheet |
| MASTER select · PAN | invariant | overlay · overlay click-through |
| D1–D8 | global | the selected band's strip: trim, contrast, transient, pre, post, attack, decay, threshold |
| K1–K5 | global | hand steadiness, response, catch, the selected axis's return, BPM (K6–K8 dark) |
| Clip row 2 · row 3, columns 1–3 | global | band scenes 1–8 · 9–11 |
| K1–K8 | preset (factory default) | brightness, speed, instances, pattern mix, field amp, field rate, bitmap opacity, zoom |
| D1–D4 | preset (factory default) | 4D depth, camera yaw, camera pitch, pattern (D5–D8 dark) |
| C (cue knob) | preset | step the shape, one click a shape |
| Activator (G8), columns 1–6 | preset | toggle planes ZW, XW, YW, XY, XZ, YZ |
| Row 3, columns 5–8 | preset | field motion STILL, ORBIT, WAVE, RIPPLE |
| Scene launch 1–5 | preset | points, lines, faces, rotate, reset view |
| ▲ ▼ | preset | brightness up / down |

The preset rows above are what a fresh preset starts with
(`apc40.SCENE` on D1–D4); a factory or user preset with knobs of its own
replaces all eight device knobs, and a preset with an empty desk has
every preset-layer control dark. D4 steps through the seventeen
patterns, which show only where faces are drawn.

**Bank pad lights** (rows 1, 4, 5): green while its preset is the loaded
one, amber while its slot holds another preset (velocity 5, Akai's
"yellow"; `apc40.filled_of`), dark when empty. The diagram draws amber at
half strength with the preset's name.

**Save on the desk.** Hold an **empty** bank pad (clip rows 1, 4 and 5)
for 0.6 s (`midi.HOLD_S`): the live state is saved as a **new** user
preset named from the loaded one with the next free number (TRIP → TRIP
2; with nothing loaded, PRESET 1; it never overwrites a file and never
hides a factory preset), it becomes the loaded preset and goes into
*that* pad's slot, and the show is written at once ("saved TRIP 2 →
F6", or "→ slot 10"); the pad blinks for 1.5 s. Holding a filled pad
just loads it — nothing is written. To make room, free a pad on the
PRESETS page: right-click its slot → **free this pad (keeps the
preset)**; the preset stays in the list. (Until 2026-10-09 the
clip-stop row was a SAVE AS bar into the next empty slot; that row is
free now.)

**Knobs and faders.** The track and device knobs are endless encoders:
the app sets their position with the ring's CC, so a knob continues from
its ring after a layer switch or a preset load. The faders are real pots
with **soft pickup**: after a change they do nothing until moved through
the param's value. A fader keeps its catch through a preset load unless
the load moved its param, so the crossfader and the faders (all session
params) carry on from where they are. A fader moved while its row is
disabled, or while an armed learn takes its messages, picks up again
from where it is (`MidiIO._passed_over`) rather than jumping.

**Knob smoothing** (`desk.slew`, "Knob smoothing", SYSTEM page under
**midi**; off to 250 ms; the running app starts at **80 ms**,
`routing.SLEW_DEFAULT_S`, unless the show saved its own value). A knob
or fader row with op `abs` on a continuous, non-integer param glides to
each new value over that long instead of landing a detent at a time, and
comes to rest on the same detent it would have. Not smoothed: the cue
knob and every other relative row, buttons, and an `abs` row on an enum,
toggle, trigger or whole-number param. A value set meanwhile by anything
else stands and the glide stops; a preset load ends every glide but a
session param's; off, an unplug or a quit lands every value at once. The
setting is saved with the show, never with a preset, and is on no knob.

**Reconnect.** With no desk connected the app looks for it every 2 s
five times, then every 10 s (`midi.RECONNECT_S`, `RECONNECT_FAST`,
`RECONNECT_SLOW_S`); a desk that vanishes is looked for at the fast pace
again. `[midi] enabled = false` stops all of it.

**Macros** (`macro.1`–`macro.8`) are knobs with subscribers: each
subscriber sets a param's base or scales a route's depth over its own
`from → to`. A hand on a macro moves only the depths.

## 9. Learn, Unbind and routing

The control model — the parameter registry, bases and effective values,
routes (`push` / `position`), one performer per param, the referee — is
[ARCHITECTURE.md](ARCHITECTURE.md) §3. What follows is
how it is operated.

**The right-click menu** opens on a param's widget, on a row's label and
on every analyzer meter. It lists what is bound — the preset's desk rows
("K2 (track knob 2)"), each route in words ("R height pushes +0.45"), the
session's rows dim — then:

- **Learn desk** — wherever a desk row can go, device plugged in or not.
  Completed only by the desk: a knob, a button, a fader, or a click on
  the diagram. The invariant controls keep working meanwhile (a fader
  moves, a bank pad loads — the learn then lands in the preset just
  loaded). With SHIFT latched any other control is refused in words
  and the learn stays armed: unlatch and the same learn lands.
- **Learn hand ▸ left / right** — only with a tracker, on a param a hand
  can drive (not a setting such as `ghost.mirror`), for the sides the
  rig's axes have. Completed only by an axis of that hand; the other
  hand and the desk do their own jobs meanwhile.
- **Cancel learn** while this param is armed.
- **Unbind** — shown only when there is something to remove; a submenu
  ("desk — K2", "route — R height, LFO 1", "both") when there are both.
  Removes the preset's desk rows and every route on the param, as one
  undo step; never a session row.
- The hand rows' "Gate: … ▸" and "Route a lane here…".

**A learn writes into the loaded preset** — never `bindings.json` — and
lights its dirty dot until a save. A desk learn makes a preset-layer row;
the line says what let go ("learned view.bright ← D3 (device knob 3)
(into the preset); K1 let go"). A hand learn makes a route naming the
axis by name (`hand:right.pitch`), so a rig that reorders `[hands] dofs`
keeps its presets; a name the rig lacks is dormant. What it lands as:
a tilt, or a sideways or in/out move on an axis whose "Centred" is on,
**pushes** by `hands.learn_depth` (default 0.25, 0.05–1, HANDS page,
saved with the show) — it adds to the setting and is nothing while the
hand is level; height pushes onto a range centred on zero (a rate, an
angle, a pan, hue) and is the fader (`position`) on anything else; a
toggle, list, trigger or whole-number param always gets the fader. A
learn takes that axis's other routes with it (the line says "moved
from …"; one ⌘Z puts them back). An armed learn never times out.

**The ROUTING page** is one page over the loaded preset: its head (the
preset, its dirty dot, save / as…, which desk layer is up), the routes,
the desk with its dark controls, the macros and their subscribers, and
the session's MIDI rows read-only. **The filter** (left of `+ route`)
keeps only the lines that contain every typed word, matched anywhere —
a route's sentence, source, target and label; a desk line's glyph, Akai's
name and target; a macro's id, label and subscribers. It is UI state:
not saved, no undo step, empty at launch, left alone by a preset load;
its × and a click on a desk control clear it. A route's `scale` can only
be a session param; a route may perform a session param, marked
"session" on its row.

## 10. Presets, shows and the bank

A **preset** (`presets/<slug>.json`) is one whole performance moment:
the performance groups' values (`view rot camera pattern dream fx lfo
macro`, `params.PERFORMANCE_GROUPS`), the performer routes, the desk's
preset layer, the macros and the module labels. **A load replaces all of
it** — every performance param lands from the file or its group default,
every route and preset-layer row is replaced — and never touches a
session param (`tempo hands ghost band master scene audio output overlay
ui desk`): a tapped BPM, the hands' feel and the ghost hands survive any
preset. Anything a file names that it may not (a session id, an unknown
id, a route onto a param that is not modulatable, a desk row on an
invariant control) is dropped with a note and the file is left as it is.

**The factory presets are generated**: `uv run python -m hyperspace.preset`
(`preset.write_factory`) writes `hyperspace/library/presets/` from
`preset.FACTORY_PRESETS`, and `tests/test_presets.py` pins the result.
The routes of the eight house moods (`preset.HOUSE`), the nine party
presets and the routing presets come from code; the house and party
presets' values and notes are data in their files. The house moods'
routes are `routing.legacy6_routes`: lane *i* pushes its plane's rate
(the reference's depth, × the drive fader) and pattern input *i* at
`routing.PATTERN_DEPTH` (0.35). Change the depth there and regenerate,
and every factory preset follows. `legacy6`, the parity anchor, puts the
rates on bases of 0 and the pattern inputs on 1.

A **show** (`projects/<slug>.hyp.json`; the code says *project*) is the
session: its values, the module presets of the session groups (the band
layout and scene), the preset it **starts on**, and the **bank**. The
factory shows are **party** (F1–F8 TUMBLE, FACES, FIELD, WAKE, TRIP,
ACID, MANDALA, NOITA; TRACER on slot 9; starts on TUMBLE) and **house**
(eight house moods). A launch opens the show opened last (`last_show`),
else the party, your copy of it if you have one.

**The bank** is twenty-four preset names (`library.SLOTS`). F1–F8 and the
APC40's clip row 1 load slots 1–8, clip rows 4–5 slots 9–24, and the
PRESETS page all of them. ⇧F1–F8 (or ⇧click on a slot's button) save the
live state as that slot's preset (`PRESET <n>` for an empty one). QUANT
and the gamepad's B step to the next **filled** slot; a learned step or
knob on `preset.select` also skips empty slots. An empty slot or a name
with no file loads nothing and says so ("slot 13: an empty slot"). A
show file holds the bank only as far as its last filled slot, never
fewer than eight entries, and **a load never rewrites a show**. The bank
and "starts on" are written to the show the moment they change (a
factory show's first write makes your copy) and are not undo steps.

**Home** — the Home key or the APC40's OVERDUB loads the show's "starts
on" preset, as a load like any other (one undo step, "home → TUMBLE").
A show that names none loads nothing and says so.

**The PRESETS page**, top to bottom: **show** — its name, "factory"
beside a factory show, show ▾ · save · save as · new; **starts on /
home ▾**, written into the show when picked; **the bank** — F1–F8 as
eight buttons two a row, slots 9–24 as sixteen smaller buttons four a
row ("9 TRACER", "10 —"), the live one lit, click loads, ⇧click saves,
right-click **put preset here…** / **clear slot** (clearing deletes no
file); a slot whose preset has no file is drawn in the warning ink;
**the preset strip** — the loaded preset, its dirty dot, save (**save
copy** on a factory preset) and as…; **more**, folded: a module-preset
strip per group (save / as… / reset).

**The dirty dot** (`ui.dirty_dot`) is a red disc on every strip, on
ROUTING's head and on the rail; while there is something to save the
save chip is solid red, and the loaded slot's bank button carries a
white disc. It compares the live state with the loaded preset or show
within undo's float tolerance, so a performer's round-off lights nothing.
Nothing asks before a save.

**The preset list** (click the preset strip's name): every preset,
factory ones dim, twelve rows before it scrolls. **×** on yours moves it
to the trash (slots that name it keep the name, and the line says what
still points at it); × on a factory preset **hides** it (`hidden.json`;
only the list loses it). **rename** on yours renames the file, the name
inside and every show of yours that names it (each copied to the trash
first; a taken name is refused; a factory preset is refused — save a
copy first). At the foot, while each applies: **show hidden (n)** with
**unhide**, and **trash (n) ▸** — every file in the trash, newest first,
each with **restore**, then **empty trash…**, which asks "delete N files
for good? — click again" for 4 s. None of these is an undo step.

**Module presets** (one group each, `hyperspace.preset/1`) replace only
their group. The analyzer's band presets are also its **scenes** (§13).

## 11. Undo

Cmd+Z or Ctrl+Z undoes; with ⇧, redoes (`undo.py`). The footer says what
it did ("undid Brightness 2.00× → 2.96×", "nothing to undo").

**A step** is one gesture — a slider drag, a desk knob turn, a typed
value, a toggle, a key or pad press that sets something, a mouse orbit,
an edit on ROUTING — or one replacing action: a preset load by any road,
a show load or new show, home, a module preset load or reset, a learn
landing, an Unbind, a ×, Replace in the Replace / Keep prompt. Once a
frame `Undo.tick` compares a fingerprint of what the user sets; a change
opens a step that closes after **0.4 s of quiet** (`undo.SETTLE_S`), so a
slider moved within 0.4 s of a load joins the load's step. The stack
keeps 100 steps; a launch starts empty.

**Watched:** the base of every persisted param that is not an alias, a
trigger or in the `tempo` group — performance and session alike, the
camera included — and the loaded preset's routes, preset layer and
macros.

**Not a step:** a performer (a hand, a band, an LFO writes an offset,
never the base); the rotation phases; the tempo (a tap is never undone);
triggers; selections and panel state (`band.select`, `fx.select`,
`preset.select`, `desk.shift`, `ui.*`); the transport; the rig's output
settings (screen, fullscreen, overlay, the master dim, every
`output.N.*` switch); `bindings.json`'s session rows; a band added,
removed or moved (a step's band strips land only on the layout they were
taken on); a save, a delete, the bank and "starts on" (their net is the
trash and the show file).

**A restore** puts back only what differs, through `Param.set` and the
table's own calls: undoing one slider sets one param — no load runs, the
desk layer stays, faders keep their catch, LFOs keep their phase. Undoing
a load also puts back what the library calls loaded, so the PRESETS page
names the earlier preset and **save** writes that one. A restore writes
no file. The band strips' 8-second "Reset all → Undo" is separate.

## 12. Hands

Ultraleap hands (`hyperspace/hands/`), off until `[hands] enabled =
true`. Each hand gives its palm's pose — six axes by default, from the
features in `hands/core.py` (`FEATURES`: x y z in mm, roll pitch yaw in
degrees, grab, pinch, grab angle, pinch distance, four thumb-to-finger
ratios) — plus eight pinch switches. Each axis is calibrated, smoothed,
shaped (dead zone, curve), enveloped (attack, decay), sprung back to a
rest value when the hand leaves and glided back onto it when it returns
(Catch). Inside the app the axes are `hand:<side>.<name>` sources for
routes; outside they go to a MIDI port for a DAW (`[hands] out`).
`uv run python tools/hands_probe.py` shows every axis live without the
app (`--calibrate 20` runs the sweep, `--solo right.pitch` sends one axis
to the DAW).

**The HANDS page** (`hands/panel.py`): the setup strip (a setup is every
per-axis and global hand setting, a module preset of the `hands` group);
the status (tracker, each hand — ● in the box, ◌ tracked but outside it,
○ not seen — the DAW port, the last MIDI sent); the pinch switches with
their live gaps; the box from above with a height gauge; one row per
axis (click to edit); the selected axis's transfer plot and settings
(invert, centred, dead zone, curve, attack, decay, on exit, rest,
return, bounce, MIDI out, mirror, solo); **feel & calibration** —
steadiness, response, catch, MIDI rate, hysteresis, pinch thresholds,
**Learn depth**, **calibrate 20 s**, **reset ranges**; and, under the
box, the ghost hands: the **Ghost hands** tick; while it is on,
**Opacity** and a **more ▸** chip on its line and **Style** and
**Guide** on the next. **more ▸** opens Mirror, Tethers (with a guide
on) and the ghost's notes — an error, or the unmeasured-mode note; while
there is one the chip reads **! more ▸** in the warning colour and its
hover says it. A narrower panel wraps a group onto the next line.

**The interaction box.** A hand counts only while its palm is inside a
box in the camera's millimetres (x across, y up, z toward the
performer), one box for both hands. A hand outside it is **absent to
everything**: its routes let go and the settings return that frame, its
switches drop, its presence note goes off, its ghost fades. A hand that
is in stays in until its palm is 15 mm past a face. The **calibrate 20 s**
sweep sets the box and every axis's range: the box is where the palms
went (2nd–98th percentile) plus 40 mm; a direction swept less than 12 cm
is left open and the note says so. The box is off during the sweep, so
calibrate with nobody else in view. **reset ranges** opens the box and
restores the default ranges. There is no other control; `hands.json`
can be edited by hand: `"box": {"x": [lo, hi], "y": [lo, hi], "z":
null}`, `null` meaning open; a pair that is not two finite numbers with
lo < hi opens that coordinate with a note.

**Ghost hands** (`ghost.py`): both tracked hands drawn over the render,
following the skeleton raw (no smoothing), a display only.

| Param | Default | Notes |
|---|---|---|
| `ghost.on` | off | modulatable |
| `ghost.alpha` | 0.6 | modulatable |
| `ghost.mirror` | off | flip left for right (a mirror or a Pepper's Ghost glass) |
| `ghost.guide` | OFF | OFF · BESIDE · ON HAND: per hand, a ball per axis, an arc per rotation, the pinch beads and a grab ring; what a route reads is bright, the rest grey |
| `ghost.tethers` | off | with a guide: a line from each routed mark to a label naming the params it drives |
| `ghost.style` | HANDS | HANDS (capsules), JOINTS (beads), PALMS (an orb that swells as the hand opens, a ring, a spoke), CAGE (a wire octahedron), MARIONETTE (fingertips on strings from a bar) |

All six are in the `ghost` group, a session group: saved with the show,
never moved by a preset. `mirror`, `guide`, `tethers` and `style` are
settings — a hand learn onto one is refused in words, and a preset's
route onto one is dropped at load. The ghost has its own fixed camera
framing the box (or, with no box, the calibrated ranges); a hand leaving
fades out over 0.3 s and one coming back fades in over 0.1 s. Desktop is
the only tracking mode whose axes have been measured; with `screentop`
or `hmd` and the ghost on, the HANDS page says so (in **! more ▸**). Where the hands show
on each output, and whether the effects bend them, is §14.

**Without a camera.** `tools/hands_tape.py record <file>` keeps a few
seconds of real frames as a tape; `[hands] tape = "<path>"` (with
`enabled = true`) plays one in the app instead of the camera; `shots`,
`synth`, `styles` and `info` render, make or describe tapes. A missing
or malformed tape is a note on the SYSTEM and HANDS pages.

## 13. Audio

**Sources** (`audio.py`). Nothing captures at launch. **A capture
device**: M or *Listen to mic*; mono, 48 kHz. The device combo lists
every input; a loopback driver (BlackHole, Soundflower, anything named
"loopback") is recognised by name, pre-selected, and labelled `System ·
…` — that is how the Mac's own output is captured (SETUP). **rescan**
reads the device list again. **A file** (*Load track*; wav, mp3, flac,
ogg): played through an output stream at the track's rate, the analyser
built at that rate. Pause keeps the stream running on silence, so the
bands decay on their own time; K plays / pauses, 0 restarts. Stopping a
capture lets every lane go at once.

**The chain** (`analyzer.Analyzer`; `bands.py` holds the constants and
shapers): N bands (1–16), each a centre frequency, a Q and a weighting
curve (rect, triangular, gaussian, butterworth). Per band:

```
FFT bins → weighted power under the band's curve → dB → u (1.0 nominal)
  ├─ LEVEL: attack / decay envelope → peak / valley window + gate
  │         → upward expansion about the band's running mean   (contrast)
  └─ TRANSIENT: fast env − slow env, peak-normalised            (transient)
  → blend → harmonic coupling → soft ceiling          ← the INPUT meter (white)
  → pre-drive → soft ceiling → transfer function → post-drive → soft ceiling
                                                      ← the OUTPUT meter (red)
  → lane i
```

The chain ends at the lanes; a lane reaches a rotation plane or anything
else only as a route. Nothing hard-clamps: three soft ceilings bend from
1.25 towards 2.6. The FFT is 4096 points, Blackman window, smoothing
0.15 (the band envelopes do the smoothing). Harmonic coupling boosts a
band by its coherence with the next band up — a proxy, not true
harmonic detection. `master.dyn` scales the dynamics recovery (valley
tracker, expansion, transient path), which brings back motion a limiter
took from a brickwalled master; it runs to 4×. A meter column pinned
near the ceiling for half a second lights a blinking annunciator.

**Input trim** (`band.{i}.trim`, `master.trim`; off, then −60 to +12 dB)
is applied before the trackers and again after them, because the
window normaliser removes any static gain in front of it. **AUTO /
MANUAL** (`band.{i}.norm`, the chip on the strip): AUTO, the default, is
the reference chain, where trim is not monotonic through the useful
range; MANUAL bypasses the window, expansion and warm-up for that band,
so its level is the envelope and the trim a plain gain — at the cost of
the dynamics recovery. `uv run python tools/trim_sweep.py --manual`
prints a sweep.

**Thirteen transfer functions**: LIN SQRT SQ CUBE CURV GATE INV HOLD STAC
CHOP TREM S&H SLEW (CHOP, TREM and S&H run at fixed rates, not the
tempo clock).

**Eleven scenes**: Balanced, Kick & Sizzle, Glacial Drift, Strobe Cage,
Bass Engine, Air & Lace, Inverse World, Percussive, Tremolo Web,
Harmonic Bloom, Slow Bass / Fast Air. A scene is a band preset
(`library/band/*.json`). The scene combo, the APC40's scene pads and
**Reset** re-tune the bands you have from the scene; the band preset
strip loads a file whole, layout included. **Reset all** relabels to
**Undo** for 8 s.

**Faders** are integer positions on tapers that map exactly both ways
(`tapers.py`): logarithmic for gains and time constants, linear where
the quantity is already even; the tag is in each knob's tooltip.

**The tempo clock** (LFO page; B or TAP TEMPO taps, NUDGE shifts the
downbeat) drives the four LFOs. It syncs to nothing outside the app.

**The bridge** (`[bridge]`, `bridge.py`) sends the lanes (or any param)
out as 14-bit MIDI — pitch bend per channel, or CC pairs — rate-limited
and only on change, and turns the same messages coming in on `in` into
`ext:<i>` sources for routes. Use two buses: IAC echoes. The SYSTEM page
shows its state.

## 14. Outputs

**One output** by default: the render window, from `[output] monitor` /
`fullscreen`. **Several** from `[[output.screens]]` (§5), up to four
(`outputs.MAX_OUTPUTS`), numbered by their place in the list whether or
not they opened. Output 1 is made as the single render window always is
(4× MSAA; transparent only with `[output] overlay = true`), sets the
frame's size and paces the loop (its swap waits for its screen; later
outputs' swaps do not). Later outputs are opaque, never overlay, and
their screen and fullscreen come only from the config (the OUTPUT page's
Screen and Fullscreen rows move output 1). A later output whose
`monitor` names no connected screen **is not opened**, with a note
("output 2 (projector): monitor = 2, but 2 screens are connected (0–1) —
not opened"); output 1 always opens. A later output of another shape
shows the whole frame letterboxed, the hands registered on it. Each
later output is drawn from the shared textures in its own context
(`outputs.Presenter`); a failing present marks that output and the rest
go on.

**Per-output switches** (`overlay.register_switches`): `output.N.scene`,
`output.N.hands`, `output.N.through` ("Hands through effects") and, with
two or more outputs or a lone entry whose `dim` is under 1,
`output.N.dim` (multiplied by the master dim). They are **rig settings**:
set from the config entry at every launch and Cmd+R (defaults scene on,
hands on, through off, dim 1), never saved, never in a preset, show or
undo step; a switch flipped mid-set lasts until the restart. They can be
learned onto a desk button.

| Scene | Hands | Through | The output shows |
|---|---|---|---|
| on | on | off | the scene with its effects, the hands clean on top (default) |
| on | on | on | the scene and the hands, both through the effects |
| on | off | — | the scene with its effects |
| off | on | off | the hands alone on the ground |
| off | on | on | the hands alone, through the effects |
| off | off | — | black |

"Hands shown" also needs `ghost.on` and a hand drawn this frame; with no
effect on, "through" changes nothing. The echoes and the dream never
hold the hands. With the guide on, its gauges and labels are drawn over
the hands after the effects, so they are never bent. The OUTPUT page
says in words what each output shows ("scene + hands through the
effects · 64%", "black — the scene is off and no hand shows").

**The master dim** (`output.dim`, the crossfader, the OUTPUT page's first
row) multiplies the finished frame — scene, look-back, effects and
hands — on every output: 0 black, 1 full. It is a rig setting: not
saved, not modulatable, not in any preset, show or undo step, so every
launch starts at full. On an opaque ground the ground stays opaque black;
in overlay the render fades off the desktop.

**Overlay** is possible only with `[output] overlay = true`; without it
the render window is always opaque and T, MASTER select and the panel's
toggle do nothing (the OUTPUT page greys it and says why). With it, T
puts output 1 over the desktop: no frame, above everything, clearing to
see-through, clicks passing through (G or PAN takes them back);
`output.bg` and `output.alpha` set the ground and opacity. The
`overlay.*` ids are aliases of `output.*`.

**Where windows open** (`placement.py`): a configured `monitor` /
`control_monitor` index first, then `windows.json` (the last quit's
rects — always the plain window's, never a fullscreen cover), else the
render window top-left of the primary screen and the controls flush
right; two later outputs with no memory open 40 px apart. A remembered
rect is used only when enough of it is on a connected screen; otherwise
the default spot, with a note. `windows.json` is written on quit and
Cmd+R only.

## 15. Hot reload and the watchdog

**Hot reload** (`hotreload.py`). Save a module on `hotreload.MODULES`
while the app runs and live objects pick up the new code in place; a
broken save keeps the last good version and shows the error on the
SYSTEM page. `app.py`, `hotreload.py`, `offline.py` and `watchdog.py`
are cold: changing them needs Cmd+R. A changed `__init__` does not
re-run on live objects. Shaders (`patterns.glsl`, `_common.glsl`,
`shaders/fx/`) and the library's JSON files reload too.

**The watchdog** (`watchdog.py`) appends to `<home>/stall.log` a `===
<kind>` header — the time, the loaded preset, what happened — and every
thread's stack, for:

- `stall` — no frame completed for 2 s;
- `render error` — the render draw raised (the panel lives on; the
  render window holds its last frame), once per distinct error;
- `render stall` — no render output presented for 2 s while the loop
  runs (minimised, occluded, another Space…), with the window's state;
- `warning` — one output not presenting while another does, an output's
  present that raised, or a preset asking for the dream with no worker;
- `stranded target` — a frame that began on an offscreen framebuffer;
- `non-finite` — a param that dropped a NaN or inf.

`kill -USR1 <pid>` dumps every thread on demand, and a stall that holds
the GIL is caught by faulthandler's timer. The SYSTEM page shows the
log's line once it has entries. Nothing in the watchdog can stop the
show: a log that will not open is kept as an error and the loop goes on.

## 16. Testing

```bash
uv run pytest -q
uv run ruff check .
```

- Every test runs against its own temporary home: `tests/conftest.py`
  sets `HYPERSPACE_HOME` to the test's `tmp_path` in `os.environ`
  itself, so no test can read or write `~/Hyperspace`.
- No test reaches the machine's MIDI: the autouse fixture
  `_no_real_midi` makes the port lists empty and every open raise,
  unless a test patches `mido` itself.
- One test is skipped:
  `tests/test_hands_tape.py::test_every_recorded_tape_replays_through_the_ghost`,
  because no real hand tape has been recorded into
  `tests/fixtures/hands/` (`tools/hands_tape.py record` on the rig).
- The parity net: `tests/golden/` traces recorded from the retired HTML
  app (`tools/record_golden.py`, which needs Playwright's Chromium) hold
  geometry exact and the audio chain's behaviour; `tests/legacy_chain.py`
  is a frozen copy of the reference chain that the analyzer's "Legacy 6"
  layout must match bit for bit. Re-freeze it only when the maths
  changes on purpose.
- GL and imgui run headless: every shape renders offscreen, every panel
  page draws and fits, every factory effect compiles. Extra windows and
  screens are fake GLFW window systems (`tests/test_app_boundary.py`).
  `HYPERSPACE_FRAMES=n uv run hyperspace` is a windowed smoke run.
- The patterns: `tests/test_patterns.py` holds the shader to
  `patterns.py`'s table and checks every input moves every mode;
  `test_the_face_shaders_pass_the_reference_compiler` runs
  `glslangValidator` and skips where it is missing. Fit tests measure in
  this machine's font metrics: in the cloud container test_fx's own two
  fit tests miss by 18 px, so a pass or a fail there says nothing about
  the Mac.
- The shapes: `tests/test_shapes4d.py` holds every shape to its
  recorded digest (`tests/golden/shape_digests.json`, floats rounded to
  1e-9) and every lifted or masked shape to `VOLUME_FLOOR` through each
  W plane; `tools/turntable.py` draws the same sweeps (§1).
- Import boundaries are tests: the core never imports `midi`, `bridge`
  or `dream`; `hands/core.py`, `hands/signal.py`, `lfo.py`, `tempo.py`,
  and `undo.py` import nothing from the package; `library.py` never
  imports `config`.

What only a person at the machine can check is
[`TESTING-GUIDE.md`](TESTING-GUIDE.md) and the numbered list in
[`plans/11-hand-checks.md`](plans/11-hand-checks.md).

## 17. Known limits

- **A screen plugged in after launch is not used** until a relaunch
  (Cmd+R): a later output that did not open stays closed, and output 1's
  configured screen stays −1 for the run.
- **Frame pacing with two screens has never been observed by a person.**
  Output 1 waits for its screen and later outputs do not; whether that
  paces the loop on two real screens, and whether a non-waiting
  fullscreen output tears, is unknown.
- **With no desk connected the app keeps looking** — every 2 s five
  times, then every 10 s. Each look creates a CoreMIDI client; `[midi]
  enabled = false` stops it.
- **On the masked Heart, the W planes' readouts keep counting**: the
  VIEW page's XW / YW / ZW keys, `rot.phase.*` and ROUTING show the W
  planes turning while the picture turns in XZ, YZ and XY. Nothing says
  the planes are folded.
- **The FACES page's fit and `patterns.glsl` on Apple's GL are
  unverified**: both were checked only in a container with Mesa and
  other font metrics (hand checks 120, 121).
- The amber "filled" pad light and the save-as blink use Akai's
  documented velocities and have not been confirmed on an APC40 mk1.
- Open findings in [`AUDIT-2026-09.md`](AUDIT-2026-09.md): R13, R14,
  R15, U9, U10, P6, V8.
