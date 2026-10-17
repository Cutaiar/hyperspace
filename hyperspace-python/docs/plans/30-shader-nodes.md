# Plan 30 — shader nodes: every effect an image node, the palette anywhere

**Not built.** The design, agreed with the owner on 2026-10-16. The
launch prompt that runs it together with plan 28 is
[`28-30-orchestrator-prompt.md`](28-30-orchestrator-prompt.md). When it
is built this file is rewritten as built, in the shape of
[`26-render-graph.md`](26-render-graph.md).

## What the owner wants (2026-10-16)

> For shaders, and generally the effects tab we have now, there has to
> be a concept of a **shader node** in this graph. You need to be able
> to have **multiple instances** of these shader nodes. You need to be
> able to apply them **anywhere it makes sense**. What I don't want is
> one single point in the render graph that contains all the shaders
> and is not flexible beyond that. You need to be able to apply these
> things basically anywhere there are **bitmap-in, bitmap-out**
> exchanges between nodes.

The colour palette transform is the first use: a shader that takes a
bitmap in, folds its colours, and puts a bitmap out — placed wherever
the preset says. Auxiliary ports on it (a palette **out** to lights, an
**image in** that parameterises the palette from a camera) are separate
concerns: this plan designs the node so they can be added, and builds
neither.

## Where the code is today (`plan-24-26-27-integration`)

The render graph (plan 26, `graph.py`) already speaks bitmap in, bitmap
out everywhere downstream of the scene:

| Node | In | Out |
| --- | --- | --- |
| `Shape`, `Hands`, `PointCloud` | params | geometry |
| `Scene` | geometries | image |
| `HandsLayer`, `Readout` | geometry | image |
| `History` (the look-back's echoes and the dream) | image, cover mask | image |
| `Capture` (feeds the look-back ring and the dream worker) | image | — |
| `Composite` | under, over, depth images | image |
| **`Fx`** | image | image |
| `Output` | image, hands, readout | the screen |

The one inflexible point is `Fx`: one node per pipeline end (`fx.scene`,
`fx.scene+hands`, `fx.hands`) that runs **every** enabled effect file as
a block, in `@order`, through `FxChain.run`'s ping-pong textures. An
effect is a file in `shaders/fx/` with a `// @param` header (`fx.py`);
its params are `fx.<name>.*` (`on`, `mix`, `speed`, `blend`, `order`,
`target`, and one per uniform); a second instance is `fx.<name>.2.*`
(plan 26 A4, `FxState.set_instances`), on the same compiled program.
The palette fold (`palette.glsl`, `@order 95`) is one of those effects,
so it can only ever run at the end of a pipeline, on the whole picture.

Two things to carry, not break:

- **The pipeline end's jobs** live in `Fx.run`: paint straight into the
  one output when it is the frame's size and unflipped, else into the
  pipeline's frame texture once for every output that takes it; a
  pipeline whose layer is not bent this frame "stands down" to its
  fallback (`Fx.bent`, `Output.settle`); a pipeline that raises marks its
  views and they show their ground.
- **The faces target** (plan 20): an effect aimed at `faces` runs in a
  second chain (`render.face_fx`, borrowing the frame chain's programs)
  on the shape's face layer inside the scene's drawing, not on a graph
  edge.

## The design

### An `Effect` node, one per effect instance

`graph.Effect(name)` — `KIND = "effect"`, `INPUTS = {"image": IMAGE}`,
`OUTPUT = IMAGE`. Its name is the effect's (`acid`, `acid.2`,
`palette`); its params are the existing `fx.<name>.*`; its program and
uniforms come from `FxChain` as now (hot reload untouched). An effect
that is **off** is skipped: its consumers read its input's image, and no
pass runs, so the default frame costs what it costs today. An effect
that is **on** paints its input through its program into a texture the
next node reads. `mix`, `speed` and `blend` mean what they mean today;
`order` orders effects **within a chain run** (below); `target` is
superseded by placement for the frame and kept for the faces (below).

### The chain is a run of effect nodes

`default_graph` replaces each `Fx` node with a run of `Effect` nodes in
`@order`, one per effect file instance, ending in a thin pipeline-end
node that keeps `Fx.run`'s jobs (direct-to-output, the frame texture,
stand-down, the error path). The 556 golden frames pass **unchanged**:
a moved frame is a bug. `frame.stats["chain_runs"]` and the FX page's
status keep their meaning; the SYSTEM page's one `fx.scene` time becomes
one line per effect that ran, which is a gain.

### Placement: a shader node on any image edge

The preset's `graph` section (plan 26 A4) already lists `effect` nodes
(`file`, `instance`). It gains **where** the node sits. Two keys, one
per edge kind:

```json
"graph": {"nodes": [
 {"kind": "effect", "file": "palette", "after": "hands"},
 {"kind": "effect", "file": "palette", "instance": 2, "into": "output.2"},
 {"kind": "effect", "file": "acid", "instance": 2, "after": "scene"}
]}
```

- `after: "<node>"` inserts the effect on that node's **output**: every
  consumer of the node reads the effect instead. `after: "hands"` folds
  the hands' layer only; `after: "scene"` folds the scene before the
  history and the capture, so the dream inherits the folded colours.
- `into: "<node>[.<port>]"` inserts the effect on **one consumer's
  input** edge. `into: "output.2"` (its `image` port) folds one output —
  the projector matches the room while the glass stays raw.
