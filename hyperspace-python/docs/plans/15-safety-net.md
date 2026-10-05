# Plan 15 — Safety net and the bank: undo, home, master dim, save-as on the desk

**From the Oct 3–4 session at the machine** (Dan and Dillon;
[`15-21-roadmap.md`](15-21-roadmap.md) §4, decisions 26–29 in
`docs/DECISION-REGISTER.md` Part A4, all answered 2026-10-04). Undo was
called "absolutely the most important thing": it is what makes a mistake
recoverable and a good preset findable. This plan builds it down to single
edits, a trash for preset files, one press back to a known-good look, a
master dim on the crossfader, and a save-as on the desk that never
overwrites.

Written 2026-10-04 against `plan-15-integration` at 61d037b, by reading
the code; no code was changed. Every row of §1 cites the function as it
stands on that commit. Three things were measured headless on a temp home
(the scripts are not kept): the registry's size and the cost of the
fingerprint, what a performer taking a parameter does to its base, and
which key rows fire on a two-modifier chord. Nobody was available to
answer questions, so every fork met is written up in §7 with the option
taken; the ones the owner can see go into the decision register as rows
after 33 (WP5).

## 1. What the owner hit, and what it is

| # | The session asked for | What the code does today | So |
|---|---|---|---|
| 1 | Undo, down to one slider ("how good presets get found") | There is one undo in the app: `Control._reset_all` / `_undo_reset_all` (`control.py`), 8 seconds, for "Reset all" on the band strips only. A parameter write fires no event (`Param.set`, `params.py`), and the ROUTING page edits rows in place (`ui_routing._row`, `desk`, `macros`). | WP1: a watcher that compares a fingerprint once a frame; no write hook. |
| 2 | The roadmap: "a performer writes an offset, never the base, so a hand moving makes no step" | True of the *writes* (`Router.modulate` → `Param.modulate`; `Param.set` writes `_base` while modulated). **Not true of what `p.base` reads.** `Param.modulate` adopts `_norm_of(get())` as `_base`, and `base` then returns `_value_of_norm(_base)`: the round trip moves the last bits. Measured: 29 of 455 watched params change (`view.speed` 0.3 → 0.29999999999859905, `camera.zoom` 1.3 → 1.3000000000000003, `dream.fade`, most log-range `fx.*`), and they stay changed after the performer lets go (`Param.apply` writes the round-tripped base back). | WP1's fingerprint compares floats within a tolerance. (The same round-off lights the loaded preset's dirty dot the first time a hand takes such a param — `Presets.signature` compares exactly. Found, not fixed here: a paper cut for plan 16.) |
| 3 | The roadmap: "rotation angles, clocks, anything `ViewState.integrate` writes" are left out | `ViewState.integrate` (`view.py`) writes only `ang`, the six `rot.phase.*` params, which are `persist=False` (`build_registry`). The clock's `tempo.bpm` and `tempo.nudge` (`tempo.register`) **are** persisted session params, and `Clock.tap` rewrites `bpm` on every tap of a burst. | The watched set is "persisted, not an alias, not a trigger, not the `tempo` group"; §2 WP1 lists what that leaves out. |
| 4 | The roadmap: "band add / remove / move keeps the existing 8-second undo" | Those three have no undo. `Control.add_band`, `remove_band` and `move_band` each *clear* the reset undo (`clear_undo`); only `reset_all_clicked` arms it. A layout change also re-declares every `band.*` param (`build_bands`, the `on_layout` hook) and `move_band` shifts values between the same ids. | Not folded in. A stored `band.*` value is put back only onto the band layout it was made on; a load that brings its own layout puts the layout back first (WP1, fork 4). Everything else in the stack is untouched by a layout change. |
| 5 | Ctrl+Z / Ctrl+Shift+Z "as key rows" | `routing.MODIFIERS = ("SHIFT", "SUPER")`: there is no Control modifier, and `app.Keys` has only `shift()` and `super()`. And `Router.keys` fires a modified row when its modifiers are a **subset** of those held (`mods <= held`): rows `key:SUPER+Z` and `key:SHIFT+SUPER+Z` would both fire on ⌘⇧Z (checked). No factory row has two modifiers today, so nothing shows it. | WP1 adds the modifier and makes a chord fire only its own row (fork 1). |
| 6 | A preset load "from any road" is one undo step | Every road meets in one function: F-keys, the clip row, QUANT, the pad's B, the strip's list and arrows, the startup preset, and the file watch all reach `Presets.load_doc` (`preset.py`) through `Library._apply_doc` (`library.py`). A show load (`Project.load`) also replaces the `Project` object's own fields (name, path, bank, startup), and a load of either kind changes what the library calls current (`Library._landed`). Neither is a param or a table row. | One push site for presets. An action step that loads also carries "what was loaded" (`Library.landed` / `reland`, which exist for exactly this), so Save after an undo cannot write the old look over the wrong file. |
| 7 | "A preset file about to be overwritten or deleted goes to the trash" | Two places do it: `Library.save_as` writes `<home>/<group>/<slug>.json` without looking (every strip save and as…, `overwrite`, `Presets.save_as`, ⇧F through `Project.save_slot`), and `Library.delete` unlinks (the list's ×). The migrations that rewrite preset files keep their own backups (`preset.migrate_echo_home` through `routing.backup`); `preset.put_preset` never overwrites. A folder named `trash` in the home would be listed as a module group by `Library.groups()`. | WP1: one helper, two calls, and `trash` named as no group. |
| 8 | One status line naming what was undone | No message line is visible on every page. `Library.status` and `warning` are drawn only on the PRESETS page (`ui_presets.notes`); an empty F-key's "an empty slot" is seen only there. The footer (`Panel._footer`, `ui.py`) holds the frame rate, the reloader's status and the show's name. | WP1 gives the footer one message slot. |
| 9 | Home: back to a known-good look | `Project.startup` and `load_startup` exist (`library.py`, D11); nothing fires them after launch. OVERDUB (`apc40.N_OVERDUB`, note 0x40, glyph B11) has no row in `apc40.DEFAULT_MAP`. A MacBook has no Home key; fn+← sends it. | WP2. |
| 10 | Dim the whole picture from the desk | The crossfader's row is `_cc("overlay.bg", CC_XFADE, 0, ring=0)` (`apc40.DEFAULT_MAP`), invariant, onto an alias of `output.bg` (`Output.register`, `overlay.py`), which does nothing unless `[output] overlay = true` (`Output.bg_alpha`). `Renderer._draw_frame` (`render.py`) ends with `self.ghost.draw(target, vp, t, opaque=fx.opaque)`; nothing multiplies the finished frame. | WP3. |
| 11 | The roadmap: "WP3 touches nothing the others do" | False. `apc40.py`, `routing.py` and the generated `bindings.default.json` are also WP1's, WP2's and WP4's; the output's state reaches the renderer through one line of `app.frame` (`h.renderer.bg_alpha = h.output.bg_alpha`), and `app.py` is WP1's; the OUTPUT page is in `ui.py`. | §2 says who owns which lines and the merge order. |
| 12 | Save from the desk by holding a button | `MidiIO._handle` (`midi.py`) keeps no press time. `_held` maps a note to the rows its press went to (D12) and nothing else; the adapter's `clock` argument is passed to `Ports` and not kept. A trigger row's LED is its press echo (`routing.led_lit`). No code sends a blink velocity (`apc40.GREEN_BLINK` and its kin are "unused today", the module says). The eight clip-stop notes (`N_CLIPSTOP`, 0x34 on channels 0–7, glyphs G6·1–G6·8) have no rows. | WP4: a `hold` op, a clock on the adapter, a blink. |
| 13 | "Next empty slot reads the bank's size from one place" | Two constants say eight: `library.SLOTS` (the bank list) and `routing.BANK_SLOTS` (the F-key rows). The params loop already reads `len(bank.bank)` (`build_registry`). | WP4 reads `len(project.bank)` and neither constant. |
| 14 | Names like "TRIP 2", "TRIP 3" | The migration already names that way (`preset.put_preset`: "the next free `<name> 2`, `3`"), and it knows the trap: the library keys files by slug (`Library._files`), so a user file whose slug is another preset's file hides that preset. ⇧F on an empty slot uses a different style, `PRESET 3 (2)` (`Project._fresh_name`). | WP4's naming checks file stems as well as names; `_fresh_name` is left alone. |
| 15 | The roadmap puts the hand checks in "group I" | Groups I (plan 14) and J (ghost hands, check 47) exist in `11-hand-checks.md`. | Plan 15's group is **K**, checks 48–57 (§9). |
| 16 | The crossfader "survives a preset load" | `MidiIO.redraw(load=True)` (`midi.py`) clears the catch of every fader on every desk replacement, whether or not the load moved the fader's param; `_uncatch_moved` already re-arms the ones that did move. A fader is then caught again only if its next message is within `PICKUP_TOL` of the value or crosses it. | WP3 narrows the clear to faders whose param moved (fork 19). |
| 17 | The roadmap lists "an FX reorder" among the actions that push | An effect's place in the stack is the param `fx.<name>.order`, edited with a slider (`ui_fx.page`). It is an ordinary base edit; the watcher sees it. | No push site today. Plan 20's drag-to-reorder calls `undo.push`. |

## 2. Work packages

Merge order onto `plan-15-integration`: **WP3, WP1, WP2, WP4, WP5**. WP1
and WP3 are built at once; WP3 is small and merges first, and WP1 rebases
onto it before its PR merges. WP2 stacks on WP1. WP4 stacks on WP2 (not
beside it: both edit the same six files). Each is one PR and one merge
commit (decision 30).

| WP | What | Size | Needs |
|---|---|---|---|
| 1 | **Undo and the trash** | M–L | — |
| 2 | **Home** | S | WP1 |
| 3 | **Master dim on the crossfader** | S | — |
| 4 | **Save-as on the desk; "put preset here…" and "clear slot"** | S–M | WP2 |
| 5 | **Docs and hand checks** | S | last |

**Shared files, and who edits what.** A package may edit only its lines.

| File | WP3 | WP1 | WP2 | WP4 |
|---|---|---|---|---|
| `apc40.py` | the crossfader's row and its comment | — | the OVERDUB row | the eight clip-stop rows, `blink_of`, the module docstring's invariant list and its "unused today" comment |
| `routing.py` | one `APC_REMAP` entry; the remap's note names its plan | `MODIFIERS`, `Router.keys`, `LOOP_KEY_ROWS` (undo, redo), `Bindings.set_desk(load=)`, `Router.sync_macros` | `LOOP_KEY_ROWS` (Home), one `APC_NEW_ROWS` entry | `OPS` (`hold`), eight `APC_NEW_ROWS` entries |
| `bindings.default.json` | regenerated (`python -m hyperspace.routing`) | regenerated | regenerated | regenerated |
| `app.py` | one line in `frame`, beside `bg_alpha` | `Host.undo`, the tick in `frame`, construction in `main`, `Keys.control`, the reload target | — | — |
| `params.py` | — | `edit.undo`, `edit.redo` | `preset.home` | `preset.save_new` |
| `library.py` | — | the trash, the pushes, `Project.mark` / `remark`, `Marks` | `Project.home` | `next_name`, `Project.next_empty` / `save_new` / `put_slot` / `clear_slot` |
| `ui.py` | the OUTPUT page's dim row; the footer's dim readout | the footer's message slot; two cheat-sheet rows | one cheat-sheet row | `_ctx(extra=)` |
| `ui_presets.py` | — | — | the "starts on / home" label and tooltip | the slot menu |
| `midi.py` | one rule in `redraw(load=True)` | pushes in `unbind` and `_learned` | — | the hold, the blink, `self.clock` |
| `tests/test_app_boundary.py` | the output stub's `dim` | `ORDER`, the host's `undo` | — | — |

No code package edits `ARCHITECTURE.md`, `DECISIONS.md`, `ENGINEERING.md`,
`DECISION-REGISTER.md`, `plans/README.md`, `11-hand-checks.md` or this
file. Each PR body carries its "as built" paragraph; WP5 folds them in.

### WP1 — Undo and the trash

**What.** Ctrl+Z (and ⌘Z) takes back the last gesture or the last
replacing action; Ctrl+Shift+Z (⌘⇧Z) redoes it. A preset file that a save
or a delete is about to destroy is copied to `<home>/trash/` first.

**Owns.** New `hyperspace/undo.py`, `tests/test_undo.py`. Its lines in the
shared table above. Also: `preset.py` (one push in `Presets.load_doc`),
`learn.py` (pushes in `Learn._place` and `learn_source`), `ui_routing.py`
(four pushes), `hands/panel.py` (one push), `hotreload.py` (`MODULES`),
and the tests that pin what it changes (`test_routing.py`,
`test_app_boundary.py`, `test_ui_shell.py`, `test_hotreload.py`,
`test_library.py`, `test_desk.py`, `test_learn.py`, `test_midi.py`,
`test_ui_routing.py`).

**Must not touch.** `render.py`, `overlay.py`, `ghost.py`, `apc40.py`,
`control.py` (the 8-second reset undo stays as it is), `hands/core.py`,
`hands/signal.py`, `lfo.py`, `tempo.py`, and `Param` / `Registry` in
`params.py` (no write hook; the two triggers in `build_registry` are its
only lines there).

#### Where it sits

`undo.py` is a leaf: it imports the standard library and **nothing from
the package**. The registry and the table arrive as arguments and are used
duck-typed, the rule `lfo.py` and `tempo.py` keep
(`tests/test_lfo_boundary.py`); `test_undo.py` holds `undo.py` to it the
same way. So any module may import it and no boundary test moves:
`routing.py` does not import it (`test_routing_boundary` is untouched),
`library.py`, `preset.py`, `learn.py`, `midi.py`, `ui_routing.py`,
`hands/panel.py` and `params.py` do. It goes in `hotreload.MODULES` before
`params` (after `tapers`), and its instance is a reload target
(`(undo_obj, "undo", "Undo")`).

In the control model it is a **scene-setter**: it writes bases through
`Registry.restore` (which ends in `Param.set`) and replaces table parts
through the table's own calls. It never calls `Param.modulate`
(`test_routing_boundary`'s walk still finds one call site) and never
writes an offset or an object.

#### Contracts

```python
# undo.py
SETTLE_S = 0.4        # quiet time that ends a step. Plan 18's knob slew must stay under it.
LIMIT = 100           # steps kept; the oldest goes first
ABSORB_FRAMES = 2     # frames after a restore whose changes are the restore's own
REL_TOL, ABS_TOL = 1e-9, 1e-12
EXCLUDED_GROUPS = ("tempo",)          # the clock

def watched(p) -> bool:
    """persisted, not an alias, not a trigger, group not in EXCLUDED_GROUPS"""

class Undo:
    def __init__(self, reg, table, *, marks=None, tag=None, tagged=("band.",),
                 on_restore=None): ...
    def tick(self, now: float) -> None      # once a frame
    def push(self, label: str, *, load: bool = False) -> None
    def undo(self) -> bool                  # False: nothing to undo
    def redo(self) -> bool
    def clear(self) -> None
    status: str        # "undid Brightness 1.20× → 0.85×", "redid load TRIP", "nothing to undo"
    said_at: float     # the frame clock when `status` was set

def install(u: Undo | None) -> None        # app.main; kept across a hot reload of this module
def push(label: str, *, load: bool = False) -> None   # the installed one's; nothing installed: a no-op
def undo() -> None
def redo() -> None
```

- `marks` is any object with `take() -> object`, `before(obj) -> None`
  and `put(obj) -> None`: "what is loaded", opaque to `undo.py`.
  `app.main` passes `library.Marks(lib)` (below).
- `tag` is a callable returning something hashable that names the shape
  the `tagged` ids live on. `app.main` passes
  `lambda: tuple(s.name for s in audio.chain.spec)`: the bands' explicit
  names in strip order. It changes on a band add, remove or move and on a
  layout with other names; it does not change when a band is re-tuned
  (centre, Q and curve are params). Not `Analyzer.layout_version`, which
  `_reshape` bumps on every `apply_layout`, a same-shaped one included,
  and not `band_names`, whose label for an unnamed band is its centre
  frequency.
- `on_restore` is called after every restore. `app.main` passes
  `router.sync_macros`.
- `undo.push(label)` is the call roadmap §5 promises every later plan. The
  `load` keyword is new and optional (fork 2).

```python
# library.py
TRASH = "trash"
def to_trash(path: Path, root: Path) -> Path | None
class Marks:                       # what is loaded: names, clean references, layouts
    def __init__(self, lib): ...
    def take(self) -> tuple        # (lib.project.mark(), {group: lib.landed(group)},
                                   #  {group: its `extra` hook's dict})   — the band layout
    def before(self, mark) -> None # a group whose layout differs: its on_layout hook, first
    def put(self, mark) -> None    # the names and references, last
# Project
def mark(self) -> tuple            # name, note, path, factory, stem, session, modules, bank, startup, _saved
def remark(self, mark) -> None

# routing.py
MODIFIERS = ("SHIFT", "SUPER", "CONTROL")
def set_desk(self, rows, *, load: bool = True) -> list[str]     # Bindings
def sync_macros(self) -> None                                   # Router

# params.py, in build_registry, beside app.restart (group "ui", modulatable=False)
"edit.undo"   # fires undo.undo()
"edit.redo"   # fires undo.redo()

# app.py
class Keys:  def control(self) -> bool     # either Control key
Host.undo: object | None = None
```

#### What is watched

Once a frame `tick` builds a fingerprint of two things.

**Bases.** `tuple(p.base for p in reg if watched(p))`, with the ids beside
it. The list is rebuilt every tick, because a band layout change and a
shader reload re-declare params (`build_bands`, `fx.declare`). Measured
headless: 529 params, 455 watched, about 60 µs; for scale, the dirty dot's
`Presets.signature` costs about 420 µs.

Left out, from the code:

| Left out | Why | Where it is declared |
|---|---|---|
| `rot.phase.XY` … `rot.phase.ZW` (6) | the integrated angles: `ViewState.integrate` writes `ang` every frame; `persist=False` | `params.build_registry` |
| `tempo.bpm`, `tempo.nudge` | the clock. Persisted, so left out by group: a tap burst rewrites `bpm` on every tap, and taps at 120 BPM are 0.5 s apart, longer than the settle time (fork 5) | `tempo.register` |
| every trigger (36 on the rig measured) | an action, not a value | `Kind.TRIGGER` |
| `band.select`, the 13 `band.sel.*` aliases | which strip is open, and views onto it | `build_bands` |
| `hands.select`, `hands.sel.return` | which axis is open, and a view onto it | `hands.core.register` |
| `fx.select`, `preset.select`, `desk.shift` | selection and the desk's latch | `fx.declare`, `build_registry`, `routing.register_desk` |
| `ui.panel`, `ui.cheatsheet`, `ui.desk`, `ui.page` | the panel's own state | `Panel._register_panel_params` |
| `audio.mic`, `audio.device`, `audio.play` | transport | `build_registry` |
| `output.monitor`, `output.fullscreen`, `output.overlay`, `output.passthrough`, the five `overlay.*` aliases, and WP3's `output.dim` | rig settings, `persist=False` | `Output.register` |

Not params at all, so never touched: the LFOs' running phases (`lfo.LFO`),
the effects' clocks (`FxState.phase`), the look-back's clock, the
renderer's `now`, the clock's downbeat (`Clock.t0`).

Everything else is watched, session params included: the hands' feel, the
band strips, the master faders, `scene.select`, the ghost hands,
`output.bg` and `output.alpha`. Camera moves are watched too (fork 8).

**The table.** A tuple of every performer row and every preset-layer row
(`source, target, op, value, enabled, scale, when, rest, layer, pickup,
feedback, on, off, ring`) in table order, and of the macros (`id, label,
(base, depth, from, to)` per subscriber). The fields are read, not a
serial, because the ROUTING page edits rows in place. Measured: about
40 µs on the factory table (195 rows). The session's rows (keys, pad,
invariant and global MIDI rows) are not watched: they are `bindings.json`'s.

**What a performer looks like to it.** While a row holds a param, `p.base`
reads `_base`, which only a setter moves, so a hand, a band or an LFO
moving changes nothing in the fingerprint. The frame a performer takes a
param, and the frame it lets go, the base can move by round-off (§1 row
2). So two fingerprints are **the same** when they are equal, or when
their ids are equal and every float pair is within `REL_TOL` /
`ABS_TOL` (`math.isclose`); the slow comparison runs only on frames where
the tuples differ, and the new tuple is then kept so the fast path
resumes. A direct object write under a performer (`camera.reset`, the
band reset's undo) is folded into `_base` by `Param.apply` one frame
later; it is a real change and is seen then.

#### The frame

`h.undo.tick(now)` runs in `app.frame` **right after
`router.follow_macros()` and before `hands_io.poll`**, in its own guarded
block (a raise records `undo: …` on `reloader.runtime_error`, like the
blocks beside it). By then this frame's keys, pad, MIDI and macro
follow-ups have written their bases; the panel's edits are the previous
frame's tail and are seen one frame late, which costs nothing. The frame
order in ARCHITECTURE §2 and `test_app_boundary.ORDER` gain `undo.tick`
after `router.follow_macros`.

`app.main` builds the `Undo` **after** `library.project.load_startup()`,
so a launch starts with an empty stack.

#### Steps

A **state** is the watched bases by id, copies of the performer rows and
the preset-layer rows (`dataclasses.replace`), `table.macros_doc()`, and
`tag()` as it read when the state was taken. `settled` is the state as of
the last quiet frame.

A **step** is `(label, before, load, action)`; it sits on the undo stack
from the moment it opens, so Ctrl+Z works at once.

`tick(now)`:

1. If the watched **ids** or `tag()` changed (a band added, removed or
   moved; a shader reloaded into another shape): close any open step, take
   the state and fingerprint as they are now, and stop. No step is opened:
   a band add, remove or move is not undone (fork 4).
2. If a restore's absorb count is running: count down; if the fingerprint
   moved, take the state as it is now. Stop.
3. If the fingerprint is not the same as last frame's: note the time. If
   no step is open, open a **gesture** step with `before = settled` and no
   label, and clear the redo stack. If one is open (a gesture or an
   action), it goes on collecting.
4. If it is the same and a step is open and `SETTLE_S` has passed since
   the last change: close it. `settled` becomes the state now; a gesture
   gets its label from the difference (below); a step whose `before` is
   the same as `settled` (tag included) is taken off the stack.

`push(label, load=False)`, called **before** a replacing action changes
anything:

1. If an **action** step was opened earlier in this same frame (no `tick`
   since), return: it is the same action from the inside (a show load
   that loads its startup preset; Replace that lands a learn). The outer
   label stands.
2. Bring the watcher up to date as of now: an edit this frame's `tick` has
   not seen yet opens a gesture step; any open step is closed (step 4
   above, without waiting).
3. Open an **action** step: `before` is the state now, with `marks.take()`
   when `load` is true; clear the redo stack.

What the action then changes arrives in the fingerprint this frame or the
next few (a load's own follow-ups, a base folded by `apply`). Step 3 sees
a step already open and opens no second one; step 4 closes it after the
settle time. **One action is one step.** A slider moved inside 0.4 s of
an action joins that action's step; a second action in a later frame
closes the first and opens its own.

`undo()`: bring the watcher up to date and close any open step; pop steps
until one has something to put back (below; one with nothing is dropped);
put the state now on the redo stack under the same label (with
`marks.take()` if the step is a load); restore; set `status`; start the
absorb count. `redo()` is the mirror. A new gesture or a `push` clears
the redo stack.

**Restore** puts back only what differs:

1. If the step is a load: `marks.before(...)`. A group whose saved layout
   differs from the one it has now gets it back through the library's own
   `on_layout` hook (`Control.apply_layout` for the bands), so the params
   exist before their values land: the order `Library._apply_doc` keeps.
2. Routes, if the row lists differ: `table.set_routes(copies)` (the
   referee runs, as on any load).
3. The preset layer, if it differs: `table.set_desk(copies, load=False)`.
   `load=False` is new: the same replacement and the same dropping rules,
   but it bumps `redraw_serial` instead of `desk_serial` and does not drop
   the layer. The desk redraws; **the layer that is up and the faders'
   catch stay** (`MidiIO._follow_table` clears the catch only on
   `desk_serial`).
4. The macros, if they differ: `table.set_macros(doc, reg)`.
5. The bases: every id in the state that the registry still has and whose
   base is not the same (the tolerance above), through
   `reg.restore(...)` in registry order, which ends in `Param.set`. Then
   compare again and repeat, at most three passes: one setter has side
   effects (`scene.select` → `Control.select_scene` lands a whole scene),
   and the second pass puts the strips back. Ids the registry no longer
   has are skipped. **An id under a `tagged` prefix (`band.`) is put back
   only when the state's tag equals `tag()` now**: a strip's values never
   land on another band. When some are left for that reason the status
   line says "(the bands have changed: their strips were left)".
6. `on_restore()`: `Router.sync_macros` marks the macros' bases and
   `macros_serial` as acted on, so `follow_macros` does not re-land the
   base subscribers next frame over the values just restored.
7. If the step is a load: `marks.put(...)`, last (a scene landing in step
   5 moves the band strip's mark).

So undoing one slider calls `Param.set` on one param and nothing else: no
load runs, the desk layer, the fader pickup and the LFO phases stay put. A
restore writes no file. The dirty dots compare the live state against the
loaded reference (`Library.is_dirty`), so they relight or go out honestly.

`Marks.put` relands each group's `(name, reference, reapply)`
(`Library.reland`) and recomputes `Project.active` from the bank. It puts
the `Project`'s own fields back (`remark`) **only when the show itself
differs** (undo of a show load). The bank and "starts on" are otherwise
left alone: they are written to the show's file the moment they change
(`Project.write`), and an undo that reverted them in memory would make the
show's dirty dot lie. `last_show` is not rewritten either.

**Labels.** A gesture's label comes from what differs between `before` and
the state at close: one param → `"<label> <old> → <new>"` in the param's
own format (`Param.fmt`, a choice's name, on / off); several in one group
→ `"<n> <group> settings"`; table parts → `"routes"`, `"desk"`,
`"macros"`; a mix → `"<n> changes"`.

#### Where `undo.push` is called

| Action | Site | Label | `load` |
|---|---|---|---|
| A preset load, any road | `Presets.load_doc`, after step 1's parsing, before step 2's `lib.restore(landed)` | `load <name>` | yes |
| A show load | `Project.load`, after the file is read (and migrated), before `_take` | `show <name>` | yes |
| A new show | `Project.new`, first line | `new show` | yes |
| A module preset load, step or file-watch re-apply | `Library._apply_doc`, the branch that is not a document kind, before the layout hook | `<group>: <name>` | yes |
| A module reset with no default preset | `Library.reset`, before its `restore` (the other branch goes through `load`) | `reset <group>` | yes |
| A hand learn landing | `Learn._place`, first line; and `Learn.learn_source` before `cur.when = when` | `learn <target>` | no |
| A knob learn landing | `MidiIO._learned`, before `table.bind` | `learn <pid>` | no |
| Unbind (desk) | `MidiIO.unbind`, before `table.unbind` | `unbind <pid>` | no |
| Unbind hand | `hands.panel.ctx_rows`, before the removes | `unbind hand <pid>` | no |
| A route's × | `ui_routing.page`, before `router.table.remove(dead)` | `delete route <source> → <target>` | no |
| A desk row's × | `ui_routing.desk`, before `table.remove(dead)` | `unmap <glyph>` | no |
| A macro subscriber's × | `ui_routing.macros`, before `m.subs.pop(dead)` | `delete subscriber of <macro>` | no |
| Replace in the Replace / Keep prompt | `ui_routing.answer`, when `replace_it`, before the commit (a held learn's `_place` pushes again in the same frame and is ignored) | `replace <target>` | no |

Not push sites: a scene pick, a band reset and "Reset all" (`control.py`
is not touched; the watcher makes each a step labelled from the
difference, and the 8-second button still works beside it); an effect's
order (§1 row 17); every ROUTING field edit, a row's checkbox, a gate
pick, a macro's label (gestures); and every save. A save changes no live
state; its net is the trash. A site that forgets to push is still undone:
the watcher makes its step, with a plain label, and without the marks.

#### Keys

`LOOP_KEY_ROWS` gains four rows, so `keymap()` has them and
`remap_factory` adds them to an existing `bindings.json` where the source
is free (`KEY_NEW_ROWS` is built from `LOOP_KEY_ROWS`):

```
("SUPER+Z", "edit.undo", "fire")        ("SHIFT+SUPER+Z", "edit.redo", "fire")
("CONTROL+Z", "edit.undo", "fire")      ("CONTROL+SHIFT+Z", "edit.redo", "fire")
```

`Router.keys` changes one rule: a row fires when its modifiers **equal**
the held modifiers that some row on that key names
(`b.modifiers == held & used`). For a bare row that is today's rule
(`not (held & used)`); for a one-modifier row beside a bare one it is
today's result (`test_key_rows_with_modifiers_are_distinct_controls`
passes unchanged); and ⌘⇧Z now fires redo alone. A keys object without a
`control()` method reads as "not held" (the tests' `FakeKeys`).

While imgui is typing, `Keys._down` ignores the control window, so Ctrl+Z
in a text field is the field's own; from the render window it is the
app's. The cheat sheet gains `("Cmd+Z", "undo · ⇧ redo (or Ctrl+Z)")`, and
`test_ui_shell._SYMBOLS` gains `"Cmd+Z": "SUPER+Z"`.

#### The footer's message slot

`Panel._footer` shows one faint line for 4 seconds after it changes: the
newest of `undo.status`, `library.status` and `library.warning` (the
panel remembers the last strings it saw and when one changed). It is where
"undid Brightness 1.20× → 0.85×" appears, on every page, and where WP4's
"saved TRIP 2 → F6" and an empty F-key's note become visible without
opening the PRESETS page. `panel.undo` is set by `app.main`.

#### The trash

`to_trash(path, root)` copies `path` to
`<root>/trash/<folder>/<stem>.<YYYYMMDD-HHMMSS><suffix>`, where `<folder>`
is the file's own folder name (`presets`, `fx`, `band`, …). A name taken
in the same second gets `-2`, `-3`, …; the copy is created exclusively
(`"xb"`, as `routing._write_new` does), so nothing is ever overwritten.
Returns the path written, or `None` when the copy failed (said on stderr).

- `Library.save_as`: when the file exists and its text differs from what
  is about to be written, `to_trash` first. A failed copy does not stop
  the save; `Library.warning` says the old file was not kept. An unchanged
  save trashes nothing.
- `Library.delete`: `to_trash` first; a failed copy **refuses the delete**
  (`LibraryError`, shown by `ui_presets._guard`).
- `Library.groups()` skips `trash` (as it skips `projects` and
  `LEGACY_DIRS`). The file watch never sees the trash: `Library._scan`
  reads `*.json` one level down, and trashed files sit two levels down.
- Factory files are never written, so never trashed. Show files
  (`Project.write`) and `bindings.json` are not preset files and keep
  their own backups (`routing.backup`). Nothing empties the trash; plan 19
  adds the view, restore and empty.

### WP2 — Home

**What.** One press loads the show's "starts on" preset: the Home key
(fn+← on the laptop) and the APC40's OVERDUB, the same on both layers.

**Owns.** Its lines in the shared table; `tests/test_presets.py`,
`test_midi.py`, `test_desk.py`, `test_routing.py`, `test_ui_presets.py`,
`test_ui_shell.py` for what it changes.

**Must not touch.** `undo.py`, `render.py`, `overlay.py`, `midi.py`,
`preset.py`.

**Behaviour.**

- `Project.home()` (`library.py`): with no `startup` named,
  `lib.warning = "home: this show names no 'starts on' preset — pick one
  on the PRESETS page"` and nothing loads. Otherwise
  `undo.push(f"home → {startup}", load=True)` and then exactly what
  `load_startup` does (the push inside `Presets.load_doc` is the same
  frame's and is ignored). Unsaved edits to the loaded preset go, as on
  any load; Ctrl+Z brings them back.
- `preset.home` (`build_registry`, in the `if bank is not None` block):
  `r.trigger("preset.home", "Home", bank.home, group="preset",
  lit=lambda: bool(bank.startup), tip=…)`. Modulatable like
  `preset.load.k` and `preset.next` beside it (fork 9).
- The key: `LOOP_KEY_ROWS` gains `("HOME", "preset.home", "fire")`.
- The desk: `apc40.DEFAULT_MAP` gains `_note("preset.home", N_OVERDUB)`,
  no layer, so it is **invariant** (D6, extended by the owner): a Learn on
  it is refused (`MidiIO._learned`), a preset's desk row on it is dropped
  at load with a note (`Bindings.set_desk`). Its LED is lit while the show
  has a "starts on" (the trigger's own light, as METRONOME has;
  `routing.led_lit`), dark when it has none.
- An existing `bindings.json`: `APC_NEW_ROWS` gains
  `(f"note:0:{apc40.N_OVERDUB}", "preset.home", "toggle", 1.0, False)`.
  `remap_factory` adds the OVERDUB row and the Home key row only where
  nothing uses the source, and `Bindings.load` backs the file up
  (`routing.backup` → `bindings.json.bak-v3`, or a dated name when that
  is taken) and writes it back once.
- The PRESETS page: the label `starts on` reads `starts on / home`
  (`ui_presets.starts_on`); its tooltip adds "Home (fn ←) or OVERDUB, B11
  on the desk, loads it". No new widget. The cheat sheet gains
  `("Home", "home preset (fn ←)")` and `_SYMBOLS` gains `"Home": "HOME"`.

### WP3 — Master dim on the crossfader

**What.** The crossfader dims the finished picture: left is black, right
is full. A preset load never moves it; a launch is always full.

**Owns.** `render.py` (the final pass), `overlay.py` (the param), its
lines in the shared table, `tests/test_render.py`, `test_overlay.py`,
`test_midi.py`, `test_desk.py`, `test_routing.py`, and the output stub
in `test_app_boundary.py`.

**Must not touch.** `ghost.py`, `fx.py`, `lookback.py`, `library.py`,
`params.py`, `preset.py`, and `midi.py` beyond the one rule in `redraw`
named below.

**Behaviour.**

- `Output.dim = 1.0` and, in `Output.register`,
  `reg.continuous("output.dim", "Master dim", …, lo=0.0, hi=1.0,
  fmt=lambda v: "black" if v <= 0 else f"{v * 100:.0f}%", group="output",
  **rig)`. `rig` is the dict already there: `persist=False,
  modulatable=False` (fork 10). The setter clamps to 0–1. It is a session
  param by group (`"output"` is in `SESSION_GROUPS`), so no preset can
  name it, and not persisted, so no show saves it and
  `test_rig_settings_never_persist_or_modulate`'s snapshot stays
  `{output.bg, output.alpha}`. No config key: a launch is bright. No
  `overlay.*` alias.
- `app.frame`: `h.renderer.dim = h.output.dim`, beside the `bg_alpha`
  line (the state lives on `Output` and reaches the renderer the way the
  ground does; fork 11).
- `Renderer.dim = 1.0` (`__init__`; read with `getattr(self, "dim", 1.0)`
  so a renderer from before a hot reload works). At the end of
  `Renderer._draw_frame`, **after** `self.ghost.draw(...)`:

  ```python
  dim = getattr(self, "dim", 1.0)
  if dim < 1.0:
      self.dim_pass(target, vp, dim, opaque=fx.opaque)
  ```

  `dim_pass(target, vp, factor, opaque)` binds the target and its
  viewport and draws one full-screen triangle whose fragment is
  `vec4(0, 0, 0, factor)`, blending only: no texture is read.
  - **Opaque ground** (window and fullscreen): blend
    `(ZERO, SRC_ALPHA, ZERO, ONE)`. Colour becomes colour × factor; alpha
    is left exactly as it was, so the Pepper's Ghost window stays opaque
    black (plan 14 WP1).
  - **Overlay's see-through ground**: blend
    `(ZERO, SRC_ALPHA, ZERO, SRC_ALPHA)`. The frame is premultiplied
    (`draw_scene`'s ground, the ghost hands' composite), so colour and
    alpha both scale: the render fades out and the desktop behind is left
    as the config asked for (fork 12).
  - It puts `blend_func` back to `SRC_ALPHA, ONE_MINUS_SRC_ALPHA` and
    leaves the target bound, like the ghost hands' pass. Its program is
    built on first use and rebuilt in `on_reload`; a driver that refuses
    it leaves the frame undimmed, says why in `Renderer.dim_error`, and
    never raises.
  - **At 1 the pass does not run**: no GL state is touched and the frame
    is bit-identical to today's.
  - It is last, so it dims the scene, the look-back, every effect and the
    ghost hands alike. The look-back's history and the dream worker are
    fed from the scene texture before it, so an echo never remembers a
    dim.
  - The multiply is linear in the framebuffer's values. If the bottom of
    the throw feels too sudden on the glass, that is a curve inside
    `dim_pass`, not a param.
- The desk: the row becomes `_cc("output.dim", CC_XFADE, 0, ring=0)`,
  still with no layer (a fader, invariant), `abs` with soft pickup (the
  default). CC 0 is black. That CC 0 is the **left** end is read from the
  old row's comment ("the video behind (left)", which was `bg` 0), not
  from the device; hand check 55 confirms it, and the other way round is
  a one-line change.
  - A launch with the crossfader parked at the left: `dim` is 1, the row
    is not caught, and `MidiIO._apply` does nothing until the fader
    reaches the value. So it cannot black the rig out by being touched;
    it takes hold at the right end.
  - A preset load must not loosen it. Today `MidiIO.redraw(load=True)`
    clears **every** fader's catch, whether or not the load moved its
    param, and the fader is caught again only if its next message lands
    within `PICKUP_TOL` of the value or crosses it. The value sits on the
    param's own detent (`set_norm` rounds to a hundredth for an untapered
    param) and the fader on a MIDI step, so a first move away from the
    value misses roughly one time in ten, and the fader is then dead until
    it is brought back across. WP3 changes the one rule (fork 19): a load
    clears the catch of a fader **whose param is no longer where the
    adapter last put it** (`abs(p.norm − self._writes[target]) >
    PICKUP_TOL`, the test `_uncatch_moved` already applies every poll). A
    preset load never moves a session param (D9), so the crossfader, S1–S8
    and SM keep their hold through it; a fader with no last write, or a fader
    whose base a load did move still picks up
    (`test_a_preset_load_clears_the_faders_catch` passes unchanged).
  - Dragging the panel's fader re-arms pickup (`_uncatch_moved`).
- An existing `bindings.json`: `APC_REMAP` gains
  `(f"cc:0:{apc40.CC_XFADE}", "overlay.bg", "abs", 1.0): ("output.dim",
  "abs", 1.0)`. Only the exact factory row is swapped; a crossfader row
  the owner changed is left alone. The file is backed up first, as above.
  The note `remap_factory` writes says "plan 15", not "plan 09".
- The OUTPUT page: `self._row("output.dim")` first on the page. The
  overlay's ground stays where it is, on that page, shown only when the
  config allows overlay. The footer shows `dim 40%` in the warning colour
  while `output.dim` is under 1, so a dark picture is never a mystery.
- No blackout button (roadmap §6).
- **The seam for plan 21**: `dim_pass(target, vp, factor, opaque)` takes
  the factor. Plan 21 calls it once per output with
  `master × that output's dim`.

### WP4 — Save-as on the desk; "put preset here…" and "clear slot"

**What.** Hold anywhere on the clip-stop row for 0.6 s: the live state is
saved as a **new** preset, named from the loaded one, into the next empty
bank slot, whose pad blinks. A tap does nothing. The desk never
overwrites. On the PRESETS page a slot's right-click menu can point the
slot at any preset or empty it.

```
 the button field (left of the desk)

 clip row 1   [G1·1][G1·2][G1·3][G1·4][G1·5][G1·6][G1·7][G1·8]  [G1·9]   press: load slot k
 clip rows 2–5   …                                                        (today, unchanged)
 clip stop    [=============== SAVE AS  ·  G6·1 … G6·8 ==============]  [G6·9]  STOP ALL: reset all,
               hold any of the eight 0.6 s: a NEW preset → the next               unchanged
               empty slot, whose pad on clip row 1 blinks; a tap: nothing

 the right-hand section

 device buttons   [B5 ][B6 ][B7 ][B8 ]
                  [B9 ][B10][B11][B12]      B9 DETAIL: cheat sheet    B10 QUANT: next preset
                                            B11 OVERDUB: home (WP2)   B12 METRONOME: LFO trigger
 crossfader  X    [■■■■■■■■■──────────]     left: black … right: full (WP3)
```

**Owns.** Its lines in the shared table; `tests/test_midi.py`,
`test_desk.py`, `test_presets.py`, `test_library.py`, `test_routing.py`,
`test_ui_presets.py`.

**Must not touch.** `undo.py`, `render.py`, `overlay.py`, `preset.py`,
`learn.py`.

**The hold, in `midi.py`.**

- `routing.OPS` gains `"hold"`: a note row whose target fires once the
  button has been down `HOLD_S`; a release before that does nothing.
  `routing.act` ignores it (a key or pad row with it does nothing); the
  ROUTING page's session section prints it as it prints any op
  (`ui_routing._op_text`).
- `midi.HOLD_S = 0.6`, `midi.BLINK_S = 1.5`. `MidiIO` keeps its `clock`
  argument as `self.clock` (today it only passes it to `Ports`).
- `_handle`: a note-on whose rows include `hold` rows records
  `self._holds[(channel, note)] = (self.clock(), rows)` and sets `b.lit`
  on **every** enabled `hold` row with that target, so the whole bar
  lights while any part of it is held (the press echo, spread over the
  bar). The note-off removes the entry; when no entry for that target is
  left, the bar goes dark. A tap therefore lights the bar for as long as
  it lasts and fires nothing.
- `poll`, after the messages are handled: for each entry held `HOLD_S` or
  longer, note which LED rows are lit now, fire the target once
  (`p.fire()`), and remove **every** entry with that target, so a hand
  lying across the row saves once, and a button still down fires nothing
  more: only a new press starts a new hold. It fires **while held** (fork
  14): the blink is what tells you to let go.
- The blink: every LED row that the fire turned on, and the bar's own
  rows, blink for `BLINK_S`: `feedback` sends the profile's blink
  velocity for those controls, whatever their state, until the time is
  up, then the ordinary state. `apc40.blink_of(number, on)` is `on + 1` on the clip
  grid (green 1 → 2, red 3 → 4, yellow 5 → 6) and 2 on any other button,
  the protocol's numbers in the module docstring. `midi.py` knows nothing
  of the bank: after a save the new slot is the loaded one, its pad's row
  (`preset.select`, `set k`) turns on, so it is the pad that blinks, and
  then stays green.
- At rest the bar is dark (fork 15). While a Learn is armed a press goes
  to `_learned`, which refuses an invariant control; no hold starts.
  `_enter` (a reconnect) clears `_holds`.

**The rows.** `apc40.DEFAULT_MAP` gains
`*[_note("preset.save_new", N_CLIPSTOP, k, op="hold") for k in range(8)]`,
no layer: **invariant**, the same on both layers, refused by Learn,
dropped from a preset's desk with a note. For an existing `bindings.json`,
`APC_NEW_ROWS` gains the eight
`(f"note:{k}:{apc40.N_CLIPSTOP}", "preset.save_new", "hold", 1.0, False)`,
added where nothing uses the source, with the backup as above.

**The trigger.** `preset.save_new` (`build_registry`, the bank block):
`r.trigger("preset.save_new", "Save as a new preset", bank.save_new,
group="preset", modulatable=False)`, like `preset.save.k` beside it. A new
trigger because no existing one means this: `preset.save.k` writes over
the preset slot k names, which is exactly what the desk must never do.

**Naming and the bank, in `library.py`.**

```python
def next_name(base: str | None, taken: set[str]) -> str
```

- `taken` is a set of slugs. If `base` ends in whitespace and a number
  after a non-empty stem, the stem is what comes before and counting
  starts above that number; otherwise the stem is `base` and counting
  starts at 2. The answer is the first `"<stem> <n>"` whose slug is not
  taken. `TRIP` → `TRIP 2`; `TRIP 2` → `TRIP 3`; `TRIP 2` with `TRIP 3`
  there → `TRIP 4`; `2001` → `2001 2`. With no preset loaded the stem is
  `PRESET` and counting starts at 1.
- `Project.save_new()` builds `taken` from three things: the file stems in
  both preset folders (`lib._files(PRESETS)`: factory and user, because a
  user file with a factory file's slug would hide that preset, §1 row 14),
  the slugs of every listed name, and the slugs of the bank's names. Then
  `presets.save_as(name)`, which writes a new user file and makes it the
  loaded preset with a clean dot, as the panel's "as…" does
  (`Library.save_as`). Then `k = self.next_empty()`; if there is one,
  `bank[k] = name`, `active = k`, `self.write()`, and
  `lib.status = f"saved {name} → F{k + 1}"`; if the bank is full,
  `lib.warning = f"saved {name} — the bank is full: it is in the preset
  list"`. A failed write is said in `bank_error`, as `save_slot` does. No
  `undo.push`: nothing live changes.
- `Project.next_empty() -> int | None`: the first `k` with
  `self.bank[k] is None`, over `range(len(self.bank))`. That list is the
  one place the bank's size is read; plan 19's twenty-four slots need no
  change here.
- Because the new preset becomes the loaded one, a second hold counts on:
  `TRIP 2`, then `TRIP 3`.
- `Project.put_slot(k, name)`: point slot k at a preset (the file must
  exist, else a warning); `Project.clear_slot(k)`: empty it. Both write
  the show at once (`Project.write`: a factory show's first write makes
  your copy, as "starts on" does), recompute `active`, and delete no
  file. Neither is an undo step: the bank is the show file's.

**The PRESETS page.** `Panel._ctx(a, key="", extra=None)` draws `extra()`
inside the param's popup before it closes. `ui_presets.preset_bank` passes
a function that draws:

- **put preset here…**: a submenu listing `names(panel, PRESETS)` in a
  child at most twelve rows tall (it scrolls past that); a pick calls
  `put_slot(k, name)`.
- **clear slot**: disabled on an empty slot; calls `clear_slot(k)`.

Plain Save and "as…" on the strip are unchanged. ⇧F1–F8 is unchanged.

### WP5 — Docs and hand checks

**Owns.** `ARCHITECTURE.md` (§1 a row for `undo.py` and the library row's
imports; §2 the frame order and "the dim is the frame's last pass, after
the ghost hands"; §3.2 undo among the scene-setters; §3.7 rows for Home,
the crossfader, the hold; §3.8 the new factory rows), `DECISIONS.md` (a
row each for decisions 26–29 as built; D6's row gains the crossfader as
dim, OVERDUB and the clip-stop row; the 2026-10-04 ghost row gains "the
dim follows it"; the key-modifier row gains CONTROL and the chord rule),
`ENGINEERING.md`, `DECISION-REGISTER.md` (rows after 33 for forks 1, 5,
7, 8, 12, 14, 15 and 16, each "built on the recommendation; confirm or
overturn" with its cost to reverse), `plans/README.md` (a row for this
plan), `11-hand-checks.md` (§9 below as group K; its opening paragraph;
check 1's list of keys), and this file's "As built".

## 3. Parameter budget

Everything the plan adds, and what each replaces.

| Added | Kind | Replaces, or why nothing |
|---|---|---|
| `edit.undo`, `edit.redo` | 2 triggers | Nothing: a key row needs a param to fire. No widget, no page. |
| ⌘Z, ⌘⇧Z, Ctrl+Z, Ctrl+⇧Z | 4 key rows | Nothing; two chords would do (fork 1). |
| `CONTROL` | a key modifier | Nothing; it is what "Ctrl+Z" needs. |
| the footer's message | a line, shown 4 s | Replaces having to open the PRESETS page to read `Library.status` and `warning`. |
| `<home>/trash/` | a folder | Nothing. No view of it here (plan 19). |
| `preset.home` | 1 trigger | No new noun: it loads "starts on" (decision 27). The label on the PRESETS page changes; no widget is added. |
| Home key; OVERDUB | 1 key row, 1 desk row | OVERDUB was unused. |
| `output.dim` | 1 param, 1 fader on OUTPUT | Takes the crossfader from `overlay.bg`, which has done nothing since decision 21. Not saved, not modulatable, no config key, no blackout button. |
| the footer's `dim 40%` | a readout | Nothing; it is a label, shown only while dimmed. |
| `preset.save_new` | 1 trigger | Nothing: `preset.save.k` overwrites. No panel widget ("as…" is the panel's). |
| the clip-stop bar | 8 desk rows, one meaning | The row was unused. One bar, not eight buttons to learn. |
| `hold` | an op | Nothing; a press that must last has no other spelling in the table (fork 13). |
| "put preset here…", "clear slot" | 2 menu items | Replace load-then-⇧F as the only way to fill a slot; there was no way to empty one. |

Rejected because a default or an existing concept does the job: a settle
time setting (one constant); an undo depth setting (one constant); a
history panel (the footer line); a separate "home" pointer in the show
(decision 27 (b)); a dim curve param; a `[output] dim` config key; a
blackout toggle; a "save-as name" prompt on the desk (the name is made;
plan 19's rename fixes it afterwards); a held modifier for save (the desk
has none: SHIFT is a latch); a setting for the hold time.

## 4. What this plan does not change

- The control model (ARCHITECTURE §3). Undo and home are scene-setters:
  bases through `Param.set`, table parts through `set_routes` /
  `set_desk` / `set_macros`. `Router.modulate` stays the one caller of
  `Param.modulate`; the dim is a read by the render stack.
- **D2**: a preset load replaces everything. Undo of a load puts the
  earlier state back the same way, whole. Home is a load.
- **D5**: the global layer is fixed. Nothing here is learned into it.
- **D6**: invariant controls mean one thing on both layers and no preset
  maps them. The list grows by the crossfader's new meaning, OVERDUB and
  the clip-stop row (the owner, decisions 27–29).
- **D7**: faders soft-pick-up. The crossfader is a fader.
- **D8**: an unmapped control is dark and dead.
- **D9**: a preset never moves a session param. `output.dim` is one.
- **D11**: the show names what it starts on. Home is that preset.
- **D12**: a modifier is read at the press. A hold's rows are those of
  the press.
- Factory presets are read-only and a user file shadows one. The trash
  never holds a factory file, and save-as never takes a factory file's
  slug.
- The render window has no imgui. Every message is on the control window.
- The ghost hands are the last thing *drawn*. The dim multiplies the
  finished frame after them and draws nothing of its own.
- The 8-second "Reset all" undo (`control.py`).
- Tap-only tempo; a tap is not an undo step.

## 5. Exit criteria

### Headless: named tests

**WP1** (`tests/test_undo.py` unless a file is named)

| Test | Proves |
|---|---|
| `test_undo_imports_nothing_from_the_package` | the leaf rule, by an AST walk as `test_lfo_boundary` does |
| `test_a_slider_drag_is_one_step_and_undo_sets_only_that_param` | many base writes inside the settle time are one step; the restore calls `Param.set` on one param |
| `test_a_pause_longer_than_the_settle_time_makes_a_second_step` | `SETTLE_S` is the boundary |
| `test_a_knob_turn_on_the_desk_is_one_step` | CC messages through `MidiIO` over injected ports |
| `test_a_performer_moving_makes_no_step` | a hand feed on `view.speed` (a param whose base moves by round-off) entering, moving for 120 frames and leaving: the stack stays empty |
| `test_integrated_state_and_the_clock_are_not_watched` | `rot.phase.*` advancing, a tap burst, `ui.page`, `output.fullscreen`: no step |
| `test_session_params_are_covered` | `hands.smooth` and `master.gain` undo |
| `test_undo_of_a_slider_does_not_rerun_a_load` | `desk_serial`, the layer, a caught fader and an LFO's running phase are as they were |
| `test_a_preset_load_is_one_step_by_every_road` | F-key trigger, `preset.next`, the strip's load, the file watch: one step each, labelled `load <name>` |
| `test_undo_of_a_load_puts_back_the_values_the_routes_the_desk_the_macros_and_the_name` | the whole earlier state and `Library.current` |
| `test_save_after_undoing_a_load_writes_the_earlier_preset` | the marks: the old look cannot land on the wrong file |
| `test_a_show_load_and_its_startup_preset_are_one_step` | nested pushes in one frame; the `Project` comes back |
| `test_a_push_and_its_changes_are_one_step` | a push, then changes over the next frames: one entry |
| `test_an_action_that_changes_nothing_leaves_no_step` | an empty step is dropped |
| `test_redo_and_a_new_edit_clears_it` | both directions |
| `test_undo_writes_no_file_and_the_dirty_dot_is_honest` | no mtime in the home moves; `is_dirty` follows the state |
| `test_a_scene_pick_undoes_with_its_strips` | the second restore pass |
| `test_the_macros_do_not_re_land_after_an_undo` | `Router.sync_macros` |
| `test_a_band_preset_load_with_a_layout_undoes_whole` | `Marks.before`: the layout, then the strips |
| `test_strips_are_put_back_only_onto_the_layout_they_were_made_on` | the tag: after a band is added, an older strip edit is left and the rest of that step lands; with the band removed again it lands |
| `test_a_band_add_remove_or_move_makes_no_step` | tick step 1 |
| `test_the_stack_is_bounded` | `LIMIT` |
| `test_learn.py::test_a_learn_is_one_undo_step`, `test_midi.py::test_an_unbind_is_one_undo_step` | the pushes in `learn.py` and `midi.py`; the row comes back |
| `test_ui_routing.py::test_a_route_delete_and_a_replace_are_undo_steps` | the pushes on the page |
| `test_desk.py::test_undoing_a_desk_row_redraws_and_keeps_the_layer_and_the_faders_catch` | `set_desk(load=False)` |
| `test_routing.py::test_a_chord_fires_only_its_own_row` | ⌘⇧Z fires redo alone; `…::test_key_rows_with_modifiers_are_distinct_controls` still passes unchanged |
| `test_routing.py::test_an_older_file_gets_the_undo_keys_where_they_are_free` | `remap_factory`, with the backup |
| `test_routing.py::test_factory_table_binds_only_real_params`, `::test_factory_files_match_the_code` | every new row names a real param and a real op; the generated file is current (the counts in the first are updated by each package) |
| `test_app_boundary.py::test_the_frame_runs_in_the_documented_order` | `undo.tick` after `router.follow_macros` |
| `test_app_boundary.py::test_keys_read_the_modifiers_the_table_spells` | `Keys.control` |
| `test_ui_shell.py::test_the_cheat_sheet_matches_the_tables_and_the_loop_keys` | the sheet names Z (and, after WP2, Home) |
| `test_ui_shell.py::test_the_footer_says_what_was_undone`, `::test_every_page_fits_the_control_window` | the message slot; no page scrolls |
| `test_hotreload.py::test_every_package_module_but_the_cold_core_is_watched`, `::test_the_watch_list_is_in_dependency_order` | `undo` is in `MODULES`, before `params` |
| `test_routing_boundary.py`, `test_lfo_boundary.py`, `test_hands_boundary.py`, `test_audio_boundary.py` | unchanged and green |
| `test_library.py::test_a_save_over_a_preset_keeps_the_old_file_in_the_trash` | `Library.save_as` |
| `test_library.py::test_a_delete_keeps_the_file_in_the_trash_or_does_not_delete` | `Library.delete`, and the refusal |
| `test_library.py::test_a_save_that_changes_nothing_trashes_nothing` | no noise |
| `test_library.py::test_two_trashings_in_one_second_do_not_collide` | the names |
| `test_library.py::test_the_trash_is_no_group_and_is_never_watched` | `groups()`, `poll()` |

**WP2**

| Test | Proves |
|---|---|
| `test_presets.py::test_home_loads_what_the_show_starts_on` | from another preset, with edits |
| `test_presets.py::test_home_with_no_starts_on_says_so_and_loads_nothing` | the warning |
| `test_presets.py::test_home_is_one_undo_step` | Ctrl+Z after home brings the edited look back |
| `test_desk.py::test_overdub_is_home_on_both_layers_and_is_lit` | invariant; the LED |
| `test_learn.py::test_learn_refuses_the_global_layer_and_invariant_controls` (extended) | OVERDUB refuses a Learn |
| `test_routing.py::test_an_older_file_gets_home_where_it_is_free` | the key row and the OVERDUB row, with the backup |
| `test_ui_presets.py::test_starts_on_reads_starts_on_home`, `::test_the_page_speaks_one_word_per_thing` | the label |
| `test_ui_shell.py::test_every_page_fits_the_control_window`, `::test_the_cheat_sheet_matches_the_tables_and_the_loop_keys` | still fits; the sheet names Home |

**WP3**

| Test | Proves |
|---|---|
| `test_render.py::test_dim_at_one_is_the_old_frame_exactly` | bit-identical, effects and ghost hands on |
| `test_render.py::test_dim_scales_the_colour_and_leaves_an_opaque_grounds_alpha` | 0.5 halves every channel within a step; alpha 255 everywhere |
| `test_render.py::test_dim_at_zero_is_black_and_opaque` | left is black |
| `test_render.py::test_dim_is_after_the_effects_and_the_ghost_hands` | hands on over an effect: both dimmed alike |
| `test_render.py::test_dim_fades_a_see_through_ground` | overlay: alpha scales too |
| `test_render.py::test_the_history_never_holds_the_dim` | the look-back's capture is undimmed |
| `test_overlay.py::test_dim_is_a_rig_setting_that_starts_bright` | not persisted, not modulatable, 1 on a fresh `Output`; `::test_rig_settings_never_persist_or_modulate` unchanged |
| `test_presets.py::test_a_preset_load_never_touches_a_session_param` (extended) | a load and a show load leave `output.dim` |
| `test_midi.py::test_the_crossfader_dims_with_soft_pickup` | parked at 0 with dim at 1: nothing until it reaches 1; then it follows; CC 0 is 0 |
| `test_desk.py::test_the_crossfader_keeps_its_hold_across_a_preset_load` | still caught after a load; the next message moves the dim from where it is, in either direction; `::test_a_preset_load_clears_the_faders_catch` unchanged |
| `test_routing.py::test_an_old_crossfader_row_moves_to_the_dim_with_a_backup` | `APC_REMAP`; a changed row is left alone |
| `test_routing.py::test_the_apc_migration_tables_agree_with_the_default_map` | the remap and the map agree (existing; holds every package's rows) |
| `test_app_boundary.py::test_the_frame_runs_in_the_documented_order` | `renderer.dim` is the output's, this frame |
| `test_ui_shell.py::test_every_page_fits_the_control_window` | OUTPUT with its new row |

**WP4**

| Test | Proves |
|---|---|
| `test_midi.py::test_a_hold_fires_once_at_the_hold_time_while_held` | the fake clock at 0.59 s and 0.6 s; nothing more at 2 s |
| `test_midi.py::test_a_tap_fires_nothing` | released at 0.3 s |
| `test_midi.py::test_the_bar_is_one_control` | two buttons held: one fire; a button still down fires nothing more; a new press starts a new hold |
| `test_midi.py::test_the_bar_lights_while_held_and_the_new_slots_pad_blinks` | the velocities sent, and for how long |
| `test_desk.py::test_the_clip_stop_row_is_invariant` | both layers; refuses a Learn; a preset's row on it is dropped with a note |
| `test_library.py::test_next_name_counts_on_from_a_trailing_number` | `TRIP`, `TRIP 2`, a gap, `2001`, no preset |
| `test_presets.py::test_save_new_never_overwrites` | with `trip-2.json` present under another name, and a factory slug in the way |
| `test_presets.py::test_save_new_fills_the_next_empty_slot_and_becomes_the_loaded_preset` | the bank, the show file, `current`, a clean dot |
| `test_presets.py::test_save_new_on_a_full_bank_saves_to_the_list_and_says_so` | the warning; the bank untouched |
| `test_presets.py::test_the_new_slot_loads_from_the_preset_row` | clip row 1's pad k after a save |
| `test_presets.py::test_put_and_clear_slot_write_the_show_and_delete_no_file` | the two menu items' calls |
| `test_library.py::test_next_empty_reads_the_banks_own_length` | a bank of 24 answers without a code change |
| `test_routing.py::test_an_older_file_gets_the_save_bar_where_it_is_free` | eight rows, the backup |
| `test_ui_presets.py::test_a_slots_menu_offers_put_and_clear` | the items; clear disabled on an empty slot |
| `test_ui_shell.py::test_every_page_fits_the_control_window` | PRESETS still fits |

**Every package**: `uv run pytest -q` and `uv run ruff check` green on the
integration branch after its merge, run with `HYPERSPACE_HOME` on a temp
folder.

### At the machine

Group K, §9: checks 48–57.

## 6. The owner's to-do list at the machine

Before launching this build: `cp -R ~/Hyperspace ~/Hyperspace-2026-10-04`.
The first launch rewrites `bindings.json` once (the crossfader, OVERDUB,
the clip-stop row, the Home and undo keys) and keeps the old file beside
it.

- [ ] 57 **first** — the first launch: the backup exists, the notes on
  stderr, and any preset of yours that mapped OVERDUB or a clip-stop
  button says so.
- [ ] 48, 50, 53 — laptop alone: undo a slider drag; undo a load; the
  trash.
- [ ] 49, 51, 54, 55, 56 — APC40 in: undo a knob turn; undo a Learn and
  an Unbind; home; the crossfader; save-as.
- [ ] 52 — camera and box: a hand moving makes no step.

## 7. Forks

Each was settled without the owner. The cost to reverse is what it takes
to switch to another option after the build.

**1. Which keys undo.** The roadmap says Ctrl+Z; the rig is a Mac, where
undo is ⌘Z and the sheet already says "Cmd+R".

| Option | Trade-off |
|---|---|
| (a) ⌘Z / ⌘⇧Z only | No new modifier. "Ctrl+Z", as written and as said, does nothing. |
| (b) Ctrl+Z / Ctrl+⇧Z only | What was said. Wrong for Mac hands. One new modifier. |
| **(c) Both** | Either hand finds it. One new modifier name and two more rows. |

**Recommended: (c).** A missed undo mid-party costs more than two rows.
The chord rule in `Router.keys` is needed under every option. Reverse:
delete two rows, or the modifier.

**2. What comes back with a step besides values and rows.** After undoing
a load, the library must say the earlier preset is loaded, or Save writes
the earlier look over the later file.

| Option | Trade-off |
|---|---|
| (a) Never restore "what is loaded" | Simplest. Save after undoing a load overwrites the wrong preset. Rejected. |
| (b) Restore it with every step | A slider undone after a save-as would put you back "on" the old name. |
| **(c) Only with steps pushed as loads** (`load=True`) | Right in both cases. One optional keyword on the published call. |

**Recommended: (c).** Reverse: drop the keyword and pick (b).

**3. How callers reach the undo.**

| Option | Trade-off |
|---|---|
| **(a) Module functions over an installed instance** (`undo.push`) | One import and one line per site; a no-op in tests with nothing installed. A module-level current instance, kept across a hot reload. |
| (b) Hand the object to every caller | No global. Six objects to wire, and every later plan's call site needs the object passed down to it. |

**Recommended: (a)**; it is the call roadmap §5 names. Reverse: mechanical.

**4. The band layout.** See §1 row 4.

| Option | Trade-off |
|---|---|
| (a) Fold it all in: add, remove and move become steps, the 8-second button retires | Pushes in `control.py`, a layout in every state, and the reset undo's own snapshot (params by object, `Control._undo_reset_all`) redone. Not cheap. |
| (b) Clear the whole stack on any layout change | Adding a band throws away the history of the look. |
| (c) Drop `band.*` from the history on any layout change | Simple, but every factory band preset carries a layout, so Ctrl+Z after loading one from the strip would find its own step emptied and undo the edit *before* it. |
| **(d) Tag each state with the bands' names; put `band.*` back only onto the same tag; a load step carries its layout and puts it back first** | A band preset load, a show load and a scene pick undo whole. Add, remove and move are not steps; strips edited before one are left alone by an undo until the layout is the same again. About twenty lines, all in `undo.py` and `library.Marks`; `control.py` is not touched. |

**Recommended: (d).** The 8-second "Reset all" button stays beside it.
Reverse: (a) is a later plan's work and builds on (d).

**5. Is a tap an undo step.**

| Option | Trade-off |
|---|---|
| (a) Watch `tempo.bpm` | Each tap of a burst is a step; Ctrl+Z after tapping walks back through tempos before it reaches the slider you meant. |
| **(b) Leave the `tempo` group out** | "Clocks" are on the roadmap's own list. A typed BPM is not undone either. |

**Recommended: (b).** Reverse: one tuple.

**6. The trash on a save.**

| Option | Trade-off |
|---|---|
| (a) Trash on every overwrite | A Save that changes nothing fills the folder. |
| **(b) Trash only when the text differs; a failed copy warns on save and refuses a delete** | Quiet. A full disk cannot make a delete unrecoverable, and cannot block a save. |
| (c) A failed copy refuses the save too | Safest for the file, worst at a party. |

**Recommended: (b).** Reverse: one condition.

**7. The Home key on a laptop.** A MacBook has none; fn+← sends it.

| Option | Trade-off |
|---|---|
| **(a) `key:HOME` only; the sheet says "fn ←"** | One row. The desk's OVERDUB is the party road. |
| (b) A second key as well (say ⇧H) | One more thing on the sheet for a road the desk already has. |

**Recommended: (a).** The row is in the table; it rebinds like any other.

**8. Are camera moves undo steps.** Mouse orbit, the sticks, the wheel and
↑ / ↓ write bases (`Param.nudge` / `scale`), and the camera is preset
state.

| Option | Trade-off |
|---|---|
| **(a) Watch them like any base** | R (reset view) and an orbit undo. Someone who orbits a lot must press Ctrl+Z past the orbits; the stack holds 100. |
| (b) Leave the camera group out | Ctrl+Z always reaches a "real" edit. A wrecked camera is not undone, though it is saved in presets. |

**Recommended: (a).** Reverse: add `"camera"` to `EXCLUDED_GROUPS`.

**9. May a performer fire `preset.home`.**

| Option | Trade-off |
|---|---|
| **(a) Modulatable, like `preset.load.k` and `preset.next`** | No new rule. A pinch can send the show home. |
| (b) Not modulatable | A second rule for one trigger of a family. |

**Recommended: (a).** Reverse: one flag.

**10. Is `output.dim` modulatable.**

| Option | Trade-off |
|---|---|
| (a) Yes | A band or a hand could strobe the room, and a hand leaving could black it out. A session param under a preset's route is allowed (row 19), so a preset could carry it. |
| **(b) No, like the four rig settings beside it** | The dim is the operator's. A strobe is an effect's job. |

**Recommended: (b).** Reverse: one flag.

**11. Where the dim's state lives.**

| Option | Trade-off |
|---|---|
| **(a) On `Output`, handed to the renderer by one line in `app.frame`** | The road `bg_alpha` takes. One line in the file WP1 owns. |
| (b) A state object through `build_registry`, like `GhostState` | Touches `params.py`, `app.main` and the renderer's constructor for one float. |

**Recommended: (a).**

**12. What the dim does in overlay mode.**

| Option | Trade-off |
|---|---|
| (a) Colour only, as on an opaque ground | The ground's alpha stays, so a part-dark ground stays dark over the desktop while the shape goes: neither black nor gone. |
| **(b) Colour and alpha** | The render fades away and the desktop is left as the config asked. "Black" cannot mean anything on a ground the config made see-through. |

**Recommended: (b).** Overlay is off unless the config asks. Reverse: one
blend tuple.

**13. How the table spells a hold.**

| Option | Trade-off |
|---|---|
| **(a) A new op, `hold`** | The row says what it does on the ROUTING page; the adapter times any row with it. One more op. |
| (b) `midi.py` treats rows on `preset.save_new` specially | No new op. The adapter then knows a param by name. |
| (c) A `Binding` field, `hold: float` | A setting per row nobody asked for. |

**Recommended: (a).** Reverse: (b) is a few lines.

**14. When the hold fires.**

| Option | Trade-off |
|---|---|
| **(a) At 0.6 s, while held** | The blink is the feedback: you know it saved and let go. Something left lying on the row saves once, a new preset, and then nothing. |
| (b) On release after 0.6 s | No confirmation until the hand is gone; a long lean saves nothing, silently. |

**Recommended: (a).** Reverse: move one call.

**15. The bar's LEDs at rest.**

| Option | Trade-off |
|---|---|
| (a) Lit | Says "mapped". Eight lights under the grid all night, and on this desk a lit button means a state that is on. |
| **(b) Dark; lit while held; blinking with the new slot's pad when it saves** | The light is the gesture's feedback. The on-screen desk and the hand-check card say what the row is. |

**Recommended: (b).** Reverse: the rows' `off` velocity.

**16. What a made-up name counts against, and what happens next.**

| Option | Trade-off |
|---|---|
| (a) Count against the listed names only | A user file whose slug is another preset's file would be overwritten, or would hide a factory preset. |
| **(b) Count against file stems in both folders, listed names and the bank; the new preset becomes the loaded one** | Never overwrites, never hides. A second hold counts on (TRIP 2 → TRIP 3), and Save on the panel then saves the new one. A factory "TRIP" yields a user "TRIP 2". |
| (c) As (b), but stay on the old preset | Every hold makes "TRIP 2", "TRIP 3" from TRIP, but Save on the panel would still write TRIP, which the owner did not ask to change. |

**Recommended: (b).** It is what the panel's "as…" already does. Reverse:
one line.

**17. A drag that pauses.** A slider held still for more than 0.4 s with
the mouse down, then moved again, is two steps.

| Option | Trade-off |
|---|---|
| **(a) The settle time only** | One rule for the panel, the desk, keys and typed values. |
| (b) Also hold the step open while imgui has an active item | One step per mouse press. `undo.py` would need the panel to tell it, and the desk's knobs get nothing from it. |

**Recommended: (a)**, as the roadmap says. Reverse: one flag set by the
panel.

**18. Who edits the shared documents.**

| Option | Trade-off |
|---|---|
| (a) WP4, last | One fewer PR; WP4 becomes a code and docs PR to review as one. |
| **(b) A small WP5** | The four code PRs touch no shared table, so they do not conflict there. One more PR. |

**Recommended: (b).**

**19. The crossfader after a preset load.** See WP3: a load clears every
fader's catch today, moved or not.

| Option | Trade-off |
|---|---|
| (a) Leave `MidiIO.redraw` as it is | No change to the adapter. After about one load in ten the crossfader is dead until it is brought back across its value: with the picture half dimmed, mid-party. |
| **(b) A load clears a fader's catch only when its param moved** | "Survives a preset load" is exact. The same fix reaches S1–S8 and SM, whose params a preset never moves. One condition in `redraw`; the existing test of a moved base passes unchanged. |
| (c) Give the crossfader's row `pickup: false` | It would jump to the fader's position on first touch: a crossfader parked at the left blacks the rig out. Rejected. |

**Recommended: (b).** Not seen at the machine: the one-in-ten is worked
from `PICKUP_TOL`, the MIDI step and the detent, not measured. Reverse:
one condition.

## 8. As built

Filled as the work packages land.

## 9. Appendix — group K for `11-hand-checks.md`

WP5 pastes this in after group J (its heading at the level of the other
groups'), and adds "then plan 15's group K" to the file's opening
paragraph. The text is final except for PR numbers.

### K. Plan 15 — undo, home, the dim, save-as on the desk — added 2026-10-04

Run on `finish-line` once plan 15 is merged into it. 48, 50 and 53 run on
the laptop alone; 49, 51 and 54–57 need the APC40; 52 needs the camera
and the box. About 35 minutes. The headless tests named are the ones each
package adds; run them first. Before the first launch:
`cp -R ~/Hyperspace ~/Hyperspace-2026-10-04`, and do 57 first.

**48. Undo takes back one slider drag (plan 15 WP1, decision 26).**
Headless: `uv run pytest -q tests/test_undo.py::test_a_slider_drag_is_one_step_and_undo_sets_only_that_param tests/test_undo.py::test_a_pause_longer_than_the_settle_time_makes_a_second_step`.
Launch, VIEW page. Note Brightness. Drag it somewhere else in one move
and let go. Wait a second. Press ⌘Z (Ctrl+Z does the same). *Pass:*
Brightness is back where it was, nothing else moved, and the footer says
"undid Brightness … → …" for a few seconds. ⌘⇧Z: it goes forward again
("redid …"). Now drag Brightness, wait a second, drag Speed, wait, press
⌘Z twice: Speed comes back first, then Brightness. Change a route's depth
on the ROUTING page and ⌘Z: it comes back. Click in a text field (a
macro's label) and press ⌘Z there: only the text changes. With nothing
left the footer says "nothing to undo". *Fail:* nothing comes back → the
tick is not running (`app.frame`, `Host.undo`) or the key rows are
missing (`routing.LOOP_KEY_ROWS`; ROUTING page, session keys); two
presses needed for one drag → the settle time (`undo.SETTLE_S`); ⌘⇧Z
undoes instead of redoing → the chord rule in `Router.keys`; no footer
line → `Panel._footer`.

**49. Undo takes back one knob turn on the desk (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_undo.py::test_a_knob_turn_on_the_desk_is_one_step tests/test_undo.py::test_undo_of_a_slider_does_not_rerun_a_load`.
APC40 in, F5 (TRIP). Turn D1 (the effect mix) from where it is to the
other end in one sweep. Wait a second. ⌘Z. *Pass:* the mix and D1's ring
are back; the next turn of D1 carries on from the ring, no jump. Latch
SHIFT, move S1 (SUB's drive) a little, wait, ⌘Z: the drive is back,
SHIFT is still lit, and S1 does nothing until it passes the value again
(pickup). *Fail:* SHIFT dropped or every fader lost its hold → the
restore ran a desk replacement (`Undo._restore`, `Bindings.set_desk`'s
`load`); the ring not following → `MidiIO.feedback`.

**50. Undo after an F-key load (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_undo.py::test_a_preset_load_is_one_step_by_every_road tests/test_undo.py::test_undo_of_a_load_puts_back_the_values_the_routes_the_desk_the_macros_and_the_name tests/test_undo.py::test_save_after_undoing_a_load_writes_the_earlier_preset`.
F1 (TUMBLE). Change three things (brightness, the shape, switch faces
on) so the preset's dot is lit. F5 (TRIP). ⌘Z, once. *Pass:* the look is
TUMBLE with your three changes, the PRESETS page says TUMBLE with its dot
lit, F1's button is lit, the ROUTING page shows TUMBLE's routes and
desk, and the footer says "undid load TRIP". ⌘⇧Z: TRIP again, clean. ⌘Z
again, then press F5 by hand: redo is gone (a new action clears it).
Repeat the load from the PRESETS list, and with QUANT (next preset): one
⌘Z each. *Fail:* the look back but the name still TRIP → the marks
(`library.Marks`, `push(load=True)` in `Presets.load_doc`); two presses
for one load → a second push in the same action; routes not back →
`Bindings.set_routes` in the restore.

**51. Undo after a Learn, and after an Unbind (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_learn.py::test_a_learn_is_one_undo_step tests/test_midi.py::test_an_unbind_is_one_undo_step tests/test_ui_routing.py::test_a_route_delete_and_a_replace_are_undo_steps`.
F5 (TRIP), ROUTING page. Right-click Brightness → Learn, turn D3. The
DESK section shows "D3 view.bright" and D3's old param is gone from it.
⌘Z. *Pass:* D3 drives what it drove before, the row is back, the
footer says "undid learn view.bright", the preset's dot is as it was.
Right-click a param a desk knob drives → Unbind; its ring goes dark; ⌘Z:
the row and the ring are back. Delete a route with its ×; ⌘Z: it is back
with its depth and its gate. `ls -l ~/Hyperspace/presets` before and
after: no file's time moved. *Fail:* a row not back → the push before
the edit (`MidiIO._learned`, `MidiIO.unbind`, `ui_routing.page`); the
ring staying dark → `redraw_serial` in `set_desk(load=False)`.

**52. A hand moving makes no undo step (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_undo.py::test_a_performer_moving_makes_no_step`.
Camera and box on, F1 (TUMBLE). On the VIEW page drag Brightness and
wait a second. Now play: both hands in the box for half a minute, in and
out several times, the music on. Press ⌘Z once. *Pass:* Brightness goes
back: the one thing you did by hand. Nothing a hand, a band or an LFO
moved made a step. *Fail:* the footer says "undid Speed …" (or any param
a hand route drives) with values that differ only in the last digits →
the tolerance in the fingerprint (`undo.REL_TOL`); it names a
`rot.phase` or the BPM → `undo.watched`.

**53. A saved-over or deleted preset is in the trash (plan 15 WP1).**
Headless: `uv run pytest -q tests/test_library.py -k trash`.
PRESETS page. Load a preset of yours (make one with "as…" if you have
none: `CHECK 53`). Change the brightness; press **save**. Then open the
preset list and press × beside it. *Pass:* `ls ~/Hyperspace/trash/presets/`
shows two files, `check-53.<date>-<time>.json`, the first holding the
look before the save and the second the look that was deleted; copying
one back into `~/Hyperspace/presets/` as `check-53.json` brings the
preset back into the list within a couple of seconds. Press save twice with no change in between:
no new file in the trash. The PRESETS page's "more" lists no module
called "trash". *Fail:* nothing in the trash → `library.to_trash` in
`Library.save_as` / `Library.delete`; a "trash" strip under "more" →
`Library.groups`.

**54. Home, from any preset, on either layer (plan 15 WP2, decision 27).**
Headless: `uv run pytest -q tests/test_presets.py::test_home_loads_what_the_show_starts_on tests/test_desk.py::test_overdub_is_home_on_both_layers_and_is_lit`.
The party show; the PRESETS page reads "starts on / home ▾ TUMBLE".
OVERDUB (B11, beside METRONOME) is lit. F5 (TRIP), change a few things.
Press OVERDUB. *Pass:* TUMBLE is up, its desk lit. ⌘Z: TRIP with your
changes is back. F7, latch SHIFT, press OVERDUB: TUMBLE again, and SHIFT
has dropped (a load drops to the preset layer). F3, then fn+← on the
laptop: TUMBLE. Set "starts on" to — none: OVERDUB goes dark, and
pressing it loads nothing and the footer says the show names no "starts
on" preset; set it back to TUMBLE. Right-click any control → Learn, press
OVERDUB: refused ("B11 (OVERDUB) is invariant"). *Fail:* OVERDUB dark or
dead → its row (`apc40.DEFAULT_MAP`; in your `bindings.json` after check
57); doing something else under SHIFT → the row has a layer; fn+←
nothing → `key:HOME` in `routing.LOOP_KEY_ROWS`.

**55. The crossfader is the master dim (plan 15 WP3, decision 28).**
Headless: `uv run pytest -q tests/test_render.py -k dim tests/test_midi.py::test_the_crossfader_dims_with_soft_pickup tests/test_desk.py::test_the_crossfader_keeps_its_hold_across_a_preset_load`.
Quit. Push the crossfader hard left. Launch. *Pass (a), starts bright:*
the picture is at full brightness, and the OUTPUT page's Master dim reads
100%. *(b), cannot dim by accident:* nudge the crossfader a little from
the left: nothing happens. *(c), takes hold at the value:* slide it all
the way right, then back left: from the right end it has the picture,
which dims smoothly to **black** at the left, the footer reading
"dim …%"; back right, full. *(d), everything dims:* with F5 (TRIP), the
look-back on (F4) and the ghost hands on, at half way the shape, the
effects, the trail and the hands are all half as bright; on the glass
the ground stays black, never grey, and nothing behind shows through.
*(e), survives a load:* leave it at half; press F1, F5, OVERDUB: the
picture stays at half through each; the next move of the crossfader
carries on from half with no jump. *(f), both layers:* latch SHIFT: the
crossfader still dims. *(g):* quit at half, relaunch: full again. *Fail:*
dark at launch → `output.dim` is being saved or seeded (`Output.register`,
`persist`); right is black → the fader's direction (the row is `abs`; say
so, it is one line); a jump when first touched → pickup on the row
(`MidiIO._apply`); the hands or an effect not dimming → the pass is not
last (`Renderer._draw_frame`); the desktop showing through on the glass →
the opaque blend in `Renderer.dim_pass`; a preset moving it → a preset or
show landing a rig param.

**56. A hold on the clip-stop row saves a new preset; a tap does not (plan 15 WP4, decision 29).**
Headless: `uv run pytest -q tests/test_midi.py -k "hold or tap or bar" tests/test_presets.py -k "save_new or new_slot" tests/test_library.py::test_next_name_counts_on_from_a_trailing_number`.
Make room first: PRESETS page, right-click F8's button → **clear slot**
(F8 reads "—"; NOITA is still in the preset list). F5 (TRIP); change the
look. Tap any clip-stop button, quickly. *Pass (a):* the row lights
while your finger is down and nothing else happens: no new preset in the
list, no file in `~/Hyperspace/presets`. *(b):* hold any clip-stop
button. After a little over half a second the whole row and pad 8 of
clip row 1 blink; let go. F8's button reads **TRIP 2** and is lit, the
PRESETS strip says TRIP 2 with no dot, the footer says "saved TRIP 2 →
F8", and `~/Hyperspace/presets/trip-2.json` exists. *(c), the new slot
loads from the desk:* press pad 1 (TUMBLE), then pad 8: your look is
back. *(d), it never overwrites:* change the look, hold the row again
(a different button of it): the footer says "saved TRIP 3 — the bank is
full: it is in the preset list"; the row blinks and no pad does; TRIP 2
is unchanged (load it). *(e), one bar:* lay two fingers on the row and
hold: one new preset, not two; keep holding for five seconds: still one.
*(f):* latch SHIFT and hold the row: it saves the same way. *(g):*
right-click F8 → **put preset here…** → NOITA: F8 is NOITA again, and
TRIP 2 and TRIP 3 are still in the list. Plain **save** on the panel
still writes over the loaded preset (check 53). *Fail:* a tap saving →
the hold time (`midi.HOLD_S`, `MidiIO._handle`); a save into a taken slot
or over a file → `Project.next_empty`, `library.next_name`; no blink →
`apc40.blink_of` and the blink in `MidiIO.feedback` (if the clip-stop
LEDs never light at all on this device, note it: the save still works
and the pad's blink is the sign); two presets from one hold → the bar
rule in `MidiIO.poll`; the row doing nothing → its rows (`apc40.DEFAULT_MAP`;
your `bindings.json` after check 57).

**57. The first launch brings your `bindings.json` up to date, with a backup (plan 15 WP2–WP4).**
Headless: `uv run pytest -q tests/test_routing.py -k "older_file or old_crossfader"`.
Before the first launch of this build, `ls -la ~/Hyperspace`. Launch and
read stderr. *Pass:* one `backup:` line naming `bindings.json.bak-v3`
(or a dated name if you already had one), and one line per change: the
crossfader's row moved from `overlay.bg` to `output.dim`; rows added for
OVERDUB, the eight clip-stop buttons, Home, and the four undo keys. The
ROUTING page's session section lists X → `output.dim`, B11 →
`preset.home`, and G6·1–G6·8 → `preset.save_new  hold` under "invariant
· both layers". A crossfader, OVERDUB or clip-stop row you had changed
by hand is left as you had it (and that control then does what you set,
not this plan's job). Launch again: stderr says nothing and no file's
time moves. Then load each preset you saved on the night: if one had
learned a control onto OVERDUB or a clip-stop button, the ROUTING head
says "desk: dropped … that control is invariant", and that row is gone
from the preset when you next save it (the old file goes to the trash).
*Fail:* no backup → `routing.backup` in `Bindings.load`; a row of yours
replaced → `routing.remap_factory` (it may only swap the exact factory
row); the notes every launch → the remap is not finding its own rows.
