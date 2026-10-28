# Vision spike: segmentation, edges and masks on the graph (towards plan 39)

Investigation run 2026-10-27 on the dev MacBook (Apple M3 Max, macOS 26.6, Python 3.14.4, torch 2.14 on MPS).
Nothing in the app changed; the two benchmark scripts beside this file ran in scratch `uv run --with`
environments. The ask: take real-time video, split it into foreground and background, find edges, and use
any picture as a mask laid over other pictures — and understand what each needs before deciding how the
nodes are cast onto the graph. Plan 37 (nodes as pictures, the faces) and plan 38 (output hold) are spoken
for, so this is written towards a plan 39 — now [`../../39-vision.md`](../../39-vision.md), agreed the same
day; this file stays as the record of what was found and measured.

Summary:

| Question | Answer |
|---|---|
| Do we have live video on the graph? | Yes: `channel.a`–`h` (camera via PyAV/avfoundation, NDI, Syphon), a premultiplied RGBA picture at frame size |
| Can a CPU model read the camera frame without a GL readback? | Yes for camera and NDI: the newest frame stays a numpy array (`MediaState.frame(c)`); Syphon is GPU-only and needs the dream's readback path |
| Is there a precedent for an asynchronous ML producer on the graph? | Yes: `dream` (torch on MPS on its own thread, latest-wins, result a frame or two late) — the template |
| Person segmentation cost here | Apple Vision on the Neural Engine: **3.6 ms** (fast, 256×192 mask) / 14 ms (balanced, 512×384) / 36 ms (accurate, 2016×1512) per 720p frame; torchvision LR-ASPP on MPS: **7 ms** at 640×360 including upload and readback |
| Any-subject (not only people) segmentation | Apple Vision subject lift: 11 ms per 720p frame |
| Edge detection cost | Negligible: a one-pass Sobel in an effect file, no Python, today |
| Can a picture be used as a mask today? | **No, not cohesively.** Alpha rides on every picture (premultiplied) and a composite's `over` keeps it, but no node makes a mask from a picture, no node takes one except the look-back's cover, and effects have two picture inputs and one pass |
| New dependencies | `pyobjc-framework-vision` (tiny, macOS only) for the Vision path; none for the torchvision path (a 13 MB weights file on first use) |

## 1. What the engine has today

### 1a. Live video in

- **Camera** (`media/camera.py`): PyAV `avfoundation`, 1280×720@30 first; each frame is swscale'd to RGBA8
  on the `media-live-<id>` thread and published by one reference swap (`source.Latest`), newest wins.
  Frames over 720p are shrunk with a Lanczos resize on that thread. Colour is whatever swscale defaults to;
  nothing marks sRGB or linear.
- **NDI** (`media/ndi.py`): cyndilib, RGBA, one copy per frame, capped to 720p, alpha passed through when sent.
- **Syphon** (`media/syphon.py`): a GL texture in our share group, no CPU pixels at any point.
- **Upload** (`media_tex.py`): one synchronous `tex.write` plus mipmaps per channel per frame, only when
  `(frame, t)` moved and only if something reads the channel; rows top-first so samplers flip v.
- **On the graph** (`graph.MediaNode`, `Renderer._media_fit`): the consumer gets a frame-size RGBA8 picture,
  premultiplied by the source's alpha and the channel's opacity, transparent outside a contain fit.
- **After upload the CPU frame stays readable**: `LiveSource.latest()`, `MediaState.frame(c)`. A model can
  read it with no readback at all.
- **Readback paths that exist**: `lookback.Dreamer.submit` (a downsample pass then one `read_into`, about
  0.4 ms, straight into a torch MPS tensor's host-visible buffer); `publish.NdiOut._read` (double-PBO,
  a frame late, ~4 ms at 1080p).

### 1b. Masking and compositing

Port types are `image`, `mask`, `geometry`, `value` (`graph.py:147-168`). `mask` is "a one-channel mask at
the frame's size". **One node makes a mask** (`Cover`: the faces drawn solid, for the look-back) and **one
port takes one** (`lookback.cover`). `value` is declared and unused.

