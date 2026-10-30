---
name: drive-the-app
description: See a Hyperspace change working without a person at the rig — render frames offscreen, drive the real panel with the mouse and keys by control id, capture both windows, cut a demo video. Use when asked to demo, screenshot, record or check by eye a change to the renderer or the panel, in a cloud session or on the Mac.
---

# Drive the app

Three tools, lightest first. Pick the one that answers the question; a
picture is not a test, so when an assertion can say it, write the
assertion.

## 0. The machine

On the Mac, `uv sync` and go. In a cloud session the setup hook
(`.claude/hooks/session-start.sh`, registered in `.claude/settings.json`)
makes the machine CI tests on. If it did not run:

```bash
apt-get install -y --no-install-recommends libasound2-dev libportaudio2 libgl-dev \
  libgl1-mesa-dri libglx-mesa0 libegl1 xvfb xauth fonts-dejavu-core glslang-tools
export UV_NO_GROUP="hands dream"     # keep it set: `uv run` re-syncs the groups otherwise
cd hyperspace-python && uv sync --locked
Xvfb :99 -screen 0 1920x1080x24 & export DISPLAY=:99
```

The fast tier (`uv run pytest -q`) is green there; a red test is yours.

## 1. Pictures of the renderer: offscreen

`moderngl.create_context(standalone=True)`, a framebuffer, `Renderer.draw`
with `t_now` pinned — no window, no panel, deterministic. For a strip of
states or a quick look at a layout. Examples: `tools/instances_shots.py`,
`render.render_offscreen`. Advance rotation with `ViewState.integrate(dt)`
yourself, at the video's frame rate.

## 2. A panel control in a test: `tests/ui_driver.py`

The headless rig (`tests/test_ui_shell.build_rig`) plus a `Driver`:

```python
d = Driver(step=lambda: frame(r.panel, "view"))
d.record(monkeypatch.setattr)            # notes every widget's rect by its id
d.run(d.click("view.inst_fit"), d.park())
d.run(d.pick("view.inst_layout", NAMES.index("FCC")))
d.run(d.enter("view.instances", 12))
```

`tests/test_ui_driver.py` is the worked example. Prefer it to a new
`_click` helper and a hand-wrapped widget in a test file.

## 3. The whole app: `tools/app_driver.py`

```bash
uv run python tools/app_driver.py tools/drive_instances.py --out <scratch>/run
```

The real app, a script of the same `Driver` actions stepped once a frame by
the app's own loop; every 2nd frame of each window lands in
`<out>/<window>/NNNNN.png`, with `frames.json` (frame, window, mouse — imgui
draws no cursor, so overlay one from it). `tools/drive_instances.py` is the
worked example.

## Driving rules

- **Find controls by id**, never by coordinates: the text after `##` —
  the param id for everything `ui.py` draws for a param; page tabs are
  `page<n>` (`PAGE_KEYS.index("view")`). A missing id raises with what was
  drawn: read it, it names the right one.
- **Menus and exact values by keyboard**: `pick` opens a combo and walks
  it with the arrow keys; `enter` Ctrl+clicks a slider and types. A tapered
  slider takes its detent, not its readout (`view.instances`: 153 is 299).
  `slide` is for showing a drag, not for landing a value.
- **Input lands a frame late**; every action yields between move, press
  and release. Do not set a value and read it back in the same frame.
- **`park()`** after an action, or a tooltip covers the next shot.

## A known start

- `app_driver.py` makes a fresh home seeded with the test corpus (the
  party show opens) and a config with no devices and no dream. An empty
  home (`--empty`) opens an unwired preset: the output is black, by design.
- A show or preset brings its own camera: set `camera.zoom`, `yaw`,
  `pitch`, `pan` in the script before judging framing (a show left zoom at
  1.3 once and cropped every fitted field in a demo).
- Load another preset with `panel.presets.load(name)`.

## A video

```bash
ffmpeg -framerate 30 -i run/controls/%05d.png ...        # or compose frames in PIL first
ffmpeg -i in.mp4 -c:v libx264 -preset slow -b:v 3200k -pass 1 -an -f null /dev/null
ffmpeg -i in.mp4 -c:v libx264 -preset slow -b:v 3200k -pass 2 -pix_fmt yuv420p \
  -movflags +faststart out.mp4
```

Dense wireframes are noise to an encoder: constant quality made 270 MB of
2½ minutes; two-pass at ~3 Mbps made 60 MB that reads the same. Keep
videos out of the repository — send the file to the person.

## What a headless run cannot tell you

- **Speed.** Off the Mac, GL is Mesa's software rasteriser: the app's FPS
  readout (~20) and `PassTimer`'s GPU times say nothing about the rig.
  Measure CPU-side cost by stubbing the draw calls; leave frame rate to a
  hand check on the Mac (`docs/TESTING-GUIDE.md`).
- **Golden frames** run on "Apple M3 Max" only and skip elsewhere.

## Not this way

- **Dear ImGui Test Engine.** It is in imgui-bundle, and it drives widgets
  by label — but from Python only under imgui-bundle's own runners
  (HelloImGui, ImmApp): its scripts run on a second thread and need the GIL
  handed over from C++. Started from the app's own GLFW loop it deadlocks
  in the first `new_frame` (tried 2026-10-30). `ui_driver` is the
  stand-in.
- **Coordinates and feedback loops on sliders**, the way demos were driven
  before `ui_driver`: they miss by a row, overshoot, and break when the
  layout moves.
