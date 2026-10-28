# T1 review — PR #274 (`plan-40-t1` @ 6677797, diff `51106e1...origin/plan-40-t1`)

### Spec compliance
❌ issues — one requirement (D2 / the plan 36 rule) is broken by a path `check` lets through; the rest matches P1, D5 and Task 1.

- ❌ **D2 / no hidden edge: a wire a port "covers" is landed by `spawn` as a real wire.** `check` (patches.py:659-665) accepts a `wires` entry whose far end is not a member as long as a port with the same `to`/`was` (or `from`/`was`) exists, and `test_a_wire_a_port_covers_is_no_refusal` (test_patches.py:217) locks that in. `read` keeps the wire in `Patch.wires`, and `spawn` lands every one (patches.py:1087). I probed it: acid-wash plus `scene → acid.image` and `delay → output.all.image` passes `check` with `[]`, and `spawn` into a host holding `acid` returns `wires` containing `{'from': 'scene', 'to': 'acid.2.image'}` and `{'from': 'delay', 'to': 'output.all.image'}`. So the saved names get attached automatically, which D2 rules out. `lift` never writes such a wire, but a hand-written file or a factory patch can. Details under Important 1.
- ⚠️ **Judgement: four places where the build departs from the spec, all acceptable.**
  - `mod:1` in the example: correct. `Modifier.address` is `mod:<n>` for `mod.<n>`, and `_lane("mod:0")` is None.
  - Envelopes in the file start at `env.6`: this matches "lane envelopes 1–5 by identity" and ARCHITECTURE §3.3, and `check` refuses `envs` 1–5 in words.
  - `lift` returns `(doc, refused)`: this matches the build plan's "return the refusals; the caller … lifts the rest".
  - The main run is `run_back(spec, "output.all.image")`: confirmed that `graph.run_of` reads `frame → … → fx.image`, which a `/7` wired frame does not have. The 16 skipped presets are named (`NO_RUN`) and the test asserts that set exactly.
- ⚠️ **Outside the brief's file list, all declared and justified in decisions 476x and the report.**
  - `library.py` goes beyond "a new kind beside the old": `HIDEABLE`, `_read_hidden`, `hidden`, `_write_hidden`, `hide`, `unhide` and `rename` were widened. The brief's assumption that "hide/rename work with no new code" was false; the code was presets-only.
  - `hotreload.MODULES` gets one word. Without it `test_every_package_module_but_the_cold_core_is_watched` fails.
  - `test_library.py` and `test_ui_routing.py` each get one `lib.kinds` assertion, updated rather than weakened.
  - None of this touches T4's or T5's regions.
- ✅ **Binding constraints.**
  - Untouched: `graph.py`, `render.py`, the goldens, `frame-signatures.json`, Dylan's files, every preset, `docs/plans/40-*.md` and every docs-owned file.
  - No `groups` key is written anywhere.
  - `Landing.group` has no `id`, and the docstring says T2 numbers groups.
  - `save_patch` writes only `<home>/patches/<slug>.json`: atomic `_write_text`, a different old text goes to the trash first.
  - `spawn` is pure: the host table is unchanged, and the test asserts it.
- ✅ **Doubt (1), the classifier is open.** `rig_rows` is "source is not a `mod:`/`lfo:`/`env:` lane" (`_lane(src) is None`), so it is not a list of schemes. `cc@apc40:…` and `axis@p2:…` fall to rig because their head is not a lane head. A lane of an id the patch does not hold becomes a derived value port (patches.py:547-555). No `macro:` source scheme exists in `routing`, so "a macro of its own" has nothing to classify.
- ✅ **Doubt (2), every id is renamed, in both `lift` and `spawn`.**
  - Values, wires and ports (`to`/`from`) are renamed.
  - Routes and desk rows: source lane, target param and the `when` lane.
  - Modifier `id` and `in`; macro subscribers' `base` and `depth.source`/`depth.target`.
  - Layout and the group's canvas ids.
  - `scale` cannot name a member: routing's migration (routing.py:1413-1427) leaves only session ids.
- ✅ **Doubt (3), the rename map does not collide**, with one gap under Important 2.
  - Render nodes take the lowest free instance over `host.names ∪ held`, which is `_new_instance`'s rule (graphview.py:3988). For a host with `acid` and `acid.2`, `acid` becomes `acid.3` (tested).
  - Modifiers take `modifiers.next_id`.
  - Voices take the bank's `next_id`, envelopes clamped to ≥ 6.
  - A macro keeps its number when free, else takes the lowest free one. A chained case cannot reuse a number because `used` grows as it goes.
  - With no macro free: the note is written and the macro's subscribers, value and rows stay out.
- ✅ **Doubt (4), conflicts.**
  - Desk: `Binding.overlaps` against `Bindings.desk()`, which is the preset layer only. The qualifier is respected because `overlaps` compares `device`.
  - Source: `hand`/`axis`, exact string match, onto a different param.
  - Target: `Host.owner` equals `Bindings.owner` (routing.py:2036, enabled performer).
  - Each `Conflict` carries the patch row and the host row, so the caller can apply either choice.
- ✅ **Doubt (5), D5.** `lift` keeps only `members.owns(pid)` values, and `check` refuses a host param's value in words.
- ✅ **Doubt (6), the round trip.** It is `read(lift(land(spawn(p))))` against `read(p)`, field by field. It runs over the example in three hosts and over 9 factory runs, and names the skipped ones.
- ✅ **Doubt (7), the leaf.** `patches` imports `graph`, `modifiers` and `routing` only; `library` imports `patches`. An AST walk tests this.
- ✅ **Doubt (8), the library.**
  - `read_patch` checks schema and shape and raises `LibraryError`.
  - `save_patch` is atomic and trashes a changed old text.
  - An old `hidden.json` with no `"patches"` key still reads: `doc.get(PATCHES, [])`.
  - The `"patches"` key is written only when non-empty.
  - The `lib.kinds`/`groups()` growth is harmless at the sites I checked:
    - `Project` skips `_kinds`;
    - `is_dirty` sees `_loaded` empty, so not dirty;
    - `defaults` returns `{}`;
    - `ui_presets.py:983` filters by `OVERVIEW_GROUPS`.
