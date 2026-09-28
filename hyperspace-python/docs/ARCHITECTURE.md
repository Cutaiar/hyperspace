# Hyperspace — architecture

What the parts are, where a value goes each frame, and who may write a
parameter. This is the structure reference; behaviour is in
[`ENGINEERING.md`](ENGINEERING.md), the reasons in
[`DECISIONS.md`](DECISIONS.md), and what is currently wrong or drifting in
[`AUDIT-2026-09.md`](AUDIT-2026-09.md).

Written by plan 10 against `main` **ef299ef** (2026-09-27). Every
`file:line` is that commit; the symbol names will outlive the numbers.
When a boundary, the frame order or the control model changes, change the
line here in the same PR — this document exists so that a fix can be made
in the right place, first time, by someone who has never seen the repo.

Two questions it must answer from this file alone:

1. **Where does a given controller's value go each frame?** — §2 and §3.7.
2. **Who may write a given parameter?** — §3.2.

Paths are relative to `hyperspace-python/hyperspace/` unless they start
with `tests/` or `docs/`.

---

## 1. Component map

Hyperspace is one Python process: a parameter **registry** in the middle,
**sources** that feed a **routing table**, a **render stack** that reads the
registry's live objects, a **panel** that edits the registry, and a
**library** that saves and loads it. `app.py` builds everything once and
runs the one frame loop.

```mermaid
flowchart LR
    subgraph inputs [Input adapters]
        KEYS[keys · mouse<br/>app.Keys / app.Mouse]
        PAD[gamepad.Pad]
        MIDI[midi.MidiIO<br/>apc40 profile]
        HANDS[hands/<br/>HandsIO]
        BRIDGE[bridge.Bridge]
    end
    subgraph sources [Sources that are not inputs]
        AUDIO[audio.AudioEngine<br/>analyzer.Analyzer]
        LFO[lfo.LFOs<br/>tempo.Clock]
    end
    ROUTER[routing.Router<br/>the binding table]
    REG[(params.Registry<br/>base + offsets → objects)]
    subgraph render [Render stack]
        VIEW[render.ViewState]
        RENDER[render.Renderer<br/>geometry · fx · lookback · dream]
        OUT[overlay.Output]
    end
    subgraph panel [Control window]
        UI[ui.Panel + ui_* pages<br/>hands/panel]
        CTRL[control.Control]
    end
    LIB[library.Library<br/>presets · projects · config]

    KEYS -- "key:/rows → base" --> ROUTER
    PAD -- "pad:/hat: rows → base" --> ROUTER
    KEYS -- "nudge/scale → base" --> REG
    PAD -- "sticks → base" --> REG
    MIDI -- "cc/note rows → base" --> REG
    MIDI -- "learn → a route" --> ROUTER
    HANDS -- "feed hand" --> ROUTER
    BRIDGE -- "feed ext" --> ROUTER
    AUDIO -- "lanes" --> ROUTER
    LFO -- "feed lfo" --> ROUTER
    ROUTER -- "modulate → offset" --> REG
    REG -- "apply() writes objects" --> VIEW
    REG --> OUT
    REG --> CTRL
    VIEW --> RENDER
    UI -- "set → base" --> REG
    UI -- "edits rows" --> ROUTER
    LIB -- "restore → base" --> REG
    UI --> LIB
    REG -- "feedback reads base" --> MIDI
```

