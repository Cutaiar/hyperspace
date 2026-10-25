# Plan 32 Media Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Media sources (stills, video, webcam, Syphon, NDI) on eight switchable channels with a scrubbable transport, read by a backdrop, the faces, an effect's image/`aux` input or an output — and the rig's outputs published back out over Syphon and NDI.

**Architecture:** A new package `hyperspace/media/` holds frames, sources, adapters, the pool, the media folder, the transport and the channels; nothing in it touches GL. Live kinds are device-registry kinds. The renderer owns `MediaTextures` (upload) and the graph gains a `media` node kind; the backdrop is a `Composite` under the scene. All decoding happens on the pool or a source's own thread; the frame thread only steps transports and uploads.

**Tech Stack:** Python 3.14 (`.python-version`), moderngl, numpy, Pillow + `pillow-heif`, PyAV (`av`), `syphon-python`, `cyndilib`, imgui-bundle; pytest via `uv run pytest`.

**Spec:** [`32-media-channels.md`](32-media-channels.md) (decisions 321–339 answered 2026-10-22). Read it first; this plan does not repeat its reasons.

## Global Constraints

- Work under `hyperspace-python/`. Integration branch `plan-32-media` (base `plan-28-30-integration` @ 1a5cc2e). Each task on its own branch `plan-32-<task id>` in its own git worktree, merged into `plan-32-media` by the orchestrator.
- **Nothing decodes, resizes, scans or blocks on the frame thread.** Jobs that end → `media.pool.submit`; blocking reads → the source's own thread. The frame thread steps transports and uploads textures only.
- **Importing `hyperspace.app` imports no adapter library** (`av`, `pillow_heif`, `syphon`, `cyndilib`): each is imported inside the function that opens a source (extend `tests/test_app_boundary.py`).
- Channels: exactly `CHANNELS = "abcdefgh"`; bin length `BIN = 16`.
- Caps: files ≤ 1920×1080, live ≤ 1280×720, aspect kept (`CAP_FILE`, `CAP_LIVE`).
- Transport: `rate` −4…+4 (default 1, 0 holds/freezes); `pos` 0…1; `jog` −1…+1; `loop` ∈ (`loop`, `pingpong`, `once`).
- Proxies: clips ≤ 600 s, MJPEG, ≤ 1280×720, in `<home>/media-cache/proxies/`, never in the shared folder.
- Folder rescan every 2.0 s; thumbnails 160 px in `<home>/media-cache/thumbs/`.
- A live feed that stops holds its last frame 1.0 s, then reads None (black).
- Source ids: `shared:<rel>`, `local:<rel>`, `file:<abs>`, `camera:<name>`, `syphon:<app>/<server>`, `ndi:<sender>`; `phone:` reserved (V2), parsed but never opened.
- Preset: a `media` section `{"channels": {"a": [id | null, …≤16], …}}`; schema `hyperspace.preset/4` **only** when the document has a `media` section with any id, or a `media.*` / `backdrop.*` / `view.media*` value away from its default; otherwise the file is byte-for-byte what this base writes. Load accepts both.
- `view.bmp_*` are removed; a loaded value under `view.bmp_*` is dropped with the load note `bitmap file <path> is no longer read: put it on a media channel` (only when `view.bmp_file` was non-empty).
- No desk/APC40 default bindings; `apc40.py`, `midi.py` untouched (row 339).
- Match the surrounding code: module docstrings that say what and why, the plan/row numbers in comments where the repo does that, `getattr(self, "x", None)` for state a hot-reloaded object may lack, `# noqa: BLE001` on a must-not-kill-the-app except.
- **No existing golden moves.** New goldens only for new fixtures.
- Commits end with the session's attribution lines (the orchestrator passes them).

## Review Focus

1. **A file on a channel is deleted, renamed or replaced mid-show** → the channel goes black and its status `missing`; a replaced file (new mtime) reloads; nothing raises on the frame thread. (T4, T5 tests)
2. **Junk in the shared folder** — a `.txt`, a truncated mp4, a 0-byte cloud placeholder, a file still syncing → listed with `error: …` or `fetching`, never stops the scan or the app. (T4 tests)
3. **Rapid slot switching** (the sequencer at 16ths, a macro sweeping `slot`) → sources opened and closed in balance, every source thread joined on close, no thread or texture leak; app exit joins everything within 2 s. (T5 test with a counting fake adapter)
4. **A huge image** (8000×6000 HEIC/JPEG) → decoded and capped on the pool; the frame thread never waits for it (it reads None until ready). (T1 test with a sleeping fake decode)
5. **A live sender vanishes and comes back** (Resolume quits, Wi-Fi drops) → last frame held 1 s, then black, status `lost`; picked up again with no relaunch. (T8 test on a fake feed)

---

## Task order and parallelism

