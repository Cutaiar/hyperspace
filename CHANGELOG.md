# Changelog

## v2 — 2026-10-30

### Panel

- The panel's fonts now ship inside the app — Inter for words, JetBrains Mono for numbers, DejaVu behind both for symbols — so the Mac, Linux and CI all draw the same text (#297)
- A missing media source's banner no longer clips "shows black"; long source ids shorten, the ending stays whole, and the hover keeps the full sentence (#297)

### Renderer

- Effects and the cut read their own pixel exactly (`texelFetch` when the read is the target's size) instead of through the smoothed sampler — a 1:1 read that landed a step off on ~0.7% of pixels is now byte for byte (#296)

### For developers

- CI on every PR and push to `main`: ruff + the fast tier on Linux under Xvfb, ~3.5 min, green — including a real bug fix (Mesa's GLSL error format is now parsed) and the end of the OOM that hung runs at ~99% (one shared GL-context fixture; workers peak ~1 GB, not 4) (#286)
- Vercel deploys `main` only — the 100-deploys-a-day free quota stops running out; PR previews are gone, a manual `vercel deploy` still makes one (#294)
- Cloud sessions set themselves up like CI — the session-start hook installs the system libraries, runs a slim `uv sync`, and starts Xvfb (#295)
- Drive the app with no person at the rig: `tests/ui_driver.py` works the panel by control id, `tools/app_driver.py` runs the same actions in the real app and captures both windows, and the `drive-the-app` skill says when to use which (#295)

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