| Component | Modules | Owns | Reads | Writes | Boundary rule (held by) |
|---|---|---|---|---|---|
| **Registry** | `params.py`, `tapers.py` | every `Param`: id, kind, taper, flags, base, this frame's offsets | the live objects through each param's `get` | the live objects, once per frame in `Registry.apply()` | imports no adapter (`tests/test_params.py:286` for `midi`); it does import `fx`/`lookback` for their state classes, so it needs GL bindings importable (see audit) |
| **Routing table** | `routing.py` | `Binding` rows, the file `bindings.json`, the referee, the per-frame modulation pass | `Router.feeds` (what adapters fed), the analyzer's lanes, param bases | offsets via `Param.modulate` (`routing.py:1138`, the only caller in the package) | never imports `ui*`, `app`, `hands`; `glfw`/`gamepad` only lazily to resolve names (`routing.py:1182-1192`). Unenforced by a test |
| **Input adapters** | `midi.py` + `apc40.py`, `hands/`, `gamepad.py`, `bridge.py`, `app.Keys` / `app.Mouse` | a device; its own learn or pickup state | the table (discrete rows), param bases (MIDI pickup, feedback) | MIDI/keys/pads: the **base**; hands/bridge: only `Router.feed` | the core never imports `midi` or `bridge` (`tests/test_params.py:286`, `tests/test_bridge.py:381`); `hands/core.py` + `signal.py` import nothing from the package (`tests/test_hands_boundary.py`) |
| **Audio source** | `audio.py`, `analysis.py`, `analyzer.py`, `bands.py` | capture / playback, the FFT, N band lanes | the audio device | `analyzer.lanes` (read by `Router.modulate`); `band.*` params are views onto its objects | imports nothing from routing, ui or the render stack |
| **LFOs and clock** | `lfo.py`, `tempo.py` | four oscillators, one tap-tempo clock | their own dataclass fields (last frame's effective values) | `Router.feed("lfo", …)`, `labels`, `rests` | import **nothing** from `hyperspace` — registry, router, clock arrive as arguments (`tests/test_lfo_boundary.py`) |
| **Render stack** | `geometry.py`, `render.py`, `fx.py`, `lookback.py`, `dream.py`, `shaders/`, `overlay.py` | GL resources, `ViewState`, the frame history, the dream worker, the window's placement | `ViewState` and the `FxState` / `DreamState` objects the registry writes | the screen; `ViewState.integrate` writes `ang` directly (folded into the base next frame) | zero registry traffic; `dream` is imported lazily by `app.py:247` under `[dream] enabled` (`tests/test_dream.py:55-72`) |
| **Panel** | `ui.py`, `ui_*.py`, `hands/panel.py`, `control.py` | imgui state, page selection, the Replace / Keep modal, the routing page's edits | everything, for display | param **bases** through `Param.set*`; table rows through `Bindings.add/enable/remove/replace_owner` | a leaf: no engine module imports `ui*` (only `app.py:78` and `hands/panel.py:41`). Unenforced by a test |
| **Library** | `library.py`, `presets.py`, `config.py`, `library/` | the home folder, preset and project files, the F1–F8 bank, `config.toml` | `Registry.snapshot` | `Registry.restore` (bases) | depends only on `params` and `presets`; nothing imports it back except `config`, `bridge`, `dream` for `DEFAULTS`/`FACTORY` |
| **Host** | `app.py`, `hotreload.py` | the two windows, construction order, the frame loop, the reload watch list | — | the relative writers' bases (`nudge`/`scale`), `act()` for its four loop keys | the one cold module; the only importer of every optional adapter, each behind its config gate (`app.py:184-252`) |

The direction to remember: **everything points at the registry; the
registry points at nothing above it.** Adapters and sources feed the
router; the router writes offsets; the panel and the library write bases;
the render stack only reads.

---

## 2. The frame

`app.main()` (`app.py:392`) is the only entry point and the loop at
`app.py:504-641` is the only place the frame order exists. No test pins
it; read the loop when it matters.

```mermaid
sequenceDiagram
    autonumber
    participant W as glfw / imgui
    participant K as keys · pad · mouse<br/>(app.py)
    participant M as midi.MidiIO
    participant H as hands.HandsIO
    participant A as audio / analyzer
    participant B as bridge.Bridge
    participant L as lfo.LFOs
    participant R as routing.Router
    participant P as params.Registry
    participant V as render.ViewState
    participant D as Renderer / Panel

    W->>W: poll_events · new_frame · clock.tick(now)  app.py:509-522
    K->>R: router.keys(keys)  :532 — table rows → act() → base
    K->>P: R, ↑/↓, F1–F8 — loop keys → base  :533-548
    K->>R: router.pad(pad)  :554 — pad/hat rows → base
    K->>P: sticks, triggers → nudge/scale → base  :557-567
    M->>P: cc/note rows → set_norm/step/toggle → base  :572
    H->>R: feed("hand", lanes | None), labels, gates, rests  :579
    H->>M: a moved axis completes a learn → route or pending
    W->>W: output.apply() (reads last frame's objects)  :584
    K->>P: mouse orbit / pan / zoom → nudge/scale → base  :588
    A->>A: audio.step(dt) — new lanes  :594
    B->>R: feed("ext", …) · reads eff_norm out  :596
    L->>R: lfos.step · publish → feed("lfo", …)  :599-600
    R->>P: modulate(): every live performer row → p.modulate(offset)  :604
    P->>V: reg.apply(): base + Σoffsets → every object  :605
    V->>V: integrate(dt): ang += rate · dt  :606
    D->>D: renderer.draw(view)  :617
    D->>P: panel.draw(): widgets → base · modal → table  :626
```

Two rules follow from the order.

**One-frame lag.** Everything that a performer moves is landed by
`reg.apply()` once, at step 15. A source that reads a parameter — an LFO
reading its own `depth`, a route reading its `scale` macro, the bridge
sending `eff_norm`, `output.apply` reading `output.alpha` — reads what
`apply()` wrote **last** frame. So a hand that owns `lfo.1.depth` lands one
frame before that LFO's output does; a lane that owns `macro.2` scales its
dependent route next frame; and there is no recursion, because nothing in
the modulation pass reads a value it is about to write
(`tests/test_lfo.py:253-290`, `tests/test_routing.py:1310`).

**Base before offset.** Every scene-setter runs before `router.modulate`
(steps 2–11 and the panel at step 18, which is the previous frame's tail),
so a base write and the offsets on top of it are combined in one `apply()`.
The one writer after `apply()` is the rotation integrator (step 16), which
writes the object directly; `Param.apply` adopts that as a delta on the
base the next frame (`params.py:449-455`, `tests/test_modulation.py:198`).

Guarding: the step block (steps 11–16), `renderer.draw` and `panel.draw`
are each wrapped so hot-reloaded code that raises records
`reloader.runtime_error` and the loop continues (`app.py:592-628`).

---

## 3. The control model

This is the canonical statement. Where another document disagrees with
this section, this section is wrong only if the code is; check the cited
line, then fix whichever is lying.

### 3.1 The registry

Every settable thing is a `Param` with a stable id (`view.bright`,
`rot.rate.XY`, `band.2.atk`, `fx.acid.speed`, `lfo.1.depth`, `macro.3`), a
`Kind` — `CONTINUOUS`, `ENUM`, `TOGGLE`, `TRIGGER`, `TEXT` (`params.py:98`)
— and a `get`/`put` pair that reads and writes the live object it is a
view onto. Flags (`params.py:131-133`):

| Flag | Means | Default |
|---|---|---|
| `persist` | belongs in a snapshot (preset, theme, project) | on; triggers never |
| `modulatable` | a performer may drive it | on; off for rig settings (`output.monitor…`, every `hands.*`), UI state, aliases |
| `alias` | a view onto another param (`band.sel.*` follows the selection) | off; an alias neither persists nor modulates |

A continuous param has a **taper** (`tapers.py`): an integer position ↔
real value map with `unmap(map(p)) == p` on every detent
(`tests/test_control.py:27`). The user's setters snap to detents; the
modulation path maps floats through the taper without snapping, and a
tapered value's position is continuous between detents (`_taper_pos`,
`params.py:227-247`) so a sub-detent base survives under a performer.

**Base vs effective.** A param has no storage of its own until something
modulates it. `p.value` reads the object (the *effective* value);
`p.base`, `p.norm`, `p.position()`, `p.text()` read the user's *setting*.
They are the same thing until the first `modulate()` call adopts the
object's current value as `_base` (`params.py:428-431`); from then on
every setter writes `_base` (`params.py:197-202`) and `apply()` writes
`base + Σ offsets` to the object. The frame no source calls, `apply()`
writes the base back and forgets it (`params.py:444-448`,
`tests/test_modulation.py:151`).

**`Registry.apply()`** (`params.py:517-523`) runs once per frame over every
modulated param, in registry insertion order. Per param
(`params.py:437-477`): fold any direct object write since last frame into
the base as a delta; `target = base + offsets`; clamp or wrap; continuous
→ float through the taper; enum → nearest index with a dead-band
(`MOD_DEADBAND`, `params.py:95`); toggle → hysteresis about `MOD_ON` /
`MOD_OFF` (`params.py:94`); trigger → fire once on the rising edge, re-arm
below `MOD_OFF` (`tests/test_modulation.py:232-277`).

### 3.2 Who may write a parameter

Three classes of writer, and the model is that they never fight:

| Class | Writes | Who | Enforced by |
|---|---|---|---|
| **Scene-setter** | the **base** | panel widgets (`ui.py:683-807`); key / pad / hat rows via `routing.act` (`routing.py:443-468`); MIDI knobs, faders, buttons (`midi.py:431-482`); presets, themes, projects via `Registry.restore` (`library.py:520`, `routing.py:994/1148/1165`); the relative writers — mouse orbit / pan / zoom, sticks, triggers, ↑/↓ — via `Param.nudge` / `scale` (`app.py:330-372, 559-567`); the loop keys `R`, F1–F8 via `app.act` (`app.py:95`) | every setter ends in `Param.set`, which writes `_base` while modulated (`params.py:197-202`); `nudge`/`scale` read `self.base` (`params.py:368, 383`); `tests/test_modulation.py:180`, `tests/test_app_relative.py`, `tests/test_midi.py:272` |
| **Performer** | an **offset** | `Router.modulate` → `Param.modulate` (`routing.py:1138`) — the only caller in the package | grep; adapters only `feed` (`hands/core.py:758`, `lfo.py:170`, `bridge.py:228`). No test |
| **Object writer** | the live object, bypassing `Param` | the rotation integrator (`render.py:231`), `camera.reset` (`params.py:748-751`), `Control`'s scene / band resets (`control.py:56-133`), `mirror()` on the non-modulatable `hands.*` (`hands/core.py:449`) | `Param.apply` folds the delta into the base next frame (`params.py:449-455`, `tests/test_modulation.py:198`); non-modulatable params are never applied, so a direct write is simply the value |

Consequences to hold onto:

- A knob turned on a hand-owned parameter moves the **return value**, which
  shows when the hand's row lets go. It never prompts and is never blocked
  (decision 3; `tests/test_routing.py:1052`).
- A relative writer reads the base, never the effective value. Reading the
  effective value folded the whole offset into the base on every drag
  frame — plan 09's audit simulation 1 (`tests/test_app_relative.py:53`).
- MIDI ring feedback shows the base (`midi.py:502`) and never chases a
  performer; LED feedback on a toggle or enum reads the effective value
  (`midi.py:523-525`) and does. That asymmetry is real (audit).
- `Router.modulate` never checks ownership. The referee lives in the
  table's edit doors (§3.5); a table mutated directly could still stack two
  rows on one target.

### 3.3 Sources and rows

A `Binding` (`routing.py:279`) is one row: `source` (`scheme:address`),
`target` (a param id), `op`, `value`, `enabled`, and for performers
`scale`, `when`, `rest`; MIDI rows add `pickup`, `feedback`, `on`, `off`,
`ring`.

| Scheme | Address | Fed by | Reaches the param as |
|---|---|---|---|
| `key:` | a GLFW key name, optional `SHIFT+` / `SUPER+` | `Router.keys` (`routing.py:1013`) | a **discrete op** on the base |
| `pad:` / `hat:` | a `gamepad` button / hat name | `Router.pad` (`routing.py:1040`) | discrete op on the base |
| `cc:` / `note:` / `pitch:` | `channel:number` | `MidiIO._apply` (`midi.py:431`) | `abs` (with soft pickup), `rel`, `rel64`, `step`, `toggle`, `set`, `momentary` — all base |
| `lane:` | analyzer band index | `analyzer.lanes / CEIL` inside `Router.modulate` (`routing.py:1107`) | **performer** |
| `hand:` | axis index: 12 axes, 2 presence, 8 pinch switches | `HandsIO.poll` → `Router.feed("hand")` (`hands/core.py:758`) | performer; a switch may also be a gate |
| `ext:` | DAW lane 0–15 | `Bridge.step` → `Router.feed("ext")` (`bridge.py:228`) | performer |
| `lfo:` | 0–3 (`lfo:0` is "LFO 1"; param ids are 1-based) | `LFOs.publish` → `Router.feed("lfo")` (`lfo.py:170`) | performer |

`LANE_SCHEMES = ("lane", "ext", "lfo", "hand")` are the continuous
schemes (`routing.py:214`). A row on one of them may carry **only** the
two performer ops (`MOD_OPS = ("push", "position")`, `routing.py:215`;
`Bindings._check` raises otherwise, `routing.py:845-847`). The other ops
in `OPS` (`routing.py:216`) belong to keys, pads and MIDI.

### 3.4 The one path

Every continuous source reaches a parameter through exactly one pass,
`Router.modulate` (`routing.py:1102-1138`), once per frame, in table order:

1. Find the source's vector: the analyzer's lanes for `lane:`, otherwise
   `feeds[scheme]`. No vector, an out-of-range index or a `NaN` reading
   (a hand never yet seen) → the row does nothing this frame.
2. If the row has a gate (`when`), the gate's source must be **fed** and
   read ≥ 0.5; a gate whose source is not live holds the row **shut**
   (`Router.gated`, `routing.py:1063-1088`). `lane:` can never gate.
3. `depth = value × scale`, where `scale` names a param (a macro, say)
   whose **effective** value multiplies the depth; a missing scale param
   makes the row dormant (`routing.py:1121-1126`).
4. The op:
   - **push** — `offset = depth · (u − rest)`. The performer adds to the
     base, centred where the source rests. `rest` is the row's own number
     or, when `None`, the source's rest as its adapter published it this
     frame (`Router.rest_of`, `routing.py:1090`; hands publish each axis's
     configured rest, LFOs 0.5, the analyzer and the bridge nothing → 0).
     Idle adds nothing (`tests/test_routing.py:586`).
   - **position** — `offset = clamp(depth · u, 0, 1) − base_norm`. The
     source *is* the fader, along the param's taper; when it lets go the
     base returns (`tests/test_routing.py:641`).
5. `p.modulate(offset)` (`routing.py:1138`). Range, wrap, hysteresis and
   the return to base are all `Param.apply`'s job (§3.1).

A row whose source stops being fed (`Router.feed(scheme, None)`: the
tracker off, the DAW port gone) or whose gate opens simply stops calling
`modulate`, and `apply()` writes the base back that frame.

### 3.5 One performer per parameter

A **performer** is an enabled row on a continuous scheme with a performer
op (`Binding.is_performer`, `routing.py:366-370`). Disabled rows own
nothing; key, pad and MIDI rows never own. A target has at most one:

- `Bindings.owner(pid)` answers who (`routing.py:826`).
- `Bindings.add` and `bind` raise `Owned(existing, new)` when the target
  has a different performer (`routing.py:841-853, 888-894`); the table is
  untouched. Waking a disabled row (`enable`) runs the same check
  (`routing.py:924-936`).
- `Bindings.replace_owner(new, *, target=None)` is the **one door** onto a
  taken target: it removes whoever owns it *at commit* and adds or
  retargets the new row (`routing.py:896-922`). Every *Replace* in the app
  is that call (`ui_routing.py:206, 237, 243`; `midi.py:380`).
- Loading a file or a preset runs `referee()`: first performer per target
  wins in file order, the rest go to `table.dropped` with a reason, shown
  on the ROUTING page until the next edit (`routing.py:556-573, 768, 945`).
- Gates do not exempt a row: two rows on one target with different pinches
  are two performers (decision 2).

Tests: `tests/test_routing.py:892-1009` (the referee), `:1029-1095` (the
four audit simulations), `:1359` (every factory preset has one owner per
target).

**The Replace / Keep prompt.** A conflicting learn or edit is *held*, not
applied:

- A hand learn goes through `MidiIO.learn_source` (`midi.py:323-355`): if
  another performer owns the target the pair is parked in `MidiIO.pending`
  and nothing is written. A learn onto a target the same axis already
  positions only refreshes the gate.
- A ROUTING-page add, enable or retarget that raises `Owned` parks in the
  page's own state (`ui_routing.py:225-231`).
- `ui_routing.modal` is drawn first thing in `Panel.draw`, on **every**
  page, panel collapsed or not (`ui.py:938`), reading whichever question is
  up (`_question`, `ui_routing.py:245-266`). *Replace* →
  `replace_owner` and the file is written; *Keep* → the table is untouched
  (`tests/test_routing.py`,
  `test_the_replace_prompt_swaps_the_owner_or_leaves_the_table`;
  `tests/test_midi.py:387`).
- While a question is up `MidiIO.learning` is `None`, so moving the hands
  learns nothing more (`hands/core.py:812-814`, `tests/test_hands.py:521`).

### 3.6 Chaining, not stacking

Layers come from the graph, never from two rows on one knob. Every knob
of an LFO (`lfo.N.shape/rate/sync/depth/phase`) and every macro
(`macro.1–8`) is an ordinary, ownable, persistent param, so:

```
hand:7 ──position──▶ lfo.1.depth      lfo:0 ──push──▶ view.bright
lane:0 ──push──▶ macro.2              hand:1 ──position──▶ fx.mix  ×scale macro.2
```

The eight macros exist only to be a route's `scale` and to be owned
(`params.py:823-836`). They are **routing-layer state**
(`ROUTING_GROUPS = ("macro",)`, `params.py:83`): outside the whole-surface
snapshot a theme or project takes, inside a routing preset's `values` and
the live `bindings.json`'s `values`, landed at startup by the first
`Router` built over the table (`routing.py:977-994`,
`tests/test_routing.py:1449`). LFO and tempo params are **not** in
`ROUTING_GROUPS`: they are theme state, though the `lfo-breathe` routing
preset also writes three of them as `values` (audit).

### 3.7 Where a controller's value goes

| You move… | It becomes… | Writes | Path |
|---|---|---|---|
| a panel fader, combo, checkbox | `Param.set_position` / `set` / `toggle` | base | `ui.py:683-807` → `params.py:197` |
| a key with a table row (`B`, `F`, `1–6`, …) | `routing.act` on the row | base (step / toggle / fire / set) | `app.py:532` → `routing.py:1013` → `:443` |
| `R`, F1–F8, ⇧F1–F8, Cmd+R, Esc/Q | loop code in `app.py` | base (fire) / restart / quit | `app.py:529-548` — the four keys outside the table |
| ↑ / ↓ | `_ride_depth` on `view.depth4` | base, relative, in log space | `app.py:539-544, 369-372` |
| mouse drag / shift-drag / wheel | `Mouse.poll` → `nudge` / `scale` on camera params | base, relative | `app.py:320-366` |
| a pad button or hat | `routing.act` on the row | base | `app.py:554` → `routing.py:1040` |
| a stick or trigger | `nudge` / `scale` / `_ride_depth` | base, relative | `app.py:557-567` |
| an APC40 knob or fader (`abs`) | `Param.set_norm` after soft pickup; ring feedback shows the base | base | `midi.py:473-482, 491-518` |
| an APC40 button (note) | `momentary` / `toggle` / `step` / `fire` | base | `midi.py:435-447` |
| an APC40 knob on a **hand-owned** param | the same — it moves the return value | base | decision 3; `tests/test_routing.py:1052` |
| an analyzer band | `lane:<i>` → its performer row | offset | `routing.py:1107` |
| a hand axis | `hand:<i>` → its performer row (push or position) | offset | `hands/core.py:758` → `routing.py:1102` |
| a pinch | `hand:<14+…>` — a lane like any other, and a gate for rows whose `when` names it | offset, or opens / shuts a row | `hands/core.py:688-696`, `routing.py:1063` |
| a DAW lane in | `ext:<i>` → its performer row | offset | `bridge.py:228` |
| an LFO | `lfo:<i>` → its performer row | offset | `lfo.py:170` |
| right-click → Learn, then move a hand | `MidiIO.learn_source` → a `position` row, or the prompt | the table | `hands/core.py:808-832` → `midi.py:323` |
| right-click → Learn, then turn a knob | `MidiIO._learned` → an `abs` / `rel` / `toggle` MIDI row | the table | `midi.py:296-321` |
| a preset, theme or project | `Registry.restore` | base | `library.py:520` |
| a routing preset | `Bindings.set_routes` + `reg.restore(values)` | the performer rows and the macros | `routing.py:1150-1165` |

### 3.8 The binding file

`<home>/bindings.json`, schema `hyperspace.bindings/2` (`routing.py:205`):
`{"schema", "profile", "bindings": [rows], "values": {macro ids}}`. Rows
carry only non-default fields. It is the live table — keys, pads, MIDI and
performer rows in one file — written on every edit (`Bindings.write`,
`routing.py:791`), which also refreshes `values` from the registry.

On load (`Bindings.load`, `routing.py:702-738`):

- no file → the factory table (`keymap + padmap + apc40.DEFAULT_MAP +
  legacy6_routes`, `routing.py:696`); an old `midi_map.json` beside it is
  merged once;
- schema 1 → `migrate_v1` renames the ops (`mod → push`, `span →
  position`, lane `abs → position`; `replace` is dropped with a note)
  and `referee` settles duplicate owners (`routing.py:576-599`);
- **every** load runs `remap_factory` (`routing.py:602-631`): the plan-09
  moves (TAP TEMPO, NUDGE ±, METRONOME, `B`, `⇧B`) applied only where the
  user's table still has the exact old factory row or nothing on the
  source; idempotent;
- anything migrated or remapped is announced on stderr and written back
  once; an unknown schema is never rewritten — the factory table stands
  in and `Bindings.error` says why (`tests/test_routing.py:1138-1285`).

Routing **presets** (`library/bindings/*.json`, user files shadow factory
ones) carry only performer rows and `values`; loading one replaces every
performer row — learned hand rows included — and leaves key, pad and MIDI
rows alone (`routing.py:1150-1165`). The factory set is generated from
code by `python -m hyperspace.routing` and pinned by
`tests/test_routing.py:393`.

### 3.9 Tempo and the LFOs

`tempo.Clock` (`tempo.py:60`) is one free-running clock. `tick(now)` once
a frame makes every call in that frame agree on the time (`app.py:522`).
`tap()`: taps more than 2 s apart start a new burst; BPM is the mean
interval of the burst's last 8 taps, clamped 20–300 (`tempo.py:82-98`).
`beat(t) = (t − t0) · bpm / 60 + nudge`; `bar` is beat mod 4. Params
`tempo.bpm`, `tempo.tap`, `tempo.nudge` (`tempo.py:138-156`).

**The global LFO trigger** (`lfo.trigger`, `lfo.py:181`; `⇧B`, the APC40's
METRONOME) sets the downbeat to now — folding the current nudge in so beat
0 lands on the press (`tempo.py:110-118`) — and restarts every LFO in a
division mode at phase 0 together; Hz LFOs are untouched. Once the clock
has been triggered, a tap changes the BPM and not the downbeat, so a
re-tap mid-set moves the readout, not the picture (`tempo.py:93-98`,
`tests/test_lfo.py:98-140`). Before the first trigger a tap does re-pin the
downbeat (audit: the docstring says otherwise).

`lfo.LFOs` (`lfo.py:130`): four. Per LFO `shape` (sine, tri, saw, square,
random = sample-and-hold per cycle), `rate` (Hz, log 0.01–20), `sync` (Hz
or a bar division), `depth`, `phase`, and a `reset` trigger. In Hz the
phase integrates `rate · dt`; in a division it is `clock.beat · ratio +
phase` (`lfo.py:106-119`). Output `u = 0.5 + 0.5 · depth · wave`, rest
0.5, published every frame (`lfo.py:167-172`). An LFO is a performer and
every one of its knobs is ownable; it reads its knobs from its own
dataclass fields, i.e. last frame's effective values, which is the whole
one-frame-lag / no-recursion mechanism (§2).

### 3.10 What this section does not promise

Behaviour the code has today that the model above does not describe, all
filed in [`AUDIT-2026-09.md`](AUDIT-2026-09.md):

- A hand leaving the box with the tracker still on does **not** release a
  `position` row: the axis springs to its rest value and the row keeps
  positioning the param there. Only the tracker going dark feeds `None`
  (`hands/core.py:693`, `signal.py:124-131`).
- Hand Learn lives in the MIDI adapter object; with `[midi] enabled =
  false` there is no hand Learn.
- Nothing in `Router.modulate` checks ownership.
- `tempo.tap`, `lfo.trigger` and `lfo.N.reset` are modulatable by default.

---

## 4. Module shapes

One screen per module or package, in the component map's order. *Public
surface* is what other modules or tests use; *must never* is the invariant
and what holds it; *tests* is where to look first.

### 4.1 `params.py` — the registry

**Purpose.** One address space for everything the surface can set; base
vs effective; the once-per-frame `apply()`.
**Public surface.** `Kind`, `Param` (`value base norm eff_norm modulated
set set_value set_norm set_position step nudge scale cycle toggle fire
text position modulate apply`), `Registry` (`add get group remove
remove_prefix apply snapshot restore continuous enum toggle trigger text`),
`build_registry(view, control, audio, presets, dream=, fx=)`,
`ROUTING_GROUPS`, `PLANES`, `PATTERNS`, `ROT_RATE_MAX`.
**Must never.** Import an adapter (`tests/test_params.py:286`). Snapshot a
macro into the whole surface (`params.py:540-541`). Snap a modulated base
to a detent (`_taper_pos`). Iterate the live dict while a trigger changes
the layout (`params.py:521`, a list copy).
**Tests.** `tests/test_params.py`, `tests/test_modulation.py`.

### 4.2 `tapers.py`

**Purpose.** Integer position ↔ real value maps (`exp_zero`, `exp_pure`,
`exp_time`, `lin_t`, `lin_db`), the module tapers (`T_BRIGHT`, `T_SPEED`,
`T_DEPTH`, …), formatters, and the band knob specs `KNOBS`.
**Must never.** Break `unmap(map(p)) == p` on any detent
(`tests/test_control.py:27`). Import from the package (it does not).
**Tests.** `tests/test_control.py:13-56`.

### 4.3 `routing.py` — the binding table

**Purpose.** One `Binding` model for keys, pads, MIDI and performers; the
file, the referee, the per-frame modulation pass.
**Public surface.** `Binding` (+ `describe is_performer to_json
from_json`), `Bindings` (`load factory from_json write of routes owner
route for_param bind unbind add replace_owner enable remove set_routes`;
`values dropped notes error`), `Router` (`keys pad feed gated rest_of
modulate describe apply_preset load_preset save_preset`; `feeds labels
gates rests missing_values`), `Owned`, `act`, `bindings_path`,
`MOD_OPS`, `OPS`, `LANE_SCHEMES`, `SCHEMA`, `keymap`, `padmap`,
`PRESETS`, `migrate_v1`, `remap_factory`, `referee`.
**Must never.** Let a lane-scheme row carry a non-performer op
(`_check`). Let two enabled performers share a target through its edit
doors (`tests/test_routing.py:892-1009`). Write a base from `modulate`.
Rewrite a file of unknown schema (`tests/test_routing.py:1212`). Touch a
user's row on a moved note or key in `remap_factory`
(`tests/test_routing.py:1231`). Import `ui*`, `app`, `hands` (unenforced).
**Tests.** `tests/test_routing.py` (1528 lines: parity anchor, grammar,
factory table, adapters, Router, referee, the four audit simulations,
migration, macros, presets).

### 4.4 `midi.py` + `apc40.py` — the MIDI adapter and the device profile

**Purpose.** `Ports` (open, reconnect), `MidiIO` (poll → `_apply` rows
with soft pickup; `feedback` rings and LEDs; `learn`, `learn_source`,
`pending`, `resolve_pending`), `MidiMap` (a thin view over `Bindings`).
`apc40.py`: port match, mode SysEx (`enter`/`leave`), LED colours, ring
styles, `DEFAULT_MAP` (113 rows), `N_TAP`/`N_NUDGE_*`/`N_METRO`/`N_QUANT`.
**Must never.** Be imported by the core (`tests/test_params.py:286`).
Write an offset (every path ends in `set_norm`/`step`/`toggle`/`fire`/
`act`). Let a ring chase a performer (`midi.py:502`,
`tests/test_midi.py:272`). Apply or lose a held learn silently
(`midi.py:281-285, 351-354`). Fire a note release as a bind
(`midi.py:423`).
**Tests.** `tests/test_midi.py`; `apc40` indirectly there and in
`tests/test_routing.py:374` (the remap tables pinned to `DEFAULT_MAP`).

### 4.5 `hands/` — the Ultraleap instrument

**Purpose.** `core.py`: `features()` from a Leap hand, `HandSettings` /
`AxisSettings` (the setup, registered as non-modulatable `hands.*`
params), `LeapSource` (the SDK on its own thread), `HandsIO.poll(dt,
midi, router)` — 12 axes + 2 presence + 8 pinch switches → `Router.feed`
+ `labels` + `gates` + `rests`, MIDI out to a DAW, Learn hand-off, box
calibration. `signal.py`: the pure per-axis chain (`shape`, `Follower`,
`quantize`, `encode`). `panel.py`: the HANDS page and the context menu's
hand rows.
**Public surface.** `HandsIO`, `HandSettings.from_config`, `register`,
`features`, `mirror`, `conflicts`, `SIDES`, `FEATURES`, `PINCHES`,
`GROUP`; `panel.page`, `panel.ctx_rows`.
**Must never.** `core.py` / `signal.py` import from `hyperspace`; only
`panel.py` knows the host (`tests/test_hands_boundary.py`). Write a
param (they declare and feed only). Touch the registry or Router from
the SDK thread (`core.py:567-568`, unenforced). Change the lane order
under a saved `hand:<i>` (`tests/test_hands.py:391`). Let a gate open on
a source that is not live (`tests/test_hands.py:752`). Learn while a
question is up (`tests/test_hands.py:521`).
**Tests.** `tests/test_hands.py`, `tests/test_hands_boundary.py`.
`LeapSource` itself is untested (no fake SDK).

### 4.6 `lfo.py` + `tempo.py`

**Purpose.** `tempo.Clock` (`tick tap set_bpm trigger beat bar on_beat`;
params `tempo.bpm/tap/nudge`), `lfo.LFOs` (`step publish reset trigger`;
params `lfo.N.shape/rate/sync/depth/phase/reset`, `lfo.trigger`).
**Public surface.** `Clock`, `LFOs`, `LFO`, both `register(reg, …)`
functions, `SHAPES`, `SYNCS`, `REST`, `GROUP`, `BEATS_PER_BAR`.
**Must never.** Import from `hyperspace` at all (`tests/test_lfo_boundary.py`).
Read a `Param` (they read their own fields — that is the one-frame lag).
Move a running synced LFO on a tap once triggered
(`tests/test_lfo.py:98`). Touch a Hz LFO or the nudge from the global
trigger (`tests/test_lfo.py:118-156`). Declare twice. Read the wall clock
after construction (`tests/test_tempo.py:149`).
**Tests.** `tests/test_lfo.py`, `tests/test_tempo.py`,
`tests/test_lfo_boundary.py`, `tests/test_ui_lfo.py` (the page).

### 4.7 `geometry.py`

**Purpose.** The 25 shapes (18 polytopes, 7 trig-equation surfaces) as
unit-circumradius vertex / edge / face arrays; `project_h` (the renderer's
transform) and `project` (the parity oracle); faces, triangles, UVs.
**Public surface.** `SHAPES`, `Shape`, `geom(i)`, `RATE`, `project_h`,
`project`, `faces`, `face_triangles`, `face_uvs`, `PLANES` (index pairs).
**Must never.** Change the first 18 shapes' vertex or edge order
(`tests/test_core.py:33`, `tests/test_shapes3d.py:16`). Return an
un-normalised shape. Import from the package (it does not; unenforced).
**Tests.** `tests/test_core.py:33-53`, `tests/test_shapes3d.py`,
`tests/test_golden.py`.

### 4.8 `render.py`

**Purpose.** `ViewState` (the live object the `view.*`, `rot.*`,
`camera.*`, `pattern.*` params write; `integrate` advances `ang`) and
`Renderer.draw` — scene pass into an MSAA target (faces through
`patterns.glsl` + bitmap, edges as quads, points), the coverage mask,
look-back capture / composite, the FX chain, to the window.
**Public surface.** `ViewState`, `Renderer` (`draw draw_scene on_reload
bg_alpha lookback fx scene pattern_error bitmap_error`),
`render_offscreen`, `N_MOD`.
**Must never.** Import audio, input, params or routing (plan 02;
unenforced). Write `ViewState` from `draw`; write anything but `ang` from
`integrate` (unenforced). Differ from `draw_scene` when look-back and FX
are off (`tests/test_render.py:306`). Capture the effected frame into the
history (`render.py:474-477`). Read `u_bands` (`tests/test_render.py:231`).
**Tests.** `tests/test_render.py`.

### 4.9 `fx.py` + `shaders/fx/`

**Purpose.** One GLSL file per effect; `// @param` uniforms become
`fx.<file>.<key>` params plus `on mix speed blend order`; `FxState` is
their object; `FxChain` compiles and runs the enabled passes ping-pong
after the composite, polling the folder every 30 frames.
**Public surface.** `FxState`, `FxChain`, `declare`, `parse`, `FX_DIR`,
`BLENDS`.
**Must never.** Define an effect in Python. Let a broken edit take the
frame down (`tests/test_fx.py:194, 293`). Leave alpha below the brightest
channel (`fx.py:381`). Change the frame when off (`tests/test_fx.py:268`).
**Tests.** `tests/test_fx.py`.

### 4.10 `lookback.py` + `dream.py`

**Purpose.** `Lookback`: the echo atlas, the dream buffer `D`, chroma,
occlusion, the age-weighted premultiplied composite; `DreamState` is the
`dream.*` object. `DreamWorker` (optional, torch): temporal Deep Dream on a
thread, fed the newest echo, latest result wins.
**Public surface.** `Lookback`, `DreamState`, `LAYERS OCTAVES RES
TINT_FROM MAX_ECHOES`, `tint_colour`; `DreamWorker` (`submit latest status
close`), `guard_step`.
**Must never.** Import `dream` from the core; import torch outside
`dream.py` (`tests/test_dream.py:55`). Block the frame in `submit`
(`tests/test_dream.py:151`). Re-tint the echoes (`tests/test_lookback.py:405`).
Read the registry from the worker thread (`dream.py:378`, unenforced).
Reload out of order (`tests/test_dream.py:94`).
**Tests.** `tests/test_lookback.py`, `tests/test_dream.py` (worker tests
skip without torch).

### 4.11 `overlay.py`

**Purpose.** `Output`: the render window's placement (window · fullscreen
· overlay, passthrough, opacity, background) as `output.*` params, applied
once a frame through an injectable backend; `overlay.*` are aliases.
**Must never.** Touch the window system outside `apply()`
(`tests/test_overlay.py:115`). Persist or modulate the rig settings
(`tests/test_overlay.py:86`). Raise a backend error into the frame.
**Tests.** `tests/test_overlay.py`.

