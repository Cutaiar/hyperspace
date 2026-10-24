"""The render graph (plan 26 A1, A3, A4): the frame as nodes, evaluated in
dependency order.

`Renderer._draw_frame` (render.py) used to be a fixed list of passes.
It is now "build or reuse the graph for this frame's views, evaluate
it": `default_graph` builds the frame as nodes from each output's
`Switches` and the renderer's `Wiring`, and `Graph.evaluate` runs the
nodes once each, in an order computed when the graph is built, never per
frame. With the default wiring the graph is today's three pipelines
(`outputs.SCENE`, `SCENE_HANDS`, `HANDS`) and draws every golden frame
without hands byte for byte.

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

- **FX** (`Effect`, `Fx`; plan 30 D0): each effect instance is an image
  node (`Effect`: one pass of its file's program, `FxChain.run_one`),
  and each pipeline's chain is a run of them in the stack's order ending
  in the pipeline's end (`Fx`). An effect that is off reads its input
  through: no pass, no texture.
- **History** (`History`, `Capture`): the look-back (`lookback.Lookback`)
  as two nodes, because its composite must read the ring before the
  frame's capture changes it: `history` lays the echoes and the dream
  over its input; `capture` puts its input — whatever it is wired to: the
  scene, or the scene with the hands' layer (A3) — into the ring after
  every composite of the frame has run.
- **Output** (`Output`): one render output — `fit`, flip, the hands over,
  the readout, the dim — exactly `Renderer._compose`, so an output in
  another context gets the same five-step `outputs.Handoff`.

And plan 32 R's: **Media** (`MediaNode`, `media.a` … `media.h`), a media
channel fitted to the frame — the backdrop the scene is laid over
(`grounded`), or any picture port a wire names.

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
and the pipeline's last node (`Fx`) decides where the picture lands:
**a pipeline with one consumer at the frame size, unflipped, paints
straight into that output; otherwise once into a frame texture that each
of its outputs shows** (`Renderer._frame_target`, `_show`). A consumer
that needs a texture of a painted node (the capture of a composite) gets
it materialised once a frame (`Composite.image`).

**What is static and what is per frame.** The node set, the wiring and
the order are a function of the views' switches and the renderer's
`Wiring` (`graph_key`, `Graph.wiring`): the renderer keeps the last graph
and builds a new one only when either changes. Each output is wired to
its pipeline's end; per frame a through pipeline whose layer is not bent
— no effect on, or no hand drawn — stands down for the pipeline it was
laid onto, with the layer laid over at the output instead (`Fx.fallback`,
`Output.settle`): `outputs.route`'s table, as wiring. A pipeline with no
output this frame is skipped and its nodes read 0 ms.

**The graph in the preset** (plan 26 A4). A preset may carry a `graph`
section: plain JSON listing node instances by kind and their wiring,
never a param (`GraphSpec`, `read_graph`; the kinds in `NODE_KINDS`).
What it says becomes the `Wiring` the default graph is built from —
where each hands node is drawn (in the scene or as the layer), solid or
as lines, how the layer is laid on, what the history holds — and the
effect instances the chain holds (`FxState.set_instances`). A second
instance of a node is named by the naming rule (ENGINEERING §2):
`ghost.2` (its own `Ghost`, `Renderer.ghost_of`, its own `ghost.2.*`
params), `hands.2` its layer, `fx.acid.2.*` a second acid. No section
is the default graph; one this build cannot read is a note and the
default graph (preset.py, `GraphSection`). The words the OUTPUT and
LOOKBACK pages say it in are here too (`hands_words`, `history_words`,
`graph_words`): no editor until plan 28.

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
from .outputs import HANDS, NAMES, PIPELINES, SCENE, SCENE_HANDS, Switches, View

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
# the scene laid over the backdrop, before the history (`Wiring.backdrop`)
GROUNDED = "grounded"
# the side, in texels, of the picture the faces show while something other
# than the pattern is wired into them (plan 20 fork F2; plan 33 R: the size
# `shape.faces` asks of what feeds it, `Node.size_for`): square, fixed, a
# constant and not a param — 512 cannot be told from it on a face and 2048
# costs several times as much. render.py takes it from here
FACE_PIC = 1024


def media_name(c: str) -> str:
    """Channel `c`'s node, and its name as a wire's end: `media.a` …"""
    return f"media.{c}"


def hands_name(n: int) -> str:
    """The n-th hands geometry node's name — its params' prefix by the
    naming rule (ENGINEERING §2): `ghost`, `ghost.2`, …"""
    return "ghost" if n == 1 else f"ghost.{n}"


def layer_name(n: int) -> str:
    """The hands' layer drawn from the n-th hands node: `hands` (today's
    SYSTEM line), `hands.2`, …"""
    return "hands" if n == 1 else f"hands.{n}"


def readout_name(n: int) -> str:
    """The readout alone of the n-th hands node: `readout`, `readout.2`, …"""
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
    """The choices the default graph is built from besides the outputs'
    switches (plan 26 A3): where the hands are drawn, how their layer is
    laid on, what the history captures. The defaults are today's frame.
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

    Plan 32 R: `backdrop`, the channel laid under the scene (`GROUNDED`),
    and `backdrop_history`, whether the capture takes it with the scene.
    Plan 33 R: the channel is the section's (`media.<c> → backdrop.image`,
    `GraphSpec.wiring`); a branch into `backdrop.image` is one of `wires`.

    Plan 33 R: `run`, the effects wired from `frame` into `fx.image`, in
    wire order — each pipeline's run (`default_graph`); `()` is the empty
    run (`frame → fx.image`). None: the wiring says no run (no preset's
    graph reached it — a test rig, a tool, the app before its first load),
    and the default graph takes the stack it is handed instead, as before
    plan 33, until the stack retires (plan 33 T7)."""

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
        if len(layers) > 1:
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
_PLACE_NODE = re.compile(rf"scene|history|hands(?:\.{_INSTANCE})?|output\.[1-9][0-9]*")
# plan 33 G: the wire ends that are no effect — `frame`, the pipeline end
# `fx`, the faces' `shape`, `pattern`, `backdrop`, `switch` — so no effect
# file may take them, and no effect's place is one of them
RESERVED = ("frame", "fx", "pattern", "shape", "backdrop", "switch")
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

    Unplaced: an extra instance of a file, `fx.<file>.<n>.*` (n ≥ 2), its
    own params and clock — instance 1 is the file itself, always there.
    Plan 33 R: where it draws is its wires (a run from `frame`, a branch),
    never its `order`; one on no wire has no node.

    Placed (D1): `after` a node — on that node's output, every consumer
    of its picture reading the effect instead — or `into` one — on that
    node's `image` input alone (`output.<n>`: that output's picture) —
    one of the two, never both; then any instance, 1 included, may be
    named. A placed instance is in no pipeline's run: it sits where it is
    put (`default_graph`)."""

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
        if self.n < 2 and not self.placed:
            raise ValueError(f"effect {self.file} instance {self.n!r}: 2 or more (instance 1 "
                             "is the file itself)")
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
        """("after" | "into", the node's name), or None: in the chain."""
        if self.after is not None:
            return "after", self.after
        if self.into is not None:
            return "into", self.into
        return None

    def unplaced(self) -> EffectAt | None:
        """This instance at the default placement: in the chain at its
        order (None for instance 1, the file itself, always there)."""
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


