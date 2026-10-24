"""The GRAPH page's model (plan 28 N2): both graphs as one set of nodes,
ports and cables, built from the live objects and drawn by ui_graph.py.

Nothing here draws. `build` reads the binding
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
  while it is not connected (its cables dormant); a device with `layers`
  one per layer (plan 28 N5: *apc40* and *apc40 (SHIFT)*,
  ``device:<role>/global``, `device_nodes`); a role this rig lists no
  device for, a grey placeholder of that id (its cables waiting);
  ``template`` — the loaded preset's desk template (``template:<name>``),
  a subgraph of the preset-layer rows still its own; ``source`` — the
  keys, which are no device; ``analyzer`` — one port per band lane;
- ``lfo`` — each LFO (``lfo.<n>``), its knobs (`lfo.<n>.*`) as input
  ports and its lane as the output; ``env`` (plan 31) — each envelope
  (``env.<n>``), the same way; ``seq`` — the step sequencer (one node,
  ``seq``): its params as inputs and a trigger output per lane
  (``seq:<l>``), each bound lane's envelope drawn as a ``lane`` cable into
  that envelope's ``fire``; ``modifier`` (``mod.<n>``, plan 28
  N1) — its inputs, its params, its lane; ``macro`` (``macro.<n>``) — a
  bus: its knob in, one output, its subscribers as cables;
- ``render`` / ``output`` — the render graph's nodes (``render:<name>``),
  with their image / geometry / mask ports and, as input ports, the
  params of the render node that owns them (`OWNERS`, the one table);
  ``render:eye`` — the shared camera (`camera.*`, `eye.*`), which draws
  through every geometry and so has no image port; ``render:media.<c>``
  — the eight media channels (plan 32 T10), always, each with its image
  out and its `media.<c>.*` params, one node per channel however many
  nodes the render graph made of it (the backdrop's, a wire's);
  ``render:frame``, ``render:pattern``, ``render:backdrop`` (plan 33 U)
  — the run's head, the face pattern, the backdrop, the pattern and the
  backdrop always; an unreached effect, composite or switch of the
  section drawn from it (`unreached`), ``faint`` ("reaches nothing");
- ``group`` — a node per group of params no render node owns
  (``group:tempo``, ``group:master`` …).

**Ports** (`VPort`): a source port has one pin (``out:<address>``); a
param port has a ``base:<pid>`` stub (the setters: desk, pad and key
rows, a macro's base subscriber — many, last touch wins) and a
``mod:<pid>`` stub (the one performer under the referee), and a
``depth:<pid>`` stub while a route lands on it (a macro's depth
subscriber scales that route); a modifier's inputs are ``in:<id>.<k>``,
a macro's output ``bus:<id>``, a render node's ports ``rin:<node>/<port>``
and ``rout:<node>``; every node's single in / out stub (plan 28 N7, where
its bundles end while it is collapsed) ``nin:<node>`` / ``nout:<node>``.
Pins are strings; the page maps them to the widget's integer ids.

**Collapsed nodes and bundles** (plan 28 N7): `summary` is a collapsed
node's lines (five at most); `wiring` folds every value / trigger cable
with a collapsed end into one `VBundle` per (source node, target node)
pair; `land_choices` is the picker a drag onto a stub opens.

**Cables** (`VCable.kind`): ``route`` (one per performer row, `ref` the
`Binding`, into ``mod``), ``setter`` (a desk / pad / key row, into
``base``), ``sub`` (a macro subscriber, into ``base`` or ``depth``,
`ref` (macro id, `Sub`)), ``input`` (a modifier's input), ``render`` (a
render-graph edge, `ref` (source node, node, port)), ``lane`` (plan 31: a
sequencer lane's envelope binding, `ref` (lane, envelope id) — no row:
dragging a lane's pin onto an envelope's ``base:env.<n>.fire`` rebinds it,
and it cannot be deleted). A route's `scale`
and its `when` gate are said on the cable (`label`), not drawn: a param
has no output pin. Sink rows are not drawn in this plan.

**Layout** (`auto_layout`, `home`): positions live in two maps — the
preset's (`preset.LAYOUT_KEY`) for the nodes a preset holds (modifiers,
macros, the render nodes and their params, a performance group's node,
the LFOs, the envelopes, the sequencer) and the show's for the rig's
(devices, sources, the analyzer, the outputs, a session group's node). An unplaced node is laid out in its
**area** (plan 28 N9, the owner's decision of 2026-10-20: the canvas
organised by concern), left to right: *controllers* (the devices, the
keys, a placeholder, a desk template) → *audio* (the analyzer, the band,
tempo, master, audio and scene params; the small *other* area — the
preset, ui and desk params — stacked under it) → *modulation* (the LFOs,
the modifiers, the macros) → *media* (the eight channels and the
backdrop, plan 32 T10; plan 33 the pattern, the switches, and any
effect or composite made of the media alone, `media_made`) → *geometry*
(the shape, the camera, the hands, a cloud, the scene that draws them) →
*shaders* (the history, `frame`, the effects, the composites, `fx`, the
outputs). Every wire runs right but the shaders' wrapped rows and a
scene picture taken back into a switch (`returns`). `AREA` is the one table (`area_of`);
each area's title is drawn on the canvas over its first column
(`layout`). A node with nothing in and nothing out (`VNode.idle`: an
unused macro, an unpatched LFO, a group node no cable reaches, a lost
device with no rows) is not drawn: its area shows one "n idle" line in
its place that expands to show them.

Imports `routing`, `params`, `graph`, `patch`, `modifiers` — the device
registry is handed in and read through `devices.Device`'s protocol
(`role`, `kind`, `status`, `sources`, `schemes`), so nothing of
`devices.py` is imported — and never imgui (tests/test_graphview.py
holds it)."""

from __future__ import annotations

import copy
import itertools
import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from . import envelope as envmod
from . import graph as rgraph
from . import learn as learnmod
from . import modbank
from . import modifiers as modmod
from . import patch as patchmod
from . import sequencer as seqmod
from .params import PERFORMANCE_GROUPS, Kind, Param, Registry
from .routing import (
    MOD_OPS,
    SAVE_PARAM,
    Binding,
    Bindings,
    Macro,
    Owned,
    Router,
    Sub,
    base_refusal,
    base_scheme,
    is_continuous,
    is_macro,
    is_session_row,
)

# signal kinds a port and a cable carry (decision 10: values and triggers;
# plan 26's image, geometry and mask)
VALUE, TRIGGER = "value", "trigger"
IMAGE, GEOMETRY, MASK = rgraph.IMAGE, rgraph.GEOMETRY, rgraph.MASK
TYPES = (VALUE, TRIGGER, IMAGE, GEOMETRY, MASK)

KINDS = ("device", "source", "analyzer", "lfo", "env", "seq", "modifier", "macro", "group",
         "render", "output", "template")
# plan 31 G1: ``lane`` is a sequencer lane's envelope binding (``seq.<l>.env``,
# a fixed link the sequencer fires directly — no row), drawn as a cable
CABLE_KINDS = ("route", "setter", "sub", "input", "render", "lane")
IN, OUT = "in", "out"
BASE, MOD, DEPTH = "base", "mod", "depth"
# which layout map a node's position is saved in
PRESET, SESSION = "preset", "session"

ANALYZER = "analyzer"
EYE = "eye"                  # the shared camera's node: `render:eye`
MISSING = "missing"          # a group node for the cables' targets no registry holds
# plan 31 G1: the modulator banks the canvas draws a node per voice of
# (``lfo.<n>``, ``env.<n>``: the scheme is the node's kind and the params'
# group), in drawing order, and the sequencer's one node
BANK_SCHEMES = ("lfo", "env")
SEQ = "seq"
LANE_ENVS = envmod.LANE_ENVS      # the lanes' own envelopes, never deleted
# a bank's voice in words (one, many): the picker's entries, the refusals
BANK_WORDS = {"lfo": ("LFO", "LFOs"), "env": ("envelope", "envelopes")}


def voice_of(nid: str) -> tuple[str, int] | None:
    """``lfo.3`` → ("lfo", 3), ``env.7`` → ("env", 7); None for any other id."""
    scheme, dot, n = nid.partition(".")
    if scheme in BANK_SCHEMES and dot and n.isdecimal() and int(n) >= 1:
        return scheme, int(n)
    return None
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
    bipolar: bool = False        # a source centred on its rest (a hand's roll, a stick)
    # plan 28 N5: the device layer a desk port sends on ("" every layer: an
    # invariant control, any other device's port) and whether that layer is
    # up this frame (`refresh`: the table's latch, `Bindings.layer_of`)
    layer: str = ""
    up: bool = True

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
    # plan 28 N5: a layered device's node is one layer's (`layer`, of the
    # device of `role`), lit while that layer is up (`up`, `refresh`); a
    # `placeholder` is a role this rig lists no device for (grey, its
    # cables waiting)
    layer: str = ""
    role: str = ""
    up: bool = True
    placeholder: bool = False
    # plan 28 N7: how many cables start or end on this node (`build`), for
    # its collapsed lines
    wires: int = 0
    # plan 28 N9: the concern area the canvas lays this node out in
    # (`area_of`, `AREA`), and whether it sits with nothing in and nothing
    # out (`build`: not drawn until its area's idle line is opened)
    area: str = ""
    idle: bool = False
    # plan 33 U: an effect, composite or switch the preset's graph holds
    # that no path leads from to a sink (`graph.reaches`): kept, never run,
    # drawn faint with the line "reaches nothing" — never idle
    faint: bool = False

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
    # plan 28 N5: the subgraph node (a desk template's, ``template:<name>``)
    # the cable is inside of: the page draws it only while that node is
    # open (ui_graph.is_open); "" for every other cable
    inside: str = ""


@dataclass
class View:
    nodes: list[VNode] = field(default_factory=list)
    cables: list[VCable] = field(default_factory=list)
    spec: Any = None                 # the preset's graph spec (graph.GraphSpec | None)
    pins: dict[str, tuple[str, str]] = field(default_factory=dict)   # pin → (node, port)

    def node(self, nid: str) -> VNode | None:
        # by an index kept while the node list is the same list of the same
        # length (plan 28 N7: `refresh` asks it per cable every frame)
        idx = self.__dict__.get("_index")
        if idx is None or idx[0] is not self.nodes or idx[1] != len(self.nodes):
            idx = self.__dict__["_index"] = (self.nodes, len(self.nodes),
                                             {n.id: n for n in reversed(self.nodes)})
        n = idx[2].get(nid)
        if n is not None and n.id == nid:
            return n
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
    # `fx.mix` the scene pipeline's end; (plan 33 U)
    # `fx.face_map` the shape's, whose faces it maps the picture onto
    if pid == "fx.face_map":
        return "shape"
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


def _media_owner(pid: str, ctx: _Ctx) -> str | None:
    # plan 32 T10: `media.<c>.<key>` on channel c's node, there whatever the
    # render graph holds (`build` adds the eight)
    seg = pid.split(".")
    return rgraph.media_name(seg[1]) if len(seg) >= 3 else None


def _view_owner(pid: str, ctx: _Ctx) -> str | None:
    # plan 33 U: the face pattern and its media layer (`view.pattern*`,
    # `view.media_*`) are the pattern node's; the rest of `view.*` the shape's
    key = pid.partition(".")[2]
    return "pattern" if key.startswith(("pattern", "media_")) else "shape"


def _switch_owner(pid: str, ctx: _Ctx) -> str | None:
    # plan 33 S: `switch[.<n>].select` on its switch's node
    return pid.rpartition(".")[0] or None


