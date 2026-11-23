# Field: rings lens

**What you see.** The shape, pushed out from the middle of the frame like a lens
breathing. The sub band pumps it; your right hand slides where the middle is.

**How it is wired.**

```
scene ──────────────▶ displace.image ─▶ output.all
measure ────────────▶ displace.field
```

- **Measure** (`fx.measure.*`) makes the field: **Along** rings (distance from
  the point), **Out** direction — at every pixel, the unit arrow pointing away
  from the point. A vector field (green cable).
- **Displace** (`fx.displace.*`) moves each pixel of its picture by the field on
  its `displace.field` port: **Amount** × the arrow, in frame heights. With a
  field wired, its aux is not read.

**Play it.** `lane:0` (sub) pushes `fx.displace.amount`; `hand:right.y` pushes
`fx.measure.cx`, the point's X.

**Try.** Out value instead of direction: the rings' distance becomes a number,
and Displace pushes every pixel along its **Angle** by it — the frame slides
more the further from the point. Along spokes and Out direction: a swirl.
