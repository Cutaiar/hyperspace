# Dream: party-wake as it opens now

**What you see.** party-wake's wake — the 16-cell's trail of copies, held back where the
shape is bright — with the dream on it: Deep Dream's loops and swirls grown into the
trail where it is lit, laid over it at half strength. With no dream worker (the cloud,
a laptop without torch) the dream passes its picture through and its node says so: you
see the trail alone. This is what a saved dream opens as since plan 90 (H3).

**On GRAPH** it is two folded groups: **trail** (the look-back's parts, as
`stack-lookback`) and **dream** — the picture in, the dreamed picture out; **+** opens
each to the parts below.

**How it is wired.**

```
… trail ─▶ cut ─▶ cut.2 ─┬─▶ resize.2 (keyed) ─▶ dream ─▶ hueturn ─▶ curve.2 ─▶ fade.2 ─▶ composite.2.over
                         └──────────────────────────────────────────────────────────────▶ composite.2.under
scene ─▶ composite.under          composite.2 ─▶ composite.over          composite ─▶ output.all
```

- **Resize 2** (`resize.2.size` 512 on the long side), keyed (`key.resize.2.*`: peak, linear
  ramp, level 0, softness ¼, keep colour): the size the dream works at — so its cost —
  and where it may dream: four times the trail's brightness is its coverage, the old
  dream's mask.
- **Dream** (`fx.dream.*`: layer conv3_3, 2 passes of strength 0.03, jitter 8, scales
  "2 alt", Hold 0.08): its picture is the dreamed bitmap. Hold below 1 keeps what it
  dreamed and dreams it again — deeper, lingering; at 1 each picture is dreamed anew.
- **Hue turn** (`fx.hueturn.sat` 1.2, turn 0, paint 0, still): the old dream saturation.
- **Curve 2** (`fx.curve.2.shape` 0): the old dream contrast — straight here, in the patch
  because a desk knob drives it.
- **Fade 2** (`fx.fade.2.level` 0.5): the old dream's mix × (1 − darken).
- **Composite 2** (over): the dream laid on the trail; **Composite** (add) the whole wake
  under the scene.

**Play it.** The right hand as party-wake's: roll turns the dream's hue, pitch its
brightness; the desk's knobs 18 and 19 the trail's and the dream's grade.

**Try.** Set the dream's **Hold** to 1: it follows the trail at once and dreams shallow.
Lower Resize 2 to 256: four times cheaper, coarser forms. Wire the dream straight into
`output.all.image` — the dreamed bitmap alone, to do whatever you like with after.
