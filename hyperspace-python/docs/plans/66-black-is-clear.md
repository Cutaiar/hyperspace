# Plan 66 — black is clear: a luma key on the media channels

**Built** 2026-11-22 on `claude/hyperspace-luma-key-transparency-ysmbfq`.
Register rows 902–913, hand checks 699–706 (group EB). No schema move.
Rows 911 and 912 are open for the owner; the rest are the build's,
"(rec)", to keep or overturn.

## Why

A media source is opaque: `media.frame.to_rgba` gives a picture with no
alpha of its own an alpha of 255, and the fit pass (`media_tex.FIT_FS`)
premultiplies by it. So a video's black, a camera's dark room, a Syphon or
NDI feed's empty ground and a still's black border all cover whatever is
under them. Laid over the scene, a clip of fire on black is a black
rectangle with fire in it.

Today the fix is a `matte` (from luma) and a `cut` per picture: two
nodes, a mask wire, four params to set and the matte's symmetric edge to
fight (a key of 0.02 with soft 0.1 lets 35 % of pure black through). That
is plan 39's machinery for a *pattern* — a person cut out, a region kept —
used to say something simpler: *this picture's black is not there*.

## What "alpha is not a mask" asks of this

DECISIONS, "Masks are their own wire", and register row 440 (the owner,
2026-10-27): "Alpha is: how transparent is this thing? A mask means that I
have a pattern here, and it's a very binary thing. Either the pixel
passes, or it doesn't. I don't necessarily want to ride on alpha to make
that happen."

The key is the first of those two things, not the second. It does not
make a pattern that passes or does not; it says how transparent each pixel
of the picture is — the alpha a PNG would have carried if the source had
one, worked out from the source's own brightness. It makes no mask wire,
no mask rides in it, and a mask is still only ever made by `matte` (and
`segment`). So it is a **setting on the picture's source**, not a node
and not a mask: where the source becomes a picture (the fit pass), with
the source's other settings (`fit`, the transport). Row 902.

What would break row 440 — and is not built — is reading a picture's
alpha as a mask anywhere (`matte` from alpha already exists and is the
explicit converter), or a `mask` port on `composite` (row 445: not until
the machine asks).

## Read first

- `docs/DECISIONS.md`, "Media" and "Masks are their own wire (plan 39)".
- `docs/GLOSSARY.md`: no word changes. "Key" is not a glossary word; the
  panel says **black is clear** (row 903).
- `REVIEW.md`: a saved id is a file format (the seven new ids, row 903);
  what a build from before makes of a file this one writes (row 907);
  conversions at their edges (row 904's 0 and 1).

## What is built

### 1. The key, per channel (`media.<c>.key*`)

Seven params per channel `a`–`h`, group `media`, persisted, modulatable,
on the `Channel` (`media/channels.py`) beside `fit`:

| Id | Kind | Default | What |
|---|---|---|---|
| `media.<c>.key` | toggle | **off** | Black is clear: the switch. |
| `media.<c>.key_measure` | enum `peak`, `luma` | `peak` | What brightness is: the largest of r, g, b (a saturated red or blue counts as bright), or Rec. 709 luma (a pure blue is dark, and goes). |
| `media.<c>.key_level` | 0–1 | 0.02 | The threshold: at or below it a pixel is clear. |
| `media.<c>.key_soft` | 0–1 | 0.10 | The ramp above the threshold: a smoothstep from clear at `level` to solid at `level + soft`. 0 is a hard edge. |
| `media.<c>.key_keep` | toggle | **on** | Keep colour: the premultiplied colour is left as it was and only the alpha comes from the ramp, so a dim glow stays a glow over what is under it. Off: colour goes with alpha (what matte → cut gives), so a fringe dims. |
| `media.<c>.key_feather` | 0–32 px | 0 | A blur of the ramp's result (masks.py's `BLUR_FS`, the matte's feather) before it becomes alpha. |
| `media.<c>.key_invert` | toggle | off | White is clear instead. Keep colour does not apply inverted (a bright pixel kept at alpha 0 would be added, not cleared). |

Defaults are the ask's numbers (row 903).

**The ramp** is one-sided, `k = smoothstep(level, level + soft, m)`, on
the source's straight (unpremultiplied) colour, so pure black is always
fully clear whatever the softness. The matte's edge is symmetric
(`smoothstep(key − soft, key + soft, v)`), right for a mask's threshold in
the middle of a range and wrong at the bottom of one (row 904).

**Out**, premultiplied, with `a` the source's own alpha (a PNG's) and `u`
the node's opacity (the backdrop's fader): colour `rgb·a·u` with keep
colour, else `rgb·a·k·u`; alpha `a·k·u`. Off, the pass is the bytes it was
(row 907).

### 2. Where it runs: the fit pass