| Primitive | What it does with alpha or a second picture | Is it a mask? |
|---|---|---|
| `composite` (`under`, `over`, `depth`; blend over/add/depth) | premultiplied over: `over + under·(1−over.a)`; since PR #240 a laid-over scene clears to alpha 0 so its alpha survives | takes no matte |
| `blend.glsl` (effect, `aux` in) | over / multiply / screen / difference / **luma key**: keys the aux by its own brightness, then aux over src | a keyer of the overlay, not a matte for a third picture |
| `displace.glsl` | aux luma as an offset | no |
| `lookback.occluder` + `cover` | an IMAGE's brightness ×4 and the cover MASK hold the trail back | the only real "picture as mask" in the code, hard-wired to the trail |
| every effect's tail (`fx.py:560-575`) | `c.a = max(c.a, max(rgb))`, and `c.a = 1` on an opaque window unless the effect is laid over | lifts alpha, never cuts it |
| faces (`shape.faces`) | a wired picture's alpha is the face intensity | a mask-like read, by accident of the premultiplied convention |

What is missing: any picture → mask (luma/alpha/chroma key, threshold, invert, feather, dilate), any
image + mask → image (cut, matte on a composite), any Sobel/blur/convolution/morphology shader (the
nearest is `_lib.glsl reach()`, a 16-tap dilation only glimmer uses, and `zoomblur`). Effects are capped
at two picture inputs (`image`, `aux`) and one pass; a separable blur is two chained files, which the pool
already ping-pongs.

### 1c. The node system, as it bears on this

- A kind is spread over tables in `graph.py` (`NODE_KINDS`, `DECLARED`, `RESERVED`, `_wired_kind`,
  `WIRED_MAKES`/`WIRED_TAKES`, `_Build._make`) plus `graphview.py` (labels, picker, owners) and a
  `params.declare_*`; the comment at `graph.py:605` says a kind is "one line here and its node class in its
  own block". A `/7` preset needs no migration for a new kind; an older build reads the section as black.
- Nodes *make* a texture or *paint* into the consumer's framebuffer; `picture(frame, node)` binds a painted
  one. Persistent state lives on the renderer keyed by node name (delay pairs, rings), since nodes are
  rebuilt with the graph.
- **Own size** (plan 34/35): a node may run at its own size and consumers get it refitted by cover
  (`OWN_FIT`). A mask at the model's resolution fits this exactly.
- **No latency concept** on edges: nothing aligns branches in time. The dream shows the only pattern:
  show whatever result has landed, pass the input through until the first one, say the lag in `said`.
- **No per-node previews** on GRAPH; the backdrop draws output 1 with `add_image`, and the render
  context's textures are visible to the control window, so a node body could draw its mask the same way.
- A shader node is one file in `shaders/fx/` with `@param` uniforms; `src(uv)`, `aux(uv)`, `aux_luma(uv)`;
  no Python, hot-reloaded.

### 1d. A caveat found on the way (untested)

`render.py:2785`: `if s.cut_through and bg_alpha < 1.0` picks the plain `SRC_ALPHA, ONE_MINUS_SRC_ALPHA`
blend, whose alpha is `a² + (1−a)·dst`. Since PR #240 a scene laid into a composite's `over` clears to a
zero ground, so on an opaque window with `view.cut_through` at its default (on) that scene's alpha lands as
a² while its colour is c·a — not consistent premultiplied data, and an over-composite of a half-transparent
face would then show too much of what is under it. The existing tests check the window's alpha (forced to 1
at the output) and the overlay case, not this one. Masks will lean on alpha being honest, so a test here is
a pre-step of the plan.

## 2. The technical requirements

### 2a. Foreground / background segmentation: three families

**ML matte** (a person, or any subject). Measured on synthetic 720p frames, so these are costs not accuracy:

