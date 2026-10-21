# N8 — the palette as a colour compression transform; its strip's controls (plan 30)

You are the implementer of work package **N8**, from the owner's second look (2026-10-20).
Read first, in full: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your
rules; your first git commands: `git fetch origin plan-28-30-integration`, `git merge --ff-only
FETCH_HEAD` (or `git -C <worktree> merge --ff-only origin/plan-28-30-integration` if refused),
`git branch -m plan-30-n8-palette-compression`; one plain git command per shell call). Base
**980bdd9** (gates: 2387 passed, 2 skipped; ruff clean; 596 goldens match). **Exception to
common.md: the docs WPs are done, so you write your own docs (below).**

## The owner's words (2026-10-20)
> One of the mode controls is like a slider, but it's really a discrete picker, so that's not
> the right control type for that.
>
> The width control is like what angle around the HSV cylinder you are going to. The saturation
> and values seem to be bounds on how saturated or bright a given pixel can be. What we have is
> an angle, a radius, and a height. For the radius and the height, we have bounds, but for the
> angle, it's just a choice. What I would really like to be able to do is define a closed
> extruded slice on the HSV cylinder. I need a start angle and a stop angle, a start sat and a
> stop sat, and then a start value and a stop value. Every single pixel has to be compressed
> down into that resultant color space. What I want this to be is a color compression
> transform. It is definitionally mapping the space of the HSV cylinder onto a bounded subspace
> of that cylinder. If I want the entire image to all be shades of a particular red, I want to
> be able to do that. If I want the image to be particular shades of yellow and derivations on
> yellow for a given angular slice of the HSV cylinder, I need to be able to do that.

This is the owner's new direction for the palette; it supersedes plan 30 decision 2's "its fold
and gradient map are unchanged" (record that in DECISIONS.md and the register).

## Investigate first (write what you find in your report before you change anything)
- `hyperspace/shaders/fx/palette.glsl`: the header (`@param` lines, `@mix 0`, `@order 95`), the
  fold (hue by a triangle wave onto `centre ± width/2`), how sat and val are "rescaled into a
  chosen range" (a linear map or a clamp? — the owner wants a MAP: the whole input range lands
  inside the slice, nothing is cut off), the gradient-map mode (`mode` 0/1, `anchors`, `a1`–`a4`).
- `hyperspace/fx.py` `parse`/`declare`: what `@param` kinds exist (float ranges; is there a
  discrete/enum kind? how does `target` (frame/faces) or `face_map` get its picker?), the
  reserved names, how a renamed/added param lands in the registry, and what happens to a saved
  preset's value for a param that no longer exists (dropped with a note? kept?).
- `hyperspace/ui_fx.py` `strip_rows`, `HIDDEN_BY_MODE`, how a row is drawn (slider vs combo),
  `_lo`/`_hi` pairing (plan 24 row 139 packs `_lo`/`_hi` onto one row).
- `hyperspace/params.py` `Kind` (is there an enum/choice kind other effects or pages use?).
- Who uses `fx.palette.*` today: `grep -rn "palette" hyperspace/ tests/ tools/` — the two D1
  fixtures (`tests/fixtures/presets/palette-hands.json`, `palette-glass.json` with centre 200,
  width 60) and their 16 goldens; D2's `placed_chips`; any factory preset (`hyperspace/library/`
  — expected none, the palette being off everywhere); the docs (ENGINEERING §2, DECISIONS
  "Effects", rows 134–139, 30-shader-nodes.md, hand checks 220–231).
- The design doc's intent for the palette: `docs/plans/24-party-fixes.md` (C6) and
  `docs/plans/30-shader-nodes.md`.

