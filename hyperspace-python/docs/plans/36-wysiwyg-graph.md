# Plan 36 — the WYSIWYG graph: no default graph, no hidden edges; look-back and dream as two nodes

**Status: built (2026-10-26)** on `plan-36-build` (cut from the quick
wins, PR #241), from the owner's notes after the 2026-10-25 install,
agreed with Dylan. **D1–D5 accepted by the owner as recommended
(2026-10-26).** Build plan [`36-wysiwyg-graph-build.md`](36-wysiwyg-graph-build.md).
Tests at 1810314: the full suite (`uv run pytest -q --all`) 4155 passed,
2 skipped — the fast tier 3941 passed, 2 skipped; goldens 128 passed (757
pictures, 9 re-recorded, each with its reason under "What changed in the
build"); the final review's fixes add their own tests on top.
Hand checks 354-369 (group AG); register rows 396-416. Plan 37 is the
faces (their shaders consolidated, faces as a target like any other) and
the nodes-as-pictures visual language (FL Patcher-style); the quick wins
from the same notes (insert spawn, no automatic layout, the output behind
the canvas, bigger canvas, two-finger pan) are on their own PR.

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
| cover built from the scene | `scene.cover → lookback.cover` (a mask port) | no occlusion |
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
  `contrast`) as a premultiplied picture with alpha. Optional `cover`
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
schema bump. T4 depends on T2 (the cover port) and T3 (no implicit
look-back).

## Size

27 test files / ~600 tests use `Wiring()`, `build_graph`, `output.all`,
the edge tables or `wired_of`. 757 goldens (181 PNGs) are drawn through
`graphmigrate.output_wires`; `tests/fixtures/frame-signatures.json` has
125 signatures against the retired default graph. The goldens and the
signatures are the safety net: none should move, because every preset is
migrated to the explicit wiring it drew. That makes this a plan-35-sized
build.

## What changed in the build

The plan above is the design; this is where the build differs from it, or
chose within it. Each ruling was made by the controller on 2026-10-26 and
has a row in [`DECISION-REGISTER.md`](../DECISION-REGISTER.md) (396-416),
the owner to say keep or overturn.

**As built, in the plan's terms.**

- **The cover port is `lookback.cover`**, fed by `scene.cover`; the W2 text
  and the look-back's W4 text above said `occluder` and are corrected.
  The look-back's brightness-mask port from `/6` kept its own name.
- **All outputs is a drawn bus of rig-owned cables** (`graph.RigWires`):
  one `output.all.<port> → output.N.<port>` per window and port, four bus
  ports in all (image, hands, guide and depth), drawn on GRAPH, cut by
  Delete, re-added by dragging from All outputs' pin onto the window's
  same port, persisted in the show (`library.Project.rig`, file key
  `"rig"`, written only when something is cut) and undone with the app's
  undo. A window's port is its own wire, else the standing bus cable,
  else nothing (`graph.window_ports`).
- **Look-back = picture in → trail out; dream = picture in → dreamed
  picture out.** `dream.on` off passes the input through and the worker
  does not run; one live dream, a second refused in words (D2). The
  starters lay the composite (D3: trail only).
- **Schema `/7`.** A save writes `hyperspace.preset/7` and nothing older.
  The 25 factory presets are `/7` files regenerated by
  `tools/migrate_library.py` (their `/6` sources are kept in
  `tests/fixtures/factory-sources/`). Reading `/4`-`/6` survives only as
  the explicit one-way migration to `/7`, with a note on load.
- **A new preset** is `shape → scene → output.all.image`, plain faces,
  no pattern wire; the starters (scene chain, tracers, tracers + dream,
  dream on a picture, a channel to the backdrop) are the picker's.
- **Preset only** is on by default for every preset (D4), a chip on the
  GRAPH head, `· N hidden` on the head line; nothing is mutated and
  nothing is laid out again.
- **Goldens re-recorded during the build (9 of 757).** T1 four:
  `party-trip`, `party-noita` and `lfo-breathe` at `|absent|hands+through`
  (the hands mute now acts on the hands layer's input to that window's
  chain, so the stand-down that used to paint the chain clean is gone),
  and `through-one-output|present|scene+through` (its old golden drew
  hands with the hands mute on, an R9 violation; the new frame is byte
  identical to the fixture's own `scene` golden). T3 four:
  `palette-glass|…|scene+hands+through` and `wired-outputs` at
  `scene+hands`, `scene` and `scene+through` (a placement on a window's
  shared picture was not a wire; the explicit wire the canvas draws moves
  104 of 36000 thumbnail pixels, mean 0.18). T4 one:
  `wired-outputs|present|scene+hands+through` (6029 pixels by 1/255:
  `history → acid.2` read the off look-back's copy pass, now
  `scene → acid.2`). The other 748 did not move; all 125 frame signatures
  were re-recorded for the new ids.

**Rulings** (the controller's, 2026-10-26; cost-if-wrong in the register).

1. **Factory presets regenerate at T4.** `/7` is unreleased during the
   build, so T4 may change what a `/7` look-back means and regenerates the
   25 factory `/7` files by re-running the migration from their pre-T3
   `/6` originals; "migrate to the explicit wiring it drew" holds either
   way.
2. **"No `/6` reader" means no fill-in and no `/6` saves.** Reading
   `/4`-`/6` survives only as the explicit one-way migration to `/7`
   (`migrate_library` and the old fixtures need it), with a note on load.
3. **`migrate_library` is never run on the owner's data by the build**
   (`~/Hyperspace`, the Drive library): it is the hand check.
4. **Tasks run one after another**, one implementer and one reviewer per
   task, not parallel implementers on one branch.
5. **The WYSIWYG rule beats "goldens unmoved".** The stand-down
   (`Output.settle`, `Shown.fallback`, bent) is deleted; the hands mute
   acts on the hands layer's input to that window's chain (a mute, not a
   rewire); three `…|absent|hands+through` goldens re-recorded to what the
   wiring draws, the two resize ones held by the mute. Supersedes an
   earlier ruling to keep the stand-down as the mutes' mechanism.
6. **`through-one-output|present|scene+through` re-recorded** (see above).
7. **The `/6` re-migration on every load is T3's to close.** T2's cut
   hidden-edge wire returned on load; T3 gates on `/7` and tests "cut a
   migrated wire, save, reload: stays cut".
8. **The four placement goldens are accepted** (T3, above).
9. **Implementers skip the full suite** (owner, 2026-10-26): from T3 the
   covering tests, then from T4 the fast tier plus `--all -m golden` and
   ruff; the controller runs the full suite once before the final review.
10. **The golden speed-ups start at T4's implementer head** (e441780), in
    parallel, merged into the build after T5: one golden test per rig job,
    hashes not held pixels, a shader-program pool in `tools/golden_frames.py`
    (goldens 12-14 s and 0.33 GB, were 32-64 s and 2 GB; nothing under
    `hyperspace/` changed).
11. **Dream fidelity is kept as the spec's three-node chain** and deferred
    (below).
12. **The new preset's chain is exactly `shape → scene →
    output.all.image`**, plain faces, no pattern wire: the owner's words
    were "basic geometry routed into a scene, the scene into the output".
13. **T5's review ran alongside T6's implementer** (the owner wants it
    merged soon); no fix needed a rebase.
14. **"Preset only" shows whatever is cabled to the section**, of any
    kind (an LFO routed to an effect, a controller bound to a param, so a
    moving param shows its source); controllers, modulation and macros
    with no cable to the section are hidden, as are group nodes and the
    camera. T6's implementer first hid controllers and modulation even
    when cabled; the controller's T6 fix (1810314) reversed that, as the
    brief had it.

**Known limitation, deferred by the owner (2026-10-26): dream fidelity.**
The migrated dream dreams the look-back's *occluded trail*, not the raw
capture, and D is no longer occluded by the shape; no drawn wiring of the
three nodes reproduces the old look exactly, so `party-wake` with the
worker live looks different from `/6`. The follow-up is a separate dream
`submit` port (apart from the picture it lays over) and an occluder after
the dream. Priority was finishing plan 36; hand check 366 is the look by
eye. Plan 34's `dream → X` now reads trail + D.

**Known follow-ups** (reviewer minors, none blocking): the `into
output.N` placements' retired plumbing (`Wiring.placed`, `_WireCtx.placed`,
`lookback_words`, `output_placement_words`, `graph_words`,
`Graph.placed_names`) is dead code; `tools/outputs_shots.py:89` crashes
(`wired_of` on already-wired wiring); an old file with an unreadable
section is stamped `/7` and not re-migrated; the golden manifest's stale
route words (~25 entries) want one `--record` pass; `GraphSpec.effect_names`
and `graphmigrate.section_effects` duplicate each other, as do
`_through_chain` and `through_of`; `placed_wires`' refused-note filter is
prefix-based; `laid` depth now applies only to the `laid_on` hands layer
(a user preset laid depth-aware with `hands.2.layer` on a window changes);
a window muted while a sibling shares its through composite is not still
shows hands (one composite); `graphview.build` with no render graph or rig
draws every bus cable as standing (headless, first frame); dragging
`render:output.all` with a `pre` entry has no test that `pre` follows; the
scene-chain starter silently drops what already fed All outputs' image
(`STARTER_SAID` should name it); the `acid-scene` preset draws a wire
backwards (area rules; plan 37); `test_desk_coverage::
test_the_committed_report_is_fresh` is to be checked in the final full
run.

**Plan 37** is the faces (their shaders consolidated, faces as a target
like any other) and the nodes-as-pictures visual language (FL
Patcher-style).
