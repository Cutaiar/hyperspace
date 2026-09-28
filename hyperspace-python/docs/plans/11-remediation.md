# Plan 11 — Remediation: settle and close the register

**After plan 10.** Plan 10 wrote the documents and filed ~70 findings in
[`AUDIT-2026-09.md`](../AUDIT-2026-09.md) without fixing any of them. This
plan closes that register — every audit item plus the hand checks owed by
plans 07, 08 and 09 — and leaves a machine-side checklist
([`11-hand-checks.md`](11-hand-checks.md)) for the things only the owner
can verify with the camera, the box, the APC40 and a projector.

Nothing here is a redesign. The control model in
[`ARCHITECTURE.md`](../ARCHITECTURE.md) §3 stands as written: one performer
per parameter, scene-setters write the base, `Router.modulate` is the only
performer path, hands and LFOs import nothing from the package. Where an
audit item seemed to need a change to that model, it became a decision
(§2) rather than a fix.

Written 2026-09-27 against `main` **39caedf** (628 tests).

## 1. Scope

**In:** every row of the audit — B1–B8, H1–H4, R1–R12, N1–N6, V1–V7,
A1–A10, L1–L7, U1–U8, P1–P5, D1–D6 — and the verification owed by earlier
plans: plan 09's hand checks 3–7, plan 08's "Not yet verified" list, plan
07's WP6c dream tuning, the first real audio capture, the APC40's knobs /
buttons / LEDs, the second monitor, IAC + FL Studio, and the eyeballing
owed for PRs #24, #25, #26 and the LFO page.

**Out (parked or blocked, unchanged):** plan 04's booth hardware (DJ Link,
IMU, delay compensation), plan 05's MIDI clock and FL-side script, plan
06's items other than the trim (tempo-locked shapers, scrub bar, real
harmonic detection, per-band LFO knobs — the last two are covered by the
LFOs and routing already), the instanced GPU field, per-cell grouping.

**Concurrent work.** Another session is authoring performance presets in
`library/bindings`, `library/fx`, `library/dream`, `library/projects` and
possibly new `shaders/fx/*.glsl`. This plan touches factory preset files
only where A1 and A2 require it (the `band` folder), keeps those edits
minimal, and every branch rebases on `main` before its PR opens and again
before review.

## 2. Decisions

Six forks the audit left to the owner, plus the ones found while planning.
Each has a dated row in [`DECISIONS.md`](../DECISIONS.md) the day it is
settled; until then the work package that depends on it waits and every
other package proceeds. The recommendation is the plan's; the owner's
answer replaces it.

