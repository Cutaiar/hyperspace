# Plan 82 — control widgets: ticks, unipolar and bipolar faders, XY pads

**Built** 2026-11-22 on `claude/eager-maxwell-19lf9p` (plan 69 before the
post-install wave was renumbered: [`66-launch.md`](66-launch.md)). Register rows
1020–1029, hand checks 820–825 (group FC). Draft PR to `main`; the owner merges.
Item 82 of [`66-post-install.md`](66-post-install.md); decision D3 built as
recommended.

## Why

From the November install: on a trackpad, at a distance, the panel's sliders
all looked alike. A stepped control (Zoom burst's Taps, Kaleidoscope's
Segments) snapped but showed no steps; a centre (−1…+1) and an amount
(0…1) were drawn the same; and a burst's centre took two sliders a row
apart, where a performer thinks of one point on the screen.

## What was built

### 1. One abstraction for every fader: `ui_fields.Shape`

`ui_fields.shape_of(panel, param)` says how a CONTINUOUS param is drawn:

| Class | Which params | Fill | Detent |
| --- | --- | --- | --- |
| **unipolar** | 0..1-like, resting at 0 or the top | from the left | none |
| **bipolar** | symmetric, neutral at 0 | from 0 | at 0 |
| **unity** | a multiplier neutral at 1 | from 1 | at 1 |

Plus, for any of them, **steps** (an integer range): a tick per step under
the track. A taper's unity (an effect's speed at 1×) keeps its notch beside
the detent. The kit slider (`ui_fields._slider`) and the stock fallback
(`Panel._origin`, `ui.py`) both read the shape, and the pad's knobs and
crosshair below do too.

**The class is inferred** (`ui_fields.polarity`):

- bipolar: a range across 0 whose default is 0 — or whose default is
  unknown, which is every param that is not an effect's own uniform (VIEW's
  rates, the camera's yaw and pan): they filled from 0 before and still do;
