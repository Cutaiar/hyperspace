# Structural audit — 2026-10-27

Where the codebase stands on four questions the owner asked before Dylan's
UI pass and before the files grow further: the type system, the contracts
between modules, where the multi-thousand-line files split, and how far
the UI is from decoupled. Companion to [`ARCHITECTURE.md`](ARCHITECTURE.md)
(which says what the boundaries *are*) and [`AUDIT-2026-09.md`](AUDIT-2026-09.md)
(open defects). This file is about shape, not bugs.

Method: measured with scripts over `hyperspace/` (ast walk, import graph,
pyright 1.1.405 run inside the project venv), then nine small-scope reviews
one per module cluster, each reading outlines and targeted ranges rather than
whole files, then spot-checked. Line numbers are as of `7506f54`
(plan-37-specs) and will drift; symbols are the durable reference.

---

## 0. Verdict

**The architecture is better than the code.** The layer boundaries in
ARCHITECTURE §1 are real: the render stack imports no registry, routing
imports nothing above it, every leaf is a leaf, and twenty-three import
tests hold that in place. Outside `app.py` and `hands/panel.py` no
non-`ui_*` module imports imgui. That is unusual discipline for a 70k-line
app and it is the thing to protect.

What the boundaries do **not** give you is typed contracts *across* them.
Nearly every hand-off between layers is an untyped object that the receiver
probes with `getattr`, a `dict[str, Any]`, a bare string with a convention,
or an attribute that is `None` until `app.py` sets it. The package has 884
`getattr`/`hasattr` calls, six files that define a `Protocol`, and zero
`Literal`, `StrEnum` or `TypedDict`. pyright in basic mode reports 933
errors, and about 600 of them are one pattern: attribute access on a value
whose type the checker cannot see.

So the answer to "where does the type system stand" is: **good inside a
module, absent between modules.** The answer to "are the contracts clear" is:
**clear in prose (the docstrings are excellent), unenforced in code.** The
big files split along seams the authors already drew with section comments.
And the UI is decoupled at the import level but not at the data level: every
page takes the whole `Panel` and reaches through it into the registry, the
router and the library directly.

Scorecard (A = ship it, D = rewrite the shape):

| Cluster | Files | Lines | Structure | Types | Main problem |
|---|---|---|---|---|---|
| Registry + host | `params`, `tapers`, `app`, `control`, `watchdog`, `headless` | 5,100 | C | C | `build_registry` is a 700-line god-declaration; `Host`/`Panel`/`Renderer` filled by 28 late assignments |
| Routing table | `routing`, `patch`, `modifiers`, `learn`, `midi`, `apc40`, `motion` | 7,000 | C+ | C | five modules in one file; ops/schemes are bare strings; midi writes adapter scratch into persisted rows |
| Render graph | `graph`, `graphmigrate` | 8,100 | C+ | B- | four modules in one file; `Frame.r: Any` is the real renderer contract |
| Render stack | `render`, `geometry`, `ghost`, `lookback`, `fx`, `field`, `view`, `outputs`, `overlay`, `dream` | 11,900 | C- | C- | `Renderer` is 140 untyped attributes; 112 `getattr` guards; graph reaches 12 private members |
| GRAPH page | `graphview`, `ui_graph`, `placement` | 7,900 | B- | C | the one view-model split, but `st: dict` ×70 and edit logic in the drawing file |
| Panel pages | `ui`, `ui_*` (12), `hands/panel`, `seq_page` | 11,500 | C | C- | `page(panel, dt)` with `panel` untyped; per-page state as dicts hung on the panel; widget API is `panel._combo` |
| Persistence | `preset`, `library`, `config`, `undo`, `palettecompat`, `hotreload` | 7,300 | C | C- | `preset`↔`library` cycle; preset is `dict[str, Any]`; schema ladder in three files built by string surgery |
| Devices | `devices`, `gamepad`, `osc`, `bridge`, `hands/*`, `pinch` | 6,300 | B- | C+ | the one `Device` Protocol is never used as a type; 54 `getattr` in `devices.py`; `hands/` is the model package |
| Sources | `media/*`, `analyzer`, `audio`, `bands`, `lfo`, `envelope`, `sequencer`, `modbank`, `tempo` | 5,900 | B | B- | `media/` is the best-typed subsystem; `analyzer` seeds eleven arrays with `setattr` |

---

## 1. The numbers

