# Plan 32 M0 findings: Syphon and NDI beside our GL

Throwaway spike, run 2026-10-22 on the dev MacBook (Apple M3 Max, macOS Darwin 25.6, Python 3.14, moderngl context
from a hidden GLFW window, GL 4.1 Metal). Libraries were installed only into a scratch `uv run --with` environment; no
project dependency changed. Feeds T8 (live sources in) and T9 (outputs published out).

Summary:

| Question | Answer |
|---|---|
| Syphon: publish a moderngl texture with no CPU copy | **Yes**, `publish_frame_texture(tex.glo, size=(W, H))`, 0.32 ms mean at 1080p |
| Syphon: received frame is a GL texture, not numpy | **Yes**, `client.new_frame_image.textureName()` is a GL texture name in our context |
| NDI runtime bundled in the wheel | **Yes**, `libndi.dylib` (NDI SDK 6.3.2.0) ships inside the `cyndilib` macOS wheel |
| NDI loopback 1920x1080 BGRA 30 fps, 10 s | **29.4 fps** received, ~15 ms age, ~35 % of one core for sender and receiver together |
| `extra_ips` on the finder | **Not exposed** by cyndilib 0.1.3 (hard-coded NULL); use the NDI config file (below) |

## 1. Syphon (`syphon-python` 0.2.0)

Install: `syphon-python[opengl]==0.2.0`. The plain package does not carry PyOpenGL and `SyphonOpenGLServer.__init__`
raises `ImportError: OpenGL support requires PyOpenGL. Install it with: pip install 'syphon-python[opengl]'` without it.
It pulls `pyobjc-core`, `pyobjc-framework-Cocoa`, `pyobjc-framework-Metal`, `numpy`; the Syphon framework itself is
bundled in the wheel. `SyphonOpenGLServer`, `SyphonOpenGLClient`, `SyphonMetalServer`, `SyphonMetalClient` and
`SyphonServerDirectory` all exist, so no Metal fallback is needed.

API calls that worked, in one process, with our moderngl context current on the calling thread:

```python
import syphon
tex = ctx.texture((1920, 1080), 4); fbo = ctx.framebuffer([tex])
srv = syphon.SyphonOpenGLServer("name")          # uses the current NSOpenGLContext/CGL context
srv.publish_frame_texture(tex.glo, size=(1920, 1080))   # texture id handoff, no CPU copy
d = syphon.SyphonServerDirectory()
d.servers_matching_name(name="name")             # list[SyphonServerDescription]; also app_name=
cl = syphon.SyphonOpenGLClient(desc)             # cgl context defaults to the current one
img = cl.new_frame_image                         # SyphonIOSurfaceImageCore or None (consumes the new-frame flag)
ext = ctx.external_texture(img.textureName(), (w, h), 4, 0, "f1")   # wrap as a moderngl texture
cl.stop(); srv.stop()
```

Numbers (1920x1080, 120 and 60 frame loops):

- Publish only (`publish_frame_texture`): 0.32 ms mean, 0.44 ms max.
- Publish plus directory run-loop pump (5 ms interval) plus `new_frame_image`: 4.8 ms mean (dominated by the 5 ms pump).
  119 of 120 frames were delivered.
- `ext.read()` of the received 8,294,400 bytes (test only, not a production step): 3.6 to 6.7 ms. Pixel check
  after clearing to red: received `[255, 0, 0, 0]`, correct.
- The received texture name was different from the one published (3 vs 1): it is Syphon's own IOSurface-backed
  texture, bound in our context. No numpy hop is needed; sample it directly in a shader.

Things T8/T9 must handle:

- `SyphonServerDirectory.servers` and `servers_matching_name` call `update_run_loop()`, which spins the CFRunLoop for
  `run_loop_interval` (default **1.0 s**) per call. It must not run on the frame thread. Poll the directory on the
  source's own scan thread (T8). Discovery of a freshly created server took under 1 s.
- `new_frame_image` and `textureName()` must run on the thread that owns the GL context (the frame thread);
  the client's new-frame callback runs on a Syphon background thread and must only set a flag (docstring: "short,
  synchronous, no UI/OpenGL work"). Keep the returned image object alive while its texture is sampled.