# a param's group → the render node that owns it: a node name, or a rule
# over the id (an instance's number, an effect's name). A name the render
# graph does not hold this frame (no output shows the hands, no scene
# pipeline) leaves the param to its group's node. `EYE` is the shared
# camera's node, which the render graph has no node for. A group not
# listed here has no render node: a node per group (`group:<group>`)
OWNERS: dict[str, str | Callable[[str, _Ctx], str | None]] = {
    "view": _view_owner,
    "rot": "shape",
    "pattern": "shape",
    # plan 33 U: the backdrop's params on its node (always drawn), a
    # switch's pick on its switch
    "backdrop": "backdrop",
    "switch": _switch_owner,
    "ghost": _hands_owner,
    "cloud": _cloud_owner,
    "dream": "history",
    "fx": _effect_owner,
    "camera": EYE,
    "eye": EYE,
    "output": _output_owner,
    "media": _media_owner,
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

def bank_of(router: Router | None, scheme: str):
    """The modulator bank (modbank.Bank) of `scheme` the router steps, or
    None: ``lfo`` is also `Router.lfos` (the callers that hand it in
    alone)."""
    if router is None:
        return None
    d = getattr(router, "__dict__", {})
    bank = (d.get("banks") or {}).get(scheme)
    if bank is None and scheme == "lfo":
        bank = d.get("lfos")
    return bank


# the param each bank's voice always declares: a bare registry's voices
BANK_PROBE = {"lfo": "depth", "env": "fire"}


def bank_ids(router: Router | None, reg: Registry, scheme: str) -> list[int]:
    """A bank's voice ids (1-based, ascending): the router's bank's, else
    every ``<scheme>.<n>.<probe>`` the registry holds. A list, not a count —
    ids keep their gaps when a voice is removed (plan 31 B)."""
    ids = getattr(bank_of(router, scheme), "ids", None)
    if callable(ids):
        try:
            return list(ids())
        except TypeError:
            pass
    probe = BANK_PROBE.get(scheme, "depth")
    return [n for n in range(1, modbank.MAX_ID + 1) if f"{scheme}.{n}.{probe}" in reg]


def _lfo_ids(router: Router | None, reg: Registry) -> list[int]:
    """The LFOs' ids (`bank_ids`)."""
    return bank_ids(router, reg, "lfo")


def has_sequencer(router: Router | None, reg: Registry) -> bool:
    """Is there a step sequencer to draw: the router steps one, or the
    registry holds its params (plan 31 S)."""
    return (router is not None and getattr(router, "__dict__", {}).get("sequencer")
            is not None) or f"{seqmod.GROUP}.run" in reg


def seq_lanes(reg: Registry) -> list[tuple[int, int, bool, bool]]:
    """Each sequencer lane's envelope binding as (0-based lane, the 1-based
    envelope id its steps fire — ``seq.<l>.env`` — whether any of its steps
    is on, whether it is muted), read off the registry."""
    out = []
    for li in range(seqmod.LANES):
        p = reg.get(f"{seqmod.GROUP}.{li + 1}.env")
        if p is None:
            continue
        try:
            env = round(float(p.value))
        except (TypeError, ValueError):
            continue
        on = any(bool(getattr(reg.get(f"{seqmod.GROUP}.{li + 1}.{s + 1}"), "value", False))
                 for s in range(seqmod.STEPS))
        mute = reg.get(f"{seqmod.GROUP}.{li + 1}.mute")
        out.append((li, env, on, bool(mute.value) if mute is not None else False))
    return out


def seq_running(reg: Registry) -> bool:
    p = reg.get(f"{seqmod.GROUP}.run")
    return bool(p.value) if p is not None else False


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
    The base of `device_nodes` (plan 28 N5), which makes a device with
    `layers` one node per layer from it."""
    role = str(getattr(d, "role", "") or "")
    try:
        status = str(d.status)
    except Exception as e:  # noqa: BLE001 — a status line never takes the page down
        status = f"error: {e}"
    node = VNode(f"device:{role}", "device", role, grey=not status.startswith("connected"),
                 status=f"{getattr(d, 'kind', '')} · {status}", ref=d)
    try:
        ports = [p for p in d.sources if p.kind in (VALUE, TRIGGER)]
    except Exception:  # noqa: BLE001
        ports = []
    return node, ports


# ---------------------------------------------------------------- controllers (plan 28 N5)
#
# A device with `layers` (the first MIDI role's APC40: "preset", "global")
# is **one node per layer** (decision 12): *apc40* — the preset layer's
# rows and the invariant ones (SHIFT, the crossfader, the bank pads,
# transport, tap: `Bindings.is_invariant`), whose controls are ports on this
# node only — and *apc40 (SHIFT)* (``device:<role>/global``), the global
# layer's rows. Each port is lit while its layer is up — the table's latch,
# the one `MidiIO` reads (`Bindings.layer_of(role)`) — and each row's cable
# leaves the node of the layer it belongs to. Presentation only: no row,
# no home, no layer changes here. A desk template the loaded preset names
# (plan 24 C3) is one more node, ``template:<name>``, whose ports are its
# mapped controls: the live preset-layer rows that are still the
# template's hang off it (`VCable.inside`: the page draws them only while
# the node is open); an override hangs off *apc40*. A row whose role this
# rig lists no device for draws from a grey placeholder ``device:<role>``.

PRESET_LAYER, GLOBAL_LAYER = "preset", "global"
TEMPLATE = "template"
# what a layer's node is called after the device's role ("apc40 (SHIFT)")
LAYER_LABEL = {GLOBAL_LAYER: "SHIFT"}
# the desk's port groups (`Port.group` is the profile's control kind), in
# the order a desk node lists them; the invariant controls first, as their
# own group, on the device's first node only
INVARIANT = "invariant"
DESK_GROUPS = (INVARIANT, "track knobs", "device knobs", "knobs", "faders", "clip grid",
               "buttons")
# a role-less row's role when no listed device publishes its scheme: the
# rig's usual name for the kind behind it (config.py's example list); a
# scheme not here is a role of its own (an OSC device's scheme is its role)
SCHEME_ROLE = {"hand": "leap", "hands": "leap", "axis": "pad", "pad": "pad", "hat": "pad",
               "cc": "apc40", "note": "apc40", "pitch": "apc40"}
# schemes that are no device's: the keyboard, the built-in lanes, the modifiers
NO_DEVICE = ("key", "lane", "lfo", "env", SEQ, modmod.SCHEME)
PLACEHOLDER_STATUS = "not in this rig: its cables wait for it"


def desk_group(group: str, label: str, invariant: bool = False) -> str:
    """A desk port's group on its node: ``invariant`` for an invariant
    control; else the profile's control kind (`Port.group`) as a plural,
    the knobs split by Akai's name ("track knob 3", "device knob 1")."""
    if invariant:
        return INVARIANT
    if group == "knob":
        low = label.lower()
        return ("track knobs" if low.startswith("track knob") else
                "device knobs" if low.startswith("device knob") else "knobs")
    return {"fader": "faders", "grid": "clip grid", "button": "buttons"}.get(group, group)


def hand_group(port) -> str:
    """A hands port's group (the design's axes, pinches, grab, dance):
    `hands/device.py`'s groups, its ``switches`` told apart by address —
    a grab is ``<side>.grab``, every other switch a pinch."""
    g = getattr(port, "group", "") or ""
    if g == "switches":
        return "grab" if str(getattr(port, "name", "")).endswith(".grab") else "pinches"
    return g


def _invariant(table, addr: str) -> bool:
    """Is the control `addr` names invariant on its desk (SHIFT, or the
    control of an enabled layer-None row)? False for anything else."""
    fn = getattr(table, "is_invariant", None)
    if fn is None:
        return False
    try:
        return bool(fn(Binding(addr, "")))
    except Exception:  # noqa: BLE001 — a malformed address is no control
        return False


def _desk_order(rows: list) -> list:
    rank = {g: i for i, g in enumerate(DESK_GROUPS)}
    return sorted(rows, key=lambda r: rank.get(r[1], len(rank)))     # stable: layout order


def device_nodes(d, table=None) -> list[tuple[VNode, list]]:
    """A listed device as its nodes, each with the ports it draws as
    ``(Port, group, layer)``. A device with fewer than two `layers` is one
    node (`device_node`); one with layers is a node per layer — the first
    (``device:<role>``) every port, the invariant controls among them
    (layer "": lit on every layer), the others (``device:<role>/<layer>``)
    every port but the invariant controls. A desk's ports take
    `desk_group`'s groups, the hands' `hand_group`'s."""
    node, ports = device_node(d)
    kind = getattr(d, "kind", "")
    if kind == "hands":
        return [(node, [(p, hand_group(p), "") for p in ports])]
    if kind != "midi":
        return [(node, [(p, p.group, "") for p in ports])]
    try:
        layers = tuple(getattr(d, "layers", ()) or ())
    except Exception:  # noqa: BLE001
        layers = ()
    if len(layers) < 2:
        return [(node, _desk_order([(p, desk_group(p.group, p.label), "") for p in ports]))]
    inv = {p.address: _invariant(table, p.address) for p in ports}
    node.layer, node.role = layers[0], node.label
    out = [(node, _desk_order([(p, desk_group(p.group, p.label, inv[p.address]),
                                "" if inv[p.address] else layers[0]) for p in ports]))]
    for layer in layers[1:]:
        n = VNode(f"{node.id}/{layer}", "device",
                  f"{node.label} ({LAYER_LABEL.get(layer, layer)})", grey=node.grey,
                  status=node.status, ref=d, layer=layer, role=node.label)
        out.append((n, _desk_order([(p, desk_group(p.group, p.label), layer)
                                    for p in ports if not inv[p.address]])))
    return out


def template_rows(template) -> tuple[str, list[Binding]] | None:
    """The loaded preset's desk template — handed in as ``(name, its rows
    as the load read them)`` — with its rows parsed, or None."""
    if not template:
        return None
    name, rows = template
    out = []
    for r in rows or ():
        try:
            out.append(Binding.from_json(r))
        except (KeyError, TypeError, ValueError):
            continue
    return str(name), out


def _row_key(b: Binding) -> tuple:
    """What makes a live desk row the template's own (`preset.compact_desk`
    writes no override for it): its control, target, op and value."""
    return (b.source, b.target, b.op, float(b.value))


def _port_type(kind: str) -> str:
    return TRIGGER if kind == TRIGGER else VALUE


# ---------------------------------------------------------------- the free graph (plan 33 U)
#
# The preset's graph is wires (plan 33): the run `frame → … → fx.image`,
# branches from the channels and the pattern, the faces' and the
# backdrop's inputs, the switches. The canvas draws it as the render graph
# built it, and three things the render graph has no node for:
#
# - **`frame`** — each pipeline's picture before its effects (the history;
#   the history with the hands laid on; the hands' layer). The render graph
#   reads the run from that picture directly; the canvas draws one `frame`
#   node, the run's first cable leaving it (so a cable names the wire the
#   section says, `frame → acid.image`), and a `feeds` cable from each
#   pipeline's picture into it — what `frame` is, never a wire;
# - **the pattern and the backdrop**, always, as the channels are: a wire
#   end is somewhere to drag to before anything is wired there;
# - **the unreached** (`unreached`): an effect, composite or switch of the
#   section that no path leads from to a sink has no render node (it never
#   runs); the canvas draws it from the section — a stand-in node, faint,
#   "reaches nothing", its wires in — so it can be wired in.

REACHES_NOTHING = "reaches nothing"     # the spec's canvas word for an unreached node
FEEDS = "feeds"                         # a cable from a pipeline's picture into `frame`
FEEDS_NO_DELETE = ("frame is each pipeline's picture before its effects (the history, "
                   "the hands laid on): nothing to delete — insert effects after it")
RUN_KEPT = "the run starts at frame and ends at fx.image — insert effects into it"
MAKER_KINDS = ("effect", "composite", "switch")


class FrameNode(rgraph.Node):
    """`frame` on the canvas (plan 33 U): the pipelines' picture before
    their effects, a source. A stand-in the view draws, never in a render
    graph: the render graph's run reads its pipeline's own picture."""

    KIND = "frame"
    INPUTS: ClassVar[dict[str, str]] = {}
    OUTPUT = IMAGE


def says_run(spec) -> bool:
    """Does the section say the free graph's run (a `frame` wire)? Every
    preset loaded on this build does (plan 33 M); one that does not (an
    edit with no preset loaded) has the empty run (R23, plan 33 T7)."""
    return spec is not None and any(w.src == "frame" or w.dst == "fx.image"
                                    for w in getattr(spec, "wires", ()))


def unreached(spec) -> frozenset[str]:
    """The effects, composites and switches of section `spec` that reach
    no sink (`graph.reaches`): drawn faint, never run — with a run or
    without (R23, plan 33 T7: no stack runs what no wire reaches); a
    D1-placed effect sits where it is placed, so it reaches."""
    if spec is None:
        return frozenset()
    got = set(rgraph.reaches(spec)) | {e.name for e in spec.effects if e.placed}
    names = {e.name for e in spec.effects} | {s.name for s in spec.switches}
    names |= {c.name for c in spec.composites()}
    names |= {n for w in spec.wires for n in (w.src, w.node)
              if rgraph.wire_node_kind(n) in MAKER_KINDS}
    return frozenset(n for n in names if n not in got)


def _stand_in(name: str, spec) -> rgraph.Node | None:
    """A render node of the section's unreached `name` for the canvas to
    draw (never built into a graph, never run)."""
    kind = rgraph.wire_node_kind(name)
    if kind == "effect":
        return rgraph.Effect(name, node=name)
    if kind == "switch":
        return rgraph.SwitchNode(name)
    if kind == "composite":
        c = next((c for c in spec.composites() if c.name == name), None)
        return rgraph.Composite(name, blend=c.blend if c is not None else "over")
    return None


MEDIA_MADE = (rgraph.Effect, rgraph.Composite, rgraph.SwitchNode)


def media_made(r) -> bool:
    """Is render node `r` an effect, composite or switch whose picture is
    made of the media alone (plan 33 T6's layout rule): every path back
    from it through its picture inputs starts at a channel or the pattern,
    and there is one. Such a node is a branch of the media and sits in the
    media area, so `media.a → acid.2 → shape.faces` runs left to right."""
    if not isinstance(r, MEDIA_MADE):
        return False
    seen: set[int] = set()
    todo = [r]
    heads = 0
    while todo:
        n = todo.pop()
        if id(n) in seen:
            continue
        seen.add(id(n))
        if isinstance(n, (rgraph.MediaNode, rgraph.PatternNode)):
            heads += 1
            continue
        ins = [x for x in getattr(n, "inputs", {}).values() if x is not None]
        if not ins:
            if n is not r:
                return False            # a scene picture (the frame, the history …)
            continue
        todo.extend(ins)
    return heads > 0


def build(table: Bindings, reg: Registry, router: Router | None = None, devices=None,
          render_graph: rgraph.Graph | None = None, spec=None, *, lanes=None,
          bands: Iterable[str] | None = None, template=None) -> View:
    """The view of `table`, `reg`, `router`, the device registry `devices`
    and the render graph `render_graph` (the renderer's last), with the
    preset's graph `spec` kept on the view. `lanes` are the analyzer's
    lanes this frame, normalised (None: not live); `bands` their names
    (else the Router's published ``lane`` labels); `template` the loaded
    preset's desk template as ``(name, rows)`` (plan 28 N5), None when it
    names none."""
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
                   group: str = "", bipolar: bool = False) -> str:
        key = _lane_key(router, addr)
        if key in src_pins:
            return src_pins[key]
        pin = f"out:{addr}"
        add_port(n, VPort(pin, name, OUT, _port_type(kind), group, addr=addr,
                          bipolar=bipolar))
        src_pins[key] = pin
        return pin

    # ---- the sources: devices, the analyzer, LFOs, modifiers ----
    by_scheme, midi_first = _device_schemes(devices)
    # plan 28 N5: a layered device's nodes by role and layer, and each
    # port's pin on them by (node id, address): the first layer's pins are
    # ``out:<address>`` (so a drag or a Learn reads them as before), every
    # other node's carry its tag (``out:<address>|global``)
    layered: dict[str, dict[str, VNode]] = {}
    lpins: dict[tuple[str, str], str] = {}

    def add_layer_port(n: VNode, addr: str, name: str, kind: str, group: str,
                       layer: str, bipolar: bool = False) -> str:
        k = (n.id, addr)
        if k in lpins:
            return lpins[k]
        first = n.kind == "device" and n.id == f"device:{n.role}"
        if first:
            pin = add_source(n, addr, name, kind, group, bipolar)
            port = n.port(pin)
            if port is not None:
                port.layer = layer
        else:
            tag = n.layer if n.kind == "device" else TEMPLATE
            pin = f"out:{addr}|{tag}"
            add_port(n, VPort(pin, name, OUT, _port_type(kind), group, addr=addr,
                              bipolar=bipolar, layer=layer))
        lpins[k] = pin
        return pin

    for d in (devices or ()):
        for node, ports in device_nodes(d, table):
            n = add_node(node)
            if node.layer:
                layered.setdefault(node.role, {})[node.layer] = n
            for p, group, layer in ports:
                bip = bool(getattr(p, "bipolar", False))
                if node.layer:
                    add_layer_port(n, p.address, p.label, p.kind, group, layer, bip)
                else:
                    add_source(n, p.address, p.label, p.kind, group, bip)

    labels = getattr(router, "labels", {}) if router is not None else {}
    band_names = list(bands) if bands is not None else list(labels.get("lane") or [])
    analyzer = add_node(VNode(ANALYZER, "analyzer", "analyzer"))
    for i, name in enumerate(band_names):
        add_source(analyzer, f"lane:{i}", f"{i} {name}", group="bands")

    # plan 31 G1: a node per bank voice (the LFOs, the envelopes), by id —
    # ids keep their gaps — then the sequencer's one node, a trigger out
    # per lane
    for scheme in BANK_SCHEMES:
        names = list(labels.get(scheme) or [])
        word = "LFO" if scheme == "lfo" else scheme
        for k in bank_ids(router, reg, scheme):
            i = k - 1
            n = add_node(VNode(f"{scheme}.{k}", scheme, names[i] if i < len(names)
                               and names[i] else f"{word} {k}"))
            addr = router.address(scheme, i) if router is not None else f"{scheme}:{i}"
            add_source(n, addr, "out")
    if has_sequencer(router, reg):
        n = add_node(VNode(SEQ, SEQ, "sequencer"))
        for li in range(seqmod.LANES):
            addr = router.address(SEQ, li) if router is not None else f"{SEQ}:{li}"
            add_source(n, addr, f"lane {li + 1}", TRIGGER, group="lanes")

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
        elif base in BANK_SCHEMES:
            scheme_i = router.lane(addr)[1] if router is not None else -1
            owner = nodes.get(f"{base}.{scheme_i + 1}") if scheme_i >= 0 else None
        elif base == SEQ:
            owner = nodes.get(SEQ)
        elif base == modmod.SCHEME:
            owner = nodes.get(modmod.id_of(addr) or "")
        if owner is None and at and role:
            owner = nodes.get(f"device:{role}")
        if owner is None:
            d = by_scheme.get(scheme) or by_scheme.get(base)
            if d is None and base in ("cc", "note", "pitch") and midi_first and not at:
                owner = nodes.get(f"device:{midi_first}")
            elif d is not None:
                owner = nodes.get(f"device:{d.role}")
        if owner is None and base not in NO_DEVICE:
            # plan 28 N5, roles not serials (decision 11): a device this rig
            # lists none for is a grey placeholder named by its role — the
            # row's qualifier, else the desk's first role, else the kind's
            # usual role — its cables dormant until a device of that role
            # comes (the same id, so it takes the placeholder's place)
            who = role if at and role else (
                (getattr(table, "primary_role", lambda: "")() or SCHEME_ROLE[base])
                if base in ("cc", "note", "pitch") else SCHEME_ROLE.get(base, base))
            nid = f"device:{who}"
            owner = nodes.get(nid) or add_node(VNode(nid, "device", who, grey=True,
                                                     status=PLACEHOLDER_STATUS, role=who,
                                                     placeholder=True))
        if owner is None:
            nid = f"source:{scheme}"
            owner = nodes.get(nid) or add_node(VNode(nid, "source", scheme, grey=True,
                                                     status="no device publishes it"))
        return add_source(owner, addr, addr.partition(":")[2] or addr)

    # plan 28 N5: the loaded preset's desk template, and which live
    # preset-layer rows are still its own (an override is not)
    tmpl = template_rows(template)
    tmpl_keys = {_row_key(t) for t in tmpl[1]} if tmpl else set()
    tmpl_node: VNode | None = None
    if tmpl is not None:
        role = (getattr(table, "primary_role", lambda: "")() or midi_first
                or SCHEME_ROLE["cc"])
        dev = nodes.get(f"device:{role}")
        tmpl_node = add_node(VNode(f"{TEMPLATE}:{tmpl[0]}", TEMPLATE, f"template {tmpl[0]}",
                                   grey=dev is None or dev.grey, role=role,
                                   layer=PRESET_LAYER,
                                   status=f"desk template · {len(tmpl[1])} rows · + shows "
                                          "them as cables; an edit is the preset's override"))
        names = {p.addr: p.name for p in (dev.ports if dev is not None else ())}
        groups = {p.addr: p.group for p in (dev.ports if dev is not None else ())}
        for t in tmpl[1]:
            add_layer_port(tmpl_node, t.source, f"{names.get(t.source, t.bare)} → {t.target}",
                           TRIGGER if t.kind == "note" else VALUE,
                           groups.get(t.source, ""), PRESET_LAYER)

    def row_pin(b: Binding, shadowed: bool = False) -> tuple[str, str]:
        """(the pin a desk row's cable leaves from, the subgraph it is
        inside): the node of the layer it belongs to on a layered desk —
        an invariant row (layer None) the first node's, a preset-layer row
        still the template's the template node's — else `source_pin`. A
        layered row `shadowed` by an invariant control (D6: it never acts)
        leaves that control's port on the first node, so an invariant
        control is a port there only."""
        if not b.is_midi:
            return source_pin(b.source), ""
        role_of = getattr(table, "role_of", None)
        role = (role_of(b) if role_of is not None else "") or midi_first or ""
        mine = layered.get(role)
        if tmpl_node is not None and b.layer == PRESET_LAYER and _row_key(b) in tmpl_keys \
                and role == tmpl_node.role:
            n, inside = tmpl_node, tmpl_node.id
        elif mine is None:
            return source_pin(b.source), ""
        else:
            layer = PRESET_LAYER if shadowed else (b.layer or PRESET_LAYER)
            n = mine.get(layer) or mine[PRESET_LAYER]
            inside = ""
        pin = lpins.get((n.id, b.source))
        if pin is None:
            kind = TRIGGER if b.kind == "note" else VALUE
            pin = add_layer_port(n, b.source, b.bare, kind, INVARIANT if shadowed else "",
                                 "" if b.layer is None or shadowed else b.layer)
        return pin, inside

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
    # plan 32 T10: the eight channels are source nodes whatever the render
    # graph holds — a channel nothing reads this frame has no node there,
    # and one that is both the backdrop and a wire's start has two
    # (`media.a`, `media.a(wire)`): each is drawn as its channel's one node
    chans: dict[str, rgraph.MediaNode] = {}
    for r in rnodes:
        if isinstance(r, rgraph.MediaNode) and (r.channel not in chans
                                                or r.name == rgraph.media_name(r.channel)):
            chans[r.channel] = r
    for c in rgraph.MEDIA_CHANNELS:
        name = rgraph.media_name(c)
        ctx.names.add(name)
        r = chans.get(c) or rgraph.MediaNode(name, c)       # a stand-in: never drawn into
        n = add_node(VNode(f"render:{name}", "render", name, ref=r))
        add_port(n, VPort(f"rout:{name}", r.OUTPUT, OUT, r.OUTPUT))
    # plan 33 U: the pattern and the backdrop always (wire ends before
    # anything is wired there), `frame` beside the pipelines' ends, and a
    # stand-in for each unreached node of the section (`unreached`) — none
    # of them ever drawn into
    gone = unreached(spec)
    stand: dict[str, rgraph.Node] = {}
    if "pattern" not in ctx.names:
        stand["pattern"] = rgraph.PatternNode("pattern")
    if "backdrop" not in ctx.names:
        stand["backdrop"] = rgraph.BackdropNode("backdrop")
    # (`frame` while the render graph's wiring says its run, as every
    # loaded preset's does: one that says none — no preset loaded, a graph
    # put together by hand — has the empty run, R23, plan 33 T7, and its
    # pipelines are drawn from their pictures straight to their ends)
    ends = [r for r in rnodes if isinstance(r, rgraph.Fx)]
    wired_run = getattr(getattr(render_graph, "wiring", None), "run", None) is not None
    if ends and wired_run:
        stand["frame"] = FrameNode("frame")
    built_fx = {r.effect for r in rnodes if isinstance(r, rgraph.Effect)}
    for name in sorted(gone):
        if name in ctx.names or name in built_fx:
            continue
        r = _stand_in(name, spec)
        if r is not None:
            stand[name] = r
    ctx.names |= set(stand)
    # the section's spec name → the drawn node standing for it (an effect
    # by its scene pipeline's node, a channel by its one node)
    by_name: dict[str, rgraph.Node] = {}
    for r in (*rnodes, *stand.values()):
        if isinstance(r, rgraph.Effect):
            if r.name == r.effect or r.effect not in by_name:
                by_name[r.effect] = r
        elif isinstance(r, rgraph.MediaNode):
            by_name.setdefault(rgraph.media_name(r.channel), r)
        elif isinstance(r, rgraph.Fx):
            by_name.setdefault("fx", r)
        else:
            by_name.setdefault(r.name, r)
    for c in rgraph.MEDIA_CHANNELS:
        by_name.setdefault(rgraph.media_name(c), nodes[f"render:{rgraph.media_name(c)}"].ref)
    # a stand-in's inputs are the section's wires into it (its cables in,
    # and what the layout reads its picture as made of: `media_made`)
    for w in (spec.wires if spec is not None else ()):
        r, src = stand.get(w.node), by_name.get(w.src)
        if r is not None and src is not None and w.port in r.INPUTS and w.node in gone:
            r.inputs[w.port] = src
    # the run's head: each pipeline's first cable of its run leaves `frame`,
    # and the pipeline's own picture feeds `frame` (plan 33 U)
    heads: dict[int, rgraph.Node] = {}          # id(first of the run) → the picture
    run_set = set(getattr(render_graph, "run", ()) or ())
    if "frame" in stand:
        for end in ends:
            prev, n = end, end.inputs.get("image")
            while (isinstance(n, rgraph.Effect) and n.placed is None
                   and n.effect in run_set):
                prev, n = n, n.inputs.get("image")
            if n is not None:
                heads[id(prev)] = n
    for r in (*rnodes, *stand.values()):
        if isinstance(r, rgraph.MediaNode):
            continue
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
        elif (p.group in BANK_SCHEMES and pid.startswith(f"{p.group}.")
              and pid.split(".")[1].isdigit()):
            owner = (nodes.get(f"{p.group}.{pid.split('.')[1]}")
                     or _group_node(nodes, p.group, add_node))
        elif p.group == seqmod.GROUP and SEQ in nodes:
            owner = nodes[SEQ]
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
    inv_rows = table.invariant_rows() if hasattr(table, "invariant_rows") else []
    for b in setters:
        # a layered row on an invariant control never acts (D6)
        shadowed = (b.is_midi and b.layer is not None and bool(inv_rows)
                    and table.is_invariant(b, inv_rows))
        src, inside = row_pin(b, shadowed)
        dst = f"{BASE}:{b.target}"
        p = reg.get(b.target)
        typ = TRIGGER if (b.op in TRIGGER_OPS or pin_type.get(src) == TRIGGER) else VALUE
        layer = f"  {b.layer} layer" if b.layer else ""
        if inside:
            layer += f"  (desk template {tmpl[0]})"
        view.cables.append(VCable(cable_id(f"set:{b.source}>{b.target}"), src, dst, typ,
                                  ref=b, kind="setter",
                                  off=not b.enabled or p is None or shadowed,
                                  label=f"{b.op}{layer}" + ("  (under an invariant control)"
                                                            if shadowed else ""),
                                  addr=b.source, inside=inside))
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
    # plan 31 G1: each sequencer lane's envelope binding, a cable from its
    # lane's pin to the envelope's `fire` — only for a lane that can fire
    # (a step on, or the sequencer running); dormant while it is stopped
    # or the lane muted
    seq_node = nodes.get(SEQ)
    if seq_node is not None:
        running = seq_running(reg)
        for li, env, on, mute in seq_lanes(reg):
            dst = f"{BASE}:{envmod.GROUP}.{env}.fire"
            src = src_pins.get(_lane_key(router, f"{SEQ}:{li}"))
            if src is None or dst not in view.pins or not (on or running):
                continue
            why = "  (muted)" if mute else "" if running else "  (stopped)"
            view.cables.append(VCable(cable_id(f"lane:{li}>{env}"), src, dst, TRIGGER,
                                      ref=(li, env), kind="lane", off=mute or not running,
                                      label=f"lane {li + 1} fires env {env}{why}",
                                      addr=seq_node.port(src).addr))
    fed: list[str] = []
    for r in (*rnodes, *stand.values()):
        for port, src in r.inputs.items():
            if src is None:
                continue
            if port == "image" and heads.get(id(r)) is src:
                # plan 33 U: the run's first cable is the section's
                # `frame → <first>.image`; the picture feeds `frame`
                f = stand["frame"]
                view.cables.append(VCable(f"wire:frame>{r.name}/{port}", "rout:frame",
                                          f"rin:{r.name}/{port}", IMAGE, ref=(f, r, port),
                                          kind="render"))
                if src.name not in fed:
                    fed.append(src.name)
                continue
            out = (rgraph.media_name(src.channel) if isinstance(src, rgraph.MediaNode)
                   else src.name)          # a channel's every node is its one node's out
            view.cables.append(VCable(f"wire:{src.name}>{r.name}/{port}", f"rout:{out}",
                                      f"rin:{r.name}/{port}", r.INPUTS[port],
                                      ref=(src, r, port), kind="render"))
    for name in fed:
        view.cables.append(VCable(f"{FEEDS}:{name}>frame", f"rout:{name}",
                                  stub_in("render:frame"), IMAGE, kind=FEEDS,
                                  label=f"{name} is frame here: the picture this pipeline's "
                                        "run starts from"))

    # ---- what is patched; the nodes in column order ----
    hit = {c.src_port for c in view.cables} | {c.dst_port for c in view.cables}
    for n in nodes.values():
        for port in n.ports:
            port.patched = any(pin in hit for pin in port.pins)
    for c in view.cables:                       # plan 28 N7: each node's cable count
        ends = {node_of(view, c.src_port), node_of(view, c.dst_port)}
        for nid in ends:
            if nid in nodes:
                nodes[nid].wires += 1
    # plan 28 N9: each node's area, and which sit with nothing in and out
    named = {b.scale for b in routes if b.scale} | {b.when for b in routes if b.when}
    # review round 1: an effect switched off whose nodes no value cable
    # reaches is idle (its render cables do not count: the chain draws a
    # through wire over it)
    cabled: set[str] = set()
    for c in view.cables:
        if c.kind in ("render", FEEDS):
            continue
        for nid in (view.pins.get(c.src_port, ("",))[0], view.pins.get(c.dst_port, ("",))[0]):
            ref = nodes[nid].ref if nid in nodes else None
            if isinstance(ref, rgraph.Effect):
                cabled.add(ref.effect)
    for n in nodes.values():
        n.area = area_of(n)
        # plan 33 U: an unreached node is drawn faint, and so never idle —
        # it was just added, or it waits to be wired in
        ref = n.ref
        n.faint = n.kind == "render" and isinstance(ref, MEDIA_MADE) and (
            (ref.effect if isinstance(ref, rgraph.Effect) else ref.name) in gone)
        n.idle = not n.faint and (is_idle(n, macros, named) or (
            n.kind == "render" and effect_off(n, reg) and n.ref.effect not in cabled) or (
            channel_empty(n, reg)))
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