| Measure | Value |
|---|---|
| Package | 91 files, 70,082 lines, 3,672 functions, 256 classes |
| Tests | 73,455 lines; 23 import-boundary tests |
| Files over 2,000 lines | 9 (`graph` 6,276 · `graphview` 4,776 · `routing` 3,493 · `render` 3,163 · `preset` 2,864 · `ui_graph` 2,791 · `ui` 2,704 · `library` 2,637 · `geometry` 2,195) |
| Functions fully annotated (every arg + return) | 2,544 / 3,672 = 69 % |
| Same, in `ui_*` pages | 19 % in `ui_routing`, 15 % in `ui_desk`, 0 % in `ui_lfo`. Almost entirely the untyped `panel` argument; returns are annotated |
| `getattr(` / `hasattr(` calls | 884 (`render` 112, `graphview` 85, `graph` 58, `ui` 54, `devices` 53, `hands/core` 43) |
| `__dict__` reads/writes as hot-reload shims | 36 in `routing.py` alone |
| `Protocol` classes | 7, in 6 files (`devices.Device`, `lookback.LookbackSource`, `media.source.Source`, `media.adapters.Resolver`, `media.publish.Publisher`, one in `gamepad`); only `Source` is used as a type in signatures |
| `Literal` / `StrEnum` / `TypedDict` | 0 |
| `@dataclass` | 100 across the package; `render.py` has none |
| Module-level import cycles | 1 (the `ui` ↔ `ui_*` star, harmless: nothing is used at import time) |
| Function-local imports that hide a cycle if hoisted | 12 (`library→preset`, `devices→osc/hands.device/media.*`, `seq_page→routing`, `ui_graph↔ui_fx/ui_presets`, `ui_graph→ui_lfo/ui_media/ui_seq`) |
| Type checker configured | none (ruff only). pyright basic: **933 errors** |
| pyright by rule | 419 attribute-access (undeclared attrs), 184 Optional member access, 172 argument type, 43 Optional subscript |
| pyright by file | `render` 156, `graph` 102, `graphview` 90, `analyzer` 56, `outputs` 52, `ghost` 46, `lookback` 40, `ui` 38, `app` 37, `params` 35 |
| Attributes `app.py` sets on objects after constructing them | 28 (21 on `Panel`, 7 on `Renderer`) |
| Fan-in (importers) | `params` 18, `routing` 13, `bands` 11, `graph` 9, `view`/`geometry`/`media.source` 8 |

---

## 2. Where the type system stands

**Inside a module it is decent.** The hubs are annotated (`graph.py` 349 of
384 functions, `routing.py` 160 of 186, `hands/core.py` 77 of 112) and the
good patterns are real:

- `Kind` is an enum and `Param` has one documented write path (`params.py:159`).
- `graph.Node.INPUTS: ClassVar[dict[str, str]]` with a construction-time
  port-type check — a typed, runtime-checked port contract (`graph.py:3049`).
- `Wiring`, `Wire`, the `*At` entries, `GraphSpec` are typed dataclasses.
- `routing.Binding` is a dataclass with `from_json`; `patch.py` is frozen
  dataclasses and a leaf.
- `media.frame.MediaFrame` is frozen with invariants in `__post_init__`;
  `media.source.Latest` documents its thread rules.
- `devices.Port` and `devices.PointCloud` are frozen with dtype/shape in the
  docstring.
- `tapers.Taper`, `motion.Motion`, `geometry.Layer`/`Shape`,
  `outputs.View`/`Switches`/`Handoff`, `view.ViewState`.

**Between modules it is absent.** Five patterns account for nearly all of it,
in order of how much they cost:

1. **Attributes the checker cannot see.** `Renderer.__init__` assigns ~140
   `self.x` with no class-level declarations (`render.py:995-1128`).
   `build_registry` grows `r.media`, `r.switch_state`, `r.resize_state`,
   `r.lookback_state`, `r.fx_state` onto the `Registry` from outside
   (`params.py:1224-1658`). `Analyzer` seeds eleven lane arrays with
   `setattr(self, name, np.zeros(0))` (`analyzer.py:256`). `panel.envs` and
   `panel.seq` exist only because `app.py:1350` assigns them. This is the
   419-error `reportAttributeAccessIssue` bucket.
2. **`None` until set by `app.py`.** `Panel` declares ~18 handles as `None`
   (`ui.py:692-710`), `Host` types `learn`/`undo`/`dream_io` as `object`
   (`app.py:1003`), `Renderer.cloud_source`/`rig_source`/`media` start `None`
   (`render.py:1066-1099`), `Bank.reg`/`declare` are `None` until `bind`
   (`modbank.py:73`), `graphview.Edit` takes `table/reg/router` as `X | None`
   and every method guards them (`graphview.py:2815`; `ui_graph.py:2377`
   builds `Edit(None, None, None, view)` just to call a pure helper). This is
   the 184-error Optional bucket.
3. **Hot-reload shims that erase types.** `getattr(self, "_rdepth", ...)`
   "for a renderer from before the instanced draws" (×44 in `render.py`),
   `self.__dict__.setdefault("layers", {})` (`routing.py:2194`), class-level
   defaults on `Bindings` (`routing.py:1707-1766`), `setdefault` back-fills in
   every `_state(panel)` dict (`ui_routing.py:182`, `ui_presets.py:116`).
   Each is a declared-attribute that was replaced by a probe so a reloaded
   class could meet an old instance. They are dead code except across
   reload, and they hide typos from the checker.
4. **`Any` and `dict[str, Any]` at the seams that matter most.**
   `graph.Frame.r: Any` and `.s: Any` are how every node reaches the
   renderer and the view (`graph.py:2958`); nodes call twelve *private*
   `Renderer` members through them (`_frame_target` ×11, `_refit` ×9, `_pic`
   ×4). A preset is a `dict[str, Any]` end to end (`preset.py:843, 1160`;
   `library.py:443`). The whole migration ladder is `Any` in, `Any` out
   (`graphmigrate.py:346, 933, 1025, 1280, 1474`). `Param.get/put` are
   `Callable[[], Any]` / `Callable[[Any], None]` and `value`/`base`/`set` are
   unannotated (`params.py:171-247`). `ui_graph`'s page state is `st: dict`
   in 70 signatures with ~25 keys declared in three places (`ui_graph.py:229,
   254`). `Frame.data`, `Frame.resizes`, `Frame.stats`, `Renderer.stats` are
   free-form dicts other modules read.
