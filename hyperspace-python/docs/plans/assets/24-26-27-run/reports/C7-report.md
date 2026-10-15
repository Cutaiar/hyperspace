# C7 report: plan 24's docs

- **Status:** DONE_WITH_CONCERNS (the concerns are about older docs; nothing blocks the merge)
- **Branch:** `plan-24-c7-docs`. **Base:** `2336df6` (the merge of C3, PR #182), confirmed after `git reset --hard FETCH_HEAD`.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/186, into `plan-24-26-27-integration`
- **N = 139** (the last register row). A5 and B5 continue at 140.
- **M = 167** (the last hand check). V and W continue at 168.

## Commits
- `24d10df` Plan 24 C7: register rows 110-139 and the owner's plan-24 decisions
- `7076353` Plan 24 C7: hand checks T 144-147 and U 148-167; the testing guide
- `c59bf80` Plan 24 C7: the party fixes as built; ENGINEERING, SETUP, README

## What I wrote
- **`docs/plans/24-party-fixes.md` (new).**
  - Plan 24 as built, one section per WP (C1–C6), each with At the machine, Code and Tests.
  - The coverage table per preset. 0 of 23 meet the bar, and the file says no preset was remapped.
  - What no person has verified, and the known rough edges.
  - What the launch prompt asked for that was not done as written.
- **`docs/DECISION-REGISTER.md`.**
  - A new section, `## The party fixes (plan 24)`, with rows 110–139, plus their answer-sheet lines. The header's row ranges are updated.
  - Rows 42 and 44 are marked superseded in part. Row 42: its clip-stop bar was retired by #158, and clip stop 8 is now SAVE. Row 44: superseded by row 112 for the preset's faders.
  - Rows 61 and 73 get a note that plan 24 changed their diagrams.
- **`docs/DECISIONS.md`.**
  - Owner decisions 17–21, 23 and 24 are now `owner` rows.
  - Rewritten: D5 (the strip under SHIFT), D6 (MASTER and not the faders; SAVE and the four toggles added), D7 (pickup from where the fader is), and "the desk never overwrites a preset" (the two-handed save, never trashed).
  - New rows:
    - S1–S8 belong to the preset; the relight; the desk log; the coverage report; templates; ranked click-to-map.
    - The dance sources; the grab; the opacities; hands on the projector; the palette fold.
    - The run rules: no preset is edited, and new params default to today's picture.
  - The code WPs' choices are rows marked `row N`.
- **`docs/plans/11-hand-checks.md`.**
  - Group T, 144–147: the pad's four checks, taken from TESTING-GUIDE §(f).
  - Group U, 148–167:

    | Checks | What they cover |
    | --- | --- |
    | 148 | the two-handed save, ten times |
    | 149 | the toggles |
    | 150 | the relight |
    | 151 | the desk log |
    | 152 | the fixture's faders and a fader learned from the desk |
    | 153 | the strip under SHIFT and the migration |
    | 154 | opacity |
    | 155 | coverage against what the owner sees |
    | 156 | templates |
    | 157 | the ranked offer |
    | 158–162 | the dance sources |
    | 163, 164 | the grab and the grab mapping |
    | 165 | the projector |
    | 166 | the palette fold on a fader |
    | 167 | a saved palette and the strip |

  - The Order list, the group-U branch note and "What no test covers" are updated.
- **`docs/TESTING-GUIDE.md`.**
  - §(f) renumbered to 144–147, in the entries and in the Summary.
  - New entries: L69 palette, L70 saved palette, L71 opacity, A24–A32 desk, B30–B36 hands, C5 projector.
  - Summary, order, branch note and the judge list are updated.
  - Entries plan 24 made untrue are corrected:
    - A2 and A4: faders are under SHIFT now.
    - A14 step 9: only clip stops 1–7 are free.
    - A16 step 6: S2 is now mappable, so the step uses SM instead.
    - A17: S1 under SHIFT.
    - L1: the plan-24 migration lines.
    - L35: S8 is now "· global layer".
    - L37: S1–S8 are dark, and G6·8 is Save.
    - The glossary: clip-stop row, invariant, track faders.
- **`docs/ENGINEERING.md`.**
  - §6: the click-to-map offer.
  - §8: the desk table (SM, SAVE, toggles, S1–S8 on both layers, scene launch 5), the fader rows, the template format, the coverage tool, the two-handed save, the relight, the desk log, and pickup on a load and on a switch.
  - §12: the dance sources and the grab.
  - The Effects paragraph inside §2: thirteen effects, `@mix`, the palette, strip packing. Nothing else in §2 was touched.
  - §16: fixtures (force-added) and the coverage test.
- **`docs/SETUP.md`:** an APC40 at-a-glance list with the two-handed save. C5's `hands = true` is kept.
- **`docs/plans/README.md`:**
  - New entry for `24-party-fixes.md`.
  - The prompt's entry now reads "the launch prompt plans 24, 26 and 27 were run from".
  - The wishlist entry names its three plans.
  - "numbered 1–167 (current as of plan 24's docs …)".
- **`24-party-wishlist.md`:** only the priority paragraph's renumbering note changed. It points at `24-party-fixes.md`, `26-render-graph.md` and `27-device-registry.md`.
- **Not touched:** ARCHITECTURE.md/.html, CHECKPOINT.md, docs/plans/26-* and 27-*, and §5 of ENGINEERING.

## Drafts deduplicated or corrected against the code
- **Merged rows.**
  - C4's "no setup params / DAW / Learn" row and C5's grab row of the same kind became row 129.
  - C4's HANDS-page column row and C5's grab-glyph row became row 130.
  - C6's "mode is int" became part of row 136.
- **C4's `routing.LANE_SCHEMES` / `ui_routing.SOURCE_ORDER`.** On the base neither name exists any more: B2 moved the schemes to the devices. The hands device declares `schemes = ("hand", "hands")` in `hands/device.py`. I documented that, not the draft.
- **C6's palette param count.** The draft says "21 params + the 6 own". `palette.glsl` has 20 `@param` lines, so the docs say twenty.
- **C6's U.1.** It cited tests that do not exist by that name ("narrow slice is one hue", "routed mix moves"). I cited the real ones instead, for example `test_every_palette_param_takes_a_route`.
- **C2's U.5.** It used only the fixture. I added the required "a fader learned from the desk" step (check 152), backed by `test_a_track_fader_is_learnable_on_the_preset_layer`.
- **The prompt's "each hand source … learned onto a param".** A hand Learn lands only the axes (row 129), so checks 159–164 put the sources on params through ROUTING and say why.
- **C6's U.2 "load from the fx preset list".** The fx module strip is the FX page's section strip, so check 167 says that.
- **C2's opacity check.** TRIP has points off, so L71 ticks Points on first.
- **Test counts are the ones collected on the base:** desk_trust 22, desk_faders 13, coverage 11, templates 11, hands_dance 18, hands_grab 11, fx_palette 8.

## Docs that say what the code does not do (found, not plan 24's, left as they were)
- **TESTING-GUIDE L1** still expects "eight `added note:…:52 → preset.save_new`" lines and G6·1–8 → `preset.save_new hold` on ROUTING. Since #158 those rows are retired: `routing.RETIRED_ROWS` drops them. I only added the plan-24 bullet.
- **DECISIONS "The cheat sheet…" row** says the pad's MENU "held, it now saves a new preset". `PAD_REMAP` drops `pad:MENU → preset.save_new` (START/BACK unbound, #166).
- **DECISIONS pinch-switch row** cited `hands/signal.py`, but `Gate` is in `hands/core.py`. I corrected it, because the new grab row sits beside it.
- **Hand checks order item 4 (check 90, "the home in git")** is superseded by plan 25. I did not touch it.
- **The launch prompt's C5 text says to set the projector in `config.toml.rig`.** That file is the owner's, in `~/Hyperspace`. The docs say this, and check 165 asks the owner to add the line.
- **The prompt's WP table lists "two named palettes" in `library/fx/`.** None ship, per decision 23. The plan file says so.

## Gates
```
uv run pytest -q          2036 passed, 2 skipped in 138.44s
uv run ruff check .       All checks passed!
uv run python tools/desk_coverage.py --check   rc=0
git diff --stat 56c7d44 HEAD -- hyperspace-python/hyperspace/library/   (empty)
```
- I ran every test node cited in groups T and U and in the plan file, as whole files plus the two single nodes: `127 passed in 5.98s`.
- A script confirmed that every cited `tests/…::name` exists.

## Concerns
- The pre-existing doc staleness listed above is for whoever owns those sections.
- I edited the Effects paragraph inside ENGINEERING §2 (which A5 owns) because the dispatch asked for the FX section. A5 should keep it when rewriting §2.
- Commit trailers use the session attribution (`Claude Opus 5.5`), as the earlier C WPs did, not the brief's "Fable 5.1".

---

# Fix report, review round 1 (commit `c24b716`, pushed; PR #186 body updated)

1. (Important) TESTING-GUIDE L1: dropped the "eight `added note:…:52 → preset.save_new`" expectation; ROUTING now lists X → `output.dim`, B11 → `preset.home`, G6·8 → `desk.save`, scene launch 1–4 → the toggles, and says an old file's bar rows are dropped with a note; "Later" and the second-launch bullet say SAVE (and its every-launch "SAVE not added" line). Hand check 57 had the same stale facts: fixed the same way.
2. DECISIONS cheat-sheet row: "START and BACK are now unbound".
3. 24-party-fixes.md: "K4 (pattern mix) and the pattern knob (D4; D7 on hands-pinch)".
4. Check 156 and A31: three rows, not the seven of the expanded desk (`EXPANDED`).
5. SETUP.md: blank line restored before "To check the device without the app".
6. ENGINEERING §8, register row 122, DECISIONS templates row: the factory has no templates; the folder need not exist.
7. ENGINEERING palette paragraph: before the dim, and before the hands unless an output sends them through the effects.
8. 24-party-fixes.md: PRs listed in merge order.

```
uv run pytest -q      2036 passed, 2 skipped in 163.77s
uv run ruff check .   All checks passed!
```
