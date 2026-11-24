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
| **Hue cycle** | P → P | a diagonal or rings from a fixed centre (scalar) | a measure (line, rings); an HSV colouring | hue in **turns** (Palette's in degrees) | **retired into Palette** [Rec, §6]: an LFO on Hue turn is its turning, and Spread is a field on Hue turn (§3.9) |
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

- **"Amount" moves pixels in six units.** Kept as they are for now (the owner, 2026-11-23):
  labelled per effect instead, below, and in each knob's tip on the panel (the four tips
  that did not say were rewritten; a tip is not saved). Unifying them on frame heights
  (plan 67 rule 3) is a later format-lane move.

  | Effect | Knob | Unit | What that means |
  | --- | --- | --- | --- |
  | Wave, Blocks (shift), Shake, Grow, Displace | Amount | frame heights | 0.1 moves a pixel a tenth of the frame's height, the same distance across as up |
  | Blocks (zoom, stretch, bulge, turn, swap) | Amount | doublings, quarter turns, trades | per its Action (DISTORTION.md) |
  | Acid | Bend / Twist | frame heights / radians | Twist: the roll at full swing |
  | Prism | Amount / Tilt | frame heights at the frame's edge / px | |
  | Wobble | Amount | a share of the frame | 0.01: 1% of its width across, 1% of its height up and down: on a wide frame a push across is longer than one up |
  | Double vision | Amount | half-percents of the frame | 1: 0.5% of its width across and its height up and down |
  | Trip warp | Amount | none of its own | at 1, a few percent of the frame near a corner (at most about a seventh), none at the centre; past 0.67 also a 10% zoom |
  | Deconverge | Amount / Radial | px / a share of the distance from the centre | |
  | Zoom burst | Amount | a share of the distance to the centre | 0.1: a pixel smears a tenth of the way in |
  | Time Displace | Span | seconds | |
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

## 6. Hue cycle and Palette (the owner: "if it is completely covered by one Palette and one LFO, get rid of it")

Checked against both files [V]:

| Hue cycle | Palette (Compress) |
| --- | --- |
| Its clock turns every hue (Paint 0, Spread 0) | Hue from 0, Hue to 360 (the whole wheel: the map is the identity), an LFO (saw) on **Hue turn**: the same rotation |
| Paint 1: the frame's brightness in the cycling colour, `peak × hsv(h, 0.85, 1)` | Hue from = Hue to (a slice of zero width) on the LFO, Sat from = Sat to = 0.85, Val 0 … 1: `hsv(h, 0.85, peak)`, the same pixels |
| Paint between: a mix of the two | two Palettes, or one at its Mix |
| Sat | Sat from / Sat to |
| **Spread**: the hue banded across the frame (a diagonal, or rings) | **not covered today**; covered once a knob takes a field: `measure (line or rings) → Hue turn` |

So it is covered but for Spread, and Spread is exactly plan 67 §3.9. [Rec] Retire Hue cycle
when §3.9 lands; its field example (`loadable/field-examples/hue-cycle`) is that Palette patch. Six
saved files use it (`presets/kinetic/kinetic-comet`, `kinetic-tunnel`; the corpus's `dial`,
`hands-pinch`, `party-acid`, `party-trip`), so the retirement is a migration in the lane:
each `huecycle` node rewritten as the Palette patch, its look proven by the golden frames.

## 7. Built: the shared field pieces (P2's first step, 2026-11-23)

`shaders/fx/_lib.glsl`, a new section "fields: the shared pieces", every effect's program:

| Piece | What | Replaces |
| --- | --- | --- |
| `point_at(cx, cy)`, `from_point(uv, cx, cy)` | a Centre X / Y pair as a place in frame heights; this pixel seen from it | the centre spelled out in Wave, Prism, Zoom burst, Time Displace |
| `Measure` (`x`, `g`) | a measure and the unit direction it grows in | — |
| `measure_line(p, angle)` | distance along an angle, frame heights | Wave's and Time Displace's lines |
| `measure_rings(p)` | distance from the point, frame heights; outward | Wave, Prism, Time Displace, Oil slick |
| `measure_spokes(p)` | the angle round the point, turns (−½ … ½); anticlockwise | Wave, Time Displace |
| `measure_cells(id, rule, spread)` | a cell's place along a rule (rows, columns, diagonal, rings, random) | Blocks |
| `read_signed(v, alpha)` | a picture read as a signed field about mid-grey, premultiplied | Displace |
| `quantise(x, steps)` | steps each side of 0 | Wave's and Time Displace's Steps |
| `threshold_soft(x, key, soft)` | the soft key | Blend's luma key |
| `remap`, `combine` | in → out ranges; add, multiply, min, max | — (for the field nodes) |