5. **Strings with a convention.** Routing ops, schemes, feedback kinds and
   layer names are `str` with ~69 scattered literals; `"lfo"`/`"env"`/`"seq"`
   is restated in `routing.BUILTIN_LANES`, `patch.KINDS`, `modifiers.SCHEME`,
   `lfo.LFOs.SCHEME` and `devices.BUILTIN_SCHEMES` with a test as the only
   glue. `Binding.scheme`/`kind`/`channel`/`number` each re-parse `source`
   with `split(":")`. Node kinds are `NODE_KINDS: dict[str, Any]`
   (`graph.py:611`); `wire_node_kind(name: Any)`, `new_id(name: Any) -> Any`.
   Device status is `"error: …"`/`"lost"`/`"off"` parsed by prefix. Schema
   ids are built with `f"{SCHEMA.rpartition('/')[0]}/3"` (`preset.py:182`).
   `Port.kind` and `graphview`'s `VALUE`/`TRIGGER`/`OUT` are string
   constants.

Where a `Protocol` already exists it is declared, not used: `Device` is
`@runtime_checkable` yet `DeviceRegistry.devices: list` is unparameterised and
the registry reads the protocol's own members with `getattr(d, "feeds", ())`
(`devices.py:1339-1427`); `Publisher` has no use as a type anywhere;
`Resolver` is used only inside `adapters.py` while `MediaState.__init__`
takes `resolver=None`.

**Verdict:** the project has no type *discipline*, only type *annotation*. A
checker was never run, so nothing stopped the drift. Turning pyright on in
basic mode and ratcheting (baseline the 933, fail on new) is the single
highest-leverage structural act available, and it costs nothing in behaviour.

---

## 3. Contracts between modules

**What exists.** The import-direction rules of ARCHITECTURE §1, held by
tests. Edit "doors" on the routing table (`bind`/`add`/`replace_owner`/
`unbind`, raising `Owned`). `Param.set*` as the only base writer.
`Router.modulate` as the only offset writer (test-pinned). `Registry`'s
read/write surface (`add`, `[]`, `get`, `ids`, `apply`, `snapshot`,
`restore`) is clean. These are good contracts and the docstrings describe
them precisely.

**What is missing.** The *shape* of what crosses each boundary. Per seam:

| Seam | Today | Evidence | Should be |
|---|---|---|---|
| graph nodes → renderer | `Frame.r: Any`; nodes call 12 private `Renderer` members | `graph.py:2958`; `render.py` `_frame_target`, `_refit`, `_pic`, `_timed`, `_show`, `_pattern_into`, `_face_plain`, `_draw_cover`… | a `RenderHost` Protocol in `graph.py` naming those members publicly; `s: ViewState` |
| app → renderer, per frame | attribute writes (`renderer.bg_alpha = …`, `dim`, `max_frame`, `bands`) | `app.py:1153-1195` | a `FrameInputs` dataclass passed to `draw` |
| app → panel | 21 post-construction assignments; `Panel(...)` takes 7 args | `app.py:1349-1523`; `ui.py:658` | a `PanelDeps` dataclass (or constructor kwargs) with typed handles |
| pages → everything | `page(panel, dt)`, `panel` untyped; pages read `panel.reg` (×84), `panel.library` (×26), call `panel._combo` (×18), `panel._section` (×17) | all `ui_*.py` | `page(ctx: PageContext, dt)`; widgets on `ctx.widgets`; commands on `ctx.cmd` |
| devices → routing | untyped `router`, `reg`, `learn`; values pushed into `router.names[scheme]`/`labels`/`rests` dicts; rows as strings `"pad@p2:A"` | `devices.py:199-208`, `gamepad.py:739-808` | `RouterHost`/`LearnHost` Protocols listing the five or six members devices call |
| registry → adapters | `Device` Protocol declared, members read by `getattr`; `io`/`cloud`/`media_sources` not in the Protocol | `devices.py:157, 1339-1427, 1488, 1503` | use the Protocol as the type; add the missing members; `devices: list[Device]` |
| midi → routing rows | adapter writes `b.caught`, `b.last_hw`, `b.last_out`, `b.lit` into persisted `Binding`s (26 sites) | `midi.py:431-1140`; `Binding._RUNTIME` | per-adapter dicts keyed by row id, as `_writes`/`_hw` already are |
| midi/learn → profile | `PROFILES = {"apc40": apc40, "generic": generic}`; modules probed for `PORT_MATCH`, `feedback_for`, `named`, `glyph` | `midi.py:130`, `learn.py:493, 529, 555` | a `DeviceProfile` Protocol; `generic.py` exists only to satisfy the implicit shape |
| build_registry → subsystems | `build_registry(view, control, audio, bank, dream, fx, restart, ghost, media)` with no annotations; `getattr(view, "switch")` + try/except ×3 | `params.py:1199, 1227-1252` | `ViewLike`, `AudioLike` Protocols; per-subsystem `declare_*(r, …)` |
| preset ↔ library | real cycle: `preset` imports 17 names incl. private `_module_values`, `_write_text`; `library` imports `preset` lazily for schema-1 migration; `lib.presets = self` back-pointer | `preset.py:129-148, 782`; `library.py:323, 1189, 885` | move schema-1 migration to `legacy.py`; `Project.load` takes a `migrate_v1` hook; `PresetLoader` Protocol |
| preset → every subsystem | `Presets.load_doc`/`document` hard-code every section key; 16 module imports | `preset.py:843-1400` | each subsystem owns `to_doc`/`from_doc`; `Presets` loops over registered sections (as `lib.kind()` already does) |
| graphview ← domain | `build(bindings, reg, router, devices, graph, …)` with six untyped inputs; `View.spec: Any` | `graphview.py:1158, 299` | annotate; Protocols for `devices`, `profile`, `slots` |
| render ↔ media | `graph.MEDIA_CHANNELS = "abcdefgh"` separate from `channels.CHANNELS` (held equal by `tests/test_media_render.py:108`); `Renderer.media` untyped | `graph.py:192`, `render.py:1094` | a `MediaView` Protocol (`frame(c)`, `status(c)`, `playhead(c)`); the test is doing a constant's job |
| devices → graph | `getattr(frame.r, "cloud_source", None)`; `graph.PointCloud` (a node) vs `devices.PointCloud` (a frame) share a name | `graph.py:3501`, `devices.py:951` | `CloudSource`/`CloudFrame` Protocols on the render side; rename one |
| config → subsystems | deferred imports of `outputs.MAX_OUTPUTS`, `hands.core.DEFAULTS`, `overlay.RENDER_NAMES` for validation limits | `config.py:428, 492, 679, 742` | inject the limits or a leaf `limits.py` |
| ghost → hands | three function-local `from .hands.core import SIDES, PALM_W, default_range` because `params` imports `ghost` and must not pull the hands adapter | `ghost.py:198, 383, 461` | a leaf `hands/ranges.py` |

