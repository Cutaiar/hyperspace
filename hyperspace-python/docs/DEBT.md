# Debt

Every shortcut the code knowingly takes, in one place. This is the only
place a shortcut is explained. At the site in the code there is at most a
one-line pointer, `# DEBT: <slug>`.

An entry stays here until the proper fix lands. The change that lands the
fix deletes the entry and its pointers.

## Format

```
### <slug>

- **Where:** `path/to/file.py:function` (and every other site)
- **What it does now:** one or two sentences, present tense.
- **The proper fix:** what doing it right would take.
- **Cost while it stays:** what breaks, misleads or slows down because of it.
```

## Entries

### value-port-unbuilt

- **Where:** `hyperspace/graph.py:VALUE` (and `PORT_TYPES`); `hyperspace/modgraph.py:RENDER_VALUE` names it without importing it
- **What it does now:** `VALUE` is a port type beside `IMAGE`, `MASK` and `GEOMETRY`: a scalar or small vector of floats a node publishes once a frame, which the modulation graph (`modgraph.RENDER_VALUE`) may read as a source. No node declares or reads one.
- **The proper fix:** build out the palette's value output (its hue/sat/val slice and the ramp's anchors) for a lights sink, and an image-in `sample` port on the palette that sets its params from a bitmap.
- **Cost while it stays:** the node editor cannot draw value wires between render nodes.

### cloud-instances-share-params

- **Where:** `hyperspace/graph.py:cloud_nodes`, `hyperspace/graph.py:PointCloud.draw`; the `cloud.*` params in `hyperspace/params.py`
- **What it does now:** point-cloud nodes (`cloud`, `cloud.2`, ...) are all drawn from the one set of `cloud.*` view params (`ViewState.cloud_scale`, `cloud_size`, `cloud_bright`, `cloud_colors`); a second instance has no params of its own.
- **The proper fix:** give each numbered instance its own `cloud.<n>.*` params, as hands nodes have `ghost.<n>.*`.
- **Cost while it stays:** two clouds cannot be sized, scaled, brightened or tinted independently.

### segment-subject-mode

- **Where:** `hyperspace/graph.py:SegmentNode._make` (and the mode list in the class docstring); `hyperspace/view.py:SEGMENT_MODES`
- **What it does now:** `subject` is one of the `segment.mode` choices but makes no matte: `_make` refuses it with "subject is not in this build".
- **The proper fix:** a subject-segmentation worker alongside the person worker.
- **Cost while it stays:** choosing `subject` yields no matte; `fg` is the input whole and `bg` nothing.

### combobox-popup-ring-clip

- **Where:** `hyperspace/dkit/comp_combobox.py:RING_PAD` (and `combobox`, which sizes and places the popup window with it)
- **What it does now:** `RING_PAD` is 0.0, so the popup window ends at the trigger's edge. ImGui clips a window's draw list to the window, so the 3px focus ring drawn outside the field's box is cut off square when the list is open (visible only when the field was reached by Tab). Inflating the window by 6 on every side fixes the clip but leaves artifacts at the panel's top and bottom edges on a Retina Mac.
- **The proper fix:** do not put the trigger inside the popup. Draw the list as an ordinary window with `no_focus_on_appearing`, so the parent input keeps the caret, and hand-roll the dismissal and z-order the popup stack provides.
- **Cost while it stays:** a cosmetic clipped ring.

### shadow-triple-box-blur

