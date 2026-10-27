# Plan 37A — nodes as pictures: the picture a node makes is the node, the cable palette, legibility from the display

**Status: spec (2026-10-27), awaiting the owner's decisions D1–D5.** Build
plan [`37a-nodes-as-pictures-build.md`](37a-nodes-as-pictures-build.md).
From item 4 and item 1 of the owner's notes after the 2026-10-25 install
(register row 415, owner 2026-10-26: "Plan 37 is nodes as pictures, and
the faces"). Plan 37 is two workstreams that do not depend on each other:
this one (37A) and the faces ([`37b-faces.md`](37b-faces.md)). Either
may be built, reviewed and merged first; "Independence" below lists what
each touches so a merge of the second is mechanical.

The owner's words (2026-10-26): **not icons on boxes — the nodes *are*
pictures**, like FL Studio Patcher's generator and effect images; hover
gives the details. Cables coloured by what they carry. And from item 1:
fonts, pins and hit areas a bit bigger in general, scaled to the display.
Everything here obeys the WYSIWYG rule of plan 36: nothing is added to the
graph, nothing is laid out by itself, nothing is hidden.

## What is there today (the map, `main` @ f2351a0)

File and line references drift; the names hold.

1. **A node is text.** `ui_graph._node` (1216–1272) draws a title line
   (in stub, label, `+`/`-`, out stub) and, collapsed, up to
   `SUMMARY_LINES = 5` disabled lines from `graphview.summary` (2477): the
   node's `said` word, the switch pick or "reaches nothing", "n params ·
   k patched", the picture-port count. Expanded, the port rows. A
   collapsed render node is `HEAD_H + ROW_H × lines` tall
   (`graphview.height`, 2267; `HEAD_H` 42, `ROW_H` 28 at `SCALE` 1.25), so
   at most 182 px; `NODE_W` is 237.
2. **No node has a picture of its own.** Painted nodes (effect,
   composite, history, dream) paint into the framebuffer their consumer
   hands them (graph.py 85–97); `Node.image(frame)` materialises a
   texture only on demand; the `Frame` and its `frame.frames` are thrown
   away after `graph.evaluate` (render.py 1514–1592). What persists on the
   renderer: `_frames` by key (pruned after `SIZED_KEEP_FRAMES`), the
   per-size pools (scratch, not stable per node), each delay's
   `DelayPair`, each look-back's ring atlas, the dreamer's `dream`
   texture, the scene's `SceneTarget`.
3. **Two precedents for drawing for the panel.** `outputs.Preview`
   (291–329) is a tap on output 1's presented frame, asked for by the
   GRAPH head's **output behind** chip (`_backdrop`, ui_graph 828) and
   drawn with `add_image(ImTextureRef(tex.glo))`. The FACES swatches
   (`Renderer.want_swatches` / `_swatch_step`, render.py 2537–2572) draw
   one 64² swatch a frame, round robin, only while the page wants them.
   `_for_the_panel` (render.py 1644) runs at the end of `draw_outputs`
   with `PREVIEWS_PER_FRAME = 2`.
4. **One thread, shared textures.** `draw_render` then `draw_panel` on
   one loop (app.py 1201–1214); the control window shares output 1's
   context (app.py 436), so a texture the renderer drew this frame can be
   sampled by the panel after the flush at app.py 663. FBOs and VAOs are
   per context; textures are shared.
5. **The canvas node is the live render node.** `VNode.ref` is the
   renderer's `rgraph.Node` (graphview 1369, 1390–1404; id
   `render:<name>`), so a node's picture, `said` and timing are one
   attribute away from the drawing code.
6. **Hover is thin.** `_hover` (ui_graph 1342–1382) shows a compile
   error, the faint tip or `n.status`; the details are in the side pane
   (`_node_side`, 1664: the page chip, the effect strip or the modifier
   block, `_param_rows`). `ui.tooltip` (ui.py 199) is text only.
