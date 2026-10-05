# Plan 17 — Learn, Unbind and seeing the desk

**Written 2026-10-04 against `plan-15-integration` at 2c3b282** (`finish-line`
plus plan 15's code). Scope: roadmap §4 "Plan 17"
([`15-21-roadmap.md`](15-21-roadmap.md)). Plan 16 lands on `finish-line`
before this is built; of this plan's files it touches only `ui.py`'s
`Panel.__init__` (the cheat sheet off at launch). Plan 18 runs beside this
plan; the seam between them is in §2.

Mapping was where the Oct 3–4 session lost the most time: a hand learn
went to the wrong hand, "Unbind" was two items that each removed half,
and nobody could see from a step back what the desk did. This plan makes
a learn listen to one source, makes Unbind one item, lets the on-screen
desk grow until its controls carry their params' names, and makes it
clickable.

Every claim about existing code below was read in the file named.
Numbers marked *measured* come from headless probes on this branch (a
temp home, the rig of `tests/test_ui_shell.py` and `tests/test_hands.py`).

## 1. What the owner hit, and what it is

| # | The owner hit, or the roadmap says | What the code does | So |
|---|---|---|---|
| 1 | "The Leap assigned a learn to the wrong hand" | `HandsIO._learn` (`hands/core.py`, not `hands/panel.py`) takes a baseline of every axis's output when a param is armed, then each frame takes the axis that has travelled furthest since, **over all twelve axes of both hands**, and completes the learn when that travel reaches `LEARN_MOVE` (0.25). An axis whose hand arrives later gets its baseline on its first live frame. Nothing says which hand was meant. *Measured:* left hand rolling slowly on purpose while the right hand travels in from the edge → `hand:right.x` in 8 frames; both hands in the box, left rolls 29° while right drops 150 mm → `hand:right.y`. A still hand entering the box does not complete a learn. The hand that armed the learn with the mouse is the one that comes back over the box. | WP2: the menu says which hand; `_learn` considers only that hand's axes. |
| 2 | "A knob bump during a hand learn is ignored" | It is not. `MidiIO._handle` (`midi.py`): while `learner.learning` is set, **every** CC and note-on goes to `_learned` and every message returns without being dispatched. A preset-layer knob takes the param (and its own old row is dropped, `Bindings.bind`); a fader, SHIFT, TAP or a preset pad ends the learn with a refusal (`_learned` calls `lrn.take()` before it refuses) and does not do its own job. MIDI is polled before the hands (`app.frame`), so the desk wins a tie. | WP2: a learn has a `want`; a desk message completes only a desk learn. Fork 6 settles what a control that cannot be learned does meanwhile. |
| 3 | A hand twitch during a knob learn | `HandsIO.poll` calls `_learn` whenever `learn.learning` is set, whatever armed it: the first axis to travel 0.25 lands a `position` route at depth 1 (`Learn.learn_source`), or raises the Replace / Keep prompt if the param has a performer. | WP2: the hands complete only a hand learn. |
| 4 | One menu, "shown whether or not a MIDI port is open" | `Panel._ctx` (`ui.py`) reads the desk row through the **adapter object**: `b = m.binding_for(a.id) if m is not None else None`, and "Unbind" calls `m.unbind`. With `[midi] enabled = false` (or the adapter failing to build, `app._open_midi`) `panel.midi` is `None`: the row's line and "Unbind" are missing although the row is in the shared table and the diagram shows it. With the adapter built and no device, `MidiIO` exists and both show. "Learn" shows in every case; armed with nothing to complete it the hint reads "nothing to learn from (no MIDI, no hands)". | WP1 reads and edits the table, never the adapter. |
| 5 | "One Unbind … removes whatever performs the param (desk row, hand rows)" | Two items. **"Unbind"** → `MidiIO.unbind` → `Bindings.unbind`: every preset-layer MIDI row whose target is the drawn id. It is offered when `for_param` finds *any* MIDI row, so on a param only the session maps (a fader's `band.0.post`, the crossfader's `output.dim`) it is shown and then refuses; the refusal is `learner.last`, drawn only on ROUTING's head and the SYSTEM page. **"Unbind hand"** → `hands.panel.ctx_rows`: every `hand:` row on the real param, enabled or not. Neither removes a lane, LFO or `ext` route, which is the param's performer just as often ("performed by LFO 1" is printed in the same menu). In the control model a desk row is a scene-setter, not a performer (ARCHITECTURE §3.2). | WP1: one item over "what is bound here": the preset's desk rows and the routes. Fork 4. |
| 6 | The menu's wording | `Learn`, then for a mapped param `Unbind`, the hand rows as text, `Gate: … ▸`, `Unbind hand`, `Route a lane here…` (`_ctx`, `ctx_rows`, `ui_routing.ctx_item`). The desk row's line is `Binding.describe()` ("MIDI CC 48 ch1"), not the glyph the diagram and ROUTING print. | WP1 prints the glyph. |
| 7 | "Learn where it is missing: the controls the sweep lists" | No list exists in the repo. *Measured:* every param widget is drawn through a `Panel` helper (`_fader`, `_slider`, `_combo`, `_check`, `_button`, `_lit_button`, `_path`; `_row` and `half` end in `_slider`) or calls `_ctx` itself (`ui_bands._norm_chip`, the nudge chips in `ui_lfo._clock_strip`, the bank in `ui_presets.preset_bank`, the rail's pills), so every drawn param has the menu. What lacks it: a row's **label** (`Panel._label_cell` is a dummy; the fader's label line), the analyzer's **meters 2–N** (`Panel._meters` attaches `band.select`'s menu to meter 0 only), and controls that stand for no param (the band ◀ ▶, "Load bitmap", "Load track", the HANDS page's axis rows and its mirror / solo / calibrate buttons, the ROUTING page's rows, the desk diagram). And the reverse: the menu offers Learn where it means nothing — on a file path (`_path`), and a hand learn on a param that is not modulatable lands a row `Router.modulate` skips. | WP3: the label and every meter open the menu; Learn is offered only where it can act. §2 WP3 lists what is left alone and why. |
| 8 | A learn that sits armed | An armed learn never times out and is shown only by the red frame on its widget and by a line on ROUTING and SYSTEM (`_learn_frame`, `ui_routing._learn_line`, `Panel._learn_status`). On any other page nothing says a learn is armed or what the last one did. | WP2: the footer's message slot (plan 15) carries it. |
| 9 | "A DESK view … its own page, or the existing one enlarged" | *Measured* at `app.CONTROL_SIZE` (960 × 900): a page's content is 392 px wide (`ui.PANEL_W` 540 less the rail); the diagram today is 380 × 290 (`ui_desk.SIZE`), bottom-left, and 380 × 244 with the cheat sheet on (the sheet is 620 px tall). The layout is 13.7 × 14.5 units, 137 controls (`apc40.LAYOUT`). A param's label needs about 60 px a unit ("Brightness" is 59 px at 13.5 px type): 820 px across. A page cannot be bigger than the diagram already is. | Fork 1: the diagram takes the room it has; with the panel hidden it is the whole window. |
| 10 | "Every mapped control labelled with its param" | The diagram draws only the glyph, at 10 px (`ui_desk._draw`); the param is in the hover (`ui_desk.label`). With TRIP loaded 112 of 137 controls are lit on the preset layer, 86 on the global one (*measured*). `Param.label` is distinct and readable for every factory desk target ("Kaleidoscope segments", "Grid amp", "4D depth"); a `set` row on an enum has a better name still (the bank row reads TUMBLE … NOITA, the shape rows the shapes' names). | WP4. |
| 11 | "Click a control: the ROUTING page scrolls to its row" | The page's rows are in one child, `##routes` (`ui_routing.page`): routes, desk, macros, session. A preset-layer row is in the desk section, an invariant or global one in the session section, a dark preset control has an "unmapped — dark" line, and a control dark on the global layer has no line anywhere. The diagram is hit-tested, with no widgets of its own (`tests/test_ui_desk.py::test_the_diagram_draws_on_both_layers_and_hides` holds that). | WP4: the scroll happens inside the child; the cases with no row say so. |
| 12 | "Click a control, then a param: mapped" | The one road onto the desk is `MidiIO._learned`: it needs the adapter (its profile for the op and the feedback, `_dark` for the LEDs). With no adapter the app has no way to add a desk row (ROUTING can re-aim or delete one); ROUTING's desk section says "new rows: right-click a control → Learn, move a knob". | WP2 moves the row-making into `Learn`; WP4's click calls it. One mapping path. |
| 13 | Cancelling | Esc quits the app (`app.frame`, `LOOP_KEYS`). | No key cancels a pick; a click does. |
| 14 | "A ROUTING filter by glyph, param or source" | `_state(panel)["filter"]` exists already: it is the find field inside `_param_combo`. Routes have no glyph; desk and session lines have one. | WP5 keeps its own state key and matches what each line prints. |
| 15 | The roadmap: plan 18 owns "`_place`'s op and depth" | The op and the depth are a literal in `Learn.learn_source` (`Binding(source, p.id, "position", 1.0, when=when)`); `_place` only clears the axis's other `position` rows and calls `replace_owner`. And the code that picks the axis is in `hands/core.py`, plan 18's package. | §2 names the seam function by function. |

## 2. Work packages

Merge order onto `plan-17-integration`: **WP1, WP2, WP3, WP5, WP4, WP6.**
WP1–WP3 stack (each edits `Panel._ctx`). WP5 touches only `ui_routing.py`
and its test; it is built beside WP1 and merges before WP4, which calls
into it. One PR and one merge commit each (decision 30), each with a demo
in the PR body.

| WP | What | Size | Needs |
|---|---|---|---|
| 1 | **One Unbind** | S | — |
| 2 | **Learn that cannot pick the wrong source** | M | WP1 |
| 3 | **Learn where it is missing** | S | WP2 |
| 5 | **A ROUTING filter** | S | — |
| 4 | **The desk, big and clickable** | M | WP2, WP5 |
| 6 | **Docs and hand checks** | S | last |

**Shared files, and who edits what.** A package may edit only its lines.

| File | WP1 | WP2 | WP3 | WP5 | WP4 |
|---|---|---|---|---|---|
| `learn.py` | `Learn.unbind` (new) | `want`, `arm(pid, want)`, `accepts`, `learn_control` (new), `_row` (new, extracted), the guard at the top of `learn_source`, the docstring | — | — | `control`, `pick`, `map_picked` (new) |
| `midi.py` | `MidiIO.unbind` becomes a call to `Learn.unbind` | the learning branch of `_handle`; `_learned` becomes a call to `Learn.learn_control` | — | — | — |
| `hands/core.py` | — | in `HandsIO._learn`: the guard, the baseline's key and the `moved` list. Nothing else in the file | — | — | — |
| `hands/panel.py` | `ctx_rows` (the "Unbind hand" item goes; the lines and the gate stay) | — | — | — | — |
| `ui.py` | `_ctx`: the lines and the Unbind item | `_ctx`: the Learn items; `_learn_hint`; `_message` and `_footer` (the learn's line); `_learn_status`; one `CHEATSHEET` row | `_label_cell`, `_row`, `_fader` (the label opens the menu); `_meters`; `_ctx`'s rule for what is offered | — | `_draw` (the panel's rect; the pick wrap); `_ctx` (the pick click); the `ui.desk` tip |
| `ui_routing.py` | — | `_learn_line`; the hint in `desk()` | — | `_state`, `page`, the filtering in `desk`, `macros`, `session` | `goto`, the mark on a line in `desk` and `session`, the scroll in `page` |
| `ui_desk.py` | — | — | — | — | all of it |
| `tests/` | `test_midi.py`, `test_ui_shell.py` | `test_learn.py`, `test_midi.py`, `test_hands.py`, `test_ui_shell.py` | `test_ui_shell.py` | `test_ui_routing.py` | `test_ui_desk.py`, `test_ui_routing.py`, `test_ui_shell.py`, `test_learn.py` |

No code package edits `ARCHITECTURE.md`, `ENGINEERING.md`, `DECISIONS.md`,
`DECISION-REGISTER.md`, `plans/README.md`, `CHECKPOINT.md`,
`11-hand-checks.md` or this file. Each PR body carries its "as built"
paragraph; WP6 folds them in.

**No package touches:** `routing.py` (the table's calls are enough:
`bind`, `unbind`, `remove`, `routes_to`, `desk`, `is_invariant`,
`replace_owner`, `redraw_serial`), `apc40.py`, `app.py`, `params.py`,
`undo.py`, `preset.py`, `library.py`, `render.py`, `hands/signal.py`,
`lfo.py`, `tempo.py`. No boundary test moves: `learn.py` still imports
only `undo`, `params` and `routing` (the desk's profile arrives as an
argument); `hands/core.py` still imports nothing from the package (it
asks the learn object, duck-typed).

### The seam with plan 18

Plan 18 owns what a learned hand row looks like, and `hands/`. Its
learn-default package starts only after **WP2 is on
`plan-17-integration`**. The seam, function by function:

| Function | Plan 17 | Plan 18 |
|---|---|---|
| `Learn._row(self, source, p, when) -> Binding` (`learn.py`) | WP2 creates it as a verbatim extraction: `return Binding(source, p.id, "position", 1.0, when=when)`. Never edits it again. | Owns its body: the op and the depth of a learned row. May add keywords (`centred=`) that `learn_source` passes through. |
| `Learn._place(self, b)` | Not touched by any WP. | Owns it (its `x.op == "position"` filter, if a learn can land as `push`). |
| `Learn.learn_source(self, source, when=None)` | WP2 edits only above `p = self.target_for(pid)`: the `accepts` guard, and replaces the literal with `b = self._row(source, p, when)`. | Owns everything from `b = …` down: the same-axis test (`cur.op == "position"`), and its own signature if it adds a keyword. |
| `HandsIO._learn(self, learn)` (`hands/core.py`) | WP2 edits only the guard, the baseline's key and the `moved` list (which axes may win). | Owns the two `learn.learn_source(…)` calls at the bottom, `LEARN_MOVE`, `held_gate`, and every other line of `hands/core.py`. |
| `hands/panel.py` | WP1 edits `ctx_rows`; `_gate_menu` stays as it is. | Everything else (`page`, `_box`, the editor). |
| `learn.py`'s arming and listening (`arm`, `take`, `accepts`, `want`, `control`, `pick`, `learn_control`, `map_picked`, `unbind`) | Owned. | Not touched. |

Plan 18's knob smoothing is in `midi.py`'s `_apply`; plan 17's lines in
`midi.py` are `unbind`, `_learned` and the learning branch of `_handle`.

### WP1 — One Unbind

**What.** One menu item removes what is bound to the param. It is there
with or without a MIDI adapter, it is never offered when it could only
refuse, and it is one undo step.

**Owns.** Its lines in the table above. **Must not touch** `routing.py`,
`hands/core.py`, `Learn`'s arming.

**Contract.**

```python
# learn.py
def unbind(self, ids, *, desk: bool = True, routes: bool = True, name=None) -> list[Binding]:
    """Remove what is bound to a param, in the loaded preset: its
    preset-layer desk rows (`desk`) and its routes (`routes`). `ids` is
    the drawn param's id and the real one's (an alias and its band; one
    id when they are the same). Returns the rows removed."""
```

- Desk rows: every row with `b.is_midi and b.layer == "preset" and
  b.target in ids`, removed through `Bindings.unbind(pid)` for each id
  (it bumps `redraw_serial`, so an adapter redraws and the control goes
  dark, D8).
- Routes: every row of `table.routes_to(real_id)`, any scheme (hand,
  lane, LFO, ext), enabled or not, removed through `Bindings.remove`
  (a route's depth subscribers go with it, as on ROUTING's ×).
- `undo.push(f"unbind {real_id}")` first, once, and only when there is
  something to remove.
- `said("unbound view.bright from K1 (track knob 1) and R height")`;
  `name(b)` gives each row's words (the menu passes the glyph namer for
  desk rows and `Router.describe` for routes); without `name`,
  `Binding.describe()`.
- A session row (invariant or global layer) is never removed (D5, D6).
  With nothing removable and a session row on the param: `refuse("S3
  (track fader 3) → band.2.post is invariant (the session's, edited in
  bindings.json) — not unbound")`, today's words.
- `MidiIO.unbind(pid)` becomes `return self.learner.unbind((pid,),
  routes=False)`: its two tests keep passing.

*As built:* the delegate also passes `name=self.control_name`, so its
message names the control by glyph. The routes are taken on both ids,
never a MIDI row among them, and `Learn.bound(ids)` /
`learn.bound(table, ids)` answer "what is bound here" for `unbind` and
for the menu alike (§7, WP1).

**The menu** (`Panel._ctx`, with `ctx_rows`). Above the items, one line
per thing bound, read from `self.router.table` (`ui_routing.router_of`),
never from `self.midi`:

```
view.bright
modulated: 1.20× → 1.55×          only while modulated
K1 (track knob 1)                  each preset-layer desk row: glyph, Akai's name
B16 (▲) · step +3
R height positions                 each route (Router.describe), "(off)" if disabled
SM (MASTER fader) · invariant      a session row: dim, never an item
```

Then the items. **Unbind** is drawn only when `Learn.unbind` would remove
something:

- one kind bound (desk rows only, or routes only): a plain item,
  `Unbind`;
- both kinds: a submenu, `Unbind ▸` with `desk — K1`, `route — R
  height`, `both`.

*As built:* the submenu's label is `Unbind` (imgui draws the arrow) and
its items read `desk — K2`, `route — R height, LFO 1`, `both`; a
global-layer row's line reads "· global layer"; `ctx_rows` takes
`lines=` and `gate=` and the menu calls it twice.

"Unbind hand" is gone. `ctx_rows` keeps printing the hand rows' lines
and the `Gate: … ▸` submenu (a gate is not an unbind). The "performed
by …" line `_ctx` prints today is dropped: the route's own line says it.

**Undo.** One push, in `Learn.unbind`. The push in `ctx_rows` goes with
the item; the push in `MidiIO.unbind` goes with its body.

### WP2 — Learn that cannot pick the wrong source

**What.** The menu's one "Learn" becomes **Learn desk** and **Learn hand
▸ left / right**. A learn knows what it waits for; nothing else can
complete it.

**Owns.** Its lines in the table above. **Must not touch** `Learn._place`,
the body of `Learn._row` after creating it, `learn_source` below the
`_row` call, the `learn_source` calls in `HandsIO._learn`, anything else
in `hands/`.

**Contract.**

```python
# learn.py
WANTS = ("desk", "hand:left", "hand:right")

class Learn:
    want: str | None          # what may complete `learning`; None: anything (a bare arm(pid))

    def arm(self, pid: str | None, want: str | None = None) -> None: ...
    def accepts(self, source: str) -> bool:
        """May this source complete the armed learn? False when nothing
        is armed. want None: any source. "desk": a cc / note / pitch
        source. "hand:left": a source that starts "hand:left." (an axis
        or a switch of that hand, by name)."""
    def learn_control(self, source: str, profile=None) -> bool:
        """A desk control completes the armed learn: a preset-layer row
        into the loaded preset. True when it landed."""
    def _row(self, source: str, p: Param, when: str | None) -> Binding: ...   # plan 18's
```

*As built:* `arm` raises on a want outside `WANTS`, clears `refused`
and counts the arms (`armed_n`); `take()` clears `want` too; `said_n`
counts what was said. `_row` has since gained `centred=` and `depth=`
and a rule table: it is plan 18's (register row 52).

`arm(None)` clears `want`. New fields are read with `getattr(…, None)`
wherever an object from before a hot reload may be met (`Learn.same_source`
already does this for `lane`).

**`learn_control`** is today's `MidiIO._learned`, moved, so a click can
complete a learn with no adapter (WP4). In order:

1. `pid = self.learning`; no param by that id → `False`.
   *As built:* before this it asks `accepts(source)` (a click must not
   complete a hand learn), and an id the registry lacks **clears** the
   learn: left armed it would swallow every desk message.
2. `b = Binding(source, pid, "abs", layer="preset")`. The control is
   invariant (`table.is_invariant(b)`) → `refuse("S3 (track fader 3) is
   invariant (the session's) — not learned")`, `False`. The global layer
   is up → `refuse("K1 (track knob 1) is on the global layer (the
   session's) — latch SHIFT off to learn into the preset")`, `False`.
   **The learn stays armed** after a refusal (fork 6).
3. The op and the feedback as today: a CC the profile calls relative →
   `rel`; a CC onto a trigger, or any note → `toggle`;
   `profile.feedback_for(kind, channel, number)` sets `feedback`, `ring`,
   `on`, `off`. `profile` is duck-typed (`is_relative`, `feedback_for`,
   `named`); `None` gives a plain `abs` row named by `Binding.describe`.
4. `self.take()`; `undo.push(f"learn {pid}")`; `gone = table.bind(b,
   write=False)`; `table.redraw_serial += 1` (the adapter, if there is
   one, redraws: the replaced rows' controls go dark and the new row's
   ring is sent).
5. `said("learned view.bright ← D3 (device knob 3) (into the preset)")`,
   and when `gone` holds rows of another control: "…; K1 let go".

`MidiIO._learned(kind, channel, number, value)` becomes
`self.learner.learn_control(Binding.midi_source(kind, channel, number),
self.profile)`.

**`MidiIO._handle`**, the learning branch. For a CC, or a note-on with
velocity > 0, while `learner.learning` is set and
`learner.accepts(source)`:

- the control is invariant → it is not a candidate: the message is
  dispatched as if no learn were armed (SHIFT latches, a fader moves its
  param, TAP taps), and the learn stays armed;
- otherwise → `_learned`, and the message is not dispatched (as today),
  whether it landed or was refused for the global layer.

When the learn does not accept a desk source (a hand learn), every
message is dispatched as usual: the knob does its job and the learn is
untouched. A note-off is never a candidate; it is dispatched as it is
today when no learn is armed (to the rows its note-on went to, `_held`).

**`HandsIO._learn`** (three edits, at the top of the function):

```python
ok = getattr(learn, "accepts", None)
pid = getattr(learn, "learning", None)
if pid is None or (ok is not None and not any(ok(self.address(i)) for i in range(len(self.state)))):
    self._learn_base = None
    return
key = (pid, getattr(learn, "want", None))        # a re-arm starts a fresh baseline
if key != self._learn_key: self._learn_base, self._learn_key = None, key
...
moved = [abs(y - b) if y is not None and b is not None and (ok is None or ok(self.address(i)))
         else 0.0 for i, (y, b) in enumerate(zip(ys, self._learn_base))]
```

*As built:* the key is `(pid, want, armed_n)`, so a cancel and re-arm
of the same param and want also starts fresh.

So under "Learn hand ▸ left" only the left hand's axes can win, and
under "Learn desk" no axis can. `_learn_key` is read with `getattr`
(an adapter from before a hot reload). The pinch that becomes the gate
is still `held_gate(side)`: the learning hand's thumb first, then the
other hand's (plan 08; not changed here, see fork 10).

**The menu** (`Panel._ctx`), after WP1's lines:

- Not armed on this param:
  - `Learn desk` → `lrn.arm(a.id, "desk")`. Offered unless the param is
    `Kind.TEXT` or `desk.shift` (what `ui_routing._desk_targets` leaves
    out). Offered with no MIDI adapter and no device: a click on the
    diagram completes it (WP4).
  - `Learn hand ▸` with `left`, `right` → `lrn.arm(a.id, "hand:left")`.
    Offered only when `self.hands is not None` and the real param is
    modulatable; the sides are the ones the rig's axes have.
- Armed on this param: the hint in red and `Cancel learn`, as today.
- `self.learn is None`: the dim line "no learn", as today.

`_learn_hint()` reads the want: "turn a knob or press a button on the
desk, or click one on the diagram…", "move the left hand…", "move the
right hand…"; with `want` `None`, today's words.

*As built:* the click's words are said only when `ui_desk.click` exists
(it does since WP4). With no MIDI adapter the desk hint reads "click a
control on the desk diagram…".

**The footer** (`Panel._message`, `_footer`). While a learn is armed the
message slot reads, in red, `learning view.bright — move the left hand…
(click to cancel)`; a click on it calls `lrn.arm(None)`. When
`lrn.last` changes it is shown for `MESSAGE_S` like the undo's line, in
the warning colour when `lrn.refused`: a refusal is then seen on every
page. `_message` gains the key `"learn"` beside `"status"`, `"warning"`
and `"undo"`.

*As built:* "(click to cancel)" is on the line only where it fits, and
on the hover otherwise. A line just said (a refusal that left the learn
armed, a warning, an undo) shows first for `MESSAGE_S`; then the armed
line returns.

**Elsewhere.** `ui_routing._learn_line` and `Panel._learn_status` print
the same hint. `ui_routing.desk()`'s faint line becomes "new rows:
right-click a param → Learn desk, or click a control". The cheat sheet's
row becomes `("right-click", "a control: learn desk / hand · unbind")`.

*As built:* ROUTING's line takes the longest wording that fits ("new:
Learn desk, or click a control" at the control size), the whole on
hover. A refusal that left the learn armed shows on ROUTING and SYSTEM
as the reason and "— still learning `<id>`".

**Undo.** `Learn.learn_control` pushes (the push `_learned` has today,
moved). The hand's pushes in `learn_source` and `_place` are untouched.

### WP3 — Learn where it is missing

**What.** The menu opens from the places a hand lands when it means
"this control", and offers Learn only where a learn can act.

**Owns.** Its lines in the table above. **Must not touch** `learn.py`,
`midi.py`, `hands/`.

| Where | Today | Change | Why |
|---|---|---|---|
| A row's label (`_label_cell`, as `_row` and `half` draw it) | A dummy: right-click does nothing | `_row` calls `imgui.open_popup_on_item_click(f"##ctx.{pid}", right)` on the label's dummy; the slider's `_ctx` draws the popup as today (the two calls share one id scope) | The label is where the name is; it is a quarter of the row's width |
| A fader's label line (`_fader`) | No menu | The same call on the label, inside the fader's `push_id` | The same |
| Meters 2–N (`_meters`) | Meter 0 only | `self._ctx(self.reg["band.select"], f".{i}")` for each (the `key` the rail's pills use) | Every meter but the first did nothing on right-click |
| A file path (`_path`) | Learn offered (a `Kind.TEXT` param is never modulatable, so `ctx_item` already prints "not modulatable") | No Learn items (WP2's rule: not `Kind.TEXT`) | A knob cannot set a path |
| A param that is not modulatable (every `hands.*`, the rig's settings) | A hand Learn lands a route the router skips | No "Learn hand ▸" (WP2's rule); "Learn desk" stays | A knob on `hands.smooth` is a real use; a hand on it is a dead row |

*As built:* the label's hook is `Panel._ctx_label` (with `_ctx_id`),
called by `_row` and `_fader`; the rule for "Learn desk" is
`ui_routing.desk_target`; a learn armed from a meter frames the meters;
meter 0's menu id is now `##ctx.band.select.0`.

**Left alone, and why.**

- The band ◀ ▶, "Load bitmap", "Load track", mirror / solo / calibrate:
  they stand for no param.
- A label a page draws on its own before a combo (`_label_cell("scene")`,
  `("path")`): the call does not know the param. The combo beside it has
  the menu.
- The HANDS page's axis rows: an axis is a source, not a target. A
  source-first hand learn ("this axis, then click a param") is fork 11,
  not built.
- ROUTING's route rows: a route's depth is not a param; a macro's depth
  subscriber is how one is performed.
- ROUTING's desk lines and the diagram's controls: WP4 gives them the
  click.
- Params with no widget (`preset.next`, `preset.prev`, `preset.home`,
  `preset.select`, `preset.save.k`, `edit.undo`, `edit.redo`,
  `ui.panel`): each already has its key or its invariant control, and
  bank switching may not sit on a preset's layer (D6). A desk row's
  target combo on ROUTING reaches any of them.

**Undo.** Nothing new: no action is added.

### WP5 — A ROUTING filter

**What.** One text field on the ROUTING page's counts line. Typing in it
hides every line that does not match.

**Owns.** Its lines of `ui_routing.py`; `tests/test_ui_routing.py`.

**Behaviour.**

- The field sits on the line that reads "6 routes · 6 lanes · live",
  left of `+ route`: `imgui.input_text_with_hint("##rows", "filter", …)`,
  about 120 px. No line is added to the page.
- State: `_state(panel)["find"]` (`"filter"` is the param combo's). It is
  UI state: not a param, not saved, not in a preset, not an undo step,
  gone at restart.
- Matching: lower-case; the text is split on spaces and **every** word
  must be a substring of the line's haystack:
  - a route: `Router.describe(b)` (the source in its adapter's words),
    `b.source`, `b.target`, the target's label;
  - a desk line, a dark line, a session line: the glyph, Akai's name
    (`control_name`), `b.source`, and for a mapped line `b.target` and
    its label;
  - a macro: its id, its label, and each subscriber's param or route; a
    macro that matches is drawn whole.
  ```python
  def matches(panel, router, text: str, *hay: str) -> bool   # pure, tested
  ```
- A route keeps the index it has in the unfiltered list (`_row(…, k)`
  pushes it as its imgui id), so a filtered page has no id clashes and a
  × removes the row it is on.
- While the field is not empty the counts read "3 of 41 rows" in red and
  a `×` chip beside the field clears it. It is also cleared by emptying
  it and by a click on a desk control (WP4's `goto`, so the row it
  scrolls to is never hidden). A preset load does not clear it (fork 9).
- Section titles are always drawn; a section with no matching line says
  "no row matches".

*As built:* "n of m rows" counts every line of the page (176 over
TRIP), not the routes; a line a widget is in use on stays drawn until
it is let go; a dark line matches on its glyph, name and source only; a
filter of spaces alone is no filter; the unfiltered counts shorten to
fit beside the field (§7, WP5).

**Undo.** None.

### WP4 — The desk, big and clickable

**What.** The desk window takes the room it has. Past a size, every lit
control carries its param's name. A click picks a control; ROUTING
scrolls to its row; a click on a param then maps it.

**Owns.** `ui_desk.py`; its lines in the table above; `tests/test_ui_desk.py`.
**Must not touch** `apc40.py` (the layout is right; hand check 45),
`routing.py`, `midi.py`, `hands/`.

#### Where it lives (fork 1)

There is no DESK page. The one desk window (`ui_desk.diagram`) is laid
out each frame in the room left of the panel:

```python
# ui_desk.py
MIN_W, LABEL_UNIT = 300.0, 44.0     # px; a unit this wide or wider carries labels

def room(display: tuple[float, float], panel_x: float | None, sheet: tuple[float, float] | None
         ) -> tuple[float, float, float, float]:
    """(x, y, w, h) of the desk window. `panel_x`: the panel's left edge,
    None while it is hidden. `sheet`: the cheat sheet's (w, h), None
    while it is off."""
```

- left 12, bottom `display_h − 12`, as today;
- right edge: `panel_x − 12` with the panel open, `display_w − 12` with
  it hidden; `w` never under `MIN_W`;
- the cheat sheet, when on: with the panel open the desk sits above it
  (today's rule); with the panel hidden the desk sits beside it (its
  left edge at `12 + sheet_w + GAP`), full height;
- height: all there is, capped so a layout unit is never taller than it
  is wide.

*As built:* there are more constants (`MIN_H`, `LABEL_UNIT_H` 32,
`PICK_S`, `PICK_MOVE`), `room` returns whole pixels, and labels need a
unit `LABEL_UNIT` wide **and** `LABEL_UNIT_H` tall.

`Panel._draw` records the CONTROLS window's position each frame it is
open (`self._panel_x`); the desk, drawn before the panel, reads last
frame's, and `display_w − PANEL_W − 12` before there is one.

*At 960 × 900:* panel open, sheet off → 384 × about 430, units 27 px:
glyphs only, as today but taller. Panel hidden → 936 × 876, units
67 × 58 px: labelled, 13 px type. On a control window 1512 px wide with
the panel open → the same 936 px: labelled beside the panel.

**Getting there.** Hiding the panel is `ui.panel`: the `H` key, the
APC40's DEVICE ON/OFF (B6, invariant), the panel's close box. The desk's
header gains one chip, `big` while the panel is open (it sets `ui.panel`
off) and `panel` while it is hidden (on). `ui.desk` still hides the desk
at any size. Nothing is added to the rail, the keys or the registry.

#### What a control shows

Units under `LABEL_UNIT` wide: today's drawing, unchanged.

Labelled (`LABEL_UNIT` or wider):

- the **glyph**, small and dim, in the cell's top-left corner;
- the **label**, in the middle (a button, a grid pad), under the ring (a
  knob), at the foot (a fader), right of the glyph (the crossfader):
  ```python
  def text(reg, b: Binding) -> str      # pure, tested
  ```
  a `set` row on an enum → that value's name (`G1·5` reads "TRIP",
  `G4·4` "Tesseract", a global scene pad "Kick & Sizzle"); a `step` row →
  the label and the step ("Brightness +3"); anything else →
  `Param.label`; a target the registry lacks → the id.
- The type is `clamp(0.2 × unit_w, 11, 18)` px. The label wraps at
  spaces to as many lines as the cell holds, at most two, and each line
  is cut with `ui.fit_text`; the whole text is in the hover.
  ```python
  def wrap(text: str, width: float, lines: int) -> list[str]    # pure, tested
  ```
  *As built:* a label that would be cut at that size is drawn at 11 px
  instead, and a step keeps its amount when cut ("Brightne… +3").
- Adjacent pads of one row whose text is the same share one label drawn
  across the run (the clip-stop row reads "Save as a new preset" once);
  each pad is still its own control to the mouse.
- A dark control: its glyph, dark, as today (D8). *As built:* at the
  labelled size its glyph is in the top-left corner like every other.
- **Whose row it is.** A control mapped on the layer that is up: the
  label in the bright ink. An invariant control: the label in the dim
  ink. The header names the layer, red while it is the global one, as
  today. So from a step back the bright names are what this preset (or,
  under SHIFT, the session's global layer) puts on the desk, and the grey
  ones are the same everywhere.
- The ring's arc, a fader's cap and an LED's colour: as today.
- The hover adds the label: "D3 · fx.kaleido.segments · Kaleidoscope
  segments · preset layer", then Akai's name.

#### The drawing

*As built:* this drawing is of an idealised device. The layout that is
drawn (`apc40.LAYOUT`: the knobs in two rows of four, the bank cross
and the transport on the right) is in §7, WP4, and in
`assets/17-learn-and-the-desk/desk-big.png`.

The panel hidden, TRIP loaded, the preset layer up, D3 picked. Cells are
cut here to fit the page; `·` is a dark control, `▓` a lit LED, `▛ ▜` the
red frame of the picked control. Grey (invariant) labels are in
parentheses.

```
 APC40 · preset layer · TRIP     D3 picked: click a param to put it here · click D3 again to let go    [ panel ]
 ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
     1        2        3        4        5        6        7        8        9      ║
 G1 (TUMBLE) (FACES)  (FIELD)  (WAKE)  ▓(TRIP)▓  (ACID)  (MANDALA)(NOITA)  Points   ║   K1        K2        K3        K4
 G2    ·        ·        ·        ·        ·        ·        ·        ·     Lines    ║   (◔)       (◔)       (◔)       (◔)
 G3    ·        ·        ·        ·      STILL    ORBIT    WAVE    RIPPLE   Faces    ║  Bright-   Speed    Instances  Pattern
 G4  5-cell  3,3-duo… Cubic    Tesser-  Rectif…  4,8-duo… 6,6-duo… 16-cell  Rotate   ║  ness                          mix
                      pyramid  act                                                   ║   K5        K6        K7        K8
 G5  10,10-… Icosa…   24-cell  Trunc…   12,12-…  Dodeca…  20,20-…  120-cell Reset    ║   (◔)       (◔)       (◔)       (◔)
                                                                            view     ║  Grid amp  Grid rate Bitmap    Zoom
                                                                                     ║                      alpha
 G6 (────────────────── Save as a new preset ──────────────────────────)  (Reset    ║ B1 (Click-  B2 ·     B3 ·     B4 ·
                                                                            all)     ║     through)
 G7  (SUB)   (BASS)   (MIDB)   (MID)    (UPR)    (AIR)      ·        ·    (Overlay)  ║      ▲ Brightness +3    (Tap tempo)
 G8   ZW       XW       YW       XY       XZ       YZ       ·        ·       C       ║ ◀ (Band −1) ▶ (Band +1) (Nudge −1)(Nudge +1)
 G9  (SUB    (BASS    (MIDB    (MID     (UPR     (AIR       ·        ·      (◔)      ║      ▼ Brightness −3    (⇧ Shift)
      Transf…) Transf…) Transf…) Transf…) Transf…) Transf…)                 Shape    ║
 G10 (SUB    (BASS    (MIDB    (MID     (UPR     (AIR       ·        ·               ║   D1        D2      ▛ D3 ▜      D4
      reset)  reset)   reset)   reset)   reset)   reset)                             ║   (◔)       (◔)     ▌ (◔) ▐     (◔)
                                                                                     ║  FX mix    Plasma   ▌Kaleido-▐ Kaleido-
     S1       S2       S3       S4       S5       S6       S7       S8       SM      ║            level    ▙scope s…▟ scope z…
      │        │        │        │        │        │        │        │        │      ║   D5        D6        D7        D8
      █        │        █        │        │        █        │        │        █      ║   (◔)       (◔)       (◔)       (◔)
      │        █        │        █        █        │        █        █        │      ║  Zoom      Zoom      Hue cycle Hue cycle
      │        │        │        │        │        │        │        │        │      ║  burst am… burst gl… paint     spread
    (SUB     (BASS    (MIDB    (MID     (UPR     (AIR     (Dyna-   (Input   (Audio   ║ B5 (audio.  B6 (Control B7 ·   B8 ·
     Post-    Post-    Post-    Post-    Post-    Post-    mics)    trim)    drive)  ║     restart)    panel)
     drive)   drive)   drive)   drive)   drive)   drive)                             ║ B9 (Cheat   B10 (Next  B11     B12 (LFO
                                                                                     ║     sheet)      preset) (Home)      trigger)
                                                                                     ║ B13 (audio.play) B14 (audio.stop) B15 (Mic)
                                                                                     ║ X ├──────────────────█────┤ (Master dim)
```

Under SHIFT the header reads "global layer · shift" in red, the K and D
knobs carry the session's names in the bright ink (Steadiness, Response,
Catch, Return, BPM; the band strip on D1–D8), rows 2–3 the scenes, and
every preset-layer control is dark.

#### A click on a control

The window stays hit-tested (no widget per control). `_body` already
finds the control under the mouse; a left click calls:

```python
def click(panel, table, c: apc40.Control, b: Binding | None) -> None    # ui_desk.py, tested
```

1. **A desk learn is armed** (`lrn.learning` set and
   `lrn.accepts(c.source)`): `lrn.learn_control(c.source, apc40)`. This
   is "Learn desk" completed by a click instead of a knob bump: the same
   function, the same refusals (an invariant control, the global layer),
   the same undo step. Nothing else happens.
2. **A hand learn is armed**: nothing; the footer keeps saying what the
   learn waits for.
3. **The control is the picked one**: `lrn.pick(None)` (let go).
4. **Otherwise**: `lrn.pick(c.source)`; `ui_routing.goto(panel,
   c.source)`; and if the panel is hidden, `ui.panel` goes on (the desk
   shrinks to its column and the pick is still framed).

A click on the window where no control is lets the picked control go.

*As built:* a pick also lets go by itself after `ui_desk.PICK_S` = 20 s
with no click in the window (`ui_desk.tick`), the header and the footer
count it down, and no click on a param maps until the mouse has moved
`PICK_MOVE` = 12 px from the click that picked (`ui_desk.armed`).

#### Picked: "click a control, then a param"

```python
# learn.py
class Learn:
    control: str | None       # the picked desk control's source; None: none

    def pick(self, source: str | None) -> None:
        """Pick a desk control (None lets go). Arming a param lets it
        go; picking a control cancels an armed learn."""
    def map_picked(self, pid: str, profile=None) -> bool:
        """The picked control takes this param: arm(pid, "desk"), then
        learn_control(control). True when it landed; the pick is over
        either way unless it was refused."""
```

*As built:* a `map_picked` that does not land — refused, or a param the
registry lacks — keeps the pick and leaves no learn armed.

One mapping path: `map_picked` is `arm` and `learn_control`, so D5, D6,
the op, the feedback, the undo step and the message are the knob
learn's.

**How it is shown.** The picked control has a red frame on the desk at
either size. The desk's header and the footer's message slot read "D3
picked: click a param to put it here · click D3 again to let go". On
ROUTING the control's line is framed (below).

*As built:* with a countdown ("D3 picked (20 s): …"); on ROUTING, which
is never dimmed, the lines say to click a param on any other page.

**Whether it can be mapped** (`ui_desk.mappable(table, c) -> str | None`,
the reason it cannot, or `None`):

- an invariant control (a fader, the bank row, SHIFT, TAP, …): picked
  for the scroll only. The line reads "S3 (track fader 3) is invariant
  (the session's): SUB Post-drive", in the dim ink. No param is a
  target. D6.
- the global layer is up: the same, "K1 is on the global layer (the
  session's) — latch SHIFT off to map into the preset". D5.
- otherwise it can.

**Clicking the param.** While a mappable control is picked and the open
page is not ROUTING, `Panel._draw` draws the page inside
`imgui.begin_disabled()` and sets `self._picking`: the page dims and no
widget takes a click. `Panel._ctx`, which every param widget already
calls right after drawing itself, then does the picking: the widget
under the mouse (`is_item_hovered(allow_when_disabled)`) gets the red
learn frame, and a left click on it calls
`self.learn.map_picked(a.id, apc40)`. The rail is outside the page, so
pages still change; the footer and the desk still take clicks. A param
that cannot go on the desk (`Kind.TEXT`, `desk.shift`) is not a target.
ROUTING is never dimmed: there the picked control's own line is what the
user came for, and its target combo (an existing row) is the way to
re-aim it without leaving the page.

**The param already has a desk row.** `Bindings.bind`'s rule, as for a
knob learn: the control's old row goes, and so does the param's previous
preset-layer row *in the same role* (its knob when a knob is mapped; a
button of the same op and value when a button is). The message names
what let go ("learned view.bright ← D3 (device knob 3) (into the
preset); K1 let go") and one Ctrl+Z puts both back.

**Letting go.** A click on the picked control, on the desk's empty
ground, or on the footer's line; picking another control; arming a
learn; a successful map. Not Esc (it quits). A preset load keeps the
pick (the control is still there). *As built:* and 20 s with no click
(`PICK_S`).

#### ROUTING scrolls to its row

```python
# ui_routing.py
def goto(panel, source: str) -> None:
    """Scroll the rows' child to the line of the control `source` names
    and mark it. Clears the filter (WP5)."""
```

- `goto` sets `_state(panel)["goto"] = source` and `["find"] = ""`. It
  does **not** change the page (fork 2): if ROUTING is open it scrolls
  now; if not, it scrolls when ROUTING is next opened while that control
  is still picked.
- `desk()` and `session()` draw their lines inside the `##routes` child.
  The first line whose control overlaps the source (`Binding.overlaps`) —
  on the layer that is up for a mapped control, the "unmapped — dark"
  line for a dark preset control — calls `imgui.set_scroll_here_y(0.3)`
  once and the state's `goto` is cleared. The scroll is the child's: the
  page itself still never scrolls
  (`test_the_routing_rows_scroll_in_their_own_child`).
- The line of the picked control (`panel.learn.control`) is framed in
  red for as long as it is picked.
- A control dark on the global layer has no line: the learn line says
  "K6 · unmapped on the global layer" and nothing scrolls. *As built:*
  the desk's header and the footer say it; ROUTING's head gains no
  line.

**Undo.** `Learn.learn_control` pushes (WP2). `pick` changes no table and
is no step.

### WP6 — Docs and hand checks

Owns the shared documents:

- `ARCHITECTURE.md` §3.5 (Learn: `want`, `accepts`, `learn_control`, the
  click as a third completer, the pick; Unbind), §2's frame box S5
  ("a moved axis of the wanted hand may complete a Learn"), §4's shapes
  for `learn.py` and `ui_desk.py`.
- `ENGINEERING.md` §7 (the panel: the menu, the desk's sizes, the
  ROUTING filter, the footer's learn line).
- `DECISIONS.md` and `DECISION-REGISTER.md`: a row for each fork below
  as built, for the owner to confirm or overturn; D5 and D6's status
  lines gain the click and the "stays armed" rule; decision 25's row
  gains the desk's sizes.
- `plans/README.md` (plan 17's row), `CHECKPOINT.md`.
- `11-hand-checks.md`: group M from §8, numbered after plan 16's group
  L; the checks it supersedes in part are marked (37: a refused learn
  now stays armed; 45: the diagram's size).
- This file's "As built".

## 3. Parameter budget

Everything the plan adds or removes, and what each replaces.

| Added or removed | Kind | Replaces, or why nothing |
|---|---|---|
| `Learn desk` | menu item | Replaces `Learn`. |
| `Learn hand ▸ left / right` | menu item, a submenu of two | The other half of `Learn`: the price of a learn that cannot pick the wrong hand. Not drawn on a rig without a tracker or on a param a hand cannot drive. |
| `Unbind` (a submenu only with both kinds bound) | menu item | Replaces `Unbind` **and** `Unbind hand`. |
| `Unbind hand` | menu item | **Removed.** |
| "performed by …" | menu line | **Removed**: the route's own line says it. |
| The desk's `big` / `panel` chip | one button | Nothing new behind it: it sets `ui.panel`, which `H` and DEVICE ON/OFF already set. |
| Labels on the desk | drawing | Replace hovering each control to read its param. |
| A click on a desk control | gesture | Replaces finding the control's line on ROUTING by eye; with the next click, replaces Learn-then-reach-for-the-knob when the knob is not at hand (and is the only way with no device). |
| The ROUTING filter | one text field, UI state | Replaces scrolling the rows' child to find a line. Not a param. |
| The footer's learn line | a line in the existing slot | Replaces opening ROUTING or SYSTEM to read what a learn did or why it was refused. |
| The menu on a row's label and on every meter | where the existing menu opens | Nothing new to learn. |

**Not added:** a param, a page, a key, a config key, a file, a schema
field.

**The menu, counted** (clickable items; lines of text are not counted):

| Control | Before | After |
|---|---|---|
| Unmapped, a rig with hands | 2: Learn · Route a lane here… | 3: Learn desk · Learn hand ▸ · Route a lane here… |
| Unmapped, no tracker | 2 | 2: Learn desk · Route a lane here… |
| A knob and a hand on it (Speed in TUMBLE) | 5: Learn · Unbind · Gate ▸ · Unbind hand · Route a lane here… | 5: Learn desk · Learn hand ▸ · Unbind ▸ · Gate ▸ · Route a lane here… |
| A knob on it, no tracker | 3: Learn · Unbind · Route a lane here… | 3: Learn desk · Unbind · Route a lane here… |
| Only a fader on it (invariant), a rig with hands | 3: Learn · Unbind (which refuses) · Route a lane here… | 3: Learn desk · Learn hand ▸ · Route a lane here… |
| A file path | 1: Learn (which cannot act), over a dim "not modulatable" | 0, over the same dim line |

The menu is one item longer in one case, the unmapped param on a rig
with hands, which is the roadmap's own spelling of the fix; it is never
longer elsewhere, and no item is left that can only refuse. Fork 5 has
the shorter spellings.

Rejected because an existing concept does the job: a DESK page (the
window grows); a `ui.desk_big` param and key (`ui.panel`); a "map mode"
toggle (a pick is a click); a learn timeout setting (the footer shows an
armed learn and a click cancels it — *as built:* still so for a learn;
a *pick* does time out, after a fixed 20 s, because it dims a page); a filter per section (one field);
a "show on desk" item on ROUTING lines (the picked frame is both ways
already); a mapping dialog (the click).

## 4. What this plan does not change

- **The control model** (ARCHITECTURE §3). A desk row is a scene-setter
  and a route a performer, as before. `Learn.learn_control` writes a
  MIDI row through `Bindings.bind`; a hand learn still goes through
  `learn_source`, `_place` and `replace_owner`. `Router.modulate` stays
  the one caller of `Param.modulate`. `hands/core.py`, `hands/signal.py`,
  `lfo.py`, `tempo.py` and `undo.py` import nothing from the package.
- **One performer per parameter, and the Replace / Keep prompt.** A hand
  learn onto a performed param is still held in `Learn.pending`; a desk
  learn never prompts (scene-setters never do). Unbind removes; it
  never replaces.
- **D5.** The global layer is never learned into. A knob bump, a click
  on the diagram and a pick-then-click are all refused while it is up,
  in the same words.
- **D6.** Invariant controls mean one thing on both layers and no preset
  maps them: the faders, the bank row, SHIFT, TAP, METRONOME, NUDGE, the
  transport, the crossfader (master dim), OVERDUB (home), the clip-stop
  row (SAVE AS). None can be learned, clicked into a mapping or unbound.
  Under fork 6 they also keep doing their one job while a learn is
  armed.
- **D8.** An unmapped control is dark and dead, on the device and on the
  desk at any size.
- **D2 / plan 13 §3.3.** A learn, a map and an unbind edit the loaded
  preset: the dirty dot, no file written.
- **Hand routes are addressed by name.** `accepts` reads the name
  (`hand:left.…`); nothing writes a number.
- **Twelve axes, no gesture vocabularies.** Which hand a learn listens
  to is chosen in the menu, not by a gesture.
- **The render window has no imgui.** The desk is in the control window.
- **No page scrolls at the control size.** No page is added; ROUTING
  gains no line; the desk window has no scrollbar at any size.
- **The glyphs and the layout** (decision 25): `apc40.LAYOUT` is not
  edited.
- **Drag-to-map** stays deferred (roadmap §6).
- What a learned hand row is (`position`, depth 1): plan 18's. *As
  built:* plan 18 changed it — a `push` at `hands.learn_depth` by
  `Learn._row`'s table (register row 52).

## 5. Exit criteria

### Headless: named tests

**WP1**

| Test | Proves |
|---|---|
| `tests/test_learn.py::test_unbind_removes_the_presets_desk_rows_and_every_route` | A param with a knob, two step buttons, a hand route and a disabled LFO route: all go; an invariant row on it stays; nothing is written to disk. |
| `tests/test_learn.py::test_unbind_by_kind` | `desk=False` leaves the desk rows; `routes=False` leaves the routes. |
| `tests/test_learn.py::test_unbind_is_one_undo_step_and_none_when_nothing_goes` | One Ctrl+Z puts every row back, a route's depth subscriber with it; a refused unbind leaves no step. |
| `tests/test_ui_shell.py::test_the_menu_lists_and_unbinds_with_no_midi_adapter` | `panel.midi is None`: the desk row's line is drawn with its glyph and Unbind is offered. |
| `tests/test_ui_shell.py::test_unbind_is_not_offered_on_a_session_only_param` | A fader's param: the row's line reads "invariant", no Unbind item. |
| `tests/test_midi.py::test_unbind_removes_only_preset_layer_rows_and_writes_no_file`, `::test_an_unbind_is_one_undo_step` | Still pass, through the delegate. |

**WP2**

| Test | Proves |
|---|---|
| `tests/test_learn.py::test_accepts_by_want` | `desk` accepts `cc:` / `note:` / `pitch:` and no `hand:`; `hand:left` accepts `hand:left.roll` and `hand:left.pinch.index`, not `hand:right.y`; `None` accepts all; nothing armed accepts none. |
| `tests/test_hands.py::test_a_hand_learn_listens_to_one_hand` | §1 row 1's two cases, armed with `hand:left`: the right hand travels further and the left hand's axis is learned. |
| `tests/test_hands.py::test_the_hands_never_complete_a_desk_learn` | Armed `desk`, a hand sweeps every axis: still armed, no row. |
| `tests/test_hands.py::test_a_rearm_starts_a_fresh_baseline` | Arm A, move 0.2, arm B, move 0.1: nothing learned. |
| `tests/test_midi.py::test_a_knob_bump_during_a_hand_learn_does_its_own_job` | Armed `hand:left`, K1 turns: Brightness moves, the learn is still armed, no row added. |
| `tests/test_midi.py::test_an_invariant_control_works_through_a_desk_learn` | Armed `desk`: a fader moves its param, SHIFT latches, the learn is still armed. |
| `tests/test_learn.py::test_learn_refuses_the_global_layer_and_invariant_controls` (rewritten) | The global layer refuses in the same words and the learn stays armed; after SHIFT the same knob lands. |
| `tests/test_learn.py::test_learn_control_needs_no_adapter` | A bare `Learn` over a table, `learn_control("cc:*:18", apc40)`: a preset-layer ring row, `redraw_serial` bumped, one undo step. |
| `tests/test_learn.py::test_a_knob_learn_writes_a_desk_row_into_the_loaded_preset`, `::test_a_knob_learn_replaces_an_any_channel_row_on_the_same_knob`, `::test_a_learn_is_one_undo_step`, `tests/test_midi.py::test_learn_*` | Still pass through the delegate. |
| `tests/test_ui_shell.py::test_the_menu_offers_learn_desk_and_learn_hand` | With a tracker: both; without: Learn desk only; a non-modulatable param: no hand item; a path: neither. |
| `tests/test_ui_shell.py::test_the_footer_says_what_a_learn_waits_for_and_what_it_did` | Armed: the red line on every page; a refusal: the warning for `MESSAGE_S`. |
| `tests/test_hands_boundary.py`, `tests/test_routing_boundary.py`, `tests/test_lfo_boundary.py` | Unchanged and passing. |

**WP3**

| Test | Proves |
|---|---|
| `tests/test_ui_shell.py::test_a_rows_label_opens_its_params_menu` | `_row` and `_fader` call `open_popup_on_item_click` with the id `_ctx` uses. |
| `tests/test_ui_shell.py::test_every_meter_has_the_band_select_menu` | One `_ctx` per meter, distinct keys, no id conflict. |
| `tests/test_ui_shell.py::test_every_page_fits_the_control_window` | Unchanged and passing. |

**WP5**

| Test | Proves |
|---|---|
| `tests/test_ui_routing.py::test_the_filter_matches_glyph_param_and_source` | `matches`: "d3", "bright", "r height", "lfo 1", two words together; case does not matter. |
| `tests/test_ui_routing.py::test_a_filtered_page_draws_only_matching_lines_and_keeps_its_ids` | With "kaleido": only those routes, desk lines and macros are drawn; no imgui id conflict; × on a filtered row removes that row. |
| `tests/test_ui_routing.py::test_the_filter_is_ui_state` | Not a param, not in a snapshot, not an undo step; survives a preset load; cleared by `goto`. |
| `tests/test_ui_shell.py::test_every_page_fits_the_control_window`, `::test_the_routing_page_fits_over_a_loaded_preset_and_a_full_desk`, `::test_the_routing_rows_scroll_in_their_own_child` | Unchanged and passing, with the field drawn. |

**WP4**

| Test | Proves |
|---|---|
| `tests/test_ui_desk.py::test_the_desk_takes_the_room_it_has` | `room`: at 960 × 900 with the panel open it ends 12 px left of the panel and is at least `MIN_W`; hidden it is 936 wide; above the sheet with the panel open, beside it with the panel hidden; a unit never taller than wide. |
| `tests/test_ui_desk.py::test_the_big_desk_labels_every_lit_control_and_never_scrolls` | Panel hidden at `CONTROL_SIZE`, TRIP: a label drawn for each lit control (one per run), none for a dark one; the window's scroll range is 0; on both layers. |
| `tests/test_ui_desk.py::test_the_small_desk_draws_glyphs_only` | Panel open at `CONTROL_SIZE`: no label; the window does not overlap the panel's rect. |
| `tests/test_ui_desk.py::test_a_controls_text` | `text`: an enum `set` row's name, a step, a label, a missing param's id. `wrap`: two lines at spaces, each cut to the width. |
| `tests/test_ui_desk.py::test_a_click_picks_and_a_second_click_lets_go` | `click` on D3: `learn.control`, `goto` set, the panel opened if hidden; again: `None`. |
| `tests/test_ui_desk.py::test_a_click_completes_an_armed_desk_learn` | Armed `desk`, `click` on D5: the row, one undo step, no pick. Armed `hand:left`: nothing. |
| `tests/test_learn.py::test_pick_then_param_maps_through_the_learn` | `pick("cc:*:18")`, `map_picked("view.speed", apc40)`: the same row `learn_control` makes; the param's old knob row gone and named in the message; one Ctrl+Z restores both. |
| `tests/test_learn.py::test_a_pick_on_an_invariant_control_or_the_global_layer_maps_nothing` | `mappable` gives the reason; `map_picked` refuses; the table is untouched. |
| `tests/test_ui_shell.py::test_a_picked_control_dims_every_page_but_routing` | `begin_disabled` wraps the page for each key but `routing`; never without a mappable pick. |
| `tests/test_ui_routing.py::test_goto_scrolls_the_rows_child_to_the_controls_line` | With a full desk: after `goto("cc:*:18")` and two frames the child's scroll is not 0 and the page's is; a dark control scrolls to its dark line; the filter is cleared. |
| `tests/test_ui_desk.py::test_the_diagram_draws_on_both_layers_and_hides` (amended) | The only widget id the desk adds is its header chip. |
| `tests/test_ui_shell.py::test_every_page_fits_the_control_window` | Unchanged and passing with the desk on. |

The whole suite, `uv run ruff check` and the three boundary tests pass
on `plan-17-integration` before it merges into `finish-line`.

### At the machine

Group M, §8.

## 6. Forks

Each was settled without the owner. The cost to reverse is what it takes
to switch after the build.

**1. Where the big desk lives** (the fork the roadmap names).

| Option | Trade-off |
|---|---|
| (a) Its own page in the rail | A page is 392 px wide at the control size, the diagram 380 already: no room for one label. A fifteenth page, reached only with the mouse. |
| (b) Its own page that widens the panel while it is open | Room, at the price of a panel that changes width by page, against every page's layout and a panel the user has moved. |
| **(c) The existing window takes the room it has; with the panel hidden it is the whole control window** | Nothing new: `ui.panel` already has a key (`H`) and a button on the desk (DEVICE ON/OFF). Labels appear by size, so a maximised control window shows them beside the panel. The desk and the panel are not both big at 960 px. |
| (d) The existing window with its own `ui.desk_big` toggle, drawn over the panel | One more param and one more key for what (c) does with the panel's. |

**Recommended: (c).** Fewest new things, and the only one reachable from
the desk itself, which is where the owner is when stepping back. Reverse:
`ui_desk._body` draws into any rectangle; a page is one `_page_desk`
that calls it.

**2. What a click on a control does.** The roadmap gives a click two
jobs: scroll ROUTING to the row, and start "then a param".

| Option | Trade-off |
|---|---|
| (a) Always open ROUTING at the row; map from the row's target combo | No picked state. But the param is then found in a list of some 450 ids, not clicked where it is seen, and a click made from VIEW throws the page away. |
| **(b) Pick: frame the control; ROUTING scrolls if it is open (or when it is next opened); the next click on a param maps** | One click, one state. The page the user is on stays. ROUTING is one rail click away and already at the row. |
| (c) Pick and open ROUTING | Both jobs at once, and the user must leave ROUTING again to click the param. |

**Recommended: (b).** Reverse to (c): one line in `ui_desk.click`.

**3. How the param is chosen once a control is picked.**

| Option | Trade-off |
|---|---|
| **(a) A plain click on the param's widget, on a dimmed page** | "Click, click", the roadmap's words. The page is drawn disabled so the click cannot also move the slider; the dimming is the sign of the state. A stray click maps (one Ctrl+Z). Rests on imgui reporting hover on a disabled item (`allow_when_disabled`), to be confirmed in WP4's first hour. |
| (b) An item at the top of the param's right-click menu, "put D3 here" | No dimmed page and no chance of a stray map. Three clicks, the same count as Learn desk then a click on the desk: it adds an order, not a shortcut. |
| (c) Only ROUTING's target combo | See 2 (a). |

**Recommended: (a)**, with (b) the fallback if the disabled page does
not behave. Reverse: remove the wrap in `Panel._draw`, add one menu item.

**4. What Unbind covers.**

| Option | Trade-off |
|---|---|
| (a) The preset's desk rows and the hand rows, as the roadmap lists | A param performed by an LFO or a band still shows "performed by LFO 1" and cannot be unbound from its own menu. |
| **(b) The preset's desk rows and every route on the param** | One rule: Unbind removes what the menu's lines list. A lane or LFO route can be removed from the widget it moves. |

**Recommended: (b).** Reverse: a filter on the scheme in `Learn.unbind`.

**5. How the Learn items are spelled.**

| Option | Trade-off |
|---|---|
| **(a) `Learn desk` · `Learn hand ▸ left / right`** | The roadmap's. The commonest learn is one click. One item more than today on a rig with hands. |
| (b) `Learn desk` · `Learn left hand` · `Learn right hand` | No submenu; two items more than today. |
| (c) `Learn ▸ desk / left hand / right hand / lane` (folding in "Route a lane here…") | The shortest menu (one item where there were two). Every learn costs a hover, and "Route a lane here…" stops being findable by its name. |

**Recommended: (a).** Reverse: the item list in `Panel._ctx`.

**6. What a control that cannot be learned does while a desk learn is
armed.** Today the first message from any control ends the learn, landed
or refused, and is swallowed: a fader that jitters kills the learn, and
with the global layer up SHIFT itself is refused, so the way out is to
re-arm.

| Option | Trade-off |
|---|---|
| (a) As today | Nothing to build. The session's "learn did nothing" is partly this. |
| (b) A refusal leaves the learn armed; the message is still swallowed | A fader's jitter no longer ends a learn. SHIFT still cannot be pressed while armed. |
| **(c) A refusal leaves the learn armed, and an invariant control is not a candidate at all: it does its own job** | SHIFT, the bank, TAP and the faders work through a learn, which is what "invariant" promises. A pad pressed mid-learn loads its preset, and the learn then lands in that preset. Changes what `test_learn_refuses_the_global_layer_and_invariant_controls` pins (the press of SHIFT not latching). |

**Recommended: (c).** No invariant control can be learned under any
option, so D6 stands. Reverse: one branch in `MidiIO._handle` and one
line in `learn_control`.

**7. Where the desk learn lives.**

| Option | Trade-off |
|---|---|
| (a) Stay in `MidiIO._learned`; the click calls the adapter | No move. No adapter (`[midi] enabled = false`), no mapping; the click would be a second path beside it or depend on `panel.midi`. |
| **(b) Move it to `Learn.learn_control`; the adapter and the click both call it** | One path, working with no device. `learn.py` stays free of adapters: the profile is an argument. |

**Recommended: (b).** Reverse: move the body back.

**8. What a control's label says.**

| Option | Trade-off |
|---|---|
| (a) The param id (`fx.kaleido.segments`) | What ROUTING prints. Long, and reads as code from a step back. |
| **(b) `Param.label`, and the value's name for an enum `set` row** | The panel's own words; the bank row reads as the presets' names. Three params have no label of their own and show their id (`audio.play`, `audio.stop`, `audio.restart`). The id is in the hover. |

**Recommended: (b).** Reverse: `ui_desk.text`.

**9. What clears the filter.**

| Option | Trade-off |
|---|---|
| **(a) Only the user (emptying it, its ×) and a desk click** | It holds across presets, which is the use: "show me what is on the kaleidoscope in each". A forgotten filter hides rows; the red "3 of 41 rows" says so. |
| (b) Also a preset load | Never stale. Lost on every F-key while comparing. |

**Recommended: (a).** Reverse: one line in `Presets.load_doc`'s caller.

**10. Whose pinch gates a hand learn.** `held_gate(side)` asks the
learning hand's thumb first and then the other hand's, so under "Learn
hand ▸ left" a pinch held by the right hand becomes the row's gate when
the left hand holds none.

| Option | Trade-off |
|---|---|
| **(a) Leave it** | One hand's pinch gating the other's movement is a plan 08 feature, and `held_gate` is plan 18's file. |
| (b) Only the learning hand's pinch | Stricter reading of "one hand". Removes a use. |

**Recommended: (a)**; raised to plan 18 as a note, not a change.

**11. A source-first hand learn** (click an axis row on the HANDS page,
then a param). It would name the axis outright, with no "moved furthest"
guess, on the picked state WP4 builds.

| Option | Trade-off |
|---|---|
| **(a) Not built** | The roadmap does not ask for it; it is one more way to do what "Learn hand ▸" now does safely; it is in `hands/panel.py`, plan 18's. |
| (b) Build it | About twenty lines on `Learn.pick`. A second meaning for a click on an axis row, which selects the axis today. |

**Recommended: (a).** If the hand checks show the wrong *axis* still
winning within one hand, (b) is the fix and plan 18 has the file.

## 7. As built

Written by WP6 from each PR's "As built" and review sections, every
statement checked against the code on `plan-18-integration` at 8c0e416
(plan 17's five code packages and plan 18 whole). On that commit: 1276
passed, 1 skipped (the hands tape), `ruff check .` clean. Where this
section and §2 differ, this section is the code; §2 carries an
"*As built:*" note at each such place.

**What has been seen, and by whom.** Nothing here was tried by a person
at the rig. No APC40 has had a knob learned, unbound or mapped by a
click, no real hand has completed "Learn hand ▸ left", and **nobody has
clicked, right-clicked or typed in the real control window**: not a menu,
not a label, not a control of the desk, not the filter field. Three
kinds of evidence exist, and the entries below say which is which:

- *tests*: the named pytest nodes — synthetic hands
  (`tests/fake_hands.py`), fake MIDI ports, headless imgui, and for the
  menu on a label, the desk's click, the click on a param and the filter
  field, **imgui mouse and keyboard events fed by the test** at the
  place the item was drawn;
- *demos*: the scripts under `tools/`, each on a temp home of its own,
  with their output kept under `docs/plans/assets/17-learn-and-the-desk/`
  (reported by the agent that built the package; every picture is a
  read-back from a hidden window, every popup opened by the script and
  every click a fed event);
- *seen in scripted launches by the orchestrator*: the real app
  (`uv run hyperspace`) started against a temp home on a laptop and
  driven from a script, with no APC40 and no camera. What it saw:
  - a "Learn desk" armed on `view.bright` and completed on D3 put
    Brightness on D3 and said K1 let go;
  - with "Learn hand ▸ left" armed, the right hand's axis was ignored
    and the left hand's roll was learned — by calling the hands
    adapter's learn path directly with made-up axis readings, **no real
    hand**;
  - Unbind removed a knob row and a hand route in one go, and three
    undos put everything back with the preset clean;
  - picking D3 and then `Learn.map_picked` put Speed on D3 and said K2
    let go; a pick on a fader was refused as invariant; the control
    window ran with the panel hidden (the big desk drawn) and came
    back; one undo took the map back;
  - on the combined branch: 1276 passed, 1 skipped, ruff clean, no
    runtime error and an empty stall log.

  That is a launch on a laptop driven by function calls, not a session
  at the machine: no menu was opened and nothing was clicked in it.

Hand checks 64–71 (group M of `11-hand-checks.md`) are what the machine
still owes. Decision register rows 57–64 are this plan's forks, each
built on the plan's recommendation by the run's orchestrator, not by the
owner; row 58 also carries what the orchestrator required beyond the
plan (a pick that lets go by itself, said loudly).

**Where it was merged.** WP1, WP2 and WP5 went onto
`plan-17-integration` and from there into `plan-18-integration`
(c9bdcf6), where plan 18's learn-default package was built on top of
WP2 (§2's seam); WP3 and WP4 followed the same way (8c0e416). This
package, WP6, is written on `plan-18-integration`, after plan 18's own
documents, so the shared tables are edited once. PRs #96 and #102 show
as open on GitHub: their branches were merged into
`plan-17-integration` by the merge commits named below.

### WP1 — One Unbind (PR #93, merged 9b13e34)

**Built.** `learn.py`: `Learn.unbind(ids, *, desk=True, routes=True,
name=None) -> list[Binding]`, `Learn.bound(ids)` and the module function
`learn.bound(table, ids)` → (the loaded preset's desk rows, the routes,
the session's MIDI rows). A desk row goes through `Bindings.unbind` (it
bumps `redraw_serial`), a route — any scheme, enabled or not — through
`Bindings.remove`, its depth subscribers with it; one
`undo.push(f"unbind {real_id}")`, only when something goes; no file
written; a session row is never removed, and with nothing else to remove
that is a refusal in the old words. `midi.py`: `MidiIO.unbind(pid)` is
`self.learner.unbind((pid,), routes=False, name=self.control_name)`.
`ui.py`: `Panel._table` (the router's table, else the learn object's,
never the adapter's), `_ctx_lines`, `_ctx_unbind`, `_row_name`,
`_route_source`. The menu lists one line per thing bound — a preset desk
row as glyph and Akai's name (`K2 (track knob 2)`, `B16 (▲) · step +3`),
a route as `Router.describe` gives it (`(off)` when disabled), a session
row dim (`SM (MASTER fader) · invariant`, `… · global layer`) — and
draws **Unbind** only when it would remove something: a plain item with
one kind bound, a submenu `desk — K2` / `route — R height, LFO 1` /
`both` with both. "Unbind hand" and the "performed by …" line are gone.
`hands/panel.py`: `ctx_rows(panel, p, *, lines=True, gate=True)`.

**Differs from §2, and why.**

- *`MidiIO.unbind` passes `name=self.control_name`.* Without it the
  adapter's message would read "MIDI CC 48 ch1" where it read "K1 (track
  knob 1)".
- *`Learn.bound` and `learn.bound(table, ids)` are new.* `unbind` needed
  the three lists; the menu asks the same function, so its lines are
  exactly what Unbind removes, also on a panel with no learn object.
- *A route is never a MIDI row* (review). `Bindings.routes_to` filters
  on the op alone, so a session MIDI row with a `push` op could have
  been listed and removed as a "route"; `learn.bound` leaves every MIDI
  row out of the routes.
- *Routes are taken on both ids* (the drawn param's and the real one's),
  as the desk rows are; the plan had `routes_to(real_id)` only.
- *`ctx_rows` takes `lines=` and `gate=`* and `_ctx` calls it twice: the
  hand rows' lines above the items, the `Gate: … ▸` submenu among them.
- *The rows `unbind` returns and names are the ones the table took out*
  (`Bindings.unbind`'s own return values; review).
- *A Replace / Keep question held against a route Unbind removes is
  withdrawn* (`pending` cleared; review). Not reachable from the panel,
  where the prompt is modal.
- *The message* is "unbound view.speed from K2 (track knob 2), R height
  pushes +0.45 and LFO 1 pushes +0.3"; the old "(in the preset)" tail is
  gone, and it names the real id.
- *The submenu's label is `Unbind`*; imgui draws the arrow.
- *A no-op unbind opens no undo step at all* (it used to open an empty
  one that was dropped): one assertion of
  `tests/test_undo.py::test_an_action_that_changes_nothing_leaves_no_step`
  was amended.
- *With an adapter, the control goes dark one poll later*, at the
  adapter's next `_follow_table` (the `redraw_serial` bump), not inside
  `MidiIO.unbind`.

**Left as the plan has it, for the owner to know** (review):

- Unbind on a drawn alias (`band.sel.*`) also removes the desk rows on
  the selected band, and the message names the band's own id.
- `MidiIO.unbind` has no caller in the app any more; it stays as the
  delegate its two tests call.
- `Panel._row_name` is one more place a control is named (beside
  `ui_routing.control_name` / `control_glyph` and `MidiIO.control_name`).

**Tests.** `tests/test_learn.py::test_unbind_removes_the_presets_desk_rows_and_every_route`,
`::test_unbind_by_kind`,
`::test_unbind_is_one_undo_step_and_none_when_nothing_goes`;
`tests/test_ui_shell.py::test_the_menu_lists_and_unbinds_with_no_midi_adapter`,
`::test_unbind_is_not_offered_on_a_session_only_param`. Through the
delegate, unchanged:
`tests/test_midi.py::test_unbind_removes_only_preset_layer_rows_and_writes_no_file`,
`::test_an_unbind_is_one_undo_step`.

**Demo.** `docs/plans/assets/17-learn-and-the-desk/unbind-demo.txt`
(`tools/learn_demo.py unbind`: headless; the menu read as text, with the
popup's `begin` answered for it; the same transcript with and without
`panel.midi`) and `menu-unbind.png` (`tools/learn_shot.py unbind`: a
hidden window, the popup opened with `open_popup`, the submenu by
telling imgui the mouse is over its item). Both were regenerated by WP2
and show the Learn items as they are now.

**Not verified.** A real right-click; whether the submenu is comfortable
to hit and how the menu reads at distance. That a control goes dark on
an APC40 after an Unbind (fake ports only). `[midi] enabled = false` was
stood in for by `panel.midi = None` in the tests and the demo.

### WP2 — Learn that cannot pick the wrong source (PR #96, merged 0132f3f)

**Built.** `learn.py`: `WANTS = ("desk", "hand:left", "hand:right")`,
`Learn.want`, `Learn.arm(pid, want=None)`, `Learn.accepts(source)`,
`Learn.learn_control(source, profile=None) -> bool` (the body of
`MidiIO._learned`, moved: the same preset-layer row, op, feedback and
one `undo.push`, the profile an argument, `redraw_serial` bumped),
`Learn._row` (extracted for plan 18), `Learn.said_n`, `Learn.armed_n`;
`learn_source` asks `accepts` first. `midi.py`: `_learned` is
`self.learner.learn_control(Binding.midi_source(kind, channel, number),
self.profile)`; in `_handle`, a CC or a press is a candidate for the
armed learn only when the learn accepts a desk source **and** the
control is not invariant — a candidate is not dispatched, landed or
refused; everything else is dispatched as if no learn were armed.
`hands/core.py`: `HandsIO._learn`'s guard, its baseline's key and its
`moved` list. `ui.py`: `_ctx_learn` (**Learn desk**; **Learn hand ▸
left / right**), `_hand_sides`, `_learn_hint` reading the want, the
footer's armed line and the `"learn"` key of `_message`, `_learn_status`,
the cheat sheet's row `("right-click", "a control: learn desk / hand ·
unbind")`. `ui_routing.py`: `_learn_line`, the hint in `desk()`.

**Differs from §2, and why.**

- *`learn_control` asks `accepts` itself* (review). Only its caller in
  `MidiIO._handle` did, so a click on the desk could have completed a
  hand learn.
- *`learn_control` on an id the registry lacks clears the learn*
  (`take()`); the plan said only "→ False". Left armed it would swallow
  every desk message until cancelled.
- *`arm()` raises `ValueError` on a want outside `WANTS`*, clears
  `refused` (so `refused` while armed means *this* learn was refused and
  still waits), and counts the arms in `armed_n`; `take()` clears `want`
  too.
- *The hands' baseline key is `(pid, want, armed_n)`* (review): a cancel
  and re-arm of the same param and want between two polls starts fresh.
- *`said_n` counts what was said*, so the same refusal twice shows twice
  in the footer.
- *The footer.* "(click to cancel)" is on the line only where it fits
  and on the hover otherwise (`ui.CANCEL_TIP`); the click cancels either
  way. A line just said — a refusal that left the learn armed, a library
  warning, an undo — shows first for `MESSAGE_S`, then the armed line
  returns (review: the armed line used to hide them). At the control
  size the desk's hint is cut ("turn a knob or press a button on th…");
  the whole is on the hover.
- *ROUTING's and SYSTEM's learn lines* show a refusal that left the
  learn armed as the reason and "— still learning `<id>`" until the
  learn lands, is cancelled or is armed again.
- *The click's wording is switched on by `ui_desk.click` existing*
  (`hasattr`): `_learn_hint` says "…, or click one on the diagram…" and
  ROUTING's desk hint ", or click a control" only once the desk can be
  clicked (it can, since WP4). With no MIDI adapter and no clickable
  desk an armed desk learn would read "nothing to learn from (no MIDI)";
  with WP4 in, it reads "click a control on the desk diagram…".
- *"Let go" is said by glyph* when the profile has `glyph` ("…; K1 let
  go"), else by name.
- *`tests/test_desk.py::test_the_clip_stop_row_is_invariant` was
  rewritten* though §5 does not list it: under fork 6 a clip-stop press
  during a learn saves, as it always does, and the learn stays armed.

**What plan 18 then changed** (§2's seam; not this plan's work).
`Learn._row` is no longer the verbatim `position` row: it takes
`centred=` and `depth=` and lands a `push` at `hands.learn_depth` by its
rule table (plan 18 WP3, register row 52), and `learn_source` and
`HandsIO._learn` pass them. The demo transcript `learn-demo.txt` was
written before that and still shows "positions" rows.

**Left as the plan has it, for the owner to know** (review):

- **A desk learn armed while SHIFT is latched swallows every control
  that is not invariant** until it lands or is cancelled: each is
  refused for the global layer and not dispatched. The footer says so in
  the warning colour, a press of SHIFT (invariant) unlatches it, and a
  click on the footer's line cancels.
- **A preset pad pressed mid-learn loads its preset** (the bank row is
  invariant), and the learn then lands in that preset.
- Under "Learn hand ▸ left" the row's gate can be the right hand's
  pinch (fork 10; `held_gate` is plan 18's).
- A fader that is passed over while a learn is armed is no longer the
  audit's R13 case: an invariant control is dispatched. A preset-layer
  control refused for the global layer is still swallowed.

**Tests.** `tests/test_learn.py::test_accepts_by_want`,
`::test_learn_control_needs_no_adapter`,
`::test_learn_refuses_the_global_layer_and_invariant_controls`
(rewritten); `tests/test_hands.py::test_a_hand_learn_listens_to_one_hand`,
`::test_the_hands_never_complete_a_desk_learn`,
`::test_a_rearm_starts_a_fresh_baseline`;
`tests/test_midi.py::test_a_knob_bump_during_a_hand_learn_does_its_own_job`,
`::test_an_invariant_control_works_through_a_desk_learn`;
`tests/test_ui_shell.py::test_the_menu_offers_learn_desk_and_learn_hand`,
`::test_the_footer_says_what_a_learn_waits_for_and_what_it_did`;
`tests/test_desk.py::test_the_clip_stop_row_is_invariant`. Through the
delegate: `tests/test_learn.py::test_a_knob_learn_writes_a_desk_row_into_the_loaded_preset`,
`::test_a_knob_learn_replaces_an_any_channel_row_on_the_same_knob`,
`::test_a_learn_is_one_undo_step`, and `tests/test_midi.py`'s
`test_learn_*`. The three boundary tests are unchanged.

**Demo.** `learn-demo.txt` (`tools/learn_demo.py learn`: synthetic
hands, desk messages on fake ports, the footer read from a drawn frame —
§1 row 1's two cases replayed with a bare learn and with "Learn hand ▸
left"; a knob bump during a hand learn; a fader and SHIFT through a desk
learn, the global layer's refusal and the learn still armed),
`menu-learn.png` and `learn-armed.png` (`tools/learn_shot.py learn` /
`armed`: a hidden window, nothing clicked).

**Not verified.** A real hand, knob, fader or right-click. Whether
"Learn hand ▸ left" feels right at the box, and whether the wrong *axis*
within one hand still wins (fork 11's fallback). That SHIFT's LED
lights and a ring follows after a learn on an APC40. The footer's
click-to-cancel is `imgui.is_item_clicked()` on a text item: drawn,
and no test clicks it. A real hot reload onto a `Learn`, `HandsIO` or
`Panel` from before the new fields (they are read with `getattr`).

### WP3 — Learn where it is missing (PR #99, merged df65ce7)

**Built.** All in `ui.py`, with one predicate in `ui_routing.py`.
`Panel._ctx_id(a, key)` is the menu's popup id; `Panel._ctx_label(a)`
calls `imgui.open_popup_on_item_click` on the last item with that id.
`_row` (and so `half`) calls it on the label's dummy, `_fader` on its
label line inside the fader's `push_id`; the popup is still drawn by the
widget's own `_ctx`. Every analyzer meter calls
`_ctx(reg["band.select"], f".{i}")` and `_learn_frame`.
`ui_routing.desk_target(p)` (not `Kind.TEXT`, not `desk.shift`) is the
one rule "Learn desk", ROUTING's desk rows' target combo and the pick's
targets go by, reached as `Panel._desk_target`.

**Differs from §2, and why.**

- *The hook is `_ctx_label` / `_ctx_id`*, shared by `_row` and `_fader`,
  not a direct `open_popup_on_item_click` in `_row`: the label and the
  widget build the id in one place.
- *Meter 0's menu id changed* from `##ctx.band.select` to
  `##ctx.band.select.0`. That also ended a popup id shared with the band
  combo on the same page.
- *A learn armed from a meter frames the meters* (review): each meter
  gets the learn's red frame while `band.select` is armed.
- *WP2 had already written the two "what is offered" rules*; WP3 named
  the desk one (`ui_routing.desk_target`, a three-line edit outside its
  table) so WP4's pick uses it too. What the menu offers did not change.

**Left as the plan has it** (review): the hook is at `_row` / `_fader`,
not `_label_cell`, so a label a page draws on its own (FX "blend",
LOOKBACK's "from" / "spacing" / "net", a macro's number, "scene",
"path") opens nothing. **Found and not fixed** (outside the package):
`ui_lfo._clock_strip`'s two nudge chips both call `panel._ctx(nudge)`
with the bare id in one id scope, so their menu draws its items twice —
the defect this package fixed for the meters. Filed as audit row U9.

**Tests.** `tests/test_ui_shell.py::test_a_rows_label_opens_its_params_menu`
(fed right-clicks over the real `Panel`: the label of a `_row`, of a
`_fader`, of a fader whose row is the session's, and of a `half` label
inside a table cell open exactly `##ctx.<pid>`; the param does not move;
a left click opens nothing),
`::test_every_meter_has_the_band_select_menu`. Unchanged:
`::test_every_page_fits_the_control_window`.

**Demo.** `menu-on-label.png` (`tools/label_menu_shot.py`: a hidden
window; imgui is fed a mouse position on the word ZOOM and a right
button down and up; the red cross marks the fed click).

**Not verified.** A real mouse or a trackpad's two-finger click on a
label or a meter.

### WP5 — A ROUTING filter (PR #91, merged db7d861)

**Built.** `ui_routing.py`: the field `##rows` (hint "filter",
`FIND_W` = 120 px) on the counts line, left of `+ route`; the state
`_state(panel)["find"]`; `matches(panel, router, text, *hay)`,
`route_hay`, `control_hay`, `macro_hay`, `found(panel, router) ->
(shown, total)`, `_shown`, `_find_field`, `NO_MATCH`. While the field
holds text only the lines that say every typed word are drawn, in every
section, each under the index it has unfiltered; the counts read "N of M
rows" in red and a × chip clears it; a section with nothing to show says
"no row matches".

**Differs from §2, and why.**

- *A line in use is held* (review). A filtered line a widget is in use
  on stays drawn until the widget is let go (`_shown`: last frame's
  lines are kept while any item is active or a popup is open, the field
  itself excepted). Without it a macro found by its label vanished at
  the first backspace in that label.
- *"M rows" counts every line of the page* — routes, desk rows, dark
  controls, the eight macros, the session's rows (176 over TRIP) — not
  the routes alone.
- *The unfiltered counts give way to the field*: the longest wording
  that fits beside it ("21 routes · 6 lanes · live", else "21 routes ·
  6 lanes", else "21 routes"), the whole on hover.
- *A dark line matches on its glyph, Akai's name and source only*; its
  factory row's target is not the preset's. Nor do the words "unmapped"
  and "dark", or a line's op text, match.
- *The session section* prints one "no row matches" and drops a
  sub-title with no matching row.
- *A filter of spaces alone is no filter*, and with the field empty no
  haystack is built.
- *The clear waits for the field to lose focus* (WP4, `st["unfind"]`): a
  field that has the keyboard writes its edit buffer back on the frame
  it lets go, so `goto`'s clear holds until it has.

**Left as the plan has it, for the owner to know** (review; register
row 63):

- **A row added while a filter is set can be hidden by it.** `+ route`,
  "Route a lane here…", a Learn and an Unbind's undo all add rows a set
  filter may not show; the red count is the only sign.
- **"lfo 1" also matches LFO 2's routes**: the haystack holds the raw
  source, and LFO 2's is `lfo:1`. Any digit or one-letter word matches
  widely.
- `matches` takes `panel` and `router` and reads neither (the plan's
  signature).

**Tests.** `tests/test_ui_routing.py::test_the_filter_matches_glyph_param_and_source`,
`::test_a_filtered_page_draws_only_matching_lines_and_keeps_its_ids`,
`::test_the_filter_is_ui_state` (amended by WP4: it calls `goto`),
`::test_typing_in_the_filter_is_imguis_keyboard_not_the_apps`,
`::test_a_line_in_use_is_not_filtered_away_under_the_hand`.

**Demo.** `routing-filter.png` (`tools/routing_filter_shot.py`: a hidden
window; ROUTING over TRIP unfiltered and with "kaleido" — "4 of 176
rows" in red; the text was put in the state by the script).

**Not verified.** Typing in the real window: the caret, backspace, Esc
(imgui reverts an edit on Esc) and ⌘Z with the field focused. The hold
with a real drag, a real label edit or an open target combo (the test
patches `is_any_item_active`).

### WP4 — The desk, big and clickable (PR #102, merged a0a0661)

**Built.** `ui_desk.py`: `room(display, panel_x, sheet)` and the
constants `MIN_W` 300, `MIN_H` 120, `LABEL_UNIT` 44, `LABEL_UNIT_H` 32,
`LABEL_PX` (11, 18), `LABEL_LINES` 2, `PICK_S` 20, `PICK_MOVE` 12;
`text(reg, b)`, `wrap(text, width, lines)`, `label_px`; `click(panel,
table, c, b)`, `mappable(table, c)`, `picked`, `picking`, `armed`,
`tick`, `let_go`, `left`, `first_sight`, `pick_line`, `footer_line`,
`rect`; the header's one chip (`big` / `panel`, `ui.panel`).
`learn.py`: `Learn.control`, `Learn.pick`, `Learn.map_picked`, and
`learn.blocked(table, source)`. `ui.py`: `Panel._draw` records
`_panel_x`, runs `ui_desk.tick` and draws the open page inside
`begin_disabled` while a mappable control is picked (never ROUTING);
`_ctx_pick`; `_frame_item`; the footer's picked line; `_sheet_w`.
`ui_routing.py`: `goto(panel, source)`, `_pick_row`, `is_line_of`,
`_mark_line`.

The desk as it is drawn with the panel hidden at 960 × 900, TRIP loaded
(`desk-big.png`; names in parentheses are grey — invariant; `·` is a
dark control; a button's glyph is in its top-left corner):

```
 APC40 · PRESET LAYER · TRIP                                                            [ panel ]

      1       2        3       4        5       6       7        8         9
 G1 (TUMBLE)(FACES) (FIELD) (WAKE)  ▓(TRIP)▓ (ACID) (MANDALA)(NOITA)    Points      K1        K2       K3        K4
 G2    ·       ·        ·       ·        ·       ·       ·        ·      ▓Lines▓     (◔)       (◔)      (◔)       (◔)
 G3    ·       ·        ·       ·     ▓STILL▓  ORBIT    WAVE    RIPPLE   ▓Faces▓   Brightness  Speed  Instances Pattern mix
 G4  5-cell 3,3-duo… Cubic   Tesser- Rectified 4,8-duo… 6,6-duo… 16-cell ▓Rotate▓     K5        K6       K7        K8
                     pyramid  act     5-cell                                          (◔)       (◔)      (◔)       (◔)
 G5 10,10-… Icosah…  ▓24-   Truncat… 12,12-… Dodecah… 20,20-…  120-cell  Reset     Grid amp  Grid rate Bitmap    Zoom
             prism    cell▓  tesseract        prism                       view                          alpha

 G6 (────────────── Save as a new preset ──────────────────────────)   (Reset all)  B1 ▓(Click-  B2 ·   B3 ·    B4 ·
                                                                                        through)▓
 G7 ▓(SUB)▓ (BASS)  (MIDB)   (MID)   (UPR)    (AIR)      ·        ·     (Overlay)        B16 Brightne… +3     B20 (Tap tempo)
                                                                                    B19 (Band −1)  B18 (Band +1)  B21 (Nudge −1) B22 (Nudge +1)
 G8  ▓ZW▓    ▓XW▓     YW      XY       XZ      ▓YZ▓      ·        ·      C (◔)           B17 Brightne… −3     ⇧  (Shift)
 G9  (SUB    (BASS   (MIDB    (MID    (UPR     (AIR      ·        ·      Shape
     Transfer)Transfer)Transfer)Transfer)Transfer)Transfer)                           D1        D2       D3        D4
 G10 (SUB    (BASS   (MIDB    (MID    (UPR     (AIR      ·        ·                   (◔)       (◔)      (◔)       (◔)
      reset)  reset)  reset)   reset)  reset)   reset)                              FX mix   Plasma   Kaleido-  Kaleido-
                                                                                              level    scope     scope
     S1      S2       S3      S4       S5      S6       S7       S8       SM                           segments  zoom
      │       │        │       │        │       │        │        █        │          D5        D6       D7        D8
      │       │        │       │        │       │        █        │        █          (◔)       (◔)      (◔)       (◔)
      █       █        █       █        █       █        │        │        │       Zoom burst Zoom burst Hue cycle Hue cycle
      │       │        │       │        │       │        │        │        │        amount     glow      paint     spread
    (SUB    (BASS    (MIDB    (MID    (UPR     (AIR   (Dynamics)(Input   (Audio    B5 (audio.   B6 (Control  B7 ·   B8 ·
     Post-   Post-    Post-    Post-   Post-    Post-            trim)    drive)       restart)     panel)
     drive)  drive)   drive)   drive)  drive)   drive)                             B9 (Cheat   B10 (Next   B11 ▓(Home)▓ B12 (LFO
                                                                                       sheet)      preset)               trigger)
                                                                                   B13 (audio.play) B14 (audio.stop) B15 (Mic)
                                                                                   X (Master dim) ├───────────────────────█┤
```

`▓ … ▓` is a lit LED (the clip grid in its row's colour, any other
button red). The knobs are two rows of four with the name under each
ring; the faders run along the bottom with the name at the foot; the
crossfader is bottom right with its name beside its glyph.

**Differs from §2, and why.**

- **A pick lets go by itself after 20 s, and says so** (`PICK_S`,
  `ui_desk.tick`, run every frame, desk shown or not): "D3 let go — no
  click for 20 s". Required by the orchestrator beyond the plan, so a
  dimmed page is never left standing at a party. The desk's header and
  the footer count the seconds down ("D3 picked (20 s): click a param to
  put it here"), **the footer's line is clickable to let go**
  (`ui_desk.LET_GO_TIP`, on the line where it fits and on the hover),
  and a click anywhere in the control window — left or right — starts
  the count again. An armed *learn* still never times out (§3).
- **No click maps until the mouse has moved `PICK_MOVE` (12 px) from the
  click that picked** (`ui_desk.armed`; review). On the big desk that
  click brings the panel back under the mouse, and a second click at the
  same spot — a double click, or "click it again to let go" — would have
  landed on whatever widget was now under it. The page is dimmed
  meanwhile, so that click does nothing at all. Added by the build.
- *`learn.blocked(table, source)` is new* (review): the one rule
  `Learn.learn_control` refuses by and `ui_desk.mappable` asks before
  the click. The two sentences differ on purpose ("to map" before the
  click, "to learn" in the refusal).
- *`Learn.arm` gained one line* (`self.control = None` when a param is
  armed): "arming a param lets the pick go" cannot hold without it.
- *A `map_picked` that does not land keeps the pick and leaves no learn
  armed.* `learn_control` leaves a refused learn armed (fork 6); behind
  a pick that would be a learn nobody asked for. On a param the registry
  lacks it says "…: no such param — nothing mapped" (review).
- *Labels need height too*: `LABEL_UNIT_H` (32 px). A short, wide desk
  drew inverted faders; it now draws glyphs only (review; tested at
  1600 × 420).
- *The label's type*: `clamp(0.2 × unit, 11, 18)` px as planned (13 px
  at 960 × 900), plus one rule the plan lacks — **a label that would be
  cut at that size is drawn at 11 px**, where a low button holds two
  lines. A step keeps its amount when cut ("Brightne… +3").
- *The glyph sits in the cell's top-left corner on every control at the
  labelled size*, dark ones too (the plan had a dark control "as today",
  centred).
- *A row's label is a target while picked*, like its widget (review).
- *ROUTING says something else while picked*: it is never dimmed, so the
  header reads "D3 picked: its line is framed · on any other page, click
  a param to put it there · click D3 again to let go" and the footer
  "D3 picked (20 s): click a param on any other page" (review).
- *ROUTING has no pick line in its head.* The plan had the learn line
  say "K6 · unmapped on the global layer"; that would add a line to the
  page. The desk's header and the footer say it ("K6 (track knob 6) is
  on the global layer … : unmapped on the global layer").
- *The footer's line for a pick made before another line was said*:
  whatever the slot held when the footer first saw the pick gives way
  to it (`ui_desk.first_sight`); a line said after it shows first for
  its 4 s, as for a learn. The let-go click fires only on the pick's own
  line.
- *The hover names what a click would do* ("click: pick it — then click
  a param to put it there", "click: let go", "click: learn view.depth4
  here").
- *The tooltip on a target* reads "click: put D3 on Speed".
- *`room` returns whole pixels*; at 960 × 900 the desk is 384 × 431
  beside the panel (it was 380 × 290) and 936 × 876 with it hidden.
- *`Panel._footer` and `_draw_cheatsheet` were edited* (the picked line;
  `_sheet_w`, so the desk can sit beside the sheet), and
  `ui_routing.desk()`'s hint and `_find_field` (WP2's and WP5's lines):
  the hint now takes the longest wording that fits ("new: Learn desk, or
  click a control" at the control size, the whole on hover), the field
  holds `goto`'s clear until it has lost the keyboard.
- *The drawing in §2 is of an idealised device.* `apc40.LAYOUT` (not
  edited) puts the knobs in two rows of four and the buttons 0.7–0.75
  units tall, which is why those labels are one line or small. The
  drawing above is what is built.

**What the pictures show, judged by the agent that made them.** All 105
labels are drawn at 960 × 900 and nothing overlaps. Five are still cut
with an ellipsis ("10,10-duopr…", "12,12-duopri…", "20,20-duop…", and ▲
▼ as "Brightne… +3 / −3"); about a dozen are at 11 px (the duoprisms,
the two Kaleidoscope knobs, Click-through, Control panel,
audio.restart), which is small for a step back; `audio.play`,
`audio.stop` and `audio.restart` show their ids (fork 8). The dimming of
a picked page is imgui's disabled alpha (0.6): visible beside the rail,
not dramatic.

**Tests.** `tests/test_ui_desk.py::test_the_desk_takes_the_room_it_has`,
`::test_the_big_desk_labels_every_lit_control_and_never_scrolls`,
`::test_the_small_desk_draws_glyphs_only`, `::test_a_controls_text`,
`::test_a_click_picks_and_a_second_click_lets_go` (the function, then
fed mouse events on the drawn desk: another control, the ground, a right
click, a dark control),
`::test_a_click_completes_an_armed_desk_learn`,
`::test_a_pick_lets_go_by_itself`,
`::test_the_diagram_draws_on_both_layers_and_hides` (amended: the one
widget id is `big##desk`);
`tests/test_learn.py::test_pick_then_param_maps_through_the_learn`,
`::test_a_pick_on_an_invariant_control_or_the_global_layer_maps_nothing`;
`tests/test_ui_shell.py::test_a_picked_control_dims_every_page_but_routing`,
`::test_a_click_on_a_param_maps_the_picked_control` (fed events: a desk
click, then a click on Speed's fader on the dimmed page — mapped, the
fader did not move; a label; a combo and a check; a file path is no
target; the big desk's pick click and two more at the same spot map and
move nothing),
`::test_the_footer_says_what_is_picked_and_a_click_lets_go`,
`::test_the_click_wording_is_switched_on`;
`tests/test_ui_routing.py::test_goto_scrolls_the_rows_child_to_the_controls_line`,
`::test_a_desk_click_clears_a_filter_that_has_the_keyboard`.

**Demo.** `desk-big.png`, `desk-big-global.png`, `desk-picked.png`,
`routing-goto.png` and `desk-map.txt` (`tools/desk_shots.py`, and
`tools/desk_shots.py map`: a hidden 960 × 900 window, the real Panel on
a temp home, TRIP loaded; every click an imgui mouse event fed at the
rect the control or widget was drawn at; the timeout's clock moved
forward, not waited for).

**Not verified.** A real mouse or trackpad anywhere: hover on a disabled
item was confirmed in headless imgui and a hidden GL window only. An
APC40's rings and LEDs following a click-made row. Readability from a
step back: the pictures are 2× read-backs looked at up close, and 13 px
and 11 px may be too small at two paces. A maximised control window with
the panel open (labels beside the panel), and the cheat sheet on with
the panel hidden (the desk beside the sheet): `room`'s arithmetic only,
no render looked at. A hot reload of `ui_desk.py` or `learn.py` with a
pick standing. Measured in the hidden window, the desk window costs
0.36 ms a frame small and 0.80 ms big.

### WP6 — Docs and hand checks

This section; the "*As built:*" notes in §2–§4; `ARCHITECTURE.md` (§1's
adapters and panel rows, §2's frame, §3.5, §3.7, §3.8, §3.10, §4's rows for
`midi.py`, `hands/`, `learn.py` and the panel); `ENGINEERING.md` (§5,
where the panel's conventions are — the plan's "§7" is that document's
Process section — §6's counts, §8); `DECISIONS.md` and
`DECISION-REGISTER.md` rows 57–64; `11-hand-checks.md` group M as checks
64–71, with the notes on checks 19, 37, 45 and 51; `plans/README.md`,
`CHECKPOINT.md`, the roadmap's pointer; audit row U9. No code.

**Code comments this plan left stale** (code, so not edited here):
`midi.py`'s module docstring ("Right-click → Learn on any panel control,
then a knob or button … (`_learned` …) … a learn on an invariant control
… is refused with the reason": the item is "Learn desk", the row-making
is `Learn.learn_control`, and an invariant control is no candidate at
all); `ui_routing.py`'s module docstring ("New desk rows come from Learn
(right-click a control, then move a knob or button — midi.py's
`_learned`)"); `hands/core.py`'s module docstring (Learn "writes a
`position` route": stale since plan 18) and `HandsIO.poll`'s (a learn's
`learning`, `learn_source`: it also asks `accepts`, `want`, `armed_n`);
`Panel._ctx_learn`'s docstring names `ui_routing._desk_targets` where
the rule is now `ui_routing.desk_target`; "right-click → Learn" in the
docstrings of `app.py`, `ui_lfo.py` and `hands/panel.py` names an item
that is now two.

## 8. Appendix — group M for `11-hand-checks.md`

WP6 pastes this in after plan 16's group L, with final numbers in place
of M1–M8. The text is final except for numbers and PR numbers.

*As built:* M1–M8 are checks 64–71 of
[`11-hand-checks.md`](11-hand-checks.md), and the text there is the one
to run: it was made true to the code (the pick's 20 s and its footer
line, the refusals' wording, what a hand learn lands with since plan
18). The text below is the plan's, kept as written.

### M. Plan 17 — Learn, Unbind and seeing the desk — added 2026-10-04

Run on `finish-line` once plan 17 is merged into it. M1, M5, M6 and M8
run on the laptop alone; M2, M4 and M7 need the APC40; M3 and M4 need
the camera and the box. About 30 minutes. Run the headless tests named
first. Use a copy of the home: `cp -R ~/Hyperspace ~/Hyperspace-before-17`.

**M1. One Unbind, with or without the desk (plan 17 WP1).**
Headless: `uv run pytest -q tests/test_learn.py::test_unbind_removes_the_presets_desk_rows_and_every_route tests/test_ui_shell.py::test_the_menu_lists_and_unbinds_with_no_midi_adapter`.
APC40 unplugged, `[midi] enabled = true`. F1 (TUMBLE). VIEW page,
right-click Speed. *Pass:* the menu lists "K2 (track knob 2)" and the
right hand's height route by name, and has one "Unbind ▸" with desk,
route and both. Choose both: the lines are gone on the next right-click,
the preset's dot is lit, the footer says "unbound view.speed from …".
⌘Z: both are back. Right-click Brightness (a knob and two step buttons,
no route): a plain "Unbind", no submenu. Now set `[midi] enabled =
false`, relaunch, and do it again: the same menus. AUDIO page,
right-click the drive fader (the MASTER fader's param): the line reads
"SM (MASTER fader) · invariant" and there is no Unbind. *Fail:* no desk line with MIDI off →
`Panel._ctx` still reads `self.midi`; an Unbind that refuses →
`Learn.unbind`'s offer rule in `_ctx`; ⌘Z brings back half →
`Learn.unbind` pushed twice or after the change.

**M2. A desk learn listens only to the desk, and SHIFT works through it
(plan 17 WP2, fork 6).**
Headless: `uv run pytest -q tests/test_midi.py::test_an_invariant_control_works_through_a_desk_learn tests/test_hands.py::test_the_hands_never_complete_a_desk_learn tests/test_learn.py::test_learn_refuses_the_global_layer_and_invariant_controls`.
APC40 in, camera on, F1. Right-click 4D depth → Learn desk. Wave both
hands through the box for five seconds. *Pass:* the footer still reads
"learning view.depth4 — turn a knob …" in red; no route appears on
ROUTING. Move S3 a little: the third band's drive moves and the learn is
still armed. Press SHIFT: its LED lights. Turn K2: the footer says K2 is
on the global layer, still armed. Press SHIFT again, turn D5: "learned
view.depth4 ← D5 (device knob 5)", D5's ring lights and follows.
*Fail:* the hands took it → `HandsIO._learn`'s guard (`Learn.accepts`);
the fader ended the learn or SHIFT did not latch → the learning branch
of `MidiIO._handle`; the learn gone after the K2 refusal →
`Learn.learn_control` took before refusing.

**M3. A hand learn listens to one hand (plan 17 WP2 — the session's
"wrong hand").**
Headless: `uv run pytest -q tests/test_hands.py::test_a_hand_learn_listens_to_one_hand tests/test_hands.py::test_a_rearm_starts_a_fresh_baseline`.
Camera and box, calibrated (check 15). F1. Keep the left hand still in
the box. With the right hand on the trackpad, right-click Zoom (CAMERA
page) → Learn hand ▸ left. Now bring the right hand back over the box
and move it about freely for five seconds. *Pass:* nothing is learned;
the footer reads "learning camera.zoom — move the left hand…". Raise
the left hand slowly: "learned camera.zoom ← L height …", and Zoom
follows the left hand only. Repeat with Learn hand ▸ right and the hands
swapped. *Fail:* the right hand took it → the `moved` list in
`HandsIO._learn`, or `Learn.accepts` on the address (`hand:left.` must
be the prefix `HandsIO.address` writes); learned at once on arming → the
baseline's key (`_learn_key`).

**M4. A knob bump during a hand learn does its own job (plan 17 WP2).**
Headless: `uv run pytest -q tests/test_midi.py::test_a_knob_bump_during_a_hand_learn_does_its_own_job`.
APC40 and camera, F5 (TRIP), hands out of the box. Right-click Speed →
Learn hand ▸ right. Turn D1 and press a clip pad of row 4. *Pass:* the
FX mix moves with D1 and the shape changes; the footer still reads
"learning view.speed — move the right hand…"; ROUTING's desk has no new
line. Click the footer's line: the learn is cancelled. *Fail:* D1 now
drives Speed → `MidiIO._handle` did not ask `accepts`.

**M5. The menu opens from the label and from every meter (plan 17 WP3).**
Headless: `uv run pytest -q tests/test_ui_shell.py::test_a_rows_label_opens_its_params_menu tests/test_ui_shell.py::test_every_meter_has_the_band_select_menu`.
Laptop alone. CAMERA page: right-click the word ZOOM. VIEW page:
right-click the word BRIGHTNESS above its fader. ANALYZER page:
right-click the fourth meter. BITMAP page: right-click the file's name.
*Pass:* the first three open that param's menu; the file's name offers
no Learn. *Fail:* nothing opens on a label → `Panel._row` / `_fader`
(`open_popup_on_item_click` and `_ctx` must build the same id inside the
same id scope).

**M6. The desk from a step back (plan 17 WP4, fork 1).**
Headless: `uv run pytest -q tests/test_ui_desk.py::test_the_desk_takes_the_room_it_has tests/test_ui_desk.py::test_the_big_desk_labels_every_lit_control_and_never_scrolls`.
F5 (TRIP). Press H (or DEVICE ON/OFF on the APC40, or the desk's "big"
chip). *Pass:* the panel goes and the desk fills the control window;
every lit control carries a name; the bank row reads TUMBLE … NOITA with
TRIP lit; the device knobs read FX mix, Plasma level, Kaleidoscope …;
the faders' names are grey. Step back two paces: the knob and pad names
can be read. Press SHIFT on the desk: the header turns red, the K and D
knobs change names, the preset's pads go dark. Maximise the control
window and press H: the panel is back and the desk beside it still has
its names. Hold the APC40 beside the screen: each control is where the
drawing says (check 45's test, at this size). *Fail:* names cut to
nothing → `ui_desk.wrap` / the type size rule; the desk under the panel
→ `Panel._panel_x` not recorded (`Panel._draw`) or `ui_desk.room`; not
readable at two paces at 960 × 900 → say so: the fix is the launch size
of the control window (plan 16's placement), not this plan.

**M7. Click a control; click a param (plan 17 WP4, forks 2 and 3).**
Headless: `uv run pytest -q tests/test_ui_desk.py::test_a_click_picks_and_a_second_click_lets_go tests/test_learn.py::test_pick_then_param_maps_through_the_learn tests/test_ui_routing.py::test_goto_scrolls_the_rows_child_to_the_controls_line`.
APC40 in, F1, ROUTING page open. Click D6 on the desk. *Pass:* D6 is
framed red; the rows scroll to "D6 · unmapped — dark" (or its row),
framed; the footer says "D6 picked: click a param …". Open VIEW: the
page is dimmed; the widget under the mouse is framed. Click Speed:
"learned view.speed ← D6 (device knob 6); K2 let go"; the page is bright
again; D6's ring on the device lights and turning it moves Speed; K2 is
dark. ⌘Z: D6 is dark again and K2 has Speed. Click S2 on the desk: the
line says it is invariant and VIEW is not dimmed. Latch SHIFT, click K1:
"on the global layer", not dimmed. With SHIFT off: right-click
Brightness → Learn desk, then click D7 on the desk instead of turning
it: learned, and K1, which had Brightness, goes dark; the footer names
it. Pull the APC40's cable and map D8 the same way: it works. *Fail:* the click on Speed moved the
slider → the disabled wrap in `Panel._draw`; nothing maps →
`Panel._ctx`'s pick click (`allow_when_disabled`); ROUTING's whole page
scrolled → `set_scroll_here_y` called outside the `##routes` child; a
map landed under SHIFT → `Learn.learn_control`'s layer test.

**M8. The ROUTING filter (plan 17 WP5).**
Headless: `uv run pytest -q tests/test_ui_routing.py::test_the_filter_matches_glyph_param_and_source tests/test_ui_routing.py::test_a_filtered_page_draws_only_matching_lines_and_keeps_its_ids`.
F7 (MANDALA), ROUTING page. Type `kaleido` in the filter. *Pass:* only
the routes and desk lines on the kaleidoscope remain; the count reads
"n of m rows" in red. Type `d3`: one desk line. Type a hand axis as a
route's first column prints it (`r roll`): that hand's route. Press F5:
the filter is still there, now over TRIP's rows. Click its ×: every row is back. With a filter typed, click
a control on the desk: the filter clears and the rows scroll to it.
*Fail:* a row deleted with × was not the one shown → the row's index
(`_row`'s `k` must be its place in the unfiltered list); the page
scrolls → the field added a line (`ui_routing.page`).
