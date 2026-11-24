# Field: Trip warp, taken apart

**What you see.** The frame swims: its rim slides along drifting noise while the
middle holds still, the whole frame a little zoomed in. Near the picture of
`party-noita`'s Trip warp — built from eight primitives instead of one file.

**How it is wired.**

```
noise ─▶ combine.image        rings ─▶ combine.field
combine ─▶ scale ─▶ combine.2.image
point ─▶ scale.2 ─▶ combine.2.field
combine.2 ─▶ displace.field;  scene ─▶ displace.image ─▶ output.all
```

- **Noise** (`fx.noise.*`): **Out** flow — two octaves of noise as a vector, **Scale**
  blobs to a frame height, sliding at **Drift**. The way each pixel swims.
- **Rings** (`fx.rings.*`): **Out** value — the distance from the middle, so the swim is
  nothing at the centre and grows toward the edges.
- **Combine** (`fx.combine.*`): **How** multiply — the swim, weighted by that distance.
- **Scale** (`fx.scale.*`): **×** how deep the swim is (Trip warp's Amount × 0.4).
- **Point** (`fx.point.*`) and **Scale.2** (`fx.scale.2.*`): each pixel's offset from the
  middle, **×** a small negative number — the zoom in (up to 10 %).
- **Combine.2** (`fx.combine.2.*`): **How** add — the swim and the zoom, one push.
- **Displace** (`fx.displace.*`): moves the picture by that push, **Amount** 0.5 (its top;
  the two Scales are doubled for it).

Trip warp's own knobs, one by one: Amount → Scale's **×** (0.4 × Amount) and Scale.2's
**×** (−0.2 × min(1, 1.5 Amount)); Scale and Drift → Noise; Speed → Noise's speed.

**Play it.** `hand:right.y` pushes `fx.scale.mul` (a deeper swim); `hand:right.z` pushes
`fx.noise.scale` (bigger or finer noise); `hand:left.y` pushes `fx.noise.drift`.

**Try.** Move the Point: the calm middle moves with it (wire the same Point into Rings'
`field`). Swap Rings for a Line: the swim grows across the frame instead of outward.
Wire the Noise straight into Displace: the whole frame swims, the middle too.

**Near, not equal.** Trip warp counts in fractions of the frame's width and height,
the field nodes in frame heights: its calm middle is an oval fitted to the frame where
the patch's is round, and its swim is stretched across the width where the patch's is
as long across as up. On the frame's axes the two agree; toward the corners the patch
swims up to about a quarter more up and down (`tests/test_trip_patch.py`). The zoom is
Trip warp's exactly. The Trip warp effect itself still draws every saved look as it did.
