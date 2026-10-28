# Plan 41 — the PRESETS page, one tier

**Status: built (2026-10-28)** on `worktree-presets-one-tier`, one PR into
`main` for the owner to merge. Every decision below is the owner's, given
in the ask that opened the session ("unfuck the presets tab"); nothing
was deferred to a register row. The Drive library was changed the same
day (§4). **Both Macs on this build**: an older build still lists the
presets it shipped, and reads a `hidden.json` this one deletes.

## 1. The ask, in the owner's words

- The **Show** header and its options "are borderline useless and
  probably need to be consolidated or have a different more helpful view
  of what they are and why they exist."
- The **Starts On / Home** dropdown "is useless. I don't really care
  about that."
- The preset pill buttons, **F1 through F8 and then 9 through 24**: "that
  UI should disappear. This stuff is hard-coded. I want it completely
  deleted. I do not want there to be any visage of the hard-coded
  all-caps presets anywhere in the application." The presets themselves
  "don't necessarily have to be deleted."
- The preset **combo** with **Show Hidden**: "Any preset that is on the
  hidden list should be outright deleted immediately." "The menu itself
  should not exist. This preset page should just have a list of all of
  the presets that we have in a non-drop-down way so that we can just see
  them all."
- **Module presets**: "this particular UI for it needs to go away. The
  concept of module-level presets can stay for now" (they "probably need
  to be translated to be represented as patches" later).
- **Hidden / factory**: "there should be no concept of hiding a preset."
  "Something called factory presets … needs to go away."

## 2. What was decided

