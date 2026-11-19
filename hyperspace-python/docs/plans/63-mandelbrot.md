# Plan 63 — a live Mandelbrot node

**Built** on `plan-63-mandelbrot` (2026-11-19), from the owner's decisions of
2026-11-18. Register rows 872–881; hand checks 669–678, group DY. A first
version to be tuned on the rig, not a finished one: frame times here are
Mesa's software rasteriser and say nothing; `tools/mandel_bench.py` on the
M3 Max is the measure.

## The owner's decisions (2026-11-18)

1. **Every term is a control**, as in 2swap's "Mandelbrot's Evil Twin": z → z^p + c
   with the start z₀, the constant c and the exponent p exposed. z₀ = 0 with c across
   the screen is the Mandelbrot set; c fixed with z₀ across it is a Julia set; a blend
   tilts between them. A whole-number p (2–8) is required; a fractional p is a stretch.
2. **A selectable render target: 540, 810 and 1080 lines**, rendered there and upscaled
   to the output, switchable live.
3. **Perturbation first**, an endless loop at a Misiurewicz point as the fallback, no
   double-float.
4. **Control sensitivity scales with the zoom**: a hand moves the picture about the
   same amount on screen at any depth.
5. **Colour by steps**: the smooth escape count for Palette's gradient; inside, the
   periodicity check's convergence time as a separate choice; inside black (fast) or
   coloured (full cost).

## What was built

| Stage | State | Where |
|---|---|---|
| 1. Float32 direct, every term a param, cardioid and bulb, periodicity, zoom-scaled drives | **done** | `shaders/fx/mandel.glsl`, `mandel.py` (`escape_counts`, `in_cardioid`, `advance`) |
| 2. The rig bench | **done** | `tools/mandel_bench.py` |
| 3. Perturbation, middle tier | **done** | `mandel.reference_orbit`, `binomial_delta`, `rebase`, `Reference`, the shader's `u_perturb` path |
| 4. Skip the black (Mariani–Silver) | **done**, but for last frame's hint (row 878) | `mandel.tile_flags`, `run`'s two pre-passes, `TILES_FS` |
| 5. Deep tier (arbitrary precision), floatexp δ, the Misiurewicz loop | **not built** (row 881) | — |

Stages 1, 3 and 4 landed in one commit: the Python half was written once, and
splitting it by stage would have made history for its own sake.

### The node is an effect file with a Python half (row 872)

`docs/ARCHITECTURE.md` gives two shapes for something that makes a picture: an
effect file (one GLSL pass, its params declared by its `@param` lines, a graph
`Effect` node wherever a wire puts it) or a picture node in `graph.py` (a node
kind, its own wire grammar, entries, migration and GRAPH drawing). The
Mandelbrot is an **effect file**, `mandel.glsl`, so its params, its strip on
the panel, routes, MIDI learn, saving in a loadable patch, the GRAPH picker and
hot reload are an effect's, with no schema move ("a new effect file bumps no
schema", DECISIONS). What a fragment shader alone cannot hold — a float64
reference orbit, a render target of its own size, the tile pre-passes, the
drives — is its Python half, `hyperspace/mandel.py`, named by one new header
line, `// @hook mandel`: `FxChain.run_one` hands it the pass once every uniform
is set, and `FxState.advance` hands it the effect's values while it draws.

Like any effect it takes a picture in. It paints the whole frame, so at mix 1
(its default) the picture it is wired after is not seen: wire it after any
node (the scene, a channel), or under another effect's `aux`.

### The terms

| Param | Range | What |
|---|---|---|
| Centre x / y | −2.5 … 2.5 | where the view looks, in the plane |
| Zoom | 0.5 … 10¹³, log | 1 shows 3 units top to bottom; reads "4.2e+07×" |
| z₀ x / y, c x / y | −2 … 2 | the start and the Julia constant |
| Slice | 0 … 1 | pixel point q laid in as c = mix(q, c, s), z₀ = mix(z₀, q, s) |
| Power | 2 … 8, whole | p |
| Steps | 16 … 16384, log | the iteration cap (a float knob, rounded) |
| Size | 540 · 810 · 1080 | lines rendered, then upscaled |
| Inside | black · coloured | |
| Output | steps · ramp | the count as grey, or a built-in colour ramp |
| Cycle | 4 … 4096, log | steps per rise of the brightness |
| Tier | auto · direct · perturb | auto switches past 10⁴× |
| Skip black | on · off | the tiles |
| Pan x / y, Dive, c drive x / y, z₀ drive x / y | −1 … 1 | the drives (below) |

### Sensitivity that scales with the zoom (row 874)

