# Decisions

The settled calls behind the Python app, with the date they were made and
the reason, so nobody re-litigates them by accident. Gathered by plan 10
(2026-09-27) from the *Decisions* and *As built* sections of plans 07, 08
and 09, the earlier plans' governing notes, and the session memory where
it holds a decision the plans do not. Each row's status was checked
against the code at `main` ef299ef.

How to read it: **standing** means the code does this today; **superseded**
means a later row replaced it, and the row stays so the history is
legible. Grouped by theme, because a reader arrives with a question, not a
plan number. The structure the decisions produced is in
[`ARCHITECTURE.md`](ARCHITECTURE.md); the behaviour in
[`ENGINEERING.md`](ENGINEERING.md).

To add one: a row here the day it is settled with the owner, with the
why, and a link from the plan or PR that made it.

## Platform

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-08-21 | Full Python re-platform. `hyperspace-web/hyperspace.html` never runs at runtime; it is only the oracle the golden traces were recorded from. | One process, one language, real audio devices and GL; the browser sandbox had cost more rounds than the port. | BLUEPRINT §5, plan 00 | standing |
| 2026-08-21 | Single process: moderngl renderer, sounddevice capture, imgui panel, asyncio only where a device needs it. | No IPC to debug mid-set; every value is a Python float one frame from the screen. | BLUEPRINT §3 | standing |
| 2026-08-21 | A DAW connects only through an optional bridge, off by default; nothing in the core depends on it. | FL Studio must stay reachable later without shaping the core around MIDI. | BLUEPRINT §3.6, plan 05 | standing (`bridge.py`, config-gated) |
| 2026-08-21 | Parity bar: geometry exact (1e-12, vertex order kept), audio behavioural, visuals judged by eye. | Frame-exact tolerance gates on an adaptive audio chain cost effort without changing what matters live. | plan 01, memory | standing |
| 2026-08-22 | Plans 03 and 04 swapped: UI before booth hardware. | Deck and IMU access did not exist; the DJ Link spike is the first thing to do when it does. | CHECKPOINT | standing (plan 04 still parked) |
| 2026-09-08 | Generalise before hardware: every new input goes through registry ids and a binding table, never straight at `ViewState` or the chain. | The owner would rather pay for the abstraction up front than rewrite each device's wiring later. | memory (APC40 session) | standing (`params.py`, `routing.py`) |
| 2026-09-18 | The analyzer runs in-process on the frame loop; MIDI in/out is an adapter, never the only path. | Latency and one clock; the analyzer is a source like any other. | plan 07 | standing |