| Backend | Where it runs | Per frame | Mask |
|---|---|---|---|
| Apple Vision `VNGeneratePersonSegmentationRequest`, fast | Neural Engine | 2.7 ms (640×360 in) / 3.6 ms (1280×720 in) | 256×192, 8-bit, soft |
| … balanced | Neural Engine | 12 / 14 ms | 512×384 |
| … accurate | Neural Engine | 35 / 36 ms | 2016×1512 |
| Apple Vision `VNGenerateForegroundInstanceMaskRequest` (subject lift, macOS 14+) | Neural Engine | 11 ms | per instance, input size |
| torchvision `lraspp_mobilenet_v3_large`, fp16 | MPS, shares the GPU with the renderer and the dream | 6.6 ms at 320×240 … 7.6 ms at 640×480, upload and readback included | input size, 21 classes (person = 15), soft |

- The Vision path imports through pyobjc (`pyobjc-framework-vision`, 3 small wheels), works on this Python
  (the request needs `alloc().initWithCompletionHandler_(None)`; `init`/`new` are unavailable), and keeps the
  GPU free. It is macOS-only, which the media adapters already are.
- The torchvision path adds no dependency and would run anywhere torch does, but it contends with the
  dream on MPS and needs ImageNet-style normalisation and a softmax; the mask is per class, so "person" is a
  choice of class.
- **Input**: for camera and NDI the worker reads the channel's numpy frame, at the camera's cadence (30 fps,
  so half the render frames carry no new work). For Syphon, or any other picture on the graph (the scene, an
  effect's output), the dream's downsample-and-readback is the path; 0.4 ms at the dream's size.
- **Output**: a one-channel 8-bit mask at the model's size, uploaded like a media frame (`tex.write` keyed by
  result id). Bilinear sampling and a feather in the consumer hide the low resolution; the fast person mask
  at 256×192 is the one to try first for a party, balanced if the halo shows.
- **Latency**: on a worker thread the mask lands one or two render frames after its frame, like the dream;
  at 60 fps that is inside one camera frame, so the mask trails the picture by at most 33 ms. If the halo on a
  fast-moving dancer bothers, the picture branch can go through a `delay` to meet it — no new concept.
- **Temporal coherence**: the model is per-frame; a short exponential smoothing of the mask (in the worker, or
  in GLSL through a delay loop) removes flicker at the cost of a little more trail.
- **Threading**: one worker per segment node on the `DreamWorker` pattern (one pending job, latest wins, lock-free
  latest, errors kept out of the frame loop). Vision releases the GIL during `performRequests`.

**Background model** (a static camera, anything that moves is foreground). Pure GLSL on primitives the graph
has: `bg ← mix(bg, frame, k)` through a `delay` loop, `mask = smoothstep(t−s, t+s, |frame − bg|)`. No
dependency, no latency, no model; it fails when the subject stands still (they fade into the background at
rate k) or the camera moves, and it keys shadows. Worth having as a mode because it is free and it is the
"anything that moves" look, not the "a person" look.

**Keys** (luma, chroma). Pure GLSL, one pass, per pixel; the luma key exists inside `blend`. A chroma key is a
distance in a chroma space with a soft edge; useful with a lit backdrop or a projected colour, not for a
dance floor.

### 2b. Edge detection

- **Sobel** (gradient magnitude, optionally direction as hue): one pass, eight taps, on any picture — the
  camera, but also the scene, where the polytope's edges and face boundaries make a look of their own. Cost
  is nothing. It is an effect file today (`edges.glsl`) with no Python.
- **Canny-like** (blur → gradient → thin → hysteresis): three or four passes, each a chained effect file;
  the pool already alternates textures. The thinning and hysteresis are what make lines one pixel wide; for
  a projected look, Sobel with a threshold and a glow is usually enough.
- **Output**: an edge map is naturally a mask (magnitude) and a picture (coloured, over black, premultiplied).
  Which it is on the wire is a casting decision below.

### 2c. "Use an image as a mask": the operations a cohesive set needs

1. **picture → mask** (`matte`): from luma, from alpha, or from chroma distance; a key level and softness;
   invert; feather (blur) and dilate/erode. This is also what turns an `edges` picture, a pattern, a still
   from the media folder, or the scene itself into a mask.
2. **picture + mask → picture** (`cut`): the picture's alpha becomes the mask (premultiplied: rgb × m, a × m).
   Everything downstream already honours alpha: a composite's over, the faces, the look-back.