`Renderer._media_fit` is the one place a channel's texture becomes a
picture at a frame's size, for every `media.<c>` node (a wire's, the
backdrop's). The key is a branch of that pass (`media_tex.FIT_FS`,
`u_key`): no extra pass, no extra texture, while the feather is 0. With a
feather, two passes more: the ramp alone into a one-channel target at the
frame's size (sampled clamped to the picture, so the letterbox does not
eat the picture's edge), `MaskPasses.feather` over it, and the fit pass
reading the blurred ramp 1:1 (row 906).

Not keyed, on purpose (row 908): the faces' raw channel texture
(`view.media`, `render._face_media`: the faces sample the source at its own
size, outside the fit pass), the segment's CPU frame (`Renderer.media_now`:
a person is found in the picture as shot), the MEDIA page's previews (what
the source is).

### 3. `screen` on the composite (`graph.BLENDS`)

`BLENDS` gains `screen`, appended (`over`, `add`, `depth`, `screen`): a
composite's **laid screen**, and a hands node's `laid`. Premultiplied
screen is `src + dst·(1 − src)` per channel — one GL blend function, rgb
`(ONE, ONE_MINUS_SRC_COLOR)`, alpha as over — so black adds nothing, white
stays white, and nothing passes 1 (add's fault on bright footage). It is
the effects' own screen (`fx.FS_TAIL`'s `u_blend == 2`) at the composite.
The presenter's hands hand-off (`outputs`) lays it the same way. Words:
"screened" where `over` says nothing, `add` "added" (row 909).

A composite saved `"blend": "screen"` is new in a file. A build from
before cannot read that graph section: `read_graph` raises `GraphError` on
the blend it does not know (`CompositeAt.__post_init__`), as on any node
kind it does not know, so that patch loads black with the reason in its
notes. Only a patch that uses screen is affected, and both Macs run one
build — row 907.

### 4. Generators (surveyed, nothing built)

The ask's second stage was the generator effects "if they write opaque
black". They do not, except two that mean to:

| Effect | Alpha it writes | Verdict |
|---|---|---|
| Plasma, Fractals, Glimmer | `peak(c)`, and `@blend screen` / `add` | Black is clear already. |
| every effect | `FS_TAIL` raises alpha to at least the peak of rgb | A pass never darkens coverage. |
| Test card | 1 | A card shows its black: opaque by design. |
| Mandelbrot | 1 (the inside black) | Paints the whole frame by design ("at mix 1 that picture is not seen"). |

So no generator gets a key in this plan; a Mandelbrot over the scene is
the starter's (row 912) or a matte → cut today. Row 910.

### 5. A one-step matte + cut starter (considered, not built)

A cable starter **black is clear** on any picture (`graphview.STARTERS`,
`CABLE_STARTERS`): the cable's picture into a new `matte` (luma, key 0.02,
soft 0.1) and a new `cut`, the cut onto the cable. It would serve every
picture the channel key does not reach (the scene, an effect, a
Mandelbrot), in the vocabulary plan 39 built. Not built: it needs a
starter that sets a new node's params on landing (none does yet), and
the matte's symmetric edge would need a one-sided mode to match §1.
Open, row 912.

## What the pictures showed

Driven offscreen (the real renderer, a composite of a fire-on-black still
over the scene) and in the real app (`tools/app_driver.py`: MEDIA, channel
A, **black is clear** clicked by its id, level and feather typed in):

- At the ask's numbers (0.02, soft 0.1) a pixel is fully solid from 0.12
  up, so thin grey smoke (about 0.2) stays opaque and draws a dark band
  over the shape. Raising the level to about 0.3 lets it through. Whether
  the defaults should be higher is for hand check 700.
- With keep colour on, a pixel below the level keeps its colour at alpha
  0: over black it looks unchanged, over the shape it is added. Deep blue
  under luma therefore does not "go" unless keep colour is off. This is
  the behaviour asked for ("premultiplied rgb untouched"), and hand check
  701 is where to judge it.

## What does not change

- **No saved look.** Every key param defaults off; a load lands a value
  the file does not name at the value its object was built with
  (`loadable`, step 2: `Library._fresh_of`), so every loadable patch,
  every show and every golden is the same picture. The off pass is the
  same shader arithmetic as before (`c.rgb·c.a, c.a)·u_alpha`), so goldens
  stay byte-identical; `tests/test_golden_frames.py` passes unchanged.
- **No schema.** The ids are new values in `values`, written by every save
  from now on (row 394: every value the registry holds). A build from
  before notes them as ids nobody has and shows the picture opaque, as it
  always did — row 582's precedent (the sound's ids, plan 45). A patch with
  a `screen` composite is black on a build from before (§3). Both Macs run
  one build. Row 907.
- **No glossary word.** No new node kind, port, wire kind or menu.

## Hot reload

