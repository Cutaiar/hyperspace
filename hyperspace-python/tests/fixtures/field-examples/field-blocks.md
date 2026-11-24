# Field: Blocks, taken apart

**What you see.** A checkerboard of cells, each snapping a quarter turn one way and
then the other, the turn running along the diagonal. The same picture as the Blocks
effect's `distort-blocks-turn` — built from five primitives instead of one file.

**How it is wired.**

```
measure ───▶ waveform ───▶ cellaction.image
measure.2 ───────────────▶ cellaction.field ─▶ displace.field
scene ───────────────────────────────────────▶ displace.image ─▶ output.all
```

- **Measure** (`fx.measure.*`): **Along** cells, **Out** value — the frame cut into
  **Scale** cells to a frame height (**Aspect** wide, **Group** to a block), each
  numbered by its **Rule** (diagonal) and **Spread**. The cell's size rides along with
  the number, out of sight.
- **Waveform** (`fx.waveform.*`): a square **Shape** over each cell's number, one wave
  to a number (**Waves** 1), drifting at **Drift**; **Phase** a quarter turn on, so at
  rest a cell sits at its peak. −1 … 1: how far this cell goes now.
- **Measure.2** (a second Measure, the same grid): **Out** direction — each pixel's
  place in its cell, from the cell's middle. Wired straight into a Displace, every cell
  would zoom.
- **Cell action** (`fx.cellaction.*`): what a cell does with its number — **Action**
  turn, **Amount** quarter turns at the peak. Shift, zoom, stretch, bulge and swap are
  the others; **Angle** steers shift, stretch and swap.
- **Displace** (`fx.displace.*`): moves the picture by that push, **Amount** 0.5 (its
  top; Cell action's push is in half frame heights, so this is the push exactly);
  **Split** parts the colours along it.

Blocks' own knobs, one by one: Cell → both Measures' **Scale** (the frame's height in
pixels ÷ Cell: 1080 ÷ 90 = 12); Aspect, Group, Rule, Spread → both Measures; Shape,
Drift → Waveform; Action, Amount, Angle → Cell action; Split → Displace. For swap, both
Measures' **Pairs** say which blocks pair (across, or up — whichever Angle is nearer).

**Play it.** `lane:0` (sub) pushes `fx.cellaction.amount`; `hand:right.y` pushes
`fx.displace.split`; `hand:left.y` pushes `fx.measure.scale` and `fx.measure.2.scale`
together (raise it: fewer, bigger cells).

**Try.** Change only the first Measure's **Along** to rings or line: the cells keep
their grid but take their number from somewhere else. Wire the Waveform into a second
Displace too, or a Measure of noise into Cell action's input instead of the Waveform.
Set **Pairs** across, **Action** swap: whole cells trade places.

**Not quite byte for byte.** Blocks counts its grid in pixels and a Measure in frame
heights, so the patch is Blocks at the frame height it was mapped for (1080 here);
where a cell's edge falls exactly on a pixel's centre the two may put that pixel in
either cell, and elsewhere they agree to within one level
(`tests/test_blocks_patch.py`). The Blocks effect itself still draws every saved look
as it always did.
