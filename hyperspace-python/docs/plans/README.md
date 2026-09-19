# Implementation plans

The migration described in [`BLUEPRINT.md`](../BLUEPRINT.md) §5, broken into
executable plans. Run them in order — each one's exit criteria are the next
one's prerequisites. Machine prerequisites for all of them live in
[`docs/SETUP.md`](../SETUP.md); satisfy its tier A before plan 00.
Current state and the pick-up list: [`docs/CHECKPOINT.md`](../CHECKPOINT.md).

| Plan | Blueprint stage | Delivers |
|---|---|---|
| [00 — Golden traces](00-golden-traces.md) | Stage 0 | Python scaffold, recording harness, reference traces from `hyperspace.html` |
| [01 — Core parity](01-core-parity.md) | Stage 1 | `geometry.py` + `audio.py` + `bands.py`, headless, proven against traces |
| [02 — Renderer](02-renderer.md) | Stage 2 | `render.py` — the moderngl window, all 18 shapes |
| [03 — UI, scenes & audio](03-ui-scenes.md) | Stage 4 | `ui.py` + `audio.py` — band strips, meters, scenes, transport, capture |
| [04 — Live inputs](04-live-inputs.md) | Stage 3 | DJ Link, IMU, delay compensation (needs booth hardware) |
| [05 — DAW bridge](05-daw-bridge.md) | §3.6 (after 03–04) | `params.py` registry + `midi.py`/`apc40.py` inbound control (done); `bridge.py` — outbound MIDI/OSC, FL Studio connectivity |
| [06 — Divergence](06-divergence.md) | Stage 5 | Bug fixes and new features the HTML never had; HTML frozen |
| [07 — Overhaul](07-overhaul.md) | after 05's controller half | Two windows, preset/project library, N-band analyzer, one modulation concept over the registry — WP0 foundation done; WP1/WP2/WP4a in flight |

## Conventions that apply to every plan

- **Ground truth.** [`ENGINEERING.md`](../ENGINEERING.md) describes how the
  existing chain actually behaves; [`BLUEPRINT.md`](../BLUEPRINT.md) says
  what the target system is. Where a plan is silent, those documents govern.
  Where documents disagree about existing behaviour, ENGINEERING.md wins.
- **Parity before improvement.** Through plan 04, the Python code reproduces
  the HTML's behaviour — including its known bugs (the trim non-monotonicity,
  ENGINEERING §4). Fixes live in plan 06 only. A "fix" during a port makes
  parity failures undiagnosable.
- **Exit criteria are gates.** A plan is not done until every criterion in its
  *Exit criteria* section passes, and the criteria are checked on the merged
  state of `main`, not on a feature branch.
- **`hyperspace.html` never runs at runtime.** It is executed only by the
  plan-00 harness to record traces. No plan may import from it, embed it, or
  shell out to it in the running system.
- **Worktree traps** (ENGINEERING §10, both have already cost a round):
  1. Agents in worktrees branch from stale HEADs — every agent prompt starts
     with `git merge main --no-edit` plus a `grep -c` check for features that
     must exist, stopping to report if any are missing.
  2. An agent's measurements describe only its own branch. Re-measure the
     merged build before reporting anything as working, and keep it clear
     which numbers are first-hand.

## Tooling (established in plan 00)

Python ≥3.12, managed with `uv` (`pyproject.toml` at repo root). `pytest` for
tests, `ruff` for lint/format. Runtime deps arrive per plan: `numpy` (00),
`moderngl`+`glfw` (02), `sounddevice` (03), `imgui-bundle` (04),
`mido`/`python-rtmidi`/`python-osc` (05). `playwright` is a dev-only
dependency for the recording harness.
