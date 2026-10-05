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
| [14 — The party rig](14-party-rig.md) | after 13 | From the first night at the machine: an opaque window for Pepper's Ghost, a stall watchdog, the party show as what the rig opens, a PRESETS page for a party, the effects in the show, the dream and legible echoes, the desk drawn with glyphs; the owner's to-do list at the machine (§6) — merged (PR #77, with #72–#76); decisions 21–25 answered; hand checks group I (43–46) pending |
| [15 — Safety net and the bank](15-safety-net.md) | after 14 | From the Oct 3–4 session: undo down to single edits with no write hook (⌘Z / Ctrl+Z, a step per gesture or per load, Learn, Unbind and delete; a hand moving makes none), a trash for preset files a save or a delete would destroy, home (the show's "starts on" preset on the Home key and OVERDUB), the crossfader as master dim of the finished frame, and save-as on the desk (a hold on the clip-stop row makes a new preset in the next empty slot; the desk never overwrites) — built on `finish-line`, PRs #81–#83 and #87–#88 (WP3 the dim, WP1 undo and the trash, WP2 home, WP4 save-as, WP5 these documents); decisions 26–29, and rows 34–44 built on the run's recommendation for the owner to confirm; hand checks group K (48–57) pending |
| [16 — Paper cuts](16-paper-cuts.md) | after 15 | From the Oct 3–4 session, five small fixes with no new param, page or menu item: the cheat sheet off at launch (`/` shows it); an FX chip whose name opens the effect and whose dot switches it, three chips to a row, the open effect remembered by name; an effect that is not running says why, with "turn on" and its controls dimmed but live; the windows open where `config.toml` says (`[output] monitor`, new `control_monitor`), else where they were at the last quit (`<home>/windows.json`); `view.instances` down to 0 (nothing drawn; echoes and effects carry on) and `dream.layer` not modulatable; plus four follow-ups (a footer line said twice shows twice, a performer's round-off lights no dirty dot, the desk diagram's one-frame jump, a config screen that is not a number) — built on `finish-line`, PRs #84–#86, #89, #90 and #92 (WP2, WP4, WP3, WP1, WP5, WP7), these documents in WP6; no decision was the owner's before the build, and rows 45–49 were built on the run's recommendation for the owner to confirm; hand checks group L (58–63) pending — window placement has not met a second screen |
| [17 — Learn, Unbind and seeing the desk](17-learn-and-the-desk.md) | after 16, beside 18 | From the Oct 3–4 session, where mapping lost the most time: one **Unbind** that removes the preset's desk rows and every route on a param, there with MIDI off and never offered where it could only refuse; **Learn desk** and **Learn hand ▸ left / right**, so a learn listens to one source — a knob bumped during a hand learn does its own job, and the session's controls (SHIFT, the faders, TAP, the preset pads) work through a desk learn, which stays armed after a refusal; the menu on a row's label and on every meter; the on-screen desk taking the room it has — the whole control window with the panel hidden (H), every lit control named — and clickable: click a control, then click a param on the dimmed page, with a pick that lets go by itself after 20 s; a filter on the ROUTING page. No param, page, key or file added — built (PRs #93, #96, #99, #91, #102, on `plan-18-integration`), §7 "As built"; eight calls built on the plan's recommendation wait in `DECISION-REGISTER.md` rows 57–64; hand checks group M (64–71) pending — no real click, right-click, keystroke, hand or APC40 has met any of it |
| [18 — Hand and knob feel](18-hand-and-knob-feel.md) | after 16, beside 17 | From the Oct 3–4 session's "lower hand sensitivity", "tame rotation" and the desk's stepping knobs: an interaction box in `hands.json` that the calibration sweep sets and "reset ranges" opens, drawn on the HANDS page — a hand outside it is absent everywhere; a hand Learn that lands as a `push` about the base at one session depth (`hands.learn_depth`, 0.25) wherever the axis or the target's range is centred, and takes the axis's other rows with it; knob smoothing (`desk.slew`: a straight-line glide between detents that rests where the value always did, 80 ms in the running app); and `hands-orbit`, a factory preset with the right hand orbiting the camera and the left panning and zooming it — built on `plan-18-integration`, PRs #94, #98, #100 and #97 (WP1–WP4), these documents in WP5; no decision was the owner's before the build: rows 50–56 were built by the run for the owner to confirm, six on the plan's recommendation and one (row 54, smoothing on at 80 ms) against it; hand checks group N (72–80, calibration first) pending — nothing in it has met a camera, a real hand or an APC40 |
| [20 — FX, dream and looks](20-fx-dream-looks.md) | after 16, beside 19 | From the Oct 3–4 session: **the faces as their own effect target** (the owner's ask) — each effect aimed at the frame or at the faces (`fx.<name>.target`), the faces' effects run as a second chain over a 1024² picture of what a face shows, laid on per face or in screen space (`fx.face_map`), before the scene pass, so the echoes and the dream carry them; the FX page's chip grid as the chain view — two status rows per target, a diamond for a chip on the faces, the strip's target combo, a chip dragged by its name to reorder (one undo step); the LOOKBACK page as ECHOES, DREAM and BOTH with labels that say what each knob does, here and in the registry, and the dream's layer as six chips; the dream's "speed" as `dream.k` read in dream frames; instance layouts GRID, HEX, RING (`view.inst_layout`) with the VIEW page's field in one row — built on `plan-20-integration`, PRs #101, #106, #108, #105, #107, #111 (WP1–WP6), these documents in WP7, §7 "As built"; none of its forks was asked of the owner before the build: F1–F10 were built on the plan's recommendation and wait in `DECISION-REGISTER.md` rows 65–71; hand checks group P (91–98) pending — nobody has seen a face effect on a projector or the glass, dragged a chip with a real mouse, or judged the dream at any speed |
| [15–21 — Roadmap](15-21-roadmap.md) | after 14 | From the Oct 3–4 session at the machine: the order and scope of seven plans — 15 safety net and the bank (undo down to single edits, home, master dim, save-as on the desk), 16 paper cuts, 17 Learn / Unbind / seeing the desk, 18 hand and knob feel, 19 presets and the desk layout (twenty-four slots), 20 FX / dream / looks (the faces as an effect target), 21 outputs and the hands — each plan document written when it starts, built unattended onto the `finish-line` branch ([orchestrator prompt](../prompts/plans-15-21-orchestrator.md)); decisions 26–33 answered 2026-10-04 |

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
