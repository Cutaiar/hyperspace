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
| 2026-09-26 | The factory `default` table keeps legacy6's push rows on `rot.rate` bases of 1; only the `legacy6` preset zeroes them. | Idle spin stays in the default; `legacy6` is the parity anchor, driven. | plan 09 as built | standing |
| 2026-09-26 | Bindings file schema 2. A v1 file migrates on load (op renames; `replace` dropped with a note), the referee settles duplicate owners (first wins), `remap_factory` moves the plan-09 buttons where nothing uses the source; written back once. | Presets are disposable; a user file must not silently keep rows the new rules cannot express. | plan 09 d.10, as built | standing |
| 2026-09-26 | Key modifiers are table rows (`key:SHIFT+B`); rows on one key settle together. F1–F8 / ⇧F1–F8, Cmd+R, ESC/Q stay in the loop. | ⇧B needed to be a binding, not loop code; the theme keys were out of scope. | plan 09 as built | standing |
| 2026-09-26 | MIDI is not the internal bus. Values flow as floats; MIDI survives only at the edges (controller in, DAW out). | None of the conflict classes was about wire format; a 7-bit bus would add quantisation for nothing. | BLUEPRINT §1, plan 08, plan 09 | standing |

## Inputs

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-08-30 | The Xbox pad is polled raw through GLFW with our own index map, not the gamepad-mapping database. | The bundled SDL database misses the BLE controller's GUID and `update_gamepad_mappings` did not take on macOS. | memory | standing (`gamepad.py`) |
| 2026-09-08 | The APC40 is a device *profile* (`apc40.py`: port name, mode SysEx, LED rules, default map) over a generic MIDI adapter (`midi.py`). | The adapter must outlive the controller. | plan 05 | standing |
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
| 2026-09-26 | One free-running clock, tapped into time. Tap sets BPM; the downbeat is the global trigger's. No DJ Link, no MIDI clock, no drift correction: re-tap. 4/4 assumed. | Sync sources do not exist on this rig yet; a tap is what a lighting operator already does. | plan 09 d.9 | standing with two deviations (`tempo.py`): a tap also re-pins the downbeat *until the clock is first triggered* (audit B2), and there is no BPM → Hz conversion — a synced LFO reads `clock.beat · ratio` directly while a Hz LFO integrates its rate |
| 2026-09-26 | BPM is the mean of the burst's last 8 taps; a gap over 2 s starts a new burst. | A tempo change should register within a bar. | plan 09 as built | standing |
| 2026-09-26 | The global LFO trigger sets the downbeat to now and restarts every synced LFO at phase 0 together; tapping alone never moves a running LFO. | A re-tap mid-set must not jolt the picture until the performer says so. | plan 09 WP4 | standing (`lfo.trigger`) |
| 2026-09-26 | `Clock.trigger` folds the current nudge into `t0`; `Clock.tick(now)` once a frame so a key-fired trigger and the LFO step agree. | Without the tick a synced LFO read phase ≈ 0.999 on the trigger frame. | plan 09 as built | standing |
| 2026-09-26 | Four LFOs. Each is a performer and every one of its knobs (shape, rate, sync, depth, phase) is an ordinary, ownable param. Output `u = 0.5 + 0.5 · depth · wave`, rest 0.5. | Ownable knobs are what makes them chainable. | plan 09 d.8 | standing (`lfo.py`) |
| 2026-09-26 | The APC40's TAP TEMPO → `tempo.tap`, NUDGE ± → `tempo.nudge`, METRONOME → `lfo.trigger` with a beat-blink LED; `theme.next` moved to QUANT; the shape steps went. | The physical buttons should do what they say; the clip grid already sets shapes. | plan 09 WP4 | standing (`remap_factory`) |

## Audio

| Date | Decision | Why | Source | Status |
|---|---|---|---|---|
| 2026-08-21 | The six-band chain ports faithfully, including its known bugs (the trim non-monotonicity), until plan 06. | A "fix" during a port makes parity failures undiagnosable. | plans README | standing for `bands.py` |
| 2026-09-18 | The chain becomes an N-band (1–16) graphic-EQ analyzer: per band centre / width / weighting curve, then the existing envelope, transient and shaper chain. Band → plane mapping and `dir` leave the chain and become routes. | Audio as a source, not a special case. | plan 07 WP4a | standing (`analyzer.py`) |
| 2026-09-18 | A factory `legacy6` preset reproduces the reference chain on the golden traces. | The regression net for the refactor. | plan 07 WP4a | standing |
| 2026-09-18 | The band editor shows a live spectrogram heat map with the band curves drawn over it. | Bands are shaped against real signal, not numbers. | plan 07 | standing (`ui_bands.py`) |

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
