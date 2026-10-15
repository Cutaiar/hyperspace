# C5 report: the grab switch as a gate, hands on the projector by default

**Status:** DONE_WITH_CONCERNS. The concern is that `config.toml.rig` was not edited (see Concerns).
**PR:** https://github.com/Cutaiar/hyperspace/pull/178 (base `plan-24-26-27-integration`)
**Branch:** `plan-24-c5-grab`. Base confirmed as `87d2e29` (Merge plan 24 C4, PR #176).

## Commits
- `89dc90f` Plan 24 C5: the grab switch — a closed fist as a gate like the pinches. This commit also carries the two C4 code review fixes in `core.py` and `panel.py`.
- `b6dd307` C4 review: energy falls on a frame with no speed; dance test counts and wording.
- `6e6b1db` SETUP.md: the projector entry says hands = true (hands on the main projection).

## What was built
- **`hands/core.py`**
  - New: `GRAB_FINGERS`, `GRAB_CLOSE = 0.65`, `GRAB_OPEN = 0.45`, `GRAB_HOLD_S = 0.05`, `fist()`, `step_grab()` and `grab_name()`.
  - `addresses()` and `Layout` append `left.grab` and `right.grab` after C4's lanes, taking the count from 38 to 40. `Layout.grab` is new, and `Layout.gates` lists the 8 pinches and then the 2 grabs.
  - `HandsIO.grab` holds one `Gate` per side. It is stepped in `_dances` from the raw curls and reset when the hand is away; `lanes()` fills it.
  - The hot-reload guards (`_grabs`, `_layout`) cover objects created before the change.
  - C4 fix: `Dance.step` sets the energy target to 0 on a fresh frame that measures no speed.
  - Still imports nothing from the package.
- **`hands/__init__.py`**: exports `fist` and `grab_name`.
- **`hands/panel.py`**
  - `_grab` draws a "grab ●/○" glyph on each hand's curl row, with a tooltip showing the fist level against the thresholds.
  - C4 fix: after the dance column, the cursor goes to the larger of the two bottoms, then an empty item is drawn. The cursor is set one item-spacing short so a normal-length `dofs` page lays out exactly as before.
- **`docs/SETUP.md`**: the projector entry in the example has `hands = true`, plus one sentence.
- **Tests**
  - New file `tests/test_hands_grab.py` with 11 tests.
  - New fixture `tests/fixtures/grab-follow/grab-follow.json`, force-added. It holds the owner's mapping: yaw→`camera.yaw`, pitch→`camera.pitch`, roll→`rot.phase.XY`, each `when hand:right.grab`.
  - `tests/fake_hands.py` gains `close=` for a half-closed hand; defaults are unchanged.
  - `tests/test_hands_dance.py` gains the energy test.
  - Count-pinned assertions moved from 38 to 40. Each one is listed in the PR body and in the decisions file §4.

## How it was tested
```
uv run pytest -q
  1933 passed, 2 skipped in 130.48s (0:02:10)        (base: 1921 + 2; +12 new)
uv run ruff check .
  All checks passed!
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/c5-smoke-home uv run hyperspace -ApplePersistenceIgnoreState YES
  exit=0
  ApplePersistenceIgnoreState: Existing state will not be touched. New state will be written to …/org.python.python.savedState
  dream: mps · alias copy path · fp32 · weights /tmp/c5-smoke-home/weights
```
- **Smoke run.** The scratch home's `config.toml` has `[hands] enabled = true, tape = "grab.tape.json"` (the grab test's tape), a single `[[output.screens]]` projector entry with `hands = true`, `[midi] enabled = false`, and no `[library]` section. I passed `-ApplePersistenceIgnoreState YES` on the command line, as B1 found, to get past the "reopen windows?" alert. It is per-process and writes nothing.
- **Fixes fail without their change.**
  - With the old cursor line put back, the short-dofs test fails. I checked this by reverting the line temporarily.
  - The energy test asserts `_target == 0.0`, which the old code never set.
- `git diff --stat -- hyperspace/library/ hyperspace/preset.py` is empty.

## Self-review
- The grab's `Gate` closes on a strict `<`, so "closes at 0.65" really means "closes past 0.65". The comments and the decisions file say "past".
- The grab lives in `HandsIO.grab`, not `HandsIO.gates[side]`. That keeps the ghost (`ghost.py` reads `gates.get(f)` for the pinch names), `tools/hands_probe.py` and the outputs tooling untouched.
- `held_gate` (learn while pinching) is unchanged: making a fist during a learn writes no gate. This is written up as a decision with the alternative.
- The grab sends no DAW note.
- `hands/signal.py` is untouched. The grab reuses core's `Gate` and C4's curls; the prompt's WP table had listed `signal.py`.

## Concerns
1. **`config.toml.rig` was not edited.** It is not in the repo. Per the memory notes, it is the owner's `~/Hyperspace/config.toml.rig`, and the hard rule forbids touching `~/Hyperspace`, so I neither read nor wrote it. The line lives in SETUP.md's example instead, and hand-check draft U.8 asks the owner to add `hands = true` to the projector entry. It changes nothing in practice, because the switch already defaults on. If the orchestrator meant a new repo file named `config.toml.rig`, that is a one-line follow-up.
2. **`position` is absolute.** With the fixture mapping, grabbing snaps the shape to the hand's pose rather than catching it where it is. The owner's "follows 1:1" may want a relative op (plan 28) or a depth/scale choice. Noted in U.7; nothing was built for it.
3. **The thresholds are tuned only on synthetic hands.** Real fists may not reach 1; that is why the close threshold is a low 0.65.

## Files
- Decisions: `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/C5.md`. Five register-row drafts, hand checks U.6–U.8 and as-built notes.
- `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/C4.md`: one sentence added to its first row draft (only the pinches and the grab are gates, not a flick).
- Changed in the repo, all under `hyperspace-python/`:
  - `hyperspace/hands/{core,__init__,panel}.py`
  - `docs/SETUP.md`
  - `tests/{fake_hands,test_hand_names,test_hands,test_hands_boundary,test_hands_dance,test_hands_grab}.py`
  - `tests/fixtures/grab-follow/grab-follow.json`
