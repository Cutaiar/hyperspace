# Field: line shear

**What you see.** The picture sheared: the left side drops, the right side
rises, more the further from the middle. The sub band pushes it; your left
hand turns the line.

**How it is wired.**

```
scene ──────────────▶ displace.image ─▶ output.all
measure ────────────▶ displace.field
```

- **Measure** (`fx.measure.*`): **Along** line, **Out** value — at every pixel,
  its distance along **Angle** from the point, in frame heights × **Scale**. A
  scalar field (green cable): negative on one side, positive on the other.
- **Displace** (`fx.displace.*`): a scalar field pushes along its own **Angle**
  (`fx.displace.angle`, a quarter turn: up) by **Amount** × the value. So the
  push grows across the frame, and the two halves go opposite ways.

**Play it.** `lane:0` (sub) pushes `fx.displace.amount`; `hand:left.y` pushes
`fx.measure.angle`, which way the line counts.

**Try.** Make the two angles equal (both 0): each pixel is pushed along the line
it is counted on — the picture stretches out from the middle instead of shearing.