- The server and client are created with our GL context current (they take it from `NSOpenGLContext.currentContext()`),
  and drawing/bind calls need exclusive use of the CGL context. `bind_to_draw_frame(size)` /
  `unbind_and_publish()` exist as an alternative (draw straight into Syphon's framebuffer); the texture path above is
  simpler for T9 because the app already renders to a texture.
- Id mapping: `syphon:<app>/<server>` maps to `description.app_name` / `description.name`; `description.uuid` is the
  unique key. A client can only be built from a description object.
- The texture target of the received image was not separately probed (a 2D `external_texture` read gave correct
  pixels). If a viewer app publishes a rectangle texture, T8 should check the target before choosing a sampler.

## 2. NDI (`cyndilib` 0.1.3)

Install: `cyndilib==0.1.3` (11.5 MiB wheel for cp314 macOS arm64). It **carries the NDI runtime**:
`cyndilib/.dylibs/libndi.dylib` (29.8 MB), `wrapper/bin/libndi.dylib` and `libndi_licenses.txt`.
`cyndilib.get_ndi_version()` returned `NDI SDK APPLE 12:49:17 Apr 13 2026 6.3.2.0` with no separate NDI install.
The NDI SDK license applies to redistributing `libndi`; check it before shipping a build.

API calls that worked (loopback, one process, sender thread plus finder plus receiver):

```python
from fractions import Fraction
from cyndilib import Sender, Finder, Receiver, VideoSendFrame, VideoFrameSync, FourCC, RecvColorFormat, RecvBandwidth

snd = Sender("name")
vf = VideoSendFrame(); vf.set_resolution(1920, 1080); vf.set_frame_rate(Fraction(30, 1)); vf.set_fourcc(FourCC.BGRA)
snd.set_video_frame(vf); snd.open()
snd.write_video(np_uint8_flat_array)            # clocked: blocks to the frame rate, does NOT hold the GIL

finder = Finder(); finder.open(); finder.wait_for_sources(5.0)   # found the sender in ~1.0 s
src = finder.get_source(finder.get_source_names()[0])            # names look like "HOST (name)"

rx = Receiver(color_format=RecvColorFormat.BGRX_BGRA, bandwidth=RecvBandwidth.highest)
vfs = VideoFrameSync(); rx.frame_sync.set_video_frame(vfs); rx.set_source(src)
rx.frame_sync.capture_video()                   # non-blocking, ~7 microseconds; always returns the latest frame
if vfs.xres > 0:                                # xres == 0 until the first frame arrives
    ts = vfs.get_timestamp_posix()              # changes per new frame: use it to detect new frames
    arr = vfs.get_array()                       # flat uint8, H*W*4 for BGRX_BGRA, no stride padding at 1080p
```

Results, 1920x1080 at 30 fps for 10 s, frame-sync receiver polled at ~120 Hz:

| Sender fourcc | Receiver format | Frames received | Age (wall - frame timestamp) | CPU (one core, sender plus receiver) | Received layout |
|---|---|---|---|---|---|
| UYVY | `BGRX_BGRA` | 294 (29.4 fps) | 12 ms | 30 % | 1080p30, 8,294,400 bytes, 4 B/px |
| BGRA | `BGRX_BGRA` | 294 (29.4 fps) | 18 ms | 37 % | fourcc BGRA, 4 B/px, stride 7680 |
| BGRA | `fastest` | 300 (30.0 fps) | 14 ms | 35 % | fourcc UYVA, 6,220,800 bytes (UYVY plane plus alpha plane), stride 3840 |

`capture_video()` mean 0.007 ms, max 0.23 ms. Sender wrote 30.0 fps. Connect time after `set_source`: ~10 ms.
Pixel format the receiver gives is whatever `RecvColorFormat` asks for: `BGRX_BGRA` gives BGRA bytes; `RGBX_RGBA`
exists and would upload to a GL RGBA texture with no swizzle (enum present, not run); `UYVY_BGRA` / `UYVY_RGBA` /
`fastest` are the cheaper wire formats (`fastest` returns packed UYVY plus alpha that needs a shader to convert).
`BGRX_BGRA` with an opaque sender reports `bits_per_pixel 24` but the buffer is still 4 bytes per pixel.

### The GIL trap (important for T8)

`Receiver.receive(ReceiveFrameType.recv_video, timeout_ms)` **holds the GIL for the whole timeout**. With a 200 ms
timeout and no sender, a 1 ms heartbeat thread ticked 16 times in 3 s (max gap 205 ms). In the first loopback attempt
(`receive(..., 100)` in the main thread, sender on a thread) the sender thread fell to 5.8 fps and only 1 to 1.5 fps
were received. With `timeout_ms=0` the heartbeat was healthy (2,294 ticks, max gap 14 ms) but `receive` then returned a
video frame on only ~4 of 30 polls, and a ring buffer that is not drained stalls (`recv_buffers_full` = 32 forever).
`rx.frame_sync` (`FrameSync` plus `VideoFrameSync`) avoids all of it: it never blocks and is the correct pull-style API
for a render loop that wants the latest frame. T8 should use the frame sync path, polled from the source's own thread
(which publishes the latest array for the frame thread to upload), never `receive()` with a timeout on a thread that
shares the GIL with the frame thread. `Sender.write_video` (clocked) did not starve a heartbeat thread (max gap 16 ms).

Also: a first attempt that polled `is_connected()` without ever calling `receive()` / `capture_video()` never
connected (cross-process too, "connected False" after 5 s with the sender listening on TCP 5960). The receiver
only connects as it is pumped. And `Receiver(source=src, ...)` followed by `receive(recv_video, 100)` got stuck at 4
frames until `fill_p_data` drained the ring; the `Receiver()` + `set_source()` + frame sync form above has neither problem.

### Other findings

- `VideoRecvFrame.fill_p_data(dest)` requires `dest` to be exactly the frame size (`ValueError: got differing extents in dimension 0 (got 8294400 and 6220800)`)
  and costs 0.3 to 0.7 ms at 1080p; the frame-sync path avoids it.
- `Receiver.video_stats` / `get_performance_data()` reported `frames_total 0` on the plain-receive path in this
  version, so count frames yourself (timestamp changes).
- A BGRA sender with incompressible noise content ran at about 1 fps (NDI encode cost) while smooth content ran at
  30 fps; real video is in between, so T9 should expect NDI-out cost to depend on content. UYVY is cheaper to send.

### `extra_ips` (Resolume / TouchDesigner on another machine)

`cyndilib.Finder()` takes **no arguments**: `finder.pyx` builds `NDIlib_find_create_t find_settings = [True, NULL, NULL]`,
so `p_extra_ips` is hard-coded NULL and cannot be passed per finder. Discovery on the same LAN worked without it
(mDNS). For a sender on another subnet, the fallback is the NDI per-user config file read by the runtime,
`~/.ndi/ndi-config.v1.json` (the directory did not exist on this machine), with
`{"ndi": {"networks": {"ips": "192.168.1.50,192.168.1.51"}}}` (shape from the NDI SDK docs; **not verified in this
spike**, loopback cannot show it). T8 should write that file on demand (or surface a "your NDI network list" setting)
rather than expect an API argument, and recreate the finder after editing it.

### Hygiene

The spike scripts ended with `os._exit(0)` to avoid waiting on interpreter teardown. One earlier run left a ghost
`m0ndi` entry on the finder until its process was killed. T8/T9 must close senders and receivers explicitly on app exit
(inside the 2 s join budget).

## 3. Recommendation

- **T9 (publish out), Syphon: GPU handoff.** Publish the final render texture with
  `publish_frame_texture(tex.glo, size=...)` from the frame thread right after the frame is drawn (0.3 ms at 1080p, no
  readback). Create the server once with the render context current.
- **T8 (live in), Syphon: GPU handoff.** A client frame is already a GL texture in our context. Sample the received
  `textureName()` directly (wrap with `ctx.external_texture` or bind by id) on the frame thread; do not read it back.
  Only the directory scan (up to 1 s of run-loop per call) goes on the source's own thread.
- **T9, NDI out: CPU copy is unavoidable** (NDI takes host memory): one `fbo.read()` (or a PBO readback) of the 1080p
  frame, ~4 to 7 ms, then `Sender.write_video(flat_uint8)` on a sender thread (it is clocked and releases the GIL).
  Prefer PBO readback so the frame thread only issues the read command.
- **T8, NDI in: CPU upload.** Poll `rx.frame_sync.capture_video()` on a per-source thread at ~60 to 120 Hz, copy
  `vfs.get_array()` when `get_timestamp_posix()` changes, and hand the array to the frame thread for `texture.write()`.
  Prefer `RecvColorFormat.BGRX_BGRA` (or `RGBX_RGBA`) for a straightforward RGBA upload; `fastest` is cheaper on the wire
  but needs a UYVY plus alpha shader. Never call `receive()` with a nonzero timeout.
- Both libraries must be imported inside the function that opens a source (`syphon` imports pyobjc and loads the
  Syphon framework at import; not separately timed here).
- Scratch scripts (not committed) are in `/Users/dallman/.claude/jobs/72d5be13/tmp/`: `spike_syphon.py`,
  `spike_ndi.py` (blocking-receive attempt), `spike_ndi_fs.py` (frame-sync version, the one to copy from), `ndi_gil*.py`.
