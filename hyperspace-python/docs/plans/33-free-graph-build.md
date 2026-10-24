# Plan 33 Free Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Effects exist where they are wired and nowhere else; the faces (`shape.faces`), the pattern's media layer (`pattern.media`) and the backdrop (`backdrop.image`) are graph inputs; a switch node picks one of eight pictures by a param; the ordered stack (`order`, `target`) is retired and the FX page becomes a browser of the graph's effect nodes; every older preset loads as the graph it always drew.

**Architecture:** The graph's vocabulary gains `frame`, `fx.image`, `pattern`, `shape.faces` and `backdrop`; `default_graph` builds each pipeline's run from the wires `frame → … → fx.image` instead of `FxState.names()`, and any other reached branch is made once a frame at the size its consumer asks. A pure-data module, `graphmigrate.py`, turns an old preset's `order` / `target` / `view.media` / `backdrop.channel` values into wires on load, and back into those values on save whenever `/4` can say the graph. The GRAPH page becomes the one place structure is edited; the FX page lists the effect nodes the graph holds and plays their params.

**Tech Stack:** Python 3.14 (`.python-version`), moderngl, numpy, imgui-bundle (`imgui_node_editor`); pytest via `uv run pytest`.

**Spec:** [`33-free-graph.md`](33-free-graph.md) (rows 341–352; 341, 342, 346, 348 and 350 answered by the owner on 2026-10-24, the rest recommendations to confirm before Task 1). Read it first; this plan does not repeat its reasons.

## Global Constraints

