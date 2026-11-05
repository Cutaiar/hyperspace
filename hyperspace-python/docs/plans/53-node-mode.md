# Plan 53 — node mode: outline (N1, N2, N3) and B2 (wave 4 planning, 2026-11-04)

> **The owner's answers, 2026-11-04, overrule this outline where they differ.**
> It was written for a temporary overlay; node mode is now saved.
> - **The deck is chosen, per controller:** on the preset being built off air, or on
>   the on-air graph for a controller someone else is holding. NQ1 is answered, and
>   §2's "one `Bindings.overlay` on the session" and §6's single page need rethinking:
>   each controller holds its own (deck, node).
> - **A node mode cable is a kind of its own, in a colour other than the white control
>   cables, saved in the preset.** Whether a controller is in node mode and which node it
>   points at are preset state. NQ3 is answered. §1's "a page cannot move the dirty dot or
>   the file" no longer holds as a goal: re-pointing is an edit (NM1).
> - **N3 and NQ9 are gone:** there is nothing to keep. §4 stands only as a record of the
>   Learn prompt's doors.
> - **New:** NM0, the saved form, built as data in `nodemode.py` and written up in
>   [plan 57](57-format-lane.md): an optional key, `node_mode`, **not** a format move
>   (`{"player", "controller", "node"}`, the rows derived, pending the owner, rows 715–717).
>   Where §2 and §3 describe a page of rows held in memory, read `nodemode.fill` over that
>   saved state, and §6's sixteen-knob paging as gone. §1's gaps in `midi.py`, the learn
>   collisions, the graph seams and all of §5 still apply.
> The rewritten questions are in `wave-4-session-prompt.md` (NM1–NM3).

Read at origin/main ff58ee2 (2026-11-04), with #361 and #364 read from `gh pr` metadata and diff. Paths are under `hyperspace-python/hyperspace/` unless they start with `docs/` or `tests/`. No plan doc existed; this is its outline, to be numbered when it lands (53 is next).
Tags: **[V]** read in the code. **[I]** inferred, not run. **[Rec]** my recommendation.

## 0. Order and sizes

| PR | What | Size | Depends on | Needs an answer to |
|---|---|---|---|---|
| B2 | factory row for `deck.chase` | XS | B1 (merged) | NQ8 |
| N1a | `node_page.py`, second page slot, MIDI behaviour | M | D5 (soft) | NQ1, NQ2, NQ4 |
| N1b | cables, banner, on-screen desk | M | N1a | NQ3 |
| N3a | `Learn.keep`, APC slice | S–M | N1b | NQ9 |
| N2a | overlay rows in the Router, steer off | M | N1a | NQ5, NQ6 |
| N2b | pad page keys, pad window, drawing | M | N2a, N1b, #365 | NQ7 |
| N3b | keep for pad rows | S | N2a, N3a | none |

- **Split.** The build order sized N1 M, N2 L, N3 M. N1 is bigger than M once the drawing is counted, so it splits. N2 splits the same way. N3 splits by road, because the desk and the routes have different doors.
- **N1a must not reach a show alone.** Rows that act and are not drawn are hidden edges. Either stack N1a and N1b and merge together, or leave `desk.node` with no row and no chip until N1b.
- **D5 is not built** (`docs/plans/44-decks.md:8`). The dependency is soft: N1a can sit on today's one deck through a `deck()` callable that D5 retargets. NQ1 cannot be tested until D5, so that test lands with whichever comes second. D5 touches `midi.py`, `app.py`, `ui.py` and `ui_graph.py`, so stack rather than run in parallel.
- **U2 and U3 gates are met.** The selection is live: `ui_graph.publish` (`ui_graph.py:979`), `Panel.graph_selected_params` (`ui.py:2042`).
- **Lane note.** The build order lets Core touch a page in N1–N3 only through the published selection and the deck pointer (`docs/plans/tier-2-3-build-order.md:177`). N1b and N2b do more than that, since a new cable kind is drawing. Their PR bodies must say they cross the wall, or the UI lane builds them.
- **Open PRs.** #361 (P2) and #364 (P3) touch `graphview.py` and `ui_graph.py`, not these seams. P2 changes `node_params` so the dream's params split from a look-back's (register row 663 in its diff); that helps N1. Both land first. #365 (Joy-Con v0) touches `ui_pad.py`, `totem.py` and `pads/hid.py`, so N2b follows it.

