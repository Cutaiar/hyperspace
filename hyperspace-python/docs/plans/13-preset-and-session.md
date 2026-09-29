# Plan 13 — Preset and session: two nouns, a latched desk, one load

**After plans 11 and 12.** Plan 12 composed five hand presets and, in doing
so, showed that the app has five nouns for saved state — module preset,
theme, project, routing preset, scene — split by which file system they
came from rather than by what they are. This plan replaces them with two,
settles what a load does, and gives the APC40 two layers under a latched
SHIFT so every preset can lay the desk out for itself without losing the
global controls. It is the design; the decisions were taken with the owner
on 2026-09-28 and are listed first so the rest can be checked against them.

Plans 11 and 12 are merged (main 4bffa9d); plan 13 runs from its WP1 and
supersedes plan 12's file shape (the five `party-*` presets are re-cut into
the new shape in WP5). §9 maps this design onto the code as it now is, §10
is the exit criteria, §11 the work packages as run, §12 the forks still
open.

## 1. Decisions

| # | decision |
|---|---|
| D1 | Two nouns. A **preset** is one file that holds everything a performance moment is. A **session** is the boilerplate that makes the rig ready to play and that a preset never touches. "Theme", "routing preset" and the UI word "scene" go away. |
| D2 | **A preset load replaces everything.** Every performance parameter lands, from the file or from the app's default when the file does not name it; every performer row is replaced; the desk's preset layer is replaced. No merging. |
| D3 | **Module presets stay** as a separate tool: a file of values for one group, cycled from that group's strip, replacing that group. A preset records the module preset each group was showing when it was saved, as a **label only**; loading the preset never chain-loads a module preset. |
| D4 | The APC40 has **two layers under a latched SHIFT**; the SHIFT LED shows which layer is up. Loading a preset drops to the preset layer. |
| D5 | The **global layer is fixed**: it lives in the session's files, is edited there, and is never the target of a Learn. A Learn writes only into the loaded preset. |
| D6 | A set of controls is **invariant**: one meaning on both layers, and no preset may map them. The faders, the preset-select row, SHIFT, TAP TEMPO, METRONOME, NUDGE ± and the transport are invariant. |
| D7 | On a layer switch the **knobs jump** to the layer's values (they are endless encoders the host re-bases); the **faders soft-pick-up**. Faders are invariant, so pickup only ever happens after a preset load moves a base. |
| D8 | A control a preset does not map **does nothing** and shows dark. No fall-through to the global layer. |
| D9 | The **analyzer is session**: its bands, dynamics, scene and the drive fader are never in a preset. |
| D10 | **One macro concept** (owner, 2026-09-28). A macro is a knob (`macro.1–8`, an ordinary param) with a list of **subscribers**. A subscriber either sets a target's **base** or scales a route's **depth** (attenuation), and each states its own **polarity** as a `from` → `to` range, so one knob can raise one thing while lowering another. The separate multi-target desk row is gone: a desk control that should move several things maps to one macro. §2.4 is the definition; a performer on a macro moves its depth subscribers only (plan 11 §2 row 19). |
| D11 | A session **names its startup preset**, loaded on launch. |
| D12 | A modifier is read **at the press**; SHIFT's release never re-evaluates a button already down. |

## 2. The nouns

### 2.1 Preset — `hyperspace.preset/2`

One file, `<library>/presets/<slug>.json`, factory ones in the package,
user ones in the home folder shadowing by name (as every group does today).

```json
{
 "schema": "hyperspace.preset/2",
 "name": "TRIP",
 "note": "…",
 "values":  {"view.shape": 10, "fx.kaleido.on": true, "macro.1": 1.0, …},
 "routes":  [{"source": "hand:7", "target": "fx.zoomblur.amount", "op": "push", "value": 0.8}, …],
 "desk":    [{"source": "cc:0:48", "target": "view.bright", "op": "abs"},
             {"source": "note:0:82", "target": "view.points", "op": "toggle"},
             {"source": "cc:0:51", "target": "macro.1", "op": "abs"}, …],
 "macros":  {"macro.1": {"label": "Heat", "subs": [
               {"base": "fx.plasma.level", "from": 0.0, "to": 0.6},
               {"base": "view.speed", "from": 0.8, "to": 0.3},
               {"depth": {"source": "hand:7", "target": "fx.zoomblur.amount"}, "from": 0.0, "to": 1.0}]}},
 "modules": {"fx": "trip", "dream": "wake"}
}
```

