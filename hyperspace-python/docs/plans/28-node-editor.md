# Plan 28 — the node editor

**Not built.** The design, agreed with the owner on 2026-10-16: the
whole wishlist section (N1–N4 and "controllers as nodes") in one plan,
with modifiers living in the preset. The launch prompt that runs it
together with plan 30 is
[`28-30-orchestrator-prompt.md`](28-30-orchestrator-prompt.md). When it
is built this file is rewritten as built, in the shape of
[`26-render-graph.md`](26-render-graph.md).

## What the owner wants

One patch-cable editor for both the modulation and the visual pipeline
([`24-party-wishlist.md`](24-party-wishlist.md), "Node based editor"
and "Controllers as nodes", 2026-10-12; scope confirmed 2026-10-16):

| Stage | What it adds |
| --- | --- |
| N1 — modifier nodes | Routes become chains: source → modifiers → param. Curve, scale/offset, smooth, combine two sources (+, ×, min, max), threshold-to-trigger |
| N2 — read-only graph view | A page that draws what is wired to what: devices, routes, modifiers, params, render nodes |
| N3 — edit the modulation | Drag cables between sources, modifiers and params; Learn still works and lands as a cable |
| N4 — edit the render graph | The same editor on the render graph: geometry, hands, materials, effect placement, palette, outputs |

With it: each controller instance is a node (*Wand 1*, *Drums*, *Leap*,
*APC40*), each degree of freedom an output port; roles, not serials;
two input ports per param (`base` takes many setters, last touch wins;
`mod` takes one performer, under the referee; combining two performers
needs an explicit combine node); values and triggers are two signal
kinds, crossed by envelope and threshold nodes; collapsible port groups
and "patched ports only" for the APC40 and the hands; the APC40 as two
nodes, *APC40* and *APC40 (SHIFT)*, with no layer view; feedback
implicit along a cable, lights explicit sinks; **evaluation in
dependency order each frame removes today's one-frame lag**; loops only
through a one-frame delay node; both graphs stored in the preset as
plain JSON so they stay git-diffable; today's routes convert
one-to-one. **Rejected**: GLSL written in the graph, or a general
TouchDesigner — nodes are a curated set of built-ins
(`DECISIONS.md`, "Decided not to build").

## Where the code is today (`plan-24-26-27-integration`)

**The modulation model** (`routing.py`). A route is a `Binding`:
`source` (`scheme:address`, a `@role` qualifier allowed), `target` (a
param id), `op`, `value` (the depth for `push` / `position`),
`enabled`, `scale` (a param whose value multiplies the depth), `when`
(a gate address), `rest`, `motion` (the envelope follower and spring of
`motion.py`), `pickup`, `feedback`, `layer`. Ops: `fire toggle step set
abs rel rel64 momentary hold push position send`; `push` and
`position` are the performer ops (`MOD_OPS`), `send` marks a sink row.
One flat table (`Bindings.bindings`) mixes the session's rows with the
loaded preset's; `is_session_row` decides what reaches `bindings.json`
(everything but performer rows and preset-layer MIDI rows). **The
referee**: a param has at most one enabled performer (`Owned`,
`referee`, `replace_owner`); a disabled row owns nothing. **Macros**
(`macro.N`, `Macro.subs`): a `Sub` sets a param's base or multiplies one
route's depth, so a macro is already a fan-out of cables into `base`
and `depth` ports. `Router.modulate` (frame step 10) runs every live
performer row: depth = `value × scale.value × Π depth subs`, the source
through its follower, `push`: `depth·(u − rest)`, `position`: `depth·u −
norm`, then `Param.modulate`; `reg.apply()` (step 11) lands `base + mod`
on every object. **The one-frame lag** (`ARCHITECTURE.md` §2): a `scale`
param, a macro's depth subscriber and an LFO's own `depth` read what
`apply()` wrote last frame; two tests pin it
(`test_an_lfo_owning_another_lfos_depth_changes_its_output_next_frame`,
`test_a_macro_owned_by_a_hand_scales_a_lanes_push_one_frame_later`).