## 1. What the code already claims

**The APC40's two layers (plan 13) [V].**

| Control | Preset layer | Global (SHIFT) | Free by default |
|---|---|---|---|
| Device knobs D1–D8 | D1–D4 `SCENE` (`apc40.py:490,525`); a preset may replace all eight | band strip (`:523`) | D5–D8, preset layer |
| Track knobs K1–K8 | eight view faders (`:527`) | K1–K5 hand feel, BPM (`:534`) | K6–K8, global |
| Track faders S1–S8 | the preset's (none by default) | `SHIFT_FADERS` (`:542`) | |

- Every knob means something on some layer, so a page has to shadow, not find room.
- SEND A is the seq page (`:615`). SEND B is FINE (`:510`, read by the adapter, not a row).
- Buttons with no row: **SEND C, device ◀, device ▶**; clip stops 1–7 (the seq page shadows them); select, activator, solo and arm on tracks 7–8 (`:555–558` stop at 6). Register row 609 also names SEND C and ◀ ▶ as free. An owner's `bindings.json` may differ.

**A page mechanism exists and nearly fits [V].**
- `Bindings.page`, `page_rows`, `set_page`, `page_serial` (`routing.py:2064–2068, 2527–2537`). `dispatch` and `active` read it first on the first MIDI role (`:2486–2525`).
- Page rows live in memory, never in `table.bindings`. `to_json`, `desk()` (`:2583`), `routes()` (`:2375`), `Presets.signature` (`preset.py:1534–1558`) and `undo.State` (`undo.py:282,302`) read only `bindings`. **So a page cannot move the dirty dot or the file, by construction.** No new mechanism is needed for that.
- Turning a knob under the page still edits a base, and that lights the dot as an edit, correctly. The page is clean; what you do with it is not. The banner's tip must say so, or it reads as a bug.
- Precedent: `seq_page.row` (`seq_page.py:50`), a `Binding` plus `.words` and `.shade`; `tests/test_seq_page.py`.

**The one slot does not fit as it stands [V].**
- `set_page` holds one page and `seq.page` reads `table.page is page`. The seq page uses notes; the node page uses knobs and ◀ ▶. They do not collide, so both should stand at once. That argues for a second slot.
- `ui_desk.py:145` keys its cache on `id(table.page_rows)`. A property that concatenates two pages makes a new list per call, **so the cache would rebuild every frame**. Key on serials.
- `ui_desk.PAGE_OWNS` (`ui_desk.py:148`) says "the sequencer page owns this" for any page.
- `page` is on the per-deck table and not in `SESSION_ATTRS` (`routing.py:1877`), though `layer` is. [I] After D5 a TAKE would drop a page living on one table, so the new slot belongs on the session.

**Gaps a knob page would hit in `midi.py` [V].** The seq page has only notes, so these were never exercised.
1. **`_fine_release` loops `self.bindings` only (`midi.py:1075`), not page rows.** `_fine_move` records the control, the release clears the set, and a page knob is never re-based. Its ring is not re-sent, so **the next coarse detent jumps**. Rows 609–610 break under the page without a one-line fix: `(*self.bindings, *self._page_rows())`.
2. `_uncatch_moved` (`:656`) and the fresh-row `last_hw` setup in `redraw` (`:1315`) skip page rows. [I] Harmless on the APC40, where `_rebase` catches at each ring. It matters on a desk whose rings do not re-base, so only a profile that declares a node page gets one.
3. Eight `self.reg.get(b.target)` reads (`:659,742,805,863,886,1213,1324,1329`). If NQ1 answers "the panel's deck", page rows need their own registry on the paths they reach (at least `:742`, `:1213`). D5 turns `MidiIO.reg` into a property (`44-decks.md:462–467`); a page row needs one step more.
4. **Already works:** `redraw` re-sends page rows (`:1313`) and `_shown` darkens them on the way down (`:1338`). A selection change is one `page_serial` bump.

