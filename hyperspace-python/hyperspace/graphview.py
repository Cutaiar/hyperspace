"""The GRAPH page's model (plan 28 N2): both graphs as one set of nodes,
ports and cables, built from the live objects and drawn by ui_graph.py.

Nothing here draws and nothing here edits. `build` reads the binding
table (`routing.Bindings`: the routes, the desk / pad / key rows, the
macros, the modifiers), the registry (every param a cable can reach), the
Router (the source lanes' names and readings, the LFOs, the loops `patch`
keeps off), the device registry (`devices.DeviceRegistry`: one node per
listed device, its ports its `Device.sources` in their port groups) and
the render graph the renderer last built (`graph.Graph`: its nodes, their
typed ports and the edges between them), and returns a `View`. The page
rebuilds it whenever any of those changes (`key`), and `refresh` moves
only the readings each frame. One table, two views: the ROUTING page and
this one read the same rows, so an edit on either is on both next frame.

**Nodes** (`VNode.kind`, the design's §3):

- ``device`` — one per listed device, by role (``device:<role>``), grey
  while it is not connected (its cables dormant); ``source`` — a scheme
  no listed device publishes (the keys, a role this rig lacks), so every
  row's source has a port; ``analyzer`` — one port per band lane;
- ``lfo`` — each LFO (``lfo.<n>``), its knobs (`lfo.<n>.*`) as input
  ports and its lane as the output; ``modifier`` (``mod.<n>``, plan 28
  N1) — its inputs, its params, its lane; ``macro`` (``macro.<n>``) — a
  bus: its knob in, one output, its subscribers as cables;
- ``render`` / ``output`` — the render graph's nodes (``render:<name>``),
  with their image / geometry / mask ports and, as input ports, the
  params of the render node that owns them (`OWNERS`, the one table);
  ``render:eye`` — the shared camera (`camera.*`, `eye.*`), which draws
  through every geometry and so has no image port;
- ``group`` — a node per group of params no render node owns
  (``group:tempo``, ``group:master`` …).

**Ports** (`VPort`): a source port has one pin (``out:<address>``); a
param port has a ``base:<pid>`` stub (the setters: desk, pad and key
rows, a macro's base subscriber — many, last touch wins) and a
``mod:<pid>`` stub (the one performer under the referee), and a
``depth:<pid>`` stub while a route lands on it (a macro's depth
subscriber scales that route); a modifier's inputs are ``in:<id>.<k>``,
a macro's output ``bus:<id>``, a render node's ports ``rin:<node>/<port>``
and ``rout:<node>``. Pins are strings; the page maps them to the widget's
integer ids.

**Cables** (`VCable.kind`): ``route`` (one per performer row, `ref` the
`Binding`, into ``mod``), ``setter`` (a desk / pad / key row, into
``base``), ``sub`` (a macro subscriber, into ``base`` or ``depth``,
`ref` (macro id, `Sub`)), ``input`` (a modifier's input), ``render`` (a
render-graph edge, `ref` (source node, node, port)). A route's `scale`
and its `when` gate are said on the cable (`label`), not drawn: a param
has no output pin. Sink rows are not drawn in this plan.

**Layout** (`auto_layout`, `home`): positions live in two maps — the
preset's (`preset.LAYOUT_KEY`) for the nodes a preset holds (modifiers,
macros, the render nodes and their params, a performance group's node)
and the show's for the rig's (devices, sources, the analyzer, LFOs, the
outputs, a session group's node). An unplaced node gets a column by kind,
left to right.

Imports `routing`, `params`, `graph`, `patch`, `modifiers` — the device
registry is handed in and read through `devices.Device`'s protocol
(`role`, `kind`, `status`, `sources`, `schemes`), so nothing of
`devices.py` is imported — and never imgui (tests/test_graphview.py
holds it)."""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from . import graph as rgraph
from . import modifiers as modmod
from . import patch as patchmod
from .params import PERFORMANCE_GROUPS, Kind, Param, Registry
from .routing import MOD_OPS, Bindings, Router, is_macro

# signal kinds a port and a cable carry (decision 10: values and triggers;
# plan 26's image, geometry and mask)
VALUE, TRIGGER = "value", "trigger"
IMAGE, GEOMETRY, MASK = rgraph.IMAGE, rgraph.GEOMETRY, rgraph.MASK
TYPES = (VALUE, TRIGGER, IMAGE, GEOMETRY, MASK)

KINDS = ("device", "source", "analyzer", "lfo", "modifier", "macro", "group", "render",
         "output")
CABLE_KINDS = ("route", "setter", "sub", "input", "render")
IN, OUT = "in", "out"
BASE, MOD, DEPTH = "base", "mod", "depth"
# which layout map a node's position is saved in
PRESET, SESSION = "preset", "session"

ANALYZER = "analyzer"
EYE = "eye"                  # the shared camera's node: `render:eye`
MISSING = "missing"          # a group node for the cables' targets no registry holds
# the LFO's knobs, in the order its node lists them (patch.py's ports)
LFO_KNOBS = patchmod.LFO_KNOBS
# setter ops that move a param in steps or fire it: a trigger cable
TRIGGER_OPS = ("fire", "toggle", "step", "set", "momentary", "hold")


# ---------------------------------------------------------------- the model

@dataclass
class VPort:
    """One port. `pins` are its connection points: one for a source, a
    modifier input or a render port; a param port's `base` and `mod`
    stubs (and `depth` while a route lands on it). `param` is the param
    id for a param port; `addr` the source address a source port reads;
    `live` the reading (a source's 0–1 lane, a param's effective norm),
    None while it is not live."""

    id: str
    name: str
    direction: str
    type: str = VALUE
    group: str = ""
    patched: bool = False
    live: float | None = None
    pins: tuple[str, ...] = ()
    param: str | None = None
    addr: str | None = None

    def __post_init__(self):
        if not self.pins:
            self.pins = (self.id,)


@dataclass
class VNode:
    """One node: `id` (its layout key), `kind` (KINDS), `label`, `ports`
    in drawing order, `grey` (a device that is not connected, a source no
    device publishes), `status` (the device's, said on hover), `ref` the
    live object it stands for (the device, the render node, the
    `Modifier`), `column` (auto_layout's)."""

    id: str
    kind: str
    label: str
    ports: list[VPort] = field(default_factory=list)
    grey: bool = False
    status: str = ""
    ref: Any = None
    column: int = 0

    def port(self, pid: str) -> VPort | None:
        return next((p for p in self.ports if p.id == pid), None)


