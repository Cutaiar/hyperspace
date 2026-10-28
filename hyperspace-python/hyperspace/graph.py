"""The render graph (plan 26 A1, A3, A4): the frame as nodes, evaluated in
dependency order.

`Renderer._draw_frame` (render.py) used to be a fixed list of passes.
It is now "build or reuse the graph for this frame's views, evaluate
it": `build_graph` builds the frame as nodes from the renderer's
`Wiring` — plan 35 (rows 372, 377): a wired frame, every node of it an
ordinary node a wire reaches (plan 36 T3: nothing else — `EMPTY` is the
empty frame, and an old preset's words are wired only by the one-way
migration, `graphmigrate`) — and `Graph.evaluate`
runs the nodes once each, in an order computed when the graph is built,
never per frame. Plan 35 T4 retired the switch-built pipelines
(`SCENE`, `SCENE_HANDS`, `HANDS`, their ends `Fx` and `Wired`, the
through switch): every golden frame is drawn byte for byte by the wires,
proven node for node by `signature` against the reference the retired
graph recorded (`tests/fixtures/frame-signatures.json`).

Seven node kinds. The owner's four (wishlist, "Render graph design
decisions"):

- **Geometry** (`Shape`, `Hands`): draw calls in the shared camera (the
  eye, `eye.*`), no framebuffer of its own. The shape is the see-through
  4D shape; the hands (`ghost.py`'s parts and styles, plan 26 A3) are
  solid geometry, settled once a frame (`Hands.run`) and drawn by
  whatever holds them — the scene, the hands' layer, or both; one node
  per instance (`ghost`, `ghost.2`, A4), solid or as lines. The point
  cloud (`PointCloud`, kind `cloud`, plan 26 A4b) draws a cloud device's
  points, solid, in the scene of any graph built while one is listed.
- **Scene** (`Scene`): any number of geometries into one colour + depth
  target (`render.SceneTarget`): the solid geometry first (the hands,
  depth written), then the sorted see-through shape, depth-tested against
  them and writing its own visible surface after (`render.DEPTH_ALPHA`).
- **Layer** (`HandsLayer`, `Readout`, `Cover`): one geometry into its own
  target. The hands' layer is the hands alone in the shared camera with
  their own colour and depth (`Ghost.layer`); the readout is the guide and
  the tethers' labels, a texture laid on at the outputs, never through an
  effect (register row 80); the cover is the faces' coverage mask the
  look-back's occlusion reads.
- **Composite** (`Composite`): `over` laid on `under` — over, add, or
  depth-aware (hidden where the scene's visible surface is nearer,
  `render.LAYER_DEPTH_BIAS`): the hands onto the look-back's picture before
  the effects (today's "through"), or the hands onto the scene for the
  history.

And the three that wrap what exists (A1's call, registered):

- **FX** (`Effect`, `Copy`, `Shown`; plan 30 D0, plan 35): each effect
  instance is an image node (`Effect`: one pass of its file's program,
  `FxChain.run_one`), the run a chain of them in wire order ending in an
  output's end (`Shown`, one per picture an output shows); a copy draws an
  instance again on another picture (a through output's). An effect that
  is off reads its input through: no pass, no texture.
- **History** (`History`, `Capture`): a look-back (`lookback.Lookback`,
  one ring per instance: `lookback`, `lookback.2` …) as two nodes, because
  its trail must read the ring before the frame's capture changes it:
  `lookback` makes the trail — picture in, trail out, laid over nothing
  (plan 36 T4, D3: a composite lays it, an "add" one in a single pass) —
  and `lookback(capture)` puts what its `image` is wired to — the scene,
  or the scene with the hands' layer (A3) — into the ring after every
  reader of the frame has run. Its frames are its pins
  (`lookback.echo.<k>`, `EchoNode`).
- **Dream** (`DreamNode`; plan 36 T4, W4): picture in → dreamed picture
  out — its input to the worker, `D` laid over it (`lookback.Dreamer`);
  `dream.on` off passes its input through. One live dream (D2).
- **Output** (`Output`): one render output — `fit`, flip, the hands over,
  the readout, the dim — exactly `Renderer._compose`, so an output in
  another context gets the same five-step `outputs.Handoff`.

And plan 32 R's: **Media** (`MediaNode`, `channel.a` … `channel.h` in the
new ids, `media.a` … before them), a media channel fitted to the frame —
the backdrop the scene is laid over (`backdrop`, once `grounded`), or any
picture port a wire names.

And plan 33 R's: **Pattern** (`PatternNode`, `pattern`), the face pattern
as a picture with its media layer's input (`pattern.media`), and the
**Backdrop** sink (`BackdropNode`, `backdrop.image`) — with the shape's
`faces` port (`shape.faces`), the three ends a channel's own shaders reach
the faces and the scene's ground by. A branch is made at the size its
consumer asks (`Node.size_for`, `Frame.at`): the faces' `FACE_PIC`², the
pattern's layer at its channel's own, the frame's for everything else.
Plan 33 S's **Switch** (`SwitchNode`, `switch`, `switch.2` …): eight
pictures in, the one its `select` picks out (`Frame.selects`) — a cut; only
the picked input's branch is made (`Graph.pulled`).

**Materialised and painted images.** A Scene or Layer node *makes* a
texture that lives until the next frame (`image(frame)`); the History,
Composite and FX nodes *paint* into whatever framebuffer their consumer
hands them (`paint(frame, dst)`), as today's passes do — the look-back
composites straight into the chain's half-float input, the chain writes
straight into the output's window. An intermediate texture there would
quantise the picture, so the painted nodes are pulled by their consumer
and the picture's end (`Shown`) decides where the picture lands:
**a picture with one consumer at the frame size, unflipped, paints
straight into that output; otherwise once into a frame texture that each
of its outputs shows** (`Renderer._frame_target`, `_show`). A consumer
that needs a texture of a painted node (the capture of a composite) gets
it materialised once a frame (`Composite.image`).

**What is static and what is per frame.** The node set, the wiring and
the order are a function of the views' count and the renderer's `Wiring`
(`graph_key`, `Graph.wiring`): the renderer keeps the last graph and
builds a new one only when either changes. A window's mutes (picture,
hands) are read by its output each frame, never a rebuild (row 374).
Each output is wired to its end, and shows exactly that (plan 36 T1: the
through stand-down is gone). An end with no output this frame is skipped
and its nodes read 0 ms.

**The graph in the preset** (plan 26 A4). A preset may carry a `graph`
section: plain JSON listing node instances by kind and their wiring,
never a param (`GraphSpec`, `read_graph`; the kinds in `NODE_KINDS`).
What it says becomes the `Wiring` the graph is built from —
where each hands node is drawn (in the scene or as the layer), solid or
as lines, how the layer is laid on, what the history holds — and the
effect instances the chain holds (`FxState.set_instances`). A second
instance of a node is named by the naming rule (ENGINEERING §2):
`ghost.2` (its own `Ghost`, `Renderer.ghost_of`, its own `ghost.2.*`
params), `hands.2` its layer, `fx.acid.2.*` a second acid. No section
is the factory frame; one this build cannot read is a note and the
factory frame (preset.py, `GraphSection`). The words the OUTPUT and
LOOKBACK pages say it in are here too (`hands_words`, `lookback_words`,
`graph_words`, plan 35 T4: read off the wires).

Render stack (ARCHITECTURE §3): this module reads params through the
objects it is handed and never writes one; it imports moderngl and its
sibling render modules only, never params, routing, library, preset,
undo or control. Node methods are `run`, `paint`, `draw`, `image`,
`depth` — never `apply`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar

import moderngl
import numpy as np

from .geometry import EYE_DISTANCE, EYE_FOV, EYE_NEAR, eye_matrix
from .lookback import MAX_ECHOES
from .outputs import View
from .view import (
    MATTE_FEATHER,
    MATTE_FROM,
    RESIZE_ASPECTS,
    RESIZE_FILTERS,
    RESIZE_FITS,
    RESIZE_SIDES,
    SEGMENT_FEATHER,
    SEGMENT_LEARN,
    SEGMENT_MODES,
    SEGMENT_QUALITY,
    CutState,
    MatteState,
    ResizeState,
    SegmentState,
)

# port types: a colour picture at the frame's size, a one-channel mask at
# its maker's size, or draw calls (a geometry, drawn by its scene or layer).
# Plan 39 T2 (W1): a mask is a pattern — a pixel passes (1) or it does not
# (0), a value between only an edge a softness or a feather asked for — on
# its own wire, never in a picture's alpha; wired where a picture is taken
# it reads as one (white where it passes: `MaskPicture`), one way only
IMAGE, MASK, GEOMETRY = "image", "mask", "geometry"
# plan 30 D2: the fourth port type, designed and not built
VALUE = "value"
"""A port type beside `IMAGE`, `MASK` and `GEOMETRY`: a scalar or a
small vector of floats a node publishes once a frame (plan 30, "Designed,
not built: the auxiliary ports"). Plan 28's modulation graph (`patch.py`,
whose `RENDER_VALUE` is this name) may read one as a source, like a fed
lane. Two uses are named so the node editor can draw them later without a
schema change:

- the palette's ``palette`` value **out** — its slice (the hue, sat and
  val ends, N8) and the ramp's anchors — for a lights sink (plan 29) to
  take;
- an image-in ``sample`` port on the palette that would set its params
  from a bitmap (a camera frame of a neighbouring install) — an `IMAGE`
  port whose reading becomes values.

**No node publishes or reads a `VALUE` in this plan**
(`test_the_value_port_type_exists_and_no_node_uses_it`): `Node.__init__`
type-checks a wired port, so the first node to declare one wires like
any other."""
PORT_TYPES = (IMAGE, MASK, GEOMETRY, VALUE)

# ---------------------------------------------------------------- the wiring

# where the hands geometry is drawn: its own layer, laid on at the outputs
# or before the effects (today), or inside the scene (A3) — then an output
# without the scene still gets the layer, so the same hands can be in the
# scene on the projector and a clean layer on the glass
HANDS_IN = ("layer", "scene")
# how a layer is laid on: premultiplied over (today), added, or over but
# hidden where the scene's visible surface is nearer (depth-aware)
BLENDS = ("over", "add", "depth")
# what the history captures: the scene (today), or the scene with the
# hands' layer laid on (with the hands inside the scene, the scene holds
# them already)
HISTORY_OF = ("scene", "scene+hands")
# how a hands node draws its style's parts (plan 26 A4): solid (today), or
# as lines — the edges of the same meshes (`Ghost.draw_solid(…, lines)`),
# a node's setting in the preset's graph, not a param
DRAWS = ("solid", "lines")
# plan 32 R: the media channels a `media.<c>` node reads — `media.channels.
# CHANNELS`, kept here because this module imports no media module (the
# render stack's rule); `test_the_graph_knows_the_channels_media_does`
# holds the two equal
MEDIA_CHANNELS = "abcdefgh"
# plan 35 T4 (V2, row 373): the render nodes are named in the new ids — the
# SYSTEM lines and `Graph.timed` say these: the look-back's picture, its
# capture and its cover, and the scene laid over `backdrop.image` (once
# `grounded`); a hands node is `hands` / `hands.<n>` (`wired_hands_name`),
# its layer `hands.layer`, its guide `hands.guide`, a channel `channel.a`
LOOKBACK = "lookback"
CAPTURE = "lookback(capture)"
COVER = "lookback(cover)"
BACKDROP = "backdrop"
# the side, in texels, of the picture the faces show while something other
# than the pattern is wired into them (plan 20 fork F2; plan 33 R: the size
# `shape.faces` asks of what feeds it, `Node.size_for`): square, fixed, a
# constant and not a param — 512 cannot be told from it on a face and 2048
# costs several times as much. render.py takes it from here
FACE_PIC = 1024
# plan 34 D (row 358): how a picture of its own size (`Node.own_size`: a
# delay's, a resize's, an echo's) is laid into a consumer of another shape
# — `media_tex.COVER` (`media_tex.FITS[0]`), written out because this
# module imports no media module; a test holds the two equal
OWN_FIT = 0


def channel_name(c: str) -> str:
    """Channel `c`'s node, and its name as a wired frame's wire end (plan
    35 V2): `channel.a` …"""
    return f"channel.{c}"


def hands_name(n: int) -> str:
    """The n-th hands geometry node's old id — its params' prefix by the
    naming rule (ENGINEERING §2): `ghost`, `ghost.2`, … (plan 35 V2: the
    node is `hands`, `hands.2` …, `wired_hands_name`)"""
    return "ghost" if n == 1 else f"ghost.{n}"


def layer_name(n: int) -> str:
    """The old id of the hands' layer drawn from the n-th hands node:
    `hands`, `hands.2`, … (plan 35 V2: `hands.layer`, `wired_layer_name`)"""
    return "hands" if n == 1 else f"hands.{n}"


@dataclass(frozen=True)
class HandsAt:
    """One hands geometry node of the graph (plan 26 A4): its instance
    (`n`: 1 is `ghost.*`, n ≥ 2 `ghost.<n>.*`), where it is drawn (`into`:
    `HANDS_IN`) and how (`draw`: `DRAWS`). Each node is its own `Ghost`
    with its own `ghost[.n].*` params (`Renderer.ghost_of`)."""

    n: int = 1
    into: str = "layer"
    draw: str = "solid"

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"hands instance {self.n!r}: a whole number, 1 or more")
        if self.into not in HANDS_IN:
            raise ValueError(f"hands {self.n} into {self.into!r}: one of {', '.join(HANDS_IN)}")
        if self.draw not in DRAWS:
            raise ValueError(f"hands {self.n} draw {self.draw!r}: one of {', '.join(DRAWS)}")


@dataclass(frozen=True)
class Wiring:
    """What the graph is built from (plan 26 A3). Plan 35 T4: a wired frame
    (`wired`: every wire in `wires`) is what `build_graph` builds; an
    unwired one — the words before the wired frame, below, the defaults
    the factory look — is an old preset's, which only the one-way
    migration wires (plan 36 T3: `graphmigrate.wired_wiring`; `build_graph`
    refuses it): where the hands are drawn, how their layer is laid on,
    what the history captures.
    The renderer holds one (`Renderer.wiring`); a preset's `graph` section
    sets it (A4, `GraphSpec.wiring`).

    Plan 26 A4: `draw` is the first hands node's (`HandsAt`), and `extra`
    the hands nodes after it (`ghost.2` …), each its own `Ghost`. One
    hands node makes the layer: the one `into` "layer", else the first;
    `blend` is how that layer is laid on.

    Plan 30 D1: `placed`, the effect instances the preset's graph places
    after or into a node (`EffectAt` with `after` / `into`), in the order
    the section lists them: each sits there and not in the chain's run.

    Plan 28 N4: `wires`, the preset's wires the default graph builds as
    edges (`split_wires`: those D1 would write short are in `placed`) —
    into an output's port, overriding what its switches give it; into the
    history's picture; into an effect wired on; into a composite of
    `composites`. Part of the renderer's graph key (`Renderer._graph_for`
    compares the wiring).

    Plan 32 R: `backdrop`, the channel laid under the scene (`BACKDROP`),
    and `backdrop_history`, whether the capture takes it with the scene.
    Plan 33 R: the channel is the section's (`media.<c> → backdrop.image`,
    `GraphSpec.wiring`); a branch into `backdrop.image` is one of `wires`.

    Plan 33 R: `run`, the effects wired from `frame` into `fx.image`, in
    wire order — the run into All outputs' picture once wired; `()` is the empty
    run (`frame → fx.image`), and so is None (R23, plan 33 T7: the
    order-built stack is gone — a wiring no preset's graph reached, a test
    rig's, a tool's, the app's before its first load, runs no effect; one
    that wants effects gets its run as a load does, `graphmigrate.wiring_for`)."""

    hands: str = "layer"
    blend: str = "over"
    history: str = "scene"
    draw: str = "solid"
    extra: tuple[HandsAt, ...] = ()
    placed: tuple[EffectAt, ...] = ()
    wires: tuple[Wire, ...] = ()
    composites: tuple[CompositeAt, ...] = ()
    # plan 32 R (row 330): the media channel laid under the scene before the
    # history ("" none, else a letter of `MEDIA_CHANNELS`), and whether the
    # history captures it too. Plan 33 R: the channel is the preset's graph
    # (the wire `media.<c> → backdrop.image`); `backdrop_history` the old
    # words' capture of it (plan 36 T3: the migration writes it as the
    # capture wire; nothing lays it on per frame)
    backdrop: str = ""
    backdrop_history: bool = False
    run: tuple[str, ...] | None = None
    # plan 35 F: a wired frame's (`GraphSpec.wired`): `wires` holds every
    # wire, and any hands node may have a layer (row 380). T2's builder reads
    # it; T1 sets it so a wired section reads
    wired: bool = False
    # plan 35 F: a wired frame's copies (`CopyAt`: each one's `of`), by instance
    copies: tuple[CopyAt, ...] = ()
    # plan 36 T2: in a wired frame, the hands node whose layer `blend` is
    # (its entry's `laid`): how that layer is laid on at an output — any
    # other layer is laid over
    laid_on: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.backdrop, str) or (
                self.backdrop and (len(self.backdrop) != 1
                                   or self.backdrop not in MEDIA_CHANNELS)):
            raise ValueError(f"wiring backdrop {self.backdrop!r}: '' or a channel of "
                             f"{MEDIA_CHANNELS}")
        if not isinstance(self.backdrop_history, bool):
            raise ValueError(  # noqa: TRY004 — the Wiring's one error type, as its other checks
                f"wiring backdrop_history {self.backdrop_history!r}: true or false")
        names = [getattr(e, "name", None) for e in self.placed]
        if (any(not isinstance(e, EffectAt) or not e.placed for e in self.placed)
                or len(set(names)) != len(names)):
            raise ValueError(f"wiring placed {self.placed!r}: placed effect instances, "
                             "each once")
        for name, value, allowed in (("hands", self.hands, HANDS_IN),
                                     ("blend", self.blend, BLENDS),
                                     ("history", self.history, HISTORY_OF),
                                     ("draw", self.draw, DRAWS)):
            if value not in allowed:
                raise ValueError(f"wiring {name} {value!r}: one of {', '.join(allowed)}")
        ns = [getattr(h, "n", None) for h in self.extra]
        if (any(not isinstance(h, HandsAt) or h.n < 2 for h in self.extra)
                or len(set(ns)) != len(ns)):
            raise ValueError(f"wiring extra {self.extra!r}: hands nodes numbered 2 or more, "
                             "each once")
        layers = [h for h in self.nodes() if h.into == "layer"]
        if len(layers) > 1 and not self.wired:
            raise ValueError("wiring: one hands node makes the layer, not "
                             + " and ".join(hands_name(h.n) for h in layers))

    def nodes(self) -> list[HandsAt]:
        """Every hands node, the first first, then by instance."""
        return [HandsAt(1, self.hands, self.draw), *sorted(self.extra, key=lambda h: h.n)]

    def layer_node(self) -> HandsAt:
        """The hands node whose layer the outputs lay on: the one drawn
        `into` "layer", else the first (A3: the scene's hands, laid on an
        output without the scene)."""
        nodes = self.nodes()
        return next((h for h in nodes if h.into == "layer"), nodes[0])

    def in_scene(self) -> list[HandsAt]:
        """The hands nodes drawn inside the scene, in instance order."""
        return [h for h in self.nodes() if h.into == "scene"]


# plan 36 T3 (W3): the empty wired frame — what a renderer draws before a
# preset lands, and a `/7` with no graph section (or an empty one): only the
# outputs, nothing wired, black. There is no other fallback.
EMPTY = Wiring(wired=True)
UNWIRED_WIRING = ("an unwired Wiring is the words before the wired frame (plan 35): an old "
                  "preset's — wire it by the one-way migration (graphmigrate.wired_wiring)")


# ---------------------------------------------------------------- the preset's graph

class GraphError(ValueError):
    """A preset's `graph` section this build cannot read: the load notes
    it and takes the default graph (plan 26 A4)."""


# plan 30 D1: the names a placed effect may sit after or into — the graph's
# own node names, the words the OUTPUT and SYSTEM pages use: the scene, a
# hands' layer, the history, an output, an effect instance
PLACE_KEYS = ("after", "into")
_INSTANCE = r"(?:[2-9]|[1-9][0-9]+)"
# (plan 35 V2: and the new ids a wired frame places on — `lookback`, the
# layers `hands.layer`, `hands.<n>.layer`)
_PLACE_NODE = re.compile(rf"scene|history|lookback|hands(?:\.{_INSTANCE})?(?:\.layer)?"
                         r"|output\.[1-9][0-9]*")
# plan 33 G: the wire ends that are no effect — `frame`, the pipeline end
# `fx`, the faces' `shape`, `pattern`, `backdrop`, `switch` — so no effect
# file may take them, and no effect's place is one of them. Plan 34 L: and
# feedback's `delay`, `resize`, `echo` (`echo.<k>`) and `dream`. Plan 35 F:
# and the wired frame's `copy` (`copy.<n>`) and the source word `ground`.
# Plan 39 T2: and the mask node `matte` (`matte.<n>`); T3: and `cut` (`cut.<n>`);
# T4: and `segment` (`segment.<n>`)
RESERVED = ("frame", "fx", "pattern", "shape", "backdrop", "switch", "delay", "resize", "echo",
            "dream", "copy", "ground", "matte", "cut", "segment")
_PLACE_EFFECT = re.compile(rf"(?!(?:{'|'.join(RESERVED)})(?![a-z0-9_]))"
                           rf"[a-z][a-z0-9_]*(?:\.{_INSTANCE})?")
PLACE_WORDS = {"after": "scene, hands, hands.2 …, history, output.1 …, or an effect",
               "into": "history, output.1 …, or an effect"}


def instance_name(file: str, n: int) -> str:
    """An effect instance's name as `FxState` knows it: `acid`, `acid.2`."""
    return file if n == 1 else f"{file}.{n}"


def placement_error(effect: str, key: str, where: Any,
                    effects: set[str] | frozenset[str] | None = None) -> str | None:
    """Why effect instance `effect` cannot sit `key` ("after" / "into")
    `where`, in words — None when it can (plan 30 D1). `effects`: the
    effect instance names this build knows (None: any well-formed name).
    `into` takes the image input of the history, an output or an effect:
    the scene's and a hands' layer's inputs are geometry, so those two
    take `after`. `after output.<n>` is that output's picture, as `into`."""
    if not isinstance(where, str):
        return (f"{effect} {key} {where!r} — a node's name in quotes: this build places "
                f"{key} {PLACE_WORDS[key]}")
    if where == effect:
        return f"{effect} {key} {where!r} — an effect cannot sit {key} itself"
    if _PLACE_NODE.fullmatch(where):
        if key == "into" and (where == "scene" or where.startswith("hands")):
            return (f"{effect} into {where!r} — its inputs are geometry, not a picture: "
                    f"after {where!r} folds its picture")
        return None
    if _PLACE_EFFECT.fullmatch(where) and (effects is None or where in effects):
        return None
    return f"{effect} {key} {where!r} — this build places {key} {PLACE_WORDS[key]}"


@dataclass(frozen=True)
class EffectAt:
    """An effect instance the preset's graph names (plan 26 A4, plan 30 D1).

    Unplaced: an instance of a file — an extra one, `fx.<file>.<n>.*`
    (n ≥ 2), its own params and clock, or (plan 33 R21) instance 1, the
    file's own `fx.<file>.*`, named with no `instance` when the section
    keeps it on no wire (taken out of the run: kept, unreached, faint on
    the canvas — row 349). Plan 33 R: where it draws is its wires (a run
    from `frame`, a branch), never its `order`; one on no wire has no node.

    Placed (D1): `after` a node — on that node's output, every consumer
    of its picture reading the effect instead — or `into` one — on that
    node's `image` input alone (`output.<n>`: that output's picture) —
    one of the two, never both; then any instance, 1 included, may be
    named. A placed instance is in no pipeline's run: it sits where it is
    put. Plan 36 T3: only in an old section — the one-way migration writes
    it as the wires it stands for (`graphmigrate.placed_wires`), and a `/7`
    frame reads no placement (`PLACEMENT_IS_A_WIRE`)."""

    file: str
    n: int
    after: str | None = None
    into: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.file, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", self.file):
            raise ValueError(f"effect file {self.file!r}: an effect's file name, "
                             "lower_snake_case")
        if self.file in RESERVED:
            raise ValueError(f"effect file {self.file!r}: a name the graph's wires keep "
                             f"({', '.join(RESERVED)})")
        if self.after is not None and self.into is not None:
            raise ValueError(f"{self.file} after {self.after!r} and into {self.into!r} at "
                             "once — one of the two")
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"effect {self.file} instance {self.n!r}: a whole number from 1")
        # (plan 33 R21: an unplaced instance 1 is the file kept on no wire —
        # T1's "instance 1 is the file itself, always there" was the stack's)
        for key in PLACE_KEYS:
            where = getattr(self, key)
            why = placement_error(self.name, key, where) if where is not None else None
            if why is not None:
                raise ValueError(why)

    @property
    def name(self) -> str:
        """The instance's name (`palette`, `acid.2`): its params' prefix
        after `fx.`, its node's name in the scene's pipeline."""
        return instance_name(self.file, self.n)

    @property
    def placed(self) -> bool:
        return self.after is not None or self.into is not None

    @property
    def where(self) -> tuple[str, str] | None:
        """("after" | "into", the node's name), or None: where its wires
        put it (plan 33: no stack holds it)."""
        if self.after is not None:
            return "after", self.after
        if self.into is not None:
            return "into", self.into
        return None

    def unplaced(self) -> EffectAt | None:
        """This instance at the default placement: where its wires put
        it (None for instance 1: a D1 placement refused leaves the file
        where its wires put it — R21's unwired entry is written, never made here)."""
        return EffectAt(self.file, self.n) if self.n >= 2 else None


def placement_loops(placed) -> dict[str, str]:
    """The placed effects (`EffectAt`s) whose placement makes a loop —
    each sits after or into another placed effect that, followed on,
    comes back to it — with the loop in words (`palette after acid.2
    after palette`): effect name → words. Refused at read and again at
    build (plan 30 D1): the effect takes the default placement."""
    by = {e.name: e for e in placed if e.placed}
    out: dict[str, str] = {}
    for e in by.values():
        path, cur = [e.name], e
        while cur.where is not None and cur.where[1] in by:
            nxt = cur.where[1]
            if nxt == e.name:
                out[e.name] = " ".join(f"{n} {by[n].where[0]}" for n in path) + f" {e.name}"
                break
            if nxt in path:
                break                         # a loop further on, not through this one
            path.append(nxt)
            cur = by[nxt]
    return out


@dataclass(frozen=True)
class HistoryAt:
    """The history node: what its capture holds (`HISTORY_OF`)."""

    holds: str = "scene"

    def __post_init__(self) -> None:
        if self.holds not in HISTORY_OF:
            raise ValueError(f"history holds {self.holds!r}: one of {', '.join(HISTORY_OF)}")


def _entry_keys(e: dict, kind: str, allowed: tuple[str, ...]) -> None:
    extra = sorted(set(e) - {"kind", *allowed})
    if extra:
        raise GraphError(f"{kind} node: no key {', '.join(map(repr, extra))} "
                         f"(it takes {', '.join(allowed) or 'nothing'})")


def _instance(e: dict) -> int:
    n = e.get("instance", 1)
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise GraphError(f"{e.get('kind')} node: instance {n!r}, a whole number from 1")
    return n


def _hands_entry(e: dict, wired: bool = False) -> tuple[HandsAt, str | None]:
    if wired and "into" in e:
        # plan 35 F: in a wired frame the hands go into the scene by a wire
        raise GraphError(INTO_IS_A_WIRE.format(hands=wired_hands_name(_instance(e))))
    _entry_keys(e, "hands", ("instance", "into", "draw", "laid"))
    laid = e.get("laid")
    if laid is not None and laid not in BLENDS:
        raise GraphError(f"hands node: laid {laid!r}, one of {', '.join(BLENDS)}")
    return HandsAt(_instance(e), e.get("into", "layer"), e.get("draw", "solid")), laid


def _effect_entry(e: dict) -> tuple[EffectAt | None, str | None]:
    """(the instance, None), or — for a placement this build cannot honour
    (plan 30 D1: both keys at once, a name that is not a string or not in
    the placeable vocabulary) — (the instance at the default placement,
    or None for instance 1, which its wires name; the reason).
    `read_graph` notes the reason; the rest of the graph stands."""
    _entry_keys(e, "effect", ("instance", "file", *PLACE_KEYS))
    if "file" not in e:
        raise GraphError("effect node: names no file")
    file, n = e["file"], _instance(e)
    after, into = e.get("after"), e.get("into")
    if "after" not in e and "into" not in e:
        return EffectAt(file, n), None
    EffectAt(file, max(n, 2))                 # the file's name is the file's, placed or not
    name = instance_name(file, n)
    if "after" in e and "into" in e:
        why = f"{name} after {after!r} and into {into!r} at once — one of the two"
    else:
        # a key present is a placement: an explicit null is not a name
        key, where = ("after", after) if "after" in e else ("into", into)
        why = placement_error(name, key, where)
        if why is None:
            return EffectAt(file, n, after=after, into=into), None
    return (EffectAt(file, n) if n >= 2 else None), why


def _history_entry(e: dict, wired: bool = False) -> HistoryAt | LookbackAt:
    """A `history` entry (plan 26 A4), or (plan 35 F) the look-back's
    `{"kind": "lookback"}` of a wired frame, whose `holds` is a wire now
    (`lookback.capture`). In a wired frame `history` is the old id
    (`OLD_ID_IN_A_WIRED_FRAME`; T3's `graphmigrate.renamed` renames it)."""
    if e.get("kind") == "lookback":
        if "holds" in e:
            raise GraphError(HOLDS_IS_A_WIRE)
        _entry_keys(e, "lookback", ("instance",))
        return LookbackAt(_instance(e))
    if wired:
        raise GraphError(OLD_ID_IN_A_WIRED_FRAME.format(old="history", new=new_id("history")))
    _entry_keys(e, "history", ("holds",))
    return HistoryAt(e.get("holds", "scene"))


# The node kinds a preset's graph may name: kind → the reader of one entry
# (a dict with "kind"). A kind missing here is unknown: a note and the
# default graph, never a crash. A later WP adds its kind with one line
# here (plan 26 A4b: the point cloud) and its node class in its own block;
# an entry of a kind not hands / effect / history rides in
# `GraphSpec.others` as its reader returned it.
NODE_KINDS: dict[str, Any] = {
    "hands": _hands_entry,
    "effect": _effect_entry,
    "history": _history_entry,
}


# ---------------------------------------------------------------- wires (plan 28 N4)
#
# The preset's graph is nodes plus a wire list: `{"nodes": [...], "wires":
# [{"from": "hands.2", "to": "output.2.hands"}, {"from": "palette", "to":
# "output.1.image"}]}`. A wire names a node's output (`from`: the node's
# name) and an input port (`to`: `<node>.<port>`). An input no wire names
# is the default graph's: an output's ports follow the session's switches
# (the rig's, not the look's); an effect is where its wires put it, and one
# on no wire is in no run (plan 33: no stack holds it).
# D1's `after` / `into` are the same wires written short, and read as such
# (`d1_wires`): `{"file": "palette", "after": "hands"}` is the wire
# `hands → palette.image`, `{"file": "palette", "into": "output.2"}` the
# wire `palette → output.2.image`.

WIRE_KEYS = ("from", "to")
_LAYER = re.compile(rf"hands(?:\.{_INSTANCE})?")
_GHOST = re.compile(rf"ghost(?:\.{_INSTANCE})?")
# plan 35 F: and All outputs, `output.all` (a wired frame's: outside one
# `wire_node_kind` keeps plan 34's table, which has no such output)
_OUTPUT = re.compile(r"output\.(?:[1-9][0-9]*|all)")
_COMPOSITE = re.compile(rf"composite(?:\.{_INSTANCE})?")
_MEDIA = re.compile(rf"media\.[{MEDIA_CHANNELS}]")     # plan 32 R: a channel, a wire's end
_SWITCH = re.compile(rf"switch(?:\.{_INSTANCE})?")       # plan 33 S: `switch`, `switch.2` …
# plan 34 L: `delay`, `delay.2` …; `resize`, `resize.2` …; `echo.1` … (the
# index's range is the entry's to say: `echo.40` is an echo none declares)
_DELAY = re.compile(rf"delay(?:\.{_INSTANCE})?")
_RESIZE = re.compile(rf"resize(?:\.{_INSTANCE})?")
_MATTE = re.compile(rf"matte(?:\.{_INSTANCE})?")         # plan 39 T2: `matte`, `matte.2` …
_CUT = re.compile(rf"cut(?:\.{_INSTANCE})?")             # plan 39 T3: `cut`, `cut.2` …
_SEGMENT = re.compile(rf"segment(?:\.{_INSTANCE})?")     # plan 39 T4: `segment`, `segment.2` …
# plan 39 T4: a segment's pins — its foreground, its background, its matte
# (`segment.fg`, `segment.2.mask` …)
_SEGMENT_PIN = re.compile(rf"(segment(?:\.{_INSTANCE})?)\.(fg|bg|mask)")
_ECHO = re.compile(r"echo\.[1-9][0-9]*")
# plan 36 T4 (W4): a look-back's instances (`lookback`, `lookback.2` …), its
# echo outputs — pins, frames of its own ring (`lookback.echo.3`,
# `lookback.2.echo.1`) — and the dream's (`dream`; a second, `dream.2`, is
# named only to be refused: one live dream at a time, D2)
_LOOKBACK = re.compile(rf"lookback(?:\.{_INSTANCE})?")
_ECHO_PIN = re.compile(rf"(lookback(?:\.{_INSTANCE})?)\.echo\.([1-9][0-9]*)")
_DREAM = re.compile(rf"dream(?:\.{_INSTANCE})?")
SWITCH_PORTS = tuple(f"in{i}" for i in range(1, 9))
# what each kind of wireable node makes, and the ports a wire may go into
# (port → type). The scene's and a layer's geometry ports and the
# history's mask port are typed so a drag can say why it is refused: a
# hands node's place is its `into`, the cover is the history's own
WIRE_MAKES = {"scene": IMAGE, "history": IMAGE, "layer": IMAGE, "effect": IMAGE,
              "composite": IMAGE, "ghost": GEOMETRY, "cover": MASK, "output": None,
              "media": IMAGE,
              # plan 33 G: the pipeline's picture before its effects, the
              # face pattern as a picture, a switch's selected input; the
              # pipeline end, the faces and the backdrop make nothing
              "frame": IMAGE, "pattern": IMAGE, "switch": IMAGE,
              "fx": None, "shape": None, "backdrop": None,
              # plan 34 L: last frame's picture, a picture at a size of its
              # own, a look-back frame and the dream buffer
              "delay": IMAGE, "resize": IMAGE, "echo": IMAGE, "dream": IMAGE}
WIRE_TAKES: dict[str, dict[str, str]] = {
    "output": {"image": IMAGE, "hands": IMAGE, "readout": IMAGE},
    "history": {"image": IMAGE, "cover": MASK},
    "effect": {"image": IMAGE, "aux": IMAGE},      # plan 32 R: aux, its second picture
    "composite": {"under": IMAGE, "over": IMAGE},
    "scene": {"geometry": GEOMETRY},
    "layer": {"geometry": GEOMETRY},
    "ghost": {}, "cover": {}, "media": {}, "frame": {},
    # plan 33 G: the run's end, the pattern's media layer, the faces, the
    # backdrop, and a switch's eight pictures
    "fx": {"image": IMAGE}, "pattern": {"media": IMAGE}, "shape": {"faces": IMAGE},
    "backdrop": {"image": IMAGE}, "switch": {p: IMAGE for p in SWITCH_PORTS},
    # plan 34 L: what a delay keeps for next frame, what a resize crops; an
    # echo and the dream read the look-back, never a wire
    "delay": {"image": IMAGE}, "resize": {"image": IMAGE}, "echo": {}, "dream": {},
}
TYPE_WORDS = {IMAGE: "a picture", GEOMETRY: "geometry", MASK: "a mask", None: "nothing"}
WIRE_FROM_WORDS = ("scene, hands …, history, frame, pattern, an effect, a composite, "
                   "a switch, a delay, a resize, echo.1 …, dream or a channel (media.a …)")
WIRE_TO_WORDS = ("output.1 … (image, hands, readout), history.image, fx.image, "
                 "shape.faces, backdrop.image, pattern.media, an effect's image or aux, "
                 "a composite's under / over, a switch's in1 … in8, or a delay's or a "
                 "resize's image")
# plan 33 G: the kinds whose input ports end a path — what a picture is
# for. `reaches` follows the picture ports back from these
SINKS = ("output", "fx", "shape", "pattern", "backdrop", "history")
# a node that takes a picture and puts it outside the graph makes none
NO_SOURCE = ("output", "fx", "shape", "backdrop")
AUX = "aux"     # plan 32 R: an effect's second picture port (`Effect.INPUTS`)


def wire_node_kind(name: Any, wired: bool = False) -> str | None:
    """What kind of node a wire's name is (`WIRE_MAKES`'s keys), or None.
    Plan 35 F: `wired`, a name of a wired frame (`WIRED_MAKES`' keys), in
    the new ids — `hands` is the hands geometry there, `hands.layer` its
    layer — where an old id (`ghost`, `history`, `media.a` …) is no node."""
    if not isinstance(name, str):
        return None
    if wired:
        return _wired_kind(name)
    if name == ALL_OUTPUTS:
        return None
    if name in ("scene", "history", "cover"):
        return name
    if name in ("frame", "fx", "pattern", "shape", "backdrop", "dream"):
        return name
    for kind, pat in (("layer", _LAYER), ("ghost", _GHOST), ("output", _OUTPUT),
                      ("composite", _COMPOSITE), ("media", _MEDIA), ("switch", _SWITCH),
                      ("delay", _DELAY), ("resize", _RESIZE), ("echo", _ECHO)):
        if pat.fullmatch(name):
            return kind
    if _PLACE_EFFECT.fullmatch(name):
        return "effect"
    return None


def is_aux(w: Wire) -> bool:
    """Whether wire `w` goes into an effect's `aux` port (plan 32 R): an
    input beside the picture, never a placement — the effect stays where
    it sits (its run, D1's place, its own wires) and reads `w.src` there."""
    return w.port == AUX and wire_node_kind(w.node) == "effect"


def split_instance(name: str) -> tuple[str, int]:
    """`acid.2` → ("acid", 2); `palette` → ("palette", 1)."""
    head, _, n = name.partition(".")
    return head, int(n) if n else 1


def _wire_node(dst: Any) -> str | None:
    """A raw wire entry's `to` → the node it goes into, or None."""
    return dst.rpartition(".")[0] if isinstance(dst, str) else None


@dataclass(frozen=True)
class Wire:
    """One wire of the preset's graph (plan 28 N4): `src`, a node's name
    (its output), into `dst`, `<node>.<port>` (`output.2.hands`,
    `acid.2.image`). JSON `{"from": src, "to": dst}`."""

    src: str
    dst: str

    def __post_init__(self) -> None:
        if (not isinstance(self.src, str) or not isinstance(self.dst, str) or not self.src
                or "." not in self.dst):
            raise ValueError(f"wire {self.src!r} → {self.dst!r}: from a node's name into "
                             "'<node>.<port>'")

    @property
    def node(self) -> str:
        """The node the wire goes into (`output.2`, `acid.2`)."""
        return self.dst.rpartition(".")[0]

    @property
    def port(self) -> str:
        return self.dst.rpartition(".")[2]

    def to_json(self) -> dict:
        return {"from": self.src, "to": self.dst}

    def __str__(self) -> str:
        return f"{self.src} → {self.dst}"