## Build
**A. The transform.** The palette becomes a colour compression: the HSV cylinder mapped onto a
closed slice given by six params — `hue_from`, `hue_to` (degrees on the wheel, the slice running
from `from` to `to` the short way or the explicit way: decide, register; a slice may wrap through
0°/360°; `from == to` means one hue), `sat_from`, `sat_to`, `val_from`, `val_to` (0–1). Every
pixel's hue is mapped from the full wheel onto the arc (a continuous map with no seam: the
triangle fold today is one such map and may stay as the hue mapping — keep it if it reads as the
owner's "derivations of yellow for a given angular slice"; say why), its saturation from 0–1 onto
`[sat_from, sat_to]`, its value from 0–1 onto `[val_from, val_to]` — a MAP (linear or the
existing curve), not a clamp, so nothing is cut off and the output occupies exactly the slice.
`from > to` on sat or val is a legal inversion (dark becomes bright) unless you find a reason to
refuse it; decide and register. `mix` stays the wet/dry. The gradient-map mode stays as the
second mode (it is a different transform: brightness through anchor colours) unless you find the
owner's words make it redundant — do not remove it; say what you think.
**Compatibility:** `centre`/`width` go away as params. A saved preset carrying `fx.palette.centre`
/ `fx.palette.width` (any instance) is converted at load to `hue_from`/`hue_to` (= centre ∓
width/2, wrapped) — find how plan 26 converted `camera.pan`'s units (`preset.py`, the `units`
marker, rows 183–184) and do the same shape: convert on read, write the new keys, never lose a
look. The sat/val `_lo`/`_hi` params: rename to `_from`/`_to` only if the whole strip reads
better for it; if you keep `_lo`/`_hi`, say so. Defaults: the palette **off** and at `mix 0` as
today; the slice defaults to the full cylinder (0–360, 0–1, 0–1) so an on palette at mix 1 with
defaults is the identity — the picture unchanged (a test).
**B. The strip.** `mode` (and any other discrete param) drawn as a picker — a combo or chips —
not a slider; if `fx.parse` has no discrete kind, add one (`// @param mode choice 0 fold 1
gradient` or the like, registered as the header's new form, used by `palette.glsl`; `declare`
makes it a `Kind` the strip draws as a picker; other effect files unchanged). The hue slice drawn
as one row (`from` → `to` with a small wheel or a coloured bar between them if cheap, else two
sliders on one row like the `_lo`/`_hi` pairing), sat and val as one row each; the gradient
mode's rows hidden in fold mode as today (`HIDDEN_BY_MODE`). The strip's words say what the
owner said: "compress into: hue a → b · sat a → b · val a → b".
**C. Goldens.** The 556 base goldens do not move (no factory preset turns the palette on —
verify by grepping `hyperspace/library/` for `fx.palette`). The two D1 palette fixtures
(`palette-hands`, `palette-glass`) are converted to the new keys (they are fixtures, yours to
edit: write the equivalent slice — centre 200 width 60 → hue 170 → 230 — and keep their other
values); their 16 goldens are re-recorded ONLY if the pixels differ after the conversion (if
your hue mapping is the same fold, they should not move; if they move, the one reason is "N8:
the palette's slice parametrisation", named per frame in the PR body). `acid-scene` and the N4
fixtures do not use the palette.
**D. Tests** (`tests/test_palette.py`, new): the identity at defaults; a red slice (hue 350 → 10,
sat 0.6 → 1, val 0.3 → 1) gives only reds (every output pixel's hue within the arc, sat and val
within the ranges — on a synthetic rainbow input through the real shader headless as
`test_fx.py` does); a yellow slice; a wrapping arc; an inverted val range; the conversion of a
preset carrying `centre`/`width`; the `mode` picker drawn as a picker; the strip's rows; the
fixtures load with no note after conversion. `tests/test_fx.py` and `tests/test_graph_placement.py`
stay green (name any assertion you must change, with its reason).

## Docs (yours, in the same PR)
- `docs/DECISIONS.md` "Effects and the look-back": the palette-fold row rewritten as the owner
  says it (a colour compression onto a closed HSV slice; Who `owner (2026-10-20)`); plan 30's
  decision-2 row amended ("the fold was reparametrised as a slice on 2026-10-20").
- `docs/DECISION-REGISTER.md`: a `## The palette as compression (plan 30, N8)` section, rows
  from **291** (the slice's param names and wrap rule; the hue mapping kept or changed; map vs
  clamp; inversion; the conversion of `centre`/`width`; the discrete `@param` form; the strip's
  rows), on the answer sheet; rows 134, 136–139 amended/superseded where they describe
  `centre`/`width` or the sliders, the way plan 25 marked 78/108.
- `docs/plans/11-hand-checks.md` group **X** (plan 30) from **267**: the whole picture as shades
  of one red on the projector; a yellow slice with derivations; a wrapping arc; the mode picker;
  an old preset with centre/width loading as the same look. `docs/TESTING-GUIDE.md` the same in
  plain words with the numbers. `docs/plans/30-shader-nodes.md`: an N8 section; the intro's
  ranges. `docs/ENGINEERING.md` §2's palette paragraph. `docs/plans/README.md` and
  `docs/CHECKPOINT.md` ranges (rows 214–N, checks 220–M). Hand checks 220–231 that name
  `centre`/`width` (e.g. "centre 200, width 60") rewritten to the slice.
- `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N8.md` and
  `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/N8-report.md` (what you found, what you
  built, every golden re-recorded with its reason, every changed assertion, your final N and M).

Another WP (N9, the GRAPH page's layout by concern) runs in parallel and touches `graphview.py`
/ `ui_graph.py` and the register from the same next row; you touch `palette.glsl`, `fx.py`,
`ui_fx.py`, `preset.py` (the conversion), the fixtures, the docs. If N9 lands first, the
orchestrator will tell you to renumber your rows/checks after its last ones. Hard limits:
`apc40.py`, `midi.py`, `hyperspace/library/` untouched; the 556 base goldens unmoved; scratch
`HYPERSPACE_HOME` with the APC40 disabled for any windowed run.

PR: `gh pr create --base plan-28-30-integration` titled `Plan 30 N8: the palette as a colour
compression onto an HSV slice; a picker for mode`. Reply with the short contract, its first line
your final N and M.
