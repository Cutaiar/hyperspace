# Plan 38 — hold the projector: the program stays up while the next look is built

**Status: built (2026-10-27)** on `plan-38-hold`, rebased by B1 onto
`plan-37-38-39-integration` (the first cut's commit kept), with B2's
hand-check tests and B3's review fixes merged (cd56b6f); it lands on the
integration branch first of plans 37–39. Tests at cd56b6f: the fast tier
3990 passed, 2 skipped; the full suite (`--all`) 4201 passed, 2 skipped;
goldens 128 passed, 757 pictures, none moved; `tests/test_hold.py` 32
tests (4 on GL). D1–D5 taken as recommended and accepted by the
controller (register rows 430–434), the owner to keep or overturn; the
build's rulings are rows 435–439 and 461–470. Hand checks 377–383
(group AI). "What changed in the build" at the end says where the build
differs from the text above.

**First cut (2026-10-27)** on `output-hold`, cut from
`graph-quick-wins` (PR #241). It uses #241's GRAPH backdrop
(`outputs.Preview`) as the operator's monitor, so it lands after #241 or
with it. It is independent of plan 36 (PR #242, a doc only): it reads the
wiring as plan 35 left it (`Renderer.wiring`, `graph.build_graph`) and
works the same once plan 36 makes the graph explicit. No preset, schema
or golden changes. 16 new tests (`tests/test_hold.py`), one of them on GL.

**Rebased onto plan 36 (2026-10-27, task B1)** as `plan-38-hold`, off
`plan-37-38-39-integration`. Plan 36's explicit graph needed one thing
more held: the rig's bus cables from All outputs into each window
(`graph.RigWires`, the open show's, which the renderer reads through its
`rig_source`). The hold now keeps them with the wiring, so a bus cable cut
on GRAPH during a hold stays off the projector. The preview renderer reads
the show's cables too, never a default. Three tests prove it, one on GL
(19 in all).
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
  1. The app's renderer is handed the held wiring, the held rig cables
     (plan 36's bus, `rig_source`) and the held extra hands states.
  2. Each held param whose base the operator has moved is written to its
     object with `Param.put`, never `set`. No base moves, so undo, the
     dirty dot and the desk's lights are unaffected.
  3. The draw runs.
  4. The live values are put back, whether or not the draw raised.

  A param nobody moved costs one compare. The graph is cached as before:
  its key is the held wiring and rig, which never change while held; it
  rebuilds only when a landing changes the effect set (the instances the
  hold keeps, below), and then without losing a frame.
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
- **A landing keeps the program's nodes** (B3, ruling 12). Every
  `preset.GraphSection` landing — a load, **new**, a GRAPH edit, an undo
  — settles the effect instances, switch picks, resizes and extra
  look-backs to its own graph, which would strip the program's. While
  held, `GraphSection._settle` asks `Hold.keep(kind, names)`, which adds
  the program's own names (snapshotted at HOLD), so their params, values,
  picks, states and effect clocks stay for the projector. Take releases
  the hook and settles to the live graph; Drop releases it before its
  revert lands the hold point. A save during a hold leaves the kept
  instances out (`Presets._values` drops `Hold.program_only()`), and an
  undo mark taken while held records the landed graph's own instances.
- **A load's delay reset goes to the preview** (B3). `Presets.load`'s
  reset of the delays and echoes goes through the hold while held: the
  preview's delays start empty, the projector's trail carries on, and at
  Take the projector's are reset if a load happened.
- **The canvas reads the preview** (B3, ruling 13): `hold.canvas_renderer`
  is the preview renderer while held and drawn, so new nodes get real refs
  and the dormant and refusal lines describe what TAKE will put up.

## What is held, and what is shared by both (`hold.HELD_GROUPS`)

Held: `view`, `camera`, `pattern`, `dream`, `fx`, `backdrop`, `switch`,
`resize`. These are the performance groups the renderer reads.

Shared by both program and preview, and so visible on the projector
during a hold:

| what | why | if it matters |
|---|---|---|
| the turn: `rot.*`, `view.speed`, `view.plane.*`, the 3D switch | the angles are integrated once a frame, before either draw | D2 |
| the media channels (`media.*`) | a channel decodes once for every reader | switch sources after Take |
| the modulators and routes (`lfo`, `env`, `seq`, `macro`, `mod`) | their offsets are read once per frame | a new route moves the program's param too |
| the clouds and the effect files on disk | the device registry and the disk, not the look | saving an effect file shows on the projector |
| a Syphon input read twice a frame | the second read may have no new frame | hand check 6 |

An effect instance, switch pick or resize that a load or a GRAPH edit
removes is **not** shared: the hold keeps it for the program until Take
(B3; the first cut's table said it "reads through", which was the bug).

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
- `hyperspace/preset.py` (B3, ruling 12) — `GraphSection.hold`, `names`,
  `settle`, `_settle` (the land block's declares through `Hold.keep`),
  the delay reset through the hold, `Presets._values` leaving out the
  program's instances, `mark` recording the landed graph's own.
- `hyperspace/ui.py` (B3) — `graph_words` and `dormant_lines` read through
  `hold.canvas_renderer`.
- `hyperspace/ui_graph.py` — the head's **hold** / **held · take ·
  drop** chips and red line (`hold_line`), the backdrop forced on while
  held, and the PROJECTOR inset (`monitor_rect`, `_monitor`).

## Hand checks (need the machine)

Group AI, 377–383, in [`11-hand-checks.md`](11-hand-checks.md) (with the
tests behind each) and [`../TESTING-GUIDE.md`](../TESTING-GUIDE.md) (in
plain words). The first cut's list, as written:

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

## What changed in the build

The plan above is the design and the first cut; this is where the build
(tasks B1–B3, 2026-10-27) differs from it, or chose within it. Each
ruling has a row in [`DECISION-REGISTER.md`](../DECISION-REGISTER.md)
(430–439, 461–470), the owner to say keep or overturn.

**B1: the rebase onto plan 36** (e4d3af4, 3e89e0a, 397b7ba; PR #251).
The first cut's commit cherry-picked onto `plan-37-38-39-integration`;
only `ui_graph.py`'s import line conflicted. Two fixes the explicit graph
needed:

- **The hold keeps the rig's bus cables** (row 435). Plan 36 feeds each
  window through `graph.RigWires`, read from `Renderer.rig_source`; the
  first cut held only the wiring, so a bus cable cut during a hold reached
  the projector. `Hold.rig` is captured at HOLD, `program` hands the
  renderer a `_HeldRig` stand-in and restores the live one, and
  `rewired()` compares the rig.
- **The preview reads the show's cables, never a default** (row 436).
  `mirror` did not pass `rig_source`, so the preview renderer drew every
  bus cable standing; `MIRRORED` gains it.
- The hold chips sit first on the head, before plan 36's (row 461).
  Three tests, one on GL with the app's empty-frame renderer; 19 in all.

**B2: the hand checks as tests** (a4ea685; PR #257). The seven checks
became group AI; three gained tests: the program drawing the held wiring
while a GRAPH edit lands (GL, byte for byte against each graph drawn
alone; mutation-checked), Drop after a whole new look as one undo step
back and one forward (row 439), and learned desk buttons lighting while
held. 22 tests.

**B3: the review and its fixes** (b4ebba9, c834e74; PR #259).

- **Critical: a landing stripped the program's nodes** (row 462, ruling
  12). Every `GraphSection.land` re-settled the effect instances, switches
  and resizes to the landed graph, so **new**, a load or a delete on GRAPH
  during a hold took the projector's effects away (a blank graph landed
  left `fx.specs == []`). Fixed with the `Hold.keep` hook in
  `GraphSection._settle`, released at Take and Drop; a save leaves the
  kept instances out (row 463, ruling 12b); an undo mark taken while held
  records the landed graph's own instances (row 464).
- **A load's delay reset cut the projector's trails** (row 465): it now
  goes to the preview while held, the projector's at Take after a load.
- **The canvas read the projector's graph** (row 466, ruling 13):
  `hold.canvas_renderer` over five reads in `ui_graph.py` and `ui.py`.
- `view.speed` and `view.plane.*` out of the held set (row 431); the
  preview drawn with output 1's switches at full dim (row 467);
  `rewired()` reads the rig's cuts (`_cut`); the raise test checks undo
  and the dirty dot too.
- Recorded, not changed: Drop puts back what the show's mark carries
  (row 438), the preview renderer's lifetime and hot reload (row 468), the
  inset on the foreground list (row 469), plan 39's seam (row 470).
- B1's note that "the program's graph never rebuilds while held" was
  wrong: it rebuilds when a landing changes the effect set, losslessly.
  32 tests in `tests/test_hold.py`.

**What plan 39 must add at integration** (so its mattes, cuts and
segments are kept by a hold and left out of a save): a `matte`, `cut`
and `segment` key in both branches of `GraphSection.names` and in
`_settle`'s no-spec dict; the `declare_mattes` / `declare_cuts` /
`declare_segments` calls inside `_settle` beside `declare_lookbacks`
(not in `land`); and `hold.PROGRAM_IDS` entries for the three kinds —
without them `Hold.program_only` raises `KeyError` the first time a held
matte, cut or segment is deleted, on purpose. Plan 37's thumbnails must
read through `hold.canvas_renderer` (the controller routes them at the
37 merge).

**Not verified by any person:** everything on screen (the chips, the red
line, the inset, the forced backdrop) and everything in checks 377–383:
trails through a Take, the FPS, Syphon / NDI in the preview, the real
LEDs, the feel of a pumping held param.

**Known rough edges:** while held, the kept instances' params show on the
EFFECTS and desk pages (GRAPH does not draw them); an effect deleted and
re-added during a hold gets the program's values; a desk learn made during
a hold is undone by Drop (learn before holding); the inset sits over
canvas popups in its corner; a hot reload of an effect module does not
reach the preview renderer's sub-objects.
