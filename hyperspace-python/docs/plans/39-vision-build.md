# Plan 39 — build plan

Spec: [`39-vision.md`](39-vision.md), the authority; the spike
[`assets/39-vision/findings.md`](assets/39-vision/findings.md) has the
file:line map of what exists (as of `main` @ f2351a0; re-find by symbol).
Every decision is answered (spec table). Branch `plan-39-vision`, cut from
`main` (see the orchestrator prompt for the base and the integration branch).
Work in `hyperspace-python/`; tests `uv run pytest -q` (fast tier) and
`uv run pytest -q --all` (full, before DONE).

## Global constraints

- **The rule.** The graph on GRAPH is the whole truth (plan 36): every input
  of every new node is a drawn wire; nothing is filled in; no hidden edge.
  The CPU-frame shortcut in `segment` changes where the worker reads, never
  what is wired.
- **Alpha is not a mask.** A `mask` is one channel, 0 or 1 but at a feathered
  edge; it travels only on `mask` wires or through the promotion of W1. No
  node of this plan writes a mask into a picture's alpha except `cut` and
  `segment.fg`/`.bg`, whose job that is.
- **Pictures don't move.** No golden PNG under `tests/golden/` changes; new
  fixtures add goldens. The frame-signature fixture gains cases, loses none.
- **Boundaries.** `graph.py` keeps importing the render stack only
  (`test_graph_imports_only_the_render_stack_and_names_no_write`); the new
  `masks.py` (GLSL passes) imports `moderngl`, `numpy`, `glsl` only; the new
  `segment.py` (the worker) is imported by `app.py` behind the graph's need,
  never by `graph.py` (reach it duck-typed through the renderer, as the dream
  worker is: `Renderer.segmenter(name)`); `Vision`, `objc`'s Vision wrapper
  and `torch` are imported inside the worker's first job only
  (`test_app_boundary.py` extended).
- **Files other streams own** (orchestrator prompt): do not touch
  `hold.py`, `undo.py`, `hotreload.py`, `app.py`'s `_draw_render` (plan 38);
  `ui_graph._node` and `graphview.summary`'s body, `patterns.glsl`,
  `patterns.py`, `ui_patterns.py` (plan 37). In `graphview.py` add only table
  entries (`LABELS`, `HOVERS`, `OWNERS`, `PICKER_GROUP`, `picker`,
  `FRAME_CLASS`, `_stand_in`, `STARTERS`); in `ui_graph.py` only `COLOURS`
  if a promoted cable needs a style. In `render.py` add only
  `segmenter()`, `motion_pair()` and the hook that hands `masks.py` a
  `_frame_target`; the passes live in `masks.py`.
- **Style.** The repo's voice in docstrings; comments cite the plan
  (`# plan 39 T3: …`); dependencies: `pyobjc-framework-vision` only.