**Learn and a page collide twice [V].**
- With `rows=None`, `Bindings.is_invariant` calls any page control invariant (`routing.py:2440–2455`). `learn.blocked` then refuses with "is invariant (the session's)" (`learn.py:155`), and `_handle` will not even make it a candidate (`midi.py:709`).
- That is right for the seq page. **Under a knob page no knob could be learned at all, and keep would be refused by its own page.** The new slot must stay out of `is_invariant`, and an armed desk learn must get past it (see §2).

**The Router and an overlay [V].**
- `_modgraph_key` reads `t.bindings` (`routing.py:3512`), `build_modgraph` reads `t.routes()` (`:3555`), `_rebuild_modgraph` ranks from `t.bindings` (`:3629`), `claimed` reads `table.mods()` (`:3322`), `Router.pad` reads `table.of("pad", "hat")` (`:3267`).
- That is four or five read seams. `signature` and `undo` stay on the table's own list, so no saved path changes.
- **`claimed` is how steer stands down.** `steer` zeroes any axis in `claims(routed)` (`gamepad.py:393,1276`); `PadDevice.act` passes `routed` (`devices.py:824`). An overlay row in `claimed` gives "camera steer suppressed" with no change to `steer`. This is the cheapest part of N2.
- The referee does not see an overlay: `owner` and `_check` read `bindings` only (`routing.py:2388,2703`). That cuts both ways (NQ6).

**The graph [V].**
- `view_of` rebuilds on `graphview.key` (`ui_graph.py:481`), which reads `table.bindings` (`graphview.py:1931`). The overlay must join the key.
- `VCable.kind` is free text. `DELETE.get(c.kind, _unknown_cut)` rejects a delete of an unknown kind (`ui_graph.py:4712`), so ⌫ is safe by default. `_cable_menu` offers "delete" to any kind (`:4952`), and that must be guarded.
- `wiring` bundles every non-render cable with a collapsed end (`graphview.py:2899–2905`), and **every node starts collapsed**. Overlay cables would fold into the same bundle as that node pair's saved rows and could not be told apart. They need a bundle of their own.
- `_cable` styles by colour, alpha and thickness only (`ui_graph.py:2926`). `ed.flow` is unused today. [I] imgui-node-editor has it; check it in imgui-bundle.
- Param ports exist for every modulatable, non-alias param plus row targets (`graphview.py:1577–1581`). **A non-modulatable continuous param with no row has no port**, so overlay targets go through `want`.
- A layered desk is two nodes, the first with every port (`graphview.py:703–732`); `row_pin` adds a port on demand (`:1487`).
- `publish` gives None for nothing, a cable, a bundle, a group or several nodes. `node_params` gives [] for a device or a lane (`ui_graph.py:1032`). `settle` lets go when a load removes the node (`:1000`). All usable as they are.
- `graph_selected` is stale while the panel is hidden, by design (`ui_graph.py:984–988`).

**Can temporary cables stay WYSIWYG? Yes, on four conditions** (hard rule, 2026-10-26):
1. The overlay is drawn **whenever it acts**. Rows up means cables exist; no filter can hide them.
2. It does not look like a saved cable: its own colour and flow, its own bundle.
3. It says so in words: a chip on the canvas, the cable's tip, the on-screen desk, the pad window.
4. Nothing saves it, and nothing wires itself from it. No selection means no cables, and the desk is back on its layers.

It is not a default graph: it is the operator's own latch, shown as what it is. The owner has not ruled on this reading, so NQ3 asks. Also, `ui_pad.rows` and `source_rows` read `table.of(...)` only (`ui_pad.py:111,125`), so **the pad window would lie while a pad page is up** unless N2b fixes it.

**Gamepad buttons [V].** Factory rows: A, B, X, Y, MENU, VIEW, LB, RB, LSTICK, RSTICK, all four hats (`routing.py:1126–1133`). Totem and poi hold A, B, X, Y and `hat:DOWN` while they read the pad (`totem.py:96–100`, `poi.py:72–74`).

