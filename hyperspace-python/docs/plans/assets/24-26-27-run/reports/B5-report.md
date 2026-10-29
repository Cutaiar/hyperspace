# B5 report — Plan 27 B5: docs — the device registry as built

**Status:** DONE_WITH_CONCERNS (the concerns are findings in the code, not in the docs; below)
**Branch / base:** `plan-27-b5-docs`, cut from `plan-24-26-27-integration` at **606fcd9**
(Merge plan 24 C7, PR #186; B1–B4 and C7's docs on it), confirmed with `git log --oneline -1`
after the reset.
**Commit:** `3a02f0f` Plan 27 B5: docs — the device registry as built, register rows 140–168, hand checks W 168–190
**PR:** https://github.com/Cutaiar/hyperspace/pull/188
**No code changed** (docs only; no docstring or comment needed fixing for a doc to be true).

**Register rows: 140–168 (N = 168). Hand checks: group W, 168–190 (M = 190).** A5 continues
from row 169 and check 191 (group V).

## What I wrote

- `docs/plans/27-device-registry.md` (new): as built, by WP (B1 the protocol / registry /
  `[[devices]]` / SYSTEM lines; B2 several desks, profiles, the per-role latch, the pad and hands
  devices, schemes and wants from the registry; B3 sinks, the sink row, Learn sink, the bridge
  and `hands-daw`; B4 OSC, `PointCloud`, the cloud device) — At the machine / Code / Tests per
  part; "The block to paste" with the exact today's-rig block (verbatim from
  `tests/test_devices.py::TODAYS_RIG`), the hands-on variant, the OSC phone block and the cloud
  block (B4's), a second-desk entry; the translation table from the old tables; every kind's keys;
  not verified by a person; known rough edges; what was built otherwise than the prompt said.
- `docs/DECISION-REGISTER.md`: header ranges (rows 140–168 in plan 27; 110–168 on integration);
  `## The device registry (plan 27)` with rows 140–168 (29 rows: B1 7 → 140–146, B2 8 →
  147–154, B3 6 → 155–160, B4 8 → 161–168; B1's shim row merged with the hands-in-feed-slot
  note into 143 now that B2 replaced the shims); 29 answer-sheet lines. **Superseded rows: none.**
  No register row's text became wholly untrue with adapters as devices; row 60 ("Learn desk /
  Learn hand") got a "Changed in plan 27" bullet (what can be armed now comes from the registry;
  Learn <role>, Learn sink) and its answer-sheet line says so, the way row 61 was annotated for
  plan 24. Row 86 untouched, as instructed.