7. **Cables are coloured by type**, five of them: `ui_graph.COLOURS`
   (162–168) keys `VALUE` grey, `TRIGGER` orange, `IMAGE` red,
   `GEOMETRY` blue, `MASK` purple, since plan 28 N2 (2026-10-16). A
   value cable's thickness is its reading; a render cable is `WIRE`;
   dormant `0.22`, through `0.5`. A picture graph is nearly all `IMAGE`,
   so every wire that matters is the same red: this is why the install
   read the cables as uncoloured. `VCable.ref` is the wire, so a cable's
   source node is `view.owner(c.src_port)` and its area `VNode.area`.
8. **Size is a constant.** `graphview.SCALE = 1.25` (1897) feeds
   `COL_W`, `ROW_H`, `HEAD_H`, `GAP`, `TITLE_H`, `NODE_W` and the
   canvas font (`ui_graph` 951); `PIN` is 12. The quick wins made it a
   quarter bigger for every display alike; nothing reads the display.
   The canvas zooms (wheel, ⌘ + two fingers, Dillon's pinch, #246) and
   that zoom scales text, pins and hit areas together.

## What this plan does

### P1 — a thumbnail per picture node (the renderer's half)

A **thumbnail service** on the renderer, `render.Thumbs`, in the shape of
the swatches and the preview:

- The GRAPH page says which nodes it wants (`thumbs.want(names)`): the
  render nodes whose output is a picture or a mask and that are on the
  canvas this frame, inside the visible part of it, and not hidden by
  **preset only**. Nothing is drawn for a page that is not shown.
- Each wanted node gets one small texture (`THUMB_W × THUMB_H`, 16:9,
  `THUMB_W = 240`, RGBA8), kept by name across frames like
  `Preview.tex`, released when the node is gone from the graph or has not
  been wanted for `THUMB_KEEP_FRAMES`.
- The capture is a **cover-fit blit** of the node's result, taken where
  the result exists: for a node with a texture of its own (scene, delay,
  echo, resize, dream, a materialised composite or effect) from that
  texture; for a node that painted into its consumer's framebuffer, from
  that framebuffer immediately after the paint, before the consumer
  draws on. `Frame` grows one hook, `frame.made(node, texture_or_fbo)`,
  called by every node at the end of its pass (today's `with
  frame.timed(name)` is the model); the hook does nothing unless the
  node is wanted and its turn is up.
- **Budget**: `THUMBS_PER_FRAME = 4` captures a frame, round robin over
  the wanted names, so a 40-node graph refreshes every ~10 frames. Each
  capture is one small blit; SYSTEM shows one `thumbs` line in the GPU
  timer. A mask thumbnail is drawn as grey.
- Outputs: output N's thumbnail is its presented frame. `outputs.Preview`
  becomes one per output (`Preview(k)`), the GRAPH backdrop keeping
  output 1's as today.
- Geometry nodes (shape, hands, clouds) have no picture. **Decision D2.**
- Value nodes (controllers, LFOs, modifiers, macros, devices) are
  unchanged by this plan.

### P2 — the node is its picture (the canvas's half)

- A collapsed picture node is its **title line and its thumbnail**, the
  thumbnail `NODE_W` wide and 16:9 (133 px at `SCALE` 1.25): **no taller
  than the five summary lines it replaces**, so every saved layout stands
  and nothing overlaps that did not before. Under the picture, only the
  node's `said` word when it has one (the warning line, as today's first
  summary line), nothing else.
- Expanded, the thumbnail stays at the top and the port rows follow it.
- The summary's other lines (the switch pick, "n params · k patched",
  the picture-port count) move to **hover**: over a node, a tooltip with
  the picture at `2 × THUMB_W`, the summary lines and the GPU time. A
  new `ui.tooltip_image(tex, size, lines)` beside `ui.tooltip`. Pins,
  stubs and cables keep their tips.
- A node whose picture is stale (dormant, off, or `reads` nothing this
  frame) shows its last picture at `DORMANT_ALPHA`, with its `said` word
  under it. A node that has never made a picture shows a plain dark
  rectangle with the node's kind word in it (not an icon: the words
  "scene", "acid.2").
- The **preset only** chip, collapse/expand, Delete, insert on a cable,
  the starters, drag and the side pane are untouched.
- The picture is the node's output, after its own pass, before anything
  its consumer does; a through (off) effect shows the picture that
  passes through it, faint.
- Plan 36's one GRAPH leftover comes here: the `acid-scene` preset draws
  a wire backwards because the area rules (`graphview.AREA`, `area_of`)
  put its source to the right of its consumer. The rule is fixed for
  where a *new* node lands; no saved position moves.

### P3 — the cable palette

Today's "by type" is right and too coarse: one red for every picture.
A cable is coloured by **what it carries, more finely**, and its pins the
same:

| carries | colour | today |
|---|---|---|
| a value (route, setter, modifier) | grey, thickness its reading | same |
| a trigger | orange | same |
| geometry | blue | same |
| a mask (cover, depth as a mask) | violet | same |
| a picture from a **media** channel, a still, a camera | amber | red |
| a picture from the **scene** or a geometry's layer | white-blue | red |
| a picture from an **effect** or a composite | teal | red |
| a trail (look-back, echo) | sand | red |
| a dream | magenta | red |
| a depth picture | the mask violet, dashed | red |

- The sub-type of a picture cable is the **kind of its source node**
  (`graphview.node_of(c.src_port).kind`, one table `PICTURE_HUES`), so
  it is decided at `graphview.build` with no renderer call; a bundle
  takes the colour of what it carries as today.
- **Red leaves the cables**: `ui.RED` is "one red everywhere" (the
  points' colour and the warning word), and a picture cable in it reads
  as an error.
- A **legend** chip on the GRAPH head (`?`) lists the colours in words,
  the one place the palette is spelled out; it is off by default.
- **Decision D3** picks between this table and a hue per source node.

### P4 — legibility from the display

The canvas already zooms, and the zoom scales fonts, pins and hit areas
together; what the install lacked was a *default* that fits the screen.
`graphview.SCALE` stays a constant, so saved layouts are the same canvas
units on every Mac, and instead:

- The canvas's **launch zoom** comes from the control window: `zoom₀ =
  clamp(content_scale × window_height / 900, 1.0, 2.0)`, so the
  MacBook's panel opens a little bigger than today and a tall rig
  monitor bigger still. It applies once per window size change until the
  user zooms; the user's zoom is kept in the show per window as the pan
  is (#246's `panned`).
- `PIN` grows to 14 and a pin's hit area to the row's height; the
  in/out stubs the same.
- The panel's font: `[ui] font = auto | <px>` in `config.toml`, `auto`
  = `ui.FONT_BASE × content_scale`-aware default; the GRAPH canvas font
  follows it. The APC40 diagram window and the desk are Dylan's and are
  not touched.
- **Decision D5** is whether the launch zoom is per Mac (the show, as
  recommended) or per preset.

### What this plan does not do

- No node is added, moved, hidden or wired by this plan. No layout runs.
- No pictures for value nodes (an LFO's waveform, a controller's
  reading as a bar) — a follow-up, noted below.
- No change to what any node *makes*: every golden stays (the thumbnail
  path is a read of a result, never a write into it). A test proves the
  frame signatures and the 757 goldens unmoved with thumbnails wanted
  for every node.
- No change to the faces, the patterns or `shape.faces` (plan 37B).

## Decisions for the owner

| # | question | recommendation |
|---|---|---|
| D1 | The picture's size on the node: 16:9 at the node's width (133 px, the summary's height) or square? | **16:9 at the node's width.** It is the outputs' shape, it is no taller than today's node, and every saved layout stands. |
| D2 | Geometry nodes (shape, hands, clouds): a live edges-only render into their thumbnail, or no picture (the words, as today)? | **A live edges-only render**, white on dark, from the scene's own camera, one more small pass under the same budget. The owner's "nodes are pictures" should hold for the shape most of all. |
| D3 | Picture cables: a hue by the source's **kind** (the table above), or a hue **per source node** (each node its own colour from a wheel, Patcher-style)? | **By kind.** Two media channels read alike, two effects read alike, and the legend fits on a chip. Per node is prettier and says nothing. |
| D4 | The thumbnail budget: 4 captures a frame, round robin (a 40-node graph refreshes every ~10 frames), or every wanted node every frame? | **4 a frame.** The GRAPH page is for wiring, not watching; the output-behind backdrop is the live picture. SYSTEM shows the cost either way. |
| D5 | The launch zoom from the display: kept per Mac in the show (with the pan), or per preset? | **Per Mac.** It is a property of the screen in front of you; a preset's layout is in canvas units and does not change. |

## Order of work

| task | what | proves |
|---|---|---|
| T1 | P1: `render.Thumbs`, the `frame.made` hook, `Preview` per output | a thumbnail per wanted node; goldens and signatures unmoved with every node wanted |
| T2 | P2: the node draws its picture; summary to hover; `tooltip_image` | a collapsed node's height ≤ today's; hover shows the lines that left |
| T3 | P3: the palette by kind, pins the same, the legend chip | no cable is `ui.RED`; two cables from a channel and a scene differ |
| T4 | P4: launch zoom from the display, `PIN` 14, `[ui] font` | the zoom at launch on a 900-px window is 1.0 and on a 1440-px one 1.6 |
| T5 | docs: this spec's "as built", ARCHITECTURE, register rows, hand checks | — |

T1 and T3 are independent; T2 needs T1; T4 is independent of all. T3
and T4 can land as their own PRs if the owner wants the palette sooner.

## Independence from plan 37B

| | 37A touches | 37B touches |
|---|---|---|
| `render.py` | a new `Thumbs` class, `Frame.made`, `_for_the_panel`, `Preview` plumbing | the face passes (`FACE_PX`, `_face_picture`, `_pattern_picture`, the swatches) |
| `graph.py` | reads `Node.OUTPUT`, `.kind`, `.reads`; one call to `frame.made` at the end of each picture node's pass | `Shape`, `PatternNode`, their ports and params |
| `graphview.py` | `VCable` colour, `height`, `summary`, the legend | `AREA`/`summary` words for the pattern node |
| `ui_graph.py` | `_node`, `_cable`, `_pin`, `_hover`, `COLOURS`, the head | nothing |
| `ui_patterns.py`, `patterns.py`, `shaders/patterns.glsl` | nothing | the browser, the modes, the GLSL |
| schema | none (the show gains a zoom per window) | `/8` (the pattern by name) |

The one shared seam is each picture node's pass calling `frame.made` at
its end (37A) while 37B rewrites the faces' and pattern's passes: whoever
merges second keeps both, one line per pass.

## Size

`ui_graph.py` (~2200 lines) and `graphview.py` (~4600) carry most of it;
`render.py` gains a class of ~120 lines and a hook; `app.py` the preview
per output. Tests: `tests/test_graph_legible.py`, `test_graphview.py`,
`test_graph_areas.py` for the canvas (headless, as `test_ui_shell.build_rig`
does it); a standalone-GL test for `Thumbs` (the precedent is
`test_ui_shell.py:655`); the goldens and `frame-signatures.json` as the
proof that nothing a node makes has moved. About the size of plan 36's
T5–T6 together.

## Hand checks (written into `11-hand-checks.md` by T5, numbered after the last group in the file when this lands)

1. **The nodes are pictures.** Load `party-trip`, open GRAPH: the scene,
   each effect, the look-back, the dream, the composite and the outputs
   each show the picture they make, moving; the shape shows its edges.
   Nothing moved on the canvas from where it was.
2. **Hover is the detail.** Hover a node: the bigger picture, the summary
   lines and the GPU time. Hover a pin: its reading, as before.
3. **The palette.** With `party-noita` loaded, a channel cable, a scene
   cable, an effect cable and a trail cable are four colours, none of
   them red; the `?` chip names them.
4. **Dormant is faint.** Close output 2: its node and the cables into it
   go faint with the last picture they had.
5. **The size fits the screen.** Launch on the MacBook alone, then with
   the rig's control monitor: GRAPH opens at a size that reads from the
   chair, and a pinch or ⌘-scroll from there is kept across a relaunch.
6. **The cost.** SYSTEM's `thumbs` line with a 40-node preset on GRAPH,
   then on another page (it should read 0 there).

## Follow-ups (not in this plan)

- Value nodes as pictures: an LFO's waveform, an envelope's shape, a
  controller's reading as a bar.
- A thumbnail on the FX page's strips and the MEDIA page's channel rows
  from the same service.
- The side pane's `_param_rows` as a hover for a value node.
