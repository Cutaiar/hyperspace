# T1 report — the patch as data (plan 40 P1, D5)

**Status: DONE_WITH_CONCERNS** (concerns below are judgement calls, not failures).
Base confirmed: `51106e1` (Merge PR #269, T0). Branch `plan-40-t1`, commit `6677797`.
PR: https://github.com/Cutaiar/hyperspace/pull/274 (into `plan-40-build`, not merged).

## What I built

- `hyperspace/patches.py` (new, 1155 lines, a leaf: imports only `graph`, `modifiers`,
  `routing`):
  - `check(doc) → list[str]`: the schema and every key's shape; refusals in words for a frame
    singleton (`scene`, `hands`, `lookback.2` …), an output, the camera, a cloud, a media
    channel (as an entry or a wire), a port of an unknown type / onto no member / without
    `was`, a wire to a node the patch lacks that no port covers, a value of a host param (D5),
    a modifier's param in `values`, a lane envelope 1–5, a copy without its original, a row
    that touches nothing of the patch's, a desk row that is not MIDI, a bad macro id.
  - `read(doc) → Patch` (frozen): the fragment in canonical order (nodes by name, wires and
    ports sorted, modifier entries in full, rows in their order) and the two boundary lists:
    `rig_rows` (source not the patch's own and not a modulation lane) and `host_ports` (the
    file's ports, then `{"id": "value.<k>", "type": "value", to|from, was, row?}` for each
    member lane → host param route, host lane → member route, member macro base on a host
    param, modifier input from a host lane).
  - `lift(spec, table, values, layout, node_ids) → (doc, refused)`.
  - `Host` (+ `Host.of(spec, table, banks, params, held)`), `spawn(doc, host, at, *, patch)
    → Landing`, `Conflict(kind, control_or_source, host_target, patch_target, row, host_row)`.
  - helpers: `entry_name`, `held_words`, `spec_names`, `slug` (library's rule, tested equal),
    `is_rig_source`.
- `hyperspace/library.py` (beside the existing kinds): `PATCHES`, `PATCH_SCHEMA`,
  `PATCH_SPAWNED`, `_patch_kind()` registered in `Library.__init__`, `read_patch`,
  `save_patch`; `HIDEABLE = (PRESETS, PATCHES)` with `_read_hidden` / `hidden` /
  `_write_hidden` / `hide` / `unhide` / `rename` widened (the patches' stems under
  `hidden.json`'s `"patches"`, written only when non-empty; rename skips the show repoint for
  a patch). Nothing in T5's regions (`defaults`, `DEFAULT_NAMES`) touched.
- `hyperspace/hotreload.py`: `"patches"` after `"routing"` in `MODULES` (outside my file list:
  `test_every_package_module_but_the_cold_core_is_watched` fails without it; `library`'s
  `from . import patches` is a bare module import, no ordering constraint).
- `tests/test_patches.py` (new, 41 tests), `tests/fixtures/patches/acid-wash.json` (force-added).
- `tests/test_library.py`, `tests/test_ui_routing.py`: one assertion each, `lib.kinds ==
  ("patches", "presets")`.

## Where the spec and the build differ, and why

1. **`mod:1`, not `mod:0`, in the example.** `mod.1`'s lane is `mod:1`
   (`Modifier.address`); `mod:0` is no lane. Fixture fixed; T3's brief names the file.
2. **Envelopes are `env.6`+ in a patch file**, not `env.1` — "lowest as if alone" in a preset
   where 1–5 always exist, and so "lane envelopes 1–5 refused by identity" holds in `check`.
3. **`lift` returns `(doc, refused)`** and takes the performance snapshot (a dict) as its third
   argument (the dispatch: "the registry's snapshot of its performance groups").
4. **The factory "main run"** is `graph.run_back(spec, "output.all.image")`: in a `/7` wired
   frame `run_of(spec)` (frame → fx.image) is always `()`. 16 presets have no run and are
   named in the test (`NO_RUN`); 9 round-trip (dial — 12 effects —, hands-fx, hands-pinch,
   lfo-breathe, party-acid, party-mandala, party-noita, party-trip, seq-demo).
5. **`hide` / `rename` needed new code** (the dispatch expected none): `hide` and `rename` were
   presets-only. Widened minimally (see decisions 476x).
6. **The round trip includes "wire as saved"**: `read(lift(spawn(p)))` only equals `read(p)` if
   the spawned ports are attached again (the landing leaves them open pins, D2). The test's
   `land` helper wires each port to its `was` (an outlet taking over the port it went into),
   which is what P3's chip does.
7. `Landing.renames` holds only ids that moved (the example's map is of moved ids).

## How I tested

```
uv run pytest -q tests/test_patches.py                     41 passed
uv run pytest -q                                           4163 passed, 2 skipped in 21.23s  (base 4122 + 41)
uv run ruff check hyperspace/patches.py hyperspace/library.py hyperspace/hotreload.py \
  tests/test_patches.py tests/test_library.py tests/test_ui_routing.py    All checks passed!
uv run pytest -q --all -m golden                           136 passed in 31.45s  (nothing re-recorded)
uv run pytest -q --all                                     1 failed, 4384 passed, 2 skipped in 55.12s
  FAILED tests/test_media_publish.py::test_ndi_out_never_blocks (0.0584 < 0.05, timing under -n auto)
uv run pytest -q --all -n0 tests/test_media_publish.py::test_ndi_out_never_blocks   1 passed
```

What the tests prove: `check` refuses 16 refusable things by their exact words; `read`
classifies the example (rig rows = the lane route and K1's row, verbatim; host ports = `in`,
`out`) and derives the four value-port kinds; `lift` of warp/doublevision/fractals out of
party-noita gives the inlet `was: scene`, the outlet `was: tripcolour.image`, exactly the three
effects' values, their 6 desk rows and 5 hand routes verbatim; a lift naming scene / output.all
/ camera / seq / env.2 / device:apc40 refuses each in words and keeps warp; renames to the
lowest ids with every reference (values, wires, routes incl. lanes, desk, modifier inputs,
macro base + depth subscribers, layout rebased); spawn into party-noita renames to `.2`
everywhere and lists the desk and hand conflicts; acid-wash into party-noita lists exactly one
conflict (K1) and leaves the host table untouched; host modifier/bank/macro rules (`mod.7`,
`lfo.6`, `env.6`, `macro.3`, `acid.3`); macro with no free number → the note, the rest
spawned; full bank → a note; a patch twice collides with itself (K1, the hand); a route onto an
owned host param is a target conflict; the round trip over the example in three hosts and
over every factory main run; the library lists, hides (`hidden.json` exact), unhides, renames,
deletes, saves (trash on change, none on the same text), reads, refuses a bad schema / a bad
shape / no name, and refuses `load`. Leaf import walk; `RIG_NODES` agrees with
`graphview.spec_name`'s `NOT_REMOVABLE`; `_kind` agrees with `graphview.kind_of`.

## Files changed

```
hyperspace-python/hyperspace/patches.py                  (new)
hyperspace-python/hyperspace/library.py
hyperspace-python/hyperspace/hotreload.py                (one word)
hyperspace-python/tests/test_patches.py                  (new)
hyperspace-python/tests/fixtures/patches/acid-wash.json  (new, force-added)
hyperspace-python/tests/test_library.py                  (one assertion)
hyperspace-python/tests/test_ui_routing.py               (one assertion)
```
`docs/plans/40-patches.md` untouched; no golden, preset or `bindings.json` touched.

## Self-review findings

- `Conflict` field names follow the build plan; for the "target" kind `control_or_source` is
  the contested param and `host_target` / `patch_target` are the two *sources* — documented in
  the class docstring; T3 should word it from `kind`. I added `host_row` (the host's colliding
  row) so T3 can apply a "keep existing" choice without searching again.
- Spawning a cut back into its own preset lists every shared hand axis as a conflict
  (one-axis-one-param) — correct by the rule, but noisy; owner may want hands relaxed.
- `wants` does not include a row's `when` gate source; `Host.params` is carried, unused.
- `lift` cannot verify an `lfo.N` / `env.N` id exists (no banks passed); T3 passes only ids the
  canvas drew. A `mod.N` not in the table is refused.
- An extra hands entry's `laid` is dropped at lift (a second `laid` makes the host unreadable).
- `patches.py` is ~1155 lines against the spec's ~500 estimate (docstrings and `check`).

## Concerns

1. The `hide` / `rename` widening touches library code beyond "a new kind beside the old"
   (`_read_hidden`, `hidden`, `_write_hidden`, `hide`, `unhide`, `rename`) — far from T5's
   `defaults` region, so the merge should still be mechanical.
2. `lib.kinds` now includes `"patches"`: anything that iterates kinds expecting only loadable
   ones would see it. I checked every use (`Project._apply`/`follow`, `ui_presets`,
   `ui_routing`, `defaults`, `reset`, `is_dirty`, `poll`) — all skip or never reach a patch.
3. The one full-suite failure is a known-style timing flake (NDI publish, 58 ms vs 50 ms under
   load), not one of the two named in common.md; passes serially.

## Rulings made

See `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t1.md`: 471x–479x (example lane,
envelopes from 6, macro-in-use rule, one-owner schemes per scheme, lift's return, hidden
patches, port ids / `was`, hands `laid`, copies), hand-check drafts AK.1–AK.4, as-built notes.

---

# Fix report (review of PR #274) — commit 4ac3a1d

**Important 1 (D2, no hidden edge).** `check` now refuses every `wires` entry with an end
outside the patch, a port or not: "wire scene → acid.image crosses the edge: a port says it"
(the rig's own ends — an output, a channel, the camera, a cloud — keep their own words).
`spawn` emits only wires with both ends members, whatever the file says. Tests:
`test_a_wire_across_the_edge_is_refused_even_where_a_port_says_it` (the inverted test) and
`test_spawn_lands_only_the_patchs_own_wires` (a file with `scene → acid.image` and
`delay → output.all.image`, check skipped: `Landing.wires` is the two internal wires, every
end inside the spawned members).

**Important 2 (a voice that does not spawn).** `_Renamer.gone`: a lane of a member that did
not spawn resolves to None, never its old number. A modifier input on it is left empty and
said ("mod.2: its input 2 read lfo.1, which did not spawn — left empty"); depth and base
subscribers naming it are dropped (`_sub_dropped`); its values and rows stay out as before.
`test_a_full_bank_is_a_note_and_its_lane_reads_nothing` asserts no `lfo:0` route, input or
subscriber survives, the input is `None`, and the note names it.

**Minors.**
- (a) `Host.of` without banks starts one past every voice id the table names (row sources and
  `when`s, modifier inputs, depth subscribers) and past the defaults (LFOs 1–4, envelopes 1–5)
  — `test_host_of_without_banks_starts_past_every_voice_the_table_names`.
- (b) `modbank.MAX_ID`: `Host.of` gives a bank whose `next_id()` is past it no room; `spawn`
  also refuses an id past it with a note — `test_used_up_voice_ids_are_a_note`.
- (c) decisions 474x and AK.1 now say plainly that a one-owner source read through a modifier
  (acid-wash's `smooth` on `hand:right.y`) is no conflict even where the host's axis owns a
  param — the spec's D3 example — for the owner to rule on.
- (d) 474x says the lowest free instance can wake a host's dormant rows on a removed instance's
  params (as `_new_instance`); the `spawn` docstring says it too.
- (e) `spawn` keeps only members' values — `test_spawn_lands_only_the_members_values`.
- (f) `Host.params` and `Host.of`'s `params` argument removed (nothing needs registry ids: a
  route onto a param the host lacks lands dormant, no conflict).

`patches.py` now also imports `modbank`, `lfo`, `envelope` (leaves, for `MAX`, `MAX_ID`, the
LFO default and `LANE_ENVS`); the leaf test still passes.

**Gates.**
```
uv run pytest -q tests/test_patches.py        45 passed
uv run pytest -q                              4167 passed, 2 skipped in 26.03s  (base 4122 + 45)
uv run ruff check hyperspace/patches.py hyperspace/library.py tests/test_patches.py   All checks passed!
uv run pytest -q --all -m golden              136 passed in 9.47s
```