- `docs/DECISIONS.md`: Who-legend ranges; Platform: the DAW row rewritten (bridge and
  `hands-daw` as devices), new owner rows for decision 10 (the registry's shape), 10's
  done-when / "adding a device" (no edit to `app.py`), 16 (the core never imports `midi`,
  `bridge`, `dream`, `osc`, `torch`, `leap`; adapters only feed; hands liftable), and row-N rows
  140, 142–146; the control model: owner rows for 11 (roles), 12 (two input ports per param),
  13 (values and triggers), 14 (layers), row-N rows 141/150 and 155, "One path" / scene-setters /
  "Push is centred" reworded for devices; Learn: the "A Learn says what it waits for" row
  rewritten (`learn.WANTS` → `Learn.wants`, `DeviceRegistry.wants`; rows 60, 151), Learn sink
  (158), one knob per desk (154), "One road onto the desk" (every desk); "Inputs" became
  **"Inputs and devices"**: the APC40-profile row extended, several desks (owner + 149), the
  qualifier (147), SHIFT per desk (148), the pad device (152), the hands device (143, 153), the
  DAW sink (157), the bridge (156, 159, 160), OSC (owner + 161–164), point clouds (owner +
  165–168); the liftable-hands row and the hand-settings row reworded; `bindings.json` holds the
  sink rows. (DECISIONS has no "Adding a source" theme; the "Adding a source" paragraph is
  ARCHITECTURE §3.4's, rewritten there as "Adding a device", and DECISIONS got an owner row for it.)
- `docs/plans/11-hand-checks.md`: group **W, 168–190**, every draft check (B1 W.1–W.7, B2
  W.8–W.12, B3 W.13–W.17, B4 W.B4.1–5) renumbered in one sequence plus one new check the
  prompt's list required and no draft had (**175, the APC40 unplugged at launch and plugged in**,
  on `test_a_missing_desk_is_lost_its_rows_wait_and_it_comes_up_with_its_feedback`). Mapping:
  168 W.1, 169 W.2, 170 W.3, 171 W.4, 172 W.5, 173 W.6, 174 W.7, 175 new, 176 W.8, 177 W.9,
  178 W.10, 179 W.11, 180 W.12, 181 W.13, 182 W.14, 183 W.15, 184 W.16, 185 W.17, 186–190
  W.B4.1–5. The prompt's "at least" list: 175 (APC40 replug), 176 (generic desk learned onto a
  knob), 186 (phone on Wi-Fi), 182 (the bridge's send list as sink rows, seen in the DAW).
  "Before you start", the run order (item 7) and "What no test covers" updated. All 228 test
  nodes named in the plan-27 docs (W group, plan file, register section, ARCHITECTURE,
  ENGINEERING, DECISIONS) collect (`pytest --collect-only`, a script over the docs).
- `docs/TESTING-GUIDE.md`: Part 1 "The device list (on the copy)" L72–L76 (168, 173+174, 170,
  178, 190); FL Studio L77–L81 (181–185) and L46's bridge line brought up to date; Part 2 (a)
  A33 (175); (b) B37 (169, 180), B38 (172); (f) F5 (171, 179); new **(g) A second controller,
  a phone (OSC)** G1–G6 (176, 177, 186–189). Every W check is cited once. Summary table rows,
  "Before you start" (plan 27 entries on the integration branch; the device list is the one part
  of config.toml edited live), the risks box, the run order (item 10), "What a person has to
  judge", glossary (Device list, OSC, Sink, SYSTEM page).
- `docs/ARCHITECTURE.md` (device parts): §1 diagram (devices' rows / feeds, sinks), **Devices**
  row replacing "Input adapters", the Host row's gate list (`_open_devices`, `_open_dream` the
  one gate left), Learn and Library rows, the leaves (`generic`; `devices` imports lazily);
  §2 frame table renumbered to 16 steps (0–15) with the three device slots (2 poll, 8 feed,
  12 send) as `ORDER` has them, the one-frame-lag rule (sinks after apply are not a frame
  behind), a new "Devices poll / feed / send" rule, the guards; §3.3 scheme table (`axis:`,
  MIDI with the qualifier, `hand:`, `hands:`, `ext:`, `<role>:`), the sink row, "There is no
  fixed list of schemes" in place of the stale `LANE_SCHEMES` text; §3.4 "Adding a device" in
  place of "Adding a source"; §3.5 Learn (`Learn.wants` in place of the three-item `WANTS`,
  pad/OSC and sink completers); §3.7 rows (a second desk, OSC, Learn sink, the pad's camera job);
  §3.8 (sink rows, `sinks_seeded`, the `"profile"` key; the stale "nothing in the app edits a
  session row" fixed); §3.10 two bullets; §4 rows for `learn`, `midi`+`apc40`+`generic`,
  `hands/`, `config`, new `devices.py` and `osc.py`, `gamepad`+`bridge`, `app`; §5 the desk
  (several desks), new **Devices**, **Sinks**, **Point clouds**, Hands.
  **Two numerals in A5's drawing subsection changed** only because I renumbered the frame
  table: "the integrator (step 14)" → 13 and "as step 7 hands over the dim" → 5; also §3.6's
  "frame step 4" → 3 and §5 Undo's "frame step 5" → 4. Nothing else in the Graph row, §2's
  drawing subsection or §5's render parts was touched.
- `docs/ARCHITECTURE.html` (device parts): the §02 diagram's two input labels (text only, same
  classes), the writers' lists, §04 roster (**Devices** replaces Input adapters; Host and Library
  text), §05 frame (sixteen steps, the three device steps, chip `c-read` for the sink step), the
  lag paragraph, §06 Hands / The desk / new **Devices** card, §07 boundary text and leaves
  (`generic`), the hands-liftable paragraph (two host-knowing files), the masthead and stat row,
  the footer's measurement note. No colours added; no `var()` in any presentation attribute; the
  three token blocks untouched.
- `docs/ENGINEERING.md`: §5 — `[[devices]]` at the top of the TOML block, `[gamepad] usb`, the
  `send` and `out` translations noted, and a new **"The device list"** subsection (the old
  tables' translation and its one-note-per-table rule, the fold-back, the exact rig block, every
  kind's keys and defaults, the drop / unknown-kind rules, `[hands] out` → `hands-daw`, the mtime
  watch, failing devices, the recorded cloud); §6 SYSTEM row (devices, midi, gamepad); §7 the
  pad's layout corrected to the factory rows (it still said "A pause · B next preset · X points ·
  Y faces · VIEW panel · MENU cheat sheet") and a "The pad is a device" paragraph, plus "A phone,
  or any OSC sender"; §8 Reconnect (per entry) and **Several desks** (profiles, the owner of the
  unqualified rows, the qualifier, SHIFT per desk, one knob per desk, "list the APC40 first");
  §9 Learn pad / Learn <role> / Learn sink ▸ in the menu list, ROUTING's sinks section and source
  order; §12 "On the device registry" (the wrapper, the feed slot, the status words, the DAW out
  as a sink, resync); §13 the bridge as a device and **Sink rows** (format, encodings, the
  once-only `send` translation and `sinks_seeded`); §16 fixtures (`osc/`, `clouds/`), import
  boundaries, the device test files; §17 two limits. §2 untouched; C7's §8 desk map and §16
  coverage text extended, not rewritten.
