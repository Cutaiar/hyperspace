# Plan 19 — Presets and the desk layout

**Written 2026-10-04 against `plan-18-integration` at d594935** (`finish-line`
— plans 15 and 16 — plus One Unbind, Learn desk / Learn hand, the ROUTING
filter, the interaction box, knob smoothing and `hands-orbit`). Scope:
roadmap §4 "Plan 19" ([`15-21-roadmap.md`](15-21-roadmap.md)). Two packages
are still being built and land before this plan is: plan 17 WP4 (the
on-screen desk grows and labels every lit control;
[`17-learn-and-the-desk.md`](17-learn-and-the-desk.md) §2 "WP4") and plan 18
WP3 (a hand Learn's default). Plan 20 is built beside this plan; §2 says
where the two meet.

The owner, 2026-10-04: "more than eight on the desk; clean out the unwanted
ones; no always-ask on save". This plan grows the bank to twenty-four
slots, gives the dark device knobs something to do, and lets the owner
cull, rename and recover presets from the list, with the home folder in
git for those who ask.

No code was changed. Every claim about existing code was read in the file
named. Numbers marked *measured* come from headless probes on this branch
with `HYPERSPACE_HOME` on a temp folder (the scripts are not kept).
**Nothing here read, listed or wrote `~/Hyperspace`**, and nothing a build
agent does may: this is the plan that renames, hides and trashes files in
that folder and can put it in git, and the presets saved on the night may
have no backup. Nobody was available to answer questions, so every fork is
in §6 with the option taken.

**The rule for the owner's files, in every package.** A package that
changes a file's format, or moves, renames or deletes a file in the home,
says in its section what is copied first and where (`routing.backup`
beside the file, or `library.to_trash` into `<home>/trash/`), does nothing
when that copy cannot be made, and has a named test that runs it on a
**copy** of a home shaped like the owner's (the `owner_home` fixture,
WP1). The whole list is in §2 "The owner's files".

## 1. What the owner hit, and what it is

| # | The owner hit, or the roadmap says | What the code does | So |
|---|---|---|---|
| 1 | "More than eight on the desk." The bank grows from 8 to 24 | The bank is `Project.bank`, a list of `library.SLOTS` (8) names (`Project.__init__`). A show file's `bank` is cut to `SLOTS` and padded on load (`Project._take`). | WP1. |
| 2 | "`SLOTS = 8` is wired into the keys, the clip row, the PRESETS page and the params loop" | Partly. **The params loop already reads the list**: `for k in range(len(bank.bank))` (`build_registry`, "the preset bank"). **The PRESETS page loops over `pr.bank`** (`ui_presets.preset_bank`) but labels every slot `F{k+1}` and lays them two a row (`BANK_COLS`). **The clip row is a literal** `range(8)` in `apc40.DEFAULT_MAP`. **The keys read a second constant**, `routing.BANK_SLOTS = 8` (`LOOP_KEY_ROWS`, `THEME_TO_PRESET`), which a test pins equal to `SLOTS` because `routing` may not import `library` (`test_routing.py`, the F-key test). `SLOTS` itself is read in `Project.__init__`, `_take`, `load_slot`, `save_slot`, `library.migrate`, and `preset.migrate_project` / `_into_default`. | Setting `SLOTS = 24` alone would add 32 params (`preset.load.8…23`, `preset.save.8…23`), label pads "F9"–"F24", leave `BANK_SLOTS` failing its test, and make the page twelve rows. WP1 separates "the bank's size" from "the F-keys". |
| 3 | "Next empty slot reads the bank's size from one place, so plan 19 needs no change to it" (roadmap §5) | True of `next_empty`, `save_new`, `put_slot`, `clear_slot` (`test_library.py::test_next_empty_reads_the_banks_own_length` runs them on a bank of 24). But their messages say `F{k + 1}` ("saved TRIP 2 → F18"), and `load_slot` / `save_slot` refuse `k ≥ SLOTS`. Plan 15 §8 also left "the active slot follows the loaded preset" spelled in four places (`Project._set_slot`, `Project._apply`, `Marks.put`, `Presets._landed`). | WP1: one name for a slot (`slot_key`), one `Project.follow`. |
| 4 | "Clip rows 4–5 become slots 9–24 … Shape selection leaves those two rows for the cue knob, which already has it" | True: `_cc("view.shape", CC_CUE, 0, op="rel", ring=0, layer=P)`. Rows 4–5 carry `view.shape` `set 0…15` on the **preset** layer and nothing on the global layer (dark under SHIFT). The pads reach 16 of the 25 shapes (`geometry.SHAPES`, *measured*); the cue knob reaches all 25. Nothing else is on those rows. | Nothing has to move. What is lost: a lit green pad showed which of the 16 shapes was up; the cue knob has no light. The VIEW page's shape combo and plan 17's desk label ("Shape") are what show it. |
| 5 | "A preset whose desk layer maps rows 4–5 has those rows dropped at load with a note, as any row on an invariant control is today" | The shape pads are preset-layer rows, so they are **in the presets**: `fresh_desk()` (`preset.py`) is the factory map's preset layer, 42 rows, 16 of them the shape pads; 18 of the 23 factory files carry a `desk` with those 16 (*measured*), and **every preset saved from the app does** (`Presets.document` writes `desk_json(table.desk())`). `Bindings.set_desk` notes each dropped row, and `Presets._warn` puts the first on the warning line with "(+15 more)". | As written, every preset the owner saved would warn on every load, all night. WP2: a row that is exactly one of the sixteen old factory rows goes quietly; a row the owner put on those pads is dropped with the note (fork 4). Every factory file is regenerated. |
| 6 | The clip row's lights | `routing.led_lit`: a `set` row on an enum is lit when the enum's value is the row's. So the loaded slot is green and **every other pad is dark, filled or empty** (`_note("preset.select", N_CLIP[0], k, op="set", value=k, on=GREEN)`). | With 24 pads, 23 dark ones say nothing about where the presets are. WP2: a filled slot shows amber (fork 5). |
| 7 | "The device knobs, dark on most presets today" | *Measured* (§2 WP3's table): D1–D8 are dark on 16 of 23 factory presets; `lfo-breathe` has one (D1 Breathe); six have eight (WAKE, TRIP, ACID, MANDALA, NOITA, TRACER). K1–K8 are the same eight on all 23. The factory map's preset layer has no device-knob row and a test says so (`test_desk.py::test_the_default_map_is_sorted_as_plan_13_says`); `knob_desk` appends eight rows to `fresh_desk()`. | WP3 puts a block on the fresh preset layer and makes `knob_desk` replace it rather than add to it (no control mapped twice). |
| 8 | "A × on any preset in the list: a user preset goes to the trash" | Already so. `ui_presets._list_popup` draws × on user presets only; it calls `Library.delete`, which copies the file to the trash first and refuses when it cannot (plan 15). A factory preset has no ×. | WP4 adds what is missing: × on a factory preset hides it. |
| 9 | "Rename a preset (the file, and every bank slot that points at it)" | A slot is a name in a **show file** (`Project.bank`, `startup`); a home has several shows (`mine`, a copy of `party`, …) and only one is open. A preset is found by the name inside its file, else by its file's stem (`Library.path_of`), and the two differ for factory presets (`party-trip.json` is "TRIP"). Nothing renames. | WP4: every `hyperspace.project/2` show in the home is repointed, each copied to the trash first. |
| 10 | "Undo.push is called by … 19's hide, rename and trash" (roadmap §5) | Undo cannot put a file back: a restore "writes no file" (decision 26), and `Undo._swap` skips a step with nothing to put back. A push before a rename would make either an empty step or, when the renamed preset is loaded, a step that puts the **old name** back as "loaded" with no file under it. | No `undo.push` in WP4. Each action has its own net (§2 WP4). |
| 11 | "The trash: a view of it, restore, empty" | `to_trash` writes `<home>/trash/<folder>/<stem>.<YYYYMMDD-HHMMSS>[-n].json`, the folder being the file's own (`presets`, `fx`, `band`…); `trash` is no group and `Library._scan` never reaches it (it globs `*.json` one level under the home, and the trash's files are two levels down). Nothing lists, restores or empties it. | WP4. |
| 12 | "'save' on yours, 'save copy' on a factory one" | The behaviour exists: `Library.overwrite` → `save_as(group, cur)` writes a user file that shadows the factory one of the same name; only the hover says so. *Measured* at the control size: the strip's left part (◀ name ● ▶) is 205 px, "save · as… · reset" 163 px, "save copy · as… · reset" 196 px, the page 392 px: the longer label does not fit a strip. On the preset strip `reset` does nothing: `Library.reset` on a document kind returns `None` unless a preset happens to be called "default". | WP5: the preset strip loses `reset` and gains the label; module strips keep "save". |
| 13 | "A dirty dot that reads at arm's length" | The dot is the glyph "●" in `ui.RED` at the 16 px type (`ui_presets.strip`, `ui_routing._preset_line`; about 7 px of ink in a 13 × 16 cell, *measured*), and a 7 px disc on the rail (`Panel._rail`, radius 3.5). | WP5: a 12 px disc, and the save chip itself lit. |
| 14 | "The home in git … opt-in from config" | `config.py` imports `library`; `library` may import only `params` and `undo` (ARCHITECTURE §1). `Library._scan` and `Library.groups` skip folders whose name starts with a dot, so a `.git` in the home is neither watched nor a group. *Measured* on a temp home with 30 presets: `git add -A` + `commit` takes about 50 ms; a locked index fails in 24 ms with exit 128; `git rev-parse --show-toplevel` tells a home that is its own repository from one inside another. | WP6: a leaf module the app wires in; the library calls a hook. |
| 15 | `Bindings.load` and a backup that fails | `backup(path, t.read_at)` then `t.write()`, whatever `backup` returned (`routing.py`). `preset.migrate_home` checks the return and does not write; this older branch does not. | WP2's remap is the next thing through that branch: it is made "no backup, no rewrite". |
| 16 | The roadmap: "6 WPs, S–M, one L"; hand checks | Groups exist through L (checks to 63); plans 17 and 18 take M and N. | Seven packages: the L item cut in two, and docs. Group **O**, checks O1–O10 (§8). |

## 2. Work packages

Merge order onto `plan-19-integration`: **WP1, WP2, WP3, WP5, WP4, WP6,
WP7.** WP1–WP3 stack (WP2 and WP3 both regenerate every factory preset
file). WP5 touches one function WP4 does not and is built beside WP2; WP4
starts once WP1 is merged (both edit `library.py`) and is built beside WP2
and WP3. WP6 starts once WP4 is merged. One PR and one merge commit each
(decision 30), each with a demo in the PR body.

| WP | What | Size | Needs |
|---|---|---|---|
| 1 | **A bank of twenty-four** (the library, the params, the page) | M | — |
| 2 | **Rows 4–5 are the bank** (the desk, its lights, old files) | M–L | WP1 |
| 3 | **The factory preset layer re-cut** | S–M | WP2 |
| 5 | **The dirty dot and the save label** | S | WP1 |
| 4 | **Hide, rename and the trash** | M | WP1 |
| 6 | **The home in git** | S–M | WP4 |
| 7 | **Docs and hand checks** | S | last |

**Shared files, and who edits what.** A package may edit only its lines.

