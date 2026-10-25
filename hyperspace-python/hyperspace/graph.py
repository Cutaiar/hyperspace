"""The render graph (plan 26 A1, A3, A4): the frame as nodes, evaluated in
dependency order.

`Renderer._draw_frame` (render.py) used to be a fixed list of passes.
It is now "build or reuse the graph for this frame's views, evaluate
it": `build_graph` builds the frame as nodes from the renderer's
`Wiring` — plan 35 (rows 372, 377): a wired frame, every node of it an
ordinary node a wire reaches; an unwired wiring is wired first as a load
wires it (`wired`), `Wiring()` the factory look — and `Graph.evaluate`
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
- **History** (`History`, `Capture`): the look-back (`lookback.Lookback`)
  as two nodes, because its composite must read the ring before the
  frame's capture changes it: `lookback` lays the echoes and the dream
  over its input; `lookback(capture)` puts what `lookback.capture` is
  wired to — the scene, or the scene with the hands' layer (A3) — into
  the ring after every composite of the frame has run.
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
Each output is wired to its end; per frame a through output's copies
whose layer is not bent — no copy live, or no hand drawn — stand down for
the originals over what the layer was laid onto, with the layer laid over
at the output instead (`Shown.fallback`, `Output.settle`). An end with no
output this frame is skipped and its nodes read 0 ms.

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

import functools
import math
import re
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar

import moderngl
import numpy as np

from .geometry import EYE_DISTANCE, EYE_FOV, EYE_NEAR, eye_matrix
from .lookback import MAX_ECHOES
from .outputs import View
from .view import RESIZE_ASPECTS, RESIZE_FILTERS, RESIZE_FITS, RESIZE_SIDES, ResizeState

# port types: a colour picture at the frame's size, a one-channel mask at
# the frame's size, or draw calls (a geometry, drawn by its scene or layer)
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


def media_name(c: str) -> str:
    """Channel `c`'s name as a wire's end before the wired frame (the old
    id): `media.a` …"""
    return f"media.{c}"


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


def readout_name(n: int) -> str:
    """The old id of the n-th hands node's readout alone: `readout`,
    `readout.2`, … (plan 35 V2: `hands.guide`, `wired_guide_name`)"""
    return "readout" if n == 1 else f"readout.{n}"


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
    the factory look — is wired as a load would wire it first
    (`graph.wired`, `graphmigrate.wired_of`): where the hands are drawn,
    how their layer is laid on, what the history captures.
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
    # (the wire `media.<c> → backdrop.image`); `backdrop_history` stays a
    # value the renderer lays on per frame (`Renderer.backdrop_wiring`), so
    # the graph is built again only when one changes
    backdrop: str = ""
    backdrop_history: bool = False
    run: tuple[str, ...] | None = None
    # plan 35 F: a wired frame's (`GraphSpec.wired`): `wires` holds every
    # wire, and any hands node may have a layer (row 380). T2's builder reads
    # it; T1 sets it so a wired section reads
    wired: bool = False
    # plan 35 F: a wired frame's copies (`CopyAt`: each one's `of`), by instance
    copies: tuple[CopyAt, ...] = ()

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
# and the wired frame's `copy` (`copy.<n>`) and the source word `ground`
RESERVED = ("frame", "fx", "pattern", "shape", "backdrop", "switch", "delay", "resize", "echo",
            "dream", "copy", "ground")
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
    put (`build_graph`, `_place`)."""

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
        _entry_keys(e, "lookback", ())
        return LookbackAt()
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
_ECHO = re.compile(r"echo\.[1-9][0-9]*")
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
    loop drawn through one is legal (`wire_loops`, `sink_loops`) —
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
    """The look-back's dream buffer as a source (plan 34 L, E): `dream`,
    one only (`n` is always 1, so `read_graph`'s two-of-one-instance check
    holds it to one)."""

    @property
    def n(self) -> int:
        return 1

    @property
    def name(self) -> str:
        return "dream"

    def to_json(self) -> dict:
        return {"kind": "dream"}


def _dream_entry(e: dict) -> DreamAt:
    _entry_keys(e, "dream", ())
    return DreamAt()


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
ALL_OUTPUTS = "output.all"    # what every output shows unless its own port is wired
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
# (reader, read) edges no wire says: the shape reads the faces pattern while
# `shape.faces` is unwired (`reaches`) …
IMPLICIT_EDGES = (("shape", "pattern"),)
# … and the edges `sink_loops` walks in a wired frame (row 393: plan 34's
# `FRAME_EDGES` less what the wires now say): that one, and the cover the
# look-back makes from the scene's face buffer
HIDDEN_EDGES = (("shape", "pattern"), ("lookback", "scene"))

GONE_IN_A_WIRED_FRAME = ("{name} is gone in a wired frame (plan 35): wire the picture "
                         "straight into an effect, a composite or an output")
HOLDS_IS_A_WIRE = ("lookback holds: in a wired frame what the look-back records is a wire "
                   "— wire a picture into lookback.capture")
INTO_IS_A_WIRE = ("{hands} into: in a wired frame the hands go into the scene by a wire — "
                  "wire {hands} into scene.geometry")
FRAME_VALUE = "frame {value!r}: the one value is \"wired\""
GEOMETRY_INTO_SCENE = "{src} makes geometry: it goes into scene.geometry"
COPY_NO_OF = "copy {name}: names no of (the effect instance it draws again)"
COPY_BAD_OF = "copy {name}: of {of!r} is no effect instance of this graph"
GROUND_ONLY_INTO_OUTPUTS = "ground goes only into an output's port: it shows nothing there"
OLD_ID_IN_A_WIRED_FRAME = "{old} is the old name (plan 35): in a wired frame it is {new}"
# (a frame kind's entry outside a wired frame: plan 34's table has no such node)
FRAME_KIND_UNWIRED = ("{kind} node: only in a wired frame (plan 35: the section says "
                      "\"frame\": \"wired\")")

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
    """The hands node a layer or a guide of a wired frame draws, by name:
    `hands.2.layer` → `hands.2`, `hands.guide` → `hands`."""
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
    for kind, pat in (("hands", _HANDS_W), ("layer", _LAYER_W), ("guide", _GUIDE_W),
                      ("output", _OUTPUT), ("composite", _COMPOSITE), ("channel", _CHANNEL),
                      ("switch", _SWITCH), ("delay", _DELAY), ("resize", _RESIZE),
                      ("echo", _ECHO), ("copy", _COPY)):
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
    """The look-back (was `history`, row 381): echoes and the dream over
    `lookback.image`, recording `lookback.capture`. It replaces `HistoryAt`
    in a wired frame; what it holds is the capture wire."""

    KIND: ClassVar[str] = "lookback"


@dataclass(frozen=True)
class _HandsPictureAt:
    """A picture of the n-th hands node (plan 35 F, row 380): drawn from
    `hands[.n]` by name, no geometry wire."""

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
DECLARED = ("composite", "switch", "delay", "resize", "echo", "dream", "copy", *FRAME_KINDS)


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

    def declared(self, kind: str) -> frozenset[str]:
        """The names of kind `kind` (one of `DECLARED`) the section declares
        (a frame kind's: none here — a wire of a wired frame declares it)."""
        return {"composite": self.composites, "switch": self.switches, "delay": self.delays,
                "resize": self.resizes, "echo": self.echoes, "copy": self.copies,
                "dream": frozenset({"dream"}) if self.dream else frozenset()
                }.get(kind, frozenset())