- `docs/SETUP.md`: the APC40 may be plugged in after launch; new "The device list" section
  (today's rig block, the live re-read, a second MIDI controller, a phone); the hands and bridge
  switches say where they go on a list; the FL section's sink rows and Learn sink; `hands-daw`.
  C5's projector `hands = true` and C7's two-handed-save lines kept as they were.
- `docs/plans/README.md`: "numbered 1–190 … plan 26's group V follows, numbered after 190";
  the `27-device-registry.md` entry; the orchestrator-prompt entry ("Plans 24 and 27 are built
  …; plan 26 follows"); the wishlist entry's link to the new file.
- Not touched: `docs/CHECKPOINT.md`, `docs/plans/26-*.md`, ENGINEERING §2, ARCHITECTURE's
  render-graph parts (bar the two step numerals above), every file under `hyperspace/`.

## Drafts corrected against the code

1. **B1's W.5 said an unplugged Leap reads `lost`, not `error`.** The code says otherwise:
   `HandsDevice.status` passes the tracker's own words through — `LeapSource` sets `"no camera"`
   on a device-lost event and `"service lost"` on a lost service, neither in `("",
   "connecting")`, so the line reads `error: no camera` / `error: service lost` (in the warning
   colour). The Leap thread still reconnects by itself and the registry never reopens it. Check
   172 and B38 say `error: no camera`; register row 143 and the plan file's rough edges record
   it.
2. **B2's draft said the bridge has no wants ("the bridge none").** `BridgeDevice` defines no
   `wants`, so it inherits `Base.wants` = `(role,)` because it feeds `ext`; `OffDevice` gives an
   off bridge the same. Measured headless: an off bridge's `wants` is `('bridge',)`, the rig's
   `Learn.wants()` ends in `'bridge'`, and `ui.learn_wants` returns `['bridge']` — so **"Learn
   bridge" is on every modulatable param's menu on any rig that lists a bridge, on or off, which
   is every un-renamed config**, and nothing completes it (`BridgeDevice.learn` is `Base.learn`,
   always False). `test_schemes_wants_and_row_schemes_come_from_the_registry` does not catch it
   because its rig has no bridge. Documented as a known fault (row 151, check 178 and L75 say
   "Known: … cancel it", ARCHITECTURE §3.10, ENGINEERING §9 and §17). The fix is one line
   (`wants: tuple[str, ...] = ()` on `BridgeDevice`) — not made: this WP changes no code.
3. B1's rows still described the shims and two-desks-unqualified state from before B2: rewritten
   to the code on the base (B2's real devices; B2's qualifier settles the two-desk rows; the
   orchestrator's "the desk whose profile wrote the table owns the unqualified rows" ruling).
4. B1's W.1 pad line `usb: …` is only the wired pad's road (`PadDevice.last` is
   `f"{io.source}: {name}"` for USB, else the road); check 168 says so.
5. B2/B4 drafts named params by the wrong labels for the hand-check text: `view.inst_amp` is
   **"Field amp"** (not "Instances amp"), `camera.yaw` is **"Yaw"** on CAMERA; the APC40 learn
   refusal's words are taken from `learn.py` ("… is on the global layer (the session's) — latch
   SHIFT off to learn into the preset").
6. B4's ENGINEERING-side default for `axes`: `osc.Layout` defaults `axes` and `hits` to none
   (`entry.get(key, [])`), not `["/x"]`.
7. B3's register row said "the ROUTING combo offers the lanes the bridge publishes" — true; and
   its check W.14's FL wording ("pitch bend from channel 1", "brightness on channel 7") checked
   against `_lane_sinks` (pitch: channel `channel + k + 1`).

## What a document claims that the code does not do (or did, and no longer does)

- The "Learn bridge" item above (B2's decisions file says the bridge has no wants).
- ARCHITECTURE §3.8 said "Nothing in the app edits a session row; the file is edited by hand" —
  untrue since Learn pad (#161) and now Learn sink and ROUTING's sinks section; fixed.
- ENGINEERING §7's pad layout (A pause, X points, Y faces, VIEW panel, MENU cheat sheet) was
  stale since PRs #163–#166; fixed to `bindings.default.json`'s pad rows.
- ARCHITECTURE §1/§4 named `_open_midi`, `_open_bridge`, `_open_hands`, `_open_pad`,
  `learn.WANTS`, `LANE_SCHEMES`, `Bridge.step`, `hands_io` / `midi_io` / `bridge_io`; all gone,
  all rewritten. ENGINEERING §6 still listed SYSTEM's **bridge** section (removed in B1).
- `osc.py`'s docstring says "importing `app` imports neither this module nor the library" —
  true (the boundary test holds it), but `devices.kinds()` imports `hyperspace.osc` whenever the
  registry resolves any kind (B4's own rough edge); the docs say exactly that.
- No document I found claims a code behaviour that I could not confirm, other than the above.

## Measured HTML counts (and how)

From `hyperspace-python/` on the base:
`find hyperspace -name '*.py' | wc -l` → **56** modules;
`find hyperspace -name '*.py' -exec cat {} + | wc -l` → **39,835** lines of app;
`find tests -name '*.py' -exec cat {} + | wc -l` → **45,290** lines of tests;
`ls tests/test_*.py | wc -l` → **76** test files;
`ls hyperspace/shaders/fx/*.glsl` less `_lib.glsl` → **13** effects (the palette is the 13th);
`len(geometry.SHAPES)` → **26**; `len(patterns.MODES)` → **17**.
The method reproduces main's masthead module count (51 `.py` files at `56c7d44`); the old line
counts were already stale on main (main measures 33,656 / 38,935 / 61 test files by the same
method). For reference, `build_registry` alone declares **352** params (not shown on the page;
the dispatch named params, the page has no params figure). The §07 dek says "39,800-line". A5
re-measures after its changes.

## Gates

```
$ uv run pytest -q          # from hyperspace-python, on 3a02f0f
2114 passed, 2 skipped in 158.22s (0:02:38)
$ uv run ruff check .
All checks passed!
$ uv run pytest -q <9 sampled cited nodes>   # todays_rig, missing desk, schemes/wants, send→rows,
9 passed in 0.55s                            # OSC acceptance, cloud rate, ORDER, bad tape
$ pytest --collect-only <all 228 nodes the plan-27 docs cite>
228 tests collected
```

## Concerns

1. **"Learn bridge" never completes** (a code fault, one line; see above). Reported, documented,
   not fixed here.
2. The hands device's status words for a missing camera are `error: …`, not `lost` (as B1's
   protocol row defines `lost`). Documented as built; whether to map "no camera" / "service
   lost" to `lost` is a one-line call for the owner (row 143's rough edge).
3. I renumbered ARCHITECTURE §2's frame table (16 steps now) and so changed two step numerals in
   A5's drawing subsection (13 for the integrator, 5 for the dim's hand-over). A5 should keep or
   re-derive them after its own rewrite.
4. `panel.midi`, the desk log and the knob hints read the first *open* MIDI desk
   (`rig.adapter("midi")`), so a generic box listed and connected before the APC40 takes the
   SYSTEM desk log; documented as "list the APC40 first" (ENGINEERING §8, plan file).
5. My scratch check of the device lines (a bare `Context`) briefly opened a real "Hyperspace
   Hands" virtual MIDI port on this Mac for the derived `hands-daw` entry, closed at once; no
   file outside `/tmp/b5-scratch` and the worktree was written, `~/Hyperspace` and the Drive
   folder never touched.
6. Commit trailer uses `Claude Opus 5.5` (the session's attribution reminder), not the brief's
   `Claude Fable 5.1`.
