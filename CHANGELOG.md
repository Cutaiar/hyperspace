# Changelog

## v1.2 — 2026-11-01

### Graph

- Any picture node can be dropped on a cable to splice it in — composite, switch, delay, resize, dream, look-back, cut, segment, backdrop, the faces pattern, a media channel — not just effects (#307)
- Dropping a composite or switch on a cable asks which inlet takes it (under / over, in1 … in8); the others stay open (#307)
- A channel dropped on a cable feeds that port instead; the old source keeps its other cables and the line says if it now feeds nothing (#307)
- ⌘-drag lifts a wired node of any kind out of its chain and onto a cable, closing the gap behind it (#307)
- Right-click a cable → "insert ▸" offers every picture kind, not just effects (#307)
- A node that can't go on a cable says why, and only the cables that could take it dim while you drag (#307)
- Cable drag targets stay finger-sized at any zoom — at least 22 px on screen — and the drop onto a cable reaches as far zoomed out as zoomed in (#300)
- Media channels a–h are in the add menu (media ▸ channel), and the preset-only view always shows all eight, wired or not (#303)
- A node you just added is never hidden by the preset-only view, and an LFO feeding a modifier feeding a param is drawn too (#303)

### Routes

- Every new route lands with the `smooth` spring feel (0.5 s, no bounce) instead of raw; envelope routes keep auto, and saved routes are unchanged (#301)
- A band routed to a param now lands as a gentle push about its base (`LANE_DEPTH` 0.12) instead of taking the param over; an LFO lands as a push (0.25) too; toggles and menus still follow the source (#305)

### Effects

- Calmer shipped defaults — effect speeds about a quarter, amounts about a third, LFO depth 1.0 → 0.5 — so turning an effect on is no longer jarring; presets that set their own values look the same (#304)

### For developers

- The panel publishes the GRAPH page's selected node (`Panel.graph_selected`, `select_graph_node`, `graph_selected_params`) — groundwork for a controller node mode; restart, don't hot reload (#302)

## v1.1 — 2026-10-30

### Panel

- The panel's fonts ship inside the app — Inter for words, JetBrains Mono for numbers — so every machine draws the same text (#297)

### Renderer

- Effects and the cut read their own pixel exactly — a 1:1 read that landed a step off on ~0.7% of pixels now copies byte for byte (#296)

### For developers

- CI on every PR and push to `main`: ruff + the fast test tier on Linux, ~3.5 min, green off the Mac (#286)
- Vercel deploys `main` only — PR previews are gone; a manual `vercel deploy` still makes one (#294)
- Cloud sessions set themselves up like CI, and a script can drive the app's panel by control id with no person at the rig (#295)

## v1 — 2026-10-29

### Graph

- Drop a node onto a wire to splice it into the chain — the wire it will land on glows gold while you drag, everything else dims, and the pointer says what letting go will do (#292)
- ⌘-drag moves an effect that's already wired; its old chain closes over the gap, one undo step (#292)
- Deleting a modifier now bridges the chain — `LFO → Smooth → size` becomes `LFO → size` instead of a dead cable (#292)
- Delete / ⌫ removes the selected node or cable whenever the canvas is focused — a Mac's delete key finally works (#285)
- Option-drag box-selects cables — now said on the page (#292)
- Selecting the Shape node shows a live white wireframe of just the shape at the top of its side panel; it costs nothing when not shown (#283)

### Gamepad

- Preset walk moved to a 0.6 s hold on d-pad ◀/▶ — brushing past them no longer throws away the live look (#284)
- B now toggles points, X toggles screen strokes, BACK taps tempo (#284)
- Existing bindings files migrate themselves with a backup; anything you remapped by hand is left alone (#284)

### Feel

- Springs are set by duration and bounce (Apple's model) instead of frequency and damping — named feels: snappy, smooth, bouncy, wobbly, lazy (#289)
- Every feel now shows two plots: the curve of what the setting does, plus the last few seconds of the live signal (#289)
- The spring preset picker draws each option's curve on one shared axis so you can compare before picking (#289)
- Old shows convert on open and back themselves up first — restart, don't hot reload, to pick this up (#289)

### For developers

- The screenshot tools render the real frame again instead of black (#288)
- Vercel skips a deploy when the project's folder didn't change — Python-only PRs stop burning the daily quota (#290)
- New `REVIEW.md` + `/deep-review` skill: the checklist that caught a saved-show data-loss bug before merge, now runnable on every PR (#291)
