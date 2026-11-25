# Field: Hue cycle, taken apart

**What you see.** The shape in turning rainbow bands, diagonal stripes bent into rings
round the middle — Hue cycle as it always looked. The sub band widens the bands; your
right hand turns every hue round the wheel.

**How it is wired.**

```
scene ──────────────────────────────────────▶ hueturn.image ─▶ output.all
line ─▶ scale.image ─┐
                     ├─▶ combine ─▶ scale.3.image
rings ─▶ scale.2.image ─┘                    │
                          scale.3 ─(depth 360)▶ hueturn.turn
```

- **Hue turn** (`fx.hueturn.*`) turns the frame's hues by its clock (**Speed**) and by
  **Turn**, in degrees. **Paint** puts the frame's brightness in the turning hue (so a
  white wireframe comes out rainbow); **Saturation** runs to 2.
- **The bands are a field into Turn**, what Hue cycle hid inside it. **Line**
  (`fx.line.*`, Angle 45°, Scale √2) counts the diagonal; **Rings** (`fx.rings.*`,
  Scale 2) the distance from the middle. Two **Scale**s weigh them (× 0.5 each: Hue
  cycle's Rings 0.5), **Combine** adds them, and a third Scale is Hue cycle's
  **Spread** (`scale.3`, × 0.8). The cable into Turn has a depth of 360: one unit of the
  field is one whole turn of the wheel.

**Play it.** `lane:0` (sub) pushes the bands' × (`scale.3`'s), as it pushed Spread;
`hand:right.y` pushes `fx.hueturn.turn`.

**Try.** Change the two weights for more rings or more stripes, or swap Line's Angle.
Wire a Point into Rings' `field` and the rings follow it. Every look saved with Hue
cycle opens as this patch, the same picture.
