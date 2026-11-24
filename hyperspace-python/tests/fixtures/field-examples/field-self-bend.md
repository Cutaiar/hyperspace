# Field: self bend

**What you see.** The shape bending itself: its bright parts push one way, the
dark ground pulls the other, so the light smears along the angle. The sub band
pushes it; your right hand turns the way.

**How it is wired.**

```
scene ─┬────────────▶ displace.image ─▶ output.all
       └▶ tofield ──▶ displace.field
```

- **To field** (`fx.tofield.*`) reads a picture as a field: **Read** luma,
  **About** signed — mid-grey is 0, black −1, white +1. A scalar field (green
  cable). It is how a picture is wired into a port that takes a field: a picture
  straight into `displace.field` is refused, in words that name To field.
- **Displace** (`fx.displace.*`): the scalar pushes along **Angle** by **Amount**
  × the value.

**Play it.** `lane:0` (sub) pushes `fx.displace.amount`; `hand:right.y` pushes
`fx.displace.angle`.

**Try.** About unsigned: black is 0, so the dark ground stays still and only the
light moves. Read red/green: the picture's colours become a vector field, and
each colour pushes its own way.
