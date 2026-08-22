# Plan 03 — UI, scenes & audio sources

**Blueprint stage 4, executed third.** Renumbered 2026-08-21: the booth
hardware for the live-inputs plan (decks, IMU) is not available yet, so the
control surface comes first and the audio-capture task migrates here from
the live-inputs plan — meters and strips are dead widgets without a signal.
Scope: everything reachable in the HTML panel becomes reachable in the
imgui overlay, in the same visual language, plus mic/loopback capture and
file playback as the signal sources.

## Prerequisites

Plans 01–02 complete (the UI binds to `bands.py` parameters and the
renderer's view state).

## Deliverables

```
hyperspace/tapers.py     # fader taper objects (moved here from plan 01)
hyperspace/control.py    # headless panel state: selection, scenes, reset/undo
hyperspace/audio.py      # mic/loopback capture + file playback (sounddevice)
hyperspace/ui.py         # imgui overlay in the render window
tests/test_control.py    # taper/reset/undo/transport state tests (no pixels)
```

### 0. Audio sources (migrated from the live-inputs plan)

`sounddevice` input stream feeding `analysis.py` through a ring buffer, with
device enumeration and the loopback-preselect heuristic; file playback for
wav/mp3/flac/ogg via `soundfile` + an output stream, with the reference
transport semantics (position off the stream clock, pause freezes and decays,
restart is RTZ preserving state, loop folds). The chain keeps stepping on
silence while paused — the coast-to-rest is a feature.

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


## Results (2026-08-21)

Executed after the renumber, with the audio-capture task migrated in and
three expansions the user requested (face shading, multi-instance, camera).
123 tests green (+1 slow), ruff clean, windowed smoke run exits clean.

**Control surface** (`ui.py` + `control.py` + `tapers.py`):

- Every taper ported with the round-trip law under test at every position
  of every throw; `T_DEPTH.map(100) == 2.60` exactly; the trim taper's
  −∞ off-notch round-trips. Readouts format real values, not positions.
- Reset resolves to the selected scene; Reset-all arms an 8 s undo on the
  same button; scene changes discard the snapshot; shaper changes clear
  scratch state — all under test in `test_control.py` with a fake clock.
- Meters: input (white) / output (red) pairs per band with NOM and KNEE
  landmark lines and the blinking over-drive annunciator (PIN_AT 92% of
  CEIL, PIN_HOLD 0.5 s). Click a meter to open that band's strip; all
  eight knobs with LIN/LOG tags and tooltips ported from the reference.
- A headless imgui smoke test runs the entire panel with no window, so
  API breakage is caught by pytest, not by launching.
- **Divergences from the HTML, accepted:** native tooltips replace the
  hint-readout strip; the imgui default font replaces the monospace
  styling pass (full aesthetic pass deferred); no per-fader detent notch
  drawn yet.

**Audio** (`audio.py`): sounddevice capture with device enumeration and
loopback preselect; file playback (wav/mp3/flac/ogg via soundfile) with
the reference transport semantics — position off the stream clock, pause
freezes and lets bands decay (coast-to-rest preserved), restart is RTZ
preserving state, loop folds; callbacks only copy into a ring buffer.
Transport math and ring behaviour under test. **Live mic/loopback capture
still needs its first real-hardware press of the button** (mic permission
prompt included) — that verification stays on plan 04's checklist.

**Face shading** (user-requested expansion, from the fork-agent
investigation): true 2-face extraction — planar cycle walk plus a
support-half-plane filter that rejects internal cycles (equatorial squares
of the 16-cell, central hexagons of the 24-cell). Face counts match known
values for all shapes under test (tesseract 24, 120-cell 720, 600-cell
1200, Clifford torus 560…). Rendered as fan-triangulated translucent fills
painter-sorted under the wireframe (`0.010 + 0.055·t²` with face-count
density compensation). Toggle: F key / Faces checkbox. Extraction cached
per shape (600-cell ~1 s first build).

**Camera + instances** (user-requested expansion): scroll zoom about the
cursor, right-drag pan, R resets; edge widths and point sizes scale with
zoom. Instances 1–100 as a synchronized grid (one projection, tiled with
offsets — measured by the investigation at 51–132 fps for 100 copies;
per-instance rotation phases and GPU instancing are the documented next
step if a live field becomes a performance feature). Showcase renders in
`docs/plans/assets/03-*.png`.

**Environment note:** pyGLFW and imgui-bundle both ship libglfw; app.py
points pyGLFW at imgui-bundle's copy before import to avoid macOS ObjC
class collisions. imgui-bundle's GLFW backend needs `pyopengl` (added).