- **Before DONE:** `uv run ruff check` clean on touched files; the full suite
  green (base: main's count at the cut, report it); goldens
  `uv run pytest -q tests/test_golden_frames.py` green with the new pictures
  recorded and listed.
- **Commits** end with the attribution lines the session gives. Never push
  to main, merge or rebase.

## T0 — `edges.glsl` (spec W5)

Goal: the quick win, alone, first.

1. `hyperspace/shaders/fx/edges.glsl`: `@label Edges`, `@blend mix`; Sobel
   on `src` luma (8 taps at `1/u_res`), `u_threshold` (@param 0 1 0.2),
   `u_glow` (@param 0 4 0), `u_colour` (@param choice [white|source|direction]
   0). Premultiplied out: white × magnitude; or `src.rgb × magnitude`; or
   hue by `atan(gy, gx)`.
2. Fixture `tests/fixtures/presets/edges-scene.json` (`scene → edges →
   output.all.image`) and its goldens; a test that the file declares its
   three params and that a flat picture makes black.
3. Commit as its own PR-able commit; the orchestrator may land it ahead.

## T1 — alpha is honest (spec "Risks")

1. `tests/test_render.py`: a scene with one half-transparent face laid into
   a `composite.over` over a white backdrop on an opaque window, drawn with
   `view.cut_through` on and off: the two pictures are equal, and the
   composite's result equals `face + white × (1 − face.a)` within a tolerance
   at the face's centre.
2. If it fails: in `render.draw_scene`, the cut-through branch applies only
   when the *window* is see-through (`View.bg_alpha < 1`), not when a scene
   node's ground is 0; keep `test_cut_through_still_cuts_in_overlay_mode`
   and `..._never_cuts_an_opaque_ground` green. Note it in the register row.

## T2 — the mask wire and `matte` (spec W1, W2)

1. `graph.py`: the promotion in `_wired_error` (a `MASK` maker into an
   `IMAGE` port is accepted); `Node.picture_of_mask` — a mask node asked for
   a picture by a consumer paints white where it passes (`masks.PROMOTE_FS`)
   into a `_frame_target` at the consumer's size, fitted by cover like an
   own-sized node. The refusal words for picture → mask name `matte`.
2. `MatteAt` + reader + `NODE_KINDS["matte"]`, `DECLARED`, `RESERVED`,
   `_wired_kind` regex, `WIRED_MAKES["matte"] = MASK`,
   `WIRED_TAKES["matte"] = {"image": IMAGE}`, `_Build._make` branch,
   `MatteNode` (own size: its input's; `paint`/`image` through
   `masks.matte(...)`: one pass, then the feather's two separable passes when
   `feather > 0`).
3. `masks.py`: the GLSL (`MATTE_FS`: luma / alpha / chroma with key, soft,
   invert; `BLUR_FS` separable, one channel; `PROMOTE_FS`; `CUT_FS` for T3)
   and a `MaskPasses` object the renderer holds (programs, a fullscreen
   triangle), given `_frame_target` by the renderer.
4. `params.declare_mattes(r, names)` on `declare_resizes`' pattern, group
   `matte`, state in `ViewState.mattes`, read as `Frame.mattes`; landing in
   `preset.GraphSection` beside the resizes.
5. `graphview.py` table entries; `ui_graph.COLOURS` unchanged (purple).
6. Tests: `tests/test_graph_masks.py` — type rules (mask into picture
   accepted, picture into mask refused with the matte words, cover →
   lookback.cover unchanged), the matte's three sources on a synthetic
   picture, feather widens, invert; `mask-as-picture` fixture + goldens.

## T3 — `cut` (spec W3)

1. `CutAt`, reader, tables as T2; `CutNode` with `INPUTS {"image": IMAGE,
   "mask": MASK}`, OUTPUT IMAGE, own size its picture's; no mask → paints its
   picture through (`src.paint`); `masks.cut(...)` one pass (`CUT_FS`:
   `m = texture(mask)`, `m = invert ? 1 − m : m`, `c = src × mix(1, m,
   amount)`), the mask sampled bilinearly, flagged for the flip if it came
   from the CPU path (T4).
2. `params.declare_cuts` (`invert`, `amount`), group `cut`.
3. Fixture `cut-out` (a media still → `matte` → `cut` of a scene branch →
   `composite.over`, scene under) + goldens; tests: the hole is transparent,
   the under shows through, `amount 0.5` dims, `invert` keeps the hole.

## T4 — `segment`: the node and the worker (spec W4)

1. `segment.py`: `SegmentWorker(backend, quality, …)` on `dream.DreamWorker`'s
   shape — thread, condition, one pending job, three rotating input slots,
   lock-free `latest() -> (mask: np.ndarray HxW uint8, index, size)`, errors
   to `.error`, `close()` joins within 1 s. Backends as classes with
   `open()`, `run(frame_rgba) -> mask`, `close()`:
   - `VisionBackend` (pyobjc): the request built once per quality level;
     a `CGImage` from the frame's bytes; the result pixel buffer locked, read,
     unlocked. Import inside `open()`.
   - `TorchBackend`: the LR-ASPP model, fp16 on MPS if there, the normalise
     and softmax of the spike's script; weights as the dream finds them.
   - `pick_backend(cfg)`: `[segment] backend` auto / vision / torch; a missing
     library is a reason string the node says, never an exception past
     `open()`.
2. `graph.py`: `SegmentAt` (instance, no mode in the entry — the mode is a
   param), reader, tables; pins `segment.fg` (IMAGE), `segment.bg` (IMAGE),
   `segment.mask` (MASK) in `PINS` as `scene.depth` is; `SegmentNode.run`:
   pull the newest result into the node's mask texture (`_frame_target`
   `name#mask`, one channel, keyed by result index), then submit — through
   the shortcut if `inputs["image"]` is a `MediaNode` whose channel's newest
   `MediaFrame` has pixels and its `frame` id moved, else the dream's
   downsample + `read_into`; `fg`/`bg` painted by `masks.cut` with the mask /
   inverted; `said` as the spec. `mode == motion`: no worker — `masks.motion`
   updates the renderer's `motion_pair(name)` and writes the mask texture on
   the frame thread.
