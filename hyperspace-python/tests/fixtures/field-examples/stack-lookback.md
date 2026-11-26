# Stack: the look-back from public parts

**What you see.** party-tracer's tracer — the 16-cell's points and lines trailing
copies of the last second and a half — drawn by ordinary nodes: this is what a saved
look-back opens as since plan 90 (H2). Where the shape is bright, the wake behind it is
held back a little (shape hides wake, 0.3).

**On GRAPH** it is one folded group, **look-back** — the picture in, the wake out
(and the occluder and the faces' cover in) — as every saved look-back now opens and the
tracers starter lands; **+** opens it to the parts below.

**How it is wired.**

```
scene ─▶ curve ─▶ fade (keyed) ─▶ resize ─▶ delay ═(stack)═▶ trail ─▶ cut ─▶ cut.2 ─▶ composite.over
scene ─▶ matte ─────────────────────────────────────────────────▶ cut.mask
scene.cover ────────────────────────────────────────────────────────────▶ cut.2.mask
scene ──────────────────────────────────────────────────────────────────────────▶ composite.under ─▶ output.all
```

- **Curve** (`fx.curve.shape` 0): the old look-back's contrast, log₄ — here 1, so straight;
  it is in the patch because a hand row drives it (right pitch).
- **Fade**, keyed (`fx.fade.level` = 1 − darken; `key.fade.*`: peak, linear ramp, level 0,
  softness 1, keep colour): what each copy keeps, and its brightness as its coverage —
  the old look-back's "black is clear".
- **Resize** (`resize.size` 512 on the long side): the size the copies are kept at.
- **Delay** (`delay.depth` 24, `delay.every` Hz, `delay.hz` 15): the copies, 1/15 s apart.
- **Trail** (`fx.trail.level` 0.7, `fx.trail.fade` 0.76 s, lay over): each copy over the
  older ones by its coverage, fainter by its age.
- **Cut** by a **Matte** of the scene (peak, linear, key ⅛, soft ⅛ — `min(4 · peak, 1)`)
  and **Cut 2** by the faces' cover (`scene.cover`), each inverted at amount 0.3: the
  wake held back where the shape is bright or a face is drawn.
- **Composite** (add): the wake under the scene.

**Play it.** The right hand: height pushes the trail's level, depth its fade, roll how much
the shape hides the wake (both cuts), pitch the curve. The desk's knobs 16–22 as party-tracer's.

**Try.** Raise the delay's depth and lower its Hz: a longer, sparser trail. Set Trail's
**lay** to add and take the key off the fade: a brighter, summed glow. Wire a **Read**
from the delay to see one copy alone.
