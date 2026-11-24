# Plan 87 — black is clear, on any picture node

**Built** 2026-11-22 on `claude/hyperspace-luma-key-transparency-ysmbfq`.
Register rows 1063–1074, hand checks 859–867 (group FH). No schema move.
Rows 1063 (2026-11-22) and 1072 (2026-11-23) are the owner's; the
rest are the build's, "(rec)", to keep or overturn.

## Why

A picture in the graph is opaque wherever it is black. A media source is
opaque because `media.frame.to_rgba` gives a picture with no alpha of its
own an alpha of 255; the scene on an opaque ground, the Test card and the
Mandelbrot are opaque by design; an effect's alpha is at least the peak of
its colour. So a video's black, a camera's dark room, a feed's empty
ground, a generator's black between its lines all cover what is under
them. Laid over the scene, a clip of fire on black is a black rectangle
with fire in it.

Today the fix is a `matte` (from luma) and a `cut` per picture: two
nodes, a mask wire, four params and the matte's symmetric edge to fight (a
key of 0.02 with soft 0.1 lets 35 % of pure black through). That is plan
39's machinery for a *pattern* — a person cut out, a region kept — used to
say something simpler: *this picture's black is not there*.

The first build put the key on the media channels only. The owner
(2026-11-22): "this is supposed to apply to all bitmap outputting nodes,
not just media nodes" — and chose how it is switched (row 1063).

## What "alpha is not a mask" asks of this

DECISIONS, "Masks are their own wire", and register row 440 (the owner,
2026-10-27): "Alpha is: how transparent is this thing? A mask means that I
have a pattern here … Either the pixel passes, or it doesn't. I don't
necessarily want to ride on alpha to make that happen."

The key is the first of those, not the second. It does not make a pattern
that passes or does not; it says how transparent each pixel of a picture
is — the alpha a PNG would have carried, worked out from the picture's
own brightness. It makes no mask wire, reads none, and a mask is still
only ever made by `matte` and `segment`. So it is a **setting on the
picture node**, not a node of its own on GRAPH and not a mask. Row 440
stands.

## Read first

