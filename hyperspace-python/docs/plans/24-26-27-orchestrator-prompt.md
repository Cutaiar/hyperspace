# Plans 24, 26 and 27 — the party fixes, the render graph and the device registry (orchestrator prompt)

You are the top-level orchestrator for the first group of work from the
post-party wishlist in `Cutaiar/hyperspace` (the Python app under
`hyperspace-python/`). Three independent streams, each its own plan:

- **Plan 26 — the render graph (F2).** Today's fixed order of render passes
  becomes a graph of nodes in code; the hands become a geometry node in one
  shared camera; the graph is stored in the preset as JSON.
- **Plan 27 — the device registry (F1).** A `Device` interface, devices
  listed in `config.toml`, several MIDI ports at once, source schemes from
  the registry instead of fixed tuples, sinks treated the same way, a
  point-cloud source type, and an OSC device added with no edit to
  `app.py`.
- **Plan 24 — the party fixes.** The desk you can trust (the two-handed
  save, loads that relight everything, toggles on both layers), the track
  faders freed for presets, a coverage report and desk templates, the
  hands' dance sources and a grab switch, and the palette fold — the
  mechanisms only. **No preset is edited or added in this run** (owner,
  2026-10-14): the creative pass that uses all of this is the owner's,
  after the infrastructure lands.

Work the way plans 21, 22 and 23 were worked: numbered work packages, one
branch and PR each, an integration branch, a review pass, and a docs work
package per plan that records what was built. Sub-agents, one per WP, each
in its own git worktree off a verified base.

**Read first, in full:** `docs/plans/24-party-wishlist.md` (the owner's
intent and the F2 design decisions), then `docs/CHECKPOINT.md`,
`ARCHITECTURE.md` (§1, §2 and §3 are the contract you are changing),
`DECISIONS.md`, `DECISION-REGISTER.md`, `docs/plans/README.md`, and
`docs/plans/21-outputs-and-the-hands.md` as the model for the as-built docs.
The shared Claude Doc the wishlist file links to is the owner's working
plan; this prompt carries everything from it that these two plans need, so
you do not need to open it.

Code sites below are `file:line` as of `main` at `648cf83`
(`hyperspace-python/` there is identical to `6473fda`). Re-find them by
symbol if they have moved.

## Why these three first

Most of the wishlist items hang off these two refactors. The owner's
priority (2026-10-12): **the node-based render pipeline is high priority;
the device registry is a high-leverage idea.** Both start now, in parallel. The
node editor (plan 28) follows the render graph directly; the new devices
(wands, drums, lights, Kinect: plan 29) follow the registry. The party fixes
(plan 24) need no foundation and "run alongside as a small plan": they are
stream C here, so the next event gets them whatever the two refactors'
pace.

