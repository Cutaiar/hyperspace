# Dillon's PRs #214 and #223 against the integration stack and plan 32

Read-only analysis, 2026-10-23. "Stack" = `origin/plan-28-30-integration` (plans 24/26/27/28/30 + main @ fec80ee).
"Plan 32" = `d580d06` on top of the stack. Conflicted trees from `git merge-tree --write-tree <ours> <theirs>`.

Short answer: **every textual conflict in both PRs is superficial** (union them). The one real design question is not
in a conflict hunk at all. It is a silent semantic clash in #223: the venue overlay meets plan 27's `[[devices]]` list and
its live config watch. There is also a numbering collision (decision rows, L-items, hand checks) that git cannot see.

---

## PR #214 `origin/subjects-flow-logo`: Flow mark as a vector subject

Merge base with the stack: `419c292` (plan 28 spike #211). The PR touches geometry.py (two shapes appended at
indices 99/100, a `flat` geom flag, builder-given face UVs `FUV`), render.py (6 lines), tests and docs.

### Conflict hunks

| # | file:line | kind | resolution |
|---|---|---|---|
| 1 | `hyperspace/render.py:2306` (stack tree `66cbf3a`); `:2608` (plan-32 tree `0326c9c`) | **superficial**, misplaced by git | The stack side is empty because git anchored the hunk at the wrong spot (the end of `_copies_of`, before `class _PanPx`). **The code did not move.** The depth-cue block (`near, far = pd.min(), pd.max()` / `span = …` / `edepth` / painter `order`) is still in the scene draw, at stack `render.py:1950–1954` (plan 32 `render.py:2252`), now after the plan 26 camera/`shape_world` setup. Resolution: drop the conflict block entirely (do not keep the PR's duplicated `near/span/E/edepth/order` lines there) and insert only the PR's 6 new lines (`if g.get("flat"): near, span = far - 2.0, 2.0` and its comment) right after `span = max(far - near, 1e-6)` at stack 1951 / plan 32 2253. `g` is in scope there, and the alpha `t = (edepth[order] - near) / span` that follows still reads `near`/`span`, so the fix has the same effect. |

Auto-merged and checked: geometry.py, test_render.py, test_ui_desk.py, test_golden.py, ENGINEERING.md (V/E rows 100/101 land),
golden `shape_digests.json`, plan 28 doc.

### Silent clashes: none found

Checks made:
- **Shape indices.** The stack and plan 32 append no shapes (`SHAPES` count 99 on both), so the Flow shapes take
  99/100 as the PR assumes. `test_golden` merges to `== 101`. `view.shape` names, the Shape menu and the UI are all
  built from `SHAPES` at runtime. No test hard-codes index 99 except the one the PR already fixed (`test_a_controls_text`).
- **Depth cue.** The only `pd.min()/pd.max()` cue on the stack and plan 32 is the one above. field.py's and ghost.py's
  `near, far` are different cues (lattice z, hand tubes) and need nothing.
- **`flat` name overlap.** The stack's `shape_world(…, flat=held)` means "the 3D switch holds it". The PR's
  `g["flat"]` means "a plane figure". They are different things that only share a name. Flow mark is `dims=3`, so
  `is_3d` → `view_depth`, the case the PR's comment assumes.
- **Face UVs.** `face_uvs()` is unchanged on the stack, and its only caller (stack `render.py:2064`, plan 32 `:2366`)
  is the face texture path that plan 32's media bitmaps also use. So a media channel on the Flow mark's faces shows
  "one picture across the five bars", as the PR intends. That works in its favour.
- **Frame goldens** (`test_golden_frames.py`, 596 frames) do not iterate shapes. Adding shapes moves no golden.
  `test_shape_renders` parametrises over `SHAPES` and skips the vertex-pixel assert for `curve`, which both new
  shapes set.

Watch item (not a clash today): shape indices are identity ("appended: index is identity"). Any other open PR that
appends shapes (none found on the stack or plan 32) would collide on 99/100, and the later PR renumbers.

**#214 tally: 1 superficial / 0 conceptual / 0 silent.**

---

## PR #223 `origin/venues`: one venue per place, `<library>/venues/<name>.toml` laid over `config.toml`

Merge base with the stack: `cdd6364` (#206, managed Python 3.14). The PR adds `config.load(path, venue=)` with
`_venue_data` and `_layer` (a table-by-table `dict.update`, where a list key such as `[[output.screens]]` is replaced
whole), `--venue`/`--no-venue`, `<home>/last_venue`, named screens (`placement.named/match`, resolved in
`app._slots`/`_windows`), and a venue picker on the SYSTEM page.

### Conflict hunks vs the stack (tree `09f9d14`)

| # | file:line | kind | resolution |
|---|---|---|---|
| 1 | `hyperspace/config.py:412–708` | superficial | Both sides added top-level functions before `load()`. Stack: `_kind_defaults`/`_midi_role`/`_device`/`_translate`/`_daw`/`_devices`/`devices`/`read_devices`. Venues: `venue_*`/`last_venue`/`remember_venue`/`_venue_data`/`_layer`. Keep both sets, then a single `def load(path=None, venue="")` with the venues body. The tail after the hunk already merged correctly (`if section == "devices": continue` sits inside the venue-layered `data` loop). Git did exactly this union in the plan-32 merge (no conflict there), so copy that shape. |
| 2 | `hyperspace/app.py:136–175` | superficial | Keep the stack's `_destroy_windows` and the venues' `_without_venue`. The `_restart` signature takes the stack's `windows=()`. The body merged clean: venues only changed a comment, and `os.execv(…, sys.argv)` is unchanged, which the picker relies on. |
| 3 | `hyperspace/app.py:1331–1336` | superficial | Take the venues' two new lines (`panel.venue`, `panel.venues`). **Drop** its `panel.config_notes = cfg.get("notes", [])`: the stack sets `panel.config_notes = cfg["notes"]` a few lines below as a *shared* list that the device registry appends to. `home` is in scope. |
| 4 | `tests/test_config.py:270` | superficial | Keep both test blocks: plan 27 B1 `[[devices]]` tests and the venue tests. No venue test asserts an exact `notes` list that the plan 27 translation notes would break. |
| 5 | `tests/test_app_boundary.py:16` | superficial | `from hyperspace import app, config, devices`. |
| 6 | `docs/SETUP.md:188` (hands/leapc paragraph) | superficial | Take the stack's longer paragraph (Gemini 5/6, `LEAPC_*` overrides, "on a device list … the `leap` entry"). Apply the venues' wording fix: "3.12" becomes "this project's Python", twice, since #206 moved to 3.14 and the stack's text still says 3.12. |
| 7 | `docs/SETUP.md:281` | superficial | Keep both paragraphs: the stack's "hands show on every output…" and the venues' "Name the screen rather than numbering it…". |
| 8 | `docs/DECISION-REGISTER.md:111` (index table) | superficial in text, **needs renumbering** (see S1) | Venues' rows `110`/`111` collide with the stack's `110 SAVE…`/`111 two-handed save`. Append as new rows after the last one. |
| 9 | `docs/DECISION-REGISTER.md:1671` (bodies) | same | Append the venues' `### 110`/`### 111` bodies after the stack's last body, renumbered. |
| 10 | `docs/TESTING-GUIDE.md:193` (L-index table) | same | The venues' `L69 … check 144` collides with the stack's L69 and check 144 (`F1` Xbox pad). Renumber. The L69 body auto-merged and has to be renamed to match. |

### Additional / changed hunks vs plan 32 (tree `8fe2f11`)

config.py **auto-merges** here, the same union as hunk 1. The doc and test hunks are the same as above, with
plan 32's media tests in `test_config.py:270` and its media tests and `MediaResolver`/`MediaIO`/`_open_media`
classes in `app.py:157`. All of them are unions. One new hunk:

| # | file:line | kind | resolution |
|---|---|---|---|
| P1 | `hyperspace/app.py:319–327` (`_slots`) | superficial | Combine both: `monitor=placement.index(e["monitor"], screens=scr)` (venues) **and** plan 32's `window=…, syphon=…, ndi=…` kwargs. Plan 32's `_windows` already calls `_slots(cfg, scr)` after the auto-merge, and publish-only slots skip placement, so a named `monitor` on a `window = false` output is resolved but never used. That is harmless. |

### Conceptual clash (design, outside any hunk)

**C1. The venue overlay versus plan 27's device list and its live watch.** Venues was written against the old
`[midi]`/`[gamepad]`/`[hands]`/`[bridge]` tables. On the stack:
- `_layer` lays a venue's tables on *before* `_devices` runs, so a venue's values are read like config.toml's.
  - A venue `[[devices]]` **replaces the whole list**: list keys are replaced, not merged.
  - A venue `[hands]`/`[midi]` table is merged key by key and translated, **but only if config.toml has no
    `[[devices]]`**. If it has one, the venue's table is ignored with a "[[devices]] is listed, so [hands] is ignored"
    note.
  - Relative `map`/`calibration`/`tape` paths in a venue's entries resolve against config.toml's folder (the home),
    not the venue's folder.
- **The live watch drops the venue.** `DeviceRegistry.watch()` (devices.py:1662) re-reads only `config.toml` on an
  mtime change, through `config.read_devices(path)`, which calls `load(path)` **with no venue**. So with a venue that
  sets devices, any edit to config.toml mid-show silently reverts the device list to config.toml's: devices close and
  reopen. Edits to the venue file itself are never watched (venues documents "edit, then ⌘R", which still works).

The venues design intent (decision text: "what changes between places is the screens; `[hands]`, `[library]` and the
rest do not") never needed devices. So the clash only bites if a venue is allowed to touch them. Plan 32 makes that
tempting: the NDI entry's `extra_ips` (senders on another subnet) is the one device key that really is per place.

- **Recommendation (a):** a venue may not set `devices` or the old device tables (`midi`, `gamepad`, `hands`, `bridge`).
  `_venue_data` drops them with a note, exactly as it already drops `[library]`. This is one line in
  `_venue_data` plus a test. It matches the venues' own stated scope, keeps the plan 27 watch correct, and leaves
  `extra_ips` in config.toml, where listing every venue's sender IPs at once is harmless because the list is additive.
- **(b), later, if a per-place device ever matters:** thread the venue into `read_devices` and the registry (watch
  both files' mtimes, call `load(path, venue)`), and decide whether a venue's `[[devices]]` replaces the list or
  overlays entries by `role`. That is a bigger design and not needed now.
- **Owner:** Dillon decides the venue scope (his PR's intent). Dan or the plan 27 side confirms the watch stays
  config.toml-only.

### Silent clashes (auto-merged, or invisible to git)

- **S1. Numbering collisions.**
  - Decision rows 110/111 are taken on the stack (SAVE), and plan 32 runs to row 339.
  - Hand check 144 is the stack's (F1 Xbox pad, inside 144–218), and plan 32 uses checks through 316.
  - L69 is taken (the stack has L-items to L138, plan 32 to L145).
  - Venues cites "decision 110/111" in **15 places in code and tests**, all of which auto-merge and would then point at
    the SAVE rows:
    - app.py ×2, config.py ×3, placement.py ×2, ui.py ×2
    - test_app_boundary ×1, test_config ×2, test_placement ×2, test_ui_shell ×1
  - Resolution: renumber to the next free numbers where it lands. On top of plan 32 that is rows **340/341**, **L146**,
    check **317**. Plan 31 (#230, checks 280–295) is still open too, so whichever lands last takes the next free
    numbers. Update every citation, including the venue L-item body that auto-merged.
- **S2. SYSTEM page height.** `test_the_system_page_fits_with_the_picker_open` asserts that SYSTEM and OUTPUT do not
  scroll with the picker open. Since the base, the stack added device-list lines to SYSTEM, and plan 32 adds
  Syphon/NDI publish lines (fps, readback ms). Neither side's suite covers that combination. Run the test after
  merging, and if SYSTEM now scrolls, shorten the picker (one line until something is picked).
- **S3. Plan 32 keys a venue may want: they work with no code.**
  - `[output] syphon`/`ndi`/`window` and the per-entry `syphon`/`ndi`/`window` in `[[output.screens]]` are ordinary
    `[output]` keys, so a venue sets them through `_layer` like any screen key. A per-place publish name ("td" at
    the club) is supported for free.
  - One edge to document: if config.toml uses `[[output.screens]]`, a venue's scalar `[output] syphon` is ignored with
    plan 32's "[[output.screens]] is listed, so [output] syphon is ignored" note. Output 1's entry decides, so the
    venue has to restate the screens list. That follows from replacing the list whole.
  - Recommend one sentence in SETUP's venue section: "a venue may also set an output's `syphon`/`ndi` names and
    `window`".
  - **Media folders:** derived from `[library] path` + `<home>` (`app._open_media`). A venue cannot set
    `[library]`, so media folders are deliberately not per venue. That is consistent and needs no change.
  - **NDI `extra_ips`:** a `[[devices]]` key, so it falls under C1. Keep it in config.toml.
- **S4. The plan 27 SETUP text sits next to the venues' text.** The venue section says "[hands] … do not" change and
  does not mention `[[devices]]`. Once C1 is decided, add a line: "a venue cannot set `[[devices]]` (or the old device
  tables); config.toml says which devices there are".

### Found in passing: bugs inside #223 itself, not clashes (for Dillon)

- The docs still say the picker is on the **OUTPUT** page (SETUP "The OUTPUT page has a picker…", decision 110 body
  "The OUTPUT page picks one"). Commit `df14e07` moved it to SYSTEM, where the code and tests have it.
- ENGINEERING.md: the "Command line:" table and the named-screen paragraph were inserted *inside* the environment
  variable table. The `--no-venue` row ended up after the paragraph, and `PYGLFW_LIBRARY`/`LEAPSDK_INSTALL_LOCATION`
  are now orphaned under the flag table.
- `load()` computes `venue_root(base, home)` from the **raw** `[library] path`, with `~` expanded but no
  relative-to-config resolution. `app.main` computes `panel.venues` from the **resolved** one. With a relative
  `[library] path`, the venue that is read and the picker's list come from different folders.
- The test names still say "rig" (`test_a_rig_is_laid_over…`). This is cosmetic, after the "rig" → "venue" rename.

**#223 tally vs the stack: 10 superficial / 1 conceptual (C1, outside the hunks) / 4 silent (S1–S4).** Plan 32 adds
1 more superficial hunk (P1), and config.py auto-merges there.

---

## Decisions needed

| # | decision | recommendation | owner |
|---|---|---|---|
| D1 | Can a venue set devices (`[[devices]]`, `[midi]`/`[gamepad]`/`[hands]`/`[bridge]`)? | **No for now.** Drop them in `_venue_data` with a note, as `[library]` already is, and leave NDI `extra_ips` in config.toml. Revisit with a venue-aware `read_devices`/watch only if a per-place device is ever wanted. | Dillon (venue scope); Dan to confirm for plan 27/32 |
| D2 | Merge order and numbering: venues before or after plan 32 and plan 31? | Whichever lands last renumbers. On top of plan 32: rows 340/341, L146, check 317, plus the 15 code/test citations. | Dan (stack owner), Dillon applies |
| D3 | Venue-settable plan 32 output keys (`syphon`/`ndi`/`window`) | Allow (they already work) and document the one-liner in SETUP. | Dillon |
| — | #214 | Nothing to decide. Re-apply the 6-line `flat` cue at stack render.py:1951 / plan 32 :2253 and drop the misplaced block. | Dillon (or whoever merges) |
