# Plan 39 — vision: foreground and background from any picture, masks as their own wire, edges

**Status: agreed, not built (2026-10-27).** From the owner's ask of 2026-10-27
("take real-time video feeds and segment them into foreground and background,
possibly doing edge detection as well … use an image as a mask to lay on top
of other images") and the spike that answered what it needs
([`assets/39-vision/findings.md`](assets/39-vision/findings.md): the engine's
video, masking and node system as they are, and segmentation measured on the
dev Mac). **Every decision is the owner's, 2026-10-27**, recorded below; none
is open. Build plan [`39-vision-build.md`](39-vision-build.md). Runs in
parallel with plans 37 and 38
([`37-38-39-orchestrator-prompt.md`](37-38-39-orchestrator-prompt.md)), and
lands before either if it is ready first.

The owner's two sentences this plan builds on:

- **One concept.** "I can take an arbitrary bitmap and do foreground/background
  segmentation on that, and then have those two things come out of that node
  as two bitmaps. A separate node could handle the conversion of a bitmap
  into a mask."
- **Alpha is not a mask.** "Alpha is: how transparent is this thing? A mask
  means that I have a pattern here, and it's a very binary thing. Either the
  pixel passes, or it doesn't. I don't necessarily want to ride on alpha to
  make that happen … have an image as your foreground, then put a mask over
  that image that cuts out part of that image, and then allow the background
  to shine through."

## What exists (the spike, in one paragraph)

Live video is on the graph as `channel.a`–`h` (camera through PyAV, NDI,
Syphon), a premultiplied picture at frame size; a camera's or NDI's newest
frame stays a readable numpy array after upload, Syphon has no CPU pixels.
`dream` is an asynchronous worker on the graph (its own thread, latest wins, a
result a frame or two late, the lag said on the node) and is the template.
`mask` is already a port type (purple), made by one node (the faces' cover)
and taken by one port (`lookback.cover`). Nothing makes a mask from a
picture, nothing cuts a picture by a mask, effects have two picture inputs
and one pass, and there is no Sobel, blur or morphology shader. Measured on
the M3 Max: Apple Vision person masks 3.6 ms per 720p frame on the Neural
Engine (fast, 256×192), 14 ms balanced; subject lift 11 ms; torchvision
LR-ASPP 7 ms on MPS with no new dependency.

## The decisions (owner, 2026-10-27)

| # | decision | answer |
|---|---|---|
| 1 | A mask is its own wire type (`mask`), with explicit converters (`matte`: picture → mask, `cut`: picture + mask → picture); masks never ride in alpha | **yes** |
| 2 | A mask may be wired where a picture is taken; it reads as white where it passes, black elsewhere (one-way; the reverse is always a `matte`) | **yes** |
| 3 | `segment` takes any bitmap and makes two bitmaps, `segment.fg` and `segment.bg`; its matte is also a pin, `segment.mask`; bitmap → mask is the separate `matte` | **yes** |
| 4 | Backend: Apple Vision first (the Neural Engine), torchvision behind the same node as the fallback | **yes** |
| 5 | Modes in this build: **person** and **motion** (a background model); **subject** after | **yes** |
| 6 | `cut` first; a `mask` port on `composite` only if the two-node wiring feels like one too many at the machine | **cut first** |
| 7 | `edges` as an effect file, ahead of the plan | **yes** (T0) |
| 8 | Order: before plans 37 and 38 — now: in parallel with them, each on its own branch | **parallel** |

## What this plan does

### W1 — the mask is a wire (decisions 1, 2)

- `graph.MASK` stays the type. Its meaning is the owner's: **a pattern; a
  pixel passes (1) or it does not (0)**; a value between is only an edge the
  feather or softness asked for. Stored as a one-channel 8-bit texture at the
  maker's size.
- **Promotion.** `_wired_error` accepts a `mask` maker into an `image` port.
  The consumer sees a picture: white (premultiplied, opaque) where the mask
  passes, black elsewhere, at the consumer's size (fitted by cover, as an
  own-sized node is). So a mask can be wired to an output to be seen, into an
  effect, into a switch, into the faces. The reverse is refused as today
  ("`x` makes a picture, `y.mask` takes a mask — put a `matte` between").
- No node of plan 36 or earlier changes: `scene.cover → lookback.cover` is
  unchanged (the cover is now one of several mask makers).

### W2 — `matte[.n]`: picture → mask (decision 3)

One GLSL pass over its `image` input, at the input's size (own size: its
input's), one channel out.

- `matte.from` (choice): **luma** (brightness), **alpha** (the picture's own
  coverage — how a `segment.fg` or a cut picture becomes a mask again),
  **chroma** (distance from `matte.hue` at `matte.sat`, a chroma key).
- `matte.key` 0–1: where a pixel starts to pass. `matte.soft` 0–0.5: the
  width of the edge around the key (0 = hard). `matte.invert`.
  `matte.feather` 0–32 px: a blur of the mask (two chained passes inside the
  node, separable). All modulatable; group `matte` (the preset's).
- Unwired: makes nothing (the node says so; a `cut` fed by it shows its
  picture whole).

### W3 — `cut[.n]`: picture + mask → picture (decisions 1, 6)

One GLSL pass at the picture's size. Where the mask passes, the picture;
elsewhere **cut away**: transparent black (premultiplied), so on a
`composite.over` what is under shines through, on the faces that face is
dark, on an output it is the ground. `cut.invert` (keep the hole, cut the
rest); `cut.amount` 0–1 (how far the cut goes: 1 cuts to nothing, 0.5 dims the
cut part). The mask is sampled bilinearly at the picture's size (a
256×192 person mask on a 720p picture is smooth, not blocky; `matte.feather`
softens it further). No mask wired: the picture through, untouched.

Composite stays as it is. The owner's use case is the wiring
`fg → cut.image`, `mask → cut.mask`, `cut → composite.over`,
`bg → composite.under`.

### W4 — `segment[.n]`: any picture → foreground, background, mask (decisions 3, 4, 5)

The one concept. A node with one `image` input and three pins:

| pin | type | what it is |
|---|---|---|
| `segment.fg` | image | the input where the matte passes, cut away elsewhere (premultiplied) — the dancer |
| `segment.bg` | image | the input where the matte does not pass, cut away elsewhere — the room |
| `segment.mask` | mask | the matte itself, at the model's size |

- **`segment.mode`** (choice, not modulatable): **person** (a person
  segmentation model), **motion** (a background model: what moves against
  a still camera). **subject** (any foreground object) is declared in the
  choice and refused in words until a later build.
- **`segment.quality`** (choice): fast / balanced / accurate — the model's
  own levels (Vision: 256×192 at ~4 ms, 512×384 at ~14 ms, 2016×1512 at
  ~36 ms per 720p frame); the torch backend maps them to its input size.
- **`segment.feather`** 0–32 px, **`segment.smooth`** 0–1 (an exponential
  smoothing of the matte between results, against flicker),
  **`segment.on`** (off: `fg` is the input whole, `bg` nothing, `mask` nothing,
  the worker idle). Group `segment`, the preset's; `feather`, `smooth`,
  `on` modulatable.
- **The worker.** One per node, on the dream's pattern (`segment.py`, a
  `SegmentWorker`): `submit(frame, index)` never blocks (latest wins, drops
  counted), `latest()` lock-free, errors caught and said, the thread sleeps
  when nothing is submitted. The backend is chosen once from config
  (`[segment] backend = "vision" | "torch" | "auto"`, auto = Vision on macOS
  else torch), imported inside the worker's first job — never on
  `import hyperspace.app` (the app-boundary test extends to `Vision`,
  `objc` through it, and keeps `torch` gated).
  - **vision**: `VNGeneratePersonSegmentationRequest` through pyobjc
    (`alloc().initWithCompletionHandler_(None)`, quality level from
    `segment.quality`), a `CGImage` made from the RGBA frame without a copy
    where pyobjc allows, the result's `CVPixelBuffer` (`L008`) read into a
    numpy array. New dependency `pyobjc-framework-vision ; sys_platform ==
    'darwin'`.
  - **torch**: `torchvision.models.segmentation.lraspp_mobilenet_v3_large`,
    fp16 on MPS, class 15 (person) softmax as the matte; weights looked for
    in `<home>/weights` then torch's hub cache, downloaded on first use with
    a line on stderr, like the dream's.
  - **motion** needs no backend: it is GLSL on the frame thread — a running
    background `bg ← mix(bg, frame, k)` in a half-float pair the renderer
    holds under the node's name (as `delay_pair` does), the matte
    `smoothstep(t − s, t + s, |frame − bg|)` with `segment.sense` (t) and
    the feather; `segment.learn` (k) says how fast a still thing becomes
    background.