- Work under `hyperspace-python/`. Integration branch `plan-33-free-graph`, base `plan-31-32-integration` @ 3547a7a. Each task on its own branch `plan-33-t<n>` in its own worktree, merged into `plan-33-free-graph` in order.
- **No existing golden moves**: all 661 in `tests/golden/frames/frames.json` match after every task that touches `graph.py`, `render.py` or `fx.py` (`uv run pytest tests/test_golden_frames.py -q`, on the M3 Max that recorded them). New goldens only for new fixtures, recorded with `uv run python tools/golden_frames.py --record --only <slugs>`.
- **No file under `hyperspace/library/` is edited**; no factory preset gains a `graph` section. Proofs are fixtures under `tests/fixtures/presets/`.
- `apc40.py`, `midi.py`, `bindings.default.json` and the desk are untouched (the desk and faders are Dylan's).
- New wire ends, exactly: `frame` (source, `IMAGE`), `fx.image` (`IMAGE` in), `pattern` (source, `IMAGE`; input `pattern.media`), `shape.faces` (`IMAGE` in), `backdrop.image` (`IMAGE` in). `switch`, `switch.<n>` (inputs `in1` … `in8`, makes `IMAGE`; param `switch[.<n>].select`, an enum off / 1–8). `frame`, `pattern`, `backdrop`, `switch` are reserved names.
- Retired ids: `fx.<n>.order`, `fx.<n>.target`, `fx.select`, `view.media`, `backdrop.channel`. Kept: `fx.on`, `fx.mix`, `fx.face_map`, every `fx.<n>.{on,mix,speed,blend}` and uniform param, `view.media_{alpha,scale,mode,amp,rate}`, `backdrop.{alpha,history}`, the `view.bmp_alpha` alias.
- Schema: `hyperspace.preset/5` only when `graphmigrate.legacy_values` returns None (the graph needs words `/4` lacks); else the lowest of `/2`–`/4` by row 340's rule. `VERSIONS = (2, 3, 4, 5)`.
- Load note for an effect left out of a run while something in the preset targets its params, exactly: `<name> was off, so it is not in the run: wire it in on GRAPH to use it`.
- Refusal for a wrong `fx.image` source, exactly: `fx.image takes the run from frame; to replace an output's picture wire it into output.N.image`.
- Canvas word for an unreached node, exactly: `reaches nothing`.
- Match the surrounding code: module docstrings that say what and why, plan/row numbers in comments where the repo does, `getattr(self, "x", None)` for state a hot-reloaded object may lack, `# noqa: BLE001` on a must-not-kill-the-app except, the render stack's import rule (ARCHITECTURE §3: `graph.py` imports no params, preset or media module).
- Commits end with the session's attribution lines.

## Review Focus

1. **A `/4` preset opened and saved untouched on this build is byte-identical**, so the second Mac on the older build keeps reading it. (Task 3: `test_an_untouched_v4_preset_saves_byte_identical`, every factory preset and every fixture.)
2. **A switch over eight playing channels** makes only the selected one: the other seven branches run no pass and their channels upload nothing; flicking `select` at 16ths never rebuilds the graph. (Task 5: `test_only_the_selected_input_is_made`, `test_select_changes_do_not_rebuild_the_graph`.)
3. **An effect file deleted or renamed while wired** (hot reload) → its node reads through, says "no <file> effect in this build", its wires are kept and come back when the file does; nothing raises on the frame thread. (Task 3: `test_a_wired_effect_whose_file_goes_reads_through_and_returns`.)
4. **A channel feeding the faces goes missing or lost mid-show** → the faces show the pattern that frame, not black. (Task 4: `test_faces_fall_back_to_the_pattern_when_the_branch_reads_nothing`.)
5. **A branch read at two sizes** (the faces at 1024² and an output at the frame size) → made once per size per frame; the texture pool does not grow over 100 frames. (Task 4: `test_a_branch_read_at_two_sizes_is_made_once_each_and_does_not_leak`.)

---

## Task order

| Order | Task | Touches |
|---|---|---|
| 1 | T1 vocabulary | `graph.py` (data half) |
| 2 | T2 migration + schema | create `graphmigrate.py`; `preset.py` |
| 3 | T3 the run from wires | `graph.py` (`default_graph`, `Effect`, `Fx`), `fx.py`, `render.py` (`_graph_for`, `draw`) |
| 4 | T4 faces, pattern, backdrop, branches | `graph.py`, `render.py` (face path, backdrop), goldens |
| 5 | T5 the switch | `graph.py` (`SwitchNode`, `Graph.evaluate`), `params.py`, `preset.py` (land), goldens |
| 6 | T6 GRAPH page | `graphview.py`, `ui_graph.py`, `ui_fx.strip` |
| 7 | T7 the FX page as a browser; the stack retired | `ui_fx.py`, `fx.py`, `ui.py`, `params.py`, `learn.py`, `render.py`, tests |
| 8 | T8 docs | `docs/` |

Sequential: each task consumes the one before (T3–T5 all rewrite `default_graph`; T6 and T7 both touch `ui_fx.py`). Between T4 and T5 a preset whose migration made a switch (a route on `view.media` / `backdrop.channel`; none in the library or the fixtures) shows the pattern / no backdrop.

---

### Task 1 (T1): The vocabulary — new ends, branches instead of refusals, `reaches`

**Files:** Modify `hyperspace/graph.py` (`WIRE_MAKES`, `WIRE_TAKES`, `wire_node_kind`, `WIRE_FROM_WORDS`, `WIRE_TO_WORDS`, `wire_error`, `split_wires`, `GraphSpec`, `NODE_KINDS`, new `SwitchAt`); Test `tests/test_graph_free.py` (new), `tests/test_graph_json.py`.

**Interfaces — Produces:**
- Kinds in `WIRE_MAKES`: `"frame": IMAGE`, `"pattern": IMAGE`, `"backdrop": None`. In `WIRE_TAKES`: `"fx": {"image": IMAGE}`, `"pattern": {"media": IMAGE}`, `"shape": {"faces": IMAGE}`, `"backdrop": {"image": IMAGE}`. `"switch": IMAGE` makes, `"switch": {f"in{i}": IMAGE for i in 1..8}` takes. `wire_node_kind("frame" | "fx" | "pattern" | "shape" | "backdrop" | "switch" | "switch.2")` returns that kind; `_PLACE_EFFECT` no longer matches the reserved names.
- `graph.SwitchAt(n: int = 1)`: frozen dataclass like `CompositeAt`; `name` → `switch` / `switch.<n>`; JSON `{"kind": "switch"}` / `{"kind": "switch", "instance": 2}`; `NODE_KINDS["switch"]`; `GraphSpec.switches: tuple[SwitchAt, ...]`. A switch no wire feeds or reads is kept (unreached).
- `split_wires(wires, placed=())`: a wire whose source fails `placement_error` is kept as a wire (a branch), never shortened to `EffectAt(after=…)`.
- `graph.SINKS = ("output", "fx", "shape", "pattern", "backdrop", "history")` — the kinds whose input ports end a path.
- `graph.reaches(spec: GraphSpec) -> frozenset[str]`: every node with a path (via `image`, `aux`, `under`, `over`, `media`, `faces`, `in1`–`in8` ports) to a sink port.
- `graph.run_of(spec: GraphSpec, head: str = "frame", end: str = "fx.image") -> tuple[str, ...]`: the effect names on the wired path from `head` to `end`, in order; `()` with no such path (a switch on the path ends it: a run is effects only). The faces run is `run_of(spec, "pattern", "shape.faces")`.

- [ ] **Step 1: Failing tests** in `tests/test_graph_free.py`:
  - `test_a_channel_into_an_effect_is_a_branch_not_a_refusal`: `read_graph({"wires": [{"from": "media.a", "to": "acid.2.image"}]})` → no error, `reaches(spec)` lacks `acid.2`.
  - `test_a_branch_to_the_faces_reaches`: wires `media.a → acid.2.image`, `acid.2 → tripcolour.2.image`, `tripcolour.2 → shape.faces` → `reaches` ⊇ {`media.a`, `acid.2`, `tripcolour.2`}.
  - `test_the_run_is_read_from_frame_to_fx`: `frame → acid.image`, `acid → wobble.image`, `wobble → fx.image` → `run_of(spec) == ("acid", "wobble")`.
  - `test_fx_image_refuses_a_branch_not_from_frame`: `media.a → acid.2.image`, `acid.2 → fx.image` → `wire_error` equals the Global Constraints' refusal.
  - `test_a_loop_through_aux_is_refused` (`acid.2 → tripcolour.2.image`, `tripcolour.2 → acid.2.aux`) → a loop error, the canvas words of `wire_loops`.
  - `test_reserved_names_are_no_effect`: `wire_node_kind("frame") == "frame"`, and an `EffectAt("frame", 1, after="scene")` raises.
  - `test_a_switch_takes_eight_pictures`: `media.a → switch.in1`, `media.h → switch.in8`, `switch → pattern.media` → no error; `switch.in9` → `switch has no port 'in9' (it takes in1, …, in8)`.
  - In `test_graph_json.py`: `test_the_new_ends_round_trip` — a section using all five ends and `switch.2` reads and `to_json`s back equal.
- [ ] **Step 2:** `uv run pytest tests/test_graph_free.py tests/test_graph_json.py -q` → the new tests FAIL.
- [ ] **Step 3:** implement in `graph.py`; `graphview` and the render ignore the new kinds until T3–T5 (a section naming them builds today's default graph plus whatever it already built).
- [ ] **Step 4:** `uv run pytest -q -x` passes; the golden suite is unchanged (no render code touched).
- [ ] **Step 5:** commit `"Plan 33 T1: the free graph's words — frame, fx, pattern, faces, backdrop, switch; a channel into an effect is a branch"`.

---

### Task 2 (T2): Old presets as wires, and back — `graphmigrate.py`, schema `/5`

**Files:** Create `hyperspace/graphmigrate.py`; Modify `hyperspace/preset.py` (`VERSIONS`, `schema_of`, `load_doc`, `document`, `GraphSection.read`); Test `tests/test_graph_migrate.py` (new).

**Interfaces — Consumes:** T1's `run_of`, `reaches`, `read_graph`, `GraphSpec`; `fx.reordered`. **Produces:**
- `graphmigrate.FREE_SCHEMA = "hyperspace.preset/5"`.
- `graphmigrate.RETIRED = ("fx.select", "view.media", "backdrop.channel")` and `retired(pid: str) -> bool` (also true for `fx.<n>.order` / `fx.<n>.target`).
- `graphmigrate.targets(doc: dict) -> frozenset[str]`: every param id any route, desk row, macro, modifier output or sequencer step in `doc` drives.
- `graphmigrate.to_free(doc: dict, specs: dict[str, int]) -> tuple[dict, list[str]]`: `specs` maps each effect instance name to its file's `@order` default. Returns the doc's `graph` section with the runs and channel wires added (unchanged when it already has a `frame` run) and the load notes. Run membership: aimed at the frame (`target` absent or 0), not placed or wired by the section, and `on` and `mix > 0` (row 346); sorted by `(order, name)` with `order` from the doc else `specs`. The same with `target == 1` for `pattern → … → shape.faces`. `view.media = k > 0` → `media.<"abcdefgh"[k-1]> → pattern.media`; `backdrop.channel = k > 0` → `… → backdrop.image`. When `view.media` (or `backdrop.channel`) is in `targets(doc)`: a new `switch.<n>` (the next free instance) with `media.a … media.h → in1 … in8`, the switch into `pattern.media` (`backdrop.image`), `switch.<n>.select` set to the old value, and every row driving the old id retargeted to `switch.<n>.select`. An effect left out while some `fx.<name>.` id is in `targets(doc)` gets the load note.
- `graphmigrate.legacy_values(section: dict, values: dict) -> dict | None`: the `order` / `target` / `view.media` / `backdrop.channel` values that say `section` in `/4` terms — orders from `fx.reordered` so values that already sort right are kept — or None when `/4` cannot say it (a branch, an unreached node, more than one run per head, a non-channel into `pattern.media` / `backdrop.image`, a switch, an effect on outside every run).
- `preset.schema_of(doc)` returns `FREE_SCHEMA` when `legacy_values(...)` is None, else the existing rule; `VERSIONS = (2, 3, 4, 5)`. **`load_doc` does not call `to_free` yet**: on this base an effect named by a wire leaves the run, so the run's wires must not reach the renderer before T3 reads them. T3 hooks it in.

- [ ] **Step 1: Failing tests** in `tests/test_graph_migrate.py`:
  - `test_every_library_preset_migrates_without_a_note` (parametrised over `hyperspace/library/presets/*.json` and `library/fx/*.json`): `to_free` returns no note, and its run equals `[n for n in sorted-by-(order, name) if on and mix > 0]`.
  - `test_no_library_preset_routes_an_effect_it_leaves_out` (the owner's reading, row 346): over the same files, no id in `targets(doc)` starts with the `fx.<name>.` of an effect the run leaves out. A failure lists them: a preset to look at, not a test to loosen.
  - `test_mandala_keeps_kaleido_first` (`fx.kaleido.order = 8`): `run_of(...)[0] == "kaleido"`.
  - `test_an_off_effect_left_out_says_so_when_something_drives_it`: parametrised over a route, a desk row, a macro, a modifier output and a sequencer step targeting `fx.warp.mix`, with `fx.warp.on = false` → `"warp"` not in the run, the note `warp was off, so it is not in the run: wire it in on GRAPH to use it`.
  - `test_faces_aimed_effects_become_the_faces_run`: `fx.acid.target = 1`, on → wires `pattern → acid.image`, `acid → shape.faces`.
  - `test_view_media_and_backdrop_channel_become_wires`: `view.media = 3`, `backdrop.channel = 2` → `media.c → pattern.media`, `media.b → backdrop.image`.
  - `test_a_route_onto_view_media_becomes_a_switch`: `view.media = 2` and an LFO route onto it → `switch` with `media.a … media.h` into `in1 … in8`, `switch → pattern.media`, `switch.select = 2`, the route's destination `switch.select`; the same for `backdrop.channel` (its own instance when both are routed).
  - `test_legacy_values_inverts_to_free`: for every factory preset and every file under `tests/fixtures/presets/` and `tests/fixtures/merge-31-32/`: `legacy_values(to_free(doc)[0], values)` gives back the doc's own `order` / `target` / `view.media` / `backdrop.channel` values for every effect in a run (orders that already sort right untouched).
  - `test_a_branch_saves_as_v5_and_reloads`: a section with `media.a → acid.2 → shape.faces` → `schema_of == FREE_SCHEMA`; reload gives the same section.
  - `test_v5_is_refused_by_the_ladder_below`: `VERSIONS` of the base (2, 3, 4) refuse the file with the schema message.
- [ ] **Step 2:** run, see them FAIL.
- [ ] **Step 3:** implement `graphmigrate.py` (pure data; imports `graph` and `fx.reordered` only) and `schema_of` / `VERSIONS` in `preset.py`.
- [ ] **Step 4:** `uv run pytest -q -x` passes; golden suite unchanged (nothing on the load path changed).
- [ ] **Step 5:** commit `"Plan 33 T2: old presets become wires on load and go back to /4 on save; /5 only when needed"`.

---

### Task 3 (T3): The run from wires; `order` and `target` leave the render

**Files:** Modify `hyperspace/graph.py` (`default_graph`'s `run(key, src)`, `_chain_now`, `Effect.on`, `Fx.effects`, `Capture.run`, `_Wiring._put` for `fx.image`, `EffectAt` docs), `hyperspace/fx.py` (`FxState.live`, `FxState.chain`), `hyperspace/render.py` (`_graph_for` key, `draw`'s `fx_on`); Test `tests/test_graph_free.py`, `tests/test_graph_effects.py`, `tests/test_graph_placement.py`.

**Interfaces — Consumes:** T1's `run_of`, `reaches`; T2's `to_free`, `legacy_values`. **Produces:**
- `preset.load_doc` calls `graphmigrate.to_free` before `GraphSection.read`, so every loaded preset carries its run as wires; `Presets.document` writes `legacy_values(...)` back when `schema_of` is not `/5`. The retired values still load (`view.media`, `backdrop.channel` drive the faces and the backdrop until T4; `order` / `target` are declared until T7 and read by nothing after this task).
- `FxState.live(name: str) -> bool`: `on` (stack) and `mix > 0` (stack) and the effect's `on` and `mix > 0`. `FxState.chain(target)` is removed in T7; from here nothing in `graph.py` calls it.
- `default_graph`: each pipeline's run is `run_of(spec)` in order, one `Effect` per name per pipeline (names suffixed per pipeline as today); an effect not in `reaches(spec)` has no node; `frame` is `src` of `run(key, src)`.
- `Renderer._graph_for` keys on `frozenset(fx.state.specs)`, not `names()`.
- `Frame.fx_on`: any effect in the frame's runs is `live`.

- [ ] **Step 1: Failing tests:**
  - `test_only_wired_effects_have_nodes`: PARTY-ACID migrated → the scene pipeline's effect nodes are exactly its run (not 13).
  - `test_the_run_order_is_the_wire_order`: wires `frame → wobble → acid → fx.image` → `wobble` evaluates before `acid` whatever their `@order`.
  - `test_an_unreached_effect_is_never_run`: `media.a → acid.2.image` alone → no `acid.2` node; `frame.stats["effects"]` lacks it.
  - `test_an_untouched_v4_preset_saves_byte_identical` (Review Focus 1): for every factory preset and every file under `tests/fixtures/presets/` and `tests/fixtures/merge-31-32/`: load into a scratch library, save, compare bytes with the file the base build writes.
  - `test_order_changes_do_not_rebuild_the_graph`: changing `fx.acid.order` (still declared until T7) leaves `Renderer._graph_for` returning the same object.
  - `test_a_wired_effect_whose_file_goes_reads_through_and_returns` (Review Focus 3): remove `acid.glsl` from a temp effects folder mid-run → the run's picture equals the run without it, a dormant note names it, the wires stay in the section; restore → the node is back.
  - Rewrite (not delete) the assertions in `test_graph_effects.py` / `test_graph_placement.py` that say "in chain order" to build their graph from wires.
- [ ] **Step 2:** run, see FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `uv run pytest -q -x` passes **and** `uv run pytest tests/test_golden_frames.py -q`: 661 unchanged.
- [ ] **Step 5:** commit `"Plan 33 T3: each pipeline's run is its wires; an effect not wired has no node"`.

---

### Task 4 (T4): The faces, the pattern, the backdrop, branches at their consumer's size

**Files:** Modify `hyperspace/graph.py` (new `PatternNode`, `BackdropNode`; `Shape.INPUTS = {"faces": IMAGE}`; `Frame.data` keyed by `(name, size)`; `Node.size_for(port) -> tuple[int, int]`; `default_graph` builds the reached branches and the `grounded` composite from `backdrop.image`), `hyperspace/render.py` (`_face_picture` from the wired picture; `_face_media` from `pattern.media`; the one-block `face_fx` path retired; `Renderer.wiring.backdrop` set from the section, not `backdrop.channel`); Test `tests/test_graph_faces.py` (new), `tests/test_media_render.py`, `tests/test_media_faces_aux.py`, `tests/test_render.py`; Create fixtures `tests/fixtures/presets/{media-chain-faces,media-chain-backdrop,branch-two-sizes}.json`; goldens.

**Interfaces — Consumes:** T3's run and `reaches`. **Produces:**
- `graph.PatternNode(Node)`: `KIND = "pattern"`, `INPUTS = {"media": IMAGE}`, `OUTPUT = IMAGE`, `MAKES = True`; `image(frame)` → `frame.r._pattern_picture(s, t, media)` — `Renderer._pattern_picture(s: ViewState, t: float, media: tuple[moderngl.Texture, bool] | None) -> moderngl.Texture`: today's seed pass (`_seed_prog`, `_face_uniforms`) into a `FaceTarget` at `(FACE_PIC, FACE_PIC)`, `media` being what `pattern.media` reads (the raw channel texture and its row order, or a branch's picture).
- `Renderer._face_media` and `Wiring.backdrop` read `pattern.media` / `backdrop.image` from the section, not `view.media` / `backdrop.channel`; from here those two values are read only by `graphmigrate.to_free`.
- `graph.BackdropNode(Node)`: `KIND = "backdrop"`, `INPUTS = {"image": IMAGE}`, no output; built only when `backdrop.image` is wired.
- `Node.size_for(port: str) -> tuple[int, int]`: frame size for every port but `shape.faces` (`(FACE_PIC, FACE_PIC)`) and `pattern.media` (its head's own size: a channel's `media_texture(c).size`, else `FACE_PIC`²). An `Effect` passes its consumer's size to its input.
- Faces: `shape.faces` unwired or wired straight from `pattern` → today's direct draw (no `FACE_PIC` pass). From `pattern` through effects → the effects run on the pattern at `FACE_PIC`², bound as `u_pic`. From anything else → that picture at `FACE_PIC`² as `u_pic`. A picture that read nothing this frame → `u_pic_on = 0` (the pattern).
- Backdrop: `media.<c> → backdrop.image` → `MediaNode(alpha_of="backdrop_alpha")` as today; any other source → `Composite(GROUNDED, over=scene, under=src, under_alpha_of="backdrop_alpha")`.

- [ ] **Step 1: Failing tests** in `tests/test_graph_faces.py`:
  - `test_a_channel_through_effects_lands_on_the_faces`: a red still on `a`, wires `media.a → huecycle.2.image`, `huecycle.2 → shape.faces`, `fx.huecycle.2.mix = 1` → a face-centre pixel is not red and not the pattern's colour; with the wire to `shape.faces` removed, it equals the no-media frame.
  - `test_faces_unwired_draw_as_today`: every pixel equal to the base for PARTY-FACES.
  - `test_faces_fall_back_to_the_pattern_when_the_branch_reads_nothing` (Review Focus 4): the channel's source `missing` → equal to the faces-unwired frame.
  - `test_a_branch_into_pattern_media_keeps_the_channels_aspect`: a 2:1 still through an effect into `pattern.media` → the made texture is 2:1.
  - `test_a_branch_under_the_scene`: `media.b → kaleido.2.image`, `kaleido.2 → backdrop.image` → an empty-shape frame's centre is the kaleidoscoped still at `backdrop.alpha`.
  - `test_a_branch_read_at_two_sizes_is_made_once_each_and_does_not_leak` (Review Focus 5): `acid.2` read by `shape.faces` and `output.2.image` → two makes per frame; `len(renderer.fx._tex)` (the `FxChain.pool` textures) equal at frame 10 and frame 110.
  - Rewrite the face-chain tests in `test_render.py` (1103–1601) to wire `pattern → … → shape.faces` instead of `target = 1`.
- [ ] **Step 2:** run, see FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** record the three new fixtures' goldens (`--only media-chain-faces,media-chain-backdrop,branch-two-sizes`); run the whole golden suite: the 661 unchanged.
- [ ] **Step 5:** `uv run pytest -q -x` passes; commit `"Plan 33 T4: the faces, the pattern's media layer and the backdrop are inputs; branches are made at their consumer's size"`.

---

### Task 5 (T5): The switch

**Files:** Modify `hyperspace/graph.py` (new `SwitchNode`; `default_graph` builds each reached switch; `Graph.evaluate` skips what no selected path pulls), `hyperspace/params.py` (`declare_switches`), `hyperspace/preset.py` (`GraphSection.land` declares the switches' params, as it calls `set_instances` for effects), `hyperspace/render.py` (the switch's selection read once a frame); Test `tests/test_graph_switch.py` (new); Create fixture `tests/fixtures/presets/switch-faces.json`; goldens.

**Interfaces — Consumes:** T1's `SwitchAt`, T4's sinks and `size_for`. **Produces:**
- `params.declare_switches(r: Registry, names: Iterable[str]) -> list[str]`: declares `switch[.<n>].select` (enum `["off", "1", … "8"]`, default off, group `"switch"`, modulatable) for each name and undeclares those no longer named; returns the changed ids (as `FxState.set_instances` does).
- `graph.SwitchNode(Node)`: `KIND = "switch"`, `INPUTS = {f"in{i}": IMAGE for i in range(1, 9)}`, `OUTPUT = IMAGE`; `selected(frame) -> Node | None` (the node on the selected port, None for off or unwired); `image(frame)` and `paint(frame, dst)` pass the selected node's through at the consumer's size; with None, `image` is None (the faces show the pattern, the backdrop nothing).
- `Graph.pulled(frame) -> frozenset[str]`: the nodes on some path from a sink that runs only through selected switch inputs; `evaluate` runs a `MAKES` node only when it is in `pulled`. Computed once a frame from the `select` values, never a rebuild.

- [ ] **Step 1: Failing tests** in `tests/test_graph_switch.py`:
  - `test_the_switch_shows_its_selected_input`: a red still on `a`, a blue on `b`, into `switch.in1` / `in2`, `switch → output.1.image` → the centre is red at `select = 1`, blue at `2`, black at off.
  - `test_only_the_selected_input_is_made` (Review Focus 2): eight playing fake channels, each through its own `acid.<n>` into `in1 … in8`, `select = 3` → `frame.stats["effects"]` holds only `acid.3`; `MediaTextures.uploads` grows for `c` only.
  - `test_select_changes_do_not_rebuild_the_graph`: step `select` 1 → 8 over 8 frames → `Renderer._graph_for` returns the same object each frame.
  - `test_a_route_drives_select`: an LFO square route on `switch.select` → the output alternates between the two inputs.
  - `test_a_migrated_view_media_route_still_switches_the_faces`: T2's migrated preset (a route on `view.media`) → the faces show channel 1 then channel 2 as the route moves.
  - `test_switch_params_come_and_go_with_the_graph`: loading a preset with `switch.2` declares `switch.2.select`; loading one without it undeclares it.
- [ ] **Step 2:** run, see FAIL. **Step 3:** implement.
- [ ] **Step 4:** record `switch-faces` (`--only switch-faces`); the whole golden suite: everything before unchanged. `uv run pytest -q -x` passes.
- [ ] **Step 5:** commit `"Plan 33 T5: the switch — eight pictures in, one param picks, only the picked one runs"`.

---

### Task 6 (T6): The GRAPH page edits the free graph

**Files:** Modify `hyperspace/graphview.py` (`build`: `frame`, `fx`, `pattern`, `backdrop`, the switches, the faces port; `AREA` (`PatternNode`, `BackdropNode`, `SwitchNode` → MEDIA; `frame`, `fx` → SHADERS); `OWNERS`: `view.pattern*` and `view.media_*` to `pattern`, `backdrop.*` to `backdrop`, `switch.*` to its switch, `fx.face_map` to `shape`; `spec_name`; `render_add` lands an effect or a switch unwired; a faint flag from `reaches`), `hyperspace/ui_graph.py` (`render_picker` offers effects and a switch; `dropped` for an effect node on a render cable; a render cable's menu "insert effect ▸"; an error-coloured title; the side pane's selection read from and written to `Panel.fx_selected`), `hyperspace/ui_fx.py` (`strip`: no order slider, no ONTO chips, no `FAINT_FACES`); Test `tests/test_graph_edit.py`, `tests/test_graphview.py`, `tests/test_graph_legible.py`.

**Interfaces — Consumes:** T1's ends, `reaches`, `run_of`, `SwitchAt`; `graphview.Edit.wire / unwire / add_node`; `graphview.cable_near`. **Produces:**
- `graphview.Edit.insert_effect(cable: VCable, file: str) -> Refusal | None`: adds the next instance of `file` and rewires `src → new.image`, `new → dst` in one undo step.
- `ui_graph.dropped` also inserts a free effect node let go on a render cable (`n.kind == "effect"`, no cable in or out).
- `graphview.VNode.faint: bool` (true when not in `reaches`), drawn with the summary line `reaches nothing`.
- `Panel.fx_selected: str | None` — the effect instance selected on GRAPH or on the FX page (panel state, saved nowhere); `ui_graph.select_effect(panel, name: str) -> None` selects and centres `render:<name>` on the canvas next frame.

- [ ] **Step 1: Failing tests:**
  - `test_the_picker_adds_an_effect_unwired`: `render_add("acid")` → `acid.2` in the section, no wire, `faint`; `render_add("switch")` → `switch`, the same.
  - `test_insert_effect_on_a_render_cable`: on `media.a → shape.faces`, insert `kaleido` → wires `media.a → kaleido.2.image`, `kaleido.2 → shape.faces`; one undo restores the one wire.
  - `test_dropping_a_free_effect_on_the_run_inserts_it`: drop `wobble.2` on `frame → fx.image` → it is in `run_of`.
  - `test_reordering_the_run_is_rewiring`: drag `acid` from before `wobble` to after it (unwire + insert on `wobble → fx.image`) → `run_of == ("wobble", "acid")`, one undo step.
  - `test_the_new_nodes_sit_in_their_areas`: `pattern`, `backdrop`, `switch` in MEDIA; `frame`, `fx` in SHADERS.
  - `test_selecting_an_effect_node_sets_the_shared_selection`: selecting `render:acid.2` → `panel.fx_selected == "acid.2"`.
  - `test_the_strip_has_no_order_or_onto`: `ui_fx.strip` draws no `fx.<n>.order` / `.target` widget (the existing strip test harness).
- [ ] **Step 2:** run, see FAIL. **Step 3:** implement. **Step 4:** `uv run pytest -q -x`.
- [ ] **Step 5:** commit `"Plan 33 T6: GRAPH adds effects and switches unwired, inserts effects on cables, draws the faces, pattern and backdrop"`.

---

### Task 7 (T7): The FX page as a browser of the graph's effects; the stack retired

**Files:** Modify `hyperspace/ui_fx.py` (`page` rewritten as the browser; the chip grid, drag-and-drop, placed grid, `REORDER`, `_drop`, `_chip`, `_drop_target`, `_dragged`, `_placed`, `_dormant`, `_faces_row` removed; `strip` kept; new `groups`), `hyperspace/fx.py` (`declare`: no `order` / `target` / `fx.select`; `RESERVED`; `TARGETS`, `FACES`, `MAX_ORDER` removed; `FxState.names` sorts by name; `chain` removed; `FxChain.run` and the borrowed-programs faces chain removed; `parse` still accepts and ignores `@order`), `hyperspace/ui.py` (`r.fx.active()` / `fx_on` words at 1740 read `Frame.fx_on`; the FX page stays in `PAGES`), `hyperspace/params.py` (`view.media`, `backdrop.channel` undeclared), `hyperspace/learn.py` (160–205, 286: the `fx.on` / `fx.mix` gates kept, any `names()` order use replaced), `hyperspace/render.py` (`face_fx`, `on_reload`'s rebuild of it), `hyperspace/graphview.py` (`_effect_owner`: `fx.select` gone); Test `tests/test_fx.py`, `tests/test_render.py`, `tests/test_ui_shell.py`.

**Interfaces — Consumes:** T3's `FxState.live`, T4's face path, T6's `strip`, `Panel.fx_selected`, `ui_graph.select_effect`. **Produces:**
- `ui_fx.groups(spec: GraphSpec) -> list[tuple[str, list[str]]]`: pure; the effect instances of the loaded graph grouped by where their path ends, in this order — `"Run"` (the `run_of` order), `"→ faces"`, `"→ pattern media"`, `"→ backdrop"`, `"→ output <n>"` (by n), `"→ <effect> aux"`, `"reaches nothing"` last; an effect behind a switch is grouped by the switch's destination; an effect that ends in two places is listed in each; within a group, path order from the head to the sink.
- The page: head `fx.on`, `fx.mix`; then each group, its header (the `→ faces` header carries `fx.face_map`), each row the effect's name, an `on` checkbox, a small `mix` slider and one state word (`running`, `off`, the `why_idle` reason, or `error: <first line>`); a click sets `Panel.fx_selected`; below the list, `strip(panel, Panel.fx_selected)` and a **Show on GRAPH** button calling `ui_graph.select_effect`. With no effect in the graph: `no effects in the graph — add one on GRAPH (right-click the canvas)`.
- The retired ids no longer exist in the registry (`params.Registry.get("fx.acid.order")` raises like any unknown id).

- [ ] **Step 1: Tests first:**
  - `test_groups_follow_the_wires`: a fixture with a run of two, `media.a → acid.2 → shape.faces`, `kaleido.2 → backdrop.image`, an unreached `wobble.2`, and `acid.3` read by `output.2.image` and `blend.aux` → the exact groups and names above.
  - `test_the_fx_page_lists_the_graphs_effects` (the panel harness): every name from `groups` is drawn once per group; clicking `acid.2` sets `panel.fx_selected` and draws its strip.
  - `test_show_on_graph_selects_the_node`: the button → GRAPH's selection is `render:acid.2`.
  - `test_an_empty_graph_says_where_to_add`: the exact empty-state line.
  - `test_the_retired_ids_are_gone`; `test_an_effect_file_with_an_order_line_still_parses`; `test_an_old_preset_loads_its_retired_ids_without_a_note` (a `/4` fixture with every `fx.<n>.order` / `.target`, `view.media`, `backdrop.channel` → no unknown-id note, the same wires as before this task).
  - Rewrite the stack tests in `test_fx.py` (about 31: order, target, drag, the placed grid): keep each one whose behaviour survives as a wire test, delete those that test only the removed UI, and list the deleted names in the commit message.
- [ ] **Step 2:** run, see FAIL. **Step 3:** implement and remove. **Step 4:** `uv run pytest -q -x` and the golden suite (661 + T4's and T5's new, unchanged).
- [ ] **Step 5:** commit `"Plan 33 T7: the FX page browses the graph's effects; order, target and the faces chain retired"`.

---

### Task 8 (T8): Docs

**Files:** `docs/plans/33-free-graph.md` (a "What was built" section above the design, as plans 30–32), `docs/plans/README.md`, `docs/ARCHITECTURE.md` (the render graph section), `docs/ENGINEERING.md` (effects, the switch, the faces, the backdrop; both Macs and `/5`), `docs/DECISIONS.md`, `docs/DECISION-REGISTER.md` rows 341–352 (built, other options, to reverse, rough edge, judge it), `docs/plans/11-hand-checks.md` group AC from 318, `docs/TESTING-GUIDE.md`, `docs/plans/merge-checklist.md`, `hyperspace/shaders/fx/` header comment on `@order`.

Hand checks to write (group AC, from 318): the owner's headline graph at the machine (a clip → two effects → the faces, the camera → kaleido → the backdrop); a switch over three channels on an APC40 knob into the faces; reordering the run by dragging; the FX page finding and playing an effect on a branch; an old party preset loads and looks the same, saved untouched opens on the second Mac; a channel on the faces lost mid-show; the frame cost of two branches, the faces branch and an eight-way switch on SYSTEM.

- [ ] **Step 1:** write them. **Step 2:** `uv run pytest -q` (doc-linked tests, if any). **Step 3:** commit `"Plan 33 T8: docs — the free graph as built, rows 341–352, hand checks group AC"`.
