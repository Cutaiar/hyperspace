# Decisions

The design decisions in force in the Python app, one row each, so nobody
re-asks a settled question. Everything here is built; the code is the
reference for detail. Structure is in [`ARCHITECTURE.md`](ARCHITECTURE.md),
behaviour in [`ENGINEERING.md`](ENGINEERING.md).

**Who** says who decided:

- **owner**: settled with the owner.
- **row N**: built on a recommendation during an unattended run (rows
  34–88 on 2026-10-04, rows from 89 in plan 22 on 2026-10-06). The owner
  has still to confirm or overturn it in
  [`DECISION-REGISTER.md`](DECISION-REGISTER.md) under that row number.

To add a decision, add one row to the theme it belongs to. When it
replaces a row, rewrite that row instead of adding a new one.

## Platform

| Decision | Where | Who |
|---|---|---|
| One Python process: a moderngl renderer, sounddevice capture and an imgui control panel. The retired web app never runs; it is only the oracle the golden traces were recorded from. | `app.py` | owner |
| A DAW connects only through an optional bridge, which is off by default. Nothing in the core depends on it. | `bridge.py`, `[bridge] enabled` | owner |
| Parity bar: geometry is exact (1e-12, vertex order kept), audio is behavioural and visuals are judged by eye. | `tests/` | owner |
| Generalise before hardware: every input goes through registry ids and the binding table, never straight at the view state or the chain. | `params.py`, `routing.py` | owner |
| The analyzer runs in-process on the frame loop. MIDI is an adapter at the edges and never the internal bus: values flow as floats. | `analyzer.py`, `midi.py` | owner |
| The dream is part of the app. torch is an ordinary dependency and the worker is on by default, but torch is imported only when the dream opens. | `[dream] enabled = true` | owner |

## The control model

| Decision | Where | Who |
|---|---|---|
| **One parameter registry.** Everything settable has a stable id and one normalised interface (continuous, enum, toggle or trigger). | `params.py` | owner |
| **Base and effective value.** `p.base` is the user's setting. Once a frame, `Registry.apply` writes base plus the sum of offsets. | `Registry.apply` | owner |
| **Any param is a modulation target unless it is flagged `modulatable=False`.** That includes enums, toggles and triggers, which follow with hysteresis. | `Param.modulatable` | owner |
| **One path.** Every continuous source (lane, hand, ext, lfo) reaches a param only through `Router.modulate`. | `Router.modulate` | owner |
| **One performer per parameter.** A performer is an enabled route row from a continuous scheme. A second performer on the same target asks *Replace / Keep*, and gates do not exempt a row. The panel's tooltip names the param's owner. | `Bindings.owner`, `Router.describe` | owner |
| **Scene-setters write the base and never prompt**: the panel, keys, pad buttons, the APC40, presets, the mouse and the sticks. Relative writers read the base, not the effective value. | `Param.nudge`, `Param.scale` | owner |
| **Hands grab and never yield.** A performer row has no pickup. | `routing.py` | owner |
| **Two ops.** `push` adds depth · scale · (u − rest). `position` makes the source the param's fader along its taper, and the base returns when the source stops. | `routing.MOD_OPS` | owner |
| **Push is centred where the source rests.** The rest is the one the source's adapter publishes, unless the row sets its own. | `Router.rest_of` | owner |
| **Chaining, not stacking.** Layers come from a performer owning another source's knob (an LFO's depth, a macro), never from two rows on one target. | `routing.py` | owner |
| **One macro concept.** `macro.1–8` each have subscribers. A subscriber either sets a param's base or scales a route's depth, over its own from → to range, so polarity is per subscriber. A performer on a macro moves only its depth subscribers. Base subscribers follow the macro's base. | `routing.Macro`, `Router.follow_macros` | owner |
| A route keeps `scale` only when the scale names a session param (the MASTER drive fader on the six band → rotation routes). On a performance param, `scale` is dropped at load with a note. | `routing.migrate_scales` | owner |
| A preset's route may perform a session param. The preset never sets that param's value. The ROUTING page marks such a route "session". | `ui_routing.is_session_target` | owner |
| **Hand routes are addressed by name** (`hand:right.roll`, `hand:left.pinch.index`). A name the rig lacks leaves the row dormant and never moves it onto another axis. | `Router.address` | owner |
| A hand out of the box reads `NaN` on its axes, so every row on them lets go and the base returns that frame. The return spring and `hold` shape only the DAW output. | `Follower.live`, `HandsIO.lanes` | owner |
| A gate whose source is not live holds its row **shut**. Only fed sources (hand, ext, lfo) can gate; analyzer lanes cannot. | `routing.py` | owner |
| `rot.phase.*` is a param but is never saved. | `params.py` | owner |
| Presets carry the six band → rotation push rows over rate bases of 1, so the shape idles while spinning. Only `legacy6`, the parity anchor, sets those bases to 0. | `preset.legacy6_values` | owner |
| An older `bindings.json` migrates on load. Duplicate owners are settled first-wins, and the file is written back once. | `routing.SCHEMA_VERSIONS`, `remap_factory` | owner |
| **No backup, no rewrite.** `bindings.json` is never rewritten unless `routing.backup` has made a copy first. Without the copy, writes are refused for the session. What a launch changed is one line on the SYSTEM page. | `Bindings.unbacked`, `Bindings.said` | row 74 |
| Key modifiers are part of a row's source (`key:SHIFT+B`, `key:CONTROL+Z`; SHIFT, SUPER, CONTROL). A key press fires only the row whose modifiers match exactly what is held. | `routing.MODIFIERS`, `Router.keys` | row 34 |
| R, F1–F8, ⇧F1–F8, undo/redo and Home are binding-table rows, so they can be rebound. An older file gets each one only where its key is free. Cmd+R, Esc/Q and ↑/↓ stay in the loop. | `routing.LOOP_KEY_ROWS` | owner |
| `view.instances` goes down to 0, which shows "0 · nothing drawn": the ground, the echoes, the effects, the ghost hands and the dim still run. There is no separate "blank" param. | `params.py` `view.instances` | row 47 |
| Not modulatable: `dream.layer`, `dream.gap` and `dream.res` (each change rebuilds something); `tempo.tap`; `output.dim` and every `output.N.*` switch; `ghost.mirror`, `ghost.guide`, `ghost.tethers` and `ghost.style`; and every `fx.<name>.target`. Still modulatable: `fx.face_map`, `ghost.on`, `ghost.alpha`, `lfo.trigger`, `lfo.N.reset` and `preset.home`. | each `register` | rows 40, 49, 66, 87, 88; tap: owner |
| **A hand Learn onto a non-modulatable param is refused in words** and makes no row. A preset's saved route onto a known non-modulatable param is dropped at load with a note, and the file is not rewritten. | `Learn.learn_source`, `Presets.load_doc` | row 88 |

