# Stack: a trail

**What you see.** The wireframe with a tracer behind it: copies of the last half
second, each fainter by its age. The mid band lengthens the tail.

**How it is wired.**

```
scene ─▶ delay.image          delay ═(stack)═▶ trail.stack ─▶ composite.over
scene ──────────────────────────────────────────────────────▶ composite.under ─▶ output.all
```

- **Delay** (`delay.depth` 16, `delay.every` Hz, `delay.hz` 30): the frames the trail is
  made of — its Depth is how many copies, its rate how far apart.
- **Trail** (`fx.trail.*`): **Level** the newest copy's strength; **Fade** the seconds
  in which a copy's strength halves; **Lay** add (they sum) or over (each covers the
  older where its alpha is — key the scene's black clear first, with a linear ramp, for
  the old look-back's look).
- **Composite** (add): the trail laid on the shape now.

**Play it.** `lane:1` pushes `fx.trail.fade`.

**Try.** Lay over with Black is clear on the scene (linear ramp, level 0, softness 1):
each copy covers the older ones only where it is bright. A Curve after the trail
(`curve`, Shape up) keeps only its brightest parts.
