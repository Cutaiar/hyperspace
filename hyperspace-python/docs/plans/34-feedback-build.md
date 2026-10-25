# Plan 34 Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `delay` picture node (last frame's input) makes a loop on GRAPH legal when it passes through one. The look-back's frames (`echo.1` … `echo.32`, `dream`) are picture sources. A `resize` node crops its input and makes it at a size of its own. Every wire that would loop through the faces, the backdrop or the frame is refused when the section is read, in words, instead of landing dormant.

**Architecture:** In `graph.py`'s data half, four new node kinds (`delay`, `resize`, `echo`, `dream`) join `NODE_KINDS`, and a second loop pass, `sink_loops`, checks the wires against the default graph's hidden edges (`FRAME_EDGES`), skipping edges into a delay. In the render half, `Delay` / `DelayWrite` read and write a renderer-owned half-float ping-pong pair that `Renderer._turn_delays` swaps at each frame's start. `EchoNode` / `DreamNode` paint a ring slot or the dream buffer. `ResizeNode` makes its picture at its own size. A new `Node.own_size` and one refit pass (`Renderer._refit`) carry pictures of their own size into consumers of another, by cover. GRAPH adds the four from its picker, draws a delay as one node, and shows the resize's params as side-panel rows.

**Tech Stack:** Python 3.14 (`.python-version`), moderngl, numpy, imgui-bundle (`imgui_node_editor`); pytest via `uv run pytest`.

**Spec:** [`34-feedback.md`](34-feedback.md) (rows 353–371, all recommendations the build takes; the owner said "build" on 2026-10-24; none waits for the owner). Read it first; this plan does not repeat its reasons.

## Global Constraints

