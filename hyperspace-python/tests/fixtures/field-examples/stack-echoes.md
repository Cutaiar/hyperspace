# Stack: several echoes

**What you see.** The wireframe turning, and six copies of it behind, each 0.2 s
older and fainter than the last — about a second of its past, spread out. The sub
band slows the copies down: they spread further apart.

**How it is wired.**

```
scene ─▶ delay.image          delay ═(stack)═▶ trail.stack ─▶ composite.over
scene ──────────────────────────────────────────────────────▶ composite.under ─▶ output.all
```

- **Delay** (`delay.depth` 6, `delay.every` Hz, `delay.hz` 5): takes a picture five times
  a second and keeps the last six. **The spacing between echoes is the delay's rate**:
  at 30 Hz (as in `stack-trail`) the copies sit on top of one another and read as one
  smear; at 5 Hz they come apart.
- **Trail** (`fx.trail.*`): lays all six, oldest first. **Level** the newest copy's
  strength; **Fade** the seconds in which a copy's strength halves (0.6: the oldest, a
  second back, is about a third as bright); **Lay** add.
- **Composite** (add): the echoes laid on the shape now.

**Play it.** `lane:0` (sub) pushes `delay.hz` down: fewer pictures a second, wider gaps.

**Try.** Depth up to 12 at the same rate: twice as far back. The rate on a tempo unit
(**every** 1/8): an echo on every eighth note. Lay over, with Black is clear on the
scene (linear ramp, level 0, softness 1): each echo covers the older ones where it is bright.
