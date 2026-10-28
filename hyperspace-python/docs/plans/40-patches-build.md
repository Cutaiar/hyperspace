# Plan 40 — build plan

Spec: [`40-patches.md`](40-patches.md), the authority. Read its "What is
there today" map before any task; its file:line references are to `main`
@ f2351a0 and may have drifted. **Every decision D1–D10 is the owner's
(2026-10-27)**; build what the "the owner" column says, not the
recommendation where the two differ (D3, D4, D6, D10).

Branch `plan-40-build`, cut from **`plan-37-38-39-integration` @ 2b185ea
or later** (plan 38 and plan 39 T0–T4 are on it; `main` @ f984d3b, with
PR #266's resizable side pane, is under it). Each task in its own
worktree off `plan-40-build` (`plan-40-t<n>`), merged into it when green;
the final PR is `plan-40-build` → `main`, the owner merges. Work in
`hyperspace-python/`. Tests: `uv run pytest -q …` from there (the fast
tier; `--all` for everything, `--all -m golden` for the goldens).

**Running beside plans 37–39** (their orchestrator's state, 2026-10-27
evening, confirmed in git): plan 39's T5 (`graphview.py` tables) and T6
(docs) and the whole of plan 37 (`ui_graph.py` `_canvas` / `_node` /
hover, `graphview.py` `build` / `summary` / `laid_areas`, `render.py`,
`outputs.py`, one SYSTEM line in `ui.py`) land on the integration branch
after this plan has started, and the integration branch's final PR to
`main` opens two to three hours after. `routing.py`, `devices.py`,
`library.py`, `ui_routing.py`, `modgraph.py` are free. So:

- **T0, T1, T4 and T5 start at once** (T0 first, alone, then the three
  in parallel): none of them touches the regions above. T0's one import
  line in `graphview.py` and T4's one chip on the head are the whole
  overlap, and both merge mechanically.
- **T2 and T3 wait for the integration branch's final PR to merge to
  `main`** (or, if the owner says go sooner, for plan 37 to be on the
  integration branch): the controller then merges `main` (or the
  integration head) into `plan-40-build` once, re-runs the fast tier,
  and cuts T2 from that. T2 and T3 are the canvas work and would
  otherwise conflict with plan 37's `_node`, `build` and `summary`. By
  the build plan's own order T2 needs T1 anyway, and T1 is the longest
  task, so the wait is mostly absorbed.
- `preset.py`: plan 38's hook lives in `GraphSection._settle` / `names`
  / `_values` and plan 39's declares in `_settle`; this plan's T2 touches
  `document`, `load_doc` step 6½ and `signature`, and T5 the module
  hooks — different functions, keep it that way.
- The schema number (D7): 37B took none, so `groups` is `/8` unless
  something else has taken it by the time T2 cuts; the migration is "the
  key is absent → no groups".

## Global constraints

- **The rule, and its one exception.** The graph on GRAPH is the whole
  truth (plan 36): no default graph, no hidden edge, no auto layout,
  nothing filled in at load. A spawn attaches nothing by itself (D2); a
  patch's layout is its own, placed where the user clicked, not an auto
  layout. The exception is D4, the owner's: a **collapsed group** folds
  its internal cables until `+`. Nothing else may hide a cable.
- **The renderer learns nothing.** `graph.build_graph`, `graph.signature`,
  `render.py` and the goldens see the flat graph. No golden PNG under
  `tests/golden/` changes; `tests/fixtures/frame-signatures.json` is not
  re-recorded. T2 proves it with a grouped preset against its ungrouped
  twin.
- **Through the doors.** Every change to the table, the banks, the graph
  section and the values goes through the calls that exist (`gs.land`,
  `Bindings.add` / `bind` / `replace_owner` / `add_modifier` /
  `set_macros`, `bank.add`, `lib.restore`). No new write path onto a
  `Param`, no new path onto the table. A spawn, a group, an ungroup, a
  "wire as saved" are each **one undo step** (`undo.push(label,
  load=True)` before the first write).
- **No file is written by a spawn.** The preset's dirty dot lights; a
  save writes it. Saving a patch writes `<library>/patches/<slug>.json`
  and nothing else. `bindings.json` is never touched by this plan.
- **Dylan's files.** `apc40.py`, `midi.py`, `bindings.default.json`, the
  desk diagram and `ui_desk*.py` are untouched (D8).
- **Style.** Match the surrounding code: docstrings in the repo's voice,
  comments that cite the plan (`# plan 40 T<n>: …`), no new dependencies.
  New modules are leaves like `graphmigrate.py`: pure data in, pure data
  out, nothing imported from the app.
- **Before reporting DONE:** `uv run ruff check` clean on the files you
  touched; the fast tier passing; `uv run pytest -q --all -m golden`
  passing with nothing re-recorded. Report the numbers. The controller
  runs the full suite once before the final review.
- **Commits.** One or more per task, each message ending with the
  attribution lines the session gives you. Never push, merge or rebase.
  Never dispatch subagents.

## Numbers (assigned now so the docs task never collides)

| | |
|---|---|
| register rows | 471–495 (plan 38 ends at 470; plan 39 holds 440–459) |
| hand checks | 394–401, group **AK** (plan 39's AJ ends at 393) |

A task that needs more rows takes them after 495 and says so in its
report.

## Task 0: the word (D1)

Goal: `patch` means the owner's thing and nothing else.

1. `git mv hyperspace/patch.py hyperspace/modgraph.py`. In `routing.py`
   and `graphview.py`: `from . import patch as patchmod` → `from . import
   modgraph`; `patchmod.` → `modgraph.`; `Router.build_patch` →
   `build_modgraph`, `Router.patch` → `Router.modgraph`,
   `router.patch_notes` → `modgraph_notes`; every caller and every test
   (`grep -rn "patchmod\|build_patch\|patch_notes\|\.patch\b"`). The
   module docstring's first line becomes "The modulation graph as data,
   and the order it is evaluated in" with a note that the file was
   `patch.py` until plan 40. `hotreload.MODULES` if it lists the module.
2. The word "patched" on a node's summary ("n params · k patched") and
   `PATCHED_TIP` stay: the same sense.
3. `ARCHITECTURE.md`, `ENGINEERING.md`, `DECISIONS.md` and the plan 28
   docs: the symbol names only (a sed, checked by eye); no prose rewritten.
4. Proof: the fast tier passes unchanged in count; `grep -rn
   "patch\.py\|patchmod"` over `hyperspace/` and `tests/` is empty.

## Task 1: the patch as data (spec P1, D5)

Goal: `hyperspace/patches.py`, a pure leaf, can cut a patch out of a
loaded preset's parts and work out what spawning it into another would
add — and the library can list, read and write patch files.

1. **The file kind.** `library.py`: `PATCHES = "patches"` beside `DESK`,
   `PATCH_SCHEMA = "hyperspace.patch/1"`, a `DocKind` for it (`load` is
   never called through the group door — a patch is not loaded, it is
   spawned — so it raises `LibraryError("a patch is spawned, not
   loaded")`; `document` and `signature` are not used either; the kind
   exists so `list`, `path_of`, `read`, `save_as`, `hide`, `rename`,
   the trash and the cloud conflict copies work for the folder as they do
   for presets). `Library.read_patch(name) → dict` validates the schema
   and the shape (`patches.check`); `Library.save_patch(doc) → Path`
   writes through `_write_text` (atomic), trashing an old text as
   `save_as` does; the factory folder `hyperspace/library/patches/` may
   not exist (as `desk/` may not).
2. **`patches.read(doc) → Patch`.** `Patch` is a frozen dataclass: the
   fragment's `nodes`, `wires`, `values`, `modifiers`, `routes`, `desk`,
   `macros`, `lfos`, `envs`, `layout`, the `ports` list, and the two
   classified boundary lists — `rig_rows` (every route or desk row whose
   source scheme is not the patch's own: `mod:`, `lfo:`, `env:` of its
   own ids, or a macro of its own) and `host_ports` (every `ports` entry;
   plus every route whose target is not a patch param, every macro base
   subscriber onto one, every modifier input from a lane that is not the
   patch's — these three are **derived** from the fragment, so `ports`
   in the file holds only the picture / geometry / mask ports). A port
   entry: `{"id", "type", "to" | "from", "was"}`; `type` in
   `graph.PORT_TYPES`. `patches.check(doc) → list[str]` returns the
   refusals in words (a frame singleton named in `nodes`, an output, a
   cloud, a camera, a media channel as a node, a port of an unknown
   type, a wire to a node the patch lacks that no port covers).
3. **`patches.lift(spec, table, reg, layout, node_ids) → dict`.** From
   the loaded preset's parts (`GraphSpec`, `Bindings`, the registry's
   snapshot of its performance groups, the GRAPH `layout`) and a set of
   canvas node ids (`render:acid.2`, `mod.3`, `lfo.5`, `macro.2`):
   refuse what the spec's P1 refuses (return the refusals; the caller
   says them and lifts the rest), rename members to the lowest ids
   (`acid.2` → `acid` if no other acid is in the patch, else `acid`,
   `acid.2` in the patch's order; `mod.3` → `mod.1`; `lfo.5` → `lfo.1`;
   `macro.2` stays `macro.2` — macros keep their number, eight exist),
   rewrite every id in values, wires, routes, desk rows, modifier inputs,
   subscribers and layout, rebase the layout to the top-left member at
   `(0, 0)`, classify every cable that crosses the edge: a render wire
   from a non-member into a member → an inlet port (`was` the source's
   name), from a member into a non-member → an outlet port; a route or
   desk row from a rig scheme → kept as a `rig_row` verbatim; a route
   from a non-member lane (`lfo:0` of a host LFO) → a modifier input or
   route kept with its source as is (a host port, derived); a route from
   a member lane onto a non-member param → kept (a host port, derived).
   `values` holds only the members' params (D5). Returns the file's
   dict with `schema`, `name`, `note` empty.
