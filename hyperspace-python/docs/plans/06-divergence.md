# Plan 06 — Divergence

**Blueprint stage 5.** Parity is over: fix what the HTML got wrong, build
what it never had, and freeze the HTML. From here the Python system is the
only implementation that moves.

## Prerequisites

Plans 00–04 complete (05 can proceed in parallel — nothing here depends on
the bridge).

## Tasks

### 1. Freeze the HTML

Tag the parity commit (`html-parity`). `hyperspace.html` no longer receives
changes; whether it stays deployed on Vercel as a zero-install demo is
cosmetic. Update `README.md` and `ENGINEERING.md` headers to point at the
Python system as the live implementation, and mark ENGINEERING's HTML
sections as historical reference for the ported behaviour.

### 2. Fix the input trim non-monotonicity — **decision required first**

The one known bug ported on purpose (ENGINEERING §4 warning: cutting 6–12 dB
makes BASS drive *harder*; only attenuates from ~−20 dB). Three candidate
fixes, which behave very differently (ENGINEERING §9):

1. bias the adaptive window in proportion to trim;
2. apply trim as a post-normaliser multiplier on the band's contribution;
3. a per-band **auto/manual** normalisation switch — manual bypasses adaptive
   normalisation and trim becomes a plain gain.

(3) is closest to what a mix engineer expects and is the one to propose
first — but **ask before building**; the user was asked once and the session
ended before an answer. Whatever is chosen: add a monotonicity test (real
material, settled state, trim swept 0 → −20 dB, `out` non-increasing) so the
regression can't return.

### 3. Tempo-locked shapers

CHOP/TREM (and future LFOs) gain a sync mode: rate expressed in beat
divisions (1/4, 1/8, 1/16, triplets), phase-locked to `bar_phase` from
`djlink.py` — the tempo-sync open thread (ENGINEERING §9) resolved with real
beat-grid data. Free-running Hz remains when no DJ Link is present. Add the
optional per-plane bar-spin scene parameter (one revolution per bar,
phase-locked, off by default — BLUEPRINT §4.1).

### 4. Saveable scenes

Trivially unblocked outside the artifact sandbox: user scenes as JSON files
in a config directory; save/load/rename in the scene dropdown; built-in 11
remain read-only. Scene files carry a schema version from day one.

### 5. Backlog (order by appetite, each small and independent)

- Per-band LFO rate/depth as knobs rather than constants inside CHOP/TREM.
- Real harmonic detection (integer-multiple peak picking) to replace the
  octave-coherence proxy — A/B against the proxy before adopting.
- A scrub bar on the transport (position math already exists).
- Retune `OPEN_SPAN`, `CONF_LO`/`CONF_SPAN` against real commercial
  material (ENGINEERING §9 flagged these as the likely-to-need-tuning
  constants once real tracks are in play).
- Solid/raymarched render mode (the one salvageable idea from the rev-1
  shader) — only if wanted on aesthetic grounds.

## Exit criteria

This plan is open-ended; it exits by *shipping the decided items*, not by
emptying the backlog:

- [ ] HTML frozen and tagged; docs point at the Python system.
- [ ] Trim fix chosen (with the user), implemented, monotonicity test green.
- [ ] Tempo-locked shapers working against real DJ Link data.
- [ ] User scenes save and load across restarts.

## Risks / notes

- Every change from here lands with a test where one is possible — parity
  tests stop guarding behaviour the moment behaviour is *supposed* to
  change, so each divergence replaces the corresponding golden expectation
  deliberately, never silently.
