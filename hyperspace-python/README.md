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
uv run pytest          # 172 tests, ~10s
uv run hyperspace      # opens the render window
```

## Layout

- `hyperspace/` — the package: `app`, `render`, `audio`, `geometry`, `bands`,
  `control`, `presets`, `ui`, `hotreload`, `gamepad`, `analysis`, `offline`,
  and `shaders/`.
- `tests/` — pytest suite plus committed `golden/` traces recorded from
  `hyperspace-web/hyperspace.html` (the oracle for renderer parity).
- `tools/` — `record_golden.py` (re-records goldens via Playwright against the
  HTML oracle), `compare_render.py` (side-by-side diff), `gen_test_audio.py`.
- `docs/` — [`BLUEPRINT.md`](docs/BLUEPRINT.md) is the design north star,
  [`ENGINEERING.md`](docs/ENGINEERING.md) is the working reference,
  [`CHECKPOINT.md`](docs/CHECKPOINT.md) is the current pick-up list, and
  [`plans/`](docs/plans/) breaks the re-platform into stages.

## Re-recording golden traces

The `record_golden.py` and `compare_render.py` tools drive
`hyperspace-web/hyperspace.html` in headless Chromium. To run them:

```bash
uv run playwright install chromium   # one-time, ~150 MB
uv run python tools/record_golden.py
```

Consuming committed traces (which `pytest` does) needs neither Playwright nor
Chromium.