3. **mask + mask → mask** (min, max, multiply, invert): `cut` composes most of these implicitly (cut by one,
   then matte again); a dedicated node can wait.
4. **mask in time**: smooth (exponential), hold. The segment node should own its own smoothing; a general
   version is a delay loop.

With the segment node making two pictures (§3) and 1 and 2 beside it, the stated use cases are all wiring:
camera → segment.fg → composite.over (the dancer over the polytope); segment.fg → kaleido (the effect only
inside the silhouette); segment.fg → matte → cut(scene) (the scene only where the dancer is);
segment.bg → matte → cut(scene) (the scene only where they are not); edges → matte → cut(pattern).

## 3. Casting onto the graph: a proposal

Principle: **segmentation is one node on any bitmap, foreground and background out as bitmaps** (the owner's
casting, 2026-10-27); **a mask is a wire type**, the existing `mask`, a one-channel picture of some size, and
**nodes convert between bitmap and mask explicitly** (`matte`, `cut`); the WYSIWYG rule holds (every input is
a drawn wire, no default graph). Because the input is any bitmap, the general path is the dream's
downsample-and-readback; reading the camera's numpy frame instead is a shortcut the node takes only when its
`image` wire comes straight from a channel, and the wire is still drawn.

| Node | In → out | Params (modulatable unless said) | Notes |
|---|---|---|---|
| `segment[.n]` | `image` → two pictures: `segment.fg` and `segment.bg` (pins, like `scene.depth`); optionally `segment.mask` | `mode` person / subject / motion (choice); `quality` fast / balanced / accurate; `feather`; `smooth`; `on` | the owner's casting (2026-10-27): any bitmap in, the foreground and the background out as bitmaps, each the input with its alpha cut by the matte (premultiplied), so either lands straight on a `composite.over`, the faces or an effect; the matte itself is internal unless the `mask` pin is wired. The mask is made at the model's own size and sampled bilinearly at the input's; one worker per node; `said` carries "256×192 · Vision fast · a frame or two late"; `on` off: `fg` is the input whole, `bg` nothing |
| `matte[.n]` | `image` → mask | `from` luma / alpha / chroma; `key`; `soft`; `invert`; `feather` | one GLSL pass; the general picture → mask; `key` is where a pixel starts to pass, `soft` and `feather` the only departures from 0 or 1 |
| `cut[.n]` | `image`, `mask` → image | `invert`, `amount` | one GLSL pass; where the mask passes the picture stays, elsewhere it is cut away (transparent, premultiplied), so what is under it on a composite shines through; no mask wired = the picture through |
| `edges` | an effect file | `threshold`, `glow`, `colour`/`hue by direction` | needs no Python; its picture becomes a mask through `matte` |
| `composite.mask` | an optional `mask` port on `composite` | — | the familiar matte-on-the-layer; optional, `cut → over` does the same |

- **Type rule to add**: a `mask` wired where a picture is taken reads as a grey picture (white where the
  mask is 1). One-way promotion: it lets a mask feed an effect, a switch, an output (so you can *see* the
  mask on a window and on a node preview) without a converter; the reverse is always an explicit `matte`.
- **Resolution**: `segment` has an own size like `resize`; consumers get it refitted by cover; `cut` runs
  at its picture's size and samples the mask bilinearly, feathered.
- **Latency**: no new concept; the dream's "show what has landed" and `said`. The `delay` node is the
  alignment tool when needed.
- **Backends**: a `segment.backend` in config, not in the preset (Vision first on macOS; torchvision as the
  cross-platform fallback; "motion" needs neither), imported lazily like the media adapters and the dream,
  never on `import hyperspace.app`. Weights for the torch path go with the dream's in `<home>/weights`.
- **Cadence**: submit only when the channel's `MediaFrame.frame` moved (camera 30 fps), not every render
  frame.
- **Previews**: a mask node drawing its texture in its body on GRAPH is the first per-node preview; plan 37
  (nodes as pictures) is the natural home, or a `want()`-gated texture like MEDIA's channel previews.
- **Effects stay at two inputs and one pass.** Masking is a node's business (`cut`, `composite.mask`), not
  a third effect input; a blur is two chained files.