def refresh(view: View, reg: Registry, router: Router | None, lanes=None,
            collapsed: Callable[[str], bool] | None = None) -> None:
    """This frame's readings on an already built view: each source port's
    and each cable's reading, each param port's effective value, and which
    cables are dormant (`off`, or a source not live), and each route's
    effective depth and words (a macro's depth subscriber turning, a
    depth dragged on ROUTING: `key` leaves the values out, so neither
    rebuilds the view). Cheap: no structure changes. A node `collapsed`
    says true for (plan 28 N7) reads only what its lines show — its
    patched ports, its outputs and a macro's knob — not every port."""
    table = getattr(router, "table", None) if router is not None else None
    cut = set(getattr(router, "patch_cut", ()) or ()) if router is not None else set()
    layer_of = getattr(table, "layer_of", None)
    for n in view.nodes:
        if n.layer and layer_of is not None:      # plan 28 N5: the latch, read each frame
            up = layer_of(n.role or None)
            n.up = up == n.layer
            for port in n.ports:
                port.up = not port.layer or port.layer == up
        shut = collapsed is not None and n.kind != "macro" and collapsed(n.id)
        for port in n.ports:
            if shut and not port.patched and port.direction != OUT:
                continue
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
        if hit is not None and (hit[0].grey or (hit[1] is not None and not hit[1].up)):
            grey = True                  # a lost device, or a desk layer that is down
        c.dormant = c.off or grey or (c.kind != "sub" and c.live is None)


