# Plan 43 — the preset contract: a preset is a complete look; the rig is what is plugged in

The contract line and an audit of where today's code draws the line
between a preset and a session. Docs only (wave 0, C1, 2026-11-02): this
plan moves no param, changes no file format and writes no code. It gives
the two PRs that act on it — **C2** (one orbit camera: `camera.*` and
`eye.*` as one preset group) and **D3** (the per-deck versus rig
migration) — their exact worklists.

**Status (2026-11-02): C2 built** (wave 1, branch `wave1/c2`; register
rows 572–576; hand checks 431–433, group AX) — §5 says what it did and
where it differed, §7 records the owner's answers. **D3 built**
(2026-11-03, wave 2, plan 44 D3; register rows 611–625; hand checks
461–470, group BJ) — §6's "What changed in the build" says what it did
and where it differed. The audit below is as read at 72da1ed, before C2.

Agreed by the owner on 2026-11-02, from the triage of the 2026-10-30
show (2026-10-31): "camera not restored" — a preset saved after the
operator framed the picture came back framed differently, because the
preset/session line is drawn **per param group**
(`params.PERFORMANCE_GROUPS` / `SESSION_GROUPS`), not per thing on
screen. Register rows 554 (the line) and 555 (the camera).

## 1. The contract

> **A preset is a complete look; the rig is what is plugged in.**

Two consequences, which every row below is sorted by:

- **Everything that renders goes in the preset.** The eye, the shape's
  pose, the hands' look, the show's bus-cable cuts, the point cloud's
  look, the desk template inlined. Loading a preset on any rig that can
  show it draws the same picture.
- **Everything about hardware stays out, and is requested.** Devices,
  tempo, the band scene and the analyzer, the output count, calibration,
  feel (`desk.pad.*`, `desk.slew`, `hands.*`). A preset says what it
  wants of the rig (a desk, a hands tracker, two windows) and the rig
  says what it has; the preset draws with what is there and says in
  words what is missing (`devices.wants`, plan 40 P4, already does this
  for desks).

Later, patch, group and preset become **one format** (register row 540
already points module presets at patches); the camera and eye merge
(C2) is the first step, and the per-deck split (D3) the second.

The test of a row is one question: *if this changed and nothing else
did, would the projector show a different picture?* Yes → the preset's.
No → the rig's, or nobody's.

## 2. Where the line is drawn today

Read from the code on `main` at 72da1ed.