| # | Decision | Where |
|---|---|---|
| D1 | **One tier.** Nothing ships with the app. `Library` has one root; `is_factory`, `factory_names`, `hidden`, `hide`, `unhide`, `hidden.json`, the "save copy" label and user-shadows-factory are gone. Every preset is listed, loaded, renamed and trashed alike. | `library.py`, `ui_presets.py` |
| D2 | **The hidden presets are deleted.** The 21 shipped presets on the owner's hidden list left the app with the other four; the Drive library's `hidden.json` (and the home's stale copy) was deleted. | §4 |
| D3 | **The shipped presets become test data.** The 25 files, the 3 dream module presets and the `party` / `house` shows moved to `tests/corpus/` — the golden frames' subjects (`tools/golden_frames.py` `CORPUS_PRESETS`) and the test harness's seed (`conftest.seed`, `boot_home`). The app reads none of it. Their names (TUMBLE, BIG BLUE WAVE…) appear nowhere in the application. | `tests/corpus/`, `conftest.py` |
| D4 | **The generator and plan 13's migration are gone** from `preset.py`: `FACTORY_PRESETS`, every `party_*`/`hands_*`/`lfo_breathe_*`/`seq_demo_*` routes function, `knob_desk`, the `*_KNOBS`, `write_factory`, `factory_schema`, `migrate_home` and the schema-1 / routing-preset / echo migrations. Their old-schema sources stay under `tests/fixtures/factory-sources/` as the migration tests' inputs. | `preset.py`, `app.py` |
| D5 | **The band scenes are code data**, `hyperspace/scenes/band/*.json`, read by the scene combo without a library; a band preset in the library is the user's own and never stands in for a scene. | `control.py`, `library.scene_doc` |
| D6 | **The PRESETS page is the list.** Top to bottom: the preset strip (◀ name ● ▶ · new · save · as…; the name is a readout), every preset as a list filling the page (click loads; rename, ×), **trash (n) ▸** at its foot while the trash holds something, **patches ▸** folded, one **show** line, the library's notes. No pills, no starts-on, no drop-down, no module-preset fold, nothing dim. | `ui_presets.page` |
| D7 | **The show is one line** that says what it is — "show · the desk's pads, the session, the rig's wires" (hover: the long form) — then its name ●, **open ▾**, **save**, **as…**, **new**. A fresh library opens an unsaved `untitled` show with every pad empty; `new` makes the same. The pads are set on the desk only (hold a pad, SAVE + a pad). `startup` stays in the show file and Home still loads it; nothing on the panel sets it. | `ui_presets.show_line`, `Project` |
| D8 | **Module presets keep their strips on their own pages** (band, patterns…) with the popup list (× only), save, as… and reset; the PRESETS page shows none. The concept waits for the patches work. | `ui_presets.strip` |
| D9 | **The desk is untouched.** `apc40.py`, `midi.py`, the `preset.*` triggers (`load.k`, `save.k`, `select`, `save_new`, `save_into`, `next/prev`, `list.next/prev`, `home`) are as they were; only their tips were reworded (pads, not F-keys). | `params.py` |

## 3. What was built

- `hyperspace/library.py`: one root (`_roots` yields `home`, or nothing
  while a shared library is missing); `Project` without the `factory`
  flag (`mark()` is 13 fields, `MARK_LAYOUT = 9`, `MARK_RIG = 11`);
  `_open_default` opens `last_show`'s file or a blank `untitled` show;
  `Project.new` is the blank show; `list`, `_taken`, `delete`, `rename`,
  `restore_trash` without the hidden set; `RENAMABLE = (PRESETS,
  PATCHES)`; `scene_doc(path)`; `HOME_UNSET` reworded. `unshadow_default`,
  `legacy_slot`, the `presets.json` theme-bank import and every
  factory/hidden constant are gone.
- `hyperspace/preset.py`: ~1470 lines gone (D4). Kept: `Presets`,
  `desk_json`, `fresh_desk`, `device_knob`, `track_fader`.
  `NEW_SAID` says "default values".
- `hyperspace/control.py`: `SCENES_DIR`, `scene_doc()` from the scene file.
- `hyperspace/ui_presets.py`: rewritten (D6–D8); `ui.Panel._page_presets`
  calls `ui_presets.page`.
- `hyperspace/headless.py`: `resave` without the `factory` keyword.
- `hyperspace/scenes/band/` (from `hyperspace/library/band/`);
  `tests/corpus/{presets,dream,projects}/` (from `hyperspace/library/`).
- `tools/golden_frames.py`: `CORPUS`, `CORPUS_PRESETS`; `Rig` and
  `Loader` copy the corpus into the scratch library. The goldens'
  subjects, states and hashes are unchanged.
- `tests/conftest.py`: `CORPUS`, `seed(home, *groups, last_show="party")`,
  `boot_home(home, corpus=True)`.
- Tests of removed behaviour deleted (`test_party_show.py`,
  `test_plan12_presets.py`, `test_migration.py`, and the factory / hidden
  / generator / bank-pill cases inside other files); tests of kept
  behaviour seeded from the corpus; `test_ui_presets.py` rewritten for
  the new page. Tools that demonstrated removed features deleted, the
  rest pointed at the corpus.
- Docs: ENGINEERING §4, §6, §7, §8, §10, §16; ARCHITECTURE; DECISIONS;
  DECISION-REGISTER; SETUP; README; TESTING-GUIDE and
  `11-hand-checks.md` (a new check for the page; the superseded entries
  marked); CHECKPOINT.

## 4. The Drive library, 2026-10-28

Done in the session, on the owner's "deleted immediately":

- `My Drive/Hyperspace/hidden.json` deleted (it named 21 of the 25 shipped
  presets); `~/Hyperspace/hidden.json`, a stale copy from before plan 25,
  deleted; `projects/RENAMED.txt`, plan 14's one-off note, deleted.
- The four shipped presets the owner had **not** hidden were adopted into
  the library as his own, lower-cased, never over a file: `dial`, `trip`
  (was `party-trip` / TRIP), `plasma heart` (`plasma-heart.json`),
  `seq-demo`. The `mine` show's pads that name `TRIP` still load it (a
  name is found by its slug). Its pads naming TUMBLE, FACES and FIELD now
  name nothing on disk and say so when pressed.
- The three dream module presets (`default`, `tracer-only`, `wake`) were
  copied into `dream/` beside the owner's `loud`.
- The band scenes need no copy: they are code data (D5).

Dillon's Mac needs nothing but this build: its own `~/Hyperspace/hidden.json`,
if any, is read by nothing.

## 5. Hand checks

The new check at the end of Part 1 of `TESTING-GUIDE.md` (and its number
in `11-hand-checks.md`): the PRESETS page as D6–D7 describe it, over the
Drive library; the desk's pads still load and save (D9).