@dataclass(frozen=True)
class CompositeAt:
    """A composite node the preset's graph adds (plan 28 N4): `under` with
    `over` laid on it at `blend`, its ports and its picture wired by the
    wire list — `composite`, `composite.2` … One no wire feeds is built
    nowhere."""

    n: int = 1
    blend: str = "over"

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"composite instance {self.n!r}: a whole number from 1")
        if self.blend not in BLENDS:
            raise ValueError(f"composite blend {self.blend!r}: one of {', '.join(BLENDS)}")

    @property
    def name(self) -> str:
        return "composite" if self.n == 1 else f"composite.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "composite"}
        if self.n != 1:
            d["instance"] = self.n
        if self.blend != "over":
            d["blend"] = self.blend
        return d


def _composite_entry(e: dict) -> CompositeAt:
    _entry_keys(e, "composite", ("instance", "blend"))
    return CompositeAt(_instance(e), e.get("blend", "over"))


NODE_KINDS["composite"] = _composite_entry


@dataclass(frozen=True)
class SwitchAt:
    """A switch node the preset's graph adds (plan 33 S): eight picture
    inputs `in1` … `in8` and one picture out — the selected input's, by
    the param `switch[.n].select` (off, 1–8; a value, not the graph) —
    `switch`, `switch.2` … One no wire feeds or reads is kept, unreached."""

    n: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"switch instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "switch" if self.n == 1 else f"switch.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "switch"}
        if self.n != 1:
            d["instance"] = self.n
        return d


def _switch_entry(e: dict) -> SwitchAt:
    _entry_keys(e, "switch", ("instance",))
    return SwitchAt(_instance(e))


NODE_KINDS["switch"] = _switch_entry


@dataclass(frozen=True)
class DelayAt:
    """A delay node the preset's graph adds (plan 34 L): one picture input
    `image`, and out the picture that came into it last frame (z⁻¹) — so a
    loop drawn through one is legal (`wire_loops`) —
    `delay`, `delay.2` … One whose picture reaches nothing is unreached
    and holds no buffer (`reaches`)."""

    n: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"delay instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "delay" if self.n == 1 else f"delay.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "delay"}
        if self.n != 1:
            d["instance"] = self.n
        return d


def _delay_entry(e: dict) -> DelayAt:
    _entry_keys(e, "delay", ("instance",))
    return DelayAt(_instance(e))


NODE_KINDS["delay"] = _delay_entry


@dataclass(frozen=True)
class ResizeAt:
    """A resize node the preset's graph adds (plan 34 L, Z): its input
    `image` cropped and made at a size of its own (`resize[.n].*`, values,
    not the graph) — `resize`, `resize.2` …"""

    n: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"resize instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "resize" if self.n == 1 else f"resize.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "resize"}
        if self.n != 1:
            d["instance"] = self.n
        return d


def _resize_entry(e: dict) -> ResizeAt:
    _entry_keys(e, "resize", ("instance",))
    return ResizeAt(_instance(e))


NODE_KINDS["resize"] = _resize_entry


@dataclass(frozen=True)
class MatteAt:
    """A matte node the preset's graph adds (plan 39 T2, W2): its input
    `image` made a mask — by brightness, coverage or a keyed hue
    (`matte[.n].*`, values, not the graph) — `matte`, `matte.2` …"""

    n: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"matte instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "matte" if self.n == 1 else f"matte.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "matte"}
        if self.n != 1:
            d["instance"] = self.n
        return d


def _matte_entry(e: dict) -> MatteAt:
    _entry_keys(e, "matte", ("instance",))
    return MatteAt(_instance(e))


NODE_KINDS["matte"] = _matte_entry


@dataclass(frozen=True)
class CutAt:
    """A cut node the preset's graph adds (plan 39 T3, W3): its `image`
    cut by the mask on its `mask` port — where the mask passes the picture,
    elsewhere cut away (`cut[.n].*`, values, not the graph) — `cut`,
    `cut.2` …"""

    n: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"cut instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "cut" if self.n == 1 else f"cut.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "cut"}
        if self.n != 1:
            d["instance"] = self.n
        return d


def _cut_entry(e: dict) -> CutAt:
    _entry_keys(e, "cut", ("instance",))
    return CutAt(_instance(e))


NODE_KINDS["cut"] = _cut_entry


@dataclass(frozen=True)
class SegmentAt:
    """A segment node the preset's graph adds (plan 39 T4, W4): its `image`
    cut into a foreground and a background by a matte — three pins,
    `segment.fg`, `segment.bg`, `segment.mask` — the mode, the model's
    level and the rest values (`segment[.n].*`), never the entry —
    `segment`, `segment.2` …"""

    n: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"segment instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "segment" if self.n == 1 else f"segment.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "segment"}
        if self.n != 1:
            d["instance"] = self.n
        return d


def _segment_entry(e: dict) -> SegmentAt:
    _entry_keys(e, "segment", ("instance",))
    return SegmentAt(_instance(e))


NODE_KINDS["segment"] = _segment_entry


@dataclass(frozen=True)
class EchoAt:
    """A look-back frame as a source (plan 34 L, E): `echo.<n>`, the ring's
    n-th newest commit (1 the newest, `MAX_ECHOES` the oldest). No input:
    it is read before this frame's capture writes, so no loop runs
    through it."""

    n: int

    def __post_init__(self) -> None:
        if (not isinstance(self.n, int) or isinstance(self.n, bool)
                or not 1 <= self.n <= MAX_ECHOES):
            raise ValueError(f"echo node: index {self.n!r}, a whole number from 1 to "
                             f"{MAX_ECHOES}")

    @property
    def name(self) -> str:
        return f"echo.{self.n}"

    def to_json(self) -> dict:
        return {"kind": "echo", "index": self.n}


def _echo_entry(e: dict) -> EchoAt:
    _entry_keys(e, "echo", ("index",))
    if "index" not in e:
        raise GraphError("echo node: names no index (echo.1 is the newest)")
    try:
        return EchoAt(e["index"])
    except ValueError as err:
        raise GraphError(str(err)) from err


NODE_KINDS["echo"] = _echo_entry


@dataclass(frozen=True)
class DreamAt:
    """The dream (plan 36 T4, W4; was plan 34's dream-buffer source):
    picture in → dreamed picture out — `dream`. One live dream at a time
    (D2: one worker, one GPU job): a second (`{"kind": "dream", "instance":
    2}`) may be declared, but a wire to or from it is refused in words."""

    n: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"dream instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "dream" if self.n == 1 else f"dream.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "dream"}
        if self.n != 1:
            d["instance"] = self.n
        return d


def _dream_entry(e: dict) -> DreamAt:
    _entry_keys(e, "dream", ("instance",))
    return DreamAt(_instance(e))


NODE_KINDS["dream"] = _dream_entry


# ---------------------------------------------------------------- the wired frame (plan 35 F, V2)
#
# A section that says `"frame": "wired"` holds the whole frame in its wires
# and entries — the shape to the outputs — in the owner's names (V2, row
# 373: `hands` the tracked hands as geometry, `hands.layer` their layer,
# `hands.guide` their guide, `lookback` the look-back, `channel.a` a media
# channel). Nothing is built that no wire or entry says (T2's builder).
# Outside one, plan 34's words hold unchanged: an old section is read in
# the old ids, and T3's migration renames it (`graphmigrate.renamed`).

FRAME_KEY = "frame"           # the section's third key …
WIRED_FRAME = "wired"         # … and its one value
ALL_OUTPUTS = "output.all"    # the bus: what a window shows by the rig's cable from it
GROUND = "ground"             # a source with no node: wired into an output's port, nothing
# the frame's entry kinds (`layer` and `guide` take `instance`): a frame
# node exists when a wire names it or an entry declares it (GRAPH keeps
# an unwired one so, faint)
FRAME_KINDS = ("scene", "shape", "backdrop", "pattern", "lookback", "layer", "guide")
# the one port several wires go into, drawn in their section order
MANY_PORTS = frozenset({"scene.geometry"})
# what a picture is for in a wired frame (`reaches`): every port of an
# `output.<n>` or `output.all`, and what the look-back records
SINK_PORTS = ("output", "lookback.capture")
# plan 36 T2 (W2): no edge is read that no wire says. A node's second
# outputs are pins, named `<node>.<pin>` as a wire's `from` (as All
# outputs' bus pins are): the scene's faces' coverage mask, which the
# look-back's `cover` takes, and its depth, which a composite's or an
# output's `depth` takes (the hands laid depth-aware). A pin is its node:
# reaching it reaches the node, a loop through it runs through the node
# Plan 39 T4: and a segment's three — its foreground and background
# pictures and its matte (`segment.2.fg` … too: `_SEGMENT_PIN`); unlike the
# scene's, each goes wherever its type is taken
PINS = {"scene.cover": "scene", "scene.depth": "scene",
        "segment.fg": "segment", "segment.bg": "segment", "segment.mask": "segment"}
DEPTH_PORT = "depth"
# the pin kinds a segment's pins are (`_wired_kind`): what each makes
SEGMENT_PINS = {"fg": IMAGE, "bg": IMAGE, "mask": MASK}
PIN_WORDS = {"scene.cover": "the scene's faces' coverage mask: it goes into lookback.cover",
             "scene.depth": ("the scene's depth: it goes into a composite's or an output's "
                             "depth")}
SEGMENT_IS_ITS_PINS = ("{name} makes its pictures on its pins: {name}.fg (the foreground), "
                       "{name}.bg (the background), {name}.mask (the matte)")
DEPTH_TAKES = ("{dst} takes the scene's depth (scene.depth), for the hands laid "
               "depth-aware")
LAYER_TAKES_HANDS = "{dst} takes a hands node (hands, hands.2 …): the hands it draws"


def pin_node(name: Any) -> str | None:
    """The node pin `name` (`scene.cover`, `scene.depth`) is an output of,
    or None for a name that is no pin (plan 36 T2). Plan 36 T4: and a
    look-back's echo (`lookback.2.echo.3` → `lookback.2`)."""
    if not isinstance(name, str):
        return None
    got = PINS.get(name)
    if got is None:
        m = _ECHO_PIN.fullmatch(name) or _SEGMENT_PIN.fullmatch(name)
        return m.group(1) if m is not None else None
    return got


def segment_pin(name: Any) -> tuple[str, str] | None:
    """A segment's pin → (the segment, which: fg, bg or mask) —
    `segment.2.bg` → ("segment.2", "bg"); None for any other name (plan 39 T4)."""
    m = _SEGMENT_PIN.fullmatch(name) if isinstance(name, str) else None
    return (m.group(1), m.group(2)) if m is not None else None


def echo_of(name: Any) -> tuple[str, int] | None:
    """A look-back's echo pin → (the look-back, k): `lookback.echo.3` →
    ("lookback", 3) — None for any other name (plan 36 T4)."""
    m = _ECHO_PIN.fullmatch(name) if isinstance(name, str) else None
    return (m.group(1), int(m.group(2))) if m is not None else None


def capture_name(lookback: str) -> str:
    """A look-back's capture's render node (`lookback(capture)`,
    `lookback.2(capture)`): what records its `image` into its ring."""
    return f"{lookback}(capture)"


GONE_IN_A_WIRED_FRAME = ("{name} is gone in a wired frame (plan 35): wire the picture "
                         "straight into an effect, a composite or an output")
HOLDS_IS_A_WIRE = ("lookback holds: in a wired frame what the look-back records is a wire "
                   "— wire a picture into lookback.image")
INTO_IS_A_WIRE = ("{hands} into: in a wired frame the hands go into the scene by a wire — "
                  "wire {hands} into scene.geometry")
# plan 36 T3 (W3): D1's `after` / `into` are the wires they stood for since
# `/7` (`graphmigrate.placed_wires` writes them at migration) — a wired
# frame's entry that still says one is not read
PLACEMENT_IS_A_WIRE = ("{name} {key} {where!r}: a placement is not read since /7 (plan 36) "
                       "— wire {name} on GRAPH")
FRAME_VALUE = "frame {value!r}: the one value is \"wired\""
GEOMETRY_INTO_SCENE = "{src} makes geometry: it goes into scene.geometry"
COPY_NO_OF = "copy {name}: names no of (the effect instance it draws again)"
COPY_BAD_OF = "copy {name}: of {of!r} is no effect instance of this graph"
GROUND_ONLY_INTO_OUTPUTS = "ground goes only into an output's port: it shows nothing there"
OLD_ID_IN_A_WIRED_FRAME = "{old} is the old name (plan 35): in a wired frame it is {new}"
# (a frame kind's entry outside a wired frame: plan 34's table has no such node)
FRAME_KIND_UNWIRED = ("{kind} node: only in a wired frame (plan 35: the section says "
                      "\"frame\": \"wired\")")

# ---------------------------------------------------------------- the rig's wires (plan 36 T1)
#
# Plan 36 W1, decision D1: what reaches a window is a drawn cable. All
# outputs is a bus: the rig — the open show, `library.Project.rig` — owns
# one cable per window and port, `output.all.<port> → output.<n>.<port>`
# for the picture, the hands and the guide (`bus_wire`), present until
# the show cuts it, drawn on GRAPH and cut or joined there like any wire.
# A preset's own wire into a window's port takes that port: the bus cable
# into it is then neither drawn nor read (`window_ports`, the one rule).
# `RigWires` is the show's word on its own wires — which of the rig's
# defaults it has cut — and `present` the wires that stand; any other
# rig-owned wire (plan 36 T2: a cloud's) is one more set of defaults.
#
# Plan 36 T2 (W2): a window's fourth port, `depth` — the scene's depth the
# hands are laid against depth-aware — rides the bus like the others. And
# a cloud device is the rig's, so its wire into the scene is too:
# `cloud → scene.geometry`, `cloud.2 → scene.geometry` … one per listed
# cloud device (`cloud_wires`), standing until the show cuts it.

BUS_PORTS = ("image", "hands", "guide", "depth")   # the ports a bus cable feeds, per window


def bus_wire(n: int, port: str) -> Wire:
    """The rig's bus cable from All outputs into window `n`'s `port`."""
    return Wire(f"{ALL_OUTPUTS}.{port}", f"output.{n}.{port}")


def is_bus(w: Wire) -> bool:
    """Whether `w` is a bus cable: All outputs' `<port>` into the same port
    of a window (`output.<n>`)."""
    head, _, n = w.node.partition(".")
    return (head == "output" and n.isdecimal() and int(n) >= 1 and w.port in BUS_PORTS
            and w.src == f"{ALL_OUTPUTS}.{w.port}")


def cloud_name(i: int) -> str:
    """The point-cloud node of the `i`-th listed cloud device (from 0):
    `cloud`, `cloud.2` … (the naming rule's marker form)."""
    return "cloud" if i == 0 else f"cloud.{i + 1}"


def cloud_wire(i: int) -> Wire:
    """Plan 36 T2: the rig's wire of the `i`-th cloud into the scene."""
    return Wire(cloud_name(i), "scene.geometry")


def cloud_wires(roles) -> tuple[Wire, ...]:
    """The rig's cloud wires for the listed cloud devices `roles`, in order."""
    return tuple(cloud_wire(i) for i in range(len(tuple(roles))))


def is_cloud_wire(w: Wire) -> bool:
    """Whether `w` is a cloud's wire into the scene (the rig's, plan 36 T2)."""
    head, _, n = w.src.partition(".")
    return (w.dst == "scene.geometry" and head == "cloud"
            and (not n or (n.isdecimal() and int(n) >= 2)))


def is_rig(w: Wire) -> bool:
    """Whether `w` is one of the rig's own wires (plan 36: a bus cable, a
    cloud's wire) — the show's to cut and join, never a preset's."""
    return is_bus(w) or is_cloud_wire(w)


@dataclass(frozen=True)
class RigWires:
    """The rig's own drawn wires as the show holds them (plan 36 T1): the
    defaults the show has `cut` — every other default stands. Immutable:
    `cutting` and `joining` return the new word, so an undo mark holds one
    by reference. JSON (`to_json`, in the show's file under ``rig``):
    ``{"cut": [{"from": …, "to": …}, …]}``, sorted; nothing cut is ``{}``."""

    cut: frozenset[Wire] = frozenset()

    def has(self, w: Wire) -> bool:
        """Whether default `w` stands (is not cut)."""
        return w not in self.cut

    def present(self, defaults) -> tuple[Wire, ...]:
        """The `defaults` that stand, in their order."""
        return tuple(w for w in defaults if w not in self.cut)

    def cutting(self, w: Wire) -> RigWires:
        return RigWires(self.cut | {w})

    def joining(self, w: Wire) -> RigWires:
        return RigWires(self.cut - {w})

    def to_json(self) -> dict:
        if not self.cut:
            return {}
        return {"cut": [w.to_json() for w in sorted(self.cut, key=lambda w: (w.dst, w.src))]}

    @classmethod
    def read(cls, value: Any) -> RigWires:
        """A show file's ``rig`` value; what is not a wire is left out (a
        hand-edited file never stops a show from opening)."""
        cut = value.get("cut") if isinstance(value, dict) else None
        got: set[Wire] = set()
        for x in cut if isinstance(cut, list) else ():
            try:
                got.add(Wire(x["from"], x["to"]))
            except (TypeError, KeyError, ValueError):
                continue
        return cls(frozenset(got))


def rig_of(source: Any) -> RigWires:
    """The rig wires `source` holds (duck-typed: its `rig`, as the open show
    `library.Project` has) — the renderer's `rig_source`; None, or a source
    with none, is the rig as it ships: every default standing."""
    got = getattr(source, "rig", None)
    return got if isinstance(got, RigWires) else RigWires()


def window_ports(wires, n: int, rig: RigWires | None = None) -> dict[str, Wire | None]:
    """Window `n`'s four ports (`BUS_PORTS`) → the one wire into each, or
    None: its own wire of `wires` (the preset's), else the bus cable when
    `rig` has it standing — then the wire into All outputs' same port (the
    bus carries it; None while nothing is wired there). Plan 36 W1: nothing
    else reaches a window."""
    rig = rig if rig is not None else RigWires()
    own = {w.port: w for w in wires if w.node == f"output.{n}"}
    alls = {w.port: w for w in wires if w.node == ALL_OUTPUTS}
    return {p: own[p] if p in own else (alls.get(p) if rig.has(bus_wire(n, p)) else None)
            for p in BUS_PORTS}

# V2 (row 373, "approve, but rename ids too"): old wire name → new, for
# whole names and D1's `after` / `into` values; `<n>` an instance from 2
# (an output's from 1), `<c>` a channel letter. The entry kind `history` is
# `lookback` by the same row. Every other id is unchanged: `shape`,
# `scene`, `pattern`, `backdrop`, `output.<n>`, effects, `composite`,
# `switch`, and plan 34's `delay`, `resize`, `echo.<k>`, `dream`
NEW_IDS = {
    "ghost": "hands", "ghost.<n>": "hands.<n>",
    "hands": "hands.layer", "hands.<n>": "hands.<n>.layer",
    "readout": "hands.guide", "readout.<n>": "hands.<n>.guide",
    "history": "lookback",
    "media.<c>": "channel.<c>",
    "output.<n>.readout": "output.<n>.guide",
}
OLD_IDS = {new: old for old, new in NEW_IDS.items()}
# params keep their ids (V2): a node's params' prefix by its kind — the
# rest of the node's id after the kind's head (`hands.2` → `ghost.2`); an
# effect's is `fx.<id>`, any other node's its own id (`param_prefix`)
PARAM_PREFIX = {"hands": "ghost", "lookback": "dream", "channel": "media", "camera": "eye"}


def _id_pattern(template: str) -> re.Pattern:
    """`NEW_IDS`' template as a pattern: `<n>` an instance (an output's from
    1, a hands node's from 2), `<c>` a channel."""
    n = r"[1-9][0-9]*" if template.startswith("output.") else _INSTANCE
    out = re.escape(template).replace(re.escape("<n>"), f"(?P<n>{n})")
    return re.compile(out.replace(re.escape("<c>"), f"(?P<c>[{MEDIA_CHANNELS}])"))


_NEW_MAP = [(_id_pattern(src), dst) for src, dst in NEW_IDS.items()]
_OLD_MAP = [(_id_pattern(src), dst) for src, dst in OLD_IDS.items()]


def _mapped(name: Any, table: list[tuple[re.Pattern, str]]) -> Any:
    if not isinstance(name, str):
        return name
    for pat, dst in table:
        got = pat.fullmatch(name)
        if got is not None:
            return dst.replace("<n>", got.groupdict().get("n") or "").replace(
                "<c>", got.groupdict().get("c") or "")
    return name


def new_id(name: Any) -> Any:
    """Old wire name → its new id (`ghost.2` → `hands.2`, `hands` →
    `hands.layer`, `media.c` → `channel.c`, `output.2.readout` →
    `output.2.guide`); a name not in `NEW_IDS` is itself."""
    return _mapped(name, _NEW_MAP)


def old_id(name: Any) -> Any:
    """New id → the old wire name it was (`OLD_IDS`, `new_id`'s inverse);
    a name not in the table is itself."""
    return _mapped(name, _OLD_MAP)


def wired_hands_name(n: int) -> str:
    """The n-th hands geometry node of a wired frame: `hands`, `hands.2` …
    (its params `ghost[.n].*`, `param_prefix`)."""
    return "hands" if n == 1 else f"hands.{n}"


def wired_layer_name(n: int) -> str:
    """The n-th hands node's layer in a wired frame, and its render node:
    `hands.layer`, `hands.2.layer` …"""
    return f"{wired_hands_name(n)}.layer"


def wired_guide_name(n: int) -> str:
    """The n-th hands node's guide in a wired frame, and its render node:
    `hands.guide`, `hands.2.guide` …"""
    return f"{wired_hands_name(n)}.guide"


def hands_of(name: str) -> str:
    """The hands node a layer or a guide of a wired frame is of, by its
    name: `hands.2.layer` → `hands.2`, `hands.guide` → `hands` (plan 36
    T2: what it draws is the wire into its `hands` port; a load from
    before writes this one there, `graphmigrate.drawn_edges`)."""
    return name.rpartition(".")[0]


def param_prefix(name: str) -> str:
    """A wired frame's node id → its params' prefix (V2: params keep their
    ids): `hands.2` → `ghost.2` (its layer and guide too), `lookback` →
    `dream`, `channel.a` → `media.a`, `camera` → `eye`, an effect `acid.2`
    → `fx.acid.2`; any other node's prefix is its own id."""
    kind = "camera" if name == "camera" else wire_node_kind(name, wired=True)
    if kind in ("layer", "guide"):
        name, kind = hands_of(name), "hands"
    if kind == "effect":
        return f"fx.{name}"
    head = PARAM_PREFIX.get(kind)
    if head is None:
        return name
    rest = name.partition(".")[2]
    return f"{head}.{rest}" if rest else head


_HANDS_W = re.compile(rf"hands(?:\.{_INSTANCE})?")
_LAYER_W = re.compile(rf"hands(?:\.{_INSTANCE})?\.layer")
_GUIDE_W = re.compile(rf"hands(?:\.{_INSTANCE})?\.guide")
_CHANNEL = re.compile(rf"channel\.[{MEDIA_CHANNELS}]")
_COPY = re.compile(rf"copy(?:\.{_INSTANCE})?")


def _wired_kind(name: str) -> str | None:
    """`wire_node_kind(name, wired=True)`: a wired frame's kinds. `frame`
    and `fx` are named so `wire_error` can say they are gone; an old id
    (`new_id(name) != name`) and the cover are no node."""
    if name in ("scene", "shape", "backdrop", "pattern", "lookback", "dream", "frame", "fx",
                GROUND):
        return name
    if name in PINS or _SEGMENT_PIN.fullmatch(name):
        # plan 36 T2: the scene's mask and depth pins; plan 39 T4: a
        # segment's fg, bg and mask
        return name.rpartition(".")[2]
    for kind, pat in (("hands", _HANDS_W), ("layer", _LAYER_W), ("guide", _GUIDE_W),
                      ("output", _OUTPUT), ("composite", _COMPOSITE), ("channel", _CHANNEL),
                      ("switch", _SWITCH), ("delay", _DELAY), ("resize", _RESIZE),
                      # plan 36 T4: a look-back's echo pin is an echo; `echo.<k>`
                      # (plan 34's own node) only an old frame's, read to migrate
                      ("echo", _ECHO_PIN), ("echo", _ECHO), ("lookback", _LOOKBACK),
                      ("dream", _DREAM), ("copy", _COPY), ("matte", _MATTE),
                      ("cut", _CUT), ("segment", _SEGMENT)):
        if pat.fullmatch(name):
            return kind
    if new_id(name) != name or name == "cover":
        return None
    if _PLACE_EFFECT.fullmatch(name):
        return "effect"
    return None


@dataclass(frozen=True)
class _FrameAt:
    """One of the frame's own nodes declared by an entry (plan 35 F): one
    only (`n` is 1), named by its kind, `{"kind": <kind>}`."""

    KIND: ClassVar[str] = ""

    @property
    def n(self) -> int:
        return 1

    @property
    def name(self) -> str:
        return self.KIND

    def to_json(self) -> dict:
        return {"kind": self.KIND}


@dataclass(frozen=True)
class SceneAt(_FrameAt):
    """The scene: draws the geometry wired into `scene.geometry`."""

    KIND: ClassVar[str] = "scene"


@dataclass(frozen=True)
class ShapeAt(_FrameAt):
    """The polytope, its faces the pattern or what is wired into `faces`."""

    KIND: ClassVar[str] = "shape"


@dataclass(frozen=True)
class BackdropAt(_FrameAt):
    """The backdrop: `backdrop.scene` laid over `backdrop.image`."""

    KIND: ClassVar[str] = "backdrop"


@dataclass(frozen=True)
class PatternAt(_FrameAt):
    """The faces pattern (and its media layer, `pattern.media`)."""

    KIND: ClassVar[str] = "pattern"


@dataclass(frozen=True)
class LookbackAt(_FrameAt):
    """A look-back (was `history`, row 381; plan 36 T4, W4): it records
    what is wired into its `image` into a ring of its own and makes the
    trail — picture in, trail out, laid over nothing (D3: a composite lays
    it). `lookback` is declared by a wire naming it, as a frame kind;
    `lookback.<n>` by its entry, `{"kind": "lookback", "instance": n}`."""

    n: int = 1
    KIND: ClassVar[str] = "lookback"

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"lookback instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "lookback" if self.n == 1 else f"lookback.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "lookback"}
        if self.n != 1:
            d["instance"] = self.n
        return d


@dataclass(frozen=True)
class _HandsPictureAt:
    """A picture of the n-th hands node (plan 35 F, row 380): drawn from
    the hands node wired into its `hands` port (plan 36 T2; none, empty)."""

    n: int = 1
    KIND: ClassVar[str] = ""

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"{self.KIND} instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return f"{wired_hands_name(self.n)}.{self.KIND}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": self.KIND}
        if self.n != 1:
            d["instance"] = self.n
        return d


@dataclass(frozen=True)
class LayerAt(_HandsPictureAt):
    """The hands drawn alone (`hands.layer`, `hands.<n>.layer`), to lay
    over a picture or put through effects."""

    KIND: ClassVar[str] = "layer"


@dataclass(frozen=True)
class GuideAt(_HandsPictureAt):
    """The hands' labels and tethers (`hands.guide`, `hands.<n>.guide`),
    laid over last and never bent."""

    KIND: ClassVar[str] = "guide"


@dataclass(frozen=True)
class CopyAt:
    """A copy (plan 35 F, row 377): effect instance `of` drawn again on
    another picture, with its knobs and its clock — its own `image` and
    `aux` — `copy`, `copy.<n>`. What the per-pipeline run was, said as a
    node, only where one is wanted."""

    n: int
    of: str

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 1:
            raise ValueError(f"copy instance {self.n!r}: a whole number from 1")

    @property
    def name(self) -> str:
        return "copy" if self.n == 1 else f"copy.{self.n}"

    def to_json(self) -> dict:
        d: dict[str, Any] = {"kind": "copy", "of": self.of}
        if self.n != 1:
            d["instance"] = self.n
        return d


def _frame_entry(cls):
    def read(e: dict) -> _FrameAt:
        _entry_keys(e, cls.KIND, ())
        return cls()
    return read


def _picture_entry(cls):
    def read(e: dict) -> _HandsPictureAt:
        _entry_keys(e, cls.KIND, ("instance",))
        return cls(_instance(e))
    return read


def _copy_entry(e: dict) -> CopyAt:
    _entry_keys(e, "copy", ("of", "instance"))
    n = _instance(e)
    name = CopyAt(n, "").name
    if "of" not in e:
        raise GraphError(COPY_NO_OF.format(name=name))
    if not isinstance(e["of"], str):
        raise GraphError(COPY_BAD_OF.format(name=name, of=e["of"]))
    return CopyAt(n, e["of"])


for _cls in (SceneAt, ShapeAt, BackdropAt, PatternAt):
    NODE_KINDS[_cls.KIND] = _frame_entry(_cls)
for _cls in (LayerAt, GuideAt):
    NODE_KINDS[_cls.KIND] = _picture_entry(_cls)
NODE_KINDS["lookback"] = _history_entry
NODE_KINDS["copy"] = _copy_entry
del _cls

# plan 34 L: the node kinds a section declares by an entry, one per
# instance, before a wire may name one (as a composite and a switch).
# Plan 35 F: and a copy, which always needs its entry, and the frame's
# kinds — but a wire of a wired frame naming one of those declares it
DECLARED = ("composite", "switch", "delay", "resize", "echo", "dream", "copy", "matte",
            "cut", "segment", *FRAME_KINDS)


def d1_wires(effects) -> list[Wire]:
    """D1's placements (`EffectAt.after` / `into`) as the wires they are
    short for: `after X` is `X → E.image`, `into Y` is `E → Y.image`
    (`output.<n>`, `after` or `into`: its image port)."""
    out = []
    for e in effects:
        if e is None or e.where is None:
            continue
        key, where = e.where
        if key == "after" and not where.startswith("output."):
            out.append(Wire(where, f"{e.name}.image"))
        else:
            out.append(Wire(e.name, f"{where}.image"))
    return out


@dataclass
class _WireCtx:
    """What a wire is checked against: the layer's name, the hands nodes,
    the effect instances this build has (None: any well-formed name), the
    composites declared, D1's placed effects (name → (key, where))."""

    layer: str = "hands"
    ghosts: frozenset[str] = frozenset({"ghost"})
    effects: set[str] | frozenset[str] | None = None
    composites: frozenset[str] = frozenset()
    placed: dict[str, tuple[str, str]] = field(default_factory=dict)
    # plan 33 G: the switches declared, and every wire of the section (D1's
    # placements too) — what `fx.image`'s source is followed through. None:
    # the wires are not known, the run is not checked (a drag on the canvas)
    switches: frozenset[str] = frozenset()
    wires: tuple[Wire, ...] | None = None
    # plan 34 L: the delays, resizes and echoes declared (their names), and
    # whether the dream is
    delays: frozenset[str] = frozenset()
    resizes: frozenset[str] = frozenset()
    echoes: frozenset[str] = frozenset()
    dream: bool = False
    # plan 35 F: whether the section is a wired frame (its wires in the new
    # ids, `WIRED_TAKES`; `ghosts` then holds the hands nodes' new names,
    # `hands`, `hands.2` …), and the copies declared (their names)
    wired: bool = False
    copies: frozenset[str] = frozenset()
    # plan 36 T4: the look-backs declared (their names: `lookback` by a
    # wire, `lookback.<n>` by an entry), and whether the read is a
    # migration's of an old frame (`legacy`: `lookback.capture` and plan
    # 34's `echo.<k>` are read, to be rewritten — `graphmigrate.split_lookback`)
    lookbacks: frozenset[str] = frozenset({"lookback"})
    legacy: bool = False
    # plan 39 T2: the mattes declared (their names)
    mattes: frozenset[str] = frozenset()
    # plan 39 T3: the cuts declared (their names)
    cuts: frozenset[str] = frozenset()
    # plan 39 T4: the segments declared (their names)
    segments: frozenset[str] = frozenset()

    def declared(self, kind: str) -> frozenset[str]:
        """The names of kind `kind` (one of `DECLARED`) the section declares
        (a frame kind's: none here — a wire of a wired frame declares it)."""
        return {"composite": self.composites, "switch": self.switches, "delay": self.delays,
                "resize": self.resizes, "echo": self.echoes, "copy": self.copies,
                "dream": frozenset({"dream"}) if self.dream else frozenset(),
                "lookback": self.lookbacks, "matte": self.mattes,
                "cut": self.cuts, "segment": self.segments}.get(kind, frozenset())


FX_IMAGE_REFUSAL = ("fx.image takes the run from frame; to replace an output's picture "
                    "wire it into output.N.image")
# plan 34 L: `frame` exists only as the run's head (it is the history's
# picture as the pipeline starts its effects), so a wire out of it goes into
# the run's first effect or `fx.image`, nowhere else
FRAME_SOURCE_REFUSAL = ("frame is the run's head: it goes into the run's first effect or "
                        "fx.image — the picture before the effects is history, after them "
                        "the run's last effect")
# the words for a wired frame's loop (`loop_words`): which drawn wire it
# runs through, and the delay that makes it legal. (Plan 36 T2: plan 34's
# hidden edges, `FRAME_EDGES`, and the walk over them are gone — a loop is
# one over drawn wires, `wire_loops`; an old section's loop through the
# frame it migrates to is the migration's, `graphmigrate.wired_section`)
LOOP_FACES = ("that makes a loop through the faces ({path}): the faces are drawn inside "
              "the scene — wire it through a delay for last frame's picture")
LOOP_BACKDROP = ("that makes a loop through the backdrop ({path}): the backdrop lies under "
                 "the scene's picture — wire it through a delay for last frame's picture")
# a wired frame's words for any other loop (plan 34 T5, row 359): there is
# no frame to name, so they point at the delay that makes it legal
LOOP_PLAIN = "that makes a loop ({path}): wire it through a delay for last frame's picture"


def _run_from_frame(src: str, wires) -> bool:
    """Whether `src` is `frame`, or an effect whose `image` chain of effects
    leads back to `frame` (plan 33 G: what `fx.image` takes)."""
    seen: set[str] = set()
    while src != "frame":
        if wire_node_kind(src) != "effect" or src in seen:
            return False
        seen.add(src)
        into = [w.src for w in wires if w.dst == f"{src}.image"]
        if len(into) != 1:
            return False
        src = into[0]
    return True


def wire_error(w: Wire, ctx: _WireCtx | None = None) -> str | None:
    """Why wire `w` cannot be, in words — None when it can (plan 28 N4):
    a name that is no node, a port that does not exist, a port of another
    type, a geometry or mask wire (a hands node's place is its `into`),
    a layer or a hands node this graph lacks, an effect D1 already
    places. The canvas's drag says the same words. Plan 35 F: a wired
    frame's wire (`ctx.wired`) is checked by its own table (`_wired_error`)."""
    ctx = ctx if ctx is not None else _WireCtx()
    if ctx.wired:
        return _wired_error(w, ctx)
    src_kind = wire_node_kind(w.src)
    if src_kind is None:
        return f"no node {w.src!r}: a wire leaves {WIRE_FROM_WORDS}"
    if src_kind == "output":
        return f"{w.src} is an output: it makes nothing to wire on"
    if src_kind in NO_SOURCE:
        return f"{w.src} takes a picture and makes nothing to wire on"
    node, port = w.node, w.port
    kind = wire_node_kind(node)
    if kind is None or kind in ("ghost", "cover"):
        return f"no input {w.dst!r}: a wire goes into {WIRE_TO_WORDS}"
    takes = WIRE_TAKES[kind]
    if port not in takes:
        names = list(takes) if len(takes) < 4 else [next(iter(takes)), "…", [*takes][-1]]
        said = f"it takes {', '.join(names)}" if takes else "nothing is wired into it"
        return f"{node} has no port {port!r} ({said})"
    makes, want = WIRE_MAKES[src_kind], takes[port]
    if makes != want:
        return f"{w.src} makes {TYPE_WORDS[makes]}, {w.dst} takes {TYPE_WORDS[want]}"
    if want == GEOMETRY:
        return f"a hands node's place is its into ({w.src} into scene or layer), not a wire"
    if want == MASK:
        return "the cover is the history's own: no mask is wired"
    for name, k in ((w.src, src_kind), (node, kind)):
        if k == "effect" and ctx.effects is not None and name not in ctx.effects:
            return f"no {name} effect in this build"
        if k in DECLARED and k not in FRAME_KINDS and name not in ctx.declared(k):
            entry = (f'{{"kind": "echo", "index": {split_instance(name)[1]}}}' if k == "echo"
                     else f'{{"kind": "{k}"}}')
            return f"no {name} node in this graph (add one: {entry})"
    if kind == "fx" and ctx.wires is not None and not _run_from_frame(w.src, ctx.wires):
        return FX_IMAGE_REFUSAL
    # plan 34 L: `frame` feeds the run only
    if w.src == "frame" and w.dst != "fx.image" and not (kind == "effect" and port == "image"):
        return FRAME_SOURCE_REFUSAL
    if src_kind == "layer" and w.src != ctx.layer:
        return f"no {w.src} layer in this graph ({ctx.layer} makes the layer)"
    if w.src == node:
        return f"{node} into itself makes a loop"
    if kind == "output" and port == "readout" and src_kind != "layer":
        return f"{w.dst} takes a hands layer's guide ({ctx.layer})"
    if kind == "composite" and port == "over" and src_kind == "history":
        return _LAID_OVER.format(name="history")
    if kind == "output" and port == "hands" and src_kind == "history":
        return _LAID_OVER_OUTPUT.format(name="history")
    # (an aux wire places nothing: a placed effect takes one where it sits)
    for name, k, into in ((node, kind, port != AUX), (w.src, src_kind, False)):
        if k == "effect" and name in ctx.placed and (into or kind != "effect"):
            key, where = ctx.placed[name]
            return f"{name} sits {key} {where!r} already (its node says so): one place"
    return None


# plan 35 F: a wired frame's ports (the table of the global constraints):
# what each kind makes and takes. The shape and the hands make geometry,
# which goes into the scene alone (several wires, `MANY_PORTS`); the
# backdrop lays `scene` over `image`; a look-back records its `image`
# (plan 36 T4: and makes the trail, held back by `occluder`'s brightness and
# the `cover` mask), the dream dreams its `image`; a
# copy is an effect's; an output and All outputs take a picture, the hands
# over it and the guide over all; `ground` makes nothing, as a picture
WIRED_MAKES = {"scene": IMAGE, "shape": GEOMETRY, "hands": GEOMETRY, "layer": IMAGE,
               "guide": IMAGE, "lookback": IMAGE, "channel": IMAGE, "backdrop": IMAGE,
               "copy": IMAGE, "output": None, GROUND: IMAGE, "effect": IMAGE,
               "composite": IMAGE, "pattern": IMAGE, "switch": IMAGE, "delay": IMAGE,
               "resize": IMAGE, "echo": IMAGE, "dream": IMAGE,
               # plan 36 T2: the scene's pins (`PINS`)
               "cover": MASK, DEPTH_PORT: IMAGE,
               # plan 39 T2: a matte makes a mask of its picture; T3: a cut,
               # its picture cut by a mask; T4: a segment, nothing of its own
               # — its foreground, background and matte are its pins
               "matte": MASK, "cut": IMAGE, "segment": None, **SEGMENT_PINS}
