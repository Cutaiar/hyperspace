# Plan 23 — the glass flip, windows that come back, the panel across the top

**Partly built.** WP1 (Flip X / Flip Y) was built on its own, straight onto
main, in PR #157 (2026-10-08); the glass needs Flip Y. WP2, WP3, the review
pass and the docs WP are not built. Scoped 2026-10-07 against `plan-22-integration` at
`1d7a293`. Three small work packages before the event, then a review
pass and a docs WP that rewrites this file as built. The launch prompt
for the session that runs it is
[`23-session-prompt.md`](23-session-prompt.md).

The owner's words, in short: *the performer must see their hands move the
way their hands move, with no mental mirroring; we must not spend set-up
time dragging windows around; the control window should be the MacBook's
screen, half desk, half panel, with the page tabs across the top.*

---

## WP1 — Flip X / Flip Y on each output

### The problem

A Pepper's Ghost glass shows the screen by reflection, which mirrors it
about one axis. A screen lying flat under a 45° glass usually flips the
picture top-to-bottom; a screen facing the glass flips it left-to-right.
Uncorrected, the ghost hands move opposite to the performer's.

`ghost.mirror` (`ghost.py:120`, `basis()` at `:148`) does not fix this.
It flips the hands' x in the stage's basis — left-right only, the hands
only. The scene, the guide's readout and the y axis are untouched.

### The decision (owner, 2026-10-07)

**Flip the picture at each output, as its last step**, not on the hand
side. The glass mirrors once and the software mirrors once, so everything
the audience sees is the right way round, with the scene, the hands and the
readout text all flipped together. A hand-side fix would only re-aim
the controls (`hands.*.invert` already exists per axis) and could never flip
the drawn hands vertically.

- Two flags per output: **`output.N.flip_x`** and **`output.N.flip_y`**,
  toggles beside `output.N.scene` / `.hands` / `.through` in
  `overlay.register_switches` (`overlay.py:407`). Rig settings like
  their siblings: group `output`, `persist=False`, `modulatable=False`,
  learnable onto a desk button. They are drawn on the OUTPUT page.
- Launch values from the config: `flip_x = false`, `flip_y = false` in
  each `[[output.screens]]` entry and in the single-window `[output]`
  form (`config.SCREEN`, `config.py:174`, checked in the entry reader at
  `:196` like `through`). `app._slots` (`app.py:173`) copies them into
  `Switches`.

### Where the flip goes

`outputs.Switches` (`outputs.py:40`) gains `flip_x: bool = False`,
`flip_y: bool = False`. The flip is applied **inside the fit rect**
(`inner`, the letterboxed picture): the bars do not move. Every pass
that puts the finished frame or a layer onto an output honours it, and
nothing else does:

| Pass | Where | Output |
| --- | --- | --- |
| The frame | `SHOW_FS` (`render.py:125`), via `Renderer._show` (`:1014`) | 1 |
| The hands, after | `COMPOSITE_FS` (`ghost.py:817`), via `Ghost._lay` (`:1400`) from `composite` | 1 |
| The readout | the same, from `composite_readout` | 1 |
| Frame, hands, readout | `PRESENT_FS` (`outputs.py`), via `Presenter.present`; `Handoff` carries the flags | 2+ |
| The dim | `dim_pass` / `PRESENT_DIM_FS`, which covers the whole rect | no change needed |

Both the `texelFetch` (1:1) path and the scaled `texture()` path of each
shader must flip. A uniform (`u_flip`, an `ivec2` or two ints) defaults to
no flip, and with both off the output must be **bit-identical** to today.
The existing 1:1 tests pin this.

**Do not flip the hands-through pass.** With `through` on and an effect
running, `ghost.composite` lays the hands into the effect buffer *before*
the effects (`render.py:961`, the SCENE_HANDS pipeline). That frame is
flipped whole when it is shown, so flipping there too would flip the hands
twice. The flip must be an argument of `composite`/`_lay` that defaults to
off, passed on only from `_compose` (`render.py:1001`).

### The render window's mouse

`app.Mouse` (`app.py:683`) orbits, pans and zooms from output 1's
window. On a flipped output a drag would run backwards and the wheel
would zoom about the wrong point. Mirror the cursor (and the drag deltas)
by output 1's flags before use. This is output 1 only, because the mouse is
output 1's only (`app.py:1165`).

### `ghost.mirror`

It stays, for a real mirror in front of the hands. Its tooltip, and the
two new toggles' tooltips, say that with an output flip on `ghost.mirror`
belongs off, or the hands flip twice.

### Acceptance

- With both flags off, every output is bit-identical to today
  (tests).
- Each flag mirrors the frame, the hands and the readout on that output
  alone, inside the fit rect, on output 1 and on a presenter output
  (offscreen tests, as plan 21's output tests do).
- Hands-through with an effect on and a flip on flips the hands once.
- The flags come from the config at launch and from the toggles at run
  time. They are never in a preset, show or undo step.
- At the glass (hand check): a hand moving right / up appears to move
  right / up in the reflection, with the right flag on.

---

## WP2 — windows that come back

### What exists

`placement.py` already remembers every window's windowed rect in
`~/Hyperspace/windows.json` (schema `hyperspace.windows/1`), written on
quit and ⌘R, read at launch (`app.py:231–380`). The config's screen
index wins over it (register row 48).

### Why it does not work on the owner's rig

Rects are stored and restored as **absolute GLFW desktop coordinates**,
and placement is "decided by geometry alone". macOS renumbers that space
whenever the arrangement or the primary display changes. The owner's
file today:

```
"control": {"x": 999, "y": 65, "w": 726, "h": 978, "screen": "Built-in Retina Display"}
```

The rig now has `AORUS FO48U` as screen 0 at (0, 30, 3840×2046) and the
MacBook's `Built-in Retina Display` at (3840, 1076, 1728×1084) (work
areas, points). (999, 65) is on the AORUS, so the control window opens there.
The file still names the right screen, but nothing reads the name.

