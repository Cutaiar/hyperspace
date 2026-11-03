# Changelog

## v1.2 — 2026-11-02

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
- Right-click a picture cable → starters ▸ feedback splices in a trail loop (composite laid over, a one-frame delay, the new `fade` effect at 0.75); a picture node's menu has "add feedback after" too — one undo step, as many loops as you like (#319)
- Groups behave: ungrouping no longer hands the old number to the next group, a deleted node leaves its group at once, and undoing the delete puts it back in (#321)

### Media

- The GRAPH canvas is a live source: MEDIA → Live → `panel:graph`, put it in a channel and wire it anywhere a picture goes — the projector, or the backdrop behind the canvas for a loop; off the page it holds 1 s, then reads black (#313)
- Videos can play their sound: each channel has an `audio` toggle and a gain slider (off, then −30 … +6 dB) on MEDIA, mixed into one output that follows the transport; SYSTEM shows a `media sound` line; an occasional click at rate 1 is expected for now (#316, #324, #329)
- The segment node no longer leaks memory — two segment nodes over a long set had grown the app to 140 GB and frozen the Mac (#310)

### Gamepad

- The DualSense Edge works over USB and Bluetooth: touchpad, back and Fn buttons, motion, light bar, rumble, trigger resistance, player lights — new `touch:` and `motion:` sources and `<role>:0`–`8` output ports, all in Learn pad (#306)
- Any controller can fill any role: a gamepad entry's `controller =` takes `any`, a model (`edge`, `dualsense`, `xbox`, `x360`), a family (`sony`, `xbox`) or a USB id (#306)
- The Joy-Con (L or R) connects over Bluetooth, one per role, with its six-axis sensor, stick drift calibrated, HD rumble and player lights (`controller = "joycon-l"`) (#315)
- The pad window has four views — Map, Faithful, Lanes, Cockpit — picked with Pad view on SYSTEM or by clicking the view's name in the pad window's header (#312, #315)
- Experiment: the Joy-Con as a 4D totem — its gyro turns the shape's rotation planes, X / Y / B swing one into W, A resets, tilt pans; switch it on with "totem off" in the pad window's header or `[totem] on = true` (#330, #335)

### Routes

- Every new route lands with the `smooth` spring feel (0.5 s, no bounce) instead of raw; envelope routes keep auto, and saved routes are unchanged (#301)
- A band routed to a param now lands as a gentle push about its base (`LANE_DEPTH` 0.12) instead of taking the param over; an LFO lands as a push (0.25) too; toggles and menus still follow the source (#305)

### Effects

- Calmer shipped defaults — effect speeds about a quarter, amounts about a third, LFO depth 1.0 → 0.5 — so turning an effect on is no longer jarring; presets that set their own values look the same (#304)
- Fine control at the low end: every effect's `speed` and fourteen amounts are on new tapers, so 0.05× and 5 % are a few knob steps instead of under one; saved routes onto them are converted at load and reach the same values (#322)
- A knob turned an hour into a set no longer throws the picture somewhere else — warp's drift and scale, tripcolour's pulse, RINGS' colour and the field's and media path's rates now change speed without a jump (#325, #326, #328)

### For developers

- The panel publishes the GRAPH page's selected node (`Panel.graph_selected`, `select_graph_node`, `graph_selected_params`) — groundwork for a controller node mode; restart, don't hot reload (#302)
- `tools/calm_lanes.py` holds every preset's band routes to the new depth, as springs; `tools/retaper_routes.py --write` rewrites a library for the new tapers — run it before the next show (#311, #322)
- One `Deck` bundle built by `Deck.build` (`Host.deck`, `Panel.deck`), no behaviour change — the first step of plan 44's decks; restart, don't hot reload (#327)
- A hung test fails by name instead of stalling the run, and live-device tests take turns across processes (#331)
- The panel driver's Ctrl is the key imgui reads as Ctrl, so it types on a Mac (#309)

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