def key(table: Bindings, reg: Registry, router: Router | None, devices,
        render_graph, spec) -> tuple:
    """What `build` is made of, cheaply compared each frame: the rows (by
    identity and the fields that make cables), the macros' and the
    modifiers' serials, the registry's add / remove serial, each device's
    status and port count, the render graph and the spec, every effect's
    on switch (an off effect is idle: review round 1). The page builds
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
            tuple(labels.get("lfo") or ()), tuple(labels.get("env") or ()),
            frozenset(getattr(router, "patch_cut", ()) or ()) if router is not None else (),
            effect_switches(reg), seq_key(reg), channel_bins(reg))


def seq_key(reg: Registry) -> tuple:
    """What the sequencer's binding cables are made of (plan 31 G1), for
    `key`: each lane's envelope, whether a step is on and its mute, and the
    transport — a step toggled from the grid or the APC40 rebuilds the view
    only when it moves a lane between empty and not."""
    if f"{seqmod.GROUP}.run" not in reg:
        return ()
    return (seq_running(reg), tuple(seq_lanes(reg)))


# ---------------------------------------------------------------- layout

# plan 28 N9 — the canvas organised by concern (the owner's decision of
# 2026-10-20: "all things audio need to live in one area; all things
# geometry … another; all things shader … another"). Five areas, left to
# right, so the wires read one way: the controllers, the audio (the
# analyzer is a source: what the music says, read by the modulation and
# the look), the modulation (the LFOs, the modifiers, the macros), then
# the two the sources feed — the geometry and the shaders, the render
# graph's own order (the shape is drawn by the scene, the scene feeds the
# effects, the effects the outputs). A group no area claims goes to the
# small `OTHER` area, stacked under the audio in its column.
#
# Plan 32 T10 adds a sixth, *media*, between the modulation and the
# geometry: the eight channels are sources of pictures (what the folder
# and the feeds say), read by the shaders (an output, an effect's aux, the
# backdrop under the scene) and by the faces; the backdrop's node with them.
CONTROLLERS, AUDIO, MODULATION, MEDIA, GEOMETRY, SHADERS = (
    "controllers", "audio", "modulation", "media", "geometry", "shaders")
OTHER = "other"
AREAS = (CONTROLLERS, AUDIO, MODULATION, MEDIA, GEOMETRY, SHADERS)   # left to right
SHARES = {OTHER: AUDIO}       # an area drawn under another's, in its column
ORDER = (CONTROLLERS, AUDIO, OTHER, MODULATION, MEDIA, GEOMETRY, SHADERS)

# the one table: a node's area by its kind, a group node by its id
# (``group:<param group>``), a render node by its class (or a base class)
AREA: dict[str, str] = {
    # by kind
    "device": CONTROLLERS, "source": CONTROLLERS, "template": CONTROLLERS,
    "analyzer": AUDIO,
    "lfo": MODULATION, "env": MODULATION, SEQ: MODULATION,
    "modifier": MODULATION, "macro": MODULATION,
    "output": SHADERS,
    # a group node, by its param group
    "group:band": AUDIO, "group:bands": AUDIO, "group:tempo": AUDIO,
    "group:master": AUDIO, "group:audio": AUDIO, "group:scene": AUDIO,
    "group:lfo": MODULATION, "group:mod": MODULATION, "group:macro": MODULATION,
    "group:env": MODULATION, "group:seq": MODULATION,
    "group:view": GEOMETRY, "group:rot": GEOMETRY, "group:pattern": GEOMETRY,
    "group:camera": GEOMETRY, "group:eye": GEOMETRY, "group:ghost": GEOMETRY,
    "group:hands": GEOMETRY, "group:cloud": GEOMETRY,
    "group:fx": SHADERS, "group:dream": SHADERS, "group:output": SHADERS,
    "group:overlay": SHADERS,
    "group:media": MEDIA, "group:backdrop": MEDIA, "group:switch": MEDIA,
    # a render node, by its class: the geometry and what draws it
    f"render:{EYE}": GEOMETRY,
    "Shape": GEOMETRY, "Hands": GEOMETRY, "PointCloud": GEOMETRY, "Scene": GEOMETRY,
    "HandsLayer": GEOMETRY, "Readout": GEOMETRY, "Cover": GEOMETRY,
    # the media channels (plan 32 T10), and (plan 33 U) the pictures made
    # beside them: the backdrop they lie under the scene as, the pattern the
    # faces draw, a switch picking one of them — and any effect or
    # composite made of the media alone (`media_made`, by `area_of`)
    "MediaNode": MEDIA, "BackdropNode": MEDIA, "PatternNode": MEDIA, "SwitchNode": MEDIA,
    # …and the pictures it goes through: (plan 33 U) the run from `frame`
    # to the pipeline's end (`fx`)
    "History": SHADERS, "Capture": SHADERS, "Effect": SHADERS, "Fx": SHADERS,
    "Composite": SHADERS, "Output": SHADERS, "FrameNode": SHADERS,
}
TITLES = {CONTROLLERS: "CONTROLLERS", AUDIO: "AUDIO", OTHER: "OTHER",
          MODULATION: "MODULATION", MEDIA: "MEDIA", GEOMETRY: "GEOMETRY",
          SHADERS: "SHADERS"}
# a title too long for its room at the floor size (review round 1)
SHORT_TITLES = {CONTROLLERS: "CTRL", AUDIO: "AUD", OTHER: "OTH", MODULATION: "MOD",
                MEDIA: "MED", GEOMETRY: "GEO", SHADERS: "SHD"}

COL_W = 260.0          # canvas units between two columns
ROW_H = 22.0           # one port line
HEAD_H = 34.0          # a node's title and padding
GAP = 28.0             # between two nodes of a column
TITLE_H = 64.0         # an area's title, above its first node
IDLE_H = HEAD_H        # an area's idle line


def area_of(n: VNode) -> str:
    """The area node `n` is laid out in (`AREA`): a group node by its id, a
    render node by its class or a base of it (a render class no row names
    is a shader: it is in the picture's chain), every other node by its
    kind; a node the table does not name is `OTHER`. Plan 33 T6: an
    effect, composite or switch made of the media alone (`media_made`) is
    the media's."""
    if n.kind == "group" or n.id == f"render:{EYE}":
        return AREA.get(n.id, OTHER)
    if n.kind in ("render", "output") and n.ref is not None:
        if media_made(n.ref):
            return MEDIA
        for cls in type(n.ref).__mro__:
            if cls.__name__ in AREA:
                return AREA[cls.__name__]
        return SHADERS
    return AREA.get(n.kind, OTHER)


# which kinds may sit idle (`is_idle`): a node of any other kind is always
# drawn — the analyzer, a modifier just picked (it is dropped onto a cable
# next), a render node, a connected device, a placeholder (it has rows)
IDLE_KINDS = ("macro", "lfo", "env", SEQ, "group", "device")
IDLE_NOUNS = {"macro": ("idle macro", "idle macros"), "lfo": ("idle LFO", "idle LFOs"),
              "env": ("idle envelope", "idle envelopes"),
              SEQ: ("idle sequencer", "idle sequencers"),
              "group": ("idle param group", "idle param groups"),
              "effect": ("off effect", "off effects"),
              "channel": ("empty channel", "empty channels"),
              "off": ("off device", "off devices"), "lost": ("lost device", "lost devices")}
# plan 32 T10: the backdrop's node (its channel picker, alpha and history
# switch) is the media area's one setting: drawn with nothing patched, so
# the area always says what is under the scene
ALWAYS_DRAWN = ("group:backdrop",)
NOUN_ORDER = ("macro", "lfo", "env", SEQ, "effect", "channel", "group", "off", "lost")


def effect_off(n: VNode, reg: Registry | None) -> bool:
    """Is render node `n` an effect switched off (`fx.<effect>.on` false
    when the view is built)? Not `Effect.on(frame)`: a mix at 0 or the
    stack bypassed would reshape the chain mid-show."""
    if not isinstance(n.ref, rgraph.Effect) or reg is None:
        return False
    p = reg.get(f"fx.{n.ref.effect}.on")
    return p is not None and not bool(p.value)


def channel_empty(n: VNode, reg: Registry | None) -> bool:
    """Is node `n` a media channel with nothing to show and nothing to say
    (plan 32 T10): no cable at either end, no param of it named by a
    route, and every entry of its bin empty (`reg.media`, the channels the
    ``media.*`` params write)? Such a channel sits on its area's idle line,
    as an unused macro does; one with a source in its bin is drawn though
    nothing reads it yet — it is what a wire would start from."""
    if not isinstance(n.ref, rgraph.MediaNode) or n.wires:
        return False
    if any(p.patched for p in n.ports):
        return False
    media = getattr(reg, "media", None)
    ch = getattr(media, "channels", {}).get(n.ref.channel) if media is not None else None
    return ch is None or not any(ch.bin)


def channel_bins(reg: Registry) -> tuple:
    """Which channels hold anything, for `key`: a bin filled or emptied on
    the MEDIA page rebuilds the view (an empty channel is idle)."""
    media = getattr(reg, "media", None)
    chans = getattr(media, "channels", None) or {}
    return tuple(c for c, ch in chans.items() if any(getattr(ch, "bin", ())))


def effect_switches(reg: Registry) -> tuple:
    """Every effect's on switch, for `key`: turning one on or off from the
    FX page rebuilds the view (an off effect with no cable is idle)."""
    group = getattr(reg, "group", None)
    params = group("fx") if group is not None else ()
    return tuple((p.id, bool(p.value)) for p in params if p.id.endswith(".on"))


def is_idle(n: VNode, macros: Mapping[str, Macro] | None = None,
            named: Iterable[str] = ()) -> bool:
    """Does node `n` sit with nothing in and nothing out — not drawn by
    default (plan 28 N9)? No cable starts or ends on it (`VNode.wires`), no
    route names one of its params as its `scale` or its sources as its
    `when` (`named`: neither is drawn as a cable), and: a macro has no
    label and no subscriber (an idle knob of the rig's eight — the picker
    names one to bring it on); an LFO and a group node are idle on that
    alone; a device only while it is lost or off (grey, not a placeholder:
    a connected device is drawn even unmapped — it says the rig has it).
    An effect switched off is idle by `build`'s own rule (`effect_off`,
    review round 1): its render cables do not count, a value cable on any
    node of that effect does."""
    if n.kind not in IDLE_KINDS or n.wires or n.id in ALWAYS_DRAWN:
        return False
    names = set(named)
    if any(p.param in names or p.addr in names for p in n.ports):
        return False
    if n.kind == "macro":
        m = (macros or {}).get(n.id)
        return m is None or m.empty
    if n.kind == "device":
        return n.grey and not n.placeholder
    return True


def _idle_noun(n: VNode) -> str:
    if isinstance(n.ref, rgraph.MediaNode):
        return "channel"
    if n.kind == "render":
        return "effect"
    if n.kind == "device":
        return "off" if n.status.rpartition(" · ")[2].strip() == "off" else "lost"
    return n.kind


def idle_words(nodes: Iterable[VNode]) -> str:
    """An idle line's words: how many of each kind ("8 idle macros · 3 idle
    LFOs", "10 off effects", "1 off device")."""
    counts: dict[str, int] = {}
    for n in nodes:
        k = _idle_noun(n)
        counts[k] = counts.get(k, 0) + 1
    words = []
    for kind in NOUN_ORDER:
        k = counts.get(kind, 0)
        if k:
            one, many = IDLE_NOUNS[kind]
            words.append(f"{k} {one if k == 1 else many}")
    return " · ".join(words)

def idle_id(area: str) -> str:
    """The page's id for an area's idle line (no node of the view has it)."""
    return f"idle:{area}"


SHADER_ROW = 4         # the shaders' chain wraps into rows of this many columns (Z rows)
THROUGH = "through"    # a display-only wire over a run of hidden (off) effects


def throughs(view: View, shown: Callable[[VNode], bool]) -> list[VCable]:
    """The display-only wires over the runs of hidden render nodes (review
    round 1: an off effect with no cable is idle): from a drawn node's
    output, through every hidden node its render cables reach, to the
    input of each drawn node at the end of the run — one wire per (start
    pin, end pin), kind `THROUGH`, no `ref`. Not a render edge: nothing
    deletes it, nothing is inserted into it."""
    out_of: dict[str, list[VCable]] = {}
    for c in view.cables:
        if c.kind == "render":
            out_of.setdefault(node_of(view, c.src_port), []).append(c)
    made: dict[str, VCable] = {}
    for c in view.cables:
        if c.kind != "render":
            continue
        s, d = view.node(node_of(view, c.src_port)), view.node(node_of(view, c.dst_port))
        if s is None or d is None or not shown(s) or shown(d):
            continue
        stack, seen = [(d, (d.label,))], set()
        while stack:
            m, path = stack.pop()
            if m.id in seen:
                continue
            seen.add(m.id)
            for c2 in out_of.get(m.id, ()):
                e = view.node(node_of(view, c2.dst_port))
                if e is None:
                    continue
                if not shown(e):
                    stack.append((e, (*path, e.label)))
                    continue
                cid = f"{THROUGH}:{c.src_port}>{c2.dst_port}"
                if cid not in made:
                    k = len(path)
                    made[cid] = VCable(cid, c.src_port, c2.dst_port, c.type, kind=THROUGH,
                                       label=f"through {k} off effect{'' if k == 1 else 's'}: "
                                             f"{', '.join(path)}")
    return list(made.values())


def _links(view: View, cables: Iterable[VCable]) -> list[tuple[str, str]]:
    return [(node_of(view, c.src_port), node_of(view, c.dst_port)) for c in cables]


def _depths(nodes: list[VNode], links: Iterable[tuple[str, str]]) -> dict[str, int]:
    """Each node's depth inside its own area: 0, or one more than the
    deepest node of the same area with a cable into it — the longest path
    over the area's own cables, a loop's closing cable left out (a DFS in
    view order drops each edge back onto its stack). For the render nodes
    that is their depth in the render graph; for the modulation an LFO or
    a macro fed by nothing is 0, a modifier one past what feeds it."""
    area = {n.id: n.area for n in nodes}
    succ: dict[str, list[str]] = {}
    for a, b in links:
        if a != b and a in area and b in area and area[a] == area[b]:
            succ.setdefault(a, []).append(b)
    dag: dict[str, list[str]] = {k: [] for k in area}
    state: dict[str, int] = {}
    post: list[str] = []
    for root in area:
        if root in state:
            continue
        state[root] = 1
        stack = [(root, iter(succ.get(root, ())))]
        while stack:
            v, it = stack[-1]
            for w in it:
                if state.get(w) == 1:          # back onto the stack: a loop's cable
                    continue
                dag[v].append(w)
                if w not in state:
                    state[w] = 1
                    stack.append((w, iter(succ.get(w, ()))))
                    break
            else:
                state[v] = 2
                post.append(v)
                stack.pop()
    depth = dict.fromkeys(area, 0)
    for v in reversed(post):
        for w in dag[v]:
            depth[w] = max(depth[w], depth[v] + 1)
    return depth


def _grid(view: View, opened: set, extra: Iterable[VCable]):
    """The canvas's grid: (column, row) for each node laid out by depth —
    every drawn node but an idle one shown under its line — each area's
    span in columns and its first column. An area's columns are its
    depths (`_depths`, over the drawn nodes' cables and the through
    wires); the shaders' outputs one past their deepest node, and their
    depths wrapped into rows of `SHADER_ROW` (Z order: every row left to
    right). The areas follow one another in `AREAS`; `OTHER` takes the
    audio's first column."""
    def gridded(n: VNode) -> bool:
        return not n.idle or (n.area in opened and n.kind == "render")

    nodes = [n for n in view.nodes if n.area and gridded(n)]
    ids = {n.id for n in nodes}
    links = [(a, b) for a, b in _links(view, (*view.cables, *extra))
             if a in ids and b in ids]
    depth = _depths(nodes, links)
    sh = [n for n in nodes if n.area == SHADERS]
    if any(n.kind == "output" for n in sh):
        last = max((depth[n.id] for n in sh if n.kind != "output"), default=-1) + 1
        for n in sh:
            if n.kind == "output":
                depth[n.id] = last
    local: dict[str, tuple[int, int]] = {}
    for n in nodes:
        d = depth[n.id]
        if n.area == SHADERS:
            local[n.id] = (d % SHADER_ROW, d // SHADER_ROW)
        elif n.area == OTHER:
            local[n.id] = (0, 0)
        else:
            local[n.id] = (d, 0)
    present = {n.area for n in view.nodes if n.area}
    width: dict[str, int] = {a: 1 for a in present}
    for n in nodes:
        width[n.area] = max(width[n.area], local[n.id][0] + 1)
    first: dict[str, int] = {}
    col = 0
    for a in AREAS:
        if a in present or any(SHARES.get(b) == a for b in present):
            first[a] = col
            col += width.get(a, 1)
    for a, under in SHARES.items():
        if a in present:
            first[a] = first.get(under, 0)
            width[a] = 1
    cols = {n.id: first[n.area] + local[n.id][0] for n in nodes}
    rows = {n.id: local[n.id][1] for n in nodes}
    return cols, rows, {a: width[a] for a in present}, first


def _columns(view: View, render_graph=None) -> None:
    """Each node's column on the default canvas (every idle line shut):
    `_grid`'s, an idle node its area's first column."""
    for n in view.nodes:
        if not n.area:
            n.area = area_of(n)
    shown = (lambda n: not n.idle)
    cols, _, _, first = _grid(view, set(), throughs(view, shown))
    for n in view.nodes:
        n.column = cols.get(n.id, first.get(n.area, 0))


@dataclass
class Layout:
    """`layout`'s answer: a position for each node (`nodes`), each area's
    title (`titles`, over its first column), each area's idle line
    (`lines`) and the idle nodes it stands for (`idle`); how many columns
    each area spans (`spans`); each laid-out node's grid column (`cols`)
    and row (`rows`: only the shaders wrap); the through wires over the
    hidden effects (`throughs`)."""

    nodes: dict[str, tuple[float, float]] = field(default_factory=dict)
    titles: dict[str, tuple[float, float]] = field(default_factory=dict)
    lines: dict[str, tuple[float, float]] = field(default_factory=dict)
    idle: dict[str, list[str]] = field(default_factory=dict)
    spans: dict[str, int] = field(default_factory=dict)
    cols: dict[str, int] = field(default_factory=dict)
    rows: dict[str, int] = field(default_factory=dict)
    throughs: list[VCable] = field(default_factory=list)


# plan 33 T6: the sinks of the media and the geometry a picture is taken
# back into — the faces, the pattern's layer, the backdrop, a switch
TAKEN_BACK = (rgraph.Shape, rgraph.PatternNode, rgraph.BackdropNode, rgraph.SwitchNode)


def returns(view: View, lay: Layout) -> set[str]:
    """The ids of the wires that run back by design: inside the shaders,
    from one row of the wrapped chain to a later one (the row's last
    output to the next row's first input); and (plan 33 T6) a picture the
    scene made, taken back from the shaders into a sink that sits left of
    them (`TAKEN_BACK`: `history → acid.2 → switch.in1`; into the faces,
    the pattern or the backdrop such a picture is a loop — the scene draws
    them — and is never built) — a picture made of the media alone sits
    with the media (`media_made`), so its wire runs right. Every other
    wire runs right."""
    out = set()
    for c in (*view.cables, *lay.throughs):
        a, b = view.node(node_of(view, c.src_port)), view.node(node_of(view, c.dst_port))
        if a is None or b is None:
            continue
        if a.area == b.area == SHADERS and lay.rows.get(b.id, 0) > lay.rows.get(a.id, 0) or (a.area == SHADERS and b.area in (MEDIA, GEOMETRY)
              and isinstance(b.ref, TAKEN_BACK) and c.type == IMAGE):
            out.add(c.id)
    return out

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


def height(n: VNode, full: bool = False, folds=frozenset(), collapsed: bool = False) -> float:
    """A node's height as auto_layout stacks it: its title, the ports it
    shows (`visible`) and, expanded, a line per port group — or, while it
    is `collapsed` (plan 28 N7), its title and its lines (`summary`)."""
    if collapsed:
        return HEAD_H + ROW_H * len(summary(n))
    rows = len(visible(n, full, folds))
    if grouped(n, full):
        rows += len({p.group for p in n.ports})
    return HEAD_H + ROW_H * rows


def layout(view: View, placed: Mapping[str, Any] | None = None,
           expanded: Callable[[str], bool] | None = None,
           folds=frozenset(),
           collapsed: Callable[[str], bool] | None = None,
           idle_open: Iterable[str] = ()) -> Layout:
    """The canvas laid out by area (plan 28 N9): area by area in `ORDER`,
    every node `placed` does not hold stacked down its grid column
    (`_grid`: an area's depths left to right, the shaders wrapped into
    rows — each row starting under the tallest column of the one before),
    the columns starting under a row for the areas' titles; `OTHER`
    titled and stacked under the audio in its column. An area's idle
    nodes (`VNode.idle`) take no room: its idle line goes under its nodes
    in its first column and they sit at it — unless the area is in
    `idle_open`, when they are laid out (an off effect in its place in
    the chain, any other under the line). The nodes already placed keep
    their positions and take no room here (a tidy passes none).
    `expanded(node id)` says which nodes show every port (default none)
    and `folds` which of their groups are folded, so an expanded node
    pushes the column under it down instead of overlapping. `collapsed(node
    id)` (plan 28 N7: the page's default, every node) says which nodes draw
    only their title and lines; such a node takes that much room whatever
    `expanded` says."""
    placed = placed or {}
    opened = set(idle_open)
    thr = throughs(view, lambda n: not n.idle or n.area in opened)
    cols, rows, spans, first = _grid(view, opened, thr)
    out = Layout(spans=spans, cols=cols, rows=rows, throughs=thr)
    tops: dict[int, float] = {}

    def put(n: VNode, col: int) -> None:
        if n.id in placed:
            return
        full = bool(expanded(n.id)) if expanded is not None else False
        shut = bool(collapsed(n.id)) if collapsed is not None else False
        # an expanded node on the N7 page has its all ports / patched only line
        chip = ROW_H if collapsed is not None and not shut and n.kind != TEMPLATE else 0.0
        out.nodes[n.id] = (col * COL_W, tops[col])
        tops[col] += height(n, full, folds, shut) + chip + GAP

    for area in ORDER:
        mine = [n for n in view.nodes if n.area == area]
        if not mine:
            continue
        f = first[area]
        span = range(f, f + spans.get(area, 1))
        tops[f] = tops[f] + TITLE_H if f in tops else TITLE_H   # a second area: under the first
        for c in span:
            tops.setdefault(c, TITLE_H)
        out.titles[area] = (f * COL_W, tops[f] - TITLE_H)
        grid = [n for n in mine if n.id in cols]
        for r in range(max((rows[n.id] for n in grid), default=0) + 1):
            if r:                                   # a wrapped row: under the tallest
                t = max(tops[c] for c in span)
                for c in span:
                    tops[c] = t
            for n in grid:
                if rows[n.id] == r:
                    put(n, cols[n.id])
        idle = [n for n in mine if n.idle]
        if not idle:
            continue
        out.idle[area] = [n.id for n in idle]
        line = (f * COL_W, tops[f])
        out.lines[area] = line
        tops[f] += IDLE_H + GAP
        for n in idle:
            if n.id in cols:
                continue
            if area in opened:
                put(n, f)
            elif n.id not in placed:
                out.nodes[n.id] = line
    for n in view.nodes:                    # a node of no area (a hand-made view)
        if n.area not in ORDER:
            tops.setdefault(n.column, 0.0)
            put(n, n.column)
    return out

def auto_layout(view: View, placed: Mapping[str, Any] | None = None,
                expanded: Callable[[str], bool] | None = None,
                folds=frozenset(),
                collapsed: Callable[[str], bool] | None = None,
                idle_open: Iterable[str] = ()) -> dict[str, tuple[float, float]]:
    """A position for every node `placed` does not hold: `layout`'s nodes
    (its titles and idle lines left out)."""
    return layout(view, placed, expanded, folds, collapsed, idle_open).nodes


def home(n: VNode) -> str:
    """Which layout map holds node `n`'s position: the preset's for what
    a preset holds (modifiers, macros, the render nodes, a performance
    group's node, the desk template it names, and since plan 31 the LFOs,
    the envelopes and the sequencer: a bank's membership is preset
    content), the show's for the rig (devices — a layered desk's every
    node, a placeholder — sources, the analyzer, the outputs, a session
    group's node)."""
    if n.kind in ("modifier", "macro", "render", TEMPLATE, *BANK_SCHEMES, SEQ):
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


# ---------------------------------------------------------------- a legible graph (plan 28 N7)
#
# The owner's decisions of 2026-10-20: **every node starts collapsed** — its
# title and at most five short lines (`summary`), no row per port — and
# **one wire between two nodes while either end is collapsed**, however
# many params are mapped between them (`VBundle`, `wiring`); the real
# cables appear when both ends are expanded. A collapsed node has one pin
# pair, an ``in`` and an ``out`` stub (`stub_in`, `stub_out`) on its title
# line: the bundles end there, and so does a render cable (image /
# geometry / mask: few, kept one wire each) whose end is collapsed. A drag
# onto a stub lands on one of that node's ports, picked from a list
# (`land_choices`), through `Edit.connect` unchanged. Presentation only:
# nothing here changes a row.

STUB_IN, STUB_OUT = "nin", "nout"
SUMMARY_LINES = 5          # at most, under a collapsed node's title
TIP_ROWS = 10              # a bundle's hover lists this many cables, then "+ k more"
EXPAND_TO_EDIT = "expand a node to edit its cables"
NOTHING_TAKES = "nothing on {label} takes it"


def stub_in(nid: str) -> str:
    """Node `nid`'s single input stub (its bundles and collapsed render cables)."""
    return f"{STUB_IN}:{nid}"


def stub_out(nid: str) -> str:
    """Node `nid`'s single output stub."""
    return f"{STUB_OUT}:{nid}"


def is_stub(pin: str) -> bool:
    return pin_kind(pin) in (STUB_IN, STUB_OUT)


def stub_node(pin: str) -> str:
    """The node a stub pin belongs to ("" for any other pin)."""
    return pin.partition(":")[2] if is_stub(pin) else ""


def _short(v: float | None) -> str:
    return "not live" if v is None else f"{v:.2f}"


def _loudest(ports: Iterable[VPort]) -> str:
    """The line for the loudest live port of `ports` (by |reading|)."""
    best = max((p for p in ports if p.live is not None), key=lambda p: abs(p.live),
               default=None)
    return "nothing live" if best is None else f"> {best.name} {best.live:.2f}"


def _count(k: int, noun: str) -> str:
    return f"{k} {noun}{'' if k == 1 else 's'}"


def summary(n: VNode) -> list[str]:
    """A collapsed node's lines under its title — at most `SUMMARY_LINES`,
    the same number every frame (only the readings move): what it holds
    and how much of it is patched, and its live reading (a device's or the
    analyzer's loudest patched port, a modifier's or an LFO's output, a
    macro's knob)."""
    outs = [p for p in n.ports if p.direction == OUT]
    params = [p for p in n.ports if p.param is not None and p.direction == IN]
    pics = [p for p in n.ports if p.type in (IMAGE, GEOMETRY, MASK)]
    patched = sum(p.patched for p in n.ports)
    lines: list[str]
    if n.kind == TEMPLATE:
        lines = [f"{_count(len(n.ports), 'mapped control')}", "+ shows its rows as cables"]
    elif n.kind in ("device", "source", "analyzer"):
        noun = "band" if n.kind == "analyzer" else "port"
        lines = [f"{_count(len(n.ports), noun)} · {patched} patched",
                 _loudest(p for p in outs if p.patched)]
        if n.layer:
            lines.append(f"{n.layer} layer · {'up' if n.up else 'down'}")
        if n.placeholder:
            lines.append("not in this rig")
        elif n.grey:
            lines.append(n.status.rpartition(" · ")[2] or "not connected")
    elif n.kind in BANK_SCHEMES:
        lines = [f"out {_short(outs[0].live if outs else None)}",
                 f"{_count(len(params), 'knob')} · {sum(p.patched for p in params)} patched"]
    elif n.kind == SEQ:
        lines = [f"{_count(len(outs), 'lane')} · {sum(p.patched for p in outs)} patched",
                 f"{_count(len(params), 'param')} · {sum(p.patched for p in params)} patched"]
    elif n.kind == "modifier":
        m = n.ref
        ins = [a for a in getattr(m, "inputs", ()) if a]
        out = _short(outs[0].live if outs else None)
        lines = [f"{getattr(m, 'kind', 'modifier')} · out {out}",
                 "in " + (", ".join(ins) if ins else "nothing yet"),
                 f"{_count(len(params), 'param')} · {sum(p.patched for p in params)} patched"]
    elif n.kind == "macro":
        knob = next((p for p in n.ports if p.direction == IN), None)
        subs = len(getattr(n.ref, "subs", ()) or ())
        lines = [f"knob {_short(knob.live if knob is not None else None)}",
                 _count(subs, "subscriber")]
    else:                                   # render, output, group
        lines = ([f"{_count(len(params), 'param')} · {sum(p.patched for p in params)} patched"]
                 if params or not pics else [])
        if pics:
            lines.append(_count(len(pics), "picture port"))
        if params:
            lines.append(_loudest(p for p in params if p.patched))
        if n.faint:                         # plan 33 U: unreached, said first
            lines.insert(0, REACHES_NOTHING)
    return lines[:SUMMARY_LINES]


@dataclass
class VBundle:
    """The one wire between two nodes while either is collapsed: every
    value and trigger cable from node `src` to node `dst`. `type` is
    TRIGGER when every cable is a trigger, else VALUE; `live` the largest
    |reading| of its live cables (None while none is live); `dormant`
    while every cable is."""

    id: str
    src: str
    dst: str
    type: str = VALUE
    cables: list[VCable] = field(default_factory=list)
    live: float | None = None
    dormant: bool = False

    @property
    def count(self) -> int:
        return len(self.cables)

    @property
    def src_port(self) -> str:
        return stub_out(self.src)

    @property
    def dst_port(self) -> str:
        return stub_in(self.dst)


def node_of(view: View, pin: str) -> str:
    """The id of the node pin `pin` is on (a stub's own node), "" if none."""
    return stub_node(pin) or view.pins.get(pin, ("",))[0]


def wiring(view: View, collapsed: Callable[[str], bool],
           drawn: Callable[[VCable], bool] | None = None,
           shown: Callable[[str], bool] | None = None,
           extra: Iterable[VCable] = ()
           ) -> tuple[list[tuple[VCable, str, str]], list[VBundle]]:
    """What the canvas draws this frame for `view`: the cables drawn one
    wire each, as (cable, the pin it leaves, the pin it lands on), and the
    bundles. A value or trigger cable with a `collapsed` end goes into the
    bundle of its (source node, target node) pair; a render cable stays
    itself, its collapsed ends moved to the node's stub; a cable between
    two expanded nodes is drawn as it is. `drawn(cable)` (a desk template's
    closed rows: False) leaves a cable out altogether, and so does
    `shown(node id)` False for either end (plan 28 N9: an idle node is not
    drawn); `extra` are the through wires over hidden effects, drawn as
    render cables are. Bundles are in the order of their first cable;
    their readings are this frame's."""
    singles: list[tuple[VCable, str, str]] = []
    pairs: dict[tuple[str, str], VBundle] = {}
    for c in (*view.cables, *extra):
        if drawn is not None and not drawn(c):
            continue
        s, d = node_of(view, c.src_port), node_of(view, c.dst_port)
        if shown is not None and not (shown(s) and shown(d)):
            continue
        shut_s, shut_d = collapsed(s), collapsed(d)
        if c.kind in ("render", THROUGH) or c.type in RENDER_TYPES:
            singles.append((c, stub_out(s) if shut_s else c.src_port,
                            stub_in(d) if shut_d else c.dst_port))
        elif shut_s or shut_d:
            b = pairs.get((s, d))
            if b is None:
                b = pairs[(s, d)] = VBundle(f"bundle:{s}>{d}", s, d)
            b.cables.append(c)
        else:
            singles.append((c, c.src_port, c.dst_port))
    for b in pairs.values():
        b.type = TRIGGER if all(c.type == TRIGGER for c in b.cables) else VALUE
    bundles = list(pairs.values())
    readings(bundles)
    return singles, bundles


def readings(bundles: Iterable[VBundle]) -> None:
    """Each bundle's reading this frame from its cables' (`refresh` moved
    them): the largest live |reading|, dormant while every cable is — so a
    page may keep `wiring`'s answer while the collapse state holds."""
    for b in bundles:
        lives = [abs(c.live) for c in b.cables if c.live is not None and not c.dormant]
        b.live = max(lives) if lives else None
        b.dormant = all(c.dormant for c in b.cables)


def cable_words(view: View, c: VCable) -> str:
    """One cable as a bundle's hover lists it: "<source port> → <param>"."""
    src, dst = view.owner(c.src_port), view.owner(c.dst_port)
    a = src[1].name if src and src[1] else (c.addr or c.src_port)
    b = (dst[1].param or dst[1].name) if dst and dst[1] else c.dst_port.partition(":")[2]
    return f"{a} → {b}"


def bundle_tip(view: View, b: VBundle) -> str:
    """What hovering a bundle says: "<n> cables: <source port> → <param>,
    …" — the first `TIP_ROWS`, then "+ k more" — and its reading."""
    s, d = view.node(b.src), view.node(b.dst)
    head = f"{s.label if s else b.src}  →  {d.label if d else b.dst}"
    noun = "cable" if b.count == 1 else "cables"
    rows = [cable_words(view, c) for c in b.cables[:TIP_ROWS]]
    more = b.count - len(rows)
    body = f"{b.count} {noun}: " + ", ".join(rows) + (f", + {more} more" if more > 0 else "")
    lines = [head, body, f"reading {_short(b.live)}"]
    if b.dormant:
        lines.append("dormant")
    return "\n".join(lines)


def stub_pin(view: View, pin: str) -> str:
    """What a stub stands for in a drag: a node's ``out`` stub, when the
    node has exactly one output pin (a modifier's lane, an LFO's, a macro's
    bus), is that pin — so a collapsed modifier is patched from its stub
    with no picker on its side; any other pin is itself."""
    if pin_kind(pin) != STUB_OUT:
        return pin
    n = view.node(stub_node(pin))
    outs = [q for port in (n.ports if n is not None else ()) if port.direction == OUT
            for q in port.pins]
    return outs[0] if len(outs) == 1 else pin


def land_choices(view: View, edit, fixed: str, nid: str
                 ) -> list[tuple[str, str, str, str | None]]:
    """A drag from pin `fixed` let go on collapsed node `nid`'s stub: the
    pins of that node it could land on, as (pin, label, port group, why
    `Edit.connect` would refuse it — None when it would act or ask). From
    an output pin, the node's input pins (a param's `mod` / `base` /
    `depth` stub, a modifier's input, a render port); from an input pin,
    its output pins. `edit` is the page's `Edit` (None: nothing refused)."""
    n = view.node(nid)
    if n is None:
        return []
    out: list[tuple[str, str, str, str | None]] = []
    from_out = is_output(fixed)
    for port in n.ports:
        if (port.direction == OUT) == from_out:
            continue
        for pin in port.pins:
            stub = pin_kind(pin) if port.param is not None else ""
            label = f"{port.name} · {stub}" if stub else port.name
            src, dst = (fixed, pin) if from_out else (pin, fixed)
            why = edit.refusal(src, dst) if edit is not None else None
            out.append((pin, label, port.group, why))
    return out



# ---------------------------------------------------------------- editing (plan 28 N3)
#
# `Edit` turns a gesture on the canvas — a cable dragged from one pin to
# another, a cable deleted, a modifier dropped onto a cable, a node picked
# or deleted — into the binding table's own calls (`Bindings.add`,
# `replace_owner`, `move_route`, `remove`, `bind`, the macros' subscribers,
# `add_modifier` / `set_modifiers` / `remove_modifier`), so undo (which
# watches the table), the preset's dirt, the referee and the session /
# preset split are what they are for ROUTING. Each request returns what the
# table call returned, a `Refusal` (the words the page shows, nothing
# changed) or an `Ask` (the target has a performer: the page puts up the
# same Replace / Keep prompt ROUTING does, `ui_routing.ask`, and *Replace*
# runs `commit`).
#
# **The seam with plan 28 N4** (render-graph edits): a request is
# dispatched by the type of the pins it joins. Value and trigger pins are
# this section's (`connect_value`, `disconnect_value`, `remove_value_node`);
# an image, geometry or mask pin, a render cable or a render node goes to
# the method N4 adds beside them — `Edit.wire(src, dst)`,
# `Edit.unwire(cable)`, `Edit.remove_render_node(node id)`, and
# optionally `Edit.wire_refusal(src, dst)` for the drag's feedback —
# looked up by name (`_render`; a plain-words refusal from them becomes a
# `Refusal`). `RENDER_NOT_YET` is said only by an Edit without them.

RENDER_TYPES = (IMAGE, GEOMETRY, MASK)
RENDER_NOT_YET = "render cables: not yet"
# the words a refusal says
NOT_A_PORT = "not a port"
SAME_SIDE = "join an output to an input"
HAND_NO_BASE = "a hand sets no base; aim at mod"
NO_BASE = "{what} sets no base; aim at mod"
DESK_NO_MOD = "{what} sets a base, not a performer; aim at base"
MACRO_NO_MOD = "a macro sets a base or scales a depth; aim at base or a depth stub"
MACRO_NO_MACRO = "a macro cannot set a macro"
ONLY_MACRO_DEPTH = "only a macro scales a route's depth; drag from a macro"
NO_ROUTE_DEPTH = "no route lands on {pid}: nothing to scale"
NOT_MODULATABLE = "{label} is not modulatable: no performer may drive it"
NO_PARAM = "no param {pid}"
ALREADY = "already patched"
SELF_LOOP = "a modifier cannot read itself (a loop)"
MACRO_NO_LANE = "a macro is no lane: it cannot feed a modifier"
NO_LANE = "{what} is no lane: it cannot feed a modifier"
KEY_ROWS = "keys are the session's rows: map them on ROUTING"
MOD_ONLY_ROUTE = "a modifier goes onto a route or a modifier's input"
ROUTE_END = "a route's end moves to another param's mod"
SESSION_ROW = "{what} is the session's (bindings.json): edit it on ROUTING"
SHIFT_NODE = "{addr} on the SHIFT node is the session's (bindings.json): map it on ROUTING"
NOT_REMOVABLE = "{label}: the rig's, not the preset's (nothing to delete)"
NO_SUCH_MOD = "no modifier {kind}"
# plan 31 G1: the banks' nodes and the sequencer's bindings
LANE_ENV_KEPT = "{label} is a sequencer lane's envelope: it stays (an extra one can go)"
BANK_FULL = "{k} {what}, the most there can be: delete one to add another"


def bank_refusal(bank, scheme: str) -> str | None:
    """Why the picker may not add a voice to `bank`: `BANK_FULL` at the
    cap, else the bank's own reason (`modbank.Bank.refusal`: its ids used
    up), or None."""
    why = bank.refusal()
    if why is not None and len(bank) >= bank.MAX:
        return BANK_FULL.format(k=len(bank), what=BANK_WORDS[scheme][1])
    return why
NO_BANK = "no {what} bank on this rig"
LANE_NO_DELETE = ("a lane always fires an envelope: drag its pin onto another "
                  "envelope's fire to rebind it")
LANE_BOUND = "lane {lane} fires env {env} already"

# a continuous scheme's noun for the refusals ("a hand sets no base")
NOUNS = {"hand": "a hand", "hands": "the hands", "lane": "a band", "lfo": "an LFO",
         "env": "an envelope", SEQ: "a sequencer lane",
         "mod": "a modifier", "axis": "a stick", "ext": "an outside lane"}
DESK_NOUNS = {"cc": "a desk knob", "note": "a desk button", "pitch": "a desk fader",
              "pad": "a pad button", "hat": "the D-pad", "key": "a key"}
OUT_PINS = ("out", "bus", "rout")


class Refusal(str):
    """A request the table did not take, in the words the page shows."""


@dataclass
class Ask:
    """The target has a performer (`Owned`): `old` holds it, `new` asks;
    *Replace* runs `commit` (`Bindings.replace_owner`, which reads the
    owner at that moment). Nothing has changed yet."""

    old: Binding
    new: Binding
    commit: Callable[[], Any]


def pin_kind(pin: str) -> str:
    """A pin's prefix: ``out`` / ``bus`` / ``rout`` (outputs), ``mod`` /
    ``base`` / ``depth`` / ``in`` / ``rin`` (inputs)."""
    return pin.partition(":")[0]


def is_output(pin: str) -> bool:
    return pin_kind(pin) in OUT_PINS


def _scheme(addr: str) -> str:
    return base_scheme(addr.partition(":")[0])


def _noun(addr: str) -> str:
    return NOUNS.get(_scheme(addr), f"a {_scheme(addr)} source")


def _desk_noun(addr: str) -> str:
    return DESK_NOUNS.get(_scheme(addr), f"a {_scheme(addr)} control")


class Edit:
    """The canvas's edits on one table. `view` is the page's current view
    (the pins' types, the sources' addresses, whether a source is centred,
    the cable a drag picked up); `router` resolves lanes and rests (None:
    addresses compare as strings). `profile` is the desk's profile module,
    duck-typed, for the desk learn a MIDI cable into `base` goes through
    (the page passes `apc40`, as the panel's click-to-map does)."""

    def __init__(self, table: Bindings | None = None, reg: Registry | None = None,
                 router: Router | None = None, view: View | None = None, profile=None, *,
                 graph=None, render=None, push: Callable[[str], None] | None = None):
        self.table, self.reg, self.router, self.view = table, reg, router, view
        self.profile = profile
        # plan 28 N4, the render edits: the preset's `GraphSection` they land
        # through, the renderer's last graph (canvas pins → names), the undo
        # step pushed before a landing (the page: `undo.push(label,
        # load=True)`; None: none), the last edit's words
        self.graph, self.render, self.push = graph, render, push
        self.said = ""
        self.added = ""         # plan 33 U: the node the last add or insert made (its name)

    # ---- the render graph (plan 28 N4): each returns None (done; its
    # words in `said`) or a refusal in words, nothing changed ----

    def wire(self, src_port: str, dst_port: str, dry: bool = False) -> str | None:
        """A picture from `src_port` into `dst_port` (a geometry cable: the
        hands node's place). `dry`: only say whether it may be."""
        return render_wire(self, src_port, dst_port, dry)

    def wire_refusal(self, src_port: str, dst_port: str) -> str | None:
        """Why `wire` would refuse, changing nothing (the drag's words)."""
        return self.wire(src_port, dst_port, dry=True)

    def unwire(self, cable, dst: str | None = None) -> str | None:
        """Take a render cable (a `VCable`, or its two ends; one port's
        name alone: whatever is wired into it) out of the graph."""
        return render_unwire(self, cable, dst)

    def add_node(self, kind: str, file: str | None = None, **settings) -> str | None:
        """The picker: an effect instance (`EffectAt(file, n + 1)`), a hands
        node (`HandsAt(n + 1)`), a composite or (plan 33 U) a switch — an
        effect, a composite and a switch on no wire (unreached, faint, until
        one is wired). The new node's name is `added`."""
        return render_add(self, kind, file, **settings)

    def insert_effect(self, cable, file: str) -> Refusal | None:
        """Plan 33 U: the next instance of effect `file` onto picture cable
        `cable` (a `VCable`, or its two ends: pins or the section's names):
        `src → new.image`, `new → dst`, in one landing (one undo step).
        Into the run's `frame → fx.image` it is the run's one effect (R9)."""
        why = render_insert(self, cable, file)
        return Refusal(why) if why is not None else None

    def place_effect(self, cable, name: str) -> Refusal | None:
        """Plan 33 U: effect instance `name` (an existing one: a free node
        dropped on a cable, or one dragged out of its place — reordering the
        run is this) taken out of wherever its picture goes, the wires
        either side of it closed over it, and put onto `cable` — one
        landing."""
        why = render_place(self, cable, name)
        return Refusal(why) if why is not None else None

    def drop_node(self, node: str) -> str | None:
        """Delete a render node — an extra effect instance, hands node or
        composite — out of the section, with every wire on it."""
        return render_drop(self, node)

    remove_render_node = drop_node          # N3's name for it (`remove_node`)

    def set_node(self, node: str, **settings) -> str | None:
        """A node's setting: a hands node's `draw` / `into`, a composite's `blend`."""
        return render_set(self, node, **settings)

    # ---- what a pin is ----

    def _port(self, pin: str) -> VPort | None:
        hit = self.view.owner(pin) if self.view is not None else None
        return hit[1] if hit is not None else None

    def type_of(self, pin: str) -> str:
        """A pin's signal type: the view's, else by its prefix."""
        port = self._port(pin)
        if port is not None:
            return port.type
        return IMAGE if pin_kind(pin) in ("rout", "rin") else VALUE

    def is_render(self, *pins: str) -> bool:
        """Does a request on `pins` belong to the render graph (N4's)?"""
        return any(pin_kind(p) in ("rout", "rin") or self.type_of(p) in RENDER_TYPES
                   for p in pins)

    def address(self, pin: str) -> str | None:
        """The source address an ``out:`` pin reads."""
        if pin_kind(pin) != "out":
            return None
        port = self._port(pin)
        if port is not None and port.addr:
            return port.addr
        return pin.partition(":")[2] or None

    def _centred(self, pin: str) -> bool:
        port = self._port(pin)
        return bool(port is not None and port.bipolar)

    def _same_lane(self, a: str, b: str) -> bool:
        if a == b:
            return True
        if self.router is None:
            return False
        la = self.router.lane(a)
        return la[1] >= 0 and la == self.router.lane(b)

    def _render(self, name: str, *args):
        """N4's method `name` (`wire`, `unwire`, `remove_render_node`), or
        the refusal until it lands."""
        fn = getattr(self, name, None)
        if fn is None:
            return Refusal(RENDER_NOT_YET)
        res = fn(*args)
        # N4's methods refuse in plain words: a Refusal to the page
        return Refusal(res) if isinstance(res, str) and not isinstance(res, Refusal) else res

    @staticmethod
    def ordered(a: str, b: str) -> tuple[str, str]:
        """(output, input): a drag may start at either end."""
        return (b, a) if is_output(b) and not is_output(a) else (a, b)

    def _param(self, pid: str) -> Param | None:
        p = self.reg.get(pid)
        if p is None:
            return None
        real = getattr(self.reg, "real", None)
        return real(p) if real is not None else p

    # ---- a cable dragged ----

    def connect(self, src_port: str, dst_port: str):
        """A cable dragged from `src_port` to `dst_port` (either order).
        Dispatched by type: a render pin is N4's (`wire`). Between two
        input pins — a cable's end picked up where it lands and dropped on
        another — the cable moves (`move`). A sequencer lane's pin onto an
        envelope's ``fire`` base stub rebinds the lane (`bind_lane`)."""
        if self.is_render(src_port, dst_port):
            return self._render("wire", *self.ordered(src_port, dst_port))
        bound = self._binding(*self.ordered(src_port, dst_port))
        if bound is not None:
            return self.bind_lane(*bound)
        if is_output(src_port) == is_output(dst_port):
            return self.move(src_port, dst_port)
        return self.connect_value(*self.ordered(src_port, dst_port))

    def refusal(self, src_port: str, dst_port: str) -> str | None:
        """Why `connect` would refuse, changing nothing (the drag's words
        while it is held); None when it would act or ask."""
        if self.is_render(src_port, dst_port):
            if getattr(self, "wire", None) is None:
                return RENDER_NOT_YET
            check = getattr(self, "wire_refusal", None)
            return check(*self.ordered(src_port, dst_port)) if check is not None else None
        if is_output(src_port) == is_output(dst_port):
            return self._move_refusal(src_port, dst_port)
        bound = self._binding(*self.ordered(src_port, dst_port))
        if bound is not None:
            return self._bind_refusal(*bound)
        return self._value_refusal(*self.ordered(src_port, dst_port))

    # ---- a sequencer lane's envelope (plan 31 G1) ----

    def _binding(self, src: str, dst: str) -> tuple[int, int] | None:
        """(0-based lane, envelope id) when `src` is a sequencer lane's pin
        and `dst` an envelope's ``base:env.<n>.fire`` — a binding, not a
        route (a route from the lane lands on ``mod``); else None."""
        if pin_kind(dst) != BASE:
            return None
        head, n, tail = ([*dst.partition(":")[2].split("."), "", "", ""])[:3]
        if head != envmod.GROUP or tail != "fire" or not n.isdecimal():
            return None
        hit = self.view.owner(src) if self.view is not None else None
        if hit is None or hit[0].kind != SEQ or hit[1] is None or not hit[1].addr:
            return None
        addr = hit[1].addr
        if self.router is not None:
            li = self.router.lane(addr)[1]
        else:
            tail_i = addr.partition(":")[2]
            li = int(tail_i) if tail_i.isdecimal() else -1
        return (li, int(n)) if 0 <= li < seqmod.LANES else None

    def _bind_refusal(self, lane: int, env: int) -> str | None:
        pid = f"{seqmod.GROUP}.{lane + 1}.env"
        p = self.reg.get(pid) if self.reg is not None else None
        if p is None:
            return NO_PARAM.format(pid=pid)
        if f"{envmod.GROUP}.{env}.fire" not in self.reg:
            return NO_PARAM.format(pid=f"{envmod.GROUP}.{env}.fire")
        if round(float(p.value)) == env:
            return LANE_BOUND.format(lane=lane + 1, env=env)
        return None

    def bind_lane(self, lane: int, env: int):
        """Sequencer lane `lane` (0-based) fires envelope `env` from now on:
        its ``seq.<l>.env`` param set — the fixed link the sequencer calls,
        no row. (lane, env), or a Refusal when it may not be."""
        why = self._bind_refusal(lane, env)
        if why is not None:
            return Refusal(why)
        self.reg[f"{seqmod.GROUP}.{lane + 1}.env"].set(env)
        return (lane, env)

    def _value_refusal(self, src: str, dst: str) -> str | None:
        kind, pid = pin_kind(dst), dst.partition(":")[2]
        skind = pin_kind(src)
        if skind not in ("out", "bus") or kind not in (MOD, BASE, DEPTH, "in"):
            return NOT_A_PORT
        addr = self.address(src)
        if kind == "in":
            return self._input_refusal(skind, addr, pid)
        p = self._param(pid)
        if p is None:
            return NO_PARAM.format(pid=pid)
        if skind == "bus":
            return self._macro_refusal(src.partition(":")[2], kind, p)
        if addr is None:
            return NOT_A_PORT
        scheme = addr.partition(":")[0]
        if kind == DEPTH:
            return ONLY_MACRO_DEPTH
        if kind == MOD:
            if not is_continuous(scheme):
                return KEY_ROWS if _scheme(addr) == "key" else DESK_NO_MOD.format(
                    what=_desk_noun(addr))
            if not p.modulatable:
                return NOT_MODULATABLE.format(label=p.label or p.id)
            cur = self.table.owner(p.id)
            if cur is not None and self._same_lane(cur.source, addr):
                return ALREADY
            return None
        # into base: a setter row, for a desk control or a pad button only
        if is_continuous(scheme):
            noun = _noun(addr)
            return HAND_NO_BASE if noun == "a hand" else NO_BASE.format(what=noun)
        if _scheme(addr) == "key":
            return KEY_ROWS
        if p.id == SAVE_PARAM:
            return learnmod.SAVE_REFUSAL
        if Binding(addr, p.id).is_midi:
            # plan 28 N5 (D5): the global layer is never a Learn target, so a
            # drag from the SHIFT node is refused whatever the latch
            port = self._port(src)
            if port is not None and port.layer == GLOBAL_LAYER:
                return SHIFT_NODE.format(addr=addr)
            why = learnmod.blocked(self.table, addr)
            if why == "invariant":
                return f"{addr} is invariant (the session's)"
            if why == "global":
                return f"{addr} is on the global layer: latch SHIFT off to map into the preset"
        return None

    def _input_refusal(self, skind: str, addr: str | None, pid: str) -> str | None:
        mid, _, k = pid.rpartition(".")
        m = self.table.modifier(mid)
        if m is None or not k.isdigit() or int(k) >= len(m.inputs):
            return NOT_A_PORT
        if skind == "bus":
            return MACRO_NO_LANE
        if addr is None:
            return NOT_A_PORT
        if not is_continuous(addr.partition(":")[0]):
            return NO_LANE.format(what=_desk_noun(addr))
        if modmod.id_of(addr) == mid:
            return SELF_LOOP
        if m.inputs[int(k)] and self._same_lane(m.inputs[int(k)], addr):
            return ALREADY
        return None

    def _macro_refusal(self, mid: str, kind: str, p: Param) -> str | None:
        if kind == MOD:
            return MACRO_NO_MOD
        m = self.table.macros.get(mid)
        if kind == BASE:
            if is_macro(p.id):
                return MACRO_NO_MACRO
            why = base_refusal(p.id, self.reg)
            if why is not None:
                return why
            if m is not None and any(s.base == p.id for s in m.subs):
                return ALREADY
            return None
        r = self._route_on(p.id)
        if r is None:
            return NO_ROUTE_DEPTH.format(pid=p.id)
        if m is not None and any(s.depth == (r.source, r.target) for s in m.subs):
            return ALREADY
        return None

    def connect_value(self, src: str, dst: str):
        """`src` (an output pin: a source's ``out:``, a macro's ``bus:``)
        into `dst` (a param's ``mod`` / ``base`` / ``depth`` stub, a
        modifier's ``in``)."""
        why = self._value_refusal(src, dst)
        if why is not None:
            return Refusal(why)
        kind, pid = pin_kind(dst), dst.partition(":")[2]
        if kind == "in":
            mid, _, k = pid.rpartition(".")
            return self.set_input(mid, int(k), self.address(src))
        if pin_kind(src) == "bus":
            return self.subscribe(src.partition(":")[2], kind, pid)
        addr = self.address(src)
        p = self._param(pid)
        if kind == MOD:
            return self._add(self.route_for(src, p))
        return self._setter(addr, p)

    def route_for(self, src: str, p: Param) -> Binding:
        """The route a cable from `src` into `p`'s mod makes: the hand
        learn's row (`learn.row_for`) — a push at the hands' Learn depth
        (`hands.learn_depth`) where the source or the param is centred,
        else the `position` fader at 1."""
        addr = self.address(src)
        depth = None
        if _scheme(addr) == "hand":
            hd = self.reg.get("hands.learn_depth")
            depth = float(hd.value) if hd is not None else None
        return learnmod.row_for(addr, p, centred=self._centred(src), depth=depth)

    def _add(self, b: Binding):
        table = self.table
        try:
            return table.add(b)
        except Owned as e:
            return Ask(e.existing, b, lambda: table.replace_owner(b))
        except ValueError as e:
            return Refusal(str(e))

    def _setter(self, addr: str, p: Param):
        """A desk control or a pad button into `p`'s base: the row the
        desk learn makes (`Learn.learn_control`: a preset-layer row through
        `bind(write=False)`) or the pad learn (`Learn.learn_pad_button`:
        the session's row, `bindings.json` written) — through a Learn of
        its own, so the rules are theirs and nothing of the panel's learn
        (an armed param, a held question) is touched. One undo step (the
        learn's own)."""
        lane = self.router.lane if self.router is not None else None
        lrn = learnmod.Learn(self.reg, self.table, lane=lane)
        lrn.arm(p.id)
        landed = (lrn.learn_control(addr, self.profile) if Binding(addr, p.id).is_midi
                  else lrn.learn_pad_button(addr))
        if not landed:
            return Refusal(lrn.last or f"{addr} did not land on {p.id}")
        return next((b for b in reversed(self.table.bindings)
                     if b.source == addr and b.target == p.id), None)

    def subscribe(self, mid: str, kind: str, pid: str) -> Sub:
        """A macro's cable: into `pid`'s base (a base subscriber, from = to
        = where the param sits, so adding it moves nothing — ROUTING's
        "+ base") or onto the depth of the route landing on `pid` (a depth
        subscriber over 0…1 — ROUTING's "+ depth")."""
        if kind == BASE:
            p = self._param(pid)
            s = Sub(base=p.id, lo=p.norm, hi=p.norm)
        else:
            r = self._route_on(pid)
            s = Sub(depth=(r.source, r.target), lo=0.0, hi=1.0)
        self.table.macros.setdefault(mid, Macro()).subs.append(s)
        self.table.macros_serial += 1
        return s

    def _route_on(self, pid: str) -> Binding | None:
        """The route a `depth:<pid>` stub stands for: the param's performer,
        else its first route (a sleeping one)."""
        return self.table.owner(pid) or next(iter(self.table.routes_to(pid)), None)

    def set_input(self, mid: str, k: int, source: str | None):
        """Modifier `mid`'s input `k` reads `source` ("" / None: none) —
        N1's path (`ui_routing.set_modifier_input`): the modifier replaced
        whole, its params at their bases. Returns `set_modifiers`' notes."""
        return self.table.set_modifier_input(mid, k, source, self.reg)

    # ---- a cable's end moved ----

    def _cable_at(self, pin: str) -> VCable | None:
        """The cable ending on input pin `pin` (a route's ``mod``, a
        modifier's ``in``) — the one a drag from that pin picks up: on a
        `mod` stub the param's performer's (`Bindings.owner`) before a
        sleeping route on the same param."""
        if self.view is None:
            return None
        here = [c for c in self.view.cables if c.dst_port == pin
                and c.kind in ("route", "input")]
        if pin_kind(pin) == MOD:
            owner = self.table.owner(pin.partition(":")[2])
            mine = next((c for c in here if c.ref is owner), None)
            if mine is not None:
                return mine
        return here[0] if here else None

    def _picked(self, a: str, b: str) -> tuple[VCable | None, str]:
        picked = self._cable_at(a)
        if picked is not None:
            return picked, b
        return self._cable_at(b), a

    def _move_refusal(self, a: str, b: str) -> str | None:
        if is_output(a) and is_output(b):
            return SAME_SIDE
        picked, to = self._picked(a, b)
        if picked is None:
            return SAME_SIDE
        if picked.kind == "input":
            if pin_kind(to) != "in":
                return SAME_SIDE
            return self._value_refusal(f"out:{picked.addr}", to)
        if pin_kind(to) != MOD:
            return ROUTE_END
        p = self._param(to.partition(":")[2])
        if p is None:
            return NO_PARAM.format(pid=to.partition(":")[2])
        if p.id == picked.ref.target:
            return ALREADY
        if not p.modulatable:
            return NOT_MODULATABLE.format(label=p.label or p.id)
        return None

    def move(self, a: str, b: str):
        """A cable's end picked up at input pin `a` and dropped on input pin
        `b` (or the reverse): a route re-pointed at another param
        (`move_route`, its depth subscribers with it; a taken param asks,
        and *Replace* is `replace_owner(row, target=…)`), or a modifier's
        input moved to another modifier's input."""
        why = self._move_refusal(a, b)
        if why is not None:
            return Refusal(why)
        picked, to = self._picked(a, b)
        if picked.kind == "input":
            m, k = picked.ref
            res = self.connect_value(f"out:{picked.addr}", to)
            if not isinstance(res, Refusal):
                self.set_input(m.id, k, "")
            return res
        row, pid = picked.ref, self._param(to.partition(":")[2]).id
        cur = self.table.owner(pid)
        if cur is not None and cur is not row:
            return Ask(cur, row, lambda: self.table.replace_owner(row, target=pid))
        return self.table.move_route(row, target=pid)

    # ---- a cable deleted ----

    def disconnect(self, cable: VCable):
        """Delete a cable: dispatched by kind (a render cable is N4's,
        `unwire`; a sequencer lane's binding is refused: it is rebound)."""
        if cable.kind == "render" or cable.type in RENDER_TYPES:
            return self._render("unwire", cable)
        if cable.kind == "lane":
            return Refusal(LANE_NO_DELETE)
        return self.disconnect_value(cable)

    def disconnect_value(self, cable: VCable):
        """A route → `remove` (its depth subscribers go with it); a desk
        row of the loaded preset → `remove`; a macro subscriber → out of
        its macro; a modifier's input → unset. The session's rows (keys,
        the pad, an invariant or global-layer desk row) are `bindings.json`'s
        and are refused: ROUTING edits them."""
        table = self.table
        if cable.kind == "route":
            return table.remove(cable.ref)
        if cable.kind == "setter":
            b = cable.ref
            if is_session_row(b):
                return Refusal(SESSION_ROW.format(what=b.source))
            table.remove(b)
            table.redraw_serial += 1
            return None
        if cable.kind == "sub":
            mid, s = cable.ref
            m = table.macros.get(mid)
            if m is None:
                return Refusal(NOT_A_PORT)
            m.subs = [x for x in m.subs if x is not s]
            table.macros_serial += 1
            return None
        if cable.kind == "input":
            m, k = cable.ref
            return self.set_input(m.id, k, "")
        return Refusal(NOT_A_PORT)

    # ---- nodes ----

    def add_modifier(self, kind: str, inputs: Iterable[str] = ()):
        """A new modifier node (`Bindings.add_modifier`, its params declared)."""
        if kind not in modmod.KINDS:
            return Refusal(NO_SUCH_MOD.format(kind=kind))
        return self.table.add_modifier(kind, tuple(inputs), self.reg)

    def insert_modifier(self, cable: VCable, kind: str):
        """A modifier dropped onto a cable: `kind` makes a new one, a
        modifier's id (``mod.3``) uses that one. The cable's source becomes
        its (first) input and its lane the cable's new source — a route's
        through `move_route` (op, depth and depth subscribers kept; a push
        keeps the rest its old source had, so a centred hand stays centred
        through a smooth), a modifier's input through `set_input`."""
        if cable.kind not in ("route", "input") or not cable.addr:
            return Refusal(MOD_ONLY_ROUTE)
        src = cable.addr
        table = self.table
        if kind in modmod.KINDS:
            m = table.add_modifier(kind, (src,), self.reg)
        else:
            m = table.modifier(kind)
            if m is None:
                return Refusal(NO_SUCH_MOD.format(kind=kind))
            if m.address == src or (cable.kind == "input" and cable.ref[0].id == m.id):
                return Refusal(SELF_LOOP)
            self.set_input(m.id, 0, src)
            m = table.modifier(kind)
        if cable.kind == "input":
            owner, k = cable.ref
            self.set_input(owner.id, k, m.address)
            return m
        b = cable.ref
        if b.op == "push" and b.rest is None and self.router is not None:
            b.rest = self.router.rest_of(src)
        table.move_route(b, source=m.address)
        return m

    def show_macro(self, mid: str):
        """An idle macro picked on the canvas: it gets a label ("macro 3"),
        so ROUTING's macro strip and the canvas both name it as in use."""
        if not is_macro(mid) or mid not in self.reg:
            return Refusal(NO_PARAM.format(pid=mid))
        m = self.table.macros.setdefault(mid, Macro())
        if not m.label:
            m.label = f"macro {mid.rpartition('.')[2]}"
        self.table.macros_serial += 1
        return m

    def remove_node(self, nid: str):
        """Delete a node: a modifier (`remove_modifier`: its params go, a
        route on its lane stays, dormant); a macro (its label and every
        subscriber go — the knob stays: the eight are the rig's); a render
        node is N4's (`remove_render_node`); anything else is the rig's (a
        device, the analyzer, an LFO, a group) and is refused."""
        node = self.view.node(nid) if self.view is not None else None
        if node is not None:
            kind = node.kind
        else:
            kind = ("modifier" if modmod.number(nid) else "macro" if is_macro(nid)
                    else "render" if nid.startswith("render:")
                    else nid.partition(".")[0] if voice_of(nid) else "")
        if kind in ("render", "output"):
            return self._render("remove_render_node", nid)
        if kind in BANK_SCHEMES:
            return self.remove_voice(nid, node)
        return self.remove_value_node(nid, kind, node)

    # ---- a bank's voices (plan 31 G1) ----

    def remove_voice(self, nid: str, node: VNode | None = None):
        """Delete an LFO or an extra envelope (``lfo.3``, ``env.7``) through
        its bank (`Bank.remove`): its params go, the ids above keep theirs,
        a route on its lane goes dormant. A lane envelope (1–5) is refused.
        None when it went."""
        hit = voice_of(nid)
        label = node.label if node is not None else nid
        if hit is None:
            return Refusal(NOT_REMOVABLE.format(label=label))
        scheme, n = hit
        if scheme == envmod.GROUP and n in LANE_ENVS:
            return Refusal(LANE_ENV_KEPT.format(label=label))
        bank = bank_of(self.router, scheme)
        if bank is None:
            return Refusal(NO_BANK.format(what=BANK_WORDS[scheme][0]))
        if not bank.remove(n):
            return Refusal(NOT_REMOVABLE.format(label=label))
        return None

    def add_voice(self, scheme: str):
        """A new LFO or envelope (`Bank.add`, one past the highest id, its
        params declared): its node id (``lfo.5``), or a Refusal at the cap."""
        if scheme not in BANK_SCHEMES:
            return Refusal(NOT_A_PORT)
        bank = bank_of(self.router, scheme)
        if bank is None:
            return Refusal(NO_BANK.format(what=BANK_WORDS[scheme][0]))
        why = bank_refusal(bank, scheme)
        if why is not None:
            return Refusal(why)
        return f"{scheme}.{bank.add()}"

    def remove_value_node(self, nid: str, kind: str, node: VNode | None = None):
        if kind == "modifier" and self.table.modifier(nid) is not None:
            return self.table.remove_modifier(nid, self.reg)
        if kind == "macro" and nid in self.table.macros:
            return self.table.set_macros(
                {k: v for k, v in self.table.macros_doc().items() if k != nid}, self.reg)
        return Refusal(NOT_REMOVABLE.format(label=node.label if node is not None else nid))


# ---- a node dropped onto a cable: the geometry ----

LINK_STRENGTH = 100.0      # imgui_node_editor's default `Style.link_strength`
NEAR = 14.0                # canvas units: how close a drop must come to a cable


def bezier(p0, p3, strength: float = LINK_STRENGTH, steps: int = 16) -> list[tuple]:
    """A cable's curve as the widget draws it: a cubic from an output pin
    at `p0` to an input pin at `p3`, its handles `strength` out to the
    right of the output and to the left of the input."""
    p1 = (p0[0] + strength, p0[1])
    p2 = (p3[0] - strength, p3[1])
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        a, b, c, d = u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _seg_dist(p, a, b) -> float:
    ax, ay = b[0] - a[0], b[1] - a[1]
    n = ax * ax + ay * ay
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / n))
    return math.hypot(p[0] - (a[0] + t * ax), p[1] - (a[1] + t * ay))


