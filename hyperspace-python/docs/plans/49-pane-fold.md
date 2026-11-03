# Plan 49 — the panel fold: graph always on, pages fold into the side pane

Wave 2 item U1 of the post-show plan (2026-11-03): stage 1 of three.
Register rows 597–601, hand checks 449–455 (group BF).

## The ask

The build-order doc's row "Graph always on, pages fold into the side
pane": the time at a show is spent on GRAPH (the owner, 2026-10-26: the
app opens there, the desk down), and every other page is a trip to the
rail and back. The side pane PR #266 made resizable opened only while
something was selected; it becomes the one place the rest of the panel
folds into, in three stages. The fold was Dillon's lane and never
started; on 2026-11-03 the owner gave it to us, on its own schedule.

## The three stages

1. **U1, this plan: the pane always on, five sections.** On GRAPH the
   side pane is drawn with or without a selection and holds folding
   sections: **selection** (what the pane showed before), **presets**,
   **lookback** (the dream), **faces**, **analyzer**. Every page and the
   rail stay as they are.
2. **U2: the rest fold in.** Media, fx, LFO, sequencer, audio, camera
   and output become sections; the FX page is retired (its browser is
   GRAPH's effects already). The owner's note for the lookback section
   (2026-11-02): the LOOKBACK page's split into look-back / dream /
   shared is "a horrid representation of what's going on there" — stage
   2 redraws it as what the two nodes are (plan 36's look-back and dream
   as two picture nodes), not stage 1, which draws the page as it is.
3. **U3: the rail goes.** With every page a section, the rail is
   removed and `ui.page` becomes "focus section": the param a key row, a
   pad or ⌘[ / ⌘] moves unfolds and scrolls to a section instead of
   switching a page. GRAPH is then always drawn, so `Panel.graph_selected`
   is live on every frame (today it is as of the last frame GRAPH drew).

## What stage 1 does

- **The pane is always on** (`ui_graph.page`): `details_rect` and
  `over_details` are set every frame, so a right-click or a wheel over
  the pane is the pane's on every frame, as it was while something was
  selected. Its width and memory (`graph.side_w` in `<machine>/ui.json`)
  are #266's; the grip is a hit test of its own on the column's left edge,
  not an item inside the scrolling column (review fix 1). On a narrow page
  it is #266's `BELOW_H` band under the canvas, and the **details beside /
  below** chip now shows whenever the page is narrow. The held projector's inset
  (plan 38) sits in the canvas's corner left of the pane, not under it.
- **Sections** (`hyperspace/ui_pane.py`): a header each — ▾ / ▸, the
  title in the micro face, the rail's dirty dot where the section's
  group has moved off its preset; the selection's header names what is
  selected. A click folds or unfolds it. Beside the canvas the open
  sections share the pane's height evenly, never under `MIN_BODY_H`
  (160 px; past that the pane scrolls). In the narrow band the headers
  are one row of chips and the open sections share the rest with no
  floor, so one open section has the whole band. Each body is a child of
  its own and scrolls by itself.
- **No page code is duplicated.** A section's body is the function its
  page draws — `Panel._page_presets`, `ui_lookback.page`,
  `ui_patterns.page`, `Panel._page_analyzer` — named in its row of
  `ui_pane.SECTIONS` (key, title, the rail's groups, the body), so a
  section U2 adds is one row. The page is the section at full height.
- **Selection** is `ui_graph._side`, as before; with nothing selected the
  section says so in words. Only a click folds or unfolds it: a
  selection leaves the fold alone, and a folded selection's header names
  what is selected (review fix 7).
- **Ids.** A widget in a section carries the label it carries on its
  page (`##<param id>`), so `tests/ui_driver.py`, Learn's framing and the
  right-click menu find it by the same id. Each body is drawn under
  `push_id("pane.<key>")` inside the pane's child, so imgui's own ids (the
  label hashed under the id stack) never collide between a section and
  its page, or between two sections that both draw a preset strip. A page
  and its section are never on screen together: the pane is on GRAPH.
  Headers are `##pane.<key>`.
- **Fold state** is this Mac's, in `<machine>/ui.json` beside
  `graph.side_w`: `pane.open` for the column beside the canvas
  (selection and presets open at first) and `pane.below` for the narrow
  band (selection alone at first). `read_doc` / `write_doc` are the
  library's own tolerant read and atomic write (`library._read_json`,
  `_write_text`), shared with the width. A click is written half a second
  after the last one (`ui_pane.flush`), and `ui_graph.close` writes what
  is left. A library attached after GRAPH first drew is read the first
  frame the machine is known. A bad file costs only the memory.
- **Narrow strips.** Two things the pages never needed at their width:
  the preset strip's name button is squeezed to what is left beside its
  chips (`ui_presets.strip_name_w`, never under 48 px; `name_w` where it
  fits, so every page draws as before) — the presets strip's **N devices
  missing** chip budgeted beside ▶, or on a row of its own under the
  strip when even a squeezed name leaves no room — and the show line's
  chips start a new row where they would pass the edge
  (`ui_presets._beside`).

## What stays

Every page, the rail, `ui.page`, the page history, the cheat sheet, the
desk and pad diagrams. Keys and Learn act on a section's widgets as on
the page's (the same params, the same `_ctx` menu). The graph's content
is untouched: the pane is panel chrome laid over the canvas, not graph
content — no node, edge or position is added, hidden or laid out
(DECISIONS "The WYSIWYG graph").

## Decisions

- **597** — the pane always on, five sections, page bodies shared, ids
  kept by label with a `push_id` per section. (rec)
- **598** — the fold state per Mac in `ui.json`, one per layout:
  beside, selection and presets open by default; in the narrow band,
  selection alone. Only a click unfolds; written half a second after the
  last click. (rec)
- **599** — beside, open sections share the pane's height evenly, 160 px
  at least; in the narrow band, headers in one row and no floor; each
  body scrolling by itself; the details chip on every narrow page. (rec)
- **600** — the strip's name squeezed (the devices chip budgeted or
  wrapped) and the show line wrapped in a narrow pane; the held
  projector's inset left of the pane. (rec)
