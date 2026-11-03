# Plan 44 — decks: N looks, one on air

**Status: D1 built** (2026-11-02, wave 1: `hyperspace/deck.py`, the
`Deck` bundle and `Deck.build`, no behaviour change — register row 571,
hand check 430, group AW); D2 built (2026-11-03, rows 590–593); **D3
built** (2026-11-03, wave 2: rows 611–625, hand checks 461–470, group BJ);
D4–D6 a plan, not built. Written 2026-11-02 as
wave 0 item D0 of the post-show sequencing. Written against `main` at 72da1ed: every symbol below is in
the code today unless the text says it is new. Its four decisions are
register rows 556–559, answered by the owner on 2026-11-02 (as recommended; 558 with a nuance, §7). The build is six PRs,
D1–D6, each its own and behaviour-neutral until D4; D1 does not start
before this plan and plan 43 (the preset contract, written in parallel)
are merged, because D3 and plan 43 draw the same line.

The ask (the owner, after the 2026-10-30 show, reshaped 2026-11-02):
**"hold" leaks**. Plan 38's hold keeps a second copy of the held params'
bases and swaps them in around the draw (`hold.Hold.program`: a param
whose base is unmoved since HOLD costs one `alike` compare and is skipped),
but there is one `params.Registry` and one `routing.Bindings`, so a new
route, an LFO, envelope, sequencer or macro edit, a modifier, or a preset
load while held reaches the projector — plan 38's own table says so ("a
new route moves the program's param too"). The owner now calls that an
architectural flaw and asked for A/B decks: two pipelines and a crossfade.
The 2026-10-31 triage found the render side medium (a second `Renderer` on
one context already exists for hold's preview) and the control side large
(the registry, the table, the router, the presets, the library's current
and dirty dot, undo, learn and every device adapter assume one instance).
On 2026-11-02 the owner reshaped it: not A/B but **N looks, one on air**.

## 1. One line, and the words

**A deck is a look with its own controls: its registry's performance
part, its routes, macros, modifiers and banks, its graph, its renderer,
its undo and its dirty dot. Any number of decks exist; one is on air; the
outputs show the on-air deck through one mix pass.**

- **look** — what a preset saves (plan 43 says exactly what: values,
  routes, desk's preset layer, macros, modifiers, graph, banks' membership,
  layout, groups, media bins). The thing a deck holds.
- **deck** — a look loaded and running: `Deck` (new, `hyperspace/deck.py`),
  the bundle in §2's "per deck" column. The deck is what a controller, the
  panel, the library's dirty dot and undo point at. Decks are numbered
  (deck 1, deck 2 …) and have no fixed role: "A" and "B" below mean the
  on-air deck and the deck the panel points at, whichever numbers those
  are this minute.
- **on air** — the one deck the outputs show at `output.xfade` 0; during a
  fade two are, the one going on air at `xfade` and the one leaving at
  `1 − xfade`; at 1 the roles swap and `xfade` is 0 again.
- **the panel's deck** — the deck every page edits. After HOLD it is not
  the on-air deck, so nothing on the panel reaches the room until TAKE.
- **the rig** — what is not a look: the session (`params.SESSION_GROUPS`),
  the show (`library.Project`: session values, bank, startup, the bus
  cables `rig`), `bindings.json`'s session rows, the devices, the outputs,
  the analyzer, the clock. One of each, shared by every deck.

Hold becomes a deck operation (copy the on-air deck into the panel's), the
take-fade becomes the deck crossfade, and the playlist (D6) advances the
on-air deck with a fade, so the fades the owner has asked for in four
places are one mix pass. The master dim stays a dim (§5).

## 2. The singletons

Every object `app.main` builds once, who holds it, and where it goes under
the plan. "Per deck" means one per `Deck`; "shared" means one, the rig's;
"lent" means one, handed to the deck that needs it this frame. The right
column is why the code says so, not why it would be nice.

| Object | Module and symbol | Who holds it today | Under the plan | Why |
|---|---|---|---|---|
| the registry | `params.Registry`, built by `params.build_registry(view, control, audio, bank, dream, fx, restart, ghost, media)` | `app.Host.reg`, `ui.Panel.reg`, `devices.Context.reg` (every adapter: `midi.MidiIO.reg` ×14 uses, `PadDevice.act`), `learn.Learn.reg`, `undo.Undo.reg`, `library.Library.reg`, `preset.Presets.reg`, `hold.Hold.reg`, `dream.DreamWorker.reg` | **per deck** for `PERFORMANCE_GROUPS`; the `SESSION_GROUPS` params are one set of `Param` objects every deck's registry holds by reference (D3) | a `Param` *is* the base and its offsets; two looks need two bases of `view.bright`. A session param (`output.dim`, `hands.*`, `tempo.bpm`) is the room's, and `reg["output.dim"]` must keep working from any deck |
| the view state | `view.ViewState` (`s`) | `Host.view`, `app.Mouse`, `Panel`, `build_registry(view)`, `Renderer._view_now`, `Renderer.draw_outputs(s, …)` | **per deck** | the `view.*`, `rot.*`, `camera.*` params write it; `switch`, `resize`, `mattes`, `cuts`, `segments` are keyed by the preset's node names; `integrate` turns it. Plan 38's "the turn is one for both" (`hold.ONE_FOR_BOTH`) was a consequence of one `ViewState`; with one per deck each look turns at its own speed and the rule goes |
| the binding table | `routing.Bindings` | `Router.table`, `Learn.table`, `MidiIO.table`, `Context.table`, `Undo.table`, `Presets.router.table`, `seq_page` | **split** (D3): the session rows (`routing.is_session_row`: key, pad, hat, invariant and global-layer MIDI rows, sink rows; what `to_json` writes) **shared**; the preset's rows (routes, the desk's preset layer, `macros`, `modifiers`) **per deck** | `Bindings.to_json` already writes only the session rows — the file marks the seam. The referee (`referee`, `_check`) runs over one table's rows, so a deck's table must present both halves as one |
| the router | `routing.Router` | `Host.router`, `Panel.router`, `ghost.Ghost.router` (the guide's lights), `Learn.lane`, `Presets.router`, `Router.use(devices)` | **split** (D2): the shared sources — `feeds`, `labels`, `gates`, `rests`, `names`, `_codes`, `devices`, `clock`, `feed`, `felt` — one; the evaluator — `modulate`, `modgraph` / `_plan` / `_mod_states`, the banks and `_step_sequencer`, `follow_macros` / `_macro_bases`, `keys`, `pad`, `_movers` — per deck | one lane vector a frame (the analyzer's `lane`, `hand`, `ext`, `axis`) feeds every deck; each deck lands its own offsets through its own `modgraph`. `test_only_router_modulate_calls_param_modulate` pins `modulate` where it is |
| the modulator banks | `lfo.LFOs`, `envelope.Envelopes`, `sequencer.Sequencer` (each a `modbank.Bank`) | `Host.lfos`, `Panel.lfos` / `envs` / `seq`, `Router.use_lfos` / `use_bank` / `use_sequencer`, `Undo.banks` | **per deck** | `lfo`, `env`, `seq` are `PERFORMANCE_GROUPS`; a bank's membership is the preset's (`Presets.document` writes `bank.KEY` when it is not the default); they step inside the deck's pass. The clock they read (`tempo.Clock`) is shared |
| the modifiers | `Bindings.modifiers`, `Router._mod_states`, `routing.declare_modifiers` | the table and the router | **per deck** | `mod` is a performance group; the entries are the preset's (`MODIFIERS_KEY`) |
| the macros | `Bindings.macros` (`routing.Macro`, `Sub`), `Router._macro_bases`, `_macros_seen` | the table and the router | **per deck** | the preset's `macros`; `follow_macros` sets *this deck's* bases |
| the loaded preset | `preset.Presets` and its `GraphSection` (`Presets.graph`) | `library.Library.presets` (one: `lib.presets = self`, and `lib.kind(GROUP, …)` binds the kind's hooks to one instance), `Hold.section`, `Panel` (the strip), `app` (`presets.listeners`) | **per deck** | `note`, `layout`, `groups`, `unsaved`, the landed `spec` / `doc` are one look's. The library's kind registration is the seam D1 names and D5 breaks: a kind's `load` / `document` / `signature` become the panel's deck's |
| what is loaded, and the dot | `Library._current["presets"]`, `_loaded`, `Library.current(group)`, `is_dirty(group)` (`undo.alike` against `kind.signature()`), `land_unsaved`, `label` | `Presets.current`, the PRESETS strip, `watchdog.Watchdog(preset=lambda: library.current("presets"))`, `library.Marks` | **per deck** for the `presets` kind (the module groups — `band`, a session group — stay the library's) | the dot says whether *this look* moved off its file |
| undo | `undo.Undo`, and the module global `undo._installed` (`install`, `installed`, `push`, `undo`, `redo`, `_guarded`) | `Host.undo`, `Panel.undo`, `Hold.undo`; `undo.push` is called from 33 sites in 10 modules (`graphview`, `learn`, `library`, `preset`, `ui_lfo`, `ui_media`, `ui_graph`, `ui_routing`, `ui_seq`, `ui_patterns`) | **per deck**; `_installed` becomes "the panel's deck's `Undo`", re-pointed when the panel moves | a step is a gesture on one look. The module-level reach stays (the 33 sites), pointed at the deck the panel edits; `edit.undo` / `edit.redo` are session key rows and fire on it |
| the marks | `library.Marks` | `Undo.marks` | **per deck** | "what is loaded" is per deck |
| learn | `learn.Learn` | `Host.learn`, `Panel.learn`, `Context.learn` (`MidiIO.learner`, `hands.device.HandsDevice._learn`, the pad's `learn_from`), `Learn.devices` | **per deck**: the panel's | a learn is armed on a param of the panel's deck and lands a row in that deck's table; the devices offer their move to `devices.poll(learn=)` before `act`, so the on-air deck's rows do not also fire |
| the renderer and its GL | `render.Renderer` with `SceneTarget`, `CoverTarget`, `FaceTarget` ×2, `fx.FxChain`, `ghost.Ghost` (+ `_ghosts`), `lookback.Lookback` (`rings`), `lookback.Dreamer`, `render.DelayPair`s, `_frames`, `_segmenters`, `PassTimer`, `outputs.PreviewTextures` (`thumbs`), `media_tex.MediaTextures` | `Host.renderer`, `Panel.renderer`, `Hold.preview` (the second one, `hold.preview_renderer`: `Renderer(main.ctx, dream=…, fx=…, ghost=…)`, `_t0` shared) | **per deck**, on the one context | what a look renders is the look's: its graph (`wiring`), its delays' trails, its look-back rings, its effect pool. The bench (§8) is two of these |
| the effects' state | `fx.FxState` | `Renderer.fx.state`, `build_registry(fx=)`, `reg.fx_state`, `GraphSection.fx` | **per deck** | instances and values are the preset's (`FxState.hold`: exactly the section's instances exist). The files on disk (`FxState.files`) and the compiled programs (`FxChain`'s, per renderer) are not — a file saved shows on every deck, as plan 38 said |
| the dream's knobs | `lookback.DreamState` | `Renderer.lookback.state`, `Renderer.dreamer.state`, `build_registry(dream=)` | **per deck** | `dream.*` is a performance group |
| the hands' look | `ghost.GhostState` (node 1), `Renderer.ghost_states` (nodes 2…) | `Renderer.ghost.state`, `build_registry(ghost=)`; the extras from `GraphSection.states` | node 1 **shared** (`ghost` is a session group); the extras **per deck** | `ghost.register` says "session, not performance"; the extra nodes' states are declared by each deck's graph section |
| the hold | `hold.Hold` and its three controls `output.hold` / `.take` / `.drop` (`hold.register`) | `panel.hold`, `app._draw_render(hold=, monitor=)`, `GraphSection.hold`, `Presets._values` (`program_only`) | **gone in D5**; the three ids stay, as deck operations (§4) | its one job — two looks from one registry — is what a second deck does without the swap |
| the media channels' state | `media.channels.Channel` ×8: `bin`, `slot`, `fit`, `rate`, `pos`, `jog`, `loop` (the `media.*` params), `source`, `transport`, `held` | `media.channels.MediaState.channels`, `reg.media`, `Renderer.media`, `Presets.media` (the bins are the preset's `media` section) | **per deck** — the brief said shared; the code says no | `media.a.slot`, `.rate`, `.pos` are performance params and the bins are the preset's: two looks on two presets want two pictures from "channel a". Plan 38 shared the channels and admitted the cost ("switch sources after Take"). `MediaState` splits: the eight `Channel`s per deck; the rest of it shared (next row) |
| the media sources | `MediaState.resolver` (`app.MediaResolver`), `opener` (`media.adapters.open_source`), `Closer`, `media.pool` (`DaemonExecutor`s), `media.folder.MediaFolder`, `media.live.LiveKind` and `LiveSource`s, the publishers | `app.MediaIO`, `Host.media` | **shared** | a decode is one for every reader (`media.source.Latest` is a lock-free read). Two decks on one `sid` share the `Source` by reference, as plan 32's "one decode" rule wants |
| the dream worker | `dream.DreamWorker` (one torch thread, one buffer `D`, one `M`) | `Host.dream_io`, `Renderer.dreamer.source` | **shared and lent** to the on-air deck, and to the deck going on air from the first frame of a fade | ~19 ms a step on MPS: a second worker does not fit beside a frame. Two things the code adds: the worker reads `dream.*` off `self.reg` on every `submit` (`DreamWorker._params`), so a lend must hand the deck's params with the frame (a small change: `submit(frame, index, params)`); and `D` is the dream's memory, so a lend restarts the dream — the crossfade covers it. The GL half (`lookback.Dreamer`, its own `D` copy) is the renderer's, per deck |
| the segment workers | `segment.SegmentWorker` (one thread per node), `segment._shared_model` under `_SHARED_LOCK` | `Renderer._segmenters` by node name (`Renderer.segmenter(name)`, `_tend_segments`, `close`) | **per deck, as today** — the brief said shared; the code already shares what costs | the worker is keyed by node name on a renderer and tended by that renderer's graph; the torch model is shared by `_shared_model` already, and Apple Vision runs on the Neural Engine (3.6 ms). An off-air deck at preview size submits smaller frames; a deck with no graph node submits nothing |
| the analyzer | `audio.AudioEngine`, `analyzer.Analyzer` (`audio.chain`), `control.Control` | `Host.audio`, `Host.control`, `build_registry(control, audio)`, `Panel.audio` / `control` | **shared** (`band`, `scene`, `audio`, `master` are session groups) | one room, one microphone; `audio.publish(router)` names the lanes once and `Router.feeds["lane"]` is read by every deck's pass |
| the clock | `tempo.Clock` | `Host.clock`, `Router.clock`, every bank, `Panel.clock` | **shared** (`tempo` is a session group) | one beat for every deck, so a TAKE on the bar lands two sequencers on one grid |
| the devices | `devices.DeviceRegistry` and each adapter: `midi.MidiIO` per desk, `gamepad.Pad`, `hands.HandsIO`, the bridge, OSC, the clouds | `Host.devices`, `devices.Context` (`reg`, `table`, `learn`, `audio`), `Panel.midi` / `pad` / `hands` / `devices`, `Renderer.cloud_source`, `Learn.devices`, `Router.devices` | **shared**; they act on the deck controllers point at (D5: `Context` carries a deck handle, not a registry) | one APC40. `MidiIO.__init__` takes `registry` and `table` once, so "retarget" is a handle the adapter reads through, not a per-frame argument |
| the library and the show | `library.Library` (files, trash, kinds, module groups), `library.Project` (session values, bank, startup, `rig` = `graph.RigWires`) | `Panel.library`, `Presets.lib`, `Marks.lib`, `Renderer.rig_source` (`graph.rig_of` reads `.rig`), `build_registry(bank=library.project)`, the reloader's `watchers` | **shared** (the show is the session) | both renderers read the bus cables from one `Project.rig`; the `preset.*` bank params load into the panel's deck |
| the outputs | `overlay.Output` ×N (`output.*`, `output.N.*`), `outputs.Slot`, `Switches`, `Presenter`, the publishers, `outputs.Preview` ×2 (`panel.preview`, `panel.monitor`) | `Host.output` / `outputs`, `Panel.output` / `outputs` / `preview` / `monitor`, `app._draw_render(slots)` | **shared** — the room | the mix pass (D4) draws into them; `Renderer.dim` and `bg_alpha` are handed to whichever renderer draws a view |
| the hands' setup | `hands.core.HandSettings` | `Context.hand_settings`, `Panel.hand_settings` | **shared** (session) | calibration is the room's |
| keys and the mouse | `app.Keys`, `app.Mouse(render_win, reg, s, switches)` | `Host.keys` / `mouse` | **shared**, pointing at the on-air deck | the render window is the room's; `Mouse` takes `reg` and `s` once, so it reads them through the deck handle |
| the reloader | `hotreload.HotReloader` | `Host.reloader`, `Panel.reloader` | **shared**; `targets()` enumerates each deck's objects through `Deck.targets()`, as `rig.targets()` does for the devices | §8 |
| the watchdog and the keep-awake | `watchdog.Watchdog`, `RenderWatch`, `app.Awake` | `Host.render_watch`, `Panel.watchdog` | **shared** | cold modules, the process's |
| the panel | `ui.Panel` | `Host.panel` | **shared**; points at one deck (`panel.deck`) | its 21 late-assigned handles (`reg`, `router`, `learn`, `undo`, `lfos`, `envs`, `seq`, `hold`, `renderer` …, the audit's §3) become reads through `panel.deck` |

Twenty-eight objects: sixteen per deck (eleven whole, three split, the
hold gone, the channels' state), eleven shared, one lent. Nothing the brief
named as shared turned out impossible to share; two were wrong in the
other direction: the media channels' *state* is a look's and must be per
deck (their sources stay shared), and the segment workers are already per
renderer with their model shared, so there is nothing to lend. The dream
worker can be lent, but only once `submit` takes the deck's params with
the frame.

## 3. The build: D1–D6

Each step is one PR into `main`, green on the fast tier and the full suite
(`uv run pytest`, `uv run pytest --all`), the goldens unmoved
(`tests/test_golden_frames.py`: every corpus preset's pictures byte for
byte, 757 and more). D1–D3 change no behaviour and no file; D4 adds a
control that does nothing at its default; D5 is the first behaviour the
owner sees. Sizes as the audit uses them: S under a day, M a few days, L
a week or more.

### D1 — bundle today's singletons into one `Deck` (M) — **built**

*Built 2026-11-02 (wave 1, row 571).* As written, with one shape the
text left open: where `main` builds a rig object between two deck lines
(the hands' setup, the outputs' params and switches, the panel, the
devices with the dream worker, the dial and the keep-awake), `Deck.build`
takes it as a hook it calls at that very place (`hands`, `outputs`,
`panel`, `devices`; the table through `table(reg)`), so the registry's
order is unmoved and the headless `boot` runs the same lines with its
stand-ins. The panel hook is handed what exists by then (the clock, the
banks, the hold, and what the outputs hook returned), so the panel's
handles are set where `main` set them; only `panel.undo` and the new
`panel.deck` come after `build`. The rig's own wiring that declares no
param (the library's band hooks, `control.library`) stays with the
caller, before `build`, so a second deck does not wire it again. The
clock is a `Deck` field, built in `build` for now; D3+ passes the rig's
one in. `Deck.targets()` lists the deck itself first, so a save of
`deck.py` re-classes it. The hooks return what they make and `build`
threads it to the hooks after them (`RigMade` records it for `main`).
`attach`, `startup` and `install` — the steps there is one of in the
process — are switches, on by default; a second deck turns them off
until D2+ decides. The proof found one drift: the old `boot` never handed
the router its banks, as `main` has since plans 28 N0 and 31 — with
those three lines the old body and the deck agree to the bit.


**New** `hyperspace/deck.py`: a `Deck` dataclass holding what §2 marks
per deck as the objects exist today — `reg`, `view`, `table`, `router`,
`lfos`, `envs`, `seq`, `presets` (and `presets.graph`), `learn`, `undo`,
`marks`, `renderer`, `hold` — and `Deck.build(ctx, library, audio,
control, media, cfg, …)` holding the lines of `app.main` from
`s = ViewState()` to `undo.install(undo_obj)` in their present order (the
order *is* the registry order and the attach order; move it, do not edit
it). `Deck.targets()` returns the hot-reload tuples `main` lists for these
objects today, in the same order. `app.Host` gains `deck: Deck`; its flat
fields (`reg`, `view`, `router`, `lfos`, `renderer`, `learn`, `undo`)
stay for this PR, assigned from the deck, so `frame()` does not change.
`Panel` gains `deck` beside its handles; the 21 assignments stay.
`tests/test_undo.boot` — the headless copy of `main`'s construction order
that fifteen test files build on — becomes a call to `Deck.build` with the
same arguments, so the two orders cannot drift again.

- **Touches**: `app.py` (`main`, `Host`), `deck.py` (new), `ui.py`
  (`Panel.deck`), `hotreload.MODULES` (`deck` after `learn`, before
  `midi`), `tests/test_undo.py::boot`, `tests/test_app_boundary.py`,
  `tests/test_hotreload.py`.
- **Proof it changed nothing**: the goldens unmoved; and
  `tests/test_deck.py::test_a_deck_built_the_old_way_and_the_new_way_reach_the_same_state`:
  over one seeded home, the objects built as `boot` builds them at 72da1ed
  (the test keeps a copy of that body) and through `Deck.build`; load
  every `tests/corpus/presets/*.json` in turn, run 120 frames of
  `router.modulate(chain, dt, now)` + `reg.apply()` with one fixed lane
  vector, turn `view.bright` on each, `undo.undo()`; after every preset
  compare `reg.snapshot()` for every group, `table.to_json()`,
  `table.routes()`, `desk()`, `macros_doc()`, `modifiers_doc(reg)`, each
  bank's `doc()`, and the undo stack's labels and `State`s (`undo.alike`
  on the bases). Two registries must not share `Registry.serial`, `frame`
  or `landed` (class-level defaults; the test builds two and asserts the
  instance attributes diverge). An AST test, like
  `test_main_hands_the_router_its_lfos`, that `main` calls `Deck.build`
  once and `frame`'s `ORDER` is unchanged. `test_every_swap_target_lives_in_a_watched_module`
  over `Deck.targets()`.
- **Must not**: add a second registry or renderer; split anything; change
  a frame step; declare a param; touch a file format; rename an id.
- **While it is open**: `params.py`, `routing.py`, `library.py`,
  `preset.py`, `undo.py`, `hold.py` and `main` are frozen for other PRs
  (it is a conflict magnet, and short).

### D2 — split the router's shared sources from its per-deck evaluator (L) — **built**

*Built 2026-11-03 (wave 2, rows 590–593).* As written, with these
differences. **The grammar moved with the sources:** `Sources` resolves
addresses, so `BUILTIN_LANES`, `MIDI_SCHEMES`, `ROW_SCHEMES`,
`QUALIFIER`, `base_scheme`, `qualified`, `is_continuous` and `_resolve`
(with its lazy `glfw` / `gamepad` imports) live in `routing_sources.py`,
unchanged, and `routing.py` imports them back and re-exports them;
`routing.py` imports nothing lazily now. `lane_kinds` and `_codes`
(`Sources.code`) are the sources' too; `claimed` stays the router's (it
reads the table). **The router reads through:** every source-side name
`Router` had (`feeds`, `labels`, `rests`, `gates`, `names`, `lane_kinds`,
`devices`, `clock`, `use`, `follow_devices`, `schemes`, `lane`,
`address`, `feed`, `source_feel`, `felt`, `felt_lanes`) is a property or
a one-line method on its `sources`, and a router built without sources
makes its own — so the panel, Learn, the ghost (which reads the table
and `lane` through the router, unchanged) and the tests keep working.
**`devices.poll` keeps `router=`** (row 592): `act` lands the deck's rows
and `Router.pad` feeds the axes into the router's sources; the pad's
touch and motion lanes moved to `PadDevice.feed(sources)`. `feed`,
`audio.publish` and the adapters' feeds take the sources; `app.frame`
hands them `router.sources` (no `Host` field), and `Router(…, sources=)`
is keyword-only. **The tables are
followed, never read** (row 593): `Sources.follow(table)` holds every
router's table weakly and writes the rig facts into each; an address is
resolved against the asking router's own table (`Sources.resolve(source,
primaries)`, cached on the router) and a feel under its own pad feel;
the camera job's followers (`felt`) are each router's own.
**One clock** (row 590): the sources own it; the first bank's clock sets
it and a router handed another is refused. **Not yet split** (row 591):
the banks' and the modifiers' own lanes still publish into the shared
sources; each router republishes before it reads, and its `mod` vector is
its own (seeded from its own outputs, put back by assignment when
another router published, and taken out of the sources only while it is
the entry there), so two routers on different modifiers each land what
they would alone; the names and what the panel
reads between passes are D4's to layer. A router from before the build,
re-classed by a hot reload, makes sources of its own from what it held. The proof is
`tests/test_deck.py::test_one_sources_fed_once_drives_two_routers_as_one_router_did`
(three headless rigs: one over its own sources, two over one shared;
every corpus preset; each frame every param of the shared two equals the
solo one) and, from the review,
`test_two_routers_with_different_modifiers_each_keep_their_own_mod_lanes`
and `tests/test_routing_sources.py`, beside D1's test unchanged.

**New** `routing_sources.py` (the audit's split list names
`routing_schemes` / `binding` / `sinks` for `routing.py`; this is the
first cut it did not foresee): `Sources` holds `feeds`, `labels`, `gates`,
`rests`, `names` / `_names` / `_codes`, `devices` (`use`,
`follow_devices`, `schemes`, `continuous` / `row` schemes), `lane`,
`address`, `feed`, `felt` / `_felt` / `felt_lanes` / `source_feel`, and
`clock`. `Router(reg, table, sources)` keeps `modulate`, `build_modgraph`
/ `modgraph` / `_rebuild_modgraph` / `_plan`, `_step_modifier` /
`_mod_states` / `_publish_modifiers`, the banks (`use_lfos`, `use_bank`,
`use_sequencer`, `_step_sequencer`, `_banks`), `follow_macros` /
`sync_macros` / `_macro_bases`, `keys`, `pad`, `gated`, `rest_of`,
`_move` / `_movers`, `describe`; its lane reads go through `sources`.
`devices.poll` / `feed` and `audio.publish` feed the `Sources`, not a
router; `app.frame` hands `h.sources` where it hands `router` for feeding.
`routing.py` re-exports `Sources` so importers do not change in this PR.

- **Touches**: `routing.py` (`Router`), `routing_sources.py` (new),
  `app.py` (`frame`, `Deck.build`), `devices.py` (`poll(router=)` →
  `poll(sources=, …)`; the adapters' `router.feed` / `labels` / `rests`
  / `gates` writes — `gamepad.py`, `bridge.py`, `osc.py`, `hands/device.py`,
  `audio.publish`), `ghost.Ghost.router` (reads the table through the
  deck's router still), `hotreload.MODULES`, `tests/test_routing_boundary.py`
  (the import wall and the AST pin extended to the new file).
- **Proof it changed nothing**: the goldens;
  `tests/test_routing.py::test_every_factory_preset_lands_the_same_values_one_frame_earlier`,
  `tests/test_lfo.py::test_an_lfo_owning_another_lfos_depth_changes_its_output_the_same_frame`,
  `tests/test_routing.py::test_a_macro_owned_by_a_hand_scales_a_lanes_push_the_same_frame`,
  `test_a_cycle_without_a_delay_disables_its_last_cable_with_a_note`,
  `tests/test_devices.py::test_devices_run_in_list_order_poll_learn_act_then_feed_then_send`,
  `tests/test_app_boundary.py::test_the_frame_runs_in_the_documented_order`
  (`ORDER` unchanged; the stubs feed `sources`); D1's same-state test
  extended with a second comparison: one `Sources` fed once, two `Router`s
  over two registries both loaded with the same preset, every param of
  the two lands the same value every frame as one did — the first thing
  decks promise, proved before a deck exists.
- **Must not**: split the table (D3); move `modulate`
  (`test_only_router_modulate_calls_param_modulate` pins it); change any
  op or scheme string; change what `Binding` holds.

### D3 — split session params from per-deck performance params (L) — **built**

*Built 2026-11-03 (wave 2, rows 611–625).* As written, with these
shapes the text left open. **The registry** (row 611): `build_session`
declares only what has no deck-side object — the analyzer's groups, the
audio transport, `app.restart`, the undo keys — and every later session
declaration (the clock's, the hands', the outputs', the desk's, the
panel's) reaches the session through the deck's registry:
`Registry.add` hands a param `part_of` calls session to the
`SessionRegistry`, which adds the same object to every deck that follows
it, so a session param is declared once whichever deck declares it; a
deck's registry lists the session's params first (nothing reads the
order across the line, row 624). `ghost.mirror` is a session **key** of
the `ghost` group (`params.SESSION_KEYS`, row 612), written to every
deck's hands state (a `ghost.RoomSetting` on the session's param, each
state held weakly). A session param is applied **once a frame**, by the
session's lead deck alone, and every deck's pass in a frame shares the
session's mark (review of #351: two decks would otherwise release each
other's modulation). **The table** (row 614): `SessionTable` reads its rows
off the deck tables that follow it and owns the file and the session's
state; a deck's `Bindings` holds the session rows by reference and
proxies `SESSION_ATTRS`; a session row bound, added or removed on one
deck is handed to every other (`_share`); `Sources.follow` follows the
session table. **The library** (row 615): `Presets.landing` /
`current` / `loaded` / `is_dirty`, the library asking `Library._owner`.
**Media** (row 616): `MediaSources` and `Channels`, `MediaState` the old
name; V3's `audio.mix` is the session's, declared by `build_session`.
**The schema** (rows 617–622): preset `/10` (`graphmigrate.ten`: the
open show's hands' and clouds' looks and its bus cuts into an old file —
one id set, `graphmigrate.is_look_id`, for the show's reader and this one,
an id the preset's graph does not declare dropped quietly —
`modules` and `desk_template` dropped), the show `/3`
(`library.show_without_look`, `.bak-v2-look`), the bus cuts the
preset's (`Presets.bus`, key `bus`, the renderer's `rig_source`), desk
templates retired and the labels dropped (the owner, 2026-11-03),
`tools/migrate_library.py` extended (one pass, every folder down, the
show's look and cuts into every preset, every show `/3`). **The proof**:
`tests/test_session_line.py` (two decks' tables and channels over one
session; an old `/9` preset and an old `/2` show end to end; the tool on
a scratch copy), `tests/test_params.py::test_two_decks_hold_the_session_params_by_reference`,
D1's and D2's same-state tests, `test_undo.py::test_session_params_are_covered`
and `tests/test_hold.py` (its two bus-cut tests read the presets' cuts
where they read the show's); the goldens over the migrated corpus are
the orchestrator's to run, expected unmoved. **Not done** (row 625):
`hold._preset_part` sorts Drop by group (the mirror goes back with the
look); a deck that runs after the lead lands its session offsets a frame
late; the window-wanted line is not drawn yet (row 623).

The same line as plan 43's preset contract: what belongs to a look is
what belongs to a deck. Plan 43 says *which groups and rows* cross the
line (the camera, C2, among them); D3 makes the line mechanical.

- **The registry.** `build_registry` splits into `build_session(control,
  audio, bank, ghost, hand_settings, outputs, …)` → the one
  `SessionRegistry` (a `Registry`), and `build_performance(view, dream,
  fx, media_channels, …)` → a deck's. A deck's `Registry` holds its own
  performance `Param`s and the session `Param`s **by reference** (one
  `Param` object, added to every deck's registry), so `reg["output.dim"]`,
  `reg.snapshot("output")`, `undo.watched`, the panel's widgets and the
  key rows keep working from any deck, and a base written through one
  deck is the room's. `params.part_of` stays the one rule;
  `tests/test_params.py::test_every_persisted_group_is_performance_or_session`
  holds it.
- **The table.** `Bindings` → `SessionTable` (the session rows and the
  file: `load`, `write`, `backup`, `migrate_v1`, `remap_factory`, the
  sink rows, `layer` / `layers` / `desk.shift`'s latch) and a deck's
  `Bindings` holding its own rows plus the session rows by reference, so
  `bindings`, `routes()`, `desk()`, `serves`, the referee and
  `Bindings.dispatch` see one list as they do now. `register_desk` and
  `_register_pad_feel` declare session params (`desk.slew`, `desk.pad.*`)
  once.
- **The library.** `Library` keeps the files and the module groups;
  `Presets` (per deck from D5, one until then) keeps its own `current`,
  `loaded` reference and `is_dirty` — moved off `Library._current` /
  `_loaded` for the `presets` kind now, so D5 moves nothing.
- **Media.** `MediaState` → `MediaSources` (resolver, opener, closer, the
  pool, the folder) and `Channels` (the eight `Channel`s), the
  `media.*` params declared on the deck's `Channels`.
- **The schema.** This is the one bump: a preset `/N+1` and a show
  `hyperspace.project/3` whose `values` and `session` sets are plan 43's
  line, with a one-way migration in `tools/` that backs the library up
  first (the pattern of `tools/calm_lanes.py` and `routing.backup`:
  `~/Hyperspace/library-backup-<stamp>`), run between shows with both
  Macs on the build (CHECKPOINT's rule). If C2 (one camera) has already
  bumped, D3 takes the next number; the ladder is `preset.VERSIONS` and
  `library.PROJECT_SCHEMA`.
- **Touches**: `params.py` (`build_registry` → two), `routing.py`
  (`Bindings`, `register_desk`), `library.py`, `preset.py`
  (`Presets.load_doc` / `document` on the new sets), `media/channels.py`,
  `deck.py`, `app.py`, `graphmigrate.py` or a new `tools/migrate_line.py`,
  `tests/fixtures/` (a `/N` corpus copy), `docs/ENGINEERING.md` §10.
- **Proof**: the goldens over the migrated corpus (the pictures do not
  move when a value crosses the line); an old preset and an old show
  opened end to end (REVIEW.md: not only a unit test of the converter);
  D1's same-state test still passing with the session params shared by
  reference; `test_undo.py::test_session_params_are_covered` (undo still
  sees them); `tests/test_hold.py` as it stands (hold still works on one
  deck).
- **Must not**: add a deck; change any id; move a group plan 43 did not
  rule on; write a file without its backup.

### D4 — deck B in render only, and the `output.xfade` mix pass (M)

`app.main` builds two decks through `Deck.build`; deck 2's renderer is
what `hold.preview_renderer` builds today (`Renderer(ctx, dream=, fx=,
ghost=)`, `_t0` shared, `media`, `cloud_source`, `rig_source`, `bands`
handed over each frame as `hold.mirror` does). Nothing points at deck 2:
no controller, not the panel, not undo. **New** `output.xfade`, a
continuous rig control (group `output`, `persist=False`,
`modulatable=False`, learnable onto a fader) and `output.xfade_s` (the
take's seconds). `app._draw_render`: at `xfade` 0 exactly today's draw; at
`xfade` > 0 deck 2's renderer draws its outputs into frame textures at
each view's size (`render_offscreen`'s road), and **new**
`Renderer.mix_pass(target, vp, tex, k)` — a full-screen triangle beside
`dim_pass`, premultiplied blend, `k` linear — lays them over the on-air
deck's views before `dim_pass`, so the dim is the last pass as decision 28
says. The SYSTEM page's GPU lines gain a second block.

- **Touches**: `app.py` (`main`, `_draw_render`), `render.py`
  (`mix_pass`, `_build_mix`), `overlay.py` or `deck.py` (`register_xfade`),
  `ui.py` (SYSTEM page), `hotreload` targets (both decks).
- **Proof**: the goldens at `xfade` 0 (the mix pass never runs);
  `tests/test_deck.py`: `_draw_render` over stand-ins (as
  `tests/test_hold.py::test_held_the_outputs_draw_the_program_and_the_preview_follows`
  does) — at 0 deck 2 draws nothing; a GL test over the corpus: deck 2
  loaded with preset X at `xfade` 1 equals deck 1 loaded with X at
  `xfade` 0 byte for byte; at 0.5 a solid white over black reads 0.5
  within one 8-bit step; a raise in deck 2's draw costs the on-air deck
  nothing (the pattern of `_draw_preview`'s `try`).
- **Must not**: let anything write deck 2; show it on the panel; touch a
  file.

### D5 — controllers to A, the panel to B; dirty dot and undo per deck; hold = copy A into B (L)

The first PR a performer notices. **New** `deck.Decks`: the list, `on_air`
and `panel` indices, `take(seconds)`, `copy(src, dst)`. The retargets:
`devices.Context` carries a `decks` handle whose `reg` / `table` / `learn`
resolve to the on-air deck (controllers) each frame — `MidiIO`, the pad,
the hands, the bridge, OSC read through it, so `MidiIO.reg` is a property;
`app.Mouse` the same; `panel.deck` is `decks.panel`; `undo.install` is
re-pointed when the panel moves (the module-level `push` / `undo` / `redo`
reach the panel's deck); the PRESETS strip, the dot and `Marks` are the
panel's deck's; the GRAPH canvas reads `panel.deck.renderer` (where
`hold.canvas_renderer` read the preview's); the GRAPH backdrop is the
panel's deck drawn at `hold.preview_size` into the page's tap (where
`_draw_preview` drew hold's preview); the PROJECTOR inset is the on-air
deck. Then the three controls (§4). `learn` lands rows in the panel's
deck's table, armed from the panel, completed by a controller move offered
through `devices.poll(learn=)` as now. The hands' guide (`Ghost.router`)
lights what the deck it draws routes.

- **Touches**: `deck.py` (`Decks`), `devices.py` (`Context`), `midi.py`,
  `gamepad.py`, `hands/device.py`, `bridge.py`, `osc.py` (reads through
  the handle), `app.py` (`main`, `frame`, `_draw_render`, `Mouse`),
  `undo.py` (`install` by deck), `hold.py` (§4: most of it deleted),
  `preset.py` (`GraphSection.hold`, `Presets._values`' `program_only`
  filter gone), `ui.py`, `ui_graph.py` (the head's chips and red line,
  `picture_sources`, `monitor_rect`), `ui_presets.py` (the strip per
  deck), `tests/test_hold.py` (rewritten as `tests/test_decks.py`).
- **Proof**: the leak test plan 38 could not write —
  `test_nothing_on_the_panel_reaches_the_on_air_deck`: after HOLD, a route
  added, an LFO's rate moved, a modifier dropped on a cable, a macro
  turned, a preset loaded and a GRAPH edit on the panel's deck leave the
  on-air deck's `reg.snapshot()`, `table.routes()`, `modgraph` key and
  rendered frame (GL) unchanged; `test_a_controller_moves_the_on_air_deck_and_the_panel_moves_the_other`;
  `test_undo_is_per_deck` (a step on deck 2, ⌘Z moves deck 2 only);
  `test_the_dot_is_per_deck`; the three controls (`test_the_output_controls`
  rewritten: hold copies, take fades and swaps, drop copies back);
  `test_a_learn_armed_on_the_panels_deck_lands_in_its_table`; every
  `test_hold.py` test that is about the *controls' meaning* kept with its
  new body, every test about the swap (`program_value`, `keep`,
  `program_only`, `_HeldRig`, `mirror`) deleted with the code.
- **Must not**: change an id in `bindings.json` (`output.hold`,
  `output.take`, `output.drop` are learnable targets in the owner's
  session rows); change the preset format; let the on-air deck's dot or
  stack move from the panel.

### D6 — the playlist (M)

One paragraph in §6.

## 4. Hold becomes copy A into B

Today (`hold.py`, 500 lines): `Hold.engage` snapshots the held params'
bases (`held`: persisted, real, set params of `HELD_GROUPS` less
`ONE_FOR_BOTH`), the wiring, the rig cables and the extra hands states,
and the undo point; `Hold.program` swaps them in around `draw_outputs` and
back in a `finally`, each moved param written with `Param.put` as
`program_value` (held base plus this frame's offset); `Hold.keep` /
`program_only` / `PROGRAM_IDS` make `GraphSection._settle` keep the
program's instances while held and `Presets._values` leave them out of a
save; `preview_renderer` / `mirror` / `MIRRORED` build and feed the second
renderer; `canvas_renderer` points the GRAPH page at it; `_preset_part`
cuts Drop's revert to the performance groups. All of that is one look
pretending to be two.

Under D5 the three controls keep their ids and become `Decks` operations:

- **HOLD** (`output.hold` on) — `Decks.copy(on_air, panel)`: the panel's
  deck takes the on-air deck's look (`reg.restore(src.reg.snapshot(g))`
  for every performance group; `table.set_routes` / `set_desk(load=False)`
  / `set_macros` / `set_modifiers`; each bank's `set(ids)`;
  `presets.graph.land(src.spec, src.doc)`; the channels' bins and slots;
  `Presets.current`, the clean reference and `unsaved`), as one undo step
  named "hold" on the panel's deck's stack, and the panel stays pointed
  at it. From this frame the room cannot see the panel. Nothing is held:
  the on-air deck simply is not what the panel edits. `output.hold` reads
  on while the panel's deck differs from the on-air deck.
- **TAKE** (`output.take`) — `Decks.take(output.xfade_s)`: `xfade` runs 0
  → 1 over the seconds, deck B drawn at output size through the mix pass,
  the dream worker lent to B from the first frame; at 1 `on_air` becomes
  B, `xfade` returns to 0, and the panel keeps pointing at B (the look the
  room sees is the look under the operator's hands again). `xfade_s` 0 is
  plan 38's cut. The look-back's trails and the delays are B's renderer's
  and carry on through the fade, as plan 38 wanted for its cut.
- **DROP** (`output.drop`) — `Decks.copy(on_air, panel)` again: the
  panel's deck is the on-air look once more, one undo step; ⌘Z brings the
  dropped edits back, as plan 38's Drop did through `Undo.revert`.

Deleted from `hold.py` in D5: `Hold` (`engage`, `take`, `drop`, `toggle`,
`_let_go`, `_release`, `_settle`, `keep`, `program_only`, `reset_delays`,
`changed`, `rewired`, `program`, `preview_renderer`, `draw_preview`),
`held`, `program_value`, `HELD_GROUPS`, `ONE_FOR_BOTH`,
`ONE_FOR_BOTH_PREFIXES`, `MIRRORED`, `mirror`, `preview_renderer`,
`_preset_part`, `PROGRAM_IDS`, `_HeldRig`, `_rig`, `_cut`,
`canvas_renderer`, `_copy`; with them `GraphSection.hold` and the
`hold.keep` call in `_settle`, `Presets._values`' and `parts`'
`program_only` filters, `Hold.reset_delays`' seam in `Presets.load`,
`app._draw_preview`'s `hold.draw_preview` call (the function stays, drawing
the panel's deck), `ui_graph.hold_line`'s `changed()` / `rewired()` reads
(the red line says "deck 2 · 1:42 · take fades 2 s" instead), and 30 of
`tests/test_hold.py`'s 37 tests. Kept, moved to `deck.py`: `register`
(the three controls, their ids and `lit`), the tips rewritten,
`preview_size` / `PREVIEW_MAX` (the panel's deck's size off air). The
module `hold.py` goes; `hotreload.MODULES` drops it and
`tests/test_hotreload.py::test_every_package_module_but_the_cold_core_is_watched`
is the check.

What plan 38 held one-for-both and the decks do not: the turn (each deck's
`ViewState.integrate`), the media channels' state (per deck), the
modulators and routes (per deck). What stays one for both: the effect
files on disk, the clouds, the hands' source, the bands, the clock.

## 5. The crossfader and the dim

The APC40's crossfader (`apc40.CC_XFADE`, `cc:0:15`) is the master dim
(`apc40.py:536` → `output.dim`, an invariant row on both layers;
`routing.py:444` remaps the old `overlay.bg` row; DECISIONS "The
crossfader is the master dim"; register row 40: nothing may drive the dim).
It stays so. The deck fade is a new control, `output.xfade`, not the dim:
the dim multiplies the finished picture of every output (`Renderer.dim_pass`,
master × the output's own) and is the operator's black-out; the fade mixes
two decks before the dim. They compose: a fade under a half-dim fades
under a half-dim.

Until the dim has another home, `output.xfade` has no desk control by
default. It is learnable (the MASTER fader is audio drive, the CUE knob is
`view.shape` on the preset layer — `apc40.py:537` — neither is free), the
`take` button runs it over `output.xfade_s`, and the panel's GRAPH head
has the chip. If the owner later gives the dim another home (the CUE knob,
a pad trigger, a second desk), the crossfader can take `xfade` by one row
in `apc40.factory_desk`'s invariant set and the remap table — one line,
one register row. Not modulatable: a band on the crossfade would cut the
room on every kick, the argument row 40 made for the dim.

## 6. The playlist (D6)

There is no preset scheduler in the code today — the nearest things are
the bank's triggers `preset.next` / `preset.prev` / `preset.list.next` /
`preset.list.prev` / `preset.home` (`params.py:2131–2146`,
`library.Project.cycle` / `walk` / `home`) and the show's `startup`. D6
builds the playlist from nothing, over `Decks`: a `Playlist` (new,
`playlist.py`) is an ordered list of entries `{preset, dwell_s, fade_s}`
saved as its own library kind, `<library>/playlists/<slug>.json`,
`hyperspace.playlist/1` (a new folder, so no older build opens it and no
schema moves); `playlist.play` / `pause` / `next` / `prev` triggers and
`playlist.select`, rig controls in group `output` like the hold's;
`Playlist.tick(now)` loads the next entry into the deck that is *not* on
air and not the panel's (deck 3 when there are three; with two, the panel's
deck while the panel is idle, else it waits and says so), then
`Decks.take(fade_s)` — so an advance is a HOLD + TAKE nobody pressed, and
the one mix pass is the only fade in the app. The panel's deck is never
written by the playlist while the operator is editing it (the dot or an
open undo step says so). Tests: an advance over stand-in decks lands the
entry's preset in the right deck and fades; the panel's deck is never
touched while dirty; a missing preset is skipped with a note. Size M.

## 7. Decisions for the owner

**Answered by the owner, 2026-11-02: all four as recommended, 558 with
a nuance** (register rows 556–559).

1. **N looks, one on air; the deck is the thing controllers, the panel and
   undo point at** (row 556). *Recommend yes*, with two decks built in D4
   and D5 and N free from D6 (a deck beyond the two that render is data:
   its registry, table and undo exist, its renderer is not made until it
   is the panel's or going on air). The alternative — A/B with fixed roles
   and a swap — makes "which deck am I editing" a mode the operator has to
   remember; "on air" and "the panel's" are facts the head can show.
   Sub-choice: controllers follow the *on-air* deck (the room keeps being
   performed while a look is built), the panel the other. A later toggle
   "controllers follow the panel" (for tuning a look by knob before it
   goes up) is a one-line retarget once `Context` reads through the
   handle; not in D5.
2. **Hold becomes copy A into B; no hotfix of plan 38's hold** (row 557).
   *Recommend yes.* The triage's S-tier "hold honesty hotfix" (say on the
   head what a hold does not hold) would be a tooltip for a mechanism D5
   deletes; the leak itself cannot be fixed inside one registry. D5 keeps
   the three ids so the owner's learned desk buttons keep working.
3. **What is shared and lent** (row 558). *Recommend*: the dream worker
   shared and lent to the deck going on air (one worker; `submit` takes
   the deck's params; the dream restarts under the fade); the segment
   workers per renderer as today with the torch model shared as today
   (nothing to lend); the media *sources* shared and the channels' *state*
   per deck (the code's correction to the brief); the analyzer and the
   clock shared. The alternative for the dream — a worker per deck — is
   two 19 ms steps a frame on the one GPU and does not fit beside two
   renderers at the 1080p cap. *The owner's nuance (2026-11-02):* the
   look-back (its rings, its knobs) and the dream's knobs are per deck;
   only the dream worker itself — the torch step — is reserved for the
   on-air deck, and as little as possible beyond it (§2's table already
   says so). His question — a second, lower-resolution dream worker for
   the off-air (panel's) deck's preview — is possible in principle (the
   panel's deck already draws at preview size), to be measured on the
   bench in D4/D5 against the one-GPU budget of §8; not decided now.
4. **The APC crossfader stays the master dim** (row 559). *Recommend yes*
   until the dim has another home; `output.xfade` learnable, the `take`
   button its default road. The alternative — the crossfader fades decks
   and the dim moves to the CUE knob — takes `view.shape` off the desk and
   changes a row every show preset's desk layer expects.

Two questions this plan leaves to plan 43, named so they are not lost: a
deck's performer row onto a *session* param (`eye.fov`, `scene.select`:
ARCHITECTURE §3.2 allows it) — recommend the on-air deck's rows land and
the other decks' are dormant, said on ROUTING; and which groups cross the
line (the camera, C2).

## 8. Risks

**Hot reload.** `hotreload.HotReloader.targets` is re-evaluated each
reload and today lists, from `app.main`, the renderer and its parts
(`SceneTarget`, `CoverTarget`, `Lookback`, `DreamState`, `FxChain`,
`FxState`, `Ghost`, `GhostState`), `ViewState`, `MediaState` and its
`Channel`s, `MediaFolder`, `Panel`, `Control`, `AudioEngine`, `Analyzer`
and its `Params`, `Registry` and every `Param`, each `Output` and
`GlfwBackend`, each `Presenter`, `Library`, `Project`, `Marks`, `Undo`,
`Hold` and its preview `Renderer`, `Router`, `Presets`, `GraphSection`,
`Learn`, `Clock`, `LFOs` and each `LFO`, `Envelopes` and each voice,
`Sequencer` and each `Lane`, `HandSettings`, `DreamWorker`, and
`rig.targets()`. D1 moves the per-deck ones into `Deck.targets()` and
`main` concatenates every deck's; a deck made later (D6's third) is picked
up because `targets` is a callable. `deck.py` goes into `MODULES` after
`learn` (it imports `params`, `routing`, `preset`, `library`, `undo`,
`render`, `learn`, the banks, `view`) and before `midi`;
`test_the_watch_list_is_in_dependency_order` holds it. `undo._installed`
survives a reload by `globals().get("_installed")`; the per-deck pointer
keeps the trick. A `Deck` is a dataclass, so a field added later is
back-filled by `_backfill_dataclass`, but a changed `__init__` does not
re-run on live instances: every D-PR that adds a field to a live object
says "restart" in its description (REVIEW.md). `segment` stays cold.
`Registry.serial` / `frame` / `landed` are class-level defaults by design
(a registry from before a reload has them); two registries diverge on
first write, which D1's test asserts.

**The two-Macs rule.** D1, D2, D4, D5 and D6 change no file an older
build reads: D1/D2 are moves, D4's `output.xfade` and D5's deck
operations are rig controls (`persist=False`), D6 is a new folder. D3 is
the one bump (§3), landed between shows with the migration tool and the
backup, both Macs on the build before the first save — the line in
CHECKPOINT's standing rules and register row 394 (every save the newest
schema). If plan 43's C2 bumps first, D3 bumps again; two bumps between
two shows are two migrations and two backups, which the tools do already.
No row in `bindings.json` changes in any step: the hold's three ids are
kept on purpose.

**Performance.** The bench on the M3 Max at the 1080p cap: the heaviest
show preset went 6.7 → 11.9 ms a frame with two renderers drawing at
output size (both views, every pass), inside the 16.7 ms frame with ~5 ms
over; the dream worker at ~19 ms a step on MPS is the limit, on its own
thread but on the one GPU. The rules that follow, built into D4/D5: the
panel's deck draws at `preview_size` (≤ 1280 px on the long side) while
off air and at output size only during a fade; one dream worker, lent;
the render cap (`output.render`) applies to both renderers; decks beyond
the two that render build no renderer; the SYSTEM page shows a GPU block
per rendering deck so the owner sees the cost. Two renderers reading one
media channel read it twice a frame — `Renderer._media_now` is per
renderer, and a Syphon feed's `gl_poll` twice a frame may return no new
frame the second time (plan 38's hand check 6); D4 reads each channel once
a frame on the shared `MediaSources` and hands both renderers the same
`MediaFrame`. Two `Ghost`s draw the hands twice (one per deck) only during
a fade; off air the panel's deck draws them at preview size.

**The audit's order.** The structural audit (2026-10-27) put "declare what
already exists" first and the deep `Router` / `preset` / `library` splits
last. D1 is its Phase 1 (the `Host` / `Panel` late assignments become one
typed bundle); D2 and D3 pull two Phase 5 splits forward because the decks
need them, which is the one reason the audit allows. Each keeps the old
module as a re-exporting façade and extends the import-wall tests to the
new files, as the audit's §4 requires; the audit's pyright ratchet (Phase
0) is worth landing before D2 so the new seams are typed from the start.

**The hold's tests.** 37 tests in `tests/test_hold.py` (4 on GL) describe
a mechanism D5 removes; §4 says which die with the code (30) and which
keep their names with new bodies (7: the controls, the head line, the lit
desk buttons, `_draw_render` over stand-ins, the inset, `preview_size`). The PR that deletes `hold.py` is the PR that
adds the leak test plan 38 could not write.

## Read against the code: where the brief and the code differ

- "The preset scheduler becomes a playlist": there is no scheduler
  (`grep -i schedul hyperspace/` finds only device reconnect schedules).
  D6 builds the playlist from the bank's triggers and the show's startup.
- "Take-fade becomes the deck crossfade": `output.take_fade` was never
  built; plan 38 D1 (row 430) made take a cut and left the fade as a
  follow-up. The four fades the owner has met are the master dim, each
  output's own dim, the take and the playlist's; the two dims stay the dim
  pass, the other two are the one mix pass.
- "Media channels shared and lent": the `Channel`'s state is the look's
  (§2); its sources are shared. Plan 38's table had already paid for
  sharing them.
- "Segment worker shared and lent": one worker per node per renderer,
  model shared, already; nothing to lend.
- The dream worker is bound to one registry (`DreamWorker.reg`, read on
  every submit): lending it needs `submit` to carry the deck's params.
- `hold.py`'s skip of unmoved params is `Hold.program`'s `alike(p.base,
  v)` test; the brief's line number is close enough that the symbol is the
  durable reference.
