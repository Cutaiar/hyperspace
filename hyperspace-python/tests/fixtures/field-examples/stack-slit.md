# Stack: a slit-scan

**What you see.** The wireframe smeared through time across the frame: the left edge
is now, the right edge about a second ago, so a turning shape leans and stretches.
The right hand's height turns the direction time runs.

**How it is wired.**

```
scene ─▶ delay.image          delay ═(stack)═▶ read.stack ─▶ output.all
line ─(depth 16)──────────────────────────────▶ read.at
```

- **Any knob takes a field**, and Read's **At** is a knob: a field on it gives every
  pixel its own moment. That is a time displace — no node of its own.
- **Line** (`fx.line.*`): the distance along its **Angle**, in frame heights.
- **Read** (`fx.read.*`): **At** 14 frames back in the middle, ± 16 × the line across.
- **Delay** (`delay.depth` 32, `delay.every` Hz, `delay.hz` 30): what there is to read.

**Play it.** `hand:right.y` pushes `fx.line.angle`.

**Try.** Rings instead of Line: now in the middle, the past toward the edges. A
Waveform between Line and At: bands of time. Between on nearest: hard steps.