- Neither key: the effect is in the chain run at its `order`, as today.

The node names are the graph's (`scene`, `hands`, `hands.2`, `history`,
`output.<n>`, an effect's own name), the same words the OUTPUT page's
"shows:" line and the SYSTEM page use. A placement this build cannot
honour — an unknown node, a port that is not an image, a cycle — is a
note on the preset strip and the default placement, like an unknown
kind today; the section is kept and written back. The orchestrator may
simplify the two keys to one if the build shows one suffices; the
contract is "any image edge, by name".

Several instances anywhere: the naming rule holds (the first instance
keeps today's ids, extra instances are `fx.<name>.<n>.*`), so a second
palette on the glass has its own centre and width, routable like any
effect's.

### The FX page, the OUTPUT page, SYSTEM

The FX page stays the editor of the **default chain**: chips, order by
drag, the strip. A placed instance shows its chip with where it sits
("after hands", "into output 2") and cannot be reordered there; moving
it is plan 28's editor (N4), or the JSON. The OUTPUT page's "shows:"
line and the LOOKBACK page say the placements in words, as A4 does for
the hands. SYSTEM times each effect node.

### The faces target stays an inner chain

`target = faces` keeps running inside the shape's face drawing
(`render.face_fx`): the faces' image is not a graph edge today, and
lifting it means the shape's faces becoming a layer, which is not this
plan. It is the one shader run the graph does not show; register it as a
rough edge with the lift as the other option. If the build finds the
faces image is a clean edge after all, the orchestrator may take it and
say so.

### Designed, not built: the auxiliary ports

The node interface gets a third port type beside `IMAGE`, `GEOMETRY` and
`MASK`: **`VALUE`**, a scalar or small vector a node publishes once a
frame, which plan 28's modulation graph can read as a source. Two uses
are named so the plan 28 editor can draw them later without a schema
change, and **neither is built here**:

- the palette's `palette` **value out** (centre, width, the sat and val
  ranges, the ramp's anchors) — what a lights sink (plan 29) would take;
- an `image` **data in** on the palette (`sample`) that would set its
  params from a bitmap — a camera frame of a neighbouring install.

Register the port type and the two uses as one decision row.

## Work packages

Small: three code WPs and a docs WP, in order, each a PR into the
integration branch.

- **D0 — the effect node and the chain as a run.** `graph.Effect`, the
  pipeline-end node, `default_graph` building the run, `FxChain` made
  able to run one effect between two textures, SYSTEM's per-effect
  lines. Goldens unchanged (all 556), no extra pass when every effect is
  off, `test_the_render_stack_imports_no_registry` untouched.
- **D1 — placement in the preset.** `after` / `into` in `graph.GraphSpec`
  / `read_graph` / `to_json` and `preset.GraphSection`; the graph built
  with placed nodes; the three proof fixtures under
  `tests/fixtures/presets/` — palette after `hands`, palette into
  `output.2`, a second acid after `scene` — each with its golden; the
  words on OUTPUT and LOOKBACK; refusals as notes. Depends on D0.
- **D2 — the FX page and the `VALUE` port.** Placed chips on the FX
  page, the `VALUE` port type declared with its two named uses (no node
  publishes one yet), the faces exception registered. Depends on D1.
- **D3 — docs.** This file as built; `ENGINEERING.md` §2 (the effect
  node, placement, the goldens); `ARCHITECTURE.md` and `.html` (the
  graph's node list; the `Fx` row becomes `Effect`); `DECISIONS.md`
  (the owner's decisions below with Who `owner`); `DECISION-REGISTER.md`
  rows; `11-hand-checks.md` group **X**; `TESTING-GUIDE.md`;
  `plans/README.md`; `24-party-wishlist.md`'s palette line points here.

## Decisions already made (owner, 2026-10-16) — do not relitigate

1. **Shaders are nodes**: an effect file is an image node, bitmap in,
   bitmap out, several instances, placeable on any image edge. No single
   point in the graph holds "the shaders".
2. **The palette is the first shader node moved**, with a fixture per
   placement. Its fold and gradient map (plan 24 C6) are unchanged.
3. **Auxiliary ports are separate concerns**: the palette's value out
   and image-in are designed (the `VALUE` port type), not built.
4. **No preset is edited or added**; every proof is a fixture through a
   scratch library (decision 23 of the previous run holds).
5. **The default graph is pixel-identical**: every golden passes
   unchanged, and SYSTEM gains a line per effect.

## Decisions the run may make

The placement keys' final form (`after` / `into`, or one key); the
pipeline-end node's name and whether `Fx` keeps its class; how an off
effect is skipped in the graph (a pass-through alias or a rewired edge);
whether the faces image becomes an edge; the `VALUE` port's exact
shape. Each as a register row from the next free number, in the file's
format.

## Done when

- A preset in a scratch library says `{"kind": "effect", "file":
  "palette", "after": "hands"}` and the hands fold while the shape does
  not; `into: "output.2"` folds one output only; `after: "scene"` folds
  what the dream echoes. Each has a golden.
- With no `graph` section every one of the 556 goldens matches.
- SYSTEM shows a time per effect that ran.
- Hand checks (group X, written by D3): the three placements on the
  real projector and glass; two palettes with different centres on two
  outputs; the FX page's placed chip; the faces target still bending the
  faces.