# plan 36 T2 (W2): every edge a port — a layer's and a guide's hands, the
# look-back's cover mask, a composite's and an output's depth
WIRED_TAKES: dict[str, dict[str, str]] = {
    "scene": {"geometry": GEOMETRY}, "shape": {"faces": IMAGE},
    "hands": {}, "layer": {"hands": GEOMETRY}, "guide": {"hands": GEOMETRY}, "channel": {},
    GROUND: {}, "cover": {}, DEPTH_PORT: {},
    "lookback": {"image": IMAGE, "occluder": IMAGE, "cover": MASK},
    "dream": {"image": IMAGE},
    "backdrop": {"image": IMAGE, "scene": IMAGE},
    "copy": {"image": IMAGE, "aux": IMAGE},
    "output": {"image": IMAGE, "hands": IMAGE, "guide": IMAGE, DEPTH_PORT: IMAGE},
    "composite": {**WIRE_TAKES["composite"], DEPTH_PORT: IMAGE},
    **{k: WIRE_TAKES[k] for k in ("effect", "pattern", "switch", "delay",
                                  "resize", "echo")},
    "matte": {"image": IMAGE},
    # plan 39 T3 (W3): a cut takes the picture it cuts and the mask it cuts by
    "cut": {"image": IMAGE, "mask": MASK},
    # plan 39 T4 (W4): a segment the picture it cuts (its pins take nothing)
    "segment": {"image": IMAGE}, **{k: {} for k in SEGMENT_PINS},
}
WIRED_TO_WORDS = ("output.1 …, output.all (image, hands, guide, depth), scene.geometry, "
                  "shape.faces, backdrop.image / scene, lookback.image / occluder / cover "
                  "(lookback.2 …), dream.image, hands.layer.hands …, hands.guide.hands …, "
                  "pattern.media, an effect's or a copy's image or aux, a composite's under "
                  "/ over / depth, a switch's in1 … in8, a delay's, a resize's, a "
                  "matte's or a segment's image, or a cut's image / mask")
WIRED_FROM_WORDS = ("scene, scene.cover, scene.depth, shape, hands …, hands.layer …, "
                    "hands.guide …, lookback …, lookback.echo.1 …, dream, backdrop, pattern, "
                    "an effect, a copy, a composite, a switch, a delay, a resize, a matte, "
                    "a cut, segment.fg / .bg / .mask, a channel (channel.a …) or ground")
# plan 39 T2 (W1, decision 2): a picture into a mask port is refused with the
# converter's name; the promotion runs the other way only
PICTURE_INTO_MASK = "{src} makes a picture, {dst} takes a mask — put a matte between"
# plan 36 T4 (W4): the words for what the split took away
CAPTURE_IS_IMAGE = ("{node}.capture is gone (plan 36): a look-back records what is wired "
                    "into {node}.image, and a composite lays its trail")
ECHO_IS_A_PIN = ("{name} is the old name (plan 36): a look-back's frames are its own "
                 "outputs — lookback.echo.{k}")
ONE_DREAM = ("{name}: one live dream at a time (one worker, one GPU job) — wire dream, "
             "or turn it off with dream.on")
ECHO_RANGE = "{name}: a look-back holds {most} frames (echo.1 the newest … echo.{most})"
# the look-back paints into what reads it (plan 28): the words for a wire
# laying it over, either frame's
_LAID_OVER = ("the {name} paints into what reads it, so it is not laid over: "
              "wire it under, or an effect after it over")
_LAID_OVER_OUTPUT = ("the {name} paints into what reads it, so it is not laid over: "
                     "wire it into the output's image, or an effect after it over")


def _wired_error(w: Wire, ctx: _WireCtx) -> str | None:
    """`wire_error` in a wired frame (plan 35 F): `frame` and `fx` are gone,
    an old id is said by its new one, geometry goes into the scene alone,
    `ground` into an output's port alone, an output's guide takes a hands
    layer or guide; the rest — the types, the declared nodes, a loop into
    itself, the look-back laid over, D1's one place — as plan 34 says."""
    ends = (w.src, w.node)
    for name in ends:
        if name in ("frame", "fx"):
            return GONE_IN_A_WIRED_FRAME.format(name=name)
    for name in ends:
        if wire_node_kind(name, wired=True) is None and new_id(name) != name:
            return OLD_ID_IN_A_WIRED_FRAME.format(old=name, new=new_id(name))
    src_kind = wire_node_kind(w.src, wired=True)
    if src_kind is None:
        return f"no node {w.src!r}: a wire leaves {WIRED_FROM_WORDS}"
    if src_kind == "output":
        return f"{w.src} is an output: it makes nothing to wire on"
    if src_kind == "segment":
        return SEGMENT_IS_ITS_PINS.format(name=w.src)
    node, port = w.node, w.port
    kind = wire_node_kind(node, wired=True)
    if kind is None:
        return f"no input {w.dst!r}: a wire goes into {WIRED_TO_WORDS}"
    if kind == "output" and new_id(w.dst) != w.dst:
        return OLD_ID_IN_A_WIRED_FRAME.format(old=w.dst, new=new_id(w.dst))
    takes = WIRED_TAKES[kind]
    if kind == "lookback" and port == "capture":
        # plan 36 T4: the look-back records its `image` — an old frame's
        # capture wire is read only by the migration that rewrites it
        if not ctx.legacy:
            return CAPTURE_IS_IMAGE.format(node=node)
        takes = {**takes, "capture": IMAGE}
    for name, k in ((w.src, src_kind), (node, kind)):
        if k == "echo" and echo_of(name) is None and not ctx.legacy:
            return ECHO_IS_A_PIN.format(name=name, k=split_instance(name)[1])
        if k == "echo" and echo_of(name) is not None and echo_of(name)[1] > MAX_ECHOES:
            return ECHO_RANGE.format(name=name, most=MAX_ECHOES)
        if k == "dream" and name != "dream":
            return ONE_DREAM.format(name=name)
    if port not in takes:
        names = list(takes) if len(takes) < 4 else [next(iter(takes)), "…", [*takes][-1]]
        said = f"it takes {', '.join(names)}" if takes else "nothing is wired into it"
        return f"{node} has no port {port!r} ({said})"
    if src_kind == GROUND and kind != "output":
        return GROUND_ONLY_INTO_OUTPUTS
    makes, want = WIRED_MAKES[src_kind], takes[port]
    # plan 36 T2: a pin goes where its kind is taken, a depth port takes the
    # scene's depth alone, a layer's or a guide's hands a hands node
    if PINS.get(w.src) == "scene" and not (src_kind == "cover" and port == "cover") and not (
            src_kind == DEPTH_PORT and port == DEPTH_PORT):
        return f"{w.src} is {PIN_WORDS[w.src]}"
    if (port == DEPTH_PORT and kind in ("composite", "output")
            and src_kind not in (DEPTH_PORT, GROUND)):
        return DEPTH_TAKES.format(dst=w.dst)
    if kind in ("layer", "guide") and port == "hands" and src_kind != "hands":
        return LAYER_TAKES_HANDS.format(dst=w.dst)
    if makes == GEOMETRY and want != GEOMETRY and kind != "output":
        return GEOMETRY_INTO_SCENE.format(src=w.src)
    if makes == IMAGE and want == MASK:
        return PICTURE_INTO_MASK.format(src=w.src, dst=w.dst)
    # plan 39 T2 (W1): a mask goes where a picture is taken — it reads as one
    if makes != want and not (makes == MASK and want == IMAGE):
        return f"{w.src} makes {TYPE_WORDS[makes]}, {w.dst} takes {TYPE_WORDS[want]}"
    for name, k in ((w.src, src_kind), (node, kind)):
        if k == "effect" and ctx.effects is not None and name not in ctx.effects:
            return f"no {name} effect in this build"
        if k in ("hands", "layer", "guide"):
            hands = name if k == "hands" else hands_of(name)
            if hands != "hands" and hands not in ctx.ghosts:   # (hands 1 is always there)
                n = split_instance(hands)[1]
                return (f"no {hands} node in this graph (add one: "
                        f'{{"kind": "hands", "instance": {n}}})')
        if k == "echo" and echo_of(name) is not None:
            # plan 36 T4: an echo pin is its look-back's: that one declared
            name, k = echo_of(name)[0], "lookback"
        if k in SEGMENT_PINS and segment_pin(name) is not None:
            # plan 39 T4: a segment's pin is its segment's: that one declared
            name, k = segment_pin(name)[0], "segment"
        if k == "lookback" and name not in ctx.declared("lookback"):
            n = split_instance(name)[1]
            return (f"no {name} node in this graph (add one: "
                    f'{{"kind": "lookback", "instance": {n}}})')
        if k in DECLARED and k not in FRAME_KINDS and name not in ctx.declared(k):
            entry = (f'{{"kind": "echo", "index": {split_instance(name)[1]}}}' if k == "echo"
                     else f'{{"kind": "{k}"}}')
            return f"no {name} node in this graph (add one: {entry})"
    if w.src == node:
        return f"{node} into itself makes a loop"
    if kind == "output" and port == "guide" and src_kind not in ("layer", "guide", GROUND):
        return f"{w.dst} takes a hands layer or a hands guide (hands.layer, hands.guide …)"
    # (plan 36 T4: the trail is a picture with alpha, laid on by a composite
    # like any other — the old "not laid over" refusal is gone)
    for name, k, into in ((node, kind, port != AUX), (w.src, src_kind, False)):
        if k == "effect" and name in ctx.placed and (into or kind != "effect"):
            key, where = ctx.placed[name]
            return f"{name} sits {key} {where!r} already (its node says so): one place"
    return None


def _later(w: Wire, wired: bool, legacy: bool = False) -> bool:
    """Whether wire `w` is read only after this frame (no dependency, never
    on a loop): one into a delay (plan 34 L: its picture is last frame's)
    or (plan 35 F) into `lookback.capture`, which the ring records for the
    frames after, once every end has run — plan 36 T4: into a look-back's
    `image`, what it records so (its trail is the frames before this one);
    but in an old frame (`legacy`, the migration's) `lookback.image` was
    the picture the trail was laid on, read this frame."""
    kind = wire_node_kind(w.node, wired=wired)
    return (kind == "delay"
            or (wired and (w.dst == "lookback.capture"
                           or (not legacy and kind == "lookback" and w.port == "image"))))


def _legacy(wires) -> bool:
    """Whether wired `wires` are an old frame's (plan 36 T4): its look-back
    records `lookback.capture`."""
    return any(w is not None and w.dst == "lookback.capture" for w in wires)


def wire_loops(wires: list[Wire], wired: bool = False) -> dict[Wire, str]:
    """The wires on a loop — a node reading, through wires, its own
    picture — each with the loop in words (`acid.2 → palette → acid.2`).
    A wire makes its node depend on its source — but (plan 34 L) a wire
    into a delay: a delay's picture is last frame's, so it depends on
    nothing this frame, and such a wire is never on a loop. Plan 35 F:
    `wired`, a wired frame's wires (`_later`: the capture's too). Plan 36
    T2: over drawn wires only — a pin (`scene.cover`) is its node, so a
    loop through it runs through the scene."""
    deps: dict[str, set[str]] = {}
    legacy = wired and _legacy(wires)
    for w in wires:
        _depend(deps, w, wired, legacy)
    out: dict[Wire, str] = {}
    for w in wires:
        if _later(w, wired, legacy):
            continue
        path = _loop_path(deps, w)
        if path is not None:
            out[w] = " → ".join(path)
    return out


def _depend(deps: dict[str, set[str]], w: Wire, wired: bool, legacy: bool = False) -> None:
    """Wire `w`'s dependency (`wire_loops`) into `deps`: its node reads its
    source, a pin its node — none for a wire read after the frame."""
    if not _later(w, wired, legacy):
        deps.setdefault(w.node, set()).add(w.src)
        if wired and pin_node(w.src) is not None:
            deps.setdefault(w.src, set()).add(pin_node(w.src))


def loop_closers(stand: list[Wire], wires: list[Wire | None]) -> dict[int, str]:
    """Plan 36 T3: which of a wired frame's `wires`, read in order over the
    wires that `stand` (and the earlier ones of `wires` kept), close a loop
    — index into `wires` → why, in `loop_words`. A wire that closes one is
    not read on: those after it are read without it. None in `wires` (an
    entry that is no wire) is passed over. The one-way migration's question
    of an old section's own wires against the frame written for it
    (`graphmigrate.wired_section`)."""
    deps: dict[str, set[str]] = {}
    legacy = _legacy([*stand, *wires])        # (plan 36 T4: an old frame's, before the split)
    for w in stand:
        _depend(deps, w, True, legacy)
    out: dict[int, str] = {}
    for k, w in enumerate(wires):
        if w is None or _later(w, True, legacy):
            continue
        path = _loop_path(deps, w)
        if path is not None:
            out[k] = loop_words(" → ".join(path), _hops(path))
            continue
        _depend(deps, w, True, legacy)
    return out


def _loop_path(deps: dict[str, set[str]], w: Wire) -> list[str] | None:
    """The loop wire `w` closes over `deps` (node → what it reads), as the
    names from `w.node` back to it, each read by the next (`[shape, scene,
    shape]`), or None when `w.node` is not reached from `w.src`."""
    parent: dict[str, str | None] = {w.src: None}
    todo = [w.src]
    while todo and w.node not in parent:
        cur = todo.pop()
        for d in sorted(deps.get(cur, ())):
            if d not in parent:
                parent[d] = cur
                todo.append(d)
    if w.node not in parent:
        return None
    path: list[str] = []
    cur: str | None = w.node             # w.node … back to w.src, each read by the next
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return [*path, w.node]


def _hops(path: list[str]) -> set[tuple[str, str]]:
    """A loop's (reader, read) edges, its names each read by the next."""
    return {(path[i + 1], path[i]) for i in range(len(path) - 1)}


def loop_words(path: str, hops: set[tuple[str, str]]) -> str:
    """The refusal for a wired frame's loop `path` (`shape → scene →
    shape`) whose (reader, read) edges are `hops` (plan 35 F): through the
    faces when it runs through a wire into `scene.geometry` (the scene's
    one port), through the backdrop when through `backdrop.scene` or the
    look-back over the backdrop, else plain (`LOOP_PLAIN`)."""
    if any(r == "scene" for r, _ in hops):
        return LOOP_FACES.format(path=path)
    if ("lookback", "backdrop") in hops or ("backdrop", "scene") in hops:
        return LOOP_BACKDROP.format(path=path)
    return LOOP_PLAIN.format(path=path)


def _read_wires(raw: Any, ctx: _WireCtx, d1: list[Wire]) -> tuple[tuple[Wire, ...], list[str]]:
    """The section's `wires` → (the wires that stand, the notes for the
    ones refused, each `wire <from> → <to> — why`). Anything that is not
    a list of `{"from", "to"}` strings is unreadable (`GraphError`)."""
    if not isinstance(raw, list):
        raise GraphError("wires is not a list")
    wires: list[Wire] = []
    for e in raw:
        if (not isinstance(e, dict) or set(e) != set(WIRE_KEYS)
                or not all(isinstance(e[k], str) for k in WIRE_KEYS)):
            raise GraphError(f'a wire is {{"from": a node, "to": "node.port"}}, not {e!r}'[:140])
        try:
            w = Wire(e["from"], e["to"])
        except ValueError as err:
            raise GraphError(str(err)) from err
        if w in wires:
            raise GraphError(f"the wire {w} twice")
        wires.append(w)
    notes: list[str] = []
    ok: list[Wire] = []
    ctx.wires = (*d1, *wires)          # plan 33 G: what `fx.image`'s run is followed through
    for w in wires:
        why = wire_error(w, ctx)
        if why is not None:
            notes.append(f"wire {w} — {why}")
        else:
            ok.append(w)
    # two wires into one port (D1's placements count): each refused, the
    # port keeps its default (or D1's placement). Plan 35 F: but in a wired
    # frame the scene's geometry takes several, drawn in section order
    # Plan 35 B: and there D1's `into` is a fold of what the port reads
    # (the migration's `placed_wires`), not a second wire into it — so an
    # output's own picture (a through's copies) and the look-back's take
    # their wire with an effect placed into them
    into: dict[str, list[Wire]] = {}
    folds = {w for w in d1 if (w.src in ctx.placed and ctx.placed[w.src][0] == "into")
             or w.dst.startswith("output.")} if ctx.wired else set()
    for w in (*(w for w in d1 if w not in folds), *ok):
        into.setdefault(w.dst, []).append(w)
    for dst, ws in into.items():
        if len(ws) > 1 and not (ctx.wired and dst in MANY_PORTS):
            srcs = " and ".join(x.src for x in ws)
            for w in ws:
                if w in ok:
                    ok.remove(w)
                    notes.append(f"wire {w} — {dst} takes one wire, and {len(ws)} go into "
                                 f"it ({srcs}): it keeps its default")
    # an effect no wire feeds sits into one port (D1's `into`); to feed
    # more, wire its input (plan 35 F: a wired frame's names in its kinds)
    def kind(name: str) -> str | None:
        return wire_node_kind(name, wired=ctx.wired)

    fed = {w.node for w in (*d1, *ok) if kind(w.node) == "effect" and w.port != AUX}
    outs: dict[str, list[Wire]] = {}
    for w in ok:
        if kind(w.src) == "effect" and kind(w.node) != "effect":
            outs.setdefault(w.src, []).append(w)
    # (R15, plan 35 T5: not in a wired frame — there no wire is short for
    # D1's `into`, and an effect with no input reads nothing: unreached,
    # drawn faint, its outs kept)
    for e, ws in outs.items():
        if e not in fed and len(ws) > 1 and not ctx.wired:
            for w in ws[1:]:
                ok.remove(w)
                notes.append(f"wire {w} — {e} has no wire in, so it sits into one port "
                             f"({ws[0].dst}): wire its input to feed more")
    loops = wire_loops([*d1, *ok], wired=ctx.wired)
    for w in list(ok):
        if w in loops:
            ok.remove(w)
            # plan 35 F: a wired frame's wires say the faces and the backdrop
            # themselves, so their loops keep plan 34's words (`loop_words`)
            why = (loop_words(loops[w], _hops(loops[w].split(" → ")))
                   if ctx.wired else f"that makes a loop ({loops[w]})")
            notes.append(f"wire {w} — {why}")
    return tuple(w for w in wires if w in ok), notes


def split_wires(wires, placed=()) -> tuple[tuple[EffectAt, ...], tuple[Wire, ...]]:
    """The wire list as the default graph builds it: (the effects the
    wires place as D1 would — an effect fed by one wire and wired into
    nothing sits `after` its source; one wired into one output's or the
    history's `image` port and fed by none sits `into` it — and the wires
    left, each built as an edge: into an output's port, the history's
    image, a composite's, or an effect both fed and wired on). `placed`:
    D1's own placements (an effect they place is not placed again).
    Pre-33 sections only (the owner, 2026-10-24): one with a `frame` run
    is read with no shortening (`GraphSpec.wiring`)."""
    own = {e.name for e in placed}
    # plan 32 R: an aux wire is always an edge (`is_aux`), never a placement
    aux = tuple(w for w in wires if is_aux(w))
    wires = [w for w in wires if not is_aux(w)]
    is_fx = {w.node: True for w in wires if wire_node_kind(w.node) == "effect"}
    ins: dict[str, Wire] = {w.node: w for w in wires if is_fx.get(w.node)}
    outs: dict[str, list[Wire]] = {}
    for w in wires:
        if wire_node_kind(w.src) == "effect" and not is_fx.get(w.node):
            outs.setdefault(w.src, []).append(w)
    synth: list[EffectAt] = []
    edges: set[Wire] = set()
    for name in sorted(set(ins) | set(outs)):
        i, o = ins.get(name), outs.get(name, [])
        if name in own:                      # (refused at read)
            continue
        file, n = split_instance(name)
        # plan 33 G: a wire is shortened only from a place D1 has a word
        # for; from a channel, `frame`, a switch … it is a branch, an edge
        if (i is not None and not o and wire_node_kind(i.src) != "composite"
                and placement_error(name, "after", i.src) is None):
            synth.append(EffectAt(file, n, after=i.src))
        elif (i is None and len(o) == 1 and o[0].port == "image"
              and (o[0].node == "history" or o[0].node.startswith("output."))):
            synth.append(EffectAt(file, n, into=o[0].node))
        else:
            edges.update([*([i] if i is not None else []), *o])
    for w in wires:
        if wire_node_kind(w.src) != "effect" and not is_fx.get(w.node):
            edges.add(w)
    return tuple(synth), tuple(w for w in wires if w in edges) + aux


@dataclass(frozen=True)
class GraphSpec:
    """A preset's `graph` section, read (plan 26 A4): the node instances
    and their wiring, in data — never anything that is already a param
    (an effect's on, mix and order, `ghost.alpha`, `dream.*` are in
    `values` or the show). What the default graph is built from besides
    the outputs' switches (`wiring`), and the effect instances the chain
    holds (`effect_counts`). A kind added by a later WP rides in `others`.

    The JSON (`to_json`, plain and git-diffable)::

        "graph": {"nodes": [
            {"kind": "hands", "into": "scene", "draw": "lines"},
            {"kind": "hands", "instance": 2, "into": "layer", "laid": "depth"},
            {"kind": "effect", "file": "acid", "instance": 2},
            {"kind": "history", "holds": "scene+hands"}]}

    A node left out is the default one: hands 1 a solid layer laid over,
    the history of the scene, every effect file once. `laid` (how the
    hands' layer is laid on: over, add, depth) belongs on the hands node
    that makes the layer.

    Plan 30 D1: an effect node may say where it sits — `"after":
    "hands"` (on the hands' layer, every consumer of it reading the
    effect), `"into": "output.2"` (on that output's picture alone) — and
    then instance 1 may be named too (`{"kind": "effect", "file":
    "palette", "after": "hands"}`: the palette itself, out of the chain).
    `notes`: the placements read but refused (a name out of the
    vocabulary, both keys, a loop), each at the default placement — the
    preset strip says them; the rest of the graph stands."""

    hands: tuple[HandsAt, ...] = ()
    laid: str = "over"
    history: HistoryAt = HistoryAt()
    effects: tuple[EffectAt, ...] = ()
    others: tuple[tuple[str, Any], ...] = ()      # (kind, what its reader returned)
    notes: tuple[str, ...] = field(default=(), compare=False)
    wires: tuple[Wire, ...] = ()                  # plan 28 N4: the wire list, as read
    # plan 35 F: whether the section says `"frame": "wired"` — every node of
    # the frame in its wires or entries, in the new ids (V2)
    wired: bool = False
    # plan 35 T3 (row 380): the hands entry `laid` sits on in a wired frame,
    # where any hands node may have a layer (1 outside one: the layer node's)
    laid_on: int = 1

    @property
    def frame_nodes(self) -> tuple:
        """The frame kinds' entries (plan 35 F: `SceneAt`, `LookbackAt`,
        `LayerAt` …, `FRAME_KINDS`), as read, in section order."""
        return tuple(got for k, got in self.others if k in FRAME_KINDS)

    @property
    def copies(self) -> tuple[CopyAt, ...]:
        """The copies the section adds (plan 35 F), by instance."""
        return self._of("copy")

    def wiring(self) -> Wiring:
        """The default graph's wiring this graph says. Plan 28 N4: the
        wires D1 would write short are placements (`split_wires`), after
        D1's own; the rest are the wiring's `wires`. Plan 33 (the owner,
        2026-10-24): only in a section with no run — one with a run
        (a wire from `frame` or into `fx.image`) shortens nothing, so its placements
        are D1's own entries and every other wire is an edge."""
        first = next((h for h in self.hands if h.n == 1), HandsAt())
        placed = tuple(e for e in self.effects if e.placed)
        if self.wired:
            # plan 35 F: a wired frame's wires are every wire, as they stand
            # (no run, no shortening, no backdrop channel); T2 builds them
            return Wiring(draw=first.draw, extra=tuple(h for h in self.hands if h.n != 1),
                          blend=self.laid, placed=placed, wires=self.wires,
                          composites=self.composites(), wired=True, copies=self.copies,
                          laid_on=self.laid_on)
        run, wires = None, self.wires
        if any(w.src == "frame" or w.dst == "fx.image" for w in wires):
            # plan 33 R: the section says the run (every preset loaded on
            # this build does, `graphmigrate`): its wires are the run, not
            # edges. The faces', the pattern's and the backdrop's wires are
            # edges like any other (T4), and so are a switch's (T5)
            run = run_of(self)
            wires = tuple(w for w in wires if w not in _run_wires(run))
        # plan 33 R: a channel straight into the backdrop is the plan 32
        # backdrop, node for node (`MediaNode(alpha_of="backdrop_alpha")`)
        back = next((w for w in wires if w.dst == "backdrop.image"
                     and wire_node_kind(w.src) == "media"), None)
        if back is not None:
            wires = tuple(w for w in wires if w != back)
        if run is None:
            synth, edges = split_wires(wires, placed)
        else:
            # the owner, 2026-10-24: a section with a run shortens no wire
            # to D1. A glimmer wired only `zoomblur → glimmer.image` drew
            # on zoomblur's picture (`after zoomblur`) while GRAPH and the
            # FX page, reading the wires, said it reaches nothing. Here a
            # wire is a wire: an effect with nothing out of it is an
            # unreached branch, never run; D1's own entries still place.
            # A pre-33 section (no run) keeps the shortening, and its
            # migration writes each as the D1 entry it stood for
            # (`graphmigrate.migrate`), so an old preset draws as it did
            synth, edges = (), wires
            edges = _reached_edges(edges, run, placed)
        return Wiring(hands=first.into, blend=self.laid, history=self.history.holds,
                      draw=first.draw, extra=tuple(h for h in self.hands if h.n != 1),
                      placed=placed + synth, wires=edges, composites=self.composites(),
                      backdrop=back.src.partition(".")[2] if back is not None else "",
                      run=run)

    def composites(self) -> tuple[CompositeAt, ...]:
        """The composite nodes the section adds (plan 28 N4), by instance."""
        return tuple(sorted((got for kind, got in self.others if kind == "composite"),
                            key=lambda c: c.n))

    @property
    def switches(self) -> tuple[SwitchAt, ...]:
        """The switch nodes the section adds (plan 33 S), by instance."""
        return tuple(sorted((got for kind, got in self.others if kind == "switch"),
                            key=lambda s: s.n))

    def _of(self, kind: str) -> tuple:
        return tuple(sorted((got for k, got in self.others if k == kind), key=lambda o: o.n))

    @property
    def delays(self) -> tuple[DelayAt, ...]:
        """The delay nodes the section adds (plan 34 L), by instance."""
        return self._of("delay")

    @property
    def resizes(self) -> tuple[ResizeAt, ...]:
        """The resize nodes the section adds (plan 34 L), by instance."""
        return self._of("resize")

    @property
    def mattes(self) -> tuple[MatteAt, ...]:
        """The matte nodes the section adds (plan 39 T2), by instance."""
        return self._of("matte")

    @property
    def cuts(self) -> tuple[CutAt, ...]:
        """The cut nodes the section adds (plan 39 T3), by instance."""
        return self._of("cut")

    @property
    def segments(self) -> tuple[SegmentAt, ...]:
        """The segment nodes the section adds (plan 39 T4), by instance."""
        return self._of("segment")

    @property
    def echoes(self) -> tuple[EchoAt, ...]:
        """The look-back frames the section reads (plan 34 L), by index."""
        return self._of("echo")

    @property
    def dream(self) -> DreamAt | None:
        """The dream's node, when the section declares it (plan 34 L; plan
        36 T4: the one live dream, `dream`)."""
        return next((got for k, got in self.others if k == "dream" and got.n == 1), None)

    @property
    def lookbacks(self) -> tuple[LookbackAt, ...]:
        """The look-backs the section declares by an entry (plan 36 T4:
        `lookback` may be, `lookback.<n>` must be), by instance."""
        return self._of("lookback")

    def all_wires(self) -> list[Wire]:
        """Every wire this graph says (plan 28 N4): D1's placements as the
        wires they are short for (`d1_wires`), then the wire list."""
        return [*d1_wires(self.effects), *self.wires]

    def effect_counts(self) -> dict[str, int]:
        """Effect file → how many instances the chain holds (only files
        with more than one; the highest instance named counts)."""
        out: dict[str, int] = {}
        for e in self.effects:
            out[e.file] = max(out.get(e.file, 1), e.n)
        return {f: n for f, n in out.items() if n > 1}

    def effect_names(self) -> frozenset[str]:
        """Plan 36 T3 (W3): every effect instance the section names — by an
        entry, a wire's end, a copy's `of` — the ones that exist while it is
        landed (`FxState.hold`): instance 1 of a file too, only when named."""
        out = {e.name for e in self.effects} | {c.of for c in self.copies}
        out |= {name for w in self.all_wires() for name in (w.src, w.node)
                if wire_node_kind(name, wired=self.wired) == "effect"}
        return frozenset(out)

    def to_json(self) -> dict:
        """The section as a preset writes it: every node that is not the
        default, in a fixed order (hands by instance, effects by file and
        instance, the history, then later kinds' entries as read).

        Plan 36 T3 (W3): a wired frame writes every hands entry — hands 1,
        which is always there, and each one declared — and `laid` on the
        one whose layer it is, `over` too: nothing of it is left for a
        default to say."""
        nodes: list[dict] = []
        layer = self.laid_on if self.wired else self.wiring().layer_node().n
        hands = {h.n: h for h in self.hands}
        if layer not in hands and (self.laid != "over" or self.wired):
            hands[layer] = HandsAt(layer)
        if self.wired:
            hands.setdefault(1, HandsAt(1))
        for n in sorted(hands):
            h = hands[n]
            d: dict[str, Any] = {"kind": "hands"}
            if h.n != 1:
                d["instance"] = h.n
            if h.into != "layer":
                d["into"] = h.into
            if h.draw != "solid":
                d["draw"] = h.draw
            if h.n == layer and (self.laid != "over" or self.wired):
                d["laid"] = self.laid
            if len(d) > 1 or self.wired:
                nodes.append(d)
        for e in sorted(self.effects, key=lambda e: (e.file, e.n)):
            d = {"kind": "effect", "file": e.file}
            if e.n != 1:                       # instance 1: no instance key (D1 placed, or R21 kept unwired)
                d["instance"] = e.n
            if e.where is not None:
                d[e.where[0]] = e.where[1]
            nodes.append(d)
        if self.history.holds != "scene":
            nodes.append({"kind": "history", "holds": self.history.holds})
        for kind, got in self.others:
            to = getattr(got, "to_json", None)
            nodes.append(to() if to is not None else {"kind": kind, **dict(got)})
        # plan 35 F: a wired frame says so first
        head = {FRAME_KEY: WIRED_FRAME} if self.wired else {}
        if not self.wires:                     # N4: a graph with no wires is D1's, short
            return {**head, "nodes": nodes}
        return {**head, "nodes": nodes, "wires": [w.to_json() for w in self.wires]}


def read_graph(section: Any, effects: set[str] | frozenset[str] | None = None, *,
               placements: bool = False) -> GraphSpec:
    """A preset's `graph` section → its `GraphSpec`; raises `GraphError`
    (the reason in words) for anything this build cannot read — a kind
    not in `NODE_KINDS`, a key a node does not take, a value out of its
    choices, two nodes of one instance, two hands layers, `laid` on a
    hands node that makes no layer. The caller notes it; since plan 36 the
    section is not read (black), nothing filled in.

    Plan 30 D1: a placement this build cannot honour is not a reason to
    drop the graph — both keys at once, a name that is not a string or
    not in the placeable vocabulary (`placement_error`; `effects`: the
    effect files on disk, so `after: "teapot"` is refused — None takes
    any well-formed effect name), or a loop of placed effects
    (`placement_loops`) — the effect takes the default placement (plan
    33: where its wires put it, none for an instance on no wire) and the
    reason rides in `GraphSpec.notes`.

    Plan 36 T3 (W3): a wired frame reads no placement — an entry's `after`
    / `into` is dropped with a note (`PLACEMENT_IS_A_WIRE`), the effect
    where its wires put it — but with `placements`, which only the
    one-way migration passes for a `/6` frame it is about to rewrite as
    wires (`graphmigrate.placed_wires`). An old (unwired) section is read
    as it always was: it is only ever a migration's input."""
    if not isinstance(section, dict):
        raise GraphError(f"not an object but {type(section).__name__}")
    extra = sorted(set(section) - {"nodes", "wires", FRAME_KEY})
    if extra:
        raise GraphError(f"no key {', '.join(map(repr, extra))} (it takes nodes, wires and "
                         "frame)")
    # plan 35 F: the marker — a wired frame, its one value
    if FRAME_KEY in section and section[FRAME_KEY] != WIRED_FRAME:
        raise GraphError(FRAME_VALUE.format(value=section[FRAME_KEY]))
    wired = FRAME_KEY in section
    entries = section.get("nodes", [])
    if not isinstance(entries, list):
        raise GraphError("nodes is not a list")
    hands: dict[int, HandsAt] = {}
    laid: dict[int, str] = {}
    found: dict[tuple[str, int], EffectAt | None] = {}
    history: HistoryAt | None = None
    others: list[tuple[str, Any]] = []
    notes: list[str] = []
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("kind"), str):
            raise GraphError(f"a node that names no kind: {e!r}"[:120])
        kind = e["kind"]
        reader = NODE_KINDS.get(kind)
        if reader is None:
            raise GraphError(f"unknown node kind {kind!r} (this build knows "
                             f"{', '.join(sorted(NODE_KINDS))})")
        if not wired and (kind in FRAME_KINDS or kind == "copy"):
            raise GraphError(FRAME_KIND_UNWIRED.format(kind=kind))
        try:
            # plan 35 F: a wired frame's hands take no `into`, and `history`
            # is its old id
            got = reader(e, wired=wired) if kind in ("hands", "history") else reader(e)
        except GraphError:
            raise
        except (ValueError, TypeError) as err:
            raise GraphError(str(err)) from err
        if kind == "hands":
            h, how = got
            if h.n in hands:
                raise GraphError(f"two hands nodes of instance {h.n}")
            hands[h.n] = h
            if how is not None:
                laid[h.n] = how
        elif kind == "effect":
            at, why = got
            key = (e["file"], _instance(e))
            if key in found:
                raise GraphError(f"two effect nodes {key[0]} instance {key[1]}")
            place = next((k for k in PLACE_KEYS if k in e), None)
            if wired and not placements and place is not None:
                # plan 36 T3: a `/7` frame says where an effect sits by wires
                # (a placement is not read, honoured or not)
                why = PLACEMENT_IS_A_WIRE.format(name=instance_name(*key), key=place,
                                                 where=e[place])
                at = EffectAt(*key)
            found[key] = at
            if why is not None:
                notes.append(why)
        elif kind == "history":
            if history is not None:
                raise GraphError("two history nodes")
            history = got
        else:
            if kind in DECLARED and any(
                    k == kind and o.n == got.n for k, o in others):
                raise GraphError(f"two {kind} nodes of instance {got.n}")
            others.append((kind, got))
    # D1: a placement on an effect this build does not have (an instance
    # the section does not hold, a file not on disk) …
    known = None
    if effects is not None:
        known = set(effects) | {instance_name(f, k) for (f, n) in found for k in range(2, n + 1)}
    for key, at in list(found.items()):
        if at is None or at.where is None or _PLACE_NODE.fullmatch(at.where[1]):
            continue
        why = placement_error(at.name, *at.where, effects=known)
        if why is not None:
            notes.append(why)
            found[key] = at.unplaced()
    # … and a loop of placed effects: each at the default placement
    loops = placement_loops([at for at in found.values() if at is not None])
    for key, at in list(found.items()):
        if at is not None and at.name in loops:
            notes.append(f"{at.name} {at.where[0]} {at.where[1]!r} — that makes a loop "
                         f"({loops[at.name]})")
            found[key] = at.unplaced()
    effects_at = tuple(found[k] for k in sorted(found) if found[k] is not None)
    raw_wires = section.get("wires")
    # plan 35 F: a copy draws an effect instance the section holds — by an
    # entry, a wire or D1 — again; one whose `of` names none is said and
    # dropped with its wires (the rest of the graph stands)
    if any(k == "copy" for k, _ in others):
        held = {e.name for e in effects_at} | {
            name for w in (raw_wires if isinstance(raw_wires, list) else ())
            if isinstance(w, dict) for name in (w.get("from"), _wire_node(w.get("to")))
            if wire_node_kind(name, wired=True) == "effect"}
        for k, got in list(others):
            if k == "copy" and got.of not in held:
                notes.append(COPY_BAD_OF.format(name=got.name, of=got.of))
                others.remove((k, got))
                if isinstance(raw_wires, list):
                    raw_wires = [w for w in raw_wires if not isinstance(w, dict)
                                 or got.name not in (w.get("from"), _wire_node(w.get("to")))]
    if wired:
        # plan 36 T3: hands 1 is always there, and a `/7` writes its entry
        # (`to_json`): read with or without it, the spec is one spec
        hands.setdefault(1, HandsAt(1))
    spec = GraphSpec(hands=tuple(hands[n] for n in sorted(hands)),
                     history=history if history is not None else HistoryAt(),
                     effects=effects_at, others=tuple(others), notes=tuple(notes), wired=wired)
    try:
        wiring = spec.wiring()
    except ValueError as err:
        raise GraphError(str(err)) from err
    layer = wiring.layer_node().n
    if wired and laid:
        # plan 35 F (row 380, T3): in a wired frame any hands node may have a
        # layer, so `laid` sits on the entry whose layer is laid — one of them
        if len(laid) > 1:
            raise GraphError(" and ".join(f"hands {n}" for n in sorted(laid))
                             + ": laid twice (one hands entry says how the layer is laid on)")
        layer = next(iter(laid))
    for n, how in laid.items():
        if n != layer:
            said = wired_hands_name(layer) if wired else hands_name(layer)
            raise GraphError(f"hands {n}: laid {how!r}, but {said} makes the layer")
    spec = replace(spec, laid=laid.get(layer, "over"), laid_on=layer if wired else 1)
    if "wires" not in section:
        return spec
    # plan 28 N4: the wire list — each wire this build cannot honour (no
    # such node or port, a port of another type, two into one port, a
    # loop) is a note and that port's default; the rest stand
    names = {e.name for e in effects_at}
    named = wired_hands_name if wired else hands_name
    ctx = _WireCtx(layer=layer_name(layer),
                   ghosts=frozenset(named(h.n) for h in wiring.nodes()),
                   effects=None if known is None else known | names,
                   composites=frozenset(c.name for c in spec.composites()),
                   switches=frozenset(s.name for s in spec.switches),
                   delays=frozenset(d.name for d in spec.delays),
                   resizes=frozenset(r.name for r in spec.resizes),
                   mattes=frozenset(m.name for m in spec.mattes),
                   cuts=frozenset(c.name for c in spec.cuts),
                   segments=frozenset(x.name for x in spec.segments),
                   echoes=frozenset(e.name for e in spec.echoes),
                   dream=spec.dream is not None,
                   placed={e.name: e.where for e in effects_at if e.placed},
                   wired=wired, copies=frozenset(c.name for c in spec.copies),
                   lookbacks=frozenset({"lookback", *(lb.name for lb in spec.lookbacks)}),
                   legacy=placements)
    wires, wire_notes = _read_wires(raw_wires, ctx, d1_wires(effects_at))
    if ctx.effects is not None and wire_notes:
        wires, wire_notes = _through_missing(raw_wires, ctx, d1_wires(effects_at),
                                             wires, wire_notes, spec, set(effects))
    spec = replace(spec, wires=wires, notes=spec.notes + tuple(wire_notes))
    try:
        spec.wiring()
    except ValueError as err:
        raise GraphError(str(err)) from err
    return spec