def cable_near(view: View, pins: Mapping[str, tuple], point, within: float = NEAR,
               kinds=("route", "input"), skip: Iterable[str] = ()) -> VCable | None:
    """The cable of `kinds` nearest `point` (canvas units) within
    `within`, by the curve the widget draws between its pins' positions
    (`pins`: pin → (x, y), as the page last drew them); None. A cable into
    or out of a node in `skip` (the node being dropped) is passed over. A
    render cable with a collapsed end is drawn to that node's stub (plan 28
    N7), so the stub's position stands for the pin it does not draw."""
    skip = set(skip)
    best, dist = None, within
    for c in view.cables:
        if c.kind not in kinds:
            continue
        s, d = node_of(view, c.src_port), node_of(view, c.dst_port)
        a, b = pins.get(c.src_port), pins.get(c.dst_port)
        if c.type in RENDER_TYPES:           # (a value cable's collapsed end is a bundle)
            a = a or pins.get(stub_out(s))
            b = b or pins.get(stub_in(d))
        if a is None or b is None or {s, d} & skip:
            continue
        pts = bezier(a, b)
        d = min(_seg_dist(point, a, b) for a, b in itertools.pairwise(pts))
        if d < dist:
            best, dist = c, d
    return best


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


def _is_plumbing(name: str) -> bool:
    return any(name == head or name.startswith(head if head.endswith("(") else head + "(")
               or (not head.endswith("(") and name.startswith(head + "."))
               for head in PLUMBING)


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
    # plan 33 G: the pipeline's end and the faces are wire ends — each
    # pipeline's end is `fx.image`, the shape's picture input `shape.faces`
    # (the nodes themselves stay the frame's own, `PLUMBING`)
    if head == "rin" and port == "image" and built in rgraph.FX_NAMES.values():
        return "fx.image", None
    if head == "rin" and built == "shape" and port == "faces":
        return "shape.faces", None
    nodes = getattr(render_graph, "nodes", None) or {}
    node = nodes.get(built)
    if node is None and _is_plumbing(built):     # (no graph to ask: by its name)
        return None, _plumbing(built)
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
    elif isinstance(node, rgraph.MediaNode):
        name = rgraph.media_name(node.channel)      # `media.a(wire)` is channel a's
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