The scaling lives **in the node**, not in a route modifier. A modifier puts out
a lane in 0–1 and cannot read the view; a route's `scale` names a param, and
the view's width is not one; and an absolute knob cannot be scaled at all
without becoming relative. So each term the performer steers has a **drive**,
a rate in view heights a second (`mandel.advance`, Dive in doublings a
second, four at full throw), integrated in float64 into the term every frame
the effect draws. A knob, a hand push, an LFO: any source on a drive moves the
picture by the same amount on screen at 1× and at 10⁹×, nothing jumps when the
zoom moves, and the term stays an absolute, saved value. A route straight on a
term still works, at its unscaled range. This is velocity, not displacement:
a hand held off its rest keeps the picture moving. A displacement design
(the hand's change since last frame × the view) jumps back when a clutch lets
go, since the route's base returns; the owner judges the feel (check 669).

### The tiers (row 876)

Float32 direct up to 10⁴×. Past it, perturbation: the reference orbit Z₀ … Z_N
in float64 on the CPU at the view's centre (`reference_orbit`, a Python loop,
ending at the step past the bail-out), uploaded RG32F 1024 wide; each pixel
iterates δₙ₊₁ = (Zₙ + δₙ)^p − Zₙ^p + δc in float32, the difference by the
binomial theorem in Horner form (no large terms cancel), δ₀ = δz₀, with δc =
(1 − s)·Δq and δz₀ = s·Δq for the pixel's offset Δq from the reference point.
The rebase: when the full z is nearer the orbit's start than δ is to the
reference — |z − Z₀| < |δ|, which is |Z + δ| < |δ| when Z₀ = 0 — or the
reference runs out, δ = z − Z₀ and the index restarts. The reference is
recomputed only when a term changes (p, Steps, Slice, c, z₀) or its point
leaves the view; a pan inside the view moves only a float64 shift sent as
float32.

Deep in, the full z = Zₙ + δₙ in float32 has lost δ's digits, so no two full
z's are ever subtracted: the rebase's z − Z₀ is (Zₘ − Z₀) + δ, and the
periodicity check compares (Zₘ − Z_saved) + (δ − δ_saved). The first build
subtracted full z's and painted escaping pixels black at 10¹² (a false cycle)
and on a Julia slice off zero (a rebase to δ = 0); Devin's review of PR #462
found both, and `tests/test_mandel.py` holds the fix.

Measured (`tests/test_mandel.py`): float64 perturbation is the oracle within
2% of pixels a step apart at 10⁵–10⁹×; float32 direct is 34% off at 10⁵×,
float32 perturbation 6%, which is float32's own: the GPU agrees with numpy's
float32 twin to 3%.

### Skip the black (rows 877, 878)

Three passes at the render size when valid (`skip_valid`: on, the inside
black, and p whole with z₀ = 0 on the Mandelbrot slice or a pure Julia slice,
whose sets have no holes): the effect again with `u_pass` 1, where only tile
border pixels iterate and write 1 if inside; a 16×-smaller pass reading each
tile's border (`TILES_FS`); the picture pass, which fills a flagged tile black
without iterating. Anywhere else the periodicity check alone stops the inside
early. **Last frame's black tiles as a hint is not built**: on a GPU every tile
runs at once, so there is no "first", and since the border test always runs a
hint can skip nothing; the owner dropped it (2026-11-19, row 878).

### Colour (row 879)

The smooth count n + 1 − log_p log|z| (the owner's n + 1 − log₂ log|z| at p = 2),
bail-out |z|² > 10⁴ so z⁸ stays in float32. Output steps puts out grey that
rises over Cycle steps and falls over the next, so Palette's gradient wraps
with no seam. Inside coloured takes the step at which the periodicity check
caught the point (the cap where none did), through the same rise; it turns the
cardioid test and the skip off.

## The owner's answers (2026-11-19)

Every recommendation taken: an effect may have a Python half (row 872); the
drives are velocity, not displacement (row 874); Size stays 810 by default
until the bench and check 674 say otherwise (row 875); the skip's last-frame
hint is dropped (row 878); `mpmath` becomes a direct dependency when the deep
tier is built (row 881); and no schema bump, as for every new effect file.

## On the rig

```bash
uv run python tools/mandel_bench.py
uv run python tools/mandel_bench.py --out 3840x2160 --caps 256,1024,4096,16384
```

One line per view, Size and Steps cap, each the pass's median GPU ms by the
renderer's `PassTimer`; `ref ms` is the reference orbit's CPU cost, paid on a
frame a term changes. Hand checks 669–678 are what the owner judges.

## What is open

- **The deep tier** past ~10¹³×: an arbitrary-precision reference needs
  `mpmath` as a direct dependency (it is in `uv.lock` only transitively).
  The owner agreed (2026-11-19, row 881): it becomes a direct dependency when
  the deep tier is built. Zoom stops at 10¹³ until then.
- **Floatexp δ** past 10³⁸×: only after the deep tier.
- **The endless loop at a Misiurewicz point**, with Newton tracking of the
  point as p changes: not built.
- **A fractional p**: not built; Power is a whole number, an int param.
- **Goldens**: the golden frames run only on the M3 Max, so none were recorded
  here; none can have moved (no existing effect's pass or default changed).
  Record mandel's on the rig.
- **The reference on a hand on c at high Steps** is a Python loop every frame
  (16384 steps ≈ 10 ms off the rig); `ref ms` in the bench says whether it
  needs numba or a worker thread.

## Assets

[`assets/63-mandelbrot/`](assets/63-mandelbrot/): `sizes.png` (each Size into
1920×1080), `zoom.png` (1× to 10⁹× across the tier switch), `terms.png` (the
term sweep), `colour.png` (steps, through Palette, the ramp, the inside
coloured). `tools/mandel_demo.py` redraws them and the video.