def _through_missing(raw: Any, ctx: _WireCtx, d1: list[Wire], wires: tuple[Wire, ...],
                     notes: list[str], spec: GraphSpec, files: set[str]
                     ) -> tuple[tuple[Wire, ...], list[str]]:
    """`_read_wires`' result with a run's wires through an effect file this
    machine lacks kept (plan 33 R27): `frame → foo → acid → fx.image` with
    no `foo` on disk is read as if `foo` were there — the run, and the
    faces' run, keep every wire — so the section a save writes still holds
    them for the Mac that has the file, and the renderer reads the run
    through it (the build: `foo` dormant, said, the run closed over
    it). Only the run's wires on an effect whose *file* is missing are
    kept; a wire on any other missing effect stays refused, as before."""
    every, _ = _read_wires(raw, replace(ctx, effects=None), d1)
    probe = replace(spec, wires=every)
    # (plan 35 T3: a wired frame's run is the one into All outputs — plan 36
    # T4: from whatever heads it, the look-back no longer always does)
    if ctx.wired:
        found = list(run_back(probe, f"{ALL_OUTPUTS}.image"))
    else:
        found = list(run_of(probe, "frame", "fx.image"))
    found += run_of(probe, "pattern", "shape.faces")
    missing = {e for e in found if split_instance(e)[0] not in files}
    if not missing:
        return wires, notes
    back = {w for w in every if w not in wires and (w.src in missing or w.node in missing)}
    if not back:
        return wires, notes
    stood = set(wires)
    keep = tuple(w for w in (Wire(e["from"], e["to"]) for e in raw) if w in stood or w in back)
    return keep, [n for n in notes if not any(n.startswith(f"wire {w} — ") for w in back)]


# the ports a picture goes into (a geometry port or the history's cover is no
# picture): what `reaches` follows
_PICTURE_PORTS = frozenset({"image", "aux", "under", "over", "media", "faces",
                            "hands", "readout", *SWITCH_PORTS})


def reaches(spec: GraphSpec) -> frozenset[str]:
    """Every node with a path, through wires into picture ports, to a sink
    port (`SINKS`: an output, the pipeline end, the faces, the pattern's
    media, the backdrop, the history) — plan 33 G. A node outside it is
    unreached: kept in the preset, drawn faint ("reaches nothing") and
    never run. Reads D1's placements as the wires they are short for.

    Plan 34 L: a delay's `image` is no sink port of its own — it is one
    once the delay is reached (its picture read by something that reaches
    a sink), and then what feeds it is reached too. The walk is that
    fixpoint: a delay is a node like any other, followed back from only
    when reached, so a delay that feeds nothing is unreached and holds no
    buffer, and a loop through one is followed round once.

    Plan 35 F: in a wired frame (`spec.wired`) the walk is seeded by every
    wire into a sink port (`SINK_PORTS`: an output's, All outputs', the
    look-back's capture), and a node is reached when its picture or its
    geometry goes into a port of a reached node. Plan 36 T2: by drawn wires
    only — the faces read the pattern when `pattern → shape.faces` says so
    — and a pin reached (`scene.cover`) reaches its node. `ground` is no
    node: it reaches nothing."""
    if spec.wired:
        return _wired_reaches(spec)
    wires = [w for w in spec.all_wires() if w.port in _PICTURE_PORTS]
    into: dict[str, list[str]] = {}
    for w in wires:
        into.setdefault(w.node, []).append(w.src)
    todo = [src for node, srcs in into.items() if wire_node_kind(node) in SINKS
            for src in srcs]
    got: set[str] = set()
    while todo:
        name = todo.pop()
        if name in got:
            continue
        got.add(name)
        todo.extend(into.get(name, ()))
    return frozenset(got)


def _is_sink(w: Wire) -> bool:
    """Whether wire `w` goes into a sink port of a wired frame (`SINK_PORTS`:
    a whole kind's ports, or one port by its full name)."""
    return any(w.dst == p if "." in p else wire_node_kind(w.node, wired=True) == p
               for p in SINK_PORTS)


def _wired_reaches(spec: GraphSpec) -> frozenset[str]:
    """`reaches` in a wired frame (plan 35 F): the fixpoint from the sinks."""
    return _wired_reach(spec.all_wires())


def _wired_reach(wires) -> frozenset[str]:
    """The names a wired frame's `wires` reach from the sinks (`reaches`,
    and the builder's own: plan 35 B builds only these) — over its drawn
    wires alone (plan 36 T2), a pin reaching its node."""
    wires = [w for w in wires if w.src != GROUND]
    into: dict[str, list[str]] = {}
    for w in wires:
        into.setdefault(w.node, []).append(w.src)
        if pin_node(w.src) is not None:
            into.setdefault(w.src, []).append(pin_node(w.src))
    todo = [w.src for w in wires if _is_sink(w)]
    got: set[str] = set()
    while todo:
        name = todo.pop()
        if name in got:
            continue
        got.add(name)
        todo.extend(into.get(name, ()))
    return frozenset(got)


def run_back(spec: GraphSpec, end: str) -> tuple[str, ...]:
    """The effects wired one after another into input `end`, first first,
    back to the first source that is no effect — whatever heads them (plan
    36 T4: All outputs' run starts at the scene, a composite, a look-back)."""
    wires = [w for w in spec.wires if not is_aux(w)]
    run: list[str] = []
    src = next((w.src for w in wires if w.dst == end), None)
    while src is not None and wire_node_kind(src, wired=spec.wired) == "effect" and src not in run:
        run.insert(0, src)
        src = next((w.src for w in wires if w.dst == f"{src}.image"), None)
    return tuple(run)


def run_of(spec: GraphSpec, head: str = "frame", end: str = "fx.image") -> tuple[str, ...]:
    """The effects wired one after another from `head` to the input `end`,
    in order (plan 33 G): `("acid", "wobble")` for `frame → acid → wobble →
    fx.image`. `()` with no such path — a run is effects only, so a switch
    or a composite on the way ends it. The faces' run is
    `run_of(spec, "pattern", "shape.faces")`. Read off the wire list alone:
    a run is never D1's (`frame` is no place), and D1's `into` an effect of
    the run is a second wire into its `image` that is not the run's."""
    wires = [w for w in spec.wires if not is_aux(w)]
    run: list[str] = []
    src = next((w.src for w in wires if w.dst == end), None)
    while src is not None and src != head:
        if wire_node_kind(src) != "effect" or src in run:
            return ()
        run.insert(0, src)
        src = next((w.src for w in wires if w.dst == f"{src}.image"), None)
    return tuple(run) if src == head else ()


def source_into(wires, port: str, selects: dict[str, int] | None = None) -> str | None:
    """The node whose picture `wires` put into `port` (`pattern.media`,
    `backdrop.image`) — straight, or through a switch, followed to the
    input its pick selects (`selects`: switch name → 0 off, k `in<k>`;
    plan 33 S) — or None: nothing wired, or a switch off or on an unwired
    input."""
    by_dst = {w.dst: w.src for w in wires}
    src, seen = by_dst.get(port), set()
    while src is not None and wire_node_kind(src) == "switch" and src not in seen:
        seen.add(src)
        try:
            k = int((selects or {}).get(src, 0))
        except (TypeError, ValueError):
            k = 0
        src = by_dst.get(f"{src}.in{k}") if 1 <= k <= len(SWITCH_PORTS) else None
    return src


def channel_into(wires, port: str, selects: dict[str, int] | None = None) -> str | None:
    """The media channel (`"a"` … `"h"`) `source_into` finds feeding
    `port`, or None (nothing, or a picture that is not a channel's own: a
    branch through an effect). What `view.media` and `backdrop.channel`
    said before plan 33 T7 retired them, read off the section (the MEDIA
    page's tags, the FACES page's tiles). Plan 35 V2: `channel.<c>` in a
    wired frame, `media.<c>` before it."""
    src = source_into(wires, port, selects)
    if wire_node_kind(src) == "media" or wire_node_kind(src, wired=True) == "channel":
        return src.partition(".")[2]
    return None


def _run_wires(run: tuple[str, ...]) -> set[Wire]:
    """The wires of the run `frame → run… → fx.image` (`frame → fx.image`
    for the empty one)."""
    names = ["frame", *run]
    out = {Wire(a, f"{b}.image") for a, b in zip(names, run)}
    out.add(Wire(names[-1], "fx.image"))
    return out


# the sinks a wire's picture is drawn at (plan 33 R): an output, the
# history, and the faces, the pattern's layer and the backdrop (T4)
_DRAWN_AT = ("output", "history", "shape", "pattern", "backdrop")


def _reached_edges(edges: tuple[Wire, ...], run: tuple[str, ...],
                   placed: tuple[EffectAt, ...]) -> tuple[Wire, ...]:
    """`edges` without the wires into an effect, a composite or (plan 33
    S) a switch that reaches nothing this graph draws (plan 33 R: an unreached node has no node and
    never runs). What is drawn: an output's or the history's port, the
    faces, the pattern's layer, the backdrop (T4), an effect of the run,
    and a placed effect where it sits (D1's own and the wires D1 would
    write short) — and whatever feeds one of those through a picture port.
    Plan 34 L: a resize or a delay is kept by the same rule (`reaches`': a
    delay's input is followed only once the delay is reached), so a wire
    into an unreached one is dropped and it is never built."""
    wires = [*d1_wires(placed), *edges]
    into: dict[str, list[str]] = {}
    for w in wires:
        if w.port in _PICTURE_PORTS:
            into.setdefault(w.node, []).append(w.src)
    todo = [*run, *(e.name for e in placed),
            *(w.src for w in wires if wire_node_kind(w.node) in _DRAWN_AT)]
    got: set[str] = set()
    while todo:
        name = todo.pop()
        if name in got:
            continue
        got.add(name)
        todo.extend(into.get(name, ()))
    return tuple(w for w in edges
                 if wire_node_kind(w.node) not in ("effect", "composite", "switch", "resize",
                                                   "delay")
                 or w.node in got)


# ---------------------------------------------------------------- in words

def output_ports(wiring: Wiring, n: int, rig: RigWires | None = None
                 ) -> dict[str, str | None]:
    """Output `n`'s three ports under a wired frame (plan 35 T4):
    each port's source by `window_ports` (plan 36 T1: its own wire, else
    All outputs' by the bus cable `rig` has standing) — None where nothing
    is wired or `ground` is."""
    got = window_ports(wiring.wires, n, rig)
    return {p: None if w is None or w.src == GROUND else w.src for p, w in got.items()}


def _picture_head(wiring: Wiring, src: str | None) -> str | None:
    """`src` back through the effects and copies on its way (their `image`
    wires) to what they start from."""
    into = {x.dst: x.src for x in wiring.wires}
    seen: set[str] = set()
    while src is not None and wire_node_kind(src, wired=True) in ("effect", "copy") \
            and src not in seen:
        seen.add(src)
        src = into.get(f"{src}.image")
    return src


def through_of(wiring: Wiring, n: int, rig: RigWires | None = None
               ) -> tuple[str, str | None] | None:
    """(the hands layer output `n` puts through the effects, what it is laid
    over — None: nothing, the hands alone) — plan 35 M: its picture a chain
    over a composite whose `over` is a layer, "hands through the effects"
    as wiring — or None. `rig`: the bus cables standing (`output_ports`)."""
    w = wiring
    head = _picture_head(w, output_ports(w, n, rig)["image"])
    if wire_node_kind(head or "", wired=True) != "composite":
        return None
    over = next((x.src for x in w.wires if x.dst == f"{head}.over"), None)
    if wire_node_kind(over or "", wired=True) != "layer":
        return None
    return over, next((x.src for x in w.wires if x.dst == f"{head}.under"), None)


def through_layer(wiring: Wiring, n: int, rig: RigWires | None = None) -> str | None:
    """The hands layer output `n` puts through the effects (`through_of`), or None."""
    got = through_of(wiring, n, rig)
    return got[0] if got is not None else None


def in_scene_hands(wiring: Wiring) -> list[int]:
    """The hands nodes wired into the scene, by instance."""
    return sorted(split_instance(x.src)[1] for x in wiring.wires
                  if x.dst == "scene.geometry" and wire_node_kind(x.src, wired=True) == "hands")


def hands_words(wiring: Wiring, sw, n: int = 1, rig: RigWires | None = None) -> str:
    """Where output `n`'s hands come from, in words (the OUTPUT page, plan
    26 A4; plan 35 T4: read off the wires): `hands: in the scene`
    (a hands node wired into `scene.geometry`, while its picture shows),
    `hands: through FX` (its picture a chain over the layer laid on:
    `through_layer`) or `hands: over` (a layer on its `hands` port) — with
    the hands node's number when the graph has more than one, `as lines`
    for a node drawn as lines, and how a layer is laid on when it is not
    plainly over (`· depth-aware`, `· added`). `hands: off` with the
    window's hands muted — but an output whose scene holds the hands says
    so whatever its mute. `rig`: the bus cables standing (`output_ports`)."""
    w = wiring
    inside = in_scene_hands(w)
    thru = through_of(w, n, rig)
    ports = output_ports(w, n, rig)
    if (inside and sw.scene and ports["image"] is not None
            and not (thru is not None and thru[1] is None)):
        # the scene holds the hands whatever this window's hands mute says
        # (that mute then mutes only the guide)
        return "hands: " + " · ".join(f"in the scene{_node_words(w, k)}" for k in inside)
    if not sw.hands:
        return "hands: off"
    if thru is not None:
        return f"hands: through FX{layer_words(w, thru[0])}"
    return f"hands: over{layer_words(w, ports['hands'])}"


def _node_words(wiring: Wiring, k: int) -> str:
    """` (2)` when the graph has more than one hands node, ` as lines`."""
    nodes = {h.n: h for h in wiring.nodes()}
    h = nodes.get(k, HandsAt(k))
    return ((f" ({k})" if len(nodes) > 1 else "")
            + (" as lines" if h.draw == "lines" else ""))


def layer_words(wiring: Wiring, layer: str | None = None) -> str:
    """What a hands layer is, after "over" or "through FX": its hands
    node's number when there are two, `as lines`, and its blend when it is
    not plainly over (`· depth-aware`, `· added`); "" for today's layer.
    `layer` is the wired layer (`hands.2.layer`); None, All outputs'."""
    w = wiring
    if layer is None:
        layer = output_ports(w, 1)["hands"]
    k = (split_instance(hands_of(layer))[1]
         if wire_node_kind(layer or "", wired=True) == "layer" else 1)
    words = _node_words(w, k)
    if w.blend != "over":
        words += " · depth-aware" if w.blend == "depth" else " · added"
    return words


def lookback_words(wiring: Wiring, lookback: str = LOOKBACK) -> str:
    """What a look-back records, in words (the LOOKBACK page, plan 26 A4;
    plan 36 T4: the wire into its `image`): `history: the scene`, or
    `history: the scene · with the hands` — the hands' layer laid on in a
    composite, or hands drawn inside the scene — or the picture wired in
    when it is not the frame's own (the scene, the backdrop); `history:
    nothing` with none. Plan 30 D1: then each effect placed on the
    look-back's way in or after it (`acid 2 before the history`)."""
    w = wiring
    held = next((x.src for x in w.wires if x.dst == f"{lookback}.image"), None)
    over = next((x.src for x in w.wires if held is not None and x.dst == f"{held}.over"), None)
    hands = (wire_node_kind(held or "", wired=True) == "composite"
             and wire_node_kind(over or "", wired=True) == "layer") or bool(in_scene_hands(w))
    if held is None:
        words = "history: nothing"
    elif hands:
        words = "history: the scene · with the hands"
    else:
        words = "history: the scene"
    for e in w.placed:
        if e.where in (("after", "scene"), ("into", lookback), ("after", lookback)):
            words += " · " + placement_words(e)
    if held is not None and not hands and held not in ("scene", BACKDROP):
        words += " · " + wire_words(Wire(held, f"{lookback}.image"))
    return words


def output_placement_words(wiring: Wiring, n: int, scene: bool, hands: bool) -> str:
    """The placed effects one output's picture goes through (plan 30 D1:
    the OUTPUT page's "shows:" line), each ` · ` and its words: those on
    this output (`palette 2 on output 2 only` reads `palette 2 on this
    output only`), those on a hands layer while it shows them, those on the
    scene's way (the look-back, an effect of the chain) while it shows the
    scene; "" for none. Plan 35 T4: the placements as the wired frame says
    them (`after: hands.layer`, `into: lookback`)."""
    out = []
    for e in wiring.placed:
        where = e.where[1]
        if where.startswith("output."):
            if where == f"output.{n}":
                out.append(f"{_effect_words(e.name)} on this output only")
        elif where == "hands" or where.startswith("hands."):
            if hands:
                out.append(placement_words(e))
        elif scene:
            out.append(placement_words(e))
    return "".join(" · " + w for w in out)


def _effect_words(name: str) -> str:
    """An effect instance in words: `palette`, `acid 2`."""
    return name.replace(".", " ")


def _node_said(where: str) -> str:
    """A placeable node in words: `the scene`, `the hands`, `hands 2`,
    `the history`, `output 2`, `acid 2` (plan 35 T4: the new ids too —
    `lookback`, `hands.layer`, `hands.2.layer`, `channel.a`)."""
    if where.endswith(".layer") and where.startswith("hands"):
        where = hands_of(where)
    if where == LOOKBACK:
        where = "history"
    if where in ("scene", "hands", "history"):
        return f"the {where}"
    if where.startswith("hands."):
        return "hands " + where.partition(".")[2]
    if where.startswith("output."):
        return "output " + where.partition(".")[2]
    return _effect_words(where)


def placement_words(e: EffectAt) -> str:
    """Where a placed effect sits, in words (plan 30 D1: the OUTPUT and
    LOOKBACK pages): `palette on the hands`, `acid 2 before the history`
    (after the scene: the history and the capture both read it), `palette
    2 on output 2 only`, `acid 2 into the history only` (the capture
    keeps the scene), `palette after the history`, `palette after acid 2`,
    `palette before acid 2`."""
    w = _effect_words(e.name)
    key, where = e.where
    if where.startswith("output."):
        return f"{w} on {_node_said(where)} only"
    if key == "after":
        if where == "scene":
            return f"{w} before the history"
        if where == "hands" or where.startswith("hands."):
            return f"{w} on {_node_said(where)}"
        return f"{w} after {_node_said(where)}"
    if where in ("history", LOOKBACK):
        return f"{w} into the history only"
    return f"{w} before {_node_said(where)}"


def graph_words(spec: GraphSpec | None, dormant: dict[str, str] | None = None) -> str:
    """The loaded preset's graph in one line (the OUTPUT page): `graph:
    default`, or what it changes — `graph: hands 1 in the scene as lines ·
    hands 2 a layer · acid ×2 · history with the hands`. Plan 30 D1: then
    each placed effect where it sits (`placement_words`), or — `dormant`,
    the built graph's `Graph.dormant` — why it runs nowhere this frame
    (`palette after hands — no hands layer this frame`)."""
    if spec is None:
        return "graph: default"
    w, parts = spec.wiring(), []
    several = len(w.nodes()) > 1
    for h in w.nodes():
        if h.into == "layer" and h.draw == "solid" and not several:
            continue
        where = "in the scene" if h.into == "scene" else "a layer"
        parts.append(f"hands {h.n} {where}" + (" as lines" if h.draw == "lines" else ""))
    if w.blend != "over":
        parts.append("laid " + ("depth-aware" if w.blend == "depth" else "added"))
    parts += [f"{f} ×{n}" for f, n in sorted(spec.effect_counts().items())]
    if w.history == "scene+hands":
        parts.append("history with the hands")
    dormant = dormant or {}
    parts += [dormant.get(e.name) or placement_words(e) for e in w.placed]
    parts += [kind for kind, _ in spec.others if kind != "composite"]
    # plan 28 N4: the wires the graph builds as edges, or why one is dormant
    parts += [dormant.get(str(x)) or wire_words(x) for x in w.wires]
    return "graph: " + (" · ".join(parts) if parts else "default")


def wire_words(w: Wire) -> str:
    """One wire in words (plan 28 N4, the OUTPUT and LOOKBACK pages):
    `output 2 shows acid 2`, `hands 2 over output 2`, `the guide of the
    hands on output 1`, `the history holds the hands`, `acid 2 reads the
    history`, `the hands over in composite`."""
    src = _node_said(w.src)
    if w.node.startswith("output."):
        out = _node_said(w.node)
        if w.port == "image":
            return f"{out} shows {src}"
        if w.port == "hands":
            return f"{src} over {out}"
        if w.port == DEPTH_PORT:                # plan 36 T2
            return f"the hands on {out} depth-aware against {src}"
        return f"the guide of {src} on {out}"
    if w.node in ("history", LOOKBACK):
        return f"the history holds {src}"
    if wire_node_kind(w.node) == "composite":
        return f"{src} {w.port} in {_effect_words(w.node)}"
    return f"{_effect_words(w.node)} reads {src}"


def output_wires(wiring: Wiring, n: int) -> dict[str, Wire]:
    """Output `n`'s ports the wiring's wires take (plan 28 N4): port → wire."""
    return {w.port: w for w in wiring.wires if w.node == f"output.{n}"}


class _SizedData:
    """A frame's per-frame `data` at another size (plan 33 R): the root
    frame's own dict, each key stored as `(key, size)` — so a node read at
    two sizes is made once at each, and what it made at the frame's size
    (keyed by its bare name, as before) is never the other's."""

    __slots__ = ("data", "size")

    def __init__(self, data: dict, size: tuple[int, int]):
        self.data, self.size = data, size

    def __contains__(self, key) -> bool:
        return (key, self.size) in self.data

    def __getitem__(self, key):
        return self.data[(key, self.size)]

    def __setitem__(self, key, value) -> None:
        self.data[(key, self.size)] = value

    def get(self, key, default=None):
        return self.data.get((key, self.size), default)

    def setdefault(self, key, default=None):
        return self.data.setdefault((key, self.size), default)

    def pop(self, key, *default):
        return self.data.pop((key, self.size), *default)


@dataclass
class Frame:
    """One frame as the nodes see it: the renderer and what
    `Renderer._draw_frame` settled before evaluation (the frame's size
    under the cap, the first output's target to bind again after a
    failure, the chain's state), and what the nodes fill in as they run
    (the cover, the hands' layer, the readout, each end's frame texture
    — `frames`, by the `Shown` end's name —, the failures, `stats`, each
    node's per-frame `data`).

    Plan 33 R: a branch is made at the size its consumer asks
    (`Node.size_for`): `at(size)` is this frame at another size — the
    faces' `FACE_PIC`², the pattern's layer at its channel's own — with
    its own `data` (the root's, keyed `(name, size)`: `_SizedData`), its
    own pool of effect textures (`pool`), a see-through ground and every
    effect pass at `u_opaque` 0 (`opaque`): a picture made there is one
    whose alpha is a face's intensity, never the window's."""

    r: Any                                   # the Renderer (duck-typed: graph.py never imports render)
    ctx: moderngl.Context
    s: Any                                   # the ViewState
    w: int
    h: int
    dpr: float
    t: float
    views: list[View]
    size: tuple[int, int]                    # the frame's pixel size (output 1 under the cap)
    samples: int                             # the scene's MSAA sample count (output 1's)
    target: moderngl.Framebuffer             # output 1's framebuffer …
    vp: tuple[int, int, int, int]            # … and its rect: bound again after a failure
    bg_alpha: float = 1.0
    fx_on: bool = False
    stats: dict = field(default_factory=dict)
    # filled by the nodes
    cover: moderngl.Texture | None = None
    hands: bool = False                      # the hands' layer drew (a hand shows)
    readout: moderngl.Texture | None = None
    frames: dict[str, moderngl.Texture | None] = field(default_factory=dict)  # end → texture; None: direct
    failed: set[str] = field(default_factory=set)            # (plan 35: by the end's name)
    data: dict[str, Any] = field(default_factory=dict)    # a node's per-frame values, by name
    graph: Graph | None = None
    _users: dict[str, list[int]] | None = None
    # plan 33 R: `u_opaque` for the effects' passes painted for this frame
    # (None: the chain's own, the window's ground), the frame this one is
    # at another size of (None: the frame itself), and those it has made
    opaque: int | None = None
    parent: Frame | None = None
    _at: dict[tuple[int, int], Frame] = field(default_factory=dict)
    # plan 33 S: each switch's `select` this frame (switch name → 0 off,
    # 1–8 the input), read once by the renderer (`ViewState.switch`): what
    # `SwitchNode.selected` and `Graph.pulled` read — never a rebuild
    selects: dict[str, int] = field(default_factory=dict)
    # plan 34 Z: each resize's values this frame (resize name → its
    # `view.ResizeState`), read once by the renderer (`ViewState.resize`):
    # what `ResizeNode` crops and sizes by — a value, never a rebuild
    resizes: dict[str, Any] = field(default_factory=dict)

    @property
    def root(self) -> Frame:
        """The frame itself: what `at` made this one from, or this one."""
        return self.parent if self.parent is not None else self

    @property
    def mattes(self) -> dict[str, Any]:
        """Plan 39 T2: each matte's values this frame (matte name → its
        `view.MatteState`): the view state's (`ViewState.mattes`, the
        `matte[.n].*` params') — what `MatteNode` makes its mask by, a value,
        never a rebuild (getattr: a view state from before the matte has none)."""
        return getattr(self.root.s, "mattes", None) or {}

    @property
    def cuts(self) -> dict[str, Any]:
        """Plan 39 T3: each cut's values this frame (cut name → its
        `view.CutState`): the view state's (`ViewState.cuts`, the
        `cut[.n].*` params') — a value, never a rebuild (getattr: a view
        state from before the cut has none)."""
        return getattr(self.root.s, "cuts", None) or {}

    @property
    def segments(self) -> dict[str, Any]:
        """Plan 39 T4: each segment's values this frame (segment name → its
        `view.SegmentState`): the view state's (`ViewState.segments`, the
        `segment[.n].*` params') — a value, never a rebuild (getattr: a view
        state from before the segment has none)."""
        return getattr(self.root.s, "segments", None) or {}

    def at(self, size: tuple[int, int]) -> Frame:
        """This frame at `size` (see the class): made once a frame per
        size, however many consumers ask it."""
        size = (int(size[0]), int(size[1]))
        root = self.root
        got = root._at.get(size)
        if got is None:
            got = root._at[size] = replace(root, size=size, bg_alpha=0.0, opaque=0,
                                           data=_SizedData(root.data, size), parent=root,
                                           _at={}, _users=None)
        return got

    def key(self, name: str):
        """A renderer's texture key for node `name` at this frame's size:
        the name itself at the frame's, `(name, size)` at another."""
        return name if self.parent is None else (name, self.size)

    def pool(self, n: int) -> list[tuple[moderngl.Texture, moderngl.Framebuffer]]:
        """The effects' textures at this frame's size, at least `n`: the
        chain's pool (`FxChain.pool`) at the frame's size, the renderer's
        pool for that size at another (`Renderer.pool_at`)."""
        if self.parent is None:
            return self.r.fx.pool(self.size, n)
        return self.r.pool_at(self.size, n)

    def users(self, end: Node) -> list[int]:
        """The views end `end` feeds this frame (indexes into `views`):
        each output's wired end, settled (`Output.settle`). Asked by the
        ends (`Shown`), which run after the hands' layer —
        whether a hand shows decides where a through output's picture
        comes from. Plan 35 B: counted through each window's mutes (a
        window whose picture is muted takes no end), so muting one of two
        windows puts the other back on the direct paint, with no rebuild."""
        if self._users is None:
            users: dict[str, list[int]] = {}
            for out in self.graph.outputs if self.graph is not None else ():
                got, _ = out.settle(self)
                if got is not None:
                    users.setdefault(got.name, []).append(out.index)
            self._users = users
        return self._users.get(end.name, [])

    def timed(self, name: str):
        """``with frame.timed(node.name):`` — the node's GPU time this frame."""
        return self.r._timed(name)


class Node:
    """One node: a unique `name` (the SYSTEM page's line and the timer's
    key), typed input ports (`INPUTS`: port → type) wired to other nodes,
    one output of type `OUTPUT` (None for a sink), and `after`, ordering
    dependencies that carry no image (the capture after every end, each
    delay's write and each output's hands and guide: `Capture.after`).

    `run(frame)` is called once a frame, in the graph's order. A node
    whose picture is a texture overrides `image(frame)` (and `depth` when
    it has one); one that paints into its consumer's framebuffer
    overrides `paint(frame, dst)`. The default `paint` shows the texture
    1:1, so any image can feed any image port."""

    KIND = "node"
    INPUTS: ClassVar[dict[str, str]] = {}      # port → type
    OUTPUT: str | None = None
    TIMED = True              # a line on the SYSTEM page; a geometry's time is its scene's
    SOLID = False             # a geometry drawn opaque, before the see-through shape
    # plan 30 D1: a node whose picture is a texture it made in `run` (the
    # scene, a layer): `image` None means no picture this frame, and an
    # effect placed after it folds that texture once, in its own `run`
    MAKES = False
    # plan 30 D1: the image ports that read something besides the picture
    # (a depth, a readout, the face buffer): an effect placed `after` a node
    # leaves these reading the node itself
    REFS: ClassVar[frozenset[str]] = frozenset()
    # plan 33 R: the image ports that ask a size of their own, not the
    # frame's (`size_for`: the faces, the pattern's layer) — an effect that
    # only they read is made there and never folded at the frame's size
    SIZED: ClassVar[frozenset[str]] = frozenset()
    # plan 33 R: a node that makes a texture (`MAKES`) but draws itself
    # straight into any framebuffer at that framebuffer's size (the
    # pattern's seed): an effect after it paints it, as the faces' chain
    # always seeded its first texture, rather than folding its texture
    PAINTS = False
    # plan 34 (the brief's `Node.said`): what the node says it holds, in
    # words, set in `run` by a node that has any (a delay's "last frame's ·
    # 960×600 half-float") — GRAPH's summary reads it
    said: str = ""

    def __init__(self, name: str, after: tuple[Node, ...] = (), **inputs: Node | None):
        unknown = set(inputs) - set(self.INPUTS)
        if unknown:
            raise ValueError(f"{self.KIND} node {name!r}: no port {sorted(unknown)}")
        for port, node in inputs.items():
            want = self.INPUTS[port]
            if node is not None and node.OUTPUT != want:
                raise TypeError(f"{self.KIND} node {name!r}: port {port!r} takes {want}, "
                                f"{node.name!r} makes {node.OUTPUT}")
        self.name = name
        self.inputs: dict[str, Node | None] = {p: inputs.get(p) for p in self.INPUTS}
        self.after = tuple(after)

    def deps(self) -> list[Node]:
        """What must run before this node: its wired inputs, then `after`."""
        return [n for n in self.inputs.values() if n is not None] + list(self.after)

    def run(self, frame: Frame) -> None:
        """This node's work for the frame; nothing by default."""

    def image(self, frame: Frame) -> moderngl.Texture | None:
        """The texture this node made this frame, or None when it paints."""
        return None

    def depth(self, frame: Frame) -> moderngl.Texture | None:
        """The depth beside `image` (the shared camera's), or None."""
        return None

    def alpha(self, frame: Frame) -> float:
        """The opacity this node's picture is laid on at (a layer's)."""
        return 1.0

    def size_for(self, port: str, frame: Frame) -> tuple[int, int]:
        """The size port `port` asks of what feeds it this frame (plan 33
        R): the frame's (`frame.size` — an effect's is its consumer's, the
        frame it is painted for); the faces and the pattern's layer say
        their own (`SIZED`)."""
        return tuple(frame.size)

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        """The size this node makes its picture at whatever its consumer
        asks (plan 34 D, row 368): a delay's held size, a resize's, an
        echo's — or None, its consumer decides (every node before plan 34).
        A consumer of another size gets the picture fitted by `OWN_FIT`."""
        return None

    def reads(self, frame: Frame) -> bool:
        """Whether this node's picture comes from something this frame
        (plan 33 R): False only for a channel with nothing on it, and what
        reads only such (`MediaNode`, an `Effect`, a `Composite`) — the
        faces then show the pattern, not black."""
        return True

    def lay(self, frame: Frame, dst: moderngl.Framebuffer, rect: tuple, blend: str,
            opaque: bool, flip: tuple[bool, bool] = (False, False),
            scene_depth: moderngl.Texture | None = None) -> None:
        """This node's picture laid into `dst`'s `rect` with `blend`, at its
        opacity (`Renderer.lay`), depth-aware against `scene_depth` — what
        a Composite or an Output asks of the layer on its `over` port."""
        frame.r.lay(self.image(frame), dst, rect, blend=blend, alpha=self.alpha(frame),
                    opaque=opaque, flip=flip,
                    depth=self.depth(frame) if scene_depth is not None else None,
                    scene_depth=scene_depth)

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """This node's picture into `dst`'s viewport: the texture 1:1 when
        it made one (nothing when it made none this frame)."""
        tex = self.image(frame)
        if tex is None:
            return
        rect = tuple(dst.viewport)
        frame.r._show(dst, rect, rect, tex, frame.size, frame.bg_alpha >= 1.0, frame.bg_alpha)

    def __repr__(self) -> str:
        wired = ", ".join(f"{p}={n.name if n else None}" for p, n in self.inputs.items())
        return f"{self.KIND}({self.name!r}{', ' + wired if wired else ''})"


# ---------------------------------------------------------------- geometry

class Shape(Node):
    """The 4D shape (`Renderer.draw_scene`): the faces, the edges, the
    points, instanced, painter-sorted, in the shared camera — see-through:
    depth-tested against the solid geometry already drawn, its visible
    surface written after. `draw` draws into whatever is bound — clearing
    it first when it is the scene's only geometry (`clear`), as it always
    did.

    Plan 33 R: `faces`, the faces' one input (`shape.faces`). Unwired, or
    wired straight from the `pattern` (or through effects of it all off
    this frame), the faces draw the pattern per face as they always did —
    no `FACE_PIC` pass. Wired from anything else, `prepare` paints that
    picture at `FACE_PIC`² (`size_for`, `Frame.at`) into the faces'
    picture (`Renderer._face_picture`, before the scene's target is
    bound), shown per face or in screen space by `fx.face_map`: from the
    pattern through effects that is the faces' chain as it always ran (the
    pattern seeded into the first texture, the effects one after another).
    A picture that reads nothing this frame (a channel empty or lost:
    `Node.reads`) leaves the faces the pattern for that frame, never
    black. `prepare` also hands the scene pass what the pattern's layer
    reads (`PatternNode.layer`, `Renderer._face_layer`).

    Plan 36 T2 (W2): the pattern is a wire, `pattern → shape.faces` (or
    through effects, a switch …), never read by name. Unwired, the faces
    are plain (`Renderer._face_plain`: no pattern, no media layer — a flat
    face); the media layer handed over is the pattern node's the faces'
    wires lead back to, if any."""

    KIND = "geometry"
    INPUTS: ClassVar[dict[str, str]] = {"faces": IMAGE}
    OUTPUT = GEOMETRY
    TIMED = False
    SIZED: ClassVar[frozenset[str]] = frozenset({"faces"})

    def size_for(self, port: str, frame: Frame) -> tuple[int, int]:
        if port == "faces":
            return (FACE_PIC, FACE_PIC)
        return super().size_for(port, frame)

    def faces(self, frame: Frame) -> Node | None:
        """What the faces' picture is painted from this frame, or None —
        the faces draw the pattern per face: unwired, the pattern itself
        (or effects of it each off this frame), or a picture that reads
        nothing — a switch at off, or picking an unwired input, among them
        (plan 33 S)."""
        src = self.inputs.get("faces")
        head = src
        while True:
            if isinstance(head, Effect) and not head.on(frame):
                head = head.inputs["image"]
            elif isinstance(head, SwitchNode):     # plan 33 S: the input it picks
                head = head.selected(frame)
            else:
                break
        if head is None or isinstance(head, PatternNode):
            return None
        at = frame.at(self.size_for("faces", frame))
        return src if src.reads(at) else None

    def pattern(self) -> PatternNode | None:
        """The pattern node the faces' wires lead back to (plan 36 T2):
        straight, or through effects, copies, switches and composites —
        whatever reads it on the way — or None."""
        todo, seen = [self.inputs.get("faces")], set()
        while todo:
            n = todo.pop()
            if n is None or id(n) in seen:
                continue
            seen.add(id(n))
            if isinstance(n, PatternNode):
                return n
            todo.extend(v for _, v in sorted(n.inputs.items(), reverse=True))
        return None

    def prepare(self, frame: Frame) -> None:
        r = frame.r
        pattern = self.pattern()
        r._face_layer = None
        r._face_plain = self.inputs.get("faces") is None
        try:
            # (the layer read only for faces that draw: a channel nothing
            # shows is not read, as before plan 33)
            if isinstance(pattern, PatternNode) and getattr(frame.s, "faces", True):
                r._face_layer = pattern.layer(frame)
            src = self.faces(frame)
        except Exception as e:  # noqa: BLE001 — the faces' picture must not take the frame down
            r.face_error = f"faces: {type(e).__name__}: {e}"[:160]
            r._pic = None
            return
        paint = None
        if src is not None:
            at = frame.at(self.size_for("faces", frame))

            def paint(dst: moderngl.Framebuffer, src: Node = src, at: Frame = at) -> None:
                src.paint(at, dst)
        r._pic = r._face_picture(frame.s, frame.t, paint)

    def draw(self, frame: Frame, clear: bool = True) -> None:
        try:
            frame.r.draw_scene(frame.s, frame.w, frame.h, frame.dpr, frame.t, clear=clear)
        finally:
            frame.r._pic = None          # handed to that one scene pass only
            frame.r._face_layer = False  # (and the layer: outside a frame, the wiring's)
            frame.r._face_plain = False  # (and plain faces: outside a frame, as ever)