- `docs/DECISIONS.md`: "Media", "Masks are their own wire (plan 39)".
- `docs/GLOSSARY.md`: no word changes; the panel says **black is clear**.
- `REVIEW.md`: a saved key is a file format (`"keys"`, `key.<node>.*`,
  row 1064); what a build from before makes of a file this one writes (row
  1068); conversions at their edges (row 1065's 0 and 1).

## What is built

### 1. Which nodes are keyed: the graph's `"keys"` (owner, row 1063)

A loadable patch's graph section gains one optional key, `"keys"`: the
names of the picture nodes whose black is clear, sorted, written last and
only when there are any — a section with none is the bytes it was.

```json
"graph": {"frame": "wired", "nodes": [...], "wires": [...],
          "keys": ["channel.a", "scene", "testcard"]}
```

Any node that makes a picture can be keyed (`graphview.keyable`): a
channel, the scene, an effect or a copy, a composite, a switch, a delay, a
resize, the dream, the look-back, a cut, the pattern, the backdrop, a hands
layer or guide. Not a window, All outputs, a geometry or a matte. It is
switched like a composite's blend: the node's menu on GRAPH, **black is
clear**, checked while on (`graphview.render_key`, one undo step); the
MEDIA page's switch on a channel is the same edit on `channel.<c>`.

It is the graph's, not a param: on and off is a graph edit, so it cannot
be Learned or LFO'd (the knobs can). That was the owner's choice over a
toggle param on every node, which would have put ~7 values per picture
node in every save and a wrapper in every graph (row 1063).

### 2. The knobs: `key.<node>.*`, while a node is keyed

Declared on landing for each keyed node (`params.declare_keys`, as a
matte's are), dropped with the key; group `key`, a patch group, persisted,
modulatable, on the selection with the node's own params
(`graphview.param_ids`) and on MEDIA for a channel:

| Id | Kind | Default | What |
|---|---|---|---|
| `key.<node>.level` | 0–1 | 0.02 | At or below this brightness a pixel is clear. |
| `key.<node>.soft` | 0–1 | 0.10 | The ramp above the level: a smoothstep to solid at `level + soft`. 0 is a hard edge. |
| `key.<node>.measure` | `peak`, `luma` | `peak` | Brightness as the largest of r, g, b (a saturated colour stays), or Rec. 709 luma (a deep blue goes). |
| `key.<node>.feather` | 0–32 px | 0 | A blur of the ramp (masks.py's `BLUR_FS`) before it becomes alpha. |
| `key.<node>.keep` | toggle | **on** | Keep colour: premultiplied colour untouched, only the alpha from the ramp — a dim glow stays a glow over what is under it. Off: colour goes with alpha, so a fringe dims. |
| `key.<node>.invert` | toggle | off | White is clear instead. Keep colour does not apply inverted. |

Ids are `key.<node name>.<knob>` (`key.channel.a.level`, `key.acid.2.soft`,
`key.hands.2.layer.feather`), not under the node's own prefix: an effect's
`fx.<name>.*` are its file's uniforms, which a `key` param could collide
with. The first build's `media.<c>.key*` never merged; they are gone.

**The ramp** (`glsl.KEY_RAMP`, shared by both passes) is one-sided,
`k = smoothstep(level, level + soft, m)` on the straight colour, so pure
black is always fully clear (row 1065).

### 3. Where it runs

- **Any picture but a channel:** the build reads every consumer of a keyed
  node through a `graph.KeyNode` after it (`_Build._keyed`): one pass,
  `MaskPasses.key` (`masks.KEY_FS`), into a frame texture of its own, once
  a frame. The picture comes in premultiplied; its colour is
  unpremultiplied for the measure; out, keep colour is `(rgb, a·k)`, else
  `(rgb, a)·k`. Its opacity, depth and whether it reads anything are its
  input's. A graph that keys nothing builds no `KeyNode`: the graph and its
  signature are what they were.
- **A channel:** keyed inside its own fit pass (`media_tex.FIT_FS`,
  `MediaNode.keyed`), no pass more — the source's straight colour, the
  source's own alpha (a PNG's) and the backdrop's fader on top, into a
  target of its own (`media.<c>@key`). A channel nothing keys runs the pass
  it always did, byte for byte.
- **The feather**, either way: the ramp alone into a one-channel target,
  `MaskPasses.feather`, then the pass keys by it — two passes more, only
  while the feather is above 0. A channel's ramp is sampled clamped into
  the picture, so its letterbox does not eat its edge (row 1067).

Not keyed, on purpose (row 1069): the faces' raw channel texture (sampled
outside the fit pass), the segment's CPU frame (a person is found in the
picture as shot), the MEDIA page's previews.

### 4. `screen` on the composite (`graph.BLENDS`)

