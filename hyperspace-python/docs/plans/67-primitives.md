# Plan 67 — the primitives: a few kinds, one grammar

**A model, not a build** (2026-11-22). The frame plan 66 (fields) and the shader roundup
are measured against. Nothing here is built. Tags: **[V]** read in the code, **[Rec]** a
recommendation.

The owner, 2026-11-22, after plan 66's questions:

> "A lot of these questions … are indicating that a lot of our concepts and primitives
> overlap / are unaware of each other / are competing. The whole goal here is to enable us
> to hold the primitives in our head when we're jamming and be able to compose them
> together in novel ways. When primitives compete / have esoteric quirks / don't interface
> with each other, you end up with a pile of disjoint bitmaps stacked on top of each other."

And the decision that started it: **a field is its own wire** (owner, 2026-11-22; row 1085).

Two sessions answered the owner's question separately — plan 66's builder and the session
that wrote plan 66's brief — and agreed on the diagnosis. This doc merges them; where an
item came from the brief's session it says **(brief)**. Their claims were checked against
the code; corrections are marked.

## 1. The test every primitive passes

1. **It is one kind of thing, on one kind of wire.** What it takes and what it makes are
   wires of §2's kinds, and nothing else.
2. **It reads only from wires.** No knob names another node (a "which look-back" knob
   fails), and it has no private copy of another primitive (a file that measures rings
   for itself, when a measure is a primitive, fails).
3. **One vocabulary.** The same operation has the same name, the same knobs, the same
   choices in the same order and the same units in every kind it applies to: frame
   heights for distance, seconds for time, turns or radians for angle (once, everywhere),
   0 … 1 or −1 … 1 for a level.
4. **Every kind can be seen, and turned into another only on purpose.** Each kind has a
   one-way promotion to a picture, so a thumbnail and an output can always show it, and
   every other conversion is a named node.
5. **A convenience is a patch, not a fork.** "Wave" is a saved patch of primitives that
   folds to one node, not a file that re-implements them. When the patch is the fast path
   too, there is only one thing to learn.

## 2. The kinds

Four dimensions cover everything the graph carries:

| Kind | A value of … | Over | Made by (today, and to come) | Seen as |
| --- | --- | --- | --- | --- |
| **lane** | a number | time | the analyzer, LFOs, envelopes, the sequencer, controllers, modifiers | a meter (and the `value` port, §3.8) |
| **field** | a number or a pair | space | measure, point, pins, a picture's read, a region; ops (plan 66) | grey about the middle |
| **picture** | a colour | space | the scene, a channel, effects, composites, switches | itself |
| **history** | a picture | space and time | a look-back (live), a file's decoded window, a delay (one frame) | its newest frame |

Beside them stay two kinds that are not values of a dimension:

- **mask**: a pattern, a pixel passes or it does not (the owner's plan 39 words). A field
  is continuous and signed; a mask is binary. [Rec] keep it its own kind, with
  `threshold` (field → mask) and the promotion mask → field (0 / 1) as its converters.
- **geometry**: draw calls, drawn by a scene or a layer.

**History is new** [Rec, Q1]. Today the past is four unrelated things (§3.4); as a kind,
it has makers and readers like any other, and a reader takes it on a wire.

## 3. What overlaps today, and what each becomes

### 3.1 Curve shapes: one list [V]

`wave()` in `_lib.glsl`: sine, triangle, square, saw, noise (that order, stored as an
index in every distortion's `shape`). The LFOs (`lfo.SHAPES`): sine, tri, saw, square,
random. **The same five curves, two spellings and two orders.** A performer who learns
"square is 2" on Wave finds 3 on an LFO.

→ **One `shapes` list**, one spelling, one order, used by the LFOs, by `wave()` and by any
field or remap that takes a curve. The words change on the panel now (a label is not
saved); the stored indices are mapped in the format lane (both are saved indices: a
migration, a backup, an end-to-end test).

### 3.2 Operations: one vocabulary across lanes and fields [V]

The modifiers (`modifiers.KINDS`) are curve, scale, smooth, combine, threshold, delay, on
lanes. Plan 66 proposed remap, add, multiply, quantise and gradient on fields. They are the
same operations in another dimension.

| Operation | On a lane | On a field | On a picture |
| --- | --- | --- | --- |
| **remap** (curve + range) | `curve`, `scale` | remap | (grade: the roundup) |
| **combine** (add, multiply, min, max) | `combine` | add, multiply | composite |
| **threshold** | `threshold` | → a mask | `matte` |
| **quantise** (steps) | — | quantise | — |
| **smooth** | `smooth` (in time) | blur (in space) | blur |
| **delay** | `delay` (a frame) | — | a one-frame history |
| **gradient** | the rate of change | gradient (scalar → vector) | — |

→ One name per row and the same knobs in each column it fills. The field ops are written
to the modifiers' names (`remap`, `combine`, `threshold`, `smooth`), not new ones, and a
missing cell is a gap to fill in either kind (`quantise` on a lane is a stepped LFO).

### 3.3 Measures: one primitive [V]

Wave counts its wave along a line, rings or spokes; Blocks numbers cells by a rule; plan
66's Time Displace measures a line, rings and spokes for itself. Sixteen files compute a
centre-relative position or an angle of their own; the roundup says which of those are a
measure.

→ **`measure` is a field generator** (line, rings, spokes, cells by rule, noise), written
once in `_lib.glsl`; the generator node and any file that still measures inline call the
same function, so a patch and a file agree to the bit.

**The effects that hide a field (brief).** Each builds a field inside its shader and uses
it at once:

| Effect | The field it hides | Becomes |
| --- | --- | --- |
| Wave | measure × waveform | measure → waveform → Displace |
| Blocks | a cell-number field | measure (cells) → … → Displace |
| Trip warp | noise vectors | measure (noise, vector) → Displace |
| Wobble, Acid | a swirl | a swirl generator → Displace |
| Kaleidoscope | angle folding | a fold generator → Displace |
| Zoom burst, Prism, Deconverge | radial from a centre | `point` → a blur or split that follows a field |
| Shake, Double vision | one vector for the whole frame | a constant vector → Displace; **but** Shake's Smear and Split read past *phases*, so Shake is a field over time (§3.4), not one field (plan 66 §4) |

**`point` is one pin** (brief): Wave, Prism and Zoom burst each carry their own Centre X/Y
[V], and plan 66's Time Displace added a fourth. One `point` generator, wired into each.

A file kept for speed or for saved looks stays, and is proven equal to its patch (plan 66
§4: a float32 field and the same arithmetic).

### 3.4 The past: one kind, `history` [V]

| Today | What it is | How it is reached |
| --- | --- | --- |
| `delay` | last frame's picture | a wire |
| the look-back's ring | 32 frames, `gap` apart | its trail, its `echo.<k>` pins |
| `echo.<k>` | one frame of a ring | a pin of the look-back |
| `dream` | the dream buffer, fed by the look-back | a node |
| Shake's Smear and Split | the frame at past phases | inside one shader |
| Time Displace (plan 66, branch) | the ring at a field of ages | **a knob naming the look-back** |
| the look-ahead (plan 66, planned) | a file's decoded window | — |
| a channel's `pos`, `jog` | where a clip is | params |

→ **A history is a wire.** Its makers are a look-back (a picture recorded, live), a file
channel's window (past and future), and a delay (a history one frame deep). Its readers
are an **echo** (the history at one age: a constant field of time), a **trail** (a
weighted sum over ages: today's look-back picture) and **time displace** (the history at
a field of ages). The look-back stops being a node that is also its own reader: it makes a
history, and the trail is one reader among three.

**Its storage is a time volume (brief).** Today's ring is 32 slots stacked in one 2D atlas,
so the driver's largest texture caps a slot's size (`fit_atlas`). One `TimeVolume` object,
a 3D texture (or a texture array), filled by the live ring and by a file's window alike: a
3D texture blends two neighbouring moments in hardware, so a read between frames is one
fetch, and the slot is no longer capped by the stack. An echo is a read at a constant age;
the trail is a weighting over ages, which a field could then vary per pixel. Memory is the
question (plan 66 Q5, Q6): 32 × 1920 × 1080 × 4 = 265 MB.

### 3.5 Blending: one list [V]

Three lists share words and differ:

- each effect's own `blend` (`fx.BLENDS`): mix, add, screen, multiply;
- the Blend effect's Mode: over, multiply, screen, difference, luma key;
- a composite's: over, add, depth.

→ **Composite owns blending** and has the one list. An effect keeps `mix` (a fade-in from
its input: rule 1 of DISTORTION.md, "Amount 0 is the picture again") and loses its own
blend modes; Blend becomes a composite. A question for the roundup (Q3): 29 files say
`@blend`, and saved looks carry `fx.<n>.blend`.

### 3.6 The wavetable is the shapes bank; the switch gets a position [V]

Two things were both heading for the name "wavetable" in plan 66: a bank of curves, and a
node that crossfades pictures. They are one idea, "a bank and a position between its
entries", in two kinds:

- **Curves (brief).** The one `shapes` list of §3.1 *is* the wavetable: a bank of
  waveforms the LFOs read on the CPU and shaders read as a small texture. An LFO's shape
  becomes a position in it, so it morphs between shapes instead of switching. Envelopes and
  the sequencer's steps are one-dimensional over time too, and can be entries.
- **Pictures, fields, histories.** No new node [Rec, Q4]: the switch's select becomes a
  position, a whole number a cut as today, a fraction a crossfade of the two neighbours
  (still only those two built), on inputs of any one kind.

Both use the same word for the knob, **position**, and the same blend between neighbours.
"Wave Table", the effect, is renamed **Stamp Trail** (plan 66 Q7) so nothing else is called
a wavetable.

### 3.7 The second input: typed, not "aux" [V]

`aux` means a picture laid on (Blend), an offset by convention (Displace) and, on the
branch, a field of time (Time Displace). → A file says what its second input is (`// @takes
aux field`, `picture`, `mask`), the port is named for it, and the wire is checked (plan 65
already reads whether a file has one at all).

### 3.8 Lanes into the picture graph [V]

`graph.VALUE` is declared and unused. → It is a **lane** on the render graph: a knob of
any node can take one by wire, the same lane the routes carry, and a field read at a point
(`sample`) makes one, which closes the loop from what is on screen back to what moves.

### 3.9 Any knob takes a field (brief)

The largest single lever. A knob today takes lanes over time (the routes). It should take
a field over space the same way: **value + depth × field(uv)**, per pixel. Every existing
effect then consumes fields at once, without its logic rewritten: Amount by a radial
`point`, Mix by a mask promoted, Hue by a measure.

- **The control model holds.** ARCHITECTURE §3.5 allows one performer per parameter. A
  field does not perform the knob; it varies it per pixel *about* its value, the way the
  knob's base and its lanes already land in one `apply`. An LFO and a field on the same
  knob compose (the LFO moves the value, the field spreads it) instead of fighting.
- **Mechanical, but every file.** A shader reads a knob through a generated accessor
  (`P_amount(uv)` instead of `u_amount`), which `fx.py` writes from the `@param` lines: a
  bare uniform where no field is wired, so an unwired knob costs nothing and renders the
  same bytes. It touches all the effect files, which is the roundup's work anyway.
- **What cannot vary per pixel** [V]: a choice (`@param choice`), an integer that sets a loop
  count, and a `@clock`'s rate — the host integrates one phase per effect, so a rate field
  would need a phase per pixel. Those knobs refuse a field in words.

### 3.10 Generators that pretend to be effects (brief)

Fractals, Glimmer, Grain, Oil slick and Test card fade out their input with a **Ground**
knob [V: those five carry one; the brief also named Plasma and Hue cycle, which do not,
and Mandelbrot, which paints over its input at mix 1]. Each is a field and a colouring of
it. → Split each into a field generator and a **colour ramp**.

**Palette is two ideas (brief).** The HSV slice is a colour → colour transform; the
gradient map is a field → colour consumer that only takes brightness. → The gradient map
comes out as the colour ramp, taking any scalar field; the slice stays Palette. The
Mandelbrot's smooth escape count is a scalar field like any other: into a ramp, a Displace,
or a Time Displace.

### 3.11 One key: measure, then threshold (brief)

`masks.py`'s `MATTE_FS`, Blend's **luma key** mode and session 1's black key are three
copies of the same steps: measure the picture, threshold it, soften the edge. → A matte is
picture → field (brightness, coverage, distance from a hue: the `picture` generator) then
field → mask (`threshold` with Softness). The owner's rule holds: a mask stays
pass-or-fail, reached through a field. The measure and the ramp are shared helpers in
`_lib.glsl` from the start.

**For session 1, now** (the brief's note, to paste there): *Build the black key's measure
(max rgb / luma) and threshold + softness ramp as shared helpers, not inline. `masks.py`'s
`MATTE_FS` and `blend.glsl`'s luma-key mode do the same thing and will be refactored onto
them by the fields plan.*

### 3.12 Fields beyond the effects

- **The copies (brief).** Each copy of the shape (the instance layout, `field.py`) could
  sample a field at its position for its scale, alpha or offset, so the copies answer the
  same gradient as the picture. Later.
- **The face patterns** (`shaders/patterns.glsl`) make fields in each face's own
  coordinates from eight modulation inputs; let them take a field input later. Not
  redesigned now.
- **Left alone**: tapers, routing and the binding rows work on single values.

### 3.13 A field is a texture, now (brief)

A field as a **texture** can be wired to many consumers, seen and shared, at one pass and
one read each. A field as **code** inlined into its one consumer at compile time is faster
but invisible. [Rec, both sessions] textures now; later, a generator wired to a single
consumer may be inlined as an optimisation that renders the same bytes. Everything else
depends on this; it is recorded so nobody re-asks it.

### 3.14 One meaning for "field" [V]

"Field" means four things today: the instance layout (`field.py`), Wave
Table's **Field** knob (grass, noodles or curls), Grow's **Field** knob, and — added by plan
66's branch — Time Displace's **Field** knob. The glossary needs one meaning before the
wire uses the word (plan 66 Q2): rename the instance layout (**lattice**, the brief's
suggestion; its 3D layouts are lattices already) and the three knobs, or call the new kind
a **map**.

## 4. What this does to plan 66

- **Field is its own wire, stored as a texture** (decided; §3.13).
- **Time Displace as built on the branch is the pattern to avoid**: a private measure
  (line, rings, spokes), a fourth Centre X/Y, a fourth "Field" knob, and a knob naming a
  look-back. [Rec] it does not merge as it is. Rebuilt on §2 it takes a history, a field of
  ages and the picture now, with two knobs, Span and Between; its slit-scan is the saved
  patch `measure (line) → time displace`.
- **Wave and Blocks**, and the rest of §3.3's table, become patches over generators and
  Displace (rule 5); the files stay until the lane retires them (plan 66 Q3 stands).
- **The wavetable** is the shapes bank and the switch's position (§3.6).
- **The look-ahead** is a second maker of history, filling the same time volume.

## 5. Order [Rec]

| Step | What | Unblocks |
| --- | --- | --- |
| **P0** | This model agreed with the owner; the roundup puts every effect file through §1 and fills one table: kinds in and out, the field it hides, private copies (centres, measures, keys, blends), quirks, its family. Session 1's key built on shared helpers (§3.11) | everything |
| P1 | The word (§3.14); one `shapes` list and one op vocabulary, on the panel (§3.1, §3.2) | the names the rest uses |
| P2 | The field wire as a texture; `measure`, `point`, `picture` and the ops in `_lib.glsl`; Displace's field port; threshold as field → mask | §3.3's patches, §3.11 |
| P3 | Any knob takes a field (§3.9): the accessor, file by file with the roundup | every effect a consumer |
| P4 | The history wire on a time volume (§3.4): the look-back makes one; echo, trail and time displace read one; a delay is one deep | Time Displace rebuilt, the look-ahead |
| P5 | The colour ramp out of Palette; the generators split (§3.10); the shapes bank and the switch's position (§3.6); typed second inputs (§3.7); lanes into the picture graph (§3.8) | — |
| P6 | Blending owned by composite (§3.5), if the owner says so | — |

## 6. Questions for the owner

1. **Is history a kind** (a wire, on a time volume), with the look-back, a file's window and
   a delay its makers and echo, trail and time displace its readers? [Rec] yes.
2. **Mask stays its own kind** beside field, binary, reached from a field by `threshold`?
   [Rec] yes, as plan 39 meant it.
3. **Any knob takes a field**, about its value, never replacing it (§3.9)? [Rec] yes: it is
   what makes every effect composable at once.
4. **Who owns blending**: composite alone (effects keep `mix` only), or every effect keeps
   its blend modes? It reaches 29 files and every saved look.
5. **The wavetable is the shapes bank plus the switch's position**, not a new node? [Rec] yes.
6. **The word**: the instance layout renamed **lattice** (and the three "Field" knobs
   renamed), or the new kind called a **map**?
7. **Time Displace on the branch**: hold it unmerged until P2 and P4 [Rec], or merge it now
   as a stopgap and rebuild it then? Merged, its knobs land in saved looks and become one
   more thing to migrate.

## 7. The owner's second round (2026-11-22)

Overrules §2–§6 where they differ.

1. **History is a temporal vector of a generic type T, T matrix-like** (the owner: "history
   (vector of bitmaps) is a narrow primitive"). Taken one step further, **a stack of T**: an
   ordered vector of one kind, indexed by time *or* by position, read with a blend between
   neighbours. T is a picture, a field or a mask; a number is a 1 × 1 matrix, so a lane's
   past is a stack too.
   - Makers: a look-back (T recorded over time), a file's decoded window (pictures, past and
     future), a delay (depth 1), a bank of wired inputs (the wavetable), the shapes bank
     (curves, §3.1).
   - Readers, the same for every T: **at an index** (an echo; the switch as it is today), **at
     a field of indices** (time displace; a wavetable morphing per pixel), **a weighted sum
     over indices** (the trail; a weighted sum of a mask stack is a field: how often each
     pixel passed).
   - This answers Q5: the wavetable is a stack read at a position, not a node of its own,
     and §3.6's switch position and shapes bank are two of its makers. Storage is §3.4's time
     volume, its texture format by T (RGBA8 a picture, RG32F a field, R8 a mask).
2. **A mask is a binary bitmap, a gate** (as plan 39). What cuts with one also says **what the
   pixels that do not pass become**: transparent, one colour (`#ffaa2233`), or a second
   picture wired in. The third is the composite's job, so cut and composite share one node
   rather than competing.
3. **Q3 (any knob takes a field)** asked again with its context: open.
4. **Blending stays in the effects, as shared code.** Each effect is M → M′ → f(M, M′); f is
   the same blend library a standalone Blend / Composite node runs, with one list (§3.5). The
   list grows to the standard modes not supported today: darken, lighten, colour dodge and
   burn, linear dodge and burn, overlay, soft, hard, vivid, linear and pin light,
   difference, exclusion, subtract, divide, hue, saturation, colour, luminosity, and the
   Porter–Duff operators (in, out, atop, xor). Saved `blend` indices stay readable: new
   modes are appended.
5. **Q5 (the wavetable)**: answered by 1, for the owner to confirm.
6. **Q6 (the word)** asked again with its context: open.
7. **Time Displace on this branch: hold.**

## 8. The owner's third round (2026-11-23)

1. **Any knob takes a field** (Q3): yes, as §3.9 — about its value, never replacing it;
   choices, loop counts and `@clock` rates refuse one in words.
2. **The stack is confirmed** (Q5, §7.1): history and the wavetable are one primitive, a
   stack of T read at an index, at a field of indices, or summed over them.
3. **The word is "field"** (Q6). The copy layout is renamed the **lattice** (the owner:
   "lattice or structure"; lattice taken because the 3D layouts already are lattices and
   "structure" is the structure audit's word). What it reaches [V], none of it saved:
   - `field.py` → `lattice.py` (imported by `render.py`, `ui_view.py`, `app.py`), with
     `hotreload.MODULES` and the import wall's lists;
   - the panel's labels "Field motion", "Field amp", "Field rate", "Field depth"
     (`view.inst_*` keep their ids);
   - Grow's and Wave Table's "Field" knob labels (stored as `mode`): "Growth" and "Paths"
     [rec];
   - prose: ARCHITECTURE, ENGINEERING, the glossary.
   `ui_fields.py` (the panel's form fields) is code only and no performer reads it; renamed
   with the rest if the builder of P1 wants the word clean in code too.
4. **Time Displace: hold** (unchanged).

Every question of §6 is now answered but Q4's follow-on (the blend list is §7.4). P0, the
roundup's table, can start.

**P0 started 2026-11-23:** the roundup's table is [`67-roundup.md`](67-roundup.md).

## 9. The owner's fourth round (2026-11-23): motion, blending, examples

### 9.1 Motion: a position, not a speed

The owner: the private `speed` multiplier "has become unwieldy … it's not tempo-synced and
it's not even synchronized with the other effects." Instead:

- **Each effect has a `pos`, drawn as a jog wheel**, not a `speed` fader. Nothing moves
  until something turns it, so a new effect lands still.
- **Beside the jog, an LFO picker**: a chip (or a short menu) that maps one of the LFO
  bank's onto that jog in one click, the way the faces node's input chips (`+ SUB` …,
  `ui_patterns.suggest`) put an analyzer lane on an input. One slow, tempo-synced master
  LFO (a saw) can then turn every effect's jog, so their motion is in phase.
- **The cable carries a phase offset.** [V] It does not today: a route has a depth
  (`value`), a scale, a gate, a rest and a motion, and an LFO has its own `phase` knob, but
  nothing offsets a cable. An optional `offset` key on a position route (wrapping), so two
  jogs on one LFO can sit a quarter turn apart. An optional key: no bump.

**The one decision inside it.** An effect's own rates (Wave's Drift, Shake's Rate, the
other `@clock`s) were integrated over time so that a knob step never jumps the picture
(DECISIONS, "No shader multiplies time by a param", K4). Driven by a position, there are two
ways to keep that:

| | A. Rates per turn (absolute) | B. The jog drives the clocks (relative) |
| --- | --- | --- |
| What a rate means | waves (shakes, cycles) per turn of `pos` | as today, × how far `pos` moved this frame |
| Phase alignment | **exact**: one LFO, one picture, every time; offsets hold | lost: each effect integrates from where it was, and drifts apart after a knob step |
| A rate knob step | jumps the picture by Δrate × pos, at most one turn's worth, never growing with time (K4's rule holds: the step is the same size an hour in) | never jumps |
| A seamless loop when `pos` wraps | only for a whole number of cycles per turn: rates become whole numbers (or snap to them) | always |

[Rec] **A**: it is the one that composes — the reason for the change is phase alignment, and
a tempo-synced loop wants whole cycles per bar anyway. Q8.

**Saved looks** carry `fx.<n>.speed` and move at it. [Rec] the migration gives each such
effect what it had: a route from a free-running source at that speed onto its jog (a
**free** choice in the picker, a rate of its own, off by default, so the LFO bank is not used
up by old looks). Q9.

### 9.2 Blending: what the Blend node is

[V] The Blend effect's modes (over, multiply, screen, difference, luma key) and `@blend`'s
(mix, add, screen, multiply) are **not** one list with a subset: they share two words and
differ in the rest, written twice. And they do different jobs:

- an effect's `blend` lays its own result back on its input: f(M, T(M)), one picture;
- Blend lays a **second** picture (its aux) on its input: f(M, A), two pictures.

The graph already has a node for "two pictures meet": **Composite** (`under`, `over`: over,
add, depth). So Blend is a second Composite with another list, and the luma key a copy of
the key (§3.11). [Rec] **Composite is where two pictures meet**, with the one blend library
and a mask port (§7.2, what the cut pixels become); Blend is retired into it. Every effect
keeps `mix` and `blend` for f(M, T(M)), from the same library.

**Not every effect reading an aux to blend** (the owner's other option): it would make every
effect a two-picture node that also composites, competing with Composite in every file.
An effect's second input stays typed data it *reads* (Displace's field, Time Displace's
stack; §3.7), never a second picture it lays on. One rule to hold in the head: **one picture
through an effect; two pictures meet at a composite.** Q10.

### 9.3 The examples: a deliverable of every change

Every effect that changes for fields ships a **field example**: a loadable patch and a short
Markdown beside it, saying what the effect does, how the fields in it are wired, and what to
try. Brief, to the point, easy to scan.

- **Where: `loadable/field-examples/`** in the library on the Drive — the owner, 2026-11-23:
  "loadable is the SINGLE canonical location to save patches." The session writes them
  there itself, through the Google Drive connector (`Hyperspace/loadable/field-examples/`,
  2026-11-24: the first four and the README). The repository keeps a copy only as test
  fixtures, `tests/fixtures/field-examples/`, which `tests/test_field_examples.py` opens
  through the library's own load; a change updates both.
- A change is not done until its example loads, renders the picture the Markdown describes
  (a test, as `tests/test_distort_presets.py` does for `distort/`), and its Markdown names
  only knobs and wires that exist.

### 9.4 New questions

8. **Rates per turn (A) or the jog driving the clocks (B)?** [Rec] A.
9. **Old looks' speed** becomes a free-running source on the jog? [Rec] yes.
10. **Blend retired into Composite**, Composite taking the one library and a mask? [Rec] yes.

## 10. The owner's fifth round (2026-11-23)

Decided:

- **Motion is A: rates per turn** (below, in detail, for the owner to confirm the detail).
- **Blend is retired into Composite** (§9.2): Composite takes the one blend library and a
  mask; every effect keeps `mix` and `blend` from the same library.
- **Hue cycle is retired into Palette + fields** (roundup §6), once a knob takes a field.
- **Examples go in `loadable/field-examples/`** on the Drive; `loadable/` is the single
  canonical place a patch is saved (§9.3, corrected).

### 10.1 Rates per turn, in detail

**A turn.** Each effect gets one position knob, its jog, running 0 … 1 and wrapping: one
**turn**. Something turns it — an LFO saw from the bank is the usual thing, one turn per LFO
cycle (a bar, four bars, a beat), a hand on the jog is another. Nothing turning it: the
effect is still.

**A rate becomes a count per turn.** Every knob that today says "… a second" — Wave's and
Blocks' Drift (waves passing a second), Shake's Rate (shakes a second), Trip warp's and Oil
slick's Drift, Grow's and Wave Table's Flow, Trip colour's Pulse — becomes "… a turn": a
whole number, signed (minus runs it backwards). The shader reads `count × position`.

*Example.* A master LFO, a saw, one cycle a bar at 120 bpm: a turn is 2 s. Wave with Drift
**2 a turn** moves two wavelengths a bar, one a second. Shake with Rate **24 a turn** shakes
12 times a second, on the beat grid: six shakes a beat. Blocks with Drift **1 a turn** cycles
once a bar. All three are wired to the same LFO, so at every bar line each is back at its
starting picture, and every bar looks the same as the last.

**Why whole numbers.** When the position wraps from 1 back to 0, the picture must not jump.
Every motion in these files repeats with period 1 in its count (a wave one wavelength on, a
shake one shake on, a cell number one cycle on), so `count × 1` lands where `count × 0` does
only when the count is whole. Drift 2.5 a turn would jump half a wavelength at every bar
line. So the knobs snap to whole numbers.

**How slow and how fast.** The slowest is 1 a turn; slower comes from a longer turn (an LFO
over 4 or 16 bars). The fastest is the knob's top (Shake: 1 … 128 a turn). Speed is no longer
a knob of the effect: it is how fast its turn goes, chosen once, for every effect on that LFO.

**Phase.** At position 0 every effect is at its own zero (the picture it shows unmoved). Two
effects on one LFO keep their relation for ever. A **cable offset** (§9.1) moves one by a
share of a turn: Wave a quarter turn behind Blocks, on every bar.

**A rate knob step does not jump.** Changed while the turn runs, the count would jump the
picture by `(new − old) × position` cycles. Instead the new count **lands at the next point
where the old and new pictures agree**: where `(new − old) × position` is whole. A step of 1
lands at the next wrap; a step of 4 at the next quarter turn; the knob shows the new value at
once and its ring says "waiting". Nothing ever jumps, and the effects stay in phase. (A hand
or an LFO sweeping a rate is therefore stepped: a rate is a musical choice here, not a
gesture. A gesture belongs on a knob that is not a rate — Amount, Waves, Cell.)

**Not every clock turns.** Grain's shutter (a new field of grain every frame), Glimmer's
twinkle and Trip colour's flicker are texture, not rhythm: they stay on the wall clock and
have no jog. The roundup marks each file's clocks as **turned** or **texture** [Rec].

**The files without a rate knob** (Plasma, Acid, Kaleidoscope, Wobble, Double vision,
Deconverge, Prism's tilt, Fractals, Hue cycle) move by `u_phase` times constants written in
the file — Plasma's 1.3, 0.9, 0.7 and 1.1, Acid's T / 143, T / 256 and T / 200. Those never
repeat. Each becomes whole counts per turn, chosen to keep its look (Plasma: 1, 1, 1 and 2,
say), so its motion loops on the turn. Its still pictures are the same; its motion is close,
not identical.

**The id.** The jog cannot be `fx.<n>.pos`: Wave Table already saves `fx.wavetable.pos`, its
"Position" (how far each stamp has been dragged). [Rec] the jog is **`fx.<n>.phase`**,
labelled **Position**, and Stamp Trail's knob is relabelled **Drag** (its id stays).

**Old looks.** A saved look carries `fx.<n>.speed` and rates a second. Each effect that moved
gets a **free** source on its jog (§9.1, Q9): a turn of 1 s × its old speed, and its rate as
a count of that turn — `drift × 1 s`, which is whole only by luck. [Rec] the migration rounds
it and says so in the load's note; a look whose motion must be exact keeps a free turn whose
length makes the count whole (Drift 0.5 a second → a 2 s turn, 1 a turn). Still frames are
unchanged; the golden frames, drawn at fixed times, move where a rate rounds — each is
re-recorded with the reason, as a format change asks.

### 10.2 New questions

11. **The detail above**: whole counts per turn; a rate step landing where the pictures
    agree; texture clocks left on the wall clock; the jog as `fx.<n>.phase`, "Position";
    Stamp Trail's "Position" relabelled "Drag". Confirm or change.

**P2 started 2026-11-23:** the shared field pieces are built in `_lib.glsl` and eight files
moved onto them byte for byte ([roundup §7](67-roundup.md)). Next: the field wire (a texture
pool, the grey promotion, the refusal in words), then Wave as a proven patch with its example.

**F1 built 2026-11-23: the field wire** (roundup §8): `graph.FIELD`, field makers as
`FieldEffect`, the grey promotion, the refusal naming To field, Measure and To field, Displace's
field port, three field examples in `loadable/field-examples/`. Next: Wave as a proven patch
(`measure → waveform → quantise → displace`), which needs the `waveform` op and Displace's Split.

## 12. Wave as a patch (2026-11-24)

Built: **Waveform** and **Combine** (field ops), Measure's Out **across**, Displace's **Split**,
and Wave as `measure → waveform`, `measure.2 → combine`, `combine → displace`
(`tests/wavepatch.py`), its field example `loadable/field-examples/field-wave`. Equal to
`wave.glsl` up to the compiler's rounding (row 1095): every field bit for bit; a smooth wave's
saved looks byte for byte; a hard wave's edges a pixel apart at most 1 % of the time. GLSL
lets a compiler reorder a chain of multiplies inside one program and not across two, so
"byte for byte across a program boundary" is a promise the language does not make; the
files stay for the saved looks and for speed (one pass, not five).

**The owner's questions of 2026-11-24** (row 1096): a field stays four float32 channels (33 MB at
1080p). Two would halve it and lose the scalar-or-vector flag and the spare half; half floats
would halve it too and round an offset to a quarter pixel and a large count to 1/32 of a wave.
A per-field precision choice is the later step, for smooth fields.

**Testing it locally** (the Mac): `git checkout ccr-956dc2aa-r1kaqe`, `cd hyperspace-python &&
uv sync`, `uv run pytest tests/test_field_wire.py tests/test_field_lib.py
tests/test_field_examples.py tests/test_wave_patch.py`; the examples are already
in the Drive's `loadable/field-examples/`, restart (`uv run hyperspace`), hand checks 878–883.

**The owner, 2026-11-24:** four channels at 1080p are fine for now. Fields made at 0.75k and
0.5k (810 and 540 lines) and upscaled are a follow-up session (row 1096).

## 13. Handoff (2026-11-24): where this stands, and the next session's work

*(Item 1 is built: §14.)*

**State.** Branch `ccr-956dc2aa-r1kaqe`, draft PR #488 into `main` (merged with `main` on
2026-11-24; full suite 8220 passed). Built: the shared field pieces (§11, roundup §7), the field
wire (roundup §8), Measure, To field, Waveform, Combine, Displace's field port and Split, Wave as
a patch (§12, roundup §9), four field examples. Held: Time Displace (owner: hold; rebuild it on the
field and stack wires, §4, §7.1). Decided and not built: motion as a position jog with rates per
turn (§9.1, §10.1), Blend retired into Composite and one blend library with the standard modes
(§9.2, §7.4), Hue cycle retired into Palette + fields (roundup §6), the stack of T (§7.1), the
lattice rename (§8.3), fields at 0.75k and 0.5k upscaled (a later session, row 1096).

**The next session's work — the roundup's next rows, in this order:**

1. **Blocks as a patch.** `measure (cells)` → Waveform → an *action* field → Displace. The cell
   rule is `measure_cells`; Blocks' actions (shift, zoom, stretch, turn, bulge, swap) each make an
   offset from the cell's number and the pixel's place in its cell, so the action is a field op
   that needs the cell-local position — decide whether Measure's cells output carries it (its
   spare channels, as §12 did for the direction) or the action op recomputes it. Prove it as
   `tests/test_wave_patch.py` does (`tests/wavepatch.py` is the pattern), and ship
   `field-blocks` as an example.
2. **Trip warp as a patch.** `measure (noise, vector)` × a radial weight (`point`, `combine`) →
   Displace. Its Amount is in "no unit of its own" (roundup §4): say how the patch's Amount maps.
3. **Any knob takes a field (P3, §3.9, owner: yes).** `value + depth × field(uv)` per pixel,
   through a generated accessor so an unwired knob is a bare uniform and the bytes do not move;
   choices, loop counts and `@clock` rates refuse a field in words. Then **retire Hue cycle into
   Palette + fields** (roundup §6): a migration of its six saved files in the format lane.

**How to work** (what this session learned):

- **Prove every move.** `tools/fx_sweep.py save before.npz <files>` on the old code (stash), then
  `check` on the new: every byte equal, or say exactly why not. Across two programs a GLSL
  compiler may reorder a chain of multiplies, so a patch equals its file *up to rounding*
  (§12): hold the bound in the test, and keep the file for saved looks.
- **A field example ships with every change**: a loadable patch + a short Markdown, written to the
  Drive's `Hyperspace/loadable/field-examples/` with the Google Drive connector (the folder id is
  in that folder's own listing; upload JSON and Markdown with conversion off), and the same files
  in `tests/fixtures/field-examples/`, which `tests/test_field_examples.py` opens.
- **Numbers.** Plans 66 and 67 keep theirs. Before writing a register row or a hand check,
  `git fetch origin main` and take the next free numbers there (on 2026-11-24: rows from 1097,
  hand checks from 884, groups from FL); `main` moves fast.
- **Overlaps to watch.** `main`'s plan 80 added effects built with no input (`_Build.generators`,
  `Effect.generates`); a field generator is built first, by `FieldEffect`. The two should become
  one rule. The FX page still shows Mix and Blend on a field maker (they do nothing there); a copy
  of a field maker is a picture effect's copy; a field is RGBA32F (33 MB at 1080p, owner: fine).