class Hands(Node):
    """The hands as geometry (plan 26 A3): `Ghost`'s styles (`ghost.style`:
    `hands_parts` … `marionette_parts`) in the shared camera
    (`ghost.shared_camera`: the eye and the Leap calibration). `run`
    settles the frame's poses once (`Ghost.settle`: the fades stepped, the
    camera fitted) for every draw of them; `draw` puts them into the bound
    framebuffer as solid geometry — the scene's, before the see-through
    shape (`Ghost.draw_solid`). The hands' layer and the readout draw the
    same settled poses into their own targets. The `ghost.*` params are
    this node's (the naming rule: the first hands node keeps today's ids).

    Plan 26 A4: each hands node is its own `Ghost` (`Renderer.ghost_of`
    its name: `ghost` is the renderer's own, `ghost.2` … a second one
    with its own `ghost.2.*` params), drawn solid or as lines (`draw`,
    the preset's graph). Its time is its own SYSTEM line where a scene
    draws it — the consumer edge decides (`Graph.timed`), the node is
    never told — and the layer's otherwise. A draw that raises costs the
    scene nothing: the frame goes on without the hands and its
    `Ghost.error` says why."""

    KIND = "geometry"
    OUTPUT = GEOMETRY
    SOLID = True
    TIMED = False             # timed under its own name by the scene that draws it

    def __init__(self, name: str, after: tuple[Node, ...] = (), draw: str = "solid",
                 **inputs: Node | None):
        if draw not in DRAWS:
            raise ValueError(f"hands {name!r}: draw {draw!r}, one of {', '.join(DRAWS)}")
        super().__init__(name, after, **inputs)
        self.draw_as = draw

    def ghost(self, frame: Frame):
        """This node's `Ghost` (`Renderer.ghost_of`), by its params' prefix
        (plan 35 V2: the node `hands.2` draws `ghost.2`)."""
        return ghost_of(frame.r, param_prefix(self.name))

    def run(self, frame: Frame) -> None:
        w, h = frame.size
        s, r = frame.s, frame.r
        frame.data[self.name] = None
        try:
            frame.data[self.name] = self.ghost(frame).settle(
                frame.t, max(w, 1) / max(h, 1), getattr(s, "eye_fov", None),
                getattr(s, "eye_distance", None))
        except Exception as e:  # noqa: BLE001 — a malformed skeleton costs the hands only
            r._hands_failed(e, frame.target, frame.vp, ghost=self.ghost(frame))

    def now(self, frame: Frame):
        """This frame's settled (poses, view_proj, eye), or None."""
        return frame.data.get(self.name)

    def prepare(self, frame: Frame) -> None:
        """Nothing before the scene's target is bound."""

    def draw(self, frame: Frame) -> None:
        r, gh = frame.r, self.ghost(frame)
        try:
            now = self.now(frame)
            drew = bool(gh.draw_solid(now, lines=True) if self.draw_as == "lines"
                        else gh.draw_solid(now))
            frame.stats["in_scene"] = bool(frame.stats.get("in_scene")) or drew
        except Exception as e:  # noqa: BLE001 — the hands must not take the scene down
            if not gh.error:
                gh.error = f"ghost hands in the scene: {type(e).__name__}: {e}"[:160]
            r._rebind(r.scene.draw_fbo, (0, 0, *frame.size))


# ---------------------------------------------------------------- point cloud (plan 26 A4b)
#
# A point-cloud source (plan 27 B4's contract, `devices.PointCloud`: N×3
# float32 points, read-only and C-contiguous, a frame id, a timestamp,
# optional N×3 colours) drawn as points in the shared camera, each a
# screen-space quad with a real depth (A2's point-quad expansion, one
# instance per point). The renderer is handed the device registry
# (`Renderer.cloud_source`, by `app`, as the hands' tracker is handed to
# `renderer.ghost.source`); this module never imports `devices`: the
# source is duck-typed — iterable of devices with `kind` and `role`, and
# a `clouds` mapping ``cloud:<role>`` → the latest cloud with `points`,
# `colors`, `frame`, `t`, `n`. The look is the `cloud.*` session params
# (`ViewState.cloud_*`). A role with no device, a device not open, or a
# frame not yet published draws nothing and raises nothing.

# the device kind a point-cloud node is made for (the ruling of this run:
# clouds follow the device list; A4's graph JSON has no `cloud` node kind)
CLOUD_KIND = "cloud"

CLOUD_EYE_W = f"{EYE_NEAR * 1.2:.6f}"    # render.EYE_W: a point behind the eye is dropped

CLOUD_VS = """
#version 330
in vec2 in_corner;   // per vertex: the quad's corner, (±1, ±1)
in vec3 in_pos;      // per instance: the point, in the cloud's units
in vec3 in_color;    // per instance: its RGB (white when the cloud has none)
uniform mat4 u_vp;   // the eye (geometry.eye_matrix)
uniform mat4 u_model;   // the cloud's units → the world (cloud.scale)
uniform vec2 u_px;   // the target's size, px
uniform float u_size;   // radius, framebuffer px
uniform float u_bright;
uniform float u_colors;  // 1 the cloud's colours, 0 white
out vec2 v_corner;
out vec3 v_color;
void main() {
    vec4 c = u_vp * (u_model * vec4(in_pos, 1.0));
    v_corner = in_corner;
    v_color = mix(vec3(1.0), in_color, u_colors) * u_bright;
    if (c.w < """ + CLOUD_EYE_W + """) {        // behind the eye: nothing
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }
    gl_Position = vec4(c.xy + in_corner * u_size / (0.5 * u_px) * c.w, c.z, c.w);
}
"""

# solid round dots: opaque inside the radius (depth written), nothing outside
CLOUD_FS = """
#version 330
in vec2 v_corner;
in vec3 v_color;
out vec4 f_color;
void main() {
    if (dot(v_corner, v_corner) > 1.0) discard;
    f_color = vec4(clamp(v_color, 0.0, 1.0), 1.0);
}
"""

# a point's quad: two triangles over its corners (render._POINT_CORNERS)
_CLOUD_CORNERS = np.array([(-1, -1), (1, -1), (-1, 1), (1, -1), (1, 1), (-1, 1)],
                          dtype=np.float32)


def cloud_roles(source) -> tuple[str, ...]:
    """The roles of the `cloud` devices `source` lists (a device registry,
    duck-typed), in list order — listed, open or not: what the default
    graph gains a point-cloud node for. None (no registry) is none."""
    if source is None:
        return ()
    try:
        return tuple(str(d.role) for d in source if getattr(d, "kind", "") == CLOUD_KIND)
    except Exception:  # noqa: BLE001 — a registry mid-change costs the clouds, never the frame
        return ()


class _CloudGL:
    """One renderer's GL objects for its clouds: the program and the
    quad's corners, shared, and per node the points' and colours'
    buffers, their vertex array and the (frame, t) they hold — uploaded
    only when that moves. Kept on the renderer (`_cloud_gl`), so a graph
    rebuilt for new switches re-uploads nothing."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=CLOUD_VS, fragment_shader=CLOUD_FS)
        self.corners = ctx.buffer(_CLOUD_CORNERS.tobytes())
        self.slots: dict[str, dict] = {}

    def upload(self, name: str, cloud) -> dict:
        """`cloud` into node `name`'s buffers when its (frame, t) moved;
        the slot: `vao`, `n`, `key`, `uploads` (a count, for the tests)."""
        slot = self.slots.get(name)
        key = (int(cloud.frame), float(cloud.t))
        if slot is not None and slot["key"] == key:
            return slot
        pts = cloud.points
        n = int(pts.shape[0])
        cols = cloud.colors if cloud.colors is not None else np.ones((n, 3), np.float32)
        if slot is None:
            pbuf = self.ctx.buffer(reserve=max(pts.nbytes, 12), dynamic=True)
            cbuf = self.ctx.buffer(reserve=max(pts.nbytes, 12), dynamic=True)
            vao = self.ctx.vertex_array(self.prog, [
                (self.corners, "2f", "in_corner"),
                (pbuf, "3f/i", "in_pos"),
                (cbuf, "3f/i", "in_color")])
            slot = self.slots[name] = {"pbuf": pbuf, "cbuf": cbuf, "vao": vao, "uploads": 0}
        for buf, data in ((slot["pbuf"], pts), (slot["cbuf"], cols)):
            if n:
                arr = np.ascontiguousarray(data, dtype=np.float32)   # sized as written
                buf.orphan(max(arr.nbytes, 12))
                buf.write(arr)
        slot["n"], slot["key"] = n, key
        slot["uploads"] += 1
        return slot

    def release(self) -> None:
        """Every GL object (`Renderer.on_reload`: a shader edit lands)."""
        for slot in self.slots.values():
            for k in ("vao", "pbuf", "cbuf"):
                slot[k].release()
        self.slots = {}
        self.corners.release()
        self.prog.release()


class PointCloud(Node):
    """A point-cloud geometry (plan 26 A4b): the latest frame of
    ``cloud:<role>`` (`Renderer.cloud_source.clouds`, plan 27 B4) as
    round points in the shared camera — the eye (`eye.*`) and the cloud's
    own world transform, a uniform scale about the world origin
    (`cloud.scale`): the shape's `camera.*` and `rot.*` are the shape's,
    not the cloud's. Solid, like the hands: drawn into the scene before
    the see-through shape, depth tested and depth written, so the shape's
    strokes in front of a point draw over it and a point in front of them
    hides them. `cloud.size` is each point's radius in logical px (a
    whole number of framebuffer pixels across, as A2's points),
    `cloud.bright` and `cloud.colors` its colour. The buffer is uploaded
    only when the cloud's frame id (or its publish time, for a device
    re-opened) moves. Its draw is its own SYSTEM line (the node's name);
    a cloud that is missing draws nothing and costs nothing else."""

    KIND = CLOUD_KIND
    OUTPUT = GEOMETRY
    SOLID = True

    def __init__(self, name: str, role: str, after: tuple[Node, ...] = (),
                 **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.role = role

    @property
    def source(self) -> str:
        """The registry's key for this node's cloud: ``cloud:<role>``."""
        return f"{CLOUD_KIND}:{self.role}"

    def cloud(self, frame: Frame):
        """This frame's cloud, or None (no registry, no device, nothing
        published yet)."""
        src = getattr(frame.r, "cloud_source", None)
        if src is None:
            return None
        try:
            return (getattr(src, "clouds", None) or {}).get(self.source)
        except Exception:  # noqa: BLE001 — a source that raises is a cloud not there
            return None

    def prepare(self, frame: Frame) -> None:
        """Nothing before the scene's target is bound."""

    def draw(self, frame: Frame) -> None:
        drawn = frame.stats.setdefault("clouds", {})
        drawn[self.name] = 0
        cloud = self.cloud(frame)
        if cloud is None or not getattr(cloud, "n", 0):
            return
        r, ctx, s = frame.r, frame.ctx, frame.s
        try:
            gl = getattr(r, "_cloud_gl", None)
            if gl is None:
                gl = r._cloud_gl = _CloudGL(ctx)
            slot = gl.upload(self.name, cloud)
            vp = eye_matrix(frame.w, frame.h, getattr(s, "eye_fov", EYE_FOV),
                            getattr(s, "eye_distance", EYE_DISTANCE))
            k = float(getattr(s, "cloud_scale", 0.3))
            p = gl.prog
            p["u_vp"].write(np.asarray(vp, dtype="f4").T.tobytes())
            p["u_model"].write(np.diag([k, k, k, 1.0]).astype("f4").T.tobytes())
            w, h = frame.size
            p["u_px"].value = (float(max(w, 1)), float(max(h, 1)))
            # radius in framebuffer px (× dpr), the diameter a whole number
            # of pixels — draw_scene's points (A2's rounding)
            rad = max(float(getattr(s, "cloud_size", 2.0)), 0.0) * frame.dpr
            p["u_size"].value = math.floor(2.0 * rad + 0.5) / 2.0
            p["u_bright"].value = max(float(getattr(s, "cloud_bright", 1.0)), 0.0)
            p["u_colors"].value = 1.0 if getattr(s, "cloud_colors", True) else 0.0
            ctx.enable(moderngl.DEPTH_TEST | moderngl.BLEND)
            ctx.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
            slot["vao"].render(moderngl.TRIANGLES, vertices=6, instances=slot["n"])
            drawn[self.name] = slot["n"]
        except Exception as e:  # noqa: BLE001 — a cloud must not take the scene down
            frame.stats["cloud_error"] = f"{self.name}: {type(e).__name__}: {e}"[:160]
        finally:
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA


def cloud_nodes(g: Graph, roles: tuple[str, ...] | list[str]) -> list[PointCloud]:
    """One point-cloud node per listed role, added to `g`: the first is
    `cloud`, the next `cloud.2`, … (the naming rule's marker form). Each
    reads the `cloud.*` params (a second instance's own params are A4's)."""
    return [g.add(PointCloud(CLOUD_KIND if i == 0 else f"{CLOUD_KIND}.{i + 1}", role))
            for i, role in enumerate(roles)]


# ---------------------------------------------------------------- end point cloud
def ghost_of(r, name: str):
    """The `Ghost` that draws hands node `name` (`Renderer.ghost_of`); the
    renderer's one ghost for a renderer from before A4 (or a stand-in)."""
    get = getattr(r, "ghost_of", None)
    return get(name) if get is not None else r.ghost


# ---------------------------------------------------------------- scene

def _geometry_port(i: int) -> str:
    """A scene's i-th geometry port: `geometry`, `geometry.2`, … (the
    naming rule's marker form)."""
    return "geometry" if i == 0 else f"geometry.{i + 1}"


class Scene(Node):
    """The scene: its geometries into the renderer's `SceneTarget` (colour
    and depth, at the frame's size and output 1's sample count), resolved
    into its texture. Any number of geometries, one port each
    (`geometry`, `geometry.2`, …): the solid ones first (the hands, depth
    written), then the see-through shape, painter-sorted and depth-tested
    against them (A2's depth pass then writes its visible surface). With
    no solid geometry the pass is exactly A2's — the shape clears and
    draws. The blank texture takes the sampler units first, so the scene
    texture is never bound while it is the target.

    Plan 32 R: `ground`, the alpha the scene clears to when not the
    window's ground (`Renderer.scene_ground`): 0 when it is laid over the
    backdrop (`BACKDROP`), so it is a premultiplied layer the backdrop
    shows through; None, the window's (`bg_alpha`), as it always was."""

    KIND = "scene"
    OUTPUT = IMAGE
    MAKES = True

    def __init__(self, name: str, geometries: tuple[Node, ...] | list[Node] = (),
                 after: tuple[Node, ...] = (), ground: float | None = None,
                 **inputs: Node | None):
        geoms = list(geometries)
        if "geometry" in inputs:
            geoms.insert(0, inputs.pop("geometry"))
        self.INPUTS = {_geometry_port(i): GEOMETRY for i in range(max(len(geoms), 1))}
        super().__init__(name, after, **{_geometry_port(i): g for i, g in enumerate(geoms)},
                         **inputs)
        self.ground = ground

    def geometries(self) -> list[Node]:
        return [g for g in self.inputs.values() if g is not None]

    def run(self, frame: Frame) -> None:
        r = frame.r
        if self.ground is not None:
            r.scene_ground = self.ground
        try:
            self._run(frame)
        finally:
            if self.ground is not None:
                r.scene_ground = None
            # (final review: the faces' layer and picture the shape's
            # `prepare` set are this pass's alone — a solid's draw that
            # raises before the shape's own draw must not leave them stale)
            r._pic = None
            r._face_layer = False

    def _run(self, frame: Frame) -> None:
        r, ctx = frame.r, frame.ctx
        r.scene.ensure(frame.size, frame.samples)
        for unit in range(4):
            r._blank.use(location=unit)
        geometries = self.geometries()
        solids = [g for g in geometries if g.SOLID]
        # plan 33 R: the faces' picture is made before the scene's timer
        # starts — a branch on the faces times its own nodes (queries never
        # nest), and its passes are its own lines on SYSTEM
        rest = [g for g in geometries if not g.SOLID]
        for g in rest:
            g.prepare(frame)
        if not solids:                    # A2's scene pass, byte for byte
            with frame.timed(self.name):
                r.scene.draw_fbo.use()
                ctx.viewport = (0, 0, *frame.size)
                if not geometries:        # (plan 35 B: a wired scene with no geometry)
                    r.clear_scene()
                for g in geometries:
                    g.draw(frame)
                r.scene.resolve()
            return
        with frame.timed(self.name):
            r.scene.draw_fbo.use()
            ctx.viewport = (0, 0, *frame.size)
            r.clear_scene()
        for g in solids:                  # solid first, depth written
            with frame.timed(g.name):
                g.draw(frame)
        with frame.timed(self.name):
            for g in rest:                # then the see-through shape
                g.draw(frame, clear=False)
            r.scene.resolve()

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.r.scene.tex

    def depth(self, frame: Frame) -> moderngl.Texture | None:
        """The scene's depth at the frame's size, resolved out of the
        multisampled target on the first ask of a frame."""
        key = self.name + "#depth"
        if key not in frame.data:
            frame.data[key] = frame.r.scene.depth_texture()
        return frame.data[key]


# ---------------------------------------------------------------- media

class MediaNode(Node):
    """A media channel's picture (plan 32 R): `media.<c>`, the channel's
    texture fitted to the frame (`media.<c>.fit`: cover, contain, stretch)
    by one small pass into a texture of the renderer's
    (`Renderer._media_fit`), premultiplied — so it keeps the `IMAGE` port's
    contract, a colour picture at the frame's size, and any image port may
    read it: an output's, an effect's, the history's, a composite's.

    Made once a frame however many read it, and only when one does: the
    picture is pulled by its first consumer (`image`), so a channel whose
    readers do not run this frame is neither read nor uploaded (the
    channel plays on in `MediaState.poll`). A channel with no picture (an
    empty slot, a file still decoding, a feed lost) is transparent black,
    never a wait.

    `alpha_of` names the `ViewState` field that is its opacity — the
    backdrop's is `backdrop_alpha`, folded into the picture — or None for
    1 (a wire's)."""

    KIND = "media"
    OUTPUT = IMAGE
    MAKES = True

    def __init__(self, name: str, channel: str, after: tuple[Node, ...] = (),
                 alpha_of: str | None = None):
        if channel not in MEDIA_CHANNELS or len(channel) != 1:
            raise ValueError(f"media node {name!r}: channel {channel!r}, one of "
                             f"{MEDIA_CHANNELS}")
        super().__init__(name, after)
        self.channel = channel
        self.alpha_of = alpha_of

    def opacity(self, frame: Frame) -> float:
        """The opacity folded into the picture this frame: the `alpha_of`
        field's, held to 0…1 (1 with none)."""
        if self.alpha_of is None:
            return 1.0
        return min(max(float(getattr(frame.s, self.alpha_of, 1.0)), 0.0), 1.0)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        key = self.name + "#image"
        if key not in frame.data:
            fit = getattr(frame.r, "_media_fit", None)
            with frame.timed(self.name):
                frame.data[key] = (fit(self.channel, frame.size, self.opacity(frame))
                                   if fit is not None else None)
        return frame.data[key]

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """The picture 1:1 into `dst` — or the ground, when there is none
        (a renderer from before the media), so a consumer never shows what
        `dst` held."""
        if self.image(frame) is not None:
            super().paint(frame, dst)
            return
        rect = tuple(dst.viewport)
        dst.use()
        frame.ctx.viewport = rect
        frame.ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha, viewport=rect)


    def reads(self, frame: Frame) -> bool:
        get = getattr(frame.r, "media_texture", None)
        return get is not None and get(self.channel) is not None


def picture(frame: Frame, node: Node, dtype: str = "f1") -> moderngl.Texture | None:
    """`node`'s picture at `frame`'s size as a texture (plan 33 R): the
    one it made, else painted once a frame into a texture of the
    renderer's under its name (`Frame.key`) — what a consumer that binds a
    picture reads (the pattern's layer, a branch under the scene). Plan
    34 D: `dtype` the texture's ("f2", half-float, for a picture that must
    not quantise), kept under its own key beside the RGBA8 one."""
    tex = node.image(frame)
    if tex is not None:
        return tex
    key = node.name + "#picture" + ("" if dtype == "f1" else "." + dtype)
    if key not in frame.data:
        # (the RGBA8 call as it always was: a stand-in renderer's too)
        tex, fbo = (frame.r._frame_target(frame.key(key), frame.size) if dtype == "f1"
                    else frame.r._frame_target(frame.key(key), frame.size, dtype=dtype))
        fbo.viewport = (0, 0, *frame.size)
        node.paint(frame, fbo)
        frame.data[key] = tex
    return frame.data[key]


def _head(node: Node | None, frame: Frame | None = None) -> Node | None:
    """The node a run of effects starts from (`node` itself if no effect)
    — and, given the `frame`, through each switch to the input it picks
    then (plan 33 S; None at off)."""
    while True:
        if isinstance(node, Effect):
            node = node.inputs["image"]
        elif frame is not None and isinstance(node, SwitchNode):
            node = node.selected(frame)
        else:
            return node


class PatternNode(Node):
    """The face pattern as a picture (plan 33 G, R): `pattern`, a wire's
    source — what face 0 shows, the pattern and its media layer over it,
    premultiplied by its intensity (the faces' chain's seed) — and the
    layer's one input, `media` (`pattern.media`, where `view.media` chose a
    channel). `view.media_alpha / scale / mode / amp / rate` stay the
    layer's params.

    `channel`: the channel wired straight into `media` — read raw, as the
    faces always read it (`Renderer._channel_layer`: the texture at its
    own size, no fit pass, no node of its own). Any other picture on
    `media` is a branch, made at its head's own size (`size_for`: a
    channel's texture size, else `FACE_PIC`²) so its aspect is the
    channel's.

    It paints itself straight into any framebuffer (`PAINTS`: the seed
    drawn there, `Renderer._pattern_into`) — so the faces' run from it is
    the faces' chain as it always ran — and makes `FACE_PIC`² for a
    consumer that binds a texture (`image`, `Renderer._pattern_picture`)."""

    KIND = "pattern"
    INPUTS: ClassVar[dict[str, str]] = {"media": IMAGE}
    OUTPUT = IMAGE
    MAKES = True
    PAINTS = True
    TIMED = False                 # its time is the scene's, or its consumer's
    SIZED: ClassVar[frozenset[str]] = frozenset({"media"})

    def __init__(self, name: str = "pattern", after: tuple[Node, ...] = (),
                 channel: str = "", **inputs: Node | None):
        if channel and (channel not in MEDIA_CHANNELS or len(channel) != 1):
            raise ValueError(f"pattern node {name!r}: channel {channel!r}, one of "
                             f"{MEDIA_CHANNELS}")
        super().__init__(name, after, **inputs)
        self.channel = channel

    def size_for(self, port: str, frame: Frame) -> tuple[int, int]:
        if port != "media":
            return super().size_for(port, frame)
        head = _head(self.inputs["media"], frame)
        # plan 34 D: a head with a size of its own (a delay's, a resize's)
        # is made there, as a channel's texture is
        own = head.own_size(frame) if head is not None else None
        if own is not None:
            return tuple(own)
        get = getattr(frame.r, "media_texture", None)
        tex = get(head.channel) if isinstance(head, MediaNode) and get is not None else None
        return tuple(tex.size) if tex is not None else (FACE_PIC, FACE_PIC)

    def layer(self, frame: Frame) -> tuple[moderngl.Texture, bool] | None:
        """What the pattern's media layer draws this frame — (the texture,
        whether its rows are in GL's order) — or None, the layer off: the
        raw channel `channel` names (or a switch picks: plan 33 S), or the
        branch's picture at its head's size (rendered: GL's order). Once a
        frame (the root frame's)."""
        root = frame.root
        key = self.name + "#layer"
        if key not in root.data:
            got = None
            src = self.inputs["media"]
            if float(getattr(root.s, "media_alpha", 1.0)) <= 0.0:
                pass                       # the layer off: nothing read for it
            elif self.channel:
                get = getattr(root.r, "_channel_layer", None)
                got = get(self.channel) if get is not None else None
            elif src is not None:
                # plan 33 S: through a switch, the input it picks — a channel
                # picked is read raw, as one wired straight in (the migrated
                # `view.media` knob draws what the old one drew)
                while isinstance(src, SwitchNode):
                    src = src.selected(root)
                if isinstance(src, MediaNode):
                    get = getattr(root.r, "_channel_layer", None)
                    got = get(src.channel) if get is not None else None
                elif src is not None:
                    at = root.at(self.size_for("media", root))
                    if src.reads(at):
                        tex = picture(at, src)
                        got = (tex, True) if tex is not None else None
            root.data[key] = got
        return root.data[key]

    def image(self, frame: Frame) -> moderngl.Texture | None:
        key = self.name + "#image"
        if key not in frame.data:
            frame.data[key] = frame.r._pattern_picture(frame.s, frame.t, self.layer(frame))
        return frame.data[key]

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        frame.r._pattern_into(dst, frame.s, frame.t, self.layer(frame))


class BackdropNode(Node):
    """The backdrop's node on the GRAPH canvas only (plan 35): the stand-in
    `graphview._stand_in` draws for `backdrop` (`graphview.FRAME_CLASS`),
    never built into a graph and never run. In a wired frame the builder
    makes `backdrop` itself (`_Build._make`): `backdrop.scene` laid over
    `backdrop.image` at `backdrop.alpha` — a channel straight in as the
    plan 32 `MediaNode(alpha_of="backdrop_alpha")`, any other picture a
    `Composite(…, under_alpha_of="backdrop_alpha")`."""

    KIND = "backdrop"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = None
    TIMED = False


class SwitchNode(Node):
    """A switch (plan 33 S, rows 350 and 352): `switch`, `switch.2` …, eight
    picture inputs `in1` … `in8` and one picture out — the input its
    `switch[.n].select` picks this frame (`Frame.selects`: 0 off, k the
    input `in<k>`, R11), passed through at the size its consumer asks. A
    cut: no pass, no texture of its own — `image`, `paint`, `alpha`,
    `depth` and `reads` are the picked input's.

    Off, or picking an input nothing is wired to, it reads nothing
    (`reads` False, `image` None): the faces then show the pattern, the
    backdrop nothing, an output its ground. Only the picked input's branch
    is made: what feeds the others is pulled by no consumer this frame,
    and `Graph.evaluate` runs none of their folds (`Graph.pulled`)."""

    KIND = "switch"
    INPUTS: ClassVar[dict[str, str]] = {p: IMAGE for p in SWITCH_PORTS}
    OUTPUT = IMAGE
    TIMED = False                 # no pass of its own: its time is its input's

    def index(self, frame: Frame) -> int:
        """The input picked this frame, 1–8, or 0 (off; a value out of
        range is off)."""
        sel = getattr(frame, "selects", None) or {}
        try:
            k = int(sel.get(self.name, 0))
        except (TypeError, ValueError):
            return 0
        return k if 1 <= k <= len(SWITCH_PORTS) else 0

    def selected(self, frame: Frame) -> Node | None:
        """The node on the picked input this frame, or None (off, or that
        input unwired)."""
        k = self.index(frame)
        return self.inputs[SWITCH_PORTS[k - 1]] if k else None

    def reads(self, frame: Frame) -> bool:
        src = self.selected(frame)
        return src is not None and src.reads(frame)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        src = self.selected(frame)
        return src.image(frame) if src is not None else None

    def depth(self, frame: Frame) -> moderngl.Texture | None:
        src = self.selected(frame)
        return src.depth(frame) if src is not None else None

    def alpha(self, frame: Frame) -> float:
        src = self.selected(frame)
        return src.alpha(frame) if src is not None else 1.0

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        """Its pick's (plan 34 D): a cut passes the picture as it is made."""
        src = self.selected(frame)
        return src.own_size(frame) if src is not None else None

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """The picked input painted into `dst` — or the ground with none,
        so a consumer never shows what `dst` held (as an empty channel)."""
        src = self.selected(frame)
        if src is not None:
            src.paint(frame, dst)
            return
        rect = tuple(dst.viewport)
        dst.use()
        frame.ctx.viewport = rect
        frame.ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha, viewport=rect)


# ---------------------------------------------------------------- delay

class Delay(Node):
    """A delay's picture (plan 34 D, rows 353–358): `delay`, `delay.2` …,
    what came into its `image` last frame — z⁻¹. No inputs: its picture is
    the read side of a half-float pair the renderer holds under its name
    (`Renderer.delay_pair`, `render.DelayPair`), written last frame by its
    other half, `DelayWrite`, and swapped at the start of this one
    (`Renderer._turn_delays`). So a loop through it is no dependency, and
    no pass ever reads the texture it writes.

    It reads nothing (`reads` False: the faces show the pattern, an output
    its ground) on the first frame and in any frame after one nothing was
    written: strict z⁻¹, never a stale picture. Its own size is the read
    side's (`own_size`, row 357): a consumer of another size gets it
    fitted by cover (`OWN_FIT`, `Renderer._refit`) — painted (`paint`) or,
    for one that binds a texture (`image`), refitted once a frame into a
    half-float target of its own (`<name>#fit`), so the `IMAGE` contract
    (a picture at the frame's size) holds for every consumer."""

    KIND = "delay"
    INPUTS: ClassVar[dict[str, str]] = {}
    OUTPUT = IMAGE
    TIMED = False                 # no pass of its own: its write's is `delay(write)`

    def _read(self, frame: Frame) -> moderngl.Texture | None:
        """The read side's texture while the pair holds a frame, else None
        (getattr: a renderer from before plan 34 has no delays)."""
        get = getattr(frame.r, "delay_pair", None)
        pair = get(self.name) if get is not None else None
        if pair is None or not pair.holds or pair.read is None:
            return None
        return pair.read[0]

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        tex = self._read(frame)
        return tuple(tex.size) if tex is not None else None

    def reads(self, frame: Frame) -> bool:
        return self._read(frame) is not None

    def run(self, frame: Frame) -> None:
        tex = self._read(frame)
        self.said = (f"last frame's · {tex.size[0]}×{tex.size[1]} half-float"
                     if tex is not None else "nothing yet")

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """Last frame's picture laid into `dst` by cover — or the ground
        while it holds none, so a consumer never shows what `dst` held."""
        tex = self._read(frame)
        if tex is not None:
            frame.r._refit(tex, dst, fit=OWN_FIT)
            return
        rect = tuple(dst.viewport)
        dst.use()
        frame.ctx.viewport = rect
        frame.ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha, viewport=rect)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        tex = self._read(frame)
        if tex is not None and tuple(tex.size) == tuple(frame.size):
            return tex
        key = self.name + "#fit"
        if key not in frame.data:
            out, fbo = frame.r._frame_target(frame.key(key), frame.size, dtype="f2")
            fbo.viewport = (0, 0, *frame.size)
            if tex is not None:
                frame.r._refit(tex, fbo, fit=OWN_FIT)
            else:
                fbo.use()
                frame.ctx.viewport = (0, 0, *frame.size)
                frame.ctx.clear(0.0, 0.0, 0.0, 0.0)
            frame.data[key] = out
        return frame.data[key]


class DelayWrite(Node):
    """A delay's other half (plan 34 D): `<delay>(write)`, its `image`
    input painted into the pair's write side once a frame — before the
    capture (`Capture.after`, as each `Shown` end is) — at the size it holds
    (`held`: its input's own size, else the frame's, row 357), cleared to
    transparent black first. An input that reads nothing this frame leaves
    the pair unwritten (R7): next frame the delay reads nothing, as a
    channel with nothing on it does. A size change makes the write side again and
    leaves the read side, so the next frame still reads the one before,
    fitted. Timed: the SYSTEM line `delay(write)` (row 354)."""

    KIND = "delay"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = None
    TIMED = True
    SIZED: ClassVar[frozenset[str]] = frozenset({"image"})

    def __init__(self, name: str, delay: str, image: Node | None = None,
                 after: tuple[Node, ...] = ()):
        super().__init__(name, after, image=image)
        self.delay = delay            # the `Delay` whose pair this writes

    def held(self, frame: Frame) -> tuple[int, int]:
        """The size it holds this frame: its input's own, else the frame's."""
        src = self.inputs["image"]
        own = src.own_size(frame) if src is not None else None
        return tuple(own) if own is not None else tuple(frame.root.size)

    def size_for(self, port: str, frame: Frame) -> tuple[int, int]:
        if port == "image":
            return self.held(frame)
        return super().size_for(port, frame)

    def run(self, frame: Frame) -> None:
        r = frame.r
        get = getattr(r, "delay_pair", None)
        src = self.inputs["image"]
        if get is None or src is None:
            return
        try:
            held = self.held(frame)
            pair = get(self.delay)
            fbo = pair.target(frame.ctx, held)
            fbo.viewport = (0, 0, *held)
            fbo.use()
            frame.ctx.viewport = (0, 0, *held)
            frame.ctx.clear(0.0, 0.0, 0.0, 0.0)
            at = frame if held == tuple(frame.size) else frame.at(held)
            # (R7, the controller 2026-10-24: an input that read nothing
            # leaves the pair unwritten — next frame the delay reads nothing
            # and the faces fall back to the pattern, plan 33's rule)
            if src.reads(at):
                with frame.timed(self.name):
                    src.paint(at, fbo)
                pair.wrote = True
            self.said = ""
        except Exception as e:  # noqa: BLE001 — a delay must not take the frame down
            # (nothing written: next frame the delay reads nothing)
            self.said = f"{self.name}: {type(e).__name__}: {e}"[:160]
            rebind = getattr(r, "_rebind", None)
            if rebind is not None:
                rebind(frame.target, frame.vp)


# ---------------------------------------------------------------- the look-back's frames

class EchoNode(Node):
    """A look-back's echo (plan 34 E, rows 360–363; plan 36 T4: one of its
    outputs, `lookback.echo.<k>`, `lookback.2.echo.<k>` — a pin): the k-th
    newest commit of *that* look-back's ring (`Lookback.echo_slot`), its
    slot's rect of the atlas cropped, the samples clamped half a texel
    inside it so no neighbour bleeds. No inputs: read before this frame's
    capture writes (every consumer runs before the capture: a wired
    output's end, a delay's write, the faces in the scene), so no loop
    runs through one. Its own size is the ring's echo size while it reads;
    a consumer of another size gets it fitted by cover (`OWN_FIT`,
    `Renderer._refit`) — painted, or for one that binds a texture refitted
    once a frame into a half-float target of its own (`<name>#fit`), as a
    delay's is. It reads nothing before k commits since the ring was made,
    the frame a `dream.res` change makes it again, or with no ring
    (`Lookback.ring_error`); the faces then show the pattern, an output its
    ground, an effect transparent black. What it holds is what its look-back
    records, 8-bit, at `dream.res` on its short side, every `dream.gap`
    seconds."""

    KIND = "echo"
    INPUTS: ClassVar[dict[str, str]] = {}
    OUTPUT = IMAGE
    TIMED = False                 # its one pass is its consumer's

    def __init__(self, name: str, k: int, after: tuple[Node, ...] = (),
                 lookback: str = LOOKBACK):
        super().__init__(name, after)
        self.k = k                    # 1 the newest commit, MAX_ECHOES the oldest
        self.lookback = lookback      # whose ring (plan 36 T4)

    def ring(self, frame: Frame):
        return frame.r.ring(self.lookback)

    def _slot(self, frame: Frame) -> int | None:
        """The slot this frame reads: the one `run` took before the capture
        (fix round 1: a consumer that paints after the capture — an
        output's `hands` — still reads last frame's commit, not one newer),
        or None when this frame's capture has written over it since (the
        oldest slot, re-used). Without a `run` this frame, the slot now."""
        lb = self.ring(frame)
        took = frame.root.data.get(self.name + "#slot")
        if took is None:
            return lb.echo_slot(self.k)
        slot, at = took
        if slot is not None and getattr(lb, "wrote", None) == (at + 1, slot):
            return None
        return slot

    def _src(self, frame: Frame) -> tuple | None:
        """(texture, crop, clamp) this frame, or None while it reads nothing."""
        lb = self.ring(frame)
        slot = self._slot(frame)
        # (fix round 2: a slot taken before a capture whose remake failed —
        # the ring released, `atlas` None — reads nothing, R7)
        if slot is None or lb.atlas is None:
            return None
        eh = max(int(lb.echo[1]), 1)
        crop = (0.0, slot / MAX_ECHOES, 1.0, 1.0 / MAX_ECHOES)
        clamp = (0.0, (slot + 0.5 / eh) / MAX_ECHOES, 1.0, (slot + 1 - 0.5 / eh) / MAX_ECHOES)
        return lb.atlas, crop, clamp

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        return tuple(self.ring(frame).echo) if self._src(frame) is not None else None

    def reads(self, frame: Frame) -> bool:
        return self._src(frame) is not None

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        got = self._src(frame)
        if got is not None:
            tex, crop, clamp = got
            frame.r._refit(tex, dst, crop=crop, fit=OWN_FIT, clamp=clamp)
            return
        rect = tuple(dst.viewport)
        dst.use()
        frame.ctx.viewport = rect
        frame.ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha, viewport=rect)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        key = self.name + "#fit"
        if key not in frame.data:
            out, fbo = frame.r._frame_target(frame.key(key), frame.size, dtype="f2")
            fbo.viewport = (0, 0, *frame.size)
            got = self._src(frame)
            if got is not None:
                tex, crop, clamp = got
                frame.r._refit(tex, fbo, crop=crop, fit=OWN_FIT, clamp=clamp)
            else:
                fbo.use()
                frame.ctx.viewport = (0, 0, *frame.size)
                frame.ctx.clear(0.0, 0.0, 0.0, 0.0)
            frame.data[key] = out
        return frame.data[key]

    def run(self, frame: Frame) -> None:
        lb = self.ring(frame)
        slot = lb.echo_slot(self.k)
        # (before the capture: every consumer of an echo is in `Capture.after`)
        frame.root.data[self.name + "#slot"] = (slot, lb.frame)
        if slot is None:
            if lb.atlas is None and lb.ring_error:
                self.said = lb.ring_error
            elif lb.remaking():
                self.said = "the look-back is remaking its frames (resolution changed)"
            else:
                self.said = f"not held yet: the ring holds {lb.held()} of {MAX_ECHOES}"
            return
        w, h = lb.echo
        gap = max(float(lb.state.gap), 0.0)
        every = "every frame" if gap <= 0.0 else f"every {gap:.2f} s"
        self.said = f"{w}×{h} · {every} · {_ring_holds(frame, self.lookback)}"


def _ring_holds(frame: Frame, lookback: str = LOOKBACK) -> str:
    """What look-back `lookback` records this frame, in words (plan 34 E,
    row 363; plan 36 T4: what is wired into its `image`): the scene, with
    the hands' layer laid on, or over the backdrop."""
    g = frame.graph
    cap = g.nodes.get(capture_name(lookback)) if g is not None else None
    src = cap.inputs.get("image") if cap is not None else None
    if isinstance(src, Composite) and isinstance(src.inputs.get("over"), HandsLayer):
        return "the scene + hands"
    if isinstance(src, Composite) and src.name == BACKDROP:
        return "the scene + backdrop"
    return "the scene" if isinstance(src, Scene) else (
        src.name if src is not None else "nothing")


