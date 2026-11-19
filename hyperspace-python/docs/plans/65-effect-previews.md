# Plan 65 — effect previews and the effect picker

**Built** 2026-11-19 on `plan-65-effect-previews` (cut from
`claude/lucid-maxwell-54j27i`, the test-card work: `testcard.glsl` and the
**card** chip on an effect's thumbnail, both kept). Register rows 892–901,
hand checks 689–698 (group EA). Draft PR to `main`; the owner merges.

## Why

There are 26 effects in `hyperspace/shaders/fx/` (27 files with the test
card), and adding one meant walking GRAPH's right-click picker to
**effects ▸** and down a list of file names — "Context Menu Tree Hell".
Many names no longer say what the effect does. The owner and Dillon want to
*see* each effect before picking it. A shader roundup will soon sort the
effects into families, so nothing here hard-codes today's list or grouping.

## What was built

### 1. The previews (`previews.py`)

`previews.EffectPreviews` puts the test card through each effect file at
the file's own defaults and keeps the pictures:

- **A still** per file: the card through the effect `STILL_T` (0.6 s) into
  its clock — at phase 0 a shake or a wave can be the plain card.
- **A loop** per file: `LOOP_FRAMES` (24) frames over `LOOP_S` (2 s) of the
  effect's clock at its default speed (12 a second), made once and kept.
  It is a cut of the clock, not a cycle: an effect's motion has no period
  in general, so the loop jumps back at its end.
- **Defaults**, with one exception: a file whose `@mix` is 0 (palette, a
  pass that starts as a no-op) is shown at mix 1, or its tile would be the
  plain card (`preview_values`).
- **Lazy and off the frame's critical path.** The picker `want`s the tiles
  it shows each frame, and the loop of the one under the pointer; the
  renderer `make`s at most `PASSES_PER_FRAME` (3) passes at its frame's
  end, in `_for_the_panel` after the thumbnails, stills before loops. A
  closed picker asks nothing and costs nothing. Opened, every still is
  made within ten frames and a hovered loop within eight more.
- **On its own state and chain.** The show's `FxState` holds only the
  effects its graph names (`FxState.hold`), so the cache runs a chain and
  an `FxState` of its own over the show's files, with the files' defaults,
  into textures of its own. Nothing of the show's is read but the files,
  nothing is written, nothing reaches an output
  (`tests/test_effect_previews.py::test_the_outputs_are_the_same_bytes_and_the_shows_values_untouched`).
- **Faithful at a tile's size.** Each pass runs at `WORK_W` × `WORK_H`
  (960 × 540), told that size, over a card drawn at it, and is shrunk
  through mipmaps into its 192 × 108 cell. The first build told a small
  picture it was 1920 × 1080 so px knobs would match the stage: an effect
  that reads its neighbours by the pixel then read between them, and Edges
  drew nothing. Now a px knob (a cell, a split) is twice what it is
  against a 1080p frame, and every effect draws as it would on stage. The
  card's Line is widened so a line is as wide in a tile as on a thumbnail.
- **Invalidated on a file change.** The cache reads the show's own
  `FxState.files`, which the chain's hot reload keeps current
  (ENGINEERING §15). A file whose program source — the file, `_lib.glsl`
  and `_common.glsl` — is not what its cells were made from has them
  forgotten and made again on the next ask; a file gone from the folder has
  its atlas freed. A file that does not compile shows the plain card, and
  `failed(name)` says why.
- **View state.** Never saved; dropped and made again after a restart or a
  reload of the renderer (`Renderer.on_reload` releases it).

**Memory.** One RGBA8 atlas a file, 5 × 5 cells of 192 × 108 (cell 0 the
still, cells 1–24 the loop): 960 × 540 × 4 = **2.07 MB a file**, so the 27
files are **56.0 MB**, kept once made, plus the card and the work picture
(2.1 MB, 2.8 MB mipmapped, and the aux disc's 2.1 MB): **62.9 MB** with every file made
(`bytes_kept`, held under 64 MiB by
`tests/test_effect_previews.py::test_every_file_fits_in_the_memory_the_plan_states`).
On the Mac's unified memory that is comfortable; a smaller loop would be
`LOOP_FRAMES` and the atlas's grid.

**The first open compiles.** Each effect's program is built on its first
pass, so the first time the picker opens after a launch the renderer
compiles up to three programs a frame at its end. On Mesa's software
rasteriser here the whole set took about six seconds of frames; on the Mac
it is for hand check 696 to say whether it shows.

### 2. The effect picker (`ui_effect_picker.py`)

The nested **effects ▸** submenu is gone from both of GRAPH's paths:

- the canvas's right-click picker: **effects…** (row `graph.pick.effects`)
  opens the picker in "add" mode, the node landing unwired where the menu
  opened, as **effects ▸ <file>** did (`ui_graph.add_render`);
- a picture cable's **insert ▸ effects…** opens it in "insert" mode, the
  effect spliced into that cable, as **insert ▸ effects ▸ <file>** did
  (`ui_graph.insert_effect`).

The dialog (`graph.effects`):

- a grid of tiles, each the effect's preview with its label under it, the
  whole tile the click target (192 × 140, up to six across);
- grouped by family, families in a fixed order, files by `@order` then
  label;
- hovering a tile plays its loop and puts its label and the first sentence
  of its tip at the foot (two lines, read on stage, not a tooltip);
- a search box with the keys from the moment it opens: every word must be
  in the label, the tip, the file name or the family (any case); Enter
  takes the first tile whose label answers, else the first tile;
- Esc or a click outside closes it.

It is an ImGui popup, so GRAPH's guard (`ui_graph._menu_up`, #452) is up
while it is open: no hover words, click, wheel or Delete reach the canvas
under it (`tests/test_effect_picker.py::test_the_canvas_under_it_is_swallowed`).
Its colours and spacing are dkit's tokens (`DARK`, `SPACE`, `RADII`). It is
drawn with ImGui widgets inside the popup, not dkit's measured menu panel:
the menu panel lays out rows, and this is a grid of pictures.

What is open, the search and the hovered tile are the page's state
(`st["graph.effects"]`), never a file, never an undo step. A pick is the
menu row's own action, so it is one undo step as it was.

**Families come from data.** `previews.family_of(spec)`: a file's own
`// @family <name>` line (`fx.EffectSpec.family`, parsed now, written by
no file yet — the hook the shader roundup fills), else the band its
`@order` sits in, from one table, `previews.ORDER_FAMILIES`:
generators (0–9), distort (10–29), split (30–49), glow and texture
(50–79), colour (80–99). A family declares nothing, so it is not in
`EffectSpec.signature` and a family change re-declares no param. When the
roundup lands, each file says `@family` and the table is a fallback.

### 3. Previews for unwired nodes

**Why an unwired node is not made.** A node with no path to an output is
*unreached*: "kept in the preset, drawn faint, never built" (register row
349, DECISIONS "Render graph without a stack"; `graph.reaches`,
`graphview.unreached`). Four reasons, from plans 33–35:

1. **Nothing hidden costs the frame.** `build_graph` builds only what a
   wire reaches (plan 35 F, its review focus 2: "Nothing hidden is
   built"); a switch makes only its picked input and an unread channel is
   not uploaded. A dozen parked effects on a canvas cost nothing on stage.
2. **The canvas and the renderer must agree.** The owner's glimmer
   (2026-10-24, row 349's amendment): an effect wired in and out of
   nothing drew on the output through a hidden placement while GRAPH drew
   it faint as "reaches nothing". Since then what is faint is never built
   and never touches an output, and both read one rule (`reaches`).
3. **State.** An unreached delay holds no buffer (plan 34 L), and a node
   that is not built holds no pool texture, so a parked node is free.
4. **The proof.** `graph.signature` fingerprints the chains behind each
   output and the order of the nodes a frame can show
   (`tests/fixtures/frame-signatures.json`); building a parked node would
   move it.

So a thumbnail cannot come from building the node. It comes the way the
test card's chip does, beside the graph: `render.unwired_through` puts the
node's input through the effect at a thumbnail's size, at the frame's end,
on the renderer's chain into the renderer's own small texture
(`card_out`), with the effect's values and clocks as the frame left them
(an unreached instance's clock already runs: `FxState.advance` moves every
held effect). The input is the picture wired into its `image` when the
frame made that node this frame (`Node.image`: nothing is painted or pulled
for it), else — no wire, or an input itself unreached — the test card
(`Renderer.card`). An effect that is off, or under the global bypass
(`fx.on`), shows its input as it is, as it would pass it through.

- The page asks `graphview.UNWIRED_PIC` for a faint effect or copy
  (`ui_graph.thumb_how`); the **card** chip still wins when lit. Its hover
  adds `graphview.UNWIRED_WORDS`.
- **Budget:** `render.UNWIRED_PER_FRAME` (4) a frame, round robin from
  after the last made (`Renderer._unwired_budget`); the others keep their
  last picture until their turn.
- **Nothing reaches an output, and the outputs are the same bytes**:
  the node stays out of `Graph.nodes`, `stats["effects"]` and
  `stats["chain_runs"]`
  (`tests/test_unwired_thumbs.py::test_the_outputs_are_the_same_bytes_and_the_node_stays_unbuilt`).

No rule of ARCHITECTURE is broken: the render graph builds nothing more,
the renderer writes no param, and the thumbnail is a picture for the
panel, as plan 37's are (§5 "Nodes as pictures").

### 4. Exported loops (stretch, built)

`tools/effect_previews.py --out DIR [--sheet] [--no-gif] [--only …]`
writes every effect's still (`<name>.png`) and loop (`<name>.gif`, 24
frames at 12 a second, looping), made exactly as the picker makes them on a
standalone context, and with `--sheet` every still on one page grouped as
the picker groups them. It refuses to write under `~/Hyperspace`.
`assets/65-effect-previews/sheet.png` and the two GIFs there are its
output.

### 5. The aux port, and a known aux in the previews (the owner, 2026-11-19)

The owner: "most of our effect nodes … have an image input and an
auxiliary input. I think for a lot of the effects, the auxiliary input
doesn't really do anything." Found:

- **Every effect node has an `aux` port**, and every copy: `graph.Effect.INPUTS`
  is `image` and `aux` for any file (plan 32 R, row 332). `_lib.glsl`
  gives every effect `aux(uv)` and `aux_luma(uv)`, transparent black while
  nothing is wired.
- **Two files read it**: **Displace** (moves the frame's pixels by the aux:
  along an angle by its brightness, or by its red and green) and **Blend**
  (lays the aux on the frame: over, multiply, screen, difference, luma
  key). The other 25 ignore whatever is wired there.

Built:

- **The port only where it does something.** `fx.reads_aux` reads the
  file: an effect has `EffectSpec.aux` when its code calls `aux(` or
  `aux_luma(` outside a comment, so a file that starts using one gains the
  port with no list to edit. GRAPH draws the aux port of an effect (or a
  copy of one) only then (`graphview.aux_shown`) — or when a saved wire goes
  into it, which still loads, is drawn and can be deleted. Nothing about
  the saved format changes, and a wire into an ignoring aux is still
  accepted by the graph as it was.
- **A known aux in the previews.** Blend and Displace are previewed with a
  known second picture wired into their aux: a warm disc, white-orange at
  its centre fading to black at its rim, clear outside it
  (`previews.AUX_FS`). Blend lays it on the card; Displace bends the grid
  inside it. Its tile carries an **aux** badge.
  The disc is drawn once, at the work size, by a program of the cache's
  own (another 2.1 MB).

## What the previews show at the defaults

The contact sheet (`assets/65-effect-previews/sheet.png`) is the honest
answer to "what does each effect do", and for about a quarter of the files
the answer at their defaults is "very little": **Fade** is level 1, **Double
vision**, **Deconverge**, **Trip colour**, **Grain** and **Shake** are at
their first-stage amounts, and **Palette** compresses the full wheel (an
identity). The previews are as asked — the file's defaults — and this is
row 901, for the owner and the roundup: give each file a line of showcase
values (say `// @preview amount=0.3 split=0.5`), parsed beside `@family`,
or leave the defaults.

## Screens

- [`assets/65-effect-previews/picker-open.png`](assets/65-effect-previews/picker-open.png)
  — the picker as it opens, every still made.
- [`assets/65-effect-previews/picker-searched.png`](assets/65-effect-previews/picker-searched.png)
  — "wave": Wave and Wave Table by their labels, Prism and Oil slick by
  their tips.
- [`assets/65-effect-previews/picker-hovered.png`](assets/65-effect-previews/picker-hovered.png)
  — Kaleidoscope hovered: its loop playing, its tip at the foot.
- [`assets/65-effect-previews/unwired-thumbnail.png`](assets/65-effect-previews/unwired-thumbnail.png)
  and [`-zoom`](assets/65-effect-previews/unwired-thumbnail-zoom.png) — the
  Kaleidoscope just added, on no wire, faint, its thumbnail the test card
  through it.
- [`assets/65-effect-previews/picker-aux.png`](assets/65-effect-previews/picker-aux.png)
  — "aux": the two effects that read a second picture, each with its
  **aux** badge and the warm disc wired in (Displace bends the grid inside
  it, Blend lays it on).
- [`assets/65-effect-previews/sheet.png`](assets/65-effect-previews/sheet.png),
  [`kaleido.gif`](assets/65-effect-previews/kaleido.gif),
  [`wave.gif`](assets/65-effect-previews/wave.gif) — the export tool.

Captured with `tools/app_driver.py tools/drive_effect_picker.py` in the
real app under Xvfb (Mesa's software rasteriser: the FPS readout says
nothing about the rig). The script opens the picker with the menu row's
own action (`open_picker`) rather than a right-click, which the tests
cover, and switches the party show's `fx.on` on in the run's scratch home:
the party show bypasses every effect, and an effect under the bypass
passes its input through, so its unwired thumbnail would be the plain
card.

## Restart or hot reload

Hot reload is enough for edits to these modules after this build is
running. Pulling this build needs a **restart**: two new modules join
`hotreload.MODULES` (`previews` after `fx`, `ui_effect_picker` before
`ui_graph`), and the renderer gains `previews` and `_unwired_last` (read
through `getattr`, so a live renderer is not broken by a reload, but the
module list is read at launch). `fx.EffectSpec` gains `family`, defaulted.

## Not built

- A right-click on the canvas driven in the tests: the tests choose the
  menu's row through `ui_menu.Menu` and drive the dialog by the mouse and
  keys; the dkit menu panel's own click is #452's.
- Seamless loops: a loop is a cut of the effect's clock.
- A preview over the scene, or over the effect's real input, in the
  picker: it shows the card, so every tile is compared on the same picture.
- Keyboard arrows between tiles: Enter takes the first match; the rest is
  the pointer's.