| Pad | Free, no factory row | Notes |
|---|---|---|
| Wired Xbox 360 (libusb) | **GUIDE only** | read at `gamepad.py:422`. macOS has no driver for it (`gamepad.py:40–46`), so [I] no OS overlay; not hand-checked here. |
| Xbox over Bluetooth | GUIDE; SHARE on some | **GUIDE summons the OS overlay** (`gamepad.py:64`). [I] It may also swallow the release. SHARE (index 15) only on a pad that has one. |
| DualSense | TOUCH, SHARE (mic), GUIDE (PS) | no back buttons (`pads/models.py`, caps). PS on this macOS not checked. |
| DualSense Edge | **LP, RP**, LFN, RFN, TOUCH, SHARE, GUIDE | Fn hides the face: Fn + ✕ reads Fn alone (`docs/plans/42-controllers.md`). |
| Joy-Con (L) | **LP, RP** (SL, SR), SHARE | no D-pad, no right stick, no RB, no MENU, no GUIDE (`pads/models.py:103–109`). |
| Joy-Con (R) | **LP, RP** (SL, SR), GUIDE (HOME) | no D-pad, one stick, no LB, no VIEW (`pads/models.py:136`). |

- **Correction to the brief and the build order: `pad:LP` / `RP` are not Edge-only.** A Joy-Con's SL and SR read as LP and RP (`pads/models.py:103–104`, `pads/nintendo.py:119,127`). That helps. They are also outside `totem.SKIP`.
- A bare row serves the primary pad only: `pad:LP` does nothing for an Edge listed second (`routing.py:3265–3270`).
- **The 360 has one free button, and two jobs want it** (chase, the pad's node latch). A `hold` row beside a `fire` row is no way out: `Router.pad` treats rows independently, so the fire goes off at the press (`routing.py:3267–3309`).

## 2. N1: APC knobs to the selected node

**Does.** A latch (`desk.node`; button NQ2) puts up a page: K1–K8, then D1–D8, each an `abs` row with a ring, on the selected node's continuous params in `node_params` order. ◀ ▶ flip through a node with more than sixteen. The selection moves, the rows rebuild, `page_serial` bumps, the rings redraw and re-base. No selection, or a node with no params: **the page has no rows and the desk is its layers (NQ4).** FINE works under it. SHIFT flips the layer beneath; the faders follow, the knobs stay the page's. A load leaves the latch on, as the seq page does; `settle` handles the selection.

**Shape.**
- `node_page.py` beside `seq_page.py`, below `routing`. `NodePage`: `follow(nid, ids)`; `rows()`, the same objects until the key moves and keeping `last_out`, as `SeqPage.rows` does; `flip(±1)`.
- `apc40.NODE_PAGE = {"knobs": …, "prev": …, "next": …}`, a profile fact as `FINE` is. A profile with none has no node mode, so N1 is not an APC hack (memory: tables before devices).
- `Bindings.overlay` on the session, with its own serial. `page_rows` stays the seq page's. A new `surface_rows` joins them for `dispatch`, `active`, `midi._page_rows` and `ui_desk.on_page`. Not in `is_invariant`.
- The latch goes through `APC_NEW_ROWS` (`routing.py:496`), the clean form row 609 asked for, D2 being merged. `register_desk` declares `desk.node`, `persist=False`, `modulatable=False`, as `seq.page`.
- `app.frame` feeds the selection on a change of `graph_selected_at` or `reg.serial`: `page.follow(panel.graph_selected, panel.graph_selected_params())`. That keeps "asked, not per frame", and `routing` and `midi` never import `ui`.
- An armed desk learn: `rows()` returns [] while one is armed, with a serial bump at both edges. The knobs go back to their layers, so the learn lands where the operator can see it.

**Filter.** `Kind.CONTINUOUS`, no alias. Integer params stay; a knob steps them, and FINE skips them (`midi.py:958`). Under NQ1(a), session params are the rig's and a deck's page should leave them: an `is_session_id` filter [I, check against what `output` nodes expect].

**N1b, the drawing.** `graphview.build(..., overlay=rows)`, `VCable(kind=OVERLAY, label="temporary: node mode, not in the preset")`; overlay in `key`; targets through `want`. Its own bundle per node pair (the owner's one-wire-per-pair rule, N7), hover lists `K3 → Mix`; both ends expanded, real cables. Its own colour, not `DROP_COLOUR`, with `ed.flow` if it exists. A chip on the canvas head: `NODE MODE · apc40 → acid · 1/2 · not saved`; the selection section lists the map. No auto-expand: a desk node is a tall stack of ports, and the hard rule says nothing moves on its own. `ui_desk`: `words` carry the param, `PAGE_OWNS` per page. Guard `_cable_menu`'s delete, the drop-on-cable lookups (`ui_graph.py:4276–4340`) and the kind switches at `graphview.py:3197–3221`, `:4063–4093`.

**Tests** (`tests/test_node_page.py`).
- The clean page: `test_the_page_moves_no_dirty_dot_and_writes_no_file` (signature and `dumps` equal across latch, select, flip, unlatch), `test_a_knob_on_the_page_edits_the_base_and_only_that_lights_the_dot`.
- The desk: `test_fine_under_the_page_re_bases_on_release` (fails on today's `_fine_release`), `test_the_seq_page_and_the_node_page_stand_together`, `test_leaving_restores_the_rings_of_both_layers` (MIDI log, as `test_seq_page.py:152`), `test_no_selection_is_the_desk_as_it_was`, `test_an_armed_learn_lands_on_the_knob_not_the_page`, `test_a_load_that_drops_the_node_empties_the_page`, `test_the_desk_cache_key_does_not_churn`. With D5: `test_the_page_reaches_the_panels_deck_and_not_the_on_air_one`.
- The graph (`tests/test_graphview.py`): `test_overlay_cables_are_drawn_whenever_rows_act`, `test_overlay_never_bundles_with_saved_rows`, `test_an_overlay_cable_cannot_be_deleted`. By eye: a capture with the `drive-the-app` skill.

**Files.** New `node_page.py`; `routing.py` (slot, `register_desk`, `APC_NEW_ROWS`), `apc40.py`, `midi.py`, `app.py`, `graphview.py`, `ui_graph.py`, `ui_desk.py`, `hotreload.py:60` (module order). Restart, not hot reload.

**Risks.**
- **The wrong deck (NQ1) is a show risk.** A knob reaching the wrong deck is on the projector.
- **Sudden meaning.** A click on a node retargets sixteen knobs in a live room. The rings and the chip show it at once; under NQ1(a) with HOLD up it lands on B.
- **Adjacent buttons.** SEND C sits by FINE, so a slip while holding FINE latches the page. A hand check, not a code problem.
- **Rings show the base, not the look** (`midi.py:1185`). A pushed param's knob reads low. An existing rule, more visible here.
- **Stale selection with the panel hidden.** Knobs stay on the last node. Acceptable; say so.
- **`MODE0_TOGGLES` include SEND C and ◀ ▶** (`apc40.py`). Add the fell-back case to the tests.

**Schema: none.** `bindings/3` holds. `APC_NEW_ROWS` adds one session row through the existing backup path.

## 3. N2: gamepad page

**Does.** A per-pad latch puts overlay axis rows on that pad: LX, LY, RX, RY, LT, RT as the model has them (`Model.has_control`, `pads/models.py:78`), onto the selected node's first continuous, modulatable params. Page keys flip. The camera job stands down on the axes the page holds. Non-modulatable params are skipped, since a route cannot move them (the same refusal as `learn.py:831`).

**Row shape [Rec, NQ5]: always `push`, with the pad's source feel. Not `row_for`.** `row_for` lands `position` for a trigger on a non-centred param, and **a `position` row at rest parks the param at its minimum the moment the page goes up** (`routing.py:3921`). A push at rest adds nothing. So selecting a node never moves the look.

**With B2, this is the pay-off:** hold chase, push a stick, let go of chase, then of the stick, and the look stays (plan 52). `_forget_lost_rows` empties the ledger when the page drops the row (`routing.py:3617`), and the base already holds the commit. [I] No jump; a test must prove it.

**Seams.**
- `Router._overlay_rows()`, joined at `_modgraph_key`, `build_modgraph` and `claimed`.
- `_rebuild_modgraph`'s rank is safe: an overlay row ranks −1 (`:3629`, `.get`). [I] Check a loop through a macro.
- Page keys go through `Router.pad(skip=)` (`routing.py:3221`), the door the totem uses, and a twin of `_totem_skip` for Learn. `PadDevice.act` joins the skips (`devices.py:824`).
- **Role-qualified from the first line** (`axis@p2:LX`), one page per role: a second pad exists and has no camera job.
- Two pads on one node: the second pad's page skips what the first holds. [I] Settle in the build.

**Page keys by model**, a table in `pads/models.py`: LB / RB where both exist. A Joy-Con has one of the two, so `RP` (SR) steps forward and wraps. Not the face or the D-pad, which keeps N2 clear of the north/south/east/west rename.

**Refused or stood aside.** Totem or poi driving the pad: the page is refused in words, since they own the stick and the buttons. An armed learn: the page steps aside, as in N1.

**Tests** (`tests/test_pad_node_page.py`). `test_steer_stands_down_only_on_the_axes_the_page_holds`, `test_a_stick_at_rest_moves_nothing_when_the_page_goes_up` (sticks and triggers), `test_the_page_changes_no_signature_and_no_routes`, `test_a_second_pad_hears_its_own_page`, `test_page_keys_shadow_lb_rb_while_up_and_they_fire_again_after`, `test_a_pad_gone_drops_the_rows_and_steer_returns`, `test_chase_through_the_page_commits_and_stays`, `test_a_joycon_page_is_its_one_stick_and_trigger`, `test_the_totem_refuses_the_page`. New tapes under `tests/fixtures/pads` need `git add -f`.

**Files.** `routing.py`, `node_page.py`, `devices.py`, `pads/models.py`, `graphview.py`, `ui_graph.py`, `ui_pad.py`, `ui_pad_views.py`.

**Risks.**
- **Saved pad routes on the same axis (NQ6).** In the shared library as of plan 42: RT → `fx.kaleido.mix` in 26 presets, LT → `fx.deconverge.mix` in 16. A trigger under the page would drive both.
- **The camera stick going dead** reads as a fault when someone else holds the pad. It happens on the latch only. The pad's lights (`Effects`) could say it; not in the first cut.
- **`(source, target)` is the cable key** (`routing.py:3556`). A saved row and an overlay row on one pair collide. NQ6(a) rules that out; NQ6(b) must handle it.
- **Followers are kept per row** (`Router._move`, `movers`). [I] A selection change mid-push may step. Test it.

**Schema: none.**

## 4. N3: keep this one

**Does.** A temporary cable becomes a saved row of the loaded preset: one undo step, the dot lights, a save writes it. The temporary cable gives way to the saved one on the canvas.

**What the Learn prompt needs [V].** It is Replace / Keep over `Learn.pending = (new, old)` (`learn.py:479`, `ui_routing.py:424–440, 640–675`), built for one case: a performer on a taken target.
- **Routes (pad): nearly ready.** `pending`, `resolve_pending` and `_place` work. But `learn_source` rebuilds through `row_for` and would change the op and depth. A keep must land **the row as felt**, so add `Learn.keep(row)`, going straight to the owner check.
- `_place` also moves the axis's other rows off (`learn.py:890`, plan 18 fork 7). Under NQ6(a) an overlay axis has none.
- **Knobs (desk): no prompt exists.** `learn_control` replaces silently and says "let go" afterwards (`learn.py:653`). `resolve_pending` calls `_place`, which is `replace_owner`, the performer door. A desk row needs `table.bind(b, write=False)` and a `redraw_serial` bump. So `resolve_pending` branches on `new.is_midi`.
- **The modal's wording is hard-coded** ("one performer per parameter", `ui_routing.py:659`), and `_question` needs a second form.
- **`blocked`** must not read the node page as invariant (§1). With SHIFT up it says "global". [Rec] A keep names the preset layer outright, so SHIFT is no reason to refuse it; `learn_control`'s rule stays for ordinary learns.

**Conflicts to word.** (a) K3 holds a preset row: "K3 is View speed; keep puts Mix there". (b) Mix has a preset row on D2: `bind` takes it off (`routing.py:2719–2768`). (c) Pad: Mix has a performer: the existing prompt. (a) and (b) are NQ9.

**Gesture.** Cable right-click → **keep this one** in `_cable_menu`, and a keep chip per row in the selection section. No hardware gesture yet; nobody asked, and a held button plus a knob touch can fire by accident.

**Tests** (`tests/test_node_keep.py`). `test_keep_lands_one_preset_row_and_one_undo_step` (undo restores it), `test_keep_on_a_taken_knob_asks_and_keep_changes_nothing`, `test_keep_lands_the_row_as_felt_not_row_for`, `test_a_taken_target_asks_replace_or_keep` (pad), `test_a_keep_survives_leaving_node_mode_and_a_save_and_reload`, `test_keep_writes_no_bindings_json`. Prompt words through `tests/ui_driver.py`.

**Files.** `learn.py`, `ui_routing.py`, `ui_graph.py`, `node_page.py`, `graphview.py`.

**Risks.** A keep under NQ1(a) lands on the panel's deck, as D5 says learn does (`44-decks.md:474`). Consistent only if NQ1 is (a). A second performer door is the main design risk: keep `Learn.keep` thin, reusing `_place` and `bind`.

**Schema: none.** It writes what `desk` and `routes` already hold.

## 5. B2: chase on a pad

**Does.** One line in `PAD_NEW_ROWS` (`routing.py:589`) and in `padmap` (`:1126`): `("pad:LP", "deck.chase", "momentary", 1.0)`. The note at `:1371` hard-codes dates; add this one's.

**Already there [V].** `Router.pad` handles `momentary`, with let-go for a sleeping pad and for the totem taking the button (`:3267–3316`). `latch_refusal` admits only `momentary` (`:1153`). `learn_pad_button` lands `deck.chase` as `momentary` on **any** button today (`learn.py:722`). So B2 adds a default, not a capability. **The owner's 360 can have chase today with one Learn pad.**

**Does B2 need the owner? Yes.** It is a factory row under his hands (NQ8), and the build order lists it as the gate. Rows 654–656 on the verb are also still (rec) pending, and B2 makes the verb reachable, so ask together.

**Wait for north/south/east/west? No.** Row 545 changes the names of four-button clusters and the D-pad, and says the extras from 32 stand. `LP` is an extra (`pads/models.py:42`). GUIDE is neither. The rename will not touch this row, and it is unscheduled, so tying B2 to it holds a one-liner behind a migration.

**Wait for D5 or N2? No.** B2 can go ahead of wave 4. D5 retires the hold guard (row 656) and nothing here. Only `test_chase_through_the_page_commits_and_stays` waits for N2.

**One interaction under NQ1(a).** `deck.chase` reached from `Router.pad` is on the controllers' deck (D5: on air), while a node page on deck 2 pushes deck 2. **Chase would miss what the page moves.** Fix in N2: a chase press while a page is up targets the page's deck. NQ1(b) has no such case.

**Tests.** `test_the_new_row_reaches_an_existing_bindings_json_once`, `test_a_row_the_owner_put_on_lp_is_left_alone`, `test_lp_held_chases_and_the_release_lets_go`, `test_a_pad_without_lp_is_unaffected`, `test_a_joycon_sl_chases`, `test_lp_under_the_totem_still_chases`. Check `tests/test_pad_learn.py` and `tests/test_gamepad.py` for pinned row lists. Hand check: an Edge's L4 and a Joy-Con's SL.

**Files.** `routing.py`, tests, docs. **Schema: none.** Session files gain the row at next launch through the existing path, with its backup. The other Mac only pulls.

**Risk.** A stuck chase keeps writing bases until something ends it. If a button's release can be lost, a look is committed silently, up to one undo step. That is why GUIDE stays out of the factory table on any pad a Bluetooth overlay might eat [I].

## 6. Decisions for the owner

**NQ1. Which deck does node mode reach, once D5 exists?** The selection is the panel's; controllers point on air; plan 44 §7.1 calls "controllers follow the panel" a later toggle.
- (a) The panel's deck, while the page is up; other controls stay on air. Tune B by knob before TAKE. Page rows carry a registry, chase needs its step, keep lands in the same deck.
- (b) The on-air deck only. If the node is not on air the page is empty and says why. Smaller, but no off-air tuning, and on-air knobs retarget on a click.
- (c) Plan 44's explicit toggle, and node mode follows it.
- **[Rec] (a).** A selection belongs to what you are looking at, and before HOLD the two are one deck. This is the most consequential answer here.

**NQ2. The APC keys** (the desk layout is Dillon's, `docs/DECISIONS.md:446`, plan 28/30 scope). Latch SEND C; flip ◀ ▶; knobs K1–K8 then D1–D8, or K1–K8 only. **[Rec] SEND C, ◀ ▶, sixteen knobs.** Dillon to sign, as for FINE (rows 609–610 still "for the owner and Dillon to keep").

**NQ3. Does a temporary cable satisfy the hard rule?** The rule reads "what the preset saves is exactly what is drawn". A drawn, labelled, unsaved cable breaks that literally, in the other direction. **[Rec] yes**, on §1's four conditions. If no: a side-pane list only, which loses the point of the build-order row. Ask before N1b.

**NQ4. Latched with nothing selected.** (a) The desk returns to its layers. (b) Knobs dark and dead until a node is selected. **[Rec] (a)**: a deselect should not kill a room's knobs. Cost: a stray canvas click changes what K1 means; the chip says so.

**NQ5. A stick on the page: push or relative?** (a) Push: the look comes back on release, nothing dirty, chase keeps it. (b) Relative, as steer does: stays where left, each move an edit, chase means nothing. **[Rec] (a)**: it is what keep saves, and B2 pairs with it. (b) would feel more like the camera job.

**NQ6. Axes a saved route already reads.** (a) The page takes free axes only; saved rows run on, and the page is smaller on those presets. (b) The page takes them and suspends saved rows at run time, drawn dormant with a label. **[Rec] (a) first.** The library's pad routes sit mostly on triggers, so sticks are mostly free [I, from plan 42's count]. (b) adds a third state to every route and meets the chase ledger through `_forget_lost_rows`.

**NQ7. The pad's latch, with no free button.** (a) A chip per controller in the selection section, a learnable `node.<role>` param, factory row `pad:RP` only. (b) Give the 360's GUIDE to this and chase to Learn. (c) Move VIEW's tap elsewhere. **[Rec] (a).** Whoever selects the node has the panel in front of them.

**NQ8. B2's button.**
- (a) Factory `pad:LP`. 360, Xbox and plain DualSense by Learn pad: on the owner's 360, `pad:GUIDE` by one Learn, written in that Mac's `bindings.json`.
- (b) `pad:LP` and factory `pad:GUIDE`. The 360 needs no Learn, but a Bluetooth Xbox gets chase and the OS overlay together.
- (c) A `Model` field naming its chase button. Right for every pad, but machinery for one row.
- (d) Take a button off the owner's layout.
- **[Rec] (a).** Go to (c) only if a second default wants it. Check on the 360 that GUIDE reads cleanly when held.

**NQ9. Keep on a taken knob.** (a) Ask Replace / Keep. (b) As a learn does today: replace, then say "let go". **[Rec] (a)** for a keep. Plain learn stays (b); changing it is out of scope.

**Still pending and touching this, not gates:** rows 654–656 (verb), 609–610 (FINE), 546, 552.

## 7. Docs each PR carries

The plan doc, `docs/DECISIONS.md` lines, register rows from the next free (685 is last on main; P2 and P3 take more, so read main at build), hand checks from the next free (519 is last on main, likewise), `docs/CHECKPOINT.md`, `docs/ARCHITECTURE.md` for the second page slot and the new cable kind.

## 8. Not verified

No code was run; this is a reading. Not checked: `ed.flow` in this imgui-bundle; `ui_desk`'s drawing of a page's knob (it has drawn page buttons only); Fn or PS behaviour on this macOS; GUIDE on the wired 360 with no overlay; `_passed_over` under a page. D5's shape comes from its plan, not from code, and may move. Plan 42's preset counts are from 2026-11-01 and I did not re-read the library, as instructed.