`BLENDS` gains `screen`, appended (`over`, `add`, `depth`, `screen`): a
composite's **laid screen**, and a hands node's `laid`. Premultiplied
screen is `src + dst·(1 − src)` per channel — one blend function, rgb
`(ONE, ONE_MINUS_SRC_COLOR)`, alpha as over — so black adds nothing and
nothing passes white (add's fault on bright footage). The presenter's
hands hand-off (`outputs`) lays it the same way. Words: "screened" (row 1070).

### 5. Generators

Every effect is a picture node, so the Test card and the Mandelbrot —
opaque by design — can be keyed like anything else. Plasma, Fractals and
Glimmer already write alpha = the peak of their colour and need nothing
(row 1071). The one-step matte + cut starter the first build left open is
not needed: the key reaches every picture (row 1073).

## Review of #479 (Devin, 2026-11-23)

Six findings, each real, each fixed with a test that fails without it
(`tests/test_black_is_clear.py`):

- **A channel straight into the backdrop** is made apart from the channel's
  node (the backdrop's fader in its fit pass) and was never keyed: it is
  keyed when the channel is, keeping its alpha over the ground.
- **A keyed Blend or Displace lost its aux**: the aux wire is joined to the
  effect under its `KeyNode`.
- **A keyed node in a hands through-chain broke the window's hands mute**:
  the mute's walk reads through a `KeyNode` as through an effect.
- **A keyed picture painted into an effect's input was made opaque** on an
  opaque window (`Node.paint`): a keyed node laid over another picture
  keeps its alpha (`Node.keeps_alpha`, set by the build on keyed nodes
  only — every other node paints as it did); the window's end makes it
  opaque.
- **The knobs were not on the selection**: `graphview.OWNERS` puts
  `key.<node>.*` on the keyed node (a stray `group:key` box was drawn
  instead), and an effect's selection shows them under its strip.
- **Save as patch dropped the key**: a fragment carries `"keys"` (its keyed
  members, renamed, written only when there are any) and the members'
  `key.<node>.*` values; a spawn lands them keyed in the host. A build from
  before refuses a patch file with `"keys"` in words, as any key it does
  not know; both Macs run one build.

## What the pictures showed

Driven offscreen (the real renderer) and in the real app
(`tools/app_driver.py`, controls found by id):

- At the ask's numbers (0.02, soft 0.1) a pixel is fully solid from 0.12
  up, so thin grey smoke (about 0.2) stays opaque and draws a dark band
  over the shape. A level about 0.3 lets it through. Hand check 860.
- With keep colour on, a pixel below the level keeps its colour at alpha
  0: over black it looks unchanged, over the shape it is added. Deep blue
  under luma does not "go" unless keep colour is off. As asked
  ("premultiplied rgb untouched"); hand check 861.

## What does not change

- **No saved look.** A section without `"keys"` keys nothing, declares no
  knob and saves without the key — the file a build before wrote; every
  corpus loadable resaves byte for byte, unchanged. A channel nothing keys
  is the fit pass's old bytes (tested against the old shader), and a graph
  that keys nothing has no `KeyNode`.
- **No schema** (row 1068). A build from before reading a section with
  `"keys"` refuses the section (`read_graph`: "no key 'keys'") and loads
  that patch black with the reason in its notes, as for a `screen`
  composite or any node kind it does not know. Only patches that use them
  are affected; both Macs run one build.
- **No glossary word**, no new wire kind or port; `KeyNode` is built, never
  placed.

## Hot reload

New fields on live objects (`ViewState.keys`, `Wiring.keys`,
`GraphSpec.keys`, `MediaNode.keyed`): **restart** after pulling (row 1074).

## Register rows

| # | Decision | Check | Keep / overturn |
|---|---|---|---|
| 1063 | Black is clear on **any picture node**, switched from the node's menu (and MEDIA for a channel) into the graph section's `"keys"`, its knobs then on the selection; channels on the same model. Not a toggle param on every node. A picture's own transparency, not a mask: row 440 kept | 859, 867 | **owner — 2026-11-22**: "this is supposed to apply to all bitmap outputting nodes, not just media nodes"; "Node menu, then knobs"; channels "Same model as every node" |
| 1064 | The knobs `key.<node>.level` 0.02, `soft` 0.1, `measure` (peak, luma), `feather` 0–32 px, `keep` on, `invert` off: declared while the node is keyed (group `key`), not under the node's own prefix; the panel's words "black is clear" | 859, 860 | (rec) |
| 1065 | One-sided ramp `smoothstep(level, level + soft, m)` on the straight colour (`glsl.KEY_RAMP`, one for both passes): pure black always clear; the matte's symmetric edge left as it is | 860 | (rec) |
| 1066 | Keep colour on: premultiplied colour untouched, alpha from the ramp; off: colour goes with alpha. Inverted, keep colour does not apply | 861 | (rec) |
| 1067 | A keyed node is read through a `KeyNode` (one pass); a channel is keyed in its fit pass (no pass more); the feather is the ramp alone blurred by `MaskPasses.feather`, two passes more only above 0 | 862 | (rec) |
| 1068 | Nothing keyed is the graph, the bytes and the save it was; `"keys"` is written only when there are any; no schema bump — a build from before refuses a section with `"keys"` or a `screen` composite in words (that patch black) | 866 | (rec) |
| 1069 | Not keyed: the faces' raw channel, the segment's CPU frame, the MEDIA previews | 863 | (rec) |
| 1070 | `screen` appended to `graph.BLENDS`: premultiplied `src + dst·(1 − src)`, one blend function; the composite's and a hands node's laid; "screened" | 864 | (rec) |
| 1071 | Generators: the Test card and the Mandelbrot are keyed like any node; Plasma, Fractals and Glimmer need nothing (alpha = peak) | 865 | (rec) |
| 1072 | A node is never keyed when it is added (a channel included): keying is always asked for, from the node's menu or MEDIA | 859 | **owner — 2026-11-23: "it doesnt have to spawn nodes with keying on" — a node is never keyed when added** |
| 1073 | The one-step matte + cut "black is clear" starter is not built: the key reaches every picture | — | (rec) |
| 1074 | A restart after pulling: `ViewState.keys`, `Wiring.keys`, `GraphSpec.keys` and `MediaNode.keyed` do not reach live objects by hot reload | — | (rec) |

## Hand checks (group FH)

Setup: a clip with a black ground (fire, smoke, particles on black) in
channel A; on GRAPH, `channel.a → composite.over`, `scene → composite.under`,
the composite into All outputs, a shape in the scene.

- **859. Black is clear on a channel.** MEDIA, channel A: **black is
  clear** on. *Pass:* the black goes; the fire is over the shape; the
  picture is unchanged where it is bright; GRAPH's menu on Channel A shows
  it checked. Off again: the black rectangle is back. *Fail:* any change
  with it off, or a dark halo round the fire with it on.
- **860. Level and softness by hand.** Level 0 → 0.2, then soft 0 → 0.5.
  *Pass:* level eats into the darks smoothly; soft 0 is a hard edge, higher
  a gentler one; pure black stays clear throughout.
- **861. Keep colour.** Keep colour off, then on, on smoke. *Pass:* on, the
  thin smoke stays as bright over the shape as it was over black; off, it
  dims at its edges. Say which the show wants by default.
- **862. Feather.** Feather 0 → 16 px on a hard-edged still. *Pass:* the
  edge softens, nothing shifts, and SYSTEM's line for the node rises a
  little only while the feather is above 0.
- **863. The backdrop.** The `channel to backdrop` starter, the backdrop
  keyed from its menu. *Pass:* the backdrop's black shows the desktop or
  ground; the backdrop fader still fades it.
- **864. Laid screen.** The composite's menu → **laid screen**, nothing
  keyed. *Pass:* the clip's black adds nothing, its brights lighten the
  shape and never clip to a flat white where add would.
- **865. A generator.** Add the Test card (and then the Mandelbrot) from
  the picker, `scene → testcard.image`, the card into the composite's
  `over`; its menu → **black is clear**. *Pass:* the shape shows between
  the card's lines (the Mandelbrot: through its black inside); the knobs
  are on its selection. *Fail:* the card still covers the shape.
- **866. An old patch.** Load a loadable patch saved before this branch.
  *Pass:* it looks exactly as it did, nothing keyed; save it: the file is
  unchanged.
- **867. The scene and an effect keyed.** Key the scene from its menu,
  over a channel in a composite (channel under, scene over), then an effect
  after the scene instead. *Pass:* the channel shows wherever the scene
  (then the effect) is dark; ⌘Z takes each key off in one step.

## Tests

`tests/test_black_is_clear.py`: the section's `keys` (read, write only
when any, through the wiring); the knobs' ids, defaults and lifecycle;
which nodes can be keyed; the build — one `KeyNode` read by every
consumer, a channel keyed in its own pass, none when nothing is keyed; the
node menu's edit in one undo step, a save and a load of a keyed patch, a
patch from before saving as it did; MEDIA driven by mouse at three
widths; the channel's pass and any picture's pass against a numpy oracle;
the unkeyed channel byte for byte the pass from before; the feather; a
keyed Test card letting the scene through in a whole draw; `screen`
against its formula. The goldens (`-m golden`, the M3 Max only) are
untouched by a graph that keys nothing.
