# Plan 45 — video audio: a video's sound, under the transport's clock

**Status: V1 built (2026-11-02; review fixes the same day)** on
`wave0/v1-video-audio-decode`, the first of four PRs; V2–V4 are designed
here and not built. From the
post-show triage of 2026-10-31: PyAV decoded only the video stream, the
proxies are MJPEG with no audio, and the only output stream was the
analyzer's WAV playback (`audio.py`) — no mixer, no per-channel gain.

## The rule: no second time base

**The media transport is the one clock and audio is its slave** (owner,
2026-11-02, addendum 8). `Transport.step` (`media/transport.py`) is
stepped once a frame on the frame thread and its playhead, in seconds, is
the only position a video has: the video thread follows it through
`want(t)`, and so does the soundtrack. Nothing in the audio path has a
clock, a stream position, a playhead or a sample counter of its own that
the transport does not set; a rate change, a scrub, a jog, reverse and a
loop wrap are each the transport moving, and the sound follows because it
is *read at the transport's position*, never because it was told to play.
The analyzer picks the mix as a source (V3) — one more input beside the
mic and the WAV file — not a second engine with a position of its own.
What `audio.py`'s file transport does today (`_played` counted against the
stream's callbacks, `position()` derived from it) is exactly the second
time base this rule forbids for video sound, and V4 must not copy it.

## The data path

```
file ──PyAV──▶ media-video-<name>   (video frames → Latest → the renderer)
   └───PyAV──▶ media-audio-<name>   (Soundtrack: float32 stereo 48 kHz in memory)
                       ▲ want(t)                      │ read(at, n)
MediaState.poll ─▶ Transport.step ─▶ VideoSource.want ┘      ▼
                                                    V2 mixer ─▶ V3 analyzer source
                                                              └▶ V4 output (varispeed)
```

- **V1 (this PR), `media/video.py`.** `VideoSource.audio` is a
  `Soundtrack` on a second thread of the source's own
  (`media-audio-<name>`), always from the original file (a proxy has no
  audio), closed with the source inside the same `CLOSE_JOIN_S` budget.
  Both threads are a `_Follower`: `open` / `want` / `close`, and a stop
  event per start handed to `_run`, so a thread `close` gave up on (stuck
  in `av.open` on a cloud file) ends when the open returns and never
  resumes beside the one a later `open` started.
  `VideoSource.want(t)` hands the transport's position to both threads.
  **Nothing is read until something asks for sound**: `Soundtrack.enable()`
  starts the thread (V2's play-audio toggle will call it; `disable()` ends
  it and lets the samples go), and until then the file is not opened and
  `status` is `off`. The reason is I/O: a window decode demuxes every
  packet in its range, video included, so a 120 s window of a 4K clip at
  100 Mbit/s reads about 1.5 GB and a whole-held ≤ 120 s clip reads the
  whole file — on a cloud-synced library, beside the video thread and the
  proxy job. An unheard soundtrack must cost none of that; in V1 nothing
  calls `enable()`, so this PR adds no read at all.
  The track is resampled by PyAV on that thread to **float32, stereo,
  48 kHz** (`AUDIO_RATE`, `AUDIO_CHANNELS`): one rate and one layout so
  the mixer adds every track into one buffer and opens one output stream;
  mono is doubled and surround downmixed by the resampler, so the memory
  cost is 384 kB a second whatever the file; V4's varispeed resamples at
  read time anyway, so the file's own rate buys nothing. A file with no
  audio track is `status == "none"`: `read` is silence, the thread ends,
  nothing is logged. Nothing plays; nothing audible changes.
