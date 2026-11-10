# Plan 62: the 4D projection in the vertex shader

**Status: planned, not scheduled (2026-11-10). No current need** (the owner,
2026-11-10: no need for 4D instance fields yet). Needs plan 61.

## 1. Why

After plan 61 the field's copies (`field.py`) are still placed after the 4D-to-3D
step: one projection, drawn thousands of times. For copies at different
4D positions to look different, each needs its own projection. On the CPU
(numpy) that costs N times as much: fine for tens of copies, too slow for thousands.
On the GPU it is nearly free.

## 2. What changes

- **The vertex shaders** (`render.py`, the two that read `in_pos` and `in_w4`)
  take 4D points plus each object's or copy's pose and the 4D eye, and do the
  turn and divide themselves. `in_w4` is computed there, still multiplied into
  the clip w for perspective-correct uv.
- **Buffer formats** carry 4D points and per-instance poses.
- **Edge strokes**, today scaled on the CPU from projected points, move to the GPU.
- **The CPU parity oracle** (`geometry.project`) stays as the reference the GPU
  is tested against.

## 3. The hard part

The see-through shape is **painter-sorted on the CPU**, from the projected
depths. With projection on the GPU those depths are no longer on the CPU. The
options: keep a CPU projection for sorting only (sorting cost, not drawing
cost), sort on the GPU, or move to order-independent transparency. That choice
decides this plan's size and is the first thing to settle.

## 4. Tests

The golden images unchanged at default, and the GPU's points matching
`geometry.project` within float tolerance on every shape.