- `values`: every persisted performance parameter's base (§4 says which
  params are performance and which are session). A partial file is legal;
  unnamed ids land on the app default at load (D2).
- `routes`: the performer rows — `hand:`, `lane:`, `lfo:`, `ext:` sources,
  `push` / `position`, gate, rest — today's routing rows less a `scale`
  that names a macro (a depth subscriber replaces it, §2.4; a `scale` on
  a non-macro param is decision 18, §12).
  One performer per target; the referee settles a file with two.
- `desk`: the preset layer of the APC40, MIDI rows in today's form. A
  control that should move several things maps to a macro (D10). A row on
  an invariant control is dropped at load with a note (D6).
- `macros`: each macro's label and subscribers (§2.4). Routes no longer
  carry a `scale` field; a depth subscriber replaces it.
- `modules`: labels (D3).

Rotation phases stay out (a load changes the look, not where the spin is).
Macros are in (D10). Nothing session-level is in; a file that names a
session id gets a note and the id is ignored.

### 2.2 Session

The session is the home folder: `config.toml` (the rig), `hands.json`
(the box calibration), `bindings.json` (the session's controls), and the
project file. Plan 13 changes two of them.

`bindings.json` becomes the **session controls**: the keyboard and gamepad
rows as today, the **invariant** MIDI rows, and the **global-layer** MIDI
rows (`"layer": "global"` on the row). It no longer holds performer rows or
the preset layer; those moved into presets. It is still written by the app
(a keyboard learn, say) but the global-layer rows are never learned (D5).

The project file keeps its name (`<slug>.hyp.json`) and becomes:

```json
{
 "schema": "hyperspace.project/2",
 "name": "party",
 "startup": "TUMBLE",
 "bank": ["TUMBLE", "FACES", "FIELD", "WAKE", "TRIP", null, null, null],
 "session": {"tempo.bpm": 124, "band.0.post": 1.0, "hands.smooth": 1.0, …}
}
```

- `startup`: the preset loaded on launch (D11).
- `bank`: eight preset names (by name, not inline — a slot is a pointer to a
  preset file; F1–F8 and the preset-select row load it; ⇧F1–F8 save the live
  state *as* that preset, into the user folder).
- `session`: the session parameters' values (§4), landed on project load
  and never touched by a preset.

The `values`, `modules`, `io` and inline `bank` of schema 1 are migrated
(§6).

### 2.3 Module preset — `hyperspace.preset/1`, unchanged

A file of values for one group, in `<library>/<group>/`. Loading one
replaces that group's values (every id in the group: from the file or the
group's default). Its strip stays on the PRESETS page. The `bindings/`
folder and the ROUTING page's strip go away: routes live in the preset.

### 2.4 Macros — one concept (D10)

A **macro** is one knob, `macro.1` to `macro.8`, whose value `m` runs 0 to
1. It is an ordinary parameter: a desk control, the panel, or a preset
sets it, and a performer may own it. It does nothing on its own; it acts
through its **subscribers**, which live in the preset beside the routes.

A subscriber is one of two kinds:

| Kind | Written | What `m` does |
|---|---|---|
| base | `{"base": "<param id>", "from": a, "to": b}` | sets that param's base to `a + m · (b − a)`, measured along the param's own fader (norm units), so `from` and `to` are fader positions |
| depth | `{"depth": {"source": …, "target": …}, "from": a, "to": b}` | multiplies that route's depth by `a + m · (b − a)`; `from 0, to 1` is today's `scale` |

**Polarity is per subscriber.** `from > to` runs the other way, so one
knob can brighten the picture while slowing the spin, or deepen one route
while flattening another. A depth range may cross zero, which flips the
route's direction partway through the throw.

**Where it sits in the control model.** A base subscriber is a
scene-setter: it writes the base, never an offset, exactly as a knob on
the desk does. A performer on the same param still adds its offset on
top, and the macro moves the value the performer returns to. Two
scene-setters on one param do not compete: the last write wins, and the
ROUTING page marks a param that two macros set. A depth subscriber reads
the macro's effective value every frame, as `scale` does today, so a hand
riding a macro deepens or flattens its routes one frame later.

**A performer on a macro** (owner, 2026-09-28, plan 11 §2 row 19). Base
subscribers follow the macro's **base** only: the desk, the panel or a
preset moves them. Depth subscribers follow its effective value, so a
hand riding a macro deepens or flattens its routes and leaves the bases
alone. Letting a performer's macro move bases as offsets (the macro as a
performer of each param) is a later extension, not this plan.