## Learn, Unbind and mapping

| Decision | Where | Who |
|---|---|---|
| **A Learn says what it waits for.** The menu offers "Learn desk" and "Learn hand ▸ left / right", and only that kind of source can complete it. Anything else does its own job. | `learn.WANTS`, `Learn.accepts` | row 60 |
| **A new hand Learn lands by a table.** A centred axis, or any axis onto a range centred on zero, lands a `push` at `hands.learn_depth` (0.25). A one-sided axis on a one-sided param, or any axis on an enum, toggle, trigger or whole-number param, lands a `position` row. Existing rows are never rewritten. | `Learn._row`, `learn.PUSH_DEPTH` | row 52 |
| **A learned axis drives one param.** A hand learn removes that axis's other push/position rows. Learning the same pair again only refreshes the gate. | `Learn._place` | row 53 |
| Whose pinch gates a hand learn is left as it was: the learning hand's thumb first, then the other hand's. Within the wanted hand, the axis that travelled furthest wins. | `HandsIO.held_gate`, `LEARN_MOVE` | row 64 |
| **The global layer is never a Learn target.** A Learn writes only into the loaded preset. A refused desk learn stays armed. | `learn.blocked` | owner (D5) |
| **An invariant control is not a learn candidate: it keeps doing its job through an armed learn.** | `MidiIO._handle` | row 61 |
| **One road onto the desk.** `Learn.learn_control` serves the MIDI adapter, a click on the on-screen desk and pick-then-click alike, so mapping works with no device. | `Learn.learn_control` | row 62 |
| **Click a desk control, then a param's widget, to map it.** Every page but ROUTING dims while a control is picked. A pick lets go after 20 s, or when its footer line is clicked. | `ui_desk.click`, `ui_desk.PICK_S`, `Learn.map_picked` | row 58 |
| **One Unbind.** It removes the loaded preset's desk rows and every route on the param as one undo step. It is offered only when it would remove something, and it never touches a session row. | `Learn.unbind`, `learn.bound` | row 59 |

## Inputs