def picker(edit: Edit) -> list[tuple[str, str | None, str]]:
    """The right-click picker's list: (kind, file, label) — every effect
    file this build has, (plan 33 U) a switch, then a hands node and a
    composite."""
    gs = edit.graph
    files = gs.files() if gs is not None and hasattr(gs, "files") else None
    out: list[tuple[str, str | None, str]] = [("effect", f, f) for f in sorted(files or ())]
    return out + [("switch", None, "switch"), ("hands", None, "hands"),
                  ("composite", None, "composite")]


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
    picks: an extra instance's entry kept with no place (on no wire: it
    reaches nothing, plan 33), instance 1's entry gone."""
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
        # the effect is fed by this wire now — but an aux wire (plan 32 T7)
        # is a second picture: the effect stays where it sits
        if name == w.node and not rgraph.is_aux(w):
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
        if cable.ref is not None:
            src_node, node, port = cable.ref
            src, dst = f"rout:{src_node.name}", f"rin:{node.name}/{port}"
        else:                                # (its pins name it as well)
            src, dst = cable.src_port, cable.dst_port
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
    # plan 33 U (R9, R20): the run always runs from frame to fx.image — a
    # cable of it deleted takes the effect it leads into (the last cable's:
    # the effect it leaves) out of the run, the run closed over it; the
    # empty run's own cable stays
    spec = getattr(edit.graph, "spec", None)
    if says_run(spec):
        run = rgraph.run_of(spec)
        here = [w for w in _run_cables(run) if w.dst == d and (s is None or w.src == s)]
        if here and set(_run_cables(run)) <= set(spec.wires):
            w = here[0]
            if w.src == "frame" and w.dst == "fx.image":
                return RUN_KEPT
            name = w.src if w.dst == "fx.image" else w.node
            doc = _doc(edit)
            _lift(doc, name)
            return _land(edit, doc, f"unwire {w}", f"{name} out of the run: the run closes "
                                                   "over it")
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