## 14. Blocks as a patch (2026-11-24)

Built: **Cell action** (a field op: Action, Amount, Angle), Measure's cells drawn on Blocks'
grid (**Aspect**, **Group**, **Pairs**; Scale to 512), Waveform's **Phase** (`fx.waveform.start`),
the shared `cell_of` and `cell_pair` in `_lib.glsl` (Blocks moved onto them byte for byte, 960
renders), and Blocks as `measure (cells) → waveform → cell action ← measure.2 (cells,
direction) → displace` (`tests/blockspatch.py`), its field example `field-blocks`.

**The decision §13 left open: where the cell-local position comes from.** An action needs four
things at a pixel: the cell's number through a waveform, the place in the cell, the cell's
size (shift moves whole cells, bulge's lens fills the inscribed circle) and, for swap, which
half of a pair it is. Recomputing them in the action would give it Cell, Aspect and Group knobs
of its own — a second grid to keep in step, the private copy rule 2 forbids. So they **ride on
the Measure's fields** (row 1098), as §12's direction rides with a value: Out value carries the
cell's size beside the number, Out direction *is* the place in the cell (a field worth seeing:
into Displace, every cell zooms) with the pair's side beside it, and Waveform passes on what
rides with its input. That is why two field ports (image and field) are enough for Cell action.

**Equal up to rounding, and where not** (row 1097). Blocks counts its grid in pixels (Cell) and
the Measure in frame heights (Scale = the frame's height ÷ Cell), so the patch is Blocks at the
frame height it is mapped for. Where a cell's edge falls exactly on a pixel's centre (an odd
number of pixels to a cell) the two may round that pixel into either cell; off the edges they
agree to one level — on Mesa 349 of 396 renders byte for byte, the rest one level on at most
26 pixels of 6144 — and every saved Blocks look through the renderer holds the same bound.

**Displace stays 0 … 0.5** (row 1099, for the owner). Cell action's push is in half frame
heights and the patch's Displace sits at its top Amount, 0.5: exact, since ×2 then ×½ is.
Widening Displace's Amount to 1 is cleaner, but saved route depths are measured along a knob's
taper (`params.retaper_depths`), so a wider range moves every saved route on it — a migration
in the format lane. Recommendation: leave it until a migration runs for another reason.

**Next** (§13): Trip warp as a patch, then any knob takes a field.
