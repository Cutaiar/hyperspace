# Plan 90 — the history primitive, and the dream rebuilt on public parts

**A design, not a build** (2026-11-25). Plan 67's P4 (§3.4, §7.1, §8.2) made concrete, and
the deep-dream subsystem taken apart against it. Nothing here is built. Tags: **[V]** read
in the code, **[M]** measured in this session, **[Rec]** a recommendation. The owner holds
Time Displace (#488) until this is settled.

**Revised 2026-11-26 (§7):** the owner's answer — nothing added only to serve the dream, and a
dream composes with no recipe. §7 overrules §3.3–§6 where they differ.

The owner, 2026-11-25:

> "A lot of the architecture of the dreaming subsystem is legacy … a result of old
> limitations and old ways of thinking. These new primitives call for a much more
> simplified and composable version of the dream node."
>
> "The dream node is very much an async thing. It runs at its own pace. That's absolutely
> right, but it is currently rebuilding a lot of stuff privately that has become public
> utility since the dream node's inception."
>
> "The only thing that needs to really go into the dream's torch tensor is the thing that
> the dream is being done on."
>
> "I need more information about the recursive accumulator in order to make a decision."

**The short answer.** The dream is three things wearing one name: (1) an *async gradient
pass* — the only part that needs torch; (2) a *recursive loop* around it (the running
blend `D`, the mask `M`); (3) a *look* laid on afterwards (mask, re-colour, grade, laid
over at a mix). Only (1) is the dream. (2) is a feedback loop that the public **delay**
already is, once a delay can carry a field; (3) is Fade, Hue turn / Palette, a grade and a
composite. The look-back is a **stack maker** plus a **trail reader**; an echo is a
**read at an index**; Time Displace is the same read with **a field on its index knob**
(plan 67 §18) — not a node of its own.

## 1. Inventory: what the dream and the look-back do privately [V]

`dream.py` (the worker), `lookback.py` (`Lookback`, `Dreamer`, `DreamState`), the graph's
`History`, `Capture`, `EchoNode`, `DreamNode`, and what GRAPH, the LOOKBACK page and the
migrations know of them. **Pull out**: a public primitive covers it now. **Becomes a
primitive**: worth making public (others want it). **Dream-only**: and why.

### 1.1 The worker (`dream.py`)

| What it does | Where | Public primitive now | Verdict |
| --- | --- | --- | --- |
| Gradient ascent on a net layer: roll by jitter, ∂mean(layer)/∂x, unroll, ÷ std, × mask, step, clamp 0…1 | `dream_step`, `dream_steps` | none | **dream-only** — this *is* the dream; the one thing torch is for |
| Octaves: one scale a job in rotation (÷1.5ⁿ), lost-detail reinjection | `dream_octave`, `_process` | none (a resize is not a reinjection) | **dream-only** — part of the gradient pass, costs nothing extra |
| Nets, layers, weights: VGG16 / GoogLeNet cut at a layer, read once per net, downloaded on first use | `TRUNKS`, `build_trunk`, `load_stack` | none | **dream-only** |
| Running blend `D ← D·(1−k) + frame·k` | `_process` | a delay + Fade + an add Composite already makes it for pictures (the **feedback** starter, DECISIONS row 564) | **pull out** — §3 |
| Content mask `M ← max(M·decay, clamp(4·blur₉(mean rgb)))` | `_update_mask` | To field (luma), Scale, Combine (max); a delay — but a delay carries only pictures, and no field op blurs | **pull out**, with two **becomes a primitive**: a field **Smooth** (plan 67 §3.2's empty cell) and a **delay of any kind** (plan 67 §7.1: a stack one deep) |
| Mask gates the gradient (`g·M`) | `dream_step` | none | **dream-only, as an input** — the gate changes *what the gradient does*, so it cannot be applied after. It crosses as the subject's alpha (§4.7) |
| Output premultiplied by the mask, alpha = M | `_process` | Fade with a field on Level (#497: any knob takes a field) | **pull out** |
| ImageNet normalisation, rows bottom-up, uint8 ↔ float | `normalize_in`, `_frame_tensor` | none | **dream-only** — plumbing |
| Stability guard `step ≤ 1.5·k/steps`, clamped, said | `guard_step` | none | **drop** — `k` leaves the worker, so the worker cannot see it (§2, prior 5) |
| NaN reset (non-finite `D` → the frame) | `_process` | none | **dream-only** — a worker's own safety |
| Thread, condition, latest-wins, 3 input slots, 3 output slots | `DreamWorker._run`, `submit`, `latest` | none | **dream-only** — the async-ness the owner wants kept |
| MPS host-alias copy path (private torch API) | `alias_view`, `probe_alias` | none | **dream-only** — plumbing |
| One worker lent between decks; a lend restarts the dream | `lend` (plan 44 D4) | none | **dream-only** — but simpler once `D` lives in GL (§2, prior 4) |
| Status line (ms, behind, drops, resets, clamped, loading) | `stats`, `status` | a node's `said` | **keep**, said on the node |
| `[dream] enabled` gate; torch never imported otherwise | `app._open_dream` | — | **keep** (prior 11) |

### 1.2 The dream's GL half (`lookback.Dreamer`, `DREAM_FS`, `DreamNode`)

| What it does | Public primitive now | Verdict |
| --- | --- | --- |
| Downsample its input to `dream.res` on the short side (4 choices) | **Resize** (plan 34 Z) | **pull out** — the dream runs at its input's own size; a Resize before it chooses. Resize counts its *long* side, so a short-side choice is wanted (Q11) |
| Read back every frame, hand the worker a uint8 array | — | **dream-only** (the crossing); the per-frame cadence is a prior (prior 1) |
| Pull the newest result into a texture `D` | — | **dream-only** — the node's held output |
| Re-colour: hue rotate, saturation about grey | **Hue turn** (#509), Palette | **pull out** — Hue turn's turn and saturation; prove `hue_rotate` (`_common.glsl`) equals Hue turn's YIQ turn, else a row says how close |
| Tint: `mix(own, luma × colour, tint)` | Palette's gradient map (black → the tint colour) at its mix | **pull out**, proven or bounded |
| Tint from the input's mean colour (host mean, every 4th pixel) | none (plan 67 §3.8's `sample` makes a lane; not built) | **becomes a primitive**: *Mean colour*, picture → lane (Q6) |
| Grade: `pow(c, contrast)·(1 − darken)` | none: no public picture curve (plan 67 §3.2's "(grade: the roundup)") | **becomes a primitive**: *Grade*, a picture op (the trail uses it too) (Q5) |
| Lay over its input at `mix`, coverage = the layer's own peak brightness | **Black is clear** (plan 87, peak measure, level 0, soft 1, keep colour) → Fade (mix) → Composite over | **pull out** — the trail's layering is the same rule (§1.3) |
| `dream.on` off passes through and idles the worker | an effect's `on` | **keep** as the node's on |
| One live dream (D2): a wire on a second refused | — | prior 4 (Q7) |

### 1.3 The look-back (`Lookback`, `History`, `Capture`, `POST_FS`)

| What it does | Public primitive now | Verdict |
| --- | --- | --- |
| Records its input every `gap` seconds into 32 slots | — | **becomes a primitive**: the **stack maker** (§4.2) |
| Slots in one 2D atlas (32 stacked), capped by `GL_MAX_TEXTURE_SIZE` (`fit_atlas`) | — | **replaced** by a texture array (§4.3). The atlas existed because moderngl cannot attach an array layer; [M] PyOpenGL (already a dependency) can: `glFramebufferTextureLayer` on a moderngl framebuffer's `glo` renders into layer 5 and only layer 5, here on Mesa (GL 3.2 core: the Mac's 4.1 has it; to check there) |
| `res` (4 choices, short side) | **Resize** | **pull out**, as the dream's |
| Its own clock, seconds; a frame whose clock did not move counts as 60 Hz | — | **becomes the maker's** clock (§4.4) |
| Capture after every reader of the trail (`Capture.after`) | the delay's write runs last too | **becomes a primitive invariant**: a stack's write runs after every read of it this frame, so a reader never sees this frame, and a loop through any stack is legal (as a delay's is) |
| Trail: weight `echo_mix·½^(age/fade)`, oldest → newest, premultiplied over, coverage = the graded layer's peak | none as one pass | **becomes a primitive**: the **trail reader** (§4.5). Its "over by peak" is Black is clear + over, written once in `_lib.glsl` |
| Grade each layer (darken, contrast) | none | → *Grade* (above), placed before the maker (§4.6) |
| Occlude: `wake × (1 − occlude·max(min(4·peak(occluder), 1), cover))` | Black is clear / Matte (brightness) → **Cut** (amount = occlude), the cover a mask wire | **pull out** |
| The `cover` input (the faces' coverage mask) | a mask wire into Cut | **pull out** |
| `_trail_of` / `lay_onto`: an "add" composite of a look-back draws in one pass, byte for byte the old one-shader look-back | Composite add | **drop** after migration — a byte-exactness hack for `/7`'s split; the new trail is proven against the old one instead (§5) |
| `idle`: not in the graph, forget the history | — | **keep** on the maker |
| Shares `DreamState` with the dream (`Renderer.dreamer` made on `lookback.state`): `res`, `darken`, `contrast` read by both | — | **drop** — the coupling (prior 9) |
| Its knobs are `dream.*` (`LOOKBACK_KEYS` splits one prefix between two nodes; `dream.<n>.*` for `lookback.<n>`) | — | **drop** — ids by owner (§4.9) |
| Thumbnails of the echoes on the LOOKBACK page | a node's thumbnail | **keep**, as the stack's picture: its newest entry (plan 67 §2: "seen as its newest frame"), the page's strip of entries a reader's view |

### 1.4 Echoes, Time Displace, and the rest of the house

| Thing | Today | Verdict |
| --- | --- | --- |
| `lookback.echo.<k>` pins (`EchoNode`): the k-th newest commit, cropped from the atlas, refitted by cover | — | **pull out** into the **Read** reader at a constant index (§4.6) |
| Time Displace (#488): a private measure (line, rings, spokes), Centre X/Y, a "Field" knob, a "Look-back" knob naming a ring, Repeat, Drift, Steps, Flip, Between | Point, Line, Rings, Spokes, Waveform, Scale, Combine; any knob takes a field | **pull out** entirely: Read with a field on its index knob (§4.8) |
| Delay (`Delay` / `DelayWrite`, half-float pair, own size, z⁻¹) | public | **becomes the stack maker of depth 1**, of any kind (§3, §4.2) |
| Feedback starter (delay → Fade 0.75 → composite) | public | the trail's other mechanism; stays, and is how the dream's loop is drawn (§3) |
| Generators, slots (plan 89) | public | nothing private here: the dream draws on one picture |
| Composites, the one blend list | public (`graph.BLENDS`: over, add, depth, screen; plan 67 §7.4 adds the standard modes) | the trail's fold names its blend from that list (§4.5); the dream's lay is a Composite over |
| Fields into knobs | public (#497) | the trail's fade, the loop's `k`, the Read's index all take fields: per-pixel decay and Time Displace for free |

## 2. The owner's priors

Every assumption the current design bakes in; what it costs; what dropping it means.

| # | Prior | Where | Cost | Drop or simplify |
| --- | --- | --- | --- | --- |
| 1 | **Cadence: a readback every render frame**, latest wins in the worker | `Dreamer.submit`, `DreamWorker.submit` | a GL sync (~0.4 ms, glReadPixels) every frame, though the worker (19–30 ms a job) uses one in two to four | **Submit only when the worker is idle** (a ready flag): one readback per job. Same picture, fewer stalls (Q8) |
| 2 | **Resolution is the look-back's `dream.res`**, four short sides (128 … 384) | `RES`, `Dreamer._ensure`, `echo_size` | the dream cannot run at a size the look-back does not; changing one changes the other | the dream runs at its **input's own size**; a Resize before it chooses. Costlier sizes are the performer's to pick, said in ms |
| 3 | **Readback is uint8, and `D` lives in the worker** | `Slot`, `_process` | fine while `D` never leaves torch. Once the blend is outside (§3), 8 bits stall it: at k 0.05 a pixel stops moving 10 levels short of the frame (½ / (255·k)) | the crossing is **RGBA16F** both ways: 0.84 MB each way at 408 × 256. Half floats stall at 1¼ levels, unseen |
| 4 | **One live dream, one worker** (D2), lent between decks (plan 44 D4) | `ONE_DREAM`, `lend` | a second dream is refused in words; a deck change restarts `D` | keep one worker; once `D` is a GL texture per node (§3) a lend no longer throws a deck's dream away — the worker is stateless between jobs, so **two dreams can share it round-robin** at half the rate each (Q7) |
| 5 | **The stability rule** `step × steps / k ≤ 1.5`, clamped | `guard_step`, `STABLE_RATIO` | ties three knobs; the 1.5 ceiling holds only *with* the mask gating the gradient (0.5 without) | `k` is no longer the worker's. Keep the NaN reset; say the ratio in words on the dream when its loop is wired (Q9) |
| 6 | **Octaves rotate one scale per job** | `dream_octave` | none: one octave's cost | keep — it is the dream's own |
| 7 | **The mask** (`M`, decay 0.99, blur 9, gain 4) gates the gradient *and* premultiplies the output | `_update_mask` | four constants nobody can reach (blur, gain) and one knob (`mask_decay`); the mask cannot be any other shape | the gate is **an input** (whatever is wired: a key, a field, a hand), the shape public field ops; `M` as today is a saved patch (§3, §4.10) |
| 8 | **The wake is `k`** — content that moved fades at `k` | `_process` | a dream's memory and its speed are one knob; per-pixel memory impossible | `k` is a Mix's amount in the loop: a knob that takes a field (per-pixel wake) |
| 9 | **Tint and grade in the compositor**, sharing `darken` / `contrast` with the look-back | `DREAM_FS`, `DreamState` | the dream and the look-back cannot be graded apart; "Darken" moves both | Hue turn, Palette, *Grade* — each wired where wanted |
| 10 | **The look-back coupling**: one `DreamState` for both, one `dream.*` prefix split by `LOOKBACK_KEYS`, `dream.<n>.*` for other look-backs | `params.is_lookback_knob`, `patches.dream_owner`, `graphview.DREAM_SHARE` | a performer reads "params dream.*" under a node called Look-back; three helpers exist to say which node owns a knob | each node owns its ids (§4.9) |
| 11 | **The config gate** `[dream] enabled`; without it torch is never imported | `app._open_dream` | the dream is invisible until a file is edited | keep: torch is 2 GB and a 528 MB download. The node always exists; unconfigured it says how to turn it on |
| 12 | **Threading**: a thread, a condition, 3 + 3 slots, a lock-free latest | `DreamWorker` | — | keep; one change: the worker returns `D` unmasked, so it holds **no state between jobs** but the net (§3) |
| 13 | **What is saved**: every `dream.*` value, the worker's included; `dream.layer` an index into an append-only `LAYERS`; never `D` or the ring | `DreamState`, `LAYERS` | — | keep the worker's ids (`dream.layer`, `steps`, `step`, `jitter`, `octaves`, `on`) as they are; move the rest (§4.10) |
| 14 | **Premultiplied, alpha from brightness** everywhere (the overlay window) | `DREAM_FS`, `POST_FS` | — | keep: it is Black is clear, and public since plan 87 |
| 15 | **The echoes' clock in seconds, a frozen clock read as 60 Hz** | `Lookback.tick` | — | keep, on the maker (§4.4) |
| 16 | **32 echoes**, uniform arrays of 32 | `MAX_ECHOES` | the stack's depth is a constant | a texture array holds up to 2048 layers [M]; the maker's **Depth** knob (a count, refusing a field), 1 … 64 (Q4) |

## 3. The recursive accumulator, laid out for a decision

### 3.1 What `D` and `M` compute [V]

Once per **worker job** (not per render frame), with `f` the newest submitted frame:

```
D′ = D·(1 − k) + f·k                          a running blend: infinite memory
M  = max(M·mask_decay, clamp(4·blur₉(mean(f.rgb)), 0, 1))   a decaying peak-hold
D  = G(D′, M)                                 s gradient steps, each gated by M
out = (D·M, M)                                premultiplied
```

`D` is **not a function of the past frames alone**. `G` is the net's gradient pass, and it
is *inside* the recursion: a pixel that stays dreams `G(G(G(…)))` — that is what "dreams
deep" means. A stack of stored frames read as a weighted sum gives `Σ wᵢ fᵢ`: the frames,
blended. It can never give `G` applied a hundred times. So for the dream, a stored stack is
not a substitute at any depth; only a loop is.

`M` is a peak-hold, `max over i of decayⁱ · xᵢ`. A stack read with a *max* fold could
express it exactly, but at decay 0.99 it reaches 1 % after 460 jobs — 460 stored frames.
The loop holds it in one.

The trail is the other way round: 8 discrete echoes, `gap` apart, are *the look* (the tracer
copies you see); a running blend would smear them into a fog. The trail wants the stack.

### 3.2 The options

| | A. A running-blend node ("feedback" kind) | B. A stack with an exponential read | C. A delay of any kind + ordinary ops, in a loop [Rec] |
| --- | --- | --- | --- |
| What it is | a node holding its own previous output: `out = mix(prev, in, k)` (or `max(prev·d, in)`) | the stack maker (§4.2) + the trail reader weighting `½^(age/half-life)` | `in → Mix(k) ← delay(out)`; the dream's own output, a frame or more late, breaks the loop the way a delay does |
| Memory (1080p) | one f16 pair: 33 MB | N frames: 32 × RGBA8 = 265 MB | one f16 pair per delay: 33 MB (at the dream's 408 × 256: 1.7 MB) |
| Cost a frame | one pass | N fetches a pixel (32) | one pass per op (2–3 small ones) |
| Memory length | infinite | N × gap (32 × 1/30 s ≈ 1 s; a 10 s fade is cut to its first second) | infinite |
| Can hold the dream (`G` inside) | **no** — unless its "previous" becomes a port, which is C | **no** (§3.1) | **yes**: the dream sits in the loop |
| Expresses | blend, peak-hold | any weighting, any fold, read at an age, reverse | any recurrence: blend, peak-hold, decay, gated feedback, the dream |
| Per-pixel decay | its `k` takes a field | its half-life takes a field | the Mix's amount takes a field (#497, today) |
| Fits plan 67 §1 | rule 2 fails softly: a delay in disguise, private state | yes (a reader) | yes: a delay is the stack of depth 1 (§7.1); nothing new |
| On GRAPH | one node | two nodes | three to five nodes — folded as a saved patch (rule 5) |
| The dream | — | — | `Mix(k)`, delay-free, around the dream; `M` a field loop through a field delay |
| The trail | a fog, not echoes | **yes** (today's look) | the feedback starter (exists) |

### 3.3 Recommendation: C, and B for the trail

**The running blend is a loop, not a kind.** `D` and `M` are recurrences, and the public
way to write a recurrence is a delay in a loop. History stays what plan 67 §7.1 says: a
stack of stored T. Two things make C whole:

1. **The delay carries any kind** — a picture, a field, a mask — as the stack maker of
   depth 1 (§4.2). `M`'s loop needs a field delay.
2. **An async node breaks a loop.** The dream's output this frame always answers an
   earlier submit, so the graph treats it like a delay's (`wire_loops`): `frame → Mix ←
   dream; Mix → dream` is legal with no delay in it. The blend then happens once per
   *job*, as today: each job dreams `mix(the last result, the frame now, k)`. A delay in
   the loop would blend once per *render frame* instead, and change the look with the
   worker's speed.

The dream's whole recurrence, in public parts:

```
picture ─► Resize (short side 256) ─┬────────────► Mix (k) ─► dream ─┬─► … the look (§4.10)
                                    │                  ▲             │
                                    │                  └─────────────┘   (no delay: async)
                                    └─► To field (luma) ─► Smooth (9 px) ─► Scale ×4, clamp
                                              ─► Combine (max) ◄─ Scale ×0.99 ◄─ delay (field)
                                                     │
                                                     └─► dream.gate   and   Fade.level (the lay)
```

What it costs: a Smooth field op and a clamp on Scale (both small, both wanted elsewhere),
a field delay, a **Mix** — `mix(a, b, amount)` — as a Combine mode and a Composite level,
and the loop rule for an async node.

## 4. The spec

### 4.1 The wire type

**`stack`** — one wire type, one colour on GRAPH, carrying a stack of one kind T. The wire
knows its T (picture, field, mask; a lane later), so a reader's output is a wire of T and a
mismatch is refused in words, as a picture into a field port is today. A stack is **seen as
its newest entry** (plan 67 §1 rule 4), through T's own promotion (a field's grey).

### 4.2 Makers

| Maker | Takes | Makes | Knobs |
| --- | --- | --- | --- |
| **Record** (the look-back's maker; keeps the id `lookback`, Q12) | one wire of T | a stack of T | **Depth** (1 … 64, a count), **Gap** (seconds, 0 = every frame), **On** |
| **Delay** (as today, generalised) | one wire of T | T, last frame's — a Record of depth 1 read at 0, written short | none |
| **Bank** (later: the wavetable, plan 67 §3.6) | up to 8 wires of T | a stack of T, indexed by position | — |
| **File window** (later: the look-ahead, plan 66 Q6) | a channel | a stack of pictures, past and future | — |

A maker **writes after every reader of it this frame** (today's `Capture.after`, made the
rule), so every read is of the frames before this one and any loop through a stack is legal.
Its size is its input's own (a Resize before it chooses: `dream.res` gone); a size change
makes it again, clean, and its readers say so for a frame (`remaking`, kept).

### 4.3 Storage

**A 2D texture array**, one layer an entry, written by binding one layer as the framebuffer's
colour attachment (`glFramebufferTextureLayer`, PyOpenGL, on the moderngl framebuffer's `glo`
[M]). Not a 3D texture: `GL_MAX_3D_TEXTURE_SIZE` is 2048 here [M] (Apple's GL to confirm on the Mac), so a 4K
frame does not fit, and hardware blending in z would blend across the ring's seam (newest
beside oldest); a read between two entries is two fetches and a `mix`, which it must be anyway
when entries are not evenly spaced in time.

Format by T, and what 32 entries cost at 1920 × 1080:

| T | Format | One entry | 32 entries | At the look-back's default (408 × 256) |
| --- | --- | --- | --- | --- |
| picture | RGBA8 (as the echoes today) | 8.3 MB | 265 MB | 13 MB |
| picture, 16-bit (the delay today) | RGBA16F | 16.6 MB | 531 MB | 27 MB |
| field | RGBA16F [Rec] (the field wire is RGBA32F: 1.06 GB at 32) | 16.6 MB | 531 MB | 27 MB |
| mask | R8 | 2.1 MB | 66 MB | 3 MB |
| lane | R32F, 1 × 1 (a CPU ring) | 4 B | — | — |

[Rec] a **budget for all stacks together, 512 MB by default** (`[render] stack_budget`): a
maker that would pass it is refused in words naming its size and depth, and the SYSTEM page
says what is held. A delay is RGBA16F as today; a Record of pictures RGBA8 unless its **Bits**
choice says 16 (Q4).

### 4.4 The time base

[Rec] **A stack is indexed in steps: 0 the newest entry, 1 the one before**, fractional
between two. A step is the stack's own unit — a capture for a Record, an entry for a Bank —
so one reader reads every maker. For a Record, seconds are `steps × Gap`; a reader's index
knob says its unit in its label ("steps back, Gap apart"). The alternatives:

- **seconds**: rule 3's unit for time, but a Bank has no time; and with a Gap that is not a
  whole number of frames the stored ages are uneven, so a read in seconds walks timestamps
  (as #488 does) — exact, and a loop over 32 ages a pixel.
- **turns** (plan 67 §10.1): the maker captures on a lane's turn (N entries a turn), so a
  stack and every jog on one LFO agree. Worth adding as a **Clock** input on Record later — a
  lane wire — rather than a unit.

The maker's own clock stays seconds, a frame whose clock did not move counting as 60 Hz (prior
15), so a 120 Hz screen keeps the same trail.

### 4.5 Readers

| Reader | Takes | Makes | Knobs |
| --- | --- | --- | --- |
| **Read** | a stack of T | T | **At** (steps back, 0 … Depth − 1, takes a field), **Between** (blend, nearest) |
| **Trail** | a stack of T | T | **Count** (the newest n entries), **Level** (0 … 1, takes a field), **Fade** (half-life in seconds, takes a field), **Blend** (from the one list: **over** — each entry laid over the older by its own peak, today's — or **add**, the weighted sum; **max** for masks and fields) |

Trail's weight is `Level · ½^(age / Fade)`, age = steps × Gap: today's formula. A weighted sum
of a mask stack is a field — how often each pixel passed (plan 67 §7.1).

### 4.6 The look-back as a maker plus a trail

Today's `lookback`, exactly, becomes:

```
X ─► Grade (darken, contrast) ─► Resize (res) ─► Record (Depth 32, Gap) ═► Trail (Count = echoes,
     Level = echo_mix, Fade, over) ─► Cut ◄─ mask: max(Black is clear (peak ×4) of the occluder, cover)
                                         (amount = occlude)
```

- **Grade before Record**: the grade is per pixel and per layer, so grading what goes in equals
  grading each stored layer — exact for a look whose knobs hold still; a knob moved re-grades
  only new entries (a sweep looks different for Depth × Gap, about a second). After Trail would
  be wrong: the over-fold's coverage is the graded peak (Q5).
- **Echoes are reads**: `lookback.echo.<k>` → **Read at k − 1**, Between nearest. One node per
  echo read, as the pins were one per read.
- What leaves: `res`, the atlas, `fit_atlas`, `_trail_of` / `lay_onto`, `TRAIL_VARIANTS`,
  `HISTORY_OF`, the four look-back helpers in `params` / `patches` / `graphview`.

### 4.7 The GL ↔ torch boundary

**Only the dream's subject crosses.** At submit, one RGBA16F texture at the dream's input size:
**rgb the picture to dream, a the gate** (the `gate` field port, unwired = 1 everywhere), read
back once, when the worker is idle. Back comes **rgb, the dreamed picture**, unmasked, RGBA16F,
written into the node's output texture. Nothing else crosses: no blend state, no mask state, no
colour, no grade. The worker keeps the net and its weights and nothing between jobs, so a lend
(plan 44 D4) or a second dream (Q7) costs it nothing.

**Testable without torch.** The GL side talks to a `LookbackSource` (`submit`, `latest`); a numpy
fake (an identity, a fixed brighten) drives every GL test, every loop, every migration and every
old-against-new render. [V] `tests/test_dream.py` and `tests/test_deck_fade.py` skip without torch;
torch is not installed in the cloud environment, so the worker's own tests run on the Mac (a hand
check), and the cloud's proofs use the fake.

### 4.8 Time Displace, rebuilt

Not a node. **Read, with a field on At** (plan 67 §18: any knob takes a field):

```
Point ─► Line (angle) ─► Waveform (saw, Repeat, Phase = Drift) ─► Scale (× Span in steps) ─► Read.at
lookback ═══════════════════════════════════════════════════════════════════════════════► Read
```

#488's knobs each become a public part: Field → which measure is wired (Line, Rings, Spokes, a
constant, To field of any picture: the "aux"); Repeat and Drift → Waveform; Steps → quantise;
Flip → Scale × −1; Between → Read's own; Centre → a Point; **Look-back → the wire** (the knob
naming a ring, rule 2's failure, is gone). Its `now`-to-newest blend (a pixel younger than the
newest entry blends with the picture now) is a Read reading index 0 and below as the newest:
**[Rec] At below 0 reads the newest**, and a slit-scan that must include *now* lays the picture
over by a Combine — said in the example. Shipped as the saved patch and example `slit-scan`;
#488 is closed with a pointer here (Q13).

### 4.9 Ids, and how saved looks migrate

The model is #509's: **keyed on the retired thing, run as the ladder's last step, no schema
bump**, a backup by `tools/migrate_library.py`, an old-file end-to-end test, notes said on load.

| Saved | Becomes | Exact? |
| --- | --- | --- |
| node `lookback` / `lookback.<n>` and its wires | Grade → Resize → Record (`lookback[.n]`) → Trail (`trail[.n]`) → Cut, wired where the look-back's picture went | the trail to the GPU's rounding (§5) |
| `dream.echo_mix`, `fade`, `echoes` (and `dream.<n>.*`) | `trail[.n].level`, `.fade`, `.count` | yes |
| `dream.gap` | `lookback[.n].gap` | yes |
| `dream.darken`, `dream.contrast` | `grade[.n].darken`, `.contrast` — one Grade on the look-back, a second on the dream when the file has one (today they were shared) | yes |
| `dream.occlude` and the `occluder` / `cover` wires | a Cut's amount and its mask | to rounding |
| `dream.res` | a Resize's size (Q11) | yes with a short-side choice |
| `lookback.echo.<k>` wires | a Read at k − 1, nearest | yes |
| node `dream` with `dream.k`, `mask_decay` | §3.3's loop | not frame-exact: the worker is async and jittered. Proven with the fake worker, synchronous, byte for byte against the old path up to the f16 crossing |
| `dream.mix`, `hue`, `sat`, `tint`, `tint_from`, `tint_hue`, `tint_sat` | Key → Fade (mix) → Composite over; Hue turn; Palette (gradient) ← Mean colour | bounded per row |
| `dream.on`, `layer`, `steps`, `step`, `jitter`, `octaves` | the dream's own, **ids unchanged** | yes |
| routes, desk rows, macros on any moved id | retargeted, as `hue_turns` does; a push across a changed range redrawn and said | per row |

### 4.10 The new, smaller dream node

- **Takes:** `image` (a picture, at its own size: what it dreams on) and `gate` (a field,
  optional: where the gradient may act — prior 7).
- **Makes:** a picture — the newest result, held between results, a job or more late. Its own
  size is its input's. Before its first result, and off, it passes its input through (today's
  rule). Async, so it **breaks a loop** (§3.3).
- **Keeps:** the worker and its thread, the nets and `dream.layer`, `steps`, `step`, `jitter`,
  `octaves`, the octave rotation, the NaN reset, the status in its words, `dream.on`, device,
  precision and weights in config, the config gate, one worker shared.
- **Gives up:** `k`, the mask and `mask_decay`, `mix`, the colour (`hue` … `tint_sat`), the
  grade, `res`, the stability clamp, the shared `DreamState`, the per-frame readback.
- **Today's look** is a saved patch, **Dream look**, that folds to one group on GRAPH: Resize →
  the loop (Mix k ← dream) → Fade by the mask field → Hue turn → Palette (tint) → Grade → Key
  (peak) → Fade (mix) → Composite over the input, and the mask's field loop. The `tracers +
  dream` and `dream on a picture` starters spawn it. Every part can be pulled out, rewired or
  dropped.

## 5. Build order [Rec] — one PR each, after the owner's answers

| PR | What | Proof |
| --- | --- | --- |
| H1 | The `stack` wire; **Record**, **Read**, **Trail** on a texture array; Grade; a field **Smooth**; Scale's clamp; the **Mix** op; Delay of any kind; an async node breaks a loop | tests for each; GRAPH and the FX pane in the app; examples `stack-echo`, `stack-trail` |
| H2 | The look-back and echoes on H1; the migration `graphmigrate.lookbacks`; the old ring, atlas and `DreamState`'s look-back half deleted | `tools/fx_sweep.py`-style old-vs-new renders of every saved look-back (filled rings, fixed clocks), golden frames re-recorded on the Mac where the rounding moves them (a hand check) |
| H3 | The slim dream: the worker's `G` only, the f16 crossing, submit-when-idle, the gate; Mean colour; the Dream look patch; the dream's migration | the fake worker, synchronous, old-vs-new; the real worker on the Mac (hand check: the look by eye, ms by the status line) |
| H4 | Time Displace as Read + a field; `slit-scan`; #488 closed | against #488's own shader as a test fixture (as Hue cycle's was), to rounding |

Each ships register rows, hand checks, DECISIONS, ARCHITECTURE, GLOSSARY, a field example in the
Drive's `Hyperspace/loadable/field-examples/` and `tests/fixtures/field-examples/`.

## 6. Questions for the owner

1. **The accumulator.** The running blend and the mask become loops of public parts — a delay
   that carries any kind, a Mix, and the dream itself breaking the loop because its output is
   always a job late (C). The alternatives are a new running-blend node (A: one node, but it
   cannot hold the dream inside it) or a stored stack read with exponential weights (B: cannot
   express a dream at any depth, cuts memory at Depth × Gap, 265 MB at 1080p). [Rec] **C**, with
   today's look a folded saved patch.
2. **The gate.** Does the dream keep an optional `gate` field port — where the gradient may act,
   crossing to torch as the subject's alpha (today's mask, which also holds the stability ceiling
   at 1.5) — or does it dream everywhere and get cut afterwards (one input only, but the ground
   fills with texture and the ceiling falls to 0.5)? [Rec] **keep the gate port**.
3. **The time base.** A stack is indexed in **steps** (0 the newest entry; seconds = steps × Gap),
   one unit for every maker; or in seconds (rule 3, but a Bank has none); or in turns (a lane
   clocking the maker). [Rec] **steps**, and a Clock input on Record later for turns.
4. **Storage and memory.** A texture array (not 3D: 4K does not fit, and z-blending crosses the
   ring's seam); pictures RGBA8 unless a Bits choice says 16, fields RGBA16F, masks R8; Depth 1 …
   64; one budget for all stacks, 512 MB, refused in words past it. [Rec] **yes to all**; change
   any number.
5. **Grade.** Darken and contrast become a public **Grade** picture op. On the look-back it goes
   *before* the Record: exact for a still look, and a knob moved re-grades only new frames (about
   a second to show fully). After the Trail it would change every look with contrast ≠ 1. [Rec]
   **before**.
6. **Tint from the picture.** `tint_from = scene` takes the input's mean hue. Make **Mean colour**
   a public picture → lane node (plan 67 §3.8's `sample`), or drop the choice and migrate those
   looks to their colour at load? [Rec] **make it public**.
7. **More than one dream.** Today one live dream (one worker, one GPU job). With `D` out of the
   worker, two dreams can share it, each at half the rate. [Rec] **keep one for now**, the refusal
   unchanged; revisit when a look wants two.
8. **Cadence.** Read back only when the worker is ready for a job, instead of every frame (the
   same picture, a ~0.4 ms stall saved on most frames). [Rec] **yes**.
9. **The stability clamp.** With `k` outside the worker the clamp cannot be computed. Drop it,
   keep the NaN reset, and say `step × steps / k` in words on the dream when its loop's Mix is
   wired straight to it? [Rec] **yes**.
10. **Saved dreams.** Each opens as the **Dream look** patch, folded to one group, its parts
    pullable. [Rec] **yes**; or keep a convenience file drawing today's look in one pass.
11. **`dream.res`.** Resize counts its long side. Add a **short side** choice to Resize, so 256
    means 256 at any aspect, or migrate to a long side for 16 : 10? [Rec] **add the choice**.
12. **Names.** The maker keeps the id **`lookback`** (on GRAPH "Look-back", a stack out) and its
    readers are **`trail`** and **`read`**; every knob takes its node's prefix (`trail.fade`, not
    `dream.fade`). [Rec] **yes**; or new names (`record`, `history`).
13. **Time Displace.** Close #488; its slit-scan is the saved patch `Line → Waveform → Scale →
    read.at` and every knob a public part; At below 0 reads the newest. [Rec] **yes**.
14. **Order.** H1 → H2 → H3 → H4, one PR each. [Rec] **yes**.

## 7. The owner's answer (2026-11-26) — overrules §3.3–§6 where they differ

> "Recommendations are good here. That being said, I want it to be easier to compose dream
> stuff without needing to remember specific ways of combining the dream node and other
> nodes. The whole point is to have composable primitives. If we're introducing things here
> that are only existing in order to serve the dream, the question is why."

**The rule this sets.** Nothing is added only to serve the dream. A dream dropped on any
picture cable does its job alone, with no recipe to remember: §3.3's loop (`Mix ← dream`,
a field delay for the mask) and §4.10's folded *Dream look* were exactly such a recipe, and
go. What the dream keeps is what makes it a dream; what it gives up goes to primitives that
other things already use.

### 7.1 Every addition of §3–§6, asked "who else needs it?"

| Added in §3–§6 | Who else needs it | Verdict |
| --- | --- | --- |
| The `stack` wire; Record, Read, Trail | echoes, the trail, Time Displace, the look-ahead, the wavetable (plan 67 §7.1) | **keep** — this is history, not the dream |
| An async node breaks a loop | only the dream's loop | **drop** |
| A **Mix** op (Combine mix, Composite level) | only the dream's loop | **drop** |
| The dream's `gate` field port | only the dream | **drop** — the dream reads its input's **alpha** (§7.2) |
| A delay of any kind; a field Smooth; Scale's clamp | fields in general (plan 67 §3.2, §7.1) — but nothing in *this* plan any more | **out of this plan**: plan 67's backlog, built when a field patch wants them |
| The 16-bit crossing | only because `D` left the worker | **drop** — `D` stays in the worker (§7.2) |
| Submit when the worker is idle | nothing public: inside the node | **keep**, internal |
| *Grade* (darken, contrast) | darken is **Fade** exactly; contrast has no other user | darken → Fade; contrast → Q15 |
| *Mean colour* (picture → lane) | only `tint_from = scene` | **drop**; Q16 |
| Resize's short-side choice | only the migration of `dream.res` | **drop**; Q18 |
| *Dream look*, a folded patch | it is the recipe the owner does not want | **drop** — the bare dream is the look (§7.2) |

What is left new is the history primitive alone: one wire, one maker, two readers.

### 7.2 The dream node, revised

It follows the two rules every picture node follows, and nothing of its own:

1. **Alpha is coverage.** It dreams where its input is: the gradient is gated by the input's
   alpha. Brightness becomes alpha by **Black is clear** (plan 87), which any node already
   offers — so the scene keyed dreams as today, and a cut-out, a segment's foreground or a
   channel with alpha dreams only its subject, with nothing wired to say so. The private
   "brightness is coverage" rule (`DREAM_FS`, `POST_FS`, the mask `M`) retires house-wide;
   the trail lays by alpha too (§7.3).
2. **One picture through; its result laid back on its input by `mix` and `blend`**, from the
   one blend library, as every effect does (plan 67 §7.4, §9.2: M → M′ → f(M, M′)). No
   composite to remember.

| | |
| --- | --- |
| **Takes** | `image`, at its own size (the dream runs at whatever size arrives; a Resize before it is the performer's choice, as before any node) |
| **Makes** | a picture: its input with the dreamed picture laid back at `mix` / `blend`, alpha the held coverage |
| **Knobs** | `on`, `layer`, `steps`, `step`, `jitter`, `octaves` (ids unchanged); **Hold** (`dream.k`, id unchanged: how long the dream keeps what it dreamed, the one temporal knob); `mix` (id unchanged), `blend` (new, the library's list) |
| **Inside, with no public surface** | `D`, float, in the worker — the thing the dream is done on, so the only thing in the tensor. Each job: `D′ = mix(D, input, k)` on rgba; the gradient gated by `D′.a`; out rgba. The octave rotation, the NaN reset, the thread, latest-wins, submit-when-idle, the stability guard (it can see `k` again; it reads its gate's coverage for the ceiling, 1.5 gated, 0.5 where the gate is everywhere) |
| **Gone** | `res`, `mask_decay`, the mask's blur and gain, `hue`, `sat`, `tint`, `tint_from`, `tint_hue`, `tint_sat`, `darken`, `contrast`, the shared `DreamState` |

**Why the hold is the dream's own, not a loop.** The gradient pass runs *inside* the
recursion (§3.1): "dreaming deep" is the same pixel dreamed again job after job. That is
what a temporal dream *is*, so it is the node's own behaviour, the way a delay's memory is
the delay's. It costs no public part and no recipe. A performer who wants another recursion
sets Hold to 1 (the dream follows its input each job, holding nothing) and draws a loop with
the delay and composite that exist today.

**Colour and grade are after it, if wanted**: Hue turn (hue, saturation), Palette (a tint),
Fade (darker). None is needed for the dream to look like a dream.

**What a look gives up, said on load.** The mask's linger merges into Hold: at the defaults
the dreamed region faded over ≈ 69 jobs after its content left (`mask_decay` 0.99) and the
picture over ≈ 13.5 (`k` 0.05); now both fade together, at Hold (Q17). The mask's 9 px blur
and ×4 gain are Black is clear's soft and feather on the input.

### 7.3 The look-back, revised

```
X ─► Key (black is clear: peak, level, soft, keep colour) ─► Fade (1 − darken) ─► Record
     (Depth, Gap) ═► Trail (Count, Level, Fade, blend over) ─► Cut (amount = occlude)
                                                                ▲ mask: Matte of the occluder, cover
```

The trail lays each entry over the older ones **by its alpha**, from the one blend list, like
any composite; the key before the Record makes that alpha from brightness, which is what the
old shader did privately. Every part is one a performer already uses elsewhere.

### 7.4 What the build is now

| PR | What |
| --- | --- |
| H1 | the `stack` wire; Record, Read, Trail on a texture array (§4.2–§4.5) |
| H2 | the look-back and echoes on H1, migrated (§7.3, §4.9's rows) |
| H3 | the dream, slimmed (§7.2), migrated: hue / sat → Hue turn, tint → Palette, darken → Fade, each only where a file's value is off its default; `dream.res` → a Resize only where a file set one (Q18) |
| H4 | Time Displace as Read + a field on At (§4.8); #488 closed |

Proofs, migrations and docs as §5. Q2, Q6, Q10 and Q11 are void; Q1's answer is C for
recursions a performer draws, and the dream's own hold for the dream.

### 7.5 New questions

15. **Contrast.** A power curve on the look-back's and the dream's layers. Nothing else has one.
    Drop it (a look with contrast ≠ 1 opens without it, said on load), or build a picture
    **Remap** — plan 67 §3.2's "(grade)" cell, the lane's `curve` in the picture kind — which
    would be general, not the dream's? [Rec] **Remap**, in H1, as §3.2's row: it is a gap in
    the operation table, and the migration is then exact.
16. **Tint from the picture** (`tint_from = scene`, the input's mean hue). Drop it, a look
    keeping its chosen tint colour, or build plan 67 §3.8's picture → lane sampler first?
    [Rec] **drop it**: the sampler is worth building for its own reasons, later.
17. **The linger.** One Hold for the dream and its coverage (a dream fades with its picture,
    ≈ 5× sooner at the defaults than its region did), or a second knob, **Linger**, the
    coverage's own hold? [Rec] **one Hold**; Linger only if a look on the rig misses it.
18. **`dream.res`.** The dream runs at its input's size; a file that set a res gets a Resize
    before the dream. Resize counts its long side, so the migration needs an aspect: the rig's
    16 : 10 (res 256 → 408)? [Rec] **yes, 16 : 10**, said on load.
19. **Black is clear's ramp** is a smoothstep; the old "brightness is coverage" was linear, so a
    migrated trail or dream lays a little differently in its soft edges (up to about a tenth of
    coverage mid-ramp). Add a **linear** shape to the key — the classic luma-as-alpha, useful on
    any light-on-black picture — or accept the difference? [Rec] **add the linear shape**: a
    choice of the key's, appended, general.

## 8. The owner's goal, restated (2026-11-26): less duplication — overrules §4 and §7 where they differ

> "Recommendations look okay, generally. My goal is to reduce the degree by which the dream /
> echo subsystem is duplicitous of the other primitives we have in the system."

§3–§7's recommendations stand (Q15 Remap, Q16 drop, Q17 one Hold, Q18 16 : 10, Q19 linear
key: accepted as recommended). Asked of §7's design in turn — *what is still a second copy of
something the house has?* [V] — three things are:

| Still a copy | Of what | Instead [Rec] |
| --- | --- | --- |
| **Record** beside **Delay** | a delay is a stack one deep (plan 67 §7.1): two nodes that remember past frames, two buffers, two write passes, two "runs after every reader" rules (`Capture.after`, `DelayWrite`) | **one maker, the Delay**, with **Depth** (1 today's) and **Gap** (0 today's). Its output is a stack; a stack wired where a picture is taken is promoted to its newest entry (plan 67 §1 rule 4), so every saved delay draws as it does. The look-back is a Delay of depth 32. In audio terms, a multi-tap delay: an echo is a tap |
| **Read**, **Trail** and the **dream** as node classes of their own (`EchoNode`, `History`, `DreamNode`, `Dreamer`, `DREAM_FS`) | the effect: a file with knobs, `on`, `mix`, `blend` from the one library, a strip on the FX pane, a preview, fields into any knob (#497), a Python half where it needs one (`// @hook`, plan 63's Mandelbrot) | **all three are effect files.** Read and Trail are plain GLSL taking a stack (`// @takes image stack`: fx binds a `sampler2DArray` and the stack's count and ages, read through `_lib.glsl`'s `stack_at`). The dream is `dream.glsl` with a Python half: its hook submits the input when the worker is idle and binds the newest result; the file returns it; the effect's own `mix` and `blend` lay it back. Read's **At** takes a field because every effect knob does — that *is* Time Displace, with no line of its own |
| The **LOOKBACK page / pane section** (`ui_lookback`), the `dream.*` prefix split (`LOOKBACK_KEYS`, `is_lookback_knob`, `dream_owner`, `DREAM_SHARE`, `declare_lookbacks`), GRAPH's look-back area, echo pins and dream starters | the FX pane's strips, the effect's `fx.<file>.*` ids, GRAPH's ordinary nodes | **retired**: the readers and the dream are drawn, saved and routed as every effect is; the Delay as the delay is |
| Trail's **Count** beside the Delay's **Depth** | two knobs for "how many" | **Depth alone**: the trail reads all its stack holds (`dream.echoes` → Depth) |

**What remains new**, and why it cannot be an existing thing: the **stack** as a port type
(a picture is one entry; a field is space, not time), the Delay's Depth and Gap, and the
binding of a stack into an effect file. Everything else the dream and the echoes did is a
public primitive's.

**What remains the dream's own**, and why: the net's gradient pass, its octaves and its
Hold (§7.2) — the recursion that makes it a dream — and its worker thread. Its ids move to
`fx.dream.*` (`dream.layer` → `fx.dream.layer`, …), its `mix` / `blend` / `on` are the
effect's, and "one live dream" is said by its hook on a second instance.

**The build, again:** H1 the stack type, the Delay's Depth and Gap on a texture array, the
stack binding in fx, Read and Trail as files, picture Remap, the key's linear shape; H2 the
look-back and echoes migrated onto them, and `History`, `Capture`, `EchoNode`, the atlas,
`ui_lookback` and the prefix split deleted; H3 the dream as a hooked file, migrated, and
`DreamNode`, `Dreamer`, `DREAM_FS` deleted; H4 Time Displace as Read + a field, #488 closed.

### 8.1 Questions

20. **One maker**: the look-back merged into the **Delay** (Depth, Gap; a stack promoted to its
    newest where a picture is taken)? Its name **Delay** [Rec] — the word the graph and audio
    already use — or Look-back.
21. **Readers and the dream are effect files**, their knobs `fx.<file>.*` (saved `dream.*` and
    `dream.<n>.*` ids migrated), the LOOKBACK page retired into the FX pane? [Rec] yes.
22. **Depth is the only count**: the trail reads all the stack holds? [Rec] yes.

### 8.2 The owner's answers (2026-11-26)

- **Q20: one maker, the Delay** (Depth, Gap; a stack promoted to its newest where a picture is
  taken). Saved look-backs migrate to a Delay of depth 32.
- **Q21: Read, Trail and the dream are effect files**, the dream with a Python half; `dream.*`
  ids migrate to `fx.dream.*`; the LOOKBACK page retires into the FX pane.
- **Q22: Depth is the only count**; the trail reads all the stack holds.

Every question of §6, §7.5 and §8.1 is answered. H1 starts.

## 9. H1 built (2026-11-26)

Rows 1171–1174, hand checks 959–962 (group GF).

- **The delay's stack.** `delay[.n].depth` (1–64) keeps the pictures a delay takes, newest
  first, in a half-float texture array beside its pair (`stack.DelayStack`), copied in at the
  turn; made on a reader's ask, grown never shrunk, all stacks within 1 GiB. Its own picture is
  unchanged: every delay test, and 2916 sweep renders of every effect equal to `main`'s.
- **One cadence.** Main's #514 gave the delay its rate (frames, Hz, tempo) the same day;
  §4.2's **Gap** was dropped for it — a stack keeps exactly what the delay takes — so
  there is one cadence, and §4.4's time base is the delay's rate (seconds per entry are its
  ages, kept per entry).
- **The `stack` port**, typed in `graph` and `fx`, takes a delay and nothing else; a delay
  still makes a picture for every other port (so no wire type changed on GRAPH).
- **Read** (At, Between) and **Trail** (Level, Fade, Lay), effect files `@takes stack stack`.
  Time Displace is `Line → read.at` (`stack-slit`): H4 is now docs, the #488 proof and its close.
- **Curve** (Q15, named for the lane modifier per plan 67 §3.2) and **the key's linear ramp**
  (Q19), both public, both general.
- **Examples** `stack-echo`, `stack-trail`, `stack-slit`; checked in the app
  (`tools/drive_stack.py`): nothing unreached, every effect in the run, the delay's rate and
  Depth on its pane.

**Next: H2**, the look-back and its echoes onto the delay and Trail, migrated.

## 10. H2: the look-back and its echoes onto the delay (2026-11-26, a design)

The owner, after checking H1 out on the Mac: "it looks good for now. We should probably start the
H2 work in its own section." Stacked on H1 (#519). Nothing here is built.

### 10.1 What a saved look-back is [V]

A wired frame's `lookback` (or `lookback.<n>`): `X → lookback.image` (what it records),
`lookback.occluder` (whose brightness holds the wake back; the old default, `X` itself),
`scene.cover → lookback.cover` (the faces' coverage mask, **binary**: 1 where a face was drawn,
`render.CoverTarget`), and its picture into a composite's `over` (add, under `X`: the
one-shader look-back's bytes, `_trail_of`). Its pins `lookback.echo.<k>` are its k-th newest
commits. Its knobs are `dream.*` (`LOOKBACK_KEYS`), `dream.<n>.*` for `lookback.<n>`. The old
trail pass, per echo i, oldest first:

```
c   = pow(L_i, contrast) · (1 − darken)            (grade)
a   = w_i · peak(c),  w_i = echo_mix · ½^(age_i / fade)
wake = wake · (1 − a) + c · w_i
wake ×= 1 − occlude · max(min(4 · peak(occluder), 1), cover)
```

In the repository: 5 files hold a look-back node, 2 read echo pins, 1 wires an occluder, 1 a
cover; 59 carry `dream.*` values (contrast 1.0 in all, darken 0.1 or 0, occlude 1.0 in 48, 0.3
in 12). The owner's library on the Drive holds more; the migration is run over a copy of it and
its notes read before it lands (`tools/migrate_library.py`, a backup first).

### 10.2 What it becomes [Rec]

```
X ─► Curve (shape log₄ contrast) ─► Fade (level 1 − darken; keyed: peak, linear, level 0, soft 1,
     keep colour) ─► Resize (res) ─► Delay (depth = echoes, every Hz at 1 / gap) ═► Trail
     (level = echo_mix, fade, lay over) ─► Cut (amount occlude; mask: Matte of the occluder,
     peak, linear, key ⅛, soft ⅛ — that is min(4·peak, 1)) ─► Cut (amount occlude; mask: cover)
     ─► composite.over (add, under X)
lookback.echo.<k>  →  Read (at k − 1, nearest) of the same delay
```

- **Curve** only where contrast ≠ 1 (none in the repository); the **Fade** always (it carries the
  key; at darken 0 its level is 1).
- **The key on the Fade**, not on `X`: a key keys a node's picture for every consumer, and only
  the recorded copy must be keyed. Keyed, the delay keeps its alpha (`_Build._stacked`, #519), so
  Trail's over is the old layering, exactly: `c·w` laid by alpha `w·peak(c)`.
- **The two Cuts** are exact wherever the cover is 0 or 1 at occlude 1 or 0 (the default and 48 of
  60 files); at a partial occlude, where a face is drawn *and* the occluder is bright, they hold the
  wake back by up to a quarter more than the old max did. No public part takes the max of two masks.
- **Cadence:** gap seconds → the delay's rate in Hz (#514's grid), gap 0 → every frame.
- **Echo pins deeper than `echoes`** (Q25): a second delay of that depth, the same input, so the
  trail still lays `echoes` copies.
- **The dream** still reads `dream.darken`, `contrast` and `res` until H3 (it shares
  `DreamState`): they stay its own; the look-back's chain gets copies of their values, and a route
  on one is copied onto both (Q26).
- **Deleted:** `Lookback`, `History`, `Capture`, `EchoNode`, the atlas, `POST_FS`,
  `TRAIL_VARIANTS`, `_trail_of`, `lay_onto`, `fit_atlas`; `LOOKBACK_KEYS`, `is_lookback_knob`,
  `declare_lookbacks`, `ViewState.lookback`; GRAPH's look-back area and echo pins; the LOOKBACK
  page's look-back half. Old files keep loading: the migration rewrites them.

### 10.3 The migration

`graphmigrate.lookbacks(doc)`, keyed on a `lookback` node, a `lookback.<n>` entry or an echo pin
in any section, run as the ladder's last step after `hue_turns` (#509's model): no schema bump;
each new node takes the next free instance of its kind; values and rows retargeted with their
ranges (echo_mix → `fx.trail.level` 0–1 and fade → `fx.trail.fade`, the same log range, exact;
echoes → `delay.<n>.depth`, a push re-drawn across 1–64; darken → `fx.fade.level` = 1 − darken,
a push flipped; occlude → each Cut's amount; res → a Resize size; gap → hz, a push on gap
dropped and said — its inverse is no straight line, Q27). Notes on load name each.

**Proof.** Every repository file with a look-back, and the owner's library copy, drawn through
`main`'s renderer and through the migrated patch on this branch, the same frames at a fixed clock
(echoes need a run of frames): byte for byte where §10.2 says exact, bounded where it says not.
Golden frames that move are re-recorded on the Mac (a hand check).

### 10.4 Questions

23. **Occlusion.** Matte gains Key's **peak** measure and its **linear** ramp — one measure list and
    one ramp for the two (plan 67 §3.11: "one key: measure, then threshold"; they are copies today)
    — and the cover is a second Cut, exact at occlude 0 and 1? [Rec] yes. The alternative is a
    mask union op (`max` of two masks), new and used by nothing else yet.
24. **The trail's size.** The old ring was `res` on the short side (256: 408 × 256 at 16 : 10);
    Resize's sizes are powers of two on the long side. [Rec] **512** (320 short: a little more
    detail, 1.6× the memory, 13 → 21 MB at depth 8); or 256 (160 short: softer); or Resize takes
    any size.
25. **Echo pins deeper than the trail's count.** [Rec] a second delay at that depth; or one delay at
    the deeper depth, and the trail lays more copies than it did.
26. **Shared knobs until H3.** `dream.darken`, `contrast`, `res` keep driving the dream; the
    look-back's copies are new nodes; a route on one is copied onto both. [Rec] yes.
27. **A route on `dream.gap`** (none in the repository). [Rec] dropped with a note; or mapped
    approximately onto Hz.
28. **The tracers starters** (`tracers`, `tracers + dream`) spawn Delay (8, 30 Hz) → Trail (add)
    → Composite (add) — no key, no cuts: the simplest trail from public parts. [Rec] yes; the full
    chain is what a migrated file gets, not what a starter spawns.

### 10.5 The owner's answers (2026-11-26)

"The recommendations you had for the H2 stuff are fine." Q23–Q28 as recommended: Matte gains
peak and the linear ramp, the cover a second Cut; the trail's Resize at 512; a second delay for
echo pins deeper than the count; darken, contrast and res copied, routes onto both; a route on
gap dropped with a note; the tracers starters spawn Delay → Trail → Composite (add).

From the owner's hand checks of H1 on the Mac: past a frame size's budget the picture went black
(depths 36, 53); fixed in #519 — a delay keeps the frames that fit and says so. A migrated
look-back at 512 × 320, depth 32, is 42 MB, far inside it.