- **Where:** `hyperspace/dkit/draw.py:_blur_layers` (used by `shadow`)
- **What it does now:** approximates a CSS blur with integer-expansion rounded rects weighted by a Gaussian. Chromium (Skia) blurs with three box passes, so the two shapes diverge most against the box's own edge. Half-step layers were tried and do not close the gap.
- **The proper fix:** model the triple box blur in the layer weights.
- **Cost while it stays:** a residual of a few levels at soft shadows (up to 7 levels on the two rows against the box's own edge for shadow-md).

### scrim-backdrop-blur

- **Where:** `hyperspace/dkit/layer.py:SCRIM` (the `blur` entry) and `scrim`; module docstring, "THE BLUR"
- **What it does now:** the browser's modal scrim carries `backdrop-filter: blur(4px)`. A draw list cannot read back the frame, so the kit paints only the 10% black wash; `SCRIM["blur"]` records the gap as a number. A dkit modal reads as less separated from the page than the browser's.
- **The proper fix:** render the page to an offscreen target, blur it and composite (a renderer change). Alternatively a heavier wash, which is an app design decision.
- **Cost while it stays:** modals are less visually separated from the page than the browser's.

### select-closed-typeahead

- **Where:** `hyperspace/dkit/interact.py:select`; `hyperspace/dkit/menu.py` (`KEY_MODEL`, pointer site)
- **What it does now:** on the real Select, typing a character with the panel shut and the trigger focused sets the value to the first label with that prefix, without opening. `interact.select` reads no characters, so a focused closed Select ignores typing. The open panel's typeahead works.
- **The proper fix:** read `input_queue_characters` in the trigger path of `interact.select` and run `next_match` over the items.
- **Cost while it stays:** a keyboard parity gap with the browser's Select.

### legacy-ghost-n-mirror-id

- **Where:** `hyperspace/params.py:SHARED_META_KEYS`
- **What it does now:** `ghost.<n>.mirror` is no param (a hands node's state follows `ghost.mirror`), but an old show may still hold the id. Shared meta is matched on an id's last segment, so `SHARED_META_KEYS` keeps classing that id as the meta controller's, and no look takes it.
- **The proper fix:** once old shows no longer carry `ghost.<n>.mirror` (a migration drops it on read), match shared meta on the exact id and drop the leftover case.
- **Cost while it stays:** shared meta is matched by last segment rather than exact id, so a future `ghost.<n>.<key>` param named `mirror` would be classed as the room's without anyone choosing it.

### family-from-order-band

- **Where:** `hyperspace/previews.py:ORDER_FAMILIES`, `hyperspace/previews.py:family_of`
- **What it does now:** the effect picker groups a file by its own `// @family` line when it has one. Otherwise it falls back to the `ORDER_FAMILIES` table, which maps `@order` bands to family names. Fewer than half the effect files declare `@family`.
- **The proper fix:** give every effect file an `@family` line and delete `ORDER_FAMILIES` and the fallback.
- **Cost while it stays:** a file's family depends on its stack position, so moving an effect in the stack can move it to another family in the picker.

### node-mode-modulators-always-give-way

- **Where:** `hyperspace/node_desk.py` (module docstring; `holding` and the `Router` plan)
- **What it does now:** while a node-mode desk holds a param, every modulator route on it (LFO, envelope, analyzer lane, sequencer, modifier) is left out of the `Router` plan, and it comes back when the desk lets go. There is no way to keep a chosen modulator running under node mode.
- **The proper fix:** a per-patch or per-controller setting that lets chosen modulators keep running while node mode holds their param.
- **Cost while it stays:** a param cannot be modulated and played from a node-mode controller at the same time.

### both-layers-modules

- **Where:** `tests/test_layer_boundary.py:BOTH_LAYERS` and `META_NAMES`; the modules listed in `BOTH_LAYERS`: `hyperspace/params.py`, `routing.py`, `routing_sources.py`, `library.py`, `undo.py`, `learn.py`, `outputs.py`, `groupwords.py`, `hot_slots.py`, `writes.py`
- **What it does now:** each of these modules holds classes of both the patch layer and the meta layer (for example `params.MetaRegistry`, `routing.MetaTable`, `library.MetaMarks`), which an import cannot tell apart. The boundary test cannot classify them as one side, so `META_NAMES` lists the meta layer's names and `test_a_patch_module_takes_only_the_listed_meta_names_from_a_module_of_both` checks what a patch module takes from them.
- **The proper fix:** split each module by layer, so the boundary test can check imports directly and `BOTH_LAYERS` and `META_NAMES` go away.
- **Cost while it stays:** the guard is by name prefix, so a meta-layer name that does not start with a `META_NAMES` prefix crosses unseen; the attribute-handle test covers only the listed handles.
