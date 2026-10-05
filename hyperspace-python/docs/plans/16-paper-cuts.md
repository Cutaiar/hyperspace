# Plan 16 — Paper cuts: five small fixes with no new knob

**From the Oct 3–4 session at the machine** (roadmap
[`15-21-roadmap.md`](15-21-roadmap.md) §4, "Plan 16"). Five things that
were each hit that night and need no decision from the owner: the cheat
sheet covering the control window at launch, an effect chip that cannot
be opened without switching the effect, an effect's faders doing nothing
with no word why, both windows opening in the same place every launch,
and an instance count that cannot reach zero — plus three places where
the code and its own comments had drifted apart.

Written 2026-10-04 against `finish-line` 61d037b, by reading the code and
running two headless probes (the numbers marked *measured* below). **Plan
15 is being built at the same time and lands first**; it is not in the
code this plan cites. Where a work package edits a file plan 15 also
edits, the package says so under "re-read": the build agent opens the
file as it stands after plan 15 before changing it.

The plan adds **no registry param, no page and no menu item** (§3). It
adds one config key and one file in the home folder.

## 1. What the owner hit, and what it is

| # | The owner saw | What it is in the code | Where the roadmap's wording and the code differ |
|---|---|---|---|
| 1 | The cheat sheet is in the way at every launch. | `Panel.__init__` sets `self.cheatsheet = True` (`ui.py:363`); `Panel._draw` draws `_draw_cheatsheet()` while it is true (`ui.py:967`), a 28-row window pinned bottom-left. The desk diagram is its own switch, `self.desk = True` (`ui.py:364`), and `ui_desk.diagram` sits above the sheet only while the sheet shows (`below = … if panel.cheatsheet else 0.0`, `ui_desk.py:198`), so with the sheet off the desk drops to the bottom-left corner on its own. Three roads toggle the sheet, all through the one param `ui.cheatsheet`: the key row `key:SLASH` (`routing.py:586`), the pad's MENU (`routing.py:605`) and the APC40's DETAIL button (`apc40.py:427`); the SYSTEM page has its checkbox (`ui.py:1314`). | None. (The sheet prints the key as "H / ?"; the table row is `SLASH`. Same key.) |
| 2 | Clicking an effect's chip to look at its faders switches the effect on or off. Moving an effect in the order changed which effect was open. | One widget does both jobs: `ui_fx.page` draws each chip with `panel._lit_button("fx.<name>.on", …)` (`ui_fx.py:65`), which toggles the param on every click (`Panel._lit_button`, `ui.py:813–814`), and then sets `fx.select` to the chip's index (`ui_fx.py:67`). The selection is an **index**: `FxState.sel` (`fx.py:184`), read by `FxState.selected()` as `names()[sel]` (`fx.py:279`), where `names()` is every effect sorted by `(order, name)` (`fx.py:268`). Anything that changes an `order` re-sorts the list under the index: the order slider in the open strip (`ui_fx.py:90`) moves the strip to another effect *while it is being dragged*, and a preset load (which lands every `fx.*.order`) does the same. | The roadmap offers "a lit corner or the strip's 'on'" as the toggle. The strip's "on" check already exists (`ui_fx.py:82`); what is missing is a chip click that does not toggle. There are no "reorder clicks" today: reordering is the order slider. |
| 3 | An effect's faders do nothing and the page does not say why. | With `fx.<name>.on` off the strip draws exactly as when it is on (`ui_fx.py:72–94`). The only sign is the chip not being red and the status line at the top of the page, which lists what is running (`ui_fx.py:39–42`). The same silence covers three more cases `FxState.chain()` drops an effect for (`fx.py:272–277`): the chain bypassed (`fx.on` off), `fx.mix` at 0, the effect's own mix at 0. | The roadmap names only "off". The other three are the same finding and cost one line of text; WP3 covers all four. |
| 4 | Both windows open on the laptop screen in the same spot every launch; the render has to be dragged to the projector each time. | `app._windows` puts the render window at the primary screen's work area + 16 px and the control window flush right on the same screen (`app.py:172–178`). Nothing reads a position from the config and nothing is remembered. `[output] monitor` exists (`config.py:102`) but means "the screen fullscreen and overlay cover" (`overlay.Output._target_monitor`, `overlay.py:333`), seeded into the `output.monitor` param by `app._make_output` (`app.py:195`); it does not move the window at launch. `Output` keeps the windowed rect only in memory (`_saved_rect`, `overlay.py:190, 281`). | "`[output]` config for which monitor each window opens on": one of the two keys already exists with a narrower meaning; WP4 widens it rather than adding a second. No `output.*` param holds a position, so placement is config and a file, not params. |
| 5a | "Instances to zero": no way to have nothing drawn. | Two floors. The param: `view.instances` is `lo=1, hi=100, integer=True`, no taper (`params.py:768–769`). The renderer: `n_inst = max(1, int(s.instances))` (`render.py:527`). *Measured:* a `ViewState` forced to `instances = 0` renders the same picture, bit for bit, as `instances = 1`. | The orchestrator's brief asks whether 0 would divide by zero or draw an empty buffer today. Neither: it is clamped to one copy. There is no taper to change; the range is linear. |
| 5b | (sweep) `dream.layer` can be owned by a performer. | `dream.layer` is a plain enum with no flags (`params.py:927`), so it is modulatable. Changing the layer makes the worker load another trunk (`DreamWorker._ensure_net`, `dream.py:452`). Its two neighbours that also rebuild things are already shut: `dream.gap` (`params.py:909`) and `dream.res` (`params.py:914`). `tests/test_lookback.py::test_dream_params_declared` asserts that every dream param except those two **is** modulatable, so it pins today's behaviour. No factory file routes onto it (grep of `hyperspace/library/`: four files set its value, none has a row targeting it). | Plan 12 §2's sentence ("`every`, `res` and `layer` rebuild things; never routed", `12-presets.md:72`) describes how the party presets were composed. It was never a rule in code for `layer`. |
| 5c | (sweep) The `ui_presets.py` docstring contradicts the code. | Lines 10–11 say "save overwrites the current preset — disabled for a factory one, which can only be saved *as* something". The code disables save only when nothing is loaded (`imgui.begin_disabled(cur is None)`, `ui_presets.py:216`) and its tooltip says a factory one is "saved as your own copy of it" (`ui_presets.py:221–223`; `Library.overwrite`, `library.py:1210`). The same docstring says so itself three lines later (lines 14–15). | None. |
| 5d | (sweep) The `preset.py` comment says `party-noita` follows a rule it does not follow. | The comment over the three effect presets says "Plan 12's rules hold (tests/test_plan12_presets.py sweeps them)" (`preset.py:581–582`). Plan 12 §2 names `fx.warp.drift` and `fx.tripcolour.pulse` as rate hazards and says "No hand touches any of those" (`12-presets.md:59–62`); NOITA's routes put a hand on both (`preset.py:692–693`). No test sweeps a rate rule. | The comment does not name the rate rule; it claims all of plan 12's rules by reference. The owner has since said rate-type params under a hand are allowed (roadmap §7), so the claim is reworded and the two rows stay. |

## 2. Work packages

