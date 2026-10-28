# Plan 37 — nodes as pictures, and the faces

**Status: built (P1, P3; P2 a dry run awaiting the owner's list)** on
`plan-37-pictures`, 2026-10-27. The build is in PRs #255 (C1, thumbnails),
#258 (C2, the hover and the tint switch), #253 (C3, the backward wire) and
#250 (C4, the faces' sheets and migration map). At 48b263e the fast tier
was 4035 passed, 2 skipped, and the goldens 128 passed, with all 757
pictures unmoved. The faces' sheets and the migration map are in
[`assets/37-faces/`](assets/37-faces/) ([`sheet.png`](assets/37-faces/sheet.png),
[`heart-sheet.png`](assets/37-faces/heart-sheet.png),
[`migration-map.md`](assets/37-faces/migration-map.md)). The hand checks
are 370–376 (group AH) and the register rows 417–429 and 460. D1 is open.
The controller accepted D2–D5 as recommended, in the owner's absence.
Where the build differs from this spec is under "What changed in the
build" at the end.

The spec as written: plans 37, 38 and 39 can be cut and run in parallel
([`37-38-39-orchestrator-prompt.md`](37-38-39-orchestrator-prompt.md)).
Its source is the owner's words after the 2026-10-25 install, kept in
register row 415 ("FL Patcher-style nodes shown as the picture they make;
face shaders consolidated and faces as a target like any other") and the
install notes' items 4 and 8 (*"NOT icons on boxes — nodes ARE pictures,
like FL Studio Patcher's generator/effect images; hover gives details.
Cables coloured by data type"*; *"face shaders: consolidate to a few good
ones; faces-as-effect-target is stretch"*), plus the one bug plan 36 filed
here (the `acid-scene` preset draws a wire backwards under the area rules).
Decisions D1–D5 below are the owner's. The build took the recommendation
for D2–D5, and D1 is still open (register rows 417–421).

## What exists

- **A node on GRAPH is text.** `ui_graph._node` draws a title line, and
  collapsed (the default since N7) up to five lines from
  `graphview.summary`: param counts, "N picture ports", the node's own
  `said` words. Expanded, its ports. Cables are already coloured by type
  (`ui_graph.COLOURS`: picture red, geometry blue, mask purple, value and
  trigger for the modulation side), but a picture graph is nearly all red
  and grey, so it reads as uncoloured.
- **The one picture on the page** is output 1 as the canvas backdrop
  (`outputs.Preview`, a publisher-shaped tap that copies output 1's picture
  on frames after the page `want`ed it, into a texture the control window's
  context shares, drawn with `add_image`). Nothing draws any other node's
  picture. The MEDIA page draws channel previews from strided CPU
  subsamples (`MediaTextures.preview`), wanted only while drawn.
- **Every picture node can be asked for its texture** on the frame thread
  (`graph.picture(frame, node)` paints a painted node once a frame into a
  keyed `_frame_target`; a made node's `image(frame)`). Nothing asks unless
  a consumer does, so an unwatched node costs nothing.
- **The faces** take one picture at `shape.faces` (plan 33: the pattern, a
  channel, any branch; per face instance is "next"); the pattern node has
  17 modes (`patterns.NAMES`: FLAT, RINGS, PLAID, MOIRE, BLOOM, CAUSTIC,
  HEX, SPIRAL, CELLS, PLASMA, WEAVE, EMBER, METER, PULSE, MARBLE, TRUCHET,
  KALEIDO) in one 505-line `patterns.glsl`, eight inputs with one meaning
  each (plan 22), the FACES page (`ui_patterns.py`) choosing and tuning them.
  "Faces as a target like any other" is largely plan 33's `shape.faces`
  already: an effect branch can end on the faces. What is not there: the
  faces per instance, and a face picture on the node.

## What this plan does

### P1 — nodes are pictures

- Every node whose output is a picture (`channel`, `pattern`, `scene`,
  `backdrop`, `composite`, `switch`, `delay`, `resize`, `lookback`, `dream`,
  every effect and copy, `segment.fg`/`.bg` once plan 39 lands, a mask
  through plan 39's promotion) shows **the picture it makes** as its body,
  collapsed or not: a thumbnail at the node's width, the right aspect,
  live. A geometry node shows its scene's picture faint (it makes draw
  calls, not a picture); a hands node its layer; an output the window's
  picture; the modulation side (LFOs, envelopes, modifiers, devices) stays
  text — its reading is a number, and the N7 summary already shows it.
- **How**: the GRAPH page `want`s, each frame it draws, the ids it has on
  screen (not hidden, inside the view rect); the renderer, at the frame's
  end (`Renderer._for_the_panel`, where the MEDIA previews are made), asks
  each wanted node's picture through `graph.picture` and copies it into a
  small per-node texture (`PreviewTextures`, the long side `THUMB_PX` =
  192, mipmapped from the full picture by one blit per node, kept by node
  name, dropped when not wanted for a second). The page draws them with
  `add_image` as the backdrop is drawn. A node not on screen costs nothing;
  a node on screen costs one small blit. A node that made nothing this
  frame shows its last thumbnail dimmed, then black after a second.
- **Hover gives details**: the hover on a picture node's thumbnail is the
  N7 summary's text (what `summary` says today) plus the picture's size,
  and for a timed node its GPU time; the title line stays.
- **Cables by type, legibly**: the five colours stay; a picture cable is
  drawn with its thumbnail's dominant hue bled into its red when the
  owner's eye says so (D3), so a graph of pictures reads as what flows.

### P2 — the faces: a few good shaders

- The 17 pattern modes are judged by the owner by eye (D1) and the plan
  keeps the ones he names; the rest are removed from `patterns.glsl`,
  `patterns.MODES`, the FACES page and the presets that used them (each
  such preset migrated to its nearest kept mode with a note in its card,
  goldens re-recorded with the reason).
- The kept modes' inputs keep plan 22's eight meanings; the FACES page's
  layout is unchanged except for the shorter list.
- **Faces per instance** (plan 33's "next") is the stretch item (D4): a
  `shape.faces.<k>` port per drawn instance, so a kaleido branch lands on
  copy 1 and the pattern on copy 2.

### P3 — the `acid-scene` preset's backward wire

- Under the N9 area rules a wire from EFFECTS back into SCENE is drawn
  right-to-left. Decide (D5): either the area rules let a node sit in the
  area of its consumer when its only consumer is there, or the preset is
  re-laid by hand. Fix whichever the owner picks; a test that no factory
  preset's cable runs backwards across areas.

## Decisions for the owner

| # | question | recommendation | answer (register row) |
|---|---|---|---|
| D1 | Which of the 17 face patterns stay? (the owner's eye, at the machine, from the FACES page or `tools/preset_shots.py`'s sheets) | the build drops nothing until the owner names the list; P2 is the last task so the list can arrive during the run | **open** (417). Nothing was dropped. The sheets come from `tools/faces_sheets.py` (row 460). With the list, the owner also decides renumber or tombstones, and allows the `preset.py` edit |
| D2 | Thumbnails on every picture node always, or only on collapsed nodes (expanded ones show ports)? | **always**: the picture is the node's identity; an expanded node shows the thumbnail above its ports | (rec) accepted by the controller 2026-10-27 (418) |
| D3 | Picture cables tinted by what flows, or plain red? | **plain red first**, the tint behind a switch on the head (`pictures · tint cables`) to judge by eye | (rec) accepted by the controller 2026-10-27 (419; the tint is row 428) |
| D4 | Faces per instance in this plan, or after? | **after** (plan 33's "next", a `graph.py` change that collides with plan 39's work there) | (rec) accepted by the controller 2026-10-27 (420); not built |
| D5 | The backward wire: area rules or the preset? | **the rules**: a node whose only consumers are in one area is laid in that area; the preset then draws forward on its own | (rec) accepted by the controller 2026-10-27 (421), with the tie-break extended (429) |

## Not in this plan

- Faces per instance (D4), unless the owner says now.
- A thumbnail for the modulation side.
- Anything in `graph.py` beyond reading `picture()` (plan 39 owns new kinds
  there); anything on the GRAPH head (plan 38 owns the hold chips).

## Hand checks (group AH, 370–376)

Written out in [`11-hand-checks.md`](11-hand-checks.md) (group AH), and in
plain words in [`../TESTING-GUIDE.md`](../TESTING-GUIDE.md) (L174–L178).

- **370.** GRAPH on the laptop with a party preset: every picture node
  shows its picture, moving, and the effects' thumbnails differ from their
  inputs'. Then the tint, by eye, with the switch lit.
- **371.** The frame rate on the show Mac with GRAPH open and twenty nodes
  on screen, against SYSTEM's time before: the thumbnails' cost (and the
  tint's).
- **372.** Collapse and expand a node: the thumbnail stays (D2).
- **373.** Hover a thumbnail: the summary, the size and the GPU time.
- **374.** Hide a node with **preset only**: its thumbnail stops being
  made, and SYSTEM's copy count drops. A node behind an unpicked switch
  input dims, then goes black.
- **375.** The owner names the list from the sheets. Then the FACES page
  after P2: only the kept patterns, and a preset that used a dropped one
  shows its nearest and says so.
- **376.** `acid-scene` on GRAPH: no cable runs backwards.

## What changed in the build

The plan above is the design. This section says where the build differs
from it, or chose within it. Each ruling was made by the controller on
2026-10-27, in the owner's absence, and has a row in
[`DECISION-REGISTER.md`](../DECISION-REGISTER.md) (417–429 and 460) for
the owner to keep or overturn. Nothing in `graph.py` or `app.py` changed,
and no preset, golden or frame signature moved.

**As built, in the plan's terms.**

- **P1, the thumbnails (C1, PR #255).**
  - `outputs.PreviewTextures` sits beside `Preview` and knows nothing of
    the graph. It keeps one small texture per wanted node name:
    `THUMB_PX` = 192 on the long side, at the picture's aspect, written
    opaque.
  - `render.thumb_source` resolves what a name's picture is: the node's
    own picture through `graph.picture`, the scene a geometry is drawn
    in, the hands layer, or a window. `Renderer._thumbnails` calls it
    last in `_for_the_panel`, on the frame `_draw_frame` kept after a
    successful `evaluate`.
  - The page wants the nodes it draws whose rect overlaps the editor's
    visible canvas (`ui_graph.thumb_wants`). It never wants output 1,
    which is the existing `Preview`.
  - `graphview.THUMBS` is the one table of how each kind shows a picture
    (row 424). Any kind it does not name whose `OUTPUT` is `IMAGE` gets
    `picture`, so plan 39's `segment`, `matte` and `cut` show theirs on
    merge, with no code written for them.
  - SYSTEM gains `thumbnails · N copied · K repainted · M kept`.
- **P1, the hover and the tint (C2, PR #258).**
  - Hovering the picture gives `graphview.picture_hover`: the title,
    `summary`'s lines, `W×H picture` and `gpu N.NN ms` (row 427).
  - The chip `pictures · tint cables` is last on the head, off by
    default, and page state only (rows 419, 428).
  - Lit, red leans by 20° × sin(hue − red), with the hue read
    asynchronously, one node a frame, each node once a second.
- **P2, the faces (C4, PR #250): a dry run.**
  - `tools/faces_sheets.py` drew the sheets and the per-mode PNGs in
    [`assets/37-faces/`](assets/37-faces/), 1.5 MB in all.
  - `migration-map.md` is generated by `--map` and held to every factory
    preset and fixture by `tests/test_faces_map.py` (fast tier). It gives
    `faces_sheets.NEAREST`, three ranked neighbours per mode, and
    `nearest_kept(mode, kept)` answers for any list (row 460).
  - What the map says:
    - On screen in factory presets today: RINGS 3, MOIRE 1, CAUSTIC 1,
      HEX 2, SPIRAL 1, CELLS 1, PLASMA 4, EMBER 3.
    - With the faces off: FLAT 7, PLASMA 1, WEAVE 1.
    - Shown by no preset or fixture: PLAID, BLOOM, METER, PULSE, MARBLE,
      TRUCHET and KALEIDO.
    - 17 of the 25 factory presets put `view.pattern` on a desk knob.
  - No shader, mode, preset or golden was changed.
- **P3, the backward wire (C3, PR #253).** `graphview.laid_areas` is
  applied in `build` (rows 421, 429). In the `acid-scene` fixture, acid.2
  moves to LOOK-BACK. The sweep
  `test_no_cable_runs_backwards_across_areas` covers 25 factory presets
  and 22 graph fixtures, and N9's acid-scene exemption is gone.

**Where the build differs from the spec.**

1. **No mipmaps** (P1 says "mipmapped"). One 16-tap downsample pass with
   a sampler of its own, because `build_mipmaps` would change a
   frame-owned texture's filter, a golden risk (row 422).
2. **The box is fixed at 16:9** at the node's width, with the picture
   letterboxed inside. The node does not take the picture's aspect, so
   the layout never moves when a window resizes (row 425).
3. **Output 1 is the page's `Preview`**, not a thumbnail. Outputs 2–4 show
   their `Handoff.frame`, without the hands laid on (row 424).
4. **A collapsed picture node's N7 lines moved into the hover.** The
   collapsed body is the title and the picture (rows 418, 427).
5. **The tint is a lean, not a bleed.** Red's hue moves by at most ±20°
   and keeps its saturation and value, so a blue picture never gives the
   mask's purple (row 428).
6. **The area rule's tie-break.** The brief said "a node with consumers
   in several areas keeps today's area", but that leaves P3's own wire
   backwards: acid.2 feeds the look-back and a composite in EFFECTS. As
   built, the node goes to the leftmost consumer area not left of what
   feeds it, and only effect-area nodes move (row 429).
7. **`acid-scene` is a test fixture, not a factory preset**
   (`tests/fixtures/presets/acid-scene.json`, `/2`, migrated on load).
   Its effect feeds the look-back, not `shape.faces`. It carries no saved
   positions, and no preset was edited.
8. **The sheets come from a tool of their own** (`tools/faces_sheets.py`),
   not `tools/preset_shots.py`, which is a hand-pose tool with no mode
   axis (row 460).

**What P2 does when the list arrives.** Every step needs the owner's list
first. The full steps are in §4 of C4's decisions file, which is copied
with the run's ledger into `assets/37-38-39-run/decisions/37-C4.md`.

1. Decide the index (row 417): renumber and remap every value, which is
   schema-visible (both Macs together, the library migrated with a
   backup), or keep tombstones that a load maps to the nearest kept mode.
   The controller leans to tombstones.
2. Edit `patterns.py`'s `MODES`, `patterns.glsl`'s branches and helpers
   (then `tools/check_glsl.py`), and `ui_patterns.py` (only the shorter
   list).
3. Migrate the presets that used a dropped mode. This includes
   `hyperspace/preset.py`'s four `view_pattern=` presets and
   `tests/fixtures/factory-sources/presets/`, an edit the controller
   allows (the run's ruling 10). Each card gets "Pattern X was retired
   (plan 37); now Y". Then run `tools/faces_sheets.py --map`.
4. Re-record only the *on screen* goldens of a dropped mode, each named
   in the commit with its reason.
5. Migrate the owner's Drive library with a tool, on his say, backup
   first. The build never does this.
6. Amend DECISIONS' Face patterns row 105 ("appended, never inserted").

**Not verified by a person.**

- Everything visual: how the thumbnails read at the canvas's zooms, the
  faint shape, the dim and black ages, and the tint by eye.
- The thumbnails' and the hue read's cost on the show Mac.
- That the hover shows inside `imgui_node_editor`. Headless, it is driven
  through a stand-in.
- That the control window samples this frame's thumbnails
  (`_thumbnails` flushes after copying).
- The sheets' fidelity to the projector, and the `NEAREST` ranking (the
  controller's eye, not the owner's).
- The moved effect's area frame on a preset saved before plan 37.

**Known rough edges.**

- A node wanted for the first time is black for one frame.
- Output 1's thumbnail never dims.
- Outputs 2–4 lack the hands.
- Each painted-direct node holds a full-size target while it is wanted,
  about 8 MB at 1080p (row 426).
- A look-back asked after the capture is one commit ahead; an echo whose
  slot was just rewritten dims.
- Picture nodes laid out automatically moved once, because their height
  changed. Stored positions did not move.
- The tint lags its picture by a frame plus up to a second, and it is not
  remembered across launches.
- A moved effect does not wrap in the effects' rows of four.
- A channel that no wire reaches shows a black box.

**Known follow-ups** (none blocking).

- At the integration merge, plan 38's hold supplies "the renderer the
  canvas reads": the preview while held and drawn, else the main
  renderer. The thumbnails' `want` and `_graph` reads go through it (the
  run's ruling 13).
- Plan 38's hold chips land on the head before `_tint_chip`, in a
  one-line merge.
- `ruff check .` reports 25 errors that predate this plan, in files it
  does not touch.