**Migration.** A route with `scale: "macro.N"` becomes a depth subscriber
of `macro.N` with `from 0, to 1`; the route loses the field. Every factory
file is regenerated; a user file migrates on load with a note.

## 3. The desk

### 3.1 Three classes of control

| class | who defines it | on SHIFT up | on SHIFT down | Learn | in a preset file |
|---|---|---|---|---|---|
| **invariant** | the session (`bindings.json`) | same meaning | same meaning | no | dropped with a note |
| **global layer** | the session (`bindings.json`, `layer: global`) | dark, inert | its meaning | no | — |
| **preset layer** | the loaded preset's `desk` | its meaning, or dark if unmapped (D8) | dark, inert | yes, into the preset | yes |

SHIFT (note 0x62) latches the layer; its LED is lit while the global layer
is up. Loading a preset drops the layer (D4). Every ring and LED is redrawn
on a layer change and on a preset load, and only the up layer's values
show. The knobs are re-based by the same message that draws their rings;
the faders' catch state is cleared on a preset load (D7).

### 3.2 The sorted default map

Today's `apc40.DEFAULT_MAP` (113 rows), sorted by the decisions. QUANT
(`theme.next` today) is not in the tables below; it becomes `preset.next`
and is **invariant**, for D6's reason (switching presets is never behind
a layer). Names are
Akai's; "row n" is a clip-launch row across the eight tracks.

**Invariant** (D6, D9):

