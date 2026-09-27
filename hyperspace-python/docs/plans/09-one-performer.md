# Plan 09 — One performer per parameter: the referee, two ops, tempo and LFOs

**After plan 08.** Every live controller — hands, audio lanes, a DAW, an
LFO — reaches a parameter through **one path**, and a parameter has **at
most one performer** at a time. Assigning a second one asks, the way FL
Studio does, whether to replace the first. Layered performances come from
**chaining** (a hand owns an LFO's depth; the LFO owns brightness), never
from two things pulling on one knob. Four tempo-aware LFOs and a tap-tempo
clock arrive on that footing.

Code: `routing.py` (the referee, the two ops, file schema 2), `params.py`
(`glide` removed), `midi.py` (`learn_source` → a route), `hands/core.py`
(`_learn` → a route), `app.py` (scene-setters read the base), new
`tempo.py` and `lfo.py`, `ui_routing.py` (the prompt, LFO sources, macro
knobs), a new LFO page, `library/bindings/*.json` rewritten,
`tests/test_routing.py`, `tests/test_lfo.py`, `tests/test_tempo.py`.

## Why

The audit of 2026-09-26 (session notes; the four simulations below are
its exit criteria) found that the registry's base + offset model is sound
but that continuous sources reach a parameter by **two different paths**
with nothing deciding between them:

- `Router.drive` — the `abs` rows hand Learn writes — rewrites the *base*
  every frame, ignores pickup, never yields.
- `Router.modulate` — `mod` / `replace` / `span` rows — adds *offsets*.

Plus MIDI `abs` with its own soft pickup, and out-of-registry relative
writers (mouse orbit, gamepad sticks, `_ride_depth`) that read the
*effective* value and write the base. Reproduced against the real code:

| # | Setup | Result |
|---|---|---|
| 1 | Mouse orbit / stick / scroll on a param a lane or hand modulates | The whole offset folds into the base **every drag frame** (asked +0.01 rad/frame, got +0.32). `hands-pinch` routes L middle → `camera.zoom`, so pinch + scroll hits it today. |
| 2 | Two `span` rows on one target | Departures from base sum: both hands at 0.2 → **0.00**; 0.9 and 0.1 → 0.50. |
| 3 | Learned hand + APC knob on one target | The knob catches for one frame, then `drive` rewrites; the knob is dead while a hand is in view. |
| 4 | Hand `abs` + hand `mod` on one target | Doubled: hand 0.5 → 1.00. `Bindings.bind` keeps mod rows on purpose. |

Nothing checks for two rows on one target anywhere (`Bindings.add`
appends). And "the source drives the param" is spelled five ways —
`abs` (throw, float), MIDI `abs` (throw, detented), `mod` (offset),
`replace` (param units; the op that capped brightness at 1×), `span`
(throw) — which is why the same gesture behaves differently depending on
whether it was Learned or routed.

MIDI as an internal bus was considered and rejected again: BLUEPRINT §1
already decided values flow as floats internally, and none of the four
faults above is about wire format. They are about **policy**.

## Decisions (settled with the user 2026-09-26 — don't re-litigate)

1. **One registry, one path.** Every continuous source (`lane`, `hand`,
   `ext`, `lfo`) reaches a parameter only through `Router.modulate`.
   `Router.drive`, `Param.glide` and the `abs` op on lane-scheme sources
   are removed. Hand Learn writes a route.
2. **One performer per parameter.** A *performer* is an enabled route row
   whose source is a continuous scheme. A target has at most one. Adding
   a second prompts: *"Brightness is already performed by R height —
   replace?"* Yes removes the old row. Gates don't exempt a row: two rows
   on one target with different pinches is still two performers.
3. **Scene-setters don't compete.** The panel, keys, pad buttons, the
   APC40 (abs / rel / notes), presets, and the mouse / stick relative
   writers set the parameter's **base** — the value the performer works
   from and the value it returns to. They never prompt and are never
   blocked. An APC knob turned on a hand-owned parameter moves the return
   value, which shows when the hand leaves.
4. **Hands grab; they never yield.** The box is a continuous performance.
   `pickup` is meaningless on a performer row and is dropped.
5. **Two ops.** `push` (was `mod`): the performer adds to the base. `position`
   (was `span`): the performer *is* the fader; the base returns when it
   stops. `replace` is deleted — its only use was `legacy6`'s rotation
   formula, which becomes push on a base of 0 (the "additive twin",
   `ROT_DEPTH`). Behavioural difference: planes stop when audio stops
   rather than returning to the reference's 1× idle spin; inside the
   relaxed parity bar.
6. **Push is centred where the source rests.** `offset = depth · scale ·
   (u − rest)`. A lane rests at 0, an LFO and a centred hand axis at 0.5.
   Without this every LFO route sits permanently offset by half its depth.
7. **Chaining, not stacking.** Layering is a property of the graph: LFO
   knobs and macro knobs are parameters, so a performer can own them.
   Eight **macro knobs** (`macro.1–8`) exist only to be a route's `scale`
   and to be owned.
8. **LFOs are performers** (they own their target exclusively) and are
   themselves ownable (depth, rate, phase).
9. **Tempo: one free-running clock, tap to set it.** Hz is the base unit;
   BPM + a division is converted to Hz. Tap sets BPM *and* the downbeat.
   No DJ Link, no MIDI clock, no sync drift correction: re-tap. 4/4 assumed.
10. **Presets are disposable.** Every factory routing preset is rewritten;
    a user file migrates on load with a note; nothing is preserved that
    the new rules can't express.
11. **After this plan: plan 10, a documentation and architecture pass.**
    Not part of 09's exit criteria, but 09's docstrings and this file are
    written to be its inputs.

## The model

```
                       scene-setters (write the BASE, never prompt)
    panel · keys · pad buttons · APC40 · presets · mouse/stick (relative, on base)
                                   │
                                   ▼
   Param ─── base ──────────────────────────────▶ effective = base + offset
                                   ▲
                                   │  ONE route row, ONE per-frame path: Router.modulate
              performer ───────────┘
    lane:<i> · hand:<i> · ext:<i> · lfo:<i>      op = push | position
                                                  depth · scale (a param, e.g. macro.3)
                                                  rest (push only) · when (a gate)

   chaining:  hand:7 ──position──▶ lfo.1.depth      lfo:1 ──push──▶ view.bright
              lane:0 ──push──▶ macro.2              hand:1 ──position──▶ fx.mix  ×scale macro.2
```

Frame order (unchanged in kind, one new step): keys / pad / MIDI →
`hands.poll` (feeds `hand`) → `audio.step` → bridge (feeds `ext`) →
**`lfo.step` (feeds `lfo`)** → `Router.modulate` → `reg.apply()` →
`integrate` → `draw`. A performer that owns an LFO's depth lands one
frame before that LFO's output does — the same one-frame lag every
modulated value has.

## Work packages

Sizes: S ≤ ½ day, M ≈ 1–2 days, L ≈ 3–4 days. WP1 first; WP2, WP3, WP4
in parallel against it; WP5 last on the merged state.

### WP1 — The referee and the two ops · L · first

`routing.py`, `params.py`, `midi.py`, `hands/core.py`, `ui_routing.py`,
`tests/test_routing.py`, `tests/test_hands.py`.

- **Ops.** `MOD_OPS = ("push", "position")`. `OPS` drops `abs` for lane
  schemes, drops `replace`. `Binding` gains `rest: float = 0.0`. `to_json`
  writes `rest` only when non-zero. `Router.modulate`: push is
  `depth · scale · (u − rest)`; position is `clamp(depth · scale · u) −
  base_norm`; `p.norm` remains the base. `describe()` says "pushes" /
  "positions".
- **Referee.** `Bindings.performers()` (enabled rows, lane scheme, op in
  MOD_OPS), `Bindings.owner(pid) -> Binding | None`. `Bindings.add` and
  `bind` raise `Owned(existing)` when the target has a different enabled
  performer; `Bindings.replace_owner(new)` removes it and adds. Enabling a
  disabled row goes through the same check. `set_routes` / `load_preset`
  keep the first row per target, drop the rest into `table.dropped`
  (list of `(row, why)`), which the ROUTING page shows until the next
  edit. Disabled rows don't own.
- **One path.** Delete `Router.drive`, `Param.glide`, `Bindings.learned`,
  and the `_learned` section of the ROUTING page. `MidiIO.learn_source`
  builds `Binding(source, pid, "position", 1.0, when=gate)` and routes it
  through `table.add`; `Owned` surfaces on the panel as the prompt (see
  WP5) — the learn is held pending until answered. `hands/core.py::_learn`
  unchanged except for what it calls.
- **File schema 2.** `SCHEMA = "hyperspace.bindings/2"`. A v1 file migrates
  on load: `mod` → `push` (rest by scheme: `lfo` and hand axes flagged
  bipolar → 0.5, else 0; the loader asks nothing — the migration table is
  fixed: `hand` rows get 0.5 for indices whose default dof is centred, 0
  otherwise); `span` → `position`; lane-scheme `abs` → `position` depth 1,
  `pickup` dropped; `replace` → dropped with a stderr line naming the
  row. Duplicate owners after migration: first wins, rest dropped, noted.
  Written back once (the `midi_map.json` precedent).
- **Tests.** The four audit simulations as tests (1 belongs to WP2 but
  lives here). Exclusivity: add on an owned target raises; replace works;
  preset with two rows keeps the first; disabling releases; enabling
  re-checks. Migration of a hand-written v1 file. Rest-centred push at
  u = rest is a no-op. `legacy6` still lands the reference's rate to
  round-off *with the source live* (the parity anchor moves: assert the
  driven value, not the idle one).

### WP2 — Scene-setters read the base · S · parallel

`app.py`, `midi.py` docstring, `ui.py`.

- `Mouse.poll`, the gamepad analog block and `_ride_depth` read `p.base`
  and write `set_value` — six lines. Audit simulation 1 is the test
  (`tests/test_app_relative.py` over a `Param` with a fake object).
- Rotation's integrator is unchanged (apply() already folds a direct
  object write into the base).
