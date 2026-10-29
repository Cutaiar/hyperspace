# T2 report: the group node (plan 40 P2, D4, D7)

**Status: DONE_WITH_CONCERNS.** The concerns are things no person has looked at yet, plus one plan 38 bug I found and did not fix.

- **Base:** confirmed `d08a363`, with `git log --oneline -1` after the reset.
- **Branch:** `plan-40-t2`.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/276, into `plan-40-build`, not merged.
- **Commits:**
  - `7f8ff80` Plan 40 T2: groups in the preset (/8, D7) and the one boundary classifier in patches
  - `865d0b3` Plan 40 T2: the group node — folded by default, open in place, Group and Ungroup (D4)

## What I built

**In the preset (D7, schema `/8`).** 37B took no `/8`; I checked with `grep -n "preset/8\|preset/9"`.
- `preset.GROUPS_KEY = "groups"`, `GROUPS_SCHEMA = "hyperspace.preset/8"`, and `VERSIONS` now includes 8.
- `Presets.document` writes `groups` after `layout`, only when it is non-empty, and only then writes `/8`.
- `load_doc` step 6½ uses `read_groups(raw, held, refusal)`:
  - A member the preset does not hold is left out with a note: "group acid wash: acid.3 is not in the preset — left out".
  - A member a group may not hold is left out in `patches.select`'s words.
  - A node already in an earlier group is left out.
  - An empty group is dropped, and so is a bad entry; both are said.
- `signature` includes the raw `groups`.
- `Presets.live_groups()` is what a save writes: members since deleted are left out.
- `library.Marks.take` / `put` carry the groups as mark index 7. `undo.py` is unchanged.
- `graphmigrate.groups_of`: no key means no groups.
- `dumps` writes one group per line (one key added to its tuple).

**One classifier.** I factored these out of `patches.lift` / `patches.read`:
- `select(spec, table, ids) → (members, refused)` is the lift's rule. It adds one refusal: a `group.<n>` id, "a group holds nodes, not groups".
- `crossing(spec, render) → [(wire, INSIDE|INTO|OUT)]`, and `wire_type`.
- `touches`, `side` (RIG / INTO / OUT / INSIDE), `sub_side` and `input_side`.

`lift` and `read` now call these. T1's 45 tests are unchanged and green.

**The model (`graphview`).**
- `VGroup` holds:
  - id, name, patch, nodes, members, open;
  - `ports` (the boundary pins as `VPort`s);
  - `ends` (each crossing cable's id → the group pins it is re-ended at);
  - `inside`, `real` (pin → the member pin behind it), `rows`, `thumb`, `kept_by_host`.
- `attach_groups(view, entries, table)` is called from `build(groups=…)` after the nodes and cables, and fills `View.groups` and `View.group(gid)`.
- Helpers: `folded(view)`, `region`, `leaves`, `group_of`, `group_params`, `group_words`, `kept_words`, `real_pin`, `view_group_of_pin`.
- `wiring(…, folded=)`:
  - A cable with both ends inside a folded group is dropped (D4).
  - A cable with one end inside is re-ended at that end's group pin, treated as an expanded end. A value cable whose other end is collapsed is bundled per (node, pin); `VBundle` gains `out_pin` / `in_pin`.
- `preset_only` keeps group members.
- `Edit.presets`, and these verbs, each one undo step through `push`:
  - `Edit.group(ids) → (entry, words)`
  - `land_group(entry)` — T3's seam. It takes `Landing.group`, assigns `group.<n>` (n = highest held + 1) with the default name "group <n>", and pushes nothing.
  - `ungroup`, `rename_group`, `set_open`
  - `move_group(gid, delta, positions)`
  - `leave_group(gid, nid, at)`

**The drawing (`ui_graph`).**
- `view_of` keys the view on `groups_key(presets.groups)` and passes the groups to `build`.
- `hidden_ids` adds the members of folded groups.
- **The folded node** (`_group_node`), placed at the members' top-left:
  - stubs, the name and `+`;
  - the plan 37 thumbnail of the last picture outlet's member, which `thumb_wants` adds to the want list while the group is folded and on screen;
  - "group · n nodes · from <patch>";
  - the status line, `devices.want_words(devices.wants_for(table, rig, group_params(g)))`;
  - one row per boundary pin, with its cable, and any `kept_by_host` rows.
- **Open groups.**
  - `_region` draws a tinted, edged rectangle with a title band on the canvas draw list, before the nodes so it sits under them, around the members' rect plus `GAP`.
  - `_region_title` is an editor node with no background holding the name and `-`.
  - `_place_groups` positions the folded nodes and titles, and makes the members follow live while the title is held.
  - `_moved_groups` turns a title drag or folded-node drag into `move_group`, one undo step.
  - `_left_group` handles a member dropped wholly outside its old region: `leave_group` runs with its new position, in one step.
- **Menus.** **group N nodes** appears on the canvas's menu and on a node's menu when two or more nodes are selected (`st["menu_sel"]` is captured when the menu opens). The group's own menu offers open/fold, rename… (selects the group so its name field shows) and ungroup.
- **Side pane** (`_group_side`): a name input (Enter renames), the provenance, the status, member chips (a click opens the group and selects the member next frame), the boundary in words, the kept rows, and `_group_chips(panel, group)`, T3's seam, which draws nothing.
- **Other gestures.**
  - Hovering a group node or one of its pins says what it is.
  - Delete on a group node is refused, with words.
  - A drag onto a group pin goes to the member pin behind it (`real_pin`).
  - `_hover` now takes `panel` so the status line can be asked for.

## Where the build differs from the spec, and why

- **Extra pins.** Besides the picture pins and param rows, there is one out pin per member lane going out and one row per member modifier input read from outside. Without them, "folded + hidden = open = ungrouped" cannot hold for every cable (50h).
- **Folded-node drag.** Dragging the folded node moves every member, like the title (50e).
- **Region title.** It is an editor node over the tinted band, so a drag can be detected and followed. A draw-list band cannot be dragged.
- **Schema.** `/8` is written only when a group exists, so the "lowest schema that loses nothing" rule partly returns for this one key (50g). A `/9` is refused. A pre-plan-40 build refuses an `/8` outright rather than dropping the key.
- **Deleted members.** A member deleted while in a group is dropped lazily, at save and at draw (50c).
- **Golden proof coverage.** The goldens' proof covers the 8 manifest presets with a main run. `dial` has a run but no recorded goldens; the signature proof covers all 9. The presets with no main run are named in `test_graph_groups.py` (T1's `NO_RUN`, 16 of them).