FX_IMAGE_REFUSAL = ("fx.image takes the run from frame; to replace an output's picture "
                    "wire it into output.N.image")
# plan 34 L: `frame` exists only as the run's head (it is the history's
# picture as the pipeline starts its effects), so a wire out of it goes into
# the run's first effect or `fx.image`, nowhere else
FRAME_SOURCE_REFUSAL = ("frame is the run's head: it goes into the run's first effect or "
                        "fx.image — the picture before the effects is history, after them "
                        "the run's last effect")
# plan 34 L: the default graph's hidden edges — (node, what it reads) — that
# no wire says: the faces are drawn inside the scene, the faces read the
# pattern's layer, the history composites the scene and the backdrop under
# it, and `frame` is the history's picture. `sink_loops` counts them
FRAME_EDGES = (("scene", "shape"), ("shape", "pattern"), ("history", "scene"),
               ("history", "backdrop"), ("frame", "history"))
# the words for a loop the hidden edges close (`loop_words`): which one it
# runs through, and the delay that makes it legal
LOOP_FACES = ("that makes a loop through the faces ({path}): the faces are drawn inside "
              "the scene — wire it through a delay for last frame's picture")
LOOP_BACKDROP = ("that makes a loop through the backdrop ({path}): the backdrop lies under "
                 "the scene's picture — wire it through a delay for last frame's picture")
LOOP_FRAME = ("that makes a loop through the frame ({path}): frame is the history's "
              "picture — wire it through a delay for last frame's picture")


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
    # plan 34 L: `frame` feeds the run only — but a wire out of it that the
    # hidden edges alone close into a loop (`frame → shape.faces`) is said
    # as that loop, by `sink_loops`, which names the delay to put between
    if (w.src == "frame" and w.dst != "fx.image" and not (kind == "effect" and port == "image")
            and not sink_loops([w])):
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
# backdrop lays `scene` over `image`; the look-back records `capture`; a
# copy is an effect's; an output and All outputs take a picture, the hands
# over it and the guide over all; `ground` makes nothing, as a picture
WIRED_MAKES = {"scene": IMAGE, "shape": GEOMETRY, "hands": GEOMETRY, "layer": IMAGE,
               "guide": IMAGE, "lookback": IMAGE, "channel": IMAGE, "backdrop": IMAGE,
               "copy": IMAGE, "output": None, GROUND: IMAGE, "effect": IMAGE,
               "composite": IMAGE, "pattern": IMAGE, "switch": IMAGE, "delay": IMAGE,
               "resize": IMAGE, "echo": IMAGE, "dream": IMAGE}
WIRED_TAKES: dict[str, dict[str, str]] = {
    "scene": {"geometry": GEOMETRY}, "shape": {"faces": IMAGE},
    "hands": {}, "layer": {}, "guide": {}, "channel": {}, GROUND: {},
    "lookback": {"image": IMAGE, "capture": IMAGE, "occluder": IMAGE},
    "backdrop": {"image": IMAGE, "scene": IMAGE},
    "copy": {"image": IMAGE, "aux": IMAGE},
    "output": {"image": IMAGE, "hands": IMAGE, "guide": IMAGE},
    **{k: WIRE_TAKES[k] for k in ("effect", "composite", "pattern", "switch", "delay",
                                  "resize", "echo", "dream")},
}
WIRED_TO_WORDS = ("output.1 …, output.all (image, hands, guide), scene.geometry, "
                  "shape.faces, backdrop.image / scene, lookback.image / capture / occluder, "
                  "pattern.media, an effect's or a copy's image or aux, a composite's under / "
                  "over, a switch's in1 … in8, or a delay's or a resize's image")
WIRED_FROM_WORDS = ("scene, shape, hands …, hands.layer …, hands.guide …, lookback, "
                    "backdrop, pattern, an effect, a copy, a composite, a switch, a delay, "
                    "a resize, echo.1 …, dream, a channel (channel.a …) or ground")
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
    node, port = w.node, w.port
    kind = wire_node_kind(node, wired=True)
    if kind is None:
        return f"no input {w.dst!r}: a wire goes into {WIRED_TO_WORDS}"
    if kind == "output" and new_id(w.dst) != w.dst:
        return OLD_ID_IN_A_WIRED_FRAME.format(old=w.dst, new=new_id(w.dst))
    takes = WIRED_TAKES[kind]
    if port not in takes:
        names = list(takes) if len(takes) < 4 else [next(iter(takes)), "…", [*takes][-1]]
        said = f"it takes {', '.join(names)}" if takes else "nothing is wired into it"
        return f"{node} has no port {port!r} ({said})"
    if src_kind == GROUND and kind != "output":
        return GROUND_ONLY_INTO_OUTPUTS
    makes, want = WIRED_MAKES[src_kind], takes[port]
    if makes == GEOMETRY and want != GEOMETRY and kind != "output":
        return GEOMETRY_INTO_SCENE.format(src=w.src)
    if makes != want:
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
        if k in DECLARED and k not in FRAME_KINDS and name not in ctx.declared(k):
            entry = (f'{{"kind": "echo", "index": {split_instance(name)[1]}}}' if k == "echo"
                     else f'{{"kind": "{k}"}}')
            return f"no {name} node in this graph (add one: {entry})"
    if w.src == node:
        return f"{node} into itself makes a loop"
    if kind == "output" and port == "guide" and src_kind not in ("layer", "guide", GROUND):
        return f"{w.dst} takes a hands layer or a hands guide (hands.layer, hands.guide …)"
    if kind == "composite" and port == "over" and src_kind == "lookback":
        return _LAID_OVER.format(name="lookback")
    if kind == "output" and port == "hands" and src_kind == "lookback":
        return _LAID_OVER_OUTPUT.format(name="lookback")
    for name, k, into in ((node, kind, port != AUX), (w.src, src_kind, False)):
        if k == "effect" and name in ctx.placed and (into or kind != "effect"):
            key, where = ctx.placed[name]
            return f"{name} sits {key} {where!r} already (its node says so): one place"
    return None


def _later(w: Wire, wired: bool) -> bool:
    """Whether wire `w` is read only after this frame (no dependency, never
    on a loop): one into a delay (plan 34 L: its picture is last frame's)
    or (plan 35 F) into `lookback.capture`, which the ring records for the
    frames after, once every end has run."""
    return (wire_node_kind(w.node, wired=wired) == "delay"
            or (wired and w.dst == "lookback.capture"))


def wire_loops(wires: list[Wire], wired: bool = False) -> dict[Wire, str]:
    """The wires on a loop — a node reading, through wires, its own
    picture — each with the loop in words (`acid.2 → palette → acid.2`).
    A wire makes its node depend on its source — but (plan 34 L) a wire
    into a delay: a delay's picture is last frame's, so it depends on
    nothing this frame, and such a wire is never on a loop. Plan 35 F:
    `wired`, a wired frame's wires (`_later`: the capture's too)."""
    deps: dict[str, set[str]] = {}
    for w in wires:
        if not _later(w, wired):
            deps.setdefault(w.node, set()).add(w.src)
    out: dict[Wire, str] = {}
    for w in wires:
        if _later(w, wired):
            continue
        path = _loop_path(deps, w)
        if path is not None:
            out[w] = " → ".join(path)
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


