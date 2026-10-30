# Changelog

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
