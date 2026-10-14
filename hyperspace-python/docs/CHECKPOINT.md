# Checkpoint

Hyperspace is a live-visuals app: a 4D polytope driven by music, hands
(an Ultraleap camera), an APC40 and LFOs, shown on a Pepper's Ghost glass
and a projector. It is one Python process in `hyperspace-python/`.

## Where things are

- **The app:** `hyperspace-python/` (package `hyperspace/`, tests in
  `tests/`, tools in `tools/`). Presets are shared through a cloud-synced
  folder named by `[library] path` (plan 25; [`SETUP.md`](SETUP.md)).
- **Run it:** `uv sync`, then `uv run hyperspace`; machine setup is in
  [`SETUP.md`](SETUP.md).
- **The docs:**
  - [`ARCHITECTURE.md`](ARCHITECTURE.md): the parts, the frame, who may
    write a parameter.
  - [`ARCHITECTURE.html`](ARCHITECTURE.html): the same map as a diagrammed
    page, for reading in a browser. Maintained with the Markdown.
  - [`ENGINEERING.md`](ENGINEERING.md): how each part behaves.
  - [`DECISIONS.md`](DECISIONS.md): the decisions in force, and what was
    decided not to build.
  - [`DECISION-REGISTER.md`](DECISION-REGISTER.md): rows 34–108, built on
    a recommendation and waiting for the owner's keep or overturn; row 109
    records the owner's plan 25 answers.
  - [`AUDIT-2026-09.md`](AUDIT-2026-09.md): the open defects.
  - [`TESTING-GUIDE.md`](TESTING-GUIDE.md): everything a person still has
    to test, in plain words, by hardware.
  - [`plans/11-hand-checks.md`](plans/11-hand-checks.md): the same checks,
    numbered 1–143, with the automated test behind each.
  - [`plans/`](plans/README.md) `15-…` to `22-…`: what each of the last
    eight plans built; plan 22 also has a ranked shortlist of new
    4-polytopes and macro candidates to audition.
  - [`plans/assets/12-presets/`](plans/assets/12-presets/): the performer
    cards, one per party preset.

## Where the code stands

`main` is at `2d4ea11`: everything through plan 21 (PR #80, with the
shared presets of PR #113), the architecture page and plan 22's prompt.
Plan 22 — the flat shapes given real 4D extent, the Klein bottle, and the
face patterns made usable — is on `plan-22-integration`; its PR to `main`
waits for the owner. Check `git log` and the PRs for the current state.

## What is left

- **The hand checks.** None has been run by a person. Start from
  [`TESTING-GUIDE.md`](TESTING-GUIDE.md), on a copy of `~/Hyperspace`.
- **The owner's keep or overturn** on register rows 34–108 (the answer sheet
  at the top of [`DECISION-REGISTER.md`](DECISION-REGISTER.md)).
- **The open audit findings:** R14, R15, U9, U10, P6, V8, and the small
  defects listed under them.
- **Things nobody has observed:** frame pacing with two screens; a screen
  unplugged mid-run; anything on the APC40, the hand camera, the projector
  or the glass. No real hand has been tracked: every hands picture comes
  from a synthetic tape. No person has watched the lifted shapes or the
  Klein bottle turn, or seen the FACES page or the seventeen patterns on
  the Mac: its fit and Apple's shader compiler are unverified (hand
  checks 120, 121).
- **Plan 22's choices for the owner:** which new 4-polytopes to build
  ([`plans/22-polytope-shortlist.md`](plans/22-polytope-shortlist.md)),
  the macro candidates' listening session
  ([`plans/22-macro-candidates.md`](plans/22-macro-candidates.md)), and
  whether to re-save the sixteen presets from Dan's snapshot (now in his
  library) that still push the pattern inputs at depth 1 (the factory's
  is now 0.35).
- **Deliberately not built:** see "Decided not to build" in
  [`DECISIONS.md`](DECISIONS.md).

## Standing rules

- Tests and agents never read or write the owner's real `~/Hyperspace`.
  Tests run against a temp home (`HYPERSPACE_HOME`, set by
  `tests/conftest.py`).
- Never push to `main`. The owner merges.
- A change to a file format backs the old file up before the first
  rewrite.

## Ideas for later (not started)

- An IMU prop feeding rotation phase offsets over UDP: packet
  `struct {uint8 ver; uint8 id; float qw, qx, qy, qz}`, little-endian,
  100 Hz; orientation deltas go to the XW / YW / ZW phase offsets, never
  to a speed; a silent prop decays to no contribution.
- DJ Link tempo: `{bpm, beat_phase, bar_phase, master_deck, on_air[]}`;
  a pure-Python source first, Beat-Link-Trigger over OSC as the fallback.
  MIDI clock in is the other tempo source. (DECISIONS currently says
  neither is built: tempo is tap-only.)
- Audio delay compensation: stream latency + analysis latency − about
  1 ms, calibrated with a metronome.
- FL Studio does not fuse 14-bit MSB/LSB pairs in "Link to controller":
  the bridge needs a small FL MIDI script, or per-channel pitch bend.
- An instanced GPU field (per-instance rotation phases, true instancing).