**Frame-slot state through hidden attributes.** `HandsDevice` stashes
`_learn` and `_dt` in `learn()`/`poll()` and reads them in `feed()`
(`hands/device.py:44, 114`); `Router.modulate` evaluates `self.patch` for
effect and then reads `self.__dict__["_plan"]` (`routing.py:3361`). The
poll → learn → act → feed → send order is documented; the data each slot
hands the next is not an argument.

**Counters, not events.** `layer_serial_of`, `page_serial`,
`modifiers_serial`, `macros_serial` are polled by `MidiIO._seen` and
`Router._macros_seen`; `ui_routing.py:1221` bumps `table.macros_serial += 1`
by hand. Consistent, but every consumer must know the convention.

**The one good counter-example is `hands/`.** `core.py` imports only
`signal`, `tape` and `mido`; `__init__` has a curated `__all__` and a
docstring on how to host it; `device.py` is the one host-aware piece and
imports one name; `panel.py` is the UI in its own file. It is the template.
`media/` is the second: one concern per file, three Protocols, a frozen
frame. Its weakness is the same as everywhere: the Protocols are not used as
parameter types.

---

## 4. Where the big files split

Every proposal below keeps the test-held import walls, keeps the old module
as a re-exporting façade so the importers do not change in the first pass,
and follows seams the files already mark with section comments. Risk is
about hidden coupling found while moving, not about behaviour change. The
boundary tests parse `Path(module.__file__)` only, so **each split must
extend its test to the new files** (`tests/test_graph.py:66`,
`tests/test_routing_boundary.py`, `tests/test_render.py`) or the wall goes
unchecked.

### `graph.py` (6,276) — four modules in one

Confirmed: (a) spec/wiring/reader 215-2907 (~2,700 lines, no GL), (c)
pure algorithms inside that range, (b) GL node classes 2910-5275 (~2,350),
(d) `Graph`/`build_graph`/`_Build` 5421-6276.

| New module | Symbols / lines | Imports | Risk |
|---|---|---|---|
| `graph_wiring.py` | constants 130-215, `HandsAt`…`CopyAt` + `_*_entry` 235-1480, `Wire`/`Wiring`/`RigWires`/id tables 744-1290, `GraphSpec`/`read_graph`/`NODE_KINDS` 2041-2469 | `re`, dataclasses, `view` constants, `lookback.MAX_ECHOES` | M — `*At` helpers interleave with validators |
| `graph_check.py` | `wire_error`, `_wired_error`, `wire_loops`, `loop_closers`, `loop_words`, `placement_loops` 410, 505, 1593-1916 | `graph_wiring` | L — pure |
| `graph_reach.py` | `reaches`, `run_of`, `run_back`, `source_into`, `channel_into`, `output_ports`, `through_of`, the `*_words` 2478-2907 | `graph_wiring` | L — pure; `ui_fx`, `ui_media`, `learn` then stop importing a GL module |
| `graph_nodes.py` | `Frame`…`Output` 2910-5275; later `nodes_base` / `nodes_media` / `nodes_time` / `nodes_out` | moderngl, numpy, geometry | H — `Effect` (285 lines) and `Output` cross-reference; `Frame.graph` forward-refs `Graph` |
| `graph_build.py` | `Graph`, `graph_key`, `build_graph`, `_Build`, `signature` 5421-6276 | all above | M — `_Build._make` (104 lines) wants a kind→class table |