def _with_run(doc: dict, spec) -> None:
    """`doc` given the bare run `frame → fx.image` (R9) when its section
    says none (`says_run`): a node added unwired then reads as the free
    graph's, unreached, and a save writes it as `/5` — no older build's
    stack ever runs it."""
    if not says_run(spec):
        doc.setdefault("wires", []).append({"from": "frame", "to": "fx.image"})


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
        name = edit.added = rgraph.instance_name(file, n)
        # plan 33 U: on no wire — it reaches nothing until it is wired in
        # (R23, plan 33 T7: with or without a run; a section with none gets
        # the bare `frame → fx.image`, R9, so it saves as the free graph)
        _with_run(doc, spec)
        return _land(edit, doc, f"add {name}", f"{name} added: its params are fx.{name}.*")
    if kind == "switch":
        n = max([s.n for s in (spec.switches if spec is not None else ())], default=0) + 1
        sw = rgraph.SwitchAt(n)
        doc["nodes"].append(sw.to_json())
        edit.added = sw.name
        _with_run(doc, spec)
        return _land(edit, doc, f"add {sw.name}",
                     f"{sw.name} added: wire pictures into in1 … in8, pick one with "
                     f"{sw.name}.select")
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
        name = edit.added = rgraph.hands_name(n)
        return _land(edit, doc, f"add {name}", f"{name} added, drawn in the {into}")
    if kind == "composite":
        n = max([c.n for c in (spec.composites() if spec is not None else ())], default=0) + 1
        c = rgraph.CompositeAt(n, settings.get("blend", "over"))
        edit.added = c.name
        doc["nodes"].append(c.to_json())
        return _land(edit, doc, f"add {c.name}", f"{c.name} added: wire its under and over")
    return f"no node kind {kind!r}: the picker adds an effect, a switch, hands or a composite"


