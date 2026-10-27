# Plan 36 — build plan

Spec: [`36-wysiwyg-graph.md`](36-wysiwyg-graph.md), the authority. Read its
"What is implicit today" map before any task; its file:line references are
to `main` @ 8eb5695 and may have drifted by a few lines. Decisions D1–D5
were accepted by the owner as recommended on 2026-10-26.

Branch `plan-36-build`, which is cut from the quick wins (PR #241). Work
in `hyperspace-python/`. Run tests with `uv run pytest -q …` from there.

## Global constraints

- **The rule.** The graph on GRAPH is the whole truth: what is drawn is
  what is saved is what runs.
  - No code may build, fill in, or infer a node or edge that is not in the
    preset's section or the rig/session's own drawn wires.
  - A canvas drag changes exactly the one wire it lands. It never removes
    or adds another wire, placement or switch as a side effect.
  - No layout runs by itself (the quick wins enforce this already; keep it).
- **Pictures don't move.** No golden PNG under `tests/golden/` may change.
  Every factory preset and fixture must draw exactly what it drew before,
  because it is migrated to the explicit wiring that drew it.
  - Signature fixtures (`tests/fixtures/frame-signatures.json`, the
    `wiredframe` helpers) may be re-recorded only where the picture is
    proven identical by the goldens. Say so in the commit message.
- **Old files.** Code that reads `/4`–`/6` exists only as an explicit,
  one-way migration to the equivalent explicit `/7` section, in
  `graphmigrate`. A `/7` file is never filled in: what it says is all there
  is. Saves write `/7` only (the owner's "no old-schema support").
- **Never touch the owner's Drive library** or `~/Hyperspace`. The
  migration tool is changed and tested on copies; the owner runs it.
- **Style.** Match the surrounding code: docstrings in the repo's voice,
  comments that cite the plan (`# plan 36 T<n>: …`), and no new
  dependencies.
- **Before reporting DONE:** `uv run ruff check` must be clean on the files
  you touched, and the **full suite** must pass (`uv run pytest -q`, about
  5 minutes; the base is 3943 passed, 2 skipped). Report the numbers.
- **Commits.** One or more commits per task, each message ending with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01LGSeU3A25ZzroofFN6pu25
  ```
  Never push, merge or rebase. Never dispatch subagents.

## Task 1: outputs show only their own wires; All outputs is a drawn bus (spec W1, D1)

Goal: fix the install's "rewire the output and something else gets
rerouted". After this task, wiring X into `output.1.image` changes that
one port and nothing else, and everything that reaches a window is a cable
on the canvas.

1. Remove the per-port fallback from window ports to `output.all`
   (graph.py around 5706–5715).
2. Make **All outputs** a bus. The rig/session owns one wire per
   (window N, port) `output.all.<port> → output.N.<port>` for `image`,
   `hands` and `guide`:
   - present by default for every window;
   - drawn on GRAPH as ordinary cables;
   - deletable and re-addable there, with the change persisted where the
     session's/show's own wiring lives (find it: `Shows`, the window
     nodes' home — `graphview.home`).
   A preset wire into `output.N.<port>` takes that port. The bus cable
   into that port is then not drawn and not used while the preset wire
   is there. One wire into a port, always visible.
3. Delete the implicit output behaviours the spec lists:
   - `Output.settle` / `Shown.fallback` / `Shown.bent` swapping ends;
   - `_Wiring._put`'s rules (a picture wire drops the guide, "SH"→"S")
     from every live edit path (`set_through`, `set_picture`'s
     `_drop_through`);
   - `render_wire._unplace` removing placements as a side effect.
   If an OUTPUT-page control (picture / through / hands) did those as
   one user action, it now edits only the wires it names. Say in the
   report what each control does now.
4. Tests. Write the install repro as a test: on the factory
   `party-trip` frame, wire `scene` into `output.1.image`. Assert that
   the section's other wires, every other port's input, and output 2 are
   unchanged, and that output 1's hands/guide are exactly the drawn bus
   cables. Also test: cutting a bus cable persists in the session and
   the window shows nothing on that port.
5. Goldens unmoved. The rig default (bus cables present) must reproduce
   today's pictures.

## Task 2: every hidden edge becomes a port and a cable (spec W2)

Goal: each row of the spec's W2 table becomes a real port plus a drawn,
saved, deletable wire. An unwired port means what the table says, never
a default.

| from (hidden) | to (drawn) | unwired |
|---|---|---|
| shape reads `pattern` by name | `pattern → shape.faces` | plain faces |
| cover built from the scene | `scene.cover → lookback.occluder` (mask) | no occlusion |
| hands.layer / guide read `hands` by name | `hands → hands.layer.hands`, `hands → hands.guide.hands` | empty |
| clouds injected into the scene | `cloud.N → scene.geometry` (several allowed) | no cloud |
| `depth` auto-wired; `blend` global | `scene.depth → composite.depth`; `blend` a param per composite | no depth |

- Delete `HIDDEN_EDGES`, `IMPLICIT_EDGES` and `FRAME_EDGES` (and their
  loop-word special cases) once nothing reads them. Loop detection then
  runs over drawn wires only.
- Migration (`graphmigrate`): every `/4`–`/6` section gains the explicit
  wires its hidden edges stood for, so the pictures don't move. This
  includes the factory frame `frame_wires` / `wired_of` still makes for a
  section-less old file; Task 3 removes that path for `/7`.
- The cloud wire is the rig's (a cloud device is the rig's), drawn like
  the Task 1 bus cables and persisted the same way.
- Tests per row:
  - unwired behaves as the table says;
  - wired reproduces today;
  - migration adds the wire;
  - the canvas draws it (`graphview` view has the cable).
- Goldens unmoved.

## Task 3: nothing loads that isn't in the file; schema `/7` (spec W3, D5)

1. **`/7` is the schema** (`WIRED_SCHEMA`). Loading a `/7` file never
   adds anything. A `/7` with no `graph` section, or an empty one, loads
   as an empty graph (black) and the preset strip says so. `wired()`,
   `Wiring()` as a fallback, `frame_wires`/`wired_of` on any `/7` path,
   "the default placement", `Renderer.wiring = Wiring()` as a picture
   source, and `GraphSection` with no spec drawing the factory frame are
   all gone.
   - A refused wire in a `/7` file is dropped, with a note. It is not
     replaced by a default.
2. **Effects exist only where the section names them.** Instance 1 of
   every file stops existing implicitly (`set_instances`, preset.py
   around 402). The FX page lists the section's effects. At migration,
   values for effects that aren't in the section are dropped.
3. **`into` / `after` placements become the wires they stand for** at
   migration. `/7` doesn't read those keys, and `_place`/`_place_one`
   leave the build.
4. **Hands entries and `laid` are always written.**
5. **One-way migration** `/4`–`/6` → `/7` in `graphmigrate`, used on load
   of an old file (with a note) and by `tools/migrate_library.py`.
   - Rewrite all 25 factory presets in `hyperspace/library/presets/` as
     `/7` with their explicit graphs, using the tool.
   - Rewrite test fixtures only where a test is about `/7` behaviour.
     Old-schema fixtures stay as migration inputs.
   - Update `migrate_library.py` for `/7` and test it on a temp copy
     (a backup is made, as it was for `/6`).
6. Tests:
   - section-less `/7` loads black;
   - an old section-less preset migrates to today's frame;
   - an effect not in a `/7` section is absent from the build and the FX
     page;
   - every factory preset round-trips (load → save → identical bytes);
   - goldens unmoved.

## Task 4: look-back and dream, two nodes (spec W4, D2, D3)

1. **`lookback`**: picture in → trail out.
   - Port `image` (what it records) plus optional `occluder` (mask).
   - Output: the age-weighted trail as a premultiplied picture with alpha
     (echo_mix, fade, darken, contrast). It is not laid over anything
     (D3).
   - Outputs `echo.k` are frames of this node's own ring.
   - Each instance (`lookback`, `lookback.2` …) has its own ring (echoes,
     gap, res).
   - Nothing about dream lives in it. Split `Lookback` (lookback.py) so
     the ring/composite and the dream buffer are separate objects.
2. **`dream`**: picture in → dreamed picture out.
   - Port `image`. It submits its input to the worker at its own cadence,
     pulls `D` itself (no longer through `History.run`), and outputs `D`
     with its chroma (hue, sat, tint).
   - **`dream.on` off passes `image` through unchanged and stops
     submitting**, so the worker idles.
   - One live dream at a time (D2): a second `dream` node is refused in
     words when wired.
   - It works with no lookback anywhere in the graph.
3. **Params.** Keep the param ids where they still mean the same thing.
   Where a param moves meaning (`dream.on` used to gate the whole
   look-back; `dream.mix` was the D layer's weight in the look-back
   composite), migrate the values. Record each change in the report.
4. **Migration.** An old preset's look-back becomes:
   - `scene → lookback → composite(over: scene/its old image input) → …`
     where the old look-back sat;
   - plus `lookback → dream → (into the composite)` when its dream was
     live (`dream.mix > 0` and the worker enabled in config is not a
     preset fact, so key on `dream.mix > 0`).
   - The composite reproduces the old one-shader blend closely enough
     that **the goldens are unmoved**. If an exact match is impossible
     for some preset, stop and report BLOCKED with the numbers; do not
     re-record goldens.
5. **Plan 34's `echo.k`/`dream` source nodes** fold into the two nodes
   above (an `echo.k` is a lookback output). Migrate their wires.
6. Tests:
   - tracers with dream off: worker gets no submissions;
   - dream alone on a channel picture, with no lookback, refreshes;
   - a second dream is refused;
   - two lookbacks keep separate rings;
   - migration of a dream preset;
   - goldens unmoved.

## Task 5: a new preset that starts somewhere; starters (spec W5)

1. PRESET strip **new**: the section is `shape → scene → output.all.image`.
   With the rig's bus cables, a shape is on screen. Its three nodes are
   placed left to right in the preset's layout map, at the canvas point
   currently in view (the page's `pan`), not left to auto layout.
2. The picker (right-click background) gets a **starters** submenu. Each
   starter adds a pre-wired group at the right-click point, laid out left
   to right, as one undo step. Every node and cable is ordinary
   afterwards. The starters:
   - **scene chain**: shape → scene → output.all.image;
   - **tracers**: lookback (fed by the cable/picture the user picks, or
     by `scene` if present) → composite over that picture;
   - **tracers + dream**: as tracers, with lookback → dream → composite;
   - **dream on a picture**: dream → composite;
   - **channel to backdrop**: channel.a → backdrop.image.
   A starter whose input is ambiguous wires what it can and leaves the
   rest visibly unwired. It never guesses silently.
3. Tests: new → section equals the three wires and the layout map has
   three positions; each starter adds exactly its nodes and wires, at the
   point, as one undo step.

## Task 6: "preset only" view (spec W6, D4)

- A head chip **preset only** on GRAPH, **on by default** for every
  preset (D4).
- When on, the canvas draws only:
  - the preset section's nodes;
  - nodes with a cable to one of them;
  - the rig's window/output nodes those reach (with their bus cables).
  Controllers, modulation, macros and binding cables not wired to a
  section node are hidden. One click turns it off.
- The head line says how many nodes are hidden.
- Tests: on a factory preset, the drawn set is exactly that. Off shows
  today's canvas. The state survives a preset load.

## Task 7: docs

- `docs/plans/36-wysiwyg-graph.md`: status **built** with test and golden
  numbers. Add a "What changed in the build" section listing every ruling
  from `.superpowers/sdd/…/progress.md` (the controller will hand you the
  list).
- `docs/plans/README.md`: update the plan 36 entry.
- `docs/DECISIONS.md`: a section "The WYSIWYG graph" covering the rule,
  the bus, the hidden edges as cables, `/7`, and the two nodes.
- `docs/DECISION-REGISTER.md`: rows for D1–D5 (answered 2026-10-26 by the
  owner, as recommended) and for each ruling.
- `docs/plans/11-hand-checks.md`: a new group AF of hand checks, numbered
  after the last one there. Include:
  - the quick wins' five (insert spawn, no snap, output behind, scale,
    trackpad pan/⌘ zoom);
  - rewire output 1 changes nothing else;
  - cut a bus cable;
  - the new preset shows a shape;
  - each starter;
  - tracers without dream (worker idle);
  - dream alone;
  - preset only;
  - run `tools/migrate_library.py` on the Drive library (with the backup)
    on both Macs.
- `docs/ARCHITECTURE.md`: update wherever it describes the default graph,
  the hidden edges, or the look-back/dream coupling.