Safe first cut: (a)+(c) only, ~3,400 lines, zero GL. `graphmigrate.py`
splits along its own rungs (`migrate_free` 346-760, `migrate_wired`
892-1360, `migrate_seven` 1474-1787) at low risk.

### `graphview.py` (4,776) + `ui_graph.py` (2,791)

| New module | Symbols / lines | Risk |
|---|---|---|
| `graphview_types.py` | `VPort`/`VNode`/`VCable`/`View`, constants 120-325 | L |
| `graphview_render.py` | render-node vocabulary, `LABELS`/`HOVERS`/`OWNERS`, `kind_of`…`media_made` 330-1155 | L |
| `graphview_build.py` | `build` (one 518-line closure, 1158-1675), `refresh`, `device_node(s)`, `template_rows` | M — carve `build` into per-kind builders |
| `graphview_layout.py` | `Layout`, `layout`, `auto_layout`, `home`, `split`, `preset_only` 1906-2419 | L |
| `graphview_bundle.py` | `VBundle`, `wiring`, `readings`, `bundle_tip`, `land_choices` 2443-2689 | L |
| `graphedit.py` | `Edit` + `Refusal`/`Ask` 2747-3431 | M |
| `graphedit_render.py` | `render_*`, `_land`, `_frame_order`, `starter`, `picker` 3440-4530 (take `edit` as first arg → methods or a ctx) | M |
| `graphedit_picture.py` | `page_spec`, `picture_*`, `set_picture`, `set_through` 4564-4776 | L |
| `ui_graph_state.py` | `_state` and open/fold/hide/idle 229-527, **as a dataclass** | L |
| `ui_graph_side.py` | `_selection`, `_side`, `_node_side`, side groups 1606-1988 (where the deferred `ui_lfo`/`ui_media`/`ui_seq` imports sit) | M |
| `ui_graph_edit.py` | `edit_of`…`delete_*` 2007-2607 — ~500 lines of orchestration (`_act`, `_settle`, `dropped`, `*_cut`, `route_from_*`) that belongs next to `Edit` with an `EditContext`, not `panel` | M |
| `ui_graph_menus.py` | `_menus`…`picker` 2610-2791, `render_picker` 1490-1601 | L |

### `routing.py` (3,493) — five modules in one

| New module | Symbols / lines | Risk |
|---|---|---|
| `routing_schemes.py` | constants 252-600, `base_scheme`/`qualified`/`is_continuous` — the home for a `StrEnum` of ops and schemes | L |
| `binding.py` | `Owned`, `Binding` 594-853 | L |
| `sinks.py` | `sink_target`, `parse_sink`, `sink_refusal`, `sink_rows_from_send`, `sink_values` 899-995 | L |
| `routing_io.py` | `bindings_path`, `migrate_v1`, `backup`, `remap_factory`, `legacy6_routes`, `dumps_doc`, `Bindings.load/from_json/to_json/write` 998-1283, 1824-2012 | M — `load` is a classmethod |
| `desk.py` | `register_desk`, `_register_pad_feel`, `led_*`, `sort_layers`, `factory_desk`, `declare_modifiers`, `Carried` 1353-1704 | L-M — `midi`, `ui_desk` import these |
| `macros.py` | `Sub`, `Macro`, `macros_of`, `base_refusal`, `settle_bases`, `Bindings.set_macros`, `Router.sync_macros/follow_macros` 1301-1400, 2708-2756 | M |
| `referee.py` | `referee`, `save_refusal`, `Bindings._check/bind/add/replace_owner/enable/unbind` 1059-1131, 2338-2490 — the edit doors; keep as a mixin | M |
| *(stays)* | `Router.modulate`, `build_patch`, `_step_modifier` 2956-3464 — `test_only_router_modulate_calls_param_modulate` pins it here | — |

Also: `midi.py` → `midi_ports.py` (`Ports`, `find_port`, `Slew`,
`DeskEvent`, `DeskLog` 141-307) and `midi_feedback.py` (996-1152, where the
`Binding` runtime writes can be isolated). `learn.py` → `learn_rules.py`
(`ranked`, `cannot_show`, `row_for`, `blocked`, `drawn_of` 125-376, pure).

### `render.py` (3,163) — `Renderer` is 2,089 lines, 73 methods

