"""The render graph (plan 26 A1, A3): the frame as nodes, evaluated in
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
  whatever holds them — the scene, the hands' layer, or both. The point
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

- **FX** (`Fx`): the effect chain (`fx.FxChain`), one node per pipeline,
  the effects' order inside it as today. Inactive, it passes its input
  through untouched.
- **History** (`History`, `Capture`): the look-back (`lookback.Lookback`)
  as two nodes, because its composite must read the ring before the
  frame's capture changes it: `history` lays the echoes and the dream
  over its input; `capture` puts its input — whatever it is wired to: the
  scene, or the scene with the hands' layer (A3) — into the ring after
  every composite of the frame has run.
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

Render stack (ARCHITECTURE §3): this module reads params through the
objects it is handed and never writes one; it imports moderngl and its
sibling render modules only, never params, routing, library, preset,
undo or control. Node methods are `run`, `paint`, `draw`, `image`,
`depth` — never `apply`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, ClassVar

import moderngl
import numpy as np

from .geometry import EYE_DISTANCE, EYE_FOV, EYE_NEAR, eye_matrix
from .outputs import HANDS, NAMES, PIPELINES, SCENE, SCENE_HANDS, Switches, View

# port types: a colour picture at the frame's size, a one-channel mask at
# the frame's size, or draw calls (a geometry, drawn by its scene or layer)
IMAGE, MASK, GEOMETRY = "image", "mask", "geometry"

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


@dataclass(frozen=True)
class Wiring:
    """The choices the default graph is built from besides the outputs'
    switches (plan 26 A3): where the hands are drawn, how their layer is
    laid on, what the history captures. The defaults are today's frame.
    The renderer holds one (`Renderer.wiring`); A4 reads it from a
    preset's `graph` section."""

    hands: str = "layer"
    blend: str = "over"
    history: str = "scene"

    def __post_init__(self) -> None:
        for name, value, allowed in (("hands", self.hands, HANDS_IN),
                                     ("blend", self.blend, BLENDS),
                                     ("history", self.history, HISTORY_OF)):
            if value not in allowed:
                raise ValueError(f"wiring {name} {value!r}: one of {', '.join(allowed)}")