- **601** — section titles follow the rail's words (`lookback`, not
  `dream`); the lookback section draws the page as it is until stage 2.
  (rec)

## What changed in the build

- `hyperspace/ui_pane.py` (new): `SECTIONS` (each with its body),
  `DEFAULT_OPEN`, `DEFAULT_BELOW`, `draw`, `read_open` / `write_open`,
  `read_doc` / `write_doc`, `opened`, `set_open`, `flush`, `body_height`.
- `hyperspace/ui_graph.py`: the pane drawn every frame (`page`), the
  machine asked until a library is attached, `_grip` as a hit test with
  no item, `wants_chip_w`, `_wants_chip(beside=)`, `sel_words`,
  `read_side` / `write_side` over `ui_pane.read_doc` / `write_doc`, the
  monitor inset beside the pane, `close` flushing the fold.
- `hyperspace/ui.py`: docstrings only (`_page_presets` and
  `_page_analyzer` are the section bodies as they stand).
- `hyperspace/ui_presets.py`: `strip_name_w` (with the devices chip),
  `NAME_MIN`, `_beside`.
- `hyperspace/hotreload.py`: `ui_pane` on the watched list, before `ui_graph`
  (the one line outside U1's files; `tests/test_hotreload.py` requires it).
- Tests: `tests/test_ui_pane.py` (new); two tests whose premise was "no
  pane without a selection" now say the pane is on
  (`test_graph_legible.py::test_beside_shows_on_a_narrow_page_selected_or_not`,
  `test_media_panel.py::test_canvas_px_is_recorded_only_while_graph_draws`).
- A new module: restart, not hot reload.
- **Review fixes** (PR #345, one round): 1 the grip a hit test outside
  the scrolling column's items; 2 the narrow band's own fold
  (selection alone), headers in one row, no floor; 3 the header
  measured in the micro face; 4 the machine asked until known, the fold
  read then; 5 the devices chip budgeted or wrapped; 6 the library's
  atomic write and tolerant read; 7 no unfold on a selection, the write
  deferred; 8 the bodies in `SECTIONS`, the page wrappers dropped.