| New module | Symbols / lines | Risk |
|---|---|---|
| `render_shaders.py` | GLSL constants 209-621, `TILE_FS_HEAD` 3125 (~400 lines of strings) | very L |
| `render_targets.py` | `SceneTarget`, `CoverTarget`, `DelayPair`, `FaceTarget`, `PassTimer`, `_Timed` 646-991 (own their GL, have `release()`) | L |
| `render_scene.py` | `draw_scene` 2661-2944 (284 lines), `_depth_pass`, `_field`, `_legacy_field`, `_copies_of`, `_PanPx` | M |
| `render_media.py` | `media_texture`, `_media_fit`, `_refit`, `_sampler`, `ui_*` 1686-1860 | M — graph calls `_refit` |
| `render_faces.py` | face/pattern pipeline 1250-1346, 2314-2574 | M — shares `_ptime`, `_view_now` |
| `render_compose.py` | `_compose`, `_show`, `lay`, `_frame_target`, `pool_at`, delays, rings 1878-2300 | M — graph calls `_frame_target` ×11 |
| *(stays)* | `__init__`, `draw*`, `_draw_frame`, `on_reload`, `render_offscreen` (~500) | — |

Prerequisite: give the twelve private members graph.py calls public names
(the `RenderHost` Protocol), or every split drags graph with it.
`geometry.py` → `shapes_4d.py` (24-430), `shapes_3d.py` (433-1440), keep
cache + camera (L). `ghost.py` → `ghost_pose.py` (190-660, pure numpy,
takes ranges as args — removes the deferred imports), `ghost_labels.py`
(660-800, PIL), `ghost.py` GL (1165-1836).

### `preset.py` (2,864) + `library.py` (2,637)

| New module | Symbols / lines | Risk |
|---|---|---|
| `preset_factory.py` | party/lfo_breathe/seq_demo/hands generators, `Factory`, `write_factory`, `knob_desk`, `effects_on` 1473-2185 (~700, pure) | L |
| `legacy.py` | schema-1 migration `preset.py:2192-2859` + `library.py:303-391` — **this is the cycle cut** | M — `migrate_home` call order at startup |
| `preset_doc.py` | `GraphSection` 303-506, `dumps`, `expand_desk`/`compact_desk`, `merge_modifiers` 552-746 | L-M |
| `schema.py` | one ordered ladder (`PRESET_1`…`WIRED_7`, `PROJECT_1/2`, `DESK_1`) replacing `library.py:165-189`, `preset.py:182-190`, `graphmigrate.py:58-67` | S |
| `project.py` | `Project`, `Marks`, `_kept`, `_bank_len` `library.py:667-1470` | M |
| `libtrash.py` | `to_trash`, `Trashed`, trash/restore/empty, `_scan`/`_sync`/`poll` 486-558, 2404-2637 | L |
| `config_devices.py` | `_screen`…`_devices` `config.py:338-674` | L |

### `params.py` (1,895) and `app.py` (1,609)

`params.py`: the core (`Kind`, `Param`, `Registry`, 159-877, ~720 lines) is
a leaf that only needs `tapers`; the other ~1,175 lines are `build_registry`
(1199-1895) and its declaration clusters. Split into `registry.py` (core,
re-exported as `params`) and a `declare/` package — `view` 1263-1530,
`lookback` 1531-1650, `fx` 1650-1661, `audio`/bands/scene/macros
1662-1895, `bank` 1791-1851, plus the existing `declare_switches/resizes/
lookbacks` 938-1170 — with `build_registry` left as ~40 lines calling them
in the current order (the order *is* the registry order; keep it). This
moves ten subsystem imports out of the most-imported module in the package.

`app.py`: `inputs.py` (`Keys`, `Mouse`, `flipped`, `_zoom_about`,
`_ride_depth` 844-999, L), `windows.py` (231-575, M), `wiring.py`
(`_open_devices`, `_open_dream`, `MediaIO`, `MediaResolver`, `_open_media`
162-228, 684-831, L-M), `host.py` (`Host`, `frame` 1003-1225 — importable
without GLFW, L). Leave `main()` (361 lines, 1245-1605) where it is; its
closures reference `host` before it exists and it is the one place
construction order lives.

### `ui.py` (2,704) and the pages

`ui_widgets.py` — the stateless helpers at 152-553 (`tooltip`, `chip`,
`lit_chip`, `fit_text`, `dirty_dot`, `shows_line`) plus the Panel widget
methods at 761-1463 (`_ctx*`, `_slider`, `_fader`, `_combo`, `_check`,
`_button`, `_track`, `_ghost`, `_section`, ~700 lines) as a `Widgets` class.
This is the actual shared widget library and the unit Dylan would restyle.
`ui_system.py` (2268-2704), `ui_output.py` (1811-2220); Panel drops to
~1,100 lines of shell. `ui_routing.py` → `routing_ops.py` (no imgui:
`add_route`, referee ask/answer, `_sources/_gates/_scales`, modifier ops,
`shared_bases`, ~35 % of the file) + `ui_routing_modifiers.py` +
`ui_routing_macros.py`. `ui_presets.py` → `_lists` + `_bank`. `ui_seq.py`
needs nothing; it is the cleanest page.

### Smaller

`devices.py` → `devices_base.py` (`Port`, `Device`, `Context`, `Base`, the
three placeholder devices 99-420 — ends the `kinds()` lazy imports of `osc`
and `hands.device`), `device_midi/pad/bridge.py`, `clouds.py` (935-1155),
`device_config.py` (watch + reload 1590-1723). `gamepad.py` →
`gamepad_usb.py` (289-465), state, `gamepad_route.py` (734-858).
`hands/core.py` → `features.py` (254-682), `settings.py` (683-1143), io
(1145-1972; keep `HandsIO` where `targets()` names it for hot reload).
`analyzer.py` → `analyzer_bands.py` (101-235), `spectrum_history.py`
(442-476). `media/channels.py` → `closer.py`, `bins.py`.