| Decision | Where | Who |
|---|---|---|
| The Xbox pad is polled raw through GLFW with the app's own index map, not the gamepad-mapping database. | `gamepad.py` | owner |
| The APC40 is a device *profile* over a generic MIDI adapter. | `apc40.py`, `midi.py` | owner |
| APC40 feedback: **rings show the base** (while a knob glides, its target), and **LEDs show the effective value**. | `MidiIO._ring_norm`, `MidiIO.feedback` | owner |
| Hands are the primary performing surface. The APC40 keeps presets, scenes and master controls. | — | owner |
| **Twelve axes** (palm pose, six per hand), shaped as analog signals, plus eight pinch switches. **No gesture vocabularies and no more DOFs.** The skeleton is kept for display only. | `hands/core.py` | owner |
| The hands package is liftable: `core.py` and `signal.py` import nothing from the host. | `tests/test_hands_boundary.py` | owner |
| Pinch switches are a Schmitt trigger plus a debounce. | `hands/signal.py` | owner |
| Hand settings live in three places, each where it changes: rig settings in `[hands]`, the room (ranges and box) in `hands.json`, and the feel (including `hands.learn_depth`) in the hands params. | `hands/core.py` | owner |
| **The interaction box** bounds the palm in the Leap's mm. It is one box for both hands, with x symmetric. The calibration sweep sets it (2nd–98th percentile + `BOX_MARGIN`) and "reset ranges" opens it. No widget edits it. Its edge is a Schmitt edge (`BOX_EDGE`). | `load_box`, `inside`, `HandsIO._sweep_box` | row 50 |
| **A hand outside the box is absent everywhere**: NaN axes, presence off, pinches dropped and its ghost faded. Only the HANDS page shows it, drawn hollow. | `HandsIO.poll`, `ghost.box_of` | row 51 |
| Home on the keyboard is `key:HOME` only (fn ← on a laptop). | `routing.LOOP_KEY_ROWS` | row 38 |

## Tempo and LFOs

| Decision | Where | Who |
|---|---|---|
| **One free-running clock, tapped into time.** No DJ Link, no MIDI clock and no drift correction: re-tap. 4/4 is assumed. A synced LFO reads `clock.beat · ratio`. | `tempo.py` | owner |
| BPM is the mean of the burst's last 8 taps. A gap over 2 s starts a new burst. | `tempo.TAPS`, `tempo.GAP` | owner |
| **A tap never moves the downbeat.** Only the global trigger (⇧B, METRONOME) places it, and it restarts every synced LFO at phase 0. | `Clock.tap`, `Clock.trigger` | owner |
| A trigger or reset that fires after this frame's LFO step is held and applied at the start of the next step. | `LFOs.pending` | owner |
| Leaving a division for Hz carries the LFO's phase. Switching into a division lands on the beat. | `lfo.py` | owner |
| **Four LFOs**, each a performer. Every knob of each LFO is an ownable param. Output is `u = 0.5 + 0.5 · depth · wave`, at rest 0.5. | `lfo.N`, `lfo.REST` | owner |
| APC40: TAP TEMPO → `tempo.tap`, NUDGE ± → `tempo.nudge`, METRONOME → `lfo.trigger` (its LED blinks on the beat), QUANT → `preset.next`. | `apc40.DEFAULT_MAP` | owner |

## Audio

| Decision | Where | Who |
|---|---|---|
| The analyzer is an N-band (1–16) graphic EQ followed by the reference envelope, transient and shaper chain. Band → plane mapping is done by routes. | `analyzer.py` | owner |
| A factory `legacy6` preset reproduces the reference chain on the golden traces. | `library/presets/legacy6.json` | owner |
| The band editor shows a live spectrogram with the band curves over it. | `ui_bands.py` | owner |
| Per-band **AUTO / MANUAL** normalisation (`band.{i}.norm`, default AUTO). AUTO is the reference chain, bit for bit, known trim quirk included. MANUAL applies trim once as a plain gain. | `bands.NORMS` | owner |
| `master.dyn` keeps its 0.06×–4× range. Up to 1× it blends toward the normaliser; past 1× only the expansion grows. | `tapers.T_DYN` | owner |
| The eleven files under `library/band/` are the one scene store. | `control.SCENES`, `Analyzer.apply_scene` | owner |

## Shapes