@dataclass
class VCable:
    """One cable from an output pin to an input pin. `ref` is what it
    stands for (the `Binding`, (macro id, `Sub`), (`Modifier`, input
    index), (source node, node, port) for a render edge); `off` a cable
    that cannot act whatever its source reads (a disabled row, a target no
    registry holds or no performer may drive, a cable `Router.patch` keeps
    off to break a loop, a depth subscriber on a route that is not there);
    `dormant` that, or a source not live this frame. `depth` the route's
    effective depth (`value × scale × Π depth subs`); `label` what the
    hover says beside the reading."""

    id: str
    src_port: str
    dst_port: str
    type: str = VALUE
    live: float | None = None
    dormant: bool = False
    ref: Any = None
    kind: str = "route"
    off: bool = False
    depth: float | None = None
    label: str = ""
    addr: str | None = None


@dataclass
class View:
    nodes: list[VNode] = field(default_factory=list)
    cables: list[VCable] = field(default_factory=list)
    spec: Any = None                 # the preset's graph spec (graph.GraphSpec | None)
    pins: dict[str, tuple[str, str]] = field(default_factory=dict)   # pin → (node, port)

    def node(self, nid: str) -> VNode | None:
        return next((n for n in self.nodes if n.id == nid), None)

    def owner(self, pin: str) -> tuple[VNode, VPort] | None:
        """The node and port a pin belongs to."""
        hit = self.pins.get(pin)
        if hit is None:
            return None
        n = self.node(hit[0])
        return None if n is None else (n, n.port(hit[1]))

    def cables_of(self, nid: str) -> list[VCable]:
        """Every cable into or out of node `nid`."""
        pins = {p for n in self.nodes if n.id == nid for port in n.ports for p in port.pins}
        return [c for c in self.cables if c.src_port in pins or c.dst_port in pins]


# ---------------------------------------------------------------- params → render nodes

def _first_segment_number(pid: str, head: str) -> int:
    """The instance number in `head.<n>.key` (ENGINEERING §2's naming
    rule), 1 for `head.key`."""
    rest = pid[len(head) + 1:]
    seg = rest.partition(".")[0]
    return int(seg) if seg.isdigit() and "." in rest else 1


def _hands_owner(pid: str, ctx: _Ctx) -> str | None:
    n = _first_segment_number(pid, "ghost")
    return rgraph.hands_name(n)


def _effect_owner(pid: str, ctx: _Ctx) -> str | None:
    # `fx.<effect>.<key>`: the effect's node in the scene's pipeline (named
    # by the effect), else the first node of that effect; `fx.on`,
    # `fx.mix`, `fx.select` the scene pipeline's end
    for e in ctx.effects:
        if pid.startswith(f"fx.{e}."):
            return ctx.effect_node.get(e)
    return rgraph.FX_NAMES[rgraph.SCENE]


def _output_owner(pid: str, ctx: _Ctx) -> str | None:
    seg = pid.split(".")
    if len(seg) >= 3 and seg[0] == "output" and seg[1].isdigit():
        return f"output.{seg[1]}"
    return None


def _cloud_owner(pid: str, ctx: _Ctx) -> str | None:
    return ctx.first_cloud


# a param's group → the render node that owns it: a node name, or a rule
# over the id (an instance's number, an effect's name). A name the render
# graph does not hold this frame (no output shows the hands, no scene
# pipeline) leaves the param to its group's node. `EYE` is the shared
# camera's node, which the render graph has no node for. A group not
# listed here has no render node: a node per group (`group:<group>`)
OWNERS: dict[str, str | Callable[[str, _Ctx], str | None]] = {
    "view": "shape",
    "rot": "shape",
    "pattern": "shape",
    "ghost": _hands_owner,
    "cloud": _cloud_owner,
    "dream": "history",
    "fx": _effect_owner,
    "camera": EYE,
    "eye": EYE,
    "output": _output_owner,
}


@dataclass
class _Ctx:
    names: set[str] = field(default_factory=set)          # the render graph's node names
    effects: list[str] = field(default_factory=list)      # effect instances, longest first
    effect_node: dict[str, str] = field(default_factory=dict)
    first_cloud: str | None = None


def render_owner(p: Param, ctx: _Ctx) -> str | None:
    """The render node (`render:<name>`, or `render:eye`) that owns param
    `p`, or None: no render node does (or not in this graph)."""
    rule = OWNERS.get(p.group)
    if rule is None:
        return None
    name = rule(p.id, ctx) if callable(rule) else rule
    if name == EYE:
        return f"render:{EYE}"
    if name is None or name not in ctx.names:
        return None
    return f"render:{name}"


# ---------------------------------------------------------------- reading

def reading(router: Router | None, addr: str, lanes=None) -> float | None:
    """A source address's 0–1 reading this frame, None while not live —
    the analyzer's lanes from `lanes` (already normalised), anything else
    from the Router's fed vectors (`Router.feeds`)."""
    if router is None or not addr:
        return None
    scheme, i = router.lane(addr)
    vec = lanes if scheme == "lane" else router.feeds.get(scheme)
    if vec is None or not 0 <= i < len(vec):
        return None
    try:
        u = float(vec[i])
    except (TypeError, ValueError):
        return None
    return None if math.isnan(u) else u


def _norm(p: Param | None) -> float | None:
    if p is None:
        return None
    try:
        u = float(p.eff_norm)
    except Exception:  # noqa: BLE001 — a param that cannot say its value reads as not live
        return None
    return u if math.isfinite(u) else None


def _value(p: Param | None, default: float = 1.0) -> float:
    if p is None:
        return default
    try:
        v = float(p.value)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


# ---------------------------------------------------------------- build

def _lfo_count(router: Router | None, reg: Registry) -> int:
    lfos = getattr(router, "__dict__", {}).get("lfos") if router is not None else None
    if lfos is not None:
        try:
            return len(lfos)
        except TypeError:
            pass
    n = 0
    while f"lfo.{n + 1}.depth" in reg:
        n += 1
    return n


def _lane_key(router: Router | None, addr: str) -> tuple | str:
    """What two addresses naming one lane share (`hand:7` and
    `hand:right.y`): (scheme, index), else the address itself."""
    if router is None:
        return addr
    scheme, i = router.lane(addr)
    return (scheme, i) if i >= 0 else addr


def _modifiers(table: Bindings) -> list:
    mods = getattr(table, "modifiers", None) or ()
    return list(mods.values() if isinstance(mods, dict) else mods)


