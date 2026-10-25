# N5 report — controllers as nodes; the APC40 as two nodes

**Status:** DONE_WITH_CONCERNS (one rough edge, left out of `Edit` by instruction; see Concerns)

- **Base:** `d94115e` (confirmed with `git log --oneline -1` after `merge --ff-only origin/plan-28-30-integration`). `origin/plan-28-30-integration` at 2a3599c (D3, docs only) was merged in before the PR.
- **Branch:** `plan-28-n5-controllers`.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/220 (into `plan-28-30-integration`).

## Commits
- `f6af833` The APC40 is two nodes, a desk template a subgraph, a missing role a placeholder
- `822aaf6` Merge remote-tracking branch 'origin/plan-28-30-integration' into plan-28-n5-controllers

## What was built
- **`graphview.device_nodes(d, table)`.** A device whose `layers` has two or more entries becomes one node per layer:
  - `device:<role>` ("apc40"): every control, the invariant ones first in an `invariant` group;
  - `device:<role>/global` ("apc40 (SHIFT)"): every control but the invariant ones, with pins `out:<addr>|global`.
- **`build` places each desk row on its node** (`row_pin`): an invariant row on the first node, a global-layer row on the SHIFT node, a preset-layer row on the first node. The exception is a preset-layer row that is still the loaded template's, which goes on the template node, with `inside` set to that node.
- **Placeholders.** A row from a role the rig lacks draws from a grey placeholder `device:<role>`.
- **The latch.** `refresh` reads `Bindings.layer_of(role)` each frame and sets the nodes' and ports' `up`. A cable from a down layer is dormant.
- **The template node.** `template:<name>` (kind `template`, column 0, preset layout): its ports are the template's controls.
- **The hands' groups.** `switches` is split into `pinches` / `grab`.
- **`ui_graph`.**
  - `template_of(panel)` hands `build` the template rows as the load read them.
  - A subgraph node starts collapsed; its **+** opens it (`is_open`, `toggle_open`, `drawn_cable`, with the open set kept in `st["open"]` by `setdefault`).
  - A down layer is drawn faint; an up layer's ports are drawn bright.
- **Untouched:** `Edit`, `CREATE`, `DELETE`, `DELETE_NODE`, `_state`, `devices.py`, `apc40.py`, `midi.py`, `library/`.

## Tests
`tests/test_graphview_devices.py` (6):
- `test_the_apc40_is_two_nodes_and_each_row_hangs_off_its_layers_node`
- `test_invariant_controls_are_ports_on_the_first_node_only`
- `test_a_templated_desk_is_one_collapsed_node_whose_edits_write_overrides`, which:
  - uses the plan 24 C3 fixture;
  - draws the page headless and checks collapsed / opened;
  - deletes a template row, connects a template port to a base, saves, and checks the dark row and the override in the file, with the template's bytes unchanged.