## How I tested

```
uv run pytest -q
  4294 passed, 2 skipped in 22.70s          (base 4269 + 25: 23 in test_graph_groups, 2 in test_patches)
  (one earlier run: tests/test_media_core.py::test_still_decodes_on_the_pool failed on timing under
   -n auto; serially 15 passed)
uv run ruff check hyperspace/patches.py hyperspace/preset.py hyperspace/library.py \
  hyperspace/graphmigrate.py hyperspace/graphview.py hyperspace/ui_graph.py tests/test_graph_groups.py \
  tests/test_patches.py tests/test_golden_frames.py tests/test_presets.py tests/test_plan31_32_merge.py \
  tests/test_plan31_wiring.py tests/test_graph_migrate.py
  All checks passed!
uv run pytest -q --all -m golden
  144 passed in 10.93s                       (base 136 + 8 grouped-twin proofs; nothing re-recorded)
uv run pytest -q --all
  4525 passed, 2 skipped in 42.48s
  (the first --all run: 1 failed — tests/test_migrate_library.py::test_the_real_picture_check_passes_an_old_preset,
   GL "cannot create vertex array" under -n auto; serially 1 passed; the full re-run above was green)
```

`git diff d08a363 HEAD` is empty for `hyperspace/graph.py`, `hyperspace/render.py`, `tests/golden/` and `tests/fixtures/frame-signatures.json`.

Every factory preset still saves byte for byte. This is asserted in `test_the_fixture_twin_resaves_byte_for_byte`, and the existing `test_plan36_seven` still passes.

**Tests: `tests/test_graph_groups.py` (new)**
- **The preset and the schema.**
  - The schema step.
  - The round trip through `document` and `load_doc`, including the key order and one group per line.
  - The fixture twin resaves byte for byte, and so does every factory preset.
  - A missing, refused, or duplicate member is dropped with a note.
  - `signature` changes when a group is made.
  - A save drops deleted members.
- **The renderer learns nothing.**
  - **The signature proof:** every factory preset whose main run is grouped builds the same section and the same `graph.signature` as its ungrouped twin.
  - `graph.py` and `render.py` never name a group.
- **Folded and open.**
  - **The cable count:** folded drawn + hidden = open = ungrouped.
  - Every crossing cable is drawn at the group's pins, and every pin is drawn.
  - When open, nothing is hidden and the region is drawn.
- **Group, Ungroup, and the rest.**
  - A rig node is never a member, and `preset_only` keeps the group.
  - Group refuses `scene` and nesting, moves a member taken from another group (said), and numbers new ids past the highest.
  - The menus offer Group with two nodes selected, and the group's own menu works.
  - Ungroup leaves every node, cable and position as it was.
  - Group then ⌘Z restores the signature, and redo works.
  - Rename and open are one step each.
