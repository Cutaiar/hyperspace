# Review — 37-C2 (hover and the head switch), PR #258

**Task quality: Needs fixes** (one Important), then merge.

Sound: the hover text from the model (`graphview.picture_hover`: the N7
summary + `W×H picture` + `gpu N ms` looked up by the render node's
name), shown only when the editor's hovered node and the thumbnail's
`is_item_hovered` agree (the pattern the node's + button already uses);
the switch off by default, page-only state like `patched_only`/
`backdrop`/`preset_only`, proven not to reach the preset or the show
file; one line `_tint_chip(st)` last in `_head` (plan 38's hold chips go
above it, so the merge is clean); the tint a pure hue rotation of at
most ±20° keeping red's saturation and value, `COLOURS` unchanged; the
hue a chroma-weighted circular mean (grey pictures stay plain red); reads
one node a frame, each once a second, only while asked; nothing in
graph.py/app.py/render.py/hold.py; no golden; 11 new tests asserting
content.

**Important**: the hue read is a synchronous `tex.read()` at the end of
the render frame — a full CPU–GPU wait on each reading frame while the
switch is lit, and the row claimed it was free. Fix: a tiny downsample
target + `read_into` a Buffer, read back a frame later; the row's cost
corrected; an fps line in AH.1. Minors: the lean follows distance from
red, not warmth, and cyan sits on a ±20° discontinuity (reword or a
continuous mapping); AH.4 names the hover fallback; reads continue for
the drop grace after the switch goes off.
