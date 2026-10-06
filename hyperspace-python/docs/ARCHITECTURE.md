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
 keys · mouse · pad · MIDI desk ──rows──▶ Param.set* ──▶ BASE ─┐
 panel widgets · presets · undo ─────────▶ Param.set* ──▶ BASE ─┤
                                                                ├─▶ Registry.apply() ─▶ live objects ─▶ render stack
 audio lanes · hands · LFOs · DAW in ──feed──▶ Router.modulate ─┤      (once a frame)    (ViewState,    (reads only)
                                    (one performer row per param)▶ OFFSET                FxState, …)
```

| Component | Modules | Owns | Writes | Boundary (held by) |
|---|---|---|---|---|
| **Registry** | `params.py`, `tapers.py` | every `Param`: id, kind, taper, flags, base, this frame's offsets | the live objects, once a frame, in `Registry.apply()` | never imports `midi`, `bridge` or `dream` (`tests/test_params.py::test_core_does_not_import_the_midi_adapter`, `tests/test_bridge.py::test_core_does_not_import_the_bridge`, `tests/test_dream.py::test_core_does_not_import_the_worker`). It does import `fx`, `ghost`, `lookback`, `geometry`, `analyzer` and `bands` for their state classes and constants |
| **Routing table** | `routing.py` | `Binding` rows, `<home>/bindings.json` (the session's controls), the referee, the desk's layers, the macros, the per-frame modulation pass | offsets, through `Router.modulate` → `Param.modulate` (the only call site in the package); bases for key / pad rows (`routing.act`) and macro base subscribers | imports nothing above it — no `ui`, `app`, `hands`, `midi`, `bridge`, `learn`, `dream`, `hotreload`, `library`; `glfw` and `gamepad` only lazily, to resolve key and pad names (`tests/test_routing_boundary.py::test_routing_imports_nothing_above_it`, `::test_importing_routing_pulls_in_no_adapter_or_panel`, `::test_only_router_modulate_calls_param_modulate`) |
| **Learn** | `learn.py` | the armed param and what it waits for, the held Replace / Keep question, the picked desk control, Unbind | table rows, through the table's edit doors | imports only `undo`, `params`, `routing`; the device profile arrives as an argument (`tests/test_learn.py::test_learn_control_needs_no_adapter`) |
| **Input adapters** | `midi.py` + `apc40.py`, `hands/`, `gamepad.py`, `bridge.py`, `app.Keys` / `app.Mouse` | a device and its pickup state | MIDI / keys / pad / mouse: the **base**; hands and bridge: only `Router.feed` | the core never imports `midi` or `bridge` (above); `hands/core.py`, `signal.py`, `tape.py` import nothing from the package and `hands/panel.py` is the only piece that knows the host (`tests/test_hands_boundary.py`) |
| **Audio source** | `audio.py`, `analysis.py`, `analyzer.py`, `bands.py` (and the tests' `offline.py`) | capture or file playback, the FFT, the N band lanes | `Analyzer.lanes` (read by `Router.modulate`), the lanes' names (`AudioEngine.publish`) | imports only itself and `tapers` (`tests/test_audio_boundary.py`) |
| **LFOs and clock** | `lfo.py`, `tempo.py` | four oscillators, one tap-tempo clock | `Router.feed("lfo", …)`, its labels and rests | import nothing from the package; registry, router and clock arrive as arguments (`tests/test_lfo_boundary.py`) |
| **Render stack** | `geometry.py`, `view.py`, `render.py`, `glsl.py`, `fx.py`, `lookback.py`, `dream.py`, `ghost.py`, `outputs.py`, `overlay.py`, `shaders/` | GL resources, `ViewState`, the frame history, the dream worker, the faces' picture, the outputs' pipelines, the one wall clock (`Renderer.now`) | the screen; `ViewState.integrate` writes `ang` directly | reads parameters, never writes one: `render.py` and `fx.py` import no `params`, `routing`, `library`, `preset`, `undo`, `control` (`tests/test_render.py::test_the_render_stack_imports_no_registry`); `outputs.py` imports `moderngl` and `glsl` only (`tests/test_outputs.py::test_outputs_imports_nothing_from_app_ui_or_params`); `dream` is imported only by `app._open_dream` behind `[dream] enabled` and is the one module that imports `torch` (`tests/test_dream.py::test_core_does_not_import_the_worker`) |
| **Panel** | `ui.py`, `ui_*.py`, `hands/panel.py`, `control.py` | imgui state, page selection, the Replace / Keep modal, the routing page's edits | param **bases** through `Param.set*`; table rows through the table's edit doors and `Learn` | only `app`, `hands/panel.py` and the `ui*` modules import `ui*`. By convention: no test holds it |
| **Library** | `library.py`, `preset.py`, `config.py`, `library/` | the home folder, module presets, presets, shows (projects), the bank of twenty-four, the trash, `hidden.json`, `config.toml` | bases through `Registry.restore`; a preset load replaces the table's performer rows, desk layer and macros | `library` imports `params` and `undo` (and `routing`, `preset` lazily), never `homegit` or `config` (`tests/test_app_boundary.py::test_homegit_is_a_leaf_and_the_library_never_imports_it`) |
| **Undo** | `undo.py` | the undo and redo stacks, the last settled state | bases (`Registry.restore`) and the table's preset parts, on ⌘Z / Ctrl+Z only | a leaf: imports nothing from the package and never touches `modulate` or `feed` (`tests/test_undo.py::test_undo_imports_nothing_from_the_package`) |
| **Host** | `app.py`, `hotreload.py`, `placement.py`, `homegit.py`, `watchdog.py` | construction order, the frame loop, the windows and render outputs, the reload watch list, the stall log, the home in git | bases for the relative writers (↑ / ↓, pad sticks); no key of its own but `app.LOOP_KEYS` | the only importer of every optional adapter, each behind its config gate (`_open_midi`, `_open_bridge`, `_open_hands`, `_open_dream`, `_open_homegit`, `_open_pad`); importing `app` imports no gated adapter, no `torch`, no `leap` (`tests/test_app_boundary.py::test_importing_app_leaves_every_gated_adapter_unimported`); `placement` and `homegit` are leaves (`tests/test_placement.py::test_placement_imports_nothing_from_the_package`, `tests/test_app_boundary.py::test_homegit_is_a_leaf_and_the_library_never_imports_it`) |

**Everything points at the registry; the registry points at nothing
above it.** Adapters and sources feed the router; the router writes
offsets; the panel, the desk and the library write bases; the render
stack only reads.

**Leaves** — modules that import nothing from the package, so anything
may import them: `analysis`, `tapers`, `undo`, `placement`, `homegit`,
`geometry`, `tempo`, `lfo`, `glsl`, `gamepad`, `apc40`, `watchdog`,
`hands/signal.py`, `hands/tape.py`. Near-leaves: `outputs`, `fx` and
`lookback` import only `glsl`; `view` only `geometry`.

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
| 0 | `clock.tick(now)`, `reloader.poll()`; Esc / Q quit; ⌘R restarts (claims R's edge first) | — |
| 1 | `router.keys(keys)` — key rows, R, F1–F8 / ⇧F1–F8, ⌘Z among them; ↑ / ↓ ride `view.depth4` (`_ride_depth`) | bases |
| 2 | `pad.poll()`, `router.pad(pad)`; sticks and triggers through `nudge` / `scale` | bases |
| 3 | `midi_io.poll()` — the rows of the layer that is up and the invariant rows; knob glides; an armed desk Learn takes its candidate message | bases |
| 4 | `router.follow_macros()` — a macro whose base moved sets its base subscribers' bases | bases |
| 5 | `undo.tick(now)` — compares the watched bases and the preset's table with last frame's | nothing |
| 6 | `hands_io.poll(dt, learn, router)` — feeds `hand`; may complete a hand Learn | feed |
| 7 | `output.apply()` for every output; `renderer.bg_alpha` and `renderer.dim` handed over | window state |
| 8 | `mouse.poll(shift)` — orbit, pan, zoom through `nudge` / `scale` | bases |
| 9 | `audio.step(dt)`, `audio.publish(router)` | lanes |
| 10 | `bridge_io.step(…)` — feeds `ext`, sends lanes out | feed |
| 11 | `lfos.step(dt, now, clock)`, `lfos.publish(router)` — feeds `lfo` | feed |
| 12 | `router.modulate(chain)` — every live performer row calls `p.modulate(offset)` | offsets |
| 13 | `reg.apply()` — base + offsets onto every live object | objects |
| 14 | `view.integrate(dt)` — `ang += rate · dt` | an object, directly |
| 15 | `draw_render` — every render output (below) | the screens |
| 16 | `draw_panel` — the control window | bases, rows |

Rules that follow from the order:

- **One-frame lag.** Everything a performer moves lands once, in
  `reg.apply()`. A source that reads a parameter — an LFO reading its own
  `depth`, a route scaled by a macro's depth subscriber or by
  `master.gain`, the bridge sending `eff_norm`, `output.apply` — reads what
  `apply()` wrote **last** frame. There is no recursion, because nothing in
  the pass reads a value it is about to write
  (`tests/test_lfo.py::test_an_lfo_owning_another_lfos_depth_changes_its_output_next_frame`,
  `tests/test_routing.py::test_a_macro_owned_by_a_hand_scales_a_lanes_push_one_frame_later`).
- **Base before offset.** Every scene-setter runs before `router.modulate`
  (the panel's edits are the previous frame's tail), so a base write and
  the offsets on it combine in one `apply()`. The one writer after
  `apply()` is `ViewState.integrate`; `Param.apply` adopts that write as a
  delta on the base next frame
  (`tests/test_modulation.py::test_a_direct_object_write_is_adopted_into_the_base`).
- **The undo watcher sits between the scene-setters and the feeds**, so it
  sees every base this frame's keys, pad, MIDI and macros wrote and no
  performer has run. It writes nothing; `edit.undo` / `edit.redo` are
  key-row triggers in step 1 (`tests/test_undo.py::test_an_idle_app_makes_no_step`).
- **Guards.** The MIDI poll, the macro step, the undo tick, the hands
  poll, steps 9–14 as one block, the render draw and the panel draw are
  each wrapped: hot-reloaded code that raises sets
  `reloader.runtime_error` (cleared by the next clean frame) and the loop
  goes on (`tests/test_app_boundary.py::test_a_raising_step_is_recorded_and_the_windows_still_draw`).
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
- **Session params are declared before the show lands.** `app.main` calls
  `app._desk_table` (`routing.register_desk`, then
  `slew = routing.SLEW_DEFAULT_S`) and `overlay.register_switches` before
  `library.attach(reg)`, which takes the registry as it stands as "fresh"
  and then lands the show's session values
  (`tests/test_app_boundary.py::test_the_app_starts_with_knob_smoothing_at_80_ms_and_a_show_keeps_its_own`).

### Drawing: one frame, a picture per output

`app._draw_render` makes output 1 current, builds one `outputs.View` per
opened output (output 1's with `target=ctx.screen`, a later output's with
its `Presenter`) and calls `Renderer.draw_outputs(s, w, h, dpr, views)`.
`Renderer.draw` is the same call with one default `View` on the bound
framebuffer. In `Renderer._draw_frame`:

```text
ONCE A FRAME (output 1's context)
  the face picture   _face_picture — only while an effect is aimed at the faces
  the scene pass     into the scene target; then resolve and the cover mask
  look-back          lookback.tick, pull; fx.tick
  the hands' layer   Ghost.layer — only if some view shows hands
  route every view   outputs.route(switches, fx_active, hands_visible)
ONCE PER DISTINCT PIPELINE (SCENE, SCENE_HANDS, HANDS)
  look-back composite [+ Ghost.composite] [+ the frame's effect chain]
  → the view itself when it is the pipeline's only consumer at the frame size, else a frame texture
  then lookback.capture(scene.tex) exactly once, after every pipeline
ONCE PER VIEW
  the picture (direct | 1:1 | letterboxed by outputs.fit) — or an outputs.Handoff for a presenter
  hands over it (Ghost.composite), the readout layer (Ghost.composite_readout)
  dim: Renderer.dim × the view's own dim, when under 1 (Renderer.dim_pass)
EXIT  views[0].target bound again with its rect and blending, a raise included
THEN in app._draw_render: glFlush (only with a later output); each later output
  Presenter.present then swap; output 1 swapped last
```

What the order guarantees, each held by tests in `tests/test_render.py`,
`tests/test_outputs.py` and `tests/test_ghost.py`:

- **The faces' effects are in the scene texture**, so the echoes and the
  dream carry them; the frame's effects never reach the history. With
  nothing aimed at the faces no face pass runs and the frame is
  bit-identical (`test_nothing_aimed_at_the_faces_is_the_old_frame_exactly`,
  `test_the_echoes_carry_the_faces_effects`).
- **The history holds only the scene**: never the frame's effects, the
  hands or the dim (`test_the_history_never_holds_the_hands_in_any_state`,
  `test_the_history_never_holds_the_dim`).
- **The effects' clocks advance once a frame** however many chains run
  (`FxState.advance_to`; `test_both_chains_in_a_frame_run_the_clocks_once`).
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
  records `View.error`; a raising presenter does not stop the frame
  (`test_a_raising_hands_pass_costs_no_output_its_frame_or_its_dim`,
  `test_a_raising_pipeline_leaves_its_views_on_the_ground_and_the_rest_drawn`,
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
param writes an **offset** through `Router.modulate`; `Registry.apply()`
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
| `persist` | belongs in a snapshot. Its group puts it in the **performance** part (a preset's `values`) or the **session** part (a show's `session`): `params.PERFORMANCE_GROUPS` / `SESSION_GROUPS`, `part_of`. On by default; never for triggers |
| `modulatable` | a performer may drive it. Off for rig settings (`output.monitor`, `.fullscreen`, `.overlay`, `.passthrough`, `.dim`, every `hands.*`), UI state, aliases, `tempo.tap`, the dream params whose change rebuilds something (`dream.gap`, `dream.res`, `dream.layer`), an effect's structure (`fx.<name>.order`, `fx.<name>.target`), the per-output switches, and `ghost.style` / `.mirror` / `.guide` / `.tethers`. A route onto one is dormant; a hand Learn onto one is refused in words (`Learn.learn_source`), and a preset's route onto one is dropped at load with a note (`Presets.load_doc`) |
| `alias` | a view onto another param (`band.sel.*` follows the selected band); never persists or modulates. `Registry.real` resolves it |

A continuous param has a **taper** (`tapers.py`): an integer position ↔
value map, exact on every detent
(`tests/test_control.py::test_taper_round_trip`). User setters snap to
detents; the modulation path does not, and a tapered position is
continuous between detents (`Param._taper_pos`), so a sub-detent base
survives under a performer.

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
| **Scene-setter** | the **base** | panel widgets (`Param.set*`); key / pad / hat rows (`routing.act` via `Router.keys`, `Router.pad`); MIDI rows of the layer that is up and the invariant rows (`midi.py`, `Bindings.dispatch`), including the knob **glide** (`MidiIO._aim` / `_glide`: `Param.set` between detents, then the row's `set_norm`); a macro's base subscribers (`Router.follow_macros`); `Registry.restore` (module presets, shows); a preset load (`Presets.load`); the relative writers — mouse, sticks, triggers, ↑ / ↓ — via `Param.nudge` / `scale`, which read the base; home (`Project.home`); undo and redo (`Undo._restore`) | every setter ends in `Param.set`, which writes the base while modulated (`tests/test_modulation.py::test_setting_a_modulated_param_moves_its_base`, `tests/test_app_relative.py`) |
| **Performer** | an **offset** | `Router.modulate` → `Param.modulate`, the only call site | `tests/test_routing_boundary.py::test_only_router_modulate_calls_param_modulate` (an AST walk). Adapters only `feed` |
| **Object writer** | the live object, bypassing `Param` | `ViewState.integrate` (`ang`), `camera.reset`, `control.Control`'s resets and their undo, `hands.core.mirror` on the non-modulatable `hands.*` | `Param.apply` folds the delta into the base next frame |

Consequences:

- **Scene-setters don't compete with performers.** A knob turned on a
  hand-owned param moves the **return value**, which shows when the hand
  lets go; it never prompts and is never blocked
  (`tests/test_routing.py::test_audit_3_a_knob_moves_the_return_value_under_a_hand`).
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
- **A preset's route may perform any modulatable param**, a session one
  included; a preset never sets a session *base*. The ROUTING page marks
  such a row "session" (`ui_routing.is_session_target`).
- **The output switches add no writer.** `output.N.scene` / `.hands` /
  `.through` / `.dim` (`overlay.register_switches`, one set per opened
  output) are rig settings — not persisted, not modulatable — whose base
  is the slot's `outputs.Switches`; the renderer only reads it
  (`tests/test_overlay.py::test_the_output_switches_are_rig_settings`).
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
**session** param only, such as `master.gain`), `when` (a gate), `rest`;
MIDI rows add `pickup`, `feedback`, `on`, `off`, `ring` and `layer` —
absent for an **invariant** control (the session's, one meaning on both
layers), `"global"` (the SHIFT layer) or `"preset"` (the loaded preset's
desk).

| Scheme | Address | Fed by | Reaches the param as |
|---|---|---|---|
| `key:` | a GLFW key name, with modifiers `SHIFT+` / `SUPER+` / `CONTROL+` (`routing.MODIFIERS`) | `Router.keys`, reading `app.Keys` | a discrete op on the base |
| `pad:` / `hat:` | a `gamepad` button / hat name | `Router.pad` | a discrete op on the base |
| `cc:` / `note:` / `pitch:` | `channel:number` (`pitch:` channel only; `*` any channel) | `MidiIO._handle` → `Bindings.dispatch` → `MidiIO._apply` | `abs` (soft pickup), `rel`, `rel64`, `step`, `toggle`, `set`, `momentary`, `fire`, `hold` — all base |
| `lane:` | analyzer band index | `Analyzer.lanes / CEIL` inside `Router.modulate`; names and rests from `AudioEngine.publish` | **performer** |
| `hand:` | a name: `left.x` … `right.yaw` as `[hands] dofs` spells them, `left.present`, `left.pinch.index` … `right.pinch.pinky`; a number still reads as that lane | `HandsIO.poll` → `Router.feed("hand")`; the name → lane map in `router.names["hand"]` (`hands.core.Layout`) | performer; a pinch may also gate |
| `ext:` | DAW lane 0–15 | `Bridge.step` → `Router.feed("ext")` | performer |
| `lfo:` | 0–3 (`lfo:0` is LFO 1) | `LFOs.publish` → `Router.feed("lfo")` | performer |

`routing.LANE_SCHEMES = ("lane", "ext", "lfo", "hand")` are the
continuous schemes; a row on one carries only `routing.MOD_OPS =
("push", "position")` (`Bindings._check` raises otherwise).

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
they and every LED the fire lit blink for `midi.BLINK_S`. The clip-stop
row's `preset.save_new` is its one use
(`tests/test_midi.py::test_the_bar_is_one_control`).

A named hand address resolves only through the map the hands adapter
published; a name the rig lacks is dormant, never another lane, so a rig
that reorders `[hands] dofs` keeps every preset on its axes
(`tests/test_hand_names.py`).

### 3.4 The one path

Every continuous source reaches a parameter through one pass,
`Router.modulate`, once a frame, over the enabled performer rows
(`Bindings.mods`) in table order:

1. **Find the lane** (`Router.lane`): a number is the index; a name is
   looked up in `router.names[scheme]`, cached against the map's
   identity. The vector is the analyzer's lanes for `lane:`, else
   `feeds[scheme]`. No vector, an index out of range, or a `NaN` reading
   (a hand out of the box) → the row does nothing this frame.
2. **Gate.** If the row has a `when`, the gate's source must be fed and
   read ≥ 0.5; a gate whose source is not live holds the row shut
   (`Router.gated`).
3. **Depth** `= value × scale × Π (from + m · (to − from))`: `scale` is a
   session param's effective value; each **depth subscriber** of a macro
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

| The target | A centred axis | A one-sided axis (height) |
|---|---|---|
| continuous, range centred on zero (`learn.centred_target`) | `push`, depth D | `push`, depth D |
| any other continuous param | `push`, depth D | `position`, depth 1 |
| enum, toggle, trigger, whole-number | `position`, depth 1 | `position`, depth 1 |

D is the session's `hands.learn_depth` (`learn.PUSH_DEPTH` when a caller
names none); a learned push has `rest = None`.

**Adding a source** is an adapter that, before `router.modulate`, does
what `LFOs.publish` does: `router.feed("<scheme>", vector)` (floats in
`[0, 1]`, `NaN` for a lane out of view, `None` when the device is gone)
and publishes `router.labels`, `router.rests`, optionally `router.gates`
and `router.names` (a new dict whenever its layout changes). The scheme
must be in `LANE_SCHEMES` for its rows to perform. The adapter imports
nothing from the package, never writes a `Param`, and is opened by
`app.main` behind a config gate.

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
through `test_a_preset_load_lists_what_it_dropped`, and
`test_every_factory_preset_names_real_params_with_one_owner`.

**Learn.** The host owns one `learn.Learn`, built over the live table
whatever the MIDI gate says. The right-click menu arms a param with what
it waits for (`Learn.arm(pid, want)`, `learn.WANTS`: `"desk"`,
`"hand:left"`, `"hand:right"`); `Learn.accepts(source)` is the one
question every completer asks. Three completers:

- **A hand** — `HandsIO._learn` → `Learn.learn_source`: the axis that
  moved, by name, with a pinch held as its gate. A non-modulatable target
  is refused in words. If another performer owns the target the pair is
  parked in `Learn.pending` for the Replace / Keep prompt and nothing is
  written. A landed learn takes the axis's other rows first: one axis,
  one param (`tests/test_learn.py::test_a_learned_axis_drives_one_param`).
- **A desk control** — `Learn.learn_control(source, profile)`, the one
  road onto the desk, called by `MidiIO._learned` with the message and by
  `ui_desk.click` with the control clicked. It binds a **preset-layer**
  row (`Bindings.bind(b, write=False)`), replacing whatever preset-layer
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

Every learn lands in the **loaded preset**: the table changes, the
preset's dirty dot lights (`Presets.signature`), and no file is written
until a save. **Unbind** is `Learn.unbind(ids, *, desk=True,
routes=True)`: the loaded preset's desk rows and every route on the param
and its real param, as one undo step; a session row is never removed.
`learn.bound(table, ids)` is what both Unbind and the menu's lines ask
(`tests/test_learn.py::test_unbind_removes_the_presets_desk_rows_and_every_route`).

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
  (`Router.follow_macros`, frame step 4). It names a persisted,
  non-alias **performance** param; any other is dropped with a note
  (`routing.base_refusal`;
  `tests/test_macros.py::test_a_base_subscriber_on_a_session_param_is_dropped_with_a_note`).
- a **depth** subscriber `{"depth": {"source", "target"}, "from", "to"}`
  multiplies that route's depth (§3.4 step 3).

So a performer that owns a macro moves only its depth subscribers; the
base subscribers follow the knob, the panel or a restore
(`tests/test_macros.py::test_a_performer_on_a_macro_moves_only_its_depth_subscribers`).
Two macros on one param: the later id wins. The subscribers and the
macros' values belong to the loaded preset; `bindings.json` never holds
them.

### 3.7 Where a controller's value goes

| You move… | It becomes… | Writes |
|---|---|---|
| a panel widget | `Param.set_position` / `set` / `toggle` | base |
| a key with a row (`B`, `⇧B`, `F`, `M`, `1–6`, …) | `Router.keys` → `routing.act` | base |
| `R`, F1–F8, ⇧F1–F8 | key rows (`routing.LOOP_KEY_ROWS`): `camera.reset`, `preset.load.k` → `Project.load_slot`, `preset.save.k` → `Project.save_slot`. Only the first `params.F_KEYS` = 8 slots have keys | base (a trigger) |
| ⌘Z / Ctrl+Z, with ⇧ | key rows → `edit.undo` / `edit.redo` → `undo.undo()` / `undo.redo()` | the bases and table parts that differ |
| Home, or the APC40's OVERDUB | `preset.home` → `Project.home`: the show's "starts on" preset loads | a preset load |
| ⌘R, Esc / Q, ↑ / ↓ | loop code (`app.LOOP_KEYS`): restart, quit, `_ride_depth` on `view.depth4` | ↑ / ↓: base, relative |
| mouse drag / wheel, a pad stick or trigger | `Mouse.poll`, the pad block of `app.frame` → `nudge` / `scale` | base, relative |
| a pad button or hat | `Router.pad` → `routing.act` | base |
| an APC40 knob or fader | the row of the layer that is up, or the invariant row → `Param.set_norm` (a fader after soft pickup; a knob caught at the ring just sent, `apc40.RING_REBASES_KNOB`, hand check 31); smoothed by `desk.slew` | base |
| an APC40 button | the rows its press went to — the release goes there too | base |
| SHIFT | the invariant row → `desk.shift`: flips the table's layer; every ring and LED redrawn, a control the layer does not map dark | the table's layer |
| the crossfader | invariant row → `output.dim`, the master dim (CC 0 black — hand check 55); a rig setting, 1 at every launch | base of a rig setting |
| a bank pad (clip rows 1, 4, 5) or a bank button | invariant `set` rows → `preset.select = k` → `Project.load_slot(k)` (`apc40.BANK_PADS`: 24 slots, `library.SLOTS`). Lights by `routing.led_level`: loaded, filled, empty | a preset load |
| a hold on the clip-stop row | eight invariant `hold` rows → `preset.save_new` → `Project.save_new`: a new user preset named from the loaded one (`library.next_name`), into the next empty slot | files, not params; no undo step |
| a macro's knob | its base → `Router.follow_macros` → each base subscriber's base | base |
| an analyzer band, a hand axis, a pinch, a DAW lane, an LFO | `lane:` / `hand:` / `ext:` / `lfo:` → its performer row → `Router.modulate` | offset (a pinch may instead gate a row) |
| right-click → Learn hand / Learn desk / click-then-map | `Learn` (§3.5) | the loaded preset's table |
| right-click → Unbind | `Learn.unbind` | the loaded preset's table |
| a ROUTING-page edit | the table in place: the loaded preset, its dirty dot | the table |
| a preset | `Presets.load`: every performance base in one `Library.restore`, then `Bindings.set_routes`, `set_desk`, `set_macros`, the base subscribers landed (`Router.follow_macros(force=True)`); session params never | bases and the preset's table |
| a module preset or show | `Library.restore` (a show: its session part) | base |

### 3.8 The binding file

`<home>/bindings.json`, schema `routing.SCHEMA`
(`hyperspace.bindings/3`), holds the **session's controls** only: the
keys, the pad, and the invariant and global-layer MIDI rows. Performer
rows, preset-layer rows, macros and values are the loaded preset's and
are never written there (`routing.is_session_row`;
`tests/test_routing.py::test_the_live_table_writes_only_the_sessions_controls`).
Nothing in the app edits a session row; the file is edited by hand. The
factory session table is exported to `hyperspace/bindings.default.json`
(`python -m hyperspace.routing`;
`tests/test_routing.py::test_factory_files_match_the_code`).

On load (`Bindings.load`) an older file is migrated and new factory rows
are added only where nothing on the table overlaps their control
(`routing.remap_factory`, `Binding.overlaps`); anything changed is
written back once, after a copy of the old file (`routing.backup`, never
over an existing backup). **No backup, no rewrite**: if the copy fails,
the file is left as it was and `Bindings.unbacked` stops every later
write that session. An unknown schema is never rewritten. A file that
still holds a preset's part is left for the first-launch migration
(`preset.migrate_home`), which moves it into presets. The details are
ENGINEERING's.

### 3.9 Tempo and the LFOs

`tempo.Clock` is one free-running clock; `tick(now)` once a frame makes
every call agree on the time. `tap()` sets the BPM and **never moves the
downbeat**; `lfo.trigger` (`⇧B`, the APC40's METRONOME) sets the downbeat
to now and restarts every LFO in a division mode at phase 0 together; Hz
LFOs are untouched. Tempo is session state: a preset never moves it
(`tests/test_lfo.py::test_a_tap_does_not_move_a_running_synced_lfo_but_the_trigger_does`).

`lfo.LFOs` holds four: `shape`, `rate`, `sync` (Hz or a bar division),
`depth`, `phase`, `reset`. Output `u = 0.5 + 0.5 · depth · wave`, rest
0.5. An LFO reads its knobs from its own fields — last frame's effective
values — which is the one-frame lag (§2). A trigger or reset that arrives
after this frame's step lands at exactly phase 0 at the start of the next
step.

### 3.10 What the model does not promise

Behaviour the code has today that the model does not guard:

- `Router.modulate` checks no ownership at run time (§3.2).
- A `hand:<i>` row still reads by index, so one saved by number re-points
  on a rig that reorders `dofs`; and the table compares sources as
  strings, so a depth subscriber written for `hand:7` does not scale a row
  on `hand:right.y`.
- A preset saved after a module-preset load moved a param that a macro's
  base subscriber sets does not round-trip it: the reload lands the
  subscriber's value.
- Undo does not take back: a band added, removed or moved; a tap or a
  typed BPM (the `tempo` group is `undo.EXCLUDED_GROUPS`); the bank and
  "starts on"; a save or a delete (the trash is their net); an edit in
  the `undo.ABSORB_FRAMES` frames after a restore.
- Knob smoothing infers a glide's ownership by reading the norm back, not
  from a write counter; a preset load drops a performance param's glide
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

---

## 4. Module shapes

One row per module or package: what it is for, the names you would grep
for, and the rule it keeps with the test that holds it. The module's
docstring has the rest.

| Module | For | Names | Rule (held by) |
|---|---|---|---|
| `params.py` | the registry: ids, base vs effective, the once-a-frame `apply()` | `Param`, `Registry`, `Kind`, `build_registry`, `PERFORMANCE_GROUPS` / `SESSION_GROUPS`, `F_KEYS` | never imports an adapter; every persisted group is performance or session (`tests/test_params.py::test_every_persisted_group_is_performance_or_session`); `Kind` keeps its identity across a reload (`tests/test_hotreload.py::test_reloading_params_keeps_kind_identity`) |
| `tapers.py` | position ↔ value for every fader | `Taper` | exact round trip on every detent (`tests/test_control.py::test_taper_round_trip`) |
| `routing.py` | the table, the file, the referee, the desk's layers, the macros, the modulation pass | `Binding`, `Bindings`, `Router`, `Macro` / `Sub`, `Owned`, `act`, `referee`, `register_desk`, `led_level`, `LOOP_KEY_ROWS`, `backup`, `remap_factory` | §3.3–§3.8; imports nothing above it (`tests/test_routing_boundary.py`); `tests/test_routing.py`, `tests/test_desk.py`, `tests/test_macros.py`, `tests/test_hand_names.py` |
| `learn.py` | arming, completing and refusing a Learn; pick-then-map; Unbind | `Learn` (`arm`, `accepts`, `learn_control`, `learn_source`, `pick`, `map_picked`, `unbind`, `pending`, `last`), `WANTS`, `blocked`, `bound`, `centred_target`, `PUSH_DEPTH` | nothing completes a learn its `want` does not name; a refused desk learn stays armed; a non-modulatable target is refused for a hand; no learn writes a file (`tests/test_learn.py`) |
| `midi.py` + `apc40.py` | the MIDI adapter (ports, two-layer dispatch, feedback, soft pickup, knob glides, holds) and the APC40 profile (the default map, `LAYOUT` of every control, LED colours) | `MidiIO`, `Ports`, `Slew`, `retry_after`, `HOLD_S`, `BLINK_S`; `apc40.DEFAULT_MAP`, `BANK_PADS`, `SCENE`, `LAYOUT`, `named` | every write is a base write; a note-off goes where its note-on went; a message a row did not apply (a disabled row, a learn candidate) makes that pickup row pick up again (`MidiIO._passed_over`); a lost port is looked for at `retry_after`'s pace (`tests/test_midi.py`, `tests/test_desk.py`). Every test runs with no real MIDI port (`tests/conftest.py::_no_real_midi`) |
| `hands/` | the Ultraleap instrument: twelve shaped axes, presence, eight pinch switches, MIDI out to a DAW, calibration and the interaction box, hand tapes, the HANDS page | `HandsIO`, `HandSettings`, `Layout`, `LeapSource`, `Box`, `inside`, `DEFAULTS` (`core.py`); `signal.py` (shaping, MIDI encoding); `tape.py` (`TapeSource`, `record`); `panel.py` (`page`) | `core.py`, `signal.py`, `tape.py` import nothing from the host; `panel.py` alone knows it (`tests/test_hands_boundary.py`); a hand outside the box is absent for every consumer; the layout is published to the router only on a change (`tests/test_hands.py`) |
| `lfo.py` + `tempo.py` | four LFOs and the tap-tempo clock | `LFOs`, `LFO`, `Clock`, `register` | import nothing from the package (`tests/test_lfo_boundary.py`); §3.9 (`tests/test_lfo.py`, `tests/test_tempo.py`) |
| `audio.py` + `analysis.py` + `analyzer.py` + `bands.py` | capture or file playback, the FFT, the N-band analyzer whose output is `lanes`; `bands.py` is its parts bin | `AudioEngine`, `Analyser`, `Analyzer`, `CEIL` | imports only the stack and `tapers` (`tests/test_audio_boundary.py`); the legacy six-band layout matches the frozen oracle to the bit (`tests/test_analyzer.py::test_legacy_layout_is_bit_exact`) |
| `geometry.py` | the shapes as vertex, edge and face arrays; the 4D → 2D transform | `SHAPES`, `geom`, `project_h`, `PLANES` | the first 18 shapes' order never changes — the golden traces key on it (`tests/test_core.py::test_construction_exact`, `tests/test_golden.py`) |
| `view.py` | `ViewState`, the live object the view, rotation and camera params write | `ViewState` (`integrate`, `instances`, `inst_layout`), `RED` | imports only `geometry`; no GL, so the registry and tests can hold a view |
| `render.py` | the frame (§2): face picture, scene, cover, look-back, pipelines, outputs, ghost hands, dim | `Renderer` (`draw`, `draw_outputs`, `dim_pass`, `face_fx`, `stats`, `now`), `FaceTarget`, `inst_positions`, `render_offscreen` | imports no registry (`tests/test_render.py::test_the_render_stack_imports_no_registry`); §2's draw guarantees (`tests/test_render.py`) |
| `fx.py` + `shaders/fx/` | post effects as GLSL files whose `// @param` uniforms become params; a chain over the frame and one over the faces' picture | `FxState` (`chain(target)`, `select`, `advance_to`, `face_map`), `FxChain`, `FRAME` / `FACES`, `TARGETS`, `FACE_MAPS`, `declare`, `reordered` | an effect is never defined in Python; a broken edit keeps the last good spec; off is bit-identical; `fx.<name>.target` is not modulatable, `fx.face_map` is (`tests/test_fx.py`) |
| `lookback.py` + `dream.py` | the frame history and its age-weighted composite; the torch worker that dreams on it | `Lookback`, `DreamState`, `DreamWorker` | torch only in `dream.py`; nothing in the core imports `dream`; `submit` never blocks the frame (`tests/test_dream.py`, `tests/test_lookback.py`) |
| `ghost.py` | the ghost hands over the finished frame — a display, not a source | `Ghost` (`layer`, `composite`, `readout`, `composite_readout`, `error`), `GhostState`, `Geometry`, `HandPose`, `STYLES`, `PARTS`, `box_of` | writes no param; off or with no hand it touches no GL state; never in the history; `ghost.style` / `.mirror` / `.guide` / `.tethers` not modulatable (`tests/test_ghost.py`) |
| `outputs.py` | the render outputs as the renderer sees them | `Switches`, `route`, `fit`, `View`, `Handoff`, `Slot`, `Presenter`, `PIPELINES`, `MAX_OUTPUTS` | imports `moderngl` and `glsl` only (`tests/test_outputs.py::test_outputs_imports_nothing_from_app_ui_or_params`); `route` and `fit` are pure |
| `glsl.py` + `shaders/_common.glsl` | the GLSL every shader shares | `QUAD_VS`, `common`, `FALLBACK` | a helper is defined once; a broken edit falls back to `FALLBACK` (`tests/test_fx.py::test_the_shared_helpers_are_written_once`) |
| `overlay.py` | where output 1 is and how it looks (window, fullscreen, overlay); the master dim; the per-output switches | `Output` (`register`, `apply`, `allowed`, `dim`), `register_switches` | touches the window system only in `apply()`; rig settings never persist or modulate; overlay only when the config allows (`tests/test_overlay.py`) |
| `ui.py` + `ui_*.py` + `hands/panel.py` | the control window: fourteen pages (`ui.PAGES`), widgets as views onto params, the right-click menu, the modal, the on-screen desk (`ui_desk.py`) | `Panel`, `PAGES`; each page's `page(panel)`; `ui_routing.modal`; `ui_desk.click` | a widget writes only bases; nothing here calls `modulate`; no page scrolls at the control size (`tests/test_ui_shell.py::test_every_page_fits_the_control_window`); no conflicting imgui ids (`tests/test_ui_routing.py`, `tests/test_ui_lfo.py`) |
| `control.py` | the headless half of the analyzer page: band selection, scenes, reset | `Control`, `SCENES` | reset goes to the selected scene and never changes the layout (`tests/test_control.py::test_reset_resolves_to_selected_scene`) |
| `library.py` | the home folder, document kinds, module presets, shows, the bank, the trash, `hidden.json` | `Library`, `Project`, `Marks`, `SLOTS`, `to_trash`, `next_name`, `bank_doc` | never writes a factory file; a user file is copied to the trash before it is overwritten or deleted; a load never rewrites a show; imports neither `homegit` nor `config` (`tests/test_library.py`, `tests/test_presets.py`) |
| `preset.py` | the preset document kind: values, routes, desk, macros, module labels; the factory generator; the first-launch migration | `Presets` (`load`, `load_doc`, `document`, `signature`), `FACTORY_PRESETS`, `write_factory`, `migrate_home` | a load lands every performance base and replaces every performer row, never a session param; a route onto a non-modulatable param is dropped with a note (`tests/test_presets.py`, `tests/test_migration.py`) |
| `config.py` | `config.toml`: defaults, reading, `[[output.screens]]` | `DEFAULTS`, `load`, `screens`, `number` | a bad value is its default with a note, never a raise (`tests/test_config.py`) |
| `undo.py` | undo and redo with no write hook | `Undo`, `watched`, `alike`, `install`, `push`, `SETTLE_S`, `LIMIT` | a leaf (`tests/test_undo.py::test_undo_imports_nothing_from_the_package`); §3.2 (`tests/test_undo.py`) |
| `gamepad.py` + `bridge.py` | the Xbox pad polled raw through GLFW; the DAW bridge (lanes out as MIDI, `ext` lanes in) | `Pad`, `Bridge` | the pad never raises when absent; the bridge never writes a `Param` and is off by default (`tests/test_gamepad.py`, `tests/test_bridge.py`) |
| `app.py` | the entry point: windows and outputs, construction order, the frame loop, the adapters' gates | `main`, `Host`, `frame`, `Keys`, `Mouse`, `close_all`, `_draw_render`, `_open_*` | §1 Host row, §2 (`tests/test_app_boundary.py`, `tests/test_app_relative.py`) |
| `hotreload.py` | hot reload of every module but the cold core | `HotReloader`, `MODULES` | every module but `app`, `hotreload`, `offline`, `watchdog` is watched, in dependency order, leaves first (`tests/test_hotreload.py::test_every_package_module_but_the_cold_core_is_watched`, `::test_the_watch_list_is_in_dependency_order`) |
| `placement.py` | where the windows open and `<home>/windows.json` | `place`, `screens`, `load` / `save`, `read` | a leaf; a remembered rect is used only when enough of it is on a connected screen (`tests/test_placement.py`) |
| `homegit.py` | the home as a local git repository, a commit per save, opt-in (`[library] git`) | `Committer`, `IGNORE` | a leaf, imported only behind its gate; the library calls a hook (`Library._commit`); never a network verb (`tests/test_homegit.py`) |
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

**The desk (APC40).** Two layers in one table: the **preset** layer (the
loaded preset's `desk`) and the **global** layer (the session's), plus
**invariant** rows that mean the same on both (SHIFT, the faders, the
crossfader, the bank pads, OVERDUB, the clip-stop bar). SHIFT latches the
layer (`desk.shift`). `Bindings.dispatch` sends a message to the invariant
rows or the up layer's, never both; `Bindings.active` is what the desk
lights and what `ui_desk` draws. A preset load replaces the preset layer
(`Bindings.set_desk`) and drops to it; at the next `MidiIO.redraw`, a
fader's catch is cleared only if its param moved, and every control that
lost its row goes dark. The bank of twenty-four (`library.SLOTS`) is
F1–F8 plus clip row 1 for slots 1–8 (`params.F_KEYS`) and clip rows 4–5
for slots 9–24 (`apc40.BANK_PADS`).

**Hands.** `hands/core.py`'s `LeapSource` (or a `TapeSource`) gives
features and skeletons; `HandsIO.poll` shapes twelve axes, two presence
lanes and eight pinch switches (`Layout`), feeds them as `hand`, publishes
the name map, may complete a Learn, and sends MIDI to a DAW. The ghost
hands read `HandsIO.skeleton` raw through `renderer.ghost.source`; they
are not a source.

**Effects.** Each `shaders/fx/*.glsl` file is an effect; its uniforms
become `fx.<name>.*` params (`fx.declare`). `fx.<name>.target` aims it at
the frame or the faces; `fx.face_map` says whether the faces show the
picture per face or in screen space. The frame's chain
(`FxState.chain(FRAME)`) runs in each pipeline; the faces' chain
(`Renderer.face_fx`, borrowing the frame chain's programs) runs before the
scene pass.

**Look-back and dream.** `Lookback` keeps a history of scene textures and
composites echoes over the frame; `DreamWorker` (only with
`[dream] enabled`) takes frames from the history on its own thread and
returns dreamed ones without ever blocking the frame.

**Outputs.** `config.toml`'s `[[output.screens]]` lists up to
`outputs.MAX_OUTPUTS` render outputs (no list is one). `app._windows`
makes one `outputs.Slot` per entry: output 1 is the render window, each
later one a window in its share group with its own `Presenter` and its own
`overlay.Output` (no params). Each opened output gets `output.N.*`
switches (`overlay.register_switches`); `placement.py` remembers one rect
per output.

**Presets, shows, the library.** A **preset** (`hyperspace.preset/2`) is
the performance: values, routes, desk, macros, module labels. A **show**
(`library.Project`, `hyperspace.project/2`) is the session: session values,
the bank of preset names and a "starts on" preset. The launch opens the
show opened last (`<home>/last_show`). A user preset file is copied to
`<home>/trash/<group>/` before a save overwrites it or a delete removes
it; the trash is listed, restored and emptied from the preset list.
Factory presets are hidden, not deleted (`<home>/hidden.json`). With
`[library] git = true`, `app._open_homegit` attaches a
`homegit.Committer` as `library.committer`, and `Library._commit` asks it
for a commit after each save, delete, rename, hide, unhide, restore and
show write.

**Undo.** `Undo.tick` (frame step 5) compares a fingerprint of the watched
bases (`undo.watched`: persisted, not an alias, not a trigger, not the
`tempo` group), the table's performer and preset-layer rows, the macros
and the band layout; a change opens a step and `SETTLE_S` of quiet closes
it. A replacing action — a load, a Learn, a ROUTING ×, a reorder — calls
`undo.push(label)` first. `library.Marks` lets an undo of a load put back
what the library calls loaded.

**Hot reload.** `hotreload.MODULES` lists every package module but the
cold core, leaves first; a save re-executes the changed module and every
one after it, then re-classes live instances in place. `app`,
`hotreload`, `offline` and `watchdog` need a restart.