- Work under `hyperspace-python/`. Integration branch `plan-34-feedback`, base `plan-33-free-graph` @ 052d889 (3550 passed, 2 skipped). Each task on its own branch `plan-34-t<n>` in its own worktree, merged into `plan-34-feedback` in order.
- **No existing golden moves**: all 693 in `tests/golden/frames/frames.json` match after every task (`uv run pytest tests/test_golden_frames.py -q`, on the M3 Max that recorded them). New goldens only for the new fixtures, recorded with `uv run python tools/golden_frames.py --record --only <slugs>`: T2 `delay-faces,delay-trails`, T3 `echo-faces`, T4 `resize-faces,resize-crop` (5 × 8 states = 40; 733 after T4).
- **No file under `hyperspace/library/` is edited.** Proofs are fixtures under `tests/fixtures/presets/` (force-added, as plan 33's: `tests/fixtures/` is ignored).
- `apc40.py`, `midi.py`, `bindings.default.json` and the desk are untouched (Dylan's).
- `graph.py` imports no params, preset or media module (ARCHITECTURE §3, `tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`). It may import `view` (for `ResizeState`, `RESIZE_*`) and `lookback` (for `MAX_ECHOES`).
- Preset schema stays `hyperspace.preset/5`. The new kinds are `/5`-only (`graphmigrate.uses_free_words`); `VERSIONS` is unchanged.
- New wire ends, exactly:

  | Kind | Names | Takes | Makes | Entry |
  |---|---|---|---|---|
  | `delay` | `delay`, `delay.<n>` | `image` | `IMAGE` | `{"kind": "delay"[, "instance": n]}` |
  | `resize` | `resize`, `resize.<n>` | `image` | `IMAGE` | `{"kind": "resize"[, "instance": n]}` |
  | `echo` | `echo.<k>`, k 1–32 | nothing | `IMAGE` | `{"kind": "echo", "index": k}` |
  | `dream` | `dream` | nothing | `IMAGE` | `{"kind": "dream"}` |

  `RESERVED` becomes `("frame", "fx", "pattern", "shape", "backdrop", "switch", "delay", "resize", "echo", "dream")`.
- Hidden edges, exactly (node, what it reads): `FRAME_EDGES = (("scene", "shape"), ("shape", "pattern"), ("history", "scene"), ("history", "backdrop"), ("frame", "history"))`.
- Refusal words, exactly (`{path}` is `wire_loops`' path form, `a → b → a`):
  - `LOOP_FACES = "that makes a loop through the faces ({path}): the faces are drawn inside the scene — wire it through a delay for last frame's picture"`
  - `LOOP_BACKDROP = "that makes a loop through the backdrop ({path}): the backdrop lies under the scene's picture — wire it through a delay for last frame's picture"`
  - `LOOP_FRAME = "that makes a loop through the frame ({path}): frame is the history's picture — wire it through a delay for last frame's picture"`
  - `FRAME_SOURCE_REFUSAL = "frame is the run's head: it goes into the run's first effect or fx.image — the picture before the effects is history, after them the run's last effect"`
  - An undeclared node: `no {name} node in this graph (add one: {{"kind": "<kind>"}})`. For an echo the entry is `{"kind": "echo", "index": <k>}`.
- Node words, exactly (`Node.said`):
  - echo: `"{w}×{h} · every frame · {holds}"` / `"{w}×{h} · every {gap:.2f} s · {holds}"`, with holds one of `the scene`, `the scene + hands`, `the scene + backdrop`; not held: `"not held yet: the ring holds {n} of 32"`
  - dream: `"{w}×{h} · the dream worker's, a frame or two late"` / `"no dream worker: reads nothing"` / `"waiting for the dream worker"`
  - delay: `"last frame's · {w}×{h} half-float"` / `"nothing yet"`
  - resize: `"{w}×{h} · {fit} · {filter}"`, plus `" · crop {cw:.0%}×{ch:.0%}"` while either crop size is below 1
- Match the surrounding code: module docstrings that say what and why, plan/row numbers in comments, `getattr(self, "x", None)` for state a hot-reloaded object may lack, `# noqa: BLE001` on a must-not-kill-the-app except.
- Commits end with the session's attribution lines.

## Review Focus

1. **No pass samples the texture it writes.** A delay's read and write sides are different textures every frame. A loop of effects (`delay → zoomblur.2 → composite.under`, `composite → delay.image`) never binds the write side as a source. (T2: `test_a_delay_ping_pongs_half_float`, `test_a_loop_of_effects_never_reads_what_it_writes`.)
2. **Every sink loop is refused at read, and the wire refused is the one closing the loop.** The drag's own wire is the refusal; the run's wires stand. (T1: `test_each_sink_loop_is_refused_at_read`, `test_the_later_wire_closing_a_sink_loop_is_the_one_refused`; `tests/test_graph_edit.py::test_a_sink_loop_drag_is_refused_in_words`.)
3. **Nothing before this plan draws differently.** No node of plan 33 has an own size, so the `Effect` own-size path and the refit never run for the 693 goldens. (Every task: the golden suite.)
4. **Feedback survives what it should and only that.** A GRAPH edit elsewhere keeps the delay's frame. A window resize loses no frame. A delay removed is released after `SIZED_KEEP_FRAMES`. (T2: `test_a_graph_rebuild_keeps_the_delay`, `test_a_size_change_loses_no_frame`, `test_a_delay_leaving_the_graph_is_released`.)
5. **A resize's saving is real.** A delay through it holds its size, and an effect after it runs in that size's pool. (T4: `test_a_delay_through_a_resize_holds_a_small_buffer`, `test_an_effect_after_a_resize_runs_at_its_size`.)

---

## Task order

| Order | Task | Touches |
|---|---|---|
| 1 | T1 vocabulary + loop refusal | `graph.py` (data half), `graphmigrate.py` |
| 2 | T2 the delay | `graph.py` (`Node.own_size`, `Delay`, `DelayWrite`, `Effect` own size, `default_graph`, `_Wiring`), `render.py` (`DelayPair`, `_turn_delays`, `_refit`, `REFIT_FS`, `_frame_target` dtype), goldens |
| 3 | T3 echoes and the dream as sources | `graph.py` (`EchoNode`, `DreamNode`, `Graph.reads_ring`), `lookback.py` (`echo_slot`, `held`, `keep`), `render.py`, goldens |
| 4 | T4 the resize | `view.py`, `params.py`, `preset.py`, `ui_presets.py`, `graph.py` (`ResizeNode`, `resize_size`), `render.py`, goldens |
| 5 | T5 GRAPH | `graphview.py`, `ui_graph.py` |
| 6 | T6 docs | `docs/` |

Sequential. T2 builds the refit and the own-size rule that T3 and T4 use. T5 needs all four node classes. Between T1 and T2 a section naming a delay, an echo, the dream or a resize reads cleanly, but those nodes are not built yet: their wires are dormant ("no delay this frame").

---

### Task 1 (T1): The words and the loop refusal

**Files:** Modify `hyperspace/graph.py`: `RESERVED`, `_DELAY` / `_RESIZE` / `_ECHO` patterns, `wire_node_kind`, `WIRE_MAKES`, `WIRE_TAKES`, `WIRE_FROM_WORDS`, `WIRE_TO_WORDS`, new `DelayAt` / `ResizeAt` / `EchoAt` / `DreamAt` and their `NODE_KINDS` readers, `GraphSpec.delays` / `resizes` / `echoes` / `dream`, `_WireCtx`, `wire_error`, `wire_loops`, new `FRAME_EDGES` / `sink_loops` / `loop_words`, `_read_wires`, `read_graph`'s duplicate check, `reaches`, `_reached_edges`. Modify `hyperspace/graphmigrate.py`: `uses_free_words`, `_FREE_SRCS`, `_FREE_DSTS`, `_free_node`. Test `tests/test_graph_feedback.py` (new), `tests/test_graph_edit.py`.

**Interfaces — Consumes:** plan 33's `SwitchAt` pattern, `wire_loops`, `_read_wires`, `reaches`, `_reached_edges`, `uses_free_words`. **Produces:**
- `graph.DelayAt(n: int = 1)` and `graph.ResizeAt(n: int = 1)`: frozen dataclasses shaped exactly like `SwitchAt` (`name` → `delay` / `delay.<n>`, `to_json`). Readers `_delay_entry` and `_resize_entry` take `("instance",)`.
- `graph.EchoAt(n: int)`: `n` from 1 to `lookback.MAX_ECHOES`. `name` → `echo.<n>`. `to_json` → `{"kind": "echo", "index": n}`. Reader `_echo_entry` takes `("index",)`. A missing index raises `GraphError("echo node: names no index (echo.1 is the newest)")`. A bad one raises `GraphError(f"echo node: index {i!r}, a whole number from 1 to {MAX_ECHOES}")`.
- `graph.DreamAt()`: `name` → `dream`; `n` is always 1; `to_json` → `{"kind": "dream"}`. Reader `_dream_entry` takes `()`.
- `read_graph` refuses two entries of one kind and instance for `delay`, `resize`, `echo` and `dream` (`"two echo nodes of instance 3"`, as for a switch).
- `GraphSpec.delays`, `.resizes`, `.echoes` (tuples sorted by `n`) and `.dream` (`DreamAt | None`), read off `others`.
- `wire_node_kind`: `"delay"`, `"delay.2"` → `"delay"`; `"resize"`, `"resize.3"` → `"resize"`; `"echo.7"` → `"echo"`; `"dream"` → `"dream"`. `_PLACE_EFFECT` no longer matches them.
- `_WireCtx` gains `delays: frozenset[str]`, `resizes: frozenset[str]`, `echoes: frozenset[str]` and `dream: bool`, all filled by `read_graph`. `wire_error` refuses a wire naming one not declared, in the undeclared-node words.
- `wire_error` refuses `Wire("frame", d)` unless `d` is an effect's `image` port or `fx.image`, with `FRAME_SOURCE_REFUSAL`.
- `wire_loops(wires)` builds no dependency for a wire into a delay (`wire_node_kind(w.node) == "delay"`), and never reports such a wire.
- `graph.FRAME_EDGES` (Global Constraints).
- `graph.sink_loops(wires: list[Wire]) -> dict[Wire, str]`. It walks `wires` in order, with `deps` seeded from `FRAME_EDGES`. A wire into a delay adds nothing. For any other wire, if `w.node` is reachable from `w.src` through `deps`, the wire maps to `loop_words(path, hops)`. Otherwise `deps[w.node]` gains `w.src`. The path has the same form as `wire_loops` gives.
- `graph.loop_words(path: str, hops: set[tuple[str, str]]) -> str`. `hops` is the set of (reader, read) edges the path used. It returns `LOOP_FACES` when `("scene", "shape")` is among them, else `LOOP_BACKDROP` for `("history", "backdrop")`, else `LOOP_FRAME`.
- `_read_wires`: after `wire_loops`' refusals, it runs `sink_loops([*d1, *ok])` and refuses each wire found, noting `f"wire {w} — {words}"`.
- `reaches(spec)`: a delay's `image` port is a sink port only once the delay is in the result. This is a fixpoint: re-walk from each newly reached delay's `image` wire sources until nothing is added. `_reached_edges` uses the same rule. Its kept-node filter also covers `"resize"` and `"delay"`, so a wire into an unreached resize or delay is dropped.
- `graphmigrate.uses_free_words(spec)` is True when any of `spec.delays`, `spec.resizes`, `spec.echoes` or `spec.dream` is set, or any wire end has one of the four kinds. `_FREE_SRCS` gains `"delay", "resize", "echo", "dream"`. `_FREE_DSTS` gains `"delay", "resize"`. `_free_node` is True for the four kinds. So `legacy_values` returns None and `legacy_section` strips them.

- [ ] **Step 1: Failing tests** in `tests/test_graph_feedback.py`:
  - `test_the_new_kinds_read_and_round_trip`: a section with nodes `delay`, `delay` instance 2, `resize`, `echo` index 3 and `dream`, and wires `scene → delay.image`, `delay → shape.faces`, `media.a → resize.image`, `resize → output.2.image`, `echo.3 → output.3.image`, `dream → acid.2.aux` (plus an `acid.2` entry and the run `frame → fx.image`). Asserts: `read_graph` gives no notes; `spec.to_json()` read back equals the spec; `spec.delays == (DelayAt(1), DelayAt(2))`; `spec.echoes == (EchoAt(3),)`; `spec.dream == DreamAt()`.
  - `test_the_new_names_are_reserved_kinds`: `wire_node_kind` maps the eight examples in Interfaces; `EffectAt("resize", 1, after="scene")` raises `ValueError`.
  - `test_a_wire_into_an_undeclared_node_is_refused`, parametrised over `scene → delay.2.image`, `media.a → resize.image`, `echo.3 → output.2.image` and `dream → output.2.image`, each with no entry. `spec.notes` equals `(f"wire {w} — no {name} node in this graph (add one: {entry})",)`, where the entry is `{"kind": "delay"}`, `{"kind": "resize"}`, `{"kind": "echo", "index": 3}` and `{"kind": "dream"}`.
  - `test_an_echo_index_out_of_range_is_unreadable`: index 0, 33 and `"3"` each raise `GraphError` with the words in Interfaces.
  - `test_each_sink_loop_is_refused_at_read` (Review Focus 2). Parametrised; each row is the wires, the refused wire and the exact note:
    - `scene → shape.faces`: `LOOP_FACES` with `shape → scene → shape`.
    - `history → shape.faces`: `LOOP_FACES` with `shape → scene → history → shape`.
    - `frame → shape.faces`: `LOOP_FACES` with `shape → scene → history → frame → shape`.
    - `frame → acid.image`, `acid → fx.image`, `acid → shape.faces`: the last refused, `LOOP_FACES` with `shape → scene → history → frame → acid → shape`.
    - `pattern → acid.2.image`, `acid.2 → shape.faces`, `scene → acid.2.aux`: the last refused, `LOOP_FACES` with `acid.2 → shape → scene → acid.2`.
    - `scene → pattern.media`: `LOOP_FACES` with `pattern → shape → scene → pattern`.
    - `history → backdrop.image`: `LOOP_BACKDROP` with `backdrop → history → backdrop`.

    Each row also asserts that the refused wire is not in `spec.wires` and every other wire is.
  - `test_the_later_wire_closing_a_sink_loop_is_the_one_refused`: row 4 above. `run_of(spec) == ("acid",)` and `Wire("frame", "acid.image") in spec.wires`.
  - `test_a_loop_through_a_delay_is_legal`: `scene → delay.image`, `delay → shape.faces` gives no notes. `delay → zoomblur.2.image`, `zoomblur.2 → composite.under`, `scene → composite.over`, `composite → delay.image`, `composite → output.1.image` (with the composite, zoomblur.2 and delay entries) gives no notes, and `wire_loops` of its wires is `{}`.
  - `test_a_delay_into_itself_is_still_refused`: `delay → delay.image` gives the existing `delay into itself makes a loop`.
  - `test_frame_feeds_the_run_only`: `frame → delay.image`, `frame → acid.aux` and `frame → output.2.image` each note `FRAME_SOURCE_REFUSAL`; `frame → acid.image` with `acid → fx.image` notes nothing.
  - `test_a_delay_reaches_only_when_read` (each section with the run `frame → fx.image`, as `_reached_edges` filters only then): `scene → delay.image` alone means `"delay" not in reaches(spec)`, and `spec.wiring().wires` lacks the wire. Adding `delay → output.2.image` means `{"delay", "scene"} <= reaches(spec)` and the wiring keeps both wires.
  - `test_the_new_words_are_v5_only`: for a section using each kind, `graphmigrate.uses_free_words(spec)` is True, `legacy_values(section, {})` is None, and `legacy_section(section)` holds none of the four kinds' entries or wires.
  - In `tests/test_graph_edit.py`: `test_a_sink_loop_drag_is_refused_in_words`. With the `edit(rig)` harness, `e.refusal("rout:scene", "rin:shape/faces")` returns `"wire scene → shape.faces — " + LOOP_FACES.format(path="shape → scene → shape")`. The section is unchanged. A `delay` entry then lets `e.refusal("rout:delay", "rin:shape/faces")` return None. (The canvas's `rout:delay` pin arrives in T5; until then this half drives `render_wire(e, "delay", "shape.faces", dry=True)`.)
- [ ] **Step 2:** `uv run pytest tests/test_graph_feedback.py tests/test_graph_edit.py -q` shows the new tests FAIL.
- [ ] **Step 3:** implement in `graph.py` and `graphmigrate.py`. `_Wiring._sink` and `_Wiring.aux`'s build-time loop words stay as a backstop for a `Wiring` built by hand.
- [ ] **Step 4:** `uv run pytest -q -x` passes, with `tests/test_graph_wires.py`'s explicit-loop words unchanged and `tests/test_graph_free.py::test_the_faces_run_and_a_switch_ends_a_run` still passing (it asserts the run only). The golden suite is unchanged (no render code touched).
- [ ] **Step 5:** commit `"Plan 34 T1: delay, resize, echo and dream as words; a loop through the faces, the backdrop or the frame refused at read"`.

---

### Task 2 (T2): The delay — a frame late, half-float, ping-pong

**Files:**
- Modify `hyperspace/graph.py`:
  - new `Node.own_size`, `Node.said`, `OWN_FIT`, `Delay`, `DelayWrite`;
  - `Effect.paint` and `Effect.image` (the own-size path);
  - `picture` (the `dtype` keyword);
  - `default_graph` (a `Delay` for each delay a wire leaves);
  - `_Wiring.node` and `_Wiring._put` (a wire into `delay.image` builds the `DelayWrite`, added to `capture.after`);
  - `PatternNode.size_for` (an own-size head).
- Modify `hyperspace/render.py`:
  - new `DelayPair`, `Renderer.delay_pair`, `Renderer._turn_delays`, `REFIT_FS`, `Renderer._refit`, `Renderer._refit_program`, `Renderer._sampler`;
  - `_frame_target(key, size, dtype="f1")`;
  - `_draw_frame` calls `_turn_delays(graph)` after `_graph_for`.
- Test `tests/test_graph_delay.py` (new).
- Create fixtures `tests/fixtures/presets/delay-faces.json` and `delay-trails.json`; add both to `tools/golden_frames.py` `FIXTURE_PRESETS`; goldens.

**Interfaces — Consumes:** T1's `DelayAt`, `GraphSpec.delays`, the reached wiring; plan 33's `Frame.at`, `_prune_sized`, `SIZED_KEEP_FRAMES`, `media_tex.fit_scale` / `COVER` / `CONTAIN` / `STRETCH`. **Produces:**
- `Node.own_size(self, frame: Frame) -> tuple[int, int] | None`: None by default. `Node.said: str = ""`, a class attribute that a node sets in `run`.
- `graph.OWN_FIT = COVER` (the fit index `0`, `media_tex.FITS[0]`). `graph.py` imports no media module, so the constant is `0` with a comment naming `media_tex.COVER`, and `tests/test_graph_delay.py::test_own_fit_is_cover` holds the two equal.
- `graph.Delay(Node)`: `KIND = "delay"`, `INPUTS = {}`, `OUTPUT = IMAGE`, `TIMED = False`.
  - `own_size(frame)`: the read side's size while the pair `holds`, else None.
  - `reads(frame)`: `frame.r.delay_pair(self.name).holds`.
  - `paint(frame, dst)`: `r._refit(read_tex, dst, fit=OWN_FIT)` while it holds, else `dst` cleared to `(0, 0, 0, frame.bg_alpha)`.
  - `image(frame)`: the read texture when its size is `frame.size`. Otherwise it refits once a frame into `r._frame_target(frame.key(self.name + "#fit"), frame.size, dtype="f2")`. Not holding, it returns that target cleared to transparent black.
  - `run(frame)`: sets `said`.
- `graph.DelayWrite(Node)`: `KIND = "delay"`, `INPUTS = {"image": IMAGE}`, `OUTPUT = None`, `TIMED = True`, `SIZED = frozenset({"image"})`. Constructor `DelayWrite(name: str, delay: str, image: Node | None = None, after=())`, with `name` = `f"{delay}(write)"`.
  - `held(frame) -> tuple[int, int]`: `src.own_size(frame) or frame.root.size`.
  - `size_for("image", frame)`: `held(frame)`.
  - `run(frame)`: `fbo = r.delay_pair(self.delay).target(ctx, held)`, then cleared to `(0, 0, 0, 0)`. If the input `reads` at `at` (`frame` when `held == frame.size`, else `frame.at(held)`), `src.paint(at, fbo)` runs under `frame.timed(self.name)`. Then `pair.wrote = True`.
- `render.DelayPair`: fields `read: tuple[Texture, Framebuffer] | None`, `write: tuple[...] | None`, `holds: bool = False`, `wrote: bool = False`, `idle: int = 0`. Methods:
  - `target(ctx, size) -> Framebuffer`: the write side at `size`. When it is missing or another size, the write side is released and made again as RGBA `dtype="f2"`, LINEAR, `repeat_x = repeat_y = False`, cleared to transparent black. The read side is left alone.
  - `turn()`: `wrote` means swap the sides and `holds = True`; otherwise `holds = False`. `wrote = False` either way.
  - `release()`.
- `Renderer.delay_pair(name: str) -> DelayPair`: one per name in `self.__dict__.setdefault("_delays", {})`, made on first ask.
- `Renderer._turn_delays(graph: Graph) -> None`, once a frame before `evaluate`: each pair `turn()`s. A pair whose name is no `Delay` of `graph` counts `idle += 1` and is released and dropped at `SIZED_KEEP_FRAMES`. One in the graph resets `idle = 0`.
- `render.REFIT_FS`. Uniforms: `u_src`, `u_crop` (vec4 x0, y0, w, h in the source's GL uv), `u_scale` (vec2, `fit_scale(fit, crop px, dst px)`) and `u_clamp` (vec4 min uv, max uv). It writes transparent black outside the fit or the crop. Inside it writes `texture(u_src, clamp(u_crop.xy + q * u_crop.zw, u_clamp.xy, u_clamp.zw))` untouched (premultiplied in, premultiplied out).
- `Renderer._refit(tex, dst, crop=(0.0, 0.0, 1.0, 1.0), fit=COVER, filter="linear", clamp=None, mip=False) -> None`. It draws into `dst.viewport` with blending off. The sampler is `self._sampler(filter, mip)`: a moderngl `Sampler`, cached by key, bound at location 0 and cleared after, so `tex.filter` is never changed. With `mip` it calls `tex.build_mipmaps()` and puts `tex.filter` back as it was. Blending is on again on every exit.
- `_frame_target(key, size, dtype="f1")`: a stored texture whose `dtype` differs is released and made again. The default keeps every existing caller byte for byte.
- `picture(frame, node, dtype="f1")`: the key is `node.name + "#picture"`, plus `"." + dtype` when not `"f1"`.
- **The own-size rule for `Effect`:**
  - `Effect.own_size(frame)` is `self.inputs["image"].own_size(frame)` (None without an input).
  - `Effect.paint(frame, dst)`, when that is not None and not `frame.size`: `tex = self.image(frame.root.at(own))` (or `self.image(frame.root)` when `own == frame.root.size`), then `r._refit(tex, dst, fit=OWN_FIT)`.
  - `Effect.image(frame)`, in the same case: that texture refit once a frame into `r._frame_target(frame.key(self.name + "#fit"), frame.size, dtype="f2")`.
  - `SwitchNode.own_size` is its pick's.
  - `PatternNode.size_for("media", frame)` returns its head's `own_size(frame)` first, when not None.
- `default_graph`: one `Delay(name)` for each delay name some wire leaves (`wire_node_kind(w.src) == "delay"`), added beside the media nodes. `_Wiring._put` for `w.node` of kind `delay` adds `DelayWrite(f"{w.node}(write)", w.node, image=src)` and appends it to `capture.after`.

- [ ] **Step 1: Failing tests** in `tests/test_graph_delay.py`. GL tests use the `ctx` fixture and the harness of `tests/test_graph_faces.py` (`_renderer`, `_draw`, `_faces`, `_rgba`, `Still`, `_media`, `section`), imported.
  - `test_a_delay_shows_last_frames_picture`: channel a's still is swapped red → blue → green across frames 1–3, with `media.a → delay.image` and `delay → output.2.image`. Output 2's centre pixel is the ground at frame 1, red at frame 2 and blue at frame 3.
  - `test_the_first_frame_reads_nothing_and_the_faces_show_the_pattern`: with `scene → delay.image` and `delay → shape.faces`, frame 1's picture equals the faces-unwired frame pixel for pixel, and frame 2's does not.
  - `test_a_delay_ping_pongs_half_float` (Review Focus 1): after each of three frames, `pair = r.delay_pair("delay")` has `pair.read[0].dtype == pair.write[0].dtype == "f2"` and `pair.read[0].glo != pair.write[0].glo`. The read side at frame n+1 is the texture written at frame n (`glo` compared).
  - `test_a_loop_of_effects_never_reads_what_it_writes` (Review Focus 1): the `delay-trails` section over 8 frames gives `ctx.error == "GL_NO_ERROR"`. A spy on `FxChain.run_one` records each pass's `(src.glo, dst.color_attachments[0].glo)`, and no pass has the two equal or uses the write side's `glo` as `src`.
  - `test_a_size_change_loses_no_frame` (Review Focus 4): draw two frames at 240×150, then frame 3 at 200×200. Output 2 at frame 3 is not the ground: it is frame 2's picture fitted. `pair.write[0].size == (200, 200)` after frame 3.
  - `test_a_graph_rebuild_keeps_the_delay` (Review Focus 4): after two frames, land a section with `media.b → output.3.image` added. `Renderer._graph_for` gives a new graph and `r.delay_pair("delay").holds` is still True at frame 3.
  - `test_a_delay_leaving_the_graph_is_released` (Review Focus 4): after the delay's wires are removed, `"delay" in r._delays` holds for `SIZED_KEEP_FRAMES - 1` frames and is gone after `SIZED_KEEP_FRAMES`.
  - `test_the_delay_write_runs_before_the_capture`: in `g.order`, `delay(write)` comes before `capture`, and `capture.after` holds it.
  - `test_refit_cover_and_contain`: a 200×100 texture, left half red and right half blue, refit into a 64×64 framebuffer. `fit=COVER` gives columns 0–31 red and 32–63 blue. `fit=CONTAIN` gives rows 0–15 and 48–63 transparent black and the middle rows half red, half blue. `fit=STRETCH` gives every row half and half. The texture's `filter` is unchanged after `_refit(..., mip=True)`.
  - `test_own_fit_is_cover`: `G.OWN_FIT == media_tex.COVER`.
  - `test_nothing_of_plan_33_has_an_own_size`: over every node of the default graph and of each plan-33 fixture's graph (`tests/fixtures/presets/*.json`, landed through the golden tool's `Rig`), `own_size(frame)` is None.
- [ ] **Step 2:** run, see FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** create the two fixtures. Each has a `frame → fx.image` run and `"schema": "hyperspace.preset/5"`, with the values plan 33's fixtures carry.
  - `delay-faces`: nodes `delay`; wires `scene → delay.image`, `delay → shape.faces`.
  - `delay-trails`: nodes `delay`, `zoomblur` instance 2, `composite`; wires `delay → zoomblur.2.image`, `zoomblur.2 → composite.under`, `scene → composite.over`, `composite → delay.image`, `composite → output.1.image`; `fx.zoomblur.2.on` true and `.mix` 1.

  Record `--only delay-faces,delay-trails`. Run the whole golden suite: the 693 are unchanged.
- [ ] **Step 5:** `uv run pytest -q -x` passes. Commit `"Plan 34 T2: the delay — last frame's picture, half-float ping-pong, a loop through it drawn"`.

---

### Task 3 (T3): The look-back's frames as sources

**Files:**
- Modify `hyperspace/graph.py`:
  - new `EchoNode`, `DreamNode`, `Graph.reads_ring`;
  - `default_graph` builds one node per echo or dream a wire leaves;
  - `_Wiring.node`.
- Modify `hyperspace/lookback.py`: `Lookback.echo_slot`, `Lookback.held`, `Lookback.keep`, `_capture`.
- Modify `hyperspace/render.py`: `_draw_frame` sets `self.lookback.keep`.
- Test `tests/test_graph_echo.py` (new).
- Create fixture `tests/fixtures/presets/echo-faces.json`; add it to `FIXTURE_PRESETS`; goldens.

**Interfaces — Consumes:** T1's `EchoAt`, `DreamAt`; T2's `_refit`, `own_size`, `said`, `OWN_FIT`. **Produces:**
- `Lookback.echo_slot(k: int) -> int | None`: `self._captures[-k][0]` when `self.atlas is not None and 1 <= k <= len(self._captures)`, else None.
- `Lookback.held() -> int`: `len(self._captures)`.
- `Lookback.keep: bool = False`. `_capture` calls `idle()` and returns only when `not s.on and not self.keep`. `composite` and `wants_cover` are unchanged (the wake needs `dream.on`).
- `graph.EchoNode(Node)`: `KIND = "echo"`, `INPUTS = {}`, `OUTPUT = IMAGE`, `TIMED = False`. Constructor `EchoNode(name: str, k: int)`.
  - `reads(frame)`: `frame.r.lookback.echo_slot(self.k) is not None`.
  - `own_size(frame)`: `tuple(lb.echo)` while it reads.
  - `paint(frame, dst)`: `r._refit(lb.atlas, dst, crop=(0.0, slot / MAX_ECHOES, 1.0, 1.0 / MAX_ECHOES), fit=OWN_FIT, clamp=(0.0, (slot + 0.5 / eh) / MAX_ECHOES, 1.0, (slot + 1 - 0.5 / eh) / MAX_ECHOES))` while it reads, else `dst` cleared to `(0, 0, 0, frame.bg_alpha)`.
  - `image(frame)`: refit once a frame into `r._frame_target(frame.key(self.name + "#fit"), frame.size, dtype="f2")`.
  - `run(frame)`: sets `said` from `lb.echo`, `lb.state.gap`, `frame.graph.wiring.history` and `backdrop_history` (Global Constraints' words).
- `graph.DreamNode(Node)`: the same shape. `reads` is `lb.dream is not None and lb.dream_frame >= 0`. `paint` refits `lb.dream` with `crop=(0, 0, 1, 1)`. `said` reads `lb.source` (None: no worker).
- `Graph.reads_ring: bool`, settled by `default_graph`: any `EchoNode` or `DreamNode` in `nodes`. `Renderer._draw_frame` sets `self.lookback.keep = getattr(graph, "reads_ring", False)` after `_graph_for` (getattr: a renderer from before has no lookback).

- [ ] **Step 1: Failing tests** in `tests/test_graph_echo.py`:
  - `test_echo_k_is_the_kth_newest_capture`: three slots written with `Lookback.write_slot(slot, pixels, at=t)` in red, green and blue at t = 1, 2, 3. `echo.1 → output.2.image` shows blue, `echo.2` green and `echo.3` red, each at the output's centre.
  - `test_an_echo_past_the_ring_reads_nothing`: with those three captures, `echo.4 → shape.faces` draws the faces-unwired frame, and `echo.4 → output.2.image` shows the ground. `EchoNode.said == "not held yet: the ring holds 3 of 32"`.
  - `test_the_ring_keeps_capturing_for_an_echo_with_the_look_back_off`: with `dream.on` False and `echo.1 → output.2.image`, `lb.held() == 3` after three frames (gap 0). Output 1's picture equals the same section without the echo wire. With the echo wire removed, `lb.held() == 0` after one frame (`idle`).
  - `test_an_echo_read_this_frame_is_last_frames_capture`: gap 0, a fake channel changing colour each frame on the backdrop, and `echo.1 → output.2.image`. Output 2 at frame n is the backdrop's colour at frame n−1.
  - `test_a_res_change_empties_the_echoes`: after four frames, `dream.res` goes 2 → 3. `echo.1` reads nothing in the next frame, reads again the frame after, and `echo.2` reads only once two commits have landed.
  - `test_the_dream_reads_nothing_until_written`: `dream → output.2.image` shows the ground and `said == "no dream worker: reads nothing"`. After `lb.write_from(pixels, 1)` and a fake `lb.source` set, the output shows `pixels` (centre) and `said` starts with the echo size.
  - `test_echo_words_say_size_and_cadence`: at 960×600 with `dream.res` 2 (256) and gap 0, after two frames `said == "408×256 · every frame · the scene"`. With gap 0.1 it is `"408×256 · every 0.10 s · the scene"`. With `history.holds` `scene+hands` it is `"… · the scene + hands"`.
  - `test_an_echo_on_the_faces_is_fitted`: `echo.1 → shape.faces`, with `Shape.prepare`'s paint into `face_pic` (1024²). `face_pic.tex` centre equals slot centre colour; `r.face_error == ""`.
- [ ] **Step 2:** run, see FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** create `echo-faces`. It has the run `frame → fx.image`, values `dream.on: false` and `dream.gap: 0`, an `echo` index 3 entry and the wire `echo.3 → shape.faces`. Record `--only echo-faces`. The whole golden suite: everything before is unchanged.
- [ ] **Step 5:** `uv run pytest -q -x` passes. Commit `"Plan 34 T3: the look-back's echoes and dream as picture sources; the ring kept while read"`.

---

### Task 4 (T4): The resize — crop, a size of its own, its params per instance

**Files:**
- Modify `hyperspace/view.py`: new `ResizeState`, `RESIZE_SIDES`, `RESIZE_ASPECTS`, `RESIZE_FITS`, `RESIZE_FILTERS`; `ViewState.resize`.
- Modify `hyperspace/params.py`: new `RESIZE_GROUP`, `resize_ids`, `is_resize_id`, `declare_resizes`; `PERFORMANCE_GROUPS`; `build_registry` (`r.resize_state` = `view.resize`).
- Modify `hyperspace/preset.py`: `GraphSection.land` calls `declare_resizes`; `load_doc` sorts `is_resize_id` into `later`; `NO_MODULE`.
- Modify `hyperspace/ui_presets.py`: `OVERVIEW_GROUPS` leaves out `"resize"`.
- Modify `hyperspace/graph.py`: new `ResizeNode`, `resize_size`; `MAKERS`; `_Wiring.node` / `_Wiring._make`; `Frame.resizes`.
- Modify `hyperspace/render.py`: `_draw_frame` copies `s.resize` into `Frame.resizes`.
- Test `tests/test_graph_resize.py` (new), `tests/test_presets.py`.
- Create fixtures `tests/fixtures/presets/resize-faces.json` and `resize-crop.json`; add `resize-crop` to `MEDIA_FIXTURES` and `resize-faces` to `FIXTURE_PRESETS`; goldens.

**Interfaces — Consumes:** T1's `ResizeAt`, `GraphSpec.resizes`; T2's `_refit`, `own_size`, the `Effect` own-size path, `DelayWrite.held`, `_frame_target(dtype=)`, `picture(dtype=)`; plan 33's `declare_switches` pattern. **Produces:**
- `view.RESIZE_SIDES = (16, 32, 64, 128, 256, 512, 1024, 2048)`, `RESIZE_ASPECTS = ("input", "square")`, `RESIZE_FITS = ("cover", "contain", "stretch")` (`media_tex.FITS`' order; a test holds them equal) and `RESIZE_FILTERS = ("linear", "nearest")`.
- `view.ResizeState` dataclass: `size: int = 4` (an index into `RESIZE_SIDES`: 256), `aspect: int = 0`, `fit: int = 0`, `filter: int = 0`, `crop_x: float = 0.5`, `crop_y: float = 0.5`, `crop_w: float = 1.0`, `crop_h: float = 1.0`. `ViewState.resize: dict[str, ResizeState]` (default_factory dict).
- `params.RESIZE_GROUP = "resize"`, added to `PERFORMANCE_GROUPS` after `"switch"`.
- `params.resize_ids(name: str) -> list[str]`: `[f"{name}.{k}" for k in ("size", "aspect", "fit", "filter", "crop_x", "crop_y", "crop_w", "crop_h")]`.
- `params.is_resize_id(pid) -> bool`: `re.fullmatch(r"resize(?:\.(?:[2-9]|[1-9][0-9]+))?\.(size|aspect|fit|filter|crop_x|crop_y|crop_w|crop_h)", pid)`.
- `params.declare_resizes(r: Registry, names: Iterable[str]) -> list[str]`, as `declare_switches`. For each name it declares the four enums (`size` over `[str(s) for s in RESIZE_SIDES]`, `aspect`, `fit`, `filter`) and the four continuous params (`crop_x` / `crop_y` 0–1, `crop_w` / `crop_h` 0.01–1). All are group `resize`, modulatable, with labels `"{name} size"` … `"{name} crop w"`. They read and write `r.resize_state[name]`, a `ResizeState` made when first declared. Those of names no longer given are removed. It returns the changed ids.
- `graph.resize_size(side: int, aspect: str, src: tuple[int, int]) -> tuple[int, int]`. `"square"` gives `(side, side)`. `"input"` keeps `src`'s orientation, with its long side `side` and its short side `max(1, round(side * short / long))`.
- `Frame.resizes: dict[str, Any]`, filled by `_draw_frame` as `dict(getattr(s, "resize", None) or {})`.
- `graph.ResizeNode(Node)`: `KIND = "resize"`, `INPUTS = {"image": IMAGE}`, `OUTPUT = IMAGE`, `MAKES = False`, `TIMED = True`.
  - `state(frame)`: `frame.root.resizes.get(self.name) or ResizeState()`.
  - `size_for("image", frame)`: `src.own_size(frame) or frame.root.size`.
  - `own_size(frame)`: `resize_size(RESIZE_SIDES[st.size], RESIZE_ASPECTS[st.aspect], self.size_for("image", frame))`.
  - `made(frame) -> Texture | None`, once a frame (root data `name + "#own"`):
    1. the input as a texture at its size: `src.image(at_in)`, else `picture(at_in, src, dtype="f2")`;
    2. the crop as a GL-uv rect: `x0 = crop_x - crop_w / 2`, `y0 = 1 - crop_y - crop_h / 2`, `w = crop_w`, `h = crop_h`;
    3. `mip = filter == "linear" and (crop px w / out w > 2 or crop px h / out h > 2)`;
    4. `r._refit(tex, own_fbo, crop=…, fit=st.fit, filter=…, mip=mip)` into `r._frame_target((self.name + "#own", own), own, dtype="f2")`, under `frame.timed(self.name)`.

    None when the input is None or does not `reads`.
  - `reads(frame)`: the input's.
  - `paint(frame, dst)`: `r._refit(made, dst, fit=OWN_FIT, filter=RESIZE_FILTERS[st.filter])`, or the ground.
  - `image(frame)`: `made` when `own == frame.size`, else that refit once a frame into `frame.key(self.name + "#fit")` (f2).
  - `run(frame)`: sets `said`.
- `MAKERS = ("effect", "composite", "switch", "resize")`. `_Wiring._make` builds `ResizeNode(name, image=srcs.get("image"))`. A resize fed by no wire is dormant: `"{name} is fed by nothing here: wire its input"`.

- [ ] **Step 1: Failing tests** in `tests/test_graph_resize.py`:
  - `test_resize_size_model`:
    - `resize_size(256, "input", (1920, 1080)) == (256, 144)`
    - `(1080, 1920)` gives `(144, 256)`
    - `resize_size(16, "input", (1920, 1080)) == (16, 9)`
    - `resize_size(64, "square", (1920, 1080)) == (64, 64)`
    - `resize_size(256, "input", (1024, 1024)) == (256, 256)`
  - `test_the_fits_are_the_media_fits`: `view.RESIZE_FITS == media_tex.FITS`.
  - `test_declare_resizes_comes_and_goes`:
    - `declare_resizes(reg, ["resize", "resize.2"])` declares the 16 ids of `resize_ids`, each group `resize` and modulatable. `reg["resize.2.size"]` has the 8 choices and value index 4; `reg["resize.crop_w"].value == 1.0`.
    - `declare_resizes(reg, ["resize"])` removes `resize.2.*` and returns those 8 ids.
    - Setting `reg["resize.crop_x"]` writes `reg.resize_state["resize"].crop_x`.
  - `test_a_resize_makes_its_own_size`: `media.a → resize.image`, `resize → output.2.image`, a 16:9 still, `resize.size` index 2 (64). After one frame, `r._frames` holds `("resize#own", (64, 36))` with `dtype == "f2"`, and `"resize" in r._graph.timed`.
  - `test_an_effect_after_a_resize_runs_at_its_size` (Review Focus 5): `resize → acid.2.image`, `acid.2 → output.2.image` gives `"acid.2" in r.stats["effects"]` and `(64, 36) in r._pools`, and no frame-size pass ran for `acid.2` (`run_one`'s `dst` sizes recorded by a spy are all `(64, 36)`).
  - `test_a_delay_through_a_resize_holds_a_small_buffer` (Review Focus 5): `scene → resize.image`, `resize → delay.image`, `delay → shape.faces`, size 64, aspect square. After two frames `r.delay_pair("delay").read[0].size == (64, 64)`.
  - `test_the_crop_takes_the_rect`: a still with quadrants red (top left), green (top right), blue (bottom left) and white (bottom right). `crop_x = crop_y = 0.25`, `crop_w = crop_h = 0.5` into `output.2.image` makes output 2 all red (centre and the four inset corners).
  - `test_a_crop_past_the_edge_is_transparent`: `crop_x = 0.9`, `crop_w = 0.5` makes the made texture's right ~30% columns transparent black and the left part the still.
  - `test_nearest_keeps_hard_pixels`: a 2×2 checker still at size 16 nearest into a 64² output gives pixel values only from the two colours. With linear, some pixel lies strictly between them.
  - `test_linear_mipmaps_a_big_reduction`: a 512×512 one-pixel stripe still at size 16 linear gives a made texture with every pixel's red within 0.5 ± 0.1. At nearest every pixel is 0 or 1.
  - `test_a_route_animates_the_crop_without_a_rebuild`: an LFO route on `resize.crop_w` over 8 frames leaves `Renderer._graph_for` returning the same object, and output 2 differs between frames 1 and 5.
  - `test_a_size_step_reallocates_once_each_way`: `size` stepped 64 → 128 → 64 → 128 over 4 frames makes exactly two `("resize#own", …)` targets (`_frames`' keys) and none released within `SIZED_KEEP_FRAMES`.
  - `test_nothing_of_plan_33_draws_through_a_resize`: the golden suite's 693 unchanged (a pointer, not a new test: Step 4).
  - In `tests/test_presets.py`: `test_resize_values_save_and_load_with_the_preset`. A preset with a `resize.2` entry and `resize.2.crop_x = 0.3`, saved and reloaded into a fresh rig, gives `reg["resize.2.crop_x"].value == 0.3` and no unknown-id note. A preset without the entry undeclares `resize.2.*`.
- [ ] **Step 2:** run, see FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** create the fixtures and record `--only resize-faces,resize-crop`. The whole golden suite: everything before is unchanged.
  - `resize-faces` (the owner's headline): nodes `resize`, `delay`; wires `scene → resize.image`, `resize → delay.image`, `delay → shape.faces`; values `resize.size: 2` (64), `resize.aspect: 1` (square), `resize.filter: 1` (nearest).
  - `resize-crop` (a media fixture: still `a` from `tests/golden/media/`): nodes `resize` and `acid` instance 2; wires `media.a → resize.image`, `resize → acid.2.image`, `acid.2 → output.2.image`; values `resize.size: 3`, `resize.crop_x: 0.35`, `resize.crop_w: 0.5`, `resize.crop_h: 0.5`, `fx.acid.2.on: true`, `fx.acid.2.mix: 1`.
- [ ] **Step 5:** `uv run pytest -q -x` passes. Commit `"Plan 34 T4: resize — crop and a size of its own; a delay and an effect after it run small"`.

---

### Task 5 (T5): GRAPH adds, draws and explains them

**Files:**
- Modify `hyperspace/graphview.py`:
  - `picker`, `render_add`, `render_drop`, `_stand_in`, `unreached`;
  - `MAKER_KINDS`, `MEDIA_MADE` and `media_made`'s heads, `AREA`, `returns`;
  - `OWNERS["resize"]`;
  - `build`: a `DelayWrite` drawn as its delay's `image` port;
  - `summary`: `said` first;
  - `spec_name`.
- Modify `hyperspace/ui_graph.py`: `render_picker`'s `look-back frame` submenu, `home_page`.
- Test `tests/test_graph_edit.py`, `tests/test_graph_areas.py`, `tests/test_graph_legible.py`, `tests/test_graphview.py`.

**Interfaces — Consumes:** T1–T4's kinds and node classes, `said`; plan 33's `render_add`, `_with_run`, `_land`, `Edit.refusal`, `returns`, `media_made`, `side_groups`, `_param_rows`. **Produces:**
- `graphview.picker(edit)` gains, after the switch and the channels' switch and before hands: `("delay", None, "delay")`, `("resize", None, "resize")`, `("echo", "1", "echo.1 (newest)")`, `("echo", str(k), f"echo.{k}")` for k from 2 to 31, `("echo", "32", "echo.32 (oldest)")`, and `("dream", None, "dream")`.
- `graphview.render_add(edit, kind, file)`:
  - `"delay"` and `"resize"` add the next instance (`max(n) + 1`), saying `"{name} added: wire a picture into {name}.image — its picture is that one, a frame late"` and `"{name} added: wire a picture into {name}.image — it makes it at {name}.size"`.
  - `"echo"` with `file = str(k)` adds `EchoAt(k)`, saying `"echo.{k} added: the look-back's {ordinal} newest frame — wire it into a picture port"` (`1st`, `2nd`, `3rd`, `4th` …). A second add is refused: `"echo.{k} is in the graph already"`.
  - `"dream"` says `"dream added: the look-back's dream buffer — wire it into a picture port"`; a second add is refused: `"dream is in the graph already"`.

  Each calls `_with_run(doc, spec)` and sets `edit.added`.
- `graphview.render_drop`: kinds `delay` and `resize` are dropped by instance, `echo` by index and `dream` alone, with their wires, as `composite` / `switch` are.
- `MAKER_KINDS = ("effect", "composite", "switch", "resize", "delay", "echo", "dream")` (read by `unreached` alone). `unreached(spec)`'s names also take `spec.delays`, `spec.resizes`, `spec.echoes` and `spec.dream`, so an unwired entry is drawn faint. `_stand_in` returns `Delay(name)`, `ResizeNode(name)`, `EchoNode(name, k)` and `DreamNode("dream")`.
- `build`: a `DelayWrite` has no `VNode`. Its `image` input is a port `image` on `render:<delay>` with pin `rin:<delay>/image`; its source's cable ends there. A stand-in delay has that port too. `spec_name("rin:delay/image") == ("delay.image", None)`.
- `AREA`: `"Delay": MEDIA`, `"EchoNode": MEDIA`, `"DreamNode": MEDIA`, `"ResizeNode": SHADERS`. `MEDIA_MADE` gains `rgraph.ResizeNode`. `media_made` counts `Delay`, `EchoNode` and `DreamNode` as heads, as `MediaNode` and `PatternNode` are.
- `returns(view, lay)` also holds every cable whose destination port is a `Delay` node's `image` (by design: the picture kept for next frame).
- `OWNERS["resize"] = _resize_owner`, which returns `pid.rpartition(".")[0]` (`resize.2.crop_x` → `resize.2`).
- `summary(n)`: a render node's `getattr(n.ref, "said", "")`, when not empty, is its first line, after `REACHES_NOTHING` when faint.
- `ui_graph.render_picker`: a `look-back frame` menu (constant `LOOKBACK_MENU = "look-back frame"`) holds the `echo` and `dream` items. An item already in the section is drawn disabled. `delay` and `resize` are top-level items beside `switch`.
- `ui_graph.home_page`: an `EchoNode` or `DreamNode` gives `("lookback", None)`; a `Delay` or `ResizeNode` gives `None`.

- [ ] **Step 1: Failing tests:**
  - `test_graph_edit.py::test_the_picker_offers_delay_resize_and_the_look_back_frames`: `picker(e)` holds the exact items above, in that order and place.
  - `test_graph_edit.py::test_each_new_node_lands_unwired_and_faint`:
    - `render_add(e, "delay")` puts `DelayAt(1)` in the section, `edit.said` reads as above, and `view.node("render:delay").faint` with summary `["reaches nothing", …]`. A second add gives `delay.2`.
    - The same for `resize`.
    - `render_add(e, "echo", "3")` gives `EchoAt(3)`; again, `"echo.3 is in the graph already"`.
    - `render_add(e, "dream")` twice is refused the second time in words.
    - Each add with no run in the section adds `frame → fx.image`.
  - `test_graph_edit.py::test_dropping_each_new_node_takes_its_wires`: `render_drop` of `delay`, `resize.2`, `echo.3` and `dream`, each wired, removes the entry and every wire touching it in one undo step.
  - `test_graph_edit.py::test_a_delay_is_one_node_with_an_image_pin`: `scene → delay.image`, `delay → shape.faces` built and viewed gives no `render:delay(write)` node. `render:delay` has port `image` with pin `rin:delay/image`, and the cable from `rout:scene` ends there. Dragging `rout:history` onto `rin:delay/image` replaces the wire (`render_wire`).
  - `test_graph_edit.py::test_a_sink_loop_drag_is_refused_in_words` (T1's test, now through `e.refusal("rout:delay", "rin:shape/faces")` returning None).
  - `test_graph_areas.py::test_the_feedback_nodes_sit_in_their_areas`: `delay`, `echo.3` and `dream` are MEDIA. A resize fed by `scene` is SHADERS; one fed by `media.a` is MEDIA. `acid.2` fed by `delay` alone is MEDIA.
  - `test_graph_areas.py::test_a_delays_input_cable_runs_back_by_design`: `scene → resize → delay.image`, `delay → shape.faces`. The cable into `rin:delay/image` is in `returns`, and `back_wires(view) == []`.
  - `test_graph_legible.py::test_a_resize_nodes_params_are_rows_in_the_side_panel`: `side_groups(panel, view.node("render:resize"))` is `[("resize", resize_ids("resize"))]`. `_param_rows` draws 8 rows headless. A row edit (`Panel._row` on `resize.crop_w`) sets the param through the registry, one undo step.
  - `test_graph_legible.py::test_home_page_maps_the_feedback_nodes`: echo and dream go to `("lookback", None)`; delay and resize give None.
  - `test_graphview.py::test_the_feedback_nodes_say_their_words`: each fixture drawn at 960×600 through the golden tool's `Rig` for four frames. The `render:echo.3` summary's first line in `echo-faces` is `"408×256 · every frame · the scene"`. The `render:delay` summary's first line in `delay-faces` is `"last frame's · 960×600 half-float"`. After one frame only, it is `"nothing yet"`.
  - `test_graph_legible.py::test_every_nodes_side_panel_draws` (plan 33's) passes with the four new kinds in its fixture.
- [ ] **Step 2:** run, see FAIL. **Step 3:** implement. **Step 4:** `uv run pytest -q -x`; the golden suite unchanged.
- [ ] **Step 5:** commit `"Plan 34 T5: GRAPH adds a delay, a resize and the look-back's frames; a delay is one node; a loop drag is refused in words"`.

---

### Task 6 (T6): Docs

**Files:**
- `docs/plans/34-feedback.md`: a "What was built" section above the design, as plan 33's, with the commits by task, the rulings and "What no person has verified".
- `docs/plans/README.md`: the entry becomes "built".
- `docs/ARCHITECTURE.md`: the render graph section — the delay as z⁻¹, `own_size`, the hidden edges.
- `docs/ENGINEERING.md`: the delay, the echoes, the resize, both Macs and `/5`.
- `docs/DECISIONS.md`: a "Feedback" section.
- `docs/DECISION-REGISTER.md`: rows 353–371 in the table and in full (Answer, Built, Other options, To reverse, Rough edge, Judge it).
- `docs/plans/11-hand-checks.md`: group AD, checks 332–341 as the spec lists them; the header's range sentence.
- `docs/TESTING-GUIDE.md`: the five fixtures and 40 goldens.
- `docs/plans/merge-checklist.md`.

- [ ] **Step 1:** write them, with the test names each row's "Built" cites.
- [ ] **Step 2:** `uv run pytest -q` (the doc-linked tests, if any).
- [ ] **Step 3:** commit `"Plan 34 T6: docs — feedback as built, rows 353–371, hand checks group AD"`.
