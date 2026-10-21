# Decisions

The design decisions in force in the Python app, one row each, so nobody
re-asks a settled question. Everything here is built; the code is the
reference for detail. Structure is in [`ARCHITECTURE.md`](ARCHITECTURE.md),
behaviour in [`ENGINEERING.md`](ENGINEERING.md).

**Who** says who decided:

- **owner**: settled with the owner.
- **row N**: built on a recommendation during an unattended run (rows
  34–88 on 2026-10-04, rows 89–108 in plan 22 on 2026-10-06, rows
  110–139 in plan 24, rows 140–168 in plan 27 and rows 169–209 in plan
  26 on 2026-10-14, rows 210–213 in plan 27's B6 on 2026-10-15, and
  rows 214–232 in plan 30 and rows 233–277 in plan 28 on 2026-10-17,
  and rows 278–290 in plan 28's N7 on 2026-10-20).
  The owner
  has still to confirm or overturn it in
  [`DECISION-REGISTER.md`](DECISION-REGISTER.md) under that row number.

To add a decision, add one row to the theme it belongs to. When it
replaces a row, rewrite that row instead of adding a new one.

## Platform

| Decision | Where | Who |
|---|---|---|
| One Python process: a moderngl renderer, sounddevice capture and an imgui control panel. The retired web app never runs; it is only the oracle the golden traces were recorded from. | `app.py` | owner |
| A DAW connects only through optional devices: the bridge (lanes out, `ext` lanes in), off by default, and the hands' DAW out (`hands-daw`, a `midi-out` sink). Nothing in the core depends on them. | `bridge.py`, the `bridge` and `midi-out` entries | owner |
| **The device registry** (plan 27): every input and output is a `Device` — open, poll each frame, close — publishing its sources as ports (values, and triggers with velocity), their names and rests, and a status (`connected`, `lost`, `off`, `error: …`) for the SYSTEM page. Devices are listed in `config.toml` as `[[devices]]` and come and go without a relaunch; several MIDI ports at once, each with its own profile; source schemes come from the registry, not a fixed tuple; sinks are devices too; a point-cloud source type exists. Done when the APC40, the pad and the hands run on it and an OSC device is added with no edit to `app.py`. | `devices.py` | owner |
| **Adding a device is a class and one line in the kind table**, never an edit to `app.py`: `osc.py` and `devices.kinds()` are the only code that names the OSC device. | `devices.kinds`, `tests/test_osc.py::test_only_osc_py_and_the_kind_table_name_the_osc_device` | owner |
| **The core never imports `midi`, `bridge`, `dream`, `osc`, `torch` or `leap`**; adapters only `feed`; the hands package stays liftable. `devices.py` is the one importer of every adapter module, each inside its device's `open`. | `tests/test_app_boundary.py`, `tests/test_hands_boundary.py` | owner |
| A config with no `[[devices]]` list keeps working: the old `[midi]`, `[gamepad]`, `[hands]` and `[bridge]` tables become the equivalent entries at load (`pad`, `apc40`, `leap`, `bridge`), one note per table the file holds. With a list, the list says. `[dream]` is a worker, not a device. | `config._translate`, `config.DEVICE_TABLES` | row 140 |
| `config.toml`'s mtime is looked at every 30 frames and only the device list is re-read; a bad edit is a note and the old list stands. A device whose `open` raised is retried every 2 s five times, then every 10 s; a `lost` device reconnects itself. Devices close last listed first, the pad included. | `DeviceRegistry.watch`, `retry_after`, `DeviceRegistry.close` | rows 144, 145 |
| The `Device` protocol's frame slots: `poll`, `learn`, `act` in the scene-setter slot; `feed` in the feed slot; `send` after `reg.apply`. One `Port` type describes a device for the node editor. The SYSTEM page shows one line per device. | `devices.Device`, `devices.Port`, `ui.device_lines` | rows 142, 143, 146 |
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
| **One path.** Every continuous source (lane, hand, ext, lfo, a device's own scheme) reaches a param only through `Router.modulate`. | `Router.modulate` | owner |
| **Two input ports per param**: the base takes many scene-setters, last touch wins; the modulation takes one performer, under the referee. Combining two performers is an explicit `combine` modifier (plan 28). The GRAPH page draws them as a square `base` stub and a round `mod` stub. | `routing.Owned`, `routing.referee`, `Router.modulate`, `modifiers.KINDS` | owner (plan 28 decision 9) |
| **The modulation is a graph evaluated in dependency order** (plan 28): each node — a fed lane, an LFO, a modifier, a macro, a param — runs after everything it reads, so an LFO owning another's depth, a macro scaling a push and a modulated `scale` land the same frame; there is no one-frame lag. **Nothing reads a stale value but through a delay node**: a loop through no `delay` modifier keeps its last cable off, with a note. The sinks still read after `apply()`. Today's routes convert one-to-one into cables. | `patch.py`, `Router.build_patch`, `Router.modulate` | owner (plan 28 decisions 7, 13) |
| The pass lands only the params a later node reads (`Param.apply` under a frame mark, never twice); the rest land in `reg.apply()` in registry order. The patch is cached on a key built each frame. A loop's last cable in table order is the one cut, its row kept; a delay that closes a loop runs first, one frame late. | `Registry.begin_frame`, `Router._patch_key`, `Router._rebuild_patch`, `patch.ordering` | rows 233–237, 239 |
| **Modifiers** — `curve`, `scale`, `smooth`, `combine`, `threshold`, `delay` — are value nodes between sources and routes; each publishes `mod:<n>`, which a route sources like any lane, and its params `mod.<n>.<p>` are performance params. A modifier whose input is not live reads NaN (its routes let go). Ids are one past the highest; a removal leaves its routes dormant. | `modifiers.py`, `routing.declare_modifiers`, `Router._step_modifier` | rows 240–242 |
| **Roles, not serials.** A `[[devices]]` entry has a `role` (`apc40`, `pad`, `leap`, `phone`), the name rows and the SYSTEM page use; the session maps roles to physical devices (a port, USB, a host and port). A preset names a role's sources; a device the rig lacks is `lost` or unlisted and its rows wait, dormant — on the GRAPH page, from a grey placeholder node named by the role (plan 28). | `config._device`, `Router.lane`, `graphview.source_pin` | owner (plan 28 decision 11); row 275 (the placeholder) |
| **Values and triggers are two signal kinds.** A value (an axis, a fader, a lane) is fed; a trigger (a hit, a button, a pad, with a velocity when it has one) is delivered as rows through the table. Encoder or fader behaviour, soft pickup included, is set by the device profile. A `threshold` modifier crosses a value into a trigger lane; a `smooth` follows either. | `devices.Port.kind`, `routing.is_continuous`, `modifiers.OUT` | owner (plan 28 decision 10) |
| **A device may expose layers**, so a device with a mode switch is one node per mode: **the APC40 is two nodes**, *apc40* (the preset layer's rows and every invariant control) and *apc40 (SHIFT)* (the global layer's), no layer view; D1, D4–D6 and D12 hold, and the APC40's map and feel are untouched (Dylan's). | `Device.layers`, `Bindings.layer_of`, `graphview.device_nodes` | owner (plan 28 decision 12); rows 270–273 (ids, groups, the latch, a shadowed row) |
| A new device publishes under its role (`phone:x`); today's devices keep the schemes their rows already name (`hand`, `axis`, `ext`, `cc`), and two enabled devices never feed one Router key (since plan 27 B6 a second pad feeds its own, `axis@<role>`; a second hands device is refused). A continuous source is any scheme the table does not dispatch as a row; which schemes exist, and in what order a page offers them, is the registry's (`lane`, `lfo`, then each device's feeds in list order). | `Device.schemes`, `devices.make`, `routing.is_continuous`, `Router.use` | rows 141, 150 |
| **A sink row** sends a param's effective value (`param:<id>`) or an analyzer lane (`lane:<i>`, `lane:*`) out on a sink port, `<role>:<channel>`. It is the session's (sinks are rig), never a performer, never asks Replace / Keep and is never in a preset. | `routing.SINK_OP`, `sink_values` | row 155 |
| **One performer per parameter.** A performer is an enabled route row from a continuous scheme. A second performer on the same target asks *Replace / Keep*, and gates do not exempt a row. The panel's tooltip names the param's owner. | `Bindings.owner`, `Router.describe` | owner |
| **Scene-setters write the base and never prompt**: the panel, keys, pad buttons, every MIDI desk, an OSC device's hits, presets, the mouse and the sticks. Relative writers read the base, not the effective value. | `Param.nudge`, `Param.scale` | owner |
| **Hands grab and never yield.** A performer row has no pickup. | `routing.py` | owner |
| **Two ops.** `push` adds depth · scale · (u − rest). `position` makes the source the param's fader along its taper, and the base returns when the source stops. | `routing.MOD_OPS` | owner |
| **Push is centred where the source rests.** The rest is the one the source's device publishes, unless the row sets its own. | `Router.rest_of` | owner |
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
| Not modulatable: `dream.layer`, `dream.gap` and `dream.res` (each change rebuilds something); `tempo.tap`; `output.dim` and every `output.N.*` switch; `ghost.mirror`, `ghost.guide`, `ghost.tethers` and `ghost.style` (and a second hands node's, `ghost.2.*`); every `fx.<name>.target`; `eye.fov` and `eye.distance` (the camera is the rig); `cloud.colors`. Still modulatable: `fx.face_map`, `ghost.on`, `ghost.alpha`, `lfo.trigger`, `lfo.N.reset`, `preset.home`, `view.screen_strokes` and `cloud.size` / `scale` / `bright`. | each `register` | rows 40, 49, 66, 87, 88, 182, 190, 206; tap: owner |
| **A hand Learn onto a non-modulatable param is refused in words** and makes no row. A preset's saved route onto a known non-modulatable param is dropped at load with a note, and the file is not rewritten. | `Learn.learn_source`, `Presets.load_doc` | row 88 |

## Learn, Unbind and mapping

| Decision | Where | Who |
|---|---|---|
| **A Learn says what it waits for.** The menu offers "Learn desk" and "Learn hand ▸ left / right" (and Learn pad, and "Learn <role>" for any other listed device that feeds), and only that kind of source can complete it. Anything else does its own job. What can be armed is "desk" plus each listed device's `wants`, not a fixed tuple. | `Learn.wants`, `DeviceRegistry.wants`, `Learn.accepts` | rows 60, 151 |
| **Learn sink ▸ <role>:<channel>** sends a param out on a sink port: the pick lands at once as a session row in `bindings.json`, with no question, no undo step and no preset dirt. | `Learn.learn_sink`, `ui.sink_items` | row 158 |
| One knob per param **per desk**: a desk learn replaces the param's knob on the same desk only. | `Bindings.bind` | row 154 |
| **A new hand Learn lands by a table.** A centred axis, or any axis onto a range centred on zero, lands a `push` at `hands.learn_depth` (0.25). A one-sided axis on a one-sided param, or any axis on an enum, toggle, trigger or whole-number param, lands a `position` row. Existing rows are never rewritten. | `Learn._row`, `learn.PUSH_DEPTH` | row 52 |
| **A learned axis drives one param.** A hand learn removes that axis's other push/position rows. Learning the same pair again only refreshes the gate. | `Learn._place` | row 53 |
| Whose pinch gates a hand learn is left as it was: the learning hand's thumb first, then the other hand's. Within the wanted hand, the axis that travelled furthest wins. | `HandsIO.held_gate`, `LEARN_MOVE` | row 64 |
| **The global layer is never a Learn target.** A Learn writes only into the loaded preset. A refused desk learn stays armed. (On the GRAPH page a drag from the *apc40 (SHIFT)* node into a `base` stub is refused for the same reason.) | `learn.blocked`, `graphview.Edit` | owner (D5) |
| A modifier's lane completes only a Learn armed for anything or for "mod"; no menu entry learns one. | `Learn.accepts` | row 246 |
| **An invariant control is not a learn candidate: it keeps doing its job through an armed learn.** | `MidiIO._handle` | row 61 |
| **One road onto the desk.** `Learn.learn_control` serves every MIDI desk, a click on the on-screen desk and pick-then-click alike, so mapping works with no device. | `Learn.learn_control` | row 62 |
| **Click a desk control, then a param's widget, to map it.** Every page but ROUTING dims while a control is picked. A pick lets go after 20 s, or when its footer line is clicked. | `ui_desk.click`, `ui_desk.PICK_S`, `Learn.map_picked` | row 58 |
| **One Unbind.** It removes the loaded preset's desk rows and every route on the param as one undo step. It is offered only when it would remove something, and it never touches a session row. | `Learn.unbind`, `learn.bound` | row 59 |

## Inputs and devices

| Decision | Where | Who |
|---|---|---|
| The Xbox pad is polled raw through GLFW with the app's own index map, not the gamepad-mapping database. | `gamepad.py` | owner |
| The APC40 is a device *profile* over a generic MIDI adapter; each `midi` entry names its profile. | `apc40.py`, `midi.py` | owner |
| **Several MIDI desks at once**, each a `midi` entry with its own profile. The `generic` profile (plain CC, note and pitch; nothing sent back; the entry names its `port`) lets a second controller map on Learn desk with no code. | `generic.py`, `midi.PROFILES` | owner (several ports, own profiles); row 149 (the profile) |
| One desk reads the unqualified rows (every row before plan 27): the first MIDI entry whose profile is `bindings.json`'s, else the first listed. Any other desk's rows carry its role, `cc@<role>:<ch>:<n>`. | `routing.QUALIFIER`, `DeviceRegistry.midi_roles` | row 147 |
| SHIFT (`desk.shift`) is that first desk's latch; every other desk has a layer of its own and no SHIFT; a preset load drops every desk to the preset layer. | `Bindings.layer_of`, `MidiDevice.layers` | row 148 |
| The pad is a device: it publishes its axes and runs the sticks' camera job itself, right after its rows. | `gamepad.publish`, `gamepad.steer`, `PadDevice` | row 152 |
| **Several gamepads at once** (plan 27 B6), each a `gamepad` entry reading its own controller (the next free GLFW joystick in list order, or `joystick = n`). The first enabled pad owns the unqualified rows (every row before B6, the factory rows) and the sticks' camera job; any other pad's rows carry its role, `pad@<role>:A`, `axis@<role>:LX`, and it starts with none. The `@<role>` qualifier works on any scheme. One USB reader, lent each poll to the first `usb = true` pad with no GLFW joystick and kept while it has none; "Learn <role>" for a second pad; one pad feel; the hands stay single. | `routing.base_scheme`, `Bindings.primaries`, `devices.primaries_of`, `gamepad.Claims`, `PadDevice` | owner (several pads, "without having to change much", 2026-10-15); rows 210–213 |
| The hands' device is a thin wrapper in `hands/device.py`; the hands' one call runs in the feed slot. | `hands.device.HandsDevice` | rows 143, 153 |
| The hands' DAW out is a `midi-out` sink, `hands-daw`: `HandsIO` makes the messages and opens no port. `[hands] out` becomes that entry at load. | `devices.MidiOutDevice`, `HandsIO.carry`, `config._daw` | row 157 |
| The bridge is one device with two halves: `ext` in (with its labels and rests), sink rows out after `reg.apply`. Its old `send` list becomes sink rows once, marked `"sinks_seeded"` in `bindings.json`. A sink's SYSTEM line says how many rows it sends. | `devices.BridgeDevice`, `DeviceRegistry._seed_sinks` | rows 156, 159, 160 |
| **An OSC device** is added by a `[[devices]]` entry alone (`kind = "osc"`): its role is its scheme, an address is a source name (`/1/fader1` → `phone:1/fader1`), its hits are rows under the same scheme with a velocity; values are the first number mapped from `range`, held while the sender is silent; the socket is read in `poll`, UDP `0.0.0.0:9000` by default. | `osc.py` | owner (no edit to `app.py`); rows 161–164 |
| **A point cloud is a source type, not a scalar lane**: `devices.PointCloud` (read-only N×3 float32, a time, a frame id, bounds, optional colours) on the registry as `cloud:<role>` (`DeviceRegistry.clouds`), never through the Router. A `cloud` device plays a recorded version-1 `.npz` at its own rate. The Kinect and the live sensors are plan 29. | `devices.PointCloud`, `devices.CloudDevice` | owner (the type); rows 165–168 |
| APC40 feedback: **rings show the base** (while a knob glides, its target), and **LEDs show the effective value**. | `MidiIO._ring_norm`, `MidiIO.feedback` | owner |
| Hands are the primary performing surface. The APC40 keeps presets, scenes and master controls. | — | owner |
| **Twelve axes** (palm pose, six per hand), shaped as analog signals, plus eight pinch switches. **No gesture vocabularies and no more DOFs.** The twelve axes stay as they are; the dance sources and the grab below are added beside them as sources (2026-10-12). | `hands/core.py` | owner |
| **The dance sources** (plan 24): per hand `hand:<side>.curl.<finger>` (five), `.spread`, `.energy` and `.flick`; for both hands `hands:gap` and `hands:twist`. Each is routable like any hand source and idles at its rest. Curls and spread read the skeleton. A flick spikes and decays until a trigger kind exists. No preset is built on them yet: that is the owner's authoring pass. | `hands/core.py` `DANCE`, `PAIR`, `Dance` | owner |
| The dance lanes go after the pinch switches and `hands:` is a scheme of its own, so no older lane moves. | `hands.addresses`, `Layout` | row 124 |
| Curl is the summed bend of a finger's joints; spread is the index–pinky fan in the palm's plane; energy is the mean speed of palm and tips; a flick is the fastest tip passing 1500 mm/s; gap is the palms' distance and twist the right roll less the left. | `hands/core.py` (the `DANCE` constants) | rows 125–128 |
| **The grab switch** (plan 24): `hand:<side>.grab` closes on a fist and is a gate like the pinches. What it is for — the shape following a closed hand — is a mapping the owner authors; nothing in a preset uses it yet. | `hands.fist`, `step_grab`, `HandsIO.grab` | owner |
| The grab is the four fingers' mean curl through the pinches' `Gate` (closes past 0.65, opens under 0.45, 0.05 s debounce). Its two lanes go after the dance lanes, its gates after the pinches. | `GRAB_CLOSE`, `GRAB_OPEN`, `Layout.gates` | rows 131, 132 |
| The dance sources and the grab have no settings of their own, send nothing to the DAW, and are not offered by a hand Learn: pick them on ROUTING. The HANDS page shows them in a column beside the axes. | `hands/panel.py` `_dance`, `_grab` | rows 129, 130 |
| The hands package is liftable: `core.py`, `signal.py` and `tape.py` import nothing from the host; `device.py` and `panel.py` are the only files that know it. | `tests/test_hands_boundary.py` | owner |
| Pinch switches are a Schmitt trigger plus a debounce. | `hands/core.py` `Gate` | owner |
| Hand settings live in three places, each where it changes: rig settings in the hands device's entry (`[[devices]] kind = "hands"`, or the old `[hands]` table), the room (ranges, box and, since plan 26, the calibration into the shape's world, `units`) in `hands.json`, and the feel (including `hands.learn_depth`) in the hands params. | `hands/core.py` | owner |
| **The Leap is calibrated into the shape's world** (plan 26, decision 4): `hands.json` is `hyperspace.hands/3` with `"units": {"mm", "origin", "tilt"}`, "from the box" by default — the padded box fitted into a 16:9 picture of the eye, tilted 32°; an older file is kept as `hands.json.bak-v2` before the first rewrite. | `hands.core.Units`, `ghost.calibration`, `CAL_ASPECT` | owner (the calibration in `hands.json`); row 187 (its form and fit) |
| **The interaction box** bounds the palm in the Leap's mm. It is one box for both hands, with x symmetric. The calibration sweep sets it (2nd–98th percentile + `BOX_MARGIN`) and "reset ranges" opens it. No widget edits it. Its edge is a Schmitt edge (`BOX_EDGE`). | `load_box`, `inside`, `HandsIO._sweep_box` | row 50 |
| **A hand outside the box is absent everywhere**: NaN axes, presence off, pinches dropped and its ghost faded. Only the HANDS page shows it, drawn hollow. | `HandsIO.poll`, `ghost.box_of` | row 51 |
| Home on the keyboard is `key:HOME` only (fn ← on a laptop). | `routing.LOOP_KEY_ROWS` | row 38 |

## Tempo and LFOs

| Decision | Where | Who |
|---|---|---|
| **One free-running clock, tapped into time.** No DJ Link, no MIDI clock and no drift correction: re-tap. 4/4 is assumed. A synced LFO reads `clock.beat · ratio`. | `tempo.py` | owner |
| BPM is the mean of the burst's last 8 taps. A gap over 2 s starts a new burst. | `tempo.TAPS`, `tempo.GAP` | owner |
| **A tap never moves the downbeat.** Only the global trigger (⇧B, METRONOME) places it, and it restarts every synced LFO at phase 0. | `Clock.tap`, `Clock.trigger` | owner |
| A trigger or reset that fires after this frame's LFO step is held and applied at the start of the next step; since plan 28 a reset that lands before its LFO's node in the pass takes effect that frame. | `LFOs.pending`, `LFO.at` | owner; row 238 |
| **The LFOs step inside the modulation pass**, each at its own node after its knobs land, every LFO a node whether or not a cable touches it (plan 28). | `Router.use_lfos`, `LFOs.step_one` | owner (plan 28 decision 7); row 238 |
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
| **Per shape, a 3D surface either gets real 4D extent or stays 3D with its W planes masked**, never all down one path; no shape is removed for reading badly. | `geometry.SHAPES` | owner |
| The Heart is masked. The Star, Torus, Trefoil knot and Starfruit are lifted, and every lifted shape's alias reads "4D lift · …". | `geometry.SHAPES` | row 89 |
| `Shape.w` is one of four words — `native`, `flat`, `lift`, `mask` — not a 3D/4D flag (a cell count of 0 marks a surface, not a 3D shape). A masked shape's W planes are folded where it is drawn — XW onto XZ, YW onto YZ, ZW onto XY — never in the integrator or a param. | `geometry.Shape.w`, `W_KINDS`, `view_angles`, `W_REMAP`, `Renderer.draw_scene` | row 90 |
| A masked shape's depth cue (line fade, width, draw order) reads its depth toward the 3D camera (z after the camera's yaw and pitch), as a 4D shape's reads w. | `Renderer.draw_scene`, `geometry.view_depth` | row 91 |
| **Every lifted or masked shape keeps `VOLUME_FLOOR` (0.15) through a full turn of each W plane**, from rest and from a generic pose, and turns at most 0.15 of its face area edge-on. The floor is half the 4D shapes' worst (the cubic pyramid, 0.30). | `geometry.VOLUME_FLOOR`, `tests/test_shapes4d.py` | row 92 |
| A lift is a function of the builder's own parameters, with no linear part of x, y or z, odd under each single-axis mirror, z-dependent on an extruded outline, and agreeing wherever the surface welds. A shape's digest hashes floats rounded to 1e-9. | `geometry.param_surface`, `spherical_surface`, `ring_prism`, `tube` | row 93 |
| The Möbius strip is lifted, and 0.55 wide (was 0.45). | `geometry._build_mobius` | row 94 |
| The Rose is lifted, and 0.16 deep (was 0.12). | `geometry._build_rose` | row 95 |
| **The Klein bottle is shape 26**: the classic bottle immersion, lifted by w = sin 2u + ½·sin v·cos 2u so it never crosses itself, `Shape.w` "lift", 37 × 16 samples, centred. | `geometry._build_klein`, `_klein_xyz` | row 96 |
| A face of more than four corners that is not planar (a lifted cap) is framed by its least-squares plane; every planar face keeps its basis. | `geometry._face_xy` | row 97 |

## Render and outputs

| Decision | Where | Who |
|---|---|---|
| **The frame is a render graph** (plan 26): nodes of a curated set of built-in kinds — **Geometry** (draw calls in the shared camera, no framebuffer of its own: the shape, the hands, a point cloud), **Scene** (any number of geometries into one colour + depth target), **Layer** (one geometry into its own target), **Composite** (over, add or depth-aware) — plus the effect nodes, the history and the outputs; evaluated once a frame in dependency order, settled when the graph is built. | `graph.py`, `Renderer._draw_frame` | owner (decisions 2, 7) |
| **Shaders are nodes** (plan 30): every effect file is an image node — bitmap in, bitmap out, several instances — placeable on any image edge of the render graph. No single point in the graph holds "the shaders". | `graph.Effect`, `graph.EffectAt` | owner (plan 30 decision 1) |
| **The Effect node and the pipeline end** (plan 30 D0): one `Effect` node per effect instance (`fx.<name>.*` its params, `FxChain.run_one` its pass); each pipeline's chain is a run of them in the stack's order, every instance on or off, an off one read through (no pass, no texture), so a toggle rebuilds nothing; the run ends in `Fx`, which keeps the end's jobs (straight into its one output or once into a frame texture, the stand-down, the error path) and keeps its name and its `fx` lines. The pool is the chain's half-float textures, two plus one per held picture. The History and Output wrappers: the history as `history` (echoes and dream over its input) and `capture` (the ring, once a frame, after every pipeline); the Output node is `_compose`. Made images (scene, layers) are pulled by their consumers; painted images (history, composite, an effect) draw into the consumer's framebuffer, so nothing is quantised between them. The cover mask is a layer node. | `graph.Effect`, `Fx`, `History`, `Capture`, `Output`, `Cover`, `Node`, `fx.FxChain.pool` | owner (plan 30 decision 1: the node); rows 177–179, 181, 214–217 |
| **Placement** (plan 30 D1): a preset's `graph` section may put an effect `after` a node (every consumer of its picture reads the effect) or `into` one (its `image` input alone) — `scene`, `hands`, `hands.<n>`, `history`, `output.<n>`, an effect instance. A placed effect is not in the chain's run. A placement this build cannot honour (both keys, an unknown name, a loop) is a note and that effect's default placement; one on a node the built graph lacks this frame is dormant, said in words on the OUTPUT page. On a layer it keeps the ground see-through and the guide unfolded; a presenter gets the folded picture. | `graph.EffectAt`, `read_graph`, `default_graph`, `placement_words` | owner (plan 30 decision 1: any image edge); rows 219–225 |
| **The `VALUE` port type** is declared beside `IMAGE`, `MASK` and `GEOMETRY` for the palette's two auxiliary ports — a value out for the lights (plan 29) and an image-in `sample` port — designed and **not built**: no node publishes or reads one. | `graph.VALUE`, `patch.RENDER_VALUE` | owner (plan 30 decision 3); row 231 (its shape) |
| **Today's three pipelines are the default graph**, built from each output's switches (and the renderer's `Wiring`, the listed clouds, the effect stack's list and the placements), reused until one changes; evaluating them in dependency order changed no pixel. | `graph.default_graph`, `Renderer._graph_for` | owner (decision 7); row 180 (the key) |
| **Step 0 came first**: golden frames of every factory preset in every output state (596 today with the fixtures', compared to the byte on "Apple M3 Max"), GPU time per node on the SYSTEM page, and the naming rule. | `tools/golden_frames.py`, `tests/test_golden_frames.py`, `render.PassTimer` | owner (decision 8); rows 170–175 (the rig, the timer) |
| **The default graph is pixel-identical through plan 30**: every golden recorded before it matched unchanged after the effect nodes and placement; SYSTEM gained a line per effect that ran, and the end's own `fx` line reads 0.00. | `tests/test_golden_frames.py`, `Graph.timed_in` | owner (plan 30 decision 5); rows 214, 218 |
| **The naming rule**: the first instance of a node keeps today's ids (`fx.acid.mix`, `ghost.alpha`); only an extra instance carries its number right after the prefix (`fx.acid.2.mix`, `ghost.2.alpha`, its layer `hands.2`); the group never changes, so nothing migrates. No effect file or `@param` key may be digits alone. | `params.instance_id`, `instance_of`, `fx.FxState.set_instances`, `ghost.prefix` | owner (the rule); rows 169, 198 (the marker's form, its use) |
| **The render stack reads params and never writes one**; no render node or graph method is named `apply`, `modulate`, `snapshot` or `set_value`; `graph.py` imports no `params`, `routing`, `library`, `preset`, `undo`, `control` or `devices`. | `tests/test_render.py::test_the_render_stack_imports_no_registry`, `tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write` | owner (decision 16, in the launch prompts of plans 26 and 28–30) |
| **The shape's transform** (decision 4): `rot.*` is its local 4D tumble; `camera.yaw` / `camera.pitch` its world pose (ids unchanged); `camera.zoom` / `camera.pan` its world scale and position. The whole-frame 2D zoom is gone until an image node brings it back. The CPU takes the shape to 3D (`geometry.world_points`); the vertex shaders take it to the clip through one shared 4×4. `project()` stays the parity oracle. | `geometry.model_matrix`, `world_points`, `render.py` | owner |
| **A fixed camera, the eye** (`eye.fov`, `eye.distance`), framed on the Leap box, is session (no preset moves it). Its defaults are the old 3D divide: every vertex within 1.1e-4 px of `project_h` in float32 (the bar is 0.5 px). | `geometry.eye_matrix`, `EYE_FOV`, `EYE_DISTANCE` | owner (the eye); row 182 (ids, defaults) |
| `camera.pan` is in world units (±12 shape radii); a file without `"units": {"camera.pan": "world"}` stored px and is converted through the 1080p screen (324 px a unit) at load, presets and camera modules alike; every save writes the marker. Copies are in the world (`render.CELL`). | `params.pan_world`, `PAN_RANGE`, `geometry.PAN_REF_PX` | rows 183, 184 |
| **Lines and points have a real depth**: quads expanded in the vertex shader from 3D ends, their width following depth and brightness. The see-through shape stays painter-sorted and is never depth-tested against itself; its visible surface (alpha over 0.25) is written to depth after its colour. A point's quad is a whole number of pixels; a stroke end behind the eye is slid in front of it. | `render.LINE_VS`, `POINT_VS`, `DEPTH_ALPHA`, `Renderer._depth_pass` | owner (decision 5); rows 185, 186, 188 |
| **Strokes in world space or screen space** (`view.screen_strokes`, part of the look): edge width and dot radius either scale with `camera.zoom` — the pre-plan-26 feel — or keep their pixel weight whatever the zoom. Off (world space) by default. | `view.screen_strokes`, `Renderer.draw_scene` | owner (2026-10-14: the toggle); rows 189, 190 (the default, the form) |
| **The hands in the scene or as a layer, or both at once** (decision 3): in the scene, solid geometry is drawn first, then the sorted see-through shape; as a layer, its own colour and depth target composited over, added or depth-aware. The same hands can be in the scene on the projector and a clean layer on the glass. | `graph.Hands`, `Scene`, `HandsLayer`, `Composite`, `graph.Wiring` | owner |
| Hands inside the scene are solid (`ghost.alpha` sets only their layer; 0 still removes them). A depth-aware layer hides a texel where the scene's visible surface is nearer by more than 0.05 shape radii. | `Ghost.draw_solid`, `render.LAYER_DEPTH_BIAS` | rows 191, 192 |
| The OUTPUT switches set the default graph's wiring; `Wiring` (hands in the layer or the scene, how the layer is laid on, what the history holds) is renderer-wide, its default today's frame, set only by a preset's graph. | `graph.default_graph`, `Wiring`, `Renderer.wiring` | rows 193, 194 |
| **A preset may say its graph in data**: a `graph` section listing the nodes that differ from the default (`hands`, `effect`, `history`), never anything that is a param. No section is the default graph; a section this build cannot read is a note and the default graph, kept as written — except a placement it cannot honour, which costs only that effect its place (plan 30). A `cloud` kind is unknown in this run (clouds follow the device list). | `graph.read_graph`, `preset.GraphSection` | rows 196, 197, 221 |
| A second hands node is its own `Ghost` with its own `ghost.2.*` (session) settings; the in-scene nodes go in the scene, the layer node on the outputs without the hands in their scene; a hands node is timed by the scene that draws it; a hands node may be drawn as lines; the pages say the wiring in words; undo puts the graph back. | `Renderer.ghost_of`, `graph.default_graph`, `Graph.timed`, `ui.output_shows` | rows 195, 199–203 |
| **A point cloud is a geometry**: a listed `cloud` device adds a solid point-cloud node to the default scene, drawn in the shared camera at its own scale (`cloud.*`, session). | `graph.PointCloud`, `Renderer.cloud_source` | owner (decision 2: the point cloud among the geometries); rows 204–209 |
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
| **The hands show on the main projection by default**: each output's `hands` switch defaults on, and the rig's projector entry says `hands = true`. Nothing in a preset. | `config.SCREEN`, `docs/SETUP.md` | owner; row 133 (the line is in SETUP.md, not the home) |
| **Lines and points have an opacity each** (`view.lines_alpha`, `view.points_alpha`), 1 by default, so the picture is as it was until one is moved. | `params.py`, `Renderer.draw_scene` | owner (a mix wherever a layer lacks one); row 117 (the ids) |
| **The ghost hands** are a geometry in the shape's camera (plan 26), settled once a frame; by default drawn into their own layer and laid on per output after the effects and before the dim, and not in the look-back history (a preset's graph may put them in the scene or the history). `ghost.*` are session params, off by default. A raising hands pass is caught. | `ghost.py`, `graph.Hands`, `graph.HandsLayer` | owner |
| `ghost.on` says whether the hands are drawn at all, and each output's hands tick says where they show. | `outputs.route` | row 84 |
| **`ghost.style`** picks one of five drawn objects from the same tracking data: HANDS (the default), JOINTS, PALMS, CAGE and MARIONETTE. | `ghost.PARTS` | owner |
| `ghost.style` is a session enum, saved with the show and learnable onto a desk control. | `ghost.register` | row 87 |
| **Hands through effects** (`output.N.through`, off by default). When on, that output's hands' layer is composited after the look-back composite and before the first effect. With the scene off and through on, the output shows the hands alone through the effects. | `graph.default_graph` (`composite(scene+hands)`, `fx(scene+hands)`) | owner (switch); rows 79, 193 (where they go in) |
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
| **The palette is the first shader node moved** (plan 30): placed by a preset's graph it folds the hands' layer only, one output only, or the scene before the history and the dream; unplaced it is the chain's last pass as below. Its fold and gradient map were unchanged by the move; each placement is proven by a fixture with its golden. (The fold was reparametrised as a slice on 2026-10-20 — plan 30 N8, the next rows — with the fixtures' frames unmoved.) | `tests/fixtures/presets/palette-hands.json`, `palette-glass.json`, `acid-scene.json` | owner (plan 30 decision 2); row 225 (the fixtures' values) |
| **The faces target stays an inner chain**: an effect aimed at the faces runs inside the shape's face drawing, not on a graph edge — the one shader run the graph does not show; a placement does not move it. | `render.face_fx`, `fx.<name>.target`'s tip | row 232 |
| **The FX page edits the default chain**; a placed effect's chip sits in a second grid under it, `Palette · after hands`, not draggable, its LED and strip as any effect's, the dormant reason on hover; the status line adds "· N placed" for the placed effects that run, and one aimed at the faces says "on the faces" and is not counted. The chip's words are the edit view (`after hands`); OUTPUT's are the show view (`palette on the hands`). | `ui_fx.page`, `ui_fx._status`, `graph.placed_chips` | rows 226–230 |
| **The palette is a colour compression transform** (the owner, 2026-10-20): its first mode maps the whole HSV cylinder onto a closed, extruded slice of it — a start and a stop hue, a start and a stop saturation, a start and a stop value — and every pixel is compressed into that slice (the whole picture as shades of one red; a yellow slice and its derivations). A map, never a clamp: nothing is cut off. Its second mode is the gradient map, brightness through two to four anchor colours. It is, unplaced, one final colour pass after the other effects and the dream, before the outputs. A saved palette is a named `fx` module preset. Off and at mix 0 by default, and its slice defaults to the whole cylinder, so on at mix 1 the picture is as it was on an opaque ground (on a see-through one the premultiplied colour is scaled by alpha once more). Lights following it is plan 29. This replaced the fold onto `centre` ± `width`/2 (plan 24 C6). | `shaders/fx/palette.glsl` | owner (2026-10-20) |
| The palette is an effect file, so its ids are `fx.palette.*`; it is `@order 95`; `mode` is a choice (compress / gradient) drawn as a picker; the slice is `hue_from`/`hue_to` (degrees, up the wheel, through 360 when to < from) turned by `hue_turn` (wraps, as the old centre did), `sat_from`/`sat_to`, `val_from`/`val_to`; the anchors are `anchors` plus `a1`–`a4` hue, sat and val; the hue map is the old triangle fold up to 180° and slides to the identity at 360°. A preset with the old `centre`/`width`, `sat_lo`/`_hi`, `val_lo`/`_hi` is read as the slice. | `palette.glsl`, `palettecompat.palette_slice` | rows 134, 136–138, 291–297 |
| An effect file may set its default wet/dry with `// @mix` (1 when absent). | `fx.EffectSpec.mix` | row 135 |
| The FX page packs a strip's `_lo`/`_hi`, `_from`/`_to` (drawn `from → to`) and `_hue`/`_sat`/`_val` params onto one row, draws an effect's `@param choice` as a picker, and the palette shows only its open mode's rows. | `ui_fx.strip_rows`, `HIDDEN_BY_MODE` | rows 139, 296, 297 |
| **The dream is temporal**: one running buffer blended with each frame, a few gradient steps per frame. | `dream.py` | owner |
| The compositor re-colours the dream buffer (`dream.hue / sat / tint`). Echoes pass untouched. | `lookback.py` | owner |
| **The history is wiring** (decision 6): the capture takes a chosen image — the scene (the default, as before) or the scene with the hands. It never holds the frame's effects or the dim. | `graph.Capture`, `Wiring.history` | owner |
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
| A module preset is one group's values (`hyperspace.preset/1`), a preset is `hyperspace.preset/2` and a show is `*.hyp.json` (`hyperspace.project/2`). Unknown ids are reported, not fatal. A preset may carry a `graph` section (plan 26) and a `units` marker for `camera.pan`; neither bumps the schema. | `library.py`, `preset.py` | owner; rows 183, 196 |
| The library is watched like source: editing a file shows in the running app. The library's own renames and trash moves are never re-applied. | `hotreload.py`, `Library._sync` | owner |
| `<home>/bindings.json` holds only the session's controls, the sink rows among them (sinks are rig). A show carries no routing of its own. | `routing.FILE` | owner |
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
| **D5** The global layer is defined in the session's files. Its track knobs K1–K5 are the hand feel (smoothing, response, catch, the selected axis's return) and `tempo.bpm`. K6–K8 are free. Its track faders S1–S6 are the bands' post-drive, S7 the master dynamics and S8 the master trim: the audio one latch away (plan 24, amending D6). | `apc40.DEFAULT_MAP`, `apc40.SHIFT_FADERS` | owner; row 115 (faders, not knobs) |
| **D6 Invariant controls** have one meaning on both layers, and no preset maps them: the MASTER fader (audio drive), the crossfader (master dim), clip rows 1, 4 and 5 (the bank: a tap loads, a hold on an empty slot saves), SAVE (track 8's clip stop), scene launch 1–4 (points, lines, faces, rotate: their LEDs always show the live state), SHIFT, TAP TEMPO, METRONOME, NUDGE ±, QUANT, OVERDUB (home) and the transport. A preset's row on one of them is dropped at load with a note. (Until plan 24 the track faders were on this list and the four toggles were the preset's.) | `apc40.DEFAULT_MAP`, `apc40.BANK_PADS`, `apc40.TOGGLES`, `apc40.SAVE` | owner |
| **The track faders S1–S8 are the preset's**, bound by its desk like the knobs. No global defaults are inherited and nothing fills them: a preset with no fader rows leaves them dark, and today every factory preset does, until the owner authors fader sets. | `apc40.TRACK_FADERS`, `preset.track_fader`, `knob_desk(faders=)` | owner; row 118 (the helpers) |
| **D7** On a layer switch the knobs **jump** to the layer's values (the ring re-bases the encoder) and the faders **soft-pick-up**: each layered fader starts from where it physically is and catches its own param, so a fader moved on one layer never jumps the other's. | `apc40.RING_REBASES_KNOB`, `MidiIO.redraw` | owner; row 116 (from where it is) |
| **D8** A control the preset does not map **does nothing** and shows dark. It never falls through to the other layer. | `routing.py` | owner |
| **D9 The analyzer is session**: bands, dynamics, scenes and the drive fader are never in a preset. | `params.SESSION_GROUPS` | owner |
| **D11** A show names its **startup preset**, which loads at launch. | `Project.startup`, `load_startup` | owner |
| **D12** A modifier is read **at the press**. SHIFT's release never re-evaluates a button already down. | `midi.py` | owner |
| **The bank is twenty-four slots.** F1–F8, ⇧F1–F8 and clip row 1 are slots 1–8, and clip rows 4–5 are slots 9–24. A slot names a preset file. | `library.SLOTS`, `params.F_KEYS` | owner |
| Slots 9–24 have no triggers of their own (they use `preset.select`). The show file stays `hyperspace.project/2` and holds the bank only up to its last filled slot. The factory party show has TRACER on slot 9. | `library.bank_doc` | row 72 |
| A bank pad is green when its preset is loaded, amber when its slot is filled and dark when empty. The old factory shape rows on those pads drop quietly at load. | `routing.led_level`, `routing.RETIRED_DESK_ROWS` | row 73 |
| **Home is the show's "starts on" preset**, on OVERDUB and the Home key. It is one undo step. | `Project.home`, `preset.home` | owner |
| **The desk never overwrites a preset, and never trashes one.** The **two-handed save**: hold SAVE (track 8's clip stop) and tap any bank pad, on either layer. An empty slot gets the live state as a new preset ("TRIP 2"); a filled slot gets a new preset too, the slot points at it, and the old preset keeps its file and stays in the list, unpadded. The pad blinks. Holding an **empty** bank pad about 0.6 s still saves into it; holding a filled pad just loads it. (Until 2026-10-09 a hold on the clip-stop row saved into the next empty slot.) Panel Save and ⇧F1–F8 still overwrite. A pad is freed, the preset kept, with the slot's right-click → *free this pad (keeps the preset)*. | `Project.save_into`, `Project.save_empty`, `MidiIO._save_tap`, `midi.HOLD_S` | owner (2026-10-09, two-handed save 2026-10-14) |
| SAVE is a held `momentary` row on the session param `desk.save`: never latched, never learned, released on a reconnect; where the owner's own row holds clip stop 8, SAVE is not added and every launch says so. | `apc40.SAVE`, `routing.save_refusal`, `save_missing` | row 110 |
| The two-handed save names the new preset from the loaded one (`next_name`), says which preset is still in the list, and blinks the pad only when the slot took it. | `library.Project._save_new` | row 111 |
| The save-as details: a `hold` op fires once while held; the buttons of a learned bar light together; the new pad blinks; names are counted against files, names and bank; and the new preset becomes the loaded one. | `routing.OPS`, `library.next_name` | row 42 |
| **Every load relights the whole desk** from the new preset: every control no row draws goes dark, and every fader the new preset binds lets go and picks up from it. The session's faders (crossfader, MASTER, the band strip under SHIFT) keep their catch through a load when the load did not move their param. | `MidiIO.redraw`, `MidiIO._dark_desk` | owner (relight); row 112 (the faders; row 44 for the session's) |
| The factory files still carry the four toggle rows (no library file changes in plan 24); a load drops those exact rows without a note. | `routing.TOGGLE_DESK_ROWS`, `preset.file_desk` | row 113 |
| **A desk event log**: the last twenty presses, what each did and the layer it was read on, on the SYSTEM page. | `midi.DeskLog`, `Panel._desk_log` | owner; row 114 (its shape) |
| An older `bindings.json` moves its eight invariant fader rows to the SHIFT layer once, with a backup. | `routing.FADER_SHIFT_ROWS` | row 119 |
| **A coverage report** says, for every factory preset, which of its preset-layer controls are mapped, dark or dead; it is committed and a test keeps it fresh. The owner's bar — at most four dark or dead per preset layer — is for the authoring pass; no preset was remapped to meet it. | `tools/desk_coverage.py`, `docs/plans/assets/24-party-fixes/desk-coverage.md` | owner |
| A control is dead when the preset's bases cannot show its param (`cannot_show`); the preset layer counted is 38 controls. | `learn.cannot_show`, `layer_controls` | rows 120, 121 |
| **Desk templates** are named binding sets in their own JSON: a preset may name one and keep only its overrides, so one fix reaches every preset that uses it. The factory has no templates (its `desk/` folder need not exist). | `Library.desk_template`, `preset.expand_desk`, `compact_desk` | owner; row 122 (the format) |
| **Modifiers live in the preset** (plan 28), beside `routes`, never in `bindings.json`; a desk template may carry them, a preset overriding by id. | `preset.MODIFIERS_KEY`, `merge_modifiers` | owner (plan 28 decision 8) |
| A modifier's params are in its entry only, at their bases; a save writes only the entries that differ from the template's; undo watches the modifiers as one table part. | `Presets._values`, `Presets._modifiers_part`, `undo.TABLE_GROUPS` | rows 243–245 |
| **Both graphs live in the preset as plain JSON** (plan 28): the routes and modifiers, and the `graph` section's nodes and a `wires` list (`{"from": "<node>", "to": "<node>.<port>"}`) in which the outputs are nodes; an output no wire names keeps the session's switches. The GRAPH page's positions are the preset's `layout` for the look's nodes and the show's for the rig's. None bumps the schema. | `graph.Wire`, `GraphSpec.wires`, `preset.LAYOUT_KEY`, `library.Project.layout` | owner (plan 28 decision 13); rows 251, 263–269 |
| A build from before plans 28 and 30 opens a preset with placements or wires as the default graph with a note, ignores `modifiers` and `layout` and drops them on its save: both Macs sharing a library run the same build. | (the base build's reader) | row 277 |
| **Click-to-map offers the preset's own params first**, ranked (routed, moved, switched on, already on the desk), then the rest by group. | `learn.ranked`, `ui_desk._offer` | owner; row 123 (the tiers and where the list sits) |
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
| The ROUTING page is one page over the loaded preset: its desk rows and macros, and the session's rows read-only below (its routes and modifiers are the GRAPH page's since plan 28 N7; a pointer line says so). | `ui_routing.page` | owner |
| **The cheat sheet is off at every launch.** `/` and the APC40's DETAIL toggle it (the pad's MENU did until 2026-10-14; START and BACK are now unbound). The desk diagram stays on. | `ui.cheatsheet` | owner |
| The desk's glyphs (K1–K8, D1–D8, S1–S8, SM, X, C, G, B1–B22, ⇧) appear on every ROUTING row and Learn message, with an APC40 diagram of the layer that is up. | `apc40.LAYOUT`, `ui_desk.py` | owner |
| The on-screen desk takes the room it has, and there is no DESK page. Once a unit is 44 × 32 px, every lit control carries its label. | `ui_desk.room`, `ui_desk.LABEL_UNIT` | row 57 |
| The ROUTING page has one filter field. Only the user clears it, or a click on a desk control. | `ui_routing.matches` | row 63 |
| The param's menu also opens from a row's label and from every analyzer meter. | `Panel._ctx_label` | owner |
| The VIEW page's field is one row, and the six plane rates are three rows of two. | `Panel._page_view` | owner |
| The dirty dot is a 12 px red disc and the save chip is solid red while there is something to save. On a factory preset, save reads "save copy". Saving never prompts. | `ui.dirty_dot`, `ui_presets.save_label` | row 77 |
| The OUTPUT page says in words what each output shows, and there is no picture of the render. The footer names a black output. | `ui.output_shows`, `Panel._output_blocks` | row 85 |
| **One editor for both graphs** (plan 28): the GRAPH page draws the controllers, the analyzer, the LFOs, the modifiers, the macros, the params under their render nodes, the render graph and the outputs on one canvas, and edits both; the modulation stages N1–N4 and controllers as nodes were one plan. **The editor is `imgui_node_editor` from imgui-bundle**: no new dependency. | `ui_graph.py`, `graphview.py` | owner (plan 28 decisions 6, 15) |
| The GRAPH page edits only through the table's own calls (a cable into `mod` is the row a Learn would make; into `base` a desk or pad setter; a macro onto `mod` refused) or a `graph` section read back before it lands; Learn starts from a `mod` port with the param menu's own items. ROUTING and GRAPH are two views of one table: **GRAPH edits the routes and modifiers; ROUTING keeps the desk, macros, session and sinks until it is retired.** | `graphview.Edit`, `learn.row_for`, `Panel._ctx_learn_block` | rows 255–262, 268; owner (2026-10-20) |
| The GRAPH page's ids, its params-to-render-node table, what it draws (no sinks), its tidy columns, its editor context on the panel, its selection pane under the canvas. | `graphview.OWNERS`, `graphview.auto_layout`, `ui_graph.page` | rows 248–254 |
| **Every node on the GRAPH page is collapsed by default**: its title and at most five short lines, nothing per port until it is expanded. | `graphview.summary`, `ui_graph.collapsed` | owner (2026-10-20) |
| **One wire between two nodes while either end is collapsed**, however many parameters are mapped between them; the real cables appear when both ends are expanded. | `graphview.wiring`, `graphview.VBundle` | owner (2026-10-20) |
| **GRAPH replaces ROUTING**, in steps: the routes and the modifiers are edited on GRAPH now; ROUTING keeps its desk, macros, session and sinks (the desk is Dylan's work in flight) until a later pass retires it. | `ui_routing.page`, `ui_graph._side` | owner (2026-10-20) |
| A collapsed node's lines, its stubs, a bundle's thickness and hover, its rows in the side pane and its refused Delete, the collapse state as UI state only, the picker on a collapsed node's stub, Learn from a node's menu, tidy's collapse and words, the details chip, expand all, ROUTING's pointer, a modifier's editor on GRAPH. | `ui_graph.py`, `graphview.py`, `ui_routing.page` | rows 278–290 |
| **The GRAPH canvas is organised by concern**: all things audio live in one area, all things geometry in another, all things shader in another, the controllers and the modulation feeding them from the left; **a macro that connects to nothing is not drawn by default**. | `graphview.AREA`, `graphview.layout`, `ui_graph.drawn_node` | owner (2026-10-20) |
| The areas' order and titles, where the LFOs, modifiers and macros sit, the small "other" area, the idle rule for each kind of node (an effect switched off with no cable among them) and the idle line that shows them, the through wire over hidden effects, the shaders' rows of four, the area chips, each area's own depth, the titles' floor. | `graphview.py`, `ui_graph.py` | rows 299–309 |
| A preset's desk template is one collapsible node on the GRAPH page; an edit inside is an override; the hands node folds as axes, pinches, grab, presence, dance. | `graphview.template_rows`, `graphview.hand_group` | rows 274, 276 |
| The MODIFIERS strip's block is a modifier's editor; since plan 28 N7 it is drawn on GRAPH's side pane for a selected modifier node, not on ROUTING. | `ui_routing.modifier_block` | rows 247, 289 |

## Process

| Decision | Who |
|---|---|
| Each code PR gets a `/code-review` before merge. Agents work on their own branches, and the owner merges. | owner |
| Agent work lands on an integration branch, never on `main` (`finish-line` through plan 21, `plan-22-integration` for plan 22, `plan-24-26-27-integration` for plans 24, 26 and 27, `plan-28-30-integration` for plans 28 and 30); the owner merges it into `main`. | owner |
| Agents in a run work on Opus or Sonnet, never Fable (plans 28 and 30, 2026-10-16). | owner |
| **A run that builds mechanisms edits and adds no preset** (plans 24, 26 and 27, 2026-10-14; plans 28 and 30, 2026-10-16): every file under `hyperspace/library/` stays byte-identical, and every proof is a fixture under `tests/fixtures/` (force-added: the folder is gitignored) loaded through a scratch library. Fader sets, hand mappings, dance presets, palettes, templates and the factory presets' graph wiring are the owners' creative pass. | owner |
| **Every new param defaults to today's picture**: a new mix or opacity at what the frame does now, a new switch off, a new source at its rest. | owner |
| **Plans 24, 26 and 27 ran in parallel** (2026-10-12): the render graph is the top priority, the device registry the highest-leverage piece. | owner |

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
| GLSL written inside the render graph, or a general TouchDesigner: nodes are a curated set of built-ins; shaders stay files with hot reload (plans 28 and 30, decision 14). | owner |
| Order-independent transparency (deferred): hands inside the scene are solid, drawn before the sorted see-through shape. | owner |
| Touch shows (fingertips lighting the shape where they meet it) and hand–shape contact: looks for the creative pass, after plan 26 put the hands and the shape in one space. | owner |
| New 4-polytope families in plan 22: ranked in [`plans/22-polytope-shortlist.md`](plans/22-polytope-shortlist.md); none is built until the owner picks. | owner |
