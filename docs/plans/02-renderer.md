# Plan 02 — Renderer

**Blueprint stage 2.** The moderngl window: all 18 shapes drawn live, driven
by the plan-01 transform functions, visually matching the HTML.

## Prerequisites

Plan 01 complete (geometry parity exact — the renderer trusts it).

## Deliverables

```
hyperspace/render.py     # GL pipeline, window, frame loop
hyperspace/app.py        # entry point: window + keyboard + shape selection
tests/test_render.py     # offscreen-render smoke + screenshot comparisons
docs/plans/assets/       # side-by-side comparison shots (checked in)
```

## Tasks

### 1. Pipeline

moderngl + GLFW, GL 4.1 core (macOS ceiling; fine everywhere else).

- Per frame on CPU (numpy): integrate angles
  (`ang[p] += dt·speed·RATE[p]·PLANEDRIVE[p]`, with `PLANEDRIVE ≡ 1` until
  plan 03 — same substitution the HTML makes with no source), compose the
  six-plane rotation into one 4×4, upload as a uniform.
- Vertex shader: apply rotation, 4D→3D `k = D4/(D4−w)`, yaw/pitch, standard
  perspective. Pass post-rotation `w` to the fragment stage for depth cueing.
- Edges as `LINES` with per-edge alpha `(0.10 + 0.90·t²)·B`, `t` = normalised
  w-depth, `B = brightness · dens`, `dens = clamp(340/edges, .42, 1)` —
  ENGINEERING §3, load-bearing on the 120-cell.
- Vertices as red points, radius and alpha depth-cued.

### 2. Blending decision

The HTML painter-sorts edges (a Canvas-2D necessity). In GL, try **additive
blending first** — order-independent, and the glow/recede look likely
survives. Judge it on the comparison shots (task 4). If additive visibly
diverges (the HTML's compositing is alpha-over, and dense shapes may bloom
differently), fall back to CPU painter sort — `argsort` on ≤1200 edge depths
per frame is nothing. Record the decision and why in *Results* below.

### 3. Interaction

Drag orbit (yaw/pitch with the same sensitivity feel), scroll/keys for shape
selection and brightness, DPR-aware framebuffer sizing, plane on/off toggles,
point toggle. Keyboard map mirrors the HTML where it exists.

### 4. Verification

- Offscreen (FBO) render test: every shape draws without GL errors at two
  sizes; runs headless in CI where a GL context is available, else marked
  local-only.
- **Screenshot parity:** for the 5-cell, tesseract, 120-cell and Clifford
  torus, render at the exact angle sets golden geometry traces used; capture
  the HTML at the same angles via the plan-00 harness; compose side-by-sides
  into `docs/plans/assets/`. Judged by eye — the bar is "visually
  indistinguishable", per BLUEPRINT §5.
- **Performance:** ≥60 fps at 1080p on this machine for the 20,20-duoprism
  (800 edges) and 120-cell (1200 edges); measure and record.

## Exit criteria

- [ ] All 18 shapes render, orbit, and toggle correctly.
- [ ] Side-by-side shots committed; blending decision recorded with them.
- [ ] 60 fps criterion met and the numbers written into *Results*.
- [ ] `app.py` runs from a clean checkout: `uv run hyperspace`.

## Risks / notes

- Line width >1 px is effectively unsupported in core-profile GL. If hairline
  edges look too thin next to the HTML at high DPR, the fix is screen-space
  quads (a geometry expansion), not `glLineWidth`. Don't gold-plate: try
  1 px first, judge on the comparison shots.
- Keep `render.py` free of any audio/input imports — plan 03 plugs in through
  `PLANEDRIVE` only. That boundary is what keeps the stages independent.