- ✅ **Doubt (9), the refusals.** `held_words` uses `G.FRAME_KINDS` directly. `RIG_NODES` is tested against `graphview.spec_name`'s `NOT_REMOVABLE` refusal and `_kind` against `graphview.kind_of`, without importing graphview into `patches`.

### Strengths
- The boundary is classified at `read`, as P1 asks, so it is not stored twice. The value ports (member lane to host param, host lane to member, member macro base on a host param, modifier input from a host lane) are derived and tested by exact tuples.
- The rename runs through one `_Renamer`, used by both `lift` and `spawn`. The prefix-ownership rule (`fx.acid.2.mix` is never `acid`'s) is right and exercised.
- The tests mostly derive their expectations independently. The noita lift compares against the preset file's own values, desk rows and routes. Conflicts and wants are compared as whole tuples or dicts, and refusals by their exact words.
- The decisions file gives a register row for each choice the task made (471x–479x), names the one-owner rule scheme by scheme, and has hand-check drafts AK.1–AK.4.

### Issues
#### Critical (must fix)
None.

#### Important (should fix)
1. **patches.py:1087 with check at 652-669, and test_patches.py:217: a crossing wire in the file is landed as an automatic attachment.**
   - What happens: `check` lets a wire with a non-member end through when a port covers it, `read` keeps it in `wires`, and `spawn` hands it to P3 as a wire to land. The probe output is above.
   - Why it matters: this is the "port whose `was` is attached automatically" that D2 and plan 36 forbid. It also drops a second wire into `output.all.image` next to the host's own.
   - Fix: in `check`, a wire must have both ends in the patch; a crossing is a port, and saying "`scene → acid.image` crosses the edge: a port says it" is enough. Invert the test so it asserts the refusal. If tolerance is preferred instead, `read` must drop such wires and `spawn` must never emit them.
2. **patches.py:1043-1056, 1089, 1092 and `_Renamer.lane` at 385-389: when a bank is full, a member voice that does not spawn leaves its lane address on modifier inputs and macro depth subscribers.**
   - What happens: `routes` and `desk` are filtered by `_names_dropped`, but `mods` and the macros' `depth` are not. `rn.lane` maps a gone member to its own number, so `lfo:0` stays `lfo:0` and silently reads the host's `lfo.1`.
   - Probe: a patch with `lfo.1`, and `mod.1` with `in: ["lfo:0"]`, spawned with `room={"lfo": 0}`, gives `modifiers[0]["in"] == ["lfo:0"]` together with the "bank is full" note.
   - The test misses it: `test_a_full_bank_is_a_note` (test_patches.py:473) asserts `r["source"] != "lfo:16"`, which cannot fail, because a gone voice is never renamed to 16.
   - Fix: lanes of gone voices should resolve to nothing. Blank or drop that modifier input and say it; drop depth subscribers that name a gone lane. Assert those in the test, and assert that no `lfo:0` row survives.

#### Minor
- **patches.py:917-921 and 1044: `Host.of(spec, table)` without `banks` collides.** `next_voice` is `{}`, so LFOs start at `lfo.1` and envelopes at `env.6` regardless of what the host holds. Make `banks` required, or fall back to one past the highest voice id in the table and spec. The tests build every `Host` this way, which is safe only because no factory run lifts a voice.
- **patches.py:921: `room` counts only `MAX - len(bank)`.** It ignores `modbank.MAX_ID` (`Bank.refusal`, modbank.py:147), so a bank whose high-water mark is near `MAX_ID` can be handed an id the bank will refuse. Use `next_id() > MAX_ID` as no room.
- **Decisions 474x: one-owner sources read through a modifier are never a conflict.** The rule is routes-only, so a `hand:`/`axis:` source read by a modifier input never produces a source conflict. Acid-wash's `smooth` on `hand:right.y`, spawned into party-noita where `hand:right.y` drives a param, yields no conflict. Spec D3 names "`hand:right.y` already owns a param" as its example. Say this explicitly in 474x (and AK.1) so the owner rules on it.
- **patches.py:1033-1040: reusing the lowest free instance revives dormant host rows.** When a host has dormant routes or desk rows left on a removed `acid.2`'s params, spawning `acid` as `acid.2` brings them back. A dormant desk row is neither a conflict nor said. This is consistent with `_new_instance`, so at most a sentence in 478x/474x.
- **patches.py:1088: `spawn` trusts its input for D5.** It keeps every value in the doc, relying on `check` upstream. A one-line `m.owns(k)` filter would make D5 hold for any caller.
- **library.py `_write_hidden`: an older build loses hidden patches.** An older build that rewrites `hidden.json` drops the `"patches"` key. This is harmless while both Macs update together; it is already noted in 476x.
- **patches.py:905: `Host.params` is carried but unused.** Already self-reported.

### Assessment
**Task quality:** Needs fixes. The module is careful and mostly right: the classifier, the renames, D5, the library kind and the round trip all hold. But a patch file can still make `spawn` attach crossing wires by their saved names (D2), and a full bank leaves member modifier inputs reading the host's voices. Both fixes are small and local, and each needs a test that can actually fail.
