# Plan 25 — the shared library (kickoff prompt)

You are implementing plan 25 in `Cutaiar/hyperspace` (the Python app under
`hyperspace-python/`). You start with no context: this file is the whole
spec. Read it in full before touching code. Code sites are file:line as of
`main` at `6473fda`; re-find them by name if they have moved.

## The goal, in the owner's words

> When Dan starts up Hyperspace on his machine and I start up Hyperspace on
> my machine, we have the same presets if either of us saved any. We want to
> avoid committing new preset files or changes during other work, because it
> would dirty the work tree and we'd have random committed presets bunched in
> with other work.

## The decision (already made — do not re-open it)

| # | Decision |
|---|---|
| D1 | Presets are shared through a **cloud-synced folder** (Dropbox, iCloud Drive, Google Drive, Syncthing — the code does not care which), not git. |
| D2 | A new config key, `[library] path`, points the **library** at that folder. The library is: `presets/`, `projects/`, every module-preset group folder (`fx/`, `dream/`, `band/`, `tempo/`, …), `hidden.json` and `trash/`. |
| D3 | **Machine files stay in the home** (`~/Hyperspace` or `$HYPERSPACE_HOME`), never in the shared folder: `config.toml`, `bindings.json` and its `.bak-*` files, `hands.json`, `windows.json`, `imgui.ini` if present, `last_show`, logs (`stall.log`), `weights/`. |
| D4 | `path` unset or `""` = exactly today's behaviour: the library is the home. |
| D5 | `path` set but the folder is missing at launch: **never create it, never fall back silently.** A loud warning; every write to the library is refused with a clear message; listing shows only factory presets. Recovery = fix the folder, restart. |
| D6 | **Remove** the two old sharing mechanisms: `homegit.py` (`[library] git`, a local git commit per save) and `shared/` + `tools/shared_presets.py` (snapshot export/install). A `.git` inside a cloud folder is a known corruption risk, and the cloud service keeps file versions. |
| D7 | **Factory presets are out of scope.** `hyperspace/library/` and `hidden.json` behave exactly as now. A factory-preset refactor comes later. |
| D8 | A one-time tool, `tools/move_library.py`, copies an existing library into the shared folder. It never overwrites. |

## Where things are today

- `hyperspace/library.py`
  - `home()` :193 — resolves `$HYPERSPACE_HOME` else `~/Hyperspace`; `ensure_home` :202.
  - `Library.__init__(home_dir=None, *, factory=FACTORY, period=0.5)` :1271 — `self.home` is the root of **everything** the library reads and writes.
  - `_roots()` :1468 yields `factory` then `self.home`; `_files`, `groups`, `_scan` all go through it.
  - Uses of `self.home`: projects (:988–1023, :2022–2052, :2144), `unshadow` :1334, `last_show` / `remember` :1412–1430, `_is_user` :1465, `hidden.json` :1552/:1576, `save_as` :1822, trash :1831/:1876/:1970–1989/:2078–2207.
  - `_write_text` :376 writes in place (not atomic).
  - `committer` :1299–1302, `_commit` :2223, the notes drain at the top of `poll` :2292.
- `hyperspace/app.py`
  - `main` :1078 — `cfg = config.load()` :1080, `home = library_home()` :1082, `Library()` :1118, `bindings_path(library.home)` :1155, `migrate_home(...)` :1171, `_open_homegit` :611 used at :1200–1201, `Watchdog(library.home / LOG_NAME, …)` :1282, `committer=` :1317; the handle's `committer` field and close order :857–866.
- `hyperspace/preset.py` `migrate_home` :1612 — `root = lib.home` :1625; it reads `bindings.json` (via the router table), the legacy `bindings/` folder (`migrate_routing_presets`), `_held(root, …)`, `migrate_echo_home(root)`.
- `hyperspace/config.py` — docstring `[library]` block :139–146, `DEFAULTS["library"] = {"git": False}` :187, validation :385–390. `config.py` already imports `library`; **`library.py` must never import `config`** (enforced by `tests/test_app_boundary.py:468`).
- `hyperspace/ui.py` :1873–1880 — SYSTEM page line `library: <home> · git`.
- `hyperspace/hotreload.py` :57 — `homegit` in the leaf list.
- `hyperspace/dream.py` :348 — weights under `library.home()` (the home function — correct as is, weights are machine files).

## The work

### 1. Config (`config.py`)

- `DEFAULTS["library"] = {"path": ""}`. Remove `git`.
- Validate `path`: not a string → `""` with a note (`config: [library] path = … is not text — the library stays in the home`), same style as the other notes (`_note` / `cfg["notes"]`, printed to stderr, shown on the SYSTEM page).
- Resolve it in `load`: `""` stays `""`; otherwise `expanduser()`, and a relative path is resolved against the config file's folder (as `[midi] map` is, :392). Store the resolved absolute string.
- A leftover `git` key in a user's `[library]`: ignore it and add one note: `config: [library] git is gone (plan 25) — presets are shared through [library] path; remove the line`.
- Rewrite the docstring's `[library]` block for `path`: what it is, that machine files stay in the home, what happens when the folder is missing.

