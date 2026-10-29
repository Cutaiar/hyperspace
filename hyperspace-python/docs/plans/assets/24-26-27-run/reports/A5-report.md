# A5 report: plan 26's docs (the render graph as built)

- **Status:** DONE_WITH_CONCERNS (the concerns are small; nothing blocks the merge)
- **Branch:** `plan-26-a5-docs`. **Base:** `14103cb` (contains `f00a494`, the A2b merge), confirmed after `git reset --hard FETCH_HEAD`.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/193, into `plan-24-26-27-integration`. Not merged.
- **N = 209** (the last register row; plan 26's rows are 169–209).
- **M = 218** (the last hand check; group V is 191–218, after W).

## Commits
- `45dc13f` Plan 26 A5: the render graph as built; register rows 169-209 and the owner's plan-26 decisions
- `3695f6c` Plan 26 A5: hand checks V 191-218; the testing guide's render-graph entries
- `ee0687a` Plan 26 A5: ENGINEERING section 2, ARCHITECTURE (md and html), CHECKPOINT, the plans README
- `388f79d` Plan 26 A5: the handoff says the run finished (PR #193)

## Files changed (docs only)
- `docs/plans/26-render-graph.md` (new)
- `docs/DECISION-REGISTER.md`, `docs/DECISIONS.md`
- `docs/plans/11-hand-checks.md`, `docs/TESTING-GUIDE.md`
- `docs/ENGINEERING.md`, `docs/ARCHITECTURE.md`, `docs/ARCHITECTURE.html`
- `docs/CHECKPOINT.md`, `docs/plans/README.md`, `docs/plans/27-device-registry.md`, `docs/plans/24-26-27-handoff.md`
- Not changed: `docs/plans/24-party-wishlist.md` — C7 had already made its priority paragraph link `26-render-graph.md` and `27-device-registry.md`, which both now exist; nothing left to do.
- `git diff --stat 14103cb -- hyperspace/ tests/ tools/` is empty.

## Numbering
- Register rows 169–209, by WP: A0 169–175; A1 176–181; A2 182–188 (187 = A2's calibration row merged with A3's 16:9 fit); A2b 189–190; A3 191–195 (195 = A3's hands-node row merged with A4's consumer-edge timing row); A4 196–203; A4b 204–209.
- Hand checks: 191 V.1, 192 (new: every preset by eye), 193 V.3, 194 V.4 + V.2 folded, 195 V.5, 196 V.6, 197 V.7 reworded (world-space strokes by default), 198 V.A2b.1, 199 V.8, 200 (new: hands-orbit turns only the shape), 201 V.9, 202 V.11 reworded, 203 V.16, 204 V.12, 205 V.10, 206 (new: in the scene on the projector, a layer on the glass), 207 V.13, 208 V.14, 209 V.15, 210 V.17, 211 V.18, 212 V.19, 213 V.20, 214 V.21, 215 V.22, 216–218 V.A4b.1–3.
- TESTING-GUIDE: Part 1 "The render graph" L82–L94; Part 2 B39, B40 (hand camera), C6, C7 (projector), D16–D18 (glass + projector). The prompt says the render ones go in Part 1; I put the ones that cannot run without a projector, the rig or a real hand under Part 2's hardware sections (as the guide is organised), and the rest — including the in-scene hands with the synthetic tape — in Part 1.

## The facts recorded (each checked against the code and the ledger)
- Goldens on the branch: 556 (130 distinct), counted from `tests/golden/frames/frames.json`: 368 + 46 solo + 12 solo-through + 1 cap = 427 (A0); + 115 in-scene/depth + 2 history+hands = 544 (A3); + 8 hands-lines = 552 (A4); + 4 cloud = 556 (A4b). GL_RENDERER "Apple M3 Max", GL_VERSION "4.1 Metal - 90.5".
- Moved: A2 184 (zoom as world scale, copies in the world, party-mandala's pan converted, float32 face positions); A3 122 (the hands through the shared camera: 47.6° vs 38°; sanctioned although the prompt said A3 must match A2); A2b 218 (212 + 6 after the A4/A4b merge; world-space strokes, the owner's decision); every other merge moved none.
- Default eye's maximum vertex error: 2.3e-13 px (float64), 1.1e-4 px (float32), bar 0.5 px. A1 matched all 427. The modulation lag (ARCHITECTURE §2) untouched, plan 28's.
- Rulings recorded: clouds follow the device list; a `cloud` kind in JSON is an unknown kind until plan 28 (register 197, 207; ENGINEERING §2; plan file); stroke default = world space, screen space the registered option (189); `tests/fixtures/` gitignored, fixtures force-added (plan file, ENGINEERING §16).

## Measured HTML counts (B5's method, from `hyperspace-python/` on the branch)
`find hyperspace -name '*.py' | wc -l` → **56** modules; `find hyperspace -name '*.py' -exec cat {} + | wc -l` → **41,792**; `find tests -name '*.py' -exec cat {} + | wc -l` → **46,985**; `ls tests/test_*.py | wc -l` → **80** test files; `ls hyperspace/shaders/fx/*.glsl` less `_lib` → **13** effects; `len(geometry.SHAPES)` → **26**; `len(patterns.MODES)` → **17**. The masthead, the closing stat row and the §07 dek ("41,800-line") were updated; "Eleven parts" became "Twelve parts" with the Graph row.

## What a document said that the code does not do, and what I wrote instead
- `ENGINEERING.md` §2 said the transform projects to 2D on the CPU, and described "The frame" as a pass list: rewritten for the graph and the shared camera.
- `DECISIONS.md`: "The CPU transforms through `project()`…" (now the parity oracle only), "the ghost hands … in a fixed camera framing the box … never in the look-back history", "Hands through … `Renderer._pipeline`": rewritten to what the code does.
- `ENGINEERING.md` §12 ("The ghost has its own fixed camera framing the box") and §14 ("The echoes and the dream never hold the hands"): corrected (the shared camera and the calibration; the history holds the hands only when a preset's graph wires it).
- `ARCHITECTURE.md` cited `test_the_history_never_holds_the_hands_in_any_state` and `test_the_history_never_holds_the_dim`, both renamed by A3; hand check 103 cited the first: all now cite the new names. (The historical plan files 15 and 21 still cite the old names; left as the record of their time.)
- A0's draft V.2 / ENGINEERING's naming paragraph used `dream.3.mix` as an example; no `dream` instance exists in the code — the extended paragraph says so.
- A4b's decisions file says "A4's JSON can name a node `{"kind": "cloud"}`"; the code (`NODE_KINDS`) and the ruling say it cannot: the docs follow the code.
- A4b's register draft said "To reverse: set `TIMED = False`" for the cloud's SYSTEM line; since A4, `Graph.timed` lists every solid geometry a scene draws whatever its `TIMED`, so row 209 says "local to `Scene.run` and `Graph.timed`".
- B5's four "nothing on screen draws it yet" sentences (ARCHITECTURE §5, ENGINEERING §5, check 190, TESTING-GUIDE L76) and the same sentence in `27-device-registry.md` B4 now say the `cloud` node draws it and point at checks 216–218 / L84.

## Test ids cited, and their collect count
Every `tests/…::name` the new or changed text cites (extracted from the diff and the new plan file by a script; brace forms expanded): **93 ids**, `uv run pytest --collect-only -q <ids>` → **148 tests collected, no error** (some ids are parametrised).

## Gates
```
uv run pytest -q          2190 passed, 2 skipped in 174.64s (on the base; docs-only since)
uv run ruff check .       All checks passed!
```

## Concerns
1. Hand check 192 / L83 compares the live app with the goldens' `solo` PNGs by eye; the goldens are 8 frames in, silent, LFOs at rest, so the pose differs — the check says to judge size, weight, colours and effects, not the angle.
2. The checks that need a preset with a `graph` section use the `hands-lines` fixture and four hand-made variants in the copy's `presets/`; group V's preamble (and the guide's) tells the tester to delete `[library] path` from the copy's config first, so nothing is ever copied into the shared Drive folder.
3. D18 / check 213 asks for "save the show" before the restart (the `ghost.2.*` settings are the show's session); the exact control name for saving a show was not re-checked in the UI.
4. The TESTING-GUIDE glossary has one pre-existing out-of-order pair (Synthetic tape / Sink), not mine; left.
5. The handoff's new top line names PR #193 as the last WP; the integration → `main` PR does not exist yet, so it is not named.

---

# Fix report — review round 1 (FIX BASE 388f79d → 7a30689, pushed)

1. Checks 102/103 *Fail* pointers: `Renderer._pipeline` → `graph.default_graph` / `Output.settle` (102) and `graph.default_graph` / `graph.Capture` (+ `Wiring.history`) (names verified in graph.py).
2. Check 195 moved to the rig in both places: order item 9 ("193, 194 and 196–198 on the laptop"; "206 and 213 … with 195 and 208") and group V's preamble ("191–194, 196 … laptop alone; 195, 206, 208 and 213 the glass and the projector").
3. 26-render-graph.md: C6 merged into integration just before A0, and A0's goldens held there (moved none) — the "in before A0 recorded" wording is gone.
4. ARCHITECTURE.md Graph row: instances `ghost.2`, `fx.acid.2` (the HTML row names no instances; nothing to mirror).
5. CHECKPOINT keeps the clause: nobody has watched the lifted shapes / Klein bottle or seen the FACES page and patterns on the Mac (checks 120, 121).
6. TESTING-GUIDE step 2: plan 22's entries are plan 22's, "which is on `main`".
7. Register row 173: "hashing one 33 MB frame".
8. DECISIONS decision-16 render row: "adapters only `feed`" removed.

Checks: `git diff --stat 14103cb -- hyperspace/ tests/ tools/` empty; the touched test ids (check 103's headless line) `--collect-only` → 2 tests collected; ruff unaffected (docs only).
