# Plan 32 — media: sources, the media folder, eight channels, and what reads them

**Status: designed, not built (2026-10-22).** Designed with the owner in
one session; the decisions below (rows 321–339) carry a recommendation
each and wait for the owner's answer. Nothing here is code yet. Once the
rows are answered, the work packages become an executable plan (briefs
per WP, as `28-30-orchestrator-prompt.md` did).

**Base: `plan-28-30-integration` @ 1a5cc2e** (row 338). `main` (fec80ee)
has no `graph.py` and no `devices.py`: the render graph (plan 26), the
device registry (plan 27) and the effect nodes (plan 30) this plan plugs
into exist only on the #195 → #224 stack. Plan 31 (`plan-31-integration`)
is independent of this one; the one place they meet is the preset
schema number (row 337).

## What the owner wants (2026-10-22)

- **Use pictures and video in a more fun way**: stills and videos under
  the geometry, through the shaders, on the faces.
- **A media library**: the pictures and videos you care about, easy to
  reason about and swap between. Ideally the **shared cloud folder**,
  responsive when a file is dropped in, plus sources local to one Mac.
  A preset that names a local source another Mac lacks is fine: a clear
  banner on the media page says so.
- **Live feeds**: anything giving frames at a resolution and rate — a
  local webcam, **Syphon** and **NDI** (to talk to Resolume and
  TouchDesigner), and **a phone streaming into the show after scanning
  a QR code**. Bringing our own router for that is acceptable.
- **A bus of channels**: a source is put on a channel; consumers (the
  backdrop, the faces, an effect) subscribe to a channel; swapping what
  is on channel A while things read channel A *is the point*. **Eight
  channels.**
- **Adapters**, modular and isolated, so a new kind of feed (compressed
  video, a protocol) is one new module.
- **A playback cursor you can scrub**: native speed, any multiple of it,
  and a jog behaviour like Harmor's image-resynthesis playhead — a
  rotary encoder you spin to scrub.
- **No decoding on the render thread**: a pool for this kind of work.
- **Effects with a second image input**: the schema may change for it.
- **The backdrop in the look-back is a toggle.** The whole compositing
  order (look-back, backdrop, effects, the shape, masking, outputs)
  needs its own reconciliation session before it is settled; this plan
  takes a default and does not settle it.
- **Out for now**: per-face media (there are many faces; filling them
  needs a lot of media — later), the audio of videos, and old
  `view.bmp_*` presets (break or migrate, whichever helps).

## The words

| Word | Means | Not |
|---|---|---|
| **source** | anything that yields frames: a still, a video file, a camera, a Syphon or NDI sender, a phone | a "bitmap registry" — "registry" already means the param registry and the device registry |
| **media folder** | where file sources live: `<library>/media/` (shared) and `<home>/media/` (this Mac) | the preset *library* (`library.py`, plan 25) |
| **adapter** | the module that turns one kind of input into frames | |
| **channel** | one of eight slots `a`–`h` that holds a source choice; what consumers read | a wire: a wire is fixed in the graph, a channel's content changes live |
| **bin** | a channel's list of up to 16 sources it can switch between | |
| **consumer** | a graph node that reads a channel: the backdrop, the faces, an effect's input or aux, an output | |

## The shape in one paragraph

