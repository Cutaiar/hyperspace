# Plan 37B — the faces: a few good patterns, and the faces a target like any other

**Status: spec (2026-10-27), awaiting the owner's decisions D1–D5.** Build
plan [`37b-faces-build.md`](37b-faces-build.md). From item 8 of the
owner's notes after the 2026-10-25 install (register row 415, owner
2026-10-26: "face shaders consolidated and faces as a target like any
other"; his triage words: "consolidate to a few good ones;
faces-as-effect-target is stretch"). Plan 37 is two workstreams that do
not depend on each other: this one (37B) and nodes as pictures
([`37a-nodes-as-pictures.md`](37a-nodes-as-pictures.md)). Either may be
built, reviewed and merged first; "Independence" below lists what each
touches.

The owner judges visuals by eye (the parity bar), so this plan does not
decide which patterns are good: it puts the sheet in front of him (D1),
builds the consolidation he picks, and makes the faces' input as plain
as any other picture port, with no hidden fallback (plan 36's rule).

## What is there today (the map, `main` @ f2351a0)

File and line references drift; the names hold.

1. **Seventeen patterns, one shader.** `patterns.MODES` (patterns.py
   88–158): FLAT, RINGS, PLAID, MOIRE, BLOOM, CAUSTIC, HEX, SPIRAL,
   CELLS, PLASMA, WEAVE, EMBER, METER, PULSE, MARBLE, TRUCHET, KALEIDO.
   `shaders/patterns.glsl` (505 lines) is one `pattern(int mode, vec2
   uv, float fid)` whose `design()` is an if-chain (323–497; modes 12–16
   as functions, 179–303) over a shared `finish()` (156). The eight
   inputs `u_mod[8]` are `pattern.mod.0`–`.7` with one meaning each
   (SCALE, GLOW, WARP, SPEED, COLOUR, SHARP, HUE, SPREAD; plan 22). A
   mode is a **stored index**: `view.pattern` is an enum over
   `patterns.NAMES` (params.py 1339), and "modes are appended, never
   inserted" is held by a test (`test_patterns.py:294`).
2. **What the factory presets use.** All 25 are `/7` and every one wires
   `pattern → shape.faces`. Ten modes are in use: FLAT (seven presets
   with faces off), RINGS (dial, inverse-halo, party-acid), MOIRE
   (strobe-cage), CAUSTIC (big-blue-wave), HEX (hex-engine,
   party-faces), SPIRAL (spiral-silk), CELLS (party-tumble), PLASMA
   (party-mandala, party-trip, party-wake, plasma-heart, party-tracer),
   WEAVE (woven-lattice), EMBER (ember-orbit, party-field, party-noita).
   **Seven are used by none: PLAID, BLOOM, METER, PULSE, MARBLE, TRUCHET,
   KALEIDO.** None wires `pattern.media`. The Drive library (75 presets)
   has not been counted; T0 counts it.
3. **The pattern node and the faces' wire.** `graph.PatternNode` (3772):
   one input `media`, output a picture (`MAKES`, `PAINTS`); its
   `image()` makes a 1024² `FaceTarget` (`Renderer._pattern_picture`,
   render.py 2370). `graph.Shape` (3169) has `INPUTS = {"faces": IMAGE}`
   (3198). `Shape.faces()` (3208) walks through off effects and
   switches; **if it lands on a pattern node it returns None and the
   faces draw the pattern per fragment** (no picture pass, analytic,
   resolution-free); any other picture is painted at `FACE_PIC = 1024²`
   (`_face_picture`, render.py 2313) and mipmapped. Unwired:
   `r._face_plain` → `u_mode = 0`, no media: a flat fill.
4. **What can be wired into `shape.faces`.** Anything that makes a
   picture: a channel, an effect, a composite, a switch, a delay, a
   resize, an echo, the look-back, the dream. The scene is refused as a
   loop unless through a delay (`scene → delay → shape.faces`, plan 34).
   So "faces as an effect target" **already holds** since plan 33 (row
   342); what is missing is below.
5. **What `shape.faces` lacks against `composite.over` or
   `output.N.image`** (the gaps):
   - a **hidden fallback**: when the wired picture reads nothing this
     frame the faces fall back to the pattern (`Node.reads`, graph.py
     3135) — a default the canvas does not draw;
   - **one fit for all**: `fx.face_map` (per face / screen) is a global
     param that belongs to the shape only by convention (graphview 376);
     own-size pictures are cover-fitted only (`OWN_FIT`); no opacity, no
     blend, no `depth`;
   - a **fixed 1024² RGBA8 square** (`FaceTarget`, render.py 823–860),
     no choice of resolution;
   - the **pattern is special-cased** (the analytic bypass) and its
     media layer is a side channel of the pattern node
     (`pattern.media`, `_face_layer`) rather than a picture over the
     faces;
   - **one port for every instance**: `FACE_VS` (render.py 383–404)
     carries no instance id, so every copy of the shape wears the same
     faces (`view.instances`, plan 33's "next step", deferred three
     times: 33 §Not in this plan, 34, 35).
6. **The FACES page** (`ui_patterns.py`, 405 lines): faces / cut-through
   ticks and the mix, a chip per mode with a live 64² swatch
   (`Renderer.want_swatches`, one a frame round robin), the mode's line,
   eight named input rows with their drivers and "+ source" pushes.
7. **Dylan's side**: `apc40.py` puts `view.pattern` on device knob D4 and
   `view.pattern_mix` / `view.bmp_alpha` on two ccs; 17 presets carry a
   desk row for `view.pattern`, 25 for the mix and the alpha; ~19
   presets route `lane:i → pattern.mod.i` at the factory depth. None of
   these names a mode by index; an enum with fewer modes steps across
   fewer.

## What this plan does

### F1 — the patterns consolidated (D1)

- **T0 is a sheet, not code.** `tools/pattern_sheet.py` draws every mode
  at the neutral inputs and at three driven settings, one row per mode,
  into `assets/37b-patterns/sheet.png`, with the count of factory and
  Drive presets on each mode under its name. The owner marks keep /
  retire on it. **Decision D1** is that list; the recommendation is to
  keep the ten in use and retire the seven no preset uses.
- The retired modes' GLSL and `MODES` rows are deleted; the if-chain
  becomes **one function per kept mode** in a table, `finish()` shared,
  `pattern()`'s contract unchanged. `tools/check_glsl.py` compiles it.
  The depth-pass bound (`fa.max() · 2.8`, render.py 2869) is kept and
  asserted per mode.
- **A mode is stored by name, not index** (`view.pattern` saved as
  `"plasma"`): the "appended, never inserted" rule goes, and so does the
  test that holds it; a retired name in an old file maps by a table
  (`RETIRED = {"plaid": "moire", …}`, each pair the owner's or the
  nearest look) with a note on load. This is **schema `/8`**: a save
  writes `/8` only, `tools/migrate_library.py` rewrites a library once
  (the owner runs it on the Drive library as he did for `/7`; both Macs
  on this build). **Decision D2.**
- The FACES page's browser shows the kept modes; the swatch round robin
  shrinks with it. The eight inputs keep their meanings; the desk rows
  and the factory routes are untouched.

### F2 — the faces' input like any other (the WYSIWYG gaps)

- **No hidden fallback.** A wired picture that reads nothing this frame
  gives **plain faces** and the shape's `said` word ("faces: `acid.2`
  made nothing"), the same as unwired. The pattern is reached only by a
  cable.
- **The fit is the port's.** `fx.face_map` becomes `shape.faces_fit`
  (`per face` / `screen`, modulatable as today), a param of the shape,
  migrated by name in `/8`; it is drawn on the shape's node where the
  port is. `shape.faces_alpha` (0–1, default 1) lays the picture over
  the plain shade — today's `view.pattern_mix` renamed to where it
  belongs (the mix is of the faces' picture, whatever it is, not of the
  pattern): the desk row and the APC cc follow by the alias table
  (`params.py` aliases, as `view.bmp_alpha` does), so Dylan's files do
  not change. **Decision D3** is the rename.
- **The pattern is a picture.** The analytic bypass stays as an
  optimisation **only when the pattern is wired straight into
  `shape.faces`** (it is pixel-identical to today, so the goldens hold);
  through anything else it is the 1024² picture it already is. The media
  layer stays `pattern.media` (a drawn cable, so WYSIWYG already); the
  same look as a drawn `composite` is noted on the FACES page, not
  forced.
- **Resolution** stays `FACE_PIC` 1024² (the 1080p render cap makes more
  pointless); a note in the spec, no param.

### F3 — faces per instance (the stretch; D4)

- `shape.faces` becomes **`shape.faces` plus `shape.faces.2` …
  `shape.faces.8`**: up to eight picture inputs, instance *k* wearing
  input *k* and, past the last wired one, wrapping (instances 9–16 wear
  1–8 again). `FACE_VS` carries the instance index; the fragment shader
  samples one of up to eight pictures (a 2D array texture at 1024², one
  layer per wired input, the analytic pattern as layer 0 when it is
  wired straight). `faces_fit` and `faces_alpha` are shared by all.
- Unwired `faces.k` means **plain faces for that instance**, never "the
  same as faces.1" (no fallback). The canvas draws the eight ports
  grouped, folded to the wired ones plus one spare, as the switch node
  draws its eight.
- Cost: one array texture instead of one texture; a shape with one wire
  costs what it does today. SPREAD (input 7) keeps its per-face meaning.
- This is the owner's "stretch": T4 is last and can be cut from the PR
  without touching T1–T3.

### What this plan does not do

- No new pattern. "A few good ones" is a selection; if the owner wants
  one improved, it is a line on the sheet and a follow-up.
- No change to the FACES page's shape beyond the browser shrinking and
  the two renamed params; "FACES as a view of the graph" (plan 33's
  deferral) stays deferred.
- No change to the GRAPH canvas's drawing (plan 37A), the desk, the APC40
  or `bindings.default.json`.

## Decisions for the owner

| # | question | recommendation |
|---|---|---|
| D1 | Which patterns stay? (T0's sheet; the seven no preset uses are PLAID, BLOOM, METER, PULSE, MARBLE, TRUCHET, KALEIDO) | **Keep the ten in use, retire the seven.** Strike or add on the sheet; each retired one needs a "nearest kept" for the migration. |
| D2 | A mode stored by name with schema `/8` and a library migration, or keep the index and leave retired slots as holes? | **By name, `/8`.** Holes are a hidden rule; a name reads in the file and survives any later reorder. The Drive library migrates once, as `/7` did. |
| D3 | Rename `fx.face_map` → `shape.faces_fit` and `view.pattern_mix` → `shape.faces_alpha` (aliases keep the desk and APC working), or keep the names? | **Rename**, with aliases. The faces' fit and mix belong to the shape's port, and the GRAPH node should say so. |
| D4 | Build faces per instance (F3) now, as T4, or leave it deferred a fourth time? | **Build it as T4**, cuttable. It is the one thing "a target like any other" still cannot do, and the array texture is the whole cost. |
| D5 | The retired modes' GLSL: deleted, or kept in a `patterns-retired.glsl` nobody compiles? | **Deleted.** Git has it. |

## Order of work

| task | what | proves |
|---|---|---|
| T0 | the sheet: `tools/pattern_sheet.py` extended, `assets/37b-patterns/sheet.png`, the Drive count | the owner can answer D1 from one picture |
| T1 | F1: the kept modes as a table, retired ones deleted, mode by name, `/8`, `migrate_library` | every golden of a kept mode unmoved; a retired name migrates with a note |
| T2 | F2: no fallback, `faces_fit` / `faces_alpha` on the shape, the bypass only when straight | a wired picture that reads nothing draws plain faces and says so; goldens unmoved |
| T3 | the FACES page follows (browser, the two params' rows, the composite note) | the page lists only kept modes |
| T4 | F3: `faces.2`–`.8`, the array texture, the canvas's folded ports | two instances wearing two channels; one wire costs today's frame |
| T5 | docs: this spec's "as built", DECISIONS, register rows, hand checks | — |

T0 blocks T1 (the owner's D1). T2 does not need T1 and can be built first
if D1 is slow. T4 needs T2. T3 needs T1 and T2.

## Independence from plan 37A

| | 37B touches | 37A touches |
|---|---|---|
| `patterns.py`, `shaders/patterns.glsl`, `ui_patterns.py`, `tools/pattern_sheet.py` | all of it | nothing |
| `graph.py` | `Shape` (ports, params, `faces()`), `PatternNode`, `_PICTURE_PORTS`, the words tables | one `frame.made` call at the end of each picture node's pass |
| `render.py` | `FACE_VS`/`FACE_PX`, `_face_picture`, `_pattern_picture`, `FaceTarget`, the swatches | a new `Thumbs` class, `Frame.made`, `Preview` plumbing |
| `preset.py`, `graphmigrate.py`, `tools/migrate_library.py` | `/8` | nothing |
| `graphview.py` | the pattern node's words, the shape's folded ports | cable hues, node heights, the legend |
| `ui_graph.py` | nothing | nodes, cables, pins, hover, the head |

Shared seam: the face passes in `render.py`/`graph.py` — 37A adds one
line at their end, 37B rewrites them. Whoever merges second keeps the
line.

## Size

`patterns.glsl` loses ~200 lines and gains a table; `patterns.py` and
`ui_patterns.py` shrink; `graph.Shape` and the face shaders grow for F3;
`/8` is a small migration (one enum by name, two renames). Tests:
`test_patterns.py` (per-mode, parametrised: the mode list shrinks),
`test_ui_patterns.py`, `test_graph_faces.py`, `test_media_faces_aux.py`;
the faces goldens (`faces-media`, `media-chain-faces`, `switch-faces`,
`delay-faces`, `echo-faces`, `resize-faces`, `CLOUDED`) and every pattern
preset's goldens as the proof. About the size of plan 34.

## Hand checks (written into `11-hand-checks.md` by T5, numbered after the last group in the file when this lands)

1. **The sheet.** Open `assets/37b-patterns/sheet.png`: every mode at
   rest and driven; the counts under each.
2. **The kept patterns look as they did.** Load `party-trip` (PLASMA),
   `party-noita` (EMBER), `hex-engine` (HEX) on the rig: nothing moved.
3. **A retired one migrates.** A Drive preset on a retired mode (if any;
   else make one on `/7`) loads on its nearest kept with a note on the
   strip, saves as `/8`.
4. **No fallback.** Wire `media.a → shape.faces` with channel `a` empty:
   plain faces and the shape says so; drop a still in: the faces take it.
5. **The fit and the mix on the shape.** On GRAPH the shape shows
   `faces_fit` and `faces_alpha`; knob D4 still steps the pattern, the
   mix cc still mixes.
6. **Per instance (if T4).** `view.instances` 3, `media.a → faces`,
   `media.b → faces.2`, nothing on `faces.3`: the three copies wear a, b,
   plain.
7. **The desk.** With Dylan: the APC40 pattern knob, mix and alpha ccs
   on `party-faces` before and after.

## Follow-ups (not in this plan)

- `pattern.media` retired in favour of a drawn composite over the faces,
  once the FACES page can say so.
- FACES as a view of the graph (plan 33's deferral).
- A pattern improved on the owner's say, from the sheet.