| Decision | Where | Who |
|---|---|---|
| **A shape is honestly 4D or 3D** (`Shape.dims`). A 4D shape has real w-extent and every plane turns it. A 3D shape sits at w = 0 — nothing invented for a w it does not have — and the W planes, with whatever drives them, do nothing to it. This overturns plan 22's lifts (rows 89, 93–96) and its fold of the Heart's W planes onto 3D planes (row 90). | `geometry.Shape.dims`, `view_angles`, `is_3d` | owner, 2026-10-17 |
| The Shape menu is grouped by kind: sections 4D, 3D and Scenes, each in families (regular polytopes, uniform polytopes, Platonic solids, star polyhedra …; `geometry.MENU`); the index stays the identity. The VIEW header says 3D or 4D; the W plane keys dim while they can do nothing. | `ui.Panel._shape_combo`, `_page_view` | owner, 2026-10-17 |
| **The 3D switch holds a 4D shape's pose and turns it rigidly in 3D**, with no jump going on or off: the pose is folded into `ViewState.body` on the frame it changes. | `view.three_d`, `ViewState.integrate`, `geometry.shape_view` | owner, 2026-10-17 |
| A 3D shape's depth cue (line fade, width, draw order) reads its depth toward the 3D camera (z after the camera's yaw and pitch), as a 4D shape's reads w. | `geometry.shape_view`, `geometry.view_depth` | row 91 |
| **Every 4D shape keeps `VOLUME_FLOOR` (0.15) through a full turn of each W plane**, from rest and from a generic pose. The floor is half the polytopes' worst (the cubic pyramid, 0.30). A shape's digest hashes floats rounded to 1e-9. | `geometry.VOLUME_FLOOR`, `tests/test_shapes4d.py` | row 92 |
| The Möbius strip is 0.55 wide (was 0.45) and the Rose 0.16 deep (was 0.12), the sizes plan 22 gave them. | `geometry._build_mobius`, `_build_rose` | rows 94, 95 |
| **The Klein bottle is shape 26**: the classic bottle immersion, crossing itself as any Klein bottle in 3D does, 37 × 16 samples, centred. | `geometry._build_klein`, `_klein_xyz` | owner, 2026-10-17 |
| A face of more than four corners that is not planar (a lifted cap) is framed by its least-squares plane; every planar face keeps its basis. | `geometry._face_xy` | row 97 |

## Render and outputs

| Decision | Where | Who |
|---|---|---|
| The CPU transforms through the parity-proven `project()` and the GPU rasterises. Edges are screen-space quads at the reference width. | `render.py` | owner |
| **No imgui on any render output.** Everything for the operator is in the control window. | `app.py` | owner |
| **A render frame binds its target explicitly**, again on every exit, including a raise. | `app.draw_render`, `Lookback.capture` | owner |
| **Overlay mode only when the config asks** (`[output] overlay = true`, default off). Window and fullscreen are always opaque, and `view.cut_through` applies only in overlay. | `Output.allowed` | owner |
| **Up to four render outputs** (`[[output.screens]]`) show the same frame. Each output has `output.N.scene`, `output.N.hands`, `output.N.through` and, when there are two or more outputs, `output.N.dim`. With no list there is one output. | `outputs.py`, `outputs.MAX_OUTPUTS` | owner |
| Each output's switches are rig settings: never saved, not modulatable, and untouched by presets, shows and undo. Every launch and ⌘R takes them from the config, and a config `dim` under 0.1 is raised to 0.1. | `overlay.register_switches` | row 81 |
| Output 1's context renders every distinct picture. Each later output copies it in its own context; only output 1's swap waits for the screen. | `Renderer.draw_outputs`, `outputs.Presenter` | row 83 |
| An output of another shape shows the whole frame, letterboxed. | `outputs.fit` | row 82 |
| A later output whose screen is not connected at launch is not opened, and a note says so. Later outputs take their screen and fullscreen from the config only. | `app._later_output` | row 86 |
| **The crossfader is the master dim** on both desk layers (left is black). It multiplies each output's finished picture, times that output's own dim, as the last pass. It is a rig setting: 1 at every launch, never saved, with soft pickup. There is no blackout button. | `output.dim`, `Renderer.dim_pass` | owner |
| In overlay mode the dim fades colour and alpha together. On an opaque ground only the colour scales. | `Renderer.dim_pass` | row 41 |
| **The ghost hands** are drawn once a frame into their own layer, in a fixed camera framing the box. They are composited per output after the effects and before the dim, and they are never in the look-back history. `ghost.*` are session params, off by default. A raising hands pass is caught. | `ghost.py`, `Ghost.layer`, `Ghost.composite` | owner |
| `ghost.on` says whether the hands are drawn at all, and each output's hands tick says where they show. | `outputs.route` | row 84 |
| **`ghost.style`** picks one of five drawn objects from the same tracking data: HANDS (the default), JOINTS, PALMS, CAGE and MARIONETTE. | `ghost.PARTS` | owner |
| `ghost.style` is a session enum, saved with the show and learnable onto a desk control. | `ghost.register` | row 87 |
| **Hands through effects** (`output.N.through`, off by default). When on, that output's hands go in after the look-back composite and before the first effect. With the scene off and through on, the output shows the hands alone through the effects. | `Renderer._pipeline` | owner (switch); row 79 (where they go in) |
| The guide and the tethers' labels are never bent: when hands go through effects, they are drawn in a layer of their own laid on afterwards. | `Ghost.readout` | row 80 |
| **Instances are laid out by `view.inst_layout`: GRID, HEX or RING.** | `render.inst_positions` | row 71 |