3. `render.py`: `segmenter(name) -> SegmentWorker | None` (made on first
   need from `Renderer.segment_cfg`, kept across rebuilds by name, closed
   when the node has been gone `SIZED_KEEP_FRAMES`, all closed in
   `Renderer.close`); `motion_pair(name)` on `delay_pair`'s pattern.
   `app.py`: `renderer.segment_cfg = config["segment"]` beside the dream's;
   workers on the close list.
4. `params.declare_segments` (`mode`, `quality`, `feather`, `smooth`, `on`,
   `sense`, `learn`), group `segment`.
5. `pyproject.toml`: `pyobjc-framework-vision>=12.2 ; sys_platform ==
   'darwin'` with a comment in the file's voice; `uv lock`.
6. Tests: `tests/test_segment.py` — the worker with a fake backend (latest
   wins, drops counted, an error said, close joins); `tests/test_graph_segment.py`
   — the node with a fake worker: passes through before the first result,
   `fg`/`bg`/`mask` from a known matte, the shortcut taken for a channel
   with pixels and the readback for one without (a count on each path),
   orientation (an asymmetric frame's mask lands on the right rows), `on`
   off idles the worker, a removed node closes it; `segment-motion` fixture
   + goldens; `@pytest.mark.live`-style marked tests that run each real
   backend once on a synthetic frame and assert shape and range;
   `test_app_boundary.py` extended with `Vision`.

## T5 — GRAPH and the pages (spec W6)

1. `graphview.py`: `PICKER_GROUP` MEDIA for `segment`, a new MASKS group for
   `matte` and `cut`; `LABELS`/`HOVERS` in the repo's words; `OWNERS` so each
   node's params are its ports; the **cut-out** starter in `STARTERS`.
2. The node's body line (`said`) through the existing `summary` hook — no
   change to how a node is drawn (plan 37's).
3. `ui_fx.py` / FX page: `edges` appears as any effect file does (nothing to
   do; check).
4. Tests: the picker lists the three; the starter wires what the spec says
   and refuses nothing; a `/7` round trip of each entry.

## T6 — docs

1. `docs/plans/39-vision.md` status → built, with what changed in the
   build; the as-built list in `README.md`'s line.
2. `ARCHITECTURE.md`: the port types paragraph (mask's meaning, the
   promotion), the node table (`segment`, `matte`, `cut`, `masks.py`,
   `segment.py` rows), the thread table (`segment-<name>` workers), the
   boundaries (what imports Vision/torch).
3. `DECISIONS.md`: "Masks are their own wire" with the owner's two
   sentences; `DECISION-REGISTER.md`: the rows the orchestrator assigned
   (the eight decisions and the build's rulings), each with Built / Other
   options / To reverse / Rough edge / Judge it.
4. `11-hand-checks.md`: group AJ from the spec, numbered as assigned.
5. `CHECKPOINT.md` and `TESTING-GUIDE.md` lines for the new fixtures and
   the marked backend tests.
