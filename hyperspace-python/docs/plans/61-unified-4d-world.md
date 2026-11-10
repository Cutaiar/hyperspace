# Plan 61: one 4D world

**Status: planned, not scheduled (2026-11-10).** Needs plan 59 merged.
Independent of plan 60. Plan 62 builds on this.

## 1. What changes

Today each 4D shape is turned and projected down to 3D **in its own frame**
(`geometry._to3`: six plane turns, then the 4D perspective divide with that
shape's own `view.depth4`) and then placed in a 3D world, where the hands are.

In one 4D world every object has a 4D pose (plan 59's `Pose`, now with
w ≠ 0 and qL ≠ qR allowed), and there is **one 4D eye** and **one 4D divide in
world space**. An object can drift through w, objects can share a 4D space,
and a hand could push something into the fourth dimension.

With the shape at the origin and the 4D eye not turned, the maths is identical
to today's, so **default frames stay byte-identical** and the golden images
survive. Only things moved in w look different.

## 2. What it touches

| Part | Change |
| --- | --- |
| `geometry.py`: `_to3`, `world_points`, `shape_world`, `project_h`, `project3`, and `project`, the parity oracle the golden traces use | Take an object pose and the 4D eye instead of `ang`; `depth4` becomes one world value |
| `view.py`: `body`, `held`, `integrate`, the 3D switch | Act on the object's pose instead of folding into `ang` |
| Scenes with layers (`geometry._build_scene`) | Each layer becomes a child object, at its own spin |
| Ghost hands | At w = 0, which the default 4D eye shows exactly as now. Turning the 4D eye tips them into w |
| `field.py` instances | **Stay placed after the 4D-to-3D step, in 3D.** The shape is still projected once and drawn per copy, at no new cost |
| GPU shaders, painter sort, depth pass, post effects, outputs, graph | Unchanged: they already work on 3D points plus the 4D divisor `in_w4` |

The totem (`rot.phase.*`) becomes the shape object's 4D orientation.

## 3. Open questions for the owner

- **Where the 4D eye sits and whether it can turn.** Turning it moves
  everything, hands included, through w.
- **Whether `view.depth4`** becomes the eye's distance, or stays per shape as a
  scale on the object.

## 4. Tests

Byte-identical frames at the default; a shape moved in w projects as a single
4D divide predicts; layers as child objects draw as the scene did.
