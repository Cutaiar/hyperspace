# Review — 39-T0 (edges.glsl), PR #254

**Task quality: Approved; stands alone and can go to main on its own.**
The shader meets W5 in the voice of its neighbours (eight taps at 1/u_res,
a threshold ramp, a glow that costs nothing at 0, white | source |
direction, premultiplied). The goldens are additions only: 8 `edges-scene`
entries (3 new PNGs, 5 reusing existing ones), the 741-entry digest and
`frame-signatures.json` untouched. The four test edits are the minimal
bookkeeping a new effect file and a `/7` fixture force (count + 8,
`GOLDENS_SINCE`, the no-preset allow-list, `/7` tolerated in
`test_graph_free`, `WIRED_FIXTURES`); none weakens a boundary. `@order 75`
sits between glimmer 70 and tripcolour 80 and is read only by the
migration. The PNGs show the tesseract's lines as thin white outlines on
black; the hands as edge outlines in the through state.

Taste call for the owner (AJ.7 step 4): source mode is `src × m` (alpha
included: an opaque black line on a dark edge where something is under
it); the alternative `rgb × m, alpha 0` (line-as-light) is in the
decisions row. Minors applied before merge: a stale comment in
`test_golden_frames.py`; the PR body says the fixture also carries the
hands-fx hands wires and one route.
