# Plan 34 Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `delay` picture node (last frame's input) makes a loop on GRAPH legal when it passes through one. The look-back's frames (`echo.1` … `echo.32`, `dream`) are picture sources. A `resize` node crops its input and makes it at a size of its own. Every wire that would loop through the faces or the backdrop is refused when the section is read, in words that point at a delay, instead of landing dormant.

**Status (2026-10-25).** T1–T3 are built (54b7495..ce0b0c6) and kept below as they were written and built, in plan 33's ids. Plan 34 was then paused (ledger R8) and plan 35, "the frame as wires", was built on this branch (51ef105..6193cb7). **T4–T6 below are rewritten on plan 35's model.** Read [`35-free-frame.md`](35-free-frame.md)'s "What was built" and "What changes for plan 34" first. In T1–T3's text, `default_graph`, `_Wiring`, `MAKERS`, `frame`/`fx`, `history`, `media.<c>` and `capture.after` are plan 33's. Plan 35 replaced them with `build_graph`/`_Build`, `lookback`, `channel.<c>` and `Capture.after`. The node classes T2 and T3 made (`Delay`, `DelayWrite`, `EchoNode`, `DreamNode`, `Node.own_size`, `Renderer._refit`) are unchanged.

**Architecture:** In `graph.py`'s data half, `delay`, `resize`, `echo` and `dream` are node kinds both of an old section (`/5`) and of a wired frame (`/6`). A wire into a delay is no dependency, so a loop through one is legal. `sink_loops` counts `FRAME_EDGES` while reading an old section and `HIDDEN_EDGES` in a wired frame (row 393). In the render half (built), `Delay`/`DelayWrite` read and write a half-float ping-pong pair the renderer owns, `EchoNode`/`DreamNode` paint a ring slot or the dream buffer, and `Node.own_size` with `Renderer._refit` carries a picture of its own size into a consumer of another, by cover. Plan 35's `build_graph` (by `_Build`) makes each node only when the wires reach it. It adds each reached delay's write in `_Build.build` and orders it before the internal `Capture`. **Left to build:**
- T4: `ResizeNode`, made by `_Build._make`, with per-instance params `resize[.n].*`.
- T5: GRAPH's last pieces. The canvas takes the render `ResizeNode`, its params become side-panel rows, a node's `said` becomes its first summary line, and a wired frame's plain loop refusal points at a delay.
- T6: the docs.

**Tech Stack:** Python 3.14 (`.python-version`), moderngl, numpy, imgui-bundle (`imgui_node_editor`); pytest via `uv run pytest`.

**Spec:** [`34-feedback.md`](34-feedback.md), rows 353–371. The owner said "build" on 2026-10-24, and none of the rows waits for the owner. On 2026-10-25 the spec's Z, G, Risks, Decisions (359, 370, 371) and Hand checks sections were amended for plan 35. Read it first; this plan does not repeat its reasons. The ledgers `.superpowers/sdd/34-feedback-build/progress.md` (rulings R1–R11) and `.superpowers/sdd/35-free-frame-build/progress.md` (R1–R17) are binding. In this plan a bare **R10** is plan 35's (the schema) and **plan 34 R10** is plan 34's (the echo words).

## Global Constraints