def _device_schemes(devices) -> tuple[dict[str, Any], str | None]:
    """scheme → the device whose rows / lanes it is, and the MIDI role
    whose rows are unqualified."""
    out: dict[str, Any] = {}
    midi_first = None
    if devices is None:
        return out, None
    roles = getattr(devices, "midi_roles", None)
    try:
        midi = list(roles()) if roles is not None else []
    except Exception:  # noqa: BLE001
        midi = []
    midi_first = midi[0] if midi else None
    for d in devices:
        if getattr(d, "kind", "") == "midi":
            continue
        for s in (*getattr(d, "schemes", ()), *getattr(d, "feeds", ())):
            out.setdefault(s, d)
    return out, midi_first


def device_node(d) -> tuple[VNode, list]:
    """One listed device as a node (``device:<role>``) and the source ports
    it draws (`Device.sources`, value and trigger lanes; a point cloud is
    no lane, plan 27 B4), in their port groups. Grey while not connected.
    The one place a device becomes a node: plan 28 N5 makes a device with
    `layers` one node per layer here."""
    role = str(getattr(d, "role", "") or "")
    try:
        status = str(d.status)
    except Exception as e:  # noqa: BLE001 — a status line never takes the page down
        status = f"error: {e}"
    node = VNode(f"device:{role}", "device", role, grey=status != "connected",
                 status=f"{getattr(d, 'kind', '')} · {status}", ref=d)
    try:
        ports = [p for p in d.sources if p.kind in (VALUE, TRIGGER)]
    except Exception:  # noqa: BLE001
        ports = []
    return node, ports


def _port_type(kind: str) -> str:
    return TRIGGER if kind == TRIGGER else VALUE


