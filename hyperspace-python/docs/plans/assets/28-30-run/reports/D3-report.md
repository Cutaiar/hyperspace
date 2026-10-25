Final N = 232 (register rows 214–232), final M = 231 (hand checks 220–231, group X).

# D3 report: plan 30's docs

**Status:** DONE.

- **Base:** d5d905f (`git reset --hard FETCH_HEAD` worked); branch `plan-30-d3-docs`.
- **Commit:** d733bdf "Plan 30's docs: shader nodes as built, register rows 214-232, hand checks 220-231".
- **PR:** https://github.com/Cutaiar/hyperspace/pull/218 (into `plan-28-30-integration`).
- Docs only: no code, no test, nothing under `hyperspace/library/`. Commit trailer is the session's (Opus 5.5), as D2 did.

## Rows numbered (draft → row)

| Draft | Row |
|---|---|
| D0 1: the end keeps the name `Fx` | 214 |
| D0 2: an off effect read through | 215 |
| D0 3: the pool | 216 |
| D0 4: the effect node's name | 217 |
| D0 5: a SYSTEM line only for an effect that ran | 218 |
| D1 1: keys `after` / `into` | 219 |
| D1 2: the vocabulary | 220 |
| D1 3: a refused placement costs only that effect + **D1 4: loops refused at read and build** | 221 (**fold**) |
| D1 5: dormant | 222 |
| D1 6: how an effect sits on an edge (presenters, fx_on) | 223 |
| D1 7: the words | 224 |
| D1 8: the fixtures' extra values | 225 |
| D2 1: the placed chip's grid | 226 |
| D2 2: the status line's count | 227 |
| D2 3: two vocabularies | 228 |
| D2 4: a dormant placement shows as placed | 229 |
| D2 5: a faces-aimed placed chip | 230 |
| D2 6: the `VALUE` port | 231 |
| D2 7: the faces target stays an inner chain | 232 |

One fold: D1's refusal row and loop row (both "a placement this build cannot honour → that effect's default placement") → row 221. (D1's report said 7 drafts; its decisions file has 8.)

Rows marked: **176 superseded by 214, 215** (the brief said 177; 177 is the history row, 176 is the "FX node is the chain" row); **197 superseded in part by 221**; **196 amended by 219**; **180 amended** (the key holds `FxState.names()` and the placements). Answer sheet extended 214–232.

## Checks numbered (X.n → number)

X.1 → 220, X.2 → 221, X.3 → 222, X.4 → 223, X.5 → 224, X.6 → 225, X.7 → 226, X.8 → 227, X.9 → 228, X.10 → 229, X.11 → 230; **231 new** (two palettes with different centres on two outputs, a `two-palettes.json` variant; its section checked headless with `read_graph`: no notes, `palette ×2`, chips `into output 1` / `into output 2`). TESTING-GUIDE: L95 (220), L96 (221), L97 (230), L98 (223), L99 (225), L100 (226), L101 (228), L102 (229); D19 (222), D20 (223), D21 (224), D22 (227), D23 (231).

## Files
- `docs/plans/30-shader-nodes.md` (rewritten as built), `docs/DECISION-REGISTER.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/ARCHITECTURE.html`, `docs/ENGINEERING.md` (§2; one count in §16), `docs/plans/11-hand-checks.md`, `docs/TESTING-GUIDE.md`, `docs/plans/README.md`, `docs/plans/24-party-wishlist.md`, `docs/CHECKPOINT.md` (plan 30 paragraph only).
- Left to N6 as briefed: ARCHITECTURE §2's frame step table and the lag rule (and its "modulation is not a graph" sentence), the masthead counts, "Decided not to build"'s plan 28 line, CHECKPOINT's other sections.

## Doc statements corrected
1. Check 194 / TESTING-GUIDE L85: "`fx` falls near 0 with the effects off and comes back" — the end's `fx` line now always reads 0.00; rewritten to the effects' own lines coming and going.
2. "all 556 frames match" / "556 golden frames" in check 191, L82, the glossary, ENGINEERING §2 and §16, ARCHITECTURE §2, ARCHITECTURE.html — now 580 (136 pictures).
3. ENGINEERING §2's default order `history → fx` and the FX row of the node table (the chain "one node per pipeline") — now the run of effect nodes then the `Fx` end; DECISIONS' Fx row likewise.
4. D1's draft X.5 had "projector as output 1, glass as output 2"; the guide's two-output rig (D1 / check 101) has the glass as output 1, so `into: output.2` folds the **projector**, which is the presenter — the checks say so and use it to exercise the half-float Handoff.
5. D2's as-built note "the page-fit tests do not cover placements" is stale (`test_the_page_fits_with_three_placed_effects` exists); not carried over.
6. The prompt calls `VALUE` "a third port type"; it is the fourth (`MASK` exists) — said in the plan file's departures.

## Gates
```
uv run pytest -q        -> 2327 passed, 2 skipped in 194.45s (0:03:14)
uv run ruff check .     -> All checks passed!
```

## Concerns
- None blocking. The two-palettes check (231) relies on `fx.palette.2.*` values landing for a placed instance 2; the section reads clean, but no test loads that exact preset.

## Fix round 1 (commit 5c98e8a, pushed to PR #218)

1. Check 231's Headless line now says "(neighbours only: no test loads this configuration, two placed instances of one file into two outputs)". Row 225's rough edge and the plan file's "What no person has verified" say the same.
2. `begin` described in words in row 216 and the plan file: it hands out the pool's first framebuffer, asking for at least the textures the pool already holds (two at the least). The wrong expression `pool(size, 2)[0]` is gone.
3. Answer sheet: row 197's answer column is now empty, following row 108. Row 228's checks read "228, 229", in the sheet and in the row.
4. TESTING-GUIDE heading is now "## Shader nodes (L95–L97 on the laptop; L98–L102 on the copy)". The D20–D22 cross-references ("Part 1, \"Shader nodes\"") still match it.
5. ARCHITECTURE.html: "580 golden frames pin every factory preset's picture, and the fixture presets', to the byte."
6. `docs/plans/README.md`'s `28-node-editor.md` entry is untouched; it is left to N6.

```
uv run ruff check .   -> All checks passed!
uv run pytest -q      -> 2327 passed, 2 skipped in 166.20s
```
