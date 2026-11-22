# Plan 66 — fields: maps that say where and when each pixel reads

**Planned** 2026-11-22. **Stage 3a built** on `ccr-956dc2aa-r1kaqe`: Time Displace
over the live look-back, which stands alone (§5). Every other stage waits on the
owner's answers in §8. Register rows 902–910 (902–905 built, 906–910 open); hand
checks 699–703, group EB. Read at `main` b08a256. Tags: **[V]** read or run in the
code, **[I]** inferred, **[Rec]** a recommendation.

## 1. Why

Shake, Wave and Blocks (`docs/DISTORTION.md`) are each one file that answers three
questions in one pass: what is measured across the frame, which waveform is laid over
it, which way the result pushes. Displace answers only the last one, from a picture
wired into its `aux`, by a convention: mid-grey moves nothing. The ask is to take the
first two answers out as parts you can wire — **fields**, a value (or a pair) at every
pixel — so one field can drive more than one thing, fields can be combined, and the same
field can say *when* a pixel reads as well as *where*: Time Displace, the slit-scan.

A field is never seen; it is what something else reads. That is why its wire is the
first question (§8, Q1).

## 2. What is there today [V]

- **Displace** (`shaders/fx/displace.glsl`, plan 32 R, row 332) reads its `aux`:
  `(luma − ½·alpha) · 2` along an angle, or `(rg − ½·alpha) · 2` as x and y, in frame
  heights × Amount. Premultiplied, so a see-through pixel and an unwired aux are no
  slope. No corpus file uses it.
- **The distortion helpers** (`shaders/fx/_lib.glsl`): `wave(shape, x)` (sine, triangle,
  square, saw, noise; period 1, −1 … 1), `noise1`, `perlin`, `pushed(uv, d, split)`.
  Wave counts its measure along a line, rings or spokes; Blocks hands each cell a number
  by a rule (rows, columns, diagonal, rings, random). The measures are inline in each file.
- **Ports are typed** `image`, `mask`, `geometry` and `value` (`graph.PORT_TYPES`);
  `value` is declared and unused (plan 30 D2). Plan 39 made `mask` its own wire, one
  channel at its maker's size, with a one-way promotion into picture ports
  (`graph.MaskPicture`) and an explicit converter the other way (`matte`). That is the
  precedent for §3.
- **An effect's ports come from its file** since plan 65: the `aux` port is drawn only
  where the code calls `aux(` (`fx.reads_aux`, `EffectSpec.aux`).
- **The effects' pool is half-float RGBA** (`FxChain.pool`, `dtype="f2"`). Media, the
  look-back ring and the echoes are 8-bit.
- **The look-back ring** (`lookback.Lookback`): one atlas, `MAX_ECHOES` = 32 slots
  stacked in v, each at `dream.res` (128–384 px on the short side), one capture every
  `dream.gap` seconds (0 … 0.25), so the ring holds at most 32 × gap: **1.07 s at the
  default gap of 1/30 s, 8 s at the most**. A slot is 8-bit premultiplied. The atlas is
  shrunk to fit the driver's largest texture (`fit_atlas`). `echo.<k>` (`graph.EchoNode`)
  reads one slot, before this frame's capture.
- **A hooked effect** (plan 63, `// @hook mandel`): an effect file whose Python half runs
  its pass. No schema move: "a new effect file bumps no schema".
- **"Field" is taken.** `field.py` is the instance field (where each copy of the shape
  sits), and `ui_fields.py` its panel. See Q2.
- **The "Wave Table" effect** (`wavetable.glsl`) stamps the picture along paths; it is not
  a wavetable. Its ids are `fx.wavetable.*`. No corpus file uses it.

## 3. Fields (stage 1)

**[Rec] A field is its own wire** (Q1), the way a mask is:

- **What it holds.** Two float32 channels, signed, unbounded, not premultiplied, no alpha,
  at the frame's size: a *scalar* field uses x, a *vector* field x and y. Units are the
  reader's: frame heights for an offset (as `pushed` reads them), spans for a time.
- **Its storage.** A pool of its own, RG32F (`FxChain.field_pool`): 16.6 MB a texture at
  1920 × 1080, one held per field a frame keeps alive at once. Float32 because stage 2's
  identity needs it (§4); half-float would round an offset of 0.3 to 1/4096 of itself.
- **Into a picture port it reads as grey**, one way, as a mask does: a scalar as
  `0.5 + 0.5·v` in r, g and b, a vector as `0.5 + 0.5·x`, `0.5 + 0.5·y`, 0.5 — which is
  Displace's own convention, so a field wired into an old aux, an output or a thumbnail
  shows, and moves Displace the way it always read. A picture into a field port is
  refused in words that name the converter, the **picture** generator below.
