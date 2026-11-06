# Hyperspace — architecture

The map of the system: what the parts are, the order a frame runs in,
who may write a parameter, and which test holds each boundary.
How to run, tune and change things is in [`ENGINEERING.md`](ENGINEERING.md);
the reasons behind the calls are in [`DECISIONS.md`](DECISIONS.md) and
[`DECISION-REGISTER.md`](DECISION-REGISTER.md); what is known to be wrong
is in [`AUDIT-2026-09.md`](AUDIT-2026-09.md).

Two questions this file answers on its own:

1. **Where does a controller's value go each frame?** — §2 and §3.7.
2. **Who may write a parameter?** — §3.2.

[`ARCHITECTURE.html`](ARCHITECTURE.html) is this file's visual companion —
the same component map, frame order and writer classes as a diagrammed page,
plus the band-to-plane map. Open it in a browser.

When a boundary, the frame order or the control model changes, change
this file **and `ARCHITECTURE.html`** in the same PR. Paths are relative to
`hyperspace-python/hyperspace/` unless they start with `tests/` or `docs/`.
A reference is a symbol or a test name, never a line number.

---

## 1. Component map

Hyperspace is one Python process: a parameter **registry** in the middle,
**sources** that feed a **routing table**, a **render stack** that reads
the registry's live objects, a **panel** that edits the registry, and a
**library** that saves and loads it. `app.py` builds everything once and
runs the one frame loop.

```text
 keys · mouse · devices' rows (pad, MIDI desks, OSC hits) ──▶ Param.set* ──▶ BASE ─┐
 panel widgets · loadable patches · undo ─────────────────────────────▶ Param.set* ──▶ BASE ─┤
                                                                                    ├─▶ Registry.apply() ─▶ live objects ─▶ render stack
 audio lanes · LFOs · envelopes · the sequencer's lanes · devices' feeds ──▶ Router.modulate ─┤  (once a frame)  (ViewState,    (reads only)
                                              (one performer row per param) ▶ OFFSET     │                  FxState, …)
                                                                                         └─▶ sinks (bridge out, hands-daw): effective values out
```