## Effects and the look-back

| Decision | Where | Who |
|---|---|---|
| **Post effects are one GLSL file each** under `shaders/fx/`. Their `// @param` uniforms become `fx.<file>.<uniform>` params. New effects are new `.glsl` files, not Python. With every effect off, the frame is bit-identical. | `fx.py` | owner |
| **Each effect is aimed at the frame or the faces** (`fx.<name>.target`). The faces' effects run into a picture the faces show, per face or in screen space (`fx.face_map`). | `fx.TARGETS`, `fx.FACE_MAPS` | owner |
| The face picture is the whole face as face 0 shows it, 1024² (`render.FACE_PIC`), cover-fit in screen mapping. It is made before the scene pass, so the echoes and dream carry it. With nothing aimed at the faces, nothing runs. | `Renderer._face_picture` | row 65 |
| The two chains share one `FxState`, which advances the effects' clocks once a frame, and the faces' chain borrows the frame chain's programs. | `FxState.advance_to` | owner |
| The FX page's open strip is chosen by name, not index. It is in no file and is not an undo step. | `FxState.sel_name` | owner |
| On a chip, the name opens the effect and the dot at its left switches it (a diamond when the effect is aimed at the faces). Chips sit three to a row. | `ui_fx._chip`, `ui_fx.CHIPS_PER_ROW` | row 45 |
| The chip grid is the chain view. Dragging a chip onto another reorders the chain as one undo step. The order slider stays. | `fx.reordered` | row 67 |
| An effect is re-aimed by the ONTO frame / faces chips on the open strip's title line. A drag never changes a target. | `ui_fx._strip_header` | row 68 |
| An open effect that is not running says why, and its controls are dimmed by a veil but stay live. | `ui_fx.why_idle` | row 46 |
| **The dream is temporal**: one running buffer blended with each frame, a few gradient steps per frame. | `dream.py` | owner |
| The compositor re-colours the dream buffer (`dream.hue / sat / tint`). Echoes pass untouched. | `lookback.py` | owner |
| `dream.occlude` ("Shape hides wake"): the shape covers the wake where it drew. | `params.py` | owner |
| Echo time is in seconds: `dream.fade` is a half-life and `dream.gap` is the time between echoes. | `params.py` | owner |
| The LOOKBACK page has three sections: ECHOES, DREAM and BOTH. The dream layer is one menu of every layer of VGG16 and GoogLeNet (25), grouped by net, each with its name and a short description, a longer one on hover; the registry labels match the page. | `ui_lookback.SECTIONS`, `lookback.LAYER_INFO` | row 69 |
| `dream.layer` is stored as an index into `lookback.LAYERS`, which is append-only: a new layer goes at the end, so a saved look keeps its layer. The menu's order is `LAYER_INFO`'s. | `lookback.LAYERS` | row 69 |
| A net's weights are read once a run: every layer of that net is a cut of the same loaded stack. | `dream.build_trunk`, `DreamWorker.stacks` | row 69 |
| The dream's "speed" is `dream.k`, read as the dream frames in which a frame's share halves. | `params.dream_speed_text` | row 70 |

## Face patterns

