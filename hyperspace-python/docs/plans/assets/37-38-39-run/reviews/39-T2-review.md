# Review — 39-T2 (the mask wire and matte), PR #256

**Task quality: Needs fixes** (two Important), then merge.

Sound: a mask is R8, 0 or 1 but at a soft/feathered edge; no pass writes a
mask into alpha but `CUT_FS` (T3's); the promotion (`MaskPicture`, one per
mask node at build: white/black fitted by cover) with the reverse refused
in the matte's words, the pin and geometry/depth rules first,
`scene.cover → lookback.cover` and every factory signature unchanged; the
matte's three sources, key, soft, invert, feather (two passes only when
> 0) with real-pixel tests; `masks.py` a leaf (its own test), programs
compiled once, no texture read while written, own ping-pong keys;
`declare_mattes` on the resizes' pattern, `Frame.mattes`, the `/7` round
trip; `graphview` table entries only; the orientation test; goldens +8
(`mask-as-picture`: a white disc on black), digest and signatures
untouched (a wired fixture gets no signature case by the tool's rule —
the brief was wrong there); `ui_presets.OVERVIEW_GROUPS` excludes
`matte` as it does `resize` (necessary, disclosed).

**Important 1**: `matte → lookback.cover` is legal but the look-back
fetches its cover 1:1 at the frame's size; an own-sized input upstream
puts the cover in a corner; promoted/cut/cover readings of one mask
disagree unless it is frame-sized. Fix: the mask-port binding
(`MatteNode.image`) refits by cover to the frame's size; `CUT_FS` gets a
`u_scale`; a pixel test. **Important 2**: `Renderer.on_reload` never drops
`_mask_passes`. Minor: `own_size` as a pass-through; a promoted mask into
an occluder/over is opaque everywhere (note for AJ.6). For T5: the cable
colour at `graphview.py:1606` keys by the destination port — use MASK when
the source makes a mask; the picker item + `render_add` branch. For the
controller at integration: `"masks"` before `"render"` in
`hotreload.MODULES`, out of `cold` in `test_hotreload`.