### The change

1. **Screen-relative rects, keyed by name.** Schema
   `hyperspace.windows/2`: each entry is `{screen, x, y, w, h}` with
   `x, y` relative to that screen's work-area origin. At launch, find the
   screen by name and place the window relative to it. If that name is
   not connected, or two connected screens share it, fall back to today's
   rules (absolute geometry, then the default spot), with the note as
   today. A `/1` file still loads, read as absolute, and is rewritten as
   `/2` at the next quit.
2. **Fullscreen is remembered** (owner, 2026-10-07; this overturns
   register row 48, "Fullscreen is never remembered"). For output 1, the
   quit records whether `output.fullscreen` was on and the screen it
   covered (`output.monitor`), by name. For a later output, it records the
   screen its window was on, by name. At launch a remembered fullscreen
   output goes fullscreen on that named screen again.
   **The config still wins where it speaks.** A `fullscreen` or `monitor`
   key the config actually sets beats the file. A key the config leaves out
   is "no say", so `config.py` must stop filling a default for these two
   keys and let the reader tell "absent" from "false" / "−1". Overlay
   (`output.overlay`) is not remembered, which is unchanged.
3. **The control window's default is the MacBook's screen.** With no
   remembered rect and no `control_monitor`, the control window opens
   filling the work area of the built-in display (the screen whose name
   starts with `Built-in`), else of the primary screen. That is no longer a
   fixed `app.CONTROL_SIZE`: `placement.default_rect("control", …)`
   takes the screen's work area. The render windows' default is
   unchanged.
4. **imgui's own memory lives in the home folder.** No `ini_filename` is
   set today, so imgui writes `imgui.ini` to the launch directory. The repo
   root and `hyperspace-python/` each have a stray one (ignored by git,
   so untracked). Point it at `~/Hyperspace/imgui.ini` (where
   `config.load` and `windows.json` live).

### Acceptance

- Unit tests (as `tests/test_placement.py` does, with fake screens): a
  `/2` rect returns to its named screen after that screen moves in the
  desktop space and after the primary changes; a missing name falls back
  with a note; duplicate names fall back to geometry; a `/1` file loads;
  nothing ever opens off every screen (the `usable` rule holds).
- The config/file precedence for `fullscreen` and `monitor`: set beats
  file, absent defers to the file.
- First launch with no file: the control window fills the built-in
  display's work area.
- At the machine (hand check): quit with the render fullscreen on the
  AORUS and the controls on the MacBook. Relaunch, and both are back with
  nothing dragged. Then change the primary display in System Settings,
  relaunch, and both are still back.

---

## WP3 — the tabs across the top, the panel on the right half

### What exists

The control window holds two imgui windows: the desk diagram
(`ui_desk.diagram`, `ui_desk.py:776`), which fills the room left of the
panel (`ui_desk.room`, `:360`), and `CONTROLS` (`ui.py:1270`), placed
once at `PANEL_W` = 540 wide on the right and then free to drag, with
its position kept by `imgui.ini`. Inside `CONTROLS`, a left rail
(`Panel._rail`, `ui.py:1304`, `RAIL_W` = 112) lists the 14 `PAGES`
(`ui.py:414`) as pills, and the page is a child beside it (about 428 px).

### The change (owner, 2026-10-07)

1. **The panel is pinned to the right half** of the control window:
   `set_next_window_pos/size` every frame (`Cond_.always`), no move, no
   resize, its left edge at half the display width. Give it a floor: below
   a window width where half is narrower than today's panel, keep today's
   `PANEL_W` and let the desk shrink. The desk follows by itself
   through `room()`. `big` (panel hidden, desk takes the window) is
   unchanged.
2. **The rail becomes a bar across the top.** The same pills, the same
   red lit pill, the same dirty dot and right-click menu (`_ctx` on
   `ui.page`), laid left to right, wrapping to a second row when they do
   not fit. They do not fit in one: the 14 labels at `FONT_MICRO` with
   today's 12 px inner padding need about 960 px, and half the MacBook is
   864. Tighten the padding first, and wrap only when it is still short.
   The page child takes the full panel width beneath the bar, with the
   footer unchanged.
3. **The pages get wider, not reflowed.** A page goes from about 428 px to
   about 840 px on the MacBook. Pages are laid out to fit without a
   scroll; check each of the 14 at the MacBook's half width and at the
   floor width, and fix only what breaks (a fixed width that now looks
   lost is fine; an overlap is not).

### Tests that will move

`PANEL_W` / `RAIL_W` are read by `tests/test_ui_patterns.py`,
`test_ui_desk.py` (the room arithmetic and `_panel_x`),
`test_ui_shell.py`, and about seven more test files. Re-derive their
expectations from the new layout and do not delete them. Add tests: the
bar wraps at a narrow width and keeps one row at a wide one; a click on
a pill sets `ui.page`; the panel's left edge is half the display at the
MacBook's size and the floor below it.

### Acceptance

- First launch on the MacBook: the control window fills the screen, the
  desk the left half and the panel the right half. The 14 tabs sit across
  the top, and no page scrolls or overlaps.
- The panel cannot be dragged off its half, and quitting and relaunching
  gives the same layout without `imgui.ini` having any say in it.

---

## Not in this plan

- Flipping on the control window or the desk.
- Remembering overlay mode, or any `output.N.*` switch other than what
  the config sets.
- A user-adjustable desk/panel split ratio.
- Any change to `ghost.mirror`'s behaviour (tooltip only).