`Channel` gains seven fields. A live channel from before lacks them, so
the renderer reads them by `getattr` with the defaults, and the params
would raise on a live channel built before: **restart** after pulling.

## Register rows

| # | Decision | Check | Keep / overturn |
|---|---|---|---|
| 902 | The key is a setting on the channel (the source), applied where the source becomes a picture; not a node, not a mask, no mask wire: alpha as "how transparent", row 440 kept | 699 | (rec) |
| 903 | Seven persisted params per channel, `media.<c>.key`, `key_measure` (peak, luma), `key_level` 0.02, `key_soft` 0.1, `key_keep` on, `key_feather` 0, `key_invert` off; the panel's words "black is clear" | 699, 700 | (rec) |
| 904 | One-sided ramp `smoothstep(level, level + soft, m)` on the straight colour: pure black always clear; the matte's symmetric edge is left as it is | 700 | (rec) |
| 905 | Keep colour on: premultiplied colour untouched, alpha from the ramp; off: colour goes with alpha. Inverted, keep colour does not apply | 701 | (rec) |
| 906 | Feather: the ramp alone into a one-channel target, `MaskPasses.feather`, read 1:1 by the fit pass; two passes more only while the feather is above 0 | 702 | (rec) |
| 907 | Off for every existing patch, show and golden (a missing value lands the build's off); no schema bump (row 582's precedent); a build from before notes the ids and shows the picture opaque, and reads a patch with a `screen` composite as black, with the reason in its notes | 706 | (rec) |
| 908 | Keyed: every `media.<c>` picture (wires, the backdrop). Not keyed: the faces' raw channel, the segment's CPU frame, the MEDIA previews | 703 | (rec) |
| 909 | `screen` appended to `graph.BLENDS`: premultiplied `src + dst·(1 − src)`, one blend function; the composite's and a hands node's laid; "screened" | 704 | (rec) |
| 910 | Generators surveyed: Plasma, Fractals and Glimmer already write alpha = peak; Test card and Mandelbrot are opaque by design; no effect gets a key | 705 | (rec) |
| 911 | Whether the key defaults **on** for a channel in a new loadable patch (a fresh patch, or a channel first given a source), while every existing patch stays off | 699 | **pending the owner** |
| 912 | Whether to build the one-step **black is clear** cable starter (matte + cut, §5) for the pictures the channel key does not reach | — | **pending the owner** |
| 913 | A restart after pulling: `Channel`'s seven new fields do not reach live channels by hot reload | — | (rec) |

## Hand checks (group EB)

Setup: a clip with a black ground (fire, smoke, particles on black) in
channel A; on GRAPH, `channel.a → composite.over`, `scene → composite.under`,
the composite into All outputs, a shape in the scene.

- **699. Black is clear.** MEDIA, channel A: **key** on. *Pass:* the black
  goes; the fire is over the shape; the picture is unchanged where it is
  bright. Off again: the black rectangle is back. *Fail:* any change with
  the key off, or a dark halo round the fire with it on.
- **700. Level and softness by hand.** Level 0 → 0.2, then soft 0 → 0.5.
  *Pass:* level eats into the darks smoothly; soft 0 is a hard (aliased)
  edge, higher a gentler one; pure black stays clear throughout.
- **701. Keep colour.** Keep colour off, then on, on smoke. *Pass:* on, the
  thin smoke stays as bright over the shape as it was over black; off, it
  dims at its edges. Say which the show wants by default.
- **702. Feather.** Feather 0 → 16 px on a hard-edged still. *Pass:* the
  edge softens, nothing shifts, and SYSTEM's line for `channel.a` rises a
  little only while the feather is above 0.
- **703. The backdrop.** The `channel to backdrop` starter with the key on.
  *Pass:* the backdrop's black shows the desktop or ground; the backdrop
  fader still fades it.
- **704. Laid screen.** The composite's menu → **laid screen**, the key
  off. *Pass:* the clip's black adds nothing, its brights lighten the shape
  and never clip to a flat white where add would.
- **705. A live feed.** A Syphon or NDI source and a camera in a dark room,
  key on. *Pass:* as 699, at the feed's rate, with no frame time change
  worth naming on SYSTEM.
- **706. An old patch.** Load a loadable patch saved before this branch
  that uses media. *Pass:* it looks exactly as it did, every key off;
  save it and load it on this build: the same.

## Tests

`tests/test_media_key.py`: the shader's arithmetic against a numpy
oracle (peak and luma, the ramp's edges at 0 and 1, keep colour, invert,
a PNG's own alpha, the backdrop's opacity) through the real fit pass on a
headless context; the off pass byte-identical to the pass before this
plan; the feather blurs only the alpha and only when asked; the params'
ids, defaults and persistence; an old patch lands every key off; `screen`
in `BLENDS`, through `Renderer.lay` against the formula, and its words.
The goldens (`-m golden`) unchanged.