def build(table: Bindings, reg: Registry, router: Router | None = None, devices=None,
          render_graph: rgraph.Graph | None = None, spec=None, *, lanes=None,
          bands: Iterable[str] | None = None) -> View:
    """The view of `table`, `reg`, `router`, the device registry `devices`
    and the render graph `render_graph` (the renderer's last), with the
    preset's graph `spec` kept on the view. `lanes` are the analyzer's
    lanes this frame, normalised (None: not live); `bands` their names
    (else the Router's published ``lane`` labels)."""
    view = View(spec=spec)
    nodes: dict[str, VNode] = {}
    src_pins: dict[tuple | str, str] = {}       # lane key → pin
    pin_type: dict[str, str] = {}

    def add_node(n: VNode) -> VNode:
        nodes[n.id] = n
        return n

    def add_port(n: VNode, port: VPort) -> VPort:
        n.ports.append(port)
        for pin in port.pins:
            view.pins[pin] = (n.id, port.id)
            pin_type[pin] = port.type
        return port

    def add_source(n: VNode, addr: str, name: str, kind: str = VALUE,
                   group: str = "") -> str:
        key = _lane_key(router, addr)
        if key in src_pins:
            return src_pins[key]
        pin = f"out:{addr}"
        add_port(n, VPort(pin, name, OUT, _port_type(kind), group, addr=addr))
        src_pins[key] = pin
        return pin

    # ---- the sources: devices, the analyzer, LFOs, modifiers ----
    by_scheme, midi_first = _device_schemes(devices)
    for d in (devices or ()):
        node, ports = device_node(d)
        n = add_node(node)
        for p in ports:
            add_source(n, p.address, p.label, p.kind, p.group)

    labels = getattr(router, "labels", {}) if router is not None else {}
    band_names = list(bands) if bands is not None else list(labels.get("lane") or [])
    analyzer = add_node(VNode(ANALYZER, "analyzer", "analyzer"))
    for i, name in enumerate(band_names):
        add_source(analyzer, f"lane:{i}", f"{i} {name}", group="bands")

    lfo_names = list(labels.get("lfo") or [])
    for i in range(_lfo_count(router, reg)):
        k = i + 1
        n = add_node(VNode(f"lfo.{k}", "lfo", lfo_names[i] if i < len(lfo_names) else f"LFO {k}"))
        addr = router.address("lfo", i) if router is not None else f"lfo:{i}"
        add_source(n, addr, "out")

    for m in _modifiers(table):
        n = add_node(VNode(m.id, "modifier", f"{m.id} {m.kind}", ref=m))
        for k in range(modmod.INPUTS.get(m.kind, len(m.inputs))):
            add_port(n, VPort(f"in:{m.id}.{k}", f"in {k + 1}" if modmod.INPUTS.get(
                m.kind, 1) > 1 else "in", IN))
        add_source(n, m.address, "out", m.out)

    def source_pin(addr: str) -> str:
        """The pin a row's source address leaves from: a published port's,
        else a port added for it on the node its scheme belongs to (a lost
        device publishes no ports; the keys are no device)."""
        key = _lane_key(router, addr)
        if key in src_pins:
            return src_pins[key]
        scheme = addr.partition(":")[0]
        base, at, role = scheme.partition("@")
        owner = None
        if base == "lane":
            owner = analyzer
        elif base == "lfo":
            scheme_i = router.lane(addr)[1] if router is not None else -1
            owner = nodes.get(f"lfo.{scheme_i + 1}") if scheme_i >= 0 else None
        elif base == modmod.SCHEME:
            owner = nodes.get(modmod.id_of(addr) or "")
        if owner is None and at and role:
            owner = nodes.get(f"device:{role}")
        if owner is None:
            d = by_scheme.get(scheme) or by_scheme.get(base)
            if d is None and base in ("cc", "note", "pitch") and midi_first:
                owner = nodes.get(f"device:{midi_first}")
            elif d is not None:
                owner = nodes.get(f"device:{d.role}")
        if owner is None:
            nid = f"source:{scheme}"
            owner = nodes.get(nid) or add_node(VNode(nid, "source", scheme, grey=True,
                                                     status="no device publishes it"))
        return add_source(owner, addr, addr.partition(":")[2] or addr)

    # ---- the render graph's nodes ----
    ctx = _Ctx()
    rnodes = list(render_graph.order) if render_graph is not None else []
    ctx.names = {r.name for r in rnodes}
    effects: dict[str, str] = {}
    for r in rnodes:
        if isinstance(r, rgraph.Effect):
            # the scene pipeline's node is named by the effect; else the first
            if r.name == r.effect or r.effect not in effects:
                effects[r.effect] = r.name
        elif isinstance(r, rgraph.PointCloud) and ctx.first_cloud is None:
            ctx.first_cloud = r.name
    ctx.effect_node = effects
    ctx.effects = sorted(effects, key=len, reverse=True)   # `acid.2` before `acid`
    for r in rnodes:
        kind = "output" if isinstance(r, rgraph.Output) else "render"
        n = add_node(VNode(f"render:{r.name}", kind, r.name, ref=r))
        for port, typ in r.INPUTS.items():
            add_port(n, VPort(f"rin:{r.name}/{port}", port, IN, typ))
        if r.OUTPUT is not None:
            add_port(n, VPort(f"rout:{r.name}", r.OUTPUT, OUT, r.OUTPUT))

    # ---- the params: every one a cable can reach ----
    rows = list(table.bindings)
    routes = [b for b in rows if b.op in MOD_OPS]
    setters = [b for b in rows if b.op not in MOD_OPS and not b.is_sink]
    macros = dict(getattr(table, "macros", {}) or {})
    targets: list[str] = []
    seen_t: set[str] = set()

    def want(pid: str | None) -> None:
        if pid and pid not in seen_t:
            seen_t.add(pid)
            targets.append(pid)

    for p in reg:
        if p.modulatable and not p.alias:
            want(p.id)
    for b in (*routes, *setters):
        want(b.target)
    for mid, m in macros.items():
        if m.subs or m.label:
            want(mid)
        for s in m.subs:
            want(s.base if s.depth is None else s.depth[1])
    depth_of = {b.target for b in routes}
    depth_of |= {s.depth[1] for m in macros.values() for s in m.subs if s.depth is not None}

    def param_port(pid: str, p: Param | None) -> VPort:
        typ = TRIGGER if p is not None and p.kind is Kind.TRIGGER else VALUE
        pins = [f"{BASE}:{pid}", f"{MOD}:{pid}"]
        if pid in depth_of:
            pins.append(f"{DEPTH}:{pid}")
        name = p.label if p is not None and p.label else pid
        return VPort(f"param:{pid}", name, IN, typ, group=_sub_group(pid, p),
                     pins=tuple(pins), param=pid, live=_norm(p))

    for pid in targets:
        p = reg.get(pid)
        if p is None:
            nid = f"group:{MISSING}"
            owner = nodes.get(nid) or add_node(VNode(nid, "group", "missing params", grey=True,
                                                     status="ids no param has"))
        elif p.group == "lfo" and pid.startswith("lfo.") and pid.split(".")[1].isdigit():
            owner = nodes.get(f"lfo.{pid.split('.')[1]}") or _group_node(nodes, p.group, add_node)
        elif p.group == modmod.GROUP:
            mid = ".".join(pid.split(".")[:2])
            owner = nodes.get(mid) or _group_node(nodes, p.group, add_node)
        elif is_macro(pid):
            owner = nodes.get(pid)
            if owner is None:
                m = macros.get(pid)
                owner = add_node(VNode(pid, "macro", (m.label if m and m.label else pid),
                                       ref=m))
                add_port(owner, VPort(f"bus:{pid}", "out", OUT, VALUE, param=pid,
                                      live=_norm(p)))
        else:
            rid = render_owner(p, ctx)
            if rid == f"render:{EYE}" and rid not in nodes:
                add_node(VNode(rid, "render", "eye"))
            owner = nodes.get(rid) if rid is not None else None
            if owner is None:
                owner = _group_node(nodes, p.group or "misc", add_node)
        add_port(owner, param_port(pid, p))
    # a macro's knob port sits above its bus output
    for n in nodes.values():
        if n.kind == "macro":
            n.ports.sort(key=lambda q: q.direction == OUT)

    # ---- the cables ----
    cut = set(getattr(router, "patch_cut", ()) or ()) if router is not None else set()
    ids: dict[str, int] = {}

    def cable_id(base: str) -> str:
        k = ids.get(base, 0)
        ids[base] = k + 1
        return base if k == 0 else f"{base}#{k + 1}"

    for b in routes:
        src = source_pin(b.source)
        dst = f"{MOD}:{b.target}"
        p = reg.get(b.target)
        off = (not b.enabled or p is None or not p.modulatable
               or (b.source, b.target) in cut)
        depth, said = route_said(b, table, reg, (b.source, b.target) in cut)
        view.cables.append(VCable(cable_id(f"route:{b.source}>{b.target}"), src, dst,
                                  pin_type.get(src, VALUE), ref=b, kind="route", off=off,
                                  depth=depth, label=said, addr=b.source))
    for b in setters:
        src = source_pin(b.source)
        dst = f"{BASE}:{b.target}"
        p = reg.get(b.target)
        typ = TRIGGER if (b.op in TRIGGER_OPS or pin_type.get(src) == TRIGGER) else VALUE
        layer = f"  {b.layer} layer" if b.layer else ""
        view.cables.append(VCable(cable_id(f"set:{b.source}>{b.target}"), src, dst, typ,
                                  ref=b, kind="setter", off=not b.enabled or p is None,
                                  label=f"{b.op}{layer}", addr=b.source))
    keyed = {(b.source, b.target) for b in routes}
    for mid, m in sorted(macros.items(), key=lambda kv: _macro_n(kv[0])):
        src = f"bus:{mid}"
        if src not in view.pins:
            continue
        for s in m.subs:
            if s.depth is None:
                dst, off = f"{BASE}:{s.base}", reg.get(s.base or "") is None
            else:
                dst, off = f"{DEPTH}:{s.depth[1]}", s.depth not in keyed
            view.cables.append(VCable(cable_id(f"sub:{mid}>{dst}"), src, dst, VALUE,
                                      ref=(mid, s), kind="sub", off=off, label=sub_said(s)))
    for m in _modifiers(table):
        for k, addr in enumerate(m.inputs):
            if not addr:
                continue
            src = source_pin(addr)
            dst = f"in:{m.id}.{k}"
            if dst not in view.pins:
                continue
            view.cables.append(VCable(cable_id(f"in:{addr}>{m.id}.{k}"), src, dst,
                                      pin_type.get(src, VALUE), ref=(m, k), kind="input",
                                      off=(addr, m.address) in cut, addr=addr))
    for r in rnodes:
        for port, src in r.inputs.items():
            if src is None:
                continue
            view.cables.append(VCable(f"wire:{src.name}>{r.name}/{port}", f"rout:{src.name}",
                                      f"rin:{r.name}/{port}", r.INPUTS[port],
                                      ref=(src, r, port), kind="render"))

    # ---- what is patched; the nodes in column order ----
    hit = {c.src_port for c in view.cables} | {c.dst_port for c in view.cables}
    for n in nodes.values():
        for port in n.ports:
            port.patched = any(pin in hit for pin in port.pins)
    view.nodes = list(nodes.values())
    _columns(view, render_graph)
    refresh(view, reg, router, lanes)
    return view


