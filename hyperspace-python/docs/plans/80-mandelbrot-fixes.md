# Plan 80 — Mandelbrot fixes

**Built** on `plan-80-mandelbrot-fixes` (2026-11-22), in a local session on the
rig Mac (an M3 Max), so the frame times below are the rig's. Item 80 of the
post-install wave (`66-post-install.md`, first numbered 67). Register rows
1000–1007; hand checks 800–807, group FA. Builds on plan 63
([`63-mandelbrot.md`](63-mandelbrot.md)).

Making patches with plan 63's Mandelbrot on the rig turned up four problems.
They were fixed in the owner's order.

## 1. Black unless a picture is wired in (row 1000)

`graph.Effect` read nothing and painted nothing with no node on `image`. That
is right for a filter, but the Mandelbrot paints the whole frame from nothing.
Its Python half now says `GENERATOR = True`, and `Effect.generates` reads that
through `fx.HOOKS`. A generator with no input reads, paints and is made like
any effect, over a pool texture cleared to transparent black.

This needed `graph.py`, which plan 80 does not own. The change is limited to
`Effect.reads`, `paint`, `_pass` and the new `generates`. The Test card is a
generator too; making it one is row 1007, for the owner.

## 2. The coloured inside under perturbation (row 1001)

**The cause.** Rendered on the rig and in numpy at the owner's views (the
seahorse at 1e6× and 9e6×, Steps 6000), the colour rule itself was at fault,
mixed with float32 after a rebase. The inside's colour was the step at which
the periodicity check caught a point, with a tolerance of 5 % of a pixel. Deep
in, that tolerance is tiny:

- **The flat grey.** At 9e6× even the **float64 oracle** leaves 81 % of the
  inside at the cap, with eight distinct values in all.
- **The bands and discs.** What does get caught is quantised by Brent's
  doubling window (19 values at 1e6×).
- **The rectangular blocks.** In float32, after a rebase, a catch needs z to
  repeat to its last bit, so 19 % of catch steps were off the oracle.

The direct tier looked clean at shallow zooms because a float32 catch there is
an exact repeat, which is in effect a fixed tolerance of about 10⁻⁷.

**The fix.** The inside is coloured by how fast a point settles, taken from
its cycle's multiplier. Each step adds ln|f′(z)| = ln p + (p − 1) ln|z|. Where
the periodicity check finds z back near the saved z (within 10⁻³), the sum
since the save is ln|λ_L| over a lag L that is a whole number of periods.
L · ln K / ln|λ_L| is then the steps to come K times nearer the cycle. It does
not depend on which multiple of the period L is, the tolerance, the depth or
the tier. K is 5 % of a pixel at zoom 1 and 810 lines.

This is smooth: rings round every nucleus, 0 at the centre, slower toward the
edge. The float32 perturbation twin agrees with the float64 oracle on 97 % of
pixels, and the GPU with both. Whether a point is inside is decided exactly as
before. The cost is one log a step, paid only with the inside coloured.

What still reads as the cap colour is a ring slower than the cap, or an
outside point still running there. More Steps shows it.

## 3. Off-screen term sensitivity (row 1002)

How fast the picture changes with c (on a Julia slice) or z₀ (on the
Mandelbrot one) doesn't follow the zoom. Measured as the step of c that
changes the picture's brightness as much as an equal pan, it ran from 3·10⁻⁵
to 20 view heights across eight Julia views. So the drive measures it.

R = Σ|∂z/∂q|·g / Σ|∂z/∂term|·g, over a 16×9 grid of the view iterated to 192
steps, with g = 1/(|z| ln|z|) at escape. g is how a point's smooth count, and
so its brightness, answers a change of z. R predicted the measured ratio
within about ×2 at most views.

- **The rate** is view height × min(1, 0.1·R). It is measured on a drive's
  first frame and then every 0.25 s, at about 1 ms of CPU each time. A faster
  rate is eased in over 0.5 s; a slower one is taken at once.
- **At the owner's view** (Julia, zoom 1.7, c −0.8 + 0.156i), a second at full
  throw moves c by 0.067, where plan 63 moved it 1.765.
- **Unchanged:** Pan and Dive. A term the picture does not use (c at Slice 0)
  keeps plan 63's rate.
- **TERM_RATE (0.1)** is a first value for the rig (check 802).

## 4. Perturbation cost (rows 1003–1006)

Median GPU ms on this M3 Max, 1080p output, Size 810, Steps 2000 (the
coloured lines at Steps 6000), from `tools/mandel_bench.py --owner`:

| Case | Plan 63 (owner's rig numbers) | Before, measured here | After |
|---|---|---|---|
| direct 1.5e4 | 4 | 3.93 | 3.11 |
| perturbation 1.5e4 | 19 | 19.71 | 5.14 |
| perturbation 4e5 | 38 | 36.93 | 9.30 |
| perturbation 1e7 | 80 | 81.11 | 14.87 |
| skip on, 3e6 | 72 | 75.81 | 12.79 |
| skip off, 3e6 | 59 | 60.68 | 27.38 |
| coloured 1e6 | — | 114.79 | 46.95 |
| coloured 9e6 | — | 183.71 | 89.63 |

**Why it was slow, and what changed:**

- **Two reference fetches a step.** Zₘ is now carried from the step before.
- **Z's powers in a dynamically indexed array** in `binomial_delta`. p = 2 now
  takes its closed form (2Z + δ)·δ, and other powers walk Z's powers up as the
  binomial coefficients walk down.
- **Integer division and modulo** for the texel. They are now `& 1023` and
  `>> 10`.
- **The skip's border pass ran at full size**, returning off the border.
  Every 8×4 SIMD group of a 16×16 tile meets its first or last column, so the
  pass cost almost a whole picture, which is why the skip made perturbation
  slower. It is now packed, 64 slots a tile along x, so every pixel of it
  iterates a border pixel.
- **The skip turns itself off** (row 1004) where it costs more. Forced on
  against off, it paid only above about 30 % of tiles flagged. A samples query
  on the tiles pass counts them, read three passes late. Under 30 % the skip
  rests, probing every 30 passes, or at once when the zoom has moved a
  doubling.

Series approximation, the stretch, is **not built** (row 1005).

## On the rig

```bash
uv run python tools/mandel_bench.py --owner
uv run python tools/mandel_bench.py            # plan 63's full table
```

Hand checks 800–807 are the owner's.

## Goldens

No golden frame draws the Mandelbrot: plan 63 recorded none, and
`tests/test_golden_frames.py` names no `mandel` scene. `graph.py`'s change
runs only for an effect that says `GENERATOR` with no input wired, which no
golden has. So no golden can move.
