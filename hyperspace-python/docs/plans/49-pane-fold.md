# Plan 49 — the panel fold: graph always on, pages fold into the side pane

Wave 2 items U1 and U2 and wave 3 item U3 of the post-show plan
(2026-11-03): all three stages, built. Register rows 597–601, 626–632 and
668–672, hand checks 449–455 (group BF), 471–479 (group BK) and 506–509
(group BS).

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
  (`ui_presets._beside`). The held projector's inset (plan 38) sits in
  the canvas's corner left of the column, or above the band on a narrow
  page (`monitor_rect` keeps it under the room's height).

## What stage 2 does (U2)

- **Seven more sections** (`ui_pane.SECTIONS`, one row each): **fx**
  (`ui_fx.page`), **media** (`ui_media.draw`), **lfo** (`ui_lfo.page`),
  **seq** (`ui_seq.page`), **audio**, **camera**, **output**
  (`Panel._page_audio` / `_page_camera` / `_page_output`, the bodies as
  they stand — as U1 used `_page_presets`). Down the pane: selection,
  presets, fx, lookback, faces, media, lfo, seq, analyzer, audio,
  camera, output. Every new one folded at first, beside and in the band
  (rec). The ids are the pages' (`##<param id>`), under
  `push_id("pane.<key>")`; all twelve open draw with no conflicting id.
- **The FX page retired.** The rail draws no FX pill and
  `Panel._page_fx` is gone; the browser (effect nodes grouped by where
  each ends, plan 33 U) is the fx section. `ui.page`'s value is an index
  and a binding's `set` stores it, so the FX row stays in `ui.PAGES`
  (`ui.RETIRED`): landing on it — the param, a page set straight by ⌘[ /
  ⌘], GRAPH's **open on FX** chip — opens GRAPH with the fx section
  unfolded and scrolled to the pane's top (`ui_pane.focus`: a request the
  next draw acts on in its own layout, beside or in the narrow band; kept
  as a click's unfold). The hand checks that name the FX page carry a line
  saying so (retired in place, not deleted).
- **Narrow.** Checked with the panel driver at `SIDE_MIN` (240 px) and
  `SIDE_W` (320 px): no control's rect passes the pane's right edge.
  `ui.beside(w)` replaces `same_line()` where a row can spill (AUDIO's
  buttons, OUTPUT's toggles, each output block's ticks and flips — the
  ticks under the name in the pane — the band's twelve header chips,
  which wrap to rows); `Panel._section` cuts a note to what its title
  leaves. **MEDIA** goes four channels to a row (A–D over E–H) where a
  column would be under 40 px (`COL_MIN`), each column as on the page;
  **Add file…** gets a row of its own. **SEQ** keeps the eight steps
  across (the APC40's grid): under 320 px the lane column is 56 px and a
  cell may thin to 12 px (16 on the page), and the beat light and step go
  under the transport; the folded envelopes go one to a line and an open
  strip's scope sits over its knobs. **LFO**: the scope over the knobs
  where fewer than 220 px are beside it; the pickers share what
  **reset** leaves; a folded line's bar shortens. **LOOKBACK**'s cells
  go one to a row under 360 px. The pages at the panel's width draw as
  before (every page-fit test unchanged).
- **LOOKBACK redrawn** (the owner's "a horrid representation"): the page
  and the section, one function, draw plan 36's two picture nodes, each
  a head drawn as a node's band — **LOOK-BACK** (picture in → trail out;
  how far back it reaches) over what it records, its eight knobs
  (`params.LOOKBACK_KEYS`) and its echoes; **DREAM** (picture in →
  dreamed picture out; `dream.on` after its name, off passes the picture
  through) over its worker's line beside the dream buffer, the layer and
  its knobs. A head says "not on the canvas" when the loaded graph has no
  such node; its hover is the whole band, and the dream's names
  `[dream]` in config.toml as where its worker is set up. "Both" is gone: darken, contrast and detail are the
  look-back's knobs, which the dream reads (one state), and a line under
  the dream says so. The page still fits the control window.
- **Height and cost.** With many sections open the pane scrolls; a body
  scrolled out of view is not drawn (imgui skips the child). Each drawn
  body's time is a running mean (`st["pane_ms"]`); SYSTEM shows "side
  pane: …" under GRAPH's own line, the dearest first.

## What stage 3 does (U3)

- **The rail is gone; GRAPH is always drawn.** `Panel._draw` draws
  `ui_graph.page` every frame the panel is up, so `Panel.graph_selected`
  and `canvas_px` are live on all of them. `ui.RETIRED` is gone: FX is a
  section like the rest.
- **`ui.page` is the focus.** Same param id, same sixteen slots in the same
  order (`ui.PAGE_KEYS`; `Panel.page` its one owner), labelled "Focus section": a saved index names the
  section of the name its page had; GRAPH's slot (10) has no section and
  lets go of the focus, scrolling the pane to its top. `Panel.go_page` is
  the setter; `_draw` sees an index set straight (`app.frame`'s ⌘[ / ⌘],
  which is untouched: it still sets `panel.page`). A click that lets go moves
  it to GRAPH's slot; selecting a node does not move it.
- **Four more sections**: view, hands, routing, system, folded at first.
  Down the pane: selection, presets, view, fx, lookback, faces, media, lfo,
  seq, hands, routing, analyzer, audio, camera, output, system. No page
  stays.
- **The focus leaves the fold alone** (row 669, changing the end of 627): a
  focused section shows however it is folded and goes back when the focus
  moves on; nothing is written.
- **Its room** (row 670): its header at the pane's top, its body down to the
  headers after it. In the narrow band: alone, the band all but `CANVAS_MIN`
  of the page; a click on a chip lets go.
- **A picked desk control** (row 672): the canvas and the bodies dim, ROUTING's
  not, the headers live.
- **The cost.** `panel.draw`'s CPU time on the Mac, the party show through
  `tools/app_driver.py` at 2372 × 900, no devices: GRAPH alone 3.0–3.3 ms (as
  before); a section focused 2.0–3.4 ms, where its page alone was 0.8–1.7 ms.
  So up to about 2 ms a frame more while a section is focused, none while
  nothing is. The extra GL of drawing the canvas is not in that number (hand
  check 509).

## What stays

`ui.page`, the page history, the cheat sheet, the desk and pad diagrams. Keys and Learn act on a section's widgets as on
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
- **626** — stage 2's seven sections, their order, all folded at first.
  (rec)
- **627** — the FX page retired, its `ui.page` slot kept and opening
  GRAPH with the fx section unfolded. (rec)
- **628** — narrow layouts: rows wrap (`ui.beside`), notes cut, cells and
  folds one to a row, scopes over knobs. (rec)
- **629** — MEDIA four channels to a row under 40 px a column. (rec)
- **630** — SEQ eight steps across, a 56 px lane column and 12 px cells
  at the narrowest. (rec)
- **631** — LOOKBACK as the two picture nodes, "both" named as the
  look-back's grade the dream reads. (rec)
- **632** — SYSTEM's per-section cost line. (rec)

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
  Round 2: a fold clicked before the library attached kept over the
  file's (`pane_clicks`); the projector's inset above the narrow band.

## What changed in the build (stage 2, U2)

- `hyperspace/ui_pane.py`: seven rows in `SECTIONS` (bodies `_fx`,
  `_media`, `_lfo`, `_seq`, `_audio`, `_camera`, `_output`),
  `DEFAULT_OPEN` from the keys, `focus`, `timing_line`, `_body` timing
  each body (`pane_ms`), `pane_focus` acted on in either layout, the band's header chips
  wrapping (`_header(first=)`).
- `hyperspace/ui.py`: `RETIRED`, `Panel.go_page` (`ui.page`'s setter,
  and `draw` for a page set straight), the rail skipping retired rows,
  `_page_fx` dropped (and `ui_fx` no longer imported), `beside`,
  `check_w`, `NAME_ROOM`; `_section`'s note cut to fit; the AUDIO,
  CAMERA and OUTPUT bodies' rows wrapping; SYSTEM's side pane line.
- `hyperspace/ui_lookback.py`: the page redrawn (`SECTIONS` by node,
  `PORTS`, `GRADE_LINE`, `_node_head`, `_dream_word`, `_held`,
  `_dream_thumb`, `TWO_UP`); `_status` dropped.
- `hyperspace/ui_media.py`: `COL_MIN`, the channels four to a row,
  **Add file…** wrapping. `hyperspace/ui_seq.py`: `ROOMY`,
  `LANE_W_NARROW`, `CELL_MIN`, `BESIDE_SCOPE`, the lane width passed
  down, the transport's light wrapping, fitted strip heads.
  `hyperspace/ui_lfo.py`: `BESIDE_SCOPE`, `fit_micro`, the strip's
  pickers sized to the room, the folded line's bar.
- `tools/lookback_page_shots.py`: its labels table reads `SECTIONS` as
  it now is (one line).
- Tests: `tests/test_ui_pane.py` (the stage-2 sections at 240 and 320 px,
  MEDIA and SEQ in the pane, the redrawn lookback, the FX retirement,
  `focus`, the cost line; U1's band test now says the chips wrap, the
  late-library test reads the fold, the click test opens the lookback
  section alone in a tall window); `tests/test_lookback.py` (the two
  nodes); `tests/test_fx.py` (the browser at the panel's size, not the
  retired page); `tests/test_ui_shell.py` (the page loops skip the
  retired FX).
- Restart, not hot reload: `Panel.go_page` is new and `ui.page`'s setter
  is bound at launch; `ui_pane` imports four more page modules.
- **Review fixes** (PR #350, one round): 1 `focus` a pending request the
  next draw unfolds and scrolls to in its own layout (the band had
  ignored it); 2 a node head's hover the whole band; 3 the track readout
  measured as printed; 4 MEDIA's and SEQ's flush-right rows through
  `ui.beside`; 5 `ui.fit_micro`, one helper for four callers; 6 the
  look-back's node names asked once per graph; 7 `[dream] in config.toml`
  back on the dream's hover; 8 `ui_pane.timing_line(panel)` fetches the
  state itself.

## What changed in the build (stage 3, U3)

- `hyperspace/ui.py`: `_rail`, `RAIL_W`, `RETIRED` gone, `PAGES` now
  `PAGE_KEYS` alone (the groups are `ui_pane.SECTIONS`) (`RAIL_DOT_R` is
  `HEADER_DOT_R`); `_draw` always GRAPH, `_focus_seen`; `go_page` is the focus;
  the `Panel._page_<key>` methods stay as the sections' bodies; VIEW's and
  SYSTEM's rows through `beside`, `SLIDER_MIN`.
- `hyperspace/ui_pane.py`: four rows; `_paged`, `_wrapped`; `section_of`,
  `focused`, `scroll_to`, `let_go`, `shown` (`focus` gone); `draw`'s focus
  handling and headers' height; `_body` dims; `pane_last` for `timing_line`
  (the line asks mid-draw).
- `hyperspace/ui_graph.py`: `_dimmed`, `band_height`, `details_rect(band_h)`;
  the sections drawn with no router.
- `hyperspace/hands/panel.py`, `ui_routing.py`, `ui_presets.py`: the narrow
  rows (row 671). `ui_desk.py`: the words.
- `tools/app_driver.py`: `sys.argv` cleared before `app.main()` (the tool had
  stopped running when the app grew `--laptop`); its docstring,
  `tools/drive_instances.py` and the `drive-the-app` skill say sections, not
  tabs. Every other tool sets `ui.page` and still lands. `tests/ui_driver.py`:
  `Driver.reveal`, each action scrolling its control into view first.
- Tests: `test_ui_shell.page_frame`, a section's body alone in a window the
  size a page was, for the body tests (layout, clicks); the height-fit tests
  removed; the real route is `frame` and `tests/test_ui_pane.py`, with
  `test_every_section_focused_lands_in_view_and_inside_the_pane` as the rule
  now. `test_ui_driver.py` runs the real route in a tall window.
  `test_graph_edit.py::test_a_channel_dropped_…` waits out the editor's glide
  to the selection: its drag raced the glide, and reproduces on the base build
  (fails there at a 1712 px page; passes at 1600 px with the rail).
- Restart: `Panel.__init__` has a new field and the param's label changed.
- **Review fixes** (PR #360, one round): 1 a chip hidden by the focus unlit and
  opening what it asks for; 2 the spacing after each open body counted (no
  scrollbar on a fresh launch); 3 the pick's words ask `ui_pane.shown`; 4
  `Panel.page` the one owner of the focus (`let_go`); 5 `select_id` no longer
  moves the focus; 6 the macro row's room counted once; 7 the false words
  (`off page`, `POINTER`, the desk's close, the show's name, `OPEN_TIP`, the
  "on the GRAPH page" tips); 8 the band scrolls on a focus; 9 `REVIEW.md`,
  `ARCHITECTURE.md`, the fit tests; 10 `PAGE_KEYS` names only, the groups in
  `SECTIONS`. Found by the new test: ANALYZER's band row wraps at 240 px.

## After the plan: one viewer (2026-11-07)

Dillon, 2026-11-07: with every page folded in, the open sections shared
the pane and each got a couple of hundred pixels. The folds and the focus
are replaced by **one view at a time**, at the pane's full height
(`ui_pane.draw`, DECISIONS "The side pane is one viewer"):

- **The view is `ui.page`.** GRAPH's slot is the selection, every other
  slot its section (`showing`, `section_of`, `slot_of`, `show`). Every way
  a view comes up goes through it, so ⌘[ / ⌘] walk all of them. The
  history keeps the selection's view with its node (`ui.view_of`,
  `ui.go_view`): back from node B to node A selects and centres A. A step
  waits a few frames for its node to land (`ui.SETTLE_NOTES`); a node
  deleted since leaves what landed in its place, the forward run kept.
- **Every view has a mouse route.** A row of chips: the selection and the
  six sections no node's **open on …** leads to (`TABS`), then
  **sections ▾**, a menu of the other eleven (`MENU`). The menu's chip
  names the view while it is one of them; dirty dots on the chips and the
  rows. **open on …** shows the node's section with a **← <node>** chip
  back.
- **A click on the canvas shows the selection** (`ui_graph._note_pick`):
  pressed and let go on the canvas, not over the pane, no menu open, no
  desk control picked, and something selected after it. A selection by
  code leaves the view.
- **Gone:** the fold state and its file (`opened`, `set_open`,
  `read_open`, `write_open`, `flush`, `DEFAULT_OPEN`, `DEFAULT_BELOW`,
  `LAYOUTS`), the shared heights (`body_height`, `MIN_BODY_H`,
  `FRESH_BODY_H`), `focused`, `scroll_to`, `let_go`, `draw`'s `below`.
  `pane.open` and `pane.below` stay in an old `ui.json`, unread.
- **Tests:** `tests/test_ui_pane.py` — every view by the mouse alone,
  one route each, a real canvas click, open on … and ←, ⌘[ / ⌘] through
  views brought up every way, the body at the pane's full height, no
  conflicting ids view by view, the band; the fit tests unchanged
  (`test_every_section_focused_lands_in_view_and_inside_the_pane`). Hand
  checks 629–632 (group DO).
- Restart after pulling: `Panel.go_page` and the param's label changed.

