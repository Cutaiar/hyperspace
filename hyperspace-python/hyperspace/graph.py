"""The render graph (plan 26 A1): the frame as nodes, evaluated in
dependency order.

`Renderer._draw_frame` (render.py) used to be a fixed list of passes.
It is now "build or reuse the graph for this frame's views, evaluate
it": `default_graph` builds today's three pipelines (`outputs.SCENE`,
`SCENE_HANDS`, `HANDS`) as nodes from each output's `Switches`, and
`Graph.evaluate` runs the nodes once each, in an order computed when the
graph is built, never per frame. The default graphs draw every golden
frame of A0 byte for byte: this module moves no pixel.

Seven node kinds. The owner's four (wishlist, "Render graph design
decisions"):

- **Geometry** (`Shape`): draw calls in the shared camera, no framebuffer
  of its own. A3 adds the hands; A4 a point cloud.
- **Scene** (`Scene`): any number of geometries into one colour target
  (`render.SceneTarget`; depth arrives with A2).
- **Layer** (`HandsLayer`, `Cover`): one geometry into its own target.
  In A1 the hands' layer wraps `Ghost.layer` — the hands keep their own
  camera until A3 — and the cover is the faces' coverage mask the
  look-back's occlusion reads.
- **Composite** (`Composite`): two images, over — the hands laid onto the
  look-back's picture (or the ground) before the effects, today's
  "through". Add and depth-aware come with A3.

And the three that wrap what exists (A1's call, registered):

- **FX** (`Fx`): the effect chain (`fx.FxChain`), one node per pipeline,
  the effects' order inside it as today. Inactive, it passes its input
  through untouched.
- **History** (`History`, `Capture`): the look-back (`lookback.Lookback`)
  as two nodes, because its composite must read the ring before the
  frame's capture changes it: `history` lays the echoes and the dream
  over its input; `capture` puts its input into the ring after every
  composite of the frame has run.
- **Output** (`Output`): one render output — `fit`, flip, the hands over,
  the readout, the dim — exactly `Renderer._compose`, so an output in
  another context gets the same five-step `outputs.Handoff`.

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
of its outputs shows** (`Renderer._frame_target`, `_show`), as
`Renderer._pipeline` did.

**What is static and what is per frame.** The node set and the order are
a function of the views' switches alone (`graph_key`): the renderer
keeps the last graph and builds a new one only when that key changes.
Which pipelines *run* in a frame is `outputs.route` per view, resolved
after the hands' layer has drawn (whether a hand shows this frame is only
known then, exactly as before) — a pipeline with no output this frame is
skipped and its nodes read 0 ms. A3 turns the route into wiring.

Render stack (ARCHITECTURE §3): this module reads params through the
objects it is handed and never writes one; it imports moderngl and its
sibling render modules only, never params, routing, library, preset,
undo or control. Node methods are `run`, `paint`, `draw`, `image` —
never `apply`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

import moderngl

from .outputs import HANDS, NAMES, PIPELINES, SCENE, SCENE_HANDS, Switches, View, route

# port types: a colour picture at the frame's size, a one-channel mask at
# the frame's size, or draw calls (a geometry, drawn by its scene or layer)
IMAGE, MASK, GEOMETRY = "image", "mask", "geometry"


@dataclass
class Frame:
    """One frame as the nodes see it: the renderer and what
    `Renderer._draw_frame` settled before evaluation (the frame's size
    under the cap, the first output's target to bind again after a
    failure, the chain's state), and what the nodes fill in as they run
    (the cover, the hands' layer, the routes, each pipeline's frame
    texture, the failures, `stats`)."""

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
    frames: dict[int, moderngl.Texture | None] = field(default_factory=dict)  # key → texture; None: direct
    failed: set[int] = field(default_factory=set)
    _routes: list[tuple[int | None, bool]] | None = None
    _users: dict[int, list[int]] | None = None

    def routes(self) -> list[tuple[int | None, bool]]:
        """Each view's (pipeline, hands after), `outputs.route` — settled
        once, the first time a node asks, which is after the hands' layer
        (A1: the route is per frame; A3 makes it wiring)."""
        if self._routes is None:
            # right only once `hands` is settled: every caller runs after
            # the hands' layer — `Fx` through `after=gate`, `Output` through
            # its `layer` port (default_graph)
            self._routes = [route(v.switches, self.fx_on, self.hands) for v in self.views]
            users: dict[int, list[int]] = {}
            for i, (key, _) in enumerate(self._routes):
                if key is not None:
                    users.setdefault(key, []).append(i)
            self._users = users
        return self._routes

    def users(self, key: int) -> list[int]:
        """The views pipeline `key` feeds this frame (indexes into `views`)."""
        self.routes()
        return self._users.get(key, [])

    def timed(self, name: str):
        """``with frame.timed(node.name):`` — the node's GPU time this frame."""
        return self.r._timed(name)


class Node:
    """One node: a unique `name` (the SYSTEM page's line and the timer's
    key), typed input ports (`INPUTS`: port → type) wired to other nodes,
    one output of type `OUTPUT` (None for a sink), and `after`, ordering
    dependencies that carry no image (the capture after every pipeline).

    `run(frame)` is called once a frame, in the graph's order. A node
    whose picture is a texture overrides `image(frame)`; one that paints
    into its consumer's framebuffer overrides `paint(frame, dst)`. The
    default `paint` shows the texture 1:1, so any image can feed any
    image port."""

    KIND = "node"
    INPUTS: ClassVar[dict[str, str]] = {}      # port → type
    OUTPUT: str | None = None
    TIMED = True              # a line on the SYSTEM page; a geometry's time is its scene's

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
    points, instanced, painter-sorted, in the CPU camera. `prepare`
    makes the faces' picture while an effect is aimed at them
    (`Renderer._face_picture`, before the scene's target is bound);
    `draw` draws into whatever is bound. A1 keeps the scene's clear inside
    `draw_scene`, so a scene holds one shape; A3 moves it to the scene."""

    KIND = "geometry"
    OUTPUT = GEOMETRY
    TIMED = False

    def prepare(self, frame: Frame) -> None:
        frame.r._pic = frame.r._face_picture(frame.s, frame.t)

    def draw(self, frame: Frame) -> None:
        try:
            frame.r.draw_scene(frame.s, frame.w, frame.h, frame.dpr, frame.t)
        finally:
            frame.r._pic = None          # handed to that one scene pass only


# ---------------------------------------------------------------- scene

class Scene(Node):
    """The scene: its geometries into the renderer's `SceneTarget` (colour,
    at the frame's size and output 1's sample count), resolved into its
    texture. The blank texture takes the sampler units first, so the
    scene texture is never bound while it is the target."""

    KIND = "scene"
    INPUTS: ClassVar[dict[str, str]] = {"geometry": GEOMETRY}
    OUTPUT = IMAGE

    def run(self, frame: Frame) -> None:
        r, ctx = frame.r, frame.ctx
        r.scene.ensure(frame.size, frame.samples)
        for unit in range(4):
            r._blank.use(location=unit)
        geometries = [g for g in self.inputs.values() if g is not None]
        with frame.timed(self.name):
            for g in geometries:
                g.prepare(frame)
            r.scene.draw_fbo.use()
            ctx.viewport = (0, 0, *frame.size)
            for g in geometries:
                g.draw(frame)
            r.scene.resolve()

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.r.scene.tex


# ---------------------------------------------------------------- layers

class Cover(Node):
    """The faces' coverage mask (`render.CoverTarget`): the scene's faces
    again, solid, one channel — only while the look-back occludes
    (`Lookback.wants_cover`). Reads the face buffer the scene pass left,
    so it runs after the scene it masks."""

    KIND = "layer"
    INPUTS: ClassVar[dict[str, str]] = {"scene": IMAGE}
    OUTPUT = MASK

    def run(self, frame: Frame) -> None:
        frame.cover = None
        if frame.r.lookback.wants_cover():
            with frame.timed(self.name):
                frame.cover = frame.r._draw_cover(frame.w, frame.h)

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.cover


class HandsLayer(Node):
    """The hands' layer (`Ghost.layer`): the hands in their own camera,
    opaque with depth and their own MSAA, into their own texture — and,
    while some output puts them through the effects, the guide and the
    tethers' labels into a second one (`Ghost.readout`) that no effect
    bends. Runs only while some view shows hands; a pass that raises is
    caught (`Renderer._hands_failed`): the frame goes on without the
    hands and `Ghost.error` says why. A3 makes the hands a geometry."""

    KIND = "layer"
    OUTPUT = IMAGE

    def run(self, frame: Frame) -> None:
        r, views = frame.r, frame.views
        frame.hands, frame.readout = False, None
        if any(v.switches.hands for v in views):
            through = frame.fx_on and any(v.switches.hands and v.switches.through for v in views)
            try:
                with frame.timed(self.name):
                    frame.hands = bool(r.ghost.layer(frame.size, frame.t, readout=through))
            except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
                r._hands_failed(e, frame.target, frame.vp)
        frame.readout = r.ghost.readout if frame.hands else None
        frame.stats["layer"], frame.stats["readout"] = frame.hands, frame.readout is not None

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.r.ghost.tex if frame.hands else None


# ---------------------------------------------------------------- history

class History(Node):
    """The look-back's picture: its input over the echoes and the dream
    (`Lookback.composite`), occluded by the cover mask when there is one;
    a copy of the input when the look-back is off. `run` moves the
    echoes' clock and pulls a finished dream once a frame; the picture
    is painted into each consumer's framebuffer (the chain's input, or
    the output itself with no effect on)."""

    KIND = "history"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE, "cover": MASK}
    OUTPUT = IMAGE

    def run(self, frame: Frame) -> None:
        lb = frame.r.lookback
        lb.tick(frame.t)                 # echo time is seconds (plan 14 WP6)
        lb.pull()

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        src = self.inputs["image"].image(frame)
        cover = self.inputs["cover"].image(frame) if self.inputs["cover"] is not None else None
        with frame.timed(self.name):
            frame.r.lookback.composite(src, dst, cover)


class Capture(Node):
    """The look-back's capture (`Lookback.capture`): its input into the
    ring on the echoes' cadence, and out to the dream worker. Exactly
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
        with frame.timed(self.name):
            r.lookback.capture(self.inputs["image"].image(frame), r.scene.fbo)
        if frame.fx_on and not frame.stats["chain_runs"]:
            r.fx.state.advance_to(frame.t)


