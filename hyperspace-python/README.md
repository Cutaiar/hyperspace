# Hyperspace (Python)

The active re-platform of Hyperspace: a real-time 4D polytope visualizer with
audio-reactive rotation. Replaces the original single-file
[`hyperspace-web/`](../hyperspace-web/) version, which is preserved for
reference and used as the renderer test oracle.

## Quickstart

Requires macOS with [`uv`](https://docs.astral.sh/uv/) installed
(`brew install uv`). Setting up a new Mac — microphone permission,
capturing the Mac's own sound, the APC40, the Ultraleap hands, FL Studio
over IAC, a second screen — is [`docs/SETUP.md`](docs/SETUP.md).

```bash
uv sync
uv run pytest -q       # the test suite
uv run hyperspace      # opens the render window and the control window
```

The manual — every config key, page, key binding, the APC40 map, the
files the app keeps in `~/Hyperspace` — is
[`docs/ENGINEERING.md`](docs/ENGINEERING.md).

### Dream worker

The look-back's Deep Dream worker is part of the app: `uv sync` installs
torch with everything else, and `[dream] enabled` defaults to on. The
pretrained weights are read from `~/Hyperspace/weights`, else torch's hub
cache, and downloaded there on first use. If the worker cannot start the
app runs the echoes alone and says why — the red banner at the bottom of
the control window, the SYSTEM page and the LOOKBACK page. Turn it off
with `[dream] enabled = false`.

### When the render freezes

The app keeps `~/Hyperspace/stall.log`: a 2 s stall of the whole loop, a
render draw that raised, a render output that stopped presenting for 2 s
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
- `docs/` — [`SETUP.md`](docs/SETUP.md) a new Mac,
  [`ENGINEERING.md`](docs/ENGINEERING.md) the manual,
  [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) the structure,
  [`DECISIONS.md`](docs/DECISIONS.md) and
  [`DECISION-REGISTER.md`](docs/DECISION-REGISTER.md) the reasons,
  [`TESTING-GUIDE.md`](docs/TESTING-GUIDE.md) what a person still has to
  check, [`AUDIT-2026-09.md`](docs/AUDIT-2026-09.md) the open findings,
  and [`plans/`](docs/plans/) short records of what each recent plan built
  and the numbered hand checks.

## Re-recording golden traces

The `record_golden.py` and `compare_render.py` tools drive
`hyperspace-web/hyperspace.html` in headless Chromium. To run them:

```bash
uv run playwright install chromium   # one-time, ~150 MB
uv run python tools/record_golden.py
```

Consuming committed traces (which `pytest` does) needs neither Playwright nor
Chromium.

## Operating it

Everything the panel can set is a named parameter in `hyperspace/params.py`
(`view.bright`, `band.2.atk`, …). Keys, the gamepad, MIDI, the hands and
the analyzer's lanes all drive those parameters through one binding table
(`hyperspace/routing.py`), so any audio band, hand axis or LFO can
modulate any parameter. Press `/` in the app for the cheat sheet;
right-click any control in the panel to learn a desk control or a hand
onto it, or to unbind it.

A **preset** is one whole performance moment — the look, its routes, the
APC40's preset layer and the macros — and a load replaces all of it
without touching the session (tempo, the hands' feel, the analyzer, the
outputs). A **show** holds the session, the preset it starts on and a
bank of twenty-four presets: F1–F8 and the APC40's clip rows 1, 4 and 5
load them. Factory presets and shows live in `hyperspace/library/`;
yours go in `~/Hyperspace` (or `$HYPERSPACE_HOME`) in the same tree, as
plain JSON the running app follows when you edit it.

The control window has fourteen pages — Output · View · Faces · Bitmap ·
Camera · Lookback · FX · Audio · Analyzer · Routing · LFO · Hands ·
Presets · System. The render window is pure output; more render outputs,
overlay mode, the APC40's two layers and everything else are in
[`docs/ENGINEERING.md`](docs/ENGINEERING.md).