class DreamNode(Node):
    """`dream` (plan 36 T4, W4): picture in → dreamed picture out. Its
    `image` goes to the dream worker at its own cadence — every frame while
    `dream.on`, downsampled to `dream.res` and read back once
    (`lookback.Dreamer.submit`) — and its picture is that input with the
    worker's result `D` laid over at `dream.mix`, re-hued, (de)saturated,
    tinted (`dream.hue`, `sat`, `tint` …) and graded (`dream.darken`,
    `contrast`). `dream.on` off passes the input through untouched and
    submits nothing, so the worker sleeps; so does a dream with no worker,
    or before its first result has landed. It pulls its own results (no
    look-back is needed anywhere). One live dream at a time (D2): the
    graph refuses a wire on a second."""

    KIND = "dream"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = IMAGE

    def passes(self, frame: Frame) -> bool:
        """Whether this frame's picture is its input, untouched (`Dreamer.shows`)."""
        return not frame.r.dreamer.shows()

    def run(self, frame: Frame) -> None:
        d = frame.r.dreamer
        if not d.state.on:
            d.idle()
            self.said = "off: the picture passes through, the worker idle"
            return
        d.pull()
        src = self.inputs["image"]
        if src is not None and d.wants_input():
            tex = picture(frame, src)
            if tex is not None:
                with frame.timed(self.name):
                    d.submit(tex, *frame.size)
        if d.ring_error:
            self.said = d.ring_error
        elif d.source is None:
            self.said = "no dream worker: the picture passes through"
        elif d.dream_frame < 0:
            self.said = "waiting for the dream worker"
        else:
            w, h = d.size
            self.said = f"{w}×{h} · the dream worker's, a frame or two late"

    def reads(self, frame: Frame) -> bool:
        src = self.inputs["image"]
        return (not self.passes(frame)) or (src is not None and src.reads(frame))

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        src = self.inputs["image"]
        return src.own_size(frame) if self.passes(frame) and src is not None else None

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        src = self.inputs["image"]
        if self.passes(frame):
            if src is not None:
                src.paint(frame, dst)
                return
            rect = tuple(dst.viewport)
            dst.use()
            frame.ctx.viewport = rect
            frame.ctx.clear(0.0, 0.0, 0.0, 0.0, viewport=rect)
            return
        under = picture(frame, src) if src is not None else None
        frame.r.dreamer.lay(under, dst)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        src = self.inputs["image"]
        if self.passes(frame):
            return src.image(frame) if src is not None else None
        if self.name not in frame.data:
            tex, fbo = frame.r._frame_target(frame.key(self.name), frame.size, dtype="f2")
            fbo.viewport = (0, 0, *frame.size)
            self.paint(frame, fbo)
            frame.data[self.name] = tex
        return frame.data[self.name]


def _trail_of(node: Node | None, frame: Frame) -> History | None:
    """The look-back whose trail `node` is this frame (plan 36 T4): the
    look-back itself, or a dream passing it through (off, no worker, no
    result yet) — what an "add" composite lays on in one pass with its
    `under` (`Composite.paint`), the one-shader look-back's bytes."""
    while isinstance(node, DreamNode) and node.passes(frame):
        node = node.inputs["image"]
    return node if isinstance(node, History) else None


# ---------------------------------------------------------------- the resize

def resize_size(side: int, aspect: str, src: tuple[int, int]) -> tuple[int, int]:
    """A resize's own size (plan 34 Z, row 368): `side` square, or `src`'s
    orientation with its long side `side` and its short side in proportion
    (never under 1 pixel)."""
    side = int(side)
    if aspect == "square":
        return side, side
    w, h = int(src[0]), int(src[1])
    long, short = max(w, h, 1), min(w, h)
    other = max(1, round(side * short / long))
    return (side, other) if w >= h else (other, side)


def _pick(values: tuple, i: Any) -> Any:
    """`values[i]`, held into range (a value off either end is that end's)."""
    try:
        k = int(i)
    except (TypeError, ValueError):
        k = 0
    return values[min(max(k, 0), len(values) - 1)]


# (the values of a resize with none this frame: read, never written)
_RESIZE_DEFAULT = ResizeState()


class ResizeNode(Node):
    """A resize (plan 34 Z, row 368): `resize`, `resize.2` …, its `image`
    input's crop (`crop_*`, a normalised rect from the top left) made at a
    size of its own (`size` the long side, `aspect` the input's or square:
    `resize_size`) by `fit` and `filter` (`ViewState.resize`, read as
    `Frame.resizes`: values, never a rebuild). So what comes after it — a
    delay's pair (`DelayWrite.held`), an effect's pool (`Effect.own_size`)
    — runs at that size: the owner's "no 1080p buffer into the faces for
    no reason". It breaks "the consumer decides the size" on purpose (row
    368).

    Made once a frame (`made`: a half-float target of the renderer's keyed
    `(<name>#own, size)`, so a size step reallocates once each way and the
    size left is kept for `SIZED_KEEP_FRAMES`); a consumer of another size
    gets it fitted by cover (`OWN_FIT`) — painted, or for one that binds a
    texture refitted once a frame into `<name>#fit`, as a delay's is. A
    crop past the input's edge is transparent black (`REFIT_FS`); a linear
    reduction of more than 2× samples mipmaps. It reads what its input
    reads: with nothing, the faces show the pattern, an output its ground."""

    KIND = "resize"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = IMAGE
    TIMED = True

    def __init__(self, name: str, image: Node | None = None, after: tuple[Node, ...] = ()):
        super().__init__(name, after, image=image)

    def state(self, frame: Frame) -> ResizeState:
        """This frame's values (`Frame.resizes`), else the defaults."""
        return (getattr(frame.root, "resizes", None) or {}).get(self.name) or _RESIZE_DEFAULT

    def size_for(self, port: str, frame: Frame) -> tuple[int, int]:
        """What `image` is made at: its input's own size, else the frame's."""
        if port == "image":
            src = self.inputs["image"]
            own = src.own_size(frame) if src is not None else None
            return tuple(own) if own is not None else tuple(frame.root.size)
        return super().size_for(port, frame)

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        st = self.state(frame)
        return resize_size(_pick(RESIZE_SIDES, st.size), _pick(RESIZE_ASPECTS, st.aspect),
                           self.size_for("image", frame))

    def reads(self, frame: Frame) -> bool:
        src = self.inputs["image"]
        return src is not None and src.reads(frame)

    @staticmethod
    def _crop(st: ResizeState) -> tuple[float, float, float, float]:
        """The crop as a GL-uv rect (x0, y0, w, h): `crop_y` runs down."""
        w, h = float(st.crop_w), float(st.crop_h)
        return float(st.crop_x) - w / 2, 1.0 - float(st.crop_y) - h / 2, w, h

    def made(self, frame: Frame) -> moderngl.Texture | None:
        """The picture at its own size, made once a frame (the root's data)
        — None while the input reads nothing."""
        root = frame.root
        key = self.name + "#own"
        if key in root.data:
            return root.data[key]
        root.data[key] = None
        src = self.inputs["image"]
        if src is None or not src.reads(frame):
            return None
        r = frame.r
        st = self.state(frame)
        size = self.size_for("image", frame)
        at_in = root if size == tuple(root.size) else root.at(size)
        own = self.own_size(frame)
        # (the input drawn on demand first, outside the timer: its nodes
        # time themselves, and `resize`'s line is its own refit alone)
        tex = src.image(at_in)
        if tex is None:
            tex = picture(at_in, src, dtype="f2")
        if tex is None:
            return None
        crop = self._crop(st)
        filt = _pick(RESIZE_FILTERS, st.filter)
        fit = _pick(range(len(RESIZE_FITS)), st.fit)
        mip = filt == "linear" and (crop[2] * tex.size[0] / own[0] > 2.0
                                    or crop[3] * tex.size[1] / own[1] > 2.0)
        out, fbo = r._frame_target((key, own), own, dtype="f2")
        fbo.viewport = (0, 0, *own)
        with frame.timed(self.name):
            r._refit(tex, fbo, crop=crop, fit=fit, filter=filt, mip=mip)
        root.data[key] = out
        return out

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """Its picture laid into `dst` by cover with its filter — or the
        ground while it reads nothing, so a consumer never shows what `dst`
        held."""
        tex = self.made(frame)
        if tex is not None:
            frame.r._refit(tex, dst, fit=OWN_FIT,
                           filter=_pick(RESIZE_FILTERS, self.state(frame).filter))
            return
        rect = tuple(dst.viewport)
        dst.use()
        frame.ctx.viewport = rect
        frame.ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha, viewport=rect)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        """Its picture at the frame's size (the `IMAGE` contract): the one it
        made when that is its own, else refitted once a frame (`#fit`)."""
        tex = self.made(frame)
        if tex is None or tuple(tex.size) == tuple(frame.size):
            return tex
        key = self.name + "#fit"
        if key not in frame.data:
            out, fbo = frame.r._frame_target(frame.key(key), frame.size, dtype="f2")
            fbo.viewport = (0, 0, *frame.size)
            frame.r._refit(tex, fbo, fit=OWN_FIT,
                           filter=_pick(RESIZE_FILTERS, self.state(frame).filter))
            frame.data[key] = out
        return frame.data[key]

    def run(self, frame: Frame) -> None:
        """What it says (GRAPH's summary, Global Constraints' words)."""
        if not self.reads(frame):
            self.said = "its input reads nothing"
            return
        st = self.state(frame)
        w, h = self.own_size(frame)
        said = f"{w}×{h} · {_pick(RESIZE_FITS, st.fit)} · {_pick(RESIZE_FILTERS, st.filter)}"
        cw, ch = float(st.crop_w), float(st.crop_h)
        if cw < 1.0 or ch < 1.0:
            said += f" · crop {cw:.0%}×{ch:.0%}"
        self.said = said


# ---------------------------------------------------------------- the masks (plan 39 T2)

# (the values of a matte with none this frame: read, never written)
_MATTE_DEFAULT = MatteState()


class MatteNode(Node):
    """A matte (plan 39 T2, W2): `matte`, `matte.2` …, its `image` input
    made a mask — a one-channel 8-bit texture at the input's own size (its
    own size, else the frame's): from the picture's brightness, its own
    coverage (how a cut picture becomes a mask again) or its closeness to a
    keyed hue (`matte.from`), passing at `key`, a `soft` edge about it,
    `invert`, and a `feather` blur (two separable passes inside the node,
    only when > 0) — `ViewState.mattes`, read as `Frame.mattes`: values,
    never a rebuild. The passes are the renderer's (`masks.MaskPasses`,
    `Renderer.mask_passes`).

    Made once a frame on the first ask (`made`, the root's data), into a
    frame target keyed `(<name>#mask, size)`; a mask consumer
    (`lookback.cover`) binds it as it is, a picture consumer gets it through
    the promotion (`MaskPicture`, the build's). While its input reads
    nothing it makes no mask; fed by nothing it is not built and says so."""

    KIND = "matte"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = MASK
    TIMED = True

    def __init__(self, name: str, image: Node | None = None, after: tuple[Node, ...] = ()):
        super().__init__(name, after, image=image)

    def state(self, frame: Frame) -> MatteState:
        """This frame's values (`Frame.mattes`), else the defaults."""
        return frame.mattes.get(self.name) or _MATTE_DEFAULT

    def size_for(self, port: str, frame: Frame) -> tuple[int, int]:
        """What `image` is made at: its input's own size, else the frame's."""
        if port == "image":
            src = self.inputs["image"]
            own = src.own_size(frame) if src is not None else None
            return tuple(own) if own is not None else tuple(frame.root.size)
        return super().size_for(port, frame)

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        """Its input's own size (W2's "own size: its input's"), passed
        through as an effect's is — None when the input has none (the mask
        is then at the frame's size). A mask port is handed it refitted to
        the frame (`image`), a picture port promoted (`MaskPicture`)."""
        src = self.inputs["image"]
        return src.own_size(frame) if src is not None else None

    def reads(self, frame: Frame) -> bool:
        src = self.inputs["image"]
        return src is not None and src.reads(frame)

    def made(self, frame: Frame) -> moderngl.Texture | None:
        """The mask, made once a frame (the root's data) at its input's
        size (`size_for`) — None while the input reads nothing."""
        root = frame.root
        key = self.name + "#mask"
        if key in root.data:
            return root.data[key]
        root.data[key] = None
        src = self.inputs["image"]
        if src is None or not src.reads(frame):
            return None
        size = self.size_for("image", frame)
        at_in = root if size == tuple(root.size) else root.at(size)
        # (the input drawn on demand first, outside the timer: its nodes
        # time themselves, and the matte's line is its own passes alone)
        tex = src.image(at_in)
        if tex is None:
            tex = picture(at_in, src)
        if tex is None:
            return None
        st = self.state(frame)
        with frame.timed(self.name):
            out = frame.r.mask_passes().matte(
                tex, key, size, source=_pick(range(len(MATTE_FROM)), st.source),
                level=float(st.key), soft=float(st.soft), invert=bool(st.invert),
                feather=float(st.feather), hue=float(st.hue), sat=float(st.sat))
        root.data[key] = out
        return out

    def native(self, frame: Frame) -> moderngl.Texture | None:
        """The mask at its own size, as made: what the promotion (and T3's
        cut) fits by cover themselves."""
        return self.made(frame)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        """Its mask as a mask port binds it (the `MASK` contract: one
        channel at the frame's size — `lookback.cover` fetches it 1:1 by
        the frame's pixel): the mask itself when it is that size, else
        refitted by cover once a frame into `<name>#fit` (one R8 pass,
        `MaskPasses.fit`), so it lands where its promoted picture shows it."""
        return mask_port(self, frame)

    def run(self, frame: Frame) -> None:
        """What it says (GRAPH's summary)."""
        if not self.reads(frame):
            self.said = "its input reads nothing: no mask"
            return
        st = self.state(frame)
        w, h = self.size_for("image", frame)
        said = f"{w}×{h} mask · {_pick(MATTE_FROM, st.source)} at {float(st.key):.2f}"
        if float(st.soft) > 0.0:
            said += f" ± {float(st.soft):.2f}"
        if st.invert:
            said += " · inverted"
        feather = min(max(float(st.feather), 0.0), MATTE_FEATHER)
        if feather > 0.0:
            said += f" · feather {feather:g} px"
        self.said = said


class MaskPicture(Node):
    """A mask read as a picture (plan 39 T2, W1, decision 2): what a mask
    wired into a picture port is to that port — white (premultiplied,
    opaque) where it passes, black elsewhere, at the consumer's size, the
    mask fitted by cover as an own-sized node's picture is
    (`masks.PROMOTE_FS`). The build makes one per mask node a picture port
    reads (`_Build._taken`), named `<mask>(picture)`: the drawn wire is the
    mask's, the promotion only how the port reads it — no node on GRAPH,
    no edge of its own. One way only: a picture into a mask port is refused
    (`PICTURE_INTO_MASK`). While the mask reads nothing it paints the
    ground, as a resize reading nothing does."""

    KIND = "mask→picture"
    INPUTS: ClassVar[dict[str, str]] = {"mask": MASK}
    OUTPUT = IMAGE
    TIMED = False             # (one cheap pass; the mask's maker times its own)

    def __init__(self, name: str, mask: Node | None = None, after: tuple[Node, ...] = ()):
        super().__init__(name, after, mask=mask)

    def reads(self, frame: Frame) -> bool:
        m = self.inputs["mask"]
        return m is not None and m.reads(frame)

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        m = self.inputs["mask"]
        # (the mask at its own size where its maker keeps one — `native` —
        # fitted by cover here, once, never refitted twice; plan 39 T4: read
        # upside down when its rows are top first — `mask_of`'s flag)
        tex, flip = mask_of(m, frame) if m is not None else (None, False)
        if tex is not None:
            frame.r.mask_passes().promote(tex, dst, flip=flip)
            return
        rect = tuple(dst.viewport)
        dst.use()
        frame.ctx.viewport = rect
        frame.ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha, viewport=rect)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        """The picture at the frame's size, painted once a frame (`#picture`)."""
        key = self.name + "#picture"
        if key not in frame.data:
            tex, fbo = frame.r._frame_target(frame.key(key), frame.size)
            fbo.viewport = (0, 0, *frame.size)
            self.paint(frame, fbo)
            frame.data[key] = tex
        return frame.data[key]


def mask_of(node: Node, frame: Frame) -> tuple[moderngl.Texture | None, bool]:
    """Mask node `node`'s mask as a pass that fits it by cover reads it
    (plan 39 T3): its mask at its own size where its maker keeps one
    (`native`: a matte's), else what a mask port binds (`image`); and
    whether its rows are top first — the flip flag. A mask a GL pass made
    has its first row at the bottom, as every texture here; one uploaded
    from a CPU array as it is (plan 39 T4's segment worker) has its top row
    first, and its maker says so by a method `rows_top_first(frame) -> bool`
    (none: False). `masks.MaskPasses.cut(flip=…)` reads such a mask upside
    down, so it lands the right way up."""
    native = getattr(node, "native", None)
    tex = native(frame) if native is not None else node.image(frame)
    if tex is None:
        return None, False
    top = getattr(node, "rows_top_first", None)
    return tex, bool(top(frame)) if top is not None else False


def mask_port(node: Node, frame: Frame) -> moderngl.Texture | None:
    """Mask node `node`'s mask as a mask port binds it (the `MASK`
    contract: one channel at the frame's size, its first row at the bottom
    — `lookback.cover` fetches it 1:1 by the frame's pixel): its own mask
    (`mask_of`) when that is the frame's size and the right way up, else
    refitted by cover — and turned, when its rows are top first (plan 39
    T4) — once a frame into `<name>#fit` (one R8 pass, `MaskPasses.fit`)."""
    tex, flip = mask_of(node, frame)
    if tex is None or (tuple(tex.size) == tuple(frame.size) and not flip):
        return tex
    key = node.name + "#fit"
    if key not in frame.data:
        frame.data[key] = frame.r.mask_passes().fit(tex, frame.key(key), frame.size, flip=flip)
    return frame.data[key]


# (the values of a cut with none this frame: read, never written)
_CUT_DEFAULT = CutState()


class CutNode(Node):
    """A cut (plan 39 T3, W3; decisions 1 and 6): `cut`, `cut.2` …, its
    `image` cut by the mask on its `mask` port — where the mask passes the
    picture, elsewhere cut away to transparent black (premultiplied, so
    colour and alpha go together): on a `composite.over` what is under
    shows through, on an output the ground. `cut.amount` how far (1 to
    nothing, 0.5 the cut part dimmed by half), `cut.invert` keeps the hole
    and cuts the rest (`ViewState.cuts`, read as `Frame.cuts`: values,
    never a rebuild). The one pass is the renderer's (`masks.MaskPasses.cut`,
    `CUT_FS`); the mask is sampled bilinearly at the picture's size, fitted
    by cover as its promoted picture is (`mask_of`: the maker's own-size
    mask, and the flip flag for a mask whose rows are top first).

    Its own size is its picture's (an own-sized input's: the cut made
    there, then fitted into a consumer of another size by cover, as an
    effect's is). No mask wired — or a mask making nothing this frame (a
    matte reading nothing) — and it is its picture through, untouched: no
    pass, no texture of its own (`image`, `paint` the input's). Made once a
    frame on the first ask (`made`, into a frame target `<name>#cut`), so
    a consumer never reads what it writes. Fed nothing on `image`, it is
    not built and says so."""

    KIND = "cut"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE, "mask": MASK}
    OUTPUT = IMAGE
    TIMED = True

    def __init__(self, name: str, image: Node | None = None, mask: Node | None = None,
                 after: tuple[Node, ...] = ()):
        super().__init__(name, after, image=image, mask=mask)

    def state(self, frame: Frame) -> CutState:
        """This frame's values (`Frame.cuts`), else the defaults."""
        return frame.cuts.get(self.name) or _CUT_DEFAULT

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        """Its picture's (W3's "at the picture's size"): passed through as
        an effect's is — None when its input has none."""
        src = self.inputs["image"]
        return src.own_size(frame) if src is not None else None

    def reads(self, frame: Frame) -> bool:
        src = self.inputs["image"]
        return src is not None and src.reads(frame)

    def mask(self, frame: Frame) -> tuple[moderngl.Texture | None, bool]:
        """The mask it cuts by this frame and its flip flag (`mask_of`) —
        (None, False) with none wired, or one reading or making nothing."""
        m = self.inputs["mask"]
        if m is None or not m.reads(frame):
            return None, False
        return mask_of(m, frame)

    def cuts(self, frame: Frame) -> bool:
        """Whether it cuts this frame: its picture reads and its mask makes
        one. Else it is its picture through, untouched."""
        return self.reads(frame) and self.mask(frame)[0] is not None

    def made(self, frame: Frame) -> moderngl.Texture | None:
        """The cut picture at `frame`'s size, made once a frame (`frame`'s
        data — an own-sized one's at its size, `Frame.at`) into an RGBA8
        frame target `<name>#cut` — None when it does not cut."""
        key = self.name + "#cut"
        if key in frame.data:
            return frame.data[key]
        frame.data[key] = None
        if not self.cuts(frame):
            return None
        src = self.inputs["image"]
        # (the picture and the mask made on demand first, outside the timer:
        # their nodes time themselves, and the cut's line is its pass alone)
        tex = src.image(frame)
        if tex is None:
            tex = picture(frame, src)
        mask, flip = self.mask(frame)
        if tex is None or mask is None:
            return None
        st = self.state(frame)
        out, fbo = frame.r._frame_target(frame.key(key), frame.size)
        fbo.viewport = (0, 0, *frame.size)
        with frame.timed(self.name):
            frame.r.mask_passes().cut(tex, mask, fbo, invert=bool(st.invert),
                                      amount=min(max(float(st.amount), 0.0), 1.0), flip=flip)
        frame.data[key] = out
        return out

    def _own(self, frame: Frame) -> tuple[int, int] | None:
        """Its own size when that is not `frame`'s, else None."""
        own = self.own_size(frame)
        return tuple(own) if own is not None and tuple(own) != tuple(frame.size) else None

    def _at_own(self, frame: Frame, own: tuple[int, int]) -> moderngl.Texture | None:
        root = frame.root
        return self.made(root if own == tuple(root.size) else root.at(own))

    def image(self, frame: Frame) -> moderngl.Texture | None:
        """Its picture at the frame's size (the `IMAGE` contract): the
        input's own while it does not cut; else the cut made here, or made
        at its own size and refitted once a frame (`#fit`, half-float)."""
        src = self.inputs["image"]
        if not self.cuts(frame):
            return src.image(frame) if src is not None else None
        own = self._own(frame)
        if own is None:
            return self.made(frame)
        key = self.name + "#fit"
        if key not in frame.data:
            tex = self._at_own(frame, own)
            out, fbo = frame.r._frame_target(frame.key(key), frame.size, dtype="f2")
            fbo.viewport = (0, 0, *frame.size)
            if tex is not None:
                frame.r._refit(tex, fbo, fit=OWN_FIT)
            else:
                fbo.use()
                frame.ctx.viewport = (0, 0, *frame.size)
                frame.ctx.clear(0.0, 0.0, 0.0, 0.0)
            frame.data[key] = out
        return frame.data[key]

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """Its picture into `dst`: the input painted as it is while it does
        not cut; else the cut 1:1, or laid in by cover from its own size."""
        src = self.inputs["image"]
        if src is None:
            return
        if not self.cuts(frame):
            src.paint(frame, dst)
            return
        own = self._own(frame)
        if own is not None:
            tex = self._at_own(frame, own)
            if tex is not None:
                frame.r._refit(tex, dst, fit=OWN_FIT)
                return
        super().paint(frame, dst)

    def run(self, frame: Frame) -> None:
        """What it says (GRAPH's summary)."""
        m = self.inputs["mask"]
        if not self.reads(frame):
            self.said = "its picture reads nothing"
        elif m is None:
            self.said = "no mask wired: its picture through, whole"
        elif not m.reads(frame):
            self.said = f"{m.name} makes nothing: its picture through, whole"
        else:
            st = self.state(frame)
            said = f"cut by {m.name}"
            if st.invert:
                said += " · inverted"
            amount = min(max(float(st.amount), 0.0), 1.0)
            if amount < 1.0:
                said += f" · amount {amount:.2f}"
            self.said = said


# (the values of a segment with none this frame: read, never written)
_SEGMENT_DEFAULT = SegmentState()


class SegmentNode(Node):
    """A segment (plan 39 T4, W4; decisions 3, 4, 5): `segment`,
    `segment.2` …, its `image` cut into a foreground and a background by a
    matte. The node itself is the matte (`OUTPUT` a mask: the `segment.mask`
    pin); its pictures are two pin nodes over it (`SegmentPin`:
    `segment.fg`, the input where the matte passes, cut away elsewhere;
    `segment.bg`, the reverse). `ViewState.segments`, read as
    `Frame.segments`, holds its values (never a rebuild).

    `segment.mode`:
    - **person** — a model's matte, made off the frame thread by the
      renderer's worker for this node (`Renderer.segmenter(name)`, a
      `segment.SegmentWorker`, reached duck-typed: graph.py never imports
      segment.py). Once a frame the newest result is pulled into the node's
      mask texture (uploaded only when its index moved; `segment.smooth`
      keeps that much of the last one), then the input is submitted — the
      channel's own CPU frame when the wire comes straight from a channel
      whose newest frame has pixels and is fitted by cover (the shortcut: no
      readback; it changes where the worker reads, never what is wired),
      else the picture downsampled and read back once (`MaskPasses.
      readback`, the dream's path) — and only when the input moved (a
      channel's frame id; any other picture every frame), and only while
      the worker has nothing waiting. The matte is the worker's array as
      it is, rows top first: `rows_top_first` says so and every pass that
      samples it turns it (`mask_of`).
    - **motion** — no worker: a background model in GLSL on the frame
      thread (`masks.MaskPasses.motion` / `learn` over the renderer's
      half-float pair for this node, `Renderer.motion_pair`): the matte
      passes where the picture differs from the background past
      `segment.sense`, and the background learns the picture at a rate
      that fades a still thing in over `segment.learn` seconds.
    - **subject** — declared in the choice, refused in words (a later build).

    `segment.feather` blurs the matte (`MaskPasses.feather`). Before the
    first matte, with `segment.on` off, with no worker (a renderer given no
    `segment_cfg`: the hold's preview), on a worker's error, or with an
    input reading nothing, it makes no matte: `fg` is the input whole,
    `bg` nothing, `mask` nothing — and off, the worker is not fed (it
    sleeps). Fed nothing on `image`, it is not built and says so."""

    KIND = "segment"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = MASK
    TIMED = True

    def __init__(self, name: str, image: Node | None = None, after: tuple[Node, ...] = ()):
        super().__init__(name, after, image=image)
        self._raw = None              # the texture the newest result went into …
        self._uploaded = -1           # … and that result's index
        self._prev: np.ndarray | None = None    # the smoothed matte, for the next
        self._feathered = None        # (raw texture, index, radius, out) last blurred
        self._fed: tuple | None = None          # what was last submitted (moved?)
        self._n = 0                   # the submits' own count
        self._buf: np.ndarray | None = None     # the readback's array
        self._worker = None           # the worker the results came from
        self.taken = {"shortcut": 0, "readback": 0}   # each input path's submits

    def state(self, frame: Frame) -> SegmentState:
        """This frame's values (`Frame.segments`), else the defaults."""
        return frame.segments.get(self.name) or _SEGMENT_DEFAULT

    def mode(self, frame: Frame) -> str:
        return _pick(SEGMENT_MODES, self.state(frame).mode)

    def quality(self, frame: Frame) -> str:
        return _pick(SEGMENT_QUALITY, self.state(frame).quality)

    def rows_top_first(self, frame: Frame) -> bool:
        """The flip flag (`mask_of`): a worker's matte is its array as it
        is, top row first; motion's a GL pass's."""
        return self.mode(frame) != "motion"

    # ---- the matte, once a frame ----

    def matte(self, frame: Frame) -> moderngl.Texture | None:
        """This frame's matte at its own size (the root's data: made on the
        first ask, `run` or a consumer), or None when it makes none — with
        the words it says (`said`)."""
        root = frame.root
        key = self.name + "#matte"
        if key not in root.data:
            root.data[key] = None
            tex, said = self._make(root)
            root.data[key] = tex
            self.said = said
        return root.data[key]

    def _make(self, frame: Frame) -> tuple[moderngl.Texture | None, str]:
        st = self.state(frame)
        mode = self.mode(frame)
        src = self.inputs["image"]
        whole = "its picture through, whole"
        if not st.on:
            return None, f"off: {whole}, the worker idle"
        if mode == "subject":
            return None, (f"subject is not in this build: {whole} (person or motion "
                          "for now)")
        if src is None or not src.reads(frame):
            if isinstance(src, MediaNode):
                return None, f"no frame on channel {src.channel}: {whole}"
            return None, f"its picture reads nothing: {whole}"
        if mode == "motion":
            return self._motion(frame, st)
        worker = getattr(frame.r, "segmenter", lambda name: None)(self.name)
        if worker is None:
            return None, f"no worker in the preview: {whole}"
        if worker is not self._worker:
            self._worker, self._uploaded, self._prev, self._fed = worker, -1, None, None
        raw = self._pull(frame, worker, st)
        with frame.timed(self.name):
            self._feed(frame, worker, src)
        if worker.error:
            return None, f"{worker.said()}: {whole}"
        if raw is None:
            return None, f"{worker.said()}: {whole} until the first matte"
        return self._feather(frame, raw, self._uploaded, st), worker.said()

    def _pull(self, frame: Frame, worker, st: SegmentState) -> moderngl.Texture | None:
        """The newest result in the node's mask texture (`<name>#mask`, one
        channel at the result's size, rows top first as the array's):
        written only when its index moved (or the texture is new) —
        smoothed against the last by `segment.smooth`. None before the first."""
        got = worker.latest()
        if got is None:
            return None
        mask, index, size = got
        size = (int(size[0]), int(size[1]))
        tex, _ = frame.r._frame_target(self.name + "#mask", size, components=1)
        if index != self._uploaded or tex is not self._raw:
            # (the smoothed matte is kept in float: re-quantised each result,
            # a smooth near 1 would stall short of the new value for good —
            # 1 itself would never move, so it is held under)
            k = min(max(float(st.smooth), 0.0), 0.99)
            if index != self._uploaded:
                m = np.asarray(mask, dtype=np.float32)
                if k > 0.0 and self._prev is not None and self._prev.shape == m.shape:
                    m = self._prev * k + m * (1.0 - k)
                self._prev = m
            elif self._prev is None:
                self._prev = np.asarray(mask, dtype=np.float32)
            up = np.ascontiguousarray(np.clip(np.round(self._prev), 0, 255).astype(np.uint8))
            tex.write(up.tobytes(), alignment=1)
            self._raw, self._uploaded = tex, index
        return tex

    def _feather(self, frame: Frame, raw: moderngl.Texture, index: int,
                 st: SegmentState) -> moderngl.Texture:
        """`raw` blurred by `segment.feather` (`<name>#feather`), blurred
        again only when the matte or the radius moved."""
        radius = min(max(float(st.feather), 0.0), SEGMENT_FEATHER)
        if radius <= 0.0:
            return raw
        key = self.name + "#feather"
        out, _ = frame.r._frame_target(key, tuple(raw.size), components=1)
        got = self._feathered
        if got is not None and got[0] is raw and got[1] == index and got[2] == radius \
                and got[3] is out:
            return out
        out = frame.r.mask_passes().feather(raw, key, radius)
        self._feathered = (raw, index, radius, out)
        return out

    def _feed(self, frame: Frame, worker, src: Node) -> None:
        """Submit the input when it moved and the worker would take it: the
        channel's own pixels by the shortcut, else the readback."""
        quality = self.quality(frame)
        mf = None
        if isinstance(src, MediaNode):
            now = getattr(frame.r, "media_now", None)
            mf, fit = now(src.channel) if now is not None else (None, None)
            if mf is None:
                return
            moved = ("channel", src.channel, mf.frame, quality)
        else:
            moved = None                      # (any other picture moves every frame)
        if moved is not None and moved == self._fed:
            return
        if not worker.wants():
            return
        self._n += 1
        if (mf is not None and mf.pixels is not None and fit == 0
                and src.alpha_of is None):
            # the shortcut: the channel's frame as it is (rows top first),
            # fitted by cover as the picture is, so the matte lands on it
            worker.submit(mf.pixels, self._n, quality)
            self.taken["shortcut"] += 1
        else:
            tex = src.image(frame)
            if tex is None:
                tex = picture(frame, src)
            if tex is None:
                return
            size = worker.input_size(tuple(frame.size), quality)
            self._buf = frame.r.mask_passes().readback(
                tex, frame.key(self.name + "#down"), size, self._buf)
            worker.submit(self._buf[::-1], self._n, quality)    # (rows top first)
            self.taken["readback"] += 1
        self._fed = moved

    def _motion(self, frame: Frame, st: SegmentState) -> tuple[moderngl.Texture | None, str]:
        """Motion mode's matte, on the frame thread: the difference from the
        background model, then the model's step (see the class)."""
        src = self.inputs["image"]
        tex = src.image(frame)
        if tex is None:
            tex = picture(frame, src)
        if tex is None:
            return None, "its picture reads nothing: its picture through, whole"
        size = tuple(frame.size)
        pair = frame.r.motion_pair(self.name)
        bg = pair.read[0] if pair.holds and pair.read is not None else None
        if bg is not None and tuple(bg.size) != size:
            bg = None
        t = float(frame.t)
        last = getattr(pair, "t", None)
        dt = 0.0 if last is None else min(max(t - last, 0.0), 0.25)
        pair.t = t
        learn = min(max(float(st.learn), SEGMENT_LEARN[0]), SEGMENT_LEARN[1])
        k = 1.0 - float(np.exp(-dt / learn))
        passes = frame.r.mask_passes()
        out, fbo = frame.r._frame_target(self.name + "#mask", size, components=1)
        fbo.viewport = (0, 0, *size)
        with frame.timed(self.name):
            passes.motion(tex, bg, fbo, sense=min(max(float(st.sense), 0.0), 1.0))
            wfbo = pair.target(frame.ctx, size)
            wfbo.viewport = (0, 0, *size)
            passes.learn(tex, bg, wfbo, k)
            pair.wrote = True
            pair.turn()
        self._raw, self._uploaded = out, -1
        said = (f"{size[0]}×{size[1]} · motion · sense {float(st.sense):.2f} · "
                f"learns in {learn:g} s")
        return self._feather(frame, out, int(t * 1000), st), said

    # ---- the mask contract ----

    def reads(self, frame: Frame) -> bool:
        return self.matte(frame) is not None

    # (no `own_size`: the matte is at the model's size — `native` — and every
    # consumer of a mask fits it by cover from there, as a matte's)

    def native(self, frame: Frame) -> moderngl.Texture | None:
        """The matte at its own size, as made (rows as `rows_top_first`
        says): what the promotion, a cut and the pins fit by cover."""
        return self.matte(frame)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        """The matte as a mask port binds it (`mask_port`)."""
        return mask_port(self, frame)

    def run(self, frame: Frame) -> None:
        """The matte made (and the worker fed) once a frame, and what it says."""
        self.matte(frame)


class SegmentPin(Node):
    """A segment's picture (plan 39 T4, W4): `segment.fg` — its input
    where the matte passes, cut away elsewhere (premultiplied: on a
    `composite.over` what is under shows through) — or `segment.bg`, the
    input where the matte does not pass. One `masks.MaskPasses.cut` pass
    once a frame into `<name>#cut` at the frame's size, the matte fitted by
    cover (and turned when its rows are top first: `mask_of`), feathered as
    its segment says. While the segment makes no matte: `fg` the input
    whole, `bg` nothing (transparent black; it reads nothing)."""

    KIND = "segment pin"
    INPUTS: ClassVar[dict[str, str]] = {"segment": MASK}
    OUTPUT = IMAGE
    TIMED = False             # (one cut pass; the segment times its own work)

    def __init__(self, name: str, which: str, segment: Node | None = None,
                 after: tuple[Node, ...] = ()):
        if which not in ("fg", "bg"):
            raise ValueError(f"segment pin {name!r}: fg or bg, not {which!r}")
        super().__init__(name, after, segment=segment)
        self.which = which

    def _src(self) -> Node | None:
        seg = self.inputs["segment"]
        return seg.inputs.get("image") if seg is not None else None

    def _cuts(self, frame: Frame) -> bool:
        seg = self.inputs["segment"]
        return seg is not None and seg.reads(frame)

    def reads(self, frame: Frame) -> bool:
        src = self._src()
        if self.which == "bg" and not self._cuts(frame):
            return False
        return src is not None and src.reads(frame)

    def made(self, frame: Frame) -> moderngl.Texture | None:
        """The cut picture at `frame`'s size, once a frame — None while the
        segment makes no matte."""
        key = self.name + "#cut"
        if key in frame.data:
            return frame.data[key]
        frame.data[key] = None
        src = self._src()
        if src is None or not self._cuts(frame):
            return None
        tex = src.image(frame)
        if tex is None:
            tex = picture(frame, src)
        mask, flip = mask_of(self.inputs["segment"], frame)
        if tex is None or mask is None:
            return None
        out, fbo = frame.r._frame_target(frame.key(key), frame.size)
        fbo.viewport = (0, 0, *frame.size)
        frame.r.mask_passes().cut(tex, mask, fbo, invert=self.which == "bg", flip=flip)
        frame.data[key] = out
        return out

    def _nothing(self, frame: Frame) -> moderngl.Texture:
        key = self.name + "#none"
        if key not in frame.data:
            out, fbo = frame.r._frame_target(frame.key(key), frame.size)
            fbo.use()
            frame.ctx.viewport = (0, 0, *frame.size)
            frame.ctx.clear(0.0, 0.0, 0.0, 0.0)
            frame.data[key] = out
        return frame.data[key]

    def image(self, frame: Frame) -> moderngl.Texture | None:
        got = self.made(frame)
        if got is not None:
            return got
        src = self._src()
        if self.which == "fg" and src is not None:
            return src.image(frame)
        return self._nothing(frame)

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        if self.made(frame) is None:
            src = self._src()
            if self.which == "fg" and src is not None:
                src.paint(frame, dst)
                return
            rect = tuple(dst.viewport)
            dst.use()
            frame.ctx.viewport = rect
            frame.ctx.clear(0.0, 0.0, 0.0, 0.0, viewport=rect)
            return
        super().paint(frame, dst)

    def run(self, frame: Frame) -> None:
        seg = self.inputs["segment"]
        what = "foreground" if self.which == "fg" else "background"
        if self._cuts(frame):
            self.said = f"the {what}, cut by {seg.name}'s matte"
        else:
            self.said = (f"{seg.name if seg else 'its segment'} makes no matte: "
                         + ("its picture whole" if self.which == "fg" else "nothing"))


# ---------------------------------------------------------------- layers

class Cover(Node):
    """The faces' coverage mask (`render.CoverTarget`): the scene's faces
    again, solid, one channel — only while a look-back it is wired into
    occludes (`Lookback.wants_cover`). Reads the face buffer the scene pass left,
    so it runs after the scene it masks."""

    KIND = "layer"
    INPUTS: ClassVar[dict[str, str]] = {"scene": IMAGE}
    OUTPUT = MASK
    REFS: ClassVar[frozenset[str]] = frozenset({"scene"})   # the face buffer, not the picture

    # plan 36 T4: the look-backs whose `cover` it is (set by the build)
    wanted_by: tuple[str, ...] = (LOOKBACK,)

    def run(self, frame: Frame) -> None:
        frame.cover = None
        if any(frame.r.ring(n, _ring_state(frame, n)).wants_cover() for n in self.wanted_by):
            with frame.timed(self.name):
                frame.cover = frame.r._draw_cover(frame.w, frame.h)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.cover