| control | parameter |
|---|---|
| track faders 1–6 | `band.0–5.post` |
| track faders 7, 8 | `master.dyn`, `master.trim` |
| MASTER fader | `master.gain` |
| crossfader | `overlay.bg` |
| clip row 1, 8 buttons | **preset select**, slots 1–8 (was `theme.select`) |
| SHIFT | the layer latch (new) |
| TAP TEMPO, NUDGE +, NUDGE − | `tempo.tap`, `tempo.nudge` ±1 |
| METRONOME | `lfo.trigger` (the global LFO trigger; its LED blinks on the beat) |
| PLAY, STOP, REC | `audio.play`, `audio.stop`, `audio.mic` |
| STOP ALL CLIPS | `scene.reset_all` (the analyzer's) |
| track select ×6, ◀ ▶ | `band.select` (set / step) |
| solo ×6, rec-arm ×6 | `band.N.fn`, `band.N.reset` |
| DEVICE ON/OFF, DETAIL | `ui.panel`, `ui.cheatsheet` |
| CLIP/TRACK | `audio.restart` |
| MASTER select, PAN | `overlay.on`, `overlay.passthrough` |

**Global layer** (SHIFT down; session-level things that want a knob):

| control | parameter |
|---|---|
| device knobs 1–8 | the open band's strip, `band.sel.trim / exp / trn / pre / post / atk / dec / thr` (as today, moved behind SHIFT) |
| track knobs 1–4 | hand feel: `hands.smooth`, `hands.response`, `hands.catch`, the selected axis's return |
| track knob 5 | `tempo.bpm` |
| track knobs 6–8 | free |
| clip row 2, 8 buttons + row 3, 3 buttons | `scene.select` 0–10, the analyzer's band scenes |
| everything else | dark |

**Preset layer, factory default** (what a fresh preset starts with):

| control | parameter |
|---|---|
| track knobs 1–8 | `view.bright`, `view.speed`, `view.instances`, `view.pattern_mix`, `view.inst_amp`, `view.inst_rate`, `view.bmp_alpha`, `camera.zoom` |
| device knobs 1–8 | free (a preset's own eight — plan 12's `wake` and `trip` put their bases here) |
| cue level | `view.shape` step |
| activator ×6 | `view.plane.ZW / XW / YW / XY / XZ / YZ` |
| clip row 3, buttons 5–8 | `view.inst_motion` STILL / ORBIT / WAVE / RIPPLE |
| clip rows 4–5 | `view.shape` 0–15 |
| scene launch 1–5 | `view.points`, `view.lines`, `view.faces`, `view.rotate`, `camera.reset` |
| ▲ ▼ | `view.bright` ±3 |

Two things this sorting changes on the desk: the band strip moves behind
SHIFT (its eight knobs are the ones a preset most wants), and the theme row
becomes the preset row. Everything else keeps its place on one layer or the
other.

### 3.3 Learn and edit

- Right-click → Learn, then turn a knob: a `desk` row into the loaded
  preset, which is now dirty. With SHIFT down, or on an invariant control,
  the learn is refused with the reason on the panel (D5, D6).
- A hand learn: a `routes` row into the loaded preset, as today's
  `position` route, through the same Replace / Keep prompt.
- The ROUTING page edits the loaded preset's `routes` and `desk`; the
  session's controls are edited in `bindings.json` by hand, and the page
  shows them read-only so a collision (a preset mapping an invariant
  control) is visible.
- Save (⇧F-key, the strip's save / as…) writes the live state as a preset
  file: `values` from the registry's performance params, `routes` and
  `desk` from the table, `modules` from the strips' current names.

## 4. What is performance, what is session

The split is by parameter group, declared once in `params.py` (today's
`ROUTING_GROUPS` becomes this), and the snapshot / restore helpers take it
from there.

| session (a preset never touches) | performance (a preset replaces) |
|---|---|
| `tempo.*` (the clock) | `view.*`, `rot.rate.*`, `camera.*`, `pattern.mod.*` |
| `hands.*` (setup and feel; calibration is `hands.json`) | `dream.*` |
| `band.*`, `master.*`, `scene.*`, `audio.*` (the analyzer and its source) | `fx.*` |
| `output.*`, `overlay.*`, `ui.*`, `app.*` | `lfo.*` |
| | `macro.*` |

`rot.phase.*` is neither: never saved. Plan 12's review found the TRIP
theme resetting a tapped BPM; under this table it cannot.

## 5. What a load does, in order

1. Read the file; note ids that are session-level, invariant desk rows,
   unknown ids, and second performers on a target.
2. Land `values`: every performance param, from the file or its default.
3. Replace every performer row with `routes` (referee first-wins).
4. Replace the preset layer with `desk`; drop the layer to preset (D4).
5. Redraw every ring and LED for the layer that is up; clear the faders'
   catch state.
6. Set the strips' labels from `modules`; mark the preset clean.
7. Report the notes from step 1 on the panel.

Rotation continues through a load (the integrator is untouched); a hand in
the box keeps performing (its rows may now point elsewhere, and its old
targets return to their new bases the frame the old rows are gone).

## 6. Migration, one-time, on first launch

- Each slot of a schema-1 project's `bank` becomes a preset file named by
  the slot (`values` from the slot; `routes` from the live `bindings.json`'s
  performer rows; `desk` from the sorted default map's preset layer;
  `modules` from the project's `modules`). The project becomes schema 2 with
  `bank` naming them and `session` holding the session-group values from
  the old `values`.
- `bindings.json`: performer rows move into the startup preset (the first
  filled slot); MIDI rows are sorted by §3.2; rows the sorting does not
  know keep the layer they are on (preset layer, into the startup preset).
- `library/bindings/*.json`: `legacy6`, `lfo-breathe` and the `hands-*`
  files become **full** presets (decision 10: no exception to D2 — each
  takes the factory default's values under its own); the five `party-*`
  files merge with their `party.hyp.json` slots into five full presets —
  plan 12's real deliverable in the new shape.
- The factory `library/projects/default.hyp.json` becomes eight factory
  presets (the house themes) and a schema-2 project naming them.
- `ROUTING_GROUPS`, `theme.*` params, the routing preset document kind
  (`Library.routing`, `Router.apply_doc` / `preset_doc`, `routing.PRESETS`)
  and `ui_routing`'s strip go; the F-keys and the preset row call the one
  loader. (`Presets` already went in plan 11, PR #52; audit L1 and L2
  closed there and in PR #58; R1 was decided (c) and dissolves here.)

## 7. Work packages and order

After plan 11's routing and library packages (they touch the same files):

| WP | what | size |
|---|---|---|
| 1 | The performance / session split in `params.py`; snapshot and restore over it; the session values in the project | S |
| 2 | Preset schema 2: loader, saver, referee; the library's one preset strip; F-keys and the preset row on it; module presets unchanged | M |
| 3 | The desk: `layer` on MIDI rows, the SHIFT latch, invariant set, redraw on switch and load, fader catch reset; the unified macro (§2.4: base and depth subscribers, per-subscriber polarity, `scale` migrated to depth subscribers) | M |
| 4 | Learn into the preset; refusals on the global layer and invariant controls; ROUTING page over the loaded preset | S |
| 5 | Migration of project, bindings and factory files; the five `party-*` presets re-cut; hand-check the rings and knob re-basing on the real desk | M |
| 6 | Docs: ARCHITECTURE §3.8 and the file table; DECISIONS; the plan 12 cards say "press F-key" only | S |

## 8. Settled since

Every question this section listed was answered by the owner on
2026-09-28 (DECISIONS.md, "Presets and the desk"; docs/DECISION-REGISTER.md
rows 9–13 and 12b):

- The global layer's track knobs: four hand-feel settings plus BPM, as a
  first cut; better global controls are expected to turn up with use.
- A routes-only file under D2: no exception; the migration turns it into a
  full preset.
- Bank slots name preset files.
- Macros: one concept (§2.4); a performer on a macro moves its depth
  subscribers only.
- The ROUTING page: one page over the loaded preset.

## 9. Against main

Checked against main **75f8ef7** (2026-09-28: plan 11 as PR #55, plan 12
as #47, the keys as #58, decisions 10–13 and 12b). What each section
above assumes, and what the code already gives it.

| Claim | Where it is today | What plan 13 changes |
|---|---|---|
| §4 the performance / session split "is `ROUTING_GROUPS`" | `params.ROUTING_GROUPS = ("macro",)`; `Registry.snapshot()` leaves it out of the whole surface; `Library.groups()` hides it; `Router.routing_values` saves the macros into `bindings.json`'s `values` | WP1: two tuples, `PERFORMANCE_GROUPS` (`view rot camera pattern dream fx lfo macro`) and `SESSION_GROUPS` (`tempo hands band master scene audio output overlay ui`), every persisted group in exactly one (a test walks the full registry); `snapshot(part=…)`; `ROUTING_GROUPS` goes. Those are all the groups the registry has; `rot.phase.*` is already `persist=False` |
| §2.2 the session's values in the project | `Project.values` is a whole-surface snapshot (session ids included), `Project.bank` holds eight inline `{name, values}` slots, `Project.modules` the module labels (`hyperspace.project/1`) | WP1 adds a `session` section and splits `values`; WP2 bumps to `hyperspace.project/2` (`startup`, `bank` of names, `session`) |
| §2.1 the preset file, "user ones shadowing by name (as every group does)" | `Library` already does list / shadow / load / save as / delete / dirty dot / watch for any folder, and for a foreign format through a **document kind** (`Library.kind(group, schema, load=, document=, signature=)`, plan 11 WP6); the routing presets are the one kind so far (`Library.routing` → `Router.apply_doc` / `preset_doc` / `signature`) | WP2 registers `presets/` as a document kind whose hooks are a new `preset.py` (`Presets`): the strip, shadowing, watch and dirty dot come for free. The routing kind goes in WP5 |
| §5 steps 2–3, "land values, replace routes, referee first-wins" | `Router.apply_doc` already replaces every performer row (`Bindings.set_routes`, referee first-wins into `table.dropped`) and restores `values`; `Library.defaults(group)` is the "app default" fill-in (the group's default module preset over the build values) | WP2 calls those two, over every performance group, not only the ids the file names |
| §3.2 the F-keys and the preset row | F1–F8 / ⇧F1–F8 and `R` are table rows (`routing.LOOP_KEY_ROWS` → `theme.load.k` / `theme.save.k`, PR #58); clip row 1 is `theme.select`; QUANT and `pad:B` are `theme.next`; `remap_factory` adds rows to older files where the key is free | WP2 renames the targets (`preset.load.k`, `preset.save.k`, `preset.select`, `preset.next` / `prev`) and remaps a user file's `theme.*` rows to them |
| §3 the desk | `MidiIO` routes every MIDI row with no notion of a layer; soft pickup on every `abs` row (`_apply`, `_uncatch_moved`); rings show the base, LEDs the state (R6, decided); `apc40.N_SHIFT` (0x62) is defined and unmapped | WP3: `layer` on MIDI rows, the latch, feedback per layer, the knobs re-based on a switch (check 31 is the hardware assumption) |
| §2.4 macros and `scale` | `Binding.scale` names **any** param whose effective value multiplies the depth. Factory files use it twice: `lfo-breathe`'s `lfo:1 → fx.mix × macro.1`, and **every legacy6 lane → `rot.rate` row, × `master.gain`** — that is how the MASTER (drive) fader drives the rotation, and the legacy6 parity anchor (`tests/test_core.py`) depends on it | WP3 turns `scale: macro.N` into a depth subscriber. `scale: master.gain` is not a macro, and D10's "routes lose `scale`" would take the drive fader off the rotation: **decision 18** (§12). Until it is answered WP3 leaves non-macro `scale` rows exactly as they are |
| §3.3 Learn | `learn.Learn` is the one armed id (plan 11 WP5): `MidiIO._learned` binds a MIDI row into the live table and writes `bindings.json`; `Learn.learn_source` places a hand `position` route through `replace_owner`, parking a conflict in `pending` for the Replace / Keep modal | WP4 points both at the loaded preset (dirty, not written) and adds the refusals |
| §3.3 the ROUTING page | `ui_routing.page`: the library strip over `bindings`, the macro strip, the performer rows (with a `scale` combo); MIDI rows are not shown | WP4: one page (decision 13) |
| §6 backups before a rewrite | `routing.backup(path, schema)` writes `<file>.bak-v<schema>` once, a dated copy when taken, never over any `.bak-*` (plan 11 WP8, audit R12) | WP5 reuses it for every file it rewrites (project, `bindings.json`, a user's `bindings/*.json`) |
| D9 "the analyzer is session" | Every house theme and every party slot sets `scene.select` (the eight house themes each pick a different band scene); `party-tumble` pushes `master.gain` with the left hand | The `scene.select` values drop at the migration — decided by D9, and felt: a house preset no longer changes the band scene. A route *onto* a session param is **decision 19** (§12) |
| Plan 12's cards, "F-key then the ROUTING strip" | A party scene loads in two steps (a theme, then a routing preset) | One step after WP5: the F-key |

Two sentences plan 11 made stale are fixed above (§2.1's `routes`, §6's
list of what closes). Two choices the design left open are taken here as
defaults, overturnable in review: QUANT and `pad:B` become `preset.next`,
invariant (§3.2's note); the macro group gets no module-preset strip (a
macro's meaning is its subscribers, which live in the preset).

## 10. Exit criteria (checked on merged main)

Headless, each held by a named test (the work package that adds it in
brackets):

- [ ] 1. Every persisted param is in exactly one of `PERFORMANCE_GROUPS` /
      `SESSION_GROUPS` — `test_params.py::test_every_persisted_group_is_performance_or_session` [WP1].
- [ ] 2. A preset load never touches a session param (a tapped BPM
      survives TRIP) — `test_presets.py::test_a_preset_load_never_touches_a_session_param` [WP2].
- [ ] 3. A preset load lands every performance base (the file's, else the
      group default) and replaces every performer row —
      `test_presets.py::test_a_preset_load_lands_every_base_and_replaces_every_route` [WP2].
- [ ] 4. Session ids and invariant desk rows in a preset are noted and
      ignored — `test_presets.py::test_session_ids_in_a_preset_are_noted_and_ignored`,
      `test_desk.py::test_a_desk_row_on_an_invariant_control_is_dropped_with_a_note` [WP2, WP3].
- [ ] 5. A slot names a file; an empty or dangling slot loads nothing and
      says so; ⇧F saves the live state as that preset in the user folder —
      `test_presets.py::test_a_slot_names_a_preset_file`,
      `::test_shift_f_saves_the_live_state_as_the_slots_preset` [WP2].
- [ ] 6. The startup preset loads on launch —
      `test_presets.py::test_the_startup_preset_loads_on_launch` [WP2].
- [ ] 7. Module labels are recorded and never chain-load —
      `test_presets.py::test_module_labels_are_recorded_and_never_chain_load` [WP2].
- [ ] 8. SHIFT latches and lights; a load drops to the preset layer; a
      modifier is read at the press —
      `test_desk.py::test_shift_latches_the_layer_and_lights_its_led`,
      `::test_a_preset_load_drops_to_the_preset_layer`,
      `::test_shift_release_never_reevaluates_a_held_button` [WP3].
- [ ] 9. On a layer switch the knobs are re-based and the faders pick up;
      a load clears the faders' catch —
      `test_desk.py::test_a_layer_switch_rebases_the_knobs_and_leaves_the_faders_to_pick_up`,
      `::test_a_preset_load_clears_the_faders_catch` [WP3].
- [ ] 10. An unmapped control is dark and does nothing; invariant controls
      mean one thing on both layers —
      `test_desk.py::test_an_unmapped_control_is_dark_and_does_nothing`,
      `::test_invariant_controls_mean_one_thing_on_both_layers` [WP3].
- [ ] 11. Two base subscribers of opposite polarity move opposite ways; a
      performer on a macro moves only its depth subscribers; `scale:
      macro.N` migrates to a depth subscriber —
      `test_macros.py::test_base_subscribers_of_opposite_polarity_move_opposite_ways`,
      `::test_a_performer_on_a_macro_moves_only_its_depth_subscribers`,
      `::test_scale_on_a_macro_migrates_to_a_depth_subscriber` [WP3].
- [ ] 12. Learn writes into the loaded preset and refuses the global layer
      and invariant controls —
      `test_learn.py::test_a_knob_learn_writes_a_desk_row_into_the_loaded_preset`,
      `::test_a_hand_learn_writes_a_route_into_the_loaded_preset`,
      `::test_learn_refuses_the_global_layer_and_invariant_controls` [WP4].
- [ ] 13. The ROUTING page is one page and fits —
      `test_ui_routing.py::test_the_routing_page_is_one_page_over_the_loaded_preset`,
      `test_ui_shell.py::test_every_page_fits_the_control_window` [WP4].
- [ ] 14. The migration: a schema-1 project, `bindings.json` and every
      routes-only file become presets and a schema-2 project, a backup kept
      before each rewrite and never over a hand-made `.bak-*` —
      `test_migration.py` [WP5].
- [ ] 15. The five party presets load by F-key as presets and still hold
      plan 12's rules — `test_plan12_presets.py` [WP5].
- [ ] 16. The control model holds: `tests/test_routing_boundary.py` (one
      caller of `Param.modulate`) and `tests/test_app_boundary.py` (the
      frame order, with the macro step in the scene-setter block) green;
      pytest green, ruff clean, ENGINEERING §6's count updated.
- [ ] 17. DECISIONS' plan 13 rows read "standing"; the register's notes say
      where each answer was built; ARCHITECTURE §3 and §3.8 describe the
      code [WP6].

At the machine: `11-hand-checks.md` group H (checks 33–41, with check 31
as its first step). Plan 13 is settled when the owner has run them.

## 11. Work packages as run

The suggested waves held, with one move: **WP2 converts the factory files
it needs** (the house themes and the party slots into factory presets,
generated from code the way the routing presets are today), because
without a factory bank the F-keys have nothing to load and WP2 nothing to
test. WP5 keeps every *user*-file migration and the real re-cut (desk
blocks, macros, the regenerated factory set).

| Wave | WP | Branch | Owns | Must not touch |
|---|---|---|---|---|
| 1 | WP1 split | `plan-13-wp1-split` | `params.py` (the two tuples, `snapshot(part=)`), `library.py` (`Project.session`, slot capture / restore over performance only, `groups()`), `routing.py` (`routing_values` names the macro group) | presets, desk, UI |
| 2 | WP2 preset/2 | `plan-13-wp2-preset` | new `preset.py`; `library.py` (`presets/` kind, `hyperspace.project/2`); `params.py` (`theme.*` → `preset.*`); `routing.py` (`LOOP_KEY_ROWS`, `keymap` / `padmap` targets, the `theme.*` remap); `apc40.py` (**target ids only**: clip row 1, QUANT); `ui_presets.py`; `app.py` (construction, startup load); `library/presets/`, `library/projects/` | `midi.py`, `learn.py`, `ui_routing.py`, row layers |
| 2 | WP3 desk + macros | `plan-13-wp3-desk` | `routing.py` (`Binding.layer`, `Macro` and its subscribers on `Bindings`, the `scale` migration, depth in `Router.modulate`, the macro base-follow step); `midi.py` (layers, latch, feedback, re-base, catch); `apc40.py` (**layers only**: the sorted map, the SHIFT row, the global track knobs); `hands/` (`hands.select`, the `hands.sel.return` alias); `app.py` (the macro step in the frame); `ui_routing.py` (only what removing `scale` forces) | target ids, `library.py`, `ui_presets.py` |
| 3 | WP4 learn + page | `plan-13-wp4-learn` | `preset.py` wiring (desk and macros into load and save); `learn.py`; `midi.py` `_learned`; `hands/core.py` `_learn`; `ui_routing.py` (the one page); `ui.py` (the refusal line) | file formats |
| 4 | WP5 migration + re-cut | `plan-13-wp5-migrate` | the migrations (`library.MIGRATIONS`, `Bindings.load`), removing the routing kind and `routing.PRESETS`, the factory generator's inputs, `library/bindings/` → `library/presets/`, `tests/test_plan12_presets.py`, `tools/preset_shots.py` | docs beyond its own lines |
| 4 | WP6 docs | `plan-13-wp6-docs` | ARCHITECTURE §3 / §3.8 / the file table, ENGINEERING, DECISIONS statuses, the register's notes, plan 12's cards, CHECKPOINT, plans README row 13, this plan's §13 | code |

**Contracts between them.**

- *WP1 → all.* `params.PERFORMANCE_GROUPS`, `params.SESSION_GROUPS`,
  `params.part_of(p) -> "performance" | "session" | None`,
  `Registry.snapshot(group=None, *, ids=None, part=None)`; from WP1 on the
  whole snapshot includes the macros.
- *WP2 → WP4, WP5.* `preset.Presets(lib, reg, router)` with `load(name)`,
  `load_doc(doc, path=None) -> notes`, `document(name) -> dict`,
  `save_as(name)`, `current`, `notes`; the file is §2.1's shape. WP2
  carries `desk` and `macros` **verbatim** (kept from the loaded file,
  written back on save) and applies neither; WP4 wires them. Bank params:
  `preset.load.0–7`, `preset.save.0–7`, `preset.select`, `preset.next` /
  `prev`, group `preset`, never persisted. WP2 does not migrate a *user*
  schema-1 project; it refuses one with a clear `Library.error` until WP5
  registers the migration.
- *WP3 → WP4, WP5.* MIDI rows carry `layer`: absent = invariant (the
  session defines the control), `"global"`, or `"preset"`.
  `Bindings.set_desk(rows) -> notes` replaces every preset-layer row,
  dropping with a note a row on an invariant source;
  `Bindings.desk() -> list[Binding]`; `Bindings.macros` with
  `set_macros(doc)` / `macros_doc()`; the adapter's `layer` and
  `drop_layer()`; `MidiIO.redraw()` (every ring and LED for the up layer,
  the knobs caught at the value just sent, the faders' catch cleared).
  Until WP4 and WP5 the preset layer and the macros persist in
  `bindings.json` (`layer: "preset"` rows, a `macros` key) so the desk
  works on its own branch; WP5 moves them into presets.
- *WP4 → WP5.* A learn marks the loaded preset dirty and never writes
  `bindings.json`; only ⇧F or the strip's save writes a preset.

## 12. Open forks

Filed in `docs/DECISION-REGISTER.md` (rows 18 and 19) with a pending line
in DECISIONS.md. Work that does not depend on them runs meanwhile.

| # | Fork | Recommendation | Blocks |
|---|---|---|---|
| 18 | **P13-h** The drive fader reaches the rotation as `scale: master.gain` on every lane → rotation route; D10 says routes lose `scale`. | (a) keep a route's `scale`, allowed only on a session param; macros move to subscribers | WP3's last step (it leaves those rows alone meanwhile) and WP5's factory regeneration |
| 19 | **P13-i** May a preset's route *perform* a session param (`party-tumble`'s left height pushes `master.gain`)? | (a) yes: D9 keeps the analyzer's settings out of a preset, and an offset is not a setting | WP5's re-cut of `party-tumble` |

## 13. As built

Filled as the work packages land: one line per deviation, with its PR.

- **WP1** (PR #62): `PERFORMANCE_GROUPS` / `SESSION_GROUPS` / `PARTS`, `part_of`, `snapshot(part=)` in `params.py`; `ROUTING_GROUPS` is gone and the whole snapshot carries the macros. A theme slot captures and restores the performance part only (a slot's `scene.select` stays in the file, ignored). `Project.session` is an additive `"session"` key under `hyperspace.project/1` (an old file's session ids are split out of `values` on read). The `app` group of §4 has no params (`app.restart` is `ui`, not persisted), so `SESSION_GROUPS` does not name it. Interim until WP5: the macros are in the project *and* `bindings.json`'s `values`; at startup the table's copy lands last and wins, so a project opened at launch shows dirty when its macros differ from the table's, and loading it again by hand does land its own. An open project fills the ids its file lacks (an old file's macros) from the state the load left, so it opens clean (review of PR #62).