def _hands_entry(e: dict) -> tuple[HandsAt, str | None]:
    _entry_keys(e, "hands", ("instance", "into", "draw", "laid"))
    laid = e.get("laid")
    if laid is not None and laid not in BLENDS:
        raise GraphError(f"hands node: laid {laid!r}, one of {', '.join(BLENDS)}")
    return HandsAt(_instance(e), e.get("into", "layer"), e.get("draw", "solid")), laid


def _effect_entry(e: dict) -> tuple[EffectAt | None, str | None]:
    """(the instance, None), or — for a placement this build cannot honour
    (plan 30 D1: both keys at once, a name that is not a string or not in
    the placeable vocabulary) — (the instance at the default placement,
    or None for instance 1, which is always in the chain; the reason).
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


def _history_entry(e: dict) -> HistoryAt:
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
# (the rig's, not the look's), an effect sits in the chain at its order.
# D1's `after` / `into` are the same wires written short, and read as such
# (`d1_wires`): `{"file": "palette", "after": "hands"}` is the wire
# `hands → palette.image`, `{"file": "palette", "into": "output.2"}` the
# wire `palette → output.2.image`.

WIRE_KEYS = ("from", "to")
_LAYER = re.compile(rf"hands(?:\.{_INSTANCE})?")
_GHOST = re.compile(rf"ghost(?:\.{_INSTANCE})?")
_OUTPUT = re.compile(r"output\.[1-9][0-9]*")
_COMPOSITE = re.compile(rf"composite(?:\.{_INSTANCE})?")
_MEDIA = re.compile(rf"media\.[{MEDIA_CHANNELS}]")     # plan 32 R: a channel, a wire's end
_SWITCH = re.compile(rf"switch(?:\.{_INSTANCE})?")       # plan 33 S: `switch`, `switch.2` …
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
              "fx": None, "shape": None, "backdrop": None}
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
}
TYPE_WORDS = {IMAGE: "a picture", GEOMETRY: "geometry", MASK: "a mask", None: "nothing"}
WIRE_FROM_WORDS = ("scene, hands …, history, frame, pattern, an effect, a composite, "
                   "a switch or a channel (media.a …)")
WIRE_TO_WORDS = ("output.1 … (image, hands, readout), history.image, fx.image, "
                 "shape.faces, backdrop.image, pattern.media, an effect's image or aux, "
                 "a composite's under / over, or a switch's in1 … in8")
# plan 33 G: the kinds whose input ports end a path — what a picture is
# for. `reaches` follows the picture ports back from these
SINKS = ("output", "fx", "shape", "pattern", "backdrop", "history")
# a node that takes a picture and puts it outside the graph makes none
NO_SOURCE = ("output", "fx", "shape", "backdrop")
AUX = "aux"     # plan 32 R: an effect's second picture port (`Effect.INPUTS`)


def wire_node_kind(name: Any) -> str | None:
    """What kind of node a wire's name is (`WIRE_MAKES`'s keys), or None."""
    if not isinstance(name, str):
        return None
    if name in ("scene", "history", "cover"):
        return name
    if name in ("frame", "fx", "pattern", "shape", "backdrop"):
        return name
    for kind, pat in (("layer", _LAYER), ("ghost", _GHOST), ("output", _OUTPUT),
                      ("composite", _COMPOSITE), ("media", _MEDIA), ("switch", _SWITCH)):
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


FX_IMAGE_REFUSAL = ("fx.image takes the run from frame; to replace an output's picture "
                    "wire it into output.N.image")


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
    places. The canvas's drag says the same words."""
    ctx = ctx if ctx is not None else _WireCtx()
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
        if k == "composite" and name not in ctx.composites:
            return f'no {name} node in this graph (add one: {{"kind": "composite"}})'
        if k == "switch" and name not in ctx.switches:
            return f'no {name} node in this graph (add one: {{"kind": "switch"}})'
    if kind == "fx" and ctx.wires is not None and not _run_from_frame(w.src, ctx.wires):
        return FX_IMAGE_REFUSAL
    if src_kind == "layer" and w.src != ctx.layer:
        return f"no {w.src} layer in this graph ({ctx.layer} makes the layer)"
    if w.src == node:
        return f"{node} into itself makes a loop"
    if kind == "output" and port == "readout" and src_kind != "layer":
        return f"{w.dst} takes a hands layer's guide ({ctx.layer})"
    if kind == "composite" and port == "over" and src_kind == "history":
        return ("the history paints into what reads it, so it is not laid over: "
                "wire it under, or an effect after it over")
    if kind == "output" and port == "hands" and src_kind == "history":
        return ("the history paints into what reads it, so it is not laid over: "
                "wire it into the output's image, or an effect after it over")
    # (an aux wire places nothing: a placed effect takes one where it sits)
    for name, k, into in ((node, kind, port != AUX), (w.src, src_kind, False)):
        if k == "effect" and name in ctx.placed and (into or kind != "effect"):
            key, where = ctx.placed[name]
            return f"{name} sits {key} {where!r} already (its node says so): one place"
    return None


def wire_loops(wires: list[Wire]) -> dict[Wire, str]:
    """The wires on a loop — a node reading, through wires, its own
    picture — each with the loop in words (`acid.2 → palette → acid.2`).
    A wire makes its node depend on its source."""
    deps: dict[str, set[str]] = {}
    for w in wires:
        deps.setdefault(w.node, set()).add(w.src)
    out: dict[Wire, str] = {}
    for w in wires:
        parent: dict[str, str | None] = {w.src: None}
        todo = [w.src]
        while todo and w.node not in parent:
            cur = todo.pop()
            for d in sorted(deps.get(cur, ())):
                if d not in parent:
                    parent[d] = cur
                    todo.append(d)
        if w.node not in parent:
            continue
        path, cur = [], w.node            # w.node … back to w.src, each read by the next
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        out[w] = " → ".join([*path, w.node])
    return out


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
    # port keeps its default (or D1's placement)
    into: dict[str, list[Wire]] = {}
    for w in (*d1, *ok):
        into.setdefault(w.dst, []).append(w)
    for dst, ws in into.items():
        if len(ws) > 1:
            srcs = " and ".join(x.src for x in ws)
            for w in ws:
                if w in ok:
                    ok.remove(w)
                    notes.append(f"wire {w} — {dst} takes one wire, and {len(ws)} go into "
                                 f"it ({srcs}): it keeps its default")
    # an effect no wire feeds sits into one port (D1's `into`); to feed
    # more, wire its input
    fed = {w.node for w in (*d1, *ok) if wire_node_kind(w.node) == "effect" and not is_aux(w)}
    outs: dict[str, list[Wire]] = {}
    for w in ok:
        if wire_node_kind(w.src) == "effect" and wire_node_kind(w.node) != "effect":
            outs.setdefault(w.src, []).append(w)
    for e, ws in outs.items():
        if e not in fed and len(ws) > 1:
            for w in ws[1:]:
                ok.remove(w)
                notes.append(f"wire {w} — {e} has no wire in, so it sits into one port "
                             f"({ws[0].dst}): wire its input to feed more")
    loops = wire_loops([*d1, *ok])
    for w in list(ok):
        if w in loops:
            ok.remove(w)
            notes.append(f"wire {w} — that makes a loop ({loops[w]})")
    return tuple(w for w in wires if w in ok), notes