### 4.12 `ui.py` and the pages

**Purpose.** `Panel` (rail, pages, footer, cheat sheet, meters, the
context menu) and the widget helpers; every widget is a view onto one
`Param` and writes its base. Pages are functions over the panel:
`ui_bands` (spectrogram band editor), `ui_fx`, `ui_lfo`, `ui_lookback`,
`ui_presets` (strips, project row, theme bank), `ui_routing` (the matrix,
macros, the Replace / Keep modal), `hands/panel` (HANDS).
**Public surface.** `Panel(.draw)`, `apply_style`, `load_fonts`, `PAGES`,
`PAGE_KEYS`, `CHEATSHEET`, `chip`, `lit_chip`, `chip_w`, `button_w`;
each page's `page(panel)`; `ui_routing.modal`, `ctx_item`;
`ui_presets.strip`, `dirty`.
**Must never.** Be imported by an engine module (a leaf; unenforced).
Call `Param.modulate` (grep). Write a param's live object directly (the
helpers only call `set*`). Park the prompt behind a hidden panel
(`ui.py:938`, `tests/test_ui_bands.py:436`). Scroll a page at
`app.CONTROL_SIZE` (`tests/test_ui_shell.py:92`; ROUTING's rows scroll in
a child by design). Reuse an imgui id (`tests/test_ui_lfo.py:86`).
**Tests.** `tests/test_ui_shell.py`, `tests/test_ui_bands.py` (also the
ROUTING page), `tests/test_ui_lfo.py`, the page tests in `test_fx`,
`test_lookback`, `test_hands`.

