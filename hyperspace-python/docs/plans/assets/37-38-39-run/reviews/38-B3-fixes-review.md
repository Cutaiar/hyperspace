# Verification — plan 38 B3 fixes, PR #259 (b4ebba9)

C1 fixed as ruled: the hook `hold.keep(kind, names)` in
`GraphSection._settle` (fx, switch, resize, lookback), `land` → `_settle`,
`settle()` re-runs it; `put` routes `fx.hold` through it; held names
snapshotted at engage; Take releases then settles the live set; Drop
releases before the revert; 12b's `_values` drops `program_only()`;
nothing in fx.py/params.py; phase continuity pinned; the four C1 tests
fail with `keep` as identity (checked). I1: the reset to the hold while
held, the program's at Take only if loaded. I2: `hold.canvas_renderer`
over five reads (`view_of`, `render_edit`, `edit_of`, `graph_words`,
`dormant_lines`); `_canvas`/`_node` untouched. M1/M3/M5/M8 as claimed.

**Important I-a** (sent back): undo marks taken while held record
`fx.held` incl. the kept instances; after Take ⌘Z re-creates them and a
save writes dead ids. Fix in `mark()`; a test.

Integration notes (the controller's, at the 39 and 37 merges):
- plan 39: `declare_mattes`/`cuts`/`segments` must move from `land` into
  `_settle` through `keep`, with keys in `names()` (both branches) and
  the no-spec dict, and entries in `Hold.program_only`'s table.
- plan 37: `ui_graph.py` `st["thumbs"] = panel.renderer.thumbs` and the
  timing line read through `canvas_renderer`; the preview renderer then
  has its own `PreviewTextures` (two sets while held).