| # | Item | What the code does today | Options | Recommendation | Status |
|---|---|---|---|---|---|
| 1 | **B2** does a tap ever move the downbeat? | `Clock.tap` re-pins `t0` on every tap until the first `trigger`; after that a tap only changes BPM (`tempo.py:95-101`). | (a) never — only the trigger sets the downbeat; (b) keep as is and document; (c) the first tap of every burst sets it (plan 09 d.9 literally). | **(a)**: one rule, and the one DECISIONS already states ("the downbeat is the global trigger's"). A fresh app's synced LFOs run from launch until ⇧B, which plan 09 calls "the one button pressed after tapping". Hand check 5 then holds from the first tap. | open |
| 2 | **B5** are `tempo.tap`, `lfo.trigger`, `lfo.N.reset` modulatable? | All three are (`modulatable=True` default); a lane or a pinch switch can own one and fire it on rising edges. | (a) keep all three; (b) `modulatable=False` on all three; (c) keep the two LFO triggers, drop `tempo.tap`. | **(a)**: the pinch switches are lanes so that a pinch can be a button, and `lfo.N.reset` is documented as "a per-LFO gesture hook". A kick lane re-triggering the LFOs is a legitimate route. Record it as intended; the rising-edge trigger in `Param.apply` exists for exactly this. | open |
| 3 | **R1** are LFO knobs routing-layer state or theme state? | Theme state (`ROUTING_GROUPS = ("macro",)`), yet `lfo-breathe`'s `values` set `lfo.1.sync/shape/depth`, `lfo.2.sync` — as `hands-fx` sets `fx.acid.speed`. | (a) add `lfo` (and `tempo`) to `ROUTING_GROUPS`; (b) theme state, and strip non-routing ids from every preset's `values`; (c) theme state, and a routing preset's `values` may set any persisted base its rows assume (the `hands-fx` precedent), documented. | **(c)**: an LFO arrangement is part of the look a theme carries; a routing preset that assumes "LFO 1 at one bar" should say so rather than silently depend on the user's settings. The dirty dot it leaves on the LFO group is honest. One test: every factory `values` id is a persisted, non-alias param. | open |
| 4 | **R6** do LEDs on toggles follow the performer or show the base? | Rings show the base (`p.norm`); a toggle's LED, or an enum `set` row's, reads the effective value (`midi.py:526-528`). | (a) keep: rings are pickup readbacks and must show the base or the knob can never catch, LEDs are state lights and show what the show does; (b) LEDs read the base too, one rule for all feedback. | **(a)**, documented as intended in ARCHITECTURE §3.2 and `midi.py`. Nothing changes on the desk. | open |
| 5 | **A7** `master.dyn`'s 0.06×–4× range vs the chain's clamp to 1. | The window blend uses `clamp(dyn, 0, 1)`; the expansion ratio uses `dyn` raw (`analyzer.py:534, 545`); the parity oracle is frozen at dyn ∈ {0, 1}. | (a) cap the taper at 1× (moves every saved preset's detent; re-map positions); (b) keep the range and document the split: past 1× the window blend is full and only the expansion keeps growing; (c) two knobs. | **(b)**: a tooltip and an ENGINEERING sentence; no preset moves and the oracle stays frozen. | open |
| 6 | **A10** the trim non-monotonicity: which of plan 06's three fixes. | Trim is applied pre-envelope and again as `t_u`; frozen bit-exact by the parity test. | (1) bias the adaptive window in proportion to trim; (2) trim as a post-normaliser multiplier; (3) a per-band **auto / manual** normalisation switch — manual bypasses the adaptive window and trim becomes a plain gain. | **(3)**, as plan 06 proposed: the auto path stays bit-exact (the oracle is not re-frozen), manual is where a mix engineer reaches for a trim, and the monotonicity test runs in manual. (1) and (2) each change the reference path and re-freeze the oracle. | open |
| 7 | **R2 + L2** R and F1–F8 / ⇧F1–F8 into the table? | Loop code (`app.act`), by a standing decision of 2026-09-26 whose reason was scope, not design. | (a) make them rows (`key:R → camera.reset`, `key:F1 → theme.load.1`, `key:SHIFT+F1 → theme.save.1`), delete `app.act`, `remap_factory` adds them to older files; (b) keep them in the loop and delete only the duplicate `set_value`. | **(a)**: closes R2 and half of L2, the cheat-sheet test (U2) then covers them, and the only keys left outside the table are Cmd+R and Esc / Q. Supersedes the 2026-09-26 row. | open |
| 8 | **B1** sub-fork: when a hand leaves the box, does `rest = hold` still latch a route? | A `position` row keeps positioning at the follower's value (spring or hold) until the tracker goes dark. | (a) the axis reads NaN the moment its hand is absent — every row lets go and the base returns (a jump, as a gate opening is today); the spring and `hold` still shape the DAW output; (b) NaN after the spring settles (two motions: a glide to `depth · rest`, then a jump). | **(a)**, the audit's fix and plan 08's sentence ("every performer row springs back to the base when the hand leaves"). Latching is done by setting the base. Proceeding on this. | proceeding |
| 9 | **A1** which scene store survives. | `bands.PRESETS` (drives `scene.select`, reset, undo; keeps names) and `library/band/*.json` (the strip; a layout, no names). | (a) the JSON files are the one source, `name` in the layout, `scene.select` loads through the library; (b) delete the JSON and keep the strip on `bands.PRESETS`. | **(a)**, the audit's first choice: user scenes then work like every other module preset. Proceeding on this. | proceeding |
| 10 | **L3** `Project.io`, never written. | Always `{}`; the live table is `<home>/bindings.json` (DECISIONS). | (a) delete it and fix the tooltip; (b) fill it (a project carries its routing). | **(a)**: the standing decision is that the table is one home file. Proceeding on this. | proceeding |
| 11 | **B6** trigger-frame phase from the panel or a performer. | Keys trigger before `lfos.step`; the panel chip and a performer-fired trigger run after it, so the LFOs see the new downbeat next frame with phase ≈ `dt · bpm / 60 · ratio`. | (a) document; (b) a trigger that fires after this frame's step is held and applied at the start of the next step, so the first frame the LFOs see it reads exactly phase 0 (one frame later, invisible). | **(b)**: makes the docstring's promise true on every path. Proceeding on this. | proceeding |

## 3. Work packages

One branch, one PR per package, the audit ids in the title, tests for the
behaviour it changes, `pytest` and `ruff` green, and the ARCHITECTURE /
ENGINEERING / AUDIT lines updated in the same PR. **Marking an audit row
done:** append ` — **done, PR #N**` (or `— **decided, PR #N**` for a
documented decision) to the row's *Finding* cell; never delete a row.
Every branch starts from current `main` and rebases before its PR opens.

Waves run in parallel where the files are disjoint; a package that
depends on an unmerged PR branches from that PR's branch and says so.

### Wave 1 — what a performer feels, and what every session leans on

| WP | Closes | Files | Size |
|---|---|---|---|
| **WP1 hands release** | B1, N6 | `hands/core.py` (`lanes()` publishes NaN for an axis whose hand is absent; the follower keeps springing for MIDI out), `hands/signal.py` docstring, `tests/test_hands.py` (the tracker-on test the audit says is missing), plan 08 and ARCHITECTURE §3.10 lines | M |
| **WP2 hot reload** | H1, H2, H3, H4 | `hotreload.py` (`MODULES` gains `tempo`, `lfo`, `fx`, `hands.signal`, `hands.core`, `hands.panel`, `gamepad`, `config`, `ui_fx`, `ui_lfo` in dependency order; a test that every swap target's module is watched), `params.py` (`Kind` identity survives a reload), `render.py:373-385` (dead backfills out), `hands/core.py:759-769` (guards out), `tests/test_hotreload.py` | M |
| **WP3 scenes** | A1, A2 | `bands.py`, `analyzer.py`, `control.py`, `library.py` (a per-group `extra` hook), `ui_presets.py`, `library/band/*.json` (a `name` per band in the layout — the only factory preset edit), `tests/test_control.py`, `tests/test_library.py`, `tests/test_analyzer.py` | M |
| **WP4 tempo and LFOs** | B6, B7, B8; B2 and B5 when decided | `tempo.py`, `lfo.py`, `tests/test_lfo.py`, `tests/test_tempo.py`, an AST test that `Param.modulate` has one caller, ARCHITECTURE §3.9 / §3.10, DECISIONS | S |

### Wave 2 — the structural four

| WP | Closes | Files | Size |
|---|---|---|---|
| **WP5 the learn object** | B3, B4 | a `Learn` object (`learning` / `pending` / `learn_source`) owned by the panel or router, completed by MIDI and by hands alike; the alias resolved to the real band param; `midi.py`, `hands/core.py`, `ui.py`, `ui_routing.py`, `tests/test_midi.py`, `tests/test_hands.py`, ARCHITECTURE §3.5 | M |
| **WP6 one library** | L1, L2, L3, L5, L6 | `Library` learns the `hyperspace.bindings/2` document kind with a loader hook; `routing.py` drops its shadowing copy; one preset strip; `Presets` folded into `library.Project`; `Project.io` deleted; `rename` dropped; `_fresh` per group; `tests/test_library.py`, `tests/test_presets.py`, `tests/test_routing.py` | M |
| **WP7 the keys into the table** (decision 7) | R2, the rest of L2 | `routing.py` (`keymap`, `remap_factory`), `app.py` (`act` deleted), `ui.py` (`CHEATSHEET`), `tests/test_routing.py` | S |

### Wave 3 — one sweep per component, each landing its missing test

| WP | Closes | Files | Size |
|---|---|---|---|
| **WP8 routing + MIDI sweep** | R3, R4, R5, R7, R8, R9, R10, R11, R12; R1 and R6 as documented decisions | `routing.py`, `midi.py`, `apc40.py`, `tapers.py` (one `_clamp`), `audio.py` (lane labels), new `tests/test_routing_boundary.py` (import boundary, one caller of `Param.modulate`, the frame order over a stub loop) | M |
| **WP9 hands sweep** | N1, N2, N3, N4, N5 | `hands/core.py`, `hands/__init__.py`, `config.py` (refers to the one defaults table), a `FakeLeap` fixture, `tests/test_hands.py` | M |
| **WP10 render sweep** | V1, V2, V3, V4, V5, V6, V7 | `geometry.py`, `render.py` (`ViewState` → `view.py`), `fx.py`, `lookback.py`, `shaders/`, `pyproject.toml`, `tests/test_render.py`, `tests/test_core.py` | M |
| **WP11 audio sweep** | A3, A4, A5, A6, A8, A9; A7 as a documented decision | `audio.py`, `analyzer.py`, `bands.py` (`Chain` alias gone, one default table, `DRIVE` to routing), `offline.py`, `ui.py` (device list refresh, the analyser's rate), a fake `sounddevice`, an FFT test, `tests/test_audio.py` (new), a boundary test | M |
| **WP12 library + config sweep** | L4, L7 | `config.py` (`[output]` canonical, `[overlay]` a deprecated alias, `cfg["error"]` shown on SYSTEM), `app.py:174-182`, an autouse `HYPERSPACE_HOME` fixture in `tests/conftest.py` | S |
| **WP13 panel sweep** | U1, U2, U3, U4, U5, U6, U7, U8 | `ui.py`, `ui_routing.py`, `ui_lfo.py`, `ui_lookback.py`, `hands/panel.py`, `params.py` (`audio.mic` / `audio.device` / `app.restart` in `build_registry`), `tests/test_ui_shell.py`, a cheat-sheet-vs-table test | M |
| **WP14 host sweep** | P1, P2, P3, P4, P5 | `app.py` (`close_all`, one `now`), `config.py` (`[gamepad] enabled`, default on), `gamepad.py`, `bridge.py` / `ui.py` (a bridge line on SYSTEM), `overlay.py` (a "follow window" monitor choice), new `tests/test_app_boundary.py` (import hygiene, `_open_*` gates, `Keys`, `Mouse`, the loop order over stubs) | M |

### Wave 4 — the decision-gated fix and the documents

| WP | Closes | Files | Size |
|---|---|---|---|
| **WP15 the trim** (decision 6) | A10 | `analyzer.py`, `bands.py`, `tapers.py`, `ui_bands.py` (the switch on the strip), `library/band/*.json` (only if the layout schema needs a field; default auto), a monotonicity test on real material, ENGINEERING §4's warning rewritten | M |
| **WP16 documents** | D1, D2, D3, D4, D5, D6; this plan's "As built"; `11-hand-checks.md` | `README.md`, `docs/CHECKPOINT.md`, `docs/plans/README.md`, `tests/legacy_chain.py`, test files renamed for what they test, `tests/test_golden.py`, `docs/plans/11-hand-checks.md` | S |

## 4. Exit criteria (checked on merged `main`)

- [ ] 1. Every audit row is marked done or decided with a PR number; none
      is deleted.
- [ ] 2. ARCHITECTURE §3.10 ("what this section does not promise") lists
      nothing this plan fixed; §3.2's consequences and §3.9 say what the
      code does after the decisions above.
- [ ] 3. DECISIONS has a dated row for every decision in §2 that the owner
      made in this plan, and the 2026-09-26 tempo row's "two deviations"
      note is gone or reduced to what still holds.
- [ ] 4. The four missing tests exist and pass: `routing.py`'s import
      boundary and the one caller of `Param.modulate` (R11), the audio
      stack's streams and FFT with a boundary test (A9), `app.py`'s import
      hygiene and loop order over stubs (P5), and hands releasing a
      `position` row with the tracker on (B1).
- [ ] 5. `uv run pytest` green, `uv run ruff check .` clean, on `main`
      after the last merge; ENGINEERING §6's test count updated.
- [ ] 6. `11-hand-checks.md` exists: one numbered check per item only the
      owner can verify, in machine order, each with commands, config keys,
      the preset, the gesture, pass, fail, and the audit item or code path
      a fail points at; every check that can be simulated headless names
      the pytest or `tools/` command.
- [ ] 7. The owner has run the hand checks; what failed is filed as new
      audit rows dated with this plan.

## 5. As built

Filled in as the packages land: one line per deviation from the text above,
for the next plan to gather.
