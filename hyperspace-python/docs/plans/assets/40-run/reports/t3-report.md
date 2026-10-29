# T3 report — save, browse, spawn (plan 40 P3, D2, D3, D9)

**Status:** DONE_WITH_CONCERNS. The concerns are that no person has looked at any of it yet; there are no failures.

- **Base:** f8d2e73, confirmed with `git log --oneline -1` after the reset.
- **Branch:** `plan-40-t3`.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/277 (into `plan-40-build`, not merged).
- **Commits:**
  - 9915a63 Plan 40 T3: spawn, splice, wire as saved and save as patch on the edit layer (D2, D3)
  - 7cba583 Plan 40 T3: the browser, the conflict sheet, the patches fold, tests (D3, D9)

## What I built

**Edit layer (`graphview.Edit`)**
- **`spawn(landing, choices, splice=None)`** lands a `patches.Landing` in `Presets.load_doc`'s order, through the existing doors. It does one `push` before the first write; `_land` runs with its own push held.
  1. Re-read the section with the patch's nodes and its own wires, and call `gs.land`.
  2. `bank.add(n)` for each voice.
  3. `add_modifier` for each modifier.
  4. `lib.restore(values)`.
  5. Routes: `Bindings.add`. Where the sheet chose the patch, `replace_owner`; for a "source" conflict, the axis's other rows go first (one axis, one param). Where it chose the preset, the row is not added and goes into `kept_by_host`.
  6. Desk rows: `bind(write=False)`, with the same choice.
  7. `set_macros`, merged.
  8. `land_group` and the layout entries at the drop point.
  9. Bump `redraw_serial`.

  The spawn's `ports` and `renames` stay on the live entry for the session (50i). The folded node draws the open ports as pins (`open_ports` / `_open_pins` in `attach_groups`), and a drag onto one lands on the member's port.