def route_said(b, table, reg: Registry, cut: bool = False) -> tuple[float, str]:
    """A route's effective depth — `value × scale × Π depth subscribers`,
    the arithmetic `Router.modulate` runs — and the words its hover says:
    the depth, the op, what scales it, its gate, a loop's cut."""
    subs = list(table.depth_subs(b)) if hasattr(table, "depth_subs") else []
    depth = float(b.value)
    said = [f"depth {b.value:+.2f}", b.op]
    if b.scale is not None:
        depth *= _value(reg.get(b.scale))
        said.append(f"× {b.scale}")
    for mid, s in subs:
        mp = reg.get(mid)
        depth *= s.at(float(mp.base)) if mp is not None else 1.0
        said.append(f"× {mid}")
    if b.when is not None:
        said.append(f"while {b.when}")
    if cut:
        said.append("off: a loop needs a delay")
    return depth, "  ".join(said)


def sub_said(s) -> str:
    """A macro subscriber's hover words: what it sets and over what span."""
    if s.depth is None:
        return f"base {s.lo:.2f}…{s.hi:.2f}"
    return f"depth of {s.depth[0]} × {s.lo:.2f}…{s.hi:.2f}"


def _macro_n(mid: str) -> int:
    tail = mid.rpartition(".")[2]
    return int(tail) if tail.isdigit() else 0


def _sub_group(pid: str, p: Param | None) -> str:
    """A param port's group on its node — what folds: its param group's
    next segment (`fx.acid.*` all one; `view.*` by its group), so a big
    node lists its params in runs."""
    if p is None:
        return ""
    if p.group in ("fx", "ghost", "output"):
        seg = pid.split(".")
        return ".".join(seg[:2]) if len(seg) > 2 else p.group
    return p.group


def _group_node(nodes: dict[str, VNode], group: str, add_node) -> VNode:
    nid = f"group:{group}"
    return nodes.get(nid) or add_node(VNode(nid, "group", group))


def refresh(view: View, reg: Registry, router: Router | None, lanes=None) -> None:
    """This frame's readings on an already built view: each source port's
    and each cable's reading, each param port's effective value, and which
    cables are dormant (`off`, or a source not live), and each route's
    effective depth and words (a macro's depth subscriber turning, a
    depth dragged on ROUTING: `key` leaves the values out, so neither
    rebuilds the view). Cheap: no structure changes."""
    table = getattr(router, "table", None) if router is not None else None
    cut = set(getattr(router, "patch_cut", ()) or ()) if router is not None else set()
    for n in view.nodes:
        for port in n.ports:
            if port.addr is not None:
                port.live = reading(router, port.addr, lanes)
            elif port.param is not None:
                port.live = _norm(reg.get(port.param))
    for c in view.cables:
        if c.kind == "render":
            continue
        if c.addr is not None:
            c.live = reading(router, c.addr, lanes)
        elif c.kind == "sub":
            c.live = _norm(reg.get(c.ref[0]))
            c.label = sub_said(c.ref[1])
        if c.kind == "route" and table is not None:
            b = c.ref
            c.depth, c.label = route_said(b, table, reg, (b.source, b.target) in cut)
        grey = False
        hit = view.owner(c.src_port)
        if hit is not None and hit[0].grey:
            grey = True
        c.dormant = c.off or grey or (c.kind != "sub" and c.live is None)


def key(table: Bindings, reg: Registry, router: Router | None, devices,
        render_graph, spec) -> tuple:
    """What `build` is made of, cheaply compared each frame: the rows (by
    identity and the fields that make cables), the macros' and the
    modifiers' serials, the registry's add / remove serial, each device's
    status and port count, the render graph and the spec. The page builds
    a new view only when this moves."""
    rows = tuple((id(b), b.source, b.target, b.op, b.enabled, b.scale, b.when)
                 for b in table.bindings)          # not `value`: `refresh` follows a depth
    subs = tuple((mid, len(m.subs), m.label) for mid, m in
                 (getattr(table, "macros", {}) or {}).items())
    devs: tuple = ()
    if devices is not None:
        out = []
        for d in devices:
            try:
                out.append((getattr(d, "role", ""), d.status, len(d.sources)))
            except Exception:  # noqa: BLE001
                out.append((getattr(d, "role", ""), "error", 0))
        devs = tuple(out)
    labels = getattr(router, "labels", {}) if router is not None else {}
    return (id(table), rows, getattr(table, "macros_serial", 0), subs,
            getattr(table, "modifiers_serial", 0), getattr(reg, "serial", len(reg)),
            devs, id(render_graph), id(spec), len(labels.get("lane") or ()),
            tuple(labels.get("lfo") or ()),
            frozenset(getattr(router, "patch_cut", ()) or ()) if router is not None else ())


# ---------------------------------------------------------------- layout

# the columns, left to right (the design: devices → LFOs, modifiers and
# macros → render nodes → outputs); the render nodes spread over as many
# columns as the render graph is deep, so its cables run left to right
COLUMN = {"device": 0, "source": 0, "analyzer": 0, "lfo": 1, "modifier": 2, "macro": 3,
          "group": 4, "render": 5}
COL_W = 260.0          # canvas units between two columns
ROW_H = 22.0           # one port line
HEAD_H = 34.0          # a node's title and padding
GAP = 28.0             # between two nodes of a column


def _columns(view: View, render_graph) -> None:
    depth: dict[str, int] = {}
    for r in (render_graph.order if render_graph is not None else ()):
        ins = [depth[d.name] + 1 for d in r.inputs.values() if d is not None and d.name in depth]
        depth[r.name] = max(ins, default=0)
    last = COLUMN["render"] + max(depth.values(), default=0) + 1
    for n in view.nodes:
        if n.kind == "output":
            n.column = last
        elif n.kind == "render":
            n.column = COLUMN["render"] + depth.get(n.label, 0)
        else:
            n.column = COLUMN.get(n.kind, COLUMN["group"])


def visible(n: VNode, full: bool, folds=frozenset()) -> list[VPort]:
    """The ports node `n` draws: a patched port and a render port always;
    the rest only while the node is expanded (`full`) and its group is not
    folded (`(node id, group)` in `folds`) — so no cable ever ends on a
    pin that is not drawn."""
    return [p for p in n.ports
            if p.patched or (p.param is None and p.addr is None)
            or (full and (n.id, p.group) not in folds)]


def grouped(n: VNode, full: bool) -> bool:
    """Does node `n` draw a header line per port group (expanded, more than one)?"""
    return full and len({p.group for p in n.ports}) > 1


