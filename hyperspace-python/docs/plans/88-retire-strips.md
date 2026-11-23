# Plan 88: retire the module strips

Built 2026-11-23 on `claude/retire-strips` (off `claude/sweet-pascal-y7dpe4`). The owner's decision: nobody knows how to use the library strips (`◀ name ● ▶ · save · as… · reset`), so retire them for as many module groups as possible; sane defaults replace them and a patch that wants to differ carries an optional override key in its own JSON. The mechanism is plan 40 T5's `library.RETIRED_MODULES` (D6, which retired `fx`). The `hands` strip is another session's and is not touched here (nor `grip`'s hands wiring, `hands/panel.py`).

## Inventory

A strip is drawn by `Panel._section(title, group)` → `ui_loadable.strip` → `ui_strip.strip`. Before this plan: `view`, `rot`, `camera`, `pattern`, `dream`, `lfo`, `env`, `seq`, `tempo`, `master`, `output`, `band`, `hands`, `grip`, plus `loadable` (the loadable patches' own strip, a document kind, not a module) and `fx` (already retired). `PATCH_GROUPS` (saved inside every loadable patch's `values`): view, rot, camera, pattern, dream, lfo, env, seq, grip. `SHARED_META_GROUPS` (the show's `session`, a module label in its `modules`): tempo, master, output, band, hands.

Module presets are reached from strips and nowhere else (`lib.load(group, …)` has no other caller), and a loadable patch records no module label since plan 44 D3, so the patch groups lose nothing. No shipped loadable patch, install (`tests/corpus/installs/{party,house}.json` name only `band: Balanced`), preset or fixture names a module of a retired group. A show's `session` holds every shared meta value as saved, so its `modules.<group>` reference only names where the values came from.

## Classification

| group | kind | class | why |
|---|---|---|---|
| view, rot, camera, pattern, dream | patch | (a) retired | values live in every loadable patch; no label saved (D3); nothing else loads them |
| lfo, env | patch | (a) retired | same; the LFO bank's size is a patch value |
| seq | patch | (a) retired, flagged | row 509 made "pattern slots" `seq` module presets; the owner's call supersedes it. A saved pattern is still in every patch that carries it, and as a patch of nodes on GRAPH |
| tempo, master, output | shared meta | (a) retired | the show's `session` holds the values; `modules.<group>` ignored on load, kept on save |
| fx | patch | (a) already retired | plan 40 D6 |
| band | shared meta | (c) stays | a scene is a band **layout** (`Library.on_layout` → `control.apply_layout`, the band count) and `on_load` → `control.scene_loaded`; the install corpus names `Balanced`; scenes are code data (`scenes/band/`) with no other picker |
| loadable | kind | (c) stays | the loadable patches' strip, not a module |
| hands | shared meta | retired by its own commit (`f631530`) | another session; listed in `RETIRED_MODULES` here too |
| grip | patch | not touched | its strip is the hands node's, another session's |

(b), "retired but an override key wanted first": none. Every retired group's defaults are the build's fresh values, which a loadable patch already overrides by carrying the value; nothing needed a new key. When a patch wants a non-default for a group with no values of its own to write, that is a new key in that patch's JSON, a later plan.

## What was built

- `library.RETIRED_MODULES` gains the eleven groups. Effects: `strip` returns early (already), `groups()` omits them, `default_name` is None so `defaults` is the build's fresh values even over an old `<library>/<group>/default.json`.
- Show load ignores a retired group's `modules` entry, by name or inline; a show save carries it through untouched (review of #483: an inline copy may be the only one). No error, no note.
- `library.DELETED_MODULES = ("fx",)`: `tools/migrate_library.py` still deletes only the fx files (D6); every other retired group's saved module files are moved into `patches/<group>/` like any, kept and unlisted. Without this the tool would have deleted users' saves.
- The retired `_section(title, group)` calls lose the group argument; `ui_patterns` loses its `ui_loadable.strip` call.
- Dirty dots and per-section reset were drawn only by the strip, so both go with it. A section's values are still undoable (undo), a loadable patch's own dot compares the whole look, and the desk's reset rows are untouched. Per-section reset to defaults is the one thing lost; say so if the owner wants it back as a plain "reset" chip.
- Tests: `test_library` (old show names `master`/`output`; retired groups unlisted, files kept), `test_ui_loadable` (the overlap test now covers the strips that remain), fixes for tests that used `view` as the example module group.

## Left, and why

`band` (above) and `grip` (other session). The strip code stays: `band`, `loadable` and `grip` still use it, and the library API (`save_as`, `load`, `list`) still works for a retired group so files stay readable.
