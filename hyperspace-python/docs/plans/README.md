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
| [02 — Renderer](02-renderer.md) | Stage 2 | `render.py` — the moderngl window, all 18 shapes (now `app.py` owns the windows; 25 shapes, `geometry.py`) |
| [03 — UI, scenes & audio](03-ui-scenes.md) | Stage 4 | `ui.py` + `audio.py` — band strips, meters, scenes, transport, capture |
| [04 — Live inputs](04-live-inputs.md) | Stage 3 | DJ Link, IMU, delay compensation (needs booth hardware) |
| [05 — DAW bridge](05-daw-bridge.md) | §3.6 (after 03–04) | `params.py` registry + `midi.py`/`apc40.py` inbound control (done); `bridge.py` — outbound MIDI/OSC, FL Studio connectivity |
| [06 — Divergence](06-divergence.md) | Stage 5 | Bug fixes and new features the HTML never had; HTML frozen |
| [07 — Overhaul](07-overhaul.md) | after 05's controller half | Two windows, preset/project library, N-band analyzer, one modulation concept over the registry — WP0 foundation done; WP1/WP2/WP4a in flight |
| [08 — Hands](08-hands.md) | after 07 | Ultraleap two-hand tracking → 12 shaped analog axes (curve, dead zone, attack/decay, rest springs): float `hand:` sources + Learn in-app, 7/14-bit CC · bend · pressure to a DAW; HANDS page, setups as presets |
| [09 — One performer](09-one-performer.md) | after 08 | One path for every live source, one performer per parameter with an FL-style replace prompt, two ops (`push` / `position`), macro knobs, tap-tempo clock, four chainable LFOs; bindings schema 2 — executed 2026-09-26 (PRs #33–#37); hand checks pending |
| [10 — Architecture & documentation](10-architecture.md) | after 09 | The system as built, for maintainers and agents: `ARCHITECTURE.md` (component map, the frame, the control model as the canonical statement, module shapes), `DECISIONS.md` (dated, with the why), `ENGINEERING.md` refreshed for the Python app, `AUDIT-2026-09.md` (findings, sized, filed for plan 11) — executed 2026-09-27; docstrings were the only code touched |
| [11 — Remediation](11-remediation.md) | after 10 | Settle and close the audit register: every B/H/R/N/V/A/L/U/P/D row fixed or decided, sixteen work packages as one PR each (#40–#54, integrated on `plan-11-integration`), the missing boundary and loop-order tests, `11-hand-checks.md` for what only the owner can verify at the machine — executed 2026-09-27/28; merged (PR #55, main 4bffa9d); its owner decisions answered (`docs/DECISION-REGISTER.md`) |
| [12 — Party presets](12-presets.md) | after 11 | Five party presets, one per render attraction, for two hands over the box: routes, the look each expects, a card per preset, headless sweeps — merged (PR #47); re-cut as full presets by plan 13 WP5; projector and box checks pending (hand check 32 / 41) |
| [13 — Preset and session](13-preset-and-session.md) | after 11 and 12 | Two nouns (a preset = values + routes + desk + macros; a session = the rig), a two-layer APC40 under a latched SHIFT, one macro concept (base and depth subscribers), Learn into the loaded preset, one ROUTING page, the one-time migration of a home — merged (PR #69, with #61–#68 and #70; the first-frame crash fixed in #71); pending: hand checks group H (`11-hand-checks.md`, 33–42 with 31) |
| [14 — The party rig](14-party-rig.md) | after 13 | From the first night at the machine: an opaque window for Pepper's Ghost, a stall watchdog, the party show as what the rig opens, a PRESETS page for a party, the effects in the show, the dream and legible echoes, the desk drawn with glyphs; the owner's to-do list at the machine (§6) — planned; WP1 in progress; decisions 21–25 open |

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
