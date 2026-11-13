# Distortion effects: Shake, Wave, Blocks

Three effect nodes that move the picture's pixels, and the two helpers
they share. Added 2026-11-13. Each is one file in
`hyperspace/shaders/fx/` with nothing in Python, like every effect
(`fx.py`'s docstring has the file format).

- Patches to play them: `presets/distort/` (its README lists all 23).
- Tests: `tests/test_fx_distort.py`, `tests/test_distort_presets.py`.
- Demo video: `tools/distort_demo.py` (see "Showing an effect" below).

## The model

A distortion is a field of offsets: for every pixel, how far away it
reads the frame. One is made by answering three questions.

1. **What is measured across the frame?** A distance along a line, a
   radius, an angle, a block's number in a grid.
2. **What waveform is laid over that measure?** `wave(shape, x)` in
   `_lib.glsl`: sine, triangle, square, saw or noise, period 1, −1 … 1.
3. **Which way does the result push?** Along the measure (a squeeze),
   across it (a slide), or something a cell does with its number.

`pushed(uv, d, split)` in `_lib.glsl` then does the read: `d` is the
offset in frame heights, and `split` parts the colours along it (red
reads `1 + split` times as far, blue `1 − split` times), so every
distortion has its own chromatic aberration, widest where it moves most.

Rules every one of them keeps, each held by a test:

- **Amount 0 is the picture again**, in every mode. Amount is an `amount`
  param (zero-safe log taper), so a lane, a hand or a pad on it fades the
  effect in from nothing.
- **A flat frame stays flat.** They only move pixels; none adds light.
- **Rates are clocks.** Rate and Drift are `@clock` lines, never
  `time × knob`, so a knob step never jumps the field
  (`tests/test_shader_time_lint.py`).

## Shake (`shake.glsl`)

The whole frame moved, the way a camera on a speaker cabinet is.

| Knob | What it does |
| --- | --- |
| Amount | The throw, in frame heights (0 … 0.25) |
| Rate | Shakes a second (0.5 … 60) |
| Motion | `buzz` back and forth along Angle · `orbit` round a circle · `punch` in and out about the centre · `jolt` knocked a random way each shake, then settling |
| Angle | Buzz: the line it shakes along |
| Hard | Buzz and punch: 0 swings like a sine, 1 snaps end to end |
| Smear | The shutter left open over up to half a shake: a blur, not a jump (8 taps) |
| Split | Red runs ahead of green and blue behind, up to a third of a shake each |

Split here is in time, not distance: at 1 on an orbit the three colours
sit a third of a turn apart, which is a turning deconverge.

## Wave (`wave.glsl`)

One waveform laid across the frame.

| Knob | What it does |
| --- | --- |
| Amount | How far the crest pushes, in frame heights (0 … 0.5) |
| Waves | Waves in one frame height; for spokes, waves in one turn |
| Along | What the wave is counted over: `line` (distance along Angle), `rings` (distance from the centre), `spokes` (angle round the centre) |
| Push | `slide` sideways to the wave's travel (a shear) · `squeeze` along it (bunching and stretching) |
| Shape | sine, triangle, square, saw, noise. Square and saw have an edge, so they cut the picture |
| Steps | Flattens the wave into that many levels each side of rest: slabs |
| Angle, Drift | Line: the way the wave travels. Waves passing a second |
| Split, Centre X/Y | The colour split; the centre for rings and spokes |

Along × Push gives six fields: rows slipping (line, slide), a spring
(line, squeeze), a pond (rings, squeeze), counter-turning rings (rings,
slide), petals (spokes, slide), pinched wedges (spokes, squeeze).

## Blocks (`blocks.glsl`)

The frame cut into a grid; a rule hands each cell a number; an action
uses it.

| Knob | What it does |
| --- | --- |
| Amount | How much a cell does at its number's peak: cells moved (shift, swap), doublings of size (zoom, stretch, bulge), quarter turns (turn) |
| Cell, Aspect | A cell's height in px; its width over its height (16 is long strips) |
| Group | Cells on a side that share one number: 4 is "4 × 4 blocks of units" |
| Rule | How the number runs over the grid: rows, columns, diagonal, rings (square, from the middle), random |
| Spread | How far out of step one block is with the next along the rule. 0.5 on diagonal is a checkerboard |
| Shape, Drift | How a cell's number moves in time, and how fast. Drift 0 holds the grid still |
| Action | `shift` · `zoom` · `stretch` (one way; low numbers pull a line into streaks) · `turn` · `bulge` (a lens inside the cell, still at its rim, so cells stay joined) · `swap` (whole cells trade places) |
| Angle, Split | The way shift, stretch and swap go; the colour split |

## Adding another distortion

Write a file that computes `d`, the offset in frame heights, and ends
`return pushed(uv, d, u_split);`. Use `wave()` for anything periodic and
a `@clock` for anything that moves. Then:

1. Add its `fx.<name>.amount` to `AMOUNTS` in `tests/test_retaper.py`.
2. Add it to `NAMES` in `tests/test_fx_distort.py`: the Amount 0 and
   flat-frame tests then run over every choice it declares.
3. Add one test that says where its push goes, on a white line.
4. Add segments to `tools/distort_demo.py` and a patch or two.

## Showing an effect

How this set was handed over, kept because it worked: the reviewer saw
every knob do its job in two minutes and could judge the idea, not the
diff.

- **One video, one segment per idea.** 25 segments of 5 s: each names
  the node and the knobs that differ from default, in the caption.
- **The real passes.** The scene is drawn by `Renderer.draw` into a
  texture and put through `FxChain.run_one`, the pass a graph Effect node
  runs. Nothing is mocked.
- **A test card in the corner.** The same pass over a grid, a circle and
  colour bars: what a field does to straight lines is plain there when
  the scene is busy.
- **Amount is driven, and the meter shows it.** `kick` is a 120 bpm
  decaying pulse (a stand-in for a bass lane), `swell` a slow rise and
  fall (a hand). Say in the handoff that these are stand-ins.
- **A contact sheet** of one still per segment, taken on a beat, for a
  look without playing the video.
- **Tests before the video.** The invariants above were green first, so
  the video is for taste and the tests are for truth.
- **The handoff message** is a table of nodes and knobs, what was and was
  not checked, and the video. Videos stay out of the repository.

```bash
cd hyperspace-python/tools
uv run python distort_demo.py --out <dir>                    # the video and the sheet
uv run python distort_demo.py --out <dir> --only 3,7 --no-video   # two segments, sheet only
```

About 2½ minutes on Mesa's software rasteriser for the whole video.

## Not checked

Written in a cloud session on software GL. Frame rate on the Mac, a real
band or hand on Amount, and how the patches feel were not checked there.
Shake with Smear and Split on is 24 reads a pixel; the rest are 1 to 3.
