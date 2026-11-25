# Field: a field on a knob

**What you see.** The shape, waved: still around the middle of the frame, rippling
more and more toward the edges. The sub band pumps the whole wave; your right hand
slides where the still middle is.

**How it is wired.**

```
scene ─────────────────────────▶ wave.image ─▶ output.all
point ─▶ rings.field
rings ─(depth 0.06)────────────▶ wave.amount
```

- **Any knob takes a field.** A green cable into a knob — dropped on the knob's
  row on GRAPH — makes that knob a value at every pixel: **value + depth × field**.
  The knob's own value (and anything routed onto it) is the base; the field spreads
  it across the frame.
- **Point** (`fx.point.*`): where the still middle sits, **X** and **Y**.
- **Rings** (`fx.rings.*`), **Out** value: each pixel's distance from the Point, in
  frame heights — 0 at the Point, about 0.9 in a corner.
- **Wave** (`fx.wave.*`): its **Amount** is 0, and the field adds 0.06 × the
  distance, so a corner's Amount is about 0.05. The depth is the wire's: right-click
  the cable, **depth ▸**, for a share of the knob's range (or minus one, to turn it
  round: strong in the middle, still at the edges, from a higher Amount).

**Play it.** `lane:0` (sub) pushes `fx.wave.amount`, the base under the field;
`hand:right.y` pushes `fx.point.x`.

**Try.** Wire the same Rings into **Waves** as well: the wave tightens outward.
Swap Rings for Line: a wave that grows across the frame. Not every knob takes one:
Along, Push and Shape are choices, Steps counts and Drift is a rate — GRAPH says so
in words when you drop a field on them.