def sink_loops(wires: list[Wire], wired: bool = False) -> dict[Wire, str]:
    """The wires that close a loop through the default graph's hidden edges
    (plan 34 L: `FRAME_EDGES` — the faces drawn in the scene, the history
    over the scene and the backdrop, `frame` the history's picture), each
    with the refusal in words (`loop_words`). Walked in `wires`' order over
    the hidden edges and the wires already taken: an earlier wire stands,
    so the one refused is the wire that closes the loop (a drag's own,
    appended last). A wire into a delay is no dependency (z⁻¹: the loop
    through one is the point). `wire_loops` has refused the explicit loops
    first; what it would refuse is left to it.

    Plan 35 F (row 393): in a wired frame (`wired`) the wires say most of
    those edges themselves (`shape → scene.geometry`, `scene →
    backdrop.scene`, `backdrop → lookback.image`), and the walk counts the
    two left hidden, `HIDDEN_EDGES`, in place of `FRAME_EDGES`."""
    deps: dict[str, set[str]] = {}
    for node, reads in (HIDDEN_EDGES if wired else FRAME_EDGES):
        deps.setdefault(node, set()).add(reads)
    out: dict[Wire, str] = {}
    for w in wires:
        if _later(w, wired):
            continue
        path = _loop_path(deps, w)
        if path is None:
            deps.setdefault(w.node, set()).add(w.src)
            continue
        out[w] = loop_words(" → ".join(path), _hops(path), wired=wired)
    return out


def _hops(path: list[str]) -> set[tuple[str, str]]:
    """A loop's (reader, read) edges, its names each read by the next."""
    return {(path[i + 1], path[i]) for i in range(len(path) - 1)}


def loop_words(path: str, hops: set[tuple[str, str]], wired: bool = False) -> str:
    """The refusal for a loop `path` (`shape → scene → shape`) whose
    (reader, read) edges are `hops`: through the faces when it runs
    through the scene drawing the faces, else through the backdrop when
    it runs through the history over the backdrop, else through the frame.

    Plan 35 F: in a wired frame (`wired`) through the faces is any wire into
    `scene.geometry` (the scene's one port), through the backdrop a wire
    into `backdrop.scene` or the look-back over the backdrop, and any other
    loop has `wire_loops`' words — there is no frame."""
    if ("scene", "shape") in hops or (wired and any(r == "scene" for r, _ in hops)):
        return LOOP_FACES.format(path=path)
    if ("history", "backdrop") in hops or (
            wired and (("lookback", "backdrop") in hops or ("backdrop", "scene") in hops)):
        return LOOP_BACKDROP.format(path=path)
    return f"that makes a loop ({path})" if wired else LOOP_FRAME.format(path=path)


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
    # (`_place`, on the built graph), not a second wire into it — so an
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
            why = (loop_words(loops[w], _hops(loops[w].split(" → ")), wired=True)
                   if ctx.wired else f"that makes a loop ({loops[w]})")
            notes.append(f"wire {w} — {why}")
    # plan 34 L: then a loop through the default graph's hidden edges — the
    # faces, the backdrop, the frame — refused here, in words, not left to
    # land dormant at build (`_Wiring._sink` stays the backstop)
    sinks = sink_loops([*d1, *ok], wired=ctx.wired)
    for w in list(ok):
        if w in sinks:
            ok.remove(w)
            notes.append(f"wire {w} — {sinks[w]}")
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
        (`graphmigrate.has_frame_run`) shortens nothing, so its placements
        are D1's own entries and every other wire is an edge."""
        first = next((h for h in self.hands if h.n == 1), HandsAt())
        placed = tuple(e for e in self.effects if e.placed)
        if self.wired:
            # plan 35 F: a wired frame's wires are every wire, as they stand
            # (no run, no shortening, no backdrop channel); T2 builds them
            return Wiring(draw=first.draw, extra=tuple(h for h in self.hands if h.n != 1),
                          blend=self.laid, placed=placed, wires=self.wires,
                          composites=self.composites(), wired=True, copies=self.copies)
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
    def echoes(self) -> tuple[EchoAt, ...]:
        """The look-back frames the section reads (plan 34 L), by index."""
        return self._of("echo")

    @property
    def dream(self) -> DreamAt | None:
        """The dream buffer's node, when the section reads it (plan 34 L)."""
        return next((got for k, got in self.others if k == "dream"), None)

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

    def to_json(self) -> dict:
        """The section as a preset writes it: every node that is not the
        default, in a fixed order (hands by instance, effects by file and
        instance, the history, then later kinds' entries as read)."""
        nodes: list[dict] = []
        layer = self.laid_on if self.wired else self.wiring().layer_node().n
        hands = {h.n: h for h in self.hands}
        if layer not in hands and self.laid != "over":
            hands[layer] = HandsAt(layer)
        for n in sorted(hands):
            h = hands[n]
            d: dict[str, Any] = {"kind": "hands"}
            if h.n != 1:
                d["instance"] = h.n
            if h.into != "layer":
                d["into"] = h.into
            if h.draw != "solid":
                d["draw"] = h.draw
            if h.n == layer and self.laid != "over":
                d["laid"] = self.laid
            if len(d) > 1:
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