- **The API V2 consumes.** `src.audio.enable()` / `disable()` (the
  play-audio toggle); `src.audio.read(at: int, n: int) -> np.ndarray` —
  `n` samples from sample `at` (counted at 48 kHz from the clip's start)
  as an `(n, 2)` float32 array, zeros wherever nothing is held; it never
  blocks and never raises. `status` (`off`, `fetching`, `ready`, `none`,
  `error: …` — an error is the last window's; an older window stays
  readable), `duration`, `rate`, `channels`, `held` (the span of seconds
  in memory) and `nbytes`. A source without an `audio`
  attribute (a still, a live feed, a missing one) has no sound.
- **V2 — the mixer.** One `sounddevice.OutputStream` at 48 kHz stereo,
  owned by the media package, whose callback asks each channel with a
  timed source for `read(round(playhead × 48000), frames)` × that
  channel's gain and sums. A per-video "play audio" toggle and a
  per-channel gain, both `media.<c>.*` params (so Learn, the pad, a macro
  and undo reach them; defaults: off and unity, today's silence). The
  playhead the callback reads is the transport's last stepped value; the
  callback integrates nothing.
- **V3 — the analyzer listens to the mix.** The mixer's summed block is
  pushed into the analyzer's ring as a source beside `mic` and `file`
  (`AudioSource` grows a `mix` mode): the bands follow the show's video
  sound. One analyser, fed by one more input.
- **V4 — sync with video as master; varispeed.** The callback reads at
  the transport's position with the transport's speed: at rate r it
  consumes r × frames source samples per output block and resamples
  them (linear first; a windowed sinc if it is heard), so scrub, reverse
  and a rate change sound like tape, and rate 0 is silence. A block that
  reaches outside the held window is zeros. V4 also decides the window's
  wrap case (below) and whether a short clip's loop needs the head
  prefetched.

## The memory policy

A two-hour film must not allocate gigabytes on open. The policy, in
`video.py` and held by `tests/test_media_audio.py`:

- **A track of `AUDIO_WINDOW_S` (120 s) or shorter is held whole**,
  decoded once, never re-decoded: at most 46 MB.
- **A longer track is held as one window of 120 s centred on the
  transport's position**, kept inside the track, and re-decoded (on the
  soundtrack's thread; the old window stays readable until the new one is
  swapped in by one reference) when the position is more than
  `AUDIO_RECENTRE_S` (30 s) from the window's centre. A window is decoded
  straight into one buffer of its size — no chunk list, no concatenate —
  so a two-hour film holds `AUDIO_WINDOW_BYTES` = 46 MB, **92 MB for the
  moment a new window is made while the old stays readable**, and eight
  channels of them 370 MB (740 MB in that moment) at the very worst; a
  decode of 120 s of AAC is a fraction of a second. A decode that the
  transport has left behind (a far scrub mid-decode) is abandoned, not
  finished first; one that fails or comes back empty leaves the old
  window and is tried again at the next move past the recentre distance.
  A track held whole ends its thread and closes its file once it is in.
- **Outside the window is silence.** Forward play at any rate up to the
  re-centre threshold's margin never leaves the window; a scrub far away
  reads zeros until the window arrives (one decode later). A loop wrap on
  a long file reads zeros at the head for that same moment — V4's problem
  to judge by ear, not V1's.

Why not whole-decode to N minutes and window past it: one code path.
A short clip is simply a window that covers it and never moves.

## Tests

`tests/test_media_audio.py`, fast tier: clips synthesized with PyAV (no
committed fixture) — PCM in a `.mov` and AAC in an `.mp4`, 440 Hz left
and 880 Hz right; a 30 s mono clip whose tone changes at 15 s for the
window. Length, rate and channels; the sines recovered by FFT in each
channel; a file without audio is `none` with nothing printed; the window
policy's edges; a probe made to say two hours holds one window; a
patched 4 s window follows a scrub and lets the head go; `open` returns
under 100 ms with `av.open` gated; `close` joins the audio thread, also
mid-decode; the adapter hands out a source with a soundtrack; the
soundtrack reads the original while the picture reads the proxy.

Review fixes (2026-11-02, ten findings on PR #316), each with its test:
pts are the container's and the window is transport time (a file whose
streams start late — MPEG-TS, a MOV with an edit list — is held from its
first sample); a window's error is the window's; one buffer a window;
a whole track's thread ends; a stale decode is abandoned; an empty
decode is not held; `audio` a class attribute; the `_Follower` base with
a stop event per start; nothing read until `enable()`; `close` proven
mid-decode.

Hand check 421 ([`11-hand-checks.md`](11-hand-checks.md)): open a show
video, nothing audible changes, memory stays flat, **no extra read**
(nothing asks for sound in V1). Register row 562; DECISIONS "Media".

## What fights the rule, for V2–V4 to mind

- `audio.py`'s file transport counts `_played` in the output callback
  and derives `position()` from it: a second time base of exactly the
  kind forbidden. V3 feeds the analyzer from the mix; it must not reuse
  `start_file`'s model for video sound.
- `Transport.step` runs on the frame thread, so the position the audio
  callback reads is at most one frame old and advances in frame-sized
  steps; V4 smooths within a block by the transport's `speed`, never by
  a clock of its own.
- The soundtrack is not in `hotreload.MODULES` as a module of its own
  because it lives in `media.video`, which is; a hot reload re-classes a
  live `VideoSource` and its `Soundtrack` and keeps their threads. A
  `VideoSource` from before this build has no `audio` (guarded with
  `getattr`): restart to hear one.
