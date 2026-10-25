# N5 — controllers as nodes; the APC40 as two nodes (plan 28, stream N)

You are the implementer of work package **N5**. Read first, in full:
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your rules and your
first three git commands: fetch `origin plan-28-30-integration`, `git reset --hard
FETCH_HEAD` (if the classifier refuses it, `git merge --ff-only FETCH_HEAD` from a
clean tree), `git branch -m plan-28-n5-controllers`; one plain git command per shell
call). Your base must be the SHA in your dispatch or later (N2 and N3 merged).

Then, in your worktree under `hyperspace-python/`:
- `docs/plans/28-30-orchestrator-prompt.md` lines 279–345 (stream N today), 477–575
  (N2, N3 — built; what you extend), **629–666 (your section N5)**, 673–763
  (decision 12 above all: the APC40 is two nodes, *APC40* and *APC40 (SHIFT)*, no
  layer view; D1, D4–D6, D12 hold; invariant controls on *APC40* only; the faders
  and the APC40's map and feel are Dylan's and untouched), 745–763 (out of scope:
  the desk), 764–839, 840–900.
- `docs/plans/28-node-editor.md` §6; `docs/plans/27-device-registry.md` (the
  registry, `Device.layers`, the hands device's port groups `dance`/`switches`);
  `docs/DECISIONS.md` "Presets and the desk" (D1–D12) and "Inputs and devices".
- N2's and N3's decisions and reports in `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/`
  and `.../reports/` — N2's `device_node` function, port ids, the `View` model, the
  collapse state; N3's `Edit` requests (template-override edits go through them).
- `hyperspace/graphview.py`, `hyperspace/ui_graph.py`, `hyperspace/devices.py`
  (`Device`, `Base`, `MidiDevice.layers`, `sources`, port groups, the registry's open
  devices, roles, status), `hyperspace/hands/device.py` (port groups — read only;
  `tests/test_hands_boundary.py` must stay green), `hyperspace/routing.py`
  (`Binding.layer`, `is_session_row`, the `@role` qualifier, a row's scheme/role,
  desk templates: how a preset's `desk` = template + overrides is held and written),
  `hyperspace/preset.py` (`_desk_part`, the template expansion), `hyperspace/midi.py`
  and `hyperspace/apc40.py` **read-only** (the latch state of SHIFT — `MidiIO`'s
  layer that is up — read through the registry; the invariant rows: SHIFT, the
  crossfader, the bank pads, transport, tap; which controls are which), the desk
  templates under `hyperspace/library/` (read-only; nothing under `library/` changes).

Build exactly what N5's section says — **presentation only**: nothing in `apc40.py`
or `midi.py` changes, no row moves, no home changes.
- A device with `layers` is one node per layer: *APC40* (the rows with `layer ==
  "preset"` and the invariant rows) and *APC40 (SHIFT)* (the rows with `layer ==
  "global"`), each port lit while its layer is up (`MidiIO`'s latch state read
  through the registry), each cable drawn from the node its row belongs to; the
  invariant controls are ports on *APC40* only. Register the two nodes' port groups
  (knobs, faders, buttons, …) as your decision.
- Desk templates as subgraphs: a preset whose `desk` is a template plus overrides
  draws the template as one collapsed node whose ports are its mapped controls;
  expanded, its rows show as cables; an edit inside writes the preset's overrides
  through the same table methods (N3's `Edit`), never the template file.
- Roles, not serials: a cable from a device this rig lacks (a row's `@role` or a
  scheme with no open device) draws from a grey placeholder node named by role, its
  cables dormant, as ROUTING shows a dormant row.
- The hands device node's port groups: axes, pinches, dance, grab, from
  `hands/device.py`'s groups.
- `hyperspace/devices.py` only if `layers` needs exposing on `Base`.

Tests (`tests/test_graphview_devices.py`): `test_the_apc40_is_two_nodes_and_each_row_hangs_off_its_layers_node`,
`test_invariant_controls_are_ports_on_the_first_node_only`,
`test_a_templated_desk_is_one_collapsed_node_whose_edits_write_overrides`,
`test_a_missing_role_is_a_grey_placeholder_with_dormant_cables`, and the hands node's
groups. In the PR body: `git diff --stat origin/plan-28-30-integration --
hyperspace/apc40.py hyperspace/midi.py hyperspace/library/` (must be empty). Goldens
unmoved. Base gates in your dispatch.

Decisions (the port groups, the placeholder's look, how the SHIFT latch is read,
the template node's collapsed ports) as register-row drafts into
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N5.md` with hand-check drafts
(Y.n: the APC40 as two nodes with the real desk, SHIFT latched and released; a
SHIFT-layer cable in `bindings.json`, a preset-layer one in the preset) and
as-built notes; report to `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/N5-report.md`.

PR: `gh pr create --base plan-28-30-integration` titled `Plan 28 N5: controllers as
nodes, the APC40 as two nodes, templates as subgraphs`. Reply with the short contract.