def split_wires(wires, placed=()) -> tuple[tuple[EffectAt, ...], tuple[Wire, ...]]:
    """The wire list as the default graph builds it: (the effects the
    wires place as D1 would — an effect fed by one wire and wired into
    nothing sits `after` its source; one wired into one output's or the
    history's `image` port and fed by none sits `into` it — and the wires
    left, each built as an edge: into an output's port, the history's
    image, a composite's, or an effect both fed and wired on). `placed`:
    D1's own placements (an effect they place is not placed again)."""
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

    def wiring(self) -> Wiring:
        """The default graph's wiring this graph says. Plan 28 N4: the
        wires D1 would write short are placements (`split_wires`), after
        D1's own; the rest are the wiring's `wires`."""
        first = next((h for h in self.hands if h.n == 1), HandsAt())
        placed = tuple(e for e in self.effects if e.placed)
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
        synth, edges = split_wires(wires, placed)
        if run is not None:
            edges = _reached_edges(edges, run, placed + synth)
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
        layer = self.wiring().layer_node().n
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
            if e.n != 1:                       # D1: instance 1 is named only when placed
                d["instance"] = e.n
            if e.where is not None:
                d[e.where[0]] = e.where[1]
            nodes.append(d)
        if self.history.holds != "scene":
            nodes.append({"kind": "history", "holds": self.history.holds})
        for kind, got in self.others:
            to = getattr(got, "to_json", None)
            nodes.append(to() if to is not None else {"kind": kind, **dict(got)})
        if not self.wires:                     # N4: a graph with no wires is D1's, short
            return {"nodes": nodes}
        return {"nodes": nodes, "wires": [w.to_json() for w in self.wires]}


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
    (`placement_loops`) — the effect takes the default placement (the
    chain, at its order) and the reason rides in `GraphSpec.notes`."""
    if not isinstance(section, dict):
        raise GraphError(f"not an object but {type(section).__name__}")
    extra = sorted(set(section) - {"nodes", "wires"})
    if extra:
        raise GraphError(f"no key {', '.join(map(repr, extra))} (it takes nodes and wires)")
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
        try:
            got = reader(e)
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
            if kind in ("composite", "switch") and any(
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
    spec = GraphSpec(hands=tuple(hands[n] for n in sorted(hands)),
                     history=history if history is not None else HistoryAt(),
                     effects=effects_at, others=tuple(others), notes=tuple(notes))
    try:
        wiring = spec.wiring()
    except ValueError as err:
        raise GraphError(str(err)) from err
    layer = wiring.layer_node().n
    for n, how in laid.items():
        if n != layer:
            raise GraphError(f"hands {n}: laid {how!r}, but {hands_name(layer)} makes the layer")
    spec = replace(spec, laid=laid.get(layer, "over"))
    if "wires" not in section:
        return spec
    # plan 28 N4: the wire list — each wire this build cannot honour (no
    # such node or port, a port of another type, two into one port, a
    # loop) is a note and that port's default; the rest stand
    names = {e.name for e in effects_at}
    ctx = _WireCtx(layer=layer_name(layer),
                   ghosts=frozenset(hands_name(h.n) for h in wiring.nodes()),
                   effects=None if known is None else known | names,
                   composites=frozenset(c.name for c in spec.composites()),
                   switches=frozenset(s.name for s in spec.switches),
                   placed={e.name: e.where for e in effects_at if e.placed})
    wires, wire_notes = _read_wires(section["wires"], ctx, d1_wires(effects_at))
    spec = replace(spec, wires=wires, notes=spec.notes + tuple(wire_notes))
    try:
        spec.wiring()
    except ValueError as err:
        raise GraphError(str(err)) from err
    return spec


# the ports a picture goes into (a geometry port or the history's cover is no
# picture): what `reaches` follows
_PICTURE_PORTS = frozenset({"image", "aux", "under", "over", "media", "faces",
                            "hands", "readout", *SWITCH_PORTS})


def reaches(spec: GraphSpec) -> frozenset[str]:
    """Every node with a path, through wires into picture ports, to a sink
    port (`SINKS`: an output, the pipeline end, the faces, the pattern's
    media, the backdrop, the history) — plan 33 G. A node outside it is
    unreached: kept in the preset, drawn faint ("reaches nothing") and
    never run. Reads D1's placements as the wires they are short for."""
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
    write short) — and whatever feeds one of those through a picture port."""
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
                 if wire_node_kind(w.node) not in ("effect", "composite", "switch")
                 or w.node in got)


# ---------------------------------------------------------------- in words

def hands_words(wiring: Wiring, sw: Switches) -> str:
    """Where one output's hands come from under `wiring`, in words (the
    OUTPUT page, plan 26 A4: no editor until plan 28): `hands: in the
    scene`, `hands: through FX` or `hands: over` — with the hands node's
    number when the graph has more than one, `as lines` for a node drawn
    as lines, and how a layer is laid on when it is not plainly over
    (`· depth-aware`, `· added`). `hands: off` with the hands switch off — but an
    output whose scene holds the hands says so whatever its switch."""
    inside = wiring.in_scene()
    if inside and sw.scene:
        # the scene holds the hands whatever this output's hands switch
        # says (that switch then wires only the readout)
        return "hands: " + " · ".join(f"in the scene{_node_words(wiring, h)}" for h in inside)
    if not sw.hands:
        return "hands: off"
    return f"hands: {'through FX' if sw.through else 'over'}{layer_words(wiring)}"


def _node_words(wiring: Wiring, h: HandsAt) -> str:
    """` (2)` when the graph has more than one hands node, ` as lines`."""
    return ((f" ({h.n})" if len(wiring.nodes()) > 1 else "")
            + (" as lines" if h.draw == "lines" else ""))


def layer_words(wiring: Wiring) -> str:
    """What the hands' layer is, after "over" or "through FX": its node's
    number when there are two, `as lines`, and its blend when it is not
    plainly over (`· depth-aware`, `· added`); "" for today's layer."""
    words = _node_words(wiring, wiring.layer_node())
    if wiring.blend != "over":
        words += " · depth-aware" if wiring.blend == "depth" else " · added"
    return words


def history_words(wiring: Wiring) -> str:
    """What the history captures under `wiring`, in words (the LOOKBACK
    page, plan 26 A4): `history: the scene`, or `history: the scene · with
    the hands` — the hands' layer laid on, or hands drawn inside the scene
    (which then holds them whatever the history node says). Plan 30 D1:
    then each effect placed on the history's way in or after it
    (`acid 2 before the history`)."""
    if wiring.history == "scene+hands" or wiring.in_scene():
        words = "history: the scene · with the hands"
    else:
        words = "history: the scene"
    # plan 30 D1: an effect placed on the history's way in, or after it
    for e in wiring.placed:
        if e.where in (("after", "scene"), ("into", "history"), ("after", "history")):
            words += " · " + placement_words(e)
    # plan 28 N4: a wire into the history's picture
    for w in wiring.wires:
        if w.node == "history":
            words += " · " + wire_words(w)
    return words