- **How field nodes are made.** As effect files, with hot reload, their params
  `fx.<file>.*`, family `field` in the picker. A file says what its ports carry: `// @makes
  field` and `// @takes image field`, `// @takes aux field`, parsed into `EffectSpec` the
  way `aux` is. `graph.Effect` reads its ports' types from its spec and takes the field
  pool for a field maker. One node class, no node kind per generator: DECISIONS' "nodes
  are a curated set of built-ins; shaders stay files" holds.
- **The schema.** A field maker is an effect file (no new key); a wire into a field port
  is a wire. An older build reading a file with one sees an effect it does not know (a
  note, the node dropped) and a wire it refuses. Rows 347 and 371's rule, "both Macs on
  this build before saving one", covers it; no bump [Rec].

**Generators** (each a file; from DISTORTION.md's steps 1 and 2):

| File | Makes | What |
| --- | --- | --- |
| `measure` | scalar | line (distance along Angle), rings (from a centre), spokes (angle round it), blocks (a cell's number by Blocks' rule), noise (perlin) — in waves, with Scale, Angle, Centre |
| `waveform` | scalar | `wave(shape, x − drift)` over a scalar field in, with Steps: the step-2 half |
| `point` | scalar or vector | a falloff about a point (Radius, Softness, Curve); vector: toward or away from it |
| `region` | scalar | a mask in (promoted) → 1 inside, 0 outside, Feather in px (a blur first; a distance transform if the blur reads soft) |
| `pins` | scalar | 2 to 4 pins, each a place and a value, interpolated (two: linear along their line; more: inverse distance) |
| `picture` | scalar or vector | the converter: a picture's luma, or its red and green, about mid-grey — Displace's read, as a field |
| `wavefield`, `blockfield` | vector | Wave's and Blocks' offsets exactly, for stage 2 (§4) |

**Operations** (a field on `image`, a second on `aux`): `add` (a + k·b), `multiply`,
`remap` (in lo … hi → out lo … hi, through a curve, clamped or not), `quantise` (Steps,
as Wave's), `gradient` (scalar → vector, central differences in frame heights, a Scale).
Each is a few lines of GLSL. A vector `length` and `angle` are cheap later additions.

**A field is never live on its own.** A field node no consumer reaches is unreached, faint
and never built (row 349), like any node; its thumbnail is the grey promotion.

## 4. Consumers (stage 2)

- **Displace takes a `field` port** beside `aux` (Q1): a vector field is the offset; a
  scalar one pushes along Angle. Amount scales it; a new **Split** param (default 0) is
  `pushed`'s colour split. Its `aux` path is unchanged byte for byte.
- **Wave and Blocks as patches.** `wavefield → displace` and `blockfield → displace`,
  saved under `patches/distort/`, with the same knobs as the files. Every knob but Split
  and Amount lives on the field; Amount and Split on Displace. The offset is computed in
  float32 in the generator exactly as the file computes `d` before `pushed`, written to
  RG32F, read at the texel centre by Displace (`texelFetch`), and passed to the same
  `pushed`: the same float operations in the same order, so the same sample positions
  and the same bytes. Proven by `tests/test_field_identity.py`: every Wave and Blocks
  patch in `presets/distort/` (18 name one or both), file and patch side by side, byte for byte,
  on Mesa. A GPU whose compiler fuses differently between two programs could differ by a
  level; that is the Mac's hand check, not a test here.
- **Shake is not one field** [V]: Smear averages eight reads at eight phases, Split reads
  three phases. Only buzz, orbit, punch and jolt at Smear 0 and Split 0 are a field.
  [Rec] Shake stays its file; its motion can be a generator for new patches.
- **Saved looks** (Q3). [Rec] The Wave and Blocks files **stay**; the patches sit beside
  them, proven identical. No saved file changes and nothing migrates. Retiring the files
  later is a format-lane move (a migration from each `wave` node to the two nodes, `fx.wave.*`
  ids remapped in routes, macros, node mode and groups, a backup, an end-to-end test), with
  the identity already proven.

## 5. Time Displace (stage 3)

Each pixel reads the past: at `now − field × Span`. The echo node is the constant field.

### 3a. The live look-back — **built** (rows 902–905)

It stands alone: it needs no field wire, because until stage 1 it carries its own field
and reads a picture as one by convention. An effect file with a Python half
(`shaders/fx/timedisplace.glsl`, `// @hook timedisplace`, `hyperspace/timedisplace.py`),
so no node kind and no schema move (row 902).

- **Where the past comes from.** A look-back's ring, named by the **Look-back** knob (1 is
  `lookback`, 2 `lookback.2` …). The renderer hands its chain its rings
  (`FxChain.rings`); the hook binds that ring's atlas and, newest first, every commit it
  holds — its slot and its age in seconds on the ring's own clock (`Lookback.frames`) —
  not only the `echoes` the trail composites. The pass runs before this frame's capture
  (every effect does: the capture runs after every `Shown`), so it reads what an echo node
  reads.
- **The field.** **Field**: `line` (a ramp across the frame along Angle: the classic
  slit-scan, one edge now and the other Span ago), `rings` (from the centre out), `spokes`
  (round it), `flat` (every pixel Span ago: an echo), `aux` (the brightness of a picture
  wired into the aux: black is now, white Span ago — row 903). **Repeat** lays the ramp
  that many times across; **Drift** sweeps it (a `@clock`, repeats a second); **Steps**
  flattens it into bands; **Flip** turns it end for end. The field is 0 … 1.
- **Between frames** (row 904). A pixel whose time falls between two commits blends them
  by time (**Between** blend), or takes the nearer (nearest: hard bands, the scan's
  stripes). Between now and the newest commit it blends its own input with that commit:
  at 0 it *is* its input, so **Span 0 is the picture again**, and Span is an amount
  (zero-safe log taper, 0 … 8 s).
- **Past the ring** (row 905): a time older than the oldest commit reads the oldest. The
  ring holds 32 × `dream.gap`; to reach further back, raise the gap (coarser steps). The
  tip says so.
- **Nothing to read** — no look-back of that number in the graph, no capture wired, the
  ring being remade for a `dream.res` change — reads its input through.
- **What it costs.** One pass; per pixel one read of its input and up to two of the atlas,
  and a walk over at most 32 ages. The atlas is the ring's own: no memory of its own.
- **What it looks like.** The past is at `dream.res`: 256 lines by default, 384 at most,
  so the field's older parts are soft beside the sharp now. Q5 asks for a full-size ring.

### 3b. A field port — after stage 1

Time Displace takes a `field` port (a scalar, in spans; negative is the future, clamped to
now on the live ring) beside its own Field choice, which stays for a field-less patch.

### 3c. The look-ahead, for files — planned (Q6)

A media channel playing a file can read ahead as well as back: a **decoded window** of
frames around the playhead, `[t − back, t + ahead]`, in clip seconds, so each pixel reads
the clip at `playhead − field × Span` and a negative field is the future.

- **Where.** A second decoder beside `media/video.py`'s `VideoSource` (which follows one
  `want(t)`): a window filler that decodes outward from the playhead into a texture array
  (one layer a frame, `moderngl` `texture_array`, no atlas: the 16384 px limit that
  shrinks the look-back's atlas does not bind). `media/transport.py` drives it: playing,
  the window slides and decodes only its new edge; a `pos` move (the scrub latch) or a jog
  past the window empties it and it refills from the new playhead outward, the near frames
  first, so the field's now is right at once and its far ends fill in. Paused, the window
  holds still and the slit-scan over a frozen clip still moves with its field.
- **Live sources cannot look ahead** (a camera, NDI, Syphon): the window is a file's only.
- **Memory** (RGBA8, frames at the channel's decode size, `CAP_FILE` 1920 × 1080 at most):

  | Window | 1920 × 1080 | 960 × 540 | 480 × 270 |
  | --- | --- | --- | --- |
  | 1 s at 30 fps (30 frames) | 249 MB | 62 MB | 16 MB |
  | 2 s at 30 fps | 498 MB | 124 MB | 31 MB |
  | 4 s at 60 fps (240 frames) | 1.99 GB | 498 MB | 124 MB |

  [Rec] a window size in frames and a decode size of its own (half the channel's by
  default), a budget per channel of 128 MB, and the SYSTEM page's line saying what is held.
  The look-back's ring for comparison: 12.5 MiB at 400 × 256 × 32.
- **Decode speed** is the risk: a refill after a scrub decodes the window's worth of frames.
  To be measured on the Mac (VideoToolbox through PyAV) before it is built.

## 6. The wavetable (stage 4)

A **wavetable** is a bank of entries and a **Position** that blends between them: 0 the
first, 1 the last, a fraction the two neighbours crossfaded. Entries are all of one kind.

- **Pictures and fields: a render node**, a switch that crossfades (`graph.SwitchNode`
  has eight picture inputs and a cut). `wavetable` takes `in1` … `in8` of one type (the
  first wire decides) and Position (modulatable, 0 … 1); only the two neighbours are built
  (`Graph.pulled`), so a bank of eight costs two. A new node kind with entries and words,
  so it is a format move: the next lane's [Rec].
- **Curves: a modifier**, in the modulation graph (`modifiers.py`): a bank of curves read
  at an input lane, crossfaded by Position, out as a lane. The render node and the modifier
  share the word and the blend.
- **The existing "Wave Table" is renamed** (Q7). [Rec] its label to **Stamp Trail** now (a
  label is not saved; the picker finds by label and tip), and its file and ids
  (`wavetable.glsl`, `fx.wavetable.*` → `stamptrail.glsl`, `fx.stamptrail.*`) in the next
  format-lane migration, with a backup and an end-to-end test (REVIEW, "files on disk are
  a format"). The word **wavetable** is free for this stage only after that.

## 7. Work packages

| WP | What | Needs | State |
| --- | --- | --- | --- |
| **T1** | Time Displace over the live look-back: the file, its hook, `Lookback.frames`, `FxChain.rings`, tests | nothing | **built** |
| F1 | The field wire: `graph.FIELD`, its pool, the grey promotion, the refusal's words, GRAPH's colour; `@makes` / `@takes` | Q1, Q2 | — |
| F2 | Generators: `measure`, `waveform`, `point`, `region`, `pins`, `picture` | F1 | — |
| F3 | Operations: `add`, `multiply`, `remap`, `quantise`, `gradient` | F1 | — |
| D1 | Displace's field port and Split | F1 | — |
| D2 | `wavefield`, `blockfield`, the 16 patches, the identity test | F2, D1, Q3 | — |
| T2 | Time Displace's field port | F1 | — |
| T3 | The look-ahead window for files | Q6; a decode measure on the Mac | — |
| T4 | A full-size look-back ring (a texture array) | Q5 | — |
| W1 | The wavetable render node | F1, the lane | — |
| W2 | The wavetable modifier | nothing but the word | — |
| W3 | Stamp Trail: the label now, the ids in the lane | Q7 | — |

Order [Rec]: T1 (done); then F1 once Q1–Q2 are answered; F2, F3, D1 together; D2; T2.
T3 and T4 are measured before they are built. W2 can go any time; W1 rides the lane.

## 8. Questions for the owner

1. **Is a field its own wire** (`field`, RG32F, signed, a one-way grey promotion into
   picture ports, a `picture` converter the other way — §3), **or a picture read by
   convention**, as Displace's aux is today (no graph change; fields ride the half-float
   pool about mid-grey)? [Rec] its own wire: values are signed and unbounded, the 8-bit
   crossings clamp them, half-float rounds an offset, and stage 2's byte-for-byte identity
   needs float32. The convention is cheaper, and stage 2 would then be "within a level",
   not identical. (Row 906.)
2. **The word.** "Field" is the instance field today (`field.py`, `ui_fields.py`, "the
   field" in prose for the copies' layout). The glossary is signed and renames ride SEM.
   [Rec] **field** for the new wire, and the instance field becomes **the copies' layout**
   in prose, its modules renamed when SEM next runs; or call the new thing a **map**
   ("offset map", "time map") and leave the old word alone. (Row 907.)
3. **Stage 2's reach.** Keep `wave.glsl` and `blocks.glsl` and add patches proven
   identical (no migration), or retire the files with a migration in the next lane?
   [Rec] keep them now; Shake stays its file either way (it is not one field). (Row 908.)
4. **Time Displace's aux reading.** Built: brightness, black now, white Span ago (one-sided:
   the live ring has no future). Displace reads mid-grey as zero. [Rec] keep brightness for
   a *picture*; a *field* (stage 3b) carries signed time. (Row 903, built as recommended.)
5. **The past at full size.** The ring is 128–384 lines. A full-size ring needs a texture
   array: 32 × 1920 × 1080 × 4 = 265 MB, 64 frames 530 MB. Worth it for the slit-scan,
   as a `dream.res` choice "full"? [Rec] yes, measured first (T4). (Row 909.)
6. **The look-ahead's budget.** A window per playing file channel, at half the channel's
   size, 128 MB each by default (§5 3c's table)? (Row 909.)
7. **The wavetable.** A render node for pictures and fields and a modifier for curves,
   sharing the word; the old effect's label "Stamp Trail" now and its ids in the lane?
   Or another name? (Row 910.)
8. **Time Displace as a hooked effect** (built, row 902) rather than a graph node kind
   like the echo: no schema move, and its look-back is a knob, not a wire. Keep, or make it
   a node whose look-back is wired? [Rec] keep.

## 9. Not checked

Written in a cloud session on Mesa's software rasteriser. Time Displace's frame time on the
Mac, how the slit-scan reads on stage, a real look-back at 120 Hz, and the card on its
thumbnail (the card through it shows the card where the field is 0 and that look-back's
frames elsewhere: the past is not the card's) were not checked there: hand checks 699–703.