**By group** (`hyperspace/params.py` 146–150). `PERFORMANCE_GROUPS` =
`view rot camera pattern dream fx media backdrop switch resize matte cut
segment lfo env seq macro mod`; `SESSION_GROUPS` = `tempo hands ghost
band master scene audio output overlay ui desk eye cloud`.
`tests/test_params.py::test_every_persisted_group_is_performance_or_session`
holds every persisted param to exactly one of the two and its id's first
segment to its group. A preset's `values` is `reg.snapshot(part=
"performance")` (`preset.Presets._values`); a show's `session` is
`reg.snapshot(part="session")` (`library.Project.save`). A session id in
a preset's `values` or a macro's base subscribers is dropped with the
note "`<id>` is the session's, ignored" (`preset.py` 1007, 1139;
`routing.base_refusal`).

**The preset file** (`<library>/presets/<slug>.json`,
`hyperspace.preset/7`, `/8` with a group; `preset.Presets.document`):
`values`, `graph` (every node and wire, the hands entries, `laid`),
`routes`, `modifiers`, `desk` or `desk_template` + overrides, `macros`,
`modules` (labels only), `units`, `layout` (the look's nodes), `groups`,
`media` (the channels' bins), and each modulator bank's membership where
it differs from four.

**The show file** (`<library>/projects/<slug>.hyp.json`,
`hyperspace.project/2`; `library.Project.to_doc`): `session` (every
session param's base), `modules` (the session groups' module-preset
labels, or an inline copy), `bank` (the pads), `startup`, `layout` (the
rig's nodes on GRAPH), `rig` (`graph.RigWires`: the bus cables from All
outputs into each window this show has **cut**).

**The home** (`Library.machine`, never shared; ENGINEERING §4):
`config.toml` (`config.py`: `[[devices]]`, `[output]`, `[[output.screens]]`,
`[library]`, `[dream]`), `bindings.json` (the session's rows only:
keys, pad, OSC, the invariant and SHIFT-layer MIDI rows, sinks;
`routing.is_session_row`), `hands.json` (`hyperspace.hands/3`: the box,
each axis's range, `units` — mm, origin, tilt), `windows.json`,
`ui.json`, `last_show`, `media/` (`local:` files), `weights/`.

**The library beside the presets**: `desk/<name>.json`
(`hyperspace.desk/1`, `Library.desk_template`) — a preset names one by
name and stores only its overrides (`preset.expand_desk` /
`compact_desk`); `<group>/default.json` — `Library.resolved` lays a
preset's values **over the group's default module preset** for any id
the file lacks (`Library.defaults`, `DEFAULT_NAMES`); `patches/`;
the band scenes are code (`hyperspace/scenes/band/`).

**Never saved anywhere** (runtime): `rot.phase.*` (`persist=False`, the
integrated angles), `view.body` (the 4×4 pose the 3D switch folded in,
not a param, `view.py` 152), `seq.run`, `seq.step`, `env.<n>.gate`,
`desk.shift`, `desk.save`, `output.dim` (1 at every launch), every
`output.N.*` switch (from the config at every launch and ⌘R,
`overlay.register_switches`), `hands.select`, the hold (`hold.py`).

### The schema numbers

`hyperspace.preset/8` is **taken**: plan 40 D7 made a preset with a
group `/8` (`graphmigrate.GROUPS_SCHEMA`, `preset.VERSIONS = (2, 3, 4,
5, 6, 7, 8)`, DECISIONS "Patches and groups"). The wave-0 plan names C2
as `/8` and D3 as `/9`; in the code the next free numbers are **`/9` for
C2 and `/10` for D3**. Row 521 (a save with no group stays `/7`) is
still pending the owner; C2 is the natural place to settle it — once
`eye.*` sits in every preset's `values`, every save is the new schema
anyway and the `/7`-or-`/8` fork goes.

## 3. The audit

One row per thing that is saved, requested or runtime. *Lives today*
names the file or group as the code has it; *renders?* is the question
in §1; *destination* is where the contract puts it; *PR* is which of C2
and D3 moves it (— : stays; rig: stays on the rig, requested where a
preset needs it). Counts are from the headless registry the tests build
(`tests/test_params.py::_full_registry`: four LFOs, six bands, no hands
axes, no extra graph nodes); the app's numbers grow with each.

### 3.1 The param groups

| Thing | Lives today | Renders? | Destination | PR | Migration note |
|---|---|---|---|---|---|
| `view.*` (34 persisted of 35: shape, bright, lines/points/faces, planes, speed, 3D, instances, media path, cut-through, screen strokes; `view.bmp_alpha` an alias) | preset `values`, performance | yes | preset | — | none |
| `rot.rate.*` (6) | preset `values`, performance | yes | preset | — | none |
| **`rot.phase.*`** (6, `persist=False`, `params.py` 1732) and **`view.body`** (not a param) — the spin's pose | nowhere: a load "leaves the phases spinning" (`preset.py` docstring step 2; `view.integrate`) | **yes** — the same preset opens on a different turn every load, and the 3D fold `view.body` with it | preset | **C2** | make the pose saveable: either persist the six phases and fold `view.body` into them at save (`geometry.view_angles`, `ViewState.integrate`), or add a `pose` key to the preset; a load then **sets** the turn instead of leaving it. `hold.ONE_FOR_BOTH` reads the turn before either draw — the held program and the preview share one pose today, so a saved pose lands on both. An old file without a pose keeps today's behaviour (left spinning); decide whether a save with the pose is the default or a chip. The owner's words (2026-10-31 triage) group it with the camera, so C2; it is separable |
| `camera.zoom`, `.yaw`, `.pitch`, `.pan.x`, `.pan.y` (5; `camera.reset` a trigger) — the shape's world pose and scale (decision 4) | preset `values`, performance | yes | preset, in the **one camera group** | **C2** | ids unchanged (a saved id is a format, REVIEW.md); the merge is the eye's move into this group, not the reverse. `hold.HELD_GROUPS` already holds `camera` |
| **`eye.fov`, `eye.distance`** (2, not modulatable: "the camera is the rig", `params.py` 1791) | show `session`, `SESSION_GROUPS` | **yes** — the framing of the whole picture; the hands' default calibration scales with it (below) | preset, in the one camera group | **C2** | move `eye` out of `SESSION_GROUPS` into the camera group (rename the ids to `camera.fov` / `camera.distance`, or keep `eye.*` and put `eye` in `PERFORMANCE_GROUPS` — a rename needs a read map and a backup, keeping the ids needs only the group move); a load lands them; every preset in the library gets the **show's** value written in (there is one show per rig, so the Drive library's presets all take that rig's eye — identical to what they draw today). Read the eye out of old shows' `session` on load and drop it from the write. Overturns row 182 and the DECISIONS eye row (row 555). `ui.py` 2305 "the room's camera, not the preset's" and `graphview.py` 43 / `RIG_KINDS` ("camera" the rig's node) say the old model |
| `pattern.mod.0–7` (8) | preset `values`, performance | yes | preset | — | none |
| `dream.*` (23) | preset `values`, performance | yes | preset | — | none |
| `fx.<file>.*` (140 in the test registry; one set per effect instance the graph holds) | preset `values`, performance; written only for instances the `graph` section names (`preset.py` 1263) | yes | preset | — | none |
| `media.<a–h>.fit/jog/loop/pos/rate/slot` (48) and the channels' bins (`media` section) | preset, performance | yes | preset | — | none for the params. A bin naming a `local:<path>` file renders only where that Mac has the file (`<home>/media/`); `shared:` ids already answer this. The contract's word for a missing `local:` file is "requested": the banner exists (hand check 301) |
| `backdrop.alpha` (1) | preset `values`, performance | yes | preset | — | none |
| `switch.*`, `resize.*`, `matte.*`, `cut.*`, `segment.*` (declared per graph node, `params.declare_*`) | preset `values`, performance | yes | preset | — | none |
| `lfo.*` (20 of 25), `env.*`, `seq.*` (pattern, not transport), `macro.1–8`, `mod.*` (in `modifiers`) | preset, performance | they modulate what renders | preset | — | none. `seq.run`, `seq.step`, `env.<n>.gate` stay runtime (plan 31 decision 8) |
| **`ghost.*`** (6: `on`, `alpha`, `mirror`, `guide`, `tethers`, `style`) — the hands' look | show `session`; `ghost.register` docstring: "the hands are the room's display … a preset load never switches them off mid-set" | **yes** — what is drawn where the hands are, on every output | preset | **D3** | move `ghost` into `PERFORMANCE_GROUPS`; every preset gets the show's six values written in. `ghost.mirror` is the one row with a hardware reason (a real mirror in front of the performer): keep it in the preset — a preset that flips the hands is a look — or split it to the rig; the owner decides (§6). A hands node already lives in the preset's `graph` (plan 26 A4), so the look joining it is consistent |
| **`ghost.2.*`** (a second hands node's look) | the show's `session`, held back while no preset holds the node (`Project._held_back`); **seeded from the open show once per show opened** (`preset.GraphSection`, `self.lib`) | yes | preset | **D3** | with `ghost` performance, the node's values live in the preset's `values` under the naming rule (`ghost.2.alpha`); delete `_held_back` and the seeding |
| **`cloud.size`, `.scale`, `.bright`, `.colors`** (4) — how a point cloud is drawn | show `session`; `params.py` 1812: "a cloud is the room's sensor, and a preset load never changes how it is shown" | **yes**, whenever a `cloud` device is listed | preset (the look); the device stays rig | **D3** | move `cloud` into `PERFORMANCE_GROUPS`; a preset with no cloud device draws nothing and says so (requested). `graphview.RIG_KINDS` lists `cloud` as the rig's node: the device is, its look is not |
| `tempo.bpm`, `tempo.nudge` (2; `tempo.tap` a trigger) | show `session` | the LFOs sync to it | **rig** (requested) | — | the owner's list (2026-11-02) puts tempo on the rig: a tapped BPM survives a load (D1) |
| `hands.*` — the feel: 9 global (`smooth`, `response`, `catch`, `learn_depth`, `rate`, `steady`, `pinch_*`) + 13 per axis (`invert`, `bipolar`, `deadzone`, `curve`, `attack`, `decay`, `rest`, `rest_value`, `return`, `bounce`, `out`, `channel`, `number`; `hands/core.py` 776–866); none modulatable | show `session`; a `hands` module preset ("setup") | no — how a hand reads, not how it looks | rig | — | none; `hands.sel.*` is an alias, `hands.select` never saved |
| `band.*` (78 of 101: six bands × 13 knobs; `band.sel.*` aliases), `master.gain/dyn/trim`, `scene.select`, `audio.device/mic` (0 persisted) | show `session` (+ `modules` for the band layout and scene) | they modulate; the picture is the same with the music off | rig | — | D9 stands: the analyzer is the session's |
| `output.bg`, `output.alpha` (2 persisted of 13: the overlay ground and window opacity; the rest — `monitor`, `fullscreen`, `overlay`, `passthrough`, `render`, `dim` — never saved) | show `session` / config at launch | the ground shows only in overlay mode, a rig mode | rig | — | none |
| `output.N.scene`, `.hands`, `.flip_x`, `.flip_y`, `.dim` per opened output | config `[[output.screens]]` at every launch and ⌘R; never saved (`overlay.register_switches`) | yes, but they are the window's: a glass is flipped, a second screen is dimmed | rig | — | none. What **picture** reaches a window is the look's — see the bus cuts |
| `overlay.*` (5 aliases of `output.*`) | — | — | — | — | none |
| `ui` (`edit.undo`, `edit.redo`, `app.restart`: triggers, none persisted) | — | no | — | — | none |
| `desk.slew`, `desk.pad.attack/bounce/duration/feel/release` (6 persisted; `desk.shift`, `desk.save`, `desk.pad.spring`, `seq.page`, `seq.select` never) | show `session` (`routing.register_desk`) | no — the knobs' and sticks' feel | rig | — | the owner names `desk.pad.*` as feel, rig. Note the show's spring rename (`desk.pad.hz` → `.duration`, `routing.renamed_session`, `.bak-v2-spring`) is the precedent for reading an old `session` |
| `preset.*` (23 triggers and `preset.select`: the bank, home, next/prev) | nowhere (no persisted param; the bank is the show's `bank`) | no | rig (the pads are the desk's, row 541) | — | none |

### 3.2 The things that are not params

| Thing | Lives today | Renders? | Destination | PR | Migration note |
|---|---|---|---|---|---|
| The `graph` section: nodes, wires, hands entries, `laid`, effect instances | preset (`preset.GraphSection`, `graph.read_graph`) | yes | preset | — | none |
| `routes`, `modifiers`, `macros`, modulator bank membership | preset | they modulate | preset | — | none |
| **The rig's bus cuts** — the default cables from All outputs into each window a show has cut (`graph.RigWires`, the show's `rig` key; `Renderer.rig_source`; `graphview.BUS_SAID` "the rig's cable (the show's, not the preset's)") | **show** | **yes** — which picture a window shows | preset | **D3** | the preset's `graph` already names `render:output.<n>` as nodes and wires into them; a cut is "no wire from All outputs to window n". Write the open show's `cut` list into every preset's section as the absence of that bus wire (or an explicit `cuts` list in the section), stop writing `rig` in the show, and have `rig_of` read the loaded preset. A window the rig lacks is "requested" (the preset's wire to `output.3` on a one-window rig is dormant and said, as a missing desk is). Hold: `hold.program` hands the renderer the held rig cables — it then holds the preset's |
| **The desk template by name** (`desk_template` key, `<library>/desk/<name>.json`, `hyperspace.desk/1`; `preset.expand_desk`, `compact_desk`, `Library.desk_template`; a template may carry `modifiers`) | preset names it; the rows live in the library | the desk layer does not render, but a preset's rows are **not in the preset**: a template edited or missing changes what the preset does ("desk template … not loaded … this preset's own desk rows only") | preset, **inlined** | **D3** | at migration expand every preset's desk (`expand_desk(template, overrides)`) and its template modifiers (`merge_modifiers`) into the file and drop the key; retire `TEMPLATE_KEY`, `expand_desk`, `compact_desk`, `_at_load`, `_mods_at_load`, `Library.desk_template`, the `desk` library group (`library.DESK`, `DESK_SCHEMA`); a `/9`-or-later file with a `desk_template` key is refused. The factory has no templates; the Drive library may — count them first (`ls <library>/desk/`) |
| **Module defaults by name** — a preset's `modules` labels (D3 of plan 13: labels only) and `Library.resolved` filling an id the file lacks from `<library>/<group>/default.json` (`Library.defaults`, `DEFAULT_NAMES`, `default_name`) | preset labels; library files | the labels no; the fallback **yes** when a file is partial (a param added since, or an old file) — the same preset on two libraries with different `default.json` files draws differently | preset complete | **D3** | since row 394 a save writes every performance value, so only old files and new-build ids reach the fallback. Have a preset load take the **build's fresh values** (`Library._fresh_of`) for a missing id, never a library file; keep `resolved` for the module strips (a strip load is a group's own door). Decide whether `modules` labels stay (inert) or go (row 540 says module presets become patches) |
| The show's `layout` (the rig's nodes on GRAPH) and the preset's `layout` (the look's nodes) | show / preset | no (the canvas) | as they are; a node that moves to the preset's side (camera) takes its position with it | C2 (the camera node's position), D3 (cloud) | `graphview.RIG_KINDS = ("output", "channel", "camera", "cloud")`: after C2 the camera node is the look's (its params are), after D3 the cloud's look is; the output and channel nodes stay the rig's |
| `bindings.json` (`hyperspace.bindings/3`: keys, pad, OSC, invariant and SHIFT-layer MIDI rows, sinks) | home | no | rig | — | none |
| `hands.json` (`hyperspace.hands/3`: the box, the ranges, `units`: `mm`, `origin`, `tilt`) | home | **the hands' placement in the world** — and with `mm = null` (the default, "from the box") `ghost.calibration` fits the padded box into the **eye's** frame, so the hands' world scale is computed from `eye.fov` / `eye.distance` (`ghost.py` 295–325, `shared_camera`) | calibration: rig | **C2 must look** | once the eye is the preset's, a preset with a wide eye shrinks the shape **and re-fits the hands to the wide eye**, so the hands keep their screen size while the shape does not — the hands leave the world. C2 either calibrates against the rig's reference eye (`EYE_FOV` / `EYE_DISTANCE`, the defaults) so the preset's eye sees shape and hands alike, or writes `mm` at calibration time. Hand check: zoom the eye on a preset with the hands in the scene |
| `config.toml`: `[[devices]]` (midi, gamepad, hands, bridge, osc, cloud, ndi, syphon, camera), `[output]` (`render` cap, `overlay`, flips, `keep_awake`, `syphon` / `ndi`), `[[output.screens]]` (count, monitors, fullscreen, `window`), `[library] path`, `[dream]` (worker device, precision) | home | the render cap and the output count shape the picture, but they are what is plugged in | rig; a preset **requests** (a desk, a tracker, n windows, a cloud, a camera) | — | `devices.wants` / `DeviceRegistry.said` already say "N devices missing" for desks (plan 40 P4); D3 extends the wants to windows and the cloud |
| `windows.json`, `ui.json`, `last_show`, `media-cache/`, `weights/` | home | no | machine | — | none |
| The band scenes (`hyperspace/scenes/band/`), `bindings.default.json` | code | no | code | — | none |
| The bank (`bank`, 24 pads) and `startup` | show | no | rig (the desk's pads, row 541) | — | none |
| The hold (`hold.py`: `HELD_GROUPS = view camera pattern dream fx backdrop switch resize matte cut segment`, the held rig cables and hands states) | runtime | yes (what the projector keeps) | runtime | **C2, D3** | `HELD_GROUPS` is a second copy of "what renders" and must follow the move: C2 adds the merged camera group's eye params (held already by group name if the eye joins `camera`), D3 adds `ghost`, `cloud` and the cuts (already held as rig cables). `tests/test_hold.py` pins the set |

## 4. What the rig keeps, and why

- **Devices and their files** — `[[devices]]`, `bindings.json`,
  `hands.json`, the pad tapes: what is plugged in, where it is, how it is
  wired. A preset **requests** a device by using it (a desk row, a hand
  route, a cloud node) and the rig says what is missing.
- **Tempo** (`tempo.bpm`, `.nudge`): the room's clock; a load must not
  retime the LFOs mid-set (D1, D5).
- **The analyzer** (`band.*`, `master.*`, `scene.select`, `audio.*`): the
  room's sound (D9).
- **Outputs**: how many, which screen, fullscreen, the render cap, the
  flips, each window's dim and mutes, overlay mode and its ground. The
  picture a window shows is the preset's (the bus cuts move); the window
  is the rig's.
- **Calibration**: the hands' box, ranges and units; the camera's
  reference eye the hands are fitted to (§3.2).
- **Feel**: `desk.slew`, `desk.pad.*`, every `hands.*` knob — how a
  control reads, not what it shows.
- **The master dim** (`output.dim`): 1 at every launch, never saved
  (decision in DECISIONS "Render and outputs").
- **The bank and the show**: the pads and the startup preset are the
  desk's; the show shrinks to "the rig's settings and the pads".

What the rig **loses**: the eye (C2), the hands' look, the cloud's look,
the bus cuts, the second hands node's seed, the desk templates and the
default-module fallback (D3). After D3 a show's `session` holds only
`tempo`, `hands`, `band`, `master`, `scene`, `audio`, `output`, `desk`.

## 5. What C2 must do — one orbit camera

**Done** (2026-11-02, wave 1). What differed from the list below:

- **Ids kept, `eye` a performance group** (§7.1): `eye` joins
  `PERFORMANCE_GROUPS` beside `camera` rather than folding the two params
  into the `camera` group's registration — `tests/test_params.py` holds
  every persisted id's first segment to its group, and the group move
  keeps both without a rename.
- **The pose is a `pose` section, not in `values`** (step 2): the six
  `rot.phase.*` under `"pose"` beside `values`, `view.body` folded in by
  `geometry.pose_angles` / `ViewState.pose`, set by `ViewState.set_pose`.
  The phases stay `persist=False` (the turn moves every frame: no base, no
  undo step, no dirty dot), and `values` stays the bases' snapshot. Old
  files keep spinning; the migration's resave takes the pose back out of
  a file that had none (`headless.resave`).
- **"The first load"** (step 2): an old preset takes the old show's eye
  on *every* load while that show is open (`Project.old_eye`, read out of
  the session by `_take`), not just the first — the same eye the tool
  writes into every preset, so a preset draws the same before and after
  the migration. Nothing in `app.main`.
- **The camera node's layout** (step 6): the camera's `render:` node was
  already homed in the preset's layout (`graphview.home`); C2 moves an old
  show's `render:camera` entry into the old presets' layout
  (`Project.camera_at`, `graphmigrate.nine`) and drops it from the show.
  `RIG_KINDS` loses `camera` (`ALWAYS_KINDS` keeps it for a patch's
  wire-as-saved); deleting the camera says `CAMERA_KEPT` ("the look's one
  camera"), not `NOT_REMOVABLE`; `patches.RIG_NODES` still keeps it out of
  a patch, in its own words.
- **The hands** (step 5, §7.7, both): the calibration is fitted to the
  reference eye; hands in the scene go through the preset's eye (they
  scale with the shape); a hands layer is drawn through the reference eye
  (`ghost.Settled.layer`) and keeps its size; render.py 3079 needed no
  change.
- **The migration** (step 3): `tools/migrate_library.py` runs the retaper
  first (`tools/retaper_routes.py`'s rewrite of unmarked patches, desk
  templates and `bindings.json`; presets by their own resave), backs up,
  picks the rig's show (`--show`, else this Mac's last show, else the
  library's only show; an eye already moved to `.bak-v2-eye` is read
  there), writes `/9` with that show open (the round-trip picture drawn
  with it open too), then rewrites the shows. The corpus was rewritten
  with the tool (`--to`), the build's default eye: no golden moved.
- **Hold** (step 7): `HELD_GROUPS` gains `eye` (the eye is its own group,
  so not held through `camera`); a pose loaded under hold waits on the
  hold and lands at Take (review 2.3: the turn is one for both, so landing
  it at the load would move the held projector).

Schema **`/9`** (not `/8`; §2). Files, in order:

1. `hyperspace/params.py`: take `"eye"` out of `SESSION_GROUPS`; register
   `eye.fov` and `eye.distance` under the camera group (either keep the
   ids and add `"eye"` to `PERFORMANCE_GROUPS`, or rename them to
   `camera.fov` / `camera.distance` with a read map for old `session`
   and `values` — the rename costs a mapping, a backup and an end-to-end
   test on an old file, REVIEW.md "Files on disk are a format"). Keep
   `modulatable=False` or lift it: with the eye the preset's, "a lane
   would swing the whole room" (row 182) is no longer the objection; the
   owner decides (§6). Remove the comment "the camera is the rig" (1791).
2. `hyperspace/preset.py`: `VERSIONS` gains 9; `document` writes the new
   schema; the pose (`rot.phase.*` / `view.body`) saved and landed if C2
   takes it (§3.1); `load_doc` lands the eye like any performance value;
   an old file's missing eye takes the **open show's** `session` value
   on the first load (so the Drive library draws as before) and the
   build's default when the show has none.
3. `hyperspace/graphmigrate.py`: `NINE_SCHEMA`; the one-way migration
   `seven` → nine writes the eye into `values`; `tools/migrate_library.py`
   rewrites the Drive library once with the rig's show open (the
   round-trip picture check already compares every output's hash — the
   eye change must leave it "same").
4. `hyperspace/library.py`: `Project._take` reads `eye.*` out of an old
   `session` (as `renamed_session` reads the spring) and hands it to the
   presets' first load; `Project.save` stops writing it; a first write
   over an old show keeps `<file>.bak-v2-eye` (the `.bak-v2-spring`
   pattern, `Project.write`).
5. `hyperspace/ghost.py` (`calibration`, `shared_camera`) and
   `hyperspace/render.py` 3079: fit the hands' default calibration to the
   rig's reference eye, not the preset's (§3.2), or the hands leave the
   world when a preset zooms the eye.
6. `hyperspace/ui.py` `_page_camera`: one section; drop "the room's
   camera, not the preset's". `hyperspace/graphview.py`: the camera node
   leaves `RIG_KINDS` (or stays always-drawn but is the look's; its
   `layout` entry moves from the show's to the preset's), line 43's
   docstring, `NOT_REMOVABLE`.
7. `hyperspace/hold.py`: `HELD_GROUPS` covers the eye (it does if the
   eye joins `camera`); `tests/test_hold.py`.
8. Docs: DECISIONS "Render and outputs" eye row rewritten (replace, do
   not add); "Presets and the desk" D1 rewritten to the contract's words;
   ENGINEERING §10 (the session list), §4 (the schema table), §14;
   ARCHITECTURE §3.1's `persist` row and §3.10; row 555 answered; a hand
   check: frame a picture, save, load another, load it back — the
   framing is back.
9. Goldens: `tools/golden_frames.py` draws with the eye at its defaults
   today; a `/9` corpus must carry the same values or every golden moves.
   Record none; prove none moved.

Decide before building (§6): the ids (keep or rename), the pose (C2 or
later), the eye's modulatability, row 521.

## 6. What D3 must do — the per-deck versus rig migration

D3's own design (two decks, a crossfade; the 2026-10-31 triage's "A/B
decks") is not in this repo yet; this is what the contract requires of
it, whatever shape the decks take. Schema **`/10`** (after C2's `/9`).

1. `hyperspace/params.py`: `ghost` and `cloud` move from
   `SESSION_GROUPS` to `PERFORMANCE_GROUPS`. `tests/test_params.py`'s
   "must" list and `test_snapshot_by_part` follow.
2. `hyperspace/ghost.py` `register` docstring ("the room's display");
   `hyperspace/preset.py` `GraphSection`: drop the show seeding
   (`self.lib`, `Project._held_back`, `library.py` 1099, 1174, 1180); the
   extra node's values are the preset's under the naming rule.
3. The bus cuts: `graph.RigWires` becomes the preset's — read from the
   loaded preset's section (`Renderer.rig_source` → the presets), written
   by `Presets.document`, undone with the preset's part; `library.Project`
   loses `rig`, `_saved_rig`, `RIG`; `graphview` 838/846/5898 and
   `BUS_SAID` / `CLOUD_SAID` stop saying "the show's"; `hold.program`
   holds the preset's cuts. A window the rig lacks is requested and said
   on OUTPUT and GRAPH (extend `devices.wants`).
4. Desk templates inlined: `tools/migrate_library.py` expands every
   `desk_template` (rows and modifiers) into the file and drops the key;
   `preset.py` retires `TEMPLATE_KEY`, `expand_desk`, `compact_desk`,
   `_desk_part`'s compaction, `_at_load`, `_mods_at_load`,
   `template_of_loaded`; `library.py` retires `DESK`, `DESK_SCHEMA`,
   `desk_template`, `default_name`'s `DESK` branch;
   `tests/test_desk_templates.py` becomes the migration's test. Hand
   check 156 is retired.
5. Module defaults: a preset load fills a missing id from
   `Library._fresh_of`, never `default.json` (`Presets.load_doc`'s use of
   `lib.resolved`); the strips keep `resolved`. Decide the `modules`
   labels' fate with row 540.
6. The per-deck split itself: everything in `PERFORMANCE_GROUPS` plus the
   preset's tables (`routes`, `modifiers`, `macros`, `desk` layer, the
   graph section and its cuts, the pose) is **a deck's**; everything in
   `SESSION_GROUPS` after D3 (`tempo hands band master scene audio
   output desk`) plus `bindings.json`'s rows, `hands.json` and the config
   is **the rig's single copy**. `hold.py` is the existing two-renderer
   precedent (one program, one preview, one registry): D3 replaces its
   "swap the bases around the draw" with a registry per deck or a deck
   index on every performance param — the triage's XL item.
7. `hyperspace/library.py` `Project`: the show shrinks to the rig's
   session, the pads and `startup`; `to_doc` / `_take` / `is_dirty`
   drop `rig`; ENGINEERING §10's one show line changes words.
8. Docs: DECISIONS rows for the ghost ("session, saved with the show"),
   the cloud, the rig wires (plan 36 T1), desk templates (plan 24 C3)
   and D3 of plan 13 — each **rewritten** in place; ENGINEERING §4, §10,
   §12 (the ghost table's "session group" line), §14; ARCHITECTURE §2's
   `RigWires` and §3.8; hand checks for the hands' look and the cuts
   surviving a load; the register rows D3 is assigned.

### What changed in the build (D3, 2026-11-03)

Built on plan 44 D3's branch, with the owner's three answers of
2026-11-03 (the wave 2 checkpoint): desk templates **retired**, the
`modules` labels **dropped** with the `default.json` fallback (row 540
resolved), `ghost.mirror` **stays the rig's**. Item by item:

1. `ghost` and `cloud` are in `PERFORMANCE_GROUPS`; `ghost.mirror` (and
   an extra node's `ghost.2.mirror`) is a **session key**
   (`params.SESSION_KEYS`), kept in its group, its value a
   `ghost.RoomSetting` on the session's param (row 612). The look an old
   show gives up is one id set (`graphmigrate.is_look_id`: the hands' and
   clouds' groups less the mirror), read out of the show and handed to old
   presets by the same rule; any other id stays the show's.
2. `ghost.register`'s docstring says the look's, the mirror the room's;
   `GraphSection._seed` is **kept for the session keys alone** (an extra
   node's mirror from the open show) — dropping it outright, as the item
   said, would lose `ghost.2.mirror` on a reopen (row 613).
   `Project._held_back` stays for the same reason.
3. The bus cuts are `Presets.bus`, saved under **`bus`** (row 617);
   `Project` lost `rig`, `_saved_rig` and the mark's rig entries
   (`RIG` stays, the key an old show is read by); the renderer's
   `rig_source` is the presets; `graphview`'s words and edits, and the two
   one-line UI reads (`ui.Panel.rig_now`, `ui_graph.render_edit`), follow.
   A window the rig lacks: the rule and the words
   (`graphview.wanted_windows`, `WINDOW_WANTED`), not yet drawn — the UI
   PRs' (row 623); `devices.wants` was not the place (it names Learn's
   targets).
4. Desk templates: **retired**, not inlined (none existed): the code is
   gone, `graphmigrate.ten` drops `desk_template` (and a templated desk's
   `dark` rows), `tests/test_desk_templates.py` is the migration's test,
   check 156 retired (row 620).
5. A preset load fills from `_fresh_of`; the labels are dropped (row 621).
6. The per-deck split is plan 44 D3's (rows 611, 614–616).
7. The show is `hyperspace.project/3`: the rig's session, the pads,
   `startup` (and, as before, the session groups' module names and the
   rig nodes' layout); a `/2` is read as its `/3`, what it held of the
   look handed to old presets (row 618).
8. The docs: the DECISIONS rows rewritten in place, ENGINEERING §4, §10,
   §12, §14, ARCHITECTURE §2 and §3.8, the register rows and the checks.

## 7. What the code could not tell me

Open for the owner, each a one-line answer. **Answered by the owner on
2026-11-02** (register rows 555, 572–576):

1. Ids: **kept** (`eye.fov`, `eye.distance`; a group move).
2. The pose: **always saved**, and a load sets the turn; an old file keeps
   spinning.
3. The eye: **modulatable** (row 182 overturned, row 574).
4. `ghost.mirror`: **a room setting** — D3's business, nothing for C2.
5. Row 521: **closed** — every save `/9` (row 576).
6. `modules` labels: **inert for now** (row 540 later).
7. The hands' calibration: **both** — "it depends on where the hands are
   rendered": in the scene they scale with the shape, as a layer they keep
   their size; the calibration is fitted to the reference eye (row 575).
8. Desk templates: D3's to count.

The questions as they were put:

1. **Ids.** Keep `eye.fov` / `eye.distance` (group move only) or rename
   to `camera.fov` / `camera.distance` (a read map, a backup, one more
   format)?
2. **The pose.** Does a preset save the spin's pose by default (every
   load restarts the turn where the preset was saved), or is it a chip
   on the save, or a later PR? Today's "left spinning" is a documented
   behaviour (D2's load order), not an accident.
3. **The eye's modulatability.** Still never a performer's (row 182's
   reason was that the eye was the room's), or a lane may breathe the
   fov now that it is the look's?
4. **`ghost.mirror`.** A look (preset) or a hardware fact about a mirror
   in front of the performer (rig)? Every other `ghost.*` is clearly the
   look's.
5. **Row 521.** With C2 every save is `/9`; confirm "every save the
   newest schema" closes it.
6. **`modules` labels** (row 540): inert and kept, or dropped with the
   default-module fallback?
7. **The hands' calibration against the eye** (§3.2): fit to the rig's
   reference eye (hands stay the same size on screen whatever the
   preset's eye) or to the preset's eye (hands scale with the shape)?
   The code does one thing today because the eye never moved.
8. **How many desk templates the Drive library holds.** The repo has
   none; the inlining migration's size depends on `<library>/desk/`.

## Sources

`hyperspace/params.py` (groups 146–150; `rot.phase` 1732; `eye`
1791–1807; `cloud` 1810–1830), `hyperspace/preset.py` (docstring;
`GraphSection` 223; `TEMPLATE_KEY` 490–520; `load_doc` 1000–1060;
`document` 1234–1296; `_values` 1300), `hyperspace/library.py`
(docstring; `DESK` 155–160; `LAYOUT` / `RIG` 205–208; `Project._take`
597–626; `to_doc` 643–655; `save` / `write` 1095–1180; `desk_template`
1703; `defaults` / `resolved` 1731–1755), `hyperspace/config.py`
(docstring), `hyperspace/graph.py` (`RigWires` 1264), `hyperspace/ghost.py`
(`register` 121; `calibration` 272–325; `shared_camera` 327–345),
`hyperspace/hands/core.py` (`register` 776–885; `Units` 1000–1030),
`hyperspace/hold.py` (`HELD_GROUPS` 80), `hyperspace/graphview.py`
(43, 838, 3029), `hyperspace/ui.py` (`_page_camera` 2291),
`hyperspace/graphmigrate.py` (58–72), `tools/migrate_library.py`,
`tests/test_params.py` (`_full_registry` 450), `docs/ARCHITECTURE.md`
§3, `docs/DECISIONS.md` (Render and outputs; Library and persistence;
Presets and the desk), `docs/DECISION-REGISTER.md` rows 182, 394, 521,
540, `docs/ENGINEERING.md` §4, §10, §12, §14.