**Where things live.** A preset (`hyperspace.preset/2`): `values`,
`routes` (performer rows), `desk` (preset-layer MIDI rows, or a
template plus overrides), `macros`, `modules`, `graph` (plan 26 A4).
The session: `bindings.json` (invariant and SHIFT-layer desk rows, pad
rows, keys, sinks) and the show (`ghost.*`, outputs, `eye.*`).
Performance groups (`view rot camera pattern dream fx lfo macro`) are
preset content; session groups (`tempo hands ghost band master scene
audio output overlay ui desk eye cloud`) are not (`params.py`).

**Learn** (`learn.py`): `Learn.arm(pid, want)`; a desk learn writes a
`Binding(source, pid, "abs", layer="preset")` through `table.bind`; a
continuous learn (`learn_source`) a `push` or `position` row through
`replace_owner`, with `pending` for the referee's prompt; a sink learn a
`send` row. Every path lands in the live table, so the loaded preset is
dirty.

**The ROUTING page** (`ui_routing.py`): routes, desk, macros, session,
sinks, in that order; `_sources` lists every address with its label,
`_targets` the modulatable params, `_gates` the gate addresses,
`unmapped` the dark desk controls. Pages are `ui.PAGES` plus a
`Panel._page_<key>` method.

**The render graph** (`graph.py`, plan 26; plan 30 adds the effect
node): typed ports `IMAGE`, `GEOMETRY`, `MASK` (plan 30 adds `VALUE`);
`Graph.add` sorts by dependency; `default_graph(views, wiring)` builds
today's frame from the outputs' switches and the preset's `Wiring`; the
preset's `graph.nodes` lists what differs from the default. Known gap
(plan 26's rough edges): the section is wiring *choices*, not a wire
list — the outputs are the session's switches, at most one hands node
makes the layer, a preset cannot say which output gets which hands node.

**The editor widget.** Nothing imports `imgui_bundle.imgui_node_editor`
yet; `imgui-bundle 1.92.9` ships it (`create_editor`, `begin_node`,
`begin_pin`, `link`, `begin_create` / `query_new_link`, `begin_delete`,
`get_node_position` / `set_node_position`, selection, zoom — verified
importable in this environment). The control window is plain `imgui`
over GLFW with the app's own renderer.

## The design

### 1. The modulation graph, evaluated in dependency order

A new leaf module, `patch.py` (imports nothing from the package but
`motion` and `tapers`): the modulation graph's nodes and edges as data,
and a sorter. Nodes: **sources** (every fed lane: `lane`, `hand`,
`hands`, `axis`, `lfo`, `ext`, `mod`, an OSC role, a MIDI control),
**modifiers** (§2), **macros** (bus nodes), **params** (each with a
`base` port and a `mod` port). Edges: a performer `Binding` (source →
`mod`), a setter row (a MIDI or pad row → `base`), a macro `Sub` (macro
→ `base`, or macro → a cable's `depth`), a `scale` (param → a cable's
`depth`), a modifier's inputs, an LFO's `depth` / `rate` / `phase`
params (param → LFO). Routes convert **one-to-one**: a cable's identity
is the `(source, target)` pair, as today.

`Router.modulate` runs the graph in that order: a node is evaluated
after everything it reads. The LFOs step inside the evaluation (an LFO
is a source *with inputs*), so an LFO owning another LFO's depth, a
macro scaling a push, a `scale` param that is itself modulated, all land
**this frame**. The sort is computed when the table or the LFO list
changes, not per frame. A **cycle** is refused unless it passes through
a `delay` modifier (§2): the offending cable is kept disabled with a note
on the strip ("loop: hand R x → mod 3 → … → hand R x needs a delay"),
the way the referee drops a second performer today. Sinks still run
after `apply()`, as now. `ARCHITECTURE.md` §2's lag rule is rewritten:
"everything a performer moves lands in `reg.apply()` in dependency
order; nothing reads a stale value but through a delay node". The two
lag tests flip to "the same frame"; every existing preset produces the
same effective values one frame earlier, which a test proves over the
factory presets with a synthetic tape (the plan 26 goldens are unmoved,
because they are recorded at rest).

### 2. Modifier nodes (N1), in the preset

A modifier is a node with one or two `VALUE` inputs, a few params, and
one output lane it publishes under the scheme `mod` (`mod:<n>`), so a
route's source may be `mod:3` and the Router, Learn, the referee and
ROUTING's source combo need no new path. Kinds, the curated set:

| Kind | Inputs | Params | Out |
| --- | --- | --- | --- |
| `curve` | one | shape (exponent, S-curve or table), invert | value |
| `scale` | one | multiply, offset, clamp | value |
| `smooth` | one | attack, release (the `motion.Follower`), or a spring | value |
| `combine` | two | `+ × min max crossfade` and a balance | value |
| `threshold` | one | on level, off level (hysteresis), hold | **trigger** |
| `delay` | one | — (one frame) | value |

Ids follow the naming rule (`mod.1`, `mod.2`…); params are `mod.<n>.<p>`
in a new performance group `mod`, so they are preset content, routable
and modulatable like any other (a hand can drive a smooth's release).
**Home (owner, 2026-10-16): the preset**, beside `routes`:

```json
"modifiers": [
 {"id": "mod.1", "kind": "smooth", "in": ["hand:right.energy"], "attack": 0.05, "release": 0.6},
 {"id": "mod.2", "kind": "combine", "in": ["mod:1", "lane:0"], "how": "mul"}
],
"routes": [{"source": "mod:2", "target": "fx.acid.mix", "op": "position", "value": 1}]
```

A desk template may carry modifiers, so a rig-wide one ("always smooth
the hand energy") lands in every preset that uses the template — plan
24's mechanism for exactly this. A preset whose modifier names a source
this rig lacks keeps it dormant, as a dormant route is today. A route
onto `mod:<n>` whose modifier is missing is dropped with a note at
load. Undo covers modifiers because the preset table is watched.

Before the editor exists, modifiers are **usable from ROUTING**: a
MODIFIERS strip under the routes (add a kind, pick its inputs from the
source combo, its params on the strip), so N1 ships on its own.

### 3. The GRAPH page, read-only (N2)

A new page, `graph`, in `ui.PAGES`, drawn by `ui_graph.py` on
`imgui_node_editor` (its own editor context per panel; the widget's
own settings file is **off** — positions come from the preset). One
canvas holds both graphs, because controllers feed render params:

- **Device nodes**, one per open registry device, named by role
  (`apc40`, `pad`, `leap`, `phone`): output ports are its sources, in
  **collapsible groups** (the hands: axes, pinches, dance, grab; the
  APC40: knobs, faders, buttons…), with a **patched ports only** toggle
  per node. A lost device draws grey with its cables dormant. The
  analyzer is a node (one port per band), each LFO a node (its `depth`,
  `rate`, `phase` as input ports).
- **Modifier nodes** and **macro nodes** (a macro is a bus: one knob,
  one output, its subs as cables into `base` or `depth` ports).
- **Parameter targets grouped by the render node that owns them**: the
  render graph's nodes (`shape`, `hands`, `scene`, each effect,
  `history`, `eye`/`camera`, each output) draw their params as input
  ports — each a `base` stub (many dashed cables) and a `mod` stub (one
  solid cable). Params no render node owns (`tempo`, `master`, `desk`…)
  sit in a node per group. A collapsed node shows only its patched
  ports.
- **Render cables** between `IMAGE` / `GEOMETRY` / `MASK` ports, drawn
  from the live `Graph` (`Renderer.graph`'s nodes and inputs), including
  plan 30's placed effects.
- Cables are coloured by signal kind (value, trigger, image, geometry,
  mask); a value cable's thickness or glow follows its live reading;
  hover shows the source's reading and the depth; a click selects and
  the right-hand strip shows the ROUTING row (or the effect's strip) for
  it.
- **Layout**: node positions are saved in the preset as `layout:
  {"<node>": [x, y]}` (session nodes — devices, outputs — in the show),
  git-diffable; an unplaced node gets an automatic column by kind
  (devices → modifiers and macros → render nodes left to right, outputs
  last). A **tidy** button re-lays everything.

### 4. Editing the modulation (N3)

- Drag from a source, modifier or macro port to a param's `mod` port →
  `Bindings.add` (op `position` at depth 1, or `push` at the hand
  learn's depth for a hand axis, as `learn._row` chooses); the referee's
  `Owned` becomes the same replace prompt ROUTING shows; drop on an
  existing cable's end → `move_route`. Drag to a `base` port → a setter
  row for a desk or pad source, else refused in words ("a hand sets no
  base; aim at mod"). Drag from a macro → a `Sub`. Delete a cable →
  `remove` (its depth subs follow, as now). Drop a cable on a modifier's
  input → that modifier's `in`; drop a modifier *onto* a cable → it is
  inserted (the cable's source becomes the modifier's input, the
  modifier's output the cable's source).
- **Learn lands as a cable**: right-click a `mod` port → the same Learn
  menu ROUTING's params offer (desk, pad, hand, a role); when it
  completes, the new `Binding` appears as a cable. The ROUTING page and
  the GRAPH page edit one table, so either shows the other's change at
  once; nothing is duplicated.
- Every edit goes through the table's own methods, so undo (`undo.tick`
  watches the table), dirt, the referee and the session/preset split
  are untouched.

### 5. Editing the render graph (N4)

- The preset's `graph` section becomes **nodes plus a wire list**:
  `{"nodes": [...], "wires": [{"from": "hands", "to": "output.2.hands"},
  {"from": "palette", "to": "output.1.image"}]}`. A wire absent is the
  default graph's; a section with none is today's. Plan 30's `after` /
  `into` keys are the same wires written short, and read as such.
- **Outputs as nodes** with ports (`image`, `hands`, `readout`): a
  preset may say which output gets which hands node, which effects it
  alone takes, and whether its hands are over or depth-aware. The
  session's output switches stay the default for any output the preset
  does not wire (the rig's, not the look's), which closes plan 26's
  "wiring choices, not a graph" rough edge.
- On the canvas: drag an image cable between typed ports (a wrong type
  is refused in words); add an effect instance from the file list (a
  node picker on right-click: effects, a hands node, a composite); delete
  a node or wire. `Renderer` rebuilds the graph from the new
  `GraphSpec` as it does for a wiring change, with the same refusals
  (two layers, a cycle) as notes.
- "Hands as lines, through the acid, with tracers" is done by dragging
  on this page and saving the preset — the wishlist's done-when.

### 6. Controllers as nodes; the APC40 as two nodes (N5)

- A device's ports come from `Device.schemes` / its sources (plan 27);
  the registry's `Device.layers` gives a device with a mode switch one
  node per layer: the APC40 is **two nodes**, *APC40* (preset-layer
  cables, saved in the preset's `desk`) and *APC40 (SHIFT)* (session
  cables, `bindings.json`), each port sending only while its layer is
  up, a press belonging to the node that was up when it went down
  (D12). Invariant controls (SHIFT, crossfader, bank pads, transport,
  tap) are ports on *APC40* only. Rings and LEDs follow the node that is
  up; soft pickup re-engages per port on a latch flip. **The faders and
  the APC40's behaviour are not changed by this plan**: the two nodes
  are a presentation of the rows that exist (D1, D4–D6 hold); Dylan's
  current desk work lands first and is read, not rewritten.
- **Desk templates are subgraphs**: a template draws as one collapsed
  node whose ports are its mapped controls; expanding it shows the rows;
  edits inside write the preset's overrides, as today.
- Roles, not serials: a cable from a device this rig lacks draws from a
  grey placeholder node named by role, dormant, as dormant routes are.

### Out of scope

GLSL in the graph and a general TouchDesigner (decided); new devices or
sinks (plan 29); the palette's auxiliary ports (plan 30 designs them);
order-independent transparency; the hands' styles and textures (the
creative pass and a later plan). The faders' and the APC40's map and
feel: Dylan's, in flight.

## Work packages

Streams and order; each WP a branch and a PR into the integration
branch, a sub-agent in its own worktree off a verified base. Plan 30's
D0 and D1 run beside stream N and gate N2 and N4.

| WP | What | Depends on |
| --- | --- | --- |
| **N0** | `patch.py`: the modulation graph as data, the sorter, `Router.modulate` evaluating in dependency order, the LFOs inside it, the cycle refusal; the two lag tests flipped; the "same values one frame earlier" proof over the factory presets; `ARCHITECTURE.md` §2's rule drafted for N6 | — |
| **N1** | `modifiers.py` and the six kinds; the `mod` scheme and group; the preset's `modifiers` list; a template may carry them; the MODIFIERS strip on ROUTING; load-time refusals | N0 |
| **N2** | `ui_graph.py`, the GRAPH page read-only: device, modifier, macro, render and param-group nodes; cables by kind; live readings; `layout` in the preset and the show; tidy | N0, N1, plan 30 D0 |
| **N3** | Editing the modulation on the canvas: add, move, remove, insert a modifier, macro subs, the referee prompt, Learn from a port landing as a cable | N2 |
| **N4** | The wire list in the preset, outputs as nodes, image cables and the node picker on the canvas, `Renderer` rebuilt from the spec; plan 30's placement keys read as wires | N2, plan 30 D1 |
| **N5** | Controllers as nodes: device nodes from the registry, the APC40 as two nodes via `Device.layers`, templates as subgraphs, grey role placeholders | N3 |
| **N6** | Docs: this file as built; `ARCHITECTURE.md` §2 and §3 (the lag rule, the modulation graph) and `.html`; `ENGINEERING.md` §6 (the GRAPH page), §9 (modifiers), §2 (wires); `DECISIONS.md` rows (Who `owner`); `DECISION-REGISTER.md` rows; `11-hand-checks.md` group **Y**; `TESTING-GUIDE.md`; `plans/README.md`; `24-party-wishlist.md`'s node-editor line | all |

N0 ‖ N1 can start on day one with plan 30's D0; N2 waits for the three;
N3 ‖ N4 after N2 (N4 also after D1); N5 after N3; a review pass; N6.

## Decisions already made — do not relitigate

Owner, 2026-10-12 (the wishlist) and 2026-10-16:

1. One editor for both graphs; the four stages **N1–N4 in one plan**,
   with controllers as nodes.
2. **Modifiers live in the preset** (2026-10-16), beside `routes`; a
   desk template may carry them.
3. Two input ports per param: `base` many, `mod` one under the referee;
   combining two performers is an explicit `combine` node.
4. Values and triggers are two signal kinds, crossed by `threshold` and
   envelope (`smooth`); encoder vs fader behaviour is the port's, set by
   the device profile.
5. Roles, not serials; a missing device's cables wait.
6. The APC40 is two nodes, *APC40* and *APC40 (SHIFT)*, no layer view;
   D1, D4–D6 and D12 hold; invariant controls on *APC40* only.
7. **Evaluation in dependency order removes the one-frame lag**; loops
   only through a one-frame delay node.
8. Both graphs in the preset as plain JSON; routes convert one-to-one.
9. Rejected: GLSL in the graph, a general TouchDesigner. Nodes are
   built-ins; shaders stay files with hot reload.
10. The editor is `imgui_node_editor` from `imgui-bundle` — no new
    dependency.
11. No preset is edited or added; proofs are fixtures through a scratch
    library. The faders and the APC40's map are Dylan's and untouched.

## Decisions the run may make

The modifier kinds' exact params and curves; the `mod` scheme's address
form; the `layout` map's shape and where session nodes' positions live;
the canvas's grouping of params with no render node; the wire list's
exact keys and how plan 30's short keys map onto it; which of an
output's switches a preset may wire; the APC40 node's port groups; the
cycle refusal's words; the tidy layout's columns. Each as a register
row from the next free number.

## Done when

- Loading every factory preset gives the same effective values as
  before, one frame earlier, and the two lag tests say "the same frame".
- On ROUTING alone: "right hand energy, smoothed, times band 0, into
  acid mix" is built from the MODIFIERS strip, saved in the preset, and
  comes back.
- On the GRAPH page: that patch is drawn and can be built by dragging;
  Learn from a port lands a cable; the referee prompt appears when a
  param is taken.
- "Hands as lines, through the acid, with tracers" and "palette on the
  glass only" are made by dragging and saving, no code, and the OUTPUT
  page says them in words.
- The APC40 shows as two nodes whose ports light with the layer; a
  SHIFT-layer cable is in `bindings.json`, a preset-layer one in the
  preset.
- Hand checks (group Y): the lag gone on a real LFO-on-LFO patch; a
  cable dragged on the laptop screen at the control window's size; the
  APC40 nodes with the real desk; a patch saved on one Mac loading on
  the other through the shared library.
