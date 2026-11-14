# Distortion patches

23 whole-frame patches (`hyperspace.loadable/11`) for trying the three
distortion effects: Shake, Wave and Blocks (`docs/DISTORTION.md` has every
knob). They are not part of the app (nothing ships with it). Copy them
into the library's `loadable/` folder and they appear in the list:

```bash
cp presets/distort/*.json ~/Hyperspace/loadable/
```

Every one draws the Celestial tesseract with plaid faces through one
effect (the last through all three), with the six audio lanes on the six
rotation planes and the ghost hands on at 35%, as the kinetic presets do.

**How they are played.** A param takes one performer, so each patch gives
Amount to one:

- `distort-shake-*`, `distort-wave-*`, `distort-blocks-*`, `distort-all-three`:
  the **sub band** (`lane:0`) pushes Amount up from a small resting value,
  so the effect shows with no sound and hits with it. The right hand's
  height brings in the colour split (the smear on `shake-chroma`); the
  left hand's height moves the size knob the note names.
- `distort-hand-*`: no sound needed. The **right hand's height is Amount**,
  from nothing at the bottom; the left hand's height brings in the split.

To put Amount on something else, change that one route's source on the
graph. Each patch's note says what it is.

| Patch | What you see |
| --- | --- |
| `distort-shake-buzz` | A smeared side-to-side buzz |
| `distort-shake-chroma` | The frame circling, its three colours a third of a turn apart |
| `distort-shake-punch` | Hard snaps in and out about the centre |
| `distort-shake-jolt` | Random knocks that settle, with smear and fringe |
| `distort-wave-rows` | Rows sliding past each other on a sine |
| `distort-wave-spring` | The picture bunching and stretching sideways |
| `distort-wave-ripple` | Pond ripples from the centre, colours parting |
| `distort-wave-twist` | Rings turning against each other |
| `distort-wave-petals` | The picture growing seven petals |
| `distort-wave-slabs` | Slabs cut by a square wave |
| `distort-wave-static` | Thin rows thrown at random: a signal breaking up |
| `distort-blocks-shift` | 48 px cells each sliding its own way |
| `distort-blocks-sync` | Long strips out of step: a picture losing sync |
| `distort-blocks-zoom` | 16 px units in 4 × 4 blocks, magnified and shrunk |
| `distort-blocks-streaks` | Cells pulled into vertical streaks |
| `distort-blocks-turn` | A checkerboard snapping quarter turns |
| `distort-blocks-rings` | A turn running out from the middle in square rings |
| `distort-blocks-lens` | A lens in every cell |
| `distort-blocks-swap` | Cells trading places |
| `distort-all-three` | Wave into Blocks into Shake, all on the sub |
| `distort-hand-shake` | The buzz, raised by the right hand |
| `distort-hand-wave` | The ripples, raised by the right hand |
| `distort-hand-blocks` | The sliding cells, raised by the right hand |

`tests/test_distort_presets.py` opens each through the library's own load
and fails on any note or dropped route.