class HandsLayer(Node):
    """The hands' layer (`Ghost.layer`): its geometry — the hands, settled
    once a frame by the `Hands` node — drawn alone in the shared camera,
    opaque with depth and their own MSAA, into their own colour and depth
    textures; and the guide and the tethers' labels into a second one
    (`Ghost.readout`) that no effect bends — while the layer reaches a live
    effect (`readout` "downstream", the effects in `downstream`: plan 35 B,
    a through output's copies), or always (`readout` "always": the hands
    are also inside the scene, or an effect sits on the layer, so the
    guide may never be in a picture the effects bend). With no
    geometry wired it draws nothing (plan 36 T2: the hands are the wire
    into its `hands` port, never read by name). A pass that raises is
    caught (`Renderer._hands_failed`): the frame goes on without the
    hands and `Ghost.error` says why.

    Plan 26 A4: the layer is its geometry's `Ghost` (`Hands.ghost`) — a
    second hands node's layer (`hands.2`) is a second Ghost's — and what
    it drew is kept per node (`frame.data`), never in one slot."""

    KIND = "layer"
    INPUTS: ClassVar[dict[str, str]] = {"geometry": GEOMETRY}
    OUTPUT = IMAGE
    MAKES = True

    def __init__(self, name: str, after: tuple[Node, ...] = (), readout: str = "downstream",
                 **inputs: Node | None):
        super().__init__(name, after, **inputs)
        # "always", or "downstream": split while an effect of `downstream`
        # — what reads the layer, followed on (`_Build._split`) — is live
        self.readout = readout
        self.downstream: tuple[str, ...] = ()

    def split(self, frame: Frame) -> bool:
        """Whether the guide is split out of the layer this frame (once a
        frame): always while the hands are also in the scene or an effect
        sits on the layer — the guide is never in a picture the effects
        bend — else while the layer reaches a live effect (plan 35 B: a
        wired frame's copies)."""
        key = self.name + "#split"
        got = frame.data.get(key)
        if got is None:
            if getattr(self, "readout", "downstream") == "always":
                got = True
            else:
                live = frame.r.fx.state.live
                got = any(live(e) for e in getattr(self, "downstream", ()))
            frame.data[key] = got
        return got

    def ghost(self, frame: Frame):
        """The `Ghost` this layer draws: its geometry's, or the renderer's."""
        geo = self.inputs["geometry"]
        return geo.ghost(frame) if geo is not None else frame.r.ghost

    def drew(self, frame: Frame) -> bool:
        """The layer drew this frame (a hand shows)."""
        return bool(frame.data.get(self.name + "#drew"))

    def run(self, frame: Frame) -> None:
        r = frame.r
        frame.data[self.name + "#drew"] = False
        geo = self.inputs["geometry"]
        if geo is None:
            return                  # plan 36 T2: no hands wired into it — an empty layer
        split = self.split(frame)
        gh = self.ghost(frame)
        drew = False
        try:
            with frame.timed(self.name):
                kw = {"lines": True} if getattr(geo, "draw_as", "solid") == "lines" else {}
                drew = gh.layer(frame.size, frame.t, readout=split, now=geo.now(frame),
                                settled=True, **kw)
        except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
            r._hands_failed(e, frame.target, frame.vp, ghost=gh)
            drew = False
        frame.data[self.name + "#drew"] = bool(drew)
        frame.hands = frame.hands or bool(drew)
        ro = gh.readout if drew else None
        frame.readout = ro if ro is not None else frame.readout
        frame.stats["layer"] = bool(frame.stats.get("layer")) or bool(drew)
        frame.stats["readout"] = bool(frame.stats.get("readout")) or ro is not None

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return self.ghost(frame).tex if self.drew(frame) else None

    def depth(self, frame: Frame) -> moderngl.Texture | None:
        return self.ghost(frame).depth if self.drew(frame) else None

    def readout_image(self, frame: Frame) -> moderngl.Texture | None:
        """The guide and the tethers' labels this layer split out, or None."""
        return self.ghost(frame).readout if self.drew(frame) else None

    def alpha(self, frame: Frame) -> float:
        return float(self.ghost(frame).state.alpha)

    def lay(self, frame: Frame, dst: moderngl.Framebuffer, rect: tuple, blend: str,
            opaque: bool, flip: tuple[bool, bool] = (False, False),
            scene_depth: moderngl.Texture | None = None) -> None:
        """Plain over is `Ghost.composite`'s blend, as it always was; add
        and depth-aware are `Renderer.lay`'s."""
        if blend == "over" or (blend == "depth" and scene_depth is None):
            self.ghost(frame).composite(dst, rect, opaque=opaque, flip=flip)
            return
        super().lay(frame, dst, rect, blend, opaque, flip, scene_depth)


class Readout(Node):
    """The readout alone (plan 26 A3): the guide and the tethers' labels
    of the hands its geometry settled, into `Ghost.readout`, for the
    outputs that show the hands — when the hands are drawn inside the
    scene and no hands' layer of that geometry runs to draw it
    (`Ghost.layer(…, hands=False)`). Its own SYSTEM line. Kept per node
    (A4: a second hands node's readout is its own Ghost's)."""

    KIND = "layer"
    INPUTS: ClassVar[dict[str, str]] = {"geometry": GEOMETRY}
    OUTPUT = IMAGE
    MAKES = True

    def ghost(self, frame: Frame):
        geo = self.inputs["geometry"]
        return geo.ghost(frame) if geo is not None else frame.r.ghost

    def run(self, frame: Frame) -> None:
        r, geo = frame.r, self.inputs["geometry"]
        frame.data[self.name] = None
        if geo is None:
            return
        gh = self.ghost(frame)
        try:
            with frame.timed(self.name):
                drew = gh.layer(frame.size, frame.t, readout=True, now=geo.now(frame),
                                settled=True, hands=False)
            frame.data[self.name] = gh.readout if drew else None
        except Exception as e:  # noqa: BLE001 — the guide must not take the frame down
            r._hands_failed(e, frame.target, frame.vp, ghost=gh)
        got = frame.data[self.name]
        frame.readout = got if got is not None else frame.readout
        frame.stats["readout"] = bool(frame.stats.get("readout")) or got is not None

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.data.get(self.name)

    def readout_image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.data.get(self.name)


# ---------------------------------------------------------------- history

class History(Node):
    """A look-back (`lookback`, `lookback.<n>`; plan 36 T4, W4): picture in
    → trail out. Its ring (`Renderer.ring`, one per look-back: its own
    echoes, gap, res and clock) records what is wired into its `image` —
    by its capture (`Capture`, after every reader of the trail), so the
    picture wired in is no dependency of the trail — and its picture is
    the age-weighted trail of the frames before this one (`echo_mix`,
    `fade`, `darken`, `contrast`), held back where `occluder` is bright and
    where the `cover` mask is (`occlude`), premultiplied with its alpha.
    It is laid over nothing (D3): a composite lays it on — an "add" one in
    a single pass with its `under` (`Composite.paint`, `lay_onto`), the
    bytes the one-shader look-back drew. `run` moves its clock once a
    frame. (`KIND` keeps the old word `history`: only the repr and a port
    error's words read it.)"""

    KIND = "history"
    INPUTS: ClassVar[dict[str, str]] = {"occluder": IMAGE, "cover": MASK}
    OUTPUT = IMAGE

    def ring(self, frame: Frame):
        return frame.r.ring(self.name, _ring_state(frame, self.name))

    def run(self, frame: Frame) -> None:
        lb = self.ring(frame)
        lb.tick(frame.t)                 # echo time is seconds (plan 14 WP6)
        w, h = lb.echo
        self.said = (lb.ring_error or (f"{w}×{h} · {lb.held()} of {MAX_ECHOES} held · "
                                       f"{_ring_holds(frame, self.name)}" if w else
                                       f"records {_ring_holds(frame, self.name)}"))

    def _masks(self, frame: Frame) -> tuple:
        cover, occ = self.inputs["cover"], self.inputs["occluder"]
        return (cover.image(frame) if cover is not None else None,
                picture(frame, occ) if occ is not None else None)

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        cover, occ = self._masks(frame)
        with frame.timed(self.name):
            self.ring(frame).trail(dst, cover, occ)

    def lay_onto(self, frame: Frame, under: moderngl.Texture, dst: moderngl.Framebuffer) -> None:
        """The trail added onto `under` (a picture at the frame's size) into
        `dst`, in one pass: an "add" composite of this look-back."""
        cover, occ = self._masks(frame)
        with frame.timed(self.name):
            self.ring(frame).trail(dst, cover, occ, under=under)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        """The trail made once a frame into a half-float texture of its own
        (it carries its alpha, and must not quantise before it is laid on),
        for a consumer that binds a texture: a dream, a composite laying it
        over, an effect."""
        key = self.name + "#trail"
        if key not in frame.data:
            tex, fbo = frame.r._frame_target(frame.key(key), frame.size, dtype="f2")
            fbo.viewport = (0, 0, *frame.size)
            self.paint(frame, fbo)
            frame.data[key] = tex
        return frame.data[key]


def _ring_state(frame: Frame, name: str):
    """Look-back `name`'s values (plan 36 T4): the renderer's own
    `DreamState` for `lookback` (`dream.*`), else the view state's for that
    instance (`ViewState.lookback`, `dream.<n>.*`: params.declare_lookbacks)
    — None when none is declared (a default one)."""
    if name == LOOKBACK:
        return None
    return (getattr(frame.s, "lookback", None) or {}).get(name)


def _advance_fx(frame: Frame) -> None:
    """Once a frame, before the outputs (plan 30 D1): any effect on, a
    placed one too — its clock moves once a frame whether or not its edge
    had a picture to fold (plan 36 T4: the first capture's, or the graph's
    before its first output when nothing is recorded)."""
    if frame.data.get("fx#advanced"):
        return
    frame.data["fx#advanced"] = True
    if (frame.fx_on or _live_now(frame)) and not frame.stats["chain_runs"]:
        frame.r.fx.state.advance_to(frame.t)


class Capture(Node):
    """A look-back's capture (`lookback(capture)`, `lookback.2(capture)`):
    what is wired into its `image` — the scene, or any picture (the scene
    with the hands' layer laid on is a `Composite` wired there) — into its
    ring on the echoes' cadence. Exactly once a frame, after everything an
    output shows has read the trail (`after`: every `Shown` end, each
    delay's write, each picture laid as an output's hands or guide — a
    capture changes the echoes' weights and ages, so one between two
    readers would give two outputs different echoes), whatever the outputs
    show. (`KIND` keeps the old word `history`, as `History`'s does.)"""

    KIND = "history"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = None

    def __init__(self, name: str, after: tuple[Node, ...] = (), lookback: str = LOOKBACK,
                 **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.lookback = lookback

    def run(self, frame: Frame) -> None:
        r = frame.r
        frame.stats["captures"] = frame.stats.get("captures", 0) + 1
        src = picture(frame, self.inputs["image"])
        with frame.timed(self.name):
            r.ring(self.lookback, _ring_state(frame, self.lookback)).capture(src, r.scene.fbo)
        _advance_fx(frame)


# ---------------------------------------------------------------- composite

class Composite(Node):
    """`over` laid on `under` (`Renderer.lay`), premultiplied at `over`'s
    opacity (`ghost.alpha` for the hands' layer): `blend` "over" (today's
    `Ghost.composite`), "add", or "depth" — over, but hidden where the
    image on the `depth` port (the scene) has a visible surface nearer the
    eye (`render.LAYER_DEPTH_BIAS`), so a separate hands layer can still
    go behind the shape. `under` None is the ground (the clear at the
    renderer's `bg_alpha`). Painted into its consumer's framebuffer (the
    chain's input, before the effects: today's "through"), or made once a
    frame into a texture of its own for a consumer that needs one (the
    capture: the history with the hands). The layer failing here is
    caught: the picture is `under` alone and `Ghost.error` says why."""

    KIND = "composite"
    INPUTS: ClassVar[dict[str, str]] = {"under": IMAGE, "over": IMAGE, "depth": IMAGE}
    OUTPUT = IMAGE
    REFS: ClassVar[frozenset[str]] = frozenset({"depth"})

    def __init__(self, name: str, after: tuple[Node, ...] = (), blend: str = "over",
                 under_alpha_of: str | None = None, **inputs: Node | None):
        if blend not in BLENDS:
            raise ValueError(f"composite {name!r}: blend {blend!r}, one of {', '.join(BLENDS)}")
        super().__init__(name, after, **inputs)
        self.blend = blend
        # plan 33 R: the `ViewState` field `under` is laid on at (the
        # backdrop's `backdrop_alpha`, a branch under the scene), over the
        # ground; None paints `under` as it is
        self.under_alpha_of = under_alpha_of
        # plan 36 T1 (R9): the windows (indexes into `Frame.views`) whose
        # picture this composite heads, laying their hands through the
        # effects — while each has its hands muted it lays nothing over
        # (`_Build._mute_hands`); () for any other composite
        self.mute_hands: tuple[int, ...] = ()

    def muted(self, frame: Frame) -> bool:
        """Whether every window this composite's picture is for has its
        hands muted this frame (`mute_hands`): its `over` then lays nothing."""
        if not self.mute_hands:
            return False
        views = getattr(frame, "views", None) or ()
        return all(i < len(views) and not getattr(views[i].switches, "hands", True)
                   for i in self.mute_hands)

    def reads(self, frame: Frame) -> bool:
        return any(n is not None and n.reads(frame)
                   for n in (self.inputs["under"], self.inputs["over"]))

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        r, ctx, size = frame.r, frame.ctx, frame.size
        under = self.inputs["under"]
        if self.blend == "add" and under is not None and self.under_alpha_of is None:
            # plan 36 T4: a look-back's trail (straight, or through a dream
            # passing it on) added onto `under` is one pass — min(under +
            # trail, 1), the alphas' union: what "add" lays, without the
            # trail's own texture between (the one-shader look-back's bytes)
            lb = _trail_of(self.inputs["over"], frame)
            if lb is not None and not self.muted(frame):
                tex = picture(frame, under)
                if tex is not None:
                    lb.lay_onto(frame, tex, dst)
                    return
        if under is not None and self.under_alpha_of is not None:
            # (made before the lay: its own passes time themselves; plan 33
            # S: a switch at off, or on an unwired input, is not painted:
            # the ground alone)
            tex = (None if isinstance(under, SwitchNode) and under.selected(frame) is None
                   else picture(frame, under))
            dst.use()
            ctx.viewport = (0, 0, *size)
            ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha)
            a = min(max(float(getattr(frame.s, self.under_alpha_of, 1.0)), 0.0), 1.0)
            if tex is not None and a > 0.0:
                r.lay(tex, dst, (0, 0, *size), blend="over", alpha=a, opaque=r.fx.opaque)
        elif under is None:
            dst.use()
            ctx.viewport = (0, 0, *size)
            ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha)
        else:
            under.paint(frame, dst)
        over = self.inputs["over"]
        if over is None or self.muted(frame):
            return
        try:
            tex = over.image(frame)
            if tex is None:
                return
            with frame.timed(self.name):
                lay(frame, self.blend, over, self.inputs["depth"], dst, (0, 0, *size),
                    r.fx.opaque)
        except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
            r._hands_failed(e, frame.target, frame.vp)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        """Painted once a frame into a texture of its own (the renderer's
        frame texture under this node's name) for a consumer that needs a
        texture — the capture."""
        if self.name not in frame.data:
            tex, fbo = frame.r._frame_target(frame.key(self.name), frame.size)
            fbo.viewport = (0, 0, *frame.size)
            self.paint(frame, fbo)
            frame.data[self.name] = tex
        return frame.data[self.name]


def lay(frame: Frame, blend: str, over: Node, depth_of: Node | None,
        dst: moderngl.Framebuffer, rect: tuple, opaque: bool,
        flip: tuple[bool, bool] = (False, False)) -> None:
    """`over`'s picture into `dst`'s `rect` with `blend` (`Node.lay`): at
    its opacity; depth-aware against `depth_of`'s depth when the blend is
    "depth" and both have one (else plain over)."""
    scene_depth = depth_of.depth(frame) if (blend == "depth" and depth_of is not None) else None
    over.lay(frame, dst, rect, blend, opaque, flip, scene_depth)


# ---------------------------------------------------------------- fx

def _live_now(frame: Frame) -> frozenset[str]:
    """The effects of this frame's graph that are live (`FxState.live`: on
    with mix above 0, `fx.on` and `fx.mix` above 0 — no target, no order:
    plan 33 R), asked once a frame — the runs' and (plan 30 D1) the
    placed and wired ones', which `frame.fx_on` leaves out."""
    got = frame.data.get("fx#live")
    if got is None:
        st = frame.r.fx.state
        nodes = frame.graph.nodes.values() if frame.graph is not None else ()
        got = frame.data["fx#live"] = frozenset(
            n.effect for n in nodes if isinstance(n, Effect) and st.live(n.effect))
    return got


def _spare(frame: Frame, dst: moderngl.Framebuffer | None, hold: bool = False
           ) -> tuple[moderngl.Texture, moderngl.Framebuffer]:
    """A texture of the effects' pool (`FxChain.pool`, sized by the graph:
    `Graph.pool`) to paint an effect's input into: never `dst` (the one
    the effect writes) and never one held for the frame (an effect's
    image a second consumer still reads). The pool's two textures
    alternate down a straight run — the effect writing `dst` reads the
    other one, which the effect before it wrote from `dst`'s — so two are
    enough however long the run; one is added if none is free. `hold`
    keeps the texture for the rest of the frame."""
    held = frame.data.setdefault("fx#held", set())
    need = frame.graph.pool if frame.graph is not None else 2
    # (plan 33 R: the pool at this frame's size — `Frame.pool`)
    pool = frame.pool(max(need, 2))
    for tex, fbo in pool:
        if fbo is not dst and id(tex) not in held:
            break
    else:
        tex, fbo = frame.pool(len(pool) + 1)[-1]
    if hold:
        held.add(id(tex))
    return tex, fbo