| Wave | Tasks (parallel within a wave) | Touches |
|---|---|---|
| 1 | T0 spike · T1 core · T2 transport | `docs/plans/assets/32-media/` · `media/` · `media/transport.py` |
| 2 | T3 video · T4 folder · T5 channels · T8 live | `media/` · `media/` · `media/channels.py`, `params.py`, `preset.py`, `view.py` · `media/live*.py`, `devices.kinds` |
| 3 | T6 render + backdrop | `render.py`, `graph.py`, `media_tex.py` |
| 4 | T7 faces + aux · T9 out | `render.py` face path, `fx.py`, `graph.py` Effect, shaders · `outputs.py`, `media/publish.py`, `config.py` |
| 5 | T10 MEDIA page + GRAPH | `ui_media.py`, `ui.py`, `graphview.py` |
| 6 | T11 docs | `docs/` |

T7 and T9 both touch `render.py`; the orchestrator merges T7 first.

---

### Task 0 (T0): Spike — Syphon and NDI beside our GL (throwaway)

**Files:**
- Create: `docs/plans/assets/32-media/m0-findings.md` (kept); scratch scripts under `$CLAUDE_JOB_DIR/tmp` (not committed).

- [ ] **Step 1:** In a scratch script, make a hidden GLFW window + moderngl context like `app.py` does; create a `syphon.SyphonOpenGLServer` (or the Metal server if OpenGL is absent in `syphon-python` 0.2.0) and publish a 1920×1080 moderngl texture; receive it with a Syphon client in the same process. Record: can a texture in our context be published with no CPU copy (texture id handoff)? Received frame as a numpy array or a GL texture? ms per frame at 1080p.
- [ ] **Step 2:** `cyndilib`: a sender and a finder + receiver in one process on loopback, 1920×1080 BGRA at 30 fps for 10 s. Record: does the wheel carry the NDI runtime (no separate install)? fps received, latency, CPU %, the pixel format the receiver gives, how `extra_ips` is passed to the finder.
- [ ] **Step 3:** Write `m0-findings.md`: one section each, the API calls that worked (exact), the numbers, and the recommendation for T8 and T9 (GPU handoff vs CPU copy). Commit only that file: `git commit -m "Plan 32 M0: Syphon and NDI findings"`.

---

### Task 1 (T1): Media core — frames, sources, ids, the pool, stills

