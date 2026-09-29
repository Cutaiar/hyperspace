# Hyperspace (Python)

The active re-platform of Hyperspace: a real-time 4D polytope visualizer with
audio-reactive rotation. Replaces the original single-file
[`hyperspace-web/`](../hyperspace-web/) version, which is preserved for
reference and used as the renderer test oracle.

## Quickstart

Requires macOS with [`uv`](https://docs.astral.sh/uv/) installed
(`brew install uv`). Full prerequisite checklist — including audio routing,
DJ-link, and DAW-bridge tiers — is in [`docs/SETUP.md`](docs/SETUP.md).

```bash
uv sync
uv run pytest          # ~930 tests, ~35 s
uv run hyperspace      # opens the render window and the control window
```

### Dream worker (optional)

The look-back's Deep Dream worker needs **torch**, which is not part of a
plain install: it is the `dream` extra (torch, torchvision, and on macOS
mlx and the Metal / Quartz bindings — about 800 MB).

```bash
uv sync --extra dream                  # installs torch and the rest of the extra
uv run --extra dream hyperspace        # launch with it
```

and `[dream] enabled = true` in `~/Hyperspace/config.toml` (off by
default). Once installed, a plain `uv run hyperspace` keeps it (`uv run`
only adds what is missing), but a plain **`uv sync` removes it again** —
`uv sync` makes the environment exactly the lock without extras. Run
`uv sync --extra dream` whenever you sync. The pretrained weights (VGG16,
528 MB) are read from `~/Hyperspace/weights`, else torch's hub cache, and
downloaded there on first use otherwise. With `[dream] enabled = true`
and no torch the app runs the plain tracer and says why — the red banner
at the bottom of the control window, the SYSTEM page and the LOOKBACK
page all read "dream worker off: torch is not installed — run `uv sync
--extra dream`, then launch with `uv run --extra dream hyperspace`".

### When the render freezes

The app keeps `~/Hyperspace/stall.log`: a 2 s stall of the whole loop, a
render draw that raised, a render window that stopped presenting for 2 s
while the panel runs, and a frame that began on a stranded framebuffer
each append every thread's stack, with the time and the loaded preset.
`kill -USR1 $(pgrep -f "bin/hyperspace")` from another terminal dumps
on demand. The SYSTEM page shows the log's line once it has entries; a
live render error is a red banner at the bottom of the control window.

## Layout

- `hyperspace/` — the package, one process. In the middle, the parameter
  registry (`params`, `tapers`) that every input path drives; around it
  the routing table (`routing`, the referee and the per-frame modulation
  pass; `learn` holds an armed Learn for MIDI and hands alike), the
  sources (`audio` + `analysis` + `analyzer` + `bands`; `lfo` + `tempo`;
  `hands/`; `bridge`), the input adapters (`midi` + `apc40`, `gamepad`),
  the render stack (`geometry`, `view`, `render`, `glsl`, `fx`, `lookback`,
  `dream`, `overlay`, `shaders/`), the panel (`ui`, `ui_bands`,
  `ui_routing`, `ui_lfo`, `ui_fx`, `ui_lookback`, `ui_presets`,
  `hands/panel`, `control`), the library (`library`, `preset`, `config`,
  `library/` with the factory presets) and the host (`app`, `hotreload`). Who owns
  what and who may write a parameter: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
- `tests/` — pytest suite plus committed `golden/` traces recorded from
  `hyperspace-web/hyperspace.html` (the oracle for geometry and audio
  parity) and `legacy_chain.py`, the frozen six-band chain the analyzer
  reproduces bit for bit.
- `tools/` — `record_golden.py` (re-records goldens via Playwright against
  the HTML oracle), `compare_render.py` (side-by-side diff),
  `gen_test_audio.py`, `midi_probe.py` (echoes what a controller sends;
  lights an APC40), `hands_probe.py` (every hand axis live; `--calibrate`
  sweeps the box), `control_shots.py` / `fx_shots.py` / `lookback_shots.py`
  / `dream_shots.py` (screenshots for the docs) and `dream_bench/`.
- `docs/` — [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) is the structure,
  [`ENGINEERING.md`](docs/ENGINEERING.md) the behaviour,
  [`DECISIONS.md`](docs/DECISIONS.md) the reasons, [`BLUEPRINT.md`](docs/BLUEPRINT.md)
  the design north star, [`CHECKPOINT.md`](docs/CHECKPOINT.md) the pick-up
  list, [`AUDIT-2026-09.md`](docs/AUDIT-2026-09.md) the register of what
  drifted, and [`plans/`](docs/plans/) the stages the re-platform ran in.

## Re-recording golden traces

The `record_golden.py` and `compare_render.py` tools drive
`hyperspace-web/hyperspace.html` in headless Chromium. To run them:

```bash
uv run playwright install chromium   # one-time, ~150 MB
uv run python tools/record_golden.py
```

Consuming committed traces (which `pytest` does) needs neither Playwright nor
Chromium.

## Controls and MIDI

Everything the panel can set is a named parameter in `hyperspace/params.py`
(`view.bright`, `band.2.atk`, `preset.load.0`, …). Keys, the gamepad, MIDI
and the analyzer's lanes are one binding table over that registry
(`hyperspace/routing.py`) — so a value moved from any of them shows
on the panel the next frame, and any audio band can modulate any param.
The session's controls (keys, pad, the APC40's fixed rows) persist in
`bindings.json` (factory default `hyperspace/bindings.default.json`); the
routes, the APC40's preset layer and the macros belong to the loaded
preset.
Press `?` in the app for the cheat sheet.

Plug in an Akai APC40 and it is picked up on launch (and on reconnect):
it has two layers under a latched SHIFT (its LED lit while the global
layer is up). The faders (per-band output drive, dynamics, trim, the
MASTER drive), the first clip row (the preset bank), SHIFT, the clock
buttons and the transport mean the same on both. The **preset** layer is
the loaded preset's — by default the track knobs are the view faders and
the grid holds the shapes; the **global** layer (SHIFT) puts the open
band strip on the device knobs, hand feel and BPM on the track knobs and
the band scenes on the grid. A control the up layer does not map is dark
and does nothing; every LED and knob ring tracks the engine. The full
default layout is at the bottom of `hyperspace/apc40.py`.

To rebind anything: right-click the control in the panel → **Learn**,
then move a knob, press a button — or move a hand, with the tracker on.
A learn goes into the loaded preset (its dirty dot lights; ⇧F or the
preset strip's save writes it); with SHIFT latched, or on a fixed
control, it is refused and the panel says why. `bindings.json` in the
library home holds the session's controls (delete it to get the defaults
back; a pre-2026-09 `midi_map.json` there is merged into it once and then
ignored). Faders use soft pickup — after a preset load a fader does
nothing until it sweeps through the current value; the knobs are endless
and continue from their ring. An optional `config.toml` names the port
and profile, or disables the adapter (see `hyperspace/config.py`); MIDI
and the gamepad are the two adapters on by default (`[gamepad] enabled =
false` stops polling for a pad), the bridge, dream and hands are off.

## Presets, projects and the library

A **preset** (`presets/*.json`) is one whole performance moment: every
performance parameter (view, rotation, camera, patterns, dream, FX, LFOs,
macros), the hand / audio / LFO routes, the APC40's preset layer and the
macros' subscribers; loading one replaces all of it and never touches
the session (tempo, hands, the analyzer, output). A *project*
(`*.hyp.json`) is the session: its values, a startup preset, and the
F1–F8 bank of eight preset names (F-key loads, ⇧F-key saves the live
state as that preset). Every registry group (view, camera, band…) also
keeps its own module presets, which replace only that group. Factory presets live in `hyperspace/library/`; yours go in
`$HYPERSPACE_HOME` (default `~/Hyperspace`) in the same tree, with
`projects/`, `bindings.json` and `config.toml` next to them — a user file
shadows a factory file of the same name. The first launch of a build
from plan 13 on converts an older home once (old projects, routing
presets and `bindings.json`'s routes become presets), keeping a
`.bak-v<n>` of every file it rewrites. The files are plain JSON: edit one
in a text editor while the app runs and the loaded preset updates in place.
See `hyperspace/library.py` and `hyperspace/preset.py` for the formats
and the API the panel uses.

The panel is a rail of fourteen pages — Output · View · Faces · Bitmap ·
Camera · Lookback · FX · Audio · Analyzer · Routing · LFO · Hands ·
Presets · System — and every page that is a registry group carries its
preset strip: `◀ name ▶`, save, save-as, reset, and a red dot once the
group has moved off its preset. The Presets page holds the project row
(save / save-as / load / new, the startup preset), the F1–F8 preset bank
and the preset strip; the Routing page is one page over the loaded
preset — its routes, desk rows and macros, the session's MIDI rows
read-only; the LFO page
the clock and the four LFOs; the Hands page the tracker, the box and the
axis setups. A param a performer is driving shows its *setting* as the
handle and the *effective* value as a white ghost bar, and names the
performer in its tooltip. No page scrolls at the control size; a test
holds it.

## Two windows: output and controls

The *render* window is pure output — what goes on the projector or TV —
and the *control* window holds the panel, the cheat sheet and the
hot-reload notices. Keys work from either; the mouse orbits, pans and zooms
in the render window. The panel's Output section (`output.monitor`,
`output.fullscreen`, `output.overlay`, `output.passthrough`, `output.bg`,
`output.alpha`, all learnable) says where the render window goes:
fullscreen on a chosen screen, or overlay mode.

**Overlay mode.** Press `T` (or the APC40's master-select button) and the
render window drops its frame, covers the screen, sits above everything —
including another app's fullscreen video on macOS — and clears to
see-through, so only the shape is drawn over what is behind it. Clicks pass
straight through to the window underneath, so you can run the video behind
as normal; that also means the render window never takes focus — keys keep
working from the control window, and `G` (or the APC40's pan button) takes
clicks back for orbiting. The crossfader fades the ground from see-through
to black. The pre-split `overlay.*` ids remain as aliases, so old MIDI maps
keep working. `[output] fullscreen = true` or `on_start = true` (overlay) in
`config.toml` launches straight into a mode; `monitor = 1` picks the screen
(`-1`, the default, follows the window — the SYSTEM page says "follow window").
An older `[overlay]` section is read as the same thing (with a note asking
for the rename); the keys are documented in `hyperspace/config.py`.