- MIDI `abs` on a performed param: unchanged mechanics, documented as
  "moves the return value". Ring feedback already shows `p.norm`
  (the base); confirm with a test that a ring doesn't chase a performer.
- Panel: a performed param's readout already shows `base → effective`;
  add the owner's name to the tooltip ("performed by R height").

### WP3 — Macro knobs · S · parallel

`params.py` (`macro` group, 8 continuous 0–1 params, persist,
modulatable, `fmt` as a percentage), a strip of eight on the ROUTING
page's left column, listed in the `scale` combo first. A test that a
macro owned by a lane scales another route's depth the next frame.

### WP4 — Tempo clock and four LFOs · L · parallel

New `tempo.py`, `lfo.py`, `ui_lfo.py`; `params.py` declares their
params; `app.py` steps them; `tests/test_tempo.py`, `tests/test_lfo.py`.

- **`tempo.Clock`.** `tap(t)`: taps more than 2 s apart start a new burst;
  the burst's first tap is the downbeat `t0`; with ≥ 2 taps BPM is
  60 / mean interval (clamped 20–300). `beat(t) = (t − t0) · bpm / 60 +
  nudge`, `bar(t) = beat mod 4`, `phase(t, ratio) = (beat · ratio) mod 1`.
  Params: `tempo.bpm` (continuous, persist), `tempo.tap` (trigger),
  `tempo.nudge` (−0.5…0.5 beats, persist), and **`lfo.trigger`** (trigger).
  - **The global LFO trigger** is the one button the performer presses
    after tapping a tempo (or any time): it sets the downbeat to *now*
    (`t0 = now`, nudge untouched) and every LFO in a division mode
    restarts at phase 0 (+ its own `phase`) in that instant, together.
    Free-running Hz LFOs are untouched. Tapping alone never moves a
    running LFO's phase — only the trigger does, so a re-tap mid-set
    doesn't jolt the picture until the performer says so.
  - Keys: `B` tap, `⇧B` trigger (add to `keymap()` and `ui.CHEATSHEET`).
  - APC40 (`DEFAULT_MAP` in `apc40.py`): the physical TAP TEMPO (`N_TAP`)
    → `tempo.tap`; NUDGE +/− (`N_NUDGE_P/M`) → `tempo.nudge` step ±; the
    METRONOME button (0x41, free today) → `lfo.trigger`, with LED feedback
    that blinks on the beat (`led`, driven from `clock.beat`). Those three
    notes currently fire `theme.next` and step `view.shape`; `theme.next`
    moves to a free button (QUANT 0x3F) and the shape steps go — the clip
    grid already sets shapes. Existing user files keep their rows.
