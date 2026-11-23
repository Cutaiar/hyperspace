# Plan 67, P0 — the shader roundup's table

**Started** 2026-11-23 on `ccr-956dc2aa-r1kaqe`. Every effect file in
`hyperspace/shaders/fx/` (29, Time Displace included) put through
[plan 67](67-primitives.md)'s rules: what kinds it takes and makes, the field it hides,
the private copies of a primitive it carries, its quirks, and what it becomes. Read from
the code at `main` b08a256 plus this branch; every row is **[V]** unless it says **[Rec]**.

Kinds (plan 67 §2, §7): **picture**, **field** (scalar or vector), **mask**, **lane**,
**stack** of any of them. "Becomes" is written in the kit of §3 below, as a patch
`a → b → c`; a file kept for speed or for saved looks is proven equal to its patch.

## 1. The table

Takes / makes: **P** picture, **F** field, **L** lane (a clock counts: every file has
`speed`, so every file takes time). Blend is the file's own `@blend`.

| File | Takes → makes | The field it hides | Private copies | Quirks | Becomes [Rec] |
| --- | --- | --- | --- | --- | --- |
| **Test card** | — → P | a grid, a cross, a circle (measures) | a background level ("Ground") | ignores its input | stays a picture generator: the card |
| **Plasma** | — → P | three summed sines folded by themselves (scalar) | a cosine colour ramp (`pal`); rings from a fixed centre | ignores its input entirely; blend screen; `u_phase` × constants | `plasma field → colour ramp`, laid by composite (screen) |
| **Acid** | P → P | a swirl and a bend about the centre (a coordinate map) | the centre; its own clock ("20 ticks a second") | none worse | `swirl field → displace` |
| **Kaleidoscope** | P → P | an angle fold about the centre (a coordinate map) | the centre; spokes (`atan`) | the map is absolute, not an offset | `fold field → displace` (the offset is map − here) |
| **Zoom burst** | P → P | radial vector toward a centre | **Centre X/Y**; a glow (light spread into darker pixels) | Amount is a fraction of the distance | `point → blur along` (+ the glow as a composite) |
| **Trip warp** | P → P | noise vectors (two octaves) × a radial weight from the centre | noise; a radial weight; a zoom | Amount in "Noita units" | `measure (noise, vector) × point → displace` |
| **Time Displace** | P (+ P aux) → P | line, rings, spokes, flat, or the aux's luma — a field of ages | **Centre X/Y**; a measure (line, rings, spokes); a "Field" knob; a knob naming a look-back; Steps | **held** (plan 67 §4) | `measure → time displace ← stack` |
| **Displace** | P + P aux → P | the aux read as an offset (luma along an angle, or red/green) | a picture → field read | the aux convention (mid-grey is zero) | the consumer: `field → displace`; its aux read becomes the `picture` generator |
| **Grow** | P → P | seven growth patterns (scalar) → a soft slice → its slope | noise; a soft threshold (the knee); a **gradient** (forward differences); a relief light; a "Field" knob | two pushes in one: bulge (the slope) and lift (the height along an angle) | `growth field → remap → gradient → displace`, and `→ shade` |
| **Wave Table** | P → P | stamps dragged along paths: an offset field (root − paste) | scattered cells (roots with jitter); a relief profile; a "Field" knob | the name (it is no wavetable: **Stamp Trail**, plan 66 Q7) | `paths field → displace`, `→ shade` |
| **Wobble** | P → P | two crossed sines (vector) | its own sines (not `wave()`) | Amount in uv, not frame heights; ignores aspect in its offset | `measure (line ×2) → waveform → displace` |
| **Shake** | P → P | one vector for the whole frame, over time | a split (in time); a smear (8 taps in time) | Smear and Split read past *phases*: a stack over time, not one field | `motion lane → constant field → displace`; Smear and Split as a stack read (plan 67 §7.1) |
| **Wave** | P → P | measure × waveform → a slide or a squeeze | **Centre X/Y**; a measure (line, rings, spokes); Steps; a colour split (`pushed`) | — (the model file) | `measure → waveform → quantise → displace` |
| **Blocks** | P → P | a cell number by rule → an action | cells by rule; a colour split (`pushed`) | six actions, each its own offset | `measure (cells) → waveform → action field → displace` |
| **Double vision** | P → P | a ring of constant offsets turning in time | taps (copies) | Amount in half-percents of the frame | `constant field → displace (taps)` |
| **Deconverge** | P → P | one offset per colour channel + a radial scale | a colour split (per channel) | Amount in px | `point → displace (split)` |
| **Prism** | P → P | radial from a centre, to a power (Rim), + a turning tilt | **Centre X/Y**; a spectral colour split (taps); fringe | — | `point → remap → blur along (spectral)` |
| **Bloom** | P → P | the picture's brightness, keyed | a **key** (threshold + knee on peak); a disc blur | blend add: its own composite | `picture (peak) → threshold → blur`, laid by composite (add) |
| **Fractals** | P → P | a fractal pattern (scalar) gated by the picture's dilated brightness | noise; a colour ramp; `reach` (picture → field); "Ground" | blend screen; the pattern ignores the picture, only the gate reads it | `fractal field → colour ramp`, × `picture (reach)` |
| **Mandelbrot** | — → P | the smooth escape count (scalar) | a colour ramp (its Output ramp); its own render size | ignores its input; a Python half | a field maker (`mandel → field`) `→ colour ramp` |
| **Glimmer** | P → P | scattered sparkles (scalar) gated by the picture | scattered cells; `reach`; an HSV colouring; "Ground" | blend add; colour by wall clock | `scatter field → colour ramp`, × `picture (reach)` |
| **Oil slick** | P → P | noise bands + rings (scalar) → thin-film colour | noise; rings from a fixed centre; a colour ramp (`film`); **`haze`, a second copy of `reach`**; "Ground" | multiplies the picture by the ramp | `measure (noise + rings) → colour ramp`, combined (multiply) with the picture |
| **Edges** | P → P | the picture's luma → its **gradient** (Sobel) → length → threshold | a picture → field read; a gradient; a **threshold**; colour by direction (HSV) | — | `picture (luma) → gradient → length → threshold → colour ramp` |
| **Trip colour** | P → P | the picture's peak, pulsed (scalar), on green only | a picture read; grain (`u_time`) | one channel only | `picture (peak) → remap` on a channel knob (§3.9) |
| **Hue cycle** | P → P | a diagonal or rings from a fixed centre (scalar) | a measure (line, rings); an HSV colouring | hue in **turns** (Palette's in degrees) | **Hue rotate with a field on its hue knob** (§3.9) — the clearest case |
| **Blend** | P + P aux → P | the aux's luma, keyed (luma key mode) | **the blend library** (5 modes); a **key** (luma key) | its modes are not `@blend`'s | the composite (§3.5, §7.4); the key → `picture → threshold → mask` |
| **Grain** | P → P | cell noise per frame (scalar), toned by luma | noise cells; a tone curve; **quantise** with Bayer dither; "Ground" (a different meaning) | — | `measure (cells, per frame) → remap → combine (add)`; `quantise` as its own op |
| **Fade** | P → P | — | — | a level: `combine (multiply)` by a constant | stays, or becomes `combine` with a lane |
| **Palette** | P → P | gradient mode: the picture's luma | a colour ramp (gradient mode); a picture read | two ideas in one file (plan 67 §3.10) | compress stays Palette; gradient → `picture (luma) → colour ramp` |

## 2. The private copies, counted

The rows above, gathered by what is copied. A count over 1 is a primitive to write once.

| Copy | Where | Count | The one primitive |
| --- | --- | --- | --- |
| A centre (Centre X/Y knobs) | Wave, Prism, Zoom burst, Time Displace | 4 | `point` |
| A fixed centre (no knob) | Acid, Kaleidoscope, Trip warp, Deconverge, Hue cycle, Oil slick, Plasma, Grow | 8 | `point` (wired, or the frame's centre by default) |
| A measure: line, rings, spokes | Wave, Time Displace, Hue cycle (line, rings), Oil slick (rings), Plasma (rings), Kaleidoscope (spokes) | 6 | `measure` |
| Cells: by rule, scattered, per frame | Blocks, Glimmer, Wave Table, Grain, Fractals | 5 | `measure (cells)`, `scatter` |
| Noise | Trip warp, Grow, Oil slick, Fractals; Wave and Blocks' noise shape | 6 | `measure (noise)`; one `shapes` list |
| A picture read as a value (luma, peak, red/green, dilated) | Displace, Time Displace, Blend, Bloom, Trip colour, Grain, Edges, Fractals and Glimmer (`reach`), Oil slick (`haze`), Palette, Hue cycle (paint); `masks.MATTE_FS` | 13 | `picture` (luma, peak, rg, reach) |
| A key: threshold + softness | Blend (luma key), Bloom (threshold + knee), Edges (threshold), Grow (the knee); `masks.MATTE_FS`; session 1's black key | 6 | `threshold` (soft) |
| A gradient | Edges (Sobel), Grow (forward differences) | 2 | `gradient` |
| A colour split | Wave, Blocks (`pushed`), Shake (in time), Deconverge (per channel), Prism (spectral) | 5 | a **split** on the consumer: `displace` and `blur along` |
| Taps along a vector (a blur) | Zoom burst, Prism, Double vision, Bloom (a disc), Shake's Smear | 5 | `blur along` |
| A colour ramp | Plasma (`pal`), Oil slick (`film`), Mandelbrot, Palette (gradient), Fractals, Glimmer, Edges and Hue cycle (HSV) | 8 | `colour ramp` |
| Relief light from a slope | Grow (shade), Wave Table (profile) | 2 | `shade` |
| Quantise | Wave (Steps), Time Displace (Steps), Grain (steps + dither) | 3 | `quantise` |
| Its own composite (`@blend` not mix) | Bloom, Glimmer (add); Plasma, Fractals (screen) | 4 | composite (§7.4: the one blend library) |
| "Ground" | Test card (a background level); Fractals, Glimmer, Oil slick (a floor under the picture's gate); Grain (a floor under alpha) | 5, two meanings | gone: a gate is a field, and its floor is `remap` |

## 3. The kit the table asks for [Rec]

Every "Becomes" above is written in these, and nothing else:

- **Field makers:** `point`; `measure` (line, rings, spokes, cells by rule, noise, scatter);
  `picture` (luma, peak, red/green, reach — the converter); the generators whose field is
  their own idea: growth (Grow), paths (Stamp Trail), fractal (Fractals), plasma, mandel.
- **Field ops** (to the modifiers' names, plan 67 §3.2): `remap` (with the one shapes list
  as its curve), `combine`, `threshold` (soft; → a mask), `quantise` (with dither),
  `gradient`, `length` and `angle`.
- **Consumers:** `displace` (an offset field; Split; Taps — Double vision's ring and
  Shake's smear read a stack), `blur along` (a vector field; Taps; spectral split),
  `colour ramp` (a scalar field → a picture), `shade` (a relief light from a slope),
  `time displace` (a stack and a field of indices), and **any knob** (§3.9).
- **Pictures:** composite (the blend library, all modes), cut (a mask, and what the cut
  pixels become, §7.2), Palette's compress, Fade (or `combine`), the test card.

That is 3 field makers plus five named generators, 7 ops, 6 consumers and 5 picture nodes,
against 29 files today. Most of the 29 survive as saved patches that fold to one node and
keep their names, so the picker still shows a Wave and a Bloom.

## 4. Quirks that are not a copy

- **"Amount" moves pixels in six units.** Frame heights (Wave, Blocks, Shake, Grow,
  Displace), uv (Wobble), "Noita units" (Trip warp), half-percents
  of the frame (Double vision), px (Deconverge), a fraction of the distance (Zoom burst).
  Plan 67 rule 3: **frame heights** for every offset. Saved values convert in the lane.
- **Hue is in degrees on Palette and the dream, in turns on Hue cycle.** One unit (the
  owner's call; degrees is what the panel already reads elsewhere).
- **Time.** Twenty files move: nine by `@clock` (the rule since 2026-11-02), the rest by
  `u_phase` × a constant (lawful: no knob scales it) or the wall clock (Glimmer, Trip
  colour's grain). Each has a private `speed`. A clock is a lane (§3.8): wireable, so two
  effects can share one tempo instead of two speed knobs agreeing by hand.
- **Generators that ignore their input** (Test card, Plasma, Mandelbrot) still take a
  picture port, and are laid on by their own `@blend`. A field maker takes no picture.
- **Every effect carries `mix` and `blend`.** `mix` stays (a fade-in from the input);
  `blend` runs the one blend library (§7.4).

## 5. What next

1. **The owner reads §1** and marks any row whose "Becomes" loses something only the
   file can do. Mandelbrot (its own render size, its drives) and Stamp Trail (its path
   solver) keep their code as generators; that is in the table.
2. **The kit's GLSL first** (plan 67 P2): `point`, `measure`, `picture`, the ops and
   `displace` in `_lib.glsl`, so the files that stay can call them and agree with their
   patches to the bit.
3. **One patch proven**: Wave as `measure → waveform → quantise → displace`, byte for byte
   against `wave.glsl` on all its saved looks — the proof that rule 5 costs nothing.
4. **Units and names** (§4, plan 67 P1) ride one format-lane move.
