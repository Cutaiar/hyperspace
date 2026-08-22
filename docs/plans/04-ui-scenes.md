# Plan 04 — UI & scenes

**Blueprint stage 4.** The native control surface: everything reachable in
the HTML panel becomes reachable in the imgui overlay, in the same visual
language.

## Prerequisites

Plans 01–03 complete (the UI binds to `bands.py` parameters and `audio.py` /
`djlink.py` / `imu.py` state — all of which must exist to bind to).

## Deliverables

```
hyperspace/ui.py         # imgui overlay in the render window
hyperspace/transport.py  # file playback: play/pause/restart/position
tests/test_ui_state.py   # state-machine tests (no pixel tests)
```

## Tasks

### 1. Panel structure

`imgui-bundle` drawn in the plan-02 GL window. Port the HTML drawer's
contents: shape selector with the large cell-count readout, brightness,
speed, plane toggles, audio source controls, the six band strips, scene
dropdown, master gain, Dynamics slider, transport.

### 2. Band strips — the semantics are the hard part, port them exactly

- **Meters:** input (white, post-coupling) and output (red, post-drive),
  reading 0..`CEIL` with the NOM line at 38.5% and the KNEE line at 48.1%,
  three-shade tinting (working / headroom / knee), and the over-drive
  annunciator: a column pinned against the asymptote for `PIN_HOLD` (0.5 s)
  blinks — "full" and "wrong" must stay different-looking things
  (ENGINEERING §4).
- **Knobs/faders:** contrast, transient, pre/post drive, attack, decay,
  threshold, trim — every one through the plan-01 taper objects
  (integer positions, `unmap(map(p)) == p`), with LOG/LIN caption tags and
  unity-detent notches on the gain faders. `fmt` takes real values, so a
  scene landing between notches reads truthfully.
- **Transfer function dropdown** per band; changing it resets that band's
  scratch state (already the `bands.py` contract — the UI just calls it).
- Tooltips ported from the HTML's hint text.

### 3. Scenes & reset

Scene dropdown over the 11 `PRESETS`; **Reset resolves to the currently
selected scene**, not hard-coded defaults; reset-all guarded by the 8 s undo
(button relabels itself), undo snapshot discarded on scene change — the
exact semantics of ENGINEERING §4, which exist because scenes are the unit
of intent.

### 4. Transport

Port the HTML transport model to `sounddevice` playback: position measured
against the stream clock (not frame-counted), pause tears down / resume
rebuilds at offset, restart is return-to-zero preserving transport state,
loop folds position by modulo. Keys `K` and `0` as in the HTML. Pausing lets
bands decay on their own time constants — the coast-to-rest over ~4 s is a
feature, keep it.

### 5. Aesthetic

The instrument-panel look is a considered decision (ENGINEERING §7), and it
is reproducible in imgui: monospace font baked into the atlas, uppercase
micro-labels with wide letter-spacing, hairline 1 px rules, **square corners
everywhere** (`FrameRounding = 0` etc.), black ground, white text, red
`#ff2b2b` as the only accent, matching the vertex colour. The cell-count
readout stays the signature element.

## Verification

- `test_ui_state.py` covers the non-visual logic: reset-to-scene resolution,
  undo window expiry and discard-on-scene-change, taper round-trips from UI
  positions, transport position math across pause/resume/loop.
- Manual sweep against the HTML side by side: every control present, same
  ranges, same captions, same keyboard shortcuts. Checklist the controls in
  *Results* — "everything reachable there is reachable here" is the exit
  bar, and a checklist is how it's actually checked.

## Exit criteria

- [ ] Control-parity checklist complete, no gaps or documented waivers.
- [ ] Meter landmarks and annunciator behave per spec on the golden clips.
- [ ] State-machine tests green on merged `main`.
- [ ] A cold start (`uv run hyperspace`) reaches audio-reactive rendering
      with working panel in one command.

## Risks / notes

- imgui's default look leaks through easily (rounded corners, blue accents,
  padding). Style pass first, widgets second — retrofitting the aesthetic
  over finished widgets costs more.
- Custom widgets (meters with landmark lines, faders with detents) are draw-
  list work, not stock imgui sliders. Budget for that; the stock widgets are
  the fallback for anything that resists, waived explicitly in the checklist.
