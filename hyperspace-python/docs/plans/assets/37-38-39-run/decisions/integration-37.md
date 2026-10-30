# integration-37: decisions

Branch `integ-37` @ 96773ca (pushed; no PR). The rows below are already written into
`docs/DECISION-REGISTER.md` as 498–500 (answer sheet and bodies) and into
`docs/DECISIONS.md` (the plan 38 table's last row).

## Register rows (written as 498–500)

**498. While held, the GRAPH page's thumbnails, their hues and their GPU times are the preview renderer's**
- **Answer** (controller — 2026-10-27, at the plan 37 merge; B3's I2, ruling 13).
- **Built:** `ui_graph.picture_sources(panel)` returns the thumbnails, output 1's picture and the GPU medians from `hold.canvas_renderer(panel)`. While held, once the preview has been drawn, the page wants nodes from the preview renderer's own `PreviewTextures`. That object is made by the preview's `Renderer` constructor, and `hold.MIRRORED` has no `thumbs`. The main renderer copies none. Hue reads and SYSTEM's thumbnails line follow the same renderer. After Take or Drop it is the main renderer again. With GRAPH closed during a hold, no preview is drawn and no thumbnail is made.
- **Other options:** keep the main renderer's thumbnails while held. Every node would then show the projector, which is not the graph the canvas draws.
- **To reverse:** one line.
- **Rough edge:** the first held frame, before the preview is drawn, still reads the main renderer (row 466's edge). The preview's thumbnails stay allocated after Take until a second has passed with nothing wanting them.
- **Judge it:** check 378, step 5 (added).

**499. While held, output 1's thumbnail is the program's picture (the PROJECTOR inset's)**
- **Answer** (controller — 2026-10-27, at the plan 37 merge; the brief's "output 1's thumbnail while held stays the program's picture").
- **Built:** output 1's node draws `panel.monitor` while held and `panel.preview` otherwise. While held, `panel.preview` carries the preview picture.
- **Other options:** draw the preview, like every other node. That would claim the projector shows something it does not.
- **To reverse:** one line.
- **Rough edge:** while held, outputs 2–4's nodes show the preview renderer's `Handoff.frame`, not their screens.
- **Judge it:** check 378, step 5.

**500. A cut shows its picture on GRAPH; a matte and a segment stay text**
- **Answer** (controller — 2026-10-27, at the plan 37 merge). C1's table test failed on plan 39's kinds (`KeyError: 'cut'`).
- **Built:** `graphview.THUMBS["cut"] = PICTURE`. A matte makes a mask, and a segment's own `OUTPUT` is `MASK` (its fg and bg are pins on the one node), so `thumb_of` already returned None for both. The table test skips `SEGMENT_PINS` the same way it skips the scene's depth pin, and asserts that matte and segment are text.
- **Other options:** draw a segment as its foreground, or a matte as white-on-black. Each needs a `THUMBS` entry and a `thumb_source` case.
- **To reverse:** one entry each.
- **Rough edge:** the dancer-cutting node shows no picture.
- **Judge it:** none (tests only).

## Hand-check change
- Check **378** (AI): added the headless `tests/test_hold_thumbnails.py`, a step 5 (with GRAPH open, before Take, look at the node pictures and then at output 1's node beside the PROJECTOR inset), and the matching *Pass*/*Fail* lines.

## As-built notes
- Merge 1 (1feddab): plan-39-vision @ 2a57af6 (T5 + T6). Code merged cleanly. The docs conflicts with plan 38's B4 docs kept both sides. ARCHITECTURE's Host row now has both plan 38's `hold.py` and plan 39's segment boundary. Numeric ordering was left for after merge 2. Fast tier after merge 1: 4141 passed, 2 skipped.
- Merge 2 (96773ca): plan-37-pictures @ d2ffa7c.
  - `ui_graph.py`: both conflicts were additive (constants; plan 38's `_hold_chips`/`hold_line` beside C2's `_tint_chip`/`tint`/`cable_tints`). `_head` came out as asked: hold chips, then plan 36's chips, then `_tint_chip(st)` last, then the HELD line. Diffing each side against the result, the only lines lost are plan 37's `if not st["backdrop"] or pv is None` (superseded by plan 38's forced backdrop) and the five `panel.renderer` reads plan 38 had already routed through `canvas_renderer`.
  - `graphview.returns`: plan 39's `c.type in (IMAGE, MASK)` plus plan 37's `kept(c, b)` function.
  - `render.py`: imports from both sides.
  - Two tests broke on the plans meeting and are fixed. The THUMBS table is row 500. `test_faces_map` failed because the generated migration map lacked plan 39's four fixtures; it was regenerated with `tools/faces_sheets.py --map` under a scratch `HYPERSPACE_HOME` (data only: `edges-scene` faces off, `cut-out` and `segment-motion` HEX on screen, `mask-as-picture` HEX unwired).
- Docs numbering: register rows 417–500 sit in numeric order under one heading, "Plans 37, 38 and 39 — pictures, the hold, vision (rows 417–500)", with each plan's own note kept as a bold-led paragraph. D-row titles are prefixed "Plan 37/38/39 D…" in both the sheet and the bodies. Rows 459, 495 and 496 lost their "at the integration merge" hedge, and the plan 39 note and header were reworded to match. Row 466's rough edge now says the thumbnails are routed (row 498). Hand checks: AH, then AI, then AJ; placeholder comments removed; one header line; "They run 1–393". TESTING-GUIDE: plan 37 keeps L174–L178, plan 38's entries are renumbered L179–L181 (table, section, intro line 56), plan 39 keeps L182–L188; order items are 21 (37), 22 (38, new, with A48) and 23 (39).
- Not verified by any person: everything on screen, above all step 5 of check 378.

## Not done / deliberately left
- `ARCHITECTURE.html` got one clause (thumbnails while held); no new diagram.
- The spec docs (`37-pictures-and-faces.md`, `38-hold.md`) got no "integration" section. Rows 498–500 and the ARCHITECTURE bullet carry it.
- 25 ruff errors stay in files this integration did not touch (`hyperspace/media/*`, `tools/ingest.py`, plan 39's bench scripts, four tests). They were already there at the base. Ruff passes on every touched file.