| WP | What | Size | Needs |
|---|---|---|---|
| 1 | The cheat sheet off at launch | S | — |
| 2 | An FX chip click selects; selection by effect name | S | — |
| 3 | An effect that is not running says why, and offers "turn on" | S | **WP2** (both edit `ui_fx.py`; WP3 stacks on WP2's branch) |
| 4 | Window placement at launch: config and a remembered file | S | — |
| 5 | Instances to zero; `dream.layer` not modulatable; two comments | S | — |
| 6 | Docs and hand checks | S | last |

WP1, WP2, WP4 and WP5 run at once. WP3 starts when WP2's PR is up. WP6
runs last and is **the only package that edits the shared documents**:
`docs/ARCHITECTURE.md`, `docs/ENGINEERING.md`, `docs/DECISIONS.md`,
`docs/DECISION-REGISTER.md`, `docs/plans/11-hand-checks.md`,
`docs/plans/README.md` and this file's "As built". WP1–WP5 each leave a
three-line note in their PR body saying what the documents should say;
they do not open those files.

One PR per package on `plan-16-integration`, each with a demo (decision
30). Every agent runs with `HYPERSPACE_HOME` at a temp folder.

*As built:* PRs #89 (WP1), #84 (WP2), #86 (WP3), #85 (WP4), #90 (WP5).
A seventh package was added after them, **WP7 — four small fixes found
while building plans 15 and 16** (PR #92): a footer line said twice, the
dirty dot lit by round-off, the desk diagram's one-frame jump, and a
config screen that is not a number. It is described in §7 only.

### WP1 — The cheat sheet off at launch

**Owns:** `hyperspace/ui.py` (`Panel.__init__`, `_register_panel_params`
only), `tests/test_ui_shell.py`.
**Must not touch:** `ui.CHEATSHEET`, `routing.py`, `apc40.py`,
`ui_desk.py`.
**Re-read (plan 15 edits it):** `ui.py` — plan 15 adds rows to
`CHEATSHEET` for its new keys. WP1 changes two other places in the file.

Behaviour:

1. `Panel.__init__`: `self.cheatsheet = False`. `self.desk` stays `True`.
2. The three roads and the checkbox are unchanged: `/`, the pad's MENU and
   the APC40's DETAIL button toggle `ui.cheatsheet`; DETAIL's LED, which
   shows the param, is dark at launch.
3. `ui.cheatsheet` gains a tip (it has none today), so the SYSTEM page's
   checkbox says how to get the sheet back: "Keys, pad and desk legend,
   bottom-left of this window. / toggles it."
4. The desk diagram needs no change: with the sheet off it is drawn at
   the bottom-left corner (`ui_desk.diagram`). *As built:* true of its
   resting place, but on the first frame the sheet shows the diagram was
   placed from a height the sheet did not yet have, and jumped one frame
   later. WP7 fixed it in `Panel._draw_cheatsheet` (§7).

Not remembered across launches and not in the config: it is off every
launch (§3).

### WP2 — A chip click selects; selection by name

**Owns:** `hyperspace/fx.py` (`FxState`, `declare`'s `fx.select` only),
`hyperspace/ui_fx.py`, `tests/test_fx.py`.
**Must not touch:** `ui.py` (the page uses `ui.lit_chip` and the panel's
existing helpers; `Panel._lit_button` keeps toggling for the plane keys),
`FxChain`, any `.glsl`.
**Re-read:** nothing plan 15 edits. If plan 15's `undo.py` fingerprints
params that are not persisted, `fx.select` must be left out of it: a
selection is not an edit. Check, and say so in the PR.

Contract in `fx.py` (this is what plan 20's chain view drives):

```python
class FxState:
    sel_name: str | None      # the open effect's name; replaces `sel` (an index)

    def select(self, name: str | None) -> None:
        """Open `name`'s strip. A name with no spec is ignored; None means
        'whatever is first'. Writes nothing but sel_name."""

    def selected(self) -> str | None:
        """sel_name while it has a spec; else the first of names(); None
        with no effects. Never writes — a file that goes away and comes
        back is open again."""
```

- `FxState.sel` is deleted. `selected()` reads
  `getattr(self, "sel_name", None)`, because a hot reload re-classes the
  live `FxState` without running `__init__` (`hotreload.py:24`).
- `fx.select` keeps its id, label, `persist=False`, `modulatable=False`
  and choices. It becomes a view: get is the index of `selected()` in
  `names()` (0 with none), set is `select(names()[i])` with `i` clamped.
  A desk row or test that writes an index still works; the index is no
  longer what is stored.
- Nothing else names the selection: `sel_name` is not saved in a preset,
  a show or any file.

The page (`ui_fx.page`), per chip:

- **The body selects and only selects**: `fx.select(name)`. It never
  writes `fx.<name>.on`.
- **The LED toggles and only toggles**: a square zone the height of the
  chip at its left end, its own item with its own imgui id
  (`##led.fx.<name>.on`), drawn as a filled dot while the effect is on
  and a ring while it is off. Its hover reads "on — click to switch off"
  / "off — click to switch on". (Fork F1.)
- The chip is still solid red while its effect is on. The **selected**
  chip also carries a 2 px outline in `ui.TEXT`, so "open" and "on" read
  apart from a step back; today selection is only a text colour.
  *As built:* the outline goes round both parts, LED and name, and the
  chips are **three to a row**, not four: with the LED's square taken
  out of each chip, four to a row cut seven of the twelve names short
  (§7, WP2; register row 45).
- Right-click on either part opens the `fx.<name>.on` menu as today
  (`panel._ctx`, with a `key` so the two items do not share a popup id);
  the learn frame and the modulation dot stay on the body.
- The strip's own "on" check stays.
- Suggested build, not required: two adjacent items with no spacing (a
  square `lit_chip` for the LED, then the name chip) rather than one item
  over another, which needs imgui's overlap flags.

What "never changes which effect is open" means, each a test:
dragging any effect's order slider; a preset, module-preset or show
load; an effect file added or removed (unless it was the open one, which
falls back to the first and reopens when the file returns).

### WP3 — An effect that is not running says why

**Owns:** `hyperspace/ui_fx.py`, `tests/test_fx.py`. Stacks on WP2.
**Must not touch:** `fx.py`, `ui.py`.

Contract in `ui_fx.py`:

```python
def why_idle(fx, name: str) -> str | None:
    """Why `name` is not in fx.chain(), first reason only; None while it runs.
    "off" | "bypassed" | "fx mix 0" | "mix 0"."""
```

checked in that order against `fx.values[name]["on"]`, `fx.on`, `fx.mix`
and `fx.values[name]["mix"]`: the four conditions of `FxState.chain()`.

The open strip, when `why_idle` is not None, draws **one line** between
the effect's tip and its "on" row:

| Reason | Line (in `ui.WARN`) | Chip beside it |
|---|---|---|
| `off` | "off — nothing below shows until it is on" | **turn on** → `reg["fx.<name>.on"].set(True)` |
| `bypassed` | "the whole stack is bypassed" | **effects on** → `reg["fx.on"].set(True)` |
| `fx mix 0` | "FX mix is at 0" | none (the fader is at the top of the page) |
| `mix 0` | "its mix is at 0" | none (the fader is the next row) |

Under that line the strip's controls (mix, speed, blend, order, the
uniform rows) are drawn **dimmed but live**: `imgui.push_style_var(alpha
≈ 0.45)`, not `begin_disabled`. An effect can be set up dark and then
switched on, right-click Learn still works on every row, and the order
slider still moves it. The "on" check itself is not dimmed. (Fork F2.)

*As built:* the dimming is a **veil** — a rect of the window's ground
drawn over the rows (`ui_fx._dim`) — not a pushed style alpha, which
would also have dimmed each row's right-click menu and the blend combo's
list. At "its mix is at 0" the effect's own mix fader is left undimmed:
it is the control the line names (§7, WP3; register row 46).

Both chips write a base through `Param.set`, as the check does, so each
is one undo step under plan 15 with no explicit `undo.push`.

Room: *measured* on `finish-line`, the tightest strip at the control size
is `zoomblur` with 110 px to spare (`fractals` 126); a row is 35 px. One
more line fits. The fit test is extended to draw the tightest strip with
the line showing. *As built:* with WP2's fourth chip row, `zoomblur` has
52 px to spare with the line showing.

### WP4 — Window placement at launch

**Owns:** new `hyperspace/placement.py`, `hyperspace/app.py` (`_windows`,
the two exits in `main` and `_restart`), `hyperspace/config.py`
(`DEFAULTS["output"]` and the `[output]` docstring block),
`hyperspace/overlay.py` (one read-only method), `hyperspace/hotreload.py`
(one entry in `MODULES`), new `tests/test_placement.py`,
`tests/test_app_boundary.py`, `tests/test_overlay.py`.
**Must not touch:** `app.frame` and `Host` (the frame order is pinned by
`test_the_frame_runs_in_the_documented_order`), `params.py`, `ui.py`.
**Re-read (plan 15 edits them):** `app.py` — plan 15 adds one call in the
frame loop; WP4 edits `_windows` and the exits. `overlay.py` — plan 15
WP3 takes the crossfader off `overlay.bg`; WP4 adds a method to `Output`
and changes nothing else there.

#### Config

```toml
[output]
monitor = -1           # which screen the RENDER window opens on, and the one
                       # fullscreen covers: a screen index, or -1 = where it
                       # was last time (else the primary screen)
control_monitor = -1   # which screen the CONTROL window opens on: an index,
                       # or -1 = where it was last time (else the primary)
```

- `monitor` exists; its default and its old meaning stand (it still seeds
  `output.monitor`, `app._make_output`). New: at 0 or above the render
  window is also *created* on that screen.
- `control_monitor` is new, default −1, in `config.DEFAULTS["output"]`.
- An index with no such screen: the key is treated as −1 and a note is
  appended to `cfg["notes"]` and printed on stderr ("config: [output]
  monitor = 2, but 2 screens are connected (0–1) — using the last
  position"). `panel.config_notes` already shows `cfg["notes"]` on the
  SYSTEM page (`app.py:757`), so `ui.py` is not edited. *As built:* a
  value that is not a number at all (`monitor = "left"`) is −1 with a
  note too, written by `config.load`; and after the note the index is −1
  in the config for the rest of the run, so `Output.monitor` does not
  keep a screen that is not there (WP7, §7).

How the keys extend to plan 21's list of outputs: `[output]` stays the
table of rig-wide settings (`overlay`, `control_monitor`), and the outputs
become an array of tables inside it,

```toml
[[output.screens]]     # plan 21; not built here
monitor = 1
fullscreen = true
```

with today's scalar `monitor` / `fullscreen` read as a one-entry list,
the way `config.load` already folds the old `[overlay]` section under
`[output]`. Nothing WP4 adds has to be renamed.

#### The remembered file

`<home>/windows.json`, beside `config.toml` and `last_show`:

```json
{
 "schema": "hyperspace.windows/1",
 "control": {"x": 2100, "y": 60, "w": 960, "h": 900, "screen": "Built-in Retina Display"},
 "render": [
  {"x": 1744, "y": 41, "w": 1280, "h": 820, "screen": "DELL U2720Q"}
 ]
}
```

- `x, y, w, h` are GLFW screen coordinates of the window's content area
  (`glfw.get_window_pos` / `get_window_size`): the **windowed** rect.
- `render` is a list with one entry today. Plan 21's second output is a
  second entry; the schema does not change.
- `screen` is the name of the screen the rect's centre was on. It is
  written for the stderr note and for plan 21; placement is decided by
  geometry alone.
- Machine-specific: plan 19's `.gitignore` for the home should list it
  with `last_show` (a note for plan 19, not work here).

#### Contract (`placement.py`: no GL, no imgui, imports nothing from the package; `glfw` is passed in)

```python
FILE = "windows.json"
SCHEMA = "hyperspace.windows/1"
MIN_VISIBLE = (120, 80)        # px of a window that must be on a screen
MARGIN = 16                    # the default spot's inset, as today

@dataclass(frozen=True)
class Screen:                  # one monitor's work area
    name: str
    x: int; y: int; w: int; h: int

Rect = tuple[int, int, int, int]            # x, y, w, h

def screens(glfw) -> list[Screen]: ...      # glfw.get_monitors() order; [] when there are none
def load(home: Path) -> dict: ...           # {} when missing, unreadable, or another schema
def save(home: Path, control: Rect | None, render: list[Rect | None],
         scr: list[Screen]) -> None: ...    # atomic; a None keeps that window's old entry;
                                            # a failed write costs only the memory
def usable(rect: Rect, scr: list[Screen]) -> bool: ...
def default_rect(kind: str, size: tuple[int, int], s: Screen) -> Rect: ...
def place(kind: str, size: tuple[int, int], scr: list[Screen],
          monitor: int, remembered: dict | None) -> tuple[Rect, str]: ...
                                            # kind: "render" | "control"; returns (rect, note or "")
```

`usable(rect, scr)`: some screen's work area overlaps the rect by at
least `MIN_VISIBLE`, and the rect's top edge is inside that work area
(the title bar can be reached).

`default_rect`: today's spots on the given screen. Render: top-left +
`MARGIN`. Control: flush right − `MARGIN`, top + `MARGIN`. The size is
clipped to the work area. *As built:* **the size is not clipped**: a
clipped size would be written at the quit and follow the window to a
bigger screen, and a first launch would differ from before on a small
screen. Only a remembered size is clipped, in `place` (§7, WP4).

`place`, in order (fork F4 is the order of 1 and 2):

1. `monitor ≥ 0` and that screen exists: the remembered rect if it is
   `usable` **and its centre is on that screen**; else `default_rect` on
   that screen.
2. `monitor = −1` (or no such screen, with the note): the remembered rect
   if `usable`; else `default_rect` on the primary screen (the first).
3. A remembered size is kept, clipped to the screen it lands on, never
   under 320 × 240.

So, case by case:

| Situation | What opens |
|---|---|
| First launch, no file, default config | Exactly today's placement and sizes. |
| Both windows dragged, quit, relaunch | Both where they were, at the size they were. |
| The render was on the projector; the projector is unplugged | Its rect is on no screen → the default spot on the primary screen; stderr says which screen it was last on. |
| The file is hand-edited to nonsense, or the rect is off every screen | Ignored; default spot. |
| `monitor = 1`, last position on screen 0 | The default spot on screen 1 (config wins). |
| `monitor = 1`, last position on screen 1 | The last position. |
| `fullscreen = true`, `monitor = −1` | The window is created at its last position; `Output.apply` then takes it fullscreen on the screen it is on (`_target_monitor`'s "follow window"). Drag the render to the projector once, and every later launch is fullscreen there. |
| Quit while fullscreen or in overlay | The **windowed** rect is saved (what `Output` would restore), never the cover of the screen. Whether a launch is fullscreen is the config's `fullscreen`, never remembered (fork F6). |
| Quit with a window minimised | That window's entry is left as it was. |
| `HYPERSPACE_FRAMES` smoke run | Reads and writes like any launch (it is a launch). |

#### The edits

- `app._windows(overlay=False, cfg=None, home=None)`: asks
  `placement.screens(glfw)`; with no screens it sets no position (as
  today with no primary monitor); otherwise it loads the file, calls
  `place` for each window with `cfg["output"]["monitor"]` /
  `["control_monitor"]`, creates each window at its rect's size and sets
  its position. Notes go to `cfg["notes"]` and stderr. `main` passes
  `cfg` and the home folder (`hyperspace.library.home()`, the folder
  `config.load` has just ensured; `main`'s own `library` is the
  `Library` object, made later); the one-argument call the existing
  test makes keeps working.
- `overlay.Output.windowed_rect() -> Rect | None`: the window's rect
  while the mode is `window`, `_saved_rect` otherwise, `None` with no
  backend. Read-only.
- Saving: one helper in `app.py`, called at the end of `main` before
  `glfw.terminate()` and in `_restart` before `impl.shutdown`, inside
  `_quiet`. Control: its pos and size unless iconified. Render:
  `output.windowed_rect()` unless iconified. Not saved while running
  (fork F5).
- `hotreload.MODULES` gains `"placement"` among the leaves
  (`tests/test_hotreload.py` holds that every module but the four cold
  ones is listed).

### WP5 — Instances to zero; `dream.layer`; two comments

**Owns:** `hyperspace/params.py` (the `view.instances` and `dream.layer`
declarations only), `hyperspace/render.py` (`Renderer.draw_scene` only),
`hyperspace/view.py` (one comment), `hyperspace/ui_presets.py` (the
module docstring only), `hyperspace/preset.py` (the comment at
`575–586` only), `tests/test_params.py`, `tests/test_render.py`,
`tests/test_lookback.py`, `tests/test_plan12_presets.py`.
**Must not touch:** any file under `hyperspace/library/`, `ui.py`,
`preset.py`'s route and value functions.
**Re-read (plan 15 edits them):** `params.py` (plan 15 adds
`preset.home` and `output.dim`), `render.py` (plan 15 adds the final dim
pass in `_draw_frame`; WP5 edits `draw_scene`), `ui_presets.py` (plan 15
changes the page; WP5 edits only the docstring's strip paragraph — and
should check that paragraph is still about the strip after plan 15).

**Instances.**

- `view.instances`: `lo=0`. Default stays 1 (`ViewState.instances`).
  `fmt` reads "0 · nothing drawn" at 0 and "N instance(s)" otherwise; the
  tip gains "0 draws nothing: the ground, the echoes and the effects
  carry on."
- `Renderer.draw_scene`: `n_inst = max(0, int(s.instances))`. At 0 it
  still clears to the ground, still sets the blend function and
  `self._face_verts = 0`, then draws no faces, lines or points and writes
  no vertex buffer. Everything after the scene pass runs as on any frame:
  the cover pass sees no face vertices, the look-back composites and
  captures (so existing echoes fade out over the empty scene), the FX
  chain runs (a generator such as plasma still paints), the ghost hands
  draw. At 1 the frame is bit-identical to today.
- What moves with the floor, all checked:
  - The slider on the VIEW page reads `p.lo` (`Panel._slider`), so it
    reaches 0 with no edit to `ui.py`; the grid-motion controls already
    hide below 2 (`ui.py:1120`).
  - Track knob 3 (`cc:0:50 → view.instances`, `abs`, in every factory
    desk) reaches 0 at the very bottom of its turn (fork F3).
  - The throw is 100 steps, not 99, so a performer's push lands a hair
    differently. *Measured* on `party-field` (base 9, right height
    pushes +0.6 from rest 0): hand at the bottom 9 → 9, a tenth up
    15 → 15, half 39 → 39, top 68 → **69**; hand gone, 9. No factory
    hand row can take the count below its base, because every height
    row pushes from rest 0. *As built:* a user's row can — one that
    pushes both ways (an LFO) on a count of 1 reaches 0 for part of its
    cycle (§7, WP5; register row 47).
  - `tests/test_params.py::test_raw_ranges_clamp_int_and_log` sets −5
    and expects 1, then steps 3 and expects 4: it becomes 0 and 3.
  - No factory preset file changes (they store the count, not the
    position), so `python -m hyperspace.preset` leaves the tree clean.
  - `Param.scale` refuses a range that reaches 0 (`params.py:414`);
    nothing calls `scale` on this param (only the camera zoom does,
    `app.py:410`).

**`dream.layer`**: `modulatable=False`, as `dream.gap` and `dream.res`.
It stays persisted, on the LOOKBACK page, and settable by a preset, the
panel and a desk row (scene-setters). A route onto it is a dormant row
(`routing.py:80`), its right-click menu reads "not modulatable"
(`ui_routing.ctx_item`), and it leaves the ROUTING page's target list
(`ui_routing.py:376`). `test_dream_params_declared` adds it to the
excepted ids.

**`ui_presets.py` docstring**: lines 9–15 become one true statement:
save writes over the current preset and is disabled only when none is
loaded; on a factory preset it writes your own copy (`Library.overwrite`
shadows the factory file, never touches it).

**`preset.py` comment** (`581–586`): "Plan 12's rules hold (… sweeps
them)" becomes the list of rules that do hold and are swept (six DOF, no
pinch, a push from the axis's rest, a still or absent hand is the scene),
then one sentence: NOITA puts a hand on two rate-type params
(`fx.tripcolour.pulse`, `fx.warp.drift`), which plan 12 §2 kept hands off
and the owner has since allowed (2026-10-04). The two rows at `692–693`
and `party-noita.json` are not touched.

### WP6 — Docs and hand checks

**Owns:** the shared documents listed above, and nothing under
`hyperspace/` or `tests/`.

- `11-hand-checks.md`: group L from this plan's appendix, with final
  numbers after plan 15's group K. Check 1's "the cheat sheet (`/`)
  names all seventeen rows" gains "press `/` first: it is off at
  launch". Check 26 gains a pointer to L4.
- `DECISIONS.md`: a row each for the sheet off at launch (UI), FX
  selection by name (UI), placement — config beats the remembered file,
  the file is `windows.json` (Library and persistence), `view.instances`
  floor 0 and `dream.layer` not modulatable (The control model). The
  2026-09-28 row on plan 12's presets gains "the rate rule holds for the
  five on F1–F5; the owner allowed rate-type params under a hand on
  2026-10-04 (NOITA has two)".
- `DECISION-REGISTER.md`: forks F1–F6 as built on the recommendation, for
  the owner to confirm or overturn (roadmap §7).
- `ARCHITECTURE.md`: the registry flags table's `modulatable` examples;
  the Host and Library rows (`placement.py`, `windows.json`); the UI row
  (sheet off at launch). `ENGINEERING.md` §2.5 (where the windows open)
  and the FX page paragraph.
- `plans/README.md`: a row for plan 16. This file's "As built".
- Plan 12's document is history and is not edited; its "n = 68" is 69
  since this plan, noted in "As built".

## 3. Parameter budget

"We don't want to drown in the number of parameters." Everything this
plan adds or removes:

| Thing | Kind | Replaces, or why nothing |
|---|---|---|
| — | registry params | **None added.** `fx.select` stays one param and becomes a view onto the name. `view.instances` and `dream.layer` change a bound and a flag. |
| `[output] control_monitor` | config key | New, default −1 = "do what the remembered file says". It is the only way to pin the control window to a screen, and a rig that never sets it never sees it. |
| `[output] monitor` | config key | **Not new**: the existing key also says where the render window opens, in place of a second key (`render_monitor`) that would have had to agree with it. |
| `<home>/windows.json` | file | New. It replaces dragging two windows at every launch. No setting turns it off: delete the file to forget. |
| `FxState.select` / `sel_name` | code | Replace `FxState.sel`. |
| The chip's LED | a click target | Replaces the chip body's toggle; the body's click now only selects. No new widget row. |
| "turn on" / "effects on" | two chips | Appear only on a strip that is not running; each writes a param that already has a control. |
| Cheat sheet at launch | nothing | A default changed. No "start with the sheet" setting: `/` is one key. |
| Menu items, pages | — | None. |

Considered and not added: a `[output] remember = false` switch (delete
the file instead); a config key for the sheet; a "blank" toggle beside
the instance count (the count's own 0 is the blank); remembered
fullscreen (the config key already says it).

## 4. What this plan does not change

The DECISIONS rows it leans on:

- **The render window has no imgui at all** (2026-09-18). Nothing in WP4
  draws on it; placement notes go to stderr and the SYSTEM page.
- **Two GLFW windows on one GL context** (2026-09-18) stands until plan
  21. WP4 moves windows; it creates no third one, and its file and keys
  are shaped for plan 21's list (WP4, "Config" and "The remembered
  file").
- **No page scrolls at the control size** (2026-09-26), held by
  `tests/test_ui_shell.py::test_every_page_fits_the_control_window` and
  `tests/test_fx.py::test_the_page_draws_and_fits`. WP2 keeps the chip
  grid's shape; WP3 adds one line, measured to fit. *As built:* WP2 did
  not keep the grid's shape — three chips to a row, so four rows where
  there were three; the page still fits (§7).
- **Overlay only when the config asks** (decision 21). Placement never
  sets a mode; an overlay or fullscreen window is remembered by its
  windowed rect.
- **Rig settings never persist in a preset and cannot be modulated**
  (`overlay.py`; `tests/test_overlay.py::test_rig_settings_never_persist_or_modulate`).
  Placement is not a param at all.
- **Scene-setters write the base** (plan 09 d.3). The LED, "turn on" and
  "effects on" are `Param.set` calls.
- **Any registry param is a modulation target, subject to its
  `modulatable` flag** (2026-09-18). WP5 uses the flag as it is used for
  `dream.gap` and `dream.res`.
- **A preset load replaces everything** (D2). It still lands every
  `fx.*.order`; it no longer moves the open strip, because the strip is
  not a value.
- **New effects are new `.glsl` files, not Python** (2026-09-26). The
  page still draws from the live `FxState`.
- **Plan 12's five presets** (2026-09-28 row) are not re-tuned;
  `party-field` gains one copy at the very top of the hand's reach.

## 5. Exit criteria

### Headless

`uv run pytest -q` green and `uv run ruff check` clean on
`plan-16-integration`, with these tests present. New unless marked.

**WP1** — `tests/test_ui_shell.py`
- `test_the_cheat_sheet_is_off_at_launch_and_the_desk_is_on`: a fresh
  `Panel` has `cheatsheet False`, `desk True`; a frame draws `##desk` and
  no `##cheatsheet`.
- `test_slash_still_toggles_the_cheat_sheet`: the factory table has
  `key:SLASH → ui.cheatsheet` (toggle); toggling the param draws the
  sheet on the next frame and hides it on the one after.
- `test_every_page_fits_the_control_window` (existing): still passes.
- `tests/test_ui_desk.py::test_the_diagram_draws_on_both_layers_and_hides`
  (existing): the desk with the sheet on and off.

**WP2** — `tests/test_fx.py`
- `test_selection_is_by_name_and_survives_a_reorder`: select an effect,
  move its `order` and another's through the registry; `selected()` is
  the same name; `fx.select` reads its new index.
- `test_selection_survives_a_preset_load`: load two `fx` module presets
  with different orders; the open effect's name does not change.
- `test_a_removed_effect_falls_back_and_comes_back`: on a temp effects
  folder, delete the open effect's file and poll: `selected()` is the
  first; restore the file: it is open again.
- `test_fx_select_is_a_view_onto_the_name`: setting an index selects
  that name; out of range clamps; still not persisted, not modulatable.
- `test_a_chip_click_selects_and_never_toggles`: a simulated click on a
  chip body opens its strip and leaves every `fx.*.on` as it was.
- `test_the_chips_led_toggles_and_never_selects`: a simulated click on
  the LED flips `fx.<name>.on` and leaves `selected()` as it was.
- `test_declare_makes_ordinary_params`, `test_the_page_draws_and_fits`,
  `test_the_page_has_no_conflicting_ids` (existing): still pass, the last
  now covering the LED's ids.

**WP3** — `tests/test_fx.py`
- `test_why_idle_names_the_first_reason`: the four reasons in order, and
  None for a running effect; it agrees with `FxState.chain()` for every
  effect in every state tried.
- `test_an_off_effects_strip_says_so_and_turn_on_switches_it_on`: the
  line is drawn; a simulated click on "turn on" sets the base and the
  line is gone next frame.
- `test_a_bypassed_stack_says_so_on_the_strip`: `fx.on` off, the effect
  on: the bypass line and "effects on".
- `test_the_idle_strips_controls_stay_live`: with the effect off, a
  slider write still lands and no `begin_disabled` wraps the rows.
- `test_the_page_fits_with_the_tightest_strip_idle`: every effect's
  strip in turn, switched off, at the control size: scroll range 0.

**WP4** — `tests/test_placement.py`
- `test_first_launch_places_as_before`: no file, default config, one
  screen: the two rects `app._windows` uses today.
- `test_a_remembered_rect_is_restored`: position and size.
- `test_a_rect_on_a_screen_that_is_gone_falls_back`: two screens saved,
  one connected: the default spot on the primary, and a note naming the
  missing screen.
- `test_an_off_screen_rect_falls_back`: overlap under `MIN_VISIBLE`, or a
  top edge above the work area.
- `test_a_config_monitor_beats_the_remembered_screen`, and
  `test_a_remembered_rect_on_the_configured_screen_is_kept`.
- `test_a_config_monitor_that_is_not_there_is_a_note`: treated as −1.
- `test_a_remembered_size_is_clipped_to_its_screen`.
- `test_save_round_trips_and_render_is_a_list`: the file's shape, schema
  string and one entry in `render`.
- `test_a_none_keeps_the_old_entry`: the minimised-window case.
- `test_a_bad_file_is_ignored` (not JSON, wrong schema, wrong types) and
  `test_an_unwritable_home_costs_only_the_memory`.
- `tests/test_overlay.py::test_windowed_rect_is_the_saved_rect_while_fullscreen_or_overlay`.
- `tests/test_app_boundary.py::test_the_windows_open_where_placement_says`
  (stubbed glfw: created at the placed size, positioned at the placed
  spot, the control window on `control_monitor`) and
  `::test_the_exits_save_the_windowed_rects` (quit and restart).
- `tests/test_app_boundary.py::test_the_render_window_is_transparent_only_when_the_config_asks`
  and `tests/test_hotreload.py` (existing): still pass.

**WP5**
- `tests/test_params.py::test_raw_ranges_clamp_int_and_log` (changed:
  the floor is 0) and `::test_instances_read_nothing_drawn_at_zero`.
- `tests/test_render.py::test_zero_instances_draws_only_the_ground`:
  points, lines and faces on, `instances = 0`: every pixel is the ground,
  `_face_verts == 0`, no raise, and the window is still the bound target.
- `tests/test_render.py::test_zero_instances_still_runs_the_look_back_and_the_effects`:
  with a generator effect on, the frame is not black; with the look-back
  on and the cover pass wanted, no raise.
- `tests/test_render.py::test_one_instance_is_the_frame_it_was`: bit
  equal to a frame rendered with the count forced through the old clamp.
- `tests/test_plan12_presets.py::test_no_factory_hand_row_blanks_the_scene`:
  every factory route onto `view.instances`, swept over its source's
  whole throw: the count never drops below the preset's base.
- `tests/test_plan12_presets.py::test_field_height_is_one_gesture_over_three_params`
  (existing): still passes at 69.
- `tests/test_lookback.py::test_dream_params_declared` (changed:
  `dream.layer` is not modulatable) and
  `::test_a_route_on_the_dream_layer_is_dormant`.
- The factory presets regenerate to the same bytes.

### At the machine

Group L, appendix A. Six checks, laptop first, about 20 minutes with the
projector.

## 6. Forks

None needs the owner before the build. Each is built on the
recommendation and logged in `DECISION-REGISTER.md` (WP6).

*As built:* all six were settled as recommended, by the orchestrator and
not by the owner. They are register rows **45** (F1, with three chips to
a row), **46** (F2, built as a veil), **47** (F3), **48** (F4, F5 and F6
together, "window placement") and **49** (`dream.layer` not performable,
which §6 did not list as a fork), each to confirm or overturn.

**F1. Where the on/off target sits on a chip.**

| Option | For | Against |
|---|---|---|
| (a) An LED zone at the chip's left end; the strip's "on" stays | Switch any effect without opening it, as today, in one click; the two targets are apart by position, which works on a trackpad | Four chips share the page's width; the LED takes a chip-height square of each and can be hit by mistake |
| (b) No toggle on the chip; only the strip's "on" | Nothing to mis-hit | Two clicks to switch an effect, and the page loses its "row of switches" |
| (c) Click selects, ⇧click toggles | No new target | Invisible; needs the keyboard at a party |

**Recommendation: (a).** To reverse: delete the LED item (b), a dozen
lines in `ui_fx.py`; `fx.py` is the same either way.

**F2. An idle strip's controls: dimmed and live, or disabled.**
Disabled is the stronger signal, but it stops an effect being set up
before it is switched on, and `begin_disabled` also blocks the
right-click menu, so nothing on an off effect could be learned.
**Recommendation: dimmed and live**, with the line and the chip carrying
the message. To reverse: swap the style push for `begin_disabled`, one
line.

**F3. Is zero reachable from the knob's bottom and the slider's left
end?**

| Option | For | Against |
|---|---|---|
| (a) Yes: the range is 0–100 | It is what was asked for: a hand on the knob takes the shape out, with echoes and effects carrying on. Nothing new to learn | A knob left at the bottom is a black render with no error. The readout says "0 · nothing drawn" |
| (b) The setters stop at 1; only a preset value or a typed number reaches 0 | No accidental black | Zero becomes a hidden state nobody can reach live, which was the ask |
| (c) A separate "blank" toggle | Explicit | A new param for what the count already says (§3) |

**Recommendation: (a).** No factory preset, desk value or hand row lands
on 0 (tested). To reverse: `lo=1` again and the clamp, two lines; a
preset saved at 0 then loads as 1.

**F4. Does the config or the remembered file win?**
(a) An explicit screen index in the config wins and the file fills in
only what the config leaves at −1; (b) the file always wins once it
exists. With (b) a key in `config.toml` silently stops working after the
first quit. **Recommendation: (a)**: the config is the rig's statement,
the file is the default when it is silent. To reverse: reorder two
branches in `placement.place`.

**F5. When the file is written.**
(a) On quit and on ⌘R; (b) also while running, a second after a window
stops moving. (b) survives a crash or a `kill`, but it needs a poll in
the frame loop, which plan 15 is editing and whose order a test pins.
**Recommendation: (a).** A crash costs one drag. To reverse: add the
poll later; the file and `save` do not change.

**F6. Is fullscreen remembered?**
No: `[output] fullscreen` says it, and `output.fullscreen` is a rig
setting that never persists (`overlay.py`). A launch that goes
fullscreen because the last quit did would be a second source of truth.
**Recommendation: not remembered**; the file holds the windowed rect
only. To reverse: one boolean in the file's render entry.

Noted, not a fork: the two config keys take a **screen index**, as
`monitor` does today. Indices move when a display is plugged in; the
remembered file, which places by geometry, is what makes that tolerable.
Accepting a name ("DELL") as well is one function in `placement.py` if
the rig turns out to need it.

## 7. As built

Written by WP6 from each PR's "As built" paragraph and its notes for the
documents, every statement checked against the code on
`plan-16-wp7-followups` (WP1–WP5 as merged into `plan-16-integration` at
8970f0a, 1169 tests; with WP7, 1178 pass, 1 skipped — the hands tape).
Where this section and §2 differ, this section is the code; §2 carries an
"*As built:*" note at each such place.

**What has been seen, and by whom.** Nothing here was tried by a person
at the rig: no key pressed, no chip clicked with a real mouse, no APC40
control moved, no window dragged to a projector. Three kinds of evidence
exist, and the entries below say which is which:

- *tests*: the named pytest nodes, on headless imgui (clicks are
  simulated mouse events on the real page), offscreen framebuffers, a
  stubbed GLFW and fake screens;
- *demos*: the scripts under `tools/`, each on a temp home of its own,
  with their output kept under `docs/plans/assets/16-paper-cuts/`
  (reported by the agent that built the package; the pictures are from a
  hidden window or an offscreen render, not the app on a screen);
- *seen in a scripted launch by the orchestrator*: the real app
  (`uv run hyperspace`) started against a temp home on a one-screen
  laptop, on `plan-16-integration` at 1169 tests, and driven from a
  script. What it saw: the control window launches with the cheat sheet
  off and the desk diagram on; `view.instances` set to 0 reads
  "0 · nothing drawn", and the `edit.undo` trigger brings the count
  back; the open effect stays `kaleido` through its order being changed
  to 99 and through a preset load; `ui.cheatsheet` toggles;
  `<home>/windows.json` is written at quit; `dream.layer` is not
  modulatable; no runtime error, and an empty stall log. That is a
  launch on a laptop with no desk, camera or second screen attached, not
  a session at the machine. It was run before WP7; WP7's four fixes were
  seen by tests and a headless transcript only.

Hand checks 58–63 (group L of `11-hand-checks.md`) are what the machine
still owes. Decision register rows 45–49 are the forks this plan's run
settled on its own recommendation.

### WP1 — The cheat sheet off at launch (PR #89, merged 491d540)

**Built.** `Panel.__init__` (`ui.py`) sets `self.cheatsheet = False`;
`self.desk` stays `True`. `ui.cheatsheet` gains the tip "Keys, pad and
desk legend, bottom-left of this window. / toggles it." The three roads
(`key:SLASH`, the pad's MENU, the APC40's DETAIL) and the SYSTEM page's
checkbox are unchanged and still toggle the one param; DETAIL's LED
shows the param, so it reads dark at launch. `ui_desk.diagram` needed no
edit: with the sheet off it sits in the bottom-left corner. Not
remembered, no config key.

**Differs from §2, and why.** Nothing in the behaviour. Two additions:
`tools/sheet_shots.py`, which makes the two pictures; and the `ui.desk`
tip and the comment by `Panel.desk` now say "bottom-left of this window
(above the cheat sheet when that shows)" (its review). Comments in
`app.py` still describe the sheet as part of the launch layout: the
module docstring's "?  cheat sheet" line is still true (the key shows
it), and `CONTROL_SIZE`'s comment "wide enough for the cheat sheet on
the left and the panel on the right" is still what the width is for, but
neither says the sheet is off until `/`. They are code and were left for
a code PR.

**Found by its review and fixed in WP7:** on the frame `/` first brings
the sheet up, the desk diagram was drawn in the wrong place for that one
frame (below).

**Tests.** `tests/test_ui_shell.py::test_the_cheat_sheet_is_off_at_launch_and_the_desk_is_on`,
`::test_slash_still_toggles_the_cheat_sheet`;
`::test_every_page_fits_the_control_window` and
`tests/test_ui_desk.py::test_the_diagram_draws_on_both_layers_and_hides`
unchanged.

**Demo.** `docs/plans/assets/16-paper-cuts/launch-no-sheet.png` and
`launch-sheet-on.png` (`uv run python tools/sheet_shots.py`): the real
`Panel` in a hidden GLFW window over headless objects, before and after
the `key:SLASH` row fires once.

**Not verified.** `/` on a keyboard, MENU on the pad, DETAIL on the
APC40 and its LED; the tooltip drawn (the test reads the param's `tip`).
The orchestrator's scripted launch saw the window open with no sheet and
the param toggle, not a key press.

### WP2 — A chip click selects; selection by name (PR #84, merged 363bd41)

**Built.** `fx.py`: `FxState.sel` (an index) is gone;
`FxState.sel_name` holds the open effect's name. `FxState.select(name)`
opens it (a name with no spec is ignored; `None` means "whatever is
first") and writes nothing else. `FxState.selected()` is `sel_name`
while it has a spec, else the first of `names()`, else `None`; it never
writes, and reads `getattr(self, "sel_name", None)` so an `FxState` from
before a hot reload does not raise. `fx.select` keeps its id, label,
`persist=False`, `modulatable=False` and choices and is a view: it reads
the open effect's index in `names()`, a write selects `names()[i]` with
`i` clamped. The selection is in no preset, show or file, and — because
`undo.watched` requires `persist` — opening a strip is not an undo step.

`ui_fx._chip`: each chip is two adjacent items. The **LED**
(`##led.fx.<name>.on`), a chip-height square at the left end — a filled
dot while the effect is on, a ring while off — toggles `fx.<name>.on`
and never selects; its hover reads "on — click to switch off" / "off —
click to switch on" (from the base, with the modulation line while a
source rides the switch). The **name** (`##chip.fx.<name>.on`) calls
`fx.select(name)` and never writes the switch. Both parts are solid red
while the effect is on; the open chip has a 2 px outline in `ui.TEXT`.
Right-click on either part opens the `fx.<name>.on` menu, each with its
own popup id (`key=".led"` / `".chip"`). The strip's own "on" check is
unchanged; `ui.py` is not touched.

**Differs from §2, and why.**

- **Three chips to a row, not four** (`ui_fx.CHIPS_PER_ROW = 3`). §4
  said WP2 "keeps the chip grid's shape". With the LED taking a square
  of each chip, seven of the twelve factory names were cut short at four
  to a row ("Kaleidosc", "Trip colou"); at three only the two longest
  lose 3 px. The cost is a fourth chip row, about 29 px of the page. One
  constant to reverse. Register row 45.
- **The outline goes round both parts** of the open chip, not the name
  alone, and is not drawn while the chip's Learn is armed (the learn
  frame has the same place).
- **The page pins the launch fallback** (review): with nothing chosen,
  `selected()` is the first effect, which is a position; the first time
  the page draws it, it calls `fx.select(sel)`, so from then on it is
  held by name. `selected()` itself still never writes. While `sel_name`
  names an effect whose file is away, the fallback stays positional and
  the effect reopens when the file returns.
- `fx.select`'s getter and setter are two module functions (`_sel_index`,
  `_sel_set`), so `FxState` publishes only the contract's three names.

**Tests** (`tests/test_fx.py`). `test_selection_is_by_name_and_survives_a_reorder`,
`test_selection_survives_a_preset_load`,
`test_a_removed_effect_falls_back_and_comes_back`,
`test_fx_select_is_a_view_onto_the_name`,
`test_a_chip_click_selects_and_never_toggles`,
`test_the_chips_led_toggles_and_never_selects`,
`test_selecting_an_effect_is_not_an_undo_step`,
`test_the_first_effect_is_held_by_name_once_it_is_shown`,
`test_the_leds_hover_says_what_a_click_does`;
`test_the_page_has_no_conflicting_ids` now also checks both items of
every chip and that no two context menus share a popup id.

**Demo.** `docs/plans/assets/16-paper-cuts/fx-chips.png`
(`uv run python tools/fx_page_demo.py --shots`, a hidden window): twelve
chips, three to a row, two on, one open and off. `fx-select.txt` (the
same tool without `--shots`): the open effect stays `kaleido` while its
order goes 15 → 99, another effect moves past it, and three presets
load.

**Not verified.** A real mouse click on the LED or the name (the tests
send imgui mouse events at the item's rect): whether the LED is
comfortable to hit on a trackpad, or easy to hit by mistake, is hand
check 59. The right-click menus on the two parts were not opened. A live
hot reload of `fx.py` across this change leaves `fx.select` on its old
closures until a restart.

### WP3 — An effect that is not running says why (PR #86, merged aa1e54e)

PR #86 was stacked on WP2's branch and went onto `plan-16-integration`
by a merge commit; GitHub shows it closed, not merged, because its base
branch was deleted.

**Built.** `ui_fx.why_idle(fx, name)` returns `"off"`, `"bypassed"`,
`"fx mix 0"`, `"mix 0"` or `None`, checked in that order against the
four conditions of `FxState.chain()`. When it is not `None` the open
strip draws one line in `ui.WARN` — after the effect's tip and its error
line, before its "on" row — with a chip for the first two reasons:
"off — nothing below shows until it is on" + **turn on**
(`fx.<name>.on`), "the whole stack is bypassed" + **effects on**
(`fx.on`), "FX mix is at 0", "its mix is at 0" (`ui_fx.IDLE`). The rows
under it are dimmed and stay live; the "on" check is not dimmed. Both
chips are `Param.set` on a persisted param: one undo step each, no
explicit push.

**Differs from §2, and why.**

- **The dimming is a veil, not a pushed style alpha** (`ui_fx._dim`: a
  rect of the window's ground drawn over the rows after they are drawn;
  `IDLE_ALPHA = 0.45` is how much of a row shows through). A pushed
  alpha would still be on the stack when a row's right-click menu or the
  blend combo's list is drawn, so the Learn menu would be at 45 % too,
  on the one strip that must stay learnable. Register row 46.
- **At "its mix is at 0" the effect's own mix fader is not dimmed**: it
  is the control the line names.
- A row whose Learn is armed has its learn frame drawn again over the
  veil (`_relearn_frame`; review). Its ghost bar and modulation dot stay
  dimmed with the row.
- `why_idle` reads the effective values `chain()` reads; the chips write
  the base. With a routed source holding the switch off, "turn on" sets
  the base and the line stays (it is still true); the chip's hover names
  who is riding it.
- Room: with WP2's fourth chip row the tightest strip (`zoomblur`) has
  52 px to spare with the line showing, against §2's 110 px measured
  before either package.

**Tests** (`tests/test_fx.py`). `test_why_idle_names_the_first_reason`,
`test_an_off_effects_strip_says_so_and_turn_on_switches_it_on`,
`test_a_bypassed_stack_says_so_on_the_strip`,
`test_the_idle_strips_controls_stay_live`,
`test_the_page_fits_with_the_tightest_strip_idle`,
`test_turn_on_is_one_undo_step`,
`test_an_armed_rows_learn_frame_is_drawn_over_the_veil`.

**Demo.** `docs/plans/assets/16-paper-cuts/fx-idle.png` (the same tool,
`--shots`): Kaleidoscope open and off, the line and **turn on**, the
check at full strength, the rows under it dimmed.

**Not verified.** A real click on either chip or on a dimmed fader;
right-click → Learn on a dimmed row was not exercised by a test or a
hand. How the dimming reads from a step back is hand check 60's. The
veil assumes the page's ground is the window background colour. The
line and its chip are not wrapped: they fit at the control size and no
test holds them narrower. An effect whose shader never compiled gets its
error line and no idle line. The page's status line reads `fx.on`'s base
while the strip's line reads the effective value; under a route on
`fx.on` they can disagree.

### WP4 — Window placement at launch (PR #85, merged 6f7736f)

**Built.** `hyperspace/placement.py`, importing nothing from the package
(`glfw` is passed in): `screens`, `load`, `save`, `usable`,
`default_rect`, `place(kind, size, screens, monitor, remembered) ->
(rect, note)`. `[output] monitor` is widened — at 0 or above the render
window is also created on that screen — and `[output] control_monitor`
is new, default −1. `<home>/windows.json` (`hyperspace.windows/1`) holds
the control window's rect and a list of render rects, one entry today.
`app._windows(overlay, cfg, home)` asks `place` for each window; notes
go to stderr and `cfg["notes"]` (the SYSTEM page). `app._save_windows`
runs through `_quiet` first thing after the loop in `main` and at the
top of `_restart`. `Output.windowed_rect()` (`overlay.py`) is read-only.
`hotreload.MODULES` lists `"placement"` among the leaves. Forks F4, F5
and F6 as recommended: register row 48.

**Differs from §2, and why.**

- **`default_rect` does not clip the size to the work area.** A first
  launch is then exactly as it was on every screen, and a small laptop's
  clipped size is not what gets written at the quit and carried to a
  bigger screen. A *remembered* size is still clipped to the screen it
  lands on.
- `Output.windowed_rect()` reads the mode the window is actually in
  (`_applied["mode"]`), not the one the params ask for.
- The save runs before `close_all`, so a port that hangs on close cannot
  cost the memory.
- A remembered size is floored at 320 × 240 before the usable check, and
  the check runs again after the clip.
- A render slot with no rect and no old entry is written as `null`, so
  the list stays positional for plan 21.
- `save` does not write a rect no launch would restore (a window in the
  OS's own fullscreen, whose content area sits above the work area):
  that window's old entry is kept, as for a minimised one.
- If `place` raises on something unforeseen, `_windows` opens both
  windows at the default spots with a note.
- `screens()` is all or nothing: if any monitor's work area cannot be
  read it returns `[]` and no position is set.
- A file with another schema, or that is not JSON, is ignored without a
  note; a bad entry in a good file, or a rect on no screen, gets one.
  Two things wrong for one window arrive as one line joined by `; `.
- The temp file is per process (`windows.json.<pid>.tmp`).
- On macOS the default spot asks for the work area's top + 16 and the OS
  puts the content area lower (65, not 49, on the build machine); the
  remembered 65 restores to 65.
- **A config value that is not a number** (`monitor = "left"`) was
  treated as −1 by `place` but still stopped the launch in
  `app._make_output`. WP7 settled it (below).

**Tests.** `tests/test_placement.py` (fifteen tests:
`test_first_launch_places_as_before`, `test_a_remembered_rect_is_restored`,
`test_a_rect_on_a_screen_that_is_gone_falls_back`,
`test_an_off_screen_rect_falls_back`,
`test_a_config_monitor_beats_the_remembered_screen`,
`test_a_remembered_rect_on_the_configured_screen_is_kept`,
`test_a_config_monitor_that_is_not_there_is_a_note`,
`test_a_remembered_size_is_clipped_to_its_screen`,
`test_save_round_trips_and_render_is_a_list`,
`test_a_none_keeps_the_old_entry`, `test_a_bad_file_is_ignored`,
`test_a_bad_file_is_ignored_entry_by_entry`,
`test_an_unwritable_home_costs_only_the_memory`,
`test_screens_reads_the_work_areas_in_monitor_order`,
`test_placement_imports_nothing_from_the_package`);
`tests/test_overlay.py::test_windowed_rect_is_the_saved_rect_while_fullscreen_or_overlay`;
`tests/test_app_boundary.py::test_the_windows_open_where_placement_says`,
`::test_the_exits_save_the_windowed_rects`.

**Demo.** `docs/plans/assets/16-paper-cuts/placement-demo.txt`: the
output of `tools/placement_demo.py` (fake screens), then the transcript
of four real launches on the build machine's one screen, each on a temp
home (no file; that file; the file edited by hand; a nonsense file with
`control_monitor = 1`).

**Not verified.** **A second screen**: opening a window on another
monitor, negative or offset screen coordinates, mixed DPI and GLFW's
monitor order against the config index were exercised with fake screens
only. A projector unplugged between launches. Fullscreen and overlay on
the glass (that a fullscreen quit saves the windowed rect is covered
with a fake backend). ⌘R in a real run. A minimised window at quit. The
SYSTEM page showing a placement note. Windows and Linux window managers.

### WP5 — Instances to zero; `dream.layer`; two comments (PR #90, merged 8970f0a)

**Built.** `view.instances` is `lo=0, hi=100`, an integer, linear,
default 1; it reads "0 · nothing drawn" at 0 and "N instance(s)"
otherwise, and its tip says what 0 does. `Renderer.draw_scene`:
`n_inst = max(0, int(s.instances))`; at 0 it still clears to the ground,
sets the blend function and `self._face_verts = 0`, then returns —
no faces, lines or points, no vertex buffer written. `_draw_frame` is
untouched: the cover pass, the look-back's composite and capture, the FX
chain, the ghost hands and the dim run as on any frame. Zero is reached
from the slider's left end and track knob 3's bottom. `dream.layer` is
`modulatable=False`, with `dream.gap` and `dream.res`; it is still
persisted and set by the panel, a preset and a key or desk row. The
`ui_presets.py` docstring and the `preset.py` comment over the effect
presets say what the code does. Register rows 47 (the floor) and 49
(the layer).

**Differs from §2, and why.**

- Three additions outside the "owns" list: `tools/instances_shots.py`,
  one test in `tests/test_undo.py`, a line in `draw_scene`'s docstring.
- At 0 `draw_scene` still computes the projection and the edge order
  before it returns (the early exit sits after the clear).
- **Plan 12's "n = 68"** at the top of `party-field`'s right-hand height
  is **69**: the throw is 100 steps, not 99. Plan 12's document is
  history and is not edited.

**For the owner to know** (its review; register row 47): a performer row
that pushes both ways (an LFO, a negative lane push) on a count of 1 now
reaches 0 for part of its cycle, and a `position` row reads 0 at the
bottom of its source. No factory row does either (tested). A user's
saved route onto `dream.layer` goes dormant with no note at load
(register row 49).

**Tests.** `tests/test_params.py::test_raw_ranges_clamp_int_and_log`
(changed), `::test_instances_read_nothing_drawn_at_zero`;
`tests/test_render.py::test_zero_instances_draws_only_the_ground`,
`::test_zero_instances_still_runs_the_look_back_and_the_effects`,
`::test_one_instance_is_the_frame_it_was`;
`tests/test_plan12_presets.py::test_no_factory_hand_row_blanks_the_scene`,
`::test_field_height_is_one_gesture_over_three_params` (unchanged);
`tests/test_lookback.py::test_dream_params_declared` (changed),
`::test_a_route_on_the_dream_layer_is_dormant`;
`tests/test_undo.py::test_a_count_taken_to_zero_is_undone`. The PR also
reports a throwaway comparison of the old and new `render.py` at counts
1, 5 and 100 (byte-equal) and 0 (different); the committed test pins the
clamp instead.

**Demo.** `docs/plans/assets/16-paper-cuts/instances-zero.png`
(`tools/instances_shots.py`, an offscreen render): one scene at count 1;
at 0; at 0 with plasma on; at 0 with the look-back on, 3 and 12 frames
after the count left 1.

**Not verified.** Track knob 3 at the bottom on the APC40, the slider
dragged to its left end, a black render window with echoes fading on a
screen. The LOOKBACK page's menu reading "not modulatable" for the
layer. That a route onto `dream.layer` used to make the worker reload
trunks is from reading `DreamWorker._ensure_net`, not from a run with
the net. "Bit-identical at 1" was measured on one GL driver.

### WP7 — Four small fixes found while building 15 and 16 (PR #92)

Not in §2: added by the orchestrator after WP1–WP5, from what their
agents reported. Each was checked in the code first; all four were real.
No new param, menu item or page.

**1. A footer line said twice shows twice.** Every line that reports
something that just happened is now set through `Library.say`, which
counts it (`Library.said`), so `Panel._message` shows the same words
again: an empty F-key pressed twice, home with no "starts on" pressed
twice, a slot naming no file, a show saved twice. A plain assignment of
`lib.status` / `lib.warning` is left for clearing a line and is not
counted, so nothing that assigned the same words every frame could hold
the footer open; no site does. One exception, from the review:
`Library.adopt` says a scene only when it changes, because a knob on
`scene.select` sends the same choice many times in one turn.
`tests/test_ui_presets.py::test_a_line_said_twice_shows_twice`,
`::test_a_line_assigned_every_frame_does_not_pin_the_footer`.

**2. A performer's round-off lights no dirty dot.** `undo.alike(a, b)`
compares nested dicts, tuples and lists with floats (and a whole number
against a float) within undo's `REL_TOL` / `ABS_TOL`, everything else
exactly. `Library.is_dirty` (a module preset; a document kind's
signature, so the preset's dot) and `Project.is_dirty` (the show's
session part) compare through it. `Param` is untouched; the routes, desk
and macros in the signature are JSON text and compare exactly. Measured
with the demo's synthetic hands: 8 of the 22 factory presets read
"unsaved" after two seconds of hands on their own routes before the
change (`view.speed` 0.3 → 0.29999999999859905), none after; one detent
still lights the dot.
`tests/test_undo.py::test_a_performers_round_off_lights_no_dot`,
`::test_alike_is_exact_but_for_float_round_off`.

**3. The desk diagram does not jump when the sheet first shows.**
`Panel._draw_cheatsheet` takes the sheet's height from the rows it has
just laid out, not `get_window_height()`, which on the sheet's first
frame is not its laid-out height.
`tests/test_ui_desk.py::test_the_desk_does_not_jump_when_the_sheet_comes_up`.

**4. A config screen that cannot be used is −1 and a note, not a dead
launch.** `placement.read(key, value)` is the one reading of `[output]
monitor` / `control_monitor`. `config.load` turns a value `int()` will
not read into −1 with a note on stderr and in `cfg["notes"]`.
`app._windows`, after `place` has written its note, leaves −1 in the
config in place of an index no connected screen has, so
`Output.monitor` no longer carries it. One note per key.
`tests/test_config.py::test_a_screen_that_is_not_a_number_is_minus_one_and_a_note`,
`tests/test_app_boundary.py::test_a_config_screen_that_cannot_be_used_is_minus_one_and_one_note`.

**A consequence of 4, for the owner to know.** An index no screen has
*at launch* is −1 for the whole run. Before, `Output.monitor` kept the
index and fullscreen went to that screen once it was plugged in; now a
projector plugged in after the launch is picked by hand (the OUTPUT
page's Screen combo) or by relaunching. To reverse: the three write-back
lines in `app._windows`.

**Demo.** `docs/plans/assets/16-paper-cuts/followups-demo.txt`
(`uv run python tools/followups_demo.py`, headless, a temp home): fixes
1, 2 and 4 before and after, in words and values. "Before" is the old
rule applied to the same state inside the script. Fix 3 has no demo
beyond its test.

**Not verified.** None of the four in the running app. Fix 3 on a
screen. Noticed and left: `[output] bg = "x"` or `alpha = "x"` still
raises in `_make_output`; `monitor = true` or `1.9` is read as `int()`
reads it (1), with no note; the `macro` group reads dirty right after
`lfo-breathe` loads (`macro.1` at 0 against a group default of 1), which
is not round-off and was not touched.

### WP6 — Docs and hand checks

This section; group L of `11-hand-checks.md` (checks 58–63) and check
1's and check 26's sentences; decision register rows 45–49;
`DECISIONS.md`'s 2026-10-04 rows for this plan; `ARCHITECTURE.md` and
`ENGINEERING.md` where these packages changed a sentence;
`plans/README.md`, `CHECKPOINT.md` and the roadmap's pointer.

*As built:* the register gained five rows for six forks (F4, F5 and F6
are one row, "window placement") plus one that was not a fork in §6
(`dream.layer`); the chips-per-row consequence is part of F1's row.

## Appendix A — Hand checks, group L

For `docs/plans/11-hand-checks.md` (WP6 copies it there and gives the
checks their final numbers after plan 15's group K; `L1`–`L6` are
placeholders).

*As built:* copied by WP6 as checks **58–63** (L1 → 58 … L6 → 63), and
changed there where the builds changed a detail: three chips to a row
and the outline round both parts (59); the veil, and the own-mix fader
left undimmed (60); the one-screen caveat, `control_monitor`, and a
config screen that is not a number (61); the knob's bottom and a user's
two-way route (62). The text below is the plan's, kept as written;
`11-hand-checks.md` is the one to run.

## L. Plan 16 — paper cuts — added with plan 16

Laptop first (L1–L3, L5, L6), then the projector (L4). About 20 minutes.
First, headless: `uv run pytest -q tests/test_fx.py tests/test_placement.py tests/test_ui_shell.py tests/test_render.py`.
No config change unless a check says so.

**L1. The cheat sheet is off at launch.**
Headless: `uv run pytest -q tests/test_ui_shell.py::test_the_cheat_sheet_is_off_at_launch_and_the_desk_is_on tests/test_ui_shell.py::test_slash_still_toggles_the_cheat_sheet`.
`uv run hyperspace`. *Pass:* the control window opens with no key legend;
the APC40 diagram sits in the bottom-left corner; `/` shows the legend
with the diagram above it, `/` again hides it and the diagram drops
back; the SYSTEM page's "Cheat sheet" box follows, and its hover says
`/` toggles; with the APC40 in, DETAIL does the same and its LED is dark
at launch. *Fail:* the legend showing at launch → `Panel.__init__`; the
diagram gone, or floating with a gap under it → `ui_desk.diagram`'s
`below`; `/` dead → the `key:SLASH` row (`routing.py`, your
`bindings.json`).

**L2. An FX chip opens without switching.**
Headless: `uv run pytest -q tests/test_fx.py::test_a_chip_click_selects_and_never_toggles tests/test_fx.py::test_the_chips_led_toggles_and_never_selects tests/test_fx.py::test_selection_is_by_name_and_survives_a_reorder tests/test_fx.py::test_selection_survives_a_preset_load`.
F5 (TRIP), FX page. Click the name of an effect that is off. *Pass:* its
strip opens, the chip gains an outline, and it stays off (not red, the
render unchanged). Click the dot at the chip's left end: the effect
switches on, the chip goes red, the strip that is open does not change.
Open the kaleidoscope and drag its order slider end to end: the strip
stays the kaleidoscope's the whole way while its chip moves along the
row. Press F6, then F5: the same effect is still open. *Fail:* a click
on the name switching the effect → `ui_fx.page` (the chip body); the
strip jumping to another effect while the order moves or on an F-key →
`FxState.selected` / `sel_name`; the dot hard to hit from where you
stand → fork F1, say so.

**L3. An effect that is not running says why.**
Headless: `uv run pytest -q tests/test_fx.py::test_an_off_effects_strip_says_so_and_turn_on_switches_it_on tests/test_fx.py::test_a_bypassed_stack_says_so_on_the_strip`.
FX page, open an effect that is off. *Pass:* under its description a
line reads "off — nothing below shows until it is on" with a **turn on**
chip; the faders under it are dimmed but still move, and right-click →
Learn still works on them; **turn on** switches it on and the line goes.
Untick "Effects" at the top: the open strip reads "the whole stack is
bypassed" with **effects on**. Pull FX mix to 0: "FX mix is at 0". Pull
the effect's own mix to 0: "its mix is at 0". No page scrolls in any of
these. *Fail:* no line, or the wrong reason → `ui_fx.why_idle`; the
faders dead while dimmed → the strip was disabled, not dimmed (fork F2);
the page scrolling → the line's row, `tests/test_fx.py::test_the_page_fits_with_the_tightest_strip_idle`.

**L4. The windows open where you left them (projector).**
Headless: `uv run pytest -q tests/test_placement.py tests/test_app_boundary.py::test_the_windows_open_where_placement_says`.
(a) Laptop alone: drag and resize both windows, Esc. Relaunch. *Pass:*
both where and as big as they were; `~/Hyperspace/windows.json` exists
with one `control` entry and one entry in `render`.
(b) Plug the projector in. Drag the render window onto it, Esc,
relaunch: it opens on the projector, the control window on the laptop.
(c) Set `[output] fullscreen = true` (leave `monitor` at −1), relaunch:
fullscreen on the projector with no drag. Esc, open `windows.json`: the
render entry is still the windowed size, not the projector's.
(d) Unplug the projector, relaunch: the render window opens on the
laptop at the default spot, and the terminal names the screen it was
last on. Put `fullscreen` back.
(e) Projector in again. Set `[output] monitor = 0`, `control_monitor =
1`, relaunch: the windows are swapped — render on screen 0, controls on
screen 1 — whatever the file said. Set `monitor = 7`: the SYSTEM page
and the terminal say there is no such screen, and the last position is
used. Remove both keys.
(f) Delete `windows.json`, relaunch: today's placement — render
top-left, controls flush right, on the primary screen.
*Fail:* a window off every screen, or not where it was →
`placement.place` / `usable`; the wrong screen for an index →
`placement.screens` (GLFW's monitor order, as check 26); the fullscreen
size in the file → `Output.windowed_rect`; no file after Esc → the save
at the end of `app.main`; a window that cannot be reached at all →
delete `windows.json`, and log it.

**L5. Instances to zero.**
Headless: `uv run pytest -q tests/test_render.py::test_zero_instances_draws_only_the_ground tests/test_render.py::test_zero_instances_still_runs_the_look_back_and_the_effects tests/test_plan12_presets.py::test_no_factory_hand_row_blanks_the_scene`.
F1 (TUMBLE), VIEW page: drag Instances to the left end. *Pass:* it reads
"0 · nothing drawn" and the render is black; back to 1, the shape is
there. With the APC40: track knob 3 (K3) fully left does the same. F4 (WAKE): take the count to 0 —
the trail fades out over black rather than cutting. F5 (TRIP), count 0:
the effects that paint on their own (plasma, with its level up) still
show. F3 (FIELD) with a hand in the box: right hand at the bottom of the
box is nine copies, never none; at the top the room fills as before.
With ghost hands on, they still draw at 0. *Fail:* one copy still drawn
at 0 → `Renderer.draw_scene`'s clamp; a traceback or a frozen render at
0 → the same function (the red banner and `stall.log` will say); FIELD
blanking with a low hand → the row's rest
(`tests/test_plan12_presets.py`).

**L6. The dream's layer cannot be performed.**
Headless: `uv run pytest -q tests/test_lookback.py::test_dream_params_declared tests/test_lookback.py::test_a_route_on_the_dream_layer_is_dormant`.
LOOKBACK page, right-click the Layer combo. *Pass:* the menu reads "not
modulatable" where other controls offer "Route a lane here…"; on the
ROUTING page, adding a route, `dream.layer` is not in the target list;
the combo itself, a preset and a learned knob still change the layer.
*Fail:* a route offered or listed → the flag on `dream.layer`
(`params.py`).
