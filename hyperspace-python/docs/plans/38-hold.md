# Plan 38 — hold the projector: the program stays up while the next look is built

**Status: first cut built (2026-10-27)** on `output-hold`, cut from
`graph-quick-wins` (PR #241). It uses #241's GRAPH backdrop
(`outputs.Preview`) as the operator's monitor, so it lands after #241 or
with it. It is independent of plan 36 (PR #242, a doc only): it reads the
wiring as plan 35 left it (`Renderer.wiring`, `graph.build_graph`) and
works the same once plan 36 makes the graph explicit. No preset, schema
or golden changes. 16 new tests (`tests/test_hold.py`), one of them on GL.
The questions at the end (D1–D5) are the owner's; the build takes the
recommendation for each.

The owner's ask (2026-10-27): *hold a current render setup on the
projector while the node operator previews new changes that are not yet
on the main output, so spectators don't have to watch a new scene being
built.*

## What it does

- **HOLD** (a chip first on GRAPH's head, and `output.hold`, a toggle
  that can be learned onto a desk button) freezes what the projector is
  *showing*, not the picture itself. Every render output (each window and
  each publish-only output, so Syphon and NDI too) becomes the
  **program**: the wiring and the look as they were at the press. The
  program keeps running. Bands, LFOs, envelopes and hands still move it,
  the look-back keeps trailing, effects keep their clocks.
- Everything the operator does afterwards lands as usual: GRAPH edits, a
  **new** preset, loading another preset, a knob, a route. The dirty dot,
  undo and saving all work normally. These changes are the **preview**.
  The GRAPH canvas shows the preview behind the nodes, even with
  **output behind** off, since that is what a hold is for. A small inset
  framed in red in the canvas corner, labelled **PROJECTOR**, shows what
  the room sees. The head has a red line: `HELD 1:42 — … · 3 settings
  changed · the graph changed`.
- **TAKE** (`output.take`) puts the preview on the projector as a hard
  cut. The next frame draws from what is landed. The look-back's trails
  carry on, because they belong to the program's renderer.
- **DROP** (`output.drop`) discards the preview. It reverts to the hold
  point as one undo step: the look, the graph, the routes, the desk's
  preset layer and the macros. Rig settings (output, eye, hands feel,
  tempo) are left alone. Then the hold lets go. The projector never moved,
  so nothing changes there, and ⌘Z brings the discarded edits back.
- Both trigger buttons are lit while a hold is on, so a desk button
  learned onto either shows that a preview is pending.

## How it works (rides on plans 26, 35 and #241)

The frame is already data: `Renderer.wiring` (plan 35's wired frame) plus
the objects the params write to (`ViewState`, `FxState`, `DreamState`).
A hold keeps a second copy of each of these, and that is the whole
mechanism.

- **Program** (`hold.Hold.program`, around the one `draw_outputs` in
  `app._draw_render`):
  1. The app's renderer is handed the held wiring and the held extra
     hands states.
  2. Each held param whose base the operator has moved is written to its
     object with `Param.put`, never `set`. No base moves, so undo, the
     dirty dot and the desk's lights are unaffected.
  3. The draw runs.
  4. The live values are put back, whether or not the draw raised.

  A param nobody moved costs one compare. The graph is cached as before:
  the held wiring never changes, so it never rebuilds.
- **Modulation rides on both.** The program value of a modulated
  continuous param is the held base plus this frame's offset on the live
  base (`hold.program_value`). So a band driving `view.bright` drives it
  on the projector too.
- **Preview** (`hold.preview_renderer`) is a second `Renderer` on the same
  context. It shares the params' objects, so a knob shows on both, and it
  shares the clock (`_t0`), so effect phases advance once a frame. It
  draws the live wiring after the outputs, into #241's `Preview` tap, at
  output 1's size under the render cap and at most 1280 px on the long
  side (`hold.preview_size`). It runs only on frames where the GRAPH page
  shows it. With the page closed, a hold costs one compare per held param
  and nothing else. Its look-back has no dream worker: the dream belongs
  to the projector. Any error from the preview is reported on the head
  line, and the program frame is still drawn.
- **The monitor** is a second `Preview` that output 1 publishes into
  while held, the same way #241's backdrop works when no hold is on.

## What is held, and what is shared by both (`hold.HELD_GROUPS`)

Held: `view`, `camera`, `pattern`, `dream`, `fx`, `backdrop`, `switch`,
`resize`. These are the performance groups the renderer reads.

Shared by both program and preview, and so visible on the projector
during a hold:

| what | why | if it matters |
|---|---|---|
| the turn: `rot.*`, speed, planes, the 3D switch | the angles are integrated once a frame, before either draw | D2 |
| the media channels (`media.*`) | a channel decodes once for every reader | switch sources after Take |
| the modulators and routes (`lfo`, `env`, `seq`, `macro`, `mod`) | their offsets are read once per frame | a new route moves the program's param too |
| an effect instance a newly loaded preset removed (`fx.acid.2`) | `FxState` drops it, so the program's node reads through | Take or Drop soon after loading |
| a Syphon input read twice a frame | the second read may have no new frame | hand check 6 |

## Decisions for the owner

| # | question | the build's answer (recommendation) |
|---|---|---|
| D1 | Take as a cut, or a crossfade (a `output.take_fade` in seconds)? | **Cut** for now. A fade needs both renderers drawing to the outputs for its length and a mix pass at the end of the program. It is a small follow-up if the cut reads harshly in the room. |
| D2 | Hold the turn as well (a second integrator for the program, so a speed or plane change waits for Take)? | **Not yet.** Rotation reads as continuous motion, not construction, and a second `ViewState` integration touches the 3D switch's pose logic. |
| D3 | Drop: the preset's part only, or everything since HOLD, rig included? | **The preset's part.** A dim or a hands-feel change made during a hold is about the room, not the next look. |
| D4 | Preview only behind GRAPH, or also on its own window or screen (an output marked "preview")? | **GRAPH for now.** A preview output would be a slot the hold excludes from the program. It fits plan 36's explicit outputs once that lands. |
| D5 | Hold every output, or per output (the laptop's output 1 follows the edits while the projector holds)? | **Every output.** Per output needs a program per window. Two programs at once is a larger build, and the monitor inset covers the laptop's view of the room. |

## Files

- `hyperspace/hold.py` — new. `Hold` (engage, take, drop, program,
  draw_preview), `program_value`, `preview_size`, `mirror`,
  `preview_renderer`, `register` (`output.hold` / `.take` / `.drop`).
- `hyperspace/undo.py` — `Undo.checkpoint()` (the state with what is
  loaded) and `Undo.revert(state, label)` (one replacing action back to
  it, undoable like a load).
- `hyperspace/app.py` — `_draw_render(…, hold=, monitor=)`: the program
  inside the hold, the preview after it (`_draw_preview`), output 1 on
  the monitor. The hold is built beside the output switches, its undo
  handed over, and it and its preview renderer are hot-reload targets.
- `hyperspace/ui_graph.py` — the head's **hold** / **held · take ·
  drop** chips and red line (`hold_line`), the backdrop forced on while
  held, and the PROJECTOR inset (`monitor_rect`, `_monitor`).

## Hand checks (need the machine)

1. On the rig, with the projector up: press **hold**, then **new** on the
   PRESET strip. The projector keeps the old look and keeps moving with
   the music. GRAPH's backdrop goes black and the PROJECTOR inset shows
   the old look.
2. Build a scene by wiring shape → scene → All outputs and adding an
   effect. The backdrop shows it and the projector does not. The head
   line counts the changed settings and says "the graph changed".
3. **take**: the projector cuts to the new scene. With the look-back on,
   the trails carry on through the cut.
4. Hold again, turn a few knobs and rewire, then **drop**: the canvas and
   knobs return to what the projector shows, and the projector never
   changes. ⌘Z brings the dropped edits back.
5. Learn `output.hold` and `output.take` onto two desk buttons. Both
   light while held.
6. Frame rate with GRAPH open while held: the preview costs a second
   frame at up to 1280 px. Check the SYSTEM page's FPS on the show Mac,
   and check Syphon / NDI inputs in the preview (row 6 of the table
   above).
7. Hold while a band drives a held param, then move its base on the
   desk: the projector keeps the held base and still pumps with the band.
