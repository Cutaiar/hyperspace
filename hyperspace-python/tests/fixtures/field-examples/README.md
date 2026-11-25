# Field examples

One loadable patch per effect that changed for fields (plan 67), each with a short
Markdown: what you see, how it is wired, how to play it, what to try. Their home is
here, the library's `loadable/field-examples/` on the Drive — the one place patches
are saved. The repository keeps a copy only as test fixtures
(`hyperspace-python/tests/fixtures/field-examples/`), which `tests/test_field_examples.py`
opens through the library's own load.

| Patch | Shows |
| --- | --- |
| `field-rings-lens` | Point → Rings (direction) → Displace: a lens |
| `field-line-shear` | Line (value) → Displace along its angle: a shear |
| `field-self-bend` | To field (the scene's brightness) → Displace: the picture bends itself |
| `field-wave` | Wave taken apart: Point → Rings → Waveform, × a second Rings' direction (Combine) → Displace |
| `field-blocks` | Blocks taken apart: Cells → Waveform → Cell action, with a second Cells' place in the cell → Displace |
| `field-trip` | Trip warp taken apart, near: Noise (flow) × Rings, plus a Point scaled (the zoom) → Displace |
| `field-knob` | Any knob takes a field: Point → Rings (value) → Wave's Amount, at a depth on the wire |

A **field** is a number (or a pair) at every pixel: green cables on GRAPH, grey
when shown as a picture.
