# Cloud agent prompt: plan 64, recursive geometry ready for its PR

Paste everything below the line into a new Claude Code cloud session on the
`hyperspace` repo.

---

You are finishing plan 64 of Hyperspace, a live-visuals app (Python +
moderngl, in `hyperspace-python/`). Dillon's branch
`claude/tender-heisenberg-knlvgq` zooms into nine fractals forever with
geometry alone:
- **3D:** the Sierpinski tetrahedron, octahedron and icosahedron flakes, the
  Menger sponge, Cantor dust and the Vicsek cross.
- **4D:** the Sierpinski 5-cell, 4D Cantor dust and the 4D Vicsek cross.

The owner wants it improved **before** its PR is opened. You build on it and
open that PR as a draft. The owner reviews and merges; you never merge.

## What the branch does (read `hyperspace/fractal.py`, 532 lines, first)

- **`fractal.frame`** walks the shape from the top each frame. It splits any
  cell bigger than `SPLIT` of the screen, culls what the eye can't see
  (including the 4D eye along w), and stops at `BUDGET` = 30,000 edges.
- **New edges only:** a split adds only the edges its children add (`new_E`).
  New detail fades in; cells about to pass the eye fade out.
- **Re-rooting:** `fractal.step` re-roots the view into the child cell under
  the screen centre once zoom passes `Z_IN` = 4. Zoom stays in about
  [1.7, 4), so float32 never runs out. `Dive.path` is the only state kept.
- **Faces at every scale.** `render.draw_scene` takes the fractal's geometry
  through four `if frac is not None` special cases.

## Decisions the owner has made (2026-11-18). They overrule any other document.

1. **Stateless and re-rooting stay.**
2. **World space is a hard requirement.** Cells are world geometry like every
   other shape, never screen-space copies. The existing `field.py` instances,
   a 2D offset, scale and alpha applied after projection, are the wrong model
   for this. Don't build on them.
3. **Unsorted additive blending:** render it and let the owner look before
   anything depends on it.

## The work, in order

1. **Bring the branch up to date.** Branch `plan-64-recursive-geometry` from
   `origin/claude/tender-heisenberg-knlvgq`, then merge `origin/main` in. Keep
   Dillon's commits as they are.
2. **One shape interface.** Replace the four `frac` special cases in
   `render.draw_scene` with a provider that every shape kind implements,
   something like `frame(view, w, h) → geometry`:
   - fixed shapes return their cached `geom`;
   - scenes return their layers;
   - fractals return `fractal.frame`.

   The depth cue's fixed ends, `dens_m`, the stroke-weight rule and the
   frame's own triangles and uvs become fields of what the provider returns,
   not branches. **Goldens must not move.** This is a pure refactor for every
   non-fractal shape.
3. **World-space GPU instancing for fractal cells.**
   - Upload the fractal's mesh once (its `V`, `new_E` and solid triangles),
     plus a per-cell instance buffer of (4D centre, scale, alpha).
   - The vertex shader does the placement, the view turn, the 4D divide and
     the 3D projection. The cull and the split decision stay on the CPU, so
     only a few numbers per cell go up each frame.
   - Read `docs/plans/61-unified-4d-world.md` and `62-gpu-4d-projection.md`
     first. This is a narrow, fractal-only version of plan 62. Its §3 problem,
     the painter sort, is exactly what decision 3 is about.
   - Keep the CPU path as the oracle and the fallback, and test that the GPU
     points match it within float tolerance.
   - Add a view toggle for the line order:
     - **sorted**: today's CPU painter order, which is correct;
     - **additive**: unsorted, all on the GPU.

     Keep sorted as the default until the owner has looked.
4. **The comparison the owner asked for.** With the drive-the-app skill
   (`.claude/skills/drive-the-app/SKILL.md`), render the same dives (the
   tetrahedron, the Menger sponge and the 5-cell, each with faces off and on)
   in sorted and additive modes. Make side-by-side stills and one short video
   each. Commit them under `docs/plans/assets/64-recursive-geometry/` and link
   them at the top of the PR body.
5. **The branch's own leftovers:**
   - **The cull ignores the shape's world offset** (plan 59 world objects,
     built). Fix it, so a grabbed or moved fractal culls correctly.
   - **The dive isn't saved**, so a loaded preset starts at the top. Saving it
     is a format change. Write it up with a recommendation as a register row
     marked "(rec) — pending the owner", and don't build it.
6. **A rig bench.** `tools/fractal_bench.py` times the CPU path against the
   GPU path, using the renderer's per-node GPU timer
   (`ctx.query(time=True)`, `render.py` around line 903) plus wall time for
   the CPU side. It covers each fractal at a few depths. Your cloud machine is
   Mesa software, so its numbers mean nothing; put the command in the PR body
   for the owner to run on the rig (an M3 Max).

## Read first

- `REVIEW.md` (repo root), `hyperspace-python/docs/CHECKPOINT.md`,
  `docs/DECISIONS.md`, `docs/ARCHITECTURE.md` §3–§4 and `docs/GLOSSARY.md`.
- `docs/ENGINEERING.md`: the shape catalogue rows 102–109, the Fractals and
  4D fractals notes the branch added, and §15–§16.
- `tests/test_fractal.py` and `tools/drive_fractal.py` on the branch.

## Rules

- **Goldens must not move**, except for rows the branch itself added to
  `tests/golden/shape_digests.json`. Anything else that moves: stop and
  report. `tests/fixtures/` needs `git add -f`.
- A change to an existing saved format: stop and report.
- Never run anything against `~/Hyperspace` or a Google Drive path.
- Don't modify `.github/workflows/`.
- Report faithfully: failures with their output, a skipped step as skipped.

## Your numbers (use only these)

- Plan doc: `docs/plans/64-recursive-geometry.md`, plus a line in
  `docs/plans/README.md` and `ARCHITECTURE.md`'s module table for
  `fractal.py`.
- Decision register rows **882–891** in `docs/DECISION-REGISTER.md`.
- Hand checks **679–688**, group **DZ**, in `docs/plans/11-hand-checks.md`:
  - the look of sorted against additive;
  - the feel of a long dive in and back out;
  - a grabbed fractal;
  - each fractal's frame time on the rig.

## Testing

- Cloud setup: `.claude/hooks/session-start.sh` (or drive-the-app §0).
- `uv run pytest -q` from `hyperspace-python/` must be green.
- New tests:
  - the provider gives byte-identical frames for fixed shapes;
  - GPU against CPU point parity;
  - the cull with a world offset;
  - instance-buffer contents for a known dive.

## PR

Open a **draft** PR from `plan-64-recursive-geometry` to `main` with
`gh pr create --draft`. Credit Dillon's branch in the body. Body headings:
- **Why**
- **What** (Dillon's work, then yours)
- **Sorted vs additive** (the comparison links)
- **Testing** (counts verbatim)
- **On the rig** (the bench command)
- **Restart or hot reload**
- **Owner decisions pending**

When you finish, reply with: the PR URL, the head commit, what's done and not
done, test counts, the rows and checks used, and the open questions.