def output_placement_words(wiring: Wiring, n: int, scene: bool, hands: bool) -> str:
    """The placed effects one output's picture goes through (plan 30 D1:
    the OUTPUT page's "shows:" line), each ` · ` and its words: those on
    this output (`palette 2 on output 2 only` reads `palette 2 on this
    output only`), those on the hands while it shows them, those on the
    scene's way (the history, an effect of the chain) while it shows the
    scene; "" for none."""
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
    `the history`, `output 2`, `acid 2`."""
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
    if where == "history":
        return f"{w} into the history only"
    return f"{w} before {_node_said(where)}"


def placed_chips(spec: GraphSpec | None) -> dict[str, str]:
    """Each placed effect instance → where it sits, in a chip's few words
    (plan 30 D2: the FX page): `after hands`, `into output 2`, `after
    scene`, `into history`, `after acid 2`. The FX page edits the default
    chain, so a name here is drawn apart from the run's chips, says this
    in place of a place in the order, and is not dragged. The one source
    of these words: N4's wires extend it (an effect on a wire says where
    the wire takes it). None (no preset graph) → {}."""
    if spec is None:
        return {}
    out: dict[str, str] = {}
    w = spec.wiring()
    # D1's placements, then (plan 28 N4) the wires D1 would write short
    for e in w.placed:
        key, where = e.where
        out[e.name] = f"{key} {where.replace('.', ' ')}"
    # plan 28 N4: an effect a wire feeds and wires on (`after history into
    # output 2`), or wires into a port D1 has no word for
    ins = {x.node: x.src for x in w.wires if wire_node_kind(x.node) == "effect"}
    outs: dict[str, list[str]] = {}
    for x in w.wires:
        if wire_node_kind(x.src) == "effect":
            outs.setdefault(x.src, []).append(x.node if x.port == "image" else x.dst)
    for name in sorted(set(ins) | set(outs)):
        said = ([f"after {ins[name]}"] if name in ins else []) + (
            ["into " + ", ".join(outs[name])] if name in outs else [])
        out[name] = " ".join(said).replace(".", " ")
    return out


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
    if w.node == "history":
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
    frames: dict[int, moderngl.Texture | None] = field(default_factory=dict)  # end → texture; None: direct
    failed: set[int] = field(default_factory=set)
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
        """The views pipeline end `end` feeds this frame (indexes into
        `views`): each output's wired end, settled (`Output.settle`).
        Asked by the pipeline ends, which run after the hands' layer —
        whether a hand shows decides where a through output's picture
        comes from."""
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
        """This node's `Ghost` (`Renderer.ghost_of`)."""
        return ghost_of(frame.r, self.name)

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
    backdrop (`GROUNDED`), so it is a premultiplied layer the backdrop
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
        if self.ground is None:
            self._run(frame)
            return
        r = frame.r
        r.scene_ground = self.ground
        try:
            self._run(frame)
        finally:
            r.scene_ground = None

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