- **The input path.** The node's `image` is a drawn wire (WYSIWYG). The
  worker's input is the dream's path: a downsample pass to the model's
  input size and one `read_into`. **The shortcut:** when the wire comes
  straight from a `channel.<c>` whose newest `MediaFrame` has CPU pixels
  (camera, NDI), the worker reads that array instead and no readback runs;
  Syphon and every other picture use the readback. Submits happen only when
  the input moved (a channel's `MediaFrame.frame`; otherwise every frame).
- **Latency.** No new concept: the pins show the newest matte that has
  landed, the input passes through whole until the first one, and the node
  says `256×192 · Vision fast · a frame or two late · 29 fps` (the result
  rate). The `delay` node is the alignment tool if the halo on a fast mover
  bothers.
- **Own size.** The mask pin's own size is the model's; `fg` and `bg` are at
  the input's size (the matte sampled bilinearly, feathered).
- A `segment` no wire reaches is not built and its worker never starts; a
  removed node's worker stops within a second. Several segment nodes are
  several workers (Vision takes it; the torch backend shares one model).

### W5 — `edges`: an effect file (decision 7, T0)

`shaders/fx/edges.glsl`: Sobel over `src`, `u_threshold` (below it nothing),
`u_glow` (a wider second ring), `u_colour` choice: **white** (magnitude as
grey, over black), **source** (the input's colour on the edges), **direction**
(hue by gradient angle). Premultiplied, so it is already a picture that a
`matte` (from luma) turns into a mask. Lands first, on its own, with a golden.

### W6 — GRAPH, the pages, the preset

- GRAPH: the three kinds in the picker under MEDIA (`segment`) and a new
  **MASKS** group (`matte`, `cut`), labels and hovers, their params as ports
  (`OWNERS`), a starter **"cut-out"** (`channel.a → segment`, `segment.fg →
  composite.over`, `scene → composite.under`, `composite → output.all.image`).
  Mask cables stay purple; a promoted mask cable is drawn purple into a red
  port. Nothing else on the canvas changes (plan 37 owns how a node looks).
- The node's `said` line carries the worker's state (above); errors (no
  backend, no weights, no camera permission) in words, never a crash.
- A preset saves the nodes as entries (`{"kind": "segment", "instance": n}`
  etc.) and their params as values, schema `/7` unchanged (a new kind is new
  words; an older build reads the section as black with a note, which both
  Macs on this build avoid).
- `tests/fixtures/presets/`: `cut-out` (a still from `tests/golden/media`
  through `matte` and `cut` over the scene), `segment-motion` (two stills
  as the frames of a motion segment), `mask-as-picture` (a matte wired to an
  output); goldens for each, the 757 before unmoved. The Vision and torch
  backends are tested with a fake worker (as `test_dream.py` does) and one
  marked test each that runs the real model on a synthetic frame.

## Not in this plan

- `subject` mode (Vision's subject lift) — declared, refused in words.
- A `mask` port on `composite` (decision 6: after the machine says so).
- Mask arithmetic nodes (min/max/multiply) — `cut` then `matte` composes them.
- Per-node picture previews on GRAPH — plan 37's; `segment`'s pins show
  there as any picture node's do once plan 37 lands.
- A Canny-style thin edge (blur → gradient → thin → hysteresis) — chained
  effect files if ever wanted.
- Phone camera as a source — plan 32 V2.

## Risks, and the test that comes first

- **Alpha must be honest** before cut pictures land on composites.
  `render.py:2785`: `if s.cut_through and bg_alpha < 1.0` picks the plain
  alpha blend (alpha = a² + (1 − a)·dst); since PR #240 a scene laid into a
  composite's `over` clears to a zero ground, so on an opaque window with
  `view.cut_through` on (the default) that scene's alpha is squared while its
  colour is c·a. T1 writes the test; if it fails, the fix is that the
  cut-through branch applies only on a see-through *window*
  (`View.bg_alpha < 1`), never on a laid-over scene's ground.
- Accuracy on real content is unmeasured (synthetic frames in the spike):
  hand checks at the machine with the camera, a dancer and party light.
- The torch backend shares MPS with the dream and the renderer; Vision does
  not. `auto` picks Vision on macOS.
- Orientation: media textures are rows-top-first and samplers flip v; the
  matte from the CPU shortcut is rows-top-first too and must be flagged the
  same way, or `cut` samples it upside down (a test with an asymmetric
  frame).
- Camera permission: the first `avfoundation` open prompts; `segment` on a
  channel with no frame says "no frame on channel a" and makes nothing.

## Hand checks (group AJ, numbers assigned in the orchestrator prompt)

1. A webcam on `channel.a`, `segment` in person mode, `segment.fg` on a
   composite over the scene: the person over the polytope, the room gone;
   `segment.bg` instead: the room with a person-shaped hole showing the
   polytope.
2. `segment.quality` fast → balanced → accurate at the machine: the edge
   quality against the SYSTEM page's frame time and the node's said rate.
3. `segment.feather` and `segment.smooth` by eye: the halo and the flicker.
4. Motion mode on a still camera: walk through — the walker is foreground;
   stand still for `segment.learn` seconds — they fade into the background.
5. `matte` from luma on a still from the media folder, `cut` a kaleido
   branch by it over the scene: the owner's "image as a mask" case.
6. A `matte` wired straight into an output: white where it passes
   (decision 2).
7. `edges` on the scene: the polytope's lines; on the camera: the room's
   lines; `edges → matte → cut(pattern)`.
8. Two cameras, two segments: both run; frame time on the show Mac.
9. Unplug the camera mid-show: the node says so, the picture passes through
   whole, nothing crashes; plug it back: it resumes.
10. The cut-through test (T1) by eye: a half-transparent face laid over a
    bright backdrop on the projector, `view.cut_through` on and off, no
    brightening.