def height(n: VNode, full: bool = False, folds=frozenset()) -> float:
    """A node's height as auto_layout stacks it: its title, the ports it
    shows (`visible`) and, expanded, a line per port group."""
    rows = len(visible(n, full, folds))
    if grouped(n, full):
        rows += len({p.group for p in n.ports})
    return HEAD_H + ROW_H * rows


def auto_layout(view: View, placed: Mapping[str, Any] | None = None,
                expanded: Callable[[str], bool] | None = None,
                folds=frozenset()) -> dict[str, tuple[float, float]]:
    """A position for every node `placed` does not hold: its column's x by
    kind (`COLUMN`; the render nodes by their depth in the render graph,
    the outputs last), stacked down the column in view order. The nodes
    already placed keep their positions and take no room here (a tidy
    passes none). `expanded(node id)` says which nodes show every port
    (default none) and `folds` which of their groups are folded, so an
    expanded node pushes the column under it down instead of overlapping."""
    placed = placed or {}
    tops: dict[int, float] = {}
    out: dict[str, tuple[float, float]] = {}
    for n in view.nodes:
        if n.id in placed:
            continue
        y = tops.get(n.column, 0.0)
        out[n.id] = (n.column * COL_W, y)
        full = bool(expanded(n.id)) if expanded is not None else False
        tops[n.column] = y + height(n, full, folds) + GAP
    return out


def home(n: VNode) -> str:
    """Which layout map holds node `n`'s position: the preset's for what
    a preset holds (modifiers, macros, the render nodes, a performance
    group's node), the show's for the rig (devices, sources, the
    analyzer, LFOs, the outputs, a session group's node)."""
    if n.kind in ("modifier", "macro", "render"):
        return PRESET
    if n.kind == "group":
        group = n.id.partition(":")[2]
        return PRESET if group in PERFORMANCE_GROUPS else SESSION
    return SESSION


def split(view: View, positions: Mapping[str, Any]) -> tuple[dict, dict]:
    """`positions` (node id → (x, y)) as the preset's map and the show's,
    by each node's `home`; ids no node of the view has are left out."""
    pre: dict[str, list[float]] = {}
    ses: dict[str, list[float]] = {}
    for n in view.nodes:
        xy = positions.get(n.id)
        if xy is None:
            continue
        (pre if home(n) == PRESET else ses)[n.id] = [round(float(xy[0])), round(float(xy[1]))]
    return pre, ses


# ---------------------------------------------------------------- render edits (plan 28 N4)
#
# The GRAPH page's edits of the render graph: a cable dragged between two
# image ports is a wire in the preset's `graph` section (`graph.Wire`); a
# geometry cable from a hands node into the scene or the layer is that
# node's `into`; the picker adds an effect instance, a hands node or a
# composite; deleting a render node or cable takes it out of the section.
# Each edit is a new section read back through `graph.read_graph` with the
# build's effect files — so a refusal is the very note a preset file would
# get, in its words, and nothing changes — then landed through the
# preset's `GraphSection` (`land`: the instances' params declared or
# dropped, the renderer handed the new wiring, which builds the graph
# again), one undo step before it (`push`), the preset dirty. The seam
# with plan 28 N3's modulation edits is the port type: image / geometry /
# mask cables are these (`RENDER_TYPES`), value / trigger cables N3's.

RENDER_TYPES = (IMAGE, GEOMETRY, MASK)
# the frame's own nodes no wire names, and why
PLUMBING = {
    "fx": "is a chain's end: its outputs take it by their switches — wire into an "
          "output's image to show something else",
    "composite(": "lays the hands on before the chain (an output's through switch), "
                  "not a node a wire names",
    "capture": "holds what the history is wired to: wire into history.image",
    "shape": "is drawn by the scene, not wired",
    "readout": "is the hands' guide alone: wire the layer into an output's readout",
    "cloud": "is drawn by the scene, not wired",
}


def _plumbing(name: str) -> str:
    for head, why in PLUMBING.items():
        if name == head or name.startswith(head):
            return f"{name} {why}"
    return f"{name} is the frame's own, not a node a wire names"


def spec_name(pin: str, render_graph=None) -> tuple[str | None, str | None]:
    """A canvas pin or node id (`rout:<node>`, `rin:<node>/<port>`,
    `render:<node>`), or a name as the preset's graph says it → (that
    name — `hands.2`, `acid.2`, `output.2.hands`, `scene.geometry` —,
    None), or (None, why it is no name a wire may use). An effect's node
    in any pipeline is its instance (`acid(scene+hands)` → `acid`); a
    wired output's end stands for the output's image port and what feeds
    it."""
    head, _, rest = pin.partition(":")
    if head not in ("rout", "rin", "render") or not rest:
        node = pin.rpartition(".")[0] if rgraph.wire_node_kind(pin) is None else pin
        return (pin, None) if rgraph.wire_node_kind(node) is not None else (
            None, f"no node {pin!r}")
    built, _, port = rest.partition("/")
    nodes = getattr(render_graph, "nodes", None) or {}
    node = nodes.get(built)
    if isinstance(node, rgraph.Wired):
        out = built[len("wire("):-1]
        if head == "rin":
            return f"{out}.image", None
        src = node.inputs["image"]
        if src is None:
            return None, f"{out}'s wired picture has no source"
        return spec_name(f"rout:{src.name}", render_graph)
    if isinstance(node, rgraph.Effect):
        name = node.effect
    elif isinstance(node, (rgraph.Fx, rgraph.Capture, rgraph.Shape, rgraph.Readout,
                           rgraph.PointCloud)):
        return None, _plumbing(built)
    else:
        name = built
        if rgraph.wire_node_kind(name) is None:
            return None, _plumbing(built)
    if head == "rin":
        if isinstance(node, rgraph.Scene) and port.startswith("geometry"):
            port = "geometry"
        return f"{name}.{port}", None
    return name, None


