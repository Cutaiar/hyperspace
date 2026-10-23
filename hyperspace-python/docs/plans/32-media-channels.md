# Plan 32 — media: sources, the media folder, eight channels, and what reads them

**Status: built (2026-10-22)** on `plan-32-media` (base
`plan-28-30-integration` @ 1a5cc2e; 3105 tests passed, 2 skipped).
Designed with the owner in one session; rows 321–339 answered the same
day (below). **The phone's own page (HTTPS, WebRTC) is V2 and is not
built**; in V1 a phone joins through an NDI camera app, as an `ndi:`
source (`phone:` ids are parsed and never opened). **Resolume and
TouchDesigner both ways** is in V1 and built: their finished picture over
the network (NDI) or on this Mac (Syphon) on a channel, and any output
published back out over Syphon and NDI. The build plan was
[`32-media-build.md`](32-media-build.md).

Files, pictures and live feeds go onto **eight channels** (`a`–`h`), each a
bin of up to 16 source ids and a `media.<c>.slot` param; a video has a
transport (`rate`, `pos`, `jog`, `loop`). A channel is read by the
**backdrop** under the scene, by the **faces** (`view.media`, replacing
`view.bmp_*`), by an effect's new **`aux`** input (two effects use it,
`displace` and `blend`) and by an output. Sources are a still (PIL, HEIC),
a video (PyAV, with a scrub proxy), a camera, a Syphon server, an NDI
sender; the media folder is the shared `<library>/media/` plus this Mac's
`<home>/media/`, watched every 2 s. Nothing decodes, resizes, scans or
blocks on the frame thread. A **MEDIA** page replaces the bitmap page and
GRAPH has a media area. A preset that uses media is saved as
`hyperspace.preset/4` (**both Macs must run this build** to load one);
every other preset is the file it was, byte for byte except two effects'
default lines (rough edge 1). 40 new goldens (the 596 before are
unmoved: 636 in all). Four new dependencies (and one small one), each
imported only when a source opens.

Hand checks: [`11-hand-checks.md`](11-hand-checks.md) group AA, checks
296–316. **Numbering note:** plan 31 holds preset `/3`, register rows
311–320 and hand checks 280–295 on its own branch
(`plan-31-integration`); this branch has none of them, so rows 321–339
and checks 296+ leave a gap here that closes when plan 31 lands. The
preset schema is `/4` either way (row 337). Decisions: rows 321–339 of
[`DECISION-REGISTER.md`](../DECISION-REGISTER.md) and the "Media" section
of [`DECISIONS.md`](../DECISIONS.md). M0's findings:
[`assets/32-media/m0-findings.md`](assets/32-media/m0-findings.md).

Commits on `plan-32-media`, by task: T0 = M0, the Syphon/NDI spike
(ae64214); T1 = M1, the core and stills (997c736); T2 = the transport
(f6aada8, 46b701c, 4c4b5e7); T3 = video and proxies (4fb8fa4, 356dd63);
T4 = M3, the folder (b8964ee, 726de2c); T5 = M4, channels and the preset
(303e9a0, 2d65f22); T8 = M6, live sources (00a3847, ade60b9); T6 = M5's
render half (0e020b8, 603f76d, c0db276); T7 = faces, `aux`, `displace`,
`blend` (c9d28c4); T9 = M8, publishing (eafcaa2, f173984); T10 = M9, the
MEDIA page and GRAPH's media area (31730c6, 6125ab5); T11 = M10, this
documentation. (T8 was built before T6, so the render side could sample a
live frame.)

## What was built

### T0 — the spike (`assets/32-media/m0-findings.md`)