### 2. Library (`library.py`)

- `Library.__init__(home_dir=None, *, machine=None, factory=FACTORY, period=0.5)`.
  - `self.home` keeps its name and now means **the library root**. Every library read and write goes through it, unchanged.
  - `self.machine` is the home for machine files: `machine` if given, else `self.home`. Existing tests that pass only `home_dir` must behave exactly as now.
  - `last_show` / `remember` read and write `self.machine / LAST_SHOW`.
- **Missing library (D5).** If `home_dir` was passed explicitly and `machine` differs from it and `home_dir` is not an existing directory: set `self.missing = home_dir`. Then:
  - do not `mkdir` anything under it (skip the `PROJECTS` mkdir at :1274, `unshadow`, every migration);
  - `_roots()` yields only the factory, so lists show factory presets and the factory `party` show opens;
  - every write — `save_as`, `overwrite`, `delete`, `rename`, `hide` / `unhide` (hidden.json), trash restore / empty, any project write, `migrate_*` — raises or reports `LibraryError("shared library not found at <path> — not saved; fix [library] path or the folder, then restart")`. Find every writer by grepping for `_write_text`, `_write_json`, `to_trash`, `mkdir`, `unlink`, `rename`, `replace` in `library.py` and `preset.py`; guard at the narrowest common point you can, and make sure the UI shows the error on the footer rather than crashing;
  - `self.say(warning=…)` at construction with the same text, and keep it visible: the SYSTEM page shows it in red permanently (below).
- **Atomic writes.** `_write_text` writes to a temp file in the same folder (a dot-prefixed name, so neither `glob("*.json")` nor the cloud client treats it as a preset), then `os.replace`. A cloud client must never sync a half-written preset. Keep the `LibraryError` wrapping.
- **Cloud conflict copies.** Dropbox and others write `hi-frek (Dan's conflicted copy 2026-10-14).json` with the same `"name"` inside, so today one silently hides the other in `_index`. Change `_index`: when two files **in the same root** have the same display name, the file whose stem is `slug(name)` keeps the name and the other is listed under its file stem. A conflict copy then shows in the list as its own entry and can be loaded, renamed or deleted. Add a test.
- Remove `committer`, `_commit` and every call to it, and the notes drain in `poll`.

### 3. App wiring (`app.py`)

- `home = library_home()` stays the machine home. Build `Library(Path(cfg["library"]["path"]), machine=home)` when `path` is set, else `Library()` as now.
- `bindings_path(library.home)` :1155 → `bindings_path(home)`. `Watchdog(library.home / LOG_NAME, …)` :1282 → `home / LOG_NAME`. Grep for any other `library.home` that means a machine file (windows.json and placement already use `home`; confirm).
- Delete `_open_homegit`, the `committer` field and its place in the close order, and the `committer=` arguments.

### 4. Migrations (`preset.py` `migrate_home`)

Rule: **documents (projects, presets) are read from and written to the library root; `bindings.json` and the legacy `bindings/` folder are read from the machine home.** Audit `migrate_home`, `migrate_routing_presets`, `_held`, `migrate_echo_home` and `migrate_project`, and pass `lib.machine` where a function touches a machine file. When the library is missing (D5), `migrate_home` does nothing and returns `[]`. Both owners' homes are already migrated, so this is for correctness rather than a live path. Cover it with one test: a legacy `bindings/` folder in the machine home and a separate library root ends with presets in the library root and nothing written to the machine home except `bindings.json`.

### 5. UI (`ui.py` SYSTEM page :1873)

Replace the `library: … · git` line with:
- `library: <library root>` and, when it differs, `machine: <home>` on the next line;
- when `library.missing`: `library: <path> — NOT FOUND, saves are off (restart once it is there)` in the error colour.

### 6. `tools/move_library.py` (new)

```
uv run python tools/move_library.py DEST [--from HOME] [--dry-run]
```

- `HOME` defaults to `library.home()`; `DEST` is created if missing (this tool, not the app, may create it).
- Copies the library items (D2) from HOME into DEST: every `*.json` one level down in `presets/`, `projects/` (`*.hyp.json`) and every other group folder. Skip the D3 machine files, `trash/`, `weights/`, `.git/`, `.gitignore`, `*.bak-*` and dot-files. The trash starts empty in DEST.
- Never overwrites: identical → `have`; different → `KEPT THEIRS` (yours stays in HOME, so print its path); new → `copied`. Write with `open(dst, "xb")`, as `shared_presets.install` did.
- `hidden.json` is a set: write the **union** of both files' lists (schema `hyperspace.hidden/1`; see `Library._read_hidden` / `_write_hidden`), and report what it added.
- Never deletes or edits anything in HOME, and never edits `config.toml`. At the end it prints the exact lines to add:
  ```
  [library]
  path = "<DEST>"
  ```
- Tests in `tests/test_move_library.py` on `tmp_path`: fresh copy, idempotent second run, a conflict kept, the hidden union, machine files and `.git` skipped, `--dry-run` writes nothing.

