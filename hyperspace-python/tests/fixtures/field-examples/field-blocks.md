# Field: Blocks, taken apart

**What you see.** A checkerboard of cells, each snapping a quarter turn one way and
then the other, the turn running along the diagonal. The same picture as the Blocks
effect's `distort-blocks-turn` — built from five primitives instead of one file.

**How it is wired.**

```
cells ─────▶ waveform ───▶ cellaction.image
cells.2 ─────────────────▶ cellaction.field ─▶ displace.field
scene ───────────────────────────────────────▶ displace.image ─▶ output.all
```

- **Cells** (`fx.cells.*`): **Out** value — the frame cut into
  **Scale** cells to a frame height (**Aspect** wide, **Group** to a block), each
  numbered by its **Rule** (diagonal) and **Spread**. The cell's size rides along with
  the number, out of sight.
- **Waveform** (`fx.waveform.*`): a square **Shape** over each cell's number, one wave
  to a number (**Waves** 1), drifting at **Drift**; **Phase** a quarter turn on, so at
  rest a cell sits at its peak. −1 … 1: how far this cell goes now.
- **Cells.2** (a second Cells, the same grid): **Out** place — each pixel's place in
  its cell, −½ … ½ from the cell's middle (red across, green up on the canvas). Wired straight into a Displace, every cell
  would zoom.
- **Cell action** (`fx.cellaction.*`): what a cell does with its number — without it a
  Waveform into Displace only slides each cell along one angle. **Action**
  turn, **Amount** quarter turns at the peak. Shift, zoom, stretch, bulge and swap are
  the others; **Angle** steers shift, stretch and swap.
- **Displace** (`fx.displace.*`): moves the picture by that push, **Amount** 0.5 (its
  top; Cell action's push is in half frame heights, so this is the push exactly);
  **Split** parts the colours along it.

Blocks' own knobs, one by one: Cell → both Cells' **Scale** (the frame's height in
pixels ÷ Cell: 1080 ÷ 90 = 12); Aspect, Group, Rule, Spread → both Cells; Shape,
Drift → Waveform; Action, Amount, Angle → Cell action; Split → Displace. For swap, both
Cells' **Pairs** say which blocks pair (across, or up — whichever Angle is nearer).

**Play it.** `lane:0` (sub) pushes `fx.cellaction.amount`; `hand:right.y` pushes
`fx.displace.split`; `hand:left.y` pushes `fx.cells.scale` and `fx.cells.2.scale`
together (raise it: fewer, bigger cells).

**Try.** Wire a Point into both Cells' `field` ports and move it: the grid slides.
Put a Rings into the Waveform instead of the first Cells: each pixel's number comes
from its distance, the turn still happens cell by cell. Wire the Waveform into a second
Displace too, or a Noise into Cell action's input instead of the Waveform.
Set **Pairs** across, **Action** swap: whole cells trade places.

**Not quite byte for byte.** Blocks counts its grid in pixels and Cells in frame
heights, so the patch is Blocks at the frame height it was mapped for (1080 here);
where a cell's edge falls exactly on a pixel's centre the two may put that pixel in
either cell, and elsewhere they agree to within one level
(`tests/test_blocks_patch.py`). The Blocks effect itself still draws every saved look
as it always did.
