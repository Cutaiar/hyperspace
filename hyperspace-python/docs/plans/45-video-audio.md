# Plan 45 — video audio: a video's sound, under the transport's clock

**Status: V1, V2, V3 built.** V1 (2026-11-02; review fixes the same day) on
`wave0/v1-video-audio-decode`, merged; V2, the mixer (2026-11-02), on
`wave1/v2`; V3, the analyzer on the mix (2026-11-02), on `wave2/v3`; V4
is designed here and not built. From the
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
  the resampler puts mono on both sides at −3 dB (its centre mix level)
  and downmixes surround, so the memory cost is 384 kB a second whatever
  the file; V4's varispeed resamples at
  read time anyway, so the file's own rate buys nothing. A file with no
  audio track is `status == "none"`: `read` is silence, the thread ends,
  nothing is logged. Nothing plays; nothing audible changes.
- **The API V2 consumes.** `src.audio.enable()` / `disable()` (the
  play-audio toggle); `src.audio.read(at: int, n: int) -> np.ndarray` —
  `n` samples from sample `at` (counted at 48 kHz from the clip's start)
  as an `(n, 2)` float32 array, zeros wherever nothing is held; it never
  blocks and never raises. `status` (`off`; `fetching` until the probe and
  whenever the wanted position is outside what is held, so a reader
  hearing silence is never told `ready`; `ready` while it is inside;
  `none`; `error: …` — an error is the last window's, an older window
  stays readable, and a move of `AUDIO_RETRY_S` = 1 s tries again),
  `duration` (where the track ends in transport seconds: its own start
  less the video's, plus its length — a track whose first pts is after
  the video's ends that much later), `rate`, `channels`, `held` (the span
  of seconds in memory) and `nbytes`. A source without an `audio`
  attribute (a still, a live feed, a missing one) has no sound.
- **V2 — the mixer (built), `media/mixer.py`.** One
  `sounddevice.OutputStream` at 48 kHz stereo float32, a block of 800
  samples (one 60 Hz frame), owned by the media package. Once a frame,
  after the transports are stepped, `MediaState.poll` hands the mixer one
  tuple of voices — for each channel whose play-audio toggle is on and
  whose source has an `audio`: the soundtrack, the playhead the transport
  was just stepped to, the gain. The callback reads the tuple once, sums
  `read(round(playhead × 48000), frames)` × gain and clips at ±1. **The
  callback integrates nothing**, so the glitch is structural: the audio
  and display clocks are never locked, and even at rate 1 a block now and
  then repeats or skips — an occasional click at rate 1 is expected until
  V4 reads sequentially and slews toward the transport; any other rate
  stutters (V4's). Only forward play is read: a hold, a jog's coast under
  `HOLD_SPEED`, a `once` clip parked at its end, reverse and pingpong's
  way back are left out, silent — not a block repeated as a buzz. The
  callback allocates nothing once warm (`Soundtrack.read` grew an
  optional `out=`). A read
  that raises or returns the wrong shape is skipped and counted.
  The params (`params.build_registry`'s media loop): `media.<c>.audio`
  (a toggle, off — today's silence) and `media.<c>.gain` (linear, unity,
  `tapers.T_MEDIA_GAIN`: off, then −30…+6 dB, the notch at unity), both
  performance — persisted, learnable, modulatable, so Learn, the pad, a
  macro and undo reach them; no schema move (a file without them loads
  them at their defaults). The toggle `enable()`s the channel's
  soundtrack the frame it turns on and lets it go 30 frames after it turns
  off (`OFF_FRAMES`: a lane flicking the toggle costs nothing); a slot
  change under it enables the new, and the old ends with its source's
  `close`. `disable()` joins the soundtrack's thread, so it runs on the
  media closer, never at once with an enable (`channels._Sound`). The stream is opened, on a thread of its
  own, the first time any channel's sound is on (at rate 0 or gain off
  too) — nothing until something asks — reopened 5 s after it fails or
  stops under us (a device unplugged), and otherwise left open, playing silence, until `MediaState.close` at
  exit. MEDIA shows the toggle and the gain on the selected channel's
  source line; GRAPH's channel node side pane lists them with its other
  params; SYSTEM a `media sound` line (open, channels playing, underruns).
  `tests/test_media_mixer.py`; register rows 581–583; hand checks 437–439
  (group BB).
- **V3 — the analyzer listens to the mix (built).** The mixer's summed
  block is pushed into the analyzer's ring as a source beside `mic` and
  `file` (`AudioEngine` grows a `mix` mode): the bands follow the show's
  video sound. One analyser, fed by one more input. What the build chose
  is under "What changed in the build" below; register rows 594–596,
  hand checks 446–448 (group BE), `tests/test_audio_mix.py`.
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
  window and is tried again once the position has moved `AUDIO_RETRY_S`
  (1 s) — for a whole track too, whose thread stays until a window is in.
  A track held whole ends its thread and closes its file once it is in.
  Each resampled frame is laid by the pts the resampler gives it, so a
  gap or a dropped frame in the file is silence there and shifts nothing
  after it. A track of unknown length (no duration from the probe) is
  windowed from the position, into a buffer that starts at 2 s and doubles
  as rows land, so a short clip never allocates the 120 s window.
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

Second review (2026-11-02, eight findings on e503eff), each with its
test: the track's end in transport time (its own start less the video's,
plus its length — audio from 0.5 s under video from 0 keeps its last half
second); a stop check right before a window is published, so an
abandoned thread writes nothing back over samples let go or another
thread's; `close` clears `_opened`, so `enable` on a closed source starts
nothing (while `disable` → `enable` still works); a whole track that
fails or decodes empty keeps its thread and is woken, retried after a 1 s
move; each resampled frame placed by its own pts (a pts gap in an mkv is
silence, the rest keeps its time); an unknown-length clip's buffer starts
at 2 s and doubles, no trim copy when right-sized (tracemalloc holds the
peak under 3× the clip, far under the window); `status` is `fetching`
whenever the wanted position is outside the held window; the `getattr`
guards on `_thread` dropped.

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

## What changed in the build (V3)

- **The engine is `audio.AudioEngine`**, not an `AudioSource` (there is
  none): `start_mix(mixer)` beside `start_mic` and `start_file`, mode
  `"mix"`. It opens no stream and grabs no input device; it hands the
  mixer its ring (`Mixer.listen`), and `stop` (which every `start_*` calls
  first) takes it back (`listen(None)`).
- **What the analyzer hears** (rec): the block the callback just wrote —
  after the gains and after the ±1 clip, what the room hears — as mono,
  the mean over its channels (L and R), at 48 kHz (`AudioEngine.MIX_RATE`, held equal to
  `AUDIO_RATE` by a test rather than imported: `audio.py` may not import
  the media package). A callback with no voice pushes zeros, so the bands
  decay. The push is one copy into the mixer's kept `_mono`; it counts
  nothing and moves nothing — the analyzer drains the ring once a frame
  as it drains the mic's. `start_file`'s `_played` is not reused.
- **Silence, not a stale block** (rec): until a channel is heard the
  mixer's stream is not open (V2, unchanged), so no callback comes; once
  the mixer has not pushed for `MIX_IDLE_FRAMES` = 6 frames (never
  opened, failed, stopped, or stalled with `active` still true),
  `AudioEngine.step` zeroes the analyser's window each frame — a count of
  frame-loop steps, not the mixer's `state`. A `mix` with nothing heard
  is silence, not an error; a mixer that failed shows its `state` in
  warning colour on AUDIO.
- **The picker is a toggle, `audio.mix`**, beside `audio.mic` (AUDIO:
  *Listen to video sound*; not persisted, no key or desk binding),
  declared only when the host's `MediaState` is passed (a stand-in's
  mixer is fed by nobody) and reaching the mixer through
  `MediaState.live_mixer()`. There
  is **no config key** for the source — none names the mic or the file
  either — so `config.py` is untouched.
- **Hot reload**: the new fields are read with defaults, so the live
  stream and capture survive; the toggle is a registry param built at
  launch, so the button needs one restart. A ring push that raises is
  counted in `Mixer.tap_errors` (SYSTEM: `analyzer push errors`, apart
  from voice read errors) after the output is written: the analyzer
  loses a block, the room loses nothing.
- **`publish` is untouched** (D2 is changing its signature in parallel).
