# Plan 31 × plan 32 merge: conflicts and silent clashes

**Resolved 2026-10-23** on `plan-31-32-integration` with the owner's D1–D3 as recommended below (register row 340); the TESTING-GUIDE renumbering is L145–L151, the combined check is 317 / L152.

What was merged: `origin/plan-31-integration` (PR #230, "ours") with `d580d06` (`plan-32-media`, PR #232, "theirs"). Their common base is `1a5cc2e`. The trial tree is `5f9565eb7cd901c57e1ebbb039f601e17facab69`. Line numbers below are in that conflicted tree.

The merge conflicts in 10 files (19 hunks). 25 files were touched by both sides; the other 15 merged cleanly. The merged `tests/golden/frames/frames.json` is valid JSON with 661 goldens.

**Counts: 18 superficial hunks, 1 conceptual hunk, 9 silent clashes.** Silent clashes S1–S6 need work. S7–S9 are checked and need no change.

## Conflict hunks

| # | file:line | kind | what each side did | resolution or decision |
|---|---|---|---|---|
| 1 | `hyperspace/preset.py:716` | superficial (the value depends on D1) | 31 passes `versions=VERSIONS`, which is `(2, 3)`. 32 passes an inline `(2, 4)`. | Keep `versions=VERSIONS` and set `VERSIONS = (2, 3, 4)` next to `SCHEMA_V3`. Optionally define `MEDIA_SCHEMA` as `f"{…}/4"` the way `SCHEMA_V3` is built. |
| 2 | `hyperspace/preset.py:789` (`load_doc`, step 1) | superficial | 31 parses each bank's membership before the values loop. Its first branch sends an id this registry lacks, when it belongs to a declared bank voice, to `later`. 32 adds `bmp_alpha = {}` and a first branch for `view.bmp_*`. | Union them in this order: 31's `members`/`bank_ids` block, then `bmp_alpha: dict = {}`, then the loop with `if p is None and _bank_prefix(pid) in bank_ids: later[pid] = v`, then `elif pid.startswith(BMP_PREFIX): …` (32's body), then the existing `elif pid.startswith(modifiers.PREFIX)`. The two tests are disjoint: `_bank_prefix("view.bmp_alpha")` and `_bank_prefix("media.a.slot")` both return `""`. |
| 3 | `hyperspace/preset.py:1055` (`document`, the end) | **conceptual** | 31 sets `doc["schema"] = schema_of(doc)` and, when that is /3, puts back every value through `self._values()`. 32 writes the `media` section, sets /4 when `uses_media(doc)`, and otherwise drops the section and the media-family values. Stacked in either order they break. If 31 runs second, its `_values()` puts the stripped media values back into a /3 file. If 32 runs second, it overwrites /3 with /4, or leaves /3 carrying media defaults. Neither side's rule says what a preset using both features is. | **D1.** The recommended code is in "Decisions" below: one `schema_of` that returns /4, /3 or /2; strip each family below the schema that introduced it; /4 keeps every value. |
| 4 | `hyperspace/params.py:117` `PERFORMANCE_GROUPS` | superficial | 31 adds `env`, `seq` after `lfo`. 32 adds `media`, `backdrop` after `fx`. | `("view", "rot", "camera", "pattern", "dream", "fx", "media", "backdrop", "lfo", "env", "seq", "macro", "mod")`. Keep 31's comment. `mod` stays last (`test_modifiers.py:183`). |
| 5 | `hyperspace/graphview.py:1247` (`key()`) | superficial | 31 appends `seq_key(reg)` and defines `seq_key`. 32 appends `channel_bins(reg)`. | `effect_switches(reg), seq_key(reg), channel_bins(reg))`, then keep 31's `def seq_key` (32's `channel_bins` is defined further down and is unaffected). |
| 6 | `hyperspace/graphview.py:1359` `NOUN_ORDER` | superficial | 31 adds `"env", SEQ` after `lfo`. 32 adds `"channel"` after `effect`, plus `ALWAYS_DRAWN`. | Keep 32's `ALWAYS_DRAWN = ("group:backdrop",)` with its comment. It is required: the auto-merged `is_idle` reads it at line 1425, and leaving it out is a NameError. Then `NOUN_ORDER = ("macro", "lfo", "env", SEQ, "effect", "channel", "group", "off", "lost")`. `IDLE_NOUNS` already merged with both sets of nouns. |
| 7 | `hyperspace/hotreload.py:57` `MODULES` | superficial | 31 adds `modbank`, `envelope`, `sequencer` after `tempo` and `ui_seq` before `ui`. 32 adds a new first line of `media.*`, `media.transport` and `media.channels` after `motion`, `media_tex`, `media.live…media.publish` and `ui_media`. | Take 32's lines and insert 31's names. Line 2 becomes `…"audio", "tempo", "modbank", "lfo", "envelope", "sequencer", "glsl"…`. The last line becomes `"ui_lfo", "ui_media", "ui_desk", "ui_pad", "hands.panel", "ui_graph", "ui_seq", "ui"`. Neither set imports the other: `envelope` imports only `modbank`, `ui_seq` imports `ui_lfo`, `envelope` and `sequencer`, and `media.*` imports only `motion` and itself. |
| 8 | `tests/test_golden_frames.py:115` | superficial | 31 has 24 factory presets and 7 with an effect on. 32 adds `+ 2*8 + 3*8` for its five media fixtures. | `24 * 2 * 9 + 7 * 2 + 1 + 24 * 5 + 2 + 2 * 2 + 8 + 3 * 8 + 2 * 8 + 2 * 8 + 3 * 8` = **661**. That matches the auto-merged `frames.json` (661 goldens, `sequencer_running == ["seq-demo"]`, all 11 fixtures). Merge both comments. |
| 9 | `tools/golden_frames.py:37` (module docstring) | superficial | Each side adds a paragraph. | Keep both: 31's RUNNING paragraph, then 32's MEDIA_FIXTURES paragraph. The rest of the rig (envelope and sequencer registration, `MediaState`, `media.poll`) merged cleanly at lines 326–416. |
| 10 | `docs/DECISION-REGISTER.md:12` (intro) | superficial | Each side wrote its own sentence about its rows. | Rewrite as one sentence: "Rows 311–320 (plan 31) and 321–339 (plan 32) were accepted as recommended by the owner on 2026-10-22, before their builds…". Drop 32's "on its own branch" wording. |
| 11 | `docs/DECISION-REGISTER.md:326` (summary table) | superficial | 31 adds rows 311–320. 32 adds rows 321–339. | Rows 311–320, then 321–339. The numbers don't collide. |
| 12 | `docs/DECISION-REGISTER.md:5978–6517` (row bodies) | superficial | 31 adds a "## The step sequencer (plan 31)" section. 32 adds a "## Plan 32 — media (rows 321–339)" section. | Both sections, 31's first. Then edit row 337 ("/4 after plan 31's /3": state D1's ladder) and row 338's rough edge (no renumbering happened). Optionally add a new row 340 for D1–D3. |
| 13 | `docs/TESTING-GUIDE.md:269` (summary table) | superficial, needs renumbering | **The ids collide.** 31 adds L139–L144, and A37–A46 elsewhere. 32 adds L139–L145. | Keep 31's L139–L144 and renumber 32's to **L145–L151** (L139→L145 … L145→L151). The hand-check numbers in the right-hand column stay as they are. |
| 14 | `docs/TESTING-GUIDE.md:3507–3763` (entry bodies) | superficial, needs renumbering | 31 adds "## The step sequencer (L139–L144; plan 31)". 32 adds "## Media (plan 32: L139–L145)". | Both sections, with 32's headings renumbered to L145–L151 and its section title changed to "L145–L151". No other doc cites 32's L-numbers (checked). Also add a plan-32 line to the guide's intro (around line 38) and its "order" list (around line 123), which only 31 edited. |
| 15 | `docs/plans/11-hand-checks.md:8` (intro) | superficial | Each side describes the numbering. | "They run 1–316; … group Z (277–295): 277–279 the instanced field, 280–295 plan 31's (286–295 on `plan-31-a1`); group AA (296–316) plan 32's." |
| 16 | `docs/plans/11-hand-checks.md:30` ("Before you start") | superficial | Each side adds a branch note. | Both sentences. 32's "needs `plan-32-media`" becomes the merged branch. |
| 17 | `docs/plans/11-hand-checks.md:3926–4383` (groups) | superficial | 31 adds its checks 280–295 (under group Z). 32 adds "## AA" with 296–316. | 31's block, then AA. In AA's intro, delete "296 follows a gap on this branch that closes when plan 31 lands". No check number is duplicated in the merged file (checked: 277–316 each appear once). |
| 18 | `docs/plans/11-hand-checks.md:4453` ("What no test covers") | superficial | Each side adds bullets. | Union both lists. 31's bullet line ends in ";", so fix the punctuation of the shared "Mesa" bullet. |
| 19 | `docs/plans/assets/24-party-fixes/desk-coverage.md:103` | superficial (a generated file) | 31 adds the seq-demo rows with the old "no bitmap file" wording. 32 rewords every K7 row to "no media channel". | Take 32's lines and insert 31's three `seq-demo` rows (D4, K4, K7 "faces off") between PLASMA HEART and SPIRAL SILK. Better: regenerate it with `tools/desk_coverage.py` on the merged tree. `test_desk_coverage.py` expects both 25 rows (31) and the K7 reason "no media channel" (32), and those are compatible. |

## Silent semantic clashes (in files that merged cleanly, or between rules)

**S1. Two schema rules, and only plan 31's is used everywhere.**
- `generated()` (the factory presets) and plan 31's tests call `schema_of(doc)`, which knows only /2 and /3. Only `document()` knows /4.
- Plan 31's rule counts any route, modifier or macro naming `env`/`seq` as /3 content (`_names_v3`). Plan 32's `uses_media` reads only the bins and the values. So a preset whose only media content is a route onto `media.a.rate`, `backdrop.alpha` or `view.media_alpha`, or a graph wire from a channel with an empty bin, saves as /2. A pre-32 build then drops that route or wire on re-save without a word. That is the loss plan 31's design exists to prevent.
- **Fix (part of D1):** a single `schema_of` that also uses an `_names_media` on `routes`, `modifiers`, `macros` and the graph section.

**S2. A build that reads /4 but not /3 loses data silently.**
- `plan-32-media` alone accepts `(2, 4)`. If the merged build writes a /4 file that also carries a pattern or envelopes, a Mac still on `plan-32-media` (for example the second Mac in the group AA hand checks) opens it. It drops `env.*`/`seq.*` as unknown ids and the `lfos`/`envs` keys, and writes back a /4 without them.
- The ladder only protects data if every build that accepts N also accepts every version below N.
- **Fix:** D2.

**S3. A test pins the old version list.**
- `tests/test_plan31_wiring.py:586` asserts `preset.VERSIONS == (2, 3)`.
- Change it to `(2, 3, 4)`. The test's simulated "older build" stays `(2,)`.

**S4. A test's expected /2 values don't know about media.**
- `tests/test_plan31_wiring.py:520` asserts `set(doc["values"]) == {k for k in every if not k.startswith(("env.", "seq.", "mod."))}`. Its `make_app` calls the merged `build_registry`, which now always creates the media params, and a /2 file now strips them. The test fails.
- Fix: add `or preset.is_media_id(k)`. Plan 32's `test_presets.py::test_a_preset_round_trips` is safe: that rig registers no envelopes.

**S5. The two plans disagree on what "at its default" means.**
- Plan 31 (`_uses_v3`) compares each value with `lib.defaults(group)`, the group's default module over the build values, which is exactly what a load fills in for a missing value. It uses float tolerance (`_same`).
- Plan 32 (`uses_media`) compares with the build defaults (`MEDIA_DEFAULTS`, from a fresh `ViewState`/`Channel`), exactly.
- `view.media*` sits in the `view` group, which can have a user default module. Suppose the default module sets `view.media_alpha` to 0.5 and a preset sets it to the build default. The preset is judged "not media", the value is stripped, and a reload lands 0.5: the look changed without a word.
- **Fix:** D3.

**S6. No check covers the combined case.**
- No test and no hand check covers a preset that uses both the sequencer and media. Plan 31's 285 / L144 is "/3 on an older build". Plan 32's 301 is "/4 on an older build".
- Add a test (pattern plus a bin → /4, carrying `env.*`/`seq.*`/`lfos`, refused by `versions=(2, 3)` and by `(2,)`) and hand check **317** / guide entry **L152**.
- `docs/DECISIONS.md` merged with two separate rows (line 238, the /4 rule; line 294, the /3 rule). Add one sentence on how they combine.

**S7. Golden frames: checked, consistent, but confirm by rendering.**
- Both sides only added hashes to `frames.json`; neither changed an existing one. The merged count is 661 and matches the formula, and the per-preset and per-fixture record fields agree. The merged rig registers both envelopes and media.
- Plan 31's seq-demo goldens were recorded without plan 32's renderer and `media.poll`. Plan 32's media goldens were recorded without the envelopes and sequencer being stepped. Each side's addition is idle in the other's frames, so no hash should move.
- **Confirm** with `tools/golden_frames.py --check` on the merged tree (it needs GL).

**S8. GRAPH areas and node kinds: checked, consistent.**
- The merged `AREAS` has six areas, with MEDIA between MODULATION and GEOMETRY (32). `env`, `seq`, `group:env` and `group:seq` map to MODULATION (31).
- seq-demo's cables (`env → view.bright / camera.zoom / fx.deconverge`) still run left to right, so `test_graph_areas`' no-back-wire check should hold. 32's `test_graphview.py:608` (MEDIA before GEOMETRY) and 31's `test_graph_seq.py:31` (`IDLE_KINDS`) are both satisfied.
- Device kinds (32: `ndi`, `syphon`, `camera`) and `BUILTIN_SCHEMES` (31: `env`, `seq`) are separate tables, and each test pins only its own.

**S9. Numbering, pages and the presets page: checked, fine.**
- Register rows 311–320 and 321–339 don't collide. Hand checks 280–295 and 296–316 don't collide. Only the TESTING-GUIDE L-ids collide (hunks 13–14).
- `ui.PAGES`: 32 replaces `bitmap` with `media` at the same index, 31 inserts `seq` after `lfo`; there is no test of the page count.
- The PRESETS page overview (`ui_presets.OVERVIEW_GROUPS`): 32 hides `media` and `backdrop`; 31's `env` and `seq` now show. Consistent with each design, and no test pins it.
- The undo/`Marks` additions (31's banks in undo, 32's bins in `Marks`) are separate. `signature()` merged with both parts.

## Decisions the owner must make

**D1. What schema a preset is when it uses both the sequencer and media (conflict 3, S1).**

Recommendation: one linear ladder, **/4 = /3 + media**.
- A save writes the highest schema it needs: /4 when the media rule is true; otherwise /3 when the plan 31 rule is true; otherwise /2.
- A load accepts `VERSIONS = (2, 3, 4)`.
- What each file carries:
  - /2 has no `env.*`/`seq.*` value and no media-family value or `media` key. It is byte for byte the file it always was.
  - /3 has every `env`/`seq` value and no media-family value or `media` key. A build with plan 31 but not plan 32 then loads it without "unknown id" notes.
  - /4 has every value and the `media` section. Both plans already say "the newest schema holds every value".
- Code at the end of `document()`:

```python
media = self.media
if media is not None:
    doc[MEDIA_KEY] = media.to_json()
doc["schema"] = schema_of(doc)        # /4 if uses_media(doc), elif the /3 rule, else /2
if doc["schema"] == MEDIA_SCHEMA:
    doc["values"] = self._values()    # everything, both families
else:
    doc.pop(MEDIA_KEY, None)
    vals = self._values() if doc["schema"] == SCHEMA_V3 else doc["values"]
    doc["values"] = {k: v for k, v in vals.items() if not is_media_id(k)}
```

- Move `uses_media` into `schema_of` (`if uses_media(doc): return MEDIA_SCHEMA`) so that `generated()` and the plan 31 tests share it.
- Also extend `uses_media` to routes, modifiers and macros naming `media.`/`backdrop.`/`view.media`, and to graph wires from a `MediaNode`, matching plan 31's precedent.
- Row 337 already says "/4 after plan 31's /3", so this is the intended reading. It needs writing down.
- The rejected alternative: one schema number per combination (/3 sequencer, /4 media, /5 both), or a list of required features. Either is more general but changes both PRs' formats for little gain while only two Macs read the library.

**D2. What happens to builds that accept /4 but not /3 (S2).**

Recommendation:
- Merge plan 31 first and plan 32 on top (or both together). Never run `plan-32-media` by itself against the shared library once the merged build has written a preset.
- Run the group AA hand checks (296–316) on the merged build, on both Macs.
- Update rows 337–338 and the AA intro to say so.
- The other option is to reject /4 in `plan-32-media` alone until the merge. That costs a commit on a branch about to be retired, so it isn't worth it.

**D3. Which "default" decides whether media is used (S5).**

Recommendation: use plan 31's test for the media family too. A value counts as untouched when it is within `_same` tolerance of `lib.defaults(group)`, which is what a load lands for a missing value. Keep "an id this build does not know counts as used".
- This means `uses_media` needs the library at save time. Only `Presets.document` calls it with a library to hand.
- A document-only `uses_media(doc)` for `generated()` can keep using the build defaults, because factory presets never set media values.