Throwaway, on the dev MacBook (M3 Max). It fixed T8 and T9's approach:
Syphon hands a texture across with no CPU copy both ways (publish
0.32 ms at 1080p); `cyndilib`'s macOS wheel carries the NDI runtime
(6.3.2.0), 1080p30 loopback received at 29.4 fps, about 15 ms old, about
35 % of a core for both ends; `Receiver.receive(timeout)` holds the GIL
for the whole timeout (so the build uses `rx.frame_sync.capture_video()`,
non-blocking, on the source's own thread); `Finder()` takes no
`extra_ips` (so the build writes NDI's own config file, below).

**Dependency ruling (T0/T1):** `syphon-python[opengl]>=0.2`, not plain
`syphon-python`: its OpenGL server and client raise `ImportError` without
PyOpenGL (already a dependency), which the extra names.

### T1 — the core and stills (`hyperspace/media/`)

- `frame.MediaFrame`: H×W×4 uint8, C-contiguous, read-only; `t`, `frame`
  (id), `size`. **Ruling:** it has a GPU variant — `pixels` is None when
  `texture` (a GL texture name in the renderer's share group), `tex_size`
  and `tex_target` are set; a source may expose `gl_poll()`, called only
  on the frame thread (Syphon's `textureName()` must run on the GL
  thread).
- `source.Source` protocol and `Latest` (a one-slot reference swap; drop,
  never queue). `ids` parses `shared:`, `local:`, `file:`, `camera:`,
  `syphon:`, `ndi:`; `phone:` is parsed and never opened. `pool`: one
  `ThreadPoolExecutor` (3 workers, `media-pool*`) for jobs that end.
  `adapters.open_source` imports each adapter inside the call; an
  unparseable or unsupported id is a `MissingSource` with an `error:`
  status, never an exception.
- `still`: PIL plus `pillow-heif` (png, jpg, webp, bmp, tiff, heic),
  decoded on the pool and capped to 1920×1080 (`CAP_FILE`); a huge image
  reads None until it is ready, so the frame thread never waits.
- `tests/test_app_boundary.py` now also asserts `import hyperspace.app`
  pulls in none of `av`, `pillow_heif`, `syphon`, `cyndilib`,
  `AVFoundation`.

### T2 — the transport (`media/transport.py`)

`Transport.step(dt, rate, pos, jog, loop)`. **Ruling:** the playhead speed
is `rate + coast`; only the jog's contribution springs (`motion.spring`,
2 Hz, critically damped, target 8 × jog), and a `rate` change acts at
once. The pos latch: while `pos` moves the playhead is put there; when it
rests the playhead runs on at `rate`. `loop`, `pingpong` (direction
resets on leaving it) and `once` (clamps at the end, a new scrub moves
it).

### T3 — video (`media/video.py`, `media/proxy.py`)

PyAV decoding on the source's own thread (`media-video-<name>`), driven by
the transport, `close()` returning within one frame decode. A clip of
≤ 600 s gets an MJPEG proxy (≤ 1280×720) in `<home>/media-cache/proxies/`
made on a single cancellable worker of its own (`media-proxy`, not the
pool: a transcode cannot be cancelled there); the original plays until it
exists, forward only, scrubbing by keyframe. `proxy.cancel_all()` runs at
app exit.

### T4 — the media folder (`media/folder.py`, `media/thumbs.py`)

`MediaFolder` scans `<library>/media/` and `<home>/media/` every 2 s on
the pool: a dropped file is listed within one scan, a removed one goes
`missing`, a cloud placeholder (dataless, or an iCloud `.icloud` file) is
`fetching`, a slow or unreadable file is `error: …` or `fetching` and
never stops the scan (each probe is a 64 KiB read on a daemon thread
waited for 0.5 s). `file:` ids are listed as group `added`.
`path`/`status`/`thumb`/`add_file` never touch the disk (an unseen id is
`missing` and queues a scan). `copy_to_shared` returns a Future of the new
`shared:` id (copied as `.part`, then renamed). Thumbnails: 160 px,
`<home>/media-cache/thumbs/`, keyed by id + size + mtime.

### T5 — channels, params, the preset (`media/channels.py`, `params.py`, `preset.py`)

- `MediaState`: the eight `Channel`s, each a bin and a source opened when
  the id at `round(slot)` changes; every 1 s a channel asks the resolver
  again (a file that arrived opens, one that went turns black and reads
  `missing`, a replaced one — a new mtime/size — reopens). **Ruling:** a
  dropped source is closed on a thread of its own (`Closer`, one daemon
  thread, `media-closer`), never on the frame thread — a video's close
  joins a thread that can sit in `av.open` while a cloud file downloads;
  `close()` shares one 1.5 s budget so app exit joins everything within
  2 s.
- Params: 48 `media.<c>.slot/fit/rate/pos/jog/loop`, `backdrop.channel /
  alpha / history`, `view.media` and `view.media_alpha/scale/mode/amp/
  rate`. `view.bmp_*` are gone. **Ruling:** the APC40's factory knob 7
  row (`cc:0:54 → view.bmp_alpha`) is kept by registering `view.bmp_alpha`
  as a hidden alias of `view.media_alpha` (`alias=True`: not saved, not
  modulatable, not in a snapshot) — `apc40.py` and the factory files
  untouched.
- The `media` section and the conditional `/4` (row 337, below). A
  non-empty `view.bmp_file` in an old preset is dropped with the note
  `bitmap file <path> is no longer read: put it on a media channel`.
  `Marks` carries the bins, so an undo of a load puts them back.
- `app.py`: `MediaResolver` (folder paths, `live` ids, a change stamp, the
  proxy cache), `MediaIO` polled right after the devices each frame and
  closed first on both exits. `Host.adapters` is `(media, devices,
  dream_io)`.

### T8 — live sources (`media/live.py`, `ndi.py`, `syphon.py`, `camera.py`)

- Each live kind is a device-registry kind (`ndi`, `syphon`, `camera`) on
  `LiveKind(devices.Base)`; **Ruling:** its source map is
  `media_sources() -> dict[str, LiveSource]` (`Base.feeds` is already the
  tuple of fed Router schemes). `DeviceRegistry.media_feeds()` merges the
  open devices' maps, the first device to find an id keeping it.
  Discovery (`discover()`) runs on the pool every 2 s (Syphon on its own
  thread: its directory scan spins a run loop).
- `LiveSource` runs a reader on a thread of its own (`media-live-<id>`),
  caps to 1280×720, holds the last frame 1.0 s and then reads None
  (`lost`); a reader that raises is `error: …` and is opened again after
  2 s; one object is shared by every channel holding it (holders are
  counted; a feed nobody holds for 5 s is let go). A channel whose device
  is remade by a `config.toml` edit follows it.
- NDI in: `Finder` kept open with its change callback; frames by
  `frame_sync.capture_video()` in `RGBX_RGBA`; ids `ndi:<stream>` from
  `HOST (stream)` (`ndi:HOST (stream)` when two hosts send one name).
  **Ruling:** `extra_ips` is written to an app-owned
  `<home>/ndi/ndi-config.v1.json` with `NDI_CONFIG_DIR` set before
  `cyndilib` is first imported; the status says `extra_ips via NDI config
  (unverified)`.
- Syphon in: ids `syphon:<app>/<server>`; `SyphonSource.gl_poll` makes the
  client on the frame thread and returns the client's texture. Syphon
  discovery needs the main thread's run loop pumped (`glfw.poll_events()`
  every frame, which the app does); the scan thread only reads the list.
- Camera: the AVFoundation device list by name, permission checked (`error:
  camera permission (System Settings ▸ Privacy & Security ▸ Camera)`),
  opened through PyAV's `avfoundation` input at 1280×720, 30 fps — run on
  the real FaceTime camera: 30.5 fps. The device raises `BlockingIOError`
  between frames, which kills PyAV's demux generator, so the reader makes
  a new one each time.
- The factory `config.toml` template lists all three kinds (commented
  `[[devices]]` entries, `enabled = true`).

### T6 — textures, the media node, the backdrop (`media_tex.py`, `graph.py`, `render.py`)

- `MediaTextures`: one texture per channel, (re)allocated on a size change,
  written and mip-mapped only when a consumer reads the channel and its
  `(frame, t)` moved. **Ruling (corrected by the build):** Syphon client
  textures are `GL_TEXTURE_RECTANGLE`, not 2D as T0's note assumed; a
  rectangle frame (`MediaFrame.tex_target`) is blitted on the GPU into the
  channel's own 2D texture (PyOpenGL, imported only for such a frame); a 2D
  GPU frame is wrapped with `ctx.external_texture`.
- `graph.MediaNode` (`media.<c>`, kind `media`, `OUTPUT = IMAGE`): the
  channel fitted (`media.<c>.fit`) into one pool texture, once a frame
  however many read it. `media.a`…`media.h` are wire ends.
- The backdrop: with `backdrop.channel` set the scene clears to alpha 0
  and `grounded = Composite(over=scene, under=media.<c>)` feeds the
  history; the capture reads `grounded` when `backdrop.history` is on,
  else the scene. The hands-only pipeline has none. An effect placed
  `after scene` is retargeted to `grounded`, so it bends both. Without a
  backdrop the graph is unchanged node for node. SYSTEM times `media.<c>`
  and `grounded`.
- Goldens: `backdrop-still` and `media-to-output-2`, 16 frames, from a
  checked-in 256×144 still (`tests/golden/media/backdrop-still.png`);
  `tools/golden_frames.py` runs a real `MediaState` over a `GoldenMedia`
  resolver.

### T7 — faces, `aux`, `displace`, `blend` (`render.py`, `fx.py`, `graph.py`, `shaders/fx/`)

- The faces read the raw texture of the channel `view.media` names
  (`_face_media`); `u_bmp_flip` draws a Syphon/GPU frame upright. Placement
  (`media_scale`, `media_mode/amp/rate`) is the old bitmap's maths.
- Every effect has an optional `aux` image port
  (`Effect.INPUTS = {"image", "aux"}`); `_lib.glsl` declares `u_aux`,
  `u_aux_on`, `u_aux_size`, `aux(uv)` and `aux_luma(uv)`; unwired, `aux()`
  is transparent black. An `aux` wire is never a placement; one that
  would make a loop, or whose source is missing, is dormant with the
  reason in words. `Graph.pool` counts one more texture per wired aux.
- `displace` (the picture moved by the aux's luma or its red/green; amount,
  mode, angle) and `blend` (over / multiply / screen / difference / luma
  key; key, soft; the mix fader is the amount). No factory preset turns
  either on.
- Goldens: `faces-media`, `blend-luma-key`, `displace-luma`, 24 frames, all
  from `local:backdrop-still.png`. With T6's 16: 40 new goldens, 636 in
  all; `tools/golden_frames.py` reports "all 636 frames match their
  goldens" and the 596 before are byte-for-byte unmoved. The seven face
  tests the T5 interim skipped run again.

### T9 — publishing out (`media/publish.py`, `outputs.py`, `render.py`, `config.py`)

- `[output]` and each `[[output.screens]]` entry take `syphon = "<name>"`,
  `ndi = "<name>"` and `window = false` (publish-only). Output 1 always
  opens a window (it holds the GL context and paces the loop): `window =
  false` there is a note.
- Syphon out: the server is made once with the render context current and
  `publish_frame_texture(tex.glo)` runs on the frame thread, no readback
  (0 ms in the smoke run). NDI out: two pixel-pack buffers in turn, the
  buffer filled a frame ago copied to a staging array only when the sender
  is idle (else the frame is dropped, never queued); the send runs on
  `media-ndi-out-<name>`, unclocked (the render loop is the clock). Smoke
  run of the real app, 180 frames, a publish-only output 2: `syphon out
  hs-smoke — 60 fps, readback 0.0 ms`, `ndi out hs-smoke — 60 fps,
  readback 4.1 ms`, closed in 0.002 s.
- A window publishes at the render cap (a tap is resolved or presented
  into an `Offscreen` at `capped(size, max_frame)`, so a retina window is
  not a 4K stream); a publish-only output draws offscreen at the cap
  (`full` = output 1's framebuffer size). A publisher that raises costs
  nothing else: the error is its SYSTEM line (`stats["publish_errors"]`)
  and its fps decays to 0 after a second without a send.
- **Ruling:** publishers are SYSTEM lines (`<kind> out <name> — <fps> fps,
  readback <ms> ms`), not device-registry sink entries as the design's
  "O" had it. A registry sink with an empty `send()` adds nothing a
  performer can use.

### T10 — the MEDIA page and GRAPH's media area (`ui_media.py`, `graphview.py`)

- `ui.PAGES`: the bitmap page becomes `media`. A banner while
  `MediaState.missing()` is non-empty ("`<id>` — not on this Mac: shows
  black", three lines, then "and n more"); the library (Shared / This Mac
  / Live, thumbnails, status words, search, **Add file…**, **Copy to
  shared**); the eight channels as columns (picture with a status outline,
  a "B"/"F" tag for the backdrop's and faces' channel, playhead bar, the
  bin as two columns of eight); the backdrop's and faces' pickers.
  **Ruling:** the transport (rate, jog, position, loop, slot, fit) is
  drawn full size for the selected channel (click a column's letter), not
  in each of the eight ~45 px columns — the panel's rule is legibility at
  a distance (PR #24). They are the panel's own widgets, so Learn, the
  context menu and undo work. The page suggests Learning the cue knob to
  `media.<c>.jog`; no binding is made (row 339).
- Clicking a bin cell with a library pick assigns it; with none it cues
  that slot (writes `media.<c>.slot`); right-click empties it. A bin edit
  is an undo step (`undo.push(label, load=True)`).
- The page never opens or reads a source: the live picture is the
  renderer's (`renderer.media_watch`, drawn from `Renderer.media_shown`),
  thumbnails are decoded once on the pool and uploaded in the renderer's
  frame (`UiTextures`, LRU 256), and the library list draws only the rows
  in view (an imgui clipper), so a big library costs what is visible.
- GRAPH: a new MEDIA area between MODULATION and GEOMETRY: eight
  `render:media.<c>` nodes (a channel with an empty bin and no cable sits
  on the area's idle line, "8 empty channels"), the backdrop's node always
  drawn, the `aux` ports from `Effect.INPUTS`. A channel that is both the
  backdrop and a wire's start is one node with two cables.

## What no person has verified

Every test is headless. The hand checks (group AA) are for what only a
person at the machine can judge:

- **Resolume and TouchDesigner, both ways**, and **NDI over the
  network from a second Mac**: the loopback tests run our sender into our
  receiver in one process; no third-party app has seen a frame of ours or
  sent one to us (checks 304–309);
- **`extra_ips`** through the app's own NDI config file: loopback cannot
  show it, nothing has tested a sender on another subnet, and the NDI
  runtime reading a config file from `NDI_CONFIG_DIR` is the spike's
  expectation from the SDK docs, not something seen (check 307);
- **an NDI camera app on a phone** (the V1 phone), never tried with a real
  phone (check 312);
- **the look**: a backdrop under the scene with the look-back on and off,
  cut-through with a backdrop (never eyeballed), the faces' picture
  through the face patterns, `displace` and `blend` at distance — the
  goldens were checked by eye on one still (checks 296, 297);
- **the feel** of scrub, jog and the cue knob on the encoder (checks 298, 299);
- **the cloud**: a Drive placeholder going `fetching` then `ready`, a file
  dropped into the shared folder from the other Mac, the missing-local
  banner on the other Mac (checks 300–302);
- **a webcam and the macOS permission prompt** (the FaceTime camera ran
  once, at 30.5 fps, from a script; check 311);
- **frame cost**: three playing clips, eight channels, NDI out's ~4 ms of
  frame time at 1080p, the MEDIA page open with a big library — measured
  on the dev machine's smoke runs only, never in a show;
- **a publish-only output on the rig**, and output 1's published picture
  after a resize or DPI change (T9 could not check it; check 310);
- **the MEDIA page at distance**: whether eight 45 px columns plus a
  full-size transport for the selected channel reads from arm's length
  (check 303).

## Known rough edges

Deferred by the reviews (each task's reviewer judged them minor):

1. **Every saved preset gains `fx.displace.*` and `fx.blend.*` value lines.**
   Adding two effect files adds their params to every file the writer
   emits, so "byte-for-byte what the base writes" is true of everything
   but those lines (a preset without media loads in this build exactly as
   before; the base build loads such a file with a note per unknown id and
   lands the rest, as plan 30's palette addition did). The test
   `test_preset_without_media_is_unchanged` ignores those lines. A writer
   that skipped an off effect's default values would remove the gap.
2. **A still's late decode.** `still.close()` only cancels the future; a
   decode already running still publishes after close (harmless: a closed
   source is dropped and never read again). `open()` twice submits two
   decodes. The decode is full-resolution RGBA before the cap (about
   190 MB transient at 8000×6000; PIL's `draft()` would cut it).
3. **`MediaFrame` freezes only a view** of a writable caller array; the
   caller can still mutate it.
4. **`media.pool` reloaded** orphans the live executor (threads idle,
   harmless); `media` modules are first in hotreload's order.
5. **Video:** the proxy retimes VFR clips and GIFs (pts = frame number); a
   failed proxy retries at every open; a mid-stream decode error ends the
   thread for good; `VIDEO_EXT` is duplicated in `adapters.py`;
   `cancel_all` leaves queued-job flags (matters only if the app ran on);
   one `container.seek` is not interruptible; the backward-seek tolerance
   is loose. `once` clamps at the end and never re-arms (a new scrub moves
   it).
6. **Folder:** a new unreadable path costs a scan up to 0.5 s once
   (serial); wake threads for dataless cloud files are not capped
   (thousands of iCloud placeholders would be thousands of threads);
   `_watch` sets `_scan_job` outside its lock (worst case two queued
   scans). T4's tests were written after its code (no RED run).
7. **Closer:** it is serial — one close hung forever blocks later closes
   for the run (sources leak; the frame thread is unaffected).
8. **Live:** `LiveKind.close` joins threads and closes the finder on the
   frame thread during a config edit (about 1 s at worst, usually tens of
   ms); the Syphon release (`client.stop()`) runs inline on the frame
   thread in the kind's poll, with whatever GL context is current;
   Syphon textures arrive at the server's size, uncapped; if
   `LiveSource.open()` ever raised, the `MissingSource` would be retried
   every 1 s; the camera kind lists every AVFoundation video device
   (Continuity Camera included).
9. **Render:** with the backdrop on and `backdrop.history` off, echoes are
   not bent by an effect placed after the scene (the capture reads the
   unbent scene); a `grounded` composite failure is reported as a hands
   error (Composite's catch-all); an aux from an in-run effect reads the
   scene pipeline's node in every pipeline, and a partial loop applies the
   wire to some pipelines while reported dormant; `Graph.pool` over-counts
   one texture when the aux source has one; no graph test of an aux into a
   D1-placed effect or of `u_bmp_flip` with a live texture; `displace` and
   `blend` are in decision 24's `EFFECTS_IN_NO_PRESET` (no factory preset
   uses them); the Syphon test's context restore is skipped if its own
   setup fails before its `try`.
10. **Publishing:** NDI out's ~4 ms on the frame thread is an 8 MB copy out
    of a finished buffer (avoidable by copying on the sender thread or
    flipping on the GPU); the NDI sender is unclocked; `_said` grows per
    distinct error text; the windowed tap's presenter is never released
    with the renderer; output 1 cannot be publish-only; a change of
    `extra_ips` after `cyndilib` was imported (by NDI out, say) needs a
    restart.
11. **Panel:** the media and backdrop groups are left out of the presets
    page's module overview; unused empty channels sit on GRAPH's idle line;
    with four thumbnail decodes in flight other visible rows show a dark
    box briefly.
12. **Frozen Syphon, camera mode, coverage, cost.** (a) A rate-0 Syphon
    channel holds a frame whose texture is Syphon's own IOSurface-backed
    one, which the server keeps writing: "freeze" probably keeps animating
    (or samples a recycled name once the client's image is replaced); a
    true freeze needs a GPU copy (check 315). NDI and camera freezes hold a
    CPU frame and are exact. (b) The camera's `video_size` is fixed at
    1280×720: a device without that mode (a capture card, Continuity
    Camera) makes `av.open` raise every 2 s, shown as `error: …` that does
    not say "mode not supported" (check 316). (c) Some live logic is
    covered only by the real loopbacks: Syphon's uuid change, failed-client
    retry and hold-then-black; the camera's EAGAIN regenerate path (no
    fake-`av` test); NDI's stride and RGBX-to-opaque handling; graphview's
    `startswith("connected")`. (d) `DeviceRegistry.media_feeds()` builds a
    merged dict per call and `MediaResolver.live` calls it per id (the MEDIA
    page every frame, each channel's 1 s recheck): cheap at today's counts,
    tidier cached per scan.
13. **The phone** is V2 and `phone:` ids are never listed in
    `missing()`.

## The design, as agreed (2026-10-22), corrected where the build differs

What the build changed from the design below:

- **Publishers are SYSTEM lines, not device-registry sinks** (section O).
- **Syphon in is a `GL_TEXTURE_RECTANGLE`**, copied on the GPU into the
  channel's 2D texture, not a plain 2D texture (sections R and L).
- **A frame may be a GPU texture** (`MediaFrame.texture`), not only a numpy
  picture (section M).
- **`extra_ips`** goes through an app-owned NDI config file (section L).
- **The transport is full-size for the selected channel** on the MEDIA page
  (section U).
- **Scrub proxies** are made on a worker of their own, ≤ 600 s, MJPEG
  ≤ 1280×720 (section F; the design said the pool and ≤ 720p).
- **`view.bmp_alpha` survives as a hidden alias** of `view.media_alpha`
  (section R's faces paragraph).
- **A publish-only output 1 is refused** (section O).
- **The compositing reconciliation (plan 33) is not done**; the backdrop's
  place is the default the design names.

The rest is as written.

## What the owner wants (2026-10-22)

- **Use pictures and video in a more fun way**: stills and videos under
  the geometry, through the shaders, on the faces.
- **A media library**: the pictures and videos you care about, easy to
  reason about and swap between. Ideally the **shared cloud folder**,
  responsive when a file is dropped in, plus sources local to one Mac.
  A preset that names a local source another Mac lacks is fine: a clear
  banner on the media page says so.
- **Live feeds**: anything giving frames at a resolution and rate — a
  local webcam, **Syphon** and **NDI**, and **a phone streaming into the
  show after scanning a QR code** (bringing our own router is
  acceptable; the phone's own page is V2, an NDI camera app the V1 road).
- **Resolume and TouchDesigner, both ways — in first** (2026-10-22): "we
  keep running into people with really cool Resolume/TouchDesigner
  setups": take their finished picture, possibly over the network, pipe
  it through ours — and send ours to them.
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
that discover their feeds (`camera:`, `syphon:`, `ndi:`; `phone:` in V2). Each
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
 syphon, NDI  ndi:                  (rate pos jog)   effect image / aux
 (in and out)    ▲                                   output image ──► Syphon / NDI out
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
  - `syphon.py` — `syphon-python`: client (in) and server (out).
  - `ndi.py` — `cyndilib`: receive (in) and send (out).
  - `phone/` — V2 (below).
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
this run; V2). An entry in `[[devices]]` turns a kind on (the factory
config: camera, syphon and ndi on, each only if its library imports).
**NDI is the headline** (the other rig's picture over the network): it
finds senders by mDNS on the router; an `ndi` entry may list
`extra_ips` (NDI's own "extra IPs" for finding) where a network blocks
mDNS, so a sender on another subnet is found by address. Each gets the registry's status line, its retry schedule and its
config watch for free. A feed that drops holds its last frame for 1 s,
then shows black, with the reason in its status; it comes back on its
own when the sender returns. macOS asks for camera permission on the
first `camera` open; a refusal is `error: camera permission` with the
System Settings path in words.

### P — the phone (V2: not this sprint)

**V1:** a phone running an NDI camera app is an `ndi:` source; nothing
else is built for phones. Checking that with a real phone and app is a
hand check after this sprint (owner, 2026-10-22). The design below is
kept for V2.

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

### O — out to Resolume and TouchDesigner

- An **output** can also be published: `[[output.screens]]` (and `[output]`) gains `syphon =
  "<server name>"` and `ndi = "<sender name>"` (either, both or neither),
  and a publish-only output (no window) is allowed, so the rig can send
  a picture it does not show. Syphon out hands the output's frame
  texture to a Syphon server in our share group (no copy, if M0 shows
  it can); NDI out reads it back asynchronously (two pixel-pack
  buffers, a frame behind) and sends it on the NDI sender's own
  thread, so the render thread never waits on the network.
- Each published output is a SYSTEM line (sender name, fps, readback
  ms) and a sink on the device registry's list. *(Corrected by the build:
  publishers are SYSTEM lines only, not registry sinks — see T9's ruling
  and row 335.)*

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
  - (V2: phones — the QR code, pending phones to approve, connected
    phones to drop);
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
- **The phone's own page** (HTTPS, WebRTC, the QR join): V2.
  Checking an NDI camera app with a real phone: after this sprint.
- Google Photos, iCloud Photos (above); tempo-synced clip length (a
  clip spanning N bars); recording a channel to a file; desk defaults
  (row 339).

## Work packages

| WP | Size | What | Depends on |
|---|---|---|---|
| M0 | S | **Spike, throwaway**: `syphon-python` in and out beside our GL context (a texture in our share group, or the copy cost at 1080p); `cyndilib` send → receive on loopback at 1080p (fps, latency, CPU). Findings fix M6 and M8's approach. | — |
| M1 | M | `media/`: `MediaFrame`, `Source`, `Latest`, `pool`, ids, adapter kinds, `still` (PIL + HEIF); boundary test | — |
| M2 | M | `video` (PyAV) on its own thread; `transport.py` (rate, the pos latch, jog coast, loop modes) on a fake clock; GIF; proxies | M1 |
| M3 | M | the media folder: scan + watch (shared, this Mac, `file:`), thumbnails, `fetching`, `missing` | M1 |
| M4 | M | channels: bins, `media.<c>.*` params, preset `media` section, conditional `/4`, undo | M1 |
| M5 | L | render: `MediaTextures` + upload rule, `media.<c>` nodes, backdrop + history toggle, faces moved to `view.media`, `aux` port + `_lib.glsl` + `displace` / `blend`, wires, new goldens | M2, M4 |
| M6 | M | live kinds on the device registry: **`ndi` in first** (with `extra_ips`), `syphon` in, `camera`; status lines; permission | M1, M0 |
| M7 | — | the phone: **V2, not this sprint** | — |
| M8 | M | out: an output published as a Syphon server and/or an NDI sender, publish-only outputs, async readback (row 335) | M5, M0 |
| M9 | L | MEDIA page, GRAPH's media area | M3, M4 (library and channels), M5, M6 (the rest) |
| M10 | M | docs: this file as built, ARCHITECTURE, DECISIONS, register rows, hand checks group AA, ENGINEERING (both Macs on this build) | all |

M0, M1 start together; M2, M3, M4 run in parallel after M1; M6 needs
only M1 and M0; M8 needs M5.

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
- Syphon / NDI: loopback tests (our sender → our receiver) when the
  library imports, skipped otherwise; hand checks with Resolume and
  TouchDesigner both ways, and over the network from a second Mac.

## Risks

- **NDI's runtime**: `cyndilib`'s wheels are expected to carry the NDI
  library (M0 confirms); where one does not, NDI is off with its status saying what to install.
  NDI over a busy venue Wi-Fi is bandwidth-hungry (full NDI ~100 Mb/s
  at 1080p; NDI|HX far less): the own-router caveat applies.
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

## Decisions — answered by the owner 2026-10-22

Rows 321–339 of [`DECISION-REGISTER.md`](../DECISION-REGISTER.md), each
with what was built, the other options, how to reverse it, its rough edge
and the check that judges it. "(rec)" is the recommendation accepted;
rows the owner did not speak to were accepted as recommended with the
instruction to execute.

321. **Eight fixed channels, `a`–`h`**, params `media.<c>.*`. (rec) —
     built as written.
322. **A channel's choice is a bin of ≤ 16 sources plus a `slot`
     param.** (rec) — built; bin edits on the MEDIA page are undo steps.
323. **Bins live in the preset.** (rec) — "source lists in the preset
     are fine". Built.
324. **Source ids and places**: `shared:`, `local:`, `file:`, the live
     kinds; a missing source is black plus the banner. (rec) — built.
325. **Live kinds are device-registry kinds that discover feeds.** (rec) —
     built; the map is `media_sources()`, not `feeds()`.
326. **The transport: `pos` latch scrub, `rate` −4…+4 × native, `jog`
     a push with coast, `loop` three modes, rate 0 freezes a live
     feed.** (rec) — built (a Syphon channel's freeze is not exact, rough edge 12); only the jog's part of the speed springs.
327. **Scrub proxies for clips ≤ 10 min.** (rec) — "I can't imagine
     we'd have longer clips than that". Built on a worker of its own.
328. **Threads**: a pool for jobs that end, a thread per blocking
     source, the render thread only uploads. (rec) — built; dropped
     sources close on a closer thread.
329. **Caps** 1080p files / 720p live; upload only consumed channels
     with a new frame. (rec) — built; Syphon textures uncapped.
330. **Backdrop under the scene, before the history and the effects;
     `backdrop.history` off by default; plan 33 settles the order.**
     (rec) — "stopgap is fine". Built.
331. **Faces read a channel (`view.media`); `view.bmp_*` dropped on
     load with a note.** (rec) — built; `view.bmp_alpha` kept as a
     hidden alias for the APC40's knob 7.
332. **Every effect gets an optional `aux` input; `displace` and
     `blend`.** (rec) — built.
333. **The phone's own HTTPS page is V2.** V1 leaves the door open for
     an NDI camera app (an `ndi:` source); its check with a real phone
     comes after this sprint. (owner) — as decided; nothing built.
334. **Phone join (V2): a per-rig token in the QR, at most 4, each
     approved on the host.** (rec) — V2, not built.
335. **Resolume / TouchDesigner both ways in V1, in first**: NDI in
     (over the network, `extra_ips`) and Syphon in, then Syphon out and
     NDI out from any output, publish-only outputs allowed. (owner) —
     built; publishers are SYSTEM lines, output 1 cannot be
     publish-only, `extra_ips` unverified.
336. **Dependencies**: `av`, `pillow-heif`, `syphon-python`,
     `cyndilib` in the default install, each imported only when used;
     the phone's (`aiohttp`, `aiortc`, `segno`) come with V2. (rec) —
     built, plus `pyobjc-framework-avfoundation` (macOS) for the
     camera list.
337. **Conditional preset `/4`**, after plan 31's `/3`. (rec) — built;
     both Macs must run this build.
338. **Base `plan-28-30-integration`**, taking it in as it moves. (rec) —
     @ 1a5cc2e; nothing was taken in.
339. **No desk or APC40 default bindings**; Learn for all. (rec) — built;
     `apc40.py` and `midi.py` untouched.