- Work under `hyperspace-python/`. Branch `plan-34-feedback` (PR #236, into `main`). T4–T6 are committed in sequence on it (ledger R1), starting from 6193cb7: 3925 passed, 2 skipped, 741 goldens.
- **No existing golden moves.** All 741 in `tests/golden/frames/frames.json` must match after every task (`uv run pytest tests/test_golden_frames.py -q`, on the M3 Max that recorded them).
  - New goldens come only from T4's two fixtures, `resize-faces` and `resize-crop`. Both are `/6` wired fixtures (`tools/golden_frames.py` `WIRED_FIXTURES`): each state is drawn under the window's mutes (`state_views`), not emulated by switches (`rig_section` leaves a wired fixture as written). 2 × 8 states = 16 goldens, so 757 after T4.
  - Record with `uv run python tools/golden_frames.py --record --only resize-faces,resize-crop`.
- **The signature proof holds.** Every case in `tests/fixtures/frame-signatures.json` matches after every task (`tests/test_graph_frame.py`). None is re-recorded, since no case holds a resize.
- **No file under `hyperspace/library/` is edited.** Proofs are fixtures under `tests/fixtures/presets/`, force-added (`tests/fixtures/` is ignored).
- `apc40.py`, `midi.py`, `bindings.default.json` and the desk are untouched (Dylan's).
- `graph.py` imports no params, preset or media module (`tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`). It may import `view` for `ResizeState` and `RESIZE_*`, as it imports `lookback` for `MAX_ECHOES`.
- **Schema.** New vocabulary saves as `hyperspace.preset/6` (`preset.WIRED_SCHEMA`). `VERSIONS == (2, 3, 4, 5, 6)` is unchanged, and plan 34 adds no schema.
  - A save writes the lowest schema that loses nothing (R10). A wired frame that round-trips through `graphmigrate.unwired` into `/5` words saves as `/5`, and plan 34's four kinds are `/5` words (`graphmigrate.uses_free_words`). So the factory frame plus a resize saves as `/5`.
  - A frame that needs plan 35's vocabulary saves as `/6`.
  - A plan 33 build reads a `/5` section with plan 34's words as unknown and draws its default graph with a note (row 371). It refuses a `/6` file outright (row 385).
- **Ids are the wired frame's** (plan 35 V2): `shape`, `scene` (`geometry`), `hands`, `hands.layer`, `hands.guide`, `backdrop` (`image`, `scene`), `pattern`, `lookback` (`image`, `capture`, `occluder`), `channel.<c>`, `camera`, `output.all`, `output.<n>` (`image`, `hands`, `guide`) and `ground`. T4–T6 name nothing of `frame`, `fx`, `history`, `ghost`, `readout`, `media.<c>`, `eye`, `default_graph`, `_Wiring`, `MAKERS`, `Fx`, `Wired`, a pipeline or `_with_run`. Params keep their ids (`graph.param_prefix`). `resize[.n].*` is new, and its prefix is its node's name.
- The wire ends of `delay`, `resize`, `echo.<k>` and `dream` are as T1 built them (`graph.WIRE_TAKES`, `WIRED_TAKES`, `WIRED_MAKES`, `RESERVED`).
- **Loop edges.** In a wired frame the hidden edges are `graph.HIDDEN_EDGES == (("shape", "pattern"), ("lookback", "scene"))`. `FRAME_EDGES`, `LOOP_FRAME` and `FRAME_SOURCE_REFUSAL` stay, and are read only while an old section is read before it migrates. That read is what keeps a `/5` file's loop from migrating into a wired frame. Nothing in T4–T6 removes them.
- **Refusal words, exactly.** `LOOP_FACES` and `LOOP_BACKDROP` are as built. T5 adds `graph.LOOP_PLAIN = "that makes a loop ({path}): wire it through a delay for last frame's picture"`, a wired frame's words for any other loop (today `"that makes a loop ({path})"`). The old-section words (`"that makes a loop ({path})"`, `LOOP_FRAME`) are unchanged.
- **Node words (`Node.said`), exactly.** Echo, dream and delay are as T2 and T3 built them (`tests/test_graph_delay.py::test_the_delay_nodes_say_what_they_are`, `tests/test_graph_echo.py::test_the_echo_nodes_say_what_they_are`). T4 adds the resize's words:
  - `"{w}×{h} · {fit} · {filter}"`, plus `" · crop {cw:.0%}×{ch:.0%}"` while either crop size is below 1;
  - `"its input reads nothing"` while it reads nothing.
- Match the surrounding code: module docstrings that say what and why, plan/row numbers in comments, `getattr(self, "x", None)` for state a hot-reloaded object may lack, `# noqa: BLE001` on a must-not-kill-the-app except.
- Commits end with the session's attribution lines.

## Review Focus

1. **No pass samples the texture it writes.** (T2, built: `tests/test_graph_delay.py::{test_a_delay_ping_pongs_half_float,test_a_loop_of_effects_never_reads_what_it_writes}`.) T4 adds a loop through a resize: `test_a_loop_through_a_resize_and_a_delay_is_legal`.
2. **Every sink loop is refused at read, and the wire refused is the one closing the loop.** Built: T1 for an old section, and plan 35 for a wired one (`tests/test_graph_wired.py::test_loops_in_a_wired_frame_keep_plan_34s_words`, `tests/test_graph_edit.py::test_a_sink_loop_drag_is_refused_in_words`). T5's `LOOP_PLAIN` changes only the words of a wired frame's other loops.
3. **Nothing before T4 draws differently.** No node before `ResizeNode` takes a new path: the 741 goldens and the signature cases are unchanged after T4 and T5 (every task: the golden suite, `tests/test_graph_frame.py`).
4. **Feedback survives what it should and only that.** (T2, built: `test_a_graph_rebuild_keeps_the_delay`, `test_a_size_change_loses_no_frame`, `test_a_delay_leaving_the_graph_is_released`.) A resize's size step remakes its own target once each way: `test_a_size_step_reallocates_once_each_way`.
5. **A resize's saving is real.** A delay through it holds its size, and an effect after it runs in that size's pool (T4: `test_a_delay_through_a_resize_holds_a_small_buffer`, `test_an_effect_after_a_resize_runs_at_its_size`).
6. **A resize is built only where the wires reach it; its params live while its entry does.** `_Build` makes no `ResizeNode` that reaches no sink. `declare_resizes` follows `spec.resizes` (the entries), reached or not, so an unwired resize keeps its knobs, as an unwired switch keeps its `select` (T4: `test_a_resize_is_built_only_when_reached`, `tests/test_presets.py::test_resize_values_save_and_load_with_the_preset`).

---

## Task order

| Order | Task | Touches |
|---|---|---|
| 1 | T1 vocabulary + loop refusal — **built** (d27f7ef) | `graph.py` (data half), `graphmigrate.py` |
| 2 | T2 the delay — **built** (6a2fa41, 0a3b1e5) | `graph.py`, `render.py`, goldens |
| 3 | T3 echoes and the dream as sources — **built** (72f59c7, 2bdb55a, ce0b0c6) | `graph.py`, `lookback.py`, `render.py`, goldens |
| — | plan 35 T1–T8 — **built** (51ef105..6193cb7) | see `35-free-frame.md` |
| 4 | T4 the resize | `view.py`, `params.py`, `preset.py`, `ui_presets.py`, `graph.py` (`ResizeNode`, `resize_size`, `Frame.resizes`, `_Build._make`), `render.py` (`_draw_frame`), `tools/golden_frames.py`, goldens |
| 5 | T5 GRAPH's last pieces | `graphview.py` (`FRAME_CLASS`, `ResizeNode` stand-in deleted, `MEDIA_MADE`, `OWNERS`, `summary`), `graph.py` (`LOOP_PLAIN`, `loop_words`) |
| 6 | T6 docs | `docs/` |

Sequential. T5's side-panel rows need T4's params, and T5's canvas class swap needs T4's `ResizeNode`. Between T4 and T5 a resize's params show on the canvas as a `group:resize` node, and its node shows no `said` line.

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

- [x] **Step 1: Failing tests** in `tests/test_graph_feedback.py`:
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
- [x] **Step 2:** `uv run pytest tests/test_graph_feedback.py tests/test_graph_edit.py -q` shows the new tests FAIL.
- [x] **Step 3:** implement in `graph.py` and `graphmigrate.py`. `_Wiring._sink` and `_Wiring.aux`'s build-time loop words stay as a backstop for a `Wiring` built by hand.
- [x] **Step 4:** `uv run pytest -q -x` passes, with `tests/test_graph_wires.py`'s explicit-loop words unchanged and `tests/test_graph_free.py::test_the_faces_run_and_a_switch_ends_a_run` still passing (it asserts the run only). The golden suite is unchanged (no render code touched).
- [x] **Step 5:** commit `"Plan 34 T1: delay, resize, echo and dream as words; a loop through the faces, the backdrop or the frame refused at read"`.

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

- [x] **Step 1: Failing tests** in `tests/test_graph_delay.py`. GL tests use the `ctx` fixture and the harness of `tests/test_graph_faces.py` (`_renderer`, `_draw`, `_faces`, `_rgba`, `Still`, `_media`, `section`), imported.
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
- [x] **Step 2:** run, see FAIL.
- [x] **Step 3:** implement.
- [x] **Step 4:** create the two fixtures. Each has a `frame → fx.image` run and `"schema": "hyperspace.preset/5"`, with the values plan 33's fixtures carry.
  - `delay-faces`: nodes `delay`; wires `scene → delay.image`, `delay → shape.faces`.
  - `delay-trails` (as rebuilt under ruling R6: the first graph's opaque scene `over` hid the trail): nodes `delay`, `zoomblur` instance 2, `palette` instance 2, `composite` instance 2 blend `add`; wires `delay → zoomblur.2.image`, `zoomblur.2 → palette.2.image`, `scene → composite.2.under`, `palette.2 → composite.2.over`, `composite.2 → delay.image`, `composite.2 → output.1.image`; `fx.zoomblur.2.on` true, `.mix` 1, `.amount` 0.15, `.glow` 0; `fx.palette.2.on` true, `.mix` 1, `.val_to` 0.6.

  Record `--only delay-faces,delay-trails`. Run the whole golden suite: the 693 are unchanged.
- [x] **Step 5:** `uv run pytest -q -x` passes. Commit `"Plan 34 T2: the delay — last frame's picture, half-float ping-pong, a loop through it drawn"`.

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

- [x] **Step 1: Failing tests** in `tests/test_graph_echo.py`:
  - `test_echo_k_is_the_kth_newest_capture`: three slots written with `Lookback.write_slot(slot, pixels, at=t)` in red, green and blue at t = 1, 2, 3. `echo.1 → output.2.image` shows blue, `echo.2` green and `echo.3` red, each at the output's centre.
  - `test_an_echo_past_the_ring_reads_nothing`: with those three captures, `echo.4 → shape.faces` draws the faces-unwired frame, and `echo.4 → output.2.image` shows the ground. `EchoNode.said == "not held yet: the ring holds 3 of 32"`.
  - `test_the_ring_keeps_capturing_for_an_echo_with_the_look_back_off`: with `dream.on` False and `echo.1 → output.2.image`, `lb.held() == 3` after three frames (gap 0). Output 1's picture equals the same section without the echo wire. With the echo wire removed, `lb.held() == 0` after one frame (`idle`).
  - `test_an_echo_read_this_frame_is_last_frames_capture`: gap 0, a fake channel changing colour each frame on the backdrop, and `echo.1 → output.2.image`. Output 2 at frame n is the backdrop's colour at frame n−1.
  - `test_a_res_change_empties_the_echoes`: after four frames, `dream.res` goes 2 → 3. `echo.1` reads nothing in the next frame, reads again the frame after, and `echo.2` reads only once two commits have landed.
  - `test_the_dream_reads_nothing_until_written`: `dream → output.2.image` shows the ground and `said == "no dream worker: reads nothing"`. After `lb.write_from(pixels, 1)` and a fake `lb.source` set, the output shows `pixels` (centre) and `said` starts with the echo size.
  - `test_echo_words_say_size_and_cadence`: at 960×600 with `dream.res` 2 (256) and gap 0, after two frames `said == "408×256 · every frame · the scene"`. With gap 0.1 it is `"408×256 · every 0.10 s · the scene"`. With `history.holds` `scene+hands` it is `"… · the scene + hands"`.
  - `test_an_echo_on_the_faces_is_fitted`: `echo.1 → shape.faces`, with `Shape.prepare`'s paint into `face_pic` (1024²). `face_pic.tex` centre equals slot centre colour; `r.face_error == ""`.
- [x] **Step 2:** run, see FAIL.
- [x] **Step 3:** implement.
- [x] **Step 4:** create `echo-faces`. It has the run `frame → fx.image`, values `dream.on: false` and `dream.gap: 0`, an `echo` index 3 entry and the wire `echo.3 → shape.faces`. Record `--only echo-faces`. The whole golden suite: everything before is unchanged.
- [x] **Step 5:** `uv run pytest -q -x` passes. Commit `"Plan 34 T3: the look-back's echoes and dream as picture sources; the ring kept while read"`.

---

### Task 4 (T4): The resize — crop, a size of its own, its params per instance

**The design under plan 35 (checked 2026-10-25 against the code at 6193cb7).** Z's design holds. What plan 35 changes is where the node is made and how its goldens are drawn:
- **Its own size** still breaks "the consumer decides the size" on purpose (row 368). Plan 35 left the size path alone: `Frame.at`, `Node.own_size`, the `Effect` own-size path, `PatternNode.size_for`'s own-size head, `DelayWrite.held`, `Renderer._refit` and `_frame_target(dtype=)` are T2's and unchanged.
- **Per-instance params** (`resize[.n].*`) are declared like the switch's `select` (`params.declare_switches`, called by `preset.GraphSection.land`). `GraphSpec.resizes` reads entries in a wired frame too (`graph.DECLARED` holds `"resize"`).
- **The maker is `_Build._make`.** `MAKERS` and `_Wiring` are gone. Today `_make` falls through to dormant `"no resize in this build"` for a reached resize. T4 makes it build a `ResizeNode`.
- **The reach.** `_Build` keeps only wires whose source is reached (`_wired_reach`, from the sinks). So a resize that reaches no output port, no `output.all` port and no `lookback.capture` is never built, and its params still exist (Review Focus 6). A resize reached through a delay is reached only while the delay is: `resize → delay.image` counts once `delay` reaches a sink, because a wired frame's reach follows every wire into a reached node. That fixpoint is plan 34 T1's, kept by `_wired_reach`.
- **The delay.** For `resize → delay.image` the write is `_Build.build`'s `DelayWrite(f"{d.name}(write)", d.name, image=<the ResizeNode>)`, ordered before `Capture` (`Capture.after`). `DelayWrite.held` is `ResizeNode.own_size`, so the delay's pair is made at the resize's size. `delay → resize.image` with `resize → delay.image` is legal: the wire into the delay is `_later`, and `Delay` has no inputs, so `_Build.node`'s recursion ends at the delay.
- **The goldens.** A fixture is a `/6` wired frame, listed in `WIRED_FIXTURES`. `rig_section` leaves it as written, apart from a through state where All outputs lays the hands. `state_views` draws each state under its window's mutes.

**Files:**
- Modify `hyperspace/view.py`: new `ResizeState`, `RESIZE_SIDES`, `RESIZE_ASPECTS`, `RESIZE_FITS`, `RESIZE_FILTERS`; `ViewState.resize`.
- Modify `hyperspace/params.py`: new `RESIZE_GROUP`, `resize_ids`, `is_resize_id`, `_resize_state`, `declare_resizes`; `PERFORMANCE_GROUPS` (`"resize"` after `"switch"`); `build_registry` (`r.resize_state = view.resize`, beside `r.switch_state`).
- Modify `hyperspace/preset.py`:
  - `GraphSection.land` calls `declare_resizes` right after `declare_switches`;
  - `load_doc` sorts `is_resize_id` into `later` beside `is_switch_id`;
  - `NO_MODULE` gains `RESIZE_GROUP`;
  - `Presets.new` leaves out `is_resize_id` values, as it does `is_switch_id`.
- Modify `hyperspace/ui_presets.py`: `OVERVIEW_GROUPS` leaves out `"resize"`, beside `"switch"`.
- Modify `hyperspace/graph.py`: new `ResizeNode`, `resize_size`; `Frame.resizes`; `_Build._make` (kind `"resize"`).
- Modify `hyperspace/render.py`: `_draw_frame` passes `resizes=` to `Frame`, beside `selects=`.
- Modify `tools/golden_frames.py`:
  - `WIRED_FIXTURES` gains `"resize-faces"` and `"resize-crop"`;
  - `MEDIA_FIXTURES` gains `"resize-crop"`;
  - `FIXTURE_PRESETS` gains `"resize-faces"`, beside `"blank-frame"`;
  - the comment above `WIRED_FIXTURES` names both.
- Test: `tests/test_graph_resize.py` (new), `tests/test_presets.py`.
- Create the fixtures `tests/fixtures/presets/resize-faces.json` and `resize-crop.json`, and their goldens.

**Interfaces — Consumes:**
- T1: `ResizeAt`, `GraphSpec.resizes`.
- T2: `_refit`, `own_size`, `said`, `OWN_FIT`, the `Effect` own-size path, `DelayWrite.held`, `_frame_target(dtype=)`, `picture(dtype=)`, `SIZED_KEEP_FRAMES`.
- Plan 33: `declare_switches`, `Frame.selects`.
- Plan 35: `build_graph`, `_Build.node` / `_from` / `_keep` / `g.dormant`, `_wired_reach`, `WIRED_FIXTURES`, `state_views`, `graphmigrate.wired_section`, `graphmigrate.renamed`, `preset.WIRED_SCHEMA`.

**Produces:**
- `view.RESIZE_SIDES = (16, 32, 64, 128, 256, 512, 1024, 2048)`, `RESIZE_ASPECTS = ("input", "square")`, `RESIZE_FITS = ("cover", "contain", "stretch")` (`media_tex.FITS`' order; a test holds them equal) and `RESIZE_FILTERS = ("linear", "nearest")`.
- `view.ResizeState`, a dataclass:
  - `size: int = 4`, an index into `RESIZE_SIDES` (256);
  - `aspect: int = 0`, `fit: int = 0`, `filter: int = 0`;
  - `crop_x: float = 0.5`, `crop_y: float = 0.5`, `crop_w: float = 1.0`, `crop_h: float = 1.0`.
  
  `ViewState.resize: dict[str, ResizeState]` (default_factory dict).
- `params.RESIZE_GROUP = "resize"`, in `PERFORMANCE_GROUPS` after `"switch"`.
- `params.resize_ids(name: str) -> list[str]` returns `[f"{name}.{k}" for k in ("size", "aspect", "fit", "filter", "crop_x", "crop_y", "crop_w", "crop_h")]`.
- `params.is_resize_id(pid) -> bool` is `re.fullmatch(r"resize(?:\.(?:[2-9]|[1-9][0-9]+))?\.(size|aspect|fit|filter|crop_x|crop_y|crop_w|crop_h)", pid)`.
- `params._resize_state(r) -> dict[str, ResizeState]`, as `_switch_state`: `r.resize_state`, else a dict of the registry's own.
- `params.declare_resizes(r: Registry, names: Iterable[str]) -> list[str]`, as `declare_switches`:
  - It returns the ids that appeared or went.
  - For each name it declares the four enums (`size` over `[str(s) for s in RESIZE_SIDES]`, then `aspect`, `fit`, `filter`) and the four continuous params (`crop_x` and `crop_y` 0–1, `crop_w` and `crop_h` 0.01–1).
  - All are group `resize`, modulatable, labelled `"{name} size"` … `"{name} crop h"`.
  - They read and write `_resize_state(r)[name]`, a `ResizeState()` made when first declared and kept while the name stays.
  - The params of names no longer given are removed, and their states dropped.
- `preset.GraphSection.land`: `declare_resizes(reg, [z.name for z in spec.resizes] if spec is not None else [])`.
- `graph.resize_size(side: int, aspect: str, src: tuple[int, int]) -> tuple[int, int]`:
  - `"square"` gives `(side, side)`;
  - `"input"` keeps `src`'s orientation, with its long side `side` and its short side `max(1, round(side * short / long))`.
- `Frame.resizes: dict[str, Any]` (default_factory dict). `_draw_frame` fills it as `dict(getattr(s, "resize", None) or {})`; `Frame.at`'s `replace` carries it.
- `graph.ResizeNode(Node)`: `KIND = "resize"`, `INPUTS = {"image": IMAGE}`, `OUTPUT = IMAGE`, `TIMED = True`. Constructor `ResizeNode(name: str, image: Node | None = None)`.
  - `state(frame)`: `(getattr(frame.root, "resizes", None) or {}).get(self.name) or ResizeState()`.
  - `size_for("image", frame)`: `src.own_size(frame) or frame.root.size`.
  - `own_size(frame)`: `resize_size(RESIZE_SIDES[st.size], RESIZE_ASPECTS[st.aspect], self.size_for("image", frame))`.
  - `reads(frame)`: the input's (False without one).
  - `made(frame) -> Texture | None`: made once a frame (root data `name + "#own"`), None when the input is None or does not `reads`. The steps:
    1. The input as a texture at its size: `src.image(at_in)`, else `picture(at_in, src, dtype="f2")`, where `at_in` is `frame.root` at `size_for("image", frame)`.
    2. The crop as a GL-uv rect: `x0 = crop_x - crop_w / 2`, `y0 = 1 - crop_y - crop_h / 2`, `w = crop_w`, `h = crop_h`.
    3. `mip = filter == "linear" and (crop px w / out w > 2 or crop px h / out h > 2)`.
    4. `r._refit(tex, own_fbo, crop=…, fit=st.fit, filter=…, mip=mip)` into `r._frame_target((self.name + "#own", own), own, dtype="f2")`, under `frame.timed(self.name)`.
  - `paint(frame, dst)`: `r._refit(made, dst, fit=OWN_FIT, filter=RESIZE_FILTERS[st.filter])`, else `dst` cleared to `(0, 0, 0, frame.bg_alpha)`.
  - `image(frame)`: `made` when `own == frame.size`, else that refit once a frame into `r._frame_target(frame.key(self.name + "#fit"), frame.size, dtype="f2")`.
  - `run(frame)`: sets `said` (Global Constraints' words).
- `_Build._make`, kind `"resize"`:
  - With a wire into `<name>.image` reading a node: `self._keep(ResizeNode(name, image=self._from(f"{name}.image")))`.
  - With none: `self.g.dormant[name] = f"{name} is fed by nothing here: wire its input"` and None, as `_effect` does for an effect.

- [ ] **Step 1: Failing tests** in `tests/test_graph_resize.py`. The GL tests use `tests/test_graph_faces.py`'s `ctx`, `_fbo`, `_px`, `_faces`, `_media`, `Still`, `_rgba`. Wired sections come from `tests/test_graph_wired.py::wired`, over the module constant `FACTORY_FRAME` (the six wires of `G.wired(G.Wiring())`, in that order). The module helper `_wired_renderer(ctx, media=None, pairs=(), nodes=(), instances=None, values=None)` is shaped like `test_graph_faces._renderer`, but its wiring is `G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=nodes), effects=…).wiring()`, asserting no notes. Resize values go through `ResizeState`s in the `ViewState`'s `resize`. Every test that wires `output.2` draws two views, because a wire past the window count builds nothing (plan 35 R12).
  - `test_resize_size_model`:
    - `resize_size(256, "input", (1920, 1080)) == (256, 144)`
    - `(1080, 1920)` gives `(144, 256)`
    - `resize_size(16, "input", (1920, 1080)) == (16, 9)`
    - `resize_size(64, "square", (1920, 1080)) == (64, 64)`
    - `resize_size(256, "input", (1024, 1024)) == (256, 256)`
  - `test_the_fits_are_the_media_fits`: `view.RESIZE_FITS == media_tex.FITS`.
  - `test_declare_resizes_comes_and_goes`:
    - `declare_resizes(reg, ["resize", "resize.2"])` declares the 16 ids of `resize_ids`, each group `resize` and modulatable. `reg["resize.2.size"]` has the 8 choices and value index 4, and `reg["resize.crop_w"].value == 1.0`.
    - `declare_resizes(reg, ["resize"])` removes `resize.2.*` and returns those 8 ids.
    - Setting `reg["resize.crop_x"]` writes `reg.resize_state["resize"].crop_x`.
  - `test_a_resize_is_built_only_when_reached` (Review Focus 6):
    - `channel.a → resize.image` alone: `"resize" not in G.reaches(spec)`, and `G.build_graph(views, spec.wiring())` holds no `ResizeNode`.
    - With `resize → output.2.image` added: `isinstance(g.nodes["resize"], G.ResizeNode)`.
    - `resize → output.2.image` with no wire in: no `ResizeNode`, and `g.dormant["resize"] == "resize is fed by nothing here: wire its input"`.
  - `test_a_resize_makes_its_own_size`: `channel.a → resize.image` and `resize → output.2.image`, a 16:9 still, size index 2 (64). After one frame `r._frames` holds `("resize#own", (64, 36))` with `dtype == "f2"`, `"resize" in r._graph.timed`, and `g.nodes["resize"].said == "64×36 · cover · linear"`.
  - `test_an_effect_after_a_resize_runs_at_its_size` (Review Focus 5): `channel.a → resize.image`, `resize → acid.2.image`, `acid.2 → output.2.image`. Then `"acid.2" in r.stats["effects"]` and `(64, 36) in r._pools`, and every `dst` size a spy on `FxChain.run_one` records for `acid.2` is `(64, 36)`.
  - `test_a_delay_through_a_resize_holds_a_small_buffer` (Review Focus 5): `scene → resize.image`, `resize → delay.image`, `delay → shape.faces`, size 64, aspect square. After two frames `r.delay_pair("delay").read[0].size == (64, 64)`, and in `g.order` `delay(write)` comes after `resize` and before `lookback(capture)`.
  - `test_a_loop_through_a_resize_and_a_delay_is_legal` (Review Focus 1): `delay → resize.image`, `resize → delay.image`, `delay → output.2.image`, with a `delay` and a `resize` entry, reads with no notes. Over 4 frames `ctx.error == "GL_NO_ERROR"`, and a spy on `Renderer._refit` never records the delay pair's write side's `glo` as its `tex`.
  - `test_the_crop_takes_the_rect`: a still with quadrants red (top left), green (top right), blue (bottom left) and white (bottom right). `crop_x = crop_y = 0.25` and `crop_w = crop_h = 0.5` into `output.2.image` makes output 2 all red (the centre and the four inset corners).
  - `test_a_crop_past_the_edge_is_transparent`: `crop_x = 0.9` and `crop_w = 0.5` make the made texture's right ~30% of columns transparent black and the left part the still.
  - `test_nearest_keeps_hard_pixels`: a 2×2 checker still at size 16, nearest, into a 64² output gives pixel values only of the two colours. With linear, some pixel lies strictly between them.
  - `test_linear_mipmaps_a_big_reduction`: a 512×512 one-pixel stripe still at size 16, linear, gives a made texture whose every pixel's red is within 0.5 ± 0.1. At nearest every pixel is 0 or 1.
  - `test_a_crop_change_is_a_value_never_a_rebuild`: `crop_w` stepped 1.0 → 0.5 in the `ViewState` between frames 1 and 5. `Renderer._graph_for` returns the same object throughout, and output 2 differs between frames 1 and 5.
  - `test_a_size_step_reallocates_once_each_way` (Review Focus 4): `size` stepped 64 → 128 → 64 → 128 over 4 frames makes exactly two `("resize#own", …)` keys in `_frames`, and none is released within `SIZED_KEEP_FRAMES`.
  - `test_the_resize_says_its_size_fit_filter_and_crop`: with `crop_w = 0.5` and nearest, `said == "64×36 · cover · nearest · crop 50%×100%"`. With no input reading, `said == "its input reads nothing"`.
  - In `tests/test_presets.py`:
    - `test_resize_values_save_and_load_with_the_preset` (Review Focus 6). The preset's section is `graphmigrate.wired_section(graphmigrate.renamed(old), G.read_graph(old))` of `old = {"nodes": [{"kind": "resize", "instance": 2}], "wires": [{"from": "frame", "to": "fx.image"}, {"from": "media.a", "to": "resize.2.image"}]}`, with `resize.2.crop_x = 0.3`. Saved and reloaded into a fresh rig, it gives:
      - `reg["resize.2.crop_x"].value == 0.3` and no unknown-id note;
      - a saved file whose `schema` is `"hyperspace.preset/5"` (R10: it round-trips into `/5` words).
      
      Then a preset without the entry undeclares `resize.2.*`, and one with the entry but no wire still declares it (the reach does not decide).
    - `test_a_new_preset_carries_no_resize_values`: with a resize preset loaded, `Presets.new()` leaves no `resize.*` id in the registry and none in the new preset's values.
- [ ] **Step 2:** `uv run pytest tests/test_graph_resize.py tests/test_presets.py -q` shows the new tests FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** create the fixtures. Each is `"schema": "hyperspace.preset/6"`, with `"graph": {"frame": "wired", …}` and the values plan 35's `channel-out-only.json` carries. Its wires list the resize's wires first, then `FACTORY_FRAME`'s six in order, which is the order `wired_section` writes. Each fixture's `note` says it is a test fixture, never a factory preset.
  - `resize-faces` (the owner's headline):
    - nodes `resize`, `delay`;
    - wires `scene → resize.image`, `resize → delay.image`, `delay → shape.faces`, then the factory frame;
    - values `resize.size: 2` (64), `resize.aspect: 1` (square), `resize.filter: 1` (nearest).
  - `resize-crop` (a media fixture: `"media": {"channels": {"a": ["local:backdrop-still.png"]}}`, as `channel-out-only`'s):
    - nodes `resize` and `acid` instance 2;
    - wires `channel.a → resize.image`, `resize → acid.2.image`, `acid.2 → output.2.image`, then the factory frame;
    - values `resize.size: 3`, `resize.crop_x: 0.35`, `resize.crop_w: 0.5`, `resize.crop_h: 0.5`, `fx.acid.2.on: true`, `fx.acid.2.mix: 1`.

  Add both to `tools/golden_frames.py` (Files) and record `--only resize-faces,resize-crop`: 16 new goldens, 757. Then run the whole golden suite: the 741 are unchanged, and `tests/test_golden_frames.py::test_renaming_moved_no_golden` passes. `tests/test_graph_delay.py::PLAN_34` already names both slugs.
- [ ] **Step 5:** `uv run pytest -q -x` passes, including `tests/test_graph_frame.py` (the signature cases) and `tests/test_graph_areas.py`'s fixture sweeps, which take every fixture with a graph. Commit `"Plan 34 T4: resize — crop and a size of its own, built where the wires reach it; a delay and an effect after it run small"`.

---

### Task 5 (T5): GRAPH's last pieces — the resize on the canvas, its rows, the nodes' words, a loop's way out

**Plan 35 built most of this (checked 2026-10-25 against 6193cb7). It is out of T5's scope:**
- **The picker.** It offers resize, delay, the 32 echoes and the dream, in plan 35's groups: echo and dream under look-back ▸, resize and delay under pictures ▸ (`graphview.picker`, `PICKER_GROUP`; `tests/test_graph_edit.py::test_the_picker_groups_by_primitive`).
- **Adding them.** `render_add` adds each with its words, an echo or the dream once (`picked`, `ONCE`), through `_with_frame`.
- **Deleting them.** `render_drop` deletes any node with its wires (`test_every_frame_node_and_wire_deletes`).
- **Faintness.** `unreached` covers every kind in a wired frame.
- **The delay.** It is one node with its `image` pin: the canvas draws the section, `WIRED_TAKES["delay"]`, and no internal `DelayWrite`.
- **The returns.** `returns` holds every cable into a `Delay`'s `image` and into `lookback.capture`.
- **The areas.** `AREA` by class (`Delay` MEDIA, `EchoNode`/`DreamNode` LOOK-BACK, `ResizeNode` EFFECTS; `tests/test_graph_areas.py::test_the_areas_run_by_primitive`).
- **The pages.** `home_page` sends an echo or the dream to LOOKBACK and gives None for a delay.
- **The side panel** draws for each of the four (`tests/test_graph_legible.py::test_every_nodes_side_panel_draws`).
- **The sink-loop drag.** It is refused in `LOOP_FACES`' words, and lands through a delay (`test_a_sink_loop_drag_is_refused_in_words`).

The original T5's `media_made` heads (a delay, an echo, the dream counted as heads) are dropped. Under plan 35's areas a delay sits in MEDIA and the echoes in LOOK-BACK, both left of EFFECTS, so an effect they feed runs right without them.

**Still missing, and T5's:**
- (a) The canvas still uses its stand-in `graphview.ResizeNode`, so `_built` would skip T4's render node and lose its `said`.
- (b) `MEDIA_MADE` lacks the resize. `channel.a → resize → acid.2` puts `acid.2` in MEDIA (media-made through the resize) and the resize in EFFECTS, so that cable runs back.
- (c) `OWNERS` has no `"resize"`, so `resize[.n].*` would form a `group:resize` node instead of rows on the resize.
- (d) `summary` never shows a node's `said`.
- (e) A wired frame's plain loop says `"that makes a loop ({path})"`, with no way out. Row 359 promised words that point at a delay.

**Files:**
- Modify `hyperspace/graphview.py`:
  - `FRAME_CLASS["resize"]` becomes `rgraph.ResizeNode`, and the class `graphview.ResizeNode` is deleted;
  - `MEDIA_MADE` gains `rgraph.ResizeNode`;
  - new `_resize_owner`; `OWNERS["resize"]`;
  - `summary`.
- Modify `hyperspace/graph.py`: new `LOOP_PLAIN`; `loop_words` (its wired fallback). `_read_wires` already sends a wired frame's `wire_loops` and `sink_loops` refusals through `loop_words`, so it is not touched.
- Test: `tests/test_graph_edit.py`, `tests/test_graph_areas.py`, `tests/test_graph_legible.py`, `tests/test_graphview.py`, `tests/test_graph_wired.py`.

**Interfaces — Consumes:**
- T4: `ResizeNode`, `declare_resizes`, `resize_ids`, `said`.
- Plan 35: `_built`, `FRAME_CLASS`, `_stand_in`, `media_made`, `area_of`, `returns`, `back_wires`, `OWNERS`, `_switch_owner`, `summary`, `REACHES_NOTHING`, `ui_graph.side_groups` / `_param_rows` / `home_page`, `Edit.refusal`, `render_wire`, `loop_words`, `wire_loops`.

**Produces:**
- `graphview.FRAME_CLASS["resize"] is rgraph.ResizeNode`, and `not hasattr(graphview, "ResizeNode")`. `_stand_in("resize")` is `rgraph.ResizeNode("resize")`.
- `graphview.MEDIA_MADE == (rgraph.Effect, rgraph.Composite, rgraph.SwitchNode, rgraph.ResizeNode)`.
- `graphview._resize_owner(pid: str, ctx: _Ctx) -> str | None` returns `pid.rpartition(".")[0] or None` (`resize.2.crop_x` → `resize.2`). `OWNERS["resize"] = _resize_owner`.
- `graphview.summary(n)`: for a render node, `getattr(n.ref, "said", "")`, when not empty, is inserted first. That is after a switch's pick line, and after `REACHES_NOTHING` when the node is faint, so the faint word stays first. Every other kind's lines are unchanged, and the result is still cut to `SUMMARY_LINES`.
- `graph.LOOP_PLAIN` (Global Constraints). `loop_words(path, hops, wired=True)` returns `LOOP_PLAIN.format(path=path)` where it returned `f"that makes a loop ({path})"`. With `wired=False` the result is unchanged (`LOOP_FRAME`), and so are `_read_wires`' old-section words (`"that makes a loop ({path})"`).

- [ ] **Step 1: Failing tests:**
  - `tests/test_graph_wired.py::test_loop_words_in_a_wired_frame`: its third assertion becomes `== G.LOOP_PLAIN.format(path="a → b → a")`. The other two are unchanged.
  - `tests/test_graph_edit.py::test_a_plain_loop_drag_points_at_a_delay`, using the `wired_rig` harness with `lookback → acid.image`, `acid → wobble.image`, `wobble → output.all.image` plus `FRAME0` (the effects declared):
    - `e.refusal("rout:wobble", "rin:acid/aux")` is a string that starts `"wire "`, contains `"that makes a loop ("` and ends `": wire it through a delay for last frame's picture"`. The section is unchanged.
    - Then `e.add_node("delay")`, `graphview.render_wire(e, "rout:wobble", "rin:delay/image")` and `graphview.render_wire(e, "rout:delay", "rin:acid/aux")` each return None.
    - The section then reads with no notes, holding `Wire("delay", "acid.aux")`.
  - `tests/test_graph_areas.py::test_a_resize_sits_by_what_it_is_made_of`:
    - In a wired rig, `channel.a → resize.image`, `resize → acid.2.image`, `acid.2 → output.2.image` puts `render:resize` and `render:acid.2` in MEDIA, and `back_wires(view) == []`.
    - `scene → resize.image` with `resize → output.2.image` puts `render:resize` in EFFECTS, and `back_wires(view) == []`.
    - `graphview._built([G.ResizeNode("resize")])` has the key `"resize"`, and `not hasattr(graphview, "ResizeNode")`.
  - `tests/test_graph_legible.py::test_a_resize_nodes_params_are_rows_in_the_side_panel`, on a rig whose preset declares `resize` (wired `scene → resize.image`, `resize → output.2.image`):
    - `ui_graph.side_groups(panel, view.node("render:resize")) == [("resize", params.resize_ids("resize"))]`, and the view holds no `group:resize` node.
    - `_param_rows` draws 8 rows headless.
    - A row edit (`Panel._row` on `resize.crop_w`) sets the param through the registry in one undo step.
    - `ui_graph.home_page(view.node("render:resize")) is None`.
  - `tests/test_graphview.py::test_a_render_nodes_said_is_its_first_line`:
    - A `G.Delay("delay")` whose `said` is `"last frame's · 64×64 half-float"`, under a `VNode("render:delay", "render", "delay", ref=…)`, gives `summary(n)[0] == said`.
    - The same VNode faint gives `summary(n)[:2] == [graphview.REACHES_NOTHING, said]`.
    - A `G.Composite("composite")` with `said == ""` gives the lines it gives at 6193cb7 (asserted literally).
  - `tests/test_graph_legible.py::test_every_nodes_side_panel_draws` (plan 35's) passes unedited with the render `ResizeNode` as the stand-in.
- [ ] **Step 2:** `uv run pytest tests/test_graph_wired.py tests/test_graph_edit.py tests/test_graph_areas.py tests/test_graph_legible.py tests/test_graphview.py -q` shows the new and changed tests FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `uv run pytest -q -x` passes. `tests/test_graph_wires.py`'s old-section loop words and `tests/test_graph_feedback.py` pass unedited. The golden suite is unchanged (757) and the signature cases match.
- [ ] **Step 5:** commit `"Plan 34 T5: GRAPH draws the render resize, its params as rows, each node's words first; a loop's refusal points at a delay"`.

---

### Task 6 (T6): Docs

**Files:**
- `docs/plans/34-feedback.md`:
  - The status line becomes "built".
  - Add a "What was built" section above the design, as plan 35's: the commits by task (T1 d27f7ef; T2 6a2fa41, 0a3b1e5; T3 72f59c7, 2bdb55a, ce0b0c6; the pause for plan 35; T4; T5) and the ledger's rulings R1–R11, plus T4's and T5's.
  - Add "What no person has verified" (the AD checks) and "Known rough edges". Those include: feedback through the scene is 8-bit; a `/5` save of plan 34's words is read by a plan 33 build with a note; and `FRAME_EDGES` stays for reading old sections.
  - Note "The design, as agreed (2026-10-24), amended 2026-10-25 for plan 35" above the design.
- `docs/plans/35-free-frame.md`: the status paragraph and "What changes for plan 34" say plan 34 resumed and is built (T4–T6, the commits). "741 goldens" stays as plan 35's own count, with "757 with plan 34's T4" added once.
- `docs/plans/README.md`: plan 34's entry becomes "built", with 3925 + T4/T5's tests, 757 goldens (the 741 unmoved, 16 new; plan 34's 40 in all, 24 of them in plan 35's base), rows 353–371 and group AD.
- `docs/ARCHITECTURE.md`, the render-graph section:
  - the delay as z⁻¹ in `build_graph` (`_Build` adds each reached delay's write before `Capture`);
  - `Node.own_size` and `_refit`;
  - `ResizeNode`, built by `_Build._make` only where reached, its params from its entry;
  - `HIDDEN_EDGES` in a wired frame against `FRAME_EDGES` for an old section's read;
  - the module table's `graph.py` row;
  - the golden counts (741 → 757).
- `docs/ENGINEERING.md`:
  - the delay, the echoes and the resize;
  - `resize[.n].*` as a preset's values;
  - both Macs: a `/5` save of plan 34's words loads on a plan 33 build with a note, and a `/6` one is refused.
- `docs/DECISIONS.md`: a "Feedback (plan 34)" section, before "The frame as wires (plan 35)".
- `docs/DECISION-REGISTER.md`:
  - The intro gains rows 353–371's sentence (the owner's "build", 2026-10-24; all (rec) but 353 and 360's owner words).
  - Rows 353–371 go in the table and in full (Answer, Built, Other options, To reverse, Rough edge, Judge it), each "Built" citing its tests, in a "Plan 34 — feedback (rows 353–371)" part before plan 35's. Three rows are written as built:
    - **359.** The loop refusal at read, as T1 built it. Its `FRAME_EDGES` is **superseded in a wired frame by row 393** (`HIDDEN_EDGES`), and stands for reading an old section before it migrates. Its "point at a delay" is `LOOP_FACES` and `LOOP_BACKDROP`, plus `LOOP_PLAIN` (T5) for a wired frame's other loops.
    - **370.** GRAPH as built under row 389: delay in MEDIA, echo and dream in LOOK-BACK, resize in EFFECTS or MEDIA by `media_made`, the cable into a delay a return by design, the resize's params side-panel rows.
    - **371.** The schema, amended by row 385 (R10). Plan 34's words are `/5` words, a wired frame that round-trips saves as `/5`, and one that needs plan 35's vocabulary saves as `/6`.
  - Row 393's "Rough edge" is corrected: `FRAME_EDGES` is kept for an old section's read, not removed by plan 34 T4.
- `docs/plans/11-hand-checks.md`:
  - Write group AD, checks 332–341, before group AE, as the amended spec lists them (new ids: `channel.a`, `lookback`; `delay(write)` on SYSTEM).
  - The header's range sentence says "group AD (332–341) is plan 34's, feedback, on `plan-34-feedback` (PR #236)".
  - AD's intro says how AD and AE relate:
    - both run on the same build;
    - AD starts from a new preset (342) and its scene starter, or the factory frame;
    - 334's drag is GRAPH's, as 343 is;
    - 340 and 351 are both SYSTEM's frame cost, so time them in one sitting;
    - 341 (a `/5` save of a delay, opened on a plan 33 build: a note, its default graph) is the other half of 352 (a `/6` file there: refused).
- `docs/TESTING-GUIDE.md`:
  - New entries L163–L167 for group AD (laptop, the copy; L167 two Macs), in the table and as sections after plan 35's.
  - The fixtures' line: plan 34's five fixtures, 40 goldens.
  - The "Right if" golden count: 757.
- `docs/plans/merge-checklist.md`:
  - #236's row says plan 34 (T1–T6) + plan 35, with hand checks AD (332–341) and AE (342–352);
  - the both-Macs item names the `/5` case (341) beside the `/6` one (352);
  - 741 → 757.

- [ ] **Step 1:** write them. Each row's "Built" cites test names that exist (`uv run pytest --collect-only -q` lists them).
- [ ] **Step 2:** `uv run pytest -q` passes (no doc is test-linked; this run checks nothing broke).
- [ ] **Step 3:** commit `"Plan 34 T6: docs — feedback as built, rows 353–371 (359, 370, 371 as built under plan 35), hand checks group AD"`.