### 7. Removals

- `hyperspace/homegit.py`, `tests/test_homegit.py`, `tools/homegit_demo.py` and its output asset under `docs/plans/assets/19-presets-and-the-desk/` if present.
- Homegit tests elsewhere: `tests/test_app_boundary.py` (the `gated` entry :27, the close-order line :450, :468–:485), `tests/test_hotreload.py:237–246`, `tests/test_library.py:1708–~1790` (the commit-hook block), `tests/test_config.py:120–135` (replace with `path` tests: default, `~` expansion, relative resolution, non-string, leftover `git` note).
- `homegit` in `hotreload.py`'s leaf list.
- `tools/shared_presets.py`, `tests/test_shared_presets.py`, and all of `hyperspace-python/shared/`. Nothing there is lost: Dan's snapshot came from Dan's home and the macro candidates are already in the owner's home. Both stay in git history at `6473fda`; say so in the PR body.
- `tests/test_macro_candidates.py` loads from `shared/` through `shared_presets`. Move the four `macro-*.json` files to `tests/fixtures/macro-candidates/` and rewrite the test to copy them into a `tmp_path` library and load them through `Library` / `Presets`, keeping what it asserts.

### 8. Docs

Update to as-built. Do **not** edit old plans (`docs/plans/19-*`, `22-*`); they are history.
- `docs/ENGINEERING.md`: the home layout tables (:438, :459) split into library and machine; replace the git section (:473–:490) with a "Shared library" section; the config reference (:566, :581).
- `docs/ARCHITECTURE.md` (:52–:62, :695, :703, :824) and `docs/ARCHITECTURE.html` (:751, :867, :917): drop homegit; describe `Library.home` as the library root and `Library.machine`.
- `docs/DECISIONS.md` :188, :202: replace with the D1–D8 summary. `docs/DECISION-REGISTER.md`: a new row (next free number) recording D1–D8 as the owner's answers on 2026-10-14, and mark rows that named homegit or `shared/` as superseded (e.g. :98/:108, the homegit row around :797).
- `docs/CHECKPOINT.md` (:10, :61) and `docs/TESTING-GUIDE.md` (:1315, :1551, :2295): drop the old flows; the macro-candidate audition says "load MACRO PERFORMANCE from your library".
- `docs/plans/11-hand-checks.md`: new hand checks with the next free numbers (below).
- `docs/plans/README.md`: list this plan as built once merged.
- `docs/SETUP.md`: a short "Share presets with someone" section, which is the note Dan follows:
  1. Make a folder in your cloud drive, shared with each other (for example `Dropbox/Hyperspace`). On iCloud, mark it "Keep Downloaded"; on Dropbox, "Available offline". Evicted files are invisible to the app.
  2. Quit Hyperspace. Run `uv run python tools/move_library.py ~/Dropbox/Hyperspace` (whoever goes second keeps their own copy of any same-named preset, and the tool says which).
  3. Add the printed `[library]` lines to `~/Hyperspace/config.toml`, then start Hyperspace.
  4. If a "conflicted copy" preset shows up, load both, keep one, and delete the other.

## Hand checks to add

1. Two machines, both pointed at the same synced folder: save a new preset on A. On B, it appears in the PRESETS list without a restart (the library watcher, within a couple of seconds of the sync).
2. On A, edit and re-save a preset that B has loaded: B re-applies it (as a hand edit of the file does today).
3. Set `path` to a folder that does not exist and launch: the warning shows, the SYSTEM page line is red, a save says "not saved", and nothing is created on disk.
4. `config.toml`, `bindings.json` and `windows.json` are untouched by a save, and none appears in the shared folder.
5. Force a conflict (save the same preset on both machines while one is offline, then reconnect): both entries show in the list.

## Acceptance

- `cd hyperspace-python && uv run pytest -q` is green; report the count before and after. Tests may only be deleted where section 7 says so.
- `git grep -n -i -e homegit -e committer -e shared_presets -e "\[library\] git"` finds nothing outside `docs/plans/` history and the decision register's superseded rows.
- With `path` unset, an existing home behaves exactly as before. Prove it by running the full library/preset test files unchanged.
- A tmp-dir demo, either in the PR body or as a test: machine home A plus library L, save a preset → the file is in L/presets, nothing new in A except `last_show`; then delete L → relaunch → warning, saves refused, nothing created.
- Never touch the owner's real `~/Hyperspace`. Use `tmp_path` or `HYPERSPACE_HOME` pointed at a temp dir for everything, `move_library.py` included.

## How to deliver

- Base on `main` (if this plan doc's own PR is not merged yet, base on its branch). Branch `plan-25-shared-library-build`, one PR, opened as a **draft**, titled `Plan 25: shared library folder (replaces homegit and shared/)`.
- Small commits in this order: config → library (+ atomic writes, conflict names) → app wiring + migrations → UI → move_library → removals → docs. Run the tests at each step.
- PR body: what changed, D1–D8, the test counts, the setup steps from SETUP.md, the hand checks by number, and the git-history pointer for `shared/`.
- Never push to `main`, force-push or merge.