def read_graph(section: Any, effects: set[str] | frozenset[str] | None = None) -> GraphSpec:
    """A preset's `graph` section → its `GraphSpec`; raises `GraphError`
    (the reason in words) for anything this build cannot read — a kind
    not in `NODE_KINDS`, a key a node does not take, a value out of its
    choices, two nodes of one instance, two hands layers, `laid` on a
    hands node that makes no layer. The caller notes it and takes the
    default graph.

    Plan 30 D1: a placement this build cannot honour is not a reason to
    drop the graph — both keys at once, a name that is not a string or
    not in the placeable vocabulary (`placement_error`; `effects`: the
    effect files on disk, so `after: "teapot"` is refused — None takes
    any well-formed effect name), or a loop of placed effects
    (`placement_loops`) — the effect takes the default placement (plan
    33: where its wires put it, none for an instance on no wire) and the
    reason rides in `GraphSpec.notes`."""
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
                   echoes=frozenset(e.name for e in spec.echoes),
                   dream=spec.dream is not None,
                   placed={e.name: e.where for e in effects_at if e.placed},
                   wired=wired, copies=frozenset(c.name for c in spec.copies))
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
    # (plan 35 T3: a wired frame's run is the look-back's into All outputs)
    runs = ((("lookback", f"{ALL_OUTPUTS}.image"),) if ctx.wired else (("frame", "fx.image"),))
    missing = {e for head, end in (*runs, ("pattern", "shape.faces"))
               for e in run_of(probe, head, end) if split_instance(e)[0] not in files}
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
    geometry goes into a port of a reached node; the shape reads the faces
    pattern (`IMPLICIT_EDGES`) while `shape.faces` is unwired and the
    section has a pattern. `ground` is no node: it reaches nothing."""
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
    wires = spec.all_wires()
    has_pattern = any(isinstance(n, PatternAt) for n in spec.frame_nodes)
    return _wired_reach(wires, has_pattern)


def _wired_reach(wires, has_pattern: bool = False) -> frozenset[str]:
    """The names a wired frame's `wires` reach from the sinks (`reaches`,
    and the builder's own: plan 35 B builds only these); `has_pattern`, the
    section declares the faces pattern."""
    wires = [w for w in wires if w.src != GROUND]
    into: dict[str, list[str]] = {}
    for w in wires:
        into.setdefault(w.node, []).append(w.src)
    has_pattern = has_pattern or any("pattern" in (w.src, w.node) for w in wires)
    if has_pattern and not any(w.dst == "shape.faces" for w in wires):
        for node, reads in IMPLICIT_EDGES:
            into.setdefault(node, []).append(reads)
    todo = [w.src for w in wires if _is_sink(w)]
    got: set[str] = set()
    while todo:
        name = todo.pop()
        if name in got:
            continue
        got.add(name)
        todo.extend(into.get(name, ()))
    return frozenset(got)


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

def output_ports(wiring: Wiring, n: int) -> dict[str, str | None]:
    """Output `n`'s three ports under a wired frame (plan 35 T4, `wired`):
    each port's source, its own wire else All outputs' — None where nothing
    is wired or `ground` is."""
    w = wired(wiring)
    own = {x.port: x.src for x in w.wires if x.node == f"output.{n}"}
    alls = {x.port: x.src for x in w.wires if x.node == ALL_OUTPUTS}
    out: dict[str, str | None] = {}
    for p in ("image", "hands", "guide"):
        src = own.get(p, alls.get(p))
        out[p] = None if src == GROUND else src
    return out


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


def through_of(wiring: Wiring, n: int) -> tuple[str, str | None] | None:
    """(the hands layer output `n` puts through the effects, what it is laid
    over — None: nothing, the hands alone) — plan 35 M: its picture a chain
    over a composite whose `over` is a layer, "hands through the effects"
    as wiring — or None."""
    w = wired(wiring)
    head = _picture_head(w, output_ports(w, n)["image"])
    if wire_node_kind(head or "", wired=True) != "composite":
        return None
    over = next((x.src for x in w.wires if x.dst == f"{head}.over"), None)
    if wire_node_kind(over or "", wired=True) != "layer":
        return None
    return over, next((x.src for x in w.wires if x.dst == f"{head}.under"), None)


def through_layer(wiring: Wiring, n: int) -> str | None:
    """The hands layer output `n` puts through the effects (`through_of`), or None."""
    got = through_of(wiring, n)
    return got[0] if got is not None else None


def in_scene_hands(wiring: Wiring) -> list[int]:
    """The hands nodes wired into the scene (`wired`), by instance."""
    return sorted(split_instance(x.src)[1] for x in wired(wiring).wires
                  if x.dst == "scene.geometry" and wire_node_kind(x.src, wired=True) == "hands")


def hands_words(wiring: Wiring, sw, n: int = 1) -> str:
    """Where output `n`'s hands come from, in words (the OUTPUT page, plan
    26 A4; plan 35 T4: read off the wires, `wired`): `hands: in the scene`
    (a hands node wired into `scene.geometry`, while its picture shows),
    `hands: through FX` (its picture a chain over the layer laid on:
    `through_layer`) or `hands: over` (a layer on its `hands` port) — with
    the hands node's number when the graph has more than one, `as lines`
    for a node drawn as lines, and how a layer is laid on when it is not
    plainly over (`· depth-aware`, `· added`). `hands: off` with the
    window's hands muted — but an output whose scene holds the hands says
    so whatever its mute."""
    w = wired(wiring)
    inside = in_scene_hands(w)
    thru = through_of(w, n)
    if (inside and sw.scene and output_ports(w, n)["image"] is not None
            and not (thru is not None and thru[1] is None)):
        # the scene holds the hands whatever this window's hands mute says
        # (that mute then mutes only the guide)
        return "hands: " + " · ".join(f"in the scene{_node_words(w, k)}" for k in inside)
    if not sw.hands:
        return "hands: off"
    if thru is not None:
        return f"hands: through FX{layer_words(w, thru[0])}"
    over = output_ports(w, n)["hands"]
    return f"hands: over{layer_words(w, over)}"


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
    w = wired(wiring)
    if layer is None:
        layer = output_ports(w, 1)["hands"]
    k = (split_instance(hands_of(layer))[1]
         if wire_node_kind(layer or "", wired=True) == "layer" else 1)
    words = _node_words(w, k)
    if w.blend != "over":
        words += " · depth-aware" if w.blend == "depth" else " · added"
    return words


def lookback_words(wiring: Wiring) -> str:
    """What the look-back records, in words (the LOOKBACK page, plan 26 A4;
    plan 35 T4: the wire into `lookback.capture`, `wired`): `history: the
    scene`, or `history: the scene · with the hands` — the hands' layer
    laid on in a composite, or hands drawn inside the scene. Plan 30 D1:
    then each effect placed on the look-back's way in or after it (`acid 2
    before the history`); plan 28 N4: a picture wired into the look-back
    that is not the frame's own (the scene, the backdrop)."""
    w = wired(wiring)
    held = next((x.src for x in w.wires if x.dst == "lookback.capture"), None)
    over = next((x.src for x in w.wires if held is not None and x.dst == f"{held}.over"), None)
    hands = (wire_node_kind(held or "", wired=True) == "composite"
             and wire_node_kind(over or "", wired=True) == "layer") or bool(in_scene_hands(w))
    words = "history: the scene · with the hands" if hands else "history: the scene"
    for e in w.placed:
        if e.where in (("after", "scene"), ("into", LOOKBACK), ("after", LOOKBACK)):
            words += " · " + placement_words(e)
    for x in w.wires:
        if x.dst == "lookback.image" and x.src not in ("scene", BACKDROP):
            words += " · " + wire_words(x)
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
    for e in wired(wiring).placed:
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
    (the cover, the hands' layer, the readout, each pipeline's frame
    texture, the failures, `stats`, each node's per-frame `data`).

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
    dependencies that carry no image (the capture after every pipeline).

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
    reads (`PatternNode.layer`, `Renderer._face_layer`)."""

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

    def prepare(self, frame: Frame) -> None:
        r = frame.r
        pattern = frame.graph.nodes.get("pattern") if frame.graph is not None else None
        r._face_layer = None
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
    """The backdrop (plan 33 G): `backdrop`, the sink whose `image` input
    takes the place of `backdrop.channel`. It draws nothing itself — the
    picture on `image` is laid under the scene by `grounded` (a channel
    straight in: the plan 32 `MediaNode(alpha_of="backdrop_alpha")`; any
    other picture: `Composite(…, under_alpha_of="backdrop_alpha")`). Built
    only when `backdrop.image` is wired; `backdrop.alpha` and
    `backdrop.history` stay params."""

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
    capture (`Capture.after`, as a `Wired` end) — at the size it holds
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

class _RingNode(Node):
    """A picture of the look-back's (plan 34 E, rows 360–363): no inputs,
    read before this frame's capture writes (every consumer runs before
    `Capture`: a wired output's end, a delay's write, the faces in the
    scene), so no loop runs through one. Its own size is the ring's echo
    size (`Lookback.echo`) while it reads; a consumer of another size gets
    it fitted by cover (`OWN_FIT`, `Renderer._refit`) — painted, or for one
    that binds a texture refitted once a frame into a half-float target of
    its own (`<name>#fit`), as a delay's is. While it reads nothing the
    faces show the pattern, an output its ground, an effect transparent
    black."""

    INPUTS: ClassVar[dict[str, str]] = {}
    OUTPUT = IMAGE
    TIMED = False                 # its one pass is its consumer's

    def _src(self, frame: Frame) -> tuple | None:
        """(texture, crop, clamp) this frame, or None while it reads nothing."""
        return None

    def own_size(self, frame: Frame) -> tuple[int, int] | None:
        return tuple(frame.r.lookback.echo) if self._src(frame) is not None else None

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


def _ring_holds(frame: Frame) -> str:
    """What the capture takes this frame, in words (plan 34 E, row 363;
    plan 35 B: what is wired into `lookback.capture`): the scene, with the
    hands' layer laid on, or over the backdrop."""
    g = frame.graph
    cap = g.nodes.get(CAPTURE) if g is not None else None
    src = cap.inputs.get("image") if cap is not None else None
    if isinstance(src, Composite) and isinstance(src.inputs.get("over"), HandsLayer):
        return "the scene + hands"
    if isinstance(src, Composite) and src.name == BACKDROP:
        return "the scene + backdrop"
    return "the scene" if isinstance(src, Scene) else (
        src.name if src is not None else "nothing")