## 4. Decisions (answered by the owner 2026-10-27, item 6 pending)

**The owner's definition of a mask**, which the plan builds on: *alpha is how transparent a thing is; a mask
is a pattern — a pixel passes or it doesn't.* A mask is not carried in alpha. The use case: an image as the
foreground, a mask over it that cuts part of it out, and the background shines through where it was cut.
So the `mask` wire carries 0 or 1 per pixel (soft only at an edge the feather asks for), `cut` is the
operation that applies it to a picture, and alpha stays what it is today.

1. **Mask as a wire type with explicit converters** (`matte`, `cut`), not masks riding in alpha —
   **yes** (the owner: alpha is a different thing from a mask).
2. **A mask may be wired as a picture** (one-way promotion, read as white where it passes) — **yes**.
3. **`segment` takes any bitmap and makes two bitmaps, the foreground and the background**; bitmap → mask
   is the separate `matte` node; `segment.mask` also exposed as a pin — **yes**.
4. **Backend**: Apple Vision first (Neural Engine), torchvision as the fallback behind the same node —
   **yes**.
5. **Modes in the first build**: person and motion first, subject after — **yes**.
6. **`composite.mask` port** beside `cut` — **open** (explained to the owner; see below).
7. **`edges` as an effect file now**, ahead of the plan — **yes**.
8. **Order**: **before plans 37 and 38**.

On 6: the use case above is two nodes with `cut` — `fg → cut.image`, `mask → cut.mask`, `cut → composite.over`,
`bg → composite.under` — or one node if `composite` itself takes the mask on a third port and applies it to
its `over`. `cut` is needed either way (a cut picture also goes to the faces, an effect, an output);
`composite.mask` is a convenience that saves one node in the most common wiring. The proposal: build `cut`
first, add `composite.mask` if the two-node wiring feels like one too many at the machine.

## 5. Quick wins that need no plan

- `shaders/fx/edges.glsl`: Sobel magnitude (and hue by direction), threshold, glow.
- `shaders/fx/cutout.glsl`: `src(uv) * (aux_luma(uv) keyed)`, an interim "cut by a picture on aux" until
  `cut` exists. Its output must go into a laid-over place (a non-add `composite.over`) for the alpha to survive
  the opaque-window `c.a = 1` tail (`fx.py:572`).
- A background-model preset built from `delay` + `blend` difference + the luma key: proves the motion look
  with today's nodes.

## 6. Risks and open questions

- §1d: the cut-through blend on a laid-over scene; test first.
- Accuracy on real content is unmeasured (synthetic frames here): a hand check at the machine with the
  camera, a dancer and the party lighting; the fast person model's 256×192 halo under projection.
- MPS contention if the torch backend and the dream run together; the Vision path avoids it.
- Orientation: media textures are rows-top-first and flipped by samplers; the mask must follow the same
  convention or `cut` samples it upside down.
- A second camera (two `segment` nodes) doubles the worker; Vision handles it, the torch path would share a
  model.
- The subject-lift request returns instances; summing them to one mask is the simple first reading.

## Appendix: raw numbers (synthetic frames, 30 iterations after warm-up)

```
lraspp float32 320x240: 6.5 ms   lraspp float16 320x240: 6.6 ms
lraspp float32 640x360: 7.6 ms   lraspp float16 640x360: 7.1 ms
lraspp float32 640x480: 8.1 ms   lraspp float16 640x480: 7.6 ms
vision person q=0 (accurate) 640x360: 34.8 ms  mask 2016x1512 L008
vision person q=1 (balanced) 640x360: 12.0 ms  mask 512x384 L008
vision person q=2 (fast)     640x360:  2.7 ms  mask 256x192 L008
vision person q=0 1280x720: 36.4 ms · q=1: 14.0 ms · q=2: 3.6 ms
vision subject lift 640x360: 10.5 ms · 1280x720: 10.9 ms (no subject in noise; timing only)
```

Scripts: `bench_torch_seg.py` (run with `uv run python -I`), `bench_vision_seg.py` (run with
`uv run --with pyobjc-framework-vision python -I`).