- **`lfo.LFOs`.** Four. Per LFO the params `lfo.N.shape` (sine, tri, saw,
  square, random — random is sample-and-hold once per cycle), `lfo.N.rate`
  (Hz, log 0.01–20), `lfo.N.sync` (enum: Hz, 4 bars, 2 bars, 1 bar, 1/2,
  1/4, 1/8, 1/16), `lfo.N.depth` (0–1), `lfo.N.phase` (0–1), `lfo.N.reset`
  (trigger: this one LFO's phase to 0 now, in either mode — a per-LFO
  gesture hook; the global `lfo.trigger` is the performer's button). In
  Hz the phase integrates `rate · dt`; in a division it is
  `clock.phase(t, ratio) + lfo.phase`, so bar-length waves land on the
  downbeat and the global trigger re-aligns all of them at once. Output
  `u = 0.5 + 0.5 · depth · wave`, `wave ∈ [−1, 1]`; rest 0.5. Every
  param modulatable and persistent — that is what makes them chainable.
- **Feed.** `lfos.step(dt, clock)` then `router.feed("lfo", [u1..u4])`,
  `router.labels["lfo"] = ["LFO 1", …]`, `router.rests["lfo"] = [0.5]*4`
  (a new `Router.rests` the ROUTING page uses to default a push row's
  `rest`; hands publish theirs the same way).
- **Page.** `LFO` page key (`ui.PAGE_KEYS`): the clock strip (BPM
  readout, a beat light, tap / **trigger** / nudge) and four LFO strips, each
  with a small scope of the last two cycles, the live output as a
  hairline, and its six controls. The strips' faders are ordinary
  registry widgets so Learn and ownership work on them.
- **Tests.** Tap burst math (3 taps at 140 → 140.0; a gap restarts);
  division phase lands 0 on the downbeat; a tap after the trigger does
  not move a running synced LFO, the trigger does — all synced LFOs read
  phase 0 that frame, Hz ones don't; shapes' extremes; random holds
  within a cycle; per-LFO reset; an LFO owning another LFO's depth changes the
  second's output next frame (chain, no recursion); output rests at 0.5
  at depth 0.

### WP5 — Presets, the page, the user's file, docs · M · after WP1–4

- **Factory presets** rewritten (`python -m hyperspace.routing`):
  `default` (the table), `legacy6` (push on `values` of 0 for
  `rot.rate.*` and `pattern.mod.*`, depth `ROT_DEPTH` × `master.gain`),
  `hands-play`, `hands-pinch`, `hands-fx` (position / push, one owner per
  target — `hands-fx`'s "L height adds to brightness" stays a push),
  new `lfo-breathe` (LFO 1 at 1 bar pushes brightness; R height positions
  LFO 1 depth; LFO 2 at 1/4 pushes `fx.mix` × macro 1). `test_routing`
  guards them against drift and against two owners.
- **ROUTING page.** Op chip cycles push ↔ position; a `rest` field on
  push rows (defaulted from `Router.rests`); the owner prompt as an imgui
  modal (target label, current owner's `describe()`, *Replace* / *Keep*);
  the `dropped` notice; sources list LFO 1–4; targets include `lfo.*` and
  `macro.*`; `learned` section gone.
- **The user's `bindings.json`** is migrated by the loader (WP1); this
  package checks the result on the machine and removes stale rows by
  hand if the migration note lists any.
- **Docs.** `routing.py` docstring rewritten around the model diagram
  above; plan 08's "Learn" paragraphs and its shape diagram updated
  (Learn → a position route; `drive` gone); `ui.CHEATSHEET` (B);
  `CHECKPOINT.md`; `docs/plans/README.md` row.

## Contracts between packages

- WP2–4 build against WP1's names: `MOD_OPS = ("push", "position")`,
  `Binding.rest`, `Bindings.owner`, `Owned`, `Router.rests`. WP1 lands
  these first, even as stubs, before the others branch.
- Nothing in `lfo.py` / `tempo.py` imports from `routing.py` or `ui*.py`;
  they take a registry and a clock, and `app.py` wires them, the same
  boundary rule `hands/` has (`tests/test_hands_boundary.py` pattern).
- `Router.feed` is the only way a source reaches the table. No adapter
  calls `Param.set*` on a performer's behalf.

## Exit criteria (checked on merged `main`)

1. The four audit simulations are tests and pass: relative writers hold
   under modulation; two position rows on one target is impossible;
   a knob and a hand cannot share a target; a hand cannot own a target
   twice.
2. `grep -n "def drive\|def glide\|\"replace\"\|def learned" hyperspace/`
   is empty.
3. Right-click → Learn on a parameter a preset already performs shows the
   prompt; *Replace* swaps the owner and writes the file; *Keep* leaves
   the table untouched.
4. Loading `hands-pinch`, pinching L middle and scrolling: zoom does not
   drift, and lands back on the scroll-set value when the pinch opens.
5. Tap the APC40's TAP TEMPO four times at ~140 on an electronic track,
   press METRONOME on the "one": `tempo.bpm` reads within ±1 and
   `lfo-breathe`'s brightness swells on the bar from that press. Tapping
   again without pressing METRONOME changes the readout, not the swell.
6. With `lfo-breathe` loaded, raising the right hand deepens the swell;
   nothing else moves.
7. An APC knob turned on a hand-owned parameter moves the readout's base
   and takes effect when the hand leaves the box.
8. A v1 `bindings.json` from before this plan loads, migrates, is written
   back once, and the migration note lists every dropped row.
9. `pytest` green; `ruff` clean; every factory preset has one owner per target.

## What comes after: plan 10

A full system audit and architecture pass, for the maintainers and for
the agents that work here: a component map, the frame-order data flow,
the control model above as the canonical statement, per-module "shape"
sections, a decisions log gathered from plans 07–09, and a refreshed
ENGINEERING.md — with diagrams. Its purpose is to keep one-shot fixes
possible as the system grows. It starts when this plan's exit criteria
pass, not before.