class Effect(Node):
    """One effect instance as an image node (plan 30 D0): one effect file's
    program (`fx.FxChain`) over its input. `effect` is the instance's name
    as `FxState` knows it (`acid`, `acid.2`, `palette`) and its params are
    `fx.<effect>.*`; the node's own `name` is the effect's (a copy's its
    own, `copy.2`: plan 35 T4 retired the pipelines' `acid(scene+hands)`).

    **Off** this frame — not `FxState.live` (switched off, mix 0, the
    stack bypassed; plan 33 R: no target and no order, its place is its
    wires) or its file never compiled — it is a read-through: its consumers get its input's
    picture (`paint` paints the input straight into the consumer's
    framebuffer, `image` is the input's), no pass runs and no texture is
    taken. **On**, it paints its input into a texture of the effects' pool
    and runs its pass from there into its consumer's framebuffer
    (`FxChain.run_one`) under `frame.timed(name)`: the SYSTEM page's line
    for it, in a frame it ran. Painted once a frame however many
    consumers read it: a node with more than one reader (`Graph.readers`)
    makes its picture once into a pool texture held for the frame
    (`image`) and shows that 1:1 into each.

    `run` does nothing: the pass runs when its consumer pulls it, like
    the history's and the composites' (the class docstring of the module:
    "materialised and painted images").

    Plan 30 D1 — **placed** effects (`placed`: "after" / "into", or None for
    one the wires put where it is). One placed after a node that makes a texture (the
    scene, a hands' layer: `MAKES`; or after such an effect) folds that
    texture once, in its own `run`, into a pool texture held for the
    frame (`makes`): every consumer then reads that one picture — the
    history and the capture after the scene, the composites and the
    outputs laying the hands — and a source with no picture this frame
    (no hand drawn) leaves it none. On a layer (`see_through`) its pass
    keeps a see-through pixel see-through (`u_opaque` 0), and it is laid
    on at the layer's opacity, with its depth (`alpha`, `depth`). One on
    an output's picture (`into: output.<n>`) is run by that output
    (`fold`), on the frame texture the output settles on."""

    KIND = "effect"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE, "aux": IMAGE}
    OUTPUT = IMAGE
    TIMED = False            # a line on SYSTEM only in a frame it ran (`Graph.timed_in`)
    # its picture is laid over another (a composite's `over`, the backdrop's
    # scene: `_Build.laid_over`), so its pass keeps its own alpha — an opaque
    # ground there would cover the picture under it wherever it draws nothing
    laid_over = False
    # plan 32 R: `aux` is a second picture the pass reads, not the one it
    # bends — an effect placed after a node leaves an aux reading that node
    REFS: ClassVar[frozenset[str]] = frozenset({"aux"})

    def __init__(self, name: str, *, image: Node | None = None, node: str | None = None,
                 after: tuple[Node, ...] = (), placed: str | None = None):
        super().__init__(node if node is not None else name, after, image=image)
        self.effect = name
        self.placed = placed          # D1: "after" / "into" when the preset places it

    @property
    def makes(self) -> bool:
        """Its source makes a texture in `run` (the scene, a layer, or an
        effect folding one): this effect folds it once in its own `run`."""
        src = self.inputs["image"]
        # (plan 33 R: a source that paints itself straight in — the
        # pattern's seed, `PAINTS` — is painted, as the faces' chain was;
        # plan 36 T4: an effect of All outputs' run — `placed` None — paints
        # its input as the run always did, the look-back that headed it gone)
        return src is not None and self.placed is not None and (
            (src.MAKES and not src.PAINTS) or (isinstance(src, Effect) and src.makes))

    @property
    def see_through(self) -> bool:
        """Its picture is a layer's (premultiplied, see-through ground), or
        it is laid over another picture (`laid_over`)."""
        if self.laid_over:
            return True
        src = self.inputs["image"]
        while isinstance(src, Effect):
            src = src.inputs["image"]
        return src is not None and src.KIND == "layer"

    def reads(self, frame: Frame) -> bool:
        src = self.inputs["image"]
        return src is not None and src.reads(frame)

    def run(self, frame: Frame) -> None:
        # plan 33 R: folded here only where something reads it at the
        # frame's size — one only the faces or the pattern's layer read is
        # made at their size, when they pull it (`Graph.at_frame`)
        if (self.makes and self.on(frame)
                and (frame.graph is None or frame.graph.at_frame(self))):
            self._made(frame)

    def alpha(self, frame: Frame) -> float:
        src = self.inputs["image"]
        return src.alpha(frame) if src is not None else 1.0

    def depth(self, frame: Frame) -> moderngl.Texture | None:
        src = self.inputs["image"]
        return src.depth(frame) if src is not None else None

    def ghost(self, frame: Frame):
        """The `Ghost` whose layer this effect folds (its source's, through
        any effects between): an output laying it hands a presenter that
        Ghost's opacity — and its own layer's, for `hands.2`."""
        src = self.inputs["image"]
        while isinstance(src, Effect):
            src = src.inputs["image"]
        get = getattr(src, "ghost", None)
        return get(frame) if get is not None else frame.r.ghost

    def _made(self, frame: Frame) -> moderngl.Texture | None:
        """The folded texture of a source that makes one (`makes`): made
        once a frame into a held pool texture, None while the source has
        no picture this frame."""
        if self.name not in frame.data:
            got = self.inputs["image"].image(frame)
            if got is not None:
                tex, fbo = _spare(frame, None, hold=True)
                self._one(frame, got, fbo)
                got = tex
            frame.data[self.name] = got
        return frame.data[self.name]

    def fold(self, frame: Frame, tex: moderngl.Texture) -> moderngl.Texture:
        """`tex` (an output's frame) through this effect into a held pool
        texture, once a frame — or `tex` itself while it is off (D1: an
        effect placed into an output's picture, run by the output)."""
        if not self.on(frame):
            return tex
        if self.name not in frame.data:
            out, fbo = _spare(frame, None, hold=True)
            self._one(frame, tex, fbo)
            frame.data[self.name] = out
        return frame.data[self.name]

    def _aux(self, frame: Frame, avoid: moderngl.Framebuffer | None) -> moderngl.Texture | None:
        """The picture on the `aux` port this frame (plan 32 R), or None with
        nothing wired: the source's texture when it made one, else painted
        once into a pool texture held for the frame — never `avoid`'s (the
        framebuffer this effect's pass writes: no pass reads the texture it
        writes)."""
        src = self.inputs.get(AUX)
        if src is None:
            return None
        key = self.name + "#aux"
        if key not in frame.data:
            held = frame.data.setdefault("fx#held", set())
            # `avoid`'s texture held while the aux is made, so neither the
            # source's own passes nor the paint below can take it
            guard: set[int] = set()
            if avoid is not None:
                guard = {id(t) for t, f in frame.pool(0) if f is avoid} - held
            held |= guard
            try:
                tex = src.image(frame)
                if tex is None:
                    tex, fbo = _spare(frame, avoid, hold=True)
                    src.paint(frame, fbo)
            finally:
                held -= guard
            frame.data[key] = tex
        return frame.data[key]

    def _one(self, frame: Frame, src: moderngl.Texture, dst: moderngl.Framebuffer) -> None:
        """This effect's pass from texture `src` into `dst`, timed and
        counted; a layer's keeps its see-through ground."""
        kw = {"opaque": 0} if self.see_through else self._opaque(frame)
        aux = self._aux(frame, dst)
        if aux is not None:
            kw["aux"] = aux
        with frame.timed(self.name):
            frame.r.fx.run_one(self.effect, src, dst, frame.t, **kw)
        frame.stats.setdefault("effects", []).append(self.name)

    @staticmethod
    def _opaque(frame: Frame) -> dict:
        """`run_one`'s `opaque` for a pass painted for `frame`: the frame's
        own (0 at another size: a face's intensity, `Frame.at`), or
        nothing — the chain's, the window's ground."""
        opaque = getattr(frame, "opaque", None)
        return {} if opaque is None else {"opaque": opaque}

    def on(self, frame: Frame) -> bool:
        """Whether this effect runs a pass this frame (see the class)."""
        key = self.name + "#on"
        got = frame.data.get(key)
        if got is None:
            got = frame.data[key] = (self.effect in _live_now(frame)
                                     and frame.r.fx.ready(self.effect))
        return got

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        """Its `image` input's (plan 34 D, row 368): an effect after a
        delay, a resize or an echo runs at that size, in that size's pool,
        and is fitted into a consumer of another (`_own`). None for every
        node of plan 33, so its paths below are the ones they always were."""
        src = self.inputs["image"]
        return src.own_size(frame) if src is not None else None

    def _own(self, frame: Frame, own: tuple[int, int]) -> moderngl.Texture | None:
        """This effect's picture made at its own size `own` (the root frame
        at that size: `Frame.at`'s pool and data)."""
        root = frame.root
        return self.image(root if tuple(own) == tuple(root.size) else root.at(own))

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        src = self.inputs["image"]
        if src is None:
            return
        own = self.own_size(frame)
        if own is not None and tuple(own) != tuple(frame.size):
            # plan 34 D: made at its own size, laid in by cover
            tex = self._own(frame, own)
            if tex is not None:
                frame.r._refit(tex, dst, fit=OWN_FIT)
                return
            rect = tuple(dst.viewport)
            dst.use()
            frame.ctx.viewport = rect
            frame.ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha, viewport=rect)
            return
        if not self.on(frame):
            src.paint(frame, dst)                 # read through: no pass, no texture
            return
        if self.makes:                            # D1: folded once in `run`, shown 1:1
            super().paint(frame, dst)
            return
        readers = frame.graph.readers(self) if frame.graph is not None else 1
        if self.name in frame.data or readers > 1:
            # made once into a held texture that is never `dst` (a consumer
            # painting into a pool texture must not be shown it: a feedback
            # loop), then shown 1:1
            self._make(frame, dst)
            super().paint(frame, dst)
            return
        self._pass(frame, dst)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        src = self.inputs["image"]
        own = self.own_size(frame)
        if own is not None and tuple(own) != tuple(frame.size):
            # plan 34 D: made at its own size, refitted once a frame into a
            # half-float target at the frame's (the `IMAGE` contract)
            key = self.name + "#fit"
            if key not in frame.data:
                tex = self._own(frame, own)
                out, fbo = frame.r._frame_target(frame.key(key), frame.size, dtype="f2")
                fbo.viewport = (0, 0, *frame.size)
                if tex is not None:
                    frame.r._refit(tex, fbo, fit=OWN_FIT)
                else:
                    fbo.use()
                    frame.ctx.viewport = (0, 0, *frame.size)
                    frame.ctx.clear(0.0, 0.0, 0.0, 0.0)
                frame.data[key] = out
            return frame.data[key]
        if not self.on(frame):
            return src.image(frame) if src is not None else None
        if self.makes:
            return self._made(frame)
        return self._make(frame, None)

    def _make(self, frame: Frame, avoid: moderngl.Framebuffer | None) -> moderngl.Texture:
        """This effect's picture for the frame, made once into a pool
        texture held for the rest of it: never `avoid` (the framebuffer the
        consumer asking paints into), never one held already. A held
        texture is never handed out again this frame, so a later
        consumer's `dst` cannot be it."""
        if self.name not in frame.data:
            tex, fbo = _spare(frame, avoid, hold=True)
            self._pass(frame, fbo)
            frame.data[self.name] = tex
        return frame.data[self.name]

    def _pass(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """The input into a pool texture, then this effect's pass from it
        into `dst`; counted in `frame.stats["effects"]`. The timer brackets
        the pass alone (queries never nest: the input's own nodes time
        themselves before it)."""
        aux = self._aux(frame, dst)          # first: making it may take a spare
        tex, fbo = _spare(frame, dst)
        self.inputs["image"].paint(frame, fbo)
        kw = {"aux": aux} if aux is not None else {}
        kw.update({"opaque": 0} if self.see_through else self._opaque(frame))
        with frame.timed(self.name):
            frame.r.fx.run_one(self.effect, tex, dst, frame.t, **kw)
        frame.stats.setdefault("effects", []).append(self.name)


class Copy(Effect):
    """A copy (plan 35 F, row 377): effect instance `of` drawn again on
    another picture — `copy`, `copy.2` … — with the instance's knobs, its
    `FxState.live` and its clock (`effect` is `of`), its own `image` and
    `aux`. What each retired pipeline's own run node was
    (`acid(scene+hands)`), said as a node, made only where a wire says one."""

    KIND = "effect"

    def __init__(self, name: str, of: str, image: Node | None = None,
                 after: tuple[Node, ...] = ()):
        super().__init__(of, image=image, node=name, after=after, placed="wire")


class Shown(Node):
    """An output's picture as an end (plan 35 B): `shown(<source>)`, one per
    distinct source an output's `image` takes (`window_ports`: its own
    wire, else All outputs' by the rig's bus cable), shared by every
    output showing it — the retired pipelines' ends (`Fx`, and `Wired` for
    a picture by a wire) made one. As an end it
    decides where the picture lands (`run`): straight into its one user's
    window when exactly one output takes it this frame (`Frame.users`,
    counted through the mutes) at the frame's size, unflipped, with no tap
    and no fold — else once into a frame texture under its name, for every
    output that takes it. Each end that runs is one of `stats["ends"]`, by
    name (plan 35 T4: where the pipelines' keys were). Plan 36 T1: an end
    is always itself — the stand-down (row 378) that swapped a through
    chain for its originals, frame by frame, is gone: what is wired is
    what shows."""

    KIND = "shown"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = IMAGE

    def __init__(self, name: str, after: tuple[Node, ...] = (), **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.key = name               # its frame texture's and its routes' key
        self.chained = False          # an effect of the graph's run is on its way

    def run(self, frame: Frame) -> None:
        users = frame.users(self)
        if not users:
            return
        r, views, stats = frame.r, frame.views, frame.stats
        only = views[users[0]]
        direct = (len(users) == 1 and only.target is not None
                  and getattr(only, "tap", None) is None
                  and tuple(only.rect[2:]) == frame.size
                  and not getattr(only.switches, "flip_x", False)
                  and not getattr(only.switches, "flip_y", False)
                  and not (frame.graph is not None and frame.graph.folds(users[0])))
        stats.setdefault("ends", []).append(self.key)
        try:
            if direct:
                dst, tex = only.target, None
                dst.viewport = only.rect
            else:
                tex, dst = r._frame_target(self.key, frame.size)
                stats["direct"] = False
            self.paint(frame, dst)
            frame.frames[self.key] = tex
        except Exception as e:  # noqa: BLE001 — one end must not take the others down
            frame.failed.add(self.key)
            for i in users:
                r._view_failed(views[i], self.name, e)
            r._rebind(frame.target, frame.vp)

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """Its source into `dst`: the clocks moved and a chain run counted
        when an effect of the graph's run on its way is live this frame
        (`frame.fx_on`)."""
        src = self.inputs["image"]
        live = frame.fx_on and getattr(self, "chained", False)
        if live:
            frame.r.fx.state.advance_to(frame.t)
        if src is not None:
            src.paint(frame, dst)
        if live:
            frame.stats["chain_runs"] += 1


# ---------------------------------------------------------------- output

class Output(Node):
    """One render output (`Renderer._compose`): the picture on its `image`
    port (its end, `Shown`; already there when painted direct, else shown
    1:1 or scaled into `outputs.fit`'s rect with the rest the view's
    ground), the layer on its `hands` port over it (`blend`, depth-aware
    against the `depth` port's scene), the readout, its mirror, its dim
    (master × its own) — or, for a view with a presenter, the `Handoff`
    that says the same five steps (a presenter lays the hands plain over:
    the depth stays in this context). What it shows this frame is
    `settle`'s: its wired end and layer, through its window's mutes."""

    KIND = "output"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE, "hands": IMAGE, "readout": IMAGE,
                                        "depth": IMAGE}
    OUTPUT = None
    REFS: ClassVar[frozenset[str]] = frozenset({"readout", "depth"})

    def __init__(self, name: str, index: int, after: tuple[Node, ...] = (),
                 blend: str = "over", **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.index = index            # the view it draws, in Frame.views
        self.blend = blend

    def _muted(self, frame: Frame) -> tuple[bool, bool]:
        """(the picture muted, the hands and guide muted) this frame — plan
        35 O (row 374): an output reads its window's mutes each frame,
        `scene` ("picture") off ignores `image`, `hands` off ignores
        `hands` and the guide; never a rebuild."""
        sw = frame.views[self.index].switches
        return not getattr(sw, "scene", True), not getattr(sw, "hands", True)

    @property
    def folds(self) -> list[Effect]:
        """The effects placed into this output's picture (plan 30 D1:
        `into: output.<n>`), first applied first: they sit on its `image`
        port, between it and the end it shows (`Shown`)."""
        out: list[Effect] = []
        src = self.inputs["image"]
        while isinstance(src, Effect):
            out.append(src)
            src = src.inputs["image"]
        return out[::-1]

    def settle(self, frame: Frame) -> tuple[Node | None, tuple[Node, str] | None]:
        """(the end it shows this frame or None for its ground, (the layer
        laid over after it, its blend) or None) — through its window's
        mutes, nothing else (plan 36 T1: no stand-down swaps the end; a
        hands mute inside a through chain is the composite's,
        `Composite.mute_hands`)."""
        key = self.name + "#settle"
        if key in frame.data:
            return frame.data[key]
        end = self.inputs["image"]
        while isinstance(end, Effect):            # D1: the end behind its folds
            end = end.inputs["image"]
        over, blend = self.inputs["hands"], self.blend
        no_picture, no_hands = self._muted(frame)
        if no_picture:
            end = None
        if no_hands:
            over = None
        laid = (over, blend) if over is not None and over.image(frame) is not None else None
        frame.data[key] = got = (end, laid)
        return got

    def _stood_down(self, frame: Frame, folds: list[Effect]) -> None:
        """Each of `folds` dormant this frame in `Graph.dormant` (and
        `Graph.stood`, so the next frame takes the words out again):
        `palette into output 2 — output 2 stands down this frame`."""
        g = frame.graph
        if g is None:
            return
        n = self.name.partition(".")[2] or str(self.index + 1)
        for e in folds:
            if e.effect not in g.dormant:
                g.dormant[e.effect] = (f"{e.effect} into output {n} — output {n} "
                                       "stands down this frame")
                g.stood.add(e.effect)

    def run(self, frame: Frame) -> None:
        r, v = frame.r, frame.views[self.index]
        # the readout goes on every output that shows the hands, over,
        # through or in the scene: in its own layer the guide is in none.
        # A4: the readout of the node wired to this output's port, and the
        # hands laid over by their own layer's Ghost (a second hands node's
        # on the glass, the first's in the scene on the projector)
        src = self.inputs["readout"] if not self._muted(frame)[1] else None
        ro = None if src is None else (src.readout_image(frame)
                                       if hasattr(src, "readout_image") else frame.readout)
        try:
            end, laid = self.settle(frame)
            if "routes" in frame.stats:          # what this output shows: (end, hands over)
                frame.stats["routes"][self.index] = (
                    end.key if end is not None else None, laid is not None)
            put = None
            # D1: a layer through a placed effect is laid by the node (its
            # folded texture), not the Ghost's own `composite` — and (plan 28
            # N4) so is anything a wire lays on the hands port that is not a
            # hands' layer (the scene, a composite): only a HandsLayer is a
            # Ghost's picture
            laid_node = laid is not None and not isinstance(laid[0], HandsLayer)
            if laid is not None and (laid[1] != "over" or laid_node):
                over, blend = laid

                def put(tgt, rect, opaque, flip, over=over, blend=blend):
                    lay(frame, blend, over, self.inputs["depth"], tgt, rect, opaque, flip)
            ghosts = {}
            if laid is not None and hasattr(laid[0], "ghost"):
                ghosts["ghost"] = laid[0].ghost(frame)
            if laid_node:
                # D1: a presenter lays the folded layer, not the Ghost's own
                # (N4: or the wired node's picture)
                ghosts["hands_tex"] = laid[0].image(frame)
            if ro is not None and hasattr(src, "ghost"):
                ghosts["readout_ghost"] = src.ghost(frame)
            frames = frame.frames
            folds = self.folds
            if folds and end is not None and end.key not in frame.failed:
                # D1: the frame this output settled on, through the effects
                # placed into it — this output's alone
                tex = frame.frames.get(end.key)
                if tex is not None:
                    for e in folds:
                        tex = e.fold(frame, tex)
                    frames = {**frame.frames, end.key: tex}
            elif folds and end is None:
                # a through output standing down to its ground: nothing to
                # fold this frame — say so where the build's dormant words
                # are read (`graph_words`, OUTPUT's `dormant:` lines)
                self._stood_down(frame, folds)
            with frame.timed(self.name):
                r._compose(v, end.key if end is not None else None, laid is not None,
                           frames, frame.failed, frame.size, ro, lay=put,
                           blend=laid[1] if laid is not None else "over", **ghosts)
        except Exception as e:  # noqa: BLE001 — one view must not take the others down
            r._view_failed(v, "output", e)
            r._rebind(frame.target, frame.vp)


# ---------------------------------------------------------------- the graph

class Graph:
    """Nodes and their order. `add` takes a node whose inputs are already
    in the graph (names unique); `order` is dependency order, settled when
    the graph is built: a depth-first walk from each node in the order
    they were added, dependencies first, so ties fall in insertion order
    (today's frame order). `evaluate` runs every node once.

    Plan 30 D0: `readers` counts each node's consumers (an effect read by
    two is made once into a held texture), `pool` is how many textures
    the effects' pool needs for this graph, and `effects` the effect
    instances the build had (plan 33 R: the renderer builds again when a
    file comes or goes), `run` the effects the wires reach (plan 35: no
    pipeline's run — the effects in the order the wires put them).

    Plan 30 D1: `insert` puts a placed effect on an edge after the graph
    is built (`build_graph`), `dormant` says why a placed effect has no
    node in this graph (`palette after hands — no hands layer this
    frame`), `notes` a placement refused at build (a loop), `folds` the
    effects placed into an output's picture."""

    def __init__(self, key: tuple = (), wiring: Wiring | None = None):
        self.key = key
        self.wiring = wiring if wiring is not None else EMPTY
        self.nodes: dict[str, Node] = {}
        self.order: list[Node] = []
        self.clouds: tuple[str, ...] = ()        # the cloud roles the default graph drew (A4b)
        self.effects: tuple[str, ...] = ()       # the effect instances of its runs (D0)
        self.dormant: dict[str, str] = {}        # D1: placed effect → why it has no node
        # the entries of `dormant` written while the graph ran (an output's
        # folds skipped this frame: `Output.run`), taken out again before
        # the next frame runs — the build's own are never among them
        self.stood: set[str] = set()
        self.notes: list[str] = []               # D1: placements refused at build
        # D1: the effects placed by `after`/`into` (dormant ones included):
        # the renderer's `fx_on` ("an effect bends the picture") leaves them out
        self.placed_names: frozenset[str] = frozenset()
        # the effects the wires reach, first to last (plan 35: the wired
        # frame's, no pipeline's run) — the renderer's `fx_on` is any of them live
        self.run: tuple[str, ...] = ()
        self._readers: dict[str, int] = {}
        self._pool: int | None = None
        self._framed: frozenset[str] | None = None     # plan 33 R: `at_frame`, settled
        # plan 33 S: `pulled`, by the switches' picks (None: not yet asked)
        self._pulled: dict[tuple[int, ...], frozenset[str]] | None = None

    def relink(self) -> None:
        """Count the readers and sort again after inputs were rewired in
        place (D1's `insert`, plan 28 N4's wires)."""
        self._readers = {}
        for n in self.nodes.values():
            for src in n.inputs.values():
                if src is not None:
                    self._readers[src.name] = self._readers.get(src.name, 0) + 1
        self.order = self._sort()
        self._pool = self._framed = None
        self._pulled = None

    def folds(self, index: int) -> bool:
        """Whether output `index`'s picture goes through an effect placed
        into it (D1): its end is then never painted direct."""
        return any(out.index == index and out.folds for out in self.outputs)

    def add(self, node: Node) -> Node:
        if node.name in self.nodes:
            raise ValueError(f"two nodes named {node.name!r}")
        for dep in node.deps():
            if self.nodes.get(dep.name) is not dep:
                raise ValueError(f"{node.name!r} depends on {dep.name!r}, not in the graph")
        self.nodes[node.name] = node
        for src in node.inputs.values():
            if src is not None:
                self._readers[src.name] = self._readers.get(src.name, 0) + 1
        self.order = self._sort()
        self._pool = self._framed = None
        self._pulled = None
        return node

    def at_frame(self, node: Node) -> bool:
        """Whether `node`'s picture is read at the frame's size (plan 33
        R): some port reads it that is not one asking a size of its own
        (`Node.SIZED`: the faces, the pattern's layer) — through an effect
        or a switch (plan 33 S), whatever reads it. A node nothing reads counts as read
        there (as before plan 33). Settled with the graph."""
        if self._framed is None:
            readers: dict[str, list[tuple[Node, str]]] = {}
            for c in self.nodes.values():
                for port, src in c.inputs.items():
                    if src is not None:
                        readers.setdefault(src.name, []).append((c, port))
            memo: dict[str, bool] = {}

            def framed(n: Node) -> bool:
                if n.name not in memo:
                    memo[n.name] = False           # (a loop reads it nowhere new)
                    got = readers.get(n.name, [])
                    memo[n.name] = not got or any(
                        port not in c.SIZED
                        and (not isinstance(c, (Effect, SwitchNode)) or framed(c))
                        for c, port in got)
                return memo[n.name]

            self._framed = frozenset(n.name for n in self.nodes.values() if framed(n))
        return node.name in self._framed

    def readers(self, node: Node) -> int:
        """How many input ports of this graph's nodes read `node`."""
        return self._readers.get(node.name, 0)

    @property
    def pool(self) -> int:
        """The textures the effects' pool needs (`FxChain.pool`): none
        without an effect node; two for straight runs (each effect reads
        the one its consumer does not write); one more for each effect
        read by more than one node, whose picture is held for the frame —
        and (plan 30 D1) for each placed effect that folds a made texture
        (`Effect.makes`) or an output's frame (`Output.folds`), whose
        picture is held too. Settled with the graph (asked once a pass)."""
        if self._pool is None:
            effects = [n for n in self.order if isinstance(n, Effect)]
            folded = {id(e) for out in self.outputs for e in out.folds}
            # plan 32 R: and one for each aux a pass paints (`Effect._aux`)
            self._pool = (2 + sum(1 for n in effects
                                  if self.readers(n) > 1 or n.makes or id(n) in folded)
                          + sum(1 for n in effects if n.inputs.get(AUX) is not None)
                          ) if effects else 0
        return self._pool

    def _sort(self) -> list[Node]:
        done: list[Node] = []
        seen: set[int] = set()

        def visit(n: Node) -> None:
            if id(n) in seen:
                return
            seen.add(id(n))
            for d in n.deps():
                visit(d)
            done.append(n)

        for n in self.nodes.values():
            visit(n)
        return done

    @property
    def timed(self) -> list[str]:
        """The names the GPU timer reports, one per node, in order: every
        node that times itself (`TIMED`), and every solid geometry a scene
        draws — the scene times those draws under the geometry's name (plan
        26 A4: decided by the consumer edge, so one hands node may feed a
        scene and a layer and its line is its in-scene draws)."""
        held = self.in_scene()
        return [n.name for n in self.order if n.TIMED or n.name in held]

    def timed_in(self, frame: Frame) -> list[str]:
        """`timed` with the effect nodes that ran a pass this frame
        (`frame.stats["effects"]`) in their places (plan 30 D0): the
        names the renderer hands the timer for the frame, so the SYSTEM
        page has a line per effect that ran and none for one that is off."""
        held = self.in_scene()
        ran = set(frame.stats.get("effects", ()))
        return [n.name for n in self.order if n.TIMED or n.name in held or n.name in ran]

    def in_scene(self) -> set[str]:
        """The names of the solid geometries some scene of this graph draws."""
        return {g.name for n in self.order if isinstance(n, Scene)
                for g in n.geometries() if g.SOLID}

    @property
    def outputs(self) -> list[Output]:
        return [n for n in self.order if isinstance(n, Output)]

    def pulled(self, frame: Frame) -> frozenset[str]:
        """The nodes some consumer pulls this frame (plan 33 S): every node
        on a path from one nothing reads (an output, the capture, the
        pattern, the backdrop) that runs through each switch's picked input
        alone. A branch only an unpicked input reads is not made: its folds
        do not run (`evaluate`) and nothing pulls its picture, so its
        channels are not read or uploaded. Every node with no switch in the
        graph; with switches, settled once per set of picks — `select`
        moving is a lookup, never a rebuild."""
        switches = [n for n in self.order if isinstance(n, SwitchNode)]
        cache = getattr(self, "_pulled", None)          # (a graph from before a reload)
        if cache is None:
            cache = self._pulled = {}
        key = tuple(sw.index(frame) for sw in switches)
        got = cache.get(key)
        if got is not None:
            return got
        todo = [n for n in self.nodes.values() if self.readers(n) == 0]
        seen: set[str] = set()
        while todo:
            n = todo.pop()
            if n.name in seen:
                continue
            seen.add(n.name)
            if isinstance(n, SwitchNode):
                picked = n.selected(frame)
                todo.extend([picked, *n.after] if picked is not None else n.after)
            else:
                todo.extend(n.deps())
        if len(cache) >= 256:         # (eight switches flicked at random: bounded)
            cache.clear()
        got = cache[key] = frozenset(seen)
        return got

    def evaluate(self, frame: Frame) -> None:
        """Run the frame: each node once, in order — but a node that makes
        its picture in `run` (`MAKES`, an effect folding a made texture)
        that no consumer pulls this frame (`pulled`: behind a switch's
        unpicked input), which makes nothing."""
        frame.graph = self
        for name in self.stood:                   # last frame's run-time words
            self.dormant.pop(name, None)
        self.stood.clear()
        pulled = self.pulled(frame)
        for node in self.order:
            if node.name not in pulled and (node.MAKES or isinstance(node, Effect)):
                continue
            if isinstance(node, Output):
                _advance_fx(frame)       # (plan 36 T4: a frame with no capture too)
            node.run(frame)

    def __repr__(self) -> str:
        return "Graph(" + " → ".join(n.name for n in self.order) + ")"


def graph_key(views: list[View]) -> tuple:
    """What selects the graph besides the wiring (plan 35 B, row 379): the
    views' count. A window's mutes, size, flips and presenter are read when
    its nodes run — a mute never rebuilds."""
    return (len(views),)


def _upstream(node: Node) -> set[int]:
    """The ids of every node `node` depends on, through its inputs and `after`."""
    ups: set[int] = set()
    todo = [node]
    while todo:
        for d in todo.pop().deps():
            if id(d) not in ups:
                ups.add(id(d))
                todo.append(d)
    return ups


# ---------------------------------------------------------------- the wired frame (plan 35 B)

def build_graph(views: list[View], wiring: Wiring | None = None, clouds: tuple[str, ...] = (),
                effects: tuple[str, ...] = (), rig: RigWires | None = None) -> Graph:
    """A wired frame as a graph (plan 35 B, rows 372 and 379): only what the
    wires reach (`reaches`: a path to an output's port, All outputs', or
    the look-back's capture) is built — `{"frame": "wired"}` alone is the
    outputs and nothing else, black. No node is made before the wires say
    it; the switches build nothing (`Graph.key` is the views' count: a mute
    is the window's, read each frame by its `Output`).

    The build, by `_Build`: every reached name its node, made once what it
    reads is made (the shape and the hands as geometry; the scene, the
    clouds and the `scene.geometry` wires' sources in wire order, drawn
    see-through when a `backdrop.scene` wire reads it; the backdrop, the
    scene laid over `backdrop.image` at `backdrop.alpha`; the look-back
    over `lookback.image`, its cover the wire into `lookback.cover` (plan
    36 T2: `scene.cover`, the scene's mask pin); each hands layer and guide
    drawing the hands node wired into its `hands` (none: empty) — a guide
    is its layer's split-out picture while that layer is built on the same
    hands, as the default graph's in-scene readout was; the clouds by the
    rig's wires into the scene (`cloud_wire`, while standing); a
    composite's and an output's depth the wire into its `depth`, an
    output's hands laid as their layer's `laid` says; effects, copies,
    composites, switches, channels, the pattern, plan 34's delays and ring
    pictures); then one `Shown` per distinct picture an output takes; then the capture (`lookback.capture`'s) after every end and
    every delay's write; then one `Output` per view, each port its own
    wire else All outputs' by the bus cable `rig` has standing (plan 36
    T1, `window_ports`; None: the rig as it ships, every cable standing),
    through its window's mutes.

    Plan 35 T4: every frame is this one's. Plan 36 T3 (W3): and nothing is
    built that the wiring does not say — None is the empty frame (`EMPTY`,
    black), and an unwired `Wiring` (the words before the wired frame) is
    refused: it is an old preset's, which the one-way migration wires
    (`graphmigrate.wired_wiring`); D1's placements are wires since `/7`, so
    none is placed here. The render nodes are named
    in the new ids (`hands`, `hands.layer`, `hands.guide`, `lookback`,
    `lookback(capture)`, `lookback(cover)`, `channel.a`, `backdrop`): the
    SYSTEM lines and `Graph.timed` say them. A wire into an output this rig
    has not open builds nothing (dormant, `no output 3 this frame`)."""
    wiring = wiring if wiring is not None else EMPTY
    if not wiring.wired:
        raise ValueError(UNWIRED_WIRING)
    g = Graph(graph_key(views), wiring)
    g.clouds = tuple(clouds)
    g.effects = tuple(effects)
    g.rig = rig if rig is not None else RigWires()
    _Build(g, wiring, len(views), g.rig).build()
    return g


def _kind(name: str) -> str | None:
    """A wired frame's kind of `name` (`wire_node_kind(…, wired=True)`)."""
    return wire_node_kind(name, wired=True)


# the order the reached names are first asked for (each makes what it reads
# first): the frame's own nodes first, as the default graph adds them
_RANKS = ("pattern", "shape", "hands", "scene", "backdrop", "layer", "guide", "lookback")


def _build_rank(name: str) -> tuple[int, str]:
    kind = _kind(name)
    return (_RANKS.index(kind) if kind in _RANKS else len(_RANKS)), name


def _effects_of(node: Node | None) -> list[Effect]:
    """The effects (copies too) a picture runs through, first first."""
    out: list[Effect] = []
    while isinstance(node, Effect):
        out.insert(0, node)
        node = node.inputs["image"]
    return out


def _laid_of(node: Node | None) -> str:
    """How a picture on an output's hands port is laid on (plan 36 T2): a
    hands layer's own `laid` (through the effects placed on it), else over."""
    while isinstance(node, Effect):
        node = node.inputs["image"]
    return getattr(node, "laid", "over") if isinstance(node, HandsLayer) else "over"


def _through_chain(node: Node | None) -> bool:
    """Whether picture `node` is a chain of copies over a composite laying a
    hands layer on — "hands through the effects" as wiring. Order only
    (plan 36 T1): such a chain is added right after the run, where the
    through pipelines ran; it shows exactly as wired."""
    while isinstance(node, Copy):
        node = node.inputs["image"]
    return isinstance(node, Composite) and isinstance(node.inputs["over"], HandsLayer)


class _Build:
    """`build_graph`'s work (plan 35 B): the reached wires made into nodes,
    added to `g` in the default graph's order (the frame's own nodes, the
    run, each through's composite and copies, the ends, the capture, the
    outputs), so the passes run as today's frame ran them."""

    def __init__(self, g: Graph, wiring: Wiring, count: int, rig: RigWires | None = None):
        self.g, self.wiring, self.count = g, wiring, count
        self.rig = rig if rig is not None else RigWires()     # plan 36 T1: the bus cables
        self.have = set(g.effects)
        wires = tuple(getattr(wiring, "wires", ()))
        # plan 35 T4: a wire into an output this rig has not open (`output.3`
        # with two windows) reaches nothing — what only it shows is not
        # built (Review Focus 2: nothing hidden is built; a window opened
        # is a new count, so a new graph that builds it); said dormant
        self.closed = [w for w in wires if _kind(w.node) == "output" and w.node != ALL_OUTPUTS
                       and int(w.node.partition(".")[2]) > count]
        self.reached = _wired_reach([w for w in wires if w not in self.closed])
        self.wires = [w for w in wires if (w.src in self.reached or w.src == GROUND)
                      and (_is_sink(w) or w.node in self.reached)]
        self.into: dict[str, list[Wire]] = {}
        for w in self.wires:
            self.into.setdefault(w.dst, []).append(w)
        self.blends = {c.name: c.blend for c in getattr(wiring, "composites", ())}
        self.copy_of = {c.name: c.of for c in getattr(wiring, "copies", ())}
        self.draws = {h.n: h.draw for h in wiring.nodes()}
        back = self._one("backdrop.image")
        self.back_channel = (back.src.partition(".")[2]
                             if back is not None and _kind(back.src) == "channel" else "")
        self.made: dict[str, Node | None] = {}       # a wire's name → what it reads as
        self.built: list[Node] = []                  # every node made, in order
        # plan 36 T2: a cloud is in the scene by the rig's wire into it
        # (`cloud_wire`), while the show has not cut it — and the scene is
        # reached by the section's own wires
        self.clouds = ([PointCloud(cloud_name(i), role) for i, role in enumerate(g.clouds)
                        if self.rig.has(cloud_wire(i))] if "scene" in self.reached else [])
        # the layers' blends (plan 36 T2: `laid` is the hands entry's own word,
        # how its layer is laid on wherever an output lays it — not one
        # global over every output)
        self.laid = {getattr(wiring, "laid_on", 1): wiring.blend}
        self.cover: Cover | None = None
        self.lookbacks: list[History] = []           # plan 36 T4: each look-back made
        self.ends: list[Shown] = []
        self._ends: dict[int, Shown] = {}
        self._names: set[str] = set()
        self._pictures: dict[int, MaskPicture] = {}  # plan 39 T2: each mask read as a picture

    # ---- the wires

    def _one(self, dst: str) -> Wire | None:
        got = self.into.get(dst)
        return got[0] if got else None

    def laid_over(self, src: str, seen: frozenset[str] = frozenset()) -> bool:
        """Whether `src`'s picture is laid over another picture: wired into
        the backdrop's scene or the `over` of a composite that blends by it
        (over, depth — "add" ignores it: black adds nothing), straight or
        through effects or cuts. A scene laid over clears see-through
        (`Scene.ground` 0) and the effects between keep that ground
        (`Effect.laid_over`), so the picture covers what is under it only
        where it draws. Plan 39 T3: a cut's `image` is a picture path like
        an effect's (its `mask` is not) — `CUT_FS` multiplies the alpha it
        is given, so the see-through ground passes through it, and where
        the mask passes the picture is what it would be without the cut.
        Plan 39 T4: a segment's `image` likewise, when its `fg` or `bg` pin
        is laid over — each is its input, cut or (before a matte, off, in
        the preview) whole, so it keeps the input's see-through ground."""
        for w in self.wires:
            if w.src != src or w.node in seen:
                continue
            kind = _kind(w.node)
            if (w.dst == "backdrop.scene"
                    or (kind == "composite" and w.port == "over"
                        and self.blends.get(w.node, "over") != "add")
                    or (kind in ("effect", "cut") and w.port == "image"
                        and self.laid_over(w.node, seen | {w.node}))
                    # plan 39 T4: a segment's image is a picture path to its
                    # fg and bg pins (each its input, cut or whole)
                    or (kind == "segment" and w.port == "image"
                        and any(self.laid_over(f"{w.node}.{p}", seen | {w.node})
                                for p in ("fg", "bg")))):
                return True
        return False

    def _from(self, dst: str) -> Node | None:
        """What the wire into `dst` reads, made (None: no wire, or nothing)
        — a mask into a picture port as its picture (`_taken`)."""
        w = self._one(dst)
        return self._taken(self.node(w.src), w) if w is not None and w.src != GROUND else None

    def _taken(self, src: Node | None, w: Wire) -> Node | None:
        """`src` as wire `w`'s port takes it (plan 39 T2, W1): a mask into a
        picture port is read through its one `MaskPicture`; anything else
        as it is."""
        if src is None or src.OUTPUT != MASK:
            return src
        kind = _kind(w.node)
        if WIRED_TAKES.get(kind, {}).get(w.port) != IMAGE:
            return src
        got = self._pictures.get(id(src))
        if got is None:
            got = self._pictures[id(src)] = self._keep(
                MaskPicture(f"{src.name}(picture)", mask=src))
        return got

    def _unique(self, name: str) -> str:
        out = name
        while out in self._names or out in (CAPTURE, COVER, LOOKBACK, BACKDROP):
            out = f"fx.{out}"
        self._names.add(out)
        return out

    def _keep(self, node: Node) -> Node:
        self._names.add(node.name)
        self.built.append(node)
        return node

    # ---- the nodes

    def node(self, name: str) -> Node | None:
        """Wire name `name`'s node, made on the first ask (what it reads
        first); a name read through (an effect whose file this build lacks)
        is what it reads."""
        if name in self.made:
            return self.made[name]
        self.made[name] = None                       # (a loop reads nothing: refused at read)
        got = self.made[name] = self._make(name)
        return got

    def _make(self, name: str) -> Node | None:
        kind = _kind(name)
        if kind == "shape":
            return self._keep(Shape("shape", faces=self._from("shape.faces")))
        if kind == "hands":
            n = split_instance(name)[1]
            return self._keep(Hands(wired_hands_name(n), draw=self.draws.get(n, "solid")))
        if kind == "layer":
            # plan 36 T2: the hands it draws are the wire into its `hands`
            # (none: an empty layer)
            n = split_instance(hands_of(name))[1]
            layer = HandsLayer(wired_layer_name(n), geometry=self._from(f"{name}.hands"))
            layer.laid = self.laid.get(n, "over")
            return self._keep(layer)
        if kind == "guide":
            hands = hands_of(name)
            src = self._one(f"{name}.hands")
            mine = self._one(f"{hands}.layer.hands")
            if (f"{hands}.layer" in self.reached and src is not None and mine is not None
                    and mine.src == src.src):
                # its layer's own split-out guide: the layer draws the same
                # hands, so it draws their guide too (one pass, as ever)
                return self.node(f"{hands}.layer")
            n = split_instance(hands)[1]
            return self._keep(Readout(wired_guide_name(n), geometry=self._from(f"{name}.hands")))
        if name == "scene.cover":
            # plan 36 T2: the scene's faces' coverage mask, made once
            if self.cover is None:
                scene = self.node("scene")
                if scene is not None:
                    self.cover = self._keep(Cover(COVER, scene=scene))
            return self.cover
        if name == "scene.depth":
            return self.node("scene")             # (a depth is its scene's: `Node.depth`)
        if kind == "scene":
            geos = [self.node(w.src) for w in self.into.get("scene.geometry", ())]
            return self._keep(Scene("scene", geometries=[*self.clouds,
                                                         *(x for x in geos if x is not None)],
                                    ground=0.0 if self.laid_over("scene") else None))
        if kind == "backdrop":
            over = self._from("backdrop.scene")
            if self.back_channel:
                # a channel straight in: the plan 32 backdrop, node for node
                under = self._keep(MediaNode(channel_name(self.back_channel), self.back_channel,
                                             alpha_of="backdrop_alpha"))
                return self._keep(Composite(BACKDROP, blend="over", over=over, under=under))
            wired = self._one("backdrop.image") is not None
            return self._keep(Composite(BACKDROP, blend="over", over=over,
                                        under=self._from("backdrop.image"),
                                        under_alpha_of="backdrop_alpha" if wired else None))
        if kind == "lookback":
            # plan 36 T2: its cover mask is the wire into `lookback.cover`;
            # T4: its `image` is what its capture records (`build`), no
            # input of the trail's
            lb = self._keep(History(name, cover=self._from(f"{name}.cover"),
                                    occluder=self._from(f"{name}.occluder")))
            self.lookbacks.append(lb)
            return lb
        if kind == "channel":
            c = name.partition(".")[2]
            nm = channel_name(c) if c != self.back_channel else f"{channel_name(c)}(wire)"
            return self._keep(MediaNode(nm, c))
        if kind == "pattern":
            w = self._one("pattern.media")
            if w is not None and _kind(w.src) == "channel":
                return self._keep(PatternNode("pattern", channel=w.src.partition(".")[2]))
            return self._keep(PatternNode("pattern", media=self._from("pattern.media")))
        if kind in ("effect", "copy"):
            return self._effect(name, kind)
        if kind == "composite":
            # plan 36 T2: its blend its own, its depth the wire into its
            # `depth` (none: no depth test)
            return self._keep(Composite(self._unique(name), blend=self.blends.get(name, "over"),
                                        under=self._from(f"{name}.under"),
                                        over=self._from(f"{name}.over"),
                                        depth=self._from(f"{name}.{DEPTH_PORT}")))
        if kind == "switch":
            return self._keep(SwitchNode(name, **{p: self._from(f"{name}.{p}")
                                                  for p in SWITCH_PORTS
                                                  if self._one(f"{name}.{p}") is not None}))
        if kind == "delay":
            return self._keep(Delay(name))
        if kind == "resize":
            # plan 34 Z: made where the wires reach it; fed by nothing, it
            # builds nothing (as an unfed effect, plan 35 R15)
            src = self._from(f"{name}.image")
            if src is None:
                self.g.dormant[name] = f"{name} is fed by nothing here: wire its input"
                return None
            return self._keep(ResizeNode(name, image=src))
        if kind == "matte":
            # plan 39 T2: as a resize — fed by nothing, it builds nothing
            src = self._from(f"{name}.image")
            if src is None:
                self.g.dormant[name] = f"{name} is fed by nothing here: wire its input"
                return None
            return self._keep(MatteNode(name, image=src))
        if kind == "cut":
            # plan 39 T3: fed no picture, it builds nothing (as a matte);
            # no mask wired, it is its picture through (the node's own rule)
            src = self._from(f"{name}.image")
            if src is None:
                self.g.dormant[name] = f"{name} is fed by nothing here: wire its image"
                return None
            return self._keep(CutNode(name, image=src, mask=self._from(f"{name}.mask")))
        if kind == "segment":
            # plan 39 T4: fed no picture, it builds nothing (as a matte) —
            # and its worker never starts
            src = self._from(f"{name}.image")
            if src is None:
                self.g.dormant[name] = f"{name} is fed by nothing here: wire its image"
                return None
            return self._keep(SegmentNode(name, image=src))
        if kind in SEGMENT_PINS and segment_pin(name) is not None:
            # plan 39 T4: a segment's pin — the matte is the segment itself
            # (as `scene.depth` is the scene), each picture a node over it
            seg_name, which = segment_pin(name)
            seg = self.node(seg_name)
            if seg is None or which == "mask":
                return seg
            return self._keep(SegmentPin(name, which, segment=seg))
        if kind == "echo":
            # plan 36 T4: a look-back's pin, a frame of its ring — the
            # look-back made first, so it records
            got = echo_of(name)
            if got is None:
                self.g.dormant[name] = f"no {name} in this build"
                return None
            self.node(got[0])
            return self._keep(EchoNode(name, got[1], lookback=got[0]))
        if kind == "dream":
            return self._keep(DreamNode(name, image=self._from(f"{name}.image")))
        if kind is not None and kind not in ("output", GROUND):
            self.g.dormant[name] = f"no {name} in this build"
        return None

    def _effect(self, name: str, kind: str) -> Node | None:
        """An effect instance's node, or a copy's (plan 35 F: `effect` its
        original's) — read through while its file is not in this build, as
        the default graph's run read through one (plan 33 R27)."""
        effect = name if kind == "effect" else self.copy_of.get(name)
        if effect is None:
            return None
        src = self._from(f"{name}.image")
        if effect not in self.have:
            self.g.dormant[name] = f"{name} — no {effect} effect in this build"
            return src
        if src is None:
            self.g.dormant[name] = f"{name} is fed by nothing here: wire its input"
            return None
        if kind == "copy":
            return self._keep(Copy(self._unique(name), effect, image=src))
        node = Effect(name, image=src, node=self._unique(name), placed="wire")
        node.laid_over = self.laid_over(name)
        return self._keep(node)

    def _end(self, src: Node) -> Shown:
        """Picture `src`'s one end."""
        got = self._ends.get(id(src))
        if got is not None:
            return got
        end = self._ends[id(src)] = Shown(f"shown({src.name})", image=src)
        self.ends.append(end)
        return end

    def _mute_hands(self, ports: list[dict], readers: list[Node]) -> None:
        """Plan 36 T1 (R9): a window's hands mute inside a through chain.
        Each composite laying a hands layer `over` at the head of a window's
        picture chain (through its effects and copies) is told the windows
        it feeds (`Composite.mute_hands`): while every one of them has its
        hands muted, it lays nothing over — a mute, read per frame, not a
        rewire. A composite (or a node of its chain) anything else reads —
        the capture, a delay, another node — keeps its hands: a mute of one
        window cannot reach another's picture."""
        chains: dict[int, tuple[Composite, set[int], set[int]]] = {}
        for i, p in enumerate(ports):
            n, mine = p["image"], set()
            while isinstance(n, Effect):
                mine.add(id(n))
                n = n.inputs["image"]
            if isinstance(n, Composite) and isinstance(n.inputs["over"], HandsLayer):
                got = chains.setdefault(id(n), (n, set(), set()))
                got[1].add(i)
                got[2].update(mine)
        for comp, windows, mine in chains.values():
            inside = mine | {id(comp)}
            foreign = any(v is not None and id(v) in inside
                          for r in readers if id(r) not in mine and not isinstance(r, Shown)
                          for v in r.inputs.values())
            comp.mute_hands = () if foreign else tuple(sorted(windows))

    # ---- the frame

    def _by_name(self, name: str) -> bool:
        """Whether every reached wire out of channel `name` goes where the
        channel is read by its letter, never by a node (plan 35 T4, carried
        from T2): `pattern.media` (`PatternNode.channel`) and, straight,
        `backdrop.image` (the backdrop's own `MediaNode`) — so the reach
        makes no second, unread node of it."""
        outs = [w for w in self.wires if w.src == name]
        return bool(outs) and all(w.dst in ("pattern.media", "backdrop.image") for w in outs)

    def build(self) -> None:
        g = self.g
        for name in sorted(self.reached, key=_build_rank):
            if _kind(name) == "channel" and self._by_name(name):
                continue
            self.node(name)
        for w in self.closed:
            if w.src != GROUND:
                n = w.node.partition(".")[2]
                g.dormant[str(w)] = f"wire {w} — no output {n} this frame"
        # plan 34 D: each delay's write, once every node is made (a loop
        # through a delay reads last frame's picture: no dependency)
        writes = []
        for d in [n for n in self.built if isinstance(n, Delay)]:
            src = self._from(f"{d.name}.image")
            if src is not None:
                writes.append(self._keep(DelayWrite(f"{d.name}(write)", d.name, image=src)))
        self._aux()
        # the run: All outputs' picture back through its effects (what
        # `frame.fx_on` asks, as of the pipelines' runs)
        run: list[Effect] = []
        n = self._from(f"{ALL_OUTPUTS}.image")
        while isinstance(n, Effect) and not isinstance(n, Copy) and n not in run:
            run.insert(0, n)
            n = n.inputs["image"]
        for e in run:
            e.placed = None
        g.run = tuple(e.effect for e in run)
        # each output's ports (plan 36 T1, `window_ports`): its own wire,
        # else All outputs' by the rig's bus cable while it stands
        # (`ground`, or nothing: nothing) — no other fallback
        ports = []
        for i in range(self.count):
            got = {}
            for p, w in window_ports(self.wires, i + 1, self.rig).items():
                got[p] = (self._taken(self.node(w.src), w)
                          if w is not None and w.src != GROUND else None)
            ports.append(got)
        layers = tuple(n for n in self.built if isinstance(n, HandsLayer))
        shown = [self._end(p["image"]) if p["image"] is not None else None for p in ports]
        for end in self.ends:
            # (the users an end counts are settled through the layers'
            # pictures, `Output.settle`: the layers run first)
            end.after = layers
            end.chained = any(e.effect in g.run for e in _effects_of(end.inputs["image"]))
        # plan 36 T4: each look-back's capture, what is wired into its
        # `image`, after every reader of its trail
        laid = [x for p in ports for x in (p["hands"], p["guide"]) if x is not None]
        helds: list[Node] = []
        captures: list[Capture] = []
        for lb in self.lookbacks:
            held = self._from(f"{lb.name}.image")
            if held is None:
                continue
            helds.append(held)
            captures.append(Capture(capture_name(lb.name), lookback=lb.name, image=held,
                                    after=tuple(dict.fromkeys([*self.ends, *writes, *laid]))))
        if self.cover is not None:
            self.cover.wanted_by = tuple(lb.name for lb in self.lookbacks
                                         if lb.inputs["cover"] is self.cover)
        outputs = []
        for i, (p, end) in enumerate(zip(ports, shown)):
            # plan 36 T2: the hands laid on as their layer says (`laid`, its
            # hands entry's), depth-aware against the wire into `depth`
            outputs.append(Output(f"output.{i + 1}", i, after=tuple(captures),
                                  blend=_laid_of(p["hands"]), image=end,
                                  hands=p["hands"], readout=p["guide"],
                                  depth=p[DEPTH_PORT] if p["hands"] is not None else None))
        self._mute_hands(ports, [*self.built, *self.ends, *writes, *captures])
        # into the graph in the default graph's order: the frame's own
        # nodes, the run, each through's composite and copies, the
        # capture's picture, the ends, the writes, the capture, the outputs
        made = self.made
        roots: list[Node | None] = [*self.clouds, made.get("pattern"), made.get("shape")]
        roots += [n for n in self.built if isinstance(n, Hands)]
        roots += [made.get("scene"), self.cover]
        roots += [n for n in self.built if isinstance(n, MediaNode) and n.alpha_of]
        roots += [n for n in self.built if n.name == BACKDROP and isinstance(n, Composite)]
        roots += [*layers, *(n for n in self.built if isinstance(n, Readout))]
        roots += [n for n in self.built if isinstance(n, History)]
        # (each end right after its chain, as each pipeline's `Fx` was: an
        # effect placed into an output sits after it, `Graph.insert`)
        head = self._from(f"{ALL_OUTPUTS}.image")
        roots += [*run, self._ends.get(id(head)) if head is not None else None]
        for end in shown:
            if end is not None and _through_chain(end.inputs["image"]):
                roots += [*_effects_of(end.inputs["image"]), end]
        roots += [*helds, *self.ends, *writes, *captures, *outputs, *self.built]
        seen: set[int] = set()

        def add(node: Node | None) -> None:
            if node is None or id(node) in seen:
                return
            seen.add(id(node))
            for d in node.deps():
                add(d)
            g.add(node)

        for node in roots:
            add(node)
        # (plan 36 T3: no placement step — D1's are the wires they stood for)
        self._split(layers)
        g.placed_names = frozenset(
            n.effect for n in g.nodes.values() if isinstance(n, Effect) and n.placed)
        g.relink()

    def _aux(self) -> None:
        """Each aux wire on its effect's or copy's `aux` port (plan 32 R): a
        source the effect feeds (a loop) is dormant, in words."""
        for w in self.wires:
            if w.port != AUX or _kind(w.node) not in ("effect", "copy"):
                continue
            target, src = self.made.get(w.node), self._taken(self.node(w.src), w)
            if not isinstance(target, Effect) or target not in self.built or src is None:
                continue
            if src is target or id(target) in _upstream(src):
                self.g.dormant[str(w)] = f"wire {w} — {w.node} feeds {w.src}: that makes a loop"
                continue
            target.inputs[AUX] = src

    def _split(self, layers: tuple[HandsLayer, ...]) -> None:
        """How each layer splits its guide out (`HandsLayer.split`): always
        while its hands are also in the scene or an effect reads the layer
        (the guide is never folded), else while an effect it reaches is
        live (the copies a through output wires)."""
        readers: dict[int, list[Node]] = {}
        for c in self.g.nodes.values():
            for src in c.inputs.values():
                if src is not None:
                    readers.setdefault(id(src), []).append(c)
        scene = self.made.get("scene")
        held = set(map(id, scene.geometries())) if isinstance(scene, Scene) else set()
        for layer in layers:
            on = any(isinstance(c, Effect) and not isinstance(c, Copy)
                     and c.inputs.get("image") is layer for c in readers.get(id(layer), ()))
            if id(layer.inputs["geometry"]) in held or on:
                layer.readout = "always"
                continue
            down: list[str] = []
            todo, seen = [layer], set()
            while todo:
                n = todo.pop()
                for c in readers.get(id(n), ()):
                    # (past an end an effect folds an output's picture: not
                    # the layer bent before it, as D1's `into` never split it)
                    if id(c) in seen or isinstance(c, (Output, Capture, DelayWrite, Shown)):
                        continue
                    seen.add(id(c))
                    if isinstance(c, Effect) and c.effect not in down:
                        down.append(c.effect)
                    todo.append(c)
            layer.readout = "downstream"
            layer.downstream = tuple(down)


# ---------------------------------------------------------------- the proof (plan 35 B)

def _sig_class(n: Node) -> str:
    """A node's class in `signature`: a copy is the effect it draws again
    (each pipeline's own run node was an `Effect`: plan 35 V)."""
    return "Effect" if isinstance(n, Copy) else type(n).__name__


def _sig_what(n: Node) -> Any:
    """Which one of its class a node is, past its name (plan 35 T3): an
    effect's instance, a channel's letter, a hands node's (its layer's,
    its guide's) instance, a look-back frame's index."""
    if isinstance(n, Effect):
        return n.effect
    if isinstance(n, (MediaNode, PatternNode)):
        return getattr(n, "channel", None)
    if isinstance(n, Hands):
        return split_instance(n.name)[1]
    if isinstance(n, (HandsLayer, Readout)):
        # (plan 35 T4: named `hands.2.layer` now — the instance of its hands)
        return split_instance(hands_of(n.name))[1]
    if isinstance(n, EchoNode):
        return n.name
    return None


def _sig_chain(n: Node | None, depth: int = 0) -> tuple | None:
    """`n`'s picture back to its sources, as (class, which, ((port, what it
    reads), …)) over every port that is wired — an effect's `image` and
    `aux`, a switch's `inN`, a composite's `under`, `over` and `depth`, the
    look-back's `cover` and `occluder`, the scene's geometry (plan 35 T3:
    every port, named, recorded before T4 deleted the oracle); an end
    (`Shown`) is passed through, so its name never counts."""
    while isinstance(n, Shown):
        n = n.inputs.get("image")
    if n is None or depth > 64:
        return None
    ins = tuple((p, _sig_chain(v, depth + 1)) for p, v in sorted(n.inputs.items())
                if v is not None)
    return (_sig_class(n), _sig_what(n), ins)


def _live_nodes(g: Graph) -> set[int]:
    """The nodes an output, the capture or a delay's write reads (through
    their inputs — plan 36 T2: the faces' pattern too, a wire now): what the
    frame can show. The retired default graph built
    pipelines no output took (an output whose picture a wire replaced):
    those were not in `signature`, as recorded."""
    todo = [n for n in g.order if isinstance(n, (Output, Capture, DelayWrite))]
    seen: set[int] = set()
    while todo:
        n = todo.pop()
        if id(n) in seen:
            continue
        seen.add(id(n))
        todo += [v for v in n.inputs.values() if v is not None]
    return seen


def signature(g: Graph) -> tuple:
    """What a graph shows, node for node (plan 35 B, Review Focus 1): per
    output, (its index, its picture's chain, its hands', its guide's, its
    blend, its depth's, and None — where its end's stand-down was, plan 36
    T1, kept so the recorded signatures keep their shape); then every node the
    frame can show (`_live_nodes`) in the graph's order but the outputs,
    the ends (`Shown`; the retired `Fx` and `Wired` when it was recorded)
    and the old backdrop sink (which drew nothing), each (class, which, the
    ports wired).
    Names never count — `fx` and `shown(lookback)` are one end — and a
    copy counts as the `Effect` it draws again. Plan 35 T3: a chain
    follows every wired port by name, and "which" is past the effect
    (`_sig_what`: a channel's letter, a hands node's instance); last, each
    sink no output shows — the capture, each delay's write — by the chain
    of what it reads."""
    outs = []
    for out in g.outputs:
        outs.append((out.index, _sig_chain(out.inputs["image"]),
                     _sig_chain(out.inputs["hands"]), _sig_chain(out.inputs["readout"]),
                     out.blend, _sig_chain(out.inputs["depth"]), None))
    live = _live_nodes(g)
    order = tuple((_sig_class(n), _sig_what(n),
                   tuple(sorted(k for k, v in n.inputs.items() if v is not None)))
                  for n in g.order
                  if id(n) in live and not isinstance(n, (Output, Shown, BackdropNode)))
    # (T3 review: the sinks no output shows — what the look-back records and
    # what each delay writes — by what they read, port by port)
    sinks = tuple((_sig_class(n), getattr(n, "delay", None),
                   tuple((p, _sig_chain(v)) for p, v in sorted(n.inputs.items())
                         if v is not None))
                  for n in g.order if isinstance(n, (Capture, DelayWrite)))
    return (*outs, order, sinks)