### 4.13 `control.py`

**Purpose.** Headless panel state the registry's `scene.*` and `band.*`
params act on: band selection, scene select, reset with the 8 s undo,
band add / remove / move and the `on_layout` hook that rebuilds `band.*`.
**Must never.** Reset to hard-coded defaults instead of the selected scene;
keep an undo across a scene change (`tests/test_control.py:74-112`).
**Tests.** `tests/test_control.py` (its transport / loopback / face-count
tests are misfiled there — audit).

### 4.14 `library.py` + `presets.py` + `config.py`

**Purpose.** The home folder (`$HYPERSPACE_HOME`, default `~/Hyperspace`);
one JSON per module preset (`hyperspace.preset/1`, a group's snapshot,
user shadows factory); projects (`hyperspace.project/1`, the whole
snapshot plus the F1–F8 bank); `Presets` is the bank's view; `config.load`
reads `config.toml` with defaults for `[midi] [overlay] [bridge] [dream]
[hands]`. Routing presets are `routing.py`'s, not the library's.
**Public surface.** `Library` (`attach on_layout groups list load save_as
overwrite delete reset is_dirty restore report poll home project bank`),
`LibraryError`, `home()`, `slug`, `FACTORY`; `Presets` (`save load
cycle slots active`), `SLOTS`; `config.load`, `config.DEFAULTS`.
**Must never.** Write a factory file (`tests/test_library.py:164`). Carry
a macro in a theme or project (`tests/test_library.py:123`). Move a
rotation phase (`tests/test_presets.py:73`). Restore anything but the base
(`Registry.restore`). Apply values before the analyzer's layout
(`tests/test_library.py:240`). Stop the show on a bad file.
**Tests.** `tests/test_library.py`, `tests/test_presets.py`, the factory
tests in `tests/test_routing.py`.

