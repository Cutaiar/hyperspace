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

## Results (2026-08-21)

All exit criteria met (83 tests green, ruff clean); side-by-sides awaiting
the user's eye, which is the standing final judge.

- **Pipeline decision:** the CPU transforms through the parity-proven
  `geometry.project()` and the GPU only rasterises — at ≤600 verts/1200
  edges the numpy cost is nothing, and reusing the proven path makes visual
  agreement structural rather than aspirational.
- **Blending decision (recorded per task 2):** alpha-over in painter order,
  *not* additive. The additive suggestion existed to dodge a CPU depth
  sort; the CPU computes every edge depth anyway, so the argsort is free
  and the reference compositing is reproduced exactly.
- **Line-width risk materialised as predicted:** 1 px GL lines lost the
  near-edge weight hierarchy, visibly on the tesseract/5-cell shots. Edges
  are now screen-space quads at the reference's exact width formula
  (0.5–2 px depth- and brightness-scaled; heavy shapes 0.35–1.2 px), with
  sub-pixel widths folded into alpha. End caps are butt rather than round —
  invisible in practice because vertices sit on every edge end.
- **Comparison shots** (`docs/plans/assets/02-*.png`, judge shapes at the
  golden generic pose): mean absolute pixel delta vs the HTML canvas —
  5-cell 0.10, tesseract 0.27, 120-cell 1.05, Clifford torus 0.75 (of
  255). Regenerate any time with `tools/compare_render.py`.
- **Performance:** offscreen raw-draw at 1080p exceeds 60 fps on the
  120-cell and 20,20-duoprism by a wide margin (test-gated; hundreds of
  fps in practice on this machine). The windowed app is vsync-bound.
- **`uv run hyperspace`** opens the GLFW window: drag orbit, ←/→ shape,
  space pause, P points, R reset, [/] brightness, ,/. speed, 1–6 plane
  toggles. Angle integration is the reference's `frame()` update with
  `PLANEDRIVE ≡ 1` until plan 03.