@dataclass
class Edit:
    """Edit requests from the GRAPH page, each returning None (done; its
    words in `said`) or a refusal in words, nothing changed.

    Plan 28 N4, the render graph: `wire`, `unwire`, `add_node`,
    `drop_node`, `set_node` — each lands a new `graph.GraphSpec` through
    `graph` (the preset's `GraphSection`), with `push(label)` (the undo
    step: the page passes `undo.push(label, load=True)`) before it;
    `render` is the renderer's last graph, through which a canvas pin
    names its node. (Plan 28 N3 adds the modulation's requests beside
    these.)"""

    graph: Any = None                       # preset.GraphSection
    render: Any = None                      # graph.Graph: canvas pins → names
    push: Callable[[str], None] | None = None
    said: str = ""

    def wire(self, src_port: str, dst_port: str, dry: bool = False) -> str | None:
        """A picture from `src_port` into `dst_port` (a geometry cable: the
        hands node's place). `dry`: only say whether it may be."""
        return render_wire(self, src_port, dst_port, dry)

    def unwire(self, cable, dst: str | None = None) -> str | None:
        """Take a render cable (a `VCable`, or its two ends; one port's
        name alone: whatever is wired into it) out of the graph."""
        return render_unwire(self, cable, dst)

    def add_node(self, kind: str, file: str | None = None, **settings) -> str | None:
        """The picker: an effect instance (`EffectAt(file, n + 1)`), a hands
        node (`HandsAt(n + 1)`) or a composite."""
        return render_add(self, kind, file, **settings)

    def drop_node(self, node: str) -> str | None:
        """Delete a render node — an extra effect instance, hands node or
        composite — out of the section, with every wire on it."""
        return render_drop(self, node)

    def set_node(self, node: str, **settings) -> str | None:
        """A node's setting: a hands node's `draw` / `into`, a composite's `blend`."""
        return render_set(self, node, **settings)


def picker(edit: Edit) -> list[tuple[str, str | None, str]]:
    """The right-click picker's list: (kind, file, label) — every effect
    file this build has, then a hands node and a composite."""
    gs = edit.graph
    files = gs.files() if gs is not None and hasattr(gs, "files") else None
    out: list[tuple[str, str | None, str]] = [("effect", f, f) for f in sorted(files or ())]
    return out + [("hands", None, "hands"), ("composite", None, "composite")]


def _doc(edit: Edit) -> dict:
    spec = getattr(edit.graph, "spec", None)
    return copy.deepcopy(spec.to_json()) if spec is not None else {"nodes": []}


def _land(edit: Edit, doc: dict, label: str, said: str, dry: bool = False) -> str | None:
    """Read `doc` back as a preset would (a note is the refusal, nothing
    changed); else, unless `dry`, the undo step and the landing."""
    gs = edit.graph
    if gs is None:
        return "no preset is loaded"
    files = gs.files() if hasattr(gs, "files") else None
    if not doc.get("wires"):
        doc.pop("wires", None)
    try:
        spec = rgraph.read_graph(doc, effects=files)
    except rgraph.GraphError as e:
        return str(e)
    if spec.notes:
        return spec.notes[0]
    if dry:
        return None
    new = spec.to_json()
    if new == _doc(edit):
        edit.said = "already so"
        return None
    if edit.push is not None:
        edit.push(label)
    if new == {"nodes": []}:                 # nothing left: the default graph, no section
        gs.land(None, None)
    else:
        gs.land(spec, new)
    edit.said = said
    return None


def _entry_name(e: dict) -> str | None:
    if e.get("kind") != "effect" or "file" not in e:
        return None
    return rgraph.instance_name(e["file"], e.get("instance", 1))


def _unplace(doc: dict, which: Callable[[str, str, str], bool]) -> None:
    """D1's placement off each effect entry `which(name, key, where)`
    picks: an extra instance back in the chain, instance 1's entry gone
    (the file itself, always there)."""
    keep = []
    for e in doc.get("nodes", []):
        name = _entry_name(e)
        key = next((k for k in rgraph.PLACE_KEYS if k in e), None)
        if name is not None and key is not None and which(name, key, e[key]):
            if e.get("instance", 1) < 2:
                continue
            e = {k: v for k, v in e.items() if k not in rgraph.PLACE_KEYS}
        keep.append(e)
    doc["nodes"] = keep


def _hands_entry(doc: dict, n: int) -> dict | None:
    return next((e for e in doc.get("nodes", []) if e.get("kind") == "hands"
                 and e.get("instance", 1) == n), None)


def render_wire(edit: Edit, src: str, dst: str, dry: bool = False) -> str | None:
    s, why = spec_name(src, edit.render)
    if s is None:
        return why
    d, why = spec_name(dst, edit.render)
    if d is None:
        return why
    if rgraph.wire_node_kind(d) is not None:
        return f"{d} is a node, not a port: a wire goes into {rgraph.WIRE_TO_WORDS}"
    w = rgraph.Wire(s, d)
    src_kind, dst_kind = rgraph.wire_node_kind(s), rgraph.wire_node_kind(w.node)
    takes = rgraph.WIRE_TAKES.get(dst_kind or "", {}).get(w.port)
    makes = rgraph.WIRE_MAKES.get(src_kind or "")
    if takes == GEOMETRY and makes == GEOMETRY:
        return _hands_into(edit, s, "scene" if w.node == "scene" else "layer", dry)
    if takes == MASK and makes == MASK:
        return "the cover is the history's own: it is wired so already"
    doc = _doc(edit)
    doc["wires"] = [x for x in doc.get("wires", []) if x["to"] != d] + [w.to_json()]
    into_effect = dst_kind == "effect"

    def moves(name: str, key: str, where: str) -> bool:
        if name == w.node:                       # the effect is fed by this wire now
            return True
        target = where if key == "into" or where.startswith("output.") else None
        if target is not None and f"{target}.image" == d:   # its port takes this wire
            return True
        return name == s and not into_effect     # the effect is wired on, elsewhere
    _unplace(doc, moves)
    return _land(edit, doc, f"wire {w}", f"wired {w}", dry)


def _hands_into(edit: Edit, ghost: str, into: str, dry: bool = False) -> str | None:
    """A geometry cable: hands node `ghost` drawn in the scene or as the layer."""
    _, n = rgraph.split_instance(ghost)
    spec = getattr(edit.graph, "spec", None)
    wiring = spec.wiring() if spec is not None else rgraph.Wiring()
    if n not in {h.n for h in wiring.nodes()}:
        return f"no {ghost} hands node in this graph"
    layer = wiring.layer_node()
    if into == "layer" and layer.n != n and layer.into == "layer":
        return (f"{rgraph.hands_name(layer.n)} makes the layer: put it in the scene first "
                "(one hands node makes the layer)")
    doc = _doc(edit)
    e = _hands_entry(doc, n)
    if e is None:
        e = {"kind": "hands", **({"instance": n} if n > 1 else {})}
        doc["nodes"].insert(0, e)
    if into == "layer":
        e.pop("into", None)
    else:
        e["into"] = into
        e.pop("laid", None)
    if len(e) == 1:
        doc["nodes"].remove(e)
    return _land(edit, doc, f"{ghost} into the {into}", f"{ghost} drawn in the {into}", dry)