class EchoNode(_RingNode):
    """`echo.<k>` (plan 34 E, rows 360–363): the look-back ring's k-th
    newest commit (`Lookback.echo_slot`), its slot's rect of the atlas
    cropped, the samples clamped half a texel inside it so no neighbour
    bleeds. It reads nothing before k commits since the ring was made,
    the frame a `dream.res` change makes it again, or with no ring
    (`Lookback.ring_error`). The ring keeps capturing for it with the
    look-back off (`Graph.reads_ring`, `Lookback.keep`): what it holds is
    what the capture takes, 8-bit, at `dream.res` on its short side, every
    `dream.gap` seconds."""

    KIND = "echo"

    def __init__(self, name: str, k: int, after: tuple[Node, ...] = ()):
        super().__init__(name, after)
        self.k = k                    # 1 the newest commit, MAX_ECHOES the oldest

    def _slot(self, frame: Frame) -> int | None:
        """The slot this frame reads: the one `run` took before the capture
        (fix round 1: a consumer that paints after the capture — an
        output's `hands` — still reads last frame's commit, not one newer),
        or None when this frame's capture has written over it since (the
        oldest slot, re-used). Without a `run` this frame, the slot now."""
        lb = frame.r.lookback
        took = frame.root.data.get(self.name + "#slot")
        if took is None:
            return lb.echo_slot(self.k)
        slot, at = took
        if slot is not None and getattr(lb, "wrote", None) == (at + 1, slot):
            return None
        return slot

    def _src(self, frame: Frame) -> tuple | None:
        lb = frame.r.lookback
        slot = self._slot(frame)
        # (fix round 2: a slot taken before a capture whose remake failed —
        # the ring released, `atlas` None — reads nothing, R7)
        if slot is None or lb.atlas is None:
            return None
        eh = max(int(lb.echo[1]), 1)
        crop = (0.0, slot / MAX_ECHOES, 1.0, 1.0 / MAX_ECHOES)
        clamp = (0.0, (slot + 0.5 / eh) / MAX_ECHOES, 1.0, (slot + 1 - 0.5 / eh) / MAX_ECHOES)
        return lb.atlas, crop, clamp

    def run(self, frame: Frame) -> None:
        lb = frame.r.lookback
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
        self.said = f"{w}×{h} · {every} · {_ring_holds(frame)}"


class DreamNode(_RingNode):
    """`dream` (plan 34 E, rows 360–361): the look-back's dream buffer —
    the dream worker's result at the echo size, a frame or two after the
    capture it answers. It reads nothing with no worker attached, or
    before the worker's first result has landed (`Lookback.dream_frame`)."""

    KIND = "dream"
    _WHOLE = (0.0, 0.0, 1.0, 1.0)

    def _src(self, frame: Frame) -> tuple | None:
        lb = frame.r.lookback
        if lb.dream is None or lb.dream_frame < 0:
            return None
        return lb.dream, self._WHOLE, None

    def run(self, frame: Frame) -> None:
        lb = frame.r.lookback
        if self._src(frame) is not None:
            w, h = lb.echo
            self.said = f"{w}×{h} · the dream worker's, a frame or two late"
        elif lb.source is None:
            self.said = "no dream worker: reads nothing"
        else:
            self.said = "waiting for the dream worker"


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


# ---------------------------------------------------------------- layers

class Cover(Node):
    """The faces' coverage mask (`render.CoverTarget`): the scene's faces
    again, solid, one channel — only while the look-back occludes
    (`Lookback.wants_cover`). Reads the face buffer the scene pass left,
    so it runs after the scene it masks."""

    KIND = "layer"
    INPUTS: ClassVar[dict[str, str]] = {"scene": IMAGE}
    OUTPUT = MASK
    REFS: ClassVar[frozenset[str]] = frozenset({"scene"})   # the face buffer, not the picture

    def run(self, frame: Frame) -> None:
        frame.cover = None
        if frame.r.lookback.wants_cover():
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
    geometry wired it settles the hands itself. A pass that raises is
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
        split = self.split(frame)
        geo = self.inputs["geometry"]
        gh = self.ghost(frame)
        drew = False
        try:
            with frame.timed(self.name):
                if geo is not None:
                    kw = {"lines": True} if getattr(geo, "draw_as", "solid") == "lines" else {}
                    drew = gh.layer(frame.size, frame.t, readout=split, now=geo.now(frame),
                                    settled=True, **kw)
                else:
                    drew = gh.layer(frame.size, frame.t, readout=split)
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
    """The look-back's picture: its input over the echoes and the dream
    (`Lookback.composite`), occluded by the cover mask when there is one;
    a copy of the input when the look-back is off. `run` moves the
    echoes' clock and pulls a finished dream once a frame; the picture
    is painted into each consumer's framebuffer (the chain's input, or
    the output itself with no effect on).

    Plan 32 (final review B-I1): `occluder`, whose brightness holds the
    wake back — the scene alone when the history's picture is the scene
    over a backdrop the history keeps out of (`backdrop_history` off), so
    the echoes and the dream show over the backdrop rather than under its
    brightness. With `backdrop_history` on the echoes hold the backdrop
    too and the history occludes from its own picture, as without a
    backdrop: by the scene alone a still backdrop would add onto itself
    and wash to white. The port is there only when given,
    so a history without a backdrop is the one it always was, port for
    port."""

    KIND = "history"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE, "cover": MASK}

    def __init__(self, name: str, after: tuple[Node, ...] = (), **inputs: Node | None):
        if inputs.get("occluder") is not None:
            self.INPUTS = {**type(self).INPUTS, "occluder": IMAGE}
        else:
            inputs.pop("occluder", None)
        super().__init__(name, after, **inputs)
    OUTPUT = IMAGE

    def run(self, frame: Frame) -> None:
        lb = frame.r.lookback
        lb.tick(frame.t)                 # echo time is seconds (plan 14 WP6)
        lb.pull()

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        img = self.inputs["image"]
        if img is None:
            # (plan 35 B: a wired look-back with nothing wired into its
            # image draws nothing over the ground)
            rect = tuple(dst.viewport)
            dst.use()
            frame.ctx.viewport = rect
            frame.ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha, viewport=rect)
            return
        src = img.image(frame)
        cover = self.inputs["cover"].image(frame) if self.inputs["cover"] is not None else None
        occ = self.inputs.get("occluder")
        occ = occ.image(frame) if occ is not None else None
        with frame.timed(self.name):
            frame.r.lookback.composite(src, dst, cover, occ)