Plan numbers: the wishlist file said F2 = plan 25 and F1 = plan 26, but
plan 25 became the shared library (PRs #167/#168). So: **F2 is plan 26, F1
is plan 27**, the node editor is 28, the devices are 29. The wishlist file's
priority paragraph has been corrected to say so.

---

## The base

Base on `main` at `8f80b94` or later, and the final PR targets `main`.
Plan 25 (the shared library, PRs #167/#168) is merged there: `[library]
path` points the library at a cloud folder, `homegit` and `shared/` are
gone, and plan 25 took register row 109, hand checks 139–143 (group S)
and its README entry. Plan 27 touches `config.py`, `app.py` (`main`, the
close order) and the SYSTEM page, which plan 25 changed: read them as they
are on `main`, not as the surveys in this prompt describe them where the
two differ (the line numbers below are from `648cf83`, before plan 25).

Register rows start at **110**; hand checks start at **148**,
groups **U** (plan 24), **V** (plan 26) and **W** (plan 27), because group
**T**, 144–147, goes to the pad's checks that PR #161 left without numbers
(see "What landed since the wishlist was written"). Verify the base
before anything else, and re-check it immediately before each worktree is
cut.

---

## Stream A — plan 26, the render graph

### Where the frame is today

One frame runs in `Renderer._draw_frame` (`render.py:839`) in a fixed
order: the face picture (`:864`, face-aimed FX into a 1024² texture) → the
scene pass `draw_scene` (`:1419`: faces `:1514–1561`, then edges as six-vertex
quads `:1563–1589`, then point sprites `:1591–1606`, each painter-sorted
`:1480/:1527/:1593`) into `SceneTarget` (`:416`, **colour only, no depth**)
→ MSAA resolve → the cover mask → `lb.tick/pull` (`:875`) → the hands' own
pass `ghost.layer` (`:896–901`) → per distinct pipeline `_pipeline` (`:960`:
look-back composite `:970`, hands-through `:988`, FX chain `:991`) →
`lb.capture` from the **raw scene texture** (`:946`) → per output `_compose`
(`:994`: `fit` `:1020`, `_show` `:1046`, hands over `:1033`, readout `:1035`,
`dim_pass` `:1352`). `outputs.route` (`outputs.py:55`) picks one of three
pipelines, `SCENE / SCENE_HANDS / HANDS` (`:34`), per output's `Switches`
(`:40`). An output in another GL context gets a `Handoff` (`:109`) whose
five-step contract (`:116–131`) `Presenter.present` (`:320`) replays.

The shape reaches the GPU as 2D logical pixels: `geometry.project_h`
(`geometry.py:1009`) does `rotate4` (`:672`) → the 4D divide (`_to3` `:972`)
→ the yaw/pitch turntable (`_camera` `:988`) → an ad-hoc 3D divide
`CAM3 - 0.9*z1` (`:1023`) and `min(w,h)*0.30` (`:1025`). There is no 4×4
matrix and no z on the GPU: `FACE_VS` writes `z = 0` (`render.py:153`), the
line VAO is `"2f 1f"` (`:609`), the point VAO `"2f 1f 1f"` (`:617`).
`camera.zoom` / `camera.pan` are a 2D zoom of the finished picture
(`:1444–1447`) and zoom also scales the instance cell (`:1454`), the line
width (`:1491`) and the point radius (`:1594`). `camera.pan.x/y` are in
pixels, ±4000 (`params.py:927`), and presets store them.

The hands are a separate subsystem: `Ghost` (`ghost.py:1154`) builds a real
perspective camera in Leap mm, refitted every frame to the calibrated palm
box (`camera(box, m, aspect)` `:219`, `_perspective` `:201`, `_look` `:189`,
`stage_box` `:211`); draws spheres, tubes and a mesh (`Geometry` `:1050`,
`PARTS` `:1026`, `style_parts` `:1029`) opaque with depth and its own 4×
MSAA (`_make` `:1496`); and composites premultiplied at `ghost.alpha`
(`_lay` `:1413`, `COMPOSITE_FS` `:820`). `ghost.mirror` flips x in the Leap
basis (`basis` `:151`). The readout (guide, tether labels) is a second
texture that effects never bend (`:1361–1384`). There is no `ghost.camera`
param; the wishlist's phrase means this module function.

The FX chain: `FxState._scan` (`fx.py:217`) finds `shaders/fx/*.glsl`,
`declare` (`:391`) makes `fx.<file>.<key>` params (`fx.acid.mix` is
`{pre}.mix` at `:426`), `names()` (`:287`) orders by `@order`, `FxChain.run`
(`:620`) ping-pongs two textures. **Effects have no instances today**: one
spec per file, ids without an index. (The "instances" of plans 16/20 are
shape copies: `view.instances`, `render.inst_positions`.)

History: `Lookback.capture` (`lookback.py:726`) takes the scene texture;
`composite` (`:684`) lays echoes and the dream over the scene in the post
pass; `dream.layer` is a VGG/GoogLeNet layer index, not a render source.
The history never holds hands, FX or dim
(`tests/test_outputs.py:454`, `tests/test_render.py:650`).

Headless rendering exists: `render_offscreen` (`render.py:1642`),
module-scoped `moderngl.create_context(standalone=True)` fixtures in
`tests/test_render.py:23`, `test_outputs.py`, `test_fx.py`, `test_ghost.py`,
`test_lookback.py`, and `tools/preset_shots.py`'s `Stage` (`:175–240`),
which loads every `party-*` preset through the real `Presets` over a
`Router`, drives fake hands through the real `HandsIO`, and renders at
960×600 with `t_now` pinned. **There are no pixel goldens and no GPU timer
queries** (`Renderer.stats` `:561` counts passes; the panel footer shows an
fps EMA). `tests/golden/` holds the plan-00 geometry traces only.

Presets are `hyperspace.preset/2` (`preset.py:122`, `library.py:156`) with
sections `schema, name, note, values, routes, desk, macros, modules`
(`preset.py:4–9`); `load_doc` (`:265`) ignores unknown top-level keys;
`document` (`:371`) and `signature` (`:386`) write and compare them.

### The work packages

| WP | What | Mostly touches |
| --- | --- | --- |
| **A0** | Step 0: golden frames, GPU timing per pass, the naming rule | `tests/test_golden_frames.py` (new), `tests/golden/frames/`, `tools/golden_frames.py` (new), `render.py` (`stats`), `ui.py` (SYSTEM page) |
| **A1** | The graph in code: today's three pipelines as default graphs, pixel for pixel | `render.py`, a new `graph.py` (nodes, evaluation), `outputs.py` (`route`), `lookback.py`, `fx.py`, `ghost.py` (composite only) |
| **A2** | One camera: a shared 4×4, depth, `eye.*`, zoom/pan as the shape's world transform, the Leap calibration | `geometry.py`, `render.py` (shaders, VAOs, `draw_scene`), `view.py`, `params.py` (`camera.*`, `eye.*`), `ghost.py` (`camera`), `preset.py` (pan migration), `hands/` calibration (`hands.json`) |
| **A3** | The hands as a geometry node: in the scene or as a layer, composited anywhere; history as wiring | `ghost.py` → a geometry node, `graph.py`, `render.py`, `lookback.py` (capture from a node), `outputs.py` (`Switches.through` → graph wiring) |
| **A4** | The graph in the preset as JSON; node instances and the naming rule; the point-cloud geometry node | `preset.py`, `graph.py`, `params.py`, `library/presets/*.json`, `ui_*.py` (the OUTPUT / LOOKBACK pages that pick what is wired) |
| **A5** | Docs | as under "What the docs WPs must produce" |

Branches `plan-26-a0-golden`, `plan-26-a1-graph`, `plan-26-a2-camera`,
`plan-26-a3-hands-node`, `plan-26-a4-graph-json`, `plan-26-a5-docs`.

**Sequencing.** A0 first and alone; nothing in stream A merges before A0's
goldens are on the integration branch, because every later WP is judged
against them. A1 after A0. A2 and A3 both change `ghost.py` and the scene
pass: A2 then A3, in sequence. A4 after A3. A5 last. Stream A is therefore
serial; stream B runs beside it.

### A0 — step 0

The owner asked for three things before F2 step 1 (wishlist file
`:120–126`):

- **Golden frames.** For every factory preset (`preset.FACTORY_PRESETS`,
  23 files in `hyperspace/library/presets/`: the eight house moods, the
  nine `party-*`, `legacy6`, `lfo-breathe`, the four `hands-*`), every
  reachable output state: the `Switches` combinations
  `tests/test_outputs.py:461–463` already enumerates (scene × hands ×
  through), with hands present and absent through `tests/fake_hands.py`
  the way `tools/preset_shots.py` does it. A pipeline is not selectable
  on its own: `outputs.route` derives it from the switches, the preset's
  effects and whether a hand shows, so record what each preset actually
  reaches and skip nothing silently (the tool lists the states it
  recorded). Render at a fixed size (960×600 at dpr 1, and once at the
  1080p cap for one preset) with `t_now` pinned, the LFOs and analyzer at
  rest, and the preset's own look-back setting kept, after **8 frames** at
  `dt = 1/60` so the echoes exist; then store a frame hash plus a
  down-sampled PNG under `tests/golden/frames/`. Pin the dream off (the
  worker is not deterministic). The test compares the full-resolution
  frame **exactly** (every byte); the PNG is for a person. A tool,
  `tools/golden_frames.py [--record] [--only …]`, records and diffs, and
  writes a contact sheet of the differences under
  `docs/plans/assets/26-render-graph/`.
  **Where they are recorded:** on the Mac the gates run on (there is no
  CI). Each golden carries the `GL_RENDERER` string it was recorded on
  (`ctx.info`); on another renderer the test skips with a note that says
  which renderer the goldens expect, never fails and never passes
  vacuously. Re-record only what a WP changed, say so in the commit, and
  list each changed frame in that WP's PR body with the one reason it
  changed. **A golden that moves in A1 means A1 is wrong**; in A2–A4 a
  moved golden needs its reason.
- **GPU timing per pass.** `moderngl` query objects (`ctx.query(time=True)`)
  around each pass of `_draw_frame`, kept in `Renderer.stats` as a rolling
  median in ms per pass, shown on the SYSTEM page as one line per pass
  (`scene 1.2 · cover 0.1 · hands 0.4 · lookback 0.3 · fx 2.1 · compose 0.2`).
  Off, with a note, when the context has no timer queries.
  After A1 the lines are one per node.
- **The naming rule.** Written into `docs/ENGINEERING.md` and pinned by a
  test: the first instance of a node keeps today's ids (`fx.acid.mix`,
  `ghost.alpha`, `dream.mix`); only extra instances get an **instance
  marker inside the id** (`fx.acid.2.mix` or the like: choose one form and
  register it), never a new first segment, because the first segment is
  the group (`preset.part_of` splits on the first `.`) and decides whether
  the param is in a preset. No preset or binding ever needs migrating for
  a single-instance graph.

### A1 — the graph in code

`graph.py` (new, in the render stack: imports `moderngl`, `glsl` and its
sibling render modules only, never `params`, `routing`, `library`,
`preset`, `undo`, `control`): node classes with typed ports, and an
evaluator that runs them in dependency order each frame. The node kinds the
owner decided (wishlist file, "Render graph design decisions") are the
first four; the last three wrap what exists and are your call (register
them):

| Node | Takes | Makes |
| --- | --- | --- |
| **Geometry** (shape, hands, point cloud) | its params | draw calls in the shared camera; **no framebuffer of its own** |
| **Scene** | any number of geometries | one colour + depth target: solid geometry first, then the sorted see-through shape |
| **Layer** | one geometry | its own colour + depth target, usable before the FX, after them, in history, or on one output |
| **Composite** | two images | over, add, or depth-aware |
| **FX** | an image | the chain (`FxChain`) — one node per chain, the effects' order inside it as today |
| **History** | an image | the look-back capture, echoes and the dream (`Lookback`) |
| **Output** | an image | `fit`, flip, hands-over, readout, dim, as `_compose` does now |

In A1 the hands stay as they are (`Ghost.layer` is wrapped as a Layer node
with its own camera; A3 makes it a Geometry). Today's three pipelines
become three default graphs, built in code from an output's `Switches`, and
`Renderer._draw_frame` becomes "build or reuse the graph for this frame's
views, evaluate it". **A0's goldens pass unchanged**: every pixel of every
preset on every pipeline, with and without hands. Keep `Handoff` and
`Presenter` as they are: an Output node produces the same five-step
hand-off. Keep `Renderer.draw` / `draw_outputs` signatures so
`app._draw_render` and the tests' stubs do not change.

Evaluation order is dependency order, computed once when the graph changes,
not per frame. A node is evaluated once per frame even when two outputs
share it (today's "each distinct pipeline once", `:914–938`). The
per-node GPU timing from A0 attaches here.

**Name the node method `run` or `evaluate`, never `apply`.**
`tests/test_render.py::test_the_render_stack_imports_no_registry` bans any
call named `apply`, `modulate`, `snapshot` or `set_value` in `render.py`
(`:1598–1601`).

### A2 — one camera

The owner's decisions (wishlist file, "The shape's transform"):

- **Local motion is `rot.*`**, the six-plane 4D tumble (`rotate4`),
  unchanged.
- **World pose is `camera.yaw` / `camera.pitch`.** They already rotate the
  vertices after the tumble as a turntable about fixed axes (`_camera`), so
  they compose with `rot.*`. Ids unchanged; only their meaning is written
  down.
- **Scale and position are `camera.zoom` / `camera.pan`.** They become the
  shape's scale and position **in the world**, no longer a 2D zoom of the
  finished picture. The hands stay aligned with the performer; only the
  shape grows. A whole-frame 2D zoom can return later as an image node.
- **The real camera is new and fixed**, framed on the Leap box, with new
  ids `eye.*` (session group, not in a preset). `hands-orbit` then turns
  only the shape.
- **Lines and points** become quads expanded in the vertex shader with a
  real depth, so a hand can pass between edges. The shape layer's depth is
  the depth of its nearest visible surface (fragments above an alpha
  threshold).
- **Units.** A calibration maps Leap mm into shape units; it lives with the
  room settings in `hands.json` (`hands/core.py:124–125`, schema bump with a
  backup of the old file).

Build it as: keep 4D → 3D on the CPU (`_to3`), then 3D → clip in the vertex
shader with one shared 4×4 (`u_vp`, the same matrix `ghost.Geometry` already
takes at `ghost.py:1116`). `SceneTarget` gains a depth attachment. Express
today's divide (`CAM3 - 0.9*z1`, the 0.30 scale, y down) as the **default
`eye.*`** so that, with the default eye and `camera.zoom = 1`, `pan = 0`,
every vertex lands within half a logical pixel of where `project_h` put it.
Pin that with a test over every shape at the three golden view
configurations (`tests/golden/geometry/`), and keep `project` (`:715`) as
the parity oracle it is.

The goldens **will** move in A2 (sub-pixel positions, depth-tested overlap
instead of painter order where geometry crosses, line width no longer
scaling with zoom). Re-record them with the contact sheet in the PR, and
list what moved and why. The painter sort stays for the see-through shape
(solid-then-sorted, below); it is not replaced by the depth test.

`camera.pan` changes unit from pixels to world units (the shape's unit
circumradius; pick the range, register it). Migrate stored values at load
(`preset.py` step 0, beside `echo_seconds` `:164`): a `preset/2` pan in px
becomes world units through the default eye, so a saved preset looks the
same. The param's range and format (`params.py:927–928`, ±4000 "px")
change with it, and a routed pan maps its depth over the new range:
`hands-orbit` (`preset.hands_orbit_routes`) pushes `hand:left.x/z` onto
`camera.pan.x/y` and `hand:left.y` onto `camera.zoom`, so pick the range
such that a hand across the box pans about as far as it does today, and
make the hand check judge exactly that. Bump the preset schema only if you need to;
`load_doc` ignores unknown keys, so a new `camera.pan` unit can also be
marked by a key. Say which you chose in the register.

`ghost.mirror` keeps its meaning (the hands mirrored in the Leap basis); the
output flips (`Switches.flip_x/y`, plan 23 WP1) are untouched.

### A3 — the hands as a geometry node

Decision (owner, 2026-10-12): **any geometry, the hands included, can be
drawn either inside the scene or as its own buffer that the pipeline
composites anywhere, and the same hands can do both at once** (in the
scene on the projector, a clean layer on the glass).

- `Ghost`'s parts (`hands_parts`, `joints_parts`, `palms_parts`,
  `cage_parts`, `marionette_parts`) become a **Hands geometry node** drawing
  in the shared camera from A2. `ghost.style`, `ghost.alpha`, `ghost.guide`,
  `ghost.tethers`, `ghost.on`, `ghost.mirror` keep their ids and meanings
  (the naming rule: the first hands node keeps today's ids).
- **In the scene:** solid geometry is drawn first, then the sorted
  see-through shape (alpha-over in painter order, `render.py:11`). A hand in
  front of or behind the shape reads correctly. Order-independent
  transparency is **deferred**: until then, hands inside the scene have
  `ghost.alpha` at 1, or are sorted as one see-through object. Pick one,
  register it.
- **As a layer:** a Layer node with its own colour + depth target, and a
  **Composite** node that merges it with over, add, or **depth-aware**
  blending, so a separate hands layer can still be hidden by the shape.
  Today's "through" (`Switches.through`, `Renderer._pipeline` `:988`) is the
  layer composited before the FX; "over" is the layer composited at the
  output. Both stay reachable from the OUTPUT page's existing switches,
  which now set the default graph's wiring.
- **The readout** (guide, tether labels) stays its own texture laid on at
  the output, never through effects (register row 80 holds).
- **History becomes wiring.** The History node captures from a chosen
  image: the scene with or without the hands layer. The test "the history
  never holds hands, FX or dim" becomes "the history holds what it is
  wired to, and the default graph wires it as today".
- Each output's `Switches` (`scene`, `hands`, `through`) keep their
  meaning as the three knobs on the default graph. Register rows 81–84
  hold.

Goldens: the default graphs must still match A2's recordings exactly. New
cases (hands in the scene, a depth-aware composite) get new goldens.

### A4 — the graph in the preset

- A `graph` section in the preset document (`preset.py` `document`,
  `load_doc`, `signature`): plain JSON, git-diffable, listing nodes by kind
  and instance, their wiring, and nothing that is already a param. Absent
  → the default graph, so every existing preset loads unchanged and
  `signature` sees no dirt. A preset that carries a graph loads it; an
  unknown node kind is a note and the default graph, never a crash.
- **Node instances and the naming rule** (A0): a second instance of a node
  gets prefixed ids and its own registry params; the first keeps today's.
  Two acid effects in one chain, or two hands layers (one in the scene, one
  over the glass), are the proof.
- **The point-cloud geometry node:** draws a point-cloud source (stream B's
  B4 contract: a GPU buffer of 3D points plus a timestamp) as points, in
  the shared camera, from a recorded cloud file so no sensor is needed.
  This is the one cross-stream item: it is its own small WP,
  `plan-26-a4b-points`, cut from the integration branch once B4 and A3
  are both in.
- The OUTPUT and LOOKBACK pages show the wiring they set in words
  (`hands: in the scene · through FX · over`), no editor yet (plan 28).
- **The proof preset is a fixture, not a factory preset.**
  `tests/fixtures/presets/hands-lines.json`, loaded through a scratch
  library in the test, carries a `graph` section that puts the hands in
  the scene as lines through the acid effect with the look-back wired to
  capture them; it gets its own golden, recorded from the fixture. Every
  factory preset file stays byte-identical, so no existing golden moves
  because of A4.

**Acceptance for stream A:** a preset can say "hands as lines, through the
acid FX, with tracers" in data, not code; every factory preset renders
pixel-identical to the goldens recorded on its WP; the SYSTEM page shows a
time per node; `tests/test_render.py`'s and `test_outputs.py`'s boundary
tests pass untouched, and the one history test A3 rewrites is the only
test in `test_outputs.py` that changes.

---

## Stream B — plan 27, the device registry

### The brief, in the owner's working plan (2026-10-12)

The wishlist file records F1 only through "Controllers as nodes"; the F1
brief itself is in the shared doc, quoted here so it is in the repo:

> **Today.** The app opens exactly one MIDI port with one profile, the
> APC40. Continuous sources are a fixed list (lane, ext, lfo, hand).
> Buttons are hard-wired to the keyboard and the Xbox pad. A drum kit, a
> wand or a second MIDI device each means editing `app.py`.
>
> **Build.** A Device interface: open, poll each frame, close. Each device
> publishes its sources (continuous axes, and discrete hits with
> velocity), their names and rest values, and a connected/lost status for
> the panel. Devices are listed in `config.toml` (`[[devices]]`) and come
> and go without a relaunch. Several MIDI ports at once, each with its own
> profile (APC40, generic pads, generic CC). Source schemes come from the
> registry, not a fixed tuple. Examples: `wand:2.tilt`, `drum:snare` (a hit
> plus its velocity), `osc:/x`, `kinect:1.centroid`. Sinks get the same
> treatment. A sink takes param values out to the world: the existing DAW
> bridge, DMX universes, smart bulbs. Routing a param to a light uses the
> same table and Learn flow as routing a hand to a param. A point-cloud
> source type: a GPU buffer of 3D points plus a timestamp, not a scalar
> lane. This is how the app starts to "speak point clouds" before any
> sensor is bought.
>
> **Done when** the APC40, the gamepad and the hands run on the registry,
> and an OSC device can be added with no edit to `app.py`.

(The example source strings above are the doc's; B1 below fixes the
grammar so a role contains no `:`.)

### Where the devices are today

`app.main` (`app.py:1078`) opens each adapter by hand behind its own config
gate: `_open_midi` `:519` (`[midi] enabled`, one `MidiIO`, one port, one
profile), `_open_bridge` `:537`, `_open_hands` `:563`, `_open_dream` `:597`,
`_open_pad` `:626` (no try/except; `Pad` never raises). `Host` (`:824`)
has one field per adapter (`pad :849`, `midi_io :850`, `hands_io :851`,
`bridge_io :852`, `dream_io :853`) and `adapters` (`:862`) lists them in
shutdown order — **the pad is not in it and `Pad` has no `close()`**; its
libusb reader is a daemon thread stopped only by `atexit`
(`gamepad.py:153–193`). `frame` (`:869`) polls them in a fixed order that
`tests/test_app_boundary.py::test_the_frame_runs_in_the_documented_order`
(`:317`, `ORDER :297`) pins by stub name. Hot-reload targets are listed per
adapter at `:1252–1257`.

Sources are fixed tuples: `routing.LANE_SCHEMES = ("lane", "ext", "lfo",
"hand", "axis")` (`routing.py:278`, enforced in `Binding.is_performer :575`,
`to_json :619`, `describe :656`, `migrate_v1 :796`, `Bindings._check :1748`,
`replace_owner :1834`, `preset.py:297`), beside `learn.PAD_SCHEMES`
(`learn.py:83`);
`ui_routing.SOURCE_ORDER = ("hand", "axis", "lfo", "ext")` (`:490`, a scheme
not in it is never offered); `learn.WANTS = ("desk", "hand:left",
"hand:right", "pad")` (`learn.py:82`) with the matching menu in
`ui.py:675–697`. `Router.feed` (`routing.py:2144`) stores any scheme
unchecked; the Router's source registry is plain dicts the adapters fill:
`feeds :1893`, `labels :1894`, `gates :1898`, `rests :1903`, `names :1917`,
`lane(source) :1932` (−1 = dormant), `address :1958`, `rest_of :2172`.

Publishers today: `LFOs.publish` (`lfo.py:244`: feed, labels, rests);
`HandsIO._publish` (`hands/core.py:1099`: labels, gates, names, rests) and
`poll` (`:1124`, feeds `hand` or `None`); the pad's axes are published by
the Router itself (`_publish_axes :2118`, a lazy `gamepad` import) and its
buttons are rows (`Router.pad :2070`); the bridge feeds `ext` with **no
labels or rests**, so the UI hard-codes `N_EXT = 16` (`ui_routing.py:133`);
the `lane` scheme is never fed — `modulate` reads `analyzer.lanes / CEIL`
directly (`:2237`). **MIDI is never a feed source**: every message is a
discrete scene-setter applied straight to a base (`midi._apply :595`).

The APC40 is a duck-typed profile module (`apc40.py`: `PORT_MATCH :70`,
`enter/leave :103/:107`, `is_relative :126`, `ring_setup :130`,
`feedback_for :137`, `control_name :183`, `LAYOUT :310`, `DEFAULT_MAP
:416`), chosen by `midi.PROFILES = {"apc40": apc40}` (`midi.py:125`) —
and the `"profile"` field in `bindings.json` wins over `[midi] profile`
(`:281`). MIDI sources carry **no device or port identity** (`cc:<ch>:<n>`,
`note:<ch>:<n>`, `pitch:<ch>`; `Binding.midi_source :578`); `dispatch`,
`overlaps` and `control` key on (kind, channel, number). The **SHIFT latch
lives in routing, not midi or apc40**: `SHIFT_SOURCE :290`, `desk.shift` in
`register_desk :1162`, one `Bindings.layer` for the whole table
(`:1345–1350`, `dispatch :1609`, `set_layer :1629`). Two desks would share
one layer. APC40 is also hard-wired in `routing.factory_desk :1075`, the
remap tables `:343–435`, `preset.fresh_desk :139` / `device_knob :872`,
`ui.py:569/:611`, `ui_routing.control_name :995`, and all of `ui_desk.py`.

`HandsIO` is a source and a sink at once (DAW MIDI out inside `poll`,
`_open :1308` / `_send :1352`), and a second consumer reads it: the ghost
renderer (`app.py:1184`). `hands/core.py`, `signal.py`, `tape.py` import
nothing from the package and `tests/test_hands_boundary.py` holds that
(`:30`, `:40`, and `:48`: `HandsIO` runs with no host and gives 22 lanes).
Its status is a string on `LeapSource.status` (`hands/core.py:771–877`),
shown on the HANDS page (`hands/panel.py:313`), not SYSTEM. The bridge
(`bridge.py:144`) is today's one sink: `transmit :248` sends lanes and
`param:<id>` norms; `receive :218` feeds `ext`; it uses `midi.Ports`
(`:167`, so it imports midi, apc40 and mido).

`config.load` (`config.py:324–332`) accepts only dict top-level sections:
**a top-level `[[devices]]` parses to a list and lands in `cfg["error"]`**.
The existing list-of-tables, `[[output.screens]]`, is nested under
`[output]` and checked per entry by `_screen :215` / `_screens :249`. The
SYSTEM page (`ui.py:1858`) has `_midi_status :1989`, `_bridge_status
:1973`, no pad status and no hands line. `hotreload.MODULES` (`:56–62`) is
in import order and two tests pin it (`tests/test_hotreload.py:218, :272`).
`tests/test_app_boundary.py:27` lists the gated modules (`midi`, `bridge`,
`dream`, `homegit`, `leap`, `torch`; on the plan 25 base `homegit` is gone
from it and from `hotreload.MODULES`); `test_bridge.py:425` asserts the core
never imports `bridge`. **There is no OSC support and no `python-osc`
dependency.**

### The work packages

| WP | What | Mostly touches |
| --- | --- | --- |
| **B1** | The `Device` interface and the registry; `[[devices]]`; one status line per device; `Host.devices` | `devices.py` (new), `config.py`, `app.py` (`main`, `Host`, `frame`, close order, hot reload), `ui.py` (SYSTEM) |
| **B2** | The existing inputs on the registry: several MIDI ports with their own profiles, the pad, the hands; schemes from the registry | `midi.py`, `apc40.py`, `gamepad.py`, `hands/panel.py` (+ a wrapper outside `hands/core.py`), `routing.py`, `learn.py`, `ui_routing.py`, `ui.py` |
| **B3** | Sinks: the bridge and the hands' DAW out as sinks; a param routed to a sink through the table and Learn | `devices.py`, `bridge.py`, `hands/`, `routing.py`, `learn.py`, `ui_routing.py` |
| **B4** | An OSC device with no edit to `app.py`; the point-cloud source type and a recorded-cloud device | `osc.py` (new, gated), `devices.py`, `pyproject.toml` (`python-osc`), `tests/fixtures/clouds/` |
| **B5** | Docs | as under "What the docs WPs must produce" |

Branches `plan-27-b1-registry`, `plan-27-b2-inputs`, `plan-27-b3-sinks`,
`plan-27-b4-osc-clouds`, `plan-27-b5-docs`.

**Sequencing.** B1 first. B2 after B1. B3 and B4 may run in parallel after
B2: B3 touches `routing.py`/`learn.py` and B4 touches neither, and both
add to `devices.py` — B1 owns the protocol and the registry, B3 adds only
the sink half, B4 adds only new kinds, so their diffs do not overlap.
B5 last. B4's
point-cloud contract is what stream A's A4 consumes: land B4's contract
(`devices.PointCloud`, the file format, the recorded-cloud device) early in
B4 and say so on the integration branch.

### B1 — the interface and the registry

- `devices.py`: a `Device` protocol — `open()`, `poll(dt, now)`, `close()`,
  `status` (`connected`, `lost`, `error: …`, `off`), `name` (the role, below),
  `sources` (continuous axes: name, label, rest, bipolar; hits: name, label,
  with velocity), `feed(router)` (publishes its vectors, labels, rests,
  gates, names under its own scheme), and `learn(learn)` (offers its moved
  axis or pressed button to an armed Learn, as `gamepad.learn_from` and
  `HandsIO._learn` do now). Discrete controls (buttons, pads, MIDI) stay
  scene-setters: a device delivers them as rows through the table, as
  `Router.keys` / `Router.pad` / `MidiIO._handle` do today. Keep the two
  signal kinds distinct — **values** (axes, faders) and **triggers** (hits,
  buttons) — because the node editor (plan 28) crosses them only through
  envelope and threshold nodes.
- `DeviceRegistry`: owns the list, opens each behind its own config entry,
  polls them in order each frame, retries a lost device on the `Ports`
  schedule (`midi.py:164`, fast then slow), and never lets one device's
  exception stop the frame (a note, as `_open_hands` does, and `status`).
  It is the one importer of every adapter module, each imported lazily
  under its entry, so `tests/test_app_boundary.py::test_importing_app_leaves_every_gated_adapter_unimported`
  keeps passing with `osc` and `pythonosc` added to its `gated` list.
- **Roles, not serials** (owner, 2026-10-12): a device entry has a `role`
  (`apc40`, `pad`, `leap`, `wand1`, `phone`) and the role is what source
  strings and rows name. **The role is the scheme**: a continuous source
  is `<role>:<name>` (`phone:x`, `wand1:tilt`), so `Router.feeds`, `labels`,
  `names` and `rests`, which are keyed by scheme (`routing.py:1893–1917`),
  hold one vector per device and `_resolve_lane`'s split at the first `:`
  (`:1951`) still works. A role therefore contains no `:`; `hand`, `axis`,
  `lane`, `lfo`, `ext` and the MIDI schemes stay the roles of today's
  devices so every existing row is unchanged. The session maps roles to
  physical devices (`port`, `usb`, `host:port`). A missing device shows
  as `lost` and its rows wait, as dormant routes do today (`Router.lane`
  → −1).
- **A device is the node class** (owner, 2026-10-12, for plan 28): each
  source and each sink a device publishes is a **port** — name, label,
  kind (value or trigger), rest, bipolar, and a group for collapsing (the
  APC40's hundred controls, the hands' forty sources) — so the node editor
  can draw a device with no second description of it.
- `[[devices]]` in `config.toml`: `role`, `kind` (`midi`, `midi-out`,
  `gamepad`, `hands`, `bridge`, `osc`, `cloud`), `enabled`, and the kind's
  own keys (the keys the `[midi]`, `[gamepad]`, `[hands]` and `[bridge]`
  tables hold today, docstring `config.py:1–147`). `config.load` gets a branch for a
  top-level list-of-tables, checked per entry like `_screen`. **The old
  tables keep working**: a config with `[midi]`/`[gamepad]`/`[hands]`/
  `[bridge]` and no `[[devices]]` is translated to the equivalent entries
  at load with one note per table, so no rig config breaks. Devices come
  and go without a relaunch, by two mechanisms: a lost device is retried
  on the `Ports` schedule and comes back with its feedback; and the
  registry watches `config.toml`'s mtime (every 30 frames, as the shaders
  are watched — `hotreload.py` watches only `.py` files today, and the
  config is read once in `app.main`, `app.py:1081`) and re-reads **only
  the `[[devices]]` list**, closing what left and opening what arrived. A
  bad edit is a note and the old list stands.
- `Host.devices` replaces the per-adapter fields; `Host.adapters` becomes
  the registry's close list (now including the pad, which gets a real
  `close()` that stops its reader thread). `frame` polls devices where the
  adapters are polled now: scene-setting devices in the step-2/3 slot,
  feeders in the step-6 slot, sinks after `reg.apply`. **Rewrite `ORDER` in
  `tests/test_app_boundary.py` consciously** to "devices poll in the
  scene-setter slot, sources feed in the feed slot, sinks run after apply",
  and update ARCHITECTURE §2's table to match in B5. The hot-reload swap
  targets (`app.py:1252–1257`) come from the registry.
- SYSTEM page: one line per device — `role · kind · status · n sources ·
  last` — replacing `_midi_status` and `_bridge_status`, plus the hands
  line it never had. The HANDS page keeps its own status.

### B2 — the existing inputs on the registry

- **Several MIDI ports, each with its own profile.** `MidiIO` becomes a
  device whose profile is per entry (`profile = "apc40" | "generic"`), and
  a `generic` profile (plain CC/note/pitch, no feedback) ships so a second
  controller works with no profile code. Source strings gain the role when
  there is more than one MIDI device: an unqualified `cc:<ch>:<n>` means
  the **first MIDI role listed** (today's `bindings.json` and every preset
  keep working, and a rig whose only desk is a generic one still maps),
  and a second device's rows are `cc@<role>:<ch>:<n>` (or a form you
  choose, as long as the qualifier does not add a `:`; register it). `Binding.midi_source`, `dispatch`, `overlaps`
  and `control` learn the qualifier. `bindings.json`'s top-level
  `"profile"` becomes the `apc40` role's profile and stops overriding the
  config (`midi.py:281`).
- **The SHIFT latch per device.** `Bindings.layer` becomes per role; the
  `desk.shift` param is the `apc40` role's latch (ids unchanged). A second
  desk has its own, or none. The wishlist's "APC40 is two nodes" (plan 28)
  needs exactly this: a device with a mode switch presents as one node per
  mode, so model it as **a device may expose layers**, and the table knows
  which role's layer a row belongs to — no more than that in this plan;
  the two-node presentation is plan 28's. Three rules the layer model
  must keep (owner, 2026-10-12): the invariant controls (SHIFT, the
  crossfader, the bank pads, the transport, tap) work on both layers; a
  press and its release belong to the layer that was up when it went down
  (D12); soft pickup re-engages per control when the latch flips (D7).
  D1 and D4–D6 hold.
- **The pad** is a device: `Pad` gets `open`/`close`/`status`; the axes'
  labels and rests come from the device (`_publish_axes` leaves the
  Router); the camera job that `app.frame` inlines at `:912–951` moves to
  the pad device's `poll` (it needs `router.claimed("axis")` and the
  params' `nudge`/`scale`, so it takes the router and registry as
  arguments, as `HandsIO.poll` takes the router).
- **The hands.** `hands/core.py` stays liftable: do not import `devices`
  there. The device is a thin wrapper that owns a `HandsIO` and satisfies
  the protocol, in a new `hands/device.py`; `tests/test_hands_boundary.py`'s
  host-reaching list becomes `["device.py", "panel.py"]` and nothing else
  in that test changes. The ghost renderer (A3's hands node) keeps reading
  `HandsIO` through `renderer.ghost.source`; the registry hands it over.
- **Schemes from the registry.** `LANE_SCHEMES`, `SOURCE_ORDER` and
  `learn.WANTS` stop being tuples: the Router asks the registry which
  schemes are continuous and in what order to offer them; Learn asks it
  what can be armed (`desk` for every MIDI role, `hand:left/right`, `pad`,
  and each new device's role). `lane` (the analyzer) and `lfo` stay
  built-in schemes the registry lists first. Routing still imports nothing
  above it: the registry object arrives as an argument, and
  `tests/test_routing_boundary.py`'s `ABOVE` / `LAZY` sets stay as they
  are (add `devices` to neither; if routing must import a protocol, put
  the protocol in a leaf module and name it in the test).
- `ui_desk.py` stays APC40-only in this plan: it draws the `apc40` role's
  layout. Note it as the thing plan 29's generic desk replaces.

### B3 — sinks

- A sink is a device that reads **effective** param values (or lanes) after
  `reg.apply` and sends them out: `sinks` on the protocol, `send(reg,
  analyzer)` in the slot after apply. The bridge's `transmit` is the first
  sink; its `receive` stays a source (`ext`), so the bridge is one device
  with both halves. The hands' DAW out (`HandsIO._send`) becomes a sink
  entry (`kind = "midi-out"`, role `hands-daw`), so `hands/core.py` no
  longer opens a MIDI port — but keep the `out` setting working by
  translating it to that entry at load, as B1 does for the old tables.
- **A param routed to a sink uses the same table and Learn flow as a hand
  routed to a param.** Add a sink row: a `Binding` whose source is a param
  (`param:<id>`) or a lane (`lane:<n>`) and whose target is a sink port
  (`<role>:<channel>`), saved in the **session** (sinks are rig, D1/D9). The
  bridge's `send` list (`config.py:176`) becomes those rows at load. Learn
  can arm a sink port through the existing right-click Learn menu on a
  param (`Learn → sink → <role>:<channel>`), no new page or picker; the
  row appears as the others do, with the referee rules unchanged (a sink
  row is not a performer and never asks Replace / Keep). Publish the
  bridge's `ext` labels and rests so `N_EXT` leaves `ui_routing.py`.

### B4 — OSC and point clouds

- **OSC device** (`osc.py`, gated, `python-osc` added to `pyproject.toml`):
  a UDP server on `host:port` from its entry; `axes = ["/x", "/y", …]`
  become continuous sources (`osc:<role>.<name>`, rest from the entry), and
  `hits = ["/hit"]` become triggers with velocity (the message's first
  float). It feeds under its scheme, publishes labels and rests, reports
  `lost` when nothing has arrived for a timeout. **The acceptance for the
  whole plan is adding this device with no edit to `app.py`**: the only
  code that names it is `osc.py` itself and the registry's kind table.
  Test it with `pythonosc`'s client in-process, no network assumptions
  beyond localhost.
- **Point-cloud source type** (`devices.PointCloud`): a GPU-ready buffer
  of N×3 float32 points plus a timestamp and a frame id, a `bounds`, and
  an optional N×3 colour; a device publishes it on the registry under its
  role (`cloud:<role>`), not through the Router (it is not a scalar lane).
  A `cloud` device kind reads a recorded file (`tests/fixtures/clouds/`,
  a small `.npz` sequence you generate deterministically) at its own
  rate, so the type is exercised with no sensor. Stream A's point-cloud
  geometry node (A4) draws it. The Kinect and the live sensors are plan 29.

**Acceptance for stream B:** the APC40, the pad and the hands run on the
registry with `bindings.json` and every preset unchanged; a second MIDI
controller with the `generic` profile maps on the desk's Learn with no
code; the bridge's `send` list is sink rows; the OSC device is added by a
`[[devices]]` entry alone; a cloud device publishes frames the A4 node
draws; the boundary tests pass with the conscious changes above and no
others.

---

## Stream C — plan 24, the party fixes

The owner's wishlist items that need no foundation, from the wishlist file
("The wishlist as the owner meant it") and the working plan's sections
"The desk: APC40 and faders", "Hands: into the scene" (H1, H2) and "Palette
fold". Three independent lines inside the stream: the desk (C1 → C2 → C3),
the hands (C4 → C5), the palette (C6), then docs (C7).

### Where it is today

**The desk.** `apc40.DEFAULT_MAP` (`apc40.py:416`): the device knobs
D1–D8 are the preset layer's `SCENE` (`:420`) and the SHIFT layer's
`band.sel.*` (`:418`); the track faders are **invariant** (`:432–435`:
`band.{i}.post` on faders 1–6, `master.dyn` and `master.trim` on 7–8,
`master.gain` on the MASTER fader); the crossfader is the master dim. The
render toggles (points, lines, faces, rotate) are preset-layer rows, so
they go dark under SHIFT and every preset load rewrites them (the wishlist
file cites `apc40.py:469`). Invariance is a table property (`layer=None`,
`routing.invariant_rows :1568`), not a profile one. Saving from the desk:
`Param.held` (`params.py:166`) is what a held `set` button does;
`Project.save_into` (`library.py:801`) saves the live state into an
**empty** slot and `save_new` (`:813`) into the next free one; `midi.HOLD_S`
(`midi.py:132`) and `_fire_holds` (`:557`) time the hold; the clip-stop row
has been free since PR #158 (`routing.py:384` drops its old rows). The
standing decision (owner, 2026-10-09, `DECISIONS.md` "Presets and the
desk"): **the desk never overwrites a preset**; a held filled pad only
loads. Desk Learn: `ui_desk.click` (`ui_desk.py:293`), `Learn.pick` /
`map_picked` (`learn.py:270/:278`), `Panel._ctx_pick` (`ui.py:549`); the
pick offers the whole registry. Module-preset groups (`band`, `dream`,
`fx`; `Library.kind` `library.py:1383`) are the mechanism a `desk` group of
templates can reuse, and with plan 25 a user's templates live in the shared
library folder. The factory party presets' desk sections come from code
(`preset.knob_desk`, register row 107: "the house presets' routes are
generated from code").

**Mix params that exist:** `view.pattern_mix` (`params.py:858`),
`dream.mix` (`:950`), `ghost.alpha` (`ghost.py:116`), `fx.<name>.mix`
(`fx.py:426`), `view.bright` (`:816`). **Missing:** a lines opacity and a
points opacity (`draw_scene` derives the edge alpha from `bright · dens`
at `render.py:1484` and the point alpha at `:1591–1606`).

**The hands.** Twelve axes (`hands/core.py:162` `DEFAULT_DOFS` × two
sides), presence and eight pinch switches, 22 lanes (`addresses()` `:917`,
`Layout` `:931`, pinned at 22 by `tests/test_hands_boundary.py:48`). The
fingertip is `tip()` (`:203`). `position` is one of the two performer ops
(`routing.MOD_OPS :279`); a pinch switch gates a row (`when`, `:478`). The
party presets are composed with six DOF only and no pinch dependence
(`tests/test_plan12_presets.py`, owner's row). Each output's `hands`
switch already defaults on (`config.py:194`), so "hands on the main
projection by default" is a line in the rig's `config.toml`, not code.

**The palette.** There is no colour pass after the effects. The FX
mechanism (`fx.py`: a `shaders/fx/*.glsl` file with `// @label|order|…`
and `uniform float|int u_x; // @param …` lines becomes `fx.<file>.*`
params, modulatable, saved in presets, hot-reloaded; `@order` places it in
the chain; module presets in `library/fx/` are saved settings) already
gives a single shader pass everything the fold needs: a knob on the desk,
a hand, an LFO or a band on any of its params, and named saved palettes.

### The work packages

| WP | What | Mostly touches |
| --- | --- | --- |
| **C1** | The desk you can trust: the two-handed save, every load relights the whole desk, the render toggles on both layers, a desk event log | `midi.py` (`_handle`, `_fire_holds`, `redraw`), `apc40.py` (`DEFAULT_MAP`), `routing.py` (`remap_factory`), `library.py` (`save_into` on a filled slot: a new preset into the slot, the old one kept), `params.py`, `ui.py` (the log) |
| **C2** | The faders freed: S1–S8 preset-layer targets, band post/dyn/trim on the SHIFT faders, a mix param wherever a layer lacks one | `apc40.py`, `preset.py` (`knob_desk`, `fresh_desk`), `params.py`, `render.py` (two alpha lines in `draw_scene`) |
| **C3** | Making every preset's desk interesting: `tools/desk_coverage.py` and its committed report, desk templates as a `desk` module-preset group, click-to-map ranked by the params the preset uses | `tools/desk_coverage.py` (new), `tests/test_desk_coverage.py` (new), `library.py` (the group), `preset.py`, `ui_desk.py`, `learn.py` |
| **C4** | Inputs that reward dancing (H2): `hand:*.curl.<finger>`, `hand:*.spread`, `hand:*.energy`, `hands:gap`, `hands:twist`, `hand:*.flick` as routable sources | `hands/core.py`, `hands/signal.py`, `hands/panel.py` |
| **C5** | Cause and effect (H1): the `grab` switch as a source; hands on the projector in the rig config | `hands/signal.py`, `hands/core.py` (the grab switch), `config.toml.rig` |
| **C6** | The palette fold as an effect: `shaders/fx/palette.glsl`, its params, a gradient-map mode, saved palettes | `shaders/fx/palette.glsl` (new), `library/fx/` (two named palettes), `fx.py` only if a `@param` form is missing |
| **C7** | Docs | as under "What the docs WPs must produce" |

Branches `plan-24-c1-desk-trust`, `plan-24-c2-faders`, `plan-24-c3-coverage`,
`plan-24-c4-dance-sources`, `plan-24-c5-grab`, `plan-24-c6-palette`,
`plan-24-c7-docs`.

**Sequencing.** C1 → C2 → C3 in sequence (one desk map). C4 → C5 in
sequence (C5's grab needs C4's curl). C6 alone, any time. C1, C4 and C6
may all start on day one. C7 last. **C1 lands before B2 cuts its worktree**: B2 turns `MidiIO` into a
device and must carry C1's save and relight with it, not re-do them.

### C1 — the desk you can trust

What went wrong at the party, and the fix (working plan, "What went wrong,
and why"):

- **Hold-to-save was unreliable.** The pad's press loads first; the hold
  timer starts after it; a filled slot can never be saved over; a short
  hold does nothing. Fix: **a two-handed save** — hold a dedicated SAVE
  button, tap a pad; it saves into any slot, filled ones included; the
  pad blinks to confirm. **No preset is ever overwritten or trashed from
  the desk** (owner, 2026-10-09 and again 2026-10-14: "overwritten presets
  should not go in the trash"). On a filled pad the save lands as a **new
  preset** (`TRIP 2`, named as `save_new` names them) and the slot points
  at it; the old preset keeps its file and stays in the list, unpadded,
  exactly as "free this pad (keeps the preset)" leaves it. On an empty
  pad it is #158's save. `Project.save_into` grows that one case; the
  trash is untouched. The SAVE button is **track 8's clip-stop** (the
  working plan's open question; the row is free since #158; register it).
  Keep #158's hold-on-an-empty-pad save beside it (the pad's `START` was
  unbound on 2026-10-14, so the desk is the only place with a hold-save).
  The 2026-10-09 row "the desk never overwrites a preset" **stands**; its
  text gains the two-handed save.
- **Load felt inconsistent.** Tied to the save confusion, plus loads that
  release only the faders whose param they moved (`MidiIO.redraw`, register
  row 44). Fix: **every load relights the whole desk** from the new
  preset, and a **desk event log** on the SYSTEM page (the last twenty
  desk events: press, what it did, which layer) so the owner can see what
  a press did.
- **The render toggles acted inconsistently.** Points, lines, faces and
  rotate live on the preset layer only, so they go dark under SHIFT and a
  load rewrites them. Fix: **invariant rows** (same on both layers, D6's
  list grows by four) whose **LEDs always show the live state**.

### C2 — the faders freed

Owner's decisions (working plan, "Faders"):

- The **master fader stays audio drive**; the **crossfader stays the
  master dim**.
- **Track faders S1–S8 become preset-layer targets**, bound by each
  preset's desk like the knobs. **No global defaults are inherited**; a
  preset with no fader rows leaves them dark. **No auto-suggested fill.**
- The band post-drive, dyn and trim **move to the SHIFT-layer faders**, so
  the audio is one latch away (the working plan's open question "is that
  acceptable, or the knobs?": build it on the faders, register it). Soft
  pickup (D7) already handles the jump between layers. This amends D6.
- To give the faders something worth moving, **every layer and effect
  gets a mix or opacity param where it lacks one**: a lines opacity and a
  points opacity (two lines in `draw_scene`, the fewest you can: stream
  A's A2 rewrites that function, so keep your diff small and expect the
  overlap at integration); the pattern, the hands, the dream and each FX
  have theirs already.
- **No preset gets fader rows in this run.** The faders stay dark on
  every factory preset until the owner authors the sets after the
  infrastructure lands. A test proves the mechanism: a fixture preset
  with fader rows, loaded through a scratch library, lights S1–S8 and the
  rows round-trip through save and load.

### C3 — every preset's desk interesting

- **Coverage report** `tools/desk_coverage.py`: a table of preset × control,
  each cell `mapped`, `dark` or `dead` (mapped to a param the preset cannot
  show, such as a pattern knob with faces off). It runs in the tests and
  its output is committed at `docs/plans/assets/24-party-fixes/desk-coverage.md`,
  so a diff shows coverage going up or down; the test regenerates it
  deterministically and fails when the committed file is stale.
  The owner's bar — **at most 4 dark or dead controls on the preset
  layer** of every factory and party preset — is for the authoring pass
  that follows this run. Here the report is built and its numbers
  reported; **no preset is remapped to meet it**.
- **Desk templates**: named binding sets stored as their own JSON — a
  `desk` module-preset group (`hyperspace/library/desk/` for factory ones,
  the library folder for the owner's, so plan 25 shares them). A preset's
  desk is a template plus its own overrides, so one fix lands in every
  preset that uses it. The preset file records the template's name and
  the overrides; a preset with a plain desk section loads as today. **The
  mechanism only**: the factory `desk/` folder ships empty, the proof is a
  fixture template under `tests/fixtures/`, and no preset's desk section
  changes. The owner names the templates (`shape`, `fx`, `dream`, `hands`
  were the plan's examples) in the authoring pass.
- **Faster mapping at the screen**: a click on a control on the on-screen
  desk offers the params this preset uses first, ranked, then the rest —
  not the whole registry in one list (`ui_desk.click`, `Learn.pick`).

### C4 — inputs that reward dancing (H2)

Owner (2026-10-12): **the twelve axes stay**; these are added beside
them, each routable like any other hand source, in `hands/core.py` (which
stays liftable), with `signal.py` shaping them:

| Source | What it measures |
| --- | --- |
| `hand:*.curl.<finger>` | how bent each finger is (10 values) |
| `hand:*.spread` | how far the fingers fan out |
| `hand:*.energy` | smoothed speed of the whole hand and fingers |
| `hands:gap` | distance between the two palms |
| `hands:twist` | relative rotation of one hand to the other |
| `hand:*.flick` | a hit event on a sharp flick, with strength (a trigger: stream B's B1 names the two signal kinds; until B2 lands, a flick is a lane that spikes and decays) |

`hands:` is a new two-hand scheme with its own rests. The lane count
changes, so `tests/test_hands_boundary.py:48`'s `22` becomes the new
count (the only change in that test). Publish labels, rests and gates as
today. **No preset is built on them in this run** (the working plan's
`hands-dance` is the owner's to compose afterwards). A test routes each
new source onto a param through a scratch library and shows it moving.

### C5 — cause and effect (H1)

- **The grab switch.** A `hand:*.grab` switch (a closed fist from C4's
  curls, Schmitt + debounce like the pinches), published as a gate like
  the pinches, shown on the HANDS page. What it is for: "close a hand
  near the shape and the shape follows that hand's rotation 1:1; open it
  to let go" — `position` rows from the hand's roll/pitch/yaw onto
  `camera.yaw` / `camera.pitch` and a `rot.*` plane, gated by the grab.
  That mapping is the owner's to author afterwards; a test proves it
  works through a scratch library, and nothing in `preset.py` or
  `library/presets/` changes.
- **Hands on the main projection by default** in the party presets: the
  output switch already defaults on; set it in `config.toml.rig` for the
  projector output and say so in SETUP.md. Nothing in a preset.
- The working plan's "one or two strong hand mappings per party preset"
  is authoring, not infrastructure: **not in this run**. No stream edits
  `library/presets/`, so no golden moves for preset content.

### C6 — the palette fold

Owner's design (working plan, "Palette fold"): one final colour pass folds
every hue onto a slice of the HSV cylinder that is chosen and moved live.

- **Hue is folded, not clamped**: a triangle wave maps the 0–360° circle
  onto `centre ± width/2`, so neighbouring hues stay neighbours and there
  is no seam. **Saturation and value are rescaled** into a chosen low–high
  range. A second mode, **gradient map**, maps brightness onto a ramp
  through 2–4 anchor colours.
- Params, all routable: `mix` (0–1; 0 is today's picture), `centre`
  (0–360°), `width` (0–360°), `sat_lo`/`sat_hi`, `val_lo`/`val_hi`,
  `mode` (fold / gradient map), the anchor colours.
- **Build it as an effect file**, `shaders/fx/palette.glsl` with the last
  `@order`, so the ids are `fx.palette.*` (the working plan wrote
  `palette.*`; register the difference), the desk, hands, LFOs and bands
  reach it through the FX mechanism unchanged, it sits after the other
  effects and the dream and before the outputs as the plan asks, and with
  stream A it becomes a node for free. "Whether the hands are folded too"
  is today's `through` switch, not a new param. A saved palette is an
  `fx` module preset, which the library already does: prove it with one
  fixture under `tests/fixtures/` loaded through a scratch library, and
  ship no palette in `library/fx/` (the owner's "match the room" sets are
  made at the venue). Off by default, so no golden moves.

**Acceptance for stream C:** the two-handed save works ten times in a
row on the real APC40 (a hand check: say so); the toggles behave the same
with SHIFT up or down; the coverage report is committed with the numbers
per preset; a fixture preset's fader rows light the faders; the six H2
sources and the grab switch are routable; the palette fold is an effect
a fader can be learned onto; **`git diff --stat -- hyperspace/library/`
is empty**. The owner's "done when" lines that need authored presets
(the coverage goal met, the five-guest test) belong to the pass after
this run.

---
## What landed since the wishlist was written — rectify against it

The wishlist and its working plan are dated 2026-10-12. These merged on
2026-10-13/14 and every stream must build on them, not around them:

- **The wired Xbox 360 pad over libusb** (PR #160, `gamepad.UsbPad`), and
  **Learn pad** with momentary / hold on pad rows and **routable sticks**
  (`axis:LX…RT` routes; a routed axis leaves its default camera job,
  `router.claimed("axis")`) (PR #161). Stream B's B2 makes `Pad` a device
  on top of this, not instead of it: `learn_from`, `claimed`, the
  `PAD_REMAP` migration table (`routing.py:423`) and the pad's factory rows
  all stay. (The 2026-10-14 report that holding START hid the panel was
  the select button being pressed, not a decode fault: `decode()` is
  right, nothing to probe.) The owner said peripheral control was "due a
  broader refactor soon":
  that refactor is B2, so do not polish pad mappings elsewhere.
- **Route motion** (PR #162): `motion.py` is the one kernel (the analyzer's
  followers and a closed-form spring; a leaf); `Binding.motion` holds a
  route's feel (`routing.py:489`); `Router.felt` / `source_feel`
  (`:2192/:2182`) run it; the pad's feel is the `desk.pad.*` session params
  (`register_desk`, `PAD_FEEL :1188`), which the camera job also reads. B2's
  pad device publishes its feel through the registry and `felt` stays in
  the router; nothing in C or A touches it.
- **The pad layout** (PRs #163–#166): B / X walk the preset list
  (`preset.list.next/prev`, `params.py:1232`), not the bank; A faces, Y
  lines; the right-stick click resets the 4D spin (`rot.reset_w`
  `:912`); pitch wraps like yaw; the right stick's X rides the W planes'
  spin; **START and BACK are unbound**. C1's two-handed save is on the
  desk only; it does not re-bind START.
- **Plan 25, the shared library** (PRs #167/#168, may be unmerged): the
  library root may be a cloud folder, machine files stay in the home,
  `homegit` and `shared/` are gone, `Library(home_dir, machine=…)`. C3's
  desk templates are a library group, so they share through it. Every
  stream's tests point the home at a scratch folder as before.
- **The hand-check numbers clashed.** PR #161 wrote the pad's four checks
  into `TESTING-GUIDE.md` §(f) as checks 139–142 but never added them to
  `docs/plans/11-hand-checks.md` (which ends at 138 on `main`); plan 25's
  build then used 139–143 for group S. **The first docs WP to land** writes
  the pad's four checks as **group T, 144–147** (from §(f)'s own text) and
  corrects §(f)'s numbers; plans 24, 26 and 27 are groups **U, V, W** from
  **148**. `docs/plans/README.md`'s "numbered 1–N" line follows.
- **Golden geometry traces** and the plan-02 `project` oracle are untouched
  by all of this; A2's half-pixel bound is against `project_h` as it is on
  `main` today.

---
## Decisions already made — do not relitigate

All the owner's, 2026-10-12, from the wishlist and its working plan:

1. **Both streams start now, in parallel.** The render graph is the top
   priority; the registry is the highest-leverage piece.
2. **The four node kinds** (Geometry, Scene, Layer, Composite) and their
   contracts as tabled under A1. (The FX, History and Output wrappers are
   yours: register them.)
3. **Hands in the scene or as a layer, or both at once.** Solid first,
   then the sorted see-through shape. **Order-independent transparency is
   deferred.**
4. **The shape's transform:** `rot.*` local, `camera.yaw/pitch` world pose
   (ids unchanged), `camera.zoom/pan` the shape's world scale and position,
   and a new fixed `eye.*` camera on the Leap box. The whole-frame 2D zoom
   is gone until an image node brings it back.
5. **Lines and points get a real depth** as vertex-expanded quads.
6. **History becomes wiring**: capture from a chosen node, with or without
   hands.
7. **Today's three pipelines become default graphs that A1 must
   reproduce pixel for pixel.**
8. **Step 0 before step 1:** golden frames for every factory and party
   preset, GPU timing per pass, and the naming rule (first instance keeps
   today's ids; only extra instances are prefixed; nothing migrates).
9. **Twelve hand axes stay.** No gesture vocabularies in this plan (H2's
   new sources are plan 24).
10. **The registry's shape:** a `Device` with open/poll/close publishing
    axes and hits with velocity, names, rests and status; `[[devices]]`;
    hot-plug; several MIDI ports with their own profiles; schemes from the
    registry; sinks the same way; a point-cloud source type. **Done when
    the APC40, the pad and the hands run on it and an OSC device is added
    with no edit to `app.py`.**
11. **Roles, not serials.** A preset names a role; the session maps roles
    to devices; a missing device's rows wait.
12. **Two input ports per param is today's model** (base: many
    scene-setters, last touch wins; mod: one performer, the referee). The
    registry changes nothing about `Owned` / `referee` / `Router.modulate`.
    Combining two performers needs an explicit combine node, which is
    plan 28, not this run.
13. **Values and triggers are two signal kinds.** Encoder vs fader
    behaviour, soft pickup included, is a property of the port set by the
    device profile.
14. **A device with a mode switch can appear as one node per mode** (the
    APC40 as *APC40* and *APC40 (SHIFT)* in plan 28). The registry must
    model a device's layers so that plan 28 can do this without
    re-plumbing; D1, D4–D6 and D12 hold.
15. **Rejected:** writing GLSL inside the graph, or a general
    TouchDesigner. Nodes are a curated set of built-ins; shaders stay as
    files with hot reload.
16. **The processes in force:** `DECISIONS.md` "Process" (a `/code-review`
    per code PR; agents on branches; the owner merges); nothing in the
    render stack writes a param; adapters only `feed`; the hands package
    stays liftable; the core never imports `midi`, `bridge`, `dream`,
    `osc`, `torch`, `leap`.

17. **The desk keeps its map's shape**; the master fader stays audio
    drive and the crossfader the master dim; **the track faders S1–S8
    become preset-layer targets** with no inherited defaults and no
    auto-fill; band post/dyn/trim move to the SHIFT layer; every layer
    and effect gets a mix where it lacks one. The fader sets themselves
    are the owner's, after this run.
18. **The render toggles are the same on both layers** and their LEDs show
    the live state; **every load relights the whole desk**; the save is
    two-handed (SAVE held, a pad tapped), into any slot — a filled slot
    takes a new preset and the old one keeps its file; **nothing is
    overwritten or trashed from the desk** (owner, 2026-10-14).
19. **A coverage report** committed in the repo, **desk templates** as
    their own JSON, click-to-map ranked by the preset's own params. The
    goal of at most four dark or dead controls per preset layer is the
    bar for the owner's authoring pass, reported here, not met here.
20. **The twelve axes stay**; the H2 sources (curl, spread, energy, gap,
    twist, flick) and a **grab** switch are added beside them as sources;
    hands on the projector by default. The `hands-dance` preset, the grab
    mapping and the strong per-preset hand mappings are the owner's,
    after this run.
21. **The palette fold**: hue folded by a triangle wave onto a movable
    slice, saturation and value rescaled, a gradient-map mode, the param
    list under C6, after the effects and the dream and before the
    outputs, saved palettes as named library entries. Lights following it
    is plan 29.
22. **Touch shows** (fingertips light the shape where they are) is a
    look, so it is the creative pass after this run; A2 and A3 give it
    its foundation (the hands and the shape in one space, the fingertips
    in that space).
23. **No preset is edited or added in this run** (owner, 2026-10-14).
    Every file under `hyperspace/library/` stays byte-identical; every
    proof uses a fixture under `tests/fixtures/` loaded through a scratch
    library. Fader sets, hand mappings, dance presets, palettes and the
    graph wiring of the factory presets are the creative pass, done by
    the owners after the infrastructure lands.
24. **Every new param defaults to today's picture.** A new mix or
    opacity defaults to what the frame does now, the palette fold to
    `mix = 0` with a neutral grey ramp as its gradient anchors, a new
    switch to off, a new source to its rest. Nothing in this run authors
    a look.

When the docs WPs record these, they go into `DECISIONS.md` with **Who** =
`owner`.

## Decisions you may make yourself

Anything the three streams leave open: the SAVE button's control, the
desk event log's shape, the template file format, the ranking in
click-to-map, the H2 sources' shaping constants, the grab switch's
thresholds, the fold's anchor-colour params, the palette effect's ids
(`fx.palette.*` against the plan's `palette.*`), the node and port class design, the
graph JSON's shape, the prefix form for extra instances, the hands-in-scene
alpha rule (alpha 1 vs sorted as one object), the depth-aware composite's
threshold, the `eye.*` ids and defaults, how `camera.pan` migrates, the
`[[devices]]` keys, the MIDI role qualifier's form, the sink row's form,
the OSC address mapping, the cloud file format. When you take your own
recommendation and build it, append a row to `docs/DECISION-REGISTER.md`
starting at **row 110** in that file's format (what was built and what the
owner will see or feel; the other option(s); the cost to reverse; the known
rough edge; the hand check that lets the owner judge it), and mark the
matching `DECISIONS.md` row's **Who** as `row N`. Never mark a row `owner`
yourself, except the sixteen above.

## Out of scope for this run

- **Plan 24's hardware and rig items**: the touchscreen, the Dante
  adapter, the multi-channel capture, the pocket projector, the mic mount.
- **Plan 28**, the node editor (N1 modifier nodes between a source and a
  param; N2 a read-only graph view; N3 editing the modulation graph with
  cables; N4 the same editor on the render graph). With it goes
  **removing the one-frame modulation lag** by evaluating the modulation
  graph in dependency order: this run evaluates only the *render* graph
  that way, and ARCHITECTURE §2's lag rule stands until plan 28. A4 shows wiring in words; nothing draws cables.
- **Plan 29**, the devices: wands, drums, Kinect, DMX/sACN, bulbs, a
  generic on-screen desk. B4's OSC device and cloud file are the proofs
  the registry works, not products.
- Order-independent transparency; the hands' FX, textures and tracers as
  *params of the hand look* (H3, "hands as geometry": styles, FX,
  textures and tracers as params — this run's A3 makes them possible,
  their params come later); touch shows (H1's glow where a fingertip
  meets the shape) and hand–shape contact (H4: fingertips denting the
  shape's vertices).
- The web remote, the touch panel, Dante, multi-channel audio capture.

---

## How to orchestrate

- One sub-agent per WP, each in its own git worktree off the verified
  base. Verify the base, don't assume it: the failure that silently ruins
  this workflow is an agent on a stale base whose diff quietly reverts a
  sibling's work. Re-check right before each worktree is cut.
- Branch names as listed; one PR per WP, into `plan-24-26-27-integration`,
  titled `Plan 26 A1: the graph in code, today's three pipelines pixel for
  pixel` and the like. Each WP's PR body lists the goldens it re-recorded
  (streams A and C) or the boundary assertions it consciously changed
  (streams B and C), each with its one reason.
- Stream A is serial (A0 → A1 → A2 → A3 → A4 → A5). Stream B: B1 → B2 →
  (B3 ‖ B4) → B5. Stream C: (C1 → C2 → C3) ‖ (C4 → C5) ‖ C6, then C7.
  Run all three beside each other. A and B share `app.py`
  (A touches `_draw_render` / `draw_render`; B touches `main`, `Host`,
  `frame`, the close order) and `ghost.py` (A rewrites it; B only hands
  `HandsIO` over). Expect those overlaps and resolve them at integration,
  never by one WP reverting the other's lines. Two more expected
  overlaps: the SYSTEM page in `ui.py` (A0's timing lines, B1's device
  lines) and `hotreload.MODULES` with `tests/test_hotreload.py` (A1 adds
  `graph`; B1 and B4 add `devices` and `osc`). Stream C's expected
  overlaps: `midi.py` and `apc40.py` (C1/C2 change the map and the save;
  B2 makes `MidiIO` a device — C1 lands first and B2 carries it);
  `draw_scene` (C2's two alpha lines; A2's rewrite); `hands/core.py`
  (C4 adds sources; B2 wraps `HandsIO` and must not pin the lane count).
  No stream touches `hyperspace/library/`, so no golden moves for preset
  content. Anything else colliding means a WP is mis-scoped: stop and
  re-cut it.
- Merge each WP into `plan-24-26-27-integration` as it lands. The
  cross-stream item (the point-cloud node `plan-26-a4b-points` after B4
  and A3) is cut from integration.
- A review pass over the integration branch before the final PR, with
  fixes committed as `Review: <what was fixed>`. Look hard at:
  - **A golden that moved without a reason.** Diff every frame in
    `tests/golden/frames/` against A0's recording and account for each.
  - **The hands flipped, mirrored or scaled twice**: `ghost.mirror`, the
    output flips, the shared camera and the Leap calibration all touch
    the same pixels.
  - **A second output in another context** (`Presenter`): after A3 the
    hand-off must still carry hands-over, readout and dim.
  - **A device that raises on `open` or `poll`**: the frame goes on, the
    SYSTEM line says `error`, the retry schedule runs, nothing else
    changes.
  - **A preset or `bindings.json` from before this run** loads with no
    note and no dirt.
  - **A missing device at launch** (`lost`): its rows wait, the desk shows
    dark, and plugging it in later brings it up with its feedback.
  - **The two-handed save on a filled slot**: the old preset's file is
    untouched and still in the list, the slot holds the new preset, the
    new one is loaded, the pad blinks, the trash is unchanged, and a SAVE
    press with no pad does nothing. Under SHIFT the same.
  - **The toggles under SHIFT**: points, lines, faces, rotate from both
    layers, their LEDs right after a load on either layer.
  - **The coverage report** regenerates byte-identical on a second run.
- **Re-measure everything on the merged branch.** A sub-agent's green run
  inside its own worktree does not survive integration. Re-run the gates
  on `plan-24-26-27-integration` itself before claiming anything.
- One final PR from `plan-24-26-27-integration` to the base decided above,
  titled `Plans 24, 26 and 27: the party fixes, the render graph and the
  device registry`. The owner merges.

## Gates — all green before any PR

```
uv run pytest -q
uv run ruff check .
HYPERSPACE_FRAMES=120 uv run hyperspace     # windowed smoke run
```

`main` is at 1890 passed, 2 skipped (the plan 25 branch at 1885 + 2). Run
the smoke run once per stream with the new paths on: a preset that carries
a `graph` section with the hands in the scene (stream A); a `[[devices]]`
list with the OSC device and a cloud device enabled and the APC40 absent
(stream B); the fixture preset with fader rows loaded from a scratch
library, SHIFT latched and released, the palette fold's mix up (stream C,
with the fake MIDI ports the tests inject). Point the home at a scratch
folder the way the tests do (`HYPERSPACE_HOME`), whose `config.toml` has
no `[library]` section, so the library is that scratch home too.
**Never touch the owner's real `~/Hyperspace`, and never the shared
library it points at (`~/My Drive/Hyperspace`, a Google Drive folder that
syncs to another Mac): never run the app or a tool against the real
home, and never write a preset, template, palette or fixture there.**

These must keep passing **untouched**:

- `tests/test_render.py::test_the_render_stack_imports_no_registry`
  (so: no node method named `apply`).
- `tests/test_outputs.py::test_outputs_imports_nothing_from_app_ui_or_params`
  (`outputs.py` imports `glsl` and nothing else from the package).
- `tests/test_hands_boundary.py`'s three-standalone-files test and its
  no-host test (C4 changes only that test's lane count).
- `tests/test_routing_boundary.py` (`ABOVE` and `LAZY` as they are).
- `tests/test_bridge.py::test_core_does_not_import_the_bridge`.
- `tests/test_hotreload.py::test_every_package_module_but_the_cold_core_is_watched`
  and `::test_the_watch_list_is_in_dependency_order` — add `graph`,
  `devices` and `osc` to `hotreload.MODULES` in import order.
- `tests/test_golden.py`, `tests/test_core.py`, `tests/test_shapes4d.py`:
  the geometry traces and digests never move.

These may change **only as this prompt says**, each change named in the
PR body:

- `tests/test_hands_boundary.py::test_the_panel_is_the_only_piece_that_knows_the_host`:
  the list becomes `["device.py", "panel.py"]` (B2); `::test_the_instrument_runs_with_no_host_at_all`:
  `22` becomes the new lane count (C4).
- `tests/test_desk.py` and `tests/test_midi.py`: the rows C1 and C2 move
  (the toggles invariant, the faders to the preset layer, the band rows to
  SHIFT, the SAVE button) change the assertions that pin the map's shape
  (`test_the_default_map_is_sorted_as_plan_13_says`,
  `test_invariant_controls_mean_one_thing_on_both_layers`); each changed
  assertion is named in the PR body with its decision number.
- `tests/test_app_boundary.py`: `gated` gains `hyperspace.osc` and
  `pythonosc`; `ORDER` and `test_the_host_close_list_…` are rewritten for
  the registry (B1); `test_a_shut_gate_opens_nothing` and
  `test_the_pad_gate_is_open_by_default` become registry tests with the
  same meaning.
- `tests/test_outputs.py:454` (`test_the_history_never_holds_the_hands_in_any_state`)
  and `tests/test_render.py:650` (`…_the_dim`) become "the default graph's
  history holds what today's does" (A3).
- `tests/test_golden_frames.py`: re-recorded only with a reason (A2–A4).

Invariants that hold throughout: the render stack reads parameters and
never writes one; modulation is non-destructive (`Router.modulate` is the
only caller of `Param.modulate`); no new module imports `torch` outside
`dream.py`; with no `graph` section and no `[[devices]]` list, every
output is byte-identical to A0's goldens and every device comes up as
before.

---

## What the docs WPs must produce

A5 writes plan 26's, B5 writes plan 27's, C7 writes plan 24's; the shared
files are edited by whichever lands later, on the integration branch, so
they do not collide.

- `docs/plans/24-party-fixes.md`, `docs/plans/26-render-graph.md` and
  `docs/plans/27-device-registry.md`: each **as built**, in the shape of
  `21-outputs-and-the-hands.md` — what was built (by WP), what no person
  has verified, known rough edges — with the hand-check group and register
  rows named in the intro. Keep this prompt file; the docs WPs together
  update `docs/plans/README.md` (this prompt's entry becomes "the launch
  prompt plans 24, 26 and 27 were run from"; the three new entries;
  `24-party-wishlist.md`'s entry says which streams are now plans).
- `docs/plans/24-party-wishlist.md`: the priority paragraph points at the
  three as-built files. Nothing else in it changes; it is the owner's
  record.
- `docs/SETUP.md`: the projector output's hands switch in the rig config
  (C5), and the two-handed save in the APC40 quick reference.
- `docs/ARCHITECTURE.md` **and `docs/ARCHITECTURE.html`** together: §1's
  component map (a **Graph** row in the render stack; **Devices** replacing
  the input-adapters row and the host's gate list), §2's frame table
  (devices poll, sources feed, sinks send; the drawing subsection becomes
  the graph's evaluation), §3.3's scheme table (schemes from the registry;
  the stale `LANE_SCHEMES` text at `:388` and the three-item WANTS at
  `:494` are already wrong on `main` — fix them), the "Adding a source"
  paragraph inside §3.4 (`:462`) rewritten as "Adding a device", §5's subsystems. Update the counts in
  the HTML's masthead and closing stat row (measure them; they are
  already stale on `main`). Keep SVG colours in CSS classes, never `var()`
  in presentation attributes, and keep the three token blocks (light, dark
  media, dark attribute) in step.
- `docs/ENGINEERING.md`: §2 Rendering (the graph, the nodes, the camera,
  the naming rule, the goldens and how to re-record them, the per-node
  timing), §5 `config.toml` (`[[devices]]`, the old tables' translation),
  §7–§9 and §12–§14 where the devices and sinks changed them, §16 Testing
  (the golden-frame tool).
- `docs/DECISIONS.md` and `docs/DECISION-REGISTER.md`: the sixteen owner
  decisions as rows with Who `owner`; your own from row 110, each under a
  `## The render graph (plan 26)` or `## The device registry (plan 27)`
  section and on the answer sheet; rows that are now superseded (for
  example 79, "where the hands go in", and the `placement`/`ghost` rows
  whose text no longer matches) marked the way plan 25 marked 78 and 108.
- `docs/plans/11-hand-checks.md`: group **T** (the pad's four from
  `TESTING-GUIDE.md` §(f), 144–147), then **U** (plan 24), **V** (plan 26)
  and **W** (plan 27) from **148**, in the existing format (bold number
  and title; the headless tests behind it; the setup; *Pass:* and *Fail:*
  with the likely cause). At least:
  - the two-handed save ten times in a row on the real APC40, into empty
    and filled slots, with SHIFT up and down;
  - the toggles from both layers and their LEDs after a load;
  - a fader learned onto a param from the desk, felt, and the band faders
    under SHIFT;
  - the coverage report's numbers against what the owner sees as dark;
  - each of the six new hand sources and the grab switch, with a real
    hand, learned onto a param and seen moving it;
  - the palette fold's mix learned onto a fader and swept, on any preset;
  - every factory preset against its golden contact sheet, by eye, on the
    Mac (Apple's shader compiler is unverified for the new vertex path);
  - the hands in the scene on the projector and as a clean layer on the
    glass at once;
  - a hand passing between the shape's edges;
  - `hands-orbit` turning only the shape with the hands staying put;
  - a saved pre-run preset with a non-zero `camera.pan` looking the same;
  - the per-node times on SYSTEM while an effect is toggled;
  - the APC40 on the registry: launch with it unplugged, plug it in, the
    desk lights up;
  - a second MIDI controller on the `generic` profile learned onto a
    knob;
  - the OSC device from a phone app on the same Wi-Fi driving a param;
  - the bridge's `send` list as sink rows, seen in the DAW.
- `docs/TESTING-GUIDE.md`: the same checks in plain words, by hardware,
  each ending with its check numbers; the render ones go in Part 1 and
  the device ones under Part 2's APC40 and a new "(g) a second
  controller / OSC" entry.
- `docs/CHECKPOINT.md`: **it is stale on `main`** (it says `2d4ea11` and
  plan 22 unmerged). Rewrite "Where the code stands" and "What is left" to
  be true at the end of this run, and keep it short.

## Report back

When the final PR is open, report:

- What landed per WP, with the PR links, and the test count on the
  integration branch.
- **The goldens.** How many frames, which WPs moved which, and the contact
  sheets' paths. If any frame moved in A1, say so first: that is a bug.
- **The default eye.** The maximum vertex error against `project_h` at the
  default eye, and what the default view looks like by eye in the smoke
  run.
- **The render graph's order.** Whether evaluating the render graph in
  dependency order changed any pixel of any golden beyond A2's accounted
  moves. The modulation lag (ARCHITECTURE §2) is plan 28's, so say if
  anything in this run touched it.
- The register rows you opened (110–N), each with what it needs from the
  owner.
- The new hand check numbers and their groups (T for the pad's four, U
  for plan 24, V for 26, W for 27).
- **Stream C.** The coverage numbers per preset, and confirmation that
  `hyperspace/library/` is byte-identical to the base.
- What stream B translated from the old config tables, and the exact
  `[[devices]]` block the owner should paste to get today's rig.
- Anything you deliberately left undone, anything that contradicts this
  prompt or the wishlist file, and anything a document says that the code
  does not do. If a document says something the code does not do, say so
  rather than quietly matching it.