---

## 5. How close is true UI decoupling

**Import level: done.** Only `app.py`, the `ui_*` modules and
`hands/panel.py` import imgui. `graphview` is tested never to. Domain
modules do not import `ui`. A designer cannot break the engine by editing a
page.

**Data level: not started, with one exception.** The GRAPH page is the
exception: `graphview.py` builds `VNode`/`VCable`/`VPort` data from the
domain and `ui_graph.py` draws it; `Edit` is a command object returning
`None | Refusal | Ask`. That is the right shape. Even there, ~500 lines of
decision-making (`_act`, `_settle`, `dropped`, `_delete`, the `*_cut`
family) sit in the drawing module, `ui_graph` bypasses `Edit` for
`router.table.remove` (1953), `panel.reg[...].set` (680, 1864, 1939), five
direct `undo.push` calls and a private `ui_routing._row` (1950), and the
page state is `st: dict`.

Everywhere else the shape is `def page(panel, dt)`:

- Pages read domain handles off the panel directly: `panel.reg` ×84,
  `panel.library` ×26, `panel.renderer` ×8, `panel.audio` ×7, `panel.learn`
  ×6, plus `router`, `midi`, `bank`, `control`, `view`.
- Pages mutate domain state directly. Mostly through the right doors
  (`Param.set*`, `table.enable/move_route`), but also by hand:
  `table.macros.setdefault(mid, Macro())` and `table.macros_serial += 1`
  (`ui_routing.py:1216-1221`), `panel.library.save_as/rename`
  (`ui_presets.py:409-425`), `router_of(panel)` *creating* and assigning
  `panel.router` from inside a read (`ui_routing.py:356`).
- `undo.push` is written by hand at the start of each UI operation — 17
  sites in `ui_*.py` plus 5 in `ui_graph.py`. Undo is a UI-layer chore
  instead of part of the command.
- Per-page state is a dict hung on the panel by `getattr`/`setattr` with
  `setdefault` back-fills (`_routing_state` `ui_routing.py:177`,
  `_lib_state` `ui_presets.py:111`, `STATE` `ui_media.py:101`, `_state`
  `ui_fx.py:572`, `_seq_lane`/`_seq_env` `ui_seq.py:119-146`, dynamic
  `setattr(self, key, …)` in `_graph_edit` `ui.py:2044`).
- The widget API is private Panel methods called from other modules:
  `panel._combo`, `panel._section`, `panel._ctx`, `panel._slider`,
  `panel._check`, `panel._tip`, `panel._label_cell`. Every page also
  hand-rolls `imgui.begin_combo` loops.
- Page dispatch is nine one-line forwarders `_page_x(self, dt)` at
  `ui.py:2339-2355`; `PAGES` is `(key, label, group)` only.
- Line mix (rough AST count): `ui_routing` 33 % widget calls, ~25-30 % pure
  domain logic, the rest layout glue; `ui_presets` 30 % / ~20 %; `ui_seq`
  36 % / <15 %.

**Domain text in domain files.** Tooltips and display formatters live in
`lfo.declare`/`envelope.declare`; `*_words` presentation helpers in
`graph.py:2710-2907`; `Library.say`, `Undo.status` "for the footer",
`Bindings.said`/`notes`, `Learn.said_n` are footer strings on domain objects.
`Presets` carries editor state (`layout` = GRAPH node positions, `notes`,
`unsaved`). UI-facing renderer entry points (`ui_upload`, `ui_texture`,
`pattern_tile`, `swatch`, `media_shown`, `_for_the_panel`) are methods on
`Renderer`. `view.RED` duplicates `ui.RED`. `ghost.py:678` locates the
panel's font through `find_spec`. `DeviceRegistry.listeners` pushes live
adapter objects *into* the panel.

**Could Dylan restyle a page without reading `routing.py`?** Not today. The
routing page's `_row` (`ui_routing.py:689-833`, 145 lines) does the combo,
`table.move_route`, the `Owned` referee prompt and the error text in one
body, and needs `Binding`, `Owned`, `Macro`, `Motion`. `ui_seq`, `ui_desk`,
`ui_pad` and `ui_bands` are nearly pure drawing and are where a restyle
could start.

**The target shape, grounded in what exists** (graphview's split, `ui_seq`'s
pure helpers, the `Edit` command object):

```python
@dataclass
class PageContext:            # built once by app.py; replaces the 21 late assignments
    reg: Registry
    router: Router
    library: Library | None
    clock: Clock | None
    seq: Sequencer | None
    # … every handle Panel has today, typed; Protocols where tests pass stubs
    state: PageState          # one dataclass per page; replaces _x_state dicts
    widgets: Widgets          # slider/combo/check/ctx/tip, out of Panel
    cmd: Commands             # add_route(...) -> Added | NeedsReplace, toggle_step(...);
                              # each command does its own undo.push

def page(ctx: PageContext, dt: float) -> None: ...
```