@dataclass
class Frame:
    """One frame as the nodes see it: the renderer and what
    `Renderer._draw_frame` settled before evaluation (the frame's size
    under the cap, the first output's target to bind again after a
    failure, the chain's state), and what the nodes fill in as they run
    (the cover, the hands' layer, the readout, each pipeline's frame
    texture, the failures, `stats`, each node's per-frame `data`)."""

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
    surface written after. `prepare` makes the faces' picture while an
    effect is aimed at them (`Renderer._face_picture`, before the scene's
    target is bound); `draw` draws into whatever is bound — clearing it
    first when it is the scene's only geometry (`clear`), as it always
    did."""

    KIND = "geometry"
    OUTPUT = GEOMETRY
    TIMED = False

    def prepare(self, frame: Frame) -> None:
        frame.r._pic = frame.r._face_picture(frame.s, frame.t)

    def draw(self, frame: Frame, clear: bool = True) -> None:
        try:
            frame.r.draw_scene(frame.s, frame.w, frame.h, frame.dpr, frame.t, clear=clear)
        finally:
            frame.r._pic = None          # handed to that one scene pass only


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

    Its time is its own SYSTEM line while a scene draws it (`TIMED`), and
    the layer's otherwise. A draw that raises costs the scene nothing:
    the frame goes on without the hands and `Ghost.error` says why."""

    KIND = "geometry"
    OUTPUT = GEOMETRY
    SOLID = True

    def __init__(self, name: str, after: tuple[Node, ...] = (), **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.in_scene = False         # a Scene holds it: its draws there are its own line

    @property
    def TIMED(self) -> bool:     # the class attribute, per instance
        return self.in_scene

    def run(self, frame: Frame) -> None:
        w, h = frame.size
        s, r = frame.s, frame.r
        frame.data[self.name] = None
        try:
            frame.data[self.name] = r.ghost.settle(
                frame.t, max(w, 1) / max(h, 1), getattr(s, "eye_fov", None),
                getattr(s, "eye_distance", None))
        except Exception as e:  # noqa: BLE001 — a malformed skeleton costs the hands only
            r._hands_failed(e, frame.target, frame.vp)

    def now(self, frame: Frame):
        """This frame's settled (poses, view_proj, eye), or None."""
        return frame.data.get(self.name)

    def prepare(self, frame: Frame) -> None:
        """Nothing before the scene's target is bound."""

    def draw(self, frame: Frame) -> None:
        r = frame.r
        try:
            frame.stats["in_scene"] = bool(r.ghost.draw_solid(self.now(frame)))
        except Exception as e:  # noqa: BLE001 — the hands must not take the scene down
            if not r.ghost.error:
                r.ghost.error = f"ghost hands in the scene: {type(e).__name__}: {e}"[:160]
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

# the node kind (A4's graph JSON names it: {"kind": "cloud", "role": "scan"})
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
                buf.orphan(max(data.nbytes, 12))
                buf.write(np.ascontiguousarray(data, dtype=np.float32))
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
    texture is never bound while it is the target."""

    KIND = "scene"
    OUTPUT = IMAGE

    def __init__(self, name: str, geometries: tuple[Node, ...] | list[Node] = (),
                 after: tuple[Node, ...] = (), **inputs: Node | None):
        geoms = list(geometries)
        if "geometry" in inputs:
            geoms.insert(0, inputs.pop("geometry"))
        self.INPUTS = {_geometry_port(i): GEOMETRY for i in range(max(len(geoms), 1))}
        super().__init__(name, after, **{_geometry_port(i): g for i, g in enumerate(geoms)},
                         **inputs)
        for g in geoms:
            if g is not None and g.SOLID and hasattr(g, "in_scene"):
                g.in_scene = True

    def geometries(self) -> list[Node]:
        return [g for g in self.inputs.values() if g is not None]

    def run(self, frame: Frame) -> None:
        r, ctx = frame.r, frame.ctx
        r.scene.ensure(frame.size, frame.samples)
        for unit in range(4):
            r._blank.use(location=unit)
        geometries = self.geometries()
        solids = [g for g in geometries if g.SOLID]
        if not solids:                    # A2's scene pass, byte for byte
            with frame.timed(self.name):
                for g in geometries:
                    g.prepare(frame)
                r.scene.draw_fbo.use()
                ctx.viewport = (0, 0, *frame.size)
                for g in geometries:
                    g.draw(frame)
                r.scene.resolve()
            return
        rest = [g for g in geometries if not g.SOLID]
        with frame.timed(self.name):
            for g in rest:
                g.prepare(frame)
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
    hands and `Ghost.error` says why."""

    KIND = "layer"
    INPUTS: ClassVar[dict[str, str]] = {"geometry": GEOMETRY}
    OUTPUT = IMAGE

    def __init__(self, name: str, after: tuple[Node, ...] = (), readout: str = "through",
                 **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.readout = readout

    def run(self, frame: Frame) -> None:
        r, views = frame.r, frame.views
        frame.hands, frame.readout = False, None
        if self.readout == "always":
            split = True
        else:
            split = frame.fx_on and any(v.switches.hands and v.switches.through for v in views)
        geo = self.inputs["geometry"]
        try:
            with frame.timed(self.name):
                if geo is not None:
                    drew = r.ghost.layer(frame.size, frame.t, readout=split,
                                         now=geo.now(frame), settled=True)
                else:
                    drew = r.ghost.layer(frame.size, frame.t, readout=split)
            frame.hands = bool(drew)
        except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
            r._hands_failed(e, frame.target, frame.vp)
        frame.readout = r.ghost.readout if frame.hands else None
        frame.stats["layer"], frame.stats["readout"] = frame.hands, frame.readout is not None

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.r.ghost.tex if frame.hands else None

    def depth(self, frame: Frame) -> moderngl.Texture | None:
        return frame.r.ghost.depth if frame.hands else None

    def alpha(self, frame: Frame) -> float:
        return float(frame.r.ghost.state.alpha)

    def lay(self, frame: Frame, dst: moderngl.Framebuffer, rect: tuple, blend: str,
            opaque: bool, flip: tuple[bool, bool] = (False, False),
            scene_depth: moderngl.Texture | None = None) -> None:
        """Plain over is `Ghost.composite`'s blend, as it always was; add
        and depth-aware are `Renderer.lay`'s."""
        if blend == "over" or (blend == "depth" and scene_depth is None):
            frame.r.ghost.composite(dst, rect, opaque=opaque, flip=flip)
            return
        super().lay(frame, dst, rect, blend, opaque, flip, scene_depth)


class Readout(Node):
    """The readout alone (plan 26 A3): the guide and the tethers' labels
    of the hands its geometry settled, into `Ghost.readout`, for the
    outputs that show the hands — when the hands are drawn inside the
    scene and no hands' layer runs to draw it (`Ghost.layer(…,
    hands=False)`). Its own SYSTEM line."""

    KIND = "layer"
    INPUTS: ClassVar[dict[str, str]] = {"geometry": GEOMETRY}
    OUTPUT = IMAGE

    def run(self, frame: Frame) -> None:
        r, geo = frame.r, self.inputs["geometry"]
        frame.readout = None
        if geo is None:
            return
        try:
            with frame.timed(self.name):
                drew = r.ghost.layer(frame.size, frame.t, readout=True, now=geo.now(frame),
                                     settled=True, hands=False)
            frame.readout = r.ghost.readout if drew else None
        except Exception as e:  # noqa: BLE001 — the guide must not take the frame down
            r._hands_failed(e, frame.target, frame.vp)
        frame.stats["readout"] = frame.readout is not None

    def image(self, frame: Frame) -> moderngl.Texture | None:
        return frame.readout


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
        if frame.fx_on and not frame.stats["chain_runs"]:
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

    def __init__(self, name: str, after: tuple[Node, ...] = (), blend: str = "over",
                 **inputs: Node | None):
        if blend not in BLENDS:
            raise ValueError(f"composite {name!r}: blend {blend!r}, one of {', '.join(BLENDS)}")
        super().__init__(name, after, **inputs)
        self.blend = blend

    def paint(self, frame: Frame, dst: moderngl.Framebuffer) -> None:
        r, ctx, size = frame.r, frame.ctx, frame.size
        under = self.inputs["under"]
        if under is None:
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
            tex, fbo = frame.r._frame_target(self.name, frame.size)
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
    pipeline no view takes this frame does not run. A pipeline that
    raises marks its views (`View.error`, named after the pipeline) and
    they show their ground.

    A pipeline whose input lays a layer on before the effects (a
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
    def layer(self) -> Node | None:
        """The layer this pipeline lays on before the effects, if any."""
        src = self.inputs["image"]
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

    def __init__(self, name: str, index: int, after: tuple[Node, ...] = (),
                 blend: str = "over", **inputs: Node | None):
        super().__init__(name, after, **inputs)
        self.index = index            # the view it draws, in Frame.views
        self.blend = blend

    def settle(self, frame: Frame) -> tuple[Node | None, tuple[Node, str] | None]:
        """(the end it shows this frame or None for its ground, (the layer
        laid over after it, its blend) or None) — `outputs.route`'s table
        as wiring: a through end that is not bent stands down for its
        fallback and its layer goes over here."""
        key = self.name + "#settle"
        if key in frame.data:
            return frame.data[key]
        end = self.inputs["image"]
        over, blend = self.inputs["hands"], self.blend
        if isinstance(end, Fx) and not end.bent(frame):
            over, blend = end.layer, end.inputs["image"].blend
            end = end.fallback
        laid = (over, blend) if over is not None and over.image(frame) is not None else None
        frame.data[key] = got = (end, laid)
        return got

    def run(self, frame: Frame) -> None:
        r, v = frame.r, frame.views[self.index]
        # the readout goes on every output that shows the hands, over,
        # through or in the scene: in its own layer the guide is in none
        ro = frame.readout if self.inputs["readout"] is not None else None
        try:
            end, laid = self.settle(frame)
            if "routes" in frame.stats:          # what this output shows: (end, hands over)
                frame.stats["routes"][self.index] = (
                    end.key if end is not None else None, laid is not None)
            put = None
            if laid is not None and laid[1] != "over":
                over, blend = laid

                def put(tgt, rect, opaque, flip, over=over, blend=blend):
                    lay(frame, blend, over, self.inputs["depth"], tgt, rect, opaque, flip)
            with frame.timed(self.name):
                r._compose(v, end.key if end is not None else None, laid is not None,
                           frame.frames, frame.failed, frame.size, ro, lay=put,
                           blend=laid[1] if laid is not None else "over")
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

    def __init__(self, key: tuple = (), wiring: Wiring | None = None):
        self.key = key
        self.wiring = wiring if wiring is not None else Wiring()
        self.nodes: dict[str, Node] = {}
        self.order: list[Node] = []
        self.clouds: tuple[str, ...] = ()        # the cloud roles the default graph drew (A4b)

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

    @property
    def outputs(self) -> list[Output]:
        return [n for n in self.order if isinstance(n, Output)]

    def evaluate(self, frame: Frame) -> None:
        frame.graph = self
        for node in self.order:
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
                  clouds: tuple[str, ...] = ()) -> Graph:
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

    Plan 26 A4b: `clouds`, the roles of the listed `cloud` devices
    (`cloud_roles`), each a point-cloud geometry in the scene, solid,
    before the hands; none listed, the graph is the one above."""
    wiring = wiring if wiring is not None else Wiring()
    switches = [v.switches for v in views]
    in_scene = wiring.hands == "scene"
    depth_aware = wiring.blend == "depth"

    def layered(sw: Switches) -> bool:
        return bool(sw.hands) and (not in_scene or not sw.scene)

    want_layer = any(layered(sw) for sw in switches) or (
        wiring.history == "scene+hands" and not in_scene)
    g = Graph(graph_key(views), wiring)
    g.clouds = tuple(clouds)                       # plan 26 A4b: what it was built for
    points = cloud_nodes(g, g.clouds)
    shape = g.add(Shape("shape"))
    hands = g.add(Hands("ghost")) if (in_scene or want_layer) else None
    scene = g.add(Scene("scene", geometries=[*points, *([hands, shape] if in_scene else [shape])]))
    cover = g.add(Cover("cover", scene=scene))
    layer = (g.add(HandsLayer("hands", readout="always" if in_scene else "through",
                              geometry=hands)) if want_layer else None)
    readout = layer
    if in_scene and layer is None and any(sw.scene and sw.hands for sw in switches):
        readout = g.add(Readout("readout", geometry=hands))
    history = g.add(History("history", image=scene, cover=cover))
    depth = scene if depth_aware else None
    ends: dict[int, Fx] = {}
    # every pipeline end runs after the hands' layer: whether a hand shows
    # this frame decides which pipelines the views take
    gate = (layer,) if layer is not None else ()
    for key in pipelines_of(switches, in_scene):
        if key == SCENE:
            ends[key] = g.add(Fx(FX_NAMES[key], key, after=gate, image=history))
            continue
        src = g.add(Composite(COMPOSITE_NAMES[key], blend=wiring.blend, depth=depth,
                              under=history if key == SCENE_HANDS else None, over=layer))
        ends[key] = g.add(Fx(FX_NAMES[key], key, after=gate, image=src,
                             fallback=ends.get(SCENE) if key == SCENE_HANDS else None))
    held = scene
    if wiring.history == "scene+hands" and layer is not None and not in_scene:
        held = g.add(Composite(HISTORY_COMPOSITE, blend=wiring.blend, depth=depth,
                               under=scene, over=layer))
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
        g.add(Output(f"output.{i + 1}", i, after=(capture,), blend=wiring.blend, image=image,
                     hands=over, readout=readout if sw.hands else None,
                     depth=depth if layered(sw) else None))
    return g