## The control model

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-09-08 | One parameter registry: every settable thing has a stable id and one normalised interface (continuous / enum / toggle / trigger; tapered params quantise to their throw for the user, float-map for modulation). | The panel, keys, pads and MIDI become binding tables over one address space instead of three code paths. | plan 05, memory | standing (`params.py`) |
| 2026-09-18 | Base vs effective: `p.base` is the user's setting, `p.value` is the live object; `Registry.apply()` writes `base + Σ offsets` once per frame. A raw write to the object is adopted as a delta on the base. | Lets the rotation integrator and a modulation offset coexist on one param without either clobbering the other. | plan 07 WP0 | standing |
| 2026-09-18 | Any registry param is a modulation target, subject to its `modulatable` flag; enums, toggles and triggers too, with hysteresis. Plane drives and shader band inputs become ordinary params (`rot.rate.*`, `pattern.mod.*`). | One modulation concept; audio stops being a special case. | plan 07 | standing |
| 2026-09-18 | Keys, gamepad, MIDI and audio lanes are one binding table, persisted as a routing preset / the live `bindings.json`. | Three tables (`KEYMAP`, `PADMAP`, `midi_map.json`) were three places a binding could hide. | plan 07 WP4b | standing (`routing.py`; see F1–F8 exception below) |
| 2026-09-18 | `rot.phase.*` is a param but never persisted. | A theme changes the look, not where the spin currently is. | plan 07 | standing |
| 2026-09-18 | Routes are additive with signed depth; a base of 0 plus depth reproduces "audio replaces the constant". Ops `abs / step / toggle / fire / mod`, later `replace` (units) and `span` (throw) for hands. | Reproduce the six-plane drive exactly through the new bus. | plan 07 WP4b, PR #30 | **superseded** 2026-09-26 by push / position |
| 2026-09-25 | Learn on a hand writes an `abs` row that `Router.drive` applies to the base every frame. | First cut of hands-as-fader. | plan 08 (first form) | **superseded** 2026-09-26: Learn writes a `position` route |
| 2026-09-26 | **One path.** Every continuous source (`lane`, `hand`, `ext`, `lfo`) reaches a param only through `Router.modulate`. `Router.drive`, `Param.glide` and lane-scheme `abs` removed. | The audit found two write paths with nothing deciding between them; every conflict class traced to that. | plan 09 d.1 | standing |
| 2026-09-26 | **One performer per parameter.** A performer is an enabled route row from a continuous scheme; a target has at most one; a second one prompts *Replace / Keep*. Gates do not exempt a row. | Two things pulling one knob is never what the performer meant; asking is what FL Studio does. | plan 09 d.2 | standing (`Bindings.owner`, `Owned`) |
| 2026-09-26 | **Scene-setters write the base and never prompt**: panel, keys, pad buttons, the APC40 (abs / rel / notes), presets, mouse and stick relative writers. A knob turned on a hand-owned param moves the value the hand returns to. | Setting the scene and performing on it are different jobs; the second must not block the first. | plan 09 d.3 | standing |
| 2026-09-26 | Relative writers (mouse orbit, sticks, ↑/↓ depth) read the **base**, not the effective value. | Reading the effective value folded the whole modulation offset into the base every drag frame (audit sim 1). | plan 09 WP2 | standing (`Param.nudge` / `scale`) |
| 2026-09-26 | Hands grab; they never yield. No `pickup` on a performer row. | The box is a continuous performance; pickup only makes sense for a knob you let go of. | plan 09 d.4 | standing |
| 2026-09-26 | **Two ops.** `push`: offset = depth · scale · (u − rest). `position`: the source is the fader, along the param's taper; the base returns when it stops. `replace` deleted. | Five spellings of "the source drives the param" behaved five ways; `replace` capped a hand at the value 1. | plan 09 d.5 | standing (`MOD_OPS`) |
| 2026-09-26 | Push is centred where the source rests; the rest is the source's own (published by its adapter in `Router.rests`) unless the row says otherwise. | Without it every LFO route sat permanently offset by half its depth. | plan 09 d.6, as built | standing (`Binding.rest = None` → `Router.rest_of`) |
| 2026-09-26 | Chaining, not stacking: layers come from a performer owning another source's knob (LFO depth, a macro), never from two rows on one target. Eight macro knobs exist only to be owned and to be a route's `scale`. | Layering becomes a property of the graph, which the referee can police. | plan 09 d.7 | standing (`macro.1–8`) |
| 2026-09-26 | Macros are routing-layer state (`ROUTING_GROUPS`): saved in routing presets and the live table's `values`, outside the whole-surface snapshot. | A theme or project should not carry the routing layer's scratch knobs. | plan 09 as built | standing |
| 2026-09-28 | LFO and tempo knobs stay **theme state**. A routing preset's `values` may set any base its rows assume (LFO knobs, an effect's speed, dream settings), provided each id is a persisted, non-alias param a theme would save too. | An LFO arrangement is part of a look a theme carries; a preset that assumes "LFO 1 at one bar" should say so rather than hide the dependency. Plan 13's preset, which carries every base and route in one file, supersedes the question when it lands. | owner, decision register row 3 (audit R1) | standing (`test_a_routing_presets_values_are_bases_a_theme_would_save`) |
| 2026-09-26 | The factory `default` table keeps legacy6's push rows on `rot.rate` bases of 1; only the `legacy6` preset zeroes them. | Idle spin stays in the default; `legacy6` is the parity anchor, driven. | plan 09 as built | standing |
| 2026-09-26 | Bindings file schema 2. A v1 file migrates on load (op renames; `replace` dropped with a note), the referee settles duplicate owners (first wins), `remap_factory` moves the plan-09 buttons where nothing uses the source; written back once. | Presets are disposable; a user file must not silently keep rows the new rules cannot express. | plan 09 d.10, as built | standing |
| 2026-09-26 | Key modifiers are table rows (`key:SHIFT+B`); rows on one key settle together. F1–F8 / ⇧F1–F8, Cmd+R, ESC/Q stay in the loop. | ⇧B needed to be a binding, not loop code; the theme keys were out of scope. | plan 09 as built | standing; **superseded in part** 2026-09-28: R and F1–F8 / ⇧F1–F8 are table rows since PR #58; Cmd+R and Esc/Q stay in the loop |
| 2026-09-28 | **R, F1–F8 and ⇧F1–F8 become binding-table rows** (`key:R → camera.reset`, `key:F1 → theme.load.0`, `key:SHIFT+F1 → theme.save.0`; slots 1–8 are ids 0–7); `app.act` goes; `remap_factory` adds them to older files only where the key is free. Cmd+R, Esc/Q and ↑/↓ stay in the loop. | The 2026-09-26 row kept them in the loop for scope, not design; as rows they rebind, show on ROUTING and are covered by the cheat-sheet test. | owner, decision register row 7 (audit R2 + L2) | standing (PR #58); supersedes the 2026-09-26 row's loop exception for these keys |
| 2026-09-28 | Plan 11 lands as one merge of the integration branch (PR #55, carrying #39–#54, #56 and #57), then PR #47 as is. | The cross-branch conflicts were resolved once and the merged build is what was tested. | owner, decision register row 8 | standing |
| 2026-09-28 | Plan 13's global layer: the track knobs carry four hand-feel settings (smoothing, response, catch, the selected axis's return) plus `tempo.bpm`; three knobs free. **A first cut**: the owner expects better global controls to turn up with use. | The hand feel is what changes with who is in the box, and it must not cost every preset a knob. | owner, decision register row 9 (plan 13 P13-a) | decided, not built |
| 2026-09-26 | MIDI is not the internal bus. Values flow as floats; MIDI survives only at the edges (controller in, DAW out). | None of the conflict classes was about wire format; a 7-bit bus would add quantisation for nothing. | BLUEPRINT §1, plan 08, plan 09 | standing |
| 2026-09-27 | A hand out of the box reads `NaN` on its axes, so every row on them lets go and the base returns that frame; the return spring and `hold` shape only the DAW output, and the return catch stays live. `rest = hold` no longer latches a routed param — latching is done by setting the base. | Plan 08 promised "every performer row springs back to the base when the hand leaves"; only the tracker going dark did. A NaN during the catch would make a one-frame dropout a 0.15 s hole. | plan 11 §2 row 8, PR #40 | standing (`Follower.live`, `HandsIO.lanes`) |
| 2026-09-27 | A trigger or per-LFO reset that fires after this frame's LFO step is held and applied at the start of the next step, so the first frame the LFOs see it reads exactly phase 0 on every path; keys, which run before the step, land at once. | The docstring promised phase 0; the panel chip and a performer-fired trigger read `dt · bpm / 60 · ratio`. | plan 11 §2 row 11, PR #42 | standing (`LFOs.pending`) |
| 2026-09-27 | Leaving a division for Hz carries the LFO's phase; switching into a division lands on the clock's beat. | A preset restore of `lfo.N.sync` cannot be told from a knob turn, and a bar-long LFO must land on the bar. | plan 11 WP4 review, PR #42 | standing |

## Inputs

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-08-30 | The Xbox pad is polled raw through GLFW with our own index map, not the gamepad-mapping database. | The bundled SDL database misses the BLE controller's GUID and `update_gamepad_mappings` did not take on macOS. | memory | standing (`gamepad.py`) |
| 2026-09-08 | The APC40 is a device *profile* (`apc40.py`: port name, mode SysEx, LED rules, default map) over a generic MIDI adapter (`midi.py`). | The adapter must outlive the controller. | plan 05 | standing |
| 2026-09-28 | APC40 feedback: **rings show the base**, **LEDs on toggles and enum `set` rows show the effective value**. | A ring is a pickup readback — showing a performer's value would mean the knob could never catch its own; an LED is a state light and should show what the show is doing. | owner, decision register row 4 (audit R6) | standing (`midi.py` feedback) |
| 2026-09-25 | Hands are the primary performing surface; the APC40 keeps presets, scenes and master controls. | Two hands in a box is the show; the desk is the setup. | plan 08, memory | standing |
| 2026-09-25 | Twelve axes (palm pose, six per hand) shaped as analog signals — range, One Euro, dead zone, curve, attack/decay, rest spring — and eight pinch switches. **No gesture vocabularies, no more DOFs.** | Performers have to be taught the system; predictability beats expressiveness. | plan 08 | standing |
| 2026-09-25 | The hands package is liftable: `core.py` and `signal.py` import nothing from the host, everything arrives duck-typed; `panel.py` is the one adapter. A test fails the build otherwise. | Boundaries erode one convenient import at a time. | plan 08 | standing (`test_hands_boundary.py`) |
| 2026-09-25 | Inside Hyperspace nothing goes through MIDI: a hand is a float source; MIDI encodings exist only for the DAW port. | 7-bit steps and fader detents on a hand would be felt. | plan 08 | standing |
| 2026-09-25 | A gate whose source is not live holds the row **shut**. Only fed sources (hand, ext, lfo) can gate; analyzer lanes are not switches. | No param should start moving because a camera was unplugged. | plan 08 | standing |
| 2026-09-25 | Rig settings (`[hands]` in config.toml), box ranges (`hands.json`) and performance settings (a `hands` preset) live in three places, each where it changes. | Calibration, hardware and feel change on different days. | plan 08 | standing |
| 2026-09-25 | Pinch switches are a Schmitt trigger (close / open thresholds) plus a debounce. | One threshold chatters where the fingers hover. | plan 08 | standing |
| 2026-09-25 | Oscillators deferred from plan 08. | Scope; hands first. | plan 08 | **superseded** 2026-09-26: plan 09 WP4's LFOs |

## Tempo and LFOs

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-09-26 | One free-running clock, tapped into time. Tap sets BPM; the downbeat is the global trigger's. No DJ Link, no MIDI clock, no drift correction: re-tap. 4/4 assumed. | Sync sources do not exist on this rig yet; a tap is what a lighting operator already does. | plan 09 d.9 | standing with one deviation (`tempo.py`): there is no BPM → Hz conversion — a synced LFO reads `clock.beat · ratio` directly while a Hz LFO integrates its rate |
| 2026-09-28 | **A tap never moves the downbeat**, before the first trigger or after it; only the global trigger (⇧B, METRONOME) places it. A fresh launch runs its synced LFOs unaligned until the first press. | One rule instead of two that depend on history; the trigger button keeps its one job, and tapping is always safe mid-set. The cost is one press at the start of a set. | owner, decision register rows 1–2 (B2 option a); PR #42 | standing (`Clock.tap`) |
| 2026-09-28 | **`lfo.trigger` and `lfo.N.reset` are ownable by a performer; `tempo.tap` is not** (`modulatable=False`). | A pinch switch exists so a pinch can be a button, and the rising-edge trigger was built for dropping the LFOs on the one; a band routed to tap tempo would tap on every transient, a footgun with no use. | owner, decision register rows 1–2 (B5 option c); PR #42 | standing (`tempo.register`) |
| 2026-09-26 | BPM is the mean of the burst's last 8 taps; a gap over 2 s starts a new burst. | A tempo change should register within a bar. | plan 09 as built | standing |
| 2026-09-26 | The global LFO trigger sets the downbeat to now and restarts every synced LFO at phase 0 together; tapping alone never moves a running LFO. | A re-tap mid-set must not jolt the picture until the performer says so. | plan 09 WP4 | standing (`lfo.trigger`) |
| 2026-09-26 | `Clock.trigger` folds the current nudge into `t0`; `Clock.tick(now)` once a frame so a key-fired trigger and the LFO step agree. | Without the tick a synced LFO read phase ≈ 0.999 on the trigger frame. | plan 09 as built | standing |
| 2026-09-26 | Four LFOs. Each is a performer and every one of its knobs (shape, rate, sync, depth, phase) is an ordinary, ownable param. Output `u = 0.5 + 0.5 · depth · wave`, rest 0.5. | Ownable knobs are what makes them chainable. | plan 09 d.8 | standing (`lfo.py`) |
| 2026-09-26 | The APC40's TAP TEMPO → `tempo.tap`, NUDGE ± → `tempo.nudge`, METRONOME → `lfo.trigger` with a beat-blink LED; `theme.next` moved to QUANT; the shape steps went. | The physical buttons should do what they say; the clip grid already sets shapes. | plan 09 WP4 | standing (`remap_factory`) |

## Audio

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-08-21 | The six-band chain ports faithfully, including its known bugs (the trim non-monotonicity), until plan 06. | A "fix" during a port makes parity failures undiagnosable. | plans README | standing on the AUTO path; MANUAL is the fix (2026-09-28) |
| 2026-09-18 | The chain becomes an N-band (1–16) graphic-EQ analyzer: per band centre / width / weighting curve, then the existing envelope, transient and shaper chain. Band → plane mapping and `dir` leave the chain and become routes. | Audio as a source, not a special case. | plan 07 WP4a | standing (`analyzer.py`) |
| 2026-09-18 | A factory `legacy6` preset reproduces the reference chain on the golden traces. | The regression net for the refactor. | plan 07 WP4a | standing |
| 2026-09-18 | The band editor shows a live spectrogram heat map with the band curves drawn over it. | Bands are shaped against real signal, not numbers. | plan 07 | standing (`ui_bands.py`) |
| 2026-09-28 | `master.dyn` keeps its 0.06×–4× range: up to 1× it blends toward the windowed normaliser and grows the expansion; past 1× only the expansion grows. | Capping at 1× would move every saved preset's detent; two knobs would re-freeze the oracle. Documented instead. | owner, decision register row 5 (audit A7) | standing (tooltip, ENGINEERING §4) |
| 2026-09-28 | The trim fix is a per-band **AUTO / MANUAL** normalisation switch (`band.{i}.norm`, default AUTO): AUTO is the reference chain bit for bit; MANUAL bypasses the adaptive window and applies trim once, as a plain gain. | What a mix engineer expects; the reference path and its frozen oracle stay untouched; options 1 and 2 changed the reference for everyone. | owner, decision register row 6 (audit A10, plan 06 item 2) | standing (plan 11 WP15, `test_manual_normalisation_makes_trim_monotonic`) |

## Render

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-08-22 | CPU transforms through the parity-proven `project()`, GPU rasterises; edges as screen-space quads at the reference width formula. | 1 px GL lines lost the near-edge hierarchy the reference has. | plan 02 | standing (`render.py`) |
| 2026-09-18 | Two GLFW windows on one GL context; the render window has **no imgui at all**. Cheat sheet, toasts, everything: control window. | The render window is the projector; nothing of the desk belongs on it. | plan 07 | standing (`app.py`) |
| 2026-09-19 | The dream is **temporal**: one running buffer blended with each frame, a few gradient steps per frame, back to the compositor. Not per-frame deep dream. | 60 steps per frame is neither affordable nor needed; persistence *is* the tracer. | plan 07 WP6 | standing (`dream.py`) |
| 2026-09-19 | The dream worker is an optional extra, config-gated; missing torch degrades to the plain tracer with a note. | Nothing in the core may depend on it. | plan 07 WP6b | standing |
| 2026-09-20 | The compositor re-colours the dream buffer (`dream.hue / sat / tint…`); echoes pass untouched. | The net paints in its own primaries whatever the scene's palette. | plan 07 WP6b follow-up | standing (`lookback.py`) |
| 2026-09-25 | `dream.occlude`: the render covers the wake where it drew, via a face coverage mask pass. | Brightness-as-coverage barely covered; face fills draw at 1–6 % alpha. | PR #22 | standing |
| 2026-09-26 | Post effects are one GLSL file each under `shaders/fx/`; `// @param` uniforms become registry params `fx.<file>.<uniform>`; the chain runs after the look-back composite; off is bit-identical. **New effects are new `.glsl` files, not Python.** | A general effect pipeline that speaks the modulation language. | PR #25 | standing (`fx.py`) |
| 2026-09-26 | `view.cut_through` (default on) keeps the old blend; off uses separate alpha so faces do not expose the desktop in overlay mode. | The owner wants to choose between seeing the desktop through faces and seeing the lowest layer. | PR #26 | standing |

## Library and persistence

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-09-18 | Library home is `~/Hyperspace` (overridable by `HYPERSPACE_HOME` / config); factory presets ship read-only in the repo; a user file shadows a factory file of the same name. | The Ableton model: a project saves everything, each module has its own browsable preset library. | plan 07 WP2 | standing (`library.py`) |
| 2026-09-18 | One JSON per preset (`hyperspace.preset/1`, a registry group's snapshot); projects are `*.hyp.json`; a `schema` string plus a migration table; unknown ids on restore are reported, not fatal. | Human-editable, live-reloadable, versioned. | plan 07 WP2 | standing |
| 2026-09-18 | The library is watched like source: editing a preset file reflects in the running app. | The same contract `patterns.glsl` set. | plan 07 WP2 | standing (`hotreload.py`) |
| 2026-09-26 | Routing presets are disposable: every factory file was rewritten for schema 2 rather than migrated. | Nothing is preserved that the new rules cannot express. | plan 09 d.10 | standing |
| 2026-09-27 | The eleven JSON files under `library/band/` are the one scene store, each band named in the layout; `scene.select`, the APC grid, Reset and the strip all read them (the combo re-tunes the bands you have, the strip applies its layout). | Two copies of the scenes had already diverged on names. | plan 11 §2 row 9, PR #44 | standing (`control.SCENES`, `Analyzer.apply_scene`) |
| 2026-09-27 | `Project.io` is deleted: the live binding table is `<home>/bindings.json` and a project never carries the routing layer. Routing presets are a document kind of the library (`Library.routing`), listed, shadowed and reloaded like every module preset. | One preset system over one folder tree; plan 07's "bindings with the project" never happened and the standing decision is one home file. | plan 11 §2 row 10, PR #52 | standing |

## Presets and the desk

Settled with the owner on 2026-09-28 while plan 12 was composing the party
presets; the design is [`plans/13-preset-and-session.md`](plans/13-preset-and-session.md)
and nothing below is built yet. The open forks are plan 11 §2 rows 12–17.

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-09-28 | **Two nouns.** A *preset* is one file holding everything a performance moment is: every performance parameter's base, the performer rows, the APC40's preset layer, and a label per module. A *session* is the boilerplate that makes the rig ready and that a preset never touches. "Theme", "routing preset" and the UI word "scene" go. | Plan 12 found five nouns split by file lineage; one moment the performer calls TRIP was a theme, a routing preset and two module presets loaded in three steps. | plan 13 D1 | decided, not built |
| 2026-09-28 | **A preset load replaces everything**: every performance parameter lands (the file's value or the app default), every performer row is replaced, the preset layer of the desk is replaced. No merging. | "Loading different things and having states merged together is very leaky and very hard to get right" — the owner. | plan 13 D2 | decided, not built |
| 2026-09-28 | Module presets stay: one group's values, cycled from that group's strip, replacing that group. A preset records which module preset each group was showing as a **label only**; loading a preset never chain-loads one. | Cycling one module over a well-formed scene is useful; a pointer that loads on load is where merge cases come back. | plan 13 D3 | decided, not built (today's `Project.modules` already behaves so) |
| 2026-09-28 | The APC40 has two layers under a **latched SHIFT** (note 0x62); its LED shows which layer is up; loading a preset drops to the preset layer. | Command-key logic: the globals are always one press away without costing every preset a knob. Held would need two hands at the desk. | plan 13 D4 | decided, not built |
| 2026-09-28 | The **global layer is fixed**: defined in the session's files, never the target of a Learn. A Learn writes only into the loaded preset. | "Global for a reason"; an accidental learn must not overwrite them mid-set. | plan 13 D5 | decided, not built |
| 2026-09-28 | **Invariant controls** have one meaning on both layers and no preset may map them: the faders, the preset-select row, SHIFT, TAP TEMPO, METRONOME, NUDGE ±, the transport. | Switching presets and keeping time must never be behind a layer. | plan 13 D6 | decided, not built |
| 2026-09-28 | On a layer switch the knobs **jump** to the layer's values (endless encoders the host re-bases by the ring message); the faders **soft-pick-up**. | The knobs have no position of their own; the faders do. | plan 13 D7 | decided, not built — the re-basing is the one hardware assumption still to be seen (hand check 31) |
| 2026-09-28 | A control the preset does not map **does nothing** and shows dark. No fall-through to the global layer. | A knob that silently means something else is worse than a dead one. | plan 13 D8 | decided, not built |
| 2026-09-28 | The **analyzer is session**: bands, dynamics, scenes and the drive fader are never in a preset. | It is the room, and every hand preset assumes one shared lane layout. | plan 13 D9 | decided, not built |
| 2026-09-28 | A session names its **startup preset**, loaded on launch. | Under "unmapped does nothing" a fresh start would otherwise have a dark desk. | plan 13 D11 | decided, not built |
| 2026-09-28 | A modifier is read **at the press**; SHIFT's release never re-evaluates a button already down. | The two note-offs arrive in either order. | plan 13 D12 | decided, not built |
| 2026-09-28 | Plan 12's five `party-*` presets are composed six-DOF only, every hand row a push from the axis's rest (or a position on a param whose base is the rest), no pinch dependence, no rate-type param under a hand; a tilt adds ±45° because a quarter turn maps the cubic shapes onto themselves. | The party brief: intuitive in seconds, a still hand is calm, no preset depends on B1's fix. | plan 12 §3, PR #47 | standing (to be re-cut into plan 13's file shape, plan 11 §2 row 17) |

## UI

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-08-23 | The panel is a square, hairline instrument panel with a monospace atlas and detent notches. | Match the reference's look. | plan 03 | **superseded** 2026-09-26 |
| 2026-09-26 | Legibility at a distance comes first: rounded frames, pill chips, filled faders, SF Rounded / SF Mono, no page scrolls at the control size (a test holds it). Master faders live on the audio page. | The panel proved unreadable from a few feet back at a party. | PR #24, ENGINEERING §7 | standing |
| 2026-09-26 | The Replace / Keep prompt is drawn first in `Panel.draw`, on every page, even with the panel collapsed. | A learn can be armed from any page and a held learn must never be silently parked. | plan 09 as built | standing (`ui_routing.py`) |
| 2026-09-26 | The panel names a performed param's owner in its tooltip, in the adapter's words (`Router.describe`). | The performer should be able to read who has the knob. | plan 09 WP2 | standing |

## Process

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-08-21 | ENGINEERING.md is ground truth for existing behaviour; where documents disagree about behaviour, it wins. Plans say what was intended. | Plans drift the moment code lands; one document must be the one that is checked. | plans README | standing (plan 10 adds ARCHITECTURE.md for structure) |
| 2026-08-21 | Exit criteria are gates, checked on merged `main`, not on a branch. | An agent's measurements describe only its own branch. | plans README | standing |
| 2026-08-23 | Work packages run as parallel agents in worktrees, one branch and one PR each; the owner merges. Every agent prompt starts from current `main` and checks that the features it needs exist. | Two rounds were lost to agents branching from stale HEADs. | ENGINEERING §10, plan 07 | standing |
| 2026-09-26 | Each code PR gets a `/code-review` before merge. | The auto-mode classifier requires it, and it caught real faults in plan 09. | memory | standing |
| 2026-09-26 | Plan 10 (this pass) documents the system as built; findings are filed, not fixed. | Fixing while documenting is how the documents stop matching the code before the PR merges. | plan 10 | standing |
| 2026-09-27 | Plan 11 closes the audit register one work package per PR, each code-reviewed; the shared documents are updated in the same PR and audit rows are marked `done, PR #N`, never deleted. The branches integrate through one `plan-11-integration` branch because they conflict on the three shared documents' tables. | Seventeen branches editing the same tables conflict pairwise; one resolved merge is cheaper than sixteen. | plan 11 §3 | standing |
| 2026-09-27 | **Pending — the owner's.** Seven forks plan 11 raised and did not decide: B2 (does a tap ever move the downbeat; recommended: never), B5 (are `tempo.tap` / `lfo.trigger` / `lfo.N.reset` modulatable; recommended: keep all three), R1 (LFO knobs theme state, routing presets may set assumed bases; recommended), R6 (LEDs keep showing the effective value; recommended), A7 (`master.dyn` keeps 4× and documents the split; recommended), A10 (the trim: per-band auto / manual switch; recommended), R2+L2 (`R` and F1–F8 into the table; recommended). Each becomes a row here the day it is answered. Plans 12 and 13 added six more on 2026-09-28 (plan 11 §2 rows 12–17: the global layer's knobs, partial presets, bank slots by name, what a macro is, the ROUTING page's shape, sequencing — the last settled); R1 dissolves once plan 13 lands. | Listed so nobody reads the recommendation as the decision. | plan 11 §2 rows 1–7, 12–17 | pending |