| File | WP1 | WP2 | WP3 | WP5 | WP4 | WP6 |
|---|---|---|---|---|---|---|
| `library.py` | `SLOTS`, `F_KEYS`, `slot_key`, `bank_doc`, `Project.__init__` / `_take` / `to_doc` / `write` / `load_slot` / `save_slot` / `follow`, the four "active follows" sites, `migrate` | — | — | — | `Library.list(hidden=)`, `hide`, `unhide`, `hidden`, `rename`, `trash`, `restore_trash`, `empty_trash`, `HIDDEN` | `Library.committer`, `_commit`, its calls; the notes drained in `poll` |
| `preset.py` | `migrate_project`, `_into_default` (`bank_doc`); `Presets._landed` (`follow`) | no code (the quiet drop is the table's); the files regenerated | `knob_desk`, the `*_KNOBS` tuples, `FACTORY_PRESETS`' `desk=`; the files regenerated | — | — | — |
| `routing.py` | `BANK_SLOTS` → `F_KEYS` (the same 8) | `APC_REMAP`, `APC_NEW_ROWS`, `APC_REMAP_PLAN`, `RETIRED_DESK_ROWS`, `Bindings.set_desk`, `Bindings.load` (no backup, no rewrite), `led_level` | — | — | — | — |
| `apc40.py` | — | the clip rows in `DEFAULT_MAP`, `BANK_PADS`, `filled_of`, the docstring | the preset layer's device knobs in `DEFAULT_MAP` | — | — | — |
| `bindings.default.json` | — | regenerated (`python -m hyperspace.routing`) | — | — | — | — |
| `library/presets/*.json`, `library/projects/*.hyp.json` | `party.hyp.json` (slot 9) | every preset regenerated (`python -m hyperspace.preset`) | regenerated again | — | — | — |
| `params.py` | the bank block of `build_registry`: the loop's bound, `preset.select`'s tip and `has=`; `Registry.enum(has=)`, `Param.has` | — | — | — | — | — |
| `midi.py` | — | `feedback`'s LED branch | — | — | — | — |
| `ui_presets.py` | `preset_bank`, `BANK_COLS`, the docstring | — | — | `strip` (the dot, the label, no `reset` on a kind), `save_label` | `_list_popup`, `_trash_popup`, the dangling slot's ink in `preset_bank` | — |
| `ui_desk.py` | — | `_led` (amber), `text` (an empty slot) | — | — | — | — |
| `ui.py`, `ui_routing.py` | — | — | — | `ui.dirty_dot`; the rail's dot; `ui_routing._preset_line` | — | the SYSTEM page's line |
| `config.py` | — | — | — | — | — | `DEFAULTS["library"]`, the docstring |
| `app.py`, `hotreload.py`, new `homegit.py` | — | — | — | — | — | all of `homegit.py`; the wiring in `app.main`; `"homegit"` in `MODULES` |
| `tests/conftest.py` | the `owner_home` fixture | — | — | — | — | — |

No code package edits `ARCHITECTURE.md`, `ENGINEERING.md`, `DECISIONS.md`,
`DECISION-REGISTER.md`, `plans/README.md`, `CHECKPOINT.md`,
`11-hand-checks.md` or this file. Each PR body carries its "as built"
paragraph; WP7 folds them in.

**No package touches** `undo.py`, `learn.py`, `hands/`, `render.py`,
`fx.py`, `lookback.py`, `ui_fx.py`, `ui_lookback.py`, the shaders,
`view.py`, `control.py`. No boundary test moves: `library` still imports
only `params` and `undo`; `routing` still does not import `library`;
`homegit` imports nothing from the package (a new boundary test says so).

### Where plan 19 meets plan 20

Plan 20 owns `fx.py`, `ui_fx.py`, `render.py`, `lookback.py`,
`ui_lookback.py`, the shaders, `view.inst_layout` and a per-effect
`fx.<name>.target`. The two meet in four places, each settled once:

| Where | Plan 19 | Plan 20 | The rule |
|---|---|---|---|
| `library/presets/*.json` (generated) | WP2 and WP3 regenerate all 23 | regenerates if a factory preset is to carry a face target or an instance layout | **Never merged by hand.** Whoever merges second runs `uv run python -m hyperspace.preset` on the merged code and commits the output; `test_presets.py::test_write_factory_regenerates_every_factory_file` and `::test_every_factory_presets_desk_is_the_generators` arbitrate. |
| `preset.py` | `knob_desk`, the `*_KNOBS` tuples, the `desk=` of entries in `FACTORY_PRESETS` | the `*_values()` functions, if it sets a new param | Different lines of the same entries. 19 does not edit a `*_values` or `*_routes` function; 20 does not edit a `desk=` or a `*_KNOBS` tuple. |
| `params.py` | the bank block only | the view block (`view.inst_layout`); the effects' params come through `fx.declare` | Different blocks of `build_registry`. |
| `apc40.py` | clip rows 1, 4 and 5; the preset layer's device knobs | a pad or knob for a new param, if it wants one | 20 takes a control this plan leaves dark **on the preset layer** — clip row 2 (eight pads) and clip row 3 pads 1–4 are free there after this plan — and adds its row after WP3 is merged. It does not take a device knob: WP3's table is the whole of D1–D8. |
| The document tables | WP7 | its own docs package | Both are last in their plan; the second to merge rebases onto the first. No code package of either plan edits them. |

### The owner's files

Every file in the home this plan can rewrite, move or delete, and its net.
"Proved" names the test that runs it on a copy.

| File | What happens, and when | Copied first | Proved |
|---|---|---|---|
| `projects/<show>.hyp.json` | **Not rewritten by loading it.** An eight-name bank is padded in memory. Rewritten only by what rewrites it today (a bank change, "starts on", save). The first write that puts a name in slots 9–24 makes the file's `bank` longer than eight | `routing.backup(path, "2-bank8")` → `<file>.bak-v2-bank8`, once; no backup, no write (the slot is put back, as `_set_slot` does today) | `test_library.py::test_an_eight_slot_show_loads_and_is_not_rewritten`, `::test_the_first_write_past_slot_eight_keeps_the_eight_slot_file` |
| `projects/<show>.hyp.json`, every show | A rename repoints its `bank` and `startup` | `to_trash` → `trash/projects/<show>.hyp.<stamp>.json`; a show whose copy fails is left as it is, and said | `test_library.py::test_rename_updates_every_show_and_keeps_each_old_file` |
| `bindings.json` | Once: sixteen invariant rows added where rows 4–5 are free; in a file from before plan 13's migration the sixteen old shape rows swapped | `routing.backup(path, read_at)` → `bindings.json.bak-v3` (the existing call); **no backup, no rewrite** from this plan on | `test_routing.py::test_an_older_file_gets_the_bank_pads_with_a_backup`, `::test_a_remap_whose_backup_fails_writes_nothing` |
| `presets/<name>.json` (yours) | **Never rewritten by a load.** The sixteen old pads are dropped in memory; the file keeps them until you save it, and that save copies the old file to the trash (plan 15's rule, unchanged) | `to_trash` (existing) | `test_presets.py::test_an_old_preset_loads_without_its_shape_pads_and_its_file_is_untouched` |
| the same | × : copied to the trash, then removed (existing). Rename: the new file is written first, then the old one is copied to the trash and removed | `to_trash`; a copy that fails refuses the delete and undoes the rename | `test_library.py::test_a_rename_that_cannot_keep_the_old_file_changes_nothing` |
| `trash/**` | Restore moves a file back out (never over a file). **Empty deletes for good**: the one place in the app that keeps no copy | nothing: this is the end of the line, asked twice | `test_library.py::test_restore_never_overwrites`, `::test_empty_trash_removes_only_the_trash` |
| `hidden.json` (new) | Rewritten by × on a factory preset and by "unhide" | nothing: it holds only what two clicks rebuild; one that will not parse is kept by `routing.backup(path, "0")` (`hidden.json.bak-v0`) before the first rewrite | `test_library.py::test_an_unreadable_hidden_list_is_kept_before_it_is_replaced` |
| `.git/`, `.gitignore` (new, opt-in) | Created at the first save with `[library] git = true`; never when a `.gitignore` is already there (kept), never when the home is inside another repository | — | `test_homegit.py` |
| factory files (the repo's, not the owner's) | regenerated | git | — |

Of everything above, a launch of the new build with the config as it is
does one thing to the owner's files: `bindings.json` is rewritten, once,
backed up first. (`last_show` and `windows.json` are written as today.)

---

### WP1 — A bank of twenty-four

**What.** The bank is twenty-four slots; the first eight are the F-keys'.
The show file grows only when a far slot is used. The PRESETS page shows
all twenty-four without scrolling.

**Owns.** Its lines in the table; `tests/test_library.py`,
`test_presets.py`, `test_ui_presets.py`, `test_routing.py` (the one
assertion), `test_party_show.py`, `test_migration.py`, `conftest.py`.
**Must not touch** `apc40.py`, `midi.py`, `ui_desk.py` (WP2).

#### Constants and names

```python
# library.py
SLOTS = 24        # the bank: F1–F8, then the desk's clip rows 4 and 5
F_KEYS = 8        # the slots a function key reaches; a show file's bank is never shorter

def slot_key(k: int) -> str:
    """What a slot is called in a message and on the page: "F3" for the
    first F_KEYS, "slot 12" after."""

def bank_doc(bank: list[str | None]) -> list[str | None]:
    """A bank as a show file holds it: trailing empty slots left off, never
    shorter than F_KEYS."""
```

*As built:* `F_KEYS = 8` is declared once, in `params.py` (which needs
it for the trigger loop and may not import `library`); `library.F_KEYS`
and `routing.F_KEYS` are that name imported, and the test pins all
three (§7 WP1).

`routing.BANK_SLOTS` is renamed `routing.F_KEYS` and stays 8: it has only
ever counted the F-key rows (`LOOP_KEY_ROWS`, `THEME_TO_PRESET`). The test
that pinned it to `SLOTS` pins `routing.F_KEYS == library.F_KEYS`. The
desk's count is `len(apc40.BANK_PADS)` (WP2), pinned to `SLOTS` by a test.
So the bank's size is one constant, `library.SLOTS`; the two modules that
may not import `library` each hold a list whose length a test ties to it.

#### The show file

- **Load** (`Project._take`): `bank` is cut to `SLOTS` and padded with
  `None` to `SLOTS`, as today with the new number. `_saved` is the padded
  list, so a show with eight names is clean and **nothing is written**.
- **Write** (`Project.to_doc`): `bank=bank_doc(self.bank)`. A show that
  uses only slots 1–8 is written with eight entries, byte for byte the
  shape it has today.
- **The first write that makes the file's bank longer than eight**
  (`Project.write`): when the file on disk parses, holds a `bank` of at
  most `F_KEYS` entries and the document about to be written holds more,
  `routing.backup(self.path, "2-bank8")` runs first. If it returns `None`
  the write raises `LibraryError`; `_set_slot` and `save_new` already put
  the slot back and say why. One backup per file: the next write finds a
  long bank on disk.
- **Schema**: stays `hyperspace.project/2` (fork 2). An older build reads a
  long bank by cutting it to eight (`_take`'s `[:SLOTS]`), shows slots 1–8
  correctly, and **drops slots 9–24 from the file the next time it writes
  that show** (a bank change, "starts on", save). The presets' files are
  untouched and stay in the list. Going back to an older build therefore
  costs the far slots' pointers at most; `.bak-v2-bank8` is the file from
  before any far slot existed.
- `preset.migrate_project`, `preset._into_default` and `library.migrate`
  write their banks through `bank_doc` (they build `SLOTS`-long lists
  today and would start writing twenty-four entries). *As built:* they
  read a schema-1 or `presets.json` bank as the F-keys' eight
  (`[:F_KEYS]`), so the migration writes into a show exactly what it
  wrote before this plan (§7 WP1).

#### The bank's calls

- `load_slot(k)` / `save_slot(k)`: `0 <= k < len(self.bank)`; every
  message uses `slot_key(k)`. An empty slot says "F3: an empty slot — ⇧F3
  saves the live state into it" for the first eight (today's words) and
  "slot 12: an empty slot" after.
- `save_new`: unchanged but for `slot_key` ("saved TRIP 2 → slot 9").
- `Project.follow(self) -> None`: `active` follows the loaded preset —
  kept where it is when that slot still names it, else the first slot that
  names it, else −1; −1 when nothing is loaded. The four sites call it
  (`_set_slot`, `_apply`, `Marks.put`, `Presets._landed`). `load_slot`
  still sets `active = k` after the load, so a preset that sits on two
  slots lights the pad that was pressed.

#### Factory shows

`party.hyp.json` gains one name: slot 9, **TRACER** (fork 3). `house` is
unchanged. So a fresh home's party show has fifteen empty slots for
save-as to land in, the first being slot 10. A show file the owner already
has (`mine`, a copy of `party`) is never changed by this: its slots 9–24
are empty until the owner fills them.

#### Params: none added

| Param | Today | After |
|---|---|---|
| `preset.select` | enum over 8 names | enum over 24 (the list's own length); gains `has=lambda k: bank.bank[k] is not None` (below) |
| `preset.load.0…7`, `preset.save.0…7` | 16 triggers, the loop over `len(bank.bank)` | the same 16: the loop is over `min(len(bank.bank), F_KEYS)` |
| `preset.save_new`, `next`, `prev`, `home` | 4 | 4 |

Slots 9–24 need no trigger of their own (fork 1). A pad loads through
`preset.select` `set k`, as clip row 1 does. The page's button calls
`pr.load_slot(k)` and, with ⇧, `pr.save_slot(k)`. `preset.next` / `prev`
(QUANT, the pad's B) already walk every filled slot (`Project.cycle`).
What is given up: a performer or a learned button cannot fire "load slot
17" by its own id; `preset.select` can be learned onto a knob, and a pad
of rows 4–5 is the button.

`Registry.enum(…, has=None)` stores `Param.has: Callable[[int], bool] |
None` — which of an enum's choices hold something. It is the enum's
counterpart of `Registry.trigger(lit=)`: the param carries what its
lights need, so the adapter learns nothing about the bank. Only
`preset.select` sets it. WP2 reads it.

`preset.select`'s tip: "The show's twenty-four presets: F1–F8, then the
desk's clip rows 4 and 5. …".

#### The PRESETS page

*Measured* at `app.CONTROL_SIZE` (960 × 900), the rig of
`tests/test_ui_shell.py`, a bank of 24 with 16 filled. The page child has
about 796 px (the first layout to scroll did so at 825 px of content).

| Layout | Folded | "more" open | Reads |
|---|---|---|---|
| Today (8 slots, two a row) | 400 px | 680 px | "F7 MANDALA" |
| 24 slots, two a row | 632 px | 912 px: **scrolls** (computed from the fold's 280 px) | — |
| **B: F1–F8 two a row, then 9–24 four a row** (92 px chips) | 516 px; **504 px** with the sixteen's rows 3 px apart | **784 px**: fits, 12 px spare | "9 TRIP 2", "11 MAND…", "12 BIG BL…", "15 hands…" |
| A: F1–F8 two a row, then 9–24 eight a row (42 px chips) | 458 px | 738 px (computed: 767 measured with one more line) | "9 T…": a number and one letter |
| All twenty-four four a row | 458 px | 738 px (computed likewise) | F7 becomes "MAND…": the first eight lose their names |
| Three columns of eight | 545 px | scrolls, by about 29 px (58 measured with one more line) | full names |

**B is built** (fork 6):

```
 presets  ·  F1–F8  ·  ⇧ saves  ·  9–24 on the desk
 ┌──────────────────────┐ ┌──────────────────────┐
 │ F1  TUMBLE           │ │ F2  FACES            │
 │ F3  FIELD            │ │ F4  WAKE             │
 │ F5  TRIP  ●          │ │ F6  ACID             │      the loaded one lit; its dot (WP5)
 │ F7  MANDALA          │ │ F8  NOITA            │
 └──────────────────────┘ └──────────────────────┘
 ┌──────────┐┌──────────┐┌──────────┐┌──────────┐
 │ 9 TRACER ││ 10 TRIP 2││ 11 —     ││ 12 —     │      desk row 4, pads 1–4
 │ 13 —     ││ 14 —     ││ 15 —     ││ 16 —     │      desk row 4, pads 5–8
 │ 17 —     ││ 18 —     ││ 19 —     ││ 20 —     │      desk row 5, pads 1–4
 │ 21 —     ││ 22 —     ││ 23 —     ││ 24 —     │      desk row 5, pads 5–8
 └──────────┘└──────────┘└──────────┘└──────────┘
```

- `BANK_COLS = 2` for `k < F_KEYS`, `FAR_COLS = 4` after; the sixteen's
  rows are 3 px apart (`FAR_GAP`), the rest of the page as it is.
- A far slot's key is its number ("9"); its hover says where it is:
  "slot 12: TRIP 3 — the desk's row 4, pad 4. Click loads, ⇧click saves
  the live state as it". An empty one: "slot 12: empty — right-click to
  put a preset here; a hold on the clip-stop row fills the next empty
  slot".
- Click and ⇧click on a far slot call `pr.load_slot(k)` /
  `pr.save_slot(k)`. Its right-click menu is `panel._ctx(r["preset.select"],
  f".{k}", extra=…)` — the slot menu ("put preset here…", "clear slot")
  under the select param's own items, as the rail does for `ui.page`.
  The first eight keep `preset.load.k`.
- The micro label gains "9–24 on the desk"; the hover's "eight" becomes
  "twenty-four".
- No second label line, no paging, no fold: all twenty-four are on the
  page at once.

The 12 px of spare room with "more" open is thin: a wrapped warning under
the fold would scroll the page while the fold is open. WP4 keeps its two
new lines out of the fold for that reason, and the fit test below draws
the fold open.

#### `owner_home`

`tests/conftest.py` gains a fixture every package's "on a copy" test
uses: a temp home holding a `mine` show and a user copy of `party`, each
with an eight-name bank; three presets saved by today's build (so their
`desk` holds the sixteen shape pads, one of them with a pad the owner
re-aimed and a device knob the owner learned); a `bindings.json` as
today's build writes it, with one row the owner changed; `last_show`,
`windows.json`, a `stall.log`, a `weights/` file and one file already in
`trash/presets/`. It is built by running today's writers (`Presets.save_as`,
`Project.save`, `Bindings.write`), not by hand-written JSON, so it tracks
the formats.

**Undo, trash.** No `undo.push`: a bank edit is no step today
(`test_presets.py::test_the_bank_calls_are_no_undo_step`) and none is
added. No `to_trash`. One `routing.backup`.

---

### WP2 — Rows 4–5 are the bank

**What.** Clip rows 4 and 5 load slots 9–24 on both layers. A filled slot
is amber, the loaded one green, an empty one dark. Old files come along.

**Owns.** Its lines in the table; `tests/test_desk.py`, `test_routing.py`,
`test_midi.py`, `test_ui_desk.py`, `test_presets.py` (the desk tests),
`test_learn.py` (one case). **Must not touch** `library.py`, `params.py`,
`ui_presets.py`.

#### The desk

Clip rows 1–5 and the clip-stop row; column 9 is the scene-launch column.
`[ ]` is an invariant pad (the same on both layers), `·` a dark one.

```
 BEFORE (today)          preset layer                              under SHIFT (global layer)
        1     2     3     4     5     6     7     8      9         1 … 8                  9
 G1   [F1]  [F2]  [F3]  [F4]  [F5]  [F6]  [F7]  [F8]   Points      [F1] … [F8]            ·
 G2     ·     ·     ·     ·     ·     ·     ·     ·    Lines       scene 1 … scene 8      ·
 G3     ·     ·     ·     ·   STILL ORBIT WAVE RIPPLE  Faces       scene 9, 10, 11 · · · · ·   ·
 G4   shape 1 …………………………………………………………… shape 8       Rotate      · · · · · · · ·        ·
 G5   shape 9 …………………………………………………………… shape 16      Reset view  · · · · · · · ·        ·
 G6   [════════════ SAVE AS (hold) ════════════]      [Reset all]  [════ SAVE AS ════]   [Reset all]
 C    cue knob: Shape (relative, all 25)                           ·

 AFTER (plan 19)         preset layer                              under SHIFT (global layer)
        1     2     3     4     5     6     7     8      9         1 … 8                  9
 G1   [F1]  [F2]  [F3]  [F4]  [F5]  [F6]  [F7]  [F8]   Points      [F1] … [F8]            ·
 G2     ·     ·     ·     ·     ·     ·     ·     ·    Lines       scene 1 … scene 8      ·
 G3     ·     ·     ·     ·   STILL ORBIT WAVE RIPPLE  Faces       scene 9, 10, 11 · · · · ·   ·
 G4   [ 9]  [10]  [11]  [12]  [13]  [14]  [15]  [16]   Rotate      [ 9] … [16]            ·
 G5   [17]  [18]  [19]  [20]  [21]  [22]  [23]  [24]   Reset view  [17] … [24]            ·
 G6   [════════════ SAVE AS (hold) ════════════]      [Reset all]  [════ SAVE AS ════]   [Reset all]
 C    cue knob: Shape (relative, all 25)                           ·

 a bank pad:   green = the loaded preset     amber = a preset is here     dark = empty
 after a save-as: the bar and the new slot's pad blink for 1.5 s (as today on row 1)
```

Nothing else on the desk moves. Rows 2 and 3 are left as they are: row 2
is free on the preset layer for a preset (or plan 20) to use, and the
band scenes stay behind SHIFT.

```python
# apc40.py
BANK_PADS: list[tuple[int, int]] = [                 # (note, channel) of slot k
    *[(N_CLIP[0], k) for k in range(8)],             # row 1: slots 1–8
    *[(N_CLIP[3], k) for k in range(8)],             # row 4: slots 9–16
    *[(N_CLIP[4], k) for k in range(8)]]             # row 5: slots 17–24

def filled_of(number: int, on: int) -> int | None:
    """The velocity for "something is here, not selected": YELLOW on the
    clip grid, None on any other button (it has no third state)."""

# in DEFAULT_MAP, in place of the row-1 line and the two view.shape lines:
*[_note("preset.select", n, ch, op="set", value=k, on=GREEN)
  for k, (n, ch) in enumerate(BANK_PADS)],
```

No `layer`, so the 24 rows are invariant: one meaning on both layers, no
Learn takes them, no preset maps them (D6, extended by the owner's
go-ahead; the docs package records it). The module docstring's invariant
list gains "clip rows 4 and 5". `bindings.default.json` is regenerated.

#### Lights

```python
# routing.py
def led_level(b: Binding, p: Param) -> int:
    """2: lit (`led_lit`). 1: a `set` row on an enum whose param says that
    choice holds something (`Param.has`) and is not the one selected.
    0: off."""
```

`MidiIO.feedback`'s LED branch sends `b.on` at level 2, `filled_of(b.number,
b.on)` at level 1 when the profile has one and it answers (else `b.off`),
`b.off` at level 0; a blink still wins. `_leds_on` and `_fire_holds` keep
reading `led_lit`, so "the LEDs the fire turned on" is still the new
slot's pad going to level 2, and the blink after a save-as needs no
change: `apc40.blink_of` already covers every clip row.

`ui_desk._led` draws level 1 in `_LED[YELLOW]` at half strength. Plan 17's
`ui_desk.text` gives a bank pad its preset's name through the enum's
choices; an empty slot's choice is "SLOT 12" (`build_registry`'s `names`),
which WP2 turns into no label at all for a bank pad at level 0 — a dark,
empty pad shows its glyph only, like any dark control. (If `text` is not
there as plan 17 describes it when this is built, the package says what
it found in its "as built".)

Yellow at velocity 5 is from Akai's table, as the global layer's scene
pads use it; whether the mk1 shows amber that reads apart from green on a
dark desk is hand check O2.

#### An existing `bindings.json`

`bindings.json` holds only the session's rows since plan 13 WP5, so the
owner's file has no row on rows 4–5 and the sixteen pads are **added**:

```python
# routing.py
APC_NEW_ROWS += tuple(
    (f"note:{ch}:{n}", "preset.select", "set", float(k), False)
    for k, (n, ch) in enumerate(apc40.BANK_PADS) if k >= 8)
```

`remap_factory` adds a row only where nothing uses the source and builds
it with `feedback="led"`, `on=1` (green) and no layer: exactly the factory
row. *As built:* only where **no MIDI row overlaps the control**
(`Binding.overlaps`), so an any-channel row the owner wrote by hand
holds the pad too — for every `APC_NEW_ROWS` entry (§7 WP2). A file from **before** plan 13's migration still holds the sixteen
shape rows; `sort_layers` now finds them on an invariant factory control
and leaves them invariant, so they are swapped by name:

```python
APC_REMAP |= {
    (f"note:{k}:{N_CLIP[3]}", "view.shape", "set", float(k)):     ("preset.select", "set", float(8 + k)),
    (f"note:{k}:{N_CLIP[4]}", "view.shape", "set", float(8 + k)): ("preset.select", "set", float(16 + k)),
}   # for k in 0…7; APC_REMAP_PLAN names them "plan 19"
```

A plan-19 swap also clears the row's `layer`: in a schema-3 file from
between plan 13's WP3 and WP5 those rows say `"layer": "preset"`, and
left so they would be carried into the migrated preset and keep the
sixteen invariant rows from being added.

- **A row the owner changed is left alone**: any other row on one of the
  sixteen sources (another target, op or value) matches no `APC_REMAP` key
  and takes the source, so nothing is added there. That pad then does
  what the owner's row says and its slot is reached from the PRESETS page
  only. `remap_factory`'s notes say what was added and swapped; hand
  check O4 tells the owner where to look. *As built:* those notes never
  reached the panel — the startup preset's load clears `Bindings.notes`
  before the first frame, as it always had — so the launch's sum is kept
  in `Bindings.said`, one line on the SYSTEM page; each row is on stderr
  (§7 WP2).
- **Backed up first**: `Bindings.load` already calls `backup(path,
  t.read_at)` before `t.write()` when `remap_factory` changed anything.
  WP2 makes that branch `if backup(…) is None: t.error = "bindings: not
  rewritten — no backup could be made"` and **skips the write**: the
  table in memory is the remapped one, the file is as it was, and the
  next launch tries again. This also covers plan 09's and plan 15's
  remaps, which go through the same branch. *As built:* `Bindings.write`
  keeps the rule for the rest of the session (`Bindings.unbacked`: it
  tries the copy first and writes nothing without it), and
  `preset.migrate_home`'s rewrite backs up before it announces.
- **Once**: a second load finds every source taken.
- **Proved on a copy**: `owner_home`'s `bindings.json`, loaded twice.

#### A preset whose desk maps rows 4–5

```python
# routing.py
RETIRED_DESK_ROWS: frozenset[tuple[str, str, str, float]]
"""Factory preset-layer rows a later plan took for the session: plan 19's
sixteen shape pads, as (source, target, op, value)."""
```

`Bindings.set_desk` drops a row on an invariant control as today. If the
row is one of `RETIRED_DESK_ROWS` it is dropped **without a note**; any
other row on those pads keeps today's note ("dropped note:2:56 →
fx.acid.on: that control is invariant, the session's (plan 13 D6)"),
which reaches the warning line and ROUTING's head through `Presets.notes`
/ `desk_notes` as it does now. The same applies to `set_desk(load=False)`
(an undo's restore of a desk taken before the upgrade cannot exist in one
process, but a hot reload can meet one).

- The preset's **file is not rewritten** by a load. Its dot is clean (the
  reference is taken after the load: `Library._apply_doc` records
  `kind.signature()`), and the next save writes the desk without those
  rows, the old file going to the trash by plan 15's rule.
- A preset with **no `desk` key** gets the fresh preset layer, which no
  longer has the shape pads: nothing to drop.
- **Which factory presets carry those rows**: all 18 that have a `desk`
  key (*measured*: the eight house moods, the nine `party-*`,
  `lfo-breathe`). The five without one (`legacy6`, `hands-fx`,
  `hands-orbit`, `hands-pinch`, `hands-play`) follow the loader.
  `python -m hyperspace.preset` regenerates the 18; a fresh desk is 26
  rows, down from 42.

**Tests that change, by design.**
`test_desk.py::test_the_default_map_is_sorted_as_plan_13_says` (16 of its
113 old pairs are gone; the 16 bank pads join its "new rows"),
`test_ui_desk.py::test_every_midi_row_shipped_has_a_glyph` and the hover
test (their examples on G4/G5), and plan 17's desk tests if they name a
shape pad.

**Undo, trash.** None. One `routing.backup` (existing).

---

### WP3 — The factory preset layer re-cut

**What.** The device knobs that are dark get params that do something on
that preset. Generated data: `apc40.DEFAULT_MAP`'s preset layer,
`preset.py`'s tuples, the 23 files regenerated.

**Owns.** Its lines in the table; `tests/test_presets.py`,
`test_plan12_presets.py`, `test_desk.py` (one assertion). **Must not
touch** a `*_values` or `*_routes` function (plan 20's seam), `routing.py`,
`library.py`.

#### Today (*measured* from the 23 files)

K1–K8 are the same on every factory preset: Brightness, Speed, Instances,
Pattern mix, Grid amp, Grid rate, Bitmap alpha, Zoom.

| Preset (file) | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 |
|---|---|---|---|---|---|---|---|---|
| the eight house moods | · | · | · | · | · | · | · | · |
| TUMBLE, FACES, FIELD | · | · | · | · | · | · | · | · |
| `legacy6`, `hands-play`, `hands-orbit`, `hands-fx`, `hands-pinch` (no `desk` key) | · | · | · | · | · | · | · | · |
| `lfo-breathe` | `macro.1` | · | · | · | · | · | · | · |
| WAKE | `dream.echo_mix` | `dream.fade` | `dream.darken` | `dream.contrast` | `dream.occlude` | `dream.mix` | `dream.sat` | `dream.k` |
| TRACER | `dream.echo_mix` | `dream.fade` | `dream.echoes` | `dream.gap` | `dream.darken` | `dream.contrast` | `dream.occlude` | `view.depth4` |
| TRIP | `fx.mix` | `fx.plasma.level` | `fx.kaleido.segments` | `fx.kaleido.zoom` | `fx.zoomblur.amount` | `fx.zoomblur.glow` | `fx.huecycle.paint` | `fx.huecycle.spread` |
| ACID | `fx.mix` | `fx.acid.bend` | `fx.acid.twist` | `fx.acid.reach` | `fx.acid.breathe` | `fx.wobble.amount` | `fx.deconverge.amount` | `fx.huecycle.spread` |
| MANDALA | `fx.mix` | `fx.plasma.level` | `fx.kaleido.segments` | `fx.kaleido.zoom` | `fx.fractals.amount` | `fx.fractals.ground` | `fx.glimmer.amount` | `fx.glimmer.ground` |
| NOITA | `fx.mix` | `fx.warp.amount` | `fx.warp.scale` | `fx.tripcolour.amount` | `fx.fractals.amount` | `fx.fractals.size` | `fx.doublevision.amount` | `fx.doublevision.ghost` |

Sixteen presets have no device knob at all. The six that have eight
already carry what the session reached for (the stack's mix on D1, then
the family's amounts; the echoes' mix and fade on D1 and D2). Also
*measured*: no factory preset names a bitmap (`view.bmp_file`), so K7
(Bitmap alpha) moves nothing on any of them.

#### The rule

A mapped knob does something on that preset. So no factory knob lands on
an effect that is off there, or on the look-back while it is off — the
desk's version of the standing rule for routes
(`test_plan12_presets.py::test_no_factory_route_drives_an_effect_that_is_off`).
The session reached for the effect mix and the echo mix on every preset;
on a preset with no effect on and no look-back those two knobs would be
dead, so they are **not** put there (fork 7 says what it would take).

#### After

`SCENE` is the fresh preset layer's device-knob block, in
`apc40.DEFAULT_MAP` (`layer=P`), so a fresh preset, a file with no `desk`
key and every scene-only factory preset get it:

| | D1 | D2 | D3 | D4 | D5–D8 |
|---|---|---|---|---|---|
| **`SCENE`** | `view.depth4` 4D depth | `camera.yaw` Yaw | `camera.pitch` Pitch | `view.pattern` Pattern | · |

Why these four: they are the continuous scene params not already on
K1–K8 that act on every preset whatever is switched on (the 4D
perspective, the camera's two angles), and the face pattern, which is the
quickest change of look a scene has. `view.pattern` is an enum on an
`abs` knob; `MidiIO._apply` lands it with `set_norm`. The package proves
with a test that the knob steps through every pattern and its ring
follows; **if it does not, D4 stays dark** and the "as built" says so.

| Preset | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Why |
|---|---|---|---|---|---|---|---|---|---|
| the eight house moods, TUMBLE, FACES, FIELD, `legacy6`, `hands-play`, `hands-orbit` | `SCENE` | | | | · | · | · | · | scene only. On TUMBLE the right hand pushes 4D depth from where D1 leaves it; on FACES and `hands-orbit` a hand pushes the camera from where D2 / D3 leave it (a knob sets the base, ARCHITECTURE §3.2) |
| `hands-fx` | `fx.mix` | `fx.acid.bend` | `fx.acid.twist` | `fx.acid.reach` | `fx.acid.breathe` | `fx.acid.speed` | `view.depth4` | `camera.yaw` | the Acid shader is its one effect; three of these are positioned by a hand while it is in the box, and the knob is what they come back to |
| `hands-pinch` | `fx.mix` | `fx.huecycle.paint` | `fx.huecycle.spread` | `view.depth4` | `camera.yaw` | `camera.pitch` | `view.pattern` | · | the hue cycle is its one effect, at a mix of 0 until a pinch or D1 lifts it |
| `lfo-breathe` | `macro.1` | `fx.mix` | `fx.plasma.level` | `lfo.1.depth` | `view.depth4` | `camera.yaw` | `camera.pitch` | · | Breathe stays on D1 (hand check 39); the mix LFO 2 swells, the plasma it swells, and the depth the right hand deepens from |
| WAKE, TRACER, TRIP, ACID, MANDALA, NOITA | unchanged | | | | | | | | already the session's kind of eight; plan 12 §6 and plan 14 tuned them |

K1–K8 are **not** re-cut: they are the same eight on every preset and the
only knobs the owners have played. K7's dead knob is noted for the owner
(hand check O5), not changed.

Counts: 16 presets with nothing become 14 with four, one with eight
(`hands-fx`) and one with seven (`hands-pinch`); `lfo-breathe` goes from
one to seven; six are unchanged.

#### The code

- `apc40.DEFAULT_MAP`: four `_cc(…, layer=P)` rows on `DEVICE_KNOBS[0:4]`
  beside the global layer's band strip (a knob has a row per layer today:
  the track knobs do).
- `preset.knob_desk(targets)` becomes "the fresh desk **less its device
  knobs**, plus these": `[*(b for b in fresh_desk() if not _is_device_knob(b)),
  *(device_knob(k + 1, t) for k, t in enumerate(targets) if t)]`; a `None`
  in the tuple leaves that knob dark. `lfo_breathe_desk` goes through it.
- New tuples `HANDS_FX_KNOBS`, `HANDS_PINCH_KNOBS`, `BREATHE_KNOBS`;
  `hands-fx` and `hands-pinch` get `desk=knob_desk(…)` and so a `desk` key
  in their files. `legacy6`, `hands-play` and `hands-orbit` keep
  `desk=None`.
- `python -m hyperspace.preset`; the 23 files committed as generated.

#### Rules that hold (the existing tests, and two new)

- No control mapped twice on a layer; no row on an invariant control
  (`test_presets.py::test_every_factory_presets_desk_is_the_generators`,
  extended to assert one row per control). *As built:*
  `test_plan12_presets.py::test_wake_and_trip_device_knobs_move_their_bases`
  could not stay unchanged: TUMBLE's D1 is now 4D depth, which is also
  TRACER's D8, so its "does nothing on another preset" check leaves that
  one param out (§7 WP3).
- Every desk target is a persisted performance param, never a session
  one (the existing check over `values`, applied to `desk` targets).
- No factory route onto an effect that is off (unchanged).
- New: no factory knob onto an effect that is off or the look-back while
  it is off; every factory knob's target exists in the registry.

#### A preset the owner saved earlier

It carries its own `desk`, written whole by `Presets.document`. **Nothing
here touches it**: its device knobs are what they were (dark, or what was
learned). A user file with no `desk` key (one plan 13's migration made
from a slot that had no desk) gets the fresh layer by the standing rule
(`Presets.load_doc` step 4), so it gains `SCENE` on D1–D4.

**Undo, trash.** None; no file of the owner's is written.

---

### WP5 — The dirty dot and the save label

**What.** The preset's "unsaved" reads from a step back; the save chip
says whether it overwrites or copies. No new control.

**Owns.** `ui.dirty_dot`, the rail's dot, `ui_presets.strip`,
`ui_presets.save_label`, `ui_routing._preset_line`; `tests/test_ui_presets.py`,
`test_ui_routing.py`, `test_ui_shell.py`. **Must not touch**
`_list_popup` (WP4), `preset_bank` beyond the one dot.

- **The dot** is a filled disc, `ui.DOT_R = 6` px (12 px across, where
  the glyph's ink is about 7), in `ui.RED`, drawn in a cell as tall as
  the line so no row grows: `ui.dirty_dot(tip: str) -> None`. Used by the
  strip (every group's) and ROUTING's head. The rail's disc goes from
  radius 3.5 to 5. The show's own dot is left as it is.
- **The save chip is lit while there is something to save**:
  `ui.lit_chip` (solid red, white text — the panel's "a lit key, readable
  from the floor") when the group is dirty, the quiet chip when clean.
  At the control size that is a 50 × 22 px red pill ("save copy": 83 ×
  22). This is what reads at arm's length; the disc says which name it
  belongs to.
- **The loaded slot's button** in the bank carries a white disc of radius
  4 at its right end while the loaded preset is dirty.
- **The label**: `save_label(lib, group) -> str` is "save copy" when the
  loaded preset is a factory one (`Library.is_factory`), else "save". The
  hover: "Save your own copy of TRIP: the factory one is kept and yours
  takes its place in the list" / "Write the settings over TRIP (the old
  file goes to the trash)". The action is `Library.overwrite`, unchanged.
- **Where it fits.** On the **preset strip** (PRESETS) and **ROUTING's
  head**. The preset strip drops `reset` — it does nothing there (§1 row
  12) — which leaves about 205 + 135 px in 392. A **module strip** keeps
  "save": with `reset`, which works there, "save copy" makes the strip
  401 px wide in 392 (*measured*). Its hover already says a factory one
  is saved as a copy.
- No "always ask on save" (the owner's answer): nothing prompts.

Colour: `ui.RED`, the one red, as today's dot. Not measured: how the
strip under "more" lays out with a dot of the new width (its row starts
at `ui.LABEL_W`); the package measures it and the layout test below holds
whatever it finds.

**Undo, trash.** None.

---

### WP4 — Hide, rename and the trash

**What.** From the preset list: × on any preset (yours to the trash, a
factory one hidden), rename, "show hidden", and the trash with restore
and empty. All of it lives in the list popup the strip's name opens; the
page gets no new row.

**Owns.** Its lines in the table; `tests/test_library.py`,
`test_ui_presets.py`, `test_presets.py`. **Must not touch** `strip`
(WP5), `undo.py`.

#### The list

```
 presets
 ACID                              ×        factory (dim): × hides it
 TRIP 2                   rename   ×        yours: × sends it to the trash
 TRIP 3                   rename   ×
 TUMBLE                            ×
 …
 ─────────────────────────────────────
 show hidden (5)                            only when something is hidden
 trash (12) ▸                               only when the trash holds something
```

With "show hidden" on, the hidden ones are listed too, struck through
and dimmer, each with `unhide` in place of ×. "show hidden" is the
popup's own state, not a param, and is off at every launch.

Only the `presets` group's list has the new chips and lines. A module
strip's list is as today (× on your own presets; a factory module preset
cannot be hidden: the band scenes and the group defaults are read by
name, `control.SCENES`, `library.DEFAULT_NAMES`).

#### Hide

```python
# library.py
HIDDEN = "hidden.json"      # <home>/hidden.json
# {"schema": "hyperspace.hidden/1", "presets": ["hands-fx", "legacy6"]}
#   — factory file stems of the presets group, sorted

class Library:
    def hidden(self, group: str = PRESETS) -> frozenset[str]
    def hide(self, group: str, name: str) -> bool      # a factory preset; False for anything else
    def unhide(self, group: str, name: str) -> bool
    def list(self, group: str, *, hidden: bool = False) -> list[str]
```

- The file names factory **file stems** (`party-tracer`), not display
  names: a user preset is never hidden by it, and a user file that shadows
  a hidden factory preset shows as itself.
- `list()` leaves hidden factory presets out; `list(hidden=True)` is
  everything. So the strip's list and arrows, "starts on", "put preset
  here…" and `ui_presets.names` all lose them. **`Project.save_new` and
  `_fresh_name` ask with `hidden=True`**: a made-up name still never
  collides with a hidden preset.
- Hiding changes **only the list**. `path_of`, `load`, `read`,
  `is_factory` are untouched: a bank slot that names a hidden preset
  shows its name and loads it; a show that starts on one starts on it; a
  hidden preset that is loaded stays loaded. × says so: "hidden TRACER —
  slot 9 still loads it".
- It lives in the home and is **the home's, not the machine's**: a taste
  list that should travel with the presets, so it is tracked by WP6's
  git and is not in its `.gitignore`.
- Read at `Library.__init__` and after its own writes; it is in the
  home's top folder, which the watcher does not scan. A file that will
  not parse reads as "nothing hidden" with a warning and is kept beside
  itself (`routing.backup(path, "0")`, the lazy import the library
  already uses) before the first rewrite; no backup, no rewrite.
- Nothing is hidden as shipped: the owner culls at the machine.

#### × on your own preset

Unchanged: `Library.delete` (copy to the trash, then remove; a copy that
fails refuses). New is what is said and shown after:

- The status names what still points at it, from the open show: "TRIP 3
  is in the trash — F6 and 'starts on' still name it; restore it from
  the trash, or clear the slot".
- **The bank** shows a slot whose preset has no file in `ui.WARN` ink,
  with the hover "F6: TRIP 3 — no such preset. It may be in the trash
  (preset list → trash). Right-click → clear slot". It reads the polled
  listing (`names(panel, PRESETS)` at `hidden=True`), not the disk per
  frame. The pad on the desk stays amber: a slot is "filled" when it
  names something (`Param.has`), and pressing it says "no preset 'TRIP 3'"
  as `load_slot` does today. Slots are not cleared for the owner: a
  restore to the old name makes them work again, which clearing would
  prevent.
- The shadow rule is unchanged: × on your copy of a factory preset
  brings the factory one back.

#### Rename

```python
def rename(self, group: str, old: str, new: str) -> Path:
    """Rename a user preset: the file, the name inside it, and every show
    in the home that names it. Raises LibraryError and changes nothing
    when `old` is not a user preset, `new` is empty or taken, or the old
    file cannot be kept in the trash."""
```

`presets` group only (a module preset is named by shows' `modules` and by
the scene list; out of scope). In order, so that a crash at any point
loses nothing:

1. **Refuse** a factory preset ("TRIP is a factory preset: save copy,
   then rename the copy" — fork 8), an empty name, and a name that is
   **taken**: `slug(new)` equal to the slug of any file stem in either
   presets folder or of any listed name at `hidden=True` — the same
   `taken` set `save_new` builds. A rename that only changes case or
   spacing within one slug is allowed (the file keeps its stem).
   *As built:* not quite save-as's set — the renamed file's own stem
   and names are left out, and so are **the open bank's names**, so
   renaming to the name a dangling slot holds makes that slot load
   again; the case-only rename rewrites the file in place after a trash
   copy (§7 WP4).
2. **Write the new file** `<home>/presets/<slug(new)>.json`, created
   exclusively: the old document with `name` replaced, in the kind's own
   text (`preset.dumps`). Nothing else in it changes.
3. **Copy the old file to the trash** (`to_trash`); if that fails, remove
   the new file and raise. Then remove the old file.
4. `_sync(old, new)`: both are our own writes, so the watcher sees no
   edit. If the renamed preset is the loaded one, `_landed(group, new,
   <the reference it had>)`: the name changes, the clean reference does
   not, so an unsaved edit stays an unsaved edit.
5. **Every show**: each `<home>/projects/*.hyp.json` at
   `hyperspace.project/2` whose `bank` or `startup` holds `old` (or the
   old file's stem, which `path_of` also resolves). For each: `to_trash`
   the file (→ `trash/projects/`), then write it with those entries
   replaced. A show whose copy fails is left as it is and named in the
   warning. The **open show** is done through the `Project` object
   (`bank`, `startup`, `_saved`, `write`), so its dot and the bank's
   light are right; a factory show open as shipped that names the preset
   cannot exist (it names factory presets only). A schema-1 show is left
   alone and named: plan 13's migration owns it. Factory shows are never
   written.
6. `Project.follow()`; the load hook is told the new name. Status:
   "renamed TRIP 3 → SUNRISE (2 shows updated)".

**The watcher.** `Library.poll` runs on the frame loop, the same thread
as the click, so it cannot run between two steps; after step 4 the
mtime table knows both paths. A crash between 2 and 3 leaves both files,
two presets with one look: nothing is lost.

**Undo: none** (§1 row 10). The nets: the old file as it was, in
`trash/presets/` under its old name; each rewritten show as it was, in
`trash/projects/`; and renaming it back. An undo step taken **before**
the rename still holds the old name as "what was loaded"; undoing across
the rename lands that name with no file under it, and the next save
writes it as a new preset — the same as undoing across a × today.

**The control.** `rename` on a user row turns the popup's row into the
strip's inline name field (`_name_field`, its key `rename:<name>`, seeded
with the name); Enter commits, Esc or × leaves. A refusal shows on the
library's warning line and the footer.

#### The trash

```python
@dataclass(frozen=True)
class Trashed:
    path: Path          # <home>/trash/presets/trip-3.20261004-011203.json
    group: str          # "presets", "fx", "projects", …
    name: str           # the name inside the file, else its stem
    when: str           # "Oct 4 01:12", from the stamp in the file name

def trash(self) -> list[Trashed]:            # every file under <home>/trash/*/, newest first
def restore_trash(self, item: Trashed) -> str:      # the name it now has
def empty_trash(self) -> int:                # how many files went
```

"trash (12) ▸" opens a second popup:

```
 trash  ·  12 files
 presets   TRIP 3            Oct 4 01:12    restore
 presets   TRIP 3            Oct 4 00:58    restore
 projects  mine              Oct 4 01:20    restore
 fx        acid              Oct 3 23:41    restore
 …                                                     (twelve rows, then it scrolls in its own child)
 ─────────────────────────────────────────────────
 empty trash…
```

- **It lists everything the trash holds**, every group and the shows a
  rename kept, because "empty" deletes what is listed and nothing else:
  what you see is what goes. *As built:* "everything" is every file
  named as `to_trash` writes them (`<stem>.<stamp>[-n]<suffix>`, never a
  dotfile); anything else in a trash folder — a Finder `.DS_Store` — is
  not listed, restored or emptied (§7 WP4).
- **Restore** puts the file back as `<home>/<group>/<stem>.json`, the
  stem being the trash name less its stamp. **Never over a file**: the
  target is created exclusively. When the stem is taken, or (for a
  preset) the name inside is taken by another listed preset, it is
  restored under the next free name (`next_name`: "TRIP 3" → "TRIP 4"),
  with that name written inside, and the status says so: "restored as
  TRIP 4 — TRIP 3 is taken". Only after the write succeeds is the trash
  copy removed. The file keeps its own suffix (`.hyp.json` for a show).
  `_sync` the new file: a restore loads nothing and is not an edit. A restored show is a show in the list; it is not opened.
- **Empty** is the only place in the app that deletes with no copy kept.
  It asks once, in place, with no modal: the chip becomes "delete 12
  files for good? — click again" in `ui.WARN` for 4 s; a second click in
  that time empties, anything else (the time running out, closing the
  popup, any other click) disarms it. The show keeps running throughout;
  nothing waits on the answer. It removes the files `trash()` lists and
  the then-empty folders, and nothing outside `<home>/trash/`
  (`empty_trash` resolves each path and refuses one that is not under
  it). With WP6's git on, the trash is ignored, so emptying it is final
  there too; every file in it that was ever saved with git on is still
  in the history.
- The trash is still no group and still never watched.

**Undo, trash.** No `undo.push` anywhere in this package. `to_trash`:
in `rename` (the old preset file; each show) and `Library.delete`'s
existing call. One `routing.backup`: an unreadable `hidden.json`.

---

### WP6 — The home in git

**What.** With `[library] git = true`, the home is a git repository and
every save is a commit. Off by default. Git never blocks, fails or slows
a save.

**Owns.** New `homegit.py` and `tests/test_homegit.py`; its lines in
`config.py`, `app.py`, `library.py`, `hotreload.py`, `ui.py`. **Must not
touch** anything else.

#### Config

```toml
[library]
git = false     # true: <home> is a git repository and every save is a commit.
                # Local only: no remote is added, nothing is pushed or fetched.
                # Needs git on the PATH; without it saves go on and a note says so
```

`config.DEFAULTS["library"] = {"git": False}`, documented in the module
docstring beside the other sections. A value that is not a boolean is
`False` with a note in `cfg["notes"]` (the SYSTEM page shows it).

#### The module

```python
# homegit.py — imports nothing from the package (like placement.py)
IGNORE = """\
# Written by Hyperspace when [library] git was switched on. Yours to edit.
weights/
trash/
*.log
last_show
windows.json
*.bak-*
.DS_Store
"""

class Committer:
    def __init__(self, home: Path, *, git: str = "git", timeout: float = 10.0): ...
    def request(self, message: str) -> None:
        """Ask for a commit of the home as it now is. Returns at once."""
    def notes(self) -> list[str]:
        """What the worker has to say since the last call (drained)."""
    def close(self, timeout: float = 2.0) -> None
```

`app.main` builds one when the key is on and sets `library.committer`;
`Library._commit(message)` calls `committer.request` if there is one,
inside a `try` that swallows everything. The library never imports
`homegit` or `config`.

- **What is ignored, and why.** `weights/` (528 MB of downloaded
  weights), `trash/` (every file in it is an older version git already
  has, or will never have), `*.log` (`stall.log`), `last_show` and
  `windows.json` (this machine's, roadmap §5), `*.bak-*` (the
  migrations' backups: `routing.backup`'s names). **Tracked**: presets,
  shows, every module preset, `config.toml`, `bindings.json`,
  `hands.json`, `hidden.json`, the migrations' two note files.
- **When a commit is asked for**: at the end of `Library.save_as`
  ("save preset TRIP 2" / "save fx acid"), `Library.delete` ("trash
  preset TRIP 3"), `rename` ("rename preset TRIP 3 → SUNRISE"), `hide` /
  `unhide`, `restore_trash`, and `Project.write` ("show mine: bank",
  "show mine: starts on TUMBLE", "save show mine"). Not at launch, not on
  a load, not on a timer. *As built:* `rename` asks **before** its shows
  are rewritten (so it is the commit's subject), `restore_trash` asks
  "restore presets X" (the folder's name), `empty_trash` asks nothing,
  and the committer is attached only after the startup preset (§7 WP6).
- **What a commit is**: `git add -A` then `git commit -m <message>`,
  everything not ignored — so a hand edit of `config.toml`, or a
  migration's rewrite at launch, rides in the next save's commit.
  Nothing staged: no commit. Several requests waiting are one commit,
  the first message its subject and the rest its body. *As built:* the
  waiting messages are taken **after** `add -A`, so a save staged by a
  commit already running is named in it (the scripted launch found the
  words lost otherwise); the words waiting at a failure are dropped and
  their files ride in the next commit.
- **`git init`, and when.** At the first request, never at launch
  (turning the key on writes nothing until something is saved). The
  worker first asks `git rev-parse --show-toplevel` in the home:
  - not a repository → `git init`, write `.gitignore` **only if there is
    none**, and commit everything as "Hyperspace: the home as it was when
    git was switched on"; the save that triggered it is in that commit;
  - a repository whose top level **is** the home → use it as it is (the
    owner's own `.gitignore` and branch are respected; ours is written
    only if there is none);
  - a repository whose top level is **somewhere above** the home (a
    dotfiles repository, a home directory under git) → **never init,
    never commit**. One note: "git: <home> is inside another repository
    (<top>): not committing". The key does nothing for the run.
  (*Measured*: the three cases are told apart exactly this way.)
- **Git never blocks or fails a save.** `request` appends to a queue and
  returns; one daemon thread runs the commands, each with a 10 s timeout,
  `GIT_TERMINAL_PROMPT=0`, `-c core.hooksPath=/dev/null` (no hook of the
  machine's runs) and `-c commit.gpgsign=false` (a signing prompt would
  hang). The file is on disk before the request is made. A missing
  binary, a locked index (exit 128 in 24 ms, *measured*), a timeout or
  any other failure is **said once** — "git: not committed (<reason>);
  saves are not affected" — through `notes()`, which `Library.poll`
  drains onto the warning line on the frame thread (the worker never
  touches the library). It is not said again until a commit has
  succeeded in between. The next request's `add -A` picks up everything
  a failed one missed (*measured* with a lock that came and went).
- **No network.** The module never runs `remote`, `push`, `fetch`,
  `pull` or `clone`, and a test greps for them. No remote is added; if
  the owner adds one, nothing here uses it.
- **Identity.** If `git config user.email` is empty the commit carries
  `-c user.name=Hyperspace -c user.email=hyperspace@localhost`; otherwise
  the machine's identity is used as it is. *As built:* each of the two
  is passed only when the machine lacks that one; past its timeout a
  command gets SIGTERM (git removes its own lock), then SIGKILL 2 s
  later.
- **Quit.** `close` waits up to 2 s for the queue; what is left is
  committed by the next run's first save.
- **Tests never run it against a real home.** `Committer.__init__`
  raises when `PYTEST_CURRENT_TEST` is set and `home` resolves to
  `~/Hyperspace`. `tests/conftest.py` already points every test's home
  at its own temp folder and the key is off by default; the tests here
  build a `Committer` on `tmp_path` and skip when there is no `git`.
- The SYSTEM page's home line gains " · git" while a committer is
  attached and has not refused.
- `"homegit"` joins `hotreload.MODULES` among the leaves
  (`tests/test_hotreload.py` holds the list against the package).

**Undo, trash.** None. It writes `.git/` and, when absent, `.gitignore`;
it rewrites no file of the owner's.

---

### WP7 — Docs and hand checks

Owns the shared documents:

- `ARCHITECTURE.md` §1 (the Library row: the bank of twenty-four,
  `hidden.json`, rename, the trash's view, `homegit` as a leaf the Host
  wires; "never listed, watched or emptied" becomes "never watched"),
  §3.7 (the rows for a bank pad, × / hide, rename, restore), §3.8 (the
  sixteen rows `remap_factory` adds; no backup, no rewrite), §4 (the
  shapes of `library.py`, `apc40.py`, `homegit.py`).
- `ENGINEERING.md` §7 (the PRESETS page; the dot) and the home's layout.
- `DECISIONS.md`: D6's row gains clip rows 4 and 5 (the owner's
  go-ahead, 2026-10-04); "A bank slot names a preset file" gains the
  count; plan 15's trash row loses "nothing empties it yet"; a row per
  fork in §6 as built, for the owner to confirm or overturn.
- `DECISION-REGISTER.md`: those forks as rows after plan 18's.
- `plans/README.md` (plan 19's row), `CHECKPOINT.md`.
- `11-hand-checks.md`: group O from §8, numbered after plan 18's group
  N; check 45 (the diagram) and check 56 (save-as: the pad may now be on
  rows 4–5) marked where this plan changes what they say.
- The performer cards under `docs/plans/assets/12-presets/` that name a
  device knob.
- This file's "As built".

## 3. Parameter budget

The owner wants fewer presets in the list and no new nouns.

**The preset list.** Today a fresh home lists **23** presets
(*measured*: `Library.list("presets")`), and the owner's own on top. After
this plan a fresh home still lists 23 — nothing is hidden as shipped —
and every one of them has a ×. The owner's cull decides the number; the
floor is zero.

| Added or removed | Kind | Replaces, or why nothing |
|---|---|---|
| — | **params** | **None added.** `preset.select` grows from 8 choices to 24. The 32 triggers a bank of 24 would have brought (`preset.load.8…23`, `preset.save.8…23`) are not declared (fork 1). The `preset` group stays at 21 params |
| `Param.has` / `Registry.enum(has=)` | a field | Nothing; it is what lets a light say "filled" without the adapter knowing the bank. One param sets it |
| 16 invariant rows on clip rows 4–5 | desk rows | The 16 `view.shape` pads, which the cue knob covers (and reaches nine more shapes) |
| 4 device-knob rows on the fresh preset layer; knobs on `hands-fx`, `hands-pinch`, `lfo-breathe` | desk rows | Dark knobs |
| `[library] git` | config key | Nothing; opt-in, default off |
| `hidden.json` | file in the home | Nothing; without it hiding would mean deleting factory files |
| `.git/`, `.gitignore` | files in the home | Nothing; only with the key on |
| `<show>.bak-v2-bank8` | backup file | Nothing; once per show, the first time a far slot is used |
| 16 slot buttons on PRESETS | page elements | Nothing: they are the feature. No page, no fold, no label line added |
| × on a factory preset | list chip | The missing half of the × that user presets have |
| `rename` on a user preset | list chip | Nothing; there was no way to rename. Not a menu item, not a page |
| "show hidden (n)" | list line | Nothing; shown only while something is hidden |
| "trash (n) ▸" and its popup (`restore` per row, `empty trash…`) | list line, popup | Nothing; shown only while the trash holds something. Not a page |
| `reset` on the preset strip | chip **removed** | It did nothing there |
| "save copy" | a label | "save" on a factory preset |
| the dirty disc, the lit save chip, the dot on the loaded slot | drawing | The "●" glyph |
| menu items | — | None |
| pages | — | None |
| new words on the panel | — | "hidden", "unhide", "trash", "restore", "rename", "save copy". "Slot" for 9–24 is plan 15's word ("clear slot") |

## 4. What this plan does not change

- **A preset load replaces everything** (D2). A pad on rows 4–5 is a
  preset load like any other: the desk drops to the preset layer (D4),
  one undo step.
- **Module presets are labels** (D3); nothing composes.
- **Two layers under a latched SHIFT** (D4), **the global layer is fixed**
  (D5): the bank pads are invariant, so SHIFT never hides them.
- **Invariant controls** (D6) — extended, by the owner's go-ahead, with
  clip rows 4 and 5. A Learn on them is refused; a preset's row on them
  is dropped.
- **Knobs jump, faders pick up** (D7); **an unmapped control is dark and
  dead** (D8): D5–D8 on a scene preset stay dark rather than carry a
  param that does nothing there.
- **The analyzer is session** (D9): no factory knob lands on a session
  param.
- **A session names its startup preset** (D11); home is that preset.
- **A bank slot names a preset file.** F1–F8 and ⇧F1–F8 are the first
  eight, unchanged; the keys' rows are untouched.
- **Factory presets ship read-only; a user file shadows a factory file of
  the same name.** Hiding writes a list in the home; "save copy" is the
  shadow.
- **The library is watched like source.** A renamed, trashed or restored
  file is the library's own write (`_sync`) and is never re-applied or
  brought back by the watcher.
- **The party show is what the rig opens.** It gains TRACER on slot 9.
- **Plan 12's five and plan 14's three**: their routes, values and device
  knobs are as they were.
- **The glyphs and `apc40.LAYOUT`**: untouched (G4·1 is still G4·1).
- **No page scrolls at the control size.**
- **Plan 15**: undo's rules (no file is undo's); the trash's rules (copy
  first; a failed copy refuses a delete); save-as into the next empty
  slot; "put preset here…" / "clear slot". **Plan 16**: the dot's
  tolerance (`undo.alike`); `windows.json` is the machine's.
- **Not built**: preset folders (roadmap §6: hiding and the filter
  first); tags; a search field in the list; paging the bank; F9–F12;
  per-slot colours; a remote for the home's repository; restoring a
  version from git inside the app.

## 5. Exit criteria

### Headless: named tests

Every test runs on a temp home (`tests/conftest.py`). "On a copy" means
the `owner_home` fixture.

**WP1**

| Test | Proves |
|---|---|
| `test_library.py::test_the_bank_is_twenty_four_and_the_f_keys_eight` | `SLOTS == 24`, `F_KEYS == 8 == routing.F_KEYS`, `len(Project().bank) == 24` |
| `::test_an_eight_slot_show_loads_and_is_not_rewritten` | on a copy: `mine` and the `party` copy open, their files' bytes and mtimes are unchanged after open, a preset load, home and a quit; the show is clean |
| `::test_a_show_that_uses_only_the_first_eight_is_written_with_eight` | "starts on" changed: the file's `bank` has 8 entries, no backup is made |
| `::test_the_first_write_past_slot_eight_keeps_the_eight_slot_file` | `put_slot(11, …)`: `.bak-v2-bank8` holds the old bytes; a second far write makes no second backup; a backup that fails writes nothing and puts the slot back |
| `::test_a_long_bank_read_by_eight_slots_shows_the_first_eight` | a 24-entry document cut to 8, as an older build cuts it, is the first eight names (the downgrade, stated) |
| `::test_next_empty_reads_the_banks_own_length` (changed) | `next_empty` and save-as on the real 24-slot bank: the party show's first empty slot is 10; "saved … → slot 10" |
| `test_presets.py::test_save_new_lands_past_the_f_keys_and_a_full_bank_says_so` | fifteen save-as calls fill 10–24, the sixteenth saves to the list |
| `::test_active_follows_the_loaded_preset_from_one_place` | a preset on two slots lights the one pressed; a cleared slot moves the light to the other; nothing loaded lights none |
| `test_params.py::test_the_bank_adds_no_params` | the `preset` group has 21 params; `preset.select` has 24 choices and a `has` |
| `test_ui_presets.py::test_twenty_four_slots_fit_the_page_with_more_open` | at `CONTROL_SIZE`, the fold open, 24 filled slots with the longest factory names: scroll range 0 |
| `::test_a_far_slot_reads_its_number_and_name_and_has_the_slot_menu` | labels "9 TRACER", "11 —"; a click loads slot 9; the right-click menu has put / clear |
| `test_ui_shell.py::test_every_page_fits_the_control_window` | unchanged, passes |
| `test_party_show.py::test_the_party_show_has_tracer_on_slot_nine_and_room_after` | the factory show |

**WP2**

| Test | Proves |
|---|---|
| `test_desk.py::test_rows_four_and_five_load_slots_nine_to_twenty_four_on_both_layers` | each of the 16 pads loads its slot with SHIFT off and on; `len(apc40.BANK_PADS) == library.SLOTS` |
| `::test_the_bank_pads_are_invariant` | a Learn on one is refused; a preset's row on one is dropped |
| `test_midi.py::test_a_bank_pad_is_green_loaded_amber_filled_and_dark_empty` | the velocities sent for the three states; a load moves green; a cleared slot goes dark |
| `::test_save_as_blinks_the_new_pad_on_row_four` | the hold fires, slot 10's pad and the bar blink at `blink_of` for `BLINK_S` |
| `test_routing.py::test_an_older_file_gets_the_bank_pads_with_a_backup` | on a copy: 16 rows added, `bindings.json.bak-v3` holds the old bytes, a second load changes nothing |
| `::test_the_old_shape_pads_are_swapped_and_a_changed_row_is_left_alone` | a pre-plan-13 file: the 16 exact rows become bank rows; a pad the owner re-aimed keeps its row and gets no bank row |
| `::test_a_remap_whose_backup_fails_writes_nothing` | the file's bytes are unchanged, the table in memory is remapped, the error says so |
| `test_presets.py::test_an_old_preset_loads_without_its_shape_pads_and_its_file_is_untouched` | on a copy: no warning for the 16; the dot is clean; the file's bytes are unchanged; the pad the owner re-aimed is dropped **with** its note |
| `::test_write_factory_regenerates_every_factory_file` (unchanged) and `::test_every_factory_presets_desk_is_the_generators` | every factory file is what the generator writes; none maps rows 4–5 |
| `test_ui_desk.py::test_a_filled_pad_is_amber_and_an_empty_one_has_no_label` | the on-screen desk |

**WP3**

| Test | Proves |
|---|---|
| `test_presets.py::test_every_factory_presets_desk_is_the_generators` (extended) | one row per control per preset; no row on an invariant control; the knob table of §2 WP3, preset by preset |
| `test_plan12_presets.py::test_no_factory_knob_is_dead` | no device knob on an effect that is off, or on the look-back while it is off, in any factory preset; every target is a persisted performance param the registry has |
| `::test_no_factory_route_drives_an_effect_that_is_off`, `::test_every_effect_is_on_in_a_factory_preset`, `::test_wake_and_trip_device_knobs_move_their_bases` | unchanged, pass |
| `test_midi.py::test_a_knob_on_the_pattern_steps_through_every_pattern` | D4 on an enum (the gate for D4) |
| `test_presets.py::test_a_users_desk_is_untouched_by_the_recut` | on a copy: a user preset's learned device knob and its dark ones are as saved |

**WP5**

| Test | Proves |
|---|---|
| `test_ui_presets.py::test_the_dot_is_a_twelve_pixel_disc_and_save_is_lit_while_dirty` | the disc's radius; the chip is the lit one only while dirty; the row's height is unchanged |
| `::test_save_reads_save_copy_on_a_factory_preset` | the label by `is_factory`; after the save it reads "save" |
| `::test_the_preset_strip_has_no_reset_and_does_not_overlap` | the chips' rects clear the name's at the longest factory name |
| `test_ui_routing.py::test_the_head_has_the_same_dot_and_label` | ROUTING's head |

**WP4**

| Test | Proves |
|---|---|
| `test_library.py::test_hiding_a_factory_preset_takes_it_off_the_list_and_nothing_else` | `list()` loses it, `list(hidden=True)` keeps it, a slot and "starts on" still load it, the factory file is untouched, `hidden.json` has its stem |
| `::test_a_made_up_name_never_collides_with_a_hidden_preset` | `save_new` with TRACER hidden and loaded |
| `::test_an_unreadable_hidden_list_is_kept_before_it_is_replaced` | — |
| `::test_rename_updates_every_show_and_keeps_each_old_file` | on a copy: the file, the name inside, `mine` and the `party` copy (bank and `startup`), the open show's dot clean; each old show and the old preset in the trash |
| `::test_rename_refuses_a_taken_name_and_a_factory_preset` | nothing on disk changes |
| `::test_a_rename_that_cannot_keep_the_old_file_changes_nothing` | `to_trash` failing: no new file, the old one in place |
| `::test_renaming_the_loaded_preset_keeps_its_unsaved_edit` | the name changes, the dot stays lit, save writes the new file |
| `::test_the_watcher_never_resurrects_or_reloads` | after ×, rename and restore, `poll()` applies nothing, recreates nothing, and `current` is right |
| `::test_restore_never_overwrites` | a taken stem and a taken name each restore under the next free name; the trash copy goes only after the write |
| `::test_empty_trash_removes_only_the_trash` | every listed file gone, nothing else in the home touched; a path outside the trash is refused |
| `test_presets.py::test_rename_and_trash_are_no_undo_step` | the stack's length is unchanged |
| `test_ui_presets.py::test_the_list_has_a_cross_on_every_preset_and_rename_on_yours` | the chips by row; "show hidden" and "trash" lines appear only when there is something |
| `::test_empty_asks_once_and_disarms` | one click empties nothing; a second within 4 s does; a later one does not |
| `::test_a_slot_whose_preset_is_gone_says_so` | the ink and the hover |

**WP6**

| Test | Proves |
|---|---|
| `test_homegit.py::test_off_by_default_and_nothing_is_written` | no `.git`, no `.gitignore`, no thread |
| `::test_the_first_save_inits_ignores_and_commits` | `.gitignore` is `IGNORE`; `weights/`, `trash/`, `stall.log`, `last_show`, `windows.json`, a `.bak-*` are not tracked; presets, shows, `hidden.json` are |
| `::test_each_save_is_one_commit_with_its_message` | save, rename, × , a bank change |
| `::test_a_home_inside_another_repository_is_never_committed` | no `.git` made in the home, one note |
| `::test_an_existing_repository_and_gitignore_are_kept` | — |
| `::test_git_never_blocks_or_fails_a_save` | a missing binary, a locked index and a `git` that sleeps past the timeout: `save_as` returns without waiting (under half a second against a `git` that sleeps five) with the file written; one note each; the next good commit holds everything |
| `::test_a_machine_with_no_identity_commits_as_hyperspace` | `GIT_CONFIG_GLOBAL=/dev/null` |
| `::test_no_network_commands` | the module's source names no `push`, `fetch`, `pull`, `clone` or `remote` |
| `::test_it_refuses_the_real_home_under_pytest` | — |
| `test_hotreload.py` (the module list), a boundary test | `homegit` imports nothing from the package; `library` does not import it |

The suite is green on `plan-19-integration` and `ruff` is clean before
the plan merges into `finish-line`.

### At the machine

Group O, §8. It starts with a copy of the home and runs on the copy.

## 6. Forks

Each was settled by taking the option that is cheapest to reverse and
adds the fewest things to learn. None of the options writes or deletes a
file of the owner's without a copy first; where an option would, it is
not listed.

**1. Do slots 9–24 get their own load and save triggers?**

| Option | For | Against |
|---|---|---|
| **(a) No: `preset.select` and the page's direct calls** | No params added (the constraint). The pads need none | A learned button or a performer cannot fire "load slot 17" by id |
| (b) Yes: `preset.load.8…23`, `preset.save.8…23` | One spelling for all 24 | 32 params, 32 more lines in every target combo, for a road nobody asked for |

Taken: (a). To reverse: change the loop's bound in `build_registry`.

**2. The show file with more than eight slots: same schema or a new one?**

| Option | For | Against |
|---|---|---|
| **(a) `hyperspace.project/2`, the bank as long as it needs to be** | An older build still opens the show and plays slots 1–8. A show that never uses a far slot is unchanged on disk | An older build drops the far slots' pointers when it next writes that show |
| (b) `hyperspace.project/3` | An older build cannot damage the far slots | An older build refuses the owner's show outright and opens the factory party instead — at a party, the worse failure. Needs a migration step and a backup on first open |

Taken: (a), with `.bak-v2-bank8` before the first long write. To reverse:
nothing on disk needs undoing.

**3. What is on slots 9–24 of the factory shows?**

| Option | For | Against |
|---|---|---|
| (a) Empty | Sixteen places for save-as | TRACER, a party preset, stays off the desk |
| **(b) `party`: TRACER on 9; `house`: empty** | The one party preset with no key gets a pad; fifteen empty | — |
| (c) Every unslotted preset (`hands-*`, `legacy6`, `lfo-breathe`, `hands-orbit`) on row 4 | Everything reachable from the desk | Puts the demos the owner is likely to cull on the desk, and leaves nine places for save-as |

Taken: (b). Only a fresh home sees it; a show the owner has is never
rewritten for it. To reverse: one line of a data file.

**4. A preset's old shape pads at load: a note, or quiet?**

| Option | For | Against |
|---|---|---|
| (a) A note per row, as any row on an invariant control | The rule as written | Sixteen notes on every load of every preset the owner has; the warning line says "(+15 more)" all night and hides a real one |
| (b) One summary note per load | Honest | Still a warning on every load, about nothing the owner did |
| **(c) The sixteen exact old factory rows go quietly; anything else on those pads is noted** | A warning means something the owner mapped was dropped | The file and the live desk differ by rows nobody chose, silently, until the next save |

Taken: (c). To reverse: empty `RETIRED_DESK_ROWS`.

**5. The bank's lights.**

| Option | For | Against |
|---|---|---|
| (a) As today: the loaded pad green, all others dark | Nothing to build | Twenty-three dark pads; an empty slot and a full one look the same |
| **(b) Green loaded, amber filled, dark empty** | The desk shows where the presets are | One field on `Param`, one branch in `feedback`; amber on the mk1 is unseen (O2) |
| (c) Green loaded, green-dim filled | — | The mk1's clip LEDs have no dim level |

Taken: (b). To reverse: `filled_of` returns `None`.

**6. Twenty-four slots on the PRESETS page.** The table in §2 WP1.

| Option | For | Against |
|---|---|---|
| **(B) F1–F8 as today, 9–24 four a row** | Names readable on all 24; the first eight unchanged | A desk row of eight is two page rows; 12 px spare with "more" open |
| (A) F1–F8 as today, 9–24 eight a row | Mirrors the desk; 58 px spare | A far slot reads as a number and one letter; the name is in the hover only |
| A paged bank (1–8 / 9–16 / 17–24) | Smallest | Two thirds of the bank hidden at any time; a tab is a new control |

Taken: (B). If the 12 px prove too thin at the machine, (A) is a change
of two constants.

**7. Echo mix and effect mix on the scene presets' knobs.** The session
reached for them everywhere; on a preset with the look-back and the
effects off they would be dead knobs.

| Option | For | Against |
|---|---|---|
| **(a) Only where the stack is on** (the table in WP3) | No factory preset's look or cost changes; every mapped knob works | TUMBLE, FACES, FIELD and the house moods have no echo knob |
| (b) Make the scene presets "echo-ready": the look-back on with TRACER's set at an echo mix of 0, D5 echo mix, D6 fade | The same two knobs on every preset | `Lookback._capture` feeds the dream worker whenever the look-back is on, whatever the mixes: every party preset would pay for a dream nobody sees. Whether the frame at echo mix 0 equals the frame with the look-back off is unproved. It edits `*_values`, plan 20's seam, while plan 20 is re-cutting the look-back |

Taken: (a). (b) becomes a data change once `lookback.py` idles the worker
at a dream mix of 0 — plan 20's file. To reverse either: regenerate.

**8. Renaming a factory preset.**

| Option | For | Against |
|---|---|---|
| **(a) Refused, with the way to do it ("save copy, then rename the copy")** | One meaning for rename: your file moves | Two steps |
| (b) Makes your copy under the new name and hides the factory one | One step | Rename then does three things (copy, hide, repoint) and "unhide" brings back a second preset the owner thought was renamed |

Taken: (a).

**9. Where the trash and "show hidden" live.**

| Option | For | Against |
|---|---|---|
| **(a) At the foot of the preset list** | Where × is; no page height | One level down: the list, then the trash |
| (b) A line under "more" on PRESETS | Always one click from the page | 29 px: with layout (B) and the fold open the page scrolls by 17 px (*measured*) |
| (c) A TRASH page | Room | A fifteenth page |

Taken: (a).

**10. Does emptying the trash, or a hide, need more than this?** No
option that deletes without asking, and no modal, was considered. The
in-place "click again" is the smallest thing that cannot be done by one
stray click and never stops the frame.

**11. Is the trash in git?**

| Option | For | Against |
|---|---|---|
| **(a) Ignored** | Every trashed file was committed at its last save; no double history | A file trashed before git was switched on is only in the trash |
| (b) Tracked | "Empty" becomes recoverable from history | Every overwrite is stored twice; the history fills with copies |

Taken: (a). The first commit is made when the key is switched on and
holds every live file as it then is.

**12. `Bindings.load` writing after a backup that failed** (§1 row 15).
Not a choice: this plan's rule forbids a rewrite with no copy, and its
remap is the next change through that branch. It is changed for every
remap, not only this plan's.

## 7. As built

Built 2026-10-04 by the unattended run onto `plan-19-integration`, in
the merge order of §2: WP1, WP2, WP3, WP5, WP4, WP6, then these
documents (WP7). Every fork in §6 was settled as recommended — by the
run's orchestrator, not the owner — and waits in
[`DECISION-REGISTER.md`](../DECISION-REGISTER.md) rows 72–78. Hand
checks: [`11-hand-checks.md`](11-hand-checks.md) group O, checks 81–90
(§8's O1–O10, made true to the code as built). Demos are under
`docs/plans/assets/19-presets-and-the-desk/`. **Nothing of this plan
has been on the APC40 or in front of a person**: amber at velocity 5,
the pads of rows 4–5, the knobs' new choices and every popup (the list,
rename, the trash) are unseen. The build was handed between agents
mid-way at the owner's instruction: WP2 was finished by a second agent
from a pushed work-in-progress commit (`74e9db0`, four tests failing),
which is where the lost launch notes below were found.

On `plan-19-integration` with plans 15–18 and 20 merged in (4647741),
`uv run pytest -q`: **1442 passed, 1 skipped** (the hands tape);
`uv run ruff check .` clean.

### WP1 — a bank of twenty-four (PR #104, merge 94566bd)

Built as §2 WP1 says, layout B on the page, TRACER on the factory
party show's slot 9, no params added (`preset.select` 24 choices with
`has`, the sixteen F-key triggers unchanged, the `preset` group still 21
params). Where it differs:

- **`F_KEYS` is declared once, in `params.py`**; `library.F_KEYS` and
  `routing.F_KEYS` are that name imported (both already import
  `params`, which needs the number for the trigger loop and may not
  import `library`). `routing.BANK_SLOTS` is gone. A test pins
  `routing.F_KEYS == library.F_KEYS == params.F_KEYS == 8 < SLOTS`.
- **A schema-1 bank is read as eight**: `preset.migrate_project` and
  `library.migrate` (the old `presets.json` bank) take `[:F_KEYS]`, then
  write through `bank_doc`. Read as `[:SLOTS]`, a full schema-1 bank's
  "own look" would have landed on slot 9 instead of "no slot", changing
  what the migration writes into the owner's show.
  `preset._into_default` shifts the bank within the length the file
  has: an eight-entry file behaves exactly as before.
- **`Project.write`** decides on the file at its path: it parses, is not
  schema 1, holds at most eight entries, and the document holds more →
  `routing.backup(path, "2-bank8")` first (`library.BANK8_BACKUP`), and
  `LibraryError` when that returns `None`. `library._kept` skips the
  copy when a `.bak-v2-bank8*` beside the file already holds the same
  bytes (a write retried after its backup); a bank that shrinks to eight
  and grows again with other content is copied again under a stamped
  name — more kept, never less.
- **`save_slot` puts the slot back when the show's write fails** (it
  used to leave it changed in memory), then `follow()` re-aims the
  light; `Project.save` puts name, path, session and modules back and
  re-raises. The footer says why through `Project._refused`.
- **`Project.follow()`** is the one spelling of "the lit slot follows
  the loaded preset", called from `_set_slot`, `_apply`, `Marks.put` and
  `Presets._landed`; `load_slot` still sets `active = k`, so a preset on
  two slots lights the pad pressed.
- An empty far slot says "slot 12: an empty slot" (no "⇧F… saves" tail).
  A far slot has no learn outline on the page.
- **The page's fit, measured** at `CONTROL_SIZE` with "more" open and 24
  slots: 35 px spare with nothing under the fold, **12 px with the
  status line** (there after any load), and **a one-line warning on top
  of the status line scrolls the page by 11 px** while the fold is open
  (pressing an empty far slot is one way to get one); a two-line warning
  with no status scrolls it by 4 px. Folded, about 315 px spare. The
  fit test draws the fold open, all 24 filled and a status line.
- **Not fixed, from the review**: `preset.select` now has 24 choices,
  most of them empty on a fresh show, so **a learned step or toggle row,
  or a knob learned onto it, lands on empty slots** — a step stops on
  one ("slot 13: an empty slot") instead of wrapping, and an `abs` knob
  spreads over all 24. No factory row does this (the pads are `set k`;
  QUANT and pad B walk filled slots through `Project.cycle`). Filed as
  audit R14.

Tests: `test_library.py::test_the_bank_is_twenty_four_and_the_f_keys_eight`,
`::test_a_bank_is_written_as_far_as_its_last_filled_slot`,
`::test_the_owner_home_is_shaped_like_the_owners`,
`::test_an_eight_slot_show_loads_and_is_not_rewritten`,
`::test_loading_never_rewrites_a_preset_file`,
`::test_a_show_that_uses_only_the_first_eight_is_written_with_eight`,
`::test_the_first_write_past_slot_eight_keeps_the_eight_slot_file`,
`::test_save_as_lands_on_slot_nine_once_the_f_keys_are_full`,
`::test_a_long_bank_read_by_eight_slots_shows_the_first_eight`,
`::test_next_empty_reads_the_banks_own_length` (rewritten: the party
show's first empty slot is 10);
`test_presets.py::test_save_new_lands_past_the_f_keys_and_a_full_bank_says_so`,
`::test_active_follows_the_loaded_preset_from_one_place`;
`test_params.py::test_the_bank_adds_no_params`;
`test_ui_presets.py::test_twenty_four_slots_fit_the_page_with_more_open`,
`::test_a_far_slot_reads_its_number_and_name_and_has_the_slot_menu`;
`test_party_show.py::test_the_party_show_has_tracer_on_slot_nine_and_room_after`;
`test_migration.py::test_the_migrations_still_write_an_eight_slot_bank`.
The `owner_home` fixture (`tests/conftest.py`: `build_owner_home`,
`boot_home`, `tree`) is what every "on a copy" test of this plan runs
on. Demos: `bank-24.png`, `bank-24-more.png` (hidden-window renders),
`bank-24.txt` (`tools/bank_demo.py`). Not verified: the far slots' names
from a step back; an older build actually run against a long bank (the
downgrade test replays its three lines of `_take`).

### WP2 — rows 4–5 are the bank (PR #110, merge 0b4e407)

Clip rows 4 and 5 load slots 9–24, invariant on both layers
(`apc40.BANK_PADS`, 24 `(note, channel)` pairs; `DEFAULT_MAP` has 24
`preset.select` rows where the row-1 line and the two `view.shape` lines
were). A bank pad is **green loaded (velocity 1), amber filled
(velocity 5, `apc40.filled_of`), dark empty (0)**, from one rule,
`routing.led_level` (2 / 1 / 0, reading `Param.has`); `MidiIO.feedback`
sends `filled_of(…)` at level 1 and a blink still wins. On the
on-screen desk a filled pad is amber at **half strength**
(`ui_desk.FILLED = 0.5`) with its preset's name in the bright ink, and
an empty bank pad is a dark control with its glyph only (`text` is ""
for it; the hover says "slot N: empty"). A fresh desk is 26 rows, down
from 42; `bindings.default.json` and the 18 factory presets with a
`desk` key were regenerated. Where it differs from §2:

- **`remap_factory` adds an APC40 row only where no MIDI row overlaps
  the control** (`Binding.overlaps`), not where nothing uses the source
  string: an any-channel row the owner wrote by hand (`note:*:57`)
  holds every track's pad. This applies to every `APC_NEW_ROWS` entry,
  plan 09's and 15's included — only more conservative; a file already
  migrated has those rows. The sixteen plan-19 swaps (`BANK_REMAP`,
  merged into `APC_REMAP`) clear the row's `layer` and take the factory
  light. `RETIRED_DESK_ROWS = frozenset(BANK_REMAP)`.
- **No backup, no rewrite** (fork 12) is in `Bindings.load` *and*
  `Bindings.write`: when the copy fails the load sets
  `Bindings.unbacked` and `error = NOT_REWRITTEN` ("bindings: not
  rewritten — no backup could be made") and writes nothing; any later
  `write()` in the session tries the copy first and writes nothing
  without it (a Learn on a session row would otherwise have rewritten
  the file with no copy).
- **`Bindings.said` — a launch's notes were being lost.** The startup
  preset's load is an edit (`Bindings.set_routes` sets `notes = []`), so
  `remap_factory`'s per-row notes were gone before the first frame —
  true before this plan too: no launch's remap ever reached the ROUTING
  head; only stderr kept them. `Bindings.said` now holds one line for
  the session — "bindings.json updated (16 rows changed), the old file
  kept as bindings.json.bak-v3 — each change is on stderr", or "…NOT
  rewritten (16 rows changed): no backup could be made — in memory
  only, the next launch tries again" — and `app.main` adds it to the
  SYSTEM page's notes (`panel.config_notes`). A later `write()` that
  finally makes the backup updates the line. stderr still has every row.
- **`preset.migrate_home` backs up before it announces** (the review):
  with the copy refused it had claimed the file was migrated, and had
  not set `unbacked`. It now announces what happened and sets
  `unbacked` / `NOT_REWRITTEN`
  (`test_migration.py::test_bindings_json_whose_backup_fails_after_its_part_moved_is_never_rewritten`).
- `ui_desk.text` was there as plan 17 built it. A narrow edge is left
  as the plan has it: in a schema-3 file from between plan 13's WP3 and
  WP5, a re-aimed pad with `"layer": "preset"` keeps its pad through the
  migration, gets a bank row on the next launch, and is then dropped
  from the migrated preset with the note.

Tests: `test_desk.py::test_rows_four_and_five_load_slots_nine_to_twenty_four_on_both_layers`,
`::test_the_bank_pads_are_invariant`;
`test_midi.py::test_a_bank_pad_is_green_loaded_amber_filled_and_dark_empty`,
`::test_save_as_blinks_the_new_pad_on_row_four`;
`test_routing.py::test_an_older_file_gets_the_bank_pads_with_a_backup`,
`::test_the_old_shape_pads_are_swapped_and_a_changed_row_is_left_alone`,
`::test_a_remap_whose_backup_fails_writes_nothing`,
`::test_a_second_launch_writes_nothing_and_says_nothing`,
`::test_a_row_the_owner_put_on_a_bank_pad_is_left_alone`,
`::test_a_launch_whose_backup_fails_then_succeeds_rewrites_once`;
`test_presets.py::test_an_old_preset_loads_without_its_shape_pads_and_its_file_is_untouched`,
`::test_the_next_save_of_an_old_preset_writes_the_desk_without_the_pads`,
`::test_every_factory_presets_desk_is_the_generators`;
`test_ui_desk.py::test_a_filled_pad_is_amber_and_an_empty_one_has_no_label`.
Demos: `desk-bank.png`, `desk-bank-shift.png` (hidden-window renders of
the big desk: the bank pads identical under SHIFT, and the half-strength
amber apart from a selected scene's full yellow); `bank-pads.txt` (the
first launch's sixteen "added" lines, `said` and the backup; a second
launch saying nothing; an old preset loading quietly and a re-aimed pad
dropped with its note; the velocities 1 / 5 / 0; a far pad loading on
both layers; a clip-stop hold landing in slot 10). The PR's scripted
launch of the real app on an owner-like temp home: `bindings.json` 147
→ 163 rows, the owner's changed row intact, every other file
byte-identical but `windows.json`; the second launch said nothing. Not
verified: amber on the mk1 beside green; the SYSTEM line as drawn.

### WP3 — the factory preset layer re-cut (PR #115, merge 174cc60)

As §2 WP3's table, exactly: `apc40.SCENE = ("view.depth4",
"camera.yaw", "camera.pitch", "view.pattern")` on D1–D4 of the fresh
preset layer, so **fourteen presets** (the eight house moods, TUMBLE,
FACES, FIELD, `legacy6`, `hands-play`, `hands-orbit`) have 4D depth ·
Yaw · Pitch · Pattern and D5–D8 dark; `hands-fx`, `hands-pinch` and
`lfo-breathe` have their own (`HANDS_FX_KNOBS`, `HANDS_PINCH_KNOBS`,
`BREATHE_KNOBS`; `hands-fx` and `hands-pinch` gained a `desk` key); **the
six eight-knob presets (WAKE, TRACER, TRIP, ACID, MANDALA, NOITA) are
byte-identical**. `preset.knob_desk` replaces the fresh layer's device
knobs (`_is_device_knob`) instead of adding to them. 14 of the 23 files
changed; `bindings.default.json` did not (the preset layer is not in
it). **D4 passed its gate**:
`test_midi.py::test_a_knob_on_the_pattern_steps_through_every_pattern`
turns D4 0 → 127 → 0 with smoothing on and visits all twelve patterns
in order both ways, the ring following, so D4 carries `view.pattern`.
Where it differs: `test_plan12_presets.py::test_wake_and_trip_device_knobs_move_their_bases`
could not stay unchanged (TUMBLE's D1 is now 4D depth, TRACER's D8
target too): its "does nothing on another preset" check leaves that one
param out and asserts D1 moved depth on TUMBLE. **`view.pattern` shows
only where faces are drawn**: on a preset with faces off D4 changes the
state and nothing on screen. A user preset saved before plan 19 keeps
its own desk (dark knobs stay dark); only a user file with no `desk`
key gains `SCENE`. Tests: `test_plan12_presets.py::test_no_factory_knob_is_dead`,
`test_presets.py::test_a_users_desk_is_untouched_by_the_recut`,
`::test_every_factory_presets_desk_is_the_generators` (extended: the
fresh desk 30 rows, the D1–D8 table preset by preset, one row per
control, none on an invariant control). Demos: `factory-desks.md`
(before and after, generated), `desk-knobs.png` (TUMBLE on the big
desk). The review found nothing. Not verified: how the four knobs feel,
and a Pattern knob that steps every ~11 CC values on the mk1's endless
encoders.

### WP5 — the dirty dot and the save label (PR #114, merge 338ceba)

`ui.dirty_dot(tip)` — a filled red disc, `ui.DOT_R = 6` (12 px), in a
cell one text line tall — on every strip (the preset strip and each
module strip under "more") and ROUTING's head, where the "●" glyph was;
the rail's disc `ui.RAIL_DOT_R = 5`; **the save chip lit** (`ui.lit_chip`,
solid red) while the group is dirty (`ui_presets.save_chip`, shared by
the strip and the head); **a white disc of radius 4 on the loaded bank
slot** while its preset is dirty (`SLOT_DOT_R`); **"save copy"** on a
factory preset (`ui_presets.save_label`, hover `save_tip`) on the
preset strip and ROUTING's head only — module strips keep "save"; **the
preset strip's `reset` is removed**: `Library.reset` on a document kind
loads a preset called "default", none ships, so it did nothing there.
The show's own dot is unchanged. **Not fixed, measured**: on a module
strip under "more" (258 px from `ui.LABEL_W`), ◀ name ▶ takes 178 px
(192 with the disc) and save · as… · reset 163 px, so **the save chip
sits over the right end of the name button** (name 676–808 px, save
771–821 px), with or without a disc. It was already so before this
plan; fixing it needs a layout decision (fewer chips there, or a
narrower name) — audit U10. Tests:
`test_ui_presets.py::test_the_dot_is_a_twelve_pixel_disc_and_save_is_lit_while_dirty`,
`::test_save_reads_save_copy_on_a_factory_preset`,
`::test_the_preset_strip_has_no_reset_and_does_not_overlap`,
`test_ui_routing.py::test_the_head_has_the_same_dot_and_label`. Demo:
`dirty-dot.png` (`tools/dot_demo.py`, hidden-window renders). Not
verified: whether the disc and the lit chip read at arm's length on the
control screen; the app was not launched for this package.

### WP4 — hide, rename and the trash (PR #117, merge a1efb4b)

From the preset list (the strip's name): **×** on every preset — yours
to the trash (`Library.delete`, unchanged), a factory one hidden
(`Library.hide`: its file stem in `<home>/hidden.json`,
`{"schema": "hyperspace.hidden/1", "presets": […]}`); **rename** on
yours (the row becomes the strip's inline name field, key
`rename:<name>`); at the foot **"show hidden (n)"** while something is
hidden (the hidden rows then struck through and dimmer, each with
**unhide**) and **"trash (n) ▸"** while the trash holds something,
which opens the trash popup — group, name, time and **restore** per
row, newest first, then **"empty trash…"**. Both lists show **twelve
rows** (`LIST_ROWS`) and then scroll in their own child; a list row is
a chip's height, **29 px** at the control size. **Empty asks once, in
place**: the chip becomes "delete N files for good? — click again" in
the warning ink for 4 s (`EMPTY_S`); the time running out, any other
click or closing the popup disarms it; no modal. A bank slot whose
preset has no file is drawn in **the warning ink** with the hover
"F6: TRIP 3 — no such preset. It may be in the trash (preset list →
trash). Right-click → clear slot" (checked on the list's poll, never per
frame); its pad stays amber. × on yours says what still names it: "TRIP
3 is in the trash — F6 and 'starts on' still name it; restore it from
the trash, or clear the slot". The page gained no line. Where it
differs or settled what §2 left open:

- **Rename's order and nets**: the new file written exclusively, then
  the old one copied to the trash (a failed copy removes the new file
  and changes nothing), then removed; then every `hyperspace.project/2`
  show in `<home>/projects` that names it, each copied to
  `trash/projects/` first (the open one through its `Project`); a show
  whose copy or write fails, or a schema-1 show, is left and named; the
  loaded preset keeps its clean reference under the new name. **A
  rename that only changes case or spacing** keeps the stem and
  rewrites the file in place, after a trash copy (a failed copy
  refuses it).
- **Rename's "taken"** is `_taken` less the renamed file's own stem and
  names — it **does not include the open bank's names** (save-as's set
  does): renaming to a name a dangling slot holds makes that slot load
  again.
- **Restore counts factory stems as taken** (a file of that stem in the
  group's folder of either root), so a restored file never shadows a
  factory file it did not shadow before; restore never writes over a
  file and removes the trash copy only after the write.
- **The trash lists only files named as `to_trash` writes them**
  (`<stem>.<YYYYMMDD-HHMMSS>[-n]<suffix>`, never a dotfile): a Finder
  `.DS_Store` is not listed, restored or emptied (review fix, 69e5427).
  `empty_trash` refuses a symlink and any path that does not resolve one
  folder under `<home>/trash/`.
- A restore clears the warning × left about that preset. Deleting your
  copy of a factory preset that is hidden says it is hidden (review fix).
- The popups' background is slightly translucent (the panel's existing
  style): page text shows faintly behind them in the renders.

Tests: `test_library.py::test_hiding_a_factory_preset_takes_it_off_the_list_and_nothing_else`,
`::test_a_user_file_that_shadows_a_hidden_factory_preset_shows_as_itself`,
`::test_a_made_up_name_never_collides_with_a_hidden_preset`,
`::test_an_unreadable_hidden_list_is_kept_before_it_is_replaced`,
`::test_rename_updates_every_show_and_keeps_each_old_file`,
`::test_rename_refuses_a_taken_name_and_a_factory_preset`,
`::test_a_rename_that_cannot_keep_the_old_file_changes_nothing`,
`::test_renaming_the_loaded_preset_keeps_its_unsaved_edit`,
`::test_a_deleted_preset_says_which_slots_still_name_it`,
`::test_the_watcher_never_resurrects_or_reloads`,
`::test_restore_never_overwrites`, `::test_empty_trash_removes_only_the_trash`,
`::test_the_trash_lists_only_what_it_kept`,
`::test_deleting_your_copy_of_a_hidden_factory_preset_says_it_is_hidden`;
`test_presets.py::test_rename_and_trash_are_no_undo_step`;
`test_ui_presets.py::test_the_list_has_a_cross_on_every_preset_and_rename_on_yours`,
`::test_empty_asks_once_and_disarms`, `::test_a_slot_whose_preset_is_gone_says_so`
(real imgui mouse events, the nested trash popup included). Demos:
`files-demo.txt` (`tools/trash_demo.py`: what changed on disk at each
step), `preset-list.png`, `trash.png`, `bank-dangling.png` (hidden-window
renders); `tools/trash_launch.py` drove hide, rename, delete and restore
through a running app's library (120 frames, no error). Not verified:
any popup clicked by a person.

### WP6 — the home in git (PR #119, merge 7190ff2)

`homegit.py`, a leaf that imports nothing from the package, behind
`[library] git` (`config.DEFAULTS["library"] = {"git": False}`; a value
that is not a boolean is `False` with a note). **Off by default**: with
the key off `homegit` is never imported, no thread starts and nothing is
written. `app._open_homegit` builds a `Committer` only for `git = true`
and **attaches it after the startup preset** (after `migrate_home` too),
so a launch's own writes ask for no commit and ride in the first
save's; `Host.committer` is last in `Host.adapters` and `close` waits up
to 2 s on quit and ⌘R. The library calls `_commit(message)` — which
never raises and never waits — at the end of `save_as` ("save preset
TRIP 2", "save fx acid"), `delete` ("trash preset TRIP 3") and
`Project.write`, whose words are what moved since the show was opened or
last written: "show mine: starts on TUMBLE", else "show mine: bank",
else "save show mine". `Library.poll` drains `committer.notes()` onto the
warning line every call, before its period gate. The worker: **`git
init` at the first request, never at launch**; a home whose repository's
top level is somewhere above it (a dotfiles repository) is **never
initialised or committed** — one note, `refused` for the run; an
existing repository at the home is used as it is, its `.gitignore` and
branch kept (ours written only where there is none). A commit is `add
-A` then **the waiting messages taken after `add -A`** (the first its
subject, the rest its body; nothing staged, no commit) — a first version
took them before, and in the scripted launch two saves landing during
the first commit's 0.3 s lost their words. Every command: `-c
core.hooksPath=/dev/null -c commit.gpgsign=false`,
`GIT_TERMINAL_PROMPT=0`, `LC_ALL=C`, the `GIT_DIR`-style variables
removed, a 10 s timeout and then **SIGTERM, then SIGKILL 2 s later**
(the review: a SIGKILLed `git add` left `.git/index.lock` and every
later commit failed; 3d87f44). A failure is said once — "git: not
committed (<reason>); saves are not affected" — until a commit
succeeds; the words waiting at a failure are dropped and the files ride
in the next commit. Identity `Hyperspace <hyperspace@localhost>` only
for whichever of name and email the machine lacks. The SYSTEM page's
home line reads "library: <home> · git". `"homegit"` is in
`hotreload.MODULES` beside `placement`. The module names no network
command.

**The seam at the merge (the orchestrator, 7190ff2)**: WP4's calls were
not on WP6's branch, so the merge added them — `rename` asks "rename
preset TRIP 3 → SUNRISE" **before** its shows are rewritten, so it is
the commit's subject and the open show's "show mine: bank" its body;
`hide` / `unhide` ask "hide preset X" / "unhide preset X"; `restore_trash`
asks "restore presets X" (the group's folder name); **`empty_trash`
asks nothing** (the trash is ignored).
`test_library.py::test_hide_rename_and_restore_each_ask_for_a_commit`.

Tests: `tests/test_homegit.py` (20; 14 need `git` and all 14 ran on
Apple Git 2.50.1), `test_library.py::test_each_save_asks_for_one_commit_in_the_librarys_words`,
`::test_a_committer_that_raises_never_stops_a_save_and_notes_reach_the_warning_line`,
`test_config.py::test_library_git_is_off_by_default_and_a_switch`,
`test_app_boundary.py::test_homegit_is_a_leaf_and_the_library_never_imports_it`,
`::test_the_homegit_gate`, `test_hotreload.py::test_homegit_is_watched_among_the_leaves`.
Demo: `homegit-demo.txt` (`tools/homegit_demo.py`: off, the first save,
a commit per save, git missing, a locked index, a home inside another
repository, timing — `request()` 10 µs median, a commit 71 ms median).
The PR's scripted launches on an owner-like temp home: no frame raised,
first commit 321 ms after the first save, a clean status. Not verified:
the " · git" line on screen, a ⌘R with a commit in flight, a remote the
owner adds, a home on a network drive, any OS or git but this laptop's.

### What the orchestrator saw (first-hand, apart from the agents' reports)

- **The owner's seventeen real presets from the night** — the files
  under `shared/dan-2026-10-04/presets/` (PR #113, installed with
  `tools/shared_presets.py install`) — were installed into a fresh temp
  home and loaded one by one through the app's loader on this branch:
  **all load, their routes intact, with no load note at all**. The
  sixteen retired shape pads they carry dropped quietly (fork 4).
- **A scripted launch of the real app** against a temp home: with F8
  cleared, a save-as filled F8 and **the next save-as landed in slot 10**
  of the twenty-four (TRACER holds slot 9); no runtime error and an
  empty stall log.
- The suite on this branch with plans 15–18 and 20: 1442 passed,
  1 skipped; ruff clean.

### The owner's files, as built

Every file in the home this plan's code can rewrite, move or delete,
and its net. "Proved" names the test that runs it on a copy
(`owner_home`).

| File | What happens, and when | Copied first | Proved |
|---|---|---|---|
| `projects/<show>.hyp.json` | **Never rewritten by a load**: an eight-name bank is padded to 24 in memory and the show is clean. Written only by a bank change, "starts on", save, and rename (below); a show using only slots 1–8 is written with eight entries | before the first write that makes the file's bank longer than eight: `routing.backup(path, "2-bank8")` → `<file>.bak-v2-bank8` (a stamped name when that exists; skipped when one already holds the same bytes). **No backup, no write**: `LibraryError`, the slot put back, the footer says why | `test_library.py::test_an_eight_slot_show_loads_and_is_not_rewritten`, `::test_the_first_write_past_slot_eight_keeps_the_eight_slot_file` |
| `projects/<show>.hyp.json`, every user show | a rename repoints its `bank` and `startup` (schema 2 only; a schema-1 show is left and named; factory shows never written) | `to_trash` → `trash/projects/<show>.hyp.<stamp>.json`; a show whose copy fails is left as it is, and named | `test_library.py::test_rename_updates_every_show_and_keeps_each_old_file` |
| `bindings.json` | once: sixteen invariant rows added where no MIDI row overlaps the pad; in a file from before plan 13's migration the sixteen old shape rows swapped. Every launch's notes on stderr; the sum on the SYSTEM page (`Bindings.said`) | `routing.backup(path, read_at)` → `bindings.json.bak-v3` (a stamped name when that exists). **No backup, no rewrite**, in `Bindings.load`, `Bindings.write` and `preset.migrate_home` | `test_routing.py::test_an_older_file_gets_the_bank_pads_with_a_backup`, `::test_a_remap_whose_backup_fails_writes_nothing`, `::test_a_launch_whose_backup_fails_then_succeeds_rewrites_once`, `test_migration.py::test_bindings_json_whose_backup_fails_after_its_part_moved_is_never_rewritten` |
| `presets/<name>.json` (yours) | **never rewritten by a load**: the sixteen old pads dropped in memory, quietly; the file keeps them until you save it | the save's `to_trash` (plan 15, unchanged) | `test_presets.py::test_an_old_preset_loads_without_its_shape_pads_and_its_file_is_untouched`, `::test_the_next_save_of_an_old_preset_writes_the_desk_without_the_pads` |
| the same | ×: copied, then removed (plan 15). Rename: the new file written exclusively, the old one copied to the trash, then removed; a case- or spacing-only rename rewrites the file in place after its copy | `to_trash`; a failed copy refuses the delete, undoes the rename (removes the new file), or refuses the in-place rename | `test_library.py::test_a_rename_that_cannot_keep_the_old_file_changes_nothing`, `::test_rename_refuses_a_taken_name_and_a_factory_preset` |
| `<group>/<stem>.json`, `projects/<stem>.hyp.json` | restore from the trash: created exclusively, under the next free name when the stem (factory stems included) or the preset's name is taken; the trash copy removed only after | — (never over a file) | `test_library.py::test_restore_never_overwrites` |
| `trash/**` | **empty deletes for good** — the one place in the app that keeps no copy; only the files `trash()` lists (named as `to_trash` writes them), then the folders left empty; a symlink or a path outside `trash/` is refused | nothing: asked twice, in place | `test_library.py::test_empty_trash_removes_only_the_trash`, `::test_the_trash_lists_only_what_it_kept` |
| `hidden.json` (new) | written by × on a factory preset and by unhide | an unreadable one is kept as `hidden.json.bak-v0` (`routing.backup(path, "0")`) before the first rewrite; no backup, no rewrite | `test_library.py::test_an_unreadable_hidden_list_is_kept_before_it_is_replaced` |
| `.git/`, `.gitignore` (new, opt-in) | with `[library] git = true`: at the first save after launch, never at launch; `.gitignore` only when there is none; never when the home is inside another repository | — (no file of the owner's is rewritten) | `test_homegit.py::test_the_first_save_inits_ignores_and_commits`, `::test_an_existing_repository_and_gitignore_are_kept`, `::test_a_home_inside_another_repository_is_never_committed`, `::test_it_rewrites_no_file_of_the_owners` |
| factory files (the repo's) | regenerated (`python -m hyperspace.preset`, `python -m hyperspace.routing`) | git | `test_presets.py::test_write_factory_regenerates_every_factory_file` |

A launch of this build on a home as the night left it does one thing to
the owner's files that this plan adds: `bindings.json` is rewritten
once, backed up first (`last_show` and `windows.json` are written as
always; plan 15's own first-launch rewrite of `bindings.json`, if it has
not happened yet, is the same rewrite and the same backup).

## 8. Appendix — group O for `11-hand-checks.md`

WP7 pastes this in after plan 18's group N, with final numbers in place
of O1–O10. The text is final except for numbers and PR numbers.

*As built:* the checks as they are run are
[`11-hand-checks.md`](11-hand-checks.md) group O, checks 81–90 (O1 →
81 … O10 → 90), made true to the code: the first launch's sixteen
"added" lines and the SYSTEM page's one line (O4), save-as landing
"→ slot 10" on the factory party show, a TUMBLE of your own keeping its
dark knobs (O5), the trash's two-click empty and its 4 s (O8), and the
locked index's catch-up commit carrying both files under the later
save's words (O10). Where this appendix and that file differ, that file
is right.

### O. Plan 19 — twenty-four presets, the knobs, the list, the trash, git — added 2026-10-04

**Copy `~/Hyperspace` first, and run on the copy.** This is the plan that
renames, hides and trashes files in that folder.

```
cp -R ~/Hyperspace ~/Hyperspace-before-19          # the one to keep
cp -R ~/Hyperspace ~/Hyperspace-try-19             # the one to play on
export HYPERSPACE_HOME=~/Hyperspace-try-19
```

Every check below runs with that variable set. Only when O1–O10 pass,
unset it and launch on the real home; `~/Hyperspace-before-19` stays
until a party has been played. O1, O6–O10 run on the laptop alone;
O2–O5 need the APC40. About 40 minutes. Run the headless tests named
first.

**O1. An eight-slot show opens untouched, and the page holds twenty-four
(WP1).**
Headless: `uv run pytest -q tests/test_library.py::test_an_eight_slot_show_loads_and_is_not_rewritten tests/test_ui_presets.py::test_twenty_four_slots_fit_the_page_with_more_open`.
Before launching: `ls -l $HYPERSPACE_HOME/projects/`. Launch, open your
show (PRESETS → show ▾), press F1–F8, quit. `ls -l` again. *Pass:* every
show file has the same size and time as before; your eight presets are on
F1–F8; under them are sixteen smaller buttons, 9–24, all "—"; the page
has no scrollbar, with "more" open as well. Right-click 12 → put preset
here… → one of yours. *Pass:* the button reads "12" and the name; in
`projects/` there is now `<show>.hyp.json.bak-v2-bank8`. *Fail:* a show
file changed by opening it → `Project._take` / `write`; a scrollbar →
`ui_presets.preset_bank` (`FAR_COLS`, `FAR_GAP`); no backup →
`Project.write`.

**O2. Rows 4 and 5 are presets, on both layers (WP2).**
Headless: `uv run pytest -q tests/test_desk.py::test_rows_four_and_five_load_slots_nine_to_twenty_four_on_both_layers tests/test_midi.py::test_a_bank_pad_is_green_loaded_amber_filled_and_dark_empty`.
APC40 in. With a preset on slot 12 (O1): look at the grid. *Pass:* row 1
shows one green pad (the loaded preset) and amber on the other filled
slots; row 4's fourth pad is amber; empty slots are dark. Press it: it
turns green, the old one amber, the picture changes. Latch SHIFT: the
same pads, the same lights; press another: it loads and SHIFT drops.
Turn the cue knob: the shape changes through all of them. *Fail:* amber
that cannot be told from green, or no amber → `apc40.filled_of` (the
velocity) — say what you see, the fallback is green-or-dark; a pad that
changes the shape → an old row in `bindings.json` (O4); nothing under
SHIFT → the rows have a layer.

**O3. A preset you saved before loads without a fuss, and save-as lands
on row 4 (WP2).**
Headless: `uv run pytest -q tests/test_presets.py::test_an_old_preset_loads_without_its_shape_pads_and_its_file_is_untouched tests/test_midi.py::test_save_as_blinks_the_new_pad_on_row_four`.
Load three presets saved on the night. *Pass:* no warning about dropped
rows, no dirty dot. (If you had learned something onto a row-4 or row-5
pad, there **is** a warning naming it: that mapping is gone from the
live desk and is still in the file until you save.) Now fill F1–F8 if
they are not, change something, and hold the clip-stop row. *Pass:* at
about 0.6 s the bar and the first empty pad on row 4 blink for a second
and a half; the footer says "saved … → slot 9" (or the next empty one).
*Fail:* a warning on every load → `routing.RETIRED_DESK_ROWS`; the blink
on row 1 only → `apc40.blink_of`.

**O4. The session's file was brought along, with a backup (WP2).**
`ls $HYPERSPACE_HOME/bindings.json*`. *Pass:* a `bindings.json.bak-v3`
(or one with a time on it) from this launch; `grep -c preset.select
$HYPERSPACE_HOME/bindings.json` says 24. If you had put a row of your own
on a row-4 or row-5 pad by editing the file, it is still there and that
pad does what you made it do. *Fail:* no backup and a changed file →
`Bindings.load`.

**O5. The knobs that were dark (WP3).**
Headless: `uv run pytest -q tests/test_plan12_presets.py::test_no_factory_knob_is_dead`.
F1 (TUMBLE): turn D1–D4. *Pass:* 4D depth, the camera's yaw, its pitch,
the face pattern; D5–D8 dark and dead. A house mood: the same four. TRIP,
WAKE, ACID: their eight, as before. `hands-fx` from the list: D1 the mix,
D2–D6 the Acid shader. `lfo-breathe`: D1 still Breathe. Then say which
knobs you reached for and found dark or useless: K7 (Bitmap alpha) does
nothing on a factory preset, and the scene presets have no echo knob
(§6 fork 7). *Fail:* a lit knob that moves nothing → that preset's row
in `preset.py`; one knob doing two things → `knob_desk`.

**O6. Cull the list (WP4).**
Headless: `uv run pytest -q tests/test_library.py::test_hiding_a_factory_preset_takes_it_off_the_list_and_nothing_else`.
PRESETS → click the preset's name → the list. × on `legacy6`, on the
`hands-*` you do not want, on a house mood. *Pass:* each goes; the foot
of the list reads "show hidden (n)". Click it: they are back, struck
through, with "unhide". F-keys and pads that named a hidden preset still
load it. × on one of **your** presets that is on a slot: *Pass:* it goes;
the footer says which slot still names it; that slot's button is in the
warning colour. *Fail:* a hidden preset that will not load from its slot
→ `Library.list(hidden=)` leaked into `path_of`.

**O7. Give "TRIP 3" a real name (WP4).**
Headless: `uv run pytest -q tests/test_library.py::test_rename_updates_every_show_and_keeps_each_old_file`.
Put a preset of yours on a slot in two different shows. In the list:
rename → type a name → Enter. *Pass:* the list, the slot and "starts on"
(if it was that one) show the new name at once; open the other show: its
slot has the new name too. `ls $HYPERSPACE_HOME/trash/presets
$HYPERSPACE_HOME/trash/projects`: the old preset file and each show as it
was. Rename to a name that exists: refused, nothing changes. Rename a
factory preset: there is no rename on it. *Fail:* a slot that says "no
preset" after a rename → step 5 of `Library.rename`.

**O8. The trash (WP4).**
Headless: `uv run pytest -q tests/test_library.py::test_restore_never_overwrites tests/test_library.py::test_empty_trash_removes_only_the_trash`.
The list → trash ▸. *Pass:* what O6 and O7 put there, newest first, each
with a time. Restore the preset from O6: it is in the list and its slot
works again. Save over a preset twice, then restore the older copy:
*Pass:* it comes back under the next free name and the footer says so;
the newer one is untouched. Click "empty trash…" once and wait: *Pass:*
it asks, then goes back to rest, and nothing was deleted. Click, then
click again: the trash is empty and the line is gone from the list.
*Fail:* a restore that replaced a preset → `restore_trash` (tell us at
once: `~/Hyperspace-before-19` has it).

**O9. The dot from a step back (WP5).**
Headless: `uv run pytest -q tests/test_ui_presets.py::test_the_dot_is_a_twelve_pixel_disc_and_save_is_lit_while_dirty`.
Load TUMBLE, stand at arm's length, move a fader. *Pass:* you can see
that it is unsaved without leaning in: the save chip is solid red, a red
disc sits by the name, the F1 button has a dot. The chip reads "save
copy"; press it: it reads "save", the dot goes, the list shows TUMBLE
once (yours). ROUTING's head shows the same. *Fail:* cannot be read from
there → `ui.DOT_R`, or say what would read.

**O10. The home in git, if you want it (WP6).**
Headless: `uv run pytest -q tests/test_homegit.py`.
In `$HYPERSPACE_HOME/config.toml` add `[library]` and `git = true`.
Launch: `ls -a $HYPERSPACE_HOME` shows no `.git` yet. Save a preset.
*Pass:* `git -C $HYPERSPACE_HOME log --oneline` shows "Hyperspace: the
home as it was …"; save again, rename, ×: one commit each, with its
words. `git -C $HYPERSPACE_HOME status --short` is empty; `git -C
$HYPERSPACE_HOME ls-files | grep -c -e weights -e trash -e last_show -e
windows.json` says 0; `git -C $HYPERSPACE_HOME remote` prints nothing.
Now `touch $HYPERSPACE_HOME/.git/index.lock` and save: *Pass:* the save
is instant, the preset is on disk, one line says git did not commit;
remove the lock and save again: the log has both. *Fail:* a save that
waits → `homegit.Committer.request`. Leave the key off on the real home
unless you want it.