**Files:**
- Create: `hyperspace/media/__init__.py`, `frame.py`, `source.py`, `ids.py`, `pool.py`, `adapters.py`, `still.py`
- Modify: `pyproject.toml` (deps: `av>=19`, `pillow-heif>=1.8`, `syphon-python>=0.2 ; sys_platform == 'darwin'`, `cyndilib>=0.1.3`, `pyobjc-framework-avfoundation ; sys_platform == 'darwin'`, each with a comment in the file's style), `uv.lock`
- Modify: `tests/test_app_boundary.py`
- Test: `tests/test_media_core.py`

**Interfaces — Produces:**
- `frame.MediaFrame(pixels: np.ndarray, t: float, frame: int)` frozen dataclass; `pixels` H×W×4 uint8, C-contiguous, read-only; `.size -> (w, h)`. `frame.to_rgba(arr) -> np.ndarray` (accepts H×W×3/4, uint8 or float 0–1). `frame.fit_within(arr, cap: tuple[int, int]) -> np.ndarray` (downscale only, aspect kept, PIL `LANCZOS`). `CAP_FILE = (1920, 1080)`, `CAP_LIVE = (1280, 720)`.
- `source.Latest`: `put(f: MediaFrame)`, `get() -> MediaFrame | None`.
- `source.Source` Protocol: `sid: str`, `kind: str`, `status: str`, `timed: bool`, `duration: float` (0.0 untimed), `latest() -> MediaFrame | None`, `want(t: float) -> None` (seconds; no-op when untimed), `open() -> None`, `close() -> None` (joins its thread).
- `source.READY, FETCHING, MISSING, LOST = "ready", "fetching", "missing", "lost"`; `source.error(why: str) -> str` → `"error: " + why[:160]`.
- `ids.SourceId(kind: str, ref: str)`; `ids.parse(sid: str) -> SourceId` (raises `ValueError` naming the id); `ids.KINDS = ("shared", "local", "file", "camera", "syphon", "ndi", "phone")`; `ids.FILE_KINDS = ("shared", "local", "file")`.
- `pool.submit(fn, *a, **kw) -> concurrent.futures.Future`; `pool.shutdown(wait: bool = True)`; 3 workers, thread names `media-pool-<n>`.
- `adapters.Resolver` Protocol: `path(sid: str) -> Path | None`, `live(sid: str) -> Source | None`. `adapters.open_source(sid: str, resolver) -> Source` picks by extension for file kinds (`STILL_EXT = {.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.heic,.heif}`; video extensions are T3's `VIDEO_EXT`, imported lazily) and `resolver.live` for live kinds; a missing path returns a `MissingSource(sid)` whose status is `missing` and `latest()` None.
- `still.StillSource(sid: str, path: Path, cap=CAP_FILE)`: `open()` submits the decode to the pool (Pillow, `pillow_heif.register_heif_opener()` inside the job), status `fetching` until done, then `ready` or `error: …`.

- [ ] **Step 1: Write the failing tests** in `tests/test_media_core.py`:
  - `test_frame_is_read_only_rgba` — `MediaFrame(to_rgba(np.zeros((4,6,3),np.uint8)), 0.0, 0)`: `.size == (6, 4)`, `pixels.shape == (4,6,4)`, alpha 255, writing raises `ValueError`.
  - `test_fit_within_caps_and_keeps_aspect` — 8000×6000 → (1440, 1080); 100×50 unchanged.
  - `test_latest_never_torn` — a writer thread puts 2000 frames whose pixels are all `i`; a reader's every `get()` is uniform.
  - `test_parse_ids` — `parse("shared:loops/a.mp4") == SourceId("shared","loops/a.mp4")`; `parse("ndi:RIG (Arena)")` keeps the ref; `parse("nope")` and `parse("bogus:x")` raise `ValueError`.
  - `test_still_decodes_on_the_pool` — a fake decode sleeping 0.3 s (monkeypatched loader): `open()` returns in < 20 ms, `latest()` is None and status `fetching`, then within 1 s a frame and `ready`.
  - `test_huge_still_is_capped` — a generated 4000×3000 PNG in `tmp_path` → frame size (1440, 1080).
  - `test_heic_opens` (skip unless `pillow_heif` imports) — write a HEIC with `pillow_heif`, read back RGBA.
  - `test_bad_file_is_an_error` — a `.png` containing text → status starts `error: `, no raise.
  - `test_missing_path_is_missing_source` — resolver returning None → status `missing`.
  - In `tests/test_app_boundary.py`, add `av`, `pillow_heif`, `syphon`, `cyndilib` to the modules importing `hyperspace.app` must not pull in.
- [ ] **Step 2:** `uv run pytest tests/test_media_core.py tests/test_app_boundary.py -q` → fails (no module).
- [ ] **Step 3:** Implement the interfaces above. `Latest` is a single attribute swap (no lock needed for a reference; document why).
- [ ] **Step 4:** Same command → passes. `uv sync` leaves `uv.lock` updated.
- [ ] **Step 5:** Commit `"Plan 32 T1: media core — frames, sources, ids, the pool, stills"`.

---

### Task 2 (T2): The transport

**Files:** Create `hyperspace/media/transport.py`; Test `tests/test_media_transport.py`

**Interfaces — Produces:** `LOOPS = ("loop", "pingpong", "once")`. `Transport(duration: float)`; `step(dt: float, rate: float, pos: float, jog: float, loop: str) -> float` returns the playhead in seconds; attributes `playhead: float`, `scrubbing: bool`, `speed: float` (current, incl. jog coast). `reset(pos: float = 0.0)`.

Rules (the spec's C section): if `abs(pos - last_pos) > 1e-6` the playhead is put at `pos * duration` and `scrubbing` is True for that step; otherwise it advances by `speed * dt` where `speed` springs toward `rate + 8.0 * jog` using `motion.spring(x, v, target, dt, hz=2.0, damp=1.0)` (jog held → spins faster; released → coasts back to `rate`). `loop`: wrap; `pingpong`: reflect and flip the direction sign; `once`: clamp at the ends.

- [ ] **Step 1: Failing tests:** `test_native_rate_advances` (duration 10, rate 1, 60 steps of 1/60 → 1.0 ± 1e-6 after the spring settles: start with `speed` already at rate — `Transport` initialises `speed = 1.0`); `test_double_and_reverse` (rate 2 → 2 s per s; rate −1 from 5 → 4); `test_rate_zero_holds`; `test_pos_latch_scrubs_then_plays_on` (pos 0 → 0.5 jumps to 5.0, `scrubbing`; next steps with pos 0.5 unchanged advance from 5.0); `test_lfo_on_pos_drives_playhead` (pos moving every step → playhead == pos·duration each step); `test_jog_spins_and_coasts` (jog 1 for 0.5 s → speed > 4; jog 0 for 3 s → speed within 0.05 of rate); `test_loop_modes` (loop wraps 9.9+0.2 → 0.1; pingpong reflects to 9.9 and then moves down; once clamps at 10.0); `test_zero_duration_is_zero`.
- [ ] **Step 2:** run → fail. **Step 3:** implement. **Step 4:** run → pass. **Step 5:** commit `"Plan 32 T2: the transport — rate, the pos latch, jog coast, loop modes"`.

---

### Task 3 (T3): Video files and scrub proxies

**Files:** Create `hyperspace/media/video.py`, `hyperspace/media/proxy.py`; Modify `hyperspace/media/adapters.py` (route `VIDEO_EXT`); Test `tests/test_media_video.py`

**Interfaces — Consumes:** T1's `Source`, `Latest`, `MediaFrame`, `fit_within`, `pool.submit`. **Produces:**
- `video.VIDEO_EXT = {.mp4,.mov,.m4v,.webm,.mkv,.gif,.avi}`.
- `video.VideoSource(sid: str, path: Path, cap=CAP_FILE, cache: Path | None = None)` — `timed = True`; `duration`, `fps`; `want(t)` stores the wanted time; its own thread (`media-video-<name>`) decodes the frame at or before the wanted time: sequential decode when moving forward ≤ 1 s, otherwise `container.seek` then decode forward. Frames carry `frame` = decoded frame index. Reads the proxy when `proxy.proxy_for(path, cache)` exists, and submits `proxy.make_proxy` once if `duration ≤ 600` and none exists.
- `proxy.proxy_for(path: Path, cache: Path) -> Path | None`; `proxy.make_proxy(path: Path, cache: Path) -> Path` — MJPEG `.mov`, ≤ 1280×720, same fps, key `<stem>-<size>-<mtime_ns>.mov`, written to a temp name then renamed.

- [ ] **Step 1: Failing tests** (a fixture writes a 3 s 320×240 30 fps clip with PyAV whose frame *i* is filled with gray `i*2`): `test_duration_and_fps`; `test_want_decodes_that_frame` (want 1.5 → within 1 s a frame whose gray ≈ 90 ±4); `test_backward_seek` (want 2.5 then 0.2); `test_gif_is_timed` (a 5-frame GIF via Pillow); `test_proxy_made_once_and_used` (open twice; `make_proxy` called once; second open reads the proxy path); `test_long_clip_gets_no_proxy` (monkeypatch duration 601); `test_close_joins_thread` (`threading.enumerate()` has no `media-video-` thread after `close()`); `test_truncated_file_is_error`.
- [ ] **Step 2–4:** run, implement, pass (`uv run pytest tests/test_media_video.py -q`). **Step 5:** commit `"Plan 32 T3: video sources on their own thread, scrub proxies"`.

---

### Task 4 (T4): The media folder

**Files:** Create `hyperspace/media/folder.py`, `hyperspace/media/thumbs.py`; Modify `hyperspace/config.py` only if needed to expose the library root (it exists: `[library] path`); Test `tests/test_media_folder.py`

**Interfaces — Produces:**
- `folder.Entry(sid: str, path: Path, kind: str ("still"|"video"), size: int, mtime: float, group: str, status: str)` frozen.
- `folder.MediaFolder(shared: Path | None, local: Path, cache: Path)` — implements T1's `Resolver.path`; `scan() -> list[Entry]` (sync, used by tests and by the watch job); `start(every: float = 2.0)` / `stop()` run the scan on the pool on a timer thread `media-folder-watch`; `entries: tuple[Entry, ...]` (last scan); `changed: int` (bumps when the listing changes); `status(sid) -> str`; `thumb(sid) -> Path | None` (submits a thumbnail job on first ask); `add_file(path) -> str` (returns `file:<abs>`); `copy_to_shared(sid) -> str` (pool job; returns the new `shared:` id).
- `shared` is `<library>/media/`, `local` is `<home>/media/`; both created if absent (shared only when a library path is set).
- Status per file: `fetching` if a read of its first 64 KiB takes > 0.5 s or the file is 0 bytes with a cloud placeholder flag (`st_flags & UF_DATAVAULT` / `SF_DATALESS` on macOS); `error: unsupported` for other extensions (hidden by default, listed with `scan(all=True)`); else `ready`.
- `thumbs.make(path: Path, out: Path, px: int = 160) -> Path` (stills via Pillow, videos via PyAV's first frame).

- [ ] **Step 1: Failing tests** on `tmp_path` trees: `test_scan_lists_shared_and_local` (ids `shared:a/b.png`, `local:c.mp4`, group `a`); `test_dropped_file_appears_within_a_scan` (start(every=0.1), drop a file, within 1 s `changed` bumped and entry present); `test_removed_file_is_missing` (`status` → `missing`); `test_junk_does_not_stop_the_scan` (a `.txt`, a 0-byte `.mp4`, a directory named `x.png` → scan returns the good entries; the 0-byte one is not `ready`); `test_slow_read_is_fetching` (monkeypatch the probe to sleep 0.6 s); `test_conflict_copies_are_listed` (`a (1).png`); `test_thumb_keyed_by_mtime` (touch → new thumb path); `test_add_file_and_copy_to_shared`; `test_no_library_means_no_shared`.
- [ ] **Step 2–4.** **Step 5:** commit `"Plan 32 T4: the media folder — scan, watch, thumbnails, fetching and missing"`.

---

### Task 5 (T5): Channels, their params, the preset

**Files:** Create `hyperspace/media/channels.py`; Modify `hyperspace/view.py` (remove `bmp_*`, add the fields below), `hyperspace/params.py` (register), `hyperspace/preset.py` (section, schema, the note), `hyperspace/learn.py` (`_BITMAP` → media ids), `hyperspace/app.py` (build `MediaState`, poll it each frame in the scene-setter slot after the devices, close on exit, hand it to the renderer as `renderer.media`); Test `tests/test_media_channels.py`, `tests/test_media_preset.py`

**Interfaces — Consumes:** T1 (`open_source`, `Resolver`, `Source`), T2 (`Transport`, `LOOPS`). **Produces:**
- `channels.CHANNELS = "abcdefgh"`, `BIN = 16`, `FITS = ("cover", "contain", "stretch")`.
- `channels.Channel` dataclass: `name: str`, `bin: list[str | None]` (len 16), `slot: float`, `fit: int`, `rate: float = 1.0`, `pos: float = 0.0`, `jog: float = 0.0`, `loop: int = 0`; runtime (not saved): `source: Source | None`, `transport: Transport | None`.
- `channels.MediaState(resolver, opener=adapters.open_source)`: `channels: dict[str, Channel]`; `poll(dt: float, now: float) -> None` — for each channel, the id at `round(slot)`; if it changed, close the old source and open the new one; step its transport if `timed` and call `want`; `frame(c: str) -> MediaFrame | None`; `status(c) -> str`; `playhead(c) -> tuple[float, float] | None` (seconds, duration); `missing() -> list[str]` (ids in any bin the resolver cannot find on this Mac, for the banner); `assign(c, i, sid | None)`; `to_json() -> dict`; `from_json(d: dict) -> list[str]` (notes for bad ids, which are dropped); `close()`. A live source with `rate == 0` keeps its current frame (freeze).
- Params (group `media`), in `params.build_registry(..., media=None)`: for each `c`: `media.<c>.slot` continuous integer 0–15; `media.<c>.fit` enum `FITS`; `media.<c>.rate` −4…4; `media.<c>.pos` 0…1; `media.<c>.jog` −1…1 (bipolar); `media.<c>.loop` enum `LOOPS`.
- `view.ViewState` gains `media: int = 0` (0 off, 1–8 = a–h), `media_alpha: float = 1.0`, `media_scale: float = 0.9`, `media_mode: int = 0`, `media_amp: float`, `media_rate: float` (the old `bmp_*` defaults), `backdrop: int = 0`, `backdrop_alpha: float = 1.0`, `backdrop_history: bool = False`. Param ids: `view.media`, `view.media_alpha`, `view.media_scale`, `view.media_mode`, `view.media_amp`, `view.media_rate` (same labels/ranges as the old bitmap ones, "Bitmap" → "Media"), `backdrop.channel`, `backdrop.alpha`, `backdrop.history` (toggle). Channel choices for both: `("off", "a", …, "h")`.
- `preset.MEDIA_KEY = "media"`, `preset.MEDIA_SCHEMA = "hyperspace.preset/4"`; `preset.uses_media(doc: dict) -> bool` (the rule in Global Constraints).
- Render-side readers (T6/T7) use `renderer.media.frame(c)` and `renderer.media.channels[c].fit`; nothing else.

- [ ] **Step 1: Failing tests** (`tests/test_media_channels.py`, a `FakeSource`/`FakeOpener` counting opens and closes, threads optional):
  - `test_slot_switches_source` — bin a = [x, y]; slot 0 → x open; slot 1 → x closed, y open.
  - `test_rapid_switching_balances` — 500 polls alternating slot 0/1: opens − closes == 1, no `media-` threads beyond one.
  - `test_empty_entry_and_missing_are_black` — `frame("a") is None`, status `missing` for an id the resolver lacks.
  - `test_transport_drives_want` — a timed fake: rate 2, 30 polls of 1/30 → last `want` ≈ 2.0.
  - `test_live_freeze_at_rate_zero`.
  - `test_missing_lists_local_ids` — bins with `local:x.png` (absent) and `shared:y.png` (present) → `["local:x.png"]`.
  - `test_close_closes_all`.
  - (`tests/test_media_preset.py`) `test_bins_round_trip`; `test_preset_without_media_is_unchanged` (save a factory preset on this branch and on the base's writer → identical bytes; compare against a checked-in fixture written before T5 if easier); `test_media_preset_is_v4`; `test_v2_and_v4_both_load`; `test_bmp_file_dropped_with_note` (a doc with `view.bmp_file: "/x.png"` → note text exactly as in Global Constraints); `test_bad_id_in_bin_is_a_note`; `test_channel_params_registered` (48 `media.*` ids, `backdrop.*` 3, `view.media*` 6); undo of a `media.a.slot` change restores the source.
- [ ] **Step 2–4:** run (`uv run pytest tests/test_media_channels.py tests/test_media_preset.py -q`), implement, pass; then the whole suite `uv run pytest -q -x` (the `bmp_*` removal touches `render.py` readers — leave the render face path reading `view.media` with a None texture until T7: `u_bmp_on = 0`; `learn.py`, `ui.py`'s `_page_bitmap` reduced to a note "moved to MEDIA" until T10). **No golden moves.**
- [ ] **Step 5:** commit `"Plan 32 T5: eight channels, their params, the media section and preset/4"`.

---

### Task 6 (T6): Textures, the media node, the backdrop

**Files:** Create `hyperspace/media_tex.py`; Modify `hyperspace/graph.py` (`MediaNode`, `Wiring.backdrop`, `Wiring.backdrop_history`, `default_graph`, wire names), `hyperspace/render.py` (`MediaTextures`, the fit pass, the graph key, SYSTEM timing lines); Test `tests/test_media_render.py`, new goldens.

**Interfaces — Consumes:** T5's `renderer.media` (`frame(c)`, `channels[c].fit`), `ViewState.backdrop*`. **Produces:**
- `media_tex.MediaTextures(ctx)`: `texture(c: str, f: MediaFrame | None) -> moderngl.Texture | None` — (re)allocates on size change, writes only when `(f.frame, f.t)` moved, builds mipmaps; `uploads: int` (count, for tests); `release()`.
- `render.Renderer.media_texture(c: str) -> Texture | None` (raw, for the faces); `Renderer._media_fit(c: str, size: tuple[int,int], alpha: float) -> Texture | None` — one pass into a pool texture, once per frame per (c, size), cover/contain/stretch by `channels[c].fit`, premultiplied by `alpha`.
- `graph.MediaNode(Node)`: `KIND = "media"`, `OUTPUT = IMAGE`, name `media.<c>`, `image(frame)` → `frame.r._media_fit(c, frame.size, alpha)`; `alpha` is `backdrop_alpha` when used as the backdrop, else 1.0 (constructor arg `alpha_of: str | None`).
- `Wiring.backdrop: str = ""` (channel letter or ""), `Wiring.backdrop_history: bool = False`, set by the renderer from `ViewState` each frame and part of the graph key (the graph rebuilds only when they change).
- `default_graph`: with `wiring.backdrop`, `grounded = Composite("grounded", blend="over", over=scene, under=MediaNode(...))`; `History(image=grounded)`; the capture reads `grounded` when `backdrop_history` else `scene` (or the hands composite, as today). Without a backdrop the graph is exactly today's.
- Wire names: `media.a` … `media.h` are valid `from` ends in `_WireCtx` (into `output.<n>.image` and any effect's `image`; `aux` comes in T7).

- [ ] **Step 1: Failing tests:** `test_upload_only_when_frame_moves` (same frame twice → `uploads == 1`); `test_unconsumed_channel_not_uploaded` (channel b playing, nothing reads it → 0); `test_no_backdrop_graph_unchanged` (node names and order equal to the base for the default views); `test_backdrop_under_scene` (a red still on a, `backdrop = 1`: an empty-shape frame's centre pixel is red; with the shape on, a face pixel differs from pure red); `test_backdrop_history_toggle` (capture's input is `scene` when off, `grounded` when on); `test_media_wire_to_output` (wire `media.c → output.1.image` fills the output); `test_fit_modes` (a 2:1 still in a 1:1 frame: contain leaves top rows black, cover does not, stretch fills); `test_render_thread_never_waits` (a fake source whose `latest` is None until a thread sets it after 0.3 s: 20 frames drawn in < 0.3 s total).
- [ ] **Step 2:** goldens: add fixtures `backdrop-still` (a checked-in 256×144 PNG under `tests/golden/media/`) and `media-to-output-2`; record them with the repo's golden tool (see `tests/test_golden_frames.py` for the recording switch); **run the full golden suite: none of the existing ones move.**
- [ ] **Step 3–4:** implement; `uv run pytest -q -x` passes.
- [ ] **Step 5:** commit `"Plan 32 T6: media textures, the media node, the backdrop under the scene"`.

---

### Task 7 (T7): The faces read a channel; the `aux` input; displace and blend

**Files:** Modify `hyperspace/render.py` (`FACE_UNIFORMS`/`FACE_PX`/`_face_uniforms`: `u_bitmap` → the channel `view.media`'s raw texture via `media_texture`), `hyperspace/fx.py` (header declares `u_aux`, `u_aux_on`, `u_aux_size`; `run_one(..., aux: Texture | None = None)` binds it on unit 1), `hyperspace/graph.py` (`Effect.INPUTS = {"image": IMAGE, "aux": IMAGE}`, `aux` in `REFS`, wire `to: "<effect>.aux"`), `hyperspace/shaders/fx/_lib.glsl` (helpers), Create `hyperspace/shaders/fx/displace.glsl`, `hyperspace/shaders/fx/blend.glsl`; Test `tests/test_media_faces_aux.py`, goldens.

**Interfaces — Produces:**
- GLSL in `_lib.glsl`: `vec4 aux(vec2 uv)` (transparent black when `u_aux_on == 0`, mirrored edges like `src`), `float aux_luma(vec2 uv)`.
- `displace.glsl`: `@label Displace`, params `u_amount 0 0.5 0.05 "Amount"`, `u_mode @param choice "luma" "red/green"`, `u_angle 0 6.2832 0 "Angle"` (luma mode direction).
- `blend.glsl`: `@label Blend`, `u_mode @param choice "over" "multiply" "screen" "difference" "luma key"`, `u_key 0 1 0.5 "Key"`, `u_soft 0 0.5 0.1 "Softness"`; the effect's own `mix` fader is the blend amount.
- Faces: `view.media` 1–8 shows that channel's raw texture exactly where the bitmap was (same path/scale/alpha maths, `media_*` params). A face program that never declared `u_bitmap` (a user edit) still builds.

- [ ] **Step 1: Failing tests:** `test_faces_show_channel` (a red still on c, `view.media = 3`: the face centre is red-tinted; `view.media = 0`: identical to no media); `test_unwired_aux_reads_black` (blend over with nothing on aux = the input unchanged); `test_aux_wired_from_channel` (wire `media.a → blend.aux`, mode over, mix 1 → the still); `test_displace_moves_pixels` (a gradient aux displaces a checker; centre pixel differs); `test_aux_refusal_is_a_note` (wiring `aux` from a `MASK` node → note, default graph); `test_old_effects_still_compile` (every existing `.glsl` builds with the new header).
- [ ] **Step 2:** goldens `faces-media`, `blend-luma-key`, `displace-luma` from the checked-in still; existing goldens unchanged.
- [ ] **Step 3–4:** implement; full suite passes. **Step 5:** commit `"Plan 32 T7: faces read a channel; every effect gets an aux input; displace and blend"`.

---

### Task 8 (T8): Live sources — NDI in (first), Syphon in, cameras

**Files:** Create `hyperspace/media/live.py` (shared base), `hyperspace/media/ndi.py`, `hyperspace/media/syphon.py`, `hyperspace/media/camera.py`; Modify `hyperspace/devices.py` (`kinds()` gains `"ndi"`, `"syphon"`, `"camera"`; `DeviceRegistry.media_feeds() -> dict[str, Source]` beside `clouds()`), the factory `config.toml` template in `config.py` (commented entries for all three, `enabled = true`); Test `tests/test_media_live.py`.

**Interfaces — Consumes:** `m0-findings.md` (T0) for the exact Syphon/NDI calls; T1's `Source`, `Latest`, `MediaFrame`, `CAP_LIVE`. **Produces:**
- `live.LiveSource(sid: str, reader)`: own thread `media-live-<sid>`; `latest()` returns the last frame while `now - f.t ≤ 1.0`, else None and status `lost`; `timed = False`.
- `live.LiveKind(devices.Base)`: one device per kind entry; `poll` rediscovers every 2 s on the pool (never on the frame thread); `feeds() -> dict[str, LiveSource]` (opened on first ask by a channel, closed when no channel holds it for 5 s); `status` `connected — <n> feeds` / `lost` / `error: …` (library missing: `error: cyndilib not installed` etc.); `last` names the newest feed.
- `ndi.NdiKind(LiveKind)` `kind = "ndi"`, entry `extra_ips: list[str]` passed to the finder; ids `ndi:<sender name>`.
- `syphon.SyphonKind(LiveKind)` `kind = "syphon"`; ids `syphon:<app>/<server>`.
- `camera.CameraKind(LiveKind)` `kind = "camera"`; lists AVFoundation video devices (pyobjc `AVCaptureDevice`), opens with PyAV `format="avfoundation"`, `framerate=30`, `video_size=1280x720`; permission denied → `error: camera permission (System Settings ▸ Privacy & Security ▸ Camera)`.
- `MediaState`'s resolver (`app.py`) answers `live(sid)` from `DeviceRegistry.media_feeds()`.

- [ ] **Step 1: Failing tests** with a fake reader: `test_live_holds_then_black` (frames stop → `latest` non-None for 1.0 s then None, status `lost`); `test_sender_returns` (frames resume → `ready` with no reopen); `test_discovery_off_the_frame_thread` (a discover that sleeps 0.5 s: `poll` returns in < 10 ms); `test_feed_closed_when_unheld`; `test_missing_library_is_an_error_status`; `test_ndi_loopback` (skip unless `cyndilib` imports: our sender `RIG` → `ndi:RIG` frame within 3 s); `test_syphon_loopback` (skip unless `syphon` imports and a GL context can be made).
- [ ] **Step 2–4.** **Step 5:** commit `"Plan 32 T8: live sources — NDI in, Syphon in, cameras — on the device registry"`.

---

### Task 9 (T9): Out — outputs published over Syphon and NDI

**Files:** Create `hyperspace/media/publish.py`; Modify `hyperspace/config.py` (`[output]` / `[[output.screens]]` keys `syphon: str`, `ndi: str`, `window: bool = true`), `hyperspace/outputs.py` (publish-only views: an offscreen target at the configured size), `hyperspace/render.py` (after each output is composed, hand its frame texture to its publishers); Test `tests/test_media_publish.py`.

**Interfaces — Produces:** `publish.Publisher` Protocol `publish(tex: moderngl.Texture, t: float) -> None`, `close()`, `status: str`, `fps: float`, `readback_ms: float`; `publish.SyphonOut(name: str, ctx)`; `publish.NdiOut(name: str, ctx)` — two pixel-pack buffers alternating (`tex.read_into(buf)` this frame, the other buffer's bytes sent), the send on thread `media-ndi-out-<name>`, a frame dropped (never queued) when the sender is busy. SYSTEM gains one line per publisher: `<kind> out <name> — <fps> fps, readback <ms> ms`.

- [ ] **Step 1: Failing tests:** `test_config_reads_publish_keys` (and a bad type is a config note); `test_publish_only_output_has_no_window`; `test_ndi_out_never_blocks` (a fake sender sleeping 100 ms: 30 publishes take < 50 ms in all, frames dropped); `test_ndi_out_loopback` (skip unless `cyndilib`: our `RIG` out read back by T8's receiver with matching mean colour); `test_syphon_out_loopback` (skip unless `syphon`).
- [ ] **Step 2–4.** **Step 5:** commit `"Plan 32 T9: outputs published over Syphon and NDI, publish-only outputs"`.

---

### Task 10 (T10): The MEDIA page and GRAPH's media area

**Files:** Create `hyperspace/ui_media.py`; Modify `hyperspace/ui.py` (the `bitmap` tab becomes `media`, drawn by `ui_media.draw(ui, dt)`), `hyperspace/graphview.py` / `hyperspace/ui_graph.py` (a titled "media" area: eight `media.<c>` source nodes, the backdrop, `aux` ports); Test `tests/test_ui_media.py`, extend `tests/test_graphview.py`.

**Interfaces — Consumes:** `MediaState` (T5), `MediaFolder` (T4), `DeviceRegistry.media_feeds()` (T8), the registry params. The page only reads state and writes params / calls `assign`, `add_file`, `copy_to_shared`; it never opens a source itself.

Layout (spec section U): the missing banner (one line per id, "not on this Mac — shows black") at the top while `MediaState.missing()` is non-empty; the library (Shared / This Mac / Live tabs, thumbnails, status chips, a search box, **Add file…** via the existing file dialog path in `ui.py`, **Copy to shared**); the eight channel columns (live thumbnail from the channel's texture, the bin as 16 cells — click a library item then a cell to assign, right-click a cell to clear — the slot, rate, a pos bar with the playhead, jog, loop, fit, status); the backdrop and faces channel pickers; a hint "Learn the cue knob to `media.<c>.jog`".

- [ ] **Step 1: Failing tests** (the shell test harness of `tests/test_ui_shell.py`): `test_media_tab_replaces_bitmap`; `test_banner_lists_missing`; `test_assign_from_library` (simulated clicks → `bin[0]` set); `test_page_never_opens_sources` (an opener that raises if called from the UI); `test_graph_has_media_area` (eight nodes, wire from `media.a` drawn when wired).
- [ ] **Step 2–4.** **Step 5:** commit `"Plan 32 T10: the MEDIA page and GRAPH's media area"`.

---

### Task 11 (T11): Docs

**Files:** Modify `docs/plans/32-media-channels.md` (status "built", what was built per WP with commits, rough edges), `docs/DECISION-REGISTER.md` (rows 321–339 in the house format: Answer / Built / Other options / To reverse / Rough edge / Judge it), `docs/DECISIONS.md` (a "Media" section), `docs/ARCHITECTURE.md` (the media package and its threads), `docs/ENGINEERING.md` (both Macs on this build for `/4` presets; the dependency list), `docs/plans/11-hand-checks.md` (group AA from 296: a still/video backdrop, scrub and jog with the cue knob, a dropped file appearing, a missing-local banner on the other Mac, NDI in from Resolume and from TouchDesigner on a second Mac, Syphon in, Syphon/NDI out into Resolume, a webcam, the phone through an NDI camera app — after the sprint), `docs/TESTING-GUIDE.md` if it lists suites, `docs/plans/README.md` entry updated.

- [ ] **Step 1:** write them; **Step 2:** `uv run pytest -q` full suite passes, golden count reported; **Step 3:** commit `"Plan 32 T11: the docs — as built, rows 321–339, hand checks group AA"`.
