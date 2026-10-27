# Plan 37B — build plan

Spec: [`37b-faces.md`](37b-faces.md), the authority. Read its "What is
there today" map before any task; its file:line references are to
`main` @ f2351a0 and may have drifted. Decisions D1–D5 are the owner's;
D1 (which patterns stay) is answered from T0's sheet and blocks T1 only.
Build the rest on the recommendations until he says otherwise, and say
in the report which ones you built on.

Branch `plan-37b-build`, cut from `main`. Work in `hyperspace-python/`.
Run tests with `uv run pytest -q …` from there (the fast tier; `--all`
for everything, `--all -m golden` for the goldens). This workstream does
not depend on plan 37A and must not wait for it; if 37A has merged first,
cut from that `main` and keep its `frame.made` calls at the end of every
face pass you rewrite.

## Global constraints

- **The rule.** The graph on GRAPH is the whole truth (plan 36). No
  fallback: an unwired or empty faces port is plain faces, said in words.
  No code reaches the pattern except through a drawn cable.
- **Pictures don't move for a kept mode.** Every golden of a preset on a
  kept pattern, and every faces fixture (`faces-media`,
  `media-chain-faces`, `switch-faces`, `delay-faces`, `echo-faces`,
  `resize-faces`, `CLOUDED`), is byte-identical after T1 and T2. The
  analytic bypass is kept exactly where it runs today (the pattern wired
  straight into `shape.faces`) so that holds. Say in the commit if any
  golden moves and why; none should.
- **Old files.** A `/7` file reads only as the explicit one-way migration
  to `/8` in `graphmigrate` (mode index → name, the two renames, a
  retired mode → its nearest kept with a note). Saves write `/8` only.
- **Never touch the owner's Drive library** or `~/Hyperspace`. The
  migration tool is changed and tested on copies; the owner runs it.
- **Dylan's files.** `apc40.py`, `midi.py`, `bindings.default.json`, the
  desk diagram and `ui_desk*.py` are untouched. A renamed param keeps
  its old name as an alias in `params.py` (as `view.bmp_alpha` does) so
  the desk rows and the APC40 ccs land where they did.
- **The depth-pass bound** (`fa.max() · 2.8`, render.py ~2869) holds for
  every kept mode: a test clamps each mode's shade to [0, 1] at the
  extreme inputs.
- **Style.** Match the surrounding code: docstrings in the repo's voice,
  comments that cite the plan (`# plan 37B T<n>: …`), no new
  dependencies.
- **Before reporting DONE:** `uv run ruff check` clean on the files you
  touched; `tools/check_glsl.py` clean; the fast tier passing; `uv run
  pytest -q --all -m golden` passing with nothing re-recorded. Report the
  numbers. The controller runs the full suite once before the final
  review.
- **Commits.** One or more per task, each message ending with the
  attribution lines the session gives you. Never push, merge or rebase.
  Never dispatch subagents.

## Task 0: the sheet (spec F1, for D1)

Goal: the owner can answer "which patterns stay" from one picture.

1. `tools/pattern_sheet.py`: one row per mode, four tiles — the neutral
   inputs, then SCALE/GLOW/WARP driven, COLOUR/HUE driven, SHARP/SPREAD
   driven — at 256², on the patterns' clock frozen at one phase; the
   mode's name and its count of factory presets under it, plus the
   count in a library given by `--library <path>` (the owner passes the
   Drive path; the build passes `tests/fixtures/presets`).
2. Write `docs/plans/assets/37b-patterns/sheet.png` and a `counts.md`
   beside it (mode → factory presets → library presets).
3. No code under `hyperspace/` changes in T0.

## Task 1: the kept modes; a mode by name; schema `/8` (spec F1, D1, D2, D5)

Goal: the pattern shader is a table of the kept modes, a preset names
its mode, and an old file migrates once.

1. `patterns.MODES` becomes the kept list in the owner's order; each
   mode's GLSL is a function `mode_<name>(vec2 uv, float fid)` in a
   table `design()` indexes by the mode's position; retired functions
   and `MODES` rows are deleted (D5). `finish()` and the `pattern()`
   contract are unchanged. `tools/check_glsl.py` compiles the result.