| Component | Modules | Owns | Writes | Boundary (held by) |
|---|---|---|---|---|
| **Registry** | `params.py`, `tapers.py` | every `Param`: id, kind, taper, flags, base, this frame's offsets; the base chase held (`Registry.base_chase`, plan 52); each deck's dial readings (`declare_dial`, `dial_id`, `Registry.dial_modes`, and `MetaRegistry.dial_launch`, row 729) | the live objects, once a frame, in `Registry.apply()` | never imports `midi`, `bridge` or `dream` (`tests/test_params.py::test_core_does_not_import_the_midi_adapter`, `tests/test_bridge.py::test_core_does_not_import_the_bridge`, `tests/test_dream.py::test_core_does_not_import_the_worker`). It does import `fx`, `ghost`, `lookback`, `geometry`, `analyzer` and `bands` for their state classes and constants |
| **Routing table** | `routing.py`, `routing_sources.py`, `modgraph.py`, `modifiers.py` | `Binding` rows, `<home>/bindings.json` (the meta controller's controls), the referee, the desk's layers, the macros, the loadable patch's modifiers (`Bindings.modifiers`), the per-frame modulation pass — the table as a graph in dependency order (`Router.modgraph`; `modgraph.py` the leaf that sorts it, `modifiers.py` the leaf that steps a modifier); what the sources said this frame — feeds, labels, rests, gates, names, the device registry, the source feel, the clock — in `routing_sources.Sources` (plan 44 D2: shared, fed by the devices and the analyzer), each deck's `Router(reg, table, sources)` the evaluator over it | offsets, through `Router.modulate` → `Param.modulate` (the only call site in the package); bases for key / pad rows (`routing.act`) and macro base subscribers | imports nothing above it — no `ui`, `app`, `hands`, `midi`, `bridge`, `learn`, `dream`, `hotreload`, `library`; `routing_sources.py` below `routing` (no `routing`, `params`, `devices`; it writes no param), and it alone imports `glfw` and `gamepad`, lazily, to resolve key and pad names (`tests/test_routing_boundary.py::test_routing_imports_nothing_above_it`, `::test_the_shared_sources_write_no_param`, `::test_importing_routing_pulls_in_no_adapter_or_panel`, `::test_only_router_modulate_calls_param_modulate`) |
| **Learn** | `learn.py` (with `row_for`, what a wire lands; `clutch_of`, a `turn` row's default gate; `land_moved` / `move_route`, a re-pointed room or turn row landing as `row_for` would) | the armed param and what it waits for, the held Replace / Keep question, the picked desk control, Unbind | table rows, through the table's edit doors | imports only `undo`, `params`, `routing`; the device profile and the device registry (what can be armed, the sink ports) arrive as arguments (`tests/test_learn.py::test_learn_control_needs_no_adapter`) |
| **Devices** | `devices.py` (the `Device` protocol, `Port`, `DeviceRegistry`, the kind table, `PointCloud`; the pad's `schemes_for`, `SINKS`, `pad_effects`, plan 42), each kind's adapter: `midi.py` + `apc40.py` / `generic.py`, `gamepad.py`, `hands/` (`hands/device.py` the wrapper), `bridge.py`, `osc.py`; and the host's own `app.Keys` / `app.Mouse` | every input and output the meta controller lists in `config.toml`'s `[[devices]]`, each opened behind its entry with its pickup state and a status line; the device list's watch and retry; the point clouds (`DeviceRegistry.clouds`) | MIDI rows / pad buttons / OSC hits / keys / mouse: the **base** (scene-setter slot); hands, bridge `ext`, the pad's axes, OSC axes: only `Router.feed` (feed slot); sinks read effective values after `reg.apply` and send them out, writing nothing | `devices.py` is the one importer of every adapter module, each inside its device's `open`; the core never imports `midi`, `bridge`, `osc` (above, and `tests/test_app_boundary.py`); routing and learn are handed the registry as an argument (`Router.use`, `Learn.devices`); `hands/core.py`, `signal.py`, `tape.py` import nothing from the package and `hands/device.py` and `hands/panel.py` are the only pieces that know the host (`tests/test_hands_boundary.py`); only `osc.py` and `devices.kinds()` name the OSC device (`tests/test_osc.py::test_only_osc_py_and_the_kind_table_name_the_osc_device`) |
| **Audio source** | `audio.py`, `analysis.py`, `analyzer.py`, `bands.py` (and the tests' `offline.py`) | capture or file playback, the FFT, the N band lanes | `Analyzer.lanes` (read by `Router.modulate`), the lanes' names (`AudioEngine.publish`) | imports only itself, `tapers` and `motion` (`tests/test_audio_boundary.py`) |
| **LFOs, envelopes, sequencer and clock** | `modbank.py`, `lfo.py`, `envelope.py`, `sequencer.py`, `tempo.py` | the modulator banks (plan 31: voices by stable id, up to 16 a bank) — the LFOs (four by default) and the envelopes (AHDSR, 1–5 always there for the sequencer's lanes); the step sequencer (five lanes × eight steps read off the clock); one tap-tempo clock with its trigger epoch | `Router.feed("lfo" / "env" / "seq", …)`, their labels and rests (`seq`'s lanes are trigger kinds); the sequencer queues envelope fires stamped with each step's time | `modbank`, `sequencer` and `tempo` import nothing from the package, `lfo` and `envelope` only `modbank`; registry, router and clock arrive as arguments (`tests/test_lfo_boundary.py`, `tests/test_modbank.py::test_modbank_imports_nothing_from_the_host`, `tests/test_envelope_boundary.py`, `tests/test_sequencer.py::test_the_sequencer_imports_nothing_from_the_host`) |
| **Render stack** | `geometry.py`, `view.py`, `field.py`, `graph.py`, `render.py`, `glsl.py`, `fx.py`, `masks.py`, `lookback.py`, `dream.py`, `segment.py`, `ghost.py`, `outputs.py`, `overlay.py`, `shaders/` | GL resources, `ViewState`, the shared camera (the eye, `eye.*`), the render graph (below), the instance field, the frame history, the dream worker, the segment workers and the mask passes (plan 39), the faces' picture, the one wall clock (`Renderer.now`) | the screen; `ViewState.integrate` writes `ang` directly | reads parameters, never writes one: `render.py` and `fx.py` import no `params`, `routing`, `library`, `preset`, `undo`, `control` (`tests/test_render.py::test_the_render_stack_imports_no_registry`); `outputs.py` imports `moderngl` and `glsl` only (`tests/test_outputs.py::test_outputs_imports_nothing_from_app_ui_or_params`); `dream` is imported only by `app._open_dream` behind `[dream] enabled` and is the one module that imports `torch` at its top (`tests/test_dream.py::test_core_does_not_import_the_worker`, which reads `segment.py`'s top-level imports too); plan 39: `masks.py` (the mask passes) imports `moderngl`, `numpy` and `glsl` only (`tests/test_graph_masks.py::test_masks_is_a_leaf`), and `segment.py` (the segment worker) is imported only inside `Renderer.segmenter`, on a segment's first need — never by `graph.py` (`tests/test_graph_segment.py::test_graph_py_never_imports_segment_py`), never on `import hyperspace.app`; Vision, `objc` and torch are imported inside the worker's first job (`Backend.open`) |
| **Graph** (in the render stack) | `graph.py` | the frame as nodes — geometries (the shape, the hands, a point cloud), the scene, layers, composites, one effect node per effect instance the loadable patch wires (wherever its wires put it: onto the faces, the pattern, the backdrop, an output or an `aux`), the pattern, backdrop and switch nodes, the look-back and the dream, the masks (plan 39: `matte`, `cut`, and `segment` with its `fg` / `bg` / `mask` pins), the history, the outputs — built by `build_graph` from the renderer's `Wiring` alone (a loadable patch's `/7` `graph` section, every edge a wire; a window's ports its own wires, else All outputs' by the meta controller's bus cables), the listed clouds and the effect files present, evaluated once a frame in dependency order; node instances (`ghost.2`, `fx.acid.2`), the graph JSON's reader (`read_graph`, `NODE_KINDS`) | the screens, through the render stack's passes; nothing in the registry | imports `moderngl`, `numpy`, `geometry` and `outputs` only — no `params`, `routing`, `library`, `preset`, `undo`, `control`, `devices`, and neither `masks` nor `segment`, `Vision` or `torch` (plan 39: the passes and the worker are reached duck-typed, `frame.r.mask_passes()`, `frame.r.segmenter(name)`); node methods are `run` / `paint` / `draw` / `image` / `depth`, never `apply`, `modulate`, `snapshot`, `set_value` (`tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`); the device registry reaches it duck-typed (`Renderer.cloud_source`) |
| **Panel** | `ui.py`, `ui_*.py`, `hands/panel.py`, `control.py`, `graphview.py` | imgui state, page selection, the Replace / Keep modal, the routing page's edits, the GRAPH page (`ui_graph.py` drawing `graphview.py`'s model on `imgui_node_editor`; its editor context held on the panel; its selection published on the panel as `Panel.graph_selected` / `graph_selected_at`, driven from outside by `Panel.select_graph_node`, its params `Panel.graph_selected_params`) | param **bases** through `Param.set*`; table rows through the table's edit doors and `Learn` | only `app`, `hands/panel.py` and the `ui*` modules import `ui*`. By convention: no test holds it; `graphview` imports no imgui (`tests/test_graphview.py::test_graphview_imports_no_imgui`) and edits only through the table's own calls and the loadable patch's `graph` section |
| **Media** | `media/` (`frame`, `source`, `ids`, `pool`, `adapters`, `still`, `video`, `proxy`, `transport`, `mixer`, `channels`, `folder`, `thumbs`, `live`, `ndi`, `syphon`, `camera`, `panel`, `publish`), `media_tex.py`, `ui_media.py` | the eight channels (`MediaState`: bins, sources, transports), the media folder (`MediaFolder`), live kinds, the built-in `panel:graph` (`media.panel.PanelSource`, 2026-11-02: the GRAPH canvas off `outputs.CanvasTap`, answered by `app.MediaResolver.builtin` before the devices' feeds; `media.live.SharedSource` is what it and `LiveSource` share — holders under one lock, the newest frame, the status words; whether GRAPH is drawing is read from the panel, `Panel.canvas_px`, through `on_page`), the publishers; `MediaTextures` (a texture per channel; one wrapper per distinct GPU texture — name, size and the source's generation, every channel's together) on the renderer | nothing in the registry: `media.<c>.*` params are read when a channel polls; `MediaTextures` writes textures, `publish` hands finished frames to Syphon / NDI | `import hyperspace.app` imports none of `av`, `pillow_heif`, `syphon`, `cyndilib`, `AVFoundation`: each adapter library is imported inside the function that opens a source (`tests/test_app_boundary.py`); the render graph reaches a channel duck-typed (`graph.MEDIA_CHANNELS`, held equal to `channels.CHANNELS` by a test); the frame thread never decodes, resizes, scans or joins (below); a `segment` (plan 39) wired straight from a channel whose newest `MediaFrame` has CPU pixels (a camera, NDI) and a cover fit hands the worker that array (`Renderer.media_now`) and no readback runs — the shortcut changes where the worker reads, never what is wired |
| **Library** | `library.py`, `loadable.py`, `patches.py`, `config.py` | the library root (`Library.home`: module presets, loadable patches, patches (plan 40, §3.11), shows (projects) — the home, or the folder `[library] path` names; one tier since 2026-10-28: nothing ships with the app, every loadable patch is yours; loadable patches in folders, plan 48), the machine home (`Library.machine`: `last_show`, the trash since plan 48), the desk's bank of twenty-four, `config.toml` (its `[[devices]]` list checked per entry, the old device tables translated; `config.read_devices` for the registry's watch) | bases through `Registry.restore`; a loadable patch load replaces the table's performer rows, desk layer and macros | `library` imports `params` and `undo` (and `routing`, `preset` lazily), never `config` (`tests/test_app_boundary.py::test_the_library_never_imports_config`) |
| **Undo** | `undo.py` (with `keep_open` / `let_close`, a step a held control or a clutch keeps open; `watching`, a registry's own `Undo`) | the undo and redo stacks, the last settled state | bases (`Registry.restore`) and the table's loadable patch parts, on ⌘Z / Ctrl+Z only | a leaf: imports nothing from the package and never touches `modulate` or `feed` (`tests/test_undo.py::test_undo_imports_nothing_from_the_package`) |
| **Host** | `app.py`, `hotreload.py`, `placement.py`, `watchdog.py` | construction order, the frame loop, the windows and render outputs, the hold (plan 38: the program's held wiring, bus cables and values, the preview renderer), the reload watch list, the stall log, where the library is (`[library] path` → `Library(path, machine=home)`) | bases for the relative writers (↑ / ↓; the pad's sticks are the pad device's own, `gamepad.steer`); no key of its own but `app.LOOP_KEYS` | builds the device registry (`app._open_devices`: every device behind its own `[[devices]]` entry) and the dream worker behind `[dream] enabled` (`_open_dream`, the one gate left); `Host.devices`, one close list `Host.adapters == (media, devices, dream_io)` (the media close first); importing `app` imports no gated adapter, no `osc`, no `pythonosc`, no `torch`, no `leap`, and (plan 39) no `hyperspace.segment`, `Vision`, `CoreML` or `torchvision` (`tests/test_app_boundary.py::test_importing_app_leaves_every_gated_adapter_unimported`); the host hands the program renderer `[segment]` (`renderer.segment_cfg`) and closes its segment workers beside the dream's, at quit and restart; `placement` is a leaf (`tests/test_placement.py::test_placement_imports_nothing_from_the_package`) |

**Everything points at the registry; the registry points at nothing
above it.** Devices and sources feed the router; the router writes
offsets; the panel, the desk and the library write bases; the render
stack only reads.

**Leaves** — modules that import nothing from the package, so anything
may import them: `analysis`, `tapers`, `motion`, `undo`, `placement`,
`geometry`, `patterns`, `tempo`, `modbank`, `sequencer`, `glsl`, `gamepad`, `apc40`,
`generic`, `watchdog`, `modgraph`, `players`, `pointer`, `hands/signal.py`, `hands/tape.py`.
`devices` imports nothing from the package at load: every adapter, and
`routing`, only inside a function. Near-leaves: `outputs`, `fx`,
`lookback` and `masks` (plan 39) import only `glsl`; `view` and `field` only `geometry`; `lfo` and
`envelope` only `modbank` (plan 31); `modifiers` only
`motion` and `tapers`; `routing_sources` only `motion` (plan 44 D2,
`tests/test_routing_boundary.py`) (`modgraph` is held by
`tests/test_modgraph.py::test_modgraph_is_a_leaf`; `modifiers` by convention
and the hot reloader's order test).

---

## 2. The frame

`app.main()` is the only entry point. It builds an `app.Host` once and
runs `app.frame(host, now, dt, fps)` in its loop — the one place the
frame order exists. `main` keeps what needs the window system (events,
`imgui.new_frame()`, `now` and `dt`, the swaps).
`tests/test_app_boundary.py::test_the_frame_runs_in_the_documented_order`
pins this order over stubs:

| # | Step | Writes |
|---|---|---|
| 0 | `clock.tick(now)`, `reloader.poll()`; Q quits (Esc does not); ⌘R restarts (claims R's edge first) | — |
| 1 | `router.keys(keys)` — key rows, R, F1–F8 / ⇧F1–F8, ⌘Z among them; ↑ / ↓ ride `view.depth4` (`_ride_depth`) | bases |
| 2 | `devices.poll(dt, now, router=, learn=)` — **the scene-setter slot**: every open device in `[[devices]]` order is polled (`poll`), offered to an armed Learn (`learn`), then delivers its rows (`act`). The pad: `Pad.poll`, `gamepad.learn_from`, `router.pad(pad)` (the `axis` lanes fed, then the button rows), then the sticks' camera job (`gamepad.steer`: each stick or trigger no route names, through `nudge` / `scale`, `router.claimed("axis")`); each MIDI desk: `MidiIO.poll` — the rows of its layer that is up and the invariant rows, knob glides, an armed desk Learn's candidate; the bridge and a `midi-out`: their ports looked for again; an OSC device: its socket read, its hits as rows; a cloud: its frame. Every ~30 frames the registry also looks at `config.toml`'s mtime (`DeviceRegistry.watch`). Right after it, `media.poll(dt, now)` (plan 32): each of the eight channels checks whether the id at its slot changed (a source opened, the old one queued for the closer thread), steps a timed source's transport and tells its source where to be, and every second asks the resolver again; it decodes, scans and joins nothing | bases (`media.<c>.*` are read, not written) |
| 3 | `router.follow_macros()` — a macro whose base moved sets its base subscribers' bases | bases |
| 4 | `undo.tick(now)` — compares the watched bases and the loadable patch's table with last frame's | nothing |
| 5 | `output.apply()` for every output; `renderer.bg_alpha` and `renderer.dim` handed over | window state |
| 6 | `mouse.poll(shift)` — orbit, pan, zoom through `nudge` / `scale` | bases |
| 7 | `audio.step(dt)`, `audio.publish(router)` | lanes |
| 8 | `devices.feed(router)` — **the feed slot**: the hands feed `hand` and `hands` (`HandsIO.poll`, which may complete a hand Learn and makes the frame's DAW messages); the bridge feeds `ext` and publishes its labels and rests; an OSC device feeds its role's axes | feed |
| 9 | the modulator banks and the sequencer, **inside the pass** (step 10): every bank's `begin` and `publish` first (the LFOs, the envelopes — a held global trigger lands and moves `clock.epoch`); then `Router._step_sequencer` — `Sequencer.step` fires each crossed step's envelope (`Envelopes.fire(n, at=t_k, gate=…)`) and feeds `seq`; then the plan, where each voice steps at its own node (`Bank.step_one`), feeding `lfo` and `env` (plan 28 N0, plan 31) | feed |
| 10 | `router.modulate(chain, dt, now)` — the modulation patch (`Router.modgraph`, `modgraph.order`) in dependency order: at a bank voice's node (an LFO's, an envelope's) it steps; at a modifier's it steps the modifier and writes its `mod` lane; at a param's, every live performer row on it calls `p.modulate(offset)`, and a param a later node reads (a `scale`, a macro behind a depth subscriber, an LFO knob, a modifier's own param) is landed there and then (`Param.apply` under the frame's mark) | offsets; the `lfo`, `env`, `seq` and `mod` lanes; the objects of the params the pass reads |
| 11 | `reg.apply()` — base + offsets onto every other live object (a param the pass landed under this frame's mark is skipped) | objects |
| 11a | Plan 44 D4: each deck off air's `router.modulate` and `reg.apply` (a row on a shared meta param a hot reload left standing dormant, row 745, so it reads this frame's meta controller values; no door lets one in, row 743; its macros at step 8's slot, its integrator with the on-air deck's) | that deck's objects |
| 12 | `devices.send(reg, chain)` — **the sink slot**: the bridge sends its sink rows (`routing.sink_values`: effective values, the lanes) through `Bridge.send_values`; `hands-daw` sends the hands' DAW messages and its own sink rows | nothing in the app (MIDI out) |
| 13 | `view.integrate(dt)` — `ang += rate · dt`; on the frame the 3D switch changes, the 4D pose folded into `body` (`held`) | an object, directly |
| 14 | `renderer.bands = app._bands(audio)` — the analyzer's lanes, out / CEIL, handed to the renderer as a read-only input; then `draw_render` — the render graph evaluated, every render output (below) | the screens |
| 15 | `draw_panel` — the control window | bases, rows |

Rules that follow from the order:

- **Dependency order, no lag** (plan 28, decision 7). Everything a
  performer moves lands in this frame's pass in dependency order:
  `Router.modulate` runs the table as a graph (`modgraph.py`;
  `Router.build_modgraph`, cached as `Router.modgraph` and rebuilt only when
  the table's rows, macros or modifiers, each bank's ids or the registry's
  params change), each node after everything it reads. Its nodes are the
  fed lanes, each bank's voices (the LFOs, the envelopes), the modifiers, the macros and the params; its
  edges a performer row (into a param's `mod`), a row's gate, a `scale`
  or a macro's depth subscriber (into the cable's `depth`), a voice's knob
  params (an envelope's `fire` and `gate` among them), a modifier's inputs and params. An LFO is a source with
  inputs — its knobs land, then it steps; a modifier likewise; a `scale`
  param or a macro behind a depth subscriber lands before the cable that
  reads it. So an LFO owning
  another LFO's depth, a macro scaling a push, a `scale` that is itself
  modulated all land **this frame**
  (`tests/test_lfo.py::test_an_lfo_owning_another_lfos_depth_changes_its_output_the_same_frame`,
  `tests/test_routing.py::test_a_macro_owned_by_a_hand_scales_a_lanes_push_the_same_frame`),
  and every corpus loadable patch (`tests/corpus/presets/`) lands the same values as before, a frame
  earlier where it was late
  (`tests/test_routing.py::test_every_factory_loadable_lands_the_same_values_one_frame_earlier`).
  **Nothing reads a stale value but through a delay node**: a loop that
  passes through no `delay` modifier is refused — its last cable in table
  order is kept off (a loop of modifiers alone: its last modifier's input
  on the loop), the row left in the table and the file, a note on
  ROUTING's head (`Router.modgraph_notes`;
  `tests/test_routing.py::test_a_cycle_without_a_delay_disables_its_last_cable_with_a_note`,
  `tests/test_modgraph.py::test_a_loop_of_modifiers_alone_keeps_its_last_input_off_with_a_note`).
  A delay that closes a loop runs first and emits its input's lane as it
  stood last frame, so the loop is exactly one frame late; a delay on no
  loop runs after its input and holds it for the next frame
  (`tests/test_modgraph.py::test_a_loop_through_a_delay_runs_exactly_one_frame_late`).
  A macro's base subscribers are scene-setters (step 3), not part of the
  order. Only the params something later in the pass reads are landed in
  it; every other param lands in step 11, in registry order, as before. `Param.apply` is idempotent within a frame (`Registry.begin_frame`
  opens a mark, `Registry.apply` closes it): a param the pass landed is
  never applied twice. The readers outside the pass still read last
  frame's objects: `output.apply` (step 5) and the analyzer (step 7). The
  sinks run **after** `apply()` (step 12) and read this frame's effective
  values, so a param sent to the DAW is not a frame behind
  (`tests/test_sinks.py::test_a_param_routed_to_the_bridge_sends_its_effective_value_after_apply`,
  `tests/test_routing.py::test_sinks_still_send_after_apply`).
- **Devices poll with the scene-setters, feed with the sources, send
  after `apply()`** — the three slots of the registry, each over the open
  devices in `[[devices]]` order
  (`tests/test_devices.py::test_devices_run_in_list_order_poll_learn_act_then_feed_then_send`).
  `ORDER` pins them by stub name: the pad's rows and its camera job, then
  MIDI's rows, then the bridge's ports in step 2; the hands and the
  bridge's `ext` in step 8; the bridge's sink rows in step 12.
- **Base before offset.** Every scene-setter runs before `router.modulate`
  (the panel's edits are the previous frame's tail), so a base write and
  the offsets on it combine in one `apply()`. The one writer after
  `apply()` is `ViewState.integrate`; `Param.apply` adopts that write as a
  delta on the base next frame
  (`tests/test_modulation.py::test_a_direct_object_write_is_adopted_into_the_base`).
- **The undo watcher sits between the scene-setters and the feeds**, so it
  sees every base this frame's keys, devices' rows and macros wrote and no
  performer has run. It writes nothing; `edit.undo` / `edit.redo` are
  key-row triggers in step 1 (`tests/test_undo.py::test_an_idle_app_makes_no_step`).
- **Guards.** Each device's every step (`DeviceRegistry._guard`: one
  device's exception is its own `error:` line and the frame's toast, and
  the next device runs; a raising `poll` skips that device's rows for the
  frame), the macro step, the undo tick, steps 7–13 as one block, the
  render draw and the panel draw are each wrapped: hot-reloaded code that
  raises sets `reloader.runtime_error` (cleared by the next clean frame)
  and the loop goes on
  (`tests/test_app_boundary.py::test_a_raising_step_is_recorded_and_the_windows_still_draw`,
  `::test_a_raising_adapter_is_a_note_that_survives_the_frame`,
  `tests/test_devices.py::test_one_devices_exception_never_stops_the_frame`).
  The key block is not wrapped, so the module-level `undo.push` /
  `undo.undo` / `undo.redo` catch their own exceptions (`undo._guarded`).
  A raising render draw is also `watchdog.RenderWatch`'s: logged to
  `<home>/stall.log` and named on the control window's banner until
  dismissed.
- **A hand outside the interaction box is absent before any lane is
  fed.** `HandsIO.poll` decides presence first — confidence floor, then
  the palm inside `hands.json`'s box (`hands.core.inside`, with a
  Schmitt edge, `HandsIO._in_box`). An absent hand's axes read `NaN`, so
  its rows let go and the base returns that frame; nothing downstream
  knows there is a box
  (`tests/test_hands.py::test_a_hand_outside_the_box_reads_absent_everywhere`).
- **Shared meta params are declared before the show lands.** `app.main` calls
  `app._desk_table` (`routing.register_desk`, then
  `slew = routing.SLEW_DEFAULT_S`) and `overlay.register_switches` before
  `library.attach(reg)`, which takes the registry as it stands as "fresh"
  and then lands the show's session values
  (`tests/test_app_boundary.py::test_the_app_starts_with_knob_smoothing_at_80_ms_and_a_show_keeps_its_own`).

### Drawing: the render graph, a picture per output

`app._draw_render` makes output 1 current, builds one `outputs.View` per
opened output (output 1's with `target=ctx.screen`, a later output's with
its `Presenter`) and calls `Renderer.draw_outputs(s, w, h, dpr, views)`.
`Renderer.draw` is the same call with one default `View` on the bound
framebuffer. `Renderer._draw_frame` settles the frame's size under the
render cap and ticks the effect folder, then **evaluates the render
graph** (`graph.py`): the graph for these views — built by
`graph.build_graph` from the renderer's `Wiring` (the loadable patch's wired
frame) and the listed `cloud` devices, and reused until the window count,
the wiring or the clouds change (`Renderer._graph_for`; a window's mutes
never rebuild it) — runs its nodes once each, in
dependency order settled when it was built (`Graph.order`,
`Graph.evaluate`), each node timed on the GPU (`render.PassTimer`). For
one default output:

```text
GEOMETRY   [cloud …]  shape   hands[.n]    draw calls in the shared camera (the eye); a hands
                      node is in the scene only if a wire puts it in `scene.geometry`
SCENE      scene      the solid geometries first (a cloud, in-scene hands: depth written),
                      then the see-through shape, painter-sorted, depth-tested against them;
                      the face picture first, only while a picture other than the plain
                      pattern is wired into `shape.faces` (plan 33)
LAYER      lookback(cover)   the faces' mask, only while the look-back occludes
           hands.layer       Ghost.layer: the hands alone, own colour + depth — only if a wire reads it
BACKDROP   backdrop   the scene over `backdrop.image` at `backdrop.alpha` (plan 35: `grounded` merged)
HISTORY    lookback   the age-weighted trail of its `image`, alone (plan 36; the echoes' clock);
                      dream (plan 36) is its own node: its `image` in, the dreamed picture out
EFFECT     acid … palette, copy …   one node per wired effect instance, and a `copy` for an
                      instance drawn on another picture; on, its pass over its input into a
                      pool texture or its consumer; off, its input read through
MASK       matte, segment   (plan 39) a one-channel mask at its maker's size: matte from a picture
                      (luma, alpha, chroma); segment from its worker's model, a frame or two
                      late, or a motion model on the frame thread; cut and segment.fg/.bg are
                      pictures cut by a mask; a mask a picture port reads is promoted (white
                      where it passes, black elsewhere) by an untimed `<mask>(picture)` node
SHOWN      shown(src) one per distinct picture an output shows → the window itself when it is
                      the picture's only consumer at the frame size, else a frame texture
                      [a copy chain over a hands composite stands down to its originals
                       while it bends nothing: Shown.fallback]
HISTORY    lookback(capture)   the ring takes what is wired to `lookback.capture`, exactly
                      once, after every Shown, every delay's write and every output's
                      hands and guide source (a sink: it runs when nothing shows the look-back)
OUTPUT     output.N   its own `image` wire, else `output.all`'s, else the ground; the hands
                      over it, the guide over everything, through the window's mutes; the
                      flips; dim: Renderer.dim × the view's own (Renderer.dim_pass)
EXIT  views[0].target bound again with its rect and blending, a raise included
THEN in app._draw_render: glFlush (only with a later output); each later output
  Presenter.present then swap; output 1 swapped last
```

**On air and off air** (plan 44 D5, the owner, 2026-11-04). `deck.MetaController` owns two
fixed `Deck`s, each a whole look with its own renderer on one context. `output.xfade`, the
desk's crossfader, decides: 0 deck 1 alone, 1 deck 2 alone, on air the one it is closer to
(`follow_fader`). `app.frame` ticks it first of all, so every handle reads the frame's deck
from the frame's first line. Above 0 the other deck draws too and `Renderer._compose` mixes it
before the dim (`deck.Fade`). The panel looks at either (`point_panel`): on the deck off air
its backdrop is that deck's picture (`Fade.preview`), output 1 rides a second `Preview` (the
ON AIR inset), and GRAPH frames its canvas red. Two verbs and no others: the crossfade, by
hand or timed, and `copy_on_air`. HOLD, TAKE and DROP are gone (plan 38's program and preview,
`hold.py`), since with two decks there is nothing to hold. No patch reaches the other deck:
`tests/test_on_off_air.py::test_no_patch_reaches_the_other_deck`.

A Scene or Layer node *makes* a texture; the history, composite and
effect nodes *paint* into the framebuffer their consumer hands them, so
nothing is quantised between the look-back and the first effect. The
`Wiring` (a loadable patch's `graph` section) can put the hands inside the
scene, lay their layer added or depth-aware, and wire the capture to
the scene with the hands' layer; a second hands node or effect instance
is a node of its own. Evaluating the frame as a graph moved no pixel of
the 427 golden frames recorded before it, and making each effect its
own node (plan 30) moved none of the 556 recorded before that, nor did
the modulation graph and the wire list (plan 28) move any of the 580
recorded before them (`tests/test_golden_frames.py`).

**Effects as nodes; placement** (plan 30, plan 33). Plan 30 made effects
nodes; plan 33 removed the stack they sat in. Every effect instance is an
`Effect` node (one `image` in, an image out, its params `fx.<name>.*`,
its pass `FxChain.run_one`), and it exists only where the loadable patch's graph
wires it: there is no order and no target. (Plan 33's **run** — the
effects wired from `frame` to `fx.image`, ending in an `Fx` node — is
gone since plan 35's wired frame: an effect is a node wherever its wires
put it, between the scene and an output.) Every instance in a run is a node, on or off,
so a toggle changes no node; an instance or a file changed rebuilds the
graph (`Renderer._graph_for`'s key holds the effect files present, not an
order). Plan 30's
**placement** (`after` / `into` a node by name) is read only by the
one-way migration since plan 36 (`graphmigrate.placed_wires` writes each
as the wires it stood for); in a `/7` frame an entry's `after` / `into`
is dropped with a note (`PLACEMENT_IS_A_WIRE`), the effect where its
wires put it. The textures the effects paint
into are one pool (`FxChain.pool`, sized by `Graph.pool`), and a held
picture is never handed to the consumer that paints into it. The faces
have no chain of their own: their effects are nodes on a branch into
`shape.faces`. The ports are typed
`image`, `mask`, `geometry` and `value`; `graph.VALUE` is declared for
the palette's lights-out and camera-in ports and no node uses it. A
**mask** (plan 39) is the owner's meaning: a pattern, a pixel passes (1)
or it does not (0), a value between only at an edge a feather or softness
asked for; one channel, 8-bit, at its maker's size. It never rides in a
picture's alpha. Its makers are `matte`, `segment.mask` and `scene.cover`;
its takers `cut.mask` and `lookback.cover`. **The promotion is one-way:** a
mask may be wired into any picture port and reads there as white
(premultiplied, opaque) where it passes and black elsewhere, fitted by
cover at the consumer's size (`graph.MaskPicture`); a picture is never
read as a mask — wired into a mask port it is refused in words ("… put a
matte between"), and the converter is always a `matte`.

**Wires; outputs as nodes** (plan 28 N4). A loadable patch's graph may also carry
a wire list, `{"from": "<node>", "to": "<node>.<port>"}`: into an
effect's `image`, the history's, a composite's `under` / `over`, or an
output's `image`, `hands` or `readout`. D1's `after` / `into` are wires
written short. A wire into `output.<n>.image` gives that output an end
of its own (`graph.Wired`, `wire(output.<n>)`) showing that picture;
into `.hands` it lays that node over; into `.readout` that layer's
guide. (Plan 36: an output no wire names shows nothing, or its bus cable's
picture, never a default; see "The WYSIWYG graph" below.) A load never
writes a switch. The
wires ride in `Wiring`, so the graph is rebuilt when they change. A
refused wire (another type, a missing node or port, two into one port, a
loop) is dropped with a note — the port takes nothing (plan 36: no
default fills it)
(`tests/test_graph_wires.py::test_a_wire_into_an_output_overrides_its_switch_and_an_unnamed_output_keeps_them`,
`::test_a_wire_of_the_wrong_type_or_into_a_missing_port_is_a_note_and_the_default`,
`::test_a_cycle_of_wires_is_refused`). The GRAPH page edits both this
graph and the modulation (§5).

**The free graph** (plan 33). An effect exists where the loadable patch wires it
and nowhere else. Four new wire ends turn the old params and the stack
into wires: `frame` (a pipeline's picture before its effects), `fx.image`
(the pipeline end's input), `pattern` (the face pattern and its media
layer as a picture; `media` in) and `backdrop` (`image` in), plus
`shape.faces`, the faces' one input. A loadable patch's **run** is
`frame → acid.image`, `acid → wobble.image`, `wobble → fx.image`
(`graph.run_of`, held in `Wiring.run`); every pipeline draws the same run
on its own picture, and an empty run is the bare `frame → fx.image`. Any
other path of effects and composites is a **branch**: from a channel, the
pattern, the scene or another effect, to a **sink** (`graph.SINKS`: an
output, the faces, the pattern's media layer, the backdrop, the history,
the pipeline end). A node no path leads from to a sink is **unreached**
(`graph.reaches`): kept in the loadable patch, drawn faint, never built. Branches
are made once a frame at the size their consumer asks (`Frame.at(size)`,
`Node.size_for(port, frame)`; the faces ask 1024², `pattern.media` its
head's size, everything else the frame's) and shared. `shape.faces`
unwired, or wired straight from `pattern`, draws per face with no extra
pass; through effects from `pattern` it is the old ping-pong into the
1024² `face_pic`; from anything else, that picture is `u_pic`. A source
that reads nothing makes the faces show the pattern for that frame. A
channel wired straight into `pattern.media` or `backdrop.image` is plan 32
byte for byte. A **switch** (`graph.SwitchNode`, eight `IMAGE` inputs,
`switch[.n].select` declared by `params.declare_switches`) passes its
picked input through as a cut; `Graph.pulled(frame)` follows only the
picks, so an unselected branch is not made and an unread channel is not
uploaded. **Old loadable patches** are read as this graph on load
(`graphmigrate.migrate`: the effects that are on, or driven, in
`(order, name)` order become the run; `view.media`, `backdrop.channel` and
a route onto either become channel wires or a switch) and written back
as they were when nothing needs more: `preset.schema_of` picks `/5`
(`graphmigrate.needs_free`) only for a graph `/4` cannot say, and a save
below that lays `legacy_values` over the values and strips the plan-33
words from the section (`legacy_section`). The render side imports none
of this; `graph.py` still imports the render stack only
(`tests/test_graph_free.py`, `tests/test_graph_faces.py`,
`tests/test_graph_switch.py`, `tests/test_graph_migrate.py`). Pictures
unmoved: the 661 goldens before it.

**The wired frame** (plan 35). The three paragraphs above (placement,
wires, the free graph) describe the vocabulary as plan 33 left it; where
they say `frame`, `fx.image`, `history`, `ghost`, `readout`, `media.a` or a
pipeline, read the wired frame's names and wires below (`hands`,
`hands.guide`, `lookback`, `channel.a`; the run is wires into
`output.all.image`). Since plan 35 there is no default graph:
every section the app reads is a **wired frame** (`"frame": "wired"`), and
`graph.build_graph(views, wiring, clouds, effects)` builds only what its
wires reach (`graph.reaches`: a path to an output's port, to `output.all`'s
or to `lookback.capture`). The frame's own nodes are ordinary: `shape`,
`scene` (its `geometry` port takes the shape, the hands and the clouds the
meta controller lists, in wire order), `backdrop` (`scene` over `image`), `pattern`,
`lookback` (`image`, `capture`, `occluder`), `hands[.n]` with its
`.layer` and `.guide`, `channel.<c>`, effects and their `copy`, and the
outputs. `frame`, `fx`, `grounded`, `capture` and `cover` are not nodes of
the section, and there are no pipelines: the old per-pipeline run is wires
and copies. **`Shown`** is the one internal end: one per distinct picture
an output shows, carrying the direct paint into a window, the stand-down
(`Shown.fallback`, `Output.settle`) and the count of users per frame
through the mutes. **An output** shows its own `image`, `hands` and `guide`
wires, else **All outputs'** (`output.all`: a node with the output ports, no
params, always on the canvas), else its ground (`(0, 0, 0, View.bg_alpha)`:
black, or see-through in overlay). **The mutes** are the window's own
`output.N.scene` (picture) and `output.N.hands` switches, read every frame
(`Frame.users` counts through them), never in a loadable patch, never a rebuild;
a hands mute wins over a stand-down. **The capture is a sink**: the
internal `Capture` runs once, after every `Shown`, every `DelayWrite` and
every output's hands and guide source, so what is wired into
`lookback.capture` runs although nothing shows the look-back, and it closes
no loop. A node no path reaches is unreached (kept, drawn faint, never
built); a wire into `output.N` past the window count builds nothing and is
reported dormant. **Old loadable patches** are migrated to the wiring today's frame
drew (`graphmigrate.migrate`: plan 33's run, then `renamed`, then
`wired_section`, written once into All outputs by `frame_wires`), and each
golden output state is that output's own wires (`output_wires`). It is
proved, not hoped: `graph.signature(g)` fingerprints the chains behind each
output's `image`, `hands`, `guide`, `depth` and stand-down plus the order
of the nodes a frame can show, and `tests/fixtures/frame-signatures.json`
records 125 cases first made by the deleted `default_graph`
(`tests/test_graph_frame.py::test_the_wired_frame_builds_what_default_graph_builds`).
The 717 goldens before the plan did not move; 24 are new, for three `/6`
fixtures (741; 757 with plan 34 T4's resize fixtures). The ids are renamed in one table (`graph.new_id`,
`old_id`, `param_prefix`; `graphmigrate.renamed`), and a save writes the
lowest schema that loses nothing (`graphmigrate.unwired`).

**Feedback, look-back sources and the resize** (plan 34, rows 353–371).
Four node kinds on the wired frame: `delay`, `resize`, `echo.<k>` and
`dream`. **The delay is z⁻¹ in `build_graph`.** `Delay` has no inputs and
paints the read side of a half-float ping-pong pair the renderer holds
under its name (`Renderer.delay_pair`, `render.DelayPair`, swapped by
`Renderer._turn_delays` at the frame's start, kept across rebuilds — not
loads: a loadable patch load resets them, `Renderer.reset_delays` — and
released `SIZED_KEEP_FRAMES` frames after the delay leaves the graph), so
an edge into it is no dependency and a loop through one is legal.
`_Build.build` adds, for each delay the wires reach, a `DelayWrite`
(`<delay>(write)`, timed on SYSTEM) *before* the internal `Capture`, in the
capture's `after`, the way `Shown` ends are; it paints the delay's `image`
into the write side at the input's own size, else the frame's, and an
input that read nothing leaves the pair unwritten (the delay then reads
nothing next frame and the faces show the pattern). A read of an echo at an
output's `hands` is ordered before the capture the same way. **`echo.k`
and `dream` are picture sources** over the look-back's ring
(`Lookback.echo_slot`); the ring keeps capturing for them with the
look-back off (`Graph.reads_ring` → `Lookback.keep`). **Own size.**
`Node.own_size(frame)` is None for every node of plan 33 and earlier; a
delay, an echo, the dream and a resize have one, which breaks "the consumer
decides" on purpose: `Node.size_for` asks an own-sized input for its own
size, `Effect` after one runs at it (its pool keyed by that size), and a
consumer of another shape gets the picture fitted by cover through
`Renderer._refit` (`OWN_FIT`; a delay's `#fit` target for a node that binds
a texture). **`ResizeNode`** is built by `_Build._make` only where the wires
reach it, its params from its entry (`params.declare_resizes`, group
`resize`, values in `ViewState.resize`, read as `Frame.resizes`); it makes
its picture once a frame, when pulled, into a half-float `(name#own, size)`
target by one `_refit` (crop as a centre and a size, cover/contain/stretch,
mipmapped trilinear past a 2× shrink or nearest) and `_prune_sized` drops
the targets it left; a resize with no input is dormant, and one no wire
takes anywhere is not built (its params stay while its entry does). **The
loop check** reads what the wires say plus `HIDDEN_EDGES` in a wired frame
(`sink_loops`, `loop_words`: `LOOP_FACES`, `LOOP_BACKDROP`, `LOOP_PLAIN`),
and `FRAME_EDGES` for an old section's read before it migrates; both leave
an edge into a delay out. GRAPH draws none of the internals: `delay(write)`
is not a node on the canvas, a delay's `image` port is the pin
`rin:<delay>/image`. Pictures unmoved: the 741 goldens before the resize fixtures
(`tests/test_graph_delay.py`, `tests/test_graph_echo.py`,
`tests/test_graph_resize.py`, `tests/test_graph_feedback.py`).

**The WYSIWYG graph** (plan 36, `hyperspace.preset/7`). The graph on GRAPH
is the whole truth: nothing is filled in at load (`graphmigrate.migrate`'s
fill-in, `wired()`, `Wiring()` as a fallback, "the default placement", the
`into`/`after` keys are gone; a loadable patch with no `graph` section is empty),
no edge is hidden, and a window shows only its own wires.

- **The bus.** All outputs reaches a window only through a drawn cable
  `output.all.<port> → output.N.<port>` (image, hands, guide, depth: four
  bus ports). The cables are the meta controller's, and which of them stand is the
  loadable patch's (plan 44 D3: `graph.BusCuts` as `loadable.LoadedPatch.bus`, saved in
  the loadable patch under `bus` as `{"cut": [...]}`, written only when something is
  cut, in its dirty dot and its load's undo step; an old show's `rig` is
  handed to old loadable patches once, `library.Project.old_cuts`); the renderer
  reads it through `Renderer.bus_source` (the loadable patches, `LoadedPatch.bus_cuts`), so a
  cut rebuilds the graph. `graph.window_ports(wires, n, rig)` is the one place
  a window's port is resolved: its own wire, else the standing bus cable,
  else nothing. `Output.settle`, `Shown.fallback` and the bent stand-down
  are deleted; a window's hands mute removes the hands layer from that
  window's chain (`_Build._mute_hands`).
- **Hidden edges, now ports.** `pattern → shape.faces` (unwired: plain
  faces), `scene.cover → lookback.cover`, `hands → hands.layer` and
  `hands.guide`, `cloud.N → scene.geometry`, `scene.depth →
  composite.depth` with `blend` a param of each composite. The loop check's
  `HIDDEN_EDGES` is retired with them.
- **Look-back and dream.** `lookback` records `image` into its own ring
  (several may exist) and outputs the trail with alpha; `cover` is its
  optional mask; `echo.k` are frames of this node's ring. `dream` submits
  its `image` to the worker at its own cadence and outputs the dreamed
  picture with its chroma; `dream.on` off passes the input through and
  stops the worker; one live dream, a second refused in words. Old loadable patches
  migrate to `scene → lookback → dream → composite → output`.
- **Schema `/7`.** A save writes `/7` only; `graphmigrate` reads `/4`-`/6`
  as an explicit one-way migration with a note on load, and
  `tools/migrate_library.py` rewrites a library (the 25 corpus files,
  `tests/corpus/presets/`, are its output, their `/6` sources in
  `tests/fixtures/factory-sources/`).
  `graph.signature` and the goldens prove each migration. The depths onto
  the effects' retapered params are moved without a schema bump
  (`units["fx.depth"]` marks a file; `tools/retaper_routes.py`, wave 0 T1).
- **A new loadable patch and "preset only".** `LoadedPatch.new` lays `shape → scene →
  output.all.image` where GRAPH is looking; `graphview.STARTERS` are
  pre-wired groups the picker adds (a picture cable's menu offers
  `CABLE_STARTERS` on its picture; **feedback**, wave 0 E1, 2026-11-02, is
  a delay loop with a blend spliced in by the insert table —
  `_feedback_starter`, `FEEDBACK_LEVEL`, the `fade` effect its decay, many
  allowed — and a picture node's menu has **add feedback after**,
  `ui_graph.add_feedback_after` over `graphview.picture_feeds`, laid under
  the node's box by `ui_graph.node_below`; the recommendation pending the
  owner: delay loops are the trails mechanism, the look-back keeps the
  dream, DECISIONS "Feedback"). `graphview.patch_only(view)` returns
  the ids GRAPH draws (the section's nodes, whatever is cabled to them and
  what feeds those to full depth, every output and every media channel);
  `ui_graph.hidden_ids` hides the rest without mutating or laying out
  anything, except a node the picker added this session
  (`ui_graph.reveal_node`: page state, never saved, 2026-10-31).
- **Known limitation.** The migrated dream dreams the look-back's
  occluded trail, not the raw capture (`plans/36-wysiwyg-graph.md`,
  register row 412).

**Masks and vision** (plan 39, rows 440–497). Three node kinds, built
by `_Build._make` only where a wire reaches them, their params declared
per instance (`params.declare_mattes`, `declare_cuts`, `declare_segments`,
groups `matte`, `cut`, `segment`, the loadable patch's) and read as `Frame.mattes`,
`.cuts`, `.segments`; the passes are `masks.MaskPasses` (`Renderer.mask_passes()`,
compiled once, each into its own `_frame_target`, never reading what it writes).

- **`matte[.n]`**: `image` in, a mask out (`MatteNode`, one `MATTE_FS`
  pass at its input's own size, then two separable blur passes when
  `matte.feather` > 0). `matte.from` luma / alpha / chroma, `key`, `soft`,
  `invert`, `feather`, `hue`, `sat`. A mask port binds the mask refitted
  by cover to the frame's size (`graph.mask_port`); the promotion and the
  cut fit the native mask themselves, so one mask lands in the same place
  on every consumer.
- **`cut[.n]`**: `image` and `mask` in, a picture out (`CutNode`, one
  `CUT_FS` pass into its own `<name>#cut`): where the mask passes the
  picture, elsewhere premultiplied transparent black scaled by
  `cut.amount`; `cut.invert`. No mask, or one making nothing: the picture
  through, byte-identical, no pass.
- **`segment[.n]`**: `image` in; pins `segment.fg`, `.bg` (pictures, each a
  `CUT_FS` pass at the frame's size, `SegmentPin`) and `.mask` (the matte
  at the model's size). `segment.mode` person (a worker, below) / motion
  (`MOTION_FS` and `LEARN_FS` over a half-float background pair,
  `Renderer.motion_pair(name)`, on the frame thread) / subject (refused in
  words). The node shows the newest matte that has landed; before the
  first, off, on an error, with no worker or with its input reading
  nothing, `fg` is the input whole and `bg` and `mask` nothing, each said
  on the node.
- **The input path.** A person segment submits only when its input moved
  and its worker would take it: the channel's own CPU frame when the wire
  comes straight from a channel with pixels and a cover fit (the
  shortcut), else `MaskPasses.readback` (a trilinear downsample to the
  model's input size, one `read_into`, rows turned to top first).
- **Orientation.** A mask maker may say `rows_top_first(frame)` (a person
  segment's uploaded array does); `graph.mask_of(node, frame)` reads it and
  every pass that samples a mask (`CUT_FS`, `PROMOTE_FS`, the fit) flips by
  `u_flip`.
- **Laid over.** `_Build.laid_over` sees through `cut.image` and, when a
  segment's `fg` or `bg` is laid over, through `segment.image`, as through
  an effect: inserting a cut or a segment does not change the picture
  where nothing is cut.
- **The cut-through is a window's** (plan 39 T1): `render.draw_scene` takes
  the squared-alpha cut-through blend only when the window is see-through
  (`Renderer.bg_alpha < 1`), never for a laid-over scene's zero ground, so
  a translucent face over a bright under or backdrop is honest.

What the order guarantees, each held by tests in `tests/test_render.py`,
`tests/test_outputs.py`, `tests/test_ghost.py`, `tests/test_graph.py` and
`tests/test_golden_frames.py`:

- **Every golden frame is drawn byte for byte**: 789 frames (757 before plan 39; its four fixtures added 32, and eight backdrop frames were re-recorded for the honest blend, register row 448) — every
  corpus loadable patch (`tests/corpus/presets/`, the twenty-four the manifest names; nothing ships with the app since 2026-10-28) in every output state, hands absent and present, the
  other wirings, the fixture loadable patches (plan 30's three placements and
  plan 28's two wire fixtures and plan 34's five among them) and a recorded cloud — on the gate
  Mac's renderer ("Apple M3 Max"); elsewhere the test skips
  (`tests/test_golden_frames.py::test_every_golden_frame_is_drawn_byte_for_byte`).
- **The graph is built once per window count and wiring and reused** (a mute rebuilds nothing), its order
  puts dependencies first, and a pipeline no view takes this frame does
  not run (`tests/test_graph.py::test_the_graph_is_built_once_per_set_of_switches_and_reused`,
  `::test_order_puts_dependencies_first_and_ties_in_insertion_order`,
  `::test_a_pipeline_no_view_routes_to_this_frame_does_not_run`).
- **The faces' picture is in the scene texture**, so the echoes and the
  dream carry it; the frame's effects never reach the history. With no
  picture wired into `shape.faces` (or only the plain pattern) no face
  pass runs and the frame is bit-identical
  (`test_nothing_aimed_at_the_faces_is_the_old_frame_exactly`,
  `test_the_echoes_carry_the_faces_effects`, `tests/test_graph_faces.py`).
- **The history holds what it is wired to**: the scene by default —
  never the frame's effects or the dim — or the scene with the hands
  (`test_the_history_holds_what_it_is_wired_to_and_the_default_graph_wires_it_as_today`,
  `test_the_default_graphs_history_holds_what_todays_does_never_the_dim`).
- **The effects' clocks advance once a frame** however many chains run
  (`FxState.advance_to`; `test_both_chains_in_a_frame_run_the_clocks_once`).
- **An off effect costs nothing**: it is read through, no pass and no
  texture, and the run draws what the one-block chain drew
  (`tests/test_graph_effects.py::test_an_off_effect_is_read_through_and_runs_no_pass`,
  `::test_the_run_draws_what_the_one_block_chain_drew`); a held effect's
  texture is never its consumer's target
  (`::test_a_held_effect_read_through_the_pool_is_never_its_consumers_target`).
- **A placed effect folds only its edge**: after the hands the layer
  and not the scene, into output 2 that output alone, after the scene
  what the history captures; a placement the graph lacks is dormant,
  never in the chain
  (`tests/test_graph_placement.py::test_after_hands_folds_the_hands_layer_and_not_the_shape`,
  `::test_into_output_2_folds_one_output_only`,
  `::test_after_scene_feeds_the_history_the_folded_picture`,
  `::test_a_placement_the_graph_lacks_is_dormant_and_said_in_words`).
- **Two outputs with the same switches share one chain run**
  (`test_two_outputs_with_the_same_switches_run_the_chain_once`); one
  default output is byte for byte the single-window frame
  (`test_one_default_output_is_todays_frame_byte_for_byte`).
- **The dim is the last pass**: blending only, no texture; on an opaque
  ground it leaves alpha as it was, on overlay's see-through ground it
  scales alpha too. At 1 it does not run
  (`test_dim_at_one_is_the_old_frame_exactly`,
  `test_each_output_dims_by_master_times_its_own`).
- **A failure costs only its own part.** A raising face pass leaves
  `Renderer.face_error` and the frame as with no face effect; a raising
  hands pass leaves `Ghost.error` and every output still gets its dim; a
  raising pipeline leaves its views on their ground; a raising view
  records `View.error`; a raising presenter does not stop the frame; a
  hand or a cloud that raises inside the scene costs the scene nothing
  (`test_a_raising_hands_pass_costs_no_output_its_frame_or_its_dim`,
  `test_a_raising_pipeline_leaves_its_views_on_the_ground_and_the_rest_drawn`,
  `tests/test_hands_node.py::test_a_raising_hand_in_the_scene_costs_the_scene_nothing`,
  `tests/test_app_boundary.py::test_a_raising_presenter_does_not_stop_the_frame`).
- **The render target is bound explicitly.** The frame uses half a dozen
  offscreen framebuffers; one left bound would make every later frame draw
  into it while the window swapped a stale picture. `draw_outputs` binds
  `views[0].target` again on every exit, and `Lookback.capture` does the
  same for its own target.
- **The presenter** (`outputs.Presenter`, one per later output, on its
  own window's context) wraps the renderer's textures by GL name
  (`ctx.external_texture`) — a share group shares textures, never
  framebuffers or vertex arrays — and draws the ground, the frame, the
  hands, the readout and the dim. The `glFlush` before it is what makes
  the second context see this frame's texture
  (`tests/test_app_boundary.py::test_the_rendering_context_is_flushed_before_a_presenter`).
- **The render stack reads, never writes.** No node or graph method is
  named `apply`, `modulate`, `snapshot` or `set_value`, and `graph.py`
  imports no registry, routing, library, loadable patch, undo, control or device
  module (`tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`).
- **A 3D shape's W angles are dropped where it is drawn, and nowhere
  else.** `Renderer.draw_scene` draws through `geometry.shape_world` (the
  rules `geometry.shape_view` projects by), which takes `geometry.view_angles(shape, ang)`: the view's own angles
  for a 4D shape, the 3D angles with every W angle at 0 for a 3D one
  (§5, Shapes). It is a pure function read in the scene pass. It writes
  no param and not `ViewState.ang`; the integrator (step 13) and every
  `rot.*` param are as they were, and a rate or a phase route on a W
  plane still lands on that plane's param — it just turns nothing a 3D
  shape has (`tests/test_shapes4d.py::test_the_w_planes_leave_a_3d_shape_alone`,
  `::test_a_4d_shape_takes_the_views_angles_as_they_are`,
  `::test_the_renderer_draws_a_3d_shape_without_its_w_turns`).
- **The 3D switch's hold lives on the view, written by the integrator.**
  `view.three_d` is a plain toggle; on the frame it changes,
  `ViewState.integrate` (step 13, already the one direct writer of
  `ang`) folds the 4D pose into `ViewState.body` and sets
  `ViewState.held`, and while held it stops the W planes. The renderer
  reads `held` and `body` and writes neither, so a frame drawn between a
  toggle and step 13 shows the pose as it was
  (`tests/test_shapes4d.py::test_the_3d_switch_never_jumps_on_or_off`).
- **The FACES page's swatches cost nothing unless the page is open.**
  While a page calls `Renderer.want_swatches` (and for `SWATCH_HOLD` = 30
  frames after), `draw_outputs` draws one pattern's swatch a frame, round
  robin, inside its `try/finally`; a failure is `swatch_error` and never
  costs the frame, and the frame's pixels are the same with or without
  them
  (`tests/test_ui_patterns.py::test_swatches_draw_only_while_the_page_asks_and_leave_the_frame_as_it_was`).
- **The bands reach the patterns as a render input, not a param.**
  `app.frame` sets `renderer.bands` from `app._bands(audio)` (the lanes
  as a route reads them, out / CEIL; `()` with the analyzer off; it never
  raises) after the integrator and before the draw, as step 5 hands over
  the dim. The face shaders read it as `u_levels` / `u_nlevels`; only
  METER and PULSE do
  (`tests/test_patterns.py::test_only_meter_and_pulse_read_the_bands_and_they_show_them`).
  No test pins where in the frame the hand-over happens;
  `test_the_frame_runs_in_the_documented_order` logs no step for it.
- **Opaque unless overlay.** With `[output] overlay = false` (the default)
  the render window has no transparent framebuffer and `output.overlay`
  refuses to switch on, whatever road asks. Every later output is opaque.
  Output 1's swap waits for the screen (interval 1), later outputs' do not;
  whether that paces two screens without tearing is hand check 107.

---

## 3. The control model

This is the canonical statement. Where another document disagrees, this
section is wrong only if the code is: check the cited symbol or test,
then fix whichever is lying.

Scene-setters write a param's **base**; exactly one performer row per
param writes an **offset** through `Router.modulate`, or, for a `turn` row
(plan 51 O2), the base itself on a kept undo step; `Registry.apply()`
lands `base + offset` on the live object once a frame; the render stack
only reads.

### 3.1 The registry

Every settable thing is a `Param` with a stable id (`view.bright`,
`rot.rate.XY`, `band.2.atk`, `fx.acid.speed`, `lfo.1.depth`, `macro.3`), a
`params.Kind` — `CONTINUOUS`, `ENUM`, `TOGGLE`, `TRIGGER`, `TEXT` — and a
`get` / `put` pair onto the live object it is a view of.
`params.build_registry` declares the whole surface. Flags:

| Flag | Means |
|---|---|
| `persist` | belongs in a snapshot. Its group puts it in the **performance** part (a loadable patch's `values`) or the **meta controller** part (a show's `session`): `params.PATCH_GROUPS` / `SHARED_META_GROUPS`, `part_of` — by the contract "a preset is a complete look; the rig is what is plugged in" (plan 43; the eye is performance since C2). On by default; never for triggers. The rotation phases (`rot.phase.*`) are `persist=False` — the turn moves every frame, so it is no base — yet a loadable patch saves them as its `pose` (`params.POSE_IDS`, `ViewState.pose`) and a load sets the turn |
| `modulatable` | a performer may drive it. Off for meta settings (`output.monitor`, `.fullscreen`, `.overlay`, `.passthrough`, `.dim`, every `hands.*`), UI state, aliases, `tempo.tap`, the dream params whose change rebuilds something (`dream.gap`, `dream.res`, `dream.layer`), the per-output switches, and `ghost.style` / `.mirror` / `.guide` / `.tethers`. A route onto one is dormant; a hand Learn onto one is refused in words (`Learn.learn_source`), and a loadable patch's route onto one is dropped at load with a note (`LoadedPatch.load_doc`) |
| `alias` | a view onto another param (`band.sel.*` follows the selected band); never persists or modulates. `Registry.real` resolves it |

A continuous param has a **taper** (`tapers.py`): an integer position ↔
value map, exact on every detent
(`tests/test_control.py::test_taper_round_trip`). User setters snap to
detents; the modulation path does not, and a tapered position is
continuous between detents (`Param._taper_pos`), so a sub-detent base
survives under a performer. **A depth is measured along the taper**: a
route's depth, a `set` row's value and a macro base subscriber's ends are
normalised units, and the taper sits between those and the param's real
units — so a taper change changes what every saved depth onto that param
means, and comes with its migration in the same PR (wave 0 T1: the
effects' `speed` and `amount` params, `params.retaper_depths` at load,
`tools/retaper_routes.py` for the library; bases are real units and need
none).

**Base vs effective.** `p.value` reads the object (the *effective*
value); `p.base`, `p.norm`, `p.position()` read the setting. They are the
same until the first `modulate()` adopts the object's value as the base;
from then on every setter writes the base and `apply()` writes
`base + Σ offsets`. The first frame no source calls, `apply()` writes the
base back and forgets it
(`tests/test_modulation.py::test_modulation_rides_on_the_base_and_lets_go_cleanly`).

**`Registry.apply()`** runs once a frame over every modulated param, in
registry order. Per param (`Param.apply`): fold any direct object write
since last frame into the base; `target = base + offsets`; clamp or wrap;
continuous → through the taper; enum → nearest index with a dead-band
(`params.MOD_DEADBAND`); toggle → hysteresis about `MOD_ON` / `MOD_OFF`;
trigger → fire once on the rising edge
(`tests/test_modulation.py::test_discrete_targets_move_with_hysteresis`).

An enum with a `has` predicate (the bank's `preset.select`) is stepped by
`Param._walk`: a step or cycle skips choices that hold nothing.

### 3.2 Who may write a parameter

| Class | Writes | Who | Held by |
|---|---|---|---|
| **Scene-setter** | the **base** | panel widgets (`Param.set*`); key / pad / hat rows (`routing.act` via `Router.keys`, `Router.pad`); MIDI rows of the layer that is up and the invariant rows (`midi.py`, `Bindings.dispatch`), including the knob **glide** (`MidiIO._aim` / `_glide`: `Param.set` between detents, then the row's `set_norm`); a macro's base subscribers (`Router.follow_macros`); `Registry.restore` (module presets, shows); a loadable patch load (`LoadedPatch.load`); the relative writers — mouse, sticks, triggers, ↑ / ↓ — via `Param.nudge` / `scale`, which read the base; home (`Project.home`); undo and redo (`Undo._restore`) | every setter ends in `Param.set`, which writes the base while modulated (`tests/test_modulation.py::test_setting_a_modulated_param_moves_its_base`, `tests/test_app_relative.py`) |
| **Performer** | an **offset**; a `turn` row, the **base** (`Router._turn`, `Param.set`, plan 51 O2: gated and from a whole-circle lane, one undo step per closure through `Undo.keep_open`) | `Router.modulate` → `Param.modulate`, the only call site | `tests/test_routing_boundary.py::test_only_router_modulate_calls_param_modulate` (an AST walk). Adapters only `feed` |
| **Object writer** | the live object, bypassing `Param` | `ViewState.integrate` (`ang`), `camera.reset`, `control.Control`'s resets and their undo, `hands.core.mirror` on the non-modulatable `hands.*` | `Param.apply` folds the delta into the base next frame |

Consequences:

- **Scene-setters don't compete with performers.** A knob turned on a
  hand-owned param moves the **return value**, which shows when the hand
  lets go; it never prompts and is never blocked
  (`tests/test_routing.py::test_audit_3_a_knob_moves_the_return_value_under_a_hand`).
- **Two discrete controls of a pad can be one axis** (plan 56): the address
  declares it, `pair:<+ pole>/<− pole>`, and `Router.pad` feeds its one lane,
  resting at 0.5, into the shared sources, so a route reads it as it reads a stick.
  A `step` row on one acts as the two rows it stands for and stays the meta
  controller's (`tests/test_paired_axes.py`). A person's row on a pair whose pole is
  mapped asks first (`learn.propose_row`, `learn.settle_pair`, row 754;
  `tests/test_pair_consent.py`).
- **The base chase is the one road from a performer into a base** (plan 52):
  while `deck.chase` is held, `Param.apply` writes what it landed into the
  base, on this deck's look params only, and `Param._trim` keeps the offset
  from counting twice. A scene-setter's act by the hand that holds it, and
  one undo step per hold; a performer alone still writes only offsets
  (`tests/test_base_chase.py`).
- **A relative writer reads the base**, never the effective value, or the
  whole offset would fold into the base on every drag frame
  (`tests/test_app_relative.py::test_orbit_under_a_performer_moves_the_base_by_its_delta`).
- **A glide is the MIDI adapter's own, and anyone else's write ends it.**
  One glide per param (`MidiIO._slews`). Each poll the adapter reads the
  param's norm back; further than `SLEW_TOL` from its own last write means
  someone else set it, and the glide is dropped. A param that moves on its
  own is written at once (`MidiIO._restless`). Only `abs` rows on a
  continuous, non-integer param glide. `desk.slew` at 0, the port going
  away or `MidiIO.close()` lands every glide. `routing.SLEW_MAX_S` is held
  under `undo.SETTLE_S`, so one knob turn is one undo step
  (`tests/test_midi.py::test_someone_elses_write_stops_a_glide`,
  `tests/test_undo.py::test_the_slew_can_never_outlast_the_settle_time`).
- **MIDI feedback.** A ring shows the base — while a glide runs, the
  glide's target (`MidiIO._ring_norm`) — and never chases a performer, or
  the knob could never catch. An LED on a toggle or an enum `set` row
  reads the effective value (`MidiIO._lit`): it is a state light
  (`tests/test_midi.py::test_ring_shows_the_base_and_never_chases_a_performer`).
- **Triggers.** `lfo.trigger` and every `lfo.N.reset` are ownable (a
  pinch can drop the LFOs on the one). `tempo.tap` is not: a band on tap
  tempo would tap on every transient
  (`tests/test_tempo.py::test_a_performer_on_tap_tempo_is_dormant_but_one_on_the_lfo_trigger_fires`).
- **A loadable patch's route may perform any modulatable param but a meta
  controller's** (`params.is_meta_id`; `routing.meta_refusal`, register
  rows 743, 746): no row of a loadable patch drives one, and a loadable patch never sets its base.
  The line is `routing.is_meta_row`, so the meta controller's own rows stay.
- **Every param is in exactly one layer** (`params.META_PARTS`): "performance"
  is the patch, "shared_meta" and `PER_DECK_META` the meta controller. "shared_meta" is one
  object on every deck; `PER_DECK_META` (`preset.*`, `deck.chase`, `totem.*`,
  `poi.*`) closes over one deck and stays each deck's own
  (`tests/test_layer_boundary.py`, rows 746, 747). The same test holds **the
  wall:** a patch module reaches a module of the meta controller's only through
  its `SURFACE`, the named list of what crosses today and why.
- **The pattern inputs add no writer.** `pattern.mod.0–7` are ordinary
  modulatable params with a named meaning each (§5, Face patterns). The
  FACES page writes their bases like any widget, and its "+ source"
  offer adds a route through the table's edit door
  (`ui_routing.add_route`), as ROUTING does. The patterns' clock
  (`u_ptime`, SPEED integrated) and the bands (`u_levels`) are the
  renderer's own state, never a param.
- **The output switches add no writer.** `output.N.scene` / `.hands` /
  `.through` / `.dim` (`overlay.register_switches`, one set per opened
  output) are meta settings — not persisted, not modulatable — whose base
  is the slot's `outputs.Switches`; the renderer only reads it
  (`tests/test_overlay.py::test_the_output_switches_are_meta_settings`).
- **Undo is a scene-setter that watches the other scene-setters.** It has
  no write hook: `Param` and `Registry` do not know it exists. It compares
  bases, so a performer moving makes no step; floats compare within
  `undo.REL_TOL` / `ABS_TOL`, so a performer's round-off in the last bits
  makes none either (`tests/test_undo.py::test_a_performer_moving_makes_no_step`).
  A restore puts back **only what differs** — bases through
  `Registry.restore`, the table's parts through `Bindings.set_routes`,
  `set_desk(rows, load=False)`, `set_macros` — then `Router.sync_macros`,
  so `follow_macros` does not re-land the subscribers over it. It writes
  no offset, no object and no file
  (`tests/test_undo.py::test_undo_of_a_slider_does_not_rerun_a_load`).
- **`Router.modulate` never checks ownership.** The referee lives in the
  table's edit doors and loaders (§3.5); a table mutated directly could
  still stack two performers on one target.

### 3.3 Sources and rows

A `routing.Binding` is one row: `source` (`scheme:address`), `target` (a
param id), `op`, `value`, `enabled`, and for performers `scale` (a
**meta controller** param only, such as `master.gain`), `when` (a gate), `rest`;
MIDI rows add `pickup`, `feedback`, `on`, `off`, `ring` and `layer` —
absent for an **invariant** control (the meta controller's, one meaning on both
layers), `"global"` (the SHIFT layer) or `"preset"` (the loaded patch's
desk).

| Scheme | Address | Fed by | Reaches the param as |
|---|---|---|---|
| `key:` | a GLFW key name, with modifiers `SHIFT+` / `SUPER+` / `CONTROL+` (`routing.MODIFIERS`) | `Router.keys`, reading `app.Keys` | a discrete op on the base |
| `pad:` / `hat:` | a `gamepad` button / hat name (`gamepad.BUTTONS`, `HATS`; plan 42's `TOUCH`, `LP` / `RP`, `LFN` / `RFN` on a pad that has them, `gamepad.EXTRA_BUTTONS`; a DualSense's buttons by the Xbox names, `pads.models.CANON`). A pad other than the first listed writes its role after `@`: `pad@p2:A` (plan 27 B6) | `Router.pad(…, role)` (times `hold`, lets `momentary` go on the release; each pad fires only its own rows) | a discrete op on the base |
| `axis:` | `LX` `LY` `RX` `RY` (sticks, rest 0.5) / `LT` `RT` (triggers, rest 0) — `gamepad.AXES`; the sticks as dials, `L.N` … `L.NW` / `R.N` … `R.NW` (rest 0) — `gamepad.DIAL_LANES`, a prototype; a second pad's are `axis@p2:LX`, its own Router key | the pad device: `Router.pad` → `Router.feed("axis")` (`"axis@p2"`), from `Pad.lanes`; names, labels and rests from `gamepad.publish` | performer; a stick or trigger with a route leaves its default camera job (`gamepad.steer`, the first pad's only), a dial lane's route its whole stick (`gamepad.claims`) |
| `cc:` / `note:` / `pitch:` | `channel:number` (`pitch:` channel only; `*` any channel). A desk other than the one that owns the unqualified rows writes its role after `@`: `cc@launch:0:21` (`routing.QUALIFIER`, `Binding.device`; any scheme takes the qualifier since plan 27 B6) | each MIDI desk: `MidiIO._handle` → `Bindings.dispatch(…, role)` → `MidiIO._apply` | `abs` (soft pickup), `rel`, `rel64`, `step`, `toggle`, `set`, `momentary`, `fire`, `hold` — all base |
| `lane:` | analyzer band index | `Analyzer.lanes / CEIL` inside `Router.modulate`; names and rests from `AudioEngine.publish` | **performer** |
| `touch:` / `motion:` (plan 42) | `x` `y` `down` `x2` `y2` `down2` `pinch` `twist` `tap` / `roll` `pitch` `yaw` `spin.roll` `spin.pitch` `spin.yaw` `shake` `energy` (`pads.gesture`); a second pad's `touch@p2:x` | the pad device's `act` (`PadDevice._feed_extras`, after its rows) from `Pad.touch_lanes` / `motion_lanes` — only an entry that may read a Sony pad (`PadDevice.schemes_for`); not live while no finger is down or the pad has no sensors; `down` / `down2` gates, `tap` / `shake` triggers (`Router.lane_kinds`) | performer |
| `hand:` | a name: `left.x` … `right.yaw` as `[hands] dofs` spells them, `left.present`, `left.pinch.index` … `right.pinch.pinky`, the dance sources and the grab (plan 24), `left.room.roll` … `right.room.yaw` (plan 51); a number still reads as that lane | the hands device's feed (`hands.device.HandsDevice` → `HandsIO.poll`) → `Router.feed("hand")`; the name → lane map in `router.names["hand"]` (`hands.core.Layout`) | performer; a pinch or a grab may also gate |
| `hands:` | `gap`, `twist` (both hands) | the same call → `Router.feed("hands")` | performer |
| `ext:` | DAW lane 0 … `in_lanes` − 1 (16 by default) | the bridge device's feed: `Bridge.receive` → `Router.feed("ext")`, `Bridge.publish` (labels "ext 0" …, rests 0) | performer |
| `lfo:` | an LFO's id − 1 (`lfo:0` is LFO 1; four by default, up to 16 ids; a removed id's lane reads NaN, dormant) | `LFOs.publish`, then each LFO's node in the pass (`Bank.step_one`, plan 28, plan 31) | performer |
| `env:` | an envelope's id − 1 (`env:0` is env 1; 1–5 always there, extras to 16) | `Envelopes.publish`, then each envelope's node in the pass; rests 0 | performer |
| `seq:` | a sequencer lane, 0–4 (`seq:0` is lane 1, params `seq.1.*`) | `Router._step_sequencer` → `Sequencer.publish`: the step's velocity on the frame the lane fires, else 0; a trigger kind (`Router.lane_kinds`) | performer; on a trigger param, its rising edge fires it |
| `mod:` | a modifier's number (`mod:2` is `mod.2`; plan 28 N1) | the modifier's node in the pass (`Router._step_modifier` → `feeds["mod"]`); labels `<n> <kind>`, rests 0; NaN while its input is not live; a `threshold`'s lane is a trigger and a gate (`Router.lane_kinds`) | performer |
| `<role>:` (a new device's) | an OSC address without its `/`: `phone:x`, `phone:1/fader3` | the OSC device's feed → `Router.feed("<role>")`, names, labels, rests; its `hits` as rows under the same scheme in its `act` | performer (axes); a hit row: `fire`, `toggle`, `step`, `set`, `abs`, `momentary` on the base (`osc.fire`) |

A **sink row** runs the other way: its source is `param:<id>` (the
param's effective norm) or `lane:<i>` / `lane:*`, its target a sink
port `<role>:<channel>` (`bridge:3`), its op `send` (`routing.SINK_OP`).
It is a meta row, never a performer and never in a loadable patch; the sink
device reads it after `reg.apply` (`routing.sink_values`). A pad with
outputs (plan 42) is a sink too: `<role>:0`–`8` (`devices.SINKS`: light
bar hue, level, whiteness, the two rumble motors, each trigger's
resistance, the player lights, the mic light), one `Effects` a frame over
the pad's identity (`devices.pad_effects`), written by the hid reader only
when it changed. A point cloud
is no scheme at all: `DeviceRegistry.clouds` holds it as `cloud:<role>`,
off the Router.

**There is no fixed list of schemes.** A scheme is continuous unless it
is one the table dispatches as rows (`routing.is_continuous`: not in
`ROW_SCHEMES = ("key", "pad", "hat", "cc", "note", "pitch")`), so a row
on a device this rig lacks is a dormant performer, never dropped; a row
on a continuous scheme carries only `routing.MOD_OPS = ("push",
"position")` (`Bindings._check` raises otherwise) unless the scheme also
takes rows (an OSC role with hits: `Bindings.row_schemes`, which the
registry extends). *Which* schemes this rig has, and in what order the
ROUTING page offers them, is the registry's, handed to the router as an
argument (`Router.use(registry)`, `Router.schemes()` =
`DeviceRegistry.continuous_schemes()`: `lane`, `lfo`, `env`, `seq` (`devices.BUILTIN_SCHEMES`, `routing.BUILTIN_LANES` for a bare router), then each listed
device's `feeds` in list order)
(`tests/test_device_inputs.py::test_schemes_wants_and_row_schemes_come_from_the_registry`).

**A key press fires only its own chord.** Rows on one key are settled
together: a row fires when its modifiers equal the held modifiers that
some row on that key names. So `key:B` taps and `key:SHIFT+B` triggers,
and ⌘⇧Z fires only `key:SHIFT+SUPER+Z`
(`tests/test_routing.py::test_a_chord_fires_only_its_own_row`). While
imgui is typing, `Keys` ignores the control window's keys.

**`hold`** is a MIDI note row's op: the target fires once the button has
been down `midi.HOLD_S`, while still held; a tap fires nothing.
`routing.act` ignores it; the timing is the adapter's (`MidiIO._fire_holds`).
All enabled `hold` rows on one target are one control, and on the fire
they and every LED the fire lit blink for `midi.BLINK_S`
(`tests/test_midi.py::test_the_bar_is_one_control`); the factory map has
no `hold` row since 2026-10-09, but any buttons can be given one. A `set`
row on an enum that declares `held` (`Param.held`) is a press and a hold
at once: the bank pads' `preset.select` rows load on the press and, held
`midi.HOLD_S` on an empty slot, save into it (`Project.save_into`; one row
per pad, the new pad blinks).

A named hand address resolves only through the map the hands adapter
published; a name the meta controller lacks is dormant, never another lane, so a meta controller
that reorders `[hands] dofs` keeps every loadable patch on its axes
(`tests/test_hand_names.py`).

### 3.4 The one path

Every continuous source reaches a parameter through one pass,
`Router.modulate`, once a frame, over the enabled performer rows
(`Bindings.mods`) in **the patch's order** (plan 28: a param's rows run
at its node, after every node it reads — §2's dependency order; ties in
table order). Per row:

1. **Find the lane** (`Router.lane`): a number is the index; a name is
   looked up in `router.names[scheme]`, cached against the map's
   identity. The vector is the analyzer's lanes for `lane:`, else
   `feeds[scheme]`. No vector, an index out of range, or a `NaN` reading
   (a hand out of the box) → the row does nothing this frame.
2. **Gate.** If the row has a `when`, the gate's source must be fed and
   read ≥ 0.5; a gate whose source is not live holds the row shut
   (`Router.gated`).
3. **Depth** `= value × scale × Π (from + m · (to − from))`: `scale` is a
   shared meta param's effective value; each **depth subscriber** of a macro
   naming this row multiplies by its range at `m`, the macro's effective
   value (`Bindings.depth_subs`). A missing scale or macro makes the row
   dormant.
4. **The op.**
   - **push** — `offset = depth · (u − rest)`: added to the base, centred
     where the source rests (`rest`, or the source's published rest via
     `Router.rest_of`: hands their axis rest, LFOs 0.5, the analyzer 0).
     Idle adds nothing (`tests/test_routing.py::test_push_is_centred_where_the_source_rests`).
   - **position** — `offset = clamp(depth · u, 0, 1) − base_norm`: the
     source *is* the fader; when it lets go the base returns
     (`tests/test_routing.py::test_position_op_is_the_position_across_the_whole_throw`).
5. `p.modulate(offset)` — the one call in the package. Range, wrap,
   hysteresis and the return to base are `Param.apply`'s.

A row whose source stops being fed (`Router.feed(scheme, None)`) or
whose gate shuts stops calling `modulate`, and `apply()` writes the base
back that frame.

**What a new hand Learn writes** (`Learn._row`; rows already in a table
or file are never rewritten):

| The target | A centred axis | A one-sided axis (height) | A band lane | An LFO |
|---|---|---|---|---|
| continuous, range centred on zero (`learn.centred_target`) | `push`, depth D | `push`, depth D | `push`, `learn.LANE_DEPTH` | `push`, depth D |
| any other continuous param | `push`, depth D | `position`, depth 1 | `push`, `learn.LANE_DEPTH` | `push`, depth D |
| enum, toggle, trigger, whole-number | `position`, depth 1 | `position`, depth 1 | `position`, depth 1 | `position`, depth 1 |

D is the meta controller's `hands.learn_depth` (`learn.PUSH_DEPTH` when a caller
names none); a learned push has `rest = None`. Every row the table makes
carries `motion = motion.DEFAULT_ROUTE_FEEL` (the `smooth` spring), the
envelope's row excepted (it keeps auto, `None`).

**Adding a device** is a class and one line in `devices.kinds()`, never
an edit to `app.py` (`osc.py` is the proof:
`tests/test_osc.py::test_only_osc_py_and_the_kind_table_name_the_osc_device`).
The class subclasses `devices.Base` and implements only what it has:
`open()` (import its library here, so an `off` entry never imports it;
raise and the registry retries on its schedule), `poll(dt, now)` (read
the hardware; a device whose hardware went away reports `lost` and looks
for it again itself), `act(router)` for discrete controls as rows
through the table, `feed(sources)` for continuous ones — the shared
`routing_sources.Sources` (plan 44 D2) —
`sources.feed("<role>", vector)` (floats in `[0, 1]`, `NaN` for a lane
out of view, `None` when the device is gone) and `sources.labels`,
`sources.rests`, optionally `sources.gates` and `sources.names` (a new dict
whenever its layout changes) — `learn(learn)` to complete a "Learn
<role>", `sinks` and `send(reg, analyzer)` for an output, `close()`, a
`status` and `last` for its SYSTEM line, and `sources` as `Port`s. Its
role is its scheme (`feeds = schemes = (role,)`; `publishes` says so
before it is made); a row on the role performs with no list to join.
The entry's keys arrive as `self.entry` (config checks only `role`,
`kind`, `enabled`). It never writes a `Param` from `feed`, and nothing
in the core imports it.

### 3.5 One performer per parameter

A **performer** is an enabled row on a continuous scheme with a performer
op (`Binding.is_performer`). A target has at most one:

- `Bindings.owner(pid)` answers who.
- `Bindings.add` and `bind` raise `Owned(existing, new)` when the target
  has a different performer; `Bindings.enable` runs the same check.
- `Bindings.replace_owner(new, *, target=None)` is the **one door** onto
  a taken target. Every *Replace* in the app is that call
  (`ui_routing`, `Learn._place`).
- Every load runs `routing.referee`: first performer per target wins,
  the rest go to `table.dropped` with a reason (`Bindings.from_json`,
  `Bindings.set_routes`).
- Gates do not exempt a row: two rows on one target with different
  pinches are two performers.

Tests: `tests/test_routing.py` from `test_a_target_has_one_performer`
through `test_a_loadable_load_lists_what_it_dropped`, and
`test_every_factory_preset_names_real_params_with_one_owner`.

**Learn.** The host owns one `learn.Learn`, built over the live table
whatever devices are listed, and hands it the device registry
(`Learn.devices`). The right-click menu arms a param with what it waits
for (`Learn.arm(pid, want)`); what can be armed is `Learn.wants()`:
`"desk"` (the on-screen desk completes it with no MIDI device at all),
then each listed device's `wants` in list order — `"pad"`,
`"hand:left"`, `"hand:right"`, and a new device's role (`"phone"`) —
off devices included; with no registry, `learn.BARE_WANTS`.
`Learn.accepts(source)` is the one question every completer asks; a
desk want completes from any MIDI desk, and the row names which. The
completers:

- **A hand** — `HandsIO._learn` → `Learn.learn_source`: the axis that
  moved, by name, with a pinch held as its gate. A non-modulatable target
  is refused in words. If another performer owns the target the pair is
  parked in `Learn.pending` for the Replace / Keep prompt and nothing is
  written. A landed learn takes the axis's other rows first: one axis,
  one param (`tests/test_learn.py::test_a_learned_axis_drives_one_param`).
- **A desk control** — `Learn.learn_control(source, profile)`, the one
  road onto the desk, called by `MidiIO._learned` with the message and by
  `ui_desk.click` with the control clicked. It binds a **patch-layer**
  row (`Bindings.bind(b, write=False)`), replacing whatever patch-layer
  row was on that control, pushes one undo step and bumps
  `redraw_serial`. On an invariant control or with the global layer up it
  is refused (`learn.blocked`) and **stays armed**. In the adapter an
  invariant control is never a candidate: its message is dispatched as
  usual through an armed learn
  (`tests/test_learn.py::test_learn_refuses_the_global_layer_and_invariant_controls`,
  `tests/test_midi.py::test_an_invariant_control_works_through_a_desk_learn`).
  A desk learn never prompts: a desk row is a scene-setter.
- **Click a control, then a param.** With nothing armed, a click on the
  on-screen desk is `Learn.pick(source)`; the next click on a param's
  widget is `Learn.map_picked(pid, profile)` = `arm(pid, "desk")` +
  `learn_control` — the same road
  (`tests/test_learn.py::test_pick_then_param_maps_through_the_learn`).
- **A pad button, or an OSC hit** — `gamepad.learn_from` (or
  `OscDevice.learn`) → `Learn.learn_pad_button`: a meta row in
  `bindings.json`, written at once; a stick, a trigger or an OSC axis →
  `Learn.learn_source`, a route in the loaded patch.
- **A sink port** — not armed at all: the menu's **Learn sink ▸** pick
  is `Learn.learn_sink(pid, port)`, a meta controller sink row written to
  `bindings.json` at once, never a performer and never a prompt
  (`tests/test_sinks.py::test_learn_sink_on_a_param_lands_a_meta_row_with_no_question`).

Every desk, hand and stick learn lands in the **loaded patch**: the table changes, the
loadable patch's dirty dot lights (`LoadedPatch.signature`), and no file is written
until a save. **Unbind** is `Learn.unbind(ids, *, desk=True,
routes=True)`: the loaded patch's desk rows and every route on the param
and its real param, as one undo step; a meta row is never removed.
`learn.bound(table, ids)` is what both Unbind and the menu's lines ask
(`tests/test_learn.py::test_unbind_removes_the_loadables_desk_rows_and_every_route`).

**The Replace / Keep prompt.** `ui_routing.modal` is drawn first in
`Panel.draw`, on every page, reading whichever question is up (a held
learn, or a ROUTING-page add / enable / retarget that raised `Owned`).
*Replace* → `replace_owner`; *Keep* → the table is untouched. While a
question is up, the hands learn nothing more
(`tests/test_ui_routing.py::test_the_replace_prompt_swaps_the_owner_or_leaves_the_table`).

### 3.6 Chaining, not stacking

Layers come from the graph, never from two rows on one param. Every LFO
knob (`lfo.N.shape/rate/sync/depth/phase`) and every macro (`macro.1–8`)
is an ordinary, ownable, persistent param:

```text
hand:right.y ──position──▶ lfo.1.depth     lfo:0 ──push──▶ view.bright
lane:0 ──push──▶ macro.2     hand:left.y ──position──▶ fx.mix  × macro.2's depth subscriber
```

A macro acts only through its **subscribers** (`routing.Macro`, `Sub`;
`Bindings.macros`, `set_macros`):

- a **base** subscriber `{"base": id, "from": a, "to": b}` sets that
  param's base to `a + m · (b − a)` whenever the macro's *base* moves
  (`Router.follow_macros`, frame step 3). It names a persisted,
  non-alias **performance** param; any other is dropped with a note
  (`routing.base_refusal`;
  `tests/test_macros.py::test_a_base_subscriber_on_a_meta_param_is_dropped_with_a_note`).
- a **depth** subscriber `{"depth": {"source", "target"}, "from", "to"}`
  multiplies that route's depth (§3.4 step 3).

So a performer that owns a macro moves only its depth subscribers; the
base subscribers follow the knob, the panel or a restore
(`tests/test_macros.py::test_a_performer_on_a_macro_moves_only_its_depth_subscribers`).
Two macros on one param: the later id wins. The subscribers and the
macros' values belong to the loaded patch; `bindings.json` never holds
them. Since plan 28 the chain lands **the same frame**: an LFO owning
another's depth, a macro scaling a push and a modulated `scale` are read
after they land (§2).

**Modifiers** (plan 28 N1; `modifiers.py`, `Bindings.modifiers`) are the
other way to chain: a value node between sources and a route —
`curve`, `scale`, `smooth`, `combine` (two inputs: the explicit way to
combine two performers, since a param still has one), `threshold` (a
trigger lane, also a gate), `delay` (last frame's input; the one place
a loop may close). Each reads one or two lanes and publishes `mod:<n>`,
which a route sources like any lane, so the Router, Learn, the referee
and ROUTING need no other path. Its params `mod.<n>.<p>` are ordinary
patch params (group `mod`), ownable like an LFO's knobs. They
live in the loaded patch (`loadable.MODIFIERS_KEY`), never in
`bindings.json`; a desk template may carry them, and so may a patch
(§3.11, with the graph region they sit in). A modifier whose input
is not live is dormant: its lane reads NaN and a route on it lets go
(`tests/test_modifiers.py::test_a_modifier_publishes_a_lane_a_route_can_source`,
`::test_modifiers_live_in_the_loadable_and_never_in_bindings_json`).

### 3.7 Where a controller's value goes

| You move… | It becomes… | Writes |
|---|---|---|
| a panel widget | `Param.set_position` / `set` / `toggle` | base |
| a key with a row (`B`, `⇧B`, `F`, `M`, `1–6`, …) | `Router.keys` → `routing.act` | base |
| `R`, F1–F8, ⇧F1–F8 | key rows (`routing.LOOP_KEY_ROWS`): `camera.reset`, `preset.load.k` → `Project.load_slot`, `preset.save.k` → `Project.save_slot`. Only the first `params.F_KEYS` = 8 slots have keys | base (a trigger) |
| ⌘Z / Ctrl+Z, with ⇧ | key rows → `edit.undo` / `edit.redo` → `undo.undo()` / `undo.redo()`, unless the stack is latched (row 753) | the bases and table parts that differ |
| Home, or the APC40's OVERDUB | `preset.home` → `Project.home`: the show's `startup` loadable patch loads (the file's; nothing on the panel sets it since 2026-10-28) | a loadable patch load |
| ⌘R, ⌘[ / ⌘], Q, ↑ / ↓ | loop code (`app.LOOP_KEYS`): restart, the panel's page history (`ui.PageHistory`), quit, `_ride_depth` on `view.depth4` | ↑ / ↓: base, relative |
| mouse drag / wheel, a pad stick or trigger | `Mouse.poll`; the pad device's camera job (`gamepad.steer`, in `PadDevice.act`) → `nudge` / `scale` | base, relative |
| a pad button or hat | `Router.pad` → `routing.act` | base |
| a finger on a Sony pad's touchpad, a tilt or a shake (plan 42) | `touch:` / `motion:` → its performer row → `Router.modulate`; a `tap` or `shake` row onto a trigger param fires it on the rising edge | offset |
| an APC40 knob or fader | the row of the layer that is up, or the invariant row → `Param.set_norm` (a fader after soft pickup; a knob caught at the ring just sent, `apc40.RING_REBASES_KNOB`, hand check 31); smoothed by `desk.slew` | base |
| an APC40 button | the rows its press went to — the release goes there too | base |
| a second MIDI desk's knob or button | its own rows (`cc@<role>:…`), on its own layer (the patch layer: it has no SHIFT) | base |
| an OSC fader / an OSC button | `<role>:<name>` → its performer row → `Router.modulate` / its rows (`osc.fire`) | offset / base |
| SHIFT | the invariant row → `desk.shift`: flips the table's layer; every ring and LED redrawn, a control the layer does not map dark | the table's layer |
| the crossfader | invariant row → `output.dim`, the master dim (CC 0 black — hand check 55); a meta setting, 1 at every launch | base of a meta setting |
| a bank pad (clip rows 1, 4, 5) or a bank button | invariant `set` rows → `preset.select = k` → `Project.load_slot(k)` (`apc40.BANK_PADS`: 24 slots, `library.SLOTS`). Lights by `routing.led_level`: loaded, filled, empty | a loadable patch load |
| a hold on an empty bank pad | its invariant `preset.select` row, held → `Param.held` → `Project.save_into(k)`: a new loadable patch named from the loaded one (`library.next_name`), into that slot; a filled slot is never written | files, not params; no undo step |
| a row Learn put on `preset.list.next` / `prev` (no factory row since 2026-11-04, row 723) | → `Project.walk` → `Library.next` / `prev` on the presets: the PRESETS page's list (`Library.list`: every loadable patch by name, re-read each step so a new save is in it), wrapping. The APC40's QUANT (`preset.next`) walks the bank's filled slots instead (`Project.cycle`) | a loadable patch load |
| a macro's knob | its base → `Router.follow_macros` → each base subscriber's base | base |
| an analyzer band, a hand axis, a pinch, a DAW lane, an LFO | `lane:` / `hand:` / `ext:` / `lfo:` → its performer row → `Router.modulate` | offset (a pinch may instead gate a row) |
| right-click → Learn hand / Learn desk / click-then-map | `Learn` (§3.5) | the loaded patch's table |
| right-click → Learn pad | `gamepad.learn_from` → `Learn.learn_pad_button` (a button: the meta controller's `bindings.json`, written at once) or `Learn.learn_source` (a stick or trigger: a route in the loaded patch) | the table |
| right-click → Learn pad on a Sony pad (plan 42) | `gamepad.learn_from`: the touchpad click, the back and Fn buttons as button rows; a finger dragged along x or y, a pinch, a twist, a tap, a tilt from where the pad was held when the learn was armed, or a shake as a route (`gamepad._learn_extra`) | the table |
| right-click → Learn sink ▸ `<role>:<channel>` | `Learn.learn_sink`: a sink row; the sink device sends the param's effective value after `reg.apply` | `bindings.json` (no param) |
| a sink row onto a pad's port, `<role>:0`–`8` (plan 42) | `PadDevice.send` → `devices.pad_effects` → `Pad.send_effects` → the hid reader, written only when it changed | the pad's light bar, lights, rumble, triggers (no param) |
| right-click → Unbind | `Learn.unbind` | the loaded patch's table |
| a ROUTING-page edit | the table in place: the loaded patch, its dirty dot | the table |
| a modifier (ROUTING's MODIFIERS strip, or the GRAPH page) | its node in the pass → its `mod:<n>` lane → the route sourcing it → `Router.modulate` | offset; the modifier itself is the loaded patch's table |
| a cable dragged on the GRAPH page | `graphview.Edit` → the table's own calls (`Bindings.add` / `move_route` / `remove`, a Learn, a macro subscriber, a modifier input) or, for an image cable, a new `graph` section read back and landed (`GraphSection.land`) | the loaded patch's table or graph (a pad setter: `bindings.json`) |
| a loadable patch | `LoadedPatch.load`: every performance base in one `Library.restore`, then the modifiers (`Bindings.set_modifiers`, their params declared), `Bindings.set_routes`, `set_desk`, `set_macros`, the GRAPH page's `layout`, the base subscribers landed (`Router.follow_macros(force=True)`); shared meta params never | bases and the loadable patch's table |
| a module preset or show | `Library.restore` (a show: its session part) | base |
| **a picture node dropped on a picture cable**, or a cable's **insert ▸** (GRAPH, 2026-11-01: any kind, not only an effect) | `ui_graph.onto_plan` (what the drag lights is what the drop does) → `put_onto` → `Edit.place_node` (a free node, or one lifted with ⌘: out of its place, its chain closed over it, onto the cable by `graphview.INSERT_PORTS`; a composite or a switch asks its inlet first, a channel takes the cable over) or `insert_node` → `Edit.insert_node` (a new node made and spliced): a new `graph` section read back and landed | the loaded patch's graph, one undo step |
| a cable's **starters ▸ feedback**, or a picture node's **add feedback after** (GRAPH, wave 0 E1, 2026-11-02) | `ui_graph.add_starter("feedback", cable)` / `ui_graph.add_feedback_after` (the cable out of the node, `graphview.picture_feeds` off the spec's wires; several, a submenu) → `Edit.starter("feedback", cable)` → `graphview._feedback_starter`: a new composite (over) onto the cable by the insert table's splice (`_onto`), `composite → delay.image`, `delay → fade.image`, `fade → composite.under`, landed; then the fade on at level `FEEDBACK_LEVEL` (0.75) in the same step (`_set_after_landing`); the three laid left to right from the menu's point, or under the node's box (`ui_graph.node_below`; `Edit.placed`, `chain_layout`). From the picker, a scene feeding several picture ports is refused in words | the loaded patch's graph and the fade's values, one undo step |
| **spawn ▸** a patch, or a patch dropped on a cable (GRAPH, plan 40) | `ui_graph.spawn` → `patches.spawn` → the conflict sheet if any (`ui_routing.modal`) → `Edit.spawn` / `Edit.splice`: the section through `gs.land`, `bank.add`, `add_modifier`, `lib.restore`, `Bindings.add` / `replace_owner`, `bind(write=False)`, `set_macros`, the group (§3.11) | the loaded patch's graph, table, values and `groups`, one undo step; no file |
| **wire as saved**, and its take-over chip (GRAPH side pane, wave 3 P3) | `ui_graph.wire_as_saved` → `Edit.wire_as_saved`. The chip: `ui_graph.take_over_plan` → `Edit.take_over_of` → a `graphview.TakeOver` (its words by `graphview.port_said`), pressed through `ui_graph.take_over` → `Edit.wire_taking_over`. Both land through `Edit._saved_pins`. | One undo step; only the chip cuts; its source stays on the canvas, not re-wired. |
| **group N nodes** / **ungroup** (GRAPH's right-click), `+` / `−` on a group | `Edit.group` / `ungroup` / `set_open` | the loadable patch's `groups` only (nothing of the renderer), one undo step |

### 3.8 The binding file

The file is the meta table's (plan 44 D3): `routing.MetaTable` holds
the meta controller's rows, the file's doors (`load`, `to_json`, `write`, the
backup, the old migrations) and the meta controller's own state — the layer latch
per role (`desk.shift`), the slew, the pad's feel, the device registry's
facts (`Sources.follow` writes them there) — and each deck's
`routing.Bindings` holds those rows by reference beside its own (routes,
the patch layer, macros, modifiers), one list for the adapters, the
referee and `dispatch`; a meta row learned on one deck is every
deck's. One deck today.

`<home>/bindings.json`, schema `routing.SCHEMA`
(`hyperspace.bindings/3`), holds the **meta controller's controls** only: the
keys, the pad, OSC hit rows, the invariant and global-layer MIDI rows,
and the sink rows (plan 27; with `"sinks_seeded"`, the roles whose old
`send` list has been translated). Its top-level `"profile"` says which
MIDI profile its unqualified rows were written for; the desk listed with
that profile owns them (`DeviceRegistry.midi_roles`). Performer
rows, patch-layer rows, macros, modifiers and values are the loaded
loadable patch's and are never written there (`routing.is_meta_row`;
`tests/test_routing.py::test_the_live_table_writes_only_the_meta_controls`).
Learn pad (a pad button or an OSC hit) and Learn sink add meta rows,
and ROUTING's sinks section switches and removes sink rows, each writing
the file at once; the other meta rows are edited by hand. The
factory meta table is exported to `hyperspace/bindings.default.json`
(`python -m hyperspace.routing`;
`tests/test_routing.py::test_factory_files_match_the_code`).

On load (`Bindings.load`) an older file is migrated and new factory rows
are added only where nothing on the table overlaps their control
(`routing.remap_factory`, `Binding.overlaps`); anything changed is
written back once, after a copy of the old file (`routing.backup`, never
over an existing backup). **No backup, no rewrite**: if the copy fails,
the file is left as it was and `Bindings.unbacked` stops every later
write that meta controller. An unknown schema is never rewritten. A file that
still holds a loadable patch's part is left for the first-launch migration
(`preset.migrate_home`), which moves it into loadable patches. The details are
ENGINEERING's.

### 3.9 Tempo, the LFOs, the envelopes and the sequencer

`tempo.Clock` is one free-running clock; `tick(now)` once a frame makes
every call agree on the time. `tap()` sets the BPM and **never moves the
downbeat**; `lfo.trigger` (`⇧B`, the APC40's METRONOME) sets the downbeat
to now and restarts every LFO in a division mode at phase 0 together; Hz
LFOs are untouched. Tempo is meta controller state: a loadable patch never moves it
(`tests/test_lfo.py::test_a_tap_does_not_move_a_running_synced_lfo_but_the_trigger_does`).

`lfo.LFOs` is a modulator bank (`modbank.Bank`, plan 31): four LFOs by
default, up to 16, each added or removed by a stable id that never
compacts (with LFO 2 removed, LFO 3 is still `lfo:2`; the gap's lane is
NaN, so a route left on it is dormant). Membership is the loadable patch's
(`"lfos"`, written only when not `[1, 2, 3, 4]`) and undo's. Each has `shape`, `rate`, `sync` (Hz or a bar division),
`depth`, `phase`, `reset`. Output `u = 0.5 + 0.5 · depth · wave`, rest
0.5. Each LFO steps inside `Router.modulate`, at its own node of the
patch (`LFOs.step_one`, after `LFOs.begin` and `publish`; plan 28), so it
reads its knobs from its own fields **after** every performer on them has
landed this frame (§2); every LFO is a node, so each steps once a frame
whether or not a cable touches it
(`tests/test_lfo.py::test_an_lfo_owning_another_lfos_depth_changes_its_output_the_same_frame`).
A reset that arrives before its LFO's node this frame lands at phase 0
on that step; one that arrives after its LFO has stepped (`LFO.at`), or a
trigger after the step, lands at exactly phase 0 at the start of the
next step.

**Envelopes** (`envelope.py`, plan 31) are the second bank, `env:<n-1>`,
params `env.<n>.*`: AHDSR voices (`mode` gate · one-shot, the times log
1 ms – 8 s in seconds or beats, one `curve`, `retrig` legato · reset,
`amount`, `velocity`), resting at 0. They are event-driven: `fire(at=…)`
and `release(at=…)` queue an event stamped with its time, and the voice's
step walks the stage boundaries and the events up to the frame's t, so a
fire stamped between two frames renders exactly; a fire with no stamp
(the panel, `Registry.apply`) lands at the next step's t, at level 0
(the LFO rule). Envelopes 1–5 always exist — the sequencer's lanes fire
them — and extras come and go to 16. `fire` and `gate` feed the voice's
node, so a route onto `env.<n>.fire` starts the note this frame.

**The step sequencer** (`sequencer.py`) is five lanes of eight steps,
each step a toggle param `seq.<l>.<s>`, over a span of ½–4 bars. Its
position is the clock's, never integrated —
`s(t) = (clock.beat(t) + shift) · steps_per_beat` — so it cannot drift
from the synced LFOs. Each frame, after every bank's `begin` and before
the plan, it fires every step crossed since the last frame at that step's
exact clock time (tempo's `beat` inverted), odd steps `swing` late, into
the lane's envelope (`seq.<l>.env`, lane l → envelope l by default) with
a gate of `seq.gate` of a step, and pulses the lane's `seq:` trigger
lane. A stall fires only the current step; a backward nudge fires nothing
twice. **`Clock.trigger` bumps `clock.epoch`** and a new epoch fires step
0 that frame at the trigger time, so the global trigger puts the grid on
the one with the LFOs; `seq.trigger` restarts the grid alone. `seq.run`
gates firing only and is never saved; the pattern is the loadable patch's
(`tests/test_sequencer.py`, `tests/test_plan31_wiring.py`).

### 3.10 What the model does not promise

Behaviour the code has today that the model does not guard:

- `Router.modulate` checks no ownership at run time (§3.2).
- A loop's cut cable keeps its row enabled in the table: ROUTING's
  checkbox reads on while only the note says it is off (§2).
- A `hand:<i>` row still reads by index, so one saved by number re-points
  on a meta controller that reorders `dofs`; and the table compares sources as
  strings, so a depth subscriber written for `hand:7` does not scale a row
  on `hand:right.y`.
- A loadable patch saved after a module-preset load moved a param that a macro's
  base subscriber sets does not round-trip it: the reload lands the
  subscriber's value.
- Undo does not take back: a band added, removed or moved; a tap or a
  typed BPM (the `tempo` group is `undo.EXCLUDED_GROUPS`); the bank (a pad
  change is written to the show at once); a save, a rename or a delete
  (the trash is their net); an edit in
  the `undo.ABSORB_FRAMES` frames after a restore; the turn a loadable patch load
  set from its `pose` (plan 43 C2: the phases are no base).
- A loadable patch's pose is exact for a shape, a 4D shape under the 3D switch
  and a 3D shape; a scene that mixes 3D and 4D layers with a body turned
  in keeps its 4D layers' pose and folds its 3D layers' (plan 43 C2,
  `ViewState.pose`). A loadable patch loaded under hold lands its pose at Take
  (`Hold.hold_pose`), not at the load (row 573).
- An old loadable patch (before `/9`) takes the eye the open show's old meta controller
  held only while that show is open (`Project.old_eye`); the migration
  tool is what makes it the loadable patch's for good.
- Knob smoothing infers a glide's ownership by reading the norm back, not
  from a write counter; a loadable patch load drops a patch param's glide
  without landing it; an uncaught fader's pickup can catch on a value a
  glide is passing through.
- A hand Learn reads "centred" from the axis's `bipolar` flag while a push
  centres on its rest; the two can be set apart on the HANDS page. The
  interaction box is off during a calibration sweep, and the confidence
  floor has no hysteresis.
- A desk learn armed with the global layer up swallows every
  non-invariant control until SHIFT is unlatched or the learn cancelled.
- An `abs` knob learned onto `preset.select` spreads over all twenty-four
  slots and can rest on an empty one (audit R14).
- `routing.is_continuous` is open-ended: a typo'd scheme in a loadable patch
  route is a dormant performer, not a refused row. A hand-written
  `cc@<owner>:…` (the owning desk named) dispatches as that desk's but is
  a different control from its unqualified twin to `Binding.overlaps`.

### 3.11 Patches and groups (plan 40)

The reusable fragment beside the desk template (§3.6: a named set of
patch-layer desk rows and modifiers a loadable patch keeps only its overrides
of). A desk template carries rows and nothing of the graph; a **patch**
carries a region of the graph and every row inside it, with its edge.

**The file.** `<library>/patches/<slug>.json`, `hyperspace.patch/1`, a
document kind of `library.Library` (`PATCHES`, `read_patch`, `save_patch`)
that is listed, hidden, renamed and trashed like a loadable patch, but **spawned,
never loaded**. Its keys are the loadable patch's own — `nodes`, `wires`,
`values`, `modifiers`, `routes`, `desk`, `macros`, `lfos`, `envs`,
`layout` — with the patch's own ids, the lowest as if it were alone
(`acid`, `mod.1`, `lfo.1`, envelopes from `env.6`, a macro keeping its
number), its layout relative to its own origin; plus `ports`, the picture,
geometry or mask cables that crossed the edge, each with its type and
`was` (an inlet's source, an outlet's port: `{"id": "in", "type":
"image", "to": "acid.image", "was": "scene"}`).

**The boundary rule** (`patches.read`, classified at read, not stored
twice). A route or desk row whose source is not one of the patch's own
lanes (`mod:` / `lfo:` / `env:` of an id it holds, a macro it holds) is a
**control row**, kept verbatim — a knob, a hand axis, a band is the absolute
address it is. Everything that reaches the host loadable patch's graph is a
**host port**, kept as its type and the name it was on: the `ports`, and,
derived from the rows, a member lane onto a host param, a host lane onto a
member, a member macro's base subscriber on a host param, a modifier input
read from a host lane. A patch holds only what can exist twice (effects,
composites, switches, delays, resizes, copies, extra hands, mattes, cuts,
segments, modifiers, voices, macros); the frame's singletons, the outputs,
the camera, the clouds, a media channel and the sequencer are refused in
words. It never carries a host param's value (D5). `patches.select` is the
one classifier, shared by `lift`, GRAPH's **Group** and the group node's
pins. `patches.py` is a leaf over the pure pieces: it imports `graph`'s
names, `routing`'s `Binding` and scheme split, `modifiers`, `modbank`,
`lfo` and `envelope` (no app module directly; an AST test holds it).

**The lift** (`patches.lift(spec, table, values, layout, ids) → (doc,
refused)`, pure): the members renamed to the lowest ids with every
reference, the layout rebased, every crossing cable classified. The app's
half is `Edit.save_patch` over `LoadedPatch.parts()`; it writes the one file.

**The spawn** (`patches.spawn(doc, host, at) → Landing`, pure, with
`patches.Host.of(spec, table, banks, held)`): the rename map by the
host's rules (`acid` → `acid.2` by the instance rule, `mod.<next>`, the
banks' next voices, a free macro or a note), the rewritten nodes, wires,
values, modifiers, routes, desk rows and subscribers, the group, the
notes, the wants, and every **conflict** with the host: a desk control a
host patch-layer row overlaps (`Binding.overlaps`), a `hand:` / `axis:`
source a host route already sends to another param, a route onto a param
another performer owns (`Bindings.owner`). It lands only the patch's own
wires: a host port is an **open pin**, never attached by itself (D2).
`Edit.spawn` lands it **through the doors, in load order, as one undo
step** (one `_step` before the first write): the section re-read with the
patch's nodes and wires and landed (`gs.land`, so their params exist),
`bank.add` per voice, `add_modifier`, `lib.restore(values)`,
`Bindings.add` or `replace_owner` per route, `bind(write=False)` per desk
row, `set_macros`, the group and its layout at the drop point. No file is
written; the loadable patch's dirty dot lights. `Edit.splice` does the same and
replaces one picture cable with the patch's inlet and outlet; `Edit.wire_as_saved`
lands a spawned group's `was` cables where the node exists and the port is
free; `Edit.wire_taking_over` is the explicit chip that also cuts what feeds an
outlet's taken port, named on the chip (wave 3 P3).

**The conflict sheet** (D3, D9). With conflicts, `ui_routing.modal` draws
one sheet before anything lands, ahead of a Replace / Keep question: a
row per conflict, each on the patch to start, **keep all existing** /
**take all**, the patch's wants, **Spawn** / **Cancel**. While it is up
`Learn.hold` refuses every learn. A row the loadable patch keeps is not added; it
is stored in the group's `kept_by_host` with its words and said on the node
("K1 kept by the preset").

**The group** (D4, D7). A loadable patch's `groups` (after `layout`, `/8`):
`{"id": "group.1", "name", "patch"?, "nodes": [canvas ids], "open"}`.
It is a fold of the canvas and a list in the file, **never a node of the
renderer**: `graph.build_graph`, the signature and the goldens see the
flat graph. Folded, its internal cables are not drawn — the one sanctioned
exception to "no hidden edges" (plan 36), the owner's — and every crossing
cable is re-ended at one of its pins; `+` opens it in place. Group,
Ungroup, open / fold, rename, a drag of the group, a member leaving are each
one undo step through the marks (`library.Marks` carries `groups` and
`group_high`). A group's number is never reused within a loadable patch's life
(row 563): `LoadedPatch.group_high` is the one authority for the next number —
the file's highest at the load, raised by every list assigned, carried by
the marks so an undone load keeps it. Membership is eager: a member
deleted leaves its group's list in the same operation, by a hook on each
mechanism that changes what the loadable patch holds — `GraphSection.on_land`, the
table's `Bindings.on_modifiers` (every `set_modifiers`), each bank's
`Bank.on_change` — all pointed at `LoadedPatch.settle_groups`, so any road
(GRAPH's delete, ROUTING's ×, the LFO and sequencer pages' ×, a spawn, a
restore) settles alike and a draw or a save never finds a dead member to
filter (`live_groups` stays as the save's guard). Every step that removes
a node pushes with the marks, so its undo puts a member back in its group;
a refused load puts the loaded patch's groups and floor back with the rest.

**What the loadable patch wants, and the arrival** (P4). `devices.wants(table,
registry)` lists, per device role, the rows of the loaded patch (enabled
performer routes, patch-layer desk rows, modifier inputs) that the role
would feed, with its state — connected, lost, off, or not in this rig —
and the rows in words (`routing.row_words`: "K1", "right hand y"). The
role is a row's `@role`, else the first MIDI role, else the scheme's
primary, else the first listed publisher, else `devices.SCHEME_ROLE`
(moved here from `graphview`). It is shown on a group's status line, as
**N devices missing** on GRAPH's head and the PRESET strip, and on SYSTEM;
`ui_graph.panel_wants` asks it once a frame. `DeviceRegistry.poll`
compares each device's status with last frame's and, on a change, tells
the listeners once and calls `said(role, before, after)`, which app.py
points at `lib.say(devices.arrival(…))`: "apc40 connected — n controls
live". An error on an open device is no change. The bindings themselves
were always dormant and waiting (§3.3); the MIDI relight is unchanged.

---

## 4. Module shapes

One row per module or package: what it is for, the names you would grep
for, and the rule it keeps with the test that holds it. The module's
docstring has the rest.

| Module | For | Names | Rule (held by) |
|---|---|---|---|
| `params.py` | the registry: ids, base vs effective, the once-a-frame `apply()` | `Param`, `Registry`, `Kind`, `build_registry`, `PATCH_GROUPS` / `SHARED_META_GROUPS`, `F_KEYS`, `pan_world`, `retaper_depths` (a document's depths onto the effects' retapered params read as they were; `UNITS` marks a saved one) | never imports an adapter; every persisted group is performance or meta controller (`tests/test_params.py::test_every_persisted_group_is_patch_or_meta`); `Kind` keeps its identity across a reload (`tests/test_hotreload.py::test_reloading_params_keeps_kind_identity`) |
| `motion.py` | the envelope followers the analyzer is made of, and a damped spring, for any signal; a spring set by perceptual duration and bounce (Apple's model), exactly a frequency and a damping ratio (`spring_hz`, `spring_feel`, the named `SPRINGS`); what a feel does to a jump (`response`, `settle`) | `pole`, `follow`, `spring`, `Motion`, `Follower`, `response`, `settle`, `spring_hz`, `SPRINGS`, `DEFAULT_ROUTE_FEEL` (the feel a new route is made with) | the chain still matches the frozen oracle (`tests/test_golden.py`); the spring is exact at any dt; a response is what a Follower stepping frame by frame lands on; a spring file written as hz / damp reads as the same spring (`tests/test_motion.py`) |
| `tapers.py` | position ↔ value for every fader | `Taper`, `exp_zero`, `exp_pure`, `exp_time`, `lin_t`, `lin_db`, `count`, `exp_signed` (the effects' speed: a hard zero in the middle, exponential either side), `exp_amount` (an amount's zero-safe log: off at 0, then its octaves) | exact round trip on every detent (`tests/test_control.py::test_taper_round_trip`, `tests/test_retaper.py`) |
| `routing.py` | the table, the file, the referee, the desk's layers, the macros, the modifiers, the modulation pass in dependency order, the banks and the sequencer stepped in it | `Binding`, `Bindings` (`modifiers`, `set_modifiers`, `set_modifier_input`), `Router` (`modgraph`, `build_modgraph`, `modgraph_notes`, `use_lfos`, `use_bank`, `bank`, `use_sequencer`, `modulate`, `felt_now`, `felt_lanes`), `BANKS`, `BUILTIN_LANES`, `declare_modifiers`, `Macro` / `Sub`, `Owned`, `act`, `referee`, `register_desk`, `led_level`, `LOOP_KEY_ROWS`, `backup`, `remap_factory`, `renamed_session` | §3.3–§3.8; imports nothing above it (`tests/test_routing_boundary.py`); `tests/test_routing.py`, `tests/test_desk.py`, `tests/test_macros.py`, `tests/test_hand_names.py` |
| `patches.py` | a patch as data (plan 40, §3.11): the file's refusals, its fragment and boundary, the lift out of a loaded patch, the spawn's landing into another, the one boundary classifier GRAPH's groups share | `check`, `read` → `Patch`, `lift`, `Host` (`of`), `spawn` → `Landing`, `Conflict`, `select`, `crossing`, `side`, `ONE_OWNER`, `SCHEMA` | pure: `lift` and `spawn` write nothing; a leaf over the pure pieces (`graph`'s names, `routing`'s `Binding` and scheme split, `modifiers`, `modbank`, `lfo`, `envelope`; no app module imported directly: `tests/test_patches.py::test_patches_is_a_leaf`); `spawn` lands only the patch's own wires and only its members' values (`tests/test_patches.py`) |
| `modgraph.py` | the modulation graph as data and the order it runs in (plan 28 N0; named `patch.py` until plan 40, D1) | `ModNode`, `ModEdge`, `ModGraph`, `KINDS`, `PORTS`, `LFO_KNOBS`, `ENV_KNOBS`, `ordering`, `order`, `cycles`, `RENDER_VALUE` | a leaf (`tests/test_modgraph.py::test_modgraph_is_a_leaf`); dependencies first, ties in insertion order, no loop but through a delay (`tests/test_modgraph.py`) |
| `modifiers.py` | the six modifier kinds as pure steps (plan 28 N1) | `Modifier`, `KINDS`, `PARAMS`, `INPUTS`, `OUT`, `ModState`, `step`, `smooth_motion`, `next_id`, `param_id` | imports only `motion` and `tapers`; the Router declares their params (`routing.declare_modifiers`) and steps them; never in `bindings.json` (`tests/test_modifiers.py`) |
| `learn.py` | arming, completing and refusing a Learn; pick-then-map; a sink pick; Unbind | `row_for`, `whole_circle` (a hand's room lane: `position`, depth 1, no feel; plan 51), `Learn` (`arm`, `wants`, `accepts`, `learn_control`, `learn_source`, `learn_pad_button`, `learn_sink`, `sinks`, `pick`, `map_picked`, `unbind`, `pending`, `last`, `devices`), `BARE_WANTS`, `blocked`, `bound`, `centred_target`, `PUSH_DEPTH`, `LANE_DEPTH` | nothing completes a learn its `want` does not name; a refused desk learn stays armed; a non-modulatable target is refused for a hand; no learn writes a file (`tests/test_learn.py`) |
| `deck.py` | the deck (plan 44 D1): today's per-deck singletons in one bundle, built in `app.main`'s order | `Deck` (`reg`, `view`, `table`, `router`, `lfos`, `envs`, `seq`, `clock`, `presets`, `graph`, `learn`, `undo`, `marks`, `renderer`, `hold`), `Deck.build`, `Deck.targets`, `DeckHooksMade`; `library.DeckLibrary` and `DeckProject` are a deck's views of the one library and show; `MetaController` (plan 44 D5a: the two decks and a `Pointer` per holder; `point`, `point_panel`, `on_air`, `off_air`), `KEYS`, `MOUSE` | one construction order for `app.main` and the headless `tests/test_undo.boot`: the meta controller's objects built between its lines are hooks (`hands`, `outputs`, `panel`, `devices`, `table`) called at their old places, so the registry's order is unmoved; the meta controller's own wiring (the library's band hooks, `control.library`) is the caller's, before `build`; `targets()` lists the deck itself first and the clock it builds; each hook returns its object, threaded by `build` to the hooks after it and recorded on a `DeckHooksMade`; `attach` / `startup` / `install` switch off the process's one-of-a-kind steps for a second deck; a headless deck builds no GL (no renderer, no hold); it changes no behaviour — the old order and the deck land every corpus loadable patch to the same state (`tests/test_deck.py`) |
| `playlist.py` | the playlist, for installs (plan 44 D6): its file and the playing of one | `Playlist`, `Entry`, `Playing` (`select`, `play`, `stop`, `step`, `tick`, `left`), `read`, `save`, `LEAD_S`, and in `library` `PLAYLISTS`, `Library.save_playlist` | the meta controller's and an operator's verb: imports only `library`, and reaches the decks by the arguments it is given; a load through the deck off air's `LoadedPatch.load`, a fade only through `MetaController.crossfade`; nothing of it lands in a look |
| `midi.py` + `apc40.py` + `generic.py` | the MIDI adapter, one `MidiIO` per desk with its role and profile (ports, per-desk layered dispatch, feedback, soft pickup, knob glides, holds), the APC40 profile (the default map, `LAYOUT` of every control, LED colours) and the `generic` profile (plain CC / note / pitch, nothing sent back) | `MidiIO` (`role`, `qualifier`), `Ports`, `Slew`, `retry_after`, `HOLD_S`, `BLINK_S`, `PROFILES`; `apc40.DEFAULT_MAP`, `BANK_PADS`, `SCENE`, `LAYOUT`, `named`; `generic.PORT_MATCH`, `FEEDBACK` | every write is a base write; a note-off goes where its note-on went; a message a row did not apply (a disabled row, a learn candidate) makes that pickup row pick up again (`MidiIO._passed_over`); a lost port is looked for at `retry_after`'s pace (`tests/test_midi.py`, `tests/test_desk.py`). Every test runs with no real MIDI port (`tests/conftest.py::_no_real_midi`) |
| `hands/` | the Ultraleap instrument: twelve shaped axes, presence, eight pinch switches, the dance sources and the grab, the room lanes, the DAW messages (carried out by the `hands-daw` sink; the instrument opens no port), calibration and the interaction box, hand tapes, the HANDS page, the device wrapper | `HandsIO` (`poll`, `outbox`, `carry`, `resync`), `HandSettings`, `Layout`, `LeapSource`, `Box`, `inside`, `DEFAULTS` (`core.py`); `signal.py` (shaping, MIDI encoding); `room.py` (the palm in the room's frame: `Palm`, `angles`, `frame`); `tape.py` (`TapeSource`, `record`); `panel.py` (`page`); `device.py` (`HandsDevice`) | `core.py`, `room.py`, `signal.py`, `tape.py` import nothing from the host; `device.py` and `panel.py` alone know it (`tests/test_hands_boundary.py`); a hand outside the box is absent for every consumer; the layout is published to the router only on a change (`tests/test_hands.py`) |
| `modbank.py` | a modulator bank (plan 31): voices by stable 1-based id, never compacted, cap 16; params declared per voice through the kind's `declare`; NaN in a gap; the late-gesture hold | `Bank` (`ids`, `add`, `remove`, `set`, `doc`, `parse`, `next_id`, `can_add`, `bind`, `begin`, `step_one`, `late`, `late_one`, `publish`), `MAX`, `MAX_ID` | a leaf (`tests/test_modbank.py::test_modbank_imports_nothing_from_the_host`); a route from a removed voice goes dormant, LFO 3 keeps `lfo:2` (`tests/test_modbank.py`) |
| `lfo.py` + `tempo.py` | the LFOs, a bank of four by default up to 16, and the tap-tempo clock (its `epoch` counts triggers) | `LFOs` (a `Bank`), `LFO`, `declare`, `register`, `N`; `Clock` (`trigger`, `epoch`, `beat`) | `tempo` imports nothing from the package, `lfo` only `modbank` (`tests/test_lfo_boundary.py`); §3.9 (`tests/test_lfo.py`, `tests/test_tempo.py`) |
| `envelope.py` | the envelope generators (plan 31): event-driven AHDSR voices with exact stamped fires, and their bank, `env` — 1–5 always, extras to 16 | `Envelope` (`fire`, `release`, `step`, `set_gate`, `rel`), `Envelopes` (a `Bank`: `fire`, `release`, `LANE_ENVS`), `declare`, `register`, `shape`, `MODES`, `CURVE_POW` | imports only `modbank` (`tests/test_envelope_boundary.py`); a sub-frame fire equals the closed form (`tests/test_envelope.py`) |
| `sequencer.py` | the step sequencer (plan 31): five lanes × eight steps read off the clock, each crossed step fired at its exact time, the `seq:` trigger lanes | `Sequencer` (`step`, `publish`, `time_of`, `gate_seconds`, `restart`, `playhead`), `Lane`, `register`, `LANES`, `STEPS`, `SPANS` | a leaf (`tests/test_sequencer.py::test_the_sequencer_imports_nothing_from_the_host`); each step fires once at its exact t, a stall no burst, a backward nudge nothing twice (`tests/test_sequencer.py`) |
| `audio.py` + `analysis.py` + `analyzer.py` + `bands.py` | capture or file playback, the FFT, the N-band analyzer whose output is `lanes`; `bands.py` is its parts bin | `AudioEngine`, `Analyser`, `Analyzer`, `CEIL` | imports only the stack and `tapers` (`tests/test_audio_boundary.py`); the legacy six-band layout matches the frozen oracle to the bit (`tests/test_analyzer.py::test_legacy_layout_is_bit_exact`) |
| `media/mixer.py` | the media mixer (plan 45 V2, V4): every heard channel's video sound summed into one output stream (48 kHz stereo float32), each read by a head slaved to its transport and resampled by its speed | `Mixer` (`feed`, `close`, `line`, `state`, `playing`, `underruns`, `errors`, `_callback`), `Voice`, `BLOCK`, `RETRY_S`, `CEILING`, `HOLD_SPEED`; `Transport.velocity` / `wrap`, `Soundtrack.holds` / `ends_at`, `MediaState._voices`, `Channel.play_audio` / `gain`, `media.<c>.audio` / `.gain` | **no second time base**: a head is set by the transport (slewed or cut to it each block, stopped when it goes quiet) and read by nothing else (`tests/test_media_varispeed.py`, `tests/test_media_mixer.py::test_the_callback_starts_at_the_transports_position_and_moves_nothing_of_it`); once warm the callback allocates nothing a block's size (`test_the_callback_allocates_nothing_once_warm`); nothing opened until a channel's sound is on, the open off the frame thread, the callback never raises (`test_the_stream_opens_on_the_first_toggle_and_not_before`, `test_the_open_never_holds_the_frame_thread`, `test_a_read_that_raises_is_contained`); `sounddevice` imported only at the open; a reload keeps the stream (`test_a_reload_of_the_module_keeps_the_stream_and_reaches_the_new_callback`) |
| `geometry.py` | the shapes as vertex, edge and face arrays; whether each is 4D or 3D; scenes of several; the 4D → 3D transform and the shared camera (the eye, the shape's world transform); the old 4D → 2D transform as the parity oracle; the volume measures | `SHAPES`, `Shape` (`cells`, `dims`, `family`, `layers`), `Layer`, `geom`, `faces`, `world_points`, `shape_world`, `model_matrix`, `eye_matrix`, `eye_project`, `EYE_FOV`, `EYE_DISTANCE`, `PAN_REF_PX`, `project_h`, `project3`, `shape_view`, `PLANES`, `view_angles`, `is_3d`, `rot_matrix`, `view_depth`, `volume_ratio`, `sweep_ratios`, `edge_on_share`, `VOLUME_FLOOR` | the list is append-only and the first 18 shapes' order never changes — the golden traces key on it (`tests/test_core.py::test_construction_exact`, `tests/test_golden.py`); a shape draws what it was recorded drawing (`tests/test_shapes4d.py::test_every_shape_draws_what_it_was_recorded_drawing`); a 3D shape sits at w = 0 and only its W angles are dropped, never in place (`::test_a_3d_shape_sits_at_w_0`, `::test_the_w_planes_leave_a_3d_shape_alone`); every 4D shape keeps `VOLUME_FLOOR` through each W plane (`::test_every_4d_shape_clears_the_volume_floor`) |
| `patterns.py` | the face patterns' eight inputs and seventeen modes as data: names, meanings, what each input does in each mode | `INPUTS`, `MODES`, `NAMES`, `SCALE` … `SPREAD`, `effect`, `ignores`, `label`, `tip` | imports nothing (by convention); `params`, `render` and `ui_patterns` read it; `shaders/patterns.glsl`'s accessors and header are held to it, and modes are appended, never inserted (`tests/test_patterns.py`) |
| `view.py` | `ViewState`, the live object the view, rotation and camera params write | `ViewState` (`integrate`, `instances`, `inst_layout`), `RED` | imports only `geometry`; no GL, so the registry and tests can hold a view |
| `field.py` | the instance field: where each copy goes — the flat layouts, the six 3D lattices, the fit to the screen and its snapped zoom and pan, the painter's order between copies, the cull | `field` (per frame: a row of centre, scale, alpha per drawn copy), `lattice`, `inst_positions`, `fit_dims`, `NAMES`, `LAYOUTS_3D` | pure numpy, imports only `geometry`; no GL, no state but caches (`tests/test_field.py`) |
| `graph.py` | the render graph (§2): node kinds and ports (`IMAGE`, `MASK`, `GEOMETRY`, `VALUE`), evaluation in dependency order, the wired frame built from the `Wiring` alone (`build_graph`: only what a wire reaches; each window's ports its own wire else All outputs' by its bus cable, `window_ports`), the effect nodes, the look-back and the dream as two nodes, the hands node, the point-cloud node, the loadable patch's `graph` section, the wiring in words (plan 30 placements read only for the migration) | `Node`, `Graph` (`order`, `evaluate`, `pulled`, `timed`, `timed_in`, `pool`, `dormant`), `Frame`, `Shape`, `Hands`, `PointCloud`, `Scene`, `Cover`, `HandsLayer`, `Readout`, `Composite`, `Effect`, `Copy`, `Shown`, `History`, `Capture`, `Output`, `Wiring`, `PatternNode`, `BackdropNode`, `SwitchNode`, `Delay`, `DelayWrite` (z⁻¹, plan 34), `EchoNode`, `DreamNode`, `ResizeNode` (own size, `Node.own_size`, built by `_Build._make`), `MatteNode`, `MaskPicture`, `CutNode`, `SegmentNode`, `SegmentPin`, `MatteAt`, `CutAt`, `SegmentAt`, `mask_of`, `mask_port`, `segment_pin`, `SEGMENT_PINS`, `PICTURE_INTO_MASK` (plan 39), `DelayAt`, `ResizeAt`, `EchoAt`, `DreamAt`, `LookbackAt`, `BusCuts`, `BUS_PORTS`, `bus_wire`, `window_ports`, `wire_loops`, `loop_words`, `build_graph`, `graph_key`, `GraphSpec`, `EffectAt`, `CompositeAt`, `SwitchAt`, `Wire`, `wire_error`, `read_graph`, `run_of`, `reaches`, `SINKS`, `RESERVED`, `source_into`, `channel_into`, `placement_words`, `NODE_KINDS`, `PORT_TYPES`, `cloud_roles` | imports the render stack only and names no write (`tests/test_graph.py`); a loadable patch's graph it cannot read is a note and is not read — black, nothing filled in (`tests/test_graph_json.py`) |
| `render.py` | the passes the graph's nodes call: face picture, scene (with depth), cover, the hands' lay, composite, outputs, dim; the GPU timer; the patterns' clock and the FACES page's swatches; the scene's instanced draws (one 3D pass, one vec4 a copy) | `Renderer` (`draw`, `draw_outputs`, `thumbs` (GRAPH's thumbnails, plan 37; the module's `thumb_source` resolves them), `mask_passes`, `segmenter`, `motion_pair`, `media_now` (plan 39), `_graph_for`, `wiring`, `ghost_of`, `cloud_source`, `lay`, `dim_pass`, `pool_at`, `stats`, `timer`, `now`, `bands`, `_pattern_clock`, `want_swatches`, `swatch`, `pattern_tile`), `PassTimer`, `SceneTarget`, `DEPTH_ALPHA`, `LAYER_DEPTH_BIAS`, `CELL`, `FaceTarget`, `inst_positions` (re-exported from `field`), `render_offscreen` | imports no registry (`tests/test_render.py::test_the_render_stack_imports_no_registry`); §2's draw guarantees (`tests/test_render.py`, `tests/test_camera.py`, `tests/test_golden_frames.py`) |
| `fx.py` + `shaders/fx/` | post effects as GLSL files whose `// @param` uniforms become params (a line flagged `amount` is on the zero-safe log taper `amount_taper`; every `speed` on the signed exponential `T_SPEED`; `retaper_of` says what a route's depth onto one is measured against — wave 0 T1) and whose `// @clock <uniform> <rate-param> [period]` lines are phases the host integrates (speed × the param, wrapped to the period) and binds; one effect's pass for a graph node (every effect is a `graph.Effect` node where the graph wires it) | `FxState` (`names`, `live`, `advance_to`, `face_map`, `clocks`), `FxChain` (`run_one`, `pool`, `fit_pool`, `ready`), `ClockSpec`, `FACE_MAPS`, `declare` | an effect is never defined in Python; a broken edit keeps the last good spec; off is bit-identical; `@order` is parsed and read only by `graphmigrate`; `fx.face_map` is modulatable (`tests/test_fx.py`); **no shader multiplies time by a param** — a rate-like param is a `@clock` (row 560; `tests/test_shader_time_lint.py` holds every shipped shader to it, `tests/uv_flow.py` measures a step) |
| `lookback.py` + `dream.py` | the frame history and its age-weighted composite; the torch worker that dreams on it | `Lookback`, `DreamState`, `DreamWorker` | torch only in `dream.py`; nothing in the core imports `dream`; `submit` never blocks the frame (`tests/test_dream.py`, `tests/test_lookback.py`) |
| `masks.py` | the mask passes (plan 39): a picture → a mask (luma, alpha, chroma), the separable feather, the promotion (white / black by cover), the cut, the motion matte and its background learn, the worker's downsample | `MaskPasses` (`matte`, `feather`, `promote`, `fit`, `cut`, `motion`, `learn`, `readback`), `MATTE_FS`, `BLUR_FS`, `PROMOTE_FS`, `CUT_FS`, `MOTION_FS`, `LEARN_FS`, `DOWN_FS`, `cover_scale`, `MOTION_SOFT` | imports `moderngl`, `numpy` and `glsl` only (`tests/test_graph_masks.py::test_masks_is_a_leaf`); `cover_scale` equals `media_tex.fit_scale(COVER)` (a test); hot-reloadable, before `render` |
| `segment.py` | the segment worker (plan 39): a person matte off the frame thread, one worker per node on the dream's pattern; Apple Vision and torchvision behind one backend shape | `SegmentWorker` (`submit`, `latest`, `wants`, `said`, `stop`, `close`), `VisionBackend`, `TorchBackend`, `pick_backend`, `make_worker`, `find_weights`, `QUALITIES` | imported only by `Renderer.segmenter`; top level numpy and the standard library only, Vision / Quartz / torch inside `open()` and `run()` (`tests/test_app_boundary.py`, `tests/test_dream.py::test_core_does_not_import_the_worker`); `submit` never blocks, `close` joins within 1 s (`tests/test_segment.py`); cold for hot reload (live threads) |
| `ghost.py` | the ghost hands — a display, not a source: drawn in the shared camera (the eye and the Leap calibration), as their own layer or solid in the scene | `Ghost` (`settle`, `layer`, `draw_solid`, `composite`, `readout`, `composite_readout`, `depth`, `error`), `GhostState`, `Geometry`, `HandPose`, `STYLES`, `PARTS`, `box_of`, `calibration`, `shared_camera`, `CAL_ASPECT`, `prefix`, `register` | writes no param; off or with no hand it touches no GL state; in the history only when the graph wires it there; `ghost.style` / `.mirror` / `.guide` / `.tethers` not modulatable (`tests/test_ghost.py`, `tests/test_hands_node.py`) |
| `outputs.py` | the render outputs as the renderer sees them; the control window's taps on them: output 1's `Preview`, the GRAPH page's node thumbnails (plan 37) and the GRAPH canvas's own tap (`CanvasTap`, 2026-11-02: a pool of textures on the control context, each grab into one no frame holds — a `MediaFrame` carries a `Lease` on its texture, so a frame held at rate 0 names a texture no later grab writes and no resize frees — a lease dropped on any thread is handed back on a deque and counted off on the frame thread; `want` / `take` as `Preview`'s, `begin` / `end` or `abort` round a grab; `Offscreen.fit` makes the new texture before letting the old go) | `Switches`, `route`, `fit`, `View`, `Handoff`, `Slot`, `Presenter`, `PIPELINES`, `MAX_OUTPUTS`, `Preview`, `PreviewTextures`, `CanvasTap`, `Lease`, `fit_size`, `THUMB_PX`, `thumb_size`, `dominant_hue` | imports `moderngl` and `glsl` only (`tests/test_outputs.py::test_outputs_imports_nothing_from_app_ui_or_params`); `route`, `fit` and `fit_size` are pure |
| `replay.py` | draw-list replay (2026-11-02): the GRAPH canvas drawn again from its own imgui draw lists into `outputs.CanvasTap`, after the control window's own render and before its swap — the filter rule (`keep`: only the page window's own list, by `ImDrawList._owner_name`, as `Panel.canvas_px` records it; a child, a popup, a tooltip, the foreground list are dropped; the side pane's decorations — its ground, border and scrollbar, which imgui draws on the parent's list inside `begin_child` — cut out by the index range the page noted, `spans`), the GL replay with the backend's program and the projection moved onto the canvas rect | `keep`, `canvas_lists`, `spans`, `scissor`, `projection`, `draw_lists`, `framebuffer_size`, `grab`, `BACKEND_ATTRS`, `missing_backend_names`, `check_backend`, `FOREGROUND`, `BACKGROUND` | imports `outputs`, imgui and GL only; the backend's private names `draw_lists` uses are checked on import (`check_backend`: a rename raises there, not as every grab's error); `keep`, `spans`, `scissor`, `projection` are pure (`tests/test_replay.py`); the page's note covers the pane's decorations and nothing else (`tests/test_media_panel.py::test_the_pane_decorations_are_noted_for_the_replay_to_cut_out`); `grab` draws only on a frame the tap was wanted, GRAPH drew and the framebuffer is not empty (the backend skips those frames before scaling the clip rects), a draw that fails is `abort`ed — nothing published — and is the tap's `error`, never the loop's; the viewport is put back after `end` (moderngl's rebind reapplies the one it noted at creation) |
| `glsl.py` + `shaders/_common.glsl` | the GLSL every shader shares | `QUAD_VS`, `common`, `FALLBACK` | a helper is defined once; a broken edit falls back to `FALLBACK` (`tests/test_fx.py::test_the_shared_helpers_are_written_once`) |
| `overlay.py` | where output 1 is and how it looks (window, fullscreen, overlay); the master dim; the per-output switches | `Output` (`register`, `apply`, `allowed`, `dim`), `register_switches` | touches the window system only in `apply()`; meta settings never persist or modulate; overlay only when the config allows (`tests/test_overlay.py`) |
| `ui.py` + `ui_*.py` + `hands/panel.py` | the control window: GRAPH always drawn with its side pane of sections (plan 49; `ui.PAGE_KEYS`, the seventeen slots `ui.page` focuses by a saved index), widgets as views onto params, the right-click menu, the modal, the on-screen desk (`ui_desk.py`) and gamepad (`ui_pad.py`; its readouts — map, faithful, lanes, cockpit — `ui_pad_views.py`, picked by `ui.pad_view`; faithful and cockpit the lab's drawings, `ui_pad_lab.py`, drawn by NanoVG into a texture, `ui_pad_nvg.py`); the FACES page is `ui_patterns.py` (`page`, `drivers`, `suggest`, `neutral_all`); a feel beside its knobs is `ui_feel.py` (`sample`, `draw`): its shape from `motion.response` (static: a picture of the knobs; the spring presets' picker draws each one's, `spring_picker`), and the feel working live — the reading and the Router's felt value (`Router.felt_now`, `Router.felt_lanes`), sampled by the panel as it draws; the Router keeps nothing for it | `Panel`, `PAGE_KEYS`; each section body's `page(panel)`; `ui_routing.modal`; `ui_desk.click` | a widget writes only bases; nothing here calls `modulate`; no control passes the pane's edge (`tests/test_ui_pane.py::test_every_section_focused_lands_in_view_and_inside_the_pane`); no conflicting imgui ids (`tests/test_ui_routing.py`, `tests/test_ui_lfo.py`, `tests/test_ui_seq.py`) |
| `ui_seq.py` | the SEQ page (plan 31): the transport, the 5 × 8 step grid in the APC40's LED palette (the playhead column in the one red, columns past `length` dimmed and inert), each lane's select, mute and envelope picker, and a strip per envelope (one open, the rest folded) | `page`, `toggle_step`, `cell_state`, `fill`, `select_lane`, `open_env`, `add_env`, `remove_env` | a function over the Panel; every cell and knob an ordinary param write; envelopes 1–5 never removed (`tests/test_ui_seq.py`) |
| `ui_pane.py` | GRAPH's side pane as folding sections (plan 49): the selection's details, then every other body that was a page, each drawn by its own function under `push_id("pane.<key>")`; the focus, owned by `Panel.page` (`ui.page`): the section it names (`section_of`, `focused`) shown however it is folded, scrolled to (`scroll_to`), given the room, and in the narrow band alone in a taller band (`ui_graph.band_height`); a click on a header lets go (`let_go`); the fold state in `<machine>/ui.json` (`pane.open` beside the canvas, `pane.below` in the narrow band, beside `graph.side_w`), written atomically after the last click, never by a focus | `SECTIONS` (each row its body and its groups: the one table of what each section's params are), `DEFAULT_OPEN`, `DEFAULT_BELOW`, `draw`, `section_of`, `focused`, `scroll_to`, `let_go`, `shown`, `opened`, `set_open`, `flush`, `read_open`, `write_open`, `read_doc`, `write_doc`; `ui_graph.band_height` | a function over the Panel and GRAPH's page state; a widget keeps its page's label, so the driver and Learn find it by the same id; no conflicting imgui ids with every section open (`tests/test_ui_pane.py`) |
| `graphview.py` + `ui_graph.py` | the GRAPH page (plan 28): the model of both graphs as nodes, ports and cables (since plan 31 a node per LFO and envelope by id, the sequencer's node with five trigger outs, and its `lane` cables — a lane's envelope binding, rebound by a drag, never deleted), its layout and its edits (`graphview`, no imgui); the canvas on `imgui_node_editor`, its menus and the drag / delete dispatch (`ui_graph`); since plan 37 every picture node drawn as its picture, its hover and the tint switch; the shape node's details open on its wireframe, drawn by the renderer (`Renderer.want_wire`) | `View`, `VNode`, `VPort`, `VCable`, `build`, `refresh`, `key`, `OWNERS`, `auto_layout`, `home`, `device_nodes`, `Edit` (`connect`, `move`, `disconnect`, `insert_modifier`, `wire`, `unwire`, `add_node`, `insert_node`, `place_node`, `drop_node`, `set_node`; `insert_effect` / `place_effect` the effect wrappers), `INSERT_PORTS`, `INSERT_MENU`, `insert_ports`, `inlet_choices`, `is_source`, `drop_refusal`, `insert_items`, `onto_refusal`, `onto_sides`, `onto_words`, `Refusal`, `Ask`, `cable_near`, `cables_near`, `drop_reach`, `THUMBS`, `thumb_of`, `THUMB_H`, `picture_hover`, `laid_areas`; `ui_graph.page`, `editor`, `close`, `CREATE`, `DELETE`, `DELETE_NODE`, `picker`, `render_edit`, `onto_plan`, `drag_words`, `dropped`, `drop_plan`, `put_onto`, `insert_node`, `insert_effect`, `thumb_wants`, `tint`, `cable_tints`, `wire_px`, `is_pad_node`; `Renderer.want_wire`, `wire_texture` | `graphview` imports no imgui (`tests/test_graphview.py::test_graphview_imports_no_imgui`); one table for ROUTING and GRAPH (`::test_the_routing_page_and_the_graph_page_show_one_table`); every edit through the table's own calls or a `graph` section read back (`tests/test_graph_edit.py`, `tests/test_graph_wires.py`); the APC40 drawn, never changed (`tests/test_graphview_devices.py`); a thumbnail is made only for a wanted node and moves no output pixel (`tests/test_thumbnails.py`); the shape's wireframe is drawn only while asked for, freed a second after, and moves no output pixel (`tests/test_shape_wire.py`); no cable runs backwards across areas (`tests/test_graph_areas.py`) |
| `control.py` | the headless half of the analyzer page: band selection, scenes, reset | `Control`, `SCENES` | reset goes to the selected scene and never changes the layout (`tests/test_control.py::test_reset_resolves_to_selected_scene`) |
| `library.py` | the library root (`Library.home`) and the machine home (`Library.machine`), document kinds (loadable patches; patches, spawned never loaded, plan 40), module presets (fx's retired), shows, the bank, the trash — one tier since 2026-10-28: nothing ships, every loadable patch deletable and renameable | `Library`, `Project`, `Marks`, `SLOTS`, `RENAMABLE`, `scene_doc`, `to_trash`, `next_name`, `path_slug`, `bank_doc`, `PATCHES`, `read_patch`, `save_patch`, `RETIRED_MODULES` | a file is copied to the trash before it is overwritten or deleted; a load never rewrites a show; every write is atomic; a shared library missing at launch is never created and refuses every write; never imports `config` (`tests/test_library.py`, `tests/test_loadable.py`, `tests/test_shared_library.py`) |
| `loadable.py` | the loadable patch document kind: values, routes, desk, macros, module labels, the `graph` section (nodes and wires), the modifiers, the banks' membership (`lfos`, `envs`), the GRAPH page's layout, and since plan 40 its `groups` (written only when one exists, then `hyperspace.preset/8`); `hyperspace.preset/3` only when a loadable patch uses the sequencer, the envelopes or N ≠ 4 LFOs, else `/2` | `LoadedPatch` (`load`, `load_doc`, `document`, `signature`, `layout`, `template_at_load`, `live_groups`, `settle_groups`, `group_high`, `parts`, `banks`), `schema_of`, `SCHEMA_V3`, `VERSIONS`, `GraphSection`, `GRAPH_KEY`, `MODIFIERS_KEY`, `LAYOUT_KEY`, `GROUPS_KEY`, `read_groups`, `group_entry`, `merge_modifiers` | a load lands every performance base and replaces every performer row, never a shared meta param; a route onto a non-modulatable param is dropped with a note (`tests/test_loadable.py`) |
| `config.py` | `config.toml`: defaults, reading, `[[output.screens]]`, `[[devices]]` (checked per entry; the old device tables translated; `[hands] out` → `hands-daw`) | `DEFAULTS`, `load`, `screens`, `number`, `devices`, `read_devices`, `DEVICE_TABLES`, `MIDI_OUT`, `DAW_ROLE` | a bad value is its default with a note, never a raise (`tests/test_config.py`) |
| `undo.py` | undo and redo with no write hook; three stacks since plan 44 D5b, one per `Deck` scoped to its loadable patch (`only`) and the meta controller's, and `here` says which ⌘Z reaches | `Undo`, `watched`, `alike`, `install`, `install_meta`, `here`, `where`, `push`, `push_on`, `push_meta`, `by_hand`, `on_air`, `takes_back`, `SETTLE_S`, `LIMIT` | a leaf (`tests/test_undo.py::test_undo_imports_nothing_from_the_package`); §3.2 (`tests/test_undo.py`) |
| `groupwords.py` | what the panel calls a param group where that is not its saved key (wave 4 AZ, rows 737–738) | `GroupWords`, `GROUPS`, `group_word`, `group_title`, `group_part`, reached from `undo.py` through `Registry.group_word` | a leaf; `tests/test_analyzer_words.py` |
| `hold.py` | hold the projector (plan 38): the program drawn from the wiring, bus cables and look held at HOLD while edits land as the preview behind GRAPH; take, drop; the `output.hold` / `.take` / `.drop` controls | `Hold` (`engage`, `take`, `drop`, `program`, `draw_preview`, `keep`, `program_only`, `reset_delays`, `changed`, `rewired`), `HELD_GROUPS`, `ONE_FOR_BOTH`, `PROGRAM_IDS`, `program_value`, `preview_size`, `mirror`, `MIRRORED`, `preview_renderer`, `canvas_renderer`, `register` | at module level imports only `undo` and `params`' groups and id helpers, no graph and no GL (`preview_renderer` imports `render` when first called; the renderer, registry and undo are arguments, read duck-typed); the program writes with `Param.put`, never `set`, and puts every live value, the wiring and the meta controller back even when the draw raises; never constructs a `Wiring` or fills in a cable (`tests/test_hold.py`) |
| `devices.py` | the device registry: the protocol, the ports, today's devices (MIDI, the pad, the bridge, `midi-out`), the point-cloud type, file and device, the list's open / retry / watch / close | `Device`, `Port`, `Context`, `Base`, `OffDevice`, `RefusedDevice`, `MidiDevice`, `PadDevice`, `BridgeDevice`, `MidiOutDevice`, `CloudDevice`, `PointCloud`, `write_clouds`, `read_clouds`, `kinds`, `make`, `DeviceRegistry` (`poll`, `feed`, `send`, `continuous_schemes`, `row_schemes`, `midi_roles`, `primaries`, `wants`, `sink_ports`, `clouds`, `lines`, `watch`, `apply`, `said`), `retry_after`, `WATCH_FRAMES`; what a loadable patch wants (plan 40, §3.11): `wants` → `Want`, `wants_for`, `want_words`, `want_lines`, `missing_chip`, `wanted_lines`, `arrival`, `SCHEME_ROLE` | the one importer of every adapter module, each inside its device's `open` (`tests/test_app_boundary.py::test_importing_app_leaves_every_gated_adapter_unimported`); one device's exception never stops the frame; two enabled devices never feed one Router key — a second pad publishes under its role, a second hands device is refused (`tests/test_devices.py`) |
| `osc.py` | an OSC sender as a device: a non-blocking UDP socket read in `poll`, axes fed under the role, hits as rows | `OscDevice`, `Server`, `Layout`, `fire`, `TIMEOUT_S`, `DEFAULT_PORT` | `pythonosc` only inside `Server`; only this module and the kind table name the device (`tests/test_osc.py`) |
| `pads/` (plans 42, 46) | game controllers as one vocabulary: `models.py` a `Model` per kind of pad (its caps, its glyphs, which controls it has) and the `controller =` rule; `sony.py` the DualSense / Edge report format (input over USB, BT full and BT simple; calibration; output with the BT CRC; trigger effects); `nintendo.py` the Joy-Con / Pro Controller format (report 0x30 by position for the Wii-Remote hold, the flash's stick and sensor calibration and the rest's recentre, HD rumble and the player lights, the connect sequence); `gesture.py` the `touch:` and `motion:` lanes; `hid.py` the hidapi road (a reader thread per pad through its codec, the hub lending pads to entries, tapes) | `models.MODELS`, `HID_IDS`, `matches`, `may_be_hid`, `parse_spec`, `is_model`, `glfw_ids`; `sony.decode`, `calibration`, `update_version`, `output_report`, `trigger_block`, `Effects`, `Trigger`, `player_bits`; `nintendo.decode`, `calibration`, `recentre`, `setup`, `output_reports`, `rumble_bytes`, `AXIS_MAP`; `gesture.Touchpad`, `Motion`, `AxisMap`; `hid.HidPad`, `HidHub`, `TapePad`, `Recorder`, `pad_devices`, `codec_for`, `available` | `models`, `sony`, `nintendo` and `gesture` are leaves (the standard library and each other); `hid` imports `hid` only in a scan or an open (`tests/test_pads_sony.py`, `test_pads_nintendo.py`, `test_pads_gesture.py`, `test_pads_hid.py`) |
| `gamepad.py` + `bridge.py` | a pad read by one of four roads into one vocabulary (plan 42): GLFW raw (the Xbox map, or a Sony map without hidapi), hid (a Sony pad over USB or Bluetooth, `pads/hid.py`), a wired 360 pad over libusb (`UsbPad`), a tape; its axes fed as the `axis` lanes, its touchpad and sensors as `touch` / `motion` (`touch_lanes`, `motion_lanes`), its outputs taken as `Effects` (`send_effects`), the sticks' default camera job; the face drawn per model (`layout_for`, `shown_model`, `control_in`); the DAW bridge (`ext` lanes in, its sink rows out as MIDI) and the MIDI out port and gate the sinks share | `Pad` (`open`, `poll`, `close`, `publish`), `publish`, `steer`, `ride_depth`; `Bridge` (`receive`, `publish`, `send_values`, `reconnect`), `Sender`, `OutPort` | the pad never raises when absent; the bridge never writes a `Param` and is off by default (`tests/test_gamepad.py`, `tests/test_bridge.py`) |
| `app.py` | the entry point: windows and outputs, construction order, the frame loop, the device registry and the dream gate; the media resolver (`MediaResolver`: the folder, the devices' feeds and the built-in `panel:graph`); after the control window's imgui render, `replay.grab` into the GRAPH canvas's tap (2026-11-02) | `main`, `Host` (`devices`, `adapters`, `pad`), `frame`, `Keys`, `Mouse`, `MediaResolver`, `close_all`, `_draw_render`, `_open_devices`, `_open_dream` | §1 Host row, §2 (`tests/test_app_boundary.py`, `tests/test_app_relative.py`) |
| `hotreload.py` | hot reload of every module but the cold core | `HotReloader`, `MODULES` | every module but `app`, `hotreload`, `offline`, `watchdog` and `segment` (plan 39: its worker threads outlive a reload) is watched, in dependency order, leaves first (`tests/test_hotreload.py::test_every_package_module_but_the_cold_core_is_watched`, `::test_the_watch_list_is_in_dependency_order`) |
| `nodemode.py` | node mode's saved form and the fill its rows derive from (plan 57) | `NodeMode`, `Pointing`, `fill`, `Fit`, `fillable`, `enter_refusal`, the `node_mode` key | below `preset` and above `routing`; `LoadedPatch.node_mode` holds one per `Deck`, and no rows are saved (`tests/test_nodemode.py`) |
| `ui_players.py` | the player select screen (wave 4 PS, plan 55): the ON AIR and OFF AIR lanes and a token per player, drawn with imgui's draw list, as a side pane section and large in its own window (the footer's chip, O); a move by mouse, and said | `section`, `window`, `footer`, `summary`, `lay_out`, `held`, `loose`, `move`, `give`, `GLYPHS` | moves only through `MetaController.move_player` and `register`; no stick, pad or desk reaches it; nothing passes the room's edge at any width (`tests/test_ui_players.py`) |
| `players.py` | the players, their duties, who holds which controller, on this Mac (plan 55) | `Players`, `Player`, `Duty`, `<home>/players.json` | a leaf; `deck.MetaController` turns a duty into a `Deck` and moves the pointers, `devices.qualifiers_of` names a pad's rows from it, and no patch or show holds any of it (`tests/test_players.py`) |
| `pointer.py` | which `Deck` a holder is on (plan 44 D5a) | `Pointer`, `Through` | a leaf, importing nothing of the package; `Through` is a plain attribute until its holder has a pointer, then reads the deck's field and refuses a write (`tests/test_meta_controller.py`) |
| `placement.py` | where the windows open and `<home>/windows.json` | `place`, `screens`, `load` / `save`, `read` | a leaf; a remembered rect is used only when enough of it is on a connected screen (`tests/test_placement.py`) |
| `watchdog.py` | the stall log and the render watch | `Watchdog`, `RenderWatch` | never stops the show; cold, like `app` (`tests/test_watchdog.py`) |
| `offline.py` | the tests' offline analysis driver | — | part of the audio stack's boundary (`tests/test_audio_boundary.py`) |

---

## 5. Subsystems

How the modules above work together where a feature crosses several.

**Audio → bands → routes → params.** `AudioEngine.step` pulls frames
from its ring buffer through `Analyser` into `Analyzer`, whose `lanes`
(one per band, below `CEIL`) are the `lane:` source. `AudioEngine.publish`
puts the bands' names and rests on the router. `band.*` params are views
onto the analyzer's objects; `control.Control` holds the selection and the
scenes. `Router.modulate` reads `lanes / CEIL` for each `lane:` row.
The band → plane map is routes, not code in the renderer:
`routing.legacy6_routes` makes one push row per band of `bands.BANDS`
onto `rot.rate.<plane>` — SUB → ZW, BASS → XW, MIDB → YW (the three W
planes), MID → XY, UPR → XZ, AIR → YZ — with each band's `dir` as the
sign. Most of the corpus loadable patches carry those six rows (the hands and LFO
loadable patches do not), and a loadable patch may re-aim them.

**The modulation patch** (plan 28). `Router.build_modgraph` reads the table
— the performer rows, their gates and `scale`s, the macros' subscribers,
each bank voice's knob params (plan 31: the LFOs', the envelopes'), the loadable patch's modifiers — into a `modgraph.ModGraph`;
`modgraph.order` sorts it, `modgraph.cycles` finds the loops, and
`Router._rebuild_modgraph` cuts each loop through no delay (its last cable
in table order off, a note for ROUTING's head) and turns the order into
a plan of steps: step a bank voice (`Bank.step_one`: an LFO, an envelope), step a modifier
(`modifiers.step` → its `mod:<n>` lane), run a param's rows and, if a
later step reads it, land it (`Param.apply` under
`Registry.begin_frame`'s mark). The plan is cached until `_modgraph_key`
moves. A modifier is declared into the registry when it is added
(`routing.declare_modifiers`: `mod.<n>.<p>`, group `mod`), held in
`Bindings.modifiers`, saved by the loadable patch (`loadable.MODIFIERS_KEY`, after
`routes`), watched by undo as one table part, and edited on ROUTING's
MODIFIERS strip or the GRAPH page.

**The GRAPH page** (plan 28). `graphview.build` makes one `View` from
the table, the registry, the Router, the device registry (read through
the `Device` protocol: `role`, `status`, `sources`, `layers`) and the
render graph the renderer last built (`renderer._graph`); `ui_graph.page`
draws it on one `imgui_node_editor` canvas and rebuilds it only when
`graphview.key` moves, refreshing the readings each frame. A device
with layers is one node per layer (the APC40 as *apc40* and *apc40
(SHIFT)*, its latch read from `Bindings.layer_of`); a loadable patch's desk
template is one subgraph node; a role the meta controller lacks is a grey
placeholder. A drag or a delete is dispatched by its pins' type
(`ui_graph.CREATE`, `DELETE`, `DELETE_NODE`) to `graphview.Edit`: a
value or trigger cable becomes the table's own call (`Bindings.add`,
`move_route`, `remove`, a desk or pad Learn, a macro subscriber, a
modifier input), so undo, the loadable patch's dirt, the referee and the
meta controller / loadable patch split are the table's; an image cable becomes a new
`graph` section, read back through `read_graph` and landed by
`GraphSection.land` (one undo step, the renderer rebuilt). Positions
live in the loadable patch's `layout` (the look's nodes) and the show's (the
meta controller's). The page writes no param but through those calls. Apart from
output 1's backdrop and the node thumbnails below, it draws nothing of the
render (it reads `Renderer._graph`).

**Nodes as pictures** (plan 37). On the GRAPH page, every node that makes
a picture is drawn as that picture, collapsed or expanded: a thumbnail in a
16:9 box at the node's width, under the title line.

- **What is shown.** `graphview.THUMBS` (with `thumb_of` for any kind
  whose `OUTPUT` is `IMAGE`) says how each kind shows a picture:
  - its own picture;
  - for a shape or a cloud, its scene's picture, faint;
  - for a hands node, its layer;
  - for an output, its window: output 1 is the page's existing `Preview`,
    outputs 2–4 are their `Handoff.frame`.

  The modulation side stays text.
- **Wanted only on screen.** Each frame, the page `want`s the nodes that
  are drawn (not hidden by **preset only**) and that overlap the
  editor's visible canvas rect (`ui_graph.thumb_wants`).
- **Made at the frame's end.** `Renderer._thumbnails`, called last in
  `_for_the_panel`, asks each wanted node's picture through
  `render.thumb_source`, which goes over `graph.picture`. It never reads a
  node outside `Graph.pulled`. It copies each picture into
  `outputs.PreviewTextures`, a texture keeper beside `Preview` that knows
  nothing of the graph: one 16-tap downsample pass to `THUMB_PX` = 192
  on the long side.
  - While it asks, the GPU timer is muted and the frame's `stats` are
    restored, so the outputs and SYSTEM's per-node lines are the frame's
    own.
  - It flushes the context when it copied anything.
- **Lifetime.** A name unwanted for a second is dropped. A node that made
  nothing is dimmed, then black a second later. SYSTEM reports
  `thumbnails · N copied · K repainted · M kept`. A node that painted
  straight into its consumer is repainted at full size for its thumbnail,
  which costs more.
- **While the projector is held** (plan 38). The thumbnails come from the
  renderer the canvas reads (`ui_graph.picture_sources` over
  `hold.canvas_renderer`): the preview renderer, with its own
  `PreviewTextures`, once the preview has been drawn, so every node shows
  what TAKE would put up and the main renderer copies none. Output 1's
  node shows the program's picture, `panel.monitor` (the PROJECTOR inset).
  With GRAPH closed nothing is wanted and nothing is made (register rows
  498, 499).
- **The hover.** On the picture, the hover is `graphview.picture_hover`:
  the title, `summary`'s lines, `W×H picture`, and `gpu N.NN ms` from
  `Renderer.stats["gpu_ms"]`.
- **The tint switch.** The head's last chip, **pictures · tint cables**,
  is off by default and is page state only. Lit,
  `PreviewTextures.want_hues` reads one thumbnail's dominant hue a frame,
  asynchronously (a 16×16 pass into a pixel buffer, collected next frame,
  each node once a second). `ui_graph.tint` then leans each picture
  cable's red by at most 20° toward that hue, and `COLOURS` is unchanged.
- **The area rule.** `graphview.laid_areas` puts an effect-area node whose
  consumers sit left of the effects in the leftmost consumer area not left
  of what feeds it. It names the area only, never a position, so no cable
  runs backwards across areas (`tests/test_graph_areas.py`).

**Shapes: polytopes, surfaces, 3D and 4D.** `geometry.SHAPES` holds 101
shapes, append-only. Three fields say what each one is:

- `Shape.cells` is the polytope's cell count, and **0 marks a surface
  or a 3D shape, not a polytope**. The Clifford torus (shape 18) has
  cells 0 and is a native 4D surface; shapes 19–26 are surfaces built
  from trig equations, each with explicit face cycles (`"F"`).
- `Shape.dims` says, honestly, whether it is 4D or 3D (plan 28): 4 —
  real w-extent, shapes 1–18, the 4-polytopes from plan 22's
  shortlist, the Hopf fibration and the Celestial tesseract scene; 3 — a 3D shape at w = 0, shapes 19–26 and the rest
  of the catalog. Nothing is invented for a w a shape does not have.
- `Shape.family` is every shape's kind (regular polytopes, Platonic
  solids, scenes …); `geometry.MENU` orders the families into the Shape
  menu's sections, 4D, 3D and Scenes. `Shape.layers` makes a shape a
  scene of several.

A 3D shape is turned by XY, XZ and YZ only: `view_angles` drops its W
angles, so whatever drives the W planes (SUB, BASS and MIDB, with the
map above) does nothing to it. Its depth cue reads its depth toward the
3D camera (`view_depth`: z after the camera's yaw and pitch), since its
w is 0. `render.py` imports `shape_world` (`shape_view`'s rules through
the one camera: it reads `view_angles`, `is_3d` and `view_depth`); nothing
it draws reaches a param (§2, Drawing). Plan 22's lifts (seven shapes
given an invented w) and its mask (the Heart's W planes folded onto 3D
planes) are gone.

**The desk (APC40).** Two layers in one table: the **patch** layer (the
loaded patch's `desk`) and the **global** layer (the meta controller's), plus
**invariant** rows that mean the same on both (SHIFT, the faders, the
crossfader, the bank pads, OVERDUB). SHIFT latches the
layer (`desk.shift`). `Bindings.dispatch` sends a message to the invariant
rows or the up layer's, never both; `Bindings.active` is what the desk
lights and what `ui_desk` draws. A loadable patch load replaces the patch layer
(`Bindings.set_desk`) and drops to it; at the next `MidiIO.redraw`, a
fader's catch is cleared only if its param moved, and every control that
lost its row goes dark. The bank of twenty-four (`library.SLOTS`) is
F1–F8 plus clip row 1 for slots 1–8 (`params.F_KEYS`) and clip rows 4–5
for slots 9–24 (`apc40.BANK_PADS`); the pads are the desk's, set there
alone (the PRESETS page shows none since 2026-10-28). **Several desks** (plan 27): each
MIDI entry is a `MidiIO` with its role and profile. One desk owns the
unqualified rows and SHIFT — the first whose profile is `bindings.json`'s
(`DeviceRegistry.midi_roles`, told to the table as `Bindings.midi_roles`
before any desk opens); any other desk's rows are `cc@<role>:…`,
dispatched only to it (`Bindings.serves`), on a layer of its own
(`Bindings.layer_of(role)`, the patch layer: no SHIFT). A loadable patch load
drops every desk to the patch layer. `ui_desk.py` draws the APC40 only.

**Devices.** `app.main` builds one `DeviceRegistry` over `config.toml`'s
`[[devices]]` (`config.devices`; the old tables translated) with a
`Context` (the registry, the table, the Learn, the audio engine, the
hands setup, the notes, the home), opens each device behind its entry
and hands the registry to the router (`Router.use`) and the Learn
(`Learn.devices`). A listener re-points what holds an adapter — the
panel's `midi`, `pad` and `hands`, the ghost's `source` — whenever the
list changes. The registry polls, feeds and sends in the frame's three
slots (§2), retries a device whose `open` raised on the `Ports` schedule,
leaves a `lost` device to reconnect itself, watches `config.toml`'s
mtime every `WATCH_FRAMES` frames (only the device list is re-read; a
bad edit keeps the old list), and closes every device last listed first
in `Host.adapters`. The SYSTEM page draws `DeviceRegistry.lines()`, one
per device. The hot reloader's swap targets come from
`DeviceRegistry.targets()`.

**Sinks.** A sink port is `<role>:<channel>` (a `Port` in a device's
`sinks`). A sink row (`param:<id>` or `lane:<i>` / `lane:*` →
`<role>:<channel>`, op `send`) lives in `bindings.json`; the device's
`send(reg, analyzer)` runs after `reg.apply`, reads `routing.sink_values`
over the enabled rows on its role and pushes them through
`bridge.Sender` (quantise, change-gate, rate-limit, encode). The bridge
is one device with an `ext` source half and this sink half; a `midi-out`
entry (`hands-daw`) is a sink alone that also carries the hands' DAW
messages (`HandsIO.carry`) and resyncs the DAW after a reconnect. An
entry's old `send` list becomes its rows once
(`DeviceRegistry._seed_sinks`, marked `"sinks_seeded"`).

**Point clouds.** A `devices.PointCloud` (read-only N×3 float32 points,
`t`, a counting `frame`, `bounds`, optional colours) is published on the
registry, not the Router: `DeviceRegistry.clouds` maps `cloud:<role>` to
each open device's latest frame. The `cloud` kind plays a version-1
`.npz` (`write_clouds` / `read_clouds`) at its own rate against the frame
clock. The renderer is handed the registry (`Renderer.cloud_source`):
each listed `cloud` device adds a `graph.PointCloud` node to the default
scene, drawn solid in the shared camera (Render graph, below).

**Hands.** `hands/core.py`'s `LeapSource` (or a `TapeSource`) gives
features and skeletons; `HandsIO.poll` shapes twelve axes, two presence
lanes, eight pinch switches, the dance sources, the grabs and the room
lanes (`Layout`),
feeds them as `hand` (and the pair as `hands`), publishes the name map,
may complete a Learn, and makes the frame's DAW messages, which wait in
`HandsIO.outbox` for the `hands-daw` sink to carry (the instrument opens
no MIDI port). `hands/device.py`'s `HandsDevice` makes that one call from
the registry's feed slot. The ghost hands read `HandsIO.skeleton` raw
through `renderer.ghost.source` and are drawn as a geometry of the render
graph (below); they are not a source.

**Face patterns.** `shaders/patterns.glsl` paints the faces, one of
seventeen modes (`view.pattern`), reading eight inputs, `pattern.mod.0–7`
(0–2.6, 1.0 the design). Each input means one kind of change on every
mode — 0 SCALE, 1 GLOW, 2 WARP, 3 SPEED, 4 COLOUR, 5 SHARP, 6 HUE,
7 SPREAD — and `patterns.py` is where the names, the meanings and what
each does per mode live: `params` takes the labels and tips from it, the
FACES page (`ui_patterns.py`) the per-mode phrases, and the shader reads
the inputs only through named accessors that the tests hold to it. The
factory routes put lane *i* on input *i* at `routing.PATTERN_DEPTH`
(0.35) on a base of 1, so an input rises by 0.35 × the band's out; the
FACES page's "+ source" offers use the same depth. SPEED is not read by
any mode: the renderer integrates it into the patterns' clock
(`Renderer._pattern_clock`, `u_ptime`), so a moving SPEED never jumps a
pattern's phase. METER and PULSE also read the analyzer's lanes directly
(`u_levels`, §2). While the FACES page is open the renderer draws a
swatch of each mode in turn for its chips.

**Effects.** Each `shaders/fx/*.glsl` file is an effect; its uniforms
become `fx.<name>.*` params (`fx.declare`). Since plan 33 there is no
`fx.<name>.order`, no `fx.<name>.target` and no faces chain: an effect is
a `graph.Effect` node where the loadable patch's graph wires it (the run
`frame → … → fx.image`, a branch onto `shape.faces`, `pattern.media`,
`backdrop.image`, an output or an `aux`), running its pass
(`FxChain.run_one`) when `FxState.live` says so and reading through when
not. `fx.face_map` says whether the faces show a wired picture per face
or in screen space. The FX page lists the graph's effect nodes, grouped
by where each ends, and edits no structure; GRAPH does that (§2, "The
free graph").

**Look-back and dream.** `Lookback` keeps a history of scene textures and
composites echoes over the frame; `DreamWorker` (only with
`[dream] enabled`) takes frames from the history on its own thread and
returns dreamed ones without ever blocking the frame. What the history
captures is wiring (the graph's `capture` node). Since plan 36 the
look-back and the dream are two nodes ("The WYSIWYG graph" below): the
dream is no longer pulled by the look-back's run.

**Render graph.** `graph.build_graph` builds the frame as nodes from
the renderer's `Wiring` alone (plan 35/36: only what a wire reaches; no
switch builds a node, a window's mutes are read each frame), the meta controller's
standing wires (`BusCuts`: the bus and cloud cables, the loaded patch's
cuts since plan 44 D3) and the effect
files present (one `Effect` node per wired instance);
`Renderer._graph_for` keeps it
until one of those changes, and `Graph.evaluate` runs it (§2). The shape
and the hands share one camera: the CPU takes the shape to 3D
(`geometry.world_points`: `rot.*`, the 4D divide, the yaw/pitch
turntable), the vertex shaders through `u_model` (`camera.zoom`,
`camera.pan` in world units) and `u_vp` (the eye, `eye.*`, the loadable patch's since plan 43 C2); the
hands through `ghost.shared_camera` (the eye, and the Leap calibration in
`hands.json` fitted to the meta controller's reference eye). Edges and points are quads with a real depth; the scene
has a depth attachment, the see-through shape writing its visible
surface after its colour. A loadable patch's `graph` section
(`loadable.GraphSection` → `graph.read_graph` → a `GraphSpec`) sets the
renderer's `Wiring` — the hands in the scene or as a layer, solid or as
lines; the layer over, added or depth-aware; the history with or without
the hands — the effect instances the chain holds
(`FxState.set_instances`), where an effect is placed (`after` /
`into` a node, `Wiring.placed`: plan 30) and the wires (`Wiring.wires`,
outputs as nodes, composites: plan 28); a second hands node is its own `Ghost`
(`Renderer.ghost_of`) over a `GhostState` the loadable patch section keeps, so
the render stack never declares a param. The golden frames
(`tools/golden_frames.py`) pin every corpus loadable patch's picture
(`tests/corpus/presets/`) in every state to the byte on the gate Mac, and the fixture loadable patches' (the
placements and the wires among them).

**Outputs.** `config.toml`'s `[[output.screens]]` lists up to
`outputs.MAX_OUTPUTS` render outputs (no list is one). `app._windows`
makes one `outputs.Slot` per entry: output 1 is the render window, each
later one a window in its share group with its own `Presenter` and its own
`overlay.Output` (no params). Each opened output gets `output.N.*`
switches (`overlay.register_switches`); `placement.py` remembers one rect
per output. `output.N.flip_x` / `.flip_y` (plan 23 WP1) mirror an output's
picture as its last step, inside its fit rect: `SHOW_FS` and the ghost's
`COMPOSITE_FS` on output 1, `PRESENT_FS` (through `Handoff.flip`) on a
later one, never the hands-through pass into the effects. A flipped output
is never drawn direct, and the render window's mouse is mirrored by
output 1's flags (`app.flipped`).

**Loadable patches, shows, the library.** A **loadable patch** (`hyperspace.preset/2`) is
the performance: values, routes, desk, macros, module labels. A **show**
(`library.Project`, `hyperspace.project/2`) is the session: meta controller values,
the desk's bank of loadable patch names, the meta controller's wires and a `startup` loadable patch
(kept in the file; nothing on the panel sets it). `Library.home` is the
**library root** — the home, or the folder `[library] path` names (plan
25: a cloud-synced folder two machines share) — and `Library.machine` the
home for this machine's files; app.main builds `Library(path,
machine=home)` and reads `bindings.json`, `windows.json` and the stall log
from the home. The launch opens the show opened last on this machine
(`<machine>/last_show`); a fresh library opens an unsaved `untitled` show
with every pad empty and nothing loaded. A loadable patch file is copied to
this Mac's trash, `<machine>/trash/<group>/[<folder>/]`, before a save
overwrites it or a delete removes it (plan 48: never into a shared
library); the trash is listed, restored and emptied from the PRESETS
page's list. Loadable patches may sit in folders under `presets/` (plan 48): the
list walks them and names each `folder/NAME`, and the bank points by
that name. **One tier** (2026-10-28): nothing ships with the app and there is
no hidden list — every loadable patch is listed, loaded, renamed and trashed
alike; the loadable patches the build used to ship are the goldens' corpus
(`tests/corpus/`), read by no app code. Writes
are atomic (a dot-named temp file, then `os.replace`), and a cloud
client's conflict copy is listed under its own file stem. A library
folder named but missing at launch (`Library.missing`) is never created:
every list is empty and every write raises `LibraryError`.

**Media (plan 32).** Sources become frames off the frame thread and are
uploaded on it. The threads, by owner:

| Thread | Does | Ends |
|---|---|---|
| `media-pool*` (3 workers) | still decode, thumbnails, folder scans, live discovery (`discover()` every 2 s), joins of released live sources | `pool.shutdown` at exit |
| `media-video-<name>` | one video's PyAV decode, driven by `want(pos)` from the transport; stays within one frame of a `close()` | `close()` joins it |
| `media-audio-<name>` (plan 45 V1) | the same video's audio track, PyAV-decoded and resampled to float32 stereo 48 kHz into memory (`video.Soundtrack`), always from the original file; **started only by `enable()`** (something asks for sound; V2's toggle — a window decode demuxes the video's packets too, so an unheard track reads nothing); follows the same `want(pos)` — the transport is the one clock — holding the track whole to 120 s, else a 120 s window around the position, one buffer a window (46 MB; 92 MB while one is re-made); `read(at, n)` from any thread is zeros where nothing is held and never blocks, and `status` is `fetching` whenever the wanted position is outside what is held; nothing plays yet. Both video threads are a `_Follower`: a stop event per start, so a thread `close` gave up on never resumes beside a new one | ends by itself once a whole track is in; `close()` / `disable()` join it within the video's budget |
| `media-live-<id>` | a live feed's reader (`NdiReader`: `frame_sync.capture_video()`; `CameraReader`: PyAV `avfoundation`), capped to 1280×720, holding its last frame 1.0 s | released 5 s after nobody holds it, or at exit (1 s in all) |
| `media-discover-syphon` | the Syphon server list (the main thread's `glfw.poll_events()` pumps the run loop it needs) | with the kind |
| `media-proxy` | one cancellable transcode at a time | `proxy.cancel_all()` at exit |
| `media-mixer-open` (plan 45 V2) | opens the mixer's output stream the first time a channel's sound is on (a CoreAudio open off the frame thread) | when the open returns; `Mixer.close` waits 0.5 s for it |
| PortAudio's callback (plan 45 V2) | `Mixer._callback`: sums the voices the frame thread handed in, each from its read head (V4: slewed toward the transport, resampled by its speed); never blocks, never raises, never moves a transport | `Mixer.close` aborts and closes the stream at exit |
| `media-closer` | closes sources a channel dropped, and runs a soundtrack's `disable()` when a channel's sound goes off (plan 45 V2) (a close can sit in `av.open` while a cloud file downloads) | after 2 s idle; `close()` shares a 1.5 s budget |
| `media-folder-probe` (daemon) | the 64 KiB read that decides `ready` or `fetching`, waited for 0.5 s by the scan | when the read returns |
| `media-ndi-out-<name>` | NDI send of the frame the PBO readback left | `close()` joins it |
| `segment-<name>` (plan 39) | one segment node's model (Vision on the Neural Engine, or torch): sleeps on a condition until a frame is submitted, runs the newest (latest wins, drops counted), publishes the matte by one reference swap; an error is kept and said, never raised | stopped, never waited for, `SIZED_KEEP_FRAMES` frames after no graph holds its node (the thread closes its backend itself); `Renderer.close` joins every worker within 1 s at quit and restart |

The frame thread: `MediaState.poll` (step 2), `MediaTextures` uploads
(a channel is written only when a consumer reads it and its `(frame, t)`
moved; a Syphon rectangle texture is copied on the GPU into a 2D one), the
`media.<c>` node's fit pass (once a frame however many read it), the
backdrop and the faces' sampling, `_publish` after the frame (Syphon out:
a texture handed over; NDI out: a PBO read issued, the one from a frame ago
copied only if the sender is idle). A source hands its newest frame over
in a `Latest` (a reference swap: a writer never waits, a reader never sees
a torn frame, older frames are dropped). A GPU source (`gl_poll`, Syphon)
is polled only on the frame thread, where the render context is current.
The panel never opens or reads a source: the MEDIA page draws the
renderer's pictures (`Renderer.media_shown`) and thumbnails the renderer
uploaded for it (`UiTextures`).

**Vision (plan 39).** A `segment` in person mode is the one node whose
picture comes from another thread besides the dream: its worker
(`segment-<name>`, above) is made by `Renderer.segmenter(name)` on the
node's first need from `[segment]` (`backend` auto / vision / torch,
`weights_dir`, `device`), kept by node name across rebuilds, and only on
the program renderer (`segment_cfg`; the hold's preview has none). The
frame thread hands it a frame (the channel's own array, or a readback) and
uploads a result only when its index moved, smoothed per result in float
(`segment.smooth`) and feathered only when the result or the radius
changed. Vision's matte, a fixed 4:3 size per level stretched over the
image, is resampled to the frame's aspect on the worker, and every Vision
run is under its own `objc.autorelease_pool` — the worker is a plain
Python thread with no pool, and without one each job leaked its frame's
NSData copy for the life of the process (~1 MB a job; 140 GB over a
half-hour set with two segment nodes, 2026-11-01;
`tests/test_segment.py::test_vision_frees_each_jobs_memory`). Motion mode
runs no thread. The node says its state: `256×144 · Vision fast · a frame or
two late · 29 fps`.

**Undo.** `Undo.tick` (frame step 4) compares a fingerprint of the watched
bases (`undo.watched`: persisted, not an alias, not a trigger, not the
`tempo` group), the table's performer and patch-layer rows, the macros
and the band layout; a change opens a step and `SETTLE_S` of quiet closes
it. A replacing action — a load, a Learn, a ROUTING ×, a reorder — calls
`undo.push(label)` first. `library.Marks` lets an undo of a load put back
what the library calls loaded.

**Hot reload.** `hotreload.MODULES` lists every package module but the
cold core, leaves first; a save re-executes the changed module and every
one after it, then re-classes live instances in place. `app`,
`hotreload`, `offline`, `watchdog` and `segment` (plan 39: its worker
threads outlive a reload) need a restart; `masks` reloads before `render`,
which drops its cached passes (`Renderer.on_reload`).
