# Plan 21 — Outputs and the hands: a list of render outputs, the hands over or through the effects, the ghost hands finished

**From the Oct 3–4 session and the owner's answers of 2026-10-04**
([`15-21-roadmap.md`](15-21-roadmap.md) §4 "Plan 21", §5, §7; decisions 32
and 33 in `docs/DECISION-REGISTER.md`), **plus the owner's addition of
2026-10-04, made during the run**: per output, the hands are composited
either after the shader pipeline (undistorted, today) or before it (the
effects distort them too).

Written 2026-10-04 against `plan-20-integration` at 8345f4f (`finish-line`
with plans 15, 16 and plan 20's face target), reading
`origin/plan-18-integration` at 8c0e416 for `ghost.py`, `hands/core.py`
and `hands/panel.py` as plans 17 and 18 leave them. No code was changed.
Every row of §1 cites the function as it stands on 8345f4f. Six things
were measured on this laptop (Apple M3 Max, one built-in 120 Hz screen,
a temp `HYPERSPACE_HOME`; the scripts are not kept): the cost of each
pass, whether a frame routed through a texture is the same bytes, what a
second window's context sees of a texture, the frame rate with two
windows swapped per frame, whether the OUTPUT page's grid fits, and the
two picture sheets under
[`assets/21-outputs-and-the-hands/`](assets/21-outputs-and-the-hands/),
which are **offscreen renders from synthetic hands, made by a probe
script from the renderer's existing passes, not by the build**. Nobody
was available to answer questions: every fork is in §6 with the option
taken.

## HAND-OFF NOTES (2026-10-04)

**Built.** All seven work packages are done: WP5 (PR #112), WP1 and WP2
(PRs #118, #120), WP6 (PR #122), WP3 and WP4 (PRs #123, #124) are merged
into `plan-21-integration`, and WP7 (this document's §7, decision
register rows 79–88, hand checks group Q, 99–112) is its docs package.
**§7 "As built" is the record**: where the build proved a sentence below
false, the sentence stays and an *As built:* note follows it. What is
left is only the owner's: hand checks 99–112 at the machine, and rows
79–88 to confirm or overturn. Nothing in this plan has been seen on the
glass or the projector, with a real hand, or with two screens; **the
frame-rate claim of fork F6 is unconfirmed** (§7, "What the orchestrator
saw").

The notes the plan's author left when they stopped, kept as they were
(each "still to do" in them is done: the register rows are 79–88, the
test names of §5 now exist, with the differences §7 lists):

The plan below is complete as a first draft: every section asked for is
written, and every finding, measurement and fork made so far is in it
(nothing is held only in these notes). What the next reader should know:

- **Not re-read after writing.** The document was written in one pass
  and not proof-read against the code a second time. The claims in §1
  and WP5 were each taken from the file as read; the test names in §5
  are proposals, not existing tests.
- **Not looked at:** `ENGINEERING.md`, `CHECKPOINT.md`, plan 14 and the
  body of `DECISION-REGISTER.md` beyond rows 31–33; `tests/test_app_boundary.py`,
  `test_overlay.py`, `test_placement.py`, `test_fx.py` beyond their
  names; `hands/panel.py` and `hands/core.py` on `plan-18-integration`
  beyond a grep for the box and the ghost rows; plans 19 and 20's
  unbuilt parts (the FX page, the look-back page), which may move
  `ui.py` under WP4. ARCHITECTURE §3 was not re-read for this plan; R2
  rests on its one-line statement in the task ("the render stack only
  reads") and on `Registry.apply` adopting raw writes as DECISIONS says.
- **Measured, and how:** all on this laptop (M3 Max, one 120 Hz screen),
  temp home, scripts in `/tmp/plan21probe/` (not kept in the repo).
  Pass costs are medians of 120 frames between `glFinish` calls on a
  standalone context with a 4-sample renderbuffer standing in for the
  window. The swap test used three small real GLFW windows on the one
  screen.
- **Not measured:** two physical screens (swap phase, tearing, mixed
  refresh rates, real fullscreen on two monitors, a monitor unplugged);
  the cost of `glFlush` itself; `skeleton()` on the SDK thread; whether
  framebuffer and vertex-array names are unusable across the share
  group on this driver (taken from the GL specification).
- **Unverified in R5:** that both reload hooks fire in one round was
  read from `hotreload.py` and `Renderer.on_reload`, not run.
- **The pictures** are from a probe that calls the renderer's existing
  passes in the order §2 gives; they show the design is reachable with
  today's passes, not that `draw_outputs` exists.
- **Still to do:** a second read for accuracy; the register rows for the
  forks (WP7 does it at build time); no PR is open.

## Scope in brief

**What you asked for on 2026-10-04, and what it takes.** Each output gets
a third switch beside "scene" and "hands": **hands through effects**. Off
(the default, today's picture): the hands are laid over the finished
frame and no effect touches them. On: the hands are laid onto the frame
*before* the effect chain runs, so warp, kaleido and the rest bend them
with the shape.

| | |
|---|---|
| Where the hands go in when the switch is on | After the look-back composite, before the first effect. The echoes and the dream still never hold the hands. |
| Where it is built | `render.py` (the frame order), `ghost.py` (the hands' layer split from its composite), a new `outputs.py`. About 150 lines of the plan's ~900. |
| Params | One toggle per output: `output.N.through`, label "Hands through effects". |
| Cost per frame at 1080p, measured | Nothing when every output agrees. One extra composite (about 0.5 ms) when an output wants the hands through the effects. One extra run of the effect chain (0.9 ms for four effects) only when the two outputs disagree. |
| With no effect on | The switch changes nothing: there is nothing to distort, so the hands are laid over as today. |
| Default | Off on every output. A rig with one output and default switches renders today's frame byte for byte. |
| Not built | The hands in the echoes or the dream (fork F1). The guide and its text labels distorted (they stay legible, fork F3). |

**The whole plan, in one screen.**

- **Outputs.** `config.toml` lists the render outputs (`[[output.screens]]`,
  two on the rig, four at most). Each is a window on its screen. With no
  list there is one output, exactly as today. The laptop keeps the
  control window.
- **Three switches and a dim per output**, on the OUTPUT page: scene,
  hands, hands through effects, dim. Eight switch states per output
  (below). On the rig that is 8 new params; on a one-output laptop, 3.
- **Rendered once, shared.** The scene is drawn once. The hands are
  drawn once into their own layer. The effect chain runs once per
  *distinct* input, so two outputs with the same switches share it.
- **The frame rate holds.** One output's swap waits for the screen; the
  others do not. Measured here with two windows: 121 fps on the 120 Hz
  screen; with both waiting, 60 to 81.
  *As built:* the swap rule is built as stated, but the 121 fps was
  **not reproduced**: in the build's short launches both the two-output
  path and the one-window path ran unpaced (270–380 fps), so the claim is
  neither confirmed nor refuted (§7; hand check 107, register row 83).
- **PR #78 reviewed.** Fourteen findings, two that must be fixed (a
  raising hands pass skips the master dim; the pass writes a parameter).
  Check 47 is finished as part of group Q.
- **`ghost.style`.** One enum picks what is drawn from the same hand
  data: HANDS, JOINTS, PALMS, and two fun ones, CAGE and MARIONETTE
  ([pictures](assets/21-outputs-and-the-hands/styles.png)).
- **Files.** New: `outputs.py`. Changed: `render.py`, `ghost.py`,
  `app.py`, `overlay.py`, `config.py`, `placement.py` (one argument),
  `watchdog.py`, `ui.py`, `hands/panel.py`, `hands/core.py`,
  `hotreload.py`.
- **Not built.** A picture of the outputs in the control window (words
  instead, fork F8). Live monitor and fullscreen switches for the second
  output (the config says, fork F10). Different content per output
  beyond the three switches. Overlay on any output but the first.

**The eight states of one output**
([offscreen render](assets/21-outputs-and-the-hands/eight-states.png),
effects warp + kaleido on):

| # | Scene | Hands | Through effects | What the output shows |
|---|---|---|---|---|
| 1 | on | on | off | The scene with its effects, the hands clean on top. **The default; today's frame.** |
| 2 | on | on | on | The scene and the hands, both through the effects. |
| 3 | on | off | off | The scene with its effects. |
| 4 | on | off | on | The same picture as 3. |
| 5 | off | on | off | The hands alone on black. |
| 6 | off | on | on | The hands alone, through the effects. |
| 7 | off | off | off | Black. |
| 8 | off | off | on | Black, the same as 7. |

Eight switch states, six different pictures: with the hands off, the
third switch has nothing to act on. The probe confirmed 3 = 4 and 7 = 8
byte for byte.
*As built:* `eight-states.png` was regenerated from the merged code by
`tools/outputs_shots.py` (WP2) and replaces the probe's picture; still an
offscreen render from synthetic hands. 3 = 4 and 7 = 8 are held by
`test_outputs.py::test_each_of_the_eight_states_shows_its_picture`.

![The eight states, an offscreen render from a probe script](assets/21-outputs-and-the-hands/eight-states.png)

## 1. What the owner asked for and what it is

| # | Asked for | What the code does today | So |
|---|---|---|---|
| 1 | "Each a fullscreen window on its monitor **sharing the one GL context**" (roadmap §4) | GLFW gives every window its own context; `app._windows` makes the control window with `share=render_win`, and `main` already holds a second moderngl handle for it (`ui_gl`). A share group shares textures, buffers and programs; framebuffers and vertex arrays belong to one context (the GL specification; not probed, name collisions make a probe meaningless). | A second output cannot be drawn with the renderer's own vertex arrays. Each output after the first gets a small **presenter** in its own context (WP3). |
| 2 | "The scene with its effects is rendered once into a texture" | There is no texture of the finished frame. `Renderer._draw_frame` ends on the window: `fx.run(target, t)` when an effect is on, else `lb.composite(self.scene.tex, target, cover)`. | When two outputs share a picture, the pipeline's last pass goes to a frame texture and each output copies it. Measured: the copy is the same bytes (below). With one consumer it still writes straight to the window. |
| 3 | "Outputs of different size or aspect" | The look-back composite reads the scene with `texelFetch(u_scene, ivec2(gl_FragCoord.xy) - u_origin, 0)` (`lookback.POST_FS`): pixel for pixel, so its target must be the scene's size. `SceneTarget.ensure` takes the window's size. | One frame size, the first output's. Other outputs show that frame scaled (fork F5). |
| 4 | "The hands are rendered once into their own layer (as PR #78's ghost hands already do)" | `Ghost.draw(target, vp, t, opaque)` renders the layer **and** composites it in one call; the layer (`Ghost._tex`) is private and sized to the target's viewport (`_ensure`). | Split into `Ghost.layer` and `Ghost.composite`; `draw` stays as the two together (WP1). |
| 5 | "#78 draws through one call, `draw(poses, view_proj, eye)`" | True of `CapsuleHands.draw`. But the guide rides inside it: `s_rows += p.guide[0]`, `t_rows += p.guide[1]`. A replacement geometry would have to draw the guide too. | WP6 moves the guide's rows out of the geometry class before adding styles. |
| 6 | "Each output … times its own dim, times the master dim (`Renderer.dim_pass(target, vp, factor, opaque)` is the seam)" | `dim_pass` draws with `self._dim_vao`, a vertex array of the renderer's context. It serves the first output and any offscreen target; it cannot draw in another window's context. | The presenter carries its own dim (the same two shaders). The factor is `output.dim` × that output's dim, as planned. |
| 7 | "Six session params in all" | The roadmap counted scene, hands and dim for two outputs. The 2026-10-04 addition makes it four per output. The existing `output.*` params (`Output.register`: monitor, fullscreen, overlay, passthrough, bg, alpha, dim) are the one render window's. | 8 on the rig, 3 on a one-output rig (§3). The existing ids stay the first output's. |
| 8 | "The laptop screen is the control view" | The control window is imgui only. It has never shown the render. The one place it shows a render texture is the look-back page's thumbnails (`ui_lookback.py`, `imgui.image` on the atlas's GL name). | The OUTPUT page says in words what each output shows; no preview (fork F8). |
| 9 | "The shader pipeline" (the owner, 2026-10-04) | In `_draw_frame`'s order: the face picture (plan 20, before the scene pass), the scene pass, the cover mask, `lb.composite` (scene ⊕ echoes ⊕ dream), `lb.capture` (the echoes and the dream worker, from `scene.tex`), `fx.run` (the frame's effects), `ghost.draw`, `dim_pass`. | "Before" puts the hands between `lb.composite` and `fx.run` (fork F1). |
| 10 | "Never in the look-back history" (DECISIONS, 2026-10-04) | `lb.capture(self.scene.tex, …)` reads the scene texture, which the hands never touch. | Still true in every state: the hands go onto the chain's input, never onto `scene.tex`. |
| 11 | `windows.json`'s `render` is "a list, shaped for plan 21" | True of the file and of `placement.save`. `app._windows` reads `renders[0]` only and `_save_windows` writes `[render]`. | WP3 reads and writes one entry per output; the schema does not change. |
| 12 | "A render window that presents nothing for 2 s" (`watchdog.RenderWatch`) | One `info` callable, one window (`output.backend.window_state(render_win)`). | WP3: the stall is "no output presented"; one output of several going dark is a warning that names it. |
| 13 | `[[output.screens]]`, promised by plan 16 WP4 "Config" | Not built. `config.load` merges sections with `dict.update`, so an array of tables under `[output]` arrives as `cfg["output"]["screens"]`, a list of dicts, with no change to the loader. | WP3 reads it. |

Three measurements this section leans on:

- **A frame through a texture is the same bytes.** The pipeline's last
  pass into an RGBA8 texture, then a 1:1 `texelFetch` copy to the target,
  then the hands: identical to today's direct frame in all eight cases
  tried (0 and 4 samples, effects on and off, hands on and off).
- **A second context sees last frame's texture unless the first is
  flushed.** With no flush, window B showed the texture one frame late on
  199 of 200 frames. With `glFlush()` in the rendering context before
  switching: 0 of 200.
- **One vsynced swap, the rest not.** Three windows, 240 frames each:

  | Swap intervals | Rate on the 120 Hz screen |
  |---|---|
  | A waits, B does not (the design) | 121 fps |
  | both wait | 81 fps |
  | A does not, B waits | 89 fps |
  | both wait, B minimised | 60 fps |
  | A waits, B does not, B minimised or covered | 121 fps |

  *As built:* not reproduced by the build. In WP3's and WP4's real
  launches (two small windows on this laptop's one screen) the loop ran
  at a median 271 fps with two outputs **and 377 fps with one output (no
  list, today's one render window)**: the waiting swap did not pace the
  loop in either case, so this table neither confirms nor refutes fork
  F6. The code sets the intervals the design names
  (`test_app_boundary.py::test_only_the_first_output_waits_for_the_screen`);
  what they do with two screens is hand check 107.

## 2. Work packages

"Outputs and the #78 review at once; styles after the review."

| WP | What | Size | After |
|---|---|---|---|
| 1 | The compose path: layers once, a picture per output, on one context; scene, hands and dim | M | 5 |
| 2 | Hands through effects: the second and third pipelines, the readout layer | S–M | 1 |
| 3 | The output list: config, windows, presenters, swaps, placement, the watch | M–L | 1 (signature only) |
| 4 | The params and the OUTPUT page | S | 1, 3 |
| 5 | PR #78's review findings | S–M | — |
| 6 | `ghost.style` | M | 5, 1 |
| 7 | Docs, decisions, hand checks, "As built" | S | all |

Merge order: 5, 1, 2, 3, 4, 6, 7. WP3 can be built beside WP1 and WP2
against the contract below. One PR per WP on `plan-21-integration`, each
with a demo.

**Shared files.**

| File | WP1 | WP2 | WP3 | WP4 | WP5 | WP6 |
|---|---|---|---|---|---|---|
| `render.py` | `draw_outputs`, `_draw_frame` | the pipelines | — | — | the guard round the hands (lands first) | — |
| `ghost.py` | `layer` / `composite` | the readout layer | — | — | `_ensure`, `_draw_tethers`, `on_reload` | styles, the guide out of the geometry |
| `outputs.py` (new) | `Switches`, `route`, `fit`, `View` | `route`'s through rows | `Presenter` | — | — | — |
| `app.py` | — | — | all of it | — | `_open_hands` note | — |
| `overlay.py` | — | — | `Output` per window | `register` | — | — |
| `ui.py` | — | — | — | `_page_output`, footer | — | — |
| `hands/panel.py` | — | — | — | — | the unmeasured-mode line | the style combo |
| `hotreload.py`, `tests/test_hotreload.py` | `outputs` in `MODULES` | — | targets | — | — | — |

No WP edits `lookback.py`, `fx.py`, `shaders/`, `preset.py`, `routing.py`,
`library.py` or any factory JSON.

### The frame as it will be

```text
ONCE PER FRAME, in the first output's context
 0  frame size = the first output's framebuffer size; scene.ensure; blank on units 0–3
 1  the face picture                      plan 20, unchanged
 2  the scene pass → scene.tex            unchanged
 3  scene.resolve, the cover mask         unchanged
 4  lookback.tick, pull; fx.tick; fx.opaque
 5  route every output (outputs.route)    → which pipelines this frame needs
 6  the hands' layer → ghost.tex          only if some output shows hands and a hand shows
    the readout layer → ghost.readout     only if the guide is on and a through pipeline runs

ONCE PER DISTINCT PIPELINE, in this order
 7a SCENE         lb.composite(scene) → [fx chain] → dst
 7b SCENE+HANDS   lb.composite(scene) → hands over → fx chain → dst      (only with an effect on)
 7c HANDS         clear to the ground → hands over → fx chain → dst      (only with an effect on)
    lb.capture(scene.tex) runs exactly once, after the first composite of the frame,
    or on its own when no output shows the scene: the echoes and the dream go on.
    dst = the output itself when it is the pipeline's only consumer, on this
    context, at the frame size; else a frame texture (RGBA8, frame size).

ONCE PER OUTPUT
 8  the picture: nothing (direct), or the frame texture copied 1:1, or scaled to fit;
    an output with no pipeline is cleared to the ground
 9  hands over effects: the hands' layer composited, in the same rect
10  the readout layer composited, when it is separate
11  dim: output.dim × this output's dim, when under 1
12  swap: the others first (they do not wait), the first output last (it waits)
```

*As built* (§7 has the order as built): **routing runs after the hands'
layer** (step 6 before step 5), because "hands shown" (fork F7) needs "a
hand visible this frame", which only the layer knows; and **`lb.capture`
runs once, after every pipeline has composited**, not after the first
composite — with a capture between two pipelines' composites the second
pipeline showed this frame doubled as an echo, one echo short and every
echo a frame older (the review of PR #120, fixed in 29c3e4c;
`test_outputs.py::test_two_pipelines_show_the_same_echoes`). Frame
textures are always LINEAR (a 1:1 copy reads by `texelFetch`, so the
filter does not matter there). A pipeline that raises leaves its outputs
showing their ground.

What an output is given depends only on its switches, whether an effect
is on, and whether a hand shows. `outputs.route` is that table, pure
Python:

| Scene | Hands shown | Through, and an effect on | Pipeline | Hands composited after |
|---|---|---|---|---|
| on | no | — | SCENE | no |
| on | yes | no | SCENE | yes |
| on | yes | yes | SCENE+HANDS | no |
| off | no | — | none (the ground) | no |
| off | yes | no | none (the ground) | yes |
| off | yes | yes | HANDS | no |

"Hands shown" is the output's hands switch **and** `ghost.on` **and** a
hand visible this frame (fork F7). So with the hands away, or no effect
on, every output collapses to SCENE or the ground and nothing extra runs.

**How many pipelines.** Two outputs need at most two chain runs; the
default rig needs one. Four outputs need at most three.

| Glass | Projector | Chain runs |
|---|---|---|
| any state | the same state | 1 (0 if both scene off and not through) |
| scene, hands over | scene, no hands | 1 |
| scene, hands over | scene, hands through | 2 |
| scene, hands through | hands alone, through | 2 |
| scene, hands over | hands alone, over | 1 |

**The two outputs and the control view.**

```text
        config.toml                         the laptop (control view)
   [[output.screens]] #1  #2            ┌──────────────────────────────┐
                                        │ OUTPUT                       │
   ┌───────────────────────┐            │ master dim  ████████░░ 80%   │
   │ 1  GLASS  (paces)     │            │ 1 glass   ☑scene ☑hands ☐fx  │
   │  scene      [on]      │            │   dim ██████████ 100%        │
   │  hands      [on]      │            │   shows: scene + hands       │
   │  through fx [off]     │            │ 2 projector ☑scene ☐hands ☐fx│
   │  dim        100%      │            │   dim ██████░░░░ 60%         │
   │  → pipeline SCENE,    │            │   shows: scene · 48%         │
   │    hands after        │            │ paced by 1 · frame 1920×1080 │
   └───────────────────────┘            └──────────────────────────────┘
   ┌───────────────────────┐              no picture of the render here;
   │ 2  PROJECTOR          │              the footer says "output 2 black"
   │  scene      [on]      │              when an output shows nothing
   │  hands      [off]     │
   │  through fx [off]     │      scene ──► look-back ──► effects ──┬─► 1
   │  dim        60%       │      (once)   composite     (once)     └─► 2
   │  → pipeline SCENE     │      hands' layer (once) ─────────────────► 1
   └───────────────────────┘      master dim × own dim, last, per output
```

**Alpha.** On an opaque ground (every output but an overlay) every
composite leaves the target's alpha as it is, as `Ghost.draw` and
`dim_pass` do today, and `FxChain.run` writes alpha 1. In overlay the
hands add their coverage, before or after the chain, and the dim fades
colour and alpha (register row 41, unchanged). **The fade at the box's
edge** is in the hands' layer (premultiplied by each hand's fade), so it
is the same in every state. **`ghost.alpha`** is applied at the
composite, wherever that is.

### WP1 — The compose path

**What.** `Renderer.draw_outputs`, the hands' layer split from its
composite, and the per-output picture, all on one GL context with
offscreen targets standing in for windows. Scene, hands and dim
switches. No new window.

**Owns:** `render.py`, `ghost.py` (`Ghost.draw` and the targets),
new `outputs.py`, `hotreload.py` (`"outputs"` in `MODULES` before
`"render"`), `tests/test_outputs.py` (new), `tests/test_render.py`,
`tests/test_ghost.py`, `tests/test_hotreload.py`.
**Must not touch:** `app.py`, `overlay.py`, `ui.py`, `lookback.py`,
`fx.py`.

**Contracts.**

```python
# outputs.py — render stack: imports moderngl and glsl, nothing from app, ui or params
MAX_OUTPUTS = 4
SCENE, SCENE_HANDS, HANDS = 0, 1, 2          # pipeline keys, in run order

@dataclass
class Switches:                # what the output.N.* params write (WP4)
    scene: bool = True
    hands: bool = True
    through: bool = False      # hands through effects
    dim: float = 1.0

def route(sw: Switches, fx_active: bool, hands_visible: bool) -> tuple[int | None, bool]:
    """(pipeline key or None for the ground, hands composited after)."""

def fit(src: tuple[int, int], dst: tuple[int, int]) -> tuple[int, int, int, int]:
    """The rect (x, y, w, h) in dst that shows src whole, centred, aspect kept.
    Equal sizes give (0, 0, w, h)."""

@dataclass
class View:                    # one output, for one frame
    switches: Switches
    size: tuple[int, int]                       # its framebuffer, px
    target: moderngl.Framebuffer | None = None  # on the renderer's context
    presenter: "Presenter | None" = None        # WP3: another window's context
    bg_alpha: float = 1.0
    error: str = ""                             # set by draw_outputs, never raised

# render.py
class Renderer:
    def draw_outputs(self, s, w, h, dpr, views: list[View], t_now=None) -> None: ...
    stats: dict    # {"pipelines": [keys run], "chain_runs": n, "direct": bool}
    # draw(s, w, h, dpr, t_now) is unchanged: one default View on the bound framebuffer

# ghost.py
class Ghost:
    def layer(self, size, t) -> bool: ...          # render the hands' layer; False: nothing shows
    def composite(self, target, vp, opaque=True) -> None: ...
    tex: moderngl.Texture | None                   # the layer, premultiplied
    # draw(target, vp, t, opaque) stays: layer(vp's size) then composite
```

*As built:* `stats` also has `captures`, `layer` and (WP2) `readout`;
`View` also has `viewport` (a rect of its target; None is the whole
size), `handoff` (an `outputs.Handoff` for a presenter view) and `exc`
(what set `error`, re-raised by `Renderer.draw` after the frame
finished); `outputs.Handoff` and `Slot` are additions. `View.bg_alpha`
is honoured only in part: the frame and the chain are drawn on
`Renderer.bg_alpha`, so an output's own ground can make the frame opaque
on it but never see-through (the review of PR #118; in `View`'s
docstring). WP2 adds `Ghost.layer(size, t, readout=False)`,
`Ghost.readout` and `Ghost.composite_readout`.

**Behaviour.**

- `views[0]` sets the frame size and the scene's sample count
  (`_samples_of(ctx, views[0].target)`).
- `draw_outputs` with one default `View` on `ctx.fbo` runs today's
  `_draw_frame` path: the last pass writes the target, `ghost.draw`,
  `dim_pass`. `Renderer.draw` calls it that way. This is what keeps
  today's frame by construction.
- The "direct" rule: a pipeline whose only consumer is a `View` with a
  `target` at the frame size writes its last pass into that target.
  Otherwise it writes a frame texture (`RGBA8`, `repeat` off, `NEAREST`
  for a 1:1 copy, `LINEAR` when any consumer scales), kept per key and
  resized with the frame.
- A copy to a target at the frame size uses `texelFetch`; a scaled one
  samples through `fit`'s rect, and the rest of the target is cleared to
  the ground.
- Hands after: `ghost.composite(target, fit rect, opaque)`.
- Dim: `dim_pass(target, full viewport, self.dim * view.switches.dim,
  opaque)` when the product is under 1.
- `lb.capture` runs once a frame whatever the switches. With the scene
  off everywhere the scene pass still runs: the echoes, the dream worker
  and the effects' clocks carry on, so switching the scene back on shows
  no gap. `FxState.advance_to(t)` already advances once however many
  times the chain runs. *As built:* once, **after every pipeline**
  (above); with an effect on and no chain run this frame the renderer
  calls `fx.state.advance_to(t)` itself.
- Every exit binds `views[0].target` again with its viewport and
  blending, a raise included (the 2026-09-29 rule). A `View` that raises
  records `view.error` and the loop goes to the next one.
- `Renderer.on_reload` drops the frame textures and the copy program;
  `getattr` guards as the dim's.

### WP2 — Hands through effects

**What.** Pipelines SCENE+HANDS and HANDS, and the readout layer.

**Owns:** `render.py` (step 7), `ghost.py` (the readout), `outputs.py`
(`route`), the tests of WP1. **Must not touch:** `fx.py`, `lookback.py`.

**Behaviour.**

- SCENE+HANDS: `buf = fx.begin(size)`; `lb.composite(scene.tex, buf,
  cover)`; `ghost.composite(buf, (0, 0, *size), opaque=fx.opaque)`;
  `fx.run(dst, t)`. The chain's first texture is RGBA16F; the composite
  blends into it as it does into a window.
- HANDS: `buf = fx.begin(size)`; clear to `(0, 0, 0, bg_alpha)`;
  `ghost.composite(buf, …)`; `fx.run(dst, t)`. No look-back: the echoes
  are the scene's, and the scene is off. A generator effect will light
  the ground here, where state 5 (hands over) shows none: with the scene
  off the effects exist only to act on the hands. *As built:* the clear
  is the frame's ground, `Renderer.bg_alpha`, not a view's own.
- With no effect on, `route` never returns these keys. The switch then
  changes nothing, and the OUTPUT page says "no effect on" beside it.
- **The readout** (the guide and the tethers' text labels) is never
  distorted (fork F3). While no through pipeline runs it is drawn into
  the hands' layer as today, bit for bit. While one runs it is drawn
  into a second texture, `Ghost.readout`: the hands depth-only first
  (colour mask off) so an ON HAND gauge is still hidden behind the palm,
  then the guide's spheres and tubes, then the tethers. Every output
  whose hands switch is on gets it composited after everything, before
  the dim.

### WP3 — The output list: config, windows, presenters, swaps

**What.** `[[output.screens]]`, one window per entry, a presenter per
window after the first, the swap order, placement, and the watch.

**Owns:** `app.py`, `config.py`, `overlay.py` (`Output` per window; no
param changes), `outputs.py` (`Presenter`), `placement.py` (one optional
argument), `watchdog.py`, `tests/test_app_boundary.py`,
`tests/test_config.py`, `tests/test_overlay.py`, `tests/test_placement.py`,
`tests/test_watchdog.py`. **Must not touch:** `render.py` beyond calling
`draw_outputs`, `ui.py`.

**Config.**

```toml
[output]
overlay = false            # rig-wide, as today; overlay is the first output's only
control_monitor = 0        # the laptop

[[output.screens]]         # output 1: sets the frame size and paces the loop
name = "glass"             # optional; the OUTPUT page's label (default: the screen's name)
monitor = 1
fullscreen = true
# optional launch values of this output's switches (defaults shown)
scene = true
hands = true
through = false
dim = 1.0

[[output.screens]]         # output 2
name = "projector"
monitor = 2
fullscreen = true
```

- No `screens` key: one output from the scalar `monitor` / `fullscreen`,
  as today. **An existing `config.toml` keeps working unedited.**
- `screens` present: it wins; scalar `monitor` / `fullscreen` are ignored
  with one note in `cfg["notes"]`. `on_start`, `passthrough`, `bg` and
  `alpha` stay scalar and are the first output's.
- More than `MAX_OUTPUTS` entries, or an entry that is not a table: the
  extras are dropped with a note.
- `monitor` is read through `placement.read`, as today. For output 1 an
  index no screen has is −1 with a note (today's rule). **For a later
  output an index no screen has means that output is not opened**, with
  a note on stderr and the SYSTEM page (fork F9). `monitor = -1` on a
  later output opens it as a plain window where it was last, for working
  on a two-output setup with one screen.
- Outputs are numbered by their place in the list, opened or not, so
  `output.2.*` always means the second entry.
- A `dim` under 0.1 in the config is raised to 0.1 with a note: the
  config cannot launch an output black.

**Windows.** `_windows` returns `(output_wins, ctrl_win)`. Output 1 is
created as today (4 samples, the transparent hint only with `[output]
overlay`). Later outputs: `share=output_wins[0]`, `SAMPLES 0`, never
transparent, `AUTO_ICONIFY` off, titled `Hyperspace — <name>`. Each gets
an `overlay.Output` (`allowed=False` after the first; only the first
registers params) whose `fullscreen` and `monitor` come from its entry
and whose `apply()` runs each frame. `placement.place("render", …)` is
called once per output with `renders[k]`; it gains an optional
`what: str = ""` used only in its notes ("output 2"). `_save_windows`
writes one rect per opened output, `None` for one not opened (the old
entry is kept, as for a minimised window).

*As built:* `_windows` returns **`(slots, ctrl_win)`**, one
`outputs.Slot` per listed output (name, launch switches, monitor,
fullscreen, window, `missing`, `output`, `presenter`, `error`, `size`,
`label`); output 1 and the control window are created first and exactly
as before, then the later outputs. A later output's default spot
**cascades 40 px** (`app.CASCADE`) off a spot another output has. A later
output whose window or presenter will not build is **closed and counts
as not opened**, with a note (the review of PR #123). `_save_windows`
takes the later outputs as `more=`. Output 1's monitor and fullscreen
are the list's first entry, copied into `[output]` by `config.load`.


`windows.json` as it already is:

```json
{"schema": "hyperspace.windows/1",
 "control": {"x": 2100, "y": 60, "w": 960, "h": 900, "screen": "Built-in Retina Display"},
 "render": [{"x": 1744, "y": 41, "w": 1280, "h": 820, "screen": "DELL U2720Q"},
            {"x": 3700, "y": 41, "w": 1280, "h": 820, "screen": "EPSON PJ"}]}
```

**The presenter.**

```python
class Presenter:
    """One output after the first: a moderngl handle on that window's
    context, its own copy / hands / dim programs and vertex arrays."""
    def __init__(self, ctx: moderngl.Context): ...
    def present(self, frame: int | None, frame_size, hands: int | None, readout: int | None,
                alpha: float, size, factor: float, bg_alpha: float = 1.0) -> None: ...
    def on_reload(self) -> None: ...
    def release(self) -> None: ...
```

`frame`, `hands` and `readout` are GL texture names from the renderer's
context, wrapped with `ctx.external_texture` (probed: it samples
correctly). `present` leaves the window's framebuffer bound.

*As built:* **`present(handoff, size, target=None)`** takes WP1's
`outputs.Handoff` instead of eight loose arguments (`target` is another
framebuffer on the presenter's context, for the tests); the wrapped
textures are cached per (name, size). Nothing is built before the first
`present`, and `on_reload` only marks it stale, because a reload runs in
whatever context is current (§7, "The presenter hand-off as built").

**The frame in `app.draw_render`.**

1. Make output 1 current; the stranded-target check; `ctx.screen.use()`.
2. Build the `View`s: output 1 with `target=ctx.screen`, the others with
   their `presenter` and framebuffer size.
3. `renderer.draw_outputs(...)`. It draws output 1 whole and leaves the
   frame textures for the rest.
4. `glFlush()` in output 1's context. Without it a presenter shows last
   frame's texture (measured, §1).
5. For each other output, in a `try`: make it current, `present`, swap.
   Its swap interval is 0.
6. Make output 1 current and swap (`finally`, as today). Its interval is
   1: it paces the loop (fork F6).

*As built* (`app._draw_render`): the six steps as written, except that
**the swap intervals are set once at the launch** (output 1's `1` where
`main` makes its context, each later one's `0` in `_open_presenters`),
not per frame, and **`glFlush` runs only when a later output exists**,
so a one-output frame runs nothing new. What output 1's view caught is
re-raised after the others were presented.

A presenter that raises sets its output's `error` and the loop goes on:
a failing output cannot take the frame down. `Keys` polls every output
window; `Mouse` stays on output 1; the loop ends when any window is
closed. `Host` gains `outputs: list[Output]`; `Host.output` stays the
first. `close_all`, `_restart` and `HYPERSPACE_FRAMES` are unchanged in
meaning (the smoke run closes output 1). Reload targets gain each
further `Output`, its backend and each `Presenter`.

**The watch.** `RenderWatch.info` returns the first output's state with
`presentable` true when **any** output is presentable, so "no render
frame presented for 2 s" means no output showed one. Each output not
presentable for 2 s while another is, or whose present raised, is
`watch.warn("output 2 (projector): …")`, once per message, with its
window state in the log.

### WP4 — The params and the OUTPUT page

**Owns:** `overlay.py` (`register_switches`), `app.py` (one call, seeding
from the config), `ui.py` (`_page_output`, the footer),
`tests/test_overlay.py`, `tests/test_ui_shell.py`, `tests/test_params.py`.

**Params**, generated per opened output N (1-based), like the FX params:

| Id | Label | Kind | Default |
|---|---|---|---|
| `output.N.scene` | "Scene" | toggle | on |
| `output.N.hands` | "Hands" | toggle | on |
| `output.N.through` | "Hands through effects" | toggle | off |
| `output.N.dim` | "Dim" | continuous 0–1 | 1 — **registered only with two or more outputs** |

With several outputs the label is prefixed with the output's name
("Glass scene"). All are in group `output` (session), `persist=False`,
`modulatable=False`: rig settings, like `output.fullscreen` and
`output.dim` beside them (fork F4). A preset or a show never moves them,
undo does not watch them (`undo.watched` needs `persist`), a launch
takes them from the config, and they can be learned onto a desk button
like any toggle. Nothing is put on the desk by this plan.

*As built:* `output.N.dim` is registered when **the config lists** two
or more outputs (not when two open: with the projector unplugged output
1 keeps its own dim row, so its launch dim is never a mystery), **or
when a lone listed output's entry sets `dim` under 1** (otherwise its
picture would be dimmed with no fader; the review of PR #124). Persisted
nowhere: every launch and every ⌘R starts from `config.toml`; undo, a
preset load or save and a show load or save leave them where they are
(`test_undo.py::test_the_output_switches_are_left_alone_by_undo_presets_and_shows`).

**The page.** Under the master dim, one block per output, two or three
lines (measured: the page's content is 392 px wide; a one-line row with
a name, three ticks, a slider and a status needs more than that):

```text
1  glass        ☑ scene   ☑ hands   ☐ through effects
   dim  ██████████████░░░░  80%                    (two or more outputs)
   shows: scene + hands over the effects · 64%
```

- "shows:" is `route`'s answer in words, with the product of the two
  dims: "scene", "scene + hands over the effects", "scene + hands
  through the effects", "hands", "hands through the effects", "black —
  nothing switched on", "black — dim 0". In the warning colour when
  black.
- Beside "hands" when it can show nothing: "ghost hands are off (HANDS
  page)" or "no tracker". Beside "through effects" with no effect on:
  "no effect on". *As built:* on a line of their own under the ticks
  ("hands: ghost hands are off (HANDS page) · through: no effect on"),
  shared with the output's present error, which comes first; beside the
  ticks they did not fit the page's width at the panel's legible size.
  Two more "shows:" phrases: "black — the scene is off and no hand
  shows" and "black — master dim"; the footer names several outputs
  together ("· outputs 2, 4 black"); with two or more outputs the line
  under the blocks reads "paced by output 1 · frame W×H · below: output
  1's window".
- An output the config lists but that did not open: one disabled line,
  "2 projector — screen 2 is not connected".
- One line under the blocks: "paced by output 1 · frame 1920×1080", and
  an output's `error` in the warning colour.
- The existing rows (monitor, fullscreen, overlay and its three) follow,
  unchanged; they are the first output's.
- **The footer** (`ui.py`, where it prints `· dim 40%`): `· output 2
  black` while an output shows nothing for a reason other than the
  master dim, on every page.
- It fits: with four outputs drawn as six-column rows plus two lines,
  and overlay's rows showing, 307 px were left under the page at the
  control size. Three lines per output need about 65 px more than that
  probe used and still leave room.

### WP5 — PR #78, reviewed

PR #78 (Dillon's ghost hands; `ghost.py`, `hands/tape.py`,
`tools/hands_tape.py`, the skeleton in `hands/core.py`) was read whole,
its tape tool run (`synth`, `info`, `shots` all work on a temp home) and
its pass timed. It is careful work: all-or-nothing program builds, the
target bound on every exit, nothing touched when off. Findings, each
with its fix:

| # | Finding | Where | Fix |
|---|---|---|---|
| R1 | **A raising hands pass skips the master dim and fails the frame.** `_draw_frame` calls `self.ghost.draw(…)` unguarded and `dim_pass` after it. `Ghost.poses` has no guard: a skeleton with a ragged `digits` list (a hand-edited tape) raises in `pose()`, a font problem raises in `TetherLabels._label`. The crossfader at black would then show a full-bright frame. | `render.py::_draw_frame`, `ghost.py::poses`, `draw` | Guard the hands in `_draw_frame` as `_face_picture` is guarded: `Ghost.error` says why, the frame goes on to the dim. `Ghost.draw`'s `finally` also re-enables `BLEND` (today it relies on `Renderer.draw`'s). Test: a source whose skeleton is malformed leaves a dimmed frame and an error line. |
| R2 | **The render stack writes a parameter.** `_draw_tethers` sets `self.state.tethers = False` when the labels cannot build. `state.tethers` is what `ghost.tethers` reads; `Registry.apply` adopts a raw write as a new base. ARCHITECTURE §3: the render stack only reads. | `ghost.py::_draw_tethers` | A private `_labels_failed` flag; the param is left alone; the HANDS page shows `Ghost.error`. |
| R3 | `_ensure` is not all-or-nothing. It sets `self.size` and `self._tex` before the renderbuffers; if one of those raises, the next frame returns early (size and texture match) with `_fbo` `None` and raises every frame. | `ghost.py::_ensure` | Build into locals, assign at the end, release on failure, record `error`. |
| R4 | Cost. The hands' pass is 0.93 ms at 1920×1080 and 3.4 ms at 3024×1964 (two hands; 0.2 ms of it Python). The layer is the target's full size with 4× colour and depth. | `ghost.py::_ensure`, `SAMPLES` | None at 1080p, the rig's size. Noted for the laptop's own screen; a size cap is fork F11, not taken. |
| R5 | `Renderer.on_reload` calls `self.ghost.on_reload()`, and the reloader calls the same hook for the `Ghost` target (`app.main`'s target list): the programs can be rebuilt twice in one round, and are rebuilt on a `render.py` save that did not touch them. | `render.py::on_reload` | Remove the call from `Renderer.on_reload`. |
| R6 | The screentop and HMD bases (`ghost.MODES`) are guesses, as the author says. Both are proper rotations (determinant +1, by arithmetic), so neither mirrors by accident. Whether they are the right rotations can only be seen at the rig. | `ghost.py::MODES` | Check Q9. With a mode other than desktop the HANDS page says "ghost axes for this mode are unmeasured". |
| R7 | The bindings' names, flagged as assumed. Read against the pinned `leap` package (`leap/datatypes.py`): `Hand.thumb … pinky`, `.arm`, `.palm`; `Digit.metacarpal … distal` and `.bones`; `Bone.prev_joint`, `.next_joint`, `.width`, `.rotation`; `Quaternion.x y z w`; `Palm.position`, `.normal`, `.direction`, `.width`. All match `hands.core.skeleton`. | `hands/core.py::skeleton` | None. Not seen with a live camera (Q9). |
| R8 | `skeleton()` runs on the SDK thread for every tracking frame, ghost on or off. The author kept it (SDK objects must not outlive the callback). Its cost was not measured here. | `hands/core.py::_frame` | None. |
| R9 | No real tape exists: `tests/fixtures/` is not in the tree, so the replay test skips. | `tests/test_hands_tape.py` | Q9 records one. |
| R10 | A `[hands] tape` that is missing or malformed raises in `HandsIO.__init__`; `app._open_hands` prints to stderr and returns `None`. On the panel that is "no hands" with no reason. | `app.py::_open_hands` | Append the message to `cfg["notes"]` (the SYSTEM page). |
| R11 | The guide's rows are drawn by `CapsuleHands.draw` (§1 row 5). | `ghost.py` | WP6. |
| R12 | `ghost.on`, `.mirror`, `.guide` and `.tethers` are `modulatable` (the test asserts it). A performer's row on `ghost.mirror` would flip the hands with a hand's move. | `ghost.py::register` | `mirror`, `guide`, `tethers` and the new `style` become `modulatable=False`; `on` and `alpha` stay (the PR says they are meant to be learned). The test changes with it. *As built:* reverted in WP5 (a hand Learn would have written a dead row, `learn_source` never checked the target) and built in WP6 together with that check and a preset-load drop (§7, WP6). |
| R13 | `pose()` falls back to `85.0`, a second copy of `hands.core.PALM_W`; `tape.STALE_S` is a second copy of core's (said in a comment). | `ghost.py`, `hands/tape.py` | `pose()` imports the constant lazily, as `box_of` does; the tape's stays (a leaf). |
| R14 | Check 47 has never been run; its (g) "effects never touch it" is now the default of a switch. | `11-hand-checks.md` | Q9 and Q4. |

**Owns:** `ghost.py` (the lines above), `render.py` (the guard and the
`on_reload` line), `app.py::_open_hands`, `hands/panel.py` (one line),
`tests/test_ghost.py`, `tests/test_render.py`.

### WP6 — `ghost.style`

**What.** One enum, `ghost.style`, picks what is drawn from the same
poses. Session, persisted, not modulatable, on the HANDS page under
"Ghost hands". It replaces nothing: it is the "swappable" of decision 33.

![Candidate styles, an offscreen render from a probe script](assets/21-outputs-and-the-hands/styles.png)

| Style | What is drawn | Reads |
|---|---|---|
| HANDS | The capsule hands, today's. The default. | joints, bone widths |
| JOINTS | A bead per joint, larger at the fingertips, one at the palm. | joints |
| PALMS | An orb per palm that swells as the hand opens, a ring in the palm's plane, a spoke where the fingers point. | palm frame, openness |
| CAGE | A wire octahedron round each hand: it turns with the palm and breathes with the grip. A small polytope in each hand. | palm frame, openness |
| MARIONETTE | A bead per fingertip, hung on strings from a bar above each hand. | fingertips |

"Openness" is the mean fingertip distance from the palm over the palm's
width, 0 for a fist, 1 open: computed from the pose, no new data and no
route.

**Contract.**

```python
STYLES = ["HANDS", "JOINTS", "PALMS", "CAGE", "MARIONETTE"]

class Geometry:                       # was CapsuleHands' drawing half
    def draw(self, poses, view_proj, eye, parts, extra=((), ())) -> None: ...

def hands_parts(p: HandPose) -> tuple[list, list, list]: ...      # CapsuleHands.parts, moved
def joints_parts(p), palms_parts(p), cage_parts(p), marionette_parts(p)
PARTS = (hands_parts, joints_parts, palms_parts, cage_parts, marionette_parts)
```

A style is a pure function from one `HandPose` to (spheres, tubes,
triangles): no GL, testable without a context. The guide's rows are
passed to `draw` as `extra` by `Ghost`, so no style knows the guide
exists. `CapsuleHands` stays as a name for `Geometry` drawing
`hands_parts`. A palm-only pose (no digits) draws a palm orb in every
style. The fade, the colours, the camera, the guide and the tethers are
the same in every style.

*As built:* **`extra` is a list aligned with the poses** (each pose's
guide rows), not one `((), ())` pair, so the instances are drawn in the
old order and even exact depth ties resolve as before; `parts=None`
draws only the extra rows. **HANDS keeps its palm disc** for a
palm-only pose (byte-for-byte wins); the other four draw a palm orb
(0.32 × palm width). In the four new styles **the guide is drawn on top**
(the style, then the depth cleared, then the guide), because their palm
solids hid an ON HAND gauge; in HANDS it stays partly behind the palm as
before (the review of PR #122). `style_parts(i)` falls back to HANDS for
an index out of range or not a number.

**Owns:** `ghost.py`, `hands/panel.py` (one combo), `tests/test_ghost.py`,
a `styles` command in `tools/hands_tape.py` (the demo sheet).

### WP7 — Docs, decisions, hand checks

**Owns** the shared documents and nothing else: `ARCHITECTURE.md` (§1
Render stack and Host rows, §2 the frame and "the ghost hands are the
frame's last pass"), `ENGINEERING.md`, `DECISIONS.md` (the two rows
below), `DECISION-REGISTER.md` (the forks of §6 as rows after 56 — *as built:*
rows 79–88, after plan 19's 72–78),
`plans/README.md`, `CHECKPOINT.md`, `11-hand-checks.md` (group Q, check
47 marked as carried into Q9), `config.py`'s docstring is WP3's, and
this plan's §7.

The two DECISIONS rows this plan changes, and only these:

- **2026-09-18 "Two GLFW windows on one GL context; the render window
  has no imgui at all"** becomes superseded by: one control window and a
  list of render outputs, each its own window in one share group; **no
  imgui on any output** stands.
- **2026-10-04 "The ghost hands are the frame's last pass … never in the
  look-back history"** stays standing as the default of a per-output
  switch. With "hands through effects" on, that output's hands go in
  before the effect chain. "Never in the look-back history" stands in
  every state.

## 3. Parameter budget

| Added | Count | Replaces, or why nothing |
|---|---|---|
| `output.N.scene`, `.hands`, `.through` | 3 per output | Nothing: the owner's ask, per output. |
| `output.N.dim` | 1 per output, only with two or more | Nothing with two; with one output the master dim is that output's dim, so none is added. |
| `ghost.style` | 1 | Nothing: decision 33's "swappable". |
| Pages, menu items | 0 | The OUTPUT page gains a block per output. |
| On the desk | 0 | Unless the owner learns one. |

One output: 4 new params (3 switches, the style). The rig: 9. The
ceiling, four outputs: 17. They are generated in a loop for the outputs
the config opens, as `fx.declare` generates an effect's, so the registry
on a laptop never carries a projector's switches. The two fit and pacing
choices (forks F5, F6) are constants, not params.

## 4. What this plan does not change

- **The control model** (ARCHITECTURE §3). The render stack only reads:
  `outputs.Switches` is written by the registry and read by the
  renderer, and finding R2 removes the one write the hands made.
- **No imgui on any output.**
- **Rig settings never persist in a preset**; the new params are not in
  the show either.
- **Overlay only when the config asks** (decision 21), and only on the
  first output; every other output is created opaque.
- **`output.dim`**: the crossfader, never saved, 1 at launch, not
  modulatable, after everything on every output; in overlay it fades
  colour and alpha (rows 28, 40, 41).
- **`ghost.*` are session params, off by default**; the skeleton is
  display only; the interaction box frames the hands and a hand outside
  it fades (plan 18 rows 50–51, read from `ghost.box_of` on
  `plan-18-integration`).
- **A render frame binds its target explicitly** and puts it back on
  every exit.
- **Window placement** (row 48): the config beats the file, the file is
  written at the exits only, fullscreen is never remembered.
- **Effects are `.glsl` files**; no effect is edited. `lookback.py` and
  `fx.py` are not edited at all.
- **The face target** (plan 20): finished before the scene pass, known
  to nothing here. The scene pass still starts at (0, 0), which
  `u_pic_fb` assumes.

## 5. Exit criteria

### Headless: named tests

WP1 and WP2, `tests/test_outputs.py`, on an offscreen pair of targets:

- `test_one_default_output_is_todays_frame_byte_for_byte` (effects on and
  off, hands on and off, 0 and 4 samples, against `Renderer.draw` on the
  parent commit's path)
- `test_the_frame_through_a_texture_is_the_same_bytes`
- `test_each_of_the_eight_states_shows_its_picture` (states 3 = 4 and
  7 = 8; 1 holds undistorted hand pixels; 2 and 6 differ from 1 and 5
  where the hands are; 5 is hands on the ground)
- `test_two_outputs_with_the_same_switches_run_the_chain_once`
- `test_outputs_that_differ_run_one_chain_per_distinct_input`
  (`Renderer.stats`, the table of §2)
- `test_through_with_no_effect_on_is_hands_over`
- `test_through_with_no_hand_showing_runs_nothing_extra`
- `test_the_history_never_holds_the_hands_in_any_state`
- `test_capture_runs_once_a_frame_whatever_the_switches`
- `test_an_opaque_grounds_alpha_is_untouched_in_every_state`
- `test_overlay_adds_the_hands_coverage_before_or_after`
- `test_each_output_dims_by_master_times_its_own`
- `test_an_output_of_another_aspect_is_letterboxed_and_the_hands_stay_registered`
- `test_the_first_target_is_bound_after_a_view_raises`
- `test_the_guide_is_never_distorted`
- `test_route` (pure: every row of the route table)

WP3:

- `test_config.py::test_no_screens_list_is_one_output_as_today`,
  `::test_a_screens_list_wins_over_the_scalar_keys_with_a_note`,
  `::test_a_fifth_screen_is_dropped_with_a_note`,
  `::test_a_config_dim_cannot_launch_an_output_black`
- `test_app_boundary.py::test_one_window_per_listed_output`,
  `::test_a_later_output_whose_screen_is_absent_is_not_opened`,
  `::test_the_exits_save_one_rect_per_output`,
  `::test_only_the_first_output_waits_for_the_screen`,
  `::test_a_raising_presenter_does_not_stop_the_frame`,
  `::test_the_rendering_context_is_flushed_before_a_presenter`
- `test_watchdog.py::test_one_dark_output_of_two_is_a_warning_not_a_stall`,
  `::test_no_output_presenting_is_the_stall`

WP4:

- `test_overlay.py::test_the_output_switches_are_rig_settings`,
  `::test_one_output_has_no_dim_of_its_own`
- `test_ui_shell.py::test_every_page_fits_the_control_window` with four
  outputs, `::test_the_output_page_says_what_each_output_shows`,
  `::test_the_footer_names_a_black_output`

WP5: `test_render.py::test_a_raising_hands_pass_still_dims`,
`test_ghost.py::test_a_failed_label_build_writes_no_param`,
`::test_a_failed_target_build_is_all_or_nothing`.

WP6: `test_ghost.py::test_every_style_draws_from_the_same_poses`,
`::test_a_style_never_draws_the_guide`,
`::test_a_palm_only_hand_draws_in_every_style`,
`::test_hands_is_the_old_geometry_byte_for_byte`.

The whole suite green, `ruff` clean, `HYPERSPACE_FRAMES=120` exits clean
on a temp home with no `screens` list and with a two-entry list on one
screen (`monitor = -1` on both).

*As built:* every name above exists and passes on
`plan-21-integration` (`test_overlay_adds_the_hands_coverage_before_or_after`
is WP1's `…_after`, renamed by WP2). WP4's undo / preset / show test,
which the plan put in `test_params.py`, is
`test_undo.py::test_the_output_switches_are_left_alone_by_undo_presets_and_shows`;
`test_every_page_fits_the_control_window` runs with four outputs (its
rig carries them), beside
`::test_the_output_page_fits_with_four_outputs_and_overlays_rows`. The
tests the build added beyond the list are named in §7. The scripted
launches (150–330 frames, temp homes) ran with no list and with a
two-entry list on the laptop's one screen, `monitor = -1` on both.

### At the machine

Group Q, in full in the appendix. Check 47 is finished as Q9.
*As built:* group Q in `11-hand-checks.md` is checks **99–112**; check
47 is finished by check 108 (its (g) is check 103).

## 6. Forks

Each was settled by the recommendation, for the owner to confirm or
overturn (register rows after 56, WP7).

### F1. Where "before" puts the hands

| Option | Consequence |
|---|---|
| **(a) After the look-back composite, before the first effect** | The effects distort the hands. The echoes and the dream never hold them: the 2026-10-04 row's "never in the history" stands. One history serves every output. |
| (b) Onto the scene before the look-back composite | The hands also trail in the echoes and feed the dream. The history is shared, so an output with hands off or "over" would still show hand echoes: the switches would stop being per output. Fixing that needs a second history and a second dream worker. |

**Taken: (a).** The owner said "the shader pipeline", and the effect
chain is the part that distorts. Cost to reverse: (b) for all outputs at
once is a few lines; (b) per output is a second look-back ring, M–L.

### F2. Is "hands through effects, scene off" a state

**Yes** (the owner counts eight): the hands alone through the effect
chain on the ground, with no echoes. The alternative, treating it as
hands over, would make two switch states the same picture for no reason.
Reverse: one row of `route`.

### F3. The guide and the tethers' labels

| Option | Consequence |
|---|---|
| (a) They follow the hands | Nothing to build. Text through kaleido cannot be read, and the guide exists to be read. |
| **(b) Always composited after** | Legible in every state. A second layer, drawn only while the guide is on and a through pipeline runs; otherwise today's single layer, bit for bit. |

**Taken: (b).** Reverse: delete the readout layer, S.

### F4. Are the switches saved

| Option | Consequence |
|---|---|
| (a) Session params saved in the show | A show made on the rig names `output.2.*` on a laptop that has no second output. A factory show would carry a rig's arrangement. |
| **(b) Rig settings: not saved, launch values from the config** | ⌘R and a relaunch come back to what `config.toml` says. A switch flipped at the party lasts until the restart. |

**Taken: (b)**, with optional `scene` / `hands` / `through` / `dim` keys
per screen. Per-output dim follows the same rule and the config cannot
set it under 0.1; the master stays 1 at launch. Reverse: flip `persist`,
S.

### F5. Outputs of another size or aspect

| Option | Consequence |
|---|---|
| **(a) Letterbox: the whole frame, centred, aspect kept** | Nothing cropped; the tethers' labels at the edges stay in view. Bars are black, which on a Pepper's Ghost glass is nothing at all. |
| (b) Cover: fill, crop the overhang | No bars; the frame's edges are lost on one output. |
| (c) Stretch | Circles become ovals. |
| (d) Render the scene per output at its own size | Each output pixel-exact; the scene, look-back and effects run per size, and the look-back history has one size. L. |

**Taken: (a)**, a constant. The frame is the first output's size; the
hands' layer has the frame's aspect and is laid in the same rect, so the
hands stay registered with the scene on every output. List the larger
screen first. Reverse to (b) or (c): `outputs.fit`, a few lines.

### F6. Swap timing

**Taken: the first output's swap waits for its screen, the others' do
not.** Measured here: 121 fps against 60–81 with two waiting swaps.
*As built:* built so, but the 121 fps was not reproduced: the build's
launches ran unpaced with one output and with two (270–380 fps), so this
fork's frame-rate reason is unconfirmed (§1's table; hand check 107).
Reverse: one `swap_interval` call per output. Not measurable without a
second screen: tearing on a non-waiting fullscreen output (macOS
composites whole windows, so none is expected), two screens of
different refresh rates (the second repeats or drops frames), and real
fullscreen on two monitors.

### F7. `ghost.on` and the per-output hands switch

| Option | Consequence |
|---|---|
| **(a) Both: `ghost.on` is "the hands are drawn at all", the output's switch says where** | One-output rigs behave as today with the new switch left on. One learned button still takes the hands off everywhere. Two places can hide the hands; the OUTPUT page says which. |
| (b) The output switches replace `ghost.on` | One place. Breaks saved shows and learned rows on `ghost.on`; no single off. |

**Taken: (a).** Reverse: M (a migration).

### F8. What the control view shows

| Option | Consequence |
|---|---|
| **(a) Words: each output's "shows:" line, the footer naming a black output** | No GL in the control window beyond what there is. |
| (b) A small live picture per output | A true thumbnail needs each output's compose run again into a small texture (the hands-over and the dim are not in any shared texture). About 0.5 ms per output and a page that must still fit. |

**Taken: (a).** Reverse: S–M to add (b) later.

### F9. A listed screen that is not connected

**Taken: output 1 always opens (today's rule); a later output with an
index no screen has is not opened**, with a note. A third window landing
on the laptop over the controls is worse than a missing one. Reverse:
one branch in `_windows`.

### F10. Monitor and fullscreen for later outputs

**Taken: the config says; no live params.** `output.monitor` and
`output.fullscreen` stay the first output's. Adding them per output is
two more params each. Reverse: S.

### F11. A size cap on the hands' layer

Not taken. At 1080p the pass is under 1 ms. A cap would soften the hands
on a retina screen and end byte-identity there. Revisit if Q6 shows the
laptop's own screen dropping frames.

### F12. Which context renders

| Option | Consequence |
|---|---|
| **(a) The first output's (today's)** | One output is today's code path. The first output cannot be absent. |
| (b) A hidden window owns everything; every output is a presenter | Symmetric; every frame takes the texture road, and the scene's sample count stops following a window. |

**Taken: (a).** Reverse: M.

## 7. As built

Built 2026-10-04 by the unattended run, one PR per work package onto
`plan-21-integration`, merged by the orchestrator in the plan's order
(5; 1 and 2; 6; 3 and 4), with plans 19 and 20 merged underneath
(b7aa67a, 284d754; conflicts only in `hotreload.MODULES` and two test
files, both append against append). On that branch: **1549 passed, 1
skipped** (the tape replay, R9), `ruff` clean. Every fork of §6 was
settled as recommended, by the orchestrator, not the owner (register
rows 79–88). **The owner asked for three things** this plan builds: two
render outputs each with a dim, the scene on/off and the hands on/off
(roadmap decision 32); the ghost hands finished as a HUD with swappable
drawn objects (decision 33); and, on 2026-10-04 during the run, the
third per-output switch, **hands through effects** (eight states per
output).

What each piece of evidence is: a **test** is headless (offscreen GL
targets, fake window systems); an **offscreen render** is a picture made
by a tool from synthetic hands; a **real launch** is the app on this
laptop's one screen against a temp home, its windows **read back by a
script** — nobody looked at a window by eye; nothing here has met the
glass, the projector, a second screen or a real hand.

### WP5 — PR #78 reviewed (PR #112, merged b49b61a)

**Built.** The fourteen findings, with two of the build's own:

| # | As built |
|---|---|
| R1 | `_draw_frame` guards the hands as it guards the faces: a raise leaves the frame without hands, `Ghost.error` (the first reason) on the HANDS page, the target bound again and **the dim still runs**. `Ghost.draw`'s `finally` re-enables BLEND. |
| R2 | `_draw_tethers` writes no param: a private `_labels_failed`; the hands and the guide still draw; switching the ghost off and on, or a reload, retries. `TetherLabels.__init__` is all or nothing. |
| R3 | `_ensure` builds into locals, releases on failure, records the error once, returns False; the next frame tries from nothing. |
| R4 | No change. Pass 1.22–1.60 ms at 1920×1080, 2.13–2.19 ms at 3024×1964 (medians between `glFinish`, standalone context; they differ from §2's 0.93 / 3.4 ms by the method). |
| R5 | `Renderer.on_reload` no longer calls `ghost.on_reload`. |
| R6 | With the ghost on in `screentop` or HMD mode the HANDS page says those axes are unmeasured; the maths is unchanged. |
| R7 | None (the names match the pinned `leap`). |
| R8 | None: `skeleton()` 27 µs per two-hand frame on fake namespaces; real `leap` objects not measured. |
| R9 | None: no real tape exists; the replay test still skips (hand check 108 records one). |
| R10 | A bad `[hands] tape` is a note on the SYSTEM page, and the HANDS page shows it in place of "tracker off". |
| R11 | Left for WP6 (done there). |
| R12 | **Built, then reverted** (dc327ab and its revert): the review showed a hand Learn would write a dead row onto a non-modulatable `ghost.mirror` while the footer said it worked, because `learn_source` never checked the target. Built in WP6 together with that check. |
| R13 | `pose` uses `hands.core.PALM_W`; `STALE_S` lives in `hands/tape.py` only and `core` imports it. |
| R14 | Check 47 is finished by group Q (this package's docs, WP7). |
| A1 | `_build_failed` apart from `error`, so one bad frame before the first build does not keep the hands off until a reload. |
| A2 | The ghost's controls on one line (on, mirror, opacity, guide, tethers), at most one more line under it: the HANDS page already scrolled with the ghost on. |

**Tests.** `test_render.py::test_a_raising_hands_pass_still_dims[skeleton,geometry]`,
`test_ghost.py::test_a_failed_label_build_writes_no_param[build,label]`,
`::test_a_failed_target_build_is_all_or_nothing`,
`::test_one_reload_round_rebuilds_the_ghost_once`,
`test_hands_tape.py::test_a_bad_tape_path_is_a_note_the_pages_show`,
`::test_the_stale_time_and_the_palm_width_are_defined_once`,
`test_ui_shell.py::test_the_hands_page_says_the_ghost_axes_are_unmeasured`,
`::test_the_hands_page_says_why_the_ghost_or_the_tracker_is_off`,
`::test_the_hands_page_fits_with_every_ghost_line`. Each failed on the
code before its fix (the builder swapped the old files back in).

**Demo.** [`ghost-guard.png`](assets/21-outputs-and-the-hands/ghost-guard.png)
(offscreen: the hands at dim 0.5; the pass forced to raise, the scene
dimmed with no hands, byte-equal to the frame without hands; the scene
at dim 1) and [`ghost-review.txt`](assets/21-outputs-and-the-hands/ghost-review.txt)
(the findings and timings). **Real launch:** 150 frames with a synthetic
tape, the ghost, guide and tethers switched on by a script and the dim
at 0.5 from frame 91: nothing raised, `ghost.error` empty, the stall log
empty; the window was not looked at.

**Not verified.** No camera, no real hand, no rig; screentop / HMD not
seen; a font failure only simulated; R5 tested by calling the hooks in
the reloader's order, not by a real module reload.

### WP1 — The compose path (PR #118, merged with WP2 as 97a24d7)

**Built.** `outputs.py` (`MAX_OUTPUTS`, the keys and `NAMES`,
`Switches`, `route`, `fit`, `View`, `Handoff`), `Ghost.layer` /
`composite` / `tex` with `draw` as the two together, and
`Renderer.draw_outputs(s, w, h, dpr, views, t_now=None)` with `stats`.
**`Renderer.draw` is `draw_outputs` with one default `View` on the bound
framebuffer's viewport**, and raises what that view caught after the
frame finished, where it raised before. `"outputs"` is in
`hotreload.MODULES` after `"ghost"`, before `"view"` and `"render"`.

**Differs from the plan, and why.** Routing runs after the hands' layer
(F7 needs "a hand visible this frame"). Frame textures are always
LINEAR (the 1:1 copy reads by `texelFetch`). `stats` has `captures` and
`layer` (and WP2's `readout`); `View` has `viewport`, `handoff`, `exc`.
A pipeline that raises leaves its outputs showing their ground (the plan
did not say). `View.bg_alpha` is honoured in part: an output's ground
can make the frame opaque on it, never see-through (the review; overlay
is output 1's only). The presenter's rect is `fit()` inside the view's
rect (the review, d8100f6).

**Tests.** New `tests/test_outputs.py`: `test_route`, `test_fit`,
`test_a_view_defaults_to_its_whole_size`,
`test_outputs_imports_nothing_from_app_ui_or_params`,
`test_one_default_output_is_todays_frame_byte_for_byte` (7 cases × MSAA
0 / 4 against `_parent_draw`, a verbatim copy of the parent's
`draw` / `_draw_frame`), `test_the_frame_through_a_texture_is_the_same_bytes`,
`test_two_outputs_with_the_same_switches_run_the_chain_once`,
`test_outputs_that_differ_run_one_chain_per_distinct_input`,
`test_the_four_scene_and_hands_states_show_their_pictures`,
`test_capture_runs_once_a_frame_whatever_the_switches`,
`test_the_echoes_carry_on_with_the_scene_off_everywhere`,
`test_the_history_never_holds_the_hands_in_any_state`,
`test_each_output_dims_by_master_times_its_own`,
`test_an_output_of_another_aspect_is_letterboxed_and_the_hands_stay_registered`,
`test_an_opaque_grounds_alpha_is_untouched_in_every_state`,
`test_the_first_target_is_bound_after_a_view_raises`,
`test_a_raising_pipeline_leaves_its_views_on_the_ground_and_the_rest_drawn`,
`test_a_raising_hands_pass_costs_no_output_its_frame_or_its_dim`,
`test_the_presenter_handoff`,
`test_a_renderer_from_before_the_outputs_still_draws_and_reloads`;
`test_ghost.py::test_one_layer_composites_onto_many_targets_as_draw_does`;
`test_hotreload.py::test_outputs_is_watched_before_render`. No existing
test was edited. **Byte identity beyond the tests:** 320 default-path
cases (effects × echoes × ghost × dim × MSAA × ground) hashed on the
parent and after each commit — all identical (the script is not kept).

**Demo.** [`outputs-compose.png`](assets/21-outputs-and-the-hands/outputs-compose.png)
(`tools/outputs_shots.py compose`, offscreen, synthetic hands): one
640×400 frame on two outputs, the second 400×400 and letterboxed at its
own 60 % dim. **Real launch:** 150 frames on the default path only (the
app still called `Renderer.draw`): one direct pipeline, nothing raised.

**Not verified.** One GPU; offscreen targets; the presenter test a
stand-in on the same context; no timing for WP1 alone.

### WP2 — Hands through effects (PR #120, stacked on #118, merged as 97a24d7)

**Built.** `route`'s through rows (only with an effect on and a hand
shown: scene on → SCENE+HANDS, scene off → HANDS, fork F2). In
`Renderer._pipeline`: **SCENE+HANDS** = `fx.begin` → `lb.composite(scene)`
→ the hands (`Ghost.composite(buf, (0, 0, size), opaque=fx.opaque)`) →
`fx.run(dst)`; **HANDS** = `fx.begin` → clear to `(0, 0, 0,
Renderer.bg_alpha)` → the hands → `fx.run(dst)`, no look-back. A hands
composite that raises inside a pipeline leaves the chain running on the
scene alone and `Ghost.error` saying why. **The readout layer** (fork
F3): `Ghost.layer(size, t, readout=…)` asks for it only when an effect
is on and some output has its hands and through ticks on; it splits only
while the guide is on and its target builds — then the hands' layer has
the hands alone and `Ghost.readout` has the hands depth-only (so an ON
HAND gauge stays behind the palm), the guide's spheres and tubes, and
the tethers; `Ghost.composite_readout` lays it on **every output whose
hands tick is on, over or through**, after the hands and before the dim.
Otherwise the single layer, bit for bit. `stats["readout"]`.

**Differs from the plan, and why.** **The capture runs once, after all
pipelines** (the review: with echoes on, a capture before
SCENE+HANDS's composite gave the through output this frame doubled as an
echo, one echo short and every echo a frame older; fixed in 29c3e4c).
moderngl applies a framebuffer's `color_mask` only on `use()`, so the
first depth-only pass wrote colour until each mask change was followed
by a `use()` (caught by the readout test). The readout is skipped if its
target fails to build (`Ghost.error` says why); `composite_readout` is
an addition; the HANDS ground is the frame's, not the view's.

**Tests.** `test_outputs.py`: extended `test_route`,
`test_outputs_that_differ_run_one_chain_per_distinct_input`,
`test_capture_runs_once_a_frame_whatever_the_switches`,
`test_the_history_never_holds_the_hands_in_any_state`,
`test_an_opaque_grounds_alpha_is_untouched_in_every_state` (all eight
states × no effect, warp, warp + kaleido),
`test_overlay_adds_the_hands_coverage_before_or_after` (renamed); new
`test_each_of_the_eight_states_shows_its_picture`,
`test_two_pipelines_show_the_same_echoes` (the review),
`test_through_bends_the_hands_with_the_shape`,
`test_through_with_no_effect_on_is_hands_over`,
`test_through_with_no_hand_showing_runs_nothing_extra`,
`test_four_outputs_need_at_most_three_chain_runs`,
`test_the_guide_is_never_distorted[beside|on hand]`,
`test_a_raising_hands_composite_into_the_chain_still_runs_it`,
`test_the_presenter_handoff_carries_the_readout`;
`test_ghost.py::test_the_readout_layer_is_the_guide_apart_from_the_hands`.
The 320-case default-path matrix still identical.

**Demo** (offscreen, synthetic hands, `tools/outputs_shots.py`):
[`eight-states.png`](assets/21-outputs-and-the-hands/eight-states.png)
(regenerated from the build; three pipelines, three chain runs, one
capture), [`through-two-outputs.png`](assets/21-outputs-and-the-hands/through-two-outputs.png)
(the glass over, the projector through, the guide the same and unbent
on both), [`compose-timing.txt`](assets/21-outputs-and-the-hands/compose-timing.txt):
1920×1080, warp + kaleido, two synthetic hands, standalone context, each
frame ended by `glFinish` — one view 1.66 ms median, two agreeing 1.85
ms, two disagreeing (over | through) 2.24 ms. **Rendering only**: no
swap, no second window, no flush or presenter cost.

**Not verified.** The same as WP1; "legible" and "bent" are judged from
the offscreen images, not the glass.

### WP6 — `ghost.style` (PR #122, merged b231079)

**Built.** `ghost.style` (HANDS, JOINTS, PALMS, CAGE, MARIONETTE): a
session enum, **saved with the show, not modulatable**, learnable onto a
desk control, on the HANDS page as a 150 px STYLE combo leading the
ghost's second line while the ghost is on (a line of its own pushed the
page 22 px past the window). Each style is a pure function in
`ghost.PARTS`; `ghost.Geometry.draw(poses, view_proj, eye, parts,
extra)` draws whichever is picked into the same hands' layer, so over,
through, the readout, the guide and the tethers behave as with HANDS;
`CapsuleHands` stays as a name (a `Geometry` that draws HANDS).
Openness is the mean fingertip distance from the palm over the palm
width, mapped 0.45 → 0 (a fist), 1.35 → 1 (open).

| Style | What it is made of |
|---|---|
| HANDS | The capsule hands, byte for byte as before: a sphere per joint, a capsule per bone, the palm and the thumb web; a palm-only hand is the palm ellipse. The default. |
| JOINTS | Beads only: small at the metacarpals' bases, larger at knuckles and mid joints, largest at the tips (0.12 × palm width), one at the palm (0.17 ×). |
| PALMS | An orb at the palm, 0.2 → 0.4 × palm width as the hand opens; a 24-segment wire ring (0.78 ×) in the palm's plane; a spoke where the fingers point, ending in a bead. |
| CAGE | A wire octahedron (12 tubes, 6 corner beads) in the palm's frame, longest along the fingers, 0.55 → 1.1 × palm width with openness; inside, a small solid octahedron turned 45°. |
| MARIONETTE | A bead per fingertip on a string from a level bar 1.6 × palm width above the highest tip; a crossbar pointing the fingers' way and a string from its front to a bead at the palm. |

**R12 with it.** `ghost.mirror`, `.guide`, `.tethers` (and `.style`) are
`modulatable=False`; `on` and `alpha` stay modulatable. **`Learn.learn_source`
refuses a non-modulatable target in words** ("Ghost mirror can't follow
a hand (not modulatable) — not learned; Learn desk puts it on a
button") and makes no row; **`Presets.load_doc` drops a saved route onto
a known non-modulatable param** with the note `dropped <source> →
<target>: not modulatable`, the file not rewritten (an unknown target
id is still kept, dormant). 90 files and 984 routes in the factory
presets, the library and `shared/dan-2026-10-04` were scanned: none aims
at such a param; the owner's home was not read.

**Differs from the plan, and why.** `extra` is per pose, not one pair
(the old instance order, so depth ties resolve as before). HANDS keeps
its palm disc for a palm-only pose (byte-for-byte wins); the others draw
an orb (0.32 ×). **The guide is drawn on top in the four new styles**
(the review: their palm solids hid an ON HAND gauge's 5.5 mm balls;
0db74f9); in HANDS it stays partly behind the palm. `style_parts` falls
back to HANDS for a bad index. Two tests that patched
`CapsuleHands.draw` now patch `Geometry.draw`.

**Tests.** `test_ghost.py::test_every_style_draws_from_the_same_poses`,
`::test_a_style_never_draws_the_guide`,
`::test_a_palm_only_hand_draws_in_every_style`,
`::test_hands_is_the_old_geometry_byte_for_byte` (36 cases against a
frozen copy of the parent's), `::test_the_guide_on_the_hand_reads_the_same_in_every_style_but_hands`,
`::test_the_params_are_session_off_by_default_and_learnable` (updated:
only `on` and `alpha` modulatable),
`test_outputs.py::test_every_style_behaves_as_the_hands_in_every_state`,
`test_learn.py::test_a_hand_learn_onto_a_setting_is_refused_in_words`,
`test_presets.py::test_a_saved_route_onto_a_setting_is_dropped_with_a_note`,
`test_ui_shell.py::test_the_ghost_style_is_on_the_hands_page_while_the_ghost_is_on`.
148 hashes (layers and whole frames) equal on the parent and the branch.

**Demo** (offscreen, synthetic hands): [`ghost-styles.png`](assets/21-outputs-and-the-hands/ghost-styles.png)
(`tools/hands_tape.py styles`: the five side by side, both hands open
and one a fist) and [`style-through.png`](assets/21-outputs-and-the-hands/style-through.png)
(CAGE over and through warp + kaleido, the guide and labels unbent on
both). [`styles.png`](assets/21-outputs-and-the-hands/styles.png) is the
plan's probe of candidate styles, not the build. **Real launch:** 330
frames twice, `ghost.style` stepped 0 → 4 by a script: nothing raised,
`ghost.error` empty, the stall log empty, the hands' layer drawn in
every style; the window not looked at.

**Not verified.** How the styles read at distance with real hands (hand
check 109); openness calibrated on synthetic hands only; the combo never
seen in a real control window; whether a preset in the owner's home
carries a route onto mirror, guide or tethers (if one does it now loads
with a note).

### WP3 — The output list (PR #123, merged with WP4 as 00b6517)

**Built.** `[[output.screens]]` (`config.py`: `SCREEN`, `screens`,
`number`; keys `name`, `monitor`, `fullscreen`, `scene`, `hands`,
`through`, `dim`, each checked, a wrong kind back to its default with a
note, an unknown key a note). **The list wins** over `[output] monitor /
fullscreen` (one note when both are set; output 1's entry is copied into
the scalar keys); a fifth entry, an entry that is not a table, an empty
or non-list `screens` are each dropped with a note; a config `dim` under
0.1 is 0.1 with a note, over 1 is 1. **`[output] bg` / `alpha` of the
wrong kind falls back with a note** (it crashed the launch before).
`app._windows` → `(slots, ctrl_win)`; `_later_output` (an
`overlay.Output`, `allowed=False`, no params, its monitor and fullscreen
from its entry — fork F10); `_open_presenters` (each later context
current, `swap_interval(0)`, `Presenter(moderngl.create_context())`;
output 1's `swap_interval(1)` stays where `main` makes its context —
fork F6); `_draw_render` (the six steps); `Keys` polls every output
window, the mouse stays on output 1, the loop ends when any window
closes; reload targets gain each later `Output`, its backend and each
`Presenter`. **`outputs.Presenter`**: its own programs and vertex arrays
on its window's context. **`windows.json`**: schema unchanged, one rect
per opened output in config order, an output not opened (or minimised)
keeps its old entry or is `null`; **an old one-entry file loads** (output
2 at its default spot). **The watch** (`RenderWatch(outputs=…)`): the
stall is "no output presented"; one output dark for 2 s while another
presents is a warning naming it, once per message; a present that
raises is `output_failed`, a warning with its traceback.
`placement.place(…, what=)` names the output in its notes.

**Fork F9 as built, plainly:** a later output whose `monitor` index no
connected screen has **is not opened**, with a note ("config: output 2
(projector): monitor = 2, but 2 screens are connected (0–1) — not
opened") and a disabled line on the OUTPUT page; output 1 always opens
(an index no screen has is −1, plan 16's rule). **A screen plugged in
after the launch is not picked up** — a later output that did not open
stays closed for the run, and output 1's −1 stays −1 — until a relaunch
(⌘R). Late plugging is not handled (audit P6).

**Differs from the plan, and why.** `(slots, ctrl)` and `outputs.Slot`
instead of a list of windows (the page needs the name, launch switches,
the reason it is missing and the error); `present(handoff, size,
target=None)`; the swap intervals set once at the launch; `glFlush` only
with a later output; the 40 px cascade; a later output whose window or
presenter will not build is closed and counts as not opened (the
review: a never-drawn window showed garbage and fooled the watch;
15d534d); the placement fallback keeps F9 (the review).
`RenderWatch` takes an `outputs` callable instead of a composite `info`.

**Tests.** New `tests/test_config.py::test_no_screens_list_is_one_output_as_today`,
`::test_a_screens_list_wins_over_the_scalar_keys_with_a_note`,
`::test_a_fifth_screen_is_dropped_with_a_note`,
`::test_a_config_dim_cannot_launch_an_output_black`,
`::test_a_ground_or_opacity_that_is_not_a_number_is_the_default_with_a_note`;
`test_app_boundary.py` (fake window systems: a real second window
cannot exist headless) `::test_one_window_per_listed_output`,
`::test_a_later_output_whose_screen_is_absent_is_not_opened`,
`::test_the_exits_save_one_rect_per_output`,
`::test_only_the_first_output_waits_for_the_screen`,
`::test_one_output_draws_the_view_renderer_draw_would`,
`::test_the_rendering_context_is_flushed_before_a_presenter`,
`::test_a_raising_presenter_does_not_stop_the_frame`,
`::test_every_output_is_applied_and_polled_for_keys`,
`::test_a_later_output_is_the_configs_and_never_overlay`;
`test_watchdog.py::test_one_dark_output_of_two_is_a_warning_not_a_stall`,
`::test_no_output_presenting_is_the_stall`;
`test_placement.py::test_what_names_a_later_output_in_the_notes`;
`test_outputs.py::test_the_presenter_shows_what_a_target_view_shows`
(all eight states and three other shapes, byte for byte — **on the same
context** as the renderer, a stand-in) and
`::test_the_presenter_rebuilds_after_a_reload_in_its_own_context`.

**Demo.** [`wp3-two-windows.png`](assets/21-outputs-and-the-hands/wp3-two-windows.png):
output 1 and output 2 **read back from two real windows** on this
laptop (400×260 each, `monitor = -1`, synthetic tape, warp on). **Real
launches:** two outputs, 150 frames: output 2's picture equal to output
1's byte for byte at frames 60, 90, 120 and 140 (the real share group,
`external_texture` and the flush exercised); `windows.json` rewritten
with two entries. No list, 150 frames: today's direct path, one entry.
**Pacing not established**: median 271 fps with two outputs and 377 fps
with one; the swap was not pacing the loop in either.

**Not verified.** Two physical screens, fullscreen on a second monitor,
mixed refresh rates, tearing, unplugging, minimising, ⌘R, real hands;
`Output.apply()` moving a later output to fullscreen (output 1's code,
not run here); hot reload of `outputs.py` with a live presenter (a
standalone context only).

### WP4 — The params and the OUTPUT page (PR #124, stacked on #123, merged as 00b6517)

**Built.** `overlay.register_switches(reg, slots)`, called by `app.main`
right after `_make_output` and before `library.attach`:
`output.N.scene`, `.hands`, `.through` per **opened** output N (its
place in the list), and `output.N.dim` when the config lists two or
more outputs **or a lone entry sets `dim` under 1** (the review,
c173df6). All group `output`, `persist=False`, `modulatable=False`;
labels "Scene" / "Hands" / "Hands through effects" with one output, the
output's name before them with several ("Glass scene"). They write the
slot's `Switches`, which `_draw_render` hands the renderer in that
output's `View` every frame. **Persisted nowhere**: every launch and
every ⌘R starts from `config.toml`; undo, a preset load or save and a
show load or save leave them alone. The OUTPUT page
(`Panel._output_blocks`): under Master dim, a block per listed output —
"N  name" and the three ticks (lined up after the widest name, the name
cut so the ticks fit); the DIM row when the param exists; one line only
when there is something to say (the present error first, then "hands:
ghost hands are off (HANDS page)" or "hands: no tracker", "through: no
effect on"); "shows: …" in words (`ui.output_shows`), in the warning
colour when black; a disabled line for an output that did not open; and
with several outputs "paced by output 1 · frame W×H · below: output 1's
window". **With one output the page has no dim of its own: the master
dim is it.** The footer, on every page: "· output 2 black" / "· outputs
2, 4 black" for a reason other than the master dim. `Panel._check` takes
an optional short label.

Counts: 3 params on a one-output laptop, 8 on the two-output rig, 16 at
four outputs (with `ghost.style`, the plan's 4 / 9 / 17).

**Differs from the plan, and why.** The dim's registration rule (above);
the notes on their own line (they did not fit beside the ticks); two
more "shows:" phrases ("black — the scene is off and no hand shows",
"black — master dim"); several black outputs named together; the
undo / preset test in `test_undo.py`.

**Tests.** New `test_overlay.py::test_the_output_switches_are_rig_settings`,
`::test_one_output_has_no_dim_of_its_own`;
`test_ui_shell.py` (`build_rig` carries four outputs, so
`test_every_page_fits_the_control_window` runs with them)
`::test_the_output_page_fits_with_four_outputs_and_overlays_rows`,
`::test_the_output_page_says_what_each_output_shows`,
`::test_the_output_page_with_one_output_has_no_dim_of_its_own`,
`::test_the_footer_names_a_black_output`;
`test_undo.py::test_the_output_switches_are_left_alone_by_undo_presets_and_shows`;
`test_app_boundary.py::test_the_switches_are_registered_from_the_configs_launch_values`.

**Demo** (read back from real windows on this laptop):
[`wp4-eight-states-real.png`](assets/21-outputs-and-the-hands/wp4-eight-states-real.png)
— output 2 stepped through the eight states by a script, its presenter
window read back each time — and
[`wp4-output-page.png`](assets/21-outputs-and-the-hands/wp4-output-page.png),
the control window read back. **Real launch:** 210 frames, nothing
raised; `Renderer.stats` for each state of output 2 (output 1 at state
1) matched the route table and the two-output table (state 2 and 6:
two chain runs; the rest one); state 1's output 2 equal to output 1 byte
for byte. Nobody clicked the page: every change went through the params
from a script.

**Not verified.** The glass, the projector, real hands, a desk button
learned onto a switch, a real click.

### The eight states as built

`outputs.route` (`hands shown` = the output's hands tick ∧ `ghost.on` ∧
a hand drawn this frame, fork F7); the words are `ui.output_shows`'.
Warp + kaleido on:

| # | Scene | Hands | Through | Pipeline | Hands after | "shows:" |
|---|---|---|---|---|---|---|
| 1 | on | on | off | SCENE | yes | scene + hands over the effects |
| 2 | on | on | on | SCENE+HANDS | no | scene + hands through the effects |
| 3 | on | off | off | SCENE | no | scene |
| 4 | on | off | on | SCENE | no | scene (= 3) |
| 5 | off | on | off | none (the ground) | yes | hands |
| 6 | off | on | on | HANDS | no | hands through the effects |
| 7 | off | off | off | none | no | black — nothing switched on |
| 8 | off | off | on | none | no | black — nothing switched on (= 7) |

With no effect on, or no hand shown, the through tick changes nothing (2
is 1, 6 is 5); with the scene off and no hand shown the output is
"black — the scene is off and no hand shows". The readout layer (the
guide and the tethers' labels) is laid on every output whose hands tick
is on, after the hands, while it is split.

### The frame as built

```text
app._draw_render
 1  output 1's context current; the stranded-target check; ctx.screen bound
 2  a View per output: output 1's on its framebuffer (Renderer.draw's View, so one
    output is today's frame), each later one with its presenter and its size
 3  renderer.draw_outputs(...)
      once:      the face picture; the scene pass; resolve; the cover; lookback.tick, pull;
                 fx.tick; fx.opaque
                 the hands' layer (Ghost.layer), only if some View's hands tick is on —
                 guarded; the readout split only with an effect on, some output
                 through, the guide on
                 route every View (after the layer: "a hand shown" needs it)
      per key:   SCENE, SCENE+HANDS, HANDS in that order, each once, into the View
                 itself (its only consumer, at the frame size) or a frame texture
                 (RGBA8, LINEAR, frame size); a raise → its Views show their ground
      once:      lb.capture(scene.tex) — after every pipeline; fx.state.advance_to(t)
                 when an effect is on and no chain ran
      per View:  the picture (nothing | 1:1 texelFetch | scaled into fit()'s rect, the
                 rest the ground | the ground); the hands after; the readout; the dim
                 (output.dim × its own) — or, for a presenter View, a Handoff
      exit:      views[0].target bound with its rect and BLEND on, a raise included
 4  glFlush, only when a later output exists
 5  each later output, in its own try: current, Presenter.present(handoff, size), swap
    (interval 0); a raise → slot.error, watch.output_failed, the frame goes on
 6  finally: output 1 current, swap (interval 1: it paces the loop)
```

### The presenter hand-off as built

`View.handoff` is an `outputs.Handoff(frame, frame_size, rect, hands,
readout, alpha, factor, bg_alpha)`: `frame` the pipeline's frame texture
or None (the ground); `rect` `fit(frame_size, …)` inside the view's
rect; `hands` `Ghost.tex` when this output's hands go over the effects;
`readout` `Ghost.readout` when split and this output's hands tick is on;
`alpha` `ghost.alpha`; `factor` master × own dim, clamped; `bg_alpha`
the output's ground. `Presenter.present(handoff, size, target=None)`,
in its own context: (1) clear to `(0, 0, 0, bg_alpha)`; (2) the frame
into `rect`, 1:1 by `texelFetch` or scaled, alpha 1 on an opaque ground;
(3) the hands and (4) the readout into `rect` at `alpha` with
`Ghost.composite`'s blend; (5) the dim with `dim_pass`'s blend when
`factor` is under 1. Textures are wrapped by GL name
(`ctx.external_texture`), cached per (name, size); nothing is built
before the first `present`; `on_reload` marks it stale and the next
`present` rebuilds in its own context; it leaves its framebuffer bound,
a raise included.

### What the orchestrator saw (apart from what the agents reported)

- Merged WP5, then WP1 + WP2, WP6, WP3 + WP4 into `plan-21-integration`
  with plans 19 and 20 underneath; the conflicts were in
  `hotreload.MODULES` and two test files, both append against append.
- Ran the suite on that branch: **1549 passed, 1 skipped**; `ruff`
  clean.
- Looked at `ghost-styles.png` (offscreen): the five styles are clearly
  distinct; the PALMS orb and the CAGE shrink as the hand closes; the
  hands fill about a quarter of each cell at that camera distance.
- **Launched the real app** on this laptop against a temp home, with a
  two-entry `[[output.screens]]` (glass; projector with `through =
  true`, `dim = 0.6`), two small windows on the laptop's own display,
  190 frames: both outputs' params read the config's launch values;
  warp + kaleido switched on gave `chain_runs 1`; flipping output 2's
  scene and through from a script changed the stats with no error;
  `ghost.style` stepped to CAGE; an undo took back the style and effect
  edits and left the output switches where they were; `ghost.error`
  empty; the stall log empty. No hand was in view (no tape), so `layer`
  stayed False: **the hands were not drawn in that launch**. The windows
  were not looked at by eye.
- **Pacing is not confirmed.** In the agents' short launches both the
  two-output path and today's one-window path ran unpaced (270–380 fps),
  so fork F6's frame-rate claim (the first output vsynced, the others
  not) is neither confirmed nor refuted: hand check 107.
- **The unpaced launches are not this run's doing.** The orchestrator ran
  the same 240-frame scripted launch (temp home, one window) from main's
  code (fa9b3a1) and from this branch: a median of 2.48 ms a frame (403
  fps) on main and 2.44 ms (409 fps) on this branch. The swap does not
  wait in these scripted launches on either; why was not found, and a
  launch by hand at the rig has not been timed.

### During the run: a test run aborted in CoreMIDI

At 22:36 on 2026-10-04 a full pytest run aborted inside `rtmidi`
creating a CoreMIDI client (a crash dialog on the owner's screen).
`tests/test_hands_boundary.py` was found scanning and opening a real
MIDI output. `tests/conftest.py::_no_real_midi` (autouse, f289afb "Tests
never reach the machine's MIDI") now gives every test empty port lists
and an open that raises, unless a test patches `mido` itself. **The
exact crashing path (the input side) was not found.** The app has the
same exposure: with no desk connected it rescans the ports every
`midi.RECONNECT_S` (2 s) through `mido.get_input_names()`, and if
CoreMIDI refuses a client there rtmidi aborts in native code that the
`except` in `midi.Ports.connect` cannot catch. Not seen to happen in the
app; filed as audit R15.

### WP7 — Docs, decisions, hand checks (this PR)

This section and the *As built* notes above; `DECISION-REGISTER.md` rows
**79–88**; `DECISIONS.md`'s 2026-10-04 rows (the owner's three, the
rest on a recommendation) and the extended rows (the 2026-09-18 two
windows, the ghost hands' last pass, the master dim, window placement,
"any param a modulation target"); `11-hand-checks.md` group **Q, checks
99–112**, check 47 finished by 108; `ARCHITECTURE.md`, `ENGINEERING.md`;
`AUDIT-2026-09.md` rows R15 (the MIDI rescan), P6 (a screen plugged in
after launch) and V8 (`Renderer.on_reload`'s context);
`plans/README.md`, `CHECKPOINT.md`, the roadmap's pointer.

**Left stale in code** (comments and docstrings are not this package's
to edit; listed in the PR): `render.py`'s comment before the pipeline
loop ("captured after the first composite"); `ghost.py`'s module
docstring ("its own pass, after everything else … no effect … ever
touches them") and `ghost.on`'s tip ("after every effect"), both now
the default of the through tick only; `app._open_presenters`'
docstring quoting "121 fps against 60–81" as a fact; `outputs.py`'s
module docstring naming scene, hands and dim as an output's switches
but not through; `Ghost.readout`'s docstring ("only while the guide is
on"; it also needs `readout=True` and a target that builds).

### Not verified, in one place

Nothing in plan 21 has met the glass, the projector, a second screen, a
real hand or the APC40. Unseen by a person: any window of it (every
picture was an offscreen render or a script's read-back), the OUTPUT
page clicked, a style at distance, a switch learned onto the desk.
Unmeasured: pacing and tearing with two screens (F6), mixed refresh
rates, real fullscreen on two monitors, a screen unplugged or plugged in
mid-run, `skeleton()` on real `leap` objects, hot reload of `outputs.py`
under a live presenter. The order to see them in is group Q.

## Appendix — group Q for `11-hand-checks.md`

### Q. Plan 21 — outputs, the hands through effects, the ghost hands finished

The glass, the projector, the camera and the APC40. About 45 minutes.
First, headless: `uv run pytest -q tests/test_outputs.py tests/test_ghost.py
tests/test_app_boundary.py tests/test_overlay.py`. Back up the home
first. Run Q1 before editing `config.toml`.

**Q1. One output is as it was.**
With no `[[output.screens]]` in `config.toml`, launch. *Pass:* two
windows as before; the OUTPUT page shows one block, "1", with scene and
hands ticked, through effects unticked and no dim of its own; the
picture is as on the build before this plan; F5 (TRIP) with the ghost
hands on shows clean hands over a warped shape. *Fail:* `Renderer.draw_outputs`'
direct rule; `overlay.register_switches`.

**Q2. Two outputs open where the config says.**
Add two `[[output.screens]]` entries (glass first, `fullscreen = true`
on both, each its `monitor` index; `control_monitor` the laptop's).
Relaunch. *Pass:* the glass and the projector each go fullscreen with
the same picture, the control window is on the laptop, and the SYSTEM
page has no note. Quit and relaunch: the same. Set the second entry's
`monitor` to an index nothing has: only the glass opens, the OUTPUT page
says "2 … is not connected", the SYSTEM page says why. *Fail:*
`app._windows`, `placement.place`.

**Q3. The eight states, on each output.**
Ghost hands on, a hand in the box, F5. On the OUTPUT page walk output 1
through the table at the top of this plan, then output 2. *Pass:* each
state shows what its row says on that output only; the other output
does not change; the "shows:" line says what you see; with both
switches off the output is black and the footer says "output N black".
*Fail:* `outputs.route`; a change on the other output → the pipelines
are not keyed per output.

**Q4. Hands through effects.**
Glass: through effects on. Projector: off. F5, then F4 (WAKE). *Pass:*
on the glass the hands bend and recolour with the shape; on the
projector they are clean; **on neither do the hands leave echoes**;
with every effect off the two look the same and the page says "no
effect on". Turn the guide and tethers on: the labels are sharp on both.
*Fail:* hand echoes → the hands reached `scene.tex`; warped labels →
the readout layer.

**Q5. The dims.**
Crossfader to the middle: both outputs dim together. Output 2's own dim
to half: only the projector dims further, and its line shows the
product. Crossfader left: both black, the footer says `dim black`.
Relaunch: the master is full, each output's dim is what the config
says. *Pass* as described, and the glass stays opaque black, never
see-through. *Fail:* `Presenter.present`'s factor; `dim_pass`.

**Q6. The frame rate with both fullscreen.**
Both outputs fullscreen, F5, hands in the box, output 1 through effects
and output 2 not (two chain runs). *Pass:* the SYSTEM page's rate stays
at the glass's refresh rate; no tearing on the projector during a fast
rotation; no stall log entry after five minutes. Note both screens'
refresh rates. *Fail:* half rate → a second waiting swap
(`glfw.swap_interval`); tearing on the projector → fork F6, pace by
that output or let it wait too.

**Q7. Unplug the projector mid-run.**
Pull the projector's cable while it runs; wait ten seconds; plug it back.
*Pass:* the glass never stops; the control window's banner names output
2; the loop does not exit; after replugging the projector shows the
frame again or the banner says why not. *Fail:* the loop dies →
`draw_render`'s per-output `try`; the glass freezes → a presenter left
its framebuffer bound.

**Q8. Screens of different shape.**
If the two screens differ in aspect (or set the second entry
`fullscreen = false` and drag its window tall and narrow): *Pass:* the
second output shows the whole frame centred with black bars, circles
round, the hands on the same part of the shape as on the glass. *Fail:*
`outputs.fit`.

**Q9. The ghost hands follow the real ones** (check 47, finished here).
Run check 47 (a) to (f), (h) and (i) as written, on the glass. For (c),
tick **Ghost mirror** and look in the glass: note which setting the rig
wants and put it in the show. (g) is now Q4. If the rig ever runs
`screentop`, repeat (c) there: those axes are unmeasured and the HANDS
page says so. Then record the tape: `uv run python tools/hands_tape.py
record tests/fixtures/hands/rig.json --seconds 6` — both hands, open,
fist, pinches, in and out of the box — and commit it. *Fail:* as check
47's.

**Q10. The styles.**
HANDS page, **Ghost style**: step through HANDS, JOINTS, PALMS, CAGE,
MARIONETTE with both hands in the box. *Pass:* each follows the hands
with no lag; the cage and the orb open and close with your grip; a hand
leaving fades in every style; the guide looks the same in all five; the
frame rate does not change. Say which to keep. *Fail:* `ghost.PARTS`.

**Q11. Black is never a mystery.**
Untick everything on both outputs; drag output 2's dim to 0 with scene
on. *Pass:* each time the OUTPUT page says in words why that output is
black, and the footer names it from any page. *Fail:* `_page_output`'s
"shows:" line.
