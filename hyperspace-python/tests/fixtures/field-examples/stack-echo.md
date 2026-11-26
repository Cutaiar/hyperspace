# Stack: an echo

**What you see.** The wireframe, and a ghost of it as it was two thirds of a second
ago, added over it. The sub band pushes the ghost further back.

**How it is wired.**

```
scene ─▶ delay.image          delay ═(stack)═▶ read.stack ─▶ composite.over
scene ─────────────────────────────────────────────────────▶ composite.under ─▶ output.all
```

- **Delay** (`delay.depth`, `delay.gap`): keeps the last 32 frames, one every 1/30 s —
  about a second. Its own picture is still last frame's; its **stack** is what it keeps.
- **Read** (`fx.read.*`): **At** is how many of those frames back, 0 the newest; at 20
  it shows the frame from 20 × 1/30 s ago. **Between** blends two frames for a fraction,
  or takes the nearer.
- **Composite** (add): the echo laid on the shape now.

**Play it.** `lane:0` (sub) pushes `fx.read.at`.

**Try.** A second Read at another At, laid on too: a ripple of copies. Raise the
delay's Gap: the same 32 frames reach further back. Drop a field on At — see
`stack-slit`.