2. `view.pattern` is an enum over `patterns.NAMES` as today, but the
   **file** holds the name (`"plasma"`), never the index.
   `patterns.RETIRED: dict[str, str]` maps each retired name to its
   nearest kept (the owner's pairs from the sheet; the recommendation's
   defaults: plaid→moire, bloom→caustic, meter→rings, pulse→rings,
   marble→plasma, truchet→hex, kaleido→spiral), with a load note "faces:
   `plaid` is retired, showing `moire`".
3. **Schema `/8`** (`preset.py`'s ladder, `graphmigrate`): `/7` → `/8` is
   the mode index → name, plus T2's renames; `/8` is saved and nothing
   older. `tools/migrate_library.py` moves a library to `/8` with the
   same backup rule as `/7`. The 25 factory presets are regenerated from
   `tests/fixtures/factory-sources/` as plan 36 did (or from their `/7`
   files if the sources are not kept current: say which).
4. Delete the "appended, never inserted" test; add: every kept mode
   compiles and draws something other than FLAT at the neutral inputs;
   every factory preset's mode is a kept name; a `/7` file on a retired
   index migrates to the mapped name with the note; a `/8` file with an
   unknown name is refused in words.
5. Goldens: every pattern preset's goldens unmoved (the kept modes'
   GLSL is moved, not changed).

## Task 2: the faces' input like any other (spec F2, D3)

Goal: no fallback; the fit and the mix live on the shape's port.

1. `Shape.faces()` / the face passes: when the wired picture's node
   `reads` nothing this frame, the faces are **plain** and
   `shape.said = "faces: <node> made nothing"`; delete the fall-back to
   the pattern (graph.py ~3135). The analytic bypass is kept only for
   `pattern → shape.faces` with nothing between.
2. `fx.face_map` → `shape.faces_fit` and `view.pattern_mix` →
   `shape.faces_alpha` in the registry, with the old names as aliases
   (`params.py`, the alias table) so routes, desk rows and the APC40 ccs
   resolve; `graphview` lists both on the shape node beside the port
   (they already "belong to the shape" by convention). `/8` renames them
   in files (routes, desk rows, values).
3. Tests (`test_graph_faces.py`, `test_media_faces_aux.py`): an empty
   channel wired to the faces draws the plain goldens and says so; the
   aliases resolve both ways; the shape node lists the two params;
   `party-faces` goldens unmoved.

## Task 3: the FACES page follows (spec F1, F2)

1. The browser shows `patterns.MODES` (the kept ones); the swatch round
   robin is over them.
2. The faces / cut-through / mix row reads `shape.faces_alpha`; the
   page's about line says a channel over the faces is a `composite` on
   GRAPH (words only, no button).
3. `test_ui_patterns.py` follows; `tools/control_shots.py` still shoots
   FACES.

## Task 4: faces per instance (spec F3, D4) — cuttable

Goal: instance *k* wears `faces.k`; one wire costs what it does today.

1. `Shape.INPUTS` gains `faces.2`–`faces.8` (`IMAGE`); the words tables
   (`WIRE_TAKES`, `_PICTURE_PORTS`, `WIRED_FROM_WORDS`) list them;
   the canvas folds them like the switch's eight (the wired ones plus
   one spare).
2. `FaceTarget` becomes a 2D array texture at 1024², one layer per wired
   input (the straight-wired pattern stays analytic as layer 0 and is
   not painted); `FACE_VS` passes `gl_InstanceID`'s layer (`k mod wired`
   over the wired inputs, in port order); `FACE_PX` samples the layer.
   An unwired `faces.k` is plain for that instance, never another
   input's picture.
3. Tests: two instances with two channels (a GL test reading back one
   pixel of each copy); one wire's frame signature and goldens unmoved;
   the loop check refuses `scene → shape.faces.3` as it does `faces`.
4. If D4 is "defer", skip this task and say so in the report.

## Task 5: docs

- This spec's "What changed in the build" (as plan 36's), the rulings
  with a register row each (the next free rows in `DECISION-REGISTER.md`,
  after whatever plan 37A took if it landed first).
- `DECISIONS.md`: the pattern by name, no fallback, the port's fit and
  mix, per-instance faces; `ARCHITECTURE.md`'s faces and patterns
  sections; `plans/README.md`'s entry; `SETUP.md` on `/8` and the
  migration tool.
- Hand checks: the spec's seven, written into `11-hand-checks.md` as the
  next group after the last one in the file.
- Test counts in the spec header.