| Decision | Where | Who |
|---|---|---|
| **Each pattern input means one kind of change on every pattern**, named, with 1.0 the design and 0–2.6 the range; the old per-mode meanings were dropped with nothing to migrate. | `patterns.py`, `shaders/patterns.glsl` | owner |
| **The eight inputs, in order: SCALE, GLOW, WARP, SPEED, COLOUR, SHARP, HUE, SPREAD**, so the factory's lane *i* → input *i* reads SUB swells, BASS flashes, MIDB bends, MID drives the speed, UPR flares the colour, AIR sharpens; HUE and SPREAD are left for an LFO, a macro or a knob. `patterns.py` holds the names, meanings and per-mode phrases, and the registry and the panel read them from there. | `patterns.INPUTS`, `patterns.MODES`, `routing.legacy6_routes` | row 98 |
| SPEED is folded into an integrated clock, `u_ptime`, so a moving SPEED changes how fast a pattern goes and never jumps where it is. | `Renderer._pattern_clock` | row 99 |
| A straight or unison design stays straight from WARP 0 to 1 and in step from SPREAD 0 to 1, and parts only above 1. GLOW never goes below 30% of the design's light. GLOW, COLOUR's grey end and HUE are one `finish()` over every mode. | `patterns.glsl` `warp`, `face_k1`, `finish` | row 100 |
| Counts are fixed: BLOOM seven petals, SPIRAL five arms, KALEIDO six-fold. | `patterns.glsl` | row 101 |
| **The FACES page is a browser**: a chip per pattern with a live swatch, the mode's one line, and eight named inputs that each say what they do in this mode and what drives them. The renderer draws the swatches only while the page asks. | `ui_patterns.py`, `Renderer.want_swatches` | row 102 |
| An input nothing drives offers its convention's source ("+ SUB" … "+ AIR", "+ LFO 1", "+ LFO 2") as a push at the factory depth, into the loaded preset, staying on FACES. What drives an input is a link to ROUTING filtered to it. | `ui_patterns.suggest`, `drivers` | row 103 |
| **METER and PULSE draw the bands themselves**: the app hands the renderer the analyzer's lanes each frame as a read-only render input (`u_levels`), never a param; no other mode reads them. | `app._bands`, `Renderer.bands` | row 104 |
| Patterns are appended, never inserted (a preset holds the mode as an index). Five were added — METER, PULSE, MARBLE, TRUCHET, KALEIDO — and the first twelve's art is unchanged. | `patterns.MODES` | row 105 |
| **The factory pattern routes push at `PATTERN_DEPTH` = 0.35** on a base of 1; the rate routes keep the reference's depth. `legacy6` keeps the rotation parity and drops the pattern parity. | `routing.PATTERN_DEPTH`, `preset.legacy6_values` | row 106 |
| The house presets' routes are generated from code, like the party presets'; their values and notes stay data. | `preset.HOUSE`, `FACTORY_PRESETS` | row 107 |
| Macro candidates are prepared for audition, never judged by the build, and are not factory presets: they live in the owner's library (they shipped in the repo's snapshot folder until plan 25 retired it; the test fixtures keep a copy). Per-band gain in a preset macro is a depth subscriber on the lane routes. | `tests/fixtures/macro-candidates/` | row 108 |

## Library and persistence

| Decision | Where | Who |
|---|---|---|
| The library home is `~/Hyperspace` (or `HYPERSPACE_HOME` / config). Factory files ship read-only in the repo, and a user file shadows a factory file of the same name. | `library.py` | owner |
| A module preset is one group's values (`hyperspace.preset/1`), a preset is `hyperspace.preset/2` and a show is `*.hyp.json` (`hyperspace.project/2`). Unknown ids are reported, not fatal. | `library.py` | owner |
| The library is watched like source: editing a file shows in the running app. The library's own renames and trash moves are never re-applied. | `hotreload.py`, `Library._sync` | owner |
| `<home>/bindings.json` holds only the session's controls. A show carries no routing of its own. | `routing.FILE` | owner |
| **A preset file about to be overwritten or deleted is copied to `<home>/trash/` first.** | `library.to_trash` | owner |
| …only when the text differs. A failed copy warns and lets a save go on, but refuses a delete. | `library.to_trash` | row 37 |
| The windows open where the config says, otherwise where they were (`<home>/windows.json`, one render rect per output). Fullscreen is never remembered. The file is written on quit and ⌘R only. | `placement.py` | row 48 |
| **A dirty dot compares floats within undo's tolerance**, so a performer's round-off lights no dot. | `undo.alike` | owner |
| **Presets are shared through a cloud-synced folder, not git** (D1): `[library] path` points the library — `presets/`, `projects/`, every module group folder, `hidden.json`, `trash/` — at that folder (D2). Machine files stay in the home: `config.toml`, `bindings.json` and its backups, `hands.json`, `windows.json`, `last_show`, logs, `weights/` (D3). Unset or `""` is the home, as before (D4). | `config.py`, `library.py`, `app.main` | owner, row 109 |
| **A missing shared folder is never created and never silently replaced** (D5): a loud warning, every write refused, only the factory listed; fix the folder and restart. | `Library.missing`, `Library.writable` | owner, row 109 |
| **The old sharing mechanisms are removed** (D6): the home-as-git switch (a `.git` in a cloud folder risks corruption, and the cloud keeps versions) and the repo's snapshot folder with its install tool. Factory presets and `hidden.json` are out of scope (D7). `tools/move_library.py` copies an existing library into the shared folder once, never overwriting (D8). | `tools/move_library.py` | owner, row 109 |

## Presets and the desk

The D-numbers are cited from code comments.

