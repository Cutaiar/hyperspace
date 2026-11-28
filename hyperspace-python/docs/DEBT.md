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