class Capture(Node):
    """The look-back's capture (`Lookback.capture`): its input — what it
    is wired to: the scene by default, or the scene with the hands' layer
    laid on (`Wiring.history`, a `Composite` materialised for it) — into
    the ring on the echoes' cadence, and out to the dream worker. Exactly
    once a frame, after every pipeline has composited the history (a
    capture changes the echoes' weights, ages and tint, so one between
    two pipelines would give two outputs different echoes), whatever the
    switches: with no view showing the scene the history and the dream
    go on, and so do the effects' clocks."""

    KIND = "history"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = None

    def run(self, frame: Frame) -> None:
        r = frame.r
        frame.stats["captures"] = 1
        src = self.inputs["image"].image(frame)
        with frame.timed(self.name):
            r.lookback.capture(src, r.scene.fbo)
        # (plan 30 D1: any effect on, a placed one too — its clock moves
        # once a frame whether or not its edge had a picture to fold)
        if (frame.fx_on or _live_now(frame)) and not frame.stats["chain_runs"]:
            r.fx.state.advance_to(frame.t)


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

    def reads(self, frame: Frame) -> bool:
        return any(n is not None and n.reads(frame)
                   for n in (self.inputs["under"], self.inputs["over"]))

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        r, ctx, size = frame.r, frame.ctx, frame.size
        under = self.inputs["under"]
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
        if over is None:
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

    Plan 30 D1 — **placed** effects (`placed`: "after" / "into", or None in
    a pipeline's run). One placed after a node that makes a texture (the
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
        # pattern's seed, `PAINTS` — is painted, as the faces' chain was)
        return src is not None and ((src.MAKES and not src.PAINTS)
                                    or (isinstance(src, Effect) and src.makes))

    @property
    def see_through(self) -> bool:
        """Its picture is a layer's (premultiplied, see-through ground)."""
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
        kw.update(self._opaque(frame))
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
    distinct source an output's `image` takes (its own wire, else All
    outputs'), shared by every output showing it — the retired pipelines'
    ends (`Fx`, and `Wired` for a picture by a wire) made one. As an end it
    decides where the picture lands (`run`): straight into its one user's
    window when exactly one output takes it this frame (`Frame.users`,
    counted through the mutes) at the frame's size, unflipped, with no tap
    and no fold — else once into a frame texture under its name, for every
    output that takes it. Each end that runs is one of `stats["ends"]`, by
    name (plan 35 T4: where the pipelines' keys were).

    The stand-down (row 378): a source that is a chain of copies over a
    composite whose `over` is a hands layer is only itself while it bends
    the layer — the layer drawn this frame and a copy of the chain live
    (an empty chain never bends). Otherwise its outputs take `fallback` —
    the end of the copies' originals over the composite's `under`, or the
    ground (None) with nothing under — with the layer laid over at the
    output (`Output.settle`), as a through pipeline's was. Any other source is
    always itself."""

    KIND = "shown"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = IMAGE

    def __init__(self, name: str, after: tuple[Node, ...] = (), **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.key = name               # its frame texture's and its routes' key
        self.fallback: Shown | None = None
        self.stands = False           # a copy chain over a hands composite (`_Build`)
        self.copies: tuple[str, ...] = ()     # the chain's copies' effects, first first
        self.chained = False          # an effect of the graph's run is on its way

    @property
    def source(self) -> Node | None:
        """What its chain of effects starts from (the composite that lays
        the hands on, for a stand-down)."""
        src = self.inputs["image"]
        while isinstance(src, Effect):
            src = src.inputs["image"]
        return src

    @property
    def layer(self) -> Node | None:
        """The layer its composite lays on before the copies (a stand-down's
        alone), read as wired now (D1 may sit an effect on it)."""
        src = self.source
        return src.inputs["over"] if self.stands and isinstance(src, Composite) else None

    def bent(self, frame: Frame) -> bool:
        """Whether this end is itself this frame (see the class)."""
        if not getattr(self, "stands", False):
            return True
        layer = self.layer
        if layer is None or layer.image(frame) is None:
            return False
        live = frame.r.fx.state.live
        return any(live(e) for e in self.copies)

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
    the depth stays in this context). Which end it shows this frame is
    `settle`'s: its wired end, or that end's fallback with the layer over
    while the end is not bent."""

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
        port, between it and the pipeline's end."""
        out: list[Effect] = []
        src = self.inputs["image"]
        while isinstance(src, Effect):
            out.append(src)
            src = src.inputs["image"]
        return out[::-1]

    def settle(self, frame: Frame) -> tuple[Node | None, tuple[Node, str] | None]:
        """(the end it shows this frame or None for its ground, (the layer
        laid over after it, its blend) or None) — through its window's
        mutes; a through end that is not bent (`Shown.bent`) stands down
        for its fallback and its layer goes over here."""
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
        if isinstance(end, Shown) and not end.bent(frame):
            # (plan 35 B: a copy chain's stand-down, as a pipeline's was;
            # R9, T3: a hands mute wins over it — the layer stays off)
            over, blend = (end.layer if not no_hands else None), end.source.blend
            end = end.fallback
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
    file comes or goes), `run` the effects of the pipelines' runs.

    Plan 30 D1: `insert` puts a placed effect on an edge after the graph
    is built (`build_graph`), `dormant` says why a placed effect has no
    node in this graph (`palette after hands — no hands layer this
    frame`), `notes` a placement refused at build (a loop), `folds` the
    effects placed into an output's picture."""

    def __init__(self, key: tuple = (), wiring: Wiring | None = None):
        self.key = key
        self.wiring = wiring if wiring is not None else Wiring()
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
        # D1: the effects placed out of the runs (dormant ones included):
        # the renderer's `fx_on` ("an effect bends a pipeline") leaves them out
        self.placed_names: frozenset[str] = frozenset()
        # plan 33 R: the effects of every pipeline's run, first to last —
        # the renderer's `fx_on` is any of them live
        self.run: tuple[str, ...] = ()
        self._readers: dict[str, int] = {}
        self._pool: int | None = None
        self._framed: frozenset[str] | None = None     # plan 33 R: `at_frame`, settled
        # plan 33 S: `pulled`, by the switches' picks (None: not yet asked)
        self._pulled: dict[tuple[int, ...], frozenset[str]] | None = None
        # plan 34 E (row 362): an `echo.<k>` or the `dream` is in the graph —
        # the renderer keeps the ring capturing (`Lookback.keep`)
        self.reads_ring = False

    def insert(self, node: Effect, edges: list[tuple[Node, str]]) -> Effect:
        """Add placed effect `node` (its input already wired) and make each
        (consumer, port) in `edges` read it instead (plan 30 D1). Refused
        — nothing changed, ValueError — when that would make a loop: a
        consumer the node already depends on."""
        ups: set[int] = set()
        todo = [node]
        while todo:
            n = todo.pop()
            for d in n.deps():
                if id(d) not in ups:
                    ups.add(id(d))
                    todo.append(d)
        for consumer, _ in edges:
            if consumer is node or id(consumer) in ups:
                raise ValueError(f"{node.name}: placing it there makes a loop "
                                 f"through {consumer.name}")
        self.add(node)
        # listed right after what it reads, so the order (and SYSTEM's
        # lines) put it under its source, not at the end of the frame
        src = node.inputs["image"]
        if src is not None and src.name in self.nodes:
            names = [n for n in self.nodes if n != node.name]
            at = names.index(src.name) + 1
            names.insert(at, node.name)
            self.nodes = {n: self.nodes[n] for n in names}
        for consumer, port in edges:
            consumer.inputs[port] = node
        self.relink()
        return node

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
        into it (D1): its pipeline is then never painted direct."""
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
            node.run(frame)

    def __repr__(self) -> str:
        return "Graph(" + " → ".join(n.name for n in self.order) + ")"


def graph_key(views: list[View]) -> tuple:
    """What selects the graph besides the wiring (plan 35 B, row 379): the
    views' count. A window's mutes, size, flips and presenter are read when
    its nodes run — a mute never rebuilds."""
    return (len(views),)


def wired(wiring: Wiring | None) -> Wiring:
    """The wiring a graph is built from (plan 35 T4): a wired frame is
    itself; an unwired one — no preset's graph reached it: the app before
    its first load, a test rig's, a tool's (`graphmigrate.wiring_for`'s
    run) — is the wired frame a load lands for it (`graphmigrate.wired_of`):
    `Wiring()` is the factory look, `frame_wires(read_graph({}))`."""
    w = wiring if wiring is not None else Wiring()
    if getattr(w, "wired", False):
        return w
    return _wired_of(w)


@functools.lru_cache(maxsize=64)
def _wired_of(wiring: Wiring) -> Wiring:
    # (graphmigrate is pure data and imports this module: asked here, once
    # per wiring — the renderer asks each frame)
    from . import graphmigrate

    return read_graph(graphmigrate.wired_of(wiring)).wiring()


def _place(g: Graph, placed: list[EffectAt]) -> None:
    """Put each placed effect on its edge of the built graph `g` (plan 30
    D1, `build_graph`): one sitting on another placed effect after it;
    one whose node is not in this graph dormant, with why in words."""
    pending = list(placed)
    names = {e.name for e in placed}
    while pending:
        ready = [e for e in pending if e.where[1] not in names
                 or e.where[1] in g.dormant or _placed_nodes(g, e.where[1])]
        if not ready:                         # (a loop: refused before this)
            break
        for e in ready:
            pending.remove(e)
            why = _place_one(g, e)
            if why is not None:
                g.dormant[e.name] = f"{e.name} {e.where[0]} {e.where[1]} — {why}"


def _placed_nodes(g: Graph, effect: str) -> list[Effect]:
    """The effect nodes of instance `effect` in `g` (one per pipeline's run,
    or the one placed)."""
    return [n for n in g.nodes.values() if isinstance(n, Effect) and n.effect == effect]


def _place_one(g: Graph, e: EffectAt) -> str | None:
    """Put placed effect `e` into `g`; None, or why it is dormant."""
    key, where = e.where
    if e.name not in g.effects:
        return f"no {e.name} effect in this build"
    if where.startswith("output."):           # after or into an output: its picture
        out = g.nodes.get(where)
        if not isinstance(out, Output):
            return f"no output {where.partition('.')[2]} this frame"
        if out.inputs["image"] is None:
            return f"output {where.partition('.')[2]} shows no picture this frame"
        targets = [(out.inputs["image"], [(out, "image")], "")]
    elif where in ("scene", LOOKBACK) or where.startswith("hands"):
        node = g.nodes.get(where)
        if where == "scene" and key == "after" and isinstance(g.nodes.get(BACKDROP), Composite):
            # plan 32 R: over a backdrop the scene is a see-through layer an
            # effect would fold opaque (hiding the backdrop); the effect sits
            # after the scene laid over it instead, so it bends both — what
            # reads the scene alone (the capture without backdrop.history)
            # reads it unbent
            node = g.nodes[BACKDROP]
        if node is None or (where.startswith("hands") and not isinstance(node, HandsLayer)):
            hands = hands_of(where) if where.endswith(".layer") else where
            return (f"no {hands} layer this frame" if where.startswith("hands")
                    else f"no {where} this frame")
        if key == "into":                     # (only the look-back takes `into` here)
            targets = [(node.inputs["image"], [(node, "image")], "")]
        else:
            targets = [(node, _consumers(g, node), "")]
    else:                                     # an effect: each of its nodes
        if where in g.dormant:
            return f"{where} is dormant this frame"
        nodes = _placed_nodes(g, where)
        if not nodes:
            return f"no {where} effect this frame"
        targets = []
        for node in nodes:
            # (plan 35 T4: a copy's own, by its name — `acid.2(copy.3)` —
            # where each pipeline's run node had the pipeline's suffix)
            suffix = f"({node.name})" if isinstance(node, Copy) else ""
            if key == "into":
                targets.append((node.inputs["image"], [(node, "image")], suffix))
            else:
                targets.append((node, _consumers(g, node), suffix))
    for src, edges, suffix in targets:
        name = e.name + suffix
        if name in g.nodes:
            name = f"fx.{name}"
        try:
            g.insert(Effect(e.name, image=src, node=name, placed=key), edges)
        except ValueError:                    # (never, past `placement_loops`)
            return "that makes a loop"
    return None


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


def _consumers(g: Graph, node: Node) -> list[tuple[Node, str]]:
    """Every (consumer, port) of `g` reading `node`'s picture: the image
    ports wired to it, but those that read something else of it
    (`Node.REFS`: a depth, the readout, the face buffer)."""
    return [(c, port) for c in g.nodes.values() for port, src in c.inputs.items()
            if src is node and port not in c.REFS and c.INPUTS[port] == IMAGE]


# ---------------------------------------------------------------- the wired frame (plan 35 B)

def build_graph(views: list[View], wiring: Wiring | None = None, clouds: tuple[str, ...] = (),
                effects: tuple[str, ...] = ()) -> Graph:
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
    over `lookback.image`, its cover made while the scene is; each hands
    layer and guide drawing its hands node by name — a guide is its
    layer's split-out picture while that layer is built, as the default
    graph's in-scene readout was; effects, copies, composites, switches,
    channels, the pattern, plan 34's delays and ring pictures); then D1's
    placements (`_place`); then one `Shown` per distinct picture an output
    takes; then the capture (`lookback.capture`'s) after every end and
    every delay's write; then one `Output` per view, each port its own
    wire else All outputs', through its window's mutes.

    Plan 35 T4: every frame is this one's — an unwired `wiring` is wired
    first (`wired`: `Wiring()` the factory look). The render nodes are named
    in the new ids (`hands`, `hands.layer`, `hands.guide`, `lookback`,
    `lookback(capture)`, `lookback(cover)`, `channel.a`, `backdrop`): the
    SYSTEM lines and `Graph.timed` say them. A wire into an output this rig
    has not open builds nothing (dormant, `no output 3 this frame`)."""
    wiring = wired(wiring)
    g = Graph(graph_key(views), wiring)
    g.clouds = tuple(clouds)
    g.effects = tuple(effects)
    _Build(g, wiring, len(views)).build()
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


class _Build:
    """`build_graph`'s work (plan 35 B): the reached wires made into nodes,
    added to `g` in the default graph's order (the frame's own nodes, the
    run, each through's composite and copies, the ends, the capture, the
    outputs), so the passes run as today's frame ran them."""

    def __init__(self, g: Graph, wiring: Wiring, count: int):
        self.g, self.wiring, self.count = g, wiring, count
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
        self.clouds = ([PointCloud(CLOUD_KIND if i == 0 else f"{CLOUD_KIND}.{i + 1}", role)
                        for i, role in enumerate(g.clouds)] if "scene" in self.reached else [])
        self.cover: Cover | None = None
        self.ends: list[Shown] = []
        self._ends: dict[int, Shown] = {}
        self._names: set[str] = set()

    # ---- the wires

    def _one(self, dst: str) -> Wire | None:
        got = self.into.get(dst)
        return got[0] if got else None

    def _from(self, dst: str) -> Node | None:
        """What the wire into `dst` reads, made (None: no wire, or nothing)."""
        w = self._one(dst)
        return self.node(w.src) if w is not None and w.src != GROUND else None

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
            n = split_instance(hands_of(name))[1]
            return self._keep(HandsLayer(wired_layer_name(n),
                                         geometry=self.node(wired_hands_name(n))))
        if kind == "guide":
            hands = hands_of(name)
            if f"{hands}.layer" in self.reached:     # its layer's own split-out guide
                return self.node(f"{hands}.layer")
            n = split_instance(hands)[1]
            return self._keep(Readout(wired_guide_name(n), geometry=self.node(hands)))
        if kind == "scene":
            geos = [self.node(w.src) for w in self.into.get("scene.geometry", ())]
            on_backdrop = any(w.src == "scene" for w in self.into.get("backdrop.scene", ()))
            return self._keep(Scene("scene", geometries=[*self.clouds,
                                                         *(x for x in geos if x is not None)],
                                    ground=0.0 if on_backdrop else None))
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
            image, occ = self._from("lookback.image"), self._from("lookback.occluder")
            if self.cover is None and "scene" in self.reached:
                scene = self.node("scene")
                if scene is not None:
                    self.cover = self._keep(Cover(COVER, scene=scene))
            return self._keep(History(LOOKBACK, image=image, cover=self.cover, occluder=occ))
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
            blend = self.blends.get(name, "over")
            return self._keep(Composite(self._unique(name), blend=blend,
                                        under=self._from(f"{name}.under"),
                                        over=self._from(f"{name}.over"),
                                        depth=self._depth() if blend == "depth" else None))
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
        if kind == "echo":
            return self._keep(EchoNode(name, int(name.partition(".")[2])))
        if kind == "dream":
            return self._keep(DreamNode(name))
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
        return self._keep(Effect(name, image=src, node=self._unique(name), placed="wire"))

    def _depth(self) -> Node | None:
        """The scene, for a depth-aware lay (the hands' `laid: depth`)."""
        if self.wiring.blend != "depth" or "scene" not in self.reached:
            return None
        return self.node("scene")

    def _end(self, src: Node) -> Shown:
        """Picture `src`'s one end (and, for a copy chain over a hands
        composite, its stand-down's: the originals over the `under`)."""
        got = self._ends.get(id(src))
        if got is not None:
            return got
        end = self._ends[id(src)] = Shown(f"shown({src.name})", image=src)
        self.ends.append(end)
        copies, n = [], src
        while isinstance(n, Copy):
            copies.insert(0, n)
            n = n.inputs["image"]
        if isinstance(n, Composite) and isinstance(n.inputs["over"], HandsLayer):
            end.stands = True
            end.copies = tuple(c.effect for c in copies)
            under = n.inputs["under"]
            if under is not None:
                end.fallback = self._end(self._originals(under, end.copies))
        return end

    def _originals(self, under: Node, effects: tuple[str, ...]) -> Node:
        """The copies' originals over `under`: the effects of the graph that
        read it in that order, made where the wires made none."""
        cur = under
        for e in effects:
            got = next((n for n in self.built if isinstance(n, Effect)
                        and not isinstance(n, Copy) and n.effect == e
                        and n.inputs["image"] is cur), None)
            cur = got if got is not None else self._keep(
                Effect(e, image=cur, node=self._unique(e), placed="wire"))
        return cur

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
        g, wiring = self.g, self.wiring
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
        # each output's ports: its own wire, else All outputs' (`ground`: nothing)
        alls = {w.port: w for w in self.wires if w.node == ALL_OUTPUTS}
        ports = []
        for i in range(self.count):
            own = {w.port: w for w in self.wires if w.node == f"output.{i + 1}"}
            got = {}
            for p in ("image", "hands", "guide"):
                w = own.get(p) or alls.get(p)
                got[p] = self.node(w.src) if w is not None and w.src != GROUND else None
            ports.append(got)
        layers = tuple(n for n in self.built if isinstance(n, HandsLayer))
        shown = [self._end(p["image"]) if p["image"] is not None else None for p in ports]
        for end in self.ends:
            end.after = layers                  # whether a hand shows decides the stand-down
            end.chained = any(e.effect in g.run for e in _effects_of(end.inputs["image"]))
        held = self._from("lookback.capture")
        capture = None
        if held is not None:
            laid = [x for p in ports for x in (p["hands"], p["guide"]) if x is not None]
            capture = Capture(CAPTURE, image=held,
                              after=tuple(dict.fromkeys([*self.ends, *writes, *laid])))
        scene = self.made.get("scene")
        outputs = []
        for i, (p, end) in enumerate(zip(ports, shown)):
            depth = (scene if wiring.blend == "depth" and scene is not None
                     and (p["hands"] is not None or (end is not None and end.stands)) else None)
            outputs.append(Output(f"output.{i + 1}", i, after=(capture,) if capture else (),
                                  blend=wiring.blend, image=end,
                                  hands=p["hands"], readout=p["guide"], depth=depth))
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
            if end is not None and end.stands:
                roots += [end.source, *_effects_of(end.inputs["image"]), end]
        roots += [held, *self.ends, *writes, capture, *outputs, *self.built]
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
        # D1: the placements, on the built graph (`after: hands.layer` …:
        # plan 35 T4, the render graph names its nodes as the wires do)
        loops = placement_loops(wiring.placed)
        placed = []
        for e in wiring.placed:
            if e.name in loops:
                g.notes.append(f"{e.name} {e.where[0]} {e.where[1]!r} — that makes a loop "
                               f"({loops[e.name]}); the default placement")
                continue
            placed.append(e)
        _place(g, placed)
        self._split(layers)
        g.placed_names = frozenset({e.name for e in wiring.placed} | {
            n.effect for n in g.nodes.values() if isinstance(n, Effect) and n.placed})
        g.reads_ring = any(isinstance(n, _RingNode) for n in g.nodes.values())
        g.relink()

    def _aux(self) -> None:
        """Each aux wire on its effect's or copy's `aux` port (plan 32 R): a
        source the effect feeds (a loop) is dormant, in words."""
        for w in self.wires:
            if w.port != AUX or _kind(w.node) not in ("effect", "copy"):
                continue
            target, src = self.made.get(w.node), self.node(w.src)
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
    their inputs, an end's fallback, and the faces pattern the shape reads
    by name): what the frame can show. The retired default graph built
    pipelines no output took (an output whose picture a wire replaced):
    those were not in `signature`, as recorded."""
    pattern = g.nodes.get("pattern")
    todo = [n for n in g.order if isinstance(n, (Output, Capture, DelayWrite))]
    seen: set[int] = set()
    while todo:
        n = todo.pop()
        if id(n) in seen:
            continue
        seen.add(id(n))
        todo += [v for v in n.inputs.values() if v is not None]
        fb = getattr(n, "fallback", None)
        if fb is not None:
            todo.append(fb)
        if isinstance(n, Shape) and isinstance(pattern, PatternNode):
            todo.append(pattern)
    return seen


def signature(g: Graph) -> tuple:
    """What a graph shows, node for node (plan 35 B, Review Focus 1): per
    output, (its index, its picture's chain, its hands', its guide's, its
    blend, its depth's, its end's fallback's chain); then every node the
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
        end = out.inputs["image"]
        while isinstance(end, Effect):
            end = end.inputs["image"]
        outs.append((out.index, _sig_chain(out.inputs["image"]),
                     _sig_chain(out.inputs["hands"]), _sig_chain(out.inputs["readout"]),
                     out.blend, _sig_chain(out.inputs["depth"]),
                     _sig_chain(getattr(end, "fallback", None))))
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