| Decision | Where | Who |
|---|---|---|
| **D1 Two nouns.** A *preset* is one file holding a performance moment: every performance param's base, the performer rows, the APC40's preset layer and a label per module. A *session* is what makes the rig ready, and a preset never touches it. | `preset.py`, `params.PERFORMANCE_GROUPS` | owner |
| **D2 A preset load replaces everything**: every performance base, every route, the desk's preset layer and the macros. There is no merging. | `preset.py` | owner |
| **D3** Module presets stay: one group, cycled from that group's strip. A preset records each group's module preset as a label only and never chain-loads it. | `Library.label` | owner |
| **D4** The APC40 has two layers under a **latched SHIFT**, and its LED shows which layer is up. Loading a preset drops to the preset layer. | `desk.shift`, `Bindings.toggle_layer` | owner |
| **D5** The global layer is defined in the session's files. Its track knobs K1–K5 are the hand feel (smoothing, response, catch, the selected axis's return) and `tempo.bpm`. K6–K8 are free. | `apc40.DEFAULT_MAP` | owner |
| **D6 Invariant controls** have one meaning on both layers, and no preset maps them: the faders, the crossfader (master dim), clip rows 1, 4 and 5 (the bank: a tap loads, a hold on an empty slot saves), SHIFT, TAP TEMPO, METRONOME, NUDGE ±, QUANT, OVERDUB (home) and the transport. A preset's row on one of them is dropped at load with a note. | `apc40.DEFAULT_MAP`, `apc40.BANK_PADS` | owner |
| **D7** On a layer switch the knobs **jump** to the layer's values (the ring re-bases the encoder) and the faders **soft-pick-up**. | `apc40.RING_REBASES_KNOB` | owner |
| **D8** A control the preset does not map **does nothing** and shows dark. It never falls through to the other layer. | `routing.py` | owner |
| **D9 The analyzer is session**: bands, dynamics, scenes and the drive fader are never in a preset. | `params.SESSION_GROUPS` | owner |
| **D11** A show names its **startup preset**, which loads at launch. | `Project.startup`, `load_startup` | owner |
| **D12** A modifier is read **at the press**. SHIFT's release never re-evaluates a button already down. | `midi.py` | owner |
| **The bank is twenty-four slots.** F1–F8, ⇧F1–F8 and clip row 1 are slots 1–8, and clip rows 4–5 are slots 9–24. A slot names a preset file. | `library.SLOTS`, `params.F_KEYS` | owner |
| Slots 9–24 have no triggers of their own (they use `preset.select`). The show file stays `hyperspace.project/2` and holds the bank only up to its last filled slot. The factory party show has TRACER on slot 9. | `library.bank_doc` | row 72 |
| A bank pad is green when its preset is loaded, amber when its slot is filled and dark when empty. The old factory shape rows on those pads drop quietly at load. | `routing.led_level`, `routing.RETIRED_DESK_ROWS` | row 73 |
| **Home is the show's "starts on" preset**, on OVERDUB and the Home key. It is one undo step. | `Project.home`, `preset.home` | owner |
| **The desk never overwrites a preset.** Holding an **empty** bank pad about 0.6 s saves the live state as a new preset ("TRIP 2") into that pad's slot; holding a filled pad just loads it. (Until 2026-10-09 a hold on the clip-stop row saved into the next empty slot; that row is now free for Learn.) Panel Save and ⇧F1–F8 still overwrite. A pad is freed, the preset kept, with the slot's right-click → *free this pad (keeps the preset)*. | `Project.save_into`, `Param.held`, `midi.HOLD_S` | owner |
| The save-as details: a `hold` op fires once while held; the eight buttons are one bar; the new pad blinks; names are counted against files, names and bank; and the new preset becomes the loaded one. | `routing.OPS`, `library.next_name` | row 42 |
| A preset load clears a fader's catch only when the load moved its param. | `MidiIO.redraw` | row 44 |
| **Knob smoothing**: absolute knob and fader values glide over `desk.slew`, 80 ms by default and at most 250 ms (`routing.SLEW_MAX_S`), always under undo's settle time. | `routing.SLEW_DEFAULT_S`, `MidiIO._glide` | row 54 |
| `desk.slew` and `hands.learn_depth` are session params, and neither is on a global-layer knob. | `routing.register_desk` | row 55 |
| A device knob only where it does something. A fresh preset layer's D1–D4 are 4D depth, yaw, pitch and the face pattern, and D5–D8 are dark. | `apc40.SCENE`, `preset.knob_desk` | row 75 |
| The party show is what the rig opens and the last show opened is remembered. The house moods are a `house` show. | `library.DEFAULT_PROJECT`, `last_show` | owner |
| The party show's F1–F8 are TUMBLE, FACES, FIELD, WAKE, TRIP, ACID, MANDALA and NOITA, so every effect is in some factory preset; TRACER is on slot 9. | `hyperspace/library/projects/party.hyp.json` | owner |
| The party presets are composed with six DOF only: every hand row is a push from the axis's rest, with no pinch dependence. Rate-type params under a hand are allowed. | `tests/test_plan12_presets.py` | owner |
| `hands-orbit` is a factory preset: five pushes onto camera params (zoom depth 0.12). | `preset.hands_orbit_routes` | row 56 |
| **Unwanted presets are hidden or trashed from the list.** × hides a factory preset (`<home>/hidden.json`) and trashes one of yours. | `Library.hide` | owner |
| Hide, rename and the trash live in the preset list. Rename is refused on a factory preset and repoints every user show. Emptying the trash is the one delete with no copy kept, and it asks twice. | `Library.rename`, `Library.empty_trash` | row 76 |