def picture(frame: Frame, node: Node) -> moderngl.Texture | None:
    """`node`'s picture at `frame`'s size as a texture (plan 33 R): the
    one it made, else painted once a frame into a texture of the
    renderer's under its name (`Frame.key`) — what a consumer that binds a
    picture reads (the pattern's layer, a branch under the scene)."""
    tex = node.image(frame)
    if tex is not None:
        return tex
    key = node.name + "#picture"
    if key not in frame.data:
        tex, fbo = frame.r._frame_target(frame.key(key), frame.size)
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
    (`Ghost.readout`) that no effect bends — while some output puts the
    hands through the effects (`readout` "through", today's rule), or
    always (`readout` "always": the hands are also inside the scene, so
    the guide may never be in a picture the effects bend). With no
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

    def __init__(self, name: str, after: tuple[Node, ...] = (), readout: str = "through",
                 **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.readout = readout

    def ghost(self, frame: Frame):
        """The `Ghost` this layer draws: its geometry's, or the renderer's."""
        geo = self.inputs["geometry"]
        return geo.ghost(frame) if geo is not None else frame.r.ghost

    def drew(self, frame: Frame) -> bool:
        """The layer drew this frame (a hand shows)."""
        return bool(frame.data.get(self.name + "#drew"))

    def run(self, frame: Frame) -> None:
        r, views = frame.r, frame.views
        frame.data[self.name + "#drew"] = False
        if self.readout == "always":
            split = True
        else:
            split = frame.fx_on and any(v.switches.hands and v.switches.through for v in views)
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
        src = self.inputs["image"].image(frame)
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
    with mix above 0, the stack on and above mix 0 — no target, no order:
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
    `fx.<effect>.*`; the node's own `name` is the effect's in the scene's
    pipeline and `acid(scene+hands)` … in the others (`effect_node_name`).

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

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        src = self.inputs["image"]
        if src is None:
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


class Fx(Node):
    """The pipeline's end (plan 30 D0: the class keeps its name and its
    `fx` lines; before D0 it ran every effect as one block). Its input is
    the pipeline's run of `Effect` nodes — the effects wired from `frame`
    into `fx.image` (plan 33 R), an off one reading through — whose last node paints
    into the end's destination; with no effect on this frame the run
    reads straight through to the pipeline's source (the history, or the
    composite laying the hands on) and nothing of the chain is touched.
    The clocks move once a frame whatever runs (`FxState.advance_to`);
    each pipeline that runs with an effect on is one of
    `frame.stats["chain_runs"]`. The end's own line on SYSTEM is the work
    beyond its effects' passes — none — and each effect that ran has its
    own.

    As the pipeline's end it decides where the picture lands (`run`):
    straight into the one output that takes it when that output is at
    the frame's size, unflipped and on this context, else into the
    pipeline's frame texture, once, for every output that takes it. A
    pipeline no view takes this frame does not run. A pipeline that
    raises marks its views (`View.error`, named after the pipeline) and
    they show their ground.

    A pipeline whose source lays a layer on before the effects (a
    `Composite` with an `over`: today's "through") is only itself while
    the layer is bent: an effect on and the layer drawn. Otherwise its
    outputs take `fallback` — the pipeline it was laid onto, or the
    ground (None) — with the layer laid over at the output instead
    (`Output.settle`): the effects have nothing to bend."""

    KIND = "fx"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = IMAGE

    def __init__(self, name: str, key: int, after: tuple[Node, ...] = (),
                 fallback: Fx | None = None, **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.key = key                # the pipeline this node ends (outputs.SCENE …)
        self.fallback = fallback

    @property
    def effects(self) -> list[Effect]:
        """The pipeline's run of effect nodes, first to last — its wires'
        from `frame` (plan 33 R; plan 30 D1: an effect the preset placed
        after or into one of them sits in the line but is not of the run)."""
        run: list[Effect] = []
        src = self.inputs["image"]
        while isinstance(src, Effect):
            if src.placed is None:
                run.append(src)
            src = src.inputs["image"]
        return run[::-1]

    @property
    def source(self) -> Node | None:
        """What the run starts from: the history, or the composite that
        lays the hands on before the effects."""
        src = self.inputs["image"]
        while isinstance(src, Effect):
            src = src.inputs["image"]
        return src

    @property
    def layer(self) -> Node | None:
        """The layer this pipeline lays on before the effects, if any."""
        src = self.source
        return src.inputs["over"] if isinstance(src, Composite) else None

    def bent(self, frame: Frame) -> bool:
        """Whether this pipeline is itself this frame (see the class)."""
        layer = self.layer
        return layer is None or (frame.fx_on and layer.image(frame) is not None)

    def run(self, frame: Frame) -> None:
        users = frame.users(self)
        if not users:
            return
        r, views, stats = frame.r, frame.views, frame.stats
        only = views[users[0]]
        # a flipped output (plan 23 WP1) takes the frame through a texture:
        # the mirror is `_show`'s, at the output stage
        # plan 30 D1: an output whose picture goes through an effect placed
        # into it folds the frame texture, so it is never painted direct
        # plan 32 T9: nor is a published window's (its tap is presented
        # from the frame texture)
        direct = (len(users) == 1 and only.target is not None
                  and getattr(only, "tap", None) is None
                  and tuple(only.rect[2:]) == frame.size
                  and not getattr(only.switches, "flip_x", False)
                  and not getattr(only.switches, "flip_y", False)
                  and not (frame.graph is not None and frame.graph.folds(users[0])))
        stats["pipelines"].append(self.key)
        try:
            if direct:
                dst, tex = only.target, None
                dst.viewport = only.rect
            else:
                tex, dst = r._frame_target(self.key, frame.size)
                stats["direct"] = False
            self.paint(frame, dst)
            frame.frames[self.key] = tex
        except Exception as e:  # noqa: BLE001 — one pipeline must not take the others down
            frame.failed.add(self.key)
            for i in users:
                r._view_failed(views[i], NAMES.get(self.key, self.name), e)
            r._rebind(frame.target, frame.vp)

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        """Its input into `dst`: the run of effects (or, with none on, the
        source read straight through)."""
        src = self.inputs["image"]
        if frame.fx_on:
            frame.r.fx.state.advance_to(frame.t)
        src.paint(frame, dst)
        if frame.fx_on:
            frame.stats["chain_runs"] += 1


class Wired(Fx):
    """The end of a picture a wire takes into an output's `image` port
    (plan 28 N4: `{"from": "acid.2", "to": "output.2.image"}`) — not a
    chain's run but any image node: the history, an effect wired on, a
    layer, a composite. As an end it decides where the picture lands as
    `Fx` does (straight into its one output when that output is at the
    frame's size and unflipped, else once into a frame texture under its
    own key, its name); it is always itself (no fallback) and counts no
    chain run: an effect on its way runs its own pass and moves its own
    clock (`FxChain.run_one`)."""

    KIND = "wired"

    def __init__(self, name: str, after: tuple[Node, ...] = (), **inputs: Node | None):
        super().__init__(name, name, after, **inputs)

    def bent(self, frame: Frame) -> bool:
        return True

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        src = self.inputs["image"]
        if src is not None:
            src.paint(frame, dst)


def effect_node_name(effect: str, key: int) -> str:
    """The node of effect instance `effect` in pipeline `key`'s run: the
    effect's own name in the scene's pipeline (`palette`, `acid.2`: the
    SYSTEM line, the word a placement names), the pipeline's suffix in the
    others (`acid(scene+hands)`, `acid(hands)`), as the ends are named."""
    return effect if key == SCENE else effect + FX_NAMES[key][len("fx"):]


# ---------------------------------------------------------------- output

class Output(Node):
    """One render output (`Renderer._compose`): the picture on its `image`
    port (a pipeline's end; already there when painted direct, else shown
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
        laid over after it, its blend) or None) — `outputs.route`'s table
        as wiring: a through end that is not bent stands down for its
        fallback and its layer goes over here."""
        key = self.name + "#settle"
        if key in frame.data:
            return frame.data[key]
        end = self.inputs["image"]
        while isinstance(end, Effect):            # D1: the end behind its folds
            end = end.inputs["image"]
        over, blend = self.inputs["hands"], self.blend
        if isinstance(end, Fx) and not end.bent(frame):
            over, blend = end.layer, end.source.blend
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
        src = self.inputs["readout"]
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
    is built (`default_graph`), `dormant` says why a placed effect has no
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
        # (the stack it was handed for a wiring that says no run — the
        # renderer's key, `Renderer._graph_for`; None for one that does)
        self.stack: tuple[str, ...] | None = None
        self._readers: dict[str, int] = {}
        self._pool: int | None = None
        self._framed: frozenset[str] | None = None     # plan 33 R: `at_frame`, settled
        # plan 33 S: `pulled`, by the switches' picks (None: not yet asked)
        self._pulled: dict[tuple[int, ...], frozenset[str]] | None = None

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
    """What selects the default graph besides the wiring: each view's
    scene, hands and through switches. Everything else about a view (its
    size, its flips, a presenter) is read when its nodes run."""
    return tuple((bool(v.switches.scene), bool(v.switches.hands), bool(v.switches.through))
                 for v in views)


def pipelines_of(switches: list[Switches], in_scene: bool = False) -> list[int]:
    """The pipelines the switches can reach (`outputs.route`), in run
    order: SCENE for any view showing the scene; SCENE+HANDS for a view
    with the scene and the hands through (never while the hands are in the
    scene: the effects bend them there already); HANDS for one with the
    scene off and the hands through. Whether a hand shows, and whether an
    effect is on, decide per frame which of them run."""
    keys = []
    if any(sw.scene for sw in switches):
        keys.append(SCENE)
    if not in_scene and any(sw.scene and sw.hands and sw.through for sw in switches):
        keys.append(SCENE_HANDS)
    if any(not sw.scene and sw.hands and sw.through for sw in switches):
        keys.append(HANDS)
    return [k for k in PIPELINES if k in keys]


# the pipelines' node names, by key: the composite that lays the hands
# on before the chain, and the chain itself
COMPOSITE_NAMES = {SCENE_HANDS: "composite(scene+hands)", HANDS: "composite(hands)"}
FX_NAMES = {SCENE: "fx", SCENE_HANDS: "fx(scene+hands)", HANDS: "fx(hands)"}
HISTORY_COMPOSITE = "composite(history)"


def default_graph(views: list[View], wiring: Wiring | None = None,
                  clouds: tuple[str, ...] = (), effects: tuple[str, ...] = (),
                  stack: tuple[str, ...] | None = None) -> Graph:
    """The frame as a graph, from the views' switches and the wiring
    (`Wiring`; the default is today's frame). Each output's three
    switches are its wiring:

    - **scene** on: its picture is the scene's pipeline (the history, the
      effects); off, its ground;
    - **hands** on: the hands' layer laid over its picture at the output
      ("over") — or, with **through**, laid onto the history before the
      effects ("through": SCENE+HANDS, or the layer alone through them,
      HANDS, with the scene off) — and the readout on it;
    - with the hands **in the scene** (`Wiring.hands`), an output showing
      the scene shows them there (its hands switch then wires only the
      readout); one without the scene still gets the layer, over or
      through.

    The nodes: the shape, and the hands while anything draws them; the
    scene (the hands first when they are in it); the cover; the hands'
    layer while an output lays it on or the history holds it; the
    readout on its own when only the scene holds the hands; the history;
    per reachable pipeline a composite and the chain; the capture after
    every pipeline, from the scene or the scene with the hands' layer
    (`Wiring.history`); one output per view, after the capture.

    Plan 26 A4: the hands are one node per instance (`Wiring.nodes`:
    `ghost`, `ghost.2` …, each its own `Ghost`). Every node drawn into
    the scene is one of the scene's geometries; the layer — laid on the
    outputs that do not show the hands in their scene — is drawn from the
    node `into` "layer", else from the first (`Wiring.layer_node`), and
    named after it (`hands`, `hands.2`). An output showing the scene with
    hands in it takes the first in-scene node's readout; one taking the
    layer, the layer's.

    Plan 26 A4b: `clouds`, the roles of the listed `cloud` devices
    (`cloud_roles`), each a point-cloud geometry in the scene, solid,
    before the hands; none listed, the graph is the one above.

    Plan 33 R: `effects`, the effect instances this build has (what a run,
    a placement or a wire may name). Each pipeline's run is the wiring's
    (`Wiring.run`: the wires `frame → … → fx.image`, in wire order) — one
    `Effect` node per instance between the pipeline's source (`frame`) and
    its end (`Fx`), named by `effect_node_name`. An effect of the run this
    build lacks (its file gone mid-show) has no node: the run reads
    through it, and `Graph.dormant` says so (`no acid effect in this
    build`) — the wires stay, so the node is back when the file is. An
    effect on no wire has no node at all. An off effect of the run reads
    through, so switching one on or off changes no node.

    A wiring that says no run (`Wiring.run` None: no preset's graph
    reached it) takes `stack` (else `effects`) in the order given, every
    effect not placed or wired, as before plan 33 (plan 30 D0) — the
    renderer hands it the frame-aimed effects in the stack's order until
    the stack retires (plan 33 T7). None given, the ends read their
    sources directly: the frame with no effect.

    Plan 30 D1: `Wiring.placed`, the effects the preset places, are not
    in the runs; each is put on its edge once the frame is built
    (`_place`): `after` a node on that node's picture — every consumer of
    it reads the effect, but for the ports that read something else of it
    (`Node.REFS`: a depth, the readout, the face buffer) — or `into` one
    on its `image` input alone. A placement on a node this graph lacks
    (no hands layer, an output not open, an effect not on disk) leaves
    the effect dormant — no node, no pass, the words in `Graph.dormant`;
    one that makes a loop is refused (`Graph.notes`) and the effect is in
    the run at its order. The hands' layer an effect is placed on splits
    its readout always: the guide and the labels are never folded.

    Plan 32 R: with `Wiring.backdrop` the scene is cleared see-through and
    laid over the channel's node (`media.<c>`, at `backdrop.alpha`) in a
    composite, `grounded`, which the history reads; the capture reads
    `grounded` with `backdrop_history`, else the scene (each with the
    hands' layer on for "scene+hands"). The hands-only pipeline has no
    backdrop. Without one the graph is the one above, node for node. A
    channel a wire leaves (`media.c → output.2.image`) is a `media.<c>`
    node of its own (`media.<c>(wire)` beside the backdrop's).

    Plan 33 R: the faces, the pattern's layer and the backdrop are wire
    ends. A wire touching the pattern makes its node (`PatternNode`,
    `pattern`): a channel straight into `pattern.media` is read raw, with
    no node of its own, as the faces always read `view.media`'s; anything
    else wired there is a branch. A wire into `shape.faces` is the shape's
    `faces` port. A branch into `backdrop.image` lays under the scene in
    `grounded` at `backdrop.alpha` (`Composite.under_alpha_of`), as the
    channel does; either way `backdrop` (`BackdropNode`) is the sink. A
    branch is made where its consumer asks (`Node.size_for`): an effect
    only the faces read is made at `FACE_PIC`², never folded at the
    frame's size (`Graph.at_frame`)."""
    wiring = wiring if wiring is not None else Wiring()
    switches = [v.switches for v in views]
    inside = wiring.in_scene()
    in_scene = bool(inside)
    from_layer = wiring.layer_node()
    depth_aware = wiring.blend == "depth"
    # D1: the placements this graph honours (a loop of them is refused:
    # those take the run at their order), and the ones on the layer
    loops = placement_loops(wiring.placed)
    placed = [e for e in wiring.placed if e.name not in loops]
    on_layer: set[str] = set()
    grew = True
    while grew:
        grew = False
        for e in placed:
            if e.name not in on_layer and e.where[0] == "after" and (
                    e.where[1] == layer_name(from_layer.n) or e.where[1] in on_layer):
                on_layer.add(e.name)
                grew = True
    out_of_run = {e.name for e in placed}
    # plan 28 N4: the effects the wires build as edges are not of the run
    # either, and a wire from the layer wants it built whatever the switches
    # (plan 32 R: an aux wire moves neither of its ends out of the run)
    out_of_run |= {name for w in wiring.wires if not is_aux(w) for name in (w.src, w.node)
                   if wire_node_kind(name) == "effect"}
    wired_layer = any(w.src == layer_name(from_layer.n) for w in wiring.wires)
    # plan 33 R: the pattern's node, the channel read raw into its layer,
    # and a branch under the scene
    straight = next((w for w in wiring.wires if w.dst == "pattern.media"
                     and wire_node_kind(w.src) == "media"), None)
    want_pattern = any(w.src == "pattern" or w.dst == "pattern.media" for w in wiring.wires)
    under_branch = any(w.dst == "backdrop.image" for w in wiring.wires)

    def layered(sw: Switches) -> bool:
        return bool(sw.hands) and (not in_scene or not sw.scene)

    want_layer = any(layered(sw) for sw in switches) or (
        wiring.history == "scene+hands" and not in_scene) or wired_layer
    g = Graph(graph_key(views), wiring)
    g.clouds = tuple(clouds)                       # plan 26 A4b: what it was built for
    g.effects = tuple(effects)                     # plan 33 R: the instances it may hold
    g.placed_names = frozenset(out_of_run)         # plan 30 D1: placed or wired
    g.stack = tuple(stack) if stack is not None else None
    said = getattr(wiring, "run", None)            # (a Wiring from before a hot reload)
    if said is not None:                           # plan 33 R: the run is its wires
        names = list(said)
    else:                                          # (no run said: the stack, as plan 30 D0)
        names = [e for e in (stack if stack is not None else effects) if e not in out_of_run]
    have = set(g.effects)
    for e in names:
        if e not in have:
            g.dormant[e] = f"{e} in the run — no {e} effect in this build"
    g.run = tuple(e for e in names if e in have)   # the effects of every pipeline's run
    points = cloud_nodes(g, g.clouds)
    if want_pattern:
        g.add(PatternNode("pattern",
                          channel=straight.src.partition(".")[2] if straight is not None else ""))
    shape = g.add(Shape("shape"))
    geo: dict[int, Hands] = {}
    for h in wiring.nodes():
        if h.into == "scene" or (want_layer and h == from_layer):
            geo[h.n] = g.add(Hands(hands_name(h.n), draw=h.draw))
    # plan 32 R: with a backdrop the scene clears see-through (`Scene.ground`)
    scene = g.add(Scene("scene", geometries=[*points, *(geo[h.n] for h in inside), shape],
                        ground=0.0 if wiring.backdrop or under_branch else None))
    cover = g.add(Cover("cover", scene=scene))
    # plan 32 R (row 330): the scene laid over the backdrop's channel before
    # the history, so the echoes, the dream and the effects are over both
    grounded = None
    if wiring.backdrop:
        under = g.add(MediaNode(media_name(wiring.backdrop), wiring.backdrop,
                                alpha_of="backdrop_alpha"))
        grounded = g.add(Composite(GROUNDED, blend="over", over=scene, under=under))
        g.add(BackdropNode("backdrop", image=under))
    elif under_branch:
        # plan 33 R: a branch's picture under the scene — `under` is the
        # wire's (`_Wiring._put`), laid on at `backdrop.alpha`
        grounded = g.add(Composite(GROUNDED, blend="over", over=scene,
                                   under_alpha_of="backdrop_alpha"))
        g.add(BackdropNode("backdrop"))
    layer = (g.add(HandsLayer(layer_name(from_layer.n),
                              readout="always" if from_layer.into == "scene" or on_layer
                              else "through",
                              geometry=geo[from_layer.n])) if want_layer else None)
    # the readout of an output that shows the hands inside its scene: the
    # first in-scene node's — its own layer's when it makes the layer
    # (split always), else the readout alone
    scene_readout = None
    if in_scene and any(sw.scene and sw.hands for sw in switches):
        first = inside[0]
        scene_readout = (layer if layer is not None and from_layer == first else
                         g.add(Readout(readout_name(first.n), geometry=geo[first.n])))
    # B-I1: over a backdrop the history keeps out of, the scene alone holds
    # the wake back. With `backdrop_history` the echoes hold the backdrop
    # too, so the history occludes from its own input as it always did —
    # by the scene alone, a still backdrop would add onto itself to white
    history = g.add(History("history", image=grounded or scene, cover=cover,
                            occluder=scene if grounded is not None
                            and not wiring.backdrop_history else None))
    depth = scene if depth_aware else None
    ends: dict[int, Fx] = {}
    # every pipeline end runs after the hands' layer: whether a hand shows
    # this frame decides which pipelines the views take
    gate = (layer,) if layer is not None else ()

    def run(key: int, src: Node) -> Node:
        # the pipeline's run of effect nodes from its `frame` (`src`), in
        # wire order (plan 33 R); a name some other node has (or will have)
        # is kept apart by the params' prefix, `fx.<name>`
        for e in g.run:
            name = effect_node_name(e, key)
            if (name in g.nodes or name in ("capture", *FX_NAMES.values())
                    or name.startswith("output.")):
                name = f"fx.{name}"
            src = g.add(Effect(e, image=src, node=name))
        return src

    for key in pipelines_of(switches, in_scene):
        if key == SCENE:
            ends[key] = g.add(Fx(FX_NAMES[key], key, after=gate, image=run(key, history)))
            continue
        src = g.add(Composite(COMPOSITE_NAMES[key], blend=wiring.blend, depth=depth,
                              under=history if key == SCENE_HANDS else None, over=layer))
        ends[key] = g.add(Fx(FX_NAMES[key], key, after=gate, image=run(key, src),
                             fallback=ends.get(SCENE) if key == SCENE_HANDS else None))
    # what the history captures: the scene — or (plan 32) the scene over the
    # backdrop with `backdrop_history` — with the hands' layer laid on it
    # for "scene+hands"
    held = grounded if grounded is not None and wiring.backdrop_history else scene
    if wiring.history == "scene+hands" and layer is not None and not in_scene:
        held = g.add(Composite(HISTORY_COMPOSITE, blend=wiring.blend, depth=depth,
                               under=held, over=layer))
    capture = g.add(Capture("capture", image=held, after=tuple(ends[k] for k in PIPELINES
                                                                if k in ends)))
    for i, sw in enumerate(switches):
        image = None
        if sw.scene:
            through = sw.hands and sw.through and not in_scene
            image = ends[SCENE_HANDS if through else SCENE]
        elif sw.hands and sw.through:
            image = ends[HANDS]
        over = layer if layered(sw) and not sw.through else None
        readout = None
        if sw.hands:
            readout = scene_readout if (in_scene and sw.scene) else layer
        g.add(Output(f"output.{i + 1}", i, after=(capture,), blend=wiring.blend, image=image,
                     hands=over, readout=readout, depth=depth if layered(sw) else None))
    for name, words in loops.items():
        e = next(p for p in wiring.placed if p.name == name)
        g.notes.append(f"{name} {e.where[0]} {e.where[1]!r} — that makes a loop ({words}); "
                       "the default placement")
    # plan 28 N4: the wires, as edges — those from the scene, a layer, the
    # history or an effect of the run first, then D1's placements (which
    # may sit after what a wire made), then the wires from a placed effect
    # plan 32 R: a channel a wire leaves is a node of its own, at alpha 1 —
    # beside the backdrop's when the backdrop is the same channel
    media: dict[str, MediaNode] = {}
    for w in wiring.wires:
        if wire_node_kind(w.src) == "media" and w.src not in media and w != straight:
            name = w.src if w.src not in g.nodes else f"{w.src}(wire)"
            media[w.src] = g.add(MediaNode(name, w.src.partition(".")[2]))
    wiring_left = _Wiring(g, wiring, layer, depth, media)
    wiring_left.run(final=False)
    _place(g, placed)
    wiring_left.run(final=True)
    wiring_left.aux()
    return g


# the wire ends `_Wiring` makes as nodes of their own, once what they read
# is in the graph (plan 28 N4; plan 33 S: the switch)
MAKERS = ("effect", "composite", "switch")


class _Wiring:
    """The wire list's edges built into graph `g` (plan 28 N4,
    `default_graph`). Each effect or composite a wire feeds or takes from
    is made as one node (`Effect(…, placed="wire")`, `Composite`), once
    what it reads is in the graph; then each wire out of it, or out of the
    scene, a layer or the history, is put on its port: an output's
    `image` through a `Wired` end of its own (so the output shows that
    picture whatever its switches), its `hands` (the layer laid over at
    the output, and its guide where the output had none) or its
    `readout`; the history's picture. A wire whose node this graph lacks
    (an output not open, no layer, an effect not on disk) is dormant, in
    `Graph.dormant` under the wire's words."""

    def __init__(self, g: Graph, wiring: Wiring, layer: Node | None, depth: Node | None,
                 media: dict[str, MediaNode] | None = None):
        self.g, self.layer, self.depth = g, layer, depth
        self.media = media or {}          # plan 32 R: a wire's channel name → its node
        self.blends = {c.name: c.blend for c in wiring.composites}
        # plan 32 R: the aux wires are put on last (`aux`), once every node
        # of the effects they feed is in the graph
        self.aux_wires = [w for w in wiring.wires if is_aux(w)]
        # (plan 33 R: a channel straight into the pattern's layer is the
        # pattern node's own `channel`, read raw — no edge)
        pattern = g.nodes.get("pattern")
        raw = getattr(pattern, "channel", "")
        self.wires = [w for w in wiring.wires if not is_aux(w)
                      and not (raw and w.dst == "pattern.media" and w.src == media_name(raw))]
        # plan 33 R: an effect of the run has its nodes already (one per
        # pipeline): a wire on from it reads the scene pipeline's
        # plan 33 S: and a switch is made like a composite, once what its
        # wired inputs read is in the graph
        self.makers = {name for w in self.wires for name in (w.src, w.node)
                       if wire_node_kind(name) in MAKERS} - set(g.run)
        self.made: dict[str, Node | None] = {}
        self.done: set[Wire] = set()
        self.explicit = {(w.node, w.port) for w in self.wires}

    def node(self, name: str) -> Node | None:
        """What a wire's name is in the graph built so far, or None."""
        g = self.g
        if name in self.made:
            return self.made[name]
        kind = wire_node_kind(name)
        if kind == "media":
            return self.media.get(name)
        if kind == "switch":            # (made, above, or not yet)
            return None
        if kind in ("effect", "composite"):
            if name in self.makers:
                return None
            got = g.nodes.get(name)
            if isinstance(got, Effect) and got.effect == name:
                return got
            nodes = _placed_nodes(g, name)
            return nodes[0] if nodes else None
        got = g.nodes.get(name)
        if kind == "layer" and not isinstance(got, HandsLayer):
            return None
        return got

    def _dormant(self, w: Wire, why: str) -> None:
        self.done.add(w)
        self.g.dormant[str(w)] = f"wire {w} — {why}"

    def _lacks(self, name: str) -> str:
        kind = wire_node_kind(name)
        if kind == "layer":
            return f"no {name} layer this frame"
        if kind == "output":
            return f"no output {name.partition('.')[2]} this frame"
        if kind == "effect":
            return (f"{name} is dormant this frame" if name in self.g.dormant
                    else f"no {name} effect this frame")
        return f"no {name} this frame"

    def run(self, final: bool) -> None:
        g, changed = self.g, False
        grew = True
        while grew:
            grew = False
            for name in sorted(self.makers - set(self.made)):
                ins = [w for w in self.wires if w.node == name and w not in self.done]
                srcs = {w.port: self.node(w.src) for w in ins}
                if (final and wire_node_kind(name) == "switch"
                        and any(v is None for v in srcs.values())):
                    # plan 33 S: a switch is made with the inputs it has —
                    # one whose source this graph lacks is dormant alone
                    for w in [w for w in ins if srcs[w.port] is None]:
                        self._dormant(w, self._lacks(w.src) if w.src not in self.makers
                                      else f"{w.src} has no picture this frame")
                    ins = [w for w in ins if srcs[w.port] is not None]
                    srcs = {w.port: srcs[w.port] for w in ins}
                if any(v is None for v in srcs.values()):
                    if final:
                        for w in ins:
                            self._dormant(w, self._lacks(w.src) if w.src not in self.makers
                                          else f"{w.src} has no picture this frame")
                        self.made[name] = None          # (nothing made: its wires out wait)
                    continue
                self._make(name, ins, srcs)
                grew = changed = True
        for w in self.wires:
            if w in self.done or wire_node_kind(w.node) in MAKERS:
                continue
            src = self.made.get(w.src) if w.src in self.makers else self.node(w.src)
            if src is None:
                if final or (w.src not in self.makers and wire_node_kind(w.src) != "effect"):
                    self._dormant(w, self._lacks(w.src) if w.src not in self.makers
                                  else f"{w.src} has no picture this frame")
                continue
            why = self._put(w, src)
            self.done.add(w)
            if why is not None:
                self._dormant(w, why)
            changed = True
        if changed:
            g.relink()

    def aux(self) -> None:
        """Each aux wire on its effect's `aux` port (plan 32 R): every node
        of the instance — one per pipeline's run, or the one placed or
        wired — reads the wire's source there. A source this graph lacks,
        an effect with no node, or a node the source already reads (a loop:
        an effect later in the run as the aux of one before it) is dormant,
        in words."""
        g = self.g
        for w in self.aux_wires:
            src = self.node(w.src)
            if src is None:
                self._dormant(w, self._lacks(w.src))
                continue
            nodes = _placed_nodes(g, w.node)
            if not nodes:
                self._dormant(w, self._lacks(w.node))
                continue
            ups = _upstream(src)
            fed = [n for n in nodes if n is not src and id(n) not in ups]
            for n in fed:
                n.inputs[AUX] = src
            self.done.add(w)
            if len(fed) < len(nodes):
                self._dormant(w, f"{w.node} feeds {w.src}: that makes a loop")
        if self.aux_wires:
            g.relink()

    def _make(self, name: str, ins: list[Wire], srcs: dict[str, Node | None]) -> None:
        g = self.g
        node_name = name if name not in g.nodes else f"fx.{name}"
        if wire_node_kind(name) == "switch":       # plan 33 S (a reserved name: no clash)
            node = SwitchNode(name, **srcs)
        elif wire_node_kind(name) == "composite":
            blend = self.blends.get(name, "over")
            node = Composite(node_name, blend=blend, under=srcs.get("under"),
                             over=srcs.get("over"),
                             depth=self.depth if blend == "depth" else None)
        else:
            src = srcs.get("image")
            if src is None:              # fed by no wire: what its one port read
                outs = [w for w in self.wires if w.src == name]
                src = self._reads(outs[0]) if outs else None
                if src is None:
                    for w in outs:
                        self._dormant(w, f"{name} is fed by nothing here: wire its input")
                    self.made[name] = None
                    return
            node = Effect(name, image=src, node=node_name, placed="wire")
            if isinstance(src, HandsLayer):
                src.readout = "always"   # the guide is never folded
        g.add(node)
        self.made[name] = node
        self.done.update(ins)

    def _sink(self, w: Wire, src: Node) -> str | None:
        """`src` into the faces, the pattern's layer or the backdrop (plan
        33 R); None, or why it is dormant — a picture drawn from the faces
        (the scene, the history, what reads them) cannot go back into
        them, nor one drawn from the backdrop (the history over it) under
        the scene."""
        g = self.g
        ups = _upstream(src) | {id(src)}
        if w.node in ("shape", "pattern"):
            shape = g.nodes.get("shape")
            if shape is None or id(shape) in ups:
                return f"{w.src} is drawn from the faces: that makes a loop"
            if w.node == "shape":
                shape.inputs["faces"] = src
                return None
            pattern = g.nodes.get("pattern")
            if not isinstance(pattern, PatternNode):
                return self._lacks("pattern")
            pattern.inputs["media"] = src
            return None
        grounded, back = g.nodes.get(GROUNDED), g.nodes.get("backdrop")
        if grounded is None or not isinstance(back, BackdropNode):
            return self._lacks("backdrop")
        if id(grounded) in ups:
            return f"{w.src} is drawn from what lies on the backdrop: that makes a loop"
        grounded.inputs["under"] = src
        back.inputs["image"] = src
        return None

    def _reads(self, w: Wire) -> Node | None:
        """What port `w.dst` reads in the graph as built (its default)."""
        out = self.g.nodes.get(w.node)
        return out.inputs.get(w.port) if out is not None else None

    def _put(self, w: Wire, src: Node) -> str | None:
        """`src` on wire `w`'s port; None, or why it is dormant."""
        g = self.g
        if w.node == "history":
            g.nodes["history"].inputs["image"] = src
            return None
        if w.node in ("shape", "pattern", "backdrop"):
            return self._sink(w, src)
        out = g.nodes.get(w.node)
        if not isinstance(out, Output):
            return self._lacks(w.node)
        if w.port == "image":
            end = g.add(Wired(f"wire({w.node})", after=(self.layer,) if self.layer else (),
                              image=src))
            out.inputs["image"] = end
            if out.inputs["hands"] is None and (w.node, "readout") not in self.explicit:
                # the guide goes with the hands shown: a picture by a wire
                # took the hands its switches put through (or in the scene)
                out.inputs["readout"] = None
            cap = g.nodes.get("capture")
            if cap is not None:
                cap.after = (*cap.after, end)
        elif w.port == "hands":
            # a through output's switch hands are inside its picture (the
            # layer laid on before the chain): the wire replaces them, so
            # the picture becomes the end it was laid onto — the scene's,
            # or the ground — and the wired node alone is laid over
            holder, port, img = out, "image", out.inputs["image"]
            while isinstance(img, Effect):
                holder, port, img = img, "image", img.inputs["image"]
            if isinstance(img, Fx) and not isinstance(img, Wired) and img.layer is not None:
                holder.inputs[port] = img.fallback
            out.inputs["hands"] = src
            out.inputs["depth"] = self.depth
            layer = src
            while isinstance(layer, Effect):
                layer = layer.inputs["image"]
            if out.inputs["readout"] is None and isinstance(layer, HandsLayer):
                out.inputs["readout"] = layer       # the guide where it shows the hands
        else:
            out.inputs["readout"] = src
        return None


def _place(g: Graph, placed: list[EffectAt]) -> None:
    """Put each placed effect on its edge of the built graph `g` (plan 30
    D1, `default_graph`): one sitting on another placed effect after it;
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
    elif where in ("scene", "history") or where == "hands" or where.startswith("hands."):
        node = g.nodes.get(where)
        if where == "scene" and key == "after" and GROUNDED in g.nodes:
            # plan 32 R: over a backdrop the scene is a see-through layer an
            # effect would fold opaque (hiding the backdrop); the effect sits
            # after the scene laid over it instead, so it bends both — what
            # reads the scene alone (the capture without backdrop.history)
            # reads it unbent
            node = g.nodes[GROUNDED]
        if node is None or (where.startswith("hands") and not isinstance(node, HandsLayer)):
            return (f"no {where} layer this frame" if where.startswith("hands")
                    else f"no {where} this frame")
        if key == "into":                     # (only the history takes `into` here)
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
            suffix = node.name.split(where, 1)[1] if where in node.name else ""
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
