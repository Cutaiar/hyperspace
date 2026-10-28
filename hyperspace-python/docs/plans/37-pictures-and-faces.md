# Plan 37 — nodes as pictures, and the faces

**Status: draft spec, not built (2026-10-27).** Written so plans 37, 38
and 39 can be cut and run in parallel
([`37-38-39-orchestrator-prompt.md`](37-38-39-orchestrator-prompt.md)).
Its source is the owner's words after the 2026-10-25 install, kept in
register row 415 ("FL Patcher-style nodes shown as the picture they make;
face shaders consolidated and faces as a target like any other") and the
install notes' items 4 and 8 (*"NOT icons on boxes — nodes ARE pictures,
like FL Studio Patcher's generator/effect images; hover gives details.
Cables coloured by data type"*; *"face shaders: consolidate to a few good
ones; faces-as-effect-target is stretch"*), plus the one bug plan 36 filed
here (the `acid-scene` preset draws a wire backwards under the area rules).
**Decisions D1–D5 below are the owner's and are open**; the build takes
the recommendation for each unless told otherwise.

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

| # | question | recommendation |
|---|---|---|
| D1 | Which of the 17 face patterns stay? (the owner's eye, at the machine, from the FACES page or `tools/preset_shots.py`'s sheets) | the build drops nothing until the owner names the list; P2 is the last task so the list can arrive during the run |
| D2 | Thumbnails on every picture node always, or only on collapsed nodes (expanded ones show ports)? | **always**: the picture is the node's identity; an expanded node shows the thumbnail above its ports |
| D3 | Picture cables tinted by what flows, or plain red? | **plain red first**, the tint behind a switch on the head (`pictures · tint cables`) to judge by eye |
| D4 | Faces per instance in this plan, or after? | **after** (plan 33's "next", a `graph.py` change that collides with plan 39's work there) |
| D5 | The backward wire: area rules or the preset? | **the rules**: a node whose only consumers are in one area is laid in that area; the preset then draws forward on its own |

## Not in this plan

- Faces per instance (D4), unless the owner says now.
- A thumbnail for the modulation side.
- Anything in `graph.py` beyond reading `picture()` (plan 39 owns new kinds
  there); anything on the GRAPH head (plan 38 owns the hold chips).

## Hand checks (group AH, numbers assigned in the orchestrator prompt)

1. GRAPH on the laptop with a party preset: every picture node shows its
   picture, moving; the effects' thumbnails differ from their inputs'.
2. Frame rate on the show Mac with GRAPH open and twenty nodes on screen,
   against the SYSTEM page's time before: the thumbnails' cost.
3. Collapse and expand a node: the thumbnail stays (D2).
4. Hover a thumbnail: the summary, the size, the GPU time.
5. Hide a node ("preset only"): its thumbnail stops being made (the
   SYSTEM line's blit count drops).
6. The FACES page after P2: the kept patterns only; a preset that used a
   dropped one shows its nearest and says so.
7. `acid-scene` on GRAPH: no cable runs backwards.
