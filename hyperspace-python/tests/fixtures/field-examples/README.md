# Field examples

One loadable patch per effect that changed for fields (plan 67), each with a short
Markdown: what you see, how it is wired, how to play it, what to try. Their home is
here, the library's `loadable/field-examples/` on the Drive — the one place patches
are saved. The repository keeps a copy only as test fixtures
(`hyperspace-python/tests/fixtures/field-examples/`), which `tests/test_field_examples.py`
opens through the library's own load.

| Patch | Shows |
| --- | --- |
| `field-rings-lens` | Measure (rings, direction) → Displace: a lens |
| `field-line-shear` | Measure (line, value) → Displace along its angle: a shear |
| `field-self-bend` | To field (the scene's brightness) → Displace: the picture bends itself |
| `field-wave` | Wave taken apart: Measure → Waveform, × a second Measure's direction (Combine) → Displace |

A **field** is a number (or a pair) at every pixel: green cables on GRAPH, grey
when shown as a picture.
