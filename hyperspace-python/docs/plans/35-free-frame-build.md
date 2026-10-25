# Plan 35 Free Frame Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every node of the frame is an ordinary node and every wire an ordinary wire. A section says `"frame": "wired"`, the renderer builds only what its wires reach, an output shows what is wired into it (else `output.all`'s, else its ground), and every old preset migrates to the wiring `default_graph` builds for it today, with no golden moving. GRAPH deletes anything, OUTPUT and LOOKBACK read and write the wires, and a **new** chip starts a blank preset.

**Architecture:** In `graph.py`'s data half the marker, the frame kinds' entries, `copy`, `output.all` and the new ports join the wire vocabulary. `reaches` becomes a fixpoint from the output ports and `lookback.capture`. In the render half, `build_graph` makes nodes from the reached wires alone. `Shown` (today's `Fx` and `Wired` made one) keeps the direct paint and the stand-down. `Output` reads its own ports, else `output.all`'s, through the window's mutes. `graphmigrate.frame_wires` / `output_wires` write today's frame as wires; `migrate` marks every section; `legacy_section` strips a frame only by round trip. Then the pipelines are deleted, and GRAPH, OUTPUT, LOOKBACK and the PRESET strip become views and edits of the wires.

**Tech Stack:** Python 3.14 (`.python-version`), moderngl, numpy, imgui-bundle (`imgui_node_editor`); pytest via `uv run pytest`.

**Spec:** [`35-free-frame.md`](35-free-frame.md), with rows 372–393. The owner answered rows 373 (approve, rename ids too), 374 and 387 (approved) on 2026-10-24; nothing waits. Read the spec first; this plan does not repeat its reasons.

## Global Constraints

- Work under `hyperspace-python/`. The integration branch is `plan-35-free-frame`, cut from `plan-34-feedback` @ ce0b0c6 (plan 34 T3 and its fixes). Each task goes on its own branch `plan-35-t<n>` in its own worktree, merged into `plan-35-free-frame` in order. Plan 34 T4–T6 are rebased onto `plan-35-free-frame` afterwards (the spec's "What changes for plan 34").
- **No existing golden moves.** All 717 in `tests/golden/frames/frames.json` (the count at the base: check it with `jq '.goldens | length'` before T1, and use that number throughout) must match after every task (`uv run pytest tests/test_golden_frames.py -q`, on the M3 Max that recorded them). New goldens come only from T3's three fixtures (3 × 8 states = 24), recorded with `uv run python tools/golden_frames.py --record --only blank-frame,channel-out-only,through-one-output`.
- **No file under `hyperspace/library/` is edited.** Fixtures go under `tests/fixtures/presets/`, force-added (`tests/fixtures/` is ignored).
- `apc40.py`, `midi.py`, `bindings.default.json` and the desk are untouched (Dylan's).
- `graph.py` imports no params, preset or media module (`tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`). `graphmigrate.py` stays pure data (it imports `graph` and, from T2, `outputs` for nothing but `MAX_OUTPUTS`).
- **The schema is `hyperspace.preset/6`** (row 385): `/6` is `/5` with the wired frame in the new ids. `preset.VERSIONS = (2, 3, 4, 5, 6)`, and `graphmigrate.WIRED_SCHEMA = "hyperspace.preset/6"`. A `/2`–`/5` file is read in the old ids and renamed on load (`graphmigrate.renamed`). A save writes `/4` or below when the round trip says so (as today, byte for byte), else `/6`; **nothing writes `/5` any more**. A plan 33/34 build refuses a `/6` file by the ladder's own words. Both Macs need this build.
- **Ids and params:** node ids are renamed (`NEW_IDS`, T1); **param ids never change** (`ghost.*`, `dream.*`, `media.<c>.*`, `eye.*`, `camera.*`, `pattern.*`, `fx.*`, `backdrop.*`, `output.N.*`): the desk, the routes, the bindings and every preset's values keep their keys. A node's params are found by `graph.param_prefix(id)`.
- **Names, exactly:**
  - `graph.FRAME_KEY = "frame"`, `graph.WIRED_FRAME = "wired"`, `graph.ALL_OUTPUTS = "output.all"`.
  - `graph.FRAME_KINDS = ("scene", "shape", "backdrop", "pattern", "lookback", "layer", "guide")` (entry kinds; `layer` and `guide` take `instance`).
  - `graph.MANY_PORTS = frozenset({"scene.geometry"})`.
  - `graph.SINK_PORTS = ("output", "lookback.capture")` (every port of an `output.N` or `output.all`, and the look-back's capture).
  - `graph.IMPLICIT_EDGES = (("shape", "pattern"),)` (the shape reads the faces pattern while `shape.faces` is unwired).
  - `graph.HIDDEN_EDGES = (("shape", "pattern"), ("lookback", "scene"))`.
  - `RESERVED` gains `"copy"` and `"ground"`.
  - `graph.GROUND = "ground"`: a source with no node. Wired into an output's port, that port shows nothing although `output.all`'s has something (`WIRE_MAKES["ground"] = IMAGE`; it goes only into output ports).
- **Ports, exactly**, in a wired frame (`WIRE_TAKES` / `WIRE_MAKES`):

  | Kind | Names | Takes | Makes |
  |---|---|---|---|
  | `scene` | `scene` | `geometry` (GEOMETRY, many) | IMAGE |
  | `shape` | `shape` | `faces` | GEOMETRY |
  | `hands` | `hands`, `hands.<n>` (the tracked hands as geometry; params `ghost[.n].*`) | — | GEOMETRY |
  | `layer` | `hands.layer`, `hands.<n>.layer` | — | IMAGE |
  | `guide` | `hands.guide`, `hands.<n>.guide` | — | IMAGE |
  | `lookback` | `lookback` (params `dream.*`) | `image`, `capture`, `occluder` | IMAGE |
  | `channel` | `channel.a` … `channel.h` (params `media.<c>.*`) | — | IMAGE |
  | `backdrop` | `backdrop` | `image`, `scene` | IMAGE |
  | `copy` | `copy`, `copy.<n>` | `image`, `aux` | IMAGE |
  | `output` | `output.<n>`, `output.all` | `image`, `hands`, `guide` | — |

  Outside a wired frame (a section read before migration, a test's), the plan-34 table holds unchanged.
- **Words, exactly:**
  - `GONE_IN_A_WIRED_FRAME = "{name} is gone in a wired frame (plan 35): wire the picture straight into an effect, a composite or an output"`
  - `HOLDS_IS_A_WIRE = "lookback holds: in a wired frame what the look-back records is a wire — wire a picture into lookback.capture"`
  - `INTO_IS_A_WIRE = "{hands} into: in a wired frame the hands go into the scene by a wire — wire {hands} into scene.geometry"`
  - `FRAME_VALUE = "frame {value!r}: the one value is \"wired\""`
  - `GEOMETRY_INTO_SCENE = "{src} makes geometry: it goes into scene.geometry"`
  - `COPY_NO_OF = "copy {name}: names no of (the effect instance it draws again)"`
  - `COPY_BAD_OF = "copy {name}: of {of!r} is no effect instance of this graph"`
  - `GROUND_ONLY_INTO_OUTPUTS = "ground goes only into an output's port: it shows nothing there"`
  - `OLD_ID_IN_A_WIRED_FRAME = "{old} is the old name (plan 35): in a wired frame it is {new}"`
  - `graphmigrate.DRIVEN_RETIRED_NOTE = "{pid} is a wire now (plan 35): its route is dropped — pick what the look-back records on LOOKBACK"`
  - `config.THROUGH_IS_WIRING = "config: [[output.screens]] output {n}: through is wiring now (plan 35) — OUTPUT's 'hands through the effects' writes it into the preset"`
  - `graphview.OUTPUT_UNWIRED = "{label} is a window of this rig: its wires are gone, it shows its ground"`
  - `graphview.STARTER_SAID = "scene starter: shape → scene → All outputs"`
  - `preset.NEW_SAID = "new preset: factory values, nothing wired — black until something is wired to an output"`
- **The canonical frame order** that `frame_wires` writes, one group after another (this is what the round trip compares, so it is fixed):
  1. `scene.geometry` (in-scene hands by instance, then `shape`)
  2. `backdrop.scene`
  3. `lookback.image`
  4. `lookback.occluder`
  5. the run
  6. `output.all.image`
  7. `output.all.hands`
  8. `output.all.guide`
  9. the capture's composite and `lookback.capture`
- Match the surrounding code: module docstrings that say what and why, plan and row numbers in comments, `getattr(self, "x", None)` for state a hot-reloaded object may lack, `# noqa: BLE001` on an except that must not kill the app.
- Commits end with the session's attribution lines.

## Review Focus

1. **Exactly today's frame.** For every factory preset and fixture, under each of the eight states and the WIRED variants, `signature(build_graph(…))` equals `signature(default_graph(…))`. (T2: `test_the_wired_frame_builds_what_default_graph_builds`; T3: the golden suite.)
2. **Nothing hidden is built.** A wired frame builds only reached nodes. `{"frame": "wired"}` alone builds outputs and nothing else. (T2: `test_nothing_unreached_is_built`.)
3. **Mutes are the window's, never structure.** A mute changes what one window shows this frame, never the graph or the preset. (T2: `test_a_mute_ignores_its_port`, `test_a_mute_never_rebuilds`.)
4. **The `/4` byte guarantee holds by round trip.** An untouched old preset saves byte for byte; any frame edit saves `/6`. (T3: `test_an_untouched_v4_preset_saves_byte_identical`, `test_the_round_trip_is_canonical`, `test_an_edited_frame_saves_as_v6`.)
5. **No refusal but types, loops and the rig.** Every node and wire of a migrated party preset can be deleted on GRAPH. (T5: `test_every_frame_node_and_wire_deletes`.)

---

## Task order

| Order | Task | Touches |
|---|---|---|
| 1 | T1 the words | `graph.py` (data half), `graphmigrate.py` |
| 2 | T2 the builder and the frame as wires | `graph.py` (render half), `graphmigrate.py` (`frame_wires`, `output_wires`) |
| 3 | T3 load and save: every section a wired frame | `graphmigrate.py`, `preset.py`, `render.py`, `tools/golden_frames.py`, fixtures, goldens |
| 4 | T4 retire the pipelines | `graph.py`, `outputs.py`, `overlay.py`, `config.py`, `render.py`, `ui_system.py`, tests |
| 5 | T5 GRAPH | `graphview.py`, `ui_graph.py` |
| 6 | T6 OUTPUT and LOOKBACK as views | `ui.py`, `ui_lookback.py`, `graphview.py` |
| 7 | T7 the new preset | `preset.py`, `ui_presets.py` |
| 8 | T8 docs | `docs/` |

Sequential. T2 builds nothing a load reaches yet: no section is marked until T3, so the goldens cannot move in T2. T3 flips every load to the wired frame. T4 deletes what nothing calls any more. T5–T7 are the panel.

---

### Task 1 (T1): The words

**Files:**
- Modify `hyperspace/graph.py`:
  - constants: `FRAME_KEY`, `WIRED_FRAME`, `ALL_OUTPUTS`, `FRAME_KINDS`, `MANY_PORTS`, `SINK_PORTS`, `IMPLICIT_EDGES`, `HIDDEN_EDGES`, the words;
  - `_OUTPUT` (now also `output.all`), `RESERVED`, `wire_node_kind`;
  - new `SceneAt`, `ShapeAt`, `BackdropAt`, `PatternAt`, `LayerAt`, `GuideAt`, `CopyAt` and their `NODE_KINDS` readers;
  - `_history_entry` (read as kind `lookback`; kind `history` is an old id, T3), `_hands_entry` (refuse `holds` and `into` in a wired frame);
  - new `NEW_IDS`, `OLD_IDS`, `PARAM_PREFIX`, `new_id`, `old_id`, `param_prefix` (the ids, below);
  - `GraphSpec.wired`, `GraphSpec.frame_nodes`, `GraphSpec.copies`, `to_json`;
  - `read_graph` (the third key);
  - `_WireCtx.wired`, `_WireCtx.copies`;
  - `wire_error`, `WIRED_TAKES`, `WIRED_MAKES`;
  - `_read_wires` (many wires into `scene.geometry`);
  - `reaches`, `sink_loops`, `loop_words`.
- Modify `hyperspace/graphmigrate.py`: `uses_free_words`, `_FREE_SRCS`, `_FREE_DSTS`, `_free_node`.
- Test `tests/test_graph_wired.py` (new).

**Interfaces — Consumes:** plan 34's `DelayAt` reader pattern, `DECLARED`, `wire_loops`, `sink_loops`, `reaches`. **Produces:**
- `SceneAt()`, `ShapeAt()`, `BackdropAt()`, `PatternAt()`: frozen dataclasses with `n = 1`, `name` the kind and `to_json() == {"kind": <kind>}`. Readers take `()`.
- `LayerAt(n: int = 1)` (`name` is `hands.layer` / `hands.<n>.layer`) and `GuideAt(n: int = 1)` (`hands.guide` / `hands.<n>.guide`). `to_json` gives `{"kind": "layer"[, "instance": n]}` and the same for `guide`. Readers take `("instance",)`.
- `LookbackAt()` (`name` `lookback`, `to_json` `{"kind": "lookback"}`) replaces `HistoryAt` in a wired frame.
- **The ids** (`graph.NEW_IDS`, old wire name → new, applied to whole names and to D1's `after` / `into` values): `ghost` → `hands`, `ghost.<n>` → `hands.<n>`, `hands` → `hands.layer`, `hands.<n>` → `hands.<n>.layer`, `readout` → `hands.guide`, `readout.<n>` → `hands.<n>.guide`, `history` → `lookback`, `media.<c>` → `channel.<c>`; the port `output.<n>.readout` → `output.<n>.guide`; the entry kind `history` → `lookback`. `OLD_IDS` is its inverse. `new_id(name)` / `old_id(name)` map one name (a name not in the table is itself). Every other id is unchanged: `shape`, `scene`, `pattern`, `backdrop`, `output.<n>`, effects, `composite`, `switch`, and plan 34's `delay`, `resize`, `echo.<k>`, `dream`.
- **Params keep their ids.** `graph.PARAM_PREFIX = {"hands": "ghost", "lookback": "dream", "channel": "media", "camera": "eye"}`, by kind; `param_prefix(name)` gives a node's params' prefix (`hands.2` → `ghost.2`, `channel.a` → `media.a`, `lookback` → `dream`); an effect's is `fx.<id>` (`acid.2` → `fx.acid.2`); every other node's prefix is its own id.
- `CopyAt(n: int, of: str)`: `name` is `copy` / `copy.<n>`, and `to_json` gives `{"kind": "copy", "of": of[, "instance": n]}`. The reader takes `("of", "instance")`. A missing `of` is `GraphError(COPY_NO_OF)`. An `of` naming no effect instance the section holds (entries, wires, D1) is a note `COPY_BAD_OF`, and the copy is dropped with its wires.
- `DECLARED` gains `"copy"`, `"layer"`, `"guide"`, `"lookback"`, `"scene"`, `"shape"`, `"backdrop"`, `"pattern"`. In a wired frame a wire may name a frame kind without an entry: wiring it declares it. Copies always need an entry.
- `read_graph(section)`: the keys are `nodes`, `wires` and `frame`. `frame` other than `"wired"` raises `GraphError(FRAME_VALUE)`. `spec.wired` is True with it. In a wired frame the old ids are refused (`OLD_ID_IN_A_WIRED_FRAME`), `{"kind": "lookback", "holds": …}` raises `GraphError(HOLDS_IS_A_WIRE)`, and a hands entry with `into` raises `GraphError(INTO_IS_A_WIRE.format(hands=…))`. Outside a wired frame the old ids are read as today.
- `GraphSpec.wired: bool = False`. `GraphSpec.frame_nodes` is the frame kinds' entries, as read. `GraphSpec.copies` is a tuple of `CopyAt` sorted by `n`. `to_json()` writes `"frame": "wired"` first when `wired`.
- `wire_error(w, ctx)` with `ctx.wired`:
  - `frame` or `fx` at either end gives `GONE_IN_A_WIRED_FRAME.format(name=…)`;
  - a GEOMETRY source into anything but `scene.geometry` gives `GEOMETRY_INTO_SCENE`;
  - `scene.geometry` takes only GEOMETRY;
  - `output.*.guide` takes `layer` or `guide`;
  - `ground` into anything but an output port gives `GROUND_ONLY_INTO_OUTPUTS`;
  - the history-over words stay, saying `lookback`;
  - every type mismatch keeps today's words.
- `_read_wires`: in a wired frame, several wires into `scene.geometry` stand in their section order. Two into any other port stay refused, as today.
- `reaches(spec)` in a wired frame: a fixpoint. It is seeded by every wire into a `SINK_PORTS` port. A node is reached when its picture or geometry goes into a port of a reached node. `IMPLICIT_EDGES` counts while `shape.faces` is unwired. A delay's `image` is plan 34's rule. Outside a wired frame, `reaches` is unchanged.
- `sink_loops` in a wired frame walks `HIDDEN_EDGES` in place of `FRAME_EDGES`. `loop_words(path, hops)` returns `LOOP_FACES` when the path uses a wire into `scene.geometry` or the hop `("scene", "shape")`, `LOOP_BACKDROP` for a wire into `backdrop.scene` or the hop `("lookback", "backdrop")`, and otherwise the words `wire_loops` gives.
- `graphmigrate.uses_free_words(spec)` is True when `spec.wired` or `spec.copies`. `_free_node` is True for `copy` and every `FRAME_KINDS` entry. `_FREE_SRCS` gains `copy`, `ground` and `shape`. `_FREE_DSTS` gains `copy` and `scene`. A new `_FREE_PORTS = ("lookback.capture", "lookback.occluder", "backdrop.scene", "output.all.image", "output.all.hands", "output.all.guide")` makes `_free_end` True for a wire into one of them.

- [ ] **Step 1: Failing tests** in `tests/test_graph_wired.py`:
  - `test_the_marker_reads_and_round_trips`: `{"frame": "wired"}` reads with no notes, `spec.wired`, and `spec.to_json() == {"frame": "wired", "nodes": []}`. `{"frame": "yes"}` raises with `FRAME_VALUE`.
  - `test_the_frame_kinds_read_and_round_trip`: a section with entries `scene`, `shape`, `backdrop`, `pattern`, `lookback`, `layer` instance 2, `guide`, `copy` of `acid` (with an `acid` entry), and wires `shape → scene.geometry`, `hands → scene.geometry`, `scene → backdrop.scene`, `channel.a → backdrop.image`, `backdrop → lookback.image`, `scene → lookback.capture`, `lookback → acid.image`, `acid → output.all.image`, `lookback → copy.image`, `copy → output.2.image`, `hands.layer → output.all.hands`, `hands.layer → output.all.guide`. It reads with no notes, and `read_graph(spec.to_json()) == spec`.
  - `test_frame_and_fx_are_gone_in_a_wired_frame`: `lookback → fx.image` and `frame → acid.image` each give the note `f"wire {w} — " + GONE_IN_A_WIRED_FRAME.format(name=…)`.
  - `test_holds_and_into_are_wires_in_a_wired_frame`: each raises with the exact words.
  - `test_geometry_goes_into_the_scene_only`: `shape → output.all.image` gives the type words; `hands → lookback.image` gives `GEOMETRY_INTO_SCENE`; `shape → scene.geometry` gives nothing.
  - `test_the_scene_takes_several_geometry_wires_in_order`: three wires stand in section order, and `[w.src for w in spec.wires if w.dst == "scene.geometry"] == ["hands", "hands.2", "shape"]`.
  - `test_ground_goes_only_into_outputs`: `ground → output.2.image` and `ground → output.all.hands` read with no notes; `ground → acid.image` gives `GROUND_ONLY_INTO_OUTPUTS`; a ground wire reaches nothing (`"ground" not in reaches(spec)`).
  - `test_a_copy_needs_an_of_and_an_instance`: no `of` raises `COPY_NO_OF`; `of: "teapot"` is the note `COPY_BAD_OF` and the copy and its wires are gone.
  - `test_reach_runs_from_the_outputs_and_the_capture`:
    - `{"frame": "wired"}` with `shape → scene.geometry` alone means `reaches(spec) == frozenset()`;
    - adding `scene → output.all.image` gives `{"shape", "scene"}`;
    - `scene → lookback.capture` alone gives `{"shape", "scene"}`;
    - `channel.a → pattern.media` with `shape → scene.geometry`, `scene → output.1.image` reaches `pattern`, and with `channel.b → shape.faces` added it does not.
  - `test_loops_in_a_wired_frame_keep_plan_34s_words`: `scene → shape.faces` with `shape → scene.geometry` gives `LOOP_FACES` with path `shape → scene → shape`. `lookback → backdrop.image` with `scene → backdrop.scene`, `backdrop → lookback.image` gives `LOOP_BACKDROP`. `lookback → shape.faces` with `channel.a → lookback.image` and `shape → scene.geometry` is refused by the hidden edge `("lookback", "scene")` in `LOOP_FACES` words.
  - `test_outside_a_wired_frame_nothing_changes`: plan 34's `tests/test_graph_feedback.py` passes unedited (a pointer; Step 4).
  - `test_the_ids_map_both_ways`: `new_id` maps every row of `NEW_IDS` (`ghost.2` → `hands.2`, `hands.2` → `hands.2.layer`, `readout` → `hands.guide`, `history` → `lookback`, `media.c` → `channel.c`) and `old_id(new_id(x)) == x` for each; `new_id("acid.2") == "acid.2"`, `new_id("delay") == "delay"`, `new_id("echo.3") == "echo.3"`, `new_id("dream") == "dream"`.
  - `test_a_nodes_params_keep_their_prefix`: `param_prefix` gives `hands` → `ghost`, `hands.2` → `ghost.2`, `hands.2.layer` → `ghost.2`, `lookback` → `dream`, `channel.a` → `media.a`, `camera` → `eye`, `acid.2` → `fx.acid.2`, `pattern` → `pattern`.
  - `test_an_old_id_in_a_wired_frame_is_refused`: `{"frame": "wired", "wires": [{"from": "history", "to": "output.all.image"}]}` notes `OLD_ID_IN_A_WIRED_FRAME.format(old="history", new="lookback")`; `ghost → scene.geometry` the same with `hands`.
  - `test_the_wired_words_are_v6_only`: for the section of the second test, `uses_free_words` is True, and `legacy_section` holds no frame entry, copy or wired-port wire.
- [ ] **Step 2:** `uv run pytest tests/test_graph_wired.py -q`: the new tests FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `uv run pytest -q -x` passes. The golden suite is unchanged (no render code touched).
- [ ] **Step 5:** commit `"Plan 35 T1: the wired frame as words — the marker, the frame's nodes in the owner's names, copies, All outputs, reach from the outputs and the capture"`.

---

### Task 2 (T2): The builder, and today's frame as wires

**Files:**
- Modify `hyperspace/graph.py`:
  - new `build_graph`, `Shown`, `Copy`, `signature`, `_Build`;
  - `Wiring.wired`;
  - `HandsLayer.split`;
  - `History` (`capture` and `occluder` from wires, the `Cover` made inside);
  - `BackdropNode` (the composite);
  - `Output.run` / `Output.settle` (the own port, else `output.all`'s, through the mutes);
  - `Frame.users` (counted through the mutes).
- Modify `hyperspace/graphmigrate.py`: new `Shows`, `frame_wires`, `output_wires`, `wired_section`, `_next_composite`.
- Modify `hyperspace/render.py`: `_graph_for` calls `build_graph` when `wiring.wired`.
- Modify `tools/golden_frames.py`: `--signatures` (writes `tests/fixtures/frame-signatures.json`).
- Test `tests/test_graph_frame.py` (new).

**Interfaces — Consumes:** T1's spec; plan 33/34's `_Wiring` loop, `MAKERS`, `_place`, `Frame.at`, `picture`; `default_graph` (kept as the reference until T4). **Produces:**
- `graphmigrate.Shows`: a frozen dataclass `scene: bool = True`, `hands: bool = True`, `through: bool = False`. It is today's switch state as a word of the migration, not of `outputs`.
- `graphmigrate.frame_wires(spec: G.GraphSpec) -> tuple[list[dict], list[dict]]`: (entries, wires) for `Shows()`, in the canonical order, by the spec's rules (M), from `spec.wiring()`. `spec`'s own wires are not in the result. The composite for `holds = scene+hands` is `_next_composite(spec)`, the lowest instance no entry or wire holds.
- `graphmigrate.output_wires(spec: G.GraphSpec, n: int, shows: Shows) -> list[dict]`: the overrides for output `n`. It returns `[]` when `shows == Shows()` and the section has no wire into `output.<n>`. Otherwise it gives exactly the wires `default_graph` gives output `n` (its `image`, `hands`, `guide`), with `_Wiring._put`'s output rules applied to the section's own wires into `output.<n>`. A port that must show nothing although `output.all`'s has something is `{"from": "ground", "to": f"output.{n}.<port>"}`. A through (hands on and `through`, as `pipelines_of` reaches `SCENE_HANDS` or `HANDS`) always writes a `composite.k` entry (its blend the layer's `laid`, depth when `depth`) and one `copy` entry per run effect (none for an empty run), `lookback` under (no `under` wire with scene off), the layer over, and the chain composite → copies → `output.<n>.image`; whether it is bent is decided per frame (`Shown.bent`), as today.
- `graphmigrate.wired_section(section: dict, spec: G.GraphSpec) -> dict`: `section` with `"frame": "wired"`, the frame's entries and wires appended in the canonical order, and the run and `fx.image` / `frame` wires rewritten (`frame → x` becomes `lookback → x`, `y → fx.image` becomes `y → output.all.image`).
- `Wiring.wired: bool = False`: set by `GraphSpec.wiring()` from `spec.wired`. In a wired frame `Wiring.wires` holds every wire, and `run`, `hands`, `history` and `backdrop` (the old fields) are unused.
- `graph.build_graph(views: list[View], wiring: Wiring, clouds: tuple[str, ...] = (), effects: tuple[str, ...] = ()) -> Graph`, built by `_Build(g, wiring)`:
  - first the reached geometry and sources;
  - then the makers (effect, copy, composite, switch, backdrop, lookback, plan 34's nodes) once what each reads exists;
  - then D1's `_place`;
  - then one `Shown` per distinct image source of an output;
  - then the internal `Capture` after every `Shown` and `DelayWrite`;
  - then one `Output` per view.

  `Graph.key = (len(views),)`.
- `graph.Copy(Effect)`: `Copy(name: str, of: str, image=None)`. `effect` is `of` (the knobs, `FxState.live`, the clock), the node name is `name`, and `placed` is `"wire"`.
- `graph.Shown(Node)`: `KIND = "shown"`, `INPUTS = {"image": IMAGE}`, `OUTPUT = IMAGE`, the name `f"shown({src})"`. `fallback: Shown | None`, `bent(frame)` (True with no fallback; else the layer drew this frame and a copy of the chain is live, so an empty chain never bends), `run(frame)` (today's `Fx.run`'s direct test, with `frame.users(self)` counted through the mutes) and `paint` (today's `Fx.paint`: `advance_to` and `chain_runs` when a run effect is live). A source that is a chain of `Copy` over a `Composite` whose `over` is a `HandsLayer` gets `fallback` = the `Shown` of the originals over the composite's `under` (made, run only when settled on), or None when `under` is None.
- `HandsLayer.split(frame) -> bool`, once a frame: True when the layer's hands node is in the scene, an effect is placed after the layer, or a live effect (`frame.r.fx.state.live`) is downstream of the layer. The class attribute `readout` is gone.
- `Output`: for each of `image`, `hands` and `guide` (today's `readout` port), its own input when wired, else `output.all`'s source. `run` reads `v.switches.scene` (off: `image` treated as None) and `v.switches.hands` (off: `hands` and `guide` treated as None) every frame. `settle` keeps today's body over `Shown`.
- `Frame.users(node)` counts only the views whose output takes `node` after its mutes.
- `graph.signature(g: Graph) -> tuple`: a tuple of `(output.index, chain(end), hands, guide, blend, depth, chain(fallback))` for each output, then `tuple((type(n).__name__, getattr(n, "effect", None), tuple(sorted(k for k, v in n.inputs.items() if v is not None))) for n in g.order if not isinstance(n, (Output, Shown, Fx)))` (T4 drops `Fx` from the tuple when it deletes the class). `chain(n)` follows `image`, `under`, `over` back to a source, giving `(class, effect)` pairs. `Fx`, `Wired` and `Shown` are skipped, so their names never count.
- `render.Renderer._graph_for`: `build_graph` when `wiring.wired`, else `default_graph` (until T4).

- [ ] **Step 1: Failing tests** in `tests/test_graph_frame.py`:
  - `test_frame_wires_of_the_default_section`: `frame_wires(read_graph({}))[1]` equals, exactly, `shape → scene.geometry`, `scene → lookback.image`, `lookback → output.all.image`, `hands.layer → output.all.hands`, `hands.layer → output.all.guide`, `scene → lookback.capture`.
  - `test_frame_wires_variants`, parametrised, each with its exact wire list:
    - a run `acid, palette`;
    - a backdrop channel `media.c` (`scene → backdrop.scene`, `backdrop → lookback.image`, `scene → lookback.occluder`);
    - the same with `backdrop.history` (`backdrop → lookback.capture`, no occluder);
    - `holds: scene+hands` (`composite → lookback.capture` with `scene` under, `hands` over);
    - hands into the scene (`hands → scene.geometry` first, `hands.guide → output.all.guide`, no hands wire);
    - `laid: depth`.
  - `test_output_wires_for_each_state`: for the default section with the run `acid`, the eight `Shows` against today's `outputs.route` table, each its exact list:
    - `Shows()` gives `[]`;
    - `Shows(hands=False, through=True)` gives `[ground → output.N.hands, ground → output.N.guide]`;
    - `Shows(scene=False)` gives `[ground → output.N.image]`;
    - `Shows(hands=False)` gives `[ground → output.N.hands, ground → output.N.guide]`;
    - `Shows(scene=False, hands=False)` (and with `through`) gives the three ground wires;
    - `Shows(through=True)` gives the `composite.k` and `copy` (of `acid`) entries and `lookback → composite.k.under`, `hands.layer → composite.k.over`, `composite.k → copy.image`, `copy → output.N.image`, `ground → output.N.hands`;
    - `Shows(scene=False, through=True)` gives the same with no `under` wire;
    - with an empty run, `Shows(through=True)` gives the composite and `composite.k → output.N.image`, no copy.
  - `test_the_wired_frame_builds_what_default_graph_builds` (Review Focus 1). Parametrised over every factory preset slug (`tools.golden_frames.FACTORY_PRESETS`) and every fixture (`FIXTURE_PRESETS`), each × the eight `STATES` (as eight views at once, as the golden rig draws them), plus `WIRED`'s three wiring variants over their presets and states. It loads the document through `graphmigrate.migrate`, then `wired_section`, plus each view's `output_wires`. It asserts `signature(build_graph(views, wired.wiring(), …)) == signature(default_graph(views, old.wiring(), …))`, the views with today's `Switches` for `default_graph` and with `Switches()` (mutes on) for `build_graph`.
  - `test_nothing_unreached_is_built` (Review Focus 2): `{"frame": "wired"}` gives `g.order` of `Output` nodes only. With `shape → scene.geometry` added, still only outputs.
  - `test_a_mute_ignores_its_port` (GL, the `tests/test_graph_faces.py` harness): with the default frame wired, a view with `Switches(scene=False)` shows the ground with the hands laid over, pixel-equal to a section wiring `output.2.image ← ground` with mutes on. `Switches(hands=False)` shows no layer and no guide.
  - `test_a_mute_never_rebuilds` (Review Focus 3): toggling `views[1].switches.scene` over four frames leaves `Renderer._graph_for` returning the same object.
  - `test_one_end_for_two_outputs_of_one_picture`: two views taking `output.all.image` give one `Shown`, painted once into a frame texture (`stats["direct"] is False`). Muting one view's picture gives that frame `stats["direct"] is True`.
  - `test_a_copy_reads_its_originals_knobs`: `Copy("copy", "acid").effect == "acid"`. With `fx.acid.on` off, both `acid` and `copy` read through.
  - `test_a_copy_chain_stands_down`: `lookback → composite.under`, `hands.layer → composite.over`, `composite → copy.image` (copy of `acid`), `copy → output.2.image`, `lookback → acid.image`, `acid → output.all.image`. With acid off, `Output.settle` for output 2 gives the `Shown` of `acid` with the layer over. With acid on and a hand drawn, it gives its own end.
  - `test_a_scene_on_a_backdrop_is_drawn_see_through`: `scene → backdrop.scene` gives `Scene.ground == 0.0`; without it, `None`.
  - `test_the_capture_runs_once_after_every_end`: in `g.order`, `capture` is after every `Shown` and every `DelayWrite`, and `capture.after` holds them all.
- [ ] **Step 2:** run, see FAIL.
- [ ] **Step 3:** implement. `Output` reads a `ground` wire as None (the port shows nothing).
- [ ] **Step 3b:** record the reference: `uv run python tools/golden_frames.py --signatures` writes `tests/fixtures/frame-signatures.json` (force-added): `signature(default_graph(…))` as JSON lists, keyed by `"<slug>/<variant>"`, for every case of `test_the_wired_frame_builds_what_default_graph_builds`. That test compares `build_graph` against both the live `default_graph` and the file; T4 keeps only the file.
- [ ] **Step 4:** `uv run pytest -q -x` passes. The golden suite is unchanged: no section is marked yet.
- [ ] **Step 5:** commit `"Plan 35 T2: the builder — only what the wires reach, one end per picture, mutes per window, copies and their stand-down; today's frame as wires, proved node for node"`.

---

### Task 3 (T3): Every section a wired frame — load, save, the goldens

**Files:**
- Modify `hyperspace/graphmigrate.py`:
  - `migrate` calls `wired_section` last;
  - `RETIRED` gains `"backdrop.history"`;
  - `held_retired` / `with_retired` / `landed_retired` cover it;
  - `legacy_section` and `legacy_values` (the round trip);
  - `DRIVEN_RETIRED_NOTE`;
  - `has_frame_run` (true for a wired frame).
- Modify `hyperspace/params.py`: `backdrop.history` is undeclared (as `backdrop.channel` was in plan 33 T7).
- Modify `hyperspace/preset.py`: `VERSIONS`, `WIRED_SCHEMA`, `schema_of` (`/6` in place of `/5`), `GraphSection.land` / `load_doc` (a wired frame), `NO_MODULE`.
- Modify `hyperspace/render.py`: `backdrop_wiring` is a no-op for a wired frame.
- Modify `tools/golden_frames.py`: views with `Switches()` (mutes on) and each state as `output_wires`.
- Create fixtures `tests/fixtures/presets/blank-frame.json`, `channel-out-only.json` and `through-one-output.json`. Add `channel-out-only` to `MEDIA_FIXTURES` and the others to `FIXTURE_PRESETS`. Record the goldens.
- Test `tests/test_graph_migrate.py`, `tests/test_graph_free.py`, `tests/test_presets.py`.

**Interfaces — Consumes:** T2's `frame_wires`, `output_wires`, `wired_section`, `build_graph`. **Produces:**
- `graphmigrate.renamed(section: dict) -> dict`: a `/2`–`/5` section in the new ids — every wire end and D1 `after` / `into` through `new_id`, the port `output.<n>.readout` as `output.<n>.guide`, the entry kind `history` as `lookback`. A section already wired is returned as it is.
- `migrate(doc, specs)`: plan 33's steps, then `renamed`, then `wired_section`. Every readable section comes out with `"frame": "wired"` in the new ids (an empty one included: `{}` → the default frame).
  - `values["backdrop.history"]` is dropped once said by the capture wire.
  - A route or desk row on `backdrop.history` is dropped, with `DRIVEN_RETIRED_NOTE.format(pid="backdrop.history")`.
  - An unreadable section is left as it is (the loader's note and default, as today; T4 makes that default `frame_wires` of an empty spec).
- `legacy_section(section)` for a wired frame: let `rest` be the section with the marker, the frame entries, the frame wires (canonical order), the copies and `output.all` wires taken out, `into` and `holds` put back as read off the geometry and capture wires, the run written as `frame → … → fx.image` again, and every id put back through `old_id`. If `wired_section(rest, read_graph(rest))` equals the section (dict equality), it returns `legacy_section(rest)` (plan 33's rule from there). Otherwise it returns a value `legacy_values` reads as "needs `/6`" (`None` from `legacy_values`).
- `preset.schema_of(doc)`: `WIRED_SCHEMA` wherever it gave `FREE_SCHEMA` (`needs_free`).
- `with_retired(values, held, specs)` writes `backdrop.history` back where the file had it.
- `golden_frames._shoot`: `views = [View(Switches(), size, target=f) …]`. The rig's section is the preset's migrated section plus, for each view `k`, `output_wires(spec, k + 1, Shows(**state))`. The `route` assertion is replaced by `assert stats["routes"][k] == expected_route(state, fx_on, visible)`, where `expected_route` is today's `outputs.route` table copied into the tool as data.

- [ ] **Step 1: Failing tests:**
  - `test_graph_migrate.py::test_every_section_loads_as_a_wired_frame`: every factory preset, every fixture, and the 38 byte-test sources load to `spec.wired` with no new note and no old id (`old_id(n) == n` for no end).
  - `test_graph_migrate.py::test_old_ids_are_renamed_on_load`: a `/4` section with `{"kind": "hands", "instance": 2}`, `{"kind": "history", "holds": "scene+hands"}`, `hands.2 → output.2.hands`, `history → acid.2.image`, `media.c → output.2.image` and an effect `after: "hands"` loads with `hands.2.layer → output.2.hands`, `lookback → acid.2.image`, `channel.c → output.2.image` and `after: "hands.layer"`; a plan 34 `/5` fixture (`delay-trails`) loads with its delay, zoomblur and composite wires unchanged.
  - `test_presets.py::test_a_wired_preset_saves_as_v6`: `schema_of` of an edited wired frame is `hyperspace.preset/6`; `VERSIONS == (2, 3, 4, 5, 6)`; a `/7` file is refused with the ladder's words.
  - `test_graph_migrate.py::test_a_plan_33_run_becomes_wires_to_all_outputs`: `frame → acid.image`, `acid → fx.image` becomes `lookback → acid.image`, `acid → output.all.image`, and no wire names `frame` or `fx`.
  - `test_graph_migrate.py::test_backdrop_history_and_holds_become_the_capture_wire`: three documents (`backdrop.history` true with a channel; `holds: scene+hands`; both) give the exact capture wires of T2's variants, and `"backdrop.history" not in values`.
  - `test_graph_migrate.py::test_a_driven_backdrop_history_is_dropped_with_a_note` and `test_no_library_preset_drives_backdrop_history`.
  - `test_graph_free.py::test_an_untouched_v4_preset_saves_byte_identical`: the existing test, unedited, passes (Review Focus 4).
  - `test_graph_free.py::test_the_round_trip_is_canonical`: for every fixture and the 38 sources, `legacy_section(wired)` read and wired again equals `wired`.
  - `test_graph_free.py::test_an_edited_frame_saves_as_v6`: deleting `scene → lookback.capture`, or adding `channel.a → output.all.image` in place of the run's last wire, makes `needs_free` True and the saved schema `/6`.
  - `test_presets.py::test_a_wired_frame_preset_saves_and_loads`: a fixture saved and reloaded into a fresh rig lands the same `GraphSpec`.
- [ ] **Step 2:** run, see FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** create the fixtures. Each is `"schema": "hyperspace.preset/6"` with plan 33's fixtures' values.
  - `blank-frame`: `"graph": {"frame": "wired"}`.
  - `channel-out-only` (still `a` from `tests/golden/media/`): wires `channel.a → output.all.image`.
  - `through-one-output`: entries `acid`, `copy` of `acid`, `composite` instance 2; wires `shape → scene.geometry`, `scene → lookback.image`, `scene → lookback.capture`, `lookback → acid.image`, `acid → output.all.image`, `hands.layer → output.all.hands`, `hands.layer → output.all.guide`, `lookback → composite.2.under`, `hands.layer → composite.2.over`, `composite.2 → copy.image`, `copy → output.2.image`, `ground → output.2.hands`; values `fx.acid.on` true, `fx.acid.mix` 1.

  Record `--only blank-frame,channel-out-only,through-one-output`. Run the whole golden suite: every golden before is unchanged (Review Focus 1).
- [ ] **Step 5:** `uv run pytest -q -x` passes. Commit `"Plan 35 T3: every preset loads as a wired frame in the owner's names — today's look, the capture as a wire, /4 by round trip, /6 otherwise; the golden states as wiring"`.

---

### Task 4 (T4): Retire the pipelines

**Files:**
- Modify `hyperspace/graph.py`:
  - delete `pipelines_of`, `COMPOSITE_NAMES`, `FX_NAMES`, `HISTORY_COMPOSITE`, `GROUNDED`, `Fx`, `Wired`, `effect_node_name`, `FrameNode` uses, the switch half of `default_graph`, and `_Wiring._put`'s output rules;
  - `default_graph(views, wiring=None, clouds=(), effects=())` becomes `build_graph(views, wired(wiring), clouds, effects)`, where `wired` gives an unwired `Wiring` the frame of `frame_wires(read_graph({}))` (the factory look with no preset loaded);
  - `graph_key(views)` returns `(len(views),)`;
  - `hands_words`, `history_words` (renamed `lookback_words`), `output_placement_words` read wires;
  - render node names follow the new ids (`lookback`, `lookback(capture)`, `lookback(cover)`, `hands.layer`, `hands.guide`, `channel.a`): the SYSTEM lines and `Graph.timed` say them.
- Modify `hyperspace/outputs.py`: `Switches.through`, `route`, `PIPELINES`, `SCENE`, `SCENE_HANDS`, `HANDS` and `NAMES` are deleted. The module docstring says the mutes.
- Modify `hyperspace/overlay.py`: `register_switches` declares `output.N.scene` (label `picture`), `.hands`, `.flip_x`, `.flip_y`, `.dim`, and no `.through`. The tips say "mute" ("Off: this window ignores the picture wired into it and shows its ground, the hands over").
- Modify `hyperspace/config.py`: the `through` key in `[[output.screens]]` is read, ignored and said once (`THROUGH_IS_WIRING`).
- Modify `hyperspace/render.py`: `stats["pipelines"]` becomes `stats["ends"]`, the `Shown` sources that ran; `_compose`'s `key` is an end's name.
- Modify `hyperspace/ui_system.py`: the SYSTEM page reads `stats["ends"]`.
- Modify `tools/golden_frames.py`: `--names` rewrites only the manifest's per-preset `nodes` and timed-name lists (the render nodes are named in the new ids now); no `goldens` entry, hash or PNG is touched.
- Rewrite every test that names a deleted symbol, keeping the behaviour each one pins.
- Test `tests/test_outputs.py`, `tests/test_overlay.py`, `tests/test_config.py`, `tests/test_graph.py`.

**Interfaces — Consumes:** T2/T3. **Produces:** the deletions above; `graph.wired(wiring: Wiring) -> Wiring`; `stats["ends"]: list[str]`.

- [ ] **Step 1: Failing tests:**
  - `test_golden_frames.py::test_renaming_moved_no_golden`: `frames.json`'s `goldens` list is byte-equal before and after `--names` (run once in Step 4).
  - `test_graph.py::test_the_pipelines_are_gone`: `graph` has none of `pipelines_of`, `FX_NAMES`, `COMPOSITE_NAMES`, `HISTORY_COMPOSITE`, `GROUNDED`, `Fx`, `Wired`; `outputs` has no `route`, `PIPELINES`; `Switches()` has no `through`.
  - `test_graph_frame.py::test_the_wired_frame_builds_what_default_graph_builds` now compares against `tests/fixtures/frame-signatures.json` alone, every case unchanged.
  - `test_graph.py::test_no_preset_draws_the_factory_frame`: `default_graph([view])` with no wiring has the signature of the factory frame (`frame_wires(read_graph({}))`).
  - `test_overlay.py::test_output_switches_are_picture_and_hands`: the ids for one slot are exactly `output.1.scene`, `output.1.hands`, `output.1.flip_x`, `output.1.flip_y`. `reg["output.1.scene"].label == "Picture"`.
  - `test_config.py::test_a_through_key_is_said_once`: a config with `through = true` on output 2 loads, and its notes hold `THROUGH_IS_WIRING.format(n=2)` once.
  - `test_render.py::test_stats_name_the_ends`: a frame of the default section gives `stats["ends"] == ["shown(acid)"]` when acid is wired last (`["shown(lookback)"]` with no run).
- [ ] **Step 2:** run, see FAIL. **Step 3:** implement.
- [ ] **Step 4:** `uv run pytest -q -x` and the golden suite: every golden unchanged.
- [ ] **Step 5:** commit `"Plan 35 T4: the pipelines retired — no fx, no frame, no through switch; picture and hands are each window's mutes"`.

---

### Task 5 (T5): GRAPH deletes, names and groups everything

**Files:**
- Modify `hyperspace/graphview.py`:
  - delete `PLUMBING`, `_is_plumbing`, `_plumbing`, `RUN_KEPT`, `FEEDS`, `FEEDS_NO_DELETE`, `FrameNode`, `_with_run`, the default-graph unwire words, and `spec_name`'s `FX_NAMES` / `Wired` mapping;
  - new `LABELS`, `HOVERS`, `label_of`, `hover_of`, `OUTPUT_UNWIRED`, `STARTER_SAID`, `_with_frame`, `render_starter`;
  - `render_drop` (every kind), `render_unwire` (every wire), `render_add` (every frame kind, `copy`), `picker`, `unreached`, `_stand_in`;
  - areas: `AREAS`, `ORDER`, `AREA`, `TITLES`, `SHORT_TITLES` with `SCENE_AREA`, `LOOKBACK_AREA`, `EFFECTS_AREA` and `OUTPUTS_AREA` (`GEOMETRY` and `SHADERS` as areas deleted); `returns`;
  - `build`: the eight channels (graphview.py:1039–1052) go through `channel_empty` and `is_idle` (`IDLE_KINDS` gains `"channel"`, the channels' `VNode.kind` from now on, so an idle channel sits on MEDIA's idle line); the `pattern` and `backdrop` stand-ins (graphview.py:1060–1063) are drawn only when the section wires or declares them; `ALWAYS_DRAWN = ()`.
- Modify `hyperspace/ui_graph.py`:
  - the canvas pins and node ids in the new ids (`render:lookback`, `rin:lookback/capture`, `render:hands.layer`, `render:camera` …), and `home_page` keyed by them;
  - `render_picker` (the groups);
  - `_feeds_cut` and `DELETE[FEEDS]` deleted;
  - `_delete_render_node` / `_delete_render_cable` docstrings;
  - `home_page` (`output.all` gives `("output", None)`; a copy gives FX with its original selected).
- Test `tests/test_graph_edit.py`, `tests/test_graph_areas.py`, `tests/test_graph_legible.py`, `tests/test_graphview.py`.

**Interfaces — Consumes:** T1–T4. **Produces:**
- `LABELS: dict[str, str]` by wire kind:
  - `"scene": "Scene"`, `"shape": "Shape"`, `"hands": "Hands"`, `"layer": "Hands layer"`, `"guide": "Hands guide"`, `"cloud": "Point cloud"`, `"camera": "Camera"`
  - `"backdrop": "Backdrop"`, `"lookback": "Look-back"`, `"pattern": "Faces pattern"`, `"channel": "Channel"`
  - `"composite": "Composite"`, `"switch": "Switch"`, `"delay": "Delay"`, `"resize": "Resize"`, `"echo": "Echo"`, `"dream": "Dream"`, `"copy": "copy of"`
  - `"output": "Output"`, plus `"output.all": "All outputs"`
- `HOVERS: dict[str, str]`: the spec's V table's hover column, word for word, by the same keys. A hover ends with the node's id and, when it differs, its params' prefix: `"… · id lookback · params dream.*"`.
- `label_of(name: str, slots=()) -> str`:
  - `hands.2` gives `"Hands 2"`;
  - `channel.a` gives `"Channel A"`;
  - `hands.2.layer` gives `"Hands layer 2"`;
  - `echo.3` gives `"Echo 3"`;
  - `copy.2` of `acid` gives `"copy of acid (2)"`;
  - an effect gives its instance name with the dot as a space (`"acid 2"`);
  - `output.N` gives its slot's config name, else `"Output N"`.
- `render_drop(edit, node)`: any node of the section goes, with its entry and its wires, in one undo step. For `output.N` it removes the wires into it and returns `OUTPUT_UNWIRED.format(label=…)` as `edit.said` (not a refusal). A cloud and the camera return `NOT_REMOVABLE`. `hands` (hands 1) drops its wires, its layer's and its guide's.
- `render_unwire(edit, cable)`: removes the wire. The only refusal left is "no such wire". A geometry cable is an ordinary wire.
- `render_add(edit, kind, file=None)`: a frame kind adds its entry, refused in words when one is there (`"{label} is in the graph already"`). `copy` with `file` = an instance adds `CopyAt(next, file)`. Each add calls `_with_frame(doc)`.
- `render_starter(edit)`: adds `shape → scene.geometry` and `scene → output.all.image` in one step, with `STARTER_SAID`.
- `picker(edit)`, in order:
  - `("starter", None, "scene starter")`;
  - the `scene ▸` items (`scene`, `shape`, `hands`, `layer`, `guide`, `backdrop`);
  - the `look-back ▸` items (`lookback`, then plan 34's echo items and `dream`);
  - the `pictures ▸` items (`pattern`, `composite`, `switch`, the channel switches, `resize`, `delay`);
  - the effect files;
  - `("copy", <instance>, f"copy of {instance}")` for each effect instance in the section.

  The group of each item is `PICKER_GROUP[kind]`.
- Areas:
  - `AREAS = (CONTROLLERS, AUDIO, MODULATION, MEDIA, SCENE_AREA, LOOKBACK_AREA, EFFECTS_AREA, OUTPUTS_AREA)`.
  - By class: `Shape`, `Hands`, `HandsLayer`, `Readout`, `PointCloud`, `Scene`, `BackdropNode` and the camera (`render:camera`, was `render:eye`) are `SCENE_AREA`; `History`, `EchoNode` and `DreamNode` are `LOOKBACK_AREA`; `Effect`, `Copy`, `Composite` and `ResizeNode` are `EFFECTS_AREA`; `Output` and `output.all` are `OUTPUTS_AREA`; `MediaNode`, `PatternNode`, `SwitchNode` and `Delay` are `MEDIA`.
  - `returns` holds every cable into `lookback.capture` and every one into a delay's `image`.

- [ ] **Step 1: Failing tests:**
  - `test_graph_edit.py::test_every_frame_node_and_wire_deletes` (Review Focus 5): on `party-wake` migrated, each wire in turn, and then each node in turn, is removed with `edit.said` set and no refusal. The section after deleting all of them is `{"frame": "wired"}`.
  - `test_graph_edit.py::test_the_owners_sequence`: on a migrated factory preset with a backdrop fixture, `render_unwire` of `scene → backdrop.scene`, then `lookback → <first effect>.image`, each effect's out-wire, then `<last> → output.all.image`, each returns None. The last leaves `reaches(spec)` without `lookback`.
  - `test_graph_edit.py::test_deleting_a_window_unwires_it`: `render_drop(e, "render:output.2")` with two wires into it leaves none and `edit.said == OUTPUT_UNWIRED.format(label="Output 2")`.
  - `test_graph_edit.py::test_the_picker_groups_by_primitive`: `picker(e)` is the exact list above for a section with `acid` and `acid.2`.
  - `test_graph_edit.py::test_the_starter_wires_the_scene_to_all_outputs`.
  - `test_graph_edit.py::test_a_frame_node_is_added_once`: `render_add(e, "lookback")` twice gives `"Look-back is in the graph already"` the second time.
  - `test_graph_areas.py::test_the_areas_run_by_primitive`: the default frame's nodes sit in the areas above, and `back_wires(view) == []`.
  - `test_graph_areas.py::test_a_blank_preset_draws_only_the_outputs`: `{"frame": "wired"}` with every channel's bin empty gives drawn render nodes `render:output.all` and each `render:output.N` only; the eight channels are idle, and MEDIA's idle line says `"8 empty channels"`; no `render:pattern` or `render:backdrop` is drawn. With a source in channel a's bin, `render:channel.a` is drawn; with `channel.b → output.2.image`, `render:channel.b` is drawn and the line says `"6 empty channels"`. The rig's desk and session binding cables are not asserted (out of scope: another session's filter, after T5).
  - `test_graph_legible.py::test_every_node_has_a_label_and_a_hover`: every node of every fixture's view has a non-empty title from `label_of` and a hover from `HOVERS`, and no title is `frame`, `fx`, `grounded` or `capture`.
  - `test_graph_legible.py::test_every_nodes_side_panel_draws` (plan 33's) passes with the frame kinds and a copy in its fixture.
  - `test_graphview.py::test_no_plumbing_words_remain`: `graphview` has no `PLUMBING`, `RUN_KEPT`, `FEEDS` or `FrameNode`.
- [ ] **Step 2:** run, see FAIL. **Step 3:** implement. **Step 4:** `uv run pytest -q -x`; the golden suite is unchanged.
- [ ] **Step 5:** commit `"Plan 35 T5: GRAPH deletes anything — nodes named for what they are, grouped scene, look-back, effects, outputs; the scene starter"`.

---

### Task 6 (T6): OUTPUT and LOOKBACK as views of the wires

**Files:**
- Modify `hyperspace/ui.py`: `Panel._output_blocks` (the picture combo, the mutes, "hands through the effects", "open on GRAPH", the All outputs block), `output_shows`.
- Modify `hyperspace/ui_lookback.py`: `history_line` becomes `capture_line` and `draws_over_line`; the records combo.
- Modify `hyperspace/graphview.py`: new `picture_sources(spec) -> list[str]`, `set_through(edit, n, on)`.
- Test `tests/test_ui_output.py` (new), `tests/test_ui_lookback.py`.

**Interfaces — Consumes:** T5's `render_wire`, `render_unwire`, `label_of`; T2's `output_wires`. **Produces:**
- `graphview.picture_sources(spec) -> list[str]`: every picture-making node the section reaches or declares, in area order (MEDIA, SCENE, LOOK-BACK, EFFECTS). Every source the combo may offer.
- `graphview.set_through(edit, n: int, on: bool) -> str | None`:
  - on: lands the section plus `output_wires(spec, n, Shows(through=True))` in one undo step;
  - off: removes those wires and the composite and copies only they use.
- OUTPUT's block, per window:
  - `shows: <label_of(source)>`, or `shows: as All outputs`, or `shows: nothing — its ground`;
  - a combo of `["as All outputs", "nothing", *picture_sources]`: a source writes `render_wire(e, src, f"output.{n}.image")`, "nothing" writes `ground → output.{n}.image`, and "as All outputs" removes the override;
  - the checkboxes `output.N.scene` ("picture") and `output.N.hands`;
  - a checkbox "hands through the effects" bound to `set_through`;
  - dim, flips, and `open on GRAPH`.

  The All outputs block has the combo alone.
- LOOKBACK: `records: <label_of(capture source)>`, or `records: nothing — the echoes fade`, with a combo writing `lookback.capture`; `draws over: <label_of(lookback.image source)>`, as words.

- [ ] **Step 1: Failing tests** in `tests/test_ui_output.py`:
  - `test_the_output_block_says_what_it_shows`: three sections (the default frame, `channel.a → output.2.image`, `blank-frame`) give the exact `shows:` lines for outputs 1 and 2.
  - `test_picking_a_picture_wires_the_output`: the combo's pick of `channel.a` lands `channel.a → output.2.image` in one undo step; "as All outputs" removes it.
  - `test_through_writes_the_wiring`: `set_through(e, 2, True)` lands `output_wires(…, 2, Shows(through=True))`; `False` restores the section to its former `to_json()`.
  - `test_the_mutes_are_not_the_preset`: toggling `output.2.scene` leaves the preset clean (`dirty` False) and the section unchanged.
  - In `tests/test_ui_lookback.py`: `test_records_says_and_sets_the_capture`.
- [ ] **Step 2:** run, see FAIL. **Step 3:** implement. **Step 4:** `uv run pytest -q -x`; headless draws of both pages pass (`tests/test_ui_shell.py`).
- [ ] **Step 5:** commit `"Plan 35 T6: OUTPUT and LOOKBACK show and set the wires — a picture per window, through as wiring, what the look-back records"`.

---

### Task 7 (T7): The new preset

**Files:**
- Modify `hyperspace/preset.py`: new `Presets.new`, `NEW_SAID`, `UNTITLED_PRESET = "untitled"`.
- Modify `hyperspace/ui_presets.py`: `strip` (a `new` chip before `save` on the presets' document strip; `save` on an unnamed preset begins naming).
- Test `tests/test_presets.py`, `tests/test_ui_presets.py`.

**Interfaces — Consumes:** T3's wired frame landing (`GraphSection.land`); `undo.push`. **Produces:**
- `Presets.new() -> list[str]`, in one undo step `"new preset"`:
  - the values are the library's fresh values for every performance group: `lib.restore({k: v for k, v in lib._fresh_all().items() if <k's group> in params.PERFORMANCE_GROUPS})`, the reset `Project.new` uses (library.py:1197), so nothing of the preset loaded before survives;
  - the router's preset routes are emptied;
  - the desk is written explicitly as the factory preset layer: the document landed through `load_doc` carries `"desk": desk_json(fresh_desk())` (preset.py:377). `load_doc` resets everything a file leaves out except the desk (a missing key gives `fresh_desk()`, `"desk": []` an empty layer), so the blank preset says it;
  - every session param is left as it is;
  - the graph section lands as `read_graph({"frame": "wired"})`;
  - `lib.current(PRESETS)` is `UNTITLED_PRESET`, the preset is dirty and has no path;
  - it returns `[NEW_SAID]`.
- `ui_presets.strip(panel, PRESETS)`: chips `("new", save_label, "as…")`. `new` calls `Presets.new`. `save` with no path opens the name field (`_begin_naming`).

- [ ] **Step 1: Failing tests:**
  - `test_presets.py::test_a_new_preset_is_factory_values_and_nothing_wired`: after a loaded factory preset with routes and a desk row, `Presets.new()` leaves:
    - every performance param equal to `lib._fresh_all()`'s value, the same after loading two different factory presets first (`test_a_new_preset_does_not_depend_on_what_was_loaded`, parametrised over `big-blue-wave` and `hex-engine`);
    - `router` preset routes `== []`;
    - the desk equal to `fresh_desk()` (the loaded preset's own extra desk row gone), and the saved document's `"desk"` key present and equal to `desk_json(fresh_desk())`;
    - `output.1.scene` unchanged;
    - `GraphSection.spec.to_json() == {"frame": "wired", "nodes": []}`;
    - `reaches(spec) == frozenset()`.
    Undo restores the loaded preset.
  - `test_presets.py::test_a_new_preset_draws_black` (GL): one frame on two views gives both centre pixels `(0, 0, 0, 255)` on an opaque ground.
  - `test_ui_presets.py::test_the_strip_has_a_new_chip`: headless, the strip draws `new` before `save`; a click calls `Presets.new` once; `save` on the untitled preset opens naming.
- [ ] **Step 2:** run, see FAIL. **Step 3:** implement. **Step 4:** `uv run pytest -q -x`.
- [ ] **Step 5:** commit `"Plan 35 T7: a new preset — factory values, nothing wired, black until something is wired to an output"`.

---

### Task 8 (T8): Docs

**Files:**
- `docs/plans/35-free-frame.md`: a "What was built" section above the design, as plan 33's: the commits by task, the rulings, the owner's answers to rows 373, 374 and 387, and "What no person has verified".
- `docs/plans/README.md`: the entry becomes "built".
- `docs/ARCHITECTURE.md`: the render graph section, now the wired frame — `build_graph`, `Shown`, the mutes, `output.all`, the capture as a sink.
- `docs/ENGINEERING.md`: the marker, `/6` and the id renames (params unchanged), both Macs, the round trip.
- `docs/DECISIONS.md`: a "The frame as wires" section.
- `docs/DECISION-REGISTER.md`: rows 372–393, in the table and in full (Answer, Built, Other options, To reverse, Rough edge, Judge it). Row 351 is marked superseded by 372, and row 359's `FRAME_EDGES` by 393.
- `docs/plans/11-hand-checks.md`: group AE, checks 342–352 as the spec lists them, and the header's range sentence.
- `docs/TESTING-GUIDE.md`: the three fixtures and 24 goldens, the signature test, the golden states as wiring.
- `docs/plans/merge-checklist.md`.

- [ ] **Step 1:** write them, with the test names each row's "Built" cites.
- [ ] **Step 2:** `uv run pytest -q` (the doc-linked tests, if any).
- [ ] **Step 3:** commit `"Plan 35 T8: docs — the free frame as built, rows 372–393, hand checks group AE"`.
