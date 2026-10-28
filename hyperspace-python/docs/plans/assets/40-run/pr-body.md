Plan 40, **patches**: a group of nodes and its boundary, saved once, spawned anywhere. Spec `docs/plans/40-patches.md` (every decision D1–D10 the owner's, 2026-10-27), build plan `40-patches-build.md`, run records `docs/plans/assets/40-run/` (ledger, briefs, reports, reviews, decisions). Seven tasks, one sub-agent each in its own worktree, two task reviews, one plan-level review, a fix pass, docs last. **Do not merge until the two open questions below are answered** (or merge and answer them as follow-ups — both are one-line changes).

## The decisions as built (the owner's column)

| # | decision | built |
|---|---|---|
| D1 | the word | `patch.py` → `modgraph.py` (`ModGraph`, `build_modgraph`, `modgraph_notes`); `patch` is the owner's thing |
| D2 | open pins + splice + the chip | a spawn attaches nothing; a drop on a matching cable splices like **insert**; **wire as saved** lands the saved names when free, refuses in words otherwise; `patches.check` refuses any crossing wire in a file |
| D3 | ask, in one sheet | `ui_routing.modal` draws the conflict sheet ahead of Replace / Keep: a row per conflict, **keep all existing** / **take all**, the wants, **Spawn** / **Cancel**; the hands learn nothing while it is up (`Learn.hold`) |
| D4 | saved, folded until `+` | `groups` in the preset; a folded group hides its members and internal cables, re-ends crossing cables at typed pins and boundary-param rows; `+` opens it in place in a tinted region; the one sanctioned exception to the WYSIWYG rule |
| D5 | only the boundary | `lift` and `spawn` keep members' values only |
| D6 | retired outright | `library/fx/*.json`, `Presets._fx_module`, `graphmigrate.module_runs` gone; `library.RETIRED_MODULES = ("fx",)`; no conversion |
| D7 | schema | `groups` writes `/8`, only when non-empty; absent → no groups; nothing in the library rewritten (**see question 1**) |
| D8 | control window only | nothing on the desk; Dylan's files untouched (`git diff main --stat -- apc40.py midi.py bindings.default.json ui_desk*.py` is empty) |
| D9 | preselected to the patch | every row starts on the patch; **keep all existing** flips |
| D10 | the FX page stays | `ui_fx.py` untouched; its fx module-preset strip (save · as… · reset — the retired mechanism's own UI, which P5 said did not exist) is hidden through `ui_presets.strip` |

## What else is in it
- **P4**: `devices.wants` (connected / lost / off / not in this rig, rows in words), once a frame; the **N devices missing** chip on GRAPH and the PRESET strip; SYSTEM's "wanted by the preset" lines; the registry's status-change event says "apc40 connected — 26 controls live" / "apc40 lost — …"; a spawn says what waits.
- **The renderer learns nothing**: `graph.py` and `render.py` unchanged; no golden re-recorded; `frame-signatures.json` unchanged; a grouped preset builds the same `graph.signature` as its ungrouped twin (every factory preset) and draws the same goldens (8 grouped-twin proofs).
- **Through the doors, one undo step each**: Group, Ungroup, Rename, a title drag, a member dragged out, a spawn, a splice, wire as saved. No file is written by a spawn (byte-compared); save as patch writes `<library>/patches/<slug>.json` and nothing else.
- **Plan 38 fix riding along** (its own commit, 86795d5): the PROJECTOR inset's `add_rect` call raised `TypeError` the first time it drew (wrong argument order for imgui_bundle), so the inset never drew since #270; one line, with a stub-texture test.

## Tests (this Mac, Apple M3 Max)
| | |
|---|---|
| fast tier `uv run pytest -q` | 4320 passed, 2 skipped (base 4122) |
| full suite `--all` | 4551 passed, 2 skipped |
| goldens `--all -m golden` | 144 passed (136 + 8 grouped-twin proofs), none re-recorded |
| ruff | clean on every file the plan touched (25 pre-existing errors elsewhere, untouched) |

## Hand checks at the machine
Group **AK**, checks **394–401** (register rows 501–536) in `docs/plans/11-hand-checks.md`: group and ungroup; save and spawn; splice; the knobs come with it and the sheet asks; not connected, said (APC40 unplugged, then plugged in); not in this rig, said (the laptop config); the fx modules are gone, the FX page is not; twice. Nobody has seen any of the drawing yet: the folded group node, the tinted region, the sheet, the browser drag, the PRESETS patches fold.

## Both Macs
Update together before a preset with `groups` is shared: an older build **refuses** an `/8` file (the schema ladder's rule), it does not drop the key. Presets without groups keep saving `/7` for now (question 1).

## Two questions for the owner (register rows, "pending the owner")
1. **Schema of an ungrouped save** (ruling 15): built as "`/7` for no groups, `/8` for a grouped one" per the build plan's byte-for-byte proof; the reviewer notes this revives the "lowest schema that loses nothing" rule you overturned with row 394 (every save the newest schema). Recommendation: every save writes `/8`, factory files and the Drive library migrated forward as plan 36 did (schema line only). One rule in `preset.py` plus a migration run.
2. **Wire as saved on a fed port** (ruling 17): it refuses ("output.all.image is taken") as D2's text says; should there be an explicit take-over chip? Without one, in any host whose run already feeds All outputs the outlet always refuses.

## The controller's rulings
`docs/plans/assets/40-run/decisions.md`, 22 of them, each a register row in 501–536: the base and its merge (#266 came in with the docs), sub-agents on Opus, rows renumbered from 471–495 to 501–525 (plans 37–39 and #275 took through 500), T0's wider rename, the FX strip hidden (D6 + D10), `RETIRED_MODULES` by name, the party generator's values inline, `groups` is `/8`, a spawn's conflicts rule scheme by scheme (a hand axis read through a modifier is no conflict — the spec's D3 example, for your eye), the T3 examples against `party-trip`'s real contents, the plan 38 fix riding along.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_012HeFHywoiCGN2SbvC1U35W