Adapters (`hyperspace/media/`, each imported lazily) turn inputs into
`MediaFrame`s — an RGBA picture, a time and a frame id, the
`devices.PointCloud` pattern — decoded **off the render thread** into a
one-slot "latest" holder. File sources come from the media folder,
scanned and watched by the pool; live sources are device-registry kinds
that discover their feeds (`camera:`, `syphon:`, `ndi:`, `phone:`). Each
of the eight **channels** holds a **bin** of up to 16 source ids and a
`media.<c>.slot` param picking one, so switching is a param: Learn, the
pad, the APC40, the sequencer, a macro and undo all switch it, and the
preset saves it. A video source on a channel has a **transport** —
`rate`, `pos` (scrub), `jog` (spin) and `loop` — also params. The
renderer uploads a channel only when a consumer reads it this frame and
its frame id moved. In the render graph a channel is a `media.<c>` node
with an `IMAGE` output, so it wires like anything else: under the scene
as the **backdrop**, onto the faces (replacing today's one bitmap),
into an effect's `image` input or its new **`aux`** input, or straight
into an output.

```
 adapters ──► sources ──────────► channels a–h ──► consumers (graph nodes)
 PIL/HEIF     shared:/local:/file:  bin[16] + slot   backdrop (under the scene)
 PyAV         camera:/syphon:       transport        faces (view.media)
 aiortc       ndi:/phone:           (rate pos jog)   effect image / aux
 syphon, NDI     ▲                                   output image
                 └── the media folder (watched) + live discovery
```

## What exists today (on the base)

- **One still, one slot.** `view.bmp_file` (`view.py:82`) is opened with
  PIL **on the render thread** (`Renderer._sync_bitmap`, `render.py:1062`)
  and drawn inside the face shader on unit 0 (`FACE_PX`), over the
  pattern, with alpha, scale and a path (`view.bmp_alpha/scale/mode/amp/rate`).
- **One picture for every face.** `_face_picture` makes one square
  picture (the seed + effects aimed at the faces) shown per face UV or
  in screen space (`u_pic_on`). Nothing gives faces different pictures.
- **Effects take one image** (`u_src`, `shaders/fx/_lib.glsl`);
  `graph.Effect.INPUTS = {"image": IMAGE}`.
- **The precedent**: `devices.CloudDevice` publishes `PointCloud`
  frames (frame id, read-only arrays) on the registry, and
  `graph.PointCloud` reads them, uploading only when the id moves.
- **One GL share group**: every output samples the renderer's textures
  (`outputs.py`), so a channel uploads once a frame for all windows.
- **Relative encoder and push**: the APC40's cue knob is relative
  (`apc40.CC_CUE`), and routing's `push` op adds to a base — a jog.

## Components

### M — sources and adapters (`hyperspace/media/`)

- `frame.py`: `MediaFrame` — `pixels` H×W×4 uint8, C-contiguous,
  read-only; `t` (publish time, the frame's monotonic clock); `frame`
  (id, counting up while the source is open); `size`. Frozen like
  `PointCloud`.
- `source.py`: the `Source` protocol — `id`, `kind`, `status`
  (`ready` / `fetching` / `missing` / `lost` / `error: …`), `latest()`
  → `MediaFrame | None`, `open()`, `close()`, `duration` and `seek()` for
  timed sources. `Latest`: a one-slot holder (a reference swap; a writer
  never waits on a reader, a reader never sees a torn frame; older
  frames are dropped, never queued).
- `pool.py`: one `ThreadPoolExecutor` (2–4 workers) for jobs that end —
  still decode, thumbnails, folder scans, proxy transcodes, a seek.
  Sources that block (a camera read, an NDI receive, a WebRTC track,
  a playing video's decode) run on **their own thread**, started on
  `open` and joined on `close`; they never use the pool (row 328). The
  render thread only uploads.
- Adapters, one module each, registered by kind (`adapters()` like
  `devices.kinds()`), each imported inside its `open`; importing `app`
  imports none (a boundary test, as `tests/test_app_boundary.py`):
  - `still.py` — PIL + `pillow-heif` (iPhone photos are HEIC): png,
    jpg, webp, bmp, tiff, heic. One frame, decoded on the pool.
  - `video.py` — PyAV (ffmpeg): mp4, mov, m4v, webm, mkv, animated GIF,
    HAP. Decoded on its own thread; the transport (below) drives it.
  - `camera.py` — AVFoundation through PyAV's `avfoundation` input.
  - `syphon.py` — `syphon-python`, client (and server: row 335).
  - `ndi.py` — `cyndilib`, receive (send later: row 335).
  - `phone/` — the phone stream (below).
- Size cap: frames are resized on the decoding thread to ≤ 1920×1080
  for files and ≤ 1280×720 for live feeds (row 329), keeping aspect.

### F — the media folder

- **Shared**: `<library>/media/` — the plan 25 cloud folder (Google
  Drive for desktop on both Macs). Ids `shared:<relative path>`.
- **This Mac**: `<home>/media/` (`~/Hyperspace/media/`), ids
  `local:<relative path>`; and any file anywhere, `file:<absolute path>`,
  with a **Copy to shared** button.
- **Watched**: the pool rescans both folders every 2 s (names, sizes,
  mtimes; subfolders are groups). A new file appears in the library
  without a relaunch; a removed one goes `missing`. A cloud
  placeholder (Drive streaming a file it has not downloaded) is
  `fetching` while the pool reads it, then `ready`. Cloud conflict
  copies are listed as files (plan 25 lists them for presets).
- **Thumbnails**: 160 px, made on the pool, cached in
  `<home>/media-cache/thumbs/` keyed by id + size + mtime.
- **Scrub proxies** (row 327): a video clip of ≤ 10 minutes gets an
  intra-frame proxy (MJPEG, ≤ 720p) in `<home>/media-cache/proxies/`,
  made on the pool the first time it is put in a bin; until it exists
  the original plays, forward only, scrubbing coarse (keyframe seeks).
  Proxies stay on the Mac, never in the shared folder.
- **Not this plan**: Google Photos and iCloud Photos. Since March 2025
  the Google Photos Library API reads only what the app itself
  uploaded, and the Picker API needs a person to pick each time — no
  "watch this album". iCloud Photos has no web API; on a Mac with
  iCloud Photos on, PhotoKit (PyObjC) can read an album of the local
  Photos library, which is a candidate adapter for later. Dropping
  files into the shared Drive folder covers the need now.

### L — live sources as devices

Each live kind is a device-registry kind (row 325) whose one entry
**discovers** feeds and publishes each as a source: `camera`
(`camera:<device name>`), `syphon` (`syphon:<app>/<server>`), `ndi`
(`ndi:<sender name>`), `phone` (`phone:<n>`, the n-th approved phone of
this run). An entry in `[[devices]]` turns a kind on (the factory
config: camera and syphon on; ndi on when `cyndilib` imports; phone
off). Each gets the registry's status line, its retry schedule and its
config watch for free. A feed that drops holds its last frame for 1 s,
then shows black, with the reason in its status; it comes back on its
own when the sender returns. macOS asks for camera permission on the
first `camera` open; a refusal is `error: camera permission` with the
System Settings path in words.

### P — the phone

- The app runs an HTTPS server on the rig (`aiohttp`, port 8443): one
  page (`media/phone/page.html`: front/back camera, a name, Send) and
  WebRTC signalling; the video comes in through `aiortc` (which
  decodes with PyAV), on the same Wi-Fi, host candidates only, no
  STUN or TURN.
- **A browser gives a page the camera only over HTTPS** (a "secure
  context"), on iOS Safari and Android Chrome alike — this is the hard
  part (row 333). Recommended: a hostname the owner controls
  (`cam.<domain>`) with a real Let's Encrypt certificate (DNS-01,
  renewed by `tools/phone_cert.py` while online), and our own router
  resolving that name to the rig's fixed LAN address (a local DNS entry
  — a travel router does this), so it works with no internet at the
  venue. A self-signed certificate makes every guest tap through a
  warning, and may still be refused the camera; a public tunnel needs
  the venue's internet.
- **Joining**: the QR code carries the URL and a per-rig join token
  (row 334) — so it can be printed and taped up; the media page also
  draws it. A phone that connects is **pending** until the operator
  approves it on the media page (its first frame shown); approved, it
  is `phone:<n>`; the operator can drop it at any time. At most 4
  phones, 720p30 each.
- **Zero-code fallback**: a phone running an NDI camera app is an
  `ndi:` source with no page at all.

### C — channels

- Eight channels, `a`–`h` (row 321). Each holds a **bin**: up to 16
  source ids (row 322), in the preset (row 323).
- Params per channel `c` (registry group `media`, all routable):
  - `media.<c>.slot` — discrete 0–15: which bin entry is on the
    channel. An empty entry, or a missing source, is black.
  - `media.<c>.fit` — cover / contain / stretch, into a consumer's
    frame.
  - `media.<c>.rate` — −4…+4 × native speed, default 1; 0 holds. On a
    live feed, 0 freezes the frame.
  - `media.<c>.pos` — 0–1, **the scrub** (row 326): while it moves —
    any performer, an LFO, the sequencer — the playhead is put there;
    when it rests, the playhead runs on at `rate` from where it was
    left. Harmor's playhead: grab it to scrub, let go and it plays.
  - `media.<c>.jog` — a `push` target, −1…+1: a relative encoder
    (the APC40's cue knob, a stick, a hand) adds playhead speed, which
    coasts back to `rate` (a `motion.py` spring), like a platter spun
    and let go.
  - `media.<c>.loop` — loop / ping-pong / once (holds the last frame).
- The playhead itself is a readout (the media page, GRAPH), never a
  param: a param that moved itself would fight its performers.
- A channel with no consumer this frame still plays (its clock runs)
  but is not uploaded.

### R — the render side

- **Textures**: a `MediaTextures` on the renderer: one texture per
  channel, (re)allocated when the frame size changes, written when a
  consumer reads the channel this frame and its frame id moved. Mipmaps
  for the faces' sampling.
- **`media.<c>` graph nodes** (kind `media`, `OUTPUT = IMAGE`): `image`
  is the channel's texture fitted (`media.<c>.fit`) to the frame size
  (one small pass into a pool texture, once a frame however many read
  it), which keeps the `IMAGE` port's contract ("a colour picture at
  the frame's size"). The faces read the raw texture, aspect preserved.
- **Backdrop** (kind `backdrop`, row 330): `backdrop.channel` (off /
  a–h), `backdrop.alpha`, `backdrop.history` (off by default). The scene
  is laid over the backdrop before the history and the effects, so
  effects bend both. With `backdrop.history` off the capture takes the
  scene alone and the echoes and the dream are drawn over the backdrop;
  on, the capture takes the composite. The hands-only pipeline has no
  backdrop. **This is a default, not the settled order**: the
  compositing reconciliation (below) may move it.
- **Faces** (row 331): `view.media` (off / a–h) replaces
  `view.bmp_file`; `view.bmp_alpha/scale/mode/amp/rate` become
  `view.media_alpha/…` with the same meaning. A preset that still has
  `view.bmp_*` loads with them dropped and a note naming the file it
  pointed at.
- **The `aux` input** (row 332): every effect gets an optional second
  image port, `aux` (`Effect.INPUTS = {"image": IMAGE, "aux": IMAGE}`);
  `_lib.glsl` declares `u_aux`, `u_aux_on`, `u_aux_size` and helpers
  (`aux(uv)`, `aux_luma(uv)`); unwired, `u_aux_on` is 0 and an effect
  that reads it gets transparent black. Two new effects use it:
  `displace` (the picture moved by the aux's luma or its red/green) and
  `blend` (aux over / multiply / screen / difference / luma key, with
  mix). Any `IMAGE` node may feed `aux`: a channel, the scene, the
  history.
- **Wires**: the preset's existing `graph` wire list names channels
  (`{"from": "media.a", "to": "acid.2.aux"}`, `{"from": "media.c",
  "to": "output.2.image"}`); refusals are notes, as plan 28 N4's are.

### U — the panel

- **MEDIA page** (replaces the bitmap page):
  - a banner at the top while the loaded preset names sources this Mac
    lacks: "this preset relies on `local:…`, `camera:…`, which are not
    on this Mac" — one line per source, and what shows instead (black);
  - the library: Shared / This Mac / Live, thumbnails, status
    (fetching, missing, error), search, **Add file…**, **Copy to
    shared**;
  - the eight channels as columns: the live picture, the bin (assign
    from the library), the slot, the transport (rate, a pos bar with
    the playhead, jog, loop), fit, status;
  - phones: the QR code, pending phones to approve, connected phones
    to drop;
  - the backdrop's and the faces' channel pickers.
- **GRAPH**: the channels as eight source nodes in a titled "media"
  area, the backdrop node, the `aux` ports.
- **No desk bindings** (row 339): the desk is Dylan's. Learn reaches
  every channel param; the media page suggests the cue knob for `jog`.

### S — the preset

- A `media` section: `{"channels": {"a": ["shared:loops/tunnel.mp4",
  "camera:FaceTime HD Camera", null, …], …}}` — the bins. The params
  (`media.*`, `backdrop.*`, `view.media*`) are values as ever.
- Saved as `hyperspace.preset/4` only when it has a `media` section or
  a `media.*` / `backdrop.*` / `view.media` value away from its
  default; every other preset unchanged byte for byte (row 337, plan
  31's conditional `/3` precedent).

## Not in this plan

- **Per-face media** (different sources on different faces): later;
  it needs a texture array and an assignment rule (all, alternate, by
  cell, by face-id hash, reshuffled on the beat), since face ids change
  with the shape.
- **The audio of a video.**
- **The compositing reconciliation** — the order and masking of the
  look-back, the backdrop, the effects, the shape, the hands and the
  outputs, worked through with the owner as its own plan (33). This
  plan's backdrop order and its `history` toggle are the stopgap.
- Google Photos, iCloud Photos (above); tempo-synced clip length (a
  clip spanning N bars); recording a channel to a file; NDI out (row
  335); desk defaults (row 339).

## Work packages

| WP | Size | What | Depends on |
|---|---|---|---|
| M0 | S | **Spike, throwaway**: phone camera over HTTPS on iOS Safari and Android Chrome through our own router (both certificate roads); `aiortc` receiving a phone's track; `syphon-python` in and out beside our GL context (copy cost at 1080p); `cyndilib` receive. Findings answer rows 333 and 335. | — |
| M1 | M | `media/`: `MediaFrame`, `Source`, `Latest`, `pool`, ids, adapter kinds, `still` (PIL + HEIF); boundary test | — |
| M2 | M | `video` (PyAV) on its own thread; `transport.py` (rate, the pos latch, jog coast, loop modes) on a fake clock; GIF; proxies | M1 |
| M3 | M | the media folder: scan + watch (shared, this Mac, `file:`), thumbnails, `fetching`, `missing` | M1 |
| M4 | M | channels: bins, `media.<c>.*` params, preset `media` section, conditional `/4`, undo | M1 |
| M5 | L | render: `MediaTextures` + upload rule, `media.<c>` nodes, backdrop + history toggle, faces moved to `view.media`, `aux` port + `_lib.glsl` + `displace` / `blend`, wires, new goldens | M2, M4 |
| M6 | M | live kinds on the device registry: `camera`, `syphon` in, `ndi` in; status lines; permission | M1, M0 |
| M7 | L | the phone: server, page, `aiortc`, approval, QR, `tools/phone_cert.py` | M1, M0 |
| M8 | S | Syphon out: an output published as a Syphon server (row 335) | M5, M0 |
| M9 | L | MEDIA page, GRAPH's media area | M3, M4 (library and channels), M5–M7 (the rest) |
| M10 | M | docs: this file as built, ARCHITECTURE, DECISIONS, register rows, hand checks group AA, ENGINEERING (both Macs on this build) | all |

M0, M1 start together; M2, M3, M4 run in parallel after M1; M6, M7, M8
in parallel after M5 (M6 and M7 need only M1 and M0 to start).

### Tests (headless, the headline ones)

- `MediaFrame` / `Latest`: read-only arrays, no torn frame under a
  writer thread, drop-not-queue.
- **The render thread never decodes**: a fake adapter that sleeps 200 ms
  per frame leaves the frame time untouched.
- Transport on a fake clock: rate ×2 and −1, the pos latch (moving pos
  scrubs, resting pos plays on), jog coast back to rate, loop / ping-pong
  / once, rate 0 freezes a live fake.
- Media folder on temp dirs: a dropped file appears within one scan, a
  removed one goes `missing`, a slow read is `fetching`, conflict
  copies listed, thumbnails keyed by mtime.
- Channels: slot switching, bins round-trip in the preset, `/4` only
  when used, an old `view.bmp_*` preset loads with the note, undo.
- Graph: `media.<c>` wired into a backdrop, an effect's `aux`, an
  output; refusals as notes; an unwired `aux` reads transparent black.
- Goldens: new fixtures (a still backdrop; `displace` and `blend` with a
  still aux; a channel into output 2) from a checked-in still and a
  tiny generated clip; **no existing golden moves** except any that
  draw today's bitmap (none known).
- Video: a clip generated by PyAV in the test, decoded and sought.
- Phone: signalling and approval against an `aiortc` loopback peer;
  the real phone is a hand check. Syphon / NDI: skipped unless the
  library imports; hand checks with Resolume and TouchDesigner.

## Risks

- **Phone TLS** is the riskiest piece and is why M0 runs first. If
  neither certificate road gets a guest's camera reliably, the NDI
  camera app is the fallback and the page waits.
- **Upload cost**: eight 1080p RGBA channels at 30 fps is ~2 GB/s of
  `texture.write`. The rule (consumed + new frame only) and the caps
  keep a normal show to two or three channels; M5 measures it on the
  SYSTEM page per channel.
- **The GIL**: PyAV and PIL release it while decoding; the resize and
  the colour conversion are numpy. M2 measures the frame time with
  three playing clips.
- **Syphon beside our context**: if `syphon-python` cannot hand us a
  texture in our share group, Syphon in is a CPU copy (M0 measures it).
- **Drive placeholders**: the first read of a streamed file can take
  seconds; it is a pool job and the source shows `fetching`, never a
  stall.
- **Numbering**: plan 31 takes preset `/3` and register rows 311–320 on
  its own branch; this plan assumes they land first (`/4`, rows 321+,
  checks from 296). If plan 31 does not land first, renumber at merge.
- **The moving base**: `plan-28-30-integration` may move again while
  its merge agent finishes; this branch takes it in.

## Decisions for the owner

Each has a recommendation (rec). Rows 321–339 of
[`DECISION-REGISTER.md`](../DECISION-REGISTER.md) once answered.

321. **Eight fixed channels, `a`–`h`**, params `media.<c>.*`. (rec) Or
     numbered 1–8, or a bank of N.
322. **A channel's choice is a bin of ≤ 16 sources plus a `slot`
     param.** (rec) Or a free-text source param per channel (not
     routable, not switchable from a controller).
323. **Bins live in the preset** — a look carries its media. (rec) Or
     in the project/session (the rig), shared by every preset.
324. **Source ids and places**: `shared:` (`<library>/media/`),
     `local:` (`<home>/media/`), `file:` (anywhere), and the live
     kinds; a missing source is black plus the banner. (rec)
325. **Live kinds are device-registry kinds that discover feeds.**
     (rec) Or one `[[devices]]` entry per feed (rig-stable names, more
     config).
326. **The transport: `pos` is a latch scrub, `rate` −4…+4 × native,
     `jog` a push with coast, `loop` three modes, rate 0 freezes a live
     feed.** (rec)
327. **Scrub proxies**: MJPEG ≤ 720p for clips ≤ 10 min, cached on
     the Mac. (rec) Or no proxies (scrubbing coarse, no reverse play
     on long-GOP files).
328. **Threads**: one pool for jobs that end, one thread per blocking
     source, the render thread only uploads. (rec)
329. **Caps**: 1920×1080 for files, 1280×720 for live; upload only a
     consumed channel with a new frame. (rec)
330. **Backdrop under the scene, before the history and the effects;
     `backdrop.history` off by default; plan 33 settles the order.**
     (rec)
331. **The faces read a channel (`view.media`); `view.bmp_*` removed,
     dropped on load with a note.** (rec) Or migrate them onto
     channel a.
332. **Every effect gets an optional `aux` image input; two new
     effects, `displace` and `blend`.** (rec)
333. **Phone TLS: the owner's hostname + a Let's Encrypt certificate +
     our router's local DNS entry**, confirmed by M0. (rec) Or
     self-signed, or a public tunnel. *Needs: a domain the owner
     controls, and the router.*
334. **Phone join: a per-rig token in a printable QR, operator approval
     per phone, at most 4, 720p30.** (rec) Or open (anyone on the
     Wi-Fi), or a token per run (no printed code).
335. **Out to Resolume / TouchDesigner: Syphon out in this plan, NDI
     out later.** (rec) Or both now, or neither (in only).
336. **Dependencies**: `av` and `pillow-heif` in the default install;
     `aiohttp` + `aiortc` + `segno` (QR), `syphon-python` and
     `cyndilib` as well, each imported only when its kind is on. (rec,
     the repo's precedent: torch is default and imported lazily) Or
     the live and phone ones as an optional extra.
337. **Conditional preset `/4`**, after plan 31's `/3`. (rec)
338. **Base `plan-28-30-integration`**, taking it in as it moves;
     to `main` once #224 and #195 land. (rec) Or wait for them to land.
339. **No desk or APC40 default bindings** (Dylan's); Learn for all.
     (rec)
