# Plan 00 — Golden traces

**Blueprint stage 0.** Set up the Python scaffold and record the reference
behaviour of `hyperspace.html` that plans 01–02 must reproduce. This is the
only plan in which the HTML file is ever executed.

## Prerequisites

None. This is the starting point.

## Deliverables

```
pyproject.toml               # uv-managed package, python >=3.12
hyperspace/__init__.py       # empty package
tools/gen_test_audio.py      # generates the test WAVs
tools/record_golden.py       # playwright harness driving hyperspace.html
tests/golden/
  geometry/<shape>.json      # projected vertex positions at fixed angles
  audio/<clip>.jsonl         # per-frame chain state for each test clip
  audio/manifest.json        # clip → sha256, duration, settings used
```

## Tasks

### 1. Scaffold

`uv init` the package per the layout in BLUEPRINT §7. Add `numpy`, dev-deps
`pytest`, `ruff`, `playwright` (with chromium installed). CI is optional at
this stage; `pytest` must at least run locally.

### 2. Test audio

Port the proven techniques from ENGINEERING §6 into `tools/gen_test_audio.py`:

- **gate-prover.wav** — 50 Hz + 3 kHz mix: isolates SUB/BASS and UPR, leaves
  MIDB/MID/AIR at exactly zero. Proves the gate.
- **brickwalled.wav** — the synthetic limited track (full-band, near-zero
  crest factor). Exercises the dynamics-recovery path.
- **sweep.wav** — 20 Hz → 14 kHz log sweep, constant power. Exercises every
  band boundary in sequence.
- **real.mp3** — one real commercial track, user-supplied, **not committed**;
  referenced by sha256 in `manifest.json` so traces are reproducible for
  whoever holds the file.

### 3. Geometry traces (deterministic, exact)

For each of the 18 shapes: via `page.evaluate`, select the shape, set the six
`S.ang` values and the view yaw/pitch to fixed constants, invoke a single
render pass, and read back the projected 2D positions plus the post-rotation
w values for every vertex. Top-level `const` bindings in the page script
(`S`, `cache`, `PLANES`) are reachable from `evaluate` by name — no HTML
modification is needed or allowed. Record at 3 angle sets per shape.

### 4. Audio traces (time-series, tolerance-based)

Drive the file-playback path: `uploadFile` a WAV into `#fileIn`, then install
a per-frame sampler (wrap the page's rAF callback from `evaluate`) recording
`{t, AUDIO.inp[6], AUDIO.out[6], PLANEDRIVE[6]}` to an array; dump JSONL at
clip end. Launch chromium with `--autoplay-policy=no-user-gesture-required`
and a fixed window size. Record each clip **twice**; the run-to-run delta
defines the noise floor and is stored in the manifest — plan 01's tolerances
are set relative to it, not invented.

Record with all-default settings (Balanced scene), and one extra run of
`brickwalled.wav` with the Dynamics slider at 0 and at 1, since that path is
the chain's reason to exist.

## Exit criteria

- [ ] `uv run pytest` passes (even if only scaffold tests exist).
- [ ] Geometry traces exist for all 18 shapes and are byte-stable across two
      recording runs (they are deterministic; any diff is a harness bug).
- [ ] Audio traces exist for all four clips; the measured run-to-run noise
      floor is recorded in `manifest.json` and is small enough to be usable
      (frame-aligned RMS delta of `AUDIO.out` between the two runs < 0.05 —
      if it isn't, fix the harness's timing before proceeding).
- [ ] `tests/golden/` is committed (minus the real track itself).

## Risks / notes

- rAF timing makes audio traces jittery. Mitigations, in order: fixed window,
  no other tabs, sampling tied to the page's own rAF (not the harness's
  clock), and tolerance-based comparison downstream. If jitter still swamps
  the signal, fall back to `--run-all-compositor-stages-before-draw` style
  deterministic-frame flags, and note what was done in the manifest.
- The old container harness (ENGINEERING §6) used puppeteer-inside-mermaid-cli
  because that's what the container had. On this machine use playwright's own
  chromium — same techniques, supported install.

## Results (2026-08-21)

Executed on the primary Mac (Apple Silicon, headless Chromium 151 via
playwright). All exit criteria met except the user-supplied real track:

- **Scaffold:** `uv sync` from `pyproject.toml` + committed `uv.lock`;
  `uv run pytest` → 20 passed (`tests/test_golden.py` validates the traces
  against the ENGINEERING §2 V/E table, unit circumradius, and the manifest).
- **Geometry:** 18 shapes × 3 views at 1200×800, including full constructed
  `V`/`E` arrays (plan 01 gets construction parity for free). Byte-stable
  across two recording runs. 564 KB committed.
- **Audio:** three generated clips (sha256 in the manifest; regenerate with
  `tools/gen_test_audio.py`, fixed seed). Headless rAF ran at ~120 fps —
  the chain is dt-based, so cadence is recorded per-sample, not assumed.
  Run-to-run noise floors, all under the 0.05 budget:
  | clip | run | frames | noise floor (RMS) |
  |---|---|---|---|
  | gate-prover | default | 1500 | 0.0381 |
  | brickwalled | default | 1500 | 0.0222 |
  | brickwalled | dyn0 | 1501 | 0.0142 |
  | sweep | default | 1500 | 0.0066 |
- **Gate proof in the traces:** on gate-prover, settled means — SUB 0.94,
  UPR 0.54, BASS 0.52 (leakage + coupling), MIDB/MID/AIR exactly 0.0000.
- **Outstanding:** `real.mp3` (user-supplied) not yet recorded — drop the
  file in `tests/fixtures/`, uncomment its row in `AUDIO_RUNS` in
  `tools/record_golden.py`, and re-run `audio` mode.