def _touches(x: dict, names: set[str]) -> bool:
    return x["from"] in names or x["to"].rpartition(".")[0] in names


# ---- plan 33 U: effects onto picture cables, out of their place ----

def _run_cables(run: tuple[str, ...]) -> list[rgraph.Wire]:
    """The wires of the run `frame → run… → fx.image`, in order
    (`frame → fx.image` for the empty one)."""
    names = ["frame", *run]
    return [*(rgraph.Wire(a, f"{b}.image") for a, b in zip(names, run)),
            rgraph.Wire(names[-1], "fx.image")]


def _lift(doc: dict, name: str) -> None:
    """Effect `name` out of where its picture goes, in section `doc`: the
    wire into its `image` port and every wire out of it gone, and what fed
    it wired on into each port it fed — the run (or a branch) closed over
    it, so a run emptied is `frame → fx.image` again (R9). A wire into its
    `aux` stays; a D1 placement of it goes; (R21) an instance 1 left on no
    wire stays named, unreached. With nothing wired in, its
    wires out simply go."""
    wires = doc.get("wires", [])
    into = next((x for x in wires if x["to"] == f"{name}.image"), None)
    outs = [x for x in wires if x["from"] == name]
    keep = [x for x in wires if x is not into and not any(x is o for o in outs)]
    if into is not None:
        keep += [{"from": into["from"], "to": o["to"]} for o in outs]
    doc["wires"] = keep
    _unplace(doc, lambda n, key, where: n == name)
    # R21: an instance 1 left on no wire is kept, named (unreached, faint)
    file, n = rgraph.split_instance(name)
    if n == 1 and not any(_touches(x, {name}) for x in keep) and not any(
            _entry_name(e) == name for e in doc.get("nodes", [])):
        doc.setdefault("nodes", []).append({"kind": "effect", "file": file})


def _onto(doc: dict, s: str, d: str, name: str) -> None:
    """Effect `name` onto the cable `s → d` in section `doc`: `s →
    name.image`, `name → d` — whatever went into `d` before (the wire, or
    a D1 placement into its port) replaced."""
    def into_d(n: str, key: str, where: str) -> bool:
        if key == "after" and not where.startswith("output."):
            return f"{n}.image" == d
        return f"{where}.image" == d
    _unplace(doc, into_d)
    # (R21: an instance 1 kept unwired is named by its wires again)
    doc["nodes"] = [e for e in doc.get("nodes", []) if not (
        _entry_name(e) == name and e.get("instance", 1) == 1
        and not any(k in e for k in rgraph.PLACE_KEYS))]
    doc["wires"] = [x for x in doc.get("wires", []) if x["to"] != d] + [
        {"from": s, "to": f"{name}.image"}, {"from": name, "to": d}]


def _cable_ends(edit: Edit, cable) -> tuple[str | None, str | None, str | None]:
    """A picture cable as the section names it: (`src`, `dst port`, None),
    or (None, None, why not). `cable` is a `VCable` (its `ref`'s nodes, else
    its pins) or its two ends — canvas pins, or the section's names."""
    if isinstance(cable, VCable):
        if cable.ref is not None:
            src_node, node, port = cable.ref
            a, b = f"rout:{src_node.name}", f"rin:{node.name}/{port}"
        else:
            a, b = cable.src_port, cable.dst_port
    else:
        a, b = cable
    s, why = spec_name(a, edit.render)
    if s is None:
        return None, None, why
    d, why = spec_name(b, edit.render)
    if d is None:
        return None, None, why
    if rgraph.wire_node_kind(d) is not None:
        return None, None, f"{d} is a node, not a port: a wire goes into {rgraph.WIRE_TO_WORDS}"
    w = rgraph.Wire(s, d)
    takes = rgraph.WIRE_TAKES.get(rgraph.wire_node_kind(w.node) or "", {}).get(w.port)
    if takes != IMAGE or rgraph.WIRE_MAKES.get(rgraph.wire_node_kind(s) or "") != IMAGE:
        return None, None, f"{w} is no picture cable: an effect goes onto a picture"
    return s, d, None


def render_insert(edit: Edit, cable, file: str) -> str | None:
    s, d, why = _cable_ends(edit, cable)
    if why is not None:
        return why
    files = edit.graph.files() if hasattr(edit.graph, "files") else None
    if not file or (files is not None and file not in files):
        return f"no {file} effect in this build"
    spec = getattr(edit.graph, "spec", None)
    n = max([e.n for e in (spec.effects if spec is not None else ()) if e.file == file],
            default=1) + 1
    name = rgraph.instance_name(file, n)
    doc = _doc(edit)
    doc["nodes"].append({"kind": "effect", "file": file, "instance": n})
    _onto(doc, s, d, name)
    why = _land(edit, doc, f"insert {name} into {s} → {d}", f"{name} inserted: {s} → {name} → {d}")
    if why is None:
        edit.added = name
    return why


def render_place(edit: Edit, cable, name: str) -> str | None:
    s, d, why = _cable_ends(edit, cable)
    if why is not None:
        return why
    nm, why = spec_name(name, edit.render)
    if nm is None:
        return why
    if rgraph.wire_node_kind(nm) != "effect":
        return f"{nm} is no effect: an effect goes onto a picture cable"
    if s == nm or rgraph.Wire(s, d).node == nm:
        return f"{nm} is on that cable already"
    doc = _doc(edit)
    _lift(doc, nm)
    _onto(doc, s, d, nm)
    return _land(edit, doc, f"move {nm} onto {s} → {d}", f"{nm} moved: {s} → {nm} → {d}")


def render_drop(edit: Edit, node: str) -> str | None:
    name, why = spec_name(node, edit.render)
    if name is None:
        return why
    kind = rgraph.wire_node_kind(name)
    doc = _doc(edit)
    before = copy.deepcopy(doc)
    if kind == "effect":
        # (R21, plan 33 T7: instance 1 too — it is in the graph where it is
        # wired, and dropping it takes it out like any instance: lifted
        # first, so the unwired entry `_lift` keeps for it goes as well)
        _lift(doc, name)               # plan 33 U (R9): the run closes over it
        doc["nodes"] = [e for e in doc["nodes"] if _entry_name(e) != name]
        names = {name}
    elif kind in ("ghost", "layer"):
        _, n = rgraph.split_instance(name)
        if n == 1:
            return "hands 1 is the frame's own hands: it stays (switch it off on HANDS)"
        doc["nodes"] = [e for e in doc["nodes"] if not (e.get("kind") == "hands"
                                                         and e.get("instance", 1) == n)]
        names = {rgraph.hands_name(n), rgraph.layer_name(n)}
    elif kind in ("composite", "switch"):          # (plan 33 S: a switch the same way)
        _, n = rgraph.split_instance(name)
        doc["nodes"] = [e for e in doc["nodes"] if not (e.get("kind") == kind
                                                         and e.get("instance", 1) == n)]
        names = {name}
    else:
        return f"{name} is the frame's own: it stays"
    doc["wires"] = [x for x in doc.get("wires", []) if not _touches(x, names)]
    if not doc["wires"]:
        doc.pop("wires")
    _unplace(doc, lambda e, key, where: where in names)
    if doc == before:
        return f"{name} is not in the preset's graph"
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