def render_unwire(edit: Edit, cable, dst: str | None = None) -> str | None:
    if isinstance(cable, VCable):
        src_node, node, port = cable.ref
        src, dst = f"rout:{src_node.name}", f"rin:{node.name}/{port}"
    else:
        src = cable
    s, why = spec_name(src, edit.render)
    if s is None:
        return why
    d = None
    if dst is not None:
        d, why = spec_name(dst, edit.render)
        if d is None:
            return why
    else:                                    # a port's name alone: whatever goes into it
        s, d = None, s
    kind = rgraph.wire_node_kind(s) if s is not None else None
    if rgraph.WIRE_MAKES.get(kind or "") == GEOMETRY:
        if d == "scene.geometry":
            return _hands_into(edit, s, "layer")
        return f"{s} is the layer's geometry: put it in the scene instead"
    doc = _doc(edit)
    wires = doc.get("wires", [])
    left = [x for x in wires if not (x["to"] == d and (s is None or x["from"] == s))]
    changed = len(left) != len(wires)
    doc["wires"] = left
    if not changed and s is not None:
        before = copy.deepcopy(doc["nodes"])

        def placed_here(name: str, key: str, where: str) -> bool:
            if key == "after" and not where.startswith("output."):
                return where == s and d == f"{name}.image"
            return name == s and d == f"{where}.image"
        _unplace(doc, placed_here)
        changed = doc["nodes"] != before
    if not changed:
        said = f"{s} → {d}" if s is not None else d
        return (f"{said} is the default graph's: no wire says it (wire something else "
                f"into {d} to replace it)")
    return _land(edit, doc, f"unwire {d}", f"unwired {d}")


def render_add(edit: Edit, kind: str, file: str | None = None, **settings) -> str | None:
    spec = getattr(edit.graph, "spec", None)
    doc = _doc(edit)
    if kind == "effect":
        files = edit.graph.files() if hasattr(edit.graph, "files") else None
        if not file or (files is not None and file not in files):
            return f"no {file} effect in this build"
        n = max([e.n for e in (spec.effects if spec is not None else ()) if e.file == file],
                default=1) + 1
        doc["nodes"].append({"kind": "effect", "file": file, "instance": n})
        name = rgraph.instance_name(file, n)
        return _land(edit, doc, f"add {name}", f"{name} added: its params are fx.{name}.*")
    if kind == "hands":
        wiring = spec.wiring() if spec is not None else rgraph.Wiring()
        n = max(h.n for h in wiring.nodes()) + 1
        into = settings.get("into") or ("scene" if wiring.layer_node().into == "layer"
                                        else "layer")
        e: dict[str, Any] = {"kind": "hands", "instance": n}
        if into != "layer":
            e["into"] = into
        if settings.get("draw", "solid") != "solid":
            e["draw"] = settings["draw"]
        doc["nodes"].append(e)
        name = rgraph.hands_name(n)
        return _land(edit, doc, f"add {name}", f"{name} added, drawn in the {into}")
    if kind == "composite":
        n = max([c.n for c in (spec.composites() if spec is not None else ())], default=0) + 1
        c = rgraph.CompositeAt(n, settings.get("blend", "over"))
        doc["nodes"].append(c.to_json())
        return _land(edit, doc, f"add {c.name}", f"{c.name} added: wire its under and over")
    return f"no node kind {kind!r}: the picker adds an effect, hands or a composite"


def _touches(x: dict, names: set[str]) -> bool:
    return x["from"] in names or x["to"].rpartition(".")[0] in names


def render_drop(edit: Edit, node: str) -> str | None:
    name, why = spec_name(node, edit.render)
    if name is None:
        return why
    kind = rgraph.wire_node_kind(name)
    doc = _doc(edit)
    before = copy.deepcopy(doc)
    if kind == "effect":
        doc["nodes"] = [e for e in doc["nodes"] if _entry_name(e) != name]
        names = {name}
    elif kind in ("ghost", "layer"):
        _, n = rgraph.split_instance(name)
        if n == 1:
            return "hands 1 is the frame's own hands: it stays (switch it off on HANDS)"
        doc["nodes"] = [e for e in doc["nodes"] if not (e.get("kind") == "hands"
                                                         and e.get("instance", 1) == n)]
        names = {rgraph.hands_name(n), rgraph.layer_name(n)}
    elif kind == "composite":
        _, n = rgraph.split_instance(name)
        doc["nodes"] = [e for e in doc["nodes"] if not (e.get("kind") == "composite"
                                                         and e.get("instance", 1) == n)]
        names = {name}
    else:
        return f"{name} is the frame's own: it stays"
    doc["wires"] = [x for x in doc.get("wires", []) if not _touches(x, names)]
    if not doc["wires"]:
        doc.pop("wires")
    _unplace(doc, lambda e, key, where: where in names)
    if doc == before:
        return (f"{name} is a file: it is always in the chain (switch it off on FX)"
                if kind == "effect" else f"{name} is not in the preset's graph")
    return _land(edit, doc, f"delete {name}", f"{name} deleted")


def render_set(edit: Edit, node: str, **settings) -> str | None:
    name, why = spec_name(node, edit.render)
    if name is None:
        return why
    kind = rgraph.wire_node_kind(name)
    doc = _doc(edit)
    if kind in ("ghost", "layer"):
        _, n = rgraph.split_instance(name)
        if "into" in settings:
            return _hands_into(edit, rgraph.hands_name(n), settings["into"])
        e = _hands_entry(doc, n)
        if e is None:
            if n > 1:
                return f"no {name} hands node in this graph"
            e = {"kind": "hands"}
            doc["nodes"].insert(0, e)
        how = settings.get("draw", "solid")
        if how == "solid":
            e.pop("draw", None)
        else:
            e["draw"] = how
        if len(e) == 1:
            doc["nodes"].remove(e)
        return _land(edit, doc, f"{name} {how}", f"{rgraph.hands_name(n)} drawn {how}")
    if kind == "composite":
        _, n = rgraph.split_instance(name)
        blend = settings.get("blend", "over")
        for e in doc["nodes"]:
            if e.get("kind") == "composite" and e.get("instance", 1) == n:
                e.pop("blend", None)
                if blend != "over":
                    e["blend"] = blend
                return _land(edit, doc, f"{name} {blend}", f"{name} laid {blend}")
        return f"no {name} node in this graph"
    return f"{name} has no setting here"