# ---------------------------------------------------------------- composite

class Composite(Node):
    """`over` laid on `under`: the hands' layer onto the look-back's
    picture (SCENE+HANDS) or onto the ground (HANDS, `under` None: the
    clear at the renderer's `bg_alpha`), premultiplied at `ghost.alpha`
    (`Ghost.composite`'s blend), before the effects. The hands failing
    here is caught: the chain still runs on `under` alone and
    `Ghost.error` says why."""

    KIND = "composite"
    INPUTS: ClassVar[dict[str, str]] = {"under": IMAGE, "over": IMAGE}
    OUTPUT = IMAGE

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        r, ctx, size = frame.r, frame.ctx, frame.size
        under = self.inputs["under"]
        if under is None:
            dst.use()
            ctx.viewport = (0, 0, *size)
            ctx.clear(0.0, 0.0, 0.0, frame.bg_alpha)
        else:
            under.paint(frame, dst)
        try:
            with frame.timed(self.name):
                r.ghost.composite(dst, (0, 0, *size), opaque=r.fx.opaque)
        except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
            r._hands_failed(e, frame.target, frame.vp)


# ---------------------------------------------------------------- fx

class Fx(Node):
    """The effect chain (`FxChain.run`) over its input, the last node of a
    pipeline: it paints its input into the chain's first texture
    (`FxChain.begin`) and the chain's last effect writes the destination.
    With no effect on, the input is painted straight into the destination
    and the chain is not touched.

    As the pipeline's end it decides where the picture lands (`run`):
    straight into the one output that takes it when that output is at
    the frame's size, unflipped and on this context, else into the
    pipeline's frame texture, once, for every output that takes it. A
    pipeline no view routes to this frame does not run. A pipeline that
    raises marks its views (`View.error`, named after the pipeline) and
    they show their ground."""

    KIND = "fx"
    INPUTS: ClassVar[dict[str, str]] = {"image": IMAGE}
    OUTPUT = IMAGE

    def __init__(self, name: str, key: int, after: tuple[Node, ...] = (),
                 **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.key = key                # the pipeline this node ends (outputs.SCENE …)

    def run(self, frame: Frame) -> None:
        users = frame.users(self.key)
        if not users:
            return
        r, views, stats = frame.r, frame.views, frame.stats
        only = views[users[0]]
        # a flipped output (plan 23 WP1) takes the frame through a texture:
        # the mirror is `_show`'s, at the output stage
        direct = (len(users) == 1 and only.target is not None
                  and tuple(only.rect[2:]) == frame.size
                  and not getattr(only.switches, "flip_x", False)
                  and not getattr(only.switches, "flip_y", False))
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
                r._view_failed(views[i], NAMES[self.key], e)
            r._rebind(frame.target, frame.vp)

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        src = self.inputs["image"]
        if not frame.fx_on:
            src.paint(frame, dst)
            return
        fx = frame.r.fx
        buf = fx.begin(frame.size)
        src.paint(frame, buf)
        with frame.timed(self.name):
            fx.run(dst, frame.t)
        frame.stats["chain_runs"] += 1


# ---------------------------------------------------------------- output

class Output(Node):
    """One render output (`Renderer._compose`): its pipeline's picture
    (already there when painted direct; else shown 1:1 or scaled into
    `outputs.fit`'s rect with the rest the view's ground), the hands over
    it, the readout, its mirror, its dim (master × its own) — or, for a
    view with a presenter, the `Handoff` that says the same five steps.
    In A1 the pipeline it shows is `outputs.route`'s for its switches
    this frame (A3 wires it); the `pipelines` ports hold the graph's
    pipeline ends so the wiring is in the graph."""

    KIND = "output"
    INPUTS: ClassVar[dict[str, str]] = {"scene": IMAGE, "scene+hands": IMAGE, "hands": IMAGE, "layer": IMAGE}
    OUTPUT = None

    def __init__(self, name: str, index: int, after: tuple[Node, ...] = (),
                 **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.index = index            # the view it draws, in Frame.views

    def run(self, frame: Frame) -> None:
        r, v = frame.r, frame.views[self.index]
        key, after = frame.routes()[self.index]
        # the readout goes on every output that shows the hands, over or
        # through: in its own layer the guide is in neither
        ro = frame.readout if v.switches.hands else None
        try:
            with frame.timed(self.name):
                r._compose(v, key, after, frame.frames, frame.failed, frame.size, ro)
        except Exception as e:  # noqa: BLE001 — one view must not take the others down
            r._view_failed(v, "output", e)
            r._rebind(frame.target, frame.vp)


# ---------------------------------------------------------------- the graph

class Graph:
    """Nodes and their order. `add` takes a node whose inputs are already
    in the graph (names unique); `order` is dependency order, settled when
    the graph is built: a depth-first walk from each node in the order
    they were added, dependencies first, so ties fall in insertion order
    (today's frame order). `evaluate` runs every node once."""

    def __init__(self, key: tuple = ()):
        self.key = key
        self.nodes: dict[str, Node] = {}
        self.order: list[Node] = []

    def add(self, node: Node) -> Node:
        if node.name in self.nodes:
            raise ValueError(f"two nodes named {node.name!r}")
        for dep in node.deps():
            if self.nodes.get(dep.name) is not dep:
                raise ValueError(f"{node.name!r} depends on {dep.name!r}, not in the graph")
        self.nodes[node.name] = node
        self.order = self._sort()
        return node

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
        """The names the GPU timer reports, one per node, in order."""
        return [n.name for n in self.order if n.TIMED]

    def evaluate(self, frame: Frame) -> None:
        for node in self.order:
            node.run(frame)

    def __repr__(self) -> str:
        return "Graph(" + " → ".join(n.name for n in self.order) + ")"


def graph_key(views: list[View]) -> tuple:
    """What selects the default graph: each view's scene, hands and
    through switches. Everything else about a view (its size, its
    flips, a presenter) is read when its nodes run."""
    return tuple((bool(v.switches.scene), bool(v.switches.hands), bool(v.switches.through))
                 for v in views)


def pipelines_of(switches: list[Switches]) -> list[int]:
    """The pipelines the switches can route to (`outputs.route`), in run
    order: SCENE for any view showing the scene; SCENE+HANDS for a view
    with the scene and the hands through; HANDS for one with the scene
    off and the hands through. Whether a hand shows, and whether an
    effect is on, decide per frame which of them run."""
    keys = []
    if any(sw.scene for sw in switches):
        keys.append(SCENE)
    if any(sw.scene and sw.hands and sw.through for sw in switches):
        keys.append(SCENE_HANDS)
    if any(not sw.scene and sw.hands and sw.through for sw in switches):
        keys.append(HANDS)
    return [k for k in PIPELINES if k in keys]


# the pipelines' node names, by key: the composite that lays the hands
# on before the chain, and the chain itself
COMPOSITE_NAMES = {SCENE_HANDS: "composite(scene+hands)", HANDS: "composite(hands)"}
FX_NAMES = {SCENE: "fx", SCENE_HANDS: "fx(scene+hands)", HANDS: "fx(hands)"}
PORTS = {SCENE: "scene", SCENE_HANDS: "scene+hands", HANDS: "hands"}


def default_graph(views: list[View]) -> Graph:
    """Today's frame as a graph, from the views' switches: the shape into
    the scene; the cover; the hands' layer while some view shows hands;
    the history; per reachable pipeline a composite (the hands onto the
    history, or onto the ground) and the chain; the capture after every
    pipeline; one output per view, after the capture."""
    switches = [v.switches for v in views]
    g = Graph(graph_key(views))
    shape = g.add(Shape("shape"))
    scene = g.add(Scene("scene", geometry=shape))
    cover = g.add(Cover("cover", scene=scene))
    hands = g.add(HandsLayer("hands")) if any(sw.hands for sw in switches) else None
    history = g.add(History("history", image=scene, cover=cover))
    ends: dict[int, Node] = {}
    # every pipeline end runs after the hands' layer: whether a hand shows
    # this frame decides which pipelines the views route to (A1)
    gate = (hands,) if hands is not None else ()
    for key in pipelines_of(switches):
        if key == SCENE:
            src = history
        elif key == SCENE_HANDS:
            src = g.add(Composite(COMPOSITE_NAMES[key], under=history, over=hands))
        else:
            src = g.add(Composite(COMPOSITE_NAMES[key], under=None, over=hands))
        ends[key] = g.add(Fx(FX_NAMES[key], key, after=gate, image=src))
    capture = g.add(Capture("capture", image=scene, after=tuple(ends[k] for k in PIPELINES
                                                                 if k in ends)))
    for i in range(len(views)):
        wired = {PORTS[k]: n for k, n in ends.items()}
        g.add(Output(f"output.{i + 1}", i, after=(capture,), layer=hands, **wired))
    return g
