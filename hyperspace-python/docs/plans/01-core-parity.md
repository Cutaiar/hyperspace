# Plan 01 — Core parity (geometry + audio chain, headless)

**Blueprint stage 1.** Port the two subsystems that carry all the accumulated
correctness — the shape constructions and the six-band chain — and prove them
against the plan-00 traces. No window, no live audio, no UI.

## Prerequisites

Plan 00 complete: scaffold, test WAVs, golden traces committed.

## Deliverables

```
hyperspace/geometry.py    # 18 shapes, edge recovery, normalisation, cache
hyperspace/analysis.py    # Web-Audio-equivalent FFT front end
hyperspace/bands.py       # the full chain: envelopes, shapers, scenes, tapers
tests/test_geometry.py
tests/test_analysis.py
tests/test_bands.py
```

## Tasks

### 1. `geometry.py`

Transliterate from `hyperspace.html` into numpy: `expand` (index permutations
× sign changes with dedup), `cyc3`, `prism`, `duoprism`, `edgesByMinDist`,
unit-circumradius normalisation, lazy build + cache. Keep the shape order (the
slider index — ordered by cell count, ENGINEERING §2). Output arrays:
`float64` vertices `(V,4)`, `int32` edges `(E,2)` — same data model, numpy
shapes.

Also port the pure transform pipeline as free functions (no GL): six-plane
rotation matrix composition from `PLANES = [[0,1],[0,2],[1,2],[0,3],[1,3],[2,3]]`
and angles, 4D→3D projection `k = D4/(D4 − w)`, yaw/pitch view, 3D→2D
projection. Plan 02 wraps these in GL; the parity test exercises them here.

### 2. `analysis.py` — replicate AnalyserNode, not "an FFT"

Every ported constant assumes Web Audio semantics. Implement exactly:
`fftSize = 4096`, **Blackman window**, magnitude smoothing
`s[k] = 0.15·prev[k] + 0.85·|X[k]|` applied in linear magnitude before dB
conversion, dB per the `getFloatFrequencyData` definition. Band → bin ranges
computed identically to the HTML (same rounding). Feed it hops matched to the
frame cadence the traces were recorded at (~60 Hz).

Verify against a synthesized single-tone WAV: bin magnitudes within 0.5 dB of
the values the HTML reports for the same file (spot-check via the plan-00
harness if needed).

### 3. `bands.py` — the chain, verbatim

Port per ENGINEERING §4, keeping the constant *names* (`NOM`, `KNEE`, `CEIL`,
`WARM_F`, `DEV_AIM`, `OPEN_SPAN`, `CONF_LO`, `CONF_SPAN`, `PK_MIN`,
`PIN_HOLD`, `U_SPAN`…) so the two implementations stay diffable:

- power-sum RMS → dB → `u`; LEVEL path (asymmetric one-pole with per-band
  attack/decay, peak/valley window, confidence + gate, upward expansion about
  the running mean) and TRANSIENT path (fast − slow envelope, relative flux,
  peak-normalised); per-band blend (`trn`).
- harmonic coupling (octave-coherence proxy, input side) → pre-drive →
  transfer function → post-drive → `PLANEDRIVE[plane] = dir·out·3.2·gain`.
- `softCeil` as specified — identity below the knee, `knee + r·t/√(1+t²)`
  above. **No hard clamps anywhere.**
- All 13 `SHAPERS` with per-band scratch state; state resets on function
  change. All 11 `PRESETS` including the 6-element back-compat rows. The
  taper objects (`expZero`, `expPure`, `expTime`, `linT`) with
  `unmap(map(p)) == p` exact over every throw.
- Input trim applied twice (pre-`u` and post-tracker), **including its known
  non-monotonicity** (ENGINEERING §4 warning). Port the bug; fix in plan 06.

### 4. Offline driver + parity tests

A test-only driver feeds a WAV through `analysis.py` → `bands.py` at the
trace cadence.

- `test_geometry.py`: V/E/cell counts match the ENGINEERING §2 table for all
  18 shapes; projected vertex positions match the golden geometry traces to
  1e-9 (both sides are float64 running the same arithmetic).
- `test_bands.py`: for each golden audio clip, after coarse time-alignment
  (max cross-correlation on the SUB `out` series), frame-wise `AUDIO.out` and
  `PLANEDRIVE` agree within **2× the recorded run-to-run noise floor**, and
  summary statistics (per-band mean, sd, min/max of `inp` and `out`) within
  5%. The dyn=0 / dyn=1 pair must reproduce the documented sd spread
  (ENGINEERING §4: BASS 0.018→0.181, MIDB 0.080→0.697, proportionally).

## Exit criteria

- [ ] All parity tests green via `uv run pytest`, on `main` after merge.
- [ ] Geometry parity is exact (1e-9); any looser tolerance is a finding to
      chase, not to accept.
- [ ] A short parity report (which tolerances, which margins) is appended to
      this file's *Results* section when done.

## Risks / notes

- The likeliest parity killer is analyser semantics (window choice, smoothing
  in magnitude vs dB, bin rounding). If band traces diverge, bisect there
  first — the chain math is deterministic once its input matches.
- Two agents porting `analysis.py` and `bands.py` in parallel is fine, but
  the parity numbers only count when measured on the merged build
  (ENGINEERING §10, trap 2).

## Results (2026-08-21)

**Bar change, decided by the user before execution:** frame-level audio
parity was dropped. Geometry stays exact (it's cheap to prove); the audio
chain is ported faithfully but verified by *behaviour* — the documented
gate/dynamics/headroom properties — with the user's eye as the final judge
from plan 02 on. `test_bands.py`/`test_analysis.py` were folded into one
`tests/test_core.py` accordingly. Tapers moved to plan 04 with the UI they
serve.

What was delivered, all criteria met (63 tests green, ruff clean):

- **`geometry.py` — exact parity.** All 18 constructions match the golden
  `V`/`E` arrays to 1e-12 with identical vertex *order* (JS Map insertion
  order == dict insertion order; `kkey` rounding ported half-up, not
  banker's). The full `project()` transform matches every golden view to
  float32-storage precision (the traces went through `Float32Array`).
- **`analysis.py`** — AnalyserNode semantics: fftSize 4096, spec Blackman,
  1/N-normalised rFFT, per-call linear-magnitude smoothing τ=0.15, dB per
  `getFloatFrequencyData`, and the reference's exact band→bin rounding.
- **`bands.py`** — the whole chain under its reference constant names, the
  13 shapers with scratch-state semantics (including JS falsiness in S&H),
  the 11 presets with 6/8/9-element row back-compat, and the trim
  non-monotonicity ported on purpose (plan 06 fixes it).
- **`offline.py`** — WAV → chain driver at a chosen fps, used by the tests
  and later by plan-06 tuning.
- **Behaviour evidence:** gate-prover reproduces the reference exactly in
  kind (SUB/UPR driven, BASS via coupling, MIDB/MID/AIR at literal 0.0 and
  their planes stopped). At the goldens' 120 fps cadence the settled
  per-band sd on brickwalled matches the reference to ±0.08 in *both* dyn
  settings — BASS 0.234/0.196 vs reference 0.235/0.203, UPR matching to
  the third decimal. One real finding: output spread is cadence-sensitive
  through the analyser's per-call smoothing (BASS sd 0.167 @60 fps vs
  0.234 @120 fps), so behaviour comparisons must run at matched fps — and
  plan 03's live loop should expect feel to vary slightly with display
  refresh rate.
