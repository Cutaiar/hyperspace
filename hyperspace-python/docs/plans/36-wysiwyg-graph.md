# Plan 36 — the WYSIWYG graph: no default graph, no hidden edges; look-back and dream as two nodes

**Status: proposed (2026-10-26)**, from the owner's notes after the
2026-10-25 install, agreed with Dylan. Not built. Plan 37 is the faces
(their shaders consolidated, faces as a target like any other) and the
nodes-as-pictures visual language; the quick wins from the same notes
(insert spawn, no automatic layout, the output behind the canvas, bigger
canvas, two-finger pan) are on their own PR.

The owner's rule, verbatim in spirit: **the graph on GRAPH is the whole
truth.** What is drawn is what is saved is what runs. There is no default
graph that fills in what a preset leaves out, no edge that is not a drawn
cable, no rewiring the user did not do, and no layout that runs by
itself. A node editor whose picture can't be trusted is worse than none.

## What is implicit today (the map, 2026-10-26)

Plan 35 made the frame wires, but defaults still enter four ways. File
and line references are `main` @ 8eb5695.

1. **Load-time fill-in.** `graphmigrate.migrate` (324–453) gives any
   section that is not wired — *including no section* — the factory run
   (`wired_of` / `frame_wires`, 779–832, 1030–1038: `shape→scene`,
   `scene→lookback.image`, `lookback→output.all.image`,
   `hands.layer→output.all.hands`/`guide`, `scene→lookback.capture`).
   **All 25 factory presets have no `graph` key**, so every one loads this
   way. `Renderer.wiring = Wiring()` (render.py 1044), `GraphSection` with
   no spec (preset.py 337, 390), a save with no section (1111–1116), GRAPH
   edits with no spec (graphview 3478) and the OUTPUT page's words all
   fall back to the same frame.
2. **Hidden edges** — real at build, never drawn:
   - the shape reads `pattern` by name (graph.py 2892–2898); unwired
     `shape.faces` means "the pattern";
   - the look-back's cover is built from the scene whenever both are
     reached (5565–5569);
   - `hands.layer` and `hands.guide` draw the hands node by name
     (5537–5546);
   - point clouds are injected into the scene whenever a cloud device is
     listed (5468, 5549);
   - `depth` is wired to the scene when `blend == "depth"`, and `blend`
     is one global over every output (5629–5633, 5730–5733).
3. **Outputs fall back port by port.** A window's `image`, `hands` and
   `guide` each take their own wire, else **All outputs**' (5706–5715).
   No cable is drawn for the inheritance. *This is the likeliest cause of
   the install's "rewire the output and something else gets routed to
   it":* wire X into `output.1.image` and output 1's `hands`/`guide` still
   come from All outputs, so the hands layer and guide stay laid over X.
   Also implicit: `Output.settle` swaps an un-"bent" end for
   `Shown.fallback` every frame (4887–4911); `_Wiring._put` drops the
   guide when a picture is wired and turns "SH" into "S"
   (graphmigrate 1101–1117, also from `set_through`, graphview 4371);
   `render_wire._unplace` and `set_picture` remove other wires and
   placements as a side effect (graphview 3690–3701, 4290–4357).
4. **Things that exist without being in the section.** Instance 1 of
   every effect file always exists (`set_instances`, preset.py 402); the
   hands node defaults (`HandsAt`, graph.py 237) and `laid = "over"` are
   omitted from saves; D1's `into`/`after` placements are shorthand that
   `_place` turns into edges at build (5275–5351), with "the default
   placement" as the fallback for a refused one.

**Look-back and dream are one object.** `Lookback` (lookback.py 529–948)
holds the echo ring (32 slots) *and* the dream buffer `D`; `Capture.run`
both records an echo and submits it to the dream worker; one shader
(`Lookback.composite`, 698–744) lays echoes + `D` over the image.
`History.run` is the only caller of `pull()`, so a `dream` node with no
look-back never refreshes. "Tracers without dream" exists only as
`dream.mix 0` — the worker still runs on every capture. `dream.on` gates
the whole look-back. Plan 34's `echo.k` and `dream` nodes read the same
ring; `delay` is a separate z⁻¹ and is the shape we want.

## What this plan does

### W1 — outputs show exactly their own wires (fixes the install's #3)

- An output window's ports show **only what is wired into them**. Nothing
  is inherited port by port; `Output.settle`'s fallback, `_Wiring._put`'s
  rules, and every "wire this, so also drop that" in `render_wire` /
  `set_picture` / `set_through` go. A drag changes the one wire it lands.
- **All outputs** stays as a node (the laptop-vs-rig problem it solves is
  real) but becomes an explicit **bus**: its picture reaches a window only
  through a drawn cable `output.all → output.N.<port>`. Those cables are
  the rig's (the session's, like a window node), drawn on the canvas, and
  can be cut. The rig ships with them wired, so a preset wired into All
  outputs still shows on every window. **Decision D1.**

### W2 — every hidden edge becomes a port and a cable

| today (hidden) | after (drawn) | unwired means |
|---|---|---|
| shape reads `pattern` by name | `pattern → shape.faces` | plain faces (no pattern) |
| cover built from the scene | `scene.cover → lookback.occluder` (a mask port) | no occlusion |
| hands.layer / guide read `hands` by name | `hands → hands.layer.hands`, `hands → hands.guide.hands` | empty layer |
| clouds injected into the scene | `cloud.N → scene.geometry` (the geometry port takes several) | no cloud |
| `depth` auto-wired, `blend` global | `scene.depth → composite.depth`; `blend` a param of each composite | no depth test |