**Moved onto them, byte for byte:** Wave, Blocks, Displace, Blend, Prism, Zoom burst, Time
Displace, Oil slick. Proof: 1041 renders — every choice, three values of every knob, every
pair of choices, three times, an aux picture, and for Time Displace a filled ring — before
and after, every byte equal (Mesa's llvmpipe). Hue cycle is left as it is (to be retired).
`tests/test_field_lib.py` holds each piece to a numpy oracle on the GPU, and holds that no
file spells out a centre, the soft key or the cell rule again.

**Not yet moved, and why:** Grow's and Edges' gradients differentiate a function, not a
texture (GLSL has no function values), so `gradient` arrives with the field wire, over a
texture; Bloom's knee is a smoothstep and Edges' threshold a straight ramp — different curves
from `threshold_soft`, so moving them changes their look and needs the owner's eye; the
fixed centres (Acid, Kaleidoscope …) take a point when they take a field.

No look changed, so no field example yet (plan 67 §9.3): the first comes with Wave as a patch.

## 8. Built: the field wire (F1, 2026-11-23)

- **The type.** `graph.FIELD`, green on GRAPH: float32 RGBA at the frame's size, signed, .a 0
  a scalar and 1 a vector. Files declare it: `// @makes field`, `// @takes <port> <type>`.
- **The nodes.** A field maker is a `FieldEffect`, made once a frame into a float32 target that
  every consumer reads; a picture port reads it as grey through one `FieldPicture`; Displace
  reads it on its new third port, `field`.
- **The files.** Measure (the measures and a point, value or direction), To field (a picture
  read as a field). Displace with no field is byte for byte as before (the 1041 renders).
- **The examples** (rule 9.3): `loadable/field-examples/` — rings lens, line shear, self bend.
- **Not yet:** a field on any knob (P3), a field on a copy (a copy is still a picture effect's),
  RG32F (half the memory), hiding Mix and Blend on a field maker's FX strip.

## 9. Built: Wave as a patch (2026-11-24)

The roundup's "Becomes" for Wave, `measure → waveform → quantise → displace`, as built: the
quantise is Waveform's Steps, and the push's way is a second Measure (Out direction, or across
for slide) multiplied in by Combine — five nodes. Proven equal up to rounding (plan 67 §12,
register 1095). The next rows of §1 to take apart reuse these: Blocks (`measure (cells)` →
Waveform → an action), Trip warp (`measure (noise)` → Displace), Hue cycle (a field on a knob).

## 10. Built: Blocks as a patch (2026-11-24)

The roundup's "Becomes" for Blocks, `measure (cells) → waveform → action field → displace`, as
built: the action field is **Cell action**, and the place in the cell comes from a second
Measure of cells (Out direction) — five nodes, as Wave's. The cell's geometry rides on the
Measures' fields, so Cell action has no grid knobs (plan 67 §14, row 1098). Equal to
`blocks.glsl` up to rounding at the frame height it is mapped for (row 1097); `blocks.glsl`
moved onto `_lib.glsl`'s `cell_of` and `cell_pair` byte for byte, so the grid is one piece
that Blocks and Measure share; Glimmer, Wave Table, Grain and Fractals keep their own cells for
now (§2).

## 11. Measure taken apart (2026-11-24)

The roundup's `measure (…)` is five nodes now — Line, Rings, Spokes, Cells, Noise — and `point` one
more, a field every measure reads (plan 67 §15, row 1101). Where §1 says `measure (cells)` read
Cells; `measure (noise)`, Noise; `point → …`, a Point wired into the measure's `field` port.

