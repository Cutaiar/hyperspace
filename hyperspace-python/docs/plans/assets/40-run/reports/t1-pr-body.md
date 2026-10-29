## What was built

- **`hyperspace/patches.py`**, a pure leaf (imports `graph`, `modifiers`, `routing` only; a test walks the imports):
  - `check(doc)` — the refusals in words: a frame singleton, an output / `output.all`, the camera or a cloud, a media channel, a look-back, a port of an unknown type or onto no member, a wire to a node the patch lacks that no port covers, a value of a host param (D5), a lane envelope 1–5, a copy without its original.
  - `read(doc) → Patch` — the fragment (canonical order) and its boundary: `rig_rows` (routes / desk rows whose source is not the patch's own — open-ended, as `is_continuous` is) and `host_ports` (the file's picture ports, plus the value crossings derived from the rows: member lane → host param, host lane → member, member macro base → host param, modifier input from a host lane).
  - `lift(spec, table, values, layout, node_ids) → (doc, refused)` — renames to the lowest ids (`acid.2` → `acid`, `mod.3` → `mod.1`, `lfo.5` → `lfo.1`, envelopes from `env.6`, macros keep their number), rewrites every reference, rebases the layout, classifies every crossing cable.
  - `spawn(doc, host, at) → Landing` — renames by the host's rules (lowest free instance, modifier next id, bank high-water, free macro), the group entry (no `id`: T2 numbers groups), ports renamed, **conflicts** (desk / source / target) for P3's sheet, **wants** by scheme head for P4, **notes** (no free macro, full bank). Writes nothing. `Host.of(spec, table, banks, params, held)` builds the view from the live parts.
- **`library.py`**: `PATCHES`, `PATCH_SCHEMA = "hyperspace.patch/1"`, a `DocKind` whose `load` / `document` / `signature` refuse ("a patch is spawned, not loaded"), `read_patch` (schema + `patches.check`), `save_patch` (atomic, old text to the trash, nothing else written). `hide` / `unhide` / `rename` widened to the patches' group (`hidden.json` gains `"patches"` only when one is hidden). No factory `patches/` folder ships.
- `hotreload.MODULES`: `patches` after `routing` (one word; the every-module test requires it).

## Boundary assertions consciously changed

- `tests/test_library.py::test_presets_are_the_librarys_one_document_kind` and `tests/test_ui_routing.py::test_the_old_routing_presets_step_load_save_as_presets`: `lib.kinds == ("patches", "presets")` — the patches' kind is a registered document kind that is never loaded; presets stay the one loadable kind.

## Decisions taken (drafts in the controller's decisions file)

- The spec's example routes `mod:0` from `mod.1`; a modifier's lane is `mod:<n>`, so the fixture says `mod:1`.
- A patch's envelopes are `env.6`+ in the file too (lane envelopes 1–5 refused by identity).
- A macro is "in use" by a label, a subscriber or a row onto it — never by its value.
- One-owner sources: MIDI by `Binding.overlaps` (desk conflict); `hand:` / `axis:` by Learn's one-axis-one-param (source conflict); every other scheme none; any patch route onto an owned param is a target conflict.
- `lift` returns `(doc, refused)` and takes the performance snapshot, not the registry.
- The factory "main run" is `graph.run_back(spec, "output.all.image")` (in a `/7` wired frame `run_of` is always empty); 16 presets have none and are named in the test, 9 round-trip.

## Fixtures force-added

- `tests/fixtures/patches/acid-wash.json` (force-added: `tests/fixtures/` is gitignored) — the spec's P1 example (`acid`, `wobble` are factory effects).

## Gates

```
uv run pytest -q                      4163 passed, 2 skipped   (base 4122 + 41 new)
uv run ruff check <touched files>     All checks passed!
uv run pytest -q --all -m golden      136 passed               (nothing re-recorded)
uv run pytest -q --all                4384 passed, 2 skipped, 1 failed — test_media_publish.py::test_ndi_out_never_blocks (0.058 s < 0.05 under -n auto); passes serially
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_012HeFHywoiCGN2SbvC1U35W