- unity: a default of 1 in the middle of the range, linear (lo + hi = 2:
  Hue cycle's saturation) or log (lo · hi = 1: Kaleidoscope's zoom, Blocks'
  aspect). A 1 that is not in the middle (Prism's rim, 0…3) is no neutral;
- unipolar: everything else, a range across 0 with another default
  included (the Mandelbrot's c and centre; row 1021).

**An effect file can say it** on its `@param` line: `bipolar` or
`unipolar`, after the numbers (`fx.ParamSpec.polarity`). Drawing only: it
declares nothing, so it is not in `EffectSpec.signature` and moves no saved
value.

**The detent**: a drag that lands within `ui.DETENT_PX` (6 px) of a
bipolar or unity detent lands on it; a typed value (Ctrl+click) and a ⇧
fine drag are never moved (row 1023).

**Ticks** (`ui_fields.ticks`): one a step while they are `ui.TICK_GAP` (6 px)
apart; past that every 2nd, 4th, 5th, 10th … whole value, the first stride
that leaves the gap, and both ends always (row 1024).

### 2. XY pads and the XYZ volume

Two new directives in an effect file (`fx.parse`):

```glsl
// @pair   u_cx u_cy "Centre"
// @volume u_cx u_cy u_amount "Burst"
```

Each names the file's own continuous params (no choice), a param on one pad
at most (`fx.PadSpec`, `EffectSpec.pads`, `fx.pad_of`). Nothing is renamed or
re-keyed: the params are declared exactly as before, so saved patches,
routes, learn and desk layers are untouched. Like `@family`, a pad is not in
the signature.

The fx strip (`ui_fx.strip`) draws a pad at its first param's place, in
place of the sliders (`ui_fields.inline_pad`, `pad`):

- **the square**, `ui.PAD_MIN`…`ui.PAD_MAX` (120–260 px) across: a click or a
  drag sets X and Y at the pointer (Y up), ⇧ held moves a tenth as far from
  where they were. The dot is `ui.PAD_DOT_R` (10 px) with a white ring, a
  red crosshair runs through it, and the neutral cross (each axis's detent)
  and the quarters are drawn under it. A volume's third param is a halo
  about the dot;
- **a knob per axis** beside the square, or under it where the pane is too
  narrow: a vertical drag turns it (`ui.KNOB_THROW`, 200 px a full throw; ⇧ a
  tenth), a double-click returns it to its detent, and its arc fills from
  its shape's origin. The knob is the param's own control: its `##<id>`,
  right-click menu (learn, routes), learn frame and tooltip — so a route or
  a learn still addresses each param alone;
- **modulation**: while a lane rides any axis the pad draws a white dot where
  the lanes have it now, a line from the bases' dot, and a white halo for a
  volume; each knob a white tick, its readout red.

D3, as built: **Prism**, **Wave** `@pair u_cx u_cy "Centre"`; **Wave Table**
`@pair u_offset_x u_offset_y "Offset"`; **Zoom burst** `@volume u_cx u_cy
u_amount "Burst"`. Zoom burst has the volume only, not a pair as well: a
param is on one pad, and the volume is its pair plus Amount (row 1026).

Pictures: [`assets/82-control-widgets/`](assets/82-control-widgets/) — Zoom
burst's volume mid-drag and set, Kaleidoscope's Segments ticks, Zoom's unity
notch and Swirl filling from centre, and both moved. Made with
`tools/drive_control_widgets.py` through `tools/app_driver.py` on Mesa.

## Files

Owned: `ui_fields.py`, `ui.py` (the metrics and colours `TICK*`, `DETENT_PX`,
`PAD_*`, `KNOB_*`; `Panel._origin`), `fx.py` (the parse), the four effect
files. **Outside the row:** `ui_fx.py`, nine lines in `strip` — the strip is
where an effect's params are drawn, so the pad has to be drawn there; with no
kit it keeps its sliders.

## Tests

`tests/test_control_widgets.py`: the parse and its errors, the polarity
markers, the four files' pads; the inference over the shipped ranges; ticks
counted, thinned and never crowded; then the real panel through
`tests/ui_driver.py` — a bipolar fader at rest is centred and a drag near
centre lands on 0 (a typed 0.01 stays), Segments draws all 15 ticks, a drag
on Prism's pad sets both centres, a knob turns one axis and a double-click
centres it, the volume's tapered Amount turns, a lane shows on the pad.

## Not built

- No `unity` marker: the three named multipliers are inferred; one that is
  not inferred needs a marker added (row 1022).
- Z is set by its knob only, not by a scroll over the pad: a trackpad
  scroll would change it while scrolling the pane (row 1027).
- No Ctrl+click to type into a knob; the menu, learn and the pad do the rest.
- Pads on VIEW or any page but the fx strip: plan 89's to use.

## Open style questions — to settle by playing

The owner's word (2026-11-23): merge it, and keep track of what may want a
different look or feel once it has been played with. Each is a named
constant or one function, so a change is small. Tick one off with the
answer and the PR that made it.

**The pad and the volume** (`ui_fields.pad`, `_square`)
- [ ] Size: the square is 120–260 px (`ui.PAD_MIN`, `PAD_MAX`). Big enough
  on the trackpad at the stage's distance? Should it grow past 260 in a
  wide pane?
- [ ] The dot: 10 px (`ui.PAD_DOT_R`), red with a white ring. Clear enough,
  or wants to be bigger, or filled white?
- [ ] The red crosshair through the dot, the quarter grid and the faint
  neutral cross: helpful, or noise?
- [ ] A click jumps the dot to the pointer (absolute). Or should a drag move
  it from where it was (relative), as a trackpad cursor does?
- [ ] The volume's Z as a halo about the dot (`halo`: 0.15 of the side at
  full). Does it read as depth? Too big at high Amount?
- [ ] Z by its knob only (row 1027). Wants a gesture on the pad itself
  (⌥-drag, or a scroll that is not a pane scroll)?
- [ ] The head is the label alone; each value is under its knob. Wants the
  values back in the head?
- [ ] Knobs beside the square, or under it in a narrow pane (`_knob_layout`,
  `ui.KNOB_COL`): the right place?

**The knobs** (`ui_fields.knob`)
- [ ] Size: 36 px across (`ui.KNOB_R`). Easy to grab on the trackpad?
- [ ] Throw: a vertical drag of 200 px for the whole range (`ui.KNOB_THROW`).
  Too slow, too fast? Horizontal as well as vertical?
- [ ] No typing into a knob (Ctrl+click). Wanted?
- [ ] Words under a knob: the axis letter and its value. Enough, or the
  param's name?

**The faders** (`ui_fields.Shape`, `marks`, `_snap`)
- [ ] The detent's pull: 6 px (`ui.DETENT_PX`). Felt, without grabbing a
  value meant to be near it?
- [ ] An effect's speed: snaps to its stop; its 1× notch is drawn but does
  not snap. Should 1× snap as well?
- [ ] The detent's notch is drawn as a taper's unity notch always was (above
  and below the track). Wants to stand out more for a bipolar centre?
- [ ] Ticks: under the track, 3 px (`ui.TICK_H`), no closer than 6 px
  (`ui.TICK_GAP`), in a quieter grey (`ui.TICK`). Readable from the stage?
  Through the track instead?
- [ ] A tapered integer (VIEW's instance count) has no ticks: its detents
  are not whole values. Wanted?

**Which param is which** (`ui_fields.polarity`)
- [ ] The Mandelbrot's c, z₀ and centre now fill from the left (row 1021):
  mark them `bipolar` (plan 80's file)?
- [ ] Any fader whose class looks wrong once played: add `bipolar` or
  `unipolar` to its `@param` line. A unity multiplier the rule misses
  would want a `unity` marker (row 1022).

**Where else**
- [ ] Pads on VIEW (the copies' amp and spacing?) and other pages: plan 89
  builds on these widgets.
- [ ] More pairs worth a pad among the effects: the shader roundup's call.

