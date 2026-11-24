# Field: Wave, taken apart

**What you see.** Ripples in a pond: rings from the middle squeezing the picture in
and out, the colours parting at the crests. The same picture as the Wave effect's
`distort-wave-ripple` — built from five primitives instead of one file.

**How it is wired.**

```
point ─▶ rings.field, rings.2.field
rings ─────▶ waveform ──────────────▶ combine.field
rings.2 ───────────────────────────▶ combine.image ─▶ displace.field
scene ─────────────────────────────────────────────▶ displace.image ─▶ output.all
```

- **Point** (`fx.point.*`): where the rings start, **X** and **Y**; one Point feeds
  both Rings, so they always agree.
- **Rings** (`fx.rings.*`): **Out** value — at every pixel,
  its distance from the middle, in frame heights.
- **Waveform** (`fx.waveform.*`): that distance counted in **Waves** and laid
  with a **Shape** (sine), drifting outward at **Drift** waves a second; **Steps**
  would flatten it into slabs. A scalar, −1 … 1: how far to push here.
- **Rings.2** (a second Rings, its own knobs): **Out** direction — the way out
  from the middle. (**Out** across instead turns it a quarter turn: the rings slide
  round rather than squeeze.)
- **Combine** (`fx.combine.*`): **How** multiply — the way out, scaled by the wave.
- **Displace** (`fx.displace.*`): moves the picture by that, **Amount** in frame
  heights; **Split** parts the colours along the push.

Wave's own knobs, one by one: Along → which node both measures are (Line, Rings or Spokes); Push → Rings.2's
**Out** (squeeze: direction, slide: across); Waves, Shape, Drift, Steps → Waveform;
Angle → both (a Line's); Centre → the Point; Amount and Split → Displace.

**Play it.** `lane:0` (sub) pushes `fx.displace.amount`; `hand:right.y` pushes
`fx.displace.split`; `hand:left.y` pushes `fx.waveform.waves`.

**Try.** Wire the Waveform into something else as well — a second Displace on
another picture, or straight into an output to see the field itself (grey rings).
That is what taking Wave apart buys: one wave, many readers. Two Lines instead of Rings, and
Waveform Shape square: Wave's rows-slipping slabs.

**Not quite byte for byte.** The five passes draw the Wave file's picture to the bit
for a smooth wave; with a hard one (square, saw, Steps) a pixel exactly on a slab's
edge can land on the other side (`tests/test_wave_patch.py` says why). The Wave
effect itself still draws every saved look as it always did.
