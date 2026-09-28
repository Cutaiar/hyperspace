# Checkpoint — 2026-09-28

Where the Python re-platform stands and what to pick up next. What the
system *is* — the parts, the frame, who may write a parameter — is
[`ARCHITECTURE.md`](ARCHITECTURE.md); how it behaves is
[`ENGINEERING.md`](ENGINEERING.md); why it is that way, dated, is
[`DECISIONS.md`](DECISIONS.md); what drifted and how each item was closed
is [`AUDIT-2026-09.md`](AUDIT-2026-09.md); the stages it was built in are
[`plans/`](plans/README.md). This file keeps only the pick-up list.

## How to pick this up

```bash
git clone github.com/Cutaiar/hyperspace && cd hyperspace/hyperspace-python
uv sync                 # whole environment, from the committed lockfile
uv run pytest           # 772 tests, ~20 s (11 skipped without torch)
uv run hyperspace       # the app: ? shows the controls cheat sheet
```

Machine prerequisites: [`SETUP.md`](SETUP.md). Rig-specific values live in
`~/Hyperspace/config.toml` (documented in `hyperspace/config.py`).

## Where it stands

Plans 00–10 are done and described in the documents above, not here. Plan
11 (2026-09-27/28, [`plans/11-remediation.md`](plans/11-remediation.md))
closed the September audit register: a hand leaving the box releases its
rows (B1), hot reload watches every module and keeps `Kind` identity
(H1–H4), one scene store and layouts on saved band presets (A1, A2), one
Learn object shared by MIDI and hands (B3, B4), one preset system with
routing presets in the library (L1–L3, L5, L6, L8), exact trigger phase on
every path (B6–B8), and one tidy-up sweep per component with the missing
boundary and loop-order tests (R, N, V, A, L, U, P) — PRs #40–#52, WP8 and
WP16 following, one PR per work package, each code-reviewed. Seven
decisions are the owner's and pending (plan 11 §2, rows 1–7: B2, B5, R1,
R6, A7, A10, R2+L2); the trim fix (A10) and the keys-into-the-table change
(R2+L2) wait on them.

**Everything only the machine can verify** — plan 09's five hand checks,
plan 08's unverified list, plan 07's WP6c dream tuning, the first real
capture, the APC40, the second monitor, IAC + FL Studio, and the
eyeballing owed for PRs #24, #25, #26, the LFO page and the re-laid-out
HANDS page — is one numbered list with commands, presets, pass and fail:
[`plans/11-hand-checks.md`](plans/11-hand-checks.md). Do it in that order;
file what fails as new audit rows dated with plan 11.

## Not done — in rough priority order

1. **The hand checks** above. Nothing in them has been run by a person
   since plan 09 landed; B1's fix and the HANDS page re-layout (plan 11
   WP13 found it overflowing the panel by 216 px on any rig with hands
   enabled) are the two things most likely to look different.
2. **First real audio capture.** Every live path is code-complete and now
   under test over a fake device, but no human has pressed `M` on real
   hardware with the macOS microphone prompt. One click plus a clap
   (hand check 3).
3. **The owner's seven decisions** (plan 11 §2) and the two work packages
   behind them: the trim non-monotonicity fix (A10, plan 06's open
   choice) and `R` / F1–F8 as table rows (R2, L2).
4. **Plan 04 — booth hardware.** Blocked on access: the pure-Python
   Pro DJ Link spike against the CDJ-3000/XDJ-AZ (BLT+OSC is the standing
   fallback), ESP32+BNO055 IMU ingest (packet format specced in BLUEPRINT
   §3.4), Δt delay compensation + metronome calibration. The tempo clock
   deliberately syncs to nothing until then (DECISIONS).
5. **Instanced GPU field.** For a *live* field: per-instance rotation
   phases and true instancing (agent prototype measured 621–845 fps at
   N=100; 1–2 days). The synchronized-grid mode is the v1.
6. **Plan 05's rest** — MIDI clock from deck BPM and the FL-side fuser
   script; the bridge itself is built, off by default, and now has a line
   on the SYSTEM page.
7. **Plan 06's non-trim items:** tempo-locked shapers once DJ Link exists,
   real harmonic detection, a scrub bar. (Saveable scenes and per-band
   LFO knobs are covered by the JSON scenes and the routable LFOs.)
8. **Ideas parked:** per-cell (3-cell) grouping for cell-wise
   colour/pattern assignment.

## Decisions that govern future work

The full, dated list is [`DECISIONS.md`](DECISIONS.md). The ones a new
session trips over first:

- Full Python re-platform; the HTML is a frozen reference, never executed
  at runtime (BLUEPRINT §5). FL Studio connects only via the optional
  bridge (§3.6).
- Parity bar: geometry exact; audio behavioural; visuals judged by the
  owner's eye.
- One performer per parameter; scene-setters write the base; every
  continuous source reaches a param only through `Router.modulate`;
  `hands/core.py`, `hands/signal.py`, `lfo.py` and `tempo.py` import
  nothing from the package (ARCHITECTURE §3, held by tests).
- Plans 03/04 swapped (hardware unavailable). The DJ Link spike is the
  first thing to do when deck access exists — it is the only genuine
  unknown in the stack.