4. **`patches.spawn(doc, host, at) → Landing`.** `host` is a small
   read-only view the caller builds (`patches.Host`: the host spec's
   node names, `fx.hold`'s instance names, the table's modifier ids and
   their `next_id` rule, each bank's `next_id`, the macros in use, the
   preset-layer desk rows by control, `Bindings.owner` for every param,
   the registry's param ids). `Landing` holds: `renames` (`{"acid":
   "acid.2", "mod.1": "mod.7", "lfo.1": "lfo.6"}`), the rewritten `nodes`,
   `wires`, `values`, `modifiers`, `routes`, `desk`, `macros`, `lfos`,
   `envs`, the `layout` moved to `at`, the `group` entry (P2), the
   `ports` with their `to` / `from` renamed, the **conflicts** (each a
   `Conflict(kind, control_or_source, host_target, patch_target, row)`:
   a desk control the host maps; a performer source that owns a host
   param; a patch route onto a host param another performer owns), the
   **wants** (the rig-side sources by scheme, for P4 to word), and the
   `notes` (a macro with no free number: "macro.2: no free macro — its
   subscribers not spawned"; a port whose `was` the host lacks is not a
   note, it is an open pin). Pure: it writes nothing.
5. **Tests** (`tests/test_patches.py`, no GL, no imgui): `check` refuses
   each refusable thing in words; `read` classifies a hand-written doc
   (the spec's example) into the right `rig_rows` and `host_ports`;
   `lift` of `warp`, `doublevision`, `fractals` out of `party-noita`'s
   landed parts (`tests/test_graph_free.py` shows how a factory preset's
   parts are landed headless) gives one inlet (`was: "scene"`), one outlet
   (`was: "tripcolour.image"`), the three effects' values and no others,
   the desk rows on those effects' params verbatim; `spawn` into a host
   that already holds `warp` renames to `warp.2` and rewrites every
   reference; the **round trip** — `read(lift(spawn(p)))` equals
   `read(p)` up to the renames and the origin — over the spec's example
   and over a patch cut from every factory preset's main run; a spawn
   with K1 already mapped lists one conflict and lands nothing; a patch
   with `macro.2` into a host using all eight is a note, the rest spawned;
   `Library.save_patch` then `read_patch` is the same dict; a bad schema
   is a `LibraryError`.

## Task 2: the group node (spec P2, D4, D7)

Goal: a preset can hold groups; GRAPH draws a group as one node, folded
by default, opens it in place, makes one from a selection and takes one
apart. The renderer never hears the word.

1. **In the preset.** `preset.GROUPS_KEY = "groups"`: a list of
   `{"id": "group.<n>", "name", "patch"?, "nodes": [canvas ids],
   "open": bool}`. `Presets.document` writes it after `layout` when it
   is non-empty; `load_doc` reads it at step 6½ with `layout`, dropping a
   member id the graph does not hold (a note: "group acid wash: acid.3 is
   not in the preset — left out") and an empty group; `signature` covers
   it; `Marks.take` / `put` carry it for undo. The schema number per D7:
   if 37B's `/8` is on `main`, this is `/9`; else `/8`. `graphmigrate`
   gains the one-line step ("the key is absent → no groups"); the factory
   presets and the library are **not** rewritten (an absent key is the
   same preset). A preset without `groups` saves byte for byte as before.
2. **The model.** `graphview.VGroup` (id, name, members: the `VNode`s,
   open, the bounding rect of its members' positions, the boundary: the
   host-port pins — one per render cable crossing the edge, typed — and
   the boundary params — one per member param that a rig row or a
   crossing route lands on). `graphview.build` makes them from
   `preset.groups` after the nodes; `View.groups`. A member node of a
   **collapsed** group is not drawn (`drawn_node` false; `hidden_ids`
   adds them) and every cable with both ends inside is not drawn; a cable
   with one end inside is re-ended at the group node's pin for that
   boundary entry (the model says which pin, as `VBundle` re-ends a
   collapsed node's value cables today). An **open** group draws every
   member and cable as if there were no group, plus a region.
3. **The drawing.** `ui_graph._group_node`: a node like a collapsed
   render node — the title line (name, `+`), the pins down its sides by
   type (`COLOURS`), one row per boundary param with its cable, the
   status line from P4 when T4 is in (an empty string until then), and,
   when plan 37A's thumbnails are on `main`, the thumbnail of the last
   picture outlet's source (one name added to the want list; nothing if
   37A is absent). `ui_graph._region`: when open, a titled, tinted
   rectangle (`imgui.get_window_draw_list().add_rect_filled` under the
   nodes, the editor's background layer) round the members' rects with
   `GAP` of margin, the name in the title bar, `-` on it. Dragging the
   title bar moves every member by the same delta (one undo step, the
   positions in `layout`). A member dragged so its rect leaves the region
   leaves the group (**ungroup one**): its id taken from the list, the
   region shrinks. `preset_only` keeps drawing a group, open or folded.
4. **The verbs.** Right-click on the canvas with ≥ 2 nodes selected
   (`ed.get_selected_nodes`) → **Group**: `patches.check`'s rule applied
   to the selection (`graphview.Edit.group(ids) → (group, refusals)`),
   the refused named in the head's note ("scene is the frame's; left
   out"), the group made with a default name ("group 3"), folded. The
   group's right-click menu: **Open** / **Fold**, **Rename…** (an input
   on the side pane), **Ungroup** (`Edit.ungroup(id)`: the list entry
   removed, nothing else). Each one undo step through `_land`'s
   `undo.push(load=True)`. The side pane for a selected group: its name
   (editable), its members as chips (a click selects the member and opens
   the group), its boundary in words, its provenance ("from patch acid
   wash") and, in T3, the **save as patch** / **update patch** / **wire
   as saved** chips.
5. **Tests** (`tests/test_graph_groups.py`, headless as
   `test_graph_legible` does it, plus pure ones in `test_patches.py`):
   a preset with `groups` round-trips through `document` / `load_doc`;
   a member the graph lacks is dropped with a note; `signature` changes
   when a group is made; **the proof**: `graph.build_graph` of a grouped
   preset's section has the same `graph.signature` as its ungrouped
   twin, and `tools/golden_frames.py` draws every golden byte-identical
   with every factory preset's main run grouped; a folded group hides its
   members and internal cables and re-ends the crossing ones at its pins;
   open draws them all; Group from a selection refuses `scene` and keeps
   the rest; Ungroup leaves every node and cable where it was; a group
   made, then ⌘Z, is gone and the preset's signature is back; a drag of
   the title moves every member; a member dragged out leaves the group;
   a preset from before this plan saves byte for byte.

## Task 3: save, browse, spawn (spec P3, D2, D3, D9)

Goal: a group becomes a file, a file becomes a group in any preset, with
the conflicts asked first and nothing attached by itself.

1. **Save as patch.** The group's menu and side pane: **Save as patch…**
   opens a name / note input on the side pane; **Save** runs
   `patches.lift` over the loaded parts (`Presets` exposes `parts()` for
   it: the spec, the table, the registry snapshot, the layout) and
   `Library.save_patch`; the group's `patch` is set to the slug (the
   preset's dirty dot lights for that one field). A group with a `patch`
   slug shows **Update patch** (the same, over the existing file) and the
   name is prefilled. A refusal from `lift` (the group holds something it
   should not — it cannot, Group refused it, but a hand-edited file can)
   is said on the head and nothing is written.
2. **The browser.** `ui_graph._patches_chip`: a **patches** chip on the
   GRAPH head beside **new** opens a popup list (`Library.list(PATCHES)`:
   factory then the user's, hidden out, as the PRESETS list; each line
   the name, the note in `text_disabled`, and the boundary in words from
   `patches.read`: "in: picture · out: picture · wants: K1, right hand y,
   band 1" — the words for a rig row are `graphview.cable_words`'s). A
   click spawns at the canvas's centre (4 below). Each line is also a
   drag source (`imgui.begin_drag_drop_source`) carrying the slug; the
   canvas's cables accept the drop (`_cable` becomes a drop target when a
   patch is being dragged and its type matches the patch's one inlet and
   one outlet) and splice (4 below). The canvas's right-click menu gains
   **Spawn ▸** with the same list (spawn at the click). The PRESETS page
   gains a **patches** fold where "more · module presets" is, listing
   the same with **×** to hide / trash and **rename** as presets have
   (`ui_presets` reuses its own rows); no spawn from there.
3. **The conflict sheet.** `ui_routing.modal` grows a second question
   kind: `panel.spawn_question = (landing, choices: dict[int, str],
   on_spawn, on_cancel)`, drawn by the same modal (its `PROMPT` popup,
   `PROMPT_W` wider for it, `SHEET_W`), ahead of the Replace / Keep
   question. The sheet: a title ("spawn acid wash into party-acid"), one
   row per `Landing.conflicts` — the control or source in words, then two
   radio chips **the patch: `fx.acid.2.speed`** / **the preset:
   `view.bright`** — every row preselected to the patch (D9); under them
   a **keep all existing** button (flips every row to the preset) and
   **take all** (back); then the wants, one line per device role the rig
   lacks, from `devices.wants` when T4 is in (else from `Landing.wants`
   by scheme: "waits for hand: right hand y"); then **Spawn** / **Cancel**.
   While the sheet is up the hands learn nothing (`Learn.pending`-style:
   `Learn.hold()` if there is no such thing, a flag the hands completer
   checks). With no conflicts the sheet is not shown and the spawn lands
   at once.
4. **The landing.** `ui_graph.spawn(panel, slug, at, splice=None)`:
   `Library.read_patch`, `patches.spawn` over a `Host` built from the
   live parts, then — if conflicts — the sheet, else straight on — one
   `undo.push("spawn <name>", load=True)`, then in this order: the
   section re-read with the patch's nodes and internal wires added and
   landed (`gs.land`), so their params exist; `bank.add(n)` for each
   voice; `add_modifier` for each modifier; `lib.restore(values)`; for
   each route: `Bindings.add`, or `replace_owner` where the sheet chose
   the patch, or nothing where it chose the preset (the row is kept in
   the group's `kept_by_host` list and said on the node: "K1 kept by the
   preset"); for each desk row: `bind(write=False)` (the same choice);
   `set_macros` with the merged subscribers; the `groups` entry and the
   `layout` entries at `at`; `redraw_serial` bumped. **Splice** (a drop on
   a cable `a → b.port`): the same, then the cable removed and `a →
   <inlet's to>` and `<outlet's from> → b.port` added in the same landing
   (`graphview.render_insert`'s shape). The **wire as saved** chip on the
   side pane of a group with open pins: for each port whose `was` names a
   node the host has, with that port free, `render_add` the cable; refuse
   in words otherwise ("scene.cover is taken"); one undo step; the chip
   disappears when no port is open. **Nothing else is attached.**
5. **Tests** (`test_graph_groups.py`, `test_patches.py`, `test_ui_routing`
   for the sheet): save as patch from a group writes the spec's shape and
   `Library.list(PATCHES)` shows it; spawning `acid-wash` (a fixture
   under `tests/fixtures/patches/`, added with `git add -f`) into
   `party-trip` lands `acid.2`, `wobble.2`, `delay.2`, `mod.<n>`, the K1
   row, the hand row and the group, the pins open, nothing wired to the
   scene; one ⌘Z removes all of it and the signature is back; splice on
   `scene → warp.image` makes the run `scene → acid.2 → wobble.2 →
   delay.2 → warp` (`graph.run_of`); **wire as saved** on the open-pin
   group lands `scene → acid.2.image` and `delay.2 → output.all.image`
   and refuses a taken port in words; a spawn whose K1 collides opens the
   sheet (`st["modal"]`), **keep all existing** + Spawn lands the patch's
   K1 row dormant and said, Cancel lands nothing; the hands learn nothing
   while the sheet is up; a second spawn of the same patch makes `.3` ids
   and a second group; the PRESETS fold lists patches and hides one; no
   file but the patch's is written by any of it (`tmp_path` diffed).

## Task 4: what the preset wants, and the arrival (spec P4)

Goal: the app says which devices the loaded preset wants and lacks, and
says it when one arrives. Independent of T2 and T3; may land first.

1. **`devices.wants(table, registry) → list[Want]`** in `devices.py`:
   `Want(role, state, scheme, rows)` where `state` ∈ `connected`, `lost`,
   `off`, `missing` ("not in this rig"), one per device role the loaded
   preset's performer routes, preset-layer desk rows and modifier inputs
   name. The role: a row's `@role` qualifier; else for `cc:` / `note:` /
   `pitch:` the registry's primary MIDI role (`DeviceRegistry.midi_roles`,
   `primaries`); else `SCHEME_ROLE` — **moved from `graphview` to
   `devices`** (`graphview` imports it from there; the placeholder node
   keeps its words). `rows` in words (`graphview.cable_words` is a
   canvas function; the words for a row live in `routing.row_words`
   — write it there, have `cable_words` call it). `wants` never names a
   scheme that is built in (`lane`, `lfo`, `env`, `seq`, `mod`). Pure
   over the table and the registry's `lines()`; tested with a bare
   registry and a `[[devices]]` list.
2. **The status-change event.** `DeviceRegistry.poll`: after each device's
   poll, compare `d.status` to `self._status.get(d.role)`; on a change
   store it, call `_changed()` once for the frame, and call
   `self.said(role, before, after)` — a hook the app sets to
   `lib.say(...)` with the words "apc40 connected — 6 controls live" /
   "apc40 lost — 6 controls wait" / "leap off" (the count from `wants`
   for that role; "controls" for a MIDI desk, "rows" otherwise). A device
   whose `open()` finally succeeds says the same through the existing
   `_changed` path. The MIDI relight, the feeds and the placeholder's
   replacement are unchanged; prove in a test that a `MidiDevice` going
   lost → connected fires the listeners once and the hook once.
3. **Where it shows.** The group node's status line and hover (T2's
   empty string becomes "waits for apc40 (lost): K1, K2 · leap (not in
   this rig): right hand y", from the wants whose rows land on the group's
   members); the GRAPH head: a chip **N devices missing** (hover: the
   same lines for the whole preset; absent when every want is connected);
   the PRESET strip's load line gets the same chip; the SYSTEM page: one
   line per wanted role the rig lacks under the device lines ("wanted by
   the preset: leap — not in this rig; 3 rows wait"). A spawn's notes line
   says "2 rows wait for leap" (T3 reads `Landing.wants` through
   `devices.wants` when both are in).
4. **Tests** (`tests/test_device_wants.py`): a preset wanting `hand:`
   rows on a rig without a hands device → one `Want("leap", "missing",
   …)` with three rows in words; with the device listed but `enabled =
   false` → `off`; with it listed and `lost` → `lost`; a `cc@launch:`
   row with no `launch` device → `missing` for `launch`, not for the
   primary; the chip's text and the SYSTEM lines (headless); the hook
   fires once per change with the counts; nothing fires when nothing
   changed over 100 frames.

## Task 5: the fx module presets retired (spec P5, D6, D10)

Goal: the six fx module presets, their fold entry and their load hook are
gone; the FX page is untouched; no preset or golden moves.

1. `git rm hyperspace/library/fx/*.json`; `Presets._watch_fx_modules`,
   `_fx_module` and `graphmigrate.module_runs` removed with their tests
   (`grep -rn "module_runs\|_fx_module\|fx module" tests/`); `FX_GROUP`
   stays as the group's name where it is used for other things;
   `Library.defaults("fx")` is the fresh values (no default module);
   `DEFAULT_NAMES` loses `fx` if it names one. `ui_presets`'s "more ·
   module presets" fold lists no fx entry (the group has no folder: check
   `Library.groups()` does not list an empty one, or filter `fx`). A
   preset or show naming an fx module in `modules` keeps the label on
   load with no note and drops it on save (`Presets.document`'s `modules`
   skips a group with no module presets; `NO_MODULE` gains `fx`).
2. `ui_fx.py` is **not** touched (D10).
3. Tests: every factory preset loads with no note; `tools/golden_frames.py`
   byte-identical; the fold has no fx entry (headless); a preset with
   `"modules": {"fx": "trip"}` loads quietly and saves without it; the
   repo has no `library/fx/` and no test imports what went.

## Task 6: docs

- This spec's "What changed in the build" (as plan 36's), with any
  ruling the controller made and a register row for each (rows 471–495;
  D1–D10 first as "owner — 2026-10-27", then the rulings).
- `ARCHITECTURE.md` §3: a "Patches and groups" subsection beside the
  desk templates (the file, the boundary rule, the doors a spawn goes
  through, the conflict sheet, `devices.wants` and the arrival); §4's
  module table: `patches.py`, `modgraph.py`; `DECISIONS.md` "Presets and
  the desk": the rows for D1–D10 in the owner's words; `ENGINEERING.md`'s
  GRAPH section: the group node; `plans/README.md`'s entry; `SETUP.md`:
  `<library>/patches/` and `<machine>/ui.json`.
- Hand checks: the spec's eight, written into `11-hand-checks.md` as
  group AK, 394–401.
- Test counts in the spec header; `CHECKPOINT.md`'s line.

## Order

T0 first, alone (a rename touching three files and the docs; everything
after it cuts from the branch with it in). Then T1 and T4 in parallel
(T4 touches `devices.py`, `routing.row_words`, the SYSTEM page and the
head's chip; T1 touches `patches.py` and `library.py`). T2 after T1. T3
after T2 (and reads T4's `wants` if it is in; else `Landing.wants`). T5
in parallel with any of T1–T3 (it touches `preset.py`'s module hooks,
`library.py`'s defaults, `ui_presets.py`; T1's `library.py` change is a
new kind beside the old — merge is mechanical). T6 last, after a
reviewer sub-agent has read T1–T5's diff against the spec's decisions
and the global constraints and its findings are fixed in place.