### W3 — nothing loads that isn't in the file

- `migrate`'s fill-in, `wired()`, `Wiring()` as a fallback and "the
  default placement" are deleted. A preset with no `graph` section loads
  **empty** (black) and says so on the preset strip.
- Effect instances exist only where the section names them; the FX page
  lists the section's effects. Params of an effect that isn't there are
  dropped at migrate.
- `into`/`after` are rewritten as the wires they stand for; the keys stop
  being read.
- Hands entries and `laid` are always written.
- **Schema `/7`.** `tools/migrate_library.py` rewrites the 25 factory
  presets and the Drive library once, each to the explicit graph it drew
  under `/6` — proved node for node (`graph.signature`, as plan 35 did)
  and by every golden staying put. No `/6` reader is kept (the owner's
  "no old-schema support": both Macs update together).

### W4 — look-back and dream, two nodes (the install's #7)

- **`lookback`** — *picture in → its trail out.* It records whatever is
  wired into `image` into its own ring (`echoes`, `gap`, `res`) and
  outputs the age-weighted trail (`echo_mix`, `fade`, `darken`,
  `contrast`) as a premultiplied picture with alpha. Optional `occluder`
  mask. `echo.k` outputs stay (frame k of *this* node's ring). Several
  look-backs, each with its own ring. No dream inside it.
- **`dream`** — *picture in → dreamed picture out.* It submits its input
  to the worker at its own cadence and outputs `D` with its chroma
  (`hue`, `sat`, `tint`). Params are the worker's (`steps`, `step`, `k`,
  `jitter`, `octaves`, `layer`, `mask_decay`). **`dream.on` off passes the
  input through** — the toggle the owner asked for — and stops the worker
  so it costs nothing. One live dream at a time (one worker, one GPU);
  a second is refused in words. **Decision D2.**
- Laying either over the live picture is a **composite**, drawn, like
  everything else. **Decision D3** is whether the look-back also offers
  "trail over input" as one output, to save the composite in the common
  case.
- **Today's look, three nodes:** `scene → lookback → dream → composite
  (over scene) → output`. Tracers alone: drop the dream (or turn it off).
  Dream alone on any picture: `X → dream → composite`. The picker offers
  each as a **starter** — a pre-wired group, put where you right-clicked,
  every node and cable visible and editable afterwards.
- Old presets migrate to exactly that chain (dream included when its
  `mix > 0`), proved by goldens.

### W5 — a new preset that starts somewhere (the install's #6a)

**new** makes `shape → scene → output.all.image` (with the rig's bus
cables), laid out left to right where you are looking — not black. The
picker's **starters** section has: scene chain, tracers, tracers + dream,
dream on a picture, a channel to the backdrop.

### W6 — see just the preset (the install's #6b)

A **preset only** chip on the head hides every node that isn't in the
preset's section, plus anything not wired to one of them (the ~159 rig
binding cables and their controllers, per the 2026-10-24 finding).
It's on by default for a new preset. **Decision D4.**

## Decisions for the owner

| # | question | recommendation |
|---|---|---|
| D1 | All outputs: keep it as an explicit bus with drawn rig cables, or delete it and wire each window? | **Bus.** One preset still works on the laptop and the rig, and every cable is visible. |
| D2 | One live dream at a time, or several sharing the worker? | **One.** The worker is one GPU job. A second is refused in words; several would split the frame rate between them. |
| D3 | Look-back outputs its trail only (needs a composite), or also "trail over input"? | **Trail only.** WYSIWYG; the starter adds the composite for you. |
| D4 | "Preset only" on by default for every preset, or only for new ones? | **Every preset**, with rig/controller nodes one click away. |
| D5 | Migrate factory presets and the Drive library to `/7` in one go (as `/6` was)? | **Yes**, with the same backup and both Macs updated together. |

## Order of work

| task | what | proves |
|---|---|---|
| T1 | W1: outputs show only their own wires; the bus | rewire `output.1.image`: nothing else changes (test of the install's repro) |
| T2 | W2: hidden edges → ports and cables | `graph.signature` of all 25 factory presets unchanged, every edge in the wire list |
| T3 | W3: no fill-in, `/7`, `migrate_library` | goldens unmoved; a section-less preset loads black |
| T4 | W4: look-back and dream split | tracers with dream off: worker idle; old dream presets' goldens unmoved |
| T5 | W5: new preset and starters | new → a shape on screen |
| T6 | W6: preset only | factory preset: only its section's nodes drawn |
| T7 | docs: ARCHITECTURE, DECISIONS, register rows, hand checks | — |

T1 can land on its own and fixes the most visible bug. T2–T3 are one
schema bump. T4 depends on T2 (the occluder port) and T3 (no implicit
look-back).

## Size

27 test files / ~600 tests use `Wiring()`, `build_graph`, `output.all`,
the edge tables or `wired_of`. 757 goldens (181 PNGs) are drawn through
`graphmigrate.output_wires`; `tests/fixtures/frame-signatures.json` has
125 signatures against the retired default graph. The goldens and the
signatures are the safety net: none should move, because every preset is
migrated to the explicit wiring it drew. That makes this a plan-35-sized
build.
