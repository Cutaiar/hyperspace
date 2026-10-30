# Review — 37-C1 (thumbnails), PR #255

**Task quality: Needs fixes** (one Important), then merge.

Sound: the want/drop/dim lifetime and its tests; the GL side (a
16-tap downsample with its own sampler — `build_mipmaps` would change a
frame-owned texture's filter and build a full chain per node per frame;
blend disabled and restored; errors per node; the GPU timer muted and
`frame.stats` restored during the asks); outputs byte-identical with every
node wanted, the reviewer probing delay / lookback / switch chains too;
the mapping table (`graphview.THUMBS` + `thumb_of`: geometry → its scene
faint, hands → its layer, output 1 → `Preview`, outputs 2–4 → the
handoff frame, the modulation side text); no layout runs by itself (the
"moves once" is the new node height feeding the first placement of an
unstored node; `THUMB_H` constant); ownership kept (nothing in `graph.py`,
the head, `COLOURS`, `app.py`).

**Important 1**: the `pulled` gate covered only `MAKES` nodes and effects,
so a composite / delay / resize behind an unpicked switch input was
painted for its thumbnail, pulling its inputs (the gated effect, the
unpicked channel's upload) — against P1's dim rule and plan 33 S. Fix:
gate every kind + a test. Minors: `kept` counts names not textures; the
flush reliance (fixed inside `Renderer._thumbnails`, not `app.py`);
stateful kinds in the byte-identity test; `· K repainted` on SYSTEM;
output 1's thumbnail never dims; `ui_graph.thumb_of` shadows
`graphview.thumb_of`. Collapsed picture nodes lose their N7 lines until
C2's hover lands (by design; C2 follows).