### 4.15 `app.py` + `hotreload.py` + `gamepad.py` + `bridge.py`

**Purpose.** `app.main()`: two GLFW windows in one share group (render:
vsync, MSAA, transparent; control: imgui only), construction in a fixed
order (`app.py:392-497`), the loop (§2), `_restart` (execv). `Keys`
(edge / hold, defers to imgui typing), `Mouse` (orbit, pan, zoom about
the cursor). `hotreload.HotReloader`: watches `MODULES`, reloads the
changed module and everything after it, re-classes live instances, calls
`on_reload`. `gamepad.Pad`: raw GLFW joystick with the Xbox index map.
`bridge.Bridge`: analyzer lanes / param norms out as 14-bit MIDI; the same
forms in as `ext` lanes.
**Must never.** Import `midi`, `bridge`, `hands`, `dream` at module level
(lazy, gated; `tests/test_dream.py:85` covers dream). Run imgui on the
render window. Let a broken adapter or a raising reload stop the show.
Read the effective value into a base from a relative writer
(`tests/test_app_relative.py`). `bridge`: write a Param
(`tests/test_bridge.py:272`); be on by default (`:392`). `hotreload`: reload
anything when a changed file does not parse (`tests/test_hotreload.py:202`).
**Tests.** `tests/test_app_relative.py`, `tests/test_overlay.py`,
`tests/test_gamepad.py`, `tests/test_hotreload.py`, `tests/test_bridge.py`.
The loop order, `Keys`, `Mouse` and the `_open_*` gates have no test.