Measured against that: the data (`PageState`) exists only for GRAPH; the
commands exist only for GRAPH (`Edit`) and partially in `ui_routing`'s
free functions; the typed context exists nowhere; the widget library is
half there (`ui.py` helpers) and half on `Panel`. Call it **one page out of
fourteen**, with the pattern proven.

---

## 6. What to do, in order

Each step is independently shippable, changes no behaviour, and makes the
next cheaper. Sizes: S < a day, M a few days, L a week-plus. The order puts
checkability first, because nothing after it can be kept honest without it.

**Phase 0 — turn the lights on (S).**
Add `[tool.pyright]` basic mode with a baseline file; CI fails on *new*
errors. Add a `tests/test_structure.py` that asserts no module in
`hyperspace/` exceeds N lines (start N = 7,000 and ratchet) and extends the
import-wall tests to glob `graph*.py`, `routing*.py`, `render*.py`. From
here every PR below reports a number going down.

**Phase 1 — declare what already exists (M, ~-500 pyright errors).**
No moves, no renames; only make implicit attributes explicit.
1. Class-level annotations on `Renderer` (`render.py:995`); delete the 44
   `getattr(self, …)` reload guards or collapse them into one `_ensure()`.
2. Declare `Registry.media/switch_state/resize_state/lookback_state/fx_state`
   in `__init__` (`params.py:688`).
3. `Analyzer`: a `BandLanes` dataclass instead of `setattr` seeding
   (`analyzer.py:256`).
4. `Panel`: declare `envs`/`seq`; type the 18 handles (`ui.py:692`).
5. `Bindings`/`Router`/`Learn`: declare `layers`, `_lanes`, `_names`,
   `_plan`, `_movers`, `clock`, `lane`, `devices`, `said_n` in `__init__`
   (`routing.py:2194, 3361`).
6. `graphview.Edit`: make `table/reg/router` required; move `type_of`/
   `is_render` to module functions (`graphview.py:2815`).
7. Replace `st: dict` with `GraphPageState` (`ui_graph.py:229`) and each
   `_x_state(panel)` dict with a dataclass.

**Phase 2 — name the contracts (M).**
Protocols and enums at the seams in §3, in this order of payoff:
`RenderHost` for `Frame.r` (+ public names for the twelve privates);
`FrameInputs` for the per-frame renderer writes; `RouterHost`/`LearnHost`
for devices; use `Device`/`Resolver`/`Publisher` as types; `DeviceProfile`;
`ViewLike`/`AudioLike` for `build_registry`; `StrEnum`s for routing ops and
schemes, node kinds, device status; `schema.py` for the version ladder;
`TypedDict`s for a wire, a node entry and a graph section in `graphmigrate`;
one `CHANNELS` constant and a `MediaView` Protocol. Move MIDI runtime state
off `Binding` (`midi.py:431`).

**Phase 3 — the zero-GL, zero-risk splits (M).**
`graph_wiring`/`graph_check`/`graph_reach` out of `graph.py`;
`routing_schemes`/`binding`/`sinks` out of `routing.py`; `render_shaders`/
`render_targets` out of `render.py`; `preset_factory` and `legacy.py` out
of `preset.py`/`library.py` (the cycle cut); `registry.py` + `declare/` out
of `params.py`; `devices_base.py`; `hands/ranges.py` (ends the ghost
deferred imports). About 12,000 lines move with façade re-exports; no
importer changes.

**Phase 4 — the UI shape, one page at a time (L, and this is Dylan's
runway).**
`ui_widgets.py` first (the restyle unit). Then `PageContext` built in
`app.py` replacing the 21 assignments, with `page(ctx, dt)` adopted page by
page starting with `ui_seq` (cleanest), `ui_desk`/`ui_pad`/`ui_bands`
(pure drawing), then `ui_routing` after `routing_ops.py` pulls its ~30 %
domain logic out. Move `ui_graph`'s edit orchestration into `graphedit`.
Each command carries its own `undo.push`. Page dispatch becomes a table.
When this is through, a page is "take a typed context, call commands, draw"
and a designer can replace the drawing without reading the domain.

**Phase 5 — the deep splits (L, last, highest risk).**
`graph_nodes`/`graph_build` with a kind→factory table in `_Build`;
`render_scene`/`render_compose`/`render_faces`; `graphview_build` with
`build` carved into per-kind builders; `Router` persistence/desk/macros/
referee modules; per-subsystem `to_doc`/`from_doc` so `Presets` stops
knowing every section.

---

## 7. Caveats

- Line numbers are from `7506f54`; use the symbol.
- The reviewers read outlines plus targeted ranges, not every line. Bodies
  of `build_registry`, `Bindings`/`Router` beyond `modulate`, `_Build`,
  `main()` and `apc40`'s factory rows were sampled, not read through.
- The 69 % annotation figure counts a function as annotated only when every
  parameter and the return are; the pages' low numbers are almost entirely
  the untyped `panel` argument.
- `seq_page.py` imports `routing.Binding` lazily (`seq_page.py:55`) while
  `routing` imports `seq_page` at module level — one more hidden two-way
  edge, listed in §1's count of twelve.
- Not checked: whether `devices.Context`'s `object` fields could be the
  concrete classes without a cycle.
- `palettecompat.py`'s 18 pyright errors were not root-caused.