- `test_a_factory_preset_draws_no_template_node`
- `test_a_missing_role_is_a_grey_placeholder_with_dormant_cables`
- `test_the_hands_node_groups_axes_pinches_grab_and_dance` (on the real `HandsDevice` over the rig's `HandsIO`)

One assertion was changed in `tests/test_graphview.py` (hands group `switches` → `pinches`), as N5's section asks.

## Gates (after the merge)
```
uv run pytest -q                                   2349 passed, 2 skipped in 188.74s (0:03:08)
uv run ruff check .                                All checks passed!
uv run pytest tests/test_golden_frames.py -q       7 passed in 20.57s
git diff --stat origin/plan-28-30-integration -- hyperspace/apc40.py hyperspace/midi.py hyperspace/library/ tests/golden/   (empty)
```
No windowed smoke run: the dispatch did not ask for one.

## Files changed
- `hyperspace-python/hyperspace/graphview.py`
- `hyperspace-python/hyperspace/ui_graph.py`
- `hyperspace-python/tests/test_graphview.py`
- `hyperspace-python/tests/test_graphview_devices.py` (new)

## Self-review findings
- **Fixed while building.** N2's `source_pin` sent a qualified MIDI row with no such device (`cc@launch:…`) to the first desk's node. It now gets a `device:launch` placeholder.
- **Change from N2.** Device schemes with no listed device now draw from `device:<role>` placeholders, not `source:<scheme>`. Only the keys keep a `source:` node. No other test depended on this.
- **Cost.** `is_invariant` is called once per layout control (about 120) and once per layered row at rebuild only, never per frame.

## Concerns
1. **A drag from a SHIFT-node port onto a `base` stub, made while SHIFT is not latched,** goes through the desk learn. That lands a preset-layer row, so its cable appears on *apc40*. The fix is about 3 lines in `Edit._value_refusal`: refuse a source port whose `layer == "global"` as the session's. It was not built because the dispatch kept N5 out of `Edit`. With SHIFT latched, the learn's own refusal already applies.
2. **`ui_graph.template_of` reads `Presets._at_load` (private)** so that it agrees with `_desk_part`. It falls back to `lib.desk_template`. A public accessor on `Presets` would be cleaner, but `preset.py` was outside the brief.
3. **A collapsed template's target params show patched `base` stubs with no visible cable.**
4. **A placeholder desk (no MIDI device listed) is one node,** not two: with no device, its layers are unknown.

Decisions, hand checks Y.10–Y.12 and as-built notes: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N5.md`.

## Fix round 1 (review of PR #220, head 822aaf6)

**Commits:**
- `04d9add` Review: N5 round 1 — a SHIFT-node drag is refused, shadowed rows on the first node
- `ce328db` Merge of `origin/plan-28-30-integration` at d600397 (N4). No conflicts; both sides kept.

**What changed**

- **IMPORTANT 1 (D5).** In `Edit._value_refusal`'s `base` branch, a MIDI source whose port has `layer == GLOBAL_LAYER` (a SHIFT-node port) is now refused, whatever the latch.
  - The check runs before `learnmod.blocked`.
  - The words are `SHIFT_NODE`: "<addr> on the SHIFT node is the session's (bindings.json): map it on ROUTING".
  - `refusal` and `connect` share this path, so the hover and the drop agree.
  - Test: `test_a_drag_from_the_shift_node_into_base_is_refused_whatever_the_latch`.
    - With `desk.shift` False and then True, `connect` returns a `Refusal`, `refusal` gives the same words, and `table.bindings` is unchanged.
    - The same control from *apc40* still has no refusal.
- **Minor 1.** `preset.Presets.template_at_load()` is a new public accessor. `ui_graph.template_of` now calls it and catches only `LibraryError`.
- **Minor 2.** New `ui_graph.hidden_by(st, view, pin)`. Hovering a pin whose cables are inside a collapsed template now says "set by desk template <name> (collapsed: + shows it)". The template test asserts three things:
  - the line is there while the template is collapsed;
  - it is absent on an override's stub;
  - it is gone once the template is opened.
- **Minor 3.** Written into the roles row's rough edge in the decisions file.
- **Minor 4.** I chose to move the row. A layered row on an invariant control (shadowed, D6) now leaves that control's port on *apc40*, in the `invariant` group. So the SHIFT node never carries an invariant control.
  - Test: `test_a_shadowed_layered_row_leaves_the_invariant_port_on_the_first_node`.

**Gates (after the N4 merge)**
```
uv run pytest -q                                2368 passed, 2 skipped in 170.06s (0:02:50)
uv run ruff check .                             All checks passed!
uv run pytest tests/test_golden_frames.py -q    7 passed in 20.39s
git diff --stat origin/plan-28-30-integration -- hyperspace/apc40.py hyperspace/midi.py hyperspace/library/ tests/golden/   (empty)
```
Both golden tests pass: the completeness test (596 states) and the byte-for-byte frame test. Nothing under `tests/golden/` differs from the integration branch.

**Concerns now:** #1 and #2 above are fixed, and #4's placeholder is described in the decisions row. Only #3 remains, as a rough edge: there is still no cable while a template is collapsed, but the hover now names the template.