## Undo

| Decision | Where | Who |
|---|---|---|
| **Undo reaches single edits.** A step is one gesture or one replacing action (any load, home, a Learn, an Unbind, a delete). Once a frame `Undo.tick` fingerprints every watched base and the loaded preset's tables, and 0.4 s of quiet ends a step. A performer makes no step. Undo puts back only what differs and writes no file. The stack holds 100 steps. | `undo.py`, `undo.SETTLE_S`, `undo.LIMIT` | owner |
| Undo is on ⌘Z and Ctrl+Z, and ⇧ redoes. | `routing.LOOP_KEY_ROWS` | row 34 |
| A tap, a nudge or a typed BPM is not an undo step: the `tempo` group is not watched. | `undo.EXCLUDED_GROUPS` | row 36 |
| Camera moves are undo steps. | `undo.watched` | row 39 |
| A drag that pauses for longer than the settle time becomes two steps. | `undo.SETTLE_S` | row 43 |

## UI

| Decision | Where | Who |
|---|---|---|
| Legibility at a distance comes first: rounded frames, pill chips, filled faders, no page scroll at the control size. The master faders are on the AUDIO page. | `ui.py` | owner |
| The Replace / Keep prompt is drawn on every page, even with the panel collapsed. | `ui_routing.py` | owner |
| The ROUTING page is one page over the loaded preset: its routes, its desk rows and macros, and the session's rows read-only below. | `ui_routing.page` | owner |
| **The cheat sheet is off at every launch.** `/` and the APC40's DETAIL toggle it (the pad's MENU did until 2026-10-14; held, it now saves a new preset). The desk diagram stays on. | `ui.cheatsheet` | owner |
| The desk's glyphs (K1–K8, D1–D8, S1–S8, SM, X, C, G, B1–B22, ⇧) appear on every ROUTING row and Learn message, with an APC40 diagram of the layer that is up. | `apc40.LAYOUT`, `ui_desk.py` | owner |
| The on-screen desk takes the room it has, and there is no DESK page. Once a unit is 44 × 32 px, every lit control carries its label. | `ui_desk.room`, `ui_desk.LABEL_UNIT` | row 57 |
| The ROUTING page has one filter field. Only the user clears it, or a click on a desk control. | `ui_routing.matches` | row 63 |
| The param's menu also opens from a row's label and from every analyzer meter. | `Panel._ctx_label` | owner |
| The VIEW page's field is one row, and the six plane rates are three rows of two. | `Panel._page_view` | owner |
| The dirty dot is a 12 px red disc and the save chip is solid red while there is something to save. On a factory preset, save reads "save copy". Saving never prompts. | `ui.dirty_dot`, `ui_presets.save_label` | row 77 |
| The OUTPUT page says in words what each output shows, and there is no picture of the render. The footer names a black output. | `ui.output_shows`, `Panel._output_blocks` | row 85 |

## Process

| Decision | Who |
|---|---|
| Each code PR gets a `/code-review` before merge. Agents work on their own branches, and the owner merges. | owner |
| Agent work lands on an integration branch, never on `main` (`finish-line` through plan 21, `plan-22-integration` for plan 22); the owner merges it into `main`. | owner |

## Decided not to build

| Not built | Who |
|---|---|
| Auto BPM: deferred, so tempo stays tap-only. | owner |
| Preset folders. Hide and trash instead. | owner |
| Drag-to-map. Click a control, then a param, instead. | owner |
| A band added, removed or moved is not an undo step. A `band.*` value is put back only onto the band layout it was taken on. | row 35 |
| The two-hand "steering wheel" camera. `hands-orbit` instead. | row 56 |
| A source-first hand learn (click an axis, then a param). | row 64 |
| A thumbnail of each output in the control window. | row 85 |
| DJ Link, MIDI clock in and drift correction. | owner |
| New 4-polytope families in plan 22: ranked in [`plans/22-polytope-shortlist.md`](plans/22-polytope-shortlist.md). The owner picked its recommendation (2026-10-17), built in plan 28: the snub 24-cell, rectified 24-cell, bitruncated and omnitruncated 5-cell, grand antiprism and disphenoidal 288-cell. The rest is not built. | owner |
