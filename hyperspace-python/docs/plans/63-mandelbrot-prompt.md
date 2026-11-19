# Cloud agent prompt: plan 63, a live Mandelbrot node

Paste everything below the line into a new Claude Code cloud session on the
`hyperspace` repo.

---

You are building plan 63 of Hyperspace, a live-visuals app (Python + moderngl,
in `hyperspace-python/`). Build it as one draft PR to `main`. The owner reviews
and merges; you never merge.

## The goal

A Mandelbrot generator that people explore live with their hands or a
controller. **Right now the goal is a performant first version, not a perfect
one.** The owner will tune performance on the rig, an M3 Max with a 40-core GPU.
Your cloud machine renders on Mesa's software rasteriser, so its frame times
mean nothing: build the tools the owner runs on the rig, and test correctness
here.

Decisions the owner has made (2026-11-18). They overrule any other document:

1. **Every term is a control**, as in 2swap's "Mandelbrot's Evil Twin": the
   iteration z → z^p + c, with the start z₀, the constant c and the exponent p
   all exposed. z₀ = 0 with c varying is the Mandelbrot set; c fixed with z₀
   varying is a Julia set; a blend tilts between them. A whole-number p (2–8)
   is required. A fractional p is a stretch goal.
2. **A selectable render target: 540, 810 and 1080 lines** (0.5k, 0.75k, 1k),
   rendered at that size and upscaled to the output, for performance tuning.
   It is a param, so it can be switched live.
3. **Perturbation first, an endless loop at a Misiurewicz point as the
   fallback, and no double-float.**
4. **Control sensitivity scales with the zoom**, so a hand movement moves the
   picture about the same amount on screen at any depth.
5. **Colour by steps.** Output the smooth escape count (n + 1 − log₂ log|z|)
   so Palette's gradient mode can colour it. Inside the set, output the
   convergence time from periodicity checking as a separate choice. A coloured
   interior can't be skipped, so offer interior black (fast) or coloured
   (full cost).

## Build in this order and stop where time runs out

Each stage is a commit that passes tests on its own.

1. **float32 direct.**
   - A generator node: an fx effect file or a picture node, whichever fits the
     graph better. Read `docs/ARCHITECTURE.md` and decide; record it in
     DECISIONS.
   - Params: centre, zoom, z₀, c (the Julia constant), the slice blend, p,
     the iteration cap, render size, the interior mode and an output mode
     (step count as brightness, or a built-in ramp).
   - Speed-ups: the closed-form cardioid and period-2 bulb test (p = 2 only),
     and periodicity checking with an early stop.
   - Zoom-scaled sensitivity: a hand route or knob on a term moves it by an
     amount proportional to the view width. Decide where the scaling lives,
     in the node or in a route modifier, and say why.
2. **The rig bench.** `tools/mandel_bench.py` renders a fixed set of views at
   each render size and a few iteration caps, using the renderer's existing
   per-node GPU timer (`render.py` around line 903, `ctx.query(time=True)`).
   It prints a table of milliseconds. The owner runs it on the rig; put the
   command in the PR body.
3. **Perturbation, middle tier.**
   - The reference orbit is computed in float64 numpy on the CPU and uploaded
     as a texture. Each pixel iterates δₙ₊₁ = 2·Zₙ·δₙ + δₙ² + δc in float32,
     with δ₀ = δz₀.
   - Rebase when |Zₙ + δₙ| < |δₙ|: set δ to the full z and restart the
     reference index.
   - Recompute the reference only when a term changes or the reference leaves
     the view.
   - Switch from float32 direct to perturbation automatically past about
     10⁴×.
   - For a whole-number p, expand (Z + δ)^p − Z^p with the binomial theorem.
4. **Skip the black.** Mariani–Silver on 16 × 16 tiles. A first pass computes
   tile borders; the main pass fills a tile whose whole border is in the set
   without iterating it.
   - Valid only for p a whole number with z₀ = 0, or for a pure Julia slice
     (those sets have no holes). Other slices fall back to periodicity
     checking alone.
   - Last frame's black tiles go first, as a hint only; the border test always
     runs.
5. **Stretch goals:**
   - The deep tier: an arbitrary-precision reference. `mpmath` is in `uv.lock`
     only transitively. Adding it as a direct dependency is an owner decision,
     so mark it "(rec) — pending the owner" rather than doing it.
   - Floatexp δ past 10³⁸×.
   - The endless-loop mode at a chosen Misiurewicz point, with Newton tracking
     of the point as p changes.

## Read first

- `REVIEW.md` (repo root), `hyperspace-python/docs/CHECKPOINT.md`,
  `docs/DECISIONS.md`, `docs/ARCHITECTURE.md` §3–§4 and `docs/GLOSSARY.md`
  (use its words).
- `docs/ENGINEERING.md` §15 (hot reload) and §16 (testing).
- How effects are declared: `hyperspace/fx.py` (`parse`, the `@param` and
  `@clock` syntax) and `hyperspace/shaders/fx/_lib.glsl`. The rule there: no
  shader multiplies time by a param.
- `.claude/skills/drive-the-app/SKILL.md`, for renders and videos in this
  cloud session.

## Rules

- **Goldens must not move.** A new node adds goldens; it never changes old
  ones. `tests/fixtures/` needs `git add -f`.
- **New params are a saved-format question.** Follow REVIEW.md "Files on disk
  are a format". The owner's rule: no old-schema support, both Macs update
  together, saves write the newest schema. If a schema bump is needed, say so
  in the PR; don't migrate the owner's library.
- Never run anything against `~/Hyperspace` or a Google Drive path.
- Don't modify `.github/workflows/`.
- The panel must stay legible at a distance: big targets, little text.
- Report faithfully: failures with their output, a skipped step as skipped.

## Your numbers (use only these)

- Plan doc: `docs/plans/63-mandelbrot.md`, plus a line in `docs/plans/README.md`.
- Decision register rows **872–881**: a table row plus a `### <n>.` section
  each in `docs/DECISION-REGISTER.md`.
- Hand checks **669–678**, group **DY**, in `docs/plans/11-hand-checks.md`.
  Each should be something only a person at the rig can judge: the feel of
  the sensitivity, frame times at each render size, the look of the colouring.

## Testing

- Cloud setup: `.claude/hooks/session-start.sh`; the drive-the-app skill §0
  has the manual steps if it didn't run.
- The fast tier, `uv run pytest -q` from `hyperspace-python/`, must be green.
- Unit-test the maths on the CPU against a float64 numpy oracle: escape
  counts, the perturbation recurrence, the rebasing rule, and the tile
  border-fill rule.
- Render a short demo with drive-the-app: a zoom and a term sweep at each
  render size. Commit the stills under `docs/plans/assets/63-mandelbrot/`.

## Branch and PR

- Branch `plan-63-mandelbrot` from `origin/main`.
- Open a **draft** PR to `main` with `gh pr create --draft`. Body headings:
  - **Why**
  - **What** (per stage, saying which are done)
  - **Testing** (counts verbatim)
  - **On the rig** (the bench command and what to look at)
  - **Restart or hot reload**
  - **Owner decisions pending** (each with your recommendation)

When you finish, reply with: the PR URL, the head commit, the stages done, test
counts, the rows and checks used, and the open questions.