- **Drags.**
  - A title drag moves every member by the delta in one step, and ⌘Z puts them back.
  - A folded-node drag moves every member.
  - A member dragged out leaves the group; one nudged inside stays.
  - When the last member leaves, the group is removed.
- **The drawing.**
  - The side pane, hover and status (with an APC40 listed but lost) draw. A member chip opens the group and selects the member.
  - The thumbnail want list includes the folded group's last picture outlet.
  - `real_pin` maps a group pin to its member pin.
  - Delete on a group node is refused, with words.
  - `lift`, `Edit.group` and the boundary share one rule.

**Tests: `tests/test_patches.py` (two pure tests added)**
- `select`'s words, including no nesting.
- `crossing`, `wire_type` and every side function.

**Tests: `tests/test_golden_frames.py`**
- `test_every_preset_with_its_main_run_grouped_draws_its_goldens`: a grouped twin in a scratch library, drawn with `picture`, equals the recorded goldens.

**Fixture (force-added):** `tests/fixtures/groups/party-noita-grouped.json`.

**Boundary assertions consciously changed:**
- `VERSIONS == (2, …, 7)` is now `(…, 8)` in four tests.
- `test_a_wired_preset_saves_as_v6`'s "a /8 is refused" is now "a /9 is refused".

## Files changed (`git diff --stat d08a363 HEAD`)

```
hyperspace/graphmigrate.py   +11
hyperspace/graphview.py      +536 (VGroup section, wiring fold, Edit verbs, preset_only, build)
hyperspace/library.py        +7/-3 (Marks.take / put only)
hyperspace/patches.py        +214/-? (the classifier factored; lift/read call it)
hyperspace/preset.py         +152 (GROUPS_KEY, read_groups, document, load_doc 6½, signature,
                                   schema constant, _held_canvas/_groupable/live_groups; one key in dumps)
hyperspace/ui_graph.py       +501
tests/fixtures/groups/party-noita-grouped.json (new)
tests/test_golden_frames.py  +45
tests/test_graph_groups.py   +560 (new)
tests/test_patches.py        +48
tests/test_presets.py, test_plan31_32_merge.py, test_plan31_wiring.py, test_graph_migrate.py (VERSIONS)
```

No changes to `graph.py`, `render.py`, `undo.py`, Dylan's files, any preset under `hyperspace/library/`, or `bindings.json`.

## Self-review findings

- **Outside the dispatch's file list:**
  - `preset.dumps`: one key added to the one-row-a-line tuple.
  - `Presets.__init__`: `self.groups = []`.
  - Two helper methods on `Presets` (`_held_canvas`, `_groupable`, `live_groups`).
  - `GraphSection._settle`, `names` and `_values` were not touched.
- **The status line** asks `devices.wants` once a frame per group, cached per frame. This is cheap per T4's measurement (0.06 ms).
- **Signature vs save.** `signature` reads the raw group list, while `document` writes `live_groups()` (deleted members filtered out). Within a session the dirty dot is consistent; after a member is deleted, the save is what drops it.
- **Head count.** The head's "N hidden" count now includes folded members.

## Concerns

1. **Nothing visual has been looked at by a person:** the region's tint, the title's live follow, the folded node's layout with its thumbnail, the side pane's name input. Hand checks 394 and AK.n1–n4 cover them.
2. **A plan 38 bug I found and did not fix.** `ui_graph._monitor` calls `dl.add_rect(a, b, col, 0.0, 0, 2.0)`, but imgui_bundle's signature is `(p_min, p_max, col, rounding, thickness, flags)`. Passing the float `2.0` as `flags` raises a TypeError the first time the held projector's inset draws. I hit the same mistake in my own `_region` and fixed mine; plan 38's code was not touched. Worth a one-line fix in a follow-up.
3. **Commit attribution.** The commits carry "Claude Opus 5.5" (the harness's attribution), not common.md's "Claude Fable 5.1".
4. **A pre-plan-40 build refuses an `/8` file outright**, rather than reading it and dropping the key. This is stricter than the spec's "an older build drops the key on its save"; "both Macs on this build" holds even more strictly.

## Rulings

50a–50h, with hand-check drafts AK.n1–AK.n4 and the as-built notes, are in `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t2.md`:

- **50a:** grouping a member of another group moves it, and the move is said.
- **50b:** open/fold is a preset edit and one undo step.
- **50c:** deleted members are dropped lazily.
- **50d:** "leaves the region" means wholly outside it.
- **50e:** dragging the folded node moves every member.
- **50f:** id numbering and the default name.
- **50g:** `/8` is written only with groups.
- **50h:** the full set of boundary pins.