### 4.16 `audio.py` + `analysis.py` + `analyzer.py` + `bands.py`

**Purpose.** `AudioEngine`: one capture (mic / loopback device) or file
player through a callback and a ring buffer; owns `analyser`
(`analysis.Analyser`, a Web-Audio-faithful FFT front end: 4096, Blackman,
0.15 smoothing) and `chain` (`analyzer.Analyzer`, the one chain that runs:
N bands 1–16, per band centre / Q / curve, then the ported envelope,
transient, expansion, coupling, shaper stages; `lanes = out` in
`[0, CEIL)`; a 4 s spectrum history). `bands.py` is the parts bin: the
constants under their reference names, `soft_ceil`, the 13 `SHAPERS`, the
per-band `Params`, the 11 `PRESETS` scene rows, and a `Chain` alias that
resolves to `Analyzer`. `offline.py` runs a WAV through the chain for
tests. The transport: `toggle_play`, `restart`, position from the output
callback's frame count; pause keeps feeding silence so the bands decay.
**Public surface.** `AudioEngine` (`chain analyser on mode start_mic
start_file stop step toggle_play restart position duration`),
`input_devices`, `is_loopback`; `Analyzer` (`lanes n band_names inp out
spec params st step apply_layout add_band remove_band move_band set_band
history band_curve apply_preset apply_preset_band`), `legacy_layout`,
`edges`, `centre_q`, `CURVES`, `N_MAX`, `F_LO F_HI Q_LO Q_HI`; `bands`:
`BANDS CEIL KNEE HEAD NOM DRIVE soft_ceil SHAPERS Params default_params
PRESETS`; `Analyser` (`feed float_frequency_data band_bins`).
**Must never.** Let the legacy layout diverge from the frozen six-band
oracle by a bit (`tests/test_analyzer.py:63-83` vs `tests/legacy_chain.py`).
Let a lane reach `CEIL` or hard-clamp the fader path
(`tests/test_core.py:58-64, 144`). Do FFT or chain work in the audio
callback (`audio.py:190-201`, unenforced). Lose the layout, per-band
params or master faders on a source attach (`tests/test_analyzer.py:412`).
Import `params`, `routing`, `ui` or `render` (unenforced; `offline.py:17`
already imports `routing`). "Fix" the trim's non-monotonicity without
re-freezing the oracle.
**Tests.** `tests/test_analyzer.py`, `tests/test_core.py:58-167`,
`tests/test_golden.py`; transport arithmetic in `tests/test_control.py:126-168`.
`audio.py`'s streams and `analysis.py` have no tests of their own.