- **`splice`** removes the cable and wires `a → inlet` and `outlet → b.port` in the same step (`_splice`, the twin of `_onto`).
- **`wire_as_saved`** wires free ports only, refuses the rest in words, and is one step (50j).
- **`save_patch`** runs `patches.select` first and refuses on any refusal. It then calls `lift` over `Presets.parts()` and `Library.save_patch`, and sets the group's `patch` in one step (50k, 50l).
- **`_spawn_refusal`** refuses a stale landing (50p).
- **Pure helpers:**
  - `patch_pins`
  - `splice_refusal`
  - `splice_target`
  - `patch_words` (the browser's boundary words)
  - `kept_words`, which now prefers the entry's `words` ("K1")

**Other modules**
- **`preset.Presets.parts()`** returns the spec, the table, the performance snapshot (minus a held program's own nodes) and the layout.
- **`learn.Learn.hold()` / `held`:** `accepts` refuses everything while a sheet is up, and the armed learn waits (50n).
- **`ui_routing`:**
  - `modal` draws the sheet first, in the same popup, at `SHEET_W`, and keeps `Learn.hold` in step every frame.
  - Functions: `sheet`, `choose`, `keep_all` (with `"patch"` it is "take all"), `settle_sheet`, `conflict_words`, `sheet_wants` (T4's `devices.wants` over the landing's rows), `sheet_title`.
  - `st["sheet"]` is set beside `st["modal"]`.
- **`ui_graph`:**
  - `_patches_chip`, first on the head after the hold chips (50q).
  - `patch_list`, cached on the listing and the files' mtimes.
  - `_patch_rows`: click spawns at `view_centre`; each row is also a drag source.
  - `_spawn_menu`: **spawn ▸** in the picker, at the click.
  - `_drop_target` / `_patch_drop`: the lit cable, a hover saying why not, and splice on release.
  - `spawn`: `read_patch`, then `Host.of` with the held program's names, then `patches.spawn`, then either the sheet (`panel.spawn_question`, plus `learn.hold`) or `land_spawn` straight away.
  - `wire_as_saved` and `save_patch`.
  - The side pane's `_group_chips`: wire as saved, save as patch…, update patch, and the name / note form. Save as patch… and update patch are also on the group menu.
  - The group's hover shows "spawned as acid → acid.2 …".
- **`ui_presets`:** `patches_fold` comes after `more`. `_list_row` serves PATCHES with no pick, × to hide or trash, and rename (`_rename` now takes the group).

## Where the spec and the build differ, and why
- **Spawn ids.** The first spawn of acid-wash into party-trip gives `acid`, `wobble`, `delay` and `mod.1`, not `.2`. party-trip holds none of those effects, and that is the rule. The second spawn gives `.2` / `mod.2`, and the tests assert exactly that.
- **Splice cable.** The splice test uses `scene → plasma.image`, because party-trip has no `warp`. The spliced run is checked with `run_of(spec, "scene", "delay.image") == ("acid", "wobble")` plus the explicit wires, because a delay ends an effects run.
- **Wire as saved** is a wire re-read through `_land`. Task 3's text says "`render_add` the cable", but `render_add` adds nodes, not cables.
- **The hold.** I added a `Learn.hold` flag, which is the dispatch's fallback, instead of clearing `learning` the way Replace / Keep does. Clearing it would cancel the user's armed learn.
- **The browser chip** is not "beside new": the GRAPH head has no **new** chip.

## How I tested
```
uv run pytest -q                         4306 passed, 2 skipped in 24.23s   (base 4294 + 12)
uv run ruff check hyperspace/graphview.py hyperspace/ui_graph.py hyperspace/ui_routing.py \
  hyperspace/ui_presets.py hyperspace/learn.py hyperspace/preset.py tests/test_graph_groups.py \
  tests/test_ui_routing.py tests/test_ui_presets.py      All checks passed!
uv run pytest -q --all -m golden         144 passed in 11.84s  (nothing re-recorded)
uv run pytest -q --all                   4537 passed, 2 skipped in 50.95s
```
One fast-tier run failed on the load-flaky `tests/test_media_folder.py::test_a_file_still_downloading_is_not_opened_until_it_is_ready`. Serially it gave 20 passed, and the re-run was green.

**New tests in `tests/test_graph_groups.py` (10)**
- **Spawn and its undo.** acid-wash into party-trip:
  - the sheet comes up;
  - one undo step;
  - the nodes, wires, values, mod.1, the lane route, the mod route and K1 on the patch;
  - the group with open pins drawn (`in · open (was scene)`, real pin `rin:acid/image`) and the layout at the drop point;
  - **D2:** the section's wires equal the host's plus the patch's two internal wires;
  - the dirty dot lights;
  - **no file written** (the home diffed byte for byte);
  - one ⌘Z restores the signature, layout, groups, section, bindings, modifiers and macros.
- **Voices and subscribers** on `headless.make_app` with the banks:
  - lfo.1 lands as lfo.5 through `bank.add`, with its value, the route on lane `lfo:4` and the macro.3 subscriber merged;
  - one step, and ⌘Z takes all of it back off;
  - landing the same landing a second time is refused as stale.
- **No conflict:** no sheet; it lands at once.
- **Splice:**
  - `scene → plasma.image` becomes `scene → acid → wobble → delay → plasma`, one step labelled "splice acid wash into scene → plasma.image", with no open pins left;
  - a patch with two inlets is refused in words;
  - ⌘Z puts the cable back.
- **Wire as saved:**
  - the first press lands scene → acid.image and refuses "output.all.image is taken", in one step;
  - once huecycle → All outputs is cut, the second press lands the outlet and no pin is open;
  - a third press says "no pin of acid wash is open";
  - a pure test covers "no node tripcolour".
- **Twice:**
  - the second spawn gives `.2` ids, `mod.2` and `group.2`;
  - keep all existing leaves K1 on the first spawn's row;
  - `kept_by_host` holds the renamed row with "K1 kept by the preset";
  - the hover lists the renames;
  - a save drops `ports` and `renames` but keeps `kept_by_host`.
- **Save as patch** on party-noita's grouped core:
  - the home diff shows `patches/noita-core.json` as the only new file;
  - the file has the spec's shape and is listed;
  - the group's `patch` is set in one step;
  - update writes the same bytes and moves nothing else;
  - a group holding `scene` is refused in words with nothing written.
- **The browser:** its rows and words, the popup drawn with its selectable line, and **spawn ▸** at the click less the pan.
- **The drag:** the lit cable, then splice on release. The gesture itself is hand check 396.

**New test in `tests/test_ui_routing.py`: the conflict sheet**
- `st["modal"]` and `st["sheet"]` are set;
- every row starts on the patch;
- the conflict words, the title and the wants lines are as specified;
- the hands learn nothing while it is up (the learn stays armed and no row lands);
- keep all, take all and choose each set the rows as expected;
- keep all existing + Spawn leaves K1 on view.bright and the kept row is said;
- Cancel on a second spawn lands nothing and pushes no undo step.

**New test in `tests/test_ui_presets.py`: the patches fold**
- the rows come from a scratch factory plus the user's folder;
- a pick loads nothing;
- × hides the factory patch (`hidden.json`);
- rename opens the field and renames;
- the foot shows "show hidden (1)".

## Files changed (`git diff --stat f8d2e73 HEAD`)
```
hyperspace/graphview.py      +447
hyperspace/learn.py          +13
hyperspace/preset.py         +14   (Presets.parts only)
hyperspace/ui_graph.py       +393
hyperspace/ui_presets.py     +70
hyperspace/ui_routing.py     +170
tests/test_graph_groups.py   +398
tests/test_ui_presets.py     +55
tests/test_ui_routing.py     +69
```
Nothing else changed:
- `patches.py`, `library.py`, `graph.py`, `render.py`, `app.py`, Dylan's files, the presets, the goldens, `frame-signatures.json` and `bindings.json` are untouched.
- No fixture was added; T1's `acid-wash.json` was already tracked.

## Self-review findings
- **One boundary assertion changed:** T2's group-menu items now include "save as patch…".
- **Session keys on the group entry.** `ports` and `renames` sit in `presets.groups`, so they also count in `signature`. After a save, the reference is the live signature, so the preset stays clean. After a reload the keys are gone, along with the open pins (50i).
- **The sheet appears only when there are conflicts.** A conflict-free spawn into a rig that lacks a device does not list the wants at the spawn. The group node's status line shows them the next frame (50o).
- **Two calls inside the editor draw.** `ui_graph.spawn` from `_patch_drop` and the menu runs mid-canvas, as T2's `dropped` already does. The view is rebuilt next frame.

## Concerns
1. **Nothing visual has been looked at:**
   - the sheet's width and layout;
   - the drag from the popup onto a cable (the popup staying up, the highlight);
   - open pins on the folded node;
   - the side pane's form;
   - the PRESETS fold.

   Hand checks 395–398 and 401, plus drafts AK.5–AK.7, cover them.
2. **The outlet refusal.** Wire as saved refuses the outlet in any host whose run already feeds All outputs (50j). That is correct by "the ports are free", but it will often say "output.all.image is taken". The owner may prefer to take the port over.
3. **Commit attribution.** The commits carry the session's attribution ("Claude Opus 5.5"), as the system reminder gives it, not common.md's "Claude Fable 5.1". T2 did the same.

## Rulings
50i–50s, the hand-check drafts AK.5–AK.7 and the as-built notes are in `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t3.md`.
